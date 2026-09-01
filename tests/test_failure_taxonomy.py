from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import pandas as pd

from restoration_eval.failure_taxonomy import (
    ASSIGNMENT_SCHEMA_VERSION,
    CONFIG_SCHEMA_VERSION,
    FLAG_SCHEMA_VERSION,
    TAXONOMY_SCHEMA_VERSION,
    build_failure_candidate_population,
    build_failure_taxonomy,
    calibrate_operational_thresholds,
    classify_evidence_against_thresholds,
    load_failure_taxonomy_config,
    resolve_failure_taxonomy_inputs,
    uncertainty_candidate_ids,
    uncertainty_group_memberships,
    validate_failure_taxonomy,
    validate_flag_report_html,
    validate_upstream_completion,
)
from restoration_eval.grouped_statistical_analysis import (
    load_grouped_statistical_analysis_config,
)
from restoration_eval.paths import find_project_root


PROJECT_ROOT = find_project_root(Path(__file__))
CONFIG_PATH = PROJECT_ROOT / "config" / "evaluation" / "failure_taxonomy.yaml"


class FailureTaxonomyTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_failure_taxonomy_config(CONFIG_PATH)
        cls.inputs = resolve_failure_taxonomy_inputs(cls.config, PROJECT_ROOT)
        cls.grouped_config = load_grouped_statistical_analysis_config(
            cls.inputs["grouped_analysis_config_path"]
        )
        cls.canonical_uncertainty = pd.read_csv(
            cls.inputs["canonical_uncertainty_metrics_path"], low_memory=False
        )
        cls.damage_uncertainty = pd.read_csv(
            cls.inputs["damage_size_uncertainty_metrics_path"], low_memory=False
        )

    def test_config_and_exact_output_contract(self) -> None:
        self.assertEqual(self.config["config_schema_version"], CONFIG_SCHEMA_VERSION)
        settings = self.config["failure_taxonomy"]
        self.assertEqual(settings["taxonomy_schema_version"], TAXONOMY_SCHEMA_VERSION)
        self.assertEqual(settings["assignment_schema_version"], ASSIGNMENT_SCHEMA_VERSION)
        self.assertEqual(settings["flag_schema_version"], FLAG_SCHEMA_VERSION)
        self.assertEqual(settings["output"]["report_path"], "reports/flag_definitions.html")
        self.assertTrue(settings["report"]["approved_mock_structure_locked"])
        self.assertFalse(settings["evidence_policy"]["combined_trust_score_retained"])
        self.assertFalse(settings["evidence_policy"]["missing_evidence_may_count_as_pass"])
        self.assertEqual(len(self.inputs), len(settings["inputs"]))

    def test_upstream_manifests_are_complete(self) -> None:
        manifests = {
            f"{number:02d}": json.loads(
                self.inputs[f"manifest_{number:02d}_path"].read_text(encoding="utf-8")
            )
            for number in range(13, 27)
        }
        checks = validate_upstream_completion(manifests)
        self.assertEqual(len(checks), 14)
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))

    def test_supported_uncertainty_memberships_are_exact(self) -> None:
        canonical_ids = uncertainty_candidate_ids(self.canonical_uncertainty)
        damage_ids = uncertainty_candidate_ids(self.damage_uncertainty)
        self.assertEqual(len(canonical_ids), 520)
        self.assertEqual(len(damage_ids), 140)
        self.assertFalse(canonical_ids & damage_ids)
        canonical_members = uncertainty_group_memberships(self.canonical_uncertainty)
        damage_members = uncertainty_group_memberships(self.damage_uncertainty)
        self.assertEqual(canonical_members["uncertainty_group_id"].nunique(), 130)
        self.assertEqual(damage_members["uncertainty_group_id"].nunique(), 35)
        self.assertTrue(canonical_members.groupby("uncertainty_group_id").size().eq(4).all())
        self.assertTrue(damage_members.groupby("uncertainty_group_id").size().eq(4).all())

    def test_union_candidate_population_is_exact(self) -> None:
        population = build_failure_candidate_population(
            pd.read_csv(self.inputs["case_registry_path"], low_memory=False),
            pd.read_csv(self.inputs["artworks_path"], low_memory=False),
            pd.read_csv(self.inputs["opencv_candidates_path"], low_memory=False),
            pd.read_csv(self.inputs["lama_candidates_path"], low_memory=False),
            pd.read_csv(self.inputs["stable_diffusion_candidates_path"], low_memory=False),
            pd.read_csv(self.inputs["sdxl_candidates_path"], low_memory=False),
            pd.read_csv(self.inputs["damage_size_extension_candidates_path"], low_memory=False),
            self.canonical_uncertainty,
            self.damage_uncertainty,
            grouped_config=self.grouped_config,
            config=self.config,
        )
        self.assertEqual(len(population), 1785)
        self.assertEqual(population["candidate_id"].nunique(), 1785)
        self.assertEqual(int(population["is_primary_candidate"].sum()), 1240)
        self.assertEqual(int(population["is_uncertainty_candidate"].sum()), 660)
        self.assertEqual(int(population["quality_analysis_eligible"].sum()), 1090)
        self.assertEqual(int(population["is_zero_control"].sum()), 150)
        self.assertEqual(
            population["population_role"].value_counts().to_dict(),
            {
                "primary_comparison": 1115,
                "uncertainty_only": 545,
                "primary_and_uncertainty": 115,
                "bounded_sdxl": 10,
            },
        )
        self.assertEqual(
            int(population["model_id"].astype(str).eq("sdxl_inpainting").sum()), 10
        )
        self.assertTrue(
            population.loc[
                population["model_id"].astype(str).eq("sdxl_inpainting"),
                "population_role",
            ].eq("bounded_sdxl").all()
        )

    def test_taxonomy_has_fourteen_auditable_categories(self) -> None:
        taxonomy = build_failure_taxonomy(self.config)
        checks = validate_failure_taxonomy(taxonomy, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))
        self.assertEqual(len(taxonomy), 14)
        self.assertEqual(taxonomy["category_id"].nunique(), 14)
        self.assertGreaterEqual(int(taxonomy["is_proxy"].sum()), 5)
        self.assertTrue(taxonomy["recommended_action"].str.len().gt(20).all())

    def test_threshold_direction_is_not_reversed(self) -> None:
        config = copy.deepcopy(self.config)
        config["failure_taxonomy"]["threshold_policy"]["minimum_fitting_candidates"] = 1
        population = pd.DataFrame(
            {
                "candidate_id": ["c1", "c2", "c3", "c4"],
                "quality_analysis_eligible": [True] * 4,
                "is_zero_control": [False] * 4,
                "model_id": ["lama"] * 4,
            }
        )
        base = {
            "uncertainty_group_id": pd.NA,
            "case_id": "case",
            "painting_id": "p001",
            "model_id": "lama",
            "experiment_id": "canonical_missing_region",
            "prompt_variant_id": pd.NA,
            "population_role": "primary_comparison",
            "source_notebook_id": "13",
            "source_row_ids_json": "[]",
            "source": "classical",
            "evidence_family": "classical",
            "component": "component",
            "metric_name": "metric",
            "feature_model_id": "",
            "region_id": "masked_region",
            "summary_statistic": "value",
            "threshold_mode": "quantile",
            "schema_version": "failure_evidence.v1",
            "status": "ok",
            "issue": "",
        }
        rows = []
        for direction, indicator_id, values in (
            ("higher_is_worse", "high_bad", [1.0, 2.0, 3.0, 4.0]),
            ("lower_is_worse", "low_bad", [1.0, 2.0, 3.0, 4.0]),
        ):
            for candidate_id, value in zip(population["candidate_id"], values):
                rows.append(
                    {
                        **base,
                        "evidence_id": f"{indicator_id}_{candidate_id}",
                        "candidate_id": candidate_id,
                        "indicator_id": indicator_id,
                        "direction": direction,
                        "raw_value": value,
                        "adverse_value": value if direction == "higher_is_worse" else -value,
                    }
                )
        evidence = pd.DataFrame(rows)
        thresholds = calibrate_operational_thresholds(
            evidence, population, config=config
        )
        classified = classify_evidence_against_thresholds(evidence, thresholds)
        high = classified.loc[classified["indicator_id"].eq("high_bad")]
        low = classified.loc[classified["indicator_id"].eq("low_bad")]
        self.assertEqual(high.sort_values("raw_value").iloc[-1]["evidence_state"], "critical")
        self.assertEqual(low.sort_values("raw_value").iloc[0]["evidence_state"], "critical")

    def test_tied_quantile_floor_and_ceiling_are_not_critical(self) -> None:
        config = copy.deepcopy(self.config)
        config["failure_taxonomy"]["threshold_policy"]["minimum_fitting_candidates"] = 1
        population = pd.DataFrame(
            {
                "candidate_id": ["c1", "c2", "c3", "c4"],
                "quality_analysis_eligible": [True] * 4,
                "is_zero_control": [False] * 4,
                "model_id": ["lama"] * 4,
            }
        )
        base = {
            "uncertainty_group_id": pd.NA,
            "case_id": "case",
            "painting_id": "p001",
            "model_id": "lama",
            "experiment_id": "canonical_missing_region",
            "prompt_variant_id": pd.NA,
            "population_role": "primary_comparison",
            "source_notebook_id": "13",
            "source_row_ids_json": "[]",
            "source": "classical",
            "evidence_family": "classical",
            "component": "component",
            "metric_name": "metric",
            "feature_model_id": "",
            "region_id": "masked_region",
            "summary_statistic": "value",
            "threshold_mode": "quantile",
            "schema_version": "failure_evidence.v1",
            "status": "ok",
            "issue": "",
        }
        rows = []
        for direction, indicator_id, value in (
            ("higher_is_worse", "tied_floor", 0.0),
            ("lower_is_worse", "tied_ceiling", 1.0),
        ):
            for candidate_id in population["candidate_id"]:
                rows.append(
                    {
                        **base,
                        "evidence_id": f"{indicator_id}_{candidate_id}",
                        "candidate_id": candidate_id,
                        "indicator_id": indicator_id,
                        "direction": direction,
                        "raw_value": value,
                        "adverse_value": value if direction == "higher_is_worse" else -value,
                    }
                )
        evidence = pd.DataFrame(rows)
        thresholds = calibrate_operational_thresholds(
            evidence, population, config=config
        )
        classified = classify_evidence_against_thresholds(evidence, thresholds)
        self.assertFalse(classified["evidence_state"].eq("critical").any())
        self.assertFalse(classified["evidence_state"].eq("warning").any())
        self.assertTrue(classified["evidence_state"].eq("favourable").all())

    def test_mock_aligned_report_contract(self) -> None:
        settings = self.config["failure_taxonomy"]
        images = "".join(
            '<img src="data:image/png;base64,AA==" alt="diagnostic">'
            for _ in range(settings["report"]["minimum_embedded_images"])
        )
        sections = "".join(
            f'<section id="{section}"><h2>{section}</h2></section>'
            for section in settings["report"]["required_section_ids"]
        )
        html = (
            "<html><body>" + sections + images
            + "<p>1,785 candidates. RQ1 RQ2 RQ3. This is decision support. "
            "Uncertainty is not calibrated confidence. Proxy categories are explicit. "
            "This report does not constitute conservation approval. A combined trust score "
            "is not used.</p></body></html>"
        )
        checks = validate_flag_report_html(html, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))


if __name__ == "__main__":
    unittest.main()
