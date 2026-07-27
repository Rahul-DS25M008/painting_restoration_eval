"""
CLIP and DINOv2 feature-similarity metrics for restoration evaluation.

The module compares damaged and restored images against the clean reference
using image-like spatial regions only:

- full_image;
- content_region;
- mask_bbox_crop for non-zero masks.

Sparse masked pixels are intentionally excluded because CLIP and DINOv2 operate
on ordered image patches, not unordered pixel selections.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import platform
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from PIL import Image


FEATURE_SIMILARITY_MODULE_NAME = "restoration_eval.metrics_feature_similarity"
FEATURE_SIMILARITY_METRIC_SCHEMA_VERSION = "2.0.0"

DEFAULT_CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"
DEFAULT_CLIP_MODEL_REVISION = "default"
DEFAULT_DINOV2_MODEL_NAME = "dinov2_vits14"
DEFAULT_DINOV2_MODEL_REVISION = "torchhub-default"
DEFAULT_FEATURE_INPUT_SIZE = 224
DEFAULT_MASK_BBOX_MARGIN = 8
DEFAULT_MASK_BINARY_THRESHOLD = 127

FEATURE_SIMILARITY_EVALUATION_REGIONS = (
    "full_image",
    "content_region",
    "mask_bbox_crop",
)


def get_package_version(package_name: str) -> str:
    """Return an installed package version, or ``not-installed``."""
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def validate_feature_similarity_runtime_dependencies() -> pd.DataFrame:
    """Check optional packages needed for feature-similarity computation."""
    dependency_rows = []

    for module_name, package_name, required in (
        ("torch", "torch", True),
        ("torchvision", "torchvision", True),
        ("transformers", "transformers", True),
        ("safetensors", "safetensors", True),
        ("PIL", "Pillow", True),
    ):
        module_spec = importlib.util.find_spec(module_name)
        installed = module_spec is not None
        dependency_rows.append(
            {
                "component": package_name,
                "module": module_name,
                "version": get_package_version(package_name),
                "required": required,
                "installed": installed,
                "passed": installed or not required,
            }
        )

    return pd.DataFrame(dependency_rows)


def get_device(prefer_cuda: bool = True):
    """Return a torch device, preferring CUDA when requested and available."""
    torch = importlib.import_module("torch")

    if prefer_cuda and torch.cuda.is_available():
        return torch.device("cuda")

    return torch.device("cpu")


def load_clip_model_and_processor(
    model_name: str = DEFAULT_CLIP_MODEL_NAME,
    device: Any | None = None,
    revision: str | None = None,
):
    """Load CLIP lazily through Hugging Face Transformers."""
    transformers = importlib.import_module("transformers")
    clip_model_cls = getattr(transformers, "CLIPModel")
    clip_processor_cls = getattr(transformers, "CLIPProcessor")

    if device is None:
        device = get_device()

    from_pretrained_kwargs: dict[str, Any] = {}
    if revision and revision != DEFAULT_CLIP_MODEL_REVISION:
        from_pretrained_kwargs["revision"] = revision

    processor = clip_processor_cls.from_pretrained(
        model_name,
        **from_pretrained_kwargs,
    )
    model = clip_model_cls.from_pretrained(
        model_name,
        use_safetensors=True,
        **from_pretrained_kwargs,
    ).to(device)
    model.eval()

    return model, processor


def load_dinov2_model(
    model_name: str = DEFAULT_DINOV2_MODEL_NAME,
    device: Any | None = None,
    repo_or_dir: str = "facebookresearch/dinov2",
    trust_repo: bool = True,
):
    """Load a DINOv2 model lazily from torch.hub."""
    torch = importlib.import_module("torch")

    if device is None:
        device = get_device()

    model = torch.hub.load(
        repo_or_dir,
        model_name,
        verbose=False,
        trust_repo=trust_repo,
    ).to(device)
    model.eval()

    return model


def load_rgb_image(path: Path | str) -> Image.Image:
    """Load an image file as RGB."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    with Image.open(path) as image:
        return image.convert("RGB")


def load_mask_bool(
    path: Path | str,
    threshold: int = DEFAULT_MASK_BINARY_THRESHOLD,
) -> np.ndarray:
    """Load a mask as a boolean array where True marks damage."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Mask file not found: {path}")

    with Image.open(path) as image:
        mask_arr = np.asarray(image.convert("L"))

    return mask_arr > threshold


def clip_box(
    box: tuple[int, int, int, int],
    image_size: tuple[int, int],
) -> tuple[int, int, int, int] | None:
    """Clip a PIL-style crop box to image bounds."""
    left, upper, right, lower = box
    width, height = image_size

    left = max(0, min(int(left), width))
    right = max(0, min(int(right), width))
    upper = max(0, min(int(upper), height))
    lower = max(0, min(int(lower), height))

    if right <= left or lower <= upper:
        return None

    return left, upper, right, lower


def get_content_box_from_row(
    row: pd.Series,
    image_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    """Get the recorded content-region box in PIL crop coordinates."""
    required_columns = (
        "content_x_min",
        "content_y_min",
        "content_x_max",
        "content_y_max",
    )
    missing_columns = [
        column
        for column in required_columns
        if column not in row.index
    ]

    if missing_columns:
        raise ValueError(f"Missing content-region columns: {missing_columns}")

    raw_values = [
        row[column]
        for column in required_columns
    ]

    if any(_is_null_like(value) for value in raw_values):
        raise ValueError(
            "Invalid content box contains null values: "
            f"{dict(zip(required_columns, raw_values))}"
        )

    try:
        numeric_values = [
            float(value)
            for value in raw_values
        ]
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Invalid content box contains non-numeric values: "
            f"{dict(zip(required_columns, raw_values))}"
        ) from exc

    if not np.isfinite(numeric_values).all():
        raise ValueError(
            "Invalid content box contains non-finite values: "
            f"{dict(zip(required_columns, raw_values))}"
        )

    content_box = clip_box(
        tuple(
            int(round(value))
            for value in numeric_values
        ),
        image_size=image_size,
    )

    if content_box is None:
        raise ValueError(
            "Invalid content box: "
            f"{[row[column] for column in required_columns]}"
        )

    return content_box


def get_mask_bbox(
    mask_bool: np.ndarray,
    margin: int = DEFAULT_MASK_BBOX_MARGIN,
) -> tuple[int, int, int, int] | None:
    """Return a padded mask bounding box in PIL crop coordinates."""
    if margin < 0:
        raise ValueError("mask_bbox_margin must be non-negative.")

    y_coords, x_coords = np.where(mask_bool)

    if len(x_coords) == 0:
        return None

    height, width = mask_bool.shape

    return clip_box(
        (
            int(x_coords.min()) - int(margin),
            int(y_coords.min()) - int(margin),
            int(x_coords.max()) + int(margin) + 1,
            int(y_coords.max()) + int(margin) + 1,
        ),
        image_size=(width, height),
    )


def make_square_crop_box(
    box: tuple[int, int, int, int],
    image_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    """Expand a crop box to a square while staying inside the image."""
    left, upper, right, lower = box
    width, height = image_size

    crop_width = right - left
    crop_height = lower - upper
    side = min(max(crop_width, crop_height), width, height)

    center_x = (left + right) // 2
    center_y = (upper + lower) // 2

    square_left = center_x - side // 2
    square_upper = center_y - side // 2
    square_right = square_left + side
    square_lower = square_upper + side

    if square_left < 0:
        square_right -= square_left
        square_left = 0

    if square_upper < 0:
        square_lower -= square_upper
        square_upper = 0

    if square_right > width:
        shift = square_right - width
        square_left -= shift
        square_right = width

    if square_lower > height:
        shift = square_lower - height
        square_upper -= shift
        square_lower = height

    clipped_box = clip_box(
        (square_left, square_upper, square_right, square_lower),
        image_size=image_size,
    )

    if clipped_box is None:
        raise ValueError(f"Invalid square crop box derived from {box}.")

    return clipped_box


def resize_for_feature_model(
    image: Image.Image,
    size: int = DEFAULT_FEATURE_INPUT_SIZE,
) -> Image.Image:
    """Resize an image region to a square feature-model input size."""
    return image.convert("RGB").resize(
        (int(size), int(size)),
        Image.Resampling.LANCZOS,
    )


def crop_image_region(
    image: Image.Image,
    box: tuple[int, int, int, int],
    resize_to: int = DEFAULT_FEATURE_INPUT_SIZE,
) -> Image.Image:
    """Crop an image region and resize it for feature extraction."""
    return resize_for_feature_model(
        image.crop(box),
        size=resize_to,
    )


def _is_null_like(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except TypeError:
        return False


def _row_value(row: pd.Series, key: str, default: Any = "") -> Any:
    value = row.get(key, default)
    return default if _is_null_like(value) else value


def _to_bool(value: Any) -> bool:
    if _is_null_like(value):
        return False

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, np.integer)):
        return bool(value)

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}

    return bool(value)


def _safe_difference(left: float, right: float) -> float:
    if np.isnan(left) or np.isnan(right):
        return float("nan")

    return float(left - right)


def _box_to_region_info(
    box: tuple[int, int, int, int],
) -> dict[str, int]:
    left, upper, right, lower = box
    return {
        "region_x_min": int(left),
        "region_y_min": int(upper),
        "region_x_max": int(right),
        "region_y_max": int(lower),
    }


def extract_feature_tensor(features: Any, source_name: str = "model"):
    """Extract a tensor from common model output formats."""
    torch = importlib.import_module("torch")

    if isinstance(features, torch.Tensor):
        return features.detach()

    if isinstance(features, dict):
        for key in (
            "image_embeds",
            "pooler_output",
            "x_norm_clstoken",
            "last_hidden_state",
        ):
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


def cosine_similarity_from_features(features_a: Any, features_b: Any) -> float:
    """Compute cosine similarity between two feature tensors."""
    torch = importlib.import_module("torch")
    functional = importlib.import_module("torch.nn.functional")

    features_a = features_a.float()
    features_b = features_b.float()

    if features_a.ndim == 1:
        features_a = features_a.unsqueeze(0)

    if features_b.ndim == 1:
        features_b = features_b.unsqueeze(0)

    features_a = functional.normalize(features_a, dim=-1)
    features_b = functional.normalize(features_b, dim=-1)

    similarity = torch.sum(features_a * features_b, dim=-1)

    return float(similarity.item())


def compute_clip_embedding(
    image: Image.Image,
    clip_model: Any,
    clip_processor: Any,
    device: Any,
) -> Any:
    """Compute a CLIP image embedding."""
    torch = importlib.import_module("torch")

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
    dinov2_model: Any,
    device: Any,
    image_size: int = DEFAULT_FEATURE_INPUT_SIZE,
) -> Any:
    """Compute a DINOv2 image embedding."""
    torch = importlib.import_module("torch")
    transforms = importlib.import_module("torchvision.transforms")

    transform = transforms.Compose(
        [
            transforms.Resize((int(image_size), int(image_size))),
            transforms.ToTensor(),
            transforms.Normalize(
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
    clip_model: Any,
    clip_processor: Any,
    dinov2_model: Any,
    device: Any,
    feature_input_size: int = DEFAULT_FEATURE_INPUT_SIZE,
) -> dict[str, float]:
    """Compute CLIP and DINOv2 similarities for one spatial region."""
    clean_region = resize_for_feature_model(clean_region, size=feature_input_size)
    damaged_region = resize_for_feature_model(damaged_region, size=feature_input_size)
    restored_region = resize_for_feature_model(restored_region, size=feature_input_size)

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

    clean_dinov2 = compute_dinov2_embedding(
        clean_region,
        dinov2_model=dinov2_model,
        device=device,
        image_size=feature_input_size,
    )
    damaged_dinov2 = compute_dinov2_embedding(
        damaged_region,
        dinov2_model=dinov2_model,
        device=device,
        image_size=feature_input_size,
    )
    restored_dinov2 = compute_dinov2_embedding(
        restored_region,
        dinov2_model=dinov2_model,
        device=device,
        image_size=feature_input_size,
    )

    dinov2_damaged_similarity = cosine_similarity_from_features(
        clean_dinov2,
        damaged_dinov2,
    )
    dinov2_restored_similarity = cosine_similarity_from_features(
        clean_dinov2,
        restored_dinov2,
    )

    return {
        "clip_damaged_similarity": clip_damaged_similarity,
        "clip_restored_similarity": clip_restored_similarity,
        "clip_similarity_improvement": _safe_difference(
            clip_restored_similarity,
            clip_damaged_similarity,
        ),
        "dinov2_damaged_similarity": dinov2_damaged_similarity,
        "dinov2_restored_similarity": dinov2_restored_similarity,
        "dinov2_similarity_improvement": _safe_difference(
            dinov2_restored_similarity,
            dinov2_damaged_similarity,
        ),
        "mean_similarity_improvement": float(
            np.nanmean(
                [
                    _safe_difference(
                        clip_restored_similarity,
                        clip_damaged_similarity,
                    ),
                    _safe_difference(
                        dinov2_restored_similarity,
                        dinov2_damaged_similarity,
                    ),
                ]
            )
        ),
    }


def _build_feature_record(
    row: pd.Series,
    evaluation_region: str,
    region_box: tuple[int, int, int, int],
    similarities: dict[str, float],
    clip_model_name: str,
    clip_model_revision: str,
    dinov2_model_name: str,
    dinov2_model_revision: str,
    feature_input_size: int,
    mask_bbox_margin: int,
    mask_binary_threshold: int,
    device_name: str,
    torch_version: str,
    torchvision_version: str,
    transformers_version: str,
    metric_runtime_seconds: float,
    case_runtime_seconds: float,
    status: str = "ok",
    issue: str = "",
) -> dict[str, Any]:
    """Build one standardized feature-similarity output record."""
    restoration_case_id = _row_value(
        row,
        "restoration_case_id",
        _row_value(row, "case_id"),
    )
    metric_case_id = _row_value(row, "metric_case_id", restoration_case_id)
    dataset_name = _row_value(row, "dataset_name", "canonical")
    mask_type = _row_value(
        row,
        "metric_mask_type",
        _row_value(row, "mask_type"),
    )
    mask_id = _row_value(row, "metric_mask_id", _row_value(row, "mask_id"))
    source_case_id = _row_value(
        row,
        "source_case_id",
        _row_value(row, "case_id"),
    )
    source_case_id_original = _row_value(
        row,
        "source_case_id_original",
        source_case_id,
    )
    is_zero_control = _to_bool(_row_value(row, "is_zero_control", False))
    region_id = f"{metric_case_id}__{evaluation_region}"
    left, upper, right, lower = region_box

    return {
        "feature_row_id": f"{region_id}__feature_similarity",
        "feature_case_id": metric_case_id,
        "metric_case_id": metric_case_id,
        "restoration_case_id": restoration_case_id,
        "source_case_id": source_case_id,
        "source_case_id_original": source_case_id_original,
        "case_id": _row_value(row, "case_id", source_case_id),
        "dataset_name": dataset_name,
        "metric_applicability": _row_value(row, "metric_applicability", "primary"),
        "painting_id": _row_value(row, "painting_id"),
        "category": _row_value(row, "category"),
        "title": _row_value(row, "title"),
        "artist": _row_value(row, "artist"),
        "style": _row_value(row, "style", _row_value(row, "style_or_period")),
        "model_name": _row_value(row, "model_name"),
        "mask_id": mask_id,
        "mask_type": mask_type,
        "metric_mask_id": mask_id,
        "metric_mask_type": mask_type,
        "evaluation_region": evaluation_region,
        "region_pixel_count": int((right - left) * (lower - upper)),
        **_box_to_region_info(region_box),
        "mask_area_pixels": int(_row_value(row, "mask_area_pixels", 0)),
        "is_zero_control": is_zero_control,
        "mask_threshold_rule": f"> {mask_binary_threshold}",
        "mask_bbox_margin": int(mask_bbox_margin),
        "feature_input_size": int(feature_input_size),
        "clip_model_name": clip_model_name,
        "clip_model_revision": clip_model_revision,
        "dinov2_model_name": dinov2_model_name,
        "dinov2_model_revision": dinov2_model_revision,
        "clean_embedding_id": f"{region_id}__clean",
        "damaged_embedding_id": f"{region_id}__damaged",
        "restored_embedding_id": f"{region_id}__restored",
        "embedding_group_id": f"{dataset_name}__{_row_value(row, 'painting_id')}__{evaluation_region}",
        **similarities,
        "metric_runtime_seconds": float(metric_runtime_seconds),
        "case_runtime_seconds": float(case_runtime_seconds),
        "feature_similarity_schema_version": FEATURE_SIMILARITY_METRIC_SCHEMA_VERSION,
        "feature_similarity_implementation_name": FEATURE_SIMILARITY_MODULE_NAME,
        "device": device_name,
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "pillow_version": Image.__version__,
        "torch_version": torch_version,
        "torchvision_version": torchvision_version,
        "transformers_version": transformers_version,
        "status": status,
        "issue": issue,
    }


def expected_feature_similarity_rows_from_metadata(
    restoration_metadata: pd.DataFrame,
    mask_binary_threshold: int = DEFAULT_MASK_BINARY_THRESHOLD,
) -> int:
    """Return expected feature-similarity row count for the region policy."""
    if "mask_path" not in restoration_metadata.columns:
        raise ValueError("Restoration metadata missing required column: mask_path")

    nonzero_mask_cases = 0

    for mask_path in restoration_metadata["mask_path"]:
        if np.any(load_mask_bool(mask_path, threshold=mask_binary_threshold)):
            nonzero_mask_cases += 1

    return (
        len(restoration_metadata) * 2
        + nonzero_mask_cases
    )


def expected_feature_similarity_region_counts_from_metadata(
    restoration_metadata: pd.DataFrame,
    mask_binary_threshold: int = DEFAULT_MASK_BINARY_THRESHOLD,
) -> dict[str, int]:
    """Return expected row counts by feature-similarity region."""
    nonzero_mask_cases = sum(
        bool(np.any(load_mask_bool(mask_path, threshold=mask_binary_threshold)))
        for mask_path in restoration_metadata["mask_path"]
    )

    return {
        "full_image": len(restoration_metadata),
        "content_region": len(restoration_metadata),
        "mask_bbox_crop": nonzero_mask_cases,
    }


def compute_feature_similarity_for_restorations(
    restoration_metadata: pd.DataFrame,
    clip_model: Any,
    clip_processor: Any,
    dinov2_model: Any,
    device: Any,
    clip_model_name: str = DEFAULT_CLIP_MODEL_NAME,
    clip_model_revision: str = DEFAULT_CLIP_MODEL_REVISION,
    dinov2_model_name: str = DEFAULT_DINOV2_MODEL_NAME,
    dinov2_model_revision: str = DEFAULT_DINOV2_MODEL_REVISION,
    target_size: int | tuple[int, int] | None = 768,
    mask_bbox_margin: int = DEFAULT_MASK_BBOX_MARGIN,
    feature_input_size: int = DEFAULT_FEATURE_INPUT_SIZE,
    mask_binary_threshold: int = DEFAULT_MASK_BINARY_THRESHOLD,
    progress_every: int | None = 25,
) -> pd.DataFrame:
    """Compute CLIP and DINOv2 feature similarities for restoration outputs."""
    required_columns = [
        "case_id",
        "painting_id",
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
        column
        for column in required_columns
        if column not in restoration_metadata.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Restoration metadata missing required columns: {missing_columns}"
        )

    if restoration_metadata.empty:
        raise ValueError("Restoration metadata is empty.")

    if target_size is None:
        expected_size = None
    elif isinstance(target_size, int):
        expected_size = (target_size, target_size)
    else:
        expected_size = tuple(target_size)

    sort_columns = [
        column
        for column in ("dataset_name", "painting_id", "mask_type", "case_id")
        if column in restoration_metadata.columns
    ]
    sorted_metadata = (
        restoration_metadata
        .sort_values(sort_columns, kind="stable")
        .reset_index(drop=True)
    )

    records: list[dict[str, Any]] = []
    total_cases = len(sorted_metadata)
    computation_start_time = time.perf_counter()
    device_name = str(device)
    torch_version = get_package_version("torch")
    torchvision_version = get_package_version("torchvision")
    transformers_version = get_package_version("transformers")

    print("Starting feature-similarity metric computation")
    print(f"  Cases: {total_cases}")
    print(f"  Target size: {expected_size or 'not enforced'}")
    print(f"  Feature input size: {feature_input_size}")
    print(f"  CLIP model: {clip_model_name} ({clip_model_revision})")
    print(f"  DINOv2 model: {dinov2_model_name} ({dinov2_model_revision})")
    print(f"  Device: {device_name}")

    for case_index, (_, row) in enumerate(sorted_metadata.iterrows(), start=1):
        case_start_time = time.perf_counter()

        if progress_every and (
            case_index == 1
            or case_index % progress_every == 0
            or case_index == total_cases
        ):
            elapsed = time.perf_counter() - computation_start_time
            print(
                f"Computing feature case {case_index}/{total_cases} "
                f"({row['case_id']}) | elapsed {elapsed:.2f}s"
            )

        try:
            clean_image = load_rgb_image(row["clean_path"])
            damaged_image = load_rgb_image(row["damaged_path"])
            restored_image = load_rgb_image(row["restored_path"])
            mask_bool = load_mask_bool(
                row["mask_path"],
                threshold=mask_binary_threshold,
            )

            if clean_image.size != damaged_image.size or clean_image.size != restored_image.size:
                raise ValueError(
                    f"Image size mismatch for case {row['case_id']}: "
                    f"clean={clean_image.size}, damaged={damaged_image.size}, "
                    f"restored={restored_image.size}"
                )

            if mask_bool.shape != (clean_image.size[1], clean_image.size[0]):
                raise ValueError(
                    f"Mask shape mismatch for case {row['case_id']}: "
                    f"mask={mask_bool.shape}, image={clean_image.size}"
                )

            if expected_size is not None and clean_image.size != expected_size:
                raise ValueError(
                    f"Unexpected image size for case {row['case_id']}: "
                    f"{clean_image.size}, expected {expected_size}"
                )

            region_boxes = {
                "full_image": (
                    0,
                    0,
                    clean_image.size[0],
                    clean_image.size[1],
                ),
                "content_region": get_content_box_from_row(
                    row,
                    image_size=clean_image.size,
                ),
            }

            mask_box = get_mask_bbox(mask_bool, margin=mask_bbox_margin)
            if mask_box is not None:
                region_boxes["mask_bbox_crop"] = make_square_crop_box(
                    mask_box,
                    image_size=clean_image.size,
                )

            row_records: list[dict[str, Any]] = []

            for evaluation_region, region_box in region_boxes.items():
                metric_start_time = time.perf_counter()
                clean_region = crop_image_region(
                    clean_image,
                    region_box,
                    resize_to=feature_input_size,
                )
                damaged_region = crop_image_region(
                    damaged_image,
                    region_box,
                    resize_to=feature_input_size,
                )
                restored_region = crop_image_region(
                    restored_image,
                    region_box,
                    resize_to=feature_input_size,
                )
                similarities = compute_feature_similarities_for_region(
                    clean_region=clean_region,
                    damaged_region=damaged_region,
                    restored_region=restored_region,
                    clip_model=clip_model,
                    clip_processor=clip_processor,
                    dinov2_model=dinov2_model,
                    device=device,
                    feature_input_size=feature_input_size,
                )
                metric_runtime_seconds = time.perf_counter() - metric_start_time
                row_records.append(
                    _build_feature_record(
                        row=row,
                        evaluation_region=evaluation_region,
                        region_box=region_box,
                        similarities=similarities,
                        clip_model_name=clip_model_name,
                        clip_model_revision=clip_model_revision,
                        dinov2_model_name=dinov2_model_name,
                        dinov2_model_revision=dinov2_model_revision,
                        feature_input_size=feature_input_size,
                        mask_bbox_margin=mask_bbox_margin,
                        mask_binary_threshold=mask_binary_threshold,
                        device_name=device_name,
                        torch_version=torch_version,
                        torchvision_version=torchvision_version,
                        transformers_version=transformers_version,
                        metric_runtime_seconds=metric_runtime_seconds,
                        case_runtime_seconds=0.0,
                    )
                )

            case_runtime_seconds = time.perf_counter() - case_start_time
            for record in row_records:
                record["case_runtime_seconds"] = float(case_runtime_seconds)
            records.extend(row_records)

        except Exception as exc:
            case_runtime_seconds = time.perf_counter() - case_start_time
            restoration_case_id = row.get(
                "restoration_case_id",
                row.get("case_id", ""),
            )
            metric_case_id = row.get("metric_case_id", restoration_case_id)
            records.append(
                {
                    "feature_row_id": f"{metric_case_id}__error__feature_similarity",
                    "feature_case_id": metric_case_id,
                    "metric_case_id": metric_case_id,
                    "restoration_case_id": restoration_case_id,
                    "source_case_id": row.get("source_case_id", row.get("case_id", "")),
                    "source_case_id_original": row.get(
                        "source_case_id_original",
                        row.get("source_case_id", row.get("case_id", "")),
                    ),
                    "case_id": row.get("case_id", ""),
                    "dataset_name": row.get("dataset_name", "canonical"),
                    "metric_applicability": row.get("metric_applicability", "primary"),
                    "painting_id": row.get("painting_id", ""),
                    "category": row.get("category", ""),
                    "title": row.get("title", ""),
                    "artist": row.get("artist", ""),
                    "style": row.get("style", row.get("style_or_period", "")),
                    "model_name": row.get("model_name", ""),
                    "mask_id": row.get("metric_mask_id", row.get("mask_id", "")),
                    "mask_type": row.get("metric_mask_type", row.get("mask_type", "")),
                    "metric_mask_id": row.get("metric_mask_id", row.get("mask_id", "")),
                    "metric_mask_type": row.get(
                        "metric_mask_type",
                        row.get("mask_type", ""),
                    ),
                    "evaluation_region": "error",
                    "region_pixel_count": 0,
                    "region_x_min": None,
                    "region_y_min": None,
                    "region_x_max": None,
                    "region_y_max": None,
                    "mask_area_pixels": row.get("mask_area_pixels", 0),
                    "is_zero_control": row.get("is_zero_control", False),
                    "mask_threshold_rule": f"> {mask_binary_threshold}",
                    "mask_bbox_margin": int(mask_bbox_margin),
                    "feature_input_size": int(feature_input_size),
                    "clip_model_name": clip_model_name,
                    "clip_model_revision": clip_model_revision,
                    "dinov2_model_name": dinov2_model_name,
                    "dinov2_model_revision": dinov2_model_revision,
                    "clean_embedding_id": "",
                    "damaged_embedding_id": "",
                    "restored_embedding_id": "",
                    "embedding_group_id": "",
                    "clip_damaged_similarity": np.nan,
                    "clip_restored_similarity": np.nan,
                    "clip_similarity_improvement": np.nan,
                    "dinov2_damaged_similarity": np.nan,
                    "dinov2_restored_similarity": np.nan,
                    "dinov2_similarity_improvement": np.nan,
                    "mean_similarity_improvement": np.nan,
                    "metric_runtime_seconds": 0.0,
                    "case_runtime_seconds": float(case_runtime_seconds),
                    "feature_similarity_schema_version": FEATURE_SIMILARITY_METRIC_SCHEMA_VERSION,
                    "feature_similarity_implementation_name": FEATURE_SIMILARITY_MODULE_NAME,
                    "device": device_name,
                    "python_version": platform.python_version(),
                    "numpy_version": np.__version__,
                    "pandas_version": pd.__version__,
                    "pillow_version": Image.__version__,
                    "torch_version": torch_version,
                    "torchvision_version": torchvision_version,
                    "transformers_version": transformers_version,
                    "status": "error",
                    "issue": f"{type(exc).__name__}: {exc}",
                }
            )
            print(
                f"  Error in feature case {case_index}/{total_cases} "
                f"({row.get('case_id', '')}): {type(exc).__name__}: {exc}"
            )

    metrics_df = pd.DataFrame(records)
    elapsed_total = time.perf_counter() - computation_start_time

    print("Feature-similarity metric computation complete")
    print(f"  Runtime: {elapsed_total:.2f} seconds")
    print(f"  Output rows: {len(metrics_df)}")

    if "evaluation_region" in metrics_df.columns:
        print("  Region counts:")
        print(metrics_df["evaluation_region"].value_counts().to_string())

    if "status" in metrics_df.columns:
        print("  Status counts:")
        print(metrics_df["status"].value_counts(dropna=False).to_string())

    return metrics_df


def validate_feature_similarity_metrics(
    feature_df: pd.DataFrame,
    expected_rows: int | None = None,
    expected_region_counts: dict[str, int] | None = None,
    key_columns: Iterable[str] = (
        "dataset_name",
        "feature_case_id",
        "model_name",
        "evaluation_region",
    ),
) -> pd.DataFrame:
    """Validate feature-similarity output structure, counts, and policy."""
    required_columns = [
        "feature_row_id",
        "feature_case_id",
        "restoration_case_id",
        "dataset_name",
        "painting_id",
        "model_name",
        "evaluation_region",
        "region_pixel_count",
        "clip_damaged_similarity",
        "clip_restored_similarity",
        "clip_similarity_improvement",
        "dinov2_damaged_similarity",
        "dinov2_restored_similarity",
        "dinov2_similarity_improvement",
        "mean_similarity_improvement",
        "feature_similarity_schema_version",
        "feature_similarity_implementation_name",
        "status",
        "issue",
    ]
    missing_columns = [
        column
        for column in required_columns
        if column not in feature_df.columns
    ]

    validation_rows: list[dict[str, Any]] = [
        {
            "check": "required_columns",
            "passed": not missing_columns,
            "detail": (
                "All required columns present."
                if not missing_columns
                else f"Missing columns: {missing_columns}"
            ),
        }
    ]

    if expected_rows is not None:
        validation_rows.append(
            {
                "check": "row_count",
                "passed": len(feature_df) == expected_rows,
                "detail": f"Expected {expected_rows}, found {len(feature_df)}.",
            }
        )

    if "status" in feature_df.columns:
        error_rows = int((feature_df["status"] == "error").sum())
        validation_rows.append(
            {
                "check": "no_error_rows",
                "passed": error_rows == 0,
                "detail": f"Error rows: {error_rows}.",
            }
        )

    available_key_columns = [
        column
        for column in key_columns
        if column in feature_df.columns
    ]
    if len(available_key_columns) == len(tuple(key_columns)):
        duplicate_rows = int(
            feature_df.duplicated(available_key_columns, keep=False).sum()
        )
        validation_rows.append(
            {
                "check": "unique_feature_keys",
                "passed": duplicate_rows == 0,
                "detail": f"Rows participating in duplicate keys: {duplicate_rows}.",
            }
        )

    if expected_region_counts is not None and "evaluation_region" in feature_df.columns:
        actual_region_counts = feature_df["evaluation_region"].value_counts().to_dict()
        mismatches = {
            region: {
                "expected": expected_count,
                "actual": int(actual_region_counts.get(region, 0)),
            }
            for region, expected_count in expected_region_counts.items()
            if int(actual_region_counts.get(region, 0)) != int(expected_count)
        }
        validation_rows.append(
            {
                "check": "region_counts",
                "passed": not mismatches,
                "detail": (
                    "All evaluation-region counts match expectations."
                    if not mismatches
                    else f"Mismatches: {mismatches}"
                ),
            }
        )

    if "evaluation_region" in feature_df.columns:
        invalid_regions = sorted(
            set(feature_df["evaluation_region"].dropna().astype(str))
            - set(FEATURE_SIMILARITY_EVALUATION_REGIONS)
        )
        invalid_regions = [
            region
            for region in invalid_regions
            if region != "error"
        ]
        validation_rows.append(
            {
                "check": "region_policy",
                "passed": not invalid_regions,
                "detail": (
                    "All feature rows use image-like evaluation regions."
                    if not invalid_regions
                    else f"Invalid feature regions: {invalid_regions}"
                ),
            }
        )

    if "region_pixel_count" in feature_df.columns and "status" in feature_df.columns:
        invalid_counts = int(
            (
                feature_df["status"].eq("ok")
                & feature_df["region_pixel_count"].le(0)
            ).sum()
        )
        validation_rows.append(
            {
                "check": "positive_region_pixel_counts",
                "passed": invalid_counts == 0,
                "detail": (
                    f"Successful rows with non-positive region size: "
                    f"{invalid_counts}."
                ),
            }
        )

    similarity_columns = [
        "clip_damaged_similarity",
        "clip_restored_similarity",
        "dinov2_damaged_similarity",
        "dinov2_restored_similarity",
    ]
    available_similarity_columns = [
        column
        for column in similarity_columns
        if column in feature_df.columns
    ]
    if available_similarity_columns and "status" in feature_df.columns:
        ok_similarity_df = feature_df.loc[
            feature_df["status"].eq("ok"),
            available_similarity_columns,
        ]
        outside_range = int(
            (
                ok_similarity_df.lt(-1.0001)
                | ok_similarity_df.gt(1.0001)
                | ~np.isfinite(ok_similarity_df)
            ).sum().sum()
        )
        validation_rows.append(
            {
                "check": "similarity_value_ranges",
                "passed": outside_range == 0,
                "detail": (
                    "All successful cosine similarities are finite and within [-1, 1]."
                    if outside_range == 0
                    else f"Out-of-range similarity values: {outside_range}."
                ),
            }
        )

    for model_prefix in ("clip", "dinov2"):
        damaged_column = f"{model_prefix}_damaged_similarity"
        restored_column = f"{model_prefix}_restored_similarity"
        improvement_column = f"{model_prefix}_similarity_improvement"
        if {
            damaged_column,
            restored_column,
            improvement_column,
            "status",
        }.issubset(feature_df.columns):
            ok_df = feature_df.loc[feature_df["status"].eq("ok")].copy()
            if ok_df.empty:
                mismatch_count = 0
            else:
                expected_values = (
                    ok_df[restored_column].astype(float)
                    - ok_df[damaged_column].astype(float)
                )
                mismatch_count = int(
                    (
                        ~np.isclose(
                        ok_df[improvement_column].astype(float),
                        expected_values,
                        atol=1e-7,
                        equal_nan=True,
                    )
                    ).sum()
                )
            validation_rows.append(
                {
                    "check": f"{model_prefix}_improvement_direction",
                    "passed": mismatch_count == 0,
                    "detail": (
                        f"{improvement_column} equals restored - damaged."
                        if mismatch_count == 0
                        else f"Improvement mismatch rows: {mismatch_count}."
                    ),
                }
            )

    return pd.DataFrame(validation_rows)


def summarize_feature_similarity_metrics(
    feature_df: pd.DataFrame,
    group_columns: list[str],
) -> pd.DataFrame:
    """Summarize feature-similarity metrics for notebook display and reports."""
    if not group_columns:
        raise ValueError("At least one group column is required.")

    missing_group_columns = [
        column
        for column in group_columns
        if column not in feature_df.columns
    ]
    if missing_group_columns:
        raise ValueError(
            f"Feature dataframe missing group columns: {missing_group_columns}"
        )

    summary_df = feature_df.copy()
    if "status" in summary_df.columns:
        summary_df = summary_df[summary_df["status"] != "error"].copy()

    return (
        summary_df
        .groupby(group_columns, dropna=False, sort=False)
        .agg(
            rows=("feature_row_id", "count"),
            cases=("feature_case_id", "nunique"),
            median_clip_damaged_similarity=("clip_damaged_similarity", "median"),
            median_clip_restored_similarity=("clip_restored_similarity", "median"),
            median_clip_similarity_improvement=("clip_similarity_improvement", "median"),
            mean_clip_damaged_similarity=("clip_damaged_similarity", "mean"),
            mean_clip_restored_similarity=("clip_restored_similarity", "mean"),
            mean_clip_similarity_improvement=("clip_similarity_improvement", "mean"),
            clip_improvement_rate=("clip_similarity_improvement", lambda values: (values > 0).mean()),
            median_dinov2_damaged_similarity=("dinov2_damaged_similarity", "median"),
            median_dinov2_restored_similarity=("dinov2_restored_similarity", "median"),
            median_dinov2_similarity_improvement=("dinov2_similarity_improvement", "median"),
            mean_dinov2_damaged_similarity=("dinov2_damaged_similarity", "mean"),
            mean_dinov2_restored_similarity=("dinov2_restored_similarity", "mean"),
            mean_dinov2_similarity_improvement=("dinov2_similarity_improvement", "mean"),
            dinov2_improvement_rate=("dinov2_similarity_improvement", lambda values: (values > 0).mean()),
            mean_similarity_improvement=("mean_similarity_improvement", "mean"),
            median_region_pixel_count=("region_pixel_count", "median"),
        )
        .reset_index()
        .round(6)
    )


def rank_feature_similarity_cases(
    feature_df: pd.DataFrame,
    evaluation_region: str = "mask_bbox_crop",
    metric: str = "dinov2_similarity_improvement",
    top_n: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return strongest and weakest cases by feature-similarity improvement."""
    if metric not in feature_df.columns:
        raise ValueError(f"Metric column not found: {metric}")

    region_df = (
        feature_df.loc[
            feature_df["evaluation_region"].eq(evaluation_region)
            & feature_df["status"].eq("ok")
        ]
        .copy()
    )

    strongest_df = (
        region_df
        .sort_values(
            [metric, "feature_case_id"],
            ascending=[False, True],
            kind="stable",
        )
        .head(top_n)
        .reset_index(drop=True)
    )

    weakest_df = (
        region_df
        .sort_values(
            [metric, "feature_case_id"],
            ascending=[True, True],
            kind="stable",
        )
        .head(top_n)
        .reset_index(drop=True)
    )

    return strongest_df, weakest_df
