"""Metric, region-policy, threshold, and flag-ablation utilities for Notebook 28.

The module consumes validated artifacts from Notebooks 08 and 13--27.  It does
not run restoration or feature inference, does not alter frozen upstream
outputs, and never constructs a universal quality or trust score.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml

from .paths import find_project_root, resolve_repo_path


MODULE_NAME = "restoration_eval.metric_region_ablation"
MODULE_VERSION = "1.0.0"
CONFIG_SCHEMA_VERSION = "metric_region_ablation_config.v1"
SCENARIO_SCHEMA_VERSION = "metric_region_ablation_scenarios.v1"
ABLATION_RESULTS_SCHEMA_VERSION = "metric_region_ablation_results.v1"
FLAG_STABILITY_SCHEMA_VERSION = "ablation_flag_stability.v1"

SCENARIO_FAMILIES = frozenset({"metric", "region", "threshold", "aggregation"})
FLAG_STATES = frozenset(
    {"triggered", "not_triggered", "insufficient_evidence", "not_applicable"}
)

SCENARIO_COLUMNS = (
    "scenario_id", "scenario_order", "scenario_family", "display_name",
    "is_baseline", "ranking_applicable", "flag_applicable",
    "metric_mode", "component_groups_json", "active_anchor_ids_json",
    "active_indicator_ids_json", "region_policy_id",
    "preferred_regions_json", "threshold_policy_id",
    "aggregation_policy_id", "expected_effect", "schema_version", "status",
    "issue",
)

ABLATION_RESULT_COLUMNS = (
    "result_id", "scenario_id", "scenario_family", "result_kind",
    "analysis_scope", "scope_value", "entity_type", "entity_id", "model_id",
    "flag_id", "baseline_value", "scenario_value", "absolute_change",
    "relative_change", "baseline_rank", "scenario_rank", "rank_change",
    "baseline_winner_id", "scenario_winner_id", "winner_retained",
    "kendalls_tau", "spearman_rho", "baseline_triggered_count",
    "scenario_triggered_count", "changed_count", "changed_fraction",
    "insufficient_evidence_count", "available_family_count",
    "available_anchor_count", "n_paintings", "n_cases", "n_candidates",
    "independent_unit", "applicability_status", "interpretation_status",
    "schema_version", "status", "issue",
)

FLAG_STABILITY_COLUMNS = (
    "stability_id", "scenario_id", "scenario_family", "candidate_id",
    "case_id", "painting_id", "model_id", "experiment_id",
    "prompt_variant_id", "population_role", "baseline_triggered_flag_count",
    "scenario_triggered_flag_count", "baseline_critical_flag_count",
    "scenario_critical_flag_count", "baseline_insufficient_flag_count",
    "scenario_insufficient_flag_count", "unchanged_flag_count",
    "changed_flag_count", "flag_state_agreement_fraction",
    "triggered_jaccard", "newly_triggered_flag_ids_json",
    "no_longer_triggered_flag_ids_json", "new_insufficient_flag_ids_json",
    "resolved_insufficient_flag_ids_json", "changed_flag_ids_json",
    "max_severity_transition", "change_reason", "schema_version", "status",
    "issue",
)


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    settings = config.get("metric_region_ablation", config)
    if not isinstance(settings, Mapping):
        raise TypeError("metric_region_ablation settings must be a mapping")
    return settings


def _stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join("" if part is None else str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20]}"


def _json_list(values: Iterable[Any]) -> str:
    normalized = sorted(
        {str(value) for value in values if pd.notna(value) and str(value).strip()}
    )
    return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))


def _require_columns(frame: pd.DataFrame, columns: Sequence[str], label: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing columns: {missing}")


def _normalized_relative_path(value: Any) -> bool:
    text = str(value).strip()
    return bool(text) and not Path(text).is_absolute() and "\\" not in text


def _as_bool(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if value is None or (not isinstance(value, (list, tuple, dict)) and pd.isna(value)):
        return False
    return str(value).strip().lower() in {"true", "1", "1.0", "yes", "y"}


def load_metric_region_ablation_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the approved Notebook 28 contract."""

    with Path(path).open("r", encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Metric/region ablation configuration must be a mapping")
    if config.get("config_schema_version") != CONFIG_SCHEMA_VERSION:
        raise ValueError("Unsupported metric/region ablation config schema")

    settings = _settings(config)
    required = {
        "notebook_id", "notebook_stem", "scenario_schema_version",
        "ablation_results_schema_version", "flag_stability_schema_version",
        "inputs", "output", "population", "component_groups",
        "metric_scenarios", "region_scenarios", "threshold_scenarios",
        "aggregation_scenarios", "region_policy", "ranking",
        "flag_stability", "subgroup_policy", "report", "expected_counts",
        "evidence_policy", "known_limitations",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"Metric/region ablation config is missing keys: {missing}")
    if settings["notebook_id"] != "28" or settings["notebook_stem"] != "28_metric_and_region_policy_ablation":
        raise ValueError("Notebook 28 identity contract changed")

    versions = (
        ("scenario_schema_version", SCENARIO_SCHEMA_VERSION),
        ("ablation_results_schema_version", ABLATION_RESULTS_SCHEMA_VERSION),
        ("flag_stability_schema_version", FLAG_STABILITY_SCHEMA_VERSION),
    )
    for key, expected in versions:
        if settings[key] != expected:
            raise ValueError(f"Configured {key} does not match helper")

    for key, value in settings["inputs"].items():
        if not _normalized_relative_path(value):
            raise ValueError(f"inputs.{key} must be a normalized repository-relative path")

    exact_output = {
        "root": "outputs/28_metric_and_region_policy_ablation",
        "ablation_results_path": "metrics/ablation_results.csv",
        "flag_stability_path": "metrics/flag_stability.csv",
        "ranking_figure_path": "figures/ablation_ranking_changes.png",
        "flag_figure_path": "figures/ablation_flag_changes.png",
        "report_path": "reports/ablation_study.html",
        "run_manifest_path": "manifests/run_manifest.json",
        "artifacts_path": "manifests/artifacts.csv",
        "validation_path": "validation/checks.csv",
    }
    for key, expected in exact_output.items():
        if settings["output"].get(key) != expected:
            raise ValueError(f"output.{key} must equal {expected!r}")

    expected = settings["expected_counts"]
    scenario_total = (
        len(settings["metric_scenarios"])
        + len(settings["region_scenarios"])
        + len(settings["threshold_scenarios"])
        + len(settings["aggregation_scenarios"])
    )
    if scenario_total != int(expected["scenarios"]):
        raise ValueError("Scenario arithmetic is inconsistent")
    if int(expected["ranking_scenarios"]) != len(settings["metric_scenarios"]) + len(settings["region_scenarios"]):
        raise ValueError("Ranking-scenario arithmetic is inconsistent")
    if int(expected["model_rank_rows"]) != int(expected["ranking_scenarios"]) * int(expected["core_models"]):
        raise ValueError("Model-rank arithmetic is inconsistent")
    if int(expected["case_rank_rows"]) != int(expected["ranking_scenarios"]) * int(expected["matched_cases"]):
        raise ValueError("Case-rank arithmetic is inconsistent")
    if int(expected["flag_summary_rows"]) != int(expected["scenarios"]) * int(expected["trust_flags"]):
        raise ValueError("Flag-summary arithmetic is inconsistent")
    if int(expected["flag_stability_rows"]) != int(expected["scenarios"]) * int(expected["flag_candidates"]):
        raise ValueError("Flag-stability arithmetic is inconsistent")

    scenario_ids = [
        str(item["scenario_id"])
        for section in (
            "metric_scenarios", "region_scenarios", "threshold_scenarios",
            "aggregation_scenarios",
        )
        for item in settings[section]
    ]
    if len(scenario_ids) != len(set(scenario_ids)):
        raise ValueError("Scenario identifiers must be unique")
    if scenario_ids[0] != settings["flag_stability"]["baseline_scenario_id"]:
        raise ValueError("The complete framework must be the first and baseline scenario")

    groups = settings["component_groups"]
    known_groups = set(groups)
    for item in settings["metric_scenarios"]:
        unknown = sorted(set(item.get("component_groups", [])) - known_groups)
        if unknown:
            raise ValueError(f"Scenario {item['scenario_id']} references unknown groups: {unknown}")
        if item.get("mode") not in {"complete", "exclude", "include_only"}:
            raise ValueError(f"Scenario {item['scenario_id']} has an unsupported metric mode")

    required_policies = set(settings["region_policy"]["required_policy_ids"])
    configured_policies = {
        settings["region_policy"]["complete_policy_id"],
        *(str(item["region_policy_id"]) for item in settings["region_scenarios"]),
    }
    if configured_policies != required_policies:
        raise ValueError("Configured region-policy scenarios do not match the required policy IDs")

    policy = settings["evidence_policy"]
    prohibited_true = (
        "flags_are_human_ground_truth", "flags_are_conservation_ground_truth",
        "combined_trust_score_retained", "universal_model_superiority_claim_allowed",
        "missing_evidence_may_count_as_improvement", "runtime_in_quality_ranking",
        "bounded_sdxl_in_full_ranking",
    )
    if any(bool(policy[key]) for key in prohibited_true):
        raise ValueError("A prohibited evidence interpretation is enabled")
    ranking = settings["ranking"]
    if bool(ranking["retain_continuous_combined_quality_score"]) or bool(ranking["retain_continuous_case_trust_score"]):
        raise ValueError("Continuous combined quality and case-trust scores are prohibited")

    report = settings["report"]
    if not bool(report["self_contained_html"]) or not bool(report["approved_mock_structure_locked"]):
        raise ValueError("The approved self-contained report structure must remain locked")
    if len(report["required_section_ids"]) != 12 or len(set(report["required_section_ids"])) != 12:
        raise ValueError("Report must retain the approved twelve-section structure")
    if int(expected["canonical_output_files"]) != 8 or int(expected["artifact_records"]) != 6:
        raise ValueError("Canonical output or artifact count changed")
    return config


def resolve_metric_region_ablation_inputs(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
    *,
    must_exist: bool = True,
) -> dict[str, Path]:
    """Resolve every declared input without dynamic file discovery."""

    root = find_project_root(project_root)
    return {
        str(key): resolve_repo_path(value, root, must_exist=must_exist)
        for key, value in _settings(config)["inputs"].items()
    }


def validate_upstream_completion(
    manifests: Mapping[str, Mapping[str, Any]],
    *,
    expected_notebook_ids: Sequence[str] = (
        "08", "13", "14", "15", "16", "17", "18", "19", "20", "21",
        "22", "23", "24", "25", "26", "27",
    ),
) -> pd.DataFrame:
    """Return one completion-gate row for every direct evidence producer."""

    rows: list[dict[str, Any]] = []
    for notebook_id in expected_notebook_ids:
        manifest = manifests.get(str(notebook_id))
        present = isinstance(manifest, Mapping)
        rows.append({
            "notebook_id": str(notebook_id),
            "manifest_present": present,
            "run_status": str(manifest.get("run_status", "")) if present else "",
            "validation_status": str(manifest.get("validation_status", "")) if present else "",
            "completion_gate_passed": bool(manifest.get("completion_gate_passed", False)) if present else False,
        })
    result = pd.DataFrame(rows)
    result["passed"] = (
        result["manifest_present"]
        & result["run_status"].eq("completed")
        & result["validation_status"].eq("passed")
        & result["completion_gate_passed"]
    )
    return result


def _component_memberships(config: Mapping[str, Any], kind: str) -> dict[str, set[str]]:
    settings = _settings(config)
    key = "anchor_ids" if kind == "anchor" else "indicator_ids"
    result: dict[str, set[str]] = {}
    for group_id, values in settings["component_groups"].items():
        for value in values.get(key, []):
            result.setdefault(str(value), set()).add(str(group_id))
    return result


def _active_component_ids(
    config: Mapping[str, Any],
    *,
    mode: str,
    selected_groups: Sequence[str],
    kind: str,
) -> list[str]:
    memberships = _component_memberships(config, kind)
    selected = {str(value) for value in selected_groups}
    if mode == "complete":
        return sorted(memberships)
    if mode == "exclude":
        return sorted(
            component_id
            for component_id, groups in memberships.items()
            if not groups.intersection(selected)
        )
    if mode == "include_only":
        return sorted(
            component_id
            for component_id, groups in memberships.items()
            if groups.intersection(selected)
        )
    raise ValueError(f"Unsupported metric scenario mode: {mode}")


def build_scenario_catalog(config: Mapping[str, Any]) -> pd.DataFrame:
    """Build the exact ordered 23-scenario ablation catalogue."""

    settings = _settings(config)
    baseline = settings["flag_stability"]["baseline_scenario_id"]
    all_anchors = _active_component_ids(config, mode="complete", selected_groups=[], kind="anchor")
    all_indicators = _active_component_ids(config, mode="complete", selected_groups=[], kind="indicator")
    rows: list[dict[str, Any]] = []

    def add_row(
        *,
        scenario_id: str,
        scenario_family: str,
        display_name: str,
        metric_mode: str = "complete",
        component_groups: Sequence[str] = (),
        anchors: Sequence[str] = (),
        indicators: Sequence[str] = (),
        region_policy_id: str = "complete_approved_policy",
        preferred_regions: Sequence[str] = (),
        threshold_policy_id: str = "baseline_n27_thresholds",
        aggregation_policy_id: str = "baseline_two_warnings_or_one_critical",
        expected_effect: str = "recomputed_sensitivity_result",
    ) -> None:
        rows.append({
            "scenario_id": scenario_id,
            "scenario_order": len(rows) + 1,
            "scenario_family": scenario_family,
            "display_name": display_name,
            "is_baseline": scenario_id == baseline,
            "ranking_applicable": scenario_family in {"metric", "region"},
            "flag_applicable": True,
            "metric_mode": metric_mode,
            "component_groups_json": _json_list(component_groups),
            "active_anchor_ids_json": _json_list(anchors or all_anchors),
            "active_indicator_ids_json": _json_list(indicators or all_indicators),
            "region_policy_id": region_policy_id,
            "preferred_regions_json": _json_list(preferred_regions),
            "threshold_policy_id": threshold_policy_id,
            "aggregation_policy_id": aggregation_policy_id,
            "expected_effect": expected_effect,
            "schema_version": SCENARIO_SCHEMA_VERSION,
            "status": "ok",
            "issue": "",
        })

    for item in settings["metric_scenarios"]:
        mode = str(item["mode"])
        selected = list(item.get("component_groups", []))
        scenario_id = str(item["scenario_id"])
        effect = (
            "cross_model_rank_unchanged_by_design_flags_recomputed"
            if scenario_id == "without_uncertainty"
            else "metric_family_sensitivity"
        )
        add_row(
            scenario_id=scenario_id,
            scenario_family="metric",
            display_name=str(item["display_name"]),
            metric_mode=mode,
            component_groups=selected,
            anchors=_active_component_ids(config, mode=mode, selected_groups=selected, kind="anchor"),
            indicators=_active_component_ids(config, mode=mode, selected_groups=selected, kind="indicator"),
            expected_effect=effect,
        )

    for item in settings["region_scenarios"]:
        add_row(
            scenario_id=str(item["scenario_id"]),
            scenario_family="region",
            display_name=str(item["display_name"]),
            region_policy_id=str(item["region_policy_id"]),
            preferred_regions=list(item["preferred_regions"]),
            expected_effect="region_policy_sensitivity_with_explicit_missingness",
        )

    for item in settings["threshold_scenarios"]:
        add_row(
            scenario_id=str(item["scenario_id"]),
            scenario_family="threshold",
            display_name=str(item["display_name"]),
            threshold_policy_id=str(item["scenario_id"]),
            expected_effect="threshold_sensitivity_flags_only",
        )

    for item in settings["aggregation_scenarios"]:
        add_row(
            scenario_id=str(item["scenario_id"]),
            scenario_family="aggregation",
            display_name=str(item["display_name"]),
            aggregation_policy_id=str(item["scenario_id"]),
            expected_effect="aggregation_rule_sensitivity_flags_only",
        )

    result = pd.DataFrame(rows, columns=SCENARIO_COLUMNS)
    checks = validate_scenario_catalog(result, config=config)
    if not bool(checks["passed"].all()):
        raise ValueError(f"Invalid scenario catalogue: {checks.loc[~checks['passed']].to_dict('records')}")
    return result


def validate_scenario_catalog(
    frame: pd.DataFrame, *, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Validate scenario identities, ordering, families, and arithmetic."""

    _require_columns(frame, SCENARIO_COLUMNS, "scenario catalogue")
    settings = _settings(config)
    expected = settings["expected_counts"]
    baseline = settings["flag_stability"]["baseline_scenario_id"]
    checks = [
        ("scenario_row_count", len(frame) == int(expected["scenarios"]), f"observed={len(frame)}"),
        ("scenario_ids_unique", frame["scenario_id"].is_unique, f"unique={frame['scenario_id'].nunique()}"),
        ("scenario_order_exact", frame["scenario_order"].tolist() == list(range(1, len(frame) + 1)), "one-based contiguous order"),
        ("single_baseline", int(frame["is_baseline"].map(_as_bool).sum()) == 1, f"baseline_rows={int(frame['is_baseline'].map(_as_bool).sum())}"),
        ("baseline_identity", frame.loc[frame["is_baseline"].map(_as_bool), "scenario_id"].tolist() == [baseline], f"expected={baseline}"),
        ("scenario_families", set(frame["scenario_family"]) == SCENARIO_FAMILIES, f"observed={sorted(set(frame['scenario_family']))}"),
        ("ranking_scenario_count", int(frame["ranking_applicable"].map(_as_bool).sum()) == int(expected["ranking_scenarios"]), f"observed={int(frame['ranking_applicable'].map(_as_bool).sum())}"),
        ("schema_version", frame["schema_version"].eq(SCENARIO_SCHEMA_VERSION).all(), SCENARIO_SCHEMA_VERSION),
        ("status_ok", frame["status"].eq("ok").all(), f"bad={int(frame['status'].ne('ok').sum())}"),
    ]
    return pd.DataFrame(
        {
            "check_id": [item[0] for item in checks],
            "passed": [bool(item[1]) for item in checks],
            "details": [item[2] for item in checks],
        }
    )


def build_region_membership_table(
    region_policy: pd.DataFrame, *, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Explode N08's JSON ablation memberships into auditable policy rows."""

    required = (
        "policy_id", "metric_family", "region_id", "compatible",
        "ablation_policy_ids_json", "status",
    )
    _require_columns(region_policy, required, "N08 region policy")
    rows: list[dict[str, Any]] = []
    for record in region_policy.to_dict("records"):
        try:
            policy_ids = json.loads(str(record["ablation_policy_ids_json"]))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid ablation_policy_ids_json for {record['policy_id']}") from exc
        if not isinstance(policy_ids, list):
            raise ValueError("ablation_policy_ids_json must contain a JSON list")
        for ablation_policy_id in policy_ids:
            rows.append({
                "ablation_policy_id": str(ablation_policy_id),
                "policy_id": str(record["policy_id"]),
                "metric_family": str(record["metric_family"]),
                "region_id": str(record["region_id"]),
                "compatible": _as_bool(record["compatible"]),
                "status": str(record["status"]),
            })
    result = pd.DataFrame(rows)
    required_ids = set(_settings(config)["region_policy"]["required_policy_ids"])
    observed_ids = set(result["ablation_policy_id"])
    missing = sorted(required_ids - observed_ids)
    if missing:
        raise ValueError(f"N08 region policy is missing required ablation memberships: {missing}")
    return result.sort_values(
        ["ablation_policy_id", "metric_family", "region_id", "policy_id"]
    ).reset_index(drop=True)


def scenario_failure_config(
    base_failure_config: Mapping[str, Any],
    scenario: Mapping[str, Any],
    *,
    ablation_config: Mapping[str, Any],
    indicator_region_availability: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Return an isolated N27-compatible configuration for one flag scenario.

    Metric scenarios remove indicators. Threshold and aggregation scenarios
    change only their declared policy. Region scenarios require an availability
    table with ``indicator_id`` and ``region_id``; unavailable indicators are
    removed so missing evidence cannot silently become a pass.
    """

    result = copy.deepcopy(dict(base_failure_config))
    settings = result.get("failure_taxonomy", result)
    if not isinstance(settings, dict):
        raise TypeError("base_failure_config must contain mutable failure_taxonomy settings")
    scenario_id_value = scenario.get("scenario_id")
    if scenario_id_value is None or (
        not isinstance(scenario_id_value, (list, tuple, dict))
        and pd.isna(scenario_id_value)
    ):
        scenario_id_value = getattr(scenario, "name", "")
    scenario_id = str(scenario_id_value).strip()
    if not scenario_id:
        raise ValueError("scenario must provide scenario_id or use it as the row index")
    family = str(scenario["scenario_family"])

    active_ids = set(json.loads(str(scenario["active_indicator_ids_json"])))
    if family == "metric":
        settings["indicators"] = [
            item for item in settings["indicators"] if str(item["indicator_id"]) in active_ids
        ]

    if family == "region":
        if indicator_region_availability is None:
            raise ValueError("Region scenarios require indicator_region_availability")
        _require_columns(
            indicator_region_availability,
            ("indicator_id", "region_id"),
            "indicator region availability",
        )
        availability = indicator_region_availability.copy()
        if "available" in availability.columns:
            availability = availability.loc[availability["available"].map(_as_bool)]
        preferred = json.loads(str(scenario["preferred_regions_json"]))
        order = {str(region): index for index, region in enumerate(preferred)}
        availability = availability.loc[availability["region_id"].astype(str).isin(order)]
        availability = availability.assign(
            _region_order=availability["region_id"].astype(str).map(order)
        ).sort_values(["indicator_id", "_region_order"])
        chosen = (
            availability.drop_duplicates("indicator_id")
            .set_index("indicator_id")["region_id"].astype(str).to_dict()
        )
        rewritten = []
        for indicator in settings["indicators"]:
            indicator_id = str(indicator["indicator_id"])
            if indicator_id not in chosen:
                continue
            updated = dict(indicator)
            updated["region_id"] = chosen[indicator_id]
            rewritten.append(updated)
        settings["indicators"] = rewritten

    ablation_settings = _settings(ablation_config)
    if family == "threshold":
        source = next(
            item for item in ablation_settings["threshold_scenarios"]
            if str(item["scenario_id"]) == scenario_id
        )
        for key, value in source.items():
            if key not in {"scenario_id", "display_name"}:
                settings["threshold_policy"][key] = value
        settings["threshold_policy_id"] = f"ablation_{scenario_id}.v1"

    if family == "aggregation":
        source = next(
            item for item in ablation_settings["aggregation_scenarios"]
            if str(item["scenario_id"]) == scenario_id
        )
        settings["threshold_policy"]["distinct_warning_components_required"] = int(
            source["distinct_warning_components_required"]
        )
        settings["threshold_policy"]["one_critical_triggers"] = bool(
            source["one_critical_triggers"]
        )
        settings["threshold_policy_id"] = f"ablation_{scenario_id}.v1"

    return result


def _flag_key_checks(frame: pd.DataFrame, label: str) -> None:
    _require_columns(
        frame,
        (
            "candidate_id", "case_id", "painting_id", "model_id",
            "experiment_id", "prompt_variant_id", "population_role", "flag_id",
            "flag_status", "flag_severity",
        ),
        label,
    )
    if frame.duplicated(["candidate_id", "flag_id"]).any():
        raise ValueError(f"{label} has duplicate candidate/flag keys")
    bad_states = sorted(set(frame["flag_status"].astype(str)) - FLAG_STATES)
    if bad_states:
        raise ValueError(f"{label} has unsupported flag states: {bad_states}")


def build_flag_stability(
    baseline_flags: pd.DataFrame,
    scenario_flags: pd.DataFrame,
    *,
    scenario_id: str,
    scenario_family: str,
) -> pd.DataFrame:
    """Create one compact flag-stability row per candidate and scenario."""

    _flag_key_checks(baseline_flags, "baseline flags")
    _flag_key_checks(scenario_flags, "scenario flags")
    if scenario_family not in SCENARIO_FAMILIES:
        raise ValueError(f"Unsupported scenario family: {scenario_family}")

    key = ["candidate_id", "flag_id"]
    metadata = [
        "case_id", "painting_id", "model_id", "experiment_id",
        "prompt_variant_id", "population_role",
    ]
    left = baseline_flags[key + metadata + ["flag_status", "flag_severity"]].copy()
    right = scenario_flags[key + ["flag_status", "flag_severity"]].copy()
    merged = left.merge(
        right,
        on=key,
        how="outer",
        validate="one_to_one",
        suffixes=("_baseline", "_scenario"),
        indicator=True,
    )
    if not merged["_merge"].eq("both").all():
        counts = merged["_merge"].value_counts().to_dict()
        raise ValueError(f"Baseline/scenario flag keys differ: {counts}")

    severity_order = {"not_assigned": 0, "none": 1, "warning": 2, "critical": 3}
    rows: list[dict[str, Any]] = []
    for candidate_id, group in merged.groupby("candidate_id", sort=True):
        baseline_status = group.set_index("flag_id")["flag_status_baseline"].astype(str)
        scenario_status = group.set_index("flag_id")["flag_status_scenario"].astype(str)
        changed = baseline_status.ne(scenario_status)
        baseline_triggered = set(baseline_status.index[baseline_status.eq("triggered")])
        scenario_triggered = set(scenario_status.index[scenario_status.eq("triggered")])
        newly_triggered = scenario_triggered - baseline_triggered
        no_longer_triggered = baseline_triggered - scenario_triggered
        baseline_insufficient = set(
            baseline_status.index[baseline_status.eq("insufficient_evidence")]
        )
        scenario_insufficient = set(
            scenario_status.index[scenario_status.eq("insufficient_evidence")]
        )
        union = baseline_triggered | scenario_triggered
        jaccard = 1.0 if not union else len(baseline_triggered & scenario_triggered) / len(union)

        transitions = []
        for record in group.to_dict("records"):
            before = str(record["flag_severity_baseline"])
            after = str(record["flag_severity_scenario"])
            delta = abs(severity_order.get(after, 0) - severity_order.get(before, 0))
            transitions.append((delta, str(record["flag_id"]), before, after))
        max_transition = max(transitions, default=(0, "", "", ""))
        max_transition_text = (
            "none" if max_transition[0] == 0
            else f"{max_transition[1]}:{max_transition[2]}_to_{max_transition[3]}"
        )

        reasons = []
        if newly_triggered:
            reasons.append("newly_triggered")
        if no_longer_triggered:
            reasons.append("no_longer_triggered")
        if scenario_insufficient - baseline_insufficient:
            reasons.append("new_insufficient_evidence")
        if baseline_insufficient - scenario_insufficient:
            reasons.append("resolved_insufficient_evidence")
        if not reasons and max_transition[0] > 0:
            reasons.append("severity_changed")
        if not reasons:
            reasons.append("unchanged")

        first = group.iloc[0]
        rows.append({
            "stability_id": _stable_id("flagstability", scenario_id, candidate_id),
            "scenario_id": scenario_id,
            "scenario_family": scenario_family,
            "candidate_id": str(candidate_id),
            "case_id": str(first["case_id"]),
            "painting_id": str(first["painting_id"]),
            "model_id": str(first["model_id"]),
            "experiment_id": str(first["experiment_id"]),
            "prompt_variant_id": "" if pd.isna(first["prompt_variant_id"]) else str(first["prompt_variant_id"]),
            "population_role": str(first["population_role"]),
            "baseline_triggered_flag_count": len(baseline_triggered),
            "scenario_triggered_flag_count": len(scenario_triggered),
            "baseline_critical_flag_count": int(group["flag_severity_baseline"].astype(str).eq("critical").sum()),
            "scenario_critical_flag_count": int(group["flag_severity_scenario"].astype(str).eq("critical").sum()),
            "baseline_insufficient_flag_count": len(baseline_insufficient),
            "scenario_insufficient_flag_count": len(scenario_insufficient),
            "unchanged_flag_count": int((~changed).sum()),
            "changed_flag_count": int(changed.sum()),
            "flag_state_agreement_fraction": float((~changed).mean()),
            "triggered_jaccard": float(jaccard),
            "newly_triggered_flag_ids_json": _json_list(newly_triggered),
            "no_longer_triggered_flag_ids_json": _json_list(no_longer_triggered),
            "new_insufficient_flag_ids_json": _json_list(scenario_insufficient - baseline_insufficient),
            "resolved_insufficient_flag_ids_json": _json_list(baseline_insufficient - scenario_insufficient),
            "changed_flag_ids_json": _json_list(changed.index[changed]),
            "max_severity_transition": max_transition_text,
            "change_reason": "|".join(reasons),
            "schema_version": FLAG_STABILITY_SCHEMA_VERSION,
            "status": "ok",
            "issue": "",
        })
    return pd.DataFrame(rows, columns=FLAG_STABILITY_COLUMNS)


def empty_ablation_results() -> pd.DataFrame:
    return pd.DataFrame(columns=ABLATION_RESULT_COLUMNS)


def coerce_ablation_results(records: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    """Coerce heterogeneous validated result records to the canonical schema."""

    frame = pd.DataFrame(list(records))
    for column in ABLATION_RESULT_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    frame = frame.loc[:, ABLATION_RESULT_COLUMNS].copy()
    missing_ids = frame["result_id"].isna() | frame["result_id"].astype(str).eq("")
    if missing_ids.any():
        frame.loc[missing_ids, "result_id"] = [
            _stable_id(
                "ablation",
                row.scenario_id,
                row.result_kind,
                row.analysis_scope,
                row.scope_value,
                row.entity_type,
                row.entity_id,
                row.model_id,
                row.flag_id,
            )
            for row in frame.loc[missing_ids].itertuples(index=False)
        ]
    frame["schema_version"] = ABLATION_RESULTS_SCHEMA_VERSION
    frame["status"] = frame["status"].fillna("ok").replace("", "ok")
    frame["issue"] = frame["issue"].fillna("")
    return frame


def validate_flag_stability(
    frame: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    require_complete: bool = True,
) -> pd.DataFrame:
    """Validate the compact candidate/scenario stability table."""

    _require_columns(frame, FLAG_STABILITY_COLUMNS, "flag stability")
    expected = _settings(config)["expected_counts"]
    expected_rows = int(expected["flag_stability_rows"])
    expected_candidates = int(expected["flag_candidates"])
    expected_scenarios = int(expected["scenarios"])
    checks = [
        ("flag_stability_rows", (len(frame) == expected_rows) if require_complete else (len(frame) <= expected_rows), f"observed={len(frame)} expected={expected_rows}"),
        ("flag_stability_key_unique", not frame.duplicated(["scenario_id", "candidate_id"]).any(), f"duplicates={int(frame.duplicated(['scenario_id', 'candidate_id']).sum())}"),
        ("candidate_count", frame["candidate_id"].nunique() == expected_candidates if require_complete else frame["candidate_id"].nunique() <= expected_candidates, f"observed={frame['candidate_id'].nunique()}"),
        ("scenario_count", frame["scenario_id"].nunique() == expected_scenarios if require_complete else frame["scenario_id"].nunique() <= expected_scenarios, f"observed={frame['scenario_id'].nunique()}"),
        ("agreement_bounds", pd.to_numeric(frame["flag_state_agreement_fraction"], errors="coerce").between(0, 1).all(), "expected=[0,1]"),
        ("jaccard_bounds", pd.to_numeric(frame["triggered_jaccard"], errors="coerce").between(0, 1).all(), "expected=[0,1]"),
        ("changed_count_bounds", pd.to_numeric(frame["changed_flag_count"], errors="coerce").between(0, int(expected["trust_flags"])).all(), f"expected=[0,{expected['trust_flags']}]"),
        ("schema_version", frame["schema_version"].eq(FLAG_STABILITY_SCHEMA_VERSION).all(), FLAG_STABILITY_SCHEMA_VERSION),
        ("status_ok", frame["status"].eq("ok").all(), f"bad={int(frame['status'].ne('ok').sum())}"),
    ]
    return pd.DataFrame({
        "check_id": [item[0] for item in checks],
        "passed": [bool(item[1]) for item in checks],
        "details": [item[2] for item in checks],
    })


def validate_ablation_results(
    frame: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    require_complete: bool = True,
) -> pd.DataFrame:
    """Validate canonical ablation-result structure and prohibited outputs."""

    _require_columns(frame, ABLATION_RESULT_COLUMNS, "ablation results")
    expected = _settings(config)["expected_counts"]
    minimum = int(expected["minimum_ablation_result_rows"])
    result_kinds = set(frame["result_kind"].dropna().astype(str))
    forbidden = {kind for kind in result_kinds if "trust_score" in kind or "universal_score" in kind}
    checks = [
        ("minimum_result_rows", (len(frame) >= minimum) if require_complete else True, f"observed={len(frame)} minimum={minimum}"),
        ("result_id_unique", frame["result_id"].is_unique, f"unique={frame['result_id'].nunique()}"),
        ("scenario_ids_present", frame["scenario_id"].astype(str).str.len().gt(0).all(), "non-empty"),
        ("no_universal_score", not forbidden, f"forbidden={sorted(forbidden)}"),
        ("winner_retention_boolean_or_missing", frame["winner_retained"].dropna().map(lambda value: isinstance(value, (bool, np.bool_)) or str(value).lower() in {"true", "false"}).all(), "boolean or missing"),
        ("schema_version", frame["schema_version"].eq(ABLATION_RESULTS_SCHEMA_VERSION).all(), ABLATION_RESULTS_SCHEMA_VERSION),
        ("status_ok", frame["status"].eq("ok").all(), f"bad={int(frame['status'].ne('ok').sum())}"),
    ]
    return pd.DataFrame({
        "check_id": [item[0] for item in checks],
        "passed": [bool(item[1]) for item in checks],
        "details": [item[2] for item in checks],
    })


def validate_ablation_report_html(
    html: str, *, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Validate mock fidelity, embedded media, and standalone report structure."""

    report = _settings(config)["report"]
    section_ids = list(report["required_section_ids"])
    image_sources = re.findall(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", html, flags=re.I)
    embedded_sources = [source for source in image_sources if source.startswith("data:image/")]
    external_sources = [source for source in image_sources if not source.startswith("data:image/")]
    checks = [
        ("report_nonempty", len(html.encode("utf-8")) > 1000, f"bytes={len(html.encode('utf-8'))}"),
        ("report_title", str(report["title"]) in html and str(report["subtitle"]) in html, "title and subtitle"),
        ("required_sections", all(re.search(rf"\bid=[\"']{re.escape(section_id)}[\"']", html) for section_id in section_ids), f"required={len(section_ids)}"),
        ("section_order", [html.find(f'id="{section_id}"') if f'id="{section_id}"' in html else html.find(f"id='{section_id}'") for section_id in section_ids] == sorted([html.find(f'id="{section_id}"') if f'id="{section_id}"' in html else html.find(f"id='{section_id}'") for section_id in section_ids]), "approved order"),
        ("embedded_images", len(embedded_sources) >= int(report["diagnostic_tile_count"]) + int(report["canonical_figure_count"]), f"embedded={len(embedded_sources)}"),
        ("no_external_images", len(external_sources) == int(report["external_image_dependency_count"]), f"external={external_sources[:5]}"),
        ("analytical_views", len(re.findall(r"data-analytical-view=", html)) >= int(report["minimum_embedded_analytical_views"]), f"observed={len(re.findall(r'data-analytical-view=', html))}"),
        ("diagnostic_panels", len(re.findall(r"data-diagnostic-panel=", html)) >= int(report["diagnostic_panel_count"]), f"observed={len(re.findall(r'data-diagnostic-panel=', html))}"),
        ("no_file_uri", "file://" not in html.lower(), "file URI prohibited"),
        ("no_universal_trust_score_claim", "universal trust score" not in html.lower() or "no universal trust score" in html.lower(), "prohibited affirmative claim"),
    ]
    return pd.DataFrame({
        "check_id": [item[0] for item in checks],
        "passed": [bool(item[1]) for item in checks],
        "details": [item[2] for item in checks],
    })


def atomic_write_csv(
    frame: pd.DataFrame,
    output_path: str | Path,
    *,
    attempts: int = 5,
    retry_seconds: float = 0.2,
) -> Path:
    """Persist a CSV using a unique temporary file and bounded Windows retries."""

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(
        f".{target.name}.{os.getpid()}.{time.time_ns()}.tmp"
    )
    frame.to_csv(temporary, index=False)
    try:
        for attempt in range(attempts):
            try:
                os.replace(temporary, target)
                return target
            except PermissionError:
                if attempt + 1 >= attempts:
                    raise
                time.sleep(retry_seconds * (attempt + 1))
    finally:
        if temporary.exists():
            temporary.unlink()
    return target
