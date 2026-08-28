from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.error_maps import (
    CANDIDATE_MAP_TYPES,
    ERROR_MAP_VERSION,
    SPATIAL_REGION_ORDER,
    compute_candidate_spatial_diagnostics,
    compute_case_maps,
    compute_global_visualization_scales,
    load_spatial_diagnostics_config,
    make_map_id,
    render_candidate_spatial_panel,
    run_spatial_diagnostics,
    save_candidate_map_assets,
    validate_map_image_manifest,
    validate_spatial_diagnostics,
    write_dataframe_atomic,
)
from restoration_eval.schemas import (
    SPATIAL_DIAGNOSTICS_SCHEMA,
    SPATIAL_MAP_IMAGE_MANIFEST_SCHEMA,
    get_schema,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/evaluation/spatial_diagnostics.yaml"


class ErrorMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_spatial_diagnostics_config(CONFIG_PATH)

    @staticmethod
    def _write_fixture(root: Path) -> pd.DataFrame:
        height, width = 24, 32
        clean = np.zeros((height, width, 3), dtype=np.uint8)
        clean[:, :, 0] = np.arange(width, dtype=np.uint8)[None, :] * 5
        clean[:, :, 1] = 80
        damaged = clean.copy()
        damaged[8:16, 10:22] = np.array([240, 240, 240], dtype=np.uint8)
        restored = damaged.copy()
        restored[8:16, 10:16] = clean[8:16, 10:16]
        mask = np.zeros((height, width), dtype=np.uint8)
        mask[8:16, 10:22] = 255
        zero_mask = np.zeros_like(mask)
        for name, array in {
            "clean.png": clean,
            "damaged.png": damaged,
            "restored.png": restored,
            "mask.png": mask,
            "zero_mask.png": zero_mask,
        }.items():
            Image.fromarray(array).save(root / name)
        records = []
        for candidate_id, zero in (("candidate_nonzero", False), ("candidate_zero", True)):
            records.append({
                "candidate_id": candidate_id,
                "case_id": "case_nonzero" if not zero else "case_zero",
                "model_id": "lama",
                "candidate_index": 0,
                "seed": np.nan,
                "prompt_policy_id": "none",
                "prompt_variant_id": "none",
                "execution_role": "primary",
                "restored_path": "clean.png" if zero else "restored.png",
                "mask_threshold": 128,
                "dataset_id": "controlled_50",
                "dataset_scope": "controlled_50",
                "experiment_id": "canonical_missing_region",
                "painting_id": "p001",
                "input_image_path": "clean.png" if zero else "damaged.png",
                "clean_image_path": "clean.png",
                "mask_or_effect_path": "zero_mask.png" if zero else "mask.png",
                "damage_or_degradation_type": (
                    "zero_control" if zero else "binary_missing_region"
                ),
                "content_x_min": 1,
                "content_y_min": 1,
                "content_x_max": width - 1,
                "content_y_max": height - 1,
                "is_zero_control": zero,
            })
        return pd.DataFrame(records)

    @staticmethod
    def _scales() -> dict[str, dict[str, object]]:
        return {
            "absolute_error": {
                "cmap": "magma", "vmin": 0.0, "vmax": 255.0,
                "center": np.nan, "scale_scope": "test",
            },
            "signed_improvement": {
                "cmap": "RdBu", "vmin": -255.0, "vmax": 255.0,
                "center": 0.0, "scale_scope": "test",
            },
        }

    def test_config_schema_and_ids(self) -> None:
        self.assertEqual(ERROR_MAP_VERSION, "4.0.1")
        self.assertIs(get_schema("spatial_diagnostics"), SPATIAL_DIAGNOSTICS_SCHEMA)
        self.assertIs(
            get_schema("spatial_map_images"),
            SPATIAL_MAP_IMAGE_MANIFEST_SCHEMA,
        )
        self.assertEqual(
            tuple(self.config["visualization"]["map_types"]),
            CANDIDATE_MAP_TYPES,
        )
        self.assertEqual(
            tuple(self.config["regions"]["region_order"]),
            SPATIAL_REGION_ORDER,
        )
        self.assertEqual(
            self.config["expected_counts"]["spatial_diagnostic_rows"],
            18896,
        )
        self.assertEqual(
            sum(
                self.config["expected_counts"][
                    "diagnostic_rows_by_region"
                ].values()
            ),
            18896,
        )
        first = make_map_id("candidate_with_a_very_long_identifier")
        second = make_map_id("candidate_with_a_very_long_identifier")
        self.assertEqual(first, second)
        self.assertEqual(len(first), 20)

    def test_map_arithmetic(self) -> None:
        clean = np.zeros((4, 5, 3), dtype=np.uint8)
        damaged = clean.copy()
        damaged[1, 2] = 30
        restored = clean.copy()
        restored[1, 2] = 10
        maps = compute_case_maps(clean, damaged, restored)
        self.assertAlmostEqual(float(maps["damaged_absolute_error"][1, 2]), 30.0)
        self.assertAlmostEqual(float(maps["restored_absolute_error"][1, 2]), 10.0)
        self.assertAlmostEqual(float(maps["signed_improvement"][1, 2]), 20.0)
        self.assertAlmostEqual(float(maps["restoration_change"][1, 2]), 20.0)

    def test_candidate_regions_diagnostics_and_zero_control(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worklist = self._write_fixture(root)
            nonzero = compute_candidate_spatial_diagnostics(
                worklist.iloc[0], project_root=root, config=self.config
            )
            zero = compute_candidate_spatial_diagnostics(
                worklist.iloc[1], project_root=root, config=self.config
            )
            expected_canonical_regions = tuple(
                region_id
                for region_id in SPATIAL_REGION_ORDER
                if region_id != "degradation_support"
            )
            self.assertEqual(tuple(nonzero.regions), expected_canonical_regions)
            self.assertEqual(len(nonzero.diagnostics), 9)
            synthetic_row = worklist.iloc[0].copy()
            synthetic_row["experiment_id"] = "synthetic_degradation"
            synthetic = compute_candidate_spatial_diagnostics(
                synthetic_row, project_root=root, config=self.config
            )
            self.assertEqual(tuple(synthetic.regions), SPATIAL_REGION_ORDER)
            self.assertEqual(len(synthetic.diagnostics), 10)
            self.assertEqual(
                set(zero.diagnostics["region_id"]),
                {"full_image", "content_region", "outside_mask_content"},
            )
            validation = validate_spatial_diagnostics(
                pd.concat([nonzero.diagnostics, zero.diagnostics], ignore_index=True),
                expected_candidate_ids=worklist["candidate_id"],
            )
            self.assertTrue(validation["passed"], validation)
            masked = nonzero.diagnostics.loc[
                nonzero.diagnostics["region_id"].eq("masked_region")
            ].iloc[0]
            self.assertGreater(masked["signed_improvement_mean"], 0.0)
            self.assertFalse(masked["is_final_trustworthiness_flag"])

    def test_map_assets_manifest_and_panel(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worklist = self._write_fixture(root)
            result = compute_candidate_spatial_diagnostics(
                worklist.iloc[0], project_root=root, config=self.config
            )
            manifest = save_candidate_map_assets(
                worklist.iloc[0],
                result,
                scales=self._scales(),
                maps_root=root / "outputs/maps",
                project_root=root,
                config=self.config,
            )
            self.assertEqual(set(manifest["map_type"]), set(CANDIDATE_MAP_TYPES))
            validation = validate_map_image_manifest(
                manifest, project_root=root, verify_checksums=True
            )
            self.assertTrue(validation["passed"], validation)
            modes = {}
            for row in manifest.itertuples(index=False):
                with Image.open(root / row.relative_path) as image:
                    modes[row.map_type] = image.mode
            self.assertEqual(modes["signed_improvement"], "P")
            self.assertEqual(modes["spatial_overlay"], "RGBA")
            panel_path = root / "outputs/panel.png"
            figure = render_candidate_spatial_panel(
                worklist.iloc[0],
                project_root=root,
                config=self.config,
                scales=self._scales(),
                output_path=panel_path,
                selection_role="unit_test",
            )
            plt.close(figure)
            self.assertTrue(panel_path.is_file())
            self.assertGreater(panel_path.stat().st_size, 0)

    def test_global_scales_and_checkpoint_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worklist = self._write_fixture(root)
            scales_one = compute_global_visualization_scales(
                worklist, project_root=root, config=self.config
            )
            scales_two = compute_global_visualization_scales(
                worklist, project_root=root, config=self.config
            )
            self.assertEqual(scales_one, scales_two)
            diagnostic_checkpoint = root / "outputs/work/diagnostics.csv"
            manifest_checkpoint = root / "outputs/work/maps.csv"
            first = run_spatial_diagnostics(
                worklist,
                project_root=root,
                maps_root=root / "outputs/maps",
                config=self.config,
                scales=scales_one,
                diagnostics_checkpoint_path=diagnostic_checkpoint,
                map_manifest_checkpoint_path=manifest_checkpoint,
            )
            second = run_spatial_diagnostics(
                worklist,
                project_root=root,
                maps_root=root / "outputs/maps",
                config=self.config,
                scales=scales_one,
                diagnostics_checkpoint_path=diagnostic_checkpoint,
                map_manifest_checkpoint_path=manifest_checkpoint,
            )
            self.assertEqual(first.completed_candidates, 2)
            self.assertEqual(second.reused_candidates, 2)
            self.assertEqual(len(first.diagnostics), len(second.diagnostics))
            self.assertEqual(len(first.map_images), 5)
            self.assertEqual(len(second.map_images), 5)
            self.assertFalse(second.diagnostics["spatial_diagnostic_id"].duplicated().any())

    def test_atomic_csv_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "checkpoint.csv"
            write_dataframe_atomic(pd.DataFrame({"value": [1]}), path)
            write_dataframe_atomic(pd.DataFrame({"value": [2]}), path)
            self.assertEqual(pd.read_csv(path)["value"].tolist(), [2])


if __name__ == "__main__":
    unittest.main()
