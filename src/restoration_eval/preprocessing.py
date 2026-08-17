"""Deterministic, normalized image preprocessing for clean reference images."""

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
from PIL import Image, UnidentifiedImageError

from .paths import (
    find_project_root,
    notebook_output_root,
    require_notebook_output_path,
    resolve_repo_path,
    to_repo_relative,
)
from .regions import content_region
from .schemas import (
    ARTWORKS_SCHEMA,
    PREPROCESSED_IMAGES_COLUMNS,
    PREPROCESSED_IMAGES_SCHEMA,
    PREPROCESSING_AUDIT_COLUMNS,
    PREPROCESSING_AUDIT_SCHEMA,
    validate_dataframe,
)


PREPROCESSING_MODULE_VERSION = "2.0.0"
PREPROCESSING_CONFIG_SCHEMA_VERSION = "preprocessing_config.v1"
GLOBAL_AUDIT_METRIC_COUNT = 25
GROUPED_AUDIT_METRICS = (
    "processed_count",
    "mean_content_area_fraction",
    "mean_padding_area_fraction",
    "median_resize_scale",
)
IMAGE_CHECK_COLUMNS = (
    "painting_id",
    "processed_path",
    "file_exists",
    "reload_passed",
    "sha256_matches",
    "width_matches",
    "height_matches",
    "mode_matches",
    "format_matches",
    "output_icc_absent",
    "geometry_reconciles",
    "content_bbox_valid",
    "padding_pixels_match",
    "issue",
)
RUNTIME_COLUMNS = ("painting_id", "runtime_seconds")


@dataclass(frozen=True)
class PreprocessingRunResult:
    """Normalized preprocessing records plus deliberately noncanonical runtimes."""

    images: pd.DataFrame
    runtimes: pd.DataFrame


@dataclass(frozen=True)
class PreprocessingValidationResult:
    """Reload evidence and reconciliation summaries for saved clean images."""

    image_checks: pd.DataFrame
    summary: Mapping[str, int]
    orphan_paths: tuple[str, ...]
    duplicate_sha256_groups: tuple[tuple[str, ...], ...]

    @property
    def passed(self) -> bool:
        failure_keys = (
            "missing_output_count",
            "stale_output_count",
            "duplicate_sha256_group_count",
            "orphan_output_count",
            "reload_failure_count",
            "output_width_nonconforming_count",
            "output_height_nonconforming_count",
            "output_mode_nonconforming_count",
            "output_format_nonconforming_count",
            "invalid_content_bbox_count",
            "geometry_reconciliation_failure_count",
            "padding_pixel_mismatch_count",
            "output_icc_present_count",
        )
        return all(int(self.summary.get(key, 0)) == 0 for key in failure_keys)


def _require_mapping(parent: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"Preprocessing configuration key {key!r} must be a mapping")
    return value


def validate_preprocessing_config(config: Mapping[str, Any]) -> list[str]:
    """Return violations of the versioned canonical preprocessing contract."""
    errors: list[str] = []
    if config.get("config_schema_version") != PREPROCESSING_CONFIG_SCHEMA_VERSION:
        errors.append(
            f"config_schema_version must equal {PREPROCESSING_CONFIG_SCHEMA_VERSION}"
        )
    try:
        dataset = _require_mapping(config, "dataset")
        inputs = _require_mapping(config, "inputs")
        output = _require_mapping(config, "output")
        processing = _require_mapping(config, "processing")
        orientation = _require_mapping(config, "orientation")
        color = _require_mapping(config, "color")
        expected = _require_mapping(config, "expected")
        smoke = _require_mapping(config, "smoke")
        preview = _require_mapping(config, "preview")
    except ValueError as exc:
        return errors + [str(exc)]

    schema_versions = {
        "input_schema_version": ARTWORKS_SCHEMA.version,
        "output_schema_version": PREPROCESSED_IMAGES_SCHEMA.version,
        "audit_schema_version": PREPROCESSING_AUDIT_SCHEMA.version,
    }
    for key in ("dataset_id", "dataset_version", "dataset_scope", "execution_profile"):
        if not str(dataset.get(key, "")).strip():
            errors.append(f"dataset.{key} must be non-empty")
    for key, expected_version in schema_versions.items():
        if dataset.get(key) != expected_version:
            errors.append(f"dataset.{key} must equal {expected_version}")

    for key in (
        "artworks_path",
        "artifacts_path",
        "run_manifest_path",
        "required_artifact_key",
        "required_upstream_run_status",
    ):
        if not str(inputs.get(key, "")).strip():
            errors.append(f"inputs.{key} must be non-empty")

    expected_output = {
        "notebook_stem": "02_image_preprocessing",
        "image_directory": "images/clean",
        "image_filename_template": "{painting_id}.png",
        "table_path": "data/preprocessed_images.csv",
        "audit_path": "metrics/preprocessing_audit.csv",
        "preview_path": "figures/preprocessing_preview.png",
    }
    for key, value in expected_output.items():
        if output.get(key) != value:
            errors.append(f"output.{key} must equal {value}")

    exact_processing = {
        "method": "aspect_ratio_resize_median_rgb_pad",
        "version": PREPROCESSING_MODULE_VERSION,
        "target_width": 768,
        "target_height": 768,
        "output_mode": "RGB",
        "output_format": "PNG",
        "output_extension": ".png",
        "interpolation": "lanczos",
        "dimension_rounding": "round_half_up",
        "preserve_aspect_ratio": True,
        "crop_content": False,
        "padding_method": "median_rgb_source_pixels",
        "odd_padding_remainder": "right_bottom",
        "coordinate_convention": "xyxy_exclusive_zero_based",
        "strip_output_metadata": True,
    }
    for key, value in exact_processing.items():
        if processing.get(key) != value:
            errors.append(f"processing.{key} must equal {value!r}")
    compress_level = processing.get("png_compress_level")
    if not isinstance(compress_level, int) or not 0 <= compress_level <= 9:
        errors.append("processing.png_compress_level must be an integer from 0 to 9")
    if not isinstance(processing.get("png_optimize"), bool):
        errors.append("processing.png_optimize must be boolean")

    if orientation.get("expected_exif_orientation") != 1:
        errors.append("orientation.expected_exif_orientation must equal 1")
    if orientation.get("non_default_action") != "block":
        errors.append("orientation.non_default_action must equal block")
    if not str(orientation.get("policy_label", "")).strip():
        errors.append("orientation.policy_label must be non-empty")

    exact_color = {
        "missing_icc_action": "assume_srgb_no_pixel_conversion",
        "embedded_srgb_action": "preserve_pixels_strip_profile",
        "non_srgb_action": "block",
    }
    for key, value in exact_color.items():
        if color.get(key) != value:
            errors.append(f"color.{key} must equal {value}")
    tokens = color.get("accepted_profile_description_tokens")
    if not isinstance(tokens, list) or not tokens or any(
        not str(token).strip() for token in tokens
    ):
        errors.append("color.accepted_profile_description_tokens must be non-empty")

    count = expected.get("accepted_input_count")
    if not isinstance(count, int) or count <= 0:
        errors.append("expected.accepted_input_count must be a positive integer")
    if expected.get("processed_output_count") != count:
        errors.append("expected.processed_output_count must equal accepted_input_count")
    categories = expected.get("categories")
    if not isinstance(categories, list) or not categories:
        errors.append("expected.categories must be a non-empty list")
        categories = []
    elif len(set(map(str, categories))) != len(categories):
        errors.append("expected.categories must be unique")
    expected_audit_rows = GLOBAL_AUDIT_METRIC_COUNT + len(categories) * len(
        GROUPED_AUDIT_METRICS
    )
    if expected.get("audit_row_count") != expected_audit_rows:
        errors.append(f"expected.audit_row_count must equal {expected_audit_rows}")

    for section_name, section in (("smoke", smoke), ("preview", preview)):
        if section.get("group_by") != "category":
            errors.append(f"{section_name}.group_by must equal category")
        if section.get("items_per_group") != 1:
            errors.append(f"{section_name}.items_per_group must equal 1")
        if section.get("sort_by") != ["category", "painting_id"]:
            errors.append(
                f"{section_name}.sort_by must equal ['category', 'painting_id']"
            )
    dpi = preview.get("figure_dpi")
    if not isinstance(dpi, int) or dpi <= 0:
        errors.append("preview.figure_dpi must be a positive integer")
    return errors


def load_preprocessing_config(path: str | Path) -> dict[str, Any]:
    """Load and validate the canonical preprocessing configuration."""
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Preprocessing configuration not found: {config_path}")
    with config_path.open("r", encoding="utf-8-sig") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError("Preprocessing configuration must load as a mapping")
    config = dict(payload)
    errors = validate_preprocessing_config(config)
    if errors:
        raise ValueError("Invalid preprocessing configuration: " + "; ".join(errors))
    return config


def resolve_preprocessing_inputs(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
    *,
    must_exist: bool = True,
) -> dict[str, Path]:
    """Resolve the three explicit Notebook 01 handoff files."""
    errors = validate_preprocessing_config(config)
    if errors:
        raise ValueError("Invalid preprocessing configuration: " + "; ".join(errors))
    root = find_project_root(project_root)
    inputs = config["inputs"]
    return {
        key: resolve_repo_path(inputs[key], root, must_exist=must_exist)
        for key in ("artworks_path", "artifacts_path", "run_manifest_path")
    }


def validate_artworks_handoff(
    artworks: pd.DataFrame,
    config: Mapping[str, Any],
) -> list[str]:
    """Validate normalized Notebook 01 rows needed by preprocessing."""
    errors = validate_preprocessing_config(config)
    if errors:
        return ["configuration: " + error for error in errors]
    schema_result = validate_dataframe(
        artworks,
        ARTWORKS_SCHEMA,
        allow_extra_columns=False,
    )
    if not schema_result.passed or schema_result.unexpected_columns:
        errors.append(f"artworks schema violation: {schema_result.to_dict()}")
    if schema_result.missing_columns:
        return errors
    if artworks.empty:
        return errors + ["artworks table is empty"]
    accepted = artworks.loc[artworks["acceptance_status"] == "accepted"].copy()
    expected = config["expected"]
    if len(accepted) != int(expected["accepted_input_count"]):
        errors.append(
            "accepted artwork count mismatch: "
            f"expected {expected['accepted_input_count']}, observed {len(accepted)}"
        )
    for key in ("dataset_id", "dataset_version", "dataset_scope"):
        observed = set(accepted[key].astype(str)) if key in accepted else set()
        if observed != {str(config["dataset"][key])}:
            errors.append(f"accepted artworks {key} values do not match configuration")
    observed_categories = set(accepted["category"].astype(str))
    if observed_categories != set(map(str, expected["categories"])):
        errors.append("accepted artwork categories do not match configuration")
    if accepted["painting_id"].duplicated().any():
        errors.append("accepted artworks contain duplicate painting_id values")
    if accepted["dataset_sort_index"].duplicated().any():
        errors.append("accepted artworks contain duplicate dataset_sort_index values")
    if (pd.to_numeric(accepted["raw_exif_orientation"], errors="coerce") != 1).any():
        errors.append("accepted artworks contain a non-default EXIF orientation")
    for path in accepted["raw_image_path"].astype(str):
        if Path(path).is_absolute() or "\\" in path:
            errors.append("accepted artworks contain a non-normalized raw_image_path")
            break
    if accepted["raw_sha256"].astype(str).str.fullmatch(r"[0-9a-f]{64}").ne(True).any():
        errors.append("accepted artworks contain invalid raw_sha256 values")
    return errors


def select_smoke_rows(
    artworks: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select one deterministic accepted in-memory smoke case per category."""
    return _select_group_rows(artworks, config["smoke"])


def select_preview_rows(
    artworks: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select one deterministic accepted preview case per category."""
    return _select_group_rows(artworks, config["preview"])


def _select_group_rows(
    artworks: pd.DataFrame,
    settings: Mapping[str, Any],
) -> pd.DataFrame:
    accepted = artworks.loc[artworks["acceptance_status"] == "accepted"].copy()
    return (
        accepted.sort_values(list(settings["sort_by"]), kind="stable")
        .groupby(str(settings["group_by"]), sort=True, group_keys=False)
        .head(int(settings["items_per_group"]))
        .reset_index(drop=True)
    )


def round_half_up(value: float) -> int:
    """Round a non-negative finite value with halves directed upward."""
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        raise ValueError(f"round_half_up requires a non-negative finite value: {value}")
    return int(math.floor(numeric + 0.5))


def compute_median_rgb(image: Image.Image) -> tuple[int, int, int]:
    """Return source-pixel RGB medians using explicit round-half-up."""
    rgb = image.convert("RGB")
    pixels = np.asarray(rgb)
    if pixels.size == 0:
        raise ValueError("Cannot compute median RGB for an empty image")
    medians = np.median(pixels.reshape(-1, 3), axis=0)
    return tuple(round_half_up(float(value)) for value in medians)


def _source_policy_labels(
    image: Image.Image,
    source_record: Mapping[str, Any],
    config: Mapping[str, Any],
) -> tuple[int, str, str, str]:
    orientation = int(image.getexif().get(274, 1))
    declared_orientation = int(source_record["raw_exif_orientation"])
    expected_orientation = int(config["orientation"]["expected_exif_orientation"])
    if orientation != declared_orientation:
        raise ValueError(
            f"EXIF orientation changed since Notebook 01: {orientation} != "
            f"{declared_orientation}"
        )
    if orientation != expected_orientation:
        raise ValueError(f"Non-default EXIF orientation is blocked: {orientation}")

    actual_icc_present = bool(image.info.get("icc_profile"))
    declared_icc_present = bool(source_record["raw_icc_profile_present"])
    if actual_icc_present != declared_icc_present:
        raise ValueError("ICC profile presence changed since Notebook 01")
    if not actual_icc_present:
        icc_status = "missing_assumed_srgb"
        color_policy = str(config["color"]["missing_icc_action"])
    else:
        description = str(source_record["raw_icc_profile_description"]).lower()
        tokens = [
            str(token).strip().lower()
            for token in config["color"]["accepted_profile_description_tokens"]
        ]
        if not any(token in description for token in tokens):
            raise ValueError(
                "Embedded ICC profile is not an accepted sRGB profile: "
                f"{source_record['raw_icc_profile_description']!r}"
            )
        icc_status = "embedded_srgb"
        color_policy = str(config["color"]["embedded_srgb_action"])
    return (
        orientation,
        str(config["orientation"]["policy_label"]),
        icc_status,
        color_policy,
    )


def resize_with_aspect_ratio_and_pad(
    image: Image.Image,
    config: Mapping[str, Any],
    *,
    source_record: Mapping[str, Any] | None = None,
) -> tuple[Image.Image, dict[str, Any]]:
    """Build a deterministic RGB canvas and exclusive-maximum content geometry."""
    errors = validate_preprocessing_config(config)
    if errors:
        raise ValueError("Invalid preprocessing configuration: " + "; ".join(errors))
    processing = config["processing"]
    target_width = int(processing["target_width"])
    target_height = int(processing["target_height"])
    if image.mode != "RGB":
        raise ValueError(f"Source image mode must be RGB, observed {image.mode!r}")
    original_width, original_height = image.size
    if original_width <= 0 or original_height <= 0:
        raise ValueError(f"Invalid source dimensions: {image.size}")
    if source_record is not None:
        if original_width != int(source_record["raw_width"]):
            raise ValueError("Source width changed since Notebook 01")
        if original_height != int(source_record["raw_height"]):
            raise ValueError("Source height changed since Notebook 01")

    scale = min(target_width / original_width, target_height / original_height)
    resized_width = max(1, round_half_up(original_width * scale))
    resized_height = max(1, round_half_up(original_height * scale))
    resized_width = min(resized_width, target_width)
    resized_height = min(resized_height, target_height)
    resized = image.resize(
        (resized_width, resized_height),
        resample=Image.Resampling.LANCZOS,
    )
    padding_color = compute_median_rgb(image)
    pad_left = (target_width - resized_width) // 2
    pad_top = (target_height - resized_height) // 2
    pad_right = target_width - resized_width - pad_left
    pad_bottom = target_height - resized_height - pad_top
    canvas = Image.new("RGB", (target_width, target_height), padding_color)
    canvas.paste(resized, (pad_left, pad_top))
    bbox = (
        pad_left,
        pad_top,
        pad_left + resized_width,
        pad_top + resized_height,
    )
    region = content_region((target_height, target_width), bbox)
    if region.bbox != bbox or region.validity_status != "valid":
        raise RuntimeError("Canonical content-region helper rejected preprocessing geometry")
    canvas_area = target_width * target_height
    content_area = resized_width * resized_height
    metadata = {
        "original_width": original_width,
        "original_height": original_height,
        "width": target_width,
        "height": target_height,
        "mode": "RGB",
        "format": "PNG",
        "resize_scale": float(scale),
        "resized_width": resized_width,
        "resized_height": resized_height,
        "interpolation": "lanczos",
        "pad_left": pad_left,
        "pad_top": pad_top,
        "pad_right": pad_right,
        "pad_bottom": pad_bottom,
        "padding_method": str(processing["padding_method"]),
        "padding_color_r": padding_color[0],
        "padding_color_g": padding_color[1],
        "padding_color_b": padding_color[2],
        "content_x_min": bbox[0],
        "content_y_min": bbox[1],
        "content_x_max": bbox[2],
        "content_y_max": bbox[3],
        "content_width": resized_width,
        "content_height": resized_height,
        "content_area_pixels": content_area,
        "padding_area_pixels": canvas_area - content_area,
        "canvas_area_pixels": canvas_area,
        "content_area_fraction": content_area / canvas_area,
        "padding_area_fraction": (canvas_area - content_area) / canvas_area,
        "coordinate_convention": str(processing["coordinate_convention"]),
        "preprocessing_method": str(processing["method"]),
        "preprocessing_version": str(processing["version"]),
    }
    return canvas, metadata


def build_preprocessed_image(
    source_image: Image.Image,
    source_record: Mapping[str, Any],
    config: Mapping[str, Any],
) -> tuple[Image.Image, dict[str, Any]]:
    """Create one in-memory output and complete deterministic geometry metadata."""
    orientation, orientation_policy, icc_status, color_policy = _source_policy_labels(
        source_image,
        source_record,
        config,
    )
    canvas, metadata = resize_with_aspect_ratio_and_pad(
        source_image,
        config,
        source_record=source_record,
    )
    metadata.update(
        {
            "source_orientation": orientation,
            "orientation_policy": orientation_policy,
            "input_icc_profile_status": icc_status,
            "color_space_policy": color_policy,
            "output_icc_profile_present": False,
        }
    )
    return canvas, metadata


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _save_png_atomic(
    image: Image.Image,
    path: Path,
    config: Mapping[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    processing = config["processing"]
    try:
        image.save(
            temporary,
            format="PNG",
            optimize=bool(processing["png_optimize"]),
            compress_level=int(processing["png_compress_level"]),
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def preprocess_artworks(
    artworks: pd.DataFrame,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> PreprocessingRunResult:
    """Preprocess every accepted artwork into the exact Notebook 02 image root."""
    handoff_errors = validate_artworks_handoff(artworks, config)
    if handoff_errors:
        raise ValueError("Invalid artworks handoff: " + "; ".join(handoff_errors))
    root = find_project_root(project_root)
    notebook_stem = str(config["output"]["notebook_stem"])
    output_root = notebook_output_root(notebook_stem, root)
    clean_dir = require_notebook_output_path(
        output_root / str(config["output"]["image_directory"]),
        notebook_stem,
        root,
    )
    accepted = (
        artworks.loc[artworks["acceptance_status"] == "accepted"]
        .sort_values("dataset_sort_index", kind="stable")
        .reset_index(drop=True)
    )
    records: list[dict[str, Any]] = []
    runtime_records: list[dict[str, Any]] = []
    for row in accepted.to_dict(orient="records"):
        started = time.perf_counter()
        painting_id = str(row["painting_id"])
        source_path = resolve_repo_path(row["raw_image_path"], root, must_exist=True)
        source_sha256 = _sha256(source_path)
        if source_sha256 != str(row["raw_sha256"]):
            raise ValueError(f"Source SHA-256 changed since Notebook 01: {painting_id}")
        output_filename = str(config["output"]["image_filename_template"]).format(
            painting_id=painting_id
        )
        output_path = require_notebook_output_path(
            clean_dir / output_filename,
            notebook_stem,
            root,
        )
        try:
            with Image.open(source_path) as source_image:
                source_image.load()
                canvas, metadata = build_preprocessed_image(source_image, row, config)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ValueError(
                f"Failed to preprocess {painting_id} from {source_path}: {exc}"
            ) from exc
        _save_png_atomic(canvas, output_path, config)
        with Image.open(output_path) as reloaded:
            reloaded.load()
            output_icc_present = bool(reloaded.info.get("icc_profile"))
            if reloaded.size != (metadata["width"], metadata["height"]):
                raise RuntimeError(f"Saved dimensions changed for {painting_id}")
            if reloaded.mode != "RGB" or reloaded.format != "PNG":
                raise RuntimeError(f"Saved mode/format changed for {painting_id}")
            if output_icc_present:
                raise RuntimeError(f"Output metadata stripping failed for {painting_id}")
        record = {
            "dataset_id": str(row["dataset_id"]),
            "dataset_version": str(row["dataset_version"]),
            "dataset_scope": str(row["dataset_scope"]),
            "processed_image_id": f"clean_{painting_id}",
            "painting_id": painting_id,
            "dataset_sort_index": int(row["dataset_sort_index"]),
            "source_path": to_repo_relative(source_path, root),
            "source_sha256": source_sha256,
            "processed_filename": output_filename,
            "processed_path": to_repo_relative(output_path, root),
            **metadata,
            "size_bytes": int(output_path.stat().st_size),
            "sha256": _sha256(output_path),
            "output_icc_profile_present": output_icc_present,
            "status": "passed",
        }
        records.append({column: record[column] for column in PREPROCESSED_IMAGES_COLUMNS})
        runtime_records.append(
            {
                "painting_id": painting_id,
                "runtime_seconds": time.perf_counter() - started,
            }
        )
    images = pd.DataFrame(records, columns=PREPROCESSED_IMAGES_COLUMNS)
    schema_result = validate_dataframe(
        images,
        PREPROCESSED_IMAGES_SCHEMA,
        allow_extra_columns=False,
    )
    if not schema_result.passed or schema_result.unexpected_columns:
        raise RuntimeError(f"Preprocessed images violate schema: {schema_result.to_dict()}")
    if len(images) != int(config["expected"]["processed_output_count"]):
        raise RuntimeError("Preprocessed output count does not match configuration")
    return PreprocessingRunResult(
        images=images,
        runtimes=pd.DataFrame(runtime_records, columns=RUNTIME_COLUMNS),
    )


def _padding_pixels_match(array: np.ndarray, row: Mapping[str, Any]) -> bool:
    bbox = (
        int(row["content_x_min"]),
        int(row["content_y_min"]),
        int(row["content_x_max"]),
        int(row["content_y_max"]),
    )
    region = content_region(array.shape[:2], bbox)
    padding = ~region.mask
    if not padding.any():
        return int(row["padding_area_pixels"]) == 0
    expected = np.array(
        [
            int(row["padding_color_r"]),
            int(row["padding_color_g"]),
            int(row["padding_color_b"]),
        ],
        dtype=np.uint8,
    )
    return bool(np.all(array[padding] == expected))


def validate_preprocessed_outputs(
    images: pd.DataFrame,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> PreprocessingValidationResult:
    """Reload every declared PNG and detect missing, stale, duplicate, and orphan files."""
    config_errors = validate_preprocessing_config(config)
    if config_errors:
        raise ValueError(
            "Invalid preprocessing configuration: " + "; ".join(config_errors)
        )
    root = find_project_root(project_root)
    schema_result = validate_dataframe(
        images,
        PREPROCESSED_IMAGES_SCHEMA,
        allow_extra_columns=False,
    )
    if not schema_result.passed or schema_result.unexpected_columns:
        raise ValueError(f"Invalid preprocessed images table: {schema_result.to_dict()}")
    notebook_stem = str(config["output"]["notebook_stem"])
    clean_dir = require_notebook_output_path(
        notebook_output_root(notebook_stem, root)
        / str(config["output"]["image_directory"]),
        notebook_stem,
        root,
    )
    expected_paths = {
        resolve_repo_path(path, root): str(painting_id)
        for path, painting_id in zip(images["processed_path"], images["painting_id"])
    }
    actual_paths = set(clean_dir.glob("*.png")) if clean_dir.is_dir() else set()
    orphan_paths = tuple(
        sorted(to_repo_relative(path, root) for path in actual_paths - set(expected_paths))
    )
    checks: list[dict[str, Any]] = []
    observed_hashes: dict[str, list[str]] = {}
    for row in images.to_dict(orient="records"):
        path = resolve_repo_path(row["processed_path"], root)
        exists = path.is_file()
        check = {
            "painting_id": str(row["painting_id"]),
            "processed_path": str(row["processed_path"]),
            "file_exists": exists,
            "reload_passed": False,
            "sha256_matches": False,
            "width_matches": False,
            "height_matches": False,
            "mode_matches": False,
            "format_matches": False,
            "output_icc_absent": False,
            "geometry_reconciles": False,
            "content_bbox_valid": False,
            "padding_pixels_match": False,
            "issue": "",
        }
        issues: list[str] = []
        if not exists:
            issues.append("missing output")
        else:
            actual_sha = _sha256(path)
            check["sha256_matches"] = actual_sha == str(row["sha256"])
            observed_hashes.setdefault(actual_sha, []).append(str(row["painting_id"]))
            if not check["sha256_matches"]:
                issues.append("stale checksum")
            try:
                with Image.open(path) as reloaded:
                    reloaded.load()
                    check["reload_passed"] = True
                    check["width_matches"] = reloaded.width == int(row["width"])
                    check["height_matches"] = reloaded.height == int(row["height"])
                    check["mode_matches"] = reloaded.mode == str(row["mode"])
                    check["format_matches"] = reloaded.format == str(row["format"])
                    check["output_icc_absent"] = not bool(reloaded.info.get("icc_profile"))
                    bbox = (
                        int(row["content_x_min"]),
                        int(row["content_y_min"]),
                        int(row["content_x_max"]),
                        int(row["content_y_max"]),
                    )
                    region = content_region((reloaded.height, reloaded.width), bbox)
                    check["content_bbox_valid"] = (
                        region.validity_status == "valid" and region.bbox == bbox
                    )
                    content_width = bbox[2] - bbox[0]
                    content_height = bbox[3] - bbox[1]
                    canvas_area = reloaded.width * reloaded.height
                    content_area = content_width * content_height
                    check["geometry_reconciles"] = all(
                        (
                            content_width == int(row["resized_width"]),
                            content_height == int(row["resized_height"]),
                            content_width == int(row["content_width"]),
                            content_height == int(row["content_height"]),
                            bbox[0] == int(row["pad_left"]),
                            bbox[1] == int(row["pad_top"]),
                            reloaded.width - bbox[2] == int(row["pad_right"]),
                            reloaded.height - bbox[3] == int(row["pad_bottom"]),
                            content_area == int(row["content_area_pixels"]),
                            canvas_area == int(row["canvas_area_pixels"]),
                            canvas_area - content_area
                            == int(row["padding_area_pixels"]),
                            math.isclose(
                                content_area / canvas_area,
                                float(row["content_area_fraction"]),
                                rel_tol=0,
                                abs_tol=1e-12,
                            ),
                            math.isclose(
                                (canvas_area - content_area) / canvas_area,
                                float(row["padding_area_fraction"]),
                                rel_tol=0,
                                abs_tol=1e-12,
                            ),
                        )
                    )
                    check["padding_pixels_match"] = _padding_pixels_match(
                        np.asarray(reloaded), row
                    )
            except (UnidentifiedImageError, OSError, ValueError) as exc:
                issues.append(f"reload failed: {exc}")
        for key, label in (
            ("width_matches", "width mismatch"),
            ("height_matches", "height mismatch"),
            ("mode_matches", "mode mismatch"),
            ("format_matches", "format mismatch"),
            ("output_icc_absent", "output ICC present"),
            ("content_bbox_valid", "invalid content bbox"),
            ("geometry_reconciles", "geometry mismatch"),
            ("padding_pixels_match", "padding pixel mismatch"),
        ):
            if exists and check["reload_passed"] and not check[key]:
                issues.append(label)
        check["issue"] = "; ".join(issues)
        checks.append(check)
    image_checks = pd.DataFrame(checks, columns=IMAGE_CHECK_COLUMNS)
    duplicate_groups = tuple(
        tuple(sorted(ids))
        for _, ids in sorted(observed_hashes.items())
        if len(ids) > 1
    )
    summary = {
        "missing_output_count": int((~image_checks["file_exists"]).sum()),
        "stale_output_count": int(
            (image_checks["file_exists"] & ~image_checks["sha256_matches"]).sum()
        ),
        "duplicate_sha256_group_count": len(duplicate_groups),
        "orphan_output_count": len(orphan_paths),
        "reload_failure_count": int(
            (image_checks["file_exists"] & ~image_checks["reload_passed"]).sum()
        ),
        "output_width_nonconforming_count": int(
            (image_checks["reload_passed"] & ~image_checks["width_matches"]).sum()
        ),
        "output_height_nonconforming_count": int(
            (image_checks["reload_passed"] & ~image_checks["height_matches"]).sum()
        ),
        "output_mode_nonconforming_count": int(
            (image_checks["reload_passed"] & ~image_checks["mode_matches"]).sum()
        ),
        "output_format_nonconforming_count": int(
            (image_checks["reload_passed"] & ~image_checks["format_matches"]).sum()
        ),
        "invalid_content_bbox_count": int(
            (image_checks["reload_passed"] & ~image_checks["content_bbox_valid"]).sum()
        ),
        "geometry_reconciliation_failure_count": int(
            (
                image_checks["reload_passed"]
                & ~image_checks["geometry_reconciles"]
            ).sum()
        ),
        "padding_pixel_mismatch_count": int(
            (
                image_checks["reload_passed"]
                & ~image_checks["padding_pixels_match"]
            ).sum()
        ),
        "output_icc_present_count": int(
            (image_checks["reload_passed"] & ~image_checks["output_icc_absent"]).sum()
        ),
    }
    return PreprocessingValidationResult(
        image_checks=image_checks,
        summary=summary,
        orphan_paths=orphan_paths,
        duplicate_sha256_groups=duplicate_groups,
    )


def build_preprocessing_audit(
    images: pd.DataFrame,
    artworks: pd.DataFrame,
    runtimes: pd.DataFrame,
    validation: PreprocessingValidationResult,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the single 45-row global and category preprocessing audit."""
    if set(runtimes.columns) != set(RUNTIME_COLUMNS):
        raise ValueError(f"Runtime table must contain exactly {list(RUNTIME_COLUMNS)}")
    if runtimes["painting_id"].duplicated().any():
        raise ValueError("Runtime table contains duplicate painting_id values")
    dataset = config["dataset"]
    records: list[dict[str, Any]] = []

    def add(
        section: str,
        metric_name: str,
        metric_value: int | float,
        metric_unit: str,
        *,
        group_field: str = "",
        group_value: str = "",
        numerator: int | float | str = "",
        denominator: int | float | str = "",
        status: str = "passed",
        details: str = "",
    ) -> None:
        records.append(
            {
                "audit_row_id": f"preprocess_audit_{len(records) + 1:03d}",
                "dataset_id": str(dataset["dataset_id"]),
                "dataset_version": str(dataset["dataset_version"]),
                "dataset_scope": str(dataset["dataset_scope"]),
                "audit_section": section,
                "group_field": group_field,
                "group_value": group_value,
                "metric_name": metric_name,
                "metric_value": metric_value,
                "metric_unit": metric_unit,
                "numerator": numerator,
                "denominator": denominator,
                "status": status,
                "details": details,
            }
        )

    expected_count = int(config["expected"]["processed_output_count"])
    runtime_values = pd.to_numeric(runtimes["runtime_seconds"], errors="raise")
    summary = dict(validation.summary)
    failed_outputs = int((images["status"] != "passed").sum())
    source_hashes = images[["painting_id", "source_sha256"]].merge(
        artworks[["painting_id", "raw_sha256"]],
        on="painting_id",
        how="left",
        validate="one_to_one",
    )
    source_sha_mismatches = int(
        (source_hashes["source_sha256"] != source_hashes["raw_sha256"]).sum()
    )
    accepted_input_count = int(
        (artworks["acceptance_status"] == "accepted").sum()
    )
    orientation_failures = int((images["source_orientation"] != 1).sum())
    nonsrgb_count = int(
        (~images["input_icc_profile_status"].isin(["missing_assumed_srgb", "embedded_srgb"])).sum()
    )
    global_metrics: Sequence[tuple[str, int | float, str, bool]] = (
        (
            "accepted_input_count",
            accepted_input_count,
            "count",
            accepted_input_count == expected_count,
        ),
        ("processed_output_count", len(images), "count", len(images) == expected_count),
        ("failed_output_count", failed_outputs, "count", failed_outputs == 0),
        ("missing_output_count", summary["missing_output_count"], "count", summary["missing_output_count"] == 0),
        ("stale_output_count", summary["stale_output_count"], "count", summary["stale_output_count"] == 0),
        ("duplicate_sha256_group_count", summary["duplicate_sha256_group_count"], "count", summary["duplicate_sha256_group_count"] == 0),
        ("orphan_output_count", summary["orphan_output_count"], "count", summary["orphan_output_count"] == 0),
        ("reload_failure_count", summary["reload_failure_count"], "count", summary["reload_failure_count"] == 0),
        ("output_width_nonconforming_count", summary["output_width_nonconforming_count"], "count", summary["output_width_nonconforming_count"] == 0),
        ("output_height_nonconforming_count", summary["output_height_nonconforming_count"], "count", summary["output_height_nonconforming_count"] == 0),
        ("output_mode_nonconforming_count", summary["output_mode_nonconforming_count"], "count", summary["output_mode_nonconforming_count"] == 0),
        ("output_format_nonconforming_count", summary["output_format_nonconforming_count"], "count", summary["output_format_nonconforming_count"] == 0),
        ("invalid_content_bbox_count", summary["invalid_content_bbox_count"], "count", summary["invalid_content_bbox_count"] == 0),
        ("geometry_reconciliation_failure_count", summary["geometry_reconciliation_failure_count"], "count", summary["geometry_reconciliation_failure_count"] == 0),
        ("padding_pixel_mismatch_count", summary["padding_pixel_mismatch_count"], "count", summary["padding_pixel_mismatch_count"] == 0),
        ("source_sha256_mismatch_count", source_sha_mismatches, "count", source_sha_mismatches == 0),
        ("source_orientation_nonconforming_count", orientation_failures, "count", orientation_failures == 0),
        ("source_icc_missing_count", int((images["input_icc_profile_status"] == "missing_assumed_srgb").sum()), "count", True),
        ("source_icc_srgb_count", int((images["input_icc_profile_status"] == "embedded_srgb").sum()), "count", True),
        ("source_icc_nonsrgb_count", nonsrgb_count, "count", nonsrgb_count == 0),
        ("output_icc_present_count", summary["output_icc_present_count"], "count", summary["output_icc_present_count"] == 0),
        ("total_runtime_seconds", float(runtime_values.sum()), "seconds", True),
        ("mean_runtime_seconds", float(runtime_values.mean()), "seconds", True),
        ("median_runtime_seconds", float(runtime_values.median()), "seconds", True),
        ("p95_runtime_seconds", float(runtime_values.quantile(0.95)), "seconds", True),
    )
    for name, value, unit, passed in global_metrics:
        add(
            "global",
            name,
            value,
            unit,
            status="passed" if passed else "failed",
        )

    grouped = images.merge(
        artworks[["painting_id", "category"]],
        on="painting_id",
        how="left",
        validate="one_to_one",
    )
    for category in config["expected"]["categories"]:
        subset = grouped.loc[grouped["category"] == category]
        category_metrics = (
            ("processed_count", int(len(subset)), "count"),
            ("mean_content_area_fraction", float(subset["content_area_fraction"].mean()), "fraction"),
            ("mean_padding_area_fraction", float(subset["padding_area_fraction"].mean()), "fraction"),
            ("median_resize_scale", float(subset["resize_scale"].median()), "ratio"),
        )
        for name, value, unit in category_metrics:
            add(
                "category",
                name,
                value,
                unit,
                group_field="category",
                group_value=str(category),
                denominator=int(len(subset)),
                status="passed" if len(subset) > 0 else "failed",
            )
    audit = pd.DataFrame(records, columns=PREPROCESSING_AUDIT_COLUMNS)
    schema_result = validate_dataframe(
        audit,
        PREPROCESSING_AUDIT_SCHEMA,
        allow_extra_columns=False,
    )
    if not schema_result.passed or schema_result.unexpected_columns:
        raise RuntimeError(f"Preprocessing audit violates schema: {schema_result.to_dict()}")
    if len(audit) != int(config["expected"]["audit_row_count"]):
        raise RuntimeError("Preprocessing audit row count does not match configuration")
    return audit
