"""
LPIPS perceptual metric utilities for the painting restoration evaluation project.

This module computes LPIPS distances for damaged and restored images against
the clean reference image.

Lower LPIPS means higher perceptual similarity.

Evaluation regions:
- full_image
- content_region
- mask_bbox_crop

Sparse masked pixels are intentionally not used directly for LPIPS because
LPIPS expects image-like spatial inputs, not unordered masked pixels.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image

import torch
import torchvision.transforms as T


DEFAULT_LPIPS_NET = "alex"
DEFAULT_CROP_RESIZE = 256
DEFAULT_MASK_BBOX_MARGIN = 32


def get_device(prefer_cuda: bool = True) -> torch.device:
    """Return CUDA device if available and requested, otherwise CPU."""
    if prefer_cuda and torch.cuda.is_available():
        return torch.device("cuda")

    return torch.device("cpu")


def load_lpips_model(
    net: str = DEFAULT_LPIPS_NET,
    device: torch.device | None = None,
):
    """Load an LPIPS model.

    Importing lpips inside this function keeps the rest of the package importable
    even when lpips is not installed.
    """
    import lpips

    if device is None:
        device = get_device()

    model = lpips.LPIPS(net=net).to(device)
    model.eval()

    return model


def pil_to_lpips_tensor(
    image: Image.Image,
    device: torch.device,
) -> torch.Tensor:
    """Convert a PIL image to an LPIPS tensor in [-1, 1].

    LPIPS expects shape [1, 3, H, W].
    """
    transform = T.Compose(
        [
            T.ToTensor(),
            T.Normalize(
                mean=(0.5, 0.5, 0.5),
                std=(0.5, 0.5, 0.5),
            ),
        ]
    )

    return transform(image.convert("RGB")).unsqueeze(0).to(device)


def compute_lpips_distance(
    image_a: Image.Image,
    image_b: Image.Image,
    lpips_model,
    device: torch.device,
) -> float:
    """Compute LPIPS distance between two PIL images."""
    tensor_a = pil_to_lpips_tensor(image_a, device)
    tensor_b = pil_to_lpips_tensor(image_b, device)

    with torch.no_grad():
        value = lpips_model(tensor_a, tensor_b)

    return float(value.item())


def load_rgb_image(path: Path) -> Image.Image:
    """Load an image as RGB PIL image."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    with Image.open(path) as image:
        return image.convert("RGB")


def load_mask_bool(path: Path) -> np.ndarray:
    """Load a binary mask where True indicates the damaged/restored region."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Mask file not found: {path}")

    with Image.open(path) as image:
        mask_arr = np.asarray(image.convert("L"))

    return mask_arr > 0


def get_content_box_from_row(row: pd.Series) -> tuple[int, int, int, int]:
    """Get the preprocessing content box from metadata.

    Returns PIL crop box:
    (left, upper, right, lower)
    """
    required_columns = [
        "content_x_min",
        "content_y_min",
        "content_x_max",
        "content_y_max",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in row.index
    ]

    if missing_columns:
        raise ValueError(f"Missing content-region columns: {missing_columns}")

    left = int(row["content_x_min"])
    upper = int(row["content_y_min"])
    right = int(row["content_x_max"])
    lower = int(row["content_y_max"])

    if right <= left or lower <= upper:
        raise ValueError(
            f"Invalid content box: left={left}, upper={upper}, right={right}, lower={lower}"
        )

    return left, upper, right, lower


def get_mask_bbox(
    mask_bool: np.ndarray,
    margin: int = DEFAULT_MASK_BBOX_MARGIN,
) -> tuple[int, int, int, int] | None:
    """Return padded mask bounding box in PIL crop convention.

    Returns:
    (left, upper, right, lower)

    Returns None when the mask has no positive pixels.
    """
    ys, xs = np.where(mask_bool)

    if len(xs) == 0 or len(ys) == 0:
        return None

    height, width = mask_bool.shape

    left = max(0, int(xs.min()) - margin)
    right = min(width, int(xs.max()) + margin + 1)
    upper = max(0, int(ys.min()) - margin)
    lower = min(height, int(ys.max()) + margin + 1)

    if right <= left or lower <= upper:
        return None

    return left, upper, right, lower


def make_square_crop_box(
    box: tuple[int, int, int, int],
    image_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    """Expand a crop box to a square while staying inside image bounds.

    image_size is PIL convention: (width, height).
    """
    left, upper, right, lower = box
    width, height = image_size

    crop_width = right - left
    crop_height = lower - upper
    side = max(crop_width, crop_height)

    center_x = (left + right) // 2
    center_y = (upper + lower) // 2

    new_left = center_x - side // 2
    new_upper = center_y - side // 2
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

    new_left = max(0, new_left)
    new_upper = max(0, new_upper)

    if new_right <= new_left or new_lower <= new_upper:
        raise ValueError(
            f"Invalid square crop box: "
            f"left={new_left}, upper={new_upper}, right={new_right}, lower={new_lower}"
        )

    return int(new_left), int(new_upper), int(new_right), int(new_lower)


def resize_for_lpips(
    image: Image.Image,
    size: int = DEFAULT_CROP_RESIZE,
) -> Image.Image:
    """Resize an image region to a square LPIPS input size."""
    return image.convert("RGB").resize(
        (size, size),
        Image.Resampling.LANCZOS,
    )


def crop_image_region(
    image: Image.Image,
    box: tuple[int, int, int, int],
    resize_to: int = DEFAULT_CROP_RESIZE,
) -> Image.Image:
    """Crop an image region and resize it for LPIPS."""
    return resize_for_lpips(
        image.crop(box),
        size=resize_to,
    )


def _build_lpips_record(
    row: pd.Series,
    evaluation_region: str,
    damaged_lpips: float,
    restored_lpips: float,
    region_box: tuple[int, int, int, int],
    region_pixel_count: int,
    lpips_net: str,
    crop_resize: int,
    device_name: str,
    status: str = "ok",
    issue: str = "",
) -> dict[str, Any]:
    """Build one LPIPS metric record."""
    left, upper, right, lower = region_box

    return {
        "case_id": row["case_id"],
        "painting_id": row["painting_id"],
        "category": row.get("category", ""),
        "title": row.get("title", ""),
        "mask_id": row["mask_id"],
        "mask_type": row["mask_type"],
        "model_name": row["model_name"],
        "evaluation_region": evaluation_region,
        "region_pixel_count": int(region_pixel_count),
        "region_x_min": int(left),
        "region_y_min": int(upper),
        "region_x_max": int(right),
        "region_y_max": int(lower),
        "damaged_area_pixels": row.get("damaged_area_pixels", np.nan),
        "damaged_area_percentage_content": row.get("damaged_area_percentage_content", np.nan),
        "damaged_area_percentage_full": row.get("damaged_area_percentage_full", np.nan),
        "damaged_lpips": float(damaged_lpips),
        "restored_lpips": float(restored_lpips),
        "lpips_improvement": float(damaged_lpips - restored_lpips),
        "lpips_net": lpips_net,
        "crop_resize": int(crop_resize),
        "device": device_name,
        "status": status,
        "issue": issue,
    }


def compute_lpips_metrics_for_restorations(
    restoration_metadata: pd.DataFrame,
    lpips_model,
    device: torch.device,
    lpips_net: str = DEFAULT_LPIPS_NET,
    target_size: int = 768,
    mask_bbox_margin: int = DEFAULT_MASK_BBOX_MARGIN,
    crop_resize: int = DEFAULT_CROP_RESIZE,
    progress_every: int | None = 50,
) -> pd.DataFrame:
    """Compute LPIPS metrics for restoration outputs.

    Comparisons:
    - clean vs damaged
    - clean vs restored

    Evaluation regions:
    - full_image: all cases
    - content_region: all cases
    - mask_bbox_crop: non-zero mask cases only

    Expected rows for 50 paintings × 5 mask types:
    - 250 full_image
    - 250 content_region
    - 200 mask_bbox_crop
    = 700 rows
    """
    required_columns = [
        "case_id",
        "painting_id",
        "mask_id",
        "mask_type",
        "model_name",
        "clean_path",
        "damaged_path",
        "restored_path",
        "mask_path",
        "content_x_min",
        "content_y_min",
        "content_x_max",
        "content_y_max",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in restoration_metadata.columns
    ]

    if missing_columns:
        raise ValueError(f"Restoration metadata missing required columns: {missing_columns}")

    total_cases = len(restoration_metadata)
    expected_metric_rows = total_cases * 2 + int((restoration_metadata["mask_type"] != "zero_control").sum())

    print(f"Starting LPIPS computation for {total_cases} restoration cases...")
    print(f"Expected LPIPS metric rows: {expected_metric_rows}")
    print(f"Device: {device}")
    print(f"LPIPS net: {lpips_net}")

    records: list[dict[str, Any]] = []

    device_name = str(device)

    for idx, (_, row) in enumerate(
        restoration_metadata.sort_values(["painting_id", "mask_type"]).iterrows(),
        start=1,
    ):
        try:
            clean_img = load_rgb_image(Path(row["clean_path"]))
            damaged_img = load_rgb_image(Path(row["damaged_path"]))
            restored_img = load_rgb_image(Path(row["restored_path"]))
            mask_bool = load_mask_bool(Path(row["mask_path"]))

            if clean_img.size != damaged_img.size or clean_img.size != restored_img.size:
                raise ValueError(
                    f"Image size mismatch for case {row['case_id']}: "
                    f"clean={clean_img.size}, damaged={damaged_img.size}, restored={restored_img.size}"
                )

            if clean_img.size != (target_size, target_size):
                raise ValueError(
                    f"Unexpected image size for case {row['case_id']}: {clean_img.size}"
                )

            if mask_bool.shape != (target_size, target_size):
                raise ValueError(
                    f"Unexpected mask shape for case {row['case_id']}: {mask_bool.shape}"
                )

            # 1. Full image LPIPS.
            full_box = (0, 0, clean_img.size[0], clean_img.size[1])

            clean_full = resize_for_lpips(clean_img, size=crop_resize)
            damaged_full = resize_for_lpips(damaged_img, size=crop_resize)
            restored_full = resize_for_lpips(restored_img, size=crop_resize)

            damaged_lpips_full = compute_lpips_distance(
                clean_full,
                damaged_full,
                lpips_model,
                device,
            )
            restored_lpips_full = compute_lpips_distance(
                clean_full,
                restored_full,
                lpips_model,
                device,
            )

            records.append(
                _build_lpips_record(
                    row=row,
                    evaluation_region="full_image",
                    damaged_lpips=damaged_lpips_full,
                    restored_lpips=restored_lpips_full,
                    region_box=full_box,
                    region_pixel_count=target_size * target_size,
                    lpips_net=lpips_net,
                    crop_resize=crop_resize,
                    device_name=device_name,
                )
            )

            # 2. Content region LPIPS.
            content_box = get_content_box_from_row(row)

            clean_content = crop_image_region(clean_img, content_box, resize_to=crop_resize)
            damaged_content = crop_image_region(damaged_img, content_box, resize_to=crop_resize)
            restored_content = crop_image_region(restored_img, content_box, resize_to=crop_resize)

            damaged_lpips_content = compute_lpips_distance(
                clean_content,
                damaged_content,
                lpips_model,
                device,
            )
            restored_lpips_content = compute_lpips_distance(
                clean_content,
                restored_content,
                lpips_model,
                device,
            )

            content_left, content_upper, content_right, content_lower = content_box

            records.append(
                _build_lpips_record(
                    row=row,
                    evaluation_region="content_region",
                    damaged_lpips=damaged_lpips_content,
                    restored_lpips=restored_lpips_content,
                    region_box=content_box,
                    region_pixel_count=(content_right - content_left) * (content_lower - content_upper),
                    lpips_net=lpips_net,
                    crop_resize=crop_resize,
                    device_name=device_name,
                )
            )

            # 3. Mask bbox crop LPIPS, only for non-zero masks.
            mask_box = get_mask_bbox(mask_bool, margin=mask_bbox_margin)

            if mask_box is not None:
                square_mask_box = make_square_crop_box(mask_box, image_size=clean_img.size)

                clean_mask_crop = crop_image_region(
                    clean_img,
                    square_mask_box,
                    resize_to=crop_resize,
                )
                damaged_mask_crop = crop_image_region(
                    damaged_img,
                    square_mask_box,
                    resize_to=crop_resize,
                )
                restored_mask_crop = crop_image_region(
                    restored_img,
                    square_mask_box,
                    resize_to=crop_resize,
                )

                damaged_lpips_mask_crop = compute_lpips_distance(
                    clean_mask_crop,
                    damaged_mask_crop,
                    lpips_model,
                    device,
                )
                restored_lpips_mask_crop = compute_lpips_distance(
                    clean_mask_crop,
                    restored_mask_crop,
                    lpips_model,
                    device,
                )

                left, upper, right, lower = square_mask_box

                records.append(
                    _build_lpips_record(
                        row=row,
                        evaluation_region="mask_bbox_crop",
                        damaged_lpips=damaged_lpips_mask_crop,
                        restored_lpips=restored_lpips_mask_crop,
                        region_box=square_mask_box,
                        region_pixel_count=(right - left) * (lower - upper),
                        lpips_net=lpips_net,
                        crop_resize=crop_resize,
                        device_name=device_name,
                    )
                )

        except Exception as exc:
            records.append(
                {
                    "case_id": row.get("case_id", ""),
                    "painting_id": row.get("painting_id", ""),
                    "category": row.get("category", ""),
                    "title": row.get("title", ""),
                    "mask_id": row.get("mask_id", ""),
                    "mask_type": row.get("mask_type", ""),
                    "model_name": row.get("model_name", ""),
                    "evaluation_region": "error",
                    "region_pixel_count": 0,
                    "region_x_min": None,
                    "region_y_min": None,
                    "region_x_max": None,
                    "region_y_max": None,
                    "damaged_area_pixels": row.get("damaged_area_pixels", np.nan),
                    "damaged_area_percentage_content": row.get("damaged_area_percentage_content", np.nan),
                    "damaged_area_percentage_full": row.get("damaged_area_percentage_full", np.nan),
                    "damaged_lpips": np.nan,
                    "restored_lpips": np.nan,
                    "lpips_improvement": np.nan,
                    "lpips_net": lpips_net,
                    "crop_resize": crop_resize,
                    "device": device_name,
                    "status": "error",
                    "issue": f"{type(exc).__name__}: {exc}",
                }
            )

        if progress_every is not None:
            if idx == 1 or idx % progress_every == 0 or idx == total_cases:
                print(f"Processed {idx}/{total_cases} restoration cases...")

    print("LPIPS computation finished.")
    return pd.DataFrame(records)


def validate_lpips_metrics(
    lpips_df: pd.DataFrame,
    expected_rows: int = 700,
) -> pd.DataFrame:
    """Validate LPIPS metric output structure."""
    required_columns = [
        "case_id",
        "painting_id",
        "mask_type",
        "model_name",
        "evaluation_region",
        "damaged_lpips",
        "restored_lpips",
        "lpips_improvement",
        "status",
        "issue",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in lpips_df.columns
    ]

    validation_rows: list[dict[str, Any]] = []

    validation_rows.append(
        {
            "check": "required_columns",
            "passed": len(missing_columns) == 0,
            "detail": (
                "All required columns present."
                if not missing_columns
                else f"Missing columns: {missing_columns}"
            ),
        }
    )

    validation_rows.append(
        {
            "check": "row_count",
            "passed": len(lpips_df) == expected_rows,
            "detail": f"Expected {expected_rows}, found {len(lpips_df)}.",
        }
    )

    if "status" in lpips_df.columns:
        error_rows = int((lpips_df["status"] != "ok").sum())
        validation_rows.append(
            {
                "check": "status_ok",
                "passed": error_rows == 0,
                "detail": f"Rows with non-ok status: {error_rows}.",
            }
        )

    if "evaluation_region" in lpips_df.columns:
        region_counts = lpips_df["evaluation_region"].value_counts().to_dict()
        validation_rows.append(
            {
                "check": "region_counts",
                "passed": True,
                "detail": str(region_counts),
            }
        )

    return pd.DataFrame(validation_rows)


def summarize_lpips_metrics(
    lpips_df: pd.DataFrame,
    group_columns: list[str],
) -> pd.DataFrame:
    """Summarize LPIPS metrics by one or more grouping columns."""
    if not group_columns:
        raise ValueError("At least one group column is required.")

    missing_group_columns = [
        col for col in group_columns
        if col not in lpips_df.columns
    ]

    if missing_group_columns:
        raise ValueError(f"LPIPS dataframe missing group columns: {missing_group_columns}")

    return (
        lpips_df
        .groupby(group_columns, dropna=False)
        .agg(
            rows=("case_id", "count"),
            cases=("case_id", "nunique"),
            mean_damaged_lpips=("damaged_lpips", "mean"),
            mean_restored_lpips=("restored_lpips", "mean"),
            mean_lpips_improvement=("lpips_improvement", "mean"),
            median_damaged_lpips=("damaged_lpips", "median"),
            median_restored_lpips=("restored_lpips", "median"),
            median_lpips_improvement=("lpips_improvement", "median"),
            improvement_rate=("lpips_improvement", lambda values: (values > 0).mean()),
            mean_region_pixel_count=("region_pixel_count", "mean"),
        )
        .reset_index()
        .round(5)
    )


def rank_lpips_cases(
    lpips_df: pd.DataFrame,
    evaluation_region: str = "mask_bbox_crop",
    top_n: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return strongest and weakest cases by LPIPS improvement."""
    region_df = (
        lpips_df[
            (lpips_df["evaluation_region"] == evaluation_region)
            & (lpips_df["status"] == "ok")
        ]
        .copy()
    )

    strongest_df = (
        region_df
        .sort_values("lpips_improvement", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    weakest_df = (
        region_df
        .sort_values("lpips_improvement", ascending=True)
        .head(top_n)
        .reset_index(drop=True)
    )

    return strongest_df, weakest_df