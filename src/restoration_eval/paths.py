"""Repository, notebook-output, and artifact-registry path contracts."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


PATHS_MODULE_VERSION = "1.0.0"
PROJECT_PATHS_SCHEMA_VERSION = "project_paths.v1"
NOTEBOOK_STEM_PATTERN = re.compile(r"^[0-9]{2}_[a-z0-9]+(?:_[a-z0-9]+)*$")
ALLOWED_OUTPUT_SUBDIRS = frozenset(
    {
        "data",
        "images",
        "metrics",
        "figures",
        "reports",
        "manifests",
        "validation",
        "logs",
        "work",
    }
)
PROJECT_PATH_FIELDS = (
    "artifact_key",
    "producer_notebook",
    "relative_path",
    "artifact_type",
    "artifact_role",
    "schema_version",
    "dataset_scope",
    "experiment_scope",
    "validation_status",
    "row_count",
    "file_count",
    "checksum",
)


def _as_directory(path: Path) -> Path:
    return path.parent if path.is_file() else path


def find_project_root(start: str | Path | None = None) -> Path:
    """Find the repository root without assuming the current working directory."""
    candidate = Path(start).expanduser() if start is not None else Path.cwd()
    candidate = _as_directory(candidate.resolve())

    for directory in (candidate, *candidate.parents):
        if (
            (directory / ".git").exists()
            and (directory / "src" / "restoration_eval").is_dir()
            and (directory / "notebooks").is_dir()
        ):
            return directory

    raise FileNotFoundError(
        f"Could not locate the painting-restoration repository from {candidate}"
    )


def get_project_root(start: str | Path | None = None) -> Path:
    """Backward-compatible alias for :func:`find_project_root`."""
    return find_project_root(start)


def assert_within(path: str | Path, parent: str | Path) -> Path:
    """Resolve a path and require it to remain within the resolved parent."""
    resolved_path = Path(path).expanduser().resolve()
    resolved_parent = Path(parent).expanduser().resolve()
    try:
        resolved_path.relative_to(resolved_parent)
    except ValueError as exc:
        raise ValueError(
            f"Path escapes the allowed parent: {resolved_path} not under "
            f"{resolved_parent}"
        ) from exc
    return resolved_path


def resolve_repo_path(
    path: str | Path,
    project_root: str | Path | None = None,
    *,
    must_exist: bool = False,
) -> Path:
    """Resolve an absolute or repository-relative path and guard repository scope."""
    root = find_project_root(project_root)
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = assert_within(candidate, root)
    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"Required repository path does not exist: {resolved}")
    return resolved


def to_repo_relative(
    path: str | Path,
    project_root: str | Path | None = None,
) -> str:
    """Return a normalized forward-slash repository-relative path."""
    root = find_project_root(project_root)
    return assert_within(path, root).relative_to(root).as_posix()


def validate_notebook_stem(notebook_stem: str) -> str:
    """Validate the exact numbered snake-case notebook stem."""
    normalized = str(notebook_stem).strip()
    if not NOTEBOOK_STEM_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Notebook stem must match NN_lowercase_snake_case; received "
            f"{notebook_stem!r}"
        )
    return normalized


def notebook_output_root(
    notebook_stem: str,
    project_root: str | Path | None = None,
    *,
    create: bool = False,
) -> Path:
    """Return the exact notebook-owned output root, optionally creating it."""
    root = find_project_root(project_root)
    stem = validate_notebook_stem(notebook_stem)
    output_root = assert_within(root / "outputs" / stem, root / "outputs")
    if output_root.parent != (root / "outputs").resolve():
        raise ValueError(f"Invalid notebook output root: {output_root}")
    if create:
        output_root.mkdir(parents=True, exist_ok=True)
    return output_root


def require_notebook_output_path(
    path: str | Path,
    notebook_stem: str,
    project_root: str | Path | None = None,
) -> Path:
    """Require a proposed write path to remain in one notebook-owned root."""
    output_root = notebook_output_root(notebook_stem, project_root)
    return assert_within(path, output_root)


def ensure_output_subdirs(
    notebook_stem: str,
    subdirs: Iterable[str],
    project_root: str | Path | None = None,
) -> dict[str, Path]:
    """Create only explicitly requested, approved notebook-output subdirectories."""
    output_root = notebook_output_root(notebook_stem, project_root, create=True)
    requested = [str(name).strip() for name in subdirs]
    invalid = sorted(set(requested) - ALLOWED_OUTPUT_SUBDIRS)
    if invalid:
        raise ValueError(f"Unsupported notebook output subdirectories: {invalid}")

    created: dict[str, Path] = {}
    for name in requested:
        path = require_notebook_output_path(output_root / name, notebook_stem, project_root)
        path.mkdir(parents=True, exist_ok=True)
        created[name] = path
    return created


def empty_project_paths_registry() -> dict[str, Any]:
    """Return a new empty versioned project-artifact registry."""
    return {
        "registry_schema_version": PROJECT_PATHS_SCHEMA_VERSION,
        "updated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "artifacts": [],
    }


def validate_project_paths_registry(payload: Mapping[str, Any]) -> list[str]:
    """Return registry-contract violations without mutating the registry."""
    errors: list[str] = []
    if payload.get("registry_schema_version") != PROJECT_PATHS_SCHEMA_VERSION:
        errors.append("registry_schema_version is missing or unsupported")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        return errors + ["artifacts must be a list"]

    seen_keys: set[str] = set()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, Mapping):
            errors.append(f"artifacts[{index}] must be an object")
            continue
        missing = [field for field in PROJECT_PATH_FIELDS if field not in artifact]
        if missing:
            errors.append(f"artifacts[{index}] missing fields: {missing}")
        key = str(artifact.get("artifact_key", "")).strip()
        if not key:
            errors.append(f"artifacts[{index}] has an empty artifact_key")
        elif key in seen_keys:
            errors.append(f"duplicate artifact_key: {key}")
        seen_keys.add(key)

        relative_path = str(artifact.get("relative_path", ""))
        if "\\" in relative_path or Path(relative_path).is_absolute():
            errors.append(f"artifact {key!r} path is not normalized and relative")

    return errors


def load_project_paths_registry(
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    """Load and validate the machine-readable project artifact registry."""
    root = find_project_root(project_root)
    path = root / "outputs" / "inventory" / "project_paths.json"
    if not path.is_file():
        raise FileNotFoundError(f"Project paths registry does not exist: {path}")
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    errors = validate_project_paths_registry(payload)
    if errors:
        raise ValueError("Invalid project paths registry: " + "; ".join(errors))
    return payload


def render_project_paths_markdown(payload: Mapping[str, Any]) -> str:
    """Render the registry as a compact human-reviewable Markdown table."""
    errors = validate_project_paths_registry(payload)
    if errors:
        raise ValueError("Cannot render invalid registry: " + "; ".join(errors))

    lines = [
        "# Project Artifact Paths",
        "",
        f"- Schema: `{payload['registry_schema_version']}`",
        f"- Updated: `{payload.get('updated_at_utc', '')}`",
        f"- Registered artifacts: {len(payload['artifacts'])}",
        "",
    ]
    if not payload["artifacts"]:
        lines.append("No validated notebook artifacts are registered yet.")
        lines.append("")
        return "\n".join(lines)

    lines.extend(
        [
            "| Artifact key | Producer | Relative path | Role | Validation |",
            "|---|---|---|---|---|",
        ]
    )
    for artifact in sorted(payload["artifacts"], key=lambda item: item["artifact_key"]):
        lines.append(
            "| {artifact_key} | {producer_notebook} | `{relative_path}` | "
            "{artifact_role} | {validation_status} |".format(**artifact)
        )
    lines.append("")
    return "\n".join(lines)


def upsert_project_path_artifacts(
    payload: Mapping[str, Any],
    artifacts: Iterable[Mapping[str, Any]],
    *,
    include_noncanonical: bool = False,
) -> dict[str, Any]:
    """Return a validated registry with explicit validated artifacts upserted."""
    errors = validate_project_paths_registry(payload)
    if errors:
        raise ValueError("Cannot update invalid registry: " + "; ".join(errors))

    records = {
        str(item["artifact_key"]): dict(item)
        for item in payload["artifacts"]
    }
    for artifact in artifacts:
        artifact_key = str(artifact.get("artifact_key", "")).strip()
        if not artifact_key:
            raise ValueError("Artifact registry update requires artifact_key")
        validation_status = str(
            artifact.get("validation_status", "")
        ).strip().lower()
        if validation_status != "passed":
            raise ValueError(
                f"Registry accepts only passed artifacts; {artifact_key!r} "
                f"has status {validation_status!r}"
            )
        artifact_role = str(artifact.get("artifact_role", "")).strip().lower()
        if (
            artifact_role in {"temporary", "qa"}
            and not include_noncanonical
        ):
            raise ValueError(
                f"Noncanonical artifact {artifact_key!r} requires explicit "
                "include_noncanonical=True"
            )

        records[artifact_key] = {
            "artifact_key": artifact_key,
            "producer_notebook": str(artifact.get("producer_notebook", "")),
            "relative_path": str(artifact.get("relative_path", "")),
            "artifact_type": str(artifact.get("artifact_type", "")),
            "artifact_role": str(artifact.get("artifact_role", "")),
            "schema_version": str(artifact.get("schema_version", "")),
            "dataset_scope": str(artifact.get("dataset_scope", "")),
            "experiment_scope": str(
                artifact.get(
                    "experiment_scope",
                    artifact.get("experiment_id", ""),
                )
            ),
            "validation_status": validation_status,
            "row_count": artifact.get("row_count", ""),
            "file_count": artifact.get("file_count", ""),
            "checksum": str(artifact.get("checksum", "")),
        }

    updated = {
        "registry_schema_version": PROJECT_PATHS_SCHEMA_VERSION,
        "updated_at_utc": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "artifacts": [
            records[key] for key in sorted(records)
        ],
    }
    updated_errors = validate_project_paths_registry(updated)
    if updated_errors:
        raise ValueError(
            "Updated registry violates its contract: "
            + "; ".join(updated_errors)
        )
    return updated


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_project_paths_registry(
    payload: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> tuple[Path, Path]:
    """Validate and atomically write JSON plus generated Markdown registry views."""
    errors = validate_project_paths_registry(payload)
    if errors:
        raise ValueError("Cannot write invalid registry: " + "; ".join(errors))

    root = find_project_root(project_root)
    inventory_dir = root / "outputs" / "inventory"
    json_path = inventory_dir / "project_paths.json"
    markdown_path = inventory_dir / "project_paths.md"
    normalized = dict(payload)
    normalized["updated_at_utc"] = (
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    json_text = json.dumps(normalized, indent=2, ensure_ascii=False) + "\n"
    _atomic_write_text(json_path, json_text)
    _atomic_write_text(markdown_path, render_project_paths_markdown(normalized))
    return json_path, markdown_path


PROJECT_ROOT = find_project_root()
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_IMAGES_DIR = RAW_DIR / "images"
RAW_METADATA_DIR = RAW_DIR / "metadata"
MODEL_AUDIT_DIR = DATA_DIR / "model_audit"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
INVENTORY_DIR = OUTPUTS_DIR / "inventory"
PROJECT_FILE_INVENTORY_PATH = INVENTORY_DIR / "project_file_inventory.csv"
INVENTORY_RUN_PATH = INVENTORY_DIR / "inventory_run.json"
PROJECT_PATHS_JSON_PATH = INVENTORY_DIR / "project_paths.json"
PROJECT_PATHS_MARKDOWN_PATH = INVENTORY_DIR / "project_paths.md"
