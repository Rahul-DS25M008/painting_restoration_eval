"""Synthetic damage mask generation utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFilter


DEFAULT_MASK_SPECS: dict[str, dict[str, float]] = {
    "zero_control": {"min_pct": 0.0, "max_pct": 0.0},
    "scratch_thin": {"min_pct": 1.0, "max_pct": 3.0},
    "loss_small": {"min_pct": 3.0, "max_pct": 6.0},
    "loss_large": {"min_pct": 10.0, "max_pct": 18.0},
    "mixed_damage": {"min_pct": 8.0, "max_pct": 15.0},
}


def _content_box_from_row(row: pd.Series) -> tuple[int, int, int, int]:
    """Return the valid painting-content box as integer coordinates."""
    return (
        int(row["content_x_min"]),
        int(row["content_y_min"]),
        int(row["content_x_max"]),
        int(row["content_y_max"]),
    )


def _content_region_mask(
    target_size: int,
    content_box: tuple[int, int, int, int],
) -> np.ndarray:
    """Return a boolean mask for the valid painting-content region."""
    x_min, y_min, x_max, y_max = content_box

    region = np.zeros((target_size, target_size), dtype=bool)
    region[y_min:y_max, x_min:x_max] = True
    return region


def _clip_mask_to_content_region(
    mask: Image.Image,
    target_size: int,
    content_box: tuple[int, int, int, int],
) -> Image.Image:
    """Remove any mask pixels outside the painting-content region."""
    mask_arr = np.asarray(mask.convert("L")) > 0
    content_arr = _content_region_mask(target_size, content_box)

    clipped = np.where(mask_arr & content_arr, 255, 0).astype(np.uint8)
    return Image.fromarray(clipped, mode="L")


def _mask_area_percentage_content(
    mask: Image.Image,
    target_size: int,
    content_box: tuple[int, int, int, int],
) -> float:
    """Return mask area as percentage of the painting-content region."""
    mask_arr = np.asarray(mask.convert("L")) > 0
    content_arr = _content_region_mask(target_size, content_box)

    content_pixels = int(content_arr.sum())
    if content_pixels == 0:
        return 0.0

    damaged_pixels = int((mask_arr & content_arr).sum())
    return damaged_pixels / content_pixels * 100.0


def _binary_mask(mask: Image.Image) -> Image.Image:
    """Ensure a grayscale mask is strictly binary: 0 or 255."""
    arr = np.asarray(mask.convert("L"))
    binary = np.where(arr > 0, 255, 0).astype(np.uint8)
    return Image.fromarray(binary, mode="L")


def _random_point_in_content(
    rng: np.random.Generator,
    content_box: tuple[int, int, int, int],
    margin: int = 0,
) -> tuple[int, int]:
    """Sample a point inside the content region."""
    x_min, y_min, x_max, y_max = content_box

    left = min(max(x_min + margin, x_min), x_max - 1)
    right = max(min(x_max - margin, x_max), left + 1)
    top = min(max(y_min + margin, y_min), y_max - 1)
    bottom = max(min(y_max - margin, y_max), top + 1)

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
    """Draw one irregular filled blob."""
    cx, cy = center
    angles = np.linspace(0, 2 * np.pi, num_points, endpoint=False)
    rng.shuffle(angles)

    points = []
    for angle in sorted(angles):
        radius = int(rng.integers(radius_range[0], radius_range[1] + 1))
        jitter_x = int(rng.integers(-radius * 0.15, radius * 0.15 + 1))
        jitter_y = int(rng.integers(-radius * 0.15, radius * 0.15 + 1))

        x = cx + int(radius * np.cos(angle)) + jitter_x
        y = cy + int(radius * np.sin(angle)) + jitter_y
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
    """Generate an irregular blob-style loss mask."""
    mask = Image.new("L", (target_size, target_size), 0)
    draw = ImageDraw.Draw(mask)

    for _ in range(num_blobs):
        radius_max = radius_range[1]
        center = _random_point_in_content(rng, content_box, margin=radius_max)
        num_points = int(rng.integers(num_points_range[0], num_points_range[1] + 1))

        _draw_irregular_blob(
            draw=draw,
            rng=rng,
            center=center,
            radius_range=radius_range,
            num_points=num_points,
        )

    if blur_radius > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        mask = mask.point(lambda p: 255 if p > 80 else 0)

    mask = _binary_mask(mask)
    return _clip_mask_to_content_region(mask, target_size, content_box)


def _generate_scratch_mask(
    rng: np.random.Generator,
    target_size: int,
    content_box: tuple[int, int, int, int],
    num_lines_range: tuple[int, int] = (8, 16),
    width_range: tuple[int, int] = (2, 5),
    segment_count_range: tuple[int, int] = (3, 6),
    step_length_range: tuple[int, int] = (40, 120),
) -> Image.Image:
    """Generate thin irregular scratch/crack-like line damage."""
    mask = Image.new("L", (target_size, target_size), 0)
    draw = ImageDraw.Draw(mask)

    num_lines = int(rng.integers(num_lines_range[0], num_lines_range[1] + 1))

    for _ in range(num_lines):
        x, y = _random_point_in_content(rng, content_box)
        points = [(x, y)]

        angle = float(rng.uniform(0, 2 * np.pi))
        segment_count = int(rng.integers(segment_count_range[0], segment_count_range[1] + 1))

        for _segment in range(segment_count):
            angle += float(rng.normal(0, 0.45))
            step = int(rng.integers(step_length_range[0], step_length_range[1] + 1))

            x = int(x + step * np.cos(angle))
            y = int(y + step * np.sin(angle))

            x_min, y_min, x_max, y_max = content_box
            x = int(np.clip(x, x_min, x_max - 1))
            y = int(np.clip(y, y_min, y_max - 1))

            points.append((x, y))

        width = int(rng.integers(width_range[0], width_range[1] + 1))
        draw.line(points, fill=255, width=width, joint="curve")

    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.4))
    mask = mask.point(lambda p: 255 if p > 35 else 0)
    mask = _binary_mask(mask)
    return _clip_mask_to_content_region(mask, target_size, content_box)


def _generate_edge_loss_mask(
    rng: np.random.Generator,
    target_size: int,
    content_box: tuple[int, int, int, int],
    radius_range: tuple[int, int] = (35, 90),
) -> Image.Image:
    """Generate one irregular loss touching a content-region border."""
    x_min, y_min, x_max, y_max = content_box
    side = rng.choice(["left", "right", "top", "bottom"])

    if side == "left":
        center = (x_min + int(rng.integers(0, radius_range[1] + 1)), int(rng.integers(y_min, y_max)))
    elif side == "right":
        center = (x_max - 1 - int(rng.integers(0, radius_range[1] + 1)), int(rng.integers(y_min, y_max)))
    elif side == "top":
        center = (int(rng.integers(x_min, x_max)), y_min + int(rng.integers(0, radius_range[1] + 1)))
    else:
        center = (int(rng.integers(x_min, x_max)), y_max - 1 - int(rng.integers(0, radius_range[1] + 1)))

    mask = Image.new("L", (target_size, target_size), 0)
    draw = ImageDraw.Draw(mask)
    _draw_irregular_blob(
        draw=draw,
        rng=rng,
        center=center,
        radius_range=radius_range,
        num_points=int(rng.integers(10, 18)),
    )

    mask = mask.filter(ImageFilter.GaussianBlur(radius=2))
    mask = mask.point(lambda p: 255 if p > 80 else 0)
    mask = _binary_mask(mask)
    return _clip_mask_to_content_region(mask, target_size, content_box)


def _combine_masks(*masks: Image.Image) -> Image.Image:
    """Combine masks using a logical OR."""
    if not masks:
        raise ValueError("At least one mask is required.")

    arrays = [np.asarray(mask.convert("L")) > 0 for mask in masks]
    combined = np.logical_or.reduce(arrays)
    return Image.fromarray(np.where(combined, 255, 0).astype(np.uint8), mode="L")


def generate_mask_by_type(
    mask_type: str,
    rng: np.random.Generator,
    target_size: int,
    content_box: tuple[int, int, int, int],
) -> Image.Image:
    """Generate one binary mask for a given mask type."""
    if mask_type == "zero_control":
        return Image.new("L", (target_size, target_size), 0)

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

    if mask_type == "mixed_damage":
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
        return _combine_masks(scratch, small_loss, medium_loss, edge_loss)

    raise ValueError(f"Unsupported mask type: {mask_type}")


def _mask_bbox(mask: Image.Image) -> dict[str, int | None]:
    """Return bounding-box metadata for non-zero mask pixels."""
    arr = np.asarray(mask.convert("L")) > 0
    ys, xs = np.where(arr)

    if len(xs) == 0:
        return {
            "bbox_x_min": None,
            "bbox_y_min": None,
            "bbox_x_max": None,
            "bbox_y_max": None,
            "bbox_width": 0,
            "bbox_height": 0,
        }

    x_min = int(xs.min())
    x_max = int(xs.max()) + 1
    y_min = int(ys.min())
    y_max = int(ys.max()) + 1

    return {
        "bbox_x_min": x_min,
        "bbox_y_min": y_min,
        "bbox_x_max": x_max,
        "bbox_y_max": y_max,
        "bbox_width": x_max - x_min,
        "bbox_height": y_max - y_min,
    }


def _touches_content_border(
    mask: Image.Image,
    content_box: tuple[int, int, int, int],
) -> bool:
    """Return whether a mask touches the content-region border."""
    arr = np.asarray(mask.convert("L")) > 0
    x_min, y_min, x_max, y_max = content_box

    if not arr.any():
        return False

    return bool(
        arr[y_min:y_max, x_min].any()
        or arr[y_min:y_max, x_max - 1].any()
        or arr[y_min, x_min:x_max].any()
        or arr[y_max - 1, x_min:x_max].any()
    )


def _has_pixels_outside_content(
    mask: Image.Image,
    target_size: int,
    content_box: tuple[int, int, int, int],
) -> bool:
    """Return whether any damaged pixels fall outside the content region."""
    mask_arr = np.asarray(mask.convert("L")) > 0
    content_arr = _content_region_mask(target_size, content_box)

    return bool((mask_arr & ~content_arr).any())


def _generate_mask_with_area_retry(
    mask_type: str,
    seed: int,
    target_size: int,
    content_box: tuple[int, int, int, int],
    min_pct: float,
    max_pct: float,
    max_attempts: int = 30,
) -> tuple[Image.Image, float, str]:
    """Generate a mask and retry until its content-area percentage is in range."""
    if mask_type == "zero_control":
        mask = generate_mask_by_type(
            mask_type=mask_type,
            rng=np.random.default_rng(seed),
            target_size=target_size,
            content_box=content_box,
        )
        return mask, 0.0, "ok"

    best_mask = None
    best_pct = None
    best_distance = float("inf")

    for attempt in range(max_attempts):
        rng = np.random.default_rng(seed + attempt)
        mask = generate_mask_by_type(
            mask_type=mask_type,
            rng=rng,
            target_size=target_size,
            content_box=content_box,
        )

        area_pct = _mask_area_percentage_content(mask, target_size, content_box)

        if min_pct <= area_pct <= max_pct:
            return mask, area_pct, "ok"

        if area_pct < min_pct:
            distance = min_pct - area_pct
        else:
            distance = area_pct - max_pct

        if distance < best_distance:
            best_distance = distance
            best_mask = mask
            best_pct = area_pct

    assert best_mask is not None
    return best_mask, float(best_pct), "area_outside_target_after_retries"


def generate_masks_for_dataset(
    metadata: pd.DataFrame,
    mask_dir: Path,
    target_size: int = 768,
    mask_types: list[str] | None = None,
    base_seed: int = 20260630,
    mask_specs: dict[str, dict[str, float]] | None = None,
) -> pd.DataFrame:
    """Generate controlled binary masks for every processed painting."""
    mask_dir.mkdir(parents=True, exist_ok=True)

    if mask_types is None:
        mask_types = list(DEFAULT_MASK_SPECS.keys())

    if mask_specs is None:
        mask_specs = DEFAULT_MASK_SPECS

    required_columns = [
        "painting_id",
        "content_x_min",
        "content_y_min",
        "content_x_max",
        "content_y_max",
    ]
    missing_columns = [col for col in required_columns if col not in metadata.columns]
    if missing_columns:
        raise ValueError(f"Metadata missing required content-region columns: {missing_columns}")

    records: list[dict[str, Any]] = []

    for painting_index, (_, row) in enumerate(metadata.sort_values("painting_id").iterrows()):
        painting_id = row["painting_id"]
        content_box = _content_box_from_row(row)

        for mask_type_index, mask_type in enumerate(mask_types):
            if mask_type not in mask_specs:
                raise ValueError(f"Missing mask specification for mask type: {mask_type}")

            min_pct = float(mask_specs[mask_type]["min_pct"])
            max_pct = float(mask_specs[mask_type]["max_pct"])

            seed = int(base_seed + painting_index * 100 + mask_type_index)
            mask_id = f"{painting_id}_{mask_type}"
            case_id = mask_id
            mask_filename = f"{mask_id}_mask.png"
            mask_path = mask_dir / mask_filename

            mask, area_pct_content, status = _generate_mask_with_area_retry(
                mask_type=mask_type,
                seed=seed,
                target_size=target_size,
                content_box=content_box,
                min_pct=min_pct,
                max_pct=max_pct,
            )

            mask = _binary_mask(mask)
            mask.save(mask_path)

            mask_arr = np.asarray(mask.convert("L")) > 0
            area_pixels = int(mask_arr.sum())
            area_pct_full = area_pixels / (target_size * target_size) * 100.0

            bbox_metadata = _mask_bbox(mask)
            outside_content = _has_pixels_outside_content(mask, target_size, content_box)

            issue = ""
            if outside_content:
                issue = "mask_pixels_outside_content_region"
            elif status != "ok":
                issue = status

            records.append(
                {
                    "case_id": case_id,
                    "painting_id": painting_id,
                    "mask_id": mask_id,
                    "mask_type": mask_type,
                    "mask_filename": mask_filename,
                    "mask_path": str(mask_path),
                    "seed": seed,
                    "target_area_min_pct": min_pct,
                    "target_area_max_pct": max_pct,
                    "actual_mask_area_pixels": area_pixels,
                    "actual_mask_area_percentage_content": round(float(area_pct_content), 4),
                    "actual_mask_area_percentage_full": round(float(area_pct_full), 4),
                    "content_x_min": content_box[0],
                    "content_y_min": content_box[1],
                    "content_x_max": content_box[2],
                    "content_y_max": content_box[3],
                    "touches_content_border": _touches_content_border(mask, content_box),
                    **bbox_metadata,
                    "status": "ok" if issue == "" else "warning",
                    "issue": issue,
                }
            )

    return pd.DataFrame(records)


def validate_masks(
    mask_metadata: pd.DataFrame,
    target_size: int = 768,
) -> pd.DataFrame:
    """Validate generated mask files and return validation rows."""
    validation_rows: list[dict[str, Any]] = []

    for _, row in mask_metadata.iterrows():
        mask_path = Path(row["mask_path"])
        file_exists = mask_path.exists()
        readable = False
        width = None
        height = None
        mode = None
        unique_values: list[int] = []
        issue = ""

        if not file_exists:
            issue = "missing_mask_file"
        else:
            try:
                with Image.open(mask_path) as mask_img:
                    mask = mask_img.convert("L")
                    readable = True
                    width, height = mask.size
                    mode = mask_img.mode
                    unique_values = sorted(np.unique(np.asarray(mask)).astype(int).tolist())
            except Exception as exc:
                issue = f"unreadable_mask_file: {type(exc).__name__}: {exc}"

        if file_exists and readable:
            if width != target_size or height != target_size:
                issue = "wrong_mask_size"
            elif not set(unique_values).issubset({0, 255}):
                issue = "mask_not_binary"

        validation_rows.append(
            {
                "case_id": row["case_id"],
                "painting_id": row["painting_id"],
                "mask_type": row["mask_type"],
                "mask_path": str(mask_path),
                "file_exists": file_exists,
                "readable": readable,
                "width": width,
                "height": height,
                "mode": mode,
                "unique_values": unique_values,
                "issue": issue,
            }
        )

    return pd.DataFrame(validation_rows)