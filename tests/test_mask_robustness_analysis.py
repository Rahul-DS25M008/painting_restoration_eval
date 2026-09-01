from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from restoration_eval.mask_robustness_analysis import (
    ANALYSIS_COLUMNS,
    ANALYSIS_SCHEMA_VERSION,
    benjamini_hochberg,
    build_runtime_evidence,
    compute_group_dispersion,
    compute_variant_family_balanced_ranks,
    dispersion_statistics,
    empty_analysis_frame,
    exact_sign_flip_test,
    exhaustive_bootstrap_interval,
    load_mask_robustness_analysis_config,
    matched_rank_biserial,
    normalise_quality_evidence,
    resolve_analysis_inputs,
    select_mask_robustness_population,
    select_quality_anchor_values,
    validate_mask_robustness_analysis,
    validate_mask_robustness_report_html,
    validate_upstream_run_manifests,
    within_group_centered_spearman,
)
from restoration_eval.paths import find_project_root


PROJECT_ROOT = find_project_root(Path(__file__))
CONFIG_PATH = PROJECT_ROOT / "config" / "evaluation" / "mask_robustness_analysis.yaml"


class MaskRobustnessAnalysisTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_mask_robustness_analysis_config(CONFIG_PATH)
        cls.inputs = resolve_analysis_inputs(cls.config, PROJECT_ROOT)
        cls.cases = pd.read_csv(cls.inputs["mask_robustness_cases_path"])
        cls.artworks = pd.read_csv(cls.inputs["artworks_path"])
        cls.opencv = pd.read_csv(cls.inputs["opencv_candidates_path"])
        cls.lama = pd.read_csv(cls.inputs["lama_candidates_path"])
        cls.stable_diffusion = pd.read_csv(cls.inputs["stable_diffusion_candidates_path"])
        cls.selected = select_mask_robustness_population(
            cls.cases,
            cls.artworks,
            cls.opencv,
            cls.lama,
            cls.stable_diffusion,
            config=cls.config,
        )

    def test_config_inputs_and_upstream_completion_gates(self) -> None:
        settings = self.config["mask_robustness_analysis"]
        self.assertEqual(settings["notebook_id"], "24")
        self.assertTrue(settings["report"]["approved_mock_structure_locked"])
        self.assertTrue(settings["report"]["require_evidence_to_assertion_pairs"])
        self.assertFalse(settings["statistics"]["combined_quality_score_retained"])
        self.assertFalse(settings["statistics"]["use_uncertainty_terminology"])
        self.assertEqual(len(self.inputs), len(settings["inputs"]))
        notebook_by_key = {
            "06": "mask_robustness_run_manifest_path",
            "08": "contracts_run_manifest_path",
            "09": "opencv_run_manifest_path",
            "10": "lama_run_manifest_path",
            "11": "stable_diffusion_run_manifest_path",
            "13": "classical_run_manifest_path",
            "14": "lpips_run_manifest_path",
            "15": "feature_run_manifest_path",
            "16": "spatial_run_manifest_path",
            "17": "local_run_manifest_path",
            "20": "semantic_run_manifest_path",
            "21": "comparison_run_manifest_path",
        }
        manifests = {
            notebook_id: json.loads(self.inputs[key].read_text(encoding="utf-8"))
            for notebook_id, key in notebook_by_key.items()
        }
        checks = validate_upstream_run_manifests(manifests)
        self.assertEqual(len(checks), 12)
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))

    def test_primary_population_and_fixed_family_area_mapping_are_exact(self) -> None:
        self.assertEqual(len(self.selected), 225)
        self.assertEqual(self.selected["case_id"].nunique(), 75)
        self.assertEqual(self.selected["robustness_group_id"].nunique(), 15)
        self.assertEqual(self.selected["painting_id"].nunique(), 5)
        self.assertEqual(
            self.selected.groupby("model_id").size().to_dict(),
            {"lama": 75, "opencv_telea": 75, "stable_diffusion_inpainting": 75},
        )
        self.assertFalse(self.selected.duplicated(["model_id", "case_id"]).any())
        for model_id, group in self.selected.groupby("model_id"):
            self.assertTrue(group.groupby("robustness_group_id").size().eq(5).all(), model_id)
        observed = (
            self.selected[["mask_family", "target_damage_fraction"]]
            .drop_duplicates()
            .set_index("mask_family")["target_damage_fraction"]
            .to_dict()
        )
        self.assertEqual(observed, {"loss_large": 0.125, "loss_small": 0.045, "scratch_thin": 0.02})
        sd = self.selected.loc[self.selected["model_id"].eq("stable_diffusion_inpainting")]
        self.assertTrue(sd["execution_role"].eq("primary").all())
        self.assertTrue(sd["prompt_variant_id"].eq("p00_generic").all())
        self.assertTrue(pd.to_numeric(sd["seed"]).eq(2026).all())
        self.assertTrue(self.selected["restored_path"].str.startswith("outputs/").all())

    def test_all_quality_sources_and_runtime_cover_the_population(self) -> None:
        tables = {
            "classical": pd.read_csv(self.inputs["classical_metrics_path"]),
            "perceptual": pd.read_csv(self.inputs["lpips_metrics_path"]),
            "feature": pd.read_csv(self.inputs["feature_metrics_path"]),
            "spatial": pd.read_csv(self.inputs["spatial_metrics_path"]),
            "local_consistency": pd.read_csv(self.inputs["local_metrics_path"], low_memory=False),
            "semantic_structural": pd.read_csv(self.inputs["semantic_metrics_path"], low_memory=False),
        }
        normalized = normalise_quality_evidence(tables, self.selected, config=self.config)
        self.assertEqual(len(normalized), 72225)
        self.assertEqual(normalized["candidate_id"].nunique(), 225)
        self.assertEqual(normalized["case_id"].nunique(), 75)
        anchors = select_quality_anchor_values(normalized, config=self.config)
        self.assertEqual(len(anchors), 2475)
        self.assertEqual(anchors["anchor_id"].nunique(), 11)
        self.assertTrue(anchors.groupby("candidate_id").size().eq(11).all())
        runtime = build_runtime_evidence(self.selected, config=self.config)
        self.assertEqual(len(runtime), 225)
        self.assertFalse(runtime["quality_ranking_eligible"].any())

    def test_dispersion_and_family_balanced_rank_arithmetic(self) -> None:
        self.assertEqual(
            dispersion_statistics([1.0, 2.0, 3.0, 4.0, 5.0]),
            {
                "standard_deviation": np.std([1, 2, 3, 4, 5], ddof=1),
                "median_absolute_deviation": 1.0,
                "range": 4.0,
            },
        )
        rows = []
        for variant_index in range(5):
            for model_index, model_id in enumerate(("opencv_telea", "lama", "stable_diffusion_inpainting")):
                for anchor_id, family in (("a1", "pixel"), ("a2", "feature")):
                    rows.append(
                        {
                            "case_id": f"case_{variant_index}",
                            "robustness_group_id": "group_1",
                            "variant_id": f"variant_{variant_index}",
                            "painting_id": "p001",
                            "mask_family": "scratch_thin",
                            "model_id": model_id,
                            "evidence_family": family,
                            "anchor_id": anchor_id,
                            "comparison_direction": "lower_is_better",
                            "comparison_value": float(model_index + variant_index / 10),
                        }
                    )
        synthetic = pd.DataFrame(rows)
        dispersion = compute_group_dispersion(synthetic)
        self.assertEqual(len(dispersion), 18)
        self.assertTrue(dispersion["variant_count"].eq(5).all())
        ranks = compute_variant_family_balanced_ranks(synthetic)
        self.assertEqual(len(ranks), 15)
        self.assertTrue(ranks.groupby("case_id").size().eq(3).all())
        self.assertTrue(ranks.loc[ranks["model_id"].eq("opencv_telea"), "overall_rank"].eq(1).all())

    def test_exact_statistics_morphology_and_schema_validation(self) -> None:
        bootstrap = exhaustive_bootstrap_interval([1, 2, 3, 4, 5])
        self.assertEqual(bootstrap["resamples"], 3125)
        self.assertEqual(exact_sign_flip_test([1, 2, 3, 4, 5])["assignments"], 32)
        self.assertAlmostEqual(matched_rank_biserial([1, 2, 3, 4, 5]), 1.0)
        np.testing.assert_allclose(benjamini_hochberg([0.01, 0.02, 0.20]), [0.03, 0.03, 0.20])

        morphology = pd.DataFrame(
            [
                {
                    "robustness_group_id": f"{painting}_{family}",
                    "painting_id": painting,
                    "compactness": variant + family_index * 0.1,
                    "outcome": 2.0 * variant + painting_index * 0.05,
                }
                for painting_index, painting in enumerate(["p1", "p2", "p3", "p4", "p5"])
                for family_index, family in enumerate(["thin", "small", "large"])
                for variant in range(5)
            ]
        )
        association = within_group_centered_spearman(
            morphology, morphology_column="compactness", outcome_column="outcome"
        )
        self.assertEqual(association["painting_count"], 5)
        self.assertEqual(association["observation_count"], 75)
        self.assertEqual(association["bootstrap_resamples"], 3125)
        self.assertGreater(association["rho"], 0.98)

        record = {column: "" for column in ANALYSIS_COLUMNS}
        record.update(
            {
                "analysis_row_id": "mra_test",
                "analysis_kind": "model_dispersion_summary",
                "schema_version": ANALYSIS_SCHEMA_VERSION,
                "status": "ok",
                "p_value": 0.0625,
                "q_value": 0.125,
            }
        )
        self.assertEqual(list(empty_analysis_frame().columns), list(ANALYSIS_COLUMNS))
        frame = pd.DataFrame([record], columns=ANALYSIS_COLUMNS)
        validation = validate_mask_robustness_analysis(frame, config=self.config)
        self.assertTrue(validation["passed"], validation)

    def test_report_validator_enforces_approved_mock_sections(self) -> None:
        report = self.config["mask_robustness_analysis"]["report"]
        images = "".join('<img alt="mock" src="data:image/png;base64,AA==">' for _ in range(18))
        sections = "".join(f'<section id="{section}"><h2>{section}</h2></section>' for section in report["required_section_ids"])
        html = f"<html><body><h1>RQ1 RQ2 RQ3</h1><p>Conclusion and limitation.</p>{sections}{images}</body></html>"
        checks = validate_mask_robustness_report_html(html, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))


if __name__ == "__main__":
    unittest.main()
