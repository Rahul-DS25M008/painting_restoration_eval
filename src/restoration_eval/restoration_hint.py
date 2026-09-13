"""Production HINT helpers for Notebook 12A.

Torch and the external HINT repository are intentionally imported only by the
isolated worker. Notebook preflight and planning therefore remain lightweight.
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
from time import perf_counter, sleep
from typing import Any, Mapping, Sequence

import pandas as pd
import yaml

from restoration_eval.hint_mat_selection import calculate_file_sha256
from restoration_eval.restoration_lama import build_eligible_case_worklist
from restoration_eval.schemas import RESTORATIONS_COLUMNS


HELPER_NAME = "restoration_eval.restoration_hint"
HELPER_VERSION = "1.0.1"
CONFIG_SCHEMA_VERSION = "hint_config.v1"
MODEL_ID = "hint_places2"

HINT_WORK_COLUMNS = (
    *RESTORATIONS_COLUMNS,
    "painting_id",
    "experiment_id",
    "damage_or_degradation_type",
    "input_image_path",
    "clean_image_path",
    "mask_path",
    "model_load_seconds",
    "inference_seconds",
    "gpu_peak_memory_bytes",
    "output_geometry_valid",
    "outside_mask_changed_pixels",
    "technical_validation_passed",
    "failure_type",
    "error_type",
    "error_message",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def configuration_fingerprint(config: Mapping[str, Any]) -> str:
    payload = json.dumps(
        config, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_hint_config(path: str | Path) -> dict[str, Any]:
    """Load and validate the controlled-300 Notebook 12A contract."""
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise TypeError("Notebook 12A configuration must be a YAML mapping")
    required = {
        "config_schema_version", "config_version", "dataset", "inputs",
        "output", "external_asset", "model", "execution", "expected",
        "smoke", "representative_case_ids", "schema_versions",
        "known_limitations",
    }
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(f"Notebook 12A configuration is missing: {missing}")
    if config["config_schema_version"] != CONFIG_SCHEMA_VERSION:
        raise ValueError("Unsupported Notebook 12A configuration schema")
    if config["dataset"]["dataset_scope"] != "controlled_300":
        raise ValueError("Notebook 12A requires controlled_300")
    if config["model"]["model_id"] != MODEL_ID:
        raise ValueError("Notebook 12A must run hint_places2")
    expected = config["expected"]
    if int(expected["eligible_case_count"]) != 2620:
        raise ValueError("Notebook 12A requires exactly 2,620 eligible cases")
    if sum(map(int, expected["eligible_case_count_by_experiment"].values())) != 2620:
        raise ValueError("Notebook 12A experiment counts do not sum to 2,620")
    if int(expected["zero_control_case_count"]) != 300:
        raise ValueError("Notebook 12A requires exactly 300 zero controls")
    execution = config["execution"]
    if int(execution["progress_interval_cases"]) > 10:
        raise ValueError("HINT progress must print at least every ten cases")
    if not 0 < float(execution["progress_poll_seconds"]) <= 1.0:
        raise ValueError("HINT parent progress polling must be in (0, 1] seconds")
    if bool(execution["retry_failed_attempts"]):
        raise ValueError("Automatic HINT retry is prohibited")
    return config


def _resolve_asset_path(
    config: Mapping[str, Any], kind: str,
    environment: Mapping[str, str] | None = None,
) -> Path:
    values = os.environ if environment is None else environment
    asset = config["external_asset"]
    if kind == "repository":
        variable = asset["repository_environment_variable"]
        default = asset["default_repository_path"]
    elif kind == "checkpoint":
        variable = asset["checkpoint_environment_variable"]
        default = asset["default_checkpoint_path"]
    else:
        raise ValueError(f"Unsupported HINT asset kind: {kind}")
    return Path(values.get(str(variable)) or str(default)).expanduser().resolve()


def _read_git_revision(repository: Path) -> str:
    head = repository / ".git" / "HEAD"
    if not head.is_file():
        return ""
    value = head.read_text(encoding="utf-8-sig").strip()
    if not value.startswith("ref: "):
        return value
    reference = value[5:].strip()
    loose = repository / ".git" / reference
    if loose.is_file():
        return loose.read_text(encoding="utf-8-sig").strip()
    packed = repository / ".git" / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith(("#", "^")) or " " not in line:
                continue
            revision, name = line.split(" ", 1)
            if name.strip() == reference:
                return revision.strip()
    return ""


def inspect_hint_asset(config: Mapping[str, Any]) -> dict[str, Any]:
    """Inspect the pinned source and checkpoint without importing HINT."""
    asset = config["external_asset"]
    repository = _resolve_asset_path(config, "repository")
    checkpoint = _resolve_asset_path(config, "checkpoint")
    missing_files = [
        name for name in asset["required_repository_files"]
        if not (repository / str(name)).is_file()
    ]
    actual_revision = _read_git_revision(repository) if repository.is_dir() else ""
    pinned_revision = str(asset["repository_revision"])
    return {
        "repository_path": str(repository),
        "repository_exists": repository.is_dir(),
        "missing_repository_files": missing_files,
        "pinned_repository_revision": pinned_revision,
        "actual_repository_revision": actual_revision,
        "repository_revision_matches": actual_revision == pinned_revision,
        "checkpoint_path": str(checkpoint),
        "checkpoint_exists": checkpoint.is_file(),
        "checkpoint_filename_matches": (
            checkpoint.name == str(asset["expected_checkpoint_filename"])
        ),
        "checkpoint_size_bytes": checkpoint.stat().st_size if checkpoint.is_file() else 0,
        "checkpoint_sha256": (
            calculate_file_sha256(checkpoint) if checkpoint.is_file() else ""
        ),
        "ready": bool(
            repository.is_dir() and not missing_files
            and actual_revision == pinned_revision and checkpoint.is_file()
            and checkpoint.name == str(asset["expected_checkpoint_filename"])
        ),
    }


def validate_hint_decision(
    decision: Mapping[str, Any], decision_candidates: pd.DataFrame,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify that D01 selected HINT without importing its pilot candidates."""
    selected = str(decision.get("selected_method", "")).strip().lower()
    hint_rows = decision_candidates.loc[
        decision_candidates["model_id"].astype(str).eq(MODEL_ID)
    ]
    passed = bool(
        selected == str(config["inputs"]["required_decision"])
        and len(hint_rows) == 12
        and hint_rows["status"].astype(str).eq("completed").all()
    )
    return {
        "passed": passed,
        "selected_method": selected,
        "hint_pilot_rows": int(len(hint_rows)),
        "pilot_rows_reused": 0,
    }


def build_hint_worklist(
    case_registry: pd.DataFrame,
    model_eligibility: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Return the exact 2,620-case Notebook 08 HINT-eligible population."""
    return build_eligible_case_worklist(case_registry, model_eligibility, config)


def _mask_threshold(row: Mapping[str, Any], config: Mapping[str, Any]) -> int:
    policy = (
        "synthetic_degradation"
        if str(row["experiment_id"]) == "synthetic_degradation"
        else "binary_missing_region"
    )
    return int(config["model"]["mask_threshold_policy"][policy]["threshold"])


def _identifier(case_id: str, config: Mapping[str, Any]) -> tuple[str, str]:
    model_id = str(config["model"]["model_id"])
    return (
        f"restoration__{model_id}__{case_id}",
        f"candidate__{model_id}__{case_id}__c00",
    )


def build_hint_plan(
    worklist: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    project_root: str | Path,
    notebook_output_root: str | Path,
) -> pd.DataFrame:
    """Create one deterministic production record for each eligible case."""
    root = Path(project_root).resolve()
    output_root = Path(notebook_output_root).resolve()
    model = config["model"]
    records: list[dict[str, Any]] = []
    for index, row in enumerate(worklist.to_dict("records"), start=1):
        case_id = str(row["case_id"])
        restoration_id, candidate_id = _identifier(case_id, config)
        restored = (
            output_root / "images" / "restored"
            / str(row["experiment_id"]) / f"{case_id}.png"
        ).resolve()
        if not restored.is_relative_to(output_root):
            raise ValueError("A HINT output path escaped the notebook output root")
        zero_control = float(row["realized_damage_fraction"]) == 0.0
        record = {column: "" for column in HINT_WORK_COLUMNS}
        record.update({
            "restoration_id": restoration_id,
            "case_id": case_id,
            "model_id": MODEL_ID,
            "candidate_id": candidate_id,
            "candidate_index": 0,
            "seed": int(model["seed"]),
            "prompt_policy_id": "",
            "model_version": str(config["external_asset"]["repository_revision"]),
            "opencv_version": "",
            "configuration_id": str(model["configuration_id"]),
            "algorithm": "official HINT generator",
            "inpaint_radius": "",
            "mask_threshold": _mask_threshold(row, config),
            "execution_action": "identity_noop" if zero_control else "hint_inpaint",
            "restored_path": restored.relative_to(root).as_posix(),
            "input_sha256": "",
            "mask_sha256": "",
            "restored_sha256": "",
            "runtime_seconds": "",
            "device": "cuda",
            "precision": str(model["precision"]),
            "execution_backend": "official_hint_direct",
            "cpu_environment": "",
            "retry_count": 0,
            "generator_name": "HINT",
            "generator_version": HELPER_VERSION,
            "started_at_utc": "",
            "completed_at_utc": "",
            "status": "planned",
            "issue": "",
            "painting_id": str(row["painting_id"]),
            "experiment_id": str(row["experiment_id"]),
            "damage_or_degradation_type": str(row["damage_or_degradation_type"]),
            "input_image_path": str(row["input_image_path"]),
            "clean_image_path": str(row["clean_image_path"]),
            "mask_path": str(row["mask_or_effect_path"]),
            "model_load_seconds": "",
            "inference_seconds": "",
            "gpu_peak_memory_bytes": "",
            "output_geometry_valid": False,
            "outside_mask_changed_pixels": "",
            "technical_validation_passed": False,
            "failure_type": "none",
            "error_type": "",
            "error_message": "",
        })
        records.append(record)
    result = pd.DataFrame(records, columns=HINT_WORK_COLUMNS)
    expected = int(config["expected"]["eligible_case_count"])
    if len(result) != expected or result["case_id"].nunique() != expected:
        raise ValueError("HINT plan does not match the 2,620-case contract")
    if result["candidate_id"].nunique() != expected:
        raise ValueError("HINT candidate identifiers are not unique")
    return result


def atomic_write_csv(frame: pd.DataFrame, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    try:
        frame.to_csv(temporary, index=False)
        for attempt in range(8):
            try:
                os.replace(temporary, target)
                return
            except PermissionError:
                if attempt == 7:
                    raise
                sleep(0.15 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    try:
        for attempt in range(8):
            try:
                os.replace(temporary, target)
                return
            except PermissionError:
                if attempt == 7:
                    raise
                sleep(0.15 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


def materialize_input_checksums(
    plan: pd.DataFrame, *, project_root: str | Path,
) -> pd.DataFrame:
    root = Path(project_root).resolve()
    result = plan.copy()
    cache: dict[str, str] = {}
    for index, row in result.iterrows():
        for path_column, hash_column in (
            ("input_image_path", "input_sha256"),
            ("mask_path", "mask_sha256"),
        ):
            path = (root / str(row[path_column])).resolve()
            if not path.is_file():
                raise FileNotFoundError(path)
            key = str(path)
            cache.setdefault(key, calculate_file_sha256(path))
            result.at[index, hash_column] = cache[key]
    return result


@dataclass(frozen=True)
class WorkerProcessResult:
    timed_out: bool
    timeout_reason: str
    return_code: int | None
    runtime_seconds: float
    stdout: str
    stderr: str


def build_worker_job(
    plan: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    project_root: str | Path,
    notebook_output_root: str | Path,
) -> tuple[dict[str, Any], tuple[Path, ...]]:
    root = Path(project_root).resolve()
    output_root = Path(notebook_output_root).resolve()
    output = config["output"]
    paths = tuple((output_root / output[key]).resolve() for key in (
        "worker_job_path", "worker_result_path", "checkpoint_path", "progress_path"
    ))
    job_path, result_path, checkpoint_path, progress_path = paths
    rows = []
    for record in plan.to_dict("records"):
        item = dict(record)
        for field in ("input_image_path", "clean_image_path", "mask_path", "restored_path"):
            item[field] = str((root / str(item[field])).resolve())
        rows.append(item)
    payload = {
        "job_schema_version": "hint_production_worker_job.v1",
        "helper_version": HELPER_VERSION,
        "repository_path": str(_resolve_asset_path(config, "repository")),
        "checkpoint_path": str(_resolve_asset_path(config, "checkpoint")),
        "result_path": str(result_path),
        "checkpoint_path_csv": str(checkpoint_path),
        "progress_path": str(progress_path),
        "execution": dict(config["execution"]),
        "model": dict(config["model"]),
        "candidates": rows,
    }
    atomic_write_json(job_path, payload)
    return payload, paths


def worker_command(job_path: str | Path) -> list[str]:
    return [
        sys.executable, "-m", "restoration_eval.restoration_hint_production_worker",
        "--job", str(Path(job_path).resolve()),
    ]


def run_worker_process(
    command: Sequence[str], *, timeout_seconds: float,
    cwd: str | Path | None = None,
    environment: Mapping[str, str] | None = None,
    progress_path: str | Path | None = None,
    startup_timeout_seconds: float | None = None,
    stall_timeout_seconds: float | None = None,
    poll_interval_seconds: float = 1.0,
) -> WorkerProcessResult:
    started = perf_counter()
    process = subprocess.Popen(
        list(command), cwd=None if cwd is None else str(cwd),
        env=None if environment is None else dict(environment),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    timed_out = False
    timeout_reason = ""
    progress = None if progress_path is None else Path(progress_path)
    last_progress_signature: tuple[int, int] | None = None
    last_progress_at = started
    progress_seen = False

    while process.poll() is None:
        now = perf_counter()
        if now - started > float(timeout_seconds):
            timed_out = True
            timeout_reason = "global_budget_exceeded"
            process.kill()
            break

        if progress is not None and progress.is_file():
            stat = progress.stat()
            signature = (int(stat.st_mtime_ns), int(stat.st_size))
            if signature != last_progress_signature:
                last_progress_signature = signature
                last_progress_at = now
                progress_seen = True

        applicable_stall_limit = (
            stall_timeout_seconds
            if progress_seen
            else startup_timeout_seconds
        )
        if (
            applicable_stall_limit is not None
            and now - last_progress_at > float(applicable_stall_limit)
        ):
            timed_out = True
            timeout_reason = (
                "case_progress_stalled"
                if progress_seen
                else "model_load_stalled"
            )
            process.kill()
            break
        sleep(max(0.1, float(poll_interval_seconds)))

    stdout, stderr = process.communicate()
    return WorkerProcessResult(
        timed_out=timed_out, timeout_reason=timeout_reason,
        return_code=process.returncode,
        runtime_seconds=round(perf_counter() - started, 3),
        stdout=stdout, stderr=stderr,
    )


__all__ = [
    "CONFIG_SCHEMA_VERSION", "HELPER_NAME", "HELPER_VERSION",
    "HINT_WORK_COLUMNS", "MODEL_ID", "WorkerProcessResult",
    "atomic_write_csv", "atomic_write_json", "build_hint_plan",
    "build_hint_worklist", "build_worker_job", "configuration_fingerprint",
    "inspect_hint_asset", "load_hint_config", "materialize_input_checksums",
    "run_worker_process", "utc_now_iso", "validate_hint_decision",
    "worker_command",
]
