"""Preparation helpers for Notebook 34 dashboard assets.

The module owns configuration validation, input-contract inspection, normalized
dashboard schemas, safe persistence, and path/manifest utilities. It packages
validated upstream evidence and deliberately does not compute scientific metrics,
run restoration inference, or infer conservation approval.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import pandas as pd
import yaml


MODULE_NAME = "restoration_eval.dashboard_assets"
MODULE_VERSION = "1.0.0"
CONFIG_SCHEMA_VERSION = "dashboard_assets_config.v1"
DASHBOARD_PACKAGE_SCHEMA_VERSION = "dashboard_package.v1"

VALIDATION_COLUMNS = (
    "check_id",
    "validation_stage",
    "severity",
    "check_name",
    "observed",
    "expected",
    "passed",
    "issue",
)

HEADLINE_FINDING_COLUMNS = (
    "finding_id", "page_id", "display_order", "finding_type", "title",
    "value", "value_unit", "conclusion", "evidence_strength", "tone",
    "scope", "denominator", "source_notebook_ids_json",
    "source_paths_json", "limitation", "schema_version", "status", "issue",
)

STUDY_DESIGN_COLUMNS = (
    "design_row_id", "page_id", "section_id", "display_order", "record_type",
    "experiment_id", "display_name", "group_field", "group_value", "value",
    "value_unit", "scope", "denominator", "source_notebook_ids_json",
    "source_paths_json", "interpretation", "schema_version", "status", "issue",
)

METRIC_FRAMEWORK_COLUMNS = (
    "metric_row_id", "page_id", "section_id", "display_order", "record_type",
    "policy_id", "metric_family", "metric_name", "feature_model_id",
    "region_id", "region_type", "compatible", "primary_role",
    "comparison_direction", "ablation_policy_ids_json", "value", "value_unit",
    "scope", "source_notebook_ids_json", "source_paths_json", "interpretation",
    "limitation", "schema_version", "status", "issue",
)

PERFORMANCE_SUMMARY_COLUMNS = (
    "performance_row_id", "page_id", "section_id", "display_order",
    "record_type", "population_id", "analysis_scope", "scope_value",
    "experiment_id", "condition_field", "condition_value", "evidence_family",
    "metric_family", "metric_id", "metric_name", "feature_model_id",
    "region_id", "summary_statistic", "comparison_direction", "model_id",
    "estimate", "interval_low", "interval_high", "rank", "winner_model_id",
    "case_count", "painting_count", "coverage_fraction", "applicability_status",
    "source_notebook_ids_json", "source_paths_json", "interpretation",
    "schema_version", "status", "issue",
)

SENSITIVITY_SUMMARY_COLUMNS = (
    "sensitivity_row_id", "page_id", "section_id", "display_order",
    "analysis_family", "analysis_kind", "experiment_id", "condition_field",
    "condition_value", "condition_order", "evidence_family", "metric_family",
    "metric_name", "feature_model_id", "region_id", "summary_statistic",
    "comparison_direction", "model_id", "comparison_model_id", "estimate_name",
    "estimate", "interval_low", "interval_high", "effect_size_name",
    "effect_size", "p_value", "q_value", "independent_unit", "n_paintings",
    "n_cases", "n_observations", "applicability_status",
    "source_notebook_ids_json", "source_paths_json", "interpretation",
    "schema_version", "status", "issue",
)

UNCERTAINTY_SUMMARY_COLUMNS = (
    "uncertainty_row_id", "page_id", "section_id", "display_order",
    "record_type", "population_id", "experiment_id", "damage_or_degradation_type",
    "prompt_variant_id", "uncertainty_group_id", "painting_id", "category",
    "metric_family", "metric_name", "region_id", "summary_statistic", "value",
    "value_unit", "seed_count", "group_count", "case_count", "applicability_status",
    "is_calibrated_confidence", "source_notebook_ids_json", "source_paths_json",
    "interpretation", "limitation", "schema_version", "status", "issue",
)

TRUSTWORTHINESS_SUMMARY_COLUMNS = (
    "trust_row_id", "page_id", "section_id", "display_order", "record_type",
    "entity_id", "display_name", "model_id", "experiment_id", "category",
    "damage_or_degradation_type", "recommendation_category", "flag_id",
    "flag_status", "failure_category_id", "failure_status", "value", "value_unit",
    "candidate_count", "case_count", "painting_count", "affected_regions_json",
    "recommended_action", "source_notebook_ids_json", "source_paths_json",
    "interpretation", "limitation", "schema_version", "status", "issue",
)

COMPUTE_SUMMARY_COLUMNS = (
    "compute_row_id", "page_id", "section_id", "display_order", "record_type",
    "model_id", "display_name", "evaluation_status", "scenario_id",
    "experiment_id", "painting_count", "case_count", "candidate_count",
    "inference_count", "runtime_seconds", "runtime_lower_seconds",
    "runtime_upper_seconds", "throughput_candidates_per_second",
    "gpu_peak_memory_bytes", "output_file_count", "output_storage_bytes",
    "is_executed", "is_projected", "projection_basis", "applicability_status",
    "strengths_json", "weaknesses_json", "limitations_json",
    "source_notebook_ids_json", "source_paths_json", "interpretation",
    "schema_version", "status", "issue",
)

RESEARCH_QUESTION_COVERAGE_COLUMNS = (
    "coverage_row_id", "research_question_id", "research_question",
    "display_order", "page_id", "evidence_role", "coverage_status",
    "source_notebook_ids_json", "source_paths_json", "supported_interpretation",
    "prohibited_interpretation", "schema_version", "status", "issue",
)

CASE_INDEX_COLUMNS = (
    "case_index_id", "candidate_id", "case_id", "painting_id", "model_id",
    "experiment_id", "prompt_variant_id", "population_role", "category",
    "style_or_period", "degradation_family", "severity", "clean_path",
    "damaged_path", "mask_path", "restored_path", "difference_paths_json",
    "uncertainty_paths_json", "seam_paths_json", "colour_paths_json",
    "texture_paths_json", "semantic_paths_json", "mask_boundary_paths_json",
    "recommendation_category", "manual_review_required",
    "triggered_flag_ids_json", "triggered_category_ids_json",
    "affected_regions_json", "recommended_actions_json",
    "metric_disagreement_ids_json", "uncertainty_group_id",
    "uncertainty_applicability", "report_selected", "case_report_path",
    "painting_report_path", "report_selection_roles_json",
    "evidence_source_notebook_ids_json", "evidence_coverage_status",
    "scope_status", "scope_note", "schema_version", "status", "issue",
)

PAINTING_INDEX_COLUMNS = (
    "painting_index_id", "painting_id", "dataset_sort_index", "title", "artist",
    "date_or_period", "style_or_period", "category", "medium", "source",
    "license", "rights_status", "raw_image_path", "metadata_completeness_pct",
    "case_count", "candidate_count", "model_count", "has_uncertainty",
    "has_selected_case_report", "painting_report_path", "painting_report_sha256",
    "painting_report_self_contained", "source_notebook_ids_json",
    "source_paths_json", "schema_version", "status", "issue",
)

VISUAL_ASSET_INDEX_COLUMNS = (
    "visual_asset_id", "asset_role", "asset_type", "page_id", "display_order",
    "candidate_id", "case_id", "painting_id", "model_id", "experiment_id",
    "uncertainty_group_id", "feature_model_id", "map_type", "region_id",
    "selection_role", "relative_path", "sha256", "size_bytes", "width", "height",
    "format", "source_notebook_id", "source_artifact_key", "is_default_visual",
    "applicability_status", "schema_version", "status", "issue",
)

REPORT_INDEX_COLUMNS = (
    "dashboard_report_id", "report_family", "report_role", "display_order",
    "title", "description", "model_id", "case_id", "painting_id", "report_path",
    "report_sha256", "size_bytes", "format", "self_contained", "section_count",
    "embedded_image_count", "embedded_tile_count", "source_notebook_id",
    "source_artifact_key", "scope", "applicability_status", "schema_version",
    "status", "issue",
)

DASHBOARD_ASSET_COLUMNS = (
    "dashboard_asset_id", "asset_key", "asset_group", "page_ids_json",
    "relative_path", "format", "schema_version", "row_count", "file_count",
    "size_bytes", "sha256", "source_notebook_ids_json", "source_paths_json",
    "validation_status", "status", "issue",
)

OUTPUT_SCHEMAS: dict[str, tuple[str, ...]] = {
    "headline_findings": HEADLINE_FINDING_COLUMNS,
    "study_design": STUDY_DESIGN_COLUMNS,
    "metric_framework": METRIC_FRAMEWORK_COLUMNS,
    "performance_summary": PERFORMANCE_SUMMARY_COLUMNS,
    "sensitivity_summary": SENSITIVITY_SUMMARY_COLUMNS,
    "uncertainty_summary": UNCERTAINTY_SUMMARY_COLUMNS,
    "trustworthiness_summary": TRUSTWORTHINESS_SUMMARY_COLUMNS,
    "compute_summary": COMPUTE_SUMMARY_COLUMNS,
    "research_question_coverage": RESEARCH_QUESTION_COVERAGE_COLUMNS,
    "case_index": CASE_INDEX_COLUMNS,
    "painting_index": PAINTING_INDEX_COLUMNS,
    "visual_asset_index": VISUAL_ASSET_INDEX_COLUMNS,
    "report_index": REPORT_INDEX_COLUMNS,
    "dashboard_assets": DASHBOARD_ASSET_COLUMNS,
}


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    return config.get("dashboard_assets", config)


def stable_id(prefix: str, *parts: Any) -> str:
    material = "|".join(str(part) for part in parts)
    suffix = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{suffix}"


def json_list(values: Iterable[Any]) -> str:
    return json.dumps([str(value) for value in values], ensure_ascii=False)


def parse_json_list(value: Any) -> list[Any]:
    if value is None:
        return []
    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    text = str(value).strip()
    if not text:
        return []
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError(f"Expected JSON list, received {type(parsed).__name__}")
    return parsed


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def is_repo_relative(value: Any) -> bool:
    text = str(value).strip()
    if not text:
        return False
    path = Path(text)
    return not path.is_absolute() and ".." not in path.parts


def validation_row(
    stage: str,
    check_name: str,
    observed: Any,
    expected: Any,
    passed: bool,
    issue: str = "",
    severity: str = "blocking",
) -> dict[str, Any]:
    def display(value: Any) -> str:
        if isinstance(value, (dict, list, tuple, set)):
            return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)
        return str(value)

    return {
        "check_id": stable_id("check", stage, check_name),
        "validation_stage": str(stage),
        "severity": str(severity),
        "check_name": str(check_name),
        "observed": display(observed),
        "expected": display(expected),
        "passed": bool(passed),
        "issue": "" if passed else str(issue),
    }


def load_dashboard_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the approved Notebook 34 configuration."""

    with Path(path).open("r", encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Notebook 34 configuration must be a mapping")
    if config.get("config_schema_version") != CONFIG_SCHEMA_VERSION:
        raise ValueError("Unexpected Notebook 34 configuration schema")

    settings = config.get("dashboard_assets")
    if not isinstance(settings, dict):
        raise ValueError("Missing dashboard_assets configuration section")
    if settings.get("notebook_id") != "34":
        raise ValueError("Notebook 34 identity is not locked")
    if settings.get("notebook_stem") != "34_final_streamlit_dashboard_assets":
        raise ValueError("Notebook 34 stem is not locked")
    if settings.get("creates_new_scientific_evidence") is not False:
        raise ValueError("Notebook 34 must remain presentation-only")
    if settings.get("dashboard_schema_version") != DASHBOARD_PACKAGE_SCHEMA_VERSION:
        raise ValueError("Unexpected dashboard package schema")

    manifests = settings.get("upstream_manifests", {})
    expected_ids = [f"{number:02d}" for number in range(1, 34)]
    if list(manifests) != expected_ids:
        raise ValueError("Upstream manifests must explicitly cover Notebooks 01-33")

    pages = settings.get("pages", [])
    expected_pages = [
        "overview", "study_design", "metric_framework", "model_performance",
        "robustness_uncertainty", "trustworthiness_xai", "case_explorer",
        "reports_reproducibility",
    ]
    observed_pages = [str(row.get("page_id", "")) for row in pages]
    if observed_pages != expected_pages:
        raise ValueError("Dashboard page order differs from the approved eight-page structure")

    presentation = settings.get("presentation", {})
    if presentation.get("approved_mock_structure_locked") is not True:
        raise ValueError("Dashboard mock structure must remain locked")
    if int(presentation.get("principal_page_count", -1)) != len(expected_pages):
        raise ValueError("Principal page count does not match the page plan")
    if len(expected_pages) > int(presentation.get("principal_page_limit", 0)):
        raise ValueError("Principal page plan exceeds the approved limit")

    output = settings.get("output", {})
    expected_output_keys = {
        "root", "dashboard_summary_path", "dashboard_tables_dir",
        "dashboard_indexes_dir", "headline_findings_path", "study_design_path",
        "metric_framework_path", "performance_summary_path",
        "sensitivity_summary_path", "uncertainty_summary_path",
        "trustworthiness_summary_path", "compute_summary_path",
        "research_question_coverage_path", "case_index_path",
        "painting_index_path", "visual_asset_index_path", "report_index_path",
        "filter_options_path", "dashboard_assets_path", "run_manifest_path",
        "artifacts_path", "validation_path", "work_dir",
    }
    missing_output_keys = sorted(expected_output_keys - set(output))
    if missing_output_keys:
        raise ValueError(f"Missing output contract keys: {missing_output_keys}")
    if output.get("root") != "outputs/34_final_streamlit_dashboard_assets":
        raise ValueError("Notebook 34 output root differs from the approved root")

    schema_keys = set(settings.get("expected_output_schemas", {}))
    expected_schema_keys = set(OUTPUT_SCHEMAS) | {"filter_options"}
    if schema_keys != expected_schema_keys:
        raise ValueError(
            "Expected output schema keys differ: "
            f"missing={sorted(expected_schema_keys - schema_keys)}, "
            f"extra={sorted(schema_keys - expected_schema_keys)}"
        )

    return config


def resolve_output_paths(
    project_root: str | Path,
    config: Mapping[str, Any],
) -> dict[str, Path]:
    root = Path(project_root).resolve()
    output = _settings(config)["output"]
    output_root = root / output["root"]
    resolved: dict[str, Path] = {"root": output_root}
    for key, value in output.items():
        if key == "root":
            continue
        resolved[key] = output_root / str(value)
    return resolved


def create_output_directories(paths: Mapping[str, Path]) -> None:
    """Create only the directories declared by the Notebook 34 contract."""

    directory_keys = {
        "root", "dashboard_tables_dir", "dashboard_indexes_dir", "work_dir",
    }
    for key in directory_keys:
        paths[key].mkdir(parents=True, exist_ok=True)
    for key, path in paths.items():
        if key not in directory_keys:
            path.parent.mkdir(parents=True, exist_ok=True)


def read_csv_contract(
    path: str | Path,
    *,
    required_columns: Sequence[str] = (),
    expected_rows: int | None = None,
    dtype: Any = None,
) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=dtype, low_memory=False)
    missing = sorted(set(required_columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{Path(path).name} missing required columns: {missing}")
    if expected_rows is not None and len(frame) != int(expected_rows):
        raise ValueError(
            f"{Path(path).name} has {len(frame)} rows; expected {int(expected_rows)}"
        )
    return frame


def validate_input_table_contracts(
    project_root: str | Path,
    config: Mapping[str, Any],
    *,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Load all declared input tables and return blocking contract checks."""

    root = Path(project_root).resolve()
    settings = _settings(config)
    contracts = settings["input_table_contracts"]
    inputs = settings["inputs"]
    tables: dict[str, pd.DataFrame] = {}
    checks: list[dict[str, Any]] = []
    total = len(contracts)

    for number, (input_key, contract) in enumerate(contracts.items(), start=1):
        relative = inputs[input_key]
        path = root / relative
        exists = path.is_file()
        checks.append(validation_row(
            "batch_1_preflight", f"{input_key}_exists", exists, True, exists,
            f"Missing declared input table: {relative}",
        ))
        if not exists:
            if progress_callback:
                progress_callback(number, total, input_key)
            continue

        try:
            frame = read_csv_contract(
                path,
                required_columns=contract.get("required_columns", []),
                expected_rows=contract.get("rows"),
            )
            tables[input_key] = frame
            checks.append(validation_row(
                "batch_1_preflight", f"{input_key}_row_count", len(frame),
                int(contract["rows"]), len(frame) == int(contract["rows"]),
                f"Unexpected row count for {relative}",
            ))
            missing = sorted(set(contract.get("required_columns", [])) - set(frame.columns))
            checks.append(validation_row(
                "batch_1_preflight", f"{input_key}_required_columns", missing,
                [], not missing, f"Missing required columns for {relative}: {missing}",
            ))
        except Exception as exc:
            checks.append(validation_row(
                "batch_1_preflight", f"{input_key}_load", type(exc).__name__,
                "loadable with declared contract", False,
                f"{type(exc).__name__}: {exc}",
            ))
        if progress_callback:
            progress_callback(number, total, input_key)

    return tables, pd.DataFrame(checks, columns=VALIDATION_COLUMNS)


def load_upstream_manifests(
    project_root: str | Path,
    config: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], pd.DataFrame]:
    """Load and validate completed run manifests for Notebooks 01-33."""

    root = Path(project_root).resolve()
    manifests: dict[str, dict[str, Any]] = {}
    checks: list[dict[str, Any]] = []
    for notebook_id, relative in _settings(config)["upstream_manifests"].items():
        path = root / relative
        exists = path.is_file()
        checks.append(validation_row(
            "batch_1_preflight", f"manifest_{notebook_id}_exists", exists, True,
            exists, f"Missing upstream manifest: {relative}",
        ))
        if not exists:
            continue
        with path.open("r", encoding="utf-8-sig") as handle:
            manifest = json.load(handle)
        manifests[notebook_id] = manifest
        observed_id = str(manifest.get("notebook_id", "")).zfill(2)
        completed = manifest.get("run_status") == "completed"
        checks.append(validation_row(
            "batch_1_preflight", f"manifest_{notebook_id}_identity", observed_id,
            notebook_id, observed_id == notebook_id,
            f"Manifest identity mismatch for {relative}",
        ))
        checks.append(validation_row(
            "batch_1_preflight", f"manifest_{notebook_id}_completed",
            manifest.get("run_status"), "completed", completed,
            f"Upstream manifest is not completed: {relative}",
        ))
    return manifests, pd.DataFrame(checks, columns=VALIDATION_COLUMNS)


def validate_output_frame(frame: pd.DataFrame, schema_key: str) -> pd.DataFrame:
    """Return a frame in exact schema order or raise on missing/extra columns."""

    if schema_key not in OUTPUT_SCHEMAS:
        raise KeyError(f"Unknown dashboard output schema: {schema_key}")
    expected = list(OUTPUT_SCHEMAS[schema_key])
    missing = sorted(set(expected) - set(frame.columns))
    extra = sorted(set(frame.columns) - set(expected))
    if missing or extra:
        raise ValueError(
            f"{schema_key} schema mismatch: missing={missing}, extra={extra}"
        )
    return frame.loc[:, expected].copy()


def empty_output_frame(schema_key: str) -> pd.DataFrame:
    if schema_key not in OUTPUT_SCHEMAS:
        raise KeyError(f"Unknown dashboard output schema: {schema_key}")
    return pd.DataFrame(columns=OUTPUT_SCHEMAS[schema_key])


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_path(path: str | Path) -> str:
    target = Path(path)
    if target.is_file():
        return sha256_file(target)
    if not target.is_dir():
        raise FileNotFoundError(target)
    digest = hashlib.sha256()
    for child in sorted(item for item in target.rglob("*") if item.is_file()):
        relative = child.relative_to(target).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(sha256_file(child)))
    return digest.hexdigest()


def path_statistics(path: str | Path) -> dict[str, int]:
    target = Path(path)
    if target.is_file():
        return {"file_count": 1, "size_bytes": int(target.stat().st_size)}
    if not target.is_dir():
        raise FileNotFoundError(target)
    files = [item for item in target.rglob("*") if item.is_file()]
    return {
        "file_count": len(files),
        "size_bytes": sum(int(item.stat().st_size) for item in files),
    }


def atomic_write_json(payload: Mapping[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(dict(payload), indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    _replace_with_retry(temporary, target)


def atomic_write_csv(frame: pd.DataFrame, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}.{uuid.uuid4().hex}.tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8", lineterminator="\n")
    _replace_with_retry(temporary, target)


def _replace_with_retry(
    source: Path,
    target: Path,
    *,
    attempts: int = 8,
    initial_delay_seconds: float = 0.05,
) -> None:
    delay = float(initial_delay_seconds)
    for attempt in range(1, attempts + 1):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == attempts:
                raise
            time.sleep(delay)
            delay *= 2


def blocking_failures(checks: pd.DataFrame) -> pd.DataFrame:
    if checks.empty:
        return checks.copy()
    passed = checks["passed"].map(as_bool)
    return checks[(checks["severity"] == "blocking") & ~passed].copy()


def assert_no_blocking_failures(checks: pd.DataFrame, *, stage: str) -> None:
    failures = blocking_failures(checks)
    if failures.empty:
        return
    details = failures[["check_name", "issue"]].to_dict("records")
    raise AssertionError(f"{stage} has {len(failures)} blocking failures: {details}")

