"""Image preprocessing utilities for the painting restoration evaluation project."""
from pathlib import Path
from typing import Iterable

import pandas as pd
from PIL import Image


def resize_center_crop(image: Image.Image, target_size: int = 768) -> Image.Image:
    """Resize an image and center-crop it to a square.

    The image is resized so that the shortest side reaches ``target_size``.
    The center ``target_size`` × ``target_size`` crop is then returned.
    """
    image = image.convert("RGB")
    width, height = image.size

    scale = target_size / min(width, height)
    new_width = round(width * scale)
    new_height = round(height * scale)

    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    left = (new_width - target_size) // 2
    top = (new_height - target_size) // 2
    right = left + target_size
    bottom = top + target_size

    return resized.crop((left, top, right, bottom))


def preprocess_images(
    metadata: pd.DataFrame,
    raw_images_dir: Path,
    clean_output_dir: Path,
    target_size: int = 768,
) -> pd.DataFrame:
    """Create standardized clean images for every metadata row.

    Returns a dataframe describing generated clean images.
    """
    clean_output_dir.mkdir(parents=True, exist_ok=True)
    records = []

    for _, row in metadata.iterrows():
        painting_id = row["painting_id"]
        input_path = raw_images_dir / row["filename"]
        output_filename = f"{painting_id}_clean.png"
        output_path = clean_output_dir / output_filename

        with Image.open(input_path) as img:
            processed_img = resize_center_crop(img, target_size=target_size)
            processed_img.save(output_path)

        records.append(
            {
                "painting_id": painting_id,
                "raw_filename": row["filename"],
                "processed_filename": output_filename,
                "processed_width": target_size,
                "processed_height": target_size,
                "processed_path": str(output_path),
            }
        )

    return pd.DataFrame(records)


def build_processed_metadata(metadata: pd.DataFrame, processed_df: pd.DataFrame) -> pd.DataFrame:
    """Merge raw metadata with processed-image filename and size columns."""
    return metadata.merge(
        processed_df[["painting_id", "processed_filename", "processed_width", "processed_height"]],
        on="painting_id",
        how="left",
    )
