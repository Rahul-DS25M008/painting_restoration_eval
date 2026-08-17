"""Versioned run and artifact manifest construction and persistence."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from .paths import find_project_root, to_repo_relative
from .schemas import (
    ARTIFACT_MANIFEST_COLUMNS,
    ARTIFACT_MANIFEST_SCHEMA,
    RUN_MANIFEST_REQUIRED_KEYS,
    require_mapping_keys,
    validate_dataframe,
)


MANIFESTS_MODULE_VERSION = "1.0.0"
RUN_MANIFEST_SCHEMA_VERSION = "run_manifest.v1"
ARTIFACT_MANIFEST_SCHEMA_VERSION = ARTIFACT_MANIFEST_SCHEMA.version
ALLOWED_RUN_STATUSES = frozenset(
    {"initialized", "running", "completed", "failed", "partial"}
)
ALLOWED_VALIDATION_STATUSES = frozenset(
    {"passed", "failed", "warning", "not_applicable", "pending"}
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_path(path: str | Path) -> str:
    """Hash one file or a directory tree including normalized relative names."""
    target = Path(path)
    if target.is_file():
        return sha256_file(target)
    if not target.is_dir():
        raise FileNotFoundError(f"Artifact path does not exist: {target}")

    digest = hashlib.sha256()
    for file_path in sorted(item for item in target.rglob("*") if item.is_file()):
        relative = file_path.relative_to(target).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(sha256_file(file_path)))
    return digest.hexdigest()


def path_statistics(path: str | Path) -> dict[str, int]:
    target = Path(path)
    if target.is_file():
        return {"file_count": 1, "size_bytes": int(target.stat().st_size)}
    if not target.is_dir():
        raise FileNotFoundError(f"Artifact path does not exist: {target}")
    files = [item for item in target.rglob("*") if item.is_file()]
    return {
        "file_count": len(files),
        "size_bytes": sum(int(item.stat().st_size) for item in files),
    }


def git_state(project_root: str | Path | None = None) -> dict[str, Any]:
    root = find_project_root(project_root)

    def run_git(*arguments: str) -> str:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    try:
        commit = run_git("rev-parse", "HEAD")
        dirty = bool(run_git("status", "--porcelain"))
        branch = run_git("branch", "--show-current")
        return {
            "git_commit": commit,
            "git_dirty": dirty,
            "git_branch": branch,
            "git_error": "",
        }
    except (OSError, subprocess.CalledProcessError) as exc:
        return {
            "git_commit": "",
            "git_dirty": None,
            "git_branch": "",
            "git_error": f"{type(exc).__name__}: {exc}",
        }


def package_versions(package_names: Iterable[str]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in sorted(set(str(item) for item in package_names)):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "not_installed"
    return versions


def environment_summary(
    package_names: Iterable[str] = (),
    hardware: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hardware": dict(hardware or {}),
        "package_versions": package_versions(package_names),
    }


def configuration_checksums(
    paths: Iterable[str | Path],
    project_root: str | Path | None = None,
) -> dict[str, str]:
    root = find_project_root(project_root)
    result: dict[str, str] = {}
    for path in paths:
        target = Path(path)
        if not target.is_absolute():
            target = root / target
        result[to_repo_relative(target, root)] = sha256_file(target)
    return result


def build_run_manifest(
    *,
    notebook_id: str,
    notebook_name: str,
    origin: str,
    run_status: str,
    started_at_utc: str,
    completed_at_utc: str,
    inventory_run_id: str,
    dataset_versions: Mapping[str, Any],
    configuration_paths: Sequence[str],
    configuration_checksums_by_path: Mapping[str, str],
    helper_versions: Mapping[str, str],
    inputs: Sequence[Mapping[str, Any]],
    outputs: Sequence[Mapping[str, Any]],
    expected_counts: Mapping[str, Any],
    observed_counts: Mapping[str, Any],
    validation_summary: Mapping[str, Any],
    known_limitations: Sequence[str],
    project_root: str | Path | None = None,
    package_names: Iterable[str] = (),
    hardware: Mapping[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Build a complete universal run manifest without writing it."""
    normalized_status = str(run_status).strip().lower()
    if normalized_status not in ALLOWED_RUN_STATUSES:
        raise ValueError(f"Unsupported run status: {run_status!r}")

    git = git_state(project_root)
    environment = environment_summary(package_names, hardware)
    manifest = {
        "manifest_schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "run_id": run_id or f"run_{uuid.uuid4().hex}",
        "notebook_id": str(notebook_id),
        "notebook_name": str(notebook_name),
        "origin": str(origin),
        "run_status": normalized_status,
        "started_at_utc": str(started_at_utc),
        "completed_at_utc": str(completed_at_utc),
        "git_commit": git["git_commit"],
        "git_dirty": git["git_dirty"],
        "git_branch": git["git_branch"],
        "git_error": git["git_error"],
        "inventory_run_id": str(inventory_run_id),
        "dataset_versions": dict(dataset_versions),
        "configuration_paths": list(configuration_paths),
        "configuration_checksums": dict(configuration_checksums_by_path),
        "helper_versions": dict(helper_versions),
        "python_version": environment["python_version"],
        "python_implementation": environment["python_implementation"],
        "platform": environment["platform"],
        "package_versions": environment["package_versions"],
        "hardware": environment["hardware"],
        "inputs": [dict(item) for item in inputs],
        "outputs": [dict(item) for item in outputs],
        "expected_counts": dict(expected_counts),
        "observed_counts": dict(observed_counts),
        "validation_summary": dict(validation_summary),
        "known_limitations": list(known_limitations),
    }
    require_mapping_keys(
        manifest,
        RUN_MANIFEST_REQUIRED_KEYS,
        mapping_name="run manifest",
    )
    return manifest


def _infer_format(path: Path) -> str:
    return "directory" if path.is_dir() else (path.suffix.lower().lstrip(".") or "file")


def build_artifact_record(
    *,
    artifact_key: str,
    producer_notebook: str,
    path: str | Path,
    artifact_type: str,
    artifact_role: str,
    schema_version: str,
    dataset_scope: str,
    experiment_id: str = "",
    validation_status: str = "passed",
    row_count: int | None = None,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    """Describe one persisted artifact using deterministic checksums and IDs."""
    root = find_project_root(project_root)
    target = Path(path)
    if not target.is_absolute():
        target = root / target
    target = target.resolve()
    status = str(validation_status).strip().lower()
    if status not in ALLOWED_VALIDATION_STATUSES:
        raise ValueError(f"Unsupported artifact validation status: {status}")
    stats = path_statistics(target)
    relative_path = to_repo_relative(target, root)
    checksum = sha256_path(target)
    identity = f"{artifact_key}|{relative_path}|{checksum}".encode("utf-8")
    return {
        "artifact_id": f"artifact_{hashlib.sha256(identity).hexdigest()[:20]}",
        "artifact_key": str(artifact_key),
        "producer_notebook": str(producer_notebook),
        "artifact_type": str(artifact_type),
        "artifact_role": str(artifact_role),
        "relative_path": relative_path,
        "format": _infer_format(target),
        "dataset_scope": str(dataset_scope),
        "experiment_id": str(experiment_id),
        "schema_version": str(schema_version),
        "row_count": "" if row_count is None else int(row_count),
        "file_count": stats["file_count"],
        "size_bytes": stats["size_bytes"],
        "checksum": checksum,
        "validation_status": status,
    }


def artifact_records_dataframe(
    records: Sequence[Mapping[str, Any]],
) -> pd.DataFrame:
    frame = pd.DataFrame(
        [dict(record) for record in records],
        columns=ARTIFACT_MANIFEST_COLUMNS,
    )
    result = validate_dataframe(frame, ARTIFACT_MANIFEST_SCHEMA)
    if not result.passed:
        raise ValueError(f"Artifact manifest violates schema: {result.to_dict()}")
    if frame["artifact_key"].duplicated().any():
        duplicates = frame.loc[
            frame["artifact_key"].duplicated(keep=False), "artifact_key"
        ].tolist()
        raise ValueError(f"Duplicate artifact keys: {duplicates}")
    return frame


def _atomic_write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def write_run_manifest(path: str | Path, manifest: Mapping[str, Any]) -> Path:
    require_mapping_keys(manifest, RUN_MANIFEST_REQUIRED_KEYS, mapping_name="run manifest")
    return _atomic_write_text(
        Path(path),
        json.dumps(dict(manifest), indent=2, ensure_ascii=False) + "\n",
    )


def write_artifact_manifest(
    path: str | Path,
    records: Sequence[Mapping[str, Any]],
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        artifact_records_dataframe(records).to_csv(temporary, index=False)
        os.replace(temporary, output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return output_path
