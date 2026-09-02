"""Contract tests for Notebook 30 model-card and compute preparation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from restoration_eval.model_cards_compute import (
    COMPUTE_COLUMNS,
    MODEL_CARD_COLUMNS,
    atomic_write_csv,
    atomic_write_text,
    build_model_cards,
    build_scaling_projections,
    coerce_compute_scalability,
    collect_observed_compute,
    load_model_cards_compute_config,
    prepare_quality_evidence,
    render_model_card_markdown,
    resolve_model_cards_compute_inputs,
    summarize_output_storage,
    validate_compute_scalability,
    validate_model_card_markdown,
    validate_model_cards,
    validate_upstream_completion,
)


class ModelCardsComputeContractTests(unittest.TestCase):
    """Use only persisted inputs; no notebook execution or model inference."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.config = load_model_cards_compute_config(
            cls.root / "config/evaluation/model_cards_compute.yaml"
        )
        cls.settings = cls.config["model_cards_compute"]
        cls.inputs = resolve_model_cards_compute_inputs(cls.config, cls.root)

        cls.candidates = {
            "opencv_telea": pd.read_csv(cls.inputs["telea_candidates_path"], low_memory=False),
            "lama": pd.read_csv(cls.inputs["lama_candidates_path"], low_memory=False),
            "stable_diffusion_inpainting": pd.read_csv(
                cls.inputs["stable_diffusion_candidates_path"], low_memory=False
            ),
            "sdxl_inpainting": pd.read_csv(cls.inputs["sdxl_candidates_path"], low_memory=False),
        }
        cls.runtimes = {
            "opencv_telea": pd.read_csv(cls.inputs["telea_runtime_path"]),
            "lama": pd.read_csv(cls.inputs["lama_runtime_path"]),
            "stable_diffusion_inpainting": pd.read_csv(
                cls.inputs["stable_diffusion_runtime_path"]
            ),
            "sdxl_inpainting": pd.read_csv(cls.inputs["sdxl_runtime_path"]),
        }
        cls.manifests = {
            f"{number:02d}": json.loads(
                cls.inputs[f"manifest_{number:02d}_path"].read_text(encoding="utf-8-sig")
            )
            for number in range(9, 30)
        }
        cls.inventory = pd.read_csv(cls.inputs["inventory_path"], low_memory=False)
        cls.storage = summarize_output_storage(cls.inventory, config=cls.config)
        cls.cards = build_model_cards(
            cls.candidates,
            cls.runtimes,
            cls.manifests,
            cls.storage,
            config=cls.config,
        )
        cls.observed = collect_observed_compute(
            cls.runtimes, cls.cards, config=cls.config
        )
        cls.projections = build_scaling_projections(
            cls.candidates, cls.cards, cls.storage, config=cls.config
        )
        cls.compute = coerce_compute_scalability(cls.observed, cls.projections)
        cls.quality_values, cls.quality_wins = prepare_quality_evidence(
            pd.read_csv(cls.inputs["model_comparison_path"], low_memory=False),
            pd.read_csv(cls.inputs["metric_disagreement_path"], low_memory=False),
            config=cls.config,
        )

    def test_config_identity_and_arithmetic(self) -> None:
        expected = self.settings["expected_counts"]
        self.assertEqual(self.settings["notebook_id"], "30")
        self.assertEqual(expected["model_card_rows"], 4)
        self.assertEqual(expected["observed_compute_rows"], 27)
        self.assertEqual(expected["projection_rows"], 8)
        self.assertEqual(expected["compute_rows"], 35)
        self.assertEqual(len(self.settings["report"]["required_section_ids"]), 13)

    def test_declared_inputs_and_upstream_completion(self) -> None:
        self.assertTrue(all(path.exists() for path in self.inputs.values()))
        checks = validate_upstream_completion(self.manifests)
        self.assertEqual(len(checks), 21)
        self.assertTrue(checks["passed"].all(), checks.to_string(index=False))

    def test_storage_summary_has_all_models_and_no_inventory_errors(self) -> None:
        self.assertEqual(set(self.storage["model_id"]), {
            "opencv_telea", "lama", "stable_diffusion_inpainting", "sdxl_inpainting"
        })
        self.assertTrue(self.storage["output_file_count"].gt(0).all())
        self.assertTrue(self.storage["output_storage_bytes"].gt(0).all())
        self.assertTrue(self.storage["read_error_count"].eq(0).all())

    def test_model_cards_match_actual_candidate_counts(self) -> None:
        expected_counts = {
            "opencv_telea": 410,
            "lama": 410,
            "stable_diffusion_inpainting": 1330,
            "sdxl_inpainting": 10,
        }
        self.assertEqual(list(self.cards.columns), list(MODEL_CARD_COLUMNS))
        self.assertEqual(
            self.cards.set_index("model_id")["completed_count"].astype(int).to_dict(),
            expected_counts,
        )
        checks = validate_model_cards(self.cards, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_string(index=False))

    def test_compute_table_retains_observed_and_projected_distinction(self) -> None:
        self.assertEqual(list(self.compute.columns), list(COMPUTE_COLUMNS))
        self.assertEqual(len(self.observed), 27)
        self.assertEqual(len(self.projections), 8)
        self.assertEqual(len(self.compute), 35)
        checks = validate_compute_scalability(self.compute, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_string(index=False))
        sdxl_current = self.projections.loc[
            self.projections["model_id"].eq("sdxl_inpainting")
            & self.projections["scenario_id"].eq("projected_300_current_design_mix")
        ].iloc[0]
        self.assertEqual(sdxl_current["status"], "not_applicable")
        self.assertTrue(pd.isna(sdxl_current["runtime_central_seconds"]))
        canonical = self.projections.loc[
            self.projections["scenario_id"].eq("projected_300_canonical_primary")
        ]
        self.assertTrue(canonical["case_count"].eq(1500).all())
        self.assertTrue(canonical["candidate_multiplier"].eq(1.0).all())
        current_sd = self.projections.loc[
            self.projections["model_id"].eq("stable_diffusion_inpainting")
            & self.projections["scenario_id"].eq("projected_300_current_design_mix")
        ].iloc[0]
        self.assertEqual(int(current_sd["case_count"]), 2460)
        self.assertEqual(int(current_sd["candidate_count"]), 7980)
        self.assertAlmostEqual(float(current_sd["candidate_multiplier"]), 1330 / 410)
        applicable = self.projections.loc[self.projections["status"].eq("ok")]
        self.assertTrue(
            (applicable["runtime_lower_seconds"] <= applicable["runtime_central_seconds"]).all()
        )
        self.assertTrue(
            (applicable["runtime_central_seconds"] <= applicable["runtime_upper_seconds"]).all()
        )

    def test_quality_evidence_is_complete_and_not_a_combined_score(self) -> None:
        self.assertEqual(len(self.quality_values), 77)
        self.assertEqual(len(self.quality_wins), 7)
        core = self.quality_wins.loc[
            self.quality_wins["population_id"].eq("core_three_model")
        ].set_index("model_id")["anchor_win_count"].astype(int).to_dict()
        self.assertEqual(core, {
            "opencv_telea": 1,
            "lama": 10,
            "stable_diffusion_inpainting": 0,
        })
        self.assertTrue(
            self.quality_wins["interpretation"].str.contains("not_combined_quality_score").all()
        )

    def test_all_four_markdown_cards_follow_locked_structure(self) -> None:
        for model_id in self.cards["model_id"]:
            model_row = self.cards.loc[self.cards["model_id"].eq(model_id)].iloc[0].to_dict()
            rendered = render_model_card_markdown(
                model_row,
                self.compute,
                self.quality_values,
                self.quality_wins,
                config=self.config,
            )
            checks = validate_model_card_markdown(
                rendered, model_id=model_id, config=self.config
            )
            self.assertTrue(checks["passed"].all(), checks.to_string(index=False))
            self.assertNotIn("data:image", rendered)
            self.assertEqual(rendered.count("| classical_masked_mae |"), 1)
            self.assertEqual(rendered.count("| structural_affinity_correlation |"), 1)
            self.assertIn("Training-data transparency status", rendered)
            self.assertIn("Recorded peak GPU allocation", rendered)

    def test_atomic_writers_leave_no_temporary_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            csv_path = root / "table.csv"
            text_path = root / "card.md"
            atomic_write_csv(self.cards.head(1), csv_path)
            atomic_write_text("# Card\n", text_path)
            self.assertTrue(csv_path.exists())
            self.assertTrue(text_path.exists())
            self.assertFalse(any(root.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
