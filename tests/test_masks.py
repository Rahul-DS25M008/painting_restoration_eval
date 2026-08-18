from __future__ import annotations

import copy
import math
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.masks import (
    FAMILY_AUDIT_METRICS,
    GENERATOR_VERSION,
    GLOBAL_AUDIT_METRIC_COUNT,
    MaskValidationResult,
    SUPPORTED_MASK_TYPES,
    _mask_morphology_metadata,
    build_mask_audit,
    calculate_mask_morphology,
    evaluate_family_morphology,
    generate_mask_case,
    load_mask_config,
    render_mask_protocol,
    resolve_mask_inputs,
    select_representative_row,
    stable_seed,
    validate_mask_config,
    validate_preprocessed_handoff,
)
from restoration_eval.paths import find_project_root
from restoration_eval.schemas import (
    CANONICAL_MASKS_SCHEMA,
    MASK_AUDIT_SCHEMA,
    get_schema,
)


PROJECT_ROOT = find_project_root(Path(__file__))
CONFIG_PATH = PROJECT_ROOT / "config" / "masks" / "canonical_binary.yaml"


class CanonicalMaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_mask_config(CONFIG_PATH)
        cls.inputs = resolve_mask_inputs(cls.config, PROJECT_ROOT)
        cls.preprocessed = pd.read_csv(cls.inputs["geometry_path"])
        cls.representative = select_representative_row(
            cls.preprocessed, cls.config
        ).iloc[0]
        cls.case_results = {
            mask_type: generate_mask_case(
                cls.representative, mask_type, cls.config
            )
            for mask_type in SUPPORTED_MASK_TYPES
        }
        cls.case_table = pd.DataFrame(
            [
                {
                    **result.record,
                    "mask_sha256": f"unit-test-sha-{index}",
                    "generation_status": "passed",
                }
                for index, result in enumerate(cls.case_results.values())
            ]
        )

    def test_configuration_and_notebook02_handoff_contracts(self) -> None:
        self.assertEqual(validate_mask_config(self.config), [])
        self.assertEqual(
            validate_preprocessed_handoff(self.preprocessed, self.config), []
        )
        self.assertEqual(self.config["generator"]["version"], GENERATOR_VERSION)
        self.assertEqual(
            self.config["expected"]["mask_count"],
            self.config["expected"]["painting_count"]
            * len(SUPPORTED_MASK_TYPES),
        )
        self.assertEqual(
            self.config["expected"]["audit_row_count"],
            GLOBAL_AUDIT_METRIC_COUNT
            + len(SUPPORTED_MASK_TYPES) * len(FAMILY_AUDIT_METRICS)
            + math.comb(len(SUPPORTED_MASK_TYPES), 2)
            + len(SUPPORTED_MASK_TYPES),
        )

    def test_configuration_allows_touching_but_rejects_overlapping_ranges(self) -> None:
        touching = copy.deepcopy(self.config)
        self.assertEqual(
            touching["families"]["scratch_thin"]["upper_damaged_content_fraction"],
            touching["families"]["loss_small"]["lower_damaged_content_fraction"],
        )
        self.assertEqual(validate_mask_config(touching), [])

        overlapping = copy.deepcopy(self.config)
        overlapping["families"]["loss_small"][
            "lower_damaged_content_fraction"
        ] = 0.029
        self.assertTrue(
            any(
                "must not overlap" in issue
                for issue in validate_mask_config(overlapping)
            )
        )

    def test_canonical_mask_schemas_are_registered(self) -> None:
        self.assertIs(get_schema("canonical_masks"), CANONICAL_MASKS_SCHEMA)
        self.assertIs(get_schema("mask_audit"), MASK_AUDIT_SCHEMA)

    def test_representative_selection_is_rule_based_and_stable(self) -> None:
        selected = select_representative_row(self.preprocessed, self.config)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected.iloc[0]["painting_id"], "p050")
        median = float(self.preprocessed["content_area_fraction"].median())
        selected_distance = abs(
            float(selected.iloc[0]["content_area_fraction"]) - median
        )
        all_distances = (
            self.preprocessed["content_area_fraction"].astype(float) - median
        ).abs()
        self.assertAlmostEqual(selected_distance, float(all_distances.min()))

    def test_seed_derivation_and_case_generation_are_deterministic(self) -> None:
        seed = stable_seed("painting", 3, "scratch_thin")
        self.assertEqual(seed, stable_seed("painting", 3, "scratch_thin"))
        self.assertNotEqual(seed, stable_seed("painting", 4, "scratch_thin"))

        first = self.case_results["mixed_damage"]
        second = generate_mask_case(
            self.representative, "mixed_damage", self.config
        )
        np.testing.assert_array_equal(np.asarray(first.image), np.asarray(second.image))
        for field in (
            "painting_seed",
            "mask_seed",
            "retry_seed",
            "generation_attempts",
            "generator_parameters",
        ):
            self.assertEqual(first.record[field], second.record[field])

    def test_all_families_are_binary_content_only_and_in_range(self) -> None:
        for mask_type, result in self.case_results.items():
            with self.subTest(mask_type=mask_type):
                unique = set(np.unique(np.asarray(result.image)).astype(int).tolist())
                self.assertTrue(unique.issubset({0, 255}))
                self.assertTrue(result.record["binary_values_valid"])
                self.assertTrue(result.record["content_only_valid"])
                self.assertTrue(result.record["area_within_target_tolerance"])
                self.assertTrue(result.record["zero_control_rule_valid"])
                self.assertEqual(result.record["padding_overlap_pixels"], 0)
                self.assertEqual(result.image.mode, "L")
                self.assertEqual(result.image.size, (768, 768))

    def test_empty_and_known_square_morphology_are_explicit(self) -> None:
        empty = Image.new("L", (10, 10), 0)
        empty_metrics = calculate_mask_morphology(
            empty, content_box=(1, 1, 9, 9)
        )
        self.assertEqual(empty_metrics["damaged_pixel_count"], 0)
        self.assertEqual(empty_metrics["bbox_area_pixels"], 0)
        self.assertEqual(empty_metrics["connected_component_count"], 0)
        self.assertEqual(
            empty_metrics["minimum_distance_to_content_boundary_pixels"], -1
        )

        square = np.zeros((10, 10), dtype=np.uint8)
        square[2:5, 2:5] = 255
        metrics = calculate_mask_morphology(square, content_box=(0, 0, 10, 10))
        self.assertEqual(metrics["damaged_pixel_count"], 9)
        self.assertEqual(metrics["connected_component_count"], 1)
        self.assertEqual(metrics["mask_perimeter_pixels"], 12)
        self.assertAlmostEqual(metrics["mask_compactness"], math.pi / 4, places=8)

    def test_legacy_morphology_wrapper_remains_compatible(self) -> None:
        result = self.case_results["scratch_thin"]
        metadata = _mask_morphology_metadata(
            result.image,
            768,
            (
                int(self.representative["content_x_min"]),
                int(self.representative["content_y_min"]),
                int(self.representative["content_x_max"]),
                int(self.representative["content_y_max"]),
            ),
        )
        for key in (
            "actual_mask_area_percentage_content",
            "connected_component_count",
            "touches_content_border",
            "mask_compactness",
        ):
            self.assertIn(key, metadata)

    def test_family_expectations_pass_for_deterministic_smoke_cases(self) -> None:
        checks = evaluate_family_morphology(self.case_table, self.config)
        self.assertEqual(len(checks), len(SUPPORTED_MASK_TYPES))
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))

    def test_audit_builder_has_exact_105_row_contract(self) -> None:
        family_checks = evaluate_family_morphology(self.case_table, self.config)
        validation = MaskValidationResult(
            mask_checks=pd.DataFrame(
                {
                    "file_exists": [True] * len(self.case_table),
                }
            ),
            summary={
                "missing_mask_count": 0,
                "stale_mask_count": 0,
                "orphan_mask_count": 0,
                "duplicate_identity_group_count": 0,
                "duplicate_nonzero_sha256_group_count": 0,
                "cross_family_equivalent_pair_count": 0,
                "reload_failure_count": 0,
                "width_nonconforming_count": 0,
                "height_nonconforming_count": 0,
                "mode_nonconforming_count": 0,
                "format_nonconforming_count": 0,
                "nonbinary_mask_count": 0,
                "zero_control_failure_count": 0,
                "empty_nonzero_mask_count": 0,
                "padding_overlap_failure_count": 0,
                "area_tolerance_failure_count": 0,
                "morphology_reconciliation_failure_count": 0,
            },
            orphan_paths=(),
            duplicate_nonzero_sha256_groups=(),
            cross_family_equivalent_pairs=(),
        )
        runtimes = pd.DataFrame(
            {
                "mask_id": self.case_table["mask_id"],
                "runtime_seconds": [0.01] * len(self.case_table),
            }
        )
        replay = pd.DataFrame(
            {
                "mask_id": self.case_table["mask_id"],
                "replay_passed": [True] * len(self.case_table),
            }
        )
        audit = build_mask_audit(
            self.case_table,
            runtimes,
            validation,
            replay,
            family_checks,
            self.config,
        )
        self.assertEqual(len(audit), 105)
        self.assertEqual(audit["audit_row_id"].nunique(), 105)
        self.assertEqual(
            audit["audit_section"].value_counts().to_dict(),
            {
                "mask_family": 60,
                "global": 30,
                "family_comparison": 10,
                "morphology_expectation": 5,
            },
        )

    def test_protocol_states_scope_and_nonbinary_exclusions(self) -> None:
        checks = evaluate_family_morphology(self.case_table, self.config)
        protocol = render_mask_protocol(self.config, checks)
        self.assertIn("binary missing-region damage only", protocol)
        self.assertIn("`blur`", protocol)
        self.assertIn("`fading`", protocol)
        self.assertIn("`discolouration`", protocol)
        self.assertIn("never eligible for damage", protocol)


if __name__ == "__main__":
    unittest.main()
