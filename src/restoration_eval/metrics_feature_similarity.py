"""Deduplicated CLIP and DINOv2 evidence for restoration evaluation.

Notebook 15 evaluates only the canonical contiguous ``content_region`` and
``mask_bbox_crop`` inputs, retains normalized dense embeddings, and constructs
candidate-level cosine-similarity evidence from reusable clean, damaged, and
restored vectors. These general-purpose encoders are diagnostic rather than
conservation-specific quality judges.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import math
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd
from PIL import Image

from .regions import Region, content_region, mask_bbox_region, metric_region_is_valid
from .schemas import (
    FEATURE_EMBEDDING_MANIFEST_COLUMNS,
    FEATURE_EMBEDDING_MANIFEST_SCHEMA,
    FEATURE_METRICS_COLUMNS,
    FEATURE_METRICS_SCHEMA,
    validate_dataframe,
)


FEATURE_SIMILARITY_MODULE_VERSION = "3.0.1"
FEATURE_METRIC_VERSION = "feature_cosine_similarity.v1"
FEATURE_METRICS_SCHEMA_VERSION = "feature_metrics.v1"
FEATURE_EMBEDDING_SCHEMA_VERSION = "feature_embedding_manifest.v1"
FEATURE_ACTIVE_REGIONS = ("content_region", "mask_bbox_crop")
FEATURE_MODEL_IDS = ("clip_vit_b32", "dinov2_vits14")
IMAGE_ROLES = ("clean", "damaged", "restored")
DEFAULT_CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"
DEFAULT_CLIP_MODEL_REVISION = "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268"
DEFAULT_DINOV2_MODEL_NAME = "dinov2_vits14"
DEFAULT_DINOV2_MODEL_REVISION = "facebookresearch_dinov2_main_published_checkpoint"

FEATURE_EXECUTION_PLAN_COLUMNS = (
    "case_id", "candidate_id", "model_id", "painting_id", "region_id",
    "region_pixel_count", "region_width", "region_height", "crop_x_min",
    "crop_y_min", "crop_x_max", "crop_y_max", "clean_image_path",
    "input_image_path", "restored_path", "clean_sha256", "input_sha256",
    "restored_sha256", "is_zero_control",
)
FEATURE_EMBEDDING_PLAN_INTERNAL_COLUMNS = (
    *FEATURE_EMBEDDING_MANIFEST_COLUMNS,
    "crop_x_min", "crop_y_min", "crop_x_max", "crop_y_max",
)
SCRATCH_PROMPT_PAIR_COLUMNS = (
    "case_id", "painting_id", "seed", "region_id", "feature_model_id",
    "generic_candidate_id", "scratch_aware_candidate_id",
    "generic_improvement_value", "scratch_aware_improvement_value",
    "scratch_aware_minus_generic",
)

ProgressCallback = Callable[[str], None]
CheckpointCallback = Callable[[pd.DataFrame, np.ndarray], None]
EncodeBatch = Callable[[Sequence[Image.Image]], np.ndarray]


@dataclass(frozen=True)
class FeatureModelSpec:
    """Resolved, auditable contract for one feature encoder."""

    feature_model_id: str
    metric_name: str
    model_name: str
    model_revision: str
    model_checksum: str
    embedding_dimension: int
    array_name: str
    preprocessing_id: str
    input_size: int
    package_name: str


@dataclass(frozen=True)
class FeatureEmbeddingRunResult:
    """One model's dense matrix, canonical manifest rows, and run summary."""

    manifest: pd.DataFrame
    matrix: np.ndarray
    summary: Mapping[str, Any]


def get_package_version(package_name: str) -> str:
    """Return an installed distribution version without importing it."""

    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def validate_feature_similarity_runtime_dependencies() -> pd.DataFrame:
    """Return explicit availability evidence for Notebook 15 dependencies."""

    records = []
    for module_name, package_name in (
        ("torch", "torch"), ("torchvision", "torchvision"),
        ("transformers", "transformers"), ("yaml", "PyYAML"),
        ("PIL", "Pillow"),
    ):
        installed = importlib.util.find_spec(module_name) is not None
        records.append({
            "component": package_name, "module": module_name,
            "version": get_package_version(package_name), "required": True,
            "installed": installed, "passed": installed,
        })
    return pd.DataFrame(records)


def load_feature_similarity_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the versioned Notebook 15 YAML contract."""

    yaml = importlib.import_module("yaml")
    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Feature-similarity configuration must be a mapping")
    if config.get("config_schema_version") != "feature_similarity_config.v1":
        raise ValueError("Unexpected feature-similarity configuration schema")
    settings = config.get("feature_similarity")
    if not isinstance(settings, dict):
        raise ValueError("Configuration is missing feature_similarity settings")
    if settings.get("metric_version") != FEATURE_METRIC_VERSION:
        raise ValueError("Configuration metric version does not match the helper")
    if settings.get("output_schema_version") != FEATURE_METRICS_SCHEMA_VERSION:
        raise ValueError("Configuration feature-metric schema does not match")
    if settings.get("embedding_schema_version") != FEATURE_EMBEDDING_SCHEMA_VERSION:
        raise ValueError("Configuration embedding schema does not match")
    active = tuple(settings.get("regions", {}).get("active_regions", ()))
    if active != FEATURE_ACTIVE_REGIONS:
        raise ValueError(f"Active feature regions must be exactly {FEATURE_ACTIVE_REGIONS}")
    if tuple(settings.get("models", {}).keys()) != FEATURE_MODEL_IDS:
        raise ValueError(f"Feature models must be exactly {FEATURE_MODEL_IDS}")
    specs = feature_model_specs(config)
    if len({spec.array_name for spec in specs.values()}) != len(specs):
        raise ValueError("Feature-model NPZ array names must be unique")
    if len({spec.metric_name for spec in specs.values()}) != len(specs):
        raise ValueError("Feature-model metric names must be unique")
    return config


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    settings = config.get("feature_similarity", config)
    if not isinstance(settings, Mapping):
        raise TypeError("feature_similarity settings must be a mapping")
    return settings


def feature_model_specs(config: Mapping[str, Any]) -> dict[str, FeatureModelSpec]:
    """Resolve compact model specs from configuration."""

    result: dict[str, FeatureModelSpec] = {}
    for feature_model_id, raw in _settings(config)["models"].items():
        spec = FeatureModelSpec(
            feature_model_id=str(raw["feature_model_id"]),
            metric_name=str(raw["metric_name"]), model_name=str(raw["model_name"]),
            model_revision=str(raw["model_revision"]),
            model_checksum=str(raw["model_checksum_sha256"]),
            embedding_dimension=int(raw["embedding_dimension"]),
            array_name=str(raw["array_name"]),
            preprocessing_id=str(raw["preprocessing_id"]),
            input_size=int(raw["input_size"]), package_name=str(raw["package_name"]),
        )
        if spec.feature_model_id != feature_model_id:
            raise ValueError(f"Feature-model key/id mismatch: {feature_model_id}")
        if spec.embedding_dimension <= 0 or spec.input_size <= 0:
            raise ValueError(f"Invalid dimensions for {feature_model_id}")
        if len(spec.model_checksum) != 64:
            raise ValueError(f"Invalid model checksum for {feature_model_id}")
        result[feature_model_id] = spec
    return result


def resolve_feature_device(config: Mapping[str, Any]) -> str:
    """Resolve CUDA preference with the approved explicit CPU fallback."""

    torch = importlib.import_module("torch")
    execution = _settings(config)["execution"]
    preferred = str(execution["preferred_device"]).lower()
    if preferred == "cuda" and torch.cuda.is_available():
        return "cuda"
    if preferred == "cuda" and not bool(execution["allow_cpu_fallback"]):
        raise RuntimeError("CUDA was requested but is unavailable and fallback is disabled")
    return "cpu"


def configure_feature_determinism(config: Mapping[str, Any]) -> None:
    """Configure deterministic inference without forcing unsupported kernels."""

    torch = importlib.import_module("torch")
    enabled = bool(_settings(config)["execution"]["deterministic_algorithms"])
    if hasattr(torch, "use_deterministic_algorithms"):
        torch.use_deterministic_algorithms(enabled, warn_only=True)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.benchmark = False


def get_device(prefer_cuda: bool = True) -> Any:
    """Compatibility wrapper returning a torch device."""

    torch = importlib.import_module("torch")
    return torch.device("cuda" if prefer_cuda and torch.cuda.is_available() else "cpu")


def resolve_local_hf_snapshot(
    model_name: str,
    revision: str,
    *,
    cache_root: str | Path | None = None,
) -> Path | None:
    """Resolve one exact Hugging Face snapshot without network discovery.

    Passing the snapshot directory itself to Transformers avoids a 4.48.x
    Windows cache edge case where the processor resolves correctly but the
    cached PyTorch checkpoint is returned as ``None``.
    """

    if cache_root is None:
        huggingface_home = Path(
            os.environ.get(
                "HF_HOME",
                Path.home() / ".cache" / "huggingface",
            )
        )
        hub_root = huggingface_home / "hub"
    else:
        root = Path(cache_root)
        hub_root = root if root.name == "hub" else root / "hub"
    storage_name = "models--" + str(model_name).replace("/", "--")
    snapshot = hub_root / storage_name / "snapshots" / str(revision)
    return snapshot if snapshot.is_dir() else None


def load_clip_model_and_processor(
    model_name: str = DEFAULT_CLIP_MODEL_NAME, device: Any | None = None,
    revision: str | None = DEFAULT_CLIP_MODEL_REVISION, *,
    local_files_only: bool = True,
) -> tuple[Any, Any]:
    """Load pinned CLIP model and native processor lazily."""

    transformers = importlib.import_module("transformers")
    if device is None:
        device = get_device()
    source: str | Path = model_name
    kwargs: dict[str, Any] = {"local_files_only": bool(local_files_only)}
    if revision:
        kwargs["revision"] = revision
    if local_files_only and revision:
        snapshot = resolve_local_hf_snapshot(model_name, revision)
        if snapshot is not None:
            source = snapshot
            kwargs.pop("revision", None)
    processor = transformers.CLIPProcessor.from_pretrained(str(source), **kwargs)
    model = transformers.CLIPModel.from_pretrained(
        str(source), use_safetensors=False, **kwargs
    ).to(device)
    model.eval()
    return model, processor


def _cached_dinov2_repository() -> Path | None:
    torch = importlib.import_module("torch")
    candidate = Path(torch.hub.get_dir()) / "facebookresearch_dinov2_main"
    return candidate if candidate.is_dir() else None


def load_dinov2_model(
    model_name: str = DEFAULT_DINOV2_MODEL_NAME, device: Any | None = None,
    repo_or_dir: str = "facebookresearch/dinov2", trust_repo: bool = True, *,
    local_only: bool = True,
) -> Any:
    """Load DINOv2 lazily, preferring the existing torch-hub snapshot."""

    torch = importlib.import_module("torch")
    if device is None:
        device = get_device()
    local_repo = Path(repo_or_dir)
    if not local_repo.is_dir() and local_only:
        cached = _cached_dinov2_repository()
        if cached is None:
            raise FileNotFoundError("Cached facebookresearch/dinov2 repository not found")
        local_repo = cached
    if local_repo.is_dir():
        model = torch.hub.load(
            str(local_repo), model_name, source="local", verbose=False,
            trust_repo=trust_repo,
        )
    else:
        model = torch.hub.load(repo_or_dir, model_name, verbose=False, trust_repo=trust_repo)
    model = model.to(device)
    model.eval()
    return model


def load_configured_feature_models(
    config: Mapping[str, Any], *, device: str, local_only: bool = True,
) -> dict[str, dict[str, Any]]:
    """Load both approved encoders and exact preprocessing objects."""

    specs = feature_model_specs(config)
    clip_spec = specs["clip_vit_b32"]
    clip_model, clip_processor = load_clip_model_and_processor(
        clip_spec.model_name, device, clip_spec.model_revision,
        local_files_only=local_only,
    )
    dino_spec = specs["dinov2_vits14"]
    dino_model = load_dinov2_model(dino_spec.model_name, device, local_only=local_only)
    return {
        "clip_vit_b32": {
            "spec": clip_spec, "model": clip_model, "processor": clip_processor,
        },
        "dinov2_vits14": {
            "spec": dino_spec, "model": dino_model,
            "transform": build_dinov2_transform(config),
        },
    }


def build_dinov2_transform(config: Mapping[str, Any]) -> Any:
    """Build the documented official DINOv2 evaluation preprocessing."""

    transforms = importlib.import_module("torchvision.transforms")
    raw = _settings(config)["models"]["dinov2_vits14"]
    return transforms.Compose([
        transforms.Resize(
            int(raw["resize_shorter_side"]),
            interpolation=transforms.InterpolationMode.BICUBIC,
        ),
        transforms.CenterCrop(int(raw["input_size"])), transforms.ToTensor(),
        transforms.Normalize(
            mean=tuple(float(value) for value in raw["normalization_mean"]),
            std=tuple(float(value) for value in raw["normalization_std"]),
        ),
    ])


def _normalized_numpy(features: Any, expected_dimension: int) -> np.ndarray:
    if hasattr(features, "pooler_output"):
        features = features.pooler_output
    elif hasattr(features, "last_hidden_state"):
        features = features.last_hidden_state[:, 0]
    if isinstance(features, Mapping):
        for key in ("x_norm_clstoken", "pooler_output", "last_hidden_state"):
            if key in features:
                features = features[key]
                if key == "last_hidden_state":
                    features = features[:, 0]
                break
    values = (
        features.detach().float().cpu().numpy()
        if hasattr(features, "detach") else np.asarray(features, dtype=np.float32)
    )
    values = np.asarray(values, dtype=np.float32)
    if values.ndim == 1:
        values = values[None, :]
    if values.ndim != 2 or values.shape[1] != int(expected_dimension):
        raise ValueError(
            f"Unexpected embedding shape {values.shape}; expected (*, {expected_dimension})"
        )
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    if np.any(~np.isfinite(norms)) or np.any(norms <= 0):
        raise ValueError("Feature encoder produced zero or non-finite embeddings")
    return (values / norms).astype(np.float32, copy=False)


def encode_feature_batch(
    images: Sequence[Image.Image], bundle: Mapping[str, Any], *, device: str,
) -> np.ndarray:
    """Encode and L2-normalize one batch using an approved model bundle."""

    torch = importlib.import_module("torch")
    spec: FeatureModelSpec = bundle["spec"]
    if spec.feature_model_id == "clip_vit_b32":
        inputs = bundle["processor"](images=list(images), return_tensors="pt", padding=True)
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.inference_mode():
            features = bundle["model"].get_image_features(**inputs)
    elif spec.feature_model_id == "dinov2_vits14":
        batch = torch.stack([bundle["transform"](image) for image in images]).to(device)
        with torch.inference_mode():
            features = bundle["model"](batch)
    else:
        raise ValueError(f"Unsupported feature model: {spec.feature_model_id}")
    return _normalized_numpy(features, spec.embedding_dimension)


def load_rgb_array(path: str | Path) -> np.ndarray:
    """Load one image as an HxWx3 uint8 RGB array."""

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


def load_mask_array(path: str | Path) -> np.ndarray:
    """Load one mask/effect-support image as an HxW uint8 array."""

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    with Image.open(path) as image:
        return np.asarray(image.convert("L"), dtype=np.uint8)


def _resolve(project_root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(project_root) / path


def file_sha256(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def build_case_feature_regions(
    case: Mapping[str, Any], raw_mask: np.ndarray, config: Mapping[str, Any],
) -> dict[str, Region]:
    """Build only the two approved rectangular regions via ``regions.py``."""

    active_mask = np.asarray(raw_mask) >= int(case["mask_threshold"])
    content_bbox = tuple(int(case[column]) for column in (
        "content_x_min", "content_y_min", "content_x_max", "content_y_max"
    ))
    region_settings = _settings(config)["regions"]
    candidates = {
        "content_region": content_region(active_mask.shape, content_bbox),
        "mask_bbox_crop": mask_bbox_region(
            active_mask, margin=int(region_settings["mask_bbox_margin_pixels"]),
            support_bbox=content_bbox,
        ),
    }
    result: dict[str, Region] = {}
    for region_id in region_settings["active_regions"]:
        region = candidates[region_id]
        valid, reason = metric_region_is_valid("clip", region)
        if valid:
            result[region_id] = region
        elif region_id == "content_region":
            raise ValueError(f"Invalid mandatory content region: {reason}")
    return result


def build_feature_execution_plan(
    worklist: pd.DataFrame, *, project_root: str | Path,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build exact candidate-region keys without loading restoration pixels."""

    required = {
        "case_id", "candidate_id", "model_id", "painting_id", "mask_threshold",
        "mask_or_effect_path", "content_x_min", "content_y_min", "content_x_max",
        "content_y_max", "clean_image_path", "input_image_path", "restored_path",
        "restored_sha256", "is_zero_control",
    }
    missing = sorted(required - set(worklist.columns))
    if missing:
        raise ValueError(f"Evaluation worklist is missing columns: {missing}")
    records: list[dict[str, Any]] = []
    root = Path(project_root)
    for case_id, group in worklist.groupby("case_id", sort=False):
        if group["mask_threshold"].astype(int).nunique() != 1:
            raise ValueError(f"Case {case_id} has inconsistent mask thresholds")
        case = group.iloc[0]
        mask = load_mask_array(_resolve(root, case["mask_or_effect_path"]))
        regions = build_case_feature_regions(case, mask, config)
        for candidate in group.itertuples(index=False):
            for region in regions.values():
                if region.bbox is None:
                    raise ValueError(f"Rectangular region {region.region_id} has no bbox")
                x0, y0, x1, y1 = region.bbox
                records.append({
                    "case_id": str(candidate.case_id), "candidate_id": str(candidate.candidate_id),
                    "model_id": str(candidate.model_id), "painting_id": str(candidate.painting_id),
                    "region_id": region.region_id, "region_pixel_count": int(region.pixel_count),
                    "region_width": int(region.width), "region_height": int(region.height),
                    "crop_x_min": int(x0), "crop_y_min": int(y0),
                    "crop_x_max": int(x1), "crop_y_max": int(y1),
                    "clean_image_path": str(candidate.clean_image_path),
                    "input_image_path": str(candidate.input_image_path),
                    "restored_path": str(candidate.restored_path),
                    "clean_sha256": str(getattr(candidate, "clean_sha256", "")),
                    "input_sha256": str(getattr(candidate, "input_sha256", "")),
                    "restored_sha256": str(candidate.restored_sha256),
                    "is_zero_control": bool(candidate.is_zero_control),
                })
    return pd.DataFrame(records, columns=FEATURE_EXECUTION_PLAN_COLUMNS)


def embedding_id_for(
    feature_model_id: str, image_role: str, *, painting_id: str,
    case_id: str, candidate_id: str, region_id: str,
) -> str:
    """Return a deterministic ID following the approved role deduplication."""

    if image_role == "clean" and region_id == "content_region":
        identity = f"painting:{painting_id}"
    elif image_role in {"clean", "damaged"}:
        identity = f"case:{case_id}"
    elif image_role == "restored":
        identity = f"candidate:{candidate_id}"
    else:
        raise ValueError(f"Unsupported image role: {image_role}")
    payload = "|".join((feature_model_id, image_role, identity, region_id))
    return f"fe__{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20]}"


def build_feature_embedding_plan(
    execution_plan: pd.DataFrame, *, config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the exact deduplicated embedding manifest/extraction plan."""

    missing = sorted(set(FEATURE_EXECUTION_PLAN_COLUMNS) - set(execution_plan.columns))
    if missing:
        raise ValueError(f"Feature execution plan is missing columns: {missing}")
    records: list[dict[str, Any]] = []
    for spec in feature_model_specs(config).values():
        seen: set[str] = set()
        array_index = 0
        for row in execution_plan.itertuples(index=False):
            role_values = {
                "clean": (row.clean_image_path, row.clean_sha256),
                "damaged": (row.input_image_path, row.input_sha256),
                "restored": (row.restored_path, row.restored_sha256),
            }
            for role in IMAGE_ROLES:
                embedding_id = embedding_id_for(
                    spec.feature_model_id, role, painting_id=str(row.painting_id),
                    case_id=str(row.case_id), candidate_id=str(row.candidate_id),
                    region_id=str(row.region_id),
                )
                if embedding_id in seen:
                    continue
                seen.add(embedding_id)
                source_path, source_sha256 = role_values[role]
                records.append({
                    "embedding_id": embedding_id, "feature_model_id": spec.feature_model_id,
                    "image_role": role, "painting_id": str(row.painting_id),
                    "case_id": ("" if role == "clean" and row.region_id == "content_region"
                                else str(row.case_id)),
                    "representative_candidate_id": (str(row.candidate_id)
                                                       if role == "restored" else ""),
                    "region_id": str(row.region_id),
                    "source_path": str(source_path).replace("\\", "/"),
                    "source_sha256": str(source_sha256), "array_name": spec.array_name,
                    "array_index": array_index, "embedding_dimension": spec.embedding_dimension,
                    "dtype": "float32", "preprocessing_id": spec.preprocessing_id,
                    "input_width": spec.input_size, "input_height": spec.input_size,
                    "model_name": spec.model_name, "model_revision": spec.model_revision,
                    "model_checksum": spec.model_checksum,
                    "schema_version": FEATURE_EMBEDDING_SCHEMA_VERSION,
                    "status": "", "issue": "", "crop_x_min": int(row.crop_x_min),
                    "crop_y_min": int(row.crop_y_min), "crop_x_max": int(row.crop_x_max),
                    "crop_y_max": int(row.crop_y_max),
                })
                array_index += 1
    return pd.DataFrame(records, columns=FEATURE_EMBEDDING_PLAN_INTERNAL_COLUMNS)


def populate_missing_source_checksums(
    embedding_plan: pd.DataFrame, *, project_root: str | Path,
) -> pd.DataFrame:
    """Fill missing source SHA-256 values once per unique path."""

    result = embedding_plan.copy()
    cache: dict[str, str] = {}
    for index, row in result.iterrows():
        value = str(row["source_sha256"]).strip().lower()
        if len(value) == 64 and all(char in "0123456789abcdef" for char in value):
            continue
        source = str(row["source_path"])
        if source not in cache:
            cache[source] = file_sha256(_resolve(project_root, source))
        result.at[index, "source_sha256"] = cache[source]
    return result


def _load_cropped_pil(row: Any, project_root: str | Path) -> Image.Image:
    array = load_rgb_array(_resolve(project_root, row.source_path))
    x0, y0, x1, y1 = (int(row.crop_x_min), int(row.crop_y_min),
                      int(row.crop_x_max), int(row.crop_y_max))
    if not (0 <= x0 < x1 <= array.shape[1] and 0 <= y0 < y1 <= array.shape[0]):
        raise ValueError(f"Invalid crop {(x0, y0, x1, y1)} for {row.source_path}")
    return Image.fromarray(array[y0:y1, x0:x1], mode="RGB")


def _is_cuda_oom(exc: BaseException) -> bool:
    text = str(exc).lower()
    return isinstance(exc, RuntimeError) and (
        "out of memory" in text or "cuda error: memory" in text
    )


def _clear_cuda_cache() -> None:
    try:
        torch = importlib.import_module("torch")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def extract_feature_model_embeddings(
    model_plan: pd.DataFrame, *, spec: FeatureModelSpec,
    encode_batch: EncodeBatch, project_root: str | Path,
    config: Mapping[str, Any], matrix_path: str | Path | None = None,
    prior_manifest: pd.DataFrame | None = None,
    progress_callback: ProgressCallback | None = None,
    checkpoint_callback: CheckpointCallback | None = None,
) -> FeatureEmbeddingRunResult:
    """Extract one normalized dense matrix with OOM backoff and safe resume."""

    plan = model_plan.loc[
        model_plan["feature_model_id"].astype(str).eq(spec.feature_model_id)
    ].copy().sort_values("array_index", kind="stable").reset_index(drop=True)
    if plan.empty:
        raise ValueError(f"No embedding rows planned for {spec.feature_model_id}")
    if not np.array_equal(plan["array_index"].to_numpy(int), np.arange(len(plan))):
        raise ValueError("Embedding array indices must be contiguous from zero")
    shape = (len(plan), spec.embedding_dimension)
    if matrix_path is None:
        matrix: np.ndarray = np.full(shape, np.nan, dtype=np.float32)
    else:
        target = Path(matrix_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            matrix = np.lib.format.open_memmap(target, mode="r+")
            if tuple(matrix.shape) != shape or matrix.dtype != np.float32:
                raise ValueError(f"Checkpoint matrix contract mismatch: {target}")
        else:
            matrix = np.lib.format.open_memmap(target, mode="w+", dtype=np.float32, shape=shape)
            matrix[:] = np.nan
            matrix.flush()

    status = np.full(len(plan), "", dtype=object)
    issues = np.full(len(plan), "", dtype=object)
    reused = 0
    if prior_manifest is not None and not prior_manifest.empty:
        prior = prior_manifest.loc[
            prior_manifest["feature_model_id"].astype(str).eq(spec.feature_model_id)
        ].set_index("embedding_id", drop=False)
        for number, row in enumerate(plan.itertuples(index=False)):
            if row.embedding_id not in prior.index:
                continue
            previous = prior.loc[row.embedding_id]
            if isinstance(previous, pd.DataFrame):
                raise ValueError(f"Duplicate prior embedding ID: {row.embedding_id}")
            matches = all((
                str(previous["model_revision"]) == spec.model_revision,
                str(previous["model_checksum"]) == spec.model_checksum,
                str(previous["preprocessing_id"]) == spec.preprocessing_id,
                int(previous["array_index"]) == int(row.array_index),
                str(previous["status"]) == "ok",
            ))
            vector = np.asarray(matrix[int(row.array_index)], dtype=np.float32)
            if matches and np.isfinite(vector).all():
                status[number] = "ok"
                reused += 1

    execution = _settings(config)["execution"]
    sizes = [int(execution["initial_batch_size"])] + [
        int(value) for value in execution["oom_batch_size_backoff"]
    ]
    batch_sizes: list[int] = []
    for value in sizes:
        if value > 0 and value not in batch_sizes:
            batch_sizes.append(value)
    progress_interval = int(execution["progress_interval_embeddings"])
    checkpoint_interval = int(execution["checkpoint_interval_embeddings"])
    current_size_index = 0
    failures = 0
    processed_since_checkpoint = 0
    started = time.perf_counter()
    pending = [number for number in range(len(plan)) if status[number] != "ok"]
    cursor = 0
    while cursor < len(pending):
        batch_size = batch_sizes[current_size_index]
        indices = pending[cursor:cursor + batch_size]
        rows = [plan.iloc[number] for number in indices]
        try:
            images = [_load_cropped_pil(row, project_root) for row in rows]
            vectors = _normalized_numpy(encode_batch(images), spec.embedding_dimension)
            if vectors.shape != (len(rows), spec.embedding_dimension):
                raise ValueError(f"Encoder returned unexpected shape {vectors.shape}")
            for number, vector in zip(indices, vectors):
                matrix[int(plan.iloc[number]["array_index"])] = vector
                status[number] = "ok"
                issues[number] = ""
            cursor += len(indices)
            processed_since_checkpoint += len(indices)
        except Exception as exc:
            if _is_cuda_oom(exc) and current_size_index + 1 < len(batch_sizes):
                current_size_index += 1
                _clear_cuda_cache()
                continue
            issue = f"{type(exc).__name__}: {exc}"
            for number in indices:
                status[number] = "error"
                issues[number] = issue
                matrix[int(plan.iloc[number]["array_index"])] = np.nan
                failures += 1
            cursor += len(indices)
            processed_since_checkpoint += len(indices)

        observed = reused + cursor
        manifest = plan.loc[:, FEATURE_EMBEDDING_MANIFEST_COLUMNS].copy()
        manifest["status"] = status
        manifest["issue"] = issues
        if hasattr(matrix, "flush"):
            matrix.flush()
        if checkpoint_callback is not None and (
            processed_since_checkpoint >= checkpoint_interval or cursor == len(pending)
        ):
            checkpoint_callback(manifest, matrix)
            processed_since_checkpoint = 0
        if progress_callback is not None and (
            observed % progress_interval < len(indices) or cursor == len(pending)
        ):
            elapsed = time.perf_counter() - started
            throughput = cursor / max(elapsed, 1e-9)
            progress_callback(
                f"{spec.feature_model_id}: {observed}/{len(plan)} embeddings "
                f"({100.0 * observed / len(plan):.1f}%), elapsed={elapsed:.1f}s, "
                f"throughput={throughput:.2f} new embeddings/s, batch_size={batch_size}, "
                f"reused={reused}, failures={failures}, latest={rows[-1]['embedding_id']}"
            )

    final_manifest = plan.loc[:, FEATURE_EMBEDDING_MANIFEST_COLUMNS].copy()
    final_manifest["status"] = status
    final_manifest["issue"] = issues
    return FeatureEmbeddingRunResult(final_manifest, matrix, {
        "feature_model_id": spec.feature_model_id, "embedding_count": len(plan),
        "completed_count": int(np.count_nonzero(status == "ok")),
        "error_count": int(np.count_nonzero(status == "error")),
        "reused_count": reused, "new_count": len(pending),
        "final_batch_size": batch_sizes[current_size_index],
        "runtime_seconds": time.perf_counter() - started,
    })


def metric_row_id(
    case_id: str, candidate_id: str, feature_model_id: str, region_id: str,
    metric_version: str = FEATURE_METRIC_VERSION,
) -> str:
    payload = "|".join((case_id, candidate_id, feature_model_id, region_id, metric_version))
    return f"fm__{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20]}"


def _embedding_lookup(manifest: pd.DataFrame) -> dict[str, tuple[str, int, str]]:
    if manifest["embedding_id"].astype(str).duplicated().any():
        raise ValueError("Embedding manifest contains duplicate embedding IDs")
    return {
        str(row.embedding_id): (str(row.array_name), int(row.array_index), str(row.status))
        for row in manifest.itertuples(index=False)
    }


def construct_feature_metrics(
    execution_plan: pd.DataFrame, embedding_manifest: pd.DataFrame,
    arrays: Mapping[str, np.ndarray], *, config: Mapping[str, Any],
    device: str, package_versions: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Construct normalized long-form cosine metrics from retained vectors."""

    lookup = _embedding_lookup(embedding_manifest)
    versions = dict(package_versions or {})
    records: list[dict[str, Any]] = []
    for row in execution_plan.itertuples(index=False):
        for spec in feature_model_specs(config).values():
            ids = {role: embedding_id_for(
                spec.feature_model_id, role, painting_id=str(row.painting_id),
                case_id=str(row.case_id), candidate_id=str(row.candidate_id),
                region_id=str(row.region_id),
            ) for role in IMAGE_ROLES}
            damaged_value = restored_value = improvement = math.nan
            issue = ""
            try:
                vectors: dict[str, np.ndarray] = {}
                for role, embedding_id in ids.items():
                    array_name, array_index, embedding_status = lookup[embedding_id]
                    if embedding_status != "ok":
                        raise ValueError(f"{role} embedding status is {embedding_status}")
                    vectors[role] = np.asarray(arrays[array_name][array_index], dtype=np.float32)
                damaged_value = float(np.dot(vectors["clean"], vectors["damaged"]))
                restored_value = float(np.dot(vectors["clean"], vectors["restored"]))
                improvement = restored_value - damaged_value
                status = "ok"
            except Exception as exc:
                status = "error"
                issue = f"{type(exc).__name__}: {exc}"
            records.append({
                "metric_row_id": metric_row_id(
                    str(row.case_id), str(row.candidate_id), spec.feature_model_id,
                    str(row.region_id),
                ),
                "case_id": str(row.case_id), "candidate_id": str(row.candidate_id),
                "model_id": str(row.model_id), "metric_family": "feature_similarity",
                "metric_name": spec.metric_name, "feature_model_id": spec.feature_model_id,
                "region_id": str(row.region_id), "region_pixel_count": int(row.region_pixel_count),
                "region_width": int(row.region_width), "region_height": int(row.region_height),
                "damaged_embedding_id": ids["damaged"],
                "restored_embedding_id": ids["restored"], "clean_embedding_id": ids["clean"],
                "damaged_value": damaged_value, "restored_value": restored_value,
                "improvement_value": improvement,
                "improvement_direction": "restored_minus_damaged",
                "metric_version": FEATURE_METRIC_VERSION,
                "region_policy_version": str(_settings(config)["regions"]["policy_version"]),
                "preprocessing_id": spec.preprocessing_id, "input_size": spec.input_size,
                "model_name": spec.model_name, "model_revision": spec.model_revision,
                "model_checksum": spec.model_checksum,
                "schema_version": FEATURE_METRICS_SCHEMA_VERSION, "device": str(device),
                "package_version": versions.get(
                    spec.package_name, get_package_version(spec.package_name)
                ),
                "status": status, "issue": issue,
            })
    return pd.DataFrame(records, columns=FEATURE_METRICS_COLUMNS)


def validate_feature_embedding_manifest(
    manifest: pd.DataFrame, arrays: Mapping[str, np.ndarray], *,
    config: Mapping[str, Any], expected_plan: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Validate schema, coverage, matrices, dtype, indices, checksums, and norms."""

    schema = validate_dataframe(
        manifest, FEATURE_EMBEDDING_MANIFEST_SCHEMA, allow_extra_columns=False
    )
    expected_ids = (set(expected_plan["embedding_id"].astype(str))
                    if expected_plan is not None
                    else set(manifest["embedding_id"].astype(str)))
    observed_ids = set(manifest["embedding_id"].astype(str))
    matrix_failures = index_failures = norm_failures = checksum_failures = 0
    tolerance = float(
        _settings(config)["finite_value_policy"]["normalized_embedding_norm_tolerance"]
    )
    for spec in feature_model_specs(config).values():
        rows = manifest.loc[
            manifest["feature_model_id"].astype(str).eq(spec.feature_model_id)
        ]
        array = arrays.get(spec.array_name)
        if array is None or tuple(array.shape) != (len(rows), spec.embedding_dimension):
            matrix_failures += 1
            continue
        if np.asarray(array).dtype != np.float32 or not np.isfinite(array).all():
            matrix_failures += 1
        indices = rows["array_index"].to_numpy(dtype=int)
        if not np.array_equal(np.sort(indices), np.arange(len(rows), dtype=int)):
            index_failures += 1
        norms = np.linalg.norm(np.asarray(array, dtype=np.float32), axis=1)
        norm_failures += int((np.abs(norms - 1.0) > tolerance).sum())
        checksum_failures += int((~rows["source_sha256"].astype(str)
                                  .str.fullmatch(r"[0-9a-f]{64}")).sum())
    error_rows = int(manifest["status"].astype(str).eq("error").sum())
    passed = bool(
        schema.passed and expected_ids == observed_ids and matrix_failures == 0
        and index_failures == 0 and norm_failures == 0
        and checksum_failures == 0 and error_rows == 0
    )
    return {
        "schema": schema.to_dict(), "row_count": len(manifest),
        "expected_row_count": len(expected_ids),
        "missing_embedding_id_count": len(expected_ids - observed_ids),
        "unexpected_embedding_id_count": len(observed_ids - expected_ids),
        "matrix_failure_count": matrix_failures,
        "array_index_failure_count": index_failures,
        "embedding_norm_failure_count": norm_failures,
        "source_checksum_failure_count": checksum_failures,
        "error_row_count": error_rows, "passed": passed,
    }


def validate_feature_metrics(
    metrics: pd.DataFrame, execution_plan: pd.DataFrame,
    embedding_manifest: pd.DataFrame, *, config: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate schema, exact keys, references, bounds, arithmetic, and controls."""

    schema = validate_dataframe(metrics, FEATURE_METRICS_SCHEMA, allow_extra_columns=False)
    expected_keys = {
        (str(row.candidate_id), str(row.region_id), feature_model_id)
        for row in execution_plan.itertuples(index=False)
        for feature_model_id in FEATURE_MODEL_IDS
    }
    observed_keys = set(metrics[["candidate_id", "region_id", "feature_model_id"]]
                        .astype(str).itertuples(index=False, name=None))
    ok = metrics["status"].astype(str).eq("ok")
    values = metrics.loc[ok, ["damaged_value", "restored_value", "improvement_value"]]
    finite_failures = int((~np.isfinite(values.to_numpy(dtype=float))).sum())
    policy = _settings(config)["finite_value_policy"]
    cosine = metrics.loc[ok, ["damaged_value", "restored_value"]].to_numpy(float)
    bound_failures = int(((cosine < float(policy["cosine_minimum"]))
                          | (cosine > float(policy["cosine_maximum"]))).sum())
    expected_improvement = (metrics.loc[ok, "restored_value"].astype(float)
                            - metrics.loc[ok, "damaged_value"].astype(float))
    arithmetic_failures = int((np.abs(
        expected_improvement - metrics.loc[ok, "improvement_value"].astype(float)
    ) > float(policy["improvement_tolerance"])).sum())
    available = set(embedding_manifest.loc[
        embedding_manifest["status"].astype(str).eq("ok"), "embedding_id"
    ].astype(str))
    reference_failures = sum(int((~metrics[column].astype(str).isin(available)).sum())
                             for column in ("clean_embedding_id",
                                            "damaged_embedding_id",
                                            "restored_embedding_id"))
    zero_ids = set(execution_plan.loc[
        execution_plan["is_zero_control"].astype(bool), "candidate_id"
    ].astype(str))
    zero = metrics.loc[ok & metrics["candidate_id"].astype(str).isin(zero_ids)]
    tolerance = float(policy["zero_control_tolerance"])
    zero_failures = int(((np.abs(zero["damaged_value"].astype(float) - 1.0) > tolerance)
                         | (np.abs(zero["restored_value"].astype(float) - 1.0) > tolerance)
                         | (np.abs(zero["improvement_value"].astype(float)) > tolerance)).sum())
    error_rows = int((~ok).sum())
    passed = bool(
        schema.passed and expected_keys == observed_keys and len(metrics) == len(expected_keys)
        and finite_failures == 0 and bound_failures == 0 and arithmetic_failures == 0
        and reference_failures == 0 and zero_failures == 0 and error_rows == 0
    )
    return {
        "schema": schema.to_dict(), "row_count": len(metrics),
        "expected_row_count": len(expected_keys),
        "missing_key_count": len(expected_keys - observed_keys),
        "unexpected_key_count": len(observed_keys - expected_keys),
        "non_finite_ok_value_count": finite_failures,
        "cosine_bound_failure_count": bound_failures,
        "improvement_arithmetic_failure_count": arithmetic_failures,
        "embedding_reference_failure_count": reference_failures,
        "zero_control_failure_count": zero_failures,
        "error_row_count": error_rows, "passed": passed,
    }


def build_scratch_prompt_pairs(
    metrics: pd.DataFrame, worklist: pd.DataFrame, *, config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build in-memory generic-vs-scratch-aware paired ablation evidence."""

    analysis = _settings(config)["analysis"]
    metadata = worklist[[
        "candidate_id", "case_id", "painting_id", "seed", "prompt_variant_id",
        "damage_or_degradation_type", "model_id",
    ]].copy()
    joined = metrics.merge(metadata, on=["candidate_id", "case_id", "model_id"],
                           how="inner", validate="many_to_one")
    selected = joined.loc[
        joined["model_id"].astype(str).eq("stable_diffusion_inpainting")
        & joined["case_id"].astype(str).str.endswith(
            str(analysis["scratch_case_id_suffix"])
        )
        & joined["prompt_variant_id"].astype(str).isin({
            str(analysis["generic_prompt_variant_id"]),
            str(analysis["scratch_aware_prompt_variant_id"]),
        })
    ].copy()
    keys = ["case_id", "painting_id", "seed", "region_id", "feature_model_id"]
    generic = selected.loc[
        selected["prompt_variant_id"].astype(str).eq(
            str(analysis["generic_prompt_variant_id"])
        ), keys + ["candidate_id", "improvement_value"]
    ].rename(columns={"candidate_id": "generic_candidate_id",
                      "improvement_value": "generic_improvement_value"})
    aware = selected.loc[
        selected["prompt_variant_id"].astype(str).eq(
            str(analysis["scratch_aware_prompt_variant_id"])
        ), keys + ["candidate_id", "improvement_value"]
    ].rename(columns={"candidate_id": "scratch_aware_candidate_id",
                      "improvement_value": "scratch_aware_improvement_value"})
    pairs = generic.merge(aware, on=keys, how="inner", validate="one_to_one")
    pairs["scratch_aware_minus_generic"] = (
        pairs["scratch_aware_improvement_value"].astype(float)
        - pairs["generic_improvement_value"].astype(float)
    )
    return pairs.loc[:, SCRATCH_PROMPT_PAIR_COLUMNS].sort_values(keys, kind="stable").reset_index(drop=True)


def save_feature_embedding_bundle(arrays: Mapping[str, np.ndarray], output_path: str | Path) -> Path:
    """Persist exactly the two dense float32 matrices in compressed NPZ."""

    if set(arrays) != {"clip_embeddings", "dinov2_embeddings"}:
        raise ValueError("Embedding bundle must contain exactly CLIP and DINOv2 arrays")
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        np.savez_compressed(
            handle, clip_embeddings=np.asarray(arrays["clip_embeddings"], dtype=np.float32),
            dinov2_embeddings=np.asarray(arrays["dinov2_embeddings"], dtype=np.float32),
        )
    return target


def load_feature_embedding_bundle(path: str | Path) -> dict[str, np.ndarray]:
    """Reload the canonical NPZ into detached arrays."""

    with np.load(Path(path), allow_pickle=False) as bundle:
        expected = {"clip_embeddings", "dinov2_embeddings"}
        if set(bundle.files) != expected:
            raise ValueError(f"Unexpected NPZ arrays: {sorted(bundle.files)}")
        return {name: np.asarray(bundle[name], dtype=np.float32) for name in sorted(expected)}


def _atomic_csv_with_recovery(
    frame: pd.DataFrame, path: str | Path, *, retries: int = 5,
    retry_delay_seconds: float = 0.25,
) -> dict[str, Any]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".{target.name}.{uuid.uuid4().hex}.tmp"
    frame.to_csv(temporary, index=False)
    last_error = ""
    for attempt in range(1, retries + 1):
        try:
            os.replace(temporary, target)
            return {"status": "canonical", "path": target, "attempts": attempt}
        except PermissionError as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                time.sleep(retry_delay_seconds)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    recovery = target.with_name(f"{target.stem}.recovery-{stamp}{target.suffix}")
    os.replace(temporary, recovery)
    return {"status": "recovery", "path": recovery, "attempts": retries,
            "issue": last_error}


def write_embedding_checkpoint_manifest(
    manifest: pd.DataFrame, path: str | Path,
) -> dict[str, Any]:
    """Write resumable manifest state with Windows-lock recovery."""

    return _atomic_csv_with_recovery(
        manifest.loc[:, FEATURE_EMBEDDING_MANIFEST_COLUMNS], path
    )


def find_latest_embedding_checkpoint(path: str | Path) -> Path | None:
    target = Path(path)
    candidates = [target] if target.is_file() else []
    candidates.extend(item for item in target.parent.glob(
        f"{target.stem}.recovery-*{target.suffix}") if item.is_file())
    return max(candidates, key=lambda item: item.stat().st_mtime_ns) if candidates else None


def load_latest_embedding_checkpoint(
    path: str | Path,
) -> tuple[pd.DataFrame, Path | None]:
    """Load newest canonical/recovery manifest checkpoint."""

    latest = find_latest_embedding_checkpoint(path)
    if latest is None:
        return pd.DataFrame(columns=FEATURE_EMBEDDING_MANIFEST_COLUMNS), None
    frame = pd.read_csv(latest, keep_default_na=False)
    missing = sorted(set(FEATURE_EMBEDDING_MANIFEST_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Checkpoint {latest} is missing columns: {missing}")
    return frame.loc[:, FEATURE_EMBEDDING_MANIFEST_COLUMNS], latest
