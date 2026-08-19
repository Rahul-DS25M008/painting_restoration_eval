"""Deterministic non-binary synthetic-degradation generation for Notebook 07."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from .manifests import sha256_file
from .paths import (
    find_project_root,
    require_notebook_output_path,
    resolve_repo_path,
    to_repo_relative,
)
from .schemas import (
    PREPROCESSED_IMAGES_SCHEMA,
    SYNTHETIC_DEGRADATION_CASES_COLUMNS,
    SYNTHETIC_DEGRADATION_CASES_SCHEMA,
    SYNTHETIC_DEGRADATION_GENERATION_AUDIT_COLUMNS,
    SYNTHETIC_DEGRADATION_GENERATION_AUDIT_SCHEMA,
    validate_dataframe,
)


SYNTHETIC_DEGRADATION_MODULE_VERSION = "2.0.0"
SYNTHETIC_DEGRADATION_CONFIG_SCHEMA_VERSION = "synthetic_degradation_config.v1"
GENERATOR_NAME = "synthetic_degradation_generator"
GENERATOR_VERSION = SYNTHETIC_DEGRADATION_MODULE_VERSION
SEED_SCHEME_VERSION = "synthetic_degradation_seed.v2"

SUPPORTED_SINGLE_FAMILIES = (
    "gaussian_blur",
    "motion_blur",
    "local_defocus",
    "water_stain",
    "pigment_bleeding",
    "fading",
    "discolouration",
    "local_darkening",
    "dirt_dust",
    "partial_transparency",
)
SUPPORTED_COMBINED_FAMILIES = (
    "fading_discolouration",
    "water_stain_dirt",
    "gaussian_blur_fading",
)
SUPPORTED_SEVERITIES = ("mild", "moderate", "severe")
SEVERITY_RANK = {name: index for index, name in enumerate(SUPPORTED_SEVERITIES, 1)}


@dataclass(frozen=True)
class GeneratedDegradation:
    effect_mask: Image.Image
    degraded: Image.Image
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class SyntheticDegradationGenerationResult:
    cases: pd.DataFrame
    removed_stale_paths: tuple[str, ...]


@dataclass(frozen=True)
class SyntheticDegradationValidationResult:
    audit: pd.DataFrame
    orphan_paths: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return bool(
            not self.orphan_paths
            and len(self.audit) > 0
            and self.audit["validation_status"].eq("passed").all()
        )


def _mapping(parent: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"Synthetic-degradation configuration key {key!r} must be a mapping")
    return value


def _relative(value: Any) -> bool:
    text = str(value).strip()
    return bool(text) and not Path(text).is_absolute() and "\\" not in text


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def stable_case_seed(*parts: object, modulus: int = 2**32 - 1) -> int:
    """Return a stable platform-independent integer seed."""
    payload = "||".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % modulus


def degradation_id(family_id: str, severity: str) -> str:
    if family_id not in (*SUPPORTED_SINGLE_FAMILIES, *SUPPORTED_COMBINED_FAMILIES):
        raise ValueError(f"Unsupported degradation family: {family_id}")
    if severity not in SUPPORTED_SEVERITIES:
        raise ValueError(f"Unsupported severity: {severity}")
    return f"{family_id}__{severity}"


def degradation_case_id(painting_id: str, family_id: str, severity: str) -> str:
    return f"synthetic_degradation__{painting_id}__{degradation_id(family_id, severity)}"


def family_configuration(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    families = config.get("families")
    if not isinstance(families, list):
        return {}
    return {
        str(item.get("family_id", "")): dict(item)
        for item in families
        if isinstance(item, Mapping)
    }


def combined_configuration(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    combinations = config.get("combined_degradations")
    if not isinstance(combinations, list):
        return {}
    return {
        str(item.get("family_id", "")): dict(item)
        for item in combinations
        if isinstance(item, Mapping)
    }


def cohort_painting_ids(config: Mapping[str, Any]) -> tuple[str, ...]:
    cohort = config.get("cohort", {})
    paintings = cohort.get("paintings", []) if isinstance(cohort, Mapping) else []
    return tuple(
        str(item["painting_id"])
        for item in paintings
        if isinstance(item, Mapping) and "painting_id" in item
    )


def validate_synthetic_degradation_config(config: Mapping[str, Any]) -> list[str]:
    """Return every violation of the approved Notebook 07 contract."""
    errors: list[str] = []
    if config.get("config_schema_version") != SYNTHETIC_DEGRADATION_CONFIG_SCHEMA_VERSION:
        errors.append(
            f"config_schema_version must equal {SYNTHETIC_DEGRADATION_CONFIG_SCHEMA_VERSION}"
        )
    try:
        dataset = _mapping(config, "dataset")
        inputs = _mapping(config, "inputs")
        output = _mapping(config, "output")
        cohort = _mapping(config, "cohort")
        generator = _mapping(config, "generator")
        expected = _mapping(config, "expected")
        smoke = _mapping(config, "smoke")
        examples = _mapping(config, "examples")
        interpretation = _mapping(config, "interpretation")
    except ValueError as exc:
        return errors + [str(exc)]

    required_schemas = {
        "geometry_schema_version": PREPROCESSED_IMAGES_SCHEMA.version,
        "output_schema_version": SYNTHETIC_DEGRADATION_CASES_SCHEMA.version,
        "audit_schema_version": SYNTHETIC_DEGRADATION_GENERATION_AUDIT_SCHEMA.version,
    }
    for key, value in required_schemas.items():
        if dataset.get(key) != value:
            errors.append(f"dataset.{key} must equal {value}")
    for key in (
        "dataset_id", "dataset_version", "dataset_scope", "execution_profile",
        "experiment_id",
    ):
        if not str(dataset.get(key, "")).strip():
            errors.append(f"dataset.{key} must be non-empty")

    for key in (
        "geometry_path", "clean_images_path", "preprocessing_artifacts_path",
        "preprocessing_run_manifest_path",
    ):
        if not _relative(inputs.get(key, "")):
            errors.append(f"inputs.{key} must be a normalized repository-relative path")

    output_contract = {
        "notebook_stem": "07_synthetic_degradation_dataset_generation",
        "cases_path": "data/cases.csv",
        "effect_mask_directory": "images/effect_masks",
        "degraded_directory": "images/degraded",
        "image_path_template": "{painting_id}/{degradation_id}.png",
        "audit_path": "metrics/generation_audit.csv",
        "examples_figure_path": "figures/degradation_examples.png",
        "protocol_path": "reports/degradation_protocol.md",
    }
    for key, value in output_contract.items():
        if output.get(key) != value:
            errors.append(f"output.{key} must equal {value!r}")

    paintings = cohort.get("paintings") if isinstance(cohort.get("paintings"), list) else []
    ids = [str(item.get("painting_id", "")) for item in paintings if isinstance(item, Mapping)]
    categories = [str(item.get("category", "")) for item in paintings if isinstance(item, Mapping)]
    if ids != ["p001", "p018", "p026", "p039", "p043"]:
        errors.append("cohort painting identifiers differ from the approved balanced-five cohort")
    if len(set(categories)) != 5 or any(not value for value in categories):
        errors.append("cohort must contain five unique non-empty categories")

    severities = config.get("severity_levels")
    severity_names = [
        str(item.get("severity", "")) for item in severities
        if isinstance(severities, list) and isinstance(item, Mapping)
    ] if isinstance(severities, list) else []
    severity_ranks = [
        int(item.get("severity_rank", -1)) for item in severities
        if isinstance(item, Mapping)
    ] if isinstance(severities, list) else []
    if tuple(severity_names) != SUPPORTED_SEVERITIES or severity_ranks != [1, 2, 3]:
        errors.append("severity_levels must define mild, moderate, severe with ranks 1, 2, 3")

    families = family_configuration(config)
    if tuple(families) != SUPPORTED_SINGLE_FAMILIES:
        errors.append(f"single family order must equal {SUPPORTED_SINGLE_FAMILIES}")
    for family_id, family in families.items():
        if family.get("operator") != family_id:
            errors.append(f"family {family_id!r} operator must use the same stable identifier")
        if not str(family.get("spatial_support_type", "")).strip():
            errors.append(f"family {family_id!r} requires spatial_support_type")
        parameters = family.get("parameters")
        if not isinstance(parameters, Mapping) or tuple(parameters) != SUPPORTED_SEVERITIES:
            errors.append(f"family {family_id!r} requires parameters for all severities in order")

    combinations = combined_configuration(config)
    if tuple(combinations) != SUPPORTED_COMBINED_FAMILIES:
        errors.append(f"combined family order must equal {SUPPORTED_COMBINED_FAMILIES}")
    for family_id, combination in combinations.items():
        components = combination.get("components")
        if combination.get("severity") != "moderate":
            errors.append(f"combined family {family_id!r} must use moderate severity")
        if (
            not isinstance(components, list)
            or len(components) < 2
            or any(component not in SUPPORTED_SINGLE_FAMILIES for component in components)
        ):
            errors.append(f"combined family {family_id!r} has invalid components")

    generator_contract = {
        "name": GENERATOR_NAME,
        "version": GENERATOR_VERSION,
        "seed_scheme_version": SEED_SCHEME_VERSION,
        "target_width": 768,
        "target_height": 768,
        "effect_mask_mode": "L",
        "degraded_mode": "RGB",
        "output_format": "PNG",
        "output_extension": ".png",
        "support_threshold": 1,
        "active_threshold": 13,
        "change_threshold_rgb": 0,
        "progress_interval_cases": 10,
        "overwrite_existing": True,
        "stale_file_action": "remove",
    }
    for key, value in generator_contract.items():
        if generator.get(key) != value:
            errors.append(f"generator.{key} must equal {value!r}")

    count_contract = {
        "painting_count": 5, "category_count": 5,
        "single_family_count": 10, "severity_count": 3,
        "single_case_count": 150, "combined_family_count": 3,
        "combined_case_count": 15, "case_count": 165,
        "audit_row_count": 165, "effect_mask_file_count": 165,
        "degraded_file_count": 165, "artifact_record_count": 7,
        "total_output_file_count": 337,
    }
    for key, value in count_contract.items():
        if expected.get(key) != value:
            errors.append(f"expected.{key} must equal {value}")

    if (
        smoke.get("painting_id") != "p039"
        or smoke.get("single_severity") != "moderate"
        or smoke.get("expected_case_count") != 13
        or smoke.get("repeat_count") != 2
        or smoke.get("persist_outputs") is not False
    ):
        errors.append("smoke contract must be the non-persisted repeated 13-case p039 design")
    if examples.get("painting_id") != "p039" or examples.get("single_severity") != "moderate":
        errors.append("examples contract must use p039 at moderate single-family severity")
    if interpretation.get("branch_type") != "non_binary_procedural_degradation":
        errors.append("interpretation.branch_type must identify the non-binary branch")
    if "not exact simulations" not in str(interpretation.get("physical_claim", "")):
        errors.append("interpretation.physical_claim must state the procedural limitation")
    return errors


def load_synthetic_degradation_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError("Synthetic-degradation configuration must load as a mapping")
    config = dict(payload)
    errors = validate_synthetic_degradation_config(config)
    if errors:
        raise ValueError("Invalid synthetic-degradation configuration: " + "; ".join(errors))
    return config


def resolve_synthetic_degradation_inputs(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
    *,
    must_exist: bool = True,
) -> dict[str, Path]:
    errors = validate_synthetic_degradation_config(config)
    if errors:
        raise ValueError("Invalid synthetic-degradation configuration: " + "; ".join(errors))
    root = find_project_root(project_root)
    return {
        key: resolve_repo_path(value, root, must_exist=must_exist)
        for key, value in config["inputs"].items()
        if key.endswith("_path")
    }


def validate_synthetic_degradation_handoff(
    preprocessed: pd.DataFrame,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
    *,
    verify_files: bool = True,
) -> list[str]:
    errors = ["configuration: " + error for error in validate_synthetic_degradation_config(config)]
    schema_result = validate_dataframe(
        preprocessed,
        PREPROCESSED_IMAGES_SCHEMA,
        allow_extra_columns=False,
    )
    if not schema_result.passed or schema_result.unexpected_columns:
        errors.append(f"preprocessed schema violation: {schema_result.to_dict()}")
    if errors:
        return errors
    dataset = config["dataset"]
    for key in ("dataset_id", "dataset_version", "dataset_scope"):
        if set(preprocessed[key].astype(str)) != {str(dataset[key])}:
            errors.append(f"preprocessed {key} does not match configuration")
    if len(preprocessed) != 50 or preprocessed["painting_id"].duplicated().any():
        errors.append("preprocessed handoff must contain 50 unique paintings")
    wanted = set(cohort_painting_ids(config))
    available = set(preprocessed["painting_id"].astype(str))
    if not wanted.issubset(available):
        errors.append(f"preprocessed handoff is missing cohort paintings: {sorted(wanted - available)}")
    if verify_files:
        root = find_project_root(project_root)
        selected = preprocessed.loc[preprocessed["painting_id"].astype(str).isin(wanted)]
        missing = [
            str(row.processed_path)
            for row in selected.itertuples(index=False)
            if not resolve_repo_path(str(row.processed_path), root, must_exist=False).is_file()
        ]
        if missing:
            errors.append(f"cohort clean images are missing: {missing}")
    return errors


def select_synthetic_degradation_cohort(
    preprocessed: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    errors = validate_synthetic_degradation_handoff(preprocessed, config, verify_files=False)
    if errors:
        raise ValueError("Invalid Notebook 02 handoff: " + "; ".join(errors))
    category_by_id = {
        str(item["painting_id"]): str(item["category"])
        for item in config["cohort"]["paintings"]
    }
    order = {painting_id: index for index, painting_id in enumerate(cohort_painting_ids(config))}
    result = preprocessed.loc[
        preprocessed["painting_id"].astype(str).isin(order)
    ].copy()
    result["category"] = result["painting_id"].astype(str).map(category_by_id)
    result["_cohort_order"] = result["painting_id"].astype(str).map(order)
    return result.sort_values("_cohort_order").drop(columns="_cohort_order").reset_index(drop=True)


def build_degradation_design(config: Mapping[str, Any]) -> pd.DataFrame:
    """Build the normalized deterministic 165-case design without touching files."""
    errors = validate_synthetic_degradation_config(config)
    if errors:
        raise ValueError("Invalid synthetic-degradation configuration: " + "; ".join(errors))
    categories = {
        str(item["painting_id"]): str(item["category"])
        for item in config["cohort"]["paintings"]
    }
    records: list[dict[str, Any]] = []
    for painting_id in cohort_painting_ids(config):
        for family_id in SUPPORTED_SINGLE_FAMILIES:
            for severity in SUPPORTED_SEVERITIES:
                records.append(
                    _design_record(painting_id, categories[painting_id], family_id, severity, (family_id,))
                )
        for family_id, combination in combined_configuration(config).items():
            records.append(
                _design_record(
                    painting_id,
                    categories[painting_id],
                    family_id,
                    str(combination["severity"]),
                    tuple(str(value) for value in combination["components"]),
                )
            )
    design = pd.DataFrame.from_records(records)
    if len(design) != int(config["expected"]["case_count"]):
        raise RuntimeError("Constructed design does not match expected case count")
    if design["case_id"].duplicated().any() or design["degradation_id"].isna().any():
        raise RuntimeError("Constructed design contains invalid identifiers")
    return design


def _design_record(
    painting_id: str,
    category: str,
    family_id: str,
    severity: str,
    components: Sequence[str],
) -> dict[str, Any]:
    return {
        "case_id": degradation_case_id(painting_id, family_id, severity),
        "degradation_id": degradation_id(family_id, severity),
        "painting_id": painting_id,
        "category": category,
        "degradation_family": family_id,
        "severity": severity,
        "severity_rank": SEVERITY_RANK[severity],
        "is_combined": len(components) > 1,
        "component_degradations_json": _json(list(components)),
        "component_count": len(components),
        "operator_sequence_json": _json(list(components)),
    }


def smoke_design(config: Mapping[str, Any]) -> pd.DataFrame:
    design = build_degradation_design(config)
    smoke = config["smoke"]
    return design.loc[
        design["painting_id"].eq(str(smoke["painting_id"]))
        & (
            design["is_combined"]
            | design["severity"].eq(str(smoke["single_severity"]))
        )
    ].reset_index(drop=True)


def _content_box(row: Mapping[str, Any]) -> tuple[int, int, int, int]:
    return tuple(int(row[key]) for key in ("content_x_min", "content_y_min", "content_x_max", "content_y_max"))


def _content_gate(size: tuple[int, int], box: tuple[int, int, int, int]) -> np.ndarray:
    width, height = size
    gate = np.zeros((height, width), dtype=np.uint8)
    x0, y0, x1, y1 = box
    gate[y0:y1, x0:x1] = 255
    return gate


def _soft_blobs(
    size: tuple[int, int],
    box: tuple[int, int, int, int],
    rng: np.random.Generator,
    *,
    count: int,
    coverage_fraction: float,
    broad: bool = False,
) -> np.ndarray:
    width, height = size
    x0, y0, x1, y1 = box
    content_width, content_height = x1 - x0, y1 - y0
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    base_area = max(1.0, coverage_fraction * content_width * content_height / max(count, 1))
    for _ in range(count):
        aspect = float(rng.uniform(0.65, 1.55))
        blob_width = min(content_width, max(8, int(round(math.sqrt(base_area * aspect) * 1.35))))
        blob_height = min(content_height, max(8, int(round(math.sqrt(base_area / aspect) * 1.35))))
        if broad:
            blob_width = min(content_width, max(blob_width, int(content_width * 0.55)))
            blob_height = min(content_height, max(blob_height, int(content_height * 0.55)))
        cx = int(rng.integers(x0 + blob_width // 2, max(x0 + blob_width // 2 + 1, x1 - blob_width // 2)))
        cy = int(rng.integers(y0 + blob_height // 2, max(y0 + blob_height // 2 + 1, y1 - blob_height // 2)))
        draw.ellipse(
            (cx - blob_width // 2, cy - blob_height // 2, cx + blob_width // 2, cy + blob_height // 2),
            fill=int(rng.integers(190, 256)),
        )
    feather = max(2.0, 0.025 * min(content_width, content_height))
    array = np.asarray(mask.filter(ImageFilter.GaussianBlur(feather)), dtype=np.uint8)
    return np.minimum(array, _content_gate(size, box))


def _ring_stain(
    size: tuple[int, int],
    box: tuple[int, int, int, int],
    rng: np.random.Generator,
    coverage_fraction: float,
) -> np.ndarray:
    width, height = size
    x0, y0, x1, y1 = box
    content_width, content_height = x1 - x0, y1 - y0
    area = coverage_fraction * content_width * content_height
    radius_x = min(content_width // 2, max(14, int(math.sqrt(area / math.pi) * 1.25)))
    radius_y = min(content_height // 2, max(14, int(radius_x * rng.uniform(0.65, 1.15))))
    cx = int(rng.integers(x0 + radius_x, max(x0 + radius_x + 1, x1 - radius_x)))
    cy = int(rng.integers(y0 + radius_y, max(y0 + radius_y + 1, y1 - radius_y)))
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    angle_values = np.linspace(0.0, 2.0 * math.pi, 72, endpoint=False)
    radial_noise = rng.normal(0.0, 0.075, size=angle_values.size)
    radial_noise = sum(np.roll(radial_noise, shift) for shift in range(-2, 3)) / 5.0
    outer_points = [
        (
            int(round(cx + radius_x * (1.0 + noise) * math.cos(angle))),
            int(round(cy + radius_y * (1.0 + noise) * math.sin(angle))),
        )
        for angle, noise in zip(angle_values, radial_noise)
    ]
    inner_noise = np.roll(radial_noise, 9) * 0.55
    inner_points = [
        (
            int(round(cx + radius_x * 0.70 * (1.0 + noise) * math.cos(angle))),
            int(round(cy + radius_y * 0.70 * (1.0 + noise) * math.sin(angle))),
        )
        for angle, noise in zip(angle_values, inner_noise)
    ]
    draw.polygon(outer_points, fill=118)
    draw.polygon(inner_points, fill=62)
    draw.line(
        (*outer_points, outer_points[0]),
        fill=255,
        width=max(3, int(min(radius_x, radius_y) * 0.10)),
        joint="curve",
    )
    array = np.asarray(mask.filter(ImageFilter.GaussianBlur(max(2.0, min(radius_x, radius_y) * 0.045))), dtype=np.uint8)
    return np.minimum(array, _content_gate(size, box))


def _speckles(
    size: tuple[int, int],
    box: tuple[int, int, int, int],
    rng: np.random.Generator,
    parameters: Mapping[str, Any],
) -> np.ndarray:
    x0, y0, x1, y1 = box
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    radius_max = int(parameters["radius_max"])
    for _ in range(int(parameters["speck_count"])):
        x, y = int(rng.integers(x0, x1)), int(rng.integers(y0, y1))
        radius = int(rng.integers(1, radius_max + 1))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=int(rng.integers(120, 256)))
    for _ in range(int(parameters["streak_count"])):
        start = (int(rng.integers(x0, x1)), int(rng.integers(y0, y1)))
        length = int(rng.integers(8, 30))
        angle = float(rng.uniform(0, 2 * math.pi))
        end = (int(start[0] + length * math.cos(angle)), int(start[1] + length * math.sin(angle)))
        draw.line((start, end), fill=int(rng.integers(100, 220)), width=int(rng.integers(1, 3)))
    array = np.asarray(mask.filter(ImageFilter.GaussianBlur(0.65)), dtype=np.uint8)
    return np.minimum(array, _content_gate(size, box))


def generate_effect_mask(
    size: tuple[int, int],
    content_box: tuple[int, int, int, int],
    family_id: str,
    parameters: Mapping[str, Any],
    seed: int,
    spatial_support_type: str,
) -> Image.Image:
    """Create an independent grayscale operator-influence mask."""
    rng = np.random.default_rng(seed)
    if spatial_support_type == "full_content":
        array = _content_gate(size, content_box)
    elif spatial_support_type == "soft_ring_stain":
        array = _ring_stain(size, content_box, rng, float(parameters["coverage_fraction"]))
    elif spatial_support_type == "speckles_and_streaks":
        array = _speckles(size, content_box, rng, parameters)
    elif spatial_support_type in {"soft_local_blobs", "soft_broad_patch"}:
        array = _soft_blobs(
            size,
            content_box,
            rng,
            count=int(parameters.get("blob_count", 2 if spatial_support_type == "soft_broad_patch" else 1)),
            coverage_fraction=float(parameters["coverage_fraction"]),
            broad=spatial_support_type == "soft_broad_patch",
        )
    else:
        raise ValueError(f"Unsupported spatial support type: {spatial_support_type}")
    return Image.fromarray(array.astype(np.uint8), mode="L")


def _blend(base: np.ndarray, transformed: np.ndarray, mask: np.ndarray, strength: float) -> np.ndarray:
    alpha = np.clip(mask.astype(np.float32) / 255.0 * float(strength), 0.0, 1.0)[..., None]
    return np.rint(base.astype(np.float32) * (1.0 - alpha) + transformed.astype(np.float32) * alpha).clip(0, 255).astype(np.uint8)


def _motion_blur(array: np.ndarray, length: int, angle_degrees: float) -> np.ndarray:
    offsets = np.linspace(-(length // 2), length // 2, length)
    angle = math.radians(angle_degrees)
    dx = [int(round(value * math.cos(angle))) for value in offsets]
    dy = [int(round(value * math.sin(angle))) for value in offsets]
    pad = max(max(abs(value) for value in dx), max(abs(value) for value in dy), 1)
    padded = np.pad(array, ((pad, pad), (pad, pad), (0, 0)), mode="edge")
    height, width = array.shape[:2]
    shifted = [
        padded[pad - one_dy:pad - one_dy + height, pad - one_dx:pad - one_dx + width]
        for one_dx, one_dy in zip(dx, dy)
    ]
    return np.rint(np.mean(np.stack(shifted, axis=0), axis=0)).astype(np.uint8)


def _shift_channel(channel: np.ndarray, dx: int, dy: int) -> np.ndarray:
    pad = max(abs(dx), abs(dy), 1)
    padded = np.pad(channel, ((pad, pad), (pad, pad)), mode="edge")
    height, width = channel.shape
    return padded[pad - dy:pad - dy + height, pad - dx:pad - dx + width]


def apply_degradation_operator(
    image: Image.Image,
    effect_mask: Image.Image,
    family_id: str,
    parameters: Mapping[str, Any],
    seed: int,
) -> Image.Image:
    """Apply one operator only where its independent influence mask is non-zero."""
    base = np.asarray(image.convert("RGB"), dtype=np.uint8)
    mask = np.asarray(effect_mask.convert("L"), dtype=np.uint8)
    strength = float(parameters.get("strength", 1.0))
    rng = np.random.default_rng(seed)

    if family_id in {"gaussian_blur", "local_defocus"}:
        transformed = np.asarray(
            image.convert("RGB").filter(ImageFilter.GaussianBlur(float(parameters["radius"]))),
            dtype=np.uint8,
        )
    elif family_id == "motion_blur":
        transformed = _motion_blur(base, int(parameters["kernel_length"]), float(parameters["angle_degrees"]))
    elif family_id == "water_stain":
        tint = np.asarray(parameters["tint_rgb"], dtype=np.float32)
        transformed = np.rint(base.astype(np.float32) * 0.50 + tint * 0.50).clip(0, 255).astype(np.uint8)
    elif family_id == "pigment_bleeding":
        blurred = np.asarray(
            image.convert("RGB").filter(ImageFilter.GaussianBlur(float(parameters["radius"]))),
            dtype=np.uint8,
        )
        shift = int(parameters["channel_shift"])
        transformed = np.stack(
            (
                _shift_channel(blurred[..., 0], shift, 0),
                blurred[..., 1],
                _shift_channel(blurred[..., 2], -shift, max(1, shift // 2)),
            ),
            axis=-1,
        )
    elif family_id == "fading":
        pil = ImageEnhance.Color(image.convert("RGB")).enhance(float(parameters["saturation_factor"]))
        pil = ImageEnhance.Contrast(pil).enhance(float(parameters["contrast_factor"]))
        pil = ImageEnhance.Brightness(pil).enhance(float(parameters["brightness_factor"]))
        transformed = np.asarray(pil, dtype=np.uint8)
    elif family_id == "discolouration":
        tint = np.asarray(parameters["tint_rgb"], dtype=np.float32)
        transformed = np.rint(base.astype(np.float32) * 0.68 + tint * 0.32).clip(0, 255).astype(np.uint8)
    elif family_id == "local_darkening":
        transformed = np.rint(base.astype(np.float32) * float(parameters["darkness_factor"])).clip(0, 255).astype(np.uint8)
    elif family_id == "dirt_dust":
        colour = np.asarray([72, 58, 42], dtype=np.float32)
        noise = rng.normal(0.0, 7.0, size=base.shape[:2])[..., None]
        transformed = np.rint(base.astype(np.float32) * 0.42 + colour * 0.58 + noise).clip(0, 255).astype(np.uint8)
    elif family_id == "partial_transparency":
        substrate = np.asarray(parameters["substrate_rgb"], dtype=np.float32)
        loss = float(parameters["opacity_loss"])
        transformed = np.rint(base.astype(np.float32) * (1.0 - loss) + substrate * loss).clip(0, 255).astype(np.uint8)
    else:
        raise ValueError(f"Unsupported degradation operator: {family_id}")
    return Image.fromarray(_blend(base, transformed, mask, strength), mode="RGB")


def _impact_metrics(clean: np.ndarray, degraded: np.ndarray, support: np.ndarray) -> dict[str, float | int]:
    difference = degraded.astype(np.float32) - clean.astype(np.float32)
    absolute = np.abs(difference)
    changed = np.any(absolute > 0, axis=2)
    support_bool = support > 0
    if support_bool.any():
        supported_abs = absolute[support_bool]
        colour_distance = np.linalg.norm(difference[support_bool], axis=1)
        mean_absolute = float(supported_abs.mean())
        mean_colour_distance = float(colour_distance.mean())
    else:
        mean_absolute = 0.0
        mean_colour_distance = 0.0
    clean_float = clean.astype(np.float32) / 255.0
    degraded_float = degraded.astype(np.float32) / 255.0
    clean_luma = clean_float @ np.asarray([0.2126, 0.7152, 0.0722], dtype=np.float32)
    degraded_luma = degraded_float @ np.asarray([0.2126, 0.7152, 0.0722], dtype=np.float32)
    clean_sat = clean_float.max(axis=2) - clean_float.min(axis=2)
    degraded_sat = degraded_float.max(axis=2) - degraded_float.min(axis=2)
    region = support_bool if support_bool.any() else np.ones(support.shape, dtype=bool)
    clean_gradient = _gradient_energy(clean_luma, region)
    degraded_gradient = _gradient_energy(degraded_luma, region)
    clean_laplacian = _laplacian_variance(clean_luma, region)
    degraded_laplacian = _laplacian_variance(degraded_luma, region)
    return {
        "changed_pixels": int(changed.sum()),
        "outside_support_changed_pixels": int((changed & ~support_bool).sum()),
        "mean_absolute_rgb_difference": mean_absolute,
        "mean_rgb_colour_distance": mean_colour_distance,
        "mean_luminance_shift": float((degraded_luma[region] - clean_luma[region]).mean()),
        "mean_saturation_shift": float((degraded_sat[region] - clean_sat[region]).mean()),
        "gradient_energy_ratio": float(degraded_gradient / max(clean_gradient, 1e-12)),
        "laplacian_variance_ratio": float(degraded_laplacian / max(clean_laplacian, 1e-12)),
    }


def _gradient_energy(values: np.ndarray, region: np.ndarray) -> float:
    gx = np.zeros_like(values)
    gy = np.zeros_like(values)
    gx[:, 1:] = np.abs(np.diff(values, axis=1))
    gy[1:, :] = np.abs(np.diff(values, axis=0))
    return float((gx[region] + gy[region]).mean()) if region.any() else 0.0


def _laplacian_variance(values: np.ndarray, region: np.ndarray) -> float:
    laplacian = np.zeros_like(values)
    laplacian[1:-1, 1:-1] = (
        -4 * values[1:-1, 1:-1]
        + values[:-2, 1:-1] + values[2:, 1:-1]
        + values[1:-1, :-2] + values[1:-1, 2:]
    )
    return float(laplacian[region].var()) if region.any() else 0.0


def generate_degradation_case(
    clean_image: Image.Image,
    geometry: Mapping[str, Any],
    design_row: Mapping[str, Any],
    config: Mapping[str, Any],
) -> GeneratedDegradation:
    """Generate one single or ordered combined case entirely in memory."""
    clean = clean_image.convert("RGB")
    if clean.size != (int(geometry["width"]), int(geometry["height"])):
        raise ValueError("Clean image dimensions do not match Notebook 02 geometry")
    content_box = _content_box(geometry)
    components = tuple(json.loads(str(design_row["component_degradations_json"])))
    families = family_configuration(config)
    global_seed = int(config["generator"]["global_seed"])
    case_seed = stable_case_seed(
        config["generator"]["seed_scheme_version"], global_seed,
        design_row["case_id"],
    )
    effect_mask_seed = stable_case_seed(case_seed, "effect_mask")
    current = clean
    component_masks: list[np.ndarray] = []
    operator_seeds: dict[str, int] = {}
    operator_parameters: dict[str, Mapping[str, Any]] = {}
    for index, component in enumerate(components):
        family = families[component]
        parameters = dict(family["parameters"][str(design_row["severity"])])
        mask_seed = stable_case_seed(effect_mask_seed, index, component)
        operator_seed = stable_case_seed(case_seed, "operator", index, component)
        mask = generate_effect_mask(
            clean.size, content_box, component, parameters, mask_seed,
            str(family["spatial_support_type"]),
        )
        current = apply_degradation_operator(current, mask, component, parameters, operator_seed)
        component_masks.append(np.asarray(mask, dtype=np.uint8))
        operator_seeds[component] = operator_seed
        operator_parameters[component] = parameters
    combined_mask = np.maximum.reduce(component_masks)
    clean_array = np.asarray(clean, dtype=np.uint8)
    degraded_array = np.asarray(current, dtype=np.uint8)
    support_threshold = int(config["generator"]["support_threshold"])
    active_threshold = int(config["generator"]["active_threshold"])
    support = combined_mask >= support_threshold
    active = combined_mask >= active_threshold
    content_area = int(geometry["content_area_pixels"])
    impact = _impact_metrics(clean_array, degraded_array, combined_mask)
    metadata = {
        "spatial_support_type": "combined_union" if len(components) > 1 else str(families[components[0]]["spatial_support_type"]),
        "support_threshold": support_threshold,
        "active_threshold": active_threshold,
        "affected_support_pixels": int(support.sum()),
        "affected_active_pixels": int(active.sum()),
        "affected_content_fraction": float(support.sum() / content_area),
        "changed_content_fraction": float(int(impact["changed_pixels"]) / content_area),
        "seed_scheme_version": str(config["generator"]["seed_scheme_version"]),
        "global_seed": global_seed,
        "case_seed": case_seed,
        "effect_mask_seed": effect_mask_seed,
        "operator_seeds_json": _json(operator_seeds),
        "operator_parameters_json": _json(operator_parameters),
        **impact,
    }
    return GeneratedDegradation(
        effect_mask=Image.fromarray(combined_mask, mode="L"),
        degraded=current.convert("RGB"),
        metadata=metadata,
    )


def _clear_png_files(directory: Path) -> tuple[str, ...]:
    removed: list[str] = []
    if directory.exists():
        for path in sorted(directory.rglob("*.png")):
            path.unlink()
            removed.append(path.as_posix())
        for path in sorted(directory.rglob("*"), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
    directory.mkdir(parents=True, exist_ok=True)
    return tuple(removed)


def generate_synthetic_degradation_dataset(
    preprocessed: pd.DataFrame,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
    *,
    output_root: str | Path | None = None,
    design: pd.DataFrame | None = None,
    persist: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> SyntheticDegradationGenerationResult:
    """Generate the configured design; smoke designs may remain non-persistent."""
    root = find_project_root(project_root)
    errors = validate_synthetic_degradation_handoff(preprocessed, config, root, verify_files=True)
    if errors:
        raise ValueError("Invalid Notebook 02 handoff: " + "; ".join(errors))
    cohort = select_synthetic_degradation_cohort(preprocessed, config).set_index("painting_id")
    selected_design = build_degradation_design(config) if design is None else design.copy()
    notebook_stem = str(config["output"]["notebook_stem"])
    canonical_root = root / "outputs" / notebook_stem
    resolved_output_root = canonical_root if output_root is None else Path(output_root).resolve()
    if persist:
        require_notebook_output_path(resolved_output_root, notebook_stem, root)
    mask_root = resolved_output_root / str(config["output"]["effect_mask_directory"])
    degraded_root = resolved_output_root / str(config["output"]["degraded_directory"])
    removed: tuple[str, ...] = ()
    if persist and config["generator"]["stale_file_action"] == "remove":
        removed = _clear_png_files(mask_root) + _clear_png_files(degraded_root)

    records: list[dict[str, Any]] = []
    total = len(selected_design)
    interval = int(config["generator"]["progress_interval_cases"])
    for completed, design_row in enumerate(selected_design.to_dict("records"), start=1):
        painting_id = str(design_row["painting_id"])
        geometry = cohort.loc[painting_id].to_dict()
        clean_path = resolve_repo_path(str(geometry["processed_path"]), root)
        with Image.open(clean_path) as handle:
            generated = generate_degradation_case(handle.convert("RGB"), geometry, design_row, config)
        relative_name = str(config["output"]["image_path_template"]).format(
            painting_id=painting_id,
            degradation_id=design_row["degradation_id"],
        )
        mask_path = mask_root / relative_name
        degraded_path = degraded_root / relative_name
        if persist:
            mask_path.parent.mkdir(parents=True, exist_ok=True)
            degraded_path.parent.mkdir(parents=True, exist_ok=True)
            save_kwargs = {
                "format": "PNG",
                "compress_level": int(config["generator"]["png_compress_level"]),
                "optimize": bool(config["generator"]["png_optimize"]),
            }
            generated.effect_mask.save(mask_path, **save_kwargs)
            generated.degraded.save(degraded_path, **save_kwargs)
            clean_sha = sha256_file(clean_path)
            mask_sha = sha256_file(mask_path)
            degraded_sha = sha256_file(degraded_path)
            mask_size, degraded_size = mask_path.stat().st_size, degraded_path.stat().st_size
            mask_relative = to_repo_relative(mask_path, root)
            degraded_relative = to_repo_relative(degraded_path, root)
        else:
            clean_sha = sha256_file(clean_path)
            mask_sha = hashlib.sha256(np.asarray(generated.effect_mask).tobytes()).hexdigest()
            degraded_sha = hashlib.sha256(np.asarray(generated.degraded).tobytes()).hexdigest()
            mask_size = degraded_size = 0
            mask_relative = ""
            degraded_relative = ""
        record = {
            "dataset_id": str(config["dataset"]["dataset_id"]),
            "dataset_version": str(config["dataset"]["dataset_version"]),
            "dataset_scope": str(config["dataset"]["dataset_scope"]),
            "experiment_id": str(config["dataset"]["experiment_id"]),
            **design_row,
            "processed_image_id": str(geometry["processed_image_id"]),
            "clean_image_path": to_repo_relative(clean_path, root),
            "effect_mask_path": mask_relative,
            "degraded_image_path": degraded_relative,
            "content_x_min": int(geometry["content_x_min"]),
            "content_y_min": int(geometry["content_y_min"]),
            "content_x_max": int(geometry["content_x_max"]),
            "content_y_max": int(geometry["content_y_max"]),
            "content_width": int(geometry["content_width"]),
            "content_height": int(geometry["content_height"]),
            "content_area_pixels": int(geometry["content_area_pixels"]),
            "width": int(geometry["width"]),
            "height": int(geometry["height"]),
            **generated.metadata,
            "clean_image_sha256": clean_sha,
            "effect_mask_sha256": mask_sha,
            "degraded_image_sha256": degraded_sha,
            "effect_mask_size_bytes": int(mask_size),
            "degraded_image_size_bytes": int(degraded_size),
            "effect_mask_mode": "L",
            "degraded_mode": "RGB",
            "format": "PNG",
            "generator_name": GENERATOR_NAME,
            "generator_version": GENERATOR_VERSION,
            "config_schema_version": SYNTHETIC_DEGRADATION_CONFIG_SCHEMA_VERSION,
            "config_version": str(config["config_version"]),
            "source_manifest_path": str(config["inputs"]["preprocessing_run_manifest_path"]),
            "generation_status": "passed",
            "status": "passed",
            "issue": "",
        }
        records.append(record)
        if progress_callback and (completed % interval == 0 or completed == total):
            progress_callback(completed, total, str(design_row["case_id"]))
    cases = pd.DataFrame.from_records(records)
    if persist:
        cases = cases.loc[:, SYNTHETIC_DEGRADATION_CASES_COLUMNS]
        schema_result = validate_dataframe(cases, SYNTHETIC_DEGRADATION_CASES_SCHEMA, allow_extra_columns=False)
        if not schema_result.passed or schema_result.unexpected_columns:
            raise RuntimeError(f"Generated cases violate schema: {schema_result.to_dict()}")
    return SyntheticDegradationGenerationResult(cases=cases, removed_stale_paths=removed)


def validate_saved_synthetic_degradation_dataset(
    cases: pd.DataFrame,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> SyntheticDegradationValidationResult:
    """Independently reload every canonical case and reconcile saved metadata."""
    root = find_project_root(project_root)
    case_schema = validate_dataframe(cases, SYNTHETIC_DEGRADATION_CASES_SCHEMA, allow_extra_columns=False)
    if not case_schema.passed or case_schema.unexpected_columns:
        raise ValueError(f"Cases violate schema: {case_schema.to_dict()}")
    audit_records: list[dict[str, Any]] = []
    expected_paths: set[Path] = set()
    metric_columns = (
        "mean_absolute_rgb_difference", "mean_rgb_colour_distance",
        "mean_luminance_shift", "mean_saturation_shift",
        "gradient_energy_ratio", "laplacian_variance_ratio",
    )
    for row in cases.to_dict("records"):
        clean_path = resolve_repo_path(str(row["clean_image_path"]), root, must_exist=False)
        mask_path = resolve_repo_path(str(row["effect_mask_path"]), root, must_exist=False)
        degraded_path = resolve_repo_path(str(row["degraded_image_path"]), root, must_exist=False)
        expected_paths.update((mask_path.resolve(), degraded_path.resolve()))
        clean_exists, mask_exists, degraded_exists = clean_path.is_file(), mask_path.is_file(), degraded_path.is_file()
        reload_passed = False
        dimensions_match = False
        mask_mode_valid = False
        degraded_mode_valid = False
        format_valid = False
        content_only = False
        support_match = False
        active_match = False
        changed_match = False
        changed_within = False
        outside_changed = -1
        if clean_exists and mask_exists and degraded_exists:
            try:
                with Image.open(clean_path) as clean_handle, Image.open(mask_path) as mask_handle, Image.open(degraded_path) as degraded_handle:
                    clean_format, mask_format, degraded_format = clean_handle.format, mask_handle.format, degraded_handle.format
                    clean = np.asarray(clean_handle.convert("RGB"), dtype=np.uint8)
                    mask = np.asarray(mask_handle.convert("L"), dtype=np.uint8)
                    degraded = np.asarray(degraded_handle.convert("RGB"), dtype=np.uint8)
                    mask_mode_valid = mask_handle.mode == "L"
                    degraded_mode_valid = degraded_handle.mode == "RGB"
                reload_passed = True
                dimensions_match = clean.shape[:2] == mask.shape == degraded.shape[:2]
                format_valid = clean_format == mask_format == degraded_format == "PNG"
                x0, y0, x1, y1 = _content_box(row)
                gate = np.zeros(mask.shape, dtype=bool)
                gate[y0:y1, x0:x1] = True
                support = mask >= int(row["support_threshold"])
                active = mask >= int(row["active_threshold"])
                changed = np.any(clean != degraded, axis=2)
                content_only = not bool((support & ~gate).any())
                support_match = int(support.sum()) == int(row["affected_support_pixels"])
                active_match = int(active.sum()) == int(row["affected_active_pixels"])
                changed_match = int(changed.sum()) == int(row["changed_pixels"])
                outside_changed = int((changed & ~support).sum())
                changed_within = outside_changed == 0
            except (OSError, ValueError):
                reload_passed = False
        parameters_recorded = _valid_nonempty_json_mapping(row["operator_parameters_json"])
        seeds_recorded = (
            int(row["case_seed"]) >= 0
            and int(row["effect_mask_seed"]) >= 0
            and _valid_nonempty_json_mapping(row["operator_seeds_json"])
        )
        clean_sha_matches = clean_exists and sha256_file(clean_path) == str(row["clean_image_sha256"])
        mask_sha_matches = mask_exists and sha256_file(mask_path) == str(row["effect_mask_sha256"])
        degraded_sha_matches = degraded_exists and sha256_file(degraded_path) == str(row["degraded_image_sha256"])
        impact_finite = all(np.isfinite(float(row[column])) for column in metric_columns)
        checks = {
            "clean_file_exists": clean_exists,
            "effect_mask_file_exists": mask_exists,
            "degraded_file_exists": degraded_exists,
            "reload_passed": reload_passed,
            "dimensions_match": dimensions_match,
            "effect_mask_mode_valid": mask_mode_valid,
            "degraded_mode_valid": degraded_mode_valid,
            "format_valid": format_valid,
            "content_only_valid": content_only,
            "parameters_recorded": parameters_recorded,
            "seeds_recorded": seeds_recorded,
            "affected_support_pixels_match": support_match,
            "affected_active_pixels_match": active_match,
            "changed_pixels_match": changed_match,
            "changed_pixels_within_support": changed_within,
            "outside_support_changed_pixels": outside_changed,
            "clean_sha256_matches": clean_sha_matches,
            "effect_mask_sha256_matches": mask_sha_matches,
            "degraded_image_sha256_matches": degraded_sha_matches,
            "clean_reference_unchanged": clean_sha_matches,
            "impact_metrics_finite": impact_finite,
        }
        contract_valid = all(
            bool(value) for key, value in checks.items()
            if key != "outside_support_changed_pixels"
        ) and outside_changed == 0
        failed = [key for key, value in checks.items() if (key == "outside_support_changed_pixels" and value != 0) or (key != "outside_support_changed_pixels" and not value)]
        audit_records.append(
            {
                "dataset_id": row["dataset_id"],
                "dataset_version": row["dataset_version"],
                "dataset_scope": row["dataset_scope"],
                "experiment_id": row["experiment_id"],
                "case_id": row["case_id"],
                "degradation_id": row["degradation_id"],
                "painting_id": row["painting_id"],
                "degradation_family": row["degradation_family"],
                "severity": row["severity"],
                "is_combined": row["is_combined"],
                **checks,
                "output_contract_valid": contract_valid,
                "validation_status": "passed" if contract_valid else "failed",
                "issue": "; ".join(failed),
            }
        )
    audit = pd.DataFrame.from_records(audit_records).loc[:, SYNTHETIC_DEGRADATION_GENERATION_AUDIT_COLUMNS]
    audit_schema = validate_dataframe(
        audit,
        SYNTHETIC_DEGRADATION_GENERATION_AUDIT_SCHEMA,
        allow_extra_columns=False,
    )
    if not audit_schema.passed or audit_schema.unexpected_columns:
        failed_rows = audit.loc[audit["validation_status"].ne("passed"), ["case_id", "issue"]]
        if failed_rows.empty:
            raise RuntimeError(f"Audit violates schema: {audit_schema.to_dict()}")
    notebook_root = root / "outputs" / str(config["output"]["notebook_stem"])
    actual_paths = {
        path.resolve()
        for directory in (
            notebook_root / str(config["output"]["effect_mask_directory"]),
            notebook_root / str(config["output"]["degraded_directory"]),
        )
        if directory.exists()
        for path in directory.rglob("*.png")
    }
    orphan_paths = tuple(sorted(to_repo_relative(path, root) for path in actual_paths - expected_paths))
    return SyntheticDegradationValidationResult(audit=audit, orphan_paths=orphan_paths)


def _valid_nonempty_json_mapping(value: Any) -> bool:
    try:
        payload = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return isinstance(payload, Mapping) and bool(payload)


def create_degradation_examples_figure(
    cases: pd.DataFrame,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
    *,
    output_path: str | Path,
) -> Path:
    """Render one compact clean/single/combined figure with support insets."""
    import matplotlib.pyplot as plt

    root = find_project_root(project_root)
    painting_id = str(config["examples"]["painting_id"])
    severity = str(config["examples"]["single_severity"])
    selected = cases.loc[
        cases["painting_id"].astype(str).eq(painting_id)
        & (cases["is_combined"].astype(bool) | cases["severity"].astype(str).eq(severity))
    ].copy()
    family_order = {name: index for index, name in enumerate((*SUPPORTED_SINGLE_FAMILIES, *SUPPORTED_COMBINED_FAMILIES))}
    selected["_order"] = selected["degradation_family"].map(family_order)
    selected = selected.sort_values("_order")
    if len(selected) != 13:
        raise ValueError("Example figure requires the complete 13-case p039 selection")
    clean_path = resolve_repo_path(str(selected.iloc[0]["clean_image_path"]), root)
    with Image.open(clean_path) as handle:
        clean = np.asarray(handle.convert("RGB"))
    figure, axes = plt.subplots(3, 5, figsize=(16, 10), constrained_layout=True)
    flat = axes.ravel()
    flat[0].imshow(clean)
    flat[0].set_title("Clean reference")
    flat[0].axis("off")
    for axis, row in zip(flat[1:], selected.to_dict("records")):
        with Image.open(resolve_repo_path(str(row["degraded_image_path"]), root)) as handle:
            degraded = np.asarray(handle.convert("RGB"))
        with Image.open(resolve_repo_path(str(row["effect_mask_path"]), root)) as handle:
            mask = np.asarray(handle.convert("L"))
        axis.imshow(degraded)
        if np.any(mask >= int(row["active_threshold"])):
            axis.contour(mask >= int(row["active_threshold"]), levels=[0.5], colors=["cyan"], linewidths=0.45)
        axis.set_title(str(row["degradation_family"]).replace("_", " "), fontsize=9)
        axis.axis("off")
        inset = axis.inset_axes([0.72, 0.02, 0.26, 0.26])
        inset.imshow(mask, cmap="gray", vmin=0, vmax=255)
        inset.axis("off")
    for axis in flat[len(selected) + 1:]:
        axis.axis("off")
    figure.suptitle(
        "Procedural non-binary degradation examples (cyan: active support; inset: influence mask)",
        fontsize=13,
    )
    target = Path(output_path)
    require_notebook_output_path(target, str(config["output"]["notebook_stem"]), root)
    target.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(target, dpi=int(config["examples"]["figure_dpi"]), bbox_inches="tight")
    plt.close(figure)
    return target
