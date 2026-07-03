"""
Classical image restoration metrics for the painting restoration evaluation project.

This module computes full-reference classical metrics for damaged and restored
images against the clean reference image.

Mask convention:
- 0 = preserved/original region
- non-zero / 255 = damaged/restored region
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image
from skimage.metrics import structural_similarity as ssim


CLASSICAL_METRIC_COLUMNS = [
    "damaged_mse",
    "restored_mse",
    "mse_improvement",
    "damaged_mae",
    "restored_mae",
    "mae_improvement",
    "damaged_psnr",
    "restored_psnr",
    "psnr_improvement",
    "damaged_ssim",
    "restored_ssim",
    "ssim_improvement",
]


def load_rgb_array(path: Path) -> np.ndarray:
    """Load an image as an RGB float32 array in range [0, 255]."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.float32)


def load_mask_bool(path: Path) -> np.ndarray:
    """Load a binary mask as a boolean array."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Mask file not found: {path}")

    with Image.open(path) as image:
        mask_arr = np.asarray(image.convert("L"))

    return mask_arr > 0


def compute_mse(reference_arr: np.ndarray, candidate_arr: np.ndarray) -> float:
    """Compute mean squared error."""
    return float(np.mean((reference_arr - candidate_arr) ** 2))


def compute_mae(reference_arr: np.ndarray, candidate_arr: np.ndarray) -> float:
    """Compute mean absolute error."""
    return float(np.mean(np.abs(reference_arr - candidate_arr)))


def compute_psnr_from_mse(mse_value: float, data_range: float = 255.0) -> float:
    """Compute PSNR from MSE.

    Returns np.inf when MSE is zero.
    """
    if mse_value == 0:
        return float("inf")

    return float(20.0 * np.log10(data_range / np.sqrt(mse_value)))


def compute_ssim_safe(
    reference_arr: np.ndarray,
    candidate_arr: np.ndarray,
    data_range: float = 255.0,
) -> float:
    """Compute SSIM safely for RGB image arrays.

    SSIM requires a spatial image region. Very tiny regions are returned as NaN
    rather than forcing a meaningless value into the results, because apparently
    even metrics deserve basic dignity.
    """
    if reference_arr.shape != candidate_arr.shape:
        raise ValueError(
            f"SSIM shape mismatch. Reference: {reference_arr.shape}, "
            f"candidate: {candidate_arr.shape}"
        )

    if reference_arr.ndim != 3 or reference_arr.shape[2] != 3:
        raise ValueError(
            f"Expected RGB arrays with shape HxWx3, got {reference_arr.shape}"
        )

    height, width = reference_arr.shape[:2]
    min_dim = min(height, width)

    if min_dim < 7:
        return float("nan")

    reference_uint8 = np.clip(reference_arr, 0, 255).astype(np.uint8)
    candidate_uint8 = np.clip(candidate_arr, 0, 255).astype(np.uint8)

    return float(
        ssim(
            reference_uint8,
            candidate_uint8,
            channel_axis=2,
            data_range=data_range,
        )
    )


def compute_image_region_metrics(
    clean_arr: np.ndarray,
    candidate_arr: np.ndarray,
    compute_ssim_value: bool = True,
) -> dict[str, float]:
    """Compute MSE, MAE, PSNR, and optionally SSIM for an image-like region."""
    if clean_arr.shape != candidate_arr.shape:
        raise ValueError(
            f"Image shape mismatch. Clean: {clean_arr.shape}, "
            f"candidate: {candidate_arr.shape}"
        )

    mse_value = compute_mse(clean_arr, candidate_arr)
    mae_value = compute_mae(clean_arr, candidate_arr)
    psnr_value = compute_psnr_from_mse(mse_value)

    if compute_ssim_value:
        ssim_value = compute_ssim_safe(clean_arr, candidate_arr)
    else:
        ssim_value = float("nan")

    return {
        "mse": mse_value,
        "mae": mae_value,
        "psnr": psnr_value,
        "ssim": ssim_value,
    }


def compute_masked_pixel_metrics(
    clean_arr: np.ndarray,
    candidate_arr: np.ndarray,
    mask_bool: np.ndarray,
) -> dict[str, float]:
    """Compute MSE, MAE, and PSNR over masked pixels only.

    SSIM is intentionally not computed on sparse masked pixels because SSIM
    requires local spatial structure.
    """
    if clean_arr.shape != candidate_arr.shape:
        raise ValueError(
            f"Image shape mismatch. Clean: {clean_arr.shape}, "
            f"candidate: {candidate_arr.shape}"
        )

    if mask_bool.shape != clean_arr.shape[:2]:
        raise ValueError(
            f"Mask shape mismatch. Mask: {mask_bool.shape}, "
            f"image: {clean_arr.shape[:2]}"
        )

    if not np.any(mask_bool):
        return {
            "mse": float("nan"),
            "mae": float("nan"),
            "psnr": float("nan"),
            "ssim": float("nan"),
        }

    clean_pixels = clean_arr[mask_bool]
    candidate_pixels = candidate_arr[mask_bool]

    mse_value = compute_mse(clean_pixels, candidate_pixels)
    mae_value = compute_mae(clean_pixels, candidate_pixels)
    psnr_value = compute_psnr_from_mse(mse_value)

    return {
        "mse": mse_value,
        "mae": mae_value,
        "psnr": psnr_value,
        "ssim": float("nan"),
    }


def get_content_crop(
    row: pd.Series,
    clean_arr: np.ndarray,
    damaged_arr: np.ndarray,
    restored_arr: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    """Extract the recorded painting-content region."""
    required_columns = [
        "content_x_min",
        "content_y_min",
        "content_x_max",
        "content_y_max",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in row.index
    ]

    if missing_columns:
        raise ValueError(f"Missing content-region columns: {missing_columns}")

    x_min = int(row["content_x_min"])
    y_min = int(row["content_y_min"])
    x_max = int(row["content_x_max"])
    y_max = int(row["content_y_max"])

    height, width = clean_arr.shape[:2]

    x_min = max(0, min(x_min, width))
    x_max = max(0, min(x_max, width))
    y_min = max(0, min(y_min, height))
    y_max = max(0, min(y_max, height))

    if x_max <= x_min or y_max <= y_min:
        raise ValueError(
            f"Invalid content region: "
            f"x_min={x_min}, y_min={y_min}, x_max={x_max}, y_max={y_max}"
        )

    region_info = {
        "region_x_min": x_min,
        "region_y_min": y_min,
        "region_x_max": x_max,
        "region_y_max": y_max,
    }

    return (
        clean_arr[y_min:y_max, x_min:x_max],
        damaged_arr[y_min:y_max, x_min:x_max],
        restored_arr[y_min:y_max, x_min:x_max],
        region_info,
    )


def get_mask_bbox(
    mask_bool: np.ndarray,
    margin: int = 8,
) -> dict[str, int] | None:
    """Return a mask bounding box with margin.

    Coordinates are returned in Python slicing convention:
    x_min inclusive, x_max exclusive, y_min inclusive, y_max exclusive.
    """
    ys, xs = np.where(mask_bool)

    if len(xs) == 0 or len(ys) == 0:
        return None

    height, width = mask_bool.shape

    x_min = max(0, int(xs.min()) - margin)
    x_max = min(width, int(xs.max()) + margin + 1)
    y_min = max(0, int(ys.min()) - margin)
    y_max = min(height, int(ys.max()) + margin + 1)

    if x_max <= x_min or y_max <= y_min:
        return None

    return {
        "region_x_min": x_min,
        "region_y_min": y_min,
        "region_x_max": x_max,
        "region_y_max": y_max,
    }


def _build_metric_record(
    row: pd.Series,
    evaluation_region: str,
    region_pixel_count: int,
    damaged_metrics: dict[str, float],
    restored_metrics: dict[str, float],
    region_info: dict[str, int | None],
    status: str = "ok",
    issue: str = "",
) -> dict[str, Any]:
    """Build one metric output row."""
    damaged_mse = damaged_metrics["mse"]
    restored_mse = restored_metrics["mse"]
    damaged_mae = damaged_metrics["mae"]
    restored_mae = restored_metrics["mae"]
    damaged_psnr = damaged_metrics["psnr"]
    restored_psnr = restored_metrics["psnr"]
    damaged_ssim = damaged_metrics["ssim"]
    restored_ssim = restored_metrics["ssim"]

    return {
        "case_id": row["case_id"],
        "painting_id": row["painting_id"],
        "category": row.get("category", ""),
        "title": row.get("title", ""),
        "mask_id": row["mask_id"],
        "mask_type": row["mask_type"],
        "model_name": row["model_name"],
        "evaluation_region": evaluation_region,
        "region_pixel_count": int(region_pixel_count),
        "region_x_min": region_info.get("region_x_min"),
        "region_y_min": region_info.get("region_y_min"),
        "region_x_max": region_info.get("region_x_max"),
        "region_y_max": region_info.get("region_y_max"),
        "damaged_area_pixels": row.get("damaged_area_pixels", np.nan),
        "damaged_area_percentage_content": row.get("damaged_area_percentage_content", np.nan),
        "damaged_area_percentage_full": row.get("damaged_area_percentage_full", np.nan),
        "damaged_mse": damaged_mse,
        "restored_mse": restored_mse,
        "mse_improvement": damaged_mse - restored_mse,
        "damaged_mae": damaged_mae,
        "restored_mae": restored_mae,
        "mae_improvement": damaged_mae - restored_mae,
        "damaged_psnr": damaged_psnr,
        "restored_psnr": restored_psnr,
        "psnr_improvement": restored_psnr - damaged_psnr,
        "damaged_ssim": damaged_ssim,
        "restored_ssim": restored_ssim,
        "ssim_improvement": restored_ssim - damaged_ssim,
        "status": status,
        "issue": issue,
    }


def compute_classical_metrics_for_restorations(
    restoration_metadata: pd.DataFrame,
    target_size: int = 768,
    mask_bbox_margin: int = 8,
    progress_every: int | None = 25,
) -> pd.DataFrame:
    """Compute classical metrics for restoration outputs.

    The input dataframe should contain restoration metadata merged with
    processed image metadata so that content-region coordinates and category
    labels are available.

    Output layout:
    - one row per case_id, model_name, and evaluation_region
    - compares clean vs damaged and clean vs restored
    """
    required_columns = [
        "case_id",
        "painting_id",
        "mask_id",
        "mask_type",
        "model_name",
        "clean_path",
        "damaged_path",
        "restored_path",
        "mask_path",
        "content_x_min",
        "content_y_min",
        "content_x_max",
        "content_y_max",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in restoration_metadata.columns
    ]

    if missing_columns:
        raise ValueError(f"Restoration metadata missing required columns: {missing_columns}")

    metric_records: list[dict[str, Any]] = []

    sorted_metadata = restoration_metadata.sort_values(
        ["painting_id", "mask_type"]
    ).reset_index(drop=True)

    total_cases = len(sorted_metadata)
    start_time = time.perf_counter()

    print("Starting classical metric computation")
    print(f"  Cases: {total_cases}")
    print(f"  Target size: {target_size}")
    print(f"  Mask bbox margin: {mask_bbox_margin}")
    print(f"  Expected metric rows: 900 for the full 50-painting experiment")

    for index, (_, row) in enumerate(sorted_metadata.iterrows(), start=1):
        if progress_every and (
            index == 1
            or index % progress_every == 0
            or index == total_cases
        ):
            elapsed = time.perf_counter() - start_time
            print(
                f"Computing classical metrics for case {index}/{total_cases} "
                f"({row['case_id']}) | elapsed {elapsed:.2f}s"
            )

        try:
            clean_arr = load_rgb_array(Path(row["clean_path"]))
            damaged_arr = load_rgb_array(Path(row["damaged_path"]))
            restored_arr = load_rgb_array(Path(row["restored_path"]))
            mask_bool = load_mask_bool(Path(row["mask_path"]))

            if clean_arr.shape != damaged_arr.shape or clean_arr.shape != restored_arr.shape:
                raise ValueError(
                    f"Image shape mismatch for case {row['case_id']}: "
                    f"clean={clean_arr.shape}, damaged={damaged_arr.shape}, "
                    f"restored={restored_arr.shape}"
                )

            if mask_bool.shape != clean_arr.shape[:2]:
                raise ValueError(
                    f"Mask shape mismatch for case {row['case_id']}: "
                    f"mask={mask_bool.shape}, image={clean_arr.shape[:2]}"
                )

            if clean_arr.shape[:2] != (target_size, target_size):
                raise ValueError(
                    f"Unexpected image size for case {row['case_id']}: "
                    f"{clean_arr.shape[:2]}"
                )

            # 1. Full image region
            damaged_full = compute_image_region_metrics(
                clean_arr,
                damaged_arr,
                compute_ssim_value=True,
            )
            restored_full = compute_image_region_metrics(
                clean_arr,
                restored_arr,
                compute_ssim_value=True,
            )

            metric_records.append(
                _build_metric_record(
                    row=row,
                    evaluation_region="full_image",
                    region_pixel_count=int(clean_arr.shape[0] * clean_arr.shape[1]),
                    damaged_metrics=damaged_full,
                    restored_metrics=restored_full,
                    region_info={
                        "region_x_min": 0,
                        "region_y_min": 0,
                        "region_x_max": clean_arr.shape[1],
                        "region_y_max": clean_arr.shape[0],
                    },
                )
            )

            # 2. Content region
            clean_content, damaged_content, restored_content, content_region_info = get_content_crop(
                row=row,
                clean_arr=clean_arr,
                damaged_arr=damaged_arr,
                restored_arr=restored_arr,
            )

            damaged_content_metrics = compute_image_region_metrics(
                clean_content,
                damaged_content,
                compute_ssim_value=True,
            )
            restored_content_metrics = compute_image_region_metrics(
                clean_content,
                restored_content,
                compute_ssim_value=True,
            )

            metric_records.append(
                _build_metric_record(
                    row=row,
                    evaluation_region="content_region",
                    region_pixel_count=int(clean_content.shape[0] * clean_content.shape[1]),
                    damaged_metrics=damaged_content_metrics,
                    restored_metrics=restored_content_metrics,
                    region_info=content_region_info,
                )
            )

            # Zero-control has no masked target region.
            if not np.any(mask_bool):
                continue

            # 3. Masked pixel region: MSE/MAE/PSNR only, no SSIM.
            damaged_mask_metrics = compute_masked_pixel_metrics(
                clean_arr,
                damaged_arr,
                mask_bool,
            )
            restored_mask_metrics = compute_masked_pixel_metrics(
                clean_arr,
                restored_arr,
                mask_bool,
            )

            metric_records.append(
                _build_metric_record(
                    row=row,
                    evaluation_region="masked_region",
                    region_pixel_count=int(mask_bool.sum()),
                    damaged_metrics=damaged_mask_metrics,
                    restored_metrics=restored_mask_metrics,
                    region_info={
                        "region_x_min": None,
                        "region_y_min": None,
                        "region_x_max": None,
                        "region_y_max": None,
                    },
                )
            )

            # 4. Mask bounding-box crop: image-like local region, supports SSIM.
            bbox = get_mask_bbox(mask_bool, margin=mask_bbox_margin)

            if bbox is not None:
                x_min = int(bbox["region_x_min"])
                y_min = int(bbox["region_y_min"])
                x_max = int(bbox["region_x_max"])
                y_max = int(bbox["region_y_max"])

                clean_bbox = clean_arr[y_min:y_max, x_min:x_max]
                damaged_bbox = damaged_arr[y_min:y_max, x_min:x_max]
                restored_bbox = restored_arr[y_min:y_max, x_min:x_max]

                damaged_bbox_metrics = compute_image_region_metrics(
                    clean_bbox,
                    damaged_bbox,
                    compute_ssim_value=True,
                )
                restored_bbox_metrics = compute_image_region_metrics(
                    clean_bbox,
                    restored_bbox,
                    compute_ssim_value=True,
                )

                metric_records.append(
                    _build_metric_record(
                        row=row,
                        evaluation_region="mask_bbox_crop",
                        region_pixel_count=int(clean_bbox.shape[0] * clean_bbox.shape[1]),
                        damaged_metrics=damaged_bbox_metrics,
                        restored_metrics=restored_bbox_metrics,
                        region_info=bbox,
                    )
                )

        except Exception as exc:
            metric_records.append(
                {
                    "case_id": row.get("case_id", ""),
                    "painting_id": row.get("painting_id", ""),
                    "category": row.get("category", ""),
                    "title": row.get("title", ""),
                    "mask_id": row.get("mask_id", ""),
                    "mask_type": row.get("mask_type", ""),
                    "model_name": row.get("model_name", ""),
                    "evaluation_region": "error",
                    "region_pixel_count": 0,
                    "region_x_min": None,
                    "region_y_min": None,
                    "region_x_max": None,
                    "region_y_max": None,
                    **{col: np.nan for col in CLASSICAL_METRIC_COLUMNS},
                    "status": "error",
                    "issue": f"{type(exc).__name__}: {exc}",
                }
            )

            print(
                f"  Error while computing case {index}/{total_cases} "
                f"({row.get('case_id', '')}): {type(exc).__name__}: {exc}"
            )

    metrics_df = pd.DataFrame(metric_records)
    elapsed_total = time.perf_counter() - start_time

    print("Classical metric computation complete")
    print(f"  Runtime: {elapsed_total:.2f} seconds")
    print(f"  Output rows: {len(metrics_df)}")

    if "evaluation_region" in metrics_df.columns:
        print("  Region counts:")
        print(metrics_df["evaluation_region"].value_counts().to_string())

    if "status" in metrics_df.columns:
        print("  Status counts:")
        print(metrics_df["status"].value_counts(dropna=False).to_string())

    return metrics_df


def validate_classical_metrics(
    metrics_df: pd.DataFrame,
    expected_rows: int = 900,
) -> pd.DataFrame:
    """Validate metric output structure."""
    required_columns = [
        "case_id",
        "painting_id",
        "mask_type",
        "model_name",
        "evaluation_region",
        "damaged_mse",
        "restored_mse",
        "damaged_mae",
        "restored_mae",
        "damaged_psnr",
        "restored_psnr",
        "status",
        "issue",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in metrics_df.columns
    ]

    validation_rows = []

    if missing_columns:
        validation_rows.append(
            {
                "check": "required_columns",
                "passed": False,
                "detail": f"Missing columns: {missing_columns}",
            }
        )
    else:
        validation_rows.append(
            {
                "check": "required_columns",
                "passed": True,
                "detail": "All required columns present.",
            }
        )

    validation_rows.append(
        {
            "check": "row_count",
            "passed": len(metrics_df) == expected_rows,
            "detail": f"Expected {expected_rows}, found {len(metrics_df)}.",
        }
    )

    if "status" in metrics_df.columns:
        error_rows = int((metrics_df["status"] != "ok").sum())
        validation_rows.append(
            {
                "check": "status_ok",
                "passed": error_rows == 0,
                "detail": f"Rows with non-ok status: {error_rows}.",
            }
        )

    if "evaluation_region" in metrics_df.columns:
        region_counts = metrics_df["evaluation_region"].value_counts().to_dict()
        validation_rows.append(
            {
                "check": "region_counts",
                "passed": True,
                "detail": str(region_counts),
            }
        )

    return pd.DataFrame(validation_rows)


def summarize_classical_metrics(
    metrics_df: pd.DataFrame,
    group_columns: list[str],
) -> pd.DataFrame:
    """Summarize classical metrics by one or more grouping columns.

    Infinite PSNR values are replaced with NaN for summary means, because
    zero-control would otherwise turn averages into mathematical confetti.
    """
    if not group_columns:
        raise ValueError("At least one group column is required.")

    missing_group_columns = [
        col for col in group_columns
        if col not in metrics_df.columns
    ]

    if missing_group_columns:
        raise ValueError(f"Metrics dataframe missing group columns: {missing_group_columns}")

    summary_df = metrics_df.copy()

    numeric_columns = [
        "damaged_mse",
        "restored_mse",
        "mse_improvement",
        "damaged_mae",
        "restored_mae",
        "mae_improvement",
        "damaged_psnr",
        "restored_psnr",
        "psnr_improvement",
        "damaged_ssim",
        "restored_ssim",
        "ssim_improvement",
    ]

    for col in numeric_columns:
        if col in summary_df.columns:
            summary_df[col] = summary_df[col].replace([np.inf, -np.inf], np.nan)

    return (
        summary_df
        .groupby(group_columns, dropna=False)
        .agg(
            rows=("case_id", "count"),
            cases=("case_id", "nunique"),
            mean_damaged_mse=("damaged_mse", "mean"),
            mean_restored_mse=("restored_mse", "mean"),
            mean_mse_improvement=("mse_improvement", "mean"),
            mean_damaged_mae=("damaged_mae", "mean"),
            mean_restored_mae=("restored_mae", "mean"),
            mean_mae_improvement=("mae_improvement", "mean"),
            mean_damaged_psnr=("damaged_psnr", "mean"),
            mean_restored_psnr=("restored_psnr", "mean"),
            mean_psnr_improvement=("psnr_improvement", "mean"),
            mean_damaged_ssim=("damaged_ssim", "mean"),
            mean_restored_ssim=("restored_ssim", "mean"),
            mean_ssim_improvement=("ssim_improvement", "mean"),
            mean_region_pixel_count=("region_pixel_count", "mean"),
        )
        .reset_index()
        .round(4)
    )