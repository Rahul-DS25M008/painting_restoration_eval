"""Transparent repeated-seed uncertainty evidence for diffusion restoration.

Notebook 18 consumes completed candidates only.  It never runs restoration
inference, never mixes prompt variants inside an uncertainty group, and does
not construct a combined uncertainty index.  Spatial geometry is delegated to
the canonical :mod:`restoration_eval.regions` helper.
"""

from __future__ import annotations

import hashlib
import itertools
import math
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml
from PIL import Image

from .metrics_lpips import (
    build_case_lpips_regions,
    compute_lpips_batch,
    prepare_lpips_tensor,
)
from .regions import Region, build_standard_regions
from .schemas import (
    DIFFUSION_UNCERTAINTY_COLUMNS,
    DIFFUSION_UNCERTAINTY_SCHEMA,
    UNCERTAINTY_CALIBRATION_INPUTS_COLUMNS,
    UNCERTAINTY_CALIBRATION_INPUTS_SCHEMA,
    validate_dataframe,
)


DIFFUSION_UNCERTAINTY_MODULE_VERSION = "1.0.3"
DIFFUSION_UNCERTAINTY_METRIC_VERSION = "empirical_seed_uncertainty.v1"
DIFFUSION_UNCERTAINTY_SCHEMA_VERSION = "diffusion_uncertainty.v1"
UNCERTAINTY_CALIBRATION_SCHEMA_VERSION = "uncertainty_calibration_inputs.v1"
UNCERTAINTY_EVIDENCE_ROLE = "empirical_uncertainty_proxy"
CALIBRATION_REFERENCE_ROLE = "calibration_reference"
GROUP_EXECUTION_ROLE = "repeated_seed_uncertainty"

PIXEL_REGION_IDS = (
    "full_image", "content_region", "masked_region", "mask_bbox_crop",
    "boundary_ring", "outside_mask_content",
)
LEARNED_REGION_IDS = ("content_region", "mask_bbox_crop")
FEATURE_MODEL_IDS = ("clip_vit_b32", "dinov2_vits14")
GROUP_KEY_COLUMNS = (
    "case_id", "prompt_policy_id", "prompt_variant_id", "configuration_id"
)
GROUP_METADATA_COLUMNS = (
    "uncertainty_group_id", "case_id", "model_id", "painting_id",
    "category", "style_or_period", "dataset_id", "dataset_scope",
    "experiment_id", "damage_or_degradation_type", "case_label",
    "target_damage_fraction", "realized_damage_fraction",
    "configuration_id", "prompt_policy_id", "prompt_variant_id",
    "execution_role", "seed_count", "expected_seed_count",
    "seed_coverage_status",
)

ProgressCallback = Callable[[str], None]


def load_diffusion_uncertainty_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the versioned Notebook 18 contract."""

    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Diffusion-uncertainty configuration must be a mapping")
    if payload.get("config_schema_version") != "diffusion_uncertainty_config.v1":
        raise ValueError("Unsupported diffusion-uncertainty configuration schema")
    settings = payload.get("diffusion_uncertainty")
    if not isinstance(settings, dict):
        raise ValueError("Configuration is missing diffusion_uncertainty")
    required = {
        "metric_version", "output_schema_version", "calibration_schema_version",
        "inputs", "output", "population", "regions", "metrics", "calibration",
        "execution", "expected_counts", "evidence_policy",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"diffusion_uncertainty is missing keys: {missing}")
    if settings["metric_version"] != DIFFUSION_UNCERTAINTY_METRIC_VERSION:
        raise ValueError("Configured metric version disagrees with the helper")
    if settings["output_schema_version"] != DIFFUSION_UNCERTAINTY_SCHEMA_VERSION:
        raise ValueError("Configured uncertainty schema version disagrees")
    if settings["calibration_schema_version"] != UNCERTAINTY_CALIBRATION_SCHEMA_VERSION:
        raise ValueError("Configured calibration schema version disagrees")
    population = settings["population"]
    if tuple(population["group_keys"]) != GROUP_KEY_COLUMNS:
        raise ValueError(f"group_keys must be exactly {GROUP_KEY_COLUMNS}")
    seeds = tuple(int(seed) for seed in population["expected_seeds"])
    if len(seeds) < 2 or len(seeds) != len(set(seeds)):
        raise ValueError("expected_seeds must contain at least two unique seeds")
    if tuple(settings["regions"]["pixel_regions"]) != PIXEL_REGION_IDS:
        raise ValueError(f"pixel_regions must be exactly {PIXEL_REGION_IDS}")
    if tuple(settings["regions"]["learned_metric_regions"]) != LEARNED_REGION_IDS:
        raise ValueError(f"learned_metric_regions must be exactly {LEARNED_REGION_IDS}")
    if bool(settings["metrics"]["combined_index"]["retained"]):
        raise ValueError("Notebook 18 must not retain a combined uncertainty index")
    execution = settings["execution"]
    for key in (
        "progress_interval_groups", "checkpoint_interval_groups",
        "lpips_batch_size", "atomic_replace_attempts",
    ):
        if int(execution[key]) <= 0:
            raise ValueError(f"{key} must be positive")
    return payload


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    settings = config.get("diffusion_uncertainty", config)
    if not isinstance(settings, Mapping):
        raise TypeError("diffusion_uncertainty settings must be a mapping")
    return settings


def _as_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    return series.fillna("").astype(str).str.strip().str.lower().isin(
        {"true", "1", "yes"}
    )


def resolve_path(path: str | Path, project_root: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else Path(project_root) / value


def _compact_hash(prefix: str, values: Sequence[Any], length: int = 20) -> str:
    payload = "|".join(str(value) for value in values)
    return prefix + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def make_uncertainty_group_id(
    case_id: str, prompt_policy_id: str, prompt_variant_id: str,
    configuration_id: str,
) -> str:
    """Return a deterministic prompt-specific repeated-seed group identifier."""

    return _compact_hash(
        "ug_", (case_id, prompt_policy_id, prompt_variant_id, configuration_id), 18
    )


def make_uncertainty_metric_id(
    uncertainty_group_id: str, observation_level: str, metric_name: str,
    region_id: str, summary_statistic: str, *, candidate_id: str = "",
    candidate_id_a: str = "", candidate_id_b: str = "",
    metric_version: str = DIFFUSION_UNCERTAINTY_METRIC_VERSION,
) -> str:
    """Return one compact deterministic evidence-row identifier."""

    return _compact_hash(
        "um_",
        (
            uncertainty_group_id, observation_level, metric_name, region_id,
            summary_statistic, candidate_id, candidate_id_a, candidate_id_b,
            metric_version,
        ),
    )


def build_uncertainty_population(
    worklist: pd.DataFrame,
    artworks: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select exact repeated-seed groups without mixing prompt variants."""

    required = {
        "candidate_id", "case_id", "model_id", "painting_id", "seed",
        "prompt_policy_id", "prompt_variant_id", "configuration_id",
        "execution_role", "restored_path", "restored_sha256", "mask_threshold",
        "dataset_id", "dataset_scope", "experiment_id", "input_image_path",
        "clean_image_path", "mask_or_effect_path",
        "damage_or_degradation_type", "target_damage_fraction",
        "realized_damage_fraction", "content_x_min", "content_y_min",
        "content_x_max", "content_y_max", "status",
    }
    missing = sorted(required - set(worklist.columns))
    if missing:
        raise ValueError(f"Evaluation worklist is missing columns: {missing}")
    artwork_required = {"painting_id", "category", "style_or_period"}
    missing_artwork = sorted(artwork_required - set(artworks.columns))
    if missing_artwork:
        raise ValueError(f"artworks is missing columns: {missing_artwork}")
    if artworks["painting_id"].astype(str).duplicated().any():
        raise ValueError("artworks contains duplicate painting_id values")

    settings = _settings(config)
    population_settings = settings["population"]
    expected_seeds = tuple(int(value) for value in population_settings["expected_seeds"])
    selected = worklist.loc[
        worklist["model_id"].astype(str).eq(population_settings["eligible_model_id"])
        & worklist["status"].astype(str).eq(population_settings["eligible_status"])
    ].copy()
    selected["seed"] = pd.to_numeric(selected["seed"], errors="raise").astype(int)
    selected = selected.loc[selected["seed"].isin(expected_seeds)].copy()
    if selected.empty:
        raise ValueError("No completed diffusion candidates match the expected seeds")

    eligible_indices: list[int] = []
    for _, group in selected.groupby(list(GROUP_KEY_COLUMNS), sort=True, dropna=False):
        seeds = tuple(sorted(group["seed"].astype(int).tolist()))
        if seeds == tuple(sorted(expected_seeds)) and not group["seed"].duplicated().any():
            eligible_indices.extend(group.index.tolist())
    population = selected.loc[eligible_indices].copy()
    population = population.merge(
        artworks[["painting_id", "category", "style_or_period"]],
        on="painting_id", how="left", validate="many_to_one",
    )
    if population["category"].isna().any():
        raise ValueError("Eligible candidates are missing artwork category metadata")
    population["category"] = population["category"].fillna("").astype(str).str.strip()
    if population["category"].eq("").any():
        raise ValueError("Eligible candidates contain blank artwork categories")
    population["style_or_period"] = (
        population["style_or_period"].fillna("").astype(str).str.strip()
        .replace("", "unclassified")
    )
    population["case_label"] = population["case_id"].astype(str).str.rsplit("__", n=1).str[-1]
    population["uncertainty_group_id"] = population.apply(
        lambda row: make_uncertainty_group_id(
            str(row["case_id"]), str(row["prompt_policy_id"]),
            str(row["prompt_variant_id"]), str(row["configuration_id"]),
        ), axis=1,
    )
    group_counts = population.groupby("uncertainty_group_id")["seed"].transform("size")
    population["seed_count"] = group_counts.astype(int)
    population["expected_seed_count"] = len(expected_seeds)
    population["seed_coverage_status"] = np.where(
        population["seed_count"].eq(len(expected_seeds)), "complete", "insufficient"
    )
    population["source_execution_role"] = population["execution_role"].astype(str)
    population["execution_role"] = GROUP_EXECUTION_ROLE
    population = population.sort_values(
        ["case_id", "prompt_variant_id", "configuration_id", "seed", "candidate_id"],
        kind="stable",
    ).reset_index(drop=True)

    if population["candidate_id"].astype(str).duplicated().any():
        raise ValueError("Eligible uncertainty population repeats candidate_id")
    if population["uncertainty_group_id"].nunique() == 0:
        raise ValueError("No complete uncertainty groups were constructed")
    expected = settings.get("expected_counts", {})
    for key, actual in {
        "uncertainty_groups": population["uncertainty_group_id"].nunique(),
        "unique_cases": population["case_id"].nunique(),
        "candidates": len(population),
    }.items():
        if key in expected and int(expected[key]) != int(actual):
            raise ValueError(f"Expected {key}={expected[key]}, observed {actual}")
    return population


def build_uncertainty_pair_plan(population: pd.DataFrame) -> pd.DataFrame:
    """Build all unique unordered candidate pairs within each exact group."""

    required = {"uncertainty_group_id", "candidate_id", "seed"}
    missing = sorted(required - set(population.columns))
    if missing:
        raise ValueError(f"Uncertainty population is missing columns: {missing}")
    records: list[dict[str, Any]] = []
    for group_id, group in population.groupby("uncertainty_group_id", sort=True):
        ordered = group.sort_values(["seed", "candidate_id"], kind="stable")
        for left, right in itertools.combinations(ordered.to_dict("records"), 2):
            record = {column: left[column] for column in GROUP_METADATA_COLUMNS}
            record.update({
                "candidate_id_a": str(left["candidate_id"]),
                "candidate_id_b": str(right["candidate_id"]),
                "seed_a": int(left["seed"]),
                "seed_b": int(right["seed"]),
                "restored_path_a": str(left["restored_path"]),
                "restored_path_b": str(right["restored_path"]),
            })
            records.append(record)
    result = pd.DataFrame(records)
    if result.empty:
        raise ValueError("Uncertainty pair plan is empty")
    if result.duplicated(["uncertainty_group_id", "candidate_id_a", "candidate_id_b"]).any():
        raise ValueError("Uncertainty pair plan contains duplicate unordered pairs")
    if not (result["seed_a"].astype(int) < result["seed_b"].astype(int)).all():
        raise ValueError("Candidate-pair ordering must satisfy seed_a < seed_b")
    return result.reset_index(drop=True)


def load_rgb_array(path: str | Path, project_root: str | Path) -> np.ndarray:
    resolved = resolve_path(path, project_root)
    if not resolved.is_file():
        raise FileNotFoundError(f"RGB image not found: {resolved}")
    with Image.open(resolved) as image:
        return np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0


def load_mask_array(path: str | Path, project_root: str | Path) -> np.ndarray:
    resolved = resolve_path(path, project_root)
    if not resolved.is_file():
        raise FileNotFoundError(f"Mask image not found: {resolved}")
    with Image.open(resolved) as image:
        return np.asarray(image.convert("L"), dtype=np.uint8)


def build_uncertainty_regions(
    row: Mapping[str, Any] | pd.Series,
    raw_mask: np.ndarray,
    *,
    config: Mapping[str, Any],
) -> dict[str, Region]:
    """Build the six approved regions through the canonical region helper."""

    region_settings = _settings(config)["regions"]
    active_mask = np.asarray(raw_mask) >= int(float(row["mask_threshold"]))
    content_bbox = tuple(
        int(float(row[column]))
        for column in ("content_x_min", "content_y_min", "content_x_max", "content_y_max")
    )
    regions = build_standard_regions(
        active_mask,
        content_bbox=content_bbox,
        mask_bbox_margin=int(region_settings["mask_bbox_margin_pixels"]),
        boundary_width_pixels=int(region_settings["boundary_width_pixels"]),
    )
    result = {
        region_id: regions[region_id]
        for region_id in region_settings["pixel_regions"]
        if regions[region_id].validity_status == "valid"
    }
    missing = sorted(set(region_settings["pixel_regions"]) - set(result))
    if missing:
        raise ValueError(f"Required uncertainty regions are invalid or empty: {missing}")
    return result


def _group_base(group: pd.DataFrame) -> dict[str, Any]:
    first = group.iloc[0]
    return {column: first[column] for column in GROUP_METADATA_COLUMNS}


def _metric_record(
    base: Mapping[str, Any], *, observation_level: str, metric_family: str,
    metric_name: str, region_id: str, summary_statistic: str, value: float,
    value_unit: str, candidate_id: str = "", seed: int | float | str = np.nan,
    candidate_id_a: str = "", candidate_id_b: str = "",
    seed_a: int | float | str = np.nan, seed_b: int | float | str = np.nan,
    evidence_role: str = UNCERTAINTY_EVIDENCE_ROLE,
    metric_version: str = DIFFUSION_UNCERTAINTY_METRIC_VERSION,
    status: str = "ok", issue: str = "",
) -> dict[str, Any]:
    record = dict(base)
    record.update({
        "uncertainty_metric_id": make_uncertainty_metric_id(
            str(base["uncertainty_group_id"]), observation_level, metric_name,
            region_id, summary_statistic, candidate_id=candidate_id,
            candidate_id_a=candidate_id_a, candidate_id_b=candidate_id_b,
            metric_version=metric_version,
        ),
        "observation_level": observation_level,
        "candidate_id": candidate_id,
        "seed": seed,
        "candidate_id_a": candidate_id_a,
        "candidate_id_b": candidate_id_b,
        "seed_a": seed_a,
        "seed_b": seed_b,
        "metric_family": metric_family,
        "metric_name": metric_name,
        "region_id": region_id,
        "summary_statistic": summary_statistic,
        "value": float(value),
        "value_unit": value_unit,
        "metric_version": metric_version,
        "region_policy_version": "evaluation_region_policy.v1",
        "evidence_role": evidence_role,
        "is_combined_index": False,
        "status": status,
        "issue": issue,
    })
    return {column: record.get(column, "") for column in DIFFUSION_UNCERTAINTY_COLUMNS}


def compute_group_image_uncertainty(
    group: pd.DataFrame,
    *,
    project_root: str | Path,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Compute per-pixel and pairwise RGB variability for one seed group."""

    expected_seeds = tuple(int(value) for value in _settings(config)["population"]["expected_seeds"])
    ordered = group.sort_values(["seed", "candidate_id"], kind="stable")
    if tuple(ordered["seed"].astype(int)) != tuple(sorted(expected_seeds)):
        raise ValueError("Image uncertainty requires the exact configured seed set")
    arrays = [load_rgb_array(path, project_root) for path in ordered["restored_path"]]
    shapes = {array.shape for array in arrays}
    if len(shapes) != 1:
        raise ValueError(f"Seed candidates have inconsistent shapes: {sorted(shapes)}")
    stack = np.stack(arrays, axis=0).astype(np.float32)
    raw_mask = load_mask_array(ordered.iloc[0]["mask_or_effect_path"], project_root)
    if raw_mask.shape != stack.shape[1:3]:
        raise ValueError("Candidate and mask geometry disagree")
    regions = build_uncertainty_regions(ordered.iloc[0], raw_mask, config=config)
    base = _group_base(ordered)
    records: list[dict[str, Any]] = []

    ddof = int(_settings(config)["metrics"]["pixel_variability"]["seed_standard_deviation_ddof"])
    pixel_std = stack.std(axis=0, ddof=ddof).mean(axis=2)
    for region_id in PIXEL_REGION_IDS:
        values = pixel_std[regions[region_id].mask]
        records.append(_metric_record(
            base, observation_level="group_summary", metric_family="pixel_variability",
            metric_name="pixel_rgb_std_mean", region_id=region_id,
            summary_statistic="mean", value=float(values.mean()),
            value_unit="normalized_rgb_0_1",
        ))
        records.append(_metric_record(
            base, observation_level="group_summary", metric_family="pixel_variability",
            metric_name="pixel_rgb_std_p95", region_id=region_id,
            summary_statistic="p95", value=float(np.percentile(values, 95)),
            value_unit="normalized_rgb_0_1",
        ))

    rows = ordered.to_dict("records")
    for left_index, right_index in itertools.combinations(range(len(rows)), 2):
        left, right = rows[left_index], rows[right_index]
        absolute = np.abs(stack[left_index] - stack[right_index])
        squared = np.square(stack[left_index] - stack[right_index])
        for region_id in PIXEL_REGION_IDS:
            mask = regions[region_id].mask
            mae = float(absolute[mask].mean())
            rmse = float(np.sqrt(squared[mask].mean()))
            common = {
                "observation_level": "candidate_pair",
                "metric_family": "pixel_pairwise", "region_id": region_id,
                "summary_statistic": "pair_value",
                "value_unit": "normalized_rgb_0_1",
                "candidate_id_a": str(left["candidate_id"]),
                "candidate_id_b": str(right["candidate_id"]),
                "seed_a": int(left["seed"]), "seed_b": int(right["seed"]),
            }
            records.append(_metric_record(
                base, metric_name="pairwise_rgb_mae", value=mae, **common
            ))
            records.append(_metric_record(
                base, metric_name="pairwise_rgb_rmse", value=rmse, **common
            ))
    return pd.DataFrame(records, columns=DIFFUSION_UNCERTAINTY_COLUMNS)


def compute_group_lpips_uncertainty(
    group: pd.DataFrame,
    *,
    model: Any,
    device: str,
    project_root: str | Path,
    config: Mapping[str, Any],
    lpips_config: Mapping[str, Any],
) -> pd.DataFrame:
    """Compute all six unordered LPIPS pairs for both approved crops."""

    import torch

    ordered = group.sort_values(["seed", "candidate_id"], kind="stable")
    raw_mask = load_mask_array(ordered.iloc[0]["mask_or_effect_path"], project_root)
    lpips_regions = build_case_lpips_regions(ordered.iloc[0], raw_mask, lpips_config)
    if tuple(lpips_regions) != LEARNED_REGION_IDS:
        raise ValueError(f"LPIPS regions disagree with the uncertainty contract: {tuple(lpips_regions)}")
    base = _group_base(ordered)
    records: list[dict[str, Any]] = []
    pairs = list(itertools.combinations(range(len(ordered)), 2))
    ordered_rows = ordered.to_dict("records")
    for region_id in LEARNED_REGION_IDS:
        region = lpips_regions[region_id]
        tensors = []
        for path in ordered["restored_path"]:
            array = load_rgb_array(path, project_root)
            crop = array[region.y_min:region.y_max, region.x_min:region.x_max]
            tensor, _ = prepare_lpips_tensor(crop * 255.0, lpips_config)
            tensors.append(tensor)
        references = torch.stack([tensors[left] for left, _ in pairs])
        candidates = torch.stack([tensors[right] for _, right in pairs])
        values, _ = compute_lpips_batch(
            model, references, candidates, device=str(device)
        )
        for (left_index, right_index), value in zip(pairs, values, strict=True):
            left, right = ordered_rows[left_index], ordered_rows[right_index]
            records.append(_metric_record(
                base, observation_level="candidate_pair",
                metric_family="perceptual_pairwise",
                metric_name="pairwise_lpips_distance", region_id=region_id,
                summary_statistic="pair_value", value=float(value),
                value_unit="lpips_distance",
                candidate_id_a=str(left["candidate_id"]),
                candidate_id_b=str(right["candidate_id"]),
                seed_a=int(left["seed"]), seed_b=int(right["seed"]),
            ))
    return pd.DataFrame(records, columns=DIFFUSION_UNCERTAINTY_COLUMNS)


def build_embedding_lookup(
    embedding_manifest: pd.DataFrame,
    embedding_arrays: Mapping[str, np.ndarray],
    candidate_ids: Sequence[str],
) -> dict[tuple[str, str, str], np.ndarray]:
    """Resolve restored-candidate CLIP/DINO vectors from Notebook 15."""

    required = {
        "feature_model_id", "image_role", "representative_candidate_id",
        "region_id", "array_name", "array_index", "status",
    }
    missing = sorted(required - set(embedding_manifest.columns))
    if missing:
        raise ValueError(f"Embedding manifest is missing columns: {missing}")
    candidates = {str(value) for value in candidate_ids}
    selected = embedding_manifest.loc[
        embedding_manifest["image_role"].astype(str).eq("restored")
        & embedding_manifest["status"].astype(str).eq("ok")
        & embedding_manifest["representative_candidate_id"].astype(str).isin(candidates)
        & embedding_manifest["region_id"].astype(str).isin(LEARNED_REGION_IDS)
        & embedding_manifest["feature_model_id"].astype(str).isin(FEATURE_MODEL_IDS)
    ].copy()
    keys = ["representative_candidate_id", "region_id", "feature_model_id"]
    if selected.duplicated(keys).any():
        raise ValueError("Embedding manifest repeats a candidate/region/model key")
    expected = len(candidates) * len(LEARNED_REGION_IDS) * len(FEATURE_MODEL_IDS)
    if len(selected) != expected:
        raise ValueError(f"Expected {expected} eligible restored embeddings, observed {len(selected)}")
    lookup: dict[tuple[str, str, str], np.ndarray] = {}
    for row in selected.itertuples(index=False):
        array_name = str(row.array_name)
        if array_name not in embedding_arrays:
            raise ValueError(f"Embedding bundle is missing array {array_name}")
        index = int(row.array_index)
        matrix = np.asarray(embedding_arrays[array_name])
        if index < 0 or index >= len(matrix):
            raise ValueError(f"Embedding index {index} is outside {array_name}")
        vector = np.asarray(matrix[index], dtype=np.float32)
        if vector.ndim != 1 or not np.isfinite(vector).all():
            raise ValueError("Embedding vector must be finite and one-dimensional")
        lookup[(str(row.representative_candidate_id), str(row.region_id), str(row.feature_model_id))] = vector
    return lookup


def compute_feature_pairwise_uncertainty(
    population: pd.DataFrame,
    *,
    embedding_manifest: pd.DataFrame,
    embedding_arrays: Mapping[str, np.ndarray],
    config: Mapping[str, Any],
    progress_callback: ProgressCallback | None = None,
) -> pd.DataFrame:
    """Compute pairwise cosine distances from persisted Notebook 15 vectors."""

    lookup = build_embedding_lookup(
        embedding_manifest, embedding_arrays, population["candidate_id"].astype(str)
    )
    metric_names = _settings(config)["metrics"]["feature_pairwise"]["metric_names"]
    interval = int(_settings(config)["execution"]["progress_interval_groups"])
    records: list[dict[str, Any]] = []
    grouped = list(population.groupby("uncertainty_group_id", sort=True))
    for number, (_, group) in enumerate(grouped, start=1):
        ordered = group.sort_values(["seed", "candidate_id"], kind="stable")
        base = _group_base(ordered)
        rows = ordered.to_dict("records")
        for left_index, right_index in itertools.combinations(range(len(rows)), 2):
            left, right = rows[left_index], rows[right_index]
            for region_id in LEARNED_REGION_IDS:
                for model_id in FEATURE_MODEL_IDS:
                    a = lookup[(str(left["candidate_id"]), region_id, model_id)]
                    b = lookup[(str(right["candidate_id"]), region_id, model_id)]
                    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
                    if denominator <= 0:
                        raise ValueError("Cannot compute cosine distance for a zero vector")
                    distance = 1.0 - float(np.dot(a, b) / denominator)
                    records.append(_metric_record(
                        base, observation_level="candidate_pair",
                        metric_family="feature_pairwise",
                        metric_name=str(metric_names[model_id]), region_id=region_id,
                        summary_statistic="pair_value", value=distance,
                        value_unit="cosine_distance",
                        candidate_id_a=str(left["candidate_id"]),
                        candidate_id_b=str(right["candidate_id"]),
                        seed_a=int(left["seed"]), seed_b=int(right["seed"]),
                    ))
        if progress_callback and (number % interval == 0 or number == len(grouped)):
            progress_callback(
                f"Feature uncertainty: {number}/{len(grouped)} groups; latest={base['uncertainty_group_id']}"
            )
    return pd.DataFrame(records, columns=DIFFUSION_UNCERTAINTY_COLUMNS)


def write_dataframe_checkpoint(
    dataframe: pd.DataFrame,
    path: str | Path,
    *,
    attempts: int = 8,
    retry_delay_seconds: float = 0.25,
) -> dict[str, Any]:
    """Write CSV with bounded Windows-lock retries and recovery fallback."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".{target.name}.{uuid.uuid4().hex}.tmp"
    dataframe.to_csv(temporary, index=False)
    delay = float(retry_delay_seconds)
    last_error = ""
    for attempt in range(1, int(attempts) + 1):
        try:
            os.replace(temporary, target)
            return {"status": "canonical", "path": target, "attempts": attempt, "issue": ""}
        except PermissionError as error:
            last_error = f"{type(error).__name__}: {error}"
            if attempt < int(attempts):
                time.sleep(delay)
                delay = min(delay * 2.0, 2.0)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    recovery = target.with_name(f"{target.stem}.recovery-{stamp}{target.suffix}")
    os.replace(temporary, recovery)
    return {"status": "recovery", "path": recovery, "attempts": int(attempts), "issue": last_error}


def find_latest_checkpoint(path: str | Path) -> Path | None:
    target = Path(path)
    candidates = [target] if target.is_file() else []
    candidates.extend(
        item for item in target.parent.glob(f"{target.stem}.recovery-*{target.suffix}")
        if item.is_file()
    )
    return max(candidates, key=lambda item: item.stat().st_mtime_ns) if candidates else None


def load_latest_checkpoint(path: str | Path) -> tuple[pd.DataFrame, Path | None]:
    latest = find_latest_checkpoint(path)
    if latest is None:
        return pd.DataFrame(columns=DIFFUSION_UNCERTAINTY_COLUMNS), None
    frame = pd.read_csv(latest, keep_default_na=False)
    missing = sorted(set(DIFFUSION_UNCERTAINTY_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Checkpoint {latest} is missing columns: {missing}")
    return frame.loc[:, DIFFUSION_UNCERTAINTY_COLUMNS], latest


def _complete_checkpoint_groups(
    checkpoint: pd.DataFrame, *, expected_rows_per_group: int,
) -> set[str]:
    if checkpoint.empty:
        return set()
    ok = checkpoint["status"].astype(str).eq("ok")
    counts = checkpoint.loc[ok].groupby("uncertainty_group_id").size()
    return set(counts.index[counts.eq(int(expected_rows_per_group))].astype(str))


def _run_checkpointed_groups(
    population: pd.DataFrame,
    *,
    compute_group: Callable[[pd.DataFrame], pd.DataFrame],
    expected_rows_per_group: int,
    checkpoint_path: str | Path,
    config: Mapping[str, Any],
    stage_label: str,
    progress_callback: ProgressCallback | None,
) -> pd.DataFrame:
    execution = _settings(config)["execution"]
    checkpoint, loaded_path = load_latest_checkpoint(checkpoint_path)
    complete = _complete_checkpoint_groups(
        checkpoint, expected_rows_per_group=expected_rows_per_group
    )
    retained = checkpoint.loc[
        checkpoint["uncertainty_group_id"].astype(str).isin(complete)
    ].copy()
    grouped = list(population.groupby("uncertainty_group_id", sort=True))
    pending = [(group_id, group) for group_id, group in grouped if str(group_id) not in complete]
    records = retained.to_dict("records")
    interval = int(execution["progress_interval_groups"])
    checkpoint_interval = int(execution["checkpoint_interval_groups"])
    if progress_callback:
        progress_callback(
            f"{stage_label}: {len(complete)} complete groups resumed from "
            f"{loaded_path.name if loaded_path else 'no checkpoint'}; {len(pending)} pending"
        )
    completed_now = 0
    try:
        for group_id, group in pending:
            result = compute_group(group)
            if len(result) != int(expected_rows_per_group):
                raise ValueError(
                    f"Group {group_id} produced {len(result)} rows; expected {expected_rows_per_group}"
                )
            records.extend(result.to_dict("records"))
            completed_now += 1
            total_complete = len(complete) + completed_now
            if completed_now % checkpoint_interval == 0 or completed_now == len(pending):
                write_dataframe_checkpoint(
                    pd.DataFrame(records, columns=DIFFUSION_UNCERTAINTY_COLUMNS),
                    checkpoint_path,
                    attempts=int(execution["atomic_replace_attempts"]),
                    retry_delay_seconds=float(execution["atomic_replace_retry_seconds"]),
                )
            if progress_callback and (
                total_complete % interval == 0 or completed_now == len(pending)
            ):
                progress_callback(
                    f"{stage_label}: {total_complete}/{len(grouped)} groups; latest={group_id}"
                )
    except Exception:
        write_dataframe_checkpoint(
            pd.DataFrame(records, columns=DIFFUSION_UNCERTAINTY_COLUMNS),
            checkpoint_path,
            attempts=int(execution["atomic_replace_attempts"]),
            retry_delay_seconds=float(execution["atomic_replace_retry_seconds"]),
        )
        raise
    result = pd.DataFrame(records, columns=DIFFUSION_UNCERTAINTY_COLUMNS)
    return result.sort_values(
        ["uncertainty_group_id", "metric_family", "metric_name", "region_id",
         "candidate_id", "candidate_id_a", "candidate_id_b"],
        kind="stable", na_position="first"
    ).reset_index(drop=True)


def run_image_space_uncertainty(
    population: pd.DataFrame,
    *,
    project_root: str | Path,
    config: Mapping[str, Any],
    checkpoint_path: str | Path,
    progress_callback: ProgressCallback | None = None,
) -> pd.DataFrame:
    return _run_checkpointed_groups(
        population,
        compute_group=lambda group: compute_group_image_uncertainty(
            group, project_root=project_root, config=config
        ),
        expected_rows_per_group=84,
        checkpoint_path=checkpoint_path, config=config,
        stage_label="Image-space uncertainty", progress_callback=progress_callback,
    )


def run_lpips_pairwise_uncertainty(
    population: pd.DataFrame,
    *,
    model: Any,
    device: str,
    project_root: str | Path,
    config: Mapping[str, Any],
    lpips_config: Mapping[str, Any],
    checkpoint_path: str | Path,
    progress_callback: ProgressCallback | None = None,
) -> pd.DataFrame:
    return _run_checkpointed_groups(
        population,
        compute_group=lambda group: compute_group_lpips_uncertainty(
            group, model=model, device=device, project_root=project_root,
            config=config, lpips_config=lpips_config,
        ),
        expected_rows_per_group=12,
        checkpoint_path=checkpoint_path, config=config,
        stage_label="Pairwise LPIPS uncertainty", progress_callback=progress_callback,
    )


def build_seed_reference_rows(
    population: pd.DataFrame,
    source_tables: Mapping[str, pd.DataFrame],
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Retain selected seed-level upstream evidence without aggregation."""

    family_by_source = {
        "classical": "classical_reference",
        "lpips": "perceptual_reference",
        "feature": "feature_reference",
        "local_consistency": "local_consistency_reference",
    }
    candidate_lookup = population.set_index("candidate_id", drop=False)
    records: list[dict[str, Any]] = []
    for specification in _settings(config)["calibration"]["reference_metrics"]:
        source = str(specification["source"])
        if source not in source_tables:
            raise ValueError(f"Missing calibration source table: {source}")
        frame = source_tables[source]
        required = {"candidate_id", "metric_name", "region_id", "status", specification["value_column"]}
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"Calibration source {source} is missing columns: {missing}")
        selected = frame.loc[
            frame["candidate_id"].astype(str).isin(candidate_lookup.index.astype(str))
            & frame["metric_name"].astype(str).eq(str(specification["metric_name"]))
            & frame["region_id"].astype(str).eq(str(specification["region_id"]))
            & frame["status"].astype(str).eq("ok")
        ].copy()
        if selected["candidate_id"].astype(str).duplicated().any():
            raise ValueError(
                f"Calibration selection {specification['alias']} repeats candidate_id"
            )
        if len(selected) != len(population):
            raise ValueError(
                f"Calibration selection {specification['alias']} expected "
                f"{len(population)} rows, observed {len(selected)}"
            )
        for source_row in selected.itertuples(index=False):
            candidate = candidate_lookup.loc[str(source_row.candidate_id)]
            base = {column: candidate[column] for column in GROUP_METADATA_COLUMNS}
            value = float(getattr(source_row, str(specification["value_column"])))
            source_version = str(getattr(source_row, "metric_version", DIFFUSION_UNCERTAINTY_METRIC_VERSION))
            unit = (
                str(getattr(source_row, "value_unit"))
                if hasattr(source_row, "value_unit") else _reference_value_unit(str(specification["alias"]))
            )
            records.append(_metric_record(
                base, observation_level="seed_reference",
                metric_family=family_by_source[source],
                metric_name=str(specification["alias"]),
                region_id=str(specification["region_id"]),
                summary_statistic="seed_value", value=value, value_unit=unit,
                candidate_id=str(candidate["candidate_id"]),
                seed=int(candidate["seed"]), evidence_role=CALIBRATION_REFERENCE_ROLE,
                metric_version=source_version,
            ))
    return pd.DataFrame(records, columns=DIFFUSION_UNCERTAINTY_COLUMNS)


def _reference_value_unit(alias: str) -> str:
    if "psnr" in alias:
        return "dB"
    if "ssim" in alias or "clip" in alias or "dino" in alias:
        return "similarity"
    if "lpips" in alias:
        return "lpips_distance"
    if "mae" in alias:
        return "native_rgb_0_255"
    return "source_metric_unit"


def _metric_values(
    metrics: pd.DataFrame, metric_name: str, region_id: str,
) -> pd.DataFrame:
    return metrics.loc[
        metrics["metric_name"].astype(str).eq(metric_name)
        & metrics["region_id"].astype(str).eq(region_id)
        & metrics["status"].astype(str).eq("ok"),
        ["uncertainty_group_id", "value"],
    ].copy()


def build_uncertainty_calibration_inputs(
    population: pd.DataFrame,
    metrics: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build one calibration-ready row per independent uncertainty group."""

    records = []
    expected_seeds = tuple(int(value) for value in _settings(config)["population"]["expected_seeds"])
    for _, group in population.groupby("uncertainty_group_id", sort=True):
        first = group.iloc[0]
        record = {column: first[column] for column in GROUP_METADATA_COLUMNS}
        record["seeds"] = "|".join(str(value) for value in sorted(group["seed"].astype(int)))
        records.append(record)
    calibration = pd.DataFrame(records)

    components = {
        "rgb_std_mean_masked": ("pixel_rgb_std_mean", "masked_region"),
        "rgb_std_p95_masked": ("pixel_rgb_std_p95", "masked_region"),
        "rgb_pair_mae_mean_masked": ("pairwise_rgb_mae", "masked_region"),
        "rgb_pair_rmse_mean_masked": ("pairwise_rgb_rmse", "masked_region"),
        "lpips_pair_mean_content": ("pairwise_lpips_distance", "content_region"),
        "lpips_pair_mean_crop": ("pairwise_lpips_distance", "mask_bbox_crop"),
        "clip_pair_distance_mean_content": ("pairwise_clip_cosine_distance", "content_region"),
        "clip_pair_distance_mean_crop": ("pairwise_clip_cosine_distance", "mask_bbox_crop"),
        "dino_pair_distance_mean_content": ("pairwise_dinov2_cosine_distance", "content_region"),
        "dino_pair_distance_mean_crop": ("pairwise_dinov2_cosine_distance", "mask_bbox_crop"),
    }
    for output_column, (metric_name, region_id) in components.items():
        values = _metric_values(metrics, metric_name, region_id)
        summary = values.groupby("uncertainty_group_id")["value"].mean()
        calibration[output_column] = calibration["uncertainty_group_id"].map(summary)

    for specification in _settings(config)["calibration"]["reference_metrics"]:
        alias = str(specification["alias"])
        values = _metric_values(metrics, alias, str(specification["region_id"]))
        grouped = values.groupby("uncertainty_group_id")["value"]
        mean = grouped.mean()
        standard_deviation = grouped.std(ddof=1)
        worst = grouped.min() if bool(specification["higher_is_better"]) else grouped.max()
        calibration[f"{alias}_mean"] = calibration["uncertainty_group_id"].map(mean)
        calibration[f"{alias}_std"] = calibration["uncertainty_group_id"].map(standard_deviation)
        calibration[f"{alias}_worst"] = calibration["uncertainty_group_id"].map(worst)

    calibration["semantic_evidence_available"] = False
    calibration["human_review_flag_available"] = False
    calibration["failure_category_available"] = False
    calibration["combined_uncertainty_index_available"] = False
    calibration["calibration_scope"] = "pre_semantic_pre_human_partial"
    calibration["schema_version"] = UNCERTAINTY_CALIBRATION_SCHEMA_VERSION
    calibration["status"] = "ok"
    calibration["issue"] = ""
    calibration = calibration.loc[:, UNCERTAINTY_CALIBRATION_INPUTS_COLUMNS]
    if calibration.drop(columns=["issue"]).isna().any().any():
        missing_columns = calibration.columns[
            calibration.drop(columns=["issue"]).isna().any().reindex(calibration.columns, fill_value=False)
        ].tolist()
        raise ValueError(f"Calibration inputs contain missing evidence: {missing_columns}")
    if not calibration["seeds"].eq("|".join(map(str, sorted(expected_seeds)))).all():
        raise ValueError("Calibration rows do not retain the exact configured seeds")
    return calibration


def validate_uncertainty_metrics(
    metrics: pd.DataFrame,
    population: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Return compact structural and scientific validation evidence."""

    schema = validate_dataframe(metrics, DIFFUSION_UNCERTAINTY_SCHEMA)
    settings = _settings(config)
    expected = settings["expected_counts"]
    values = pd.to_numeric(metrics["value"], errors="coerce") if "value" in metrics else pd.Series(dtype=float)
    pair_rows = metrics["observation_level"].astype(str).eq("candidate_pair") if "observation_level" in metrics else pd.Series(False, index=metrics.index)
    pair_order_ok = bool(
        (pd.to_numeric(metrics.loc[pair_rows, "seed_a"], errors="coerce")
         < pd.to_numeric(metrics.loc[pair_rows, "seed_b"], errors="coerce")).all()
    )
    family_counts = metrics.groupby("metric_family").size().to_dict() if "metric_family" in metrics else {}
    candidate_count = int(expected["candidates"])
    expected_families = {
        "pixel_variability": int(expected["pixel_group_summary_rows"]),
        "pixel_pairwise": int(expected["pixel_pair_rows"]),
        "perceptual_pairwise": int(expected["lpips_pair_rows"]),
        "feature_pairwise": int(expected["feature_pair_rows"]),
        "classical_reference": candidate_count * 3,
        "perceptual_reference": candidate_count,
        "feature_reference": candidate_count * 2,
        "local_consistency_reference": candidate_count * 4,
    }
    family_counts_ok = all(int(family_counts.get(key, -1)) == value for key, value in expected_families.items())
    cosine = metrics["metric_name"].astype(str).str.contains("cosine_distance", regex=False)
    cosine_values = values.loc[cosine]
    cosine_range_ok = bool(cosine_values.between(-1e-6, 2.000001).all())
    passed = bool(
        schema.passed
        and len(metrics) == int(expected["uncertainty_metric_rows"])
        and population["uncertainty_group_id"].nunique() == int(expected["uncertainty_groups"])
        and population["candidate_id"].nunique() == int(expected["candidates"])
        and values.notna().all() and np.isfinite(values).all()
        and pair_order_ok and family_counts_ok and cosine_range_ok
        and not _as_bool(metrics["is_combined_index"]).any()
    )
    return {
        "schema": schema.to_dict(),
        "metric_rows": int(len(metrics)),
        "uncertainty_groups": int(population["uncertainty_group_id"].nunique()),
        "candidates": int(population["candidate_id"].nunique()),
        "family_counts": {str(key): int(value) for key, value in family_counts.items()},
        "family_counts_match": family_counts_ok,
        "all_values_finite": bool(values.notna().all() and np.isfinite(values).all()),
        "pair_order_ok": pair_order_ok,
        "cosine_distance_range_ok": cosine_range_ok,
        "combined_index_absent": bool(not _as_bool(metrics["is_combined_index"]).any()),
        "passed": passed,
    }


def validate_uncertainty_calibration_inputs(
    calibration: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    schema = validate_dataframe(calibration, UNCERTAINTY_CALIBRATION_INPUTS_SCHEMA)
    expected_rows = int(_settings(config)["expected_counts"]["calibration_rows"])
    numeric = calibration.select_dtypes(include=[np.number]).drop(
        columns=[
            "target_damage_fraction", "realized_damage_fraction", "seed_count",
            "expected_seed_count", "issue",
        ], errors="ignore",
    )
    finite = bool(np.isfinite(numeric.to_numpy(dtype=float)).all())
    unavailable = bool(
        not pd.concat([
            _as_bool(calibration[column]).rename(column)
            for column in (
                "semantic_evidence_available", "human_review_flag_available",
                "failure_category_available", "combined_uncertainty_index_available",
            )
        ], axis=1).any().any()
    )
    passed = bool(schema.passed and len(calibration) == expected_rows and finite and unavailable)
    return {
        "schema": schema.to_dict(), "row_count": int(len(calibration)),
        "all_numeric_evidence_finite": finite,
        "downstream_evidence_correctly_unavailable": unavailable,
        "passed": passed,
    }


def summarize_uncertainty(
    calibration: pd.DataFrame,
    *,
    group_columns: Sequence[str],
    value_columns: Sequence[str],
) -> pd.DataFrame:
    """Create an in-memory descriptive summary without persisting extra CSVs."""

    missing = sorted((set(group_columns) | set(value_columns)) - set(calibration.columns))
    if missing:
        raise ValueError(f"Summary columns are missing: {missing}")
    summary = calibration.groupby(list(group_columns), dropna=False)[list(value_columns)].agg(
        ["count", "mean", "median", "std"]
    )
    summary.columns = [f"{metric}_{statistic}" for metric, statistic in summary.columns]
    return summary.reset_index()


def render_uncertainty_distributions(
    calibration: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    """Render transparent component distributions without a composite score."""

    import matplotlib.pyplot as plt

    panels = (
        ("rgb_std_mean_masked", "Masked RGB standard deviation"),
        ("rgb_pair_mae_mean_masked", "Masked pairwise RGB MAE"),
        ("lpips_pair_mean_crop", "Mask-crop pairwise LPIPS"),
        ("clip_pair_distance_mean_crop", "Mask-crop CLIP distance"),
        ("dino_pair_distance_mean_crop", "Mask-crop DINOv2 distance"),
        ("seam_gradient_mismatch_mean", "Reference seam mismatch"),
    )
    prompts = sorted(calibration["prompt_variant_id"].astype(str).unique())
    colors = ["#3264a8", "#d1752f", "#6a4c93", "#3b8b6b"]
    figure, axes = plt.subplots(2, 3, figsize=(16, 9), constrained_layout=True)
    for axis, (column, title) in zip(axes.flat, panels, strict=True):
        data = [
            pd.to_numeric(
                calibration.loc[calibration["prompt_variant_id"].astype(str).eq(prompt), column],
                errors="coerce",
            ).dropna().to_numpy()
            for prompt in prompts
        ]
        boxplot = axis.boxplot(
            data,
            tick_labels=prompts,
            showfliers=False,
            patch_artist=True,
        )
        for patch, color in zip(boxplot["boxes"], colors, strict=False):
            patch.set_facecolor(color)
            patch.set_alpha(0.65)
        axis.set_title(title)
        axis.tick_params(axis="x", rotation=20)
        axis.grid(axis="y", alpha=0.25)
    figure.suptitle(
        "Empirical diffusion seed variability — transparent components",
        fontsize=15,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(target, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return target


def render_uncertainty_vs_performance(
    calibration: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    """Render descriptive uncertainty/performance relationships."""

    import matplotlib.pyplot as plt

    panels = (
        ("rgb_pair_mae_mean_masked", "reference_mae_masked_mean", "RGB variability", "Reference MAE"),
        ("lpips_pair_mean_crop", "reference_lpips_crop_mean", "LPIPS variability", "Reference LPIPS"),
        ("clip_pair_distance_mean_crop", "reference_clip_crop_mean", "CLIP variability", "Reference CLIP similarity"),
        ("rgb_std_mean_masked", "seam_gradient_mismatch_mean", "Pixel variability", "Seam mismatch"),
    )
    prompts = sorted(calibration["prompt_variant_id"].astype(str).unique())
    colors = {prompt: color for prompt, color in zip(prompts, ("#3264a8", "#d1752f", "#6a4c93"), strict=False)}
    figure, axes = plt.subplots(2, 2, figsize=(13, 10))
    for axis, (x_column, y_column, x_label, y_label) in zip(axes.flat, panels, strict=True):
        for prompt in prompts:
            subset = calibration.loc[calibration["prompt_variant_id"].astype(str).eq(prompt)]
            axis.scatter(
                subset[x_column], subset[y_column], s=28, alpha=0.7,
                color=colors[prompt], label=prompt,
            )
        axis.set_xlabel(x_label)
        axis.set_ylabel(y_label)
        axis.grid(alpha=0.25)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.935),
        ncol=max(1, len(labels)),
    )
    figure.suptitle(
        "Uncertainty versus performance — descriptive, not calibrated confidence",
        fontsize=15,
        y=0.985,
    )
    figure.subplots_adjust(top=0.875, hspace=0.24, wspace=0.22)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(target, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return target
