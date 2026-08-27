"""Standardized long-form classical full-reference restoration metrics."""

from __future__ import annotations

import hashlib
import math
import time
from pathlib import Path
from typing import Callable, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml
from PIL import Image
from skimage.metrics import structural_similarity

from .regions import (
    Region,
    build_standard_regions,
    crop_array,
    effect_support_region,
    metric_region_is_valid,
    select_pixels,
)
from .schemas import (
    CLASSICAL_METRICS_COLUMNS,
    CLASSICAL_METRICS_SCHEMA,
    validate_dataframe,
)

METRIC_MODULE_NAME = "restoration_eval.metrics_classical"
METRIC_MODULE_VERSION = "3.0.0"
METRIC_VERSION = "classical_full_reference.v1"
SUPPORTED_METRICS = ("mse", "mae", "psnr", "ssim")
ProgressCallback = Callable[[str], None]
CheckpointCallback = Callable[[pd.DataFrame], None]


def load_classical_metrics_config(path: str | Path) -> dict:
    """Load and validate the shared evaluation-metric configuration."""

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Metric configuration must be a mapping")
    if payload.get("config_schema_version") != "evaluation_metrics_config.v1":
        raise ValueError("Unsupported evaluation metric configuration schema")
    classical = payload.get("classical_metrics")
    if not isinstance(classical, dict):
        raise ValueError("Configuration is missing classical_metrics")
    required = {"metric_version", "data_range", "metrics", "regions", "execution"}
    missing = sorted(required - set(classical))
    if missing:
        raise ValueError(f"classical_metrics is missing keys: {missing}")
    if classical["metric_version"] != METRIC_VERSION:
        raise ValueError("Configured metric_version disagrees with the helper")
    regions = classical["regions"]
    if int(regions["outside_ring_inner_offset_pixels"]) != int(
        regions["boundary_width_pixels"]
    ):
        raise ValueError(
            "The canonical region helper requires outside-ring inner offset "
            "to equal boundary_width_pixels"
        )
    metric_names = tuple(item.get("metric_name") for item in classical["metrics"])
    if metric_names != SUPPORTED_METRICS:
        raise ValueError(f"Metric order must be {SUPPORTED_METRICS}, found {metric_names}")
    if int(classical["execution"]["progress_interval_cases"]) <= 0:
        raise ValueError("progress_interval_cases must be positive")
    if int(classical["execution"]["checkpoint_interval_cases"]) <= 0:
        raise ValueError("checkpoint_interval_cases must be positive")
    return payload


def _classical(config: Mapping) -> Mapping:
    return config["classical_metrics"]


def _resolve(project_root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(project_root) / path


def load_rgb_array(path: str | Path) -> np.ndarray:
    """Load an image as RGB float64 in the native 0-255 range."""

    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.float64)


def load_mask_array(path: str | Path) -> np.ndarray:
    """Load a mask/effect image as an unsigned 8-bit intensity array."""

    with Image.open(path) as image:
        return np.asarray(image.convert("L"), dtype=np.uint8)


def _require_same_image_shape(*arrays: np.ndarray) -> None:
    shapes = {tuple(array.shape) for array in arrays}
    if len(shapes) != 1:
        raise ValueError(f"Image geometry mismatch: {sorted(shapes)}")
    shape = arrays[0].shape
    if len(shape) != 3 or shape[2] != 3:
        raise ValueError(f"Expected RGB image arrays, received {shape}")


def build_case_regions(
    case: Mapping,
    raw_mask: np.ndarray,
    config: Mapping,
) -> dict[str, Region]:
    """Build the configured non-patch region set using the canonical helper."""

    settings = _classical(config)["regions"]
    threshold = int(case["mask_threshold"])
    active_mask = np.asarray(raw_mask) >= threshold
    content_bbox = tuple(
        int(case[column])
        for column in ("content_x_min", "content_y_min", "content_x_max", "content_y_max")
    )
    regions = build_standard_regions(
        active_mask,
        content_bbox=content_bbox,
        mask_bbox_margin=int(settings["mask_bbox_margin_pixels"]),
        boundary_width_pixels=int(settings["boundary_width_pixels"]),
        include_outside_boundary=True,
        outside_boundary_width_pixels=int(settings["outside_ring_outer_width_pixels"]),
    )
    if str(case["experiment_id"]) == "synthetic_degradation":
        regions["degradation_support"] = effect_support_region(
            raw_mask,
            support_threshold=float(settings["effect_support_threshold"]),
        )
    ordered: dict[str, Region] = {}
    for region_id in settings["region_order"]:
        if region_id in regions:
            ordered[region_id] = regions[region_id]
    return ordered


def build_metric_plan(
    regions: Mapping[str, Region],
    config: Mapping,
) -> list[tuple[str, str, Region, str]]:
    """Return valid (family, metric, region, improvement direction) tuples."""

    classical = _classical(config)
    allowed_by_family = classical["regions"]["compatible_regions"]
    plan: list[tuple[str, str, Region, str]] = []
    for definition in classical["metrics"]:
        metric_name = str(definition["metric_name"])
        metric_family = str(definition["metric_family"])
        direction = str(definition["improvement_direction"])
        for region_id in allowed_by_family[metric_family]:
            region = regions.get(region_id)
            if region is None:
                continue
            valid, _ = metric_region_is_valid(metric_name, region)
            if valid:
                plan.append((metric_family, metric_name, region, direction))
    return plan


def _region_values(array: np.ndarray, region: Region) -> np.ndarray:
    if region.spatial_support == "rectangle":
        return crop_array(array, region)
    return select_pixels(array, region)


def compute_metric_value(
    reference: np.ndarray,
    candidate: np.ndarray,
    metric_name: str,
    region: Region,
    *,
    data_range: float = 255.0,
) -> float:
    """Compute one valid full-reference metric on one canonical region."""

    valid, reason = metric_region_is_valid(metric_name, region)
    if not valid:
        raise ValueError(f"Invalid metric-region pair {metric_name}/{region.region_id}: {reason}")
    reference_values = _region_values(reference, region)
    candidate_values = _region_values(candidate, region)
    if reference_values.shape != candidate_values.shape:
        raise ValueError("Reference and candidate region shapes differ")
    metric = str(metric_name).lower()
    if metric == "ssim":
        return float(structural_similarity(
            reference_values, candidate_values,
            channel_axis=-1, data_range=float(data_range),
        ))
    difference = reference_values.astype(np.float64) - candidate_values.astype(np.float64)
    if metric == "mse":
        return float(np.mean(np.square(difference), dtype=np.float64))
    if metric == "mae":
        return float(np.mean(np.abs(difference), dtype=np.float64))
    if metric == "psnr":
        mse = float(np.mean(np.square(difference), dtype=np.float64))
        return math.inf if mse == 0.0 else float(10.0 * math.log10(data_range ** 2 / mse))
    raise ValueError(f"Unsupported metric: {metric_name}")


def compute_improvement(
    damaged_value: float,
    restored_value: float,
    direction: str,
) -> float:
    """Compute direction-aware improvement while preserving explicit infinities."""

    damaged = float(damaged_value)
    restored = float(restored_value)
    if math.isnan(damaged) or math.isnan(restored):
        return math.nan
    if math.isinf(damaged) and math.isinf(restored) and damaged == restored:
        return 0.0
    if direction == "damaged_minus_restored":
        return damaged - restored
    if direction == "restored_minus_damaged":
        return restored - damaged
    raise ValueError(f"Unsupported improvement direction: {direction}")


def metric_row_id(
    case_id: str,
    candidate_id: str,
    metric_family: str,
    metric_name: str,
    region_id: str,
    metric_version: str = METRIC_VERSION,
) -> str:
    """Return a deterministic compact identifier for one metric evidence row."""

    payload = "|".join((case_id, candidate_id, metric_family, metric_name,
                        region_id, metric_version))
    return f"cm__{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20]}"


def _safe_metric(
    clean: np.ndarray,
    candidate: np.ndarray,
    metric_name: str,
    region: Region,
    data_range: float,
) -> tuple[float, str]:
    try:
        return compute_metric_value(clean, candidate, metric_name, region,
                                    data_range=data_range), ""
    except Exception as exc:  # retained as explicit evidence rows
        return math.nan, f"{type(exc).__name__}: {exc}"


def compute_case_classical_metrics(
    case_candidates: pd.DataFrame,
    *,
    project_root: str | Path,
    config: Mapping,
) -> pd.DataFrame:
    """Compute all configured metric rows for every candidate of one case."""

    if case_candidates.empty:
        return pd.DataFrame(columns=CLASSICAL_METRICS_COLUMNS)
    if case_candidates["case_id"].nunique() != 1:
        raise ValueError("compute_case_classical_metrics accepts exactly one case_id")
    case = case_candidates.iloc[0]
    root = Path(project_root)
    clean = load_rgb_array(_resolve(root, case["clean_image_path"]))
    damaged = load_rgb_array(_resolve(root, case["input_image_path"]))
    raw_mask = load_mask_array(_resolve(root, case["mask_or_effect_path"]))
    _require_same_image_shape(clean, damaged)
    if raw_mask.shape != clean.shape[:2]:
        raise ValueError(f"Mask/image geometry mismatch: {raw_mask.shape} vs {clean.shape[:2]}")
    regions = build_case_regions(case, raw_mask, config)
    plan = build_metric_plan(regions, config)
    data_range = float(_classical(config)["data_range"])
    metric_version = str(_classical(config)["metric_version"])
    region_policy_version = str(_classical(config)["regions"]["policy_version"])
    damaged_cache = {
        (metric, region.region_id): _safe_metric(
            clean, damaged, metric, region, data_range
        )
        for _, metric, region, _ in plan
    }

    records: list[dict[str, object]] = []
    for candidate in case_candidates.itertuples(index=False):
        try:
            restored = load_rgb_array(_resolve(root, candidate.restored_path))
            _require_same_image_shape(clean, restored)
            load_issue = ""
        except Exception as exc:
            restored = None
            load_issue = f"{type(exc).__name__}: {exc}"
        for family, metric, region, direction in plan:
            damaged_value, damaged_issue = damaged_cache[(metric, region.region_id)]
            if restored is None:
                restored_value, restored_issue = math.nan, load_issue
            else:
                restored_value, restored_issue = _safe_metric(
                    clean, restored, metric, region, data_range
                )
            issues = "; ".join(item for item in (damaged_issue, restored_issue) if item)
            improvement = compute_improvement(damaged_value, restored_value, direction)
            records.append({
                "metric_row_id": metric_row_id(
                    str(candidate.case_id), str(candidate.candidate_id), family,
                    metric, region.region_id, metric_version,
                ),
                "case_id": str(candidate.case_id),
                "candidate_id": str(candidate.candidate_id),
                "model_id": str(candidate.model_id),
                "metric_family": family,
                "metric_name": metric,
                "region_id": region.region_id,
                "region_pixel_count": int(region.pixel_count),
                "damaged_value": damaged_value,
                "restored_value": restored_value,
                "improvement_value": improvement,
                "improvement_direction": direction,
                "metric_version": metric_version,
                "region_policy_version": region_policy_version,
                "status": "error" if issues else "ok",
                "issue": issues,
            })
    return pd.DataFrame(records, columns=CLASSICAL_METRICS_COLUMNS)


def expected_metric_row_count(
    worklist: pd.DataFrame,
    *,
    project_root: str | Path,
    config: Mapping,
) -> int:
    """Calculate the exact valid metric-region cardinality without restorations."""

    total = 0
    root = Path(project_root)
    for _, group in worklist.groupby("case_id", sort=False):
        case = group.iloc[0]
        raw_mask = load_mask_array(_resolve(root, case["mask_or_effect_path"]))
        regions = build_case_regions(case, raw_mask, config)
        total += len(group) * len(build_metric_plan(regions, config))
    return int(total)


def run_classical_metrics(
    worklist: pd.DataFrame,
    *,
    project_root: str | Path,
    config: Mapping,
    prior_metrics: pd.DataFrame | None = None,
    progress_callback: ProgressCallback | None = None,
    checkpoint_callback: CheckpointCallback | None = None,
) -> pd.DataFrame:
    """Compute every case with deterministic progress and optional checkpoints."""

    groups = list(worklist.groupby("case_id", sort=False))
    total_cases = len(groups)
    interval = int(_classical(config)["execution"]["progress_interval_cases"])
    checkpoint_interval = int(_classical(config)["execution"]["checkpoint_interval_cases"])
    frames: list[pd.DataFrame] = []
    prior = (prior_metrics.copy() if prior_metrics is not None
             else pd.DataFrame(columns=CLASSICAL_METRICS_COLUMNS))
    started = time.perf_counter()
    reused_cases = 0
    completed_candidates = 0

    for number, (case_id, group) in enumerate(groups, start=1):
        existing = prior.loc[prior.get("case_id", pd.Series(dtype=str)).astype(str).eq(str(case_id))]
        use_existing = False
        if not existing.empty and existing["status"].astype(str).eq("ok").all():
            root = Path(project_root)
            raw_mask = load_mask_array(_resolve(root, group.iloc[0]["mask_or_effect_path"]))
            plan = build_metric_plan(build_case_regions(group.iloc[0], raw_mask, config), config)
            expected = {
                (str(candidate), metric, region.region_id)
                for candidate in group["candidate_id"]
                for _, metric, region, _ in plan
            }
            observed = set(existing[["candidate_id", "metric_name", "region_id"]]
                           .astype(str).itertuples(index=False, name=None))
            use_existing = expected == observed
        if use_existing:
            result = existing.loc[:, CLASSICAL_METRICS_COLUMNS].copy()
            reused_cases += 1
        else:
            result = compute_case_classical_metrics(
                group, project_root=project_root, config=config
            )
        frames.append(result)
        completed_candidates += len(group)
        should_report = number % interval == 0 or number == total_cases
        should_checkpoint = number % checkpoint_interval == 0 or number == total_cases
        if should_checkpoint and checkpoint_callback is not None:
            checkpoint_callback(pd.concat(frames, ignore_index=True))
        if should_report and progress_callback is not None:
            elapsed = time.perf_counter() - started
            progress_callback(
                f"Classical metrics: {number}/{total_cases} cases "
                f"({100.0 * number / max(total_cases, 1):.1f}%), "
                f"{completed_candidates}/{len(worklist)} candidates, "
                f"elapsed={elapsed:.1f}s, throughput={number / max(elapsed, 1e-9):.3f} "
                f"cases/s, latest={case_id}, reused_cases={reused_cases}"
            )
    return pd.concat(frames, ignore_index=True).loc[:, CLASSICAL_METRICS_COLUMNS]


def validate_classical_metrics(
    metrics: pd.DataFrame,
    worklist: pd.DataFrame,
    *,
    expected_rows: int | None = None,
) -> dict[str, object]:
    """Validate schema, coverage, cardinality, missingness, and SSIM policy."""

    schema = validate_dataframe(metrics, CLASSICAL_METRICS_SCHEMA,
                                allow_extra_columns=False)
    candidates = set(worklist["candidate_id"].astype(str))
    observed_candidates = set(metrics["candidate_id"].astype(str)) if "candidate_id" in metrics else set()
    ok_rows = metrics["status"].astype(str).eq("ok") if "status" in metrics else pd.Series(False, index=metrics.index)
    numeric_columns = ["damaged_value", "restored_value", "improvement_value"]
    unexpected_missing = int(metrics.loc[ok_rows, numeric_columns].isna().sum().sum())
    invalid_ssim = int((
        metrics["metric_name"].astype(str).eq("ssim")
        & ~metrics["region_id"].astype(str).isin(
            {"full_image", "content_region", "mask_bbox_crop"}
        )
    ).sum())
    row_count_valid = expected_rows is None or len(metrics) == int(expected_rows)
    passed = (schema.passed and row_count_valid and not (candidates - observed_candidates)
              and not (observed_candidates - candidates) and unexpected_missing == 0
              and invalid_ssim == 0)
    return {
        "schema": schema.to_dict(),
        "row_count": int(len(metrics)),
        "expected_row_count": expected_rows,
        "row_count_valid": row_count_valid,
        "missing_candidate_count": len(candidates - observed_candidates),
        "unexpected_candidate_count": len(observed_candidates - candidates),
        "error_row_count": int(metrics["status"].astype(str).eq("error").sum()),
        "unexpected_missing_value_count": unexpected_missing,
        "invalid_ssim_region_rows": invalid_ssim,
        "positive_infinity_count": int(np.isposinf(metrics[numeric_columns].to_numpy()).sum()),
        "negative_infinity_count": int(np.isneginf(metrics[numeric_columns].to_numpy()).sum()),
        "passed": bool(passed),
    }
