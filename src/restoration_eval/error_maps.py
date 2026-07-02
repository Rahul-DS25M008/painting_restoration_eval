"""
Error-map utilities for the painting restoration evaluation project.

This module creates visual diagnostic figures comparing:

- clean image vs damaged image,
- clean image vs restored image,
- damaged error vs restored error,
- signed restoration improvement.

The binary mask remains the authoritative definition of the artificially
damaged/restored region.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image


DEFAULT_ERROR_CMAP = "magma"
DEFAULT_SIGNED_CMAP = "coolwarm"


def load_rgb_array(path: Path) -> np.ndarray:
    """Load an RGB image as a float32 NumPy array in range [0, 255]."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.float32)


def load_mask_bool(path: Path) -> np.ndarray:
    """Load a binary mask as a boolean array where True means damaged/missing."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Mask file not found: {path}")

    with Image.open(path) as image:
        mask = np.asarray(image.convert("L"))

    return mask > 0


def load_image_for_display(path: Path, mode: str = "RGB") -> Image.Image:
    """Load an image for matplotlib display."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    with Image.open(path) as image:
        return image.convert(mode)


def compute_absolute_error_map(
    clean_arr: np.ndarray,
    candidate_arr: np.ndarray,
) -> np.ndarray:
    """Compute per-pixel mean absolute RGB error.

    Returns a 2D array in range [0, 255].
    """
    if clean_arr.shape != candidate_arr.shape:
        raise ValueError(
            f"Image shapes do not match: clean={clean_arr.shape}, "
            f"candidate={candidate_arr.shape}"
        )

    return np.mean(np.abs(clean_arr - candidate_arr), axis=2)


def compute_signed_improvement_map(
    damaged_error_map: np.ndarray,
    restored_error_map: np.ndarray,
) -> np.ndarray:
    """Compute signed per-pixel restoration improvement.

    Positive values mean the restored image is closer to the clean reference
    than the damaged image.

    Negative values mean the restored image is farther from the clean reference
    than the damaged image.
    """
    if damaged_error_map.shape != restored_error_map.shape:
        raise ValueError(
            f"Error-map shapes do not match: damaged={damaged_error_map.shape}, "
            f"restored={restored_error_map.shape}"
        )

    return damaged_error_map - restored_error_map


def apply_mask_to_map(
    map_arr: np.ndarray,
    mask_bool: np.ndarray,
    outside_value: float = np.nan,
) -> np.ndarray:
    """Return a copy of a 2D map where pixels outside the mask are suppressed."""
    if map_arr.shape != mask_bool.shape:
        raise ValueError(
            f"Map and mask shapes do not match: map={map_arr.shape}, "
            f"mask={mask_bool.shape}"
        )

    masked_map = np.full(map_arr.shape, outside_value, dtype=np.float32)
    masked_map[mask_bool] = map_arr[mask_bool]

    return masked_map


def safe_filename(value: str) -> str:
    """Create a filesystem-safe filename component."""
    value = str(value)
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9_\-]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_")


def compute_error_map_summary(
    clean_path: Path,
    damaged_path: Path,
    restored_path: Path,
    mask_path: Path,
) -> dict[str, Any]:
    """Compute error-map summary statistics for one restoration case."""
    clean_arr = load_rgb_array(clean_path)
    damaged_arr = load_rgb_array(damaged_path)
    restored_arr = load_rgb_array(restored_path)
    mask_bool = load_mask_bool(mask_path)

    if clean_arr.shape != damaged_arr.shape or clean_arr.shape != restored_arr.shape:
        raise ValueError(
            f"Image shape mismatch: clean={clean_arr.shape}, "
            f"damaged={damaged_arr.shape}, restored={restored_arr.shape}"
        )

    if mask_bool.shape != clean_arr.shape[:2]:
        raise ValueError(
            f"Mask shape mismatch: mask={mask_bool.shape}, "
            f"image={clean_arr.shape[:2]}"
        )

    damaged_error_map = compute_absolute_error_map(clean_arr, damaged_arr)
    restored_error_map = compute_absolute_error_map(clean_arr, restored_arr)
    signed_improvement_map = compute_signed_improvement_map(
        damaged_error_map=damaged_error_map,
        restored_error_map=restored_error_map,
    )

    full_pixel_count = int(mask_bool.size)
    masked_pixel_count = int(mask_bool.sum())

    if masked_pixel_count > 0:
        damaged_error_mean_masked = float(damaged_error_map[mask_bool].mean())
        restored_error_mean_masked = float(restored_error_map[mask_bool].mean())
        improvement_mean_masked = float(signed_improvement_map[mask_bool].mean())

        negative_improvement_pixels_masked = int(
            (signed_improvement_map[mask_bool] < 0).sum()
        )
        positive_improvement_pixels_masked = int(
            (signed_improvement_map[mask_bool] > 0).sum()
        )
        zero_improvement_pixels_masked = int(
            (signed_improvement_map[mask_bool] == 0).sum()
        )

        negative_improvement_percentage_masked = (
            negative_improvement_pixels_masked / masked_pixel_count * 100.0
        )
        positive_improvement_percentage_masked = (
            positive_improvement_pixels_masked / masked_pixel_count * 100.0
        )
    else:
        damaged_error_mean_masked = float("nan")
        restored_error_mean_masked = float("nan")
        improvement_mean_masked = float("nan")
        negative_improvement_pixels_masked = 0
        positive_improvement_pixels_masked = 0
        zero_improvement_pixels_masked = 0
        negative_improvement_percentage_masked = float("nan")
        positive_improvement_percentage_masked = float("nan")

    return {
        "full_pixel_count": full_pixel_count,
        "masked_pixel_count": masked_pixel_count,
        "damaged_error_mean_full": float(damaged_error_map.mean()),
        "restored_error_mean_full": float(restored_error_map.mean()),
        "improvement_mean_full": float(signed_improvement_map.mean()),
        "damaged_error_max_full": float(damaged_error_map.max()),
        "restored_error_max_full": float(restored_error_map.max()),
        "improvement_min_full": float(signed_improvement_map.min()),
        "improvement_max_full": float(signed_improvement_map.max()),
        "damaged_error_mean_masked": damaged_error_mean_masked,
        "restored_error_mean_masked": restored_error_mean_masked,
        "improvement_mean_masked": improvement_mean_masked,
        "negative_improvement_pixels_masked": negative_improvement_pixels_masked,
        "positive_improvement_pixels_masked": positive_improvement_pixels_masked,
        "zero_improvement_pixels_masked": zero_improvement_pixels_masked,
        "negative_improvement_percentage_masked": float(negative_improvement_percentage_masked),
        "positive_improvement_percentage_masked": float(positive_improvement_percentage_masked),
    }


def create_error_map_figure(
    case_row: pd.Series,
    output_path: Path,
    selection_group: str = "",
    error_vmin: float = 0.0,
    error_vmax: float = 255.0,
    improvement_vmin: float = -255.0,
    improvement_vmax: float = 255.0,
    show: bool = False,
    dpi: int = 150,
) -> None:
    """Create and save a diagnostic error-map figure for one case.

    Figure layout:

    Row 1:
    clean | mask | damaged | restored

    Row 2:
    damaged error | restored error | signed improvement | masked signed improvement
    """
    clean_path = Path(case_row["clean_path"])
    mask_path = Path(case_row["mask_path"])
    damaged_path = Path(case_row["damaged_path"])
    restored_path = Path(case_row["restored_path"])

    clean_img = load_image_for_display(clean_path, mode="RGB")
    mask_img = load_image_for_display(mask_path, mode="L")
    damaged_img = load_image_for_display(damaged_path, mode="RGB")
    restored_img = load_image_for_display(restored_path, mode="RGB")

    clean_arr = load_rgb_array(clean_path)
    damaged_arr = load_rgb_array(damaged_path)
    restored_arr = load_rgb_array(restored_path)
    mask_bool = load_mask_bool(mask_path)

    damaged_error_map = compute_absolute_error_map(clean_arr, damaged_arr)
    restored_error_map = compute_absolute_error_map(clean_arr, restored_arr)
    signed_improvement_map = compute_signed_improvement_map(
        damaged_error_map=damaged_error_map,
        restored_error_map=restored_error_map,
    )
    masked_signed_improvement_map = apply_mask_to_map(
        signed_improvement_map,
        mask_bool,
        outside_value=np.nan,
    )

    fig, axes = plt.subplots(2, 4, figsize=(18, 9))

    axes[0, 0].imshow(clean_img)
    axes[0, 0].set_title("Clean reference")
    axes[0, 0].axis("off")

    axes[0, 1].imshow(mask_img, cmap="gray", vmin=0, vmax=255)
    axes[0, 1].set_title("Damage mask")
    axes[0, 1].axis("off")

    axes[0, 2].imshow(damaged_img)
    axes[0, 2].set_title("Damaged input")
    axes[0, 2].axis("off")

    axes[0, 3].imshow(restored_img)
    axes[0, 3].set_title("OpenCV restored")
    axes[0, 3].axis("off")

    damaged_error_display = axes[1, 0].imshow(
        damaged_error_map,
        cmap=DEFAULT_ERROR_CMAP,
        vmin=error_vmin,
        vmax=error_vmax,
    )
    axes[1, 0].set_title("Clean vs damaged\nabsolute error")
    axes[1, 0].axis("off")
    fig.colorbar(damaged_error_display, ax=axes[1, 0], fraction=0.046, pad=0.04)

    restored_error_display = axes[1, 1].imshow(
        restored_error_map,
        cmap=DEFAULT_ERROR_CMAP,
        vmin=error_vmin,
        vmax=error_vmax,
    )
    axes[1, 1].set_title("Clean vs restored\nabsolute error")
    axes[1, 1].axis("off")
    fig.colorbar(restored_error_display, ax=axes[1, 1], fraction=0.046, pad=0.04)

    improvement_display = axes[1, 2].imshow(
        signed_improvement_map,
        cmap=DEFAULT_SIGNED_CMAP,
        vmin=improvement_vmin,
        vmax=improvement_vmax,
    )
    axes[1, 2].set_title("Signed improvement\npositive = reduced error")
    axes[1, 2].axis("off")
    fig.colorbar(improvement_display, ax=axes[1, 2], fraction=0.046, pad=0.04)

    masked_improvement_display = axes[1, 3].imshow(
        masked_signed_improvement_map,
        cmap=DEFAULT_SIGNED_CMAP,
        vmin=improvement_vmin,
        vmax=improvement_vmax,
    )
    axes[1, 3].set_title("Masked signed improvement")
    axes[1, 3].axis("off")
    fig.colorbar(masked_improvement_display, ax=axes[1, 3], fraction=0.046, pad=0.04)

    title_parts = [
        str(case_row.get("case_id", "")),
        str(case_row.get("category", "")),
        str(case_row.get("mask_type", "")),
        str(case_row.get("model_name", "")),
    ]

    if selection_group:
        title_parts.append(f"selection={selection_group}")

    fig.suptitle(" | ".join([part for part in title_parts if part]), fontsize=13)

    plt.tight_layout()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight")

    if show:
        plt.show()

    plt.close(fig)


def generate_error_map_figures_for_cases(
    cases_metadata: pd.DataFrame,
    output_dir: Path,
    selection_group_column: str = "selection_group",
    show: bool = False,
    dpi: int = 150,
    progress_every: int | None = 25,
) -> pd.DataFrame:
    """Generate diagnostic error-map figures for selected cases.

    Returns a manifest dataframe with figure paths and error-map statistics.

    Parameters
    ----------
    cases_metadata:
        One row per restoration case.
    output_dir:
        Base output directory for generated figures.
    selection_group_column:
        Column name used for grouping/output subfolders.
    show:
        Whether to display figures during generation.
    dpi:
        Saved figure DPI.
    progress_every:
        If not None, print progress every N cases.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    required_columns = [
        "case_id",
        "painting_id",
        "mask_type",
        "model_name",
        "clean_path",
        "mask_path",
        "damaged_path",
        "restored_path",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in cases_metadata.columns
    ]

    if missing_columns:
        raise ValueError(f"Cases metadata missing required columns: {missing_columns}")

    total_cases = len(cases_metadata)
    print(f"Starting error-map generation for {total_cases} cases...")
    print(f"Output directory: {output_dir}")

    records: list[dict[str, Any]] = []

    for idx, (_, row) in enumerate(cases_metadata.iterrows(), start=1):
        case_id = row["case_id"]
        model_name = row["model_name"]

        if selection_group_column in row.index:
            selection_group = str(row.get(selection_group_column, ""))
        else:
            selection_group = ""

        group_folder = safe_filename(selection_group) if selection_group else "all_cases"
        case_filename = f"{safe_filename(case_id)}_{safe_filename(model_name)}_error_maps.png"
        figure_path = output_dir / group_folder / case_filename

        status = "ok"
        issue = ""

        summary: dict[str, Any] = {}

        try:
            create_error_map_figure(
                case_row=row,
                output_path=figure_path,
                selection_group=selection_group,
                show=show,
                dpi=dpi,
            )

            summary = compute_error_map_summary(
                clean_path=Path(row["clean_path"]),
                damaged_path=Path(row["damaged_path"]),
                restored_path=Path(row["restored_path"]),
                mask_path=Path(row["mask_path"]),
            )

        except Exception as exc:
            status = "error"
            issue = f"{type(exc).__name__}: {exc}"

        records.append(
            {
                "case_id": case_id,
                "painting_id": row.get("painting_id", ""),
                "category": row.get("category", ""),
                "title": row.get("title", ""),
                "mask_id": row.get("mask_id", ""),
                "mask_type": row.get("mask_type", ""),
                "model_name": model_name,
                "selection_group": selection_group,
                "figure_filename": case_filename,
                "figure_path": str(figure_path),
                **summary,
                "status": status,
                "issue": issue,
            }
        )

        if progress_every is not None:
            if idx == 1 or idx % progress_every == 0 or idx == total_cases:
                print(f"Processed {idx}/{total_cases} cases...")

    print("Error-map generation finished.")
    return pd.DataFrame(records)

def validate_error_map_manifest(
    manifest_df: pd.DataFrame,
    expected_rows: int | None = None,
) -> pd.DataFrame:
    """Validate an error-map manifest dataframe."""
    validation_rows: list[dict[str, Any]] = []

    required_columns = [
        "case_id",
        "figure_path",
        "status",
        "issue",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in manifest_df.columns
    ]

    validation_rows.append(
        {
            "check": "required_columns",
            "passed": len(missing_columns) == 0,
            "detail": (
                "All required columns present."
                if not missing_columns
                else f"Missing columns: {missing_columns}"
            ),
        }
    )

    if expected_rows is not None:
        validation_rows.append(
            {
                "check": "row_count",
                "passed": len(manifest_df) == expected_rows,
                "detail": f"Expected {expected_rows}, found {len(manifest_df)}.",
            }
        )

    if "status" in manifest_df.columns:
        error_rows = int((manifest_df["status"] != "ok").sum())
        validation_rows.append(
            {
                "check": "status_ok",
                "passed": error_rows == 0,
                "detail": f"Rows with non-ok status: {error_rows}.",
            }
        )

    if "figure_path" in manifest_df.columns:
        existing_figures = manifest_df["figure_path"].apply(lambda p: Path(p).exists())
        missing_figures = int((~existing_figures).sum())
        validation_rows.append(
            {
                "check": "figures_exist",
                "passed": missing_figures == 0,
                "detail": f"Missing figure files: {missing_figures}.",
            }
        )

    return pd.DataFrame(validation_rows)