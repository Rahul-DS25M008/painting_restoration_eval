"""Focused preparation-layer contract tests for Notebook 31."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from restoration_eval.model_report_generation import (
    REPORT_INDEX_COLUMNS,
    TRACEABILITY_COLUMNS,
    atomic_write_csv,
    atomic_write_text,
    build_applicability_matrix,
    build_mock_traceability,
    build_report_index_row,
    load_model_report_config,
    load_upstream_manifests,
    model_specs,
    render_model_report_html,
    resolve_model_report_inputs,
    select_representative_cases,
    validate_applicability_matrix,
    validate_inventory_contract,
    validate_loaded_input_table,
    validate_mock_traceability,
    validate_model_report_html,
    validate_report_index,
    validate_representative_selection,
    validate_upstream_completion,
    visual_html,
)


class ModelReportGenerationContractTests(unittest.TestCase):
    """Exercise only persisted evidence and tiny in-memory report fixtures."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.config = load_model_report_config(
            cls.root / "config/evaluation/model_report_generation.yaml"
        )
        cls.settings = cls.config["model_report_generation"]
        cls.inputs = resolve_model_report_inputs(cls.config, cls.root)
        cls.specs = model_specs(cls.config)

    def test_config_identity_structure_density_and_output_contract(self) -> None:
        self.assertEqual(self.settings["notebook_id"], "31")
        self.assertEqual(len(self.settings["models"]), 4)
        self.assertEqual(len(self.settings["report"]["required_section_ids"]), 15)
        self.assertEqual(self.settings["expected_counts"]["report_count"], 4)
        self.assertEqual(self.settings["expected_counts"]["physical_output_files"], 8)
        self.assertFalse(self.settings["evidence_policy"]["creates_new_scientific_evidence"])
        for spec in self.specs.values():
            expected_images = (
                int(spec["representative_panel_count"])
                + int(spec["analytical_view_count"])
                + int(spec["visual_atlas_count"])
            )
            self.assertEqual(int(spec["minimum_embedded_image_count"]), expected_images)

    def test_all_declared_inputs_exist_and_inventory_counts_match(self) -> None:
        self.assertTrue(all(path.exists() for path in self.inputs.values()))
        inventory = pd.read_csv(self.inputs["inventory_path"], low_memory=False)
        checks = validate_inventory_contract(inventory, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_string(index=False))

    def test_every_tabular_contract_matches_loaded_headers_and_rows(self) -> None:
        for input_key in self.settings["input_table_contracts"]:
            frame = pd.read_csv(self.inputs[input_key], low_memory=False)
            checks = validate_loaded_input_table(
                frame, input_key=input_key, config=self.config
            )
            self.assertTrue(checks["passed"].all(), checks.to_string(index=False))

    def test_notebooks_09_through_30_are_completed_inputs(self) -> None:
        manifests = load_upstream_manifests(self.inputs)
        self.assertEqual(len(manifests), 22)
        checks = validate_upstream_completion(manifests, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_string(index=False))

    def test_applicability_preserves_deterministic_diffusion_and_sdxl_distinctions(self) -> None:
        matrix = build_applicability_matrix(self.config)
        self.assertEqual(len(matrix), 28)
        checks = validate_applicability_matrix(matrix, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_string(index=False))
        uncertainty = matrix.loc[
            matrix["evidence_component"].eq("repeated_seed_uncertainty")
        ].set_index("model_id")["applicability_status"].to_dict()
        self.assertEqual(uncertainty["opencv_telea"], "not_applicable_deterministic_method")
        self.assertEqual(uncertainty["lama"], "not_applicable_deterministic_method")
        self.assertEqual(uncertainty["stable_diffusion_inpainting"], "applicable_canonical_and_damage_size")
        self.assertEqual(uncertainty["sdxl_inpainting"], "not_applicable_insufficient_seed_coverage")

    def test_representative_selections_are_deterministic_and_meet_all_quotas(self) -> None:
        catalog = pd.read_csv(self.inputs["explanation_cases_path"], low_memory=False)
        for model_id, spec in self.specs.items():
            first = select_representative_cases(catalog, model_id=model_id, config=self.config)
            second = select_representative_cases(catalog, model_id=model_id, config=self.config)
            pd.testing.assert_frame_equal(first, second)
            self.assertEqual(len(first), int(spec["representative_panel_count"]))
            checks = validate_representative_selection(
                first, model_id=model_id, config=self.config
            )
            self.assertTrue(checks["passed"].all(), checks.to_string(index=False))

    def test_mock_traceability_retains_every_approved_role(self) -> None:
        sources = {
            section: f"canonical:{section}"
            for section in self.settings["report"]["required_section_ids"]
        }
        traceability = build_mock_traceability(sources, config=self.config)
        self.assertEqual(list(traceability.columns), list(TRACEABILITY_COLUMNS))
        self.assertEqual(len(traceability), self.settings["expected_counts"]["traceability_rows"])
        checks = validate_mock_traceability(traceability, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_string(index=False))

    def _report_fixture(self, model_id: str) -> str:
        spec = self.specs[model_id]
        tiny_uri = "data:image/png;base64,AA=="
        visuals = []
        total_images = int(spec["minimum_embedded_image_count"])
        remaining_tiles = int(spec["minimum_embedded_tile_count"])
        role_counts = {
            "analytical_view": int(spec["analytical_view_count"]),
            "representative_panel": int(spec["representative_panel_count"]),
            "visual_atlas": int(spec["visual_atlas_count"]),
        }
        visual_index = 0
        for role, count in role_counts.items():
            for _ in range(count):
                visual_index += 1
                remaining_images = total_images - visual_index
                tile_count = max(1, remaining_tiles - remaining_images)
                remaining_tiles -= tile_count
                visuals.append(visual_html(
                    tiny_uri,
                    alt=f"Validated {role} {visual_index}",
                    caption=f"Canonical evidence view {visual_index}.",
                    report_role=role,
                    tile_count=tile_count,
                ))
        sections = {
            section: "<p>Validated canonical evidence and a scoped conclusion.</p>"
            for section in self.settings["report"]["required_section_ids"]
        }
        sections["executive-summary"] = (
            "<p>RQ1, RQ2, and RQ3 are addressed with validated evidence. "
            "One scoped result is better, another is worse, and an unresolved "
            "comparison remains inconclusive. A nearby limitation is retained.</p>"
            "<p>Visual plausibility is not equivalent to historical or restoration trustworthiness.</p>"
        )
        sections["representative-successes-failures"] += "".join(visuals)
        return render_model_report_html(
            {"model_id": model_id}, sections, config=self.config
        )

    def test_all_four_rendered_report_contracts_pass(self) -> None:
        for model_id in self.specs:
            rendered = self._report_fixture(model_id)
            checks = validate_model_report_html(
                rendered, model_id=model_id, config=self.config
            )
            blocking = checks.loc[checks["severity"].eq("blocking")]
            self.assertTrue(blocking["passed"].all(), checks.to_string(index=False))
            self.assertNotIn('src="outputs/', rendered)

    def test_report_index_contract_and_atomic_writers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            report_root = root / "outputs/31_model_report_generation/reports"
            rows = []
            for model_id, spec in self.specs.items():
                report_path = report_root / str(spec["report_filename"])
                atomic_write_text(self._report_fixture(model_id), report_path)
                rows.append(build_report_index_row(
                    report_path,
                    project_root=root,
                    model_id=model_id,
                    representative_candidate_ids=[f"candidate_{model_id}"],
                    source_artifact_paths=["outputs/30_model_cards_compute_and_scalability/data/model_cards.csv"],
                    source_checksums={"model_cards": "a" * 64},
                    upstream_run_ids={"30": "run_test"},
                    generated_at_utc="2026-09-02T00:00:00Z",
                    config=self.config,
                ))
            index = pd.DataFrame(rows, columns=REPORT_INDEX_COLUMNS)
            checks = validate_report_index(index, config=self.config)
            self.assertTrue(checks["passed"].all(), checks.to_string(index=False))
            index_path = root / "report_index.csv"
            atomic_write_csv(index, index_path)
            self.assertTrue(index_path.exists())
            self.assertFalse(any(root.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
