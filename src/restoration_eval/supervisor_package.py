"""Deterministic assembly and validation helpers for Notebook 36.

This module copies already validated artifacts into a portable review package.
It deliberately performs no restoration inference and no scientific metric
computation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import pandas as pd
import yaml

from .manifests import sha256_file, sha256_path
from .paths import find_project_root, resolve_repo_path, to_repo_relative


SUPERVISOR_PACKAGE_VERSION = "1.0.0"
SUPERVISOR_PACKAGE_CONFIG_SCHEMA_VERSION = "supervisor_package_config.v1"
PACKAGE_MANIFEST_SCHEMA_VERSION = "supervisor_package_manifest.v1"


class SupervisorPackageContractError(RuntimeError):
    """Raised when the fixed package contract is invalid."""


@dataclass(frozen=True)
class CopyPlanItem:
    source: Path
    destination: Path
    role: str
    group: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_supervisor_package_config(
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    root = find_project_root(project_root)
    path = root / "config" / "evaluation" / "supervisor_package.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Supervisor-package configuration is missing: {path}")
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise SupervisorPackageContractError("Configuration must be a mapping")
    if payload.get("schema_version") != SUPERVISOR_PACKAGE_CONFIG_SCHEMA_VERSION:
        raise SupervisorPackageContractError(
            f"Unsupported configuration schema: {payload.get('schema_version')!r}"
        )
    required = {
        "notebook", "runtime", "governing_inputs", "upstream_run_manifests",
        "expected_population", "research_questions", "package_policy",
        "copy_plan", "figure_sources", "configuration_sources", "outputs",
        "scientific_boundaries",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise SupervisorPackageContractError(f"Missing configuration sections: {missing}")
    return payload


def safe_repo_path(
    value: str | Path,
    project_root: str | Path | None = None,
    *,
    must_exist: bool = False,
) -> Path:
    root = find_project_root(project_root)
    path = resolve_repo_path(value, root)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SupervisorPackageContractError(f"Path escapes repository: {value}") from exc
    if must_exist and not path.exists():
        raise FileNotFoundError(f"Required repository path is missing: {path}")
    return path


def required_input_paths(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> dict[str, Path]:
    root = find_project_root(project_root)
    result = {
        str(key): safe_repo_path(value, root, must_exist=True)
        for key, value in config["governing_inputs"].items()
    }
    for index, value in enumerate(config["upstream_run_manifests"], start=1):
        result[f"run_manifest_{index:02d}"] = safe_repo_path(value, root, must_exist=True)
    for group, records in config["copy_plan"].items():
        for index, record in enumerate(records, start=1):
            result[f"copy_{group}_{index:02d}"] = safe_repo_path(
                record["source"], root, must_exist=True
            )
    return result


def output_paths(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> dict[str, Path]:
    root = find_project_root(project_root)
    return {
        str(key): safe_repo_path(value, root)
        for key, value in config["outputs"].items()
    }


def create_output_directories(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> list[Path]:
    paths = output_paths(config, project_root)
    root = paths["package_root"].parent
    directories = {
        root / "reports", root / "data", root / "manifests", root / "validation",
        paths["package_root"], paths["package_root"] / "reports" / "models",
        paths["package_root"] / "figures" / "thesis",
        paths["package_root"] / "figures" / "publication",
        paths["package_root"] / "tables", paths["package_root"] / "model_cards",
        paths["package_root"] / "manifests" / "notebook_runs",
        paths["package_root"] / "configuration" / "evaluation",
        paths["package_root"] / "environment", paths["package_root"] / "application",
        paths["package_root"] / "provenance",
    }
    for directory in sorted(directories, key=lambda item: item.as_posix()):
        directory.mkdir(parents=True, exist_ok=True)
    return sorted(directories, key=lambda item: item.as_posix())


def build_copy_plan(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> list[CopyPlanItem]:
    root = find_project_root(project_root)
    output_root = safe_repo_path(config["notebook"]["output_root"], root)
    records: list[CopyPlanItem] = []
    for group, items in config["copy_plan"].items():
        for item in items:
            source = safe_repo_path(item["source"], root, must_exist=True)
            destination = safe_repo_path(output_root / item["destination"], root)
            records.append(CopyPlanItem(source, destination, str(item["role"]), str(group)))

    thesis_dir = safe_repo_path(config["figure_sources"]["thesis_directory"], root, must_exist=True)
    publication_dir = safe_repo_path(config["figure_sources"]["publication_directory"], root, must_exist=True)
    suffixes = {str(value).lower() for value in config["figure_sources"]["allowed_suffixes"]}
    for group, source_dir in (("thesis_figures", thesis_dir), ("publication_figures", publication_dir)):
        destination_dir = output_root / "package" / "figures" / group.replace("_figures", "")
        for source in sorted(path for path in source_dir.iterdir() if path.is_file() and path.suffix.lower() in suffixes):
            records.append(CopyPlanItem(source, destination_dir / source.name, "publication_figure", group))

    config_dir = safe_repo_path(config["configuration_sources"]["directory"], root, must_exist=True)
    config_suffixes = {str(value).lower() for value in config["configuration_sources"]["allowed_suffixes"]}
    for source in sorted(path for path in config_dir.iterdir() if path.is_file() and path.suffix.lower() in config_suffixes):
        records.append(CopyPlanItem(
            source,
            output_root / "package" / "configuration" / "evaluation" / source.name,
            "configuration_snapshot",
            "configuration",
        ))

    for source_value in config["upstream_run_manifests"]:
        source = safe_repo_path(source_value, root, must_exist=True)
        producer = source.parent.parent.name
        records.append(CopyPlanItem(
            source,
            output_root / "package" / "manifests" / "notebook_runs" / f"{producer}.json",
            "upstream_run_manifest",
            "manifests",
        ))

    destinations = [item.destination.resolve() for item in records]
    if len(destinations) != len(set(destinations)):
        raise SupervisorPackageContractError("Copy plan contains duplicate destinations")
    return records


def copy_plan_frame(
    plan: Sequence[CopyPlanItem],
    project_root: str | Path | None = None,
) -> pd.DataFrame:
    root = find_project_root(project_root)
    return pd.DataFrame([
        {
            "group": item.group,
            "role": item.role,
            "source_path": to_repo_relative(item.source, root),
            "destination_path": to_repo_relative(item.destination, root),
            "size_bytes": item.source.stat().st_size,
            "source_sha256": sha256_file(item.source),
        }
        for item in plan
    ])


def materialize_copy_plan(
    plan: Sequence[CopyPlanItem],
    *,
    progress_callback: Callable[[int, int, CopyPlanItem], None] | None = None,
) -> list[Path]:
    copied: list[Path] = []
    total = len(plan)
    for number, item in enumerate(plan, start=1):
        item.destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = item.destination.with_suffix(item.destination.suffix + ".tmp")
        try:
            shutil.copy2(item.source, temporary)
            if sha256_file(temporary) != sha256_file(item.source):
                raise IOError(f"Copy checksum mismatch: {item.source}")
            os.replace(temporary, item.destination)
        finally:
            temporary.unlink(missing_ok=True)
        copied.append(item.destination)
        if progress_callback and (number % 10 == 0 or number == total):
            progress_callback(number, total, item)
    return copied


def load_upstream_manifests(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> pd.DataFrame:
    root = find_project_root(project_root)
    records: list[dict[str, Any]] = []
    for value in config["upstream_run_manifests"]:
        path = safe_repo_path(value, root, must_exist=True)
        with path.open("r", encoding="utf-8-sig") as handle:
            manifest = json.load(handle)
        summary = manifest.get("validation_summary", {})
        records.append({
            "notebook_id": str(manifest.get("notebook_id", "")),
            "notebook_name": str(manifest.get("notebook_name", "")),
            "run_id": str(manifest.get("run_id", "")),
            "run_status": str(manifest.get("run_status", "")),
            "completion_gate_passed": bool(manifest.get("completion_gate_passed", False)),
            "blocking_failures": int(
                summary.get("blocking_failure_count", summary.get("blocking_failures", 0)) or 0
            ),
            "warning_failures": int(
                summary.get("warning_failure_count", summary.get("warning_failures", 0)) or 0
            ),
            "manifest_path": to_repo_relative(path, root),
            "manifest_sha256": sha256_file(path),
        })
    frame = pd.DataFrame(records).sort_values("notebook_id", kind="stable").reset_index(drop=True)
    if frame["notebook_id"].duplicated().any():
        raise SupervisorPackageContractError("Upstream manifest notebook IDs are not unique")
    return frame


_HTML_LOCAL_REFERENCE = re.compile(
    r'''(?:src|href)\s*=\s*["'](?!data:|https?://|#|mailto:)([^"']+)["']''',
    flags=re.IGNORECASE,
)


def audit_self_contained_html(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    text = target.read_text(encoding="utf-8", errors="replace")
    local_references = [
        value for value in _HTML_LOCAL_REFERENCE.findall(text)
        if not value.lower().startswith(("javascript:", "about:"))
    ]
    return {
        "path": target.as_posix(),
        "size_bytes": target.stat().st_size,
        "sha256": sha256_file(target),
        "embedded_data_uri_count": text.lower().count("data:image/"),
        "local_reference_count": len(local_references),
        "local_references": local_references,
        "self_contained": len(local_references) == 0,
    }


def package_file_records(
    package_root: str | Path,
    project_root: str | Path | None = None,
) -> pd.DataFrame:
    root = find_project_root(project_root)
    package = Path(package_root).resolve()
    records = []
    for path in sorted(item for item in package.rglob("*") if item.is_file()):
        records.append({
            "relative_path": to_repo_relative(path, root),
            "package_relative_path": path.relative_to(package).as_posix(),
            "format": path.suffix.lower().lstrip(".") or "file",
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return pd.DataFrame(records)


def package_tree_checksum(records: pd.DataFrame) -> str:
    required = {"package_relative_path", "sha256"}
    if not required.issubset(records.columns):
        raise SupervisorPackageContractError(f"Package records missing columns: {sorted(required - set(records.columns))}")
    payload = "\n".join(
        f"{row.package_relative_path}\t{row.sha256}"
        for row in records.sort_values("package_relative_path", kind="stable").itertuples()
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def atomic_write_text(path: str | Path, text: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def atomic_write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    return atomic_write_text(path, json.dumps(dict(payload), indent=2, ensure_ascii=False) + "\n")


def package_checksum(path: str | Path) -> str:
    return sha256_path(Path(path))
