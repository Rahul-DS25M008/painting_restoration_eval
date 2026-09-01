from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from restoration_eval.grouped_statistical_analysis import (
    CORRELATION_COLUMNS,
    CORRELATION_SCHEMA_VERSION,
    RANKING_STABILITY_COLUMNS,
    RANKING_STABILITY_SCHEMA_VERSION,
    STATISTICAL_RESULT_COLUMNS,
    STATISTICAL_RESULTS_SCHEMA_VERSION,
    benjamini_hochberg,
    cliffs_delta,
    correlation_summary,
    deterministic_cluster_bootstrap_interval,
    empty_metric_correlations,
    empty_ranking_stability,
    empty_statistical_results,
    friedman_with_kendalls_w,
    kruskal_with_epsilon_squared,
    load_grouped_statistical_analysis_config,
    resolve_analysis_inputs,
    select_primary_candidate_population,
    sign_flip_test,
    validate_grouped_statistical_report_html,
    validate_metric_correlations,
    validate_ranking_stability,
    validate_statistical_results,
    validate_upstream_run_manifests,
)
from restoration_eval.paths import find_project_root


PROJECT_ROOT = find_project_root(Path(__file__))
CONFIG_PATH = PROJECT_ROOT / "config" / "evaluation" / "grouped_statistical_analysis.yaml"


class GroupedStatisticalAnalysisTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_grouped_statistical_analysis_config(CONFIG_PATH)
        cls.inputs = resolve_analysis_inputs(cls.config, PROJECT_ROOT)
        cls.selected = select_primary_candidate_population(
            pd.read_csv(cls.inputs["case_registry_path"]),
            pd.read_csv(cls.inputs["artworks_path"]),
            pd.read_csv(cls.inputs["opencv_candidates_path"]),
            pd.read_csv(cls.inputs["lama_candidates_path"]),
            pd.read_csv(cls.inputs["stable_diffusion_candidates_path"]),
            pd.read_csv(cls.inputs["sdxl_candidates_path"]),
            config=cls.config,
        )

    def test_config_inputs_and_upstream_completion_gates(self) -> None:
        settings = self.config["grouped_statistical_analysis"]
        self.assertEqual(settings["notebook_id"], "26")
        self.assertTrue(settings["report"]["approved_mock_structure_locked"])
        self.assertEqual(settings["population"]["dataset_source_levels"], ["controlled_50"])
        self.assertFalse(settings["statistics"]["combined_quality_score_retained"])
        self.assertFalse(settings["statistics"]["combined_trust_score_retained"])
        self.assertEqual(len(self.inputs), len(settings["inputs"]))
        notebook_by_key = {
            "01": "artworks_run_manifest_path", "08": "contracts_run_manifest_path",
            "09": "opencv_run_manifest_path", "10": "lama_run_manifest_path",
            "11": "stable_diffusion_run_manifest_path", "12": "sdxl_run_manifest_path",
            "13": "classical_run_manifest_path", "14": "lpips_run_manifest_path",
            "15": "feature_run_manifest_path", "16": "spatial_run_manifest_path",
            "17": "local_run_manifest_path", "18": "uncertainty_run_manifest_path",
            "19": "spatial_explanations_run_manifest_path", "20": "semantic_run_manifest_path",
            "21": "comparison_run_manifest_path", "22": "damage_size_uncertainty_run_manifest_path",
            "23": "damage_size_analysis_run_manifest_path", "24": "mask_robustness_run_manifest_path",
            "25": "degradation_analysis_run_manifest_path",
        }
        manifests = {
            notebook_id: json.loads(self.inputs[key].read_text(encoding="utf-8"))
            for notebook_id, key in notebook_by_key.items()
        }
        checks = validate_upstream_run_manifests(manifests)
        self.assertEqual(len(checks), 19)
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))

    def test_primary_population_is_exact_and_metric_independent(self) -> None:
        selected = self.selected
        self.assertEqual(len(selected), 1240)
        self.assertEqual(selected["candidate_id"].nunique(), 1240)
        self.assertEqual(selected.loc[selected["coverage_role"].eq("core_three_model"), "case_id"].nunique(), 410)
        self.assertEqual(selected.groupby("model_id").size().to_dict(), {
            "lama": 410, "opencv_telea": 410,
            "sdxl_inpainting": 10, "stable_diffusion_inpainting": 410,
        })
        core = selected.loc[selected["coverage_role"].eq("core_three_model")]
        self.assertEqual(int(core["is_zero_control"].sum()), 150)
        self.assertEqual(int(core["quality_analysis_eligible"].sum()), 1080)
        self.assertEqual(set(selected["dataset_scope"]), {"controlled_50"})
        self.assertTrue(selected["restored_path"].str.startswith("outputs/").all())

    def test_uncertainty_and_focused_analysis_coverage_is_explicit(self) -> None:
        canonical = pd.read_csv(self.inputs["canonical_uncertainty_groups_path"])
        damage_size = pd.read_csv(self.inputs["damage_size_uncertainty_path"])
        self.assertEqual(canonical["uncertainty_group_id"].nunique(), 130)
        self.assertEqual(damage_size["uncertainty_group_id"].nunique(), 35)
        self.assertEqual(
            canonical["prompt_variant_id"].value_counts().to_dict(),
            {"p00_generic": 80, "p05_scratch_aware": 50},
        )
        self.assertEqual(len(pd.read_csv(self.inputs["damage_size_analysis_path"])), 1901)
        self.assertEqual(len(pd.read_csv(self.inputs["mask_robustness_analysis_path"])), 5373)
        self.assertEqual(len(pd.read_csv(self.inputs["degradation_analysis_path"])), 4695)

    def test_deterministic_statistics(self) -> None:
        exact = sign_flip_test([1, 2, 3, 4, 5])
        self.assertEqual(exact["assignments"], 32)
        self.assertEqual(exact["method"], "exact_sign_flip")
        monte_carlo_a = sign_flip_test(np.linspace(-1, 2, 20), monte_carlo_assignments=100000)
        monte_carlo_b = sign_flip_test(np.linspace(-1, 2, 20), monte_carlo_assignments=100000)
        self.assertEqual(monte_carlo_a, monte_carlo_b)
        self.assertEqual(monte_carlo_a["assignments"], 100000)

        exhaustive = deterministic_cluster_bootstrap_interval([1, 2, 3, 4, 5])
        self.assertEqual(exhaustive["resamples"], 3125)
        sampled_a = deterministic_cluster_bootstrap_interval(range(10), resamples=5000)
        sampled_b = deterministic_cluster_bootstrap_interval(range(10), resamples=5000)
        self.assertEqual(sampled_a, sampled_b)

        friedman = friedman_with_kendalls_w(([1, 2, 3, 4], [2, 3, 4, 5], [3, 4, 5, 6]))
        self.assertEqual(friedman["n_blocks"], 4)
        self.assertGreaterEqual(friedman["kendalls_w"], 0)
        kruskal_result = kruskal_with_epsilon_squared(([1, 2, 3], [4, 5, 6]))
        self.assertGreaterEqual(kruskal_result["epsilon_squared"], 0)
        correlation = correlation_summary([1, 2, 3, 4], [4, 3, 2, 1])
        self.assertAlmostEqual(correlation["spearman_rho"], -1.0)
        self.assertAlmostEqual(cliffs_delta([3, 4], [1, 2]), 1.0)
        q_values = benjamini_hochberg([0.01, 0.04, 0.03, np.nan])
        self.assertTrue(np.isnan(q_values[-1]))
        self.assertTrue(np.all((q_values[:3] >= 0) & (q_values[:3] <= 1)))

    def test_canonical_schemas_and_mock_aligned_report_contract(self) -> None:
        statistical = empty_statistical_results()
        row = {column: pd.NA for column in STATISTICAL_RESULT_COLUMNS}
        row.update({
            "result_id": "result_test", "result_kind": "model_descriptive_summary",
            "schema_version": STATISTICAL_RESULTS_SCHEMA_VERSION, "status": "ok",
        })
        statistical.loc[len(statistical)] = row
        self.assertTrue(validate_statistical_results(statistical, config=self.config)["passed"])

        correlations = empty_metric_correlations()
        row = {column: pd.NA for column in CORRELATION_COLUMNS}
        row.update({
            "correlation_id": "correlation_test", "correlation_kind": "metric_pair_correlation",
            "schema_version": CORRELATION_SCHEMA_VERSION, "status": "ok",
        })
        correlations.loc[len(correlations)] = row
        self.assertTrue(validate_metric_correlations(correlations, config=self.config)["passed"])

        rankings = empty_ranking_stability()
        row = {column: pd.NA for column in RANKING_STABILITY_COLUMNS}
        row.update({
            "ranking_id": "ranking_test", "ranking_kind": "baseline_rank",
            "schema_version": RANKING_STABILITY_SCHEMA_VERSION, "status": "ok",
        })
        rankings.loc[len(rankings)] = row
        self.assertTrue(validate_ranking_stability(rankings, config=self.config)["passed"])

        sections = self.config["grouped_statistical_analysis"]["report"]["required_section_ids"]
        image = '<img src="data:image/png;base64,AA==" alt="test">'
        html = "<html><body>" + "".join(
            f'<section id="{section}"><h2>{section}</h2>{image}{image}</section>'
            for section in sections
        ) + (
            "<p>RQ1 RQ2 RQ3 conclusion limitation controlled_50. Painting is the "
            "independent unit. Uncertainty is not calibrated confidence. Dataset-source "
            "comparison is not_applicable_single_dataset. SDXL is bounded.</p></body></html>"
        )
        checks = validate_grouped_statistical_report_html(html, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))


if __name__ == "__main__":
    unittest.main()
