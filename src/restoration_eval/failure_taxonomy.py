"""Transparent failure-taxonomy utilities for Notebook 27.

The module turns validated evidence from Notebooks 13--26 into auditable,
candidate-level screening assignments and independent trustworthiness flags. It
does not run restoration or feature inference, does not write into frozen
upstream output roots, and does not construct a combined trust score.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml

from .grouped_statistical_analysis import select_primary_candidate_population
from .paths import find_project_root, resolve_repo_path


MODULE_NAME = "restoration_eval.failure_taxonomy"
MODULE_VERSION = "1.0.1"
CONFIG_SCHEMA_VERSION = "failure_taxonomy_config.v1"
TAXONOMY_SCHEMA_VERSION = "failure_taxonomy.v1"
ASSIGNMENT_SCHEMA_VERSION = "failure_assignments.v1"
FLAG_SCHEMA_VERSION = "trustworthiness_flags.v1"

ASSIGNMENT_STATES = frozenset(
    {"triggered", "not_triggered", "insufficient_evidence", "not_applicable"}
)
RULE_SEVERITIES = frozenset({"none", "warning", "critical", "not_assigned"})
RECOMMENDATIONS = (
    "do_not_rely_automatically",
    "unstable_candidate",
    "specialist_review_required",
    "suitable_for_preliminary_inspection",
)

TAXONOMY_COLUMNS = (
    "category_id", "display_name", "definition", "is_proxy",
    "applicable_to", "indicator_ids_json", "evidence_families_json",
    "affected_regions_json", "threshold_policy_id", "trigger_rule",
    "severity_interpretation", "recommended_action", "limitations",
    "schema_version", "status", "issue",
)

EVIDENCE_COLUMNS = (
    "evidence_id", "candidate_id", "uncertainty_group_id", "case_id",
    "painting_id", "model_id", "experiment_id", "prompt_variant_id",
    "population_role", "source_notebook_id", "source_row_ids_json",
    "source", "evidence_family", "indicator_id", "component", "metric_name",
    "feature_model_id", "region_id", "summary_statistic", "direction",
    "raw_value", "adverse_value", "threshold_mode", "schema_version",
    "status", "issue",
)

THRESHOLD_COLUMNS = (
    "threshold_id", "indicator_id", "experiment_id", "prompt_variant_id",
    "region_id", "summary_statistic", "direction", "threshold_mode",
    "fitting_scope", "n_fitting_candidates", "n_fitting_groups",
    "favourable_threshold", "warning_threshold", "critical_threshold",
    "threshold_policy_id", "interpretation", "status", "issue",
)

FAILURE_ASSIGNMENT_COLUMNS = (
    "assignment_id", "candidate_id", "case_id", "painting_id", "model_id",
    "experiment_id", "prompt_variant_id", "population_role", "category_id",
    "category_name", "assignment_status", "rule_severity", "trigger_rule",
    "triggered_indicator_count", "warning_indicator_count",
    "critical_indicator_count", "required_evidence_count",
    "available_evidence_count", "evidence_coverage_status",
    "indicator_states_json", "supporting_evidence_ids_json",
    "source_notebook_ids_json", "affected_regions_json",
    "threshold_summary_json", "observed_value_summary_json", "explanation",
    "recommended_action", "is_proxy_category", "threshold_policy_id",
    "schema_version", "status", "issue",
)

TRUSTWORTHINESS_FLAG_COLUMNS = (
    "flag_assignment_id", "candidate_id", "case_id", "painting_id",
    "model_id", "experiment_id", "prompt_variant_id", "population_role",
    "flag_id", "flag_name", "flag_status", "flag_severity",
    "triggering_rule", "supporting_category_ids_json",
    "supporting_assignment_ids_json", "supporting_evidence_ids_json",
    "source_notebook_ids_json", "affected_regions_json",
    "evidence_coverage_status", "explanation", "recommended_action",
    "recommendation_category", "manual_review_required",
    "is_combined_score", "schema_version", "status", "issue",
)

SOURCE_ROW_ID_COLUMNS = {
    "classical": "metric_row_id",
    "perceptual": "metric_row_id",
    "feature": "metric_row_id",
    "spatial": "spatial_diagnostic_id",
    "local": "local_consistency_id",
    "semantic": "semantic_metric_id",
    "uncertainty": "uncertainty_metric_id",
}

FAILURE_DEFINITIONS = {
    "residual_masked_error": "Reference error remains high inside the intended repair region.",
    "excessive_blur": "Local edges or surface variation are reduced beyond the operational screening threshold.",
    "structural_collapse_proxy": "Feature-affinity evidence indicates a possible loss or displacement of structural layout.",
    "semantic_inconsistency_proxy": "Local feature evidence is less compatible with the clean reference inside the repair crop.",
    "repeated_texture_proxy": "Periodicity or generated-detail evidence indicates potentially artificial repeated texture.",
    "texture_smoothing": "Local texture variation appears flatter than the clean reference.",
    "texture_discontinuity": "Texture or gradient behaviour changes abruptly across the repaired area or boundary.",
    "colour_bleeding_proxy": "Colour discontinuity or spillover evidence indicates possible colour transfer across the boundary.",
    "colour_drift": "Colour difference evidence is adverse inside the repaired region.",
    "boundary_seam": "Gradient, orientation, or local-structure evidence indicates a visible repair transition.",
    "mask_spillover": "The restoration changes pixels immediately outside the intended repair support.",
    "outside_mask_alteration": "Pixels outside the intended mask change beyond the approved numerical tolerance.",
    "composition_change_proxy": "Global or outside-context feature evidence indicates possible broader layout change.",
    "unstable_multi_seed_completion": "Repeated stochastic candidates vary materially across independent evidence families.",
}


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    settings = config.get("failure_taxonomy", config)
    if not isinstance(settings, Mapping):
        raise TypeError("failure_taxonomy settings must be a mapping")
    return settings


def _stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join("" if part is None else str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20]}"


def _json_list(values: Iterable[Any]) -> str:
    normalized = sorted({str(value) for value in values if pd.notna(value) and str(value)})
    return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))


def _json_object(value: Mapping[str, Any]) -> str:
    clean = {
        str(key): (None if pd.isna(item) else item.item() if hasattr(item, "item") else item)
        for key, item in value.items()
    }
    return json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _require_columns(frame: pd.DataFrame, columns: Sequence[str], label: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing columns: {missing}")


def _normalized_relative_path(value: Any) -> bool:
    text = str(value).strip()
    return bool(text) and not Path(text).is_absolute() and "\\" not in text


def _bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0).ne(0)
    def normalize(value: Any) -> bool:
        if value is None or (not isinstance(value, (list, tuple, dict)) and pd.isna(value)):
            return False
        if isinstance(value, (bool, np.bool_)):
            return bool(value)
        if isinstance(value, (int, float, np.number)):
            return bool(float(value))
        return str(value).strip().lower() in {"true", "1", "1.0", "yes", "y"}

    return series.map(normalize)


def load_failure_taxonomy_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the approved Notebook 27 contract."""

    with Path(path).open("r", encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Failure-taxonomy configuration must be a mapping")
    if config.get("config_schema_version") != CONFIG_SCHEMA_VERSION:
        raise ValueError("Unsupported failure-taxonomy config schema")
    settings = _settings(config)
    required = {
        "notebook_id", "notebook_stem", "taxonomy_schema_version",
        "assignment_schema_version", "flag_schema_version", "inputs", "output",
        "population", "threshold_policy", "indicators", "failure_categories",
        "trust_flags", "recommendation_priority", "report", "expected_counts",
        "evidence_policy", "known_limitations",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"Failure-taxonomy config is missing keys: {missing}")
    if settings["notebook_id"] != "27" or settings["notebook_stem"] != "27_failure_taxonomy_and_trustworthiness_flags":
        raise ValueError("Notebook 27 identity contract changed")
    versions = (
        ("taxonomy_schema_version", TAXONOMY_SCHEMA_VERSION),
        ("assignment_schema_version", ASSIGNMENT_SCHEMA_VERSION),
        ("flag_schema_version", FLAG_SCHEMA_VERSION),
    )
    for key, expected in versions:
        if settings[key] != expected:
            raise ValueError(f"Configured {key} does not match helper")
    for key, value in settings["inputs"].items():
        if not _normalized_relative_path(value):
            raise ValueError(f"inputs.{key} must be a normalized repository-relative path")

    exact_output = {
        "root": "outputs/27_failure_taxonomy_and_trustworthiness_flags",
        "taxonomy_path": "data/failure_taxonomy.csv",
        "assignments_path": "metrics/failure_assignments.csv",
        "flags_path": "metrics/trustworthiness_flags.csv",
        "figure_path": "figures/failure_taxonomy.png",
        "report_path": "reports/flag_definitions.html",
        "run_manifest_path": "manifests/run_manifest.json",
        "artifacts_path": "manifests/artifacts.csv",
        "validation_path": "validation/checks.csv",
    }
    for key, expected in exact_output.items():
        if settings["output"].get(key) != expected:
            raise ValueError(f"output.{key} must equal {expected!r}")

    indicators = settings["indicators"]
    indicator_ids = [str(item["indicator_id"]) for item in indicators]
    if len(indicator_ids) != len(set(indicator_ids)):
        raise ValueError("Indicator IDs must be unique")
    required_indicator_fields = {
        "indicator_id", "source", "source_notebook_id", "metric_name",
        "region_id", "summary_statistic", "value_column", "direction", "component",
    }
    for item in indicators:
        fields_missing = sorted(required_indicator_fields - set(item))
        if fields_missing:
            raise ValueError(f"Indicator {item.get('indicator_id')} is missing {fields_missing}")
        if item["direction"] not in {"higher_is_worse", "lower_is_worse"}:
            raise ValueError(f"Unsupported direction for {item['indicator_id']}")

    categories = settings["failure_categories"]
    category_ids = [str(item["category_id"]) for item in categories]
    if len(category_ids) != 14 or len(set(category_ids)) != 14:
        raise ValueError("Exactly fourteen unique failure categories are required")
    unknown = sorted(
        {
            indicator_id
            for category in categories
            for indicator_id in category["indicator_ids"]
            if indicator_id not in indicator_ids
        }
    )
    if unknown:
        raise ValueError(f"Failure categories reference unknown indicators: {unknown}")
    flag_ids = [str(item["flag_id"]) for item in settings["trust_flags"]]
    if len(flag_ids) != 11 or len(set(flag_ids)) != 11:
        raise ValueError("Exactly eleven unique trust flags are required")
    if list(settings["recommendation_priority"]) != list(RECOMMENDATIONS):
        raise ValueError("Recommendation priority changed")

    policy = settings["threshold_policy"]
    if not 0 < float(policy["warning_quantile"]) < float(policy["critical_quantile"]) < 1:
        raise ValueError("Higher-is-worse threshold quantiles are invalid")
    if not 0 < float(policy["lower_is_worse_critical_quantile"]) < float(policy["lower_is_worse_warning_quantile"]) < 1:
        raise ValueError("Lower-is-worse threshold quantiles are invalid")
    report = settings["report"]
    if not bool(report["self_contained_html"]) or not bool(report["approved_mock_structure_locked"]):
        raise ValueError("The approved self-contained report structure must remain locked")
    if len(report["required_section_ids"]) != 15 or len(set(report["required_section_ids"])) != 15:
        raise ValueError("Report must retain the approved fifteen-section structure")

    expected = settings["expected_counts"]
    arithmetic = {
        "primary_candidates": int(expected["primary_core_candidates"]) + int(expected["bounded_sdxl_candidates"]),
        "repeated_seed_candidates": int(expected["canonical_uncertainty_candidates"]) + int(expected["damage_size_uncertainty_candidates"]),
        "uncertainty_only_candidates": int(expected["repeated_seed_candidates"]) - int(expected["primary_repeated_overlap"]),
        "union_candidates": int(expected["primary_candidates"]) + int(expected["uncertainty_only_candidates"]),
        "failure_assignment_rows": int(expected["union_candidates"]) * int(expected["failure_categories"]),
        "trustworthiness_flag_rows": int(expected["union_candidates"]) * int(expected["trust_flags"]),
    }
    for key, value in arithmetic.items():
        if int(expected[key]) != value:
            raise ValueError(f"Expected-count arithmetic is inconsistent for {key}")
    if int(expected["canonical_output_files"]) != 8 or int(expected["artifact_records"]) != 6:
        raise ValueError("Canonical output or artifact count changed")
    if bool(settings["evidence_policy"]["combined_trust_score_retained"]):
        raise ValueError("A combined trust score is prohibited")
    if bool(settings["evidence_policy"]["missing_evidence_may_count_as_pass"]):
        raise ValueError("Missing evidence may not count as passing evidence")
    return config


def resolve_failure_taxonomy_inputs(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
    *,
    must_exist: bool = True,
) -> dict[str, Path]:
    """Resolve every declared input without dynamic discovery."""

    root = find_project_root(project_root)
    return {
        str(key): resolve_repo_path(value, root, must_exist=must_exist)
        for key, value in _settings(config)["inputs"].items()
    }


def validate_upstream_completion(
    manifests: Mapping[str, Mapping[str, Any]],
    *,
    expected_notebook_ids: Sequence[str] = tuple(f"{number:02d}" for number in range(13, 27)),
) -> pd.DataFrame:
    """Return one completion-gate row for every analytical dependency."""

    rows: list[dict[str, Any]] = []
    for notebook_id in expected_notebook_ids:
        payload = manifests.get(notebook_id)
        present = isinstance(payload, Mapping)
        row = {
            "notebook_id": notebook_id,
            "manifest_present": present,
            "run_status": str(payload.get("run_status", "")) if present else "",
            "validation_status": str(payload.get("validation_status", "")) if present else "",
            "completion_gate_passed": bool(payload.get("completion_gate_passed", False)) if present else False,
        }
        row["passed"] = bool(
            row["manifest_present"]
            and row["run_status"] == "completed"
            and row["validation_status"] == "passed"
            and row["completion_gate_passed"]
        )
        rows.append(row)
    return pd.DataFrame(rows)


def uncertainty_candidate_ids(frame: pd.DataFrame) -> set[str]:
    """Return every candidate referenced by seed and pairwise uncertainty rows."""

    _require_columns(frame, ("candidate_id", "candidate_id_a", "candidate_id_b"), "uncertainty metrics")
    values: set[str] = set()
    for column in ("candidate_id", "candidate_id_a", "candidate_id_b"):
        values.update(frame[column].dropna().astype(str))
    return {value for value in values if value}


def uncertainty_group_memberships(frame: pd.DataFrame) -> pd.DataFrame:
    """Explode all group-member candidate IDs from uncertainty evidence."""

    _require_columns(
        frame,
        (
            "uncertainty_group_id", "candidate_id", "candidate_id_a", "candidate_id_b",
            "case_id", "model_id", "experiment_id", "prompt_variant_id",
        ),
        "uncertainty metrics",
    )
    rows: list[dict[str, Any]] = []
    metadata_columns = [
        column for column in (
            "uncertainty_group_id", "case_id", "painting_id", "category",
            "style_or_period", "dataset_id", "dataset_scope", "experiment_id",
            "damage_or_degradation_type", "target_damage_fraction",
            "realized_damage_fraction", "model_id", "configuration_id",
            "prompt_policy_id", "prompt_variant_id", "seed_count",
            "expected_seed_count", "seed_coverage_status",
        ) if column in frame.columns
    ]
    for _, row in frame.iterrows():
        metadata = {column: row[column] for column in metadata_columns}
        for column in ("candidate_id", "candidate_id_a", "candidate_id_b"):
            value = row.get(column)
            if pd.notna(value) and str(value):
                rows.append({**metadata, "candidate_id": str(value)})
    if not rows:
        return pd.DataFrame(columns=[*metadata_columns, "candidate_id"])
    result = pd.DataFrame(rows).drop_duplicates(["uncertainty_group_id", "candidate_id"])
    return result.sort_values(["uncertainty_group_id", "candidate_id"]).reset_index(drop=True)


def build_failure_candidate_population(
    case_registry: pd.DataFrame,
    artworks: pd.DataFrame,
    opencv_candidates: pd.DataFrame,
    lama_candidates: pd.DataFrame,
    stable_diffusion_candidates: pd.DataFrame,
    sdxl_candidates: pd.DataFrame,
    damage_size_extension_candidates: pd.DataFrame,
    canonical_uncertainty: pd.DataFrame,
    damage_size_uncertainty: pd.DataFrame,
    *,
    grouped_config: Mapping[str, Any],
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the exact primary-plus-supported-uncertainty candidate union."""

    settings = _settings(config)
    expected = settings["expected_counts"]
    primary = select_primary_candidate_population(
        case_registry,
        artworks,
        opencv_candidates,
        lama_candidates,
        stable_diffusion_candidates,
        sdxl_candidates,
        config=grouped_config,
    ).copy()
    canonical_members = uncertainty_group_memberships(canonical_uncertainty)
    damage_members = uncertainty_group_memberships(damage_size_uncertainty)
    repeated = pd.concat(
        [
            canonical_members.assign(uncertainty_source="notebook_18"),
            damage_members.assign(uncertainty_source="notebook_22"),
        ],
        ignore_index=True,
    )
    repeated_ids = set(repeated["candidate_id"].astype(str))
    primary_ids = set(primary["candidate_id"].astype(str))

    source_candidates = pd.concat(
        [stable_diffusion_candidates, damage_size_extension_candidates],
        ignore_index=True,
        sort=False,
    ).drop_duplicates("candidate_id", keep="first")
    uncertainty_only_ids = repeated_ids - primary_ids
    uncertainty_only = source_candidates.loc[
        source_candidates["candidate_id"].astype(str).isin(uncertainty_only_ids)
    ].copy()
    missing = sorted(uncertainty_only_ids - set(uncertainty_only["candidate_id"].astype(str)))
    if missing:
        raise ValueError(f"Uncertainty-only candidates lack candidate records: {missing[:5]}")

    desired_columns = sorted(set(primary.columns) | set(uncertainty_only.columns))
    primary = primary.reindex(columns=desired_columns)
    uncertainty_only = uncertainty_only.reindex(columns=desired_columns)
    population = pd.concat([primary, uncertainty_only], ignore_index=True, sort=False)
    population["candidate_id"] = population["candidate_id"].astype(str)
    population["is_primary_candidate"] = population["candidate_id"].isin(primary_ids)
    population["is_uncertainty_candidate"] = population["candidate_id"].isin(repeated_ids)
    population["population_role"] = np.select(
        [
            population["model_id"].astype(str).eq("sdxl_inpainting"),
            population["is_primary_candidate"] & population["is_uncertainty_candidate"],
            population["is_primary_candidate"],
            population["is_uncertainty_candidate"],
        ],
        [
            "bounded_sdxl", "primary_and_uncertainty", "primary_comparison",
            "uncertainty_only",
        ],
        default="unsupported",
    )
    group_lookup = (
        repeated.groupby("candidate_id", dropna=False)
        .agg(
            uncertainty_group_ids=("uncertainty_group_id", lambda values: _json_list(values)),
            uncertainty_sources=("uncertainty_source", lambda values: _json_list(values)),
        )
        .reset_index()
    )
    population = population.merge(group_lookup, on="candidate_id", how="left")
    population["uncertainty_group_ids"] = population["uncertainty_group_ids"].fillna("[]")
    population["uncertainty_sources"] = population["uncertainty_sources"].fillna("[]")

    for column, default in (
        ("quality_analysis_eligible", False),
        ("is_zero_control", False),
        ("prompt_variant_id", pd.NA),
        ("seed", pd.NA),
        ("style_or_period", pd.NA),
        ("dataset_id", "controlled_50"),
        ("dataset_scope", "controlled_50"),
        ("target_damage_fraction", pd.NA),
        ("realized_damage_fraction", pd.NA),
    ):
        if column not in population.columns:
            population[column] = default
    population["quality_analysis_eligible"] = _bool_series(population["quality_analysis_eligible"])
    population["is_zero_control"] = _bool_series(population["is_zero_control"])
    population.loc[population["population_role"].eq("uncertainty_only"), "quality_analysis_eligible"] = False
    population["population_id"] = settings["population"]["union_population_id"]

    if population["candidate_id"].duplicated().any():
        raise ValueError("Candidate population contains duplicate candidate IDs")
    actual = {
        "primary_candidates": int(population["is_primary_candidate"].sum()),
        "repeated_seed_candidates": int(population["is_uncertainty_candidate"].sum()),
        "primary_repeated_overlap": int((population["is_primary_candidate"] & population["is_uncertainty_candidate"]).sum()),
        "uncertainty_only_candidates": int(population["population_role"].eq("uncertainty_only").sum()),
        "union_candidates": len(population),
    }
    for key, value in actual.items():
        if value != int(expected[key]):
            raise ValueError(f"Population count {key}={value}, expected {expected[key]}")
    return population.sort_values(["population_role", "model_id", "case_id", "candidate_id"]).reset_index(drop=True)


def build_failure_taxonomy(config: Mapping[str, Any]) -> pd.DataFrame:
    """Create the canonical fourteen-row rule-definition table."""

    settings = _settings(config)
    indicators = {item["indicator_id"]: item for item in settings["indicators"]}
    limitations = " ".join(settings["known_limitations"][:3])
    rows: list[dict[str, Any]] = []
    for category in settings["failure_categories"]:
        selected = [indicators[indicator_id] for indicator_id in category["indicator_ids"]]
        rows.append(
            {
                "category_id": category["category_id"],
                "display_name": category["display_name"],
                "definition": FAILURE_DEFINITIONS[category["category_id"]],
                "is_proxy": bool(category["is_proxy"]),
                "applicable_to": category["applicable_to"],
                "indicator_ids_json": _json_list(category["indicator_ids"]),
                "evidence_families_json": _json_list(item["source"] for item in selected),
                "affected_regions_json": _json_list(item["region_id"] for item in selected),
                "threshold_policy_id": settings["threshold_policy_id"],
                "trigger_rule": "one critical indicator or two distinct warning components",
                "severity_interpretation": settings["threshold_policy"]["severity_interpretation"],
                "recommended_action": category["recommended_action"],
                "limitations": limitations,
                "schema_version": TAXONOMY_SCHEMA_VERSION,
                "status": "ok",
                "issue": "",
            }
        )
    return pd.DataFrame(rows, columns=TAXONOMY_COLUMNS)


def _source_frame_for_indicator(
    indicator: Mapping[str, Any],
    sources: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    source = str(indicator["source"])
    frame = sources[source].copy()
    _require_columns(frame, ("candidate_id",), f"{source} evidence")
    if "status" in frame.columns:
        frame = frame.loc[frame["status"].astype(str).eq("ok")].copy()
    if source != "spatial":
        _require_columns(frame, ("metric_name",), f"{source} evidence")
        frame = frame.loc[frame["metric_name"].astype(str).eq(str(indicator["metric_name"]))]
    if "region_id" in frame.columns:
        frame = frame.loc[frame["region_id"].astype(str).eq(str(indicator["region_id"]))]
    if "summary_statistic" in frame.columns:
        frame = frame.loc[
            frame["summary_statistic"].astype(str).eq(str(indicator["summary_statistic"]))
        ]
    feature_model_id = indicator.get("feature_model_id")
    if feature_model_id and "feature_model_id" in frame.columns:
        frame = frame.loc[frame["feature_model_id"].astype(str).eq(str(feature_model_id))]
    _require_columns(frame, (str(indicator["value_column"]),), f"{source} evidence")
    return frame


def normalise_failure_evidence(
    sources: Mapping[str, pd.DataFrame],
    candidate_population: pd.DataFrame,
    canonical_uncertainty: pd.DataFrame,
    damage_size_uncertainty: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Normalize selected scalar and group uncertainty indicators."""

    settings = _settings(config)
    population_columns = [
        "candidate_id", "case_id", "painting_id", "model_id", "experiment_id",
        "prompt_variant_id", "population_role",
    ]
    _require_columns(candidate_population, population_columns, "candidate population")
    population = candidate_population[population_columns].drop_duplicates("candidate_id")
    records: list[dict[str, Any]] = []

    for indicator in settings["indicators"]:
        if indicator["source"] == "uncertainty":
            continue
        frame = _source_frame_for_indicator(indicator, sources)
        if frame.empty:
            continue
        frame = frame.merge(population, on="candidate_id", how="inner", suffixes=("", "_population"))
        row_id_column = SOURCE_ROW_ID_COLUMNS[str(indicator["source"])]
        _require_columns(frame, (row_id_column,), f"{indicator['indicator_id']} evidence")
        for _, row in frame.iterrows():
            value = pd.to_numeric(pd.Series([row[indicator["value_column"]]]), errors="coerce").iloc[0]
            if not np.isfinite(value):
                continue
            direction = str(indicator["direction"])
            records.append(
                {
                    "evidence_id": _stable_id("evidence", row["candidate_id"], indicator["indicator_id"], row[row_id_column]),
                    "candidate_id": str(row["candidate_id"]),
                    "uncertainty_group_id": pd.NA,
                    "case_id": row.get("case_id_population", row.get("case_id", pd.NA)),
                    "painting_id": row.get("painting_id_population", row.get("painting_id", pd.NA)),
                    "model_id": row.get("model_id_population", row.get("model_id", pd.NA)),
                    "experiment_id": row.get("experiment_id_population", row.get("experiment_id", pd.NA)),
                    "prompt_variant_id": row.get("prompt_variant_id_population", row.get("prompt_variant_id", pd.NA)),
                    "population_role": row["population_role"],
                    "source_notebook_id": str(indicator["source_notebook_id"]),
                    "source_row_ids_json": _json_list([row[row_id_column]]),
                    "source": str(indicator["source"]),
                    "evidence_family": str(indicator["source"]),
                    "indicator_id": str(indicator["indicator_id"]),
                    "component": str(indicator["component"]),
                    "metric_name": str(indicator["metric_name"]),
                    "feature_model_id": str(indicator.get("feature_model_id", "")),
                    "region_id": str(indicator["region_id"]),
                    "summary_statistic": str(indicator["summary_statistic"]),
                    "direction": direction,
                    "raw_value": float(value),
                    "adverse_value": float(value if direction == "higher_is_worse" else -value),
                    "threshold_mode": str(indicator.get("threshold_mode", "quantile")),
                    "schema_version": "failure_evidence.v1",
                    "status": "ok",
                    "issue": "",
                }
            )

    uncertainty_frames = [
        ("18", canonical_uncertainty),
        ("22", damage_size_uncertainty),
    ]
    for source_notebook_id, uncertainty in uncertainty_frames:
        memberships = uncertainty_group_memberships(uncertainty)
        for indicator in settings["indicators"]:
            if indicator["source"] != "uncertainty":
                continue
            frame = uncertainty.copy()
            if "status" in frame.columns:
                frame = frame.loc[frame["status"].astype(str).eq("ok")]
            frame = frame.loc[
                frame["metric_name"].astype(str).eq(str(indicator["metric_name"]))
                & frame["region_id"].astype(str).eq(str(indicator["region_id"]))
            ].copy()
            if "summary_statistic" in frame.columns:
                requested = str(indicator["summary_statistic"])
                matching = frame["summary_statistic"].astype(str).eq(requested)
                if matching.any():
                    frame = frame.loc[matching]
            frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
            frame = frame.loc[np.isfinite(frame["value"])].copy()
            if frame.empty:
                continue
            aggregation = str(indicator.get("source_aggregation", "median"))
            if aggregation != "median":
                raise ValueError(f"Unsupported uncertainty aggregation: {aggregation}")
            group_values = (
                frame.groupby("uncertainty_group_id", dropna=False)
                .agg(
                    raw_value=("value", "median"),
                    source_row_ids_json=("uncertainty_metric_id", lambda values: _json_list(values)),
                )
                .reset_index()
            )
            exploded = memberships.merge(group_values, on="uncertainty_group_id", how="inner")
            exploded = exploded.merge(population, on="candidate_id", how="inner", suffixes=("", "_population"))
            direction = str(indicator["direction"])
            for _, row in exploded.iterrows():
                value = float(row["raw_value"])
                records.append(
                    {
                        "evidence_id": _stable_id("evidence", row["candidate_id"], row["uncertainty_group_id"], indicator["indicator_id"]),
                        "candidate_id": str(row["candidate_id"]),
                        "uncertainty_group_id": str(row["uncertainty_group_id"]),
                        "case_id": row.get("case_id_population", row.get("case_id", pd.NA)),
                        "painting_id": row.get("painting_id_population", row.get("painting_id", pd.NA)),
                        "model_id": row.get("model_id_population", row.get("model_id", pd.NA)),
                        "experiment_id": row.get("experiment_id_population", row.get("experiment_id", pd.NA)),
                        "prompt_variant_id": row.get("prompt_variant_id_population", row.get("prompt_variant_id", pd.NA)),
                        "population_role": row["population_role"],
                        "source_notebook_id": source_notebook_id,
                        "source_row_ids_json": row["source_row_ids_json"],
                        "source": "uncertainty",
                        "evidence_family": "uncertainty",
                        "indicator_id": str(indicator["indicator_id"]),
                        "component": str(indicator["component"]),
                        "metric_name": str(indicator["metric_name"]),
                        "feature_model_id": "",
                        "region_id": str(indicator["region_id"]),
                        "summary_statistic": str(indicator["summary_statistic"]),
                        "direction": direction,
                        "raw_value": value,
                        "adverse_value": value if direction == "higher_is_worse" else -value,
                        "threshold_mode": str(indicator.get("threshold_mode", "quantile")),
                        "schema_version": "failure_evidence.v1",
                        "status": "ok",
                        "issue": "",
                    }
                )
    result = pd.DataFrame(records, columns=EVIDENCE_COLUMNS)
    if result.empty:
        return result
    duplicate_key = ["candidate_id", "indicator_id", "uncertainty_group_id"]
    if result.duplicated(duplicate_key).any():
        duplicates = result.loc[result.duplicated(duplicate_key, keep=False), duplicate_key]
        raise ValueError(f"Normalized evidence is not unique: {duplicates.head().to_dict('records')}")
    return result.sort_values(["candidate_id", "indicator_id"]).reset_index(drop=True)


def calibrate_operational_thresholds(
    evidence: pd.DataFrame,
    candidate_population: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Fit transparent warning, critical, and favourable screening thresholds."""

    _require_columns(evidence, EVIDENCE_COLUMNS, "normalized evidence")
    settings = _settings(config)
    policy = settings["threshold_policy"]
    population = candidate_population[
        ["candidate_id", "quality_analysis_eligible", "is_zero_control"]
    ].drop_duplicates("candidate_id")
    joined = evidence.merge(population, on="candidate_id", how="left")
    rows: list[dict[str, Any]] = []
    for indicator_id, indicator_rows in joined.groupby("indicator_id", sort=True):
        is_uncertainty = indicator_rows["source"].astype(str).eq("uncertainty").all()
        if is_uncertainty:
            fitting = indicator_rows.drop_duplicates(["uncertainty_group_id", "indicator_id"])
            prompt_values = sorted(fitting["prompt_variant_id"].dropna().astype(str).unique())
            strata = [(experiment, prompt) for experiment in sorted(fitting["experiment_id"].astype(str).unique()) for prompt in prompt_values]
        else:
            fitting = indicator_rows.loc[
                _bool_series(indicator_rows["quality_analysis_eligible"])
                & ~_bool_series(indicator_rows["is_zero_control"])
                & ~indicator_rows["model_id"].astype(str).eq("sdxl_inpainting")
            ].copy()
            strata = [(experiment, "") for experiment in sorted(indicator_rows["experiment_id"].astype(str).unique())]
        for experiment_id, prompt_variant_id in strata:
            subset = fitting.loc[fitting["experiment_id"].astype(str).eq(experiment_id)].copy()
            if is_uncertainty:
                subset = subset.loc[subset["prompt_variant_id"].astype(str).eq(prompt_variant_id)]
            if subset.empty:
                continue
            threshold_mode = str(subset["threshold_mode"].iloc[0])
            direction = str(subset["direction"].iloc[0])
            values = pd.to_numeric(subset["raw_value"], errors="coerce")
            values = values.loc[np.isfinite(values)]
            fitting_scope = "experiment_prompt" if is_uncertainty else "experiment"
            if len(values) < int(policy["minimum_fitting_candidates"]):
                fallback = fitting.loc[fitting["indicator_id"].eq(indicator_id)]
                if is_uncertainty:
                    fallback = fallback.loc[fallback["prompt_variant_id"].astype(str).eq(prompt_variant_id)]
                values = pd.to_numeric(fallback["raw_value"], errors="coerce")
                values = values.loc[np.isfinite(values)]
                fitting_scope = "approved_fallback"
            if values.empty:
                continue
            if threshold_mode == "absolute_tolerance":
                favourable = 0.0
                warning = float(policy["outside_mask_absolute_warning_tolerance"])
                critical = float(policy["outside_mask_absolute_critical_tolerance"])
            elif direction == "higher_is_worse":
                favourable = float(values.quantile(float(policy["favourable_quantile"])))
                warning = float(values.quantile(float(policy["warning_quantile"])))
                critical = float(values.quantile(float(policy["critical_quantile"])))
            else:
                favourable = float(values.quantile(float(policy["lower_is_worse_favourable_quantile"])))
                warning = float(values.quantile(float(policy["lower_is_worse_warning_quantile"])))
                critical = float(values.quantile(float(policy["lower_is_worse_critical_quantile"])))
            first = subset.iloc[0]
            rows.append(
                {
                    "threshold_id": _stable_id("threshold", indicator_id, experiment_id, prompt_variant_id),
                    "indicator_id": indicator_id,
                    "experiment_id": experiment_id,
                    "prompt_variant_id": prompt_variant_id,
                    "region_id": first["region_id"],
                    "summary_statistic": first["summary_statistic"],
                    "direction": direction,
                    "threshold_mode": threshold_mode,
                    "fitting_scope": fitting_scope,
                    "n_fitting_candidates": int(len(values)),
                    "n_fitting_groups": int(subset["uncertainty_group_id"].nunique()) if is_uncertainty else 0,
                    "favourable_threshold": favourable,
                    "warning_threshold": warning,
                    "critical_threshold": critical,
                    "threshold_policy_id": settings["threshold_policy_id"],
                    "interpretation": policy["threshold_interpretation"],
                    "status": "ok",
                    "issue": "",
                }
            )
    return pd.DataFrame(rows, columns=THRESHOLD_COLUMNS).sort_values(
        ["indicator_id", "experiment_id", "prompt_variant_id"]
    ).reset_index(drop=True)


def classify_evidence_against_thresholds(
    evidence: pd.DataFrame,
    thresholds: pd.DataFrame,
) -> pd.DataFrame:
    """Attach favourable, neutral, warning, or critical states to evidence."""

    _require_columns(evidence, EVIDENCE_COLUMNS, "normalized evidence")
    _require_columns(thresholds, THRESHOLD_COLUMNS, "threshold table")
    rows: list[pd.DataFrame] = []
    for _, threshold in thresholds.iterrows():
        subset = evidence.loc[
            evidence["indicator_id"].eq(threshold["indicator_id"])
            & evidence["experiment_id"].astype(str).eq(str(threshold["experiment_id"]))
        ].copy()
        if str(threshold["prompt_variant_id"]):
            subset = subset.loc[
                subset["prompt_variant_id"].astype(str).eq(str(threshold["prompt_variant_id"]))
            ]
        if subset.empty:
            continue
        value = pd.to_numeric(subset["raw_value"], errors="coerce")
        threshold_mode = str(threshold["threshold_mode"])
        if threshold["direction"] == "higher_is_worse":
            if threshold_mode == "quantile":
                # Strict adverse comparisons prevent a tied floor value (for
                # example, a zero-valued 97.5th percentile) from classifying
                # every zero observation as critical.
                critical = value > float(threshold["critical_threshold"])
                warning = value > float(threshold["warning_threshold"])
            else:
                critical = value >= float(threshold["critical_threshold"])
                warning = value >= float(threshold["warning_threshold"])
            favourable = value <= float(threshold["favourable_threshold"])
        else:
            if threshold_mode == "quantile":
                # The mirrored strict comparison provides the same protection
                # when a lower-is-worse metric is tied at its ceiling.
                critical = value < float(threshold["critical_threshold"])
                warning = value < float(threshold["warning_threshold"])
            else:
                critical = value <= float(threshold["critical_threshold"])
                warning = value <= float(threshold["warning_threshold"])
            favourable = value >= float(threshold["favourable_threshold"])
        subset["evidence_state"] = np.select(
            [critical, warning, favourable],
            ["critical", "warning", "favourable"],
            default="neutral",
        )
        for column in (
            "threshold_id", "favourable_threshold", "warning_threshold",
            "critical_threshold", "threshold_policy_id",
        ):
            subset[column] = threshold[column]
        rows.append(subset)
    if not rows:
        return evidence.assign(
            evidence_state=pd.Series(dtype="object"),
            threshold_id=pd.Series(dtype="object"),
            favourable_threshold=pd.Series(dtype="float64"),
            warning_threshold=pd.Series(dtype="float64"),
            critical_threshold=pd.Series(dtype="float64"),
            threshold_policy_id=pd.Series(dtype="object"),
        ).iloc[0:0]
    result = pd.concat(rows, ignore_index=True)
    if result.duplicated(["evidence_id"]).any():
        raise ValueError("Evidence matched more than one threshold stratum")
    return result.sort_values(["candidate_id", "indicator_id"]).reset_index(drop=True)


def _category_applicability(
    candidate: Mapping[str, Any],
    category_id: str,
) -> str:
    if category_id != "unstable_multi_seed_completion":
        return "applicable"
    model_id = str(candidate.get("model_id", ""))
    if model_id in {"opencv_telea", "lama"}:
        return "not_applicable"
    if model_id == "sdxl_inpainting":
        return "insufficient_evidence"
    if not bool(candidate.get("is_uncertainty_candidate", False)):
        return "insufficient_evidence"
    return "applicable"


def build_failure_assignments(
    candidate_population: pd.DataFrame,
    classified_evidence: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the complete candidate-by-category assignment ledger."""

    settings = _settings(config)
    indicators = {item["indicator_id"]: item for item in settings["indicators"]}
    evidence_by_candidate = {
        candidate_id: group.copy()
        for candidate_id, group in classified_evidence.groupby("candidate_id", sort=False)
    }
    rows: list[dict[str, Any]] = []
    for _, candidate in candidate_population.iterrows():
        candidate_id = str(candidate["candidate_id"])
        candidate_evidence = evidence_by_candidate.get(candidate_id, classified_evidence.iloc[0:0])
        for category in settings["failure_categories"]:
            category_id = str(category["category_id"])
            applicable = _category_applicability(candidate, category_id)
            required_ids = list(category["indicator_ids"])
            selected = candidate_evidence.loc[
                candidate_evidence["indicator_id"].isin(required_ids)
            ].drop_duplicates("indicator_id")
            available_ids = set(selected["indicator_id"].astype(str))
            missing_ids = sorted(set(required_ids) - available_ids)
            warning = selected.loc[selected["evidence_state"].eq("warning")]
            critical = selected.loc[selected["evidence_state"].eq("critical")]
            warning_components = set(warning["component"].astype(str))
            triggered = bool(
                len(critical) >= 1
                or len(warning_components) >= int(settings["threshold_policy"]["distinct_warning_components_required"])
            )
            if applicable == "not_applicable":
                assignment_status, severity = "not_applicable", "not_assigned"
            elif applicable == "insufficient_evidence":
                assignment_status, severity = "insufficient_evidence", "not_assigned"
            elif triggered:
                assignment_status = "triggered"
                severity = "critical" if len(critical) else "warning"
            elif missing_ids:
                assignment_status, severity = "insufficient_evidence", "not_assigned"
            else:
                assignment_status, severity = "not_triggered", "none"
            coverage = (
                "not_applicable" if assignment_status == "not_applicable"
                else "complete" if not missing_ids
                else "partial" if len(selected) else "missing"
            )
            state_map = {
                indicator_id: (
                    selected.loc[selected["indicator_id"].eq(indicator_id), "evidence_state"].iloc[0]
                    if indicator_id in available_ids else "missing"
                )
                for indicator_id in required_ids
            }
            values = {
                str(row["indicator_id"]): float(row["raw_value"])
                for _, row in selected.iterrows()
            }
            thresholds = {
                str(row["indicator_id"]): {
                    "warning": float(row["warning_threshold"]),
                    "critical": float(row["critical_threshold"]),
                    "direction": str(row["direction"]),
                }
                for _, row in selected.iterrows()
            }
            if assignment_status == "triggered":
                explanation = f"{category['display_name']} triggered by {len(warning) + len(critical)} adverse indicator(s)."
            elif assignment_status == "not_triggered":
                explanation = "All required evidence was available and the operational trigger rule was not met."
            elif assignment_status == "not_applicable":
                explanation = "Stochastic seed variability is not applicable to this deterministic method."
            else:
                explanation = "The category cannot be treated as passing because required evidence is unavailable or incomplete."
            rows.append(
                {
                    "assignment_id": _stable_id("failure", candidate_id, category_id),
                    "candidate_id": candidate_id,
                    "case_id": candidate.get("case_id", pd.NA),
                    "painting_id": candidate.get("painting_id", pd.NA),
                    "model_id": candidate.get("model_id", pd.NA),
                    "experiment_id": candidate.get("experiment_id", pd.NA),
                    "prompt_variant_id": candidate.get("prompt_variant_id", pd.NA),
                    "population_role": candidate.get("population_role", pd.NA),
                    "category_id": category_id,
                    "category_name": category["display_name"],
                    "assignment_status": assignment_status,
                    "rule_severity": severity,
                    "trigger_rule": "one critical indicator or two distinct warning components",
                    "triggered_indicator_count": int(len(warning) + len(critical)),
                    "warning_indicator_count": int(len(warning)),
                    "critical_indicator_count": int(len(critical)),
                    "required_evidence_count": len(required_ids),
                    "available_evidence_count": len(available_ids),
                    "evidence_coverage_status": coverage,
                    "indicator_states_json": _json_object(state_map),
                    "supporting_evidence_ids_json": _json_list(selected["evidence_id"]),
                    "source_notebook_ids_json": _json_list(selected["source_notebook_id"]),
                    "affected_regions_json": _json_list(selected["region_id"]),
                    "threshold_summary_json": _json_object(thresholds),
                    "observed_value_summary_json": _json_object(values),
                    "explanation": explanation,
                    "recommended_action": category["recommended_action"],
                    "is_proxy_category": bool(category["is_proxy"]),
                    "threshold_policy_id": settings["threshold_policy_id"],
                    "schema_version": ASSIGNMENT_SCHEMA_VERSION,
                    "status": "ok",
                    "issue": "",
                }
            )
    return pd.DataFrame(rows, columns=FAILURE_ASSIGNMENT_COLUMNS)


def _severity_max(values: Iterable[Any]) -> str:
    order = {"not_assigned": 0, "none": 1, "warning": 2, "critical": 3}
    normalized = [str(value) for value in values]
    return max(normalized, key=lambda value: order.get(value, -1), default="not_assigned")


def build_trustworthiness_flags(
    candidate_population: pd.DataFrame,
    assignments: pd.DataFrame,
    classified_evidence: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build eleven independent flags and one transparent recommendation per candidate."""

    settings = _settings(config)
    assignment_groups = {
        candidate_id: group.copy()
        for candidate_id, group in assignments.groupby("candidate_id", sort=False)
    }
    evidence_groups = {
        candidate_id: group.copy()
        for candidate_id, group in classified_evidence.groupby("candidate_id", sort=False)
    }
    flag_definitions = {item["flag_id"]: item for item in settings["trust_flags"]}
    rows: list[dict[str, Any]] = []
    domain_flag_ids = {
        "semantic_inconsistency", "structural_inconsistency", "texture_inconsistency",
        "colour_inconsistency", "visible_boundary_artifact_proxy",
        "outside_mask_alteration", "high_generative_uncertainty",
    }
    for _, candidate in candidate_population.iterrows():
        candidate_id = str(candidate["candidate_id"])
        candidate_assignments = assignment_groups[candidate_id]
        candidate_evidence = evidence_groups.get(candidate_id, classified_evidence.iloc[0:0])
        candidate_flags: dict[str, dict[str, Any]] = {}
        for flag_id, definition in flag_definitions.items():
            if "source_categories" not in definition:
                continue
            selected = candidate_assignments.loc[
                candidate_assignments["category_id"].isin(definition["source_categories"])
            ]
            triggered = selected.loc[selected["assignment_status"].eq("triggered")]
            if not triggered.empty:
                flag_status = "triggered"
                severity = _severity_max(triggered["rule_severity"])
            elif selected["assignment_status"].eq("insufficient_evidence").any():
                flag_status, severity = "insufficient_evidence", "not_assigned"
            elif selected["assignment_status"].eq("not_triggered").any():
                flag_status, severity = "not_triggered", "none"
            else:
                flag_status, severity = "not_applicable", "not_assigned"
            candidate_flags[flag_id] = {
                "status": flag_status,
                "severity": severity,
                "assignments": selected,
                "rule": "triggered when any mapped failure category triggers",
            }

        uncertainty = candidate_evidence.loc[candidate_evidence["source"].eq("uncertainty")]
        uncertainty_adverse = uncertainty.loc[uncertainty["evidence_state"].isin(["warning", "critical"])]
        uncertainty_critical = uncertainty.loc[uncertainty["evidence_state"].eq("critical")]
        model_id = str(candidate.get("model_id", ""))
        if model_id in {"opencv_telea", "lama"}:
            instability_status, instability_severity = "not_applicable", "not_assigned"
        elif not bool(candidate.get("is_uncertainty_candidate", False)):
            instability_status, instability_severity = "insufficient_evidence", "not_assigned"
        elif len(set(uncertainty_adverse["component"].astype(str))) >= 3 or len(set(uncertainty_critical["component"].astype(str))) >= 2:
            instability_status = "triggered"
            instability_severity = "critical" if len(set(uncertainty_critical["component"].astype(str))) >= 2 else "warning"
        else:
            instability_status, instability_severity = "not_triggered", "none"
        candidate_flags["restoration_instability"] = {
            "status": instability_status,
            "severity": instability_severity,
            "assignments": candidate_assignments.loc[candidate_assignments["category_id"].eq("unstable_multi_seed_completion")],
            "rule": "at least three adverse uncertainty components or two critical uncertainty components",
        }

        adverse = candidate_evidence.loc[candidate_evidence["evidence_state"].isin(["warning", "critical"])]
        favourable = candidate_evidence.loc[candidate_evidence["evidence_state"].eq("favourable")]
        disagreement_triggered = (
            adverse["source"].nunique() >= 2 and favourable["source"].nunique() >= 2
        )
        candidate_flags["metric_disagreement"] = {
            "status": "triggered" if disagreement_triggered else "not_triggered",
            "severity": "warning" if disagreement_triggered else "none",
            "assignments": candidate_assignments.iloc[0:0],
            "rule": "at least two adverse and two favourable independent evidence families",
        }

        insufficient_assignments = candidate_assignments.loc[
            candidate_assignments["assignment_status"].eq("insufficient_evidence")
        ]
        insufficient_triggered = not insufficient_assignments.empty
        candidate_flags["insufficient_evidence"] = {
            "status": "triggered" if insufficient_triggered else "not_triggered",
            "severity": "warning" if insufficient_triggered else "none",
            "assignments": insufficient_assignments,
            "rule": "one or more applicable categories lack required evidence",
        }

        critical = candidate_assignments["rule_severity"].eq("critical").any()
        preliminary_domain_count = sum(
            candidate_flags[flag_id]["status"] == "triggered"
            for flag_id in domain_flag_ids
        )
        manual = bool(critical or preliminary_domain_count >= 2 or insufficient_triggered or instability_status == "triggered")
        candidate_flags["manual_review_required"] = {
            "status": "triggered" if manual else "not_triggered",
            "severity": "critical" if critical else "warning" if manual else "none",
            "assignments": candidate_assignments.loc[
                candidate_assignments["assignment_status"].isin(["triggered", "insufficient_evidence"])
            ],
            "rule": "critical assignment, multiple domain flags, instability, or consequential missing evidence",
        }

        critical_blockers = candidate_assignments.loc[
            candidate_assignments["rule_severity"].eq("critical")
            & candidate_assignments["category_id"].isin(
                ["outside_mask_alteration", "structural_collapse_proxy", "composition_change_proxy"]
            )
        ]
        if not critical_blockers.empty:
            recommendation = "do_not_rely_automatically"
        elif instability_status == "triggered":
            recommendation = "unstable_candidate"
        elif manual:
            recommendation = "specialist_review_required"
        else:
            recommendation = "suitable_for_preliminary_inspection"

        for flag_id in [item["flag_id"] for item in settings["trust_flags"]]:
            payload = candidate_flags[flag_id]
            selected = payload["assignments"]
            selected_evidence_ids: set[str] = set()
            for text in selected.get("supporting_evidence_ids_json", pd.Series(dtype="object")):
                try:
                    selected_evidence_ids.update(json.loads(text))
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass
            if flag_id == "metric_disagreement":
                selected_evidence_ids.update(adverse["evidence_id"].astype(str))
                selected_evidence_ids.update(favourable["evidence_id"].astype(str))
            if flag_id == "restoration_instability":
                selected_evidence_ids.update(uncertainty_adverse["evidence_id"].astype(str))
            supporting_evidence = candidate_evidence.loc[
                candidate_evidence["evidence_id"].astype(str).isin(selected_evidence_ids)
            ]
            status = str(payload["status"])
            if status == "triggered":
                explanation = f"{flag_definitions[flag_id]['display_name']} triggered under its documented screening rule."
            elif status == "not_triggered":
                explanation = "The documented trigger rule was not met by available evidence."
            elif status == "not_applicable":
                explanation = "This stochastic-variability flag is not applicable to the deterministic method."
            else:
                explanation = "Required evidence is incomplete, so the flag cannot be treated as passing."
            rows.append(
                {
                    "flag_assignment_id": _stable_id("flag", candidate_id, flag_id),
                    "candidate_id": candidate_id,
                    "case_id": candidate.get("case_id", pd.NA),
                    "painting_id": candidate.get("painting_id", pd.NA),
                    "model_id": candidate.get("model_id", pd.NA),
                    "experiment_id": candidate.get("experiment_id", pd.NA),
                    "prompt_variant_id": candidate.get("prompt_variant_id", pd.NA),
                    "population_role": candidate.get("population_role", pd.NA),
                    "flag_id": flag_id,
                    "flag_name": flag_definitions[flag_id]["display_name"],
                    "flag_status": status,
                    "flag_severity": payload["severity"],
                    "triggering_rule": payload["rule"],
                    "supporting_category_ids_json": _json_list(selected.get("category_id", [])),
                    "supporting_assignment_ids_json": _json_list(selected.get("assignment_id", [])),
                    "supporting_evidence_ids_json": _json_list(selected_evidence_ids),
                    "source_notebook_ids_json": _json_list(supporting_evidence.get("source_notebook_id", [])),
                    "affected_regions_json": _json_list(supporting_evidence.get("region_id", [])),
                    "evidence_coverage_status": "insufficient" if status == "insufficient_evidence" else "not_applicable" if status == "not_applicable" else "sufficient",
                    "explanation": explanation,
                    "recommended_action": recommendation.replace("_", " "),
                    "recommendation_category": recommendation,
                    "manual_review_required": manual,
                    "is_combined_score": False,
                    "schema_version": FLAG_SCHEMA_VERSION,
                    "status": "ok",
                    "issue": "",
                }
            )
    return pd.DataFrame(rows, columns=TRUSTWORTHINESS_FLAG_COLUMNS)


def _validation_rows(checks: Sequence[tuple[str, bool, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "check_id": check_id,
                "passed": bool(passed),
                "severity": "blocking",
                "detail": detail,
            }
            for check_id, passed, detail in checks
        ]
    )


def validate_failure_taxonomy(frame: pd.DataFrame, *, config: Mapping[str, Any]) -> pd.DataFrame:
    settings = _settings(config)
    checks = [
        ("taxonomy_columns", list(frame.columns) == list(TAXONOMY_COLUMNS), "Canonical column order"),
        ("taxonomy_rows", len(frame) == int(settings["expected_counts"]["failure_categories"]), "Exactly fourteen categories"),
        ("taxonomy_ids_unique", frame.get("category_id", pd.Series(dtype="object")).is_unique, "Category IDs are unique"),
        ("taxonomy_schema", frame.get("schema_version", pd.Series(dtype="object")).eq(TAXONOMY_SCHEMA_VERSION).all(), "Schema version is exact"),
        ("taxonomy_no_trust_score", not any("trust_score" in column for column in frame.columns), "No combined trust score"),
    ]
    return _validation_rows(checks)


def validate_failure_assignments(
    frame: pd.DataFrame,
    candidate_population: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    settings = _settings(config)
    expected_rows = int(settings["expected_counts"]["failure_assignment_rows"])
    expected_grid = len(candidate_population) * len(settings["failure_categories"])
    states = set(frame.get("assignment_status", pd.Series(dtype="object")).astype(str))
    checks = [
        ("assignment_columns", list(frame.columns) == list(FAILURE_ASSIGNMENT_COLUMNS), "Canonical column order"),
        ("assignment_rows", len(frame) == expected_rows == expected_grid, "Complete candidate-category grid"),
        ("assignment_ids_unique", frame.get("assignment_id", pd.Series(dtype="object")).is_unique, "Assignment IDs are unique"),
        ("assignment_pairs_unique", not frame.duplicated(["candidate_id", "category_id"]).any(), "Candidate-category pairs are unique"),
        ("assignment_states", states <= ASSIGNMENT_STATES, f"Allowed states only: {sorted(states)}"),
        ("assignment_schema", frame.get("schema_version", pd.Series(dtype="object")).eq(ASSIGNMENT_SCHEMA_VERSION).all(), "Schema version is exact"),
        ("missing_not_pass", not frame.loc[frame["evidence_coverage_status"].isin(["missing", "partial"]), "assignment_status"].eq("not_triggered").any(), "Missing evidence never passes"),
        ("trigger_has_evidence", frame.loc[frame["assignment_status"].eq("triggered"), "triggered_indicator_count"].gt(0).all(), "Triggered assignments cite adverse evidence"),
        ("assignment_no_trust_score", not any("trust_score" in column for column in frame.columns), "No combined trust score"),
    ]
    return _validation_rows(checks)


def validate_trustworthiness_flags(
    frame: pd.DataFrame,
    candidate_population: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    settings = _settings(config)
    expected_rows = int(settings["expected_counts"]["trustworthiness_flag_rows"])
    expected_grid = len(candidate_population) * len(settings["trust_flags"])
    states = set(frame.get("flag_status", pd.Series(dtype="object")).astype(str))
    recommendations = set(frame.get("recommendation_category", pd.Series(dtype="object")).astype(str))
    per_candidate_recommendations = frame.groupby("candidate_id")["recommendation_category"].nunique()
    checks = [
        ("flag_columns", list(frame.columns) == list(TRUSTWORTHINESS_FLAG_COLUMNS), "Canonical column order"),
        ("flag_rows", len(frame) == expected_rows == expected_grid, "Complete candidate-flag grid"),
        ("flag_ids_unique", frame.get("flag_assignment_id", pd.Series(dtype="object")).is_unique, "Flag assignment IDs are unique"),
        ("flag_pairs_unique", not frame.duplicated(["candidate_id", "flag_id"]).any(), "Candidate-flag pairs are unique"),
        ("flag_states", states <= ASSIGNMENT_STATES, f"Allowed states only: {sorted(states)}"),
        ("flag_schema", frame.get("schema_version", pd.Series(dtype="object")).eq(FLAG_SCHEMA_VERSION).all(), "Schema version is exact"),
        ("recommendations_allowed", recommendations <= set(RECOMMENDATIONS), "Only approved recommendation categories"),
        ("one_recommendation_per_candidate", per_candidate_recommendations.eq(1).all(), "Each candidate has one recommendation"),
        ("combined_score_false", ~_bool_series(frame.get("is_combined_score", pd.Series(dtype="bool"))).any(), "No combined score rows"),
        ("flag_no_trust_score", not any("trust_score" in column for column in frame.columns), "No combined trust score"),
    ]
    return _validation_rows(checks)


def validate_flag_report_html(html: str, *, config: Mapping[str, Any]) -> pd.DataFrame:
    """Validate the approved report structure, portability, and scope language."""

    settings = _settings(config)
    report = settings["report"]
    lower = html.lower()
    sections = list(report["required_section_ids"])
    section_checks = [
        (f"report_section_{section}", bool(re.search(rf'id=[\"\']{re.escape(section)}[\"\']', html, re.IGNORECASE)), f"Section {section} is present")
        for section in sections
    ]
    image_count = len(re.findall(r"<img\b", html, re.IGNORECASE))
    embedded_count = len(re.findall(r"src=[\"\']data:image/", html, re.IGNORECASE))
    checks = [
        ("report_html_document", "<html" in lower and "</html>" in lower, "Complete HTML document"),
        ("report_self_contained_images", image_count == embedded_count, "Every visible image is embedded"),
        ("report_image_density", image_count >= int(report["minimum_embedded_images"]), "Approved minimum embedded images"),
        ("report_rq_traceability", all(rq.lower() in lower for rq in report["required_research_questions"]), "RQ1-RQ3 appear"),
        ("report_no_trust_score", "combined trust score" not in lower or "not used" in lower or "prohibited" in lower, "No retained combined trust score"),
        ("report_uncertainty_limit", "not calibrated confidence" in lower, "Uncertainty limitation is explicit"),
        ("report_decision_support", "decision support" in lower or "decision-support" in lower, "Decision-support scope is explicit"),
        ("report_no_approval_claim", "not conservation approval" in lower or "does not constitute conservation approval" in lower, "No conservation approval claim"),
        ("report_population", "1,785" in html or "1785" in html, "Union population is stated"),
        ("report_proxy_language", "proxy" in lower, "Proxy terminology is visible"),
    ]
    return _validation_rows([*section_checks, *checks])
