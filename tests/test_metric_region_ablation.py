from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from restoration_eval.failure_taxonomy import load_failure_taxonomy_config
from restoration_eval.metric_region_ablation import (
    ABLATION_RESULTS_SCHEMA_VERSION,
    CONFIG_SCHEMA_VERSION,
    FLAG_STABILITY_SCHEMA_VERSION,
    SCENARIO_SCHEMA_VERSION,
    atomic_write_csv,
    build_flag_stability,
    build_region_membership_table,
    build_scenario_catalog,
    coerce_ablation_results,
    load_metric_region_ablation_config,
    resolve_metric_region_ablation_inputs,
    scenario_failure_config,
    validate_ablation_report_html,
    validate_ablation_results,
    validate_flag_stability,
    validate_scenario_catalog,
    validate_upstream_completion,
)
from restoration_eval.paths import find_project_root


PROJECT_ROOT = find_project_root(Path(__file__))
CONFIG_PATH = PROJECT_ROOT / "config" / "evaluation" / "metric_region_ablation.yaml"


class MetricRegionAblationTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_metric_region_ablation_config(CONFIG_PATH)
        cls.inputs = resolve_metric_region_ablation_inputs(cls.config, PROJECT_ROOT)
        cls.catalog = build_scenario_catalog(cls.config)

    def test_config_and_exact_output_contract(self) -> None:
        self.assertEqual(self.config["config_schema_version"], CONFIG_SCHEMA_VERSION)
        settings = self.config["metric_region_ablation"]
        self.assertEqual(settings["scenario_schema_version"], SCENARIO_SCHEMA_VERSION)
        self.assertEqual(
            settings["ablation_results_schema_version"],
            ABLATION_RESULTS_SCHEMA_VERSION,
        )
        self.assertEqual(
            settings["flag_stability_schema_version"],
            FLAG_STABILITY_SCHEMA_VERSION,
        )
        self.assertEqual(
            settings["output"]["root"],
            "outputs/28_metric_and_region_policy_ablation",
        )
        self.assertEqual(settings["expected_counts"]["canonical_output_files"], 8)
        self.assertEqual(settings["expected_counts"]["artifact_records"], 6)
        self.assertFalse(settings["ranking"]["retain_continuous_case_trust_score"])
        self.assertFalse(settings["evidence_policy"]["combined_trust_score_retained"])
        self.assertEqual(len(self.inputs), len(settings["inputs"]))

    def test_scenario_catalog_is_exact(self) -> None:
        checks = validate_scenario_catalog(self.catalog, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))
        self.assertEqual(len(self.catalog), 23)
        self.assertEqual(
            self.catalog["scenario_family"].value_counts().to_dict(),
            {"metric": 12, "region": 6, "aggregation": 3, "threshold": 2},
        )
        self.assertEqual(
            self.catalog.loc[self.catalog["is_baseline"], "scenario_id"].tolist(),
            ["complete_approved_framework"],
        )
        self.assertEqual(int(self.catalog["ranking_applicable"].sum()), 18)

        baseline = self.catalog.set_index("scenario_id").loc["complete_approved_framework"]
        no_uncertainty = self.catalog.set_index("scenario_id").loc["without_uncertainty"]
        self.assertEqual(
            json.loads(baseline["active_anchor_ids_json"]),
            json.loads(no_uncertainty["active_anchor_ids_json"]),
        )
        self.assertNotEqual(
            json.loads(baseline["active_indicator_ids_json"]),
            json.loads(no_uncertainty["active_indicator_ids_json"]),
        )

    def test_upstream_manifests_are_complete(self) -> None:
        manifests = {
            "08": json.loads(
                self.inputs["contracts_manifest_path"].read_text(encoding="utf-8")
            )
        }
        manifests.update(
            {
                f"{number:02d}": json.loads(
                    self.inputs[f"manifest_{number:02d}_path"].read_text(
                        encoding="utf-8"
                    )
                )
                for number in range(13, 28)
            }
        )
        checks = validate_upstream_completion(manifests)
        self.assertEqual(len(checks), 16)
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))

    def test_n08_region_ablation_memberships_are_available(self) -> None:
        region_policy = pd.read_csv(self.inputs["region_policy_path"])
        memberships = build_region_membership_table(
            region_policy, config=self.config
        )
        compatible = memberships.loc[memberships["compatible"]]
        counts = compatible["ablation_policy_id"].value_counts().to_dict()
        self.assertEqual(counts["complete_approved_policy"], 86)
        self.assertEqual(counts["full_image_only"], 11)
        self.assertEqual(counts["content_region_only"], 12)
        self.assertEqual(counts["masked_pixels_where_valid"], 10)
        self.assertEqual(counts["mask_bbox_only"], 12)
        self.assertEqual(counts["boundary_regions"], 24)
        self.assertEqual(counts["outside_mask_only"], 11)

    def test_scenario_failure_config_is_isolated_and_scoped(self) -> None:
        base = load_failure_taxonomy_config(
            self.inputs["failure_taxonomy_config_path"]
        )
        original_indicator_count = len(base["failure_taxonomy"]["indicators"])
        by_id = self.catalog.set_index("scenario_id")

        without_texture = scenario_failure_config(
            base,
            by_id.loc["without_texture"],
            ablation_config=self.config,
        )
        active_ids = {
            item["indicator_id"]
            for item in without_texture["failure_taxonomy"]["indicators"]
        }
        self.assertNotIn("local_texture_error_p95", active_ids)
        self.assertLess(len(active_ids), original_indicator_count)
        self.assertEqual(len(base["failure_taxonomy"]["indicators"]), original_indicator_count)

        sensitive = scenario_failure_config(
            base,
            by_id.loc["more_sensitive_thresholds"],
            ablation_config=self.config,
        )
        policy = sensitive["failure_taxonomy"]["threshold_policy"]
        self.assertEqual(policy["warning_quantile"], 0.80)
        self.assertEqual(policy["critical_quantile"], 0.95)

        critical_only = scenario_failure_config(
            base,
            by_id.loc["critical_only"],
            ablation_config=self.config,
        )
        self.assertEqual(
            critical_only["failure_taxonomy"]["threshold_policy"][
                "distinct_warning_components_required"
            ],
            999,
        )

        availability = pd.DataFrame(
            {
                "indicator_id": ["masked_mae", "masked_mae", "crop_ssim"],
                "region_id": ["full_image", "content_region", "full_image"],
                "available": [True, True, False],
            }
        )
        full_image = scenario_failure_config(
            base,
            by_id.loc["full_image_only"],
            ablation_config=self.config,
            indicator_region_availability=availability,
        )
        rewritten = full_image["failure_taxonomy"]["indicators"]
        self.assertEqual(len(rewritten), 1)
        self.assertEqual(rewritten[0]["indicator_id"], "masked_mae")
        self.assertEqual(rewritten[0]["region_id"], "full_image")

    @staticmethod
    def _flag_frame(states: dict[tuple[str, str], tuple[str, str]]) -> pd.DataFrame:
        rows = []
        for (candidate_id, flag_id), (status, severity) in states.items():
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "case_id": f"case_{candidate_id}",
                    "painting_id": "p001",
                    "model_id": "lama",
                    "experiment_id": "canonical_missing_region",
                    "prompt_variant_id": "",
                    "population_role": "primary_comparison",
                    "flag_id": flag_id,
                    "flag_status": status,
                    "flag_severity": severity,
                }
            )
        return pd.DataFrame(rows)

    def test_flag_stability_records_trigger_and_missingness_changes(self) -> None:
        baseline = self._flag_frame(
            {
                ("c1", "texture"): ("triggered", "warning"),
                ("c1", "colour"): ("not_triggered", "none"),
                ("c2", "texture"): ("not_triggered", "none"),
                ("c2", "colour"): ("insufficient_evidence", "not_assigned"),
            }
        )
        scenario = self._flag_frame(
            {
                ("c1", "texture"): ("not_triggered", "none"),
                ("c1", "colour"): ("triggered", "critical"),
                ("c2", "texture"): ("not_triggered", "none"),
                ("c2", "colour"): ("not_triggered", "none"),
            }
        )
        stability = build_flag_stability(
            baseline,
            scenario,
            scenario_id="synthetic_test",
            scenario_family="metric",
        )
        self.assertEqual(len(stability), 2)
        first = stability.set_index("candidate_id").loc["c1"]
        self.assertEqual(first["changed_flag_count"], 2)
        self.assertEqual(json.loads(first["newly_triggered_flag_ids_json"]), ["colour"])
        self.assertEqual(json.loads(first["no_longer_triggered_flag_ids_json"]), ["texture"])
        second = stability.set_index("candidate_id").loc["c2"]
        self.assertEqual(
            json.loads(second["resolved_insufficient_flag_ids_json"]), ["colour"]
        )

    def test_actual_baseline_flags_round_trip_without_change(self) -> None:
        flags = pd.read_csv(self.inputs["trustworthiness_flags_path"], low_memory=False)
        stability = build_flag_stability(
            flags,
            flags,
            scenario_id="complete_approved_framework",
            scenario_family="metric",
        )
        self.assertEqual(len(stability), 1785)
        self.assertTrue(stability["changed_flag_count"].eq(0).all())
        self.assertTrue(stability["flag_state_agreement_fraction"].eq(1.0).all())
        partial_checks = validate_flag_stability(
            stability, config=self.config, require_complete=False
        )
        self.assertTrue(partial_checks["passed"].all(), partial_checks.to_dict("records"))

    def test_canonical_result_coercion_and_validation(self) -> None:
        frame = coerce_ablation_results(
            [
                {
                    "scenario_id": "complete_approved_framework",
                    "scenario_family": "metric",
                    "result_kind": "scenario_definition",
                    "analysis_scope": "population",
                    "scope_value": "all",
                    "entity_type": "scenario",
                    "entity_id": "complete_approved_framework",
                    "applicability_status": "supported",
                    "interpretation_status": "baseline",
                }
            ]
        )
        self.assertEqual(frame.iloc[0]["schema_version"], ABLATION_RESULTS_SCHEMA_VERSION)
        checks = validate_ablation_results(
            frame, config=self.config, require_complete=False
        )
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))

    def test_report_validator_enforces_mock_structure_and_embedded_images(self) -> None:
        report = self.config["metric_region_ablation"]["report"]
        sections = "".join(
            f'<section id="{section_id}"><h2>{section_id}</h2></section>'
            for section_id in report["required_section_ids"]
        )
        analytical = "".join(
            f'<div data-analytical-view="view-{index}"></div>'
            for index in range(report["minimum_embedded_analytical_views"])
        )
        panels = "".join(
            f'<div data-diagnostic-panel="panel-{index}"></div>'
            for index in range(report["diagnostic_panel_count"])
        )
        images = "".join(
            '<img src="data:image/png;base64,AA==" alt="diagnostic">'
            for _ in range(
                report["diagnostic_tile_count"] + report["canonical_figure_count"]
            )
        )
        html = (
            "<html><body>"
            f"<h1>{report['title']}</h1><p>{report['subtitle']}</p>"
            + sections
            + analytical
            + panels
            + images
            + "<p>No universal trust score is produced.</p>"
            + ("validated evidence " * 100)
            + "</body></html>"
        )
        checks = validate_ablation_report_html(html, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))

    def test_atomic_csv_write_leaves_no_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "table.csv"
            atomic_write_csv(pd.DataFrame({"value": [1, 2]}), path)
            self.assertTrue(path.exists())
            self.assertEqual(pd.read_csv(path)["value"].tolist(), [1, 2])
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
