from pathlib import Path
from typing import Iterable

import pandas as pd
from PIL import Image


REQUIRED_METADATA_COLUMNS = [
    "painting_id",
    "category",
    "title",
    "artist",
    "date",
    "style_or_period",
    "medium",
    "source",
    "source_url",
    "license",
    "filename",
]


def load_metadata(metadata_path: Path) -> pd.DataFrame:
    """Load metadata CSV and strip column whitespace."""
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    metadata = pd.read_csv(metadata_path)
    metadata.columns = metadata.columns.str.strip()
    return metadata


def validate_required_columns(
    metadata: pd.DataFrame,
    required_columns: Iterable[str] = REQUIRED_METADATA_COLUMNS,
) -> list[str]:
    """Return metadata columns that are required but missing."""
    return [column for column in required_columns if column not in metadata.columns]


def check_image_files(
    metadata: pd.DataFrame,
    images_dir: Path,
    filename_column: str = "filename",
    id_column: str = "painting_id",
) -> pd.DataFrame:
    """Check whether all image files referenced in metadata exist."""
    records = []

    for _, row in metadata.iterrows():
        image_path = images_dir / row[filename_column]
        records.append(
            {
                id_column: row[id_column],
                filename_column: row[filename_column],
                "image_path": str(image_path),
                "exists": image_path.exists(),
            }
        )

    return pd.DataFrame(records)


def collect_image_info(
    metadata: pd.DataFrame,
    images_dir: Path,
    filename_column: str = "filename",
    id_column: str = "painting_id",
) -> pd.DataFrame:
    """Collect width, height, mode, and format for images listed in metadata."""
    records = []

    for _, row in metadata.iterrows():
        image_path = images_dir / row[filename_column]

        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        with Image.open(image_path) as image:
            records.append(
                {
                    id_column: row[id_column],
                    filename_column: row[filename_column],
                    "width": image.width,
                    "height": image.height,
                    "mode": image.mode,
                    "format": image.format,
                }
            )

    return pd.DataFrame(records)
