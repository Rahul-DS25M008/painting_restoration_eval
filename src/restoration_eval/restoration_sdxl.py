"""SDXL feasibility planning, guarded execution, and audit helpers.

The expensive model load and inference run in an isolated worker process. This
module owns the parent-side watchdog and never imports torch or diffusers, which
keeps notebook preflight fast and makes a hard timeout enforceable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter
import time
from typing import Any, Mapping, Sequence

import pandas as pd
import yaml

from restoration_eval.restoration_stable_diffusion import build_eligible_case_worklist
from restoration_eval.schemas import (
    SDXL_FEASIBILITY_ATTEMPT_COLUMNS,
    SDXL_FEASIBILITY_ATTEMPTS_SCHEMA,
    SDXL_PARTIAL_CANDIDATE_COLUMNS,
    SDXL_PARTIAL_CANDIDATES_SCHEMA,
    validate_dataframe,
)


SDXL_HELPER_NAME = "restoration_eval.restoration_sdxl"
SDXL_HELPER_VERSION = "3.0.0"
SDXL_CONFIG_SCHEMA_VERSION = "sdxl_config.v2"


def utc_now_iso() -> str:
    """Return an RFC-3339 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def calculate_file_sha256(path: str | Path) -> str:
    """Calculate a full SHA-256 checksum for one file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configuration_fingerprint(config: Mapping[str, Any]) -> str:
    """Return a stable checksum for the parsed SDXL configuration."""
    payload = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def inspect_local_model_cache(
    config: Mapping[str, Any],
    *,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Inspect the pinned Hugging Face snapshot without loading or downloading it."""
    values = os.environ if environment is None else environment
    if values.get("HUGGINGFACE_HUB_CACHE"):
        hub_root = Path(values["HUGGINGFACE_HUB_CACHE"])
        source = "HUGGINGFACE_HUB_CACHE"
    elif values.get("HF_HOME"):
        hub_root = Path(values["HF_HOME"]) / "hub"
        source = "HF_HOME"
    else:
        hub_root = Path.home() / ".cache" / "huggingface" / "hub"
        source = "default"
    model_id = str(config["model"]["hf_model_id"])
    revision = str(config["model"]["model_revision"])
    model_root = hub_root / ("models--" + model_id.replace("/", "--"))
    snapshot = model_root / "snapshots" / revision
    files = [path for path in snapshot.rglob("*") if path.is_file()] if snapshot.is_dir() else []
    return {
        "cache_source": source,
        "hub_root": str(hub_root.resolve()),
        "model_cache_root": str(model_root.resolve()),
        "snapshot_path": str(snapshot.resolve()),
        "pinned_revision": revision,
        "snapshot_exists": snapshot.is_dir(),
        "model_index_exists": (snapshot / "model_index.json").is_file(),
        "file_count": len(files),
        "size_bytes": sum(path.stat().st_size for path in files),
        "local_files_only": bool(config["model"]["local_files_only"]),
    }


def _require_keys(mapping: Mapping[str, Any], keys: set[str], *, label: str) -> None:
    missing = sorted(keys - set(mapping))
    if missing:
        raise ValueError(f"{label} is missing required keys: {missing}")


def load_sdxl_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the versioned Notebook 12 configuration."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise TypeError("SDXL configuration must contain a YAML mapping")
    _require_keys(
        config,
        {
            "config_schema_version", "config_version", "dataset", "inputs",
            "output", "model", "prompt_policy", "memory_strategy", "execution",
            "selection", "scope", "legacy_evidence", "availability",
            "schema_versions", "known_limitations",
        },
        label="SDXL configuration",
    )
    if config["config_schema_version"] != SDXL_CONFIG_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported SDXL config schema: "
            f"{config['config_schema_version']!r}; expected {SDXL_CONFIG_SCHEMA_VERSION!r}"
        )

    model = config["model"]
    execution = config["execution"]
    memory = config["memory_strategy"]
    scope = config["scope"]
    _require_keys(
        model,
        {
            "model_id", "configuration_id", "hf_model_id", "model_revision",
            "scheduler", "requested_device", "allow_cpu_fallback", "precision",
            "inference_width", "inference_height", "output_width", "output_height",
            "num_inference_steps", "guidance_scale", "strength", "seed",
            "mask_threshold", "compositing_policy", "local_files_only",
        },
        label="model",
    )
    _require_keys(
        execution,
        {
            "mode", "maximum_current_attempts", "per_attempt_timeout_seconds",
            "stop_after_timeout", "stop_after_cuda_oom", "stop_after_model_failure",
            "retry_failed_attempts", "progress_interval_attempts",
            "preserve_worker_files", "worker_module", "timeout_policy_id",
        },
        label="execution",
    )
    _require_keys(
        memory,
        {
            "strategy_id", "model_cpu_offload", "sequential_cpu_offload",
            "attention_backend", "attention_slicing", "vae_slicing", "vae_tiling",
            "xformers", "torch_compile", "allow_tf32",
        },
        label="memory_strategy",
    )
    _require_keys(
        scope,
        {
            "eligible_primary_case_count", "comparable_candidate_count",
            "current_attempt_count", "full_execution_authorized",
        },
        label="scope",
    )

    if execution["mode"] != "feasibility_only":
        raise ValueError("This configuration authorizes feasibility_only mode only")
    if bool(scope["full_execution_authorized"]):
        raise ValueError("Full SDXL execution is not authorized by this configuration")
    if int(execution["maximum_current_attempts"]) != int(scope["current_attempt_count"]):
        raise ValueError("Attempt-count declarations disagree")
    if int(execution["per_attempt_timeout_seconds"]) <= 0:
        raise ValueError("per_attempt_timeout_seconds must be positive")
    if bool(execution["retry_failed_attempts"]):
        raise ValueError("Automatic SDXL retries are prohibited in feasibility mode")
    if model["requested_device"] != "cuda" or bool(model["allow_cpu_fallback"]):
        raise ValueError("The SDXL probe requires CUDA and prohibits CPU fallback")
    if model["precision"] != "float16":
        raise ValueError("The approved SDXL feasibility precision is float16")
    if int(model["num_inference_steps"]) != 30:
        raise ValueError("The quality-preserving SDXL probe freezes 30 denoising steps")
    if (int(model["inference_width"]), int(model["inference_height"])) != (768, 768):
        raise ValueError("The quality-preserving SDXL probe freezes 768 x 768 inference")
    if not bool(memory["model_cpu_offload"]) or bool(memory["sequential_cpu_offload"]):
        raise ValueError("The approved memory policy requires model CPU offload only")
    if memory["attention_backend"] != "pytorch_sdpa" or bool(memory["attention_slicing"]):
        raise ValueError("The approved attention policy is unsliced PyTorch SDPA")
    if bool(memory["torch_compile"]) or bool(memory["xformers"]):
        raise ValueError("Compilation and xFormers are not part of the pinned probe")
    return config


def build_sdxl_eligible_worklist(
    case_registry: pd.DataFrame,
    model_eligibility: pd.DataFrame,
    artworks: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the same 410-case eligible worklist used by Notebook 11."""
    stable_config = {
        "model": {"model_id": "stable_diffusion_inpainting"},
        "expected": {
            "eligible_case_count": int(config["scope"]["eligible_primary_case_count"]),
            "zero_control_case_count": 50,
        },
    }
    worklist = build_eligible_case_worklist(
        case_registry, model_eligibility, artworks, stable_config
    )
    expected = int(config["scope"]["eligible_primary_case_count"])
    if len(worklist) != expected:
        raise ValueError(f"Expected {expected} eligible cases, found {len(worklist)}")
    return worklist


def select_feasibility_case(
    worklist: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.Series:
    """Select the predeclared, non-metric representative feasibility case."""
    case_id = str(config["selection"]["deterministic_case_id"])
    matches = worklist.loc[worklist["case_id"].astype(str).eq(case_id)]
    if len(matches) != 1:
        raise ValueError(f"Predeclared feasibility case must match once: {case_id!r}")
    row = matches.iloc[0].copy()
    if bool(config["selection"]["require_nonzero_damage"]):
        if bool(row.get("is_zero_control", False)):
            raise ValueError("The feasibility case may not be a zero control")
        if float(row.get("realized_damage_fraction", 0.0)) <= 0:
            raise ValueError("The feasibility case must have nonzero realized damage")
    return row


def _attempt_id(case_id: str, configuration_id: str) -> str:
    token = hashlib.sha256(f"{case_id}|{configuration_id}|current".encode()).hexdigest()[:12]
    return f"sdxl_probe__{token}"


def build_feasibility_attempt_plan(
    selected_case: Mapping[str, Any],
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the single predeclared current-execution attempt."""
    model = config["model"]
    prompt = config["prompt_policy"]
    memory = config["memory_strategy"]
    execution = config["execution"]
    case_id = str(selected_case["case_id"])
    attempt = {
        "attempt_id": _attempt_id(case_id, str(model["configuration_id"])),
        "attempt_index": 1,
        "evidence_origin": "current_execution",
        "case_id": case_id,
        "painting_id": str(selected_case["painting_id"]),
        "experiment_id": str(selected_case["experiment_id"]),
        "damage_or_degradation_type": str(selected_case["damage_or_degradation_type"]),
        "input_image_path": str(selected_case["input_image_path"]),
        "mask_or_effect_path": str(selected_case["mask_or_effect_path"]),
        "input_sha256": "",
        "mask_sha256": "",
        "model_id": str(model["model_id"]),
        "hf_model_id": str(model["hf_model_id"]),
        "model_revision": str(model["model_revision"]),
        "configuration_id": str(model["configuration_id"]),
        "configuration_fingerprint": configuration_fingerprint(config),
        "prompt_policy_id": str(prompt["policy_id"]),
        "prompt": str(prompt["prompt"]),
        "negative_prompt": str(prompt["negative_prompt"]),
        "seed": int(model["seed"]),
        "requested_device": str(model["requested_device"]),
        "actual_device": "",
        "gpu_name": "",
        "gpu_total_memory_bytes": None,
        "precision": str(model["precision"]),
        "inference_width": int(model["inference_width"]),
        "inference_height": int(model["inference_height"]),
        "output_width": int(model["output_width"]),
        "output_height": int(model["output_height"]),
        "num_inference_steps": int(model["num_inference_steps"]),
        "guidance_scale": float(model["guidance_scale"]),
        "strength": float(model["strength"]),
        "scheduler": str(model["scheduler"]),
        "memory_strategy_id": str(memory["strategy_id"]),
        "model_cpu_offload": bool(memory["model_cpu_offload"]),
        "sequential_cpu_offload": bool(memory["sequential_cpu_offload"]),
        "attention_backend": str(memory["attention_backend"]),
        "attention_slicing": bool(memory["attention_slicing"]),
        "vae_slicing": bool(memory["vae_slicing"]),
        "vae_tiling": bool(memory["vae_tiling"]),
        "local_files_only": bool(model["local_files_only"]),
        "timeout_seconds": int(execution["per_attempt_timeout_seconds"]),
        "model_load_succeeded": False,
        "inference_started": False,
        "inference_completed": False,
        "timed_out": False,
        "output_generated": False,
        "output_geometry_valid": False,
        "outside_mask_changed_pixels": None,
        "technical_validation_passed": False,
        "model_load_seconds": None,
        "inference_seconds": None,
        "runtime_seconds": None,
        "gpu_peak_memory_bytes": None,
        "projected_primary_hours": None,
        "projected_comparable_hours": None,
        "availability_state": "feasibility_only",
        "status": "planned",
        "failure_type": "none",
        "worker_return_code": None,
        "error_type": "",
        "error_message": "",
        "issue": "",
    }
    frame = pd.DataFrame([attempt], columns=SDXL_FEASIBILITY_ATTEMPT_COLUMNS)
    if len(frame) != int(config["scope"]["current_attempt_count"]):
        raise ValueError("Generated attempt plan does not match the declared scope")
    return frame


def materialize_attempt_input_checksums(
    attempts: pd.DataFrame,
    *,
    project_root: str | Path,
) -> pd.DataFrame:
    """Validate current inputs and attach their full checksums."""
    result = attempts.copy()
    root = Path(project_root).resolve()
    for index, row in result.iterrows():
        input_path = (root / str(row["input_image_path"])).resolve()
        mask_path = (root / str(row["mask_or_effect_path"])).resolve()
        if not input_path.is_file() or not mask_path.is_file():
            missing = [str(path) for path in (input_path, mask_path) if not path.is_file()]
            raise FileNotFoundError(f"SDXL feasibility inputs are missing: {missing}")
        result.at[index, "input_sha256"] = calculate_file_sha256(input_path)
        result.at[index, "mask_sha256"] = calculate_file_sha256(mask_path)
    return result


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def build_worker_job(
    attempt: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    project_root: str | Path,
    work_directory: str | Path,
) -> tuple[dict[str, Any], Path, Path, Path]:
    """Build one explicit worker job and its owned work paths."""
    root = Path(project_root).resolve()
    work = Path(work_directory).resolve()
    attempt_id = str(attempt["attempt_id"])
    job_path = work / f"{attempt_id}.job.json"
    result_path = work / f"{attempt_id}.result.json"
    output_path = work / f"{attempt_id}.png"
    model = config["model"]
    memory = config["memory_strategy"]
    payload = {
        "job_schema_version": "sdxl_worker_job.v1",
        "attempt_id": attempt_id,
        "input_path": str((root / str(attempt["input_image_path"])).resolve()),
        "mask_path": str((root / str(attempt["mask_or_effect_path"])).resolve()),
        "output_path": str(output_path),
        "hf_model_id": str(attempt["hf_model_id"]),
        "model_revision": str(attempt["model_revision"]),
        "local_files_only": bool(attempt["local_files_only"]),
        "precision": str(attempt["precision"]),
        "scheduler": str(attempt["scheduler"]),
        "prompt": str(attempt["prompt"]),
        "negative_prompt": str(attempt["negative_prompt"]),
        "seed": int(attempt["seed"]),
        "num_inference_steps": int(attempt["num_inference_steps"]),
        "guidance_scale": float(attempt["guidance_scale"]),
        "strength": float(attempt["strength"]),
        "inference_width": int(attempt["inference_width"]),
        "inference_height": int(attempt["inference_height"]),
        "output_width": int(attempt["output_width"]),
        "output_height": int(attempt["output_height"]),
        "mask_threshold": int(model["mask_threshold"]),
        "compositing_policy": str(model["compositing_policy"]),
        "safety_checker_policy": str(model["safety_checker_policy"]),
        "model_cpu_offload": bool(memory["model_cpu_offload"]),
        "sequential_cpu_offload": bool(memory["sequential_cpu_offload"]),
        "attention_slicing": bool(memory["attention_slicing"]),
        "vae_slicing": bool(memory["vae_slicing"]),
        "vae_tiling": bool(memory["vae_tiling"]),
        "allow_tf32": bool(memory["allow_tf32"]),
    }
    return payload, job_path, result_path, output_path


@dataclass(frozen=True)
class WorkerProcessResult:
    """Outcome of the parent-side process watchdog."""

    timed_out: bool
    return_code: int | None
    runtime_seconds: float
    stdout: str
    stderr: str


def run_worker_process(
    command: Sequence[str],
    *,
    timeout_seconds: float,
    cwd: str | Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> WorkerProcessResult:
    """Run one owned worker and enforce a hard wall-clock timeout."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    started = perf_counter()
    process = subprocess.Popen(
        list(command),
        cwd=None if cwd is None else str(cwd),
        env=None if environment is None else dict(environment),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=creationflags,
        start_new_session=(os.name != "nt"),
    )
    try:
        stdout, stderr = process.communicate(timeout=float(timeout_seconds))
        timed_out = False
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        timed_out = True
    return WorkerProcessResult(
        timed_out=timed_out,
        return_code=process.returncode,
        runtime_seconds=round(perf_counter() - started, 3),
        stdout=stdout,
        stderr=stderr,
    )


def _worker_environment(project_root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    source_path = str((project_root / "src").resolve())
    existing = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = source_path if not existing else source_path + os.pathsep + existing
    return environment


def _compact_process_issue(process_result: WorkerProcessResult) -> str:
    parts = []
    if process_result.stdout.strip():
        parts.append("stdout=" + process_result.stdout.strip()[-1000:])
    if process_result.stderr.strip():
        parts.append("stderr=" + process_result.stderr.strip()[-2000:])
    return " | ".join(parts)


def execute_feasibility_attempt(
    attempt: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    project_root: str | Path,
    work_directory: str | Path,
    python_executable: str | Path | None = None,
) -> tuple[dict[str, Any], tuple[Path, ...]]:
    """Execute one attempt in a child process and return its audit record."""
    root = Path(project_root).resolve()
    payload, job_path, result_path, output_path = build_worker_job(
        attempt, config, project_root=root, work_directory=work_directory
    )
    for stale in (job_path, result_path, output_path):
        if stale.exists() and stale.is_file():
            stale.unlink()
    _atomic_write_json(job_path, payload)
    command = [
        str(python_executable or sys.executable), "-m",
        str(config["execution"]["worker_module"]), "--job", str(job_path),
        "--result", str(result_path),
    ]
    process_result = run_worker_process(
        command,
        timeout_seconds=float(attempt["timeout_seconds"]),
        cwd=root,
        environment=_worker_environment(root),
    )
    record = dict(attempt)
    record["runtime_seconds"] = process_result.runtime_seconds
    record["worker_return_code"] = process_result.return_code

    if process_result.timed_out:
        record.update(
            {
                "timed_out": True,
                "status": "timed_out",
                "failure_type": "runtime_guardrail",
                "error_type": "TimeoutExpired",
                "error_message": (
                    f"Isolated SDXL worker exceeded {int(attempt['timeout_seconds'])} seconds and was terminated"
                ),
                "issue": _compact_process_issue(process_result),
            }
        )
        return record, (job_path, result_path, output_path)

    if not result_path.is_file():
        record.update(
            {
                "status": "failed",
                "failure_type": "worker_failure",
                "error_type": "MissingWorkerResult",
                "error_message": "SDXL worker exited without writing its result contract",
                "issue": _compact_process_issue(process_result),
            }
        )
        return record, (job_path, result_path, output_path)

    try:
        with result_path.open("r", encoding="utf-8-sig") as handle:
            worker = json.load(handle)
        if worker.get("result_schema_version") != "sdxl_worker_result.v1":
            raise ValueError("Unsupported or missing SDXL worker result schema")
    except Exception as exc:
        record.update(
            {
                "status": "failed", "failure_type": "worker_failure",
                "error_type": type(exc).__name__, "error_message": str(exc),
                "issue": _compact_process_issue(process_result),
            }
        )
        return record, (job_path, result_path, output_path)

    transferable = {
        "actual_device", "gpu_name", "gpu_total_memory_bytes",
        "model_load_succeeded", "inference_started", "inference_completed",
        "timed_out", "output_generated", "output_geometry_valid",
        "outside_mask_changed_pixels", "technical_validation_passed",
        "model_load_seconds", "inference_seconds", "gpu_peak_memory_bytes",
        "status", "failure_type", "error_type", "error_message", "issue",
    }
    for key in transferable:
        if key in worker:
            record[key] = worker[key]
    if record["status"] == "completed":
        runtime = float(record["runtime_seconds"])
        record["projected_primary_hours"] = round(
            runtime * int(config["scope"]["eligible_primary_case_count"]) / 3600.0, 3
        )
        record["projected_comparable_hours"] = round(
            runtime * int(config["scope"]["comparable_candidate_count"]) / 3600.0, 3
        )
    if process_result.return_code not in (0, None) and record["status"] == "completed":
        record.update(
            {
                "status": "failed", "failure_type": "worker_failure",
                "error_type": "UnexpectedWorkerReturnCode",
                "error_message": f"Worker returned {process_result.return_code}",
            }
        )
    return record, (job_path, result_path, output_path)


def derive_availability_state(attempts: pd.DataFrame) -> str:
    """Derive the explicit Notebook 12 availability state."""
    if attempts.empty:
        return "failed"
    failures = set(attempts["failure_type"].astype(str))
    statuses = set(attempts["status"].astype(str))
    if "completed" in statuses:
        return "feasibility_only"
    if failures & {"runtime_guardrail", "cuda_out_of_memory"}:
        return "feasibility_only"
    if "model_unavailable" in failures:
        return "unavailable"
    return "failed"


def _must_stop(record: Mapping[str, Any], config: Mapping[str, Any]) -> bool:
    failure = str(record.get("failure_type", "none"))
    execution = config["execution"]
    return (
        (failure == "runtime_guardrail" and bool(execution["stop_after_timeout"]))
        or (failure == "cuda_out_of_memory" and bool(execution["stop_after_cuda_oom"]))
        or (
            failure in {"model_unavailable", "model_load_failure"}
            and bool(execution["stop_after_model_failure"])
        )
    )


def execute_feasibility_plan(
    attempts: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    project_root: str | Path,
    work_directory: str | Path,
    python_executable: str | Path | None = None,
) -> tuple[pd.DataFrame, tuple[Path, ...]]:
    """Execute attempts sequentially and make every guardrail omission explicit."""
    if len(attempts) > int(config["execution"]["maximum_current_attempts"]):
        raise ValueError("Attempt plan exceeds the configured maximum")
    records: list[dict[str, Any]] = []
    owned_paths: list[Path] = []
    stop_reason = ""
    total = len(attempts)
    progress_interval = int(config["execution"]["progress_interval_attempts"])
    for offset, (_, row) in enumerate(attempts.iterrows(), start=1):
        if stop_reason:
            skipped = dict(row)
            skipped.update(
                {
                    "status": "skipped", "failure_type": "skipped_after_guardrail",
                    "error_type": "", "error_message": "", "issue": stop_reason,
                }
            )
            records.append(skipped)
        else:
            record, paths = execute_feasibility_attempt(
                row.to_dict(), config, project_root=project_root,
                work_directory=work_directory, python_executable=python_executable,
            )
            records.append(record)
            owned_paths.extend(paths)
            if _must_stop(record, config):
                stop_reason = (
                    f"No later SDXL attempt was executed after {record['failure_type']} "
                    f"in {record['attempt_id']}"
                )
        if offset % progress_interval == 0 or offset == total:
            print(f"SDXL feasibility progress: {offset}/{total} attempt rows resolved")

    result = pd.DataFrame(records, columns=SDXL_FEASIBILITY_ATTEMPT_COLUMNS)
    result["availability_state"] = derive_availability_state(result)
    validation = validate_dataframe(result, SDXL_FEASIBILITY_ATTEMPTS_SCHEMA)
    if not validation.passed:
        raise ValueError(f"SDXL feasibility result violates its schema: {validation.to_dict()}")
    return result, tuple(dict.fromkeys(owned_paths))


def cleanup_owned_worker_files(paths: Sequence[str | Path]) -> tuple[str, ...]:
    """Remove only explicitly returned worker-owned files."""
    removed: list[str] = []
    for value in paths:
        path = Path(value)
        if path.exists() and path.is_file():
            path.unlink()
            removed.append(path.as_posix())
    parents = {Path(value).parent for value in paths}
    for parent in sorted(parents, key=lambda item: len(item.parts), reverse=True):
        if parent.exists() and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
    return tuple(removed)


def render_feasibility_report(
    attempts: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    package_versions: Mapping[str, str],
    hardware: Mapping[str, Any],
) -> str:
    """Render the compact standalone Markdown feasibility report."""
    state = derive_availability_state(attempts)
    row = attempts.iloc[0].to_dict()
    legacy = config["legacy_evidence"]["observations"]
    runtime = row.get("runtime_seconds")
    runtime_text = "not available" if pd.isna(runtime) else f"{float(runtime):.1f} seconds"
    projections = (
        "Not calculated because the quality-oriented probe did not complete."
        if pd.isna(row.get("projected_primary_hours"))
        else (
            f"Approximately {float(row['projected_primary_hours']):.1f} hours for 410 primary "
            f"cases and {float(row['projected_comparable_hours']):.1f} hours for 1,010 comparable candidates."
        )
    )
    package_text = ", ".join(f"{key} {value}" for key, value in sorted(package_versions.items()))
    hardware_text = ", ".join(f"{key}={value}" for key, value in sorted(hardware.items()))
    legacy_lines = "\n".join(
        f"- `{item['label']}`: {item['runtime_seconds']} seconds; {item['outcome'].replace('_', ' ')}."
        for item in legacy
    )
    limitations = "\n".join(f"- {item}" for item in config["known_limitations"])
    return f"""# SDXL feasibility report

## Decision

Validated availability state: **`{state}`**.

Notebook 12 remains a feasibility audit. It does not create SDXL candidate rows,
restoration manifests, or placeholder metric rows. The result is evidence about
practical execution on the recorded hardware, not a ranking of SDXL restoration quality.

## Current quality-oriented probe

- Status: `{row['status']}`
- Failure classification: `{row['failure_type']}`
- Runtime including model loading: {runtime_text}
- Guardrail: {int(row['timeout_seconds'])} seconds, enforced around an isolated worker
- Model: `{row['hf_model_id']}` at revision `{row['model_revision']}`
- Configuration: {int(row['inference_width'])} x {int(row['inference_height'])}, {int(row['num_inference_steps'])} steps, guidance {float(row['guidance_scale'])}, strength {float(row['strength'])}, seed {int(row['seed'])}
- Memory strategy: `{row['memory_strategy_id']}`
- Technical validation passed: `{bool(row['technical_validation_passed'])}`
- Error: `{row['error_type']}: {row['error_message']}`

## Runtime projection

{projections}

The projection is a simple wall-clock extrapolation from one probe and includes
one-time model loading, so it is deliberately conservative and is not a benchmark.

## Environment

- Hardware: {hardware_text}
- Packages: {package_text}

## Legacy context

The deleted pre-refactor Notebook 25 is retained only through commit
`{config['legacy_evidence']['source_git_commit']}` as contextual evidence:

{legacy_lines}

These observations are not included as current attempt rows and are not used to
claim that SDXL is intrinsically poor. They show that reduced-step 512 px probes
either under-filled the region or introduced visible unrelated changes.

## Interpretation and downstream contract

- A timeout or CUDA out-of-memory event is classified as a hardware/runtime limitation.
- No automatic retry, CPU fallback, lower resolution, or lower step count is attempted.
- Notebooks 13-35 must include SDXL only when a future validated run reports
  `full_evaluation_complete` or an explicitly supported `partial_evaluation`.
- The present `{state}` state therefore excludes SDXL from unified metric computation.

## Limitations

{limitations}
"""


# ---------------------------------------------------------------------------
# Version 2 partial-evaluation API. The legacy feasibility functions above are
# retained only so the committed v1 audit remains reproducible.
# ---------------------------------------------------------------------------

def load_sdxl_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the approved bounded SDXL v2 contract."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise TypeError("SDXL configuration must contain a YAML mapping")
    _require_keys(
        config,
        {
            "config_schema_version", "config_version", "dataset", "inputs",
            "output", "model", "mask_policy", "prompt_policy",
            "memory_strategy", "execution", "selection", "scope",
            "legacy_evidence", "availability", "schema_versions",
            "known_limitations",
        },
        label="SDXL configuration",
    )
    if config["config_schema_version"] != SDXL_CONFIG_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported SDXL config schema {config['config_schema_version']!r}; "
            f"expected {SDXL_CONFIG_SCHEMA_VERSION!r}"
        )
    model = config["model"]
    execution = config["execution"]
    memory = config["memory_strategy"]
    selection = config["selection"]
    scope = config["scope"]
    _require_keys(
        execution,
        {
            "mode", "global_budget_seconds", "per_case_timeout_seconds",
            "minimum_seconds_to_start_case", "stop_after_timeout",
            "stop_after_cuda_oom", "stop_after_model_failure",
            "retry_failed_attempts", "progress_poll_seconds",
            "checkpoint_interval_cases", "preserve_completed_outputs",
            "worker_module", "timeout_policy_id", "checkpoint_policy_id",
        },
        label="execution",
    )
    if execution["mode"] != "partial_evaluation":
        raise ValueError("Notebook 12 v2 authorizes partial_evaluation mode only")
    if int(execution["global_budget_seconds"]) != 7200:
        raise ValueError("The approved global SDXL budget is exactly 7200 seconds")
    if int(execution["per_case_timeout_seconds"]) != 900:
        raise ValueError("The approved per-case watchdog is exactly 900 seconds")
    if int(execution["minimum_seconds_to_start_case"]) <= 0:
        raise ValueError("minimum_seconds_to_start_case must be positive")
    if bool(execution["retry_failed_attempts"]):
        raise ValueError("Automatic SDXL retries are prohibited")
    if not bool(memory["persistent_pipeline"]):
        raise ValueError("The approved worker must reuse one persistent pipeline")
    if not bool(memory["model_cpu_offload"]) or bool(memory["sequential_cpu_offload"]):
        raise ValueError("The approved memory policy requires model CPU offload only")
    if memory["attention_backend"] != "pytorch_sdpa" or bool(memory["attention_slicing"]):
        raise ValueError("The approved attention policy is unsliced PyTorch SDPA")
    if model["requested_device"] != "cuda" or bool(model["allow_cpu_fallback"]):
        raise ValueError("The SDXL partial evaluation requires CUDA without CPU fallback")
    if model["precision"] != "float16":
        raise ValueError("The approved precision is float16")
    if (int(model["inference_width"]), int(model["inference_height"])) != (768, 768):
        raise ValueError("The approved inference geometry is 768 x 768")
    if int(model["num_inference_steps"]) != 30:
        raise ValueError("The approved quality policy uses 30 denoising steps")
    cases = selection["cases"]
    case_ids = [str(item["case_id"]) for item in cases]
    selection_ranks = [int(item["selection_rank"]) for item in cases]
    execution_orders = [int(item["execution_order"]) for item in cases]
    if len(cases) != 10 or len(set(case_ids)) != 10:
        raise ValueError("The approved partial scope contains ten unique cases")
    if sorted(selection_ranks) != list(range(1, 11)):
        raise ValueError("selection_rank must be the integers 1 through 10")
    if sorted(execution_orders) != list(range(1, 11)):
        raise ValueError("execution_order must be the integers 1 through 10")
    if int(selection["painting_count"]) != 5:
        raise ValueError("The approved independent-unit count is five paintings")
    if bool(scope["full_execution_authorized"]) or not bool(scope["partial_execution_authorized"]):
        raise ValueError("Scope authorization must be partial-only")
    if int(scope["scheduled_candidate_count"]) != 10:
        raise ValueError("scheduled_candidate_count must equal ten")
    return config


def select_partial_evaluation_scope(
    worklist: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select the predeclared ten cases and preserve both declared orders."""
    declarations = pd.DataFrame(config["selection"]["cases"])
    selected = declarations.merge(worklist, on="case_id", how="left", validate="one_to_one")
    if selected["painting_id"].isna().any():
        missing = selected.loc[selected["painting_id"].isna(), "case_id"].tolist()
        raise ValueError(f"Predeclared SDXL cases are absent from the worklist: {missing}")
    if selected["painting_id"].nunique() != int(config["selection"]["painting_count"]):
        raise ValueError("Selected cases do not span the approved five paintings")
    canonical = selected["experiment_id"].astype(str).eq("canonical_missing_region")
    if int(canonical.sum()) != int(config["selection"]["canonical_case_count"]):
        raise ValueError("Canonical-case count disagrees with the contract")
    if int((~canonical).sum()) != int(config["selection"]["synthetic_case_count"]):
        raise ValueError("Synthetic-case count disagrees with the contract")
    if selected.groupby("painting_id").size().to_dict() != {
        "p001": 2, "p018": 2, "p026": 2, "p039": 2, "p043": 2,
    }:
        raise ValueError("Each approved painting must contribute exactly two nested cases")
    return selected.sort_values("execution_order", kind="stable").reset_index(drop=True)


def validate_cross_method_comparability(
    selected_scope: pd.DataFrame,
    telea: pd.DataFrame,
    lama: pd.DataFrame,
    stable_diffusion: pd.DataFrame,
) -> pd.DataFrame:
    """Audit case coverage in the three already-completed restoration branches."""
    target = set(selected_scope["case_id"].astype(str))
    sd_primary = stable_diffusion.loc[
        stable_diffusion["prompt_variant_id"].astype(str).eq("p00_generic")
        & pd.to_numeric(stable_diffusion["seed"], errors="coerce").eq(2026)
        & stable_diffusion["status"].astype(str).eq("completed")
    ]
    sources = {
        "opencv_telea": telea.loc[telea["status"].astype(str).eq("completed")],
        "lama": lama.loc[lama["status"].astype(str).eq("completed")],
        "stable_diffusion_primary": sd_primary,
    }
    records = []
    for method, table in sources.items():
        counts = table["case_id"].astype(str).value_counts()
        for case_id in sorted(target):
            records.append({
                "method_id": method,
                "case_id": case_id,
                "matching_completed_rows": int(counts.get(case_id, 0)),
                "coverage_passed": int(counts.get(case_id, 0)) == 1,
            })
    audit = pd.DataFrame(records)
    failures = audit.loc[~audit["coverage_passed"]]
    if not failures.empty:
        raise ValueError(
            "Cross-method case comparability failed: "
            + failures[["method_id", "case_id", "matching_completed_rows"]].to_dict("records").__repr__()
        )
    return audit


def _partial_candidate_id(case_id: str, config: Mapping[str, Any]) -> str:
    prompt_id = str(config["prompt_policy"]["prompt_variant_id"])
    seed = int(config["model"]["seed"])
    token = hashlib.sha256(f"{case_id}|{prompt_id}|{seed}".encode()).hexdigest()[:12]
    return f"sdxl__{token}__{prompt_id}__seed{seed}"


def build_partial_candidate_plan(
    selected_scope: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the normalized ten-row candidate plan in execution order."""
    model = config["model"]
    prompt = config["prompt_policy"]
    execution = config["execution"]
    fingerprint = configuration_fingerprint(config)
    output_root = Path("outputs") / str(config["output"]["notebook_stem"])
    records: list[dict[str, Any]] = []
    for _, row in selected_scope.sort_values("execution_order").iterrows():
        canonical = str(row["experiment_id"]) == "canonical_missing_region"
        threshold = int(
            config["mask_policy"][
                "canonical_missing_region" if canonical else "synthetic_degradation"
            ]["threshold"]
        )
        candidate_id = _partial_candidate_id(str(row["case_id"]), config)
        restored = (
            output_root / str(config["output"]["restored_directory"])
            / str(row["experiment_id"]) / str(row["case_id"])
            / f"{candidate_id}.png"
        ).as_posix()
        record = {
            "candidate_id": candidate_id,
            "candidate_index": 1,
            "selection_rank": int(row["selection_rank"]),
            "execution_order": int(row["execution_order"]),
            "case_id": str(row["case_id"]),
            "painting_id": str(row["painting_id"]),
            "category": str(row["category"]),
            "experiment_id": str(row["experiment_id"]),
            "damage_or_degradation_type": str(row["damage_or_degradation_type"]),
            "mask_or_effect_id": str(row["mask_or_effect_id"]),
            "input_image_path": str(row["input_image_path"]),
            "clean_image_path": str(row["clean_image_path"]),
            "mask_or_effect_path": str(row["mask_or_effect_path"]),
            "input_sha256": None,
            "mask_sha256": None,
            "model_id": str(model["model_id"]),
            "hf_model_id": str(model["hf_model_id"]),
            "model_revision": str(model["model_revision"]),
            "configuration_id": str(model["configuration_id"]),
            "prompt_policy_id": str(prompt["policy_id"]),
            "prompt_variant_id": str(prompt["prompt_variant_id"]),
            "prompt": str(prompt["prompt"]),
            "negative_prompt": str(prompt["negative_prompt"]),
            "prompt_metadata_fields_used": "",
            "seed": int(model["seed"]),
            "execution_role": "primary",
            "candidate_selection_policy": str(config["selection"]["policy_id"]),
            "num_inference_steps": int(model["num_inference_steps"]),
            "guidance_scale": float(model["guidance_scale"]),
            "strength": float(model["strength"]),
            "scheduler": str(model["scheduler"]),
            "precision": str(model["precision"]),
            "device": None,
            "inference_width": int(model["inference_width"]),
            "inference_height": int(model["inference_height"]),
            "output_width": int(model["output_width"]),
            "output_height": int(model["output_height"]),
            "mask_policy_id": str(config["mask_policy"]["policy_id"]),
            "mask_threshold": threshold,
            "compositing_policy": str(model["compositing_policy"]),
            "safety_checker_policy": str(model["safety_checker_policy"]),
            "execution_action": "pending",
            "restored_path": restored,
            "restored_sha256": None,
            "runtime_seconds": None,
            "model_load_seconds": None,
            "inference_seconds": None,
            "gpu_total_memory_bytes": None,
            "gpu_memory_before_bytes": None,
            "gpu_memory_after_bytes": None,
            "gpu_peak_memory_bytes": None,
            "global_budget_seconds": int(execution["global_budget_seconds"]),
            "per_case_timeout_seconds": int(execution["per_case_timeout_seconds"]),
            "budget_seconds_before_attempt": None,
            "budget_seconds_after_attempt": None,
            "output_geometry_valid": False,
            "outside_mask_changed_pixels": None,
            "technical_validation_passed": False,
            "retry_count": 0,
            "attempt_count": 0,
            "configuration_fingerprint": fingerprint,
            "started_at_utc": None,
            "completed_at_utc": None,
            "generator_name": SDXL_HELPER_NAME,
            "generator_version": SDXL_HELPER_VERSION,
            "availability_state": "pending",
            "status": "planned",
            "failure_type": "none",
            "worker_return_code": None,
            "error_type": None,
            "error_message": None,
            "issue": None,
        }
        records.append(record)
    plan = pd.DataFrame(records, columns=SDXL_PARTIAL_CANDIDATE_COLUMNS)
    validation = validate_dataframe(plan, SDXL_PARTIAL_CANDIDATES_SCHEMA)
    if not validation.passed:
        raise ValueError(f"SDXL candidate plan violates its schema: {validation.to_dict()}")
    return plan



def materialize_partial_input_checksums(
    candidates: pd.DataFrame,
    *,
    project_root: str | Path,
) -> pd.DataFrame:
    """Resolve all planned inputs and record immutable checksums."""
    root = Path(project_root).resolve()
    result = candidates.copy()
    for index, row in result.iterrows():
        input_path = root / str(row["input_image_path"])
        mask_path = root / str(row["mask_or_effect_path"])
        if not input_path.is_file() or not mask_path.is_file():
            raise FileNotFoundError(
                f"Missing SDXL input for {row['case_id']}: {input_path} / {mask_path}"
            )
        result.at[index, "input_sha256"] = calculate_file_sha256(input_path)
        result.at[index, "mask_sha256"] = calculate_file_sha256(mask_path)
    validation = validate_dataframe(result, SDXL_PARTIAL_CANDIDATES_SCHEMA)
    if not validation.passed:
        raise ValueError(f"Checksummed SDXL plan violates its schema: {validation.to_dict()}")
    return result


def _atomic_write_csv_with_retries(
    frame: pd.DataFrame,
    path: str | Path,
    *,
    attempts: int = 12,
    delay_seconds: float = 0.25,
) -> Path:
    """Persist a CSV atomically with bounded Windows file-lock retries."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error: OSError | None = None
    for number in range(1, attempts + 1):
        temporary = destination.with_name(
            f"{destination.name}.tmp.{os.getpid()}.{time.time_ns()}"
        )
        try:
            frame.to_csv(temporary, index=False)
            os.replace(temporary, destination)
            return destination
        except OSError as exc:
            last_error = exc
            if temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass
            if number < attempts:
                time.sleep(delay_seconds)
    raise PermissionError(
        f"Could not atomically replace {destination} after {attempts} attempts"
    ) from last_error


def write_partial_checkpoint(frame: pd.DataFrame, path: str | Path) -> Path:
    """Validate and atomically checkpoint the full ten-row candidate state."""
    normalized = frame.reindex(columns=SDXL_PARTIAL_CANDIDATE_COLUMNS)
    validation = validate_dataframe(normalized, SDXL_PARTIAL_CANDIDATES_SCHEMA)
    if not validation.passed:
        raise ValueError(f"Refusing invalid SDXL checkpoint: {validation.to_dict()}")
    return _atomic_write_csv_with_retries(normalized, path)


def derive_partial_availability_state(candidates: pd.DataFrame) -> str:
    """Derive availability without turning runtime limits into quality evidence."""
    if candidates.empty:
        return "failed"
    valid = (
        candidates["status"].astype(str).eq("completed")
        & candidates["technical_validation_passed"].astype(str).str.lower().eq("true")
    )
    if bool(valid.any()):
        return "partial_evaluation"
    failures = set(candidates["failure_type"].astype(str))
    if failures & {
        "runtime_guardrail", "global_budget_exhausted",
        "cuda_out_of_memory", "not_started_global_budget",
    }:
        return "feasibility_only"
    if "model_unavailable" in failures:
        return "unavailable"
    return "failed"


def build_batch_worker_job(
    candidates: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    project_root: str | Path,
    notebook_output_root: str | Path,
) -> tuple[dict[str, Any], Path, Path, Path, Path]:
    """Create the persistent-worker job contract and resolve owned work paths."""
    root = Path(project_root).resolve()
    output_root = Path(notebook_output_root).resolve()
    output = config["output"]
    work = output_root / str(output["work_directory"])
    work.mkdir(parents=True, exist_ok=True)
    job_path = output_root / str(output["worker_job_path"])
    result_path = output_root / str(output["worker_result_path"])
    checkpoint_path = output_root / str(output["checkpoint_path"])
    progress_path = output_root / str(output["progress_path"])
    payload = {
        "job_schema_version": "sdxl_batch_worker_job.v1",
        "helper_version": SDXL_HELPER_VERSION,
        "project_root": str(root),
        "notebook_output_root": str(output_root),
        "result_path": str(result_path),
        "checkpoint_path": str(checkpoint_path),
        "progress_path": str(progress_path),
        "model": dict(config["model"]),
        "memory_strategy": dict(config["memory_strategy"]),
        "execution": dict(config["execution"]),
        "candidates": candidates.sort_values("execution_order").to_dict("records"),
    }
    return payload, job_path, result_path, checkpoint_path, progress_path


@dataclass(frozen=True)
class BatchWorkerProcessResult:
    """Parent-watchdog result for one persistent SDXL batch worker."""

    return_code: int | None
    runtime_seconds: float
    termination_reason: str
    current_candidate_id: str
    stdout: str
    stderr: str

    @property
    def terminated(self) -> bool:
        return bool(self.termination_reason)


def _read_json_if_present(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}


def run_batch_worker_process(
    command: Sequence[str],
    *,
    progress_path: str | Path,
    global_budget_seconds: float,
    per_case_timeout_seconds: float,
    poll_seconds: float = 1.0,
    cwd: str | Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> BatchWorkerProcessResult:
    """Run the persistent worker under global and heartbeat-based hard limits."""
    started = perf_counter()
    progress_file = Path(progress_path)
    process = subprocess.Popen(
        list(command),
        cwd=None if cwd is None else str(cwd),
        env=None if environment is None else dict(environment),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    reason = ""
    current_candidate = ""
    last_notice_elapsed = -60.0
    last_signature: tuple[str, int, str] | None = None
    while process.poll() is None:
        elapsed = perf_counter() - started
        progress = _read_json_if_present(progress_file)
        current_candidate = str(progress.get("current_candidate_id", "") or "")
        case_started = progress.get("case_started_epoch_seconds")
        status = str(progress.get("status", "starting") or "starting")
        resolved = int(progress.get("resolved_count", 0) or 0)
        signature = (status, resolved, current_candidate)
        heartbeat_due = elapsed - last_notice_elapsed >= 60.0
        if signature != last_signature or heartbeat_due:
            case_elapsed = (
                0.0
                if case_started in (None, "")
                else max(0.0, time.time() - float(case_started))
            )
            active = current_candidate or "none"
            print(
                "SDXL watchdog: "
                f"status={status}; resolved={resolved}/10; active={active}; "
                f"batch_elapsed={elapsed:.1f}s; case_elapsed={case_elapsed:.1f}s",
                flush=True,
            )
            last_signature = signature
            last_notice_elapsed = elapsed
        if elapsed >= float(global_budget_seconds):
            reason = "global_budget_exhausted"
        elif current_candidate and case_started not in (None, ""):
            if time.time() - float(case_started) >= float(per_case_timeout_seconds):
                reason = "runtime_guardrail"
        if reason:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
            break
        time.sleep(max(0.05, float(poll_seconds)))
    stdout, stderr = process.communicate()
    return BatchWorkerProcessResult(
        return_code=process.returncode,
        runtime_seconds=round(perf_counter() - started, 3),
        termination_reason=reason,
        current_candidate_id=current_candidate,
        stdout=stdout,
        stderr=stderr,
    )


def _load_latest_partial_checkpoint(
    plan: pd.DataFrame,
    checkpoint_path: Path,
    progress_path: Path,
) -> pd.DataFrame:
    progress = _read_json_if_present(progress_path)
    candidates = [
        Path(str(progress.get("latest_checkpoint_path", ""))),
        checkpoint_path,
    ]
    for path in candidates:
        if str(path) not in {"", "."} and path.is_file():
            frame = pd.read_csv(path, keep_default_na=False)
            for column in SDXL_PARTIAL_CANDIDATE_COLUMNS:
                if column not in frame:
                    frame[column] = None
            return frame.reindex(columns=SDXL_PARTIAL_CANDIDATE_COLUMNS)
    return plan.copy()


def finalize_partial_execution(
    plan: pd.DataFrame,
    process_result: BatchWorkerProcessResult,
    *,
    checkpoint_path: str | Path,
    progress_path: str | Path,
) -> pd.DataFrame:
    """Reconcile the latest checkpoint after completion or enforced termination."""
    result = _load_latest_partial_checkpoint(
        plan, Path(checkpoint_path), Path(progress_path)
    )
    unresolved = result["status"].astype(str).eq("planned")
    if process_result.termination_reason and process_result.current_candidate_id:
        current = result["candidate_id"].astype(str).eq(process_result.current_candidate_id)
        result.loc[current & unresolved, [
            "execution_action", "status", "failure_type", "error_type", "error_message", "issue"
        ]] = [
            "failed",
            "timed_out" if process_result.termination_reason == "runtime_guardrail" else "failed",
            process_result.termination_reason,
            "TimeoutExpired",
            "The isolated persistent SDXL worker was terminated by the parent watchdog.",
            f"termination_reason={process_result.termination_reason}",
        ]
        unresolved = result["status"].astype(str).eq("planned")
    if bool(unresolved.any()):
        global_stop = process_result.termination_reason == "global_budget_exhausted"
        failure = "not_started_global_budget" if global_stop else "skipped_after_guardrail"
        result.loc[unresolved, [
            "execution_action", "status", "failure_type", "error_type", "error_message", "issue"
        ]] = [
            "skipped", "skipped", failure, "", "",
            f"worker_return_code={process_result.return_code}; termination={process_result.termination_reason or 'worker_exit'}",
        ]
    result["worker_return_code"] = result["worker_return_code"].where(
        result["worker_return_code"].notna(), process_result.return_code
    )
    state = derive_partial_availability_state(result)
    result["availability_state"] = state
    validation = validate_dataframe(result, SDXL_PARTIAL_CANDIDATES_SCHEMA)
    if not validation.passed:
        raise ValueError(f"Final SDXL candidate state violates schema: {validation.to_dict()}")
    return result


def execute_partial_evaluation_plan(
    candidates: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    project_root: str | Path,
    notebook_output_root: str | Path,
    python_executable: str | Path | None = None,
) -> tuple[pd.DataFrame, BatchWorkerProcessResult, tuple[Path, ...]]:
    """Execute the bounded plan once and return checkpointed normalized records."""
    root = Path(project_root).resolve()
    payload, job_path, result_path, checkpoint_path, progress_path = build_batch_worker_job(
        candidates, config, project_root=root, notebook_output_root=notebook_output_root
    )
    for path in (job_path, result_path, checkpoint_path, progress_path):
        if path.is_file():
            path.unlink()
    write_partial_checkpoint(candidates, checkpoint_path)
    _atomic_write_json(job_path, payload)
    command = [
        str(python_executable or sys.executable), "-m",
        str(config["execution"]["worker_module"]),
        "--job", str(job_path), "--result", str(result_path),
    ]
    execution = config["execution"]
    process_result = run_batch_worker_process(
        command,
        progress_path=progress_path,
        global_budget_seconds=float(execution["global_budget_seconds"]),
        per_case_timeout_seconds=float(execution["per_case_timeout_seconds"]),
        poll_seconds=float(execution["progress_poll_seconds"]),
        cwd=root,
        environment=_worker_environment(root),
    )
    result = finalize_partial_execution(
        candidates,
        process_result,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
    )
    owned = (job_path, result_path, checkpoint_path, progress_path)
    return result, process_result, owned


def render_partial_evaluation_report(
    candidates: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    package_versions: Mapping[str, str],
    hardware: Mapping[str, Any],
) -> str:
    """Render a compact report that keeps partial coverage explicit."""
    state = derive_partial_availability_state(candidates)
    counts = candidates["status"].astype(str).value_counts().to_dict()
    valid = candidates.loc[
        candidates["status"].astype(str).eq("completed")
        & candidates["technical_validation_passed"].astype(str).str.lower().eq("true")
    ]
    runtime = pd.to_numeric(valid["runtime_seconds"], errors="coerce").dropna()
    runtime_text = "not available" if runtime.empty else (
        f"{runtime.sum():.1f} seconds total; median {runtime.median():.1f} seconds"
    )
    limitations = "\n".join(f"- {item}" for item in config["known_limitations"])
    packages = ", ".join(f"{key} {value}" for key, value in sorted(package_versions.items()))
    device = ", ".join(f"{key}={value}" for key, value in sorted(hardware.items()))
    return f"""# SDXL bounded partial-evaluation report

## Decision

Validated availability state: **`{state}`**.

The notebook predeclared ten cases nested within five paintings, used one generic
prompt and seed 2026, and enforced a 7,200-second global budget plus a 900-second
per-case watchdog. This is a purposive partial evaluation, not a full SDXL branch.

## Execution result

- Scheduled rows: {len(candidates)}
- Technically valid completed rows: {len(valid)}
- Status counts: `{counts}`
- Runtime: {runtime_text}
- Persistent pipeline: `{bool(config['memory_strategy']['persistent_pipeline'])}`
- Automatic retries: `{bool(config['execution']['retry_failed_attempts'])}`
- Environment: {device}
- Packages: {packages}

Only completed rows with exact output geometry and zero changed pixels outside
the binary mask are eligible for downstream metrics. Timeout, out-of-memory,
and budget omissions are runtime evidence, never restoration-quality failures.

## Statistical boundary

The independent unit is the painting (n=5). The two cases per painting are
nested observations and must not be presented as ten independent paintings.
No population-level SDXL claim is supported by this purposive scope.

## Limitations

{limitations}
"""
