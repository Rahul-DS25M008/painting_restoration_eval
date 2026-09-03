"""Focused checks for the post-notebook, read-only numerical dashboard view."""

import ast
import subprocess
import unittest
from pathlib import Path

import pandas as pd

from restoration_eval.dashboard_application import load_dashboard_package
from restoration_eval.dashboard_metrics import (
    METRIC_SOURCES, aggregate_metric_records, attach_candidate_identity,
    candidate_seed_metadata, load_case_metric_rows, metric_source_path,
)


ROOT = Path(__file__).resolve().parents[1]


class DashboardMetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load_dashboard_package(ROOT)
        cls.case_id = "canonical__p001__loss_large"
        cls.catalog = cls.bundle.indexes["case_index"]
        cls.case = cls.catalog[cls.catalog.case_id.eq(cls.case_id)]
        cls.seeds = candidate_seed_metadata(ROOT, cls.case_id)

    def test_all_families_preserve_values_and_identity(self):
        for family in METRIC_SOURCES:
            with self.subTest(family=family):
                raw = load_case_metric_rows(ROOT, self.case_id, family)
                shown, missing = attach_candidate_identity(raw, self.case, self.seeds)
                self.assertFalse(shown.empty)
                self.assertTrue(missing.empty)
                self.assertEqual(set(shown.candidate_id), set(self.case.candidate_id))
                self.assertEqual(set(shown.case_id), {self.case_id})
                for col in ["damaged_value", "restored_value", "improvement_value"]:
                    expected = raw.set_index("source_record_id")[col].loc[shown.source_record_id]
                    pd.testing.assert_series_equal(expected.reset_index(drop=True),
                                                   shown[col].reset_index(drop=True))
                self.assertTrue(shown.better_direction.isin(
                    ["Higher is better", "Lower is better", "See metric definition", "Not applicable — do not rank"]).all())

    def test_damage_size_extension_does_not_inherit_anchor_scores(self):
        case_id = "damage_size__p001__loss_large__size_02pct"
        catalog = self.catalog[self.catalog.case_id.eq(case_id)]
        raw = load_case_metric_rows(ROOT, case_id, "Classical metrics")
        shown, missing = attach_candidate_identity(raw, catalog, candidate_seed_metadata(ROOT, case_id))
        self.assertEqual(len(missing), 3)
        self.assertEqual(set(missing.seed), {"2027", "2028", "2029"})
        self.assertTrue(set(missing.candidate_id).isdisjoint(shown.candidate_id))
        self.assertEqual(set(shown.loc[shown.model_id.eq("stable_diffusion_inpainting"), "seed"]), {"2026"})

    def test_prompt_arms_are_not_mixed(self):
        case_id = "canonical__p001__scratch_thin"
        catalog = self.catalog[self.catalog.case_id.eq(case_id)]
        raw = load_case_metric_rows(ROOT, case_id, "Classical metrics")
        shown, missing = attach_candidate_identity(raw, catalog, candidate_seed_metadata(ROOT, case_id))
        self.assertTrue(missing.empty)
        sd = shown[shown.model_id.eq("stable_diffusion_inpainting")]
        self.assertEqual(sd.prompt_variant_id.nunique(), 2)
        self.assertEqual(sd.groupby("candidate_id").seed.nunique().max(), 1)
        self.assertEqual(sd.groupby("candidate_id").prompt_variant_id.nunique().max(), 1)

    def test_duplicate_identity_rejected(self):
        raw = load_case_metric_rows(ROOT, self.case_id, "Classical metrics")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            attach_candidate_identity(raw, pd.concat([self.case, self.case.iloc[:1]]), self.seeds)

    def test_missing_seed_rejected(self):
        raw = load_case_metric_rows(ROOT, self.case_id, "Classical metrics")
        with self.assertRaisesRegex(ValueError, "seed provenance"):
            attach_candidate_identity(raw, self.case, self.seeds.iloc[:0])

    def test_non_applicability_and_infinity_preserved(self):
        case_id = "canonical__p001__zero_control"
        raw = load_case_metric_rows(ROOT, case_id, "Classical metrics")
        self.assertTrue(raw.loc[raw.metric_name.eq("psnr"), "restored_value"].eq(float("inf")).any())
        local = load_case_metric_rows(ROOT, self.case_id, "Colour, seam & texture")
        self.assertTrue(local.status.eq("not_applicable").any())
        self.assertTrue(local.loc[local.status.eq("not_applicable"), "better_direction"].eq(
            "Not applicable — do not rank").all())

    def test_aggregate_values_unchanged(self):
        source = self.bundle.tables["performance_summary"]
        source = source[source.population_id.eq("core_three_model")]
        result = aggregate_metric_records(source)
        pd.testing.assert_frame_equal(result, source[result.columns])

    def test_other_existing_page_functions_unchanged(self):
        original = subprocess.check_output(["git", "show", "HEAD:streamlit_app.py"], cwd=ROOT).decode()
        current = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        old = {n.name: ast.dump(n) for n in ast.parse(original).body if isinstance(n, ast.FunctionDef)}
        new = {n.name: ast.dump(n) for n in ast.parse(current).body if isinstance(n, ast.FunctionDef)}
        # Reports has only the separately approved live-deployment note update.
        allowed = {"render_model_performance", "render_case_explorer", "render_reports"}
        for name, code in old.items():
            if name not in allowed:
                self.assertEqual(code, new[name], name)


if __name__ == "__main__":
    unittest.main()
