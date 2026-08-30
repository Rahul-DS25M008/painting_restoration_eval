"""Spatial diffusion-uncertainty maps and normalized explanation assets."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib.patches import Rectangle
from PIL import Image

from .diffusion_uncertainty import (
    build_uncertainty_population,
    build_uncertainty_regions,
    load_mask_array,
    load_rgb_array,
)
from .schemas import (
    SPATIAL_EXPLANATION_MAP_IMAGE_COLUMNS,
    SPATIAL_EXPLANATION_MAP_IMAGE_SCHEMA,
    SPATIAL_EXPLANATIONS_COLUMNS,
    SPATIAL_EXPLANATIONS_SCHEMA,
    validate_dataframe,
)


SPATIAL_EXPLANATIONS_MODULE_NAME = "restoration_eval.spatial_explanations"
SPATIAL_EXPLANATIONS_MODULE_VERSION = "1.0.1"
SPATIAL_EXPLANATIONS_METRIC_VERSION = "spatial_explanations.v1"
SPATIAL_EXPLANATION_MAP_VERSION = "spatial_explanation_map_images.v1"
SPATIAL_EXPLANATION_RENDERER_VERSION = "spatial_explanation_renderer.v1.1"
SPATIAL_EXPLANATION_EVIDENCE_ROLE = "spatial_diagnostic_proxy"


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    if "spatial_explanations" in config:
        return config["spatial_explanations"]
    return config


def load_spatial_explanations_config(path: str | Path) -> dict[str, Any]:
    """Load and validate the Notebook 19 scientific configuration."""

    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Spatial-explanations configuration must be a mapping")
    if config.get("config_schema_version") != "spatial_explanations_config.v1":
        raise ValueError("Unsupported spatial-explanations config schema")
    settings = _settings(config)
    required = {
        "notebook_id", "notebook_stem", "metric_version",
        "map_manifest_version", "renderer_version", "inputs", "output",
        "population", "map_definition", "regions", "normalization",
        "overlays", "integration", "representative_panels", "execution",
        "expected_counts", "evidence_policy", "known_limitations",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"Spatial-explanations config is missing keys: {missing}")
    expected = settings["expected_counts"]
    if int(expected["uncertainty_groups"]) * int(expected["seeds_per_group"]) != int(
        expected["candidates"]
    ):
        raise ValueError("Candidate arithmetic does not match groups x seeds")
    if int(expected["uncertainty_groups"]) * len(settings["regions"]["region_order"]) != int(
        expected["spatial_explanation_rows"]
    ):
        raise ValueError("Spatial-explanation row arithmetic is inconsistent")
    if int(expected["generic_groups"]) + int(expected["scratch_aware_groups"]) != int(
        expected["uncertainty_groups"]
    ):
        raise ValueError("Prompt-arm counts do not match uncertainty groups")
    if settings["metric_version"] != SPATIAL_EXPLANATIONS_METRIC_VERSION:
        raise ValueError("Metric version does not match the helper")
    if settings["map_manifest_version"] != SPATIAL_EXPLANATION_MAP_VERSION:
        raise ValueError("Map-manifest version does not match the helper")
    if settings["renderer_version"] != SPATIAL_EXPLANATION_RENDERER_VERSION:
        raise ValueError("Renderer version does not match the helper")
    return config


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


def make_spatial_explanation_id(uncertainty_group_id: str, region_id: str) -> str:
    return _compact_hash(
        "sx_",
        (uncertainty_group_id, region_id, SPATIAL_EXPLANATIONS_METRIC_VERSION),
    )


def make_map_asset_id(
    uncertainty_group_id: str,
    map_type: str,
    *,
    candidate_id: str = "",
    selection_role: str = "",
) -> str:
    return _compact_hash(
        "sxa_",
        (
            uncertainty_group_id,
            candidate_id,
            map_type,
            selection_role,
            SPATIAL_EXPLANATION_RENDERER_VERSION,
        ),
    )


def _diffusion_compatible_config(config: Mapping[str, Any]) -> dict[str, Any]:
    settings = _settings(config)
    return {
        "diffusion_uncertainty": {
            "population": settings["population"],
            "regions": {
                "mask_bbox_margin_pixels": settings["regions"]["mask_bbox_margin_pixels"],
                "boundary_width_pixels": settings["regions"]["boundary_width_pixels"],
                "pixel_regions": list(settings["regions"]["region_order"]),
            },
            "expected_counts": {
                key: settings["expected_counts"][key]
                for key in ("uncertainty_groups", "unique_cases", "candidates")
            },
        }
    }


def build_spatial_explanation_population(
    worklist: pd.DataFrame,
    artworks: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Reuse Notebook 18's exact prompt-specific repeated-seed population."""

    population = build_uncertainty_population(
        worklist,
        artworks,
        config=_diffusion_compatible_config(config),
    )
    settings = _settings(config)
    expected = settings["expected_counts"]
    required_prompt_counts = {
        settings["population"]["generic_prompt_variant_id"]: int(
            expected["generic_groups"]
        ),
        settings["population"]["scratch_aware_prompt_variant_id"]: int(
            expected["scratch_aware_groups"]
        ),
    }
    observed_counts = population.groupby("prompt_variant_id")[
        "uncertainty_group_id"
    ].nunique().to_dict()
    observed_prompt_counts = {
        prompt_variant_id: int(observed_counts.get(prompt_variant_id, 0))
        for prompt_variant_id in required_prompt_counts
    }
    if observed_prompt_counts != required_prompt_counts:
        raise ValueError(
            "Prompt-specific spatial population differs from the contract: "
            f"{observed_prompt_counts}"
        )
    return population


def select_representative_candidates(
    population: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select one fixed-seed candidate per uncertainty group."""

    representative_seed = int(_settings(config)["population"]["representative_seed"])
    selected = population.loc[
        pd.to_numeric(population["seed"], errors="raise").astype(int).eq(
            representative_seed
        )
    ].copy()
    if selected["uncertainty_group_id"].duplicated().any():
        raise ValueError("Representative selection produced duplicate groups")
    expected = int(_settings(config)["expected_counts"]["representative_candidates"])
    if len(selected) != expected:
        raise ValueError(
            f"Expected {expected} representative candidates, observed {len(selected)}"
        )
    return selected.sort_values(
        ["case_id", "prompt_variant_id", "uncertainty_group_id"], kind="stable"
    ).reset_index(drop=True)


def compute_group_uncertainty_map(
    group: pd.DataFrame,
    *,
    project_root: str | Path,
    config: Mapping[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    """Compute one float32 per-pixel seed-variability map and its regions."""

    settings = _settings(config)
    expected_seeds = tuple(int(value) for value in settings["population"]["expected_seeds"])
    ordered = group.sort_values(["seed", "candidate_id"], kind="stable")
    seeds = tuple(pd.to_numeric(ordered["seed"], errors="raise").astype(int))
    if seeds != tuple(sorted(expected_seeds)):
        raise ValueError(f"Group does not contain exact seeds {expected_seeds}: {seeds}")
    arrays = [load_rgb_array(path, project_root) for path in ordered["restored_path"]]
    shapes = {array.shape for array in arrays}
    if len(shapes) != 1:
        raise ValueError(f"Seed candidate shapes disagree: {sorted(shapes)}")
    stack = np.stack(arrays, axis=0).astype(np.float32)
    uncertainty_map = stack.std(axis=0, ddof=0).mean(axis=2).astype(np.float32)
    raw_mask = load_mask_array(ordered.iloc[0]["mask_or_effect_path"], project_root)
    if raw_mask.shape != uncertainty_map.shape:
        raise ValueError("Uncertainty map and mask geometry disagree")
    regions = build_uncertainty_regions(
        ordered.iloc[0],
        raw_mask,
        config=_diffusion_compatible_config(config),
    )
    return uncertainty_map, regions


def _group_metadata(group: pd.DataFrame) -> dict[str, Any]:
    ordered = group.sort_values(["seed", "candidate_id"], kind="stable")
    first = ordered.iloc[0]
    representative = ordered.iloc[0]
    return {
        "uncertainty_group_id": str(first["uncertainty_group_id"]),
        "case_id": str(first["case_id"]),
        "model_id": str(first["model_id"]),
        "painting_id": str(first["painting_id"]),
        "category": str(first["category"]),
        "style_or_period": str(first["style_or_period"]),
        "dataset_id": str(first["dataset_id"]),
        "dataset_scope": str(first["dataset_scope"]),
        "experiment_id": str(first["experiment_id"]),
        "damage_or_degradation_type": str(first["damage_or_degradation_type"]),
        "case_label": str(first["case_label"]),
        "target_damage_fraction": first["target_damage_fraction"],
        "realized_damage_fraction": first["realized_damage_fraction"],
        "configuration_id": str(first["configuration_id"]),
        "prompt_policy_id": str(first["prompt_policy_id"]),
        "prompt_variant_id": str(first["prompt_variant_id"]),
        "execution_role": str(first["execution_role"]),
        "seeds": "|".join(str(int(value)) for value in ordered["seed"]),
        "seed_count": int(len(ordered)),
        "expected_seed_count": int(first["expected_seed_count"]),
        "seed_coverage_status": str(first["seed_coverage_status"]),
        "representative_candidate_id": str(representative["candidate_id"]),
        "representative_seed": int(representative["seed"]),
    }


def summarize_group_uncertainty_map(
    group: pd.DataFrame,
    uncertainty_map: np.ndarray,
    regions: Mapping[str, Any],
    *,
    config: Mapping[str, Any],
    normalization_vmax: float = np.nan,
) -> pd.DataFrame:
    """Build six normalized spatial-explanation records for one group."""

    settings = _settings(config)
    metadata = _group_metadata(group)
    group_id = metadata["uncertainty_group_id"]
    model_id = metadata["model_id"]
    output = settings["output"]
    image_path = Path(output["uncertainty_images_root"]) / f"{group_id}.png"
    overlay_path = Path(output["overlay_images_root"]) / f"{group_id}.png"
    records: list[dict[str, Any]] = []
    for region_id in settings["regions"]["region_order"]:
        region = regions[region_id]
        values = np.asarray(uncertainty_map[region.mask], dtype=np.float64)
        if values.size == 0 or not np.isfinite(values).all():
            raise ValueError(f"Region {region_id} has no finite uncertainty values")
        record = {
            **metadata,
            "spatial_explanation_id": make_spatial_explanation_id(group_id, region_id),
            "region_id": region_id,
            "region_pixel_count": int(values.size),
            "map_metric_name": settings["map_definition"]["metric_name"],
            "mean_value": float(values.mean()),
            "median_value": float(np.median(values)),
            "p95_value": float(np.percentile(values, 95)),
            "max_value": float(values.max()),
            "nonzero_fraction": float(np.mean(values > 0.0)),
            "value_unit": settings["map_definition"]["output_value_unit"],
            "normalization_policy_id": settings["normalization"]["policy_id"],
            "normalization_vmin": float(settings["normalization"]["vmin"]),
            "normalization_vmax": float(normalization_vmax),
            "normalization_scope": settings["normalization"]["scale_population"],
            "raw_map_key": group_id,
            "uncertainty_image_path": (Path(output["root"]) / image_path).as_posix(),
            "overlay_image_path": (Path(output["root"]) / overlay_path).as_posix(),
            "source_uncertainty_metric_version": "empirical_seed_uncertainty.v1",
            "region_policy_version": settings["regions"]["policy_version"],
            "evidence_role": settings["evidence_policy"]["evidence_role"],
            "is_calibrated_confidence": False,
            "is_final_trustworthiness_flag": False,
            "status": "ok",
            "issue": "",
        }
        records.append({column: record.get(column, "") for column in SPATIAL_EXPLANATIONS_COLUMNS})
    return pd.DataFrame(records, columns=SPATIAL_EXPLANATIONS_COLUMNS)


def attach_normalization_vmax(frame: pd.DataFrame, vmax: float) -> pd.DataFrame:
    result = frame.copy()
    result["normalization_vmax"] = float(vmax)
    return result


def write_group_work_map(
    path: str | Path,
    uncertainty_group_id: str,
    seeds: Sequence[int],
    uncertainty_map: np.ndarray,
    *,
    attempts: int = 8,
    retry_delay_seconds: float = 0.25,
) -> Path:
    """Atomically persist one resumable group map."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f"{destination.name}.{uuid.uuid4().hex}.tmp"
    )
    with temporary.open("wb") as handle:
        np.savez_compressed(
            handle,
            uncertainty_group_id=np.asarray(str(uncertainty_group_id)),
            seeds=np.asarray(tuple(int(value) for value in seeds), dtype=np.int32),
            uncertainty_map=np.asarray(uncertainty_map, dtype=np.float32),
            metric_version=np.asarray(SPATIAL_EXPLANATIONS_METRIC_VERSION),
        )
    last_error: PermissionError | None = None
    for attempt in range(1, int(attempts) + 1):
        try:
            os.replace(temporary, destination)
            return destination
        except PermissionError as error:
            last_error = error
            if attempt < attempts:
                time.sleep(float(retry_delay_seconds) * attempt)
    if temporary.exists():
        temporary.unlink(missing_ok=True)
    raise PermissionError(f"Could not replace group work map: {last_error}")


def load_group_work_map(
    path: str | Path,
    *,
    expected_group_id: str | None = None,
    expected_seeds: Sequence[int] | None = None,
) -> np.ndarray:
    with np.load(Path(path), allow_pickle=False) as archive:
        group_id = str(archive["uncertainty_group_id"].item())
        seeds = tuple(int(value) for value in archive["seeds"].tolist())
        metric_version = str(archive["metric_version"].item())
        array = np.asarray(archive["uncertainty_map"], dtype=np.float32)
    if expected_group_id is not None and group_id != str(expected_group_id):
        raise ValueError("Work-map uncertainty_group_id does not match")
    if expected_seeds is not None and seeds != tuple(int(value) for value in expected_seeds):
        raise ValueError("Work-map seed set does not match")
    if metric_version != SPATIAL_EXPLANATIONS_METRIC_VERSION:
        raise ValueError("Work-map metric version does not match")
    if array.ndim != 2 or not np.isfinite(array).all():
        raise ValueError("Work-map array must be finite and two-dimensional")
    return array


def compute_global_normalization(
    maps: Mapping[str, np.ndarray],
    content_masks: Mapping[str, np.ndarray],
    *,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Compute one deterministic robust scale shared by every map."""

    settings = _settings(config)["normalization"]
    maximum = int(settings["maximum_sampled_pixels_per_group"])
    base_seed = int(settings["deterministic_sampling_seed"])
    samples: list[np.ndarray] = []
    full_values: list[np.ndarray] = []
    for group_id in sorted(maps):
        values = np.asarray(maps[group_id], dtype=np.float32)[
            np.asarray(content_masks[group_id], dtype=bool)
        ]
        if values.size == 0 or not np.isfinite(values).all():
            raise ValueError(f"Normalization values are invalid for {group_id}")
        full_values.append(values)
        if values.size > maximum:
            group_seed = int(hashlib.sha256(group_id.encode("utf-8")).hexdigest()[:8], 16)
            rng = np.random.default_rng(base_seed ^ group_seed)
            values = values[rng.choice(values.size, size=maximum, replace=False)]
        samples.append(values)
    sampled = np.concatenate(samples)
    vmax = float(np.percentile(sampled, float(settings["percentile"])))
    if not np.isfinite(vmax) or vmax <= 0.0:
        raise ValueError("Global uncertainty vmax must be finite and positive")
    total_pixels = sum(values.size for values in full_values)
    clipped_pixels = sum(int(np.count_nonzero(values > vmax)) for values in full_values)
    return {
        "normalization_policy_id": settings["policy_id"],
        "vmin": float(settings["vmin"]),
        "vmax": vmax,
        "percentile": float(settings["percentile"]),
        "sampled_pixel_count": int(sampled.size),
        "evaluated_pixel_count": int(total_pixels),
        "clipped_pixel_count": int(clipped_pixels),
        "clipped_pixel_fraction": float(clipped_pixels / total_pixels),
        "scale_scope": settings["scale_population"],
    }


def write_numeric_map_archive(
    maps: Mapping[str, np.ndarray],
    path: str | Path,
    *,
    archive_dtype: str = "float16",
) -> Path:
    """Write all group maps into one compressed, atomic numeric archive."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f"{destination.name}.{uuid.uuid4().hex}.tmp")
    payload = {
        str(group_id): np.asarray(array, dtype=archive_dtype)
        for group_id, array in sorted(maps.items())
    }
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **payload)
    os.replace(temporary, destination)
    return destination


def load_numeric_map_archive(path: str | Path) -> dict[str, np.ndarray]:
    with np.load(Path(path), allow_pickle=False) as archive:
        result = {key: np.asarray(archive[key]) for key in archive.files}
    if not result:
        raise ValueError("Numeric uncertainty archive is empty")
    for key, array in result.items():
        if array.ndim != 2 or not np.isfinite(array).all():
            raise ValueError(f"Numeric map {key} is invalid")
    return result


def _masked_map(array: np.ndarray, mask: np.ndarray) -> np.ma.MaskedArray:
    return np.ma.array(array, mask=~np.asarray(mask, dtype=bool))


def render_uncertainty_panel(
    uncertainty_map: np.ndarray,
    regions: Mapping[str, Any],
    output_path: str | Path,
    *,
    title: str,
    vmin: float,
    vmax: float,
    cmap: str = "magma",
    dpi: int = 160,
) -> Path:
    """Render full, masked, crop, boundary, and outside-mask views."""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(1, 5, figsize=(18, 4.2), constrained_layout=True)
    views = [
        ("Full image", uncertainty_map, None),
        ("Masked region", _masked_map(uncertainty_map, regions["masked_region"].mask), None),
        ("Mask-box crop", uncertainty_map, regions["mask_bbox_crop"].bbox),
        ("Boundary ring", _masked_map(uncertainty_map, regions["boundary_ring"].mask), None),
        (
            "Outside-mask content",
            _masked_map(uncertainty_map, regions["outside_mask_content"].mask),
            None,
        ),
    ]
    image_artist = None
    for axis, (label, values, bbox) in zip(axes, views):
        if bbox is not None:
            x_min, y_min, x_max, y_max = bbox
            values = values[y_min:y_max, x_min:x_max]
        image_artist = axis.imshow(values, cmap=cmap, vmin=vmin, vmax=vmax)
        axis.set_title(label)
        axis.axis("off")
    figure.suptitle(title, fontsize=13)
    figure.colorbar(image_artist, ax=axes, fraction=0.018, pad=0.02, label="RGB seed variability")
    # Masked-array pixels are deliberately transparent so that excluded
    # regions cannot be mistaken for high uncertainty.  Supplying an opaque
    # figure face colour would flatten those pixels to white and violate the
    # configured transparent-outside-selected-region policy.
    figure.savefig(
        destination,
        dpi=dpi,
        facecolor="none",
        transparent=True,
    )
    plt.close(figure)
    return destination


def render_uncertainty_overlay(
    base_rgb: np.ndarray,
    uncertainty_map: np.ndarray,
    regions: Mapping[str, Any],
    output_path: str | Path,
    *,
    title: str,
    vmin: float,
    vmax: float,
    cmap: str = "magma",
    alpha_max: float = 0.72,
    dpi: int = 160,
) -> Path:
    """Render the representative restoration with geometry and heatmap overlay."""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    base = np.asarray(base_rgb)
    if base.dtype != np.uint8:
        base = np.clip(base * (255.0 if base.max() <= 1.0 else 1.0), 0, 255).astype(np.uint8)
    figure, axes = plt.subplots(1, 2, figsize=(9.5, 4.8), constrained_layout=True)
    axes[0].imshow(base)
    axes[0].imshow(
        _masked_map(uncertainty_map, regions["masked_region"].mask),
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        alpha=alpha_max,
    )
    axes[0].set_title("Masked uncertainty overlay")
    axes[1].imshow(base)
    boundary = np.ma.array(
        np.ones_like(uncertainty_map), mask=~regions["boundary_ring"].mask
    )
    axes[1].imshow(boundary, cmap="autumn", vmin=0, vmax=1, alpha=0.75)
    for region_id, colour, label in (
        ("content_region", "cyan", "content box"),
        ("mask_bbox_crop", "magenta", "mask box"),
    ):
        bbox = regions[region_id].bbox
        if bbox is not None:
            x_min, y_min, x_max, y_max = bbox
            axes[1].add_patch(
                Rectangle(
                    (x_min, y_min), x_max - x_min, y_max - y_min,
                    fill=False, edgecolor=colour, linewidth=1.5, label=label,
                )
            )
    axes[1].legend(loc="lower right", fontsize=8)
    axes[1].set_title("Canonical geometry overlays")
    for axis in axes:
        axis.axis("off")
    figure.suptitle(title, fontsize=13)
    figure.savefig(destination, dpi=dpi, facecolor="white")
    plt.close(figure)
    return destination


def _asset_base(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "uncertainty_group_id": str(metadata.get("uncertainty_group_id", "")),
        "case_id": str(metadata.get("case_id", "")),
        "candidate_id": str(metadata.get("candidate_id", "")),
        "model_id": str(metadata.get("model_id", "")),
        "painting_id": str(metadata.get("painting_id", "")),
        "prompt_variant_id": str(metadata.get("prompt_variant_id", "")),
    }


def build_map_asset_record(
    metadata: Mapping[str, Any],
    *,
    asset_kind: str,
    ownership: str,
    map_type: str,
    relative_path: str,
    status: str,
    region_scope: str = "full_image",
    selection_role: str = "",
    archive_key: str = "",
    source_artifact_key: str = "",
    source_map_image_id: str = "",
    source_notebook: str = "",
    sha256: str = "",
    size_bytes: int | float | str = np.nan,
    width: int | float | str = np.nan,
    height: int | float | str = np.nan,
    image_mode: str = "",
    format: str = "PNG",
    cmap: str = "",
    vmin: float | str = np.nan,
    vmax: float | str = np.nan,
    center: float | str = np.nan,
    scale_scope: str = "",
    normalization_policy_id: str = "",
    quantization_policy: str = "",
    no_data_policy: str = "",
    renderer_version: str = SPATIAL_EXPLANATION_RENDERER_VERSION,
    issue: str = "",
) -> dict[str, Any]:
    base = _asset_base(metadata)
    record = {
        **base,
        "map_asset_id": make_map_asset_id(
            base["uncertainty_group_id"], map_type,
            candidate_id=base["candidate_id"], selection_role=selection_role,
        ),
        "asset_kind": asset_kind,
        "ownership": ownership,
        "map_type": map_type,
        "region_scope": region_scope,
        "selection_role": selection_role,
        "relative_path": relative_path,
        "archive_key": archive_key,
        "source_artifact_key": source_artifact_key,
        "source_map_image_id": source_map_image_id,
        "source_notebook": source_notebook,
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
        "renderer_version": renderer_version,
        "status": status,
        "issue": issue,
    }
    return {column: record.get(column, "") for column in SPATIAL_EXPLANATION_MAP_IMAGE_COLUMNS}


def build_component_integration_plan(
    representatives: pd.DataFrame,
    spatial_map_manifest: pd.DataFrame,
    local_map_manifest: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build upstream component links and the explicit missing-local worklist."""

    settings = _settings(config)
    required_representative_columns = {
        "uncertainty_group_id", "case_id", "candidate_id", "model_id",
        "painting_id", "prompt_variant_id",
    }
    missing = sorted(required_representative_columns - set(representatives.columns))
    if missing:
        raise ValueError(f"Representatives are missing columns: {missing}")
    source_required = {
        "map_image_id", "asset_kind", "candidate_id", "map_type",
        "relative_path", "sha256", "size_bytes", "width", "height",
        "image_mode", "format", "cmap", "vmin", "vmax", "center",
        "scale_scope", "quantization_policy", "no_data_policy",
        "renderer_version", "status",
    }
    for label, frame in (
        ("spatial_map_manifest", spatial_map_manifest),
        ("local_map_manifest", local_map_manifest),
    ):
        source_missing = sorted(source_required - set(frame.columns))
        if source_missing:
            raise ValueError(f"{label} is missing columns: {source_missing}")

    spatial_lookup = {
        (str(row.candidate_id), str(row.map_type)): row
        for row in spatial_map_manifest.loc[
            spatial_map_manifest["asset_kind"].astype(str).eq("candidate_map")
            & spatial_map_manifest["status"].astype(str).eq("passed")
        ].itertuples(index=False)
    }
    local_lookup = {
        (str(row.candidate_id), str(row.map_type)): row
        for row in local_map_manifest.loc[
            local_map_manifest["asset_kind"].astype(str).eq("candidate_map")
            & local_map_manifest["status"].astype(str).eq("passed")
        ].itertuples(index=False)
    }
    linked_records: list[dict[str, Any]] = []
    missing_local_records: list[dict[str, Any]] = []

    def source_record(
        representative: Mapping[str, Any],
        source: Any,
        *,
        source_artifact_key: str,
        source_notebook: str,
    ) -> dict[str, Any]:
        return build_map_asset_record(
            representative,
            asset_kind="component_map",
            ownership="upstream_link",
            map_type=str(source.map_type),
            relative_path=str(source.relative_path),
            status="passed",
            source_artifact_key=source_artifact_key,
            source_map_image_id=str(source.map_image_id),
            source_notebook=source_notebook,
            sha256=str(source.sha256),
            size_bytes=source.size_bytes,
            width=source.width,
            height=source.height,
            image_mode=str(source.image_mode),
            format=str(source.format),
            cmap=str(source.cmap),
            vmin=source.vmin,
            vmax=source.vmax,
            center=source.center,
            scale_scope=str(source.scale_scope),
            normalization_policy_id="upstream_declared_scale",
            quantization_policy=str(source.quantization_policy),
            no_data_policy=str(source.no_data_policy),
            renderer_version=str(source.renderer_version),
        )

    for representative in representatives.sort_values(
        ["case_id", "prompt_variant_id", "uncertainty_group_id"], kind="stable"
    ).to_dict("records"):
        candidate_id = str(representative["candidate_id"])
        for map_type in settings["integration"]["error_map_types"]:
            source = spatial_lookup.get((candidate_id, str(map_type)))
            if source is None:
                raise ValueError(
                    f"Notebook 16 map {map_type} is missing for {candidate_id}"
                )
            linked_records.append(source_record(
                representative,
                source,
                source_artifact_key="spatial_diagnostics.candidate_maps",
                source_notebook="16_difference_maps_and_spatial_diagnostics",
            ))
        for map_type in settings["integration"]["local_map_types"]:
            source = local_lookup.get((candidate_id, str(map_type)))
            if source is not None:
                linked_records.append(source_record(
                    representative,
                    source,
                    source_artifact_key="local_consistency.candidate_maps",
                    source_notebook="17_local_consistency_metrics",
                ))
                continue
            group_id = str(representative["uncertainty_group_id"])
            relative_path = (
                Path(settings["output"]["root"])
                / settings["output"]["integrated_local_images_root"]
                / group_id
                / f"{map_type}.png"
            ).as_posix()
            missing_local_records.append({
                **_asset_base(representative),
                "map_type": str(map_type),
                "relative_path": relative_path,
                "source_notebook": "17_local_consistency_metrics",
                "source_artifact_key": "local_consistency.metrics",
                "render_policy": settings["integration"][
                    "missing_scratch_aware_local_policy"
                ],
                "status": "planned",
                "issue": "validated upstream image absent under primary-only map policy",
            })
    links = pd.DataFrame(linked_records, columns=SPATIAL_EXPLANATION_MAP_IMAGE_COLUMNS)
    missing_local = pd.DataFrame(missing_local_records)
    expected = settings["expected_counts"]
    expected_links = int(expected["upstream_error_component_links"]) + int(
        expected["upstream_generic_local_component_links"]
    )
    if len(links) != expected_links:
        raise ValueError(f"Expected {expected_links} upstream links, observed {len(links)}")
    if len(missing_local) != int(expected["owned_scratch_aware_local_component_maps"]):
        raise ValueError(
            "Missing-local worklist does not match the scratch-aware map contract"
        )
    schema = validate_dataframe(
        links, SPATIAL_EXPLANATION_MAP_IMAGE_SCHEMA, allow_extra_columns=False
    )
    if not schema.passed:
        raise ValueError(f"Upstream component links fail schema: {schema.to_dict()}")
    return links, missing_local


def render_selected_explanation_panel(
    panels: Sequence[tuple[str, str | Path | np.ndarray]],
    output_path: str | Path,
    *,
    title: str,
    columns: int = 4,
    dpi: int = 160,
) -> Path:
    """Render one flexible selected-case panel from validated component assets."""

    if not panels:
        raise ValueError("Selected explanation panel requires at least one component")
    if columns < 1:
        raise ValueError("columns must be positive")
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = int(np.ceil(len(panels) / columns))
    figure, axes = plt.subplots(
        rows,
        columns,
        figsize=(4.0 * columns, 3.5 * rows),
        constrained_layout=True,
        squeeze=False,
    )
    flattened = axes.ravel()
    for axis, (label, source) in zip(flattened, panels):
        if isinstance(source, (str, Path)):
            with Image.open(source) as image:
                array = np.asarray(image.convert("RGBA"))
        else:
            array = np.asarray(source)
        if array.ndim not in (2, 3):
            raise ValueError(f"Panel component {label} has invalid shape {array.shape}")
        axis.imshow(array, cmap="gray" if array.ndim == 2 else None)
        axis.set_title(str(label), fontsize=10)
        axis.axis("off")
    for axis in flattened[len(panels):]:
        axis.axis("off")
    figure.suptitle(title, fontsize=14)
    figure.savefig(destination, dpi=dpi, facecolor="white")
    plt.close(figure)
    return destination


def select_representative_explanations(
    spatial_explanations: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select 15 category-balanced panels through three auditable rules."""

    settings = _settings(config)
    categories = tuple(settings["representative_panels"]["categories"])
    generic_id = settings["population"]["generic_prompt_variant_id"]
    aware_id = settings["population"]["scratch_aware_prompt_variant_id"]
    index_columns = [
        "uncertainty_group_id", "case_id", "painting_id", "category",
        "case_label", "prompt_variant_id", "representative_candidate_id",
    ]
    mean_table = spatial_explanations.pivot_table(
        index=index_columns,
        columns="region_id",
        values="mean_value",
        aggfunc="first",
    ).reset_index()
    generic = mean_table.loc[mean_table["prompt_variant_id"].eq(generic_id)].copy()
    records: list[dict[str, Any]] = []
    for category in categories:
        subset = generic.loc[generic["category"].eq(category)].copy()
        if subset.empty:
            raise ValueError(f"No generic groups exist for category {category}")
        median_value = float(subset["masked_region"].median())
        subset["selection_value"] = (subset["masked_region"] - median_value).abs()
        selected = subset.sort_values(
            ["selection_value", "case_id", "uncertainty_group_id"], kind="stable"
        ).iloc[0]
        records.append({
            **selected.to_dict(),
            "selection_role": "category_median_generic_masked_uncertainty",
            "selection_metric": "absolute_distance_to_category_median_masked_uncertainty",
        })
        subset = subset.copy()
        subset["selection_value"] = subset["boundary_ring"] / np.maximum(
            subset["masked_region"], np.finfo(float).eps
        )
        selected = subset.sort_values(
            ["selection_value", "case_id", "uncertainty_group_id"],
            ascending=[False, True, True], kind="stable",
        ).iloc[0]
        records.append({
            **selected.to_dict(),
            "selection_role": "category_max_generic_boundary_concentration",
            "selection_metric": "boundary_mean_divided_by_masked_mean",
        })
    scratch = mean_table.loc[
        mean_table["case_label"].eq("scratch_thin")
        & mean_table["prompt_variant_id"].isin([generic_id, aware_id])
    ].copy()
    paired = scratch.pivot_table(
        index=["case_id", "painting_id", "category", "case_label"],
        columns="prompt_variant_id",
        values="masked_region",
        aggfunc="first",
    ).reset_index()
    if generic_id not in paired or aware_id not in paired:
        raise ValueError("Scratch prompt-pair table is incomplete")
    paired["selection_value"] = (paired[aware_id] - paired[generic_id]).abs()
    for category in categories:
        subset = paired.loc[paired["category"].eq(category)].copy()
        if subset.empty:
            raise ValueError(f"No scratch prompt pairs exist for category {category}")
        selected = subset.sort_values(
            ["selection_value", "case_id"], ascending=[False, True], kind="stable"
        ).iloc[0]
        aware_group = scratch.loc[
            scratch["case_id"].eq(selected["case_id"])
            & scratch["prompt_variant_id"].eq(aware_id)
        ].sort_values("uncertainty_group_id", kind="stable").iloc[0]
        records.append({
            **aware_group.to_dict(),
            "selection_role": "category_max_absolute_scratch_prompt_difference",
            "selection_metric": "absolute_aware_minus_generic_masked_uncertainty",
            "selection_value": float(selected["selection_value"]),
        })
    result = pd.DataFrame(records)
    role_order = {role: index for index, role in enumerate(
        settings["representative_panels"]["rules"]
    )}
    result["_role_order"] = result["selection_role"].map(role_order)
    result["_category_order"] = result["category"].map(
        {category: index for index, category in enumerate(categories)}
    )
    result = result.sort_values(
        ["_role_order", "_category_order", "case_id", "uncertainty_group_id"],
        kind="stable",
    ).drop(columns=["_role_order", "_category_order"]).reset_index(drop=True)
    expected = int(settings["representative_panels"]["panel_count"])
    if len(result) != expected:
        raise ValueError(f"Expected {expected} selected panels, observed {len(result)}")
    if result.duplicated(["selection_role", "category"]).any():
        raise ValueError("Representative selections repeat a role/category stratum")
    return result


def validate_spatial_explanations(
    dataframe: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    settings = _settings(config)
    schema = validate_dataframe(
        dataframe, SPATIAL_EXPLANATIONS_SCHEMA, allow_extra_columns=False
    )
    numeric_columns = [
        "mean_value", "median_value", "p95_value", "max_value",
        "nonzero_fraction", "normalization_vmin", "normalization_vmax",
    ]
    numeric = dataframe[numeric_columns].apply(pd.to_numeric, errors="coerce")
    expected_regions = set(settings["regions"]["region_order"])
    region_sets = dataframe.groupby("uncertainty_group_id")["region_id"].agg(set)
    return {
        "passed": bool(
            schema.passed
            and len(dataframe) == int(settings["expected_counts"]["spatial_explanation_rows"])
            and dataframe["uncertainty_group_id"].nunique()
            == int(settings["expected_counts"]["uncertainty_groups"])
            and region_sets.map(lambda values: values == expected_regions).all()
            and np.isfinite(numeric.to_numpy(dtype=float)).all()
            and dataframe["status"].eq("ok").all()
        ),
        "schema": schema.to_dict(),
        "row_count": int(len(dataframe)),
        "group_count": int(dataframe["uncertainty_group_id"].nunique()),
        "complete_region_groups": int(
            region_sets.map(lambda values: values == expected_regions).sum()
        ),
        "numeric_values_finite": bool(np.isfinite(numeric.to_numpy(dtype=float)).all()),
    }


def validate_map_manifest(
    dataframe: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    settings = _settings(config)
    schema = validate_dataframe(
        dataframe, SPATIAL_EXPLANATION_MAP_IMAGE_SCHEMA, allow_extra_columns=False
    )
    passed_rows = dataframe["status"].eq("passed")
    passed_paths = dataframe.loc[passed_rows, "relative_path"].astype(str).str.strip()
    return {
        "passed": bool(
            schema.passed
            and len(dataframe) == int(settings["expected_counts"]["map_manifest_rows"])
            and passed_paths.ne("").all()
            and dataframe["map_asset_id"].is_unique
        ),
        "schema": schema.to_dict(),
        "row_count": int(len(dataframe)),
        "status_counts": dataframe["status"].value_counts(dropna=False).to_dict(),
        "ownership_counts": dataframe["ownership"].value_counts(dropna=False).to_dict(),
        "blank_passed_paths": int(passed_paths.eq("").sum()),
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
    "SPATIAL_EXPLANATIONS_METRIC_VERSION",
    "SPATIAL_EXPLANATIONS_MODULE_NAME",
    "SPATIAL_EXPLANATIONS_MODULE_VERSION",
    "SPATIAL_EXPLANATION_EVIDENCE_ROLE",
    "SPATIAL_EXPLANATION_MAP_VERSION",
    "SPATIAL_EXPLANATION_RENDERER_VERSION",
    "attach_normalization_vmax",
    "build_component_integration_plan",
    "build_map_asset_record",
    "build_spatial_explanation_population",
    "compute_global_normalization",
    "compute_group_uncertainty_map",
    "load_group_work_map",
    "load_numeric_map_archive",
    "load_spatial_explanations_config",
    "make_map_asset_id",
    "make_spatial_explanation_id",
    "project_relative_path",
    "render_uncertainty_overlay",
    "render_uncertainty_panel",
    "render_selected_explanation_panel",
    "resolve_path",
    "select_representative_candidates",
    "select_representative_explanations",
    "sha256_path",
    "summarize_group_uncertainty_map",
    "validate_map_manifest",
    "validate_spatial_explanations",
    "write_dataframe_atomic",
    "write_group_work_map",
    "write_numeric_map_archive",
]
