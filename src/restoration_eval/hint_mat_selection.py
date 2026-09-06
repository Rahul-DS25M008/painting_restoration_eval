"""Contract, planning, and guarded execution helpers for Notebook 37.

The module intentionally avoids importing torch or either external model. Model
code runs in isolated workers so notebook preflight remains fast and a parent
watchdog can enforce a finite model-level budget.
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

import numpy as np
import pandas as pd
from PIL import Image
import yaml


HELPER_NAME = "restoration_eval.hint_mat_selection"
HELPER_VERSION = "1.0.1"
CONFIG_SCHEMA_VERSION = "hint_mat_selection_config.v1"

SELECTION_SCOPE_COLUMNS = (
    "selection_rank", "case_id", "painting_id", "category", "experiment_id",
    "damage_type", "target_damage_fraction", "realized_damage_fraction",
    "input_image_path", "clean_image_path", "mask_path", "source_manifest_path",
    "selection_policy", "status", "issue",
)

CANDIDATE_COLUMNS = (
    "candidate_id", "candidate_index", "selection_rank", "case_id",
    "painting_id", "category", "experiment_id", "damage_type",
    "realized_damage_fraction", "input_image_path", "clean_image_path",
    "mask_path", "input_sha256", "clean_sha256", "mask_sha256", "model_id",
    "model_label", "implementation", "repository_url", "repository_revision",
    "checkpoint_id", "checkpoint_path", "checkpoint_sha256", "license",
    "configuration_id", "adapter_policy", "seed", "requested_device",
    "actual_device", "precision", "inference_width", "inference_height",
    "output_width", "output_height", "compositing_policy", "execution_action",
    "restored_path", "restored_sha256", "model_load_seconds",
    "inference_seconds", "runtime_seconds", "gpu_peak_memory_bytes",
    "output_geometry_valid", "outside_mask_changed_pixels",
    "technical_validation_passed", "started_at_utc", "completed_at_utc",
    "generator_name", "generator_version", "status", "failure_type",
    "worker_return_code", "error_type", "error_message", "issue",
)

METRIC_VALUE_COLUMNS = (
    "metric_row_id", "candidate_id", "case_id", "painting_id", "category",
    "model_id", "metric_family", "metric_name", "region_id", "value",
    "preferred_direction", "metric_version", "region_policy_version",
    "status", "issue",
)

DECISION_SCORECARD_COLUMNS = (
    "scorecard_row_id", "model_id", "criterion_family", "criterion_id",
    "criterion_label", "evidence_value", "evidence_unit",
    "preferred_direction", "hard_gate", "gate_passed", "evidence_path",
    "status", "issue",
)


def utc_now_iso() -> str:
    """Return an RFC-3339 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def calculate_file_sha256(path: str | Path) -> str:
    """Return a full SHA-256 checksum."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configuration_fingerprint(config: Mapping[str, Any]) -> str:
    payload = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _require_keys(mapping: Mapping[str, Any], keys: set[str], *, label: str) -> None:
    missing = sorted(keys - set(mapping))
    if missing:
        raise ValueError(f"{label} is missing required keys: {missing}")


def load_selection_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the Notebook 37 experiment contract."""
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise TypeError("Notebook 37 configuration must contain a YAML mapping")
    _require_keys(
        config,
        {
            "config_schema_version", "config_version", "dataset", "inputs",
            "output", "external_assets", "models", "selection", "execution",
            "evaluation", "decision", "schema_versions", "known_limitations",
        },
        label="Notebook 37 configuration",
    )
    if config["config_schema_version"] != CONFIG_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported config schema {config['config_schema_version']!r}; "
            f"expected {CONFIG_SCHEMA_VERSION!r}"
        )
    selection = config["selection"]
    cases = selection["cases"]
    case_ids = [str(item["case_id"]) for item in cases]
    ranks = [int(item["selection_rank"]) for item in cases]
    if len(cases) != int(selection["case_count"]):
        raise ValueError("Declared and listed selection case counts disagree")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("The predeclared case list contains duplicates")
    if ranks != list(range(1, len(cases) + 1)):
        raise ValueError("Selection ranks must be consecutive and ordered")
    if set(config["models"]) != {"hint", "mat"}:
        raise ValueError("Notebook 37 must compare exactly HINT and MAT")
    if int(selection["candidate_count"]) != len(cases) * len(config["models"]):
        raise ValueError("Candidate count does not equal cases multiplied by methods")
    if bool(config["evaluation"]["construct_combined_score"]):
        raise ValueError("A combined score is prohibited")
    if bool(config["decision"]["prohibit_automatic_winner"]) is not True:
        raise ValueError("The selection decision must remain human-owned")
    return config


def _resolve_external_path(
    config: Mapping[str, Any], asset_key: str, path_kind: str,
    *, environment: Mapping[str, str] | None = None,
) -> Path:
    values = os.environ if environment is None else environment
    variable = str(config["external_assets"]["environment_variables"][f"{asset_key}_{path_kind}"])
    default_key = "default_repo_root" if path_kind == "repo_root" else "default_checkpoint_path"
    raw = values.get(variable) or str(config["external_assets"][asset_key][default_key])
    return Path(raw).expanduser().resolve()


def _read_git_revision(repo: Path) -> str:
    """Read a checkout's HEAD without invoking Git or modifying the checkout."""
    git_dir = repo / ".git"
    head_path = git_dir / "HEAD"
    if not head_path.is_file():
        return ""
    head = head_path.read_text(encoding="utf-8-sig").strip()
    if not head.startswith("ref: "):
        return head
    reference = head[5:].strip()
    loose_ref = git_dir / reference
    if loose_ref.is_file():
        return loose_ref.read_text(encoding="utf-8-sig").strip()
    packed = git_dir / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith(("#", "^")) or " " not in line:
                continue
            revision, name = line.split(" ", 1)
            if name.strip() == reference:
                return revision.strip()
    return ""


def inspect_external_assets(
    config: Mapping[str, Any], *, environment: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Inspect external repositories/checkpoints without importing model code."""
    required_files = {
        "hint": ("src/networks.py", "src/models.py", "LICENSE"),
        "mat": ("generate_image.py", "legacy.py", "networks/mat.py", "LICENSE"),
    }
    rows: list[dict[str, Any]] = []
    for key in ("hint", "mat"):
        repo = _resolve_external_path(config, key, "repo_root", environment=environment)
        checkpoint = _resolve_external_path(
            config, key, "checkpoint_path", environment=environment
        )
        missing_repo_files = [name for name in required_files[key] if not (repo / name).is_file()]
        actual_revision = _read_git_revision(repo) if repo.is_dir() else ""
        pinned_revision = str(config["external_assets"][key]["repository_revision"])
        revision_matches = actual_revision == pinned_revision
        rows.append(
            {
                "model_key": key,
                "model_id": config["models"][key]["model_id"],
                "repository_path": str(repo),
                "repository_exists": repo.is_dir(),
                "repository_required_files_present": not missing_repo_files,
                "missing_repository_files": ";".join(missing_repo_files),
                "pinned_repository_revision": pinned_revision,
                "actual_repository_revision": actual_revision,
                "repository_revision_matches": revision_matches,
                "checkpoint_path": str(checkpoint),
                "checkpoint_exists": checkpoint.is_file(),
                "checkpoint_size_bytes": checkpoint.stat().st_size if checkpoint.is_file() else 0,
                "checkpoint_sha256": calculate_file_sha256(checkpoint) if checkpoint.is_file() else "",
                "license": config["external_assets"][key]["license"],
                "ready": (
                    repo.is_dir() and not missing_repo_files and revision_matches
                    and checkpoint.is_file()
                ),
            }
        )
    return pd.DataFrame(rows)


def build_selection_scope(
    case_registry: pd.DataFrame,
    artworks: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Materialize the exact predeclared 12-case population."""
    required_case_columns = {
        "case_id", "painting_id", "experiment_id", "input_image_path",
        "clean_image_path", "mask_or_effect_path", "damage_or_degradation_type",
        "target_damage_fraction", "realized_damage_fraction",
        "source_manifest_path", "status",
    }
    missing = sorted(required_case_columns - set(case_registry.columns))
    if missing:
        raise ValueError(f"Case registry is missing columns: {missing}")
    if not {"painting_id", "category"}.issubset(artworks.columns):
        raise ValueError("Artwork registry is missing painting_id or category")
    declarations = pd.DataFrame(config["selection"]["cases"])
    selected = declarations.merge(case_registry, on="case_id", how="left", validate="one_to_one")
    selected = selected.merge(
        artworks[["painting_id", "category"]], on="painting_id", how="left",
        validate="many_to_one",
    )
    selected = selected.sort_values("selection_rank").reset_index(drop=True)
    result = pd.DataFrame(
        {
            "selection_rank": selected["selection_rank"].astype(int),
            "case_id": selected["case_id"].astype(str),
            "painting_id": selected["painting_id"].astype(str),
            "category": selected["category"].astype(str),
            "experiment_id": selected["experiment_id"].astype(str),
            "damage_type": selected["case_id"].astype(str).str.rsplit("__", n=1).str[-1],
            "target_damage_fraction": pd.to_numeric(selected["target_damage_fraction"]),
            "realized_damage_fraction": pd.to_numeric(selected["realized_damage_fraction"]),
            "input_image_path": selected["input_image_path"].astype(str),
            "clean_image_path": selected["clean_image_path"].astype(str),
            "mask_path": selected["mask_or_effect_path"].astype(str),
            "source_manifest_path": selected["source_manifest_path"].astype(str),
            "selection_policy": str(config["selection"]["policy_id"]),
            "status": selected["status"].astype(str),
            "issue": "",
        },
        columns=SELECTION_SCOPE_COLUMNS,
    )
    expected = int(config["selection"]["case_count"])
    if len(result) != expected or result["case_id"].nunique() != expected:
        raise ValueError("The selected population is incomplete or duplicated")
    if set(result["experiment_id"]) != {"canonical_missing_region"}:
        raise ValueError("Notebook 37 permits canonical cases only")
    if not result["status"].eq("passed").all():
        raise ValueError("Every selected upstream case must have passed")
    family_counts = result["damage_type"].value_counts().to_dict()
    required_families = {"scratch_thin", "loss_small", "loss_large", "mixed_damage"}
    if set(family_counts) != required_families:
        raise ValueError(f"Unexpected damage-family coverage: {family_counts}")
    expected_per_family = int(config["selection"]["cases_per_damage_family"])
    if set(family_counts.values()) != {expected_per_family}:
        raise ValueError(f"Damage families are not balanced: {family_counts}")
    minimum = int(config["selection"]["minimum_cases_per_category"])
    if int(result.groupby("category").size().min()) < minimum:
        raise ValueError("A visual category falls below the minimum case count")
    return result


def validate_zero_control_qa(
    case_registry: pd.DataFrame, config: Mapping[str, Any]
) -> pd.Series:
    """Return the declared identity-QA case, which is not part of the 12 cases."""
    case_id = str(config["selection"]["zero_control_qa_case_id"])
    matches = case_registry.loc[case_registry["case_id"].astype(str).eq(case_id)]
    if len(matches) != 1:
        raise ValueError(f"Zero-control QA case must match once: {case_id}")
    row = matches.iloc[0]
    if float(row["realized_damage_fraction"]) != 0.0:
        raise ValueError("The declared zero-control QA case has nonzero damage")
    return row


def _candidate_id(case_id: str, model_id: str, fingerprint: str) -> str:
    token = hashlib.sha256(f"{case_id}|{model_id}|{fingerprint}".encode()).hexdigest()[:12]
    return f"n37__{model_id}__{token}"


def build_candidate_plan(
    scope: pd.DataFrame, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Create the exact 24-row HINT/MAT candidate plan."""
    fingerprint = configuration_fingerprint(config)
    records: list[dict[str, Any]] = []
    candidate_index = 0
    for model_key in ("hint", "mat"):
        model = config["models"][model_key]
        asset = config["external_assets"][model_key]
        checkpoint = _resolve_external_path(config, model_key, "checkpoint_path")
        inference_size = int(
            model.get("native_probe_size", model.get("inference_size", 512))
        )
        for row in scope.itertuples(index=False):
            candidate_index += 1
            model_id = str(model["model_id"])
            relative_output = (
                f"outputs/37_hint_mat_method_selection/images/restored/"
                f"{model_key}/{row.case_id}.png"
            )
            records.append(
                {
                    "candidate_id": _candidate_id(row.case_id, model_id, fingerprint),
                    "candidate_index": candidate_index,
                    "selection_rank": int(row.selection_rank),
                    "case_id": row.case_id,
                    "painting_id": row.painting_id,
                    "category": row.category,
                    "experiment_id": row.experiment_id,
                    "damage_type": row.damage_type,
                    "realized_damage_fraction": float(row.realized_damage_fraction),
                    "input_image_path": row.input_image_path,
                    "clean_image_path": row.clean_image_path,
                    "mask_path": row.mask_path,
                    "input_sha256": "",
                    "clean_sha256": "",
                    "mask_sha256": "",
                    "model_id": model_id,
                    "model_label": str(model["label"]),
                    "implementation": str(model["implementation"]),
                    "repository_url": str(asset["repository_url"]),
                    "repository_revision": str(asset["repository_revision"]),
                    "checkpoint_id": str(asset["checkpoint_id"]),
                    "checkpoint_path": str(checkpoint),
                    "checkpoint_sha256": "",
                    "license": str(asset["license"]),
                    "configuration_id": f"{model_id}_n37_v1",
                    "adapter_policy": str(model["adapter_policy"]),
                    "seed": int(model["seed"]),
                    "requested_device": str(model["requested_device"]),
                    "actual_device": "",
                    "precision": str(model["precision"]),
                    "inference_width": inference_size,
                    "inference_height": inference_size,
                    "output_width": 768,
                    "output_height": 768,
                    "compositing_policy": str(model["compositing_policy"]),
                    "execution_action": "generate",
                    "restored_path": relative_output,
                    "restored_sha256": "",
                    "model_load_seconds": None,
                    "inference_seconds": None,
                    "runtime_seconds": None,
                    "gpu_peak_memory_bytes": None,
                    "output_geometry_valid": False,
                    "outside_mask_changed_pixels": None,
                    "technical_validation_passed": False,
                    "started_at_utc": "",
                    "completed_at_utc": "",
                    "generator_name": str(model["implementation"]),
                    "generator_version": HELPER_VERSION,
                    "status": "planned",
                    "failure_type": "none",
                    "worker_return_code": None,
                    "error_type": "",
                    "error_message": "",
                    "issue": "",
                }
            )
    result = pd.DataFrame(records, columns=CANDIDATE_COLUMNS)
    expected = int(config["selection"]["candidate_count"])
    if len(result) != expected or result["candidate_id"].nunique() != expected:
        raise ValueError("Candidate plan does not match the 24-row contract")
    per_case = result.groupby("case_id")["model_id"].nunique()
    if not per_case.eq(2).all():
        raise ValueError("Each selected case must have both candidate methods")
    return result


def materialize_input_checksums(
    candidates: pd.DataFrame, *, project_root: str | Path
) -> pd.DataFrame:
    """Validate inputs and attach full source/checkpoint checksums."""
    root = Path(project_root).resolve()
    result = candidates.copy()
    checksum_cache: dict[str, str] = {}
    for index, row in result.iterrows():
        for column, checksum_column in (
            ("input_image_path", "input_sha256"),
            ("clean_image_path", "clean_sha256"),
            ("mask_path", "mask_sha256"),
        ):
            path = (root / str(row[column])).resolve()
            if not path.is_file():
                raise FileNotFoundError(f"Missing Notebook 37 input: {path}")
            path_key = str(path)
            if path_key not in checksum_cache:
                checksum_cache[path_key] = calculate_file_sha256(path)
            result.at[index, checksum_column] = checksum_cache[path_key]
        checkpoint = Path(str(row["checkpoint_path"])).resolve()
        if not checkpoint.is_file():
            raise FileNotFoundError(f"Missing external checkpoint: {checkpoint}")
        checkpoint_key = str(checkpoint)
        if checkpoint_key not in checksum_cache:
            checksum_cache[checkpoint_key] = calculate_file_sha256(checkpoint)
        result.at[index, "checkpoint_sha256"] = checksum_cache[checkpoint_key]
    return result


def prepare_model_inputs(
    input_path: str | Path,
    mask_path: str | Path,
    *,
    inference_size: int,
    mask_threshold: int = 128,
    mat_mask_semantics: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Prepare model tensors and preserve 768-pixel source/missing mask arrays.

    Returned image arrays are RGB uint8. The third array is always the canonical
    768-pixel missing mask (1 = missing). The second array is either that same
    convention or MAT's official 1 = retained convention.
    """
    with Image.open(input_path) as image_handle:
        source = np.asarray(image_handle.convert("RGB"), dtype=np.uint8)
    with Image.open(mask_path) as mask_handle:
        mask = np.asarray(mask_handle.convert("L"), dtype=np.uint8)
    if source.shape != (768, 768, 3) or mask.shape != (768, 768):
        raise ValueError(f"Expected 768x768 inputs, found {source.shape} and {mask.shape}")
    missing = (mask >= int(mask_threshold)).astype(np.uint8)
    if int(missing.sum()) == 0:
        raise ValueError("The selected mask is empty")
    image_small = np.asarray(
        Image.fromarray(source).resize((inference_size, inference_size), Image.Resampling.LANCZOS),
        dtype=np.uint8,
    )
    missing_small = np.asarray(
        Image.fromarray(missing * 255).resize(
            (inference_size, inference_size), Image.Resampling.NEAREST
        ),
        dtype=np.uint8,
    )
    missing_small = (missing_small >= 128).astype(np.uint8)
    model_mask = 1 - missing_small if mat_mask_semantics else missing_small
    return image_small, model_mask, missing, source


def exact_mask_composite(
    generated: np.ndarray, source_768: np.ndarray, missing_mask_768: np.ndarray
) -> np.ndarray:
    """Resize a generated RGB image and replace only canonical missing pixels."""
    generated_array = np.asarray(generated, dtype=np.uint8)
    if generated_array.ndim != 3 or generated_array.shape[2] != 3:
        raise ValueError("Generated image must be an HxWx3 RGB array")
    if generated_array.shape[:2] != (768, 768):
        generated_array = np.asarray(
            Image.fromarray(generated_array).resize((768, 768), Image.Resampling.LANCZOS),
            dtype=np.uint8,
        )
    missing = np.asarray(missing_mask_768).astype(bool)
    return np.where(missing[..., None], generated_array, source_768).astype(np.uint8)


def validate_restored_output(
    restored_path: str | Path,
    input_path: str | Path,
    mask_path: str | Path,
    *,
    mask_threshold: int = 128,
) -> dict[str, Any]:
    """Validate geometry, mode, and exact outside-mask preservation."""
    with Image.open(restored_path) as handle:
        restored_mode = handle.mode
        restored = np.asarray(handle.convert("RGB"), dtype=np.uint8)
        size = handle.size
    with Image.open(input_path) as handle:
        source = np.asarray(handle.convert("RGB"), dtype=np.uint8)
    with Image.open(mask_path) as handle:
        missing = np.asarray(handle.convert("L"), dtype=np.uint8) >= mask_threshold
    changed = np.any(restored != source, axis=2)
    outside_changed = int(changed[~missing].sum())
    geometry_valid = size == (768, 768) and restored_mode == "RGB"
    return {
        "output_geometry_valid": geometry_valid,
        "outside_mask_changed_pixels": outside_changed,
        "technical_validation_passed": bool(geometry_valid and outside_changed == 0),
    }


def load_resumable_candidate_records(
    job: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Load valid completed rows and retained failures from a worker checkpoint."""
    execution = job["execution"]
    if not bool(execution.get("resume_enabled", False)):
        return {}
    checkpoint = Path(str(job["checkpoint_path_csv"]))
    if not checkpoint.is_file():
        return {}
    frame = pd.read_csv(checkpoint).reindex(columns=CANDIDATE_COLUMNS)
    allowed_ids = {
        str(item["candidate_id"])
        for item in job["candidates"]
    }
    retained: dict[str, dict[str, Any]] = {}
    retry_failed = bool(execution.get("retry_failed_attempts", False))
    for record in frame.to_dict(orient="records"):
        candidate_id = str(record.get("candidate_id", ""))
        status = str(record.get("status", ""))
        if candidate_id not in allowed_ids:
            continue
        if status == "completed":
            restored_path = Path(str(record.get("restored_path", "")))
            try:
                technical = validate_restored_output(
                    restored_path,
                    record["input_image_path"],
                    record["mask_path"],
                )
            except (OSError, KeyError, TypeError, ValueError):
                continue
            if bool(technical["technical_validation_passed"]):
                record.update(technical)
                retained[candidate_id] = record
        elif status == "failed" and not retry_failed:
            retained[candidate_id] = record
    return retained


def atomic_write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        _replace_with_retry(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_write_csv(frame: pd.DataFrame, path: str | Path) -> None:
    """Persist CSV with bounded retries for transient Windows file locks."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    try:
        frame.to_csv(temporary, index=False)
        _replace_with_retry(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def _replace_with_retry(source: Path, target: Path, attempts: int = 8) -> None:
    last_error: OSError | None = None
    for attempt in range(attempts):
        try:
            os.replace(source, target)
            return
        except PermissionError as exc:
            last_error = exc
            sleep(0.15 * (attempt + 1))
    if last_error is not None:
        raise last_error


def build_worker_job(
    model_key: str,
    candidates: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    project_root: str | Path,
    output_root: str | Path,
    job_role: str,
) -> tuple[dict[str, Any], Path, Path, Path, Path]:
    """Build a batch worker job for a smoke or full model execution."""
    if model_key not in {"hint", "mat"}:
        raise ValueError(f"Unsupported model key: {model_key}")
    model = config["models"][model_key]
    model_rows = candidates.loc[candidates["model_id"].eq(model["model_id"])].copy()
    if model_rows.empty:
        raise ValueError(f"No candidate rows found for {model_key}")
    root = Path(project_root).resolve()
    owned_root = Path(output_root).resolve()
    work = owned_root / str(config["output"]["work_directory"]) / model_key / job_role
    job_path = work / "job.json"
    result_path = work / "result.json"
    checkpoint_path = work / "candidate_checkpoint.csv"
    progress_path = work / "progress.json"
    records: list[dict[str, Any]] = []
    for row in model_rows.to_dict(orient="records"):
        item = dict(row)
        for field in ("input_image_path", "clean_image_path", "mask_path", "restored_path"):
            item[field] = str((root / str(item[field])).resolve())
        records.append(item)
    payload = {
        "job_schema_version": "hint_mat_worker_job.v1",
        "helper_version": HELPER_VERSION,
        "model_key": model_key,
        "job_role": job_role,
        "repository_path": str(_resolve_external_path(config, model_key, "repo_root")),
        "repository_revision": str(config["external_assets"][model_key]["repository_revision"]),
        "checkpoint_path": str(_resolve_external_path(config, model_key, "checkpoint_path")),
        "result_path": str(result_path),
        "checkpoint_path_csv": str(checkpoint_path),
        "progress_path": str(progress_path),
        "execution": dict(config["execution"]),
        "model": dict(model),
        "candidates": records,
    }
    work.mkdir(parents=True, exist_ok=True)
    atomic_write_json(job_path, payload)
    return payload, job_path, result_path, checkpoint_path, progress_path


@dataclass(frozen=True)
class WorkerProcessResult:
    timed_out: bool
    return_code: int | None
    runtime_seconds: float
    stdout: str
    stderr: str


def run_worker_process(
    command: Sequence[str], *, timeout_seconds: float,
    cwd: str | Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> WorkerProcessResult:
    """Run one isolated worker under a hard model-level timeout."""
    started = perf_counter()
    process = subprocess.Popen(
        list(command), cwd=str(cwd) if cwd is not None else None,
        env=dict(environment) if environment is not None else None,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=float(timeout_seconds))
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        stdout, stderr = process.communicate()
    return WorkerProcessResult(
        timed_out=timed_out,
        return_code=process.returncode,
        runtime_seconds=round(perf_counter() - started, 3),
        stdout=stdout,
        stderr=stderr,
    )


def worker_command(model_key: str, job_path: str | Path) -> list[str]:
    module = {
        "hint": "restoration_eval.restoration_hint_worker",
        "mat": "restoration_eval.restoration_mat_worker",
    }[model_key]
    return [sys.executable, "-m", module, "--job", str(Path(job_path).resolve())]


def validate_candidate_table(frame: pd.DataFrame, *, expected_rows: int = 24) -> None:
    """Raise on structural violations in the normalized candidate table."""
    missing = sorted(set(CANDIDATE_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Candidate table is missing columns: {missing}")
    if len(frame) != expected_rows:
        raise ValueError(f"Expected {expected_rows} candidates, found {len(frame)}")
    if frame["candidate_id"].duplicated().any():
        raise ValueError("Candidate IDs are not unique")
    if not frame.groupby("case_id")["model_id"].nunique().eq(2).all():
        raise ValueError("Each case must contain exactly two model candidates")
