"""Normalized LPIPS evaluation for restoration candidates.

Metric preprocessing lives here; spatial geometry is delegated to the canonical
``restoration_eval.regions`` helper. Canonical evidence is limited to contiguous
content and mask-bounding-box crops.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import math
import os
import platform
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd
import yaml
from PIL import Image

from .regions import (
    Region,
    content_region,
    crop_array,
    mask_bbox_region,
    metric_region_is_valid,
)
from .schemas import LPIPS_METRICS_COLUMNS, LPIPS_METRICS_SCHEMA, validate_dataframe

LPIPS_MODULE_NAME = "restoration_eval.metrics_lpips"
LPIPS_MODULE_VERSION = "3.0.0"
LPIPS_METRIC_VERSION = "lpips_alex_full_reference.v1"
LPIPS_SCHEMA_VERSION = "lpips_metrics.v1"
LPIPS_METRIC_FAMILY = "perceptual"
LPIPS_METRIC_NAME = "lpips"
LPIPS_IMPROVEMENT_DIRECTION = "damaged_minus_restored"
LPIPS_ACTIVE_REGIONS = ("content_region", "mask_bbox_crop")

ProgressCallback = Callable[[str], None]
CheckpointCallback = Callable[[pd.DataFrame], None]


@dataclass(frozen=True)
class LPIPSInputGeometry:
    """Deterministic output geometry for one aspect-preserving transform."""

    original_width: int
    original_height: int
    resized_width: int
    resized_height: int
    input_width: int
    input_height: int
    pad_left: int
    pad_top: int


@dataclass(frozen=True)
class LPIPSCaseResult:
    """Metric rows and execution accounting for one restoration case."""

    metrics: pd.DataFrame
    summary: Mapping[str, Any]


@dataclass(frozen=True)
class LPIPSRunResult:
    """Metric rows and execution accounting for a complete run."""

    metrics: pd.DataFrame
    summary: Mapping[str, Any]


def get_package_version(package_name: str) -> str:
    """Return an installed distribution version without importing it."""

    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def validate_lpips_runtime_dependencies() -> pd.DataFrame:
    """Return a compact dependency table for notebook preflight."""

    records = []
    for package in ("lpips", "torch", "torchvision", "numpy", "pandas", "Pillow"):
        version = get_package_version(package)
        records.append({
            "dependency": package,
            "version": version,
            "installed": version != "not-installed",
            "status": "passed" if version != "not-installed" else "failed",
        })
    return pd.DataFrame(records)


def load_lpips_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the Notebook 14 configuration."""

    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("LPIPS configuration must be a mapping")
    if payload.get("config_schema_version") != "lpips_metrics_config.v1":
        raise ValueError("Unsupported LPIPS configuration schema")
    settings = payload.get("lpips_metrics")
    if not isinstance(settings, dict):
        raise ValueError("Configuration is missing lpips_metrics")
    required = {
        "metric_version", "output_schema_version", "inputs", "output",
        "model", "transform", "regions", "execution", "expected_counts",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"lpips_metrics is missing keys: {missing}")
    if settings["metric_version"] != LPIPS_METRIC_VERSION:
        raise ValueError("Configured metric_version disagrees with the helper")
    if settings["output_schema_version"] != LPIPS_SCHEMA_VERSION:
        raise ValueError("Configured output_schema_version disagrees with the schema")
    if tuple(settings["regions"]["active_regions"]) != LPIPS_ACTIVE_REGIONS:
        raise ValueError(f"active_regions must be {LPIPS_ACTIVE_REGIONS}")
    transform = settings["transform"]
    maximum = int(transform["maximum_side_pixels"])
    minimum = int(transform["minimum_side_pixels"])
    if maximum <= 0 or minimum <= 0 or minimum > maximum:
        raise ValueError("LPIPS transform sides must satisfy 0 < minimum <= maximum")
    if str(transform["interpolation"]).lower() != "bicubic":
        raise ValueError("Only deterministic bicubic LPIPS resizing is supported")
    execution = settings["execution"]
    for key in ("batch_size", "progress_interval_cases", "checkpoint_interval_cases"):
        if int(execution[key]) <= 0:
            raise ValueError(f"{key} must be positive")
    if str(settings["model"]["network"]) not in {"alex", "vgg", "squeeze"}:
        raise ValueError("LPIPS network must be alex, vgg, or squeeze")
    return payload


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    return config["lpips_metrics"]


def _resolve(project_root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(project_root) / path


def resolve_lpips_device(config: Mapping[str, Any]) -> str:
    """Resolve the configured device and enforce its fallback policy."""

    import torch

    model_settings = _settings(config)["model"]
    preferred = str(model_settings["preferred_device"]).strip().lower()
    allow_cpu = bool(model_settings["allow_cpu_fallback"])
    if preferred == "cuda" and torch.cuda.is_available():
        return "cuda"
    if preferred == "cuda" and not allow_cpu:
        raise RuntimeError("CUDA requested but unavailable; CPU fallback is disabled")
    if preferred not in {"cuda", "cpu"}:
        raise ValueError(f"Unsupported preferred_device: {preferred}")
    return "cpu"


def configure_lpips_determinism(config: Mapping[str, Any]) -> None:
    """Apply the deterministic inference policy declared by the config."""

    import torch

    enabled = bool(_settings(config)["model"]["deterministic_algorithms"])
    torch.manual_seed(0)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(0)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = enabled
    torch.use_deterministic_algorithms(enabled, warn_only=True)


def load_configured_lpips_model(
    config: Mapping[str, Any], *, device: str | None = None,
) -> tuple[Any, str, dict[str, str]]:
    """Load the configured LPIPS network and return explicit provenance."""

    import lpips
    import torch

    configure_lpips_determinism(config)
    resolved_device = device or resolve_lpips_device(config)
    model_settings = _settings(config)["model"]
    network = str(model_settings["network"])
    lpips_version = str(model_settings["lpips_version"])
    model = lpips.LPIPS(net=network, version=lpips_version).to(resolved_device).eval()
    metadata = {
        "network": network,
        "lpips_version": lpips_version,
        "lpips_package_version": get_package_version("lpips"),
        "torch_version": str(torch.__version__),
        "device": resolved_device,
        "cuda_device_name": (
            torch.cuda.get_device_name(0)
            if resolved_device == "cuda" and torch.cuda.is_available() else ""
        ),
        "python_version": platform.python_version(),
    }
    return model, resolved_device, metadata


def get_device(prefer_cuda: bool = True) -> Any:
    """Compatibility entry point retained for pre-refactor Notebook 27."""

    import torch

    return torch.device("cuda" if prefer_cuda and torch.cuda.is_available() else "cpu")


def load_lpips_model(*, net: str = "alex", device: Any | None = None) -> Any:
    """Compatibility loader retained for pre-refactor Notebook 27.

    New notebooks must use :func:`load_configured_lpips_model` so configuration
    and provenance remain explicit.
    """

    import lpips
    import torch

    resolved = device if device is not None else get_device(prefer_cuda=True)
    torch.manual_seed(0)
    model = lpips.LPIPS(net=str(net), version="0.1")
    return model.to(resolved).eval()


def load_rgb_array(path: str | Path) -> np.ndarray:
    """Load an image as RGB uint8."""

    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


def load_mask_array(path: str | Path) -> np.ndarray:
    """Load a mask or effect-support image as uint8 intensity."""

    with Image.open(path) as image:
        return np.asarray(image.convert("L"), dtype=np.uint8)


def _require_same_image_shape(*arrays: np.ndarray) -> None:
    shapes = {tuple(array.shape) for array in arrays}
    if len(shapes) != 1:
        raise ValueError(f"Image geometry mismatch: {sorted(shapes)}")
    if arrays[0].ndim != 3 or arrays[0].shape[2] != 3:
        raise ValueError(f"Expected RGB arrays, received {arrays[0].shape}")


def lpips_input_geometry(
    width: int, height: int, config: Mapping[str, Any],
) -> LPIPSInputGeometry:
    """Calculate aspect-preserving resize and minimal padding geometry."""

    width, height = int(width), int(height)
    if width <= 0 or height <= 0:
        raise ValueError(f"LPIPS dimensions must be positive: {(width, height)}")
    transform = _settings(config)["transform"]
    maximum = int(transform["maximum_side_pixels"])
    minimum = int(transform["minimum_side_pixels"])
    scale = maximum / float(max(width, height))
    resized_width = max(1, min(maximum, int(round(width * scale))))
    resized_height = max(1, min(maximum, int(round(height * scale))))
    input_width = max(minimum, resized_width)
    input_height = max(minimum, resized_height)
    return LPIPSInputGeometry(
        original_width=width,
        original_height=height,
        resized_width=resized_width,
        resized_height=resized_height,
        input_width=input_width,
        input_height=input_height,
        pad_left=(input_width - resized_width) // 2,
        pad_top=(input_height - resized_height) // 2,
    )


def prepare_lpips_tensor(
    rgb: np.ndarray, config: Mapping[str, Any],
) -> tuple[Any, LPIPSInputGeometry]:
    """Convert an RGB crop to one normalized CHW tensor on CPU."""

    import torch

    array = np.asarray(rgb)
    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError(f"Expected HxWx3 RGB input, received {array.shape}")
    if array.dtype != np.uint8:
        array = np.clip(np.rint(array), 0, 255).astype(np.uint8)
    geometry = lpips_input_geometry(array.shape[1], array.shape[0], config)
    resized = np.asarray(
        Image.fromarray(array, mode="RGB").resize(
            (geometry.resized_width, geometry.resized_height),
            resample=Image.Resampling.BICUBIC,
        ),
        dtype=np.uint8,
    )
    neutral = int(_settings(config)["transform"]["neutral_padding_value"])
    canvas = np.full(
        (geometry.input_height, geometry.input_width, 3), neutral, dtype=np.uint8
    )
    y0, x0 = geometry.pad_top, geometry.pad_left
    canvas[y0:y0 + geometry.resized_height, x0:x0 + geometry.resized_width] = resized
    normalized = canvas.astype(np.float32) / 127.5 - 1.0
    tensor = torch.from_numpy(np.transpose(normalized, (2, 0, 1))).contiguous()
    return tensor, geometry


def build_case_lpips_regions(
    case: Mapping[str, Any], raw_mask: np.ndarray, config: Mapping[str, Any],
) -> dict[str, Region]:
    """Build only the approved rectangular LPIPS regions."""

    active_mask = np.asarray(raw_mask) >= int(case["mask_threshold"])
    content_bbox = tuple(
        int(case[column])
        for column in ("content_x_min", "content_y_min", "content_x_max", "content_y_max")
    )
    region_settings = _settings(config)["regions"]
    candidates = {
        "content_region": content_region(active_mask.shape, content_bbox),
        "mask_bbox_crop": mask_bbox_region(
            active_mask,
            margin=int(region_settings["mask_bbox_margin_pixels"]),
            support_bbox=content_bbox,
        ),
    }
    result: dict[str, Region] = {}
    for region_id in region_settings["active_regions"]:
        region = candidates[region_id]
        valid, reason = metric_region_is_valid(LPIPS_METRIC_NAME, region)
        if valid:
            result[region_id] = region
        elif region_id == "content_region":
            raise ValueError(f"Invalid mandatory content region: {reason}")
    return result


def build_lpips_execution_plan(
    worklist: pd.DataFrame, *, project_root: str | Path,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build exact candidate-region keys without loading restorations or LPIPS."""

    required = {
        "case_id", "candidate_id", "model_id", "mask_threshold",
        "mask_or_effect_path", "content_x_min", "content_y_min",
        "content_x_max", "content_y_max",
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
        raw_mask = load_mask_array(_resolve(root, case["mask_or_effect_path"]))
        regions = build_case_lpips_regions(case, raw_mask, config)
        for candidate in group.itertuples(index=False):
            for region in regions.values():
                geometry = lpips_input_geometry(region.width, region.height, config)
                records.append({
                    "case_id": str(candidate.case_id),
                    "candidate_id": str(candidate.candidate_id),
                    "model_id": str(candidate.model_id),
                    "region_id": region.region_id,
                    "region_pixel_count": int(region.pixel_count),
                    "region_width": int(region.width),
                    "region_height": int(region.height),
                    "input_width": int(geometry.input_width),
                    "input_height": int(geometry.input_height),
                })
    return pd.DataFrame(records, columns=(
        "case_id", "candidate_id", "model_id", "region_id",
        "region_pixel_count", "region_width", "region_height",
        "input_width", "input_height",
    ))


def expected_lpips_row_count(
    worklist: pd.DataFrame, *, project_root: str | Path,
    config: Mapping[str, Any],
) -> int:
    """Return exact valid candidate-region cardinality."""

    return len(build_lpips_execution_plan(
        worklist, project_root=project_root, config=config
    ))


def metric_row_id(
    case_id: str, candidate_id: str, region_id: str,
    metric_version: str = LPIPS_METRIC_VERSION,
) -> str:
    """Return one deterministic compact LPIPS evidence identifier."""

    payload = "|".join((case_id, candidate_id, LPIPS_METRIC_NAME, region_id, metric_version))
    return f"lp__{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20]}"


def _synchronize(device: str) -> None:
    if device == "cuda":
        import torch
        torch.cuda.synchronize()


def compute_lpips_batch(
    model: Any, reference_batch: Any, candidate_batch: Any, *, device: str,
) -> tuple[np.ndarray, float]:
    """Compute one equal-shaped batch and return distances and wall time."""

    import torch

    if tuple(reference_batch.shape) != tuple(candidate_batch.shape):
        raise ValueError(
            f"LPIPS batch shape mismatch: {reference_batch.shape} vs {candidate_batch.shape}"
        )
    reference = reference_batch.to(device, non_blocking=(device == "cuda"))
    candidate = candidate_batch.to(device, non_blocking=(device == "cuda"))
    _synchronize(device)
    started = time.perf_counter()
    with torch.inference_mode():
        output = model(reference, candidate)
    _synchronize(device)
    elapsed = time.perf_counter() - started
    values = output.detach().float().reshape(-1).cpu().numpy().astype(float)
    if len(values) != int(reference_batch.shape[0]):
        raise ValueError("LPIPS model returned an unexpected batch length")
    return values, float(elapsed)


def _record_base(
    candidate: Any, region: Region, geometry: LPIPSInputGeometry, *,
    config: Mapping[str, Any], device: str,
) -> dict[str, Any]:
    settings = _settings(config)
    return {
        "metric_row_id": metric_row_id(
            str(candidate.case_id), str(candidate.candidate_id), region.region_id,
            str(settings["metric_version"]),
        ),
        "case_id": str(candidate.case_id),
        "candidate_id": str(candidate.candidate_id),
        "model_id": str(candidate.model_id),
        "metric_family": LPIPS_METRIC_FAMILY,
        "metric_name": LPIPS_METRIC_NAME,
        "region_id": region.region_id,
        "region_pixel_count": int(region.pixel_count),
        "region_width": int(region.width),
        "region_height": int(region.height),
        "input_width": int(geometry.input_width),
        "input_height": int(geometry.input_height),
        "resize_policy": str(settings["transform"]["resize_policy"]),
        "improvement_direction": LPIPS_IMPROVEMENT_DIRECTION,
        "network": str(settings["model"]["network"]),
        "metric_version": str(settings["metric_version"]),
        "region_policy_version": str(settings["regions"]["policy_version"]),
        "schema_version": str(settings["output_schema_version"]),
        "device": str(device),
        "lpips_package_version": get_package_version("lpips"),
    }


def _error_row(
    candidate: Any, region: Region, geometry: LPIPSInputGeometry, *,
    config: Mapping[str, Any], device: str, damaged_value: float, issue: str,
) -> dict[str, Any]:
    record = _record_base(candidate, region, geometry, config=config, device=device)
    record.update({
        "damaged_value": damaged_value,
        "restored_value": math.nan,
        "improvement_value": math.nan,
        "metric_runtime_seconds": 0.0,
        "status": "error",
        "issue": str(issue),
    })
    return record


def compute_case_lpips_metrics(
    case_candidates: pd.DataFrame, *, model: Any, device: str,
    project_root: str | Path, config: Mapping[str, Any],
) -> LPIPSCaseResult:
    """Compute LPIPS rows for every candidate of exactly one case."""

    import torch

    if case_candidates.empty:
        return LPIPSCaseResult(
            pd.DataFrame(columns=LPIPS_METRICS_COLUMNS),
            {"case_count": 0, "candidate_count": 0, "baseline_pair_count": 0},
        )
    if case_candidates["case_id"].nunique() != 1:
        raise ValueError("compute_case_lpips_metrics accepts exactly one case_id")
    if case_candidates["candidate_id"].astype(str).duplicated().any():
        raise ValueError("candidate_id must be unique within a case")
    case = case_candidates.iloc[0]
    root = Path(project_root)
    clean = load_rgb_array(_resolve(root, case["clean_image_path"]))
    damaged = load_rgb_array(_resolve(root, case["input_image_path"]))
    raw_mask = load_mask_array(_resolve(root, case["mask_or_effect_path"]))
    _require_same_image_shape(clean, damaged)
    if raw_mask.shape != clean.shape[:2]:
        raise ValueError(f"Mask/image geometry mismatch: {raw_mask.shape} vs {clean.shape[:2]}")
    regions = build_case_lpips_regions(case, raw_mask, config)
    settings = _settings(config)
    batch_size = int(settings["execution"]["batch_size"])

    restored_arrays: dict[str, np.ndarray] = {}
    restored_issues: dict[str, str] = {}
    for candidate in case_candidates.itertuples(index=False):
        candidate_id = str(candidate.candidate_id)
        try:
            restored = load_rgb_array(_resolve(root, candidate.restored_path))
            _require_same_image_shape(clean, restored)
            restored_arrays[candidate_id] = restored
        except Exception as exc:
            restored_issues[candidate_id] = f"{type(exc).__name__}: {exc}"

    records: list[dict[str, Any]] = []
    baseline_seconds = restored_seconds = 0.0
    baseline_pairs = restored_pairs = computation_failures = 0
    candidates = list(case_candidates.itertuples(index=False))
    for region in regions.values():
        clean_tensor, geometry = prepare_lpips_tensor(crop_array(clean, region), config)
        damaged_tensor, damaged_geometry = prepare_lpips_tensor(
            crop_array(damaged, region), config
        )
        if geometry != damaged_geometry:
            raise ValueError("Clean and damaged LPIPS transforms disagree")
        try:
            values, elapsed = compute_lpips_batch(
                model, clean_tensor.unsqueeze(0), damaged_tensor.unsqueeze(0),
                device=device,
            )
            damaged_value = float(values[0])
            baseline_seconds += elapsed
            baseline_pairs += 1
            baseline_issue = ""
        except Exception as exc:
            damaged_value = math.nan
            baseline_issue = f"{type(exc).__name__}: {exc}"
            computation_failures += len(candidates)

        valid_candidates: list[Any] = []
        valid_tensors: list[Any] = []
        for candidate in candidates:
            candidate_id = str(candidate.candidate_id)
            issue = restored_issues.get(candidate_id, baseline_issue)
            if issue:
                records.append(_error_row(
                    candidate, region, geometry, config=config, device=device,
                    damaged_value=damaged_value, issue=issue,
                ))
                continue
            restored_tensor, restored_geometry = prepare_lpips_tensor(
                crop_array(restored_arrays[candidate_id], region), config
            )
            if restored_geometry != geometry:
                raise ValueError("Restored LPIPS transform disagrees with clean transform")
            valid_candidates.append(candidate)
            valid_tensors.append(restored_tensor)

        for start in range(0, len(valid_candidates), batch_size):
            batch_candidates = valid_candidates[start:start + batch_size]
            candidate_batch = torch.stack(valid_tensors[start:start + batch_size], dim=0)
            reference_batch = clean_tensor.unsqueeze(0).repeat(
                len(batch_candidates), 1, 1, 1
            )
            try:
                values, elapsed = compute_lpips_batch(
                    model, reference_batch, candidate_batch, device=device
                )
                restored_seconds += elapsed
                restored_pairs += len(batch_candidates)
                allocated_runtime = elapsed / max(len(batch_candidates), 1)
                for candidate, restored_value in zip(batch_candidates, values):
                    record = _record_base(
                        candidate, region, geometry, config=config, device=device
                    )
                    restored_value = float(restored_value)
                    record.update({
                        "damaged_value": damaged_value,
                        "restored_value": restored_value,
                        "improvement_value": damaged_value - restored_value,
                        "metric_runtime_seconds": float(allocated_runtime),
                        "status": "ok",
                        "issue": "",
                    })
                    records.append(record)
            except Exception as exc:
                issue = f"{type(exc).__name__}: {exc}"
                computation_failures += len(batch_candidates)
                for candidate in batch_candidates:
                    records.append(_error_row(
                        candidate, region, geometry, config=config, device=device,
                        damaged_value=damaged_value, issue=issue,
                    ))

    frame = pd.DataFrame(records, columns=LPIPS_METRICS_COLUMNS)
    candidate_order = {
        str(candidate_id): number
        for number, candidate_id in enumerate(case_candidates["candidate_id"])
    }
    region_order = {name: number for number, name in enumerate(LPIPS_ACTIVE_REGIONS)}
    if not frame.empty:
        frame = (
            frame.assign(
                _candidate_order=frame["candidate_id"].map(candidate_order),
                _region_order=frame["region_id"].map(region_order),
            )
            .sort_values(["_candidate_order", "_region_order"], kind="stable")
            .drop(columns=["_candidate_order", "_region_order"])
            .reset_index(drop=True)
        )
    return LPIPSCaseResult(frame.loc[:, LPIPS_METRICS_COLUMNS], {
        "case_count": 1,
        "candidate_count": len(case_candidates),
        "region_count": len(regions),
        "baseline_pair_count": baseline_pairs,
        "restored_pair_count": restored_pairs,
        "restored_load_failure_count": len(restored_issues),
        "computation_failure_count": computation_failures,
        "baseline_runtime_seconds": baseline_seconds,
        "restored_runtime_seconds": restored_seconds,
    })


def _expected_case_keys(
    group: pd.DataFrame, *, project_root: str | Path,
    config: Mapping[str, Any],
) -> set[tuple[str, str]]:
    case = group.iloc[0]
    raw_mask = load_mask_array(_resolve(project_root, case["mask_or_effect_path"]))
    regions = build_case_lpips_regions(case, raw_mask, config)
    return {
        (str(candidate_id), region_id)
        for candidate_id in group["candidate_id"] for region_id in regions
    }


def run_lpips_metrics(
    worklist: pd.DataFrame, *, model: Any, device: str,
    project_root: str | Path, config: Mapping[str, Any],
    prior_metrics: pd.DataFrame | None = None,
    progress_callback: ProgressCallback | None = None,
    checkpoint_callback: CheckpointCallback | None = None,
) -> LPIPSRunResult:
    """Compute every case with deterministic progress and complete-case resume."""

    groups = list(worklist.groupby("case_id", sort=False))
    total_cases = len(groups)
    execution = _settings(config)["execution"]
    progress_interval = int(execution["progress_interval_cases"])
    checkpoint_interval = int(execution["checkpoint_interval_cases"])
    prior = prior_metrics.copy() if prior_metrics is not None else pd.DataFrame(
        columns=LPIPS_METRICS_COLUMNS
    )
    frames: list[pd.DataFrame] = []
    totals: dict[str, Any] = {
        "evaluated_case_count": 0, "reused_case_count": 0,
        "candidate_count": 0, "baseline_pair_count": 0,
        "restored_pair_count": 0, "restored_load_failure_count": 0,
        "computation_failure_count": 0, "baseline_runtime_seconds": 0.0,
        "restored_runtime_seconds": 0.0,
    }
    started = time.perf_counter()
    for number, (case_id, group) in enumerate(groups, start=1):
        existing = prior.loc[
            prior.get("case_id", pd.Series(dtype=str)).astype(str).eq(str(case_id))
        ]
        expected_keys = _expected_case_keys(
            group, project_root=project_root, config=config
        )
        observed_keys = set()
        if not existing.empty and {"candidate_id", "region_id", "status"} <= set(existing):
            observed_keys = set(existing[["candidate_id", "region_id"]]
                                .astype(str).itertuples(index=False, name=None))
        reuse = (
            bool(observed_keys) and observed_keys == expected_keys
            and existing["status"].astype(str).eq("ok").all()
        )
        if reuse:
            frame = existing.loc[:, LPIPS_METRICS_COLUMNS].copy()
            totals["reused_case_count"] += 1
        else:
            result = compute_case_lpips_metrics(
                group, model=model, device=device,
                project_root=project_root, config=config,
            )
            frame = result.metrics
            totals["evaluated_case_count"] += 1
            for key in (
                "baseline_pair_count", "restored_pair_count",
                "restored_load_failure_count", "computation_failure_count",
                "baseline_runtime_seconds", "restored_runtime_seconds",
            ):
                totals[key] += result.summary[key]
        frames.append(frame)
        totals["candidate_count"] += len(group)
        if checkpoint_callback is not None and (
            number % checkpoint_interval == 0 or number == total_cases
        ):
            checkpoint_callback(pd.concat(frames, ignore_index=True))
        if progress_callback is not None and (
            number % progress_interval == 0 or number == total_cases
        ):
            elapsed = time.perf_counter() - started
            rate = number / max(elapsed, 1e-9)
            eta = max(total_cases - number, 0) / max(rate, 1e-9)
            progress_callback(
                f"LPIPS: {number}/{total_cases} cases "
                f"({100.0 * number / max(total_cases, 1):.1f}%), "
                f"{totals['candidate_count']}/{len(worklist)} candidates, "
                f"elapsed={elapsed:.1f}s, throughput={rate:.3f} cases/s, "
                f"eta={eta:.1f}s, latest={case_id}, "
                f"reused_cases={totals['reused_case_count']}"
            )
    metrics = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=LPIPS_METRICS_COLUMNS
    )
    candidate_order = {
        str(candidate_id): number
        for number, candidate_id in enumerate(worklist["candidate_id"])
    }
    region_order = {name: number for number, name in enumerate(LPIPS_ACTIVE_REGIONS)}
    if not metrics.empty:
        metrics = (
            metrics.assign(
                _candidate_order=metrics["candidate_id"].map(candidate_order),
                _region_order=metrics["region_id"].map(region_order),
            )
            .sort_values(["_candidate_order", "_region_order"], kind="stable")
            .drop(columns=["_candidate_order", "_region_order"])
            .reset_index(drop=True)
        )
    totals.update({
        "total_case_count": total_cases,
        "metric_row_count": len(metrics),
        "error_row_count": int(metrics["status"].astype(str).eq("error").sum()),
        "total_runtime_seconds": time.perf_counter() - started,
        "device": str(device),
        "batch_size": int(execution["batch_size"]),
    })
    return LPIPSRunResult(metrics.loc[:, LPIPS_METRICS_COLUMNS], totals)


def validate_lpips_metrics(
    metrics: pd.DataFrame, worklist: pd.DataFrame, *,
    project_root: str | Path, config: Mapping[str, Any],
    expected_plan: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Validate schema, exact keys, finite values, arithmetic, and controls."""

    schema = validate_dataframe(metrics, LPIPS_METRICS_SCHEMA, allow_extra_columns=False)
    plan = expected_plan if expected_plan is not None else build_lpips_execution_plan(
        worklist, project_root=project_root, config=config
    )
    expected_keys = set(plan[["candidate_id", "region_id"]]
                        .astype(str).itertuples(index=False, name=None))
    observed_keys = set()
    if {"candidate_id", "region_id"} <= set(metrics.columns):
        observed_keys = set(metrics[["candidate_id", "region_id"]]
                            .astype(str).itertuples(index=False, name=None))
    ok = metrics["status"].astype(str).eq("ok") if "status" in metrics else pd.Series(
        False, index=metrics.index
    )
    numeric = ["damaged_value", "restored_value", "improvement_value"]
    finite_failures = negative_distances = arithmetic_failures = runtime_failures = 0
    if set(numeric) <= set(metrics.columns):
        values = metrics.loc[ok, numeric].to_numpy(dtype=float)
        finite_failures = int((~np.isfinite(values)).sum())
        policy = _settings(config)["finite_value_policy"]
        distance_values = metrics.loc[ok, ["damaged_value", "restored_value"]].to_numpy(float)
        negative_distances = int((distance_values < float(
            policy["materially_negative_distance_threshold"]
        )).sum())
        expected_improvement = (
            metrics.loc[ok, "damaged_value"].astype(float)
            - metrics.loc[ok, "restored_value"].astype(float)
        )
        arithmetic_failures = int((np.abs(
            expected_improvement - metrics.loc[ok, "improvement_value"].astype(float)
        ) > float(policy["improvement_tolerance"])).sum())
    if "metric_runtime_seconds" in metrics:
        runtimes = metrics.loc[ok, "metric_runtime_seconds"].astype(float).to_numpy()
        runtime_failures = int(((~np.isfinite(runtimes)) | (runtimes < 0)).sum())

    zero_ids = set(worklist.loc[
        worklist["is_zero_control"].astype(bool), "candidate_id"
    ].astype(str))
    zero = metrics.loc[metrics["candidate_id"].astype(str).isin(zero_ids)]
    zero_value_failures = 0
    if not zero.empty:
        zero_values = zero[numeric].to_numpy(float)
        zero_value_failures = int((np.abs(zero_values) > float(
            _settings(config)["finite_value_policy"]["zero_control_tolerance"]
        )).sum())
    zero_bbox_rows = int(zero["region_id"].astype(str).eq("mask_bbox_crop").sum())
    invalid_region_rows = int((~metrics["region_id"].astype(str)
                               .isin(LPIPS_ACTIVE_REGIONS)).sum())
    error_rows = int(metrics["status"].astype(str).eq("error").sum())
    passed = bool(
        schema.passed and not (expected_keys - observed_keys)
        and not (observed_keys - expected_keys) and len(metrics) == len(plan)
        and finite_failures == 0 and negative_distances == 0
        and arithmetic_failures == 0 and runtime_failures == 0
        and zero_value_failures == 0 and zero_bbox_rows == 0
        and invalid_region_rows == 0 and error_rows == 0
    )
    return {
        "schema": schema.to_dict(),
        "row_count": len(metrics),
        "expected_row_count": len(plan),
        "row_count_valid": len(metrics) == len(plan),
        "missing_key_count": len(expected_keys - observed_keys),
        "unexpected_key_count": len(observed_keys - expected_keys),
        "error_row_count": error_rows,
        "non_finite_ok_value_count": finite_failures,
        "materially_negative_distance_count": negative_distances,
        "improvement_arithmetic_failure_count": arithmetic_failures,
        "runtime_failure_count": runtime_failures,
        "zero_control_value_failure_count": zero_value_failures,
        "zero_control_bbox_row_count": zero_bbox_rows,
        "invalid_region_row_count": invalid_region_rows,
        "passed": passed,
    }


def write_lpips_checkpoint(
    metrics: pd.DataFrame, path: str | Path, *, retries: int = 5,
    retry_delay_seconds: float = 0.25,
) -> dict[str, Any]:
    """Write with unique temp names and a recoverable Windows-lock fallback."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".{target.name}.{uuid.uuid4().hex}.tmp"
    metrics.loc[:, LPIPS_METRICS_COLUMNS].to_csv(temporary, index=False)
    last_error = ""
    for attempt in range(1, int(retries) + 1):
        try:
            os.replace(temporary, target)
            return {
                "status": "canonical", "path": target.as_posix(),
                "row_count": len(metrics), "attempts": attempt, "issue": "",
            }
        except PermissionError as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < int(retries):
                time.sleep(float(retry_delay_seconds))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    recovery = target.with_name(f"{target.stem}.recovery-{stamp}{target.suffix}")
    os.replace(temporary, recovery)
    return {
        "status": "recovery", "path": recovery.as_posix(),
        "row_count": len(metrics), "attempts": int(retries), "issue": last_error,
    }


def find_latest_lpips_checkpoint(path: str | Path) -> Path | None:
    """Return the newest canonical or recovery checkpoint."""

    target = Path(path)
    candidates = [target] if target.is_file() else []
    candidates.extend(
        item for item in target.parent.glob(f"{target.stem}.recovery-*{target.suffix}")
        if item.is_file()
    )
    return max(candidates, key=lambda item: item.stat().st_mtime_ns) if candidates else None


def load_latest_lpips_checkpoint(
    path: str | Path,
) -> tuple[pd.DataFrame, Path | None]:
    """Load the newest checkpoint and preserve its explicit source path."""

    latest = find_latest_lpips_checkpoint(path)
    if latest is None:
        return pd.DataFrame(columns=LPIPS_METRICS_COLUMNS), None
    frame = pd.read_csv(latest)
    missing = sorted(set(LPIPS_METRICS_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Checkpoint {latest} is missing columns: {missing}")
    return frame.loc[:, LPIPS_METRICS_COLUMNS], latest
