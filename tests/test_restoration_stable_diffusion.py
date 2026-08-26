from __future__ import annotations

import copy
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval import restoration_stable_diffusion as stable_diffusion_module
from restoration_eval.restoration_stable_diffusion import (
    RESTORATION_GENERATOR_VERSION,
    binarize_mask,
    build_candidate_plan,
    build_eligible_case_worklist,
    build_prompt_ablation_design,
    build_prompt_policy,
    load_stable_diffusion_config,
    masked_composite,
    run_stable_diffusion_candidate,
    select_prompt_ablation_cases,
    select_uncertainty_cases,
)


CONFIG_PATH = Path("config/experiments/stable_diffusion.yaml")
CASE_REGISTRY_PATH = Path("outputs/08_experiment_contracts_and_region_policy/data/case_registry.csv")
MODEL_ELIGIBILITY_PATH = Path("outputs/08_experiment_contracts_and_region_policy/data/model_eligibility.csv")
ARTWORKS_PATH = Path("outputs/01_dataset_verification/data/artworks.csv")


class StableDiffusionRestorationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_stable_diffusion_config(CONFIG_PATH)
        cls.cases = pd.read_csv(CASE_REGISTRY_PATH)
        cls.eligibility = pd.read_csv(MODEL_ELIGIBILITY_PATH)
        cls.artworks = pd.read_csv(ARTWORKS_PATH)
        cls.worklist = build_eligible_case_worklist(
            cls.cases, cls.eligibility, cls.artworks, cls.config
        )

    def test_configuration_freezes_approved_method(self) -> None:
        model = self.config["model"]
        self.assertEqual(model["hf_model_id"], "stable-diffusion-v1-5/stable-diffusion-inpainting")
        self.assertEqual(model["model_revision"], "8a4288a76071f7280aedbdb3253bdb9e9d5d84bb")
        self.assertEqual(model["scheduler"], "DDIMScheduler")
        self.assertEqual(model["num_inference_steps"], 30)
        self.assertEqual(model["guidance_scale"], 7.5)
        self.assertEqual(model["strength"], 1.0)
        self.assertEqual(model["retry_seed_policy"], "preserve_exact_seed")
        self.assertFalse(model["allow_cpu_fallback"])
        self.assertEqual(self.config["execution"]["progress_interval_candidates"], 10)
        self.assertEqual(RESTORATION_GENERATOR_VERSION, "5.1.0")

    def test_real_upstream_contract_builds_exact_worklist(self) -> None:
        self.assertEqual(len(self.worklist), 410)
        self.assertEqual(int(self.worklist["is_zero_control"].sum()), 50)
        self.assertEqual(
            self.worklist.groupby("experiment_id").size().to_dict(),
            {
                "canonical_missing_region": 250,
                "damage_size_sensitivity": 35,
                "mask_robustness": 75,
                "synthetic_degradation": 50,
            },
        )

    def test_prompt_policy_and_design_have_exact_declared_cardinality(self) -> None:
        policy = build_prompt_policy(self.config)
        prompt_cases = select_prompt_ablation_cases(self.worklist, self.config)
        uncertainty_cases = select_uncertainty_cases(self.worklist, self.config)
        design = build_prompt_ablation_design(prompt_cases, uncertainty_cases, self.config)
        self.assertEqual(len(policy), 5)
        self.assertEqual(len(prompt_cases), 120)
        self.assertFalse(prompt_cases["is_zero_control"].any())
        self.assertFalse(
            prompt_cases["artist"].astype(str).str.strip().str.lower().eq("unknown").any()
        )
        self.assertEqual(len(uncertainty_cases), 40)
        self.assertEqual(uncertainty_cases.groupby("category")["painting_id"].nunique().to_dict(), {
            category: 2 for category in sorted(self.artworks["category"].unique())
        })
        self.assertEqual(len(design), 160)
        self.assertEqual(design.groupby("design_component").size().to_dict(), {
            "prompt_ablation": 120, "uncertainty": 40
        })

    def test_candidate_plan_is_exact_and_primary_is_never_metric_selected(self) -> None:
        prompt_cases = select_prompt_ablation_cases(self.worklist, self.config)
        uncertainty_cases = select_uncertainty_cases(self.worklist, self.config)
        candidates = build_candidate_plan(
            self.worklist, prompt_cases, uncertainty_cases, self.config
        )
        self.assertEqual(len(candidates), 1010)
        self.assertTrue(candidates["candidate_id"].is_unique)
        self.assertEqual(candidates.groupby("execution_role").size().to_dict(), {
            "primary": 410,
            "prompt_context": 480,
            "uncertainty_extension": 120,
        })
        primary = candidates.loc[candidates["is_primary_candidate"]]
        self.assertEqual(set(primary["seed"]), {2026})
        self.assertEqual(set(primary["prompt_variant_id"]), {"p00_generic"})
        self.assertEqual(primary.groupby("case_id").size().max(), 1)
        self.assertEqual(int(primary["case_id"].str.contains("zero_control").sum()), 50)
        inference_count = int((~primary["case_id"].str.contains("zero_control")).sum())
        self.assertEqual(inference_count, 360)
        self.assertEqual(
            set(candidates["candidate_selection_policy"]),
            {"deterministic_hash_stratified_non_metric.v1"},
        )
        self.assertEqual(
            set(candidates["prompt_variant_id"]),
            {
                "p00_generic", "p01_category", "p02_artist",
                "p03_artist_category", "p04_full_context",
            },
        )
        contextual = candidates.loc[candidates["execution_role"].eq("prompt_context")]
        self.assertFalse(contextual["prompt"].str.contains("unknown", case=False).any())
        self.assertFalse(contextual["prompt"].str.contains("style_or_period", case=False).any())
        output_root = Path.cwd() / "outputs" / self.config["output"]["notebook_stem"]
        maximum_path_length = candidates["restored_path"].map(
            lambda value: len(str(output_root / value))
        ).max()
        self.assertLess(maximum_path_length, 240)

    def test_inclusive_mask_threshold_and_exact_outside_composite(self) -> None:
        mask = np.array([[12, 13], [127, 128]], dtype=np.uint8)
        binary = binarize_mask(mask, 13)
        np.testing.assert_array_equal(binary, np.array([[0, 255], [255, 255]], dtype=np.uint8))
        source = np.zeros((2, 2, 3), dtype=np.uint8)
        generated = np.full((2, 2, 3), 200, dtype=np.uint8)
        output = masked_composite(source, generated, binary)
        np.testing.assert_array_equal(output[0, 0], source[0, 0])
        np.testing.assert_array_equal(output[0, 1], generated[0, 1])

    def test_retry_recreates_exact_seed(self) -> None:
        config = copy.deepcopy(self.config)
        config["model"]["maximum_retries"] = 1
        observed_seeds: list[int] = []

        class FailOncePipeline:
            def __init__(self) -> None:
                self.calls = 0

            def __call__(self, **kwargs):
                self.calls += 1
                observed_seeds.append(kwargs["generator"])
                if self.calls == 1:
                    raise RuntimeError("transient test failure")
                image = Image.new("RGB", (512, 512), (80, 80, 80))
                return SimpleNamespace(images=[image])

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = root / "inputs"
            inputs.mkdir()
            source = np.zeros((16, 16, 3), dtype=np.uint8)
            mask = np.zeros((16, 16), dtype=np.uint8)
            mask[4:12, 4:12] = 255
            Image.fromarray(source, mode="RGB").save(inputs / "input.png")
            Image.fromarray(mask, mode="L").save(inputs / "mask.png")
            candidate = {
                "candidate_id": "test", "input_image_path": "inputs/input.png",
                "mask_or_effect_path": "inputs/mask.png", "mask_threshold": 128,
                "output_width": 16, "output_height": 16,
                "inference_width": 512, "inference_height": 512,
                "restored_path": "images/restored/test.png", "seed": 2026,
                "prompt": "test prompt", "negative_prompt": "test negative",
                "num_inference_steps": 30, "guidance_scale": 7.5, "strength": 1.0,
            }
            record = run_stable_diffusion_candidate(
                candidate, pipeline=FailOncePipeline(), device="cpu",
                project_root=root, notebook_output_root=root / "outputs", config=config,
                generator_factory=lambda _device, seed: seed,
            )
            self.assertEqual(observed_seeds, [2026, 2026])
            self.assertEqual(record["retry_count"], 1)
            self.assertEqual(record["status"], "completed")

    def test_atomic_checkpoint_retries_transient_permission_error(self) -> None:
        frame = pd.DataFrame(
            [
                {"candidate_id": "candidate_001", "status": "completed"},
                {"candidate_id": "candidate_002", "status": "completed"},
            ]
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            checkpoint = Path(temporary_directory) / "candidate_checkpoint.csv"
            original_replace = Path.replace
            replace_attempts = {"count": 0}

            def transiently_locked_replace(source: Path, target: Path) -> Path:
                replace_attempts["count"] += 1
                if replace_attempts["count"] <= 2:
                    raise PermissionError("simulated transient Windows file lock")
                return original_replace(source, target)

            with (
                patch.object(
                    Path,
                    "replace",
                    autospec=True,
                    side_effect=transiently_locked_replace,
                ),
                patch.object(stable_diffusion_module.time, "sleep") as sleep_mock,
            ):
                stable_diffusion_module._atomic_checkpoint(frame, checkpoint)

            reloaded = pd.read_csv(checkpoint)
            self.assertTrue(reloaded.equals(frame))
            self.assertEqual(replace_attempts["count"], 3)
            self.assertEqual(
                [item.args[0] for item in sleep_mock.call_args_list], [0.125, 0.25]
            )
            self.assertFalse(checkpoint.with_suffix(".csv.tmp").exists())

if __name__ == "__main__":
    unittest.main()
