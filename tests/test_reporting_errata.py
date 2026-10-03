"""Regression gates for the explicit post-publication overlay, not a new N33 run."""
import hashlib
import json
from pathlib import Path
import unittest

import pandas as pd

from restoration_eval.final_evaluation_report import quality_population_metadata

ROOT = Path(__file__).resolve().parents[1]
ERRATA = ROOT / "docs/errata/2026-10-03"


class ReportingErrataTests(unittest.TestCase):
    def test_population_helper_does_not_replace_every_denominator(self):
        ordinary = quality_population_metadata("classical_masked_mae", 2320, 300, 2620)
        affinity = quality_population_metadata("structural_affinity_correlation", 2620, 300, 2620)
        self.assertFalse(ordinary["values"]["controls_included"])
        self.assertTrue(affinity["values"]["controls_included"])
        self.assertEqual(ordinary["values"]["population_case_count"], 2620)
        self.assertEqual(ordinary["values"]["measured_case_count"], 2320)
        self.assertIn("case-weighted", affinity["denominator"])

    def test_corrected_rows_preserve_numerical_evidence(self):
        original = pd.read_csv(ROOT / "outputs/33_final_evaluation_report/data/thesis_tables.csv").set_index("table_row_id")
        corrected = pd.read_csv(ERRATA / "corrected_thesis_rows.csv")
        self.assertEqual(corrected.groupby("table_id").size().to_dict(), {
            "t04_quality_anchor_summary": 44, "t05_metric_disagreement": 11,
            "t10_grouped_statistics": 22, "t15_limitations": 1,
        })
        for row in corrected.itertuples():
            old = original.loc[row.table_row_id.removeprefix("errata_20261003__")]
            old_values, new_values = json.loads(old.values_json), json.loads(row.values_json)
            for field, value in old_values.items():
                if field not in {"eligible_case_count", "limitation_id"}:
                    self.assertEqual(new_values[field], value)
            if row.table_id in {"t04_quality_anchor_summary", "t05_metric_disagreement"}:
                includes_controls = "structural_affinity_correlation" in row.row_key
                self.assertEqual(new_values["measured_case_count"], 2620 if includes_controls else 2320)
                self.assertEqual(new_values["controls_included"], includes_controls)
                self.assertEqual(new_values["aggregation_rule"], "case_weighted_mean")
            if row.table_id == "t10_grouped_statistics":
                canonical = row.row_key.startswith("omnibus__")
                self.assertEqual(new_values["n_cases"], 1200 if canonical else 2320)
                self.assertEqual(row.scope, "canonical_nonzero_core" if canonical else "all_nonzero_primary_core")

    def test_statistical_corrections_are_metadata_only(self):
        original = pd.read_csv(ROOT / "outputs/26_grouped_and_statistical_analysis/metrics/statistical_results.csv", dtype={"source_notebook_ids": str}, float_precision="round_trip").set_index("result_id")
        corrected = pd.read_csv(ERRATA / "corrected_statistical_rows.csv", dtype={"source_notebook_ids": str}, float_precision="round_trip")
        self.assertEqual(len(corrected), 77)
        self.assertTrue(corrected.n_cases.eq(1200).all())
        self.assertTrue(corrected.population_id.eq("canonical_nonzero_core").all())
        for row in corrected.itertuples(index=False):
            old = original.loc[row.result_id.removeprefix("errata_20261003__")]
            for field in original.columns:
                if field in {"experiment_id", "population_id", "n_cases"}:
                    continue
                expected, actual = old[field], getattr(row, field)
                if pd.isna(expected):
                    self.assertTrue(pd.isna(actual))
                elif isinstance(expected, float):
                    import math
                    self.assertTrue(math.isclose(expected, actual, rel_tol=1e-13, abs_tol=0), (field, expected, actual))
                else:
                    self.assertEqual(expected, actual)

    def test_current_producer_matches_population_corrections(self):
        from restoration_eval.final_evaluation_report import build_final_thesis_tables, load_final_evaluation_config
        config = load_final_evaluation_config(ROOT / "config/evaluation/final_evaluation_report.yaml")
        settings = config["final_evaluation_report"]
        sources = {key: pd.read_csv(ROOT / settings["inputs"][key], low_memory=False, float_precision="round_trip")
                   for key in settings["input_table_contracts"]}
        rebuilt = build_final_thesis_tables(sources, config).set_index("table_row_id")
        corrected = pd.read_csv(ERRATA / "corrected_thesis_rows.csv")
        for row in corrected.itertuples():
            produced = rebuilt.loc[row.table_row_id.removeprefix("errata_20261003__")]
            for field in ["scope", "denominator", "independent_unit", "row_label"]:
                self.assertEqual(produced[field], getattr(row, field), (row.row_key, field))
            before, after = json.loads(row.values_json), json.loads(produced.values_json)
            for field in ["n_cases", "measured_case_count", "controls_included", "aggregation_rule", "limitation_id"]:
                if field in before:
                    self.assertEqual(before[field], after[field], (row.row_key, field))

    def test_export_source_includes_canonical_tests_without_rewriting_outputs(self):
        notebook = json.loads((ROOT / "notebooks/26_grouped_and_statistical_analysis.ipynb").read_text(encoding="utf-8"))
        source = next("".join(c["source"]) for c in notebook["cells"] if "canonical_only = result_kind in" in "".join(c["source"]))
        import ast
        assignment = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "canonical_only" for t in n.targets))
        kinds = ast.literal_eval(assignment.value.comparators[0])
        self.assertIn("repeated_model_test", kinds)
        self.assertIn("paired_model_contrast", kinds)
        self.assertNotIn("quality_compute_association", kinds)

    def test_all_omnibus_values_verified_and_exports_hashed(self):
        checks = json.loads((ERRATA / "statistical_verification.json").read_text())
        self.assertEqual(len(checks), 11)
        self.assertTrue(all(r["matches_saved"] and r["n_paintings"] == 300 and r["n_cases"] == 1200 for r in checks))
        receipt = json.loads((ERRATA / "verification.json").read_text())
        for name, expected in receipt["output_sha256"].items():
            self.assertEqual(hashlib.sha256((ERRATA / name).read_bytes()).hexdigest(), expected, name)

    def test_case_examples_have_exact_source_rows_and_both_outcomes(self):
        examples = json.loads((ERRATA / "framework_examples.json").read_text())
        for key in ["structural_perceptual_disagreement", "unchanged_winner"]:
            case = examples[key]
            self.assertEqual(len(case["candidate_comparison"]), 4)
            self.assertEqual(len(case["source_rows"]), 16)
            self.assertTrue(all(r["source_row_id"] and r["source_path"] for r in case["source_rows"]))
            rows = {r["model_id"]: r for r in case["candidate_comparison"]}
            chosen = rows[case["model_id"]]
            self.assertEqual(chosen["structural_crop_ssim"], max(r["structural_crop_ssim"] for r in rows.values()))
            lpips = [r["perceptual_crop_lpips"] for r in rows.values()]
            self.assertEqual(chosen["perceptual_crop_lpips"], max(lpips) if key.startswith("structural") else min(lpips))


if __name__ == "__main__":
    unittest.main()
