"""Eligibility-gated synthetic-degradation analysis utilities for Notebook 25.

The module selects the fixed localized degradation population created by
Notebook 07 and approved by Notebook 08, normalizes already-computed model and
metric evidence, and provides deterministic statistical and report-validation
helpers. It does not run restoration inference and never writes into frozen
upstream output roots.
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
    compute_painting_slopes,
    exact_sign_flip_test,
    exhaustive_bootstrap_interval,
    family_balanced_ranks,
    matched_rank_biserial,
    summarise_painting_slopes,
    theil_sen_slope,
)
from .multi_model_comparison import (
    normalise_runtime_evidence,
    normalise_spatial_diagnostics,
    normalise_standard_metric_table,
    validate_self_contained_report_html,
)
from .paths import find_project_root, resolve_repo_path


MODULE_NAME = "restoration_eval.synthetic_degradation_analysis"
MODULE_VERSION = "1.0.0"
CONFIG_SCHEMA_VERSION = "synthetic_degradation_analysis_config.v1"
ANALYSIS_SCHEMA_VERSION = "synthetic_degradation_analysis.v1"

QUALITY_SOURCE_KEYS = (
    "classical",
    "perceptual",
    "feature",
    "spatial",
    "local_consistency",
    "semantic_structural",
)
STANDARD_SOURCE_KEYS = tuple(
    key for key in QUALITY_SOURCE_KEYS if key != "spatial"
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
    "painting_id",
    "category",
    "style_or_period",
    "degradation_family",
    "severity",
    "severity_rank",
    "is_combined",
    "component_degradation",
    "case_id",
    "candidate_id",
    "population_id",
    "coverage_role",
    "affected_content_fraction",
    "changed_content_fraction",
    "scope_type",
    "scope_value",
    "independent_unit",
    "n_paintings",
    "n_cases",
    "n_observations",
    "damaged_value",
    "restored_value",
    "improvement_value",
    "directional_utility",
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


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    settings = config.get("synthetic_degradation_analysis", config)
    if not isinstance(settings, Mapping):
        raise TypeError("synthetic_degradation_analysis settings must be a mapping")
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


def _require_columns(
    frame: pd.DataFrame,
    columns: Sequence[str],
    label: str,
) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing columns: {missing}")


def _normalized_relative_path(value: Any) -> bool:
    text = str(value).strip()
    return bool(text) and not Path(text).is_absolute() and "\\" not in text


def load_synthetic_degradation_analysis_config(
    path: str | Path,
) -> dict[str, Any]:
    """Load and strictly validate the approved Notebook 25 contract."""

    with Path(path).open("r", encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Synthetic-degradation configuration must be a mapping")
    if config.get("config_schema_version") != CONFIG_SCHEMA_VERSION:
        raise ValueError("Unsupported synthetic-degradation analysis config schema")

    settings = _settings(config)
    required = {
        "notebook_id",
        "notebook_stem",
        "analysis_schema_version",
        "inputs",
        "output",
        "population",
        "evidence_sources",
        "metric_direction",
        "spatial_metric_fields",
        "quality_anchors",
        "spillover",
        "statistics",
        "analysis_kinds",
        "report",
        "expected_counts",
        "evidence_policy",
        "known_limitations",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"Synthetic-degradation config is missing keys: {missing}")
    if settings["notebook_id"] != "25":
        raise ValueError("Notebook 25 identity contract changed")
    if settings["notebook_stem"] != "25_synthetic_degradation_analysis":
        raise ValueError("Notebook 25 stem changed")
    if settings["analysis_schema_version"] != ANALYSIS_SCHEMA_VERSION:
        raise ValueError("Configured analysis schema version does not match helper")

    for key, value in settings["inputs"].items():
        if not _normalized_relative_path(value):
            raise ValueError(
                f"inputs.{key} must be a normalized repository-relative path"
            )

    expected_output = {
        "root": "outputs/25_synthetic_degradation_analysis",
        "metrics_path": "metrics/degradation_analysis.csv",
        "performance_figure_path": "figures/degradation_performance.png",
        "failure_figure_path": "figures/degradation_failure_examples.png",
        "report_path": "reports/synthetic_degradation_analysis.html",
        "run_manifest_path": "manifests/run_manifest.json",
        "artifacts_path": "manifests/artifacts.csv",
        "validation_path": "validation/checks.csv",
    }
    for key, value in expected_output.items():
        if settings["output"].get(key) != value:
            raise ValueError(f"output.{key} must equal {value!r}")

    population = settings["population"]
    expected = settings["expected_counts"]
    if list(map(str, population["model_order"])) != [
        "opencv_telea",
        "lama",
        "stable_diffusion_inpainting",
    ]:
        raise ValueError("Core model order or scope changed")
    if list(map(str, population["all_model_order"])) != [
        "opencv_telea",
        "lama",
        "stable_diffusion_inpainting",
        "sdxl_inpainting",
    ]:
        raise ValueError("Four-model order or scope changed")
    if int(expected["eligible_case_model_rows"]) != (
        int(expected["eligible_cases"]) * len(population["all_model_order"])
    ):
        raise ValueError("Eligible case-model arithmetic is inconsistent")
    if int(expected["eligibility_case_model_rows"]) != (
        int(expected["generated_cases"]) * len(population["all_model_order"])
    ):
        raise ValueError("Eligibility audit arithmetic is inconsistent")
    if int(expected["selected_candidates"]) != (
        int(expected["core_candidates"]) + int(expected["sdxl_candidates"])
    ):
        raise ValueError("Selected-candidate arithmetic is inconsistent")
    if int(expected["four_model_subset_candidates"]) != (
        int(expected["four_model_subset_cases"]) * len(population["all_model_order"])
    ):
        raise ValueError("Four-model subset arithmetic is inconsistent")
    if sum(map(int, expected["candidates_by_model"].values())) != int(
        expected["selected_candidates"]
    ):
        raise ValueError("Per-model candidate arithmetic is inconsistent")
    if len(population["sdxl_case_ids"]) != int(expected["sdxl_candidates"]):
        raise ValueError("SDXL case registry count is inconsistent")
    if len(settings["quality_anchors"]) != int(expected["quality_anchors"]):
        raise ValueError("Quality-anchor count is inconsistent")
    anchor_ids = [str(item["anchor_id"]) for item in settings["quality_anchors"]]
    if len(anchor_ids) != len(set(anchor_ids)):
        raise ValueError("Quality-anchor IDs must be unique")

    selected_source_total = sum(
        int(expected[key])
        for key in (
            "selected_classical_source_rows",
            "selected_lpips_source_rows",
            "selected_feature_source_rows",
            "selected_spatial_source_rows",
            "selected_local_source_rows",
            "selected_semantic_source_rows",
        )
    )
    if selected_source_total != int(expected["selected_metric_source_rows"]):
        raise ValueError("Selected metric-source arithmetic is inconsistent")

    analysis_total = sum(
        int(expected[f"{kind}_rows"])
        for kind in settings["analysis_kinds"]
    )
    if analysis_total != int(expected["canonical_analysis_rows"]):
        raise ValueError("Canonical analysis-row arithmetic is inconsistent")
    if int(settings["statistics"]["bootstrap_resamples"]) != (
        int(expected["paintings"]) ** int(expected["paintings"])
    ):
        raise ValueError("Exhaustive bootstrap count is inconsistent")
    if int(settings["statistics"]["sign_flip_assignments"]) != (
        2 ** int(expected["paintings"])
    ):
        raise ValueError("Sign-flip assignment count is inconsistent")
    if bool(settings["statistics"]["combined_quality_score_retained"]):
        raise ValueError("A combined quality score is prohibited")
    if bool(settings["statistics"]["uncertainty_analysis_applicable"]):
        raise ValueError("Synthetic-degradation uncertainty evidence is unavailable")

    report = settings["report"]
    if not bool(report["self_contained_html"]):
        raise ValueError("The report must be self-contained")
    if not bool(report["approved_mock_structure_locked"]):
        raise ValueError("The approved report mock must remain structurally binding")
    prohibited = (
        "missing_region_claim_permitted",
        "exact_conservation_damage_claim_permitted",
        "physical_degradation_interaction_claim_permitted",
        "independent_category_effect_permitted",
        "independent_style_effect_permitted",
        "stochastic_uncertainty_claim_permitted",
        "full_sdxl_comparison_claim_permitted",
        "historical_authenticity_claim_permitted",
        "conservation_approval_claim_permitted",
        "runtime_is_quality_evidence",
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


def build_multi_model_adapter_config(
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Expose Notebook 21 normalizer settings under their expected key."""

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
        "01",
        "07",
        "08",
        "09",
        "10",
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
        "20",
        "21",
    ),
) -> pd.DataFrame:
    """Return one completion-gate row per direct computational producer."""

    records: list[dict[str, Any]] = []
    for notebook_id in expected_notebook_ids:
        manifest = manifests.get(str(notebook_id))
        present = isinstance(manifest, Mapping)
        records.append(
            {
                "notebook_id": str(notebook_id),
                "manifest_present": present,
                "run_status": (
                    str(manifest.get("run_status", "")) if present else ""
                ),
                "validation_status": (
                    str(manifest.get("validation_status", "")) if present else ""
                ),
                "completion_gate_passed": (
                    bool(manifest.get("completion_gate_passed", False))
                    if present
                    else False
                ),
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
    case_ids: set[str],
    model_id: str,
    notebook_id: str,
    completed_status: str,
) -> pd.DataFrame:
    _require_columns(
        frame,
        (
            "case_id",
            "candidate_id",
            "model_id",
            "restored_path",
            "runtime_seconds",
            "status",
        ),
        model_id,
    )
    subset = frame.loc[
        frame["case_id"].astype(str).isin(case_ids)
        & frame["model_id"].astype(str).eq(model_id)
        & frame["status"].astype(str).eq(completed_status)
    ].copy()
    subset["source_notebook_id"] = notebook_id
    return subset


def select_synthetic_degradation_population(
    cases: pd.DataFrame,
    artworks: pd.DataFrame,
    eligibility: pd.DataFrame,
    opencv: pd.DataFrame,
    lama: pd.DataFrame,
    stable_diffusion: pd.DataFrame,
    sdxl: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select the exact 150-candidate core and six-candidate SDXL populations."""

    settings = _settings(config)
    population = settings["population"]
    expected = settings["expected_counts"]
    _require_columns(
        cases,
        (
            "case_id",
            "painting_id",
            "category",
            "experiment_id",
            "degradation_family",
            "severity",
            "severity_rank",
            "is_combined",
            "component_degradations_json",
            "clean_image_path",
            "effect_mask_path",
            "degraded_image_path",
            "affected_content_fraction",
            "changed_content_fraction",
            "status",
        ),
        "synthetic-degradation cases",
    )
    _require_columns(
        eligibility,
        ("case_id", "model_id", "eligible", "eligibility_reason"),
        "model eligibility",
    )
    _require_columns(
        artworks,
        ("painting_id", "category", "style_or_period"),
        "artworks",
    )

    all_cases = cases.loc[
        cases["experiment_id"].astype(str).eq(str(population["experiment_id"]))
        & cases["status"].astype(str).eq(str(population["passed_status"]))
        & cases["painting_id"].astype(str).isin(
            set(map(str, population["painting_ids"]))
        )
    ].copy()
    if len(all_cases) != int(expected["generated_cases"]):
        raise ValueError("Notebook 07 synthetic-degradation population changed")
    if all_cases["case_id"].astype(str).duplicated().any():
        raise ValueError("Notebook 07 case IDs are not unique")

    all_case_ids = set(all_cases["case_id"].astype(str))
    eligible_rows = eligibility.loc[
        eligibility["case_id"].astype(str).isin(all_case_ids)
    ].copy()
    eligible_rows["eligible"] = _bool_series(eligible_rows["eligible"])
    if len(eligible_rows) != int(expected["eligibility_case_model_rows"]):
        raise ValueError("Synthetic-degradation eligibility ledger changed")
    true_rows = eligible_rows.loc[eligible_rows["eligible"]]
    if len(true_rows) != int(expected["eligible_case_model_rows"]):
        raise ValueError("Eligible case-model population changed")

    eligible_by_case = true_rows.groupby("case_id")["model_id"].nunique()
    eligible_case_ids = set(
        eligible_by_case.loc[
            eligible_by_case.eq(len(population["all_model_order"]))
        ].index.astype(str)
    )
    if len(eligible_case_ids) != int(expected["eligible_cases"]):
        raise ValueError("Expected exactly 50 cases eligible for all four models")

    approved_cases = all_cases.loc[
        all_cases["case_id"].astype(str).isin(eligible_case_ids)
    ].copy()
    observed_families = set(approved_cases["degradation_family"].astype(str))
    if observed_families != set(map(str, population["eligible_degradation_order"])):
        raise ValueError("Eligible degradation families changed")
    observed_family_counts = (
        approved_cases.groupby("degradation_family").size().to_dict()
    )
    if observed_family_counts != {
        "dirt_dust": 15,
        "partial_transparency": 15,
        "water_stain": 15,
        "water_stain_dirt": 5,
    }:
        raise ValueError("Eligible degradation-family counts changed")

    core_case_ids = set(approved_cases["case_id"].astype(str))
    completed_status = str(population["completed_status"])
    opencv_selected = _candidate_subset(
        opencv,
        case_ids=core_case_ids,
        model_id="opencv_telea",
        notebook_id="09",
        completed_status=completed_status,
    )
    lama_selected = _candidate_subset(
        lama,
        case_ids=core_case_ids,
        model_id="lama",
        notebook_id="10",
        completed_status=completed_status,
    )

    _require_columns(
        stable_diffusion,
        (
            "case_id",
            "candidate_id",
            "model_id",
            "restored_path",
            "runtime_seconds",
            "status",
            "experiment_id",
            "execution_role",
            "prompt_variant_id",
            "seed",
            "is_primary_candidate",
        ),
        "stable diffusion",
    )
    sd_selected = stable_diffusion.loc[
        stable_diffusion["case_id"].astype(str).isin(core_case_ids)
        & stable_diffusion["experiment_id"].astype(str).eq(
            str(population["experiment_id"])
        )
        & stable_diffusion["model_id"].astype(str).eq(
            "stable_diffusion_inpainting"
        )
        & stable_diffusion["status"].astype(str).eq(completed_status)
        & stable_diffusion["execution_role"].astype(str).eq(
            str(population["stable_diffusion_primary_role"])
        )
        & stable_diffusion["prompt_variant_id"].astype(str).eq(
            str(population["stable_diffusion_primary_prompt_variant"])
        )
        & pd.to_numeric(stable_diffusion["seed"], errors="coerce").eq(
            int(population["stable_diffusion_primary_seed"])
        )
        & _bool_series(stable_diffusion["is_primary_candidate"])
    ].copy()
    sd_selected["source_notebook_id"] = "11"

    sdxl_case_ids = set(map(str, population["sdxl_case_ids"]))
    if not sdxl_case_ids.issubset(core_case_ids):
        raise ValueError("SDXL subset must be nested inside the 50 eligible cases")
    sdxl_selected = _candidate_subset(
        sdxl,
        case_ids=sdxl_case_ids,
        model_id="sdxl_inpainting",
        notebook_id="12",
        completed_status=completed_status,
    )
    if "technical_validation_passed" in sdxl_selected:
        sdxl_selected = sdxl_selected.loc[
            _bool_series(sdxl_selected["technical_validation_passed"])
        ].copy()
    if "seed" in sdxl_selected:
        sdxl_selected = sdxl_selected.loc[
            pd.to_numeric(sdxl_selected["seed"], errors="coerce").eq(
                int(population["sdxl_seed"])
            )
        ].copy()

    selected = pd.concat(
        [opencv_selected, lama_selected, sd_selected, sdxl_selected],
        ignore_index=True,
        sort=False,
    )
    case_metadata = approved_cases[
        [
            "case_id",
            "painting_id",
            "category",
            "experiment_id",
            "degradation_family",
            "severity",
            "severity_rank",
            "is_combined",
            "component_degradations_json",
            "clean_image_path",
            "effect_mask_path",
            "degraded_image_path",
            "affected_content_fraction",
            "changed_content_fraction",
        ]
    ].copy()
    metadata = artworks[
        ["painting_id", "category", "style_or_period"]
    ].drop_duplicates("painting_id")
    case_metadata = case_metadata.merge(
        metadata,
        on="painting_id",
        how="left",
        suffixes=("", "__art"),
        validate="many_to_one",
    )
    case_metadata["category"] = case_metadata["category__art"].fillna(
        case_metadata["category"]
    )
    case_metadata = case_metadata.drop(columns=["category__art"])
    case_metadata["style_or_period"] = case_metadata[
        "style_or_period"
    ].fillna("unclassified")
    selected = selected.merge(
        case_metadata,
        on="case_id",
        how="inner",
        suffixes=("", "__case"),
        validate="many_to_one",
    )

    for column in (
        "painting_id",
        "category",
        "experiment_id",
        "degradation_family",
        "severity",
        "severity_rank",
        "is_combined",
        "component_degradations_json",
        "clean_image_path",
        "effect_mask_path",
        "degraded_image_path",
        "affected_content_fraction",
        "changed_content_fraction",
    ):
        authority = f"{column}__case"
        if authority in selected:
            selected[column] = selected[authority]

    selected["dataset_id"] = "painting_restoration_eval"
    selected["dataset_scope"] = str(population["dataset_scope"])
    selected["damage_or_degradation_type"] = selected[
        "degradation_family"
    ].astype(str)
    selected["damage_type"] = "not_applicable"
    selected["degradation_type"] = selected["degradation_family"].astype(str)
    selected["target_damage_fraction"] = np.nan
    selected["realized_damage_fraction"] = pd.to_numeric(
        selected["affected_content_fraction"], errors="coerce"
    )
    selected["target_damage_fraction_label"] = selected["severity"].astype(str)
    selected["is_zero_control"] = False
    selected["input_image_path"] = selected["degraded_image_path"]
    selected["mask_or_effect_path"] = selected["effect_mask_path"]
    selected["candidate_selection_policy"] = str(
        settings["selection_policy_id"]
    )
    selected["coverage_role"] = np.where(
        selected["model_id"].astype(str).eq("sdxl_inpainting"),
        "bounded_sdxl_subset",
        "core_three_model",
    )
    selected["population_id"] = np.where(
        selected["model_id"].astype(str).eq("sdxl_inpainting"),
        "sdxl_partial_six_case",
        "core_three_model",
    )
    selected["restored_path"] = [
        _normalise_restored_path(value, notebook_id)
        for value, notebook_id in zip(
            selected["restored_path"], selected["source_notebook_id"]
        )
    ]

    if selected.duplicated(["model_id", "case_id"], keep=False).any():
        raise ValueError("Candidate selection is not one-to-one by model and case")
    if selected["candidate_id"].astype(str).duplicated().any():
        raise ValueError("Selected candidate IDs are not unique")
    observed = selected.groupby("model_id").size().to_dict()
    wanted = {
        str(key): int(value)
        for key, value in expected["candidates_by_model"].items()
    }
    if observed != wanted:
        raise ValueError(f"Candidate counts differ from contract: {observed} != {wanted}")
    for model_id in population["model_order"]:
        observed_cases = set(
            selected.loc[
                selected["model_id"].astype(str).eq(str(model_id)), "case_id"
            ].astype(str)
        )
        if observed_cases != core_case_ids:
            raise ValueError(f"{model_id} does not cover the exact 50 core cases")
    observed_sdxl = set(
        selected.loc[
            selected["model_id"].astype(str).eq("sdxl_inpainting"), "case_id"
        ].astype(str)
    )
    if observed_sdxl != sdxl_case_ids:
        raise ValueError("SDXL does not cover the exact six-case contract")
    if not selected["restored_path"].astype(str).str.startswith("outputs/").all():
        raise ValueError("One or more restored paths are not repository-relative")

    keep = [
        "candidate_id",
        "case_id",
        "model_id",
        "source_notebook_id",
        "painting_id",
        "category",
        "style_or_period",
        "dataset_id",
        "dataset_scope",
        "experiment_id",
        "damage_or_degradation_type",
        "damage_type",
        "degradation_type",
        "degradation_family",
        "severity",
        "severity_rank",
        "is_combined",
        "component_degradations_json",
        "target_damage_fraction",
        "realized_damage_fraction",
        "target_damage_fraction_label",
        "affected_content_fraction",
        "changed_content_fraction",
        "is_zero_control",
        "input_image_path",
        "clean_image_path",
        "mask_or_effect_path",
        "restored_path",
        "runtime_seconds",
        "candidate_selection_policy",
        "population_id",
        "coverage_role",
    ]
    for optional in (
        "seed",
        "execution_role",
        "prompt_policy_id",
        "prompt_variant_id",
    ):
        if optional in selected:
            keep.append(optional)
    return selected[keep].sort_values(
        ["model_id", "painting_id", "degradation_family", "severity_rank"],
        kind="stable",
    ).reset_index(drop=True)


def build_eligibility_audit(
    cases: pd.DataFrame,
    eligibility: pd.DataFrame,
    selected_candidates: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Return all 660 case-model decisions with actual candidate availability."""

    settings = _settings(config)
    expected = settings["expected_counts"]
    population = settings["population"]
    case_rows = cases.loc[
        cases["experiment_id"].astype(str).eq(str(population["experiment_id"]))
    ].copy()
    ledger = eligibility.loc[
        eligibility["case_id"].astype(str).isin(
            set(case_rows["case_id"].astype(str))
        )
    ].copy()
    ledger["eligible"] = _bool_series(ledger["eligible"])
    ledger = ledger.merge(
        case_rows[
            [
                "case_id",
                "painting_id",
                "degradation_family",
                "severity",
                "severity_rank",
                "is_combined",
                "affected_content_fraction",
                "changed_content_fraction",
            ]
        ],
        on="case_id",
        how="inner",
        validate="many_to_one",
    )
    available = selected_candidates[["case_id", "model_id"]].drop_duplicates()
    available["candidate_available"] = True
    ledger = ledger.merge(
        available,
        on=["case_id", "model_id"],
        how="left",
        validate="one_to_one",
    )
    ledger["candidate_available"] = (
        ledger["candidate_available"].eq(True)
    )
    ledger["eligibility_status"] = np.where(
        ledger["eligible"], "eligible", "excluded"
    )
    if len(ledger) != int(expected["eligibility_case_model_rows"]):
        raise ValueError("Eligibility audit does not contain exactly 660 rows")
    return ledger.sort_values(
        ["model_id", "painting_id", "degradation_family", "severity_rank"],
        kind="stable",
    ).reset_index(drop=True)


def normalise_quality_evidence(
    tables: Mapping[str, pd.DataFrame],
    selected_candidates: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Normalize all selected Notebook 13–17 and 20 metric evidence."""

    missing = sorted(set(QUALITY_SOURCE_KEYS) - set(tables))
    if missing:
        raise ValueError(f"Quality evidence tables are missing: {missing}")
    adapter = build_multi_model_adapter_config(config)
    normalized: list[pd.DataFrame] = []
    for source_key in STANDARD_SOURCE_KEYS:
        normalized.append(
            normalise_standard_metric_table(
                tables[source_key],
                selected_candidates,
                source_key=source_key,
                config=adapter,
            )
        )
    spatial = normalise_spatial_diagnostics(
        tables["spatial"],
        selected_candidates,
        config=adapter,
    )
    normalized.append(spatial)
    result = pd.concat(normalized, ignore_index=True, sort=False)
    expected_rows = int(
        _settings(config)["expected_counts"]["normalized_quality_rows"]
    )
    if len(result) != expected_rows:
        raise ValueError(
            f"Normalized quality rows differ from contract: {len(result)} != {expected_rows}"
        )
    if result["candidate_id"].astype(str).nunique() != len(selected_candidates):
        raise ValueError("Normalized evidence does not cover every selected candidate")
    return result


def select_quality_anchor_values(
    normalized: pd.DataFrame,
    *,
    spatial_source: pd.DataFrame | None = None,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select one validated value per candidate and approved quality anchor."""

    settings = _settings(config)
    expected = settings["expected_counts"]
    anchors = normalized.loc[
        normalized["anchor_id"].fillna("").astype(str).ne("")
        & normalized["status"].astype(str).isin({"ok", "passed"})
    ].copy()
    if anchors.duplicated(["candidate_id", "anchor_id"], keep=False).any():
        duplicates = anchors.loc[
            anchors.duplicated(["candidate_id", "anchor_id"], keep=False),
            ["candidate_id", "anchor_id"],
        ].drop_duplicates()
        raise ValueError(
            "Quality-anchor selection is not one-to-one: "
            f"{duplicates.head(10).to_dict('records')}"
        )
    if spatial_source is not None:
        _require_columns(
            spatial_source,
            (
                "candidate_id",
                "region_id",
                "damaged_error_mean",
                "restored_error_mean",
            ),
            "spatial source",
        )
        lookup = spatial_source.loc[
            spatial_source["region_id"].astype(str).eq("masked_region"),
            ["candidate_id", "damaged_error_mean", "restored_error_mean"],
        ].drop_duplicates("candidate_id")
        lookup = lookup.set_index("candidate_id")
        spatial_mask = anchors["anchor_id"].astype(str).eq(
            "spatial_masked_error"
        )
        anchors.loc[spatial_mask, "damaged_value"] = anchors.loc[
            spatial_mask, "candidate_id"
        ].map(lookup["damaged_error_mean"])
        anchors.loc[spatial_mask, "restored_value"] = anchors.loc[
            spatial_mask, "candidate_id"
        ].map(lookup["restored_error_mean"])
        anchors.loc[spatial_mask, "improvement_value"] = (
            pd.to_numeric(
                anchors.loc[spatial_mask, "damaged_value"], errors="coerce"
            )
            - pd.to_numeric(
                anchors.loc[spatial_mask, "restored_value"], errors="coerce"
            )
        )
        anchors.loc[spatial_mask, "comparison_value"] = pd.to_numeric(
            anchors.loc[spatial_mask, "restored_value"], errors="coerce"
        )
    anchors["directional_utility"] = pd.to_numeric(
        anchors["improvement_value"], errors="coerce"
    )
    if len(anchors) != int(expected["candidate_quality_anchor_rows"]):
        raise ValueError("Expected exactly 1,716 candidate quality-anchor rows")
    if anchors["anchor_id"].astype(str).nunique() != int(
        expected["quality_anchors"]
    ):
        raise ValueError("Quality-anchor identity differs from contract")
    if not anchors.groupby("candidate_id").size().eq(
        int(expected["quality_anchors"])
    ).all():
        raise ValueError("Every selected candidate must contain all eleven anchors")
    return anchors.reset_index(drop=True)


def select_spillover_evidence(
    normalized: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select outside-mask restoration-change evidence without ranking it."""

    settings = _settings(config)
    specification = settings["spillover"]
    rows = normalized.loc[
        normalized["evidence_family"].astype(str).eq(
            str(specification["evidence_family"])
        )
        & normalized["metric_name"].astype(str).eq(
            str(specification["metric_name"])
        )
        & normalized["region_id"].astype(str).eq(
            str(specification["region_id"])
        )
        & normalized["summary_statistic"].astype(str).eq(
            str(specification["summary_statistic"])
        )
    ].copy()
    if len(rows) != int(settings["expected_counts"]["candidate_spillover_rows"]):
        raise ValueError("Spillover evidence does not cover all 156 candidates")
    if rows["candidate_id"].astype(str).duplicated().any():
        raise ValueError("Spillover evidence must be one row per candidate")
    rows["quality_ranking_eligible"] = False
    rows["anchor_id"] = ""
    return rows.reset_index(drop=True)


def build_runtime_evidence(
    selected_candidates: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Normalize runtime while keeping it outside quality rankings."""

    rows = normalise_runtime_evidence(
        selected_candidates,
        config=build_multi_model_adapter_config(config),
    )
    expected = int(_settings(config)["expected_counts"]["candidate_runtime_rows"])
    if len(rows) != expected:
        raise ValueError("Runtime evidence does not cover all selected candidates")
    if rows["quality_ranking_eligible"].any():
        raise ValueError("Runtime must not be included in quality ranking")
    return rows


def compute_case_family_balanced_ranks(
    anchor_rows: pd.DataFrame,
    *,
    model_ids: Sequence[str],
) -> pd.DataFrame:
    """Rank matched models within every case with equal evidence-family weight."""

    _require_columns(anchor_rows, ("case_id", "model_id"), "anchor rows")
    expected_models = set(map(str, model_ids))
    records: list[pd.DataFrame] = []
    for case_id, group in anchor_rows.groupby("case_id", sort=True):
        observed_models = set(group["model_id"].astype(str))
        if observed_models != expected_models:
            raise ValueError(
                f"{case_id} has models {sorted(observed_models)}, "
                f"expected {sorted(expected_models)}"
            )
        _, ranks = family_balanced_ranks(group)
        ranks["case_id"] = str(case_id)
        records.append(ranks)
    return pd.concat(records, ignore_index=True, sort=False)


def within_family_cluster_spearman(
    frame: pd.DataFrame,
    *,
    area_column: str = "affected_content_fraction",
    outcome_column: str = "comparison_value",
    painting_column: str = "painting_id",
) -> dict[str, Any]:
    """Associate affected area and outcome within painting, with cluster bootstrap.

    This is an exploratory, non-causal association intended for one individual
    degradation family with three severity levels in each of five paintings.
    """

    _require_columns(
        frame,
        (painting_column, area_column, outcome_column),
        "affected-area association input",
    )
    working = frame[[painting_column, area_column, outcome_column]].copy()
    working[area_column] = pd.to_numeric(working[area_column], errors="coerce")
    working[outcome_column] = pd.to_numeric(
        working[outcome_column], errors="coerce"
    )
    working = working.dropna()
    painting_ids = sorted(working[painting_column].astype(str).unique())
    if len(painting_ids) != 5:
        raise ValueError("Affected-area analysis requires five painting clusters")
    if len(working) != 15:
        raise ValueError("Affected-area analysis requires 15 family observations")

    working["area_centered"] = working[area_column] - working.groupby(
        painting_column
    )[area_column].transform("mean")
    working["outcome_centered"] = working[outcome_column] - working.groupby(
        painting_column
    )[outcome_column].transform("mean")
    if (
        working["area_centered"].nunique() < 2
        or working["outcome_centered"].nunique() < 2
    ):
        return {
            "rho": np.nan,
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "p_value": np.nan,
            "painting_count": 5,
            "observation_count": 15,
            "bootstrap_resamples": 0,
            "applicability_status": "not_applicable_invariant_values",
        }

    rho = float(
        spearmanr(
            working["area_centered"], working["outcome_centered"]
        ).statistic
    )
    bootstrap_values: list[float] = []
    for sample in product(painting_ids, repeat=len(painting_ids)):
        pieces: list[pd.DataFrame] = []
        for draw_index, painting_id in enumerate(sample):
            piece = working.loc[
                working[painting_column].astype(str).eq(painting_id)
            ].copy()
            piece[painting_column] = f"draw_{draw_index}_{painting_id}"
            pieces.append(piece)
        sampled = pd.concat(pieces, ignore_index=True)
        value = spearmanr(
            sampled["area_centered"], sampled["outcome_centered"]
        ).statistic
        if np.isfinite(value):
            bootstrap_values.append(float(value))
    lower, upper = np.quantile(bootstrap_values, [0.025, 0.975]).tolist()
    sign_test = exact_sign_flip_test(
        [
            spearmanr(
                group["area_centered"], group["outcome_centered"]
            ).statistic
            for _, group in working.groupby(painting_column, sort=True)
        ]
    )
    return {
        "rho": rho,
        "ci_lower": float(lower),
        "ci_upper": float(upper),
        "p_value": float(sign_test["p_value"]),
        "painting_count": 5,
        "observation_count": 15,
        "bootstrap_resamples": int(len(bootstrap_values)),
        "applicability_status": "applicable",
    }


def empty_analysis_frame() -> pd.DataFrame:
    """Return an empty canonical Notebook 25 analysis table."""

    return pd.DataFrame(columns=ANALYSIS_COLUMNS)


def validate_synthetic_degradation_analysis(
    frame: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    require_complete: bool = False,
) -> dict[str, Any]:
    """Validate schema, scientific prohibitions, IDs, and optional row contract."""

    settings = _settings(config)
    missing = sorted(set(ANALYSIS_COLUMNS) - set(frame.columns))
    ids_unique = (
        "analysis_row_id" in frame
        and not frame["analysis_row_id"].astype(str).duplicated().any()
    )
    kinds_valid = (
        "analysis_kind" in frame
        and set(frame["analysis_kind"].dropna().astype(str)).issubset(
            set(map(str, settings["analysis_kinds"]))
        )
    )
    schema_valid = (
        "schema_version" in frame
        and frame["schema_version"].astype(str).eq(ANALYSIS_SCHEMA_VERSION).all()
    )
    p_values = pd.to_numeric(
        frame.get("p_value", pd.Series(dtype=float)), errors="coerce"
    )
    q_values = pd.to_numeric(
        frame.get("q_value", pd.Series(dtype=float)), errors="coerce"
    )
    probabilities_valid = bool(
        p_values.dropna().between(0.0, 1.0).all()
        and q_values.dropna().between(0.0, 1.0).all()
    )
    prohibited_pattern = (
        "combined_quality|combined_uncertainty|trust_score|calibrated confidence|"
        "exact conservation damage|physical synergy|historical authenticity"
    )
    no_prohibited = (
        not frame.astype(str)
        .apply(
            lambda column: column.str.contains(
                prohibited_pattern,
                case=False,
                regex=True,
            )
        )
        .any()
        .any()
        if not frame.empty
        else True
    )
    status_valid = (
        "status" in frame
        and set(frame["status"].dropna().astype(str)).issubset(
            {"ok", "not_applicable"}
        )
    )
    expected_rows = int(settings["expected_counts"]["canonical_analysis_rows"])
    row_count_valid = len(frame) == expected_rows if require_complete else True
    kind_counts_valid = True
    if require_complete and "analysis_kind" in frame:
        expected_by_kind = {
            kind: int(settings["expected_counts"][f"{kind}_rows"])
            for kind in settings["analysis_kinds"]
        }
        kind_counts_valid = (
            frame.groupby("analysis_kind").size().to_dict() == expected_by_kind
        )
    passed = bool(
        not missing
        and ids_unique
        and kinds_valid
        and schema_valid
        and probabilities_valid
        and no_prohibited
        and status_valid
        and row_count_valid
        and kind_counts_valid
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


def validate_synthetic_degradation_report_html(
    html_text: str,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Validate self-containment, approved sections, and mock-aligned density."""

    base = validate_self_contained_report_html(
        html_text,
        config=build_multi_model_adapter_config(config),
    )
    report = _settings(config)["report"]
    lowered = html_text.lower()
    section_checks = pd.DataFrame(
        [
            {
                "check_name": f"report_section_{section_id}",
                "observed": section_id in lowered,
                "expected": True,
                "passed": section_id in lowered,
                "issue": (
                    "" if section_id in lowered else "approved mock section missing"
                ),
            }
            for section_id in report["required_section_ids"]
        ]
    )
    special_checks = pd.DataFrame(
        [
            {
                "check_name": "uncertainty_non_applicability_visible",
                "observed": "uncertainty" in lowered
                and (
                    "not applicable" in lowered
                    or "does not estimate" in lowered
                    or "no repeated-seed" in lowered
                ),
                "expected": True,
                "passed": "uncertainty" in lowered
                and (
                    "not applicable" in lowered
                    or "does not estimate" in lowered
                    or "no repeated-seed" in lowered
                ),
                "issue": "RQ3 uncertainty non-applicability is not explicit",
            },
            {
                "check_name": "procedural_proxy_limitation_visible",
                "observed": "procedural" in lowered
                and "not exact" in lowered
                and "conservation" in lowered,
                "expected": True,
                "passed": "procedural" in lowered
                and "not exact" in lowered
                and "conservation" in lowered,
                "issue": "procedural degradation limitation is not explicit",
            },
        ]
    )
    special_checks.loc[special_checks["passed"], "issue"] = ""
    return pd.concat(
        [base, section_checks, special_checks],
        ignore_index=True,
        sort=False,
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
    "atomic_write_csv",
    "benjamini_hochberg",
    "build_eligibility_audit",
    "build_multi_model_adapter_config",
    "build_runtime_evidence",
    "compute_case_family_balanced_ranks",
    "compute_painting_slopes",
    "empty_analysis_frame",
    "exact_sign_flip_test",
    "exhaustive_bootstrap_interval",
    "family_balanced_ranks",
    "load_synthetic_degradation_analysis_config",
    "matched_rank_biserial",
    "normalise_quality_evidence",
    "resolve_analysis_inputs",
    "select_quality_anchor_values",
    "select_spillover_evidence",
    "select_synthetic_degradation_population",
    "summarise_painting_slopes",
    "theil_sen_slope",
    "validate_synthetic_degradation_analysis",
    "validate_synthetic_degradation_report_html",
    "validate_upstream_run_manifests",
    "within_family_cluster_spearman",
]
