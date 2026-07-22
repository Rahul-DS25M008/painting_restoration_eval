"""Image preprocessing utilities for the painting restoration evaluation project."""

from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, UnidentifiedImageError


REQUIRED_METADATA_COLUMNS = {
    "painting_id",
    "filename",
}


def compute_median_rgb(
    image: Image.Image,
) -> tuple[int, int, int]:
    """Return the rounded median RGB colour of an image."""
    rgb_image = image.convert("RGB")
    pixels = np.asarray(rgb_image)

    if pixels.size == 0:
        raise ValueError("Cannot compute a median colour from an empty image.")

    median_rgb = np.median(
        pixels.reshape(-1, 3),
        axis=0,
    )

    return tuple(
        int(round(value))
        for value in median_rgb
    )


def resize_with_aspect_ratio_and_pad(
    image: Image.Image,
    target_size: int = 768,
    padding_color: tuple[int, int, int] | None = None,
) -> tuple[Image.Image, dict]:
    """Resize an image while preserving aspect ratio and pad it to a square.

    No painting content is cropped or geometrically distorted. The returned
    metadata records the content region inside the padded square so later
    masks and metrics can exclude padding.
    """
    if not isinstance(target_size, int) or target_size <= 0:
        raise ValueError(
            f"target_size must be a positive integer, received: {target_size!r}"
        )

    image = image.convert("RGB")
    original_width, original_height = image.size

    if original_width <= 0 or original_height <= 0:
        raise ValueError(
            "Invalid source image dimensions: "
            f"{original_width}x{original_height}"
        )

    scale = target_size / max(
        original_width,
        original_height,
    )

    resized_width = max(
        1,
        round(original_width * scale),
    )
    resized_height = max(
        1,
        round(original_height * scale),
    )

    resized_image = image.resize(
        (resized_width, resized_height),
        Image.Resampling.LANCZOS,
    )

    if padding_color is None:
        padding_color = compute_median_rgb(image)

    if (
        len(padding_color) != 3
        or any(
            not isinstance(value, int)
            or value < 0
            or value > 255
            for value in padding_color
        )
    ):
        raise ValueError(
            "padding_color must contain three integer RGB values "
            f"between 0 and 255, received: {padding_color!r}"
        )

    pad_left = (
        target_size - resized_width
    ) // 2

    pad_top = (
        target_size - resized_height
    ) // 2

    pad_right = (
        target_size
        - resized_width
        - pad_left
    )

    pad_bottom = (
        target_size
        - resized_height
        - pad_top
    )

    canvas = Image.new(
        "RGB",
        (target_size, target_size),
        padding_color,
    )

    canvas.paste(
        resized_image,
        (pad_left, pad_top),
    )

    content_x_min = pad_left
    content_y_min = pad_top
    content_x_max = (
        pad_left + resized_width
    )
    content_y_max = (
        pad_top + resized_height
    )

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
        "preprocessing_method": (
            "aspect_ratio_resize_median_rgb_pad"
        ),
    }

    return canvas, preprocessing_metadata


def _project_relative_path(
    path: Path,
    project_root: Path,
) -> str:
    """Return a portable POSIX-style path relative to the project root."""
    resolved_path = path.resolve()
    resolved_root = project_root.resolve()

    try:
        relative_path = resolved_path.relative_to(
            resolved_root
        )
    except ValueError as exc:
        raise ValueError(
            f"Path is outside the project root: {resolved_path}"
        ) from exc

    return relative_path.as_posix()


def preprocess_images(
    metadata: pd.DataFrame,
    raw_images_dir: Path,
    clean_output_dir: Path,
    target_size: int = 768,
    project_root: Path | None = None,
) -> pd.DataFrame:
    """Create standardized clean images for every metadata row.

    Each painting is resized while preserving aspect ratio and padded to a
    fixed square size. Processed images are saved as PNG files.

    Stored paths are project-relative when ``project_root`` is supplied.
    """
    missing_columns = sorted(
        REQUIRED_METADATA_COLUMNS
        - set(metadata.columns)
    )

    if missing_columns:
        raise ValueError(
            "Metadata is missing required preprocessing columns: "
            f"{missing_columns}"
        )

    if metadata.empty:
        raise ValueError(
            "Metadata is empty. No images are available for preprocessing."
        )

    if metadata["painting_id"].isna().any():
        raise ValueError(
            "Metadata contains null painting_id values."
        )

    if metadata["filename"].isna().any():
        raise ValueError(
            "Metadata contains null filename values."
        )

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

    if duplicate_ids:
        raise ValueError(
            "Duplicate painting_id values found: "
            f"{sorted(set(duplicate_ids))}"
        )

    if not isinstance(target_size, int) or target_size <= 0:
        raise ValueError(
            f"target_size must be a positive integer, received: {target_size!r}"
        )

    raw_images_dir = Path(raw_images_dir)
    clean_output_dir = Path(clean_output_dir)

    if not raw_images_dir.exists():
        raise FileNotFoundError(
            f"Raw image directory not found: {raw_images_dir}"
        )

    clean_output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    if project_root is not None:
        project_root = Path(project_root).resolve()

    records = []

    ordered_metadata = metadata.sort_values(
        "painting_id",
        kind="stable",
    )

    for row in ordered_metadata.itertuples(
        index=False
    ):
        painting_id = str(row.painting_id).strip()
        raw_filename = str(row.filename).strip()

        if not painting_id:
            raise ValueError(
                "Metadata contains a blank painting_id."
            )

        if not raw_filename:
            raise ValueError(
                f"Painting {painting_id} has a blank filename."
            )

        input_path = (
            raw_images_dir
            / raw_filename
        )

        if not input_path.is_file():
            raise FileNotFoundError(
                "Raw image not found for "
                f"{painting_id}: {input_path}"
            )

        output_filename = (
            f"{painting_id}_clean.png"
        )

        output_path = (
            clean_output_dir
            / output_filename
        )

        try:
            with Image.open(input_path) as source_image:
                source_image.load()

                processed_image, preprocessing_metadata = (
                    resize_with_aspect_ratio_and_pad(
                        source_image,
                        target_size=target_size,
                    )
                )

        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
        ) as exc:
            raise ValueError(
                "Failed to preprocess "
                f"{painting_id} from {input_path}: {exc}"
            ) from exc

        processed_image.save(
            output_path,
            format="PNG",
            optimize=False,
            compress_level=6,
        )

        if project_root is None:
            raw_image_path_value = str(
                input_path.resolve()
            )
            processed_path_value = str(
                output_path.resolve()
            )
        else:
            raw_image_path_value = (
                _project_relative_path(
                    input_path,
                    project_root,
                )
            )
            processed_path_value = (
                _project_relative_path(
                    output_path,
                    project_root,
                )
            )

        records.append(
            {
                "painting_id": painting_id,
                "raw_filename": raw_filename,
                "raw_image_path": raw_image_path_value,
                "processed_filename": output_filename,
                "processed_path": processed_path_value,
                "processed_width": target_size,
                "processed_height": target_size,
                **preprocessing_metadata,
            }
        )

    processed_df = pd.DataFrame(records)

    expected_count = len(metadata)

    if len(processed_df) != expected_count:
        raise RuntimeError(
            "Preprocessing row-count mismatch: "
            f"expected {expected_count}, produced {len(processed_df)}"
        )

    return processed_df


def build_processed_metadata(
    metadata: pd.DataFrame,
    processed_df: pd.DataFrame,
) -> pd.DataFrame:
    """Merge source metadata with processed-image metadata."""
    if "painting_id" not in metadata.columns:
        raise ValueError(
            "Source metadata is missing painting_id."
        )

    if "painting_id" not in processed_df.columns:
        raise ValueError(
            "Processed metadata is missing painting_id."
        )

    if metadata["painting_id"].duplicated().any():
        raise ValueError(
            "Source metadata contains duplicate painting_id values."
        )

    if processed_df["painting_id"].duplicated().any():
        raise ValueError(
            "Processed metadata contains duplicate painting_id values."
        )

    duplicate_columns = [
        column
        for column in processed_df.columns
        if (
            column in metadata.columns
            and column != "painting_id"
        )
    ]

    processed_for_merge = processed_df.drop(
        columns=duplicate_columns
    )

    merged_df = metadata.merge(
        processed_for_merge,
        on="painting_id",
        how="left",
        validate="one_to_one",
    )

    missing_processed_rows = int(
        merged_df["processed_filename"]
        .isna()
        .sum()
    )

    if missing_processed_rows:
        raise ValueError(
            "Processed metadata merge left "
            f"{missing_processed_rows} paintings without processed outputs."
        )

    return merged_df