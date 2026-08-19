"""Focused preparation-layer tests for Notebook 06."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

import numpy as np

from restoration_eval.mask_robustness import (
    _group_stats,
    _pixel_sha,
    load_canonical_mask_config,
    load_mask_robustness_config,
    robustness_group_id,
    stable_case_seed,
    validate_mask_robustness_config,
)
from restoration_eval.damage_sensitivity import scale_mask_to_target_area
from restoration_eval.schemas import get_schema


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MaskRobustnessPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_mask_robustness_config(
            PROJECT_ROOT / "config" / "experiments" / "mask_robustness.yaml"
        )
        cls.canonical = load_canonical_mask_config(
            PROJECT_ROOT / "config" / "masks" / "canonical_binary.yaml"
        )

    def test_contract_counts_and_schema_registry(self) -> None:
        expected = self.config["expected"]
        self.assertEqual(expected["robustness_group_count"], 15)
        self.assertEqual(expected["case_count"], 75)
        self.assertEqual(expected["total_output_file_count"], 156)
        self.assertEqual(
            get_schema("mask_robustness_cases").version,
            "mask_robustness_cases.v1",
        )
        self.assertEqual(
            get_schema("mask_robustness_generation_audit").version,
            "mask_robustness_generation_audit.v1",
        )

    def test_identifiers_and_seeds_are_stable(self) -> None:
        self.assertEqual(
            robustness_group_id("p001", "loss_small", "target_04p5pct"),
            "robustness__p001__loss_small__target_04p5pct",
        )
        first = stable_case_seed("mask_robustness_seed.v1", 20260606, "p001")
        self.assertEqual(first, stable_case_seed("mask_robustness_seed.v1", 20260606, "p001"))
        self.assertNotEqual(first, stable_case_seed("mask_robustness_seed.v1", 20260606, "p018"))

    def test_group_statistics_detect_distinct_location_and_morphology(self) -> None:
        arrays: list[np.ndarray] = []
        records: list[dict[str, object]] = []
        for index, offset in enumerate((4, 12, 20, 28, 36), start=1):
            array = np.zeros((64, 64), dtype=bool)
            array[offset:offset + 5, 6 + index * 6:11 + index * 6] = True
            arrays.append(array)
            records.append(
                {
                    "variant_id": f"variant_{index:02d}",
                    "mask_type": "loss_small",
                    "mask_pixel_sha256": _pixel_sha(array),
                    "content_width": 64,
                    "content_height": 64,
                    "centroid_x_pixels": 8.0 + index * 6,
                    "centroid_y_pixels": float(offset + 2),
                    "bbox_aspect_ratio": 1.0 + index * 0.01,
                    "bbox_fill_ratio": 0.5 + index * 0.01,
                    "mask_compactness": 0.3 + index * 0.01,
                    "connected_component_count": 3 + index % 2,
                    "bbox_x_min": 6 + index * 6,
                    "bbox_y_min": offset,
                    "largest_component_fraction": 0.4 + index * 0.01,
                    "component_area_cv": 0.1 + index * 0.01,
                    "maximum_component_aspect_ratio": 2.0,
                }
            )
        result = _group_stats(records, arrays, self.config, self.canonical)
        self.assertTrue(result["group_gate_passed"])
        self.assertEqual(result["group_unique_pixel_sha256_count"], 5)
        self.assertLess(result["maximum_pairwise_iou"], 0.99)

    def test_duplicate_masks_fail_group_gate(self) -> None:
        array = np.zeros((64, 64), dtype=bool)
        array[10:15, 10:15] = True
        records = [
            {
                "variant_id": f"variant_{index:02d}",
                "mask_type": "loss_small",
                "mask_pixel_sha256": _pixel_sha(array),
                "content_width": 64,
                "content_height": 64,
                "centroid_x_pixels": 12.0,
                "centroid_y_pixels": 12.0,
                "bbox_aspect_ratio": 1.0,
                "bbox_fill_ratio": 1.0,
                "mask_compactness": 0.5,
                "connected_component_count": 3,
                "bbox_x_min": 10,
                "bbox_y_min": 10,
                "largest_component_fraction": 0.34,
                "component_area_cv": 0.0,
                "maximum_component_aspect_ratio": 1.0,
            }
            for index in range(1, 6)
        ]
        result = _group_stats(records, [array] * 5, self.config, self.canonical)
        self.assertFalse(result["group_gate_passed"])
        self.assertFalse(result["group_unique_mask_count_passed"])
        self.assertFalse(result["pairwise_iou_passed"])

    def test_invalid_contract_changes_are_rejected(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["families"][1]["target_percentage_content"] = 5.0
        self.assertTrue(validate_mask_robustness_config(changed))
        changed = copy.deepcopy(self.config)
        changed["expected"]["case_count"] = 74
        self.assertIn(
            "expected.case_count must equal 75",
            validate_mask_robustness_config(changed),
        )

    def test_fast_area_addition_is_exact_and_deterministic(self) -> None:
        base = np.zeros((96, 96), dtype=np.uint8)
        base[45:48, 8:88] = 1
        first = scale_mask_to_target_area(
            base,
            target_pixels=1200,
            content_bbox=(4, 4, 92, 92),
            case_seed=1234,
            addition_strategy="nearest_unmasked_content_by_euclidean_distance",
        )
        second = scale_mask_to_target_area(
            base,
            target_pixels=1200,
            content_bbox=(4, 4, 92, 92),
            case_seed=1234,
            addition_strategy="nearest_unmasked_content_by_euclidean_distance",
        )
        self.assertEqual(int(first["mask"].sum()), 1200)
        self.assertTrue(np.array_equal(first["mask"], second["mask"]))
        self.assertEqual(
            first["addition_strategy"],
            "nearest_unmasked_content_by_euclidean_distance",
        )


if __name__ == "__main__":
    unittest.main()
