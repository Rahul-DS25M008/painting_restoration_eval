"""Reference-based semantic and structural diagnostics for Notebook 20.

The module treats CLIP and DINOv2 evidence as general-purpose representation
proxies. It does not perform object detection, face recognition, artist/style
authentication, historical reconstruction, or conservation approval.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import math
import os
import time
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from PIL import Image

from .metrics_feature_similarity import (
    build_feature_embedding_plan,
    build_feature_execution_plan,
    load_configured_feature_models,
)
from .schemas import (
    SEMANTIC_MAP_ASSET_COLUMNS,
    SEMANTIC_MAP_ASSET_SCHEMA,
    SEMANTIC_STRUCTURAL_METRIC_COLUMNS,
    SEMANTIC_STRUCTURAL_METRIC_SCHEMA,
    validate_dataframe,
)


SEMANTIC_STRUCTURAL_MODULE_NAME = "restoration_eval.semantic_structural"
SEMANTIC_STRUCTURAL_MODULE_VERSION = "1.0.3"
SEMANTIC_STRUCTURAL_METRIC_VERSION = "semantic_structural_metrics.v1"
SEMANTIC_MAP_MANIFEST_VERSION = "semantic_map_assets.v1"
SEMANTIC_NUMERIC_ARCHIVE_VERSION = "semantic_numeric_maps.v1"
SEMANTIC_MAP_RENDERER_VERSION = "semantic_map_renderer.v1"
SEMANTIC_EVIDENCE_ROLE = "semantic_structural_diagnostic_proxy"


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    settings = config.get("semantic_structural", config)
    if not isinstance(settings, Mapping):
        raise TypeError("semantic_structural settings must be a mapping")
    return settings


def load_semantic_structural_config(path: str | Path) -> dict[str, Any]:
    """Load and validate the Notebook 20 configuration contract."""

    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Semantic/structural configuration must be a mapping")
    if config.get("config_schema_version") != "semantic_structural_config.v1":
        raise ValueError("Unsupported semantic/structural config schema")
    settings = _settings(config)
    required = {
        "notebook_id", "notebook_stem", "metric_version",
        "map_manifest_version", "numeric_archive_version",
        "renderer_version", "inputs", "output", "population",
        "feature_models", "regions", "metric_families",
        "semantic_target_scopes", "numeric_maps", "visualization",
        "execution", "expected_counts", "evidence_policy",
        "downstream_consumers", "known_limitations",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"Semantic/structural config is missing keys: {missing}")
    if settings["metric_version"] != SEMANTIC_STRUCTURAL_METRIC_VERSION:
        raise ValueError("Metric version does not match the helper")
    if settings["map_manifest_version"] != SEMANTIC_MAP_MANIFEST_VERSION:
        raise ValueError("Map-manifest version does not match the helper")
    if settings["numeric_archive_version"] != SEMANTIC_NUMERIC_ARCHIVE_VERSION:
        raise ValueError("Numeric-archive version does not match the helper")
    if settings["renderer_version"] != SEMANTIC_MAP_RENDERER_VERSION:
        raise ValueError("Renderer version does not match the helper")
    expected = settings["expected_counts"]
    model_total = sum(int(value) for value in expected["candidates_by_model"].values())
    if model_total != int(expected["evaluated_candidates"]):
        raise ValueError("Candidate-by-model arithmetic is inconsistent")
    if int(expected["nonzero_candidates"]) + int(
        expected["zero_control_candidates"]
    ) != int(expected["evaluated_candidates"]):
        raise ValueError("Zero/nonzero candidate arithmetic is inconsistent")
    if int(expected["content_region_evaluations_per_encoder"]) + int(
        expected["mask_bbox_evaluations_per_encoder"]
    ) != int(expected["candidate_region_evaluations_per_encoder"]):
        raise ValueError("Candidate-region arithmetic is inconsistent")
    metric_parts = (
        "subject_preservation_rows", "local_similarity_summary_rows",
        "local_worsened_fraction_rows", "outside_context_rows",
        "structural_layout_rows", "painterly_proxy_rows",
        "encoder_agreement_rows",
    )
    if sum(int(expected[key]) for key in metric_parts) != int(
        expected["semantic_metric_rows"]
    ):
        raise ValueError("Semantic metric-row arithmetic is inconsistent")
    if int(expected["numeric_map_bundles"]) + int(
        expected["rendered_semantic_panels"]
    ) != int(expected["map_manifest_rows"]):
        raise ValueError("Semantic map-manifest arithmetic is inconsistent")
    models = settings["feature_models"]
    if set(models) != {"clip_vit_b32", "dinov2_vits14"}:
        raise ValueError("Exactly the approved CLIP and DINOv2 models are required")
    for model_id, model in models.items():
        if str(model["feature_model_id"]) != model_id:
            raise ValueError(f"Feature-model key/id mismatch: {model_id}")
        expected_grid = int(model["input_size"]) // int(model["patch_size"])
        if (int(model["grid_height"]), int(model["grid_width"])) != (
            expected_grid, expected_grid
        ):
            raise ValueError(f"Invalid local-token grid for {model_id}")
        checksum = str(model["model_checksum_sha256"])
        if len(checksum) != 64:
            raise ValueError(f"Invalid model checksum for {model_id}")
    if bool(settings["evidence_policy"]["combined_semantic_score_retained"]):
        raise ValueError("A combined semantic score is prohibited")
    return config


def validate_semantic_runtime_dependencies() -> pd.DataFrame:
    """Return an importability audit without loading model weights."""

    packages = (
        "numpy", "pandas", "PIL", "matplotlib", "yaml",
        "torch", "torchvision", "transformers",
    )
    records = []
    for package in packages:
        available = importlib.util.find_spec(package) is not None
        records.append({
            "dependency": package,
            "available": bool(available),
            "required": True,
            "status": "available" if available else "missing",
        })
    return pd.DataFrame(records)


def resolve_path(path_value: str | Path, project_root: str | Path) -> Path:
    path = Path(str(path_value).replace("\\", "/"))
    return path.resolve() if path.is_absolute() else (Path(project_root) / path).resolve()


def project_relative_path(path: str | Path, project_root: str | Path) -> str:
    return Path(path).resolve().relative_to(Path(project_root).resolve()).as_posix()


def sha256_path(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _compact_hash(prefix: str, values: Sequence[Any], length: int = 20) -> str:
    payload = "|".join(str(value) for value in values).encode("utf-8")
    return prefix + hashlib.sha256(payload).hexdigest()[:length]


def make_semantic_metric_id(
    candidate_id: str,
    evidence_family: str,
    metric_name: str,
    feature_model_id: str,
    region_id: str,
    summary_statistic: str,
) -> str:
    return _compact_hash(
        "sm_",
        (
            candidate_id, evidence_family, metric_name, feature_model_id,
            region_id, summary_statistic, SEMANTIC_STRUCTURAL_METRIC_VERSION,
        ),
    )


def make_semantic_map_asset_id(
    candidate_id: str,
    feature_model_id: str,
    region_id: str,
    map_type: str,
) -> str:
    return _compact_hash(
        "sma_",
        (
            candidate_id, feature_model_id, region_id, map_type,
            SEMANTIC_MAP_RENDERER_VERSION,
        ),
    )


def semantic_target_scope(category: str, config: Mapping[str, Any]) -> str:
    """Map one approved artwork category to a diagnostic interpretation scope."""

    scopes = _settings(config)["semantic_target_scopes"]
    key = str(category).strip()
    if key not in scopes:
        raise ValueError(f"Unsupported semantic category: {key!r}")
    return str(scopes[key])


def feature_compatible_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Adapt the Notebook 20 contract to Notebook 15's public planning API."""

    settings = _settings(config)
    models: dict[str, dict[str, Any]] = {}
    for model_id, raw in settings["feature_models"].items():
        models[model_id] = {
            **dict(raw),
            "metric_name": (
                "clip_cosine_similarity"
                if model_id == "clip_vit_b32"
                else "dinov2_cosine_similarity"
            ),
            "model_checksum_sha256": str(raw["model_checksum_sha256"]),
            "array_name": f"{model_id}_semantic_tokens",
            "package_name": "transformers" if model_id == "clip_vit_b32" else "torch",
            "resize_shorter_side": int(raw["input_size"]),
            "normalization_mean": raw.get(
                "normalization_mean", [0.48145466, 0.4578275, 0.40821073]
            ),
            "normalization_std": raw.get(
                "normalization_std", [0.26862954, 0.26130258, 0.27577711]
            ),
        }
    execution = settings["execution"]
    return {
        "feature_similarity": {
            "models": models,
            "regions": {
                "active_regions": list(settings["regions"]["encoded_regions"]),
                "mask_bbox_margin_pixels": int(
                    settings["regions"]["mask_bbox_margin_pixels"]
                ),
            },
            "execution": {
                "preferred_device": execution["preferred_device"],
                "allow_cpu_fallback": execution["allow_cpu_fallback"],
                "deterministic_algorithms": execution["deterministic_algorithms"],
            },
        }
    }


def build_semantic_population(
    worklist: pd.DataFrame,
    artworks: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Validate and enrich the exact 2,160-candidate evaluation population."""

    required = {
        "case_id", "candidate_id", "model_id", "painting_id", "status",
        "restored_path", "restored_sha256", "input_image_path",
        "clean_image_path", "mask_or_effect_path", "mask_threshold",
        "content_x_min", "content_y_min", "content_x_max", "content_y_max",
        "is_zero_control", "execution_role",
    }
    missing = sorted(required - set(worklist.columns))
    if missing:
        raise ValueError(f"Semantic worklist is missing columns: {missing}")
    artwork_required = {"painting_id", "category", "style_or_period"}
    artwork_missing = sorted(artwork_required - set(artworks.columns))
    if artwork_missing:
        raise ValueError(f"Artwork table is missing columns: {artwork_missing}")
    if artworks["painting_id"].astype(str).duplicated().any():
        raise ValueError("Artwork metadata repeats painting_id")
    settings = _settings(config)
    eligible_status = str(settings["population"]["eligible_status"])
    population = worklist.loc[
        worklist["status"].astype(str).eq(eligible_status)
    ].copy()
    if "category" in population.columns:
        population = population.drop(columns=["category"])
    if "style_or_period" in population.columns:
        population = population.drop(columns=["style_or_period"])
    population = population.merge(
        artworks[["painting_id", "category", "style_or_period"]].copy(),
        on="painting_id", how="left", validate="many_to_one",
    )
    if population["category"].isna().any():
        raise ValueError("Semantic population has unresolved artwork categories")
    population["style_or_period"] = (
        population["style_or_period"]
        .fillna("not_recorded")
        .astype(str)
        .str.strip()
        .replace("", "not_recorded")
    )
    population["semantic_target_scope"] = population["category"].map(
        lambda value: semantic_target_scope(str(value), config)
    )
    population["applicability_status"] = "applicable"
    if population["candidate_id"].astype(str).duplicated().any():
        raise ValueError("Semantic population contains duplicate candidate IDs")
    expected = settings["expected_counts"]
    required_models = {
        str(key): int(value)
        for key, value in expected["candidates_by_model"].items()
    }
    raw_observed_models = {
        str(key): int(value)
        for key, value in population["model_id"].value_counts().sort_index().items()
    }
    unexpected_models = sorted(set(raw_observed_models) - set(required_models))
    if unexpected_models:
        raise ValueError(
            f"Semantic population contains unexpected models: {unexpected_models}"
        )
    observed_models = {
        model_id: int(raw_observed_models.get(model_id, 0))
        for model_id in required_models
    }
    if observed_models != required_models:
        raise ValueError(
            f"Semantic model population differs from contract: {observed_models}"
        )
    if len(population) != int(expected["evaluated_candidates"]):
        raise ValueError("Semantic candidate count differs from contract")
    if population["case_id"].nunique() != int(expected["evaluated_cases"]):
        raise ValueError("Semantic case count differs from contract")
    return population.sort_values(
        ["model_id", "case_id", "candidate_id"], kind="stable"
    ).reset_index(drop=True)


def select_semantic_map_candidates(
    population: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select nonzero primary candidates and the complete SDXL partial scope."""

    settings = _settings(config)
    is_nonzero = ~population["is_zero_control"].astype(bool)
    model_id = population["model_id"].astype(str)
    role = population["execution_role"].astype(str)
    stable_diffusion = model_id.eq("stable_diffusion_inpainting")
    primary_role = str(settings["population"]["stable_diffusion_primary_role"])
    selected = population.loc[
        is_nonzero & (~stable_diffusion | role.eq(primary_role))
    ].copy()
    expected = int(settings["expected_counts"]["rendered_semantic_panels"])
    if len(selected) != expected:
        raise ValueError(
            f"Semantic panel scope has {len(selected)} candidates; expected {expected}"
        )
    return selected.sort_values(
        ["model_id", "case_id", "candidate_id"], kind="stable"
    ).reset_index(drop=True)


def build_semantic_execution_plan(
    population: pd.DataFrame,
    *,
    project_root: str | Path,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the exact content/crop candidate-region execution plan."""

    plan = build_feature_execution_plan(
        population,
        project_root=project_root,
        config=feature_compatible_config(config),
    )
    expected = int(
        _settings(config)["expected_counts"]["candidate_region_evaluations_per_encoder"]
    )
    if len(plan) != expected:
        raise ValueError(f"Semantic execution plan has {len(plan)} rows; expected {expected}")
    return plan


def build_semantic_token_plan(
    execution_plan: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build deduplicated source records for local-token extraction."""

    plan = build_feature_embedding_plan(
        execution_plan,
        config=feature_compatible_config(config),
    ).copy()
    plan = plan.rename(columns={"embedding_id": "token_record_id"})
    model_settings = _settings(config)["feature_models"]
    plan["grid_height"] = plan["feature_model_id"].map(
        lambda value: int(model_settings[str(value)]["grid_height"])
    )
    plan["grid_width"] = plan["feature_model_id"].map(
        lambda value: int(model_settings[str(value)]["grid_width"])
    )
    expected = int(_settings(config)["expected_counts"]["source_token_records"])
    if len(plan) != expected:
        raise ValueError(f"Semantic token plan has {len(plan)} rows; expected {expected}")
    if plan["token_record_id"].astype(str).duplicated().any():
        raise ValueError("Semantic token plan repeats token_record_id")
    return plan


def letterbox_rgb(
    image: np.ndarray | Image.Image,
    *,
    size: int,
    fill_rgb: Sequence[int],
) -> tuple[np.ndarray, np.ndarray]:
    """Resize with preserved aspect ratio and return a valid-pixel mask."""

    source = image if isinstance(image, Image.Image) else Image.fromarray(
        np.asarray(image, dtype=np.uint8), mode="RGB"
    )
    source = source.convert("RGB")
    width, height = source.size
    if width <= 0 or height <= 0 or size <= 0:
        raise ValueError("Letterbox dimensions must be positive")
    scale = min(float(size) / width, float(size) / height)
    resized_width = max(1, min(size, int(round(width * scale))))
    resized_height = max(1, min(size, int(round(height * scale))))
    resized = source.resize((resized_width, resized_height), Image.Resampling.BICUBIC)
    x0 = (size - resized_width) // 2
    y0 = (size - resized_height) // 2
    canvas = Image.new("RGB", (size, size), tuple(int(value) for value in fill_rgb))
    canvas.paste(resized, (x0, y0))
    valid = np.zeros((size, size), dtype=bool)
    valid[y0:y0 + resized_height, x0:x0 + resized_width] = True
    return np.asarray(canvas, dtype=np.uint8), valid


def token_support_fraction(mask: np.ndarray, grid_shape: tuple[int, int]) -> np.ndarray:
    """Area-average a pixel mask onto a deterministic token grid."""

    values = np.asarray(mask, dtype=np.float32)
    if values.ndim != 2:
        raise ValueError("Token support mask must be two-dimensional")
    height, width = (int(grid_shape[0]), int(grid_shape[1]))
    if height <= 0 or width <= 0:
        raise ValueError("Token grid dimensions must be positive")
    image = Image.fromarray(np.clip(values, 0.0, 1.0), mode="F")
    resized = image.resize((width, height), Image.Resampling.BOX)
    return np.clip(np.asarray(resized, dtype=np.float32), 0.0, 1.0)


def letterbox_support_mask(
    mask: np.ndarray,
    *,
    size: int,
    grid_shape: tuple[int, int],
) -> np.ndarray:
    """Project a fractional crop mask onto the exact letterboxed token grid.

    The geometry matches :func:`letterbox_rgb`, while ``BOX`` resampling
    preserves fractional area support instead of converting partial tokens to
    binary membership.
    """

    source = np.asarray(mask, dtype=np.float32)
    if source.ndim != 2:
        raise ValueError("Letterbox support mask must be two-dimensional")
    height, width = source.shape
    if height <= 0 or width <= 0 or int(size) <= 0:
        raise ValueError("Letterbox support dimensions must be positive")
    scale = min(float(size) / width, float(size) / height)
    resized_width = max(1, min(int(size), int(round(width * scale))))
    resized_height = max(1, min(int(size), int(round(height * scale))))
    image = Image.fromarray(np.clip(source, 0.0, 1.0), mode="F")
    resized = image.resize(
        (resized_width, resized_height), Image.Resampling.BOX
    )
    canvas = np.zeros((int(size), int(size)), dtype=np.float32)
    x0 = (int(size) - resized_width) // 2
    y0 = (int(size) - resized_height) // 2
    canvas[y0:y0 + resized_height, x0:x0 + resized_width] = np.asarray(
        resized, dtype=np.float32
    )
    return token_support_fraction(canvas, grid_shape)


def _normalize_last_axis(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float32)
    norms = np.linalg.norm(array, axis=-1, keepdims=True)
    if np.any(~np.isfinite(norms)) or np.any(norms <= 0):
        raise ValueError("Local tokens contain zero or non-finite norms")
    return (array / norms).astype(np.float32, copy=False)


def _validate_token_triplet(
    clean_tokens: np.ndarray,
    damaged_tokens: np.ndarray,
    restored_tokens: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    arrays = tuple(
        _normalize_last_axis(values)
        for values in (clean_tokens, damaged_tokens, restored_tokens)
    )
    if len({array.shape for array in arrays}) != 1 or arrays[0].ndim != 3:
        raise ValueError("Clean, damaged, and restored token grids must share HxWxD")
    return arrays


def compute_local_semantic_bundle(
    clean_tokens: np.ndarray,
    damaged_tokens: np.ndarray,
    restored_tokens: np.ndarray,
    *,
    clean_global: np.ndarray | None = None,
    valid_token_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Return seven unclipped local semantic channels in float32."""

    clean, damaged, restored = _validate_token_triplet(
        clean_tokens, damaged_tokens, restored_tokens
    )
    if clean_global is None:
        reference = _normalize_last_axis(clean.mean(axis=(0, 1), keepdims=False))
    else:
        reference = _normalize_last_axis(np.asarray(clean_global, dtype=np.float32))
    if reference.ndim != 1 or reference.shape[0] != clean.shape[-1]:
        raise ValueError("Reference global vector dimension does not match patch tokens")
    damaged_clean = np.sum(clean * damaged, axis=-1)
    restored_clean = np.sum(clean * restored, axis=-1)
    improvement = restored_clean - damaged_clean
    restored_damaged = np.sum(restored * damaged, axis=-1)
    clean_affinity = np.sum(clean * reference, axis=-1)
    damaged_affinity = np.sum(damaged * reference, axis=-1)
    restored_affinity = np.sum(restored * reference, axis=-1)
    bundle = np.stack(
        (
            damaged_clean, restored_clean, improvement, restored_damaged,
            clean_affinity, damaged_affinity, restored_affinity,
        ),
        axis=-1,
    ).astype(np.float32)
    if valid_token_mask is not None:
        valid = np.asarray(valid_token_mask, dtype=bool)
        if valid.shape != bundle.shape[:2]:
            raise ValueError("Valid-token mask does not match semantic bundle")
        bundle[~valid] = np.nan
    return bundle


def summarize_similarity_channel(
    values: np.ndarray,
    *,
    weights: np.ndarray | None = None,
) -> dict[str, float]:
    """Summarize one local map without treating padded tokens as evidence."""

    array = np.asarray(values, dtype=np.float64)
    finite = np.isfinite(array)
    if weights is None:
        selected = array[finite]
        if selected.size == 0:
            return {"mean": math.nan, "median": math.nan, "p10": math.nan}
        return {
            "mean": float(selected.mean()),
            "median": float(np.median(selected)),
            "p10": float(np.percentile(selected, 10.0)),
        }
    support = np.asarray(weights, dtype=np.float64)
    if support.shape != array.shape:
        raise ValueError("Summary weights do not match the map")
    valid = finite & np.isfinite(support) & (support > 0)
    if not valid.any():
        return {"mean": math.nan, "median": math.nan, "p10": math.nan}
    selected = array[valid]
    selected_weights = support[valid]
    weighted_mean = float(np.average(selected, weights=selected_weights))
    order = np.argsort(selected, kind="stable")
    sorted_values = selected[order]
    cumulative = np.cumsum(selected_weights[order])
    cumulative /= cumulative[-1]
    median = float(sorted_values[np.searchsorted(cumulative, 0.5, side="left")])
    p10 = float(sorted_values[np.searchsorted(cumulative, 0.1, side="left")])
    return {"mean": weighted_mean, "median": median, "p10": p10}


def local_worsened_fraction(
    signed_improvement: np.ndarray,
    *,
    weights: np.ndarray | None = None,
    tolerance: float = 1e-7,
) -> float:
    array = np.asarray(signed_improvement, dtype=np.float64)
    finite = np.isfinite(array)
    if weights is None:
        return float(np.mean(array[finite] < -float(tolerance))) if finite.any() else math.nan
    support = np.asarray(weights, dtype=np.float64)
    if support.shape != array.shape:
        raise ValueError("Worsening weights do not match the map")
    valid = finite & np.isfinite(support) & (support > 0)
    if not valid.any():
        return math.nan
    return float(
        np.average((array[valid] < -float(tolerance)).astype(float), weights=support[valid])
    )


def _probability_map(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    finite = np.isfinite(array)
    if not finite.any():
        raise ValueError("Affinity map has no finite values")
    selected = array[finite]
    selected = selected - selected.max()
    probabilities = np.exp(selected)
    probabilities /= probabilities.sum()
    result = np.zeros_like(array, dtype=np.float64)
    result[finite] = probabilities
    return result


def affinity_weighted_similarity(
    reference_affinity: np.ndarray,
    similarity: np.ndarray,
) -> float:
    """Average similarity using reference-derived affinity probabilities."""

    affinity = np.asarray(reference_affinity, dtype=np.float64)
    values = np.asarray(similarity, dtype=np.float64)
    if affinity.shape != values.shape or affinity.ndim != 2:
        raise ValueError("Affinity and similarity maps must share a 2D grid")
    valid = np.isfinite(affinity) & np.isfinite(values)
    if not valid.any():
        return math.nan
    probabilities = _probability_map(np.where(valid, affinity, np.nan))
    return float(np.sum(probabilities[valid] * values[valid]))


def affinity_layout_metrics(reference: np.ndarray, candidate: np.ndarray) -> dict[str, float]:
    """Compute transparent layout statistics between two affinity maps."""

    ref = np.asarray(reference, dtype=np.float64)
    cand = np.asarray(candidate, dtype=np.float64)
    if ref.shape != cand.shape or ref.ndim != 2:
        raise ValueError("Affinity maps must share a two-dimensional grid")
    valid = np.isfinite(ref) & np.isfinite(cand)
    if valid.sum() < 2:
        return {"correlation": math.nan, "js_divergence": math.nan, "centroid_shift": math.nan}
    ref_values = ref[valid]
    cand_values = cand[valid]
    if np.std(ref_values) <= 1e-12 or np.std(cand_values) <= 1e-12:
        correlation = 1.0 if np.allclose(ref_values, cand_values) else 0.0
    else:
        correlation = float(np.corrcoef(ref_values, cand_values)[0, 1])
    ref_probability = _probability_map(np.where(valid, ref, np.nan))
    cand_probability = _probability_map(np.where(valid, cand, np.nan))
    midpoint = 0.5 * (ref_probability + cand_probability)
    epsilon = 1e-12
    ref_positive = ref_probability > 0
    cand_positive = cand_probability > 0
    kl_ref = np.sum(
        ref_probability[ref_positive]
        * np.log((ref_probability[ref_positive] + epsilon) / (midpoint[ref_positive] + epsilon))
    )
    kl_cand = np.sum(
        cand_probability[cand_positive]
        * np.log((cand_probability[cand_positive] + epsilon) / (midpoint[cand_positive] + epsilon))
    )
    yy, xx = np.mgrid[:ref.shape[0], :ref.shape[1]]
    ref_centroid = np.array([
        np.sum(yy * ref_probability), np.sum(xx * ref_probability)
    ])
    cand_centroid = np.array([
        np.sum(yy * cand_probability), np.sum(xx * cand_probability)
    ])
    diagonal = max(math.hypot(ref.shape[0] - 1, ref.shape[1] - 1), 1.0)
    return {
        "correlation": correlation,
        "js_divergence": float(0.5 * (kl_ref + kl_cand)),
        "centroid_shift": float(np.linalg.norm(ref_centroid - cand_centroid) / diagonal),
    }


def patch_covariance_distance(reference_tokens: np.ndarray, candidate_tokens: np.ndarray) -> float:
    """Return a normalized patch-feature covariance distance."""

    reference = _normalize_last_axis(reference_tokens).reshape(-1, reference_tokens.shape[-1])
    candidate = _normalize_last_axis(candidate_tokens).reshape(-1, candidate_tokens.shape[-1])
    if reference.shape != candidate.shape or reference.shape[0] < 2:
        raise ValueError("Patch-token matrices must share shape with at least two patches")
    reference = reference - reference.mean(axis=0, keepdims=True)
    candidate = candidate - candidate.mean(axis=0, keepdims=True)
    reference_gram = reference @ reference.T / max(reference.shape[1], 1)
    candidate_gram = candidate @ candidate.T / max(candidate.shape[1], 1)
    denominator = max(float(np.linalg.norm(reference_gram, ord="fro")), 1e-12)
    return float(np.linalg.norm(reference_gram - candidate_gram, ord="fro") / denominator)


def map_agreement(first: np.ndarray, second: np.ndarray) -> float:
    """Correlate two maps after deterministic resizing to a shared grid."""

    a = np.asarray(first, dtype=np.float32)
    b = np.asarray(second, dtype=np.float32)
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("Map agreement requires two-dimensional maps")
    if a.shape != b.shape:
        image = Image.fromarray(b, mode="F")
        b = np.asarray(
            image.resize((a.shape[1], a.shape[0]), Image.Resampling.BILINEAR),
            dtype=np.float32,
        )
    valid = np.isfinite(a) & np.isfinite(b)
    if valid.sum() < 2:
        return math.nan
    x = a[valid]
    y = b[valid]
    if np.std(x) <= 1e-12 or np.std(y) <= 1e-12:
        return 1.0 if np.allclose(x, y) else 0.0
    return float(np.corrcoef(x, y)[0, 1])


def build_semantic_metric_record(
    metadata: Mapping[str, Any],
    *,
    evidence_family: str,
    metric_name: str,
    feature_model_id: str,
    region_id: str,
    summary_statistic: str,
    damaged_value: float,
    restored_value: float,
    improvement_value: float,
    improvement_direction: str,
    value_unit: str,
    preprocessing_id: str,
    region_policy_version: str,
    source_metric_row_id: str = "",
    status: str = "ok",
    issue: str = "",
) -> dict[str, Any]:
    """Build one normalized semantic metric record."""

    candidate_id = str(metadata.get("candidate_id", ""))
    record = {
        **{column: metadata.get(column, "") for column in SEMANTIC_STRUCTURAL_METRIC_COLUMNS},
        "semantic_metric_id": make_semantic_metric_id(
            candidate_id, evidence_family, metric_name, feature_model_id,
            region_id, summary_statistic,
        ),
        "evidence_family": evidence_family,
        "metric_name": metric_name,
        "feature_model_id": feature_model_id,
        "region_id": region_id,
        "summary_statistic": summary_statistic,
        "damaged_value": damaged_value,
        "restored_value": restored_value,
        "improvement_value": improvement_value,
        "improvement_direction": improvement_direction,
        "value_unit": value_unit,
        "source_metric_row_id": source_metric_row_id,
        "metric_version": SEMANTIC_STRUCTURAL_METRIC_VERSION,
        "region_policy_version": region_policy_version,
        "preprocessing_id": preprocessing_id,
        "evidence_role": SEMANTIC_EVIDENCE_ROLE,
        "is_combined_score": False,
        "is_final_trustworthiness_flag": False,
        "status": status,
        "issue": issue,
    }
    return {column: record.get(column, "") for column in SEMANTIC_STRUCTURAL_METRIC_COLUMNS}


def build_semantic_map_asset_record(
    metadata: Mapping[str, Any],
    *,
    asset_kind: str,
    feature_model_id: str,
    region_id: str,
    map_type: str,
    relative_path: str,
    archive_key: str = "",
    channel_schema: str = "",
    selection_role: str = "",
    sha256: str = "",
    size_bytes: int | float | str = np.nan,
    width: int | float | str = np.nan,
    height: int | float | str = np.nan,
    image_mode: str = "",
    format: str = "NPZ",
    cmap: str = "",
    vmin: float | str = np.nan,
    vmax: float | str = np.nan,
    center: float | str = np.nan,
    scale_scope: str = "numeric_unclipped",
    normalization_policy_id: str = "none",
    quantization_policy: str = "float32_compute_float16_archive",
    no_data_policy: str = "nan_for_invalid_or_padded_tokens",
    status: str = "passed",
    issue: str = "",
) -> dict[str, Any]:
    candidate_id = str(metadata.get("candidate_id", ""))
    record = {
        **{column: metadata.get(column, "") for column in SEMANTIC_MAP_ASSET_COLUMNS},
        "semantic_map_asset_id": make_semantic_map_asset_id(
            candidate_id, feature_model_id, region_id, map_type
        ),
        "asset_kind": asset_kind,
        "ownership": "owned",
        "feature_model_id": feature_model_id,
        "region_id": region_id,
        "map_type": map_type,
        "relative_path": relative_path,
        "archive_key": archive_key,
        "channel_schema": channel_schema,
        "selection_role": selection_role,
        "sha256": sha256,
        "size_bytes": size_bytes,
        "width": width,
        "height": height,
        "image_mode": image_mode,
        "format": format,
        "cmap": cmap,
        "vmin": vmin,
        "vmax": vmax,
        "center": center,
        "scale_scope": scale_scope,
        "normalization_policy_id": normalization_policy_id,
        "quantization_policy": quantization_policy,
        "no_data_policy": no_data_policy,
        "renderer_version": SEMANTIC_MAP_RENDERER_VERSION,
        "status": status,
        "issue": issue,
    }
    return {column: record.get(column, "") for column in SEMANTIC_MAP_ASSET_COLUMNS}


def load_semantic_feature_models(
    config: Mapping[str, Any],
    *,
    device: str,
    local_only: bool = True,
) -> dict[str, dict[str, Any]]:
    """Load the exact cached CLIP and DINOv2 checkpoints used by Notebook 15."""

    return load_configured_feature_models(
        feature_compatible_config(config), device=device, local_only=local_only
    )


def _tensor_from_letterboxed(
    arrays: Sequence[np.ndarray],
    *,
    mean: Sequence[float],
    std: Sequence[float],
    device: str,
) -> Any:
    torch = importlib.import_module("torch")
    values = np.stack(arrays).astype(np.float32) / 255.0
    tensor = torch.from_numpy(values).permute(0, 3, 1, 2)
    mean_tensor = torch.tensor(mean, dtype=tensor.dtype).view(1, 3, 1, 1)
    std_tensor = torch.tensor(std, dtype=tensor.dtype).view(1, 3, 1, 1)
    return ((tensor - mean_tensor) / std_tensor).to(device)


def extract_local_token_batch(
    images: Sequence[np.ndarray | Image.Image],
    *,
    feature_model_id: str,
    model_bundle: Mapping[str, Any],
    config: Mapping[str, Any],
    device: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract normalized local tokens, global vectors, and valid-token masks."""

    if not images:
        raise ValueError("At least one image is required")
    settings = _settings(config)
    model_settings = settings["feature_models"][feature_model_id]
    size = int(model_settings["input_size"])
    if feature_model_id == "clip_vit_b32":
        processor = model_bundle["processor"].image_processor
        mean = tuple(float(value) for value in processor.image_mean)
        std = tuple(float(value) for value in processor.image_std)
    elif feature_model_id == "dinov2_vits14":
        mean = tuple(float(value) for value in model_settings["normalization_mean"])
        std = tuple(float(value) for value in model_settings["normalization_std"])
    else:
        raise ValueError(f"Unsupported feature model: {feature_model_id}")
    fill = tuple(int(round(value * 255.0)) for value in mean)
    prepared = [letterbox_rgb(image, size=size, fill_rgb=fill) for image in images]
    arrays = [item[0] for item in prepared]
    valid_pixels = [item[1] for item in prepared]
    pixel_values = _tensor_from_letterboxed(arrays, mean=mean, std=std, device=device)
    torch = importlib.import_module("torch")
    model = model_bundle["model"]
    with torch.inference_mode():
        if feature_model_id == "clip_vit_b32":
            outputs = model.vision_model(pixel_values=pixel_values)
            hidden = outputs.last_hidden_state
            hidden = model.vision_model.post_layernorm(hidden)
            projected = model.visual_projection(hidden)
            global_vectors = projected[:, 0]
            patch_tokens = projected[:, 1:]
        else:
            outputs = model.forward_features(pixel_values)
            patch_tokens = outputs["x_norm_patchtokens"]
            global_vectors = outputs["x_norm_clstoken"]
    patch_values = patch_tokens.detach().float().cpu().numpy()
    global_values = global_vectors.detach().float().cpu().numpy()
    grid = (int(model_settings["grid_height"]), int(model_settings["grid_width"]))
    expected_patches = grid[0] * grid[1]
    if patch_values.shape[1] != expected_patches:
        raise ValueError(
            f"Unexpected {feature_model_id} patch count {patch_values.shape[1]}"
        )
    patch_values = _normalize_last_axis(
        patch_values.reshape(len(images), grid[0], grid[1], -1)
    )
    global_values = _normalize_last_axis(global_values)
    valid_tokens = np.stack([
        token_support_fraction(mask, grid) > 0.999 for mask in valid_pixels
    ])
    return patch_values, global_values, valid_tokens


def write_semantic_map_archive(
    bundles: Mapping[str, np.ndarray],
    output_path: str | Path,
    *,
    archive_dtype: str = "float16",
) -> Path:
    """Write numeric semantic bundles atomically as a compressed NPZ."""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f"{destination.name}.{uuid.uuid4().hex}.tmp.npz")
    arrays = {
        str(key): np.asarray(value, dtype=np.dtype(archive_dtype))
        for key, value in bundles.items()
    }
    np.savez_compressed(temporary, **arrays)
    os.replace(temporary, destination)
    return destination


def load_semantic_map_archive(path: str | Path) -> dict[str, np.ndarray]:
    with np.load(Path(path), allow_pickle=False) as archive:
        return {key: np.asarray(archive[key]) for key in archive.files}


def render_semantic_panel(
    clean_rgb: np.ndarray,
    damaged_rgb: np.ndarray,
    restored_rgb: np.ndarray,
    dinov2_bundle: np.ndarray,
    clip_bundle: np.ndarray,
    output_path: str | Path,
    *,
    title: str,
    drift_vmax: float,
    improvement_absmax: float,
) -> Path:
    """Render one six-panel candidate diagnostic without changing numeric maps."""

    if drift_vmax <= 0 or improvement_absmax <= 0:
        raise ValueError("Semantic visualization scales must be positive")
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f"{destination.stem}.{uuid.uuid4().hex}.tmp.png"
    )
    figure = None
    try:
        figure, axes = plt.subplots(
            2, 3, figsize=(13.5, 8.5), constrained_layout=True
        )
        for axis, image, label in zip(
            axes[0], (clean_rgb, damaged_rgb, restored_rgb),
            ("Clean reference", "Damaged input", "Restored candidate"), strict=True,
        ):
            axis.imshow(np.asarray(image, dtype=np.uint8))
            axis.set_title(label)
            axis.axis("off")
        dino_drift = 1.0 - np.asarray(dinov2_bundle[..., 1], dtype=np.float32)
        clip_drift = 1.0 - np.asarray(clip_bundle[..., 1], dtype=np.float32)
        improvement = np.asarray(dinov2_bundle[..., 2], dtype=np.float32)
        images = (
            axes[1, 0].imshow(dino_drift, cmap="magma", vmin=0.0, vmax=drift_vmax),
            axes[1, 1].imshow(clip_drift, cmap="magma", vmin=0.0, vmax=drift_vmax),
            axes[1, 2].imshow(
                improvement, cmap="coolwarm", vmin=-improvement_absmax,
                vmax=improvement_absmax,
            ),
        )
        for axis, label, image in zip(
            axes[1],
            (
                "DINOv2 reference drift",
                "CLIP reference drift",
                "DINOv2 signed improvement",
            ),
            images,
            strict=True,
        ):
            axis.set_title(label)
            axis.axis("off")
            figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
        figure.suptitle(title, fontsize=13)
        figure.savefig(temporary, dpi=160, facecolor="white")
    finally:
        if figure is not None:
            plt.close(figure)

    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def validate_semantic_metrics(
    dataframe: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    schema = validate_dataframe(
        dataframe, SEMANTIC_STRUCTURAL_METRIC_SCHEMA, allow_extra_columns=False
    )
    expected = int(_settings(config)["expected_counts"]["semantic_metric_rows"])
    ok_rows = dataframe["status"].astype(str).eq("ok")
    numeric = dataframe.loc[ok_rows, [
        "damaged_value", "restored_value", "improvement_value"
    ]].apply(pd.to_numeric, errors="coerce")
    populated = numeric.notna()
    populated_values = numeric.to_numpy(dtype=float)[populated.to_numpy()]
    finite = bool(
        populated_values.size > 0 and np.isfinite(populated_values).all()
    )

    evidence_family = dataframe.loc[ok_rows, "evidence_family"].astype(str)
    worsening = evidence_family.eq("local_semantic_worsening")
    outside_context = evidence_family.eq("outside_context_preservation")
    standard = ~(worsening | outside_context)

    standard_pattern = populated.all(axis=1)
    worsening_pattern = (
        ~populated["damaged_value"]
        & populated["restored_value"]
        & ~populated["improvement_value"]
    )
    outside_context_pattern = populated.all(axis=1) | ~populated.any(axis=1)
    numeric_patterns_valid = bool(
        standard_pattern.loc[standard].all()
        and worsening_pattern.loc[worsening].all()
        and outside_context_pattern.loc[outside_context].all()
    )

    outside_context_no_data = outside_context & ~populated.any(axis=1)
    no_data_issues = (
        dataframe.loc[ok_rows, "issue"]
        .fillna("")
        .astype(str)
        .str.strip()
    )
    no_data_issues_recorded = bool(
        no_data_issues.loc[outside_context_no_data].ne("").all()
    )
    return {
        "passed": bool(
            schema.passed and len(dataframe) == expected
            and dataframe["semantic_metric_id"].is_unique
            and ok_rows.all() and finite
            and numeric_patterns_valid and no_data_issues_recorded
            and not dataframe["is_combined_score"].astype(bool).any()
            and not dataframe["is_final_trustworthiness_flag"].astype(bool).any()
        ),
        "schema": schema.to_dict(),
        "row_count": int(len(dataframe)),
        "candidate_count": int(dataframe["candidate_id"].nunique()),
        "evidence_family_counts": dataframe["evidence_family"].value_counts().to_dict(),
        "numeric_values_finite": finite,
        "numeric_value_patterns_valid": numeric_patterns_valid,
        "outside_context_no_data_rows": int(outside_context_no_data.sum()),
        "outside_context_no_data_issues_recorded": no_data_issues_recorded,
    }


def validate_semantic_map_manifest(
    dataframe: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    schema = validate_dataframe(
        dataframe, SEMANTIC_MAP_ASSET_SCHEMA, allow_extra_columns=False
    )
    expected = int(_settings(config)["expected_counts"]["map_manifest_rows"])
    passed = dataframe["status"].astype(str).eq("passed")
    numeric = dataframe["asset_kind"].astype(str).eq("numeric_map_bundle")
    rendered = dataframe["asset_kind"].astype(str).eq("rendered_semantic_panel")
    nonblank_numeric_keys = dataframe.loc[numeric, "archive_key"].fillna("").astype(str).str.strip().ne("")
    nonblank_rendered_paths = dataframe.loc[rendered, "relative_path"].fillna("").astype(str).str.strip().ne("")
    return {
        "passed": bool(
            schema.passed and len(dataframe) == expected
            and dataframe["semantic_map_asset_id"].is_unique and passed.all()
            and nonblank_numeric_keys.all() and nonblank_rendered_paths.all()
        ),
        "schema": schema.to_dict(),
        "row_count": int(len(dataframe)),
        "asset_kind_counts": dataframe["asset_kind"].value_counts().to_dict(),
        "blank_numeric_archive_keys": int((~nonblank_numeric_keys).sum()),
        "blank_rendered_paths": int((~nonblank_rendered_paths).sum()),
    }


def write_dataframe_atomic(
    dataframe: pd.DataFrame,
    path: str | Path,
    *,
    attempts: int = 8,
    retry_delay_seconds: float = 0.25,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f"{destination.name}.{uuid.uuid4().hex}.tmp")
    dataframe.to_csv(temporary, index=False)
    last_error: PermissionError | None = None
    for attempt in range(1, int(attempts) + 1):
        try:
            os.replace(temporary, destination)
            return destination
        except PermissionError as error:
            last_error = error
            if attempt < attempts:
                time.sleep(float(retry_delay_seconds) * attempt)
    temporary.unlink(missing_ok=True)
    raise PermissionError(f"Could not replace dataframe destination: {last_error}")


__all__ = [
    "SEMANTIC_EVIDENCE_ROLE",
    "SEMANTIC_MAP_MANIFEST_VERSION",
    "SEMANTIC_MAP_RENDERER_VERSION",
    "SEMANTIC_NUMERIC_ARCHIVE_VERSION",
    "SEMANTIC_STRUCTURAL_METRIC_VERSION",
    "SEMANTIC_STRUCTURAL_MODULE_NAME",
    "SEMANTIC_STRUCTURAL_MODULE_VERSION",
    "affinity_weighted_similarity",
    "affinity_layout_metrics",
    "build_semantic_execution_plan",
    "build_semantic_map_asset_record",
    "build_semantic_metric_record",
    "build_semantic_population",
    "build_semantic_token_plan",
    "compute_local_semantic_bundle",
    "extract_local_token_batch",
    "feature_compatible_config",
    "letterbox_rgb",
    "letterbox_support_mask",
    "load_semantic_feature_models",
    "load_semantic_map_archive",
    "load_semantic_structural_config",
    "local_worsened_fraction",
    "make_semantic_map_asset_id",
    "make_semantic_metric_id",
    "map_agreement",
    "patch_covariance_distance",
    "project_relative_path",
    "render_semantic_panel",
    "resolve_path",
    "select_semantic_map_candidates",
    "semantic_target_scope",
    "sha256_path",
    "summarize_similarity_channel",
    "token_support_fraction",
    "validate_semantic_map_manifest",
    "validate_semantic_metrics",
    "validate_semantic_runtime_dependencies",
    "write_dataframe_atomic",
    "write_semantic_map_archive",
]
