"""Grouped statistical-analysis utilities for Notebook 26.

The module joins validated evidence produced by Notebooks 08--25, selects the
metric-independent primary candidate population, and provides deterministic
statistical and output-validation helpers.  It performs no restoration or
feature-model inference and never writes to frozen upstream output roots.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from itertools import product
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml
from scipy.stats import friedmanchisquare, kruskal, pearsonr, spearmanr

from .damage_size_analysis import (
    benjamini_hochberg,
    family_balanced_ranks,
    matched_rank_biserial,
)
from .multi_model_comparison import (
    normalise_runtime_evidence,
    normalise_spatial_diagnostics,
    normalise_standard_metric_table,
)
from .paths import find_project_root, resolve_repo_path


MODULE_NAME = "restoration_eval.grouped_statistical_analysis"
MODULE_VERSION = "1.0.0"
CONFIG_SCHEMA_VERSION = "grouped_statistical_analysis_config.v1"
STATISTICAL_RESULTS_SCHEMA_VERSION = "grouped_statistical_results.v1"
CORRELATION_SCHEMA_VERSION = "grouped_metric_correlations.v1"
RANKING_STABILITY_SCHEMA_VERSION = "grouped_ranking_stability.v1"

QUALITY_SOURCE_KEYS = (
    "classical",
    "perceptual",
    "feature",
    "spatial",
    "local_consistency",
    "semantic_structural",
)
STANDARD_SOURCE_KEYS = tuple(key for key in QUALITY_SOURCE_KEYS if key != "spatial")

STATISTICAL_RESULT_COLUMNS = (
    "result_id", "result_kind", "analysis_family_id", "source_notebook_ids",
    "source_row_ids_json", "experiment_id", "scope_type", "scope_value",
    "evidence_family", "metric_name", "feature_model_id", "region_id",
    "summary_statistic", "comparison_direction", "model_id",
    "comparison_model_id", "painting_id", "category",
    "damage_or_degradation_type", "target_damage_fraction", "population_id",
    "independent_unit", "n_paintings", "n_cases", "n_candidates",
    "n_observations", "estimate_name", "estimate", "ci_lower", "ci_upper",
    "effect_size_name", "effect_size", "test_statistic", "p_value", "q_value",
    "test_method", "bootstrap_method", "bootstrap_resamples",
    "applicability_status", "interpretation_status", "schema_version", "status",
    "issue",
)

CORRELATION_COLUMNS = (
    "correlation_id", "correlation_kind", "analysis_family_id",
    "source_notebook_ids", "experiment_id", "scope_type", "scope_value",
    "left_evidence_family", "left_metric_name", "left_region_id",
    "right_evidence_family", "right_metric_name", "right_region_id",
    "model_id", "comparison_model_id", "independent_unit", "n_paintings",
    "n_cases", "n_observations", "correlation_method", "correlation",
    "p_value", "q_value", "rank_reversal_fraction", "agreement_status",
    "applicability_status", "interpretation_status", "schema_version", "status",
    "issue",
)

RANKING_STABILITY_COLUMNS = (
    "ranking_id", "ranking_kind", "analysis_family_id", "source_notebook_ids",
    "experiment_id", "scope_type", "scope_value", "omitted_unit_type",
    "omitted_unit_id", "evidence_family", "region_policy_id", "model_id",
    "baseline_rank", "sensitivity_rank", "rank_change", "winner_model_id",
    "winner_retained", "winner_frequency", "kendalls_tau", "spearman_rho",
    "independent_unit", "n_paintings", "n_cases", "n_candidates",
    "bootstrap_resamples", "applicability_status", "interpretation_status",
    "schema_version", "status", "issue",
)


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    settings = config.get("grouped_statistical_analysis", config)
    if not isinstance(settings, Mapping):
        raise TypeError("grouped_statistical_analysis settings must be a mapping")
    return settings


def _stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join("" if part is None else str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20]}"


def _bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    return series.fillna(False).map(
        lambda value: str(value).strip().lower() in {"true", "1", "yes", "y"}
    )


def _require_columns(frame: pd.DataFrame, columns: Sequence[str], label: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing columns: {missing}")


def _normalized_relative_path(value: Any) -> bool:
    text = str(value).strip()
    return bool(text) and not Path(text).is_absolute() and "\\" not in text


def load_grouped_statistical_analysis_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the approved Notebook 26 contract."""

    with Path(path).open("r", encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Grouped statistical configuration must be a mapping")
    if config.get("config_schema_version") != CONFIG_SCHEMA_VERSION:
        raise ValueError("Unsupported grouped statistical config schema")
    settings = _settings(config)
    required = {
        "notebook_id", "notebook_stem", "statistical_results_schema_version",
        "correlation_schema_version", "ranking_stability_schema_version", "inputs",
        "output", "population", "evidence_sources", "metric_direction",
        "spatial_metric_fields", "quality_anchors", "required_disagreement_pairs",
        "uncertainty", "statistics", "statistical_result_kinds",
        "correlation_kinds", "ranking_stability_kinds", "report", "expected_counts",
        "evidence_policy", "known_limitations",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"Grouped statistical config is missing keys: {missing}")
    if settings["notebook_id"] != "26" or settings["notebook_stem"] != "26_grouped_and_statistical_analysis":
        raise ValueError("Notebook 26 identity contract changed")
    versions = (
        ("statistical_results_schema_version", STATISTICAL_RESULTS_SCHEMA_VERSION),
        ("correlation_schema_version", CORRELATION_SCHEMA_VERSION),
        ("ranking_stability_schema_version", RANKING_STABILITY_SCHEMA_VERSION),
    )
    for key, expected_version in versions:
        if settings[key] != expected_version:
            raise ValueError(f"Configured {key} does not match helper")
    for key, value in settings["inputs"].items():
        if not _normalized_relative_path(value):
            raise ValueError(f"inputs.{key} must be a normalized repository-relative path")

    exact_output = {
        "root": "outputs/26_grouped_and_statistical_analysis",
        "statistical_results_path": "metrics/statistical_results.csv",
        "metric_correlations_path": "metrics/metric_correlations.csv",
        "ranking_stability_path": "metrics/ranking_stability.csv",
        "correlation_figure_path": "figures/correlation_matrix.png",
        "grouped_performance_figure_path": "figures/grouped_performance.png",
        "effect_sizes_figure_path": "figures/effect_sizes.png",
        "report_path": "reports/statistical_analysis.html",
        "run_manifest_path": "manifests/run_manifest.json",
        "artifacts_path": "manifests/artifacts.csv",
        "validation_path": "validation/checks.csv",
    }
    for key, value in exact_output.items():
        if settings["output"].get(key) != value:
            raise ValueError(f"output.{key} must equal {value!r}")

    expected = settings["expected_counts"]
    if int(expected["selected_candidates"]) != int(expected["primary_core_candidates"]) + int(expected["bounded_sdxl_candidates"]):
        raise ValueError("Selected-candidate arithmetic is inconsistent")
    if int(expected["primary_core_candidates"]) != 3 * int(expected["evaluated_cases"]):
        raise ValueError("Core candidate arithmetic is inconsistent")
    if int(expected["quality_core_candidates"]) != 3 * int(expected["quality_cases"]):
        raise ValueError("Quality candidate arithmetic is inconsistent")
    if int(expected["mapped_nonzero_candidates_with_sdxl"]) * int(expected["quality_anchors"]) != int(expected["all_nonzero_anchor_rows_with_sdxl"]):
        raise ValueError("Quality-anchor arithmetic is inconsistent")
    source_rows = sum(int(expected[key]) for key in (
        "selected_classical_source_rows", "selected_lpips_source_rows",
        "selected_feature_source_rows", "normalized_spatial_rows",
        "selected_local_source_rows", "selected_semantic_source_rows",
    ))
    if source_rows != int(expected["normalized_quality_rows"]):
        raise ValueError("Normalized-evidence arithmetic is inconsistent")
    if int(settings["uncertainty"]["canonical_group_count"]) + int(settings["uncertainty"]["damage_size_group_count"]) != int(settings["uncertainty"]["combined_group_count"]):
        raise ValueError("Uncertainty-group arithmetic is inconsistent")
    anchors = [str(item["anchor_id"]) for item in settings["quality_anchors"]]
    if len(anchors) != int(expected["quality_anchors"]) or len(anchors) != len(set(anchors)):
        raise ValueError("Quality-anchor count or identity is inconsistent")
    if settings["population"]["dataset_source_levels"] != ["controlled_50"]:
        raise ValueError("Notebook 26 supports exactly one dataset source")
    if any(bool(settings["statistics"][key]) for key in (
        "combined_quality_score_retained", "combined_efficiency_score_retained",
        "combined_uncertainty_score_retained", "combined_trust_score_retained",
    )):
        raise ValueError("Combined quality, efficiency, uncertainty, and trust scores are prohibited")
    report = settings["report"]
    if not bool(report["self_contained_html"]) or not bool(report["approved_mock_structure_locked"]):
        raise ValueError("The approved self-contained report structure must remain locked")
    if len(report["required_section_ids"]) != 15 or len(set(report["required_section_ids"])) != 15:
        raise ValueError("Report must retain the approved fifteen-section structure")
    if int(expected["canonical_output_files"]) != 10 or int(expected["artifact_records"]) != 8:
        raise ValueError("Canonical output or artifact count changed")
    return config


def resolve_analysis_inputs(
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


def build_multi_model_adapter_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Expose the shared metric normalizer contract under its expected key."""

    settings = _settings(config)
    return {"multi_model_comparison": {
        "evidence_sources": settings["evidence_sources"],
        "metric_direction": settings["metric_direction"],
        "spatial_metric_fields": settings["spatial_metric_fields"],
        "disagreement_anchors": settings["quality_anchors"],
        "report": settings["report"],
    }}


def validate_upstream_run_manifests(
    manifests: Mapping[str, Mapping[str, Any]],
    *,
    expected_notebook_ids: Sequence[str] = (
        "01", "08", "09", "10", "11", "12", "13", "14", "15", "16",
        "17", "18", "19", "20", "21", "22", "23", "24", "25",
    ),
) -> pd.DataFrame:
    """Return one completion-gate row for each direct upstream producer."""

    records: list[dict[str, Any]] = []
    for notebook_id in expected_notebook_ids:
        manifest = manifests.get(str(notebook_id))
        present = isinstance(manifest, Mapping)
        records.append({
            "notebook_id": str(notebook_id),
            "manifest_present": present,
            "run_status": str(manifest.get("run_status", "")) if present else "",
            "validation_status": str(manifest.get("validation_status", "")) if present else "",
            "completion_gate_passed": bool(manifest.get("completion_gate_passed", False)) if present else False,
        })
    result = pd.DataFrame(records)
    result["passed"] = (
        result["manifest_present"]
        & result["run_status"].eq("completed")
        & result["validation_status"].eq("passed")
        & result["completion_gate_passed"]
    )
    return result


def _normalise_restored_path(value: Any, notebook_id: str) -> str:
    text = "" if value is None or pd.isna(value) else str(value).strip()
    text = text.replace("\\", "/")
    if text.startswith("images/"):
        roots = {
            "09": "outputs/09_opencv_telea_restoration",
            "10": "outputs/10_lama_restoration",
            "11": "outputs/11_stable_diffusion_restoration",
            "12": "outputs/12_sdxl_feasibility_or_restoration",
        }
        return f"{roots[notebook_id]}/{text}"
    return text


def _candidate_subset(
    frame: pd.DataFrame,
    *,
    model_id: str,
    notebook_id: str,
    completed_status: str = "completed",
) -> pd.DataFrame:
    _require_columns(frame, ("case_id", "candidate_id", "model_id", "restored_path", "runtime_seconds", "status"), model_id)
    subset = frame.loc[
        frame["model_id"].astype(str).eq(model_id)
        & frame["status"].astype(str).eq(completed_status)
    ].copy()
    subset["source_notebook_id"] = notebook_id
    return subset


def select_primary_candidate_population(
    case_registry: pd.DataFrame,
    artworks: pd.DataFrame,
    opencv: pd.DataFrame,
    lama: pd.DataFrame,
    stable_diffusion: pd.DataFrame,
    sdxl: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select 1,230 core primary candidates plus the bounded ten-case SDXL set."""

    settings = _settings(config)
    population = settings["population"]
    expected = settings["expected_counts"]
    _require_columns(case_registry, (
        "case_id", "dataset_id", "dataset_scope", "experiment_id", "painting_id",
        "input_image_path", "clean_image_path", "mask_or_effect_path",
        "damage_or_degradation_type", "target_damage_fraction",
        "realized_damage_fraction", "status",
    ), "case registry")
    _require_columns(artworks, ("painting_id", "category", "style_or_period"), "artworks")
    cases = case_registry.loc[case_registry["status"].astype(str).eq("passed")].copy()
    registry_case_counts = cases.groupby("experiment_id").size().to_dict()
    expected_registry_counts = {
        "canonical_missing_region": 250,
        "damage_size_sensitivity": 35,
        "mask_robustness": 75,
        "synthetic_degradation": 165,
    }
    if registry_case_counts != expected_registry_counts:
        raise ValueError(
            "Notebook 08 passed-case registry changed: "
            f"{registry_case_counts} != {expected_registry_counts}"
        )

    opencv_selected = _candidate_subset(opencv, model_id="opencv_telea", notebook_id="09")
    lama_selected = _candidate_subset(lama, model_id="lama", notebook_id="10")
    _require_columns(stable_diffusion, (
        "execution_role", "prompt_variant_id", "seed", "is_primary_candidate",
    ), "stable diffusion")
    sd_selected = _candidate_subset(
        stable_diffusion, model_id="stable_diffusion_inpainting", notebook_id="11"
    )
    sd_selected = sd_selected.loc[
        sd_selected["execution_role"].astype(str).eq(str(population["stable_diffusion_primary_role"]))
        & sd_selected["prompt_variant_id"].astype(str).eq(str(population["stable_diffusion_primary_prompt_variant"]))
        & pd.to_numeric(sd_selected["seed"], errors="coerce").eq(int(population["stable_diffusion_primary_seed"]))
        & _bool_series(sd_selected["is_primary_candidate"])
    ].copy()
    sdxl_selected = _candidate_subset(sdxl, model_id="sdxl_inpainting", notebook_id="12")
    _require_columns(sdxl_selected, ("technical_validation_passed",), "SDXL")
    sdxl_selected = sdxl_selected.loc[_bool_series(sdxl_selected["technical_validation_passed"])].copy()

    selected = pd.concat(
        [opencv_selected, lama_selected, sd_selected, sdxl_selected],
        ignore_index=True,
        sort=False,
    )
    if selected["candidate_id"].astype(str).duplicated().any():
        raise ValueError("Selected candidate IDs are not unique")
    if selected.duplicated(["model_id", "case_id"], keep=False).any():
        raise ValueError("Candidate selection is not one-to-one by model and case")
    observed = selected.groupby("model_id").size().to_dict()
    wanted = {
        **{str(k): int(v) for k, v in expected["candidates_by_core_model"].items()},
        "sdxl_inpainting": int(expected["bounded_sdxl_candidates"]),
    }
    if observed != wanted:
        raise ValueError(f"Candidate counts differ from contract: {observed} != {wanted}")

    metadata = cases.merge(
        artworks[["painting_id", "category", "style_or_period"]].drop_duplicates("painting_id"),
        on="painting_id", how="left", validate="many_to_one",
    )
    selected = selected.merge(metadata, on="case_id", how="inner", suffixes=("", "__case"), validate="many_to_one")
    for column in (
        "dataset_id", "dataset_scope", "experiment_id", "painting_id", "input_image_path",
        "clean_image_path", "mask_or_effect_path", "damage_or_degradation_type",
        "target_damage_fraction", "realized_damage_fraction", "category", "style_or_period",
    ):
        authoritative = f"{column}__case"
        if authoritative in selected.columns:
            selected[column] = selected[authoritative]
    selected["dataset_scope"] = selected["dataset_scope"].fillna(str(population["dataset_scope"]))
    selected["category"] = selected["category"].fillna("unclassified")
    selected["style_or_period"] = selected["style_or_period"].fillna("unclassified")
    selected["damage_type"] = np.where(
        selected["experiment_id"].astype(str).eq("synthetic_degradation"),
        "not_applicable", selected["damage_or_degradation_type"].astype(str),
    )
    selected["degradation_type"] = np.where(
        selected["experiment_id"].astype(str).eq("synthetic_degradation"),
        selected["damage_or_degradation_type"].astype(str), "not_applicable",
    )
    selected["target_damage_fraction_label"] = selected["target_damage_fraction"].map(
        lambda value: "missing" if pd.isna(value) else f"{float(value):.6f}"
    )
    selected["is_zero_control"] = (
        selected["experiment_id"].astype(str).eq(str(population["zero_control_experiment"]))
        & pd.to_numeric(selected["target_damage_fraction"], errors="coerce").fillna(-1).eq(0.0)
    )
    selected["quality_analysis_eligible"] = ~selected["is_zero_control"]
    selected["population_id"] = np.where(
        selected["model_id"].astype(str).eq("sdxl_inpainting"),
        "bounded_sdxl_ten_case", "core_primary",
    )
    selected["coverage_role"] = np.where(
        selected["model_id"].astype(str).eq("sdxl_inpainting"),
        "bounded_descriptive_only", "core_three_model",
    )
    selected["candidate_selection_policy"] = str(settings["selection_policy_id"])
    selected["restored_path"] = [
        _normalise_restored_path(value, notebook_id)
        for value, notebook_id in zip(selected["restored_path"], selected["source_notebook_id"])
    ]
    if not selected["restored_path"].astype(str).str.startswith("outputs/").all():
        raise ValueError("One or more restored paths are not repository-relative")

    core = selected.loc[selected["coverage_role"].eq("core_three_model")]
    if core["case_id"].nunique() != int(expected["evaluated_cases"]):
        raise ValueError("Core population does not cover exactly 410 cases")
    evaluated_case_counts = (
        core[["case_id", "experiment_id"]]
        .drop_duplicates("case_id")
        .groupby("experiment_id")
        .size()
        .to_dict()
    )
    wanted_evaluated_counts = {
        str(key): int(value)
        for key, value in population["experiment_case_counts"].items()
    }
    if evaluated_case_counts != wanted_evaluated_counts:
        raise ValueError(
            "Evaluated experiment counts changed: "
            f"{evaluated_case_counts} != {wanted_evaluated_counts}"
        )
    if int(core["is_zero_control"].sum()) != int(expected["zero_control_core_candidates"]):
        raise ValueError("Canonical zero-control population changed")
    if int(core["quality_analysis_eligible"].sum()) != int(expected["quality_core_candidates"]):
        raise ValueError("Nonzero core quality population changed")
    if set(selected["dataset_scope"].astype(str)) != {str(population["dataset_scope"])}:
        raise ValueError("Unexpected dataset source entered Notebook 26")

    keep = [
        "candidate_id", "case_id", "model_id", "source_notebook_id", "painting_id",
        "category", "style_or_period", "dataset_id", "dataset_scope", "experiment_id",
        "damage_or_degradation_type", "damage_type", "degradation_type",
        "target_damage_fraction", "realized_damage_fraction",
        "target_damage_fraction_label", "is_zero_control", "quality_analysis_eligible",
        "input_image_path", "clean_image_path", "mask_or_effect_path", "restored_path",
        "runtime_seconds", "candidate_selection_policy", "population_id", "coverage_role",
    ]
    for optional in ("seed", "execution_role", "prompt_policy_id", "prompt_variant_id"):
        if optional in selected.columns:
            keep.append(optional)
    return selected[keep].sort_values(
        ["coverage_role", "model_id", "experiment_id", "painting_id", "case_id"],
        kind="stable",
    ).reset_index(drop=True)


def normalise_quality_evidence(
    tables: Mapping[str, pd.DataFrame],
    selected_candidates: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Normalize validated Notebook 13--17 and 20 evidence."""

    missing = sorted(set(QUALITY_SOURCE_KEYS) - set(tables))
    if missing:
        raise ValueError(f"Quality evidence tables are missing: {missing}")
    adapter = build_multi_model_adapter_config(config)
    normalized = [
        normalise_standard_metric_table(
            tables[key], selected_candidates, source_key=key, config=adapter
        )
        for key in STANDARD_SOURCE_KEYS
    ]
    normalized.append(normalise_spatial_diagnostics(
        tables["spatial"], selected_candidates, config=adapter
    ))
    result = pd.concat(normalized, ignore_index=True, sort=False)
    expected = int(_settings(config)["expected_counts"]["normalized_quality_rows"])
    if len(result) != expected:
        raise ValueError(f"Normalized quality rows differ from contract: {len(result)} != {expected}")
    if result["candidate_id"].astype(str).nunique() != len(selected_candidates):
        raise ValueError("Normalized evidence does not cover every selected candidate")
    return result


def select_quality_anchor_values(
    normalized: pd.DataFrame,
    *,
    spatial_source: pd.DataFrame | None = None,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select one approved value per nonzero candidate and quality anchor."""

    expected = _settings(config)["expected_counts"]
    anchors = normalized.loc[
        normalized["anchor_id"].fillna("").astype(str).ne("")
        & normalized["status"].astype(str).isin({"ok", "passed"})
        & ~_bool_series(normalized["is_zero_control"])
    ].copy()
    if anchors.duplicated(["candidate_id", "anchor_id"], keep=False).any():
        raise ValueError("Quality-anchor selection is not one-to-one")
    if spatial_source is not None:
        _require_columns(spatial_source, (
            "candidate_id", "region_id", "damaged_error_mean", "restored_error_mean",
        ), "spatial source")
        lookup = spatial_source.loc[
            spatial_source["region_id"].astype(str).eq("masked_region"),
            ["candidate_id", "damaged_error_mean", "restored_error_mean"],
        ].drop_duplicates("candidate_id").set_index("candidate_id")
        spatial_mask = anchors["anchor_id"].astype(str).eq("spatial_masked_error")
        ids = anchors.loc[spatial_mask, "candidate_id"]
        anchors.loc[spatial_mask, "damaged_value"] = ids.map(lookup["damaged_error_mean"])
        anchors.loc[spatial_mask, "restored_value"] = ids.map(lookup["restored_error_mean"])
        anchors.loc[spatial_mask, "improvement_value"] = (
            pd.to_numeric(anchors.loc[spatial_mask, "damaged_value"], errors="coerce").to_numpy()
            - pd.to_numeric(anchors.loc[spatial_mask, "restored_value"], errors="coerce").to_numpy()
        )
        anchors.loc[spatial_mask, "comparison_value"] = pd.to_numeric(
            anchors.loc[spatial_mask, "restored_value"], errors="coerce"
        )
    anchors["directional_utility"] = np.where(
        anchors["comparison_direction"].astype(str).eq("higher_is_better"),
        pd.to_numeric(anchors["comparison_value"], errors="coerce"),
        -pd.to_numeric(anchors["comparison_value"], errors="coerce"),
    )
    if len(anchors) != int(expected["all_nonzero_anchor_rows_with_sdxl"]):
        raise ValueError("Expected exactly 11,990 nonzero candidate-anchor rows")
    if anchors["anchor_id"].nunique() != int(expected["quality_anchors"]):
        raise ValueError("Quality-anchor identity differs from contract")
    if not anchors.groupby("candidate_id").size().eq(int(expected["quality_anchors"])).all():
        raise ValueError("Every nonzero selected candidate must contain all eleven anchors")
    return anchors.reset_index(drop=True)


def build_runtime_evidence(
    selected_candidates: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Normalize runtime while keeping it outside quality ranking."""

    result = normalise_runtime_evidence(
        selected_candidates, config=build_multi_model_adapter_config(config)
    )
    if len(result) != int(_settings(config)["expected_counts"]["selected_candidates"]):
        raise ValueError("Runtime evidence must cover all 1,240 selected candidates")
    if _bool_series(result["quality_ranking_eligible"]).any():
        raise ValueError("Runtime must not enter the restoration-quality ranking")
    return result


def deterministic_cluster_bootstrap_interval(
    values: Sequence[float],
    *,
    confidence_level: float = 0.95,
    resamples: int = 5000,
    random_seed: int = 2026,
    statistic: Callable[[np.ndarray], float] = np.median,
    exhaustive_max_clusters: int = 5,
) -> dict[str, float | int | str]:
    """Return a deterministic cluster-level percentile bootstrap interval."""

    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    if len(array) == 0:
        return {"estimate": np.nan, "ci_lower": np.nan, "ci_upper": np.nan, "resamples": 0, "method": "not_applicable"}
    if not 0 < float(confidence_level) < 1:
        raise ValueError("confidence_level must lie between zero and one")
    if len(array) <= int(exhaustive_max_clusters):
        estimates = np.asarray([
            float(statistic(array[list(indices)]))
            for indices in product(range(len(array)), repeat=len(array))
        ])
        method = "exhaustive_ordered_cluster_bootstrap"
    else:
        if int(resamples) <= 0:
            raise ValueError("resamples must be positive")
        rng = np.random.default_rng(int(random_seed))
        indices = rng.integers(0, len(array), size=(int(resamples), len(array)))
        estimates = np.apply_along_axis(lambda idx: float(statistic(array[idx])), 1, indices)
        method = "deterministic_cluster_bootstrap"
    alpha = 1 - float(confidence_level)
    return {
        "estimate": float(statistic(array)),
        "ci_lower": float(np.quantile(estimates, alpha / 2)),
        "ci_upper": float(np.quantile(estimates, 1 - alpha / 2)),
        "resamples": int(len(estimates)),
        "method": method,
    }


def sign_flip_test(
    differences: Sequence[float],
    *,
    exact_max_n: int = 15,
    monte_carlo_assignments: int = 100000,
    random_seed: int = 2026,
) -> dict[str, float | int | str]:
    """Two-sided paired sign-flip test, exact when feasible and seeded otherwise."""

    values = np.asarray(differences, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return {"statistic": np.nan, "p_value": np.nan, "assignments": 0, "method": "not_applicable"}
    observed = abs(float(np.mean(values)))
    if len(values) <= int(exact_max_n):
        null = np.asarray([
            abs(float(np.mean(values * np.asarray(signs, dtype=float))))
            for signs in product((-1.0, 1.0), repeat=len(values))
        ])
        p_value = float(np.mean(null >= observed - 1e-15))
        method = "exact_sign_flip"
    else:
        rng = np.random.default_rng(int(random_seed))
        extreme = 0
        remaining = int(monte_carlo_assignments)
        while remaining:
            batch = min(10000, remaining)
            signs = rng.choice(np.asarray((-1.0, 1.0)), size=(batch, len(values)))
            null = np.abs((signs * values).mean(axis=1))
            extreme += int(np.sum(null >= observed - 1e-15))
            remaining -= batch
        p_value = float((extreme + 1) / (int(monte_carlo_assignments) + 1))
        method = "monte_carlo_sign_flip"
    return {
        "statistic": float(np.mean(values)), "p_value": p_value,
        "assignments": int(len(null) if method == "exact_sign_flip" else monte_carlo_assignments),
        "method": method,
    }


def correlation_summary(left: Sequence[float], right: Sequence[float]) -> dict[str, float | int]:
    """Return paired Spearman and Pearson evidence after finite-value filtering."""

    x = np.asarray(left, dtype=float)
    y = np.asarray(right, dtype=float)
    keep = np.isfinite(x) & np.isfinite(y)
    x, y = x[keep], y[keep]
    if len(x) < 3 or len(np.unique(x)) < 2 or len(np.unique(y)) < 2:
        return {"n": int(len(x)), "spearman_rho": np.nan, "spearman_p_value": np.nan, "pearson_r": np.nan, "pearson_p_value": np.nan}
    sr = spearmanr(x, y)
    pr = pearsonr(x, y)
    return {
        "n": int(len(x)), "spearman_rho": float(sr.statistic),
        "spearman_p_value": float(sr.pvalue), "pearson_r": float(pr.statistic),
        "pearson_p_value": float(pr.pvalue),
    }


def friedman_with_kendalls_w(groups: Sequence[Sequence[float]]) -> dict[str, float | int]:
    """Return the repeated-model Friedman test and Kendall's W effect size."""

    arrays = [np.asarray(group, dtype=float) for group in groups]
    if len(arrays) < 3 or len({len(group) for group in arrays}) != 1:
        raise ValueError("Friedman test requires at least three equal-length groups")
    matrix = np.column_stack(arrays)
    matrix = matrix[np.isfinite(matrix).all(axis=1)]
    if len(matrix) < 2:
        return {"statistic": np.nan, "p_value": np.nan, "kendalls_w": np.nan, "n_blocks": int(len(matrix)), "n_groups": len(arrays)}
    result = friedmanchisquare(*[matrix[:, index] for index in range(matrix.shape[1])])
    denominator = len(matrix) * (matrix.shape[1] - 1)
    return {
        "statistic": float(result.statistic), "p_value": float(result.pvalue),
        "kendalls_w": float(result.statistic / denominator),
        "n_blocks": int(len(matrix)), "n_groups": int(matrix.shape[1]),
    }


def kruskal_with_epsilon_squared(groups: Sequence[Sequence[float]]) -> dict[str, float | int]:
    """Return Kruskal-Wallis evidence with epsilon-squared effect size."""

    arrays = [np.asarray(group, dtype=float) for group in groups]
    arrays = [group[np.isfinite(group)] for group in arrays if np.isfinite(group).any()]
    if len(arrays) < 2:
        return {"statistic": np.nan, "p_value": np.nan, "epsilon_squared": np.nan, "n": int(sum(map(len, arrays))), "n_groups": len(arrays)}
    result = kruskal(*arrays)
    n = sum(map(len, arrays))
    k = len(arrays)
    epsilon = max(0.0, float((result.statistic - k + 1) / (n - k))) if n > k else np.nan
    return {"statistic": float(result.statistic), "p_value": float(result.pvalue), "epsilon_squared": epsilon, "n": int(n), "n_groups": int(k)}


def cliffs_delta(left: Sequence[float], right: Sequence[float]) -> float:
    """Return Cliff's delta for two independent finite samples."""

    x = np.asarray(left, dtype=float)
    y = np.asarray(right, dtype=float)
    x, y = x[np.isfinite(x)], y[np.isfinite(y)]
    if len(x) == 0 or len(y) == 0:
        return np.nan
    differences = x[:, None] - y[None, :]
    return float((np.sum(differences > 0) - np.sum(differences < 0)) / differences.size)


def empty_statistical_results() -> pd.DataFrame:
    return pd.DataFrame(columns=STATISTICAL_RESULT_COLUMNS)


def empty_metric_correlations() -> pd.DataFrame:
    return pd.DataFrame(columns=CORRELATION_COLUMNS)


def empty_ranking_stability() -> pd.DataFrame:
    return pd.DataFrame(columns=RANKING_STABILITY_COLUMNS)


def _validate_canonical_table(
    frame: pd.DataFrame,
    *,
    columns: Sequence[str],
    id_column: str,
    kind_column: str,
    allowed_kinds: Sequence[str],
    schema_version: str,
) -> dict[str, Any]:
    exact_columns = list(frame.columns) == list(columns)
    unique_ids = bool(not frame[id_column].astype(str).duplicated().any()) if id_column in frame else False
    kinds_valid = bool(frame[kind_column].astype(str).isin(set(allowed_kinds)).all()) if kind_column in frame else False
    schemas_valid = bool(frame["schema_version"].astype(str).eq(schema_version).all()) if "schema_version" in frame else False
    probability_valid = True
    for column in ("p_value", "q_value", "winner_frequency"):
        if column in frame:
            values = pd.to_numeric(frame[column], errors="coerce").dropna()
            probability_valid &= bool(values.between(0, 1).all())
    text = " ".join(map(str, frame.astype(str).to_numpy().ravel())).lower()
    no_combined = not re.search(r"combined_(quality|efficiency|uncertainty|trust)_score|trust_score", text)
    return {
        "passed": bool(exact_columns and unique_ids and kinds_valid and schemas_valid and probability_valid and no_combined),
        "exact_columns": exact_columns, "unique_ids": unique_ids,
        "kinds_valid": kinds_valid, "schemas_valid": schemas_valid,
        "probability_valid": probability_valid, "no_combined_score": no_combined,
    }


def validate_statistical_results(frame: pd.DataFrame, *, config: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_canonical_table(
        frame, columns=STATISTICAL_RESULT_COLUMNS, id_column="result_id",
        kind_column="result_kind", allowed_kinds=_settings(config)["statistical_result_kinds"],
        schema_version=STATISTICAL_RESULTS_SCHEMA_VERSION,
    )


def validate_metric_correlations(frame: pd.DataFrame, *, config: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_canonical_table(
        frame, columns=CORRELATION_COLUMNS, id_column="correlation_id",
        kind_column="correlation_kind", allowed_kinds=_settings(config)["correlation_kinds"],
        schema_version=CORRELATION_SCHEMA_VERSION,
    )


def validate_ranking_stability(frame: pd.DataFrame, *, config: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_canonical_table(
        frame, columns=RANKING_STABILITY_COLUMNS, id_column="ranking_id",
        kind_column="ranking_kind", allowed_kinds=_settings(config)["ranking_stability_kinds"],
        schema_version=RANKING_STABILITY_SCHEMA_VERSION,
    )


def validate_grouped_statistical_report_html(
    html_text: str,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Validate the approved mock structure, density, scope, and portability."""

    report = _settings(config)["report"]
    section_ids = list(map(str, report["required_section_ids"]))
    positions = [html_text.find(f'id="{section_id}"') for section_id in section_ids]
    image_sources = re.findall(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", html_text, flags=re.I)
    embedded = [source for source in image_sources if source.startswith("data:image/")]
    external = [source for source in image_sources if not source.startswith("data:image/")]
    lower = html_text.lower()
    required_terms = (
        "rq1", "rq2", "rq3", "conclusion", "limitation", "controlled_50",
        "painting", "independent unit", "not calibrated confidence",
        "not_applicable_single_dataset", "sdxl", "bounded",
    )
    checks = [
        ("html_nonempty", bool(html_text.strip()), len(html_text), "> 0"),
        ("approved_sections_present", all(position >= 0 for position in positions), sum(position >= 0 for position in positions), len(section_ids)),
        ("approved_sections_ordered", positions == sorted(positions) and all(position >= 0 for position in positions), positions, "strict approved order"),
        ("required_scope_language", all(term in lower for term in required_terms), [term for term in required_terms if term in lower], list(required_terms)),
        ("required_visuals_self_contained", len(external) == 0, len(external), 0),
        ("embedded_visual_minimum", len(embedded) >= int(report["minimum_embedded_images"]), len(embedded), int(report["minimum_embedded_images"])),
    ]
    rows = []
    for name, passed, observed, expected in checks:
        rows.append({
            "check_name": name, "observed": json.dumps(observed) if isinstance(observed, (list, dict)) else observed,
            "expected": json.dumps(expected) if isinstance(expected, (list, dict)) else expected,
            "passed": bool(passed), "issue": "" if passed else f"failed report contract: {name}",
        })
    return pd.DataFrame(rows)


def atomic_write_csv(frame: pd.DataFrame, output_path: str | Path) -> Path:
    """Write a CSV atomically and remove its temporary file on failure."""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    try:
        frame.to_csv(temporary, index=False, lineterminator="\n")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


__all__ = [
    "CONFIG_SCHEMA_VERSION", "CORRELATION_COLUMNS", "CORRELATION_SCHEMA_VERSION",
    "MODULE_NAME", "MODULE_VERSION", "QUALITY_SOURCE_KEYS",
    "RANKING_STABILITY_COLUMNS", "RANKING_STABILITY_SCHEMA_VERSION",
    "STATISTICAL_RESULT_COLUMNS", "STATISTICAL_RESULTS_SCHEMA_VERSION",
    "atomic_write_csv", "benjamini_hochberg", "build_multi_model_adapter_config",
    "build_runtime_evidence", "cliffs_delta", "correlation_summary",
    "deterministic_cluster_bootstrap_interval", "empty_metric_correlations",
    "empty_ranking_stability", "empty_statistical_results", "family_balanced_ranks",
    "friedman_with_kendalls_w", "kruskal_with_epsilon_squared",
    "load_grouped_statistical_analysis_config", "matched_rank_biserial",
    "normalise_quality_evidence", "resolve_analysis_inputs",
    "select_primary_candidate_population", "select_quality_anchor_values",
    "sign_flip_test", "validate_grouped_statistical_report_html",
    "validate_metric_correlations", "validate_ranking_stability",
    "validate_statistical_results", "validate_upstream_run_manifests",
]
