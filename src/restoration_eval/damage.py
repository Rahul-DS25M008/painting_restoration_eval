"""Damage image creation utilities for the painting restoration evaluation project."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image


DEFAULT_DAMAGE_FILL_COLOR: tuple[int, int, int] = (255, 255, 255)
DEFAULT_DAMAGE_FILL_STRATEGY = "white_fill"


def apply_mask_damage(
    clean_image: Image.Image,
    mask: Image.Image,
    fill_color: tuple[int, int, int] = DEFAULT_DAMAGE_FILL_COLOR,
) -> Image.Image:
    """Apply a binary damage mask to a clean RGB image.

    Pixels where the mask is non-zero are replaced with ``fill_color``.
    Pixels outside the mask are preserved exactly.

    Mask convention:
    - 0 = preserved/original region
    - 255 = damaged/inpaint region
    """
    clean_rgb = clean_image.convert("RGB")
    mask_l = mask.convert("L")

    clean_arr = np.asarray(clean_rgb).copy()
    mask_arr = np.asarray(mask_l) > 0

    clean_arr[mask_arr] = fill_color

    return Image.fromarray(clean_arr.astype(np.uint8), mode="RGB")


def create_damaged_images_for_dataset(
    processed_metadata: pd.DataFrame,
    mask_metadata: pd.DataFrame,
    clean_dir: Path,
    damaged_dir: Path,
    fill_color: tuple[int, int, int] = DEFAULT_DAMAGE_FILL_COLOR,
    fill_strategy: str = DEFAULT_DAMAGE_FILL_STRATEGY,
) -> pd.DataFrame:
    """Create damaged images by applying each binary mask to its clean image.

    Returns one metadata row per mask case.
    """
    damaged_dir.mkdir(parents=True, exist_ok=True)

    required_processed_columns = [
        "painting_id",
        "processed_filename",
    ]

    required_mask_columns = [
        "case_id",
        "painting_id",
        "mask_id",
        "mask_type",
        "mask_filename",
        "mask_path",
        "actual_mask_area_pixels",
        "actual_mask_area_percentage_content",
        "actual_mask_area_percentage_full",
    ]

    missing_processed = [
        col for col in required_processed_columns
        if col not in processed_metadata.columns
    ]
    missing_mask = [
        col for col in required_mask_columns
        if col not in mask_metadata.columns
    ]

    if missing_processed:
        raise ValueError(f"Processed metadata missing required columns: {missing_processed}")

    if missing_mask:
        raise ValueError(f"Mask metadata missing required columns: {missing_mask}")

    processed_lookup = (
        processed_metadata
        .set_index("painting_id")
        .to_dict(orient="index")
    )

    records: list[dict[str, Any]] = []

    for _, mask_row in mask_metadata.sort_values(["painting_id", "mask_type"]).iterrows():
        painting_id = mask_row["painting_id"]
        case_id = mask_row["case_id"]
        mask_id = mask_row["mask_id"]
        mask_type = mask_row["mask_type"]

        if painting_id not in processed_lookup:
            raise ValueError(f"Painting ID from mask metadata not found in processed metadata: {painting_id}")

        processed_row = processed_lookup[painting_id]

        clean_filename = processed_row["processed_filename"]
        clean_path = clean_dir / clean_filename

        mask_path = Path(mask_row["mask_path"])
        if not mask_path.is_absolute():
            mask_path = mask_path

        damaged_filename = f"{case_id}_damaged.png"
        damaged_path = damaged_dir / damaged_filename

        status = "ok"
        issue = ""

        try:
            with Image.open(clean_path) as clean_img, Image.open(mask_path) as mask_img:
                damaged_img = apply_mask_damage(
                    clean_image=clean_img,
                    mask=mask_img,
                    fill_color=fill_color,
                )
                damaged_img.save(damaged_path)
        except Exception as exc:
            status = "error"
            issue = f"{type(exc).__name__}: {exc}"

        records.append(
            {
                "case_id": case_id,
                "painting_id": painting_id,
                "mask_id": mask_id,
                "mask_type": mask_type,
                "clean_filename": clean_filename,
                "clean_path": str(clean_path),
                "mask_filename": mask_row["mask_filename"],
                "mask_path": str(mask_path),
                "damaged_filename": damaged_filename,
                "damaged_path": str(damaged_path),
                "damage_fill_strategy": fill_strategy,
                "damage_fill_r": fill_color[0],
                "damage_fill_g": fill_color[1],
                "damage_fill_b": fill_color[2],
                "damaged_area_pixels": int(mask_row["actual_mask_area_pixels"]),
                "damaged_area_percentage_content": float(mask_row["actual_mask_area_percentage_content"]),
                "damaged_area_percentage_full": float(mask_row["actual_mask_area_percentage_full"]),
                "status": status,
                "issue": issue,
            }
        )

    return pd.DataFrame(records)


def validate_damaged_images(
    damaged_metadata: pd.DataFrame,
    target_size: int = 768,
) -> pd.DataFrame:
    """Validate damaged image files."""
    required_columns = [
        "case_id",
        "painting_id",
        "mask_type",
        "damaged_path",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in damaged_metadata.columns
    ]

    if missing_columns:
        raise ValueError(f"Damaged metadata missing required columns: {missing_columns}")

    validation_rows: list[dict[str, Any]] = []

    for _, row in damaged_metadata.iterrows():
        damaged_path = Path(row["damaged_path"])

        file_exists = damaged_path.exists()
        readable = False
        width = None
        height = None
        mode = None
        issue = ""

        if not file_exists:
            issue = "missing_damaged_file"
        else:
            try:
                with Image.open(damaged_path) as img:
                    damaged_img = img.convert("RGB")
                    readable = True
                    width, height = damaged_img.size
                    mode = damaged_img.mode
            except Exception as exc:
                issue = f"unreadable_damaged_file: {type(exc).__name__}: {exc}"

        if file_exists and readable:
            if width != target_size or height != target_size:
                issue = "wrong_damaged_size"
            elif mode != "RGB":
                issue = "wrong_color_mode"

        validation_rows.append(
            {
                "case_id": row["case_id"],
                "painting_id": row["painting_id"],
                "mask_type": row["mask_type"],
                "damaged_path": str(damaged_path),
                "file_exists": file_exists,
                "readable": readable,
                "width": width,
                "height": height,
                "mode": mode,
                "issue": issue,
            }
        )

    return pd.DataFrame(validation_rows)


def validate_damage_application(
    damaged_metadata: pd.DataFrame,
    target_size: int = 768,
) -> pd.DataFrame:
    """Validate that damaged images differ from clean images only inside mask pixels.

    Checks:
    - outside mask: damaged image equals clean image exactly
    - inside mask: damaged image equals configured fill color
    - zero-control cases are identical to clean images
    """
    required_columns = [
        "case_id",
        "painting_id",
        "mask_type",
        "clean_path",
        "mask_path",
        "damaged_path",
        "damage_fill_r",
        "damage_fill_g",
        "damage_fill_b",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in damaged_metadata.columns
    ]

    if missing_columns:
        raise ValueError(f"Damaged metadata missing required columns: {missing_columns}")

    validation_rows: list[dict[str, Any]] = []

    for _, row in damaged_metadata.iterrows():
        clean_path = Path(row["clean_path"])
        mask_path = Path(row["mask_path"])
        damaged_path = Path(row["damaged_path"])

        issue = ""
        outside_mask_changed_pixels = None
        inside_mask_not_fill_pixels = None
        total_mask_pixels = None
        clean_equals_damaged = None

        fill_color = np.array(
            [
                int(row["damage_fill_r"]),
                int(row["damage_fill_g"]),
                int(row["damage_fill_b"]),
            ],
            dtype=np.uint8,
        )

        try:
            with Image.open(clean_path) as clean_img, Image.open(mask_path) as mask_img, Image.open(damaged_path) as damaged_img:
                clean_arr = np.asarray(clean_img.convert("RGB"))
                mask_arr = np.asarray(mask_img.convert("L")) > 0
                damaged_arr = np.asarray(damaged_img.convert("RGB"))

            if clean_arr.shape != damaged_arr.shape:
                issue = "clean_and_damaged_shape_mismatch"
            elif clean_arr.shape[:2] != (target_size, target_size):
                issue = "wrong_clean_shape"
            else:
                outside_mask = ~mask_arr
                outside_mask_changed_pixels = int(
                    np.any(clean_arr[outside_mask] != damaged_arr[outside_mask], axis=1).sum()
                )

                total_mask_pixels = int(mask_arr.sum())

                if total_mask_pixels > 0:
                    inside_mask_not_fill_pixels = int(
                        np.any(damaged_arr[mask_arr] != fill_color, axis=1).sum()
                    )
                else:
                    inside_mask_not_fill_pixels = 0

                clean_equals_damaged = bool(np.array_equal(clean_arr, damaged_arr))

                if outside_mask_changed_pixels != 0:
                    issue = "pixels_changed_outside_mask"
                elif inside_mask_not_fill_pixels != 0:
                    issue = "mask_pixels_not_set_to_fill_color"
                elif row["mask_type"] == "zero_control" and not clean_equals_damaged:
                    issue = "zero_control_changed_image"
                elif row["mask_type"] != "zero_control" and total_mask_pixels <= 0:
                    issue = "nonzero_mask_has_no_pixels"

        except Exception as exc:
            issue = f"{type(exc).__name__}: {exc}"

        validation_rows.append(
            {
                "case_id": row["case_id"],
                "painting_id": row["painting_id"],
                "mask_type": row["mask_type"],
                "outside_mask_changed_pixels": outside_mask_changed_pixels,
                "inside_mask_not_fill_pixels": inside_mask_not_fill_pixels,
                "total_mask_pixels": total_mask_pixels,
                "clean_equals_damaged": clean_equals_damaged,
                "issue": issue,
            }
        )

    return pd.DataFrame(validation_rows)