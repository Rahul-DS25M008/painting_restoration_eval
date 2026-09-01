"""Matched mask-placement robustness utilities for Notebook 24.

The module selects the fixed five-variant population created by Notebook 06,
normalizes already-computed metric evidence, and supplies deterministic
dispersion, ranking, exact-inference, and report-validation helpers. It does
not run restoration models and never writes into frozen upstream output roots.
"""

from __future__ import annotations

import hashlib
import os
from itertools import product
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml
from scipy.stats import spearmanr

from .damage_size_analysis import (
    benjamini_hochberg,
    exact_sign_flip_test,
    exhaustive_bootstrap_interval,
    family_balanced_ranks,
    matched_rank_biserial,
)
from .multi_model_comparison import (
    normalise_runtime_evidence,
    normalise_spatial_diagnostics,
    normalise_standard_metric_table,
    validate_self_contained_report_html,
)
from .paths import find_project_root, resolve_repo_path


MODULE_NAME = "restoration_eval.mask_robustness_analysis"
MODULE_VERSION = "1.0.0"
CONFIG_SCHEMA_VERSION = "mask_robustness_analysis_config.v1"
ANALYSIS_SCHEMA_VERSION = "mask_robustness_analysis.v1"

QUALITY_SOURCE_KEYS = (
    "classical",
    "perceptual",
    "feature",
    "spatial",
    "local_consistency",
    "semantic_structural",
)
STANDARD_SOURCE_KEYS = tuple(key for key in QUALITY_SOURCE_KEYS if key != "spatial")

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
    "painting_id",
    "category",
    "style_or_period",
    "mask_family",
    "robustness_group_id",
    "variant_id",
    "case_id",
    "target_damage_fraction",
    "realized_damage_fraction",
    "morphology_field",
    "scope_type",
    "scope_value",
    "independent_unit",
    "n_paintings",
    "n_groups",
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

DISPERSION_NAMES = (
    "standard_deviation",
    "median_absolute_deviation",
    "range",
)


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    settings = config.get("mask_robustness_analysis", config)
    if not isinstance(settings, Mapping):
        raise TypeError("mask_robustness_analysis settings must be a mapping")
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


def load_mask_robustness_analysis_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the approved Notebook 24 contract."""

    with Path(path).open("r", encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Mask-robustness configuration must be a mapping")
    if config.get("config_schema_version") != CONFIG_SCHEMA_VERSION:
        raise ValueError("Unsupported mask-robustness config schema")
    settings = _settings(config)
    required = {
        "notebook_id", "notebook_stem", "analysis_schema_version", "inputs",
        "output", "population", "evidence_sources", "metric_direction",
        "spatial_metric_fields", "quality_anchors", "statistics", "morphology",
        "analysis_kinds", "report", "expected_counts", "evidence_policy",
        "known_limitations",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"Mask-robustness config is missing keys: {missing}")
    if settings["notebook_id"] != "24" or settings["notebook_stem"] != "24_mask_robustness_analysis":
        raise ValueError("Notebook 24 identity contract changed")
    if settings["analysis_schema_version"] != ANALYSIS_SCHEMA_VERSION:
        raise ValueError("Configured analysis schema version does not match helper")
    for key, value in settings["inputs"].items():
        if not _normalized_relative_path(value):
            raise ValueError(f"inputs.{key} must be a normalized repository-relative path")

    output = settings["output"]
    expected_output = {
        "root": "outputs/24_mask_robustness_analysis",
        "metrics_path": "metrics/mask_robustness_analysis.csv",
        "robustness_figure_path": "figures/robustness_variance.png",
        "ranking_figure_path": "figures/ranking_stability.png",
        "report_path": "reports/mask_robustness_analysis.html",
        "run_manifest_path": "manifests/run_manifest.json",
        "artifacts_path": "manifests/artifacts.csv",
        "validation_path": "validation/checks.csv",
    }
    for key, value in expected_output.items():
        if output.get(key) != value:
            raise ValueError(f"output.{key} must equal {value!r}")

    population = settings["population"]
    expected = settings["expected_counts"]
    if list(map(str, population["model_order"])) != [
        "opencv_telea", "lama", "stable_diffusion_inpainting"
    ]:
        raise ValueError("Model order or scope changed")
    if int(expected["robustness_groups"]) != int(expected["paintings"]) * int(expected["mask_families"]):
        raise ValueError("Robustness-group arithmetic is inconsistent")
    if int(expected["cases"]) != int(expected["robustness_groups"]) * int(expected["variants_per_group"]):
        raise ValueError("Mask-variant case arithmetic is inconsistent")
    if int(expected["candidates"]) != int(expected["cases"]) * len(population["model_order"]):
        raise ValueError("Candidate arithmetic is inconsistent")
    if sum(map(int, expected["candidates_by_model"].values())) != int(expected["candidates"]):
        raise ValueError("Per-model candidate arithmetic is inconsistent")
    if int(expected["selected_metric_source_rows"]) != sum(
        int(expected[key]) for key in (
            "selected_classical_source_rows", "selected_lpips_source_rows",
            "selected_feature_source_rows", "selected_spatial_source_rows",
            "selected_local_source_rows", "selected_semantic_source_rows",
        )
    ):
        raise ValueError("Selected metric-source arithmetic is inconsistent")
    analysis_parts = (
        "variant_quality_rows", "group_quality_dispersion_rows",
        "model_dispersion_summary_rows", "paired_model_dispersion_contrast_rows",
        "variant_family_balanced_rank_rows", "group_rank_stability_rows",
        "anchor_winner_stability_rows", "group_sensitivity_summary_rows",
        "morphology_association_rows", "runtime_group_dispersion_rows",
        "runtime_model_summary_rows",
    )
    if sum(int(expected[key]) for key in analysis_parts) != int(expected["canonical_analysis_rows"]):
        raise ValueError("Canonical analysis-row arithmetic is inconsistent")
    if len(settings["quality_anchors"]) != int(expected["quality_anchors"]):
        raise ValueError("Quality-anchor count is inconsistent")
    anchor_ids = [str(item["anchor_id"]) for item in settings["quality_anchors"]]
    if len(anchor_ids) != len(set(anchor_ids)):
        raise ValueError("Quality-anchor IDs must be unique")
    if int(settings["statistics"]["bootstrap_resamples"]) != int(expected["paintings"]) ** int(expected["paintings"]):
        raise ValueError("Exhaustive bootstrap count is inconsistent")
    if int(settings["statistics"]["sign_flip_assignments"]) != 2 ** int(expected["paintings"]):
        raise ValueError("Sign-flip assignment count is inconsistent")
    if bool(settings["statistics"]["combined_quality_score_retained"]):
        raise ValueError("A combined quality score is prohibited")
    if bool(settings["statistics"]["use_uncertainty_terminology"]):
        raise ValueError("Mask robustness must not be labeled stochastic uncertainty")
    report = settings["report"]
    if not bool(report["self_contained_html"] and report["approved_mock_structure_locked"]):
        raise ValueError("The report must remain self-contained and mock-aligned")
    prohibited = (
        "independent_mask_family_effect_permitted", "independent_damage_size_effect_permitted",
        "category_effect_permitted", "style_effect_permitted",
        "stochastic_uncertainty_claim_permitted", "historical_authenticity_claim_permitted",
        "conservation_approval_claim_permitted", "runtime_is_quality_evidence",
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
    """Resolve every declared input without dynamic file discovery."""

    root = find_project_root(project_root)
    return {
        str(key): resolve_repo_path(value, root, must_exist=must_exist)
        for key, value in _settings(config)["inputs"].items()
    }


def build_multi_model_adapter_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Expose Notebook 21 normalizer settings under their expected keys."""

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
        "06", "08", "09", "10", "11", "13", "14", "15", "16", "17", "20", "21",
    ),
) -> pd.DataFrame:
    """Return one completion-gate row per direct upstream notebook."""

    records: list[dict[str, Any]] = []
    for notebook_id in expected_notebook_ids:
        manifest = manifests.get(str(notebook_id))
        present = isinstance(manifest, Mapping)
        records.append(
            {
                "notebook_id": str(notebook_id),
                "manifest_present": present,
                "run_status": str(manifest.get("run_status", "")) if present else "",
                "validation_status": str(manifest.get("validation_status", "")) if present else "",
                "completion_gate_passed": bool(manifest.get("completion_gate_passed", False)) if present else False,
            }
        )
    result = pd.DataFrame(records)
    result["passed"] = (
        result["manifest_present"]
        & result["run_status"].eq("completed")
        & result["validation_status"].eq("passed")
        & result["completion_gate_passed"]
    )
    return result


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


def select_mask_robustness_population(
    cases: pd.DataFrame,
    artworks: pd.DataFrame,
    opencv: pd.DataFrame,
    lama: pd.DataFrame,
    stable_diffusion: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select one approved primary candidate per model and mask-variant case."""

    settings = _settings(config)
    population = settings["population"]
    expected = settings["expected_counts"]
    _require_columns(
        cases,
        (
            "case_id", "robustness_group_id", "variant_id", "variant_index",
            "painting_id", "mask_type", "experiment_id", "target_damage_fraction",
            "realized_damage_fraction", "damaged_image_path", "clean_image_path",
            "mask_path", "status",
        ),
        "mask-robustness cases",
    )
    _require_columns(artworks, ("painting_id", "category", "style_or_period"), "artworks")
    case_rows = cases.loc[
        cases["experiment_id"].astype(str).eq(str(population["experiment_id"]))
        & cases["status"].astype(str).eq(str(population["passed_status"]))
        & cases["painting_id"].astype(str).isin(set(map(str, population["painting_ids"])))
    ].copy()
    if len(case_rows) != int(expected["cases"]) or case_rows["case_id"].duplicated().any():
        raise ValueError("Mask-robustness population is not exactly 75 unique cases")
    if case_rows["robustness_group_id"].nunique() != int(expected["robustness_groups"]):
        raise ValueError("Robustness-group count differs from contract")
    group_sizes = case_rows.groupby("robustness_group_id").size()
    if not group_sizes.eq(int(expected["variants_per_group"])).all():
        raise ValueError("Every robustness group must contain exactly five variants")
    if case_rows.duplicated(["robustness_group_id", "variant_id"]).any():
        raise ValueError("Variant IDs are not unique within robustness groups")
    target_map = {str(key): float(value) for key, value in population["target_damage_fraction_by_family"].items()}
    observed_families = set(case_rows["mask_type"].astype(str))
    if observed_families != set(target_map):
        raise ValueError("Mask-family population differs from contract")
    for family, target in target_map.items():
        values = pd.to_numeric(
            case_rows.loc[case_rows["mask_type"].astype(str).eq(family), "target_damage_fraction"],
            errors="coerce",
        )
        if not np.isclose(values, target, atol=1e-12, rtol=0.0).all():
            raise ValueError(f"{family} is not fixed to its approved target area")

    metadata = artworks[["painting_id", "category", "style_or_period"]].drop_duplicates("painting_id")
    case_rows = case_rows.merge(metadata, on="painting_id", how="left", suffixes=("", "__art"), validate="many_to_one")
    if "category__art" in case_rows:
        case_rows["category"] = case_rows["category__art"].fillna(case_rows.get("category"))
    if "style_or_period__art" in case_rows:
        case_rows["style_or_period"] = case_rows["style_or_period__art"]
    case_rows["style_or_period"] = case_rows["style_or_period"].fillna("unclassified")
    case_ids = set(case_rows["case_id"].astype(str))

    def deterministic(frame: pd.DataFrame, model_id: str, notebook_id: str) -> pd.DataFrame:
        _require_columns(
            frame,
            ("case_id", "candidate_id", "model_id", "restored_path", "runtime_seconds", "status"),
            model_id,
        )
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
        (
            "case_id", "candidate_id", "model_id", "restored_path", "runtime_seconds",
            "status", "experiment_id", "execution_role", "prompt_variant_id", "seed",
            "is_primary_candidate",
        ),
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
    selected = selected.merge(case_rows, on="case_id", how="inner", suffixes=("", "__case"), validate="many_to_one")
    case_authority = {
        "painting_id": "painting_id",
        "category": "category",
        "style_or_period": "style_or_period",
        "experiment_id": "experiment_id",
        "robustness_group_id": "robustness_group_id",
        "variant_id": "variant_id",
        "variant_index": "variant_index",
        "mask_type": "mask_family",
        "target_damage_fraction": "target_damage_fraction",
        "realized_damage_fraction": "realized_damage_fraction",
        "damaged_image_path": "input_image_path",
        "clean_image_path": "clean_image_path",
        "mask_path": "mask_or_effect_path",
    }
    for source, destination in case_authority.items():
        authoritative = f"{source}__case"
        if authoritative in selected:
            selected[destination] = selected[authoritative]
        elif source in selected:
            selected[destination] = selected[source]
    selected["mask_type"] = selected["mask_family"]
    selected["damage_or_degradation_type"] = selected["mask_family"]
    selected["damage_type"] = selected["mask_family"]
    selected["degradation_type"] = "not_applicable"
    selected["severity"] = "not_applicable"
    selected["is_zero_control"] = False
    selected["dataset_scope"] = str(population["dataset_scope"])
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
        if set(selected.loc[selected["model_id"].eq(model_id), "case_id"].astype(str)) != case_ids:
            raise ValueError(f"{model_id} does not cover the exact 75 matched cases")
    if selected["candidate_id"].duplicated().any():
        raise ValueError("Selected candidate IDs are not unique")
    return selected.sort_values(
        ["painting_id", "mask_family", "variant_index", "model_id"], kind="stable"
    ).reset_index(drop=True)


def normalise_quality_evidence(
    source_tables: Mapping[str, pd.DataFrame],
    selected_candidates: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Normalize all eligible quality evidence after candidate selection."""

    settings = _settings(config)
    expected = settings["expected_counts"]
    missing = sorted(set(QUALITY_SOURCE_KEYS) - set(source_tables))
    if missing:
        raise ValueError(f"Missing quality source tables: {missing}")
    adapter = build_multi_model_adapter_config(config)
    expected_rows = {
        "classical": int(expected["selected_classical_source_rows"]),
        "perceptual": int(expected["selected_lpips_source_rows"]),
        "feature": int(expected["selected_feature_source_rows"]),
        "local_consistency": int(expected["selected_local_source_rows"]),
        "semantic_structural": int(expected["selected_semantic_source_rows"]),
    }
    frames: list[pd.DataFrame] = []
    for key in STANDARD_SOURCE_KEYS:
        normalized = normalise_standard_metric_table(
            source_tables[key], selected_candidates, source_key=key, config=adapter
        )
        if len(normalized) != expected_rows[key]:
            raise ValueError(f"{key} selected row count {len(normalized)} != {expected_rows[key]}")
        normalized["source_key"] = key
        frames.append(normalized)
    selected_ids = set(selected_candidates["candidate_id"].astype(str))
    spatial_source = source_tables["spatial"]
    spatial_source_count = int(spatial_source["candidate_id"].astype(str).isin(selected_ids).sum())
    if spatial_source_count != int(expected["selected_spatial_source_rows"]):
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
        raise ValueError("Normalized source row IDs are not unique")
    values = pd.to_numeric(result["comparison_value"], errors="coerce")
    result["analysis_eligible"] = (
        result["status"].astype(str).eq("ok")
        & np.isfinite(values)
        & result["comparison_direction"].isin(["higher_is_better", "lower_is_better"])
    )
    result["directional_utility"] = np.where(
        result["comparison_direction"].eq("higher_is_better"), values, -values
    )
    return result.sort_values(["source_notebook_id", "source_metric_row_id"], kind="stable").reset_index(drop=True)


def select_quality_anchor_values(
    normalized_quality: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Return exactly one value for every candidate and approved quality anchor."""

    expected = _settings(config)["expected_counts"]
    _require_columns(
        normalized_quality,
        (
            "candidate_id", "case_id", "model_id", "painting_id", "anchor_id",
            "evidence_family", "comparison_direction", "comparison_value",
            "analysis_eligible",
        ),
        "normalized quality evidence",
    )
    anchors = normalized_quality.loc[
        normalized_quality["anchor_id"].fillna("").astype(str).ne("")
        & _bool_series(normalized_quality["analysis_eligible"])
    ].copy()
    anchors["comparison_value"] = pd.to_numeric(anchors["comparison_value"], errors="coerce")
    if len(anchors) != int(expected["variant_quality_rows"]):
        raise ValueError("Anchor-value population differs from the approved 2,475 rows")
    if anchors.duplicated(["candidate_id", "anchor_id"], keep=False).any():
        raise ValueError("Candidate/anchor keys are not unique")
    if anchors["candidate_id"].nunique() != int(expected["candidates"]):
        raise ValueError("Not every selected candidate has anchor evidence")
    return anchors.reset_index(drop=True)


def build_runtime_evidence(
    selected_candidates: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Normalize runtime as operational evidence excluded from quality ranks."""

    result = normalise_runtime_evidence(
        selected_candidates, config=build_multi_model_adapter_config(config)
    )
    expected = int(_settings(config)["expected_counts"]["runtime_rows"])
    if len(result) != expected or result["quality_ranking_eligible"].astype(bool).any():
        raise ValueError("Runtime evidence violates the Notebook 24 contract")
    return result


def dispersion_statistics(values: Sequence[float]) -> dict[str, float]:
    """Compute the three transparent within-group dispersion statistics."""

    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    if array.size == 0:
        return {name: np.nan for name in DISPERSION_NAMES}
    median = float(np.median(array))
    return {
        "standard_deviation": float(np.std(array, ddof=1)) if array.size > 1 else 0.0,
        "median_absolute_deviation": float(np.median(np.abs(array - median))),
        "range": float(np.max(array) - np.min(array)),
    }


def compute_group_dispersion(
    anchor_rows: pd.DataFrame,
    *,
    group_columns: Sequence[str] = (
        "robustness_group_id", "painting_id", "mask_family", "model_id",
        "evidence_family", "anchor_id", "comparison_direction",
    ),
) -> pd.DataFrame:
    """Return SD, MAD, and range for every five-variant model/anchor group."""

    _require_columns(anchor_rows, (*group_columns, "comparison_value", "variant_id"), "anchor rows")
    records: list[dict[str, Any]] = []
    for keys, group in anchor_rows.groupby(list(group_columns), dropna=False, sort=False):
        key_values = keys if isinstance(keys, tuple) else (keys,)
        base = dict(zip(group_columns, key_values))
        if len(group) != 5 or group["variant_id"].astype(str).nunique() != 5:
            raise ValueError("Every dispersion group must contain five distinct variants")
        for statistic, value in dispersion_statistics(group["comparison_value"]).items():
            records.append({**base, "dispersion_statistic": statistic, "dispersion_value": value, "variant_count": 5})
    return pd.DataFrame(records)


def compute_variant_family_balanced_ranks(anchor_rows: pd.DataFrame) -> pd.DataFrame:
    """Rank three models for each variant case with equal family contributions."""

    _require_columns(anchor_rows, ("case_id", "robustness_group_id", "variant_id"), "anchor rows")
    records: list[pd.DataFrame] = []
    for (case_id, group_id, variant_id), group in anchor_rows.groupby(
        ["case_id", "robustness_group_id", "variant_id"], sort=False
    ):
        _, ranks = family_balanced_ranks(group)
        ranks["case_id"] = str(case_id)
        ranks["robustness_group_id"] = str(group_id)
        ranks["variant_id"] = str(variant_id)
        records.append(ranks)
    return pd.concat(records, ignore_index=True, sort=False)


def within_group_centered_spearman(
    frame: pd.DataFrame,
    *,
    morphology_column: str,
    outcome_column: str,
    group_column: str = "robustness_group_id",
    painting_column: str = "painting_id",
) -> dict[str, Any]:
    """Associate geometry and outcome after removing each matched-group mean.

    The point estimate uses all centered observations. Its interval resamples
    the five paintings exhaustively as clusters. This remains exploratory and
    does not identify an independent causal morphology effect.
    """

    _require_columns(
        frame,
        (group_column, painting_column, morphology_column, outcome_column),
        "morphology association input",
    )
    working = frame[[group_column, painting_column, morphology_column, outcome_column]].copy()
    working[morphology_column] = pd.to_numeric(working[morphology_column], errors="coerce")
    working[outcome_column] = pd.to_numeric(working[outcome_column], errors="coerce")
    working = working.dropna()
    if working.empty:
        return {
            "rho": np.nan, "ci_lower": np.nan, "ci_upper": np.nan,
            "painting_count": 0, "observation_count": 0, "bootstrap_resamples": 0,
            "applicability_status": "not_applicable_no_finite_values",
        }
    for column in (morphology_column, outcome_column):
        working[f"{column}__centered"] = working[column] - working.groupby(group_column)[column].transform("mean")
    x_column = f"{morphology_column}__centered"
    y_column = f"{outcome_column}__centered"
    if working[x_column].nunique() < 2 or working[y_column].nunique() < 2:
        return {
            "rho": np.nan, "ci_lower": np.nan, "ci_upper": np.nan,
            "painting_count": int(working[painting_column].nunique()),
            "observation_count": int(len(working)), "bootstrap_resamples": 0,
            "applicability_status": "not_applicable_invariant_field",
        }
    rho = float(spearmanr(working[x_column], working[y_column]).statistic)
    painting_ids = sorted(working[painting_column].astype(str).unique())
    if len(painting_ids) != 5:
        raise ValueError("Morphology inference requires exactly five painting clusters")
    bootstrap_values: list[float] = []
    for sample in product(painting_ids, repeat=len(painting_ids)):
        pieces = []
        for draw_index, painting_id in enumerate(sample):
            piece = working.loc[working[painting_column].astype(str).eq(painting_id)].copy()
            piece[painting_column] = f"draw_{draw_index}_{painting_id}"
            pieces.append(piece)
        sampled = pd.concat(pieces, ignore_index=True)
        value = spearmanr(sampled[x_column], sampled[y_column]).statistic
        if np.isfinite(value):
            bootstrap_values.append(float(value))
    if not bootstrap_values:
        lower = upper = np.nan
    else:
        lower, upper = np.quantile(bootstrap_values, [0.025, 0.975]).tolist()
    return {
        "rho": rho,
        "ci_lower": float(lower),
        "ci_upper": float(upper),
        "painting_count": 5,
        "observation_count": int(len(working)),
        "bootstrap_resamples": int(len(bootstrap_values)),
        "applicability_status": "applicable",
    }


def empty_analysis_frame() -> pd.DataFrame:
    """Return an empty canonical Notebook 24 analysis table."""

    return pd.DataFrame(columns=ANALYSIS_COLUMNS)


def validate_mask_robustness_analysis(
    frame: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    require_complete: bool = False,
) -> dict[str, Any]:
    """Validate schema, scientific prohibitions, IDs, and optional row contract."""

    settings = _settings(config)
    missing = sorted(set(ANALYSIS_COLUMNS) - set(frame.columns))
    ids_unique = "analysis_row_id" in frame and not frame["analysis_row_id"].astype(str).duplicated().any()
    kinds_valid = "analysis_kind" in frame and set(frame["analysis_kind"].dropna().astype(str)).issubset(
        set(map(str, settings["analysis_kinds"]))
    )
    schema_valid = "schema_version" in frame and frame["schema_version"].astype(str).eq(ANALYSIS_SCHEMA_VERSION).all()
    p_values = pd.to_numeric(frame.get("p_value", pd.Series(dtype=float)), errors="coerce")
    q_values = pd.to_numeric(frame.get("q_value", pd.Series(dtype=float)), errors="coerce")
    probabilities_valid = bool(
        p_values.dropna().between(0.0, 1.0).all() and q_values.dropna().between(0.0, 1.0).all()
    )
    no_prohibited = not frame.astype(str).apply(
        lambda column: column.str.contains(
            "combined_quality|combined_uncertainty|trust_score|calibrated confidence",
            case=False,
            regex=True,
        )
    ).any().any() if not frame.empty else True
    status_valid = "status" in frame and set(frame["status"].dropna().astype(str)).issubset({"ok", "not_applicable"})
    expected_rows = int(settings["expected_counts"]["canonical_analysis_rows"])
    row_count_valid = len(frame) == expected_rows if require_complete else True
    kind_counts_valid = True
    if require_complete and "analysis_kind" in frame:
        expected = settings["expected_counts"]
        expected_by_kind = {
            kind: int(expected[f"{kind}_rows"])
            for kind in settings["analysis_kinds"]
        }
        observed = frame.groupby("analysis_kind").size().to_dict()
        kind_counts_valid = observed == expected_by_kind
    passed = (
        not missing and ids_unique and kinds_valid and schema_valid
        and probabilities_valid and no_prohibited and status_valid
        and row_count_valid and kind_counts_valid
    )
    return {
        "passed": passed,
        "missing_columns": missing,
        "analysis_ids_unique": ids_unique,
        "analysis_kinds_valid": kinds_valid,
        "schema_version_valid": schema_valid,
        "probabilities_valid": probabilities_valid,
        "no_prohibited_score_or_claim": no_prohibited,
        "status_valid": status_valid,
        "row_count_valid": row_count_valid,
        "analysis_kind_counts_valid": kind_counts_valid,
        "row_count": int(len(frame)),
    }


def validate_mask_robustness_report_html(
    html_text: str,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Validate self-containment, visual density, and approved mock sections."""

    base = validate_self_contained_report_html(
        html_text, config=build_multi_model_adapter_config(config)
    )
    report = _settings(config)["report"]
    lowered = html_text.lower()
    section_checks = pd.DataFrame(
        [
            {
                "check_id": f"report_section_{section_id}",
                "passed": section_id.lower() in lowered,
                "severity": "blocking",
                "details": f"Approved mock section marker: {section_id}",
            }
            for section_id in report["required_section_ids"]
        ]
    )
    return pd.concat([base, section_checks], ignore_index=True, sort=False)


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
    "DISPERSION_NAMES",
    "MODULE_NAME",
    "MODULE_VERSION",
    "atomic_write_csv",
    "benjamini_hochberg",
    "build_multi_model_adapter_config",
    "build_runtime_evidence",
    "compute_group_dispersion",
    "compute_variant_family_balanced_ranks",
    "dispersion_statistics",
    "empty_analysis_frame",
    "exact_sign_flip_test",
    "exhaustive_bootstrap_interval",
    "family_balanced_ranks",
    "load_mask_robustness_analysis_config",
    "matched_rank_biserial",
    "normalise_quality_evidence",
    "resolve_analysis_inputs",
    "select_mask_robustness_population",
    "select_quality_anchor_values",
    "validate_mask_robustness_analysis",
    "validate_mask_robustness_report_html",
    "validate_upstream_run_manifests",
    "within_group_centered_spearman",
]
