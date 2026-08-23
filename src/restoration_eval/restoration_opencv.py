"""Deterministic OpenCV Telea restoration for normalized experiment cases."""

from __future__ import annotations

import os
import platform
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Mapping

import cv2
import numpy as np
import pandas as pd
import yaml
from PIL import Image

from .schemas import (
    CASE_REGISTRY_SCHEMA,
    MODEL_ELIGIBILITY_SCHEMA,
    RESTORATION_RUNTIME_SUMMARY_COLUMNS,
    RESTORATION_RUNTIME_SUMMARY_SCHEMA,
    RESTORATIONS_COLUMNS,
    RESTORATIONS_SCHEMA,
    validate_dataframe,
)


DEFAULT_OPENCV_MODEL_NAME = "opencv_telea"
DEFAULT_TELEA_RADIUS = 3
RESTORATION_GENERATOR_NAME = "restoration_eval.restoration_opencv"
RESTORATION_GENERATOR_VERSION = "3.0.0"
OPENCV_TELEA_CONFIG_SCHEMA_VERSION = "opencv_telea_config.v1"
RESTORATIONS_SCHEMA_VERSION = RESTORATIONS_SCHEMA.version
RUNTIME_SUMMARY_SCHEMA_VERSION = RESTORATION_RUNTIME_SUMMARY_SCHEMA.version

ProgressCallback = Callable[[str], None]
CheckpointCallback = Callable[[pd.DataFrame], None]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def calculate_file_sha256(file_path: str | Path) -> str:
    """Return a complete SHA-256 checksum for one file."""
    digest = sha256()
    with Path(file_path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_mapping_keys(
    mapping: Mapping[str, Any],
    keys: set[str],
    *,
    label: str,
) -> None:
    missing = sorted(keys - set(mapping))
    if missing:
        raise ValueError(f"{label} is missing required keys: {missing}")


def load_opencv_telea_config(path: str | Path) -> dict[str, Any]:
    """Load and validate the versioned Notebook 09 configuration."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("OpenCV Telea configuration must be a mapping.")

    _require_mapping_keys(
        payload,
        {
            "config_schema_version",
            "config_version",
            "dataset",
            "inputs",
            "output",
            "model",
            "execution",
            "expected",
            "smoke",
            "representative_case_ids",
            "schema_versions",
            "known_limitations",
        },
        label="OpenCV Telea configuration",
    )
    if payload["config_schema_version"] != OPENCV_TELEA_CONFIG_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported OpenCV Telea configuration schema: "
            f"{payload['config_schema_version']!r}"
        )

    model = payload["model"]
    execution = payload["execution"]
    expected = payload["expected"]
    _require_mapping_keys(
        model,
        {
            "model_id",
            "configuration_id",
            "algorithm",
            "inpaint_radius",
            "device",
            "precision",
            "execution_backend",
            "retry_count",
            "deterministic",
            "zero_control_policy",
            "mask_threshold_policy",
        },
        label="model configuration",
    )
    _require_mapping_keys(
        execution,
        {
            "progress_interval_cases",
            "compute_checksums",
            "resume_enabled",
            "overwrite_existing",
            "target_width",
            "target_height",
            "output_mode",
            "output_format",
            "png_compress_level",
        },
        label="execution configuration",
    )
    if str(model["model_id"]) != DEFAULT_OPENCV_MODEL_NAME:
        raise ValueError("Notebook 09 configuration must target opencv_telea.")
    if str(model["algorithm"]) != "cv2.INPAINT_TELEA":
        raise ValueError("Notebook 09 must use cv2.INPAINT_TELEA.")
    if int(model["inpaint_radius"]) <= 0:
        raise ValueError("Telea inpaint radius must be positive.")
    if int(model["retry_count"]) != 0:
        raise ValueError("The deterministic Telea baseline does not retry cases.")
    if model["zero_control_policy"] != "identity_noop":
        raise ValueError("Zero controls must use the identity_noop policy.")
    if int(execution["progress_interval_cases"]) <= 0:
        raise ValueError("Progress interval must be positive.")
    if int(expected["eligible_case_count"]) <= 0:
        raise ValueError("Expected eligible case count must be positive.")

    thresholds = model["mask_threshold_policy"]
    for policy_name in ("binary_missing_region", "synthetic_degradation"):
        if policy_name not in thresholds:
            raise ValueError(f"Missing mask threshold policy: {policy_name}")
        policy = thresholds[policy_name]
        if policy.get("comparison") != "greater_than_or_equal":
            raise ValueError(
                f"Mask threshold policy {policy_name!r} must use >= comparison."
            )
        threshold = int(policy.get("threshold", -1))
        if not 0 <= threshold <= 255:
            raise ValueError(f"Invalid mask threshold for {policy_name}: {threshold}")
    return payload


def _coerce_eligibility(values: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(values):
        return values.astype(bool)
    normalized = values.astype(str).str.strip().str.lower()
    invalid = ~normalized.isin({"true", "false"})
    if invalid.any():
        bad = sorted(normalized.loc[invalid].unique().tolist())
        raise ValueError(f"Eligibility contains non-boolean values: {bad}")
    return normalized.eq("true")


def build_eligible_case_worklist(
    case_registry: pd.DataFrame,
    model_eligibility: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Return the exact normalized worklist approved for OpenCV Telea."""
    case_result = validate_dataframe(
        case_registry,
        CASE_REGISTRY_SCHEMA,
        allow_extra_columns=False,
    )
    eligibility_result = validate_dataframe(
        model_eligibility,
        MODEL_ELIGIBILITY_SCHEMA,
        allow_extra_columns=False,
    )
    if not case_result.passed:
        raise ValueError(f"Case registry violates schema: {case_result.to_dict()}")
    if not eligibility_result.passed:
        raise ValueError(
            "Model eligibility violates schema: "
            f"{eligibility_result.to_dict()}"
        )

    model_id = str(config["model"]["model_id"])
    eligibility = model_eligibility.loc[
        model_eligibility["model_id"].astype(str).eq(model_id)
    ].copy()
    if eligibility.empty:
        raise ValueError(f"No model-eligibility rows found for {model_id!r}.")
    eligibility["eligible"] = _coerce_eligibility(eligibility["eligible"])
    eligibility = eligibility.loc[eligibility["eligible"]].copy()

    worklist = case_registry.merge(
        eligibility,
        on="case_id",
        how="inner",
        validate="one_to_one",
    )
    worklist = worklist.sort_values(
        ["experiment_id", "case_id"],
        kind="stable",
    ).reset_index(drop=True)

    expected_count = int(config["expected"]["eligible_case_count"])
    if len(worklist) != expected_count:
        raise ValueError(
            f"Eligible worklist has {len(worklist)} rows; expected {expected_count}."
        )
    if worklist["case_id"].duplicated().any():
        raise ValueError("Eligible worklist contains duplicate case IDs.")
    if not worklist["status"].astype(str).eq("passed").all():
        raise ValueError("Eligible worklist contains non-passed cases.")

    observed_by_experiment = {
        str(key): int(value)
        for key, value in worklist.groupby("experiment_id").size().items()
    }
    expected_by_experiment = {
        str(key): int(value)
        for key, value in config["expected"][
            "eligible_case_count_by_experiment"
        ].items()
    }
    if observed_by_experiment != expected_by_experiment:
        raise ValueError(
            "Eligible experiment counts differ from configuration: "
            f"observed={observed_by_experiment}, expected={expected_by_experiment}"
        )
    return worklist


def resolve_project_path(path_value: str | Path, project_root: str | Path) -> Path:
    path = Path(str(path_value))
    if not path.is_absolute():
        path = Path(project_root) / path
    return path.resolve()


def to_project_relative(path_value: str | Path, project_root: str | Path) -> str:
    path = resolve_project_path(path_value, project_root)
    root = Path(project_root).resolve()
    try:
        return path.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"Path is outside the repository: {path}") from exc


def threshold_policy_for_case(
    case: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    policy_name = (
        "synthetic_degradation"
        if str(case["experiment_id"]) == "synthetic_degradation"
        else "binary_missing_region"
    )
    policy = dict(config["model"]["mask_threshold_policy"][policy_name])
    policy["policy_name"] = policy_name
    return policy


def binarize_restoration_mask(mask_gray: np.ndarray, threshold: int) -> np.ndarray:
    """Convert a grayscale source mask using the approved inclusive threshold."""
    if mask_gray.ndim != 2:
        raise ValueError(f"Expected a 2-D grayscale mask; received {mask_gray.shape}.")
    if not 0 <= int(threshold) <= 255:
        raise ValueError(f"Mask threshold must be in [0, 255]: {threshold}")
    return np.where(mask_gray >= int(threshold), 255, 0).astype(np.uint8)


def restore_array_with_opencv_telea(
    damaged_bgr: np.ndarray,
    mask_binary: np.ndarray,
    *,
    radius: int = DEFAULT_TELEA_RADIUS,
) -> tuple[np.ndarray, str]:
    """Restore one array, explicitly preserving empty-mask zero controls."""
    if damaged_bgr.ndim != 3 or damaged_bgr.shape[2] != 3:
        raise ValueError(f"Expected BGR image with three channels: {damaged_bgr.shape}")
    if mask_binary.shape != damaged_bgr.shape[:2]:
        raise ValueError(
            "Image and mask dimensions differ: "
            f"image={damaged_bgr.shape[:2]}, mask={mask_binary.shape}"
        )
    if int(radius) <= 0:
        raise ValueError("Telea inpaint radius must be positive.")
    if not np.any(mask_binary):
        return damaged_bgr.copy(), "identity_noop"
    restored = cv2.inpaint(
        damaged_bgr,
        mask_binary,
        inpaintRadius=float(radius),
        flags=cv2.INPAINT_TELEA,
    )
    return restored, "telea_inpaint"


def _output_path_for_case(
    case: Mapping[str, Any],
    restored_root: str | Path,
) -> Path:
    return (
        Path(restored_root)
        / str(case["experiment_id"])
        / f"{case['case_id']}.png"
    )


def _identifiers(case_id: str, model_id: str) -> tuple[str, str]:
    restoration_id = f"restoration__{model_id}__{case_id}"
    candidate_id = f"candidate__{model_id}__{case_id}__c00"
    return restoration_id, candidate_id


def _cpu_environment() -> str:
    processor = platform.processor() or "unknown"
    return f"{platform.platform()} | {platform.machine()} | {processor}"


def _resume_record_is_valid(
    record: Mapping[str, Any],
    *,
    output_path: Path,
    input_sha256: str,
    mask_sha256: str,
    config: Mapping[str, Any],
) -> bool:
    if str(record.get("status")) != "completed" or not output_path.is_file():
        return False
    expected = {
        "model_id": str(config["model"]["model_id"]),
        "configuration_id": str(config["model"]["configuration_id"]),
        "opencv_version": cv2.__version__,
        "generator_version": RESTORATION_GENERATOR_VERSION,
        "input_sha256": input_sha256,
        "mask_sha256": mask_sha256,
    }
    if any(str(record.get(key, "")) != value for key, value in expected.items()):
        return False
    expected_output_hash = str(record.get("restored_sha256", ""))
    return bool(expected_output_hash) and (
        calculate_file_sha256(output_path) == expected_output_hash
    )


def run_opencv_telea_case(
    case: Mapping[str, Any],
    *,
    restored_root: str | Path,
    project_root: str | Path,
    config: Mapping[str, Any],
    resume_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute one case and return normalized evidence even on failure."""
    model = config["model"]
    execution = config["execution"]
    model_id = str(model["model_id"])
    case_id = str(case["case_id"])
    restoration_id, candidate_id = _identifiers(case_id, model_id)
    output_path = _output_path_for_case(case, restored_root).resolve()
    root = Path(project_root).resolve()
    restored_root_path = Path(restored_root).resolve()
    try:
        output_path.relative_to(restored_root_path)
    except ValueError as exc:
        raise ValueError(f"Restoration output escapes restored root: {output_path}") from exc

    input_path = resolve_project_path(case["input_image_path"], root)
    mask_path = resolve_project_path(case["mask_or_effect_path"], root)
    threshold = int(threshold_policy_for_case(case, config)["threshold"])
    started_at = utc_now_iso()
    timer = perf_counter()
    input_hash = ""
    mask_hash = ""
    restored_hash = ""
    action = "failed"
    status = "failed"
    issue = ""

    try:
        input_hash = calculate_file_sha256(input_path)
        mask_hash = calculate_file_sha256(mask_path)
        if (
            bool(execution["resume_enabled"])
            and resume_record is not None
            and _resume_record_is_valid(
                resume_record,
                output_path=output_path,
                input_sha256=input_hash,
                mask_sha256=mask_hash,
                config=config,
            )
        ):
            reused = dict(resume_record)
            reused["execution_action"] = "reused_validated"
            reused["restored_path"] = to_project_relative(output_path, root)
            return {column: reused.get(column, "") for column in RESTORATIONS_COLUMNS}

        if output_path.exists() and not bool(execution["overwrite_existing"]):
            raise FileExistsError(
                "Existing output cannot be reused without matching checkpoint evidence: "
                f"{output_path}"
            )

        damaged_bgr = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
        mask_gray = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if damaged_bgr is None:
            raise FileNotFoundError(f"Could not read input image: {input_path}")
        if mask_gray is None:
            raise FileNotFoundError(f"Could not read mask: {mask_path}")
        target_shape = (
            int(execution["target_height"]),
            int(execution["target_width"]),
        )
        if damaged_bgr.shape[:2] != target_shape or mask_gray.shape != target_shape:
            raise ValueError(
                "Unexpected image dimensions: "
                f"input={damaged_bgr.shape[:2]}, mask={mask_gray.shape}, "
                f"expected={target_shape}"
            )

        mask_binary = binarize_restoration_mask(mask_gray, threshold)
        restored_bgr, action = restore_array_with_opencv_telea(
            damaged_bgr,
            mask_binary,
            radius=int(model["inpaint_radius"]),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(".tmp.png")
        try:
            written = cv2.imwrite(
                str(temporary_path),
                restored_bgr,
                [cv2.IMWRITE_PNG_COMPRESSION, int(execution["png_compress_level"])],
            )
            if not written:
                raise OSError(f"OpenCV could not write restoration: {temporary_path}")
            os.replace(temporary_path, output_path)
        finally:
            temporary_path.unlink(missing_ok=True)
        restored_hash = calculate_file_sha256(output_path)
        status = "completed"
    except Exception as exc:  # Failure evidence is part of the experiment contract.
        issue = f"{type(exc).__name__}: {exc}"

    runtime_seconds = perf_counter() - timer
    completed_at = utc_now_iso()
    return {
        "restoration_id": restoration_id,
        "case_id": case_id,
        "model_id": model_id,
        "candidate_id": candidate_id,
        "candidate_index": 0,
        "seed": "",
        "prompt_policy_id": "",
        "model_version": f"opencv-{cv2.__version__}",
        "opencv_version": cv2.__version__,
        "configuration_id": str(model["configuration_id"]),
        "algorithm": str(model["algorithm"]),
        "inpaint_radius": int(model["inpaint_radius"]),
        "mask_threshold": threshold,
        "execution_action": action,
        "restored_path": to_project_relative(output_path, root),
        "input_sha256": input_hash,
        "mask_sha256": mask_hash,
        "restored_sha256": restored_hash,
        "runtime_seconds": float(runtime_seconds),
        "device": str(model["device"]),
        "precision": str(model["precision"]),
        "execution_backend": str(model["execution_backend"]),
        "cpu_environment": _cpu_environment(),
        "retry_count": int(model["retry_count"]),
        "generator_name": RESTORATION_GENERATOR_NAME,
        "generator_version": RESTORATION_GENERATOR_VERSION,
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "status": status,
        "issue": issue,
    }


def _resume_lookup(records: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if records is None or records.empty:
        return {}
    if "case_id" not in records.columns:
        raise ValueError("Resume records are missing case_id.")
    if records["case_id"].duplicated().any():
        raise ValueError("Resume records contain duplicate case IDs.")
    return {
        str(row["case_id"]): row.to_dict()
        for _, row in records.iterrows()
    }


def run_opencv_telea_cases(
    worklist: pd.DataFrame,
    *,
    restored_root: str | Path,
    project_root: str | Path,
    config: Mapping[str, Any],
    resume_records: pd.DataFrame | None = None,
    progress_callback: ProgressCallback | None = print,
    checkpoint_callback: CheckpointCallback | None = None,
) -> pd.DataFrame:
    """Execute every approved case with deterministic progress and checkpoints."""
    required = {
        "case_id",
        "experiment_id",
        "input_image_path",
        "mask_or_effect_path",
    }
    missing = sorted(required - set(worklist.columns))
    if missing:
        raise ValueError(f"Restoration worklist is missing columns: {missing}")
    if worklist["case_id"].duplicated().any():
        raise ValueError("Restoration worklist contains duplicate case IDs.")

    ordered = worklist.sort_values(
        ["experiment_id", "case_id"], kind="stable"
    ).reset_index(drop=True)
    resume_by_case = _resume_lookup(resume_records)
    interval = int(config["execution"]["progress_interval_cases"])
    total = len(ordered)
    records: list[dict[str, Any]] = []
    timer = perf_counter()

    for position, (_, case) in enumerate(ordered.iterrows(), start=1):
        case_id = str(case["case_id"])
        record = run_opencv_telea_case(
            case.to_dict(),
            restored_root=restored_root,
            project_root=project_root,
            config=config,
            resume_record=resume_by_case.get(case_id),
        )
        records.append(record)
        should_report = position % interval == 0 or position == total
        if should_report:
            frame = pd.DataFrame(records, columns=RESTORATIONS_COLUMNS)
            if checkpoint_callback is not None:
                checkpoint_callback(frame.copy())
            if progress_callback is not None:
                elapsed = max(perf_counter() - timer, 1e-12)
                progress_callback(
                    f"Completed {position}/{total} ({position / total:.1%}) | "
                    f"elapsed={elapsed:.1f}s | throughput={position / elapsed:.2f} "
                    f"cases/s | latest={case_id}"
                )
    return pd.DataFrame(records, columns=RESTORATIONS_COLUMNS)


def validate_restoration_records(records: pd.DataFrame) -> None:
    result = validate_dataframe(records, RESTORATIONS_SCHEMA, allow_extra_columns=False)
    if not result.passed:
        raise ValueError(f"Restoration records violate schema: {result.to_dict()}")


def validate_restoration_outputs(
    records: pd.DataFrame,
    worklist: pd.DataFrame,
    *,
    project_root: str | Path,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Reload every output and evaluate file and spatial invariants."""
    joined = records.merge(
        worklist[
            ["case_id", "experiment_id", "input_image_path", "mask_or_effect_path"]
        ],
        on="case_id",
        how="left",
        validate="one_to_one",
    )
    rows: list[dict[str, Any]] = []
    expected_size = (
        int(config["execution"]["target_width"]),
        int(config["execution"]["target_height"]),
    )
    root = Path(project_root).resolve()

    for _, row in joined.iterrows():
        issues: list[str] = []
        output_path = resolve_project_path(row["restored_path"], root)
        input_path = resolve_project_path(row["input_image_path"], root)
        mask_path = resolve_project_path(row["mask_or_effect_path"], root)
        readable = False
        width: int | None = None
        height: int | None = None
        mode = ""
        image_format = ""
        checksum_matches = False
        mask_pixels: int | None = None
        changed_inside: int | None = None
        changed_outside: int | None = None
        zero_control_valid: bool | None = None
        inside_change_valid: bool | None = None
        outside_invariance_valid: bool | None = None

        if str(row["status"]) != "completed":
            issues.append("generation_status_failed")
        try:
            with Image.open(output_path) as image:
                image.load()
                readable = True
                width, height = image.size
                mode = image.mode
                image_format = str(image.format)
                restored_rgb = np.asarray(image.convert("RGB"))
            if (width, height) != expected_size:
                issues.append("unexpected_dimensions")
            if mode != str(config["execution"]["output_mode"]):
                issues.append("unexpected_mode")
            if image_format != str(config["execution"]["output_format"]):
                issues.append("unexpected_format")
            checksum_matches = (
                calculate_file_sha256(output_path) == str(row["restored_sha256"])
            )
            if not checksum_matches:
                issues.append("restored_checksum_mismatch")

            with Image.open(input_path) as image:
                input_rgb = np.asarray(image.convert("RGB"))
            with Image.open(mask_path) as image:
                mask_gray = np.asarray(image.convert("L"))
            threshold = int(threshold_policy_for_case(row.to_dict(), config)["threshold"])
            mask = mask_gray >= threshold
            changed = np.any(input_rgb != restored_rgb, axis=2)
            mask_pixels = int(mask.sum())
            changed_inside = int(np.logical_and(changed, mask).sum())
            changed_outside = int(np.logical_and(changed, ~mask).sum())
            outside_invariance_valid = changed_outside == 0
            if not outside_invariance_valid:
                issues.append("outside_mask_changed")
            if mask_pixels == 0:
                zero_control_valid = bool(np.array_equal(input_rgb, restored_rgb))
                inside_change_valid = True
                if not zero_control_valid:
                    issues.append("zero_control_not_identity")
            else:
                zero_control_valid = True
                inside_change_valid = changed_inside > 0
                if not inside_change_valid:
                    issues.append("nonempty_mask_did_not_change")
        except Exception as exc:
            issues.append(f"{type(exc).__name__}: {exc}")

        rows.append(
            {
                "restoration_id": row["restoration_id"],
                "case_id": row["case_id"],
                "file_exists": output_path.is_file(),
                "readable": readable,
                "width": width,
                "height": height,
                "mode": mode,
                "format": image_format,
                "checksum_matches": checksum_matches,
                "mask_pixels": mask_pixels,
                "changed_inside_mask_pixels": changed_inside,
                "changed_outside_mask_pixels": changed_outside,
                "inside_change_valid": inside_change_valid,
                "outside_invariance_valid": outside_invariance_valid,
                "zero_control_valid": zero_control_valid,
                "validation_passed": not issues,
                "issue": "; ".join(issues),
            }
        )
    return pd.DataFrame(rows)


def summarize_restoration_runtime(
    records: pd.DataFrame,
    worklist: pd.DataFrame,
) -> pd.DataFrame:
    """Return one overall and one per-experiment runtime summary row."""
    joined = records[["case_id", "status", "runtime_seconds"]].merge(
        worklist[["case_id", "experiment_id"]],
        on="case_id",
        how="left",
        validate="one_to_one",
    )

    def summarize(frame: pd.DataFrame, scope: str, experiment_id: str) -> dict[str, Any]:
        runtime = pd.to_numeric(frame["runtime_seconds"], errors="raise")
        completed = int(frame["status"].astype(str).eq("completed").sum())
        failed = int(len(frame) - completed)
        total_runtime = float(runtime.sum())
        return {
            "summary_scope": scope,
            "experiment_id": experiment_id,
            "case_count": int(len(frame)),
            "completed_count": completed,
            "failed_count": failed,
            "total_runtime_seconds": total_runtime,
            "mean_runtime_seconds": float(runtime.mean()),
            "median_runtime_seconds": float(runtime.median()),
            "p95_runtime_seconds": float(runtime.quantile(0.95)),
            "max_runtime_seconds": float(runtime.max()),
            "throughput_cases_per_second": (
                float(len(frame) / total_runtime) if total_runtime > 0 else 0.0
            ),
            "status": "completed" if failed == 0 else "has_failures",
        }

    rows = [summarize(joined, "overall", "all")]
    for experiment_id, group in joined.groupby("experiment_id", sort=True):
        rows.append(summarize(group, "experiment", str(experiment_id)))
    summary = pd.DataFrame(rows, columns=RESTORATION_RUNTIME_SUMMARY_COLUMNS)
    result = validate_dataframe(
        summary,
        RESTORATION_RUNTIME_SUMMARY_SCHEMA,
        allow_extra_columns=False,
    )
    if not result.passed:
        raise ValueError(f"Runtime summary violates schema: {result.to_dict()}")
    return summary


def write_dataframe_atomic(dataframe: pd.DataFrame, path: str | Path) -> Path:
    """Write a CSV through a temporary sibling file."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    try:
        dataframe.to_csv(temporary, index=False)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


__all__ = [
    "DEFAULT_OPENCV_MODEL_NAME",
    "DEFAULT_TELEA_RADIUS",
    "OPENCV_TELEA_CONFIG_SCHEMA_VERSION",
    "RESTORATION_GENERATOR_NAME",
    "RESTORATION_GENERATOR_VERSION",
    "RESTORATIONS_SCHEMA_VERSION",
    "RUNTIME_SUMMARY_SCHEMA_VERSION",
    "binarize_restoration_mask",
    "build_eligible_case_worklist",
    "calculate_file_sha256",
    "load_opencv_telea_config",
    "resolve_project_path",
    "restore_array_with_opencv_telea",
    "run_opencv_telea_case",
    "run_opencv_telea_cases",
    "summarize_restoration_runtime",
    "threshold_policy_for_case",
    "to_project_relative",
    "utc_now_iso",
    "validate_restoration_outputs",
    "validate_restoration_records",
    "write_dataframe_atomic",
]
