from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from restoration_eval.restoration_stable_diffusion import (
    build_eligible_case_worklist,
    load_stable_diffusion_config,
    select_prompt_ablation_cases,
    select_uncertainty_cases,
)
from restoration_eval.restoration_stable_diffusion_scratch_prompt_contract import (
    SCRATCH_PROMPT_EXTENSION_VERSION,
    build_effective_candidate_plan,
    build_effective_prompt_ablation_design,
    build_effective_prompt_policy,
    build_effective_stable_diffusion_config,
    load_scratch_prompt_ablation_config,
    select_paired_scratch_matrix,
    select_scratch_prompt_cases,
)


BASE_CONFIG_PATH = Path("config/experiments/stable_diffusion.yaml")
SCRATCH_CONFIG_PATH = Path(
    "config/experiments/stable_diffusion_scratch_prompt_ablation.yaml"
)
CASE_REGISTRY_PATH = Path(
    "outputs/08_experiment_contracts_and_region_policy/data/case_registry.csv"
)
MODEL_ELIGIBILITY_PATH = Path(
    "outputs/08_experiment_contracts_and_region_policy/data/model_eligibility.csv"
)
ARTWORKS_PATH = Path("outputs/01_dataset_verification/data/artworks.csv")


class StableDiffusionScratchPromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = load_stable_diffusion_config(BASE_CONFIG_PATH)
        cls.scratch = load_scratch_prompt_ablation_config(SCRATCH_CONFIG_PATH)
        cls.effective = build_effective_stable_diffusion_config(
            cls.base, cls.scratch
        )
        cls.cases = pd.read_csv(CASE_REGISTRY_PATH)
        cls.eligibility = pd.read_csv(MODEL_ELIGIBILITY_PATH)
        cls.artworks = pd.read_csv(ARTWORKS_PATH)
        cls.worklist = build_eligible_case_worklist(
            cls.cases, cls.eligibility, cls.artworks, cls.base
        )
        cls.prompt_cases = select_prompt_ablation_cases(cls.worklist, cls.base)
        cls.uncertainty_cases = select_uncertainty_cases(cls.worklist, cls.base)
        cls.scratch_cases = select_scratch_prompt_cases(cls.worklist, cls.scratch)

    def test_base_contract_remains_frozen_and_effective_counts_are_explicit(self) -> None:
        self.assertEqual(self.base["expected"]["candidate_count"], 1010)
        self.assertNotIn("scratch_prompt_ablation", self.base)
        self.assertEqual(self.effective["expected"]["candidate_count"], 1330)
        self.assertEqual(
            self.effective["expected"]["model_inference_candidate_count"], 1280
        )
        self.assertEqual(self.effective["prompt_policy"]["policy_id"], "sd15_prompt_policy.v3")
        self.assertEqual(
            self.scratch["candidate_design"]["logical_execution_roles"],
            {
                "generic_extension": "scratch_seed_control_extension",
                "damage_prompt": "scratch_damage_prompt",
            },
        )

    def test_every_painting_has_one_canonical_scratch_case(self) -> None:
        self.assertEqual(len(self.scratch_cases), 50)
        self.assertEqual(self.scratch_cases["painting_id"].nunique(), 50)
        self.assertTrue(
            self.scratch_cases["case_id"].str.endswith("__scratch_thin").all()
        )
        self.assertEqual(
            set(self.scratch_cases["experiment_id"]), {"canonical_missing_region"}
        )
        self.assertFalse(self.scratch_cases["is_zero_control"].any())

    def test_effective_prompt_policy_records_damage_specific_treatment(self) -> None:
        policy = build_effective_prompt_policy(self.base, self.scratch)
        self.assertEqual(len(policy), 6)
        self.assertEqual(set(policy["prompt_policy_id"]), {"sd15_prompt_policy.v3"})
        treatment = policy.loc[
            policy["prompt_variant_id"].eq("p05_scratch_aware")
        ].iloc[0]
        self.assertNotIn("scratch", treatment["prompt_template"].lower())
        self.assertIn("scratch", treatment["negative_prompt"].lower())
        self.assertEqual(treatment["metadata_fields"], '["damage_or_degradation_type"]')

    def test_effective_design_adds_fifty_predeclared_paired_rows(self) -> None:
        design = build_effective_prompt_ablation_design(
            self.prompt_cases,
            self.uncertainty_cases,
            self.scratch_cases,
            self.base,
            self.scratch,
        )
        self.assertEqual(len(design), 210)
        added = design.loc[
            design["selection_policy"].eq(
                "all_canonical_paintings_paired_non_metric.v1"
            )
        ]
        self.assertEqual(len(added), 50)
        self.assertTrue(added["prompt_variant_count"].eq(2).all())
        self.assertTrue(added["seed_count"].eq(4).all())

    def test_candidate_plan_is_balanced_without_duplicate_inference(self) -> None:
        candidates = build_effective_candidate_plan(
            self.worklist,
            self.prompt_cases,
            self.uncertainty_cases,
            self.scratch_cases,
            self.base,
            self.scratch,
        )
        self.assertEqual(len(candidates), 1330)
        self.assertTrue(candidates["candidate_id"].is_unique)
        self.assertEqual(
            candidates.groupby("execution_role").size().to_dict(),
            {
                "primary": 410,
                "prompt_context": 680,
                "uncertainty_extension": 240,
            },
        )
        self.assertEqual(set(candidates["prompt_policy_id"]), {"sd15_prompt_policy.v3"})
        self.assertEqual(
            set(candidates["generator_version"]), {SCRATCH_PROMPT_EXTENSION_VERSION}
        )
        matrix = select_paired_scratch_matrix(candidates, self.scratch)
        self.assertEqual(len(matrix), 400)
        self.assertEqual(
            matrix.groupby("prompt_variant_id").size().to_dict(),
            {"p00_generic": 200, "p05_scratch_aware": 200},
        )
        self.assertTrue(matrix.groupby("case_id").size().eq(8).all())
        self.assertTrue(
            matrix.groupby(["case_id", "seed"])["prompt_variant_id"].nunique().eq(2).all()
        )
        p05 = matrix.loc[matrix["prompt_variant_id"].eq("p05_scratch_aware")]
        self.assertTrue(p05["negative_prompt"].str.contains("scratch", case=False).all())
        self.assertFalse(p05["prompt"].str.contains("scratch", case=False).any())
        extension = candidates.loc[
            candidates["candidate_selection_policy"].eq(
                "all_canonical_paintings_paired_non_metric.v1"
            )
        ]
        self.assertEqual(len(extension), 320)
        self.assertEqual(
            extension.groupby("prompt_variant_id").size().to_dict(),
            {"p00_generic": 120, "p05_scratch_aware": 200},
        )


if __name__ == "__main__":
    unittest.main()
