"""
Utilities for generating restoration difference maps and comparison grids.

These functions compare clean paintings with restored outputs and save visual
diagnostics that localize reconstruction errors.
"""

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from PIL import Image
import matplotlib.pyplot as plt


def load_rgb_array(path: Path) -> np.ndarray:
    """Load an RGB image as a float32 NumPy array."""
    return np.array(Image.open(path).convert("RGB")).astype(np.float32)


def load_mask_bool(path: Path) -> np.ndarray:
    """Load a mask image as a boolean array where True means damaged/missing."""
    mask = np.array(Image.open(path).convert("L"))
    return mask > 0


def compute_abs_difference(clean_arr: np.ndarray, restored_arr: np.ndarray) -> np.ndarray:
    """
    Compute per-pixel mean absolute RGB difference.

    Parameters
    ----------
    clean_arr:
        Clean reference image as H x W x 3 array.
    restored_arr:
        Restored image as H x W x 3 array.

    Returns
    -------
    np.ndarray
        H x W array containing mean absolute RGB error per pixel.
    """
    if clean_arr.shape != restored_arr.shape:
        raise ValueError(
            f"Image shapes do not match: clean={clean_arr.shape}, restored={restored_arr.shape}"
        )

    return np.mean(np.abs(clean_arr - restored_arr), axis=2)


def normalize_for_display(arr: np.ndarray) -> np.ndarray:
    """
    Normalize an array to [0, 1] for image display.

    This is local normalization, meaning each map is scaled independently.
    It is useful for seeing where errors occur inside one case, but it should
    not be used for strict visual comparison across cases.
    """
    max_val = float(np.max(arr))
    if max_val == 0:
        return np.zeros_like(arr, dtype=np.float32)

    return (arr / max_val).astype(np.float32)


def save_grayscale_map(arr: np.ndarray, output_path: Path) -> None:
    """Save a 2D array as an 8-bit grayscale PNG after local normalization."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray((normalize_for_display(arr) * 255).astype(np.uint8))
    img.save(output_path)


def create_difference_maps(
    restoration_metadata: pd.DataFrame,
    clean_dir: Path,
    mask_dir: Path,
    restored_dir: Path,
    diff_map_dir: Path,
) -> pd.DataFrame:
    """
    Generate full and masked-only difference maps for every restoration case.

    Returns a metadata dataframe with filenames and summary difference values.
    """
    diff_map_dir.mkdir(parents=True, exist_ok=True)

    diff_records = []

    for _, row in restoration_metadata.iterrows():
        painting_id = row["painting_id"]
        mask_type = row["mask_type"]
        model_name = row["model_name"]

        clean_path = clean_dir / row["clean_filename"]
        mask_path = mask_dir / row["mask_filename"]
        restored_path = restored_dir / row["restored_filename"]

        clean_arr = load_rgb_array(clean_path)
        restored_arr = load_rgb_array(restored_path)
        mask_bool = load_mask_bool(mask_path)

        diff = compute_abs_difference(clean_arr, restored_arr)

        diff_masked_only = np.zeros_like(diff)
        diff_masked_only[mask_bool] = diff[mask_bool]

        diff_filename = f"{painting_id}_{mask_type}_{model_name}_diff.png"
        diff_masked_filename = f"{painting_id}_{mask_type}_{model_name}_diff_masked_only.png"

        save_grayscale_map(diff, diff_map_dir / diff_filename)
        save_grayscale_map(diff_masked_only, diff_map_dir / diff_masked_filename)

        if np.any(mask_bool):
            mean_abs_diff_masked = float(diff[mask_bool].mean())
        else:
            mean_abs_diff_masked = 0.0

        diff_records.append(
            {
                "painting_id": painting_id,
                "mask_type": mask_type,
                "model_name": model_name,
                "diff_filename": diff_filename,
                "diff_masked_filename": diff_masked_filename,
                "max_abs_diff": float(diff.max()),
                "mean_abs_diff_full": float(diff.mean()),
                "mean_abs_diff_masked": mean_abs_diff_masked,
            }
        )

    return pd.DataFrame(diff_records)


def create_comparison_grid(
    clean_path: Path,
    mask_path: Path,
    masked_path: Path,
    restored_path: Path,
    output_path: Path,
    title: str,
    show: bool = True,
) -> None:
    """
    Create one comparison grid:
    clean | mask | masked | restored | masked-region error map.
    """
    clean_arr = load_rgb_array(clean_path)
    restored_arr = load_rgb_array(restored_path)
    diff = compute_abs_difference(clean_arr, restored_arr)
    mask_bool = load_mask_bool(mask_path)

    diff_masked_only = np.zeros_like(diff)
    diff_masked_only[mask_bool] = diff[mask_bool]

    clean_img = Image.open(clean_path).convert("RGB")
    mask_img = Image.open(mask_path).convert("L")
    masked_img = Image.open(masked_path).convert("RGB")
    restored_img = Image.open(restored_path).convert("RGB")

    fig, axes = plt.subplots(1, 5, figsize=(18, 4))

    axes[0].imshow(clean_img)
    axes[0].set_title("Clean")
    axes[0].axis("off")

    axes[1].imshow(mask_img, cmap="gray")
    axes[1].set_title("Mask")
    axes[1].axis("off")

    axes[2].imshow(masked_img)
    axes[2].set_title("Masked")
    axes[2].axis("off")

    axes[3].imshow(restored_img)
    axes[3].set_title("Restored")
    axes[3].axis("off")

    axes[4].imshow(diff_masked_only, cmap="inferno")
    axes[4].set_title("Error map\nmasked region")
    axes[4].axis("off")

    fig.suptitle(title, fontsize=14)
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    plt.close(fig)


def create_comparison_grids(
    restoration_metadata: pd.DataFrame,
    clean_dir: Path,
    mask_dir: Path,
    masked_dir: Path,
    restored_dir: Path,
    grid_dir: Path,
    show: bool = True,
) -> None:
    """Create comparison grids for every restoration case."""
    grid_dir.mkdir(parents=True, exist_ok=True)

    for _, row in restoration_metadata.iterrows():
        painting_id = row["painting_id"]
        mask_type = row["mask_type"]
        model_name = row["model_name"]

        clean_path = clean_dir / row["clean_filename"]
        mask_path = mask_dir / row["mask_filename"]
        masked_path = masked_dir / row["masked_filename"]
        restored_path = restored_dir / row["restored_filename"]

        grid_filename = f"{painting_id}_{mask_type}_{model_name}_comparison_grid.png"
        grid_path = grid_dir / grid_filename

        create_comparison_grid(
            clean_path=clean_path,
            mask_path=mask_path,
            masked_path=masked_path,
            restored_path=restored_path,
            output_path=grid_path,
            title=f"{painting_id} | {mask_type} | {model_name}",
            show=show,
        )
