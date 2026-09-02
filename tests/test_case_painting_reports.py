"""Focused preparation-layer tests for Notebook 32."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from restoration_eval.case_painting_reports import (  # noqa: E402
    CASE_REPORT_INDEX_COLUMNS,
    CASE_REPORT_INDEX_SCHEMA_VERSION,
    PAINTING_REPORT_INDEX_COLUMNS,
    PAINTING_REPORT_INDEX_SCHEMA_VERSION,
    TRACEABILITY_COLUMNS,
    atomic_write_csv,
    atomic_write_text,
    build_mock_traceability,
    build_painting_summary,
    build_uncertainty_case_scores,
    load_case_painting_report_config,
    load_upstream_manifests,
    render_report_html,
    resolve_case_painting_report_inputs,
    select_report_cases,
    summarize_case_catalog,
    validate_case_population,
    validate_inventory_contract,
    validate_loaded_input_table,
    validate_mock_traceability,
    validate_painting_summary,
    validate_report_html,
    validate_report_indexes,
    validate_selected_cases,
    validate_upstream_completion,
    visual_html,
)


class CasePaintingReportPreparationTests(unittest.TestCase):
    """Validate the approved Notebook 32 preparation contract."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = ROOT
        cls.config = load_case_painting_report_config(
            ROOT / "config/evaluation/case_and_painting_reports.yaml"
        )
        cls.settings = cls.config["case_and_painting_reports"]
        cls.inputs = resolve_case_painting_report_inputs(cls.config, ROOT)
        cls.catalog = pd.read_csv(
            cls.inputs["explanation_cases_path"], low_memory=False
        )
        cls.case_summary = summarize_case_catalog(cls.catalog)
        cls.canonical_uncertainty = pd.read_csv(
            cls.inputs["canonical_uncertainty_path"], low_memory=False
        )
        cls.damage_size_uncertainty = pd.read_csv(
            cls.inputs["damage_size_uncertainty_path"], low_memory=False
        )
        cls.uncertainty_scores = build_uncertainty_case_scores(
            cls.canonical_uncertainty,
            cls.damage_size_uncertainty,
            config=cls.config,
        )

    def test_config_identity_population_and_output_arithmetic(self) -> None:
        expected = self.settings["expected_counts"]
        self.assertEqual(self.settings["notebook_id"], "32")
        self.assertEqual(expected["approved_candidate_count"], 1785)
        self.assertEqual(expected["case_count"], 410)
        self.assertEqual(expected["painting_count"], 50)
        self.assertEqual(expected["selected_case_count"], 30)
        self.assertEqual(expected["report_count"], 81)
        self.assertEqual(expected["physical_output_files"], 117)
        self.assertEqual(expected["traceability_rows"], 67)
        self.assertFalse(
            self.settings["evidence_policy"]["creates_new_scientific_evidence"]
        )

    def test_declared_inputs_exist_and_inventory_contract_passes(self) -> None:
        self.assertTrue(all(path.exists() for path in self.inputs.values()))
        inventory = pd.read_csv(self.inputs["inventory_path"], low_memory=False)
        checks = validate_inventory_contract(inventory, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_string(index=False))

    def test_table_headers_and_inventory_rows_match_contracts(self) -> None:
        inventory = pd.read_csv(self.inputs["inventory_path"], low_memory=False)
        inventory_rows = inventory.set_index("relative_path")[
            "tabular_row_count"
        ].to_dict()
        for input_key, contract in self.settings["input_table_contracts"].items():
            header = pd.read_csv(self.inputs[input_key], nrows=0)
            missing = sorted(
                set(contract["required_columns"]) - set(header.columns)
            )
            self.assertFalse(missing, f"{input_key}: {missing}")
            relative = self.settings["inputs"][input_key]
            self.assertEqual(int(float(inventory_rows[relative])), int(contract["rows"]))

    def test_upstream_manifest_completion_contract(self) -> None:
        manifests = load_upstream_manifests(self.inputs)
        self.assertEqual(len(manifests), 24)
        checks = validate_upstream_completion(manifests, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_string(index=False))

    def test_case_population_and_uncertainty_sort_key(self) -> None:
        checks = validate_case_population(
            self.case_summary, self.catalog, config=self.config
        )
        self.assertTrue(checks["passed"].all(), checks.to_string(index=False))
        self.assertEqual(len(self.case_summary), 410)
        self.assertEqual(int(self.case_summary["candidate_count"].sum()), 1785)
        self.assertEqual(
            len(self.uncertainty_scores),
            self.settings["expected_counts"]["uncertainty_case_count"],
        )
        self.assertTrue(self.uncertainty_scores["uncertainty_score"].notna().all())

    def test_selected_case_policy_is_deterministic_and_complete(self) -> None:
        first = select_report_cases(
            self.case_summary, self.uncertainty_scores, config=self.config
        )
        second = select_report_cases(
            self.case_summary, self.uncertainty_scores, config=self.config
        )
        pd.testing.assert_frame_equal(first, second)
        checks = validate_selected_cases(first, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_string(index=False))
        self.assertEqual(first["case_id"].nunique(), 30)

    def test_all_fifty_paintings_and_all_cases_are_retained(self) -> None:
        artworks = pd.read_csv(self.inputs["artworks_path"], low_memory=False)
        painting_summary = build_painting_summary(
            self.case_summary, artworks, config=self.config
        )
        checks = validate_painting_summary(painting_summary, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_string(index=False))
        self.assertEqual(len(painting_summary), 50)
        self.assertEqual(int(painting_summary["case_count"].sum()), 410)
        self.assertEqual(
            sorted(
                painting_summary.loc[
                    painting_summary["is_extension_painting"], "painting_id"
                ]
            ),
            ["p001", "p018", "p026", "p039", "p043"],
        )

    def test_mock_traceability_retains_all_approved_roles(self) -> None:
        sources = {
            report_kind: {
                section: f"canonical:{report_kind}:{section}"
                for section in sections
            }
            for report_kind, sections in self.settings["mock_traceability"].items()
        }
        traceability = build_mock_traceability(sources, config=self.config)
        self.assertEqual(list(traceability.columns), list(TRACEABILITY_COLUMNS))
        self.assertEqual(len(traceability), 67)
        checks = validate_mock_traceability(traceability, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_string(index=False))

    def _fixture_sections(self, report_kind: str) -> dict[str, str]:
        section_key = {
            "case": "case_sections",
            "painting": "painting_sections",
            "collection": "collection_sections",
        }[report_kind]
        sections = {
            section: "<p>Validated canonical evidence with a scoped conclusion.</p>"
            for section in self.settings["reports"][section_key]
        }
        if report_kind in {"case", "painting"}:
            first = self.settings["reports"][section_key][0]
            sections[first] += (
                "<p>A measured result is better, another is worse, and an "
                "unresolved comparison is inconclusive. A nearby limitation "
                "and human review action are retained.</p>"
                "<p>Visual plausibility is not equivalent to historical or "
                "restoration trustworthiness.</p>"
            )
        return sections

    def _add_visuals(
        self, sections: dict[str, str], *, image_count: int, tile_count: int
    ) -> None:
        tiny_uri = "data:image/png;base64,AA=="
        target = next(iter(sections))
        remaining_tiles = tile_count
        visuals = []
        for index in range(1, image_count + 1):
            remaining_images = image_count - index
            current_tiles = max(1, remaining_tiles - remaining_images)
            remaining_tiles -= current_tiles
            visuals.append(visual_html(
                tiny_uri,
                alt=f"Validated report visual {index}",
                caption=f"Canonical evidence view {index}.",
                report_role="fixture",
                tile_count=current_tiles,
            ))
        sections[target] += "".join(visuals)

    def test_case_painting_and_collection_html_contracts(self) -> None:
        fixtures = (
            ("case", False, 7, 20),
            ("painting", False, 4, 20),
            ("painting", True, 6, 35),
            ("collection", False, 2, 2),
        )
        for report_kind, extension, images, tiles in fixtures:
            sections = self._fixture_sections(report_kind)
            self._add_visuals(sections, image_count=images, tile_count=tiles)
            rendered = render_report_html(
                title=f"Fixture {report_kind}",
                subtitle="Validated preparation fixture",
                report_kind=report_kind,
                sections=sections,
                config=self.config,
            )
            checks = validate_report_html(
                rendered,
                report_kind=report_kind,
                config=self.config,
                is_extension_painting=extension,
            )
            self.assertTrue(checks["passed"].all(), checks.to_string(index=False))
            self.assertNotIn('src="outputs/', rendered)

    def test_report_index_contract_and_atomic_writers(self) -> None:
        expected = self.settings["expected_counts"]
        case_rows = []
        for index in range(int(expected["case_report_index_rows"])):
            case_rows.append({
                column: (
                    f"case_{index:03d}" if column == "case_id"
                    else f"report_{index:03d}" if column == "report_id"
                    else True if column == "self_contained"
                    else CASE_REPORT_INDEX_SCHEMA_VERSION
                    if column == "schema_version" else "ok"
                    if column == "status" else index + 1
                    if column == "selection_order" else ""
                )
                for column in CASE_REPORT_INDEX_COLUMNS
            })
        painting_rows = []
        for index in range(int(expected["painting_report_index_rows"])):
            painting_rows.append({
                column: (
                    f"p{index + 1:03d}" if column == "painting_id"
                    else f"painting_report_{index:03d}" if column == "report_id"
                    else True if column == "self_contained"
                    else PAINTING_REPORT_INDEX_SCHEMA_VERSION
                    if column == "schema_version" else "ok"
                    if column == "status" else ""
                )
                for column in PAINTING_REPORT_INDEX_COLUMNS
            })
        case_index = pd.DataFrame(case_rows, columns=CASE_REPORT_INDEX_COLUMNS)
        painting_index = pd.DataFrame(
            painting_rows, columns=PAINTING_REPORT_INDEX_COLUMNS
        )
        checks = validate_report_indexes(
            case_index, painting_index, config=self.config
        )
        self.assertTrue(checks["passed"].all(), checks.to_string(index=False))

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            text_path = atomic_write_text("validated", root / "report.html")
            csv_path = atomic_write_csv(case_index, root / "case_index.csv")
            self.assertEqual(text_path.read_text(encoding="utf-8"), "validated")
            self.assertEqual(len(pd.read_csv(csv_path)), 30)
            self.assertFalse(any(root.rglob("*.tmp")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
