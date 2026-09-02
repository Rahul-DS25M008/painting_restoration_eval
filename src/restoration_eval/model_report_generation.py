"""Presentation-only model-report utilities for Notebook 31.

The module consumes validated Notebook 09--30 artifacts and creates no new
scientific evidence.  It locks the approved mock structure, model-specific
applicability, deterministic representative selection, self-contained HTML
requirements, and normalized report-index contract.
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
from typing import Any, Mapping, Sequence

import pandas as pd
import yaml
from PIL import Image


MODULE_NAME = "restoration_eval.model_report_generation"
MODULE_VERSION = "1.0.0"
CONFIG_SCHEMA_VERSION = "model_report_generation_config.v1"
REPORT_INDEX_SCHEMA_VERSION = "model_report_index.v1"
SELECTION_SCHEMA_VERSION = "model_report_selection.v1"
TRACEABILITY_SCHEMA_VERSION = "mock_to_final_traceability.v1"

REPORT_INDEX_COLUMNS = (
    "report_id", "model_id", "display_name", "evaluation_status",
    "report_path", "report_sha256", "size_bytes", "section_count",
    "embedded_image_count", "embedded_tile_count", "analytical_view_count",
    "representative_panel_count", "visual_atlas_count",
    "representative_candidate_ids_json", "source_artifact_paths_json",
    "source_checksums_json", "upstream_run_ids_json",
    "mock_traceability_status", "self_contained", "generated_at_utc",
    "schema_version", "status", "issue",
)

SELECTION_COLUMNS = (
    "selection_id", "selection_order", "model_id", "candidate_id", "case_id",
    "painting_id", "experiment_id", "prompt_variant_id",
    "recommendation_category", "report_selection_roles_json", "clean_path",
    "damaged_path", "restored_path", "mask_path", "diagnostic_paths_json",
    "selection_reason", "schema_version", "status", "issue",
)

TRACEABILITY_COLUMNS = (
    "mock_element_id", "mock_section", "approved_role", "final_section",
    "canonical_evidence_source", "implementation_status", "deviation_reason",
    "schema_version", "status", "issue",
)

APPLICABILITY_COLUMNS = (
    "model_id", "display_name", "evaluation_status", "evidence_component",
    "applicability_status", "schema_version", "status", "issue",
)

VALIDATION_COLUMNS = (
    "check_id", "stage", "severity", "check_name", "observed", "expected",
    "passed", "issue",
)


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    return config.get("model_report_generation", config)


def _relative_path(value: Any) -> bool:
    text = str(value).strip()
    return bool(text) and not Path(text).is_absolute() and "\\" not in text


def _stable_id(prefix: str, *parts: Any) -> str:
    material = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or (not isinstance(value, (list, tuple, dict)) and pd.isna(value)):
        return False
    return str(value).strip().lower() in {"true", "1", "1.0", "yes", "y"}


def _json_array(value: Any) -> list[Any]:
    if value is None or (not isinstance(value, (list, tuple, dict)) and pd.isna(value)):
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


def load_model_report_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the approved Notebook 31 contract."""

    with Path(path).open("r", encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict) or config.get("config_schema_version") != CONFIG_SCHEMA_VERSION:
        raise ValueError("Unsupported model-report configuration schema")
    settings = _settings(config)
    required = {
        "notebook_id", "notebook_stem", "dataset_id", "dataset_version",
        "dataset_scope", "report_index_schema_version", "selection_schema_version",
        "traceability_schema_version", "inputs", "output", "input_table_contracts",
        "models", "report",
        "expected_counts", "evidence_policy", "known_limitations",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"Model-report config is missing keys: {missing}")
    if settings["notebook_id"] != "31" or settings["notebook_stem"] != "31_model_report_generation":
        raise ValueError("Notebook 31 identity contract changed")
    if settings["report_index_schema_version"] != REPORT_INDEX_SCHEMA_VERSION:
        raise ValueError("Report-index schema differs from helper")
    if settings["selection_schema_version"] != SELECTION_SCHEMA_VERSION:
        raise ValueError("Selection schema differs from helper")
    if settings["traceability_schema_version"] != TRACEABILITY_SCHEMA_VERSION:
        raise ValueError("Traceability schema differs from helper")
    for key, value in settings["inputs"].items():
        if not _relative_path(value):
            raise ValueError(f"inputs.{key} must be repository-relative with forward slashes")
    table_contracts = settings["input_table_contracts"]
    unknown_table_keys = sorted(set(table_contracts) - set(settings["inputs"]))
    if unknown_table_keys:
        raise ValueError(f"Input table contracts reference unknown keys: {unknown_table_keys}")
    for key, contract in table_contracts.items():
        if not str(settings["inputs"][key]).endswith(".csv"):
            raise ValueError(f"Input table contract {key} does not reference CSV evidence")
        if int(contract.get("rows", -1)) < 1 or not contract.get("required_columns"):
            raise ValueError(f"Input table contract {key} lacks rows or required columns")

    exact_output = {
        "root": "outputs/31_model_report_generation",
        "report_index_path": "data/report_index.csv",
        "reports_dir": "reports",
        "run_manifest_path": "manifests/run_manifest.json",
        "artifacts_path": "manifests/artifacts.csv",
        "validation_path": "validation/checks.csv",
        "smoke_dir": "work/smoke",
    }
    for key, expected in exact_output.items():
        if settings["output"].get(key) != expected:
            raise ValueError(f"output.{key} must equal {expected!r}")

    model_ids = [str(item["model_id"]) for item in settings["models"]]
    expected_models = [
        "opencv_telea", "lama", "stable_diffusion_inpainting", "sdxl_inpainting"
    ]
    if model_ids != expected_models or len(set(model_ids)) != 4:
        raise ValueError("The approved model order or identity changed")
    expected_filenames = {
        "opencv_telea": "opencv_telea.html",
        "lama": "lama.html",
        "stable_diffusion_inpainting": "stable_diffusion_inpainting.html",
        "sdxl_inpainting": "sdxl_inpainting.html",
    }
    for model in settings["models"]:
        model_id = str(model["model_id"])
        if model["report_filename"] != expected_filenames[model_id]:
            raise ValueError(f"Report filename changed for {model_id}")
        if sum(int(value) for value in model["selection_quotas"].values()) != int(
            model["representative_panel_count"]
        ):
            raise ValueError(f"Selection-quota arithmetic changed for {model_id}")
        if int(model["minimum_embedded_image_count"]) != (
            int(model["representative_panel_count"])
            + int(model["analytical_view_count"])
            + int(model["visual_atlas_count"])
        ):
            raise ValueError(f"Embedded-image arithmetic changed for {model_id}")

    report = settings["report"]
    sections = list(report["required_section_ids"])
    if len(sections) != 15 or len(set(sections)) != 15:
        raise ValueError("Approved executive summary plus fourteen-section structure changed")
    if list(report["traceability_roles"]) != sections:
        raise ValueError("Traceability section order differs from approved report order")
    traceability_count = sum(len(roles) for roles in report["traceability_roles"].values())
    if traceability_count != int(settings["expected_counts"]["traceability_rows"]):
        raise ValueError("Mock-to-final traceability arithmetic changed")
    if not report["approved_mock_structure_locked"] or not report["self_contained_html"]:
        raise ValueError("Approved mock fidelity and standalone HTML must remain locked")
    if int(report["required_external_image_dependencies"]) != 0:
        raise ValueError("Standalone reports may not require external images")
    if settings["evidence_policy"]["creates_new_scientific_evidence"]:
        raise ValueError("Notebook 31 may not create new scientific evidence")
    expected = settings["expected_counts"]
    if int(expected["upstream_manifest_count"]) != 22:
        raise ValueError("Notebook 09--30 manifest count changed")
    if int(expected["artifact_records"]) != int(expected["report_count"]) + 2:
        raise ValueError("Artifact-count arithmetic changed")
    if int(expected["physical_output_files"]) != int(expected["report_count"]) + 4:
        raise ValueError("Physical-output arithmetic changed")
    return config


def resolve_model_report_inputs(
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


def model_specs(config: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """Return model specifications keyed by canonical model ID."""

    return {
        str(item["model_id"]): item for item in _settings(config)["models"]
    }


def load_upstream_manifests(
    inputs: Mapping[str, Path], *, start: int = 9, end: int = 30
) -> dict[str, dict[str, Any]]:
    """Load the exact consecutive upstream run manifests."""

    manifests: dict[str, dict[str, Any]] = {}
    for number in range(int(start), int(end) + 1):
        key = f"manifest_{number:02d}_path"
        with inputs[key].open("r", encoding="utf-8-sig") as handle:
            manifests[f"{number:02d}"] = json.load(handle)
    return manifests


def validate_upstream_completion(
    manifests: Mapping[str, Mapping[str, Any]], *, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Validate identity, completion gate, and blocking status for N09--30."""

    rows: list[dict[str, Any]] = []
    expected_ids = [f"{number:02d}" for number in range(9, 31)]
    rows.append(_validation_row(
        stage="upstream_preflight", severity="blocking",
        check_name="exact_manifest_id_set", observed=sorted(manifests),
        expected=expected_ids, passed=sorted(manifests) == expected_ids,
        issue="upstream manifest set is not exactly Notebook 09--30",
    ))
    for notebook_id in expected_ids:
        manifest = manifests.get(notebook_id, {})
        summary = manifest.get("validation_summary", {})
        passed = (
            str(manifest.get("notebook_id", "")).zfill(2) == notebook_id
            and manifest.get("run_status") == "completed"
            and manifest.get("completion_gate_passed") is True
            and int(summary.get("blocking_failure_count", 0)) == 0
        )
        rows.append(_validation_row(
            stage="upstream_preflight", severity="blocking",
            check_name=f"manifest_{notebook_id}_completed",
            observed={
                "notebook_id": manifest.get("notebook_id"),
                "run_status": manifest.get("run_status"),
                "completion_gate_passed": manifest.get("completion_gate_passed"),
                "blocking_failure_count": summary.get("blocking_failure_count"),
            },
            expected={
                "notebook_id": notebook_id, "run_status": "completed",
                "completion_gate_passed": True, "blocking_failure_count": 0,
            },
            passed=passed,
            issue=f"Notebook {notebook_id} is not a completed zero-blocking input",
        ))
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)


def validate_inventory_contract(
    inventory: pd.DataFrame, *, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Check exact canonical row counts using the refreshed project inventory."""

    required_columns = {
        "relative_path", "tabular_row_count", "read_error_count", "hash_value"
    }
    missing = sorted(required_columns - set(inventory.columns))
    if missing:
        raise ValueError(f"Inventory is missing columns: {missing}")
    settings = _settings(config)
    expectations = {
        key: int(contract["rows"])
        for key, contract in settings["input_table_contracts"].items()
    }
    rows: list[dict[str, Any]] = []
    normalized_paths = inventory["relative_path"].astype(str).str.replace("\\", "/", regex=False)
    for key, expected_rows in expectations.items():
        relative = str(settings["inputs"][key])
        matches = inventory.loc[normalized_paths.eq(relative)]
        observed_rows = None if len(matches) != 1 else pd.to_numeric(
            matches.iloc[0]["tabular_row_count"], errors="coerce"
        )
        read_errors = None if len(matches) != 1 else pd.to_numeric(
            matches.iloc[0]["read_error_count"], errors="coerce"
        )
        passed = (
            len(matches) == 1 and pd.notna(observed_rows)
            and int(observed_rows) == expected_rows
            and pd.notna(read_errors) and int(read_errors) == 0
            and bool(str(matches.iloc[0]["hash_value"]).strip())
        )
        rows.append(_validation_row(
            stage="inventory_preflight", severity="blocking",
            check_name=f"{key}_inventory_contract",
            observed={"matches": len(matches), "rows": observed_rows, "read_errors": read_errors},
            expected={"matches": 1, "rows": expected_rows, "read_errors": 0},
            passed=passed,
            issue=f"inventory contract failed for {relative}",
        ))
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)


def validate_loaded_input_table(
    frame: pd.DataFrame, *, input_key: str, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Validate one loaded canonical table against its locked row/schema contract."""

    settings = _settings(config)
    if input_key not in settings["input_table_contracts"]:
        raise KeyError(f"No tabular input contract is declared for {input_key}")
    contract = settings["input_table_contracts"][input_key]
    required = [str(value) for value in contract["required_columns"]]
    missing = sorted(set(required) - set(frame.columns))
    rows = [
        _validation_row(
            stage="input_loading", severity="blocking",
            check_name=f"{input_key}_row_count", observed=len(frame),
            expected=int(contract["rows"]), passed=len(frame) == int(contract["rows"]),
            issue=f"{input_key} row count differs from the approved canonical artifact",
        ),
        _validation_row(
            stage="input_loading", severity="blocking",
            check_name=f"{input_key}_required_columns", observed=missing,
            expected=[], passed=not missing,
            issue=f"{input_key} is missing required canonical columns",
        ),
    ]
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)


def build_applicability_matrix(config: Mapping[str, Any]) -> pd.DataFrame:
    """Build the locked four-model evidence-applicability matrix."""

    records: list[dict[str, Any]] = []
    for model in _settings(config)["models"]:
        for component, applicability in model["applicability"].items():
            records.append({
                "model_id": model["model_id"],
                "display_name": model["display_name"],
                "evaluation_status": model["evaluation_status"],
                "evidence_component": component,
                "applicability_status": applicability,
                "schema_version": "model_report_applicability.v1",
                "status": "ok",
                "issue": "",
            })
    return pd.DataFrame(records, columns=APPLICABILITY_COLUMNS)


def validate_applicability_matrix(
    frame: pd.DataFrame, *, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Validate complete model/component coverage and key uncertainty distinctions."""

    expected = build_applicability_matrix(config)
    key = ["model_id", "evidence_component"]
    observed_pairs = set(map(tuple, frame[key].astype(str).to_numpy()))
    expected_pairs = set(map(tuple, expected[key].astype(str).to_numpy()))
    expected_status = {
        "|".join(map(str, pair)): value
        for pair, value in expected.set_index(key)["applicability_status"].to_dict().items()
    }
    observed_status = {
        "|".join(map(str, pair)): value
        for pair, value in frame.set_index(key)["applicability_status"].to_dict().items()
    }
    rows = [
        _validation_row(
            stage="applicability", severity="blocking",
            check_name="exact_model_component_pairs", observed=len(observed_pairs),
            expected=len(expected_pairs), passed=observed_pairs == expected_pairs,
            issue="applicability matrix has missing or extra model/component pairs",
        ),
        _validation_row(
            stage="applicability", severity="blocking",
            check_name="exact_applicability_statuses", observed=observed_status,
            expected=expected_status, passed=observed_status == expected_status,
            issue="one or more applicability labels changed",
        ),
    ]
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)


def _take_diverse(frame: pd.DataFrame, count: int) -> pd.DataFrame:
    """Take deterministic rows while preferring distinct paintings first."""

    if count <= 0 or frame.empty:
        return frame.head(0)
    ordered = frame.sort_values(
        ["_report_selected", "painting_id", "case_id", "candidate_id"],
        ascending=[False, True, True, True], kind="stable",
    )
    first = ordered.drop_duplicates("painting_id", keep="first").head(count)
    if len(first) == count:
        return first
    remainder = ordered.loc[~ordered.index.isin(first.index)].head(count - len(first))
    return pd.concat([first, remainder], ignore_index=False)


def select_representative_cases(
    explanation_cases: pd.DataFrame,
    *,
    model_id: str,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select the approved deterministic success/failure report population."""

    required = {
        "candidate_id", "case_id", "painting_id", "model_id", "experiment_id",
        "prompt_variant_id", "recommendation_category", "report_selected",
        "report_selection_roles_json", "clean_path", "damaged_path",
        "restored_path", "mask_path", "difference_paths_json",
        "uncertainty_paths_json", "seam_paths_json", "colour_paths_json",
        "texture_paths_json", "semantic_paths_json", "mask_boundary_paths_json",
        "scope_status", "status",
    }
    missing = sorted(required - set(explanation_cases.columns))
    if missing:
        raise ValueError(f"Explanation catalog is missing columns: {missing}")
    specs = model_specs(config)
    if model_id not in specs:
        raise ValueError(f"Unknown model_id: {model_id}")
    spec = specs[model_id]
    pool = explanation_cases.loc[
        explanation_cases["model_id"].astype(str).eq(model_id)
        & explanation_cases["status"].astype(str).eq("ok")
        & explanation_cases["scope_status"].astype(str).ne("excluded")
    ].copy()
    pool["_report_selected"] = pool["report_selected"].map(_as_bool)
    if pool["candidate_id"].duplicated().any():
        raise ValueError(f"Explanation catalog contains duplicate candidates for {model_id}")

    selected_parts: list[pd.DataFrame] = []
    used: set[str] = set()
    for category, quota in spec["selection_quotas"].items():
        candidates = pool.loc[
            pool["recommendation_category"].astype(str).eq(str(category))
            & ~pool["candidate_id"].astype(str).isin(used)
        ]
        chosen = _take_diverse(candidates, int(quota))
        if len(chosen) != int(quota):
            raise ValueError(
                f"Representative quota {category!r} for {model_id} requires {quota}, "
                f"but only {len(chosen)} rows are available"
            )
        selected_parts.append(chosen)
        used.update(chosen["candidate_id"].astype(str))
    selected = pd.concat(selected_parts, ignore_index=False).copy()

    if model_id == "stable_diffusion_inpainting":
        arms = set(selected["prompt_variant_id"].astype(str))
        if "p05_scratch_aware" not in arms:
            replacement_pool = pool.loc[
                pool["prompt_variant_id"].astype(str).eq("p05_scratch_aware")
                & ~pool["candidate_id"].astype(str).isin(used)
            ]
            replacement = _take_diverse(replacement_pool, 1)
            if replacement.empty:
                raise ValueError("Stable Diffusion selection lacks a scratch-aware candidate")
            replace_category = str(replacement.iloc[0]["recommendation_category"])
            same_category = selected.loc[
                selected["recommendation_category"].astype(str).eq(replace_category)
            ]
            if same_category.empty:
                raise ValueError("Scratch-aware replacement cannot preserve selection quotas")
            selected = selected.drop(index=same_category.index[-1])
            selected = pd.concat([selected, replacement], ignore_index=False)

    category_order = {name: index for index, name in enumerate(spec["selection_quotas"])}
    selected["_category_order"] = selected["recommendation_category"].map(category_order)
    selected = selected.sort_values(
        ["_category_order", "_report_selected", "painting_id", "case_id", "candidate_id"],
        ascending=[True, False, True, True, True], kind="stable",
    ).reset_index(drop=True)

    records: list[dict[str, Any]] = []
    diagnostic_columns = [
        "difference_paths_json", "uncertainty_paths_json", "seam_paths_json",
        "colour_paths_json", "texture_paths_json", "semantic_paths_json",
        "mask_boundary_paths_json",
    ]
    for index, row in selected.iterrows():
        diagnostics: dict[str, list[Any]] = {}
        for column in diagnostic_columns:
            values = _json_array(row[column])
            if values:
                diagnostics[column.removesuffix("_paths_json")] = values
        records.append({
            "selection_id": _stable_id("selection", model_id, row["candidate_id"]),
            "selection_order": index + 1,
            "model_id": model_id,
            "candidate_id": row["candidate_id"],
            "case_id": row["case_id"],
            "painting_id": row["painting_id"],
            "experiment_id": row["experiment_id"],
            "prompt_variant_id": row["prompt_variant_id"],
            "recommendation_category": row["recommendation_category"],
            "report_selection_roles_json": json.dumps(
                _json_array(row["report_selection_roles_json"]), separators=(",", ":")
            ),
            "clean_path": row["clean_path"],
            "damaged_path": row["damaged_path"],
            "restored_path": row["restored_path"],
            "mask_path": row["mask_path"],
            "diagnostic_paths_json": json.dumps(diagnostics, separators=(",", ":")),
            "selection_reason": (
                f"quota:{row['recommendation_category']};"
                f"upstream_report_selected:{str(bool(row['_report_selected'])).lower()}"
            ),
            "schema_version": SELECTION_SCHEMA_VERSION,
            "status": "ok",
            "issue": "",
        })
    return pd.DataFrame(records, columns=SELECTION_COLUMNS)


def validate_representative_selection(
    frame: pd.DataFrame, *, model_id: str, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Validate count, uniqueness, quotas, prompt arms, and path declarations."""

    spec = model_specs(config)[model_id]
    expected_count = int(spec["representative_panel_count"])
    actual_quotas = frame["recommendation_category"].value_counts().to_dict()
    expected_quotas = {str(key): int(value) for key, value in spec["selection_quotas"].items()}
    core_paths = ["clean_path", "damaged_path", "restored_path", "mask_path"]
    declared_paths = frame[core_paths].fillna("").astype(str).apply(
        lambda column: column.str.strip().ne("")
    ).all(axis=1)
    rows = [
        _validation_row(
            stage="representative_selection", severity="blocking",
            check_name=f"{model_id}_row_count", observed=len(frame),
            expected=expected_count, passed=len(frame) == expected_count,
            issue="representative selection count differs from approved density",
        ),
        _validation_row(
            stage="representative_selection", severity="blocking",
            check_name=f"{model_id}_candidate_uniqueness",
            observed=frame["candidate_id"].nunique(), expected=expected_count,
            passed=frame["candidate_id"].nunique() == expected_count,
            issue="representative candidates are not unique",
        ),
        _validation_row(
            stage="representative_selection", severity="blocking",
            check_name=f"{model_id}_selection_quotas", observed=actual_quotas,
            expected=expected_quotas, passed=actual_quotas == expected_quotas,
            issue="representative recommendation-category quotas changed",
        ),
        _validation_row(
            stage="representative_selection", severity="blocking",
            check_name=f"{model_id}_declared_core_paths",
            observed=int(declared_paths.sum()),
            expected=expected_count,
            passed=bool(declared_paths.all()),
            issue="one or more selected rows lacks a declared core visual path",
        ),
    ]
    if model_id == "stable_diffusion_inpainting":
        arms = set(frame["prompt_variant_id"].astype(str))
        passed = {"p00_generic", "p05_scratch_aware"}.issubset(arms)
        rows.append(_validation_row(
            stage="representative_selection", severity="blocking",
            check_name="stable_diffusion_prompt_arm_coverage", observed=sorted(arms),
            expected=["p00_generic", "p05_scratch_aware"], passed=passed,
            issue="Stable Diffusion report selection lacks one approved prompt arm",
        ))
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)


def build_mock_traceability(
    canonical_sources: Mapping[str, str], *, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Materialize the binding approved-mock roles before report implementation."""

    records: list[dict[str, Any]] = []
    for section, roles in _settings(config)["report"]["traceability_roles"].items():
        source = str(canonical_sources.get(section, "")).strip()
        for role in roles:
            missing_source = not source
            records.append({
                "mock_element_id": _stable_id("mock", section, role),
                "mock_section": section,
                "approved_role": role,
                "final_section": section,
                "canonical_evidence_source": source,
                "implementation_status": "preserved" if source else "",
                "deviation_reason": "",
                "schema_version": TRACEABILITY_SCHEMA_VERSION,
                "status": "error" if missing_source else "ok",
                "issue": "missing canonical evidence source" if missing_source else "",
            })
    return pd.DataFrame(records, columns=TRACEABILITY_COLUMNS)


def validate_mock_traceability(
    frame: pd.DataFrame, *, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Validate mock role coverage, section order, sources, and deviations."""

    settings = _settings(config)
    expected = int(settings["expected_counts"]["traceability_rows"])
    approved_statuses = {"preserved", "upgraded_additively", "approved_deviation"}
    source_ok = frame["canonical_evidence_source"].astype(str).str.strip().ne("").all()
    status_ok = frame["implementation_status"].astype(str).isin(approved_statuses).all()
    deviations = frame["implementation_status"].astype(str).eq("approved_deviation")
    reasons_ok = frame.loc[deviations, "deviation_reason"].astype(str).str.strip().ne("").all()
    observed_order = list(dict.fromkeys(frame["mock_section"].astype(str)))
    expected_order = list(settings["report"]["required_section_ids"])
    rows = [
        _validation_row(
            stage="mock_traceability", severity="blocking", check_name="traceability_row_count",
            observed=len(frame), expected=expected, passed=len(frame) == expected,
            issue="mock-to-final traceability row count changed",
        ),
        _validation_row(
            stage="mock_traceability", severity="blocking", check_name="traceability_section_order",
            observed=observed_order, expected=expected_order, passed=observed_order == expected_order,
            issue="mock-to-final section order changed",
        ),
        _validation_row(
            stage="mock_traceability", severity="blocking", check_name="traceability_sources",
            observed=bool(source_ok), expected=True, passed=bool(source_ok),
            issue="one or more approved mock roles lacks canonical evidence",
        ),
        _validation_row(
            stage="mock_traceability", severity="blocking", check_name="traceability_statuses",
            observed=sorted(set(frame["implementation_status"].astype(str))),
            expected=sorted(approved_statuses), passed=bool(status_ok),
            issue="one or more implementation status is not approved",
        ),
        _validation_row(
            stage="mock_traceability", severity="blocking", check_name="approved_deviation_reasons",
            observed=bool(reasons_ok), expected=True, passed=bool(reasons_ok),
            issue="an approved deviation lacks its approved reason",
        ),
    ]
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)


def image_path_to_data_uri(
    path: str | Path,
    *,
    max_dimension: int = 900,
    photographic_format: str = "JPEG",
    quality: int = 82,
    is_mask: bool = False,
) -> str:
    """Create a web-sized data URI in memory without persisting a duplicate."""

    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Missing report image: {source}")
    with Image.open(source) as opened:
        image = opened.convert("L" if is_mask else "RGB")
        image.thumbnail((int(max_dimension), int(max_dimension)), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        if is_mask:
            image.save(buffer, format="PNG", optimize=True)
            mime = "image/png"
        else:
            fmt = str(photographic_format).upper()
            if fmt not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError(f"Unsupported embedded image format: {fmt}")
            options: dict[str, Any] = {"format": fmt}
            if fmt in {"JPEG", "WEBP"}:
                options.update(quality=int(quality), optimize=True)
            image.save(buffer, **options)
            mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[fmt]
    return f"data:{mime};base64,{base64.b64encode(buffer.getvalue()).decode('ascii')}"


def visual_html(
    data_uri: str,
    *,
    alt: str,
    caption: str,
    report_role: str,
    tile_count: int = 1,
) -> str:
    """Render one auditable embedded visual block."""

    if not str(data_uri).startswith("data:image/"):
        raise ValueError("visual_html requires a data:image URI")
    if report_role not in {"analytical_view", "representative_panel", "visual_atlas"}:
        raise ValueError(f"Unsupported report visual role: {report_role}")
    return (
        f'<figure class="report-visual" data-report-role="{html.escape(report_role)}" '
        f'data-tile-count="{int(tile_count)}">'
        f'<img src="{data_uri}" alt="{html.escape(str(alt))}">'
        f'<figcaption>{html.escape(str(caption))}</figcaption></figure>'
    )


def render_model_report_html(
    model_record: Mapping[str, Any],
    section_html: Mapping[str, str],
    *,
    config: Mapping[str, Any],
) -> str:
    """Assemble one standalone report while preserving approved section order."""

    settings = _settings(config)
    sections = list(settings["report"]["required_section_ids"])
    if set(section_html) != set(sections):
        missing = sorted(set(sections) - set(section_html))
        extra = sorted(set(section_html) - set(sections))
        raise ValueError(f"Report sections differ from approved mock; missing={missing}, extra={extra}")
    model_id = str(model_record["model_id"])
    spec = model_specs(config)[model_id]
    display_name = str(spec["display_name"])
    title = f"{display_name} — {settings['report']['title_suffix']}"
    labels = {
        "executive-summary": "Executive Summary",
        "method-identity": "1. Method Identity",
        "coverage-applicability": "2. Coverage and Applicability",
        "overall-quality": "3. Overall Quality Evidence",
        "damage-and-experiments": "4. Damage Types and Experiments",
        "texture-colour-seam": "5. Texture, Colour, and Seam Behaviour",
        "semantic-structural": "6. Semantic and Structural Evidence",
        "uncertainty-prompt-stability": "7. Uncertainty, Prompt, and Stability Evidence",
        "representative-successes-failures": "8. Representative Successes and Failures",
        "difference-explanation-maps": "9. Difference and Explanation Maps",
        "failure-taxonomy-flags": "10. Failure Taxonomy and Trustworthiness Flags",
        "compute-scalability": "11. Compute and Scalability",
        "decision-support": "12. Decision Support",
        "limitations": "13. Limitations",
        "reproducibility-provenance": "14. Reproducibility and Provenance",
    }
    body = "\n".join(
        f'<section id="{section}" data-approved-order="{index}">'
        f'<h2>{labels[section]}</h2>{section_html[section]}</section>'
        for index, section in enumerate(sections)
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>
:root{{--ink:#172033;--muted:#5d6678;--paper:#fff;--wash:#f3f6fa;--accent:#315c9b;--good:#176b4d;--warn:#955d13;}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--wash);color:var(--ink);font:16px/1.58 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:1180px;margin:0 auto;background:var(--paper);padding:2.6rem clamp(1rem,4vw,4rem)}}h1{{font-size:2.25rem;line-height:1.15;margin-bottom:.35rem}}h2{{margin-top:2.4rem;border-bottom:2px solid #dbe3ef;padding-bottom:.35rem}}h3{{color:var(--accent)}}
.scope-banner,.conclusion,.limitation{{padding:.85rem 1rem;border-left:5px solid var(--accent);background:#edf4ff;margin:1rem 0}}.conclusion{{border-color:var(--good);background:#edf9f4}}.limitation{{border-color:var(--warn);background:#fff6e8}}
.metric-grid,.visual-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem}}table{{width:100%;border-collapse:collapse;font-size:.93rem}}th,td{{border:1px solid #d9e0ea;padding:.45rem;text-align:left}}th{{background:#eef3f9}}
.report-visual{{margin:1rem 0;border:1px solid #d9e0ea;padding:.7rem;background:#fff}}.report-visual img{{display:block;max-width:100%;height:auto;margin:auto}}figcaption{{color:var(--muted);font-size:.9rem;margin-top:.55rem}}
code{{overflow-wrap:anywhere}}@media print{{body{{background:#fff}}main{{max-width:none;padding:1rem}}}}
</style></head><body><main data-model-id="{html.escape(model_id)}" data-evaluation-status="{html.escape(str(spec['evaluation_status']))}">
<header><p>Trustworthy Evaluation of AI-Assisted Painting Restoration</p><h1>{html.escape(display_name)}</h1>
<p class="scope-banner">Evaluation status: <strong>{html.escape(str(spec['evaluation_status']))}</strong>. This report summarizes validated Notebook 09–30 evidence and creates no new scientific evidence.</p></header>
{body}</main></body></html>"""


def validate_model_report_html(
    html_text: str, *, model_id: str, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Validate fidelity, density, standalone rendering, scope, and claims."""

    settings = _settings(config)
    report = settings["report"]
    spec = model_specs(config)[model_id]
    section_matches = re.findall(r'<section\s+id="([^"]+)"', html_text, flags=re.I)
    image_tags = re.findall(r"<img\b[^>]*>", html_text, flags=re.I)
    sources = [
        match.group(1) for tag in image_tags
        if (match := re.search(r'\bsrc=["\']([^"\']+)["\']', tag, flags=re.I))
    ]
    embedded = [source for source in sources if source.startswith("data:image/")]
    external = [source for source in sources if not source.startswith("data:image/")]
    roles = re.findall(r'data-report-role="([^"]+)"', html_text, flags=re.I)
    tile_counts = [int(value) for value in re.findall(r'data-tile-count="(\d+)"', html_text)]
    required_sections = list(report["required_section_ids"])
    required_terms_missing = [
        term for term in report["required_terms"] if str(term).lower() not in html_text.lower()
    ]
    prohibited_present = [
        term for term in report["prohibited_terms"] if str(term).lower() in html_text.lower()
    ]
    size_mib = len(html_text.encode("utf-8")) / (1024 * 1024)
    role_expectations = {
        "analytical_view": int(spec["analytical_view_count"]),
        "representative_panel": int(spec["representative_panel_count"]),
        "visual_atlas": int(spec["visual_atlas_count"]),
    }
    rows = [
        _validation_row(
            stage="rendered_report", severity="blocking", check_name=f"{model_id}_section_order",
            observed=section_matches, expected=required_sections,
            passed=section_matches == required_sections,
            issue="rendered report does not preserve approved mock section order",
        ),
        _validation_row(
            stage="rendered_report", severity="blocking", check_name=f"{model_id}_self_contained_images",
            observed=len(external), expected=0, passed=len(external) == 0,
            issue="one or more visible report images depends on an external path",
        ),
        _validation_row(
            stage="rendered_report", severity="blocking", check_name=f"{model_id}_embedded_image_count",
            observed=len(embedded), expected=int(spec["minimum_embedded_image_count"]),
            passed=len(embedded) >= int(spec["minimum_embedded_image_count"]),
            issue="report contains fewer embedded images than approved",
        ),
        _validation_row(
            stage="rendered_report", severity="blocking", check_name=f"{model_id}_embedded_tile_count",
            observed=sum(tile_counts), expected=int(spec["minimum_embedded_tile_count"]),
            passed=sum(tile_counts) >= int(spec["minimum_embedded_tile_count"]),
            issue="report contains fewer visual tiles than approved",
        ),
        _validation_row(
            stage="rendered_report", severity="blocking", check_name=f"{model_id}_required_terms",
            observed=required_terms_missing, expected=[], passed=not required_terms_missing,
            issue="report lacks thesis framing or direct scoped assertion language",
        ),
        _validation_row(
            stage="rendered_report", severity="blocking", check_name=f"{model_id}_prohibited_terms",
            observed=prohibited_present, expected=[], passed=not prohibited_present,
            issue="report contains mock residue or a prohibited scientific claim",
        ),
        _validation_row(
            stage="rendered_report", severity="warning", check_name=f"{model_id}_soft_size_limit",
            observed=round(size_mib, 3), expected=f"<= {report['soft_report_size_warning_mib']} MiB",
            passed=size_mib <= float(report["soft_report_size_warning_mib"]),
            issue="standalone HTML exceeds the configured soft size warning",
        ),
    ]
    for role, expected_count in role_expectations.items():
        observed_count = roles.count(role)
        rows.append(_validation_row(
            stage="rendered_report", severity="blocking",
            check_name=f"{model_id}_{role}_count", observed=observed_count,
            expected=expected_count, passed=observed_count >= expected_count,
            issue=f"report contains fewer {role} visuals than approved",
        ))
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)


def build_report_index_row(
    report_path: str | Path,
    *,
    project_root: str | Path,
    model_id: str,
    representative_candidate_ids: Sequence[str],
    source_artifact_paths: Sequence[str],
    source_checksums: Mapping[str, str],
    upstream_run_ids: Mapping[str, str],
    generated_at_utc: str,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one normalized index row from a persisted standalone report."""

    root = Path(project_root).resolve()
    path = Path(report_path).resolve()
    try:
        relative_report_path = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("Report path escapes the project root") from exc
    text = path.read_text(encoding="utf-8-sig")
    spec = model_specs(config)[model_id]
    roles = re.findall(r'data-report-role="([^"]+)"', text, flags=re.I)
    tile_counts = [int(value) for value in re.findall(r'data-tile-count="(\d+)"', text)]
    embedded = re.findall(r'<img\b[^>]*\bsrc=["\']data:image/', text, flags=re.I)
    return {
        "report_id": _stable_id("report", model_id),
        "model_id": model_id,
        "display_name": spec["display_name"],
        "evaluation_status": spec["evaluation_status"],
        "report_path": relative_report_path,
        "report_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
        "section_count": len(re.findall(r'<section\s+id="', text, flags=re.I)),
        "embedded_image_count": len(embedded),
        "embedded_tile_count": sum(tile_counts),
        "analytical_view_count": roles.count("analytical_view"),
        "representative_panel_count": roles.count("representative_panel"),
        "visual_atlas_count": roles.count("visual_atlas"),
        "representative_candidate_ids_json": json.dumps(list(representative_candidate_ids), separators=(",", ":")),
        "source_artifact_paths_json": json.dumps(list(source_artifact_paths), separators=(",", ":")),
        "source_checksums_json": json.dumps(dict(source_checksums), sort_keys=True, separators=(",", ":")),
        "upstream_run_ids_json": json.dumps(dict(upstream_run_ids), sort_keys=True, separators=(",", ":")),
        "mock_traceability_status": "passed",
        "self_contained": True,
        "generated_at_utc": generated_at_utc,
        "schema_version": REPORT_INDEX_SCHEMA_VERSION,
        "status": "ok",
        "issue": "",
    }


def validate_report_index(frame: pd.DataFrame, *, config: Mapping[str, Any]) -> pd.DataFrame:
    """Validate exact four-report rows, schemas, paths, density, and scope labels."""

    settings = _settings(config)
    specs = model_specs(config)
    rows: list[dict[str, Any]] = []
    rows.append(_validation_row(
        stage="report_index", severity="blocking", check_name="exact_columns",
        observed=list(frame.columns), expected=list(REPORT_INDEX_COLUMNS),
        passed=list(frame.columns) == list(REPORT_INDEX_COLUMNS),
        issue="report-index columns differ from canonical schema",
    ))
    rows.append(_validation_row(
        stage="report_index", severity="blocking", check_name="exact_model_rows",
        observed=sorted(frame.get("model_id", pd.Series(dtype=str)).astype(str)),
        expected=sorted(specs),
        passed=(len(frame) == int(settings["expected_counts"]["report_index_rows"])
                and set(frame.get("model_id", pd.Series(dtype=str)).astype(str)) == set(specs)),
        issue="report index does not contain exactly one row per approved model",
    ))
    if list(frame.columns) == list(REPORT_INDEX_COLUMNS):
        unique_ok = frame["report_id"].nunique() == len(frame) and frame["model_id"].nunique() == len(frame)
        schema_ok = frame["schema_version"].eq(REPORT_INDEX_SCHEMA_VERSION).all()
        status_ok = frame["status"].eq("ok").all() and frame["self_contained"].map(_as_bool).all()
        density_ok = True
        scope_ok = True
        filename_ok = True
        for row in frame.to_dict("records"):
            spec = specs[str(row["model_id"])]
            density_ok &= (
                int(row["section_count"]) == int(settings["expected_counts"]["section_count_per_report"])
                and int(row["embedded_image_count"]) >= int(spec["minimum_embedded_image_count"])
                and int(row["embedded_tile_count"]) >= int(spec["minimum_embedded_tile_count"])
            )
            scope_ok &= str(row["evaluation_status"]) == str(spec["evaluation_status"])
            expected_path = (
                Path(str(settings["output"]["root"]))
                / str(settings["output"]["reports_dir"])
                / str(spec["report_filename"])
            ).as_posix()
            filename_ok &= str(row["report_path"]) == expected_path
        for name, passed, issue in (
            ("unique_report_and_model_ids", unique_ok, "report or model IDs are not unique"),
            ("schema_and_status", schema_ok and status_ok, "report index has invalid schema/status/portability"),
            ("per_model_density", density_ok, "report index density is below approved minimum"),
            ("evaluation_scope_labels", scope_ok, "evaluation status differs from approved model scope"),
            ("canonical_report_filenames", filename_ok, "one or more report filenames changed"),
        ):
            rows.append(_validation_row(
                stage="report_index", severity="blocking", check_name=name,
                observed=bool(passed), expected=True, passed=bool(passed), issue=issue,
            ))
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS)


def atomic_write_csv(frame: pd.DataFrame, path: str | Path, *, retries: int = 8) -> None:
    """Write CSV atomically with bounded Windows replacement retries."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    for attempt in range(int(retries)):
        try:
            os.replace(temporary, destination)
            return
        except PermissionError:
            if attempt + 1 >= int(retries):
                temporary.unlink(missing_ok=True)
                raise
            time.sleep(0.05 * (attempt + 1))


def atomic_write_text(text: str, path: str | Path, *, retries: int = 8) -> None:
    """Write UTF-8 text atomically with bounded Windows replacement retries."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    for attempt in range(int(retries)):
        try:
            os.replace(temporary, destination)
            return
        except PermissionError:
            if attempt + 1 >= int(retries):
                temporary.unlink(missing_ok=True)
                raise
            time.sleep(0.05 * (attempt + 1))


__all__ = [
    "APPLICABILITY_COLUMNS", "CONFIG_SCHEMA_VERSION", "MODULE_NAME",
    "MODULE_VERSION", "REPORT_INDEX_COLUMNS", "REPORT_INDEX_SCHEMA_VERSION",
    "SELECTION_COLUMNS", "SELECTION_SCHEMA_VERSION", "TRACEABILITY_COLUMNS",
    "TRACEABILITY_SCHEMA_VERSION", "VALIDATION_COLUMNS", "atomic_write_csv",
    "atomic_write_text", "build_applicability_matrix", "build_mock_traceability",
    "build_report_index_row", "image_path_to_data_uri", "load_model_report_config",
    "load_upstream_manifests", "model_specs", "render_model_report_html",
    "resolve_model_report_inputs", "select_representative_cases",
    "validate_applicability_matrix", "validate_inventory_contract",
    "validate_loaded_input_table",
    "validate_mock_traceability", "validate_model_report_html",
    "validate_report_index", "validate_representative_selection",
    "visual_html",
]
