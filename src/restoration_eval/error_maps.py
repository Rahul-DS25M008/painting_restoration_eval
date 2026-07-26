"""
Error-map utilities for the painting restoration evaluation project.

This module creates reusable spatial diagnostics comparing:

- clean image vs damaged image,
- clean image vs restored image,
- damaged error vs restored error,
- signed restoration improvement,
- masked signed improvement,
- boundary-focused signed improvement,
- standardized overlays for masks and bounding boxes.

The binary mask remains the authoritative definition of the artificially
damaged/restored region.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.patches import Patch, Rectangle
from PIL import Image
from skimage.morphology import binary_dilation, binary_erosion, disk


DEFAULT_ERROR_CMAP = "magma"
DEFAULT_SIGNED_CMAP = "coolwarm"

DEFAULT_MASK_OVERLAY_RGB = (255, 255, 255)
DEFAULT_BOUNDARY_OVERLAY_RGB = (255, 215, 0)
DEFAULT_CONTENT_BOX_RGB = (0, 255, 255)
DEFAULT_MASK_BOX_RGB = (255, 0, 255)


def load_rgb_array(path: Path) -> np.ndarray:
    """Load an RGB image as a float32 NumPy array in range [0, 255]."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.float32)


def load_mask_bool(
    path: Path,
    threshold: int = 0,
) -> np.ndarray:
    """Load a mask as a boolean array where True means damaged/missing."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Mask file not found: {path}")

    with Image.open(path) as image:
        mask = np.asarray(image.convert("L"))

    return mask > threshold


def load_image_for_display(
    path: Path,
    mode: str = "RGB",
) -> Image.Image:
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

    Returns
    -------
    np.ndarray
        Two-dimensional float32 array in range [0, 255].
    """
    if clean_arr.shape != candidate_arr.shape:
        raise ValueError(
            f"Image shapes do not match: clean={clean_arr.shape}, "
            f"candidate={candidate_arr.shape}"
        )

    if clean_arr.ndim != 3 or clean_arr.shape[2] != 3:
        raise ValueError(
            "Expected RGB arrays with shape (height, width, 3), "
            f"received {clean_arr.shape}."
        )

    return np.mean(
        np.abs(
            clean_arr.astype(np.float32)
            - candidate_arr.astype(np.float32)
        ),
        axis=2,
        dtype=np.float32,
    )


def compute_signed_improvement_map(
    damaged_error_map: np.ndarray,
    restored_error_map: np.ndarray,
) -> np.ndarray:
    """Compute signed per-pixel restoration improvement.

    Positive values mean the restored image is closer to the clean reference
    than the damaged image. Negative values mean it is farther away.
    """
    if damaged_error_map.shape != restored_error_map.shape:
        raise ValueError(
            f"Error-map shapes do not match: damaged={damaged_error_map.shape}, "
            f"restored={restored_error_map.shape}"
        )

    return (
        damaged_error_map.astype(np.float32)
        - restored_error_map.astype(np.float32)
    )


def apply_mask_to_map(
    map_arr: np.ndarray,
    mask_bool: np.ndarray,
    outside_value: float = np.nan,
) -> np.ndarray:
    """Return a copy of a 2D map with pixels outside the mask suppressed."""
    if map_arr.shape != mask_bool.shape:
        raise ValueError(
            f"Map and mask shapes do not match: map={map_arr.shape}, "
            f"mask={mask_bool.shape}"
        )

    masked_map = np.full(
        map_arr.shape,
        outside_value,
        dtype=np.float32,
    )
    masked_map[mask_bool] = map_arr[mask_bool]

    return masked_map


def safe_filename(value: str) -> str:
    """Create a filesystem-safe filename component."""
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9_\-]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_")


def clip_bbox(
    bbox: Sequence[int | float] | None,
    width: int,
    height: int,
) -> tuple[int, int, int, int] | None:
    """Clip an ``(x_min, y_min, x_max, y_max)`` box to image bounds.

    Coordinates use an exclusive maximum convention.
    """
    if bbox is None:
        return None

    if len(bbox) != 4:
        raise ValueError(
            f"Bounding box must contain four values, received {bbox}."
        )

    x_min, y_min, x_max, y_max = [
        int(round(float(value)))
        for value in bbox
    ]

    x_min = max(0, min(x_min, width))
    x_max = max(0, min(x_max, width))
    y_min = max(0, min(y_min, height))
    y_max = max(0, min(y_max, height))

    if x_max <= x_min or y_max <= y_min:
        return None

    return x_min, y_min, x_max, y_max


def bbox_from_binary_mask(
    mask_bool: np.ndarray,
    margin: int = 0,
) -> tuple[int, int, int, int] | None:
    """Return the tight mask box using exclusive maximum coordinates."""
    if mask_bool.ndim != 2:
        raise ValueError(
            f"Expected a two-dimensional mask, received {mask_bool.shape}."
        )

    y_coords, x_coords = np.where(mask_bool)

    if len(x_coords) == 0:
        return None

    height, width = mask_bool.shape

    bbox = (
        int(x_coords.min()) - int(margin),
        int(y_coords.min()) - int(margin),
        int(x_coords.max()) + 1 + int(margin),
        int(y_coords.max()) + 1 + int(margin),
    )

    return clip_bbox(
        bbox=bbox,
        width=width,
        height=height,
    )


def build_boundary_ring(
    mask_bool: np.ndarray,
    width_pixels: int = 3,
    mode: str = "both",
) -> np.ndarray:
    """Build a boundary ring around a binary mask.

    Parameters
    ----------
    mask_bool:
        Two-dimensional boolean mask.
    width_pixels:
        Radius of the morphological structuring element.
    mode:
        ``"inner"``, ``"outer"`` or ``"both"``.
    """
    if mask_bool.ndim != 2:
        raise ValueError(
            f"Expected a two-dimensional mask, received {mask_bool.shape}."
        )

    if width_pixels < 1:
        raise ValueError("width_pixels must be at least 1.")

    normalized_mode = str(mode).strip().lower()

    if normalized_mode not in {"inner", "outer", "both"}:
        raise ValueError(
            "mode must be one of {'inner', 'outer', 'both'}."
        )

    footprint = disk(int(width_pixels))

    eroded = binary_erosion(mask_bool, footprint=footprint)
    dilated = binary_dilation(mask_bool, footprint=footprint)

    inner_ring = mask_bool & ~eroded
    outer_ring = dilated & ~mask_bool

    if normalized_mode == "inner":
        return inner_ring
    if normalized_mode == "outer":
        return outer_ring

    return inner_ring | outer_ring


def _normalize_rgb_triplet(
    rgb: Sequence[int | float],
) -> np.ndarray:
    """Return an RGB triplet as float32 in range [0, 255]."""
    if len(rgb) != 3:
        raise ValueError("RGB values must contain exactly three elements.")

    normalized = np.asarray(rgb, dtype=np.float32)

    if np.any(normalized < 0) or np.any(normalized > 255):
        raise ValueError("RGB values must be within [0, 255].")

    return normalized


def create_spatial_overlay(
    image_arr: np.ndarray,
    mask_bool: np.ndarray,
    boundary_bool: np.ndarray | None = None,
    mask_alpha: float = 0.22,
    boundary_alpha: float = 0.85,
    mask_rgb: Sequence[int | float] = DEFAULT_MASK_OVERLAY_RGB,
    boundary_rgb: Sequence[int | float] = DEFAULT_BOUNDARY_OVERLAY_RGB,
) -> np.ndarray:
    """Create an RGB overlay containing mask fill and boundary highlighting."""
    if image_arr.ndim != 3 or image_arr.shape[2] != 3:
        raise ValueError(
            f"Expected RGB image array, received {image_arr.shape}."
        )

    if image_arr.shape[:2] != mask_bool.shape:
        raise ValueError(
            f"Image and mask shapes do not match: image={image_arr.shape[:2]}, "
            f"mask={mask_bool.shape}."
        )

    if not 0.0 <= mask_alpha <= 1.0:
        raise ValueError("mask_alpha must be in range [0, 1].")

    if not 0.0 <= boundary_alpha <= 1.0:
        raise ValueError("boundary_alpha must be in range [0, 1].")

    if boundary_bool is not None and boundary_bool.shape != mask_bool.shape:
        raise ValueError(
            f"Boundary and mask shapes do not match: "
            f"boundary={boundary_bool.shape}, mask={mask_bool.shape}."
        )

    overlay = image_arr.astype(np.float32).copy()
    mask_colour = _normalize_rgb_triplet(mask_rgb)

    overlay[mask_bool] = (
        (1.0 - mask_alpha) * overlay[mask_bool]
        + mask_alpha * mask_colour
    )

    if boundary_bool is not None:
        boundary_colour = _normalize_rgb_triplet(boundary_rgb)
        overlay[boundary_bool] = (
            (1.0 - boundary_alpha) * overlay[boundary_bool]
            + boundary_alpha * boundary_colour
        )

    return np.clip(overlay, 0, 255).astype(np.uint8)


def draw_bbox(
    axis: Axes,
    bbox: Sequence[int | float] | None,
    edgecolor: Any,
    linestyle: str = "-",
    linewidth: float = 1.8,
    label: str | None = None,
) -> None:
    """Draw a clipped bounding box on a Matplotlib axis."""
    if bbox is None:
        return

    x_min, y_min, x_max, y_max = bbox

    rectangle = Rectangle(
        (x_min, y_min),
        x_max - x_min,
        y_max - y_min,
        fill=False,
        edgecolor=edgecolor,
        linestyle=linestyle,
        linewidth=linewidth,
        label=label,
    )
    axis.add_patch(rectangle)


def _coerce_optional_bbox_from_row(
    case_row: pd.Series | Mapping[str, Any],
    candidate_column_sets: Sequence[Sequence[str]],
    width: int,
    height: int,
) -> tuple[int, int, int, int] | None:
    """Extract the first available valid bounding box from a case row."""
    for columns in candidate_column_sets:
        if not all(column in case_row for column in columns):
            continue

        values = [case_row.get(column) for column in columns]

        if any(pd.isna(value) for value in values):
            continue

        return clip_bbox(
            bbox=values,
            width=width,
            height=height,
        )

    return None


def compute_map_region_summary(
    map_arr: np.ndarray,
    region_bool: np.ndarray,
    prefix: str,
) -> dict[str, Any]:
    """Summarize a numeric map over a boolean region."""
    if map_arr.shape != region_bool.shape:
        raise ValueError(
            f"Map and region shapes do not match: map={map_arr.shape}, "
            f"region={region_bool.shape}."
        )

    values = map_arr[region_bool]
    pixel_count = int(values.size)

    if pixel_count == 0:
        return {
            f"{prefix}_pixel_count": 0,
            f"{prefix}_mean": float("nan"),
            f"{prefix}_std": float("nan"),
            f"{prefix}_min": float("nan"),
            f"{prefix}_max": float("nan"),
            f"{prefix}_positive_pixels": 0,
            f"{prefix}_negative_pixels": 0,
            f"{prefix}_zero_pixels": 0,
            f"{prefix}_positive_percentage": float("nan"),
            f"{prefix}_negative_percentage": float("nan"),
            f"{prefix}_zero_percentage": float("nan"),
        }

    positive_pixels = int((values > 0).sum())
    negative_pixels = int((values < 0).sum())
    zero_pixels = int((values == 0).sum())

    return {
        f"{prefix}_pixel_count": pixel_count,
        f"{prefix}_mean": float(values.mean()),
        f"{prefix}_std": float(values.std(ddof=0)),
        f"{prefix}_min": float(values.min()),
        f"{prefix}_max": float(values.max()),
        f"{prefix}_positive_pixels": positive_pixels,
        f"{prefix}_negative_pixels": negative_pixels,
        f"{prefix}_zero_pixels": zero_pixels,
        f"{prefix}_positive_percentage": (
            positive_pixels / pixel_count * 100.0
        ),
        f"{prefix}_negative_percentage": (
            negative_pixels / pixel_count * 100.0
        ),
        f"{prefix}_zero_percentage": (
            zero_pixels / pixel_count * 100.0
        ),
    }


def compute_error_map_summary(
    clean_path: Path,
    damaged_path: Path,
    restored_path: Path,
    mask_path: Path,
    content_bbox: Sequence[int | float] | None = None,
    boundary_width_pixels: int = 3,
    boundary_mode: str = "both",
    mask_threshold: int = 0,
) -> dict[str, Any]:
    """Compute error-map and regional summary statistics for one case."""
    clean_arr = load_rgb_array(clean_path)
    damaged_arr = load_rgb_array(damaged_path)
    restored_arr = load_rgb_array(restored_path)
    mask_bool = load_mask_bool(
        mask_path,
        threshold=mask_threshold,
    )

    if (
        clean_arr.shape != damaged_arr.shape
        or clean_arr.shape != restored_arr.shape
    ):
        raise ValueError(
            f"Image shape mismatch: clean={clean_arr.shape}, "
            f"damaged={damaged_arr.shape}, restored={restored_arr.shape}"
        )

    if mask_bool.shape != clean_arr.shape[:2]:
        raise ValueError(
            f"Mask shape mismatch: mask={mask_bool.shape}, "
            f"image={clean_arr.shape[:2]}"
        )

    height, width = mask_bool.shape

    damaged_error_map = compute_absolute_error_map(
        clean_arr,
        damaged_arr,
    )
    restored_error_map = compute_absolute_error_map(
        clean_arr,
        restored_arr,
    )
    signed_improvement_map = compute_signed_improvement_map(
        damaged_error_map=damaged_error_map,
        restored_error_map=restored_error_map,
    )

    full_region = np.ones(mask_bool.shape, dtype=bool)
    outside_mask_region = ~mask_bool
    boundary_region = build_boundary_ring(
        mask_bool=mask_bool,
        width_pixels=boundary_width_pixels,
        mode=boundary_mode,
    )

    clipped_content_bbox = clip_bbox(
        bbox=content_bbox,
        width=width,
        height=height,
    )

    content_region = np.zeros(mask_bool.shape, dtype=bool)

    if clipped_content_bbox is None:
        content_region[:] = True
    else:
        x_min, y_min, x_max, y_max = clipped_content_bbox
        content_region[y_min:y_max, x_min:x_max] = True

    summary: dict[str, Any] = {
        "image_height": int(height),
        "image_width": int(width),
        "full_pixel_count": int(full_region.sum()),
        "content_pixel_count": int(content_region.sum()),
        "masked_pixel_count": int(mask_bool.sum()),
        "outside_mask_pixel_count": int(outside_mask_region.sum()),
        "boundary_pixel_count": int(boundary_region.sum()),
        "damaged_error_mean_full": float(damaged_error_map.mean()),
        "damaged_error_std_full": float(damaged_error_map.std(ddof=0)),
        "damaged_error_max_full": float(damaged_error_map.max()),
        "restored_error_mean_full": float(restored_error_map.mean()),
        "restored_error_std_full": float(restored_error_map.std(ddof=0)),
        "restored_error_max_full": float(restored_error_map.max()),
        "improvement_mean_full": float(signed_improvement_map.mean()),
        "improvement_std_full": float(
            signed_improvement_map.std(ddof=0)
        ),
        "improvement_min_full": float(
            signed_improvement_map.min()
        ),
        "improvement_max_full": float(
            signed_improvement_map.max()
        ),
        "boundary_width_pixels": int(boundary_width_pixels),
        "boundary_mode": str(boundary_mode),
        "mask_threshold": int(mask_threshold),
    }

    for prefix, region in (
        ("improvement_masked", mask_bool),
        ("improvement_outside_mask", outside_mask_region),
        ("improvement_boundary", boundary_region),
        ("improvement_content", content_region),
    ):
        summary.update(
            compute_map_region_summary(
                map_arr=signed_improvement_map,
                region_bool=region,
                prefix=prefix,
            )
        )

    for prefix, error_map, region in (
        ("damaged_error_masked", damaged_error_map, mask_bool),
        ("restored_error_masked", restored_error_map, mask_bool),
        ("damaged_error_boundary", damaged_error_map, boundary_region),
        ("restored_error_boundary", restored_error_map, boundary_region),
        (
            "damaged_error_outside_mask",
            damaged_error_map,
            outside_mask_region,
        ),
        (
            "restored_error_outside_mask",
            restored_error_map,
            outside_mask_region,
        ),
    ):
        values = error_map[region]
        summary[f"{prefix}_mean"] = (
            float(values.mean())
            if values.size > 0
            else float("nan")
        )
        summary[f"{prefix}_std"] = (
            float(values.std(ddof=0))
            if values.size > 0
            else float("nan")
        )

    # Backward-compatible aliases used by the earlier notebook version.
    summary.update(
        {
            "masked_pixel_count": int(mask_bool.sum()),
            "damaged_error_mean_masked": summary[
                "damaged_error_masked_mean"
            ],
            "restored_error_mean_masked": summary[
                "restored_error_masked_mean"
            ],
            "improvement_mean_masked": summary[
                "improvement_masked_mean"
            ],
            "negative_improvement_pixels_masked": summary[
                "improvement_masked_negative_pixels"
            ],
            "positive_improvement_pixels_masked": summary[
                "improvement_masked_positive_pixels"
            ],
            "zero_improvement_pixels_masked": summary[
                "improvement_masked_zero_pixels"
            ],
            "negative_improvement_percentage_masked": summary[
                "improvement_masked_negative_percentage"
            ],
            "positive_improvement_percentage_masked": summary[
                "improvement_masked_positive_percentage"
            ],
        }
    )

    return summary


def _sample_values(
    values: np.ndarray,
    maximum_samples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Return deterministic samples from a one-dimensional numeric array."""
    values = np.asarray(values, dtype=np.float32)
    values = values[np.isfinite(values)]

    if values.size <= maximum_samples:
        return values

    selected_indices = rng.choice(
        values.size,
        size=int(maximum_samples),
        replace=False,
    )
    return values[selected_indices]


def compute_global_visualization_scales(
    cases_metadata: pd.DataFrame,
    clean_path_column: str = "clean_path",
    damaged_path_column: str = "damaged_path",
    restored_path_column: str = "restored_path",
    mask_path_column: str = "mask_path",
    absolute_percentile: float = 99.5,
    signed_percentile: float = 99.5,
    maximum_samples_per_case: int = 10_000,
    random_seed: int = 42,
    sample_region: str = "masked",
    mask_threshold: int = 0,
) -> pd.DataFrame:
    """Compute comparable absolute-error and signed-improvement scales.

    The function samples a deterministic subset of values from each case and
    returns a compact dataframe suitable for saving as a canonical scale file.
    """
    required_columns = {
        clean_path_column,
        damaged_path_column,
        restored_path_column,
        mask_path_column,
    }

    missing_columns = sorted(
        required_columns - set(cases_metadata.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Cases metadata missing required columns: {missing_columns}"
        )

    if not 0.0 < absolute_percentile <= 100.0:
        raise ValueError(
            "absolute_percentile must be within (0, 100]."
        )

    if not 0.0 < signed_percentile <= 100.0:
        raise ValueError(
            "signed_percentile must be within (0, 100]."
        )

    normalized_region = str(sample_region).strip().lower()

    if normalized_region not in {"masked", "full"}:
        raise ValueError(
            "sample_region must be either 'masked' or 'full'."
        )

    rng = np.random.default_rng(int(random_seed))

    absolute_samples: list[np.ndarray] = []
    signed_samples: list[np.ndarray] = []

    sampled_case_count = 0
    sampled_absolute_value_count = 0
    sampled_signed_value_count = 0

    for _, row in cases_metadata.iterrows():
        clean_arr = load_rgb_array(
            Path(row[clean_path_column])
        )
        damaged_arr = load_rgb_array(
            Path(row[damaged_path_column])
        )
        restored_arr = load_rgb_array(
            Path(row[restored_path_column])
        )
        mask_bool = load_mask_bool(
            Path(row[mask_path_column]),
            threshold=mask_threshold,
        )

        if (
            clean_arr.shape != damaged_arr.shape
            or clean_arr.shape != restored_arr.shape
        ):
            raise ValueError(
                "Image shape mismatch while computing visualization scales."
            )

        if mask_bool.shape != clean_arr.shape[:2]:
            raise ValueError(
                "Mask shape mismatch while computing visualization scales."
            )

        damaged_error_map = compute_absolute_error_map(
            clean_arr,
            damaged_arr,
        )
        restored_error_map = compute_absolute_error_map(
            clean_arr,
            restored_arr,
        )
        signed_improvement_map = compute_signed_improvement_map(
            damaged_error_map,
            restored_error_map,
        )

        if normalized_region == "masked" and mask_bool.any():
            absolute_values = np.concatenate(
                [
                    damaged_error_map[mask_bool],
                    restored_error_map[mask_bool],
                ]
            )
            signed_values = signed_improvement_map[mask_bool]
        else:
            absolute_values = np.concatenate(
                [
                    damaged_error_map.ravel(),
                    restored_error_map.ravel(),
                ]
            )
            signed_values = signed_improvement_map.ravel()

        sampled_absolute_values = _sample_values(
            absolute_values,
            maximum_samples=maximum_samples_per_case,
            rng=rng,
        )
        sampled_signed_values = _sample_values(
            signed_values,
            maximum_samples=maximum_samples_per_case,
            rng=rng,
        )

        absolute_samples.append(sampled_absolute_values)
        signed_samples.append(
            np.abs(sampled_signed_values)
        )

        sampled_case_count += 1
        sampled_absolute_value_count += int(
            sampled_absolute_values.size
        )
        sampled_signed_value_count += int(
            sampled_signed_values.size
        )

    if sampled_case_count == 0:
        raise ValueError(
            "Cannot compute visualization scales from an empty dataframe."
        )

    pooled_absolute = np.concatenate(absolute_samples)
    pooled_signed_absolute = np.concatenate(signed_samples)

    absolute_vmax = float(
        np.percentile(
            pooled_absolute,
            absolute_percentile,
        )
    )
    signed_limit = float(
        np.percentile(
            pooled_signed_absolute,
            signed_percentile,
        )
    )

    absolute_vmax = max(absolute_vmax, np.finfo(np.float32).eps)
    signed_limit = max(signed_limit, np.finfo(np.float32).eps)

    common_metadata = {
        "sample_region": normalized_region,
        "random_seed": int(random_seed),
        "maximum_samples_per_case": int(maximum_samples_per_case),
        "sampled_case_count": int(sampled_case_count),
        "mask_threshold": int(mask_threshold),
    }

    return pd.DataFrame(
        [
            {
                "scale_name": "absolute_error",
                "cmap": DEFAULT_ERROR_CMAP,
                "vmin": 0.0,
                "vmax": absolute_vmax,
                "percentile": float(absolute_percentile),
                "sampled_value_count": int(
                    sampled_absolute_value_count
                ),
                **common_metadata,
            },
            {
                "scale_name": "signed_improvement",
                "cmap": DEFAULT_SIGNED_CMAP,
                "vmin": -signed_limit,
                "vmax": signed_limit,
                "percentile": float(signed_percentile),
                "sampled_value_count": int(
                    sampled_signed_value_count
                ),
                **common_metadata,
            },
        ]
    )


def create_error_map_figure(
    case_row: pd.Series,
    output_path: Path,
    selection_group: str = "",
    error_vmin: float = 0.0,
    error_vmax: float = 255.0,
    improvement_vmin: float = -255.0,
    improvement_vmax: float = 255.0,
    content_bbox: Sequence[int | float] | None = None,
    mask_bbox: Sequence[int | float] | None = None,
    mask_bbox_margin: int = 0,
    boundary_width_pixels: int = 3,
    boundary_mode: str = "both",
    mask_threshold: int = 0,
    show: bool = False,
    dpi: int = 150,
) -> None:
    """Create and save a standardized nine-panel spatial diagnostic figure.

    Figure layout
    -------------
    Row 1:
        clean | damaged | restored

    Row 2:
        spatial overlay | damaged absolute error | restored absolute error

    Row 3:
        full signed improvement | masked signed improvement |
        boundary signed improvement
    """
    clean_path = Path(case_row["clean_path"])
    mask_path = Path(case_row["mask_path"])
    damaged_path = Path(case_row["damaged_path"])
    restored_path = Path(case_row["restored_path"])

    clean_arr = load_rgb_array(clean_path)
    damaged_arr = load_rgb_array(damaged_path)
    restored_arr = load_rgb_array(restored_path)
    mask_bool = load_mask_bool(
        mask_path,
        threshold=mask_threshold,
    )

    if (
        clean_arr.shape != damaged_arr.shape
        or clean_arr.shape != restored_arr.shape
    ):
        raise ValueError(
            f"Image shape mismatch: clean={clean_arr.shape}, "
            f"damaged={damaged_arr.shape}, restored={restored_arr.shape}"
        )

    if mask_bool.shape != clean_arr.shape[:2]:
        raise ValueError(
            f"Mask shape mismatch: mask={mask_bool.shape}, "
            f"image={clean_arr.shape[:2]}"
        )

    height, width = mask_bool.shape

    boundary_bool = build_boundary_ring(
        mask_bool=mask_bool,
        width_pixels=boundary_width_pixels,
        mode=boundary_mode,
    )

    if content_bbox is None:
        content_bbox = _coerce_optional_bbox_from_row(
            case_row=case_row,
            candidate_column_sets=(
                (
                    "content_x_min",
                    "content_y_min",
                    "content_x_max",
                    "content_y_max",
                ),
                (
                    "content_bbox_x_min",
                    "content_bbox_y_min",
                    "content_bbox_x_max",
                    "content_bbox_y_max",
                ),
            ),
            width=width,
            height=height,
        )
    else:
        content_bbox = clip_bbox(
            bbox=content_bbox,
            width=width,
            height=height,
        )

    if mask_bbox is None:
        mask_bbox = _coerce_optional_bbox_from_row(
            case_row=case_row,
            candidate_column_sets=(
                (
                    "mask_bbox_x_min",
                    "mask_bbox_y_min",
                    "mask_bbox_x_max",
                    "mask_bbox_y_max",
                ),
                (
                    "bbox_x_min",
                    "bbox_y_min",
                    "bbox_x_max",
                    "bbox_y_max",
                ),
            ),
            width=width,
            height=height,
        )

    if mask_bbox is None:
        mask_bbox = bbox_from_binary_mask(
            mask_bool=mask_bool,
            margin=mask_bbox_margin,
        )
    else:
        mask_bbox = clip_bbox(
            bbox=mask_bbox,
            width=width,
            height=height,
        )

    damaged_error_map = compute_absolute_error_map(
        clean_arr,
        damaged_arr,
    )
    restored_error_map = compute_absolute_error_map(
        clean_arr,
        restored_arr,
    )
    signed_improvement_map = compute_signed_improvement_map(
        damaged_error_map=damaged_error_map,
        restored_error_map=restored_error_map,
    )

    masked_signed_improvement_map = apply_mask_to_map(
        signed_improvement_map,
        mask_bool,
        outside_value=np.nan,
    )
    boundary_signed_improvement_map = apply_mask_to_map(
        signed_improvement_map,
        boundary_bool,
        outside_value=np.nan,
    )

    overlay_arr = create_spatial_overlay(
        image_arr=damaged_arr,
        mask_bool=mask_bool,
        boundary_bool=boundary_bool,
    )

    fig, axes = plt.subplots(
        3,
        3,
        figsize=(16, 16),
    )

    axes[0, 0].imshow(
        clean_arr.astype(np.uint8)
    )
    axes[0, 0].set_title("Clean reference")
    axes[0, 0].axis("off")

    axes[0, 1].imshow(
        damaged_arr.astype(np.uint8)
    )
    axes[0, 1].set_title("Damaged input")
    axes[0, 1].axis("off")

    axes[0, 2].imshow(
        restored_arr.astype(np.uint8)
    )
    restored_title = str(
        case_row.get(
            "model_name",
            "Restored",
        )
    ).replace("_", " ")
    axes[0, 2].set_title(
        f"{restored_title} restored"
    )
    axes[0, 2].axis("off")

    axes[1, 0].imshow(overlay_arr)
    axes[1, 0].set_title(
        "Spatial overlay"
    )
    axes[1, 0].axis("off")

    draw_bbox(
        axis=axes[1, 0],
        bbox=content_bbox,
        edgecolor=np.asarray(
            DEFAULT_CONTENT_BOX_RGB
        ) / 255.0,
        linestyle="--",
        linewidth=1.8,
        label="Content box",
    )
    draw_bbox(
        axis=axes[1, 0],
        bbox=mask_bbox,
        edgecolor=np.asarray(
            DEFAULT_MASK_BOX_RGB
        ) / 255.0,
        linestyle="-",
        linewidth=1.8,
        label="Mask box",
    )

    axes[1, 0].legend(
        handles=[
            Patch(
                facecolor=np.asarray(
                    DEFAULT_MASK_OVERLAY_RGB
                ) / 255.0,
                alpha=0.35,
                label="Mask overlay",
            ),
            Patch(
                facecolor=np.asarray(
                    DEFAULT_BOUNDARY_OVERLAY_RGB
                ) / 255.0,
                alpha=0.85,
                label="Boundary ring",
            ),
            Rectangle(
                (0, 0),
                1,
                1,
                fill=False,
                edgecolor=np.asarray(
                    DEFAULT_CONTENT_BOX_RGB
                ) / 255.0,
                linestyle="--",
                linewidth=1.8,
                label="Content box",
            ),
            Rectangle(
                (0, 0),
                1,
                1,
                fill=False,
                edgecolor=np.asarray(
                    DEFAULT_MASK_BOX_RGB
                ) / 255.0,
                linestyle="-",
                linewidth=1.8,
                label="Mask box",
            ),
        ],
        loc="lower right",
        fontsize=8,
        framealpha=0.8,
    )

    damaged_error_display = axes[1, 1].imshow(
        damaged_error_map,
        cmap=DEFAULT_ERROR_CMAP,
        vmin=error_vmin,
        vmax=error_vmax,
    )
    axes[1, 1].set_title(
        "Clean vs damaged\nabsolute error"
    )
    axes[1, 1].axis("off")
    fig.colorbar(
        damaged_error_display,
        ax=axes[1, 1],
        fraction=0.046,
        pad=0.04,
    )

    restored_error_display = axes[1, 2].imshow(
        restored_error_map,
        cmap=DEFAULT_ERROR_CMAP,
        vmin=error_vmin,
        vmax=error_vmax,
    )
    axes[1, 2].set_title(
        "Clean vs restored\nabsolute error"
    )
    axes[1, 2].axis("off")
    fig.colorbar(
        restored_error_display,
        ax=axes[1, 2],
        fraction=0.046,
        pad=0.04,
    )

    improvement_display = axes[2, 0].imshow(
        signed_improvement_map,
        cmap=DEFAULT_SIGNED_CMAP,
        vmin=improvement_vmin,
        vmax=improvement_vmax,
    )
    axes[2, 0].set_title(
        "Signed improvement\npositive = reduced error"
    )
    axes[2, 0].axis("off")
    fig.colorbar(
        improvement_display,
        ax=axes[2, 0],
        fraction=0.046,
        pad=0.04,
    )

    masked_improvement_display = axes[2, 1].imshow(
        masked_signed_improvement_map,
        cmap=DEFAULT_SIGNED_CMAP,
        vmin=improvement_vmin,
        vmax=improvement_vmax,
    )
    axes[2, 1].set_title(
        "Masked signed improvement"
    )
    axes[2, 1].axis("off")
    fig.colorbar(
        masked_improvement_display,
        ax=axes[2, 1],
        fraction=0.046,
        pad=0.04,
    )

    boundary_improvement_display = axes[2, 2].imshow(
        boundary_signed_improvement_map,
        cmap=DEFAULT_SIGNED_CMAP,
        vmin=improvement_vmin,
        vmax=improvement_vmax,
    )
    axes[2, 2].set_title(
        f"Boundary signed improvement\n"
        f"width={boundary_width_pixels}px, mode={boundary_mode}"
    )
    axes[2, 2].axis("off")
    fig.colorbar(
        boundary_improvement_display,
        ax=axes[2, 2],
        fraction=0.046,
        pad=0.04,
    )

    title_parts = [
        str(
            case_row.get(
                "restoration_case_id",
                case_row.get(
                    "case_id",
                    "",
                ),
            )
        ),
        str(
            case_row.get(
                "dataset_name",
                "",
            )
        ),
        str(
            case_row.get(
                "mask_type",
                "",
            )
        ),
        str(
            case_row.get(
                "model_name",
                "",
            )
        ),
    ]

    if selection_group:
        title_parts.append(
            f"selection={selection_group}"
        )

    fig.suptitle(
        " | ".join(
            [
                part
                for part in title_parts
                if part
            ]
        ),
        fontsize=13,
    )

    plt.tight_layout(
        rect=(0, 0, 1, 0.97)
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        output_path,
        dpi=dpi,
        bbox_inches="tight",
    )

    if show:
        plt.show()

    plt.close(fig)


def generate_error_map_figures_for_cases(
    cases_metadata: pd.DataFrame,
    output_dir: Path,
    selection_group_column: str = "selection_group",
    error_vmin: float = 0.0,
    error_vmax: float = 255.0,
    improvement_vmin: float = -255.0,
    improvement_vmax: float = 255.0,
    boundary_width_pixels: int = 3,
    boundary_mode: str = "both",
    mask_threshold: int = 0,
    show: bool = False,
    dpi: int = 150,
    progress_every: int | None = 25,
) -> pd.DataFrame:
    """Generate standardized diagnostic figures for selected cases.

    Returns a manifest dataframe containing figure paths, status fields and
    regional error-map statistics.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    required_columns = [
        "painting_id",
        "model_name",
        "clean_path",
        "mask_path",
        "damaged_path",
        "restored_path",
    ]

    if (
        "restoration_case_id" not in cases_metadata.columns
        and "case_id" not in cases_metadata.columns
    ):
        required_columns.append(
            "restoration_case_id"
        )

    missing_columns = [
        column
        for column in required_columns
        if column not in cases_metadata.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Cases metadata missing required columns: {missing_columns}"
        )

    total_cases = len(cases_metadata)

    print(
        f"Starting error-map generation for {total_cases} cases..."
    )
    print(
        f"Output directory: {output_dir}"
    )

    records: list[dict[str, Any]] = []

    for idx, (_, row) in enumerate(
        cases_metadata.iterrows(),
        start=1,
    ):
        case_id = str(
            row.get(
                "restoration_case_id",
                row.get(
                    "case_id",
                    "",
                ),
            )
        )
        model_name = str(
            row.get(
                "model_name",
                "",
            )
        )

        selection_group = (
            str(
                row.get(
                    selection_group_column,
                    "",
                )
            )
            if selection_group_column in row.index
            else ""
        )

        group_folder = (
            safe_filename(selection_group)
            if selection_group
            else "all_cases"
        )

        case_filename = (
            f"{safe_filename(case_id)}_"
            f"{safe_filename(model_name)}_"
            f"difference_maps.png"
        )
        figure_path = (
            output_dir
            / group_folder
            / case_filename
        )

        status = "ok"
        issue = ""
        summary: dict[str, Any] = {}

        try:
            content_bbox = _coerce_optional_bbox_from_row(
                case_row=row,
                candidate_column_sets=(
                    (
                        "content_x_min",
                        "content_y_min",
                        "content_x_max",
                        "content_y_max",
                    ),
                    (
                        "content_bbox_x_min",
                        "content_bbox_y_min",
                        "content_bbox_x_max",
                        "content_bbox_y_max",
                    ),
                ),
                width=int(
                    row.get(
                        "image_width",
                        10**9,
                    )
                ),
                height=int(
                    row.get(
                        "image_height",
                        10**9,
                    )
                ),
            )

            create_error_map_figure(
                case_row=row,
                output_path=figure_path,
                selection_group=selection_group,
                error_vmin=error_vmin,
                error_vmax=error_vmax,
                improvement_vmin=improvement_vmin,
                improvement_vmax=improvement_vmax,
                content_bbox=content_bbox,
                boundary_width_pixels=boundary_width_pixels,
                boundary_mode=boundary_mode,
                mask_threshold=mask_threshold,
                show=show,
                dpi=dpi,
            )

            summary = compute_error_map_summary(
                clean_path=Path(
                    row["clean_path"]
                ),
                damaged_path=Path(
                    row["damaged_path"]
                ),
                restored_path=Path(
                    row["restored_path"]
                ),
                mask_path=Path(
                    row["mask_path"]
                ),
                content_bbox=content_bbox,
                boundary_width_pixels=boundary_width_pixels,
                boundary_mode=boundary_mode,
                mask_threshold=mask_threshold,
            )

        except Exception as exc:
            status = "error"
            issue = (
                f"{type(exc).__name__}: {exc}"
            )

        records.append(
            {
                "restoration_case_id": case_id,
                "case_id": row.get(
                    "case_id",
                    case_id,
                ),
                "source_case_id": row.get(
                    "source_case_id",
                    "",
                ),
                "dataset_name": row.get(
                    "dataset_name",
                    "",
                ),
                "painting_id": row.get(
                    "painting_id",
                    "",
                ),
                "category": row.get(
                    "category",
                    "",
                ),
                "title": row.get(
                    "title",
                    "",
                ),
                "mask_id": row.get(
                    "mask_id",
                    "",
                ),
                "mask_type": row.get(
                    "mask_type",
                    "",
                ),
                "model_name": model_name,
                "selection_group": selection_group,
                "selection_metric": row.get(
                    "selection_metric",
                    "",
                ),
                "selection_value": row.get(
                    "selection_value",
                    np.nan,
                ),
                "figure_filename": case_filename,
                "figure_path": str(
                    figure_path
                ),
                **summary,
                "status": status,
                "issue": issue,
            }
        )

        if progress_every is not None:
            if (
                idx == 1
                or idx % progress_every == 0
                or idx == total_cases
            ):
                print(
                    f"Processed {idx}/{total_cases} cases..."
                )

    print(
        "Error-map generation finished."
    )

    return pd.DataFrame(records)


def validate_error_map_manifest(
    manifest_df: pd.DataFrame,
    expected_rows: int | None = None,
    require_unique_case_ids: bool = True,
    require_nonempty_figures: bool = True,
) -> pd.DataFrame:
    """Validate an error-map figure manifest dataframe."""
    validation_rows: list[dict[str, Any]] = []

    case_id_column = (
        "restoration_case_id"
        if "restoration_case_id" in manifest_df.columns
        else "case_id"
    )

    required_columns = [
        case_id_column,
        "figure_path",
        "status",
        "issue",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in manifest_df.columns
    ]

    validation_rows.append(
        {
            "check": "required_columns",
            "passed": len(
                missing_columns
            ) == 0,
            "detail": (
                "All required columns present."
                if not missing_columns
                else (
                    f"Missing columns: "
                    f"{missing_columns}"
                )
            ),
        }
    )

    if expected_rows is not None:
        validation_rows.append(
            {
                "check": "row_count",
                "passed": (
                    len(manifest_df)
                    == expected_rows
                ),
                "detail": (
                    f"Expected {expected_rows}, "
                    f"found {len(manifest_df)}."
                ),
            }
        )

    if (
        require_unique_case_ids
        and case_id_column in manifest_df.columns
    ):
        duplicate_count = int(
            manifest_df[
                case_id_column
            ].duplicated().sum()
        )
        validation_rows.append(
            {
                "check": "unique_case_ids",
                "passed": (
                    duplicate_count == 0
                ),
                "detail": (
                    f"Duplicate case IDs: "
                    f"{duplicate_count}."
                ),
            }
        )

    if "status" in manifest_df.columns:
        error_rows = int(
            (
                manifest_df["status"]
                != "ok"
            ).sum()
        )
        validation_rows.append(
            {
                "check": "status_ok",
                "passed": error_rows == 0,
                "detail": (
                    f"Rows with non-ok status: "
                    f"{error_rows}."
                ),
            }
        )

    if "figure_path" in manifest_df.columns:
        existing_figures = manifest_df[
            "figure_path"
        ].apply(
            lambda value: Path(
                value
            ).exists()
        )
        missing_figures = int(
            (~existing_figures).sum()
        )

        validation_rows.append(
            {
                "check": "figures_exist",
                "passed": (
                    missing_figures == 0
                ),
                "detail": (
                    f"Missing figure files: "
                    f"{missing_figures}."
                ),
            }
        )

        if require_nonempty_figures:
            nonempty_figures = manifest_df[
                "figure_path"
            ].apply(
                lambda value: (
                    Path(value).exists()
                    and Path(value).stat().st_size > 0
                )
            )
            empty_or_missing_count = int(
                (~nonempty_figures).sum()
            )

            validation_rows.append(
                {
                    "check": (
                        "figures_nonempty"
                    ),
                    "passed": (
                        empty_or_missing_count
                        == 0
                    ),
                    "detail": (
                        "Empty or missing figure "
                        f"files: "
                        f"{empty_or_missing_count}."
                    ),
                }
            )

    return pd.DataFrame(
        validation_rows
    )
