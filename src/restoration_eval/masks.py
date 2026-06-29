"""Synthetic damage mask generation utilities."""
from pathlib import Path
import random
from typing import Callable, Dict, Tuple

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFilter


def set_random_seed(seed: int) -> None:
    """Set Python and NumPy random seeds for reproducible mask generation."""
    random.seed(seed)
    np.random.seed(seed)


def create_irregular_blob_mask(
    size: int = 768,
    center=None,
    radius_range: Tuple[int, int] = (40, 100),
    num_points: int = 12,
    blur_radius: float = 2,
) -> Image.Image:
    """Create an irregular filled white blob on a black background.

    White pixels indicate damaged/missing area.
    """
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)

    if center is None:
        cx = random.randint(size // 4, 3 * size // 4)
        cy = random.randint(size // 4, 3 * size // 4)
    else:
        cx, cy = center

    points = []
    for i in range(num_points):
        angle = 2 * np.pi * i / num_points
        radius = random.randint(radius_range[0], radius_range[1])
        x = cx + int(radius * np.cos(angle))
        y = cy + int(radius * np.sin(angle))
        x = max(0, min(size - 1, x))
        y = max(0, min(size - 1, y))
        points.append((x, y))

    draw.polygon(points, fill=255)

    if blur_radius > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        mask = mask.point(lambda p: 255 if p > 80 else 0)

    return mask


def create_scratch_line_mask(
    size: int = 768,
    num_lines: int = 8,
    width_range: Tuple[int, int] = (3, 10),
    length_range: Tuple[int, int] = (150, 450),
) -> Image.Image:
    """Create scratch/crack-like thin white lines on a black background."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)

    for _ in range(num_lines):
        x1 = random.randint(0, size - 1)
        y1 = random.randint(0, size - 1)
        angle = random.uniform(0, 2 * np.pi)
        length = random.randint(length_range[0], length_range[1])

        x2 = int(x1 + length * np.cos(angle))
        y2 = int(y1 + length * np.sin(angle))
        x2 = max(0, min(size - 1, x2))
        y2 = max(0, min(size - 1, y2))

        width = random.randint(width_range[0], width_range[1])
        mid_x = (x1 + x2) // 2 + random.randint(-40, 40)
        mid_y = (y1 + y2) // 2 + random.randint(-40, 40)

        draw.line([(x1, y1), (mid_x, mid_y), (x2, y2)], fill=255, width=width)

    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.6))
    return mask.point(lambda p: 255 if p > 40 else 0)


def create_large_irregular_mask(size: int = 768) -> Image.Image:
    """Create a larger irregular missing-area mask."""
    return create_irregular_blob_mask(
        size=size,
        radius_range=(100, 190),
        num_points=18,
        blur_radius=3,
    )


def apply_mask_to_image(
    image: Image.Image,
    mask: Image.Image,
    fill_color: Tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Replace white mask pixels in an RGB image with ``fill_color``."""
    image = image.convert("RGB")
    mask = mask.convert("L")

    image_arr = np.array(image).copy()
    mask_arr = np.array(mask)
    image_arr[mask_arr > 0] = fill_color

    return Image.fromarray(image_arr)


def default_mask_generators(target_size: int = 768) -> Dict[str, Callable[[], Image.Image]]:
    """Return the pilot mask generators used in the OpenCV pilot."""
    return {
        "irregular_small": lambda: create_irregular_blob_mask(
            size=target_size,
            radius_range=(45, 95),
            num_points=14,
            blur_radius=2,
        ),
        "scratch_lines": lambda: create_scratch_line_mask(
            size=target_size,
            num_lines=9,
            width_range=(3, 8),
            length_range=(120, 420),
        ),
        "irregular_large": lambda: create_large_irregular_mask(size=target_size),
    }


def generate_masks_and_masked_images(
    metadata: pd.DataFrame,
    clean_dir: Path,
    mask_dir: Path,
    masked_dir: Path,
    target_size: int = 768,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Generate pilot masks and corresponding white-filled masked images."""
    set_random_seed(random_seed)
    mask_dir.mkdir(parents=True, exist_ok=True)
    masked_dir.mkdir(parents=True, exist_ok=True)

    records = []
    generators = default_mask_generators(target_size=target_size)

    for _, row in metadata.iterrows():
        painting_id = row["painting_id"]
        clean_filename = row["processed_filename"]
        clean_path = clean_dir / clean_filename
        clean_img = Image.open(clean_path).convert("RGB")

        for mask_type, generator in generators.items():
            mask = generator()
            mask_filename = f"{painting_id}_{mask_type}_mask.png"
            masked_filename = f"{painting_id}_{mask_type}_masked.png"

            mask_path = mask_dir / mask_filename
            masked_path = masked_dir / masked_filename

            masked_img = apply_mask_to_image(clean_img, mask, fill_color=(255, 255, 255))

            mask.save(mask_path)
            masked_img.save(masked_path)

            mask_area_ratio = np.mean(np.array(mask) > 0)
            records.append(
                {
                    "painting_id": painting_id,
                    "mask_type": mask_type,
                    "clean_filename": clean_filename,
                    "mask_filename": mask_filename,
                    "masked_filename": masked_filename,
                    "mask_area_ratio": round(float(mask_area_ratio), 4),
                    "mask_seed": random_seed,
                }
            )

    return pd.DataFrame(records)
