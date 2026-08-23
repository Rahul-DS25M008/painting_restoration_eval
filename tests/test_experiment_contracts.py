from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from restoration_eval.experiment_contracts import (
    build_case_registry,
    build_model_eligibility,
    build_region_policy,
    build_schema_registry_payload,
    load_evaluation_contract_config,
)


CONFIG_PATH = Path("config/experiments/evaluation_contract.yaml")


class ExperimentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_evaluation_contract_config(CONFIG_PATH)

    def _source_frames(self) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
        common = {
            "dataset_id": "painting_restoration_eval",
            "dataset_scope": "controlled_50",
            "painting_id": "p001",
            "clean_image_path": "outputs/02_image_preprocessing/images/clean/p001.png",
            "status": "passed",
        }
        canonical = pd.DataFrame(
            [
                {
                    **common,
                    "experiment_id": "canonical_missing_region",
                    "case_id": "canonical__p001__loss_small",
                    "damaged_image_path": "outputs/04/images/damaged.png",
                    "mask_id": "mask__canonical__p001__loss_small",
                    "mask_path": "outputs/03/images/mask.png",
                }
            ]
        )
        canonical_masks = pd.DataFrame(
            [
                {
                    "case_id": "canonical__p001__loss_small",
                    "target_damaged_content_fraction": 0.05,
                    "damaged_content_fraction": 0.0501,
                }
            ]
        )
        damage_size = pd.DataFrame(
            [
                {
                    **common,
                    "experiment_id": "damage_size_sensitivity",
                    "case_id": "damage_size__p001__size_02pct",
                    "input_image_path": "outputs/05/images/damaged.png",
                    "mask_or_effect_id": "mask__damage_size__p001",
                    "mask_or_effect_path": "outputs/05/images/mask.png",
                    "target_damage_fraction": 0.02,
                    "realized_damage_fraction": 0.02001,
                    "damage_or_degradation_type": "binary_missing_region",
                }
            ]
        )
        robustness = pd.DataFrame(
            [
                {
                    **common,
                    "experiment_id": "mask_robustness",
                    "case_id": "mask_robustness__p001__variant_01",
                    "damaged_image_path": "outputs/06/images/damaged.png",
                    "mask_id": "mask__robustness__p001__variant_01",
                    "mask_path": "outputs/06/images/mask.png",
                    "target_damage_fraction": 0.02,
                    "realized_damage_fraction": 0.02,
                }
            ]
        )
        synthetic = pd.DataFrame(
            [
                {
                    **common,
                    "experiment_id": "synthetic_degradation",
                    "case_id": "synthetic__p001__water_stain__mild",
                    "degraded_image_path": "outputs/07/images/water.png",
                    "degradation_id": "water_stain__mild",
                    "effect_mask_path": "outputs/07/masks/water.png",
                    "degradation_family": "water_stain",
                    "affected_content_fraction": 0.1,
                },
                {
                    **common,
                    "experiment_id": "synthetic_degradation",
                    "case_id": "synthetic__p001__gaussian_blur__mild",
                    "degraded_image_path": "outputs/07/images/blur.png",
                    "degradation_id": "gaussian_blur__mild",
                    "effect_mask_path": "outputs/07/masks/blur.png",
                    "degradation_family": "gaussian_blur",
                    "affected_content_fraction": 1.0,
                },
            ]
        )
        return (
            {
                "canonical_missing_region": canonical,
                "damage_size_sensitivity": damage_size,
                "mask_robustness": robustness,
                "synthetic_degradation": synthetic,
            },
            canonical_masks,
        )

    def test_case_registry_and_eligibility_are_normalized(self) -> None:
        frames, canonical_masks = self._source_frames()
        manifests = {
            experiment_id: f"outputs/{index:02d}/manifests/run_manifest.json"
            for index, experiment_id in enumerate(frames, start=4)
        }
        registry = build_case_registry(
            frames,
            source_manifest_paths=manifests,
            canonical_masks=canonical_masks,
        )
        self.assertEqual(len(registry), 5)
        self.assertTrue(registry["case_id"].is_unique)
        self.assertEqual(registry["source_manifest_path"].nunique(), 4)
        eligibility = build_model_eligibility(registry, self.config)
        self.assertEqual(len(eligibility), 20)
        self.assertEqual(int(eligibility["eligible"].sum()), 16)
        blur = eligibility[
            eligibility["case_id"] == "synthetic__p001__gaussian_blur__mild"
        ]
        self.assertFalse(blur["eligible"].any())
        self.assertTrue(blur["eligibility_reason"].str.contains("Blur").all())

    def test_region_policy_is_complete_and_prohibits_sparse_ssim(self) -> None:
        policy = build_region_policy(self.config)
        self.assertEqual(len(policy), 143)
        self.assertFalse(policy.duplicated(["metric_family", "region_id"]).any())
        sparse_ssim = policy[
            (policy["metric_family"] == "ssim")
            & (policy["region_id"] == "masked_region")
        ].iloc[0]
        self.assertFalse(bool(sparse_ssim["compatible"]))
        self.assertIn("sparse masked pixels", sparse_ssim["compatibility_reason"])

    def test_schema_registry_payload_is_serializable(self) -> None:
        payload = build_schema_registry_payload()
        names = {schema["name"] for schema in payload["schemas"]}
        self.assertTrue(
            {"case_registry", "model_eligibility", "region_policy"}.issubset(names)
        )


if __name__ == "__main__":
    unittest.main()
