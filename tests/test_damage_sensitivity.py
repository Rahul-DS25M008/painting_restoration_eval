from __future__ import annotations

import copy
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.damage_sensitivity import (
    DAMAGE_SIZE_MODULE_VERSION,
    _binary_array,
    _mask_centroid,
    cohort_painting_ids,
    configured_levels,
    generate_nested_mask_series,
    load_damage_size_config,
    resolve_damage_size_inputs,
    scale_mask_to_target_area,
    select_sensitivity_cohort,
    stable_case_seed,
    target_pixels_from_percentage,
    validate_damage_size_config,
    validate_damage_size_handoff,
)
from restoration_eval.manifests import sha256_file
from restoration_eval.masks import calculate_mask_morphology
from restoration_eval.paths import find_project_root
from restoration_eval.schemas import (
    DAMAGE_SIZE_CASES_SCHEMA,
    DAMAGE_SIZE_GENERATION_AUDIT_SCHEMA,
    get_schema,
)


PROJECT_ROOT = find_project_root(Path(__file__))
CONFIG_PATH = PROJECT_ROOT / "config" / "experiments" / "damage_size_sensitivity.yaml"


class DamageSizeSensitivityTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_damage_size_config(CONFIG_PATH)
        cls.inputs = resolve_damage_size_inputs(cls.config, PROJECT_ROOT)
        cls.preprocessed = pd.read_csv(cls.inputs["geometry_path"])
        cls.masks = pd.read_csv(cls.inputs["masks_path"])

    def test_configuration_and_real_upstream_handoff(self) -> None:
        self.assertEqual(validate_damage_size_config(self.config), [])
        self.assertEqual(
            validate_damage_size_handoff(
                self.preprocessed,
                self.masks,
                self.config,
                PROJECT_ROOT,
                verify_files=False,
            ),
            [],
        )
        self.assertEqual(self.config["generator"]["version"], DAMAGE_SIZE_MODULE_VERSION)
        self.assertEqual(self.config["expected"]["case_count"], 35)

    def test_damage_size_schemas_are_registered(self) -> None:
        self.assertIs(get_schema("damage_size_cases"), DAMAGE_SIZE_CASES_SCHEMA)
        self.assertIs(
            get_schema("damage_size_generation_audit"),
            DAMAGE_SIZE_GENERATION_AUDIT_SCHEMA,
        )

    def test_pinned_balanced_cohort_is_stable(self) -> None:
        expected = ("p001", "p018", "p026", "p039", "p043")
        self.assertEqual(cohort_painting_ids(self.config), expected)
        selected = select_sensitivity_cohort(
            self.preprocessed, self.masks, self.config
        )
        self.assertEqual(tuple(selected["painting_id"]), expected)
        self.assertEqual(len(selected), 5)
        self.assertTrue(selected["base_mask_type"].eq("loss_large").all())
        self.assertEqual(selected["base_mask_id"].nunique(), 5)

    def test_target_rounding_is_explicit_half_up(self) -> None:
        self.assertEqual(target_pixels_from_percentage(25, 2.0), 1)
        self.assertEqual(target_pixels_from_percentage(100, 12.5), 13)
        with self.assertRaisesRegex(ValueError, "positive"):
            target_pixels_from_percentage(0, 2.0)

    def test_stable_seed_uses_all_identity_parts(self) -> None:
        first = stable_case_seed("scheme", 7, "p001", "abc", "size_02pct")
        self.assertEqual(first, stable_case_seed("scheme", 7, "p001", "abc", "size_02pct"))
        self.assertNotEqual(first, stable_case_seed("scheme", 7, "p001", "abc", "size_04pct"))

    def test_nested_series_is_exact_deterministic_and_content_only(self) -> None:
        base = np.zeros((64, 64), dtype=np.uint8)
        yy, xx = np.ogrid[:64, :64]
        base[((xx - 31) / 12) ** 2 + ((yy - 30) / 9) ** 2 <= 1] = 255
        levels = (("size_05pct", 5.0), ("size_10pct", 10.0), ("size_20pct", 20.0))
        kwargs = {
            "content_bbox": (4, 4, 60, 60),
            "content_area_pixels": 56 * 56,
            "levels": levels,
            "global_seed": 123,
            "seed_scheme_version": "test.v1",
            "painting_id": "p_test",
            "base_mask_sha256": "abc123",
        }
        first = generate_nested_mask_series(base, **kwargs)
        second = generate_nested_mask_series(base, **kwargs)
        previous = None
        for one, two, (_, percentage) in zip(first, second, levels):
            np.testing.assert_array_equal(one["mask"], two["mask"])
            self.assertEqual(int(one["mask"].sum()), target_pixels_from_percentage(56 * 56, percentage))
            self.assertFalse(one["mask"][:4].any())
            self.assertFalse(one["mask"][60:].any())
            self.assertFalse(one["mask"][:, :4].any())
            self.assertFalse(one["mask"][:, 60:].any())
            if previous is not None:
                self.assertEqual(int((previous.astype(bool) & ~one["mask"].astype(bool)).sum()), 0)
            previous = one["mask"]

    def test_compatibility_scaler_preserves_dictionary_contract(self) -> None:
        base = np.zeros((32, 32), dtype=np.uint8)
        base[12:20, 12:20] = 1
        result = scale_mask_to_target_area(base, 128, (0, 0, 32, 32))
        self.assertEqual(result["mask"].dtype, np.uint8)
        self.assertEqual(int(result["mask"].sum()), 128)
        self.assertEqual(result["absolute_pixel_error"], 0)
        self.assertTrue(result["nested_with_previous"])

    def test_real_p039_smoke_series_meets_exact_area_and_nesting(self) -> None:
        selected = select_sensitivity_cohort(
            self.preprocessed, self.masks, self.config
        ).set_index("painting_id")
        row = selected.loc["p039"]
        base_path = PROJECT_ROOT / str(row["base_mask_path"])
        with Image.open(base_path) as base:
            series = generate_nested_mask_series(
                base.convert("L"),
                content_bbox=(
                    int(row["content_x_min"]), int(row["content_y_min"]),
                    int(row["content_x_max"]), int(row["content_y_max"]),
                ),
                content_area_pixels=int(row["content_area_pixels"]),
                levels=configured_levels(self.config),
                global_seed=int(self.config["generator"]["global_seed"]),
                seed_scheme_version=str(self.config["generator"]["seed_scheme_version"]),
                painting_id="p039",
                base_mask_sha256=sha256_file(base_path),
                maximum_iterations=int(self.config["generator"]["maximum_scale_iterations"]),
            )
        self.assertEqual(len(series), 7)
        previous = None
        for record in series:
            self.assertEqual(record["realised_pixels"], record["target_pixels"])
            if previous is not None:
                self.assertFalse((previous.astype(bool) & ~record["mask"].astype(bool)).any())
            previous = record["mask"]

    def test_real_cohort_meets_configured_morphology_gates(self) -> None:
        selected = select_sensitivity_cohort(
            self.preprocessed, self.masks, self.config
        )
        thresholds = self.config["morphology"]
        failures = []
        for row in selected.itertuples(index=False):
            base_path = PROJECT_ROOT / str(row.base_mask_path)
            with Image.open(base_path) as handle:
                base = handle.convert("L")
            content_box = (
                int(row.content_x_min), int(row.content_y_min),
                int(row.content_x_max), int(row.content_y_max),
            )
            base_array = _binary_array(base)
            base_centroid = _mask_centroid(base_array)
            base_morphology = calculate_mask_morphology(base, content_box=content_box)
            series = generate_nested_mask_series(
                base,
                content_bbox=content_box,
                content_area_pixels=int(row.content_area_pixels),
                levels=configured_levels(self.config),
                global_seed=int(self.config["generator"]["global_seed"]),
                seed_scheme_version=str(self.config["generator"]["seed_scheme_version"]),
                painting_id=str(row.painting_id),
                base_mask_sha256=sha256_file(base_path),
                maximum_iterations=int(self.config["generator"]["maximum_scale_iterations"]),
            )
            diagonal = np.hypot(int(row.content_width), int(row.content_height))
            for record in series:
                mask_array = record["mask"].astype(bool)
                morphology = calculate_mask_morphology(
                    mask_array, content_box=content_box
                )
                centroid = _mask_centroid(mask_array)
                shift = float(np.hypot(
                    centroid[0] - base_centroid[0],
                    centroid[1] - base_centroid[1],
                ))
                aspect_drift = abs(
                    morphology["bbox_aspect_ratio"]
                    - base_morphology["bbox_aspect_ratio"]
                ) / base_morphology["bbox_aspect_ratio"]
                compactness_drift = abs(
                    morphology["mask_compactness"]
                    - base_morphology["mask_compactness"]
                ) / base_morphology["mask_compactness"]
                passed = (
                    shift <= float(thresholds["maximum_centroid_shift_pixels"])
                    and shift / diagonal <= float(
                        thresholds["maximum_centroid_shift_fraction_of_content_diagonal"]
                    )
                    and aspect_drift <= float(
                        thresholds["maximum_relative_bbox_aspect_ratio_drift"]
                    )
                    and compactness_drift <= float(
                        thresholds["maximum_relative_compactness_drift"]
                    )
                    and morphology["connected_component_count"]
                    == base_morphology["connected_component_count"]
                    and not morphology["touches_content_boundary"]
                )
                if not passed:
                    failures.append(
                        (
                            row.painting_id,
                            record["level_id"],
                            round(shift, 6),
                            round(aspect_drift, 6),
                            round(compactness_drift, 6),
                            morphology["connected_component_count"],
                            morphology["touches_content_boundary"],
                        )
                    )
        self.assertEqual(failures, [])

    def test_invalid_contract_changes_are_rejected(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["levels"][0]["target_percentage_content"] = 3.0
        self.assertTrue(validate_damage_size_config(changed))
        changed = copy.deepcopy(self.config)
        changed["cohort"]["paintings"][1]["category"] = changed["cohort"]["paintings"][0]["category"]
        self.assertIn("cohort categories must be unique", validate_damage_size_config(changed))


if __name__ == "__main__":
    unittest.main()
