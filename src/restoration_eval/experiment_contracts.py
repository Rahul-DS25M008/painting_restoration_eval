"""Normalized experiment, model-eligibility, and metric-region contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd
import yaml

from .schemas import (
    CASE_REGISTRY_COLUMNS,
    CASE_REGISTRY_SCHEMA,
    MODEL_ELIGIBILITY_COLUMNS,
    MODEL_ELIGIBILITY_SCHEMA,
    REGION_POLICY_COLUMNS,
    REGION_POLICY_SCHEMA,
    SCHEMA_REGISTRY,
    SCHEMA_REGISTRY_VERSION,
    validate_dataframe,
)


EXPERIMENT_CONTRACTS_MODULE_VERSION = "1.0.0"
ACCEPTED_STATUSES = frozenset({"ok", "passed", "success", "valid"})
BINARY_EXPERIMENTS = frozenset(
    {
        "canonical_missing_region",
        "damage_size_sensitivity",
        "mask_robustness",
    }
)


def load_evaluation_contract_config(path: str | Path) -> dict[str, Any]:
    """Load and minimally validate the Notebook 08 YAML configuration."""
    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Evaluation-contract configuration must be a mapping")
    required = {
        "config_schema_version",
        "config_version",
        "dataset",
        "inputs",
        "models",
        "eligibility",
        "regions",
        "metric_families",
        "ablation_policies",
        "expected_counts",
    }
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(f"Evaluation-contract configuration is missing: {missing}")
    return config


def _accepted_rows(dataframe: pd.DataFrame, experiment_id: str) -> pd.DataFrame:
    if "status" not in dataframe.columns:
        raise ValueError(f"{experiment_id} source table has no status column")
    accepted = dataframe["status"].fillna("").astype(str).str.lower().isin(
        ACCEPTED_STATUSES
    )
    rejected_count = int((~accepted).sum())
    if rejected_count:
        raise ValueError(
            f"{experiment_id} contains {rejected_count} non-accepted source rows"
        )
    return dataframe.loc[accepted].copy()


def _require_columns(
    dataframe: pd.DataFrame,
    columns: Sequence[str],
    experiment_id: str,
) -> None:
    missing = sorted(set(columns) - set(dataframe.columns))
    if missing:
        raise ValueError(f"{experiment_id} source table is missing columns: {missing}")


def _normalize_storage_path(value: Any) -> str:
    text = str(value).strip().replace("\\", "/")
    if not text or text.lower() in {"nan", "none"}:
        raise ValueError("A required storage path is empty")
    return text


def _canonical_registry_rows(
    cases: pd.DataFrame,
    canonical_masks: pd.DataFrame,
    source_manifest_path: str,
) -> pd.DataFrame:
    experiment_id = "canonical_missing_region"
    _require_columns(
        cases,
        (
            "case_id",
            "dataset_id",
            "dataset_scope",
            "experiment_id",
            "painting_id",
            "damaged_image_path",
            "clean_image_path",
            "mask_id",
            "mask_path",
            "status",
        ),
        experiment_id,
    )
    _require_columns(
        canonical_masks,
        (
            "case_id",
            "target_damaged_content_fraction",
            "damaged_content_fraction",
        ),
        "canonical masks",
    )
    fractions = canonical_masks[
        [
            "case_id",
            "target_damaged_content_fraction",
            "damaged_content_fraction",
        ]
    ].copy()
    if fractions["case_id"].duplicated().any():
        raise ValueError("Canonical masks repeat case_id")
    merged = _accepted_rows(cases, experiment_id).merge(
        fractions,
        on="case_id",
        how="left",
        validate="one_to_one",
    )
    if merged["target_damaged_content_fraction"].isna().any():
        raise ValueError("Canonical case-to-mask fraction join is incomplete")
    return pd.DataFrame(
        {
            "case_id": merged["case_id"],
            "dataset_id": merged["dataset_id"],
            "dataset_scope": merged["dataset_scope"],
            "experiment_id": merged["experiment_id"],
            "painting_id": merged["painting_id"],
            "input_image_path": merged["damaged_image_path"].map(
                _normalize_storage_path
            ),
            "clean_image_path": merged["clean_image_path"].map(
                _normalize_storage_path
            ),
            "mask_or_effect_id": merged["mask_id"],
            "mask_or_effect_path": merged["mask_path"].map(
                _normalize_storage_path
            ),
            "damage_or_degradation_type": "binary_missing_region",
            "target_damage_fraction": pd.to_numeric(
                merged["target_damaged_content_fraction"], errors="raise"
            ),
            "realized_damage_fraction": pd.to_numeric(
                merged["damaged_content_fraction"], errors="raise"
            ),
            "source_manifest_path": _normalize_storage_path(
                source_manifest_path
            ),
            "status": "passed",
        }
    )


def _binary_registry_rows(
    cases: pd.DataFrame,
    experiment_id: str,
    source_manifest_path: str,
) -> pd.DataFrame:
    aliases = {
        "damage_size_sensitivity": {
            "input": "input_image_path",
            "mask_id": "mask_or_effect_id",
            "mask_path": "mask_or_effect_path",
        },
        "mask_robustness": {
            "input": "damaged_image_path",
            "mask_id": "mask_id",
            "mask_path": "mask_path",
        },
    }
    try:
        selected = aliases[experiment_id]
    except KeyError as exc:
        raise ValueError(f"Unsupported binary experiment: {experiment_id}") from exc
    required = (
        "case_id",
        "dataset_id",
        "dataset_scope",
        "experiment_id",
        "painting_id",
        selected["input"],
        "clean_image_path",
        selected["mask_id"],
        selected["mask_path"],
        "target_damage_fraction",
        "realized_damage_fraction",
        "status",
    )
    _require_columns(cases, required, experiment_id)
    rows = _accepted_rows(cases, experiment_id)
    damage_type = (
        rows["damage_or_degradation_type"]
        if "damage_or_degradation_type" in rows.columns
        else pd.Series("binary_missing_region", index=rows.index)
    )
    return pd.DataFrame(
        {
            "case_id": rows["case_id"],
            "dataset_id": rows["dataset_id"],
            "dataset_scope": rows["dataset_scope"],
            "experiment_id": rows["experiment_id"],
            "painting_id": rows["painting_id"],
            "input_image_path": rows[selected["input"]].map(
                _normalize_storage_path
            ),
            "clean_image_path": rows["clean_image_path"].map(
                _normalize_storage_path
            ),
            "mask_or_effect_id": rows[selected["mask_id"]],
            "mask_or_effect_path": rows[selected["mask_path"]].map(
                _normalize_storage_path
            ),
            "damage_or_degradation_type": damage_type,
            "target_damage_fraction": pd.to_numeric(
                rows["target_damage_fraction"], errors="raise"
            ),
            "realized_damage_fraction": pd.to_numeric(
                rows["realized_damage_fraction"], errors="raise"
            ),
            "source_manifest_path": _normalize_storage_path(
                source_manifest_path
            ),
            "status": "passed",
        }
    )


def _degradation_registry_rows(
    cases: pd.DataFrame,
    source_manifest_path: str,
) -> pd.DataFrame:
    experiment_id = "synthetic_degradation"
    required = (
        "case_id",
        "dataset_id",
        "dataset_scope",
        "experiment_id",
        "painting_id",
        "degraded_image_path",
        "clean_image_path",
        "degradation_id",
        "effect_mask_path",
        "degradation_family",
        "affected_content_fraction",
        "status",
    )
    _require_columns(cases, required, experiment_id)
    rows = _accepted_rows(cases, experiment_id)
    return pd.DataFrame(
        {
            "case_id": rows["case_id"],
            "dataset_id": rows["dataset_id"],
            "dataset_scope": rows["dataset_scope"],
            "experiment_id": rows["experiment_id"],
            "painting_id": rows["painting_id"],
            "input_image_path": rows["degraded_image_path"].map(
                _normalize_storage_path
            ),
            "clean_image_path": rows["clean_image_path"].map(
                _normalize_storage_path
            ),
            "mask_or_effect_id": rows["degradation_id"],
            "mask_or_effect_path": rows["effect_mask_path"].map(
                _normalize_storage_path
            ),
            "damage_or_degradation_type": rows["degradation_family"],
            "target_damage_fraction": pd.Series(
                float("nan"), index=rows.index, dtype="float64"
            ),
            "realized_damage_fraction": pd.to_numeric(
                rows["affected_content_fraction"], errors="raise"
            ),
            "source_manifest_path": _normalize_storage_path(
                source_manifest_path
            ),
            "status": "passed",
        }
    )


def build_case_registry(
    source_cases: Mapping[str, pd.DataFrame],
    *,
    source_manifest_paths: Mapping[str, str],
    canonical_masks: pd.DataFrame,
) -> pd.DataFrame:
    """Normalize the four approved source experiments without widening rows."""
    expected = BINARY_EXPERIMENTS | {"synthetic_degradation"}
    missing = sorted(expected - set(source_cases))
    missing_manifests = sorted(expected - set(source_manifest_paths))
    if missing or missing_manifests:
        raise ValueError(
            f"Missing source experiments={missing}; manifests={missing_manifests}"
        )
    frames = [
        _canonical_registry_rows(
            source_cases["canonical_missing_region"],
            canonical_masks,
            source_manifest_paths["canonical_missing_region"],
        ),
        _binary_registry_rows(
            source_cases["damage_size_sensitivity"],
            "damage_size_sensitivity",
            source_manifest_paths["damage_size_sensitivity"],
        ),
        _binary_registry_rows(
            source_cases["mask_robustness"],
            "mask_robustness",
            source_manifest_paths["mask_robustness"],
        ),
        _degradation_registry_rows(
            source_cases["synthetic_degradation"],
            source_manifest_paths["synthetic_degradation"],
        ),
    ]
    registry = (
        pd.concat(frames, ignore_index=True)
        .loc[:, CASE_REGISTRY_COLUMNS]
        .sort_values(["experiment_id", "painting_id", "case_id"], kind="stable")
        .reset_index(drop=True)
    )
    result = validate_dataframe(registry, CASE_REGISTRY_SCHEMA)
    if not result.passed:
        raise ValueError(f"Case registry failed schema validation: {result.to_dict()}")
    return registry


def _synthetic_ineligible_reason(
    degradation_family: str,
    policy: Mapping[str, Any],
) -> str:
    for group in policy.get("ineligible_reason_groups", {}).values():
        if degradation_family in set(group.get("families", [])):
            return str(group["reason"])
    return (
        "The degradation family has no approved inpainting-style routing rule; "
        "it remains available for degradation-specific analysis."
    )


def build_model_eligibility(
    case_registry: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Emit one explicit methodological routing decision per case and model."""
    schema_result = validate_dataframe(case_registry, CASE_REGISTRY_SCHEMA)
    if not schema_result.passed:
        raise ValueError("case_registry does not satisfy case_registry.v1")
    model_ids = [str(row["model_id"]) for row in config["models"]]
    if not model_ids or len(model_ids) != len(set(model_ids)):
        raise ValueError("Configured model IDs must be non-empty and unique")
    binary_policy = config["eligibility"]["binary_missing_region"]
    degradation_policy = config["eligibility"]["synthetic_degradation"]
    eligible_families = set(degradation_policy["eligible_families"])
    records: list[dict[str, Any]] = []
    for case in case_registry.to_dict(orient="records"):
        is_binary = case["experiment_id"] in BINARY_EXPERIMENTS
        is_zero_control = "zero_control" in str(case["case_id"])
        for model_id in model_ids:
            if is_binary:
                eligible = True
                reason = (
                    "Approved identity/no-op zero control for the binary "
                    "missing-region branch."
                    if is_zero_control
                    else "Approved binary missing-region restoration case."
                )
                objective = (
                    binary_policy["zero_control_objective"]
                    if is_zero_control
                    else binary_policy["restoration_objective"]
                )
                input_semantics = binary_policy["input_semantics"]
                mask_semantics = binary_policy["mask_semantics"]
            else:
                family = str(case["damage_or_degradation_type"])
                eligible = family in eligible_families
                reason = (
                    "Approved supplementary localized degradation diagnostic; "
                    "results must remain separate from missing-content claims."
                    if eligible
                    else _synthetic_ineligible_reason(family, degradation_policy)
                )
                objective = degradation_policy["restoration_objective"]
                input_semantics = degradation_policy["input_semantics"]
                mask_semantics = degradation_policy["mask_semantics"]
            records.append(
                {
                    "case_id": case["case_id"],
                    "model_id": model_id,
                    "eligible": bool(eligible),
                    "eligibility_reason": reason,
                    "input_semantics": input_semantics,
                    "mask_semantics": mask_semantics,
                    "restoration_objective": objective,
                }
            )
    eligibility = pd.DataFrame(records, columns=MODEL_ELIGIBILITY_COLUMNS)
    eligibility = eligibility.sort_values(
        ["model_id", "case_id"], kind="stable"
    ).reset_index(drop=True)
    result = validate_dataframe(eligibility, MODEL_ELIGIBILITY_SCHEMA)
    if not result.passed:
        raise ValueError(
            f"Model eligibility failed schema validation: {result.to_dict()}"
        )
    expected_pairs = len(case_registry) * len(model_ids)
    if len(eligibility) != expected_pairs:
        raise ValueError(
            f"Expected {expected_pairs} eligibility rows, found {len(eligibility)}"
        )
    return eligibility


def _region_parameters(region_id: str, regions: Mapping[str, Any]) -> dict[str, Any]:
    if region_id == "mask_bbox_crop":
        return {"margin_pixels": int(regions["mask_bbox_margin_pixels"])}
    if region_id in {
        "inner_boundary_band",
        "outer_boundary_band",
        "boundary_ring",
    }:
        return {"width_pixels": int(regions["boundary_width_pixels"])}
    if region_id == "outside_boundary_ring":
        return {
            "inner_offset_pixels": int(
                regions["outside_ring_inner_offset_pixels"]
            ),
            "outer_width_pixels": int(
                regions["outside_ring_outer_width_pixels"]
            ),
        }
    if region_id == "patch_window":
        return {
            "patch_size": list(regions["patch_size"]),
            "stride": list(regions["patch_stride"]),
            "minimum_content_fraction": float(
                regions["patch_minimum_content_fraction"]
            ),
        }
    return {}


def build_region_policy(config: Mapping[str, Any]) -> pd.DataFrame:
    """Build the complete metric-family by region compatibility matrix."""
    regions = config["regions"]
    definitions = {row["region_id"]: row for row in regions["definitions"]}
    ablations = config["ablation_policies"]
    records: list[dict[str, Any]] = []
    for family in config["metric_families"]:
        metric_family = str(family["metric_family"])
        compatible_regions = set(family["compatible_regions"])
        primary_regions = set(family["primary_regions"])
        unknown = (compatible_regions | primary_regions) - set(definitions)
        if unknown:
            raise ValueError(
                f"{metric_family} references unknown regions: {sorted(unknown)}"
            )
        for region_id, definition in definitions.items():
            compatible = region_id in compatible_regions
            if compatible:
                reason = "Approved for this metric family under the declared region semantics."
                role = "primary" if region_id in primary_regions else "diagnostic"
            else:
                reason = (
                    "Prohibited: this metric family requires different spatial "
                    "support or this region has no defensible interpretation."
                )
                role = "prohibited"
            if region_id == "masked_region" and metric_family == "ssim":
                reason = (
                    "Prohibited: SSIM requires an image-like rectangular "
                    "neighbourhood; sparse masked pixels are invalid."
                )
            case_semantics = (
                "synthetic_degradation"
                if region_id == "degradation_support"
                else "mask_or_effect"
                if region_id
                in {
                    "masked_region",
                    "mask_bbox_crop",
                    "inner_boundary_band",
                    "outer_boundary_band",
                    "boundary_ring",
                    "outside_mask_content",
                    "outside_boundary_ring",
                }
                else "all_cases"
            )
            threshold_policy = (
                f">= {int(regions['binary_mask_threshold'])} for binary masks"
                if case_semantics == "mask_or_effect"
                else "source support_threshold (inclusive)"
                if region_id == "degradation_support"
                else "not_applicable"
            )
            minimum_size_policy = (
                "both rectangle dimensions >= 7 pixels"
                if metric_family == "ssim" and compatible
                else "nonempty region"
                if compatible
                else "not_applicable"
            )
            ablation_ids = sorted(
                policy_id
                for policy_id, policy_regions in ablations.items()
                if region_id in set(policy_regions)
            )
            records.append(
                {
                    "policy_id": f"{metric_family}::{region_id}",
                    "policy_version": regions["policy_version"],
                    "metric_family": metric_family,
                    "region_id": region_id,
                    "region_type": definition["region_type"],
                    "spatial_support": definition["spatial_support"],
                    "compatible": bool(compatible),
                    "compatibility_reason": reason,
                    "primary_role": role,
                    "case_semantics": case_semantics,
                    "parameters_json": json.dumps(
                        _region_parameters(region_id, regions),
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    "threshold_policy": threshold_policy,
                    "minimum_size_policy": minimum_size_policy,
                    "ablation_policy_ids_json": json.dumps(ablation_ids),
                    "status": "approved",
                }
            )
    policy = pd.DataFrame(records, columns=REGION_POLICY_COLUMNS)
    policy = policy.sort_values(
        ["metric_family", "region_id"], kind="stable"
    ).reset_index(drop=True)
    result = validate_dataframe(policy, REGION_POLICY_SCHEMA)
    if not result.passed:
        raise ValueError(f"Region policy failed schema validation: {result.to_dict()}")
    return policy


def build_schema_registry_payload(
    schema_names: Sequence[str] = (
        "case_registry",
        "model_eligibility",
        "region_policy",
        "artifact_manifest",
        "validation_checks",
    ),
) -> dict[str, Any]:
    """Serialize the downstream-facing schema subset without Python objects."""
    schemas: list[dict[str, Any]] = []
    for name in schema_names:
        try:
            schema = SCHEMA_REGISTRY[name]
        except KeyError as exc:
            raise KeyError(f"Unknown schema requested for export: {name}") from exc
        schemas.append(
            {
                "name": schema.name,
                "version": schema.version,
                "required_columns": list(schema.required_columns),
                "primary_key": list(schema.primary_key),
                "non_nullable": list(schema.non_nullable),
                "optional_columns": list(schema.optional_columns),
                "allowed_values": {
                    column: sorted(values, key=str)
                    for column, values in schema.allowed_values.items()
                },
            }
        )
    return {
        "schema_registry_version": SCHEMA_REGISTRY_VERSION,
        "producer_module": "restoration_eval.experiment_contracts",
        "producer_module_version": EXPERIMENT_CONTRACTS_MODULE_VERSION,
        "schemas": schemas,
    }


__all__ = [
    "EXPERIMENT_CONTRACTS_MODULE_VERSION",
    "load_evaluation_contract_config",
    "build_case_registry",
    "build_model_eligibility",
    "build_region_policy",
    "build_schema_registry_payload",
]
