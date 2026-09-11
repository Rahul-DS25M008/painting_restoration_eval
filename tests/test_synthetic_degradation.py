"""Focused preparation-layer tests for Notebook 07."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.schemas import get_schema
from restoration_eval.synthetic_degradation import (
    SUPPORTED_COMBINED_FAMILIES,
    SUPPORTED_SINGLE_FAMILIES,
    build_degradation_design,
    degradation_case_id,
    degradation_id,
    generate_degradation_case,
    load_synthetic_degradation_config,
    select_synthetic_degradation_cohort,
    smoke_design,
    stable_case_seed,
    validate_synthetic_degradation_config,
    validate_synthetic_degradation_handoff,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "experiments" / "synthetic_degradation.yaml"


class SyntheticDegradationPreparationTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_synthetic_degradation_config(CONFIG_PATH)
        cls.preprocessed = pd.read_csv(
            PROJECT_ROOT
            / cls.config["inputs"]["geometry_path"]
        )

    def test_configuration_counts_and_schema_registry(self) -> None:
        self.assertEqual(validate_synthetic_degradation_config(self.config), [])
        expected = self.config["expected"]
        self.assertEqual(expected["upstream_painting_count"], 300)
        self.assertEqual(expected["painting_count"], 35)
        self.assertEqual(expected["paintings_per_category"], 7)
        self.assertEqual(expected["single_case_count"], 1050)
        self.assertEqual(expected["combined_case_count"], 105)
        self.assertEqual(expected["case_count"], 1155)
        self.assertEqual(expected["total_output_file_count"], 2317)
        self.assertEqual(
            get_schema("synthetic_degradation_cases").version,
            "synthetic_degradation_cases.v1",
        )
        self.assertEqual(
            get_schema("synthetic_degradation_generation_audit").version,
            "synthetic_degradation_generation_audit.v1",
        )

    def test_real_notebook_02_handoff_and_balanced_cohort(self) -> None:
        self.assertEqual(
            validate_synthetic_degradation_handoff(
                self.preprocessed,
                self.config,
                PROJECT_ROOT,
                verify_files=True,
            ),
            [],
        )
        selected = select_synthetic_degradation_cohort(
            self.preprocessed,
            self.config,
        )
        self.assertEqual(
            tuple(selected["painting_id"]),
            (
                "p001", "p267", "p294", "p259", "p009", "p284", "p256",
                "p018", "p157", "p178", "p198", "p181", "p173", "p199",
                "p026", "p124", "p139", "p123", "p115", "p140", "p107",
                "p039", "p100", "p089", "p077", "p093", "p052", "p073",
                "p043", "p208", "p223", "p235", "p246", "p220", "p210",
            ),
        )
        self.assertEqual(selected["category"].nunique(), 5)
        self.assertTrue(selected.groupby("category").size().eq(7).all())

    def test_design_is_complete_normalized_and_unique(self) -> None:
        design = build_degradation_design(self.config)
        self.assertEqual(len(design), 1155)
        self.assertFalse(design["case_id"].duplicated().any())
        self.assertEqual(
            tuple(design.loc[~design["is_combined"], "degradation_family"].drop_duplicates()),
            SUPPORTED_SINGLE_FAMILIES,
        )
        self.assertEqual(
            tuple(design.loc[design["is_combined"], "degradation_family"].drop_duplicates()),
            SUPPORTED_COMBINED_FAMILIES,
        )
        singles = design.loc[~design["is_combined"]]
        combinations = design.loc[design["is_combined"]]
        self.assertEqual(len(singles), 1050)
        self.assertEqual(len(combinations), 105)
        self.assertTrue(combinations["severity"].eq("moderate").all())
        self.assertTrue(
            singles.groupby(["painting_id", "degradation_family"])["severity"].nunique().eq(3).all()
        )

    def test_identifiers_and_seeds_are_stable(self) -> None:
        self.assertEqual(
            degradation_id("gaussian_blur", "mild"),
            "gaussian_blur__mild",
        )
        self.assertEqual(
            degradation_case_id("p001", "gaussian_blur", "mild"),
            "synthetic_degradation__p001__gaussian_blur__mild",
        )
        first = stable_case_seed("scheme", 7, "p001", "gaussian_blur", "mild")
        self.assertEqual(
            first,
            stable_case_seed("scheme", 7, "p001", "gaussian_blur", "mild"),
        )
        self.assertNotEqual(
            first,
            stable_case_seed("scheme", 7, "p001", "gaussian_blur", "moderate"),
        )

    def test_smoke_design_covers_all_operators_and_combinations(self) -> None:
        design = smoke_design(self.config)
        self.assertEqual(len(design), 13)
        self.assertEqual(set(design["painting_id"]), {"p039"})
        self.assertEqual(
            set(design["degradation_family"]),
            set(SUPPORTED_SINGLE_FAMILIES) | set(SUPPORTED_COMBINED_FAMILIES),
        )

    def test_all_smoke_cases_are_deterministic_and_support_bounded(self) -> None:
        rng = np.random.default_rng(20260707)
        clean_array = rng.integers(20, 236, size=(96, 96, 3), dtype=np.uint8)
        clean = Image.fromarray(clean_array, mode="RGB")
        geometry = {
            "width": 96,
            "height": 96,
            "content_x_min": 8,
            "content_y_min": 10,
            "content_x_max": 88,
            "content_y_max": 86,
            "content_width": 80,
            "content_height": 76,
            "content_area_pixels": 80 * 76,
        }
        failures: list[str] = []
        for row in smoke_design(self.config).to_dict("records"):
            first = generate_degradation_case(clean, geometry, row, self.config)
            second = generate_degradation_case(clean, geometry, row, self.config)
            first_mask = np.asarray(first.effect_mask)
            second_mask = np.asarray(second.effect_mask)
            first_degraded = np.asarray(first.degraded)
            second_degraded = np.asarray(second.degraded)
            support = first_mask >= int(first.metadata["support_threshold"])
            changed = np.any(first_degraded != clean_array, axis=2)
            gate = np.zeros((96, 96), dtype=bool)
            gate[10:86, 8:88] = True
            passed = (
                np.array_equal(first_mask, second_mask)
                and np.array_equal(first_degraded, second_degraded)
                and bool(support.any())
                and bool(changed.any())
                and not bool((support & ~gate).any())
                and not bool((changed & ~support).any())
                and int(first.metadata["outside_support_changed_pixels"]) == 0
                and json.loads(str(first.metadata["operator_parameters_json"]))
                and json.loads(str(first.metadata["operator_seeds_json"]))
            )
            if not passed:
                failures.append(str(row["case_id"]))
        self.assertEqual(failures, [])

    def test_invalid_contract_changes_are_rejected(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["expected"]["case_count"] = 1154
        self.assertIn(
            "expected.case_count must equal 1155",
            validate_synthetic_degradation_config(changed),
        )
        changed = copy.deepcopy(self.config)
        changed["families"][1]["family_id"] = "directional_blur"
        self.assertTrue(validate_synthetic_degradation_config(changed))


if __name__ == "__main__":
    unittest.main()
