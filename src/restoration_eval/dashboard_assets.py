"""Controlled-300 dashboard-package helpers for Notebook 34.

The module validates the v2 package contract, performs memory-bounded input
preflight, defines normalized output schemas and provides deterministic IDs and
atomic persistence.  It packages validated evidence; it never performs model
inference, calculates a new scientific metric or tunes a scientific threshold.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import pandas as pd
import yaml

from .schemas import ARTIFACT_MANIFEST_COLUMNS, VALIDATION_CHECK_COLUMNS


MODULE_NAME = "restoration_eval.dashboard_assets"
VERSION = "2.0.0"
MODULE_VERSION = VERSION

DASHBOARD_ASSETS_CONFIG_SCHEMA = "dashboard_assets_config.v2"
DASHBOARD_PACKAGE_SCHEMA = "dashboard_package.v2"
DASHBOARD_RUNTIME_MANIFEST_SCHEMA = "dashboard_runtime_manifest.v1"
DISPLAY_BINDING_SCHEMA = "dashboard_display_binding.v1"
DASHBOARD_ASSET_SCHEMA = "dashboard_asset.v1"
ASSET_LOCATOR_SCHEMA = "dashboard_locator.v1"
RENDITION_SCHEMA = "dashboard_rendition.v1"
ROOM_PARTITION_SCHEMA = "dashboard_room_partition.v1"

# Compatibility aliases make stale-kernel failures intelligible.  The v1
# helper behaviour itself is deliberately not retained.
CONFIG_SCHEMA_VERSION = DASHBOARD_ASSETS_CONFIG_SCHEMA
DASHBOARD_PACKAGE_SCHEMA_VERSION = DASHBOARD_PACKAGE_SCHEMA

PRINCIPAL_ROOM_IDS = (
    "exhibition_foyer",
    "study_design",
    "metric_framework",
    "model_gallery",
    "stability_lab",
    "trustworthiness",
    "case_explorer",
    "research_archive",
)
SUPPLEMENTAL_MANIFEST_IDS = ("12A", "D01", "D02")
PRIMARY_MANIFEST_IDS = tuple(f"{number:02d}" for number in range(1, 34))
EXPECTED_UPSTREAM_IDS = (*PRIMARY_MANIFEST_IDS, *SUPPLEMENTAL_MANIFEST_IDS)

VALIDATION_COLUMNS = VALIDATION_CHECK_COLUMNS

ROOM_RECORD_COLUMNS = (
    "room_record_id", "room_id", "subroute_id", "section_id", "display_id",
    "slot_id", "display_order", "record_type", "record_key", "label",
    "value_json", "value_unit", "interpretation", "limitation", "denominator",
    "applicability_state", "source_notebook_ids_json", "source_paths_json",
    "source_row_ids_json", "schema_version", "status", "issue",
)

PAINTING_LOOKUP_COLUMNS = (
    "painting_id", "dataset_sort_index", "title", "artist", "date_or_period",
    "style_or_period", "category", "medium", "source", "license",
    "rights_status", "raw_image_path", "clean_image_path",
    "metadata_completeness_pct", "case_count", "candidate_count",
    "has_uncertainty", "has_selected_case_report", "painting_partition_path",
    "schema_version", "status", "issue",
)

DISPLAY_COMPONENT_COLUMNS = (
    "binding_id", "display_id", "slot_id", "room_id", "subroute_id",
    "display_order", "component_kind", "payload_ref", "requiredness",
    "mapping_state", "loading_tier", "painting_id", "case_id", "candidate_id",
    "model_id", "experiment_id", "seed", "prompt_variant_id",
    "uncertainty_group_id", "metric_name", "region_id", "evidence_layer",
    "annotation_id", "hand_control_id", "review_unit_id", "blind_review_code",
    "source_reference_ids_json", "interpretation", "limitation", "denominator",
    "applicability_state", "applicability_reason", "schema_version", "status",
    "issue",
)

DASHBOARD_ASSET_COLUMNS = (
    "asset_id", "asset_kind", "evidence_role", "requiredness", "mapping_state",
    "identity_json", "producer_notebook_id", "producer_notebook_stem",
    "producer_run_id", "producer_manifest_sha256", "source_artifact_key",
    "source_relative_path", "source_sha256", "source_size_bytes", "mime_type",
    "source_row_id", "source_selector_json", "width", "height", "denominator",
    "derivation_type", "derivation_parameters_json", "helper_version",
    "input_checksums_json", "output_sha256", "rendition_ids_json",
    "locator_ids_json", "availability_state", "availability_reason",
    "alternative_text", "schema_version", "status", "issue",
)

ASSET_LOCATOR_COLUMNS = (
    "locator_id", "asset_id", "transport", "provider", "repository",
    "revision", "relative_path", "immutable_resolve_url", "provenance_url",
    "expected_size_bytes", "expected_sha256", "publication_record_id",
    "release_id", "release_prefix", "catalogue_path", "catalogue_size_bytes",
    "catalogue_sha256", "painting_id", "remote_asset_id", "bundle_member_path",
    "bundle_member_size_bytes", "bundle_member_sha256", "schema_version",
    "status", "issue",
)

RENDITION_COLUMNS = (
    "rendition_id", "asset_id", "profile", "relative_path", "format",
    "mime_type", "width", "height", "size_bytes", "sha256", "source_sha256",
    "transformation_json", "purpose", "breakpoint_role", "lossless",
    "scientifically_exact", "upscaled", "crop_xyxy_json", "schema_version",
    "status", "issue",
)

ROOM_PARTITION_COLUMNS = (
    "partition_id", "room_id", "subroute_id", "relative_path", "loading_tier",
    "row_count", "size_bytes", "sha256", "display_ids_json", "schema_version",
    "status", "issue",
)

THRESHOLD_STRATA_COLUMNS = (
    "threshold_stratum_id", "category_id", "indicator_id", "metric_name",
    "region_id", "direction", "warning_quantile", "critical_quantile",
    "warning_threshold", "critical_threshold", "fitting_population_count",
    "fallback_level", "source_candidate_ids_sha256",
    "source_notebook_ids_json", "schema_version", "status", "issue",
)

STABILITY_TRAJECTORY_COLUMNS = (
    "trajectory_id", "painting_id", "model_id", "experiment_id",
    "analysis_family_id", "metric_name", "region_id", "condition_value",
    "condition_order", "estimate", "value_unit", "case_id", "candidate_id",
    "source_row_id", "source_notebook_ids_json", "schema_version", "status",
    "issue",
)

D02_HAND_SUMMARY_COLUMNS = (
    "summary_id", "record_type", "model_id", "metric_name", "estimate",
    "interval_low", "interval_high", "p_value", "q_value", "matched_case_count",
    "painting_count", "review_unit_count", "interpretation", "limitation",
    "source_row_ids_json", "schema_version", "status", "issue",
)

D02_LIGHTNESS_SUMMARY_COLUMNS = (
    "summary_id", "model_id", "metric_name", "coefficient", "interval_low",
    "interval_high", "p_value", "q_value", "association_state",
    "eligible_record_count", "painting_count", "interpretation", "limitation",
    "source_row_ids_json", "schema_version", "status", "issue",
)

ARTIFACT_COLUMNS = ARTIFACT_MANIFEST_COLUMNS

OUTPUT_SCHEMAS: dict[str, tuple[str, ...]] = {
    "room_records": ROOM_RECORD_COLUMNS,
    "painting_lookup": PAINTING_LOOKUP_COLUMNS,
    "display_components": DISPLAY_COMPONENT_COLUMNS,
    "dashboard_assets": DASHBOARD_ASSET_COLUMNS,
    "asset_locators": ASSET_LOCATOR_COLUMNS,
    "renditions": RENDITION_COLUMNS,
    "room_partitions": ROOM_PARTITION_COLUMNS,
    "threshold_strata": THRESHOLD_STRATA_COLUMNS,
    "stability_trajectories": STABILITY_TRAJECTORY_COLUMNS,
    "d02_hand_summary": D02_HAND_SUMMARY_COLUMNS,
    "d02_lightness_summary": D02_LIGHTNESS_SUMMARY_COLUMNS,
    "artifacts": ARTIFACT_COLUMNS,
}

OUTPUT_SCHEMA_VERSIONS = {
    "bootstrap": "dashboard_bootstrap.v1",
    "room_catalogue": "dashboard_room_catalogue.v1",
    "glossary": "dashboard_glossary.v1",
    "painting_lookup": "dashboard_painting_lookup.v1",
    "filter_options": "dashboard_filter_options.v2",
    "room_partition": ROOM_PARTITION_SCHEMA,
    "painting_partition": "dashboard_painting_partition.v1",
    "report_index": "dashboard_report_index.v2",
    "threshold_strata": "dashboard_threshold_strata.v1",
    "stability_trajectories": "dashboard_stability_trajectories.v1",
    "d02_hand_summary": "dashboard_d02_hand_summary.v1",
    "d02_lightness_summary": "dashboard_d02_lightness_summary.v1",
    "d02_r005_geometry": "dashboard_d02_r005_geometry.v1",
    "display_components": DISPLAY_BINDING_SCHEMA,
    "dashboard_assets": DASHBOARD_ASSET_SCHEMA,
    "asset_locators": ASSET_LOCATOR_SCHEMA,
    "renditions": RENDITION_SCHEMA,
    "room_partitions": "dashboard_room_partition_index.v1",
    "runtime_manifest": DASHBOARD_RUNTIME_MANIFEST_SCHEMA,
    "artifacts": "artifact_manifest.v1",
    "run_manifest": "run_manifest.v1",
    "validation": "validation_checks.v1",
}

REQUIRED_RUNTIME_BUDGETS = {
    "bootstrap_target_bytes": 8 * 1024 * 1024,
    "bootstrap_hard_bytes": 12 * 1024 * 1024,
    "local_package_target_bytes": 32 * 1024 * 1024,
    "local_package_hard_bytes": 64 * 1024 * 1024,
    "room_partition_serialized_hard_bytes": 5 * 1024 * 1024,
    "room_partition_memory_hard_bytes": 25 * 1024 * 1024,
    "bootstrap_dataframe_memory_hard_bytes": 64 * 1024 * 1024,
    "bootstrap_rss_increase_hard_bytes": 128 * 1024 * 1024,
    "foyer_process_target_bytes": 384 * 1024 * 1024,
    "foyer_process_hard_bytes": 512 * 1024 * 1024,
    "routine_room_remote_payload_hard_bytes": 4 * 1024 * 1024,
    "exact_bundle_payload_hard_bytes": 32 * 1024 * 1024,
    "exact_bundle_transaction_hard_bytes": 34 * 1024 * 1024,
    "cache_hard_bytes": 512 * 1024 * 1024,
    "cache_evict_to_bytes": 384 * 1024 * 1024,
    "thumb_hard_bytes": 125 * 1024,
    "standard_hard_bytes": 400 * 1024,
    "diagnostic_preview_hard_bytes": 750 * 1024,
    "max_remote_requests_per_action": 2,
    "max_bundle_downloads_per_action": 1,
    "startup_network_requests": 0,
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")


class _UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that fails closed on duplicate mapping keys."""


def _construct_unique_mapping(loader: yaml.Loader, node: yaml.Node, deep: bool = False) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"Duplicate YAML mapping key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    return config.get("dashboard_assets", config)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def stable_id(prefix: str, *parts: Any) -> str:
    payload: Any = parts[0] if len(parts) == 1 else list(parts)
    return f"{prefix}_{hashlib.sha256(canonical_json_bytes(payload)).hexdigest()[:24]}"


def asset_id(identity: Mapping[str, Any], source_sha256: str, role: str) -> str:
    return stable_id("asset", {
        "identity": dict(identity), "source_sha256": source_sha256, "role": role,
    })


def binding_id(display_id: str, slot_id: str, payload_ref: str) -> str:
    return stable_id("binding", {
        "display_id": display_id, "slot_id": slot_id, "payload_ref": payload_ref,
    })


def locator_id(transport: str, repository: str, revision: str, path_or_member: str) -> str:
    return stable_id("locator", {
        "transport": transport, "repository": repository, "revision": revision,
        "path_or_member": path_or_member,
    })


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
    if not text or "\x00" in text or "://" in text or "\\" in text:
        return False
    path = Path(text)
    return text != "." and not path.is_absolute() and ".." not in path.parts


def is_sha256(value: Any) -> bool:
    return bool(_SHA256_RE.fullmatch(str(value).strip().lower()))


def is_full_git_revision(value: Any) -> bool:
    return bool(_GIT_REVISION_RE.fullmatch(str(value).strip().lower()))


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
        "validation_stage": str(stage),
        "check_id": stable_id("check", {"stage": stage, "name": check_name}),
        "check_description": str(check_name),
        "severity": str(severity),
        "expected": display(expected),
        "observed": display(observed),
        "passed": bool(passed),
        "details": "" if passed else str(issue),
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _safe_project_path(project_root: Path, relative_path: str) -> Path:
    _require(is_repo_relative(relative_path), f"Unsafe repository path: {relative_path}")
    candidate = (project_root / relative_path).resolve()
    _require(candidate == project_root or candidate.is_relative_to(project_root),
             f"Path escapes repository root: {relative_path}")
    return candidate


def load_dashboard_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the approved Controlled-300 contract."""

    with Path(path).open("r", encoding="utf-8-sig") as handle:
        config = yaml.load(handle, Loader=_UniqueKeyLoader)
    _require(isinstance(config, dict), "Notebook 34 configuration must be a mapping")
    _require(config.get("config_schema_version") == DASHBOARD_ASSETS_CONFIG_SCHEMA,
             "Unexpected Notebook 34 configuration schema")
    settings = config.get("dashboard_assets")
    _require(isinstance(settings, dict), "Missing dashboard_assets configuration")
    _require(settings.get("notebook_id") == "34", "Notebook 34 identity is not locked")
    _require(settings.get("notebook_stem") == "34_final_streamlit_dashboard_assets",
             "Notebook 34 stem is not locked")
    _require(settings.get("dataset_scope") == "controlled_300", "Dataset scope is not controlled_300")
    _require(settings.get("creates_new_scientific_evidence") is False,
             "Notebook 34 must remain presentation-only")
    _require(settings.get("dashboard_package_schema_version") == DASHBOARD_PACKAGE_SCHEMA,
             "Unexpected dashboard package schema")
    _require(settings.get("runtime_manifest_schema_version") == DASHBOARD_RUNTIME_MANIFEST_SCHEMA,
             "Unexpected runtime-manifest schema")

    primary = settings.get("upstream_manifests")
    supplemental = settings.get("supplemental_manifests")
    _require(isinstance(primary, dict) and tuple(primary) == PRIMARY_MANIFEST_IDS,
             "Primary manifests must explicitly and sequentially cover N01-N33")
    _require(isinstance(supplemental, dict) and tuple(supplemental) == SUPPLEMENTAL_MANIFEST_IDS,
             "Supplemental manifests must separately register N12A, D01 and D02")
    all_specs = {**primary, **supplemental}
    all_paths: list[str] = []
    for logical_id, spec in all_specs.items():
        _require(isinstance(spec, dict), f"Manifest spec {logical_id} must be a mapping")
        for key in ("path", "producer_notebook_id", "run_id", "sha256", "size_bytes"):
            _require(key in spec, f"Manifest spec {logical_id} is missing {key}")
        _require(is_repo_relative(spec["path"]), f"Unsafe manifest path for {logical_id}")
        _require(is_sha256(spec["sha256"]), f"Invalid manifest SHA-256 for {logical_id}")
        all_paths.append(str(spec["path"]))
    _require(len(all_paths) == len(set(all_paths)), "Manifest paths must be unique")

    rooms = settings.get("rooms")
    _require(isinstance(rooms, list) and len(rooms) == 9,
             "Exactly nine room/subroute records are required")
    principal = [row.get("room_id") for row in rooms if row.get("route_kind") == "principal"]
    _require(tuple(principal) == PRINCIPAL_ROOM_IDS,
             "Principal room order differs from the approved order")
    children = [row for row in rooms if row.get("route_kind") == "child"]
    _require(len(children) == 1
             and children[0].get("room_id") == "focused_portrait_review"
             and children[0].get("parent_room_id") == "trustworthiness",
             "Focused Portrait Review must be the sole Trustworthiness child route")

    governing = settings.get("governing_contracts")
    expected_governing = {
        "page_contract": "earlier_gate",
        "producer_artifact_map": "earlier_gate",
        "remote_asset_audit": "earlier_gate",
        "runtime_loading_contract": "earlier_gate",
        "n34_implementation_contract": "implementation_contract",
    }
    _require(isinstance(governing, dict)
             and {key: value.get("authority_kind") for key, value in governing.items()}
             == expected_governing,
             "Governing-contract closure differs from the approved five records")
    for contract_id, spec in governing.items():
        _require(is_repo_relative(spec.get("path")), f"Unsafe governing path: {contract_id}")
        _require(is_sha256(spec.get("sha256")), f"Invalid governing SHA-256: {contract_id}")

    inputs = settings.get("inputs")
    contracts = settings.get("input_table_contracts")
    _require(isinstance(inputs, dict), "inputs must be a mapping")
    _require(isinstance(contracts, dict) and contracts, "input_table_contracts must be non-empty")
    for input_key, relative_path in inputs.items():
        _require(
            is_repo_relative(relative_path),
            f"Unsafe input path: {input_key}",
        )
    for input_key, contract in contracts.items():
        _require(input_key in inputs, f"Missing input path for table contract: {input_key}")
        _require(isinstance(contract.get("rows"), int), f"Missing integer row count: {input_key}")
        _require(isinstance(contract.get("required_columns"), list)
                 and bool(contract["required_columns"]),
                 f"Missing required columns: {input_key}")

    output = settings.get("output")
    _require(isinstance(output, dict), "output must be a mapping")
    _require(output.get("root") == "outputs/34_final_streamlit_dashboard_assets",
             "Notebook 34 output root differs from the approved root")
    output_values: list[str] = []
    for key, value in output.items():
        _require(is_repo_relative(value), f"Unsafe output path: {key}")
        if key != "root":
            output_values.append(str(value))
    _require(len(output_values) == len(set(output_values)), "Output destinations must be unique")
    _require(settings.get("expected_output_schemas") == OUTPUT_SCHEMA_VERSIONS,
             "Expected output-schema mapping differs from the v2 helper")
    _require(settings.get("runtime_budgets") == REQUIRED_RUNTIME_BUDGETS,
             "Runtime budgets differ from the approved Step 4 contract")
    return config


def resolve_output_paths(project_root: str | Path, config: Mapping[str, Any]) -> dict[str, Path]:
    root = Path(project_root).resolve()
    output = _settings(config)["output"]
    output_root = _safe_project_path(root, str(output["root"]))
    resolved: dict[str, Path] = {"root": output_root}
    for key, value in output.items():
        if key == "root":
            continue
        relative = str(value)
        _require(is_repo_relative(relative), f"Unsafe output path: {key}")
        candidate = (output_root / relative).resolve()
        _require(candidate.is_relative_to(output_root), f"Output path escapes root: {key}")
        resolved[key] = candidate
    return resolved


def create_output_directories(paths: Mapping[str, Path]) -> None:
    output_root = Path(paths["root"]).resolve()
    for key, raw_path in paths.items():
        path = Path(raw_path).resolve()
        _require(path == output_root or path.is_relative_to(output_root),
                 f"Unsafe output target: {key}")
        if key == "root" or key.endswith("_dir"):
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)


def read_csv_contract(
    path: str | Path,
    *,
    required_columns: Sequence[str] = (),
    expected_rows: int | None = None,
    dtype: Any = None,
    usecols: Sequence[str] | None = None,
) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=dtype, usecols=usecols, low_memory=False)
    missing = sorted(set(required_columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{Path(path).name} missing required columns: {missing}")
    if expected_rows is not None and len(frame) != int(expected_rows):
        raise ValueError(f"{Path(path).name} has {len(frame)} rows; expected {int(expected_rows)}")
    return frame


def _csv_row_count(path: Path, count_column: str) -> int:
    """Count logical CSV records while respecting quoted embedded newlines."""

    del count_column
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def validate_input_table_contracts(
    project_root: str | Path,
    config: Mapping[str, Any],
    *,
    load_frames: bool = False,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate CSV headers and logical row counts without retaining frames."""

    if load_frames:
        raise ValueError("Controlled-300 preflight forbids eager input-frame retention")
    root = Path(project_root).resolve()
    settings = _settings(config)
    contracts = settings["input_table_contracts"]
    inputs = settings["inputs"]
    summaries: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    # Reuse the completed inventory's logical CSV counts instead of
    # re-tokenizing multi-gigabyte producer tables in every preflight. Tiny
    # fixture configs without an inventory use the RFC-aware fallback above.
    inventory_by_path: dict[str, dict[str, Any]] = {}
    inventory_relative = inputs.get("inventory_path")
    if inventory_relative and is_repo_relative(inventory_relative):
        inventory_path = _safe_project_path(root, str(inventory_relative))
        if inventory_path.is_file():
            inventory_frame = pd.read_csv(
                inventory_path,
                usecols=[
                    "relative_path",
                    "size_bytes",
                    "tabular_row_count",
                    "tabular_column_count",
                    "tabular_columns_json",
                    "hash_value",
                    "read_error_count",
                ],
                low_memory=False,
            )
            inventory_by_path = {
                str(row["relative_path"]): row.to_dict()
                for _, row in inventory_frame.iterrows()
            }
            del inventory_frame

    for number, (input_key, contract) in enumerate(contracts.items(), start=1):
        relative = str(inputs[input_key])
        required = [str(value) for value in contract["required_columns"]]
        expected_rows = int(contract["rows"])
        issue = ""
        observed_rows = -1
        observed_columns: list[str] = []
        size_bytes = -1
        try:
            path = _safe_project_path(root, relative)
            exists = path.is_file()
        except Exception as exc:
            path = None
            exists = False
            issue = f"{type(exc).__name__}: {exc}"

        checks.append(validation_row(
            "batch_1_input_tables", f"{input_key}_exists", exists, True, exists,
            issue or f"Missing declared input table: {relative}",
        ))
        if exists and path is not None:
            try:
                size_bytes = path.stat().st_size
                observed_columns = pd.read_csv(path, nrows=0).columns.astype(str).tolist()
                missing = sorted(set(required) - set(observed_columns))
                checks.append(validation_row(
                    "batch_1_input_tables", f"{input_key}_required_columns", missing,
                    [], not missing, f"Missing required columns for {relative}: {missing}",
                ))
                if not missing:
                    inventory_record = inventory_by_path.get(relative)
                    if inventory_record is not None:
                        inventory_errors = int(inventory_record["read_error_count"])
                        inventory_size = int(inventory_record["size_bytes"])
                        inventory_count = int(inventory_record["tabular_row_count"])
                        inventory_ok = inventory_errors == 0 and inventory_size == size_bytes
                        checks.append(validation_row(
                            "batch_1_input_tables",
                            f"{input_key}_inventory_record",
                            {
                                "read_errors": inventory_errors,
                                "inventory_size_bytes": inventory_size,
                                "actual_size_bytes": size_bytes,
                            },
                            {"read_errors": 0, "inventory_size_equals_actual": True},
                            inventory_ok,
                            f"Inventory record is stale or unreadable for {relative}",
                        ))
                        if not inventory_ok:
                            issue = "inventory record is stale or has read errors"
                        observed_rows = inventory_count
                    else:
                        observed_rows = _csv_row_count(path, required[0])
                    passed = observed_rows == expected_rows
                    checks.append(validation_row(
                        "batch_1_input_tables", f"{input_key}_row_count",
                        observed_rows, expected_rows, passed,
                        f"Unexpected row count for {relative}",
                    ))
                    if not passed:
                        issue = f"observed {observed_rows} rows; expected {expected_rows}"
                else:
                    issue = f"missing required columns: {missing}"
            except Exception as exc:
                issue = f"{type(exc).__name__}: {exc}"
                checks.append(validation_row(
                    "batch_1_input_tables", f"{input_key}_readable",
                    type(exc).__name__, "readable CSV", False, issue,
                ))

        passed = bool(exists and not issue and observed_rows == expected_rows)
        summaries.append({
            "input_key": input_key,
            "relative_path": relative,
            "size_bytes": size_bytes,
            "observed_rows": observed_rows,
            "observed_columns": len(observed_columns),
            "required_columns_json": json.dumps(required, ensure_ascii=False),
            "status": "passed" if passed else "failed",
            "issue": issue,
        })
        if progress_callback:
            progress_callback(number, len(contracts), input_key)

    return (
        pd.DataFrame(summaries, columns=(
            "input_key", "relative_path", "size_bytes", "observed_rows",
            "observed_columns", "required_columns_json", "status", "issue",
        )),
        pd.DataFrame(checks, columns=VALIDATION_COLUMNS),
    )


def validate_declared_input_paths(
    project_root: str | Path,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Require every declared table, document, report and registry input locally."""

    root = Path(project_root).resolve()
    checks: list[dict[str, Any]] = []
    for input_key, relative in _settings(config)["inputs"].items():
        try:
            path = _safe_project_path(root, str(relative))
            exists = path.is_file()
            observed: Any = path.relative_to(root).as_posix() if exists else False
            issue = "" if exists else f"Missing declared input: {relative}"
        except Exception as exc:
            exists = False
            observed = f"{type(exc).__name__}: {exc}"
            issue = f"Unsafe declared input: {relative}"
        checks.append(validation_row(
            "batch_1_declared_inputs",
            f"{input_key}_exists",
            observed,
            str(relative),
            exists,
            issue,
        ))
    return pd.DataFrame(checks, columns=VALIDATION_COLUMNS)


def manifest_specs(config: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    settings = _settings(config)
    return {**settings["upstream_manifests"], **settings["supplemental_manifests"]}


def load_upstream_manifests(
    project_root: str | Path,
    config: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], pd.DataFrame]:
    """Load and checksum-pin N01-N33 plus separate N12A/D01/D02 records."""

    root = Path(project_root).resolve()
    manifests: dict[str, dict[str, Any]] = {}
    checks: list[dict[str, Any]] = []
    for logical_id, spec in manifest_specs(config).items():
        relative = str(spec["path"])
        try:
            path = _safe_project_path(root, relative)
            exists = path.is_file()
        except Exception as exc:
            path = None
            exists = False
            checks.append(validation_row(
                "batch_1_upstream_manifests", f"{logical_id}_safe_path",
                f"{type(exc).__name__}: {exc}", "safe repository-relative file",
                False, f"Unsafe upstream-manifest path: {relative}",
            ))
        checks.append(validation_row(
            "batch_1_upstream_manifests", f"{logical_id}_exists", exists, True,
            exists, f"Missing upstream manifest: {relative}",
        ))
        if not exists or path is None:
            continue
        try:
            observed_sha = sha256_file(path)
            observed_size = path.stat().st_size
            with path.open("r", encoding="utf-8-sig") as handle:
                manifest = json.load(handle)
            manifests[logical_id] = manifest
            observations = {
                "sha256": (observed_sha, str(spec["sha256"]).lower()),
                "size_bytes": (observed_size, int(spec["size_bytes"])),
                "producer_notebook_id": (
                    str(manifest.get("notebook_id")), str(spec["producer_notebook_id"]),
                ),
                "run_id": (str(manifest.get("run_id")), str(spec["run_id"])),
                "run_status": (manifest.get("run_status"), "completed"),
                "completion_gate_passed": (manifest.get("completion_gate_passed"), True),
            }
            for suffix, (observed, expected) in observations.items():
                passed = observed == expected
                checks.append(validation_row(
                    "batch_1_upstream_manifests", f"{logical_id}_{suffix}",
                    observed, expected, passed,
                    f"Pinned upstream manifest differs for {logical_id}: {suffix}",
                ))
        except Exception as exc:
            manifests.pop(logical_id, None)
            checks.append(validation_row(
                "batch_1_upstream_manifests", f"{logical_id}_load",
                type(exc).__name__, "loadable pinned completed manifest", False,
                f"{type(exc).__name__}: {exc}",
            ))
    return manifests, pd.DataFrame(checks, columns=VALIDATION_COLUMNS)


def validate_output_frame(frame: pd.DataFrame, schema_key: str) -> pd.DataFrame:
    if schema_key not in OUTPUT_SCHEMAS:
        raise KeyError(f"Unknown dashboard output schema: {schema_key}")
    expected = list(OUTPUT_SCHEMAS[schema_key])
    observed = frame.columns.astype(str).tolist()
    missing = [column for column in expected if column not in observed]
    extra = [column for column in observed if column not in expected]
    if missing or extra:
        raise ValueError(f"{schema_key} columns differ; missing={missing}, extra={extra}")
    return frame.loc[:, expected]


def empty_output_frame(schema_key: str) -> pd.DataFrame:
    if schema_key not in OUTPUT_SCHEMAS:
        raise KeyError(f"Unknown dashboard output schema: {schema_key}")
    return pd.DataFrame(columns=OUTPUT_SCHEMAS[schema_key])


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_path(path: str | Path) -> str:
    root = Path(path)
    if root.is_file():
        return sha256_file(root)
    if not root.is_dir():
        raise FileNotFoundError(root)
    digest = hashlib.sha256()
    for item in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(item)))
    return digest.hexdigest()


def path_statistics(path: str | Path) -> dict[str, int]:
    target = Path(path)
    if target.is_file():
        return {"file_count": 1, "size_bytes": target.stat().st_size}
    if not target.exists():
        return {"file_count": 0, "size_bytes": 0}
    files = [candidate for candidate in target.rglob("*") if candidate.is_file()]
    return {"file_count": len(files),
            "size_bytes": sum(candidate.stat().st_size for candidate in files)}


def _replace_with_retry(source: Path, destination: Path, *, attempts: int = 8) -> None:
    last_error: OSError | None = None
    for number in range(attempts):
        try:
            os.replace(source, destination)
            return
        except OSError as exc:
            last_error = exc
            if number + 1 < attempts:
                time.sleep(0.05 * (2**number))
    if last_error is not None:
        raise last_error


def atomic_write_bytes(payload: bytes, path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(payload)
        _replace_with_retry(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_json(payload: Mapping[str, Any], path: str | Path) -> None:
    encoded = json.dumps(
        payload, ensure_ascii=False, indent=2, sort_keys=True, default=str,
    ).encode("utf-8") + b"\n"
    atomic_write_bytes(encoded, path)


def atomic_write_json_gzip(payload: Any, path: str | Path) -> dict[str, Any]:
    decoded = canonical_json_bytes(payload)
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as handle:
        handle.write(decoded)
    compressed = buffer.getvalue()
    atomic_write_bytes(compressed, path)
    return {
        "decoded_size_bytes": len(decoded),
        "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
        "compressed_size_bytes": len(compressed),
        "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
    }


def atomic_write_csv(frame: pd.DataFrame, path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        frame.to_csv(temporary, index=False, lineterminator="\n")
        _replace_with_retry(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_parquet(frame: pd.DataFrame, path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        frame.to_parquet(temporary, index=False, compression="zstd")
        _replace_with_retry(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def blocking_validation_failures(checks: pd.DataFrame) -> pd.DataFrame:
    required = {"severity", "passed"}
    missing = sorted(required - set(checks.columns))
    if missing:
        raise ValueError(f"Validation frame missing columns: {missing}")
    if checks.empty:
        return checks.copy()
    return checks.loc[
        checks["severity"].eq("blocking") & ~checks["passed"].map(as_bool)
    ].copy()


def blocking_failures(checks: pd.DataFrame) -> pd.DataFrame:
    return blocking_validation_failures(checks)


def assert_no_blocking_failures(checks: pd.DataFrame, *, stage: str) -> None:
    failures = blocking_validation_failures(checks)
    if not failures.empty:
        names = sorted(
            failures.get("check_description", pd.Series(dtype=str)).astype(str)
        )
        raise RuntimeError(
            f"{stage} failed with {len(failures)} blocking check(s): {names}"
        )
