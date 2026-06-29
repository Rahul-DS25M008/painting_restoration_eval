"""OpenCV restoration baselines."""
from pathlib import Path

import cv2
import pandas as pd
from PIL import Image


def restore_with_opencv_telea(
    masked_image_path: Path,
    mask_path: Path,
    radius: int = 3,
) -> Image.Image:
    """Restore a masked image using OpenCV Telea inpainting.

    OpenCV expects the image in BGR format and a single-channel mask where
    white pixels indicate the region to inpaint.
    """
    masked_bgr = cv2.imread(str(masked_image_path), cv2.IMREAD_COLOR)
    mask_gray = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

    if masked_bgr is None:
        raise FileNotFoundError(f"Could not read masked image: {masked_image_path}")
    if mask_gray is None:
        raise FileNotFoundError(f"Could not read mask: {mask_path}")

    _, mask_binary = cv2.threshold(mask_gray, 127, 255, cv2.THRESH_BINARY)

    restored_bgr = cv2.inpaint(
        masked_bgr,
        mask_binary,
        inpaintRadius=radius,
        flags=cv2.INPAINT_TELEA,
    )

    restored_rgb = cv2.cvtColor(restored_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(restored_rgb)


def run_opencv_telea_restoration(
    mask_metadata: pd.DataFrame,
    mask_dir: Path,
    masked_dir: Path,
    restored_dir: Path,
    model_name: str = "opencv_telea",
    radius: int = 3,
) -> pd.DataFrame:
    """Run OpenCV Telea restoration for every row in mask metadata."""
    restored_dir.mkdir(parents=True, exist_ok=True)
    records = []

    for _, row in mask_metadata.iterrows():
        painting_id = row["painting_id"]
        mask_type = row["mask_type"]

        masked_path = masked_dir / row["masked_filename"]
        mask_path = mask_dir / row["mask_filename"]
        restored_filename = f"{painting_id}_{mask_type}_restored_{model_name}.png"
        restored_path = restored_dir / restored_filename

        restored_img = restore_with_opencv_telea(masked_path, mask_path, radius=radius)
        restored_img.save(restored_path)

        records.append(
            {
                "painting_id": painting_id,
                "mask_type": mask_type,
                "model_name": model_name,
                "inpaint_radius": radius,
                "clean_filename": row["clean_filename"],
                "mask_filename": row["mask_filename"],
                "masked_filename": row["masked_filename"],
                "restored_filename": restored_filename,
                "mask_area_ratio": row["mask_area_ratio"],
            }
        )

    return pd.DataFrame(records)
