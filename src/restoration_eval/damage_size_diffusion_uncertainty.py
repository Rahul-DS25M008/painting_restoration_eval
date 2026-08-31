"""Post-freeze damage-size repeated-seed uncertainty extension.

This module is owned by Notebook 22.  It references the validated Notebook 11
seed-2026 candidates, plans only seeds 2027--2029, and never writes into a
Notebook 01--21 output root.  Existing Stable Diffusion and uncertainty helpers
remain unchanged and are reused only through their public contracts.
"""

from __future__ import annotations

import copy
import hashlib
import os
import time
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml
from PIL import Image

from .diffusion_uncertainty import (
    DIFFUSION_UNCERTAINTY_COLUMNS,
    GROUP_METADATA_COLUMNS,
    make_uncertainty_metric_id,
)
from .manifests import sha256_file
from .restoration_stable_diffusion import (
    STABLE_DIFFUSION_CANDIDATE_COLUMNS,
    STABLE_DIFFUSION_CANDIDATES_SCHEMA,
)
from .schemas import validate_dataframe


MODULE_VERSION = "1.0.0"
CONFIG_SCHEMA_VERSION = "damage_size_diffusion_uncertainty_extension_config.v1"
METRIC_VERSION = "damage_size_empirical_seed_uncertainty.v1"
METRICS_SCHEMA_VERSION = "damage_size_diffusion_uncertainty.v1"
MAP_MANIFEST_SCHEMA_VERSION = "damage_size_uncertainty_map_images.v1"

PIXEL_REGION_IDS = (
    "full_image", "content_region", "masked_region", "mask_bbox_crop",
    "boundary_ring", "outside_mask_content",
)
LEARNED_REGION_IDS = ("content_region", "mask_bbox_crop")
GROUP_KEY_COLUMNS = (
    "case_id", "prompt_policy_id", "prompt_variant_id", "configuration_id",
)

MAP_IMAGE_COLUMNS = (
    "map_image_id", "uncertainty_group_id", "case_id", "painting_id",
    "target_damage_fraction", "realized_damage_fraction", "map_metric_name",
    "raw_map_key", "relative_path", "sha256", "size_bytes", "width",
    "height", "image_mode", "format", "renderer_version", "status", "issue",
)

REFERENCE_FAMILIES = (
    "classical_reference", "perceptual_reference", "feature_reference",
    "spatial_reference", "local_consistency_reference", "semantic_reference",
)
UNCERTAINTY_FAMILIES = (
    "pixel_variability", "pixel_pairwise", "perceptual_pairwise",
    "feature_pairwise",
)


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    settings = config.get("damage_size_diffusion_uncertainty_extension", config)
    if not isinstance(settings, Mapping):
        raise TypeError("Notebook 22 settings must be a mapping")
    return settings


def _as_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    return series.fillna("").astype(str).str.strip().str.lower().isin(
        {"true", "1", "yes"}
    )


def _resolve(project_root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(project_root) / path


def _repo_owned_path(owner_root: str | Path, relative_path: str | Path) -> str:
    path = Path(relative_path)
    if path.is_absolute():
        return path.as_posix()
    return (Path(owner_root) / path).as_posix()


def _compact_hash(prefix: str, values: Sequence[Any], length: int = 20) -> str:
    payload = "|".join(str(value) for value in values)
    return prefix + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def load_damage_size_uncertainty_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the Notebook 22 extension contract."""

    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Notebook 22 configuration must be a mapping")
    if payload.get("config_schema_version") != CONFIG_SCHEMA_VERSION:
        raise ValueError("Unsupported Notebook 22 configuration schema")
    settings = payload.get("damage_size_diffusion_uncertainty_extension")
    if not isinstance(settings, dict):
        raise ValueError("Configuration is missing extension settings")
    required = {
        "inputs", "output", "frozen_boundary", "population",
        "generation_contract", "regions", "metrics", "reference_evidence",
        "execution", "expected_counts", "evidence_policy", "known_limitations",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"Notebook 22 configuration is missing keys: {missing}")

    population = settings["population"]
    expected = settings["expected_counts"]
    seeds = tuple(int(seed) for seed in population["expected_seeds"])
    generated = tuple(int(seed) for seed in population["generated_seeds"])
    anchor = int(settings["frozen_boundary"]["anchor_seed"])
    if seeds != (2026, 2027, 2028, 2029):
        raise ValueError("Expected seeds must remain exactly 2026--2029")
    if generated != tuple(seed for seed in seeds if seed != anchor):
        raise ValueError("Generated seeds must be the three non-anchor seeds")
    if tuple(population["group_keys"]) != GROUP_KEY_COLUMNS:
        raise ValueError(f"group_keys must be exactly {GROUP_KEY_COLUMNS}")
    if tuple(settings["regions"]["pixel_regions"]) != PIXEL_REGION_IDS:
        raise ValueError(f"pixel_regions must be exactly {PIXEL_REGION_IDS}")
    if tuple(settings["regions"]["learned_metric_regions"]) != LEARNED_REGION_IDS:
        raise ValueError(f"learned_metric_regions must be exactly {LEARNED_REGION_IDS}")
    if bool(settings["metrics"]["combined_index"]["retained"]):
        raise ValueError("Notebook 22 must not retain a combined uncertainty index")
    if bool(settings["frozen_boundary"]["may_write_frozen_outputs"]):
        raise ValueError("Notebook 22 may not write frozen outputs")
    if bool(settings["frozen_boundary"]["copy_anchor_images"]):
        raise ValueError("Frozen anchor images must be referenced, not copied")

    cases = int(expected["cases"])
    groups = int(expected["uncertainty_groups"])
    pairs = int(expected["unordered_candidate_pairs"])
    if cases != 35 or groups != cases:
        raise ValueError("Notebook 22 must contain exactly 35 cases/groups")
    if int(expected["new_candidates"]) != cases * len(generated):
        raise ValueError("New-candidate arithmetic is inconsistent")
    if int(expected["total_candidates"]) != cases * len(seeds):
        raise ValueError("Total-candidate arithmetic is inconsistent")
    if pairs != cases * 6:
        raise ValueError("Unordered-pair arithmetic is inconsistent")
    specifications = settings["reference_evidence"]["specifications"]
    if len(specifications) != int(expected["reference_specifications"]):
        raise ValueError("Reference-specification count is inconsistent")
    aliases = [str(item["alias"]) for item in specifications]
    if len(aliases) != len(set(aliases)):
        raise ValueError("Reference aliases must be unique")
    for key in (
        "progress_interval_candidates", "checkpoint_interval_candidates",
        "progress_interval_groups", "checkpoint_interval_groups",
        "progress_interval_embeddings", "checkpoint_interval_embeddings",
        "atomic_replace_attempts",
    ):
        if int(settings["execution"][key]) <= 0:
            raise ValueError(f"{key} must be positive")
    return payload


def build_effective_generation_config(
    base_config: Mapping[str, Any], extension_config: Mapping[str, Any],
) -> dict[str, Any]:
    """Adapt the frozen base model contract for Notebook 22-owned execution."""

    result = copy.deepcopy(dict(base_config))
    settings = _settings(extension_config)
    generation = settings["generation_contract"]
    population = settings["population"]
    output = settings["output"]
    model = result["model"]
    model_keys = (
        "hf_model_id", "model_revision", "scheduler", "num_inference_steps",
        "guidance_scale", "strength", "precision", "requested_device",
        "allow_cpu_fallback", "inference_width", "inference_height",
        "output_width", "output_height", "compositing_policy",
        "safety_checker_policy", "maximum_retries", "retry_seed_policy",
    )
    for key in model_keys:
        model[key] = generation[key]
    model["mask_threshold_policy"]["binary_missing_region"]["threshold"] = int(
        generation["mask_threshold"]
    )
    result["prompt_policy"]["policy_id"] = population["prompt_policy_id"]
    result["prompt_policy"]["primary_variant_id"] = population["prompt_variant_id"]
    result["prompt_policy"]["generic_prompt"] = generation["prompt"]
    result["prompt_policy"]["negative_prompt"] = generation["negative_prompt"]
    result["output"]["notebook_stem"] = settings["notebook_stem"]
    result["output"]["restored_directory"] = output["restored_directory"]
    result["execution"].update({
        "progress_interval_candidates": int(settings["execution"]["progress_interval_candidates"]),
        "checkpoint_interval_candidates": int(settings["execution"]["checkpoint_interval_candidates"]),
        "compute_checksums": bool(settings["execution"]["compute_checksums"]),
        "resume_enabled": bool(settings["execution"]["resume_enabled"]),
        "overwrite_existing": bool(settings["execution"]["overwrite_existing"]),
        "stale_file_action": settings["execution"]["stale_file_action"],
        "png_compress_level": int(settings["execution"]["png_compress_level"]),
    })
    return result


def select_frozen_damage_size_anchors(
    damage_size_cases: pd.DataFrame,
    stable_diffusion_candidates: pd.DataFrame,
    *,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
    verify_files: bool = False,
) -> pd.DataFrame:
    """Select and validate the exact 35 read-only Notebook 11 anchors."""

    settings = _settings(config)
    population = settings["population"]
    boundary = settings["frozen_boundary"]
    expected = settings["expected_counts"]
    required_cases = {
        "case_id", "painting_id", "experiment_id", "target_damage_fraction",
        "realized_damage_fraction", "status",
    }
    required_candidates = set(STABLE_DIFFUSION_CANDIDATE_COLUMNS)
    missing_cases = sorted(required_cases - set(damage_size_cases.columns))
    missing_candidates = sorted(required_candidates - set(stable_diffusion_candidates.columns))
    if missing_cases or missing_candidates:
        raise ValueError(
            f"Missing case columns={missing_cases}; candidate columns={missing_candidates}"
        )

    cases = damage_size_cases.loc[
        damage_size_cases["experiment_id"].astype(str).eq(population["experiment_id"])
        & damage_size_cases["status"].astype(str).isin({"completed", "passed"})
    ].copy()
    selected = stable_diffusion_candidates.loc[
        stable_diffusion_candidates["experiment_id"].astype(str).eq(population["experiment_id"])
        & stable_diffusion_candidates["model_id"].astype(str).eq(population["model_id"])
        & stable_diffusion_candidates["prompt_policy_id"].astype(str).eq(population["prompt_policy_id"])
        & stable_diffusion_candidates["prompt_variant_id"].astype(str).eq(population["prompt_variant_id"])
        & pd.to_numeric(stable_diffusion_candidates["seed"], errors="coerce").eq(
            int(boundary["anchor_seed"])
        )
        & stable_diffusion_candidates["execution_role"].astype(str).eq(
            boundary["anchor_execution_role"]
        )
        & stable_diffusion_candidates["status"].astype(str).eq(boundary["anchor_status"])
        & _as_bool(stable_diffusion_candidates["is_primary_candidate"])
    ].copy()

    if len(cases) != int(expected["cases"]):
        raise ValueError(f"Expected 35 damage-size cases, observed {len(cases)}")
    if len(selected) != int(expected["frozen_anchor_candidates"]):
        raise ValueError(f"Expected 35 frozen anchors, observed {len(selected)}")
    if cases["case_id"].duplicated().any() or selected["case_id"].duplicated().any():
        raise ValueError("Damage-size cases and anchors must be unique by case_id")
    case_ids = set(cases["case_id"].astype(str))
    anchor_ids = set(selected["case_id"].astype(str))
    if case_ids != anchor_ids:
        raise ValueError(
            f"Anchor/case mismatch: missing={sorted(case_ids-anchor_ids)}, "
            f"unexpected={sorted(anchor_ids-case_ids)}"
        )
    levels = sorted(pd.to_numeric(cases["target_damage_fraction"], errors="raise").unique())
    declared_levels = sorted(float(value) for value in population["target_damage_fractions"])
    if not np.allclose(levels, declared_levels, rtol=0.0, atol=1e-9):
        raise ValueError(f"Damage levels differ: {levels} != {declared_levels}")
    per_painting = cases.groupby("painting_id")["case_id"].size()
    if len(per_painting) != int(expected["paintings"]) or not per_painting.eq(
        int(expected["damage_levels_per_painting"])
    ).all():
        raise ValueError("Expected five paintings with seven damage levels each")

    generation = settings["generation_contract"]
    exact_fields = {
        "hf_model_id": generation["hf_model_id"],
        "model_revision": generation["model_revision"],
        "configuration_id": population["configuration_id"],
        "prompt": generation["prompt"],
        "negative_prompt": generation["negative_prompt"],
        "scheduler": generation["scheduler"],
        "precision": generation["precision"],
        "compositing_policy": generation["compositing_policy"],
        "safety_checker_policy": generation["safety_checker_policy"],
    }
    for column, value in exact_fields.items():
        if not selected[column].astype(str).eq(str(value)).all():
            raise ValueError(f"Frozen anchors disagree on {column}")
    numeric_fields = {
        "num_inference_steps": generation["num_inference_steps"],
        "guidance_scale": generation["guidance_scale"],
        "strength": generation["strength"],
        "inference_width": generation["inference_width"],
        "inference_height": generation["inference_height"],
        "output_width": generation["output_width"],
        "output_height": generation["output_height"],
        "mask_threshold": generation["mask_threshold"],
    }
    for column, value in numeric_fields.items():
        observed = pd.to_numeric(selected[column], errors="raise").to_numpy(float)
        if not np.allclose(observed, float(value), rtol=0.0, atol=1e-9):
            raise ValueError(f"Frozen anchors disagree on {column}")
    if selected["configuration_fingerprint"].astype(str).nunique() != 1:
        raise ValueError("Frozen anchors do not share one configuration fingerprint")

    if verify_files:
        if project_root is None:
            raise ValueError("project_root is required when verify_files=True")
        owner_root = settings["frozen_boundary"]["anchor_output_root"]
        for row in selected.itertuples(index=False):
            path = _resolve(project_root, _repo_owned_path(owner_root, row.restored_path))
            if not path.is_file():
                raise FileNotFoundError(path)
            if sha256_file(path) != str(row.restored_sha256):
                raise ValueError(f"Frozen anchor checksum mismatch: {row.candidate_id}")

    return selected.sort_values(["painting_id", "case_id"], kind="stable").reset_index(drop=True)


def extension_candidate_id(case_id: str, seed: int) -> str:
    """Return an extension-owned deterministic candidate identifier."""

    return _compact_hash("sd15dsu__", ("notebook_22", case_id, "p00_generic", int(seed)), 16)


def build_extension_candidate_plan(
    frozen_anchors: pd.DataFrame, *, config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build exactly 105 schema-compatible candidates without copying anchors."""

    settings = _settings(config)
    population = settings["population"]
    output = settings["output"]
    generation = settings["generation_contract"]
    expected = settings["expected_counts"]
    rows: list[dict[str, Any]] = []
    for anchor in frozen_anchors.sort_values(["painting_id", "case_id"], kind="stable").itertuples(index=False):
        base = anchor._asdict()
        for candidate_index, seed in enumerate(population["generated_seeds"]):
            candidate_id = extension_candidate_id(str(anchor.case_id), int(seed))
            relative = Path(output["restored_directory"]) / output["restored_path_template"].format(
                case_id=anchor.case_id, candidate_id=candidate_id,
            )
            record = {column: base.get(column, "") for column in STABLE_DIFFUSION_CANDIDATE_COLUMNS}
            record.update({
                "candidate_id": candidate_id,
                "candidate_index": candidate_index,
                "seed": int(seed),
                "execution_role": population["extension_execution_role"],
                "is_primary_candidate": False,
                "is_prompt_ablation_candidate": False,
                "is_uncertainty_candidate": True,
                "candidate_selection_policy": population["selection_policy"],
                "execution_action": "pending",
                "restored_path": relative.as_posix(),
                "restored_sha256": "",
                "runtime_seconds": np.nan,
                "gpu_memory_before_bytes": np.nan,
                "gpu_memory_after_bytes": np.nan,
                "gpu_peak_memory_bytes": np.nan,
                "retry_count": 0,
                "attempt_count": 0,
                "started_at_utc": "",
                "completed_at_utc": "",
                "status": "planned",
                "issue": "",
                "mask_threshold": int(generation["mask_threshold"]),
            })
            rows.append(record)
    plan = pd.DataFrame(rows, columns=STABLE_DIFFUSION_CANDIDATE_COLUMNS)
    validation = validate_extension_candidate_plan(plan, config=config, require_completed=False)
    if not validation["passed"]:
        raise ValueError(f"Invalid extension plan: {validation}")
    if len(plan) != int(expected["new_candidates"]):
        raise ValueError("Extension plan row count changed after validation")
    return plan


def validate_extension_candidate_plan(
    candidates: pd.DataFrame, *, config: Mapping[str, Any], require_completed: bool,
) -> dict[str, Any]:
    """Validate planned or completed Notebook 22-owned candidate rows."""

    settings = _settings(config)
    population = settings["population"]
    expected = settings["expected_counts"]
    schema = validate_dataframe(
        candidates.loc[:, STABLE_DIFFUSION_CANDIDATE_COLUMNS],
        STABLE_DIFFUSION_CANDIDATES_SCHEMA,
    ) if set(STABLE_DIFFUSION_CANDIDATE_COLUMNS).issubset(candidates.columns) else None
    seeds = set(pd.to_numeric(candidates.get("seed", pd.Series(dtype=float)), errors="coerce").dropna().astype(int))
    status_ok = (
        candidates["status"].astype(str).eq("completed").all()
        if require_completed and "status" in candidates
        else candidates.get("status", pd.Series(dtype=str)).astype(str).isin({"planned", "completed"}).all()
    )
    output_prefix = str(Path(settings["output"]["restored_directory"]).as_posix()) + "/"
    paths_ok = bool(
        "restored_path" in candidates
        and candidates["restored_path"].astype(str).str.replace("\\", "/", regex=False).str.startswith(output_prefix).all()
    )
    passed = bool(
        schema is not None and schema.passed
        and len(candidates) == int(expected["new_candidates"])
        and candidates["candidate_id"].astype(str).is_unique
        and candidates["case_id"].astype(str).nunique() == int(expected["cases"])
        and seeds == set(int(value) for value in population["generated_seeds"])
        and candidates.groupby("case_id")["seed"].nunique().eq(3).all()
        and candidates["execution_role"].astype(str).eq(population["extension_execution_role"]).all()
        and _as_bool(candidates["is_uncertainty_candidate"]).all()
        and not _as_bool(candidates["is_primary_candidate"]).any()
        and status_ok and paths_ok
    )
    return {
        "schema": None if schema is None else schema.to_dict(),
        "row_count": int(len(candidates)),
        "case_count": int(candidates["case_id"].nunique()) if "case_id" in candidates else 0,
        "seeds": sorted(seeds),
        "status_ok": bool(status_ok),
        "paths_owned_by_notebook_22": paths_ok,
        "passed": passed,
    }


def build_complete_uncertainty_worklist(
    frozen_anchors: pd.DataFrame,
    extension_candidates: pd.DataFrame,
    damage_size_cases: pd.DataFrame,
    geometry: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Construct a 140-row in-memory worklist with explicit path ownership."""

    settings = _settings(config)
    expected = settings["expected_counts"]
    boundary = settings["frozen_boundary"]
    output = settings["output"]
    case_lookup = damage_size_cases.set_index("case_id", drop=False)
    geometry_lookup = geometry.set_index("painting_id", drop=False)
    records: list[dict[str, Any]] = []
    for owner, owner_id, owner_root, frame in (
        ("frozen_reference", "11", boundary["anchor_output_root"], frozen_anchors),
        ("extension_owned", "22", output["root"], extension_candidates),
    ):
        for candidate in frame.itertuples(index=False):
            case_id = str(candidate.case_id)
            painting_id = str(candidate.painting_id)
            if case_id not in case_lookup.index or painting_id not in geometry_lookup.index:
                raise ValueError(f"Missing case/geometry metadata for {candidate.candidate_id}")
            case = case_lookup.loc[case_id]
            geo = geometry_lookup.loc[painting_id]
            if isinstance(case, pd.DataFrame) or isinstance(geo, pd.DataFrame):
                raise ValueError("Case and geometry lookup keys must be unique")
            record = candidate._asdict()
            record.pop("category", None)
            record.update({
                "dataset_id": str(case.dataset_id),
                "dataset_scope": str(case.dataset_scope),
                "target_damage_fraction": float(case.target_damage_fraction),
                "realized_damage_fraction": float(case.realized_damage_fraction),
                "content_x_min": int(geo.content_x_min),
                "content_y_min": int(geo.content_y_min),
                "content_x_max": int(geo.content_x_max),
                "content_y_max": int(geo.content_y_max),
                "is_zero_control": False,
                "technical_validation_passed": str(candidate.status) == "completed",
                "source_owner": owner,
                "source_owner_notebook_id": owner_id,
                "source_table_id": (
                    "notebook_11_stable_diffusion" if owner_id == "11"
                    else "notebook_22_damage_size_uncertainty_extension"
                ),
                "restored_path": _repo_owned_path(owner_root, candidate.restored_path),
            })
            records.append(record)
    result = pd.DataFrame(records)
    result["seed"] = pd.to_numeric(result["seed"], errors="raise").astype(int)
    if len(result) != int(expected["total_candidates"]):
        raise ValueError(f"Expected 140 combined candidates, observed {len(result)}")
    if result["candidate_id"].astype(str).duplicated().any():
        raise ValueError("Combined worklist repeats candidate_id")
    coverage = result.groupby("case_id")["seed"].apply(lambda values: tuple(sorted(values)))
    expected_seeds = tuple(int(value) for value in settings["population"]["expected_seeds"])
    if not coverage.map(lambda values: values == expected_seeds).all():
        raise ValueError("Combined worklist does not have exact four-seed coverage")
    return result.sort_values(["painting_id", "case_id", "seed"], kind="stable").reset_index(drop=True)


def build_uncertainty_adapter_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Return the minimal Notebook 18-compatible computation contract."""

    settings = _settings(config)
    expected = settings["expected_counts"]
    return {
        "diffusion_uncertainty": {
            "population": {
                "eligible_model_id": settings["population"]["model_id"],
                "eligible_status": "completed",
                "expected_seeds": list(settings["population"]["expected_seeds"]),
                "group_keys": list(settings["population"]["group_keys"]),
            },
            "regions": {
                "policy_version": settings["regions"]["policy_version"],
                "mask_bbox_margin_pixels": int(settings["regions"]["mask_bbox_margin_pixels"]),
                "boundary_width_pixels": int(settings["regions"]["boundary_width_pixels"]),
                "pixel_regions": list(settings["regions"]["pixel_regions"]),
                "learned_metric_regions": list(settings["regions"]["learned_metric_regions"]),
            },
            "metrics": copy.deepcopy(settings["metrics"]),
            "execution": {
                "progress_interval_groups": int(settings["execution"]["progress_interval_groups"]),
                "checkpoint_interval_groups": int(settings["execution"]["checkpoint_interval_groups"]),
                "lpips_batch_size": int(settings["execution"]["lpips_batch_size"]),
                "atomic_replace_attempts": int(settings["execution"]["atomic_replace_attempts"]),
                "atomic_replace_retry_seconds": float(settings["execution"]["atomic_replace_retry_seconds"]),
            },
            "expected_counts": {
                "uncertainty_groups": int(expected["uncertainty_groups"]),
                "unique_cases": int(expected["cases"]),
                "candidates": int(expected["total_candidates"]),
                "pixel_group_summary_rows": int(expected["pixel_group_summary_rows"]),
                "pixel_pair_rows": int(expected["pixel_pair_rows"]),
                "lpips_pair_rows": int(expected["lpips_pair_rows"]),
                "feature_pair_rows": int(expected["feature_pair_rows"]),
            },
        }
    }


def build_anchor_reference_rows(
    population: pd.DataFrame,
    source_tables: Mapping[str, pd.DataFrame],
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Normalize sixteen frozen seed-2026 evidence values per group."""

    settings = _settings(config)
    anchor_seed = int(settings["frozen_boundary"]["anchor_seed"])
    anchors = population.loc[pd.to_numeric(population["seed"], errors="coerce").eq(anchor_seed)].copy()
    if len(anchors) != int(settings["expected_counts"]["frozen_anchor_candidates"]):
        raise ValueError("Population does not contain exactly 35 anchors")
    records: list[dict[str, Any]] = []
    for specification in settings["reference_evidence"]["specifications"]:
        source_name = str(specification["source"])
        if source_name not in source_tables:
            raise ValueError(f"Missing reference source table: {source_name}")
        frame = source_tables[source_name].copy()
        if "candidate_id" not in frame:
            raise ValueError(f"Reference source {source_name} lacks candidate_id")
        frame = frame.loc[frame["candidate_id"].astype(str).isin(anchors["candidate_id"].astype(str))]
        for column, expected_value in specification.get("filters", {}).items():
            if column not in frame:
                raise ValueError(f"Reference source {source_name} lacks filter column {column}")
            frame = frame.loc[frame[column].astype(str).eq(str(expected_value))]
        if frame["candidate_id"].astype(str).duplicated().any() or len(frame) != len(anchors):
            raise ValueError(
                f"Reference specification {specification['alias']} expected one row per anchor; "
                f"observed {len(frame)}"
            )
        lookup = frame.set_index("candidate_id", drop=False)
        value_column = str(specification["value_column"])
        if value_column not in frame:
            raise ValueError(f"Reference source {source_name} lacks {value_column}")
        for anchor in anchors.itertuples(index=False):
            source = lookup.loc[str(anchor.candidate_id)]
            value = float(source[value_column])
            if not np.isfinite(value):
                raise ValueError(f"Non-finite reference value for {specification['alias']}")
            base = {column: getattr(anchor, column) for column in GROUP_METADATA_COLUMNS}
            alias = str(specification["alias"])
            region_id = str(specification.get("filters", {}).get("region_id", "not_applicable"))
            record = {
                **base,
                "uncertainty_metric_id": make_uncertainty_metric_id(
                    str(anchor.uncertainty_group_id), "seed_reference", alias,
                    region_id, "value", candidate_id=str(anchor.candidate_id),
                    metric_version=METRIC_VERSION,
                ),
                "observation_level": "seed_reference",
                "candidate_id": str(anchor.candidate_id),
                "seed": anchor_seed,
                "candidate_id_a": "",
                "candidate_id_b": "",
                "seed_a": np.nan,
                "seed_b": np.nan,
                "metric_family": str(specification["metric_family"]),
                "metric_name": alias,
                "region_id": region_id,
                "summary_statistic": "value",
                "value": value,
                "value_unit": str(specification["value_unit"]),
                "metric_version": METRIC_VERSION,
                "region_policy_version": settings["regions"]["policy_version"],
                "evidence_role": "frozen_anchor_reference",
                "is_combined_index": False,
                "status": "ok",
                "issue": "",
            }
            records.append({column: record.get(column, "") for column in DIFFUSION_UNCERTAINTY_COLUMNS})
    result = pd.DataFrame(records, columns=DIFFUSION_UNCERTAINTY_COLUMNS)
    expected_rows = int(settings["expected_counts"]["anchor_reference_rows"])
    if len(result) != expected_rows or result["uncertainty_metric_id"].duplicated().any():
        raise ValueError("Anchor reference rows violate the exact contract")
    return result.sort_values(
        ["case_id", "metric_family", "metric_name"], kind="stable"
    ).reset_index(drop=True)


def build_extension_restored_embedding_plan(
    combined_worklist: pd.DataFrame,
    *,
    project_root: str | Path,
    feature_config: Mapping[str, Any],
) -> pd.DataFrame:
    """Plan only Notebook 22 restored embeddings, excluding reusable evidence."""

    from .metrics_feature_similarity import (
        build_feature_embedding_plan,
        build_feature_execution_plan,
    )

    required = {"source_owner", "candidate_id", "restored_path"}
    missing = sorted(required - set(combined_worklist.columns))
    if missing:
        raise ValueError(f"Combined worklist is missing embedding fields: {missing}")
    extension = combined_worklist.loc[
        combined_worklist["source_owner"].astype(str).eq("extension_owned")
    ].copy()
    execution_plan = build_feature_execution_plan(
        extension, project_root=project_root, config=feature_config,
    )
    plan = build_feature_embedding_plan(execution_plan, config=feature_config)
    plan = plan.loc[plan["image_role"].astype(str).eq("restored")].copy()
    array_names = {
        "clip_vit_b32": "clip_extension_embeddings",
        "dinov2_vits14": "dinov2_extension_embeddings",
    }
    plan["array_name"] = plan["feature_model_id"].astype(str).map(array_names)
    if plan["array_name"].isna().any():
        raise ValueError("Extension plan contains an unsupported feature model")
    plan["array_index"] = plan.groupby("feature_model_id", sort=False).cumcount()
    expected_per_model = len(extension) * len(LEARNED_REGION_IDS)
    counts = plan.groupby("feature_model_id").size().to_dict()
    if counts != {
        "clip_vit_b32": expected_per_model,
        "dinov2_vits14": expected_per_model,
    }:
        raise ValueError(f"Unexpected extension embedding counts: {counts}")
    if not plan["representative_candidate_id"].astype(str).isin(
        extension["candidate_id"].astype(str)
    ).all():
        raise ValueError("Extension embedding plan references a non-extension candidate")
    return plan.sort_values(
        ["feature_model_id", "array_index"], kind="stable"
    ).reset_index(drop=True)


def combine_anchor_and_extension_embeddings(
    population: pd.DataFrame,
    frozen_manifest: pd.DataFrame,
    frozen_arrays: Mapping[str, np.ndarray],
    extension_manifests: Sequence[pd.DataFrame],
    extension_arrays: Mapping[str, np.ndarray],
    *,
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    """Combine read-only anchor vectors with extension-owned restored vectors."""

    settings = _settings(config)
    anchor_seed = int(settings["frozen_boundary"]["anchor_seed"])
    anchor_ids = set(
        population.loc[
            pd.to_numeric(population["seed"], errors="coerce").eq(anchor_seed),
            "candidate_id",
        ].astype(str)
    )
    extension_ids = set(population["candidate_id"].astype(str)) - anchor_ids
    required = {
        "feature_model_id", "image_role", "representative_candidate_id",
        "region_id", "array_name", "array_index", "status",
    }
    missing = sorted(required - set(frozen_manifest.columns))
    if missing:
        raise ValueError(f"Frozen embedding manifest is missing columns: {missing}")
    anchors = frozen_manifest.loc[
        frozen_manifest["image_role"].astype(str).eq("restored")
        & frozen_manifest["representative_candidate_id"].astype(str).isin(anchor_ids)
        & frozen_manifest["region_id"].astype(str).isin(LEARNED_REGION_IDS)
        & frozen_manifest["feature_model_id"].astype(str).isin(
            {"clip_vit_b32", "dinov2_vits14"}
        )
        & frozen_manifest["status"].astype(str).eq("ok")
    ].copy()
    extension = pd.concat(list(extension_manifests), ignore_index=True)
    if not extension["representative_candidate_id"].astype(str).isin(extension_ids).all():
        raise ValueError("Extension embeddings include an anchor or unknown candidate")
    if not extension["status"].astype(str).eq("ok").all():
        raise ValueError("Extension embedding extraction contains failures")
    combined = pd.concat([anchors, extension], ignore_index=True, sort=False)
    key_columns = ["representative_candidate_id", "region_id", "feature_model_id"]
    if combined.duplicated(key_columns).any():
        raise ValueError("Combined embedding evidence repeats a candidate/region/model key")
    expected_rows = int(settings["expected_counts"]["total_candidates"]) * 4
    if len(combined) != expected_rows:
        raise ValueError(f"Expected {expected_rows} combined restored embeddings, observed {len(combined)}")
    arrays = {
        **{str(key): np.asarray(value) for key, value in frozen_arrays.items()},
        **{str(key): np.asarray(value) for key, value in extension_arrays.items()},
    }
    referenced_names = set(combined["array_name"].astype(str))
    missing_arrays = sorted(referenced_names - set(arrays))
    if missing_arrays:
        raise ValueError(f"Combined embedding arrays are missing: {missing_arrays}")
    for row in combined.itertuples(index=False):
        matrix = arrays[str(row.array_name)]
        index = int(row.array_index)
        if not (0 <= index < len(matrix)) or not np.isfinite(matrix[index]).all():
            raise ValueError(f"Invalid embedding reference for {row.representative_candidate_id}")
    return combined.reset_index(drop=True), arrays


def validate_extension_metrics(
    metrics: pd.DataFrame, population: pd.DataFrame, *, config: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the extension-owned long-form metric table."""

    settings = _settings(config)
    expected = settings["expected_counts"]
    missing = sorted(set(DIFFUSION_UNCERTAINTY_COLUMNS) - set(metrics.columns))
    values = pd.to_numeric(metrics.get("value", pd.Series(dtype=float)), errors="coerce")
    families = metrics.groupby("metric_family").size().to_dict() if not missing else {}
    specifications = settings["reference_evidence"]["specifications"]
    reference_family_counts: dict[str, int] = {}
    for item in specifications:
        family = str(item["metric_family"])
        reference_family_counts[family] = reference_family_counts.get(family, 0) + int(
            expected["frozen_anchor_candidates"]
        )
    expected_family_counts = {
        "pixel_variability": int(expected["pixel_group_summary_rows"]),
        "pixel_pairwise": int(expected["pixel_pair_rows"]),
        "perceptual_pairwise": int(expected["lpips_pair_rows"]),
        "feature_pairwise": int(expected["feature_pair_rows"]),
        **reference_family_counts,
    }
    family_counts_match = all(
        int(families.get(family, -1)) == count
        for family, count in expected_family_counts.items()
    ) and set(families) == set(expected_family_counts)
    pair_rows = metrics.get("observation_level", pd.Series(dtype=str)).astype(str).eq("candidate_pair")
    pair_order_ok = bool(
        (pd.to_numeric(metrics.loc[pair_rows, "seed_a"], errors="coerce")
         < pd.to_numeric(metrics.loc[pair_rows, "seed_b"], errors="coerce")).all()
    ) if not missing else False
    combined_absent = bool(not _as_bool(metrics["is_combined_index"]).any()) if not missing else False
    allowed_levels = {"group_summary", "candidate_pair", "seed_reference"}
    allowed_roles = {"empirical_uncertainty_proxy", "frozen_anchor_reference"}
    passed = bool(
        not missing
        and len(metrics) == int(expected["total_metric_rows"])
        and metrics["uncertainty_metric_id"].astype(str).is_unique
        and population["uncertainty_group_id"].nunique() == int(expected["uncertainty_groups"])
        and population["candidate_id"].nunique() == int(expected["total_candidates"])
        and values.notna().all() and np.isfinite(values).all()
        and family_counts_match and pair_order_ok and combined_absent
        and set(metrics["observation_level"].astype(str)).issubset(allowed_levels)
        and set(metrics["evidence_role"].astype(str)).issubset(allowed_roles)
        and metrics["status"].astype(str).eq("ok").all()
    )
    return {
        "schema_version": METRICS_SCHEMA_VERSION,
        "missing_columns": missing,
        "row_count": int(len(metrics)),
        "group_count": int(population["uncertainty_group_id"].nunique()),
        "candidate_count": int(population["candidate_id"].nunique()),
        "family_counts": {str(key): int(value) for key, value in families.items()},
        "expected_family_counts": expected_family_counts,
        "family_counts_match": family_counts_match,
        "all_values_finite": bool(values.notna().all() and np.isfinite(values).all()),
        "pair_order_ok": pair_order_ok,
        "combined_index_absent": combined_absent,
        "passed": passed,
    }


def compute_rgb_std_maps(
    population: pd.DataFrame, *, project_root: str | Path,
    progress_callback=print,
) -> dict[str, np.ndarray]:
    """Compute one mean-channel RGB standard-deviation map per group."""

    maps: dict[str, np.ndarray] = {}
    groups = list(population.groupby("uncertainty_group_id", sort=True))
    for number, (group_id, group) in enumerate(groups, start=1):
        arrays = []
        for row in group.sort_values("seed", kind="stable").itertuples(index=False):
            path = _resolve(project_root, row.restored_path)
            if not path.is_file():
                raise FileNotFoundError(path)
            with Image.open(path) as image:
                arrays.append(np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0)
        stack = np.stack(arrays, axis=0)
        maps[str(group_id)] = stack.std(axis=0, ddof=0).mean(axis=2).astype(np.float32)
        if progress_callback is not None and (number % 10 == 0 or number == len(groups)):
            progress_callback(f"RGB uncertainty maps: {number}/{len(groups)} groups")
    return maps


def _atomic_replace(temporary: Path, target: Path, *, attempts: int, delay: float) -> None:
    for attempt in range(1, attempts + 1):
        try:
            os.replace(temporary, target)
            return
        except PermissionError:
            if attempt == attempts:
                raise
            time.sleep(delay * attempt)


def write_uncertainty_map_bundle(
    maps: Mapping[str, np.ndarray], output_path: str | Path, *, config: Mapping[str, Any],
) -> Path:
    """Persist raw maps atomically as one compressed NPZ bundle."""

    settings = _settings(config)
    expected = int(settings["expected_counts"]["raw_uncertainty_maps"])
    if len(maps) != expected:
        raise ValueError(f"Expected {expected} raw maps, observed {len(maps)}")
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("wb") as handle:
            np.savez_compressed(handle, **{
                str(key): np.asarray(value, dtype=np.float32) for key, value in maps.items()
            })
        _atomic_replace(
            temporary, target,
            attempts=int(settings["execution"]["atomic_replace_attempts"]),
            delay=float(settings["execution"]["atomic_replace_retry_seconds"]),
        )
    finally:
        temporary.unlink(missing_ok=True)
    return target


def render_uncertainty_overlays(
    population: pd.DataFrame,
    maps: Mapping[str, np.ndarray],
    *,
    project_root: str | Path,
    output_root: str | Path,
    config: Mapping[str, Any],
    progress_callback=print,
) -> pd.DataFrame:
    """Render one readable damaged/mean/uncertainty panel per group."""

    import matplotlib.pyplot as plt

    settings = _settings(config)
    output = settings["output"]
    records: list[dict[str, Any]] = []
    groups = list(population.groupby("uncertainty_group_id", sort=True))
    for number, (group_id, group) in enumerate(groups, start=1):
        ordered = group.sort_values("seed", kind="stable")
        first = ordered.iloc[0]
        with Image.open(_resolve(project_root, first["input_image_path"])) as image:
            damaged = np.asarray(image.convert("RGB"), dtype=np.uint8)
        restored = []
        for row in ordered.itertuples(index=False):
            with Image.open(_resolve(project_root, row.restored_path)) as image:
                restored.append(np.asarray(image.convert("RGB"), dtype=np.float32))
        mean_restored = np.clip(np.mean(restored, axis=0), 0, 255).astype(np.uint8)
        uncertainty = np.asarray(maps[str(group_id)], dtype=np.float32)
        destination = Path(output_root) / output["uncertainty_image_directory"] / output[
            "uncertainty_image_path_template"
        ].format(uncertainty_group_id=group_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), constrained_layout=True)
        axes[0].imshow(damaged)
        axes[0].set_title("Damaged input")
        axes[1].imshow(mean_restored)
        axes[1].set_title("Mean of four seeds")
        vmax = max(float(np.percentile(uncertainty, 99)), 1e-8)
        image = axes[2].imshow(uncertainty, cmap="magma", vmin=0.0, vmax=vmax)
        axes[2].set_title("Mean-channel RGB seed std")
        fig.colorbar(image, ax=axes[2], fraction=0.046, pad=0.04)
        for axis in axes:
            axis.axis("off")
        fig.suptitle(
            f"{first['painting_id']} · target damage {100 * float(first['target_damage_fraction']):.0f}%",
            fontsize=12,
        )
        fig.savefig(destination, dpi=180, bbox_inches="tight")
        plt.close(fig)
        with Image.open(destination) as rendered:
            width, height = rendered.size
            mode = rendered.mode
            image_format = rendered.format or "PNG"
        relative = destination.relative_to(Path(output_root)).as_posix()
        records.append({
            "map_image_id": _compact_hash("dsm_", (group_id, relative), 20),
            "uncertainty_group_id": str(group_id),
            "case_id": str(first["case_id"]),
            "painting_id": str(first["painting_id"]),
            "target_damage_fraction": float(first["target_damage_fraction"]),
            "realized_damage_fraction": float(first["realized_damage_fraction"]),
            "map_metric_name": "mean_channel_rgb_seed_standard_deviation",
            "raw_map_key": str(group_id),
            "relative_path": relative,
            "sha256": sha256_file(destination),
            "size_bytes": int(destination.stat().st_size),
            "width": int(width),
            "height": int(height),
            "image_mode": str(mode),
            "format": str(image_format),
            "renderer_version": "damage_size_uncertainty_overlay.v1",
            "status": "passed",
            "issue": "",
        })
        if progress_callback is not None and (number % 10 == 0 or number == len(groups)):
            progress_callback(f"Uncertainty overlays: {number}/{len(groups)} groups")
    result = pd.DataFrame(records, columns=MAP_IMAGE_COLUMNS)
    if len(result) != int(settings["expected_counts"]["uncertainty_overlay_images"]):
        raise ValueError("Uncertainty overlay count differs from the contract")
    return result


def render_uncertainty_extension_summary(
    metrics: pd.DataFrame, output_path: str | Path,
) -> Path:
    """Render four painting-trajectory panels without category-effect claims."""

    import matplotlib.pyplot as plt

    selections = (
        ("pixel_rgb_std_mean", "masked_region", "Mean RGB seed std"),
        ("pairwise_rgb_rmse", "masked_region", "Pairwise RGB RMSE"),
        ("pairwise_lpips_distance", "mask_bbox_crop", "Pairwise LPIPS"),
        ("pairwise_dinov2_cosine_distance", "mask_bbox_crop", "Pairwise DINOv2 distance"),
    )
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)
    for axis, (metric_name, region_id, title) in zip(axes.flat, selections):
        selected = metrics.loc[
            metrics["metric_name"].astype(str).eq(metric_name)
            & metrics["region_id"].astype(str).eq(region_id)
        ].copy()
        selected["value"] = pd.to_numeric(selected["value"], errors="raise")
        summary = selected.groupby(
            ["uncertainty_group_id", "painting_id", "target_damage_fraction"], as_index=False
        )["value"].mean()
        for painting_id, group in summary.groupby("painting_id", sort=True):
            ordered = group.sort_values("target_damage_fraction", kind="stable")
            axis.plot(
                100 * ordered["target_damage_fraction"].to_numpy(float),
                ordered["value"].to_numpy(float), marker="o", linewidth=1.5,
                label=str(painting_id),
            )
        axis.set_title(title)
        axis.set_xlabel("Target damaged area (%)")
        axis.set_ylabel("Empirical variability")
        axis.grid(alpha=0.25)
    axes.flat[0].legend(title="Painting", fontsize=8)
    fig.suptitle("Damage-size Stable Diffusion seed variability by painting trajectory")
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return target


def atomic_write_csv(frame: pd.DataFrame, output_path: str | Path, *, config: Mapping[str, Any]) -> Path:
    """Write one CSV using the extension's Windows-safe replace policy."""

    settings = _settings(config)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        frame.to_csv(temporary, index=False)
        _atomic_replace(
            temporary, target,
            attempts=int(settings["execution"]["atomic_replace_attempts"]),
            delay=float(settings["execution"]["atomic_replace_retry_seconds"]),
        )
    finally:
        temporary.unlink(missing_ok=True)
    return target
