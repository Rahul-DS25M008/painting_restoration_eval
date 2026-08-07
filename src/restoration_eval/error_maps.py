"""
Spatial error-map utilities for painting restoration evaluation.

The helpers in this module support Notebook 23's Stable Diffusion
difference-map stage. They compute candidate-level absolute-error maps,
signed-improvement maps, mask/boundary overlays, compact summary statistics,
and short-name PNG assets backed by manifest metadata.

Filename policy
---------------
Generated map filenames are deterministic short IDs such as
``dm_000001_der.png``. Case IDs, prompt text, painting titles, and candidate
IDs belong in CSV/JSON metadata, not in filenames.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.patches import Patch, Rectangle
from PIL import Image
from scipy.ndimage import binary_dilation, binary_erosion


ERROR_MAP_MODULE_NAME = "restoration_eval.error_maps"
ERROR_MAP_VERSION = "3.0.0"

DEFAULT_ERROR_CMAP = "magma"
DEFAULT_SIGNED_CMAP = "coolwarm"

DEFAULT_MASK_OVERLAY_RGB = (255, 255, 255)
DEFAULT_BOUNDARY_OVERLAY_RGB = (255, 215, 0)
DEFAULT_CONTENT_BOX_RGB = (0, 255, 255)
DEFAULT_MASK_BOX_RGB = (255, 0, 255)

DEFAULT_MAP_ASSET_TYPES = (
    "damaged_error",
    "restored_error",
    "signed_improvement",
    "masked_signed_improvement",
    "boundary_signed_improvement",
    "mask_overlay",
    "boundary_overlay",
)

MAP_ASSET_SPECS = {
    "damaged_error": {
        "subdir": "damaged_error",
        "suffix": "der",
        "path_column": "damaged_error_map_path",
        "filename_column": "damaged_error_map_filename",
    },
    "restored_error": {
        "subdir": "restored_error",
        "suffix": "rer",
        "path_column": "restored_error_map_path",
        "filename_column": "restored_error_map_filename",
    },
    "signed_improvement": {
        "subdir": "signed_improvement",
        "suffix": "sig",
        "path_column": "signed_improvement_map_path",
        "filename_column": "signed_improvement_map_filename",
    },
    "masked_signed_improvement": {
        "subdir": "masked_signed_improvement",
        "suffix": "msi",
        "path_column": "masked_signed_improvement_map_path",
        "filename_column": "masked_signed_improvement_map_filename",
    },
    "boundary_signed_improvement": {
        "subdir": "boundary_signed_improvement",
        "suffix": "bsi",
        "path_column": "boundary_signed_improvement_map_path",
        "filename_column": "boundary_signed_improvement_map_filename",
    },
    "mask_overlay": {
        "subdir": "mask_overlay",
        "suffix": "msk",
        "path_column": "mask_overlay_path",
        "filename_column": "mask_overlay_filename",
    },
    "boundary_overlay": {
        "subdir": "boundary_overlay",
        "suffix": "bnd",
        "path_column": "boundary_overlay_path",
        "filename_column": "boundary_overlay_filename",
    },
}

METADATA_COLUMNS_TO_COPY = (
    "map_id",
    "candidate_id",
    "restoration_case_id",
    "case_id",
    "source_case_key",
    "source_case_id",
    "painting_id",
    "category",
    "title",
    "mask_id",
    "mask_type",
    "prompt_policy_id",
    "prompt_variant_id",
    "prompt_template_name",
    "prompt_ablation_subset",
    "candidate_index",
    "candidate_seed",
    "effective_candidate_seed",
    "inference_mode",
    "execution_device",
    "clean_path",
    "damaged_path",
    "restored_path",
    "mask_path",
)


def resolve_path(path_value: str | Path, project_root: str | Path | None = None) -> Path:
    """Resolve an absolute or project-relative path."""
    path = Path(path_value)

    if path.is_absolute():
        return path

    if project_root is None:
        return path

    return Path(project_root) / path


def load_rgb_array(path: str | Path, project_root: str | Path | None = None) -> np.ndarray:
    """Load an RGB image as float32 in range [0, 255]."""
    resolved_path = resolve_path(path, project_root=project_root)

    if not resolved_path.exists():
        raise FileNotFoundError(f"Image file not found: {resolved_path}")

    with Image.open(resolved_path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.float32)


def load_mask_bool(
    path: str | Path,
    threshold: int = 0,
    project_root: str | Path | None = None,
) -> np.ndarray:
    """Load a mask as a boolean array where True means damaged/missing."""
    resolved_path = resolve_path(path, project_root=project_root)

    if not resolved_path.exists():
        raise FileNotFoundError(f"Mask file not found: {resolved_path}")

    with Image.open(resolved_path) as image:
        mask_arr = np.asarray(image.convert("L"))

    return mask_arr > int(threshold)


def load_image_for_display(
    path: str | Path,
    mode: str = "RGB",
    project_root: str | Path | None = None,
) -> Image.Image:
    """Load an image for display or panel generation."""
    resolved_path = resolve_path(path, project_root=project_root)

    if not resolved_path.exists():
        raise FileNotFoundError(f"Image file not found: {resolved_path}")

    with Image.open(resolved_path) as image:
        return image.convert(mode)


def _require_rgb_pair(reference_arr: np.ndarray, candidate_arr: np.ndarray) -> None:
    if reference_arr.shape != candidate_arr.shape:
        raise ValueError(
            f"Image shapes do not match: reference={reference_arr.shape}, "
            f"candidate={candidate_arr.shape}"
        )

    if reference_arr.ndim != 3 or reference_arr.shape[2] != 3:
        raise ValueError(
            "Expected RGB arrays with shape (height, width, 3), "
            f"received {reference_arr.shape}."
        )


def compute_absolute_error_map(
    clean_arr: np.ndarray,
    candidate_arr: np.ndarray,
) -> np.ndarray:
    """Compute per-pixel mean absolute RGB error in range [0, 255]."""
    _require_rgb_pair(clean_arr, candidate_arr)

    return np.mean(
        np.abs(clean_arr.astype(np.float32) - candidate_arr.astype(np.float32)),
        axis=2,
        dtype=np.float32,
    )


def compute_signed_improvement_map(
    damaged_error_map: np.ndarray,
    restored_error_map: np.ndarray,
) -> np.ndarray:
    """Compute signed restoration improvement.

    Positive values mean the restored image is closer to the clean reference
    than the damaged image. Negative values mean it is farther away.
    """
    if damaged_error_map.shape != restored_error_map.shape:
        raise ValueError(
            f"Error-map shapes do not match: damaged={damaged_error_map.shape}, "
            f"restored={restored_error_map.shape}"
        )

    return damaged_error_map.astype(np.float32) - restored_error_map.astype(np.float32)


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

    masked_map = np.full(map_arr.shape, outside_value, dtype=np.float32)
    masked_map[mask_bool] = map_arr[mask_bool]

    return masked_map


def clip_bbox(
    bbox: Sequence[int | float] | None,
    width: int,
    height: int,
) -> tuple[int, int, int, int] | None:
    """Clip an ``(x_min, y_min, x_max, y_max)`` box to image bounds."""
    if bbox is None:
        return None

    if len(bbox) != 4:
        raise ValueError(f"Bounding box must contain four values, received {bbox}.")

    x_min, y_min, x_max, y_max = [int(round(float(value))) for value in bbox]

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
        raise ValueError(f"Expected a two-dimensional mask, received {mask_bool.shape}.")

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

    return clip_bbox(bbox=bbox, width=width, height=height)


def disk_footprint(radius: int) -> np.ndarray:
    """Create a boolean disk footprint for binary morphology."""
    if radius < 1:
        raise ValueError("radius must be at least 1.")

    y_grid, x_grid = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    return (x_grid * x_grid + y_grid * y_grid) <= radius * radius


def build_boundary_ring(
    mask_bool: np.ndarray,
    width_pixels: int = 3,
    mode: str = "both",
) -> np.ndarray:
    """Build an inner, outer, or combined boundary ring around a binary mask."""
    if mask_bool.ndim != 2:
        raise ValueError(f"Expected a two-dimensional mask, received {mask_bool.shape}.")

    if width_pixels < 1:
        raise ValueError("width_pixels must be at least 1.")

    normalized_mode = str(mode).strip().lower()

    if normalized_mode not in {"inner", "outer", "both"}:
        raise ValueError("mode must be one of {'inner', 'outer', 'both'}.")

    footprint = disk_footprint(int(width_pixels))
    eroded = binary_erosion(mask_bool, structure=footprint)
    dilated = binary_dilation(mask_bool, structure=footprint)

    inner_ring = mask_bool & ~eroded
    outer_ring = dilated & ~mask_bool

    if normalized_mode == "inner":
        return inner_ring
    if normalized_mode == "outer":
        return outer_ring

    return inner_ring | outer_ring


def _normalize_rgb_triplet(rgb: Sequence[int | float]) -> np.ndarray:
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
    """Create an RGB overlay containing mask fill and optional boundary highlight."""
    if image_arr.ndim != 3 or image_arr.shape[2] != 3:
        raise ValueError(f"Expected RGB image array, received {image_arr.shape}.")

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
    overlay[mask_bool] = (1.0 - mask_alpha) * overlay[mask_bool] + mask_alpha * mask_colour

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
    for columns in candidate_column_sets:
        if not all(column in case_row for column in columns):
            continue

        values = [case_row.get(column) for column in columns]

        if any(pd.isna(value) for value in values):
            continue

        return clip_bbox(bbox=values, width=width, height=height)

    return None


def compute_case_maps(
    clean_path: str | Path,
    damaged_path: str | Path,
    restored_path: str | Path,
    mask_path: str | Path,
    boundary_width_pixels: int = 3,
    boundary_mode: str = "both",
    mask_threshold: int = 0,
    project_root: str | Path | None = None,
) -> dict[str, np.ndarray]:
    """Compute all reusable arrays for one restoration candidate."""
    clean_arr = load_rgb_array(clean_path, project_root=project_root)
    damaged_arr = load_rgb_array(damaged_path, project_root=project_root)
    restored_arr = load_rgb_array(restored_path, project_root=project_root)
    mask_bool = load_mask_bool(
        mask_path,
        threshold=mask_threshold,
        project_root=project_root,
    )

    _require_rgb_pair(clean_arr, damaged_arr)
    _require_rgb_pair(clean_arr, restored_arr)

    if mask_bool.shape != clean_arr.shape[:2]:
        raise ValueError(
            f"Mask shape mismatch: mask={mask_bool.shape}, image={clean_arr.shape[:2]}"
        )

    damaged_error_map = compute_absolute_error_map(clean_arr, damaged_arr)
    restored_error_map = compute_absolute_error_map(clean_arr, restored_arr)
    signed_improvement_map = compute_signed_improvement_map(
        damaged_error_map=damaged_error_map,
        restored_error_map=restored_error_map,
    )
    boundary_bool = build_boundary_ring(
        mask_bool=mask_bool,
        width_pixels=boundary_width_pixels,
        mode=boundary_mode,
    )

    return {
        "clean_arr": clean_arr,
        "damaged_arr": damaged_arr,
        "restored_arr": restored_arr,
        "mask_bool": mask_bool,
        "boundary_bool": boundary_bool,
        "damaged_error_map": damaged_error_map,
        "restored_error_map": restored_error_map,
        "signed_improvement_map": signed_improvement_map,
        "masked_signed_improvement_map": apply_mask_to_map(
            signed_improvement_map,
            mask_bool,
            outside_value=np.nan,
        ),
        "boundary_signed_improvement_map": apply_mask_to_map(
            signed_improvement_map,
            boundary_bool,
            outside_value=np.nan,
        ),
    }


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
    values = values[np.isfinite(values)]
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
        f"{prefix}_positive_percentage": positive_pixels / pixel_count * 100.0,
        f"{prefix}_negative_percentage": negative_pixels / pixel_count * 100.0,
        f"{prefix}_zero_percentage": zero_pixels / pixel_count * 100.0,
    }


def compute_error_map_summary(
    clean_path: str | Path,
    damaged_path: str | Path,
    restored_path: str | Path,
    mask_path: str | Path,
    content_bbox: Sequence[int | float] | None = None,
    boundary_width_pixels: int = 3,
    boundary_mode: str = "both",
    mask_threshold: int = 0,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    """Compute summary statistics for one candidate's difference maps."""
    maps = compute_case_maps(
        clean_path=clean_path,
        damaged_path=damaged_path,
        restored_path=restored_path,
        mask_path=mask_path,
        boundary_width_pixels=boundary_width_pixels,
        boundary_mode=boundary_mode,
        mask_threshold=mask_threshold,
        project_root=project_root,
    )

    clean_arr = maps["clean_arr"]
    mask_bool = maps["mask_bool"]
    boundary_bool = maps["boundary_bool"]
    damaged_error_map = maps["damaged_error_map"]
    restored_error_map = maps["restored_error_map"]
    signed_improvement_map = maps["signed_improvement_map"]

    height, width = mask_bool.shape
    full_region = np.ones(mask_bool.shape, dtype=bool)
    outside_mask_region = ~mask_bool
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
        "error_map_module": ERROR_MAP_MODULE_NAME,
        "error_map_version": ERROR_MAP_VERSION,
        "image_height": int(height),
        "image_width": int(width),
        "full_pixel_count": int(full_region.sum()),
        "content_pixel_count": int(content_region.sum()),
        "masked_pixel_count": int(mask_bool.sum()),
        "outside_mask_pixel_count": int(outside_mask_region.sum()),
        "boundary_pixel_count": int(boundary_bool.sum()),
        "damaged_error_mean_full": float(damaged_error_map.mean()),
        "damaged_error_std_full": float(damaged_error_map.std(ddof=0)),
        "damaged_error_max_full": float(damaged_error_map.max()),
        "restored_error_mean_full": float(restored_error_map.mean()),
        "restored_error_std_full": float(restored_error_map.std(ddof=0)),
        "restored_error_max_full": float(restored_error_map.max()),
        "improvement_mean_full": float(signed_improvement_map.mean()),
        "improvement_std_full": float(signed_improvement_map.std(ddof=0)),
        "improvement_min_full": float(signed_improvement_map.min()),
        "improvement_max_full": float(signed_improvement_map.max()),
        "boundary_width_pixels": int(boundary_width_pixels),
        "boundary_mode": str(boundary_mode),
        "mask_threshold": int(mask_threshold),
    }

    for prefix, region in (
        ("improvement_masked", mask_bool),
        ("improvement_outside_mask", outside_mask_region),
        ("improvement_boundary", boundary_bool),
        ("improvement_content", content_region),
    ):
        summary.update(compute_map_region_summary(signed_improvement_map, region, prefix))

    for prefix, error_map, region in (
        ("damaged_error_masked", damaged_error_map, mask_bool),
        ("restored_error_masked", restored_error_map, mask_bool),
        ("damaged_error_boundary", damaged_error_map, boundary_bool),
        ("restored_error_boundary", restored_error_map, boundary_bool),
        ("damaged_error_outside_mask", damaged_error_map, outside_mask_region),
        ("restored_error_outside_mask", restored_error_map, outside_mask_region),
    ):
        values = error_map[region]
        values = values[np.isfinite(values)]
        summary[f"{prefix}_mean"] = float(values.mean()) if values.size > 0 else float("nan")
        summary[f"{prefix}_std"] = float(values.std(ddof=0)) if values.size > 0 else float("nan")

    summary.update(
        {
            "damaged_error_mean_masked": summary["damaged_error_masked_mean"],
            "restored_error_mean_masked": summary["restored_error_masked_mean"],
            "improvement_mean_masked": summary["improvement_masked_mean"],
            "negative_improvement_pixels_masked": summary[
                "improvement_masked_negative_pixels"
            ],
            "positive_improvement_pixels_masked": summary[
                "improvement_masked_positive_pixels"
            ],
            "zero_improvement_pixels_masked": summary["improvement_masked_zero_pixels"],
            "negative_improvement_percentage_masked": summary[
                "improvement_masked_negative_percentage"
            ],
            "positive_improvement_percentage_masked": summary[
                "improvement_masked_positive_percentage"
            ],
        }
    )

    # Keep clean_arr referenced so linting does not hide the shape contract above.
    _ = clean_arr

    return summary


def _sample_values(
    values: np.ndarray,
    maximum_samples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    values = values[np.isfinite(values)]

    if values.size <= maximum_samples:
        return values

    selected_indices = rng.choice(values.size, size=int(maximum_samples), replace=False)
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
    project_root: str | Path | None = None,
) -> pd.DataFrame:
    """Compute comparable absolute-error and signed-improvement colour scales."""
    required_columns = {
        clean_path_column,
        damaged_path_column,
        restored_path_column,
        mask_path_column,
    }
    missing_columns = sorted(required_columns - set(cases_metadata.columns))

    if missing_columns:
        raise ValueError(f"Cases metadata missing required columns: {missing_columns}")

    if not 0.0 < absolute_percentile <= 100.0:
        raise ValueError("absolute_percentile must be within (0, 100].")

    if not 0.0 < signed_percentile <= 100.0:
        raise ValueError("signed_percentile must be within (0, 100].")

    normalized_region = str(sample_region).strip().lower()

    if normalized_region not in {"masked", "full"}:
        raise ValueError("sample_region must be either 'masked' or 'full'.")

    rng = np.random.default_rng(int(random_seed))
    absolute_samples: list[np.ndarray] = []
    signed_samples: list[np.ndarray] = []
    sampled_case_count = 0
    sampled_absolute_value_count = 0
    sampled_signed_value_count = 0

    for _, row in cases_metadata.iterrows():
        maps = compute_case_maps(
            clean_path=row[clean_path_column],
            damaged_path=row[damaged_path_column],
            restored_path=row[restored_path_column],
            mask_path=row[mask_path_column],
            mask_threshold=mask_threshold,
            project_root=project_root,
        )
        mask_bool = maps["mask_bool"]
        damaged_error_map = maps["damaged_error_map"]
        restored_error_map = maps["restored_error_map"]
        signed_improvement_map = maps["signed_improvement_map"]

        if normalized_region == "masked" and mask_bool.any():
            absolute_values = np.concatenate(
                [damaged_error_map[mask_bool], restored_error_map[mask_bool]]
            )
            signed_values = signed_improvement_map[mask_bool]
        else:
            absolute_values = np.concatenate(
                [damaged_error_map.ravel(), restored_error_map.ravel()]
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
        signed_samples.append(np.abs(sampled_signed_values))
        sampled_case_count += 1
        sampled_absolute_value_count += int(sampled_absolute_values.size)
        sampled_signed_value_count += int(sampled_signed_values.size)

    if sampled_case_count == 0:
        raise ValueError("Cannot compute visualization scales from an empty dataframe.")

    pooled_absolute = np.concatenate(absolute_samples)
    pooled_signed_absolute = np.concatenate(signed_samples)
    absolute_vmax = float(np.percentile(pooled_absolute, absolute_percentile))
    signed_limit = float(np.percentile(pooled_signed_absolute, signed_percentile))
    absolute_vmax = max(absolute_vmax, float(np.finfo(np.float32).eps))
    signed_limit = max(signed_limit, float(np.finfo(np.float32).eps))

    common_metadata = {
        "sample_region": normalized_region,
        "random_seed": int(random_seed),
        "maximum_samples_per_case": int(maximum_samples_per_case),
        "sampled_case_count": int(sampled_case_count),
        "mask_threshold": int(mask_threshold),
        "error_map_version": ERROR_MAP_VERSION,
    }

    return pd.DataFrame(
        [
            {
                "scale_name": "absolute_error",
                "cmap": DEFAULT_ERROR_CMAP,
                "vmin": 0.0,
                "vmax": absolute_vmax,
                "percentile": float(absolute_percentile),
                "sampled_value_count": int(sampled_absolute_value_count),
                **common_metadata,
            },
            {
                "scale_name": "signed_improvement",
                "cmap": DEFAULT_SIGNED_CMAP,
                "vmin": -signed_limit,
                "vmax": signed_limit,
                "percentile": float(signed_percentile),
                "sampled_value_count": int(sampled_signed_value_count),
                **common_metadata,
            },
        ]
    )


def scales_dataframe_to_limits(scales_df: pd.DataFrame) -> dict[str, float]:
    """Extract plotting limits from a two-row scale dataframe."""
    required_columns = {"scale_name", "vmin", "vmax"}
    missing_columns = sorted(required_columns - set(scales_df.columns))

    if missing_columns:
        raise ValueError(f"Scale dataframe missing required columns: {missing_columns}")

    scale_rows = {
        str(row["scale_name"]): row
        for _, row in scales_df.iterrows()
    }

    for scale_name in ("absolute_error", "signed_improvement"):
        if scale_name not in scale_rows:
            raise ValueError(f"Scale dataframe missing {scale_name!r} row.")

    return {
        "error_vmin": float(scale_rows["absolute_error"]["vmin"]),
        "error_vmax": float(scale_rows["absolute_error"]["vmax"]),
        "improvement_vmin": float(scale_rows["signed_improvement"]["vmin"]),
        "improvement_vmax": float(scale_rows["signed_improvement"]["vmax"]),
    }


def _numeric_map_to_rgba(
    map_arr: np.ndarray,
    cmap: str,
    vmin: float,
    vmax: float,
    center: float | None = None,
) -> np.ndarray:
    map_arr = np.asarray(map_arr, dtype=np.float32)
    finite_mask = np.isfinite(map_arr)

    if center is None:
        norm = Normalize(vmin=float(vmin), vmax=float(vmax), clip=True)
    else:
        norm = TwoSlopeNorm(vmin=float(vmin), vcenter=float(center), vmax=float(vmax))

    rgba = plt.get_cmap(cmap)(norm(np.where(finite_mask, map_arr, np.nan)))
    rgba_uint8 = np.clip(rgba * 255.0, 0, 255).astype(np.uint8)
    rgba_uint8[~finite_mask] = np.asarray([0, 0, 0, 0], dtype=np.uint8)

    return rgba_uint8


def save_numeric_map_png(
    map_arr: np.ndarray,
    output_path: str | Path,
    cmap: str,
    vmin: float,
    vmax: float,
    center: float | None = None,
) -> None:
    """Save a 2D numeric map as a standardized RGBA PNG."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rgba_uint8 = _numeric_map_to_rgba(map_arr, cmap=cmap, vmin=vmin, vmax=vmax, center=center)
    Image.fromarray(rgba_uint8, mode="RGBA").save(output_path)


def save_rgb_png(image_arr: np.ndarray, output_path: str | Path) -> None:
    """Save an RGB array as a PNG."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(image_arr, 0, 255).astype(np.uint8), mode="RGB").save(output_path)


def short_map_filename(map_id: str, asset_type: str) -> str:
    """Return a deterministic short filename for one map asset."""
    if asset_type not in MAP_ASSET_SPECS:
        raise ValueError(f"Unsupported map asset type: {asset_type!r}")

    suffix = MAP_ASSET_SPECS[asset_type]["suffix"]
    return f"{map_id}_{suffix}.png"


def make_map_id(index: int, prefix: str = "dm") -> str:
    """Return a deterministic short map ID such as ``dm_000001``."""
    if index < 1:
        raise ValueError("index must be at least 1.")

    return f"{prefix}_{int(index):06d}"


def _copy_metadata_from_row(row: pd.Series | Mapping[str, Any]) -> dict[str, Any]:
    return {
        column: row.get(column, "")
        for column in METADATA_COLUMNS_TO_COPY
        if column in row
    }


def _asset_output_path(output_root: Path, map_id: str, asset_type: str) -> Path:
    spec = MAP_ASSET_SPECS[asset_type]
    return output_root / spec["subdir"] / short_map_filename(map_id, asset_type)


def save_candidate_map_assets(
    case_row: pd.Series | Mapping[str, Any],
    output_root: str | Path,
    map_index: int,
    map_id_prefix: str = "dm",
    asset_types: Sequence[str] = DEFAULT_MAP_ASSET_TYPES,
    error_vmin: float = 0.0,
    error_vmax: float = 255.0,
    improvement_vmin: float = -255.0,
    improvement_vmax: float = 255.0,
    boundary_width_pixels: int = 3,
    boundary_mode: str = "both",
    mask_threshold: int = 0,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    """Save all requested short-name map assets for one candidate."""
    output_root = Path(output_root)
    map_id = make_map_id(map_index, prefix=map_id_prefix)

    unsupported_assets = sorted(set(asset_types) - set(MAP_ASSET_SPECS))

    if unsupported_assets:
        raise ValueError(f"Unsupported map asset types: {unsupported_assets}")

    maps = compute_case_maps(
        clean_path=case_row["clean_path"],
        damaged_path=case_row["damaged_path"],
        restored_path=case_row["restored_path"],
        mask_path=case_row["mask_path"],
        boundary_width_pixels=boundary_width_pixels,
        boundary_mode=boundary_mode,
        mask_threshold=mask_threshold,
        project_root=project_root,
    )

    image_arrays = {
        "damaged_error": maps["damaged_error_map"],
        "restored_error": maps["restored_error_map"],
        "signed_improvement": maps["signed_improvement_map"],
        "masked_signed_improvement": maps["masked_signed_improvement_map"],
        "boundary_signed_improvement": maps["boundary_signed_improvement_map"],
    }

    mask_overlay = create_spatial_overlay(
        image_arr=maps["damaged_arr"],
        mask_bool=maps["mask_bool"],
        boundary_bool=None,
    )
    boundary_overlay = create_spatial_overlay(
        image_arr=maps["damaged_arr"],
        mask_bool=maps["mask_bool"],
        boundary_bool=maps["boundary_bool"],
    )

    record = {
        "map_id": map_id,
        "map_index": int(map_index),
        "map_asset_count": int(len(asset_types)),
        "map_asset_types": " | ".join(asset_types),
        "status": "ok",
        "issue": "",
        "error_map_version": ERROR_MAP_VERSION,
        "boundary_width_pixels": int(boundary_width_pixels),
        "boundary_mode": str(boundary_mode),
        "mask_threshold": int(mask_threshold),
        "error_vmin": float(error_vmin),
        "error_vmax": float(error_vmax),
        "improvement_vmin": float(improvement_vmin),
        "improvement_vmax": float(improvement_vmax),
        **_copy_metadata_from_row(case_row),
    }

    for asset_type in asset_types:
        output_path = _asset_output_path(output_root, map_id, asset_type)
        spec = MAP_ASSET_SPECS[asset_type]

        if asset_type in {"damaged_error", "restored_error"}:
            save_numeric_map_png(
                image_arrays[asset_type],
                output_path,
                cmap=DEFAULT_ERROR_CMAP,
                vmin=error_vmin,
                vmax=error_vmax,
            )
        elif asset_type in {
            "signed_improvement",
            "masked_signed_improvement",
            "boundary_signed_improvement",
        }:
            save_numeric_map_png(
                image_arrays[asset_type],
                output_path,
                cmap=DEFAULT_SIGNED_CMAP,
                vmin=improvement_vmin,
                vmax=improvement_vmax,
                center=0.0,
            )
        elif asset_type == "mask_overlay":
            save_rgb_png(mask_overlay, output_path)
        elif asset_type == "boundary_overlay":
            save_rgb_png(boundary_overlay, output_path)

        record[spec["path_column"]] = str(output_path)
        record[spec["filename_column"]] = output_path.name
        record[f"{asset_type}_filename_length"] = len(output_path.name)
        record[f"{asset_type}_file_size_bytes"] = int(output_path.stat().st_size)

    summary = compute_error_map_summary(
        clean_path=case_row["clean_path"],
        damaged_path=case_row["damaged_path"],
        restored_path=case_row["restored_path"],
        mask_path=case_row["mask_path"],
        boundary_width_pixels=boundary_width_pixels,
        boundary_mode=boundary_mode,
        mask_threshold=mask_threshold,
        project_root=project_root,
    )
    record.update(summary)

    return record


def generate_candidate_map_assets_for_cases(
    cases_metadata: pd.DataFrame,
    output_root: str | Path,
    map_id_prefix: str = "dm",
    asset_types: Sequence[str] = DEFAULT_MAP_ASSET_TYPES,
    error_vmin: float = 0.0,
    error_vmax: float = 255.0,
    improvement_vmin: float = -255.0,
    improvement_vmax: float = 255.0,
    boundary_width_pixels: int = 3,
    boundary_mode: str = "both",
    mask_threshold: int = 0,
    project_root: str | Path | None = None,
    continue_on_error: bool = True,
    progress_every: int | None = 50,
) -> pd.DataFrame:
    """Generate all requested map PNG assets for candidate-level rows."""
    required_columns = {"clean_path", "damaged_path", "restored_path", "mask_path"}
    missing_columns = sorted(required_columns - set(cases_metadata.columns))

    if missing_columns:
        raise ValueError(f"Cases metadata missing required columns: {missing_columns}")

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    total_cases = len(cases_metadata)

    for map_index, (_, row) in enumerate(cases_metadata.iterrows(), start=1):
        map_id = make_map_id(map_index, prefix=map_id_prefix)

        try:
            record = save_candidate_map_assets(
                row,
                output_root=output_root,
                map_index=map_index,
                map_id_prefix=map_id_prefix,
                asset_types=asset_types,
                error_vmin=error_vmin,
                error_vmax=error_vmax,
                improvement_vmin=improvement_vmin,
                improvement_vmax=improvement_vmax,
                boundary_width_pixels=boundary_width_pixels,
                boundary_mode=boundary_mode,
                mask_threshold=mask_threshold,
                project_root=project_root,
            )
        except Exception as exc:
            if not continue_on_error:
                raise

            record = {
                "map_id": map_id,
                "map_index": int(map_index),
                "map_asset_count": int(len(asset_types)),
                "map_asset_types": " | ".join(asset_types),
                "status": "error",
                "issue": f"{type(exc).__name__}: {exc}",
                "error_map_version": ERROR_MAP_VERSION,
                "boundary_width_pixels": int(boundary_width_pixels),
                "boundary_mode": str(boundary_mode),
                "mask_threshold": int(mask_threshold),
                **_copy_metadata_from_row(row),
            }

        records.append(record)

        if progress_every is not None and (
            map_index == 1 or map_index % progress_every == 0 or map_index == total_cases
        ):
            print(f"Processed map assets for {map_index}/{total_cases} candidates...")

    return pd.DataFrame(records)


def create_error_map_figure(
    case_row: pd.Series | Mapping[str, Any],
    output_path: str | Path,
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
    project_root: str | Path | None = None,
    show: bool = False,
    dpi: int = 150,
) -> None:
    """Create and save a standardized nine-panel spatial diagnostic figure."""
    maps = compute_case_maps(
        clean_path=case_row["clean_path"],
        damaged_path=case_row["damaged_path"],
        restored_path=case_row["restored_path"],
        mask_path=case_row["mask_path"],
        boundary_width_pixels=boundary_width_pixels,
        boundary_mode=boundary_mode,
        mask_threshold=mask_threshold,
        project_root=project_root,
    )
    clean_arr = maps["clean_arr"]
    damaged_arr = maps["damaged_arr"]
    restored_arr = maps["restored_arr"]
    mask_bool = maps["mask_bool"]
    boundary_bool = maps["boundary_bool"]
    damaged_error_map = maps["damaged_error_map"]
    restored_error_map = maps["restored_error_map"]
    signed_improvement_map = maps["signed_improvement_map"]
    masked_signed_improvement_map = maps["masked_signed_improvement_map"]
    boundary_signed_improvement_map = maps["boundary_signed_improvement_map"]

    height, width = mask_bool.shape

    if content_bbox is None:
        content_bbox = _coerce_optional_bbox_from_row(
            case_row=case_row,
            candidate_column_sets=(
                ("content_x_min", "content_y_min", "content_x_max", "content_y_max"),
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
        content_bbox = clip_bbox(bbox=content_bbox, width=width, height=height)

    if mask_bbox is None:
        mask_bbox = _coerce_optional_bbox_from_row(
            case_row=case_row,
            candidate_column_sets=(
                ("mask_bbox_x_min", "mask_bbox_y_min", "mask_bbox_x_max", "mask_bbox_y_max"),
                ("bbox_x_min", "bbox_y_min", "bbox_x_max", "bbox_y_max"),
            ),
            width=width,
            height=height,
        )

    if mask_bbox is None:
        mask_bbox = bbox_from_binary_mask(mask_bool=mask_bool, margin=mask_bbox_margin)
    else:
        mask_bbox = clip_bbox(bbox=mask_bbox, width=width, height=height)

    overlay_arr = create_spatial_overlay(
        image_arr=damaged_arr,
        mask_bool=mask_bool,
        boundary_bool=boundary_bool,
    )

    fig, axes = plt.subplots(3, 3, figsize=(16, 16))
    axes[0, 0].imshow(clean_arr.astype(np.uint8))
    axes[0, 0].set_title("Clean reference")
    axes[0, 1].imshow(damaged_arr.astype(np.uint8))
    axes[0, 1].set_title("Damaged input")
    axes[0, 2].imshow(restored_arr.astype(np.uint8))
    axes[0, 2].set_title("Stable Diffusion restored")

    axes[1, 0].imshow(overlay_arr)
    axes[1, 0].set_title("Mask and boundary overlay")
    draw_bbox(
        axis=axes[1, 0],
        bbox=content_bbox,
        edgecolor=np.asarray(DEFAULT_CONTENT_BOX_RGB) / 255.0,
        linestyle="--",
        label="Content box",
    )
    draw_bbox(
        axis=axes[1, 0],
        bbox=mask_bbox,
        edgecolor=np.asarray(DEFAULT_MASK_BOX_RGB) / 255.0,
        linestyle="-",
        label="Mask box",
    )
    axes[1, 0].legend(
        handles=[
            Patch(
                facecolor=np.asarray(DEFAULT_MASK_OVERLAY_RGB) / 255.0,
                alpha=0.35,
                label="Mask overlay",
            ),
            Patch(
                facecolor=np.asarray(DEFAULT_BOUNDARY_OVERLAY_RGB) / 255.0,
                alpha=0.85,
                label="Boundary ring",
            ),
            Rectangle(
                (0, 0),
                1,
                1,
                fill=False,
                edgecolor=np.asarray(DEFAULT_CONTENT_BOX_RGB) / 255.0,
                linestyle="--",
                label="Content box",
            ),
            Rectangle(
                (0, 0),
                1,
                1,
                fill=False,
                edgecolor=np.asarray(DEFAULT_MASK_BOX_RGB) / 255.0,
                label="Mask box",
            ),
        ],
        loc="lower right",
        fontsize=8,
        framealpha=0.8,
    )

    panels = (
        (axes[1, 1], damaged_error_map, DEFAULT_ERROR_CMAP, error_vmin, error_vmax, None,
         "Clean vs damaged\nabsolute error"),
        (axes[1, 2], restored_error_map, DEFAULT_ERROR_CMAP, error_vmin, error_vmax, None,
         "Clean vs restored\nabsolute error"),
        (axes[2, 0], signed_improvement_map, DEFAULT_SIGNED_CMAP,
         improvement_vmin, improvement_vmax, 0.0,
         "Signed improvement\npositive = reduced error"),
        (axes[2, 1], masked_signed_improvement_map, DEFAULT_SIGNED_CMAP,
         improvement_vmin, improvement_vmax, 0.0,
         "Masked signed improvement"),
        (axes[2, 2], boundary_signed_improvement_map, DEFAULT_SIGNED_CMAP,
         improvement_vmin, improvement_vmax, 0.0,
         f"Boundary signed improvement\nwidth={boundary_width_pixels}px"),
    )

    for axis, image_arr, cmap, vmin, vmax, center, title in panels:
        norm = (
            TwoSlopeNorm(vmin=float(vmin), vcenter=float(center), vmax=float(vmax))
            if center is not None
            else Normalize(vmin=float(vmin), vmax=float(vmax), clip=True)
        )
        display = axis.imshow(image_arr, cmap=cmap, norm=norm)
        axis.set_title(title)
        fig.colorbar(display, ax=axis, fraction=0.046, pad=0.04)

    for axis in axes.ravel():
        axis.axis("off")

    title_parts = [
        str(case_row.get("candidate_id", "")),
        str(case_row.get("restoration_case_id", case_row.get("case_id", ""))),
        str(case_row.get("mask_type", "")),
    ]

    if selection_group:
        title_parts.append(f"selection={selection_group}")

    fig.suptitle(" | ".join([part for part in title_parts if part]), fontsize=13)
    plt.tight_layout(rect=(0, 0, 1, 0.97))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")

    if show:
        plt.show()

    plt.close(fig)


def generate_error_map_figures_for_cases(
    cases_metadata: pd.DataFrame,
    output_dir: str | Path,
    selection_group_column: str = "selection_group",
    error_vmin: float = 0.0,
    error_vmax: float = 255.0,
    improvement_vmin: float = -255.0,
    improvement_vmax: float = 255.0,
    boundary_width_pixels: int = 3,
    boundary_mode: str = "both",
    mask_threshold: int = 0,
    project_root: str | Path | None = None,
    show: bool = False,
    dpi: int = 150,
    progress_every: int | None = 25,
) -> pd.DataFrame:
    """Generate selected diagnostic panels with short deterministic filenames."""
    required_columns = {"clean_path", "mask_path", "damaged_path", "restored_path"}
    missing_columns = sorted(required_columns - set(cases_metadata.columns))

    if missing_columns:
        raise ValueError(f"Cases metadata missing required columns: {missing_columns}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    total_cases = len(cases_metadata)

    for idx, (_, row) in enumerate(cases_metadata.iterrows(), start=1):
        figure_id = f"dm_panel_{idx:03d}"
        figure_filename = f"{figure_id}.png"
        figure_path = output_dir / figure_filename
        selection_group = (
            str(row.get(selection_group_column, ""))
            if selection_group_column in row.index
            else ""
        )
        status = "ok"
        issue = ""
        summary: dict[str, Any] = {}

        try:
            create_error_map_figure(
                case_row=row,
                output_path=figure_path,
                selection_group=selection_group,
                error_vmin=error_vmin,
                error_vmax=error_vmax,
                improvement_vmin=improvement_vmin,
                improvement_vmax=improvement_vmax,
                boundary_width_pixels=boundary_width_pixels,
                boundary_mode=boundary_mode,
                mask_threshold=mask_threshold,
                project_root=project_root,
                show=show,
                dpi=dpi,
            )
            summary = compute_error_map_summary(
                clean_path=row["clean_path"],
                damaged_path=row["damaged_path"],
                restored_path=row["restored_path"],
                mask_path=row["mask_path"],
                boundary_width_pixels=boundary_width_pixels,
                boundary_mode=boundary_mode,
                mask_threshold=mask_threshold,
                project_root=project_root,
            )
        except Exception as exc:
            status = "error"
            issue = f"{type(exc).__name__}: {exc}"

        records.append(
            {
                "figure_id": figure_id,
                "figure_filename": figure_filename,
                "figure_path": str(figure_path),
                "figure_filename_length": len(figure_filename),
                "selection_group": selection_group,
                "status": status,
                "issue": issue,
                **_copy_metadata_from_row(row),
                **summary,
            }
        )

        if progress_every is not None and (
            idx == 1 or idx % progress_every == 0 or idx == total_cases
        ):
            print(f"Processed diagnostic panels for {idx}/{total_cases} cases...")

    return pd.DataFrame(records)


def _path_exists_and_nonempty(path_value: Any, project_root: str | Path | None = None) -> bool:
    if pd.isna(path_value) or str(path_value).strip() == "":
        return False

    path = resolve_path(str(path_value), project_root=project_root)
    return path.exists() and path.stat().st_size > 0


def validate_map_image_manifest(
    manifest_df: pd.DataFrame,
    expected_rows: int | None = None,
    expected_assets_per_row: int | None = None,
    asset_types: Sequence[str] = DEFAULT_MAP_ASSET_TYPES,
    max_filename_length: int = 40,
    require_unique_map_ids: bool = True,
    project_root: str | Path | None = None,
) -> pd.DataFrame:
    """Validate the all-candidate map image manifest."""
    validation_rows: list[dict[str, Any]] = []

    def add_row(
        check_name: str,
        observed_value: Any,
        expected_value: Any,
        passed: bool,
        failure_message: str,
    ) -> None:
        validation_rows.append(
            {
                "check_name": check_name,
                "observed_value": observed_value,
                "expected_value": expected_value,
                "passed": bool(passed),
                "failure_message": "" if passed else failure_message,
            }
        )

    path_columns = [
        MAP_ASSET_SPECS[asset_type]["path_column"]
        for asset_type in asset_types
        if asset_type in MAP_ASSET_SPECS
    ]
    filename_columns = [
        MAP_ASSET_SPECS[asset_type]["filename_column"]
        for asset_type in asset_types
        if asset_type in MAP_ASSET_SPECS
    ]
    required_columns = ["map_id", "map_index", "status", "issue", *path_columns]
    missing_columns = [column for column in required_columns if column not in manifest_df.columns]

    add_row(
        "required_columns_present",
        missing_columns,
        [],
        len(missing_columns) == 0,
        f"Manifest missing required columns: {missing_columns}",
    )

    if expected_rows is not None:
        add_row(
            "expected_row_count",
            len(manifest_df),
            int(expected_rows),
            len(manifest_df) == int(expected_rows),
            "Manifest row count does not match expected candidate count.",
        )

    if expected_assets_per_row is not None and "map_asset_count" in manifest_df.columns:
        asset_counts_ok = manifest_df["map_asset_count"].fillna(-1).astype(int).eq(
            int(expected_assets_per_row)
        )
        add_row(
            "expected_asset_count_per_row",
            sorted(manifest_df["map_asset_count"].dropna().astype(int).unique().tolist()),
            int(expected_assets_per_row),
            bool(asset_counts_ok.all()),
            "One or more rows have the wrong map_asset_count.",
        )

    if require_unique_map_ids and "map_id" in manifest_df.columns:
        duplicate_map_ids = int(manifest_df["map_id"].duplicated().sum())
        add_row(
            "unique_map_ids",
            duplicate_map_ids,
            0,
            duplicate_map_ids == 0,
            "Map IDs are not unique.",
        )

    if "status" in manifest_df.columns:
        non_ok_rows = int(manifest_df["status"].astype(str).ne("ok").sum())
        add_row(
            "status_ok",
            non_ok_rows,
            0,
            non_ok_rows == 0,
            "One or more manifest rows have non-ok status.",
        )

    if not missing_columns:
        for path_column in path_columns:
            existing_count = int(
                manifest_df[path_column].map(
                    lambda value: _path_exists_and_nonempty(value, project_root=project_root)
                ).sum()
            )
            add_row(
                f"{path_column}_files_exist",
                existing_count,
                len(manifest_df),
                existing_count == len(manifest_df),
                f"One or more files referenced by {path_column} are missing or empty.",
            )

    for filename_column in filename_columns:
        if filename_column not in manifest_df.columns:
            continue

        max_length = int(manifest_df[filename_column].astype(str).str.len().max())
        add_row(
            f"{filename_column}_short",
            max_length,
            f"<= {max_filename_length}",
            max_length <= int(max_filename_length),
            f"One or more filenames in {filename_column} exceed the length policy.",
        )

    return pd.DataFrame(validation_rows)


def validate_error_map_manifest(
    manifest_df: pd.DataFrame,
    expected_rows: int | None = None,
    require_unique_case_ids: bool = False,
    require_nonempty_figures: bool = True,
    project_root: str | Path | None = None,
) -> pd.DataFrame:
    """Validate a selected diagnostic-panel manifest dataframe."""
    validation_rows: list[dict[str, Any]] = []
    required_columns = ["figure_path", "status", "issue"]
    missing_columns = [column for column in required_columns if column not in manifest_df.columns]

    validation_rows.append(
        {
            "check_name": "required_columns_present",
            "observed_value": missing_columns,
            "expected_value": [],
            "passed": len(missing_columns) == 0,
            "failure_message": ""
            if not missing_columns
            else f"Missing columns: {missing_columns}",
        }
    )

    if expected_rows is not None:
        validation_rows.append(
            {
                "check_name": "row_count",
                "observed_value": len(manifest_df),
                "expected_value": int(expected_rows),
                "passed": len(manifest_df) == int(expected_rows),
                "failure_message": "Panel manifest row count mismatch.",
            }
        )

    if require_unique_case_ids:
        case_id_column = (
            "candidate_id"
            if "candidate_id" in manifest_df.columns
            else "restoration_case_id"
            if "restoration_case_id" in manifest_df.columns
            else "case_id"
        )

        if case_id_column in manifest_df.columns:
            duplicate_count = int(manifest_df[case_id_column].duplicated().sum())
            validation_rows.append(
                {
                    "check_name": f"unique_{case_id_column}",
                    "observed_value": duplicate_count,
                    "expected_value": 0,
                    "passed": duplicate_count == 0,
                    "failure_message": f"Duplicate {case_id_column} values found.",
                }
            )

    if "status" in manifest_df.columns:
        error_rows = int(manifest_df["status"].astype(str).ne("ok").sum())
        validation_rows.append(
            {
                "check_name": "status_ok",
                "observed_value": error_rows,
                "expected_value": 0,
                "passed": error_rows == 0,
                "failure_message": "Rows with non-ok status found.",
            }
        )

    if "figure_path" in manifest_df.columns:
        existing_figures = manifest_df["figure_path"].map(
            lambda value: _path_exists_and_nonempty(value, project_root=project_root)
        )
        missing_figures = int((~existing_figures).sum())
        validation_rows.append(
            {
                "check_name": "figures_exist",
                "observed_value": len(manifest_df) - missing_figures,
                "expected_value": len(manifest_df),
                "passed": missing_figures == 0,
                "failure_message": f"Missing figure files: {missing_figures}.",
            }
        )

        if require_nonempty_figures:
            validation_rows.append(
                {
                    "check_name": "figures_nonempty",
                    "observed_value": int(existing_figures.sum()),
                    "expected_value": len(manifest_df),
                    "passed": bool(existing_figures.all()),
                    "failure_message": "One or more panel figures are empty or missing.",
                }
            )

    return pd.DataFrame(validation_rows)


__all__ = [
    "ERROR_MAP_MODULE_NAME",
    "ERROR_MAP_VERSION",
    "DEFAULT_MAP_ASSET_TYPES",
    "MAP_ASSET_SPECS",
    "apply_mask_to_map",
    "bbox_from_binary_mask",
    "build_boundary_ring",
    "clip_bbox",
    "compute_absolute_error_map",
    "compute_case_maps",
    "compute_error_map_summary",
    "compute_global_visualization_scales",
    "compute_map_region_summary",
    "compute_signed_improvement_map",
    "create_error_map_figure",
    "create_spatial_overlay",
    "disk_footprint",
    "generate_candidate_map_assets_for_cases",
    "generate_error_map_figures_for_cases",
    "load_image_for_display",
    "load_mask_bool",
    "load_rgb_array",
    "make_map_id",
    "save_candidate_map_assets",
    "save_numeric_map_png",
    "scales_dataframe_to_limits",
    "short_map_filename",
    "validate_error_map_manifest",
    "validate_map_image_manifest",
]
