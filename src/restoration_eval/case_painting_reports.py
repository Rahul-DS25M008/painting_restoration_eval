"""Presentation-only case and painting report utilities for Notebook 32.

The module consumes validated Notebook 01 and Notebook 09--31 artifacts.  It
does not compute new scientific metrics or statistical results.  It owns the
approved report population, deterministic case-selection policy, standalone
HTML checks, normalized report indexes, and mock-to-final traceability contract.
"""

from __future__ import annotations

import base64
import hashlib
import html
import io
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd
import yaml
from PIL import Image


MODULE_NAME = "restoration_eval.case_painting_reports"
MODULE_VERSION = "1.0.0"
CONFIG_SCHEMA_VERSION = "case_and_painting_reports_config.v1"
SELECTED_CASES_SCHEMA_VERSION = "selected_report_cases.v1"
CASE_REPORT_INDEX_SCHEMA_VERSION = "case_report_index.v1"
PAINTING_REPORT_INDEX_SCHEMA_VERSION = "painting_report_index.v1"
TRACEABILITY_SCHEMA_VERSION = "case_painting_mock_traceability.v1"

VALIDATION_COLUMNS = (
    "check_id", "stage", "severity", "check_name", "observed", "expected",
    "passed", "issue",
)

CASE_SUMMARY_COLUMNS = (
    "case_id", "painting_id", "category", "style_or_period",
    "experiment_id", "degradation_family", "severity", "candidate_count",
    "model_count", "model_ids_json", "candidate_ids_json",
    "prompt_variant_count", "prompt_variant_ids_json", "uncertainty_group_count",
    "uncertainty_group_ids_json", "lower_risk_candidate_count",
    "manual_review_candidate_count", "triggered_flag_count",
    "triggered_flag_ids_json", "metric_disagreement_count",
    "metric_disagreement_ids_json", "has_sdxl", "has_uncertainty",
    "has_scratch_prompt_pair", "notebook_29_report_selected",
    "evidence_coverage_complete", "schema_version", "status", "issue",
)

SELECTED_CASE_COLUMNS = (
    "selection_id", "selection_order", "selection_lane", "selection_reason",
    "selection_reasons_json", "case_id", "painting_id", "category",
    "style_or_period", "experiment_id", "degradation_family", "severity",
    "candidate_count", "model_count", "model_ids_json", "candidate_ids_json",
    "prompt_variant_count", "uncertainty_group_count", "uncertainty_score",
    "lower_risk_candidate_count", "manual_review_candidate_count",
    "triggered_flag_count", "metric_disagreement_count", "has_sdxl",
    "has_uncertainty", "has_scratch_prompt_pair",
    "notebook_29_report_selected", "schema_version", "status", "issue",
)

PAINTING_SUMMARY_COLUMNS = (
    "painting_id", "title", "artist", "style_or_period", "category",
    "metadata_completeness_pct", "case_count", "candidate_count",
    "model_count", "model_ids_json", "experiment_count", "experiment_ids_json",
    "degradation_count", "degradation_families_json", "manual_review_case_count",
    "flagged_case_count", "uncertainty_case_count", "sdxl_case_count",
    "is_extension_painting", "schema_version", "status", "issue",
)

CASE_REPORT_INDEX_COLUMNS = (
    "report_id", "case_id", "painting_id", "selection_order",
    "selection_lane", "selection_reasons_json", "candidate_count", "model_count",
    "report_path", "report_sha256", "size_bytes", "section_count",
    "embedded_image_count", "embedded_tile_count", "self_contained",
    "source_artifact_paths_json", "upstream_run_ids_json", "generated_at_utc",
    "schema_version", "status", "issue",
)

PAINTING_REPORT_INDEX_COLUMNS = (
    "report_id", "painting_id", "category", "style_or_period", "case_count",
    "candidate_count", "model_count", "is_extension_painting", "report_path",
    "report_sha256", "size_bytes", "section_count", "embedded_image_count",
    "embedded_tile_count", "self_contained", "source_artifact_paths_json",
    "upstream_run_ids_json", "generated_at_utc", "schema_version", "status",
    "issue",
)

TRACEABILITY_COLUMNS = (
    "mock_element_id", "report_kind", "mock_section", "approved_role",
    "final_section", "canonical_evidence_source", "implementation_status",
    "deviation_reason", "schema_version", "status", "issue",
)


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    return config.get("case_and_painting_reports", config)


def _stable_id(prefix: str, *parts: Any) -> str:
    material = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or (
        not isinstance(value, (list, tuple, dict, set)) and pd.isna(value)
    ):
        return False
    return str(value).strip().lower() in {"true", "1", "1.0", "yes", "y"}


def _json_array(value: Any) -> list[Any]:
    if value is None or (
        not isinstance(value, (list, tuple, dict, set)) and pd.isna(value)
    ):
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return [text]
    if isinstance(value, Mapping):
        return list(value.values())
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _json_strings(values: Iterable[Any]) -> str:
    cleaned = sorted({str(value) for value in values if str(value).strip()})
    return json.dumps(cleaned, ensure_ascii=False)


def _relative_path(value: Any) -> bool:
    text = str(value).strip()
    return bool(text) and not Path(text).is_absolute() and "\\" not in text


def _validation_row(
    *,
    stage: str,
    severity: str,
    check_name: str,
    observed: Any,
    expected: Any,
    passed: bool,
    issue: str,
) -> dict[str, Any]:
    passed = bool(passed)
    return {
        "check_id": _stable_id("check", stage, check_name),
        "stage": stage,
        "severity": severity,
        "check_name": check_name,
        "observed": json.dumps(observed, ensure_ascii=False, default=str)
        if isinstance(observed, (dict, list, tuple)) else str(observed),
        "expected": json.dumps(expected, ensure_ascii=False, default=str)
        if isinstance(expected, (dict, list, tuple)) else str(expected),
        "passed": passed,
        "issue": "" if passed else issue,
    }


def sha256_path(path: str | Path) -> str:
    """Return a SHA-256 checksum for one file or a deterministic directory."""

    target = Path(path)
    digest = hashlib.sha256()
    if target.is_file():
        with target.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    if target.is_dir():
        for child in sorted(item for item in target.rglob("*") if item.is_file()):
            digest.update(child.relative_to(target).as_posix().encode("utf-8"))
            digest.update(bytes.fromhex(sha256_path(child)))
        return digest.hexdigest()
    raise FileNotFoundError(target)


def load_case_painting_report_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the approved Notebook 32 contract."""

    with Path(path).open("r", encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict) or (
        config.get("config_schema_version") != CONFIG_SCHEMA_VERSION
    ):
        raise ValueError("Unsupported case-and-painting report config schema")

    settings = _settings(config)
    required = {
        "notebook_id", "notebook_stem", "dataset_id", "dataset_version",
        "dataset_scope", "selected_cases_schema_version",
        "case_report_index_schema_version", "painting_report_index_schema_version",
        "traceability_schema_version", "inputs", "output",
        "input_table_contracts", "population", "selection", "reports",
        "mock_traceability", "expected_counts", "evidence_policy",
        "known_limitations",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"Notebook 32 config is missing keys: {missing}")
    if settings["notebook_id"] != "32" or settings["notebook_stem"] != (
        "32_case_and_painting_report_generation"
    ):
        raise ValueError("Notebook 32 identity contract changed")
    schema_expectations = {
        "selected_cases_schema_version": SELECTED_CASES_SCHEMA_VERSION,
        "case_report_index_schema_version": CASE_REPORT_INDEX_SCHEMA_VERSION,
        "painting_report_index_schema_version": PAINTING_REPORT_INDEX_SCHEMA_VERSION,
        "traceability_schema_version": TRACEABILITY_SCHEMA_VERSION,
    }
    for key, expected in schema_expectations.items():
        if settings[key] != expected:
            raise ValueError(f"{key} differs from the helper contract")

    for key, value in settings["inputs"].items():
        if not _relative_path(value):
            raise ValueError(f"inputs.{key} must be repository-relative")
    unknown = sorted(
        set(settings["input_table_contracts"]) - set(settings["inputs"])
    )
    if unknown:
        raise ValueError(f"Table contracts reference unknown inputs: {unknown}")
    for key, contract in settings["input_table_contracts"].items():
        if not str(settings["inputs"][key]).endswith(".csv"):
            raise ValueError(f"Table contract {key} must reference CSV evidence")
        if int(contract.get("rows", -1)) < 1 or not contract.get("required_columns"):
            raise ValueError(f"Table contract {key} lacks rows or columns")

    exact_output = {
        "root": "outputs/32_case_and_painting_report_generation",
        "selected_cases_path": "data/selected_cases.csv",
        "case_report_index_path": "data/case_report_index.csv",
        "painting_report_index_path": "data/painting_report_index.csv",
        "case_reports_dir": "reports/cases",
        "painting_reports_dir": "reports/paintings",
        "collection_index_path": "reports/index.html",
        "selected_case_grids_dir": "figures/selected_case_grids",
        "run_manifest_path": "manifests/run_manifest.json",
        "artifacts_path": "manifests/artifacts.csv",
        "validation_path": "validation/checks.csv",
        "work_dir": "work",
    }
    for key, expected in exact_output.items():
        if settings["output"].get(key) != expected:
            raise ValueError(f"output.{key} must equal {expected!r}")

    expected = settings["expected_counts"]
    population = settings["population"]
    selection = settings["selection"]
    if sum(int(value) for value in population["candidate_count_by_model"].values()) != int(
        population["approved_candidate_count"]
    ):
        raise ValueError("Approved candidate model counts do not sum correctly")
    multiplicities = population["candidate_multiplicity_by_case"]
    if sum(int(value) for value in multiplicities.values()) != int(
        population["evaluated_case_count"]
    ):
        raise ValueError("Case multiplicity counts do not sum to 410")
    if sum(int(value) for value in selection["lane_quotas"].values()) != int(
        selection["selected_case_count"]
    ):
        raise ValueError("Selection lane quotas do not sum to 30")
    if list(selection["lane_quotas"]) != list(selection["lane_order"]):
        raise ValueError("Selection lane order differs from quota order")

    reports = settings["reports"]
    if not reports["approved_mock_structure_locked"]:
        raise ValueError("The approved report mock must remain locked")
    if not reports["self_contained_case_reports"] or not reports[
        "self_contained_painting_reports"
    ]:
        raise ValueError("Case and painting reports must be self-contained")
    if int(reports["required_external_image_dependencies"]) != 0:
        raise ValueError("Narrative report visuals may not be external dependencies")

    trace_counts = {
        kind: sum(len(roles) for roles in sections.values())
        for kind, sections in settings["mock_traceability"].items()
    }
    trace_expectations = {
        "case_report": int(expected["case_traceability_rows"]),
        "painting_report": int(expected["painting_traceability_rows"]),
        "collection_index": int(expected["collection_traceability_rows"]),
    }
    if trace_counts != trace_expectations:
        raise ValueError(
            f"Mock traceability arithmetic changed: {trace_counts} != {trace_expectations}"
        )
    if sum(trace_counts.values()) != int(expected["traceability_rows"]):
        raise ValueError("Total traceability count changed")
    if int(expected["report_count"]) != (
        int(expected["case_report_count"])
        + int(expected["painting_report_count"])
        + int(expected["collection_index_count"])
    ):
        raise ValueError("Report-count arithmetic changed")
    calculated_files = (
        int(expected["case_report_count"])
        + int(expected["painting_report_count"])
        + int(expected["collection_index_count"])
        + int(expected["selected_case_grid_count"])
        + 3  # canonical data tables
        + 3  # run manifest, artifact manifest, validation table
    )
    if calculated_files != int(expected["physical_output_files"]):
        raise ValueError("Physical-output arithmetic changed")
    if settings["evidence_policy"]["creates_new_scientific_evidence"]:
        raise ValueError("Notebook 32 may not create new scientific evidence")
    return config


def resolve_case_painting_report_inputs(
    config: Mapping[str, Any], project_root: str | Path
) -> dict[str, Path]:
    """Resolve every declared input and reject missing or escaping paths."""

    root = Path(project_root).resolve()
    resolved: dict[str, Path] = {}
    for key, relative in _settings(config)["inputs"].items():
        path = (root / str(relative)).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"inputs.{key} escapes project root") from exc
        if not path.exists():
            raise FileNotFoundError(f"Missing declared input {key}: {path}")
        resolved[str(key)] = path
    return resolved


def validate_inventory_contract(
    inventory: pd.DataFrame, *, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Validate declared input presence and CSV metadata in the inventory."""

    settings = _settings(config)
    rows: list[dict[str, Any]] = []
    if "relative_path" not in inventory.columns:
        return pd.DataFrame([
            _validation_row(
                stage="inventory_preflight", severity="blocking",
                check_name="inventory_relative_path_column", observed=False,
                expected=True, passed=False,
                issue="Inventory lacks relative_path",
            )
        ], columns=VALIDATION_COLUMNS)
    lookup = inventory.set_index("relative_path", drop=False)
    for input_key, relative_path in settings["inputs"].items():
        if input_key in {"inventory_path", "inventory_run_path"}:
            # The inventory builder deliberately excludes its own generated files.
            continue
        present = relative_path in lookup.index
        rows.append(_validation_row(
            stage="inventory_preflight", severity="blocking",
            check_name=f"input_present__{input_key}", observed=present,
            expected=True, passed=present,
            issue=f"Declared input is absent from inventory: {relative_path}",
        ))
        if not present or input_key not in settings["input_table_contracts"]:
            continue
        item = lookup.loc[relative_path]
        if isinstance(item, pd.DataFrame):
            item = item.iloc[0]
        expected_rows = int(settings["input_table_contracts"][input_key]["rows"])
        observed_rows = pd.to_numeric(
            pd.Series([item.get("tabular_row_count")]), errors="coerce"
        ).iloc[0]
        matched = pd.notna(observed_rows) and int(observed_rows) == expected_rows
        rows.append(_validation_row(
            stage="inventory_preflight", severity="blocking",
            check_name=f"row_count__{input_key}", observed=observed_rows,
            expected=expected_rows, passed=matched,
            issue=f"Inventory row count changed for {input_key}",
        ))
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)


def validate_loaded_input_table(
    frame: pd.DataFrame, *, input_key: str, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Validate one loaded input table against the configuration contract."""

    contract = _settings(config)["input_table_contracts"][input_key]
    required = list(contract["required_columns"])
    missing = sorted(set(required) - set(frame.columns))
    rows = [
        _validation_row(
            stage="input_loading", severity="blocking",
            check_name=f"rows__{input_key}", observed=len(frame),
            expected=int(contract["rows"]),
            passed=len(frame) == int(contract["rows"]),
            issue=f"Loaded row count changed for {input_key}",
        ),
        _validation_row(
            stage="input_loading", severity="blocking",
            check_name=f"columns__{input_key}", observed=missing,
            expected=[], passed=not missing,
            issue=f"Missing required columns for {input_key}: {missing}",
        ),
    ]
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)


def load_upstream_manifests(inputs: Mapping[str, Path]) -> dict[str, dict[str, Any]]:
    """Load every explicitly declared upstream run manifest."""

    manifests: dict[str, dict[str, Any]] = {}
    for key, path in sorted(inputs.items()):
        match = re.fullmatch(r"manifest_(\d{2})_path", key)
        if not match:
            continue
        with path.open("r", encoding="utf-8-sig") as handle:
            manifests[match.group(1)] = json.load(handle)
    return manifests


def validate_upstream_completion(
    manifests: Mapping[str, Mapping[str, Any]], *, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Require all 24 producer manifests to be completed and validated."""

    expected_count = int(_settings(config)["expected_counts"]["upstream_manifest_count"])
    rows = [_validation_row(
        stage="upstream_preflight", severity="blocking",
        check_name="upstream_manifest_count", observed=len(manifests),
        expected=expected_count, passed=len(manifests) == expected_count,
        issue="Upstream manifest count changed",
    )]
    for notebook_id, manifest in sorted(manifests.items()):
        passed = (
            str(manifest.get("run_status", "")).lower() == "completed"
            and str(manifest.get("validation_status", "")).lower() == "passed"
            and _as_bool(manifest.get("completion_gate_passed"))
        )
        rows.append(_validation_row(
            stage="upstream_preflight", severity="blocking",
            check_name=f"completed__{notebook_id}",
            observed={
                "run_status": manifest.get("run_status"),
                "validation_status": manifest.get("validation_status"),
                "completion_gate_passed": manifest.get("completion_gate_passed"),
            },
            expected={
                "run_status": "completed", "validation_status": "passed",
                "completion_gate_passed": True,
            },
            passed=passed,
            issue=f"Upstream Notebook {notebook_id} is not complete",
        ))
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)


def summarize_case_catalog(catalog: pd.DataFrame) -> pd.DataFrame:
    """Collapse the approved candidate catalog to one auditable row per case."""

    required = {
        "candidate_id", "case_id", "painting_id", "model_id", "experiment_id",
        "prompt_variant_id", "category", "style_or_period",
        "degradation_family", "severity", "recommendation_category",
        "manual_review_required", "triggered_flag_ids_json",
        "metric_disagreement_ids_json", "uncertainty_group_id",
        "report_selected", "evidence_coverage_status", "scope_status", "status",
    }
    missing = sorted(required - set(catalog.columns))
    if missing:
        raise ValueError(f"Explanation catalog is missing columns: {missing}")
    if catalog["candidate_id"].duplicated().any():
        raise ValueError("Explanation catalog candidate_id values are not unique")

    records: list[dict[str, Any]] = []
    for case_id, group in catalog.groupby("case_id", sort=True):
        def unique_text(column: str) -> list[str]:
            return sorted({
                str(value) for value in group[column]
                if str(value).strip() and str(value).strip().lower() != "nan"
            })

        model_ids = unique_text("model_id")
        candidate_ids = unique_text("candidate_id")
        prompt_ids = unique_text("prompt_variant_id")
        uncertainty_ids = unique_text("uncertainty_group_id")
        flags = sorted({
            str(item)
            for value in group["triggered_flag_ids_json"]
            for item in _json_array(value)
            if str(item).strip()
        })
        disagreements = sorted({
            str(item)
            for value in group["metric_disagreement_ids_json"]
            for item in _json_array(value)
            if str(item).strip()
        })
        recommendations = group["recommendation_category"].astype(str)
        manual = group["manual_review_required"].map(_as_bool)
        approved_coverage_states = {
            "complete_multi_family_candidate_evidence",
            "feature_and_rule_evidence_only",
            "partial_map_or_semantic_evidence",
            "rule_evidence_with_explicit_missing_upstream_families",
        }
        approved_scope_states = {
            "supported_primary_scope",
            "supported_uncertainty_extension",
            "bounded_diagnostic_scope",
        }
        complete = (
            group["status"].astype(str).str.lower().eq("ok").all()
            and group["evidence_coverage_status"].astype(str).str.lower()
            .isin(approved_coverage_states).all()
            and group["scope_status"].astype(str).str.lower()
            .isin(approved_scope_states).all()
        )
        first = group.sort_values("candidate_id").iloc[0]
        records.append({
            "case_id": str(case_id),
            "painting_id": str(first["painting_id"]),
            "category": str(first["category"]),
            "style_or_period": str(first["style_or_period"]),
            "experiment_id": str(first["experiment_id"]),
            "degradation_family": str(first["degradation_family"]),
            "severity": str(first["severity"]),
            "candidate_count": len(candidate_ids),
            "model_count": len(model_ids),
            "model_ids_json": _json_strings(model_ids),
            "candidate_ids_json": _json_strings(candidate_ids),
            "prompt_variant_count": len(prompt_ids),
            "prompt_variant_ids_json": _json_strings(prompt_ids),
            "uncertainty_group_count": len(uncertainty_ids),
            "uncertainty_group_ids_json": _json_strings(uncertainty_ids),
            "lower_risk_candidate_count": int(
                recommendations.eq("suitable_for_preliminary_inspection").sum()
            ),
            "manual_review_candidate_count": int(manual.sum()),
            "triggered_flag_count": len(flags),
            "triggered_flag_ids_json": _json_strings(flags),
            "metric_disagreement_count": len(disagreements),
            "metric_disagreement_ids_json": _json_strings(disagreements),
            "has_sdxl": "sdxl_inpainting" in model_ids,
            "has_uncertainty": bool(uncertainty_ids),
            "has_scratch_prompt_pair": (
                str(first["degradation_family"]) == "scratch_thin"
                and len(prompt_ids) > 1
            ),
            "notebook_29_report_selected": bool(
                group["report_selected"].map(_as_bool).any()
            ),
            "evidence_coverage_complete": bool(complete),
            "schema_version": "case_report_population_summary.v1",
            "status": "ok" if complete else "error",
            "issue": "" if complete else "Incomplete candidate evidence coverage",
        })
    return pd.DataFrame(records, columns=CASE_SUMMARY_COLUMNS)


def validate_case_population(
    case_summary: pd.DataFrame,
    candidate_catalog: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Validate the approved 410-case and 1,785-candidate report population."""

    expected = _settings(config)["expected_counts"]
    population = _settings(config)["population"]
    rows: list[dict[str, Any]] = []
    checks = {
        "candidate_rows": (len(candidate_catalog), int(expected["approved_candidate_count"])),
        "candidate_ids_unique": (
            int(candidate_catalog["candidate_id"].nunique()),
            int(expected["approved_candidate_count"]),
        ),
        "case_rows": (len(case_summary), int(expected["case_count"])),
        "painting_count": (
            int(case_summary["painting_id"].nunique()), int(expected["painting_count"]),
        ),
        "candidate_sum": (
            int(case_summary["candidate_count"].sum()),
            int(expected["approved_candidate_count"]),
        ),
    }
    for name, (observed, wanted) in checks.items():
        rows.append(_validation_row(
            stage="population", severity="blocking", check_name=name,
            observed=observed, expected=wanted, passed=observed == wanted,
            issue=f"Population contract failed: {name}",
        ))
    observed_multiplicity = (
        case_summary["candidate_count"].value_counts().sort_index().astype(int).to_dict()
    )
    wanted_multiplicity = {
        int(key): int(value)
        for key, value in population["candidate_multiplicity_by_case"].items()
    }
    rows.append(_validation_row(
        stage="population", severity="blocking",
        check_name="candidate_multiplicity_by_case",
        observed=observed_multiplicity, expected=wanted_multiplicity,
        passed=observed_multiplicity == wanted_multiplicity,
        issue="Per-case approved candidate multiplicities changed",
    ))
    complete = case_summary["evidence_coverage_complete"].map(_as_bool).all()
    rows.append(_validation_row(
        stage="population", severity="blocking", check_name="coverage_complete",
        observed=bool(complete), expected=True, passed=bool(complete),
        issue="At least one approved case has incomplete evidence coverage",
    ))
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)


def build_uncertainty_case_scores(
    canonical_uncertainty: pd.DataFrame,
    damage_size_uncertainty: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the approved presentation-only uncertainty sort key by case."""

    policy = _settings(config)["selection"]["uncertainty_metric"]
    frames = []
    for source_name, frame in (
        ("notebook_18", canonical_uncertainty),
        ("notebook_22", damage_size_uncertainty),
    ):
        selected = frame.loc[
            frame["observation_level"].astype(str).eq(policy["observation_level"])
            & frame["metric_name"].astype(str).eq(policy["metric_name"])
            & frame["region_id"].astype(str).eq(policy["region_id"])
            & frame["summary_statistic"].astype(str).eq(policy["summary_statistic"])
            & frame["status"].astype(str).str.lower().eq("ok"),
            ["case_id", "uncertainty_group_id", "value"],
        ].copy()
        selected["source"] = source_name
        selected["value"] = pd.to_numeric(selected["value"], errors="coerce")
        frames.append(selected.dropna(subset=["value"]))
    combined = pd.concat(frames, ignore_index=True)
    if combined.empty:
        raise ValueError("Approved uncertainty selection evidence is empty")
    scores = (
        combined.groupby("case_id", as_index=False)
        .agg(
            uncertainty_score=("value", "max"),
            uncertainty_group_count=("uncertainty_group_id", "nunique"),
            uncertainty_sources=("source", lambda values: _json_strings(values)),
        )
        .sort_values(["uncertainty_score", "case_id"], ascending=[False, True])
        .reset_index(drop=True)
    )
    scores["uncertainty_rank"] = range(1, len(scores) + 1)
    return scores


def _all_selection_roles(row: Mapping[str, Any]) -> list[str]:
    roles: list[str] = []
    if int(row.get("lower_risk_candidate_count", 0)) > 0:
        roles.append("lower_risk")
    if int(row.get("manual_review_candidate_count", 0)) > 0:
        roles.append("flagged_or_manual_review")
    if int(row.get("metric_disagreement_count", 0)) > 0:
        roles.append("metric_disagreement")
    if pd.notna(row.get("uncertainty_score")):
        roles.append("uncertainty_available")
    if _as_bool(row.get("has_scratch_prompt_pair")):
        roles.append("scratch_prompt_sensitivity")
    if str(row.get("experiment_id")) in {
        "damage_size_sensitivity", "mask_robustness", "synthetic_degradation"
    }:
        roles.append("extension_experiment")
    if _as_bool(row.get("has_sdxl")):
        roles.append("sdxl_partial_evaluation")
    if str(row.get("degradation_family")) == "zero_control":
        roles.append("zero_control")
    return roles


def select_report_cases(
    case_summary: pd.DataFrame,
    uncertainty_scores: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select exactly 30 unique cases using the approved quota-first policy."""

    settings = _settings(config)
    selection = settings["selection"]
    frame = case_summary.copy().merge(
        uncertainty_scores[["case_id", "uncertainty_score"]],
        on="case_id", how="left",
    )
    frame["uncertainty_score"] = pd.to_numeric(
        frame["uncertainty_score"], errors="coerce"
    )
    frame["report_selected_sort"] = frame["notebook_29_report_selected"].map(
        _as_bool
    ).astype(int)
    selected_ids: set[str] = set()
    records: list[dict[str, Any]] = []

    def add_rows(lane: str, candidates: pd.DataFrame, count: int, reason: str) -> None:
        available = candidates.loc[
            ~candidates["case_id"].astype(str).isin(selected_ids)
        ].head(count)
        if len(available) != count:
            raise ValueError(
                f"Selection lane {lane} required {count}, found {len(available)}"
            )
        for _, row in available.iterrows():
            case_id = str(row["case_id"])
            selected_ids.add(case_id)
            roles = _all_selection_roles(row)
            record = {
                "selection_id": _stable_id("selection", lane, case_id),
                "selection_order": len(records) + 1,
                "selection_lane": lane,
                "selection_reason": reason,
                "selection_reasons_json": _json_strings(roles),
                "case_id": case_id,
                "painting_id": str(row["painting_id"]),
                "category": str(row["category"]),
                "style_or_period": str(row["style_or_period"]),
                "experiment_id": str(row["experiment_id"]),
                "degradation_family": str(row["degradation_family"]),
                "severity": str(row["severity"]),
                "candidate_count": int(row["candidate_count"]),
                "model_count": int(row["model_count"]),
                "model_ids_json": str(row["model_ids_json"]),
                "candidate_ids_json": str(row["candidate_ids_json"]),
                "prompt_variant_count": int(row["prompt_variant_count"]),
                "uncertainty_group_count": int(row["uncertainty_group_count"]),
                "uncertainty_score": row["uncertainty_score"],
                "lower_risk_candidate_count": int(row["lower_risk_candidate_count"]),
                "manual_review_candidate_count": int(row["manual_review_candidate_count"]),
                "triggered_flag_count": int(row["triggered_flag_count"]),
                "metric_disagreement_count": int(row["metric_disagreement_count"]),
                "has_sdxl": _as_bool(row["has_sdxl"]),
                "has_uncertainty": _as_bool(row["has_uncertainty"]),
                "has_scratch_prompt_pair": _as_bool(row["has_scratch_prompt_pair"]),
                "notebook_29_report_selected": _as_bool(
                    row["notebook_29_report_selected"]
                ),
                "schema_version": SELECTED_CASES_SCHEMA_VERSION,
                "status": "ok",
                "issue": "",
            }
            records.append(record)

    lower_sort = [
        "lower_risk_candidate_count", "manual_review_candidate_count",
        "triggered_flag_count", "report_selected_sort", "case_id",
    ]
    lower_ascending = [False, True, True, False, True]
    for category in selection["category_order"]:
        candidates = frame.loc[
            frame["category"].astype(str).eq(category)
            & frame["lower_risk_candidate_count"].gt(0)
        ].sort_values(lower_sort, ascending=lower_ascending)
        add_rows(
            "category_lower_risk", candidates, 1,
            f"Lower-risk representative for category {category}",
        )

    flagged_sort = [
        "manual_review_candidate_count", "triggered_flag_count",
        "metric_disagreement_count", "report_selected_sort", "case_id",
    ]
    for category in selection["category_order"]:
        candidates = frame.loc[
            frame["category"].astype(str).eq(category)
            & frame["manual_review_candidate_count"].gt(0)
        ].sort_values(flagged_sort, ascending=[False, False, False, False, True])
        add_rows(
            "category_flagged", candidates, 1,
            f"Flagged representative for category {category}",
        )

    quota = selection["lane_quotas"]
    disagreement = frame.loc[frame["metric_disagreement_count"].gt(0)].sort_values(
        ["metric_disagreement_count", "triggered_flag_count", "report_selected_sort", "case_id"],
        ascending=[False, False, False, True],
    )
    add_rows(
        "metric_disagreement", disagreement, int(quota["metric_disagreement"]),
        "High canonical metric-family disagreement",
    )

    uncertainty = frame.loc[frame["uncertainty_score"].notna()].sort_values(
        ["uncertainty_score", "report_selected_sort", "case_id"],
        ascending=[False, False, True],
    )
    add_rows(
        "high_uncertainty", uncertainty, int(quota["high_uncertainty"]),
        "Highest approved masked-region diffusion variability",
    )

    scratch = frame.loc[frame["has_scratch_prompt_pair"].map(_as_bool)].sort_values(
        ["uncertainty_score", "report_selected_sort", "triggered_flag_count", "case_id"],
        ascending=[False, False, False, True], na_position="last",
    )
    add_rows(
        "scratch_prompt_sensitivity", scratch,
        int(quota["scratch_prompt_sensitivity"]),
        "Paired generic and scratch-aware prompt evidence",
    )

    for experiment_id in selection["extension_experiment_order"]:
        candidates = frame.loc[
            frame["experiment_id"].astype(str).eq(experiment_id)
        ].sort_values(
            ["report_selected_sort", "triggered_flag_count", "uncertainty_score", "case_id"],
            ascending=[False, False, False, True], na_position="last",
        )
        add_rows(
            "extension_representative", candidates, 1,
            f"Representative for extension experiment {experiment_id}",
        )

    sdxl = frame.loc[frame["has_sdxl"].map(_as_bool)].sort_values(
        ["triggered_flag_count", "report_selected_sort", "case_id"],
        ascending=[False, False, True],
    )
    add_rows(
        "sdxl_partial_evaluation", sdxl, int(quota["sdxl_partial_evaluation"]),
        "SDXL partial-evaluation representative",
    )

    zero = frame.loc[
        frame["degradation_family"].astype(str).eq("zero_control")
    ].sort_values(
        ["triggered_flag_count", "manual_review_candidate_count", "case_id"],
        ascending=[True, True, True],
    )
    add_rows(
        "zero_control", zero, int(quota["zero_control"]),
        "Zero-control diagnostic representative",
    )

    selected = pd.DataFrame(records, columns=SELECTED_CASE_COLUMNS)
    if len(selected) != int(selection["selected_case_count"]):
        raise ValueError("Selected-case count differs from the approved contract")
    return selected


def validate_selected_cases(
    selected: pd.DataFrame, *, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Validate selection uniqueness, quotas, and required category coverage."""

    selection = _settings(config)["selection"]
    rows: list[dict[str, Any]] = []
    expected_count = int(selection["selected_case_count"])
    checks = {
        "selected_rows": (len(selected), expected_count),
        "unique_case_ids": (int(selected["case_id"].nunique()), expected_count),
        "selection_order_unique": (
            int(selected["selection_order"].nunique()), expected_count,
        ),
    }
    for name, (observed, expected) in checks.items():
        rows.append(_validation_row(
            stage="selection", severity="blocking", check_name=name,
            observed=observed, expected=expected, passed=observed == expected,
            issue=f"Selected-case contract failed: {name}",
        ))
    observed_lanes = selected["selection_lane"].value_counts().to_dict()
    expected_lanes = {
        key: int(value) for key, value in selection["lane_quotas"].items()
    }
    rows.append(_validation_row(
        stage="selection", severity="blocking", check_name="lane_quotas",
        observed=observed_lanes, expected=expected_lanes,
        passed=observed_lanes == expected_lanes,
        issue="Selection lane quotas changed",
    ))
    for lane in ("category_lower_risk", "category_flagged"):
        categories = sorted(
            selected.loc[selected["selection_lane"].eq(lane), "category"].unique()
        )
        expected_categories = sorted(selection["category_order"])
        rows.append(_validation_row(
            stage="selection", severity="blocking",
            check_name=f"category_coverage__{lane}", observed=categories,
            expected=expected_categories, passed=categories == expected_categories,
            issue=f"Category coverage changed for {lane}",
        ))
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)


def build_painting_summary(
    case_summary: pd.DataFrame,
    artworks: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build one descriptive coverage row for each of the 50 paintings."""

    artwork_lookup = artworks.drop_duplicates("painting_id").set_index("painting_id")
    extension_ids = set(
        _settings(config)["population"]["cases_per_painting"]["extension_painting_ids"]
    )
    records: list[dict[str, Any]] = []
    for painting_id, group in case_summary.groupby("painting_id", sort=True):
        if painting_id not in artwork_lookup.index:
            raise ValueError(f"Missing artwork metadata for {painting_id}")
        artwork = artwork_lookup.loc[painting_id]
        model_ids = sorted({
            item
            for value in group["model_ids_json"]
            for item in _json_array(value)
        })
        experiments = sorted(group["experiment_id"].astype(str).unique())
        degradations = sorted(group["degradation_family"].astype(str).unique())
        records.append({
            "painting_id": str(painting_id),
            "title": str(artwork.get("title", "")),
            "artist": str(artwork.get("artist", "")),
            "style_or_period": str(artwork.get("style_or_period", "")),
            "category": str(artwork.get("category", "")),
            "metadata_completeness_pct": artwork.get("metadata_completeness_pct", ""),
            "case_count": int(group["case_id"].nunique()),
            "candidate_count": int(group["candidate_count"].sum()),
            "model_count": len(model_ids),
            "model_ids_json": _json_strings(model_ids),
            "experiment_count": len(experiments),
            "experiment_ids_json": _json_strings(experiments),
            "degradation_count": len(degradations),
            "degradation_families_json": _json_strings(degradations),
            "manual_review_case_count": int(
                group["manual_review_candidate_count"].gt(0).sum()
            ),
            "flagged_case_count": int(group["triggered_flag_count"].gt(0).sum()),
            "uncertainty_case_count": int(group["has_uncertainty"].map(_as_bool).sum()),
            "sdxl_case_count": int(group["has_sdxl"].map(_as_bool).sum()),
            "is_extension_painting": str(painting_id) in extension_ids,
            "schema_version": "painting_report_population_summary.v1",
            "status": "ok",
            "issue": "",
        })
    return pd.DataFrame(records, columns=PAINTING_SUMMARY_COLUMNS)


def validate_painting_summary(
    painting_summary: pd.DataFrame, *, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Validate complete 50-painting and 410-case coverage."""

    settings = _settings(config)
    expected = settings["expected_counts"]
    coverage = settings["population"]["cases_per_painting"]
    observed_case_distribution = (
        painting_summary["case_count"].value_counts().sort_index().astype(int).to_dict()
    )
    expected_distribution = {
        int(coverage["standard_case_count"]): int(coverage["standard_painting_count"]),
        int(coverage["extension_case_count"]): len(coverage["extension_painting_ids"]),
    }
    rows = [
        _validation_row(
            stage="painting_population", severity="blocking",
            check_name="painting_rows", observed=len(painting_summary),
            expected=int(expected["painting_count"]),
            passed=len(painting_summary) == int(expected["painting_count"]),
            issue="Painting report population changed",
        ),
        _validation_row(
            stage="painting_population", severity="blocking",
            check_name="case_sum", observed=int(painting_summary["case_count"].sum()),
            expected=int(expected["case_count"]),
            passed=int(painting_summary["case_count"].sum()) == int(expected["case_count"]),
            issue="Painting-level cases do not sum to 410",
        ),
        _validation_row(
            stage="painting_population", severity="blocking",
            check_name="case_distribution", observed=observed_case_distribution,
            expected=expected_distribution,
            passed=observed_case_distribution == expected_distribution,
            issue="Standard or extension painting case coverage changed",
        ),
    ]
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)


def image_to_data_uri(
    path: str | Path,
    *,
    max_dimension: int = 900,
    quality: int = 82,
    image_format: str = "JPEG",
) -> str:
    """Return a resized browser-safe data URI without persisting a thumbnail."""

    with Image.open(path) as source:
        image = source.convert("RGB")
        image.thumbnail((int(max_dimension), int(max_dimension)), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format=image_format, quality=int(quality), optimize=True)
    mime = "image/jpeg" if image_format.upper() == "JPEG" else "image/png"
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def visual_html(
    data_uri: str,
    *,
    alt: str,
    caption: str,
    report_role: str,
    tile_count: int = 1,
) -> str:
    """Render one auditable embedded visual block."""

    if not data_uri.startswith("data:image/"):
        raise ValueError("Narrative visuals must be embedded image data URIs")
    if not str(alt).strip() or not str(caption).strip():
        raise ValueError("Narrative visuals require alt text and captions")
    return (
        f'<figure class="report-visual" data-report-role="{html.escape(report_role)}" '
        f'data-tile-count="{int(tile_count)}">'
        f'<img src="{data_uri}" alt="{html.escape(alt)}">'
        f'<figcaption>{html.escape(caption)}</figcaption></figure>'
    )


def render_report_html(
    *,
    title: str,
    subtitle: str,
    report_kind: str,
    sections: Mapping[str, str],
    config: Mapping[str, Any],
) -> str:
    """Render a case, painting, or collection report in approved section order."""

    reports = _settings(config)["reports"]
    section_key = {
        "case": "case_sections",
        "painting": "painting_sections",
        "collection": "collection_sections",
    }.get(report_kind)
    if section_key is None:
        raise ValueError(f"Unsupported report kind: {report_kind}")
    ordered = list(reports[section_key])
    missing = [section for section in ordered if section not in sections]
    extra = sorted(set(sections) - set(ordered))
    if missing or extra:
        raise ValueError(f"Report sections differ; missing={missing}, extra={extra}")
    section_html = "\n".join(
        f'<section id="{section_id}" data-section-id="{section_id}">'
        f'<h2>{html.escape(section_id.replace("-", " ").title())}</h2>'
        f'{sections[section_id]}</section>'
        for section_id in ordered
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root{{--ink:#172026;--muted:#56636b;--paper:#fff;--panel:#f3f6f5;--accent:#275b57;--line:#ccd6d3;}}
*{{box-sizing:border-box}} body{{margin:0;background:#e9efed;color:var(--ink);font-family:Arial,sans-serif;line-height:1.55}}
main{{max-width:1180px;margin:auto;background:var(--paper);padding:36px 44px 64px;box-shadow:0 0 24px #0002}}
h1{{margin:0;color:var(--accent);font-size:2rem}} .subtitle{{color:var(--muted);margin:.35rem 0 2rem}}
h2{{margin-top:2.2rem;border-bottom:2px solid var(--line);padding-bottom:.35rem;color:var(--accent)}}
h3{{color:#314b48}} table{{width:100%;border-collapse:collapse;margin:1rem 0 1.5rem;font-size:.92rem}}
th,td{{border:1px solid var(--line);padding:.55rem;text-align:left;vertical-align:top}} th{{background:var(--panel)}}
.report-visual{{margin:1.4rem 0;padding:1rem;background:var(--panel);border:1px solid var(--line);border-radius:8px}}
.report-visual img{{display:block;max-width:100%;height:auto;margin:auto}} figcaption{{margin-top:.65rem;color:var(--muted);font-size:.9rem}}
.conclusion{{border-left:5px solid var(--accent);background:#edf5f3;padding:.8rem 1rem;margin:1rem 0}}
.limitation{{border-left:5px solid #9b6a2f;background:#fff7e8;padding:.8rem 1rem;margin:1rem 0}}
code{{overflow-wrap:anywhere}} @media(max-width:720px){{main{{padding:22px 16px}} table{{display:block;overflow-x:auto}}}}
</style>
</head>
<body><main data-report-kind="{html.escape(report_kind)}">
<header><h1>{html.escape(title)}</h1><p class="subtitle">{html.escape(subtitle)}</p></header>
{section_html}
</main></body></html>"""


def validate_report_html(
    report_html: str,
    *,
    report_kind: str,
    config: Mapping[str, Any],
    is_extension_painting: bool = False,
) -> pd.DataFrame:
    """Validate structure, embedded visuals, wording, and portability."""

    reports = _settings(config)["reports"]
    section_key = {
        "case": "case_sections", "painting": "painting_sections",
        "collection": "collection_sections",
    }[report_kind]
    sections = re.findall(r'data-section-id="([^"]+)"', report_html)
    images = re.findall(r'<img\b[^>]*\bsrc="([^"]+)"[^>]*>', report_html)
    alts = re.findall(r'<img\b[^>]*\balt="([^"]*)"[^>]*>', report_html)
    tile_counts = [int(value) for value in re.findall(r'data-tile-count="(\d+)"', report_html)]
    external = [source for source in images if not source.startswith("data:image/")]
    if report_kind == "case":
        minimum_images = int(reports["minimum_visuals"]["case_report_images"])
        minimum_tiles = int(reports["minimum_visuals"]["case_report_tiles"])
    elif report_kind == "painting":
        prefix = "extension" if is_extension_painting else "standard"
        minimum_images = int(reports["minimum_visuals"][f"{prefix}_painting_report_images"])
        minimum_tiles = int(reports["minimum_visuals"][f"{prefix}_painting_report_tiles"])
    else:
        minimum_images = int(reports["minimum_visuals"]["collection_index_images"])
        minimum_tiles = minimum_images
    checks = [
        ("section_order", sections, list(reports[section_key])),
        ("minimum_embedded_images", len(images), minimum_images),
        ("minimum_embedded_tiles", sum(tile_counts), minimum_tiles),
        ("external_image_dependencies", len(external), 0),
        ("empty_alt_text", sum(not value.strip() for value in alts), 0),
    ]
    rows: list[dict[str, Any]] = []
    for name, observed, expected in checks:
        if name in {"minimum_embedded_images", "minimum_embedded_tiles"}:
            passed = int(observed) >= int(expected)
        else:
            passed = observed == expected
        rows.append(_validation_row(
            stage="rendered_report", severity="blocking", check_name=name,
            observed=observed, expected=expected, passed=passed,
            issue=f"Rendered {report_kind} report failed {name}",
        ))
    lowered = report_html.lower()
    if report_kind in {"case", "painting"}:
        mandatory = reports["mandatory_statement"]
        rows.append(_validation_row(
            stage="rendered_report", severity="blocking",
            check_name="mandatory_trustworthiness_statement",
            observed=mandatory in report_html, expected=True,
            passed=mandatory in report_html,
            issue="Mandatory trustworthiness statement is absent",
        ))
        for term in reports["required_terms"]:
            present = str(term).lower() in lowered
            rows.append(_validation_row(
                stage="rendered_report", severity="blocking",
                check_name=f"required_term__{term}", observed=present,
                expected=True, passed=present,
                issue=f"Required report language is absent: {term}",
            ))
    for term in reports["prohibited_terms"]:
        absent = str(term).lower() not in lowered
        rows.append(_validation_row(
            stage="rendered_report", severity="blocking",
            check_name=f"prohibited_term_absent__{term}", observed=absent,
            expected=True, passed=absent,
            issue=f"Prohibited planning or overclaiming language remains: {term}",
        ))
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)


def build_mock_traceability(
    evidence_sources: Mapping[str, Mapping[str, str]],
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the binding approved mock-to-final traceability table."""

    settings = _settings(config)
    records: list[dict[str, Any]] = []
    for report_kind, sections in settings["mock_traceability"].items():
        kind_sources = evidence_sources.get(report_kind, {})
        for section, roles in sections.items():
            source = str(kind_sources.get(section, "")).strip()
            for role in roles:
                records.append({
                    "mock_element_id": _stable_id(
                        "mock", report_kind, section, role
                    ),
                    "report_kind": report_kind,
                    "mock_section": section,
                    "approved_role": role,
                    "final_section": section,
                    "canonical_evidence_source": source,
                    "implementation_status": "preserved" if source else "",
                    "deviation_reason": "",
                    "schema_version": TRACEABILITY_SCHEMA_VERSION,
                    "status": "ok" if source else "error",
                    "issue": "" if source else "Missing canonical evidence source",
                })
    return pd.DataFrame(records, columns=TRACEABILITY_COLUMNS)


def validate_mock_traceability(
    traceability: pd.DataFrame, *, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Require every approved mock role and exact section identity."""

    expected = int(_settings(config)["expected_counts"]["traceability_rows"])
    valid_status = traceability["implementation_status"].isin({
        "preserved", "upgraded_additively", "approved_deviation"
    })
    section_match = traceability["mock_section"].eq(traceability["final_section"])
    source_present = traceability["canonical_evidence_source"].astype(str).str.strip().ne("")
    rows = [
        _validation_row(
            stage="mock_traceability", severity="blocking",
            check_name="traceability_rows", observed=len(traceability),
            expected=expected, passed=len(traceability) == expected,
            issue="Mock traceability row count changed",
        ),
        _validation_row(
            stage="mock_traceability", severity="blocking",
            check_name="valid_implementation_status",
            observed=int(valid_status.sum()), expected=len(traceability),
            passed=bool(valid_status.all()),
            issue="Traceability contains an invalid implementation status",
        ),
        _validation_row(
            stage="mock_traceability", severity="blocking",
            check_name="section_identity_preserved",
            observed=int(section_match.sum()), expected=len(traceability),
            passed=bool(section_match.all()),
            issue="An approved mock section was moved without approval",
        ),
        _validation_row(
            stage="mock_traceability", severity="blocking",
            check_name="canonical_sources_present",
            observed=int(source_present.sum()), expected=len(traceability),
            passed=bool(source_present.all()),
            issue="Traceability lacks a canonical evidence source",
        ),
    ]
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)


def atomic_write_text(
    text: str,
    path: str | Path,
    *,
    maximum_attempts: int = 6,
) -> Path:
    """Atomically write text and retry short Windows replacement locks."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    for attempt in range(1, maximum_attempts + 1):
        try:
            temporary.write_text(text, encoding="utf-8", newline="\n")
            os.replace(temporary, target)
            return target
        except PermissionError:
            temporary.unlink(missing_ok=True)
            if attempt >= maximum_attempts:
                raise
            time.sleep(0.35 * attempt)
    raise RuntimeError("Atomic text writer ended unexpectedly")


def atomic_write_csv(
    frame: pd.DataFrame,
    path: str | Path,
    *,
    maximum_attempts: int = 6,
) -> Path:
    """Atomically write CSV and retry short Windows replacement locks."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    for attempt in range(1, maximum_attempts + 1):
        try:
            frame.to_csv(temporary, index=False)
            os.replace(temporary, target)
            return target
        except PermissionError:
            temporary.unlink(missing_ok=True)
            if attempt >= maximum_attempts:
                raise
            time.sleep(0.35 * attempt)
    raise RuntimeError("Atomic CSV writer ended unexpectedly")


def build_case_report_index_row(
    report_path: str | Path,
    *,
    project_root: str | Path,
    selection_row: Mapping[str, Any],
    source_artifact_paths: Sequence[str],
    upstream_run_ids: Mapping[str, str],
    generated_at_utc: str,
) -> dict[str, Any]:
    """Build one normalized case-report index record from persisted HTML."""

    root = Path(project_root).resolve()
    path = Path(report_path).resolve()
    text = path.read_text(encoding="utf-8")
    return {
        "report_id": _stable_id("case_report", selection_row["case_id"]),
        "case_id": str(selection_row["case_id"]),
        "painting_id": str(selection_row["painting_id"]),
        "selection_order": int(selection_row["selection_order"]),
        "selection_lane": str(selection_row["selection_lane"]),
        "selection_reasons_json": str(selection_row["selection_reasons_json"]),
        "candidate_count": int(selection_row["candidate_count"]),
        "model_count": int(selection_row["model_count"]),
        "report_path": path.relative_to(root).as_posix(),
        "report_sha256": sha256_path(path),
        "size_bytes": path.stat().st_size,
        "section_count": len(re.findall(r'data-section-id="', text)),
        "embedded_image_count": len(re.findall(r'<img\b', text)),
        "embedded_tile_count": sum(
            int(value) for value in re.findall(r'data-tile-count="(\d+)"', text)
        ),
        "self_contained": not bool(re.search(r'<img\b[^>]*src="(?!data:image/)', text)),
        "source_artifact_paths_json": _json_strings(source_artifact_paths),
        "upstream_run_ids_json": json.dumps(dict(upstream_run_ids), sort_keys=True),
        "generated_at_utc": generated_at_utc,
        "schema_version": CASE_REPORT_INDEX_SCHEMA_VERSION,
        "status": "ok",
        "issue": "",
    }


def build_painting_report_index_row(
    report_path: str | Path,
    *,
    project_root: str | Path,
    painting_row: Mapping[str, Any],
    source_artifact_paths: Sequence[str],
    upstream_run_ids: Mapping[str, str],
    generated_at_utc: str,
) -> dict[str, Any]:
    """Build one normalized painting-report index record from persisted HTML."""

    root = Path(project_root).resolve()
    path = Path(report_path).resolve()
    text = path.read_text(encoding="utf-8")
    return {
        "report_id": _stable_id("painting_report", painting_row["painting_id"]),
        "painting_id": str(painting_row["painting_id"]),
        "category": str(painting_row["category"]),
        "style_or_period": str(painting_row["style_or_period"]),
        "case_count": int(painting_row["case_count"]),
        "candidate_count": int(painting_row["candidate_count"]),
        "model_count": int(painting_row["model_count"]),
        "is_extension_painting": _as_bool(painting_row["is_extension_painting"]),
        "report_path": path.relative_to(root).as_posix(),
        "report_sha256": sha256_path(path),
        "size_bytes": path.stat().st_size,
        "section_count": len(re.findall(r'data-section-id="', text)),
        "embedded_image_count": len(re.findall(r'<img\b', text)),
        "embedded_tile_count": sum(
            int(value) for value in re.findall(r'data-tile-count="(\d+)"', text)
        ),
        "self_contained": not bool(re.search(r'<img\b[^>]*src="(?!data:image/)', text)),
        "source_artifact_paths_json": _json_strings(source_artifact_paths),
        "upstream_run_ids_json": json.dumps(dict(upstream_run_ids), sort_keys=True),
        "generated_at_utc": generated_at_utc,
        "schema_version": PAINTING_REPORT_INDEX_SCHEMA_VERSION,
        "status": "ok",
        "issue": "",
    }


def validate_report_indexes(
    case_index: pd.DataFrame,
    painting_index: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Validate normalized report indexes and portability metadata."""

    expected = _settings(config)["expected_counts"]
    rows: list[dict[str, Any]] = []
    specifications = (
        (
            "case", case_index, CASE_REPORT_INDEX_COLUMNS,
            int(expected["case_report_index_rows"]), "case_id",
            CASE_REPORT_INDEX_SCHEMA_VERSION,
        ),
        (
            "painting", painting_index, PAINTING_REPORT_INDEX_COLUMNS,
            int(expected["painting_report_index_rows"]), "painting_id",
            PAINTING_REPORT_INDEX_SCHEMA_VERSION,
        ),
    )
    for name, frame, columns, count, identity, schema in specifications:
        checks = {
            f"{name}_columns": (list(frame.columns), list(columns)),
            f"{name}_rows": (len(frame), count),
            f"{name}_identity_unique": (int(frame[identity].nunique()), count),
            f"{name}_self_contained": (
                int(frame["self_contained"].map(_as_bool).sum()), count
            ),
            f"{name}_schema": (
                sorted(frame["schema_version"].astype(str).unique()), [schema]
            ),
        }
        for check_name, (observed, wanted) in checks.items():
            rows.append(_validation_row(
                stage="report_index", severity="blocking", check_name=check_name,
                observed=observed, expected=wanted, passed=observed == wanted,
                issue=f"Report index failed: {check_name}",
            ))
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)
