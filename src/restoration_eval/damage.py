"""Canonical damaged-image generation and exact pixel-integrity validation."""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml
from PIL import Image

from .manifests import sha256_file
from .paths import (
    find_project_root,
    notebook_output_root,
    require_notebook_output_path,
    resolve_repo_path,
    to_repo_relative,
)
from .schemas import (
    CANONICAL_DAMAGE_AUDIT_COLUMNS,
    CANONICAL_DAMAGE_AUDIT_SCHEMA,
    CANONICAL_DAMAGE_CASES_COLUMNS,
    CANONICAL_DAMAGE_CASES_SCHEMA,
    CANONICAL_MASKS_SCHEMA,
    PREPROCESSED_IMAGES_SCHEMA,
    validate_dataframe,
)

DAMAGE_MODULE_VERSION = "3.0.0"
CANONICAL_DAMAGE_CONFIG_SCHEMA_VERSION = "canonical_damage_config.v1"
GENERATOR_NAME = "canonical_damage_generator"
GENERATOR_VERSION = DAMAGE_MODULE_VERSION
SUPPORTED_FILL_STRATEGIES = ("constant_rgb",)
SUPPORTED_MASK_TYPES = (
    "zero_control",
    "scratch_thin",
    "loss_small",
    "loss_large",
    "mixed_damage",
)
DEFAULT_FILL_COLOR = (255, 255, 255)
ZERO_CONTROL_MASK_TYPE = "zero_control"
RUNTIME_COLUMNS = ("case_id", "runtime_seconds")


@dataclass(frozen=True)
class DamageGenerationResult:
    """Canonical cases plus deliberately noncanonical runtime and cleanup evidence."""

    cases: pd.DataFrame
    runtimes: pd.DataFrame
    removed_stale_paths: tuple[str, ...]


@dataclass(frozen=True)
class DamageValidationResult:
    """Per-case validation evidence and output-inventory reconciliation."""

    case_checks: pd.DataFrame
    summary: Mapping[str, int]
    orphan_paths: tuple[str, ...]

    @property
    def passed(self) -> bool:
        failure_keys = (
            "duplicate_case_id_count",
            "duplicate_damaged_path_count",
            "missing_output_count",
            "orphan_output_count",
            "failed_case_count",
            "reload_failure_count",
            "dimension_failure_count",
            "binary_mask_failure_count",
            "mask_pixel_count_failure_count",
            "changed_pixel_count_failure_count",
            "outside_mask_change_failure_count",
            "inside_mask_fill_failure_count",
            "zero_control_failure_count",
            "checksum_failure_count",
            "output_contract_failure_count",
        )
        return all(int(self.summary.get(key, 0)) == 0 for key in failure_keys)


def _require_mapping(parent: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"Canonical damage configuration key {key!r} must be a mapping")
    return value


def _normalize_fill_color(values: Sequence[Any]) -> tuple[int, int, int]:
    if isinstance(values, (str, bytes)) or len(values) != 3:
        raise ValueError("fill_color_rgb must contain exactly three channel values")
    color = tuple(int(value) for value in values)
    if any(value < 0 or value > 255 for value in color):
        raise ValueError("fill_color_rgb values must be integers from 0 to 255")
    return color


def validate_damage_config(config: Mapping[str, Any]) -> list[str]:
    """Return violations of the versioned canonical damage configuration."""
    errors: list[str] = []
    if config.get("config_schema_version") != CANONICAL_DAMAGE_CONFIG_SCHEMA_VERSION:
        errors.append(
            f"config_schema_version must equal {CANONICAL_DAMAGE_CONFIG_SCHEMA_VERSION}"
        )
    if not str(config.get("config_version", "")).strip():
        errors.append("config_version must be non-empty")
    try:
        dataset = _require_mapping(config, "dataset")
        inputs = _require_mapping(config, "inputs")
        output = _require_mapping(config, "output")
        generator = _require_mapping(config, "generator")
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
    schema_versions = {
        "geometry_schema_version": PREPROCESSED_IMAGES_SCHEMA.version,
        "mask_schema_version": CANONICAL_MASKS_SCHEMA.version,
        "output_schema_version": CANONICAL_DAMAGE_CASES_SCHEMA.version,
        "audit_schema_version": CANONICAL_DAMAGE_AUDIT_SCHEMA.version,
    }
    for key, value in schema_versions.items():
        if dataset.get(key) != value:
            errors.append(f"dataset.{key} must equal {value}")

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
        value = str(inputs.get(key, "")).strip()
        if not value or Path(value).is_absolute() or chr(92) in value:
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
    for key, value in required_lists.items():
        if inputs.get(key) != value:
            errors.append(f"inputs.{key} must equal {value}")
    if inputs.get("required_upstream_run_status") != "completed":
        errors.append("inputs.required_upstream_run_status must equal completed")

    output_contract = {
        "notebook_stem": "04_canonical_damaged_image_generation",
        "cases_path": "data/cases.csv",
        "image_directory": "images/damaged",
        "image_path_template": "{painting_id}/{mask_type}.png",
        "audit_path": "metrics/damage_audit.csv",
        "examples_figure_path": "figures/damage_examples.png",
    }
    for key, value in output_contract.items():
        if output.get(key) != value:
            errors.append(f"output.{key} must equal {value}")

    generator_contract = {
        "name": GENERATOR_NAME,
        "version": GENERATOR_VERSION,
        "fill_strategy": "constant_rgb",
        "zero_control_mask_type": ZERO_CONTROL_MASK_TYPE,
        "copy_zero_control_bytes": True,
        "mask_background_value": 0,
        "mask_damaged_value": 255,
        "output_mode": "RGB",
        "output_format": "PNG",
        "output_extension": ".png",
        "strip_output_metadata": True,
        "overwrite_existing": True,
        "stale_file_action": "remove",
    }
    for key, value in generator_contract.items():
        if generator.get(key) != value:
            errors.append(f"generator.{key} must equal {value!r}")
    try:
        if _normalize_fill_color(generator.get("fill_color_rgb", [])) != DEFAULT_FILL_COLOR:
            errors.append(f"generator.fill_color_rgb must equal {DEFAULT_FILL_COLOR}")
    except (TypeError, ValueError) as exc:
        errors.append(str(exc))
    width, height = generator.get("target_width"), generator.get("target_height")
    if not isinstance(width, int) or width <= 0:
        errors.append("generator.target_width must be a positive integer")
    if not isinstance(height, int) or height <= 0:
        errors.append("generator.target_height must be a positive integer")
    if width != height:
        errors.append("canonical damage target dimensions must be square")
    level = generator.get("png_compress_level")
    if not isinstance(level, int) or not 0 <= level <= 9:
        errors.append("generator.png_compress_level must be an integer from 0 to 9")
    if not isinstance(generator.get("png_optimize"), bool):
        errors.append("generator.png_optimize must be boolean")

    painting_count = expected.get("painting_count")
    case_count = expected.get("case_count")
    if not isinstance(painting_count, int) or painting_count <= 0:
        errors.append("expected.painting_count must be a positive integer")
    if expected.get("mask_types") != list(SUPPORTED_MASK_TYPES):
        errors.append(f"expected.mask_types must equal {list(SUPPORTED_MASK_TYPES)}")
    if expected.get("mask_type_count") != len(SUPPORTED_MASK_TYPES):
        errors.append(f"expected.mask_type_count must equal {len(SUPPORTED_MASK_TYPES)}")
    if isinstance(painting_count, int) and case_count != painting_count * len(SUPPORTED_MASK_TYPES):
        errors.append("expected.case_count must equal painting_count times mask_type_count")
    if expected.get("audit_row_count") != case_count:
        errors.append("expected.audit_row_count must equal expected.case_count")
    if expected.get("artifact_record_count") != 5:
        errors.append("expected.artifact_record_count must equal 5")
    if smoke.get("selection_rule") != (
        "closest_to_median_content_area_fraction_then_dataset_sort_index"
    ):
        errors.append("smoke.selection_rule is unsupported")
    if smoke.get("painting_count") != 1:
        errors.append("smoke.painting_count must equal 1")
    if examples.get("selection_rule") != "same_as_smoke":
        errors.append("examples.selection_rule must equal same_as_smoke")
    if examples.get("painting_count") != 1:
        errors.append("examples.painting_count must equal 1")
    if not isinstance(examples.get("figure_dpi"), int) or examples["figure_dpi"] <= 0:
        errors.append("examples.figure_dpi must be a positive integer")
    if examples.get("columns") != ["clean", "mask", "damaged", "changed_pixels"]:
        errors.append("examples.columns must define the approved four-panel layout")
    return errors


def load_damage_config(path: str | Path) -> dict[str, Any]:
    """Load and validate the canonical damage configuration."""
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Canonical damage configuration not found: {config_path}")
    with config_path.open("r", encoding="utf-8-sig") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError("Canonical damage configuration must load as a mapping")
    config = dict(payload)
    errors = validate_damage_config(config)
    if errors:
        raise ValueError("Invalid canonical damage configuration: " + "; ".join(errors))
    return config


def resolve_damage_inputs(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
    *,
    must_exist: bool = True,
) -> dict[str, Path]:
    """Resolve the eight explicit Notebook 02 and 03 handoff artifacts."""
    errors = validate_damage_config(config)
    if errors:
        raise ValueError("Invalid canonical damage configuration: " + "; ".join(errors))
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


def validate_canonical_damage_handoff(
    preprocessed: pd.DataFrame,
    masks: pd.DataFrame,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
    *,
    verify_files: bool = True,
) -> list[str]:
    """Validate Notebook 02/03 schemas, counts, identities, and foreign keys."""
    errors = ["configuration: " + item for item in validate_damage_config(config)]
    if errors:
        return errors
    geometry_result = validate_dataframe(
        preprocessed, PREPROCESSED_IMAGES_SCHEMA, allow_extra_columns=False
    )
    masks_result = validate_dataframe(masks, CANONICAL_MASKS_SCHEMA, allow_extra_columns=False)
    if not geometry_result.passed or geometry_result.unexpected_columns:
        errors.append(f"preprocessed schema violation: {geometry_result.to_dict()}")
    if not masks_result.passed or masks_result.unexpected_columns:
        errors.append(f"masks schema violation: {masks_result.to_dict()}")
    if geometry_result.missing_columns or masks_result.missing_columns:
        return errors

    expected, dataset = config["expected"], config["dataset"]
    if len(preprocessed) != int(expected["painting_count"]):
        errors.append("preprocessed row count does not match expected.painting_count")
    if len(masks) != int(expected["case_count"]):
        errors.append("mask row count does not match expected.case_count")
    if preprocessed["painting_id"].duplicated().any():
        errors.append("preprocessed rows contain duplicate painting_id values")
    if masks["case_id"].duplicated().any() or masks["mask_id"].duplicated().any():
        errors.append("mask rows contain duplicate case_id or mask_id values")
    for key in ("dataset_id", "dataset_version", "dataset_scope"):
        configured = {str(dataset[key])}
        if set(preprocessed[key].astype(str)) != configured:
            errors.append(f"preprocessed {key} values do not match configuration")
        if set(masks[key].astype(str)) != configured:
            errors.append(f"mask {key} values do not match configuration")
    if set(masks["experiment_id"].astype(str)) != {str(dataset["experiment_id"])}:
        errors.append("mask experiment_id values do not match configuration")
    if set(masks["mask_type"].astype(str)) != set(SUPPORTED_MASK_TYPES):
        errors.append("mask_type values do not match the canonical family set")
    counts = masks.groupby(["painting_id", "mask_type"], observed=True).size()
    if len(counts) != int(expected["case_count"]) or not counts.eq(1).all():
        errors.append("each painting must have exactly one case per canonical mask type")

    lookup = preprocessed.set_index("processed_image_id", drop=False)
    missing = set(masks["processed_image_id"].astype(str)) - set(lookup.index.astype(str))
    if missing:
        errors.append(f"mask rows reference missing processed_image_id values: {sorted(missing)[:5]}")
    else:
        for row in masks.itertuples(index=False):
            geometry = lookup.loc[str(row.processed_image_id)]
            if (
                str(geometry["painting_id"]) != str(row.painting_id)
                or str(geometry["processed_path"]) != str(row.processed_image_path)
                or str(geometry["sha256"]) != str(row.processed_image_sha256)
            ):
                errors.append(f"Notebook 02 foreign-key mismatch for case {row.case_id}")
                break
    if not masks["binary_values_valid"].astype(bool).all():
        errors.append("mask handoff contains a nonbinary mask status")
    if not masks["zero_control_rule_valid"].astype(bool).all():
        errors.append("mask handoff contains an invalid zero-control status")
    if not masks["generation_status"].astype(str).eq("passed").all():
        errors.append("mask handoff contains failed generation rows")
    if not preprocessed["status"].astype(str).eq("passed").all():
        errors.append("preprocessed handoff contains failed rows")
    for column, frame in (
        ("processed_path", preprocessed),
        ("processed_image_path", masks),
        ("mask_path", masks),
    ):
        if frame[column].astype(str).map(
            lambda value: Path(value).is_absolute() or chr(92) in value
        ).any():
            errors.append(f"{column} contains a non-normalized path")
    if verify_files:
        root = find_project_root(project_root)
        for column, frame in (("processed_path", preprocessed), ("mask_path", masks)):
            for value in frame[column].astype(str):
                try:
                    resolve_repo_path(value, root, must_exist=True)
                except (FileNotFoundError, ValueError) as exc:
                    errors.append(f"{column} file verification failed: {exc}")
                    break
    return errors


def select_representative_cases(
    preprocessed: pd.DataFrame,
    masks: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select all mask types for the deterministic median-content painting."""
    if validate_damage_config(config):
        raise ValueError("Cannot select representative cases from invalid configuration")
    geometry = preprocessed[
        ["painting_id", "dataset_sort_index", "content_area_fraction"]
    ].copy()
    median = float(geometry["content_area_fraction"].astype(float).median())
    geometry["_distance"] = (
        geometry["content_area_fraction"].astype(float) - median
    ).abs()
    selected_id = str(
        geometry.sort_values(
            ["_distance", "dataset_sort_index", "painting_id"], kind="stable"
        ).iloc[0]["painting_id"]
    )
    order = {name: index for index, name in enumerate(SUPPORTED_MASK_TYPES)}
    result = masks.loc[masks["painting_id"].astype(str) == selected_id].copy()
    result["_order"] = result["mask_type"].map(order)
    result = result.sort_values(["_order", "case_id"], kind="stable")
    result = result.drop(columns="_order").reset_index(drop=True)
    if len(result) != len(SUPPORTED_MASK_TYPES):
        raise ValueError("Representative painting does not contain every mask type")
    return result


def _binary_mask_array(mask: Image.Image) -> np.ndarray:
    array = np.asarray(mask.convert("L"), dtype=np.uint8)
    unique_values = set(np.unique(array).astype(int).tolist())
    if not unique_values.issubset({0, 255}):
        raise ValueError(f"Mask must contain only 0 and 255; observed {sorted(unique_values)}")
    return array == 255


def apply_mask_damage(
    clean_image: Image.Image,
    mask: Image.Image,
    fill_color: Sequence[int] = DEFAULT_FILL_COLOR,
) -> Image.Image:
    """Replace exactly binary-mask pixels while preserving all other RGB pixels."""
    color = np.asarray(_normalize_fill_color(fill_color), dtype=np.uint8)
    clean_array = np.asarray(clean_image.convert("RGB"), dtype=np.uint8).copy()
    mask_array = _binary_mask_array(mask)
    if clean_array.shape[:2] != mask_array.shape:
        raise ValueError(
            f"Clean image and mask dimensions differ: {clean_array.shape[:2]} "
            f"versus {mask_array.shape}"
        )
    clean_array[mask_array] = color
    return Image.fromarray(clean_array, mode="RGB")


def _expected_output_path(
    output_root: Path,
    painting_id: str,
    mask_type: str,
    config: Mapping[str, Any],
    project_root: Path,
) -> Path:
    relative = str(config["output"]["image_path_template"]).format(
        painting_id=painting_id,
        mask_type=mask_type,
    )
    path = output_root / str(config["output"]["image_directory"]) / relative
    return require_notebook_output_path(
        path, str(config["output"]["notebook_stem"]), project_root
    )


def _remove_stale_files(
    image_root: Path,
    expected_paths: set[Path],
    project_root: Path,
) -> tuple[str, ...]:
    removed: list[str] = []
    if image_root.exists():
        files = sorted(
            (item for item in image_root.rglob("*") if item.is_file()),
            key=lambda item: item.as_posix(),
        )
        for path in files:
            if path.resolve() not in expected_paths:
                removed.append(to_repo_relative(path, project_root))
                path.unlink()
        directories = sorted(
            (item for item in image_root.rglob("*") if item.is_dir()),
            key=lambda item: len(item.parts),
            reverse=True,
        )
        for directory in directories:
            if not any(directory.iterdir()):
                directory.rmdir()
    return tuple(removed)


def _save_png_atomic(
    image: Image.Image,
    path: Path,
    *,
    compress_level: int,
    optimize: bool,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        image.save(
            temporary,
            format="PNG",
            compress_level=int(compress_level),
            optimize=bool(optimize),
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _copy_file_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def generate_canonical_damage_dataset(
    preprocessed: pd.DataFrame,
    masks: pd.DataFrame,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> DamageGenerationResult:
    """Generate the complete normalized canonical damaged-image collection."""
    root = find_project_root(project_root)
    errors = validate_canonical_damage_handoff(
        preprocessed, masks, config, root, verify_files=True
    )
    if errors:
        raise ValueError("Invalid canonical damage handoff: " + "; ".join(errors))

    output_root = notebook_output_root(
        str(config["output"]["notebook_stem"]), root, create=True
    )
    image_root = require_notebook_output_path(
        output_root / str(config["output"]["image_directory"]),
        str(config["output"]["notebook_stem"]),
        root,
    )
    expected_paths = {
        _expected_output_path(
            output_root, str(row.painting_id), str(row.mask_type), config, root
        ).resolve()
        for row in masks.itertuples(index=False)
    }
    removed_stale_paths = _remove_stale_files(image_root, expected_paths, root)
    generator = config["generator"]
    fill_color = _normalize_fill_color(generator["fill_color_rgb"])
    records: list[dict[str, Any]] = []
    runtime_records: list[dict[str, Any]] = []
    ordered = masks.copy()
    mask_order = {name: index for index, name in enumerate(SUPPORTED_MASK_TYPES)}
    ordered["_mask_order"] = ordered["mask_type"].map(mask_order)
    ordered = ordered.sort_values(
        ["painting_id", "_mask_order", "case_id"], kind="stable"
    )

    for row in ordered.itertuples(index=False):
        started = time.perf_counter()
        clean_path = resolve_repo_path(
            str(row.processed_image_path), root, must_exist=True
        )
        mask_path = resolve_repo_path(str(row.mask_path), root, must_exist=True)
        damaged_path = _expected_output_path(
            output_root, str(row.painting_id), str(row.mask_type), config, root
        )
        with Image.open(clean_path) as clean_source:
            clean_image = clean_source.convert("RGB")
            clean_image.load()
        with Image.open(mask_path) as mask_source:
            mask_image = mask_source.convert("L")
            mask_image.load()
        mask_array = _binary_mask_array(mask_image)
        if int(mask_array.sum()) != int(row.damaged_pixel_count):
            raise ValueError(f"Mask pixel count mismatch before generation: {row.case_id}")

        if str(row.mask_type) == ZERO_CONTROL_MASK_TYPE:
            if mask_array.any():
                raise ValueError(f"Zero-control mask is not empty: {row.case_id}")
            _copy_file_atomic(clean_path, damaged_path)
        else:
            damaged_image = apply_mask_damage(clean_image, mask_image, fill_color)
            _save_png_atomic(
                damaged_image,
                damaged_path,
                compress_level=int(generator["png_compress_level"]),
                optimize=bool(generator["png_optimize"]),
            )

        with Image.open(damaged_path) as reloaded:
            reloaded.load()
            width, height = reloaded.size
            mode, format_name = reloaded.mode, reloaded.format
        records.append(
            {
                "dataset_id": str(row.dataset_id),
                "dataset_version": str(row.dataset_version),
                "dataset_scope": str(row.dataset_scope),
                "experiment_id": str(row.experiment_id),
                "case_id": str(row.case_id),
                "painting_id": str(row.painting_id),
                "processed_image_id": str(row.processed_image_id),
                "mask_id": str(row.mask_id),
                "mask_type": str(row.mask_type),
                "damaged_image_id": f"damaged__{row.case_id}",
                "clean_image_path": to_repo_relative(clean_path, root),
                "mask_path": to_repo_relative(mask_path, root),
                "damaged_image_path": to_repo_relative(damaged_path, root),
                "clean_image_sha256": sha256_file(clean_path),
                "mask_sha256": sha256_file(mask_path),
                "damaged_image_sha256": sha256_file(damaged_path),
                "fill_strategy": str(generator["fill_strategy"]),
                "fill_color_r": int(fill_color[0]),
                "fill_color_g": int(fill_color[1]),
                "fill_color_b": int(fill_color[2]),
                "mask_pixel_count": int(row.damaged_pixel_count),
                "damaged_filename": damaged_path.name,
                "width": int(width),
                "height": int(height),
                "mode": str(mode),
                "format": str(format_name),
                "size_bytes": int(damaged_path.stat().st_size),
                "generator_name": GENERATOR_NAME,
                "generator_version": GENERATOR_VERSION,
                "config_schema_version": CANONICAL_DAMAGE_CONFIG_SCHEMA_VERSION,
                "config_version": str(config["config_version"]),
                "generation_status": "passed",
                "status": "passed",
                "issue": "",
            }
        )
        runtime_records.append(
            {
                "case_id": str(row.case_id),
                "runtime_seconds": float(time.perf_counter() - started),
            }
        )

    cases = pd.DataFrame(records, columns=CANONICAL_DAMAGE_CASES_COLUMNS)
    schema_result = validate_dataframe(
        cases, CANONICAL_DAMAGE_CASES_SCHEMA, allow_extra_columns=False
    )
    if not schema_result.passed or schema_result.unexpected_columns:
        raise ValueError(f"Generated cases violate schema: {schema_result.to_dict()}")
    return DamageGenerationResult(
        cases=cases,
        runtimes=pd.DataFrame(runtime_records, columns=RUNTIME_COLUMNS),
        removed_stale_paths=removed_stale_paths,
    )


def validate_saved_damage_dataset(
    cases: pd.DataFrame,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> DamageValidationResult:
    """Reload all sources and outputs and verify exact corruption semantics."""
    root = find_project_root(project_root)
    config_errors = validate_damage_config(config)
    if config_errors:
        raise ValueError(
            "Invalid canonical damage configuration: " + "; ".join(config_errors)
        )
    case_schema = validate_dataframe(
        cases, CANONICAL_DAMAGE_CASES_SCHEMA, allow_extra_columns=False
    )
    if not case_schema.passed or case_schema.unexpected_columns:
        raise ValueError(f"Cases table violates schema: {case_schema.to_dict()}")

    generator = config["generator"]
    fill_color = np.asarray(
        _normalize_fill_color(generator["fill_color_rgb"]), dtype=np.uint8
    )
    target_size = (
        int(generator["target_width"]),
        int(generator["target_height"]),
    )
    rows: list[dict[str, Any]] = []

    for row in cases.itertuples(index=False):
        clean_path = resolve_repo_path(str(row.clean_image_path), root)
        mask_path = resolve_repo_path(str(row.mask_path), root)
        damaged_path = resolve_repo_path(str(row.damaged_image_path), root)
        issues: list[str] = []
        clean_exists = clean_path.is_file()
        mask_exists = mask_path.is_file()
        damaged_exists = damaged_path.is_file()
        if not clean_exists:
            issues.append("missing_clean_file")
        if not mask_exists:
            issues.append("missing_mask_file")
        if not damaged_exists:
            issues.append("missing_damaged_file")

        values: dict[str, Any] = {
            "reload_passed": False,
            "clean_width": None,
            "clean_height": None,
            "mask_width": None,
            "mask_height": None,
            "damaged_width": None,
            "damaged_height": None,
            "dimensions_match": False,
            "mask_unique_values": "[]",
            "binary_values_valid": False,
            "total_mask_pixels": None,
            "metadata_mask_pixels": int(row.mask_pixel_count),
            "mask_pixel_count_difference": None,
            "preexisting_fill_pixel_count": None,
            "expected_changed_pixel_count": None,
            "observed_changed_pixel_count": None,
            "changed_pixel_count_difference": None,
            "outside_mask_changed_pixel_count": None,
            "inside_mask_not_fill_pixel_count": None,
            "clean_equals_damaged": False,
            "zero_control_valid": False,
            "clean_sha256_matches": False,
            "mask_sha256_matches": False,
            "damaged_sha256_matches": False,
            "damaged_mode": "",
            "damaged_format": "",
            "output_contract_valid": False,
        }

        if clean_exists and mask_exists and damaged_exists:
            try:
                with Image.open(clean_path) as clean_source:
                    clean_source.load()
                    clean_array = np.asarray(
                        clean_source.convert("RGB"), dtype=np.uint8
                    )
                    clean_size = clean_source.size
                with Image.open(mask_path) as mask_source:
                    mask_source.load()
                    raw_mask = np.asarray(
                        mask_source.convert("L"), dtype=np.uint8
                    )
                    mask_size = mask_source.size
                with Image.open(damaged_path) as damaged_source:
                    damaged_source.load()
                    damaged_array = np.asarray(
                        damaged_source.convert("RGB"), dtype=np.uint8
                    )
                    damaged_size = damaged_source.size
                    damaged_mode = damaged_source.mode
                    damaged_format = damaged_source.format

                values.update(
                    {
                        "reload_passed": True,
                        "clean_width": int(clean_size[0]),
                        "clean_height": int(clean_size[1]),
                        "mask_width": int(mask_size[0]),
                        "mask_height": int(mask_size[1]),
                        "damaged_width": int(damaged_size[0]),
                        "damaged_height": int(damaged_size[1]),
                        "damaged_mode": str(damaged_mode),
                        "damaged_format": str(damaged_format),
                    }
                )
                dimensions_match = (
                    clean_size == mask_size == damaged_size == target_size
                )
                values["dimensions_match"] = dimensions_match
                if not dimensions_match:
                    issues.append("dimension_mismatch")

                unique_values = sorted(np.unique(raw_mask).astype(int).tolist())
                binary_valid = set(unique_values).issubset({0, 255})
                values["mask_unique_values"] = json.dumps(unique_values)
                values["binary_values_valid"] = binary_valid
                if not binary_valid:
                    issues.append("mask_not_binary")

                if dimensions_match and binary_valid:
                    mask_array = raw_mask == 255
                    difference = np.any(clean_array != damaged_array, axis=2)
                    total_mask = int(mask_array.sum())
                    metadata_mask = int(row.mask_pixel_count)
                    preexisting_fill = (
                        int(
                            np.all(
                                clean_array[mask_array] == fill_color, axis=1
                            ).sum()
                        )
                        if total_mask
                        else 0
                    )
                    expected_changed = total_mask - preexisting_fill
                    observed_changed = int(difference.sum())
                    outside_changed = int(difference[~mask_array].sum())
                    inside_not_fill = (
                        int(
                            np.any(
                                damaged_array[mask_array] != fill_color, axis=1
                            ).sum()
                        )
                        if total_mask
                        else 0
                    )
                    clean_equals_damaged = bool(
                        np.array_equal(clean_array, damaged_array)
                    )
                    mask_difference = total_mask - metadata_mask
                    changed_difference = observed_changed - expected_changed
                    values.update(
                        {
                            "total_mask_pixels": total_mask,
                            "mask_pixel_count_difference": mask_difference,
                            "preexisting_fill_pixel_count": preexisting_fill,
                            "expected_changed_pixel_count": expected_changed,
                            "observed_changed_pixel_count": observed_changed,
                            "changed_pixel_count_difference": changed_difference,
                            "outside_mask_changed_pixel_count": outside_changed,
                            "inside_mask_not_fill_pixel_count": inside_not_fill,
                            "clean_equals_damaged": clean_equals_damaged,
                        }
                    )
                    if mask_difference != 0:
                        issues.append("mask_pixel_count_mismatch")
                    if changed_difference != 0:
                        issues.append("changed_pixel_count_mismatch")
                    if outside_changed != 0:
                        issues.append("pixels_changed_outside_mask")
                    if inside_not_fill != 0:
                        issues.append("masked_pixels_not_equal_fill")

                    if str(row.mask_type) == ZERO_CONTROL_MASK_TYPE:
                        zero_valid = (
                            total_mask == 0
                            and clean_equals_damaged
                            and sha256_file(clean_path)
                            == sha256_file(damaged_path)
                        )
                    else:
                        zero_valid = total_mask > 0
                    values["zero_control_valid"] = bool(zero_valid)
                    if not zero_valid:
                        issues.append("zero_control_or_nonzero_rule_failure")

                clean_hash_matches = (
                    sha256_file(clean_path) == str(row.clean_image_sha256)
                )
                mask_hash_matches = sha256_file(mask_path) == str(row.mask_sha256)
                damaged_hash_matches = (
                    sha256_file(damaged_path) == str(row.damaged_image_sha256)
                )
                values["clean_sha256_matches"] = clean_hash_matches
                values["mask_sha256_matches"] = mask_hash_matches
                values["damaged_sha256_matches"] = damaged_hash_matches
                if not clean_hash_matches:
                    issues.append("clean_sha256_mismatch")
                if not mask_hash_matches:
                    issues.append("mask_sha256_mismatch")
                if not damaged_hash_matches:
                    issues.append("damaged_sha256_mismatch")
                if damaged_mode != generator["output_mode"]:
                    issues.append("damaged_mode_mismatch")
                if damaged_format != generator["output_format"]:
                    issues.append("damaged_format_mismatch")
            except Exception as exc:
                issues.append(f"reload_error:{type(exc).__name__}:{exc}")

        values["output_contract_valid"] = len(issues) == 0
        rows.append(
            {
                "dataset_id": str(row.dataset_id),
                "dataset_version": str(row.dataset_version),
                "dataset_scope": str(row.dataset_scope),
                "experiment_id": str(row.experiment_id),
                "case_id": str(row.case_id),
                "painting_id": str(row.painting_id),
                "mask_id": str(row.mask_id),
                "mask_type": str(row.mask_type),
                "clean_file_exists": clean_exists,
                "mask_file_exists": mask_exists,
                "damaged_file_exists": damaged_exists,
                **values,
                "validation_status": "passed" if not issues else "failed",
                "issue": ";".join(issues),
            }
        )

    checks = pd.DataFrame(rows, columns=CANONICAL_DAMAGE_AUDIT_COLUMNS)
    output_root = notebook_output_root(str(config["output"]["notebook_stem"]), root)
    image_root = output_root / str(config["output"]["image_directory"])
    expected_paths = {
        resolve_repo_path(value, root).resolve()
        for value in cases["damaged_image_path"].astype(str)
    }
    actual_paths = (
        {
            path.resolve()
            for path in image_root.rglob("*")
            if path.is_file()
        }
        if image_root.exists()
        else set()
    )
    orphan_paths = tuple(
        to_repo_relative(path, root)
        for path in sorted(
            actual_paths - expected_paths, key=lambda item: item.as_posix()
        )
    )
    numeric_failures = {
        "mask_pixel_count_failure_count": "mask_pixel_count_difference",
        "changed_pixel_count_failure_count": "changed_pixel_count_difference",
        "outside_mask_change_failure_count": "outside_mask_changed_pixel_count",
        "inside_mask_fill_failure_count": "inside_mask_not_fill_pixel_count",
    }
    summary = {
        "case_count": int(len(cases)),
        "duplicate_case_id_count": int(
            cases["case_id"].duplicated(keep=False).sum()
        ),
        "duplicate_damaged_path_count": int(
            cases["damaged_image_path"].duplicated(keep=False).sum()
        ),
        "missing_output_count": int(
            (~checks["damaged_file_exists"].astype(bool)).sum()
        ),
        "orphan_output_count": int(len(orphan_paths)),
        "failed_case_count": int(
            checks["validation_status"].ne("passed").sum()
        ),
        "reload_failure_count": int(
            (~checks["reload_passed"].astype(bool)).sum()
        ),
        "dimension_failure_count": int(
            (~checks["dimensions_match"].astype(bool)).sum()
        ),
        "binary_mask_failure_count": int(
            (~checks["binary_values_valid"].astype(bool)).sum()
        ),
        "zero_control_failure_count": int(
            (~checks["zero_control_valid"].astype(bool)).sum()
        ),
        "checksum_failure_count": int(
            (
                ~checks[
                    [
                        "clean_sha256_matches",
                        "mask_sha256_matches",
                        "damaged_sha256_matches",
                    ]
                ].astype(bool)
            )
            .any(axis=1)
            .sum()
        ),
        "output_contract_failure_count": int(
            (~checks["output_contract_valid"].astype(bool)).sum()
        ),
    }
    for summary_key, column in numeric_failures.items():
        summary[summary_key] = int(
            pd.to_numeric(checks[column], errors="coerce")
            .fillna(1)
            .ne(0)
            .sum()
        )
    return DamageValidationResult(
        case_checks=checks,
        summary=summary,
        orphan_paths=orphan_paths,
    )


def write_dataframe_atomic(dataframe: pd.DataFrame, path: str | Path) -> Path:
    """Write one CSV atomically without retaining a temporary artifact."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.name + ".tmp")
    try:
        dataframe.to_csv(temporary, index=False)
        os.replace(temporary, output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return output_path
