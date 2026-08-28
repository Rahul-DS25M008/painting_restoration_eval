"""Canonical spatial diagnostics and display-map utilities.

The module is model-agnostic and uses :mod:`restoration_eval.regions` as the
only source of spatial-region geometry. Floating-point arrays and CSV summary
statistics remain the scientific evidence. Indexed PNG files are documented,
standardized display assets for later XAI, report, and case-study notebooks.
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib import colormaps
from matplotlib.colors import Normalize, TwoSlopeNorm
from PIL import Image, ImageDraw

from .regions import Region, build_standard_regions, effect_support_region
from .schemas import (
    SPATIAL_DIAGNOSTICS_COLUMNS,
    SPATIAL_DIAGNOSTICS_SCHEMA,
    SPATIAL_MAP_IMAGE_MANIFEST_COLUMNS,
    SPATIAL_MAP_IMAGE_MANIFEST_SCHEMA,
    validate_dataframe,
)


ERROR_MAP_MODULE_NAME = "restoration_eval.error_maps"
ERROR_MAP_VERSION = "4.0.1"
SPATIAL_DIAGNOSTIC_VERSION = "spatial_diagnostics.v1"
SPATIAL_MAP_MANIFEST_VERSION = "spatial_map_images.v1"
SPATIAL_MAP_RENDERER_VERSION = "spatial_map_renderer.v1"

NUMERIC_MAP_TYPES = (
    "damaged_absolute_error",
    "restored_absolute_error",
    "signed_improvement",
    "masked_signed_improvement",
)
CANDIDATE_MAP_TYPES = NUMERIC_MAP_TYPES + ("spatial_overlay",)
SPATIAL_REGION_ORDER = (
    "full_image",
    "content_region",
    "masked_region",
    "mask_bbox_crop",
    "inner_boundary_band",
    "outer_boundary_band",
    "boundary_ring",
    "outside_mask_content",
    "outside_boundary_ring",
    "degradation_support",
)


@dataclass(frozen=True)
class SpatialCandidateResult:
    """Computed arrays, regions, and normalized summary rows for one candidate."""

    maps: Mapping[str, np.ndarray]
    regions: Mapping[str, Region]
    diagnostics: pd.DataFrame


@dataclass(frozen=True)
class SpatialRunResult:
    """Checkpoint-aware full execution result."""

    diagnostics: pd.DataFrame
    map_images: pd.DataFrame
    completed_candidates: int
    reused_candidates: int


def load_spatial_diagnostics_config(path: str | Path) -> dict[str, Any]:
    """Load and minimally validate the Notebook 16 configuration."""

    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Spatial diagnostics config not found: {config_path}")
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "spatial_diagnostics" not in payload:
        raise ValueError("Config must contain a spatial_diagnostics mapping")
    config = payload["spatial_diagnostics"]
    for key in (
        "notebook_id", "notebook_stem", "diagnostic_version",
        "map_manifest_version", "map_renderer_version", "inputs", "output",
        "regions", "visualization", "execution", "evidence_policy",
        "expected_counts", "known_limitations",
    ):
        if key not in config:
            raise ValueError(f"Spatial diagnostics config is missing {key!r}")
    if tuple(config["regions"]["region_order"]) != SPATIAL_REGION_ORDER:
        raise ValueError("Configured spatial region order does not match the v1 contract")
    degradation_experiments = config["regions"].get(
        "degradation_support_experiment_ids"
    )
    if degradation_experiments != ["synthetic_degradation"]:
        raise ValueError(
            "Degradation support must be restricted to synthetic_degradation"
        )
    if tuple(config["visualization"]["map_types"]) != CANDIDATE_MAP_TYPES:
        raise ValueError("Configured candidate map types do not match the v1 contract")
    if config["diagnostic_version"] != SPATIAL_DIAGNOSTIC_VERSION:
        raise ValueError("Unsupported spatial diagnostic version")
    if config["map_manifest_version"] != SPATIAL_MAP_MANIFEST_VERSION:
        raise ValueError("Unsupported spatial map manifest version")
    if config["map_renderer_version"] != SPATIAL_MAP_RENDERER_VERSION:
        raise ValueError("Unsupported spatial map renderer version")
    return config


def resolve_path(path_value: str | Path, project_root: str | Path) -> Path:
    """Resolve one project-relative or absolute path."""

    path = Path(str(path_value).strip())
    return path if path.is_absolute() else Path(project_root) / path


def project_relative_path(path: str | Path, project_root: str | Path) -> str:
    """Return a POSIX repository-relative path."""

    resolved = Path(path).resolve()
    root = Path(project_root).resolve()
    return resolved.relative_to(root).as_posix()


def sha256_path(path: str | Path) -> str:
    """Hash one file using SHA-256."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def make_map_id(candidate_id: str) -> str:
    """Build a short deterministic path-safe identifier for one candidate."""

    value = str(candidate_id).strip()
    if not value:
        raise ValueError("candidate_id must be non-empty")
    return "spm_" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def make_spatial_diagnostic_id(candidate_id: str, region_id: str) -> str:
    """Build a deterministic primary key for one candidate-region row."""

    payload = f"{candidate_id}|{region_id}|{SPATIAL_DIAGNOSTIC_VERSION}"
    return "spd_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def make_map_image_id(map_id: str, map_type: str) -> str:
    """Build a stable image-manifest primary key."""

    payload = f"{map_id}|{map_type}|{SPATIAL_MAP_RENDERER_VERSION}"
    return "smi_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def _row_value(row: Mapping[str, Any] | pd.Series, key: str, default: Any = "") -> Any:
    return row.get(key, default)


def load_rgb_array(path: str | Path, project_root: str | Path) -> np.ndarray:
    """Load an RGB image as float32 values in [0, 255]."""

    resolved = resolve_path(path, project_root)
    if not resolved.is_file():
        raise FileNotFoundError(f"RGB image not found: {resolved}")
    with Image.open(resolved) as image:
        return np.asarray(image.convert("RGB"), dtype=np.float32)


def load_mask_array(path: str | Path, project_root: str | Path) -> np.ndarray:
    """Load the original grayscale mask/effect values without threshold loss."""

    resolved = resolve_path(path, project_root)
    if not resolved.is_file():
        raise FileNotFoundError(f"Mask/effect image not found: {resolved}")
    with Image.open(resolved) as image:
        return np.asarray(image.convert("L"), dtype=np.uint8)


def load_candidate_arrays(
    row: Mapping[str, Any] | pd.Series,
    *,
    project_root: str | Path,
) -> dict[str, np.ndarray]:
    """Load and validate clean, damaged, restored, and mask arrays."""

    arrays = {
        "clean": load_rgb_array(_row_value(row, "clean_image_path"), project_root),
        "damaged": load_rgb_array(_row_value(row, "input_image_path"), project_root),
        "restored": load_rgb_array(_row_value(row, "restored_path"), project_root),
        "mask_values": load_mask_array(
            _row_value(row, "mask_or_effect_path"), project_root
        ),
    }
    shape = arrays["clean"].shape
    if len(shape) != 3 or shape[2] != 3:
        raise ValueError(f"Clean image is not RGB: {shape}")
    for role in ("damaged", "restored"):
        if arrays[role].shape != shape:
            raise ValueError(
                f"{role} shape {arrays[role].shape} does not match clean {shape}"
            )
    if arrays["mask_values"].shape != shape[:2]:
        raise ValueError(
            "Mask/effect shape does not match image shape: "
            f"{arrays['mask_values'].shape} vs {shape[:2]}"
        )
    return arrays


def compute_case_maps(
    clean: np.ndarray,
    damaged: np.ndarray,
    restored: np.ndarray,
) -> dict[str, np.ndarray]:
    """Compute canonical full-resolution floating-point spatial maps."""

    clean_arr = np.asarray(clean, dtype=np.float32)
    damaged_arr = np.asarray(damaged, dtype=np.float32)
    restored_arr = np.asarray(restored, dtype=np.float32)
    if clean_arr.ndim != 3 or clean_arr.shape[2] != 3:
        raise ValueError("clean must be an H x W x 3 RGB array")
    if damaged_arr.shape != clean_arr.shape or restored_arr.shape != clean_arr.shape:
        raise ValueError("clean, damaged, and restored arrays must have identical shape")
    damaged_error = np.mean(np.abs(clean_arr - damaged_arr), axis=2, dtype=np.float32)
    restored_error = np.mean(np.abs(clean_arr - restored_arr), axis=2, dtype=np.float32)
    signed = damaged_error - restored_error
    restoration_change = np.mean(
        np.abs(restored_arr - damaged_arr), axis=2, dtype=np.float32
    )
    return {
        "damaged_absolute_error": damaged_error.astype(np.float32, copy=False),
        "restored_absolute_error": restored_error.astype(np.float32, copy=False),
        "signed_improvement": signed.astype(np.float32, copy=False),
        "restoration_change": restoration_change.astype(np.float32, copy=False),
    }


def build_candidate_regions(
    row: Mapping[str, Any] | pd.Series,
    mask_values: np.ndarray,
    *,
    config: Mapping[str, Any],
) -> dict[str, Region]:
    """Build the complete Notebook 16 region set through the canonical helper."""

    threshold = int(float(_row_value(row, "mask_threshold")))
    active_mask = np.asarray(mask_values) >= threshold
    content_bbox = tuple(
        int(float(_row_value(row, column)))
        for column in (
            "content_x_min", "content_y_min", "content_x_max", "content_y_max"
        )
    )
    policy = config["regions"]
    regions = build_standard_regions(
        active_mask,
        content_bbox=content_bbox,
        mask_bbox_margin=int(policy["mask_bbox_margin_pixels"]),
        boundary_width_pixels=int(policy["boundary_width_pixels"]),
        include_outside_boundary=True,
        outside_boundary_width_pixels=int(policy["outside_ring_outer_width_pixels"]),
    )
    experiment_id = str(_row_value(row, "experiment_id"))
    if experiment_id in set(policy["degradation_support_experiment_ids"]):
        regions["degradation_support"] = effect_support_region(
            mask_values,
            support_threshold=float(policy["effect_support_threshold"]),
        )
    ordered = {
        region_id: regions[region_id]
        for region_id in SPATIAL_REGION_ORDER
        if region_id in regions
    }
    expected_order = tuple(
        region_id
        for region_id in SPATIAL_REGION_ORDER
        if region_id != "degradation_support"
        or experiment_id in set(policy["degradation_support_experiment_ids"])
    )
    if tuple(ordered) != expected_order:
        raise ValueError(
            f"Canonical region order mismatch: {tuple(ordered)} vs {expected_order}"
        )
    return ordered


def _percentile(values: np.ndarray, percentile: float) -> float:
    return float(np.percentile(values, percentile))


def _diagnostic_record(
    row: Mapping[str, Any] | pd.Series,
    region: Region,
    maps: Mapping[str, np.ndarray],
    *,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    pixels = region.mask
    damaged = np.asarray(maps["damaged_absolute_error"])[pixels]
    restored = np.asarray(maps["restored_absolute_error"])[pixels]
    signed = np.asarray(maps["signed_improvement"])[pixels]
    changed = np.asarray(maps["restoration_change"])[pixels]
    tolerance = float(config["evidence_policy"]["improved_pixel_tolerance"])
    change_tolerance = float(
        config["evidence_policy"]["changed_pixel_channel_tolerance"]
    )
    return {
        "spatial_diagnostic_id": make_spatial_diagnostic_id(
            str(_row_value(row, "candidate_id")), region.region_id
        ),
        "case_id": str(_row_value(row, "case_id")),
        "candidate_id": str(_row_value(row, "candidate_id")),
        "model_id": str(_row_value(row, "model_id")),
        "painting_id": str(_row_value(row, "painting_id")),
        "dataset_id": str(_row_value(row, "dataset_id")),
        "dataset_scope": str(_row_value(row, "dataset_scope")),
        "experiment_id": str(_row_value(row, "experiment_id")),
        "damage_or_degradation_type": str(
            _row_value(row, "damage_or_degradation_type")
        ),
        "candidate_index": int(float(_row_value(row, "candidate_index", 0))),
        "seed": _row_value(row, "seed", np.nan),
        "prompt_policy_id": str(_row_value(row, "prompt_policy_id", "")),
        "prompt_variant_id": str(_row_value(row, "prompt_variant_id", "")),
        "execution_role": str(_row_value(row, "execution_role", "primary")),
        "is_zero_control": bool(_row_value(row, "is_zero_control", False)),
        "region_id": region.region_id,
        "region_type": region.region_type,
        "spatial_support": region.spatial_support,
        "region_pixel_count": int(region.pixel_count),
        "damaged_error_mean": float(damaged.mean(dtype=np.float64)),
        "damaged_error_median": float(np.median(damaged)),
        "damaged_error_p95": _percentile(damaged, 95.0),
        "restored_error_mean": float(restored.mean(dtype=np.float64)),
        "restored_error_median": float(np.median(restored)),
        "restored_error_p95": _percentile(restored, 95.0),
        "signed_improvement_mean": float(signed.mean(dtype=np.float64)),
        "signed_improvement_median": float(np.median(signed)),
        "signed_improvement_p05": _percentile(signed, 5.0),
        "signed_improvement_p95": _percentile(signed, 95.0),
        "improved_pixel_fraction": float(np.mean(signed > tolerance)),
        "worsened_pixel_fraction": float(np.mean(signed < -tolerance)),
        "unchanged_pixel_fraction": float(np.mean(np.abs(signed) <= tolerance)),
        "restoration_change_mean": float(changed.mean(dtype=np.float64)),
        "restoration_change_p95": _percentile(changed, 95.0),
        "restoration_change_max": float(changed.max()),
        "restoration_changed_pixel_fraction": float(
            np.mean(changed > change_tolerance)
        ),
        "evidence_role": "diagnostic_only",
        "is_final_trustworthiness_flag": False,
        "diagnostic_version": SPATIAL_DIAGNOSTIC_VERSION,
        "region_policy_version": str(config["regions"]["policy_version"]),
        "status": "ok",
        "issue": "",
    }


def compute_candidate_spatial_diagnostics(
    row: Mapping[str, Any] | pd.Series,
    *,
    project_root: str | Path,
    config: Mapping[str, Any],
) -> SpatialCandidateResult:
    """Compute all valid-region spatial evidence for one candidate."""

    arrays = load_candidate_arrays(row, project_root=project_root)
    maps = compute_case_maps(arrays["clean"], arrays["damaged"], arrays["restored"])
    regions = build_candidate_regions(row, arrays["mask_values"], config=config)
    records = [
        _diagnostic_record(row, region, maps, config=config)
        for region in regions.values()
        if region.validity_status == "valid"
    ]
    diagnostics = pd.DataFrame(records, columns=SPATIAL_DIAGNOSTICS_COLUMNS)
    schema_result = validate_dataframe(diagnostics, SPATIAL_DIAGNOSTICS_SCHEMA)
    if not schema_result.passed:
        raise ValueError(f"Candidate diagnostics violate schema: {schema_result.to_dict()}")
    return SpatialCandidateResult(maps=maps, regions=regions, diagnostics=diagnostics)


def _sample_values(
    values: np.ndarray,
    *,
    maximum: int,
    seed: int,
) -> np.ndarray:
    flat = np.asarray(values, dtype=np.float32).ravel()
    if flat.size <= maximum:
        return flat
    rng = np.random.default_rng(seed)
    indices = rng.choice(flat.size, size=maximum, replace=False)
    return flat[indices]


def compute_global_visualization_scales(
    worklist: pd.DataFrame,
    *,
    project_root: str | Path,
    config: Mapping[str, Any],
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, dict[str, Any]]:
    """Compute one globally comparable absolute and signed display scale."""

    if worklist.empty:
        raise ValueError("Cannot compute visualization scales from an empty worklist")
    visual = config["visualization"]
    maximum = int(visual["maximum_sampled_pixels_per_candidate"])
    base_seed = int(visual["deterministic_sampling_seed"])
    absolute_samples: list[np.ndarray] = []
    signed_samples: list[np.ndarray] = []
    total = len(worklist)
    for number, (_, row) in enumerate(worklist.iterrows(), start=1):
        result = compute_candidate_spatial_diagnostics(
            row, project_root=project_root, config=config
        )
        content = result.regions["content_region"].mask
        candidate_seed = int(
            hashlib.sha256(str(row["candidate_id"]).encode("utf-8")).hexdigest()[:8],
            16,
        ) ^ base_seed
        absolute_values = np.concatenate((
            result.maps["damaged_absolute_error"][content],
            result.maps["restored_absolute_error"][content],
        ))
        signed_values = np.abs(result.maps["signed_improvement"][content])
        absolute_samples.append(_sample_values(
            absolute_values, maximum=maximum, seed=candidate_seed
        ))
        signed_samples.append(_sample_values(
            signed_values, maximum=maximum, seed=candidate_seed + 1
        ))
        if progress_callback is not None:
            progress_callback(number, total)
    absolute_pool = np.concatenate(absolute_samples)
    signed_pool = np.concatenate(signed_samples)
    absolute_cfg = visual["absolute_error"]
    signed_cfg = visual["signed_improvement"]
    absolute_max = max(
        float(np.percentile(absolute_pool, float(absolute_cfg["percentile"]))),
        float(np.finfo(np.float32).eps),
    )
    signed_limit = max(
        float(np.percentile(
            signed_pool, float(signed_cfg["absolute_percentile"])
        )),
        float(np.finfo(np.float32).eps),
    )
    scope = str(visual["scale_population"])
    return {
        "absolute_error": {
            "cmap": str(absolute_cfg["cmap"]),
            "vmin": float(absolute_cfg["vmin"]),
            "vmax": absolute_max,
            "center": np.nan,
            "percentile": float(absolute_cfg["percentile"]),
            "scale_scope": scope,
            "sampled_value_count": int(absolute_pool.size),
        },
        "signed_improvement": {
            "cmap": str(signed_cfg["cmap"]),
            "vmin": -signed_limit,
            "vmax": signed_limit,
            "center": float(signed_cfg["center"]),
            "percentile": float(signed_cfg["absolute_percentile"]),
            "scale_scope": scope,
            "sampled_value_count": int(signed_pool.size),
        },
    }


def _indexed_palette(cmap_name: str) -> list[int]:
    cmap = colormaps.get_cmap(cmap_name)
    palette = [224, 224, 224]
    for value in np.linspace(0.0, 1.0, 255):
        rgb = cmap(float(value))[:3]
        palette.extend(int(round(channel * 255.0)) for channel in rgb)
    return palette


def save_indexed_map_png(
    values: np.ndarray,
    output_path: str | Path,
    *,
    cmap: str,
    vmin: float,
    vmax: float,
    center: float | None = None,
    no_data_mask: np.ndarray | None = None,
    compress_level: int = 9,
) -> None:
    """Save one deterministic 8-bit indexed display map."""

    array = np.asarray(values, dtype=np.float32)
    if array.ndim != 2:
        raise ValueError("Numeric display maps must be two-dimensional")
    if not np.isfinite(array).all():
        raise ValueError("Numeric display maps must contain only finite values")
    if not float(vmax) > float(vmin):
        raise ValueError("vmax must be greater than vmin")
    norm = (
        TwoSlopeNorm(vmin=float(vmin), vcenter=float(center), vmax=float(vmax))
        if center is not None and np.isfinite(center)
        else Normalize(vmin=float(vmin), vmax=float(vmax), clip=True)
    )
    normalized = np.clip(norm(array), 0.0, 1.0)
    indices = 1 + np.rint(normalized * 254.0).astype(np.uint8)
    has_no_data = no_data_mask is not None
    if has_no_data:
        no_data = np.asarray(no_data_mask, dtype=bool)
        if no_data.shape != array.shape:
            raise ValueError("no_data_mask shape does not match numeric map")
        indices[no_data] = 0
    image = Image.fromarray(indices, mode="P")
    image.putpalette(_indexed_palette(cmap))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs: dict[str, Any] = {
        "format": "PNG", "optimize": True, "compress_level": int(compress_level)
    }
    if has_no_data:
        save_kwargs["transparency"] = 0
    image.save(output, **save_kwargs)


def _rgba_layer(mask: np.ndarray, colour: Sequence[int]) -> Image.Image:
    mask_bool = np.asarray(mask, dtype=bool)
    rgba = np.zeros((*mask_bool.shape, 4), dtype=np.uint8)
    rgba[mask_bool] = np.asarray(colour, dtype=np.uint8)
    return Image.fromarray(rgba, mode="RGBA")


def build_spatial_overlay_image(
    regions: Mapping[str, Region],
    *,
    config: Mapping[str, Any],
) -> Image.Image:
    """Build a transparent reusable geometry and boundary overlay."""

    full = regions["full_image"]
    overlay = Image.new("RGBA", (full.width, full.height), (0, 0, 0, 0))
    colours = config["visualization"]["overlay_colours"]
    for region_id, colour_key in (
        ("masked_region", "mask_fill_rgba"),
        ("outside_boundary_ring", "outside_spillover_rgba"),
        ("outer_boundary_band", "outer_boundary_rgba"),
        ("inner_boundary_band", "inner_boundary_rgba"),
    ):
        overlay = Image.alpha_composite(
            overlay, _rgba_layer(regions[region_id].mask, colours[colour_key])
        )
    draw = ImageDraw.Draw(overlay)
    for region_id, colour_key in (
        ("content_region", "content_box_rgba"),
        ("mask_bbox_crop", "mask_box_rgba"),
    ):
        bbox = regions[region_id].bbox
        if bbox is not None:
            x0, y0, x1, y1 = bbox
            draw.rectangle(
                (x0, y0, x1 - 1, y1 - 1),
                outline=tuple(colours[colour_key]),
                width=2,
            )
    return overlay


def save_spatial_overlay_png(
    regions: Mapping[str, Region],
    output_path: str | Path,
    *,
    config: Mapping[str, Any],
) -> None:
    """Save a transparent reusable geometry and boundary overlay."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    build_spatial_overlay_image(regions, config=config).save(
        output,
        format="PNG",
        optimize=True,
        compress_level=int(config["visualization"]["png_compress_level"]),
    )


def _candidate_manifest_base(
    row: Mapping[str, Any] | pd.Series,
    *,
    map_id: str,
) -> dict[str, Any]:
    return {
        "asset_kind": "candidate_map",
        "map_id": map_id,
        "candidate_id": str(_row_value(row, "candidate_id")),
        "case_id": str(_row_value(row, "case_id")),
        "model_id": str(_row_value(row, "model_id")),
        "painting_id": str(_row_value(row, "painting_id")),
        "selection_role": "",
        "renderer_version": SPATIAL_MAP_RENDERER_VERSION,
        "status": "passed",
        "issue": "",
    }


def save_candidate_map_assets(
    row: Mapping[str, Any] | pd.Series,
    result: SpatialCandidateResult,
    *,
    scales: Mapping[str, Mapping[str, Any]],
    maps_root: str | Path,
    project_root: str | Path,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Persist the five canonical display assets for one non-zero candidate."""

    if bool(_row_value(row, "is_zero_control", False)):
        return pd.DataFrame(columns=SPATIAL_MAP_IMAGE_MANIFEST_COLUMNS)
    map_id = make_map_id(str(_row_value(row, "candidate_id")))
    model_id = str(_row_value(row, "model_id"))
    output_dir = Path(maps_root) / model_id / map_id
    compress = int(config["visualization"]["png_compress_level"])
    paths = {
        map_type: output_dir / f"{map_type}.png"
        for map_type in CANDIDATE_MAP_TYPES
    }
    absolute_scale = scales["absolute_error"]
    signed_scale = scales["signed_improvement"]
    for map_type, source_key, scale, no_data in (
        ("damaged_absolute_error", "damaged_absolute_error", absolute_scale, None),
        ("restored_absolute_error", "restored_absolute_error", absolute_scale, None),
        ("signed_improvement", "signed_improvement", signed_scale, None),
        (
            "masked_signed_improvement", "signed_improvement", signed_scale,
            ~result.regions["masked_region"].mask,
        ),
    ):
        center = scale["center"]
        save_indexed_map_png(
            result.maps[source_key],
            paths[map_type],
            cmap=str(scale["cmap"]),
            vmin=float(scale["vmin"]),
            vmax=float(scale["vmax"]),
            center=float(center) if np.isfinite(center) else None,
            no_data_mask=no_data,
            compress_level=compress,
        )
    save_spatial_overlay_png(result.regions, paths["spatial_overlay"], config=config)
    height, width = result.maps["signed_improvement"].shape
    records: list[dict[str, Any]] = []
    base = _candidate_manifest_base(row, map_id=map_id)
    for map_type, path in paths.items():
        is_absolute = map_type in {
            "damaged_absolute_error", "restored_absolute_error"
        }
        is_signed = map_type in {
            "signed_improvement", "masked_signed_improvement"
        }
        scale = absolute_scale if is_absolute else signed_scale if is_signed else None
        records.append({
            **base,
            "map_image_id": make_map_image_id(map_id, map_type),
            "map_type": map_type,
            "relative_path": project_relative_path(path, project_root),
            "sha256": sha256_path(path),
            "size_bytes": int(path.stat().st_size),
            "width": int(width),
            "height": int(height),
            "image_mode": "P" if scale is not None else "RGBA",
            "format": "PNG",
            "cmap": str(scale["cmap"]) if scale is not None else "",
            "vmin": float(scale["vmin"]) if scale is not None else np.nan,
            "vmax": float(scale["vmax"]) if scale is not None else np.nan,
            "center": (
                float(scale["center"])
                if scale is not None and np.isfinite(scale["center"])
                else np.nan
            ),
            "scale_scope": (
                str(scale["scale_scope"]) if scale is not None else "geometry_overlay"
            ),
            "quantization_policy": (
                "indexed_uint8_documented_scale" if scale is not None else "rgba_overlay"
            ),
            "no_data_policy": (
                "transparent_outside_active_mask"
                if map_type == "masked_signed_improvement"
                else "not_applicable"
            ),
        })
    frame = pd.DataFrame(records, columns=SPATIAL_MAP_IMAGE_MANIFEST_COLUMNS)
    validation = validate_dataframe(frame, SPATIAL_MAP_IMAGE_MANIFEST_SCHEMA)
    if not validation.passed:
        raise ValueError(f"Candidate map manifest violates schema: {validation.to_dict()}")
    return frame


def write_dataframe_atomic(
    dataframe: pd.DataFrame,
    path: str | Path,
    *,
    attempts: int = 8,
    retry_delay_seconds: float = 0.25,
) -> None:
    """Write a CSV atomically with bounded Windows replace retries."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + f".{os.getpid()}.tmp")
    dataframe.to_csv(temporary, index=False)
    last_error: OSError | None = None
    for attempt in range(int(attempts)):
        try:
            os.replace(temporary, target)
            return
        except OSError as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(float(retry_delay_seconds))
    temporary.unlink(missing_ok=True)
    assert last_error is not None
    raise last_error


def _candidate_complete(
    candidate_id: str,
    *,
    is_zero_control: bool,
    diagnostics: pd.DataFrame,
    manifest: pd.DataFrame,
    project_root: str | Path,
) -> bool:
    candidate_diagnostics = diagnostics.loc[
        diagnostics.get("candidate_id", pd.Series(dtype=str)).astype(str).eq(candidate_id)
    ]
    if candidate_diagnostics.empty:
        return False
    if is_zero_control:
        return True
    candidate_maps = manifest.loc[
        manifest.get("candidate_id", pd.Series(dtype=str)).astype(str).eq(candidate_id)
        & manifest.get("asset_kind", pd.Series(dtype=str)).astype(str).eq("candidate_map")
    ]
    if set(candidate_maps.get("map_type", pd.Series(dtype=str))) != set(CANDIDATE_MAP_TYPES):
        return False
    return all(
        resolve_path(path, project_root).is_file()
        for path in candidate_maps["relative_path"]
    )


def run_spatial_diagnostics(
    worklist: pd.DataFrame,
    *,
    project_root: str | Path,
    maps_root: str | Path,
    config: Mapping[str, Any],
    scales: Mapping[str, Mapping[str, Any]],
    diagnostics_checkpoint_path: str | Path | None = None,
    map_manifest_checkpoint_path: str | Path | None = None,
    progress_callback: Callable[[int, int, int], None] | None = None,
) -> SpatialRunResult:
    """Compute summaries and map assets with resumable bounded checkpoints."""

    diagnostics = (
        pd.read_csv(diagnostics_checkpoint_path)
        if diagnostics_checkpoint_path and Path(diagnostics_checkpoint_path).is_file()
        else pd.DataFrame(columns=SPATIAL_DIAGNOSTICS_COLUMNS)
    )
    manifest = (
        pd.read_csv(map_manifest_checkpoint_path)
        if map_manifest_checkpoint_path and Path(map_manifest_checkpoint_path).is_file()
        else pd.DataFrame(columns=SPATIAL_MAP_IMAGE_MANIFEST_COLUMNS)
    )
    completed_ids: set[str] = set()
    for row in worklist.itertuples(index=False):
        candidate_id = str(row.candidate_id)
        if _candidate_complete(
            candidate_id,
            is_zero_control=bool(row.is_zero_control),
            diagnostics=diagnostics,
            manifest=manifest,
            project_root=project_root,
        ):
            completed_ids.add(candidate_id)
    reused = len(completed_ids)
    total = len(worklist)
    interval = int(config["execution"]["checkpoint_interval_candidates"])
    for number, (_, row) in enumerate(worklist.iterrows(), start=1):
        candidate_id = str(row["candidate_id"])
        if candidate_id not in completed_ids:
            result = compute_candidate_spatial_diagnostics(
                row, project_root=project_root, config=config
            )
            diagnostics = (
                result.diagnostics.copy()
                if diagnostics.empty
                else pd.concat([diagnostics, result.diagnostics], ignore_index=True)
            )
            if not bool(row["is_zero_control"]):
                map_rows = save_candidate_map_assets(
                    row,
                    result,
                    scales=scales,
                    maps_root=maps_root,
                    project_root=project_root,
                    config=config,
                )
                manifest = (
                    map_rows.copy()
                    if manifest.empty
                    else pd.concat([manifest, map_rows], ignore_index=True)
                )
            completed_ids.add(candidate_id)
        if number % interval == 0 or number == total:
            diagnostics = diagnostics.drop_duplicates(
                "spatial_diagnostic_id", keep="last"
            ).loc[:, SPATIAL_DIAGNOSTICS_COLUMNS]
            manifest = manifest.drop_duplicates(
                "map_image_id", keep="last"
            ).loc[:, SPATIAL_MAP_IMAGE_MANIFEST_COLUMNS]
            if diagnostics_checkpoint_path:
                write_dataframe_atomic(diagnostics, diagnostics_checkpoint_path)
            if map_manifest_checkpoint_path:
                write_dataframe_atomic(manifest, map_manifest_checkpoint_path)
        if progress_callback is not None:
            progress_callback(number, total, reused)
    diagnostics = diagnostics.sort_values(
        ["candidate_id", "region_id"], kind="stable"
    ).reset_index(drop=True)
    manifest = manifest.sort_values(
        ["model_id", "candidate_id", "map_type"], kind="stable"
    ).reset_index(drop=True)
    return SpatialRunResult(
        diagnostics=diagnostics,
        map_images=manifest,
        completed_candidates=len(completed_ids),
        reused_candidates=reused,
    )


def validate_spatial_diagnostics(
    diagnostics: pd.DataFrame,
    *,
    expected_candidate_ids: Sequence[str] | None = None,
    tolerance: float = 1e-5,
) -> dict[str, Any]:
    """Validate schema, arithmetic, fractions, and candidate coverage."""

    schema = validate_dataframe(diagnostics, SPATIAL_DIAGNOSTICS_SCHEMA)
    observed = set(diagnostics.get("candidate_id", pd.Series(dtype=str)).astype(str))
    expected = (
        set()
        if expected_candidate_ids is None
        else set(map(str, expected_candidate_ids))
    )
    fraction_columns = [
        "improved_pixel_fraction", "worsened_pixel_fraction",
        "unchanged_pixel_fraction", "restoration_changed_pixel_fraction",
    ]
    bounds_valid = all(
        diagnostics[column].dropna().between(0.0, 1.0).all()
        for column in fraction_columns if column in diagnostics
    )
    signed_arithmetic = (
        diagnostics["damaged_error_mean"]
        - diagnostics["restored_error_mean"]
        - diagnostics["signed_improvement_mean"]
    ).abs()
    fractions_sum = (
        diagnostics["improved_pixel_fraction"]
        + diagnostics["worsened_pixel_fraction"]
        + diagnostics["unchanged_pixel_fraction"]
    )
    missing = sorted(expected - observed) if expected else []
    unexpected = sorted(observed - expected) if expected else []
    result = {
        "schema": schema.to_dict(),
        "missing_candidate_count": len(missing),
        "unexpected_candidate_count": len(unexpected),
        "missing_candidate_examples": missing[:5],
        "unexpected_candidate_examples": unexpected[:5],
        "positive_region_pixels": bool(
            (diagnostics["region_pixel_count"] > 0).all()
        ),
        "fraction_bounds_valid": bool(bounds_valid),
        "fraction_partition_max_error": float((fractions_sum - 1.0).abs().max()),
        "signed_mean_arithmetic_max_error": float(signed_arithmetic.max()),
    }
    result["passed"] = bool(
        schema.passed
        and not missing and not unexpected
        and result["positive_region_pixels"]
        and result["fraction_bounds_valid"]
        and result["fraction_partition_max_error"] <= tolerance
        and result["signed_mean_arithmetic_max_error"] <= tolerance
    )
    return result


def validate_map_image_manifest(
    manifest: pd.DataFrame,
    *,
    project_root: str | Path,
    verify_checksums: bool = False,
) -> dict[str, Any]:
    """Validate normalized image metadata and linked PNG assets."""

    schema = validate_dataframe(manifest, SPATIAL_MAP_IMAGE_MANIFEST_SCHEMA)
    missing_paths: list[str] = []
    checksum_mismatches: list[str] = []
    for row in manifest.itertuples(index=False):
        path = resolve_path(row.relative_path, project_root)
        if not path.is_file() or path.stat().st_size <= 0:
            missing_paths.append(str(row.relative_path))
            continue
        if verify_checksums and sha256_path(path) != str(row.sha256):
            checksum_mismatches.append(str(row.relative_path))
    result = {
        "schema": schema.to_dict(),
        "missing_asset_count": len(missing_paths),
        "checksum_mismatch_count": len(checksum_mismatches),
        "missing_asset_examples": missing_paths[:5],
        "checksum_mismatch_examples": checksum_mismatches[:5],
    }
    result["passed"] = bool(
        schema.passed and not missing_paths and not checksum_mismatches
    )
    return result


def render_candidate_spatial_panel(
    row: Mapping[str, Any] | pd.Series,
    *,
    project_root: str | Path,
    config: Mapping[str, Any],
    scales: Mapping[str, Mapping[str, Any]],
    output_path: str | Path | None = None,
    selection_role: str = "preview",
) -> plt.Figure:
    """Render a labelled nine-panel diagnostic view for one candidate."""

    arrays = load_candidate_arrays(row, project_root=project_root)
    result = compute_candidate_spatial_diagnostics(
        row, project_root=project_root, config=config
    )
    active_mask = result.regions["masked_region"].mask
    absolute = scales["absolute_error"]
    signed = scales["signed_improvement"]
    fig, axes = plt.subplots(3, 3, figsize=(15, 14), constrained_layout=True)
    for axis, image, title in (
        (axes[0, 0], arrays["clean"].astype(np.uint8), "Clean reference"),
        (axes[0, 1], arrays["damaged"].astype(np.uint8), "Damaged input"),
        (axes[0, 2], arrays["restored"].astype(np.uint8), "Restored output"),
    ):
        axis.imshow(image)
        axis.set_title(title)
    axes[1, 0].imshow(active_mask, cmap="gray", vmin=0, vmax=1)
    axes[1, 0].set_title("Active mask / effect support")
    damaged_artist = axes[1, 1].imshow(
        result.maps["damaged_absolute_error"],
        cmap=absolute["cmap"],
        vmin=absolute["vmin"],
        vmax=absolute["vmax"],
    )
    axes[1, 1].set_title("Clean-damaged absolute error")
    axes[1, 2].imshow(
        result.maps["restored_absolute_error"],
        cmap=absolute["cmap"],
        vmin=absolute["vmin"],
        vmax=absolute["vmax"],
    )
    axes[1, 2].set_title("Clean-restored absolute error")
    signed_norm = TwoSlopeNorm(
        vmin=signed["vmin"], vcenter=signed["center"], vmax=signed["vmax"]
    )
    signed_artist = axes[2, 0].imshow(
        result.maps["signed_improvement"], cmap=signed["cmap"], norm=signed_norm
    )
    axes[2, 0].set_title("Signed improvement: positive = reduced error")
    masked = np.ma.masked_where(~active_mask, result.maps["signed_improvement"])
    axes[2, 1].imshow(masked, cmap=signed["cmap"], norm=signed_norm)
    axes[2, 1].set_title("Masked signed improvement")
    axes[2, 2].imshow(arrays["restored"].astype(np.uint8))
    axes[2, 2].imshow(np.asarray(
        build_spatial_overlay_image(result.regions, config=config)
    ))
    axes[2, 2].set_title("Mask, boxes, boundaries, and spillover ring")
    for axis in axes.ravel():
        axis.axis("off")
    fig.colorbar(
        damaged_artist,
        ax=[axes[1, 1], axes[1, 2]],
        shrink=0.72,
        label="Mean absolute RGB error [0-255]",
    )
    fig.colorbar(
        signed_artist,
        ax=[axes[2, 0], axes[2, 1]],
        shrink=0.72,
        label="Damaged error - restored error",
    )
    fig.suptitle(
        f"{_row_value(row, 'model_id')} | {_row_value(row, 'case_id')}\n"
        f"selection={selection_role}; diagnostic-only evidence",
        fontsize=14,
    )
    if output_path is not None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=180, bbox_inches="tight")
    return fig


__all__ = [
    "CANDIDATE_MAP_TYPES",
    "ERROR_MAP_MODULE_NAME",
    "ERROR_MAP_VERSION",
    "NUMERIC_MAP_TYPES",
    "SPATIAL_DIAGNOSTIC_VERSION",
    "SPATIAL_MAP_MANIFEST_VERSION",
    "SPATIAL_MAP_RENDERER_VERSION",
    "SPATIAL_REGION_ORDER",
    "SpatialCandidateResult",
    "SpatialRunResult",
    "build_candidate_regions",
    "build_spatial_overlay_image",
    "compute_candidate_spatial_diagnostics",
    "compute_case_maps",
    "compute_global_visualization_scales",
    "load_candidate_arrays",
    "load_mask_array",
    "load_rgb_array",
    "load_spatial_diagnostics_config",
    "make_map_id",
    "make_map_image_id",
    "make_spatial_diagnostic_id",
    "project_relative_path",
    "render_candidate_spatial_panel",
    "resolve_path",
    "run_spatial_diagnostics",
    "save_candidate_map_assets",
    "save_indexed_map_png",
    "save_spatial_overlay_png",
    "sha256_path",
    "validate_map_image_manifest",
    "validate_spatial_diagnostics",
    "write_dataframe_atomic",
]
