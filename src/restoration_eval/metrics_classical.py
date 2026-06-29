"""
Classical image restoration metrics for the painting restoration evaluation project.

This module computes full-image and masked-region metrics for restored images.
Mask convention: white/non-zero pixels indicate the damaged/restored region.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim


def load_rgb_array(path: Path) -> np.ndarray:
    """
    Load an image as an RGB float array in range [0, 255].

    Args:
        path: Path to an image file.

    Returns:
        RGB image array with dtype float32 and shape (H, W, 3).
    """
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    image = Image.open(path).convert("RGB")
    return np.array(image).astype(np.float32)


def load_mask_bool(path: Path) -> np.ndarray:
    """
    Load a binary mask as a boolean array.

    Mask convention:
        True = damaged/restored region
        False = valid unchanged region

    Args:
        path: Path to a mask image.

    Returns:
        Boolean mask array with shape (H, W).
    """
    if not path.exists():
        raise FileNotFoundError(f"Mask file not found: {path}")

    mask = Image.open(path).convert("L")
    mask_array = np.array(mask)
    return mask_array > 0


def compute_full_image_metrics(clean_arr: np.ndarray, restored_arr: np.ndarray) -> Dict[str, float]:
    """
    Compute full-image MAE, MSE, PSNR, and SSIM.

    Args:
        clean_arr: Ground-truth clean RGB image array.
        restored_arr: Restored RGB image array.

    Returns:
        Dictionary with mae, mse, psnr, and ssim.
    """
    if clean_arr.shape != restored_arr.shape:
        raise ValueError(
            f"Image shape mismatch. Clean: {clean_arr.shape}, restored: {restored_arr.shape}"
        )

    clean_uint8 = np.clip(clean_arr, 0, 255).astype(np.uint8)
    restored_uint8 = np.clip(restored_arr, 0, 255).astype(np.uint8)

    mae = np.mean(np.abs(clean_arr - restored_arr))
    mse = np.mean((clean_arr - restored_arr) ** 2)

    psnr_value = psnr(clean_uint8, restored_uint8, data_range=255)
    ssim_value = ssim(clean_uint8, restored_uint8, channel_axis=2, data_range=255)

    return {
        "mae": float(mae),
        "mse": float(mse),
        "psnr": float(psnr_value),
        "ssim": float(ssim_value),
    }


def compute_masked_region_metrics(
    clean_arr: np.ndarray,
    restored_arr: np.ndarray,
    mask_bool: np.ndarray,
) -> Dict[str, float]:
    """
    Compute MAE, MSE, and PSNR inside the masked region.

    SSIM is intentionally not computed directly on isolated masked pixels because SSIM
    requires local spatial structure.

    Args:
        clean_arr: Ground-truth clean RGB image array.
        restored_arr: Restored RGB image array.
        mask_bool: Boolean mask where True indicates damaged/restored pixels.

    Returns:
        Dictionary with mask_mae, mask_mse, and mask_psnr.
    """
    if clean_arr.shape != restored_arr.shape:
        raise ValueError(
            f"Image shape mismatch. Clean: {clean_arr.shape}, restored: {restored_arr.shape}"
        )

    if mask_bool.shape != clean_arr.shape[:2]:
        raise ValueError(
            f"Mask shape mismatch. Mask: {mask_bool.shape}, image: {clean_arr.shape[:2]}"
        )

    if not np.any(mask_bool):
        return {
            "mask_mae": 0.0,
            "mask_mse": 0.0,
            "mask_psnr": float("inf"),
        }

    clean_pixels = clean_arr[mask_bool]
    restored_pixels = restored_arr[mask_bool]

    mae = np.mean(np.abs(clean_pixels - restored_pixels))
    mse = np.mean((clean_pixels - restored_pixels) ** 2)

    if mse == 0:
        psnr_value = float("inf")
    else:
        psnr_value = 20 * np.log10(255.0 / np.sqrt(mse))

    return {
        "mask_mae": float(mae),
        "mask_mse": float(mse),
        "mask_psnr": float(psnr_value),
    }


def compute_classical_metrics_for_restorations(
    restoration_metadata: pd.DataFrame,
    clean_dir: Path,
    mask_dir: Path,
    restored_dir: Path,
) -> pd.DataFrame:
    """
    Compute full-image and masked-region classical metrics for restoration outputs.

    The metadata dataframe must contain:
        painting_id, mask_type, model_name, mask_area_ratio,
        clean_filename, mask_filename, restored_filename

    Args:
        restoration_metadata: DataFrame describing restoration outputs.
        clean_dir: Directory containing clean processed images.
        mask_dir: Directory containing binary masks.
        restored_dir: Directory containing restored images.

    Returns:
        DataFrame with one metric row per restoration case.
    """
    required_columns = {
        "painting_id",
        "mask_type",
        "model_name",
        "mask_area_ratio",
        "clean_filename",
        "mask_filename",
        "restored_filename",
    }
    missing_columns = required_columns - set(restoration_metadata.columns)
    if missing_columns:
        raise ValueError(f"Restoration metadata missing columns: {sorted(missing_columns)}")

    metric_records = []

    for _, row in restoration_metadata.iterrows():
        clean_path = clean_dir / row["clean_filename"]
        mask_path = mask_dir / row["mask_filename"]
        restored_path = restored_dir / row["restored_filename"]

        clean_arr = load_rgb_array(clean_path)
        restored_arr = load_rgb_array(restored_path)
        mask_bool = load_mask_bool(mask_path)

        full_metrics = compute_full_image_metrics(clean_arr, restored_arr)
        mask_metrics = compute_masked_region_metrics(clean_arr, restored_arr, mask_bool)

        metric_records.append(
            {
                "painting_id": row["painting_id"],
                "mask_type": row["mask_type"],
                "model_name": row["model_name"],
                "mask_area_ratio": row["mask_area_ratio"],
                **full_metrics,
                **mask_metrics,
            }
        )

    return pd.DataFrame(metric_records)


def summarize_metrics_by_mask_type(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize classical restoration metrics by mask type.

    Args:
        metrics_df: DataFrame generated by compute_classical_metrics_for_restorations.

    Returns:
        Aggregated metric summary by mask_type.
    """
    return (
        metrics_df.groupby("mask_type")
        .agg(
            cases=("painting_id", "count"),
            mean_mask_area_ratio=("mask_area_ratio", "mean"),
            mean_mae=("mae", "mean"),
            mean_psnr=("psnr", "mean"),
            mean_ssim=("ssim", "mean"),
            mean_mask_mae=("mask_mae", "mean"),
            mean_mask_mse=("mask_mse", "mean"),
            mean_mask_psnr=("mask_psnr", "mean"),
        )
        .reset_index()
        .sort_values("mean_mask_mae")
    )
