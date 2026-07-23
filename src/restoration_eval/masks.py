"""Canonical synthetic binary damage-mask generation utilities."""

from __future__ import annotations

from collections import deque
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFilter


GENERATOR_NAME = "canonical_synthetic_damage_masks"
GENERATOR_VERSION = "2.0.0"

SUPPORTED_MASK_TYPES = (
    "zero_control",
    "scratch_thin",
    "loss_small",
    "loss_large",
    "mixed_damage",
)

DEFAULT_MASK_SPECS: dict[str, dict[str, float]] = {
    "zero_control": {
        "target_area_pct": 0.0,
        "min_area_pct": 0.0,
        "max_area_pct": 0.0,
    },
    "scratch_thin": {
        "target_area_pct": 2.0,
        "min_area_pct": 1.0,
        "max_area_pct": 3.0,
    },
    "loss_small": {
        "target_area_pct": 4.5,
        "min_area_pct": 3.0,
        "max_area_pct": 6.0,
    },
    "loss_large": {
        "target_area_pct": 12.5,
        "min_area_pct": 10.0,
        "max_area_pct": 15.0,
    },
    "mixed_damage": {
        "target_area_pct": 11.5,
        "min_area_pct": 8.0,
        "max_area_pct": 15.0,
    },
}


def _stable_seed(*parts: object, modulus: int = 2**32 - 1) -> int:
    """Derive a deterministic unsigned seed from arbitrary values."""
    payload = "||".join(str(part) for part in parts).encode("utf-8")
    digest = sha256(payload).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False) % modulus


def _validate_content_box(
    target_size: int,
    content_box: tuple[int, int, int, int],
) -> None:
    """Validate a content box against the square target canvas."""
    x_min, y_min, x_max, y_max = content_box

    if target_size <= 0:
        raise ValueError("target_size must be positive.")

    if not (
        0 <= x_min < x_max <= target_size
        and 0 <= y_min < y_max <= target_size
    ):
        raise ValueError(
            "Invalid content box "
            f"{content_box} for target size {target_size}."
        )


def _content_box_from_row(row: pd.Series) -> tuple[int, int, int, int]:
    """Return the valid painting-content box from one metadata row."""
    content_box = (
        int(row["content_x_min"]),
        int(row["content_y_min"]),
        int(row["content_x_max"]),
        int(row["content_y_max"]),
    )

    target_size = int(
        row.get(
            "target_size",
            max(content_box[2], content_box[3]),
        )
    )

    _validate_content_box(target_size, content_box)
    return content_box


def _content_region_mask(
    target_size: int,
    content_box: tuple[int, int, int, int],
) -> np.ndarray:
    """Return a boolean array for the valid painting-content region."""
    _validate_content_box(target_size, content_box)

    x_min, y_min, x_max, y_max = content_box
    region = np.zeros((target_size, target_size), dtype=bool)
    region[y_min:y_max, x_min:x_max] = True
    return region


def _binary_array(mask: Image.Image) -> np.ndarray:
    """Return a boolean array for non-zero mask pixels."""
    return np.asarray(mask.convert("L")) > 0


def _binary_mask(mask: Image.Image) -> Image.Image:
    """Return a strictly binary grayscale mask using values 0 and 255."""
    binary = np.where(_binary_array(mask), 255, 0).astype(np.uint8)
    return Image.fromarray(binary, mode="L")


def _clip_mask_to_content_region(
    mask: Image.Image,
    target_size: int,
    content_box: tuple[int, int, int, int],
) -> Image.Image:
    """Remove every damaged pixel outside the painting-content region."""
    mask_arr = _binary_array(mask)
    content_arr = _content_region_mask(target_size, content_box)

    clipped = np.where(mask_arr & content_arr, 255, 0).astype(np.uint8)
    return Image.fromarray(clipped, mode="L")


def _mask_area_percentage_content(
    mask: Image.Image,
    target_size: int,
    content_box: tuple[int, int, int, int],
) -> float:
    """Return damaged area as a percentage of painting-content pixels."""
    mask_arr = _binary_array(mask)
    content_arr = _content_region_mask(target_size, content_box)

    content_pixels = int(content_arr.sum())
    if content_pixels == 0:
        raise ValueError("Content region contains zero pixels.")

    damaged_content_pixels = int((mask_arr & content_arr).sum())
    return damaged_content_pixels / content_pixels * 100.0


def _random_point_in_content(
    rng: np.random.Generator,
    content_box: tuple[int, int, int, int],
    margin: int = 0,
) -> tuple[int, int]:
    """Sample one point inside the content region."""
    x_min, y_min, x_max, y_max = content_box

    content_width = x_max - x_min
    content_height = y_max - y_min
    safe_margin = max(
        0,
        min(
            int(margin),
            max(0, (content_width - 1) // 2),
            max(0, (content_height - 1) // 2),
        ),
    )

    left = x_min + safe_margin
    right = x_max - safe_margin
    top = y_min + safe_margin
    bottom = y_max - safe_margin

    if left >= right:
        left, right = x_min, x_max

    if top >= bottom:
        top, bottom = y_min, y_max

    x = int(rng.integers(left, right))
    y = int(rng.integers(top, bottom))
    return x, y


def _draw_irregular_blob(
    draw: ImageDraw.ImageDraw,
    rng: np.random.Generator,
    center: tuple[int, int],
    radius_range: tuple[int, int],
    num_points: int,
) -> None:
    """Draw one irregular filled polygon."""
    radius_min, radius_max = radius_range

    if radius_min <= 0 or radius_max < radius_min:
        raise ValueError(
            f"Invalid radius range: {radius_range}"
        )

    if num_points < 3:
        raise ValueError("An irregular blob requires at least three points.")

    cx, cy = center
    angles = np.sort(
        rng.uniform(0.0, 2.0 * np.pi, size=num_points)
    )

    points: list[tuple[int, int]] = []

    for angle in angles:
        radius = float(rng.uniform(radius_min, radius_max))
        jitter_scale = max(1.0, radius * 0.12)

        x = int(
            round(
                cx
                + radius * np.cos(angle)
                + rng.normal(0.0, jitter_scale)
            )
        )
        y = int(
            round(
                cy
                + radius * np.sin(angle)
                + rng.normal(0.0, jitter_scale)
            )
        )

        points.append((x, y))

    draw.polygon(points, fill=255)


def _generate_blob_mask(
    rng: np.random.Generator,
    target_size: int,
    content_box: tuple[int, int, int, int],
    num_blobs: int,
    radius_range: tuple[int, int],
    num_points_range: tuple[int, int],
    blur_radius: float,
) -> Image.Image:
    """Generate an irregular blob-style missing-region mask."""
    mask = Image.new(
        "L",
        (target_size, target_size),
        0,
    )
    draw = ImageDraw.Draw(mask)

    for _ in range(num_blobs):
        center = _random_point_in_content(
            rng=rng,
            content_box=content_box,
            margin=radius_range[1],
        )

        num_points = int(
            rng.integers(
                num_points_range[0],
                num_points_range[1] + 1,
            )
        )

        _draw_irregular_blob(
            draw=draw,
            rng=rng,
            center=center,
            radius_range=radius_range,
            num_points=num_points,
        )

    if blur_radius > 0:
        mask = mask.filter(
            ImageFilter.GaussianBlur(radius=blur_radius)
        )
        mask = mask.point(
            lambda pixel: 255 if pixel > 80 else 0
        )

    mask = _binary_mask(mask)

    return _clip_mask_to_content_region(
        mask=mask,
        target_size=target_size,
        content_box=content_box,
    )


def _generate_scratch_mask(
    rng: np.random.Generator,
    target_size: int,
    content_box: tuple[int, int, int, int],
    num_lines_range: tuple[int, int] = (8, 16),
    width_range: tuple[int, int] = (2, 5),
    segment_count_range: tuple[int, int] = (3, 6),
    step_length_range: tuple[int, int] = (40, 120),
) -> Image.Image:
    """Generate elongated scratch- or crack-like line damage."""
    mask = Image.new(
        "L",
        (target_size, target_size),
        0,
    )
    draw = ImageDraw.Draw(mask)

    num_lines = int(
        rng.integers(
            num_lines_range[0],
            num_lines_range[1] + 1,
        )
    )

    x_min, y_min, x_max, y_max = content_box

    for _ in range(num_lines):
        x, y = _random_point_in_content(
            rng=rng,
            content_box=content_box,
        )

        points = [(x, y)]
        angle = float(rng.uniform(0.0, 2.0 * np.pi))

        segment_count = int(
            rng.integers(
                segment_count_range[0],
                segment_count_range[1] + 1,
            )
        )

        for _segment in range(segment_count):
            angle += float(rng.normal(0.0, 0.45))

            step = int(
                rng.integers(
                    step_length_range[0],
                    step_length_range[1] + 1,
                )
            )

            x = int(
                np.clip(
                    x + step * np.cos(angle),
                    x_min,
                    x_max - 1,
                )
            )
            y = int(
                np.clip(
                    y + step * np.sin(angle),
                    y_min,
                    y_max - 1,
                )
            )

            points.append((x, y))

        width = int(
            rng.integers(
                width_range[0],
                width_range[1] + 1,
            )
        )

        draw.line(
            points,
            fill=255,
            width=width,
            joint="curve",
        )

    mask = mask.filter(
        ImageFilter.GaussianBlur(radius=0.4)
    )
    mask = mask.point(
        lambda pixel: 255 if pixel > 35 else 0
    )
    mask = _binary_mask(mask)

    return _clip_mask_to_content_region(
        mask=mask,
        target_size=target_size,
        content_box=content_box,
    )


def _generate_edge_loss_mask(
    rng: np.random.Generator,
    target_size: int,
    content_box: tuple[int, int, int, int],
    radius_range: tuple[int, int] = (35, 90),
) -> Image.Image:
    """Generate one irregular loss touching a content-region border."""
    x_min, y_min, x_max, y_max = content_box
    radius_max = radius_range[1]

    side = str(
        rng.choice(
            ["left", "right", "top", "bottom"]
        )
    )

    if side == "left":
        center = (
            x_min + int(rng.integers(0, radius_max + 1)),
            int(rng.integers(y_min, y_max)),
        )
    elif side == "right":
        center = (
            x_max - 1 - int(rng.integers(0, radius_max + 1)),
            int(rng.integers(y_min, y_max)),
        )
    elif side == "top":
        center = (
            int(rng.integers(x_min, x_max)),
            y_min + int(rng.integers(0, radius_max + 1)),
        )
    else:
        center = (
            int(rng.integers(x_min, x_max)),
            y_max - 1 - int(rng.integers(0, radius_max + 1)),
        )

    mask = Image.new(
        "L",
        (target_size, target_size),
        0,
    )
    draw = ImageDraw.Draw(mask)

    _draw_irregular_blob(
        draw=draw,
        rng=rng,
        center=center,
        radius_range=radius_range,
        num_points=int(rng.integers(10, 18)),
    )

    mask = mask.filter(
        ImageFilter.GaussianBlur(radius=2.0)
    )
    mask = mask.point(
        lambda pixel: 255 if pixel > 80 else 0
    )
    mask = _binary_mask(mask)

    return _clip_mask_to_content_region(
        mask=mask,
        target_size=target_size,
        content_box=content_box,
    )


def _combine_masks(*masks: Image.Image) -> Image.Image:
    """Combine one or more masks using a logical OR."""
    if not masks:
        raise ValueError("At least one mask is required.")

    arrays = [
        _binary_array(mask)
        for mask in masks
    ]

    combined = np.logical_or.reduce(arrays)

    return Image.fromarray(
        np.where(combined, 255, 0).astype(np.uint8),
        mode="L",
    )


def generate_mask_by_type(
    mask_type: str,
    rng: np.random.Generator,
    target_size: int,
    content_box: tuple[int, int, int, int],
) -> Image.Image:
    """Generate one canonical binary mask for a mask family."""
    if mask_type not in SUPPORTED_MASK_TYPES:
        raise ValueError(
            f"Unsupported mask type: {mask_type}. "
            f"Supported types: {SUPPORTED_MASK_TYPES}"
        )

    _validate_content_box(target_size, content_box)

    if mask_type == "zero_control":
        return Image.new(
            "L",
            (target_size, target_size),
            0,
        )

    if mask_type == "scratch_thin":
        return _generate_scratch_mask(
            rng=rng,
            target_size=target_size,
            content_box=content_box,
        )

    if mask_type == "loss_small":
        return _generate_blob_mask(
            rng=rng,
            target_size=target_size,
            content_box=content_box,
            num_blobs=int(rng.integers(4, 9)),
            radius_range=(18, 45),
            num_points_range=(9, 16),
            blur_radius=1.5,
        )

    if mask_type == "loss_large":
        return _generate_blob_mask(
            rng=rng,
            target_size=target_size,
            content_box=content_box,
            num_blobs=int(rng.integers(1, 3)),
            radius_range=(85, 155),
            num_points_range=(14, 24),
            blur_radius=2.5,
        )

    scratch = _generate_scratch_mask(
        rng=rng,
        target_size=target_size,
        content_box=content_box,
        num_lines_range=(5, 11),
        width_range=(2, 5),
    )

    small_loss = _generate_blob_mask(
        rng=rng,
        target_size=target_size,
        content_box=content_box,
        num_blobs=int(rng.integers(3, 7)),
        radius_range=(16, 38),
        num_points_range=(8, 15),
        blur_radius=1.4,
    )

    medium_loss = _generate_blob_mask(
        rng=rng,
        target_size=target_size,
        content_box=content_box,
        num_blobs=1,
        radius_range=(55, 115),
        num_points_range=(12, 22),
        blur_radius=2.2,
    )

    edge_loss = _generate_edge_loss_mask(
        rng=rng,
        target_size=target_size,
        content_box=content_box,
        radius_range=(28, 70),
    )

    mixed = _combine_masks(
        scratch,
        small_loss,
        medium_loss,
        edge_loss,
    )

    return _clip_mask_to_content_region(
        mask=_binary_mask(mixed),
        target_size=target_size,
        content_box=content_box,
    )


def _connected_components_8(
    binary_arr: np.ndarray,
) -> list[dict[str, int]]:
    """Return 8-connected component statistics without SciPy."""
    if binary_arr.ndim != 2:
        raise ValueError(
            "Connected-component analysis requires a 2-D array."
        )

    height, width = binary_arr.shape
    visited = np.zeros_like(binary_arr, dtype=bool)

    neighbour_offsets = (
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
        (1, 1),
    )

    components: list[dict[str, int]] = []

    start_points = np.argwhere(binary_arr)

    for start_y, start_x in start_points:
        start_y = int(start_y)
        start_x = int(start_x)

        if visited[start_y, start_x]:
            continue

        queue: deque[tuple[int, int]] = deque(
            [(start_y, start_x)]
        )
        visited[start_y, start_x] = True

        area = 0
        x_min = start_x
        x_max = start_x
        y_min = start_y
        y_max = start_y

        while queue:
            y, x = queue.popleft()
            area += 1

            x_min = min(x_min, x)
            x_max = max(x_max, x)
            y_min = min(y_min, y)
            y_max = max(y_max, y)

            for delta_y, delta_x in neighbour_offsets:
                next_y = y + delta_y
                next_x = x + delta_x

                if not (
                    0 <= next_y < height
                    and 0 <= next_x < width
                ):
                    continue

                if (
                    binary_arr[next_y, next_x]
                    and not visited[next_y, next_x]
                ):
                    visited[next_y, next_x] = True
                    queue.append((next_y, next_x))

        component_width = x_max - x_min + 1
        component_height = y_max - y_min + 1

        components.append(
            {
                "area_pixels": area,
                "bbox_width": component_width,
                "bbox_height": component_height,
                "bbox_area_pixels": (
                    component_width * component_height
                ),
            }
        )

    return components


def _mask_bbox_from_array(
    mask_arr: np.ndarray,
) -> dict[str, int | None]:
    """Return a half-open bounding box for damaged pixels."""
    ys, xs = np.where(mask_arr)

    if len(xs) == 0:
        return {
            "bbox_x_min": None,
            "bbox_y_min": None,
            "bbox_x_max": None,
            "bbox_y_max": None,
            "bbox_width": 0,
            "bbox_height": 0,
            "bbox_area_pixels": 0,
        }

    x_min = int(xs.min())
    x_max = int(xs.max()) + 1
    y_min = int(ys.min())
    y_max = int(ys.max()) + 1

    bbox_width = x_max - x_min
    bbox_height = y_max - y_min

    return {
        "bbox_x_min": x_min,
        "bbox_y_min": y_min,
        "bbox_x_max": x_max,
        "bbox_y_max": y_max,
        "bbox_width": bbox_width,
        "bbox_height": bbox_height,
        "bbox_area_pixels": bbox_width * bbox_height,
    }


def _touches_content_border(
    mask_arr: np.ndarray,
    content_box: tuple[int, int, int, int],
) -> bool:
    """Return whether damage touches any content-box border."""
    if not mask_arr.any():
        return False

    x_min, y_min, x_max, y_max = content_box

    return bool(
        mask_arr[y_min:y_max, x_min].any()
        or mask_arr[y_min:y_max, x_max - 1].any()
        or mask_arr[y_min, x_min:x_max].any()
        or mask_arr[y_max - 1, x_min:x_max].any()
    )


def _minimum_distance_to_content_border(
    mask_arr: np.ndarray,
    content_box: tuple[int, int, int, int],
) -> int | None:
    """Return minimum damaged-pixel distance to a content border."""
    ys, xs = np.where(mask_arr)

    if len(xs) == 0:
        return None

    x_min, y_min, x_max, y_max = content_box

    distances = np.minimum.reduce(
        [
            xs - x_min,
            (x_max - 1) - xs,
            ys - y_min,
            (y_max - 1) - ys,
        ]
    )

    return int(distances.min())


def _mask_morphology_metadata(
    mask: Image.Image,
    target_size: int,
    content_box: tuple[int, int, int, int],
) -> dict[str, Any]:
    """Calculate canonical area, component, and morphology metadata."""
    mask_arr = _binary_array(mask)
    content_arr = _content_region_mask(
        target_size,
        content_box,
    )

    full_pixels = target_size * target_size
    content_pixels = int(content_arr.sum())
    padding_pixels = full_pixels - content_pixels

    damaged_pixels = int(mask_arr.sum())
    damaged_content_pixels = int(
        (mask_arr & content_arr).sum()
    )
    padding_overlap_pixels = int(
        (mask_arr & ~content_arr).sum()
    )

    bbox = _mask_bbox_from_array(mask_arr)
    components = _connected_components_8(mask_arr)

    component_areas = np.asarray(
        [
            component["area_pixels"]
            for component in components
        ],
        dtype=float,
    )

    component_bbox_aspects = np.asarray(
        [
            max(
                component["bbox_width"],
                component["bbox_height"],
            )
            / max(
                1,
                min(
                    component["bbox_width"],
                    component["bbox_height"],
                ),
            )
            for component in components
        ],
        dtype=float,
    )

    connected_component_count = len(components)

    largest_component_pixels = (
        int(component_areas.max())
        if connected_component_count
        else 0
    )

    smallest_component_pixels = (
        int(component_areas.min())
        if connected_component_count
        else 0
    )

    mean_component_pixels = (
        float(component_areas.mean())
        if connected_component_count
        else 0.0
    )

    median_component_pixels = (
        float(np.median(component_areas))
        if connected_component_count
        else 0.0
    )

    component_area_std_pixels = (
        float(component_areas.std(ddof=0))
        if connected_component_count
        else 0.0
    )

    mean_component_aspect_ratio = (
        float(component_bbox_aspects.mean())
        if connected_component_count
        else 0.0
    )

    maximum_component_aspect_ratio = (
        float(component_bbox_aspects.max())
        if connected_component_count
        else 0.0
    )

    bbox_area_pixels = int(
        bbox["bbox_area_pixels"] or 0
    )

    bbox_fill_ratio = (
        damaged_pixels / bbox_area_pixels
        if bbox_area_pixels > 0
        else 0.0
    )

    content_fill_ratio = (
        damaged_content_pixels / content_pixels
        if content_pixels > 0
        else 0.0
    )

    full_fill_ratio = damaged_pixels / full_pixels

    component_density_per_100k_content_pixels = (
        connected_component_count
        / content_pixels
        * 100_000
        if content_pixels > 0
        else 0.0
    )

    largest_component_fraction = (
        largest_component_pixels / damaged_pixels
        if damaged_pixels > 0
        else 0.0
    )

    bbox_aspect_ratio = (
        max(
            int(bbox["bbox_width"]),
            int(bbox["bbox_height"]),
        )
        / max(
            1,
            min(
                int(bbox["bbox_width"]),
                int(bbox["bbox_height"]),
            ),
        )
        if bbox_area_pixels > 0
        else 0.0
    )

    return {
        "canvas_area_pixels": full_pixels,
        "content_area_pixels": content_pixels,
        "padding_area_pixels": padding_pixels,
        "actual_mask_area_pixels": damaged_pixels,
        "damaged_content_pixels": damaged_content_pixels,
        "padding_overlap_pixels": padding_overlap_pixels,
        "actual_mask_area_percentage_content": round(
            content_fill_ratio * 100.0,
            6,
        ),
        "actual_mask_area_percentage_full": round(
            full_fill_ratio * 100.0,
            6,
        ),
        **bbox,
        "bbox_fill_ratio": round(
            bbox_fill_ratio,
            6,
        ),
        "bbox_aspect_ratio": round(
            bbox_aspect_ratio,
            6,
        ),
        "connected_component_count": connected_component_count,
        "largest_component_pixels": largest_component_pixels,
        "smallest_component_pixels": smallest_component_pixels,
        "mean_component_pixels": round(
            mean_component_pixels,
            6,
        ),
        "median_component_pixels": round(
            median_component_pixels,
            6,
        ),
        "component_area_std_pixels": round(
            component_area_std_pixels,
            6,
        ),
        "largest_component_fraction": round(
            largest_component_fraction,
            6,
        ),
        "component_density_per_100k_content_pixels": round(
            component_density_per_100k_content_pixels,
            6,
        ),
        "mean_component_aspect_ratio": round(
            mean_component_aspect_ratio,
            6,
        ),
        "maximum_component_aspect_ratio": round(
            maximum_component_aspect_ratio,
            6,
        ),
        "touches_content_border": _touches_content_border(
            mask_arr,
            content_box,
        ),
        "minimum_distance_to_content_border_pixels": (
            _minimum_distance_to_content_border(
                mask_arr,
                content_box,
            )
        ),
    }


def _normalize_mask_specs(
    mask_types: Sequence[str],
    mask_specs: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, dict[str, float]]:
    """Normalize and validate mask-area specifications."""
    raw_specs = (
        DEFAULT_MASK_SPECS
        if mask_specs is None
        else mask_specs
    )

    normalized: dict[str, dict[str, float]] = {}

    for mask_type in mask_types:
        if mask_type not in SUPPORTED_MASK_TYPES:
            raise ValueError(
                f"Unsupported mask type: {mask_type}"
            )

        if mask_type not in raw_specs:
            raise ValueError(
                f"Missing mask specification for {mask_type}."
            )

        raw_spec = raw_specs[mask_type]

        target_pct = float(
            raw_spec.get(
                "target_area_pct",
                raw_spec.get("target_pct", 0.0),
            )
        )
        min_pct = float(
            raw_spec.get(
                "min_area_pct",
                raw_spec.get("min_pct", target_pct),
            )
        )
        max_pct = float(
            raw_spec.get(
                "max_area_pct",
                raw_spec.get("max_pct", target_pct),
            )
        )

        if not (
            0.0
            <= min_pct
            <= target_pct
            <= max_pct
            <= 100.0
        ):
            raise ValueError(
                f"Invalid area specification for {mask_type}: "
                f"min={min_pct}, target={target_pct}, max={max_pct}."
            )

        if mask_type == "zero_control" and (
            min_pct != 0.0
            or target_pct != 0.0
            or max_pct != 0.0
        ):
            raise ValueError(
                "zero_control must use exactly 0% area."
            )

        normalized[mask_type] = {
            "target_area_pct": target_pct,
            "min_area_pct": min_pct,
            "max_area_pct": max_pct,
        }

    return normalized


def _generate_mask_with_area_retry(
    mask_type: str,
    mask_seed: int,
    target_size: int,
    content_box: tuple[int, int, int, int],
    target_pct: float,
    min_pct: float,
    max_pct: float,
    max_attempts: int,
) -> tuple[Image.Image, dict[str, Any]]:
    """Generate one mask and retain the closest attempt if none pass."""
    if max_attempts < 1:
        raise ValueError(
            "max_attempts must be at least 1."
        )

    if mask_type == "zero_control":
        retry_seed = _stable_seed(
            mask_seed,
            mask_type,
            1,
        )

        mask = generate_mask_by_type(
            mask_type=mask_type,
            rng=np.random.default_rng(retry_seed),
            target_size=target_size,
            content_box=content_box,
        )

        return mask, {
            "generation_attempts": 1,
            "accepted_attempt": 1,
            "retry_seed": retry_seed,
            "area_distance_to_target_pct": 0.0,
            "area_distance_to_allowed_range_pct": 0.0,
            "area_within_target_tolerance": True,
            "generation_status": "ok",
        }

    best_mask: Image.Image | None = None
    best_metadata: dict[str, Any] | None = None
    best_target_distance = float("inf")
    best_range_distance = float("inf")

    for attempt_number in range(1, max_attempts + 1):
        retry_seed = _stable_seed(
            mask_seed,
            mask_type,
            attempt_number,
        )

        rng = np.random.default_rng(retry_seed)

        mask = generate_mask_by_type(
            mask_type=mask_type,
            rng=rng,
            target_size=target_size,
            content_box=content_box,
        )

        area_pct = _mask_area_percentage_content(
            mask=mask,
            target_size=target_size,
            content_box=content_box,
        )

        target_distance = abs(area_pct - target_pct)

        if area_pct < min_pct:
            range_distance = min_pct - area_pct
        elif area_pct > max_pct:
            range_distance = area_pct - max_pct
        else:
            range_distance = 0.0

        candidate_metadata = {
            "generation_attempts": attempt_number,
            "accepted_attempt": attempt_number,
            "retry_seed": retry_seed,
            "area_distance_to_target_pct": round(
                target_distance,
                6,
            ),
            "area_distance_to_allowed_range_pct": round(
                range_distance,
                6,
            ),
            "area_within_target_tolerance": (
                range_distance == 0.0
            ),
            "generation_status": (
                "ok"
                if range_distance == 0.0
                else "candidate_outside_target_range"
            ),
        }

        is_better = (
            range_distance < best_range_distance
            or (
                np.isclose(
                    range_distance,
                    best_range_distance,
                )
                and target_distance < best_target_distance
            )
        )

        if is_better:
            best_mask = mask
            best_metadata = candidate_metadata
            best_target_distance = target_distance
            best_range_distance = range_distance

        if range_distance == 0.0:
            return mask, candidate_metadata

    if best_mask is None or best_metadata is None:
        raise RuntimeError(
            f"No mask candidate was produced for {mask_type}."
        )

    best_metadata = {
        **best_metadata,
        "generation_attempts": max_attempts,
        "area_within_target_tolerance": False,
        "generation_status": (
            "area_outside_target_after_retries"
        ),
    }

    return best_mask, best_metadata


def generate_masks_for_dataset(
    metadata: pd.DataFrame,
    mask_dir: Path,
    target_size: int = 768,
    mask_types: Sequence[str] | None = None,
    base_seed: int = 20260630,
    mask_specs: Mapping[str, Mapping[str, Any]] | None = None,
    max_attempts: int = 30,
    generator_name: str = GENERATOR_NAME,
    generator_version: str = GENERATOR_VERSION,
    config_version: str = "unversioned",
    experiment_name: str = "unnamed_experiment",
    experiment_version: str = "unversioned",
) -> pd.DataFrame:
    """Generate canonical controlled masks for every processed painting."""
    mask_dir = Path(mask_dir)
    mask_dir.mkdir(parents=True, exist_ok=True)

    selected_mask_types = (
        list(SUPPORTED_MASK_TYPES)
        if mask_types is None
        else list(mask_types)
    )

    if not selected_mask_types:
        raise ValueError(
            "At least one mask type must be configured."
        )

    if len(selected_mask_types) != len(set(selected_mask_types)):
        raise ValueError(
            "Configured mask types contain duplicates."
        )

    normalized_specs = _normalize_mask_specs(
        mask_types=selected_mask_types,
        mask_specs=mask_specs,
    )

    required_columns = [
        "painting_id",
        "content_x_min",
        "content_y_min",
        "content_x_max",
        "content_y_max",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in metadata.columns
    ]

    if missing_columns:
        raise ValueError(
            "Processed metadata is missing required columns: "
            f"{missing_columns}"
        )

    if metadata["painting_id"].isna().any():
        raise ValueError(
            "Processed metadata contains null painting IDs."
        )

    if metadata["painting_id"].duplicated().any():
        duplicate_ids = (
            metadata.loc[
                metadata["painting_id"].duplicated(
                    keep=False
                ),
                "painting_id",
            ]
            .astype(str)
            .tolist()
        )

        raise ValueError(
            "Processed metadata contains duplicate painting IDs: "
            f"{duplicate_ids}"
        )

    records: list[dict[str, Any]] = []

    sorted_metadata = metadata.sort_values(
        "painting_id",
        kind="stable",
    ).reset_index(drop=True)

    for painting_index, row in sorted_metadata.iterrows():
        painting_id = str(row["painting_id"])
        content_box = _content_box_from_row(row)

        _validate_content_box(
            target_size,
            content_box,
        )

        painting_seed = _stable_seed(
            base_seed,
            experiment_name,
            experiment_version,
            painting_id,
        )

        for mask_type_index, mask_type in enumerate(
            selected_mask_types
        ):
            spec = normalized_specs[mask_type]

            mask_seed = _stable_seed(
                painting_seed,
                mask_type,
                mask_type_index,
            )

            mask_id = f"{painting_id}_{mask_type}"
            case_id = mask_id
            mask_filename = f"{mask_id}_mask.png"
            mask_path = mask_dir / mask_filename

            mask, generation_metadata = (
                _generate_mask_with_area_retry(
                    mask_type=mask_type,
                    mask_seed=mask_seed,
                    target_size=target_size,
                    content_box=content_box,
                    target_pct=spec["target_area_pct"],
                    min_pct=spec["min_area_pct"],
                    max_pct=spec["max_area_pct"],
                    max_attempts=max_attempts,
                )
            )

            mask = _clip_mask_to_content_region(
                mask=_binary_mask(mask),
                target_size=target_size,
                content_box=content_box,
            )

            morphology = _mask_morphology_metadata(
                mask=mask,
                target_size=target_size,
                content_box=content_box,
            )

            unique_values = sorted(
                np.unique(
                    np.asarray(mask.convert("L"))
                )
                .astype(int)
                .tolist()
            )

            area_within_range = bool(
                spec["min_area_pct"]
                <= morphology[
                    "actual_mask_area_percentage_content"
                ]
                <= spec["max_area_pct"]
            )

            zero_control_valid = (
                morphology["actual_mask_area_pixels"] == 0
                if mask_type == "zero_control"
                else morphology["actual_mask_area_pixels"] > 0
            )

            padding_valid = (
                morphology["padding_overlap_pixels"] == 0
            )

            binary_valid = set(
                unique_values
            ).issubset({0, 255})

            generation_valid = bool(
                area_within_range
                and zero_control_valid
                and padding_valid
                and binary_valid
            )

            issue_parts: list[str] = []

            if not area_within_range:
                issue_parts.append(
                    "area_outside_configured_range"
                )

            if not zero_control_valid:
                issue_parts.append(
                    "invalid_zero_or_nonzero_damage"
                )

            if not padding_valid:
                issue_parts.append(
                    "padding_overlap_detected"
                )

            if not binary_valid:
                issue_parts.append(
                    "mask_not_binary"
                )

            mask.save(
                mask_path,
                format="PNG",
            )

            records.append(
                {
                    "case_id": case_id,
                    "painting_id": painting_id,
                    "mask_id": mask_id,
                    "mask_type": mask_type,
                    "mask_type_index": mask_type_index,
                    "mask_filename": mask_filename,
                    "mask_path": str(mask_path),
                    "generator_name": generator_name,
                    "generator_version": generator_version,
                    "config_version": config_version,
                    "experiment_name": experiment_name,
                    "experiment_version": experiment_version,
                    "global_seed": int(base_seed),
                    "painting_seed": int(painting_seed),
                    "mask_seed": int(mask_seed),
                    "retry_seed": int(
                        generation_metadata["retry_seed"]
                    ),
                    "painting_index": int(painting_index),
                    "target_area_pct": (
                        spec["target_area_pct"]
                    ),
                    "target_area_min_pct": (
                        spec["min_area_pct"]
                    ),
                    "target_area_max_pct": (
                        spec["max_area_pct"]
                    ),
                    "content_x_min": content_box[0],
                    "content_y_min": content_box[1],
                    "content_x_max": content_box[2],
                    "content_y_max": content_box[3],
                    **morphology,
                    **generation_metadata,
                    "unique_pixel_values": (
                        "|".join(
                            str(value)
                            for value in unique_values
                        )
                    ),
                    "binary_values_valid": binary_valid,
                    "zero_control_rule_valid": (
                        zero_control_valid
                    ),
                    "content_only_valid": padding_valid,
                    "area_within_target_tolerance": (
                        area_within_range
                    ),
                    "generation_valid": generation_valid,
                    "status": (
                        "ok"
                        if generation_valid
                        else "warning"
                    ),
                    "issue": "|".join(issue_parts),
                }
            )

    result = pd.DataFrame(records)

    expected_rows = (
        len(sorted_metadata)
        * len(selected_mask_types)
    )

    if len(result) != expected_rows:
        raise RuntimeError(
            f"Expected {expected_rows} generated-mask records, "
            f"produced {len(result)}."
        )

    return result


def validate_masks(
    mask_metadata: pd.DataFrame,
    target_size: int = 768,
) -> pd.DataFrame:
    """Validate saved masks against metadata and canonical rules."""
    required_columns = [
        "case_id",
        "painting_id",
        "mask_type",
        "mask_path",
        "content_x_min",
        "content_y_min",
        "content_x_max",
        "content_y_max",
        "target_area_min_pct",
        "target_area_max_pct",
        "actual_mask_area_pixels",
        "actual_mask_area_percentage_content",
        "padding_overlap_pixels",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in mask_metadata.columns
    ]

    if missing_columns:
        raise ValueError(
            "Mask metadata is missing validation columns: "
            f"{missing_columns}"
        )

    validation_rows: list[dict[str, Any]] = []

    for _, row in mask_metadata.iterrows():
        mask_path = Path(str(row["mask_path"]))
        content_box = (
            int(row["content_x_min"]),
            int(row["content_y_min"]),
            int(row["content_x_max"]),
            int(row["content_y_max"]),
        )

        file_exists = mask_path.exists()
        readable = False
        saved_format: str | None = None
        saved_mode: str | None = None
        width: int | None = None
        height: int | None = None
        unique_values: list[int] = []

        recalculated_metadata: dict[str, Any] = {}
        issues: list[str] = []

        if not file_exists:
            issues.append("missing_mask_file")
        else:
            try:
                with Image.open(mask_path) as opened_image:
                    saved_format = opened_image.format
                    saved_mode = opened_image.mode
                    width, height = opened_image.size

                    mask = opened_image.convert("L")
                    mask.load()
                    readable = True

                unique_values = sorted(
                    np.unique(
                        np.asarray(mask)
                    )
                    .astype(int)
                    .tolist()
                )

                if width != target_size or height != target_size:
                    issues.append("wrong_mask_size")

                if saved_format != "PNG":
                    issues.append("wrong_mask_format")

                if saved_mode != "L":
                    issues.append("wrong_saved_mask_mode")

                if not set(unique_values).issubset(
                    {0, 255}
                ):
                    issues.append("mask_not_binary")

                if (
                    width == target_size
                    and height == target_size
                ):
                    recalculated_metadata = (
                        _mask_morphology_metadata(
                            mask=mask,
                            target_size=target_size,
                            content_box=content_box,
                        )
                    )

                    recalculated_pixels = int(
                        recalculated_metadata[
                            "actual_mask_area_pixels"
                        ]
                    )

                    stored_pixels = int(
                        row["actual_mask_area_pixels"]
                    )

                    if recalculated_pixels != stored_pixels:
                        issues.append(
                            "stored_pixel_count_mismatch"
                        )

                    recalculated_content_pct = float(
                        recalculated_metadata[
                            "actual_mask_area_percentage_content"
                        ]
                    )

                    stored_content_pct = float(
                        row[
                            "actual_mask_area_percentage_content"
                        ]
                    )

                    if not np.isclose(
                        recalculated_content_pct,
                        stored_content_pct,
                        atol=1e-4,
                    ):
                        issues.append(
                            "stored_content_percentage_mismatch"
                        )

                    recalculated_padding_overlap = int(
                        recalculated_metadata[
                            "padding_overlap_pixels"
                        ]
                    )

                    stored_padding_overlap = int(
                        row["padding_overlap_pixels"]
                    )

                    if (
                        recalculated_padding_overlap
                        != stored_padding_overlap
                    ):
                        issues.append(
                            "stored_padding_overlap_mismatch"
                        )

                    if recalculated_padding_overlap > 0:
                        issues.append(
                            "mask_pixels_outside_content_region"
                        )

                    minimum_pct = float(
                        row["target_area_min_pct"]
                    )
                    maximum_pct = float(
                        row["target_area_max_pct"]
                    )

                    if not (
                        minimum_pct
                        <= recalculated_content_pct
                        <= maximum_pct
                    ):
                        issues.append(
                            "area_outside_configured_range"
                        )

                    if row["mask_type"] == "zero_control":
                        if recalculated_pixels != 0:
                            issues.append(
                                "zero_control_contains_damage"
                            )
                    elif recalculated_pixels == 0:
                        issues.append(
                            "nonzero_mask_contains_no_damage"
                        )

            except Exception as exc:
                issues.append(
                    "unreadable_mask_file:"
                    f"{type(exc).__name__}:{exc}"
                )

        validation_rows.append(
            {
                "case_id": row["case_id"],
                "painting_id": row["painting_id"],
                "mask_type": row["mask_type"],
                "mask_path": str(mask_path),
                "file_exists": file_exists,
                "readable": readable,
                "saved_format": saved_format,
                "saved_mode": saved_mode,
                "width": width,
                "height": height,
                "unique_pixel_values": (
                    "|".join(
                        str(value)
                        for value in unique_values
                    )
                ),
                "recalculated_mask_area_pixels": (
                    recalculated_metadata.get(
                        "actual_mask_area_pixels"
                    )
                ),
                "recalculated_mask_area_percentage_content": (
                    recalculated_metadata.get(
                        "actual_mask_area_percentage_content"
                    )
                ),
                "recalculated_padding_overlap_pixels": (
                    recalculated_metadata.get(
                        "padding_overlap_pixels"
                    )
                ),
                "validation_passed": len(issues) == 0,
                "issue_count": len(issues),
                "issue": "|".join(issues),
            }
        )

    return pd.DataFrame(validation_rows)


def audit_mask_inventory(
    mask_metadata: pd.DataFrame,
    mask_dir: Path,
    expected_mask_types: Sequence[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Audit metadata duplicates, missing files, and orphan PNG files."""
    mask_dir = Path(mask_dir)

    expected_types = (
        list(SUPPORTED_MASK_TYPES)
        if expected_mask_types is None
        else list(expected_mask_types)
    )

    duplicate_case_rows = mask_metadata[
        mask_metadata.duplicated(
            subset=["case_id"],
            keep=False,
        )
    ].copy()

    duplicate_mask_id_rows = mask_metadata[
        mask_metadata.duplicated(
            subset=["mask_id"],
            keep=False,
        )
    ].copy()

    duplicate_filename_rows = mask_metadata[
        mask_metadata.duplicated(
            subset=["mask_filename"],
            keep=False,
        )
    ].copy()

    duplicate_path_rows = mask_metadata[
        mask_metadata.duplicated(
            subset=["mask_path"],
            keep=False,
        )
    ].copy()

    missing_file_rows = mask_metadata[
        ~mask_metadata["mask_path"]
        .astype(str)
        .map(lambda value: Path(value).exists())
    ].copy()

    metadata_filenames = set(
        mask_metadata["mask_filename"]
        .astype(str)
        .tolist()
    )

    disk_files = sorted(
        path
        for path in mask_dir.glob("*.png")
        if path.is_file()
    )

    disk_filenames = {
        path.name
        for path in disk_files
    }

    orphan_filenames = sorted(
        disk_filenames - metadata_filenames
    )

    orphan_file_rows = pd.DataFrame(
        {
            "mask_filename": orphan_filenames,
            "mask_path": [
                str(mask_dir / filename)
                for filename in orphan_filenames
            ],
            "issue": "orphan_mask_file",
        }
    )

    missing_type_rows: list[dict[str, Any]] = []

    if {"painting_id", "mask_type"}.issubset(
        mask_metadata.columns
    ):
        for painting_id, group in mask_metadata.groupby(
            "painting_id",
            sort=True,
        ):
            present_types = set(
                group["mask_type"]
                .astype(str)
                .tolist()
            )

            for mask_type in expected_types:
                if mask_type not in present_types:
                    missing_type_rows.append(
                        {
                            "painting_id": painting_id,
                            "mask_type": mask_type,
                            "issue": (
                                "missing_painting_mask_type"
                            ),
                        }
                    )

    missing_mask_type_rows = pd.DataFrame(
        missing_type_rows
    )

    unexpected_mask_type_rows = mask_metadata[
        ~mask_metadata["mask_type"].isin(expected_types)
    ].copy()

    return {
        "duplicate_case_rows": duplicate_case_rows,
        "duplicate_mask_id_rows": duplicate_mask_id_rows,
        "duplicate_filename_rows": duplicate_filename_rows,
        "duplicate_path_rows": duplicate_path_rows,
        "missing_file_rows": missing_file_rows,
        "orphan_file_rows": orphan_file_rows,
        "missing_mask_type_rows": missing_mask_type_rows,
        "unexpected_mask_type_rows": unexpected_mask_type_rows,
    }