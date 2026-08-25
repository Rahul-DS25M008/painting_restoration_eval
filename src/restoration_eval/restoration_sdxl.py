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
from typing import Any, Mapping, Sequence

import pandas as pd
import yaml

from restoration_eval.restoration_stable_diffusion import build_eligible_case_worklist
from restoration_eval.schemas import (
    SDXL_FEASIBILITY_ATTEMPT_COLUMNS,
    SDXL_FEASIBILITY_ATTEMPTS_SCHEMA,
    validate_dataframe,
)


SDXL_HELPER_NAME = "restoration_eval.restoration_sdxl"
SDXL_HELPER_VERSION = "2.0.0"
SDXL_CONFIG_SCHEMA_VERSION = "sdxl_config.v1"


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
