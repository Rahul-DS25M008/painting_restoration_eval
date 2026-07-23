"""Deterministic synthetic-degradation dataset generation utilities."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

from restoration_eval.damage import compute_file_sha256


GENERATOR_NAME = "synthetic_degradation"
GENERATOR_VERSION = "1.0.0"

DEFAULT_DEGRADATION_TYPES = (
    "blur",
    "water_stain",
    "fading",
    "discolouration",
    "dirt_dust",
    "partial_transparency",
)

DEFAULT_SEVERITY_LEVELS = (
    "mild",
    "moderate",
    "severe",
)

DEFAULT_COMBINED_DEGRADATIONS = {
    "fading_discolouration": (
        "fading",
        "discolouration",
    ),
    "water_stain_dirt": (
        "water_stain",
        "dirt_dust",
    ),
    "blur_fading": (
        "blur",
        "fading",
    ),
}

SEVERITY_RANK = {
    "mild": 1,
    "moderate": 2,
    "severe": 3,
}

EFFECT_MASK_FILENAME_SUFFIX = "_effect_mask.png"
DEGRADED_FILENAME_SUFFIX = "_degraded.png"


def _stable_seed(
    *parts: object,
    modulus: int = 2**32 - 1,
) -> int:
    payload = "||".join(
        str(part)
        for part in parts
    ).encode("utf-8")

    digest = hashlib.sha256(
        payload
    ).digest()

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
        candidate = (
            Path(project_root)
            / path
        )

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

    project_root_path = (
        Path(project_root).resolve()
    )

    try:
        return (
            resolved_path.resolve()
            .relative_to(
                project_root_path
            )
            .as_posix()
        )
    except ValueError:
        return resolved_path.as_posix()


def _extract_clean_path_value(
    row: pd.Series,
) -> str | Path:
    candidates = (
        "processed_path",
        "clean_path",
        "image_path",
        "processed_image_path",
    )

    for column in candidates:
        if (
            column in row.index
            and pd.notna(row[column])
        ):
            return row[column]

    raise ValueError(
        "Processed metadata does not contain "
        "a usable clean-image path."
    )


def _content_box_from_row(
    row: pd.Series,
    target_size: int,
) -> tuple[int, int, int, int]:
    column_groups = (
        (
            "content_x_min",
            "content_y_min",
            "content_x_max",
            "content_y_max",
        ),
        (
            "content_bbox_left",
            "content_bbox_top",
            "content_bbox_right",
            "content_bbox_bottom",
        ),
    )

    for columns in column_groups:
        if not all(
            column in row.index
            and pd.notna(row[column])
            for column in columns
        ):
            continue

        values = tuple(
            int(round(float(row[column])))
            for column in columns
        )

        left, top, right, bottom = values

        if (
            0 <= left < right <= target_size
            and 0 <= top < bottom <= target_size
        ):
            return values

    raise ValueError(
        "Processed metadata does not contain "
        "a valid content bounding box."
    )


def _normalise_degradation_types(
    degradation_types: Iterable[str],
) -> tuple[str, ...]:
    values = tuple(
        str(value)
        for value in degradation_types
    )

    if not values:
        raise ValueError(
            "At least one degradation type is required."
        )

    if len(values) != len(set(values)):
        raise ValueError(
            "Degradation types must be unique."
        )

    unsupported = sorted(
        set(values)
        - set(DEFAULT_DEGRADATION_TYPES)
    )

    if unsupported:
        raise ValueError(
            f"Unsupported degradation types: {unsupported}"
        )

    return values


def _normalise_severity_levels(
    severity_levels: Iterable[str],
) -> tuple[str, ...]:
    values = tuple(
        str(value)
        for value in severity_levels
    )

    if not values:
        raise ValueError(
            "At least one severity level is required."
        )

    if len(values) != len(set(values)):
        raise ValueError(
            "Severity levels must be unique."
        )

    unsupported = sorted(
        set(values)
        - set(SEVERITY_RANK)
    )

    if unsupported:
        raise ValueError(
            f"Unsupported severity levels: {unsupported}"
        )

    return tuple(
        sorted(
            values,
            key=lambda value: SEVERITY_RANK[value],
        )
    )


def _normalise_combined_degradations(
    combined_degradations: (
        Mapping[str, Sequence[str]]
        | Iterable[str]
        | None
    ),
) -> dict[str, tuple[str, ...]]:
    if combined_degradations is None:
        return {}

    if isinstance(
        combined_degradations,
        Mapping,
    ):
        source = combined_degradations
    else:
        source = {
            str(name): (
                DEFAULT_COMBINED_DEGRADATIONS[
                    str(name)
                ]
            )
            for name in combined_degradations
        }

    result: dict[str, tuple[str, ...]] = {}

    for name, components in source.items():
        component_values = tuple(
            str(value)
            for value in components
        )

        if len(component_values) < 2:
            raise ValueError(
                "Combined degradation must contain "
                "at least two component operators."
            )

        unsupported = sorted(
            set(component_values)
            - set(DEFAULT_DEGRADATION_TYPES)
        )

        if unsupported:
            raise ValueError(
                f"Unsupported combined components "
                f"for {name}: {unsupported}"
            )

        result[str(name)] = component_values

    return result


def _severity_parameters(
    degradation_type: str,
    severity: str,
) -> dict[str, Any]:
    rank = SEVERITY_RANK[severity]

    parameters: dict[str, dict[int, dict[str, Any]]] = {
        "blur": {
            1: {
                "blur_radius": 1.5,
                "effect_opacity": 0.55,
            },
            2: {
                "blur_radius": 3.0,
                "effect_opacity": 0.75,
            },
            3: {
                "blur_radius": 5.0,
                "effect_opacity": 0.95,
            },
        },
        "water_stain": {
            1: {
                "stain_opacity": 0.18,
                "ring_strength": 0.18,
                "stain_colour_rgb": (
                    142,
                    104,
                    58,
                ),
            },
            2: {
                "stain_opacity": 0.28,
                "ring_strength": 0.28,
                "stain_colour_rgb": (
                    132,
                    91,
                    45,
                ),
            },
            3: {
                "stain_opacity": 0.40,
                "ring_strength": 0.38,
                "stain_colour_rgb": (
                    116,
                    72,
                    34,
                ),
            },
        },
        "fading": {
            1: {
                "saturation_factor": 0.82,
                "contrast_factor": 0.94,
                "brightness_factor": 1.03,
            },
            2: {
                "saturation_factor": 0.62,
                "contrast_factor": 0.86,
                "brightness_factor": 1.07,
            },
            3: {
                "saturation_factor": 0.42,
                "contrast_factor": 0.76,
                "brightness_factor": 1.12,
            },
        },
        "discolouration": {
            1: {
                "channel_scale_r": 1.04,
                "channel_scale_g": 0.99,
                "channel_scale_b": 0.94,
            },
            2: {
                "channel_scale_r": 1.09,
                "channel_scale_g": 0.97,
                "channel_scale_b": 0.86,
            },
            3: {
                "channel_scale_r": 1.15,
                "channel_scale_g": 0.94,
                "channel_scale_b": 0.76,
            },
        },
        "dirt_dust": {
            1: {
                "particle_density": 0.00020,
                "particle_radius_min": 1,
                "particle_radius_max": 3,
                "particle_opacity": 0.24,
                "grime_strength": 0.05,
            },
            2: {
                "particle_density": 0.00045,
                "particle_radius_min": 1,
                "particle_radius_max": 5,
                "particle_opacity": 0.36,
                "grime_strength": 0.10,
            },
            3: {
                "particle_density": 0.00080,
                "particle_radius_min": 1,
                "particle_radius_max": 7,
                "particle_opacity": 0.50,
                "grime_strength": 0.16,
            },
        },
        "partial_transparency": {
            1: {
                "transparency_alpha": 0.12,
                "substrate_colour_rgb": (
                    196,
                    178,
                    145,
                ),
            },
            2: {
                "transparency_alpha": 0.24,
                "substrate_colour_rgb": (
                    196,
                    178,
                    145,
                ),
            },
            3: {
                "transparency_alpha": 0.40,
                "substrate_colour_rgb": (
                    196,
                    178,
                    145,
                ),
            },
        },
    }

    return dict(
        parameters[
            degradation_type
        ][rank]
    )


def _content_gate(
    size: tuple[int, int],
    content_box: tuple[int, int, int, int],
) -> np.ndarray:
    width, height = size

    gate = np.zeros(
        (height, width),
        dtype=np.float32,
    )

    left, top, right, bottom = content_box
    gate[
        top:bottom,
        left:right,
    ] = 1.0

    return gate


def _generate_effect_mask(
    size: tuple[int, int],
    content_box: tuple[int, int, int, int],
    degradation_type: str,
    severity: str,
    rng: np.random.Generator,
) -> Image.Image:
    width, height = size
    left, top, right, bottom = content_box

    content_width = right - left
    content_height = bottom - top
    rank = SEVERITY_RANK[severity]

    mask = Image.new(
        "L",
        size,
        0,
    )
    draw = ImageDraw.Draw(mask)

    if degradation_type in {
        "fading",
        "discolouration",
        "blur",
        "partial_transparency",
    }:
        fraction = {
            1: 0.28,
            2: 0.46,
            3: 0.66,
        }[rank]

        ellipse_count = {
            1: 2,
            2: 3,
            3: 4,
        }[rank]

        for _ in range(ellipse_count):
            ellipse_width = max(
                8,
                int(
                    content_width
                    * rng.uniform(
                        fraction * 0.55,
                        fraction,
                    )
                ),
            )
            ellipse_height = max(
                8,
                int(
                    content_height
                    * rng.uniform(
                        fraction * 0.55,
                        fraction,
                    )
                ),
            )

            x0 = int(
                rng.integers(
                    left,
                    max(
                        left + 1,
                        right - ellipse_width + 1,
                    ),
                )
            )
            y0 = int(
                rng.integers(
                    top,
                    max(
                        top + 1,
                        bottom - ellipse_height + 1,
                    ),
                )
            )

            draw.ellipse(
                (
                    x0,
                    y0,
                    min(right, x0 + ellipse_width),
                    min(bottom, y0 + ellipse_height),
                ),
                fill=int(
                    rng.integers(
                        150,
                        256,
                    )
                ),
            )

        blur_radius = {
            1: 22,
            2: 30,
            3: 38,
        }[rank]

        mask = mask.filter(
            ImageFilter.GaussianBlur(
                radius=blur_radius
            )
        )

    elif degradation_type == "water_stain":
        ring_count = {
            1: 1,
            2: 2,
            3: 3,
        }[rank]

        for _ in range(ring_count):
            ellipse_width = int(
                content_width
                * rng.uniform(
                    0.22,
                    0.48,
                )
            )
            ellipse_height = int(
                content_height
                * rng.uniform(
                    0.18,
                    0.42,
                )
            )

            x0 = int(
                rng.integers(
                    left,
                    max(
                        left + 1,
                        right - ellipse_width + 1,
                    ),
                )
            )
            y0 = int(
                rng.integers(
                    top,
                    max(
                        top + 1,
                        bottom - ellipse_height + 1,
                    ),
                )
            )

            bounds = (
                x0,
                y0,
                min(right, x0 + ellipse_width),
                min(bottom, y0 + ellipse_height),
            )

            draw.ellipse(
                bounds,
                fill=int(
                    rng.integers(
                        85,
                        145,
                    )
                ),
                outline=int(
                    rng.integers(
                        190,
                        256,
                    )
                ),
                width=max(
                    2,
                    int(
                        min(
                            ellipse_width,
                            ellipse_height,
                        )
                        * 0.035
                    ),
                ),
            )

        mask = mask.filter(
            ImageFilter.GaussianBlur(
                radius={
                    1: 5,
                    2: 8,
                    3: 11,
                }[rank]
            )
        )

    elif degradation_type == "dirt_dust":
        area = (
            content_width
            * content_height
        )

        particle_count = max(
            12,
            int(
                area
                * {
                    1: 0.00018,
                    2: 0.00034,
                    3: 0.00055,
                }[rank]
            ),
        )

        for _ in range(particle_count):
            radius = int(
                rng.integers(
                    1,
                    {
                        1: 4,
                        2: 6,
                        3: 8,
                    }[rank],
                )
            )
            x = int(
                rng.integers(
                    left,
                    right,
                )
            )
            y = int(
                rng.integers(
                    top,
                    bottom,
                )
            )
            draw.ellipse(
                (
                    x - radius,
                    y - radius,
                    x + radius,
                    y + radius,
                ),
                fill=int(
                    rng.integers(
                        90,
                        256,
                    )
                ),
            )

        low_frequency = Image.new(
            "L",
            size,
            0,
        )
        low_draw = ImageDraw.Draw(
            low_frequency
        )

        for _ in range(rank + 1):
            x0 = int(
                rng.integers(
                    left,
                    right,
                )
            )
            y0 = int(
                rng.integers(
                    top,
                    bottom,
                )
            )
            radius = int(
                rng.uniform(
                    0.08,
                    0.20,
                )
                * min(
                    content_width,
                    content_height,
                )
            )
            low_draw.ellipse(
                (
                    x0 - radius,
                    y0 - radius,
                    x0 + radius,
                    y0 + radius,
                ),
                fill=int(
                    rng.integers(
                        40,
                        100,
                    )
                ),
            )

        low_frequency = low_frequency.filter(
            ImageFilter.GaussianBlur(
                radius=30
            )
        )

        mask = Image.fromarray(
            np.maximum(
                np.asarray(mask),
                np.asarray(low_frequency),
            ).astype(np.uint8),
            mode="L",
        )

    else:
        raise ValueError(
            f"Unsupported degradation type: "
            f"{degradation_type}"
        )

    mask_array = (
        np.asarray(
            mask,
            dtype=np.float32,
        )
        * _content_gate(
            size,
            content_box,
        )
    )

    return Image.fromarray(
        np.clip(
            np.rint(mask_array),
            0,
            255,
        ).astype(np.uint8),
        mode="L",
    )


def _blend_with_mask(
    clean_array: np.ndarray,
    transformed_array: np.ndarray,
    effect_mask_array: np.ndarray,
    opacity: float = 1.0,
) -> np.ndarray:
    alpha = (
        effect_mask_array.astype(
            np.float32
        )
        / 255.0
    )
    alpha = np.clip(
        alpha * float(opacity),
        0.0,
        1.0,
    )[..., None]

    blended = (
        clean_array.astype(np.float32)
        * (1.0 - alpha)
        + transformed_array.astype(
            np.float32
        )
        * alpha
    )

    return np.clip(
        np.rint(blended),
        0,
        255,
    ).astype(np.uint8)


def _apply_operator(
    image_array: np.ndarray,
    effect_mask_array: np.ndarray,
    degradation_type: str,
    severity: str,
    rng: np.random.Generator,
) -> tuple[np.ndarray, dict[str, Any]]:
    parameters = _severity_parameters(
        degradation_type,
        severity,
    )

    clean_image = Image.fromarray(
        image_array,
        mode="RGB",
    )

    if degradation_type == "blur":
        transformed = np.asarray(
            clean_image.filter(
                ImageFilter.GaussianBlur(
                    radius=float(
                        parameters[
                            "blur_radius"
                        ]
                    )
                )
            )
        )

        result = _blend_with_mask(
            image_array,
            transformed,
            effect_mask_array,
            opacity=float(
                parameters[
                    "effect_opacity"
                ]
            ),
        )

    elif degradation_type == "water_stain":
        stain_colour = np.array(
            parameters[
                "stain_colour_rgb"
            ],
            dtype=np.float32,
        )

        transformed = np.broadcast_to(
            stain_colour,
            image_array.shape,
        ).astype(np.uint8)

        base_result = _blend_with_mask(
            image_array,
            transformed,
            effect_mask_array,
            opacity=float(
                parameters[
                    "stain_opacity"
                ]
            ),
        )

        mask_float = (
            effect_mask_array.astype(
                np.float32
            )
            / 255.0
        )
        ring = np.abs(
            mask_float
            - np.asarray(
                Image.fromarray(
                    effect_mask_array,
                    mode="L",
                ).filter(
                    ImageFilter.GaussianBlur(
                        radius=8
                    )
                ),
                dtype=np.float32,
            )
            / 255.0
        )

        ring_alpha = np.clip(
            ring
            * float(
                parameters[
                    "ring_strength"
                ]
            )
            * 3.0,
            0.0,
            1.0,
        )[..., None]
        
        effect_support = (
            effect_mask_array
            > 0
        )[..., None]
        
        ring_alpha = np.where(
            effect_support,
            ring_alpha,
            0.0,
        )

        darker = (
            base_result.astype(
                np.float32
            )
            * 0.72
        )

        result = np.clip(
            np.rint(
                base_result.astype(
                    np.float32
                )
                * (1.0 - ring_alpha)
                + darker
                * ring_alpha
            ),
            0,
            255,
        ).astype(np.uint8)

    elif degradation_type == "fading":
        transformed_image = (
            ImageEnhance.Color(
                clean_image
            ).enhance(
                float(
                    parameters[
                        "saturation_factor"
                    ]
                )
            )
        )

        transformed_image = (
            ImageEnhance.Contrast(
                transformed_image
            ).enhance(
                float(
                    parameters[
                        "contrast_factor"
                    ]
                )
            )
        )

        transformed_image = (
            ImageEnhance.Brightness(
                transformed_image
            ).enhance(
                float(
                    parameters[
                        "brightness_factor"
                    ]
                )
            )
        )

        result = _blend_with_mask(
            image_array,
            np.asarray(
                transformed_image
            ),
            effect_mask_array,
        )

    elif degradation_type == "discolouration":
        scales = np.array(
            [
                parameters[
                    "channel_scale_r"
                ],
                parameters[
                    "channel_scale_g"
                ],
                parameters[
                    "channel_scale_b"
                ],
            ],
            dtype=np.float32,
        )

        transformed = np.clip(
            image_array.astype(
                np.float32
            )
            * scales,
            0,
            255,
        ).astype(np.uint8)

        result = _blend_with_mask(
            image_array,
            transformed,
            effect_mask_array,
        )

    elif degradation_type == "dirt_dust":
        particle_opacity = float(
            parameters[
                "particle_opacity"
            ]
        )
        grime_strength = float(
            parameters[
                "grime_strength"
            ]
        )

        dirt_colour = np.array(
            [55, 45, 34],
            dtype=np.float32,
        )

        transformed = (
            image_array.astype(
                np.float32
            )
            * (1.0 - grime_strength)
            + dirt_colour
            * grime_strength
        )

        transformed = np.clip(
            np.rint(transformed),
            0,
            255,
        ).astype(np.uint8)

        result = _blend_with_mask(
            image_array,
            transformed,
            effect_mask_array,
            opacity=particle_opacity,
        )

        parameters[
            "particle_count_estimate"
        ] = int(
            (
                effect_mask_array > 96
            ).sum()
        )

    elif degradation_type == "partial_transparency":
        substrate = np.array(
            parameters[
                "substrate_colour_rgb"
            ],
            dtype=np.uint8,
        )

        transformed = np.broadcast_to(
            substrate,
            image_array.shape,
        )

        result = _blend_with_mask(
            image_array,
            transformed,
            effect_mask_array,
            opacity=float(
                parameters[
                    "transparency_alpha"
                ]
            ),
        )

    else:
        raise ValueError(
            f"Unsupported degradation type: "
            f"{degradation_type}"
        )

    parameters[
        "operator_seed"
    ] = int(
        rng.integers(
            0,
            2**32 - 1,
        )
    )

    return result, parameters


def _mask_metadata(
    effect_mask_array: np.ndarray,
    content_box: tuple[int, int, int, int],
) -> dict[str, Any]:
    support = effect_mask_array > 0
    active = effect_mask_array >= 13
    ys, xs = np.where(active)

    left, top, right, bottom = content_box
    content_area = (
        (right - left)
        * (bottom - top)
    )
    full_area = (
        effect_mask_array.shape[0]
        * effect_mask_array.shape[1]
    )

    if len(xs) == 0:
        bbox = (
            np.nan,
            np.nan,
            np.nan,
            np.nan,
        )
        centroid_x = np.nan
        centroid_y = np.nan
    else:
        bbox = (
            int(xs.min()),
            int(ys.min()),
            int(xs.max()) + 1,
            int(ys.max()) + 1,
        )
        centroid_x = float(
            xs.mean()
        )
        centroid_y = float(
            ys.mean()
        )

    return {
        "effect_support_pixels": int(
            support.sum()
        ),
        "effect_active_pixels": int(
            active.sum()
        ),
        "effect_percentage_content": float(
            100.0
            * active.sum()
            / content_area
        ),
        "effect_percentage_full": float(
            100.0
            * active.sum()
            / full_area
        ),
        "effect_mean_intensity": float(
            effect_mask_array[
                active
            ].mean()
            if active.any()
            else 0.0
        ),
        "effect_max_intensity": int(
            effect_mask_array.max()
        ),
        "effect_bbox_x_min": bbox[0],
        "effect_bbox_y_min": bbox[1],
        "effect_bbox_x_max": bbox[2],
        "effect_bbox_y_max": bbox[3],
        "effect_centroid_x": centroid_x,
        "effect_centroid_y": centroid_y,
    }


def _difference_metadata(
    clean_array: np.ndarray,
    degraded_array: np.ndarray,
    effect_mask_array: np.ndarray,
) -> dict[str, Any]:
    absolute_difference = np.abs(
        clean_array.astype(
            np.int16
        )
        - degraded_array.astype(
            np.int16
        )
    )

    changed = np.any(
        absolute_difference > 0,
        axis=2,
    )
    support = effect_mask_array > 0

    inside_values = (
        absolute_difference[
            support
        ]
        if support.any()
        else np.empty(
            (0, 3),
            dtype=np.int16,
        )
    )

    return {
        "changed_pixels": int(
            changed.sum()
        ),
        "changed_percentage_full": float(
            100.0
            * changed.mean()
        ),
        "outside_effect_changed_pixels": int(
            (
                changed
                & ~support
            ).sum()
        ),
        "inside_effect_changed_pixels": int(
            (
                changed
                & support
            ).sum()
        ),
        "mean_absolute_difference_effect": float(
            inside_values.mean()
            if inside_values.size
            else 0.0
        ),
        "maximum_absolute_difference": int(
            absolute_difference.max()
        ),
    }


def create_synthetic_degradation_dataset(
    processed_metadata: pd.DataFrame,
    output_effect_mask_dir: str | Path,
    output_degraded_dir: str | Path,
    project_root: str | Path | None = None,
    degradation_types: Iterable[str] = DEFAULT_DEGRADATION_TYPES,
    severity_levels: Iterable[str] = DEFAULT_SEVERITY_LEVELS,
    combined_degradations: (
        Mapping[str, Sequence[str]]
        | Iterable[str]
        | None
    ) = DEFAULT_COMBINED_DEGRADATIONS,
    combined_severity: str = "moderate",
    target_size: int = 768,
    global_seed: int = 20260707,
    overwrite: bool = True,
    compute_checksums: bool = True,
) -> pd.DataFrame:
    """Generate deterministic single and combined synthetic degradations."""
    required_columns = {
        "painting_id",
    }

    missing_columns = sorted(
        required_columns
        - set(
            processed_metadata.columns
        )
    )

    if missing_columns:
        raise ValueError(
            "Processed metadata is missing "
            f"required columns: {missing_columns}"
        )

    degradation_values = (
        _normalise_degradation_types(
            degradation_types
        )
    )
    severity_values = (
        _normalise_severity_levels(
            severity_levels
        )
    )
    combined_values = (
        _normalise_combined_degradations(
            combined_degradations
        )
    )

    if combined_severity not in SEVERITY_RANK:
        raise ValueError(
            "combined_severity must be mild, "
            "moderate, or severe."
        )

    if target_size <= 0:
        raise ValueError(
            "target_size must be positive."
        )

    metadata = (
        processed_metadata.copy()
    )
    metadata["painting_id"] = (
        metadata[
            "painting_id"
        ].astype(str)
    )

    if (
        metadata[
            "painting_id"
        ].duplicated().any()
    ):
        raise ValueError(
            "Processed metadata contains "
            "duplicate painting IDs."
        )

    project_root_path = (
        Path(project_root)
        if project_root is not None
        else None
    )

    mask_directory = Path(
        output_effect_mask_dir
    )
    degraded_directory = Path(
        output_degraded_dir
    )

    mask_directory.mkdir(
        parents=True,
        exist_ok=True,
    )
    degraded_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    records: list[
        dict[str, Any]
    ] = []

    sorted_metadata = (
        metadata
        .sort_values(
            "painting_id",
            kind="stable",
        )
        .reset_index(drop=True)
    )

    for painting_index, row in (
        sorted_metadata.iterrows()
    ):
        painting_id = str(
            row["painting_id"]
        )
        clean_path = (
            _resolve_existing_path(
                _extract_clean_path_value(
                    row
                ),
                project_root_path,
            )
        )

        if not clean_path.exists():
            raise FileNotFoundError(
                f"Clean image not found: "
                f"{clean_path}"
            )

        with Image.open(
            clean_path
        ) as opened_clean:
            clean_image = (
                opened_clean
                .convert("RGB")
            )
            clean_image.load()

        width, height = (
            clean_image.size
        )

        if (
            width != target_size
            or height != target_size
        ):
            raise ValueError(
                f"Expected {target_size}x"
                f"{target_size} image for "
                f"{painting_id}, received "
                f"{width}x{height}."
            )

        content_box = (
            _content_box_from_row(
                row,
                target_size,
            )
        )
        clean_array = np.asarray(
            clean_image
        )
        clean_sha256 = (
            compute_file_sha256(
                clean_path
            )
            if compute_checksums
            else None
        )

        case_definitions: list[
            dict[str, Any]
        ] = []

        for degradation_type in (
            degradation_values
        ):
            for severity in (
                severity_values
            ):
                case_definitions.append(
                    {
                        "degradation_type": (
                            degradation_type
                        ),
                        "severity": severity,
                        "is_combined": False,
                        "components": (
                            degradation_type,
                        ),
                    }
                )

        for combined_name, components in (
            combined_values.items()
        ):
            case_definitions.append(
                {
                    "degradation_type": (
                        combined_name
                    ),
                    "severity": (
                        combined_severity
                    ),
                    "is_combined": True,
                    "components": (
                        components
                    ),
                }
            )

        for case_definition in (
            case_definitions
        ):
            degradation_type = str(
                case_definition[
                    "degradation_type"
                ]
            )
            severity = str(
                case_definition[
                    "severity"
                ]
            )
            is_combined = bool(
                case_definition[
                    "is_combined"
                ]
            )
            components = tuple(
                case_definition[
                    "components"
                ]
            )

            case_id = (
                f"{painting_id}"
                f"__{degradation_type}"
                f"__{severity}"
            )

            case_seed = _stable_seed(
                global_seed,
                case_id,
            )
            effect_mask_seed = (
                _stable_seed(
                    case_seed,
                    "effect_mask",
                )
            )

            mask_rng = (
                np.random.default_rng(
                    effect_mask_seed
                )
            )

            mask_type = (
                components[0]
            )
            effect_mask = (
                _generate_effect_mask(
                    size=(
                        width,
                        height,
                    ),
                    content_box=(
                        content_box
                    ),
                    degradation_type=(
                        mask_type
                    ),
                    severity=severity,
                    rng=mask_rng,
                )
            )
            effect_mask_array = (
                np.asarray(
                    effect_mask,
                    dtype=np.uint8,
                )
            )

            degraded_array = (
                clean_array.copy()
            )
            component_parameter_records = []
            component_seed_records = []

            for component_index, component in (
                enumerate(components)
            ):
                operator_seed = (
                    _stable_seed(
                        case_seed,
                        "operator",
                        component_index,
                        component,
                    )
                )
                component_rng = (
                    np.random.default_rng(
                        operator_seed
                    )
                )

                degraded_array, parameters = (
                    _apply_operator(
                        image_array=(
                            degraded_array
                        ),
                        effect_mask_array=(
                            effect_mask_array
                        ),
                        degradation_type=(
                            component
                        ),
                        severity=severity,
                        rng=component_rng,
                    )
                )

                parameters[
                    "degradation_type"
                ] = component
                parameters[
                    "seed"
                ] = int(
                    operator_seed
                )

                component_parameter_records.append(
                    parameters
                )
                component_seed_records.append(
                    int(
                        operator_seed
                    )
                )

            effect_mask_filename = (
                f"{case_id}"
                f"{EFFECT_MASK_FILENAME_SUFFIX}"
            )
            degraded_filename = (
                f"{case_id}"
                f"{DEGRADED_FILENAME_SUFFIX}"
            )

            effect_mask_path = (
                mask_directory
                / effect_mask_filename
            )
            degraded_path = (
                degraded_directory
                / degraded_filename
            )

            generation_action = (
                "generated"
            )

            if (
                not overwrite
                and effect_mask_path.exists()
                and degraded_path.exists()
            ):
                generation_action = (
                    "reused_existing"
                )

                with Image.open(
                    effect_mask_path
                ) as saved_mask:
                    effect_mask_array = (
                        np.asarray(
                            saved_mask.convert(
                                "L"
                            ),
                            dtype=np.uint8,
                        )
                    )

                with Image.open(
                    degraded_path
                ) as saved_degraded:
                    degraded_array = (
                        np.asarray(
                            saved_degraded.convert(
                                "RGB"
                            ),
                            dtype=np.uint8,
                        )
                    )
            else:
                Image.fromarray(
                    effect_mask_array,
                    mode="L",
                ).save(
                    effect_mask_path,
                    format="PNG",
                )

                Image.fromarray(
                    degraded_array,
                    mode="RGB",
                ).save(
                    degraded_path,
                    format="PNG",
                )

            mask_metadata = (
                _mask_metadata(
                    effect_mask_array,
                    content_box,
                )
            )
            difference_metadata = (
                _difference_metadata(
                    clean_array,
                    degraded_array,
                    effect_mask_array,
                )
            )

            record: dict[str, Any] = {
                "case_id": case_id,
                "painting_id": (
                    painting_id
                ),
                "painting_index": int(
                    painting_index
                ),
                "degradation_type": (
                    degradation_type
                ),
                "severity": severity,
                "severity_rank": int(
                    SEVERITY_RANK[
                        severity
                    ]
                ),
                "is_combined": (
                    is_combined
                ),
                "component_degradations": (
                    "|".join(
                        components
                    )
                ),
                "component_count": int(
                    len(components)
                ),
                "global_seed": int(
                    global_seed
                ),
                "case_seed": int(
                    case_seed
                ),
                "effect_mask_seed": int(
                    effect_mask_seed
                ),
                "operator_seeds_json": (
                    json.dumps(
                        component_seed_records
                    )
                ),
                "operator_parameters_json": (
                    json.dumps(
                        component_parameter_records,
                        sort_keys=True,
                    )
                ),
                "width": int(width),
                "height": int(height),
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
                "content_area_pixels": int(
                    (
                        content_box[2]
                        - content_box[0]
                    )
                    * (
                        content_box[3]
                        - content_box[1]
                    )
                ),
                **mask_metadata,
                **difference_metadata,
                "clean_path": (
                    _safe_relative_string(
                        clean_path,
                        project_root_path,
                    )
                ),
                "effect_mask_filename": (
                    effect_mask_filename
                ),
                "effect_mask_path": (
                    _safe_relative_string(
                        effect_mask_path,
                        project_root_path,
                    )
                ),
                "degraded_filename": (
                    degraded_filename
                ),
                "degraded_path": (
                    _safe_relative_string(
                        degraded_path,
                        project_root_path,
                    )
                ),
                "clean_sha256": (
                    clean_sha256
                ),
                "effect_mask_sha256": (
                    compute_file_sha256(
                        effect_mask_path
                    )
                    if compute_checksums
                    else None
                ),
                "degraded_sha256": (
                    compute_file_sha256(
                        degraded_path
                    )
                    if compute_checksums
                    else None
                ),
                "effect_mask_file_size_bytes": (
                    effect_mask_path.stat().st_size
                ),
                "degraded_file_size_bytes": (
                    degraded_path.stat().st_size
                ),
                "generator_name": (
                    GENERATOR_NAME
                ),
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
                if (
                    metadata_column
                    in row.index
                ):
                    record[
                        metadata_column
                    ] = row[
                        metadata_column
                    ]

            records.append(
                record
            )

    result = pd.DataFrame(
        records
    )

    expected_rows = (
        len(metadata)
        * (
            len(degradation_values)
            * len(severity_values)
            + len(combined_values)
        )
    )

    if len(result) != expected_rows:
        raise RuntimeError(
            f"Expected {expected_rows} "
            f"synthetic-degradation cases, "
            f"generated {len(result)}."
        )

    return (
        result
        .sort_values(
            [
                "painting_id",
                "is_combined",
                "degradation_type",
                "severity_rank",
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def validate_synthetic_degradation_dataset(
    degradation_metadata: pd.DataFrame,
    project_root: str | Path | None = None,
    verify_checksums: bool = True,
) -> pd.DataFrame:
    """Validate saved synthetic-degradation masks and images."""
    required_columns = {
        "case_id",
        "painting_id",
        "degradation_type",
        "severity",
        "clean_path",
        "effect_mask_path",
        "degraded_path",
        "width",
        "height",
        "effect_active_pixels",
        "outside_effect_changed_pixels",
    }

    missing_columns = sorted(
        required_columns
        - set(
            degradation_metadata.columns
        )
    )

    if missing_columns:
        raise ValueError(
            "Synthetic-degradation metadata is "
            f"missing columns: {missing_columns}"
        )

    project_root_path = (
        Path(project_root)
        if project_root is not None
        else None
    )

    records: list[
        dict[str, Any]
    ] = []

    for _, row in (
        degradation_metadata.iterrows()
    ):
        issues: list[str] = []
        case_id = str(
            row["case_id"]
        )

        clean_path = (
            _resolve_existing_path(
                row["clean_path"],
                project_root_path,
            )
        )
        effect_mask_path = (
            _resolve_existing_path(
                row[
                    "effect_mask_path"
                ],
                project_root_path,
            )
        )
        degraded_path = (
            _resolve_existing_path(
                row["degraded_path"],
                project_root_path,
            )
        )

        clean_exists = (
            clean_path.exists()
        )
        effect_mask_exists = (
            effect_mask_path.exists()
        )
        degraded_exists = (
            degraded_path.exists()
        )

        readable = False
        dimensions_valid = False
        effect_mask_mode_valid = False
        degraded_mode_valid = False
        effect_mask_format_valid = False
        degraded_format_valid = False
        effect_mask_range_valid = False
        effect_nonempty = False
        degradation_nonempty = False
        outside_effect_preserved = False
        metadata_counts_match = False
        checksum_valid = True

        observed_effect_active_pixels = (
            np.nan
        )
        observed_changed_pixels = np.nan
        observed_outside_changed_pixels = (
            np.nan
        )

        try:
            if (
                clean_exists
                and effect_mask_exists
                and degraded_exists
            ):
                with Image.open(
                    clean_path
                ) as clean_image:
                    clean_array = (
                        np.asarray(
                            clean_image.convert(
                                "RGB"
                            )
                        )
                    )

                with Image.open(
                    effect_mask_path
                ) as mask_image:
                    mask_format = (
                        mask_image.format
                    )
                    mask_mode = (
                        mask_image.mode
                    )
                    mask_array = (
                        np.asarray(
                            mask_image.convert(
                                "L"
                            ),
                            dtype=np.uint8,
                        )
                    )

                with Image.open(
                    degraded_path
                ) as degraded_image:
                    degraded_format = (
                        degraded_image.format
                    )
                    degraded_mode = (
                        degraded_image.mode
                    )
                    degraded_array = (
                        np.asarray(
                            degraded_image.convert(
                                "RGB"
                            ),
                            dtype=np.uint8,
                        )
                    )

                readable = True

                expected_shape = (
                    int(row["height"]),
                    int(row["width"]),
                )

                dimensions_valid = bool(
                    clean_array.shape[:2]
                    == expected_shape
                    and mask_array.shape
                    == expected_shape
                    and degraded_array.shape[:2]
                    == expected_shape
                )
                effect_mask_mode_valid = (
                    mask_mode == "L"
                )
                degraded_mode_valid = (
                    degraded_mode == "RGB"
                )
                effect_mask_format_valid = (
                    mask_format == "PNG"
                )
                degraded_format_valid = (
                    degraded_format == "PNG"
                )
                effect_mask_range_valid = bool(
                    mask_array.min() >= 0
                    and mask_array.max() <= 255
                )

                support = mask_array > 0
                active = mask_array >= 13
                changed = np.any(
                    clean_array
                    != degraded_array,
                    axis=2,
                )

                observed_effect_active_pixels = int(
                    active.sum()
                )
                observed_changed_pixels = int(
                    changed.sum()
                )
                observed_outside_changed_pixels = int(
                    (
                        changed
                        & ~support
                    ).sum()
                )

                effect_nonempty = bool(
                    active.any()
                )
                degradation_nonempty = bool(
                    changed.any()
                )
                outside_effect_preserved = (
                    observed_outside_changed_pixels
                    == 0
                )
                metadata_counts_match = bool(
                    observed_effect_active_pixels
                    == int(
                        row[
                            "effect_active_pixels"
                        ]
                    )
                    and observed_outside_changed_pixels
                    == int(
                        row[
                            "outside_effect_changed_pixels"
                        ]
                    )
                )

                if verify_checksums:
                    checksum_fields = (
                        (
                            clean_path,
                            "clean_sha256",
                        ),
                        (
                            effect_mask_path,
                            "effect_mask_sha256",
                        ),
                        (
                            degraded_path,
                            "degraded_sha256",
                        ),
                    )

                    for (
                        checksum_path,
                        checksum_column,
                    ) in checksum_fields:
                        expected_checksum = (
                            row.get(
                                checksum_column,
                                None,
                            )
                        )

                        if (
                            expected_checksum
                            is None
                            or pd.isna(
                                expected_checksum
                            )
                            or str(
                                expected_checksum
                            ).strip() == ""
                        ):
                            checksum_valid = False
                            issues.append(
                                f"{checksum_column}"
                                "_missing"
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
                                f"{checksum_column}"
                                "_mismatch"
                            )

        except Exception as exc:
            issues.append(
                f"{type(exc).__name__}: "
                f"{exc}"
            )

        checks = {
            "dimensions_valid": (
                dimensions_valid
            ),
            "effect_mask_mode_valid": (
                effect_mask_mode_valid
            ),
            "degraded_mode_valid": (
                degraded_mode_valid
            ),
            "effect_mask_format_valid": (
                effect_mask_format_valid
            ),
            "degraded_format_valid": (
                degraded_format_valid
            ),
            "effect_mask_range_valid": (
                effect_mask_range_valid
            ),
            "effect_nonempty": (
                effect_nonempty
            ),
            "degradation_nonempty": (
                degradation_nonempty
            ),
            "outside_effect_preserved": (
                outside_effect_preserved
            ),
            "metadata_counts_match": (
                metadata_counts_match
            ),
            "checksum_valid": (
                checksum_valid
            ),
        }

        for check_name, passed in (
            checks.items()
        ):
            if readable and not passed:
                issues.append(
                    check_name
                )

        validation_passed = bool(
            clean_exists
            and effect_mask_exists
            and degraded_exists
            and readable
            and all(
                checks.values()
            )
        )

        records.append(
            {
                "case_id": case_id,
                "painting_id": (
                    row["painting_id"]
                ),
                "degradation_type": (
                    row[
                        "degradation_type"
                    ]
                ),
                "severity": (
                    row["severity"]
                ),
                "clean_exists": (
                    clean_exists
                ),
                "effect_mask_exists": (
                    effect_mask_exists
                ),
                "degraded_exists": (
                    degraded_exists
                ),
                "readable": readable,
                **checks,
                "observed_effect_active_pixels": (
                    observed_effect_active_pixels
                ),
                "observed_changed_pixels": (
                    observed_changed_pixels
                ),
                "observed_outside_effect_changed_pixels": (
                    observed_outside_changed_pixels
                ),
                "validation_passed": (
                    validation_passed
                ),
                "issue": "|".join(
                    sorted(
                        set(issues)
                    )
                ),
            }
        )

    return pd.DataFrame(
        records
    )


def audit_synthetic_degradation_inventory(
    degradation_metadata: pd.DataFrame,
    effect_mask_dir: str | Path,
    degraded_dir: str | Path,
    expected_case_ids: Iterable[str] | None = None,
    project_root: str | Path | None = None,
) -> dict[str, pd.DataFrame]:
    """Audit duplicate, missing, unexpected, stale, and orphan cases."""
    metadata = (
        degradation_metadata.copy()
    )
    metadata["case_id"] = (
        metadata[
            "case_id"
        ].astype(str)
    )

    project_root_path = (
        Path(project_root)
        if project_root is not None
        else None
    )

    duplicate_case_rows = (
        metadata[
            metadata[
                "case_id"
            ].duplicated(
                keep=False
            )
        ].copy()
    )
    duplicate_mask_path_rows = (
        metadata[
            metadata[
                "effect_mask_path"
            ].astype(str).duplicated(
                keep=False
            )
        ].copy()
    )
    duplicate_degraded_path_rows = (
        metadata[
            metadata[
                "degraded_path"
            ].astype(str).duplicated(
                keep=False
            )
        ].copy()
    )

    metadata_case_ids = set(
        metadata[
            "case_id"
        ].tolist()
    )
    expected_case_id_set = (
        {
            str(value)
            for value in expected_case_ids
        }
        if expected_case_ids
        is not None
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
    missing_degraded_records = []
    expected_mask_filenames = set()
    expected_degraded_filenames = set()

    for _, row in (
        metadata.iterrows()
    ):
        mask_path = (
            _resolve_existing_path(
                row[
                    "effect_mask_path"
                ],
                project_root_path,
            )
        )
        degraded_path = (
            _resolve_existing_path(
                row[
                    "degraded_path"
                ],
                project_root_path,
            )
        )

        expected_mask_filenames.add(
            str(
                row[
                    "effect_mask_filename"
                ]
            )
        )
        expected_degraded_filenames.add(
            str(
                row[
                    "degraded_filename"
                ]
            )
        )

        if not mask_path.exists():
            missing_mask_records.append(
                {
                    "case_id": (
                        row["case_id"]
                    ),
                    "effect_mask_path": (
                        str(mask_path)
                    ),
                }
            )

        if not degraded_path.exists():
            missing_degraded_records.append(
                {
                    "case_id": (
                        row["case_id"]
                    ),
                    "degraded_path": (
                        str(
                            degraded_path
                        )
                    ),
                }
            )

    effect_mask_directory = Path(
        effect_mask_dir
    )
    degraded_directory = Path(
        degraded_dir
    )

    actual_mask_filenames = {
        path.name
        for path in (
            effect_mask_directory.glob(
                f"*{EFFECT_MASK_FILENAME_SUFFIX}"
            )
        )
        if path.is_file()
    }
    actual_degraded_filenames = {
        path.name
        for path in (
            degraded_directory.glob(
                f"*{DEGRADED_FILENAME_SUFFIX}"
            )
        )
        if path.is_file()
    }

    orphan_mask_rows = pd.DataFrame(
        {
            "effect_mask_filename": (
                sorted(
                    actual_mask_filenames
                    - expected_mask_filenames
                )
            )
        }
    )
    orphan_degraded_rows = pd.DataFrame(
        {
            "degraded_filename": (
                sorted(
                    actual_degraded_filenames
                    - expected_degraded_filenames
                )
            )
        }
    )
    missing_mask_file_rows = (
        pd.DataFrame(
            missing_mask_records
        )
    )
    missing_degraded_file_rows = (
        pd.DataFrame(
            missing_degraded_records
        )
    )

    summary = pd.DataFrame(
        [
            {
                "check": (
                    "duplicate_case_ids"
                ),
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
                    "duplicate_effect_mask_paths"
                ),
                "issue_count": int(
                    duplicate_mask_path_rows[
                        "effect_mask_path"
                    ].nunique()
                    if not duplicate_mask_path_rows.empty
                    else 0
                ),
            },
            {
                "check": (
                    "duplicate_degraded_paths"
                ),
                "issue_count": int(
                    duplicate_degraded_path_rows[
                        "degraded_path"
                    ].nunique()
                    if not duplicate_degraded_path_rows.empty
                    else 0
                ),
            },
            {
                "check": (
                    "missing_expected_cases"
                ),
                "issue_count": len(
                    missing_case_rows
                ),
            },
            {
                "check": (
                    "unexpected_cases"
                ),
                "issue_count": len(
                    unexpected_case_rows
                ),
            },
            {
                "check": (
                    "missing_effect_mask_files"
                ),
                "issue_count": len(
                    missing_mask_file_rows
                ),
            },
            {
                "check": (
                    "missing_degraded_files"
                ),
                "issue_count": len(
                    missing_degraded_file_rows
                ),
            },
            {
                "check": (
                    "orphan_effect_mask_files"
                ),
                "issue_count": len(
                    orphan_mask_rows
                ),
            },
            {
                "check": (
                    "orphan_degraded_files"
                ),
                "issue_count": len(
                    orphan_degraded_rows
                ),
            },
        ]
    )

    summary["passed"] = (
        summary[
            "issue_count"
        ] == 0
    )

    return {
        "summary": summary,
        "duplicate_case_rows": (
            duplicate_case_rows
        ),
        "duplicate_effect_mask_path_rows": (
            duplicate_mask_path_rows
        ),
        "duplicate_degraded_path_rows": (
            duplicate_degraded_path_rows
        ),
        "missing_case_rows": (
            missing_case_rows
        ),
        "unexpected_case_rows": (
            unexpected_case_rows
        ),
        "missing_effect_mask_file_rows": (
            missing_mask_file_rows
        ),
        "missing_degraded_file_rows": (
            missing_degraded_file_rows
        ),
        "orphan_effect_mask_rows": (
            orphan_mask_rows
        ),
        "orphan_degraded_rows": (
            orphan_degraded_rows
        ),
    }
