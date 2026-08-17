from __future__ import annotations

import copy
import unittest
from pathlib import Path

import pandas as pd
from PIL import Image

from restoration_eval.paths import find_project_root
from restoration_eval.preprocessing import (
    GLOBAL_AUDIT_METRIC_COUNT,
    GROUPED_AUDIT_METRICS,
    PreprocessingValidationResult,
    build_preprocessed_image,
    build_preprocessing_audit,
    compute_median_rgb,
    load_preprocessing_config,
    resize_with_aspect_ratio_and_pad,
    resolve_preprocessing_inputs,
    round_half_up,
    select_preview_rows,
    select_smoke_rows,
    validate_artworks_handoff,
    validate_preprocessing_config,
)
from restoration_eval.regions import content_region
from restoration_eval.schemas import (
    PREPROCESSED_IMAGES_COLUMNS,
    PREPROCESSED_IMAGES_SCHEMA,
    PREPROCESSING_AUDIT_SCHEMA,
    get_schema,
    validate_dataframe,
)


PROJECT_ROOT = find_project_root(Path(__file__))
CONFIG_PATH = PROJECT_ROOT / "config" / "preprocessing" / "canonical_768.yaml"


class PreprocessingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_preprocessing_config(CONFIG_PATH)
        inputs = resolve_preprocessing_inputs(cls.config, PROJECT_ROOT)
        cls.artworks = pd.read_csv(inputs["artworks_path"])

    def test_configuration_and_notebook01_handoff_contracts(self) -> None:
        self.assertEqual(validate_preprocessing_config(self.config), [])
        self.assertEqual(validate_artworks_handoff(self.artworks, self.config), [])
        self.assertEqual(self.config["expected"]["accepted_input_count"], 50)
        self.assertEqual(
            self.config["expected"]["audit_row_count"],
            GLOBAL_AUDIT_METRIC_COUNT
            + len(self.config["expected"]["categories"])
            * len(GROUPED_AUDIT_METRICS),
        )

    def test_configuration_rejects_noncanonical_target(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["processing"]["target_width"] = 512
        self.assertIn(
            "processing.target_width must equal 768",
            validate_preprocessing_config(changed),
        )

    def test_preprocessing_schemas_are_registered(self) -> None:
        self.assertIs(
            get_schema("preprocessed_images"),
            PREPROCESSED_IMAGES_SCHEMA,
        )
        self.assertIs(
            get_schema("preprocessing_audit"),
            PREPROCESSING_AUDIT_SCHEMA,
        )

    def test_round_half_up_and_median_rgb_are_explicit(self) -> None:
        self.assertEqual(round_half_up(2.49), 2)
        self.assertEqual(round_half_up(2.5), 3)
        image = Image.new("RGB", (2, 1))
        image.putdata([(0, 2, 4), (1, 3, 5)])
        self.assertEqual(compute_median_rgb(image), (1, 3, 5))

    def test_resize_geometry_uses_canonical_exclusive_bbox(self) -> None:
        image = Image.new("RGB", (100, 50), (11, 21, 31))
        canvas, metadata = resize_with_aspect_ratio_and_pad(image, self.config)
        self.assertEqual(canvas.size, (768, 768))
        self.assertEqual(canvas.mode, "RGB")
        self.assertEqual(metadata["resized_width"], 768)
        self.assertEqual(metadata["resized_height"], 384)
        self.assertEqual(metadata["pad_left"], 0)
        self.assertEqual(metadata["pad_right"], 0)
        self.assertEqual(metadata["pad_top"], 192)
        self.assertEqual(metadata["pad_bottom"], 192)
        bbox = (
            metadata["content_x_min"],
            metadata["content_y_min"],
            metadata["content_x_max"],
            metadata["content_y_max"],
        )
        region = content_region((768, 768), bbox)
        self.assertEqual(region.bbox, (0, 192, 768, 576))
        self.assertEqual(region.pixel_count, 768 * 384)
        self.assertAlmostEqual(
            metadata["content_area_fraction"]
            + metadata["padding_area_fraction"],
            1.0,
        )

    def test_in_memory_build_records_source_policies(self) -> None:
        source = Image.new("RGB", (80, 120), (50, 60, 70))
        source_record = {
            "raw_width": 80,
            "raw_height": 120,
            "raw_exif_orientation": 1,
            "raw_icc_profile_present": False,
            "raw_icc_profile_description": pd.NA,
        }
        canvas, metadata = build_preprocessed_image(
            source,
            source_record,
            self.config,
        )
        self.assertEqual(canvas.size, (768, 768))
        self.assertEqual(metadata["source_orientation"], 1)
        self.assertEqual(
            metadata["input_icc_profile_status"],
            "missing_assumed_srgb",
        )
        self.assertEqual(
            metadata["color_space_policy"],
            "assume_srgb_no_pixel_conversion",
        )
        self.assertFalse(metadata["output_icc_profile_present"])

    def test_smoke_and_preview_selection_are_one_per_category(self) -> None:
        smoke = select_smoke_rows(self.artworks, self.config)
        preview = select_preview_rows(self.artworks, self.config)
        self.assertEqual(len(smoke), 5)
        self.assertEqual(len(preview), 5)
        self.assertEqual(smoke["painting_id"].tolist(), preview["painting_id"].tolist())
        self.assertEqual(smoke["category"].nunique(), 5)

    def test_preprocessing_audit_has_exact_normalized_shape(self) -> None:
        rows = []
        for artwork in self.artworks.to_dict(orient="records"):
            painting_id = str(artwork["painting_id"])
            record = {
                "dataset_id": artwork["dataset_id"],
                "dataset_version": artwork["dataset_version"],
                "dataset_scope": artwork["dataset_scope"],
                "processed_image_id": f"clean_{painting_id}",
                "painting_id": painting_id,
                "dataset_sort_index": int(artwork["dataset_sort_index"]),
                "source_path": artwork["raw_image_path"],
                "source_sha256": artwork["raw_sha256"],
                "processed_filename": f"{painting_id}.png",
                "processed_path": (
                    "outputs/02_image_preprocessing/images/clean/"
                    f"{painting_id}.png"
                ),
                "original_width": int(artwork["raw_width"]),
                "original_height": int(artwork["raw_height"]),
                "width": 768,
                "height": 768,
                "mode": "RGB",
                "format": "PNG",
                "size_bytes": 1000,
                "sha256": f"{int(artwork['dataset_sort_index']):064x}",
                "resize_scale": 0.5,
                "resized_width": 768,
                "resized_height": 600,
                "interpolation": "lanczos",
                "pad_left": 0,
                "pad_top": 84,
                "pad_right": 0,
                "pad_bottom": 84,
                "padding_method": "median_rgb_source_pixels",
                "padding_color_r": 10,
                "padding_color_g": 20,
                "padding_color_b": 30,
                "content_x_min": 0,
                "content_y_min": 84,
                "content_x_max": 768,
                "content_y_max": 684,
                "content_width": 768,
                "content_height": 600,
                "content_area_pixels": 460800,
                "padding_area_pixels": 129024,
                "canvas_area_pixels": 589824,
                "content_area_fraction": 460800 / 589824,
                "padding_area_fraction": 129024 / 589824,
                "source_orientation": 1,
                "orientation_policy": "require_exif_orientation_1_no_transform",
                "input_icc_profile_status": "missing_assumed_srgb",
                "color_space_policy": "assume_srgb_no_pixel_conversion",
                "output_icc_profile_present": False,
                "coordinate_convention": "xyxy_exclusive_zero_based",
                "preprocessing_method": "aspect_ratio_resize_median_rgb_pad",
                "preprocessing_version": "2.0.0",
                "status": "passed",
            }
            rows.append({column: record[column] for column in PREPROCESSED_IMAGES_COLUMNS})
        images = pd.DataFrame(rows, columns=PREPROCESSED_IMAGES_COLUMNS)
        runtimes = pd.DataFrame(
            {
                "painting_id": images["painting_id"],
                "runtime_seconds": [0.1] * len(images),
            }
        )
        zero_summary = {
            "missing_output_count": 0,
            "stale_output_count": 0,
            "duplicate_sha256_group_count": 0,
            "orphan_output_count": 0,
            "reload_failure_count": 0,
            "output_width_nonconforming_count": 0,
            "output_height_nonconforming_count": 0,
            "output_mode_nonconforming_count": 0,
            "output_format_nonconforming_count": 0,
            "invalid_content_bbox_count": 0,
            "geometry_reconciliation_failure_count": 0,
            "padding_pixel_mismatch_count": 0,
            "output_icc_present_count": 0,
        }
        validation = PreprocessingValidationResult(
            image_checks=pd.DataFrame(),
            summary=zero_summary,
            orphan_paths=(),
            duplicate_sha256_groups=(),
        )
        audit = build_preprocessing_audit(
            images,
            self.artworks,
            runtimes,
            validation,
            self.config,
        )
        self.assertEqual(len(audit), 45)
        self.assertTrue(
            validate_dataframe(
                audit,
                PREPROCESSING_AUDIT_SCHEMA,
                allow_extra_columns=False,
            ).passed
        )
        self.assertEqual((audit["audit_section"] == "global").sum(), 25)
        self.assertEqual((audit["audit_section"] == "category").sum(), 20)


if __name__ == "__main__":
    unittest.main()
