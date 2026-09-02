"""Preparation and report helpers for Notebook 33.

The module owns deterministic contract validation, report-plan construction,
portable HTML assembly, and safe persistence.  It deliberately does not compute
new scientific metrics, tests, rankings, exclusions, or composite scores.
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
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd
import yaml
from PIL import Image


MODULE_NAME = "restoration_eval.final_evaluation_report"
MODULE_VERSION = "1.3.0"
CONFIG_SCHEMA_VERSION = "final_evaluation_report_config.v1"
THESIS_TABLE_SCHEMA_VERSION = "thesis_tables.v1"
LATEX_TABLE_SCHEMA_VERSION = "latex_tables.v1"
EVIDENCE_CATALOG_SCHEMA_VERSION = "final_report_evidence_catalog.v1"
TRACEABILITY_SCHEMA_VERSION = "final_report_mock_traceability.v1"
REPORT_SCHEMA_VERSION = "final_evaluation_report.v1"

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

THESIS_TABLE_COLUMNS = (
    "table_row_id",
    "table_id",
    "table_order",
    "section_id",
    "row_order",
    "row_key",
    "row_label",
    "values_json",
    "scope",
    "denominator",
    "independent_unit",
    "source_notebook_ids_json",
    "source_paths_json",
    "source_row_ids_json",
    "applicability_status",
    "interpretation",
    "schema_version",
    "status",
    "issue",
)

LATEX_TABLE_COLUMNS = (
    "latex_table_id",
    "table_id",
    "table_order",
    "section_id",
    "caption",
    "label",
    "column_specification",
    "latex",
    "source_row_count",
    "schema_version",
    "status",
    "issue",
)

EVIDENCE_CATALOG_COLUMNS = (
    "catalog_id",
    "record_type",
    "section_id",
    "element_id",
    "display_order",
    "approved_role",
    "source_keys_json",
    "expected_count",
    "implementation_status",
    "deviation_reason",
    "schema_version",
    "status",
    "issue",
)

TRACEABILITY_COLUMNS = (
    "mock_element_id",
    "mock_section",
    "approved_role",
    "final_section",
    "canonical_evidence_source",
    "implementation_status",
    "deviation_reason",
)

SELECTED_VISUAL_COLUMNS = (
    "visual_order",
    "selection_lane",
    "case_id",
    "painting_id",
    "grid_path",
    "case_report_path",
    "selection_reason",
)


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    return config.get("final_evaluation_report", config)


def _stable_id(prefix: str, *parts: Any) -> str:
    material = "|".join(str(part) for part in parts)
    suffix = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{suffix}"


def _json_strings(values: Iterable[Any]) -> str:
    return json.dumps([str(value) for value in values], ensure_ascii=False)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _relative_path(value: Any) -> bool:
    path = Path(str(value))
    return bool(str(value).strip()) and not path.is_absolute() and ".." not in path.parts


def _validation_row(
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
        "check_id": _stable_id("check", stage, check_name),
        "validation_stage": stage,
        "severity": severity,
        "check_name": check_name,
        "observed": display(observed),
        "expected": display(expected),
        "passed": bool(passed),
        "issue": "" if passed else issue,
    }


def sha256_path(path: str | Path) -> str:
    """Hash a file or directory using the canonical manifest framing."""

    target = Path(path)
    if target.is_file():
        digest = hashlib.sha256()
        with target.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    if not target.is_dir():
        raise FileNotFoundError(target)

    digest = hashlib.sha256()
    for child in sorted(item for item in target.rglob("*") if item.is_file()):
        relative = child.relative_to(target).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(sha256_path(child)))
    return digest.hexdigest()


def load_final_evaluation_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the approved Notebook 33 configuration."""

    with Path(path).open("r", encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Notebook 33 configuration must be a mapping")
    if config.get("config_schema_version") != CONFIG_SCHEMA_VERSION:
        raise ValueError("Unexpected Notebook 33 configuration schema")

    settings = config.get("final_evaluation_report")
    if not isinstance(settings, dict):
        raise ValueError("Missing final_evaluation_report configuration section")
    if settings.get("notebook_id") != "33":
        raise ValueError("Notebook 33 identity is not locked")
    if settings.get("notebook_stem") != "33_final_evaluation_report":
        raise ValueError("Notebook 33 stem is not locked")
    if settings.get("creates_new_scientific_evidence") is not False:
        raise ValueError("Notebook 33 must remain presentation-only")

    expected = settings["expected_counts"]
    contracts = settings["input_table_contracts"]
    if len(contracts) != int(expected["input_tables"]):
        raise ValueError("Input-table contract count does not match expected_counts")

    manifests = settings["upstream_manifests"]
    expected_ids = [f"{number:02d}" for number in range(1, 33)]
    if list(manifests) != expected_ids:
        raise ValueError("Upstream manifests must explicitly cover Notebooks 01-32")

    output = settings["output"]
    exact_output = {
        "root": "outputs/33_final_evaluation_report",
        "thesis_tables_path": "data/thesis_tables.csv",
        "latex_tables_path": "data/latex_tables.csv",
        "evidence_catalog_path": "data/report_evidence_catalog.csv",
        "thesis_figures_dir": "figures/thesis",
        "publication_figures_dir": "figures/publication",
        "final_report_path": "reports/final_evaluation.html",
        "limitations_path": "reports/limitations_and_deviations.md",
        "run_manifest_path": "manifests/run_manifest.json",
        "artifacts_path": "manifests/artifacts.csv",
        "validation_path": "validation/checks.csv",
        "work_dir": "work",
    }
    if output != exact_output:
        raise ValueError("Notebook 33 output contract differs from the approved contract")

    all_declared_paths = list(settings["inputs"].values()) + list(manifests.values())
    if not all(_relative_path(value) for value in all_declared_paths):
        raise ValueError("All Notebook 33 input paths must be repository-relative")

    tables = settings["table_plan"]
    if len(tables) != int(expected["table_definitions"]):
        raise ValueError("Unexpected final-report table count")
    if sum(int(item["expected_rows"]) for item in tables) != int(
        expected["thesis_table_rows"]
    ):
        raise ValueError("Thesis-table row arithmetic is inconsistent")
    if len({item["table_id"] for item in tables}) != len(tables):
        raise ValueError("Final-report table identifiers must be unique")

    thesis_figures = settings["thesis_figures"]
    publication_figures = settings["publication_figures"]
    if len(thesis_figures) != int(expected["thesis_figures"]):
        raise ValueError("Unexpected thesis-figure count")
    if len(publication_figures) != int(expected["publication_figures"]):
        raise ValueError("Unexpected publication-figure count")
    all_figures = thesis_figures + publication_figures
    if len({item["figure_id"] for item in all_figures}) != len(all_figures):
        raise ValueError("Final-report figure identifiers must be unique")
    if len({(item["section_id"], item["filename"]) for item in all_figures}) != len(
        all_figures
    ):
        raise ValueError("Final-report figure destinations must be unique")

    sections = settings["report"]["sections"]
    if len(sections) != int(expected["report_sections"]):
        raise ValueError("Unexpected final-report section count")
    if len({item["section_id"] for item in sections}) != len(sections):
        raise ValueError("Final-report section identifiers must be unique")
    if sum(int(item["claim_count"]) for item in sections) != int(
        expected["evidence_claims"]
    ):
        raise ValueError("Report claim arithmetic is inconsistent")

    if len(settings["limitations"]) != int(expected["limitation_records"]):
        raise ValueError("Unexpected limitation/deviation count")
    if len(set(settings["limitations"])) != len(settings["limitations"]):
        raise ValueError("Limitation identifiers must be unique")

    visual_count = sum(
        int(value)
        for value in settings["visual_selection"]["selected_case_grid_quotas"].values()
    )
    if visual_count != int(expected["selected_case_grids"]):
        raise ValueError("Selected-case visual quota arithmetic is inconsistent")

    catalog_count = (
        int(expected["evidence_claims"])
        + int(expected["table_definitions"])
        + int(expected["persisted_figures"])
        + int(expected["limitation_records"])
        + 1
    )
    if catalog_count != int(expected["evidence_catalog_rows"]):
        raise ValueError("Evidence-catalog arithmetic is inconsistent")
    if catalog_count + len(sections) != int(expected["mock_traceability_rows"]):
        raise ValueError("Mock-traceability arithmetic is inconsistent")

    physical_count = 3 + len(all_figures) + 2 + 2 + 1
    if physical_count != int(expected["physical_output_files"]):
        raise ValueError("Physical-output arithmetic is inconsistent")
    if int(expected["artifact_records"]) != 8:
        raise ValueError("Notebook 33 must register exactly eight artifacts")

    return config


def resolve_final_evaluation_inputs(
    config: Mapping[str, Any], project_root: str | Path
) -> dict[str, Path]:
    """Resolve every declared input and upstream manifest beneath the root."""

    root = Path(project_root).resolve()
    settings = _settings(config)
    resolved = {
        key: (root / str(relative)).resolve()
        for key, relative in settings["inputs"].items()
    }
    resolved.update(
        {
            f"manifest_{notebook_id}_path": (root / str(relative)).resolve()
            for notebook_id, relative in settings["upstream_manifests"].items()
        }
    )
    if any(root not in path.parents and path != root for path in resolved.values()):
        raise ValueError("A resolved Notebook 33 input escapes the repository root")
    return resolved


def resolve_final_evaluation_outputs(
    config: Mapping[str, Any], project_root: str | Path
) -> dict[str, Path]:
    """Resolve the exact Notebook 33 output contract beneath its owned root."""

    root = Path(project_root).resolve()
    output = _settings(config)["output"]
    output_root = (root / output["root"]).resolve()
    resolved = {"root": output_root}
    for key, relative in output.items():
        if key == "root":
            continue
        resolved[key] = (output_root / str(relative)).resolve()
    if any(output_root not in path.parents and path != output_root for path in resolved.values()):
        raise ValueError("A resolved Notebook 33 output escapes its owned root")
    return resolved


def validate_inventory_contract(
    inventory: pd.DataFrame,
    project_root: str | Path,
    inputs: Mapping[str, Path],
) -> pd.DataFrame:
    """Validate declared inputs against disk and the canonical inventory."""

    root = Path(project_root).resolve()
    required = {"relative_path", "read_error_count"}
    missing = sorted(required - set(inventory.columns))
    if missing:
        raise ValueError(f"Inventory is missing required columns: {missing}")

    inventory_paths = set(inventory["relative_path"].astype(str))
    excluded_inventory_names = {"project_file_inventory.csv", "inventory_run.json"}
    checks: list[dict[str, Any]] = []
    for key, path in sorted(inputs.items()):
        exists = path.exists()
        checks.append(
            _validation_row(
                "inventory_preflight",
                f"{key} exists",
                exists,
                True,
                exists,
                f"Declared input does not exist: {path}",
            )
        )
        if not exists:
            continue
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            represented = any(value.startswith(relative.rstrip("/") + "/") for value in inventory_paths)
        elif path.name in excluded_inventory_names and path.parent.name == "inventory":
            represented = True
        else:
            represented = relative in inventory_paths
        checks.append(
            _validation_row(
                "inventory_preflight",
                f"{key} represented in inventory",
                represented,
                True,
                represented,
                f"Declared input is absent from inventory: {relative}",
            )
        )

    read_errors = int(pd.to_numeric(inventory["read_error_count"], errors="coerce").fillna(0).sum())
    checks.append(
        _validation_row(
            "inventory_preflight",
            "inventory read errors",
            read_errors,
            0,
            read_errors == 0,
            "The canonical inventory contains read errors",
        )
    )
    return pd.DataFrame(checks, columns=VALIDATION_COLUMNS)


def validate_loaded_input_table(
    frame: pd.DataFrame,
    input_key: str,
    config: Mapping[str, Any],
    stage: str = "input_loading",
) -> pd.DataFrame:
    """Validate row count and required columns for one canonical input table."""

    contract = _settings(config)["input_table_contracts"][input_key]
    expected_rows = int(contract["rows"])
    required_columns = [str(value) for value in contract["required_columns"]]
    missing_columns = sorted(set(required_columns) - set(frame.columns))
    checks = [
        _validation_row(
            stage,
            f"{input_key} row count",
            len(frame),
            expected_rows,
            len(frame) == expected_rows,
            f"Unexpected row count for {input_key}",
        ),
        _validation_row(
            stage,
            f"{input_key} required columns",
            missing_columns,
            [],
            not missing_columns,
            f"Missing required columns for {input_key}: {missing_columns}",
        ),
    ]
    return pd.DataFrame(checks, columns=VALIDATION_COLUMNS)


def append_validation_checks(collector: Any, checks: pd.DataFrame) -> None:
    """Append helper-style validation rows to the shared project collector."""

    missing = sorted(set(VALIDATION_COLUMNS) - set(checks.columns))
    if missing:
        raise ValueError(f"Validation frame is missing columns: {missing}")
    for row in checks.to_dict(orient="records"):
        collector.add(
            validation_stage=str(row["validation_stage"]),
            check_id=str(row["check_id"]),
            check_description=str(row["check_name"]),
            severity=str(row["severity"]),
            expected=row["expected"],
            observed=row["observed"],
            passed=_as_bool(row["passed"]),
            details=str(row["issue"]),
        )


def load_upstream_manifests(
    config: Mapping[str, Any], project_root: str | Path
) -> dict[str, dict[str, Any]]:
    """Load the explicitly declared Notebook 01-32 run manifests."""

    root = Path(project_root).resolve()
    manifests: dict[str, dict[str, Any]] = {}
    for notebook_id, relative in _settings(config)["upstream_manifests"].items():
        path = (root / str(relative)).resolve()
        with path.open("r", encoding="utf-8-sig") as handle:
            manifests[str(notebook_id)] = json.load(handle)
    return manifests


def validate_upstream_completion(
    manifests: Mapping[str, Mapping[str, Any]],
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Require every declared upstream run to be completed and validated."""

    expected_ids = list(_settings(config)["upstream_manifests"])
    checks = [
        _validation_row(
            "upstream_preflight",
            "upstream manifest identity",
            sorted(manifests),
            expected_ids,
            sorted(manifests) == expected_ids,
            "The upstream manifest set differs from Notebooks 01-32",
        )
    ]
    for notebook_id in expected_ids:
        manifest = manifests.get(notebook_id, {})
        completed = (
            manifest.get("run_status") == "completed"
            and manifest.get("validation_status") == "passed"
            and manifest.get("completion_gate_passed") is True
        )
        checks.append(
            _validation_row(
                "upstream_preflight",
                f"Notebook {notebook_id} completion",
                {
                    "run_status": manifest.get("run_status"),
                    "validation_status": manifest.get("validation_status"),
                    "completion_gate_passed": manifest.get("completion_gate_passed"),
                },
                {
                    "run_status": "completed",
                    "validation_status": "passed",
                    "completion_gate_passed": True,
                },
                completed,
                f"Notebook {notebook_id} is not a completed upstream dependency",
            )
        )
    return pd.DataFrame(checks, columns=VALIDATION_COLUMNS)


def build_thesis_table_plan(config: Mapping[str, Any]) -> pd.DataFrame:
    """Return the approved 15-table, 293-row display plan."""

    records = []
    for order, item in enumerate(_settings(config)["table_plan"], start=1):
        records.append(
            {
                "table_order": order,
                "table_id": str(item["table_id"]),
                "section_id": str(item["section_id"]),
                "expected_rows": int(item["expected_rows"]),
                "source_keys_json": _json_strings(item["source_keys"]),
            }
        )
    return pd.DataFrame(records)


def build_figure_plan(config: Mapping[str, Any]) -> pd.DataFrame:
    """Return the approved 18 thesis and six publication figure plan."""

    settings = _settings(config)
    records = []
    for figure_class, key, output_key in (
        ("thesis", "thesis_figures", "thesis_figures_dir"),
        ("publication", "publication_figures", "publication_figures_dir"),
    ):
        for class_order, item in enumerate(settings[key], start=1):
            relative_path = Path(settings["output"]["root"]) / settings["output"][output_key] / item["filename"]
            records.append(
                {
                    "figure_order": len(records) + 1,
                    "figure_class_order": class_order,
                    "figure_class": figure_class,
                    "figure_id": str(item["figure_id"]),
                    "section_id": str(item["section_id"]),
                    "filename": str(item["filename"]),
                    "relative_path": relative_path.as_posix(),
                }
            )
    return pd.DataFrame(records)


def build_report_section_plan(config: Mapping[str, Any]) -> pd.DataFrame:
    """Return the approved 19-section report order and claim allocation."""

    records = []
    for order, item in enumerate(_settings(config)["report"]["sections"], start=1):
        records.append(
            {
                "section_order": order,
                "section_id": str(item["section_id"]),
                "title": str(item["title"]),
                "claim_count": int(item["claim_count"]),
                "source_keys_json": _json_strings(item["source_keys"]),
            }
        )
    return pd.DataFrame(records)


def build_evidence_catalog_plan(config: Mapping[str, Any]) -> pd.DataFrame:
    """Build the approved 106-record claim/table/figure/limitation catalog."""

    settings = _settings(config)
    records: list[dict[str, Any]] = []

    def append_record(
        record_type: str,
        section_id: str,
        element_id: str,
        approved_role: str,
        source_keys: Sequence[Any],
        expected_count: int = 1,
    ) -> None:
        records.append(
            {
                "catalog_id": _stable_id("catalog", record_type, section_id, element_id),
                "record_type": record_type,
                "section_id": section_id,
                "element_id": element_id,
                "display_order": len(records) + 1,
                "approved_role": approved_role,
                "source_keys_json": _json_strings(source_keys),
                "expected_count": int(expected_count),
                "implementation_status": "preserved",
                "deviation_reason": "",
                "schema_version": EVIDENCE_CATALOG_SCHEMA_VERSION,
                "status": "planned",
                "issue": "",
            }
        )

    for section in settings["report"]["sections"]:
        for number in range(1, int(section["claim_count"]) + 1):
            append_record(
                "claim",
                str(section["section_id"]),
                f"{section['section_id']}__claim_{number:02d}",
                "fact_followed_by_scoped_plain_language_assertion",
                section["source_keys"],
            )

    for table in settings["table_plan"]:
        append_record(
            "table",
            str(table["section_id"]),
            str(table["table_id"]),
            "approved_compact_thesis_and_latex_table",
            table["source_keys"],
            int(table["expected_rows"]),
        )

    for figure_class, key in (("thesis_figure", "thesis_figures"), ("publication_figure", "publication_figures")):
        for figure in settings[key]:
            append_record(
                figure_class,
                str(figure["section_id"]),
                str(figure["figure_id"]),
                "approved_persisted_analytical_figure",
                [],
            )

    for number, limitation in enumerate(settings["limitations"], start=1):
        append_record(
            "limitation",
            "limitations",
            f"limitation_{number:02d}",
            str(limitation),
            ["evidence_dependency_audit_path"],
        )

    append_record(
        "report",
        "executive-findings",
        "final_evaluation_report",
        "self_contained_final_thesis_synthesis",
        ["model_report_index_path", "case_report_index_path", "painting_report_index_path"],
    )
    return pd.DataFrame(records, columns=EVIDENCE_CATALOG_COLUMNS)


def build_mock_traceability(config: Mapping[str, Any]) -> pd.DataFrame:
    """Build the 125-row approved mock-to-final traceability baseline."""

    section_plan = build_report_section_plan(config)
    catalog = build_evidence_catalog_plan(config)
    records: list[dict[str, Any]] = []
    for row in section_plan.to_dict(orient="records"):
        records.append(
            {
                "mock_element_id": f"section__{row['section_id']}",
                "mock_section": row["section_id"],
                "approved_role": f"section_order_{int(row['section_order']):02d}",
                "final_section": row["section_id"],
                "canonical_evidence_source": row["source_keys_json"],
                "implementation_status": "preserved",
                "deviation_reason": "",
            }
        )
    for row in catalog.to_dict(orient="records"):
        records.append(
            {
                "mock_element_id": row["element_id"],
                "mock_section": row["section_id"],
                "approved_role": row["approved_role"],
                "final_section": row["section_id"],
                "canonical_evidence_source": row["source_keys_json"],
                "implementation_status": "preserved",
                "deviation_reason": "",
            }
        )
    return pd.DataFrame(records, columns=TRACEABILITY_COLUMNS)


def validate_preparation_plans(config: Mapping[str, Any]) -> pd.DataFrame:
    """Validate every approved preparation-layer cardinality and identity."""

    settings = _settings(config)
    expected = settings["expected_counts"]
    table_plan = build_thesis_table_plan(config)
    figure_plan = build_figure_plan(config)
    section_plan = build_report_section_plan(config)
    catalog = build_evidence_catalog_plan(config)
    traceability = build_mock_traceability(config)
    checks = [
        _validation_row("preparation_plan", "table definitions", len(table_plan), expected["table_definitions"], len(table_plan) == int(expected["table_definitions"]), "Unexpected table-plan count"),
        _validation_row("preparation_plan", "thesis table rows", int(table_plan["expected_rows"].sum()), expected["thesis_table_rows"], int(table_plan["expected_rows"].sum()) == int(expected["thesis_table_rows"]), "Unexpected thesis-table row arithmetic"),
        _validation_row("preparation_plan", "persisted figures", len(figure_plan), expected["persisted_figures"], len(figure_plan) == int(expected["persisted_figures"]), "Unexpected figure-plan count"),
        _validation_row("preparation_plan", "report sections", len(section_plan), expected["report_sections"], len(section_plan) == int(expected["report_sections"]), "Unexpected report-section count"),
        _validation_row("preparation_plan", "evidence claims", int(section_plan["claim_count"].sum()), expected["evidence_claims"], int(section_plan["claim_count"].sum()) == int(expected["evidence_claims"]), "Unexpected evidence-claim count"),
        _validation_row("preparation_plan", "evidence catalog", len(catalog), expected["evidence_catalog_rows"], len(catalog) == int(expected["evidence_catalog_rows"]), "Unexpected evidence-catalog count"),
        _validation_row("preparation_plan", "mock traceability", len(traceability), expected["mock_traceability_rows"], len(traceability) == int(expected["mock_traceability_rows"]), "Unexpected mock-traceability count"),
        _validation_row("preparation_plan", "mock implementation states", sorted(traceability["implementation_status"].unique()), ["preserved"], set(traceability["implementation_status"]) == {"preserved"}, "Unapproved mock deviation exists"),
    ]
    return pd.DataFrame(checks, columns=VALIDATION_COLUMNS)


def select_final_case_grids(
    selected_cases: pd.DataFrame,
    case_report_index: pd.DataFrame,
    project_root: str | Path,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select the approved 12 auditable case grids by fixed lane quotas."""

    root = Path(project_root).resolve()
    quotas = _settings(config)["visual_selection"]["selected_case_grid_quotas"]
    ordered = selected_cases.sort_values(["selection_order", "case_id"], kind="stable")
    report_lookup = case_report_index.set_index("case_id")["report_path"].to_dict()
    records = []
    grid_root = root / _settings(config)["inputs"]["selected_case_grids_dir"]
    for lane, quota in quotas.items():
        lane_rows = ordered.loc[ordered["selection_lane"].astype(str).eq(str(lane))].head(int(quota))
        if len(lane_rows) != int(quota):
            raise ValueError(f"Selection lane {lane!r} cannot satisfy quota {quota}")
        for row in lane_rows.to_dict(orient="records"):
            case_id = str(row["case_id"])
            records.append(
                {
                    "visual_order": len(records) + 1,
                    "selection_lane": str(lane),
                    "case_id": case_id,
                    "painting_id": str(row["painting_id"]),
                    "grid_path": (grid_root / f"{case_id}.png").relative_to(root).as_posix(),
                    "case_report_path": str(report_lookup.get(case_id, "")),
                    "selection_reason": str(row.get("selection_reason", "")),
                }
            )
    return pd.DataFrame(records, columns=SELECTED_VISUAL_COLUMNS)


def validate_selected_case_grids(
    selection: pd.DataFrame,
    project_root: str | Path,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Validate visual count, lane quotas, uniqueness, files, and report links."""

    root = Path(project_root).resolve()
    expected = _settings(config)["expected_counts"]
    quotas = _settings(config)["visual_selection"]["selected_case_grid_quotas"]
    observed_quotas = selection.groupby("selection_lane").size().to_dict()
    missing_files = [
        value for value in selection["grid_path"].astype(str) if not (root / value).is_file()
    ]
    checks = [
        _validation_row("visual_selection", "selected grid count", len(selection), expected["selected_case_grids"], len(selection) == int(expected["selected_case_grids"]), "Unexpected selected-grid count"),
        _validation_row("visual_selection", "selected grid lane quotas", observed_quotas, {key: int(value) for key, value in quotas.items()}, observed_quotas == {key: int(value) for key, value in quotas.items()}, "Selected-grid lane quotas differ from the approved contract"),
        _validation_row("visual_selection", "selected grid case uniqueness", selection["case_id"].nunique(), len(selection), selection["case_id"].nunique() == len(selection), "Selected visual cases are not unique"),
        _validation_row("visual_selection", "selected grid files", missing_files, [], not missing_files, "One or more selected case grids are missing"),
        _validation_row("visual_selection", "selected case report paths", int(selection["case_report_path"].astype(str).str.len().gt(0).sum()), len(selection), selection["case_report_path"].astype(str).str.len().gt(0).all(), "One or more selected cases lacks a report path"),
    ]
    return pd.DataFrame(checks, columns=VALIDATION_COLUMNS)


def _native_scalar(value: Any) -> Any:
    """Return a JSON-safe scalar while preserving explicit missingness."""

    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except (AttributeError, ValueError):
            pass
    return value


def _json_object(values: Mapping[str, Any]) -> str:
    return json.dumps(
        {str(key): _native_scalar(value) for key, value in values.items()},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def _require_row_count(frame: pd.DataFrame, expected: int, label: str) -> None:
    if len(frame) != int(expected):
        raise ValueError(f"{label} expected {expected} rows, observed {len(frame)}")


def build_final_thesis_tables(
    source_tables: Mapping[str, pd.DataFrame],
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the approved 15-table, 293-row presentation-only synthesis."""

    settings = _settings(config)
    required_keys = set(settings["input_table_contracts"])
    missing_keys = sorted(required_keys - set(source_tables))
    if missing_keys:
        raise KeyError(f"Final table construction is missing sources: {missing_keys}")

    table_plan = {
        str(item["table_id"]): {
            "table_order": order,
            "section_id": str(item["section_id"]),
            "expected_rows": int(item["expected_rows"]),
        }
        for order, item in enumerate(settings["table_plan"], start=1)
    }
    records: list[dict[str, Any]] = []

    def add(
        table_id: str,
        row_key: str,
        row_label: str,
        values: Mapping[str, Any],
        scope: str,
        denominator: str,
        independent_unit: str,
        source_notebook_ids: Sequence[str],
        source_keys: Sequence[str],
        source_row_ids: Sequence[str],
        applicability_status: str,
        interpretation: str,
    ) -> None:
        plan = table_plan[table_id]
        row_order = 1 + sum(item["table_id"] == table_id for item in records)
        records.append(
            {
                "table_row_id": _stable_id("thesis", table_id, row_key),
                "table_id": table_id,
                "table_order": int(plan["table_order"]),
                "section_id": plan["section_id"],
                "row_order": row_order,
                "row_key": str(row_key),
                "row_label": str(row_label),
                "values_json": _json_object(values),
                "scope": str(scope),
                "denominator": str(denominator),
                "independent_unit": str(independent_unit),
                "source_notebook_ids_json": _json_strings(source_notebook_ids),
                "source_paths_json": _json_strings(
                    [settings["inputs"][key] for key in source_keys]
                ),
                "source_row_ids_json": _json_strings(source_row_ids),
                "applicability_status": str(applicability_status),
                "interpretation": str(interpretation),
                "schema_version": THESIS_TABLE_SCHEMA_VERSION,
                "status": "ok",
                "issue": "",
            }
        )

    # T01: four approved research-question or practical-output positions.
    for item in settings["research_questions"]:
        question_id = str(item["id"])
        add(
            "t01_research_question_map",
            question_id,
            str(item["title"]),
            {
                "question_id": question_id,
                "evidence_status": "addressed_by_completed_upstream_evidence",
                "new_science_in_notebook_33": False,
            },
            "thesis_research_question_map",
            "one approved question or practical output",
            "research question",
            ["01", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32"],
            ["evidence_coverage_path", "proposal_path"],
            [question_id],
            "supported",
            "Notebook 33 answers this position only with completed, scoped upstream evidence.",
        )

    # T02: eight transparent dataset and population facts.
    artworks = source_tables["artworks_path"]
    cases = source_tables["case_registry_path"]
    explanations = source_tables["explanation_cases_path"]
    style_count = int(
        artworks["style_or_period"].fillna("").astype(str).str.strip().ne("").sum()
    )
    primary_count = int(
        explanations["scope_status"].astype(str).eq("supported_primary_scope").sum()
    )
    nonzero_case_ids = set(
        cases.loc[
            pd.to_numeric(cases["realized_damage_fraction"], errors="coerce")
            .fillna(0.0)
            .gt(0.0),
            "case_id",
        ].astype(str)
    )
    nonzero_primary_count = int(
        explanations.loc[
            explanations["scope_status"].astype(str).eq("supported_primary_scope"),
            "case_id",
        ].astype(str).isin(nonzero_case_ids).sum()
    )
    dataset_measures = [
        ("paintings", "Controlled paintings", len(artworks), "painting", "01", "artworks_path"),
        ("registered_cases", "Registered experimental cases", cases["case_id"].nunique(), "case", "08", "case_registry_path"),
        ("eligible_cases", "Restoration-eligible cases", explanations["case_id"].nunique(), "case", "29", "explanation_cases_path"),
        ("primary_candidates", "Primary three-model candidates", primary_count, "candidate", "29", "explanation_cases_path"),
        ("nonzero_primary", "Nonzero primary candidates", nonzero_primary_count, "candidate", "29", "explanation_cases_path"),
        ("style_documented", "Paintings with documented style or period", style_count, "painting", "01", "artworks_path"),
        ("style_missing", "Paintings without documented style or period", len(artworks) - style_count, "painting", "01", "artworks_path"),
        ("sdxl_candidates", "Bounded SDXL candidates", int(explanations["model_id"].astype(str).eq("sdxl_inpainting").sum()), "candidate", "29", "explanation_cases_path"),
    ]
    for key, label, value, unit, notebook_id, source_key in dataset_measures:
        add(
            "t02_dataset_design_scope",
            key,
            label,
            {"count": int(value), "unit": unit},
            "controlled_50_and_approved_extensions",
            f"all applicable {unit} records",
            unit,
            [notebook_id],
            [source_key],
            [f"summary:{key}"],
            "supported" if key != "style_missing" else "documented_limitation",
            "This count defines report coverage and is not evidence of real-world conservation generality.",
        )

    # T03: one row per model card.
    model_cards = source_tables["model_cards_path"].sort_values("model_id", kind="stable")
    for row in model_cards.to_dict(orient="records"):
        model_id = str(row["model_id"])
        add(
            "t03_model_coverage",
            model_id,
            str(row["display_name"]),
            {
                "evaluation_status": row["evaluation_status"],
                "model_family": row["model_family"],
                "deterministic": row["deterministic"],
                "prompt_dependent": row["prompt_dependent"],
                "evaluated_case_count": row["evaluated_case_count"],
                "evaluated_candidate_count": row["evaluated_candidate_count"],
            },
            "evaluated_model_stack",
            "one canonical model card",
            "model",
            ["30"],
            ["model_cards_path"],
            [str(row["model_card_id"])],
            "partial" if model_id == "sdxl_inpainting" else "supported",
            "Coverage status constrains comparisons; partial SDXL evidence is not a full four-model benchmark.",
        )

    # T04: 11 anchors x three core models for the overall nonzero comparison.
    comparison = source_tables["model_comparison_path"]
    quality_rows = comparison.loc[
        comparison["population_id"].astype(str).eq("core_three_model")
        & comparison["analysis_scope"].astype(str).eq("overall")
        & comparison["scope_value"].astype(str).eq("all")
        & comparison["anchor_id"].notna()
    ].sort_values(["anchor_id", "aggregate_rank", "model_id"], kind="stable")
    _require_row_count(quality_rows, 33, "T04 quality anchor selection")
    for row in quality_rows.to_dict(orient="records"):
        add(
            "t04_quality_anchor_summary",
            f"{row['anchor_id']}__{row['model_id']}",
            f"{row['anchor_id']} — {row['model_id']}",
            {
                "metric_name": row["metric_name"],
                "region_id": row["region_id"],
                "restored_mean": row["restored_mean"],
                "directional_utility_mean": row["directional_utility_mean"],
                "aggregate_rank": row["aggregate_rank"],
                "winner_model_id": row["winner_model_id"],
                "eligible_case_count": row["population_case_count"],
                "paired_painting_count": row["paired_painting_count"],
            },
            "core_three_model_overall_nonzero_cases",
            f"{int(row['population_case_count'])} cases; {int(row['paired_painting_count'])} paintings",
            "painting",
            ["21"],
            ["model_comparison_path"],
            [str(row["comparison_row_id"])],
            "supported",
            "Rank and winner apply only to this quality anchor; no universal combined score is implied.",
        )

    # T05: one overall disagreement record per quality anchor.
    disagreement = source_tables["metric_disagreement_path"]
    disagreement_rows = disagreement.loc[
        disagreement["population_id"].astype(str).eq("core_three_model")
        & disagreement["analysis_scope"].astype(str).eq("overall")
        & disagreement["scope_value"].astype(str).eq("all")
    ].sort_values("anchor_id", kind="stable")
    _require_row_count(disagreement_rows, 11, "T05 metric disagreement selection")
    for row in disagreement_rows.to_dict(orient="records"):
        add(
            "t05_metric_disagreement",
            str(row["anchor_id"]),
            str(row["anchor_id"]),
            {
                "model_rank_order": row["model_rank_order"],
                "winner_model_id": row["winner_model_id"],
                "majority_vote_winner_model_id": row["majority_vote_winner_model_id"],
                "agrees_with_majority_vote": row["agrees_with_majority_vote"],
                "loo_winner_stability_fraction": row["loo_winner_stability_fraction"],
            },
            "core_three_model_overall_nonzero_cases",
            f"{int(row['eligible_case_count'])} cases; {int(row['eligible_painting_count'])} paintings",
            "painting",
            ["21"],
            ["metric_disagreement_path"],
            [str(row["disagreement_row_id"])],
            "supported",
            "Metric-specific winners expose agreement or disagreement and are not conservation truth.",
        )

    # T06: realized-damage adverse slope per anchor and core model.
    damage = source_tables["damage_size_analysis_path"]
    damage_rows = damage.loc[
        damage["analysis_kind"].astype(str).eq("damage_trend")
        & damage["exposure_definition"].astype(str).eq("realized_damage_fraction")
        & damage["anchor_id"].notna()
    ].sort_values(["anchor_id", "model_id"], kind="stable")
    _require_row_count(damage_rows, 33, "T06 realized damage trend selection")
    for row in damage_rows.to_dict(orient="records"):
        add(
            "t06_damage_size",
            f"{row['anchor_id']}__{row['model_id']}",
            f"{row['anchor_id']} — {row['model_id']}",
            {
                "estimate_name": row["estimate_name"],
                "adverse_slope": row["estimate"],
                "ci_lower": row["ci_lower"],
                "ci_upper": row["ci_upper"],
                "q_value": row["q_value"],
                "n_paintings": row["n_paintings"],
            },
            "five_painting_damage_size_trajectories",
            f"{int(row['n_paintings'])} paintings",
            str(row["independent_unit"]),
            ["23"],
            ["damage_size_analysis_path"],
            [str(row["analysis_row_id"])],
            str(row["applicability_status"]),
            "Positive adverse slope means quality worsened as realized damage increased; the five-painting scope remains confounded.",
        )

    # T07: overall mask-placement dispersion per anchor and core model.
    robustness = source_tables["mask_robustness_analysis_path"]
    robustness_rows = robustness.loc[
        robustness["analysis_kind"].astype(str).eq("model_dispersion_summary")
        & robustness["scope_type"].astype(str).eq("overall")
        & robustness["scope_value"].astype(str).eq("all_mask_families")
    ].sort_values(["anchor_id", "model_id"], kind="stable")
    _require_row_count(robustness_rows, 33, "T07 mask robustness selection")
    for row in robustness_rows.to_dict(orient="records"):
        add(
            "t07_mask_robustness",
            f"{row['anchor_id']}__{row['model_id']}",
            f"{row['anchor_id']} — {row['model_id']}",
            {
                "estimate_name": row["estimate_name"],
                "dispersion": row["estimate"],
                "ci_lower": row["ci_lower"],
                "ci_upper": row["ci_upper"],
                "n_groups": row["n_groups"],
                "n_paintings": row["n_paintings"],
            },
            "all_mask_families_overall",
            f"{int(row['n_groups'])} robustness groups; {int(row['n_paintings'])} paintings",
            str(row["independent_unit"]),
            ["24"],
            ["mask_robustness_analysis_path"],
            [str(row["analysis_row_id"])],
            str(row["applicability_status"]),
            "Lower median within-group dispersion means greater robustness to the tested mask placements.",
        )

    # T08: overall synthetic-degradation utility per anchor and core model.
    degradation = source_tables["degradation_analysis_path"]
    degradation_rows = degradation.loc[
        degradation["analysis_kind"].astype(str).eq("core_model_scope_summary")
        & degradation["scope_type"].astype(str).eq("overall")
        & degradation["scope_value"].astype(str).eq("all_eligible_cases")
    ].sort_values(["anchor_id", "model_id"], kind="stable")
    _require_row_count(degradation_rows, 33, "T08 degradation selection")
    for row in degradation_rows.to_dict(orient="records"):
        add(
            "t08_synthetic_degradation",
            f"{row['anchor_id']}__{row['model_id']}",
            f"{row['anchor_id']} — {row['model_id']}",
            {
                "estimate_name": row["estimate_name"],
                "directional_utility": row["estimate"],
                "ci_lower": row["ci_lower"],
                "ci_upper": row["ci_upper"],
                "n_cases": row["n_cases"],
                "n_paintings": row["n_paintings"],
            },
            "five_painting_synthetic_degradation_extension",
            f"{int(row['n_cases'])} cases; {int(row['n_paintings'])} paintings",
            str(row["independent_unit"]),
            ["25"],
            ["degradation_analysis_path"],
            [str(row["analysis_row_id"])],
            str(row["applicability_status"]),
            "Directional utility summarizes the tested extension only; painting and category effects are not separable.",
        )

    # T09: four uncertainty coverage/applicability facts and four observed metrics.
    statistical = source_tables["statistical_results_path"]
    uncertainty_coverage_names = [
        "canonical_uncertainty",
        "damage_size_uncertainty",
        "mask_robustness_uncertainty",
        "synthetic_degradation_uncertainty",
    ]
    coverage_rows = statistical.loc[
        statistical["metric_name"].astype(str).isin(uncertainty_coverage_names)
        & statistical["result_kind"].astype(str).isin(
            ["evidence_availability", "applicability_audit"]
        )
    ].sort_values("metric_name", kind="stable")
    _require_row_count(coverage_rows, 4, "T09 uncertainty coverage selection")
    for row in coverage_rows.to_dict(orient="records"):
        add(
            "t09_uncertainty",
            str(row["metric_name"]),
            str(row["metric_name"]),
            {
                "result_kind": row["result_kind"],
                "estimate": row["estimate"],
                "interpretation_status": row["interpretation_status"],
            },
            "uncertainty_applicability",
            "one explicit evidence-availability record",
            str(row["independent_unit"]),
            ["26"],
            ["statistical_results_path"],
            [str(row["result_id"])],
            str(row["applicability_status"]),
            "Uncertainty is reported only for completed repeated-seed populations and is not calibrated confidence.",
        )
    uncertainty = source_tables["damage_size_uncertainty_path"]
    uncertainty_metrics = [
        "pairwise_rgb_mae",
        "pairwise_lpips_distance",
        "pairwise_clip_cosine_distance",
        "pairwise_dinov2_cosine_distance",
    ]
    for metric_name in uncertainty_metrics:
        subset = uncertainty.loc[
            uncertainty["metric_name"].astype(str).eq(metric_name)
            & uncertainty["status"].astype(str).eq("ok")
        ]
        if subset.empty:
            raise ValueError(f"T09 has no rows for uncertainty metric {metric_name}")
        numeric = pd.to_numeric(subset["value"], errors="coerce").dropna()
        if numeric.empty:
            raise ValueError(f"T09 metric {metric_name} has no finite values")
        add(
            "t09_uncertainty",
            f"damage_size__{metric_name}",
            f"Damage-size {metric_name}",
            {
                "median": float(numeric.median()),
                "q25": float(numeric.quantile(0.25)),
                "q75": float(numeric.quantile(0.75)),
                "observation_count": len(numeric),
                "uncertainty_group_count": subset["uncertainty_group_id"].nunique(),
            },
            "damage_size_repeated_seed_groups",
            f"{subset['uncertainty_group_id'].nunique()} groups; {len(numeric)} scalar observations",
            "uncertainty group",
            ["22"],
            ["damage_size_uncertainty_path"],
            [f"all_rows:metric_name={metric_name}"],
            "supported",
            "This is empirical repeated-seed variability, not correctness or calibrated confidence.",
        )

    # T10: 11 omnibus model tests plus 11 per-anchor quality/runtime summaries.
    test_rows = statistical.loc[
        statistical["result_kind"].astype(str).eq("repeated_model_test")
    ].sort_values(["metric_name", "region_id"], kind="stable")
    _require_row_count(test_rows, 11, "T10 repeated-model test selection")
    for row in test_rows.to_dict(orient="records"):
        key = f"omnibus__{row['metric_name']}__{row['region_id']}"
        add(
            "t10_grouped_statistics",
            key,
            f"Omnibus model difference — {row['metric_name']}",
            {
                "test_method": row["test_method"],
                "test_statistic": row["test_statistic"],
                "effect_size_name": row["effect_size_name"],
                "effect_size": row["effect_size"],
                "p_value": row["p_value"],
                "q_value": row["q_value"],
                "n_paintings": row["n_paintings"],
            },
            "all_nonzero_primary_core",
            f"{int(row['n_paintings'])} paintings",
            str(row["independent_unit"]),
            ["26"],
            ["statistical_results_path"],
            [str(row["result_id"])],
            str(row["applicability_status"]),
            "The omnibus result tests model differences for this metric; it does not identify historical correctness.",
        )
    compute_rows = statistical.loc[
        statistical["result_kind"].astype(str).eq("quality_compute_association")
    ]
    grouped_compute = list(compute_rows.groupby("metric_name", sort=True, dropna=False))
    if len(grouped_compute) != 11:
        raise ValueError(f"T10 expected 11 quality/runtime metric groups, observed {len(grouped_compute)}")
    for metric_name, subset in grouped_compute:
        subset = subset.sort_values("model_id", kind="stable")
        associations = {
            str(row["model_id"]): {
                "rho": _native_scalar(row["estimate"]),
                "q_value": _native_scalar(row["q_value"]),
            }
            for row in subset.to_dict(orient="records")
        }
        add(
            "t10_grouped_statistics",
            f"quality_runtime__{metric_name}",
            f"Quality/runtime association — {metric_name}",
            {
                "model_associations": associations,
                "model_count": subset["model_id"].nunique(),
                "n_paintings": int(pd.to_numeric(subset["n_paintings"], errors="coerce").max()),
            },
            "all_nonzero_primary_core",
            f"{int(pd.to_numeric(subset['n_paintings'], errors='coerce').max())} paintings per model",
            "painting",
            ["26"],
            ["statistical_results_path", "ranking_stability_path"],
            subset["result_id"].astype(str).tolist(),
            "supported_operational_association",
            "Runtime association is operational evidence, not a causal quality effect or quality ranking.",
        )

    # T11: 11 independent flags x four models.
    flags = source_tables["trustworthiness_flags_path"]
    flag_groups = list(flags.groupby(["flag_id", "model_id"], sort=True, dropna=False))
    if len(flag_groups) != 44:
        raise ValueError(f"T11 expected 44 flag/model groups, observed {len(flag_groups)}")
    for (flag_id, model_id), subset in flag_groups:
        status_counts = subset["flag_status"].astype(str).value_counts().sort_index().to_dict()
        add(
            "t11_failure_flags",
            f"{flag_id}__{model_id}",
            f"{flag_id} — {model_id}",
            {
                "candidate_count": len(subset),
                "flag_status_counts": status_counts,
                "manual_review_required_count": int(
                    subset["manual_review_required"].astype(str).str.lower().isin(["true", "1", "yes"]).sum()
                ),
                "recommendation_categories": sorted(subset["recommendation_category"].dropna().astype(str).unique()),
            },
            "approved_report_candidate_population",
            f"{len(subset)} candidate-flag records",
            "candidate nested within case and painting",
            ["27"],
            ["failure_assignments_path", "trustworthiness_flags_path"],
            [f"all_rows:flag_id={flag_id};model_id={model_id}"],
            "supported_rule_based_flag",
            "A computational flag is a review trigger, not an expert diagnosis or conservation decision.",
        )

    # T12: one auditable summary per approved ablation scenario.
    ablations = source_tables["ablation_results_path"]
    ablation_groups = list(ablations.groupby("scenario_id", sort=True, dropna=False))
    if len(ablation_groups) != 23:
        raise ValueError(f"T12 expected 23 ablation scenarios, observed {len(ablation_groups)}")
    for scenario_id, subset in ablation_groups:
        add(
            "t12_ablation",
            str(scenario_id),
            str(scenario_id),
            {
                "scenario_family": str(subset["scenario_family"].iloc[0]),
                "result_kinds": sorted(subset["result_kind"].dropna().astype(str).unique()),
                "model_ids": sorted(subset["model_id"].dropna().astype(str).unique()),
                "row_count": len(subset),
                "applicability_states": sorted(subset["applicability_status"].dropna().astype(str).unique()),
            },
            "metric_and_region_policy_ablation",
            f"{len(subset)} scenario result rows",
            "ablation scenario",
            ["28"],
            ["ablation_results_path", "flag_stability_path"],
            [f"all_rows:scenario_id={scenario_id}"],
            "supported",
            "Each scenario is retained separately so policy sensitivity is not hidden by a combined score.",
        )

    # T13: four recommendation categories, two retrieval lanes, and one overall retrieval record.
    for category, subset in explanations.groupby("recommendation_category", sort=True, dropna=False):
        add(
            "t13_explainability",
            f"recommendation__{category}",
            f"Recommendation — {category}",
            {
                "candidate_count": len(subset),
                "painting_count": subset["painting_id"].nunique(),
                "model_count": subset["model_id"].nunique(),
            },
            "complete_explanation_catalog",
            f"{len(subset)} candidates",
            "candidate nested within case and painting",
            ["29"],
            ["explanation_cases_path"],
            [f"all_rows:recommendation_category={category}"],
            "supported",
            "Recommendation categories organize review priority and do not establish restoration correctness.",
        )
    neighbors = source_tables["case_neighbors_path"]
    for lane, subset in neighbors.groupby("lane", sort=True, dropna=False):
        add(
            "t13_explainability",
            f"retrieval_lane__{lane}",
            f"Retrieval lane — {lane}",
            {
                "neighbor_rows": len(subset),
                "query_count": subset["query_candidate_id"].nunique(),
                "feature_models": sorted(subset["feature_model_id"].dropna().astype(str).unique()),
            },
            "selected_case_retrieval",
            f"{len(subset)} neighbor records",
            "query candidate",
            ["29"],
            ["case_neighbors_path"],
            [f"all_rows:lane={lane}"],
            "supported",
            "Nearest neighbors are explanatory comparisons, not proof of restoration quality.",
        )
    add(
        "t13_explainability",
        "retrieval_overall",
        "Retrieval coverage",
        {
            "neighbor_rows": len(neighbors),
            "query_count": neighbors["query_candidate_id"].nunique(),
            "lane_count": neighbors["lane"].nunique(),
        },
        "selected_case_retrieval",
        f"{len(neighbors)} neighbor records",
        "query candidate",
        ["29"],
        ["case_neighbors_path"],
        ["all_rows"],
        "supported",
        "Retrieval coverage is deliberately bounded and illustrative rather than exhaustive evidence of correctness.",
    )

    # T14: four observed-overall rows plus all eight transparent projections.
    compute = source_tables["compute_scalability_path"]
    compute_rows = compute.loc[
        (
            compute["record_type"].astype(str).eq("observed")
            & compute["scenario_id"].astype(str).eq("observed_overall_all")
        )
        | compute["record_type"].astype(str).eq("projection")
    ].sort_values(["record_type", "scenario_id", "model_id"], kind="stable")
    _require_row_count(compute_rows, 12, "T14 compute selection")
    for row in compute_rows.to_dict(orient="records"):
        add(
            "t14_compute_scalability",
            f"{row['record_type']}__{row['scenario_id']}__{row['model_id']}",
            f"{row['model_id']} — {row['scenario_id']}",
            {
                "record_type": row["record_type"],
                "is_executed": row["is_executed"],
                "is_projected": row["is_projected"],
                "candidate_count": row["candidate_count"],
                "runtime_central_seconds": row["runtime_central_seconds"],
                "runtime_lower_seconds": row["runtime_lower_seconds"],
                "runtime_upper_seconds": row["runtime_upper_seconds"],
                "output_storage_bytes": row["output_storage_bytes"],
                "projected_output_storage_bytes": row["projected_output_storage_bytes"],
            },
            str(row["scenario_id"]),
            "one observed or projected model-scenario record",
            "model-scenario",
            ["30"],
            ["compute_scalability_path", "model_cards_path"],
            [str(row["compute_row_id"])],
            str(row["applicability_status"]),
            "Observed records describe one workstation; projected records are linear planning estimates, not executed results or confidence intervals.",
        )

    # T15: the 18 locked limitations and deviations.
    for number, limitation in enumerate(settings["limitations"], start=1):
        add(
            "t15_limitations",
            f"limitation_{number:02d}",
            str(limitation).replace("_", " "),
            {"limitation_id": str(limitation), "must_remain_explicit": True},
            "final_report_interpretation_boundary",
            "one approved limitation or deviation",
            "limitation record",
            ["33"],
            ["evidence_dependency_audit_path", "evidence_coverage_path"],
            [str(limitation)],
            "documented_limitation",
            "This boundary must remain explicit wherever the affected evidence is interpreted.",
        )

    result = pd.DataFrame(records, columns=THESIS_TABLE_COLUMNS)
    expected_total = int(settings["expected_counts"]["thesis_table_rows"])
    _require_row_count(result, expected_total, "Final thesis tables")
    observed_counts = result.groupby("table_id").size().to_dict()
    expected_counts = {
        table_id: int(plan["expected_rows"]) for table_id, plan in table_plan.items()
    }
    if observed_counts != expected_counts:
        raise ValueError(
            f"Final table row allocation differs from contract: {observed_counts}"
        )
    return result


def build_final_latex_tables(
    thesis_tables: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Create one complete LaTeX-ready record for each approved table."""

    settings = _settings(config)
    records: list[dict[str, Any]] = []
    for table_order, item in enumerate(settings["table_plan"], start=1):
        table_id = str(item["table_id"])
        subset = thesis_tables.loc[
            thesis_tables["table_id"].astype(str).eq(table_id)
        ].sort_values("row_order", kind="stable")
        _require_row_count(subset, int(item["expected_rows"]), f"LaTeX {table_id}")
        display_rows = []
        for row in subset.to_dict(orient="records"):
            values = json.loads(str(row["values_json"]))
            compact = "; ".join(
                f"{key}={value}" for key, value in list(values.items())[:5]
            )
            display_rows.append(
                {"Item": row["row_label"], "Scope": row["scope"], "Evidence": compact}
            )
        latex = pd.DataFrame(display_rows).to_latex(index=False, escape=True)
        records.append(
            {
                "latex_table_id": _stable_id("latex", table_id),
                "table_id": table_id,
                "table_order": table_order,
                "section_id": str(item["section_id"]),
                "caption": table_id.replace("_", " ").title(),
                "label": f"tab:{table_id.replace('_', '-')}",
                "column_specification": "lll",
                "latex": latex,
                "source_row_count": len(subset),
                "schema_version": LATEX_TABLE_SCHEMA_VERSION,
                "status": "ok",
                "issue": "",
            }
        )
    return pd.DataFrame(records, columns=LATEX_TABLE_COLUMNS)


def validate_final_tables(
    thesis_tables: pd.DataFrame,
    latex_tables: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Validate final table schemas, counts, identities, and JSON payloads."""

    settings = _settings(config)
    expected = settings["expected_counts"]
    expected_by_table = {
        str(item["table_id"]): int(item["expected_rows"])
        for item in settings["table_plan"]
    }
    observed_by_table = thesis_tables.groupby("table_id").size().to_dict()
    json_errors: list[str] = []
    for column in (
        "values_json",
        "source_notebook_ids_json",
        "source_paths_json",
        "source_row_ids_json",
    ):
        for index, value in thesis_tables[column].items():
            try:
                json.loads(str(value))
            except (TypeError, ValueError, json.JSONDecodeError):
                json_errors.append(f"{index}:{column}")
    checks = [
        _validation_row("final_tables", "thesis column order", list(thesis_tables.columns), list(THESIS_TABLE_COLUMNS), list(thesis_tables.columns) == list(THESIS_TABLE_COLUMNS), "Thesis-table columns differ from schema"),
        _validation_row("final_tables", "latex column order", list(latex_tables.columns), list(LATEX_TABLE_COLUMNS), list(latex_tables.columns) == list(LATEX_TABLE_COLUMNS), "LaTeX-table columns differ from schema"),
        _validation_row("final_tables", "thesis row count", len(thesis_tables), expected["thesis_table_rows"], len(thesis_tables) == int(expected["thesis_table_rows"]), "Unexpected thesis-table row count"),
        _validation_row("final_tables", "latex row count", len(latex_tables), expected["latex_table_rows"], len(latex_tables) == int(expected["latex_table_rows"]), "Unexpected LaTeX-table row count"),
        _validation_row("final_tables", "table row allocation", observed_by_table, expected_by_table, observed_by_table == expected_by_table, "Per-table row counts differ from contract"),
        _validation_row("final_tables", "thesis row identifiers", thesis_tables["table_row_id"].nunique(), len(thesis_tables), thesis_tables["table_row_id"].nunique() == len(thesis_tables), "Thesis row identifiers are not unique"),
        _validation_row("final_tables", "latex identifiers", latex_tables["latex_table_id"].nunique(), len(latex_tables), latex_tables["latex_table_id"].nunique() == len(latex_tables), "LaTeX identifiers are not unique"),
        _validation_row("final_tables", "JSON payloads", json_errors, [], not json_errors, "One or more final-table JSON fields is invalid"),
        _validation_row("final_tables", "thesis schema versions", sorted(thesis_tables["schema_version"].unique()), [THESIS_TABLE_SCHEMA_VERSION], set(thesis_tables["schema_version"]) == {THESIS_TABLE_SCHEMA_VERSION}, "Unexpected thesis-table schema version"),
        _validation_row("final_tables", "latex schema versions", sorted(latex_tables["schema_version"].unique()), [LATEX_TABLE_SCHEMA_VERSION], set(latex_tables["schema_version"]) == {LATEX_TABLE_SCHEMA_VERSION}, "Unexpected LaTeX-table schema version"),
        _validation_row("final_tables", "latex source row coverage", int(pd.to_numeric(latex_tables["source_row_count"], errors="coerce").sum()), expected["thesis_table_rows"], int(pd.to_numeric(latex_tables["source_row_count"], errors="coerce").sum()) == int(expected["thesis_table_rows"]), "LaTeX tables do not cover all thesis rows"),
        _validation_row("final_tables", "latex content", int(latex_tables["latex"].astype(str).str.len().gt(0).sum()), len(latex_tables), latex_tables["latex"].astype(str).str.len().gt(0).all(), "One or more LaTeX tables is empty"),
    ]
    return pd.DataFrame(checks, columns=VALIDATION_COLUMNS)


def generate_final_figures(
    source_tables: Mapping[str, pd.DataFrame],
    thesis_tables: pd.DataFrame,
    selected_case_grids: pd.DataFrame,
    project_root: str | Path,
    config: Mapping[str, Any],
    progress_callback: Any | None = None,
) -> pd.DataFrame:
    """Generate the approved 18 thesis and six publication figures."""

    import matplotlib.pyplot as plt
    import numpy as np

    root = Path(project_root).resolve()
    settings = _settings(config)
    outputs = resolve_final_evaluation_outputs(config, root)
    figure_plan = build_figure_plan(config)
    plan_lookup = figure_plan.set_index("figure_id").to_dict(orient="index")
    model_labels = {
        "lama": "LaMa",
        "opencv_telea": "OpenCV Telea",
        "stable_diffusion_inpainting": "Stable Diffusion",
        "sdxl_inpainting": "SDXL",
    }
    palette = {
        "lama": "#287271",
        "opencv_telea": "#E07A5F",
        "stable_diffusion_inpainting": "#3D5A80",
        "sdxl_inpainting": "#8E6C8A",
    }
    records: list[dict[str, Any]] = []

    for directory in (outputs["thesis_figures_dir"], outputs["publication_figures_dir"]):
        directory.mkdir(parents=True, exist_ok=True)

    def values(table_id: str) -> pd.DataFrame:
        subset = thesis_tables.loc[
            thesis_tables["table_id"].astype(str).eq(table_id)
        ].sort_values("row_order", kind="stable")
        rows = []
        for row in subset.to_dict(orient="records"):
            payload = json.loads(str(row["values_json"]))
            rows.append({**row, **payload})
        return pd.DataFrame(rows)

    def style_axis(axis: Any, title: str, xlabel: str = "", ylabel: str = "") -> None:
        axis.set_title(title, loc="left", fontweight="bold")
        axis.set_xlabel(xlabel)
        axis.set_ylabel(ylabel)
        axis.grid(axis="y", alpha=0.22)

    def save(figure_id: str, figure: Any, tile_count: int = 1) -> None:
        plan = plan_lookup[figure_id]
        path = root / str(plan["relative_path"])
        figure.tight_layout()
        figure.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
        plt.close(figure)
        with Image.open(path) as image:
            width, height = image.size
            image_format = image.format
        records.append(
            {
                "figure_id": figure_id,
                "figure_class": plan["figure_class"],
                "section_id": plan["section_id"],
                "relative_path": path.relative_to(root).as_posix(),
                "width": int(width),
                "height": int(height),
                "format": str(image_format),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_path(path),
                "tile_count": int(tile_count),
            }
        )
        if progress_callback:
            progress_callback(len(records), len(figure_plan), figure_id)

    def grouped_points(
        frame: pd.DataFrame,
        value_column: str,
        title: str,
        xlabel: str,
    ) -> Any:
        anchors = list(dict.fromkeys(frame["anchor_id"].astype(str)))
        figure, axis = plt.subplots(figsize=(11, 7))
        y = np.arange(len(anchors), dtype=float)
        offsets = {"lama": -0.22, "opencv_telea": 0.0, "stable_diffusion_inpainting": 0.22}
        for model_id, offset in offsets.items():
            subset = frame.loc[frame["model_id"].astype(str).eq(model_id)].set_index("anchor_id")
            observed = [float(subset.loc[anchor, value_column]) for anchor in anchors]
            axis.scatter(
                observed,
                y + offset,
                s=48,
                color=palette[model_id],
                label=model_labels[model_id],
                zorder=3,
            )
        axis.axvline(0, color="#555555", linewidth=1, alpha=0.7)
        axis.set_yticks(y, [anchor.replace("_", " ") for anchor in anchors])
        axis.invert_yaxis()
        axis.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.01))
        style_axis(axis, title, xlabel, "Quality anchor")
        return figure

    # F01: report evidence allocation across sections.
    section_plan = build_report_section_plan(config)
    figure, axis = plt.subplots(figsize=(11, 10))
    axis.barh(
        section_plan["title"],
        section_plan["claim_count"],
        color="#3D5A80",
    )
    axis.invert_yaxis()
    style_axis(axis, "Final framework: evidence-backed claims by section", "Claim positions", "")
    save("f01_framework_evidence_map", figure)

    # F02: eight explicit dataset/population counts.
    dataset = values("t02_dataset_design_scope")
    figure, axis = plt.subplots(figsize=(11, 6))
    axis.barh(dataset["row_label"], pd.to_numeric(dataset["count"]), color="#81B29A")
    axis.invert_yaxis()
    style_axis(axis, "Controlled dataset and evidence population", "Count", "")
    save("f02_dataset_experiment_scope", figure)

    # F03: evaluated candidate coverage per model.
    coverage = values("t03_model_coverage")
    figure, axis = plt.subplots(figsize=(9, 5))
    colours = [palette[str(model)] for model in coverage["row_key"]]
    axis.bar(coverage["row_label"], pd.to_numeric(coverage["evaluated_candidate_count"]), color=colours)
    axis.tick_params(axis="x", rotation=18)
    style_axis(axis, "Evaluated candidate coverage by model", "Model", "Candidates")
    save("f03_model_coverage", figure)

    # F04: canonical rank heatmap.
    comparison = source_tables["model_comparison_path"]
    canonical = comparison.loc[
        comparison["population_id"].astype(str).eq("core_three_model")
        & comparison["analysis_scope"].astype(str).eq("overall")
        & comparison["scope_value"].astype(str).eq("all")
        & comparison["anchor_id"].notna()
    ].copy()
    _require_row_count(canonical, 33, "Canonical figure selection")
    rank_matrix = canonical.pivot(index="anchor_id", columns="model_id", values="aggregate_rank")
    rank_matrix = rank_matrix[["lama", "opencv_telea", "stable_diffusion_inpainting"]]
    figure, axis = plt.subplots(figsize=(8, 7))
    image = axis.imshow(rank_matrix.astype(float), cmap="YlGnBu_r", vmin=1, vmax=3, aspect="auto")
    for row_index in range(rank_matrix.shape[0]):
        for column_index in range(rank_matrix.shape[1]):
            axis.text(column_index, row_index, f"{rank_matrix.iloc[row_index, column_index]:.0f}", ha="center", va="center")
    axis.set_xticks(range(rank_matrix.shape[1]), [model_labels[value] for value in rank_matrix.columns], rotation=15)
    axis.set_yticks(range(rank_matrix.shape[0]), [value.replace("_", " ") for value in rank_matrix.index])
    axis.set_title("Canonical quality-anchor ranks (1 = better)", loc="left", fontweight="bold")
    figure.colorbar(image, ax=axis, label="Rank")
    save("f04_canonical_model_comparison", figure)

    # F05: winner count plus LOO stability.
    disagreement = values("t05_metric_disagreement")
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    winner_counts = disagreement["winner_model_id"].value_counts()
    axes[0].bar([model_labels.get(value, value) for value in winner_counts.index], winner_counts.values, color=[palette.get(value, "#777777") for value in winner_counts.index])
    style_axis(axes[0], "Metric-specific winners", "Model", "Quality anchors")
    axes[1].barh(disagreement["row_label"], pd.to_numeric(disagreement["loo_winner_stability_fraction"]), color="#F2CC8F")
    axes[1].set_xlim(0, 1.05)
    axes[1].invert_yaxis()
    style_axis(axes[1], "Leave-one-painting-out winner stability", "Fraction", "")
    save("f05_metric_disagreement", figure, 2)

    damage = source_tables["damage_size_analysis_path"]
    damage = damage.loc[
        damage["analysis_kind"].astype(str).eq("damage_trend")
        & damage["exposure_definition"].astype(str).eq("realized_damage_fraction")
        & damage["anchor_id"].notna()
    ].copy()
    damage["adverse_slope"] = pd.to_numeric(damage["estimate"], errors="coerce")
    _require_row_count(damage, 33, "Damage-size figure selection")

    robustness = source_tables["mask_robustness_analysis_path"]
    robustness = robustness.loc[
        robustness["analysis_kind"].astype(str).eq("model_dispersion_summary")
        & robustness["scope_type"].astype(str).eq("overall")
        & robustness["scope_value"].astype(str).eq("all_mask_families")
    ].copy()
    robustness["dispersion"] = pd.to_numeric(robustness["estimate"], errors="coerce")
    _require_row_count(robustness, 33, "Mask-robustness figure selection")

    degradation = source_tables["degradation_analysis_path"]
    degradation = degradation.loc[
        degradation["analysis_kind"].astype(str).eq("core_model_scope_summary")
        & degradation["scope_type"].astype(str).eq("overall")
        & degradation["scope_value"].astype(str).eq("all_eligible_cases")
    ].copy()
    degradation["directional_utility"] = pd.to_numeric(degradation["estimate"], errors="coerce")
    _require_row_count(degradation, 33, "Synthetic-degradation figure selection")

    save("f06_damage_size_sensitivity", grouped_points(damage, "adverse_slope", "Damage-size sensitivity by model and anchor", "Adverse slope per 10 percentage points"))
    save("f07_mask_robustness", grouped_points(robustness, "dispersion", "Mask-placement robustness", "Median within-group dispersion (lower is more robust)"))
    save("f08_synthetic_degradation", grouped_points(degradation, "directional_utility", "Synthetic-degradation directional utility", "Directional utility"))

    # F09: omnibus grouped effect sizes.
    grouped = values("t10_grouped_statistics")
    omnibus = grouped.loc[grouped["row_key"].astype(str).str.startswith("omnibus__")]
    figure, axis = plt.subplots(figsize=(10, 6))
    axis.barh(omnibus["row_label"].str.replace("Omnibus model difference — ", "", regex=False), pd.to_numeric(omnibus["effect_size"]), color="#287271")
    axis.invert_yaxis()
    style_axis(axis, "Grouped model differences across 50 paintings", "Kendall's W", "")
    save("f09_grouped_effects", figure)

    # F10: mean metric-pair correlation matrix across core models.
    correlations = source_tables["metric_correlations_path"]
    pairs = correlations.loc[
        correlations["correlation_kind"].astype(str).eq("metric_pair_correlation")
        & correlations["status"].astype(str).eq("ok")
    ].copy()
    pairs["left"] = pairs["left_metric_name"].astype(str)
    pairs["right"] = pairs["right_metric_name"].astype(str)
    pair_means = pairs.groupby(["left", "right"])["correlation"].mean()
    metric_names = sorted(set(pairs["left"]) | set(pairs["right"]))
    matrix = pd.DataFrame(np.eye(len(metric_names)), index=metric_names, columns=metric_names)
    for (left, right), correlation in pair_means.items():
        matrix.loc[left, right] = float(correlation)
        matrix.loc[right, left] = float(correlation)
    figure, axis = plt.subplots(figsize=(10, 8))
    image = axis.imshow(matrix, cmap="coolwarm", vmin=-1, vmax=1, aspect="auto")
    axis.set_xticks(range(len(metric_names)), metric_names, rotation=75, ha="right", fontsize=8)
    axis.set_yticks(range(len(metric_names)), metric_names, fontsize=8)
    axis.set_title("Mean metric-pair correlations across core models", loc="left", fontweight="bold")
    figure.colorbar(image, ax=axis, label="Correlation")
    save("f10_metric_correlations", figure)

    # F11: ranking retention by sensitivity analysis.
    rankings = source_tables["ranking_stability_path"]
    ranking_summary = rankings.groupby(["ranking_kind", "model_id"])["winner_retained"].mean().unstack(fill_value=0)
    figure, axis = plt.subplots(figsize=(10, 6))
    ranking_summary.rename(columns=model_labels).plot(kind="bar", ax=axis, color=[palette.get(value, "#777777") for value in ranking_summary.columns])
    axis.tick_params(axis="x", rotation=25)
    axis.set_ylim(0, 1.05)
    style_axis(axis, "Winner retention under ranking sensitivity checks", "Sensitivity analysis", "Retention fraction")
    save("f11_ranking_stability", figure)

    # F12: damage-size uncertainty distributions.
    uncertainty = source_tables["damage_size_uncertainty_path"]
    uncertainty_names = ["pairwise_rgb_mae", "pairwise_lpips_distance", "pairwise_clip_cosine_distance", "pairwise_dinov2_cosine_distance"]
    uncertainty_data = [pd.to_numeric(uncertainty.loc[uncertainty["metric_name"].eq(name), "value"], errors="coerce").dropna() for name in uncertainty_names]
    figure, axis = plt.subplots(figsize=(10, 6))
    axis.boxplot(uncertainty_data, showfliers=False)
    axis.set_xticks(
        range(1, len(uncertainty_names) + 1),
        [value.replace("pairwise_", "").replace("_distance", "") for value in uncertainty_names],
    )
    style_axis(axis, "Damage-size repeated-seed uncertainty", "Metric", "Observed variability")
    save("f12_uncertainty_summary", figure)

    # F13: deterministic montage of canonical uncertainty panels.
    panel_root = root / settings["inputs"]["canonical_uncertainty_panels_dir"]
    panel_paths = sorted(panel_root.glob("*.png"))[:4]
    if not panel_paths:
        raise FileNotFoundError(f"No canonical uncertainty panels found in {panel_root}")
    figure, axes = plt.subplots(1, len(panel_paths), figsize=(4 * len(panel_paths), 4.5))
    axes = np.atleast_1d(axes)
    for axis, path in zip(axes, panel_paths, strict=True):
        axis.imshow(plt.imread(path))
        axis.set_title(path.stem.replace("_", " "), fontsize=9)
        axis.axis("off")
    figure.suptitle("Selected spatial uncertainty explanations", fontweight="bold")
    save("f13_spatial_uncertainty", figure, len(panel_paths))

    # F14: triggered flag rate by model and flag.
    flags = source_tables["trustworthiness_flags_path"].copy()
    flags = flags.loc[
        flags["flag_status"].astype(str).isin(["triggered", "not_triggered"])
    ].copy()
    if flags.empty:
        raise ValueError("No applicable triggered/not-triggered trustworthiness flags were found")
    flags["triggered"] = flags["flag_status"].astype(str).eq("triggered").astype(float)
    flag_matrix = flags.groupby(["flag_id", "model_id"])["triggered"].mean().unstack(fill_value=0)
    model_order = [value for value in ["lama", "opencv_telea", "stable_diffusion_inpainting", "sdxl_inpainting"] if value in flag_matrix.columns]
    flag_matrix = flag_matrix[model_order]
    figure, axis = plt.subplots(figsize=(8, 7))
    image = axis.imshow(flag_matrix, cmap="OrRd", vmin=0, vmax=max(0.01, float(flag_matrix.to_numpy().max())), aspect="auto")
    axis.set_xticks(range(len(model_order)), [model_labels[value] for value in model_order], rotation=18)
    axis.set_yticks(range(len(flag_matrix)), [value.replace("_", " ") for value in flag_matrix.index])
    axis.set_title("Triggered trustworthiness-flag rates", loc="left", fontweight="bold")
    figure.colorbar(image, ax=axis, label="Triggered fraction")
    save("f14_failure_taxonomy", figure)

    # F15: flag-state agreement by ablation scenario.
    stability = source_tables["flag_stability_path"]
    scenario_agreement = stability.groupby("scenario_id")["flag_state_agreement_fraction"].mean().sort_values()
    figure, axis = plt.subplots(figsize=(11, 7))
    axis.barh(scenario_agreement.index.str.replace("_", " "), scenario_agreement.values, color="#8E6C8A")
    axis.set_xlim(0, 1.02)
    style_axis(axis, "Flag-state agreement under policy ablations", "Agreement fraction", "")
    save("f15_ablation", figure)

    # F16: explanation recommendation coverage.
    explanation = values("t13_explainability")
    recommendations = explanation.loc[explanation["row_key"].astype(str).str.startswith("recommendation__")]
    figure, axis = plt.subplots(figsize=(10, 5))
    axis.barh(recommendations["row_label"].str.replace("Recommendation — ", "", regex=False), pd.to_numeric(recommendations["candidate_count"]), color="#E07A5F")
    axis.invert_yaxis()
    style_axis(axis, "Candidate review recommendations", "Candidates", "")
    save("f16_explainability", figure)

    # F17: observed quality rank versus compute time.
    baseline = source_tables["ranking_stability_path"].loc[lambda frame: frame["ranking_kind"].astype(str).eq("baseline_rank")]
    cards = source_tables["model_cards_path"]
    quality_compute = baseline.merge(cards[["model_id", "display_name", "mean_runtime_seconds", "evaluated_candidate_count"]], on="model_id", how="left")
    figure, axis = plt.subplots(figsize=(8, 5))
    for row in quality_compute.to_dict(orient="records"):
        axis.scatter(float(row["mean_runtime_seconds"]), float(row["baseline_rank"]), s=90, color=palette[str(row["model_id"])])
        axis.annotate(str(row["display_name"]), (float(row["mean_runtime_seconds"]), float(row["baseline_rank"])), xytext=(6, 5), textcoords="offset points")
    axis.invert_yaxis()
    style_axis(axis, "Observed quality rank versus mean runtime", "Mean runtime per candidate (seconds)", "Family-balanced rank")
    save("f17_quality_compute", figure)

    # F18: projected central runtime by scenario and model.
    compute = source_tables["compute_scalability_path"]
    projected = compute.loc[compute["record_type"].astype(str).eq("projection")].copy()
    projection_matrix = projected.pivot(index="scenario_id", columns="model_id", values="runtime_central_seconds")
    figure, axis = plt.subplots(figsize=(10, 5))
    projection_matrix.rename(columns=model_labels).plot(kind="bar", ax=axis, color=[palette.get(value, "#777777") for value in projection_matrix.columns])
    axis.set_yscale("log")
    axis.tick_params(axis="x", rotation=15)
    style_axis(axis, "Transparent linear runtime projections", "Projection scenario", "Central runtime (seconds, log scale)")
    save("f18_scalability", figure)

    # Publication P01: compact canonical winner/rank summary.
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    winner_counts = canonical.drop_duplicates("anchor_id")["winner_model_id"].value_counts()
    axes[0].bar([model_labels.get(value, value) for value in winner_counts.index], winner_counts.values, color=[palette.get(value, "#777777") for value in winner_counts.index])
    style_axis(axes[0], "Quality-anchor wins", "Model", "Anchors")
    mean_ranks = canonical.groupby("model_id")["aggregate_rank"].mean().sort_values()
    axes[1].bar([model_labels.get(value, value) for value in mean_ranks.index], mean_ranks.values, color=[palette.get(value, "#777777") for value in mean_ranks.index])
    axes[1].tick_params(axis="x", rotation=15)
    style_axis(axes[1], "Mean anchor rank", "Model", "Rank (lower is better)")
    save("p01_benchmark_summary", figure, 2)

    # Publication P02: stress-test summary from the three extension tables.
    figure, axes = plt.subplots(1, 3, figsize=(15, 5))
    for axis, table_id, column, title in [
        (axes[0], "t06_damage_size", "adverse_slope", "Damage size"),
        (axes[1], "t07_mask_robustness", "dispersion", "Mask placement"),
        (axes[2], "t08_synthetic_degradation", "directional_utility", "Synthetic degradation"),
    ]:
        frame = {
            "t06_damage_size": damage,
            "t07_mask_robustness": robustness,
            "t08_synthetic_degradation": degradation,
        }[table_id]
        summary = frame.groupby("model_id")[column].median().sort_values()
        axis.bar([model_labels.get(value, value) for value in summary.index], summary.values, color=[palette.get(value, "#777777") for value in summary.index])
        axis.tick_params(axis="x", rotation=25)
        style_axis(axis, title, "", f"Median {column.replace('_', ' ')}")
    save("p02_stress_test_summary", figure, 3)

    # Publication P03: uncertainty distribution plus one spatial panel.
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].boxplot(uncertainty_data, showfliers=False)
    axes[0].set_xticks(range(1, 5), ["RGB", "LPIPS", "CLIP", "DINO"])
    style_axis(axes[0], "Repeated-seed variability", "Metric", "Observed value")
    axes[1].imshow(plt.imread(panel_paths[0]))
    axes[1].axis("off")
    axes[1].set_title("Spatial explanation example", loc="left", fontweight="bold")
    save("p03_uncertainty_spatial", figure, 2)

    # Publication P04: flag prevalence and ablation agreement.
    figure, axes = plt.subplots(1, 2, figsize=(13, 5))
    overall_flag = flags.groupby("flag_id")["triggered"].mean().sort_values()
    axes[0].barh(overall_flag.index.str.replace("_", " "), overall_flag.values, color="#E07A5F")
    style_axis(axes[0], "Triggered flag prevalence", "Fraction", "")
    axes[1].boxplot(stability["flag_state_agreement_fraction"].dropna(), vert=True)
    axes[1].set_xticks([1], ["All scenarios"])
    axes[1].set_ylim(0, 1.02)
    style_axis(axes[1], "Ablation flag agreement", "", "Agreement fraction")
    save("p04_trustworthiness_ablation", figure, 2)

    # Publication P05: recommendation balance plus one auditable case grid.
    case_path = root / str(selected_case_grids.sort_values("visual_order", kind="stable").iloc[0]["grid_path"])
    figure, axes = plt.subplots(1, 2, figsize=(13, 5))
    axes[0].barh(recommendations["row_label"].str.replace("Recommendation — ", "", regex=False), pd.to_numeric(recommendations["candidate_count"]), color="#81B29A")
    axes[0].invert_yaxis()
    style_axis(axes[0], "Review recommendation coverage", "Candidates", "")
    axes[1].imshow(plt.imread(case_path))
    axes[1].axis("off")
    axes[1].set_title("Auditable representative case", loc="left", fontweight="bold")
    save("p05_explainability", figure, 2)

    # Publication P06: quality/runtime view with candidate coverage encoded by size.
    figure, axis = plt.subplots(figsize=(8, 5))
    for row in quality_compute.to_dict(orient="records"):
        size = 45 + 0.08 * float(row["evaluated_candidate_count"])
        axis.scatter(float(row["mean_runtime_seconds"]), float(row["baseline_rank"]), s=size, alpha=0.8, color=palette[str(row["model_id"])], label=str(row["display_name"]))
    axis.invert_yaxis()
    axis.legend(frameon=False)
    style_axis(axis, "Quality, compute, and evaluated coverage", "Mean runtime per candidate (seconds)", "Family-balanced rank")
    save("p06_quality_compute", figure)

    result = pd.DataFrame(records)
    _require_row_count(result, int(settings["expected_counts"]["persisted_figures"]), "Final figure manifest")
    return result.sort_values(["figure_class", "figure_id"], kind="stable").reset_index(drop=True)


def validate_final_figures(
    figure_manifest: pd.DataFrame,
    project_root: str | Path,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Validate final figure count, identity, files, formats, and directory scope."""

    root = Path(project_root).resolve()
    settings = _settings(config)
    expected = settings["expected_counts"]
    plan = build_figure_plan(config)
    outputs = resolve_final_evaluation_outputs(config, root)
    expected_ids = set(plan["figure_id"].astype(str))
    observed_ids = set(figure_manifest["figure_id"].astype(str))
    missing_files = [
        value for value in figure_manifest["relative_path"].astype(str) if not (root / value).is_file()
    ]
    invalid_images = figure_manifest.loc[
        ~figure_manifest["format"].astype(str).eq("PNG")
        | pd.to_numeric(figure_manifest["width"], errors="coerce").le(0)
        | pd.to_numeric(figure_manifest["height"], errors="coerce").le(0),
        "figure_id",
    ].astype(str).tolist()
    actual_paths = {
        path.relative_to(root).as_posix()
        for directory in (outputs["thesis_figures_dir"], outputs["publication_figures_dir"])
        for path in directory.glob("*.png")
        if path.is_file()
    }
    expected_paths = set(figure_manifest["relative_path"].astype(str))
    checks = [
        _validation_row("final_figures", "figure count", len(figure_manifest), expected["persisted_figures"], len(figure_manifest) == int(expected["persisted_figures"]), "Unexpected final figure count"),
        _validation_row("final_figures", "thesis figure count", int(figure_manifest["figure_class"].eq("thesis").sum()), expected["thesis_figures"], int(figure_manifest["figure_class"].eq("thesis").sum()) == int(expected["thesis_figures"]), "Unexpected thesis figure count"),
        _validation_row("final_figures", "publication figure count", int(figure_manifest["figure_class"].eq("publication").sum()), expected["publication_figures"], int(figure_manifest["figure_class"].eq("publication").sum()) == int(expected["publication_figures"]), "Unexpected publication figure count"),
        _validation_row("final_figures", "figure identifiers", sorted(observed_ids), sorted(expected_ids), observed_ids == expected_ids, "Figure identifiers differ from the approved plan"),
        _validation_row("final_figures", "figure identifier uniqueness", figure_manifest["figure_id"].nunique(), len(figure_manifest), figure_manifest["figure_id"].nunique() == len(figure_manifest), "Figure identifiers are not unique"),
        _validation_row("final_figures", "figure files", missing_files, [], not missing_files, "One or more final figures is missing"),
        _validation_row("final_figures", "PNG dimensions", invalid_images, [], not invalid_images, "One or more figure has invalid format or dimensions"),
        _validation_row("final_figures", "figure directory file set", sorted(actual_paths), sorted(expected_paths), actual_paths == expected_paths, "Figure directories contain missing or stale PNG files"),
    ]
    return pd.DataFrame(checks, columns=VALIDATION_COLUMNS)


def image_to_data_uri(
    path: str | Path,
    max_dimension: int = 1000,
    photographic_quality: int = 82,
) -> str:
    """Create a bounded browser-safe data URI without persisting a thumbnail."""

    with Image.open(path) as source:
        image = source.copy()
    image.thumbnail((int(max_dimension), int(max_dimension)), Image.Resampling.LANCZOS)
    has_alpha = image.mode in {"RGBA", "LA"} or "transparency" in image.info
    buffer = io.BytesIO()
    if has_alpha:
        image.convert("RGBA").save(buffer, format="PNG", optimize=True)
        mime = "image/png"
    else:
        image.convert("RGB").save(
            buffer,
            format="JPEG",
            quality=int(photographic_quality),
            optimize=True,
        )
        mime = "image/jpeg"
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def visual_html(
    data_uri: str,
    alt: str,
    caption: str,
    visual_id: str,
    tile_count: int = 1,
) -> str:
    """Return one accessible embedded figure with auditable metadata."""

    return (
        f'<figure class="report-visual" data-visual-id="{html.escape(visual_id)}" '
        f'data-tile-count="{int(tile_count)}">'
        f'<img src="{data_uri}" alt="{html.escape(alt)}" loading="lazy">'
        f'<figcaption>{html.escape(caption)}</figcaption>'
        "</figure>"
    )


def build_final_report_sections(
    source_tables: Mapping[str, pd.DataFrame],
    thesis_tables: pd.DataFrame,
    figure_manifest: pd.DataFrame,
    selected_case_grids: pd.DataFrame,
    project_root: str | Path,
    config: Mapping[str, Any],
    progress_callback: Any | None = None,
) -> tuple[list[dict[str, str]], pd.DataFrame]:
    """Build the approved 19-section report with embedded auditable visuals."""

    root = Path(project_root).resolve()
    settings = _settings(config)
    report = settings["report"]
    image_cache: dict[Path, str] = {}
    visual_records: list[dict[str, Any]] = []
    visual_markup: dict[str, list[str]] = {
        str(item["section_id"]): [] for item in report["sections"]
    }

    def embed(
        section_id: str,
        visual_id: str,
        path: Path,
        caption: str,
        tile_count: int,
        role: str,
    ) -> None:
        resolved = path.resolve()
        if root not in resolved.parents:
            raise ValueError(f"Report visual escapes repository root: {resolved}")
        if not resolved.is_file():
            raise FileNotFoundError(f"Report visual is missing: {resolved}")
        if resolved not in image_cache:
            image_cache[resolved] = image_to_data_uri(
                resolved,
                max_dimension=int(report["image_max_dimension"]),
                photographic_quality=int(report["photographic_quality"]),
            )
        visual_markup[section_id].append(
            visual_html(
                image_cache[resolved],
                caption,
                caption,
                visual_id,
                tile_count,
            )
        )
        visual_records.append(
            {
                "visual_id": visual_id,
                "section_id": section_id,
                "visual_role": role,
                "source_path": resolved.relative_to(root).as_posix(),
                "tile_count": int(tile_count),
            }
        )
        if progress_callback:
            progress_callback(len(visual_records), visual_id)

    # All 24 persisted figures retain their configured section placement.
    for row in figure_manifest.sort_values(
        ["figure_class", "figure_id"], kind="stable"
    ).to_dict(orient="records"):
        embed(
            str(row["section_id"]),
            f"report__{row['figure_id']}",
            root / str(row["relative_path"]),
            str(row["figure_id"]).replace("_", " ").title(),
            int(row["tile_count"]),
            f"persisted_{row['figure_class']}_figure",
        )

    # Twelve approved case grids form the auditable visual atlas.
    for row in selected_case_grids.sort_values(
        "visual_order", kind="stable"
    ).to_dict(orient="records"):
        embed(
            "case-painting-atlas",
            f"atlas__{row['visual_order']:02d}",
            root / str(row["grid_path"]),
            f"Case {row['case_id']} ({row['painting_id']}): {row['selection_lane']}",
            6,
            "selected_case_grid",
        )

    def first_pngs(input_key: str, count: int) -> list[Path]:
        directory = root / str(settings["inputs"][input_key])
        paths = sorted(directory.glob("*.png"))[: int(count)]
        if len(paths) != int(count):
            raise ValueError(
                f"{input_key} supplied {len(paths)} PNGs; expected {count}"
            )
        return paths

    for index, path in enumerate(
        first_pngs("canonical_uncertainty_panels_dir", 6), start=1
    ):
        embed(
            "diffusion-uncertainty",
            f"uncertainty_panel__{index:02d}",
            path,
            f"Spatial uncertainty explanation {index}: {path.stem.replace('_', ' ')}",
            15,
            "canonical_uncertainty_panel",
        )

    for index, path in enumerate(
        first_pngs("counterfactual_panels_dir", 7), start=1
    ):
        embed(
            "explainability",
            f"counterfactual__{index:02d}",
            path,
            f"Counterfactual explanation {index}: {path.stem.replace('_', ' ')}",
            3,
            "counterfactual_panel",
        )

    for index, path in enumerate(
        first_pngs("retrieval_panels_dir", 5), start=1
    ):
        embed(
            "explainability",
            f"retrieval__{index:02d}",
            path,
            f"Case-retrieval example {index}: {path.stem.replace('_', ' ')}",
            6,
            "retrieval_panel",
        )

    # Ten individual outputs keep the model-comparison narrative visually grounded.
    explanations = source_tables["explanation_cases_path"].copy()
    explanations = explanations.loc[
        explanations["restored_path"].astype(str).str.len().gt(0)
    ].sort_values(["model_id", "painting_id", "candidate_id"], kind="stable")
    restoration_parts = []
    for model_id, quota in {
        "lama": 3,
        "opencv_telea": 3,
        "stable_diffusion_inpainting": 3,
        "sdxl_inpainting": 1,
    }.items():
        restoration_parts.append(
            explanations.loc[explanations["model_id"].astype(str).eq(model_id)]
            .drop_duplicates("painting_id", keep="first")
            .head(quota)
        )
    restoration_rows = pd.concat(restoration_parts, ignore_index=True)
    if len(restoration_rows) != 10:
        raise ValueError("Could not select ten distinct restoration examples")
    for index, row in enumerate(restoration_rows.to_dict(orient="records"), start=1):
        embed(
            "canonical-comparison",
            f"restoration__{index:02d}",
            root / str(row["restored_path"]),
            f"Restoration example {index}: {row['model_id']}, {row['painting_id']}",
            1,
            "individual_restoration",
        )

    # Four already-approved grids are reused beside failure discussions.
    for index, row in enumerate(
        selected_case_grids.sort_values("visual_order", kind="stable")
        .head(4)
        .to_dict(orient="records"),
        start=1,
    ):
        embed(
            "failure-flags",
            f"failure_context__{index:02d}",
            root / str(row["grid_path"]),
            f"Flag-review context {index}: {row['case_id']} ({row['selection_lane']})",
            6,
            "failure_review_context",
        )

    def values(table_id: str) -> pd.DataFrame:
        rows = []
        subset = thesis_tables.loc[
            thesis_tables["table_id"].astype(str).eq(table_id)
        ].sort_values("row_order", kind="stable")
        for row in subset.to_dict(orient="records"):
            rows.append({"Result": row["row_label"], **json.loads(str(row["values_json"]))})
        return pd.DataFrame(rows)

    def table_html(table_id: str, limit: int = 8) -> str:
        frame = values(table_id)
        shown = frame.head(int(limit)).copy()
        shown.columns = [str(value).replace("_", " ").title() for value in shown.columns]
        note = (
            f"<p class=\"table-note\">Showing {len(shown)} of {len(frame)} canonical rows; "
            "the complete table is retained in <code>data/thesis_tables.csv</code>.</p>"
        )
        return (
            f'<div class="table-wrap" data-table-id="{html.escape(table_id)}">'
            f"{shown.to_html(index=False, border=0, escape=True)}{note}</div>"
        )

    canonical = source_tables["model_comparison_path"]
    canonical = canonical.loc[
        canonical["population_id"].astype(str).eq("core_three_model")
        & canonical["analysis_scope"].astype(str).eq("overall")
        & canonical["scope_value"].astype(str).eq("all")
        & canonical["anchor_id"].notna()
    ]
    winner_counts = canonical.drop_duplicates("anchor_id")["winner_model_id"].value_counts()
    leader = str(winner_counts.index[0])
    leader_wins = int(winner_counts.iloc[0])
    model_name = {
        "lama": "LaMa",
        "opencv_telea": "OpenCV Telea",
        "stable_diffusion_inpainting": "Stable Diffusion",
        "sdxl_inpainting": "SDXL",
    }
    leader_label = model_name.get(leader, leader)

    claims: dict[str, list[str]] = {
        "executive-findings": [
            f"{leader_label} ranks first on {leader_wins} of 11 canonical quality anchors. It is the better overall core-model result under this metric set, not a universal conservation verdict.",
            "Damage size, mask placement, and degradation family change model behaviour. A single average therefore hides conditions where restoration becomes worse.",
            "Uncertainty, metric disagreement, and failure flags identify candidates needing human review; none of them establishes historical correctness.",
        ],
        "research-questions": [
            "The evaluation answers model comparison with complementary metric families rather than one combined score.",
            "The approved extensions test conditional behaviour, uncertainty, explanation, and practical reporting beyond the original proposal scope.",
        ],
        "dataset-design": [
            "The controlled design contains 50 paintings, 525 cases, and 1,785 approved candidates, enabling paired computational comparisons.",
            "Artificial damage and incomplete style metadata limit external validity; the dataset does not represent real physical treatment outcomes.",
        ],
        "methods-coverage": [
            "Telea, LaMa, and Stable Diffusion have complete core coverage and can be compared directly on the approved population.",
            "SDXL has ten completed candidates only, so four-model conclusions are inconclusive and SDXL remains a feasibility result.",
        ],
        "evaluation-framework": [
            "Eleven quality anchors cover classical, perceptual, feature, texture, colour, seam, semantic, spatial, and structural evidence.",
            "Metric direction and compatible image region are retained for every claim, preventing higher-is-better and lower-is-better results from being mixed blindly.",
            "No universal combined quality or trust score is reported because its weights cannot be justified from the available evidence.",
        ],
        "canonical-comparison": [
            f"{leader_label} wins {leader_wins} quality anchors and has the lowest mean anchor rank among the three fully evaluated models.",
            "OpenCV Telea wins the remaining structural anchor, showing that a classical method can still be better for a specific criterion.",
            "Stable Diffusion is competitive on several perceptual and feature anchors but is worse on the aggregate rank across the approved anchors.",
            "Metric-specific disagreement means model choice should follow the restoration objective rather than a universal winner label.",
        ],
        "damage-size": [
            "Several adverse slopes increase as realized damage grows, so larger missing regions generally make restoration worse.",
            "The model ordering changes by quality anchor; low sensitivity on one metric does not guarantee low sensitivity on another.",
            "Only five paintings support this extension, so category and painting effects remain confounded.",
        ],
        "mask-robustness": [
            "Lower within-group dispersion indicates better robustness to the tested mask placements.",
            "Robustness varies by metric and model, so stability cannot be inferred from canonical quality alone.",
            "These results cover the designed mask families and do not establish robustness to arbitrary user masks.",
        ],
        "synthetic-degradation": [
            "Directional utility differs across degradation families, meaning one model is not consistently better for every synthetic defect.",
            "Thin scratches and broad stains create different failure patterns and should not be collapsed into one damage label.",
            "The five-painting extension supports controlled comparison but remains too small for general category claims.",
        ],
        "grouped-statistics": [
            "Painting-level grouped tests preserve the painting as the independent unit instead of treating correlated candidates as independent.",
            "Metric correlations reveal overlap but also disagreement between evidence families.",
            "Leave-one-painting-out checks show which winners remain stable and which conclusions depend on individual paintings.",
            "Statistical significance is interpreted with effect size, multiplicity control, and scope rather than as automatic practical importance.",
        ],
        "diffusion-uncertainty": [
            "Stable Diffusion repeated seeds provide 165 supported uncertainty groups across canonical and damage-size experiments.",
            "Higher seed variability marks less stable generation, but lower variability does not prove a correct restoration.",
            "Spatial maps show where variability, error, colour drift, texture change, and seam evidence occur.",
            "Telea and LaMa are deterministic; their analyses use robustness rather than artificial diffusion uncertainty.",
        ],
        "failure-flags": [
            "Flags convert metric evidence into transparent review triggers rather than a hidden combined score.",
            "A triggered flag means the candidate needs attention; it does not prove that a conservator would reject it.",
            "Insufficient evidence and manual-review states are retained instead of being silently counted as successful restoration.",
        ],
        "policy-ablation": [
            "Ablations show whether rankings and flags survive reasonable metric and region-policy changes.",
            "High agreement supports a more stable conclusion; low agreement means the result is policy-sensitive and less trustworthy.",
            "Context-prompt candidates p01-p04 lack complete downstream flag coverage, which remains an explicit limitation.",
        ],
        "explainability": [
            "All 1,785 approved candidates remain catalogued with evidence and path references.",
            "Counterfactual panels explain how model, seed, damage size, or evidence-family removal changes the assessment.",
            "Nearest-case retrieval supplies comparable examples for human review but similarity is not restoration correctness.",
        ],
        "compute-scalability": [
            "Observed runtime and memory measurements describe the evaluated workstation and make practical model costs visible.",
            "Scaling values are transparent linear projections, not executed benchmarks or confidence intervals.",
        ],
        "case-painting-atlas": [
            "The 12 selected grids provide detailed examples while Notebook 32 retains complete reports for all applicable cases and paintings.",
        ],
        "limitations": [
            "The 18 declared limitations bound every conclusion and prevent computational evidence from being presented as conservation approval.",
        ],
        "research-question-answers": [
            f"RQ1: {leader_label} is better overall on the approved canonical anchors, but metric disagreement rules out a universal best method.",
            "RQ2-RQ3: condition-specific tests, uncertainty maps, flags, and retrieval improve auditability, while historical trustworthiness remains inconclusive without expert evidence.",
        ],
        "provenance": [],
    }

    questions = {
        "executive-findings": "What are the most defensible thesis-wide conclusions?",
        "research-questions": "Which research questions can the completed evidence answer?",
        "dataset-design": "What population supports the reported conclusions?",
        "methods-coverage": "Which model comparisons are complete and which remain partial?",
        "evaluation-framework": "How is restoration quality evaluated without hiding disagreement?",
        "canonical-comparison": "Which core model performs better under each approved quality anchor?",
        "damage-size": "How does restoration behaviour change as damage becomes larger?",
        "mask-robustness": "How sensitive are models to plausible changes in mask placement?",
        "synthetic-degradation": "Do restoration methods respond consistently across damage families?",
        "grouped-statistics": "Which differences remain after painting-level grouping and sensitivity checks?",
        "diffusion-uncertainty": "Where and how strongly do repeated diffusion candidates vary?",
        "failure-flags": "Which candidates require closer human review, and why?",
        "policy-ablation": "Do conclusions survive reasonable evaluation-policy changes?",
        "explainability": "Can a reviewer trace recommendations to cases and evidence?",
        "compute-scalability": "What practical cost and scaling limits accompany each model?",
        "case-painting-atlas": "What do representative cases look like across the evidence population?",
        "limitations": "What must not be inferred from this evaluation?",
        "research-question-answers": "What are the direct, scoped answers to the thesis questions?",
        "provenance": "How can the final synthesis be reproduced and audited?",
    }

    conclusions = {
        key: values[-1] if values else "The report retains complete provenance through canonical tables, manifests, and checks."
        for key, values in claims.items()
    }
    table_ids_by_section: dict[str, list[str]] = {}
    for item in settings["table_plan"]:
        table_ids_by_section.setdefault(str(item["section_id"]), []).append(str(item["table_id"]))

    sections: list[dict[str, str]] = []
    for section in report["sections"]:
        section_id = str(section["section_id"])
        section_claims = claims[section_id]
        if len(section_claims) != int(section["claim_count"]):
            raise ValueError(f"Claim allocation mismatch for {section_id}")
        claim_html = "".join(
            f'<li class="evidence-claim" data-claim-id="{section_id}__claim_{index:02d}">'
            f"{html.escape(text)}</li>"
            for index, text in enumerate(section_claims, start=1)
        )
        tables = "".join(table_html(table_id) for table_id in table_ids_by_section.get(section_id, []))
        visuals = "".join(visual_markup[section_id])
        body = (
            f'<p class="section-question"><strong>Question:</strong> {html.escape(questions[section_id])}</p>'
            + (f'<ul class="claim-list">{claim_html}</ul>' if claim_html else "")
            + tables
            + (f'<div class="visual-grid">{visuals}</div>' if visuals else "")
            + f'<div class="conclusion"><strong>Conclusion.</strong> {html.escape(conclusions[section_id])}</div>'
        )
        sections.append(
            {"section_id": section_id, "title": str(section["title"]), "body_html": body}
        )

    visual_frame = pd.DataFrame(visual_records)
    return sections, visual_frame


def render_report_html(
    title: str,
    subtitle: str,
    sections: Sequence[Mapping[str, Any]],
    metadata: Mapping[str, Any] | None = None,
) -> str:
    """Assemble a self-contained UTF-8 final-report document."""

    meta = dict(metadata or {})
    metadata_html = "".join(
        f"<dt>{html.escape(str(key))}</dt><dd>{html.escape(str(value))}</dd>"
        for key, value in meta.items()
    )
    section_html = "".join(
        (
            f'<section data-section-id="{html.escape(str(section["section_id"]))}">'
            f'<h2>{html.escape(str(section["title"]))}</h2>'
            f'{str(section.get("body_html", ""))}'
            "</section>"
        )
        for section in sections
    )
    return f"""<!doctype html>
<html lang="en" data-report-schema="{REPORT_SCHEMA_VERSION}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root{{--ink:#17202a;--muted:#5d6d7e;--accent:#245a75;--soft:#eef4f6;--line:#ced9de;}}
*{{box-sizing:border-box}} body{{margin:0;background:#f4f6f7;color:var(--ink);font:16px/1.55 Arial,sans-serif}}
main{{max-width:1180px;margin:0 auto;background:#fff;padding:42px 54px 70px}}
h1{{font-size:2.2rem;margin:0 0 .25rem}} h2{{margin-top:2.3rem;border-bottom:2px solid var(--line);padding-bottom:.35rem;color:var(--accent)}}
h3{{color:#304b5a}} .subtitle{{font-size:1.15rem;color:var(--muted)}} .report-meta{{display:grid;grid-template-columns:max-content 1fr;gap:.3rem 1rem;background:var(--soft);padding:1rem 1.2rem}}
.report-meta dt{{font-weight:700}} .report-meta dd{{margin:0}} table{{border-collapse:collapse;width:100%;margin:1rem 0 1.4rem}}
th,td{{border:1px solid var(--line);padding:.55rem .65rem;text-align:left;vertical-align:top}} th{{background:var(--soft)}}
.report-visual{{margin:1.25rem 0 1.6rem}} .report-visual img{{display:block;max-width:100%;height:auto;margin:auto}}
figcaption{{margin-top:.5rem;color:var(--muted);font-size:.93rem}} .conclusion{{border-left:5px solid var(--accent);background:var(--soft);padding:.8rem 1rem}}
.section-question{{font-size:1.05rem}} .claim-list{{padding-left:1.25rem}} .claim-list li{{margin:.45rem 0}}
.table-wrap{{overflow-x:auto;margin:1rem 0 1.5rem}} .table-note{{font-size:.9rem;color:var(--muted)}}
.visual-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:1rem}}
.visual-grid .report-visual{{margin:.5rem 0 1rem}}
@media(max-width:720px){{main{{padding:24px 18px}} table{{display:block;overflow-x:auto}}}}
</style>
</head>
<body><main>
<header><h1>{html.escape(title)}</h1><p class="subtitle">{html.escape(subtitle)}</p></header>
<dl class="report-meta">{metadata_html}</dl>
{section_html}
</main></body></html>"""


def validate_report_html(
    text: str,
    config: Mapping[str, Any],
    enforce_density: bool = True,
) -> pd.DataFrame:
    """Validate section order, portability, language, and visual density."""

    report = _settings(config)["report"]
    required_sections = [str(item["section_id"]) for item in report["sections"]]
    observed_sections = re.findall(r'data-section-id="([^"]+)"', text)
    image_sources = re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', text, flags=re.I)
    embedded_images = sum(source.startswith("data:image/") for source in image_sources)
    external_images = [source for source in image_sources if not source.startswith("data:image/")]
    tile_count = sum(int(value) for value in re.findall(r'data-tile-count="(\d+)"', text))
    missing_terms = [term for term in report["required_terms"] if term.lower() not in text.lower()]
    prohibited_terms = [term for term in report["prohibited_terms"] if term.lower() in text.lower()]
    mandatory_present = report["mandatory_statement"].lower() in text.lower()
    table_ids = re.findall(r'data-table-id="([^"]+)"', text)
    claim_ids = re.findall(r'data-claim-id="([^"]+)"', text)
    density_pass = (
        embedded_images >= int(report["minimum_embedded_image_count"])
        and tile_count >= int(report["minimum_embedded_tile_count"])
    ) if enforce_density else True
    checks = [
        _validation_row("rendered_report", "report schema", REPORT_SCHEMA_VERSION in text, True, REPORT_SCHEMA_VERSION in text, "Report schema marker is absent"),
        _validation_row("rendered_report", "section order", observed_sections, required_sections, observed_sections == required_sections, "Report sections differ from the approved mock order"),
        _validation_row("rendered_report", "external image dependencies", external_images, [], not external_images, "The standalone report contains external image dependencies"),
        _validation_row("rendered_report", "embedded image density", embedded_images, f">={report['minimum_embedded_image_count']}", density_pass if enforce_density else True, "Embedded image density is below the approved mock"),
        _validation_row("rendered_report", "embedded tile density", tile_count, f">={report['minimum_embedded_tile_count']}", density_pass if enforce_density else True, "Embedded tile density is below the approved mock"),
        _validation_row("rendered_report", "mandatory trustworthiness statement", mandatory_present, True, mandatory_present, "Mandatory trustworthiness statement is absent"),
        _validation_row("rendered_report", "required interpretation terms", missing_terms, [], not missing_terms, "Required interpretation language is absent"),
        _validation_row("rendered_report", "planning residue", prohibited_terms, [], not prohibited_terms, "Planning-mock or prohibited claim residue is present"),
    ]
    if enforce_density:
        checks.extend(
            [
                _validation_row("rendered_report", "table coverage", len(table_ids), len(_settings(config)["table_plan"]), len(table_ids) == len(_settings(config)["table_plan"]) and len(table_ids) == len(set(table_ids)), "Report table coverage differs from the approved plan"),
                _validation_row("rendered_report", "claim coverage", len(claim_ids), _settings(config)["expected_counts"]["evidence_claims"], len(claim_ids) == int(_settings(config)["expected_counts"]["evidence_claims"]) and len(claim_ids) == len(set(claim_ids)), "Report claim coverage differs from the approved plan"),
            ]
        )
    return pd.DataFrame(checks, columns=VALIDATION_COLUMNS)


def atomic_write_text(
    text: str,
    path: str | Path,
    encoding: str = "utf-8",
    retries: int = 6,
) -> Path:
    """Persist text atomically with Windows-friendly bounded retries."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(text, encoding=encoding, newline="\n")
        for attempt in range(max(1, int(retries))):
            try:
                os.replace(temporary, target)
                return target
            except PermissionError:
                if attempt + 1 >= int(retries):
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def atomic_write_csv(
    frame: pd.DataFrame,
    path: str | Path,
    retries: int = 6,
) -> Path:
    """Persist a CSV atomically with deterministic UTF-8 and line endings."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        frame.to_csv(temporary, index=False, encoding="utf-8", lineterminator="\n")
        for attempt in range(max(1, int(retries))):
            try:
                os.replace(temporary, target)
                return target
            except PermissionError:
                if attempt + 1 >= int(retries):
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        if temporary.exists():
            temporary.unlink()
    return target
