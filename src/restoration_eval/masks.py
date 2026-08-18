"""Deterministic canonical binary missing-region mask generation."""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from collections import deque
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml
from PIL import Image, ImageDraw, ImageFilter, UnidentifiedImageError

from .paths import (
    find_project_root,
    notebook_output_root,
    require_notebook_output_path,
    resolve_repo_path,
    to_repo_relative,
)
from .regions import content_region, mask_bbox
from .schemas import (
    CANONICAL_MASKS_COLUMNS,
    CANONICAL_MASKS_SCHEMA,
    MASK_AUDIT_COLUMNS,
    MASK_AUDIT_SCHEMA,
    PREPROCESSED_IMAGES_SCHEMA,
    validate_dataframe,
)


MASKS_MODULE_VERSION = "3.0.0"
CANONICAL_MASK_CONFIG_SCHEMA_VERSION = "canonical_mask_config.v1"
GENERATOR_NAME = "canonical_synthetic_damage_masks"
GENERATOR_VERSION = MASKS_MODULE_VERSION
SUPPORTED_MASK_TYPES = (
    "zero_control",
    "scratch_thin",
    "loss_small",
    "loss_large",
    "mixed_damage",
)
GLOBAL_AUDIT_METRIC_COUNT = 30
FAMILY_AUDIT_METRICS = (
    "case_count",
    "mean_damaged_content_fraction",
    "std_damaged_content_fraction",
    "median_damaged_content_fraction",
    "mean_connected_component_count",
    "median_largest_component_fraction",
    "median_bbox_fill_ratio",
    "median_maximum_component_aspect_ratio",
    "median_mask_compactness",
    "boundary_touch_fraction",
    "median_distance_to_content_boundary_pixels",
    "mean_generation_attempts",
)
FAMILY_EXPECTATION_COUNT = 5
PAIRWISE_FAMILY_COMPARISON_COUNT = 10
RUNTIME_COLUMNS = ("mask_id", "runtime_seconds")

# Compatibility values retained for the unrefactored robustness helper.
DEFAULT_MASK_SPECS: dict[str, dict[str, float]] = {
    "zero_control": {"target_area_pct": 0.0, "min_area_pct": 0.0, "max_area_pct": 0.0},
    "scratch_thin": {"target_area_pct": 2.0, "min_area_pct": 1.0, "max_area_pct": 3.0},
    "loss_small": {"target_area_pct": 4.5, "min_area_pct": 3.0, "max_area_pct": 6.0},
    "loss_large": {"target_area_pct": 12.5, "min_area_pct": 10.0, "max_area_pct": 15.0},
    "mixed_damage": {"target_area_pct": 11.5, "min_area_pct": 8.0, "max_area_pct": 15.0},
}


@dataclass(frozen=True)
class MaskCaseResult:
    image: Image.Image
    record: Mapping[str, Any]


@dataclass(frozen=True)
class MaskGenerationResult:
    masks: pd.DataFrame
    runtimes: pd.DataFrame
    family_validation: pd.DataFrame


@dataclass(frozen=True)
class MaskValidationResult:
    mask_checks: pd.DataFrame
    summary: Mapping[str, int]
    orphan_paths: tuple[str, ...]
    duplicate_nonzero_sha256_groups: tuple[tuple[str, ...], ...]
    cross_family_equivalent_pairs: tuple[tuple[str, str, str], ...]

    @property
    def passed(self) -> bool:
        failure_keys = tuple(
            key for key in self.summary if key.endswith("_count")
        )
        return all(int(self.summary[key]) == 0 for key in failure_keys)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pixel_sha256(array: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(array, dtype=np.uint8).tobytes()).hexdigest()


def stable_seed(*parts: object, modulus: int = 2**32 - 1) -> int:
    """Derive a deterministic unsigned seed from stable identifiers."""
    payload = "||".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False) % modulus


_stable_seed = stable_seed


def _require_mapping(parent: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"Canonical mask configuration key {key!r} must be a mapping")
    return value


def validate_mask_config(config: Mapping[str, Any]) -> list[str]:
    """Return violations of the canonical_mask_config.v1 contract."""
    errors: list[str] = []
    if config.get("config_schema_version") != CANONICAL_MASK_CONFIG_SCHEMA_VERSION:
        errors.append(
            f"config_schema_version must equal {CANONICAL_MASK_CONFIG_SCHEMA_VERSION}"
        )
    if not str(config.get("config_version", "")).strip():
        errors.append("config_version must be non-empty")
    try:
        dataset = _require_mapping(config, "dataset")
        inputs = _require_mapping(config, "inputs")
        output = _require_mapping(config, "output")
        generator = _require_mapping(config, "generator")
        morphology = _require_mapping(config, "morphology")
        families = _require_mapping(config, "families")
        family_validation = _require_mapping(config, "family_validation")
        expected = _require_mapping(config, "expected")
        smoke = _require_mapping(config, "smoke")
        examples = _require_mapping(config, "examples")
    except ValueError as exc:
        return errors + [str(exc)]

    schema_expectations = {
        "input_schema_version": PREPROCESSED_IMAGES_SCHEMA.version,
        "output_schema_version": CANONICAL_MASKS_SCHEMA.version,
        "audit_schema_version": MASK_AUDIT_SCHEMA.version,
    }
    for key in ("dataset_id", "dataset_version", "dataset_scope", "execution_profile", "experiment_id"):
        if not str(dataset.get(key, "")).strip():
            errors.append(f"dataset.{key} must be non-empty")
    for key, value in schema_expectations.items():
        if dataset.get(key) != value:
            errors.append(f"dataset.{key} must equal {value}")

    required_inputs = (
        "geometry_path", "clean_images_path", "artifacts_path", "run_manifest_path",
        "required_artifact_keys", "required_registry_keys", "required_upstream_run_status",
    )
    for key in required_inputs:
        if key not in inputs or inputs.get(key) in (None, "", []):
            errors.append(f"inputs.{key} must be non-empty")
    if list(inputs.get("required_artifact_keys", [])) != ["preprocessed_images", "clean_images"]:
        errors.append("inputs.required_artifact_keys must equal ['preprocessed_images', 'clean_images']")
    if list(inputs.get("required_registry_keys", [])) != [
        "preprocessing.geometry", "preprocessing.clean_images"
    ]:
        errors.append(
            "inputs.required_registry_keys must equal "
            "['preprocessing.geometry', 'preprocessing.clean_images']"
        )

    exact_outputs = {
        "notebook_stem": "03_canonical_mask_generation",
        "table_path": "data/masks.csv",
        "image_directory": "images/masks",
        "image_path_template": "{painting_id}/{mask_type}.png",
        "audit_path": "metrics/mask_audit.csv",
        "morphology_figure_path": "figures/mask_morphology.png",
        "examples_figure_path": "figures/mask_examples.png",
        "protocol_path": "reports/mask_protocol.md",
    }
    for key, value in exact_outputs.items():
        if output.get(key) != value:
            errors.append(f"output.{key} must equal {value}")

    exact_generator = {
        "name": GENERATOR_NAME,
        "version": GENERATOR_VERSION,
        "seed_scheme_version": "canonical_mask_seed.v1",
        "retry_policy": "closed_range_then_nearest_range_and_target",
        "retry_failure_action": "block",
        "target_width": 768,
        "target_height": 768,
        "output_mode": "L",
        "output_format": "PNG",
        "output_extension": ".png",
        "background_value": 0,
        "damaged_value": 255,
        "restrict_to_content_region": True,
        "coordinate_convention": "xyxy_exclusive_zero_based",
        "strip_output_metadata": True,
    }
    for key, value in exact_generator.items():
        if generator.get(key) != value:
            errors.append(f"generator.{key} must equal {value}")
    for key in ("global_seed", "maximum_generation_attempts", "png_compress_level"):
        try:
            if int(generator.get(key, 0)) < 1:
                errors.append(f"generator.{key} must be positive")
        except (TypeError, ValueError):
            errors.append(f"generator.{key} must be an integer")

    expected_types = list(expected.get("mask_types", []))
    if expected_types != list(SUPPORTED_MASK_TYPES):
        errors.append(f"expected.mask_types must equal {list(SUPPORTED_MASK_TYPES)}")
    expected_counts = {
        "painting_count": 50,
        "family_count": len(SUPPORTED_MASK_TYPES),
        "mask_count": 250,
        "audit_row_count": (
            GLOBAL_AUDIT_METRIC_COUNT
            + len(SUPPORTED_MASK_TYPES) * len(FAMILY_AUDIT_METRICS)
            + PAIRWISE_FAMILY_COMPARISON_COUNT
            + FAMILY_EXPECTATION_COUNT
        ),
        "validation_row_count": 50,
        "artifact_record_count": 7,
    }
    for key, value in expected_counts.items():
        if expected.get(key) != value:
            errors.append(f"expected.{key} must equal {value}")

    previous_upper = -1.0
    for index, mask_type in enumerate(SUPPORTED_MASK_TYPES):
        raw = families.get(mask_type)
        if not isinstance(raw, Mapping):
            errors.append(f"families.{mask_type} must be a mapping")
            continue
        if raw.get("index") != index:
            errors.append(f"families.{mask_type}.index must equal {index}")
        try:
            lower = float(raw["lower_damaged_content_fraction"])
            target = float(raw["target_damaged_content_fraction"])
            upper = float(raw["upper_damaged_content_fraction"])
            if not 0.0 <= lower <= target <= upper <= 1.0:
                errors.append(f"families.{mask_type} fractions must satisfy 0 <= lower <= target <= upper <= 1")
            if mask_type == "zero_control" and (lower, target, upper) != (0.0, 0.0, 0.0):
                errors.append("families.zero_control fractions must all equal zero")
            if mask_type in ("scratch_thin", "loss_small", "loss_large") and lower < previous_upper:
                errors.append(f"families.{mask_type} lower fraction must not overlap the preceding canonical family upper fraction")
            if mask_type != "mixed_damage":
                previous_upper = upper
        except (KeyError, TypeError, ValueError):
            errors.append(f"families.{mask_type} must define numeric lower, target, and upper fractions")
        if not isinstance(raw.get("generator"), Mapping):
            errors.append(f"families.{mask_type}.generator must be a mapping")
        if not str(raw.get("preset_version", "")).strip():
            errors.append(f"families.{mask_type}.preset_version must be non-empty")
        if mask_type not in family_validation:
            errors.append(f"family_validation.{mask_type} must be defined")

    if "cross_family" not in family_validation:
        errors.append("family_validation.cross_family must be defined")
    if morphology.get("component_connectivity") != 8:
        errors.append("morphology.component_connectivity must equal 8")
    if morphology.get("perimeter_connectivity") != 4:
        errors.append("morphology.perimeter_connectivity must equal 4")
    if smoke.get("painting_count") != 1 or examples.get("painting_count") != 1:
        errors.append("smoke.painting_count and examples.painting_count must equal 1")
    exclusions = config.get("exclusions")
    if not isinstance(exclusions, Sequence) or isinstance(exclusions, (str, bytes)):
        errors.append("exclusions must be a sequence")
    else:
        required_exclusions = {"blur", "fading", "discolouration", "dirt", "stains"}
        if not required_exclusions.issubset({str(item) for item in exclusions}):
            errors.append("exclusions must explicitly include blur, fading, discolouration, dirt, and stains")
    return errors


def load_mask_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8-sig") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, Mapping):
        raise ValueError("Canonical mask configuration must contain a mapping")
    config = dict(loaded)
    errors = validate_mask_config(config)
    if errors:
        raise ValueError("Invalid canonical mask configuration: " + "; ".join(errors))
    return config


def resolve_mask_inputs(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
    *,
    must_exist: bool = True,
) -> dict[str, Path]:
    errors = validate_mask_config(config)
    if errors:
        raise ValueError("Invalid canonical mask configuration: " + "; ".join(errors))
    root = find_project_root(project_root)
    inputs = config["inputs"]
    resolved = {
        "geometry_path": resolve_repo_path(inputs["geometry_path"], root, must_exist=must_exist),
        "clean_images_path": resolve_repo_path(inputs["clean_images_path"], root, must_exist=must_exist),
        "artifacts_path": resolve_repo_path(inputs["artifacts_path"], root, must_exist=must_exist),
        "run_manifest_path": resolve_repo_path(inputs["run_manifest_path"], root, must_exist=must_exist),
    }
    if must_exist and not resolved["clean_images_path"].is_dir():
        raise NotADirectoryError(resolved["clean_images_path"])
    return resolved


def validate_preprocessed_handoff(
    preprocessed: pd.DataFrame,
    config: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    schema_result = validate_dataframe(
        preprocessed, PREPROCESSED_IMAGES_SCHEMA, allow_extra_columns=False
    )
    if not schema_result.passed or schema_result.unexpected_columns:
        errors.append(f"preprocessed_images schema failed: {schema_result.to_dict()}")
    expected_count = int(config["expected"]["painting_count"])
    if len(preprocessed) != expected_count:
        errors.append(f"preprocessed image count must equal {expected_count}")
    if "painting_id" in preprocessed and preprocessed["painting_id"].duplicated().any():
        errors.append("preprocessed painting IDs must be unique")
    if {"width", "height"}.issubset(preprocessed.columns):
        if not (
            preprocessed["width"].eq(int(config["generator"]["target_width"])).all()
            and preprocessed["height"].eq(int(config["generator"]["target_height"])).all()
        ):
            errors.append("preprocessed images must match the configured 768 x 768 canvas")
    if "status" in preprocessed and not preprocessed["status"].eq("passed").all():
        errors.append("all preprocessed images must have passed status")
    return errors


def select_representative_row(
    preprocessed: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select one rule-based row nearest the median content-area fraction."""
    errors = validate_preprocessed_handoff(preprocessed, config)
    if errors:
        raise ValueError("Invalid preprocessing handoff: " + "; ".join(errors))
    frame = preprocessed.copy()
    median = float(frame["content_area_fraction"].median())
    frame["_distance"] = (frame["content_area_fraction"].astype(float) - median).abs()
    return (
        frame.sort_values(
            ["_distance", "dataset_sort_index", "painting_id"], kind="stable"
        )
        .head(1)
        .drop(columns="_distance")
        .reset_index(drop=True)
    )


def _legacy_family_parameters(mask_type: str) -> dict[str, Any]:
    if mask_type == "zero_control":
        return {"primitive": "empty"}
    if mask_type == "scratch_thin":
        return {
            "primitive": "polyline_scratch", "line_count_min": 8, "line_count_max": 16,
            "line_width_min": 2, "line_width_max": 5, "segment_count_min": 3,
            "segment_count_max": 6, "step_length_min": 40, "step_length_max": 120,
            "angle_jitter_std_radians": 0.45, "blur_radius": 0.4, "binary_threshold": 35,
        }
    if mask_type == "loss_small":
        return {
            "primitive": "irregular_blobs", "blob_count_min": 4, "blob_count_max": 8,
            "radius_min": 18, "radius_max": 45, "polygon_points_min": 9,
            "polygon_points_max": 16, "blur_radius": 1.5, "binary_threshold": 80,
        }
    if mask_type == "loss_large":
        return {
            "primitive": "irregular_blobs", "blob_count_min": 1, "blob_count_max": 2,
            "radius_min": 85, "radius_max": 155, "polygon_points_min": 14,
            "polygon_points_max": 24, "blur_radius": 2.5, "binary_threshold": 80,
        }
    return {
        "primitive": "mixed_union",
        "scratch": {
            "line_count_min": 5, "line_count_max": 11, "line_width_min": 2,
            "line_width_max": 5, "segment_count_min": 3, "segment_count_max": 6,
            "step_length_min": 40, "step_length_max": 120,
            "angle_jitter_std_radians": 0.45, "blur_radius": 0.4,
            "binary_threshold": 35,
        },
        "small_loss": {
            "blob_count_min": 3, "blob_count_max": 6, "radius_min": 16,
            "radius_max": 38, "polygon_points_min": 8, "polygon_points_max": 15,
            "blur_radius": 1.4, "binary_threshold": 80,
        },
        "medium_loss": {
            "blob_count_min": 1, "blob_count_max": 1, "radius_min": 55,
            "radius_max": 115, "polygon_points_min": 12, "polygon_points_max": 22,
            "blur_radius": 2.2, "binary_threshold": 80,
        },
        "edge_loss": {
            "radius_min": 28, "radius_max": 70, "polygon_points_min": 10,
            "polygon_points_max": 17, "blur_radius": 2.0, "binary_threshold": 80,
        },
    }


def _content_mask(target_size: int, content_box: Sequence[int]) -> np.ndarray:
    region = content_region((target_size, target_size), content_box)
    if region.validity_status != "valid":
        raise ValueError(f"Invalid content region: {content_box}")
    return region.mask


def _binary_array(mask: Image.Image) -> np.ndarray:
    return np.asarray(mask.convert("L")) > 0


def _binary_mask(mask: Image.Image) -> Image.Image:
    return Image.fromarray(np.where(_binary_array(mask), 255, 0).astype(np.uint8), mode="L")


def _clip_to_content(
    mask: Image.Image,
    target_size: int,
    content_box: Sequence[int],
) -> Image.Image:
    clipped = _binary_array(mask) & _content_mask(target_size, content_box)
    return Image.fromarray(np.where(clipped, 255, 0).astype(np.uint8), mode="L")


def _random_point(
    rng: np.random.Generator,
    content_box: Sequence[int],
    margin: int = 0,
) -> tuple[int, int]:
    x_min, y_min, x_max, y_max = (int(value) for value in content_box)
    width, height = x_max - x_min, y_max - y_min
    safe = max(0, min(int(margin), max(0, (width - 1) // 2), max(0, (height - 1) // 2)))
    left, right = x_min + safe, x_max - safe
    top, bottom = y_min + safe, y_max - safe
    if left >= right:
        left, right = x_min, x_max
    if top >= bottom:
        top, bottom = y_min, y_max
    return int(rng.integers(left, right)), int(rng.integers(top, bottom))


def _draw_blob(
    draw: ImageDraw.ImageDraw,
    rng: np.random.Generator,
    center: tuple[int, int],
    radius_min: int,
    radius_max: int,
    point_count: int,
    jitter_fraction: float,
) -> None:
    angles = np.sort(rng.uniform(0.0, 2.0 * np.pi, size=point_count))
    points: list[tuple[int, int]] = []
    for angle in angles:
        radius = float(rng.uniform(radius_min, radius_max))
        jitter = max(1.0, radius * float(jitter_fraction))
        points.append(
            (
                int(round(center[0] + radius * np.cos(angle) + rng.normal(0.0, jitter))),
                int(round(center[1] + radius * np.sin(angle) + rng.normal(0.0, jitter))),
            )
        )
    draw.polygon(points, fill=255)


def _scratch(
    rng: np.random.Generator,
    target_size: int,
    content_box: Sequence[int],
    parameters: Mapping[str, Any],
) -> tuple[Image.Image, dict[str, Any]]:
    mask = Image.new("L", (target_size, target_size), 0)
    draw = ImageDraw.Draw(mask)
    line_count = int(rng.integers(int(parameters["line_count_min"]), int(parameters["line_count_max"]) + 1))
    x_min, y_min, x_max, y_max = (int(value) for value in content_box)
    realized_lines: list[dict[str, int]] = []
    for _ in range(line_count):
        x, y = _random_point(rng, content_box)
        points = [(x, y)]
        angle = float(rng.uniform(0.0, 2.0 * np.pi))
        segments = int(rng.integers(int(parameters["segment_count_min"]), int(parameters["segment_count_max"]) + 1))
        for _segment in range(segments):
            angle += float(rng.normal(0.0, float(parameters["angle_jitter_std_radians"])))
            step = int(rng.integers(int(parameters["step_length_min"]), int(parameters["step_length_max"]) + 1))
            x = int(np.clip(x + step * np.cos(angle), x_min, x_max - 1))
            y = int(np.clip(y + step * np.sin(angle), y_min, y_max - 1))
            points.append((x, y))
        width = int(rng.integers(int(parameters["line_width_min"]), int(parameters["line_width_max"]) + 1))
        draw.line(points, fill=255, width=width, joint="curve")
        realized_lines.append({"segments": segments, "width": width})
    blur = float(parameters["blur_radius"])
    if blur > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=blur))
    threshold = int(parameters["binary_threshold"])
    mask = mask.point(lambda pixel: 255 if pixel > threshold else 0)
    return _clip_to_content(_binary_mask(mask), target_size, content_box), {
        "line_count": line_count, "lines": realized_lines
    }


def _blobs(
    rng: np.random.Generator,
    target_size: int,
    content_box: Sequence[int],
    parameters: Mapping[str, Any],
    jitter_fraction: float,
) -> tuple[Image.Image, dict[str, Any]]:
    mask = Image.new("L", (target_size, target_size), 0)
    draw = ImageDraw.Draw(mask)
    count = int(rng.integers(int(parameters["blob_count_min"]), int(parameters["blob_count_max"]) + 1))
    point_counts: list[int] = []
    for _ in range(count):
        center = _random_point(rng, content_box, margin=int(parameters["radius_max"]))
        point_count = int(rng.integers(int(parameters["polygon_points_min"]), int(parameters["polygon_points_max"]) + 1))
        _draw_blob(
            draw, rng, center, int(parameters["radius_min"]), int(parameters["radius_max"]),
            point_count, jitter_fraction,
        )
        point_counts.append(point_count)
    blur = float(parameters["blur_radius"])
    if blur > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=blur))
    threshold = int(parameters["binary_threshold"])
    mask = mask.point(lambda pixel: 255 if pixel > threshold else 0)
    return _clip_to_content(_binary_mask(mask), target_size, content_box), {
        "blob_count": count, "polygon_point_counts": point_counts
    }


def _edge_loss(
    rng: np.random.Generator,
    target_size: int,
    content_box: Sequence[int],
    parameters: Mapping[str, Any],
    jitter_fraction: float,
) -> tuple[Image.Image, dict[str, Any]]:
    x_min, y_min, x_max, y_max = (int(value) for value in content_box)
    radius_max = int(parameters["radius_max"])
    side = str(rng.choice(["left", "right", "top", "bottom"]))
    if side == "left":
        center = (x_min + int(rng.integers(0, radius_max + 1)), int(rng.integers(y_min, y_max)))
    elif side == "right":
        center = (x_max - 1 - int(rng.integers(0, radius_max + 1)), int(rng.integers(y_min, y_max)))
    elif side == "top":
        center = (int(rng.integers(x_min, x_max)), y_min + int(rng.integers(0, radius_max + 1)))
    else:
        center = (int(rng.integers(x_min, x_max)), y_max - 1 - int(rng.integers(0, radius_max + 1)))
    mask = Image.new("L", (target_size, target_size), 0)
    draw = ImageDraw.Draw(mask)
    point_count = int(rng.integers(int(parameters["polygon_points_min"]), int(parameters["polygon_points_max"]) + 1))
    _draw_blob(
        draw, rng, center, int(parameters["radius_min"]), radius_max,
        point_count, jitter_fraction,
    )
    blur = float(parameters["blur_radius"])
    if blur > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=blur))
    threshold = int(parameters["binary_threshold"])
    mask = mask.point(lambda pixel: 255 if pixel > threshold else 0)
    return _clip_to_content(_binary_mask(mask), target_size, content_box), {
        "side": side, "polygon_point_count": point_count
    }


def _generate_mask_with_parameters(
    mask_type: str,
    rng: np.random.Generator,
    target_size: int,
    content_box: Sequence[int],
    parameters: Mapping[str, Any],
    morphology_settings: Mapping[str, Any] | None = None,
) -> tuple[Image.Image, dict[str, Any]]:
    if mask_type not in SUPPORTED_MASK_TYPES:
        raise ValueError(f"Unsupported mask type: {mask_type}")
    jitter = float((morphology_settings or {}).get("irregular_blob_radius_jitter_fraction", 0.12))
    primitive = str(parameters.get("primitive", ""))
    if mask_type == "zero_control" or primitive == "empty":
        return Image.new("L", (target_size, target_size), 0), {"primitive": "empty"}
    if primitive == "polyline_scratch":
        image, realized = _scratch(rng, target_size, content_box, parameters)
        return image, {"primitive": primitive, **realized}
    if primitive == "irregular_blobs":
        image, realized = _blobs(rng, target_size, content_box, parameters, jitter)
        return image, {"primitive": primitive, **realized}
    if primitive != "mixed_union":
        raise ValueError(f"Unsupported primitive for {mask_type}: {primitive}")
    scratch, scratch_realized = _scratch(rng, target_size, content_box, parameters["scratch"])
    small, small_realized = _blobs(rng, target_size, content_box, parameters["small_loss"], jitter)
    medium, medium_realized = _blobs(rng, target_size, content_box, parameters["medium_loss"], jitter)
    edge, edge_realized = _edge_loss(rng, target_size, content_box, parameters["edge_loss"], jitter)
    combined = np.logical_or.reduce([
        _binary_array(scratch), _binary_array(small), _binary_array(medium), _binary_array(edge)
    ])
    image = Image.fromarray(np.where(combined, 255, 0).astype(np.uint8), mode="L")
    return _clip_to_content(image, target_size, content_box), {
        "primitive": primitive,
        "scratch": scratch_realized,
        "small_loss": small_realized,
        "medium_loss": medium_realized,
        "edge_loss": edge_realized,
    }


def generate_mask_by_type(
    mask_type: str,
    rng: np.random.Generator,
    target_size: int,
    content_box: tuple[int, int, int, int],
    parameters: Mapping[str, Any] | None = None,
    morphology_settings: Mapping[str, Any] | None = None,
) -> Image.Image:
    """Compatibility-safe public family generator."""
    effective = _legacy_family_parameters(mask_type) if parameters is None else parameters
    image, _ = _generate_mask_with_parameters(
        mask_type, rng, int(target_size), content_box, effective, morphology_settings
    )
    return image


def _connected_components(binary: np.ndarray) -> list[dict[str, int]]:
    height, width = binary.shape
    visited = np.zeros_like(binary, dtype=bool)
    components: list[dict[str, int]] = []
    for start_y, start_x in zip(*np.nonzero(binary)):
        if visited[start_y, start_x]:
            continue
        queue: deque[tuple[int, int]] = deque([(int(start_y), int(start_x))])
        visited[start_y, start_x] = True
        xs: list[int] = []
        ys: list[int] = []
        while queue:
            y, x = queue.popleft()
            xs.append(x)
            ys.append(y)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < height and 0 <= nx < width and binary[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        queue.append((ny, nx))
        x_min, x_max = min(xs), max(xs) + 1
        y_min, y_max = min(ys), max(ys) + 1
        components.append({
            "area_pixels": len(xs), "bbox_width": x_max - x_min,
            "bbox_height": y_max - y_min,
        })
    return components


def _grid_perimeter(binary: np.ndarray) -> int:
    padded = np.pad(binary.astype(np.int8), 1, mode="constant")
    vertical = np.abs(np.diff(padded, axis=0)).sum(dtype=np.int64)
    horizontal = np.abs(np.diff(padded, axis=1)).sum(dtype=np.int64)
    return int(vertical + horizontal)


def _touches_boundary(binary: np.ndarray, content_box: Sequence[int]) -> bool:
    if not binary.any():
        return False
    x_min, y_min, x_max, y_max = (int(value) for value in content_box)
    return bool(
        binary[y_min, x_min:x_max].any()
        or binary[y_max - 1, x_min:x_max].any()
        or binary[y_min:y_max, x_min].any()
        or binary[y_min:y_max, x_max - 1].any()
    )


def _distance_to_boundary(binary: np.ndarray, content_box: Sequence[int]) -> int:
    ys, xs = np.nonzero(binary)
    if not len(xs):
        return -1
    x_min, y_min, x_max, y_max = (int(value) for value in content_box)
    return int(np.minimum.reduce([xs - x_min, (x_max - 1) - xs, ys - y_min, (y_max - 1) - ys]).min())


def calculate_mask_morphology(
    mask: Image.Image | np.ndarray,
    *,
    content_box: Sequence[int],
) -> dict[str, Any]:
    """Calculate deterministic area, component, perimeter, and support evidence."""
    array = _binary_array(mask) if isinstance(mask, Image.Image) else np.asarray(mask) > 0
    if array.ndim != 2:
        raise ValueError("Mask morphology requires a two-dimensional array")
    height, width = array.shape
    content = content_region((height, width), content_box)
    content_pixels = int(content.pixel_count)
    canvas_pixels = int(height * width)
    damaged_pixels = int(array.sum())
    damaged_content = int((array & content.mask).sum())
    padding_overlap = int((array & ~content.mask).sum())
    bbox = mask_bbox(array) or (0, 0, 0, 0)
    bbox_width = int(bbox[2] - bbox[0])
    bbox_height = int(bbox[3] - bbox[1])
    bbox_area = int(bbox_width * bbox_height)
    components = _connected_components(array)
    areas = np.asarray([item["area_pixels"] for item in components], dtype=float)
    aspects = np.asarray([
        max(item["bbox_width"], item["bbox_height"]) / max(1, min(item["bbox_width"], item["bbox_height"]))
        for item in components
    ], dtype=float)
    count = len(components)
    mean_area = float(areas.mean()) if count else 0.0
    std_area = float(areas.std(ddof=0)) if count else 0.0
    perimeter = _grid_perimeter(array)
    compactness = (4.0 * math.pi * damaged_pixels / (perimeter**2)) if perimeter else 0.0
    return {
        "content_width": int(content.width),
        "content_height": int(content.height),
        "content_area_pixels": content_pixels,
        "padding_area_pixels": canvas_pixels - content_pixels,
        "canvas_area_pixels": canvas_pixels,
        "damaged_pixel_count": damaged_pixels,
        "damaged_content_pixel_count": damaged_content,
        "padding_overlap_pixels": padding_overlap,
        "damaged_content_fraction": round(damaged_content / content_pixels, 9),
        "damaged_full_fraction": round(damaged_pixels / canvas_pixels, 9),
        "bbox_x_min": int(bbox[0]), "bbox_y_min": int(bbox[1]),
        "bbox_x_max": int(bbox[2]), "bbox_y_max": int(bbox[3]),
        "bbox_width": bbox_width, "bbox_height": bbox_height,
        "bbox_area_pixels": bbox_area,
        "bbox_fill_ratio": round(damaged_pixels / bbox_area, 9) if bbox_area else 0.0,
        "bbox_aspect_ratio": round(max(bbox_width, bbox_height) / max(1, min(bbox_width, bbox_height)), 9) if bbox_area else 0.0,
        "connected_component_count": count,
        "largest_component_pixels": int(areas.max()) if count else 0,
        "smallest_component_pixels": int(areas.min()) if count else 0,
        "mean_component_pixels": round(mean_area, 9),
        "median_component_pixels": round(float(np.median(areas)), 9) if count else 0.0,
        "component_area_std_pixels": round(std_area, 9),
        "component_area_cv": round(std_area / mean_area, 9) if mean_area else 0.0,
        "largest_component_fraction": round(float(areas.max()) / damaged_pixels, 9) if damaged_pixels else 0.0,
        "component_density_per_100k_content_pixels": round(count / content_pixels * 100000.0, 9),
        "mean_component_aspect_ratio": round(float(aspects.mean()), 9) if count else 0.0,
        "maximum_component_aspect_ratio": round(float(aspects.max()), 9) if count else 0.0,
        "mask_perimeter_pixels": perimeter,
        "mask_compactness": round(compactness, 9),
        "touches_content_boundary": _touches_boundary(array, content_box),
        "minimum_distance_to_content_boundary_pixels": _distance_to_boundary(array, content_box),
    }


def _mask_morphology_metadata(
    mask: Image.Image,
    target_size: int,
    content_box: tuple[int, int, int, int],
) -> dict[str, Any]:
    """Legacy morphology-key wrapper retained for mask_robustness.py."""
    current = calculate_mask_morphology(mask, content_box=content_box)
    return {
        "canvas_area_pixels": current["canvas_area_pixels"],
        "content_area_pixels": current["content_area_pixels"],
        "padding_area_pixels": current["padding_area_pixels"],
        "actual_mask_area_pixels": current["damaged_pixel_count"],
        "damaged_content_pixels": current["damaged_content_pixel_count"],
        "padding_overlap_pixels": current["padding_overlap_pixels"],
        "actual_mask_area_percentage_content": current["damaged_content_fraction"] * 100.0,
        "actual_mask_area_percentage_full": current["damaged_full_fraction"] * 100.0,
        "bbox_x_min": current["bbox_x_min"], "bbox_y_min": current["bbox_y_min"],
        "bbox_x_max": current["bbox_x_max"], "bbox_y_max": current["bbox_y_max"],
        "bbox_width": current["bbox_width"], "bbox_height": current["bbox_height"],
        "bbox_area_pixels": current["bbox_area_pixels"],
        "bbox_fill_ratio": current["bbox_fill_ratio"],
        "bbox_aspect_ratio": current["bbox_aspect_ratio"],
        "connected_component_count": current["connected_component_count"],
        "largest_component_pixels": current["largest_component_pixels"],
        "smallest_component_pixels": current["smallest_component_pixels"],
        "mean_component_pixels": current["mean_component_pixels"],
        "median_component_pixels": current["median_component_pixels"],
        "component_area_std_pixels": current["component_area_std_pixels"],
        "largest_component_fraction": current["largest_component_fraction"],
        "component_density_per_100k_content_pixels": current["component_density_per_100k_content_pixels"],
        "mean_component_aspect_ratio": current["mean_component_aspect_ratio"],
        "maximum_component_aspect_ratio": current["maximum_component_aspect_ratio"],
        "touches_content_border": current["touches_content_boundary"],
        "minimum_distance_to_content_border_pixels": (
            None if current["minimum_distance_to_content_boundary_pixels"] < 0
            else current["minimum_distance_to_content_boundary_pixels"]
        ),
        "mask_perimeter_pixels": current["mask_perimeter_pixels"],
        "mask_compactness": current["mask_compactness"],
        "component_area_cv": current["component_area_cv"],
    }


def _generate_with_retry(
    mask_type: str,
    mask_seed: int,
    target_size: int,
    content_box: Sequence[int],
    family: Mapping[str, Any],
    config: Mapping[str, Any],
) -> tuple[Image.Image, dict[str, Any]]:
    lower = float(family["lower_damaged_content_fraction"])
    target = float(family["target_damaged_content_fraction"])
    upper = float(family["upper_damaged_content_fraction"])
    maximum = int(config["generator"]["maximum_generation_attempts"])
    best: tuple[Image.Image, dict[str, Any], float, float] | None = None
    for attempt in range(1, maximum + 1):
        retry_seed = stable_seed(mask_seed, mask_type, attempt)
        image, realized = _generate_mask_with_parameters(
            mask_type,
            np.random.default_rng(retry_seed),
            target_size,
            content_box,
            family["generator"],
            config["morphology"],
        )
        morphology = calculate_mask_morphology(image, content_box=content_box)
        fraction = float(morphology["damaged_content_fraction"])
        target_distance = abs(fraction - target)
        range_distance = lower - fraction if fraction < lower else fraction - upper if fraction > upper else 0.0
        metadata = {
            "retry_seed": int(retry_seed), "generation_attempts": attempt,
            "accepted_attempt": attempt, "distance_to_target_fraction": round(target_distance, 9),
            "distance_to_allowed_range_fraction": round(range_distance, 9),
            "realized_generator_parameters": realized,
        }
        if best is None or range_distance < best[3] or (
            np.isclose(range_distance, best[3]) and target_distance < best[2]
        ):
            best = (image, metadata, target_distance, range_distance)
        if range_distance == 0.0:
            return image, metadata
    if best is None:
        raise RuntimeError(f"No candidate generated for {mask_type}")
    raise RuntimeError(
        f"{mask_type} did not reach [{lower}, {upper}] after {maximum} attempts; "
        f"closest range distance={best[3]:.9f}"
    )


def generate_mask_case(
    preprocessed_row: Mapping[str, Any] | pd.Series,
    mask_type: str,
    config: Mapping[str, Any],
) -> MaskCaseResult:
    """Generate one deterministic in-memory canonical mask case."""
    if mask_type not in SUPPORTED_MASK_TYPES:
        raise ValueError(f"Unsupported mask type: {mask_type}")
    row = dict(preprocessed_row)
    family = config["families"][mask_type]
    painting_id = str(row["painting_id"])
    content_box = (
        int(row["content_x_min"]), int(row["content_y_min"]),
        int(row["content_x_max"]), int(row["content_y_max"]),
    )
    target_size = int(config["generator"]["target_width"])
    global_seed = int(config["generator"]["global_seed"])
    painting_seed = stable_seed(
        global_seed, config["dataset"]["experiment_id"], config["config_version"], painting_id
    )
    mask_seed = stable_seed(painting_seed, mask_type, int(family["index"]))
    image, retry = _generate_with_retry(
        mask_type, mask_seed, target_size, content_box, family, config
    )
    morphology = calculate_mask_morphology(image, content_box=content_box)
    fraction = float(morphology["damaged_content_fraction"])
    lower = float(family["lower_damaged_content_fraction"])
    upper = float(family["upper_damaged_content_fraction"])
    unique_values = sorted(np.unique(np.asarray(image, dtype=np.uint8)).astype(int).tolist())
    zero_valid = morphology["damaged_pixel_count"] == 0 if mask_type == "zero_control" else morphology["damaged_pixel_count"] > 0
    record = {
        "case_id": f"canonical__{painting_id}__{mask_type}",
        "painting_id": painting_id,
        "mask_id": f"mask__canonical__{painting_id}__{mask_type}",
        "mask_type": mask_type,
        "mask_type_index": int(family["index"]),
        "generator_name": GENERATOR_NAME,
        "generator_version": GENERATOR_VERSION,
        "config_schema_version": CANONICAL_MASK_CONFIG_SCHEMA_VERSION,
        "config_version": str(config["config_version"]),
        "preset_id": f"canonical::{mask_type}::{family['preset_version']}",
        "preset_version": str(family["preset_version"]),
        "seed_scheme_version": str(config["generator"]["seed_scheme_version"]),
        "global_seed": global_seed,
        "painting_seed": int(painting_seed),
        "mask_seed": int(mask_seed),
        "retry_seed": int(retry["retry_seed"]),
        "maximum_generation_attempts": int(config["generator"]["maximum_generation_attempts"]),
        "generation_attempts": int(retry["generation_attempts"]),
        "accepted_attempt": int(retry["accepted_attempt"]),
        "retry_policy": str(config["generator"]["retry_policy"]),
        "target_damaged_content_fraction": float(family["target_damaged_content_fraction"]),
        "lower_damaged_content_fraction": lower,
        "upper_damaged_content_fraction": upper,
        "distance_to_target_fraction": float(retry["distance_to_target_fraction"]),
        "distance_to_allowed_range_fraction": float(retry["distance_to_allowed_range_fraction"]),
        "generator_parameters": _json({
            "configured": family["generator"],
            "realized": retry["realized_generator_parameters"],
        }),
        "morphology_settings": _json(config["morphology"]),
        "content_x_min": content_box[0], "content_y_min": content_box[1],
        "content_x_max": content_box[2], "content_y_max": content_box[3],
        **morphology,
        "mask_unique_values": "|".join(str(value) for value in unique_values),
        "binary_values_valid": set(unique_values).issubset({0, 255}),
        "zero_control_rule_valid": bool(zero_valid),
        "content_only_valid": morphology["padding_overlap_pixels"] == 0,
        "area_within_target_tolerance": lower <= fraction <= upper,
    }
    return MaskCaseResult(image=image, record=record)


def evaluate_family_morphology(
    masks: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Evaluate the five configured family-level morphology expectations."""
    grouped = {name: masks.loc[masks["mask_type"].eq(name)] for name in SUPPORTED_MASK_TYPES}
    rules = config["family_validation"]
    rows: list[dict[str, Any]] = []
    zero = grouped["zero_control"]
    zero_passed = bool(
        zero["damaged_pixel_count"].eq(int(rules["zero_control"]["damaged_pixel_count"])).all()
        and zero["connected_component_count"].eq(int(rules["zero_control"]["connected_component_count"])).all()
    )
    rows.append({"mask_type": "zero_control", "rule_id": "zero_control_empty", "expected": rules["zero_control"], "observed": {"maximum_pixels": int(zero["damaged_pixel_count"].max()), "maximum_components": int(zero["connected_component_count"].max())}, "passed": zero_passed})

    scratch = grouped["scratch_thin"]
    scratch_observed = {
        "median_bbox_fill_ratio": float(scratch["bbox_fill_ratio"].median()),
        "median_maximum_component_aspect_ratio": float(scratch["maximum_component_aspect_ratio"].median()),
    }
    scratch_passed = bool(
        scratch_observed["median_bbox_fill_ratio"] <= float(rules["scratch_thin"]["maximum_median_bbox_fill_ratio"])
        and scratch_observed["median_maximum_component_aspect_ratio"] >= float(rules["scratch_thin"]["minimum_median_maximum_component_aspect_ratio"])
    )
    rows.append({"mask_type": "scratch_thin", "rule_id": "scratch_thin_elongated", "expected": rules["scratch_thin"], "observed": scratch_observed, "passed": scratch_passed})

    small = grouped["loss_small"]
    small_observed = {"median_connected_component_count": float(small["connected_component_count"].median())}
    small_passed = small_observed["median_connected_component_count"] >= float(rules["loss_small"]["minimum_median_connected_component_count"])
    rows.append({"mask_type": "loss_small", "rule_id": "loss_small_multicomponent", "expected": rules["loss_small"], "observed": small_observed, "passed": bool(small_passed)})

    large = grouped["loss_large"]
    small_median = float(small["damaged_content_fraction"].median())
    large_observed = {
        "median_fraction_ratio_to_loss_small": float(large["damaged_content_fraction"].median()) / small_median,
        "median_largest_component_fraction": float(large["largest_component_fraction"].median()),
    }
    large_passed = bool(
        large_observed["median_fraction_ratio_to_loss_small"] >= float(rules["loss_large"]["minimum_median_fraction_ratio_to_loss_small"])
        and large_observed["median_largest_component_fraction"] >= float(rules["loss_large"]["minimum_median_largest_component_fraction"])
    )
    rows.append({"mask_type": "loss_large", "rule_id": "loss_large_substantially_larger", "expected": rules["loss_large"], "observed": large_observed, "passed": large_passed})

    mixed = grouped["mixed_damage"]
    mixed_observed = {
        "median_connected_component_count": float(mixed["connected_component_count"].median()),
        "boundary_touch_fraction": float(mixed["touches_content_boundary"].astype(float).mean()),
        "median_maximum_component_aspect_ratio": float(mixed["maximum_component_aspect_ratio"].median()),
    }
    mixed_passed = bool(
        mixed_observed["median_connected_component_count"] >= float(rules["mixed_damage"]["minimum_median_connected_component_count"])
        and mixed_observed["boundary_touch_fraction"] >= float(rules["mixed_damage"]["minimum_boundary_touch_fraction"])
        and mixed_observed["median_maximum_component_aspect_ratio"] >= float(rules["mixed_damage"]["minimum_median_maximum_component_aspect_ratio"])
    )
    rows.append({"mask_type": "mixed_damage", "rule_id": "mixed_damage_combined_characteristics", "expected": rules["mixed_damage"], "observed": mixed_observed, "passed": mixed_passed})
    result = pd.DataFrame(rows)
    result["details"] = result.apply(lambda row: _json({"expected": row["expected"], "observed": row["observed"]}), axis=1)
    return result


def _save_png_atomic(image: Image.Image, path: Path, config: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        image.save(
            temporary,
            format="PNG",
            optimize=bool(config["generator"]["png_optimize"]),
            compress_level=int(config["generator"]["png_compress_level"]),
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def generate_masks_for_dataset(
    preprocessed: pd.DataFrame,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> MaskGenerationResult:
    """Generate and atomically persist the complete controlled-50 mask set."""
    config_errors = validate_mask_config(config)
    handoff_errors = validate_preprocessed_handoff(preprocessed, config)
    if config_errors or handoff_errors:
        raise ValueError("Invalid mask generation contract: " + "; ".join(config_errors + handoff_errors))
    root = find_project_root(project_root)
    output_root = notebook_output_root(config["output"]["notebook_stem"], root)
    image_root = require_notebook_output_path(
        output_root / str(config["output"]["image_directory"]),
        str(config["output"]["notebook_stem"]), root,
    )
    records: list[dict[str, Any]] = []
    runtimes: list[dict[str, Any]] = []
    ordered = preprocessed.sort_values(["dataset_sort_index", "painting_id"], kind="stable")
    for row in ordered.to_dict(orient="records"):
        for mask_type in SUPPORTED_MASK_TYPES:
            started = time.perf_counter()
            case = generate_mask_case(row, mask_type, config)
            relative_template = str(config["output"]["image_path_template"]).format(
                painting_id=row["painting_id"], mask_type=mask_type
            )
            output_path = require_notebook_output_path(
                image_root / relative_template,
                str(config["output"]["notebook_stem"]), root,
            )
            _save_png_atomic(case.image, output_path, config)
            with Image.open(output_path) as reloaded:
                reloaded.load()
                unique = sorted(np.unique(np.asarray(reloaded, dtype=np.uint8)).astype(int).tolist())
                if reloaded.size != (768, 768) or reloaded.mode != "L" or reloaded.format != "PNG":
                    raise RuntimeError(f"Saved mask technical contract failed: {output_path}")
                if not set(unique).issubset({0, 255}):
                    raise RuntimeError(f"Saved mask is not binary: {output_path}")
            record = {
                "dataset_id": str(row["dataset_id"]),
                "dataset_version": str(row["dataset_version"]),
                "dataset_scope": str(row["dataset_scope"]),
                "experiment_id": str(config["dataset"]["experiment_id"]),
                "processed_image_id": str(row["processed_image_id"]),
                "processed_image_path": str(row["processed_path"]),
                "processed_image_sha256": str(row["sha256"]),
                **case.record,
                "mask_filename": output_path.name,
                "mask_path": to_repo_relative(output_path, root),
                "mask_width": 768,
                "mask_height": 768,
                "mask_mode": "L",
                "mask_format": "PNG",
                "mask_size_bytes": int(output_path.stat().st_size),
                "mask_sha256": _sha256_file(output_path),
                "morphology_status": "pending",
                "generation_status": "passed",
                "status": "passed",
                "issue": "",
            }
            records.append(record)
            runtimes.append({"mask_id": record["mask_id"], "runtime_seconds": time.perf_counter() - started})
    masks = pd.DataFrame(records)
    family_validation = evaluate_family_morphology(masks, config)
    if not family_validation["passed"].all():
        failed = family_validation.loc[~family_validation["passed"], ["mask_type", "details"]].to_dict("records")
        raise RuntimeError(f"Family morphology validation failed: {failed}")
    masks["morphology_status"] = "passed"
    masks = masks.loc[:, CANONICAL_MASKS_COLUMNS]
    schema_result = validate_dataframe(masks, CANONICAL_MASKS_SCHEMA, allow_extra_columns=False)
    if not schema_result.passed or schema_result.unexpected_columns:
        raise RuntimeError(f"Canonical masks violate schema: {schema_result.to_dict()}")
    if len(masks) != int(config["expected"]["mask_count"]):
        raise RuntimeError("Canonical mask count does not match configuration")
    return MaskGenerationResult(
        masks=masks,
        runtimes=pd.DataFrame(runtimes, columns=RUNTIME_COLUMNS),
        family_validation=family_validation,
    )


def validate_saved_masks(
    masks: pd.DataFrame,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> MaskValidationResult:
    """Reload and reconcile every saved mask plus the exact image file set."""
    root = find_project_root(project_root)
    image_root = require_notebook_output_path(
        notebook_output_root(config["output"]["notebook_stem"], root)
        / str(config["output"]["image_directory"]),
        str(config["output"]["notebook_stem"]), root,
    )
    checks: list[dict[str, Any]] = []
    for row in masks.to_dict(orient="records"):
        issues: list[str] = []
        path = resolve_repo_path(row["mask_path"], root, must_exist=False)
        file_exists = path.is_file()
        observed_sha = ""
        morphology: dict[str, Any] = {}
        mode = format_name = ""
        width = height = 0
        unique_values: list[int] = []
        if not file_exists:
            issues.append("missing_mask_file")
        else:
            try:
                with Image.open(path) as image:
                    image.load()
                    mode, format_name = str(image.mode), str(image.format)
                    width, height = image.size
                    unique_values = sorted(np.unique(np.asarray(image, dtype=np.uint8)).astype(int).tolist())
                    morphology = calculate_mask_morphology(
                        image,
                        content_box=(row["content_x_min"], row["content_y_min"], row["content_x_max"], row["content_y_max"]),
                    )
                observed_sha = _sha256_file(path)
            except (UnidentifiedImageError, OSError, ValueError) as exc:
                issues.append(f"reload_failure:{type(exc).__name__}:{exc}")
        comparisons = {
            "checksum_mismatch": observed_sha == str(row["mask_sha256"]),
            "width_nonconforming": width == int(row["mask_width"]),
            "height_nonconforming": height == int(row["mask_height"]),
            "mode_nonconforming": mode == "L",
            "format_nonconforming": format_name == "PNG",
            "nonbinary_mask": set(unique_values).issubset({0, 255}),
        }
        for issue_name, passed in comparisons.items():
            if file_exists and not passed:
                issues.append(issue_name)
        morphology_fields = (
            "damaged_pixel_count", "damaged_content_pixel_count", "padding_overlap_pixels",
            "damaged_content_fraction", "damaged_full_fraction", "bbox_x_min", "bbox_y_min",
            "bbox_x_max", "bbox_y_max", "connected_component_count", "mask_perimeter_pixels",
            "mask_compactness", "touches_content_boundary",
            "minimum_distance_to_content_boundary_pixels",
        )
        morphology_match = bool(morphology) and all(
            np.isclose(float(morphology[field]), float(row[field]), atol=1e-9)
            for field in morphology_fields
        )
        if file_exists and morphology and not morphology_match:
            issues.append("morphology_reconciliation_failure")
        fraction = float(morphology.get("damaged_content_fraction", -1.0))
        area_passed = float(row["lower_damaged_content_fraction"]) <= fraction <= float(row["upper_damaged_content_fraction"])
        zero_passed = int(morphology.get("damaged_pixel_count", -1)) == 0 if row["mask_type"] == "zero_control" else int(morphology.get("damaged_pixel_count", 0)) > 0
        content_passed = int(morphology.get("padding_overlap_pixels", -1)) == 0
        if file_exists and not area_passed:
            issues.append("area_tolerance_failure")
        if file_exists and not zero_passed:
            issues.append("zero_or_nonzero_rule_failure")
        if file_exists and not content_passed:
            issues.append("padding_overlap_failure")
        checks.append({
            "mask_id": row["mask_id"], "painting_id": row["painting_id"],
            "mask_type": row["mask_type"], "mask_path": row["mask_path"],
            "file_exists": file_exists, "reload_passed": file_exists and bool(morphology),
            "checksum_matches": comparisons["checksum_mismatch"],
            "width_matches": comparisons["width_nonconforming"],
            "height_matches": comparisons["height_nonconforming"],
            "mode_matches": comparisons["mode_nonconforming"],
            "format_matches": comparisons["format_nonconforming"],
            "binary_values_valid": comparisons["nonbinary_mask"],
            "morphology_reconciles": morphology_match,
            "area_within_target_tolerance": area_passed,
            "zero_control_rule_valid": zero_passed,
            "content_only_valid": content_passed,
            "issue": "|".join(issues),
            "validation_passed": not issues,
        })
    checks_df = pd.DataFrame(checks)
    expected_paths = {resolve_repo_path(value, root, must_exist=False).resolve() for value in masks["mask_path"].astype(str)}
    actual_paths = {path.resolve() for path in image_root.rglob("*.png") if path.is_file()} if image_root.exists() else set()
    orphan_paths = tuple(sorted(to_repo_relative(path, root) for path in actual_paths - expected_paths))
    nonzero = masks.loc[~masks["mask_type"].eq("zero_control")]
    duplicate_groups = tuple(
        tuple(sorted(group["mask_id"].astype(str)))
        for _, group in nonzero.groupby("mask_sha256", sort=True)
        if len(group) > 1
    )
    cross_pairs: list[tuple[str, str, str]] = []
    for painting_id, group in masks.groupby("painting_id", sort=True):
        for left, right in combinations(group.to_dict("records"), 2):
            if left["mask_type"] != right["mask_type"] and left["mask_sha256"] == right["mask_sha256"]:
                cross_pairs.append((str(painting_id), str(left["mask_type"]), str(right["mask_type"])))
    identity_duplicate = int(
        masks.duplicated(["case_id"], keep=False).sum()
        + masks.duplicated(["mask_id"], keep=False).sum()
        + masks.duplicated(["mask_path"], keep=False).sum()
    )
    summary = {
        "missing_mask_count": int((~checks_df["file_exists"]).sum()),
        "stale_mask_count": int((~checks_df["checksum_matches"] & checks_df["file_exists"]).sum()),
        "orphan_mask_count": len(orphan_paths),
        "duplicate_identity_group_count": identity_duplicate,
        "duplicate_nonzero_sha256_group_count": len(duplicate_groups),
        "cross_family_equivalent_pair_count": len(cross_pairs),
        "reload_failure_count": int((~checks_df["reload_passed"] & checks_df["file_exists"]).sum()),
        "width_nonconforming_count": int((~checks_df["width_matches"] & checks_df["file_exists"]).sum()),
        "height_nonconforming_count": int((~checks_df["height_matches"] & checks_df["file_exists"]).sum()),
        "mode_nonconforming_count": int((~checks_df["mode_matches"] & checks_df["file_exists"]).sum()),
        "format_nonconforming_count": int((~checks_df["format_matches"] & checks_df["file_exists"]).sum()),
        "nonbinary_mask_count": int((~checks_df["binary_values_valid"] & checks_df["file_exists"]).sum()),
        "zero_control_failure_count": int((~checks_df["zero_control_rule_valid"] & checks_df["file_exists"]).sum()),
        "empty_nonzero_mask_count": int(((~checks_df["zero_control_rule_valid"]) & checks_df["mask_type"].ne("zero_control") & checks_df["file_exists"]).sum()),
        "padding_overlap_failure_count": int((~checks_df["content_only_valid"] & checks_df["file_exists"]).sum()),
        "area_tolerance_failure_count": int((~checks_df["area_within_target_tolerance"] & checks_df["file_exists"]).sum()),
        "morphology_reconciliation_failure_count": int((~checks_df["morphology_reconciles"] & checks_df["file_exists"]).sum()),
    }
    return MaskValidationResult(
        mask_checks=checks_df, summary=summary, orphan_paths=orphan_paths,
        duplicate_nonzero_sha256_groups=duplicate_groups,
        cross_family_equivalent_pairs=tuple(cross_pairs),
    )


def validate_deterministic_replay(
    masks: pd.DataFrame,
    preprocessed: pd.DataFrame,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> pd.DataFrame:
    """Regenerate all masks in memory and compare saved pixels and seed evidence."""
    root = find_project_root(project_root)
    upstream = preprocessed.set_index("painting_id", drop=False)
    rows: list[dict[str, Any]] = []
    for stored in masks.to_dict(orient="records"):
        source = upstream.loc[str(stored["painting_id"])]
        replay = generate_mask_case(source, str(stored["mask_type"]), config)
        with Image.open(resolve_repo_path(stored["mask_path"], root, must_exist=True)) as saved:
            saved.load()
            saved_array = np.asarray(saved, dtype=np.uint8)
        replay_array = np.asarray(replay.image, dtype=np.uint8)
        pixels_equal = np.array_equal(saved_array, replay_array)
        metadata_equal = all(
            replay.record[key] == stored[key]
            for key in ("painting_seed", "mask_seed", "retry_seed", "generation_attempts", "accepted_attempt", "generator_parameters")
        )
        rows.append({
            "mask_id": stored["mask_id"], "painting_id": stored["painting_id"],
            "mask_type": stored["mask_type"], "pixels_equal": pixels_equal,
            "metadata_equal": metadata_equal,
            "saved_pixel_sha256": _pixel_sha256(saved_array),
            "replay_pixel_sha256": _pixel_sha256(replay_array),
            "replay_passed": bool(pixels_equal and metadata_equal),
        })
    return pd.DataFrame(rows)


def _pairwise_equivalence_rows(masks: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for left, right in combinations(SUPPORTED_MASK_TYPES, 2):
        left_frame = masks.loc[masks["mask_type"].eq(left), ["painting_id", "mask_sha256"]].rename(columns={"mask_sha256": "left_sha"})
        right_frame = masks.loc[masks["mask_type"].eq(right), ["painting_id", "mask_sha256"]].rename(columns={"mask_sha256": "right_sha"})
        joined = left_frame.merge(right_frame, on="painting_id", validate="one_to_one")
        count = int(joined["left_sha"].eq(joined["right_sha"]).sum())
        rows.append({"left": left, "right": right, "count": count, "denominator": len(joined)})
    return rows


def build_mask_audit(
    masks: pd.DataFrame,
    runtimes: pd.DataFrame,
    validation: MaskValidationResult,
    replay: pd.DataFrame,
    family_validation: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the exact 105-row canonical mask audit."""
    dataset = config["dataset"]
    runtime_values = pd.to_numeric(runtimes["runtime_seconds"], errors="raise")
    summary = validation.summary
    generation_failures = int(masks["generation_status"].ne("passed").sum())
    family_failures = int((~family_validation["passed"]).sum())
    replay_failures = int((~replay["replay_passed"]).sum())
    maximum_attempts = int(masks["generation_attempts"].max())
    global_specs = [
        ("accepted_input_count", int(masks["painting_id"].nunique()), "count", True),
        ("configured_family_count", len(SUPPORTED_MASK_TYPES), "count", True),
        ("expected_mask_count", int(config["expected"]["mask_count"]), "count", True),
        ("generated_mask_count", len(masks), "count", len(masks) == int(config["expected"]["mask_count"])),
        ("saved_mask_file_count", int(validation.mask_checks["file_exists"].sum()), "count", int(validation.mask_checks["file_exists"].sum()) == len(masks)),
        ("failed_generation_count", generation_failures, "count", generation_failures == 0),
        ("missing_mask_count", summary["missing_mask_count"], "count", summary["missing_mask_count"] == 0),
        ("stale_mask_count", summary["stale_mask_count"], "count", summary["stale_mask_count"] == 0),
        ("orphan_mask_count", summary["orphan_mask_count"], "count", summary["orphan_mask_count"] == 0),
        ("duplicate_identity_group_count", summary["duplicate_identity_group_count"], "count", summary["duplicate_identity_group_count"] == 0),
        ("duplicate_nonzero_sha256_group_count", summary["duplicate_nonzero_sha256_group_count"], "count", summary["duplicate_nonzero_sha256_group_count"] == 0),
        ("cross_family_equivalent_pair_count", summary["cross_family_equivalent_pair_count"], "count", summary["cross_family_equivalent_pair_count"] == 0),
        ("reload_failure_count", summary["reload_failure_count"], "count", summary["reload_failure_count"] == 0),
        ("width_nonconforming_count", summary["width_nonconforming_count"], "count", summary["width_nonconforming_count"] == 0),
        ("height_nonconforming_count", summary["height_nonconforming_count"], "count", summary["height_nonconforming_count"] == 0),
        ("mode_nonconforming_count", summary["mode_nonconforming_count"], "count", summary["mode_nonconforming_count"] == 0),
        ("format_nonconforming_count", summary["format_nonconforming_count"], "count", summary["format_nonconforming_count"] == 0),
        ("nonbinary_mask_count", summary["nonbinary_mask_count"], "count", summary["nonbinary_mask_count"] == 0),
        ("zero_control_failure_count", summary["zero_control_failure_count"], "count", summary["zero_control_failure_count"] == 0),
        ("empty_nonzero_mask_count", summary["empty_nonzero_mask_count"], "count", summary["empty_nonzero_mask_count"] == 0),
        ("padding_overlap_failure_count", summary["padding_overlap_failure_count"], "count", summary["padding_overlap_failure_count"] == 0),
        ("area_tolerance_failure_count", summary["area_tolerance_failure_count"], "count", summary["area_tolerance_failure_count"] == 0),
        ("morphology_reconciliation_failure_count", summary["morphology_reconciliation_failure_count"], "count", summary["morphology_reconciliation_failure_count"] == 0),
        ("family_morphology_failure_count", family_failures, "count", family_failures == 0),
        ("deterministic_replay_failure_count", replay_failures, "count", replay_failures == 0),
        ("total_runtime_seconds", float(runtime_values.sum()), "seconds", True),
        ("mean_runtime_seconds", float(runtime_values.mean()), "seconds", True),
        ("median_runtime_seconds", float(runtime_values.median()), "seconds", True),
        ("p95_runtime_seconds", float(runtime_values.quantile(0.95)), "seconds", True),
        ("maximum_generation_attempts_observed", maximum_attempts, "count", maximum_attempts <= int(config["generator"]["maximum_generation_attempts"])),
    ]
    if len(global_specs) != GLOBAL_AUDIT_METRIC_COUNT:
        raise RuntimeError("Global mask audit metric count changed")
    raw_rows: list[dict[str, Any]] = []
    for name, value, unit, passed in global_specs:
        raw_rows.append({
            "audit_section": "global", "group_field": "", "group_value": "",
            "comparison_group_value": "", "metric_name": name,
            "metric_value": value, "metric_unit": unit, "numerator": value,
            "denominator": len(masks), "status": "passed" if passed else "failed",
            "details": "",
        })
    for mask_type in SUPPORTED_MASK_TYPES:
        group = masks.loc[masks["mask_type"].eq(mask_type)]
        distance_values = group["minimum_distance_to_content_boundary_pixels"].replace(-1, np.nan)
        metrics = {
            "case_count": (len(group), "count"),
            "mean_damaged_content_fraction": (float(group["damaged_content_fraction"].mean()), "fraction"),
            "std_damaged_content_fraction": (float(group["damaged_content_fraction"].std(ddof=0)), "fraction"),
            "median_damaged_content_fraction": (float(group["damaged_content_fraction"].median()), "fraction"),
            "mean_connected_component_count": (float(group["connected_component_count"].mean()), "count"),
            "median_largest_component_fraction": (float(group["largest_component_fraction"].median()), "fraction"),
            "median_bbox_fill_ratio": (float(group["bbox_fill_ratio"].median()), "fraction"),
            "median_maximum_component_aspect_ratio": (float(group["maximum_component_aspect_ratio"].median()), "ratio"),
            "median_mask_compactness": (float(group["mask_compactness"].median()), "ratio"),
            "boundary_touch_fraction": (float(group["touches_content_boundary"].astype(float).mean()), "fraction"),
            "median_distance_to_content_boundary_pixels": (float(distance_values.median()) if distance_values.notna().any() else -1.0, "pixels"),
            "mean_generation_attempts": (float(group["generation_attempts"].mean()), "count"),
        }
        for name in FAMILY_AUDIT_METRICS:
            value, unit = metrics[name]
            raw_rows.append({
                "audit_section": "mask_family", "group_field": "mask_type",
                "group_value": mask_type, "comparison_group_value": "",
                "metric_name": name, "metric_value": value, "metric_unit": unit,
                "numerator": value, "denominator": len(group), "status": "passed",
                "details": "",
            })
    for item in _pairwise_equivalence_rows(masks):
        raw_rows.append({
            "audit_section": "family_comparison", "group_field": "mask_type",
            "group_value": item["left"], "comparison_group_value": item["right"],
            "metric_name": "pixel_equivalent_painting_count", "metric_value": item["count"],
            "metric_unit": "count", "numerator": item["count"],
            "denominator": item["denominator"], "status": "passed" if item["count"] == 0 else "failed",
            "details": "",
        })
    for item in family_validation.to_dict(orient="records"):
        raw_rows.append({
            "audit_section": "morphology_expectation", "group_field": "mask_type",
            "group_value": item["mask_type"], "comparison_group_value": "",
            "metric_name": item["rule_id"], "metric_value": 1 if item["passed"] else 0,
            "metric_unit": "boolean", "numerator": 1 if item["passed"] else 0,
            "denominator": 1, "status": "passed" if item["passed"] else "failed",
            "details": item["details"],
        })
    expected_rows = int(config["expected"]["audit_row_count"])
    if len(raw_rows) != expected_rows:
        raise RuntimeError(f"Expected {expected_rows} mask audit rows, built {len(raw_rows)}")
    records = []
    for index, row in enumerate(raw_rows, start=1):
        records.append({
            "audit_row_id": f"mask_audit_{index:03d}",
            "dataset_id": str(dataset["dataset_id"]),
            "dataset_version": str(dataset["dataset_version"]),
            "dataset_scope": str(dataset["dataset_scope"]),
            "experiment_id": str(dataset["experiment_id"]),
            **row,
        })
    result = pd.DataFrame(records, columns=MASK_AUDIT_COLUMNS)
    schema_result = validate_dataframe(result, MASK_AUDIT_SCHEMA, allow_extra_columns=False)
    if not schema_result.passed or schema_result.unexpected_columns:
        raise RuntimeError(f"Mask audit violates schema: {schema_result.to_dict()}")
    return result


def render_mask_protocol(
    config: Mapping[str, Any],
    family_validation: pd.DataFrame,
) -> str:
    """Render the canonical binary missing-region protocol as Markdown."""
    lines = [
        "# Canonical Binary Missing-Region Mask Protocol",
        "",
        f"- Configuration schema: `{config['config_schema_version']}`",
        f"- Configuration version: `{config['config_version']}`",
        f"- Generator: `{config['generator']['name']}` version `{config['generator']['version']}`",
        f"- Seed scheme: `{config['generator']['seed_scheme_version']}`",
        f"- Global seed: `{config['generator']['global_seed']}`",
        f"- Retry policy: `{config['generator']['retry_policy']}`",
        f"- Maximum attempts: {config['generator']['maximum_generation_attempts']}",
        "- Spatial convention: `xyxy_exclusive_zero_based`",
        "- Area denominator: painting-content pixels from Notebook 02",
        "- Saved values: grayscale PNG with exact values 0 and 255",
        "",
        "## Canonical mask families",
        "",
        "| Family | Lower | Target | Upper | Description |",
        "|---|---:|---:|---:|---|",
    ]
    for name in SUPPORTED_MASK_TYPES:
        family = config["families"][name]
        lines.append(
            f"| `{name}` | {family['lower_damaged_content_fraction']:.3f} | "
            f"{family['target_damaged_content_fraction']:.3f} | "
            f"{family['upper_damaged_content_fraction']:.3f} | {family['description']} |"
        )
    lines.extend([
        "", "## Morphology expectations", "",
        "| Family | Rule | Status |", "|---|---|---|",
    ])
    for row in family_validation.itertuples(index=False):
        lines.append(f"| `{row.mask_type}` | `{row.rule_id}` | {'passed' if row.passed else 'failed'} |")
    lines.extend([
        "", "## Explicit exclusions", "",
        "This notebook models binary missing-region damage only. It does not model:", "",
    ])
    lines.extend(f"- `{item}`" for item in config["exclusions"])
    lines.extend([
        "", "## Interpretation boundary", "",
        "These masks are controlled synthetic evaluation instruments. They do not claim to reproduce the full material, historical, chemical, or conservation complexity of real painting damage.",
        "Padding belongs to the technical model canvas and is never eligible for damage.",
        "Runtime, run identifiers, timestamps, and environment metadata are run-dependent; mask pixels and canonical geometry are deterministic under the recorded configuration and seeds.",
        "",
    ])
    return "\n".join(lines)


def audit_mask_inventory(
    mask_metadata: pd.DataFrame,
    mask_dir: Path,
    expected_mask_types: Sequence[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Compatibility inventory audit for older callers."""
    expected = list(SUPPORTED_MASK_TYPES if expected_mask_types is None else expected_mask_types)
    path_column = "mask_path"
    filename_column = "mask_filename"
    duplicates = lambda columns: mask_metadata[mask_metadata.duplicated(columns, keep=False)].copy()
    missing = mask_metadata[~mask_metadata[path_column].astype(str).map(lambda value: Path(value).exists())].copy()
    disk = {path.name for path in Path(mask_dir).glob("*.png") if path.is_file()}
    metadata_names = set(mask_metadata[filename_column].astype(str))
    orphan_names = sorted(disk - metadata_names)
    missing_types = []
    for painting_id, group in mask_metadata.groupby("painting_id", sort=True):
        present = set(group["mask_type"].astype(str))
        for mask_type in expected:
            if mask_type not in present:
                missing_types.append({"painting_id": painting_id, "mask_type": mask_type, "issue": "missing_painting_mask_type"})
    return {
        "duplicate_case_rows": duplicates(["case_id"]),
        "duplicate_mask_id_rows": duplicates(["mask_id"]),
        "duplicate_filename_rows": duplicates([filename_column]),
        "duplicate_path_rows": duplicates([path_column]),
        "missing_file_rows": missing,
        "orphan_file_rows": pd.DataFrame({
            "mask_filename": orphan_names,
            "mask_path": [str(Path(mask_dir) / name) for name in orphan_names],
            "issue": ["orphan_mask_file"] * len(orphan_names),
        }),
        "missing_mask_type_rows": pd.DataFrame(missing_types),
        "unexpected_mask_type_rows": mask_metadata[~mask_metadata["mask_type"].isin(expected)].copy(),
    }


def validate_masks(mask_metadata: pd.DataFrame, target_size: int = 768) -> pd.DataFrame:
    """Compatibility saved-mask validator for legacy absolute-path tables."""
    rows = []
    for row in mask_metadata.to_dict(orient="records"):
        path = Path(str(row["mask_path"]))
        issues: list[str] = []
        if not path.is_file():
            issues.append("missing_mask_file")
        else:
            try:
                with Image.open(path) as image:
                    image.load()
                    unique = set(np.unique(np.asarray(image.convert("L"))).astype(int).tolist())
                    if image.size != (target_size, target_size):
                        issues.append("wrong_mask_size")
                    if image.format != "PNG":
                        issues.append("wrong_mask_format")
                    if image.mode != "L":
                        issues.append("wrong_saved_mask_mode")
                    if not unique.issubset({0, 255}):
                        issues.append("mask_not_binary")
            except (OSError, ValueError) as exc:
                issues.append(f"unreadable_mask_file:{type(exc).__name__}:{exc}")
        rows.append({
            "case_id": row.get("case_id", ""), "painting_id": row.get("painting_id", ""),
            "mask_type": row.get("mask_type", ""), "mask_path": str(path),
            "file_exists": path.is_file(), "readable": path.is_file() and not any("unreadable" in item for item in issues),
            "validation_passed": not issues, "issue_count": len(issues), "issue": "|".join(issues),
        })
    return pd.DataFrame(rows)
