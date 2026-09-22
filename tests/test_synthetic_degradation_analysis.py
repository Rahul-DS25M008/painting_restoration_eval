from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from restoration_eval.paths import find_project_root
from restoration_eval.synthetic_degradation_analysis import (
    ANALYSIS_COLUMNS,
    ANALYSIS_SCHEMA_VERSION,
    benjamini_hochberg,
    build_eligibility_audit,
    build_runtime_evidence,
    compute_case_family_balanced_ranks,
    compute_painting_slopes,
    empty_analysis_frame,
    exact_sign_flip_test,
    exhaustive_bootstrap_interval,
    load_synthetic_degradation_analysis_config,
    matched_rank_biserial,
    monte_carlo_sign_flip_test,
    normalise_quality_evidence,
    resolve_analysis_inputs,
    select_quality_anchor_values,
    select_spillover_evidence,
    select_synthetic_degradation_population,
    seeded_cluster_bootstrap_interval,
    summarise_painting_slopes_bounded,
    validate_synthetic_degradation_analysis,
    validate_synthetic_degradation_report_html,
    validate_upstream_run_manifests,
    within_family_cluster_spearman,
)


PROJECT_ROOT = find_project_root(Path(__file__))
CONFIG_PATH = (
    PROJECT_ROOT
    / "config"
    / "evaluation"
    / "synthetic_degradation_analysis.yaml"
)


class SyntheticDegradationAnalysisTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_synthetic_degradation_analysis_config(CONFIG_PATH)
        cls.inputs = resolve_analysis_inputs(cls.config, PROJECT_ROOT)
        cls.cases = pd.read_csv(cls.inputs["degradation_cases_path"])
        cls.artworks = pd.read_csv(cls.inputs["artworks_path"])
        cls.eligibility = pd.read_csv(cls.inputs["eligibility_path"])
        cls.opencv = pd.read_csv(cls.inputs["opencv_candidates_path"])
        cls.lama = pd.read_csv(cls.inputs["lama_candidates_path"])
        cls.hint = pd.read_csv(cls.inputs["hint_candidates_path"])
        cls.stable_diffusion = pd.read_csv(
            cls.inputs["stable_diffusion_candidates_path"]
        )
        cls.sdxl = pd.read_csv(cls.inputs["sdxl_candidates_path"])
        cls.selected = select_synthetic_degradation_population(
            cls.cases,
            cls.artworks,
            cls.eligibility,
            cls.opencv,
            cls.lama,
            cls.hint,
            cls.stable_diffusion,
            cls.sdxl,
            config=cls.config,
        )

    def test_config_inputs_and_upstream_completion_gates(self) -> None:
        settings = self.config["synthetic_degradation_analysis"]
        self.assertEqual(settings["notebook_id"], "25")
        self.assertTrue(settings["report"]["approved_mock_structure_locked"])
        self.assertTrue(settings["report"]["require_evidence_to_assertion_pairs"])
        self.assertFalse(settings["statistics"]["combined_quality_score_retained"])
        self.assertFalse(settings["statistics"]["uncertainty_analysis_applicable"])
        self.assertFalse(
            settings["evidence_policy"]["stochastic_uncertainty_claim_permitted"]
        )
        self.assertEqual(len(self.inputs), len(settings["inputs"]))

        notebook_by_key = {
            "01": "artworks_run_manifest_path",
            "07": "degradation_run_manifest_path",
            "08": "contracts_run_manifest_path",
            "09": "opencv_run_manifest_path",
            "10": "lama_run_manifest_path",
            "11": "stable_diffusion_run_manifest_path",
            "12": "sdxl_run_manifest_path",
            "12A": "hint_run_manifest_path",
            "13": "classical_run_manifest_path",
            "14": "lpips_run_manifest_path",
            "15": "feature_run_manifest_path",
            "16": "spatial_run_manifest_path",
            "17": "local_run_manifest_path",
            "20": "semantic_run_manifest_path",
            "21": "comparison_run_manifest_path",
        }
        manifests = {
            notebook_id: json.loads(
                self.inputs[key].read_text(encoding="utf-8")
            )
            for notebook_id, key in notebook_by_key.items()
        }
        checks = validate_upstream_run_manifests(manifests)
        self.assertEqual(len(checks), 15)
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))

    def test_population_eligibility_and_candidate_selection_are_exact(self) -> None:
        expected = self.config["synthetic_degradation_analysis"]["expected_counts"]
        self.assertEqual(len(self.selected), expected["selected_candidates"])
        self.assertEqual(self.selected["case_id"].nunique(), expected["eligible_cases"])
        self.assertEqual(self.selected["painting_id"].nunique(), expected["paintings"])
        self.assertEqual(
            self.selected.groupby("model_id").size().to_dict(),
            {
                "hint_places2": 350,
                "lama": 350,
                "opencv_telea": 350,
                "sdxl_inpainting": 11,
                "stable_diffusion_inpainting": 350,
            },
        )
        self.assertFalse(
            self.selected.duplicated(["model_id", "case_id"]).any()
        )
        self.assertTrue(self.selected["restored_path"].str.startswith("outputs/").all())
        core = self.selected.loc[
            ~self.selected["model_id"].eq("sdxl_inpainting")
        ]
        self.assertEqual(len(core), expected["core_candidates"])
        self.assertTrue(core.groupby("case_id").size().eq(4).all())
        sdxl = self.selected.loc[self.selected["model_id"].eq("sdxl_inpainting")]
        self.assertEqual(len(sdxl), expected["sdxl_candidates"])

        stable = self.selected.loc[
            self.selected["model_id"].eq("stable_diffusion_inpainting")
        ]
        self.assertTrue(stable["execution_role"].eq("primary").all())
        self.assertTrue(stable["prompt_variant_id"].eq("p00_generic").all())
        self.assertTrue(pd.to_numeric(stable["seed"]).eq(2026).all())

        audit = build_eligibility_audit(
            self.cases,
            self.eligibility,
            self.selected,
            config=self.config,
        )
        self.assertEqual(len(audit), expected["eligibility_case_model_rows"])
        self.assertEqual(int(audit["eligible"].sum()), expected["eligible_case_model_rows"])
        self.assertEqual(int((~audit["eligible"]).sum()), expected["excluded_case_model_rows"])
        self.assertEqual(int(audit["candidate_available"].sum()), expected["selected_candidates"])

    def test_metric_sources_anchors_spillover_and_runtime_cover_population(self) -> None:
        tables = {
            "classical": pd.read_csv(self.inputs["classical_metrics_path"]),
            "perceptual": pd.read_csv(self.inputs["lpips_metrics_path"]),
            "feature": pd.read_csv(self.inputs["feature_metrics_path"]),
            "spatial": pd.read_csv(self.inputs["spatial_metrics_path"]),
            "local_consistency": pd.read_csv(
                self.inputs["local_metrics_path"], low_memory=False
            ),
            "semantic_structural": pd.read_csv(
                self.inputs["semantic_metrics_path"], low_memory=False
            ),
        }
        normalized = normalise_quality_evidence(
            tables,
            self.selected,
            config=self.config,
        )
        expected = self.config["synthetic_degradation_analysis"]["expected_counts"]
        self.assertEqual(len(normalized), expected["normalized_quality_rows"])
        self.assertEqual(normalized["candidate_id"].nunique(), expected["selected_candidates"])

        anchors = select_quality_anchor_values(
            normalized,
            spatial_source=tables["spatial"],
            config=self.config,
        )
        self.assertEqual(len(anchors), expected["candidate_quality_anchor_rows"])
        self.assertEqual(anchors["anchor_id"].nunique(), 11)
        self.assertTrue(anchors.groupby("candidate_id").size().eq(11).all())
        spatial_anchor = anchors.loc[
            anchors["anchor_id"].eq("spatial_masked_error")
        ]
        self.assertTrue(spatial_anchor["improvement_value"].notna().all())

        spillover = select_spillover_evidence(normalized, config=self.config)
        self.assertEqual(len(spillover), expected["candidate_spillover_rows"])
        self.assertFalse(spillover["quality_ranking_eligible"].any())
        self.assertTrue(
            np.isclose(
                pd.to_numeric(spillover["comparison_value"]),
                0.0,
                atol=0.0,
                rtol=0.0,
            ).all()
        )

        runtime = build_runtime_evidence(self.selected, config=self.config)
        self.assertEqual(len(runtime), expected["candidate_runtime_rows"])
        self.assertFalse(runtime["quality_ranking_eligible"].any())

        spatial_maps = pd.read_csv(self.inputs["spatial_maps_path"])
        local_maps = pd.read_csv(self.inputs["local_maps_path"])
        candidate_ids = set(self.selected["candidate_id"].astype(str))
        self.assertEqual(
            int(spatial_maps["candidate_id"].astype(str).isin(candidate_ids).sum()),
            expected["spatial_map_records"],
        )
        self.assertEqual(
            int(local_maps["candidate_id"].astype(str).isin(candidate_ids).sum()),
            expected["local_map_records"],
        )

    def test_balanced_ranks_slopes_and_area_association(self) -> None:
        model_ids = [
            "opencv_telea",
            "lama",
            "hint_places2",
            "stable_diffusion_inpainting",
        ]
        rows = []
        for severity_rank, severity in enumerate(("mild", "moderate", "severe"), 1):
            for painting_index, painting_id in enumerate(
                f"p{index:03d}" for index in range(1, 36)
            ):
                for model_index, model_id in enumerate(model_ids):
                    for anchor_id, family in (("a1", "pixel"), ("a2", "feature")):
                        rows.append(
                            {
                                "case_id": f"{painting_id}_{severity}",
                                "painting_id": painting_id,
                                "model_id": model_id,
                                "degradation_family": "water_stain",
                                "severity": severity,
                                "severity_rank": severity_rank,
                                "affected_content_fraction": (
                                    severity_rank / 10 + painting_index / 1000
                                ),
                                "evidence_family": family,
                                "anchor_id": anchor_id,
                                "comparison_direction": "lower_is_better",
                                "comparison_value": float(
                                    model_index + severity_rank + painting_index / 10
                                ),
                            }
                        )
        synthetic = pd.DataFrame(rows)
        mild = synthetic.loc[synthetic["severity"].eq("mild")]
        ranks = compute_case_family_balanced_ranks(mild, model_ids=model_ids)
        self.assertEqual(len(ranks), 140)
        self.assertTrue(ranks.groupby("case_id").size().eq(4).all())
        self.assertTrue(
            ranks.loc[ranks["model_id"].eq("opencv_telea"), "overall_rank"]
            .eq(1.0)
            .all()
        )

        slope_input = synthetic.loc[
            synthetic["model_id"].eq("lama")
            & synthetic["anchor_id"].eq("a1")
        ]
        slopes = compute_painting_slopes(
            slope_input,
            exposure_column="severity_rank",
            direction="lower_is_better",
            reporting_scale_percentage_points=1.0,
        )
        self.assertEqual(len(slopes), 35)
        self.assertTrue(slopes["level_count"].eq(3).all())
        slope_summary = summarise_painting_slopes_bounded(slopes)
        self.assertEqual(slope_summary["resamples"], 5000)
        self.assertEqual(slope_summary["sign_flip_assignments"], 100000)

        association = within_family_cluster_spearman(
            slope_input,
            area_column="affected_content_fraction",
            outcome_column="comparison_value",
        )
        self.assertEqual(association["painting_count"], 35)
        self.assertEqual(association["observation_count"], 105)
        self.assertEqual(association["bootstrap_resamples"], 5000)
        self.assertGreater(association["rho"], 0.90)

        bootstrap = seeded_cluster_bootstrap_interval(range(1, 36))
        self.assertEqual(bootstrap["resamples"], 5000)
        self.assertEqual(
            monte_carlo_sign_flip_test(range(1, 36))["assignments"],
            100000,
        )
        self.assertAlmostEqual(matched_rank_biserial([1, 2, 3, 4, 5]), 1.0)
        np.testing.assert_allclose(
            benjamini_hochberg([0.01, 0.02, 0.20]),
            [0.03, 0.03, 0.20],
        )

    def test_schema_and_report_validators_enforce_contract(self) -> None:
        record = {column: "" for column in ANALYSIS_COLUMNS}
        record.update(
            {
                "analysis_row_id": "sda_test",
                "analysis_kind": "core_model_scope_summary",
                "schema_version": ANALYSIS_SCHEMA_VERSION,
                "status": "ok",
                "p_value": 0.0625,
                "q_value": 0.125,
            }
        )
        self.assertEqual(list(empty_analysis_frame().columns), list(ANALYSIS_COLUMNS))
        frame = pd.DataFrame([record], columns=ANALYSIS_COLUMNS)
        validation = validate_synthetic_degradation_analysis(
            frame,
            config=self.config,
        )
        self.assertTrue(validation["passed"], validation)

        report = self.config["synthetic_degradation_analysis"]["report"]
        images = "".join(
            '<img alt="mock" src="data:image/png;base64,AA==">'
            for _ in range(21)
        )
        sections = "".join(
            f'<section id="{section}"><h2>{section}</h2></section>'
            for section in report["required_section_ids"]
        )
        html = (
            "<html><body><h1>RQ1 RQ2 RQ3</h1>"
            "<p>Conclusion and limitation. Procedural effects are not exact "
            "conservation damage. Uncertainty is not applicable because no "
            "repeated-seed synthetic-degradation population exists.</p>"
            f"{sections}{images}</body></html>"
        )
        checks = validate_synthetic_degradation_report_html(
            html,
            config=self.config,
        )
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))


if __name__ == "__main__":
    unittest.main()
