"""D04 contract regressions; read saved inputs, never run models or notebooks."""
import copy
import hashlib
import json
import unittest
from pathlib import Path

import pandas as pd
import yaml

from restoration_eval import real_damage_restoration as d04


class RealDamageRestorationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.config = d04.load_restoration_config(cls.root / "config/experiments/real_damage_restoration.yaml")
        cls.catalog = d04.load_prompt_catalog(cls.root / cls.config["inputs"]["prompt_catalog"])
        base = cls.root / "outputs/d03_real_damage_dataset_preparation"
        cls.manifest = json.loads((base / "manifests/run_manifest.json").read_text(encoding="utf-8"))
        cls.cases = pd.read_csv(base / "data/case_registry.csv")
        cls.eligibility = pd.read_csv(base / "data/model_eligibility.csv")
        cls.baselines = {mid: yaml.safe_load((cls.root / rel).read_text(encoding="utf-8-sig"))
                         for mid, rel in cls.config["models"].items()}

    def prompts(self, catalog=None):
        return d04.validate_prompt_catalog(catalog or self.catalog, self.cases, self.manifest, self.config)

    def plan(self, prompts=None, eligibility=None):
        return d04.build_candidate_plan(self.cases, self.eligibility if eligibility is None else eligibility,
                                       self.prompts() if prompts is None else prompts, self.baselines, self.config)

    def test_exact_population_roles_and_deterministic_ids(self):
        first, second = self.plan(), self.plan()
        pd.testing.assert_frame_equal(first, second)
        self.assertEqual(len(first), 70)
        self.assertEqual(first.candidate_role.value_counts().to_dict(), {"primary": 40, "additional_seed": 30})
        self.assertTrue(first.candidate_id.is_unique)
        self.assertTrue(first.restored_path.is_unique)
        primary = first[first.candidate_role.eq("primary")]
        self.assertEqual(primary.groupby("model_id").size().to_dict(), {m: 10 for m in d04.PRIMARY_MODELS})
        self.assertFalse(first.has_clean_reference.any())
        self.assertFalse(first.reference_fidelity_metrics_applicable.any())
        self.assertTrue(first.clean_image_path.eq("").all())
        self.assertTrue(first.status.eq("planned_not_executed").all())

    def test_seed_groups_hold_one_targeted_prompt_and_negative(self):
        plan = self.plan()
        sd = plan[plan.model_id.eq(d04.SD_MODEL)]
        self.assertEqual(sd.uncertainty_group_id.nunique(), 10)
        self.assertEqual(sum(len(g) * (len(g) - 1) // 2 for _, g in sd.groupby("uncertainty_group_id")), 60)
        for _, group in sd.groupby("painting_id"):
            self.assertEqual(set(group.seed), {2026, 2027, 2028, 2029})
            self.assertEqual(group.prompt.nunique(), 1)
            self.assertEqual(group.negative_prompt.nunique(), 1)
        self.assertEqual(sd.prompt.nunique(), 10)
        self.assertTrue(sd.configuration_id.eq(d04.SD_CONFIGURATION_ID).all())
        self.assertTrue(sd.negative_prompt.eq(self.baselines[d04.SD_MODEL]["prompt_policy"]["negative_prompt"]).all())

    def test_effective_settings_do_not_mutate_baseline_or_change_model_parameters(self):
        before = copy.deepcopy(self.baselines)
        for mid, baseline in self.baselines.items():
            effective = d04.effective_model_config(baseline, mid, self.config)
            if mid == d04.SD_MODEL:
                self.assertNotIn("generic_prompt", effective["prompt_policy"])
                self.assertTrue(effective["prompt_policy"]["requires_explicit_candidate_prompt"])
                effective["model"]["configuration_id"] = baseline["model"]["configuration_id"]
                self.assertEqual(effective["model"], baseline["model"])
            else:
                self.assertEqual(effective, baseline)
        self.assertEqual(before, self.baselines)

    def test_prompt_digest_tampering_is_rejected(self):
        catalog = copy.deepcopy(self.catalog)
        catalog["records"][0]["prompt"] += " different"
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.prompts(catalog)

    def test_swapped_mask_or_image_binding_is_rejected(self):
        for key in ("case_id", "input_image_sha256", "mask_sha256", "mask_path"):
            with self.subTest(key=key):
                catalog = copy.deepcopy(self.catalog)
                catalog["records"][0][key] = catalog["records"][1][key]
                with self.assertRaisesRegex(ValueError, "binding"):
                    self.prompts(catalog)

    def test_duplicate_missing_or_generic_prompts_are_rejected(self):
        for mutation in ("missing", "duplicate", "generic"):
            with self.subTest(mutation=mutation):
                catalog = copy.deepcopy(self.catalog)
                if mutation == "missing":
                    catalog["records"].pop()
                elif mutation == "duplicate":
                    catalog["records"][1] = copy.deepcopy(catalog["records"][0])
                else:
                    for key in ("prompt", "prompt_sha256"):
                        catalog["records"][1][key] = catalog["records"][0][key]
                with self.assertRaises(ValueError):
                    self.prompts(catalog)

    def test_reference_and_outcome_based_prompt_provenance_are_rejected(self):
        for key in ("known_clean_images_consulted", "restoration_outputs_consulted"):
            catalog = copy.deepcopy(self.catalog)
            catalog[key] = True
            with self.assertRaisesRegex(ValueError, "provenance"):
                self.prompts(catalog)

    def test_changed_prompt_invalidates_only_that_paintings_SD_identities(self):
        before = self.plan()
        catalog = copy.deepcopy(self.catalog)
        catalog["records"][0]["prompt"] += " Subtle shading."
        catalog["records"][0]["prompt_sha256"] = hashlib.sha256(catalog["records"][0]["prompt"].encode()).hexdigest()
        after = self.plan(self.prompts(catalog))
        changed = before.candidate_id.ne(after.candidate_id)
        expected = before.painting_id.eq("rd001") & before.model_id.eq(d04.SD_MODEL)
        self.assertTrue(changed.equals(expected))
        self.assertEqual(changed.sum(), 4)

    def test_eligibility_holes_duplicates_and_false_values_block_planning(self):
        missing = self.eligibility.iloc[:-1].copy()
        duplicate = self.eligibility.copy()
        duplicate.iloc[1] = duplicate.iloc[0]
        false = self.eligibility.copy()
        false.loc[0, "eligible"] = False
        for frame in (missing, duplicate, false):
            with self.subTest(rows=len(frame)), self.assertRaises(ValueError):
                self.plan(eligibility=frame)

    def test_mismatched_runtime_worklist_bindings_block(self):
        frame = self.eligibility.copy()
        frame.loc[0, "mask_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "binding mismatch"):
            self.plan(eligibility=frame)

    def test_unsafe_output_paths_block(self):
        for path in ("../D03/file.png", "C:/elsewhere/file.png", "/tmp/file.png", ".codex_tmp/file.png"):
            config = copy.deepcopy(self.config)
            config["outputs"]["restored_template"] = path
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "Unsafe"):
                d04.validate_restoration_config(config)

    def test_prompt_seed_and_comparison_contract_regressions_block(self):
        changes = [("prompt_policy", "fixed_across_seeds", False),
                   ("prompt_policy", "outcome_based_tuning", True),
                   ("candidate_design", "total_candidates", 40),
                   ("comparison", "pool_real_and_synthetic_metrics", True),
                   ("comparison", "same_prompt_domain_effect_claim_allowed", True),
                   ("evaluation", "input_as_clean_reference", True),
                   ("execution", "assistant_executes_notebook", True)]
        for group, key, value in changes:
            config = copy.deepcopy(self.config)
            config[group][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                d04.validate_restoration_config(config)


if __name__ == "__main__":
    unittest.main()
