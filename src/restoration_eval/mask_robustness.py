"""Deterministic matched mask-robustness generation and validation."""

from __future__ import annotations

import hashlib
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml
from PIL import Image

from .damage import DEFAULT_FILL_COLOR, apply_mask_damage
from .damage_sensitivity import scale_mask_to_target_area, target_pixels_from_percentage
from .manifests import sha256_file
from .masks import calculate_mask_morphology, generate_mask_by_type
from .paths import find_project_root, require_notebook_output_path, resolve_repo_path, to_repo_relative
from .schemas import (
    CANONICAL_MASKS_SCHEMA,
    DAMAGE_SIZE_CASES_SCHEMA,
    MASK_ROBUSTNESS_CASES_COLUMNS,
    MASK_ROBUSTNESS_CASES_SCHEMA,
    MASK_ROBUSTNESS_GENERATION_AUDIT_COLUMNS,
    MASK_ROBUSTNESS_GENERATION_AUDIT_SCHEMA,
    PREPROCESSED_IMAGES_SCHEMA,
    validate_dataframe,
)


MASK_ROBUSTNESS_MODULE_VERSION = "3.0.0"
MASK_ROBUSTNESS_CONFIG_SCHEMA_VERSION = "mask_robustness_config.v1"
GENERATOR_NAME = "mask_robustness_generator"
GENERATOR_VERSION = MASK_ROBUSTNESS_MODULE_VERSION
SUPPORTED_ROBUSTNESS_FAMILIES = ("scratch_thin", "loss_small", "loss_large")


@dataclass(frozen=True)
class MaskRobustnessGenerationResult:
    cases: pd.DataFrame
    generation_evidence: pd.DataFrame
    removed_stale_paths: tuple[str, ...]
    preview_masks: Mapping[str, Image.Image]
    preview_damaged: Mapping[str, Image.Image]


@dataclass(frozen=True)
class MaskRobustnessValidationResult:
    audit: pd.DataFrame
    summary: Mapping[str, int]
    orphan_paths: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not any(int(value) for value in self.summary.values())


def _mapping(parent: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"Mask-robustness configuration key {key!r} must be a mapping")
    return value


def _relative(value: Any) -> bool:
    text = str(value).strip()
    return bool(text) and not Path(text).is_absolute() and "\\" not in text


def _fill(values: Sequence[Any]) -> tuple[int, int, int]:
    if isinstance(values, (str, bytes)) or len(values) != 3:
        raise ValueError("fill_color_rgb must contain exactly three channels")
    result = tuple(int(value) for value in values)
    if any(value < 0 or value > 255 for value in result):
        raise ValueError("fill_color_rgb values must lie from 0 through 255")
    return result


def validate_mask_robustness_config(config: Mapping[str, Any]) -> list[str]:
    """Return all violations of the approved Notebook 06 contract."""
    errors: list[str] = []
    if config.get("config_schema_version") != MASK_ROBUSTNESS_CONFIG_SCHEMA_VERSION:
        errors.append(f"config_schema_version must equal {MASK_ROBUSTNESS_CONFIG_SCHEMA_VERSION}")
    try:
        dataset = _mapping(config, "dataset")
        inputs = _mapping(config, "inputs")
        output = _mapping(config, "output")
        cohort = _mapping(config, "cohort")
        generator = _mapping(config, "generator")
        distinctness = _mapping(config, "distinctness")
        expected = _mapping(config, "expected")
        smoke = _mapping(config, "smoke")
        examples = _mapping(config, "examples")
    except ValueError as exc:
        return errors + [str(exc)]
    schema_values = {
        "geometry_schema_version": PREPROCESSED_IMAGES_SCHEMA.version,
        "canonical_mask_schema_version": CANONICAL_MASKS_SCHEMA.version,
        "matched_policy_schema_version": DAMAGE_SIZE_CASES_SCHEMA.version,
        "output_schema_version": MASK_ROBUSTNESS_CASES_SCHEMA.version,
        "audit_schema_version": MASK_ROBUSTNESS_GENERATION_AUDIT_SCHEMA.version,
    }
    for key, value in schema_values.items():
        if dataset.get(key) != value:
            errors.append(f"dataset.{key} must equal {value}")
    for key in ("dataset_id", "dataset_version", "dataset_scope", "execution_profile", "experiment_id"):
        if not str(dataset.get(key, "")).strip():
            errors.append(f"dataset.{key} must be non-empty")
    input_paths = (
        "geometry_path", "clean_images_path", "preprocessing_artifacts_path",
        "preprocessing_run_manifest_path", "masks_path", "canonical_mask_config_path",
        "masks_artifacts_path", "masks_run_manifest_path", "matched_policy_cases_path",
        "matched_policy_artifacts_path", "matched_policy_run_manifest_path",
    )
    for key in input_paths:
        if not _relative(inputs.get(key, "")):
            errors.append(f"inputs.{key} must be a normalized repository-relative path")
    output_values = {
        "notebook_stem": "06_mask_robustness_dataset_generation",
        "cases_path": "data/cases.csv", "mask_directory": "images/masks",
        "damaged_directory": "images/damaged",
        "image_path_template": "{robustness_group_id}/{variant_id}.png",
        "audit_path": "metrics/generation_audit.csv",
        "examples_figure_path": "figures/robustness_examples.png",
    }
    for key, value in output_values.items():
        if output.get(key) != value:
            errors.append(f"output.{key} must equal {value!r}")
    paintings = cohort.get("paintings") if isinstance(cohort.get("paintings"), list) else []
    ids = [str(item.get("painting_id", "")) for item in paintings if isinstance(item, Mapping)]
    categories = [str(item.get("category", "")) for item in paintings if isinstance(item, Mapping)]
    if ids != ["p001", "p018", "p026", "p039", "p043"]:
        errors.append("cohort painting identifiers differ from the approved Notebook 05 cohort")
    if len(set(categories)) != 5 or any(not value for value in categories):
        errors.append("cohort must contain five unique non-empty categories")
    families = config.get("families") if isinstance(config.get("families"), list) else []
    names = [str(item.get("mask_type", "")) for item in families if isinstance(item, Mapping)]
    percentages = [float(item.get("target_percentage_content", -1)) for item in families if isinstance(item, Mapping)]
    tokens = [str(item.get("target_token", "")) for item in families if isinstance(item, Mapping)]
    if tuple(names) != SUPPORTED_ROBUSTNESS_FAMILIES:
        errors.append(f"family order must equal {SUPPORTED_ROBUSTNESS_FAMILIES}")
    if percentages != [2.0, 4.5, 12.5]:
        errors.append("family target percentages must equal [2.0, 4.5, 12.5]")
    if tokens != ["target_02pct", "target_04p5pct", "target_12p5pct"]:
        errors.append("family target tokens differ from the approved identifiers")
    required_generator = {
        "name": GENERATOR_NAME, "version": GENERATOR_VERSION,
        "seed_scheme_version": "mask_robustness_seed.v1", "variants_per_group": 5,
        "target_pixel_rounding": "round_half_up",
        "area_addition_strategy": "nearest_unmasked_content_by_euclidean_distance",
        "fill_strategy": "constant_rgb",
        "mask_mode": "L", "damaged_mode": "RGB", "output_format": "PNG",
        "output_extension": ".png", "overwrite_existing": True,
        "stale_file_action": "remove",
    }
    for key, value in required_generator.items():
        if generator.get(key) != value:
            errors.append(f"generator.{key} must equal {value!r}")
    try:
        if _fill(generator.get("fill_color_rgb", [])) != DEFAULT_FILL_COLOR:
            errors.append(f"generator.fill_color_rgb must equal {DEFAULT_FILL_COLOR}")
    except (TypeError, ValueError) as exc:
        errors.append(str(exc))
    for key in ("global_seed", "maximum_generation_attempts_per_variant", "maximum_scale_iterations", "progress_interval_cases", "target_width", "target_height"):
        if not isinstance(generator.get(key), int) or int(generator[key]) <= 0:
            errors.append(f"generator.{key} must be a positive integer")
    maximum_iou = distinctness.get("maximum_pairwise_iou_exclusive")
    if not isinstance(maximum_iou, (int, float)) or not 0 < float(maximum_iou) < 1:
        errors.append("distinctness maximum pairwise IoU must lie in (0, 1)")
    if distinctness.get("require_unique_pixel_sha256_within_group") is not True:
        errors.append("distinctness requires unique pixel checksums")
    count_values = {
        "painting_count": 5, "category_count": 5, "family_count": 3,
        "robustness_group_count": 15, "variants_per_group": 5, "case_count": 75,
        "audit_row_count": 75, "mask_file_count": 75, "damaged_file_count": 75,
        "artifact_record_count": 6, "total_output_file_count": 156,
    }
    for key, value in count_values.items():
        if expected.get(key) != value:
            errors.append(f"expected.{key} must equal {value}")
    if smoke.get("painting_id") != "p039" or smoke.get("mask_type") != "loss_small" or smoke.get("persist_outputs") is not False:
        errors.append("smoke contract must use non-persisted p039/loss_small")
    if examples.get("painting_id") != "p039" or examples.get("mask_types") != list(SUPPORTED_ROBUSTNESS_FAMILIES):
        errors.append("examples contract must use p039 and all three families")
    return errors


def load_mask_robustness_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError("Mask-robustness configuration must load as a mapping")
    config = dict(payload)
    errors = validate_mask_robustness_config(config)
    if errors:
        raise ValueError("Invalid mask-robustness configuration: " + "; ".join(errors))
    return config


def load_canonical_mask_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError("Canonical mask configuration must load as a mapping")
    return dict(payload)


def resolve_mask_robustness_inputs(config: Mapping[str, Any], project_root: str | Path | None = None, *, must_exist: bool = True) -> dict[str, Path]:
    errors = validate_mask_robustness_config(config)
    if errors:
        raise ValueError("Invalid mask-robustness configuration: " + "; ".join(errors))
    root = find_project_root(project_root)
    return {key: resolve_repo_path(value, root, must_exist=must_exist) for key, value in config["inputs"].items() if key.endswith("_path")}


def cohort_painting_ids(config: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(item["painting_id"]) for item in config["cohort"]["paintings"])


def configured_families(config: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    return tuple(dict(item) for item in config["families"])


def validate_mask_robustness_handoff(preprocessed: pd.DataFrame, canonical_masks: pd.DataFrame, matched_policy_cases: pd.DataFrame, config: Mapping[str, Any], canonical_mask_config: Mapping[str, Any], project_root: str | Path | None = None, *, verify_files: bool = True) -> list[str]:
    """Validate Notebook 02/03 schemas and Notebook 05 cohort inheritance."""
    errors = ["configuration: " + value for value in validate_mask_robustness_config(config)]
    for label, frame, schema in (
        ("preprocessed", preprocessed, PREPROCESSED_IMAGES_SCHEMA),
        ("canonical masks", canonical_masks, CANONICAL_MASKS_SCHEMA),
        ("matched policy", matched_policy_cases, DAMAGE_SIZE_CASES_SCHEMA),
    ):
        result = validate_dataframe(frame, schema, allow_extra_columns=False)
        if not result.passed or result.unexpected_columns:
            errors.append(f"{label} schema violation: {result.to_dict()}")
    if errors:
        return errors
    dataset = config["dataset"]
    for key in ("dataset_id", "dataset_version", "dataset_scope"):
        wanted = {str(dataset[key])}
        for label, frame in (("preprocessed", preprocessed), ("canonical masks", canonical_masks), ("matched policy", matched_policy_cases)):
            if set(frame[key].astype(str)) != wanted:
                errors.append(f"{label} {key} does not match configuration")
    ids = set(cohort_painting_ids(config))
    if len(preprocessed) != 50 or preprocessed["painting_id"].duplicated().any():
        errors.append("preprocessed handoff must contain 50 unique paintings")
    if len(canonical_masks) != 250:
        errors.append("canonical mask handoff must contain 250 rows")
    if len(matched_policy_cases) != 35 or set(matched_policy_cases["painting_id"].astype(str)) != ids:
        errors.append("Notebook 05 must contain 35 cases for the exact pinned cohort")
    selected = canonical_masks.loc[canonical_masks["painting_id"].astype(str).isin(ids) & canonical_masks["mask_type"].astype(str).isin(SUPPORTED_ROBUSTNESS_FAMILIES)]
    if len(selected) != 15 or selected.duplicated(["painting_id", "mask_type"]).any():
        errors.append("Notebook 03 must contain one canonical reference per pinned painting/family")
    canonical_families = canonical_mask_config.get("families", {})
    for family in configured_families(config):
        name = family["mask_type"]
        if name not in canonical_families or not math.isclose(100 * float(canonical_families[name]["target_damaged_content_fraction"]), float(family["target_percentage_content"]), abs_tol=1e-12):
            errors.append(f"canonical target percentage differs for {name}")
    geometry = preprocessed.loc[preprocessed["painting_id"].astype(str).isin(ids)]
    if len(geometry) != 5 or not geometry["status"].astype(str).eq("passed").all():
        errors.append("Notebook 02 pinned cohort is incomplete or failed")
    if verify_files:
        root = find_project_root(project_root)
        for value in geometry["processed_path"].astype(str):
            try:
                resolve_repo_path(value, root, must_exist=True)
            except (FileNotFoundError, ValueError) as exc:
                errors.append(f"processed_path verification failed: {exc}")
                break
    return errors


def select_robustness_cohort(preprocessed: pd.DataFrame, matched_policy_cases: pd.DataFrame, config: Mapping[str, Any]) -> pd.DataFrame:
    ids = cohort_painting_ids(config)
    if set(matched_policy_cases["painting_id"].astype(str)) != set(ids):
        raise ValueError("Notebook 05 cases do not contain the exact pinned cohort")
    categories = {str(item["painting_id"]): str(item["category"]) for item in config["cohort"]["paintings"]}
    order = {painting_id: index for index, painting_id in enumerate(ids)}
    columns = ("painting_id", "processed_image_id", "processed_path", "sha256", "width", "height", "content_x_min", "content_y_min", "content_x_max", "content_y_max", "content_width", "content_height", "content_area_pixels", "dataset_sort_index")
    result = preprocessed.loc[preprocessed["painting_id"].astype(str).isin(ids), list(columns)].copy()
    if len(result) != 5 or result["painting_id"].duplicated().any():
        raise ValueError("Notebook 02 does not contain one row per pinned painting")
    result["category"] = result["painting_id"].astype(str).map(categories)
    result["_order"] = result["painting_id"].astype(str).map(order)
    return result.sort_values("_order").drop(columns="_order").rename(columns={"sha256": "clean_image_sha256"}).reset_index(drop=True)


def stable_case_seed(*parts: object, modulus: int = 2**32 - 1) -> int:
    digest = hashlib.sha256("||".join(str(part) for part in parts).encode()).digest()
    return int.from_bytes(digest[:8], "big") % modulus


def robustness_group_id(painting_id: str, mask_type: str, target_token: str) -> str:
    return f"robustness__{painting_id}__{mask_type}__{target_token}"


def _pixel_sha(mask: np.ndarray) -> str:
    return hashlib.sha256((np.asarray(mask) > 0).astype(np.uint8).tobytes()).hexdigest()


def _centroid(mask: np.ndarray, box: Sequence[int]) -> dict[str, Any]:
    ys, xs = np.nonzero(mask)
    if not len(xs):
        raise ValueError("Robustness masks cannot be empty")
    left, top, right, bottom = map(int, box)
    x, y = float(xs.mean()), float(ys.mean())
    nx, ny = (x - left) / max(1, right - left - 1), (y - top) / max(1, bottom - top - 1)
    return {"centroid_x_pixels": x, "centroid_y_pixels": y, "centroid_x_normalized_content": nx, "centroid_y_normalized_content": ny, "centroid_quadrant": f"{'top' if ny < .5 else 'bottom'}_{'left' if nx < .5 else 'right'}"}


def _iou(first: np.ndarray, second: np.ndarray) -> float:
    union = np.logical_or(first, second).sum()
    return float(np.logical_and(first, second).sum() / union) if union else 1.0


def _signature(record: Mapping[str, Any], fields: Sequence[str]) -> tuple[Any, ...]:
    return tuple(round(float(record[field]), 6) for field in fields)


def _candidate_family_shape_passed(
    mask_type: str,
    candidate: Mapping[str, Any],
    canonical_mask_config: Mapping[str, Any],
) -> bool:
    """Reject only per-case shapes whose canonical rule is individually meaningful."""
    if mask_type != "scratch_thin":
        return True
    rules = canonical_mask_config["family_validation"]["scratch_thin"]
    return bool(
        float(candidate["bbox_fill_ratio"])
        <= float(rules["maximum_median_bbox_fill_ratio"])
        and float(candidate["maximum_component_aspect_ratio"])
        >= float(rules["minimum_median_maximum_component_aspect_ratio"])
    )


def _group_stats(records: Sequence[Mapping[str, Any]], arrays: Sequence[np.ndarray], config: Mapping[str, Any], canonical: Mapping[str, Any]) -> dict[str, Any]:
    pair_iou, pair_distance, nearest = [], [], {}
    diagonal = math.hypot(float(records[0]["content_width"]), float(records[0]["content_height"]))
    for left in range(len(records)):
        for right in range(left + 1, len(records)):
            value = _iou(arrays[left], arrays[right]); pair_iou.append(value)
            lid, rid = str(records[left]["variant_id"]), str(records[right]["variant_id"])
            if lid not in nearest or value > nearest[lid][1]: nearest[lid] = (rid, value)
            if rid not in nearest or value > nearest[rid][1]: nearest[rid] = (lid, value)
            pair_distance.append(math.hypot(float(records[left]["centroid_x_pixels"]) - float(records[right]["centroid_x_pixels"]), float(records[left]["centroid_y_pixels"]) - float(records[right]["centroid_y_pixels"])) / diagonal)
    rules = config["distinctness"]
    unique_count = len({str(record["mask_pixel_sha256"]) for record in records})
    morphology_count = len({_signature(record, rules["morphology_signature_fields"]) for record in records})
    component_count = len({_signature(record, rules["component_arrangement_signature_fields"]) for record in records})
    frame, mask_type = pd.DataFrame(records), str(records[0]["mask_type"])
    family_rules = canonical["family_validation"][mask_type]
    if mask_type == "scratch_thin":
        family_pass = float(frame["bbox_fill_ratio"].median()) <= float(family_rules["maximum_median_bbox_fill_ratio"]) and float(frame["maximum_component_aspect_ratio"].median()) >= float(family_rules["minimum_median_maximum_component_aspect_ratio"])
    elif mask_type == "loss_small":
        family_pass = float(frame["connected_component_count"].median()) >= float(family_rules["minimum_median_connected_component_count"])
    else:
        family_pass = float(frame["largest_component_fraction"].median()) >= float(family_rules["minimum_median_largest_component_fraction"])
    result = {
        "group_variant_count": len(records), "group_unique_pixel_sha256_count": unique_count,
        "group_unique_mask_count_passed": unique_count == len(records),
        "maximum_pairwise_iou": max(pair_iou), "minimum_pairwise_iou": min(pair_iou),
        "minimum_pairwise_centroid_distance_fraction": min(pair_distance),
        "group_centroid_span_fraction_of_content_diagonal": max(pair_distance),
        "group_morphology_signature_count": morphology_count,
        "group_component_arrangement_signature_count": component_count,
        "pairwise_iou_passed": max(pair_iou) < float(rules["maximum_pairwise_iou_exclusive"]),
        "location_variation_passed": max(pair_distance) >= float(rules["minimum_centroid_span_fraction_of_content_diagonal"]),
        "morphology_variation_passed": morphology_count >= int(rules["minimum_morphology_signature_count"]),
        "component_arrangement_variation_passed": component_count >= int(rules["minimum_component_arrangement_signature_count"]),
        "family_morphology_passed": bool(family_pass), "nearest": nearest,
    }
    result["group_gate_passed"] = all(bool(result[key]) for key in ("group_unique_mask_count_passed", "pairwise_iou_passed", "location_variation_passed", "morphology_variation_passed", "component_arrangement_variation_passed", "family_morphology_passed"))
    return result


def _output_path(output_root: Path, key: str, group_id: str, variant_id: str, config: Mapping[str, Any], root: Path) -> Path:
    relative = config["output"]["image_path_template"].format(robustness_group_id=group_id, variant_id=variant_id)
    return require_notebook_output_path(output_root / config["output"][key] / relative, config["output"]["notebook_stem"], root)


def _save(image: Image.Image, path: Path, config: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_suffix(".png.tmp")
    image.save(temporary, format="PNG", compress_level=int(config["generator"]["png_compress_level"]), optimize=bool(config["generator"]["png_optimize"])); os.replace(temporary, path)


def generate_mask_robustness_dataset(cohort: pd.DataFrame, config: Mapping[str, Any], canonical_mask_config: Mapping[str, Any], output_root: str | Path, project_root: str | Path | None = None, *, persist: bool = True, retain_images: bool = False, progress_interval: int | None = None) -> MaskRobustnessGenerationResult:
    """Generate deterministic variants while enforcing group distinctness.

    When ``progress_interval`` is omitted, the generator uses the configured
    ``generator.progress_interval_cases`` value.  This keeps notebook calls
    concise while ensuring long generations always expose progress.
    """
    errors = validate_mask_robustness_config(config)
    if errors: raise ValueError("Invalid mask-robustness configuration: " + "; ".join(errors))
    root = find_project_root(project_root); owned = require_notebook_output_path(output_root, config["output"]["notebook_stem"], root)
    generator, rules = config["generator"], config["distinctness"]
    fill_color, expected_paths = _fill(generator["fill_color_rgb"]), set()
    records_all, evidence_all, previews_m, previews_d = [], [], {}, {}
    completed_cases = 0
    total_cases = len(cohort) * len(configured_families(config)) * int(generator["variants_per_group"])
    progress_started = time.perf_counter()
    effective_progress_interval = int(
        generator["progress_interval_cases"]
        if progress_interval is None
        else progress_interval
    )
    if effective_progress_interval <= 0:
        raise ValueError("progress_interval must be positive")
    for row in cohort.itertuples(index=False):
        clean_path = resolve_repo_path(row.processed_path, root, must_exist=True)
        with Image.open(clean_path) as opened: clean = opened.convert("RGB"); clean.load()
        box = (int(row.content_x_min), int(row.content_y_min), int(row.content_x_max), int(row.content_y_max))
        painting_seed = stable_case_seed(generator["seed_scheme_version"], generator["global_seed"], row.painting_id)
        for family in configured_families(config):
            mask_type, token = str(family["mask_type"]), str(family["target_token"])
            group_id = robustness_group_id(str(row.painting_id), mask_type, token); group_seed = stable_case_seed(painting_seed, group_id)
            target_pixels = target_pixels_from_percentage(int(row.content_area_pixels), float(family["target_percentage_content"]))
            records, arrays = [], []
            for index in range(1, 6):
                variant_id, variant_seed = f"variant_{index:02d}", stable_case_seed(group_seed, index)
                selected = None
                for attempt in range(1, int(generator["maximum_generation_attempts_per_variant"]) + 1):
                    generation_seed = stable_case_seed(variant_seed, attempt)
                    raw = generate_mask_by_type(mask_type, np.random.default_rng(generation_seed), int(generator["target_width"]), box, parameters=canonical_mask_config["families"][mask_type]["generator"], morphology_settings=canonical_mask_config["morphology"])
                    raw_array = np.asarray(raw, dtype=np.uint8) > 0
                    scaled = scale_mask_to_target_area(
                        raw_array,
                        target_pixels,
                        box,
                        int(generator["maximum_scale_iterations"]),
                        case_seed=generation_seed,
                        addition_strategy=str(generator["area_addition_strategy"]),
                    )
                    array = scaled["mask"].astype(bool); morphology = calculate_mask_morphology(array, content_box=box); location = _centroid(array, box); candidate = {**morphology, **location}
                    unique = _pixel_sha(array) not in {record["mask_pixel_sha256"] for record in records}
                    iou_ok = all(_iou(array, previous) < float(rules["maximum_pairwise_iou_exclusive"]) for previous in arrays)
                    family_shape_ok = _candidate_family_shape_passed(
                        mask_type,
                        candidate,
                        canonical_mask_config,
                    )
                    if unique and iou_ok and family_shape_ok: selected = (array, scaled, candidate, attempt, generation_seed, int(raw_array.sum())); break
                if selected is None: raise RuntimeError(f"Could not generate distinct {group_id}/{variant_id}")
                array, scaled, morphology, attempt, generation_seed, raw_pixels = selected
                mask_image = Image.fromarray((array * 255).astype(np.uint8), mode="L"); damaged = apply_mask_damage(clean, mask_image, fill_color)
                case_id = f"mask_robustness__{row.painting_id}__{mask_type}__{token}__{variant_id}"
                mask_path = _output_path(owned, "mask_directory", group_id, variant_id, config, root); damaged_path = _output_path(owned, "damaged_directory", group_id, variant_id, config, root)
                expected_paths.update({mask_path.resolve(), damaged_path.resolve()})
                if persist: _save(mask_image, mask_path, config); _save(damaged, damaged_path, config)
                realized = float(morphology["damaged_content_fraction"])
                record = {
                    "dataset_id": config["dataset"]["dataset_id"], "dataset_version": config["dataset"]["dataset_version"], "dataset_scope": config["dataset"]["dataset_scope"], "experiment_id": config["dataset"]["experiment_id"],
                    "case_id": case_id, "robustness_group_id": group_id, "variant_id": variant_id, "variant_index": index, "painting_id": str(row.painting_id), "category": str(row.category), "processed_image_id": str(row.processed_image_id), "mask_id": f"mask__{case_id}", "mask_type": mask_type, "family_index": int(family["family_index"]), "target_token": token, "damaged_image_id": f"damaged__{case_id}",
                    "clean_image_path": to_repo_relative(clean_path, root), "mask_path": to_repo_relative(mask_path, root), "damaged_image_path": to_repo_relative(damaged_path, root), "target_damage_fraction": float(family["target_percentage_content"]) / 100, "target_damage_pixels": target_pixels, "realized_damage_fraction": realized, "realized_damage_pixels": int(morphology["damaged_content_pixel_count"]), "absolute_percentage_point_error": abs(100 * realized - float(family["target_percentage_content"])), "raw_mask_pixels": raw_pixels, "scale_factor": float(scaled["scale_factor"]), "pre_correction_pixels": int(scaled["pre_correction_pixels"]), "correction_added_pixels": int(scaled["correction_added_pixels"]), "correction_removed_pixels": int(scaled["correction_removed_pixels"]),
                    "content_x_min": box[0], "content_y_min": box[1], "content_x_max": box[2], "content_y_max": box[3], "content_width": int(row.content_width), "content_height": int(row.content_height), "content_area_pixels": int(row.content_area_pixels), **morphology,
                    "seed_scheme_version": generator["seed_scheme_version"], "global_seed": int(generator["global_seed"]), "painting_seed": painting_seed, "group_seed": group_seed, "variant_seed": variant_seed, "generation_seed": generation_seed, "generation_attempt": attempt, "fill_strategy": generator["fill_strategy"], "fill_color_r": fill_color[0], "fill_color_g": fill_color[1], "fill_color_b": fill_color[2], "clean_image_sha256": str(row.clean_image_sha256), "mask_pixel_sha256": _pixel_sha(array), "mask_sha256": sha256_file(mask_path) if persist else "not_persisted", "damaged_image_sha256": sha256_file(damaged_path) if persist else "not_persisted", "width": clean.width, "height": clean.height, "mask_mode": "L", "damaged_mode": "RGB", "format": "PNG", "mask_size_bytes": mask_path.stat().st_size if persist else 0, "damaged_size_bytes": damaged_path.stat().st_size if persist else 0, "generator_name": GENERATOR_NAME, "generator_version": GENERATOR_VERSION, "config_schema_version": config["config_schema_version"], "config_version": config["config_version"], "source_manifest_path": config["inputs"]["matched_policy_run_manifest_path"], "generation_status": "passed", "status": "passed", "issue": "",
                }
                records.append(record); arrays.append(array)
                if retain_images: previews_m[case_id] = mask_image.copy(); previews_d[case_id] = damaged.copy()
                completed_cases += 1
                if (
                    completed_cases % effective_progress_interval == 0
                    or completed_cases == total_cases
                ):
                    elapsed = time.perf_counter() - progress_started
                    rate = completed_cases / elapsed if elapsed > 0 else 0.0
                    print(
                        "[mask-robustness] "
                        f"{completed_cases}/{total_cases} cases "
                        f"({100.0 * completed_cases / total_cases:.1f}%) | "
                        f"elapsed={elapsed:.1f}s | rate={rate:.2f} cases/s | "
                        f"latest={group_id}/{variant_id}",
                        flush=True,
                    )
            stats = _group_stats(records, arrays, config, canonical_mask_config)
            if not stats["group_gate_passed"]: raise RuntimeError(f"Robustness group gate failed for {group_id}: {stats}")
            for record in records:
                records_all.append(record); evidence_all.append({"case_id": record["case_id"], "robustness_group_id": group_id, "variant_id": record["variant_id"], **{key: value for key, value in stats.items() if key != "nearest"}, "nearest_variant_id": stats["nearest"][record["variant_id"]][0]})
    removed = []
    if persist:
        for directory_key in ("mask_directory", "damaged_directory"):
            directory = owned / config["output"][directory_key]
            if directory.exists():
                for path in directory.rglob("*.png"):
                    if path.resolve() not in expected_paths: path.unlink(); removed.append(to_repo_relative(path, root))
    cases = pd.DataFrame(records_all).loc[:, MASK_ROBUSTNESS_CASES_COLUMNS].sort_values(["painting_id", "family_index", "variant_index"]).reset_index(drop=True)
    if persist:
        schema = validate_dataframe(cases, MASK_ROBUSTNESS_CASES_SCHEMA, allow_extra_columns=False)
        if not schema.passed: raise RuntimeError(f"Generated cases violate schema: {schema.to_dict()}")
    return MaskRobustnessGenerationResult(cases, pd.DataFrame(evidence_all), tuple(sorted(removed)), previews_m, previews_d)


def validate_saved_mask_robustness_dataset(cases: pd.DataFrame, config: Mapping[str, Any], canonical_mask_config: Mapping[str, Any], output_root: str | Path, project_root: str | Path | None = None) -> MaskRobustnessValidationResult:
    """Reload all saved images and build the one canonical generation audit."""
    root = find_project_root(project_root); owned = require_notebook_output_path(output_root, config["output"]["notebook_stem"], root); fill = np.asarray(_fill(config["generator"]["fill_color_rgb"]), dtype=np.uint8)
    rows, group_arrays, group_records, expected_paths = [], {}, {}, set()
    for record in cases.to_dict("records"):
        clean_path, mask_path, damaged_path = (resolve_repo_path(record[key], root, must_exist=False) for key in ("clean_image_path", "mask_path", "damaged_image_path"))
        expected_mask = _output_path(owned, "mask_directory", record["robustness_group_id"], record["variant_id"], config, root); expected_damaged = _output_path(owned, "damaged_directory", record["robustness_group_id"], record["variant_id"], config, root); expected_paths.update({expected_mask.resolve(), expected_damaged.resolve()})
        exists = (clean_path.is_file(), mask_path.is_file(), damaged_path.is_file()); issue = []
        if all(exists):
            with Image.open(clean_path) as image: clean = image.convert("RGB"); clean.load()
            with Image.open(mask_path) as image: mask = image.convert("L"); mask.load()
            with Image.open(damaged_path) as image: damaged = image.convert("RGB"); damaged.load()
            values = sorted(np.unique(np.asarray(mask)).astype(int).tolist()); array = np.asarray(mask) == 255; box = tuple(int(record[key]) for key in ("content_x_min", "content_y_min", "content_x_max", "content_y_max")); morphology = calculate_mask_morphology(array, content_box=box); location = _centroid(array, box); changed = np.any(np.asarray(clean) != np.asarray(damaged), axis=2)
            checks = {"reload_passed": True, "dimensions_match": clean.size == mask.size == damaged.size, "binary_values_valid": set(values).issubset({0, 255}), "content_only_valid": morphology["padding_overlap_pixels"] == 0, "metadata_mask_pixels_match": int(array.sum()) == int(record["realized_damage_pixels"]), "outside_mask_changed_pixel_count": int((changed & ~array).sum()), "inside_mask_not_fill_pixel_count": int((np.any(np.asarray(damaged) != fill, axis=2) & array).sum()), "clean_sha256_matches": sha256_file(clean_path) == record["clean_image_sha256"], "mask_pixel_sha256_matches": _pixel_sha(array) == record["mask_pixel_sha256"], "mask_sha256_matches": sha256_file(mask_path) == record["mask_sha256"], "damaged_sha256_matches": sha256_file(damaged_path) == record["damaged_image_sha256"]}
        else:
            array = np.zeros((int(record["height"]), int(record["width"])), bool); morphology = {key: record.get(key) for key in ("bbox_width", "bbox_height", "bbox_fill_ratio", "bbox_aspect_ratio", "connected_component_count", "largest_component_fraction", "component_area_cv", "maximum_component_aspect_ratio", "mask_perimeter_pixels", "mask_compactness", "touches_content_boundary", "minimum_distance_to_content_boundary_pixels")}; location = {key: record.get(key) for key in ("centroid_x_pixels", "centroid_y_pixels", "centroid_x_normalized_content", "centroid_y_normalized_content", "centroid_quadrant")}; values = []; checks = {key: False for key in ("reload_passed", "dimensions_match", "binary_values_valid", "content_only_valid", "metadata_mask_pixels_match", "clean_sha256_matches", "mask_pixel_sha256_matches", "mask_sha256_matches", "damaged_sha256_matches")}; checks.update({"outside_mask_changed_pixel_count": -1, "inside_mask_not_fill_pixel_count": -1})
        realized = float(morphology.get("damaged_content_fraction", record["realized_damage_fraction"])); area_error = abs(100 * realized - 100 * float(record["target_damage_fraction"])); area_pass = area_error <= float(config["generator"]["maximum_absolute_percentage_point_error"]) and checks["metadata_mask_pixels_match"]
        row = {"dataset_id": record["dataset_id"], "dataset_version": record["dataset_version"], "dataset_scope": record["dataset_scope"], "experiment_id": record["experiment_id"], "case_id": record["case_id"], "robustness_group_id": record["robustness_group_id"], "variant_id": record["variant_id"], "painting_id": record["painting_id"], "mask_type": record["mask_type"], "target_damage_fraction": record["target_damage_fraction"], "target_damage_pixels": record["target_damage_pixels"], "realized_damage_fraction": realized, "realized_damage_pixels": int(array.sum()), "absolute_percentage_point_error": area_error, "area_within_tolerance": area_pass, **location, **morphology, "clean_file_exists": exists[0], "mask_file_exists": exists[1], "damaged_file_exists": exists[2], "mask_unique_values": "|".join(map(str, values)), **checks, "output_contract_valid": mask_path.resolve() == expected_mask.resolve() and damaged_path.resolve() == expected_damaged.resolve(), "_array": array, "_issue": issue, "content_width": record["content_width"], "content_height": record["content_height"], "mask_pixel_sha256": _pixel_sha(array)}
        rows.append(row); group_arrays.setdefault(record["robustness_group_id"], []).append(array); group_records.setdefault(record["robustness_group_id"], []).append(row)
    stats = {group: _group_stats(records, group_arrays[group], config, canonical_mask_config) for group, records in group_records.items()}
    audit_rows = []
    for row in rows:
        group = stats[row["robustness_group_id"]]; failures = [key for key, value in row.items() if key.endswith("_passed") or key.endswith("_valid") or key.endswith("_matches") if isinstance(value, (bool, np.bool_)) and not value]
        if row["outside_mask_changed_pixel_count"] != 0: failures.append("outside_mask_changed")
        if row["inside_mask_not_fill_pixel_count"] != 0: failures.append("inside_mask_not_fill")
        if not group["group_gate_passed"]: failures.append("group_gate")
        combined = {**row, **{key: value for key, value in group.items() if key != "nearest"}, "nearest_variant_id": group["nearest"].get(row["variant_id"], ("unavailable",))[0], "validation_status": "failed" if failures else "passed", "issue": " | ".join(failures)}
        audit_rows.append({key: combined[key] for key in MASK_ROBUSTNESS_GENERATION_AUDIT_COLUMNS})
    audit = pd.DataFrame(audit_rows).sort_values(["robustness_group_id", "variant_id"]).reset_index(drop=True)
    actual = set()
    for key in ("mask_directory", "damaged_directory"):
        directory = owned / config["output"][key]
        if directory.exists(): actual.update(path.resolve() for path in directory.rglob("*.png"))
    orphan = tuple(to_repo_relative(path, root) for path in sorted(actual - expected_paths))
    summary = {"duplicate_case_id_count": int(cases.duplicated("case_id", keep=False).sum()), "duplicate_group_variant_count": int(cases.duplicated(["robustness_group_id", "variant_id"], keep=False).sum()), "duplicate_output_path_count": int(cases.duplicated("mask_path", keep=False).sum() + cases.duplicated("damaged_image_path", keep=False).sum()), "missing_output_count": int((~audit[["clean_file_exists", "mask_file_exists", "damaged_file_exists"]]).sum().sum()), "orphan_output_count": len(orphan), "failed_case_count": int(audit["validation_status"].ne("passed").sum()), "failed_group_count": int(audit.loc[~audit["group_gate_passed"], "robustness_group_id"].nunique())}
    return MaskRobustnessValidationResult(audit, summary, orphan)


def write_dataframe_atomic(dataframe: pd.DataFrame, path: str | Path) -> Path:
    destination = Path(path); destination.parent.mkdir(parents=True, exist_ok=True); temporary = destination.with_suffix(destination.suffix + f".{os.getpid()}.{time.time_ns()}.tmp")
    dataframe.to_csv(temporary, index=False, lineterminator="\n"); os.replace(temporary, destination); return destination
