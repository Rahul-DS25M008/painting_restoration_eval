"""
Feature-space similarity utilities for painting restoration evaluation.

This module computes CLIP and DINOv2 cosine similarities for damaged and
restored images against the clean reference image.

Higher cosine similarity means higher feature-space similarity.

Evaluation regions:
- full_image
- content_region
- mask_bbox_crop

Sparse masked pixels are intentionally not used directly because CLIP and DINOv2
expect image-like spatial inputs, not unordered pixel sets.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image

import torch
import torch.nn.functional as F


DEFAULT_CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"
DEFAULT_DINOV2_MODEL_NAME = "dinov2_vits14"
DEFAULT_CROP_RESIZE = 224
DEFAULT_MASK_BBOX_MARGIN = 32


def get_device(prefer_cuda: bool = True) -> torch.device:
    """Return CUDA device if available and requested, otherwise CPU."""
    if prefer_cuda and torch.cuda.is_available():
        return torch.device("cuda")

    return torch.device("cpu")


def load_clip_model_and_processor(
    model_name: str = DEFAULT_CLIP_MODEL_NAME,
    device: torch.device | None = None,
):
    """Load CLIP model and processor using Hugging Face Transformers.

    The use_safetensors=True flag avoids loading PyTorch .bin weights through
    torch.load on older Torch versions.
    """
    from transformers import CLIPModel, CLIPProcessor

    if device is None:
        device = get_device()

    processor = CLIPProcessor.from_pretrained(model_name)

    model = CLIPModel.from_pretrained(
        model_name,
        use_safetensors=True,
    ).to(device)

    model.eval()

    return model, processor


def load_dinov2_model(
    model_name: str = DEFAULT_DINOV2_MODEL_NAME,
    device: torch.device | None = None,
):
    """Load DINOv2 model from torch.hub."""
    if device is None:
        device = get_device()

    model = torch.hub.load(
        "facebookresearch/dinov2",
        model_name,
        verbose=False,
    ).to(device)

    model.eval()

    return model


def load_rgb_image(path: Path) -> Image.Image:
    """Load an image as RGB PIL image."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    with Image.open(path) as image:
        return image.convert("RGB")


def load_mask_bool(path: Path) -> np.ndarray:
    """Load binary mask where True indicates the damaged/restored region."""
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


def resize_region(
    image: Image.Image,
    size: int = DEFAULT_CROP_RESIZE,
) -> Image.Image:
    """Resize an image region to a square feature-model input size."""
    return image.convert("RGB").resize(
        (size, size),
        Image.Resampling.LANCZOS,
    )


def crop_image_region(
    image: Image.Image,
    box: tuple[int, int, int, int],
    resize_to: int = DEFAULT_CROP_RESIZE,
) -> Image.Image:
    """Crop an image region and resize it for feature extraction."""
    return resize_region(
        image.crop(box),
        size=resize_to,
    )


def cosine_similarity_from_features(
    features_a: torch.Tensor,
    features_b: torch.Tensor,
) -> float:
    """Compute cosine similarity between two feature tensors."""
    features_a = features_a.float()
    features_b = features_b.float()

    if features_a.ndim == 1:
        features_a = features_a.unsqueeze(0)

    if features_b.ndim == 1:
        features_b = features_b.unsqueeze(0)

    features_a = F.normalize(features_a, dim=-1)
    features_b = F.normalize(features_b, dim=-1)

    similarity = torch.sum(features_a * features_b, dim=-1)

    return float(similarity.item())

def extract_feature_tensor(features, source_name: str = "model") -> torch.Tensor:
    """Extract a tensor from common model output formats."""
    if isinstance(features, torch.Tensor):
        return features.detach()

    if isinstance(features, dict):
        for key in [
            "image_embeds",
            "pooler_output",
            "x_norm_clstoken",
            "last_hidden_state",
        ]:
            if key in features and isinstance(features[key], torch.Tensor):
                value = features[key]
                if key == "last_hidden_state" and value.ndim == 3:
                    value = value[:, 0]
                return value.detach()

        first_key = next(iter(features.keys()))
        first_value = features[first_key]

        if isinstance(first_value, torch.Tensor):
            return first_value.detach()

        raise TypeError(
            f"Unsupported dictionary output from {source_name}. "
            f"First key {first_key!r} has type {type(first_value)}."
        )

    if hasattr(features, "image_embeds") and features.image_embeds is not None:
        return features.image_embeds.detach()

    if hasattr(features, "pooler_output") and features.pooler_output is not None:
        return features.pooler_output.detach()

    if hasattr(features, "last_hidden_state") and features.last_hidden_state is not None:
        return features.last_hidden_state[:, 0].detach()

    if hasattr(features, "hidden_states") and features.hidden_states is not None:
        return features.hidden_states[-1][:, 0].detach()

    raise TypeError(
        f"Unsupported output type from {source_name}: {type(features)}"
    )


def compute_clip_embedding(
    image: Image.Image,
    clip_model,
    clip_processor,
    device: torch.device,
) -> torch.Tensor:
    """Compute CLIP image embedding."""
    inputs = clip_processor(
        images=image.convert("RGB"),
        return_tensors="pt",
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.no_grad():
        try:
            image_features = clip_model.get_image_features(**inputs)
        except AttributeError:
            image_features = clip_model(**inputs)

    return extract_feature_tensor(image_features, source_name="CLIP")


def compute_dinov2_embedding(
    image: Image.Image,
    dinov2_model,
    device: torch.device,
    image_size: int = DEFAULT_CROP_RESIZE,
) -> torch.Tensor:
    """Compute DINOv2 image embedding.

    DINOv2 torch.hub models usually return a tensor directly.
    Some wrappers may return structured outputs, so extraction is defensive.
    """
    import torchvision.transforms as T

    transform = T.Compose(
        [
            T.Resize((image_size, image_size)),
            T.ToTensor(),
            T.Normalize(
                mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225),
            ),
        ]
    )

    tensor = transform(image.convert("RGB")).unsqueeze(0).to(device)

    with torch.no_grad():
        features = dinov2_model(tensor)

    return extract_feature_tensor(features, source_name="DINOv2")

def compute_feature_similarities_for_region(
    clean_region: Image.Image,
    damaged_region: Image.Image,
    restored_region: Image.Image,
    clip_model,
    clip_processor,
    dinov2_model,
    device: torch.device,
    feature_resize: int = DEFAULT_CROP_RESIZE,
) -> dict[str, float]:
    """Compute CLIP and DINOv2 damaged/restored similarities for one region."""
    clean_region = resize_region(clean_region, size=feature_resize)
    damaged_region = resize_region(damaged_region, size=feature_resize)
    restored_region = resize_region(restored_region, size=feature_resize)

    clean_clip = compute_clip_embedding(
        clean_region,
        clip_model=clip_model,
        clip_processor=clip_processor,
        device=device,
    )
    damaged_clip = compute_clip_embedding(
        damaged_region,
        clip_model=clip_model,
        clip_processor=clip_processor,
        device=device,
    )
    restored_clip = compute_clip_embedding(
        restored_region,
        clip_model=clip_model,
        clip_processor=clip_processor,
        device=device,
    )

    clip_damaged_similarity = cosine_similarity_from_features(clean_clip, damaged_clip)
    clip_restored_similarity = cosine_similarity_from_features(clean_clip, restored_clip)

    clean_dino = compute_dinov2_embedding(
        clean_region,
        dinov2_model=dinov2_model,
        device=device,
        image_size=feature_resize,
    )
    damaged_dino = compute_dinov2_embedding(
        damaged_region,
        dinov2_model=dinov2_model,
        device=device,
        image_size=feature_resize,
    )
    restored_dino = compute_dinov2_embedding(
        restored_region,
        dinov2_model=dinov2_model,
        device=device,
        image_size=feature_resize,
    )

    dinov2_damaged_similarity = cosine_similarity_from_features(clean_dino, damaged_dino)
    dinov2_restored_similarity = cosine_similarity_from_features(clean_dino, restored_dino)

    return {
        "clip_damaged_similarity": clip_damaged_similarity,
        "clip_restored_similarity": clip_restored_similarity,
        "clip_similarity_improvement": clip_restored_similarity - clip_damaged_similarity,
        "dinov2_damaged_similarity": dinov2_damaged_similarity,
        "dinov2_restored_similarity": dinov2_restored_similarity,
        "dinov2_similarity_improvement": dinov2_restored_similarity - dinov2_damaged_similarity,
    }


def _build_feature_record(
    row: pd.Series,
    evaluation_region: str,
    region_box: tuple[int, int, int, int],
    region_pixel_count: int,
    similarities: dict[str, float],
    clip_model_name: str,
    dinov2_model_name: str,
    feature_resize: int,
    device_name: str,
    status: str = "ok",
    issue: str = "",
) -> dict[str, Any]:
    """Build one feature-similarity metric record."""
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
        **similarities,
        "clip_model_name": clip_model_name,
        "dinov2_model_name": dinov2_model_name,
        "feature_resize": int(feature_resize),
        "device": device_name,
        "status": status,
        "issue": issue,
    }


def compute_feature_similarity_for_restorations(
    restoration_metadata: pd.DataFrame,
    clip_model,
    clip_processor,
    dinov2_model,
    device: torch.device,
    clip_model_name: str = DEFAULT_CLIP_MODEL_NAME,
    dinov2_model_name: str = DEFAULT_DINOV2_MODEL_NAME,
    target_size: int = 768,
    mask_bbox_margin: int = DEFAULT_MASK_BBOX_MARGIN,
    feature_resize: int = DEFAULT_CROP_RESIZE,
    progress_every: int | None = 50,
) -> pd.DataFrame:
    """Compute CLIP and DINOv2 feature similarities for restoration outputs.

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

    print(f"Starting feature-similarity computation for {total_cases} restoration cases...")
    print(f"Expected feature metric rows: {expected_metric_rows}")
    print(f"Device: {device}")
    print(f"CLIP model: {clip_model_name}")
    print(f"DINOv2 model: {dinov2_model_name}")

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

            # 1. Full image feature similarity.
            full_box = (0, 0, clean_img.size[0], clean_img.size[1])

            full_similarities = compute_feature_similarities_for_region(
                clean_region=clean_img,
                damaged_region=damaged_img,
                restored_region=restored_img,
                clip_model=clip_model,
                clip_processor=clip_processor,
                dinov2_model=dinov2_model,
                device=device,
                feature_resize=feature_resize,
            )

            records.append(
                _build_feature_record(
                    row=row,
                    evaluation_region="full_image",
                    region_box=full_box,
                    region_pixel_count=target_size * target_size,
                    similarities=full_similarities,
                    clip_model_name=clip_model_name,
                    dinov2_model_name=dinov2_model_name,
                    feature_resize=feature_resize,
                    device_name=device_name,
                )
            )

            # 2. Content region feature similarity.
            content_box = get_content_box_from_row(row)

            clean_content = crop_image_region(clean_img, content_box, resize_to=feature_resize)
            damaged_content = crop_image_region(damaged_img, content_box, resize_to=feature_resize)
            restored_content = crop_image_region(restored_img, content_box, resize_to=feature_resize)

            content_similarities = compute_feature_similarities_for_region(
                clean_region=clean_content,
                damaged_region=damaged_content,
                restored_region=restored_content,
                clip_model=clip_model,
                clip_processor=clip_processor,
                dinov2_model=dinov2_model,
                device=device,
                feature_resize=feature_resize,
            )

            left, upper, right, lower = content_box

            records.append(
                _build_feature_record(
                    row=row,
                    evaluation_region="content_region",
                    region_box=content_box,
                    region_pixel_count=(right - left) * (lower - upper),
                    similarities=content_similarities,
                    clip_model_name=clip_model_name,
                    dinov2_model_name=dinov2_model_name,
                    feature_resize=feature_resize,
                    device_name=device_name,
                )
            )

            # 3. Mask bbox crop feature similarity, only for non-zero masks.
            mask_box = get_mask_bbox(mask_bool, margin=mask_bbox_margin)

            if mask_box is not None:
                square_mask_box = make_square_crop_box(mask_box, image_size=clean_img.size)

                clean_mask_crop = crop_image_region(
                    clean_img,
                    square_mask_box,
                    resize_to=feature_resize,
                )
                damaged_mask_crop = crop_image_region(
                    damaged_img,
                    square_mask_box,
                    resize_to=feature_resize,
                )
                restored_mask_crop = crop_image_region(
                    restored_img,
                    square_mask_box,
                    resize_to=feature_resize,
                )

                mask_crop_similarities = compute_feature_similarities_for_region(
                    clean_region=clean_mask_crop,
                    damaged_region=damaged_mask_crop,
                    restored_region=restored_mask_crop,
                    clip_model=clip_model,
                    clip_processor=clip_processor,
                    dinov2_model=dinov2_model,
                    device=device,
                    feature_resize=feature_resize,
                )

                left, upper, right, lower = square_mask_box

                records.append(
                    _build_feature_record(
                        row=row,
                        evaluation_region="mask_bbox_crop",
                        region_box=square_mask_box,
                        region_pixel_count=(right - left) * (lower - upper),
                        similarities=mask_crop_similarities,
                        clip_model_name=clip_model_name,
                        dinov2_model_name=dinov2_model_name,
                        feature_resize=feature_resize,
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
                    "clip_damaged_similarity": np.nan,
                    "clip_restored_similarity": np.nan,
                    "clip_similarity_improvement": np.nan,
                    "dinov2_damaged_similarity": np.nan,
                    "dinov2_restored_similarity": np.nan,
                    "dinov2_similarity_improvement": np.nan,
                    "clip_model_name": clip_model_name,
                    "dinov2_model_name": dinov2_model_name,
                    "feature_resize": int(feature_resize),
                    "device": device_name,
                    "status": "error",
                    "issue": f"{type(exc).__name__}: {exc}",
                }
            )

        if progress_every is not None:
            if idx == 1 or idx % progress_every == 0 or idx == total_cases:
                print(f"Processed {idx}/{total_cases} restoration cases...")

    print("Feature-similarity computation finished.")
    return pd.DataFrame(records)


def validate_feature_similarity_metrics(
    feature_df: pd.DataFrame,
    expected_rows: int = 700,
) -> pd.DataFrame:
    """Validate feature-similarity metric output structure."""
    required_columns = [
        "case_id",
        "painting_id",
        "mask_type",
        "model_name",
        "evaluation_region",
        "clip_damaged_similarity",
        "clip_restored_similarity",
        "clip_similarity_improvement",
        "dinov2_damaged_similarity",
        "dinov2_restored_similarity",
        "dinov2_similarity_improvement",
        "status",
        "issue",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in feature_df.columns
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
            "passed": len(feature_df) == expected_rows,
            "detail": f"Expected {expected_rows}, found {len(feature_df)}.",
        }
    )

    if "status" in feature_df.columns:
        error_rows = int((feature_df["status"] != "ok").sum())
        validation_rows.append(
            {
                "check": "status_ok",
                "passed": error_rows == 0,
                "detail": f"Rows with non-ok status: {error_rows}.",
            }
        )

    if "evaluation_region" in feature_df.columns:
        region_counts = feature_df["evaluation_region"].value_counts().to_dict()
        validation_rows.append(
            {
                "check": "region_counts",
                "passed": True,
                "detail": str(region_counts),
            }
        )

    return pd.DataFrame(validation_rows)


def summarize_feature_similarity_metrics(
    feature_df: pd.DataFrame,
    group_columns: list[str],
) -> pd.DataFrame:
    """Summarize feature-similarity metrics by one or more grouping columns."""
    if not group_columns:
        raise ValueError("At least one group column is required.")

    missing_group_columns = [
        col for col in group_columns
        if col not in feature_df.columns
    ]

    if missing_group_columns:
        raise ValueError(f"Feature dataframe missing group columns: {missing_group_columns}")

    return (
        feature_df
        .groupby(group_columns, dropna=False)
        .agg(
            rows=("case_id", "count"),
            cases=("case_id", "nunique"),
            mean_clip_damaged_similarity=("clip_damaged_similarity", "mean"),
            mean_clip_restored_similarity=("clip_restored_similarity", "mean"),
            mean_clip_similarity_improvement=("clip_similarity_improvement", "mean"),
            median_clip_similarity_improvement=("clip_similarity_improvement", "median"),
            clip_improvement_rate=("clip_similarity_improvement", lambda values: (values > 0).mean()),
            mean_dinov2_damaged_similarity=("dinov2_damaged_similarity", "mean"),
            mean_dinov2_restored_similarity=("dinov2_restored_similarity", "mean"),
            mean_dinov2_similarity_improvement=("dinov2_similarity_improvement", "mean"),
            median_dinov2_similarity_improvement=("dinov2_similarity_improvement", "median"),
            dinov2_improvement_rate=("dinov2_similarity_improvement", lambda values: (values > 0).mean()),
            mean_region_pixel_count=("region_pixel_count", "mean"),
        )
        .reset_index()
        .round(5)
    )


def rank_feature_similarity_cases(
    feature_df: pd.DataFrame,
    evaluation_region: str = "mask_bbox_crop",
    metric: str = "dinov2_similarity_improvement",
    top_n: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return strongest and weakest cases by a feature-similarity improvement metric."""
    if metric not in feature_df.columns:
        raise ValueError(f"Metric column not found: {metric}")

    region_df = (
        feature_df[
            (feature_df["evaluation_region"] == evaluation_region)
            & (feature_df["status"] == "ok")
        ]
        .copy()
    )

    strongest_df = (
        region_df
        .sort_values(metric, ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    weakest_df = (
        region_df
        .sort_values(metric, ascending=True)
        .head(top_n)
        .reset_index(drop=True)
    )

    return strongest_df, weakest_df