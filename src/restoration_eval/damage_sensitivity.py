"""Matched, nested damage-size dataset generation and validation."""

from __future__ import annotations

import hashlib
import math
import os
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml
from PIL import Image
from scipy.ndimage import distance_transform_edt

from .damage import DEFAULT_FILL_COLOR, apply_mask_damage
from .manifests import sha256_file
from .masks import calculate_mask_morphology
from .paths import (
    find_project_root,
    require_notebook_output_path,
    resolve_repo_path,
    to_repo_relative,
)
from .schemas import (
    CANONICAL_MASKS_SCHEMA,
    DAMAGE_SIZE_CASES_COLUMNS,
    DAMAGE_SIZE_CASES_SCHEMA,
    DAMAGE_SIZE_GENERATION_AUDIT_COLUMNS,
    DAMAGE_SIZE_GENERATION_AUDIT_SCHEMA,
    PREPROCESSED_IMAGES_SCHEMA,
    validate_dataframe,
)


DAMAGE_SIZE_MODULE_VERSION = "3.0.0"
DAMAGE_SIZE_CONFIG_SCHEMA_VERSION = "damage_size_sensitivity_config.v1"
GENERATOR_NAME = "damage_size_sensitivity_generator"
GENERATOR_VERSION = DAMAGE_SIZE_MODULE_VERSION
DEFAULT_TARGET_PERCENTAGES = (2.0, 4.0, 6.0, 8.0, 10.0, 15.0, 20.0)
DEFAULT_BASE_MASK_TYPES = ("loss_large",)
FIRST_LEVEL_SENTINEL = ""


@dataclass(frozen=True)
class DamageSizeGenerationResult:
    """Normalized cases plus noncanonical generation and cleanup evidence."""

    cases: pd.DataFrame
    generation_evidence: pd.DataFrame
    removed_stale_paths: tuple[str, ...]


@dataclass(frozen=True)
class DamageSizeValidationResult:
    """Independent per-case audit and owned output reconciliation."""

    audit: pd.DataFrame
    summary: Mapping[str, int]
    orphan_paths: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return all(
            int(self.summary.get(key, 0)) == 0
            for key in (
                "duplicate_case_id_count",
                "duplicate_mask_id_count",
                "duplicate_output_path_count",
                "missing_output_count",
                "orphan_output_count",
                "failed_case_count",
                "area_failure_count",
                "nesting_failure_count",
                "morphology_failure_count",
                "pixel_integrity_failure_count",
                "checksum_failure_count",
                "output_contract_failure_count",
            )
        )


def _require_mapping(parent: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"Damage-size configuration key {key!r} must be a mapping")
    return value


def _normalized_relative_path(value: Any) -> bool:
    text = str(value).strip()
    return bool(text) and not Path(text).is_absolute() and "\\" not in text


def _normalize_fill_color(values: Sequence[Any]) -> tuple[int, int, int]:
    if isinstance(values, (str, bytes)) or len(values) != 3:
        raise ValueError("fill_color_rgb must contain exactly three channels")
    color = tuple(int(value) for value in values)
    if any(value < 0 or value > 255 for value in color):
        raise ValueError("fill_color_rgb values must lie from 0 through 255")
    return color


def validate_damage_size_config(config: Mapping[str, Any]) -> list[str]:
    """Return all violations of the versioned Notebook 05 contract."""
    errors: list[str] = []
    if config.get("config_schema_version") != DAMAGE_SIZE_CONFIG_SCHEMA_VERSION:
        errors.append(
            f"config_schema_version must equal {DAMAGE_SIZE_CONFIG_SCHEMA_VERSION}"
        )
    if not str(config.get("config_version", "")).strip():
        errors.append("config_version must be non-empty")
    try:
        dataset = _require_mapping(config, "dataset")
        inputs = _require_mapping(config, "inputs")
        output = _require_mapping(config, "output")
        cohort = _require_mapping(config, "cohort")
        generator = _require_mapping(config, "generator")
        morphology = _require_mapping(config, "morphology")
        expected = _require_mapping(config, "expected")
        smoke = _require_mapping(config, "smoke")
        examples = _require_mapping(config, "examples")
    except ValueError as exc:
        return errors + [str(exc)]

    for key in (
        "dataset_id",
        "dataset_version",
        "dataset_scope",
        "execution_profile",
        "experiment_id",
    ):
        if not str(dataset.get(key, "")).strip():
            errors.append(f"dataset.{key} must be non-empty")
    schema_contract = {
        "geometry_schema_version": PREPROCESSED_IMAGES_SCHEMA.version,
        "mask_schema_version": CANONICAL_MASKS_SCHEMA.version,
        "output_schema_version": DAMAGE_SIZE_CASES_SCHEMA.version,
        "audit_schema_version": DAMAGE_SIZE_GENERATION_AUDIT_SCHEMA.version,
    }
    for key, expected_value in schema_contract.items():
        if dataset.get(key) != expected_value:
            errors.append(f"dataset.{key} must equal {expected_value}")

    path_keys = (
        "geometry_path",
        "clean_images_path",
        "preprocessing_artifacts_path",
        "preprocessing_run_manifest_path",
        "masks_path",
        "mask_images_path",
        "masks_artifacts_path",
        "masks_run_manifest_path",
    )
    for key in path_keys:
        if not _normalized_relative_path(inputs.get(key, "")):
            errors.append(f"inputs.{key} must be a normalized repository-relative path")
    required_lists = {
        "required_preprocessing_artifact_keys": ["preprocessed_images", "clean_images"],
        "required_mask_artifact_keys": ["canonical_masks", "mask_images"],
        "required_registry_keys": [
            "preprocessing.geometry",
            "preprocessing.clean_images",
            "masks.canonical",
            "masks.canonical_images",
        ],
    }
    for key, expected_value in required_lists.items():
        if inputs.get(key) != expected_value:
            errors.append(f"inputs.{key} must equal {expected_value}")
    if inputs.get("required_upstream_run_status") != "completed":
        errors.append("inputs.required_upstream_run_status must equal completed")

    output_contract = {
        "notebook_stem": "05_damage_size_sensitivity_dataset_generation",
        "cases_path": "data/cases.csv",
        "mask_directory": "images/masks",
        "damaged_directory": "images/damaged",
        "image_path_template": "{painting_id}/{level_id}.png",
        "audit_path": "metrics/generation_audit.csv",
        "progression_figure_path": "figures/damage_size_progression.png",
    }
    for key, expected_value in output_contract.items():
        if output.get(key) != expected_value:
            errors.append(f"output.{key} must equal {expected_value!r}")

    if cohort.get("selection_policy") != "pinned_one_per_controlled_visual_category":
        errors.append("cohort.selection_policy is unsupported")
    if cohort.get("base_mask_type") != "loss_large":
        errors.append("cohort.base_mask_type must equal loss_large")
    paintings = cohort.get("paintings")
    if not isinstance(paintings, list) or not paintings:
        errors.append("cohort.paintings must be a non-empty list")
        paintings = []
    painting_ids: list[str] = []
    categories: list[str] = []
    for index, record in enumerate(paintings):
        if not isinstance(record, Mapping):
            errors.append(f"cohort.paintings[{index}] must be a mapping")
            continue
        painting_id = str(record.get("painting_id", "")).strip()
        category = str(record.get("category", "")).strip()
        if not painting_id or not category:
            errors.append(f"cohort.paintings[{index}] requires painting_id and category")
        painting_ids.append(painting_id)
        categories.append(category)
    if len(set(painting_ids)) != len(painting_ids):
        errors.append("cohort painting identifiers must be unique")
    if len(set(categories)) != len(categories):
        errors.append("cohort categories must be unique")

    levels = config.get("levels")
    if not isinstance(levels, list) or not levels:
        errors.append("levels must be a non-empty list")
        levels = []
    level_ids: list[str] = []
    percentages: list[float] = []
    for index, record in enumerate(levels):
        if not isinstance(record, Mapping):
            errors.append(f"levels[{index}] must be a mapping")
            continue
        level_id = str(record.get("level_id", "")).strip()
        try:
            percentage = float(record.get("target_percentage_content"))
        except (TypeError, ValueError):
            errors.append(f"levels[{index}].target_percentage_content must be numeric")
            continue
        if not level_id or not 0.0 < percentage < 100.0:
            errors.append(f"levels[{index}] has an invalid identifier or percentage")
        level_ids.append(level_id)
        percentages.append(percentage)
    if len(set(level_ids)) != len(level_ids):
        errors.append("level identifiers must be unique")
    if len(set(percentages)) != len(percentages):
        errors.append("target percentages must be unique")
    if percentages != sorted(percentages):
        errors.append("target percentages must be strictly ascending")
    if tuple(percentages) != DEFAULT_TARGET_PERCENTAGES:
        errors.append(f"target percentages must equal {DEFAULT_TARGET_PERCENTAGES}")

    generator_contract = {
        "name": GENERATOR_NAME,
        "version": GENERATOR_VERSION,
        "seed_scheme_version": "damage_size_nested_seed.v1",
        "scaling_method": "isotropic_nearest_neighbor_about_base_centroid",
        "nesting_policy": "strict_previous_level_subset",
        "boundary_correction_policy": "deterministic_radial_boundary_correction",
        "target_pixel_rounding": "round_half_up",
        "fill_strategy": "constant_rgb",
        "mask_background_value": 0,
        "mask_damaged_value": 255,
        "mask_mode": "L",
        "damaged_mode": "RGB",
        "output_format": "PNG",
        "output_extension": ".png",
        "strip_output_metadata": True,
        "overwrite_existing": True,
        "stale_file_action": "remove",
    }
    for key, expected_value in generator_contract.items():
        if generator.get(key) != expected_value:
            errors.append(f"generator.{key} must equal {expected_value!r}")
    try:
        if _normalize_fill_color(generator.get("fill_color_rgb", [])) != DEFAULT_FILL_COLOR:
            errors.append(f"generator.fill_color_rgb must equal {DEFAULT_FILL_COLOR}")
    except (TypeError, ValueError) as exc:
        errors.append(str(exc))
    for key in ("global_seed", "maximum_scale_iterations", "target_width", "target_height"):
        if not isinstance(generator.get(key), int) or int(generator[key]) <= 0:
            errors.append(f"generator.{key} must be a positive integer")
    if generator.get("target_width") != generator.get("target_height"):
        errors.append("generator target dimensions must be square")
    tolerance = generator.get("maximum_absolute_percentage_point_error")
    if not isinstance(tolerance, (int, float)) or not 0.0 < float(tolerance) <= 0.1:
        errors.append("generator maximum area error must lie in (0, 0.1]")
    compression = generator.get("png_compress_level")
    if not isinstance(compression, int) or not 0 <= compression <= 9:
        errors.append("generator.png_compress_level must lie from 0 through 9")
    if not isinstance(generator.get("png_optimize"), bool):
        errors.append("generator.png_optimize must be boolean")

    morphology_contract = {
        "component_connectivity": 8,
        "perimeter_connectivity": 4,
        "compactness_formula": "four_pi_area_over_perimeter_squared",
        "centroid_reference": "content_normalized_xy",
        "require_component_count_preserved": True,
        "require_no_content_boundary_contact": True,
        "require_strict_nesting": True,
    }
    for key, expected_value in morphology_contract.items():
        if morphology.get(key) != expected_value:
            errors.append(f"morphology.{key} must equal {expected_value!r}")
    for key in (
        "maximum_centroid_shift_pixels",
        "maximum_centroid_shift_fraction_of_content_diagonal",
        "maximum_relative_bbox_aspect_ratio_drift",
        "maximum_relative_compactness_drift",
    ):
        if not isinstance(morphology.get(key), (int, float)) or float(morphology[key]) < 0:
            errors.append(f"morphology.{key} must be non-negative")

    painting_count = expected.get("painting_count")
    level_count = expected.get("target_level_count")
    case_count = expected.get("case_count")
    if painting_count != len(painting_ids):
        errors.append("expected.painting_count must match the pinned cohort")
    if expected.get("category_count") != len(set(categories)):
        errors.append("expected.category_count must match unique cohort categories")
    if expected.get("base_mask_type_count") != 1:
        errors.append("expected.base_mask_type_count must equal 1")
    if level_count != len(level_ids):
        errors.append("expected.target_level_count must match levels")
    if case_count != len(painting_ids) * len(level_ids):
        errors.append("expected.case_count must equal painting_count times target_level_count")
    for key in ("audit_row_count", "mask_file_count", "damaged_file_count"):
        if expected.get(key) != case_count:
            errors.append(f"expected.{key} must equal expected.case_count")
    if expected.get("artifact_record_count") != 6:
        errors.append("expected.artifact_record_count must equal 6")
    if expected.get("total_output_file_count") != 76:
        errors.append("expected.total_output_file_count must equal 76")

    if smoke.get("painting_id") != "p039" or smoke.get("target_level_count") != len(level_ids):
        errors.append("smoke contract must use p039 and all configured levels")
    if smoke.get("repeat_count") != 2 or smoke.get("persist_outputs") is not False:
        errors.append("smoke must repeat twice without persisting outputs")
    if examples.get("selection_rule") != (
        "minimum_median_maximum_content_area_within_pinned_cohort"
    ):
        errors.append("examples.selection_rule is unsupported")
    if examples.get("painting_ids") != ["p018", "p039", "p001"]:
        errors.append("examples.painting_ids must equal [p018, p039, p001]")
    if examples.get("columns") != ["clean", *level_ids]:
        errors.append("examples.columns must contain clean followed by all levels")
    if not isinstance(examples.get("figure_dpi"), int) or examples["figure_dpi"] <= 0:
        errors.append("examples.figure_dpi must be a positive integer")
    return errors


def load_damage_size_config(path: str | Path) -> dict[str, Any]:
    """Load and validate the Notebook 05 YAML configuration."""
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Damage-size configuration not found: {config_path}")
    with config_path.open("r", encoding="utf-8-sig") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError("Damage-size configuration must load as a mapping")
    config = dict(payload)
    errors = validate_damage_size_config(config)
    if errors:
        raise ValueError("Invalid damage-size configuration: " + "; ".join(errors))
    return config


def resolve_damage_size_inputs(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
    *,
    must_exist: bool = True,
) -> dict[str, Path]:
    """Resolve the eight explicit Notebook 02/03 input artifacts."""
    errors = validate_damage_size_config(config)
    if errors:
        raise ValueError("Invalid damage-size configuration: " + "; ".join(errors))
    root = find_project_root(project_root)
    keys = (
        "geometry_path",
        "clean_images_path",
        "preprocessing_artifacts_path",
        "preprocessing_run_manifest_path",
        "masks_path",
        "mask_images_path",
        "masks_artifacts_path",
        "masks_run_manifest_path",
    )
    return {
        key: resolve_repo_path(config["inputs"][key], root, must_exist=must_exist)
        for key in keys
    }


def cohort_painting_ids(config: Mapping[str, Any]) -> tuple[str, ...]:
    """Return configured painting identifiers in their approved stable order."""
    return tuple(str(item["painting_id"]) for item in config["cohort"]["paintings"])


def configured_levels(config: Mapping[str, Any]) -> tuple[tuple[str, float], ...]:
    """Return level identifiers and percentage targets in approved order."""
    return tuple(
        (str(item["level_id"]), float(item["target_percentage_content"]))
        for item in config["levels"]
    )


def validate_damage_size_handoff(
    preprocessed: pd.DataFrame,
    masks: pd.DataFrame,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
    *,
    verify_files: bool = True,
) -> list[str]:
    """Validate upstream schemas and the exact pinned loss-large cohort."""
    errors = ["configuration: " + value for value in validate_damage_size_config(config)]
    if errors:
        return errors
    geometry_result = validate_dataframe(
        preprocessed, PREPROCESSED_IMAGES_SCHEMA, allow_extra_columns=False
    )
    mask_result = validate_dataframe(masks, CANONICAL_MASKS_SCHEMA, allow_extra_columns=False)
    if not geometry_result.passed or geometry_result.unexpected_columns:
        errors.append(f"preprocessed schema violation: {geometry_result.to_dict()}")
    if not mask_result.passed or mask_result.unexpected_columns:
        errors.append(f"mask schema violation: {mask_result.to_dict()}")
    if geometry_result.missing_columns or mask_result.missing_columns:
        return errors

    dataset = config["dataset"]
    expected = config["expected"]
    for key in ("dataset_id", "dataset_version", "dataset_scope"):
        wanted = {str(dataset[key])}
        if set(preprocessed[key].astype(str)) != wanted:
            errors.append(f"preprocessed {key} does not match configuration")
        if set(masks[key].astype(str)) != wanted:
            errors.append(f"masks {key} does not match configuration")
    if len(preprocessed) != 50 or preprocessed["painting_id"].duplicated().any():
        errors.append("preprocessed handoff must contain 50 unique paintings")
    if len(masks) != 250:
        errors.append("mask handoff must contain 250 rows")
    if masks["case_id"].duplicated().any() or masks["mask_id"].duplicated().any():
        errors.append("mask handoff contains duplicate case_id or mask_id values")

    ids = cohort_painting_ids(config)
    base_type = str(config["cohort"]["base_mask_type"])
    selected_geometry = preprocessed.loc[preprocessed["painting_id"].astype(str).isin(ids)]
    selected_masks = masks.loc[
        masks["painting_id"].astype(str).isin(ids)
        & masks["mask_type"].astype(str).eq(base_type)
    ]
    if set(selected_geometry["painting_id"].astype(str)) != set(ids):
        errors.append("one or more pinned paintings are missing from Notebook 02")
    if len(selected_geometry) != int(expected["painting_count"]):
        errors.append("pinned geometry row count does not match expected.painting_count")
    if len(selected_masks) != int(expected["painting_count"]):
        errors.append("pinned base-mask row count does not match expected.painting_count")
    if selected_masks["painting_id"].duplicated().any():
        errors.append("pinned cohort has duplicate loss_large masks")
    if not selected_geometry["status"].astype(str).eq("passed").all():
        errors.append("pinned preprocessed rows must all have passed status")
    for column in (
        "binary_values_valid",
        "content_only_valid",
        "area_within_target_tolerance",
    ):
        if not selected_masks[column].astype(bool).all():
            errors.append(f"pinned masks contain a failed {column} value")
    if not selected_masks["generation_status"].astype(str).eq("passed").all():
        errors.append("pinned masks contain a failed generation status")

    lookup = selected_geometry.set_index("processed_image_id", drop=False)
    for row in selected_masks.itertuples(index=False):
        if str(row.processed_image_id) not in lookup.index.astype(str):
            errors.append(f"missing processed-image foreign key for {row.mask_id}")
            continue
        geometry = lookup.loc[str(row.processed_image_id)]
        if (
            str(geometry["painting_id"]) != str(row.painting_id)
            or str(geometry["processed_path"]) != str(row.processed_image_path)
            or str(geometry["sha256"]) != str(row.processed_image_sha256)
        ):
            errors.append(f"Notebook 02/03 foreign-key mismatch for {row.mask_id}")

    if verify_files:
        root = find_project_root(project_root)
        for column, frame in (
            ("processed_path", selected_geometry),
            ("mask_path", selected_masks),
        ):
            for value in frame[column].astype(str):
                try:
                    resolve_repo_path(value, root, must_exist=True)
                except (FileNotFoundError, ValueError) as exc:
                    errors.append(f"{column} verification failed: {exc}")
                    break
    return errors


def select_sensitivity_cohort(
    preprocessed: pd.DataFrame,
    masks: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Return one joined, ordered Notebook 02/03 record per pinned painting."""
    errors = validate_damage_size_handoff(
        preprocessed, masks, config, verify_files=False
    )
    if errors:
        raise ValueError("Invalid damage-size handoff: " + "; ".join(errors))
    ids = cohort_painting_ids(config)
    order = {painting_id: index for index, painting_id in enumerate(ids)}
    geometry_columns = [
        "painting_id",
        "processed_image_id",
        "processed_path",
        "sha256",
        "width",
        "height",
        "content_x_min",
        "content_y_min",
        "content_x_max",
        "content_y_max",
        "content_width",
        "content_height",
        "content_area_pixels",
        "dataset_sort_index",
    ]
    base_columns = [
        "painting_id",
        "processed_image_id",
        "mask_id",
        "mask_type",
        "mask_path",
        "mask_sha256",
        "damaged_content_pixel_count",
        "damaged_content_fraction",
    ]
    geometry = preprocessed.loc[
        preprocessed["painting_id"].astype(str).isin(ids), geometry_columns
    ].rename(columns={"sha256": "clean_image_sha256"})
    base = masks.loc[
        masks["painting_id"].astype(str).isin(ids)
        & masks["mask_type"].astype(str).eq(str(config["cohort"]["base_mask_type"])),
        base_columns,
    ].rename(
        columns={
            "mask_id": "base_mask_id",
            "mask_type": "base_mask_type",
            "mask_path": "base_mask_path",
            "mask_sha256": "base_mask_sha256",
            "damaged_content_pixel_count": "base_mask_pixels",
            "damaged_content_fraction": "base_damage_fraction",
        }
    )
    result = geometry.merge(
        base, on=["painting_id", "processed_image_id"], how="inner", validate="one_to_one"
    )
    result["_order"] = result["painting_id"].astype(str).map(order)
    return result.sort_values("_order", kind="stable").drop(columns="_order").reset_index(drop=True)


def stable_case_seed(*parts: object, modulus: int = 2**32 - 1) -> int:
    """Derive a stable unsigned seed from identity-bearing values."""
    payload = "||".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big", signed=False) % modulus


def target_pixels_from_percentage(content_area_pixels: int, percentage: float) -> int:
    """Apply the configured round-half-up target-area convention."""
    if int(content_area_pixels) <= 0:
        raise ValueError("content_area_pixels must be positive")
    value = Decimal(str(int(content_area_pixels))) * Decimal(str(float(percentage))) / Decimal("100")
    result = int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if not 0 < result <= int(content_area_pixels):
        raise ValueError("target percentage produces an invalid pixel count")
    return result


def _binary_array(mask: Image.Image | np.ndarray) -> np.ndarray:
    array = np.asarray(mask.convert("L") if isinstance(mask, Image.Image) else mask)
    if array.ndim != 2:
        raise ValueError("Mask must be two-dimensional")
    unique = set(np.unique(array).astype(int).tolist())
    if unique.issubset({0, 1}):
        return array.astype(bool)
    if unique.issubset({0, 255}):
        return array == 255
    raise ValueError(f"Mask must contain binary values; observed {sorted(unique)}")


def _content_array(shape: tuple[int, int], content_bbox: Sequence[int]) -> np.ndarray:
    height, width = shape
    left, top, right, bottom = (int(value) for value in content_bbox)
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError("content_bbox lies outside the mask canvas")
    result = np.zeros(shape, dtype=bool)
    result[top:bottom, left:right] = True
    return result


def _mask_bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.nonzero(mask)
    if not len(xs):
        raise ValueError("Base mask contains no damaged pixels")
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def _mask_centroid(mask: np.ndarray) -> tuple[float, float]:
    ys, xs = np.nonzero(mask)
    if not len(xs):
        raise ValueError("Mask contains no damaged pixels")
    return float(xs.mean()), float(ys.mean())


def _scaled_candidate(
    base_mask: np.ndarray,
    scale: float,
    content_bbox: Sequence[int],
) -> np.ndarray:
    left, top, right, bottom = (int(value) for value in content_bbox)
    bbox_left, bbox_top, bbox_right, bbox_bottom = _mask_bbox(base_mask)
    crop = Image.fromarray(
        (base_mask[bbox_top:bbox_bottom, bbox_left:bbox_right] * 255).astype(np.uint8),
        mode="L",
    )
    new_width = max(1, int(round(crop.width * float(scale))))
    new_height = max(1, int(round(crop.height * float(scale))))
    resized = np.asarray(
        crop.resize((new_width, new_height), resample=Image.Resampling.NEAREST),
        dtype=np.uint8,
    ) == 255
    centroid_x, centroid_y = _mask_centroid(base_mask)
    resized_centroid_x, resized_centroid_y = _mask_centroid(resized)
    paste_left = int(round(centroid_x - resized_centroid_x))
    paste_top = int(round(centroid_y - resized_centroid_y))
    paste_right = paste_left + new_width
    paste_bottom = paste_top + new_height
    source_left = max(0, left - paste_left)
    source_top = max(0, top - paste_top)
    source_right = new_width - max(0, paste_right - right)
    source_bottom = new_height - max(0, paste_bottom - bottom)
    result = np.zeros_like(base_mask, dtype=bool)
    if source_right <= source_left or source_bottom <= source_top:
        return result
    target_left = paste_left + source_left
    target_top = paste_top + source_top
    target_right = paste_left + source_right
    target_bottom = paste_top + source_bottom
    result[target_top:target_bottom, target_left:target_right] = resized[
        source_top:source_bottom, source_left:source_right
    ]
    return result


def _rank_pixels_by_radius(
    pixels: np.ndarray,
    centroid: tuple[float, float],
    *,
    farthest_first: bool,
    seed: int,
) -> np.ndarray:
    ys, xs = np.nonzero(pixels)
    if not len(xs):
        return np.empty(0, dtype=np.int64)
    distance = (xs - centroid[0]) ** 2 + (ys - centroid[1]) ** 2
    rng = np.random.default_rng(int(seed))
    tie_breaker = rng.random(len(xs))
    primary = -distance if farthest_first else distance
    order = np.lexsort((tie_breaker, primary))
    return np.ravel_multi_index((ys[order], xs[order]), pixels.shape)


def scale_mask_to_target_area(
    base_mask: np.ndarray,
    target_pixels: int,
    content_bbox: tuple[int, int, int, int],
    maximum_iterations: int = 32,
    *,
    previous_mask: np.ndarray | None = None,
    case_seed: int = 0,
    addition_strategy: str = "incremental_scale",
) -> dict[str, Any]:
    """Scale about the base centroid and correct to an exact, nested pixel target.

    The compatibility-facing return value remains a dictionary and the ``mask``
    entry remains a zero/one uint8 array for the legacy Notebook 06 helper.
    """
    supported_addition_strategies = {
        "incremental_scale",
        "nearest_unmasked_content_by_euclidean_distance",
    }
    if addition_strategy not in supported_addition_strategies:
        raise ValueError(
            "Unsupported addition_strategy: "
            f"{addition_strategy!r}; expected one of "
            f"{sorted(supported_addition_strategies)}"
        )
    base = _binary_array(base_mask)
    content = _content_array(base.shape, content_bbox)
    if np.any(base & ~content):
        raise ValueError("Base mask extends outside the configured content region")
    target = int(target_pixels)
    if not 0 < target <= int(content.sum()):
        raise ValueError("target_pixels must lie within the content-region area")
    previous = np.zeros_like(base, dtype=bool)
    if previous_mask is not None:
        previous = _binary_array(previous_mask)
        if previous.shape != base.shape:
            raise ValueError("previous_mask dimensions differ from base_mask")
        if np.any(previous & ~content):
            raise ValueError("previous_mask extends outside the content region")
        if int(previous.sum()) > target:
            raise ValueError("target_pixels cannot be smaller than previous_mask")

    base_pixels = int(base.sum())
    initial_scale = math.sqrt(target / base_pixels)
    low = max(0.001, initial_scale / 4.0)
    high = max(initial_scale * 4.0, 1.0)
    candidates: list[tuple[int, float, np.ndarray]] = []
    for scale in (low, initial_scale, high):
        candidate = _scaled_candidate(base, scale, content_bbox) | previous
        candidates.append((abs(int(candidate.sum()) - target), scale, candidate))
    for _ in range(int(maximum_iterations)):
        middle = (low + high) / 2.0
        candidate = _scaled_candidate(base, middle, content_bbox) | previous
        pixels = int(candidate.sum())
        candidates.append((abs(pixels - target), middle, candidate))
        if pixels < target:
            low = middle
        elif pixels > target:
            high = middle
        else:
            break
    _, best_scale, corrected = min(candidates, key=lambda item: (item[0], item[1]))
    corrected = corrected.copy()
    pre_correction_pixels = int(corrected.sum())
    centroid = _mask_centroid(base)
    removed = 0
    added = 0
    if pre_correction_pixels > target:
        removable = corrected & ~previous
        count = pre_correction_pixels - target
        ranked = _rank_pixels_by_radius(
            removable, centroid, farthest_first=True, seed=case_seed
        )
        if len(ranked) < count:
            raise RuntimeError("Strict nesting leaves too few removable pixels")
        flat = corrected.ravel()
        flat[ranked[:count]] = False
        removed = count
    elif pre_correction_pixels < target:
        count = target - pre_correction_pixels
        if addition_strategy == "incremental_scale":
            expansion_scale = best_scale
            expansion = corrected.copy()
            for _ in range(512):
                expansion_scale *= 1.01
                expansion = _scaled_candidate(base, expansion_scale, content_bbox) | previous
                if int((expansion & ~corrected).sum()) >= count:
                    break
            pool = expansion & ~corrected
            if int(pool.sum()) < count:
                pool = content & ~corrected
            ranked = _rank_pixels_by_radius(
                pool, centroid, farthest_first=False, seed=case_seed
            )
        else:
            pool = content & ~corrected
            ys, xs = np.nonzero(pool)
            if not len(xs):
                ranked = np.empty(0, dtype=np.int64)
            else:
                distance_to_mask = distance_transform_edt(~corrected)
                distances = distance_to_mask[ys, xs]
                rng = np.random.default_rng(int(case_seed))
                tie_breaker = rng.random(len(xs))
                order = np.lexsort((tie_breaker, distances))
                ranked = np.ravel_multi_index(
                    (ys[order], xs[order]), corrected.shape
                )
        if len(ranked) < count:
            raise RuntimeError("Content region leaves too few pixels for correction")
        flat = corrected.ravel()
        flat[ranked[:count]] = True
        added = count
    realized = int(corrected.sum())
    previous_removed = int((previous & ~corrected).sum())
    if realized != target or previous_removed:
        raise RuntimeError("Exact target or strict nesting invariant was not satisfied")
    return {
        "mask": corrected.astype(np.uint8),
        "scale_factor": float(best_scale),
        "base_pixels": base_pixels,
        "target_pixels": target,
        "pre_correction_pixels": pre_correction_pixels,
        "realised_pixels": realized,
        "absolute_pixel_error": 0,
        "correction_added_pixels": int(added),
        "correction_removed_pixels": int(removed),
        "addition_strategy": addition_strategy,
        "previous_pixels_removed": previous_removed,
        "pixels_added_from_previous": int((corrected & ~previous).sum()),
        "nested_with_previous": True,
    }


def generate_nested_mask_series(
    base_mask: Image.Image | np.ndarray,
    *,
    content_bbox: tuple[int, int, int, int],
    content_area_pixels: int,
    levels: Iterable[tuple[str, float]],
    global_seed: int,
    seed_scheme_version: str,
    painting_id: str,
    base_mask_sha256: str,
    maximum_iterations: int = 32,
) -> tuple[dict[str, Any], ...]:
    """Generate a deterministic ascending sequence with strict subset nesting."""
    base = _binary_array(base_mask)
    previous: np.ndarray | None = None
    previous_level_id = FIRST_LEVEL_SENTINEL
    previous_mask_id = FIRST_LEVEL_SENTINEL
    records: list[dict[str, Any]] = []
    for level_id, percentage in levels:
        target = target_pixels_from_percentage(content_area_pixels, percentage)
        seed = stable_case_seed(
            seed_scheme_version,
            global_seed,
            painting_id,
            base_mask_sha256,
            level_id,
        )
        result = scale_mask_to_target_area(
            base,
            target,
            content_bbox,
            maximum_iterations,
            previous_mask=previous,
            case_seed=seed,
        )
        mask_id = f"mask__damage_size__{painting_id}__loss_large__{level_id}"
        result.update(
            {
                "level_id": str(level_id),
                "target_percentage_content": float(percentage),
                "case_seed": int(seed),
                "mask_id": mask_id,
                "previous_level_id": previous_level_id,
                "previous_mask_id": previous_mask_id,
            }
        )
        records.append(result)
        previous = result["mask"]
        previous_level_id = str(level_id)
        previous_mask_id = mask_id
    return tuple(records)


def _expected_output_path(
    output_root: Path,
    directory_key: str,
    painting_id: str,
    level_id: str,
    config: Mapping[str, Any],
    project_root: Path,
) -> Path:
    relative = str(config["output"]["image_path_template"]).format(
        painting_id=painting_id, level_id=level_id
    )
    path = output_root / str(config["output"][directory_key]) / relative
    return require_notebook_output_path(
        path, str(config["output"]["notebook_stem"]), project_root
    )


def _save_png_atomic(image: Image.Image, destination: Path, config: Mapping[str, Any]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    image.save(
        temporary,
        format="PNG",
        compress_level=int(config["generator"]["png_compress_level"]),
        optimize=bool(config["generator"]["png_optimize"]),
    )
    os.replace(temporary, destination)


def _remove_stale_files(
    roots: Sequence[Path], expected_paths: set[Path], project_root: Path
) -> tuple[str, ...]:
    removed: list[str] = []
    expected = {path.resolve() for path in expected_paths}
    for root in roots:
        require_notebook_output_path(
            root, "05_damage_size_sensitivity_dataset_generation", project_root
        )
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.png")):
            if path.resolve() not in expected:
                path.unlink()
                removed.append(to_repo_relative(path, project_root))
    return tuple(removed)


def generate_damage_size_dataset(
    cohort: pd.DataFrame,
    config: Mapping[str, Any],
    output_root: str | Path,
    project_root: str | Path | None = None,
) -> DamageSizeGenerationResult:
    """Generate the complete 35-case Notebook 05 image handoff."""
    errors = validate_damage_size_config(config)
    if errors:
        raise ValueError("Invalid damage-size configuration: " + "; ".join(errors))
    root = find_project_root(project_root)
    owned_root = require_notebook_output_path(
        output_root, str(config["output"]["notebook_stem"]), root
    )
    required_columns = {
        "painting_id", "processed_image_id", "processed_path", "clean_image_sha256",
        "width", "height", "content_x_min", "content_y_min", "content_x_max",
        "content_y_max", "content_area_pixels", "base_mask_id", "base_mask_type",
        "base_mask_path", "base_mask_sha256",
    }
    missing = sorted(required_columns - set(cohort.columns))
    if missing:
        raise ValueError(f"Cohort table lacks required columns: {missing}")
    if len(cohort) != int(config["expected"]["painting_count"]):
        raise ValueError("Cohort row count does not match configuration")

    fill_color = _normalize_fill_color(config["generator"]["fill_color_rgb"])
    levels = configured_levels(config)
    expected_paths: set[Path] = set()
    case_records: list[dict[str, Any]] = []
    generation_records: list[dict[str, Any]] = []
    for row in cohort.itertuples(index=False):
        clean_path = resolve_repo_path(str(row.processed_path), root, must_exist=True)
        base_path = resolve_repo_path(str(row.base_mask_path), root, must_exist=True)
        clean = Image.open(clean_path).convert("RGB")
        base = Image.open(base_path).convert("L")
        content_bbox = (
            int(row.content_x_min), int(row.content_y_min),
            int(row.content_x_max), int(row.content_y_max),
        )
        series = generate_nested_mask_series(
            base,
            content_bbox=content_bbox,
            content_area_pixels=int(row.content_area_pixels),
            levels=levels,
            global_seed=int(config["generator"]["global_seed"]),
            seed_scheme_version=str(config["generator"]["seed_scheme_version"]),
            painting_id=str(row.painting_id),
            base_mask_sha256=str(row.base_mask_sha256),
            maximum_iterations=int(config["generator"]["maximum_scale_iterations"]),
        )
        for item in series:
            started = time.perf_counter()
            level_id = str(item["level_id"])
            mask_path = _expected_output_path(
                owned_root, "mask_directory", str(row.painting_id), level_id, config, root
            )
            damaged_path = _expected_output_path(
                owned_root, "damaged_directory", str(row.painting_id), level_id, config, root
            )
            expected_paths.update({mask_path.resolve(), damaged_path.resolve()})
            mask_image = Image.fromarray((item["mask"] * 255).astype(np.uint8), mode="L")
            damaged = apply_mask_damage(clean, mask_image, fill_color)
            _save_png_atomic(mask_image, mask_path, config)
            _save_png_atomic(damaged, damaged_path, config)
            elapsed = time.perf_counter() - started
            realized_fraction = int(item["realised_pixels"]) / int(row.content_area_pixels)
            target_fraction = float(item["target_percentage_content"]) / 100.0
            absolute_pp = abs(realized_fraction - target_fraction) * 100.0
            case_id = (
                f"damage_size__{row.painting_id}__loss_large__{level_id}"
            )
            damaged_image_id = (
                f"damaged__damage_size__{row.painting_id}__loss_large__{level_id}"
            )
            record = {
                "dataset_id": str(config["dataset"]["dataset_id"]),
                "dataset_version": str(config["dataset"]["dataset_version"]),
                "dataset_scope": str(config["dataset"]["dataset_scope"]),
                "experiment_id": str(config["dataset"]["experiment_id"]),
                "case_id": case_id,
                "painting_id": str(row.painting_id),
                "processed_image_id": str(row.processed_image_id),
                "base_mask_id": str(row.base_mask_id),
                "base_mask_type": str(row.base_mask_type),
                "level_id": level_id,
                "mask_or_effect_id": str(item["mask_id"]),
                "damaged_image_id": damaged_image_id,
                "input_image_path": to_repo_relative(damaged_path, root),
                "clean_image_path": to_repo_relative(clean_path, root),
                "base_mask_path": to_repo_relative(base_path, root),
                "mask_or_effect_path": to_repo_relative(mask_path, root),
                "target_damage_fraction": round(target_fraction, 9),
                "target_damage_pixels": int(item["target_pixels"]),
                "realized_damage_fraction": round(realized_fraction, 9),
                "realized_damage_pixels": int(item["realised_pixels"]),
                "absolute_percentage_point_error": round(absolute_pp, 9),
                "scale_factor": round(float(item["scale_factor"]), 12),
                "pre_correction_pixels": int(item["pre_correction_pixels"]),
                "correction_added_pixels": int(item["correction_added_pixels"]),
                "correction_removed_pixels": int(item["correction_removed_pixels"]),
                "previous_level_id": str(item["previous_level_id"]),
                "previous_mask_id": str(item["previous_mask_id"]),
                "nested_with_previous": bool(item["nested_with_previous"]),
                "seed_scheme_version": str(config["generator"]["seed_scheme_version"]),
                "global_seed": int(config["generator"]["global_seed"]),
                "case_seed": int(item["case_seed"]),
                "damage_or_degradation_type": "binary_missing_region",
                "fill_strategy": str(config["generator"]["fill_strategy"]),
                "fill_color_r": fill_color[0], "fill_color_g": fill_color[1],
                "fill_color_b": fill_color[2],
                "clean_image_sha256": sha256_file(clean_path),
                "base_mask_sha256": sha256_file(base_path),
                "mask_sha256": sha256_file(mask_path),
                "damaged_image_sha256": sha256_file(damaged_path),
                "width": int(clean.width), "height": int(clean.height),
                "mask_mode": "L", "damaged_mode": "RGB", "format": "PNG",
                "mask_size_bytes": mask_path.stat().st_size,
                "damaged_size_bytes": damaged_path.stat().st_size,
                "generator_name": GENERATOR_NAME,
                "generator_version": GENERATOR_VERSION,
                "config_schema_version": DAMAGE_SIZE_CONFIG_SCHEMA_VERSION,
                "config_version": str(config["config_version"]),
                "source_manifest_path": (
                    "outputs/05_damage_size_sensitivity_dataset_generation/"
                    "manifests/run_manifest.json"
                ),
                "generation_status": "passed", "status": "passed", "issue": "",
            }
            case_records.append(record)
            generation_records.append(
                {
                    "case_id": case_id,
                    "painting_id": str(row.painting_id),
                    "level_id": level_id,
                    "runtime_seconds": round(elapsed, 9),
                    "previous_pixels_removed": int(item["previous_pixels_removed"]),
                    "pixels_added_from_previous": int(item["pixels_added_from_previous"]),
                }
            )
    cases = pd.DataFrame(case_records, columns=DAMAGE_SIZE_CASES_COLUMNS)
    schema_result = validate_dataframe(cases, DAMAGE_SIZE_CASES_SCHEMA)
    if not schema_result.passed or schema_result.unexpected_columns:
        raise ValueError(f"Generated cases violate schema: {schema_result.to_dict()}")
    removed = _remove_stale_files(
        [owned_root / config["output"]["mask_directory"],
         owned_root / config["output"]["damaged_directory"]],
        expected_paths,
        root,
    )
    return DamageSizeGenerationResult(
        cases=cases,
        generation_evidence=pd.DataFrame(generation_records),
        removed_stale_paths=removed,
    )


def _relative_drift(value: float, reference: float) -> float:
    return abs(float(value) - float(reference)) / max(abs(float(reference)), 1e-12)


def validate_saved_damage_size_dataset(
    cases: pd.DataFrame,
    preprocessed: pd.DataFrame,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> DamageSizeValidationResult:
    """Reload every persisted case and build the canonical generation audit."""
    root = find_project_root(project_root)
    errors = validate_damage_size_config(config)
    if errors:
        raise ValueError("Invalid damage-size configuration: " + "; ".join(errors))
    case_schema = validate_dataframe(cases, DAMAGE_SIZE_CASES_SCHEMA)
    if not case_schema.passed or case_schema.unexpected_columns:
        raise ValueError(f"Cases violate schema: {case_schema.to_dict()}")
    geometry = preprocessed.set_index("processed_image_id", drop=False)
    fill = np.asarray(_normalize_fill_color(config["generator"]["fill_color_rgb"]), dtype=np.uint8)
    tolerance = float(config["generator"]["maximum_absolute_percentage_point_error"])
    morphology_config = config["morphology"]
    records: list[dict[str, Any]] = []
    expected_paths: set[Path] = set()
    previous_by_painting: dict[str, tuple[str, np.ndarray]] = {}
    for case in cases.itertuples(index=False):
        issue: list[str] = []
        clean_path = root / str(case.clean_image_path)
        base_path = root / str(case.base_mask_path)
        mask_path = root / str(case.mask_or_effect_path)
        damaged_path = root / str(case.input_image_path)
        expected_paths.update({mask_path.resolve(), damaged_path.resolve()})
        exists = [path.is_file() for path in (clean_path, base_path, mask_path, damaged_path)]
        reload_passed = all(exists)
        if not reload_passed:
            issue.append("one or more case files are missing")
            clean = Image.new("RGB", (1, 1))
            base = Image.new("L", (1, 1))
            mask = Image.new("L", (1, 1))
            damaged = Image.new("RGB", (1, 1))
        else:
            try:
                clean = Image.open(clean_path).convert("RGB")
                base = Image.open(base_path).convert("L")
                mask = Image.open(mask_path).convert("L")
                damaged = Image.open(damaged_path).convert("RGB")
            except Exception as exc:  # pragma: no cover - corrupt image backend detail
                reload_passed = False
                issue.append(f"reload failed: {exc}")
                clean = Image.new("RGB", (1, 1))
                base = Image.new("L", (1, 1))
                mask = Image.new("L", (1, 1))
                damaged = Image.new("RGB", (1, 1))
        geometry_row = geometry.loc[str(case.processed_image_id)]
        content_bbox = (
            int(geometry_row["content_x_min"]), int(geometry_row["content_y_min"]),
            int(geometry_row["content_x_max"]), int(geometry_row["content_y_max"]),
        )
        dimensions_match = reload_passed and len({clean.size, base.size, mask.size, damaged.size}) == 1
        mask_array = _binary_array(mask) if reload_passed else np.zeros((1, 1), dtype=bool)
        base_array = _binary_array(base) if reload_passed else np.zeros((1, 1), dtype=bool)
        unique_values = sorted(np.unique(np.asarray(mask)).astype(int).tolist()) if reload_passed else []
        binary_valid = set(unique_values).issubset({0, 255})
        content = _content_array(mask_array.shape, content_bbox) if dimensions_match else np.zeros_like(mask_array)
        content_only = dimensions_match and not bool(np.any(mask_array & ~content))
        realized_pixels = int(mask_array.sum())
        metadata_pixels_match = realized_pixels == int(case.realized_damage_pixels)
        area_pp = abs(
            realized_pixels / int(geometry_row["content_area_pixels"])
            - float(case.target_damage_fraction)
        ) * 100.0
        area_passed = area_pp <= tolerance
        base_morphology = calculate_mask_morphology(base, content_box=content_bbox) if dimensions_match else {}
        scaled_morphology = calculate_mask_morphology(mask, content_box=content_bbox) if dimensions_match else {}
        base_centroid = _mask_centroid(base_array) if base_array.any() else (0.0, 0.0)
        scaled_centroid = _mask_centroid(mask_array) if mask_array.any() else (0.0, 0.0)
        centroid_shift = math.dist(base_centroid, scaled_centroid)
        diagonal = math.hypot(int(geometry_row["content_width"]), int(geometry_row["content_height"]))
        centroid_fraction = centroid_shift / diagonal if diagonal else math.inf
        aspect_drift = _relative_drift(
            scaled_morphology.get("bbox_aspect_ratio", 0.0),
            base_morphology.get("bbox_aspect_ratio", 0.0),
        )
        fill_drift = _relative_drift(
            scaled_morphology.get("bbox_fill_ratio", 0.0),
            base_morphology.get("bbox_fill_ratio", 0.0),
        )
        compactness_drift = _relative_drift(
            scaled_morphology.get("mask_compactness", 0.0),
            base_morphology.get("mask_compactness", 0.0),
        )
        component_delta = int(scaled_morphology.get("connected_component_count", 0)) - int(
            base_morphology.get("connected_component_count", 0)
        )
        largest_drift = _relative_drift(
            scaled_morphology.get("largest_component_fraction", 0.0),
            base_morphology.get("largest_component_fraction", 0.0),
        )
        previous_level_id = str(case.previous_level_id)
        previous_removed = 0
        pixels_added = realized_pixels
        nested = True
        previous = previous_by_painting.get(str(case.painting_id))
        if previous_level_id:
            if previous is None or previous[0] != previous_level_id:
                nested = False
                issue.append("previous-level sequence is missing or out of order")
            else:
                previous_array = previous[1]
                previous_removed = int((previous_array & ~mask_array).sum())
                pixels_added = int((mask_array & ~previous_array).sum())
                nested = previous_removed == 0
        previous_by_painting[str(case.painting_id)] = (str(case.level_id), mask_array.copy())
        morphology_passed = (
            centroid_shift <= float(morphology_config["maximum_centroid_shift_pixels"])
            and centroid_fraction <= float(
                morphology_config["maximum_centroid_shift_fraction_of_content_diagonal"]
            )
            and aspect_drift <= float(morphology_config["maximum_relative_bbox_aspect_ratio_drift"])
            and compactness_drift <= float(morphology_config["maximum_relative_compactness_drift"])
            and (component_delta == 0 or not morphology_config["require_component_count_preserved"])
            and (
                not bool(scaled_morphology.get("touches_content_boundary", True))
                or not morphology_config["require_no_content_boundary_contact"]
            )
        )
        clean_array = np.asarray(clean, dtype=np.uint8)
        damaged_array = np.asarray(damaged, dtype=np.uint8)
        if dimensions_match:
            changed = np.any(clean_array != damaged_array, axis=2)
            outside_changed = int((changed & ~mask_array).sum())
            inside_not_fill = int(np.any(damaged_array[mask_array] != fill, axis=1).sum())
        else:
            outside_changed = -1
            inside_not_fill = -1
        checksums = {
            "clean": exists[0] and sha256_file(clean_path) == str(case.clean_image_sha256),
            "base": exists[1] and sha256_file(base_path) == str(case.base_mask_sha256),
            "mask": exists[2] and sha256_file(mask_path) == str(case.mask_sha256),
            "damaged": exists[3] and sha256_file(damaged_path) == str(case.damaged_image_sha256),
        }
        expected_mask_path = _expected_output_path(
            root / "outputs" / config["output"]["notebook_stem"],
            "mask_directory", str(case.painting_id), str(case.level_id), config, root,
        )
        expected_damaged_path = _expected_output_path(
            root / "outputs" / config["output"]["notebook_stem"],
            "damaged_directory", str(case.painting_id), str(case.level_id), config, root,
        )
        output_contract = (
            mask_path.resolve() == expected_mask_path.resolve()
            and damaged_path.resolve() == expected_damaged_path.resolve()
        )
        passed = all(
            (
                reload_passed, dimensions_match, binary_valid, content_only,
                metadata_pixels_match, area_passed, nested, morphology_passed,
                outside_changed == 0, inside_not_fill == 0,
                all(checksums.values()), output_contract,
            )
        )
        if not passed and not issue:
            issue.append("one or more validation invariants failed")
        records.append(
            {
                "dataset_id": str(case.dataset_id), "dataset_version": str(case.dataset_version),
                "dataset_scope": str(case.dataset_scope), "experiment_id": str(case.experiment_id),
                "case_id": str(case.case_id), "painting_id": str(case.painting_id),
                "level_id": str(case.level_id), "mask_or_effect_id": str(case.mask_or_effect_id),
                "previous_level_id": previous_level_id,
                "target_damage_fraction": float(case.target_damage_fraction),
                "target_damage_pixels": int(case.target_damage_pixels),
                "realized_damage_fraction": round(realized_pixels / int(geometry_row["content_area_pixels"]), 9),
                "realized_damage_pixels": realized_pixels,
                "absolute_percentage_point_error": round(area_pp, 9),
                "area_within_tolerance": bool(area_passed),
                "scale_factor": float(case.scale_factor),
                "pre_correction_pixels": int(case.pre_correction_pixels),
                "correction_added_pixels": int(case.correction_added_pixels),
                "correction_removed_pixels": int(case.correction_removed_pixels),
                "base_centroid_x": round(base_centroid[0], 9), "base_centroid_y": round(base_centroid[1], 9),
                "scaled_centroid_x": round(scaled_centroid[0], 9), "scaled_centroid_y": round(scaled_centroid[1], 9),
                "centroid_shift_pixels": round(centroid_shift, 9),
                "centroid_shift_fraction_of_content_diagonal": round(centroid_fraction, 9),
                "base_bbox_aspect_ratio": base_morphology.get("bbox_aspect_ratio", 0.0),
                "scaled_bbox_aspect_ratio": scaled_morphology.get("bbox_aspect_ratio", 0.0),
                "relative_bbox_aspect_ratio_drift": round(aspect_drift, 9),
                "base_bbox_fill_ratio": base_morphology.get("bbox_fill_ratio", 0.0),
                "scaled_bbox_fill_ratio": scaled_morphology.get("bbox_fill_ratio", 0.0),
                "relative_bbox_fill_ratio_drift": round(fill_drift, 9),
                "base_mask_perimeter_pixels": base_morphology.get("mask_perimeter_pixels", 0),
                "scaled_mask_perimeter_pixels": scaled_morphology.get("mask_perimeter_pixels", 0),
                "base_mask_compactness": base_morphology.get("mask_compactness", 0.0),
                "scaled_mask_compactness": scaled_morphology.get("mask_compactness", 0.0),
                "relative_compactness_drift": round(compactness_drift, 9),
                "base_connected_component_count": base_morphology.get("connected_component_count", 0),
                "scaled_connected_component_count": scaled_morphology.get("connected_component_count", 0),
                "component_count_delta": component_delta,
                "base_largest_component_fraction": base_morphology.get("largest_component_fraction", 0.0),
                "scaled_largest_component_fraction": scaled_morphology.get("largest_component_fraction", 0.0),
                "largest_component_fraction_drift": round(largest_drift, 9),
                "touches_content_boundary": bool(scaled_morphology.get("touches_content_boundary", True)),
                "minimum_distance_to_content_boundary_pixels": scaled_morphology.get("minimum_distance_to_content_boundary_pixels", -1),
                "nested_with_previous": bool(nested), "previous_pixels_removed": previous_removed,
                "pixels_added_from_previous": pixels_added,
                "clean_file_exists": exists[0], "base_mask_file_exists": exists[1],
                "mask_file_exists": exists[2], "damaged_file_exists": exists[3],
                "reload_passed": bool(reload_passed), "dimensions_match": bool(dimensions_match),
                "mask_unique_values": "|".join(str(value) for value in unique_values),
                "binary_values_valid": bool(binary_valid), "content_only_valid": bool(content_only),
                "metadata_mask_pixels_match": bool(metadata_pixels_match),
                "outside_mask_changed_pixel_count": outside_changed,
                "inside_mask_not_fill_pixel_count": inside_not_fill,
                "clean_sha256_matches": bool(checksums["clean"]),
                "base_mask_sha256_matches": bool(checksums["base"]),
                "mask_sha256_matches": bool(checksums["mask"]),
                "damaged_sha256_matches": bool(checksums["damaged"]),
                "output_contract_valid": bool(output_contract),
                "morphology_preservation_status": "passed" if morphology_passed else "failed",
                "validation_status": "passed" if passed else "failed",
                "issue": "; ".join(issue),
            }
        )
    audit = pd.DataFrame(records, columns=DAMAGE_SIZE_GENERATION_AUDIT_COLUMNS)
    output_root = root / "outputs" / config["output"]["notebook_stem"]
    observed_paths = set()
    for directory_key in ("mask_directory", "damaged_directory"):
        directory = output_root / config["output"][directory_key]
        if directory.exists():
            observed_paths.update(path.resolve() for path in directory.rglob("*.png"))
    orphans = tuple(sorted(to_repo_relative(path, root) for path in observed_paths - expected_paths))
    summary = {
        "duplicate_case_id_count": int(cases["case_id"].duplicated().sum()),
        "duplicate_mask_id_count": int(cases["mask_or_effect_id"].duplicated().sum()),
        "duplicate_output_path_count": int(cases["input_image_path"].duplicated().sum() + cases["mask_or_effect_path"].duplicated().sum()),
        "missing_output_count": int((~audit["mask_file_exists"] | ~audit["damaged_file_exists"]).sum()),
        "orphan_output_count": len(orphans),
        "failed_case_count": int(audit["validation_status"].ne("passed").sum()),
        "area_failure_count": int((~audit["area_within_tolerance"]).sum()),
        "nesting_failure_count": int((~audit["nested_with_previous"]).sum()),
        "morphology_failure_count": int(audit["morphology_preservation_status"].ne("passed").sum()),
        "pixel_integrity_failure_count": int(((audit["outside_mask_changed_pixel_count"] != 0) | (audit["inside_mask_not_fill_pixel_count"] != 0)).sum()),
        "checksum_failure_count": int((~audit[["clean_sha256_matches", "base_mask_sha256_matches", "mask_sha256_matches", "damaged_sha256_matches"]].all(axis=1)).sum()),
        "output_contract_failure_count": int((~audit["output_contract_valid"]).sum()),
    }
    return DamageSizeValidationResult(audit=audit, summary=summary, orphan_paths=orphans)


def write_dataframe_atomic(dataframe: pd.DataFrame, path: str | Path) -> Path:
    """Write a normalized CSV through a same-directory atomic replacement."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    dataframe.to_csv(temporary, index=False, lineterminator="\n")
    os.replace(temporary, destination)
    return destination
