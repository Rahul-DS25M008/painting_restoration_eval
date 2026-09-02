"""Explainable case-catalog and embedding-retrieval utilities for Notebook 29.

The module consumes frozen Notebook 15--28 evidence.  It performs no model
inference, does not modify upstream outputs, and keeps DINOv2 and CLIP retrieval
as separate evidence views rather than constructing a combined similarity or
trust score.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml

from .paths import find_project_root, resolve_repo_path


MODULE_NAME = "restoration_eval.explainable_case_retrieval"
MODULE_VERSION = "1.0.0"
CONFIG_SCHEMA_VERSION = "explainable_case_retrieval_config.v1"
EXPLANATION_SCHEMA_VERSION = "explanation_cases.v1"
NEIGHBOR_SCHEMA_VERSION = "case_neighbors.v1"

EXPLANATION_CASE_COLUMNS = (
    "explanation_case_id", "candidate_id", "case_id", "painting_id",
    "model_id", "experiment_id", "prompt_variant_id", "population_role",
    "category", "style_or_period", "degradation_family", "severity",
    "restored_path", "damaged_path", "clean_path", "mask_path",
    "difference_paths_json", "uncertainty_paths_json", "seam_paths_json",
    "colour_paths_json", "texture_paths_json", "semantic_paths_json",
    "mask_boundary_paths_json", "asset_availability_json",
    "recommendation_category", "manual_review_required",
    "triggered_flag_ids_json", "insufficient_flag_ids_json",
    "triggered_category_ids_json", "triggering_evidence_ids_json",
    "affected_regions_json", "recommended_actions_json",
    "metric_disagreement_ids_json", "uncertainty_group_id",
    "uncertainty_applicability", "retrieval_dino_eligible",
    "retrieval_clip_eligible", "retrieval_lane", "report_selected",
    "report_selection_roles_json", "counterfactual_panel_ids_json",
    "evidence_source_notebook_ids_json", "evidence_coverage_status",
    "scope_status", "scope_note", "schema_version", "status", "issue",
)

CASE_NEIGHBOR_COLUMNS = (
    "neighbor_record_id", "query_id", "query_candidate_id",
    "query_case_id", "query_painting_id", "query_model_id", "lane",
    "feature_model_id", "image_role", "region_id", "neighbor_rank",
    "neighbor_candidate_id", "neighbor_case_id", "neighbor_painting_id",
    "neighbor_model_id", "neighbor_recommendation_category",
    "neighbor_manual_review_required", "cosine_similarity",
    "cosine_distance", "secondary_feature_model_id",
    "secondary_cosine_similarity", "secondary_cosine_distance",
    "secondary_query_embedding_id", "secondary_neighbor_embedding_id",
    "same_category", "same_degradation_family",
    "same_model", "same_case", "same_painting", "query_embedding_id",
    "neighbor_embedding_id", "selection_reason", "schema_version",
    "status", "issue",
)


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    return config.get("explainable_case_retrieval", config)


def _normalized_relative_path(value: Any) -> bool:
    text = str(value).strip()
    return bool(text) and not Path(text).is_absolute() and "\\" not in text


def _json_list(value: Any) -> str:
    if value is None or (not isinstance(value, (list, tuple, set, dict)) and pd.isna(value)):
        return "[]"
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return "[]"
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = [text]
    elif isinstance(value, Mapping):
        parsed = list(value)
    else:
        parsed = list(value)
    return json.dumps(sorted({str(item) for item in parsed if str(item).strip()}), separators=(",", ":"))


def _stable_id(prefix: str, *parts: Any) -> str:
    material = "|".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(material.encode('utf-8')).hexdigest()[:20]}"


def _as_bool(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if value is None or (not isinstance(value, (list, tuple, dict)) and pd.isna(value)):
        return False
    return str(value).strip().lower() in {"true", "1", "1.0", "yes", "y"}


def load_explainable_case_retrieval_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the approved Notebook 29 contract."""

    with Path(path).open("r", encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict) or config.get("config_schema_version") != CONFIG_SCHEMA_VERSION:
        raise ValueError("Unsupported explainable case-retrieval config schema")
    settings = _settings(config)
    required = {
        "notebook_id", "notebook_stem", "explanation_schema_version",
        "neighbor_schema_version", "inputs", "output", "population",
        "catalog", "retrieval", "counterfactuals", "report",
        "expected_counts", "evidence_policy", "known_limitations",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"Explainable case-retrieval config is missing keys: {missing}")
    if settings["notebook_id"] != "29" or settings["notebook_stem"] != "29_explainable_ai_and_case_retrieval":
        raise ValueError("Notebook 29 identity contract changed")
    if settings["explanation_schema_version"] != EXPLANATION_SCHEMA_VERSION:
        raise ValueError("Explanation schema version differs from helper")
    if settings["neighbor_schema_version"] != NEIGHBOR_SCHEMA_VERSION:
        raise ValueError("Neighbor schema version differs from helper")
    for key, value in settings["inputs"].items():
        if not _normalized_relative_path(value):
            raise ValueError(f"inputs.{key} must be a normalized repository-relative path")

    exact_output = {
        "root": "outputs/29_explainable_ai_and_case_retrieval",
        "explanation_cases_path": "data/explanation_cases.csv",
        "case_neighbors_path": "data/case_neighbors.csv",
        "counterfactual_panels_dir": "figures/counterfactual_panels",
        "retrieval_panels_dir": "figures/example_retrieval_panels",
        "report_path": "reports/explanation_catalog.html",
        "run_manifest_path": "manifests/run_manifest.json",
        "artifacts_path": "manifests/artifacts.csv",
        "validation_path": "validation/checks.csv",
    }
    for key, expected in exact_output.items():
        if settings["output"].get(key) != expected:
            raise ValueError(f"output.{key} must equal {expected!r}")

    expected = settings["expected_counts"]
    if int(expected["explanation_rows"]) != int(settings["population"]["catalog_candidate_count"]):
        raise ValueError("Catalog population arithmetic is inconsistent")
    if int(expected["neighbor_rows"]) != int(expected["retrieval_queries"]) * int(expected["retrieval_lanes"]) * int(expected["neighbors_per_lane"]):
        raise ValueError("Neighbor-row arithmetic is inconsistent")
    if int(expected["counterfactual_panels"]) != len(settings["counterfactuals"]["types"]) * int(settings["counterfactuals"]["panels_per_type"]):
        raise ValueError("Counterfactual-panel arithmetic is inconsistent")
    if int(expected["selected_report_units"]) != int(expected["counterfactual_panels"]) + int(expected["retrieval_panels"]):
        raise ValueError("Selected report-unit arithmetic is inconsistent")
    if not settings["catalog"]["full_population_required"] or not settings["catalog"]["selection_does_not_filter_persisted_rows"]:
        raise ValueError("The full catalog may not be reduced to report selections")
    retrieval = settings["retrieval"]
    if retrieval["combine_feature_scores"]:
        raise ValueError("DINOv2 and CLIP retrieval scores may not be combined")
    if not all(retrieval[key] for key in ("exclude_self", "exclude_same_case", "exclude_same_painting")):
        raise ValueError("All leakage exclusions must remain active")
    if retrieval["primary_feature_model_id"] == retrieval["secondary_feature_model_id"]:
        raise ValueError("Primary and secondary retrieval views must differ")
    if settings["counterfactuals"]["prompt_policy_interpretation"] != "damage_specific_not_style_specific":
        raise ValueError("Prompt ablation must remain damage-specific")
    report = settings["report"]
    if not report["self_contained_html"] or not report["approved_mock_structure_locked"]:
        raise ValueError("The approved self-contained mock structure must remain locked")
    if len(report["required_section_ids"]) != 14 or len(set(report["required_section_ids"])) != 14:
        raise ValueError("Report must retain the approved fourteen-section structure")
    prohibited = settings["evidence_policy"]
    if any(bool(prohibited[key]) for key in (
        "flags_are_human_ground_truth", "flags_are_conservation_ground_truth",
        "retrieval_similarity_is_correctness", "uncertainty_is_calibrated_confidence",
        "independent_style_effect_allowed", "style_specific_prompt_claim_allowed",
        "universal_model_superiority_claim_allowed", "bounded_sdxl_in_full_comparison",
        "combined_retrieval_score_retained",
    )):
        raise ValueError("A prohibited evidence interpretation is enabled")
    return config


def resolve_explainable_case_retrieval_inputs(
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
    expected_notebook_ids: Sequence[str] = tuple(f"{n:02d}" for n in range(15, 29)),
) -> pd.DataFrame:
    """Return one completion-gate row for each direct evidence producer."""

    rows = []
    for notebook_id in expected_notebook_ids:
        manifest = manifests.get(notebook_id)
        present = isinstance(manifest, Mapping)
        rows.append({
            "notebook_id": notebook_id,
            "manifest_present": present,
            "run_status": str(manifest.get("run_status", "")) if present else "",
            "validation_status": str(manifest.get("validation_status", "")) if present else "",
            "completion_gate_passed": bool(manifest.get("completion_gate_passed", False)) if present else False,
        })
    frame = pd.DataFrame(rows)
    frame["passed"] = frame["manifest_present"] & frame["completion_gate_passed"] & frame["run_status"].str.lower().isin({"completed", "complete", "finished"})
    frame["details"] = frame.apply(lambda row: f"run={row['run_status']}; validation={row['validation_status']}; gate={row['completion_gate_passed']}", axis=1)
    return frame


def load_embedding_index(
    manifest_path: str | Path,
    archive_path: str | Path,
    *,
    feature_model_id: str,
    image_role: str = "restored",
    region_id: str = "content_region",
) -> tuple[pd.DataFrame, np.ndarray]:
    """Load one validated embedding view and align rows with its NPZ array."""

    manifest = pd.read_csv(manifest_path, low_memory=False)
    required = {"embedding_id", "feature_model_id", "image_role", "region_id", "representative_candidate_id", "array_name", "array_index", "status"}
    missing = sorted(required - set(manifest.columns))
    if missing:
        raise ValueError(f"Embedding manifest is missing columns: {missing}")
    selected = manifest.loc[
        manifest["feature_model_id"].eq(feature_model_id)
        & manifest["image_role"].eq(image_role)
        & manifest["region_id"].eq(region_id)
        & manifest["status"].eq("ok")
    ].copy()
    selected = selected.loc[selected["representative_candidate_id"].fillna("").astype(str).str.len().gt(0)]
    if selected.empty:
        raise ValueError(f"No embeddings for {feature_model_id}/{image_role}/{region_id}")
    if selected["representative_candidate_id"].duplicated().any():
        raise ValueError("Embedding view contains duplicate candidate IDs")
    array_names = selected["array_name"].dropna().unique().tolist()
    if len(array_names) != 1:
        raise ValueError("An embedding view must resolve to exactly one array")
    with np.load(archive_path, allow_pickle=False) as archive:
        array = np.asarray(archive[array_names[0]], dtype=np.float32)
    positions = pd.to_numeric(selected["array_index"], errors="raise").astype(int).to_numpy()
    if positions.min() < 0 or positions.max() >= len(array):
        raise ValueError("Embedding array indices are out of bounds")
    vectors = array[positions]
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if not np.isfinite(vectors).all() or np.any(norms <= 0):
        raise ValueError("Embeddings must be finite and non-zero")
    vectors = vectors / norms
    return selected.reset_index(drop=True), vectors


def retrieve_neighbors(
    query_candidate_id: str,
    catalog: pd.DataFrame,
    embedding_manifest: pd.DataFrame,
    normalized_vectors: np.ndarray,
    *,
    feature_model_id: str,
    secondary_embedding_manifest: pd.DataFrame | None = None,
    secondary_normalized_vectors: np.ndarray | None = None,
    secondary_feature_model_id: str = "",
    lane: str,
    top_k: int = 5,
    lower_risk_category: str = "suitable_for_preliminary_inspection",
) -> pd.DataFrame:
    """Retrieve one leakage-controlled lane for one query candidate."""

    if len(embedding_manifest) != len(normalized_vectors):
        raise ValueError("Manifest and embedding-array row counts differ")
    if lane not in {"lower_risk", "flagged"}:
        raise ValueError("lane must be 'lower_risk' or 'flagged'")
    secondary_requested = bool(secondary_feature_model_id)
    if secondary_requested != (
        secondary_embedding_manifest is not None
        and secondary_normalized_vectors is not None
    ):
        raise ValueError("Secondary retrieval requires model ID, manifest, and vectors together")
    secondary_emb: pd.DataFrame | None = None
    secondary_index: dict[str, int] = {}
    secondary_query_index: int | None = None
    if secondary_requested:
        if len(secondary_embedding_manifest) != len(secondary_normalized_vectors):
            raise ValueError("Secondary manifest and embedding-array row counts differ")
        secondary_emb = secondary_embedding_manifest.reset_index(drop=True)
        secondary_candidates = secondary_emb["representative_candidate_id"].astype(str)
        if secondary_candidates.duplicated().any():
            raise ValueError("Secondary embedding view contains duplicate candidate IDs")
        secondary_index = {
            candidate_id: index
            for index, candidate_id in enumerate(secondary_candidates)
        }
        if query_candidate_id not in secondary_index:
            raise ValueError("Query has no secondary embedding")
        secondary_query_index = secondary_index[query_candidate_id]
    meta = catalog.set_index("candidate_id", drop=False)
    if query_candidate_id not in meta.index:
        raise KeyError(f"Query candidate not in catalog: {query_candidate_id}")
    emb = embedding_manifest.reset_index(drop=True)
    candidate_col = emb["representative_candidate_id"].astype(str)
    matches = np.flatnonzero(candidate_col.eq(query_candidate_id).to_numpy())
    if len(matches) != 1:
        raise ValueError("Query must have exactly one embedding")
    query = meta.loc[query_candidate_id]
    joined = emb.copy()
    joined["_row"] = np.arange(len(joined))
    joined = joined.merge(catalog, left_on="representative_candidate_id", right_on="candidate_id", how="inner", validate="one_to_one", suffixes=("_embedding", ""))
    eligible = (
        joined["candidate_id"].ne(query_candidate_id)
        & joined["case_id"].ne(str(query["case_id"]))
        & joined["painting_id"].ne(str(query["painting_id"]))
    )
    if lane == "lower_risk":
        eligible &= joined["recommendation_category"].eq(lower_risk_category) & ~joined["manual_review_required"].map(_as_bool)
    else:
        eligible &= joined["recommendation_category"].ne(lower_risk_category) | joined["manual_review_required"].map(_as_bool)
    pool = joined.loc[eligible].copy()
    if len(pool) < top_k:
        raise ValueError(f"Only {len(pool)} eligible {lane} neighbors; need {top_k}")
    similarities = normalized_vectors[pool["_row"].to_numpy()] @ normalized_vectors[matches[0]]
    pool["cosine_similarity"] = similarities.astype(float)
    pool = pool.sort_values(["cosine_similarity", "candidate_id"], ascending=[False, True], kind="mergesort").head(top_k).reset_index(drop=True)
    rows = []
    query_id = _stable_id("query", query_candidate_id)
    for rank, (_, neighbor) in enumerate(pool.iterrows(), start=1):
        similarity = float(neighbor["cosine_similarity"])
        neighbor_candidate_id = str(neighbor["candidate_id"])
        if secondary_requested:
            if neighbor_candidate_id not in secondary_index:
                raise ValueError(f"Neighbor has no secondary embedding: {neighbor_candidate_id}")
            secondary_neighbor_index = secondary_index[neighbor_candidate_id]
            secondary_similarity = float(
                secondary_normalized_vectors[secondary_neighbor_index]
                @ secondary_normalized_vectors[secondary_query_index]
            )
            secondary_query_embedding_id = str(
                secondary_emb.iloc[secondary_query_index]["embedding_id"]
            )
            secondary_neighbor_embedding_id = str(
                secondary_emb.iloc[secondary_neighbor_index]["embedding_id"]
            )
        else:
            secondary_similarity = np.nan
            secondary_query_embedding_id = ""
            secondary_neighbor_embedding_id = ""
        rows.append({
            "neighbor_record_id": _stable_id("neighbor", query_candidate_id, lane, feature_model_id, rank, neighbor["candidate_id"]),
            "query_id": query_id,
            "query_candidate_id": query_candidate_id,
            "query_case_id": query["case_id"],
            "query_painting_id": query["painting_id"],
            "query_model_id": query["model_id"],
            "lane": lane,
            "feature_model_id": feature_model_id,
            "image_role": str(neighbor.get("image_role", "restored")),
            "region_id": str(neighbor.get("region_id", "content_region")),
            "neighbor_rank": rank,
            "neighbor_candidate_id": neighbor["candidate_id"],
            "neighbor_case_id": neighbor["case_id"],
            "neighbor_painting_id": neighbor["painting_id"],
            "neighbor_model_id": neighbor["model_id"],
            "neighbor_recommendation_category": neighbor["recommendation_category"],
            "neighbor_manual_review_required": _as_bool(neighbor["manual_review_required"]),
            "cosine_similarity": similarity,
            "cosine_distance": 1.0 - similarity,
            "secondary_feature_model_id": secondary_feature_model_id,
            "secondary_cosine_similarity": secondary_similarity,
            "secondary_cosine_distance": 1.0 - secondary_similarity if np.isfinite(secondary_similarity) else np.nan,
            "secondary_query_embedding_id": secondary_query_embedding_id,
            "secondary_neighbor_embedding_id": secondary_neighbor_embedding_id,
            "same_category": str(neighbor.get("category", "")) == str(query.get("category", "")),
            "same_degradation_family": str(neighbor.get("degradation_family", "")) == str(query.get("degradation_family", "")),
            "same_model": str(neighbor["model_id"]) == str(query["model_id"]),
            "same_case": False,
            "same_painting": False,
            "query_embedding_id": emb.iloc[matches[0]]["embedding_id"],
            "neighbor_embedding_id": neighbor["embedding_id"],
            "selection_reason": f"{lane} nearest neighbor under {feature_model_id}; self/same-case/same-painting excluded",
        })
    return coerce_case_neighbors(rows)


def coerce_explanation_cases(records: pd.DataFrame | Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    """Coerce records into the canonical full-catalog schema."""

    frame = records.copy() if isinstance(records, pd.DataFrame) else pd.DataFrame(records)
    for column in EXPLANATION_CASE_COLUMNS:
        if column not in frame:
            frame[column] = False if column in {"manual_review_required", "retrieval_dino_eligible", "retrieval_clip_eligible", "report_selected"} else ""
    for column in EXPLANATION_CASE_COLUMNS:
        if column.endswith("_json"):
            frame[column] = frame[column].map(_json_list)
    for column in ("manual_review_required", "retrieval_dino_eligible", "retrieval_clip_eligible", "report_selected"):
        frame[column] = frame[column].map(_as_bool)
    frame["schema_version"] = EXPLANATION_SCHEMA_VERSION
    frame["status"] = frame["status"].replace("", "ok")
    missing_id = frame["explanation_case_id"].fillna("").astype(str).str.len().eq(0)
    frame.loc[missing_id, "explanation_case_id"] = [
        _stable_id("explanation", candidate_id)
        for candidate_id in frame.loc[missing_id, "candidate_id"]
    ]
    return frame.loc[:, EXPLANATION_CASE_COLUMNS].copy()


def coerce_case_neighbors(records: pd.DataFrame | Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    """Coerce records into the canonical neighbor schema."""

    frame = records.copy() if isinstance(records, pd.DataFrame) else pd.DataFrame(records)
    for column in CASE_NEIGHBOR_COLUMNS:
        if column not in frame:
            frame[column] = False if column.startswith("same_") or column == "neighbor_manual_review_required" else np.nan if column in {"neighbor_rank", "cosine_similarity", "cosine_distance", "secondary_cosine_similarity", "secondary_cosine_distance"} else ""
    for column in ("neighbor_manual_review_required", "same_category", "same_degradation_family", "same_model", "same_case", "same_painting"):
        frame[column] = frame[column].map(_as_bool)
    frame["neighbor_rank"] = pd.to_numeric(frame["neighbor_rank"], errors="coerce").astype("Int64")
    frame["cosine_similarity"] = pd.to_numeric(frame["cosine_similarity"], errors="coerce")
    frame["cosine_distance"] = pd.to_numeric(frame["cosine_distance"], errors="coerce")
    frame["secondary_cosine_similarity"] = pd.to_numeric(frame["secondary_cosine_similarity"], errors="coerce")
    frame["secondary_cosine_distance"] = pd.to_numeric(frame["secondary_cosine_distance"], errors="coerce")
    frame["schema_version"] = NEIGHBOR_SCHEMA_VERSION
    frame["status"] = frame["status"].replace("", "ok")
    return frame.loc[:, CASE_NEIGHBOR_COLUMNS].copy()


def validate_explanation_cases(
    frame: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    require_complete: bool = True,
) -> pd.DataFrame:
    """Validate schema, identity, population, and report-selection separation."""

    expected = _settings(config)["expected_counts"]
    checks = [
        ("exact_columns", list(frame.columns) == list(EXPLANATION_CASE_COLUMNS), f"columns={len(frame.columns)}"),
        ("schema_version", frame.get("schema_version", pd.Series(dtype=str)).eq(EXPLANATION_SCHEMA_VERSION).all(), EXPLANATION_SCHEMA_VERSION),
        ("candidate_unique", not frame.get("candidate_id", pd.Series(dtype=str)).duplicated().any(), f"rows={len(frame)}"),
        ("explanation_id_unique", not frame.get("explanation_case_id", pd.Series(dtype=str)).duplicated().any(), f"rows={len(frame)}"),
        ("required_ids_nonempty", frame[["candidate_id", "case_id", "painting_id", "model_id"]].fillna("").astype(str).apply(lambda col: col.str.len().gt(0)).all().all(), "candidate/case/painting/model"),
        ("report_roles_are_subset", int(frame["report_selected"].map(_as_bool).sum()) <= len(frame), f"selected_rows={int(frame['report_selected'].map(_as_bool).sum())}"),
        ("json_fields_parse", all(_valid_json_list(frame[column]) for column in frame.columns if column.endswith("_json")), "all JSON-list fields"),
    ]
    if require_complete:
        checks.extend([
            ("full_catalog_rows", len(frame) == int(expected["explanation_rows"]), f"expected={expected['explanation_rows']}; observed={len(frame)}"),
            ("unique_cases", frame["case_id"].nunique() == int(expected["unique_cases"]), f"expected={expected['unique_cases']}; observed={frame['case_id'].nunique()}"),
            ("not_report_only", len(frame) > int(expected["selected_report_units"]), f"catalog={len(frame)}; report_units={expected['selected_report_units']}"),
        ])
    return pd.DataFrame(checks, columns=["check_id", "passed", "details"])


def _valid_json_list(series: pd.Series) -> bool:
    try:
        return all(isinstance(json.loads(str(value)), list) for value in series)
    except (json.JSONDecodeError, TypeError):
        return False


def validate_case_neighbors(
    frame: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    require_complete: bool = True,
) -> pd.DataFrame:
    """Validate exact ranks, leakage exclusions, and separate feature views."""

    expected = _settings(config)["expected_counts"]
    numeric_ok = frame["cosine_similarity"].notna().all() and np.isfinite(frame["cosine_similarity"].to_numpy(dtype=float)).all()
    secondary_numeric_ok = frame["secondary_cosine_similarity"].notna().all() and np.isfinite(frame["secondary_cosine_similarity"].to_numpy(dtype=float)).all()
    group_sizes = frame.groupby(["query_id", "lane", "feature_model_id"], dropna=False).size() if len(frame) else pd.Series(dtype=int)
    checks = [
        ("exact_columns", list(frame.columns) == list(CASE_NEIGHBOR_COLUMNS), f"columns={len(frame.columns)}"),
        ("schema_version", frame["schema_version"].eq(NEIGHBOR_SCHEMA_VERSION).all(), NEIGHBOR_SCHEMA_VERSION),
        ("record_id_unique", not frame["neighbor_record_id"].duplicated().any(), f"rows={len(frame)}"),
        ("no_self", frame["query_candidate_id"].ne(frame["neighbor_candidate_id"]).all(), "candidate IDs differ"),
        ("no_same_case", ~frame["same_case"].map(_as_bool).any() and frame["query_case_id"].ne(frame["neighbor_case_id"]).all(), "same case excluded"),
        ("no_same_painting", ~frame["same_painting"].map(_as_bool).any() and frame["query_painting_id"].ne(frame["neighbor_painting_id"]).all(), "same painting excluded"),
        ("finite_similarity", numeric_ok, f"rows={len(frame)}"),
        ("finite_secondary_similarity", secondary_numeric_ok, f"rows={len(frame)}"),
        ("separate_feature_views", frame["feature_model_id"].ne(frame["secondary_feature_model_id"]).all(), "primary and secondary IDs differ"),
        ("valid_lanes", set(frame["lane"].dropna()) <= {"lower_risk", "flagged"}, str(sorted(set(frame["lane"].dropna())))),
    ]
    if require_complete:
        checks.extend([
            ("neighbor_rows", len(frame) == int(expected["neighbor_rows"]), f"expected={expected['neighbor_rows']}; observed={len(frame)}"),
            ("query_count", frame["query_id"].nunique() == int(expected["retrieval_queries"]), f"observed={frame['query_id'].nunique()}"),
            ("lane_group_sizes", len(group_sizes) > 0 and group_sizes.eq(int(expected["neighbors_per_lane"])).all(), f"groups={len(group_sizes)}"),
        ])
    return pd.DataFrame(checks, columns=["check_id", "passed", "details"])


def validate_panel_directories(
    counterfactual_dir: str | Path,
    retrieval_dir: str | Path,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Validate exact owned PNG panel counts and reject temporary files."""

    expected = _settings(config)["expected_counts"]
    cf = sorted(Path(counterfactual_dir).glob("*.png"))
    retrieval = sorted(Path(retrieval_dir).glob("*.png"))
    roots = [Path(counterfactual_dir), Path(retrieval_dir)]
    temporary = [path for root in roots if root.exists() for path in root.rglob("*") if path.is_file() and (path.suffix.lower() in {".tmp", ".temp"} or path.name.startswith("."))]
    return pd.DataFrame([
        {"check_id": "counterfactual_panel_count", "passed": len(cf) == int(expected["counterfactual_panels"]), "details": f"expected={expected['counterfactual_panels']}; observed={len(cf)}"},
        {"check_id": "retrieval_panel_count", "passed": len(retrieval) == int(expected["retrieval_panels"]), "details": f"expected={expected['retrieval_panels']}; observed={len(retrieval)}"},
        {"check_id": "no_temporary_files", "passed": not temporary, "details": str([str(path) for path in temporary[:5]])},
    ])


def validate_explanation_report_html(html: str, *, config: Mapping[str, Any]) -> pd.DataFrame:
    """Validate the approved mock-bound, self-contained report contract."""

    report = _settings(config)["report"]
    section_ids = list(report["required_section_ids"])
    positions = [html.find(f'id="{section_id}"') if f'id="{section_id}"' in html else html.find(f"id='{section_id}'") for section_id in section_ids]
    image_sources = re.findall(r"<img[^>]+src=[\"']([^\"']+)[\"']", html, flags=re.I)
    embedded = [source for source in image_sources if source.startswith("data:image/")]
    external = [source for source in image_sources if not source.startswith("data:image/")]
    checks = [
        ("report_nonempty", len(html.encode("utf-8")) > 1000, f"bytes={len(html.encode('utf-8'))}"),
        ("report_title", report["title"] in html and report["subtitle"] in html, "title and subtitle"),
        ("required_sections", all(position >= 0 for position in positions), f"required={len(section_ids)}"),
        ("section_order", positions == sorted(positions), "approved mock order"),
        ("embedded_images", len(embedded) >= int(report["minimum_embedded_images"]), f"embedded={len(embedded)}"),
        ("no_external_images", len(external) == int(report["external_image_dependency_count"]), f"external={external[:5]}"),
        ("analytical_views", len(re.findall(r"data-analytical-view=", html)) >= int(report["minimum_embedded_analytical_views"]), f"observed={len(re.findall(r'data-analytical-view=', html))}"),
        ("counterfactual_panels", len(re.findall(r"data-counterfactual-panel=", html)) >= int(report["counterfactual_panel_count"]), f"observed={len(re.findall(r'data-counterfactual-panel=', html))}"),
        ("retrieval_panels", len(re.findall(r"data-retrieval-panel=", html)) >= int(report["retrieval_panel_count"]), f"observed={len(re.findall(r'data-retrieval-panel=', html))}"),
        ("complete_catalog_declared", "1,785" in html and "complete catalog" in html.lower(), "full catalog must be described"),
        ("no_file_uri", "file://" not in html.lower(), "file URI prohibited"),
    ]
    return pd.DataFrame(checks, columns=["check_id", "passed", "details"])


def atomic_write_csv(
    frame: pd.DataFrame,
    output_path: str | Path,
    *,
    attempts: int = 5,
    retry_seconds: float = 0.2,
) -> Path:
    """Persist a CSV using a unique temporary file and Windows-safe retries."""

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.{time.time_ns()}.tmp")
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
