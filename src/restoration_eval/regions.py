"""Canonical spatial-region construction and metric-applicability policy."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from scipy.ndimage import binary_dilation, binary_erosion


REGIONS_MODULE_VERSION = "1.1.0"
REGION_SCHEMA_VERSION = "region.v1"
VALID_REGION_STATUSES = frozenset({"valid", "empty", "invalid"})
BOUNDARY_MODES = frozenset({"inner", "outer", "both"})
RECTANGULAR_ONLY_METRICS = frozenset(
    {"ssim", "lpips", "clip_similarity", "dinov2_similarity"}
)


@dataclass(frozen=True)
class Region:
    """One spatial region using exclusive maximum coordinates."""

    region_id: str
    region_type: str
    spatial_support: str
    x_min: int | None
    y_min: int | None
    x_max: int | None
    y_max: int | None
    pixel_count: int
    width: int
    height: int
    parameters: Mapping[str, Any] = field(default_factory=dict)
    validity_status: str = "valid"
    mask: np.ndarray = field(
        default_factory=lambda: np.zeros((0, 0), dtype=bool),
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if self.validity_status not in VALID_REGION_STATUSES:
            raise ValueError(f"Unsupported region validity status: {self.validity_status}")
        if self.mask.ndim != 2 or self.mask.dtype != bool:
            raise ValueError("Region mask must be a two-dimensional boolean array")
        if self.pixel_count != int(self.mask.sum()):
            raise ValueError("Region pixel_count does not match its mask")
        if self.validity_status == "valid" and self.pixel_count <= 0:
            raise ValueError("A valid region must contain at least one pixel")

    @property
    def bbox(self) -> tuple[int, int, int, int] | None:
        if None in (self.x_min, self.y_min, self.x_max, self.y_max):
            return None
        return (
            int(self.x_min),
            int(self.y_min),
            int(self.x_max),
            int(self.y_max),
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "region_schema_version": REGION_SCHEMA_VERSION,
            "region_id": self.region_id,
            "region_type": self.region_type,
            "spatial_support": self.spatial_support,
            "x_min": self.x_min,
            "y_min": self.y_min,
            "x_max": self.x_max,
            "y_max": self.y_max,
            "pixel_count": self.pixel_count,
            "width": self.width,
            "height": self.height,
            "parameters": json.dumps(
                dict(self.parameters),
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            ),
            "validity_status": self.validity_status,
        }


def normalize_mask(mask: np.ndarray, *, threshold: float = 0) -> np.ndarray:
    """Return a two-dimensional boolean mask using one explicit threshold."""
    array = np.asarray(mask)
    if array.ndim == 3 and array.shape[2] == 1:
        array = array[:, :, 0]
    if array.ndim != 2:
        raise ValueError(f"Expected a two-dimensional mask, received {array.shape}")
    if array.dtype == bool:
        return array.copy()
    if not np.issubdtype(array.dtype, np.number):
        raise TypeError(f"Mask must be numeric or boolean, received {array.dtype}")
    return array > threshold


def clip_bbox(
    bbox: Sequence[int | float] | None,
    *,
    width: int,
    height: int,
) -> tuple[int, int, int, int] | None:
    """Clip a four-value box to image bounds using exclusive maxima."""
    if bbox is None:
        return None
    if len(bbox) != 4:
        raise ValueError("Bounding box must contain four values")
    x_min, y_min, x_max, y_max = (int(round(float(value))) for value in bbox)
    x_min = max(0, min(x_min, int(width)))
    x_max = max(0, min(x_max, int(width)))
    y_min = max(0, min(y_min, int(height)))
    y_max = max(0, min(y_max, int(height)))
    if x_max <= x_min or y_max <= y_min:
        return None
    return x_min, y_min, x_max, y_max


def bbox_to_mask(
    shape: tuple[int, int],
    bbox: Sequence[int | float] | None,
) -> np.ndarray:
    height, width = shape
    result = np.zeros(shape, dtype=bool)
    clipped = clip_bbox(bbox, width=width, height=height)
    if clipped is not None:
        x_min, y_min, x_max, y_max = clipped
        result[y_min:y_max, x_min:x_max] = True
    return result


def mask_bbox(
    mask: np.ndarray,
    *,
    margin: int = 0,
) -> tuple[int, int, int, int] | None:
    mask_bool = normalize_mask(mask)
    if margin < 0:
        raise ValueError("margin must be non-negative")
    y_coords, x_coords = np.where(mask_bool)
    if x_coords.size == 0:
        return None
    height, width = mask_bool.shape
    return clip_bbox(
        (
            int(x_coords.min()) - margin,
            int(y_coords.min()) - margin,
            int(x_coords.max()) + 1 + margin,
            int(y_coords.max()) + 1 + margin,
        ),
        width=width,
        height=height,
    )


def disk_footprint(radius: int) -> np.ndarray:
    if radius < 1:
        raise ValueError("radius must be at least 1")
    y_grid, x_grid = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    return (x_grid * x_grid + y_grid * y_grid) <= radius * radius


def boundary_band(
    mask: np.ndarray,
    *,
    width_pixels: int = 3,
    mode: str = "both",
    support_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Build an inner, outer, or symmetric boundary band."""
    mask_bool = normalize_mask(mask)
    normalized_mode = str(mode).strip().lower()
    if normalized_mode not in BOUNDARY_MODES:
        raise ValueError(f"mode must be one of {sorted(BOUNDARY_MODES)}")
    footprint = disk_footprint(width_pixels)
    inner = mask_bool & ~binary_erosion(mask_bool, structure=footprint)
    outer = binary_dilation(mask_bool, structure=footprint) & ~mask_bool
    result = inner if normalized_mode == "inner" else outer
    if normalized_mode == "both":
        result = inner | outer
    if support_mask is not None:
        support = normalize_mask(support_mask)
        if support.shape != result.shape:
            raise ValueError("support_mask shape does not match mask")
        result &= support
    return result


def _region_from_mask(
    *,
    region_id: str,
    region_type: str,
    spatial_support: str,
    mask: np.ndarray,
    parameters: Mapping[str, Any] | None = None,
    rectangle_bbox: tuple[int, int, int, int] | None = None,
) -> Region:
    mask_bool = normalize_mask(mask)
    pixel_count = int(mask_bool.sum())
    bbox = rectangle_bbox if rectangle_bbox is not None else mask_bbox(mask_bool)
    if bbox is None:
        x_min = y_min = x_max = y_max = None
        width = height = 0
        status = "empty"
    else:
        x_min, y_min, x_max, y_max = bbox
        width = x_max - x_min
        height = y_max - y_min
        status = "valid" if pixel_count > 0 else "empty"
    return Region(
        region_id=str(region_id),
        region_type=str(region_type),
        spatial_support=str(spatial_support),
        x_min=x_min,
        y_min=y_min,
        x_max=x_max,
        y_max=y_max,
        pixel_count=pixel_count,
        width=width,
        height=height,
        parameters=dict(parameters or {}),
        validity_status=status,
        mask=mask_bool,
    )


def full_image_region(shape: tuple[int, int]) -> Region:
    height, width = (int(shape[0]), int(shape[1]))
    if height <= 0 or width <= 0:
        raise ValueError(f"Invalid image shape: {shape}")
    mask = np.ones((height, width), dtype=bool)
    return _region_from_mask(
        region_id="full_image",
        region_type="full_image",
        spatial_support="rectangle",
        mask=mask,
        rectangle_bbox=(0, 0, width, height),
    )


def content_region(
    shape: tuple[int, int],
    content_bbox: Sequence[int | float],
) -> Region:
    height, width = shape
    clipped = clip_bbox(content_bbox, width=width, height=height)
    mask = bbox_to_mask(shape, clipped)
    return _region_from_mask(
        region_id="content_region",
        region_type="content",
        spatial_support="rectangle",
        mask=mask,
        rectangle_bbox=clipped,
        parameters={"source_bbox": list(content_bbox)},
    )


def masked_region(mask: np.ndarray) -> Region:
    mask_bool = normalize_mask(mask)
    return _region_from_mask(
        region_id="masked_region",
        region_type="mask",
        spatial_support="irregular_pixels",
        mask=mask_bool,
    )


def mask_bbox_region(
    mask: np.ndarray,
    *,
    margin: int = 0,
    support_bbox: Sequence[int | float] | None = None,
) -> Region:
    mask_bool = normalize_mask(mask)
    bbox = mask_bbox(mask_bool, margin=margin)
    clipped_to_support = support_bbox is not None
    if bbox is not None and support_bbox is not None:
        height, width = mask_bool.shape
        support = clip_bbox(
            support_bbox,
            width=width,
            height=height,
        )
        if support is None:
            bbox = None
        else:
            bbox = clip_bbox(
                (
                    max(bbox[0], support[0]),
                    max(bbox[1], support[1]),
                    min(bbox[2], support[2]),
                    min(bbox[3], support[3]),
                ),
                width=width,
                height=height,
            )
    rectangle_mask = bbox_to_mask(mask_bool.shape, bbox)
    return _region_from_mask(
        region_id="mask_bbox_crop",
        region_type="mask_bbox",
        spatial_support="rectangle",
        mask=rectangle_mask,
        rectangle_bbox=bbox,
        parameters={
            "margin_pixels": int(margin),
            "clipped_to_support": clipped_to_support,
        },
    )


def boundary_region(
    mask: np.ndarray,
    *,
    width_pixels: int = 3,
    mode: str = "both",
    support_mask: np.ndarray | None = None,
) -> Region:
    normalized_mode = str(mode).strip().lower()
    band = boundary_band(
        mask,
        width_pixels=width_pixels,
        mode=normalized_mode,
        support_mask=support_mask,
    )
    region_id = {
        "inner": "inner_boundary_band",
        "outer": "outer_boundary_band",
        "both": "boundary_ring",
    }[normalized_mode]
    return _region_from_mask(
        region_id=region_id,
        region_type="boundary",
        spatial_support="irregular_pixels",
        mask=band,
        parameters={
            "width_pixels": int(width_pixels),
            "mode": normalized_mode,
            "clipped_to_support": support_mask is not None,
        },
    )


def outside_mask_content_region(
    mask: np.ndarray,
    content_bbox: Sequence[int | float],
) -> Region:
    mask_bool = normalize_mask(mask)
    content = content_region(mask_bool.shape, content_bbox)
    outside = content.mask & ~mask_bool
    return _region_from_mask(
        region_id="outside_mask_content",
        region_type="outside_mask",
        spatial_support="irregular_pixels",
        mask=outside,
        parameters={"restricted_to_content": True},
    )


def outside_boundary_region(
    mask: np.ndarray,
    *,
    width_pixels: int = 3,
    inner_offset_pixels: int = 0,
    outer_width_pixels: int | None = None,
    content_bbox: Sequence[int | float] | None = None,
) -> Region:
    """Build an outside-mask ring, optionally separated from the seam band.

    ``inner_offset_pixels=3`` and ``outer_width_pixels=8`` describe the
    spillover annulus from three to eight pixels outside the mask. The legacy
    ``width_pixels`` argument remains the outer width when an explicit outer
    width is not supplied.
    """
    mask_bool = normalize_mask(mask)
    if inner_offset_pixels < 0:
        raise ValueError("inner_offset_pixels must be non-negative")
    outer_width = (
        int(width_pixels)
        if outer_width_pixels is None
        else int(outer_width_pixels)
    )
    if outer_width < 1:
        raise ValueError("outer_width_pixels must be at least 1")
    if inner_offset_pixels >= outer_width:
        raise ValueError(
            "inner_offset_pixels must be smaller than outer_width_pixels"
        )
    support = (
        content_region(mask_bool.shape, content_bbox).mask
        if content_bbox is not None
        else None
    )
    outer_dilation = binary_dilation(
        mask_bool,
        structure=disk_footprint(outer_width),
    )
    inner_dilation = (
        mask_bool
        if inner_offset_pixels == 0
        else binary_dilation(
            mask_bool,
            structure=disk_footprint(inner_offset_pixels),
        )
    )
    ring = outer_dilation & ~inner_dilation
    if support is not None:
        ring &= support
    return _region_from_mask(
        region_id="outside_boundary_ring",
        region_type="outside_boundary",
        spatial_support="irregular_pixels",
        mask=ring,
        parameters={
            "inner_offset_pixels": int(inner_offset_pixels),
            "outer_width_pixels": outer_width,
            "clipped_to_support": support is not None,
        },
    )


def effect_support_region(
    effect_mask: np.ndarray,
    *,
    support_threshold: float = 1,
) -> Region:
    """Build the degradation-support region using an inclusive threshold."""
    values = np.asarray(effect_mask)
    if values.ndim == 3 and values.shape[2] == 1:
        values = values[:, :, 0]
    if values.ndim != 2:
        raise ValueError(
            f"Expected a two-dimensional effect mask, received {values.shape}"
        )
    if not np.issubdtype(values.dtype, np.number) and values.dtype != bool:
        raise TypeError(
            f"Effect mask must be numeric or boolean, received {values.dtype}"
        )
    support = values.astype(float) >= float(support_threshold)
    return _region_from_mask(
        region_id="degradation_support",
        region_type="degradation_effect",
        spatial_support="irregular_pixels",
        mask=support,
        parameters={
            "support_threshold": float(support_threshold),
            "threshold_operator": ">=",
        },
    )


def _window_starts(length: int, window: int, stride: int) -> list[int]:
    """Return row-major window starts while always covering the final edge."""
    if window > length:
        return []
    starts = list(range(0, length - window + 1, stride))
    final_start = length - window
    if not starts or starts[-1] != final_start:
        starts.append(final_start)
    return starts


def patch_regions(
    shape: tuple[int, int],
    *,
    patch_size: int | tuple[int, int],
    stride: int | tuple[int, int],
    support_mask: np.ndarray | None = None,
    minimum_support_fraction: float = 0.0,
) -> list[Region]:
    """Create deterministic row-major sliding-window rectangular regions."""
    height, width = shape
    patch_height, patch_width = (
        (patch_size, patch_size)
        if isinstance(patch_size, int)
        else patch_size
    )
    stride_y, stride_x = (stride, stride) if isinstance(stride, int) else stride
    values = (patch_height, patch_width, stride_y, stride_x)
    if any(int(value) <= 0 for value in values):
        raise ValueError("Patch dimensions and strides must be positive")
    if not 0.0 <= minimum_support_fraction <= 1.0:
        raise ValueError("minimum_support_fraction must be within [0, 1]")

    support = (
        np.ones(shape, dtype=bool)
        if support_mask is None
        else normalize_mask(support_mask)
    )
    if support.shape != shape:
        raise ValueError("support_mask shape does not match requested shape")

    regions: list[Region] = []
    for y_min in _window_starts(height, patch_height, stride_y):
        for x_min in _window_starts(width, patch_width, stride_x):
            x_max = x_min + patch_width
            y_max = y_min + patch_height
            window = np.zeros(shape, dtype=bool)
            window[y_min:y_max, x_min:x_max] = True
            support_fraction = float(
                support[y_min:y_max, x_min:x_max].mean()
            )
            if support_fraction < minimum_support_fraction:
                continue
            regions.append(
                _region_from_mask(
                    region_id=f"patch_y{y_min:04d}_x{x_min:04d}",
                    region_type="patch",
                    spatial_support="rectangle",
                    mask=window,
                    rectangle_bbox=(x_min, y_min, x_max, y_max),
                    parameters={
                        "patch_height": int(patch_height),
                        "patch_width": int(patch_width),
                        "stride_y": int(stride_y),
                        "stride_x": int(stride_x),
                        "support_fraction": support_fraction,
                    },
                )
            )
    return regions


def build_standard_regions(
    mask: np.ndarray,
    *,
    content_bbox: Sequence[int | float],
    mask_bbox_margin: int = 0,
    boundary_width_pixels: int = 3,
    include_outside_boundary: bool = False,
    outside_boundary_width_pixels: int = 8,
) -> dict[str, Region]:
    """Build the standard restoration-evaluation region set."""
    mask_bool = normalize_mask(mask)
    content = content_region(mask_bool.shape, content_bbox)
    regions = {
        "full_image": full_image_region(mask_bool.shape),
        "content_region": content,
        "masked_region": masked_region(mask_bool),
        "mask_bbox_crop": mask_bbox_region(
            mask_bool,
            margin=mask_bbox_margin,
            support_bbox=content_bbox,
        ),
        "inner_boundary_band": boundary_region(
            mask_bool,
            width_pixels=boundary_width_pixels,
            mode="inner",
            support_mask=content.mask,
        ),
        "outer_boundary_band": boundary_region(
            mask_bool,
            width_pixels=boundary_width_pixels,
            mode="outer",
            support_mask=content.mask,
        ),
        "boundary_ring": boundary_region(
            mask_bool,
            width_pixels=boundary_width_pixels,
            mode="both",
            support_mask=content.mask,
        ),
        "outside_mask_content": outside_mask_content_region(
            mask_bool,
            content_bbox,
        ),
    }
    if include_outside_boundary:
        regions["outside_boundary_ring"] = outside_boundary_region(
            mask_bool,
            width_pixels=boundary_width_pixels,
            inner_offset_pixels=boundary_width_pixels,
            outer_width_pixels=outside_boundary_width_pixels,
            content_bbox=content_bbox,
        )
    return regions


def metric_region_is_valid(metric_name: str, region: Region) -> tuple[bool, str]:
    """Return whether a metric/region pairing is methodologically valid."""
    metric = str(metric_name).strip().lower()
    if region.validity_status != "valid":
        return False, f"region status is {region.validity_status}"
    requires_rectangle = (
        metric in RECTANGULAR_ONLY_METRICS
        or any(token in metric for token in ("ssim", "lpips", "clip", "dinov2"))
    )
    if requires_rectangle and region.spatial_support != "rectangle":
        return False, f"{metric} requires a contiguous rectangular region"
    if metric == "ssim" and min(region.width, region.height) < 7:
        return False, "SSIM requires both rectangular dimensions to be at least 7"
    return True, "valid"


def require_valid_metric_region(metric_name: str, region: Region) -> None:
    valid, reason = metric_region_is_valid(metric_name, region)
    if not valid:
        raise ValueError(
            f"Invalid metric-region combination: metric={metric_name!r}, "
            f"region={region.region_id!r}: {reason}"
        )


def crop_array(array: np.ndarray, region: Region) -> np.ndarray:
    """Crop an array to a valid rectangular region."""
    if region.spatial_support != "rectangle" or region.bbox is None:
        raise ValueError(f"Region {region.region_id!r} is not rectangular")
    x_min, y_min, x_max, y_max = region.bbox
    return np.asarray(array)[y_min:y_max, x_min:x_max]


def select_pixels(array: np.ndarray, region: Region) -> np.ndarray:
    """Select arbitrary region pixels while retaining channel columns."""
    values = np.asarray(array)
    if values.shape[:2] != region.mask.shape:
        raise ValueError(
            f"Array/region shape mismatch: {values.shape[:2]} vs {region.mask.shape}"
        )
    return values[region.mask]
