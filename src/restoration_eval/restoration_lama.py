"""Normalized, resumable IOPaint LaMa restoration execution."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from hashlib import sha256
from importlib import metadata, util
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Mapping

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


MODEL_NAME = "lama"
IOPAINT_MODEL_NAME = "lama"
RESTORATION_GENERATOR_NAME = "restoration_eval.restoration_lama"
RESTORATION_GENERATOR_VERSION = "3.1.0"
LAMA_CONFIG_SCHEMA_VERSION = "lama_config.v1"
RESTORATIONS_SCHEMA_VERSION = RESTORATIONS_SCHEMA.version
RUNTIME_SUMMARY_SCHEMA_VERSION = RESTORATION_RUNTIME_SUMMARY_SCHEMA.version

LAMA_EXTRA_COLUMNS = (
    "iopaint_version",
    "model_revision",
    "model_artifact_sha256",
    "compositing_policy_id",
    "runtime_measurement_method",
    "batch_id",
    "batch_runtime_seconds",
    "attempt_count",
    "return_code",
    "command_group_id",
)
LAMA_RECORD_COLUMNS = RESTORATIONS_COLUMNS + LAMA_EXTRA_COLUMNS

ProgressCallback = Callable[[str], None]
CheckpointCallback = Callable[[pd.DataFrame], None]
BatchRunner = Callable[..., dict[str, Any]]


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


def load_lama_config(path: str | Path) -> dict[str, Any]:
    """Load and validate the versioned Notebook 10 configuration."""
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("LaMa configuration must be a mapping.")
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
        label="LaMa configuration",
    )
    if payload["config_schema_version"] != LAMA_CONFIG_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported LaMa configuration schema: "
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
            "executable",
            "iopaint_model_name",
            "model_revision",
            "model_artifact_url",
            "model_artifact_expected_md5",
            "requested_device",
            "allow_cpu_fallback",
            "precision",
            "execution_backend",
            "maximum_retries",
            "zero_control_policy",
            "compositing_policy",
            "mask_threshold_policy",
        },
        label="LaMa model configuration",
    )
    _require_mapping_keys(
        execution,
        {
            "progress_interval_cases",
            "progress_poll_seconds",
            "command_timeout_seconds",
            "resume_enabled",
            "overwrite_existing",
            "target_width",
            "target_height",
            "output_mode",
            "output_format",
            "png_compress_level",
            "batch_grouping",
        },
        label="LaMa execution configuration",
    )
    if str(model["model_id"]) != MODEL_NAME:
        raise ValueError("Notebook 10 configuration must target model_id='lama'.")
    if str(model["iopaint_model_name"]) != IOPAINT_MODEL_NAME:
        raise ValueError("Notebook 10 must use the IOPaint LaMa model.")
    if model["zero_control_policy"] != "identity_noop":
        raise ValueError("Zero controls must use identity_noop.")
    if model["compositing_policy"] != "masked_composite_preserve_outside.v1":
        raise ValueError("Notebook 10 must preserve pixels outside the approved mask.")
    if int(model["maximum_retries"]) < 0:
        raise ValueError("maximum_retries must be non-negative.")
    if int(execution["progress_interval_cases"]) <= 0:
        raise ValueError("progress_interval_cases must be positive.")
    if float(execution["progress_poll_seconds"]) <= 0:
        raise ValueError("progress_poll_seconds must be positive.")
    if float(execution["command_timeout_seconds"]) <= 0:
        raise ValueError("command_timeout_seconds must be positive.")
    if execution["batch_grouping"] != "experiment_id":
        raise ValueError("LaMa runtime grouping must be experiment_id.")
    if int(expected["eligible_case_count"]) <= 0:
        raise ValueError("Expected eligible case count must be positive.")

    thresholds = model["mask_threshold_policy"]
    for policy_name in ("binary_missing_region", "synthetic_degradation"):
        if policy_name not in thresholds:
            raise ValueError(f"Missing mask threshold policy: {policy_name}")
        policy = thresholds[policy_name]
        if policy.get("comparison") != "greater_than_or_equal":
            raise ValueError(f"{policy_name} threshold must use >= comparison.")
        threshold = int(policy.get("threshold", -1))
        if not 0 <= threshold <= 255:
            raise ValueError(f"Invalid {policy_name} threshold: {threshold}")

    smoke = payload["smoke"]
    _require_mapping_keys(
        smoke,
        {
            "deterministic_case_id",
            "zero_control_case_id",
            "deterministic_repeat_count",
            "repeatability_tolerance",
        },
        label="LaMa smoke configuration",
    )
    if int(smoke["deterministic_repeat_count"]) < 2:
        raise ValueError("LaMa smoke validation requires at least two repeats.")
    repeatability_tolerance = smoke["repeatability_tolerance"]
    _require_mapping_keys(
        repeatability_tolerance,
        {
            "maximum_absolute_difference",
            "maximum_mean_absolute_difference",
            "maximum_different_pixel_fraction",
            "require_sha256_equality",
        },
        label="LaMa repeatability tolerance",
    )
    if int(repeatability_tolerance["maximum_absolute_difference"]) < 0:
        raise ValueError("Maximum repeat absolute difference must be non-negative.")
    if float(repeatability_tolerance["maximum_mean_absolute_difference"]) < 0:
        raise ValueError("Maximum repeat mean difference must be non-negative.")
    maximum_different_pixel_fraction = float(
        repeatability_tolerance["maximum_different_pixel_fraction"]
    )
    if not 0 <= maximum_different_pixel_fraction <= 1:
        raise ValueError("Maximum different-pixel fraction must be in [0, 1].")
    if not isinstance(repeatability_tolerance["require_sha256_equality"], bool):
        raise ValueError("require_sha256_equality must be boolean.")
    return payload


def _coerce_eligibility(values: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(values):
        return values.astype(bool)
    normalized = values.astype(str).str.strip().str.lower()
    invalid = ~normalized.isin({"true", "false"})
    if invalid.any():
        raise ValueError(
            "Eligibility contains non-boolean values: "
            f"{sorted(normalized.loc[invalid].unique().tolist())}"
        )
    return normalized.eq("true")


def build_eligible_case_worklist(
    case_registry: pd.DataFrame,
    model_eligibility: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Return the exact Notebook 08 worklist approved for LaMa."""
    case_result = validate_dataframe(
        case_registry, CASE_REGISTRY_SCHEMA, allow_extra_columns=False
    )
    eligibility_result = validate_dataframe(
        model_eligibility, MODEL_ELIGIBILITY_SCHEMA, allow_extra_columns=False
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
        raise ValueError(f"No eligibility rows found for {model_id!r}.")
    eligibility["eligible"] = _coerce_eligibility(eligibility["eligible"])
    eligibility = eligibility.loc[eligibility["eligible"]].copy()
    worklist = case_registry.merge(
        eligibility, on="case_id", how="inner", validate="one_to_one"
    )
    worklist = worklist.sort_values(
        ["experiment_id", "case_id"], kind="stable"
    ).reset_index(drop=True)

    expected_count = int(config["expected"]["eligible_case_count"])
    if len(worklist) != expected_count:
        raise ValueError(
            f"Eligible LaMa worklist has {len(worklist)} rows; "
            f"expected {expected_count}."
        )
    if worklist["case_id"].duplicated().any():
        raise ValueError("Eligible LaMa worklist contains duplicate case IDs.")
    if not worklist["status"].astype(str).eq("passed").all():
        raise ValueError("Eligible LaMa worklist contains non-passed cases.")
    observed = {
        str(key): int(value)
        for key, value in worklist.groupby("experiment_id").size().items()
    }
    expected = {
        str(key): int(value)
        for key, value in config["expected"][
            "eligible_case_count_by_experiment"
        ].items()
    }
    if observed != expected:
        raise ValueError(
            "Eligible experiment counts differ from configuration: "
            f"observed={observed}, expected={expected}"
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
    case: Mapping[str, Any], config: Mapping[str, Any]
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
    if mask_gray.ndim != 2:
        raise ValueError(f"Expected a 2-D mask; received {mask_gray.shape}.")
    if not 0 <= int(threshold) <= 255:
        raise ValueError("Mask threshold must be in [0, 255].")
    return np.where(mask_gray >= int(threshold), 255, 0).astype(np.uint8)


def masked_composite(
    input_rgb: np.ndarray,
    inferred_rgb: np.ndarray,
    mask_binary: np.ndarray,
) -> np.ndarray:
    """Use inferred pixels only inside the mask and preserve all others exactly."""
    if input_rgb.shape != inferred_rgb.shape or input_rgb.ndim != 3:
        raise ValueError(
            f"Input and inferred RGB shapes differ: {input_rgb.shape}, "
            f"{inferred_rgb.shape}"
        )
    if mask_binary.shape != input_rgb.shape[:2]:
        raise ValueError("Mask geometry differs from image geometry.")
    return np.where(mask_binary[..., None] > 0, inferred_rgb, input_rgb).astype(
        np.uint8
    )


def _package_version(*names: str) -> str:
    for name in names:
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return ""


def discover_lama_model_artifact(
    config: Mapping[str, Any],
    *,
    project_root: str | Path | None = None,
) -> dict[str, str]:
    """Resolve and hash the configured or IOPaint-cached LaMa checkpoint.

    An explicit ``model_artifact_path`` remains authoritative. When it is
    blank, use IOPaint's own cache resolver and model constants so discovery
    stays portable across operating systems, users, and cache roots.
    """
    configured_value = str(
        config.get("model", {}).get("model_artifact_path", "")
    ).strip()
    artifact_path: Path | None = None
    model = config.get("model", {})
    artifact_url = os.environ.get(
        "LAMA_MODEL_URL", str(model.get("model_artifact_url", ""))
    ).strip()
    expected_md5 = os.environ.get(
        "LAMA_MODEL_MD5",
        str(model.get("model_artifact_expected_md5", "")),
    ).strip()
    discovery_method = "not_discovered"

    if configured_value:
        artifact_path = Path(configured_value).expanduser()
        if not artifact_path.is_absolute() and project_root is not None:
            artifact_path = Path(project_root).resolve() / artifact_path
        artifact_path = artifact_path.resolve()
        discovery_method = (
            "configured_path"
            if artifact_path.is_file()
            else "configured_path_missing"
        )
    else:
        try:
            from iopaint.helper import get_cache_path_by_url

            candidate = Path(
                get_cache_path_by_url(artifact_url)
            ).expanduser().resolve()
            if candidate.is_file():
                artifact_path = candidate
                discovery_method = "iopaint_cache_api"
        except (ImportError, OSError, TypeError, ValueError):
            # Runtime validation reports the missing checksum as a warning.
            # Discovery must not make an otherwise usable IOPaint setup fail.
            pass

    artifact_exists = artifact_path is not None and artifact_path.is_file()
    return {
        "model_artifact_path": (
            str(artifact_path) if artifact_path is not None else ""
        ),
        "model_artifact_sha256": (
            calculate_file_sha256(artifact_path) if artifact_exists else ""
        ),
        "model_artifact_discovery_method": discovery_method,
        "model_artifact_url": artifact_url,
        "model_artifact_expected_md5": expected_md5,
    }


def get_lama_runtime_environment(
    config: Mapping[str, Any],
    *,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    """Capture the exact local environment used by IOPaint."""
    model = config["model"]
    executable = str(model["executable"])
    executable_path = shutil.which(executable) or ""
    if not executable_path:
        executable_names = (
            f"{executable}.exe" if os.name == "nt" else executable,
            executable,
        )
        search_directories = [Path(sys.executable).resolve().parent]
        if project_root is not None:
            search_directories.append(
                Path(project_root).resolve() / ".venv" / "Scripts"
            )
        for directory in search_directories:
            resolved = next(
                (
                    directory / name
                    for name in executable_names
                    if (directory / name).is_file()
                ),
                None,
            )
            if resolved is not None:
                executable_path = str(resolved.resolve())
                break
    torch_version = ""
    cuda_available = False
    cuda_device_count = 0
    cuda_device_name = ""
    cuda_runtime_version = ""
    try:
        import torch

        torch_version = str(torch.__version__)
        cuda_available = bool(torch.cuda.is_available())
        cuda_device_count = int(torch.cuda.device_count())
        cuda_runtime_version = str(torch.version.cuda or "")
        if cuda_available and cuda_device_count:
            cuda_device_name = str(torch.cuda.get_device_name(0))
    except Exception:
        pass

    requested = str(model["requested_device"]).lower()
    effective = requested
    fallback_used = False
    if requested == "cuda" and not cuda_available:
        if bool(model["allow_cpu_fallback"]):
            effective = "cpu"
            fallback_used = True
        else:
            effective = "unavailable"
    artifact = discover_lama_model_artifact(
        config,
        project_root=project_root,
    )
    module_available = util.find_spec("iopaint") is not None
    command_prefix = (
        [str(Path(sys.executable).resolve()), "-m", "iopaint"]
        if module_available
        else ([executable_path] if executable_path else [])
    )
    return {
        "iopaint_executable": executable,
        "iopaint_executable_path": executable_path,
        "iopaint_module_available": module_available,
        "iopaint_launch_mode": "python_module" if module_available else "launcher",
        "iopaint_command_prefix": command_prefix,
        "iopaint_version": _package_version("iopaint", "IOPaint"),
        "iopaint_model_name": str(model["iopaint_model_name"]),
        "model_revision": str(model["model_revision"]),
        "model_artifact_path": artifact["model_artifact_path"],
        "model_artifact_sha256": artifact["model_artifact_sha256"],
        "model_artifact_discovery_method": artifact[
            "model_artifact_discovery_method"
        ],
        "model_artifact_url": artifact["model_artifact_url"],
        "model_artifact_expected_md5": artifact[
            "model_artifact_expected_md5"
        ],
        "requested_device": requested,
        "effective_device": effective,
        "cpu_fallback_used": fallback_used,
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "torch_version": torch_version,
        "cuda_available": cuda_available,
        "cuda_device_count": cuda_device_count,
        "cuda_device_name": cuda_device_name,
        "cuda_runtime_version": cuda_runtime_version,
    }


def validate_lama_runtime_environment(environment: Mapping[str, Any]) -> None:
    if not environment.get("iopaint_command_prefix") and not str(
        environment.get("iopaint_executable_path", "")
    ):
        raise RuntimeError("No usable IOPaint launch command is available.")
    if not str(environment.get("iopaint_version", "")):
        raise RuntimeError("The installed IOPaint package version could not be resolved.")
    if str(environment.get("effective_device")) == "unavailable":
        raise RuntimeError(
            "CUDA was requested but is unavailable and CPU fallback is disabled."
        )


def _load_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"))


def _load_gray(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("L"))


def prepare_lama_work_items(
    worklist: pd.DataFrame,
    *,
    project_root: str | Path,
    config: Mapping[str, Any],
    progress_callback: ProgressCallback | None = print,
) -> pd.DataFrame:
    """Validate files, hash inputs, and resolve zero controls before inference."""
    required = {
        "case_id",
        "experiment_id",
        "input_image_path",
        "mask_or_effect_path",
    }
    missing = sorted(required - set(worklist.columns))
    if missing:
        raise ValueError(f"LaMa worklist is missing columns: {missing}")
    if worklist["case_id"].duplicated().any():
        raise ValueError("LaMa worklist contains duplicate case IDs.")

    ordered = worklist.sort_values(
        ["experiment_id", "case_id"], kind="stable"
    ).reset_index(drop=True)
    root = Path(project_root).resolve()
    expected_size = (
        int(config["execution"]["target_width"]),
        int(config["execution"]["target_height"]),
    )
    interval = int(config["execution"]["progress_interval_cases"])
    timer = perf_counter()
    rows: list[dict[str, Any]] = []
    for position, (_, case) in enumerate(ordered.iterrows(), start=1):
        input_path = resolve_project_path(case["input_image_path"], root)
        mask_path = resolve_project_path(case["mask_or_effect_path"], root)
        if not input_path.is_file():
            raise FileNotFoundError(f"Missing LaMa input: {input_path}")
        if not mask_path.is_file():
            raise FileNotFoundError(f"Missing LaMa mask: {mask_path}")
        with Image.open(input_path) as image:
            image.load()
            if image.size != expected_size:
                raise ValueError(
                    f"Unexpected input geometry for {case['case_id']}: {image.size}"
                )
        mask_gray = _load_gray(mask_path)
        if (mask_gray.shape[1], mask_gray.shape[0]) != expected_size:
            raise ValueError(
                f"Unexpected mask geometry for {case['case_id']}: "
                f"{mask_gray.shape[::-1]}"
            )
        threshold = int(threshold_policy_for_case(case.to_dict(), config)["threshold"])
        mask_binary = binarize_restoration_mask(mask_gray, threshold)
        row = case.to_dict()
        row.update(
            {
                "input_sha256": calculate_file_sha256(input_path),
                "mask_sha256": calculate_file_sha256(mask_path),
                "mask_threshold": threshold,
                "mask_area_pixels": int((mask_binary > 0).sum()),
                "is_zero_control": not bool(np.any(mask_binary)),
            }
        )
        rows.append(row)
        if progress_callback is not None and (
            position % interval == 0 or position == len(ordered)
        ):
            elapsed = max(perf_counter() - timer, 1e-12)
            progress_callback(
                f"Prepared {position}/{len(ordered)} ({position / len(ordered):.1%}) | "
                f"elapsed={elapsed:.1f}s | throughput={position / elapsed:.2f} "
                f"cases/s | latest={case['case_id']}"
            )
    prepared = pd.DataFrame(rows)
    expected_zero = int(config["expected"]["zero_control_case_count"])
    if len(prepared) == int(config["expected"]["eligible_case_count"]):
        observed_zero = int(prepared["is_zero_control"].astype(bool).sum())
        if observed_zero != expected_zero:
            raise ValueError(
                f"Resolved {observed_zero} zero controls; expected {expected_zero}."
            )
    return prepared


def _reset_owned_directory(path: Path, owner_root: Path) -> Path:
    target = path.resolve()
    owner = owner_root.resolve()
    try:
        target.relative_to(owner)
    except ValueError as exc:
        raise ValueError(f"Refusing to reset path outside work root: {target}") from exc
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _stage_input(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
        return "hardlink"
    except OSError:
        shutil.copy2(source, destination)
        return "copy"


def stage_lama_batch(
    items: pd.DataFrame,
    *,
    batch_directory: str | Path,
    work_root: str | Path,
    project_root: str | Path,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Create ephemeral IOPaint input/mask staging with deterministic tokens."""
    if items.empty:
        raise ValueError("Cannot stage an empty LaMa batch.")
    if items["is_zero_control"].astype(bool).any():
        raise ValueError("Zero controls must not be staged for LaMa inference.")
    work = Path(work_root).resolve()
    batch = _reset_owned_directory(Path(batch_directory), work)
    input_dir = (batch / "input").resolve()
    mask_dir = (batch / "mask").resolve()
    output_dir = (batch / "output").resolve()
    logs_dir = (batch / "logs").resolve()
    for directory in (input_dir, mask_dir, output_dir, logs_dir):
        directory.mkdir(parents=True, exist_ok=True)

    root = Path(project_root).resolve()
    staged_rows: list[dict[str, Any]] = []
    for index, (_, item) in enumerate(
        items.sort_values("case_id", kind="stable").iterrows(), start=1
    ):
        token = f"case_{index:05d}"
        staged_input = input_dir / f"{token}.png"
        staged_mask = mask_dir / f"{token}.png"
        raw_output = output_dir / f"{token}.png"
        link_mode = _stage_input(
            resolve_project_path(item["input_image_path"], root), staged_input
        )
        mask_gray = _load_gray(
            resolve_project_path(item["mask_or_effect_path"], root)
        )
        mask_binary = binarize_restoration_mask(
            mask_gray, int(item["mask_threshold"])
        )
        Image.fromarray(mask_binary, mode="L").save(staged_mask, format="PNG")
        row = item.to_dict()
        row.update(
            {
                "staging_token": token,
                "staging_link_mode": link_mode,
                "staged_input_path": str(staged_input),
                "staged_mask_path": str(staged_mask),
                "raw_output_path": str(raw_output),
                "staging_input_directory": str(input_dir),
                "staging_mask_directory": str(mask_dir),
                "staging_output_directory": str(output_dir),
                "staging_logs_directory": str(logs_dir),
            }
        )
        staged_rows.append(row)
    return pd.DataFrame(staged_rows)


def build_iopaint_command(
    staged_items: pd.DataFrame,
    config: Mapping[str, Any],
    runtime_environment: Mapping[str, Any],
) -> list[str]:
    first = staged_items.iloc[0]
    command_prefix = runtime_environment.get("iopaint_command_prefix")
    if command_prefix:
        command = [str(value) for value in command_prefix]
    else:
        command = [str(runtime_environment["iopaint_executable_path"])]
    return command + [
        "run",
        "--model",
        str(config["model"]["iopaint_model_name"]),
        "--device",
        str(runtime_environment["effective_device"]),
        "--image",
        str(first["staging_input_directory"]),
        "--mask",
        str(first["staging_mask_directory"]),
        "--output",
        str(first["staging_output_directory"]),
    ]


def build_iopaint_subprocess_environment(
    base_environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return a Windows-safe, non-interactive environment for IOPaint."""
    environment = dict(
        os.environ if base_environment is None else base_environment
    )
    environment.update(
        {
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "TERM": "dumb",
            "NO_COLOR": "1",
            "RICH_NO_COLOR": "1",
        }
    )
    return environment


def run_iopaint_batch(
    staged_items: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    runtime_environment: Mapping[str, Any],
    batch_id: str,
    progress_callback: ProgressCallback | None = print,
    progress_offset: int = 0,
    progress_total: int | None = None,
) -> dict[str, Any]:
    """Run one IOPaint command while observing generated-file progress."""
    if staged_items.empty:
        raise ValueError("Cannot execute an empty IOPaint batch.")
    validate_lama_runtime_environment(runtime_environment)
    command = build_iopaint_command(staged_items, config, runtime_environment)
    logs_dir = Path(str(staged_items.iloc[0]["staging_logs_directory"]))
    stdout_path = logs_dir / "stdout.log"
    stderr_path = logs_dir / "stderr.log"
    command_path = logs_dir / "command.txt"
    command_path.write_text(subprocess.list2cmdline(command), encoding="utf-8")
    started_at = utc_now_iso()
    timer = perf_counter()
    timeout = float(config["execution"]["command_timeout_seconds"])
    poll = float(config["execution"]["progress_poll_seconds"])
    interval = int(config["execution"]["progress_interval_cases"])
    total = int(progress_total if progress_total is not None else len(staged_items))
    next_threshold = ((progress_offset // interval) + 1) * interval
    timed_out = False
    launch_issue = ""
    return_code = -1

    try:
        with stdout_path.open("w", encoding="utf-8", errors="replace") as stdout_handle, (
            stderr_path.open("w", encoding="utf-8", errors="replace")
        ) as stderr_handle:
            process = subprocess.Popen(
                command,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
                env=build_iopaint_subprocess_environment(),
            )
            while process.poll() is None:
                elapsed = perf_counter() - timer
                if elapsed > timeout:
                    process.kill()
                    timed_out = True
                    break
                generated = sum(
                    Path(str(path)).is_file()
                    for path in staged_items["raw_output_path"]
                )
                while progress_offset + generated >= next_threshold:
                    if progress_callback is not None:
                        progress_callback(
                            f"Generated {next_threshold}/{total} "
                            f"({next_threshold / total:.1%}) | elapsed={elapsed:.1f}s | "
                            f"throughput={generated / max(elapsed, 1e-12):.2f} "
                            f"cases/s | latest_group={batch_id}"
                        )
                    next_threshold += interval
                time.sleep(poll)
            return_code = int(process.wait())
    except Exception as exc:
        launch_issue = f"{type(exc).__name__}: {exc}"

    runtime_seconds = perf_counter() - timer
    generated_count = sum(
        Path(str(path)).is_file() for path in staged_items["raw_output_path"]
    )
    completed_at = utc_now_iso()
    return {
        "batch_id": batch_id,
        "case_count": int(len(staged_items)),
        "generated_count": int(generated_count),
        "return_code": return_code,
        "runtime_seconds": float(runtime_seconds),
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "timed_out": timed_out,
        "issue": launch_issue or ("command_timeout" if timed_out else ""),
        "command": command,
        "command_text": subprocess.list2cmdline(command),
        "command_log_path": str(command_path),
        "stdout_log_path": str(stdout_path),
        "stderr_log_path": str(stderr_path),
    }


def _identifiers(case_id: str, model_id: str) -> tuple[str, str]:
    return (
        f"restoration__{model_id}__{case_id}",
        f"candidate__{model_id}__{case_id}__c00",
    )


def _output_path_for_case(case: Mapping[str, Any], restored_root: Path) -> Path:
    return (
        restored_root
        / str(case["experiment_id"])
        / f"{case['case_id']}.png"
    ).resolve()


def _environment_text(environment: Mapping[str, Any]) -> str:
    return " | ".join(
        [
            str(environment.get("platform", "")),
            str(environment.get("machine", "")),
            str(environment.get("processor", "")),
            str(environment.get("cuda_device_name", "")),
        ]
    )


def _model_version(environment: Mapping[str, Any]) -> str:
    version = str(environment.get("iopaint_version", "unknown")) or "unknown"
    revision = str(environment.get("model_revision", "unknown")) or "unknown"
    return f"iopaint-{version}__{revision}"


def _base_record(
    item: Mapping[str, Any],
    *,
    output_path: Path,
    project_root: Path,
    config: Mapping[str, Any],
    environment: Mapping[str, Any],
) -> dict[str, Any]:
    model = config["model"]
    case_id = str(item["case_id"])
    restoration_id, candidate_id = _identifiers(case_id, str(model["model_id"]))
    record = {column: "" for column in LAMA_RECORD_COLUMNS}
    record.update(
        {
            "restoration_id": restoration_id,
            "case_id": case_id,
            "model_id": str(model["model_id"]),
            "candidate_id": candidate_id,
            "candidate_index": 0,
            "seed": "",
            "prompt_policy_id": "",
            "model_version": _model_version(environment),
            "opencv_version": "",
            "configuration_id": str(model["configuration_id"]),
            "algorithm": "iopaint run --model lama",
            "inpaint_radius": "",
            "mask_threshold": int(item["mask_threshold"]),
            "restored_path": to_project_relative(output_path, project_root),
            "input_sha256": str(item["input_sha256"]),
            "mask_sha256": str(item["mask_sha256"]),
            "device": str(environment["effective_device"]),
            "precision": str(model["precision"]),
            "execution_backend": str(model["execution_backend"]),
            "cpu_environment": _environment_text(environment),
            "generator_name": RESTORATION_GENERATOR_NAME,
            "generator_version": RESTORATION_GENERATOR_VERSION,
            "iopaint_version": str(environment.get("iopaint_version", "")),
            "model_revision": str(environment.get("model_revision", "")),
            "model_artifact_sha256": str(
                environment.get("model_artifact_sha256", "")
            ),
            "compositing_policy_id": str(model["compositing_policy"]),
        }
    )
    return record


def _write_rgb_png_atomic(
    image_rgb: np.ndarray, path: Path, *, compress_level: int
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.png")
    try:
        Image.fromarray(image_rgb.astype(np.uint8), mode="RGB").save(
            temporary,
            format="PNG",
            compress_level=int(compress_level),
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _resume_record_is_valid(
    record: Mapping[str, Any],
    *,
    output_path: Path,
    item: Mapping[str, Any],
    config: Mapping[str, Any],
    environment: Mapping[str, Any],
) -> bool:
    if str(record.get("status")) != "completed" or not output_path.is_file():
        return False
    expected = {
        "model_id": str(config["model"]["model_id"]),
        "configuration_id": str(config["model"]["configuration_id"]),
        "model_version": _model_version(environment),
        "generator_version": RESTORATION_GENERATOR_VERSION,
        "input_sha256": str(item["input_sha256"]),
        "mask_sha256": str(item["mask_sha256"]),
        "mask_threshold": str(int(item["mask_threshold"])),
        "compositing_policy_id": str(config["model"]["compositing_policy"]),
    }
    if any(str(record.get(key, "")) != value for key, value in expected.items()):
        return False
    output_hash = str(record.get("restored_sha256", ""))
    return bool(output_hash) and calculate_file_sha256(output_path) == output_hash


def _resume_lookup(records: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if records is None or records.empty:
        return {}
    if "case_id" not in records or records["case_id"].duplicated().any():
        raise ValueError("Resume records require unique case IDs.")
    return {
        str(row["case_id"]): row.to_dict() for _, row in records.iterrows()
    }


def _copy_zero_control(
    item: Mapping[str, Any],
    *,
    output_path: Path,
    project_root: Path,
    config: Mapping[str, Any],
    environment: Mapping[str, Any],
) -> dict[str, Any]:
    record = _base_record(
        item,
        output_path=output_path,
        project_root=project_root,
        config=config,
        environment=environment,
    )
    started = utc_now_iso()
    timer = perf_counter()
    try:
        source = resolve_project_path(item["input_image_path"], project_root)
        image_rgb = _load_rgb(source)
        _write_rgb_png_atomic(
            image_rgb,
            output_path,
            compress_level=int(config["execution"]["png_compress_level"]),
        )
        record.update(
            {
                "execution_action": "identity_noop",
                "restored_sha256": calculate_file_sha256(output_path),
                "runtime_seconds": float(perf_counter() - timer),
                "runtime_measurement_method": "measured_identity_copy_wall_clock",
                "retry_count": 0,
                "attempt_count": 0,
                "return_code": 0,
                "started_at_utc": started,
                "completed_at_utc": utc_now_iso(),
                "status": "completed",
                "issue": "",
            }
        )
    except Exception as exc:
        record.update(
            {
                "execution_action": "failed",
                "restored_sha256": "",
                "runtime_seconds": float(perf_counter() - timer),
                "runtime_measurement_method": "measured_identity_copy_wall_clock",
                "retry_count": 0,
                "attempt_count": 0,
                "return_code": -1,
                "started_at_utc": started,
                "completed_at_utc": utc_now_iso(),
                "status": "failed",
                "issue": f"{type(exc).__name__}: {exc}",
            }
        )
    return record


def _collect_inferred_item(
    item: Mapping[str, Any],
    *,
    output_path: Path,
    project_root: Path,
    config: Mapping[str, Any],
    environment: Mapping[str, Any],
    batch_run: Mapping[str, Any],
    attempt_count: int,
    allocated_runtime: float,
) -> dict[str, Any] | None:
    raw_path = Path(str(item["raw_output_path"]))
    if not raw_path.is_file():
        return None
    record = _base_record(
        item,
        output_path=output_path,
        project_root=project_root,
        config=config,
        environment=environment,
    )
    try:
        input_rgb = _load_rgb(
            resolve_project_path(item["input_image_path"], project_root)
        )
        inferred_rgb = _load_rgb(raw_path)
        mask_gray = _load_gray(
            resolve_project_path(item["mask_or_effect_path"], project_root)
        )
        mask_binary = binarize_restoration_mask(
            mask_gray, int(item["mask_threshold"])
        )
        composed = masked_composite(input_rgb, inferred_rgb, mask_binary)
        _write_rgb_png_atomic(
            composed,
            output_path,
            compress_level=int(config["execution"]["png_compress_level"]),
        )
        record.update(
            {
                "execution_action": "lama_inpaint",
                "restored_sha256": calculate_file_sha256(output_path),
                "runtime_seconds": float(allocated_runtime),
                "runtime_measurement_method": (
                    "experiment_batch_wall_clock_allocated_mean"
                ),
                "retry_count": int(attempt_count - 1),
                "attempt_count": int(attempt_count),
                "batch_id": str(batch_run["batch_id"]),
                "command_group_id": str(batch_run["batch_id"]),
                "batch_runtime_seconds": float(batch_run["runtime_seconds"]),
                "return_code": int(batch_run["return_code"]),
                "started_at_utc": str(batch_run["started_at_utc"]),
                "completed_at_utc": str(batch_run["completed_at_utc"]),
                "status": "completed",
                "issue": "",
            }
        )
        return record
    except Exception:
        return None


def _failed_record(
    item: Mapping[str, Any],
    *,
    output_path: Path,
    project_root: Path,
    config: Mapping[str, Any],
    environment: Mapping[str, Any],
    batch_runs: list[Mapping[str, Any]],
) -> dict[str, Any]:
    record = _base_record(
        item,
        output_path=output_path,
        project_root=project_root,
        config=config,
        environment=environment,
    )
    total_runtime = float(sum(float(run["runtime_seconds"]) for run in batch_runs))
    issue_parts = [str(run.get("issue", "")) for run in batch_runs if run.get("issue")]
    if not issue_parts:
        issue_parts = ["IOPaint did not produce a readable output after all attempts."]
    last = batch_runs[-1]
    record.update(
        {
            "execution_action": "failed",
            "restored_sha256": "",
            "runtime_seconds": total_runtime / max(int(last["case_count"]), 1),
            "runtime_measurement_method": "failed_batch_wall_clock_allocated_mean",
            "retry_count": max(len(batch_runs) - 1, 0),
            "attempt_count": len(batch_runs),
            "batch_id": str(last["batch_id"]),
            "command_group_id": str(last["batch_id"]),
            "batch_runtime_seconds": float(last["runtime_seconds"]),
            "return_code": int(last["return_code"]),
            "started_at_utc": str(batch_runs[0]["started_at_utc"]),
            "completed_at_utc": str(last["completed_at_utc"]),
            "status": "failed",
            "issue": "; ".join(issue_parts),
        }
    )
    return record


def run_lama_cases(
    prepared_worklist: pd.DataFrame,
    *,
    restored_root: str | Path,
    work_root: str | Path,
    project_root: str | Path,
    config: Mapping[str, Any],
    runtime_environment: Mapping[str, Any] | None = None,
    resume_records: pd.DataFrame | None = None,
    progress_callback: ProgressCallback | None = print,
    checkpoint_callback: CheckpointCallback | None = None,
    batch_runner: BatchRunner = run_iopaint_batch,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Execute zero controls and experiment-grouped LaMa batches with resume."""
    required = {
        "case_id",
        "experiment_id",
        "input_image_path",
        "mask_or_effect_path",
        "input_sha256",
        "mask_sha256",
        "mask_threshold",
        "is_zero_control",
    }
    missing = sorted(required - set(prepared_worklist.columns))
    if missing:
        raise ValueError(f"Prepared LaMa worklist is missing columns: {missing}")
    environment = dict(runtime_environment or get_lama_runtime_environment(config))
    validate_lama_runtime_environment(environment)
    root = Path(project_root).resolve()
    restored = Path(restored_root).resolve()
    work = Path(work_root).resolve()
    restored.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    resume_by_case = _resume_lookup(resume_records)
    ordered = prepared_worklist.sort_values(
        ["experiment_id", "case_id"], kind="stable"
    ).reset_index(drop=True)
    total = len(ordered)
    interval = int(config["execution"]["progress_interval_cases"])
    records_by_case: dict[str, dict[str, Any]] = {}
    batch_runs: list[dict[str, Any]] = []
    processed = 0
    pipeline_timer = perf_counter()

    pending_rows: list[dict[str, Any]] = []
    for _, item in ordered.iterrows():
        item_dict = item.to_dict()
        case_id = str(item_dict["case_id"])
        output_path = _output_path_for_case(item_dict, restored)
        resume_record = resume_by_case.get(case_id)
        if (
            bool(config["execution"]["resume_enabled"])
            and resume_record is not None
            and _resume_record_is_valid(
                resume_record,
                output_path=output_path,
                item=item_dict,
                config=config,
                environment=environment,
            )
        ):
            reused = {column: resume_record.get(column, "") for column in LAMA_RECORD_COLUMNS}
            reused["execution_action"] = "reused_validated"
            reused["restored_path"] = to_project_relative(output_path, root)
            records_by_case[case_id] = reused
            processed += 1
            continue
        if output_path.exists() and not bool(config["execution"]["overwrite_existing"]):
            raise FileExistsError(
                "Existing output lacks matching resume evidence: " f"{output_path}"
            )
        pending_rows.append(item_dict)

    pending = pd.DataFrame(pending_rows)
    if not pending.empty:
        zero_items = pending.loc[pending["is_zero_control"].astype(bool)].copy()
        for _, item in zero_items.iterrows():
            item_dict = item.to_dict()
            case_id = str(item_dict["case_id"])
            record = _copy_zero_control(
                item_dict,
                output_path=_output_path_for_case(item_dict, restored),
                project_root=root,
                config=config,
                environment=environment,
            )
            records_by_case[case_id] = record
            processed += 1
            if progress_callback is not None and (
                processed % interval == 0 or processed == total
            ):
                elapsed = max(perf_counter() - pipeline_timer, 1e-12)
                progress_callback(
                    f"Completed {processed}/{total} ({processed / total:.1%}) | "
                    f"elapsed={elapsed:.1f}s | throughput={processed / elapsed:.2f} "
                    f"cases/s | latest={case_id}"
                )

        inference = pending.loc[~pending["is_zero_control"].astype(bool)].copy()
        for experiment_id, group in inference.groupby("experiment_id", sort=True):
            remaining = group.copy()
            group_runs: list[dict[str, Any]] = []
            maximum_attempts = int(config["model"]["maximum_retries"]) + 1
            for attempt in range(1, maximum_attempts + 1):
                if remaining.empty:
                    break
                batch_id = f"{experiment_id}__attempt_{attempt:02d}"
                batch_dir = work / "batches" / batch_id
                staged = stage_lama_batch(
                    remaining,
                    batch_directory=batch_dir,
                    work_root=work,
                    project_root=root,
                    config=config,
                )
                run = batch_runner(
                    staged,
                    config=config,
                    runtime_environment=environment,
                    batch_id=batch_id,
                    progress_callback=progress_callback,
                    progress_offset=processed,
                    progress_total=total,
                )
                run = dict(run)
                run["experiment_id"] = str(experiment_id)
                run["attempt"] = attempt
                group_runs.append(run)
                batch_runs.append(run)
                allocated = float(run["runtime_seconds"]) / max(len(staged), 1)
                unresolved_rows: list[dict[str, Any]] = []
                for _, staged_item in staged.iterrows():
                    item_dict = staged_item.to_dict()
                    case_id = str(item_dict["case_id"])
                    record = _collect_inferred_item(
                        item_dict,
                        output_path=_output_path_for_case(item_dict, restored),
                        project_root=root,
                        config=config,
                        environment=environment,
                        batch_run=run,
                        attempt_count=attempt,
                        allocated_runtime=allocated,
                    )
                    if record is None:
                        unresolved_rows.append(item_dict)
                    else:
                        records_by_case[case_id] = record
                        processed += 1
                remaining = pd.DataFrame(unresolved_rows)
                if checkpoint_callback is not None:
                    checkpoint_callback(
                        pd.DataFrame(
                            list(records_by_case.values()),
                            columns=LAMA_RECORD_COLUMNS,
                        )
                    )

            if not remaining.empty:
                for _, item in remaining.iterrows():
                    item_dict = item.to_dict()
                    case_id = str(item_dict["case_id"])
                    records_by_case[case_id] = _failed_record(
                        item_dict,
                        output_path=_output_path_for_case(item_dict, restored),
                        project_root=root,
                        config=config,
                        environment=environment,
                        batch_runs=group_runs,
                    )
                    processed += 1

    records = pd.DataFrame(
        [records_by_case[str(case_id)] for case_id in ordered["case_id"]],
        columns=LAMA_RECORD_COLUMNS,
    )
    if progress_callback is not None:
        elapsed = max(perf_counter() - pipeline_timer, 1e-12)
        progress_callback(
            f"Completed {len(records)}/{total} ({len(records) / total:.1%}) | "
            f"elapsed={elapsed:.1f}s | throughput={len(records) / elapsed:.2f} "
            f"cases/s | latest={records.iloc[-1]['case_id']}"
        )
    if checkpoint_callback is not None:
        checkpoint_callback(records.copy())
    batch_runs_frame = pd.DataFrame(batch_runs)
    return records, batch_runs_frame


def validate_restoration_records(records: pd.DataFrame) -> None:
    result = validate_dataframe(records, RESTORATIONS_SCHEMA, allow_extra_columns=True)
    if not result.passed:
        raise ValueError(f"LaMa restoration records violate schema: {result.to_dict()}")
    missing_extra = sorted(set(LAMA_EXTRA_COLUMNS) - set(records.columns))
    if missing_extra:
        raise ValueError(f"LaMa records are missing provenance columns: {missing_extra}")


def validate_restoration_outputs(
    records: pd.DataFrame,
    worklist: pd.DataFrame,
    *,
    project_root: str | Path,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Reload every output and validate geometry, checksums, and spatial policy."""
    joined = records.merge(
        worklist[
            ["case_id", "experiment_id", "input_image_path", "mask_or_effect_path"]
        ],
        on="case_id",
        how="left",
        validate="one_to_one",
    )
    root = Path(project_root).resolve()
    expected_size = (
        int(config["execution"]["target_width"]),
        int(config["execution"]["target_height"]),
    )
    rows: list[dict[str, Any]] = []
    for _, row in joined.iterrows():
        issues: list[str] = []
        output_path = resolve_project_path(row["restored_path"], root)
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
            input_rgb = _load_rgb(
                resolve_project_path(row["input_image_path"], root)
            )
            mask_gray = _load_gray(
                resolve_project_path(row["mask_or_effect_path"], root)
            )
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
    """Return an overall row and one row for each experiment."""
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
        summary, RESTORATION_RUNTIME_SUMMARY_SCHEMA, allow_extra_columns=False
    )
    if not result.passed:
        raise ValueError(f"Runtime summary violates schema: {result.to_dict()}")
    return summary


def write_dataframe_atomic(dataframe: pd.DataFrame, path: str | Path) -> Path:
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
    "IOPAINT_MODEL_NAME",
    "LAMA_CONFIG_SCHEMA_VERSION",
    "LAMA_EXTRA_COLUMNS",
    "LAMA_RECORD_COLUMNS",
    "MODEL_NAME",
    "RESTORATION_GENERATOR_NAME",
    "RESTORATION_GENERATOR_VERSION",
    "RESTORATIONS_SCHEMA_VERSION",
    "RUNTIME_SUMMARY_SCHEMA_VERSION",
    "binarize_restoration_mask",
    "build_eligible_case_worklist",
    "build_iopaint_command",
    "build_iopaint_subprocess_environment",
    "calculate_file_sha256",
    "discover_lama_model_artifact",
    "get_lama_runtime_environment",
    "load_lama_config",
    "masked_composite",
    "prepare_lama_work_items",
    "resolve_project_path",
    "run_iopaint_batch",
    "run_lama_cases",
    "stage_lama_batch",
    "summarize_restoration_runtime",
    "threshold_policy_for_case",
    "to_project_relative",
    "utc_now_iso",
    "validate_lama_runtime_environment",
    "validate_restoration_outputs",
    "validate_restoration_records",
    "write_dataframe_atomic",
]
