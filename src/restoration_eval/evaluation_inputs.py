"""Model-agnostic normalization of restoration candidates for evaluation notebooks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping

import numpy as np
import pandas as pd

EVALUATION_INPUTS_MODULE_VERSION = "1.0.1"
EVALUATION_WORKLIST_SCHEMA_VERSION = "evaluation_worklist.v1"
EVALUATION_WORKLIST_COLUMNS = (
    "candidate_id", "case_id", "model_id", "candidate_index", "seed",
    "prompt_policy_id", "prompt_variant_id", "execution_role",
    "configuration_id", "restored_path", "restored_sha256", "mask_threshold",
    "technical_validation_passed", "source_table_id", "dataset_id",
    "dataset_scope", "experiment_id", "painting_id", "input_image_path",
    "clean_image_path", "mask_or_effect_id", "mask_or_effect_path",
    "damage_or_degradation_type", "target_damage_fraction",
    "realized_damage_fraction", "content_x_min", "content_y_min",
    "content_x_max", "content_y_max", "is_zero_control", "status",
)
EXCLUSION_COLUMNS = (
    "source_table_id", "candidate_id", "case_id", "model_id",
    "source_status", "exclusion_reason",
)
SOURCE_SUMMARY_COLUMNS = (
    "source_table_id", "model_id", "source_rows", "included_rows",
    "excluded_rows", "unique_cases", "zero_control_candidates",
)


@dataclass(frozen=True)
class EvaluationInputBundle:
    """Normalized candidates plus explicit exclusions and source counts."""

    worklist: pd.DataFrame
    exclusions: pd.DataFrame
    source_summary: pd.DataFrame


def _require_columns(frame: pd.DataFrame, columns: set[str], label: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def _as_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    return series.fillna("").astype(str).str.strip().str.lower().isin(
        {"true", "1", "yes"}
    )


def _optional_column(frame: pd.DataFrame, column: str, default: object) -> pd.Series:
    return frame[column] if column in frame else pd.Series(default, index=frame.index)


def _normalize_source_path(value: object, source_root: str) -> str:
    """Return a stable repository-relative path for one source-owned artifact."""

    text = str(value).strip().replace("\\", "/")
    root = str(source_root).strip().replace("\\", "/").rstrip("/")
    if not text or not root or Path(text).is_absolute():
        return text
    while text.startswith("./"):
        text = text[2:]
    while root.startswith("./"):
        root = root[2:]
    if text == root or text.startswith(root + "/"):
        return text
    return (PurePosixPath(root) / PurePosixPath(text)).as_posix()

def build_evaluation_worklist(
    case_registry: pd.DataFrame,
    model_eligibility: pd.DataFrame,
    preprocessing_geometry: pd.DataFrame,
    candidate_tables: Mapping[str, pd.DataFrame],
    candidate_source_roots: Mapping[str, str] | None = None,
) -> EvaluationInputBundle:
    """Build one auditable, non-persisted candidate worklist.

    Completed and technically valid candidates are retained. Other rows are
    returned as explicit exclusions. A completed candidate for an ineligible
    case/model pair is a contract violation and raises immediately.
    """

    _require_columns(case_registry, {
        "case_id", "dataset_id", "dataset_scope", "experiment_id",
        "painting_id", "input_image_path", "clean_image_path",
        "mask_or_effect_id", "mask_or_effect_path",
        "damage_or_degradation_type", "target_damage_fraction",
        "realized_damage_fraction", "status",
    }, "case_registry")
    _require_columns(model_eligibility, {"case_id", "model_id", "eligible"},
                     "model_eligibility")
    _require_columns(preprocessing_geometry, {
        "painting_id", "content_x_min", "content_y_min",
        "content_x_max", "content_y_max", "status",
    }, "preprocessing_geometry")
    if case_registry["case_id"].duplicated().any():
        raise ValueError("case_registry contains duplicate case_id values")
    if model_eligibility.duplicated(["case_id", "model_id"]).any():
        raise ValueError("model_eligibility contains duplicate case/model pairs")
    if preprocessing_geometry["painting_id"].duplicated().any():
        raise ValueError("preprocessing_geometry contains duplicate painting_id values")
    if not case_registry["status"].astype(str).eq("passed").all():
        raise ValueError("case_registry contains rows that did not pass")
    if not preprocessing_geometry["status"].astype(str).eq("passed").all():
        raise ValueError("preprocessing_geometry contains rows that did not pass")
    if not candidate_tables:
        raise ValueError("candidate_tables must contain at least one source table")

    source_roots = candidate_source_roots or {}
    unknown_source_roots = set(source_roots) - set(candidate_tables)
    if unknown_source_roots:
        raise ValueError(
            "candidate_source_roots contains unknown source tables: "
            f"{sorted(unknown_source_roots)}"
        )

    included_frames: list[pd.DataFrame] = []
    exclusion_records: list[dict[str, object]] = []
    summary_records: list[dict[str, object]] = []
    for source_table_id, source_frame in candidate_tables.items():
        label = str(source_table_id).strip()
        if not label:
            raise ValueError("candidate table identifiers must be non-empty")
        frame = source_frame.copy()
        _require_columns(frame, {
            "candidate_id", "case_id", "model_id", "candidate_index",
            "configuration_id", "restored_path", "restored_sha256",
            "mask_threshold", "status",
        }, label)
        if frame[["candidate_id", "case_id"]].isna().any().any():
            raise ValueError(f"{label} contains null candidate or case identifiers")
        if frame["candidate_id"].astype(str).duplicated().any():
            raise ValueError(f"{label} contains duplicate candidate_id values")

        completed = frame["status"].astype(str).eq("completed")
        technical = (_as_bool(frame["technical_validation_passed"])
                     if "technical_validation_passed" in frame
                     else pd.Series(True, index=frame.index))
        include = completed & technical
        for row in frame.loc[~include].to_dict("records"):
            source_status = str(row.get("status", ""))
            exclusion_records.append({
                "source_table_id": label,
                "candidate_id": str(row.get("candidate_id", "")),
                "case_id": str(row.get("case_id", "")),
                "model_id": str(row.get("model_id", "")),
                "source_status": source_status,
                "exclusion_reason": ("source_status_not_completed"
                    if source_status != "completed"
                    else "technical_validation_not_passed"),
            })

        selected = frame.loc[include].copy()
        if selected["restored_path"].fillna("").astype(str).str.strip().eq("").any():
            raise ValueError(f"{label} has completed candidates without restored paths")
        if selected["mask_threshold"].isna().any():
            raise ValueError(f"{label} has completed candidates without mask thresholds")
        normalized = selected[[
            "candidate_id", "case_id", "model_id", "candidate_index",
            "configuration_id", "restored_path", "restored_sha256",
            "mask_threshold", "status",
        ]].copy()
        normalized["restored_path"] = normalized["restored_path"].map(
            lambda value: _normalize_source_path(
                value, str(source_roots.get(label, ""))
            )
        )
        normalized["seed"] = _optional_column(selected, "seed", np.nan)
        normalized["prompt_policy_id"] = _optional_column(selected, "prompt_policy_id", "")
        normalized["prompt_variant_id"] = _optional_column(selected, "prompt_variant_id", "")
        normalized["execution_role"] = _optional_column(selected, "execution_role", "primary")
        normalized["technical_validation_passed"] = technical.loc[selected.index]
        normalized["source_table_id"] = label
        included_frames.append(normalized.reset_index(drop=True))
        summary_records.append({
            "source_table_id": label,
            "model_id": "|".join(sorted(frame["model_id"].astype(str).unique())),
            "source_rows": len(frame), "included_rows": int(include.sum()),
            "excluded_rows": int((~include).sum()),
            "unique_cases": int(selected["case_id"].nunique()),
            "zero_control_candidates": 0,
        })

    candidates = pd.concat(included_frames, ignore_index=True)
    if candidates["candidate_id"].astype(str).duplicated().any():
        duplicates = candidates.loc[
            candidates["candidate_id"].astype(str).duplicated(keep=False),
            "candidate_id",
        ].astype(str).unique().tolist()
        raise ValueError(f"candidate_id values are not globally unique: {duplicates[:5]}")

    case_columns = [
        "case_id", "dataset_id", "dataset_scope", "experiment_id",
        "painting_id", "input_image_path", "clean_image_path",
        "mask_or_effect_id", "mask_or_effect_path",
        "damage_or_degradation_type", "target_damage_fraction",
        "realized_damage_fraction",
    ]
    worklist = candidates.merge(case_registry[case_columns], on="case_id",
        how="left", validate="many_to_one", indicator=True)
    if not worklist["_merge"].eq("both").all():
        missing = worklist.loc[worklist["_merge"].ne("both"), "case_id"].unique()
        raise ValueError(f"Candidates reference unknown case_id values: {missing[:5]}")
    worklist = worklist.drop(columns="_merge")

    eligibility = model_eligibility[["case_id", "model_id", "eligible"]].copy()
    eligibility["eligible"] = _as_bool(eligibility["eligible"])
    worklist = worklist.merge(eligibility, on=["case_id", "model_id"],
                              how="left", validate="many_to_one")
    if worklist["eligible"].isna().any():
        raise ValueError("Candidates are missing model-eligibility records")
    ineligible = worklist.loc[~worklist["eligible"], ["case_id", "model_id"]]
    if not ineligible.empty:
        raise ValueError("Completed candidates exist for ineligible pairs: "
                         f"{ineligible.drop_duplicates().head().to_dict('records')}")
    worklist = worklist.drop(columns="eligible")

    geometry_columns = ["painting_id", "content_x_min", "content_y_min",
                        "content_x_max", "content_y_max"]
    worklist = worklist.merge(preprocessing_geometry[geometry_columns],
        on="painting_id", how="left", validate="many_to_one")
    if worklist[geometry_columns[1:]].isna().any().any():
        raise ValueError("Candidates are missing preprocessing content geometry")
    target = pd.to_numeric(worklist["target_damage_fraction"], errors="coerce")
    realized = pd.to_numeric(worklist["realized_damage_fraction"], errors="coerce")
    worklist["is_zero_control"] = target.eq(0.0) & realized.eq(0.0)
    worklist["mask_threshold"] = pd.to_numeric(worklist["mask_threshold"],
                                                errors="raise").astype(int)
    for column in ("content_x_min", "content_y_min", "content_x_max", "content_y_max"):
        worklist[column] = pd.to_numeric(worklist[column], errors="raise").astype(int)
    worklist = worklist.loc[:, EVALUATION_WORKLIST_COLUMNS].sort_values(
        ["case_id", "model_id", "candidate_index", "candidate_id"],
        kind="stable").reset_index(drop=True)
    source_summary = pd.DataFrame(summary_records, columns=SOURCE_SUMMARY_COLUMNS)
    zero_counts = worklist.groupby("source_table_id")["is_zero_control"].sum()
    source_summary["zero_control_candidates"] = (
        source_summary["source_table_id"].map(zero_counts).fillna(0).astype(int))
    return EvaluationInputBundle(worklist,
        pd.DataFrame(exclusion_records, columns=EXCLUSION_COLUMNS), source_summary)


def validate_evaluation_worklist(worklist: pd.DataFrame) -> dict[str, object]:
    """Return compact structural validation evidence for a normalized worklist."""

    missing = sorted(set(EVALUATION_WORKLIST_COLUMNS) - set(worklist.columns))
    duplicates = (int(worklist["candidate_id"].duplicated(keep=False).sum())
                  if "candidate_id" in worklist else 0)
    conflicts = (int((worklist.groupby("case_id")["mask_threshold"].nunique() > 1).sum())
                 if {"case_id", "mask_threshold"}.issubset(worklist.columns) else 0)
    completed = bool("status" in worklist and
                     worklist["status"].astype(str).eq("completed").all())
    technical = bool("technical_validation_passed" in worklist and
                     _as_bool(worklist["technical_validation_passed"]).all())
    return {
        "schema_version": EVALUATION_WORKLIST_SCHEMA_VERSION,
        "row_count": len(worklist), "missing_columns": missing,
        "duplicate_candidate_rows": duplicates,
        "mask_threshold_conflict_cases": conflicts,
        "all_completed": completed, "all_technically_valid": technical,
        "passed": not missing and duplicates == 0 and conflicts == 0
                  and completed and technical,
    }
