"""OpenCV restoration baselines for the painting restoration evaluation project."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd
from PIL import Image


DEFAULT_OPENCV_MODEL_NAME = "opencv_telea"
DEFAULT_TELEA_RADIUS = 3


def restore_with_opencv_telea(
    damaged_image_path: Path,
    mask_path: Path,
    radius: int = DEFAULT_TELEA_RADIUS,
) -> Image.Image:
    """Restore a damaged image using OpenCV Telea inpainting.

    OpenCV expects:
    - an RGB/BGR image input,
    - a single-channel mask,
    - non-zero mask pixels indicating the region to inpaint.
    """
    damaged_bgr = cv2.imread(str(damaged_image_path), cv2.IMREAD_COLOR)
    mask_gray = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

    if damaged_bgr is None:
        raise FileNotFoundError(f"Could not read damaged image: {damaged_image_path}")

    if mask_gray is None:
        raise FileNotFoundError(f"Could not read mask: {mask_path}")

    _, mask_binary = cv2.threshold(mask_gray, 127, 255, cv2.THRESH_BINARY)

    restored_bgr = cv2.inpaint(
        damaged_bgr,
        mask_binary,
        inpaintRadius=radius,
        flags=cv2.INPAINT_TELEA,
    )

    restored_rgb = cv2.cvtColor(restored_bgr, cv2.COLOR_BGR2RGB)

    return Image.fromarray(restored_rgb)


def run_opencv_telea_restoration(
    damaged_metadata: pd.DataFrame,
    restored_dir: Path,
    model_name: str = DEFAULT_OPENCV_MODEL_NAME,
    radius: int = DEFAULT_TELEA_RADIUS,
) -> pd.DataFrame:
    """Run OpenCV Telea restoration for every damaged image case.

    Parameters
    ----------
    damaged_metadata:
        Metadata produced by Notebook 04 damage creation. Must contain
        damaged image paths and mask paths.
    restored_dir:
        Directory where restored RGB PNG images will be saved.
    model_name:
        Name recorded in restoration metadata.
    radius:
        OpenCV Telea inpainting radius.

    Returns
    -------
    pd.DataFrame
        One metadata row per restored case.
    """
    restored_dir.mkdir(parents=True, exist_ok=True)

    required_columns = [
        "case_id",
        "painting_id",
        "mask_id",
        "mask_type",
        "clean_filename",
        "clean_path",
        "mask_filename",
        "mask_path",
        "damaged_filename",
        "damaged_path",
        "damaged_area_pixels",
        "damaged_area_percentage_content",
        "damaged_area_percentage_full",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in damaged_metadata.columns
    ]

    if missing_columns:
        raise ValueError(f"Damaged metadata missing required columns: {missing_columns}")

    records: list[dict[str, Any]] = []

    for _, row in damaged_metadata.sort_values(["painting_id", "mask_type"]).iterrows():
        case_id = row["case_id"]
        painting_id = row["painting_id"]
        mask_id = row["mask_id"]
        mask_type = row["mask_type"]

        damaged_path = Path(row["damaged_path"])
        mask_path = Path(row["mask_path"])

        restored_filename = f"{case_id}_restored_{model_name}.png"
        restored_path = restored_dir / restored_filename

        status = "ok"
        issue = ""

        try:
            restored_img = restore_with_opencv_telea(
                damaged_image_path=damaged_path,
                mask_path=mask_path,
                radius=radius,
            )
            restored_img.save(restored_path)
        except Exception as exc:
            status = "error"
            issue = f"{type(exc).__name__}: {exc}"

        records.append(
            {
                "case_id": case_id,
                "painting_id": painting_id,
                "mask_id": mask_id,
                "mask_type": mask_type,
                "model_name": model_name,
                "algorithm": "cv2.INPAINT_TELEA",
                "inpaint_radius": radius,
                "clean_filename": row["clean_filename"],
                "clean_path": row["clean_path"],
                "mask_filename": row["mask_filename"],
                "mask_path": str(mask_path),
                "damaged_filename": row["damaged_filename"],
                "damaged_path": str(damaged_path),
                "restored_filename": restored_filename,
                "restored_path": str(restored_path),
                "damaged_area_pixels": int(row["damaged_area_pixels"]),
                "damaged_area_percentage_content": float(row["damaged_area_percentage_content"]),
                "damaged_area_percentage_full": float(row["damaged_area_percentage_full"]),
                "status": status,
                "issue": issue,
            }
        )

    return pd.DataFrame(records)


def validate_restored_images(
    restored_metadata: pd.DataFrame,
    target_size: int = 768,
) -> pd.DataFrame:
    """Validate restored image files."""
    required_columns = [
        "case_id",
        "painting_id",
        "mask_type",
        "restored_path",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in restored_metadata.columns
    ]

    if missing_columns:
        raise ValueError(f"Restored metadata missing required columns: {missing_columns}")

    validation_rows: list[dict[str, Any]] = []

    for _, row in restored_metadata.iterrows():
        restored_path = Path(row["restored_path"])

        file_exists = restored_path.exists()
        readable = False
        width = None
        height = None
        mode = None
        issue = ""

        if not file_exists:
            issue = "missing_restored_file"
        else:
            try:
                with Image.open(restored_path) as img:
                    restored_img = img.convert("RGB")
                    readable = True
                    width, height = restored_img.size
                    mode = restored_img.mode
            except Exception as exc:
                issue = f"unreadable_restored_file: {type(exc).__name__}: {exc}"

        if file_exists and readable:
            if width != target_size or height != target_size:
                issue = "wrong_restored_size"
            elif mode != "RGB":
                issue = "wrong_color_mode"

        validation_rows.append(
            {
                "case_id": row["case_id"],
                "painting_id": row["painting_id"],
                "mask_type": row["mask_type"],
                "restored_path": str(restored_path),
                "file_exists": file_exists,
                "readable": readable,
                "width": width,
                "height": height,
                "mode": mode,
                "issue": issue,
            }
        )

    return pd.DataFrame(validation_rows)


def validate_opencv_restoration_behavior(
    restored_metadata: pd.DataFrame,
    target_size: int = 768,
) -> pd.DataFrame:
    """Validate basic OpenCV restoration behavior.

    This does not judge restoration quality. That belongs to later metric notebooks.

    Checks:
    - zero-control restored image should equal the clean image,
    - non-zero restored image should differ from the damaged image somewhere,
    - all image arrays should have matching shapes.
    """
    required_columns = [
        "case_id",
        "painting_id",
        "mask_type",
        "clean_path",
        "damaged_path",
        "restored_path",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in restored_metadata.columns
    ]

    if missing_columns:
        raise ValueError(f"Restored metadata missing required columns: {missing_columns}")

    validation_rows: list[dict[str, Any]] = []

    for _, row in restored_metadata.iterrows():
        clean_path = Path(row["clean_path"])
        damaged_path = Path(row["damaged_path"])
        restored_path = Path(row["restored_path"])

        issue = ""
        clean_equals_restored = None
        damaged_equals_restored = None
        changed_pixels_vs_damaged = None
        changed_pixels_vs_clean = None

        try:
            with Image.open(clean_path) as clean_img, Image.open(damaged_path) as damaged_img, Image.open(restored_path) as restored_img:
                clean_arr = np.asarray(clean_img.convert("RGB"))
                damaged_arr = np.asarray(damaged_img.convert("RGB"))
                restored_arr = np.asarray(restored_img.convert("RGB"))

            if clean_arr.shape != damaged_arr.shape or clean_arr.shape != restored_arr.shape:
                issue = "image_shape_mismatch"
            elif clean_arr.shape[:2] != (target_size, target_size):
                issue = "wrong_image_shape"
            else:
                clean_equals_restored = bool(np.array_equal(clean_arr, restored_arr))
                damaged_equals_restored = bool(np.array_equal(damaged_arr, restored_arr))

                changed_pixels_vs_damaged = int(
                    np.any(damaged_arr != restored_arr, axis=2).sum()
                )

                changed_pixels_vs_clean = int(
                    np.any(clean_arr != restored_arr, axis=2).sum()
                )

                if row["mask_type"] == "zero_control" and not clean_equals_restored:
                    issue = "zero_control_restoration_changed_image"
                elif row["mask_type"] != "zero_control" and damaged_equals_restored:
                    issue = "nonzero_restoration_identical_to_damaged_input"

        except Exception as exc:
            issue = f"{type(exc).__name__}: {exc}"

        validation_rows.append(
            {
                "case_id": row["case_id"],
                "painting_id": row["painting_id"],
                "mask_type": row["mask_type"],
                "clean_equals_restored": clean_equals_restored,
                "damaged_equals_restored": damaged_equals_restored,
                "changed_pixels_vs_damaged": changed_pixels_vs_damaged,
                "changed_pixels_vs_clean": changed_pixels_vs_clean,
                "issue": issue,
            }
        )

    return pd.DataFrame(validation_rows)