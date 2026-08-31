from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from restoration_eval.damage_size_analysis import (
    ANALYSIS_COLUMNS,
    ANALYSIS_SCHEMA_VERSION,
    benjamini_hochberg,
    build_runtime_evidence,
    compute_adjacent_changes,
    compute_painting_slopes,
    exact_sign_flip_test,
    exhaustive_bootstrap_interval,
    family_balanced_ranks,
    load_damage_size_analysis_config,
    matched_rank_biserial,
    normalise_quality_evidence,
    normalise_uncertainty_evidence,
    resolve_analysis_inputs,
    select_damage_size_population,
    size_and_painting_adjusted_spearman,
    summarise_painting_slopes,
    theil_sen_slope,
    validate_damage_size_analysis,
    validate_damage_size_report_html,
    validate_upstream_run_manifests,
)
from restoration_eval.paths import find_project_root


PROJECT_ROOT = find_project_root(Path(__file__))
CONFIG_PATH = PROJECT_ROOT / "config" / "evaluation" / "damage_size_analysis.yaml"


class DamageSizeAnalysisTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_damage_size_analysis_config(CONFIG_PATH)
        cls.inputs = resolve_analysis_inputs(cls.config, PROJECT_ROOT)
        cls.cases = pd.read_csv(cls.inputs["damage_size_cases_path"])
        cls.artworks = pd.read_csv(cls.inputs["artworks_path"])
        cls.opencv = pd.read_csv(cls.inputs["opencv_candidates_path"])
        cls.lama = pd.read_csv(cls.inputs["lama_candidates_path"])
        cls.stable_diffusion = pd.read_csv(cls.inputs["stable_diffusion_candidates_path"])
        cls.selected = select_damage_size_population(
            cls.cases,
            cls.artworks,
            cls.opencv,
            cls.lama,
            cls.stable_diffusion,
            config=cls.config,
        )

    def test_config_inputs_and_upstream_completion_gates(self) -> None:
        settings = self.config["damage_size_analysis"]
        self.assertEqual(settings["notebook_id"], "23")
        self.assertTrue(settings["report"]["plain_language_first"])
        self.assertFalse(settings["uncertainty"]["combined_index_retained"])
        self.assertFalse(settings["statistics"]["combined_quality_score_retained"])
        self.assertEqual(len(self.inputs), len(settings["inputs"]))
        manifests = {}
        notebook_by_key = {
            "05": "damage_size_run_manifest_path",
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
            "22": "uncertainty_run_manifest_path",
        }
        for notebook_id, key in notebook_by_key.items():
            manifests[notebook_id] = json.loads(self.inputs[key].read_text(encoding="utf-8"))
        checks = validate_upstream_run_manifests(manifests)
        self.assertEqual(len(checks), 13)
        self.assertTrue(checks["passed"].all())

    def test_primary_population_is_exact_and_metric_independent(self) -> None:
        self.assertEqual(len(self.selected), 105)
        self.assertEqual(self.selected["case_id"].nunique(), 35)
        self.assertEqual(self.selected["painting_id"].nunique(), 5)
        self.assertEqual(self.selected["target_damage_fraction"].nunique(), 7)
        self.assertEqual(
            self.selected.groupby("model_id").size().to_dict(),
            {"lama": 35, "opencv_telea": 35, "stable_diffusion_inpainting": 35},
        )
        self.assertFalse(self.selected.duplicated(["model_id", "case_id"]).any())
        sd = self.selected.loc[self.selected["model_id"].eq("stable_diffusion_inpainting")]
        self.assertTrue(sd["execution_role"].eq("primary").all())
        self.assertTrue(sd["prompt_variant_id"].eq("p00_generic").all())
        self.assertTrue(pd.to_numeric(sd["seed"]).eq(2026).all())
        self.assertTrue(self.selected["restored_path"].str.startswith("outputs/").all())

    def test_all_quality_sources_normalize_to_the_approved_population(self) -> None:
        tables = {
            "classical": pd.read_csv(self.inputs["classical_metrics_path"]),
            "perceptual": pd.read_csv(self.inputs["lpips_metrics_path"]),
            "feature": pd.read_csv(self.inputs["feature_metrics_path"]),
            "spatial": pd.read_csv(self.inputs["spatial_metrics_path"]),
            "local_consistency": pd.read_csv(self.inputs["local_metrics_path"], low_memory=False),
            "semantic_structural": pd.read_csv(self.inputs["semantic_metrics_path"], low_memory=False),
        }
        normalized = normalise_quality_evidence(tables, self.selected, config=self.config)
        self.assertEqual(len(normalized), 33705)
        self.assertEqual(normalized["candidate_id"].nunique(), 105)
        self.assertEqual(normalized["case_id"].nunique(), 35)
        self.assertEqual(normalized["anchor_id"].replace("", np.nan).dropna().nunique(), 11)
        self.assertFalse(normalized.duplicated(["source_notebook_id", "source_metric_row_id"]).any())
        runtime = build_runtime_evidence(self.selected, config=self.config)
        self.assertEqual(len(runtime), 105)
        self.assertFalse(runtime["quality_ranking_eligible"].any())

    def test_uncertainty_is_four_seed_group_level_evidence(self) -> None:
        source = pd.read_csv(self.inputs["uncertainty_metrics_path"])
        normalized = normalise_uncertainty_evidence(source, config=self.config)
        self.assertEqual(len(normalized), 1050)
        self.assertEqual(normalized["uncertainty_group_id"].nunique(), 35)
        self.assertTrue(pd.to_numeric(normalized["seed_count"]).eq(4).all())
        paired = normalized.loc[normalized["aggregation_method"].eq("median_of_six_unordered_seed_pairs")]
        self.assertTrue(pd.to_numeric(paired["pair_count"]).eq(6).all())
        self.assertEqual(normalized["component_id"].replace("", np.nan).dropna().nunique(), 5)
        self.assertTrue(normalized["comparison_direction"].eq("lower_is_better").all())

    def test_exact_small_sample_statistics_and_interval_normalization(self) -> None:
        self.assertAlmostEqual(theil_sen_slope([0.02, 0.04, 0.10], [1.04, 1.08, 1.20]), 2.0)
        bootstrap = exhaustive_bootstrap_interval([1, 2, 3, 4, 5])
        self.assertEqual(bootstrap["resamples"], 3125)
        self.assertEqual(bootstrap["estimate"], 3.0)
        sign_flip = exact_sign_flip_test([1, 2, 3, 4, 5])
        self.assertEqual(sign_flip["assignments"], 32)
        self.assertAlmostEqual(sign_flip["p_value"], 0.0625)
        self.assertAlmostEqual(matched_rank_biserial([1, 2, 3, 4, 5]), 1.0)
        np.testing.assert_allclose(benjamini_hochberg([0.01, 0.02, 0.20]), [0.03, 0.03, 0.20])

        synthetic = pd.DataFrame(
            [
                {"painting_id": painting, "target_damage_fraction": level, "comparison_value": offset + 2.0 * level}
                for offset, painting in enumerate(["p1", "p2", "p3", "p4", "p5"])
                for level in [0.02, 0.04, 0.06, 0.08, 0.10, 0.15, 0.20]
            ]
        )
        slopes = compute_painting_slopes(
            synthetic,
            exposure_column="target_damage_fraction",
            direction="lower_is_better",
        )
        self.assertEqual(len(slopes), 5)
        np.testing.assert_allclose(slopes["adverse_slope_per_reporting_interval"], 0.2)
        summary = summarise_painting_slopes(slopes)
        self.assertEqual(summary["painting_count"], 5)
        self.assertEqual(summary["sign_flip_assignments"], 32)
        adjacent = compute_adjacent_changes(synthetic, direction="lower_is_better")
        self.assertEqual(len(adjacent), 30)
        np.testing.assert_allclose(adjacent["adverse_change_per_percentage_point"], 0.02)

    def test_family_balanced_ranking_does_not_overweight_feature_anchors(self) -> None:
        rows = []
        values = {
            "pixel": {"a": 1.0, "b": 2.0, "c": 3.0},
            "feature_one": {"a": 3.0, "b": 2.0, "c": 1.0},
            "feature_two": {"a": 3.0, "b": 2.0, "c": 1.0},
        }
        families = {"pixel": "pixel", "feature_one": "feature", "feature_two": "feature"}
        for anchor, by_model in values.items():
            for model, value in by_model.items():
                for painting in ("p1", "p2"):
                    rows.append(
                        {
                            "model_id": model,
                            "painting_id": painting,
                            "evidence_family": families[anchor],
                            "anchor_id": anchor,
                            "comparison_direction": "lower_is_better",
                            "comparison_value": value,
                        }
                    )
        anchor_ranks, overall = family_balanced_ranks(pd.DataFrame(rows))
        self.assertEqual(anchor_ranks["anchor_id"].nunique(), 3)
        # Pixel and feature each receive one contribution, so the two feature
        # anchors do not outvote the single pixel anchor. All models tie here.
        np.testing.assert_allclose(overall["family_balanced_rank"], 2.0)
        np.testing.assert_allclose(overall["overall_rank"], 2.0)

    def test_morphology_association_schema_and_report_validation(self) -> None:
        morphology = pd.DataFrame(
            [
                {
                    "painting_id": painting,
                    "realized_damage_fraction": level,
                    "compactness": level + 0.01 * painting_index * level,
                    "outcome": 2.0 * level + 0.02 * painting_index * level,
                }
                for painting_index, painting in enumerate(["p1", "p2", "p3", "p4", "p5"])
                for level in [0.02, 0.04, 0.06, 0.08, 0.10, 0.15, 0.20]
            ]
        )
        association = size_and_painting_adjusted_spearman(
            morphology, morphology_column="compactness", outcome_column="outcome"
        )
        self.assertEqual(association["observation_count"], 35)
        self.assertTrue(np.isfinite(association["rho"]))

        record = {column: "" for column in ANALYSIS_COLUMNS}
        record.update(
            {
                "analysis_row_id": "dsa_test",
                "analysis_kind": "damage_trend",
                "schema_version": ANALYSIS_SCHEMA_VERSION,
                "status": "ok",
                "p_value": 0.0625,
                "q_value": 0.125,
            }
        )
        validation = validate_damage_size_analysis(pd.DataFrame([record]), config=self.config)
        self.assertTrue(validation["passed"], validation)

        images = "".join('<img alt="mock" src="data:image/png;base64,AA==">' for _ in range(17))
        html = f"<html><body><h1>RQ1 RQ2 RQ3</h1><h2>Conclusion</h2><p>Limitation</p>{images}</body></html>"
        report_checks = validate_damage_size_report_html(html, config=self.config)
        self.assertTrue(report_checks["passed"].all(), report_checks.to_dict("records"))


if __name__ == "__main__":
    unittest.main()
