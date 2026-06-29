"""LPIPS metric utilities for painting restoration evaluation.

This module computes full-image LPIPS and local crop-based LPIPS for restored
painting images. Lower LPIPS means higher perceptual similarity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from PIL import Image

import torch
import torchvision.transforms as T


CropBox = Tuple[int, int, int, int]


def get_device(prefer_cuda: bool = True) -> torch.device:
    """Return CUDA device if available and requested, otherwise CPU."""
    if prefer_cuda and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def load_lpips_model(net: str = "alex", device: Optional[torch.device] = None):
    """Load an LPIPS model.

    Importing lpips inside the function keeps the rest of the package importable
    even if lpips is not installed yet.
    """
    import lpips

    if device is None:
        device = get_device()

    model = lpips.LPIPS(net=net).to(device)
    model.eval()
    return model


def pil_to_lpips_tensor(img: Image.Image, device: torch.device) -> torch.Tensor:
    """Convert a PIL image into an LPIPS tensor in [-1, 1].

    LPIPS expects shape [1, 3, H, W].
    """
    transform = T.Compose(
        [
            T.ToTensor(),
            T.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
        ]
    )
    return transform(img.convert("RGB")).unsqueeze(0).to(device)


def compute_lpips(
    img_a: Image.Image,
    img_b: Image.Image,
    lpips_model,
    device: torch.device,
) -> float:
    """Compute LPIPS distance between two PIL images. Lower is better."""
    tensor_a = pil_to_lpips_tensor(img_a, device)
    tensor_b = pil_to_lpips_tensor(img_b, device)

    with torch.no_grad():
        value = lpips_model(tensor_a, tensor_b)

    return float(value.item())


def load_mask_bool(mask_path: Path) -> np.ndarray:
    """Load a binary mask. White/non-zero pixels are treated as damaged."""
    mask = Image.open(mask_path).convert("L")
    return np.array(mask) > 0


def get_mask_bbox(mask_bool: np.ndarray, padding: int = 32) -> CropBox:
    """Return padded bounding box around positive mask pixels.

    Returns:
        (left, upper, right, lower)
    """
    ys, xs = np.where(mask_bool)

    if len(xs) == 0 or len(ys) == 0:
        raise ValueError("Mask has no positive pixels.")

    height, width = mask_bool.shape

    left = max(int(xs.min()) - padding, 0)
    right = min(int(xs.max()) + padding + 1, width)
    upper = max(int(ys.min()) - padding, 0)
    lower = min(int(ys.max()) + padding + 1, height)

    return left, upper, right, lower


def make_square_crop_box(box: CropBox, image_size: int | Tuple[int, int]) -> CropBox:
    """Expand a crop box to a square while staying inside image bounds."""
    left, upper, right, lower = box

    if isinstance(image_size, int):
        width = height = image_size
    else:
        width, height = image_size

    crop_width = right - left
    crop_height = lower - upper
    side = max(crop_width, crop_height)

    cx = (left + right) // 2
    cy = (upper + lower) // 2

    new_left = cx - side // 2
    new_upper = cy - side // 2
    new_right = new_left + side
    new_lower = new_upper + side

    if new_left < 0:
        new_right -= new_left
        new_left = 0

    if new_upper < 0:
        new_lower -= new_upper
        new_upper = 0

    if new_right > width:
        shift = new_right - width
        new_left -= shift
        new_right = width

    if new_lower > height:
        shift = new_lower - height
        new_upper -= shift
        new_lower = height

    new_left = max(new_left, 0)
    new_upper = max(new_upper, 0)

    return int(new_left), int(new_upper), int(new_right), int(new_lower)


def _ensure_filename_columns(restoration_metadata: pd.DataFrame) -> pd.DataFrame:
    """Ensure expected image filename columns exist using pilot naming convention."""
    df = restoration_metadata.copy()

    if "clean_filename" not in df.columns:
        df["clean_filename"] = df["painting_id"].astype(str) + "_clean.png"

    if "mask_filename" not in df.columns:
        df["mask_filename"] = (
            df["painting_id"].astype(str) + "_" + df["mask_type"].astype(str) + "_mask.png"
        )

    if "restored_filename" not in df.columns:
        df["restored_filename"] = (
            df["painting_id"].astype(str)
            + "_"
            + df["mask_type"].astype(str)
            + "_restored_"
            + df["model_name"].astype(str)
            + ".png"
        )

    return df


def compute_lpips_for_restorations(
    restoration_metadata: pd.DataFrame,
    clean_dir: Path,
    mask_dir: Path,
    restored_dir: Path,
    lpips_model,
    device: torch.device,
    crop_padding: int = 48,
    crop_resize: int = 256,
) -> pd.DataFrame:
    """Compute full-image and crop-based LPIPS for all restoration rows."""
    restoration_metadata = _ensure_filename_columns(restoration_metadata)

    records: list[dict] = []

    for _, row in restoration_metadata.iterrows():
        painting_id = row["painting_id"]
        mask_type = row["mask_type"]
        model_name = row["model_name"]

        clean_path = clean_dir / row["clean_filename"]
        mask_path = mask_dir / row["mask_filename"]
        restored_path = restored_dir / row["restored_filename"]

        clean_img = Image.open(clean_path).convert("RGB")
        restored_img = Image.open(restored_path).convert("RGB")
        mask_bool = load_mask_bool(mask_path)

        lpips_full = compute_lpips(clean_img, restored_img, lpips_model, device)

        bbox = get_mask_bbox(mask_bool, padding=crop_padding)
        square_bbox = make_square_crop_box(bbox, image_size=clean_img.size)

        clean_crop = clean_img.crop(square_bbox)
        restored_crop = restored_img.crop(square_bbox)

        clean_crop_resized = clean_crop.resize((crop_resize, crop_resize), Image.Resampling.LANCZOS)
        restored_crop_resized = restored_crop.resize((crop_resize, crop_resize), Image.Resampling.LANCZOS)

        lpips_mask_crop = compute_lpips(
            clean_crop_resized,
            restored_crop_resized,
            lpips_model,
            device,
        )

        records.append(
            {
                "painting_id": painting_id,
                "mask_type": mask_type,
                "model_name": model_name,
                "lpips_full": lpips_full,
                "lpips_mask_crop": lpips_mask_crop,
                "crop_left": square_bbox[0],
                "crop_upper": square_bbox[1],
                "crop_right": square_bbox[2],
                "crop_lower": square_bbox[3],
            }
        )

    return pd.DataFrame(records)


def merge_lpips_with_classical_metrics(
    classical_metrics: pd.DataFrame,
    lpips_df: pd.DataFrame,
) -> pd.DataFrame:
    """Merge LPIPS metrics into the classical metrics table."""
    lpips_columns = [
        "painting_id",
        "mask_type",
        "model_name",
        "lpips_full",
        "lpips_mask_crop",
        "crop_left",
        "crop_upper",
        "crop_right",
        "crop_lower",
    ]

    return classical_metrics.merge(
        lpips_df[lpips_columns],
        on=["painting_id", "mask_type", "model_name"],
        how="left",
    )


def summarize_lpips_by_mask_type(metrics_with_lpips: pd.DataFrame) -> pd.DataFrame:
    """Summarize classical and LPIPS metrics by mask type."""
    return (
        metrics_with_lpips.groupby("mask_type")
        .agg(
            cases=("painting_id", "count"),
            mean_mask_mae=("mask_mae", "mean"),
            mean_mask_psnr=("mask_psnr", "mean"),
            mean_full_ssim=("ssim", "mean"),
            mean_lpips_full=("lpips_full", "mean"),
            mean_lpips_mask_crop=("lpips_mask_crop", "mean"),
        )
        .reset_index()
        .sort_values("mean_lpips_mask_crop", ascending=True)
    )


def rank_worst_lpips_cases(metrics_with_lpips: pd.DataFrame) -> pd.DataFrame:
    """Return cases ranked from worst to best by crop-based LPIPS."""
    columns = [
        "painting_id",
        "mask_type",
        "model_name",
        "mask_mae",
        "mask_psnr",
        "ssim",
        "lpips_full",
        "lpips_mask_crop",
    ]

    return metrics_with_lpips.sort_values("lpips_mask_crop", ascending=False)[columns]
