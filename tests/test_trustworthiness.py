"""Bounded read-only regressions, not a painting-by-painting inference run."""
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from restoration_eval.trustworthiness import (ROOT, OPENING, candidate_index,
    payload, assignment_records, threshold_record)
from restoration_eval.dashboard_application import open_dashboard_package
import pandas as pd


class TrustworthinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("Loading recorded Tab 6 tables once; no inference or scientific recomputation.", flush=True)
        cls.package = open_dashboard_package(ROOT)
        cls.data = payload(cls.package)

    def test_exact_opening_identity(self):
        c = self.data["candidate"]
        self.assertEqual(c["candidate_id"], OPENING)
        self.assertEqual(c["case_id"], "canonical__p002__loss_large")
        self.assertEqual(c["seed"], 2026)
        self.assertEqual(c["prompt_variant_id"], "p00_generic")

    def test_complete_union_roles(self):
        counts = Counter(r["population_role"] for r in candidate_index().values())
        self.assertEqual(sum(counts.values()), 13879)
        self.assertEqual(counts["primary_and_uncertainty"], 725)
        self.assertEqual(counts["uncertainty_only"], 3375)
        self.assertEqual(counts["bounded_sdxl"], 24)
        self.assertEqual(counts["primary_comparison"], 9755)

    def test_primary_peers_exclude_extra_seeds_and_sdxl(self):
        self.assertEqual(len(self.data["peers"]), 4)
        self.assertEqual({r["case_id"] for r in self.data["peers"]}, {"canonical__p002__loss_large"})
        sd = next(r for r in self.data["peers"] if r["model"] == "Stable Diffusion")
        self.assertEqual(sd["candidate_id"], OPENING)

    def test_exact_threshold_and_registered_stratum(self):
        t = self.data["thresholds"]["texture_smoothing"]["local_texture_error_p95"]
        self.assertEqual(t["observed"], 10.053275680541985)
        self.assertEqual(t["critical"], 4.8924025321006255)
        self.assertEqual(t["warning"], 1.7923734879493693)
        self.assertEqual(t["stratum"]["fitting_population_count"], 4800)
        self.assertEqual(t["stratum"]["threshold_stratum_id"], "threshold_fb3035ff49e0b5b77d7b")
        self.assertEqual(t["state"], "critical")

    def test_all_six_flags_and_unresolved_colour(self):
        flags = self.data["flags"]
        self.assertEqual(len(flags), 11)
        self.assertEqual({r["flag_id"] for r in flags if r["flag_status"] == "triggered"},
                         {"high_generative_uncertainty", "texture_inconsistency", "restoration_instability",
                          "metric_disagreement", "insufficient_evidence", "manual_review_required"})
        self.assertEqual(next(r for r in flags if r["flag_id"] == "colour_inconsistency")["flag_status"], "insufficient_evidence")

    def test_complete_assignment_provenance(self):
        categories = self.data["categories"]
        self.assertEqual(len(categories), 14)
        ids = {r["assignment_id"] for r in categories}
        self.assertTrue(all(set(r["supporting_assignment_ids"]).issubset(ids) for r in self.data["flags"]))
        self.assertTrue(all(r["candidate_id"] == OPENING for r in categories))

    def test_missing_and_ambiguous_threshold_do_not_pass(self):
        category = next(r for r in self.data["categories"] if r["category_id"] == "colour_drift")
        frame = pd.read_parquet(self.package.verify_relative_file("data/derived/threshold_strata.parquet"))
        self.assertIsNone(threshold_record(category, "masked_hue_shift", frame))
        category = next(r for r in self.data["categories"] if r["category_id"] == "texture_smoothing")
        result = threshold_record(category, "local_texture_error_p95", pd.concat([frame, frame]))
        self.assertIsNone(result["stratum"])

    def test_unknown_candidate_rejected(self):
        with self.assertRaisesRegex(ValueError, "nothing substituted"):
            assignment_records("unknown-candidate")

    def test_seed_identity_is_preserved(self):
        index = candidate_index()
        rows = [r for r in index.values() if r["case_id"] == "canonical__p002__loss_large"
                and r["model_id"] == "stable_diffusion_inpainting"]
        self.assertEqual({r["seed"] for r in rows}, {2026,2027,2028,2029})
        self.assertEqual(len({r["candidate_id"] for r in rows}), 4)

    def test_policy_and_images_are_recorded(self):
        self.assertEqual(len(self.data["policy"]), 23)
        self.assertTrue(all(r["candidate_id"] == OPENING for r in self.data["policy"]))
        self.assertEqual(set(self.data["images"]), {"Clean", "Damaged", "Restored"})
        self.assertTrue(all(uri.startswith("data:image/") for uri in self.data["images"].values()))
        json.dumps(self.data, allow_nan=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
