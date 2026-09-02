"""Focused preparation-layer tests for Notebook 33."""

from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from restoration_eval.final_evaluation_report import (  # noqa: E402
    EVIDENCE_CATALOG_SCHEMA_VERSION,
    LATEX_TABLE_COLUMNS,
    REPORT_SCHEMA_VERSION,
    THESIS_TABLE_COLUMNS,
    TRACEABILITY_COLUMNS,
    atomic_write_csv,
    atomic_write_text,
    build_evidence_catalog_plan,
    build_figure_plan,
    build_mock_traceability,
    build_report_section_plan,
    build_thesis_table_plan,
    image_to_data_uri,
    load_final_evaluation_config,
    load_upstream_manifests,
    render_report_html,
    resolve_final_evaluation_inputs,
    resolve_final_evaluation_outputs,
    select_final_case_grids,
    validate_inventory_contract,
    validate_loaded_input_table,
    validate_preparation_plans,
    validate_report_html,
    validate_selected_case_grids,
    validate_upstream_completion,
    visual_html,
)


class FinalEvaluationReportPreparationTests(unittest.TestCase):
    """Validate the approved Notebook 33 preparation contract."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = ROOT
        cls.config_path = ROOT / "config/evaluation/final_evaluation_report.yaml"
        cls.config = load_final_evaluation_config(cls.config_path)
        cls.settings = cls.config["final_evaluation_report"]
        cls.expected = cls.settings["expected_counts"]
        cls.inputs = resolve_final_evaluation_inputs(cls.config, ROOT)
        cls.outputs = resolve_final_evaluation_outputs(cls.config, ROOT)
        cls.inventory = pd.read_csv(
            cls.inputs["inventory_path"],
            low_memory=False,
        )

    def test_config_identity_and_output_arithmetic(self) -> None:
        self.assertEqual(self.settings["notebook_id"], "33")
        self.assertEqual(self.settings["notebook_stem"], "33_final_evaluation_report")
        self.assertFalse(self.settings["creates_new_scientific_evidence"])
        self.assertEqual(self.expected["physical_output_files"], 32)
        self.assertEqual(self.expected["artifact_records"], 8)
        self.assertEqual(self.outputs["root"], ROOT / "outputs/33_final_evaluation_report")
        self.assertEqual(
            self.outputs["final_report_path"],
            ROOT / "outputs/33_final_evaluation_report/reports/final_evaluation.html",
        )

    def test_declared_inputs_exist_and_inventory_contract_passes(self) -> None:
        missing = [key for key, path in self.inputs.items() if not path.exists()]
        self.assertEqual(missing, [])
        checks = validate_inventory_contract(self.inventory, ROOT, self.inputs)
        self.assertTrue(checks["passed"].astype(bool).all(), checks.loc[~checks["passed"]])

    def test_table_headers_and_inventory_rows_match_contracts(self) -> None:
        inventory_lookup = self.inventory.set_index("relative_path")
        for key, contract in self.settings["input_table_contracts"].items():
            path = self.inputs[key]
            header = pd.read_csv(path, nrows=0)
            checks = validate_loaded_input_table(
                pd.DataFrame(columns=header.columns, index=range(int(contract["rows"]))),
                key,
                self.config,
            )
            self.assertTrue(checks["passed"].astype(bool).all(), f"{key}: {checks}")
            relative = path.relative_to(ROOT).as_posix()
            self.assertIn(relative, inventory_lookup.index)
            inventory_rows = int(float(inventory_lookup.loc[relative, "tabular_row_count"]))
            self.assertEqual(inventory_rows, int(contract["rows"]), key)

    def test_all_upstream_manifests_are_completed(self) -> None:
        manifests = load_upstream_manifests(self.config, ROOT)
        self.assertEqual(len(manifests), 32)
        checks = validate_upstream_completion(manifests, self.config)
        self.assertTrue(checks["passed"].astype(bool).all(), checks.loc[~checks["passed"]])

    def test_preparation_plans_match_approved_cardinalities(self) -> None:
        tables = build_thesis_table_plan(self.config)
        figures = build_figure_plan(self.config)
        sections = build_report_section_plan(self.config)
        catalog = build_evidence_catalog_plan(self.config)
        traceability = build_mock_traceability(self.config)
        self.assertEqual(len(tables), 15)
        self.assertEqual(int(tables["expected_rows"].sum()), 293)
        self.assertEqual(figures["figure_class"].value_counts().to_dict(), {"thesis": 18, "publication": 6})
        self.assertEqual(len(sections), 19)
        self.assertEqual(int(sections["claim_count"].sum()), 48)
        self.assertEqual(len(catalog), 106)
        self.assertEqual(catalog["schema_version"].unique().tolist(), [EVIDENCE_CATALOG_SCHEMA_VERSION])
        self.assertEqual(len(traceability), 125)
        self.assertEqual(tuple(traceability.columns), TRACEABILITY_COLUMNS)
        checks = validate_preparation_plans(self.config)
        self.assertTrue(checks["passed"].astype(bool).all(), checks.loc[~checks["passed"]])

    def test_evidence_catalog_retains_all_approved_roles(self) -> None:
        catalog = build_evidence_catalog_plan(self.config)
        expected_types = {
            "claim": 48,
            "table": 15,
            "thesis_figure": 18,
            "publication_figure": 6,
            "limitation": 18,
            "report": 1,
        }
        self.assertEqual(catalog["record_type"].value_counts().to_dict(), expected_types)
        self.assertEqual(catalog["catalog_id"].nunique(), len(catalog))
        self.assertEqual(set(catalog["implementation_status"]), {"preserved"})
        self.assertEqual(catalog["deviation_reason"].astype(str).str.len().sum(), 0)

    def test_selected_case_grid_policy_is_deterministic_and_complete(self) -> None:
        selected_cases = pd.read_csv(self.inputs["selected_cases_path"], keep_default_na=False)
        case_index = pd.read_csv(self.inputs["case_report_index_path"], keep_default_na=False)
        first = select_final_case_grids(selected_cases, case_index, ROOT, self.config)
        second = select_final_case_grids(selected_cases, case_index, ROOT, self.config)
        pd.testing.assert_frame_equal(first, second)
        self.assertEqual(len(first), 12)
        checks = validate_selected_case_grids(first, ROOT, self.config)
        self.assertTrue(checks["passed"].astype(bool).all(), checks.loc[~checks["passed"]])

    def test_html_renderer_preserves_mock_order_and_portability(self) -> None:
        tiny_png = (
            "data:image/png;base64,"
            + base64.b64encode(
                base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
                )
            ).decode("ascii")
        )
        sections = []
        for index, item in enumerate(self.settings["report"]["sections"]):
            body = "<p>Evidence is better for one scoped result and worse for another; some comparisons are inconclusive. This limitation requires human review.</p>"
            if index == 0:
                body += f"<p>{self.settings['report']['mandatory_statement']}</p>"
                for table_number in range(15):
                    body += (
                        f'<div data-table-id="test_table_{table_number + 1:02d}">'
                        "Test table"
                        "</div>"
                    )
                for claim_number in range(48):
                    body += (
                        f'<p data-claim-id="test_claim_{claim_number + 1:02d}">'
                        "Test evidence claim."
                        "</p>"
                    )
                for visual_number in range(64):
                    tiles = 8 if visual_number == 63 else 4
                    body += visual_html(
                        tiny_png,
                        f"Test visual {visual_number + 1}",
                        "Portable preparation-layer test visual.",
                        f"test_visual_{visual_number + 1:02d}",
                        tile_count=tiles,
                    )
            sections.append(
                {
                    "section_id": item["section_id"],
                    "title": item["title"],
                    "body_html": body,
                }
            )
        report = render_report_html(
            "Trustworthy Evaluation of AI-Assisted Painting Restoration",
            "Final controlled evaluation",
            sections,
            {"report_schema": REPORT_SCHEMA_VERSION},
        )
        checks = validate_report_html(report, self.config, enforce_density=True)
        self.assertTrue(checks["passed"].astype(bool).all(), checks.loc[~checks["passed"]])

    def test_image_encoder_and_atomic_writers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image_path = root / "image.png"
            Image.new("RGB", (32, 24), (120, 80, 40)).save(image_path)
            data_uri = image_to_data_uri(image_path, max_dimension=16)
            self.assertTrue(data_uri.startswith("data:image/jpeg;base64,"))

            text_path = atomic_write_text("Notebook 33\n", root / "nested/report.md")
            self.assertEqual(text_path.read_text(encoding="utf-8"), "Notebook 33\n")

            frame = pd.DataFrame({"value": [1, 2]})
            csv_path = atomic_write_csv(frame, root / "nested/table.csv")
            pd.testing.assert_frame_equal(pd.read_csv(csv_path), frame)
            self.assertFalse(any(path.suffix == ".tmp" for path in root.rglob("*")))

    def test_output_table_schemas_are_explicit(self) -> None:
        self.assertIn("values_json", THESIS_TABLE_COLUMNS)
        self.assertIn("source_row_ids_json", THESIS_TABLE_COLUMNS)
        self.assertEqual(len(LATEX_TABLE_COLUMNS), 12)
        self.assertEqual(self.settings["report_schema_version"], REPORT_SCHEMA_VERSION)
        self.assertEqual(
            json.loads(build_thesis_table_plan(self.config).iloc[0]["source_keys_json"]),
            ["evidence_coverage_path"],
        )


if __name__ == "__main__":
    unittest.main()
