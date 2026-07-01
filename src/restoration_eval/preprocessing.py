"""Image preprocessing utilities for the painting restoration evaluation project."""

from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image


def compute_median_rgb(image: Image.Image) -> tuple[int, int, int]:
    """Return the median RGB color of an image.

    The median color is used as deterministic padding so padded areas are less
    visually harsh than pure black or white.
    """
    rgb_image = image.convert("RGB")
    pixels = np.asarray(rgb_image)

    median_rgb = np.median(pixels.reshape(-1, 3), axis=0)
    return tuple(int(round(value)) for value in median_rgb)


def resize_with_aspect_ratio_and_pad(
    image: Image.Image,
    target_size: int = 768,
    padding_color: tuple[int, int, int] | None = None,
) -> tuple[Image.Image, dict]:
    """Resize an image while preserving aspect ratio, then pad to a square.

    No painting content is cropped or geometrically distorted. The returned
    metadata records where the actual painting content sits inside the padded
    square so later masks and metrics can avoid treating padding as artwork.
    """
    image = image.convert("RGB")
    original_width, original_height = image.size

    if original_width <= 0 or original_height <= 0:
        raise ValueError(f"Invalid image size: {original_width}x{original_height}")

    scale = target_size / max(original_width, original_height)
    resized_width = max(1, round(original_width * scale))
    resized_height = max(1, round(original_height * scale))

    resized = image.resize((resized_width, resized_height), Image.Resampling.LANCZOS)

    if padding_color is None:
        padding_color = compute_median_rgb(image)

    pad_left = (target_size - resized_width) // 2
    pad_top = (target_size - resized_height) // 2
    pad_right = target_size - resized_width - pad_left
    pad_bottom = target_size - resized_height - pad_top

    canvas = Image.new("RGB", (target_size, target_size), padding_color)
    canvas.paste(resized, (pad_left, pad_top))

    content_x_min = pad_left
    content_y_min = pad_top
    content_x_max = pad_left + resized_width
    content_y_max = pad_top + resized_height

    preprocessing_metadata = {
        "original_width": original_width,
        "original_height": original_height,
        "target_size": target_size,
        "resize_scale": scale,
        "resized_width": resized_width,
        "resized_height": resized_height,
        "pad_left": pad_left,
        "pad_top": pad_top,
        "pad_right": pad_right,
        "pad_bottom": pad_bottom,
        "padding_color_r": padding_color[0],
        "padding_color_g": padding_color[1],
        "padding_color_b": padding_color[2],
        "content_x_min": content_x_min,
        "content_y_min": content_y_min,
        "content_x_max": content_x_max,
        "content_y_max": content_y_max,
        "content_width": resized_width,
        "content_height": resized_height,
        "preprocessing_method": "aspect_ratio_resize_median_rgb_pad",
    }

    return canvas, preprocessing_metadata


def preprocess_images(
    metadata: pd.DataFrame,
    raw_images_dir: Path,
    clean_output_dir: Path,
    target_size: int = 768,
) -> pd.DataFrame:
    """Create standardized clean images for every metadata row.

    Each raw painting is resized while preserving aspect ratio and padded to a
    fixed square size. The processed image is saved as PNG, and the returned
    dataframe records preprocessing metadata including the actual content region.
    """
    clean_output_dir.mkdir(parents=True, exist_ok=True)
    records = []

    for _, row in metadata.iterrows():
        painting_id = row["painting_id"]
        raw_filename = row["filename"]
        input_path = raw_images_dir / raw_filename

        output_filename = f"{painting_id}_clean.png"
        output_path = clean_output_dir / output_filename

        with Image.open(input_path) as img:
            processed_img, preprocessing_metadata = resize_with_aspect_ratio_and_pad(
                img,
                target_size=target_size,
            )
            processed_img.save(output_path)
            
        records.append(
            {
                "painting_id": painting_id,
                "raw_filename": raw_filename,
                "raw_image_path": str(input_path),
                "processed_filename": output_filename,
                "processed_path": str(output_path),
                "processed_width": target_size,
                "processed_height": target_size,
                **preprocessing_metadata,
            }
        )
    return pd.DataFrame(records)

def build_processed_metadata(metadata: pd.DataFrame, processed_df: pd.DataFrame) -> pd.DataFrame:
    """Merge raw metadata with processed-image metadata columns.

    Columns already present in the raw metadata are kept from the raw metadata
    side to avoid pandas suffixes such as ``original_width_x`` and
    ``original_width_y``.
    """
    duplicate_columns = [
        col for col in processed_df.columns
        if col in metadata.columns and col != "painting_id"
    ]
    processed_for_merge = processed_df.drop(columns=duplicate_columns)

    return metadata.merge(
        processed_for_merge,
        on="painting_id",
        how="left",
    )