"""Paired multi-model comparison support for Notebook 21.

The helper enforces metric-independent candidate selection, exact paired
populations, direction-aware metric summaries, family-balanced disagreement,
painting-cluster ranking stability, auditable representative cases, and
self-contained HTML report visuals. Computational winners are never treated as
historical truth or conservation approval.
"""

from __future__ import annotations

import base64
import hashlib
import io
import math
import re
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml
from PIL import Image, ImageDraw, ImageFont

from .schemas import (
    METRIC_DISAGREEMENT_COLUMNS,
    METRIC_DISAGREEMENT_SCHEMA,
    MODEL_COMPARISON_COLUMNS,
    MODEL_COMPARISON_SCHEMA,
    REPRESENTATIVE_CASES_COLUMNS,
    REPRESENTATIVE_CASES_SCHEMA,
    validate_dataframe,
)


MULTI_MODEL_COMPARISON_MODULE_NAME = "restoration_eval.multi_model_comparison"
MULTI_MODEL_COMPARISON_MODULE_VERSION = "1.0.0"
MODEL_COMPARISON_SCHEMA_VERSION = "model_comparison.v1"
METRIC_DISAGREEMENT_SCHEMA_VERSION = "metric_disagreement.v1"
REPRESENTATIVE_CASES_SCHEMA_VERSION = "representative_cases.v1"


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    settings = config.get("multi_model_comparison", config)
    if not isinstance(settings, Mapping):
        raise TypeError("multi_model_comparison settings must be a mapping")
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


def load_multi_model_comparison_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the Notebook 21 configuration contract."""

    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Multi-model comparison configuration must be a mapping")
    if config.get("config_schema_version") != "multi_model_comparison_config.v1":
        raise ValueError("Unsupported multi-model comparison config schema")
    settings = _settings(config)
    required = {
        "notebook_id", "notebook_stem", "comparison_schema_version",
        "disagreement_schema_version", "representative_schema_version",
        "selection_policy_id", "disagreement_policy_id", "report_policy_id",
        "inputs", "output", "populations", "candidate_selection",
        "analysis_scopes", "evidence_sources", "metric_direction",
        "spatial_metric_fields", "disagreement_anchors", "ranking",
        "representative_selection", "report", "expected_counts",
        "evidence_policy", "known_limitations", "downstream_consumers",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"Multi-model config is missing keys: {missing}")
    versions = (
        (settings["comparison_schema_version"], MODEL_COMPARISON_SCHEMA_VERSION),
        (settings["disagreement_schema_version"], METRIC_DISAGREEMENT_SCHEMA_VERSION),
        (settings["representative_schema_version"], REPRESENTATIVE_CASES_SCHEMA_VERSION),
    )
    if any(observed != expected for observed, expected in versions):
        raise ValueError("Configured output schema version does not match helper")
    populations = settings["populations"]
    core = populations["core_three_model"]
    partial = populations["four_model_subset"]
    expected = settings["expected_counts"]
    if int(core["exact_case_count"]) * len(core["models"]) != int(
        core["exact_candidate_count"]
    ):
        raise ValueError("Core population arithmetic is inconsistent")
    if int(partial["exact_case_count"]) * len(partial["models"]) != int(
        partial["exact_candidate_count"]
    ):
        raise ValueError("Four-model population arithmetic is inconsistent")
    if sum(int(value) for value in expected["selected_candidates_by_model"].values()) != int(
        expected["selected_candidates"]
    ):
        raise ValueError("Selected-candidate arithmetic is inconsistent")
    if int(expected["generic_uncertainty_groups"]) + int(
        expected["scratch_aware_uncertainty_groups"]
    ) != int(expected["uncertainty_groups"]):
        raise ValueError("Uncertainty-group arithmetic is inconsistent")
    if bool(settings["ranking"]["combined_quality_score_retained"]):
        raise ValueError("A combined quality score is prohibited")
    if bool(settings["ranking"]["conservation_truth_claim"]):
        raise ValueError("A conservation-truth claim is prohibited")
    if not bool(settings["candidate_selection"]["metric_independent"]):
        raise ValueError("Candidate selection must remain metric-independent")
    if not bool(settings["report"]["self_contained_html"]):
        raise ValueError("The approved Notebook 21 report must be self-contained")
    anchor_ids = [str(item["anchor_id"]) for item in settings["disagreement_anchors"]]
    if len(anchor_ids) != len(set(anchor_ids)):
        raise ValueError("Disagreement anchor IDs must be unique")
    return config


def validate_upstream_run_manifests(
    manifests: Mapping[str, Mapping[str, Any]],
    *,
    expected_notebook_ids: Sequence[str] = tuple(str(value) for value in range(9, 21)),
) -> pd.DataFrame:
    """Audit upstream completion gates without inferring availability from files."""

    rows: list[dict[str, Any]] = []
    for notebook_id in expected_notebook_ids:
        manifest = manifests.get(str(notebook_id))
        present = isinstance(manifest, Mapping)
        run_status = str(manifest.get("run_status", "")) if present else ""
        validation_status = str(manifest.get("validation_status", "")) if present else ""
        gate = bool(manifest.get("completion_gate_passed", False)) if present else False
        passed = present and run_status == "completed" and validation_status == "passed" and gate
        rows.append({
            "notebook_id": str(notebook_id),
            "manifest_present": present,
            "run_status": run_status,
            "validation_status": validation_status,
            "completion_gate_passed": gate,
            "passed": passed,
            "issue": "" if passed else "missing or incomplete validated upstream run manifest",
        })
    return pd.DataFrame(rows)


def _candidate_asset_map(stable_diffusion: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "case_id", "painting_id", "category", "experiment_id",
        "damage_or_degradation_type", "mask_or_effect_id", "input_image_path",
        "clean_image_path", "mask_or_effect_path", "input_sha256", "mask_sha256",
    ]
    available = [column for column in columns if column in stable_diffusion.columns]
    if "case_id" not in available:
        raise ValueError("Stable Diffusion candidates must contain case_id")
    return stable_diffusion[available].drop_duplicates("case_id")


def _normalise_restored_path(value: Any, source_notebook_id: str) -> Any:
    """Return repository-relative restored paths for cross-notebook consumers.

    Notebook 11 intentionally records restored assets relative to its own output
    root (for example ``images/restored/...``), whereas the deterministic and
    SDXL registries already use repository-relative ``outputs/...`` paths.
    Normalize only the notebook-owned ``images/`` form so repository inputs such
    as ``data/...`` and ``outputs/...`` remain unchanged.
    """

    if value is None or pd.isna(value):
        return value
    text = str(value).strip().replace("\\", "/")
    if not text or not text.startswith("images/"):
        return text
    source_roots = {
        "09": "outputs/09_opencv_telea_restoration",
        "10": "outputs/10_lama_restoration",
        "11": "outputs/11_stable_diffusion_restoration",
        "12": "outputs/12_sdxl_feasibility_or_restoration",
    }
    root = source_roots.get(str(source_notebook_id))
    return f"{root}/{text}" if root else text


def _normalise_selected_candidate_frame(
    frame: pd.DataFrame,
    *,
    model_id: str,
    source_notebook_id: str,
    case_assets: pd.DataFrame,
    selection_policy_id: str,
) -> pd.DataFrame:
    selected = frame.copy()
    selected["model_id"] = model_id
    selected["source_notebook_id"] = source_notebook_id
    selected["candidate_selection_policy"] = selection_policy_id
    selected = selected.merge(case_assets, on="case_id", how="left", suffixes=("", "__case"))
    for column in case_assets.columns:
        if column == "case_id":
            continue
        fallback = f"{column}__case"
        if fallback not in selected.columns:
            continue
        if column not in selected.columns:
            selected[column] = selected[fallback]
        else:
            selected[column] = selected[column].where(selected[column].notna(), selected[fallback])
        selected = selected.drop(columns=[fallback])
    aliases = {
        "clean_image_path": "clean_image_path",
        "input_image_path": "input_image_path",
        "mask_or_effect_path": "mask_or_effect_path",
        "restored_path": "restored_path",
    }
    for output, source in aliases.items():
        if source not in selected.columns:
            selected[output] = pd.NA
    selected["restored_path"] = selected["restored_path"].map(
        lambda value: _normalise_restored_path(value, source_notebook_id)
    )
    return selected


def derive_case_dimensions(frame: pd.DataFrame) -> pd.DataFrame:
    """Derive missing-region type, degradation, severity, and percentage labels."""

    result = frame.copy()
    case_ids = result["case_id"].astype(str)
    damage_family = result.get(
        "damage_or_degradation_type", pd.Series("", index=result.index)
    ).fillna("").astype(str)

    def damage_type(case_id: str, family: str) -> str:
        if family != "binary_missing_region":
            return "not_applicable"
        match = re.search(
            r"__(loss_large|loss_small|mixed_damage|scratch_thin|zero_control)(?:__|$)",
            case_id,
        )
        return match.group(1) if match else "binary_missing_region_unspecified"

    def severity(case_id: str, mask_id: str) -> str:
        text = f"{case_id}__{mask_id}".lower()
        for value in ("mild", "moderate", "severe"):
            if re.search(rf"(?:__|_){value}(?:__|$)", text):
                return value
        return "not_applicable"

    result["damage_type"] = [
        damage_type(case_id, family) for case_id, family in zip(case_ids, damage_family)
    ]
    result["degradation_type"] = np.where(
        damage_family.eq("binary_missing_region"), "not_applicable", damage_family
    )
    mask_ids = result.get("mask_or_effect_id", pd.Series("", index=result.index)).fillna("")
    result["severity"] = [
        severity(case_id, str(mask_id)) for case_id, mask_id in zip(case_ids, mask_ids)
    ]
    target = pd.to_numeric(
        result.get("target_damage_fraction", pd.Series(np.nan, index=result.index)),
        errors="coerce",
    )
    result["target_damage_fraction_label"] = target.map(
        lambda value: "not_recorded" if pd.isna(value) else f"{100.0 * float(value):g}%"
    )
    if "is_zero_control" not in result.columns:
        result["is_zero_control"] = case_ids.str.contains("zero_control", regex=False)
    else:
        result["is_zero_control"] = _bool_series(result["is_zero_control"])
    return result


def select_comparison_candidates(
    opencv: pd.DataFrame,
    lama: pd.DataFrame,
    stable_diffusion: pd.DataFrame,
    sdxl: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select one metric-independent baseline candidate for each model and case."""

    settings = _settings(config)
    population = settings["populations"]
    completed = str(population["completed_status"])
    selection_id = str(settings["selection_policy_id"])
    case_assets = _candidate_asset_map(stable_diffusion)

    def completed_rows(frame: pd.DataFrame) -> pd.DataFrame:
        if "status" not in frame.columns:
            raise ValueError("Candidate table is missing status")
        return frame.loc[frame["status"].astype(str).eq(completed)].copy()

    opencv_selected = completed_rows(opencv)
    lama_selected = completed_rows(lama)
    sd_selected = completed_rows(stable_diffusion)
    sd_selected = sd_selected.loc[
        sd_selected["execution_role"].astype(str).eq(
            str(population["stable_diffusion_primary_role"])
        )
        & sd_selected["prompt_variant_id"].astype(str).eq(
            str(population["stable_diffusion_primary_prompt_variant"])
        )
    ].copy()
    sdxl_selected = completed_rows(sdxl)
    if bool(population["sdxl_technical_validation_required"]):
        if "technical_validation_passed" not in sdxl_selected.columns:
            raise ValueError("SDXL candidates are missing technical_validation_passed")
        sdxl_selected = sdxl_selected.loc[
            _bool_series(sdxl_selected["technical_validation_passed"])
        ].copy()

    frames = [
        _normalise_selected_candidate_frame(
            opencv_selected, model_id="opencv_telea", source_notebook_id="09",
            case_assets=case_assets, selection_policy_id=selection_id,
        ),
        _normalise_selected_candidate_frame(
            lama_selected, model_id="lama", source_notebook_id="10",
            case_assets=case_assets, selection_policy_id=selection_id,
        ),
        _normalise_selected_candidate_frame(
            sd_selected, model_id="stable_diffusion_inpainting", source_notebook_id="11",
            case_assets=case_assets, selection_policy_id=selection_id,
        ),
        _normalise_selected_candidate_frame(
            sdxl_selected, model_id="sdxl_inpainting", source_notebook_id="12",
            case_assets=case_assets, selection_policy_id=selection_id,
        ),
    ]
    selected = pd.concat(frames, ignore_index=True, sort=False)
    if selected.duplicated(["model_id", "case_id"], keep=False).any():
        duplicates = selected.loc[
            selected.duplicated(["model_id", "case_id"], keep=False),
            ["model_id", "case_id", "candidate_id"],
        ]
        raise ValueError(f"Candidate selection is not one-to-one:\n{duplicates.head(20)}")
    expected_by_model = {
        str(key): int(value)
        for key, value in settings["expected_counts"]["selected_candidates_by_model"].items()
    }
    observed_by_model = selected.groupby("model_id").size().to_dict()
    if observed_by_model != expected_by_model:
        raise ValueError(
            f"Selected candidate counts differ from contract: {observed_by_model} != {expected_by_model}"
        )
    core_models = list(population["core_three_model"]["models"])
    core_sets = [
        set(selected.loc[selected["model_id"].eq(model_id), "case_id"].astype(str))
        for model_id in core_models
    ]
    core_cases = set.intersection(*core_sets)
    sdxl_cases = set(
        selected.loc[selected["model_id"].eq("sdxl_inpainting"), "case_id"].astype(str)
    )
    if len(core_cases) != int(population["core_three_model"]["exact_case_count"]):
        raise ValueError("Core paired case count differs from contract")
    if len(sdxl_cases) != int(population["four_model_subset"]["exact_case_count"]):
        raise ValueError("SDXL subset case count differs from contract")
    if not sdxl_cases.issubset(core_cases):
        raise ValueError("The SDXL cases are not a strict subset of the paired core cases")
    selected["core_three_model_eligible"] = selected["case_id"].astype(str).isin(core_cases)
    selected["four_model_subset_eligible"] = selected["case_id"].astype(str).isin(sdxl_cases)
    return derive_case_dimensions(selected)


def attach_case_metadata(
    selected_candidates: pd.DataFrame,
    semantic_metrics: pd.DataFrame,
) -> pd.DataFrame:
    """Attach the validated Notebook 20 category/style and case metadata."""

    fields = [
        "case_id", "painting_id", "category", "style_or_period", "dataset_id",
        "dataset_scope", "experiment_id", "damage_or_degradation_type",
        "target_damage_fraction", "realized_damage_fraction", "is_zero_control",
    ]
    missing = [column for column in fields if column not in semantic_metrics.columns]
    if missing:
        raise ValueError(f"Semantic metrics are missing case metadata: {missing}")
    metadata = semantic_metrics[fields].drop_duplicates()
    if metadata.duplicated("case_id", keep=False).any():
        raise ValueError("Notebook 20 case metadata is not unique by case_id")
    result = selected_candidates.merge(
        metadata, on="case_id", how="left", suffixes=("", "__semantic"), validate="many_to_one"
    )
    for column in fields:
        if column == "case_id":
            continue
        semantic_column = f"{column}__semantic"
        if semantic_column not in result.columns:
            continue
        if column not in result.columns:
            result[column] = result[semantic_column]
        else:
            result[column] = result[semantic_column].where(
                result[semantic_column].notna(), result[column]
            )
        result = result.drop(columns=[semantic_column])
    if result["painting_id"].isna().any() or result["category"].isna().any():
        raise ValueError("Selected candidates did not receive complete case metadata")
    return derive_case_dimensions(result)


def metric_direction(
    metric_name: str,
    evidence_family: str,
    *,
    config: Mapping[str, Any],
) -> str:
    """Resolve a metric's direct restored-value direction from the contract."""

    directions = _settings(config)["metric_direction"]
    name = str(metric_name)
    if name in set(map(str, directions["higher_is_better"])):
        return "higher_is_better"
    if name in set(map(str, directions["lower_is_better"])):
        return "lower_is_better"
    if name in set(map(str, directions["descriptive_only"])):
        return "descriptive_only"
    if str(evidence_family) in {"colour", "texture_map", "texture_descriptor", "seam"}:
        return str(directions["local_consistency_default"])
    raise KeyError(f"No comparison direction registered for {evidence_family}/{metric_name}")


def build_metric_registry(config: Mapping[str, Any]) -> pd.DataFrame:
    """Return the predeclared family-balanced anchor registry."""

    rows = []
    for item in _settings(config)["disagreement_anchors"]:
        row = dict(item)
        row.setdefault("feature_model_id", "")
        row["comparison_direction"] = metric_direction(
            str(row["metric_name"]), str(row["evidence_family"]), config=config
        )
        rows.append(row)
    return pd.DataFrame(rows).sort_values("anchor_id", kind="stable").reset_index(drop=True)


def _anchor_lookup(
    evidence_family: str,
    metric_name: str,
    feature_model_id: str,
    region_id: str,
    summary_statistic: str,
    *,
    config: Mapping[str, Any],
) -> str:
    for item in _settings(config)["disagreement_anchors"]:
        expected_feature = str(item.get("feature_model_id", ""))
        if (
            str(item["evidence_family"]) == str(evidence_family)
            and str(item["metric_name"]) == str(metric_name)
            and str(item["region_id"]) == str(region_id)
            and str(item.get("summary_statistic", "value")) == str(summary_statistic)
            and (not expected_feature or expected_feature == str(feature_model_id))
        ):
            return str(item["anchor_id"])
    return ""


def _metadata_columns() -> list[str]:
    return [
        "case_id", "candidate_id", "model_id", "painting_id", "category",
        "style_or_period", "dataset_id", "dataset_scope", "experiment_id",
        "damage_or_degradation_type", "damage_type", "degradation_type",
        "severity", "target_damage_fraction", "realized_damage_fraction",
        "target_damage_fraction_label", "is_zero_control",
    ]


def normalise_standard_metric_table(
    frame: pd.DataFrame,
    selected_candidates: pd.DataFrame,
    *,
    source_key: str,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Normalize Notebook 13, 14, 15, 17, or 20 evidence for comparison."""

    settings = _settings(config)
    source = settings["evidence_sources"][source_key]
    required = {
        "case_id", "candidate_id", "model_id", "metric_name", "region_id",
        "restored_value", "status", str(source["source_row_id_column"]),
        str(source["family_column"]),
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{source_key} metric table is missing columns: {missing}")
    candidate_columns = [column for column in _metadata_columns() if column in selected_candidates]
    candidates = selected_candidates[candidate_columns].drop_duplicates("candidate_id")
    subset = frame.loc[
        frame["candidate_id"].astype(str).isin(set(candidates["candidate_id"].astype(str)))
    ].copy()
    subset = subset.merge(
        candidates, on=["case_id", "candidate_id", "model_id"], how="inner",
        suffixes=("", "__candidate"), validate="many_to_one",
    )
    for column in candidate_columns:
        candidate_column = f"{column}__candidate"
        if candidate_column not in subset.columns:
            continue
        subset[column] = subset[candidate_column].where(
            subset[candidate_column].notna(), subset.get(column)
        )
        subset = subset.drop(columns=[candidate_column])
    family_column = str(source["family_column"])
    subset["evidence_family"] = subset[family_column].astype(str)
    subset["metric_family"] = subset.get("metric_family", subset["evidence_family"]).astype(str)
    subset["feature_model_id"] = subset.get(
        "feature_model_id", pd.Series("", index=subset.index)
    ).fillna("").astype(str)
    subset["summary_statistic"] = subset.get(
        "summary_statistic", pd.Series("value", index=subset.index)
    ).fillna("value").astype(str)
    subset["value_unit"] = subset.get(
        "value_unit", pd.Series("metric_native_unit", index=subset.index)
    ).fillna("metric_native_unit").astype(str)
    subset["comparison_direction"] = [
        metric_direction(metric, family, config=config)
        for metric, family in zip(subset["metric_name"], subset["evidence_family"])
    ]
    subset["quality_ranking_eligible"] = subset["comparison_direction"].ne("descriptive_only")
    subset["anchor_id"] = [
        _anchor_lookup(family, metric, feature, region, statistic, config=config)
        for family, metric, feature, region, statistic in zip(
            subset["evidence_family"], subset["metric_name"],
            subset["feature_model_id"], subset["region_id"], subset["summary_statistic"],
        )
    ]
    subset["source_notebook_id"] = str(source["source_notebook_id"])
    subset["source_metric_row_id"] = subset[str(source["source_row_id_column"])].astype(str)
    subset["comparison_basis"] = str(source["comparison_basis"])
    subset["damaged_value"] = pd.to_numeric(
        subset.get("damaged_value", pd.Series(np.nan, index=subset.index)), errors="coerce"
    )
    subset["restored_value"] = pd.to_numeric(subset["restored_value"], errors="coerce")
    subset["improvement_value"] = pd.to_numeric(
        subset.get("improvement_value", pd.Series(np.nan, index=subset.index)), errors="coerce"
    )
    subset["comparison_value"] = subset["restored_value"]
    subset["metric_id"] = [
        _stable_id("metric", source_key, family, metric, feature, region, statistic)
        for family, metric, feature, region, statistic in zip(
            subset["evidence_family"], subset["metric_name"],
            subset["feature_model_id"], subset["region_id"], subset["summary_statistic"],
        )
    ]
    output = _metadata_columns() + [
        "source_notebook_id", "source_metric_row_id", "evidence_family",
        "metric_family", "metric_id", "metric_name", "feature_model_id",
        "region_id", "summary_statistic", "value_unit", "comparison_basis",
        "comparison_direction", "quality_ranking_eligible", "anchor_id",
        "damaged_value", "restored_value", "improvement_value", "comparison_value",
        "status", "issue",
    ]
    for column in output:
        if column not in subset.columns:
            subset[column] = pd.NA
    return subset[output].reset_index(drop=True)


def normalise_spatial_diagnostics(
    frame: pd.DataFrame,
    selected_candidates: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Convert selected Notebook 16 wide diagnostics to a comparison-long table."""

    settings = _settings(config)
    source = settings["evidence_sources"]["spatial"]
    fields = list(map(str, settings["spatial_metric_fields"]))
    required = {
        "case_id", "candidate_id", "model_id", "region_id", "status",
        str(source["source_row_id_column"]), *fields,
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Spatial diagnostics are missing columns: {missing}")
    candidate_columns = [column for column in _metadata_columns() if column in selected_candidates]
    candidates = selected_candidates[candidate_columns].drop_duplicates("candidate_id")
    subset = frame.loc[
        frame["candidate_id"].astype(str).isin(set(candidates["candidate_id"].astype(str)))
    ].copy()
    subset = subset.merge(
        candidates, on=["case_id", "candidate_id", "model_id"], how="inner",
        suffixes=("", "__candidate"), validate="many_to_one",
    )
    for column in candidate_columns:
        candidate_column = f"{column}__candidate"
        if candidate_column in subset.columns:
            subset[column] = subset[candidate_column].where(
                subset[candidate_column].notna(), subset.get(column)
            )
            subset = subset.drop(columns=[candidate_column])
    id_columns = [column for column in subset.columns if column not in fields]
    long = subset.melt(
        id_vars=id_columns, value_vars=fields,
        var_name="metric_name", value_name="comparison_value",
    )
    long["evidence_family"] = str(source["evidence_family"])
    long["metric_family"] = str(source["evidence_family"])
    long["feature_model_id"] = ""
    long["summary_statistic"] = "value"
    long["value_unit"] = np.where(
        long["metric_name"].str.contains("fraction"), "fraction", "normalized_rgb_error"
    )
    long["comparison_direction"] = [
        metric_direction(metric, str(source["evidence_family"]), config=config)
        for metric in long["metric_name"]
    ]
    long["quality_ranking_eligible"] = long["comparison_direction"].ne("descriptive_only")
    long["anchor_id"] = [
        _anchor_lookup(
            str(source["evidence_family"]), metric, "", region, "value", config=config
        )
        for metric, region in zip(long["metric_name"], long["region_id"])
    ]
    long["source_notebook_id"] = str(source["source_notebook_id"])
    long["source_metric_row_id"] = (
        long[str(source["source_row_id_column"])].astype(str) + "__" + long["metric_name"]
    )
    long["comparison_basis"] = "spatial_diagnostic_value"
    long["damaged_value"] = np.nan
    long["restored_value"] = pd.to_numeric(long["comparison_value"], errors="coerce")
    long["improvement_value"] = np.nan
    long["comparison_value"] = long["restored_value"]
    long["metric_id"] = [
        _stable_id("metric", "spatial", metric, region)
        for metric, region in zip(long["metric_name"], long["region_id"])
    ]
    output = _metadata_columns() + [
        "source_notebook_id", "source_metric_row_id", "evidence_family",
        "metric_family", "metric_id", "metric_name", "feature_model_id",
        "region_id", "summary_statistic", "value_unit", "comparison_basis",
        "comparison_direction", "quality_ranking_eligible", "anchor_id",
        "damaged_value", "restored_value", "improvement_value", "comparison_value",
        "status", "issue",
    ]
    for column in output:
        if column not in long.columns:
            long[column] = pd.NA
    return long[output].reset_index(drop=True)


def normalise_runtime_evidence(
    selected_candidates: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Normalize candidate-level runtime without mixing it into quality voting."""

    if "runtime_seconds" not in selected_candidates.columns:
        raise ValueError("Selected candidates are missing runtime_seconds")
    settings = _settings(config)
    runtime_source = settings["evidence_sources"]["runtime"]
    rows = selected_candidates.copy()
    rows["source_notebook_id"] = str(runtime_source["source_notebook_id"])
    rows["source_metric_row_id"] = rows["candidate_id"].astype(str) + "__runtime"
    rows["evidence_family"] = "runtime_compute"
    rows["metric_family"] = "runtime_compute"
    rows["metric_name"] = "runtime_seconds"
    rows["feature_model_id"] = ""
    rows["region_id"] = "whole_candidate_execution"
    rows["summary_statistic"] = "value"
    rows["value_unit"] = "seconds"
    rows["comparison_basis"] = "candidate_runtime_seconds"
    rows["comparison_direction"] = "lower_is_better"
    rows["quality_ranking_eligible"] = False
    rows["anchor_id"] = ""
    rows["damaged_value"] = np.nan
    rows["restored_value"] = pd.to_numeric(rows["runtime_seconds"], errors="coerce")
    rows["improvement_value"] = np.nan
    rows["comparison_value"] = rows["restored_value"]
    rows["metric_id"] = _stable_id("metric", "runtime_compute", "runtime_seconds")
    rows["status"] = np.where(rows["comparison_value"].notna(), "ok", "error")
    rows["issue"] = np.where(rows["comparison_value"].notna(), "", "missing runtime")
    output = _metadata_columns() + [
        "source_notebook_id", "source_metric_row_id", "evidence_family",
        "metric_family", "metric_id", "metric_name", "feature_model_id",
        "region_id", "summary_statistic", "value_unit", "comparison_basis",
        "comparison_direction", "quality_ranking_eligible", "anchor_id",
        "damaged_value", "restored_value", "improvement_value", "comparison_value",
        "status", "issue",
    ]
    for column in output:
        if column not in rows.columns:
            rows[column] = pd.NA
    return rows[output].reset_index(drop=True)


def _population_cases(
    candidates: pd.DataFrame,
    models: Sequence[str],
) -> set[str]:
    sets = [
        set(candidates.loc[candidates["model_id"].eq(model), "case_id"].astype(str))
        for model in models
    ]
    return set.intersection(*sets) if sets else set()


def _rank_values(values: pd.Series, direction: str, method: str) -> pd.Series:
    if direction == "higher_is_better":
        return values.rank(method=method, ascending=False)
    if direction == "lower_is_better":
        return values.rank(method=method, ascending=True)
    return pd.Series(np.nan, index=values.index, dtype=float)


def _extended_values(values: pd.Series) -> np.ndarray:
    """Return numeric non-missing values while retaining signed infinities."""

    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.loc[numeric.notna()].to_numpy(dtype=float)


def _extended_mean(values: pd.Series) -> float:
    """Mean over the extended real line without warning on exact-match PSNR."""

    array = _extended_values(values)
    if not len(array):
        return np.nan
    positive = bool(np.isposinf(array).any())
    negative = bool(np.isneginf(array).any())
    if positive and negative:
        return np.nan
    if positive:
        return np.inf
    if negative:
        return -np.inf
    return float(np.mean(array))


def _extended_std(values: pd.Series) -> float:
    """Sample deviation with explicit behavior for infinite observations."""

    array = _extended_values(values)
    if len(array) <= 1:
        return 0.0
    if np.isinf(array).any():
        first = array[0]
        if np.all(array == first):
            return 0.0
        return np.inf
    return float(np.std(array, ddof=1))


def _extended_quantile(values: pd.Series, quantile: float) -> float:
    """Linear quantile that handles finite-to-infinite intervals explicitly."""

    array = np.sort(_extended_values(values))
    if not len(array):
        return np.nan
    position = (len(array) - 1) * float(quantile)
    lower_index = int(math.floor(position))
    upper_index = int(math.ceil(position))
    lower = float(array[lower_index])
    upper = float(array[upper_index])
    if lower_index == upper_index or lower == upper:
        return lower
    weight = position - lower_index
    if weight <= 0.0:
        return lower
    if np.isneginf(lower) and np.isposinf(upper):
        return np.nan
    if np.isneginf(lower):
        return -np.inf
    if np.isposinf(upper):
        return np.inf
    return float(lower + (upper - lower) * weight)


def _extended_summary(values: pd.Series) -> dict[str, float]:
    """Compute reusable extended-real summaries with one conversion and sort."""

    array = _extended_values(values)
    if not len(array):
        return {
            "mean": np.nan, "std": np.nan, "median": np.nan,
            "q25": np.nan, "q75": np.nan,
        }
    positive = bool(np.isposinf(array).any())
    negative = bool(np.isneginf(array).any())
    if positive and negative:
        mean = np.nan
    elif positive:
        mean = np.inf
    elif negative:
        mean = -np.inf
    else:
        mean = float(np.mean(array))
    if len(array) <= 1:
        std = 0.0
    elif np.isinf(array).any():
        std = 0.0 if np.all(array == array[0]) else np.inf
    else:
        std = float(np.std(array, ddof=1))
    ordered = np.sort(array)

    def quantile(probability: float) -> float:
        position = (len(ordered) - 1) * probability
        lower_index = int(math.floor(position))
        upper_index = int(math.ceil(position))
        lower = float(ordered[lower_index])
        upper = float(ordered[upper_index])
        if lower_index == upper_index or lower == upper:
            return lower
        weight = position - lower_index
        if weight <= 0.0:
            return lower
        if np.isneginf(lower) and np.isposinf(upper):
            return np.nan
        if np.isneginf(lower):
            return -np.inf
        if np.isposinf(upper):
            return np.inf
        return float(lower + (upper - lower) * weight)

    return {
        "mean": mean,
        "std": std,
        "median": quantile(0.50),
        "q25": quantile(0.25),
        "q75": quantile(0.75),
    }


def _loo_rank_stability(
    paired: pd.DataFrame,
    *,
    direction: str,
    models: Sequence[str],
    minimum_paintings: int,
    ranking_method: str,
) -> dict[str, dict[str, float]]:
    paintings = sorted(paired["painting_id"].dropna().astype(str).unique())
    empty = {
        model: {"replicates": 0.0, "top_fraction": np.nan, "rank_min": np.nan, "rank_max": np.nan}
        for model in models
    }
    if len(paintings) < minimum_paintings or direction == "descriptive_only":
        return empty
    working = paired[["painting_id", "model_id", "comparison_value"]].copy()
    numeric = pd.to_numeric(working["comparison_value"], errors="coerce")
    working["finite_sum"] = np.where(np.isfinite(numeric), numeric, 0.0)
    working["finite_count"] = np.isfinite(numeric).astype(int)
    working["positive_infinity_count"] = np.isposinf(numeric).astype(int)
    working["negative_infinity_count"] = np.isneginf(numeric).astype(int)
    aggregate_columns = [
        "finite_sum", "finite_count", "positive_infinity_count",
        "negative_infinity_count",
    ]
    totals = working.groupby("model_id")[aggregate_columns].sum().reindex(models)
    by_painting = working.groupby(
        [working["painting_id"].astype(str), "model_id"]
    )[aggregate_columns].sum()

    def remaining_mean(model: str, painting: str) -> float:
        total = totals.loc[model]
        key = (painting, model)
        excluded = (
            by_painting.loc[key]
            if key in by_painting.index
            else pd.Series(0.0, index=aggregate_columns)
        )
        positive = int(
            total["positive_infinity_count"]
            - excluded["positive_infinity_count"]
        )
        negative = int(
            total["negative_infinity_count"]
            - excluded["negative_infinity_count"]
        )
        if positive and negative:
            return np.nan
        if positive:
            return np.inf
        if negative:
            return -np.inf
        count = int(total["finite_count"] - excluded["finite_count"])
        if count <= 0:
            return np.nan
        total_sum = float(total["finite_sum"] - excluded["finite_sum"])
        return float(total_sum / count)

    ranks: dict[str, list[float]] = {model: [] for model in models}
    for painting in paintings:
        means = pd.Series(
            {model: remaining_mean(model, painting) for model in models},
            dtype=float,
        ).reindex(models)
        if means.isna().any():
            continue
        replicate_ranks = _rank_values(means, direction, ranking_method)
        for model in models:
            ranks[model].append(float(replicate_ranks.loc[model]))
    result: dict[str, dict[str, float]] = {}
    for model, values in ranks.items():
        if not values:
            result[model] = empty[model]
        else:
            array = np.asarray(values, dtype=float)
            result[model] = {
                "replicates": float(len(array)),
                "top_fraction": float(np.mean(np.isclose(array, 1.0))),
                "rank_min": float(np.min(array)),
                "rank_max": float(np.max(array)),
            }
    return result


def build_model_comparison(
    evidence: pd.DataFrame,
    selected_candidates: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> pd.DataFrame:
    """Build paired, direction-aware aggregate model comparisons."""

    settings = _settings(config)
    ranking = settings["ranking"]
    populations = [
        settings["populations"]["core_three_model"],
        settings["populations"]["four_model_subset"],
    ]
    identity_columns = [
        "source_notebook_id", "evidence_family", "metric_family", "metric_id",
        "metric_name", "feature_model_id", "region_id", "summary_statistic",
        "value_unit", "comparison_basis", "comparison_direction",
        "quality_ranking_eligible", "anchor_id",
    ]
    valid = evidence.loc[
        evidence["status"].astype(str).eq("ok")
        & pd.to_numeric(evidence["comparison_value"], errors="coerce").notna()
    ].copy()
    valid["comparison_value"] = pd.to_numeric(valid["comparison_value"], errors="coerce")
    tasks: list[tuple[Mapping[str, Any], tuple[Any, ...], pd.DataFrame]] = []
    for population in populations:
        models = list(map(str, population["models"]))
        cases = _population_cases(selected_candidates, models)
        population_evidence = valid.loc[
            valid["case_id"].astype(str).isin(cases)
            & valid["model_id"].astype(str).isin(models)
        ]
        for metric_identity, metric_rows in population_evidence.groupby(identity_columns, dropna=False, sort=True):
            tasks.append((population, metric_identity, metric_rows.copy()))
    records: list[dict[str, Any]] = []
    total = len(tasks)
    for task_number, (population, metric_identity, metric_rows) in enumerate(tasks, start=1):
        models = list(map(str, population["models"]))
        metric_meta = dict(zip(identity_columns, metric_identity))
        case_model_counts = metric_rows.groupby("case_id")["model_id"].nunique()
        paired_cases = set(case_model_counts.loc[case_model_counts.eq(len(models))].index.astype(str))
        paired = metric_rows.loc[metric_rows["case_id"].astype(str).isin(paired_cases)].copy()
        paired = paired.drop_duplicates(["case_id", "model_id"], keep="first")
        if paired.empty:
            continue
        population_case_count = int(population["exact_case_count"])
        for scope in settings["analysis_scopes"]:
            scope_id = str(scope["scope_id"])
            column = scope.get("column")
            if column is None:
                scope_groups = [("all", paired)]
            else:
                scope_groups = list(paired.groupby(str(column), dropna=False, sort=True))
            for scope_value, scoped in scope_groups:
                scoped_counts = scoped.groupby("case_id")["model_id"].nunique()
                complete_cases = set(
                    scoped_counts.loc[scoped_counts.eq(len(models))].index.astype(str)
                )
                scoped = scoped.loc[scoped["case_id"].astype(str).isin(complete_cases)]
                scoped = scoped.drop_duplicates(["case_id", "model_id"], keep="first")
                if not complete_cases:
                    continue
                model_means = (
                    scoped.groupby("model_id")["comparison_value"]
                    .mean()
                    .reindex(models)
                )
                direction = str(metric_meta["comparison_direction"])
                ranking_eligible = bool(metric_meta["quality_ranking_eligible"])
                ranks = _rank_values(
                    model_means, direction if ranking_eligible else "descriptive_only",
                    str(ranking["ranking_method"]),
                )
                if ranking_eligible:
                    winning_rank = float(ranks.min())
                    winners = sorted(ranks.index[np.isclose(ranks, winning_rank)].astype(str))
                else:
                    winners = []
                winner_text = "|".join(winners)
                stability = _loo_rank_stability(
                    scoped, direction=direction if ranking_eligible else "descriptive_only",
                    models=models,
                    minimum_paintings=int(ranking["minimum_paintings_for_stability"]),
                    ranking_method=str(ranking["ranking_method"]),
                ) if scope_id == "overall" else {
                    model: {"replicates": 0.0, "top_fraction": np.nan, "rank_min": np.nan, "rank_max": np.nan}
                    for model in models
                }
                for model in models:
                    model_rows = scoped.loc[scoped["model_id"].astype(str).eq(model)]
                    values = model_rows["comparison_value"].astype(float)
                    damaged = pd.to_numeric(model_rows["damaged_value"], errors="coerce")
                    improved = pd.to_numeric(model_rows["improvement_value"], errors="coerce")
                    restored_summary = _extended_summary(values)
                    damaged_summary = _extended_summary(damaged)
                    improvement_summary = _extended_summary(improved)
                    utility_mean = (
                        restored_summary["mean"]
                        if direction == "higher_is_better"
                        else -restored_summary["mean"]
                    )
                    rank_value = float(ranks.loc[model]) if ranking_eligible else np.nan
                    if not ranking_eligible:
                        winner_status = "not_ranked"
                    elif model in winners and len(winners) == 1:
                        winner_status = "winner"
                    elif model in winners:
                        winner_status = "tied"
                    else:
                        winner_status = "not_winner"
                    stable = stability[model]
                    record = {
                        "comparison_row_id": _stable_id(
                            "comparison", population["population_id"], scope_id,
                            scope_value, metric_meta["metric_id"], model,
                        ),
                        "population_id": str(population["population_id"]),
                        "analysis_scope": scope_id,
                        "scope_value": "not_recorded" if pd.isna(scope_value) else str(scope_value),
                        **metric_meta,
                        "model_id": model,
                        "population_case_count": population_case_count,
                        "paired_case_count": int(len(complete_cases)),
                        "paired_painting_count": int(model_rows["painting_id"].nunique()),
                        "coverage_fraction": float(len(complete_cases) / population_case_count),
                        "damaged_mean": damaged_summary["mean"],
                        "damaged_median": damaged_summary["median"],
                        "restored_mean": restored_summary["mean"],
                        "restored_std": restored_summary["std"],
                        "restored_median": restored_summary["median"],
                        "restored_q25": restored_summary["q25"],
                        "restored_q75": restored_summary["q75"],
                        "improvement_mean": improvement_summary["mean"],
                        "improvement_median": improvement_summary["median"],
                        "directional_utility_mean": utility_mean,
                        "aggregate_rank": rank_value,
                        "winner_model_id": winner_text if winner_text else np.nan,
                        "winner_status": winner_status,
                        "tie_model_ids": winner_text if len(winners) > 1 else np.nan,
                        "loo_replicate_count": int(stable["replicates"]),
                        "loo_top_rank_fraction": stable["top_fraction"],
                        "loo_rank_min": stable["rank_min"],
                        "loo_rank_max": stable["rank_max"],
                        "selection_policy_id": str(settings["selection_policy_id"]),
                        "schema_version": MODEL_COMPARISON_SCHEMA_VERSION,
                        "status": "ok",
                        "issue": "",
                    }
                    records.append(record)
        if progress_callback and (task_number % 10 == 0 or task_number == total):
            progress_callback(task_number, total, str(metric_meta["metric_id"]))
    result = pd.DataFrame(records, columns=MODEL_COMPARISON_COLUMNS)
    if not result.empty:
        result = result.sort_values(
            ["population_id", "analysis_scope", "scope_value", "metric_id", "model_id"],
            kind="stable",
        ).reset_index(drop=True)
    return result


def build_metric_disagreement(
    model_comparison: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Summarize predeclared anchor disagreement with one vote per family."""

    settings = _settings(config)
    anchors = model_comparison.loc[
        model_comparison["anchor_id"].fillna("").astype(str).ne("")
        & model_comparison["quality_ranking_eligible"].astype(bool)
        & model_comparison["status"].astype(str).eq("ok")
    ].copy()
    group_columns = ["population_id", "analysis_scope", "scope_value"]
    records: list[dict[str, Any]] = []
    for scope_key, scope_rows in anchors.groupby(group_columns, dropna=False, sort=True):
        anchor_summaries: list[dict[str, Any]] = []
        for anchor_id, anchor_rows in scope_rows.groupby("anchor_id", sort=True):
            anchor_rows = anchor_rows.sort_values(["aggregate_rank", "model_id"], kind="stable")
            first = anchor_rows.iloc[0]
            winners = str(first["winner_model_id"]).split("|")
            unique_winner = winners[0] if len(winners) == 1 else ""
            anchor_summaries.append({
                "anchor_id": str(anchor_id),
                "evidence_family": str(first["evidence_family"]),
                "metric_id": str(first["metric_id"]),
                "metric_name": str(first["metric_name"]),
                "feature_model_id": str(first["feature_model_id"] or ""),
                "region_id": str(first["region_id"]),
                "summary_statistic": str(first["summary_statistic"]),
                "comparison_direction": str(first["comparison_direction"]),
                "eligible_case_count": int(first["paired_case_count"]),
                "eligible_painting_count": int(first["paired_painting_count"]),
                "model_rank_order": "|".join(anchor_rows["model_id"].astype(str)),
                "winner_model_id": str(first["winner_model_id"]),
                "tie_model_ids": first["tie_model_ids"],
                "unique_winner": unique_winner,
                "loo_replicate_count": int(first["loo_replicate_count"]),
                "loo_winner_stability_fraction": (
                    float(anchor_rows.loc[
                        anchor_rows["model_id"].astype(str).eq(unique_winner),
                        "loo_top_rank_fraction",
                    ].iloc[0])
                    if unique_winner and anchor_rows.loc[
                        anchor_rows["model_id"].astype(str).eq(unique_winner),
                        "loo_top_rank_fraction",
                    ].notna().any()
                    else np.nan
                ),
            })
        summary = pd.DataFrame(anchor_summaries)
        family_winners: dict[str, str] = {}
        family_counts: dict[str, dict[str, int]] = {}
        for family, family_rows in summary.groupby("evidence_family", sort=True):
            counts = family_rows.loc[
                family_rows["unique_winner"].ne(""), "unique_winner"
            ].value_counts().to_dict()
            family_counts[str(family)] = {str(key): int(value) for key, value in counts.items()}
            if counts:
                maximum = max(counts.values())
                leaders = sorted(str(key) for key, value in counts.items() if value == maximum)
                family_winners[str(family)] = leaders[0] if len(leaders) == 1 else "|".join(leaders)
            else:
                family_winners[str(family)] = ""
        majority_counts: dict[str, int] = {}
        for winner in family_winners.values():
            if winner and "|" not in winner:
                majority_counts[winner] = majority_counts.get(winner, 0) + 1
        if majority_counts:
            maximum = max(majority_counts.values())
            majority_leaders = sorted(
                model for model, count in majority_counts.items() if count == maximum
            )
            majority_winner = majority_leaders[0] if len(majority_leaders) == 1 else "|".join(majority_leaders)
        else:
            majority_winner = ""
        for item in anchor_summaries:
            family = item["evidence_family"]
            family_winner = family_winners[family]
            unique_winner = item.pop("unique_winner")
            family_count_map = family_counts[family]
            vote_count = int(family_count_map.get(unique_winner, 0)) if unique_winner else 0
            vote_denominator = max(1, sum(family_count_map.values()))
            record = {
                "disagreement_row_id": _stable_id(
                    "disagreement", *scope_key, item["anchor_id"]
                ),
                "population_id": str(scope_key[0]),
                "analysis_scope": str(scope_key[1]),
                "scope_value": str(scope_key[2]),
                **item,
                "family_consensus_winner_model_id": family_winner or np.nan,
                "agrees_with_family_consensus": bool(
                    unique_winner and family_winner == unique_winner
                ),
                "majority_vote_winner_model_id": majority_winner or np.nan,
                "agrees_with_majority_vote": bool(
                    unique_winner and majority_winner == unique_winner
                ),
                "family_vote_count": vote_count,
                "family_vote_share": float(vote_count / vote_denominator),
                "distinct_metric_winner_count": int(len(family_count_map)),
                "comparison_policy_id": str(settings["disagreement_policy_id"]),
                "is_conservation_truth": False,
                "schema_version": METRIC_DISAGREEMENT_SCHEMA_VERSION,
                "status": "ok",
                "issue": "",
            }
            records.append(record)
    result = pd.DataFrame(records, columns=METRIC_DISAGREEMENT_COLUMNS)
    if not result.empty:
        result = result.sort_values(
            ["population_id", "analysis_scope", "scope_value", "anchor_id"],
            kind="stable",
        ).reset_index(drop=True)
    return result


def build_representative_case_rows(
    selected_slots: pd.DataFrame,
    selected_candidates: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> pd.DataFrame:
    """Expand deterministic selection slots to one auditable row per model."""

    required = {"selection_slot_id", "selection_role", "selection_priority", "population_id", "case_id", "selection_reason"}
    missing = sorted(required - set(selected_slots.columns))
    if missing:
        raise ValueError(f"Selected representative slots are missing columns: {missing}")
    settings = _settings(config)
    populations = {
        str(settings["populations"][name]["population_id"]): list(
            map(str, settings["populations"][name]["models"])
        )
        for name in ("core_three_model", "four_model_subset")
    }
    root = Path(project_root) if project_root is not None else None
    records: list[dict[str, Any]] = []
    for _, slot in selected_slots.sort_values("selection_priority", kind="stable").iterrows():
        population_id = str(slot["population_id"])
        if population_id not in populations:
            raise ValueError(f"Unknown representative population: {population_id}")
        case_rows = selected_candidates.loc[
            selected_candidates["case_id"].astype(str).eq(str(slot["case_id"]))
            & selected_candidates["model_id"].astype(str).isin(populations[population_id])
        ].copy()
        if set(case_rows["model_id"].astype(str)) != set(populations[population_id]):
            raise ValueError(f"Representative case lacks the complete {population_id} model set")
        for _, candidate in case_rows.iterrows():
            path_columns = [
                "clean_image_path", "input_image_path", "mask_or_effect_path", "restored_path"
            ]
            paths = [candidate.get(column, pd.NA) for column in path_columns]
            if root is None:
                path_status = "not_available"
            else:
                resolved = [
                    root / str(value) for value in paths
                    if value is not None and not pd.isna(value) and str(value).strip()
                ]
                path_status = "passed" if resolved and all(path.is_file() for path in resolved) else "error"
            record = {
                "representative_row_id": _stable_id(
                    "representative", slot["selection_slot_id"], candidate["model_id"]
                ),
                "selection_slot_id": str(slot["selection_slot_id"]),
                "selection_role": str(slot["selection_role"]),
                "selection_priority": int(slot["selection_priority"]),
                "population_id": population_id,
                "case_id": str(candidate["case_id"]),
                "painting_id": str(candidate["painting_id"]),
                "category": str(candidate["category"]),
                "style_or_period": candidate.get("style_or_period", pd.NA),
                "experiment_id": str(candidate["experiment_id"]),
                "damage_or_degradation_type": str(candidate["damage_or_degradation_type"]),
                "damage_type": candidate.get("damage_type", pd.NA),
                "degradation_type": candidate.get("degradation_type", pd.NA),
                "severity": candidate.get("severity", pd.NA),
                "model_id": str(candidate["model_id"]),
                "candidate_id": str(candidate["candidate_id"]),
                "candidate_selection_policy": str(settings["selection_policy_id"]),
                "clean_image_path": candidate.get("clean_image_path", pd.NA),
                "input_image_path": candidate.get("input_image_path", pd.NA),
                "mask_or_effect_path": candidate.get("mask_or_effect_path", pd.NA),
                "restored_path": candidate.get("restored_path", pd.NA),
                "input_sha256": candidate.get("input_sha256", pd.NA),
                "mask_sha256": candidate.get("mask_sha256", pd.NA),
                "restored_sha256": candidate.get("restored_sha256", pd.NA),
                "selection_metric_id": slot.get("selection_metric_id", pd.NA),
                "selection_score": slot.get("selection_score", np.nan),
                "selection_rank": slot.get("selection_rank", np.nan),
                "selection_reason": str(slot["selection_reason"]),
                "source_artifact_paths": slot.get("source_artifact_paths", pd.NA),
                "embedded_report_role": str(slot["selection_role"]),
                "path_validation_status": path_status,
                "schema_version": REPRESENTATIVE_CASES_SCHEMA_VERSION,
                "status": "ok" if path_status != "error" else "error",
                "issue": "" if path_status != "error" else "one or more representative image paths are missing",
            }
            records.append(record)
    return pd.DataFrame(records, columns=REPRESENTATIVE_CASES_COLUMNS).sort_values(
        ["selection_priority", "model_id"], kind="stable"
    ).reset_index(drop=True)


def image_path_to_data_uri(
    path: str | Path,
    *,
    max_dimension: int = 900,
    photographic_format: str = "JPEG",
    quality: int = 82,
    is_mask: bool = False,
) -> str:
    """Create a web-sized self-contained image URI without persisting a copy."""

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
            save_options: dict[str, Any] = {"format": fmt}
            if fmt in {"JPEG", "WEBP"}:
                save_options["quality"] = int(quality)
                save_options["optimize"] = True
            image.save(buffer, **save_options)
            mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[fmt]
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def image_grid_to_data_uri(
    items: Sequence[tuple[str, str | Path]],
    *,
    columns: int = 3,
    tile_size: tuple[int, int] = (360, 300),
    background: tuple[int, int, int] = (248, 250, 252),
    quality: int = 84,
) -> str:
    """Assemble a labelled report-only restoration grid and return a data URI."""

    if not items:
        raise ValueError("At least one image is required for a report grid")
    columns = max(1, int(columns))
    rows = int(math.ceil(len(items) / columns))
    tile_width, tile_height = map(int, tile_size)
    label_height = 34
    canvas = Image.new(
        "RGB", (columns * tile_width, rows * (tile_height + label_height)), background
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, (label, path) in enumerate(items):
        row, column = divmod(index, columns)
        x0 = column * tile_width
        y0 = row * (tile_height + label_height)
        with Image.open(path) as opened:
            image = opened.convert("RGB")
            image.thumbnail((tile_width - 12, tile_height - 12), Image.Resampling.LANCZOS)
            x = x0 + (tile_width - image.width) // 2
            y = y0 + 6 + (tile_height - 12 - image.height) // 2
            canvas.paste(image, (x, y))
        draw.text((x0 + 8, y0 + tile_height + 8), str(label), fill=(31, 41, 55), font=font)
    buffer = io.BytesIO()
    canvas.save(buffer, format="JPEG", quality=int(quality), optimize=True)
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{payload}"


def validate_self_contained_report_html(
    html_text: str,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Validate embedded visual counts, portability, thesis headings, and size."""

    report = _settings(config)["report"]
    image_sources = re.findall(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", html_text, flags=re.I)
    embedded = [source for source in image_sources if source.startswith("data:image/")]
    external_required = [source for source in image_sources if not source.startswith("data:image/")]
    size_mib = len(html_text.encode("utf-8")) / (1024 * 1024)
    required_terms = ["RQ1", "RQ2", "RQ3", "conclusion", "limitation"]
    rows = [
        {
            "check_name": "html_nonempty",
            "observed": len(html_text), "expected": "> 0",
            "passed": bool(html_text.strip()), "issue": "empty HTML report",
        },
        {
            "check_name": "required_visuals_self_contained",
            "observed": len(external_required), "expected": 0,
            "passed": len(external_required) == 0,
            "issue": "one or more required img elements use non-embedded sources",
        },
        {
            "check_name": "embedded_visual_minimum",
            "observed": len(embedded),
            "expected": int(report["minimum_embedded_analytical_views"]) + int(
                report["minimum_embedded_restoration_or_diagnostic_panels"]
            ),
            "passed": len(embedded) >= int(report["minimum_embedded_analytical_views"]) + int(
                report["minimum_embedded_restoration_or_diagnostic_panels"]
            ),
            "issue": "report contains fewer embedded visuals than the approved density contract",
        },
        {
            "check_name": "thesis_question_and_conclusion_terms",
            "observed": [term for term in required_terms if term.lower() in html_text.lower()],
            "expected": required_terms,
            "passed": all(term.lower() in html_text.lower() for term in required_terms),
            "issue": "report is missing thesis-question, conclusion, or limitation framing",
        },
        {
            "check_name": "report_soft_size_warning",
            "observed": round(size_mib, 3),
            "expected": f"<= {float(report['soft_report_size_warning_mib']):g} MiB or documented warning",
            "passed": size_mib <= float(report["soft_report_size_warning_mib"]),
            "issue": "self-contained report exceeds the configured soft size warning",
        },
    ]
    for row in rows:
        if row["passed"]:
            row["issue"] = ""
    return pd.DataFrame(rows)


def validate_model_comparison(frame: pd.DataFrame) -> dict[str, Any]:
    """Validate canonical comparison schema and scientific prohibitions."""

    schema = validate_dataframe(frame, MODEL_COMPARISON_SCHEMA, allow_extra_columns=False)
    no_combined = not frame["metric_name"].astype(str).str.contains(
        "combined|trustworthiness_score", case=False, regex=True
    ).any() if not frame.empty else True
    valid_coverage = bool(
        pd.to_numeric(frame["coverage_fraction"], errors="coerce").between(0.0, 1.0).all()
    ) if not frame.empty else True
    return {
        "passed": bool(schema.passed and no_combined and valid_coverage),
        "schema": schema.to_dict(),
        "no_combined_score": no_combined,
        "coverage_in_unit_interval": valid_coverage,
    }


def validate_metric_disagreement(frame: pd.DataFrame) -> dict[str, Any]:
    """Validate disagreement output and prohibit conservation-truth labels."""

    schema = validate_dataframe(frame, METRIC_DISAGREEMENT_SCHEMA, allow_extra_columns=False)
    no_truth = bool((~frame["is_conservation_truth"].astype(bool)).all()) if not frame.empty else True
    shares = pd.to_numeric(frame["family_vote_share"], errors="coerce")
    valid_shares = bool(shares.between(0.0, 1.0).all()) if not frame.empty else True
    return {
        "passed": bool(schema.passed and no_truth and valid_shares),
        "schema": schema.to_dict(),
        "no_conservation_truth": no_truth,
        "vote_shares_in_unit_interval": valid_shares,
    }


def validate_representative_cases(frame: pd.DataFrame) -> dict[str, Any]:
    """Validate normalized representative-case records."""

    schema = validate_dataframe(frame, REPRESENTATIVE_CASES_SCHEMA, allow_extra_columns=False)
    unique = not frame.duplicated(["selection_slot_id", "model_id"]).any()
    return {
        "passed": bool(schema.passed and unique),
        "schema": schema.to_dict(),
        "unique_slot_model_pairs": unique,
    }
