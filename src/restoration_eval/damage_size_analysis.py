"""Matched damage-size analysis utilities for Notebook 23.

The module selects the approved primary population, adapts validated upstream
metric tables, aggregates four-seed uncertainty without treating seed pairs as
independent paintings, and provides exact small-sample statistical helpers.
It performs no restoration inference and never writes to frozen output roots.
"""

from __future__ import annotations

import hashlib
import os
from itertools import combinations, product
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml
from scipy.stats import rankdata, spearmanr

from .multi_model_comparison import (
    image_grid_to_data_uri,
    image_path_to_data_uri,
    normalise_runtime_evidence,
    normalise_spatial_diagnostics,
    normalise_standard_metric_table,
    validate_self_contained_report_html,
)
from .paths import find_project_root, resolve_repo_path


MODULE_NAME = "restoration_eval.damage_size_analysis"
MODULE_VERSION = "1.0.0"
CONFIG_SCHEMA_VERSION = "damage_size_analysis_config.v1"
ANALYSIS_SCHEMA_VERSION = "damage_size_analysis.v1"

QUALITY_SOURCE_KEYS = (
    "classical",
    "perceptual",
    "feature",
    "spatial",
    "local_consistency",
    "semantic_structural",
)
STANDARD_SOURCE_KEYS = tuple(key for key in QUALITY_SOURCE_KEYS if key != "spatial")
UNCERTAINTY_FAMILIES = (
    "pixel_variability",
    "pixel_pairwise",
    "perceptual_pairwise",
    "feature_pairwise",
)

ANALYSIS_COLUMNS = (
    "analysis_row_id",
    "analysis_kind",
    "analysis_family_id",
    "source_notebook_ids",
    "source_metric_ids_json",
    "evidence_family",
    "metric_family",
    "metric_id",
    "metric_name",
    "feature_model_id",
    "region_id",
    "summary_statistic",
    "value_unit",
    "comparison_direction",
    "quality_ranking_eligible",
    "anchor_id",
    "model_id",
    "comparison_model_id",
    "exposure_definition",
    "level_id",
    "target_damage_fraction",
    "realized_damage_fraction",
    "interval_start_fraction",
    "interval_end_fraction",
    "painting_id",
    "category",
    "style_or_period",
    "scope_type",
    "scope_value",
    "independent_unit",
    "n_paintings",
    "n_cases",
    "n_observations",
    "estimate_name",
    "estimate",
    "ci_lower",
    "ci_upper",
    "effect_size_name",
    "effect_size",
    "p_value",
    "q_value",
    "test_method",
    "bootstrap_method",
    "bootstrap_resamples",
    "applicability_status",
    "interpretation_status",
    "schema_version",
    "status",
    "issue",
)

UNCERTAINTY_GROUP_COLUMNS = (
    "uncertainty_group_id",
    "case_id",
    "model_id",
    "painting_id",
    "category",
    "style_or_period",
    "experiment_id",
    "target_damage_fraction",
    "realized_damage_fraction",
    "metric_family",
    "metric_name",
    "region_id",
    "summary_statistic",
    "value",
    "value_unit",
    "aggregation_method",
    "pair_count",
    "seed_count",
    "component_id",
    "comparison_direction",
    "evidence_role",
    "status",
    "issue",
)


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    settings = config.get("damage_size_analysis", config)
    if not isinstance(settings, Mapping):
        raise TypeError("damage_size_analysis settings must be a mapping")
    return settings


def _stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join("" if part is None else str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


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


def load_damage_size_analysis_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the Notebook 23 analysis contract."""

    with Path(path).open("r", encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Damage-size analysis configuration must be a mapping")
    if config.get("config_schema_version") != CONFIG_SCHEMA_VERSION:
        raise ValueError("Unsupported damage-size analysis config schema")
    settings = _settings(config)
    required = {
        "notebook_id", "notebook_stem", "analysis_schema_version", "inputs",
        "output", "population", "evidence_sources", "metric_direction",
        "spatial_metric_fields", "quality_anchors", "uncertainty", "statistics",
        "morphology", "analysis_kinds", "report", "expected_counts",
        "evidence_policy", "known_limitations",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"Damage-size analysis config is missing keys: {missing}")
    if settings["notebook_id"] != "23" or settings["notebook_stem"] != "23_damage_size_sensitivity_analysis":
        raise ValueError("Notebook 23 identity contract changed")
    if settings["analysis_schema_version"] != ANALYSIS_SCHEMA_VERSION:
        raise ValueError("Configured analysis schema version does not match helper")
    for key, value in settings["inputs"].items():
        if not _normalized_relative_path(value):
            raise ValueError(f"inputs.{key} must be a normalized repository-relative path")

    output = settings["output"]
    expected_output = {
        "root": "outputs/23_damage_size_sensitivity_analysis",
        "metrics_path": "metrics/damage_size_analysis.csv",
        "performance_figure_path": "figures/performance_vs_damage.png",
        "ranking_figure_path": "figures/ranking_vs_damage.png",
        "uncertainty_figure_path": "figures/uncertainty_vs_damage.png",
        "report_path": "reports/damage_size_analysis.html",
        "run_manifest_path": "manifests/run_manifest.json",
        "artifacts_path": "manifests/artifacts.csv",
        "validation_path": "validation/checks.csv",
    }
    for key, value in expected_output.items():
        if output.get(key) != value:
            raise ValueError(f"output.{key} must equal {value!r}")

    population = settings["population"]
    expected = settings["expected_counts"]
    models = list(map(str, population["model_order"]))
    if models != ["opencv_telea", "lama", "stable_diffusion_inpainting"]:
        raise ValueError("Model order or scope changed")
    if len(population["painting_ids"]) != int(expected["paintings"]):
        raise ValueError("Painting-count arithmetic is inconsistent")
    if len(population["level_ids"]) != int(expected["damage_levels"]):
        raise ValueError("Damage-level arithmetic is inconsistent")
    if int(expected["paintings"]) * int(expected["damage_levels"]) != int(expected["cases"]):
        raise ValueError("Case-count arithmetic is inconsistent")
    if sum(int(value) for value in expected["candidates_by_model"].values()) != int(expected["candidates"]):
        raise ValueError("Candidate-count arithmetic is inconsistent")
    if int(expected["selected_metric_source_rows"]) != sum(
        int(expected[key])
        for key in (
            "selected_classical_source_rows", "selected_lpips_source_rows",
            "selected_feature_source_rows", "selected_spatial_source_rows",
            "selected_local_source_rows", "selected_semantic_source_rows",
        )
    ):
        raise ValueError("Selected metric-source arithmetic is inconsistent")
    if int(expected["uncertainty_only_source_rows"]) + int(expected["uncertainty_reference_rows"]) != int(expected["uncertainty_metric_rows"]):
        raise ValueError("Uncertainty-source arithmetic is inconsistent")
    if int(settings["statistics"]["bootstrap_resamples"]) != int(expected["paintings"]) ** int(expected["paintings"]):
        raise ValueError("Exhaustive bootstrap count is inconsistent")
    if int(settings["statistics"]["sign_flip_assignments"]) != 2 ** int(expected["paintings"]):
        raise ValueError("Sign-flip assignment count is inconsistent")
    if len(settings["quality_anchors"]) != int(expected["quality_anchors"]):
        raise ValueError("Quality-anchor count is inconsistent")
    anchor_ids = [str(item["anchor_id"]) for item in settings["quality_anchors"]]
    if len(anchor_ids) != len(set(anchor_ids)):
        raise ValueError("Quality anchor IDs must be unique")
    if bool(settings["uncertainty"]["combined_index_retained"]):
        raise ValueError("A combined uncertainty index is prohibited")
    if bool(settings["statistics"]["combined_quality_score_retained"]):
        raise ValueError("A combined quality score is prohibited")
    if not bool(settings["report"]["self_contained_html"]):
        raise ValueError("The Notebook 23 report must be self-contained")
    if not bool(settings["report"]["plain_language_first"]):
        raise ValueError("The Notebook 23 report must use plain language first")
    prohibited = (
        "category_effect_permitted", "style_effect_permitted",
        "universal_damage_threshold_permitted",
        "deterministic_generative_class_effect_permitted",
        "historical_authenticity_claim_permitted",
        "conservation_approval_claim_permitted", "low_uncertainty_proves_correctness",
        "uncertainty_is_calibrated_confidence", "runtime_is_quality_evidence",
    )
    if any(bool(settings["evidence_policy"][key]) for key in prohibited):
        raise ValueError("One or more prohibited scientific claims were enabled")
    return config


def resolve_analysis_inputs(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
    *,
    must_exist: bool = True,
) -> dict[str, Path]:
    """Resolve every declared Notebook 23 input without dynamic discovery."""

    root = find_project_root(project_root)
    return {
        str(key): resolve_repo_path(value, root, must_exist=must_exist)
        for key, value in _settings(config)["inputs"].items()
    }


def build_multi_model_adapter_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Expose the approved Notebook 21 normalizers under their expected keys."""

    settings = _settings(config)
    return {
        "multi_model_comparison": {
            "evidence_sources": settings["evidence_sources"],
            "metric_direction": settings["metric_direction"],
            "spatial_metric_fields": settings["spatial_metric_fields"],
            "disagreement_anchors": settings["quality_anchors"],
            "report": settings["report"],
        }
    }


def validate_upstream_run_manifests(
    manifests: Mapping[str, Mapping[str, Any]],
    *,
    expected_notebook_ids: Sequence[str] = (
        "05", "08", "09", "10", "11", "13", "14", "15", "16", "17", "20", "21", "22",
    ),
) -> pd.DataFrame:
    """Return one completion-gate row per direct upstream notebook."""

    records: list[dict[str, Any]] = []
    for notebook_id in expected_notebook_ids:
        manifest = manifests.get(str(notebook_id))
        present = isinstance(manifest, Mapping)
        run_status = str(manifest.get("run_status", "")) if present else ""
        validation_status = str(manifest.get("validation_status", "")) if present else ""
        gate = bool(manifest.get("completion_gate_passed", False)) if present else False
        records.append(
            {
                "notebook_id": str(notebook_id),
                "manifest_present": present,
                "run_status": run_status,
                "validation_status": validation_status,
                "completion_gate_passed": gate,
                "passed": present and run_status == "completed" and validation_status == "passed" and gate,
            }
        )
    return pd.DataFrame(records)


def _normalise_restored_path(value: Any, source_notebook_id: str) -> str:
    text = "" if value is None or pd.isna(value) else str(value).strip().replace("\\", "/")
    if text.startswith("images/"):
        roots = {
            "09": "outputs/09_opencv_telea_restoration",
            "10": "outputs/10_lama_restoration",
            "11": "outputs/11_stable_diffusion_restoration",
        }
        return f"{roots[source_notebook_id]}/{text}"
    return text


def select_damage_size_population(
    cases: pd.DataFrame,
    artworks: pd.DataFrame,
    opencv: pd.DataFrame,
    lama: pd.DataFrame,
    stable_diffusion: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select exactly one approved primary candidate per model and damage-size case."""

    settings = _settings(config)
    population = settings["population"]
    expected = settings["expected_counts"]
    _require_columns(
        cases,
        ("case_id", "painting_id", "level_id", "experiment_id", "target_damage_fraction",
         "realized_damage_fraction", "input_image_path", "clean_image_path",
         "mask_or_effect_path", "damage_or_degradation_type", "status"),
        "damage-size cases",
    )
    _require_columns(artworks, ("painting_id", "category", "style_or_period"), "artworks")
    case_rows = cases.loc[
        cases["experiment_id"].astype(str).eq(str(population["experiment_id"]))
        & cases["status"].astype(str).eq(str(population["passed_status"]))
    ].copy()
    case_rows = case_rows.loc[
        case_rows["painting_id"].astype(str).isin(set(map(str, population["painting_ids"])))
    ].copy()
    if len(case_rows) != int(expected["cases"]) or case_rows["case_id"].duplicated().any():
        raise ValueError("Damage-size case population is not exactly 35 unique cases")
    observed_levels = sorted(pd.to_numeric(case_rows["target_damage_fraction"], errors="coerce").unique())
    wanted_levels = sorted(map(float, population["target_damage_fractions"]))
    if not np.allclose(observed_levels, wanted_levels, atol=1e-12, rtol=0.0):
        raise ValueError("Damage-size target levels differ from the approved contract")

    metadata = artworks[["painting_id", "category", "style_or_period"]].drop_duplicates("painting_id")
    case_rows = case_rows.merge(metadata, on="painting_id", how="left", validate="many_to_one")
    if case_rows["category"].isna().any():
        raise ValueError("Damage-size cases are missing controlled category metadata")
    case_rows["style_or_period"] = case_rows["style_or_period"].fillna("unclassified")
    case_ids = set(case_rows["case_id"].astype(str))

    def deterministic(frame: pd.DataFrame, model_id: str, notebook_id: str) -> pd.DataFrame:
        _require_columns(frame, ("case_id", "candidate_id", "model_id", "restored_path", "runtime_seconds", "status"), model_id)
        selected = frame.loc[
            frame["case_id"].astype(str).isin(case_ids)
            & frame["status"].astype(str).eq(str(population["completed_status"]))
            & frame["model_id"].astype(str).eq(model_id)
        ].copy()
        selected["source_notebook_id"] = notebook_id
        return selected

    opencv_selected = deterministic(opencv, "opencv_telea", "09")
    lama_selected = deterministic(lama, "lama", "10")
    _require_columns(
        stable_diffusion,
        ("case_id", "candidate_id", "model_id", "restored_path", "runtime_seconds", "status",
         "experiment_id", "execution_role", "prompt_variant_id", "seed", "is_primary_candidate"),
        "stable diffusion",
    )
    sd_selected = stable_diffusion.loc[
        stable_diffusion["case_id"].astype(str).isin(case_ids)
        & stable_diffusion["experiment_id"].astype(str).eq(str(population["experiment_id"]))
        & stable_diffusion["status"].astype(str).eq(str(population["completed_status"]))
        & stable_diffusion["model_id"].astype(str).eq("stable_diffusion_inpainting")
        & stable_diffusion["execution_role"].astype(str).eq(str(population["stable_diffusion_primary_role"]))
        & stable_diffusion["prompt_variant_id"].astype(str).eq(str(population["stable_diffusion_primary_prompt_variant"]))
        & pd.to_numeric(stable_diffusion["seed"], errors="coerce").eq(int(population["stable_diffusion_primary_seed"]))
        & _bool_series(stable_diffusion["is_primary_candidate"])
    ].copy()
    sd_selected["source_notebook_id"] = "11"

    selected = pd.concat([opencv_selected, lama_selected, sd_selected], ignore_index=True, sort=False)
    selected = selected.merge(
        case_rows,
        on="case_id",
        how="inner",
        suffixes=("", "__case"),
        validate="many_to_one",
    )
    case_fields = (
        "painting_id", "category", "style_or_period", "experiment_id",
        "damage_or_degradation_type", "level_id", "target_damage_fraction",
        "realized_damage_fraction", "input_image_path", "clean_image_path",
        "mask_or_effect_path",
    )
    for column in case_fields:
        authoritative = f"{column}__case"
        if authoritative in selected.columns:
            selected[column] = selected[authoritative]
            selected = selected.drop(columns=[authoritative])
    selected["dataset_id"] = case_rows["dataset_id"].iloc[0] if "dataset_id" in case_rows else "painting_restoration_eval"
    selected["dataset_scope"] = str(population["dataset_scope"])
    selected["damage_type"] = "loss_large"
    selected["degradation_type"] = "not_applicable"
    selected["severity"] = "not_applicable"
    selected["is_zero_control"] = False
    selected["target_damage_fraction_label"] = pd.to_numeric(
        selected["target_damage_fraction"], errors="coerce"
    ).map(lambda value: f"{100.0 * float(value):g}%")
    selected["candidate_selection_policy"] = str(settings["selection_policy_id"])
    selected["restored_path"] = [
        _normalise_restored_path(value, notebook_id)
        for value, notebook_id in zip(selected["restored_path"], selected["source_notebook_id"])
    ]
    if selected.duplicated(["model_id", "case_id"], keep=False).any():
        raise ValueError("Primary candidate selection is not one-to-one by model and case")
    observed = selected.groupby("model_id").size().to_dict()
    wanted = {str(key): int(value) for key, value in expected["candidates_by_model"].items()}
    if observed != wanted:
        raise ValueError(f"Primary candidate counts differ from contract: {observed} != {wanted}")
    for model_id in population["model_order"]:
        model_cases = set(selected.loc[selected["model_id"].eq(model_id), "case_id"].astype(str))
        if model_cases != case_ids:
            raise ValueError(f"{model_id} does not cover the exact 35 matched cases")
    if selected["candidate_id"].duplicated().any():
        raise ValueError("Selected candidate IDs are not unique")
    return selected.sort_values(
        ["painting_id", "target_damage_fraction", "model_id"], kind="stable"
    ).reset_index(drop=True)


def normalise_quality_evidence(
    source_tables: Mapping[str, pd.DataFrame],
    selected_candidates: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Normalize all eligible quality evidence after primary-candidate selection."""

    settings = _settings(config)
    expected = settings["expected_counts"]
    adapter = build_multi_model_adapter_config(config)
    missing = sorted(set(QUALITY_SOURCE_KEYS) - set(source_tables))
    if missing:
        raise ValueError(f"Missing quality source tables: {missing}")
    frames: list[pd.DataFrame] = []
    expected_rows = {
        "classical": int(expected["selected_classical_source_rows"]),
        "perceptual": int(expected["selected_lpips_source_rows"]),
        "feature": int(expected["selected_feature_source_rows"]),
        "local_consistency": int(expected["selected_local_source_rows"]),
        "semantic_structural": int(expected["selected_semantic_source_rows"]),
    }
    for key in STANDARD_SOURCE_KEYS:
        normalized = normalise_standard_metric_table(
            source_tables[key], selected_candidates, source_key=key, config=adapter
        )
        if len(normalized) != expected_rows[key]:
            raise ValueError(f"{key} selected row count {len(normalized)} != {expected_rows[key]}")
        normalized["source_key"] = key
        frames.append(normalized)
    spatial_source = source_tables["spatial"]
    selected_ids = set(selected_candidates["candidate_id"].astype(str))
    spatial_selected_count = int(spatial_source["candidate_id"].astype(str).isin(selected_ids).sum())
    if spatial_selected_count != int(expected["selected_spatial_source_rows"]):
        raise ValueError("Spatial selected source-row count differs from contract")
    spatial = normalise_spatial_diagnostics(spatial_source, selected_candidates, config=adapter)
    if len(spatial) != int(expected["normalized_spatial_rows"]):
        raise ValueError("Normalized spatial row count differs from contract")
    spatial["source_key"] = "spatial"
    frames.append(spatial)
    result = pd.concat(frames, ignore_index=True, sort=False)
    if len(result) != int(expected["normalized_quality_rows"]):
        raise ValueError("Normalized quality row count differs from contract")
    if result.duplicated(["source_notebook_id", "source_metric_row_id"], keep=False).any():
        raise ValueError("Normalized quality source row IDs are not unique")
    values = pd.to_numeric(result["comparison_value"], errors="coerce")
    result["analysis_eligible"] = (
        result["status"].astype(str).eq("ok")
        & np.isfinite(values)
        & result["comparison_direction"].isin(["higher_is_better", "lower_is_better"])
    )
    result["directional_utility"] = np.where(
        result["comparison_direction"].eq("higher_is_better"), values, -values
    )
    return result.sort_values(
        ["source_notebook_id", "source_metric_row_id"], kind="stable"
    ).reset_index(drop=True)


def build_runtime_evidence(
    selected_candidates: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Normalize runtime as operational evidence excluded from quality rankings."""

    result = normalise_runtime_evidence(
        selected_candidates, config=build_multi_model_adapter_config(config)
    )
    expected = int(_settings(config)["expected_counts"]["runtime_rows"])
    if len(result) != expected or result["quality_ranking_eligible"].astype(bool).any():
        raise ValueError("Runtime evidence violates the Notebook 23 contract")
    return result


def normalise_uncertainty_evidence(
    metrics: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Collapse seed pairs to one transparent uncertainty value per case and component."""

    settings = _settings(config)
    uncertainty = settings["uncertainty"]
    expected = settings["expected_counts"]
    _require_columns(
        metrics,
        ("uncertainty_group_id", "observation_level", "case_id", "model_id",
         "painting_id", "category", "style_or_period", "experiment_id",
         "target_damage_fraction", "realized_damage_fraction", "seed_count",
         "metric_family", "metric_name", "region_id", "summary_statistic",
         "value", "value_unit", "evidence_role", "is_combined_index", "status", "issue"),
        "damage-size uncertainty metrics",
    )
    if len(metrics) != int(expected["uncertainty_metric_rows"]):
        raise ValueError("Notebook 22 uncertainty metric row count differs from contract")
    combined = _bool_series(metrics["is_combined_index"])
    if combined.any():
        raise ValueError("Notebook 22 unexpectedly contains a combined uncertainty index")
    subset = metrics.loc[
        metrics["experiment_id"].astype(str).eq(str(settings["population"]["experiment_id"]))
        & metrics["metric_family"].astype(str).isin(set(map(str, uncertainty["uncertainty_families"])))
    ].copy()
    if len(subset) != int(expected["uncertainty_only_source_rows"]):
        raise ValueError("Uncertainty-only source row count differs from contract")
    if subset["status"].astype(str).ne("ok").any():
        raise ValueError("One or more uncertainty-only rows are not valid")
    if subset["uncertainty_group_id"].nunique() != int(expected["uncertainty_groups"]):
        raise ValueError("Uncertainty group count differs from contract")
    if not pd.to_numeric(subset["seed_count"], errors="coerce").eq(len(uncertainty["expected_seeds"])).all():
        raise ValueError("One or more uncertainty groups lack four seeds")

    group_keys = [
        "uncertainty_group_id", "case_id", "model_id", "painting_id", "category",
        "style_or_period", "experiment_id", "target_damage_fraction",
        "realized_damage_fraction", "metric_family", "metric_name", "region_id",
        "value_unit", "evidence_role",
    ]
    group_rows = subset.loc[subset["observation_level"].astype(str).eq("group_summary")].copy()
    direct = group_rows[group_keys + ["summary_statistic", "value", "seed_count", "status", "issue"]].copy()
    direct["aggregation_method"] = "reported_group_value"
    direct["pair_count"] = 0

    pair_rows = subset.loc[subset["observation_level"].astype(str).eq("candidate_pair")].copy()
    pair_rows["value"] = pd.to_numeric(pair_rows["value"], errors="coerce")
    pair_counts = pair_rows.groupby(group_keys, dropna=False, sort=False).size()
    required_pairs = int(uncertainty["pair_count_per_group"])
    if not pair_counts.eq(required_pairs).all():
        raise ValueError("One or more pairwise uncertainty components lack six seed pairs")
    paired = (
        pair_rows.groupby(group_keys, dropna=False, sort=False)
        .agg(value=("value", "median"), seed_count=("seed_count", "first"), pair_count=("value", "size"))
        .reset_index()
    )
    paired["summary_statistic"] = "median_unordered_seed_pair"
    paired["aggregation_method"] = "median_of_six_unordered_seed_pairs"
    paired["status"] = "ok"
    paired["issue"] = ""
    result = pd.concat([direct, paired], ignore_index=True, sort=False)

    component_lookup = {
        (str(item["metric_family"]), str(item["metric_name"]), str(item["region_id"])): str(item["component_id"])
        for item in uncertainty["main_figure_components"]
    }
    result["component_id"] = [
        component_lookup.get((str(family), str(metric), str(region)), "")
        for family, metric, region in zip(result["metric_family"], result["metric_name"], result["region_id"])
    ]
    result["comparison_direction"] = "lower_is_better"
    result["value"] = pd.to_numeric(result["value"], errors="coerce")
    if not np.isfinite(result["value"]).all():
        raise ValueError("Normalized uncertainty contains non-finite values")
    if len(result) != int(expected["uncertainty_group_level_rows"]):
        raise ValueError("Group-level uncertainty row count differs from contract")
    if result.duplicated(
        ["uncertainty_group_id", "metric_family", "metric_name", "region_id"], keep=False
    ).any():
        raise ValueError("Normalized uncertainty component keys are not unique")
    return result[list(UNCERTAINTY_GROUP_COLUMNS)].sort_values(
        ["painting_id", "target_damage_fraction", "metric_family", "metric_name", "region_id"],
        kind="stable",
    ).reset_index(drop=True)


def theil_sen_slope(x: Sequence[float], y: Sequence[float]) -> float:
    """Return the median of all finite pairwise slopes."""

    x_values = np.asarray(x, dtype=float)
    y_values = np.asarray(y, dtype=float)
    valid = np.isfinite(x_values) & np.isfinite(y_values)
    x_values, y_values = x_values[valid], y_values[valid]
    slopes = [
        (y_values[j] - y_values[i]) / (x_values[j] - x_values[i])
        for i, j in combinations(range(len(x_values)), 2)
        if x_values[j] != x_values[i]
    ]
    if not slopes:
        return float("nan")
    return float(np.median(np.asarray(slopes, dtype=float)))


def exhaustive_bootstrap_interval(
    values: Sequence[float],
    *,
    confidence_level: float = 0.95,
    statistic: Callable[[np.ndarray], float] = np.median,
) -> dict[str, float | int]:
    """Return an exact ordered nonparametric bootstrap interval for small clusters."""

    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    if len(array) == 0:
        return {"estimate": np.nan, "ci_lower": np.nan, "ci_upper": np.nan, "resamples": 0}
    if not 0.0 < float(confidence_level) < 1.0:
        raise ValueError("confidence_level must lie between zero and one")
    estimates = np.asarray(
        [float(statistic(array[list(indices)])) for indices in product(range(len(array)), repeat=len(array))],
        dtype=float,
    )
    alpha = 1.0 - float(confidence_level)
    return {
        "estimate": float(statistic(array)),
        "ci_lower": float(np.quantile(estimates, alpha / 2.0)),
        "ci_upper": float(np.quantile(estimates, 1.0 - alpha / 2.0)),
        "resamples": int(len(estimates)),
    }


def exact_sign_flip_test(differences: Sequence[float]) -> dict[str, float | int]:
    """Test a paired mean against zero using every possible sign assignment."""

    values = np.asarray(differences, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return {"statistic": np.nan, "p_value": np.nan, "assignments": 0}
    observed = abs(float(np.mean(values)))
    null = np.asarray(
        [abs(float(np.mean(values * np.asarray(signs, dtype=float)))) for signs in product((-1.0, 1.0), repeat=len(values))]
    )
    return {
        "statistic": float(np.mean(values)),
        "p_value": float(np.mean(null >= observed - 1e-15)),
        "assignments": int(len(null)),
    }


def matched_rank_biserial(differences: Sequence[float]) -> float:
    """Return the matched-pairs rank-biserial effect size, omitting zero ties."""

    values = np.asarray(differences, dtype=float)
    values = values[np.isfinite(values) & ~np.isclose(values, 0.0)]
    if len(values) == 0:
        return 0.0
    ranks = rankdata(np.abs(values), method="average")
    denominator = float(ranks.sum())
    return float((ranks[values > 0].sum() - ranks[values < 0].sum()) / denominator)


def benjamini_hochberg(p_values: Sequence[float]) -> np.ndarray:
    """Return monotone Benjamini-Hochberg adjusted q-values with NaNs preserved."""

    values = np.asarray(p_values, dtype=float)
    result = np.full(values.shape, np.nan, dtype=float)
    valid_positions = np.flatnonzero(np.isfinite(values))
    if len(valid_positions) == 0:
        return result
    valid = np.clip(values[valid_positions], 0.0, 1.0)
    order = np.argsort(valid, kind="stable")
    ranked = valid[order]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0.0, 1.0)
    restored = np.empty_like(adjusted)
    restored[order] = adjusted
    result[valid_positions] = restored
    return result


def compute_painting_slopes(
    frame: pd.DataFrame,
    *,
    exposure_column: str,
    value_column: str = "comparison_value",
    direction: str,
    reporting_scale_percentage_points: float = 10.0,
) -> pd.DataFrame:
    """Compute one Theil-Sen slope per painting and orient positive values as worse."""

    _require_columns(frame, ("painting_id", exposure_column, value_column), "slope input")
    if direction not in {"higher_is_better", "lower_is_better"}:
        raise ValueError("Slope direction must be higher_is_better or lower_is_better")
    records = []
    for painting_id, group in frame.groupby("painting_id", sort=True):
        x = pd.to_numeric(group[exposure_column], errors="coerce").to_numpy(float)
        y = pd.to_numeric(group[value_column], errors="coerce").to_numpy(float)
        native = theil_sen_slope(x, y)
        adverse = native if direction == "lower_is_better" else -native
        records.append(
            {
                "painting_id": str(painting_id),
                "slope_per_fraction": native,
                "adverse_slope_per_fraction": adverse,
                "adverse_slope_per_reporting_interval": adverse * float(reporting_scale_percentage_points) / 100.0,
                "level_count": int(np.sum(np.isfinite(x) & np.isfinite(y))),
            }
        )
    return pd.DataFrame(records)


def summarise_painting_slopes(
    slopes: pd.DataFrame,
    *,
    confidence_level: float = 0.95,
) -> dict[str, float | int]:
    """Summarize five painting slopes with exact bootstrap and sign-flip evidence."""

    _require_columns(slopes, ("painting_id", "adverse_slope_per_reporting_interval"), "painting slopes")
    values = pd.to_numeric(slopes["adverse_slope_per_reporting_interval"], errors="coerce").to_numpy(float)
    values = values[np.isfinite(values)]
    bootstrap = exhaustive_bootstrap_interval(values, confidence_level=confidence_level)
    test = exact_sign_flip_test(values)
    return {
        **bootstrap,
        "p_value": float(test["p_value"]),
        "sign_flip_assignments": int(test["assignments"]),
        "rank_biserial": matched_rank_biserial(values),
        "positive_direction_count": int(np.sum(values > 0)),
        "negative_direction_count": int(np.sum(values < 0)),
        "painting_count": int(len(values)),
    }


def compute_adjacent_changes(
    frame: pd.DataFrame,
    *,
    value_column: str = "comparison_value",
    direction: str,
    level_column: str = "target_damage_fraction",
) -> pd.DataFrame:
    """Compute raw and percentage-point-normalized adjacent changes per painting."""

    _require_columns(frame, ("painting_id", level_column, value_column), "adjacent-change input")
    if direction not in {"higher_is_better", "lower_is_better"}:
        raise ValueError("Adjacent-change direction is invalid")
    records: list[dict[str, Any]] = []
    for painting_id, group in frame.groupby("painting_id", sort=True):
        ordered = group.assign(
            _level=pd.to_numeric(group[level_column], errors="coerce"),
            _value=pd.to_numeric(group[value_column], errors="coerce"),
        ).dropna(subset=["_level", "_value"]).sort_values("_level", kind="stable")
        if ordered["_level"].duplicated().any():
            raise ValueError(f"Adjacent-change input has duplicate levels for {painting_id}")
        values = ordered[["_level", "_value"]].to_numpy(float)
        for (start, start_value), (end, end_value) in zip(values[:-1], values[1:]):
            raw = float(end_value - start_value)
            adverse = raw if direction == "lower_is_better" else -raw
            interval_pp = float((end - start) * 100.0)
            records.append(
                {
                    "painting_id": str(painting_id),
                    "interval_start_fraction": float(start),
                    "interval_end_fraction": float(end),
                    "interval_percentage_points": interval_pp,
                    "raw_change": raw,
                    "adverse_change": adverse,
                    "adverse_change_per_percentage_point": adverse / interval_pp,
                }
            )
    return pd.DataFrame(records)


def family_balanced_ranks(
    anchor_rows: pd.DataFrame,
    *,
    rank_method: str = "average",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rank models per anchor, then give each evidence family one equal contribution."""

    _require_columns(
        anchor_rows,
        ("model_id", "painting_id", "evidence_family", "anchor_id",
         "comparison_direction", "comparison_value"),
        "ranking input",
    )
    summary = (
        anchor_rows.groupby(
            ["evidence_family", "anchor_id", "comparison_direction", "model_id"],
            dropna=False,
        )["comparison_value"]
        .median()
        .reset_index(name="model_median")
    )
    summary["anchor_rank"] = np.nan
    for _, indices in summary.groupby(["evidence_family", "anchor_id", "comparison_direction"], dropna=False).groups.items():
        positions = list(indices)
        direction = str(summary.loc[positions[0], "comparison_direction"])
        ascending = direction == "lower_is_better"
        summary.loc[positions, "anchor_rank"] = summary.loc[positions, "model_median"].rank(
            method=rank_method, ascending=ascending
        )
    family = (
        summary.groupby(["evidence_family", "model_id"], dropna=False)["anchor_rank"]
        .mean()
        .reset_index(name="family_rank")
    )
    overall = (
        family.groupby("model_id", dropna=False)["family_rank"]
        .mean()
        .reset_index(name="family_balanced_rank")
    )
    overall["overall_rank"] = overall["family_balanced_rank"].rank(method=rank_method, ascending=True)
    return summary.sort_values(["anchor_id", "anchor_rank"], kind="stable"), overall.sort_values(
        ["overall_rank", "model_id"], kind="stable"
    )


def size_and_painting_adjusted_spearman(
    frame: pd.DataFrame,
    *,
    morphology_column: str,
    outcome_column: str,
    size_column: str = "realized_damage_fraction",
) -> dict[str, float | int]:
    """Return an exploratory Spearman association after fixed-effect residualization."""

    _require_columns(frame, ("painting_id", morphology_column, outcome_column, size_column), "morphology association input")
    working = frame[["painting_id", morphology_column, outcome_column, size_column]].copy()
    for column in (morphology_column, outcome_column, size_column):
        working[column] = pd.to_numeric(working[column], errors="coerce")
    working = working.dropna()
    if len(working) < 4 or working[morphology_column].nunique() < 2 or working[outcome_column].nunique() < 2:
        return {"rho": np.nan, "p_value": np.nan, "observation_count": int(len(working))}
    dummies = pd.get_dummies(working["painting_id"].astype(str), drop_first=True, dtype=float)
    design = np.column_stack(
        [np.ones(len(working)), working[size_column].to_numpy(float), dummies.to_numpy(float)]
    )

    def residuals(column: str) -> np.ndarray:
        values = working[column].to_numpy(float)
        coefficients, *_ = np.linalg.lstsq(design, values, rcond=None)
        return values - design @ coefficients

    rho, p_value = spearmanr(residuals(morphology_column), residuals(outcome_column))
    return {"rho": float(rho), "p_value": float(p_value), "observation_count": int(len(working))}


def empty_analysis_frame() -> pd.DataFrame:
    """Return an empty canonical Notebook 23 analysis table."""

    return pd.DataFrame(columns=ANALYSIS_COLUMNS)


def validate_damage_size_analysis(frame: pd.DataFrame, *, config: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the canonical long analysis table and scientific prohibitions."""

    missing = sorted(set(ANALYSIS_COLUMNS) - set(frame.columns))
    allowed_kinds = set(map(str, _settings(config)["analysis_kinds"]))
    ids_unique = "analysis_row_id" in frame and not frame["analysis_row_id"].astype(str).duplicated().any()
    kinds_valid = "analysis_kind" in frame and set(frame["analysis_kind"].dropna().astype(str)).issubset(allowed_kinds)
    schema_valid = "schema_version" in frame and frame["schema_version"].astype(str).eq(ANALYSIS_SCHEMA_VERSION).all()
    p_values = pd.to_numeric(frame.get("p_value", pd.Series(dtype=float)), errors="coerce")
    q_values = pd.to_numeric(frame.get("q_value", pd.Series(dtype=float)), errors="coerce")
    probabilities_valid = bool(
        p_values.dropna().between(0.0, 1.0).all() and q_values.dropna().between(0.0, 1.0).all()
    )
    no_combined = not frame.astype(str).apply(
        lambda column: column.str.contains("combined_quality|combined_uncertainty|trust_score", case=False, regex=True)
    ).any().any() if not frame.empty else True
    status_valid = "status" in frame and set(frame["status"].dropna().astype(str)).issubset({"ok", "not_applicable"})
    return {
        "passed": not missing and ids_unique and kinds_valid and schema_valid and probabilities_valid and no_combined and status_valid,
        "missing_columns": missing,
        "analysis_ids_unique": ids_unique,
        "analysis_kinds_valid": kinds_valid,
        "schema_version_valid": schema_valid,
        "probabilities_valid": probabilities_valid,
        "no_combined_score_or_index": no_combined,
        "status_valid": status_valid,
        "row_count": int(len(frame)),
    }


def validate_damage_size_report_html(html_text: str, *, config: Mapping[str, Any]) -> pd.DataFrame:
    """Validate self-contained report density and required thesis framing."""

    return validate_self_contained_report_html(
        html_text, config=build_multi_model_adapter_config(config)
    )


def atomic_write_csv(frame: pd.DataFrame, output_path: str | Path) -> Path:
    """Write a CSV atomically without retaining temporary output."""

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
    "ANALYSIS_COLUMNS",
    "ANALYSIS_SCHEMA_VERSION",
    "CONFIG_SCHEMA_VERSION",
    "MODULE_NAME",
    "MODULE_VERSION",
    "UNCERTAINTY_GROUP_COLUMNS",
    "atomic_write_csv",
    "benjamini_hochberg",
    "build_multi_model_adapter_config",
    "build_runtime_evidence",
    "compute_adjacent_changes",
    "compute_painting_slopes",
    "empty_analysis_frame",
    "exact_sign_flip_test",
    "exhaustive_bootstrap_interval",
    "family_balanced_ranks",
    "image_grid_to_data_uri",
    "image_path_to_data_uri",
    "load_damage_size_analysis_config",
    "matched_rank_biserial",
    "normalise_quality_evidence",
    "normalise_uncertainty_evidence",
    "resolve_analysis_inputs",
    "select_damage_size_population",
    "size_and_painting_adjusted_spearman",
    "summarise_painting_slopes",
    "theil_sen_slope",
    "validate_damage_size_analysis",
    "validate_damage_size_report_html",
    "validate_upstream_run_manifests",
]
