"""Controlled mask-robustness dataset generation utilities."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.damage import (
    DEFAULT_DAMAGE_FILL_COLOR,
    DEFAULT_DAMAGE_FILL_STRATEGY,
    apply_mask_damage,
    compute_file_sha256,
)
from restoration_eval.damage_sensitivity import (
    scale_mask_to_target_area,
)
from restoration_eval.masks import (
    DEFAULT_MASK_SPECS,
    GENERATOR_NAME as MASK_GENERATOR_NAME,
    GENERATOR_VERSION as MASK_GENERATOR_VERSION,
    SUPPORTED_MASK_TYPES,
    _mask_morphology_metadata,
    generate_mask_by_type,
)


GENERATOR_NAME = "mask_robustness"
GENERATOR_VERSION = "1.1.0"

DEFAULT_BASE_MASK_TYPES = (
    "scratch_thin",
    "loss_small",
    "loss_large",
)

DEFAULT_VARIANTS_PER_MASK_TYPE = 5

MASK_FILENAME_SUFFIX = "_mask.png"
DAMAGED_FILENAME_SUFFIX = "_damaged.png"


def _stable_seed(*parts: object, modulus: int = 2**32 - 1) -> int:
    payload = "||".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=False,
    ) % modulus


def _resolve_existing_path(
    path_value: str | Path,
    project_root: str | Path | None = None,
) -> Path:
    path = Path(path_value)

    if path.is_absolute():
        return path

    if project_root is not None:
        candidate = Path(project_root) / path
        if candidate.exists():
            return candidate

    return path


def _safe_relative_string(
    path: str | Path,
    project_root: str | Path | None = None,
) -> str:
    resolved_path = Path(path)

    if project_root is None:
        return resolved_path.as_posix()

    project_root_path = Path(project_root).resolve()

    try:
        return (
            resolved_path.resolve()
            .relative_to(project_root_path)
            .as_posix()
        )
    except ValueError:
        return resolved_path.as_posix()


def _normalise_fill_color(
    fill_color: Sequence[int],
) -> tuple[int, int, int]:
    if len(fill_color) != 3:
        raise ValueError(
            "fill_color must contain exactly three RGB values."
        )

    values = tuple(int(value) for value in fill_color)

    if any(value < 0 or value > 255 for value in values):
        raise ValueError(
            "fill_color values must lie between 0 and 255."
        )

    return values


def _normalise_mask_types(
    mask_types: Iterable[str],
) -> tuple[str, ...]:
    values = tuple(str(value) for value in mask_types)

    if not values:
        raise ValueError(
            "At least one mask type is required."
        )

    if len(values) != len(set(values)):
        raise ValueError(
            "Mask types must be unique."
        )

    unsupported = sorted(
        set(values) - set(SUPPORTED_MASK_TYPES)
    )

    if unsupported:
        raise ValueError(
            f"Unsupported mask types: {unsupported}"
        )

    if "zero_control" in values:
        raise ValueError(
            "zero_control is not valid for mask-robustness variation."
        )

    return values


def _normalise_target_percentages(
    mask_types: Sequence[str],
    target_percentages: Mapping[str, float] | None,
) -> dict[str, float]:
    source = (
        {
            mask_type: float(
                DEFAULT_MASK_SPECS[mask_type]["target_area_pct"]
            )
            for mask_type in mask_types
        }
        if target_percentages is None
        else {
            str(key): float(value)
            for key, value in target_percentages.items()
        }
    )

    missing = sorted(
        set(mask_types) - set(source)
    )

    if missing:
        raise ValueError(
            "Missing target percentages for mask types: "
            f"{missing}"
        )

    normalised = {
        mask_type: float(source[mask_type])
        for mask_type in mask_types
    }

    if any(
        not np.isfinite(value)
        or value <= 0.0
        or value >= 100.0
        for value in normalised.values()
    ):
        raise ValueError(
            "Target percentages must be finite and between 0 and 100."
        )

    return normalised


def _extract_clean_path_value(row: pd.Series) -> str | Path:
    candidates = (
        "processed_path",
        "clean_path",
        "image_path",
        "processed_image_path",
    )

    for column in candidates:
        if column in row.index and pd.notna(row[column]):
            return row[column]

    raise ValueError(
        "Processed metadata does not contain a usable clean-image path."
    )


def _content_box_from_row(
    row: pd.Series,
    target_size: int,
) -> tuple[int, int, int, int]:
    required = (
        "content_x_min",
        "content_y_min",
        "content_x_max",
        "content_y_max",
    )

    missing = [
        column
        for column in required
        if column not in row.index or pd.isna(row[column])
    ]

    if missing:
        raise ValueError(
            "Processed metadata is missing content-box values: "
            f"{missing}"
        )

    content_box = tuple(
        int(row[column])
        for column in required
    )

    x_min, y_min, x_max, y_max = content_box

    if not (
        0 <= x_min < x_max <= target_size
        and 0 <= y_min < y_max <= target_size
    ):
        raise ValueError(
            f"Invalid content box {content_box} "
            f"for target size {target_size}."
        )

    return content_box


def _location_metadata(
    mask_array: np.ndarray,
    content_box: tuple[int, int, int, int],
) -> dict[str, Any]:
    binary_mask = mask_array.astype(bool)
    ys, xs = np.where(binary_mask)

    x_min, y_min, x_max, y_max = content_box
    content_width = x_max - x_min
    content_height = y_max - y_min

    if len(xs) == 0:
        return {
            "centroid_x_pixels": np.nan,
            "centroid_y_pixels": np.nan,
            "centroid_x_normalised_content": np.nan,
            "centroid_y_normalised_content": np.nan,
            "centroid_quadrant": "none",
            "mask_bbox_width_normalised_content": 0.0,
            "mask_bbox_height_normalised_content": 0.0,
            "mask_bbox_area_fraction_content_bbox": 0.0,
            "touches_left_content_border": False,
            "touches_right_content_border": False,
            "touches_top_content_border": False,
            "touches_bottom_content_border": False,
        }

    centroid_x = float(xs.mean())
    centroid_y = float(ys.mean())

    centroid_x_normalised = (
        (centroid_x - x_min)
        / max(1, content_width - 1)
    )
    centroid_y_normalised = (
        (centroid_y - y_min)
        / max(1, content_height - 1)
    )

    horizontal = (
        "left"
        if centroid_x_normalised < 0.5
        else "right"
    )
    vertical = (
        "top"
        if centroid_y_normalised < 0.5
        else "bottom"
    )

    bbox_x_min = int(xs.min())
    bbox_x_max = int(xs.max()) + 1
    bbox_y_min = int(ys.min())
    bbox_y_max = int(ys.max()) + 1

    bbox_width = bbox_x_max - bbox_x_min
    bbox_height = bbox_y_max - bbox_y_min

    return {
        "centroid_x_pixels": centroid_x,
        "centroid_y_pixels": centroid_y,
        "centroid_x_normalised_content": float(
            centroid_x_normalised
        ),
        "centroid_y_normalised_content": float(
            centroid_y_normalised
        ),
        "centroid_quadrant": (
            f"{vertical}_{horizontal}"
        ),
        "mask_bbox_width_normalised_content": float(
            bbox_width / content_width
        ),
        "mask_bbox_height_normalised_content": float(
            bbox_height / content_height
        ),
        "mask_bbox_area_fraction_content_bbox": float(
            (bbox_width * bbox_height)
            / (content_width * content_height)
        ),
        "touches_left_content_border": bool(
            binary_mask[y_min:y_max, x_min].any()
        ),
        "touches_right_content_border": bool(
            binary_mask[y_min:y_max, x_max - 1].any()
        ),
        "touches_top_content_border": bool(
            binary_mask[y_min, x_min:x_max].any()
        ),
        "touches_bottom_content_border": bool(
            binary_mask[y_max - 1, x_min:x_max].any()
        ),
    }


def create_mask_robustness_dataset(
    processed_metadata: pd.DataFrame,
    output_mask_dir: str | Path,
    output_damaged_dir: str | Path,
    project_root: str | Path | None = None,
    mask_types: Iterable[str] = DEFAULT_BASE_MASK_TYPES,
    target_percentages: Mapping[str, float] | None = None,
    variants_per_mask_type: int = DEFAULT_VARIANTS_PER_MASK_TYPE,
    target_size: int = 768,
    fill_color: Sequence[int] = DEFAULT_DAMAGE_FILL_COLOR,
    fill_strategy: str = DEFAULT_DAMAGE_FILL_STRATEGY,
    global_seed: int = 20260606,
    maximum_percentage_error: float = 0.50,
    maximum_generation_attempts: int = 20,
    overwrite: bool = True,
    compute_checksums: bool = True,
) -> pd.DataFrame:
    """Generate matched mask variants for robustness experiments."""
    required_columns = {
        "painting_id",
        "content_x_min",
        "content_y_min",
        "content_x_max",
        "content_y_max",
    }

    missing_columns = sorted(
        required_columns - set(processed_metadata.columns)
    )

    if missing_columns:
        raise ValueError(
            "Processed metadata is missing required columns: "
            f"{missing_columns}"
        )

    if variants_per_mask_type < 2:
        raise ValueError(
            "variants_per_mask_type must be at least 2."
        )

    if target_size <= 0:
        raise ValueError(
            "target_size must be positive."
        )

    if maximum_percentage_error < 0:
        raise ValueError(
            "maximum_percentage_error cannot be negative."
        )

    if maximum_generation_attempts <= 0:
        raise ValueError(
            "maximum_generation_attempts must be positive."
        )

    mask_type_values = _normalise_mask_types(mask_types)
    target_percentage_values = _normalise_target_percentages(
        mask_type_values,
        target_percentages,
    )
    fill_color_value = _normalise_fill_color(fill_color)

    metadata = processed_metadata.copy()
    metadata["painting_id"] = (
        metadata["painting_id"].astype(str)
    )

    if metadata["painting_id"].duplicated().any():
        raise ValueError(
            "Processed metadata contains duplicate painting IDs."
        )

    project_root_path = (
        Path(project_root)
        if project_root is not None
        else None
    )

    mask_output_path = Path(output_mask_dir)
    damaged_output_path = Path(output_damaged_dir)

    mask_output_path.mkdir(
        parents=True,
        exist_ok=True,
    )
    damaged_output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    records: list[dict[str, Any]] = []

    for painting_index, row in (
        metadata
        .sort_values("painting_id", kind="stable")
        .reset_index(drop=True)
        .iterrows()
    ):
        painting_id = str(row["painting_id"])
        clean_path = _resolve_existing_path(
            _extract_clean_path_value(row),
            project_root_path,
        )

        if not clean_path.exists():
            raise FileNotFoundError(
                f"Clean image not found: {clean_path}"
            )

        with Image.open(clean_path) as opened_clean_image:
            clean_rgb = opened_clean_image.convert("RGB")
            clean_rgb.load()

        width, height = clean_rgb.size

        if width != height or width != target_size:
            raise ValueError(
                f"Expected a {target_size}x{target_size} clean image, "
                f"received {width}x{height} for {painting_id}."
            )

        content_box = _content_box_from_row(
            row,
            target_size=target_size,
        )

        content_area_pixels = int(
            (content_box[2] - content_box[0])
            * (content_box[3] - content_box[1])
        )

        clean_sha256 = (
            compute_file_sha256(clean_path)
            if compute_checksums
            else None
        )

        painting_seed = _stable_seed(
            global_seed,
            painting_id,
        )

        for mask_type_index, mask_type in enumerate(
            mask_type_values
        ):
            target_percentage = (
                target_percentage_values[mask_type]
            )
            target_pixels = max(
                1,
                int(
                    round(
                        content_area_pixels
                        * target_percentage
                        / 100.0
                    )
                ),
            )

            robustness_group_id = (
                f"{painting_id}__{mask_type}"
            )

            mask_seed = _stable_seed(
                painting_seed,
                mask_type,
                mask_type_index,
            )

            for variant_index in range(
                1,
                variants_per_mask_type + 1,
            ):
                variant_seed = _stable_seed(
                    mask_seed,
                    variant_index,
                )

                selected_attempt_index: int | None = None
                selected_generation_seed: int | None = None
                selected_raw_mask_array: np.ndarray | None = None
                selected_scale_result: dict[str, Any] | None = None
                selected_absolute_percentage_error: float | None = None

                for generation_attempt_index in range(
                    1,
                    maximum_generation_attempts + 1,
                ):
                    generation_seed = _stable_seed(
                        variant_seed,
                        generation_attempt_index,
                    )

                    rng = np.random.default_rng(
                        generation_seed
                    )

                    raw_mask = generate_mask_by_type(
                        mask_type=mask_type,
                        rng=rng,
                        target_size=target_size,
                        content_box=content_box,
                    )

                    raw_mask_array = (
                        np.asarray(
                            raw_mask.convert("L")
                        ) > 0
                    ).astype(np.uint8)

                    scale_result = scale_mask_to_target_area(
                        base_mask=raw_mask_array,
                        target_pixels=target_pixels,
                        content_bbox=content_box,
                    )

                    candidate_mask_array = (
                        scale_result["mask"]
                        .astype(np.uint8)
                    )

                    candidate_realised_pixels = int(
                        candidate_mask_array.sum()
                    )

                    candidate_realised_percentage = (
                        100.0
                        * candidate_realised_pixels
                        / content_area_pixels
                    )

                    candidate_absolute_percentage_error = abs(
                        candidate_realised_percentage
                        - target_percentage
                    )

                    if (
                        selected_absolute_percentage_error is None
                        or candidate_absolute_percentage_error
                        < selected_absolute_percentage_error
                    ):
                        selected_attempt_index = int(
                            generation_attempt_index
                        )
                        selected_generation_seed = int(
                            generation_seed
                        )
                        selected_raw_mask_array = raw_mask_array
                        selected_scale_result = scale_result
                        selected_absolute_percentage_error = float(
                            candidate_absolute_percentage_error
                        )

                    if (
                        candidate_absolute_percentage_error
                        <= maximum_percentage_error
                    ):
                        break

                if (
                    selected_raw_mask_array is None
                    or selected_scale_result is None
                    or selected_attempt_index is None
                    or selected_generation_seed is None
                ):
                    raise RuntimeError(
                        "Mask generation did not produce "
                        "a usable candidate."
                    )

                if (
                    selected_absolute_percentage_error is None
                    or selected_absolute_percentage_error
                    > maximum_percentage_error
                ):
                    raise RuntimeError(
                        "Could not generate a mask within the "
                        "configured area tolerance after "
                        f"{maximum_generation_attempts} attempts: "
                        f"painting_id={painting_id}, "
                        f"mask_type={mask_type}, "
                        f"variant_index={variant_index}, "
                        "best_error="
                        f"{selected_absolute_percentage_error:.6f}"
                    )

                raw_mask_array = selected_raw_mask_array
                scale_result = selected_scale_result
                generated_mask_array = (
                    scale_result["mask"]
                    .astype(np.uint8)
                )

                generated_mask_image = Image.fromarray(
                    generated_mask_array * 255,
                    mode="L",
                )

                variant_token = (
                    f"variant_{variant_index:02d}"
                )
                case_id = (
                    f"{robustness_group_id}"
                    f"__{variant_token}"
                )
                variant_id = case_id

                mask_filename = (
                    f"{case_id}{MASK_FILENAME_SUFFIX}"
                )
                damaged_filename = (
                    f"{case_id}{DAMAGED_FILENAME_SUFFIX}"
                )

                mask_path = (
                    mask_output_path / mask_filename
                )
                damaged_path = (
                    damaged_output_path / damaged_filename
                )

                generation_action = "generated"

                if (
                    not overwrite
                    and mask_path.exists()
                    and damaged_path.exists()
                ):
                    generation_action = "reused_existing"
                    with Image.open(mask_path) as saved_mask:
                        generated_mask_image = (
                            saved_mask.convert("L")
                        )
                        generated_mask_image.load()

                    generated_mask_array = (
                        np.asarray(
                            generated_mask_image
                        ) > 0
                    ).astype(np.uint8)

                else:
                    generated_mask_image.save(
                        mask_path,
                        format="PNG",
                    )

                    damaged_image = apply_mask_damage(
                        clean_rgb,
                        generated_mask_image,
                        fill_color_value,
                    )
                    damaged_image.save(
                        damaged_path,
                        format="PNG",
                    )

                realised_pixels = int(
                    generated_mask_array.sum()
                )
                realised_percentage_content = (
                    100.0
                    * realised_pixels
                    / content_area_pixels
                )
                percentage_error_content = (
                    realised_percentage_content
                    - target_percentage
                )

                morphology = _mask_morphology_metadata(
                    mask=generated_mask_image,
                    target_size=target_size,
                    content_box=content_box,
                )
                location = _location_metadata(
                    generated_mask_array,
                    content_box,
                )

                mask_sha256 = (
                    compute_file_sha256(mask_path)
                    if compute_checksums
                    else None
                )
                damaged_sha256 = (
                    compute_file_sha256(damaged_path)
                    if compute_checksums
                    else None
                )

                record: dict[str, Any] = {
                    "case_id": case_id,
                    "variant_id": variant_id,
                    "robustness_group_id": (
                        robustness_group_id
                    ),
                    "painting_id": painting_id,
                    "painting_index": int(
                        painting_index
                    ),
                    "base_mask_type": mask_type,
                    "mask_type_index": int(
                        mask_type_index
                    ),
                    "variant_index": int(
                        variant_index
                    ),
                    "global_seed": int(
                        global_seed
                    ),
                    "painting_seed": int(
                        painting_seed
                    ),
                    "mask_seed": int(
                        mask_seed
                    ),
                    "variant_seed": int(
                        variant_seed
                    ),
                    "generation_attempt_index": int(
                        selected_attempt_index
                    ),
                    "generation_seed": int(
                        selected_generation_seed
                    ),
                    "maximum_generation_attempts": int(
                        maximum_generation_attempts
                    ),
                    "generation_area_tolerance": float(
                        maximum_percentage_error
                    ),
                    "target_percentage_content": float(
                        target_percentage
                    ),
                    "target_pixels": int(
                        target_pixels
                    ),
                    "realised_pixels": int(
                        realised_pixels
                    ),
                    "realised_percentage_content": float(
                        realised_percentage_content
                    ),
                    "percentage_error_content": float(
                        percentage_error_content
                    ),
                    "absolute_percentage_error_content": float(
                        abs(
                            percentage_error_content
                        )
                    ),
                    "scale_factor": float(
                        scale_result["scale_factor"]
                    ),
                    "raw_mask_pixels": int(
                        raw_mask_array.sum()
                    ),
                    "content_area_pixels": int(
                        content_area_pixels
                    ),
                    "content_x_min": int(
                        content_box[0]
                    ),
                    "content_y_min": int(
                        content_box[1]
                    ),
                    "content_x_max": int(
                        content_box[2]
                    ),
                    "content_y_max": int(
                        content_box[3]
                    ),
                    "width": int(width),
                    "height": int(height),
                    **morphology,
                    **location,
                    "damage_fill_strategy": (
                        fill_strategy
                    ),
                    "damage_fill_r": int(
                        fill_color_value[0]
                    ),
                    "damage_fill_g": int(
                        fill_color_value[1]
                    ),
                    "damage_fill_b": int(
                        fill_color_value[2]
                    ),
                    "clean_path": _safe_relative_string(
                        clean_path,
                        project_root_path,
                    ),
                    "mask_filename": mask_filename,
                    "mask_path": _safe_relative_string(
                        mask_path,
                        project_root_path,
                    ),
                    "damaged_filename": damaged_filename,
                    "damaged_path": _safe_relative_string(
                        damaged_path,
                        project_root_path,
                    ),
                    "clean_sha256": clean_sha256,
                    "mask_sha256": mask_sha256,
                    "damaged_sha256": damaged_sha256,
                    "mask_file_size_bytes": (
                        mask_path.stat().st_size
                    ),
                    "damaged_file_size_bytes": (
                        damaged_path.stat().st_size
                    ),
                    "mask_generator_name": (
                        MASK_GENERATOR_NAME
                    ),
                    "mask_generator_version": (
                        MASK_GENERATOR_VERSION
                    ),
                    "generator_name": GENERATOR_NAME,
                    "generator_version": (
                        GENERATOR_VERSION
                    ),
                    "generated_at_utc": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                    "generation_action": (
                        generation_action
                    ),
                    "status": "ok",
                    "issue": "",
                }

                for metadata_column in (
                    "source",
                    "title",
                    "artist",
                    "style_group",
                    "category",
                    "genre",
                ):
                    if metadata_column in row.index:
                        record[metadata_column] = (
                            row[metadata_column]
                        )

                records.append(record)

    result = pd.DataFrame(records)

    expected_rows = (
        len(metadata)
        * len(mask_type_values)
        * variants_per_mask_type
    )

    if len(result) != expected_rows:
        raise RuntimeError(
            f"Expected {expected_rows} robustness cases, "
            f"generated {len(result)}."
        )

    return (
        result
        .sort_values(
            [
                "painting_id",
                "base_mask_type",
                "variant_index",
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def validate_mask_robustness_dataset(
    robustness_metadata: pd.DataFrame,
    project_root: str | Path | None = None,
    verify_checksums: bool = True,
    maximum_percentage_error: float = 0.50,
) -> pd.DataFrame:
    """Validate saved robustness masks and corresponding damaged images."""
    required_columns = {
        "case_id",
        "painting_id",
        "base_mask_type",
        "variant_index",
        "target_percentage_content",
        "realised_pixels",
        "realised_percentage_content",
        "content_area_pixels",
        "width",
        "height",
        "clean_path",
        "mask_path",
        "damaged_path",
        "damage_fill_r",
        "damage_fill_g",
        "damage_fill_b",
    }

    missing_columns = sorted(
        required_columns - set(robustness_metadata.columns)
    )

    if missing_columns:
        raise ValueError(
            "Robustness metadata is missing required columns: "
            f"{missing_columns}"
        )

    project_root_path = (
        Path(project_root)
        if project_root is not None
        else None
    )

    records: list[dict[str, Any]] = []

    for _, row in robustness_metadata.iterrows():
        case_id = str(row["case_id"])
        issues: list[str] = []

        clean_path = _resolve_existing_path(
            row["clean_path"],
            project_root_path,
        )
        mask_path = _resolve_existing_path(
            row["mask_path"],
            project_root_path,
        )
        damaged_path = _resolve_existing_path(
            row["damaged_path"],
            project_root_path,
        )

        clean_exists = clean_path.exists()
        mask_exists = mask_path.exists()
        damaged_exists = damaged_path.exists()

        if not clean_exists:
            issues.append("clean_file_missing")
        if not mask_exists:
            issues.append("mask_file_missing")
        if not damaged_exists:
            issues.append("damaged_file_missing")

        readable = False
        dimensions_valid = False
        mask_mode_valid = False
        damaged_mode_valid = False
        mask_format_valid = False
        damaged_format_valid = False
        binary_mask_valid = False
        realised_pixels_match = False
        realised_percentage_match = False
        target_error_valid = False
        outside_mask_preserved = False
        masked_fill_valid = False
        checksum_valid = True

        observed_mask_pixels = np.nan
        observed_percentage_content = np.nan
        outside_mask_changed_pixels = np.nan
        inside_mask_not_fill_pixels = np.nan

        try:
            if clean_exists and mask_exists and damaged_exists:
                with Image.open(clean_path) as clean_image:
                    clean_array = np.asarray(
                        clean_image.convert("RGB")
                    )

                with Image.open(mask_path) as mask_image:
                    mask_format = mask_image.format
                    mask_mode = mask_image.mode
                    mask_array = np.asarray(
                        mask_image.convert("L")
                    )

                with Image.open(damaged_path) as damaged_image:
                    damaged_format = damaged_image.format
                    damaged_mode = damaged_image.mode
                    damaged_array = np.asarray(
                        damaged_image.convert("RGB")
                    )

                readable = True
                expected_shape = (
                    int(row["height"]),
                    int(row["width"]),
                )

                dimensions_valid = bool(
                    clean_array.shape[:2] == expected_shape
                    and mask_array.shape == expected_shape
                    and damaged_array.shape[:2] == expected_shape
                )
                mask_mode_valid = mask_mode == "L"
                damaged_mode_valid = damaged_mode == "RGB"
                mask_format_valid = mask_format == "PNG"
                damaged_format_valid = damaged_format == "PNG"

                unique_values = set(
                    np.unique(mask_array)
                    .astype(int)
                    .tolist()
                )
                binary_mask_valid = (
                    unique_values.issubset({0, 255})
                )

                binary_mask = mask_array > 0
                observed_mask_pixels = int(
                    binary_mask.sum()
                )
                realised_pixels_match = (
                    observed_mask_pixels
                    == int(row["realised_pixels"])
                )

                content_area_pixels = int(
                    row["content_area_pixels"]
                )
                observed_percentage_content = (
                    100.0
                    * observed_mask_pixels
                    / content_area_pixels
                )

                realised_percentage_match = bool(
                    np.isclose(
                        observed_percentage_content,
                        float(
                            row[
                                "realised_percentage_content"
                            ]
                        ),
                        atol=1e-9,
                    )
                )

                target_error_valid = bool(
                    abs(
                        observed_percentage_content
                        - float(
                            row[
                                "target_percentage_content"
                            ]
                        )
                    )
                    <= maximum_percentage_error
                )

                changed_pixels = np.any(
                    clean_array != damaged_array,
                    axis=2,
                )

                outside_mask_changed_pixels = int(
                    (
                        changed_pixels
                        & ~binary_mask
                    ).sum()
                )

                fill_color = np.array(
                    [
                        int(row["damage_fill_r"]),
                        int(row["damage_fill_g"]),
                        int(row["damage_fill_b"]),
                    ],
                    dtype=np.uint8,
                )

                inside_mask_not_fill_pixels = int(
                    (
                        binary_mask
                        & np.any(
                            damaged_array != fill_color,
                            axis=2,
                        )
                    ).sum()
                )

                outside_mask_preserved = (
                    outside_mask_changed_pixels == 0
                )
                masked_fill_valid = (
                    inside_mask_not_fill_pixels == 0
                )

                if verify_checksums:
                    checksum_fields = (
                        (
                            clean_path,
                            "clean_sha256",
                        ),
                        (
                            mask_path,
                            "mask_sha256",
                        ),
                        (
                            damaged_path,
                            "damaged_sha256",
                        ),
                    )

                    for checksum_path, checksum_column in checksum_fields:
                        expected_checksum = row.get(
                            checksum_column,
                            None,
                        )

                        if (
                            expected_checksum is None
                            or pd.isna(expected_checksum)
                            or str(expected_checksum).strip() == ""
                        ):
                            checksum_valid = False
                            issues.append(
                                f"{checksum_column}_missing"
                            )
                            continue

                        observed_checksum = (
                            compute_file_sha256(
                                checksum_path
                            )
                        )

                        if observed_checksum != str(
                            expected_checksum
                        ):
                            checksum_valid = False
                            issues.append(
                                f"{checksum_column}_mismatch"
                            )

        except Exception as exc:
            issues.append(
                f"{type(exc).__name__}: {exc}"
            )

        checks = {
            "dimensions_valid": dimensions_valid,
            "mask_mode_valid": mask_mode_valid,
            "damaged_mode_valid": damaged_mode_valid,
            "mask_format_valid": mask_format_valid,
            "damaged_format_valid": damaged_format_valid,
            "binary_mask_valid": binary_mask_valid,
            "realised_pixels_match": realised_pixels_match,
            "realised_percentage_match": realised_percentage_match,
            "target_error_valid": target_error_valid,
            "outside_mask_preserved": outside_mask_preserved,
            "masked_fill_valid": masked_fill_valid,
            "checksum_valid": checksum_valid,
        }

        for check_name, passed in checks.items():
            if readable and not passed:
                issues.append(check_name)

        validation_passed = bool(
            clean_exists
            and mask_exists
            and damaged_exists
            and readable
            and all(checks.values())
        )

        records.append(
            {
                "case_id": case_id,
                "painting_id": row["painting_id"],
                "base_mask_type": (
                    row["base_mask_type"]
                ),
                "variant_index": int(
                    row["variant_index"]
                ),
                "clean_exists": clean_exists,
                "mask_exists": mask_exists,
                "damaged_exists": damaged_exists,
                "readable": readable,
                **checks,
                "metadata_realised_pixels": int(
                    row["realised_pixels"]
                ),
                "observed_mask_pixels": (
                    observed_mask_pixels
                ),
                "metadata_realised_percentage_content": float(
                    row[
                        "realised_percentage_content"
                    ]
                ),
                "observed_percentage_content": (
                    observed_percentage_content
                ),
                "maximum_percentage_error": float(
                    maximum_percentage_error
                ),
                "outside_mask_changed_pixels": (
                    outside_mask_changed_pixels
                ),
                "inside_mask_not_fill_pixels": (
                    inside_mask_not_fill_pixels
                ),
                "validation_passed": (
                    validation_passed
                ),
                "issue": "|".join(
                    sorted(set(issues))
                ),
            }
        )

    return pd.DataFrame(records)


def audit_mask_robustness_inventory(
    robustness_metadata: pd.DataFrame,
    mask_dir: str | Path,
    damaged_dir: str | Path,
    expected_case_ids: Iterable[str] | None = None,
    project_root: str | Path | None = None,
) -> dict[str, pd.DataFrame]:
    """Audit duplicate, missing, unexpected, and orphan robustness cases."""
    metadata = robustness_metadata.copy()
    metadata["case_id"] = metadata["case_id"].astype(str)

    project_root_path = (
        Path(project_root)
        if project_root is not None
        else None
    )

    duplicate_case_rows = metadata[
        metadata["case_id"].duplicated(
            keep=False
        )
    ].copy()

    duplicate_mask_path_rows = metadata[
        metadata["mask_path"].astype(str).duplicated(
            keep=False
        )
    ].copy()

    duplicate_damaged_path_rows = metadata[
        metadata["damaged_path"].astype(str).duplicated(
            keep=False
        )
    ].copy()

    metadata_case_ids = set(
        metadata["case_id"].tolist()
    )
    expected_case_id_set = (
        {
            str(value)
            for value in expected_case_ids
        }
        if expected_case_ids is not None
        else metadata_case_ids
    )

    missing_case_rows = pd.DataFrame(
        {
            "case_id": sorted(
                expected_case_id_set
                - metadata_case_ids
            )
        }
    )

    unexpected_case_rows = pd.DataFrame(
        {
            "case_id": sorted(
                metadata_case_ids
                - expected_case_id_set
            )
        }
    )

    missing_mask_records = []
    missing_damaged_records = []

    expected_mask_filenames = set()
    expected_damaged_filenames = set()

    for _, row in metadata.iterrows():
        mask_path = _resolve_existing_path(
            row["mask_path"],
            project_root_path,
        )
        damaged_path = _resolve_existing_path(
            row["damaged_path"],
            project_root_path,
        )

        expected_mask_filenames.add(
            str(row["mask_filename"])
        )
        expected_damaged_filenames.add(
            str(row["damaged_filename"])
        )

        if not mask_path.exists():
            missing_mask_records.append(
                {
                    "case_id": row["case_id"],
                    "mask_path": str(mask_path),
                }
            )

        if not damaged_path.exists():
            missing_damaged_records.append(
                {
                    "case_id": row["case_id"],
                    "damaged_path": str(
                        damaged_path
                    ),
                }
            )

    mask_directory = Path(mask_dir)
    damaged_directory = Path(damaged_dir)

    actual_mask_filenames = {
        path.name
        for path in mask_directory.glob(
            f"*{MASK_FILENAME_SUFFIX}"
        )
        if path.is_file()
    }
    actual_damaged_filenames = {
        path.name
        for path in damaged_directory.glob(
            f"*{DAMAGED_FILENAME_SUFFIX}"
        )
        if path.is_file()
    }

    orphan_mask_rows = pd.DataFrame(
        {
            "mask_filename": sorted(
                actual_mask_filenames
                - expected_mask_filenames
            )
        }
    )
    orphan_damaged_rows = pd.DataFrame(
        {
            "damaged_filename": sorted(
                actual_damaged_filenames
                - expected_damaged_filenames
            )
        }
    )

    missing_mask_file_rows = pd.DataFrame(
        missing_mask_records
    )
    missing_damaged_file_rows = pd.DataFrame(
        missing_damaged_records
    )

    summary_df = pd.DataFrame(
        [
            {
                "check": "duplicate_case_ids",
                "issue_count": int(
                    duplicate_case_rows[
                        "case_id"
                    ].nunique()
                    if not duplicate_case_rows.empty
                    else 0
                ),
            },
            {
                "check": "duplicate_mask_paths",
                "issue_count": int(
                    duplicate_mask_path_rows[
                        "mask_path"
                    ].nunique()
                    if not duplicate_mask_path_rows.empty
                    else 0
                ),
            },
            {
                "check": "duplicate_damaged_paths",
                "issue_count": int(
                    duplicate_damaged_path_rows[
                        "damaged_path"
                    ].nunique()
                    if not duplicate_damaged_path_rows.empty
                    else 0
                ),
            },
            {
                "check": "missing_expected_cases",
                "issue_count": len(
                    missing_case_rows
                ),
            },
            {
                "check": "unexpected_metadata_cases",
                "issue_count": len(
                    unexpected_case_rows
                ),
            },
            {
                "check": "missing_mask_files",
                "issue_count": len(
                    missing_mask_file_rows
                ),
            },
            {
                "check": "missing_damaged_files",
                "issue_count": len(
                    missing_damaged_file_rows
                ),
            },
            {
                "check": "orphan_mask_files",
                "issue_count": len(
                    orphan_mask_rows
                ),
            },
            {
                "check": "orphan_damaged_files",
                "issue_count": len(
                    orphan_damaged_rows
                ),
            },
        ]
    )

    summary_df["passed"] = (
        summary_df["issue_count"] == 0
    )

    return {
        "summary": summary_df,
        "duplicate_case_rows": (
            duplicate_case_rows
        ),
        "duplicate_mask_path_rows": (
            duplicate_mask_path_rows
        ),
        "duplicate_damaged_path_rows": (
            duplicate_damaged_path_rows
        ),
        "missing_case_rows": (
            missing_case_rows
        ),
        "unexpected_case_rows": (
            unexpected_case_rows
        ),
        "missing_mask_file_rows": (
            missing_mask_file_rows
        ),
        "missing_damaged_file_rows": (
            missing_damaged_file_rows
        ),
        "orphan_mask_file_rows": (
            orphan_mask_rows
        ),
        "orphan_damaged_file_rows": (
            orphan_damaged_rows
        ),
    }
