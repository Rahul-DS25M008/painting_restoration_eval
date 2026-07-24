"""
Classical full-reference image-restoration metrics.

This module evaluates damaged and restored painting images against the clean
reference image across a standardized set of spatial regions.

Mask convention
---------------
- 0: preserved/original region
- non-zero: damaged/restored region

Region policy
-------------
Every case:
- full_image
- content_region

Non-zero-mask cases:
- masked_region
- mask_bbox_crop
- boundary_region
- outside_mask_region

SSIM is computed only for contiguous rectangular image regions. It is therefore
reported for full_image, content_region, and mask_bbox_crop, but not for sparse
or irregular pixel selections such as masked_region, boundary_region, and
outside_mask_region.
"""

from __future__ import annotations

import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import skimage
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from skimage.morphology import binary_dilation, binary_erosion, disk


METRIC_MODULE_NAME = "restoration_eval.metrics_classical"
METRIC_VERSION = "2.0.0"

BASE_REGIONS = ("full_image", "content_region")
MASKED_CASE_REGIONS = (
    "masked_region",
    "mask_bbox_crop",
    "boundary_region",
    "outside_mask_region",
)
ALL_EVALUATION_REGIONS = BASE_REGIONS + MASKED_CASE_REGIONS

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


def load_rgb_array(path: Path | str) -> np.ndarray:
    """Load an image as an RGB float32 array in the range [0, 255]."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.float32)


def load_mask_bool(path: Path | str) -> np.ndarray:
    """Load a mask as a boolean array."""
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


def compute_psnr_from_mse(
    mse_value: float,
    data_range: float = 255.0,
) -> float:
    """Compute PSNR from MSE, returning infinity for an exact match."""
    if np.isnan(mse_value):
        return float("nan")

    if mse_value == 0:
        return float("inf")

    return float(20.0 * np.log10(data_range / np.sqrt(mse_value)))


def compute_ssim_safe(
    reference_arr: np.ndarray,
    candidate_arr: np.ndarray,
    data_range: float = 255.0,
) -> float:
    """Compute RGB SSIM safely for a contiguous rectangular image region."""
    if reference_arr.shape != candidate_arr.shape:
        raise ValueError(
            f"SSIM shape mismatch. Reference: {reference_arr.shape}, "
            f"candidate: {candidate_arr.shape}"
        )

    if reference_arr.ndim != 3 or reference_arr.shape[2] != 3:
        raise ValueError(
            f"Expected RGB arrays with shape HxWx3, got {reference_arr.shape}"
        )

    min_dim = min(reference_arr.shape[:2])

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
    """Compute metrics for a contiguous rectangular image region."""
    if clean_arr.shape != candidate_arr.shape:
        raise ValueError(
            f"Image shape mismatch. Clean: {clean_arr.shape}, "
            f"candidate: {candidate_arr.shape}"
        )

    mse_value = compute_mse(clean_arr, candidate_arr)
    mae_value = compute_mae(clean_arr, candidate_arr)
    psnr_value = compute_psnr_from_mse(mse_value)
    ssim_value = (
        compute_ssim_safe(clean_arr, candidate_arr)
        if compute_ssim_value
        else float("nan")
    )

    return {
        "mse": mse_value,
        "mae": mae_value,
        "psnr": psnr_value,
        "ssim": ssim_value,
    }


def compute_selected_pixel_metrics(
    clean_arr: np.ndarray,
    candidate_arr: np.ndarray,
    selection_bool: np.ndarray,
) -> dict[str, float]:
    """Compute MSE, MAE, and PSNR over an arbitrary boolean pixel selection.

    SSIM is intentionally omitted because sparse or irregular pixel selections
    do not preserve the local spatial structure required by SSIM.
    """
    if clean_arr.shape != candidate_arr.shape:
        raise ValueError(
            f"Image shape mismatch. Clean: {clean_arr.shape}, "
            f"candidate: {candidate_arr.shape}"
        )

    if selection_bool.shape != clean_arr.shape[:2]:
        raise ValueError(
            f"Selection shape mismatch. Selection: {selection_bool.shape}, "
            f"image: {clean_arr.shape[:2]}"
        )

    if not np.any(selection_bool):
        return {
            "mse": float("nan"),
            "mae": float("nan"),
            "psnr": float("nan"),
            "ssim": float("nan"),
        }

    clean_pixels = clean_arr[selection_bool]
    candidate_pixels = candidate_arr[selection_bool]

    mse_value = compute_mse(clean_pixels, candidate_pixels)
    mae_value = compute_mae(clean_pixels, candidate_pixels)

    return {
        "mse": mse_value,
        "mae": mae_value,
        "psnr": compute_psnr_from_mse(mse_value),
        "ssim": float("nan"),
    }


def compute_masked_pixel_metrics(
    clean_arr: np.ndarray,
    candidate_arr: np.ndarray,
    mask_bool: np.ndarray,
) -> dict[str, float]:
    """Backward-compatible alias for masked-pixel metric computation."""
    return compute_selected_pixel_metrics(clean_arr, candidate_arr, mask_bool)


def get_content_bounds(
    row: pd.Series,
    image_shape: tuple[int, int],
) -> dict[str, int]:
    """Return validated content-region coordinates."""
    required_columns = [
        "content_x_min",
        "content_y_min",
        "content_x_max",
        "content_y_max",
    ]
    missing_columns = [col for col in required_columns if col not in row.index]

    if missing_columns:
        raise ValueError(f"Missing content-region columns: {missing_columns}")

    height, width = image_shape

    x_min = max(0, min(int(row["content_x_min"]), width))
    x_max = max(0, min(int(row["content_x_max"]), width))
    y_min = max(0, min(int(row["content_y_min"]), height))
    y_max = max(0, min(int(row["content_y_max"]), height))

    if x_max <= x_min or y_max <= y_min:
        raise ValueError(
            "Invalid content region: "
            f"x_min={x_min}, y_min={y_min}, x_max={x_max}, y_max={y_max}"
        )

    return {
        "region_x_min": x_min,
        "region_y_min": y_min,
        "region_x_max": x_max,
        "region_y_max": y_max,
    }


def get_content_crop(
    row: pd.Series,
    clean_arr: np.ndarray,
    damaged_arr: np.ndarray,
    restored_arr: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    """Extract the recorded painting-content region."""
    region_info = get_content_bounds(row, clean_arr.shape[:2])

    x_min = region_info["region_x_min"]
    y_min = region_info["region_y_min"]
    x_max = region_info["region_x_max"]
    y_max = region_info["region_y_max"]

    return (
        clean_arr[y_min:y_max, x_min:x_max],
        damaged_arr[y_min:y_max, x_min:x_max],
        restored_arr[y_min:y_max, x_min:x_max],
        region_info,
    )


def get_content_mask(
    row: pd.Series,
    image_shape: tuple[int, int],
) -> np.ndarray:
    """Build a boolean mask for the recorded content region."""
    region_info = get_content_bounds(row, image_shape)
    content_mask = np.zeros(image_shape, dtype=bool)

    content_mask[
        region_info["region_y_min"]:region_info["region_y_max"],
        region_info["region_x_min"]:region_info["region_x_max"],
    ] = True

    return content_mask


def get_mask_bbox(
    mask_bool: np.ndarray,
    margin: int = 8,
) -> dict[str, int] | None:
    """Return a mask bounding box with margin using slice-style coordinates."""
    if margin < 0:
        raise ValueError("mask_bbox_margin must be non-negative.")

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


def build_boundary_mask(
    mask_bool: np.ndarray,
    width: int = 3,
    content_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Build an inside-and-outside morphological boundary band.

    The band is defined as dilated(mask) XOR eroded(mask). When a content mask is
    provided, boundary pixels are restricted to the painting-content region.
    """
    if width < 1:
        raise ValueError("boundary_width must be at least 1.")

    footprint = disk(width)
    dilated = binary_dilation(mask_bool, footprint=footprint)
    eroded = binary_erosion(mask_bool, footprint=footprint)
    boundary = np.logical_xor(dilated, eroded)

    if content_mask is not None:
        if content_mask.shape != mask_bool.shape:
            raise ValueError(
                f"Content-mask shape mismatch: {content_mask.shape} "
                f"vs {mask_bool.shape}"
            )
        boundary &= content_mask

    return boundary


def _empty_metrics() -> dict[str, float]:
    return {
        "mse": float("nan"),
        "mae": float("nan"),
        "psnr": float("nan"),
        "ssim": float("nan"),
    }


def _safe_difference(left: float, right: float) -> float:
    """Return left-right while preserving meaningful infinities and NaNs."""
    if np.isnan(left) or np.isnan(right):
        return float("nan")

    if np.isinf(left) and np.isinf(right):
        return 0.0

    return float(left - right)


def _row_value(row: pd.Series, key: str, default: Any = "") -> Any:
    value = row.get(key, default)
    return default if pd.isna(value) else value


def _build_metric_record(
    row: pd.Series,
    evaluation_region: str,
    region_pixel_count: int,
    damaged_metrics: dict[str, float],
    restored_metrics: dict[str, float],
    region_info: dict[str, int | None],
    metric_timestamp_utc: str,
    status: str = "ok",
    issue: str = "",
) -> dict[str, Any]:
    """Build one standardized metric output row."""
    damaged_mse = damaged_metrics["mse"]
    restored_mse = restored_metrics["mse"]
    damaged_mae = damaged_metrics["mae"]
    restored_mae = restored_metrics["mae"]
    damaged_psnr = damaged_metrics["psnr"]
    restored_psnr = restored_metrics["psnr"]
    damaged_ssim = damaged_metrics["ssim"]
    restored_ssim = restored_metrics["ssim"]

    return {
        "dataset_name": _row_value(row, "dataset_name", "canonical"),
        "case_id": _row_value(row, "case_id"),
        "painting_id": _row_value(row, "painting_id"),
        "category": _row_value(row, "category"),
        "title": _row_value(row, "title"),
        "mask_id": _row_value(row, "mask_id"),
        "mask_type": _row_value(row, "mask_type"),
        "model_name": _row_value(row, "model_name"),
        "evaluation_region": evaluation_region,
        "region_pixel_count": int(region_pixel_count),
        "region_x_min": region_info.get("region_x_min"),
        "region_y_min": region_info.get("region_y_min"),
        "region_x_max": region_info.get("region_x_max"),
        "region_y_max": region_info.get("region_y_max"),
        "damaged_area_pixels": row.get("damaged_area_pixels", np.nan),
        "damaged_area_percentage_content": row.get(
            "damaged_area_percentage_content", np.nan
        ),
        "damaged_area_percentage_full": row.get(
            "damaged_area_percentage_full", np.nan
        ),
        "damaged_mse": damaged_mse,
        "restored_mse": restored_mse,
        "mse_improvement": _safe_difference(damaged_mse, restored_mse),
        "damaged_mae": damaged_mae,
        "restored_mae": restored_mae,
        "mae_improvement": _safe_difference(damaged_mae, restored_mae),
        "damaged_psnr": damaged_psnr,
        "restored_psnr": restored_psnr,
        "psnr_improvement": _safe_difference(restored_psnr, damaged_psnr),
        "damaged_ssim": damaged_ssim,
        "restored_ssim": restored_ssim,
        "ssim_improvement": _safe_difference(restored_ssim, damaged_ssim),
        "metric_module": METRIC_MODULE_NAME,
        "metric_version": METRIC_VERSION,
        "metric_timestamp_utc": metric_timestamp_utc,
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "skimage_version": skimage.__version__,
        "status": status,
        "issue": issue,
    }


def expected_metric_rows_from_metadata(
    restoration_metadata: pd.DataFrame,
) -> int:
    """Return the deterministic expected row count for the region policy.

    Each case receives two base-region rows. Cases with a non-zero mask receive
    four additional rows.
    """
    required_columns = ["mask_path"]
    missing_columns = [
        col for col in required_columns
        if col not in restoration_metadata.columns
    ]
    if missing_columns:
        raise ValueError(
            f"Restoration metadata missing required columns: {missing_columns}"
        )

    nonzero_mask_cases = 0

    for mask_path in restoration_metadata["mask_path"]:
        if np.any(load_mask_bool(mask_path)):
            nonzero_mask_cases += 1

    return (
        len(restoration_metadata) * len(BASE_REGIONS)
        + nonzero_mask_cases * len(MASKED_CASE_REGIONS)
    )


def expected_region_counts_from_metadata(
    restoration_metadata: pd.DataFrame,
) -> dict[str, int]:
    """Return expected output counts for every evaluation region."""
    nonzero_mask_cases = sum(
        bool(np.any(load_mask_bool(mask_path)))
        for mask_path in restoration_metadata["mask_path"]
    )

    counts = {
        "full_image": len(restoration_metadata),
        "content_region": len(restoration_metadata),
    }

    for region in MASKED_CASE_REGIONS:
        counts[region] = nonzero_mask_cases

    return counts


def compute_classical_metrics_for_restorations(
    restoration_metadata: pd.DataFrame,
    target_size: int | tuple[int, int] | None = 768,
    mask_bbox_margin: int = 8,
    boundary_width: int = 3,
    progress_every: int | None = 25,
) -> pd.DataFrame:
    """Compute classical metrics for restoration outputs.

    Input metadata must combine restoration paths with preprocessing content
    coordinates. Output contains one row per dataset, case, model, and
    evaluation region.
    """
    required_columns = [
        "case_id",
        "painting_id",
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
        raise ValueError(
            f"Restoration metadata missing required columns: {missing_columns}"
        )

    if restoration_metadata.empty:
        raise ValueError("Restoration metadata is empty.")

    sort_columns = [
        col
        for col in ["dataset_name", "painting_id", "mask_type", "case_id"]
        if col in restoration_metadata.columns
    ]
    sorted_metadata = restoration_metadata.sort_values(sort_columns).reset_index(
        drop=True
    )

    if target_size is None:
        expected_shape = None
    elif isinstance(target_size, int):
        expected_shape = (target_size, target_size)
    else:
        expected_shape = tuple(target_size)

    metric_records: list[dict[str, Any]] = []
    total_cases = len(sorted_metadata)
    start_time = time.perf_counter()
    metric_timestamp_utc = datetime.now(timezone.utc).isoformat()

    print("Starting classical metric computation")
    print(f"  Cases: {total_cases}")
    print(f"  Target shape: {expected_shape or 'not enforced'}")
    print(f"  Mask bbox margin: {mask_bbox_margin}")
    print(f"  Boundary width: {boundary_width}")

    for index, (_, row) in enumerate(sorted_metadata.iterrows(), start=1):
        if progress_every and (
            index == 1
            or index % progress_every == 0
            or index == total_cases
        ):
            elapsed = time.perf_counter() - start_time
            print(
                f"Computing case {index}/{total_cases} "
                f"({row['case_id']}) | elapsed {elapsed:.2f}s"
            )

        try:
            clean_arr = load_rgb_array(row["clean_path"])
            damaged_arr = load_rgb_array(row["damaged_path"])
            restored_arr = load_rgb_array(row["restored_path"])
            mask_bool = load_mask_bool(row["mask_path"])

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

            if expected_shape is not None and clean_arr.shape[:2] != expected_shape:
                raise ValueError(
                    f"Unexpected image size for case {row['case_id']}: "
                    f"{clean_arr.shape[:2]}, expected {expected_shape}"
                )

            full_region_info = {
                "region_x_min": 0,
                "region_y_min": 0,
                "region_x_max": clean_arr.shape[1],
                "region_y_max": clean_arr.shape[0],
            }
            metric_records.append(
                _build_metric_record(
                    row=row,
                    evaluation_region="full_image",
                    region_pixel_count=int(np.prod(clean_arr.shape[:2])),
                    damaged_metrics=compute_image_region_metrics(
                        clean_arr, damaged_arr, compute_ssim_value=True
                    ),
                    restored_metrics=compute_image_region_metrics(
                        clean_arr, restored_arr, compute_ssim_value=True
                    ),
                    region_info=full_region_info,
                    metric_timestamp_utc=metric_timestamp_utc,
                )
            )

            (
                clean_content,
                damaged_content,
                restored_content,
                content_region_info,
            ) = get_content_crop(row, clean_arr, damaged_arr, restored_arr)

            metric_records.append(
                _build_metric_record(
                    row=row,
                    evaluation_region="content_region",
                    region_pixel_count=int(np.prod(clean_content.shape[:2])),
                    damaged_metrics=compute_image_region_metrics(
                        clean_content, damaged_content, compute_ssim_value=True
                    ),
                    restored_metrics=compute_image_region_metrics(
                        clean_content, restored_content, compute_ssim_value=True
                    ),
                    region_info=content_region_info,
                    metric_timestamp_utc=metric_timestamp_utc,
                )
            )

            if not np.any(mask_bool):
                continue

            content_mask = get_content_mask(row, clean_arr.shape[:2])

            region_selections = {
                "masked_region": mask_bool,
                "boundary_region": build_boundary_mask(
                    mask_bool,
                    width=boundary_width,
                    content_mask=content_mask,
                ),
                "outside_mask_region": content_mask & ~mask_bool,
            }

            for evaluation_region, selection_bool in region_selections.items():
                metric_records.append(
                    _build_metric_record(
                        row=row,
                        evaluation_region=evaluation_region,
                        region_pixel_count=int(selection_bool.sum()),
                        damaged_metrics=compute_selected_pixel_metrics(
                            clean_arr, damaged_arr, selection_bool
                        ),
                        restored_metrics=compute_selected_pixel_metrics(
                            clean_arr, restored_arr, selection_bool
                        ),
                        region_info={
                            "region_x_min": None,
                            "region_y_min": None,
                            "region_x_max": None,
                            "region_y_max": None,
                        },
                        metric_timestamp_utc=metric_timestamp_utc,
                    )
                )

            bbox = get_mask_bbox(mask_bool, margin=mask_bbox_margin)

            if bbox is None:
                metric_records.append(
                    _build_metric_record(
                        row=row,
                        evaluation_region="mask_bbox_crop",
                        region_pixel_count=0,
                        damaged_metrics=_empty_metrics(),
                        restored_metrics=_empty_metrics(),
                        region_info={
                            "region_x_min": None,
                            "region_y_min": None,
                            "region_x_max": None,
                            "region_y_max": None,
                        },
                        metric_timestamp_utc=metric_timestamp_utc,
                        status="warning",
                        issue="Non-zero mask produced no valid bounding box.",
                    )
                )
            else:
                x_min = bbox["region_x_min"]
                y_min = bbox["region_y_min"]
                x_max = bbox["region_x_max"]
                y_max = bbox["region_y_max"]

                clean_bbox = clean_arr[y_min:y_max, x_min:x_max]
                damaged_bbox = damaged_arr[y_min:y_max, x_min:x_max]
                restored_bbox = restored_arr[y_min:y_max, x_min:x_max]

                metric_records.append(
                    _build_metric_record(
                        row=row,
                        evaluation_region="mask_bbox_crop",
                        region_pixel_count=int(np.prod(clean_bbox.shape[:2])),
                        damaged_metrics=compute_image_region_metrics(
                            clean_bbox, damaged_bbox, compute_ssim_value=True
                        ),
                        restored_metrics=compute_image_region_metrics(
                            clean_bbox, restored_bbox, compute_ssim_value=True
                        ),
                        region_info=bbox,
                        metric_timestamp_utc=metric_timestamp_utc,
                    )
                )

        except Exception as exc:
            error_record = {
                "dataset_name": _row_value(row, "dataset_name", "canonical"),
                "case_id": _row_value(row, "case_id"),
                "painting_id": _row_value(row, "painting_id"),
                "category": _row_value(row, "category"),
                "title": _row_value(row, "title"),
                "mask_id": _row_value(row, "mask_id"),
                "mask_type": _row_value(row, "mask_type"),
                "model_name": _row_value(row, "model_name"),
                "evaluation_region": "error",
                "region_pixel_count": 0,
                "region_x_min": None,
                "region_y_min": None,
                "region_x_max": None,
                "region_y_max": None,
                "damaged_area_pixels": row.get("damaged_area_pixels", np.nan),
                "damaged_area_percentage_content": row.get(
                    "damaged_area_percentage_content", np.nan
                ),
                "damaged_area_percentage_full": row.get(
                    "damaged_area_percentage_full", np.nan
                ),
                **{col: np.nan for col in CLASSICAL_METRIC_COLUMNS},
                "metric_module": METRIC_MODULE_NAME,
                "metric_version": METRIC_VERSION,
                "metric_timestamp_utc": metric_timestamp_utc,
                "python_version": platform.python_version(),
                "numpy_version": np.__version__,
                "pandas_version": pd.__version__,
                "skimage_version": skimage.__version__,
                "status": "error",
                "issue": f"{type(exc).__name__}: {exc}",
            }
            metric_records.append(error_record)

            print(
                f"  Error in case {index}/{total_cases} "
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
    expected_rows: int | None = None,
    expected_region_counts: dict[str, int] | None = None,
    key_columns: Iterable[str] = (
        "dataset_name",
        "case_id",
        "model_name",
        "evaluation_region",
    ),
) -> pd.DataFrame:
    """Validate metric output structure, row counts, status, and uniqueness."""
    required_columns = [
        "dataset_name",
        "case_id",
        "painting_id",
        "model_name",
        "evaluation_region",
        "region_pixel_count",
        "damaged_mse",
        "restored_mse",
        "damaged_mae",
        "restored_mae",
        "damaged_psnr",
        "restored_psnr",
        "metric_module",
        "metric_version",
        "status",
        "issue",
    ]

    validation_rows: list[dict[str, Any]] = []
    missing_columns = [
        col for col in required_columns
        if col not in metrics_df.columns
    ]

    validation_rows.append(
        {
            "check": "required_columns",
            "passed": not missing_columns,
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
                "passed": len(metrics_df) == expected_rows,
                "detail": f"Expected {expected_rows}, found {len(metrics_df)}.",
            }
        )

    if "status" in metrics_df.columns:
        error_rows = int((metrics_df["status"] == "error").sum())
        warning_rows = int((metrics_df["status"] == "warning").sum())
        validation_rows.append(
            {
                "check": "no_error_rows",
                "passed": error_rows == 0,
                "detail": (
                    f"Error rows: {error_rows}; warning rows: {warning_rows}."
                ),
            }
        )

    available_key_columns = [
        col for col in key_columns
        if col in metrics_df.columns
    ]
    if len(available_key_columns) == len(tuple(key_columns)):
        duplicate_rows = int(
            metrics_df.duplicated(available_key_columns, keep=False).sum()
        )
        validation_rows.append(
            {
                "check": "unique_metric_keys",
                "passed": duplicate_rows == 0,
                "detail": (
                    f"Rows participating in duplicate metric keys: "
                    f"{duplicate_rows}."
                ),
            }
        )

    if expected_region_counts is not None and "evaluation_region" in metrics_df.columns:
        actual_region_counts = (
            metrics_df["evaluation_region"].value_counts().to_dict()
        )
        mismatches = {
            region: {
                "expected": expected_count,
                "actual": int(actual_region_counts.get(region, 0)),
            }
            for region, expected_count in expected_region_counts.items()
            if int(actual_region_counts.get(region, 0)) != int(expected_count)
        }
        validation_rows.append(
            {
                "check": "region_counts",
                "passed": not mismatches,
                "detail": (
                    "All evaluation-region counts match expectations."
                    if not mismatches
                    else f"Mismatches: {mismatches}"
                ),
            }
        )

    if "region_pixel_count" in metrics_df.columns:
        invalid_counts = int(
            (
                (metrics_df["status"] == "ok")
                & (metrics_df["region_pixel_count"] <= 0)
            ).sum()
        )
        validation_rows.append(
            {
                "check": "positive_region_pixel_counts",
                "passed": invalid_counts == 0,
                "detail": (
                    f"Successful rows with non-positive region size: "
                    f"{invalid_counts}."
                ),
            }
        )

    return pd.DataFrame(validation_rows)


def summarize_classical_metrics(
    metrics_df: pd.DataFrame,
    group_columns: list[str],
) -> pd.DataFrame:
    """Summarize classical metrics by one or more grouping columns."""
    if not group_columns:
        raise ValueError("At least one group column is required.")

    missing_group_columns = [
        col for col in group_columns
        if col not in metrics_df.columns
    ]
    if missing_group_columns:
        raise ValueError(
            f"Metrics dataframe missing group columns: {missing_group_columns}"
        )

    summary_df = metrics_df.copy()

    if "status" in summary_df.columns:
        summary_df = summary_df[summary_df["status"] != "error"].copy()

    numeric_columns = [
        *CLASSICAL_METRIC_COLUMNS,
        "region_pixel_count",
    ]

    for col in numeric_columns:
        if col in summary_df.columns:
            summary_df[col] = summary_df[col].replace(
                [np.inf, -np.inf], np.nan
            )

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
