"""Read-only loading, path safety, and validation for the Streamlit dashboard.

The module deliberately contains no Streamlit dependency.  Notebook 35 can use
the same contract checks as the application without importing or launching the
UI, and the application remains a presentation-only consumer of Notebook 34.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd
import yaml

from .manifests import sha256_file
from .paths import find_project_root, resolve_repo_path, to_repo_relative


DASHBOARD_APPLICATION_VERSION = "1.0.0"
DASHBOARD_VALIDATION_CONFIG_SCHEMA_VERSION = "dashboard_validation_config.v1"
DASHBOARD_PACKAGE_SCHEMA_VERSION = "dashboard_package.v1"


class DashboardContractError(RuntimeError):
    """Raised when the immutable dashboard input contract is violated."""


@dataclass(frozen=True)
class DashboardBundle:
    """Loaded Notebook 34 presentation package."""

    project_root: Path
    config: Mapping[str, Any]
    summary: Mapping[str, Any]
    filters: Mapping[str, Any]
    upstream_manifest: Mapping[str, Any]
    tables: Mapping[str, pd.DataFrame]
    indexes: Mapping[str, pd.DataFrame]
    dashboard_assets: pd.DataFrame
    upstream_checks: pd.DataFrame


TABLE_KEYS = (
    "headline_findings",
    "study_design",
    "metric_framework",
    "performance_summary",
    "sensitivity_summary",
    "uncertainty_summary",
    "trustworthiness_summary",
    "compute_summary",
    "research_question_coverage",
)
INDEX_KEYS = (
    "case_index",
    "painting_index",
    "visual_asset_index",
    "report_index",
)
CSV_KEYS = (*TABLE_KEYS, *INDEX_KEYS, "dashboard_assets", "upstream_validation")
JSON_KEYS = ("dashboard_summary", "filter_options", "upstream_run_manifest")


def load_dashboard_validation_config(
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    """Load and minimally validate the versioned Notebook 35 contract."""

    root = find_project_root(project_root)
    path = root / "config" / "evaluation" / "dashboard_validation.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Dashboard validation configuration is missing: {path}")
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise DashboardContractError("Dashboard validation configuration must be a mapping")
    if payload.get("schema_version") != DASHBOARD_VALIDATION_CONFIG_SCHEMA_VERSION:
        raise DashboardContractError(
            "Unsupported dashboard validation configuration schema: "
            f"{payload.get('schema_version')!r}"
        )
    for key in (
        "notebook",
        "application",
        "required_inputs",
        "required_columns",
        "expected_population",
        "runtime",
        "presentation",
        "scientific_boundaries",
        "outputs",
    ):
        if key not in payload:
            raise DashboardContractError(f"Configuration section is missing: {key}")
    return payload


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise DashboardContractError(f"Expected a JSON object: {path}")
    return payload


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def required_input_paths(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> dict[str, Path]:
    """Resolve every declared input and reject repository escapes."""

    root = find_project_root(project_root)
    result: dict[str, Path] = {}
    for key, contract in config["required_inputs"].items():
        if not isinstance(contract, Mapping) or not contract.get("path"):
            raise DashboardContractError(f"Invalid required-input contract: {key}")
        result[str(key)] = resolve_repo_path(contract["path"], root)
    return result


def load_dashboard_package(
    project_root: str | Path | None = None,
    *,
    require_all_files: bool = True,
) -> DashboardBundle:
    """Load only the fixed Notebook 34 dashboard package."""

    root = find_project_root(project_root)
    config = load_dashboard_validation_config(root)
    paths = required_input_paths(config, root)
    if require_all_files:
        missing = [to_repo_relative(path, root) for path in paths.values() if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"Required dashboard inputs are missing: {missing}")

    tables = {key: _read_csv(paths[key]) for key in TABLE_KEYS}
    indexes = {key: _read_csv(paths[key]) for key in INDEX_KEYS}
    return DashboardBundle(
        project_root=root,
        config=config,
        summary=_read_json(paths["dashboard_summary"]),
        filters=_read_json(paths["filter_options"]),
        upstream_manifest=_read_json(paths["upstream_run_manifest"]),
        tables=tables,
        indexes=indexes,
        dashboard_assets=_read_csv(paths["dashboard_assets"]),
        upstream_checks=_read_csv(paths["upstream_validation"]),
    )


def json_list(value: Any) -> list[Any]:
    """Return a JSON-list cell as a list; malformed or empty values become []."""

    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return value
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def truthy(value: Any) -> bool:
    """Normalize CSV/JSON boolean representations."""

    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "passed", "ok"}


def display_label(value: Any) -> str:
    """Turn stable snake-case identifiers into compact display labels."""

    text = str(value or "").strip()
    known = {
        "lama": "LaMa",
        "opencv_telea": "OpenCV Telea",
        "stable_diffusion_inpainting": "Stable Diffusion",
        "sdxl_inpainting": "SDXL",
        "lpips": "LPIPS",
        "clip": "CLIP",
        "dinov2": "DINOv2",
        "ssim": "SSIM",
        "psnr": "PSNR",
    }
    return known.get(text.lower(), text.replace("_", " ").strip().title())


def safe_project_path(
    value: Any,
    project_root: str | Path | None = None,
    *,
    must_exist: bool = True,
    allowed_suffixes: Iterable[str] | None = None,
) -> Path | None:
    """Resolve an indexed repository path without allowing arbitrary file access."""

    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    path = resolve_repo_path(text, project_root)
    if must_exist and not path.is_file():
        return None
    if allowed_suffixes:
        suffixes = {str(item).lower() for item in allowed_suffixes}
        if path.suffix.lower() not in suffixes:
            return None
    return path


def case_visual_paths(
    row: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> dict[str, list[Path]]:
    """Resolve primary and diagnostic paths from one approved case-index row."""

    primary: dict[str, list[Path]] = {}
    for key in ("clean_path", "damaged_path", "mask_path", "restored_path"):
        path = safe_project_path(
            row.get(key), project_root, allowed_suffixes={".png", ".jpg", ".jpeg", ".webp"}
        )
        primary[key] = [path] if path is not None else []
    for key in (
        "difference_paths_json",
        "uncertainty_paths_json",
        "seam_paths_json",
        "colour_paths_json",
        "texture_paths_json",
        "semantic_paths_json",
        "mask_boundary_paths_json",
    ):
        primary[key] = [
            path
            for item in json_list(row.get(key))
            if (
                path := safe_project_path(
                    item,
                    project_root,
                    allowed_suffixes={".png", ".jpg", ".jpeg", ".webp"},
                )
            )
            is not None
        ]
    return primary


def filter_frame(frame: pd.DataFrame, **filters: Any) -> pd.DataFrame:
    """Apply exact scalar or membership filters while treating blanks as no filter."""

    result = frame
    for column, selection in filters.items():
        if column not in result.columns or selection in (None, "", "All"):
            continue
        if isinstance(selection, (list, tuple, set, frozenset)):
            values = [item for item in selection if item not in (None, "", "All")]
            if values:
                result = result[result[column].isin(values)]
        else:
            result = result[result[column] == selection]
    return result.copy()


def stable_options(frame: pd.DataFrame, column: str) -> list[str]:
    """Return sorted, non-empty string options from a dataframe column."""

    if column not in frame.columns:
        return []
    values = frame[column].dropna().astype(str).str.strip()
    return sorted(value for value in values.unique().tolist() if value)


def default_case_rows(case_index: pd.DataFrame) -> pd.DataFrame:
    """Choose deterministic representative defaults without narrowing access."""

    selected = case_index[
        case_index.get("report_selected", pd.Series(False, index=case_index.index)).map(truthy)
    ]
    if selected.empty:
        selected = case_index
    sort_columns = [
        column
        for column in ("painting_id", "case_id", "model_id", "candidate_id")
        if column in selected.columns
    ]
    return selected.sort_values(sort_columns, kind="stable") if sort_columns else selected


def report_bytes(
    relative_path: Any,
    project_root: str | Path | None = None,
) -> tuple[bytes, str] | None:
    """Read an indexed self-contained report for an explicit download action."""

    path = safe_project_path(
        relative_path,
        project_root,
        allowed_suffixes={".html", ".md", ".pdf", ".csv", ".json"},
    )
    if path is None:
        return None
    return path.read_bytes(), path.name


def _check(
    records: list[dict[str, Any]],
    *,
    stage: str,
    check_id: str,
    description: str,
    severity: str,
    expected: Any,
    observed: Any,
    passed: bool,
    details: Any = "",
) -> None:
    records.append(
        {
            "validation_stage": stage,
            "check_id": check_id,
            "check_description": description,
            "severity": severity,
            "expected": json.dumps(expected, ensure_ascii=False, default=str)
            if isinstance(expected, (dict, list, tuple))
            else str(expected),
            "observed": json.dumps(observed, ensure_ascii=False, default=str)
            if isinstance(observed, (dict, list, tuple))
            else str(observed),
            "passed": bool(passed),
            "details": json.dumps(details, ensure_ascii=False, default=str)
            if isinstance(details, (dict, list, tuple))
            else str(details),
        }
    )


def audit_dashboard_package(
    project_root: str | Path | None = None,
) -> pd.DataFrame:
    """Return deterministic file, row, column, schema, and population checks."""

    root = find_project_root(project_root)
    config = load_dashboard_validation_config(root)
    paths = required_input_paths(config, root)
    records: list[dict[str, Any]] = []

    for key, path in paths.items():
        _check(
            records,
            stage="package_paths",
            check_id=f"required_file__{key}",
            description=f"Required dashboard input exists: {key}",
            severity="blocking",
            expected="existing file",
            observed=to_repo_relative(path, root),
            passed=path.is_file(),
        )
    if any(not path.is_file() for path in paths.values()):
        return pd.DataFrame.from_records(records)

    bundle = load_dashboard_package(root)
    frames = {
        **bundle.tables,
        **bundle.indexes,
        "dashboard_assets": bundle.dashboard_assets,
        "upstream_validation": bundle.upstream_checks,
    }
    for key, frame in frames.items():
        contract = config["required_inputs"][key]
        expected_rows = contract.get("rows")
        if expected_rows is not None:
            _check(
                records,
                stage="package_rows",
                check_id=f"row_count__{key}",
                description=f"Dashboard input has the approved row count: {key}",
                severity="blocking",
                expected=int(expected_rows),
                observed=int(len(frame)),
                passed=len(frame) == int(expected_rows),
            )
        required = set(config.get("required_columns", {}).get(key, []))
        missing = sorted(required - set(frame.columns))
        _check(
            records,
            stage="package_schema",
            check_id=f"columns__{key}",
            description=f"Dashboard input exposes required columns: {key}",
            severity="blocking",
            expected="all declared columns",
            observed={"missing": missing, "column_count": len(frame.columns)},
            passed=not missing,
        )
        if "status" in frame.columns:
            invalid_status = int((frame["status"].fillna("").astype(str) != "ok").sum())
            _check(
                records,
                stage="package_status",
                check_id=f"status__{key}",
                description=f"Dashboard input rows are approved: {key}",
                severity="blocking",
                expected=0,
                observed=invalid_status,
                passed=invalid_status == 0,
            )

    summary_schema = bundle.summary.get("schema_version")
    _check(
        records,
        stage="package_schema",
        check_id="dashboard_summary_schema",
        description="Dashboard summary uses the approved package schema",
        severity="blocking",
        expected=DASHBOARD_PACKAGE_SCHEMA_VERSION,
        observed=summary_schema,
        passed=summary_schema == DASHBOARD_PACKAGE_SCHEMA_VERSION,
    )
    expected_pages = list(config["application"]["page_ids"])
    observed_pages = [item.get("page_id") for item in bundle.summary.get("pages", [])]
    _check(
        records,
        stage="package_scope",
        check_id="page_contract",
        description="Dashboard package contains the exact approved page sequence",
        severity="blocking",
        expected=expected_pages,
        observed=observed_pages,
        passed=observed_pages == expected_pages,
    )
    for key, expected in config["expected_population"].items():
        observed = bundle.summary.get("population", {}).get(key)
        _check(
            records,
            stage="package_population",
            check_id=f"population__{key}",
            description=f"Dashboard summary preserves approved population: {key}",
            severity="blocking",
            expected=expected,
            observed=observed,
            passed=observed == expected,
        )

    upstream_failed = bundle.upstream_checks[
        (~bundle.upstream_checks["passed"].map(truthy))
        & bundle.upstream_checks["severity"].isin(["error", "blocking"])
    ]
    _check(
        records,
        stage="upstream_validation",
        check_id="notebook_34_blocking_failures",
        description="Notebook 34 has no error or blocking validation failures",
        severity="blocking",
        expected=0,
        observed=int(len(upstream_failed)),
        passed=upstream_failed.empty,
    )
    return pd.DataFrame.from_records(records)


def audit_indexed_paths(
    bundle: DashboardBundle,
    *,
    include_all_visuals: bool = True,
) -> pd.DataFrame:
    """Check every indexed primary/report path and optionally every visual path."""

    records: list[dict[str, Any]] = []
    groups: list[tuple[str, pd.DataFrame, Sequence[str]]] = [
        (
            "case_index",
            bundle.indexes["case_index"],
            ("clean_path", "damaged_path", "mask_path", "restored_path"),
        ),
        ("painting_index", bundle.indexes["painting_index"], ("raw_image_path",)),
        ("report_index", bundle.indexes["report_index"], ("report_path",)),
    ]
    if include_all_visuals:
        groups.append(
            ("visual_asset_index", bundle.indexes["visual_asset_index"], ("relative_path",))
        )
    for group_name, frame, columns in groups:
        for column in columns:
            values = frame[column].dropna().astype(str).str.strip()
            values = sorted(value for value in values.unique().tolist() if value)
            missing: list[str] = []
            unsafe: list[str] = []
            for value in values:
                try:
                    path = resolve_repo_path(value, bundle.project_root)
                except ValueError:
                    unsafe.append(value)
                    continue
                if not path.is_file():
                    missing.append(value)
            _check(
                records,
                stage="indexed_paths",
                check_id=f"{group_name}__{column}",
                description=f"Indexed paths resolve safely and exist: {group_name}.{column}",
                severity="blocking",
                expected={"missing": 0, "unsafe": 0},
                observed={
                    "unique_paths": len(values),
                    "missing": len(missing),
                    "unsafe": len(unsafe),
                },
                passed=not missing and not unsafe,
                details={"missing_examples": missing[:10], "unsafe_examples": unsafe[:10]},
            )
    return pd.DataFrame.from_records(records)


def audit_streamlit_source(
    project_root: str | Path | None = None,
) -> pd.DataFrame:
    """Perform safe static checks without importing or launching Streamlit."""

    root = find_project_root(project_root)
    config = load_dashboard_validation_config(root)
    app_path = resolve_repo_path(config["application"]["entrypoint"], root)
    source = app_path.read_text(encoding="utf-8") if app_path.is_file() else ""
    records: list[dict[str, Any]] = []
    try:
        tree = ast.parse(source, filename=str(app_path))
        syntax_ok = True
        syntax_detail = ""
    except SyntaxError as exc:
        tree = None
        syntax_ok = False
        syntax_detail = f"{exc.msg} at line {exc.lineno}"
    _check(
        records,
        stage="application_static",
        check_id="python_syntax",
        description="Streamlit entrypoint parses as Python",
        severity="blocking",
        expected="valid Python syntax",
        observed=syntax_detail or "valid",
        passed=syntax_ok,
    )

    prohibited = config["scientific_boundaries"]["prohibited_source_fragments"]
    for fragment in prohibited:
        fragment_text = str(fragment)
        if fragment_text.isalnum():
            present = bool(
                re.search(rf"\b{re.escape(fragment_text)}\b", source, flags=re.IGNORECASE)
            )
        else:
            present = fragment_text.casefold() in source.casefold()
        _check(
            records,
            stage="application_static",
            check_id=f"prohibited_fragment__{str(fragment).replace(' ', '_')}",
            description=f"Application excludes obsolete or unsupported source fragment: {fragment}",
            severity="blocking",
            expected=False,
            observed=present,
            passed=not present,
        )

    for page_id, display_name in config["application"]["display_names"].items():
        present = str(display_name) in source
        _check(
            records,
            stage="application_pages",
            check_id=f"page__{page_id}",
            description=f"Application implements approved page: {display_name}",
            severity="blocking",
            expected=True,
            observed=present,
            passed=present,
        )

    forbidden_write_calls: list[str] = []
    if tree is not None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = ""
            if isinstance(node.func, ast.Attribute):
                name = node.func.attr
            elif isinstance(node.func, ast.Name):
                name = node.func.id
            if name in {
                "to_csv",
                "to_json",
                "to_parquet",
                "write_text",
                "write_bytes",
                "mkdir",
                "makedirs",
                "remove",
                "unlink",
                "rename",
            }:
                forbidden_write_calls.append(f"{name}@{getattr(node, 'lineno', '?')}")
    _check(
        records,
        stage="application_boundaries",
        check_id="read_only_application",
        description="Application source contains no filesystem or dataframe write calls",
        severity="blocking",
        expected=[],
        observed=forbidden_write_calls,
        passed=not forbidden_write_calls,
    )
    return pd.DataFrame.from_records(records)


def configuration_checksum(project_root: str | Path | None = None) -> str:
    """Return the current Notebook 35 configuration checksum."""

    root = find_project_root(project_root)
    return sha256_file(root / "config" / "evaluation" / "dashboard_validation.yaml")
