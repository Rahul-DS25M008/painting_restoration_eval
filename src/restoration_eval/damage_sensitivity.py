from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.damage import (
    DEFAULT_DAMAGE_FILL_COLOR,
    DEFAULT_DAMAGE_FILL_STRATEGY,
    apply_mask_damage,
    compute_file_sha256,
)


GENERATOR_NAME = "damage_size_sensitivity"
GENERATOR_VERSION = "1.1.0"

DEFAULT_TARGET_PERCENTAGES = (
    2.0,
    4.0,
    6.0,
    8.0,
    10.0,
    15.0,
    20.0,
)

DEFAULT_BASE_MASK_TYPES = (
    "loss_large",
)

MASK_FILENAME_SUFFIX = "_mask.png"
DAMAGED_FILENAME_SUFFIX = "_damaged.png"


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


def _normalise_percentages(
    target_percentages: Iterable[float],
) -> tuple[float, ...]:
    values = tuple(
        float(value)
        for value in target_percentages
    )

    if not values:
        raise ValueError(
            "At least one target damage percentage is required."
        )

    if any(
        not np.isfinite(value)
        for value in values
    ):
        raise ValueError(
            "Target damage percentages must be finite."
        )

    if any(
        value <= 0.0 or value >= 100.0
        for value in values
    ):
        raise ValueError(
            "Target damage percentages must be greater than "
            "0 and less than 100."
        )

    if len(set(values)) != len(values):
        raise ValueError(
            "Target damage percentages must be unique."
        )

    return tuple(sorted(values))


def _normalise_fill_color(
    fill_color: Sequence[int],
) -> tuple[int, int, int]:
    if len(fill_color) != 3:
        raise ValueError(
            "fill_color must contain exactly three RGB values."
        )

    normalised = tuple(
        int(value)
        for value in fill_color
    )

    if any(
        value < 0 or value > 255
        for value in normalised
    ):
        raise ValueError(
            "fill_color values must lie between 0 and 255."
        )

    return normalised


def _stable_seed(
    global_seed: int,
    painting_id: str,
    mask_type: str,
) -> int:
    seed_text = (
        f"{int(global_seed)}|{painting_id}|{mask_type}"
    )

    digest = hashlib.sha256(
        seed_text.encode("utf-8")
    ).hexdigest()

    return int(
        digest[:8],
        16,
    )


def _format_percentage_token(
    percentage: float,
) -> str:
    if float(percentage).is_integer():
        return f"{int(percentage):02d}pct"

    token = (
        f"{percentage:.2f}"
        .rstrip("0")
        .rstrip(".")
        .replace(".", "p")
    )

    return f"{token}pct"


def _normalise_binary_mask(
    mask_array: np.ndarray,
) -> np.ndarray:
    if mask_array.ndim == 3:
        mask_array = mask_array[..., 0]

    if mask_array.ndim != 2:
        raise ValueError(
            "Mask must be a two-dimensional array."
        )

    return (
        mask_array > 0
    ).astype(np.uint8)


def _extract_mask_bbox(
    binary_mask: np.ndarray,
) -> tuple[int, int, int, int] | None:
    y_values, x_values = np.nonzero(
        binary_mask
    )

    if len(x_values) == 0:
        return None

    left = int(x_values.min())
    top = int(y_values.min())
    right = int(x_values.max()) + 1
    bottom = int(y_values.max()) + 1

    return (
        left,
        top,
        right,
        bottom,
    )


def _extract_mask_centroid(
    binary_mask: np.ndarray,
) -> tuple[float, float] | None:
    y_values, x_values = np.nonzero(
        binary_mask
    )

    if len(x_values) == 0:
        return None

    return (
        float(x_values.mean()),
        float(y_values.mean()),
    )


def _find_first_present_value(
    row: pd.Series,
    candidate_columns: Sequence[str],
) -> Any | None:
    for column in candidate_columns:
        if column not in row.index:
            continue

        value = row[column]

        if pd.notna(value):
            return value

    return None


def _extract_content_bbox(
    row: pd.Series,
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    bbox_column_groups = (
        (
            "content_bbox_left",
            "content_bbox_top",
            "content_bbox_right",
            "content_bbox_bottom",
        ),
        (
            "content_x_min",
            "content_y_min",
            "content_x_max",
            "content_y_max",
        ),
        (
            "content_x0",
            "content_y0",
            "content_x1",
            "content_y1",
        ),
        (
            "content_left",
            "content_top",
            "content_right",
            "content_bottom",
        ),
    )

    for columns in bbox_column_groups:
        if not all(
            column in row.index
            for column in columns
        ):
            continue

        values = [
            row[column]
            for column in columns
        ]

        if any(
            pd.isna(value)
            for value in values
        ):
            continue

        left, top, right, bottom = (
            int(round(float(value)))
            for value in values
        )

        left = max(0, min(left, width))
        top = max(0, min(top, height))
        right = max(left, min(right, width))
        bottom = max(top, min(bottom, height))

        if right > left and bottom > top:
            return (
                left,
                top,
                right,
                bottom,
            )

    bbox_json_value = _find_first_present_value(
        row,
        (
            "content_bbox",
            "content_bbox_json",
        ),
    )

    if bbox_json_value is not None:
        try:
            if isinstance(
                bbox_json_value,
                str,
            ):
                parsed_bbox = json.loads(
                    bbox_json_value
                )
            else:
                parsed_bbox = bbox_json_value

            if isinstance(
                parsed_bbox,
                dict,
            ):
                left = int(
                    parsed_bbox.get(
                        "left",
                        parsed_bbox.get(
                            "x_min",
                            parsed_bbox.get(
                                "x0",
                                0,
                            ),
                        ),
                    )
                )

                top = int(
                    parsed_bbox.get(
                        "top",
                        parsed_bbox.get(
                            "y_min",
                            parsed_bbox.get(
                                "y0",
                                0,
                            ),
                        ),
                    )
                )

                right = int(
                    parsed_bbox.get(
                        "right",
                        parsed_bbox.get(
                            "x_max",
                            parsed_bbox.get(
                                "x1",
                                width,
                            ),
                        ),
                    )
                )

                bottom = int(
                    parsed_bbox.get(
                        "bottom",
                        parsed_bbox.get(
                            "y_max",
                            parsed_bbox.get(
                                "y1",
                                height,
                            ),
                        ),
                    )
                )

                left = max(
                    0,
                    min(left, width),
                )

                top = max(
                    0,
                    min(top, height),
                )

                right = max(
                    left,
                    min(right, width),
                )

                bottom = max(
                    top,
                    min(bottom, height),
                )

                if (
                    right > left
                    and bottom > top
                ):
                    return (
                        left,
                        top,
                        right,
                        bottom,
                    )

            if (
                isinstance(
                    parsed_bbox,
                    (list, tuple),
                )
                and len(parsed_bbox) == 4
            ):
                left, top, right, bottom = (
                    int(round(float(value)))
                    for value in parsed_bbox
                )

                left = max(
                    0,
                    min(left, width),
                )

                top = max(
                    0,
                    min(top, height),
                )

                right = max(
                    left,
                    min(right, width),
                )

                bottom = max(
                    top,
                    min(bottom, height),
                )

                if (
                    right > left
                    and bottom > top
                ):
                    return (
                        left,
                        top,
                        right,
                        bottom,
                    )

        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            pass

    return (
        0,
        0,
        width,
        height,
    )


def _extract_content_area_pixels(
    row: pd.Series,
    content_bbox: tuple[int, int, int, int],
) -> int:
    area_value = _find_first_present_value(
        row,
        (
            "content_area_pixels",
            "content_pixels",
            "content_pixel_count",
            "non_padding_pixels",
        ),
    )

    if area_value is not None:
        area_pixels = int(
            round(float(area_value))
        )

        if area_pixels > 0:
            return area_pixels

    left, top, right, bottom = (
        content_bbox
    )

    return int(
        (right - left)
        * (bottom - top)
    )


def _resize_binary_crop(
    crop: np.ndarray,
    scale: float,
) -> np.ndarray:
    if scale <= 0:
        raise ValueError(
            "Mask scale must be positive."
        )

    source_height, source_width = (
        crop.shape
    )

    target_width = max(
        1,
        int(
            round(
                source_width
                * scale
            )
        ),
    )

    target_height = max(
        1,
        int(
            round(
                source_height
                * scale
            )
        ),
    )

    image = Image.fromarray(
        (
            crop.astype(np.uint8)
            * 255
        ),
        mode="L",
    )

    resized = image.resize(
        (
            target_width,
            target_height,
        ),
        resample=Image.Resampling.NEAREST,
    )

    return (
        np.asarray(resized) > 0
    ).astype(np.uint8)


def _paste_mask_crop(
    crop: np.ndarray,
    canvas_shape: tuple[int, int],
    centroid_x: float,
    centroid_y: float,
    content_bbox: tuple[int, int, int, int],
) -> np.ndarray:
    canvas_height, canvas_width = (
        canvas_shape
    )

    crop_height, crop_width = crop.shape

    left_bound, top_bound, right_bound, bottom_bound = (
        content_bbox
    )

    proposed_left = int(
        round(
            centroid_x
            - crop_width / 2
        )
    )

    proposed_top = int(
        round(
            centroid_y
            - crop_height / 2
        )
    )

    maximum_left = max(
        left_bound,
        right_bound - crop_width,
    )

    maximum_top = max(
        top_bound,
        bottom_bound - crop_height,
    )

    paste_left = min(
        max(
            proposed_left,
            left_bound,
        ),
        maximum_left,
    )

    paste_top = min(
        max(
            proposed_top,
            top_bound,
        ),
        maximum_top,
    )

    paste_right = (
        paste_left
        + crop_width
    )

    paste_bottom = (
        paste_top
        + crop_height
    )

    canvas = np.zeros(
        (
            canvas_height,
            canvas_width,
        ),
        dtype=np.uint8,
    )

    source_left = 0
    source_top = 0
    source_right = crop_width
    source_bottom = crop_height

    if paste_left < left_bound:
        source_left += (
            left_bound
            - paste_left
        )

        paste_left = left_bound

    if paste_top < top_bound:
        source_top += (
            top_bound
            - paste_top
        )

        paste_top = top_bound

    if paste_right > right_bound:
        source_right -= (
            paste_right
            - right_bound
        )

        paste_right = right_bound

    if paste_bottom > bottom_bound:
        source_bottom -= (
            paste_bottom
            - bottom_bound
        )

        paste_bottom = bottom_bound

    paste_left = max(
        0,
        min(
            paste_left,
            canvas_width,
        ),
    )

    paste_top = max(
        0,
        min(
            paste_top,
            canvas_height,
        ),
    )

    paste_right = max(
        paste_left,
        min(
            paste_right,
            canvas_width,
        ),
    )

    paste_bottom = max(
        paste_top,
        min(
            paste_bottom,
            canvas_height,
        ),
    )

    destination_height = (
        paste_bottom
        - paste_top
    )

    destination_width = (
        paste_right
        - paste_left
    )

    if (
        destination_height <= 0
        or destination_width <= 0
    ):
        return canvas

    source_bottom = (
        source_top
        + destination_height
    )

    source_right = (
        source_left
        + destination_width
    )

    canvas[
        paste_top:paste_bottom,
        paste_left:paste_right,
    ] = crop[
        source_top:source_bottom,
        source_left:source_right,
    ]

    return canvas


def _create_scaled_mask_candidate(
    base_crop: np.ndarray,
    scale: float,
    canvas_shape: tuple[int, int],
    centroid_x: float,
    centroid_y: float,
    content_bbox: tuple[int, int, int, int],
) -> np.ndarray:
    resized_crop = _resize_binary_crop(
        base_crop,
        scale,
    )

    return _paste_mask_crop(
        crop=resized_crop,
        canvas_shape=canvas_shape,
        centroid_x=centroid_x,
        centroid_y=centroid_y,
        content_bbox=content_bbox,
    )


def scale_mask_to_target_area(
    base_mask: np.ndarray,
    target_pixels: int,
    content_bbox: tuple[int, int, int, int],
    maximum_iterations: int = 24,
) -> dict[str, Any]:
    binary_mask = _normalise_binary_mask(
        base_mask
    )

    image_height, image_width = (
        binary_mask.shape
    )

    if target_pixels <= 0:
        raise ValueError(
            "target_pixels must be greater than zero."
        )

    left, top, right, bottom = (
        content_bbox
    )

    content_width = right - left
    content_height = bottom - top

    maximum_content_pixels = (
        content_width
        * content_height
    )

    if target_pixels > maximum_content_pixels:
        raise ValueError(
            "Requested target exceeds the available "
            "content bounding-box area."
        )

    base_bbox = _extract_mask_bbox(
        binary_mask
    )

    base_centroid = _extract_mask_centroid(
        binary_mask
    )

    if (
        base_bbox is None
        or base_centroid is None
    ):
        raise ValueError(
            "Base mask contains no damaged pixels."
        )

    base_left, base_top, base_right, base_bottom = (
        base_bbox
    )

    base_crop = binary_mask[
        base_top:base_bottom,
        base_left:base_right,
    ]

    base_pixels = int(
        binary_mask.sum()
    )

    if base_pixels <= 0:
        raise ValueError(
            "Base mask contains no damaged pixels."
        )

    initial_scale = math.sqrt(
        target_pixels
        / base_pixels
    )

    minimum_scale = max(
        0.001,
        initial_scale / 8.0,
    )

    maximum_scale = max(
        1.0,
        initial_scale * 8.0,
        content_width
        / max(
            1,
            base_crop.shape[1],
        ),
        content_height
        / max(
            1,
            base_crop.shape[0],
        ),
    )

    centroid_x, centroid_y = (
        base_centroid
    )

    centroid_x = min(
        max(
            centroid_x,
            left,
        ),
        max(
            left,
            right - 1,
        ),
    )

    centroid_y = min(
        max(
            centroid_y,
            top,
        ),
        max(
            top,
            bottom - 1,
        ),
    )

    candidate_scales: set[float] = {
        minimum_scale,
        maximum_scale,
        initial_scale,
    }

    low_scale = minimum_scale
    high_scale = maximum_scale

    best_mask: np.ndarray | None = None
    best_scale: float | None = None
    best_pixel_difference: int | None = None

    for _ in range(
        maximum_iterations
    ):
        middle_scale = (
            low_scale
            + high_scale
        ) / 2.0

        candidate_scales.add(
            middle_scale
        )

        candidate_mask = (
            _create_scaled_mask_candidate(
                base_crop=base_crop,
                scale=middle_scale,
                canvas_shape=(
                    image_height,
                    image_width,
                ),
                centroid_x=centroid_x,
                centroid_y=centroid_y,
                content_bbox=content_bbox,
            )
        )

        candidate_pixels = int(
            candidate_mask.sum()
        )

        pixel_difference = abs(
            candidate_pixels
            - target_pixels
        )

        if (
            best_pixel_difference is None
            or pixel_difference
            < best_pixel_difference
        ):
            best_mask = candidate_mask
            best_scale = middle_scale
            best_pixel_difference = (
                pixel_difference
            )

        if candidate_pixels < target_pixels:
            low_scale = middle_scale
        elif candidate_pixels > target_pixels:
            high_scale = middle_scale
        else:
            break

    local_search_scales = []

    if best_scale is not None:
        local_search_scales.extend(
            np.linspace(
                max(
                    minimum_scale,
                    best_scale * 0.95,
                ),
                min(
                    maximum_scale,
                    best_scale * 1.05,
                ),
                num=31,
            ).tolist()
        )

    candidate_scales.update(
        float(value)
        for value in local_search_scales
    )

    for scale in sorted(
        candidate_scales
    ):
        candidate_mask = (
            _create_scaled_mask_candidate(
                base_crop=base_crop,
                scale=scale,
                canvas_shape=(
                    image_height,
                    image_width,
                ),
                centroid_x=centroid_x,
                centroid_y=centroid_y,
                content_bbox=content_bbox,
            )
        )

        candidate_pixels = int(
            candidate_mask.sum()
        )

        pixel_difference = abs(
            candidate_pixels
            - target_pixels
        )

        if (
            best_pixel_difference is None
            or pixel_difference
            < best_pixel_difference
        ):
            best_mask = candidate_mask
            best_scale = scale
            best_pixel_difference = (
                pixel_difference
            )

    if (
        best_mask is None
        or best_scale is None
        or best_pixel_difference is None
    ):
        raise RuntimeError(
            "Failed to generate a scaled mask candidate."
        )

    realised_pixels = int(
        best_mask.sum()
    )

    return {
        "mask": best_mask,
        "scale_factor": float(
            best_scale
        ),
        "base_pixels": base_pixels,
        "target_pixels": int(
            target_pixels
        ),
        "realised_pixels": realised_pixels,
        "absolute_pixel_error": int(
            abs(
                realised_pixels
                - target_pixels
            )
        ),
    }


def create_damage_size_sensitivity_dataset(
    processed_metadata: pd.DataFrame,
    mask_metadata: pd.DataFrame,
    target_percentages: Iterable[float],
    output_mask_dir: str | Path,
    output_damaged_dir: str | Path,
    project_root: str | Path | None = None,
    base_mask_types: Iterable[str] = DEFAULT_BASE_MASK_TYPES,
    fill_color: Sequence[int] = DEFAULT_DAMAGE_FILL_COLOR,
    fill_strategy: str = DEFAULT_DAMAGE_FILL_STRATEGY,
    global_seed: int = 20260505,
    overwrite: bool = True,
    compute_checksums: bool = True,
) -> pd.DataFrame:
    required_processed_columns = {
        "painting_id",
    }

    required_mask_columns = {
        "painting_id",
        "mask_type",
        "mask_path",
    }

    missing_processed_columns = sorted(
        required_processed_columns
        - set(processed_metadata.columns)
    )

    missing_mask_columns = sorted(
        required_mask_columns
        - set(mask_metadata.columns)
    )

    if missing_processed_columns:
        raise ValueError(
            "Processed metadata is missing required columns: "
            f"{missing_processed_columns}"
        )

    if missing_mask_columns:
        raise ValueError(
            "Mask metadata is missing required columns: "
            f"{missing_mask_columns}"
        )

    target_percentage_values = (
        _normalise_percentages(
            target_percentages
        )
    )

    fill_color_value = (
        _normalise_fill_color(
            fill_color
        )
    )

    base_mask_type_values = tuple(
        str(value)
        for value in base_mask_types
    )

    if not base_mask_type_values:
        raise ValueError(
            "At least one base mask type is required."
        )

    project_root_path = (
        Path(project_root)
        if project_root is not None
        else None
    )

    mask_output_path = Path(
        output_mask_dir
    )

    damaged_output_path = Path(
        output_damaged_dir
    )

    mask_output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    damaged_output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    if (
        processed_metadata[
            "painting_id"
        ]
        .astype(str)
        .duplicated()
        .any()
    ):
        raise ValueError(
            "Processed metadata contains duplicate painting IDs."
        )

    processed_lookup = (
        processed_metadata
        .copy()
    )

    processed_lookup[
        "painting_id"
    ] = (
        processed_lookup[
            "painting_id"
        ]
        .astype(str)
    )

    processed_lookup = (
        processed_lookup
        .set_index(
            "painting_id",
            drop=False,
        )
    )

    mask_source_df = (
        mask_metadata[
            mask_metadata[
                "mask_type"
            ]
            .astype(str)
            .isin(
                base_mask_type_values
            )
        ]
        .copy()
    )

    mask_source_df[
        "painting_id"
    ] = (
        mask_source_df[
            "painting_id"
        ]
        .astype(str)
    )

    mask_source_df[
        "mask_type"
    ] = (
        mask_source_df[
            "mask_type"
        ]
        .astype(str)
    )

    duplicate_base_cases = (
        mask_source_df
        .duplicated(
            subset=[
                "painting_id",
                "mask_type",
            ],
            keep=False,
        )
    )

    if duplicate_base_cases.any():
        duplicate_rows = (
            mask_source_df.loc[
                duplicate_base_cases,
                [
                    "painting_id",
                    "mask_type",
                    "mask_path",
                ],
            ]
        )

        raise ValueError(
            "Base mask metadata contains duplicate "
            "painting and mask-type combinations:\n"
            f"{duplicate_rows.to_string(index=False)}"
        )

    records: list[dict[str, Any]] = []

    for _, mask_row in (
        mask_source_df
        .sort_values(
            [
                "painting_id",
                "mask_type",
            ],
            kind="stable",
        )
        .iterrows()
    ):
        painting_id = str(
            mask_row["painting_id"]
        )

        mask_type = str(
            mask_row["mask_type"]
        )

        if painting_id not in processed_lookup.index:
            records.append(
                {
                    "painting_id": painting_id,
                    "base_mask_type": mask_type,
                    "status": "error",
                    "issue": (
                        "painting_missing_from_processed_metadata"
                    ),
                }
            )

            continue

        processed_row = (
            processed_lookup.loc[
                painting_id
            ]
        )

        if isinstance(
            processed_row,
            pd.DataFrame,
        ):
            processed_row = (
                processed_row.iloc[0]
            )

        combined_row = (
            processed_row.copy()
        )

        for column, value in mask_row.items():
            if (
                column not in combined_row.index
                or pd.isna(
                    combined_row[column]
                )
            ):
                combined_row[column] = value

        mask_path = _resolve_existing_path(
            mask_row["mask_path"],
            project_root_path,
        )

        clean_path_value = (
            _find_first_present_value(
                processed_row,
                (
                    "processed_path",
                    "clean_path",
                    "image_path",
                    "processed_image_path",
                ),
            )
        )

        if clean_path_value is None:
            records.append(
                {
                    "painting_id": painting_id,
                    "base_mask_type": mask_type,
                    "status": "error",
                    "issue": (
                        "clean_path_missing_from_processed_metadata"
                    ),
                }
            )

            continue

        clean_path = _resolve_existing_path(
            clean_path_value,
            project_root_path,
        )

        if not clean_path.exists():
            records.append(
                {
                    "painting_id": painting_id,
                    "base_mask_type": mask_type,
                    "clean_path": (
                        _safe_relative_string(
                            clean_path,
                            project_root_path,
                        )
                    ),
                    "status": "error",
                    "issue": "clean_file_missing",
                }
            )

            continue

        if not mask_path.exists():
            records.append(
                {
                    "painting_id": painting_id,
                    "base_mask_type": mask_type,
                    "mask_path": (
                        _safe_relative_string(
                            mask_path,
                            project_root_path,
                        )
                    ),
                    "status": "error",
                    "issue": "base_mask_file_missing",
                }
            )

            continue

        try:
            with Image.open(
                clean_path
            ) as clean_image:
                clean_rgb = (
                    clean_image
                    .convert("RGB")
                )

                clean_array = np.asarray(
                    clean_rgb
                )

            with Image.open(
                mask_path
            ) as mask_image:
                base_mask_array = (
                    np.asarray(
                        mask_image.convert(
                            "L"
                        )
                    )
                )

            base_mask_array = (
                _normalise_binary_mask(
                    base_mask_array
                )
            )

            image_height, image_width = (
                clean_array.shape[:2]
            )

            if (
                base_mask_array.shape
                != (
                    image_height,
                    image_width,
                )
            ):
                raise ValueError(
                    "Clean image and base mask dimensions differ."
                )

            content_bbox = (
                _extract_content_bbox(
                    combined_row,
                    width=image_width,
                    height=image_height,
                )
            )

            content_area_pixels = (
                _extract_content_area_pixels(
                    combined_row,
                    content_bbox,
                )
            )

            if content_area_pixels <= 0:
                raise ValueError(
                    "Content area must be greater than zero."
                )

            deterministic_seed = (
                _stable_seed(
                    global_seed=global_seed,
                    painting_id=painting_id,
                    mask_type=mask_type,
                )
            )

            base_mask_pixels = int(
                base_mask_array.sum()
            )

            base_percentage_content = (
                100.0
                * base_mask_pixels
                / content_area_pixels
            )

            base_percentage_full = (
                100.0
                * base_mask_pixels
                / (
                    image_width
                    * image_height
                )
            )

            clean_sha256 = None
            base_mask_sha256 = None

            if compute_checksums:
                clean_sha256 = (
                    compute_file_sha256(
                        clean_path
                    )
                )

                base_mask_sha256 = (
                    compute_file_sha256(
                        mask_path
                    )
                )

            for target_percentage in (
                target_percentage_values
            ):
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

                percentage_token = (
                    _format_percentage_token(
                        target_percentage
                    )
                )

                case_id = (
                    f"{painting_id}"
                    f"__{mask_type}"
                    f"__size_{percentage_token}"
                )

                sensitivity_mask_id = (
                    f"{case_id}__mask"
                )

                sensitivity_mask_filename = (
                    f"{case_id}"
                    f"{MASK_FILENAME_SUFFIX}"
                )

                damaged_filename = (
                    f"{case_id}"
                    f"{DAMAGED_FILENAME_SUFFIX}"
                )

                sensitivity_mask_path = (
                    mask_output_path
                    / sensitivity_mask_filename
                )

                damaged_path = (
                    damaged_output_path
                    / damaged_filename
                )

                generated_at_utc = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )

                generation_action = (
                    "generated"
                )

                if (
                    not overwrite
                    and sensitivity_mask_path.exists()
                    and damaged_path.exists()
                ):
                    generation_action = (
                        "reused_existing"
                    )

                    with Image.open(
                        sensitivity_mask_path
                    ) as saved_mask_image:
                        generated_mask = (
                            np.asarray(
                                saved_mask_image
                                .convert("L")
                            )
                            > 0
                        ).astype(np.uint8)

                    realised_pixels = int(
                        generated_mask.sum()
                    )

                    scale_result = {
                        "mask": generated_mask,
                        "scale_factor": np.nan,
                        "base_pixels": (
                            base_mask_pixels
                        ),
                        "target_pixels": (
                            target_pixels
                        ),
                        "realised_pixels": (
                            realised_pixels
                        ),
                        "absolute_pixel_error": (
                            abs(
                                realised_pixels
                                - target_pixels
                            )
                        ),
                    }

                else:
                    scale_result = (
                        scale_mask_to_target_area(
                            base_mask=(
                                base_mask_array
                            ),
                            target_pixels=(
                                target_pixels
                            ),
                            content_bbox=(
                                content_bbox
                            ),
                        )
                    )

                    generated_mask = (
                        scale_result[
                            "mask"
                        ]
                    )

                    generated_mask_image = (
                        Image.fromarray(
                            (
                                generated_mask
                                * 255
                            ).astype(np.uint8),
                            mode="L",
                        )
                    )

                    generated_mask_image.save(
                        sensitivity_mask_path,
                        format="PNG",
                    )

                    damaged_image = (
                        apply_mask_damage(
                            clean_rgb,
                            generated_mask_image,
                            fill_color_value,
                        )
                    )

                    damaged_image.save(
                        damaged_path,
                        format="PNG",
                    )

                realised_pixels = int(
                    scale_result[
                        "realised_pixels"
                    ]
                )

                realised_percentage_content = (
                    100.0
                    * realised_pixels
                    / content_area_pixels
                )

                realised_percentage_full = (
                    100.0
                    * realised_pixels
                    / (
                        image_width
                        * image_height
                    )
                )

                percentage_error = (
                    realised_percentage_content
                    - target_percentage
                )

                sensitivity_mask_sha256 = None
                damaged_sha256 = None

                if compute_checksums:
                    sensitivity_mask_sha256 = (
                        compute_file_sha256(
                            sensitivity_mask_path
                        )
                    )

                    damaged_sha256 = (
                        compute_file_sha256(
                            damaged_path
                        )
                    )

                record = {
                    "case_id": case_id,
                    "painting_id": painting_id,
                    "base_mask_id": (
                        mask_row.get(
                            "mask_id",
                            pd.NA,
                        )
                    ),
                    "base_mask_type": mask_type,
                    "sensitivity_mask_id": (
                        sensitivity_mask_id
                    ),
                    "target_percentage_content": (
                        float(
                            target_percentage
                        )
                    ),
                    "target_pixels": int(
                        target_pixels
                    ),
                    "realised_pixels": (
                        realised_pixels
                    ),
                    "realised_percentage_content": (
                        float(
                            realised_percentage_content
                        )
                    ),
                    "realised_percentage_full": (
                        float(
                            realised_percentage_full
                        )
                    ),
                    "percentage_error_content": (
                        float(
                            percentage_error
                        )
                    ),
                    "absolute_percentage_error_content": (
                        float(
                            abs(
                                percentage_error
                            )
                        )
                    ),
                    "absolute_pixel_error": int(
                        scale_result[
                            "absolute_pixel_error"
                        ]
                    ),
                    "scale_factor": (
                        float(
                            scale_result[
                                "scale_factor"
                            ]
                        )
                        if pd.notna(
                            scale_result[
                                "scale_factor"
                            ]
                        )
                        else np.nan
                    ),
                    "base_mask_pixels": (
                        base_mask_pixels
                    ),
                    "base_percentage_content": (
                        float(
                            base_percentage_content
                        )
                    ),
                    "base_percentage_full": (
                        float(
                            base_percentage_full
                        )
                    ),
                    "content_area_pixels": (
                        int(
                            content_area_pixels
                        )
                    ),
                    "content_bbox_left": int(
                        content_bbox[0]
                    ),
                    "content_bbox_top": int(
                        content_bbox[1]
                    ),
                    "content_bbox_right": int(
                        content_bbox[2]
                    ),
                    "content_bbox_bottom": int(
                        content_bbox[3]
                    ),
                    "width": int(
                        image_width
                    ),
                    "height": int(
                        image_height
                    ),
                    "deterministic_seed": int(
                        deterministic_seed
                    ),
                    "global_seed": int(
                        global_seed
                    ),
                    "generator_name": (
                        GENERATOR_NAME
                    ),
                    "generator_version": (
                        GENERATOR_VERSION
                    ),
                    "generated_at_utc": (
                        generated_at_utc
                    ),
                    "generation_action": (
                        generation_action
                    ),
                    "damage_fill_strategy": (
                        fill_strategy
                    ),
                    "damage_fill_r": (
                        fill_color_value[0]
                    ),
                    "damage_fill_g": (
                        fill_color_value[1]
                    ),
                    "damage_fill_b": (
                        fill_color_value[2]
                    ),
                    "clean_path": (
                        _safe_relative_string(
                            clean_path,
                            project_root_path,
                        )
                    ),
                    "base_mask_path": (
                        _safe_relative_string(
                            mask_path,
                            project_root_path,
                        )
                    ),
                    "sensitivity_mask_filename": (
                        sensitivity_mask_filename
                    ),
                    "sensitivity_mask_path": (
                        _safe_relative_string(
                            sensitivity_mask_path,
                            project_root_path,
                        )
                    ),
                    "damaged_filename": (
                        damaged_filename
                    ),
                    "damaged_path": (
                        _safe_relative_string(
                            damaged_path,
                            project_root_path,
                        )
                    ),
                    "clean_sha256": (
                        clean_sha256
                    ),
                    "base_mask_sha256": (
                        base_mask_sha256
                    ),
                    "sensitivity_mask_sha256": (
                        sensitivity_mask_sha256
                    ),
                    "damaged_sha256": (
                        damaged_sha256
                    ),
                    "sensitivity_mask_file_size_bytes": (
                        sensitivity_mask_path
                        .stat()
                        .st_size
                    ),
                    "damaged_file_size_bytes": (
                        damaged_path
                        .stat()
                        .st_size
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
                    if (
                        metadata_column
                        in processed_row.index
                    ):
                        record[
                            metadata_column
                        ] = processed_row[
                            metadata_column
                        ]

                records.append(
                    record
                )

        except Exception as exc:
            records.append(
                {
                    "painting_id": painting_id,
                    "base_mask_type": mask_type,
                    "clean_path": (
                        _safe_relative_string(
                            clean_path,
                            project_root_path,
                        )
                    ),
                    "base_mask_path": (
                        _safe_relative_string(
                            mask_path,
                            project_root_path,
                        )
                    ),
                    "status": "error",
                    "issue": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                }
            )

    result_df = pd.DataFrame(
        records
    )

    if result_df.empty:
        return result_df

    sort_columns = [
        column
        for column in (
            "painting_id",
            "base_mask_type",
            "target_percentage_content",
            "case_id",
        )
        if column in result_df.columns
    ]

    if sort_columns:
        result_df = (
            result_df
            .sort_values(
                sort_columns,
                kind="stable",
                na_position="last",
            )
            .reset_index(drop=True)
        )

    return result_df


def validate_damage_size_sensitivity_dataset(
    sensitivity_metadata: pd.DataFrame,
    project_root: str | Path | None = None,
    verify_checksums: bool = True,
    maximum_percentage_error: float = 0.50,
) -> pd.DataFrame:
    required_columns = {
        "case_id",
        "painting_id",
        "base_mask_type",
        "target_percentage_content",
        "target_pixels",
        "realised_pixels",
        "realised_percentage_content",
        "content_area_pixels",
        "width",
        "height",
        "clean_path",
        "sensitivity_mask_path",
        "damaged_path",
        "damage_fill_r",
        "damage_fill_g",
        "damage_fill_b",
    }

    missing_columns = sorted(
        required_columns
        - set(
            sensitivity_metadata.columns
        )
    )

    if missing_columns:
        raise ValueError(
            "Sensitivity metadata is missing required columns: "
            f"{missing_columns}"
        )

    project_root_path = (
        Path(project_root)
        if project_root is not None
        else None
    )

    records: list[dict[str, Any]] = []

    for _, row in (
        sensitivity_metadata.iterrows()
    ):
        case_id = str(
            row["case_id"]
        )

        clean_path = _resolve_existing_path(
            row["clean_path"],
            project_root_path,
        )

        mask_path = _resolve_existing_path(
            row[
                "sensitivity_mask_path"
            ],
            project_root_path,
        )

        damaged_path = _resolve_existing_path(
            row["damaged_path"],
            project_root_path,
        )

        issues: list[str] = []

        clean_exists = (
            clean_path.exists()
        )

        mask_exists = (
            mask_path.exists()
        )

        damaged_exists = (
            damaged_path.exists()
        )

        if not clean_exists:
            issues.append(
                "clean_file_missing"
            )

        if not mask_exists:
            issues.append(
                "sensitivity_mask_missing"
            )

        if not damaged_exists:
            issues.append(
                "damaged_file_missing"
            )

        readable = False
        dimensions_valid = False
        mask_mode_valid = False
        damaged_mode_valid = False
        mask_format_valid = False
        damaged_format_valid = False
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
            if (
                clean_exists
                and mask_exists
                and damaged_exists
            ):
                with Image.open(
                    clean_path
                ) as clean_image:
                    clean_rgb = (
                        clean_image
                        .convert("RGB")
                    )

                    clean_array = np.asarray(
                        clean_rgb
                    )

                with Image.open(
                    mask_path
                ) as mask_image:
                    mask_format = (
                        mask_image.format
                    )

                    mask_mode = (
                        mask_image.mode
                    )

                    mask_array = np.asarray(
                        mask_image.convert(
                            "L"
                        )
                    )

                with Image.open(
                    damaged_path
                ) as damaged_image:
                    damaged_format = (
                        damaged_image.format
                    )

                    damaged_mode = (
                        damaged_image.mode
                    )

                    damaged_array = (
                        np.asarray(
                            damaged_image
                            .convert("RGB")
                        )
                    )

                readable = True

                expected_shape = (
                    int(row["height"]),
                    int(row["width"]),
                )

                dimensions_valid = (
                    clean_array.shape[:2]
                    == expected_shape
                    and mask_array.shape
                    == expected_shape
                    and damaged_array.shape[:2]
                    == expected_shape
                )

                mask_mode_valid = (
                    mask_mode == "L"
                )

                damaged_mode_valid = (
                    damaged_mode == "RGB"
                )

                mask_format_valid = (
                    mask_format == "PNG"
                )

                damaged_format_valid = (
                    damaged_format == "PNG"
                )

                binary_mask = (
                    mask_array > 0
                )

                observed_mask_pixels = int(
                    binary_mask.sum()
                )

                realised_pixels_match = (
                    observed_mask_pixels
                    == int(
                        row[
                            "realised_pixels"
                        ]
                    )
                )

                content_area_pixels = int(
                    row[
                        "content_area_pixels"
                    ]
                )

                observed_percentage_content = (
                    100.0
                    * observed_mask_pixels
                    / content_area_pixels
                )

                realised_percentage_match = (
                    abs(
                        observed_percentage_content
                        - float(
                            row[
                                "realised_percentage_content"
                            ]
                        )
                    )
                    <= 1e-9
                )

                target_error_valid = (
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
                    clean_array
                    != damaged_array,
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
                        int(
                            row[
                                "damage_fill_r"
                            ]
                        ),
                        int(
                            row[
                                "damage_fill_g"
                            ]
                        ),
                        int(
                            row[
                                "damage_fill_b"
                            ]
                        ),
                    ],
                    dtype=np.uint8,
                )

                inside_mask_not_fill_pixels = int(
                    (
                        binary_mask
                        & np.any(
                            damaged_array
                            != fill_color,
                            axis=2,
                        )
                    ).sum()
                )

                outside_mask_preserved = (
                    outside_mask_changed_pixels
                    == 0
                )

                masked_fill_valid = (
                    inside_mask_not_fill_pixels
                    == 0
                )

                if verify_checksums:
                    checksum_pairs = (
                        (
                            clean_path,
                            row.get(
                                "clean_sha256",
                                None,
                            ),
                            "clean_sha256_mismatch",
                        ),
                        (
                            mask_path,
                            row.get(
                                "sensitivity_mask_sha256",
                                None,
                            ),
                            "sensitivity_mask_sha256_mismatch",
                        ),
                        (
                            damaged_path,
                            row.get(
                                "damaged_sha256",
                                None,
                            ),
                            "damaged_sha256_mismatch",
                        ),
                    )

                    for (
                        checksum_path,
                        expected_checksum,
                        issue_name,
                    ) in checksum_pairs:
                        if (
                            expected_checksum is None
                            or pd.isna(
                                expected_checksum
                            )
                            or str(
                                expected_checksum
                            ).strip()
                            == ""
                        ):
                            checksum_valid = False
                            issues.append(
                                f"{issue_name}_missing"
                            )

                            continue

                        observed_checksum = (
                            compute_file_sha256(
                                checksum_path
                            )
                        )

                        if (
                            observed_checksum
                            != str(
                                expected_checksum
                            )
                        ):
                            checksum_valid = False
                            issues.append(
                                issue_name
                            )

        except Exception as exc:
            issues.append(
                f"{type(exc).__name__}: {exc}"
            )

        if readable:
            if not dimensions_valid:
                issues.append(
                    "dimension_mismatch"
                )

            if not mask_mode_valid:
                issues.append(
                    "mask_mode_not_l"
                )

            if not damaged_mode_valid:
                issues.append(
                    "damaged_mode_not_rgb"
                )

            if not mask_format_valid:
                issues.append(
                    "mask_format_not_png"
                )

            if not damaged_format_valid:
                issues.append(
                    "damaged_format_not_png"
                )

            if not realised_pixels_match:
                issues.append(
                    "realised_pixel_count_mismatch"
                )

            if not realised_percentage_match:
                issues.append(
                    "realised_percentage_mismatch"
                )

            if not target_error_valid:
                issues.append(
                    "target_percentage_error_exceeded"
                )

            if not outside_mask_preserved:
                issues.append(
                    "outside_mask_changed"
                )

            if not masked_fill_valid:
                issues.append(
                    "inside_mask_fill_failure"
                )

        validation_passed = (
            clean_exists
            and mask_exists
            and damaged_exists
            and readable
            and dimensions_valid
            and mask_mode_valid
            and damaged_mode_valid
            and mask_format_valid
            and damaged_format_valid
            and realised_pixels_match
            and realised_percentage_match
            and target_error_valid
            and outside_mask_preserved
            and masked_fill_valid
            and checksum_valid
        )

        records.append(
            {
                "case_id": case_id,
                "painting_id": (
                    row["painting_id"]
                ),
                "base_mask_type": (
                    row[
                        "base_mask_type"
                    ]
                ),
                "target_percentage_content": (
                    float(
                        row[
                            "target_percentage_content"
                        ]
                    )
                ),
                "clean_exists": clean_exists,
                "mask_exists": mask_exists,
                "damaged_exists": damaged_exists,
                "readable": readable,
                "dimensions_valid": (
                    dimensions_valid
                ),
                "mask_mode_valid": (
                    mask_mode_valid
                ),
                "damaged_mode_valid": (
                    damaged_mode_valid
                ),
                "mask_format_valid": (
                    mask_format_valid
                ),
                "damaged_format_valid": (
                    damaged_format_valid
                ),
                "metadata_realised_pixels": (
                    int(
                        row[
                            "realised_pixels"
                        ]
                    )
                ),
                "observed_mask_pixels": (
                    observed_mask_pixels
                ),
                "realised_pixels_match": (
                    realised_pixels_match
                ),
                "metadata_realised_percentage_content": (
                    float(
                        row[
                            "realised_percentage_content"
                        ]
                    )
                ),
                "observed_percentage_content": (
                    observed_percentage_content
                ),
                "realised_percentage_match": (
                    realised_percentage_match
                ),
                "maximum_percentage_error": (
                    float(
                        maximum_percentage_error
                    )
                ),
                "target_error_valid": (
                    target_error_valid
                ),
                "outside_mask_changed_pixels": (
                    outside_mask_changed_pixels
                ),
                "inside_mask_not_fill_pixels": (
                    inside_mask_not_fill_pixels
                ),
                "outside_mask_preserved": (
                    outside_mask_preserved
                ),
                "masked_fill_valid": (
                    masked_fill_valid
                ),
                "checksum_valid": (
                    checksum_valid
                ),
                "validation_passed": (
                    validation_passed
                ),
                "issue": ";".join(
                    sorted(
                        set(issues)
                    )
                ),
            }
        )

    return pd.DataFrame(
        records
    )


def audit_damage_size_sensitivity_inventory(
    sensitivity_metadata: pd.DataFrame,
    mask_dir: str | Path,
    damaged_dir: str | Path,
    expected_case_ids: Iterable[str] | None = None,
    project_root: str | Path | None = None,
) -> dict[str, pd.DataFrame]:
    project_root_path = (
        Path(project_root)
        if project_root is not None
        else None
    )

    mask_directory = Path(
        mask_dir
    )

    damaged_directory = Path(
        damaged_dir
    )

    metadata_df = (
        sensitivity_metadata.copy()
    )

    metadata_df[
        "case_id"
    ] = (
        metadata_df[
            "case_id"
        ]
        .astype(str)
    )

    duplicate_case_rows = (
        metadata_df[
            metadata_df[
                "case_id"
            ]
            .duplicated(
                keep=False
            )
        ]
        .sort_values(
            "case_id",
            kind="stable",
        )
    )

    duplicate_mask_filename_rows = pd.DataFrame()
    duplicate_damaged_filename_rows = pd.DataFrame()
    duplicate_mask_path_rows = pd.DataFrame()
    duplicate_damaged_path_rows = pd.DataFrame()

    if (
        "sensitivity_mask_filename"
        in metadata_df.columns
    ):
        duplicate_mask_filename_rows = (
            metadata_df[
                metadata_df[
                    "sensitivity_mask_filename"
                ]
                .astype(str)
                .duplicated(
                    keep=False
                )
            ]
        )

    if (
        "damaged_filename"
        in metadata_df.columns
    ):
        duplicate_damaged_filename_rows = (
            metadata_df[
                metadata_df[
                    "damaged_filename"
                ]
                .astype(str)
                .duplicated(
                    keep=False
                )
            ]
        )

    if (
        "sensitivity_mask_path"
        in metadata_df.columns
    ):
        duplicate_mask_path_rows = (
            metadata_df[
                metadata_df[
                    "sensitivity_mask_path"
                ]
                .astype(str)
                .duplicated(
                    keep=False
                )
            ]
        )

    if (
        "damaged_path"
        in metadata_df.columns
    ):
        duplicate_damaged_path_rows = (
            metadata_df[
                metadata_df[
                    "damaged_path"
                ]
                .astype(str)
                .duplicated(
                    keep=False
                )
            ]
        )

    metadata_case_ids = set(
        metadata_df[
            "case_id"
        ]
    )

    expected_case_id_set = (
        set(
            str(value)
            for value in expected_case_ids
        )
        if expected_case_ids is not None
        else metadata_case_ids
    )

    missing_case_ids = sorted(
        expected_case_id_set
        - metadata_case_ids
    )

    unexpected_case_ids = sorted(
        metadata_case_ids
        - expected_case_id_set
    )

    missing_case_rows = pd.DataFrame(
        {
            "case_id": (
                missing_case_ids
            )
        }
    )

    unexpected_case_rows = pd.DataFrame(
        {
            "case_id": (
                unexpected_case_ids
            )
        }
    )

    missing_mask_file_records = []
    missing_damaged_file_records = []
    filename_mismatch_records = []

    expected_mask_filenames = set()
    expected_damaged_filenames = set()

    for _, row in (
        metadata_df.iterrows()
    ):
        case_id = str(
            row["case_id"]
        )

        mask_path = _resolve_existing_path(
            row[
                "sensitivity_mask_path"
            ],
            project_root_path,
        )

        damaged_path = _resolve_existing_path(
            row["damaged_path"],
            project_root_path,
        )

        expected_mask_filename = (
            str(
                row[
                    "sensitivity_mask_filename"
                ]
            )
        )

        expected_damaged_filename = (
            str(
                row[
                    "damaged_filename"
                ]
            )
        )

        expected_mask_filenames.add(
            expected_mask_filename
        )

        expected_damaged_filenames.add(
            expected_damaged_filename
        )

        if not mask_path.exists():
            missing_mask_file_records.append(
                {
                    "case_id": case_id,
                    "sensitivity_mask_path": (
                        _safe_relative_string(
                            mask_path,
                            project_root_path,
                        )
                    ),
                }
            )

        if not damaged_path.exists():
            missing_damaged_file_records.append(
                {
                    "case_id": case_id,
                    "damaged_path": (
                        _safe_relative_string(
                            damaged_path,
                            project_root_path,
                        )
                    ),
                }
            )

        if (
            mask_path.name
            != expected_mask_filename
        ):
            filename_mismatch_records.append(
                {
                    "case_id": case_id,
                    "file_type": (
                        "sensitivity_mask"
                    ),
                    "metadata_filename": (
                        expected_mask_filename
                    ),
                    "path_filename": (
                        mask_path.name
                    ),
                }
            )

        if (
            damaged_path.name
            != expected_damaged_filename
        ):
            filename_mismatch_records.append(
                {
                    "case_id": case_id,
                    "file_type": (
                        "damaged_image"
                    ),
                    "metadata_filename": (
                        expected_damaged_filename
                    ),
                    "path_filename": (
                        damaged_path.name
                    ),
                }
            )

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
            "sensitivity_mask_filename": sorted(
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
        missing_mask_file_records
    )

    missing_damaged_file_rows = pd.DataFrame(
        missing_damaged_file_records
    )

    filename_mismatch_rows = pd.DataFrame(
        filename_mismatch_records
    )

    summary_records = [
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
            "check": (
                "duplicate_mask_filenames"
            ),
            "issue_count": int(
                duplicate_mask_filename_rows[
                    "sensitivity_mask_filename"
                ].nunique()
                if not duplicate_mask_filename_rows.empty
                else 0
            ),
        },
        {
            "check": (
                "duplicate_damaged_filenames"
            ),
            "issue_count": int(
                duplicate_damaged_filename_rows[
                    "damaged_filename"
                ].nunique()
                if not duplicate_damaged_filename_rows.empty
                else 0
            ),
        },
        {
            "check": (
                "duplicate_mask_paths"
            ),
            "issue_count": int(
                duplicate_mask_path_rows[
                    "sensitivity_mask_path"
                ].nunique()
                if not duplicate_mask_path_rows.empty
                else 0
            ),
        },
        {
            "check": (
                "duplicate_damaged_paths"
            ),
            "issue_count": int(
                duplicate_damaged_path_rows[
                    "damaged_path"
                ].nunique()
                if not duplicate_damaged_path_rows.empty
                else 0
            ),
        },
        {
            "check": (
                "missing_expected_cases"
            ),
            "issue_count": int(
                len(
                    missing_case_rows
                )
            ),
        },
        {
            "check": (
                "unexpected_metadata_cases"
            ),
            "issue_count": int(
                len(
                    unexpected_case_rows
                )
            ),
        },
        {
            "check": (
                "missing_mask_files"
            ),
            "issue_count": int(
                len(
                    missing_mask_file_rows
                )
            ),
        },
        {
            "check": (
                "missing_damaged_files"
            ),
            "issue_count": int(
                len(
                    missing_damaged_file_rows
                )
            ),
        },
        {
            "check": (
                "orphan_mask_files"
            ),
            "issue_count": int(
                len(
                    orphan_mask_rows
                )
            ),
        },
        {
            "check": (
                "orphan_damaged_files"
            ),
            "issue_count": int(
                len(
                    orphan_damaged_rows
                )
            ),
        },
        {
            "check": (
                "filename_path_mismatches"
            ),
            "issue_count": int(
                len(
                    filename_mismatch_rows
                )
            ),
        },
    ]

    summary_df = pd.DataFrame(
        summary_records
    )

    summary_df[
        "passed"
    ] = (
        summary_df[
            "issue_count"
        ]
        == 0
    )

    return {
        "summary": summary_df,
        "duplicate_case_rows": (
            duplicate_case_rows
        ),
        "duplicate_mask_filename_rows": (
            duplicate_mask_filename_rows
        ),
        "duplicate_damaged_filename_rows": (
            duplicate_damaged_filename_rows
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
        "filename_mismatch_rows": (
            filename_mismatch_rows
        ),
    }