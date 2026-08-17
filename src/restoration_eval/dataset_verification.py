"""Reusable, deterministic dataset verification for artwork source collections."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

import pandas as pd
import yaml
from PIL import Image, ImageCms, ImageOps

from .paths import find_project_root, resolve_repo_path, to_repo_relative
from .schemas import (
    ARTWORKS_COLUMNS,
    ARTWORKS_SCHEMA,
    DATASET_AUDIT_COLUMNS,
    DATASET_AUDIT_SCHEMA,
    RAW_ARTWORK_METADATA_SCHEMA,
    validate_dataframe,
)


DATASET_VERIFICATION_MODULE_VERSION = "1.0.0"
DATASET_CONFIG_SCHEMA_VERSION = "dataset_config.v1"
DATASET_FINGERPRINT_VERSION = "dataset_fingerprint.v1"
DHASH_METHOD_VERSION = "dhash64.v1"

IMAGE_AUDIT_COLUMNS = (
    "painting_id",
    "raw_filename",
    "raw_image_path",
    "file_exists",
    "image_verified",
    "image_loaded",
    "raw_width",
    "raw_height",
    "raw_mode",
    "raw_format",
    "raw_size_bytes",
    "raw_sha256",
    "raw_dhash64",
    "raw_exif_orientation",
    "raw_icc_profile_present",
    "raw_icc_profile_description",
    "width_matches_metadata",
    "height_matches_metadata",
    "minimum_resolution_passed",
    "extension_allowed",
    "format_allowed",
    "mode_allowed",
    "exact_duplicate",
    "near_duplicate_candidate",
    "issue",
)

NEAR_DUPLICATE_COLUMNS = (
    "painting_id_a",
    "painting_id_b",
    "filename_a",
    "filename_b",
    "dhash_a",
    "dhash_b",
    "hamming_distance",
    "threshold",
    "review_status",
)


@dataclass(frozen=True)
class ImageAuditResult:
    """Structured image audit with duplicate evidence and orphan paths."""

    images: pd.DataFrame
    exact_duplicate_groups: tuple[tuple[str, ...], ...]
    near_duplicate_candidates: pd.DataFrame
    orphan_image_paths: tuple[str, ...]


def _usable(value: Any) -> bool:
    return not pd.isna(value) and bool(str(value).strip())


def _clean_optional(value: Any) -> Any:
    return str(value).strip() if _usable(value) else pd.NA


def _require_mapping(parent: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"Dataset configuration key {key!r} must be a mapping")
    return value


def validate_dataset_config(config: Mapping[str, Any]) -> list[str]:
    """Return configuration-contract errors without resolving filesystem paths."""
    errors: list[str] = []
    if config.get("config_schema_version") != DATASET_CONFIG_SCHEMA_VERSION:
        errors.append("config_schema_version must equal dataset_config.v1")

    try:
        dataset = _require_mapping(config, "dataset")
        paths = _require_mapping(config, "paths")
        expected = _require_mapping(config, "expected")
        metadata = _require_mapping(config, "metadata")
        validation = _require_mapping(config, "validation")
        preview = _require_mapping(config, "preview")
    except ValueError as exc:
        return errors + [str(exc)]

    for key in (
        "dataset_id",
        "dataset_version",
        "dataset_scope",
        "execution_profile",
        "metadata_schema_version",
        "artworks_schema_version",
        "audit_schema_version",
    ):
        if not str(dataset.get(key, "")).strip():
            errors.append(f"dataset.{key} must be non-empty")

    expected_schema_versions = {
        "metadata_schema_version": RAW_ARTWORK_METADATA_SCHEMA.version,
        "artworks_schema_version": ARTWORKS_SCHEMA.version,
        "audit_schema_version": DATASET_AUDIT_SCHEMA.version,
    }
    for key, expected_version in expected_schema_versions.items():
        if dataset.get(key) != expected_version:
            errors.append(f"dataset.{key} must equal {expected_version}")

    for key in ("metadata_path", "raw_image_dir"):
        if not str(paths.get(key, "")).strip():
            errors.append(f"paths.{key} must be non-empty")

    total = expected.get("total_paintings")
    if not isinstance(total, int) or total <= 0:
        errors.append("expected.total_paintings must be a positive integer")
    for group_key in ("categories", "sources"):
        counts = expected.get(group_key)
        if not isinstance(counts, Mapping) or not counts:
            errors.append(f"expected.{group_key} must be a non-empty mapping")
        elif isinstance(total, int) and sum(int(value) for value in counts.values()) != total:
            errors.append(f"expected.{group_key} counts must sum to total_paintings")

    for key in (
        "required_columns",
        "required_nonblank_columns",
        "descriptive_completeness_fields",
        "optional_descriptive_fields",
        "prompt_metadata_fields",
    ):
        value = metadata.get(key)
        if not isinstance(value, list) or not value:
            errors.append(f"metadata.{key} must be a non-empty list")

    if metadata.get("required_columns") != list(RAW_ARTWORK_METADATA_SCHEMA.required_columns):
        errors.append("metadata.required_columns must match raw_artwork_metadata.v1")

    identifier_pattern = str(validation.get("painting_id_regex", ""))
    try:
        re.compile(identifier_pattern)
    except re.error:
        errors.append("validation.painting_id_regex is invalid")

    near_duplicate = validation.get("near_duplicate")
    if not isinstance(near_duplicate, Mapping):
        errors.append("validation.near_duplicate must be a mapping")
    else:
        if near_duplicate.get("method") != "dhash64":
            errors.append("validation.near_duplicate.method must equal dhash64")
        if near_duplicate.get("method_version") != DHASH_METHOD_VERSION:
            errors.append(
                f"validation.near_duplicate.method_version must equal {DHASH_METHOD_VERSION}"
            )
        if near_duplicate.get("hash_size") != 8:
            errors.append("validation.near_duplicate.hash_size must equal 8")
        threshold = near_duplicate.get("hamming_distance_threshold")
        if not isinstance(threshold, int) or not 0 <= threshold <= 64:
            errors.append(
                "validation.near_duplicate.hamming_distance_threshold must be 0..64"
            )

    if not isinstance(validation.get("accepted_source_license_pairs"), list):
        errors.append("validation.accepted_source_license_pairs must be a list")
    if not isinstance(preview.get("items_per_group"), int) or preview.get(
        "items_per_group", 0
    ) <= 0:
        errors.append("preview.items_per_group must be a positive integer")

    bias_notes = config.get("bias_notes")
    if not isinstance(bias_notes, list) or not bias_notes:
        errors.append("bias_notes must be a non-empty list")
    else:
        bias_ids = [str(item.get("bias_id", "")) for item in bias_notes]
        if any(not value for value in bias_ids) or len(set(bias_ids)) != len(bias_ids):
            errors.append("bias_notes require unique non-empty bias_id values")
        for item in bias_notes:
            if not all(str(item.get(key, "")).strip() for key in (
                "bias_category",
                "statement",
                "evidence_basis",
            )):
                errors.append("every bias note requires category, statement, and evidence")
                break
    return errors


def load_dataset_config(path: str | Path) -> dict[str, Any]:
    """Load and validate one versioned dataset configuration."""
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Dataset configuration not found: {config_path}")
    with config_path.open("r", encoding="utf-8-sig") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError("Dataset configuration must load as a mapping")
    config = dict(payload)
    errors = validate_dataset_config(config)
    if errors:
        raise ValueError("Invalid dataset configuration: " + "; ".join(errors))
    return config


def resolve_dataset_inputs(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
    *,
    must_exist: bool = True,
) -> dict[str, Path]:
    """Resolve declared metadata and raw-image inputs within the repository."""
    errors = validate_dataset_config(config)
    if errors:
        raise ValueError("Invalid dataset configuration: " + "; ".join(errors))
    root = find_project_root(project_root)
    paths = config["paths"]
    return {
        "metadata_path": resolve_repo_path(
            paths["metadata_path"], root, must_exist=must_exist
        ),
        "raw_image_dir": resolve_repo_path(
            paths["raw_image_dir"], root, must_exist=must_exist
        ),
    }


def load_raw_metadata(path: str | Path) -> pd.DataFrame:
    """Load source metadata, normalize headings, and convert blank text to NA."""
    metadata_path = Path(path)
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Raw metadata not found: {metadata_path}")
    frame = pd.read_csv(
        metadata_path,
        dtype={"painting_id": "string", "filename": "string"},
    )
    frame.columns = [str(column).strip() for column in frame.columns]
    duplicate_columns = frame.columns[frame.columns.duplicated()].tolist()
    if duplicate_columns:
        raise ValueError(f"Duplicate metadata column names: {duplicate_columns}")
    for column in frame.select_dtypes(include=["object", "string"]).columns:
        frame[column] = frame[column].map(_clean_optional)
    return frame


def metadata_contract_report(
    metadata: pd.DataFrame,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Return deterministic metadata, identity, distribution, and rights findings."""
    schema_result = validate_dataframe(
        metadata,
        RAW_ARTWORK_METADATA_SCHEMA,
        allow_extra_columns=False,
    )
    settings = config["metadata"]
    validation = config["validation"]
    expected = config["expected"]
    required_nonblank = settings["required_nonblank_columns"]
    blank_counts = {
        column: int((~metadata[column].map(_usable)).sum())
        for column in required_nonblank
        if column in metadata.columns
    }
    identifier_pattern = re.compile(str(validation["painting_id_regex"]))
    invalid_ids = sorted(
        value
        for value in metadata.get("painting_id", pd.Series(dtype="string")).dropna()
        if not identifier_pattern.fullmatch(str(value))
    )
    filename_mismatches: list[str] = []
    if validation.get("filename_must_match_painting_id", False):
        for row in metadata[["painting_id", "filename"]].itertuples(index=False):
            if Path(str(row.filename)).stem != str(row.painting_id):
                filename_mismatches.append(str(row.painting_id))

    allowed_schemes = set(validation["source_url_schemes"])
    invalid_urls: list[str] = []
    for row in metadata[["painting_id", "source_url"]].itertuples(index=False):
        parsed = urlparse(str(row.source_url))
        if parsed.scheme not in allowed_schemes or not parsed.netloc:
            invalid_urls.append(str(row.painting_id))

    allowed_pairs = {
        (str(item["source"]), str(item["license"]))
        for item in validation["accepted_source_license_pairs"]
    }
    invalid_rights = [
        str(row.painting_id)
        for row in metadata[["painting_id", "source", "license"]].itertuples(
            index=False
        )
        if (str(row.source), str(row.license)) not in allowed_pairs
    ]

    normalized_status = metadata["status"].astype("string").str.lower()
    allowed_status = set(validation["accepted_selection_statuses"])
    invalid_status = metadata.loc[
        ~normalized_status.isin(allowed_status), "painting_id"
    ].astype(str).tolist()

    actual_categories = metadata["category"].value_counts().sort_index().to_dict()
    actual_sources = metadata["source"].value_counts().sort_index().to_dict()
    configured_categories = {
        str(key): int(value) for key, value in expected["categories"].items()
    }
    configured_sources = {
        str(key): int(value) for key, value in expected["sources"].items()
    }
    ordered_ids = metadata["painting_id"].astype(str).tolist()
    return {
        "schema": schema_result.to_dict(),
        "row_count": int(len(metadata)),
        "expected_row_count": int(expected["total_paintings"]),
        "required_blank_counts": blank_counts,
        "invalid_painting_ids": invalid_ids,
        "duplicate_painting_id_rows": int(
            metadata.duplicated("painting_id", keep=False).sum()
        ),
        "duplicate_filename_rows": int(
            metadata.duplicated("filename", keep=False).sum()
        ),
        "duplicate_full_rows": int(metadata.duplicated(keep=False).sum()),
        "filename_id_mismatches": filename_mismatches,
        "invalid_source_urls": invalid_urls,
        "invalid_source_license_pairs": invalid_rights,
        "invalid_selection_statuses": invalid_status,
        "actual_category_counts": actual_categories,
        "expected_category_counts": configured_categories,
        "category_counts_match": actual_categories == configured_categories,
        "actual_source_counts": actual_sources,
        "expected_source_counts": configured_sources,
        "source_counts_match": actual_sources == configured_sources,
        "source_order_is_deterministic": ordered_ids == sorted(ordered_ids),
    }


def sha256_file(path: str | Path) -> str:
    """Return a full SHA-256 file digest."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dhash_hex(
    image: Image.Image,
    *,
    hash_size: int = 8,
    apply_exif_orientation: bool = True,
) -> str:
    """Return a fixed-width horizontal difference hash for one PIL image."""
    if hash_size <= 0:
        raise ValueError("hash_size must be positive")
    working = ImageOps.exif_transpose(image) if apply_exif_orientation else image.copy()
    resized = working.convert("L").resize(
        (hash_size + 1, hash_size),
        Image.Resampling.LANCZOS,
    )
    pixels = list(resized.getdata())
    value = 0
    bit_index = 0
    for y in range(hash_size):
        offset = y * (hash_size + 1)
        for x in range(hash_size):
            if pixels[offset + x] > pixels[offset + x + 1]:
                value |= 1 << bit_index
            bit_index += 1
    width = (hash_size * hash_size + 3) // 4
    return f"{value:0{width}x}"


def hamming_distance_hex(left: str, right: str) -> int:
    """Return bitwise Hamming distance between equal-width hexadecimal hashes."""
    if len(left) != len(right):
        raise ValueError("Hashes must have equal widths")
    return (int(left, 16) ^ int(right, 16)).bit_count()


def _icc_description(raw_profile: bytes | None) -> str:
    if not raw_profile:
        return ""
    try:
        profile = ImageCms.ImageCmsProfile(io.BytesIO(raw_profile))
        return ImageCms.getProfileDescription(profile).strip()
    except Exception as exc:  # Pillow builds vary in LittleCMS support.
        return f"unreadable:{type(exc).__name__}"


def audit_image_collection(
    metadata: pd.DataFrame,
    image_dir: str | Path,
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
) -> ImageAuditResult:
    """Audit referenced images and return exact/near duplicate evidence."""
    root = find_project_root(project_root)
    directory = resolve_repo_path(image_dir, root, must_exist=True)
    validation = config["validation"]
    near_policy = validation["near_duplicate"]
    allowed_extensions = {str(value).lower() for value in validation["allowed_extensions"]}
    allowed_formats = {str(value) for value in validation["allowed_image_formats"]}
    allowed_modes = {str(value) for value in validation["allowed_image_modes"]}
    minimum_width = int(validation["minimum_width"])
    minimum_height = int(validation["minimum_height"])
    records: list[dict[str, Any]] = []

    ordered = metadata.sort_values("painting_id", kind="stable").reset_index(drop=True)
    for row in ordered.itertuples(index=False):
        painting_id = str(row.painting_id)
        filename = str(row.filename)
        path = directory / filename
        relative_path = to_repo_relative(path, root)
        record: dict[str, Any] = {
            "painting_id": painting_id,
            "raw_filename": filename,
            "raw_image_path": relative_path,
            "file_exists": path.is_file(),
            "image_verified": False,
            "image_loaded": False,
            "raw_width": pd.NA,
            "raw_height": pd.NA,
            "raw_mode": pd.NA,
            "raw_format": pd.NA,
            "raw_size_bytes": pd.NA,
            "raw_sha256": pd.NA,
            "raw_dhash64": pd.NA,
            "raw_exif_orientation": pd.NA,
            "raw_icc_profile_present": False,
            "raw_icc_profile_description": pd.NA,
            "width_matches_metadata": False,
            "height_matches_metadata": False,
            "minimum_resolution_passed": False,
            "extension_allowed": path.suffix.lower() in allowed_extensions,
            "format_allowed": False,
            "mode_allowed": False,
            "exact_duplicate": False,
            "near_duplicate_candidate": False,
            "issue": "",
        }
        issues: list[str] = []
        if not record["extension_allowed"]:
            issues.append("extension_not_allowed")
        if not record["file_exists"]:
            issues.append("missing_file")
        else:
            record["raw_size_bytes"] = int(path.stat().st_size)
            try:
                with Image.open(path) as image:
                    image.verify()
                record["image_verified"] = True
            except Exception as exc:
                issues.append(f"verify_failed:{type(exc).__name__}:{exc}")
            try:
                with Image.open(path) as image:
                    image.load()
                    record["image_loaded"] = True
                    record["raw_width"], record["raw_height"] = map(int, image.size)
                    record["raw_mode"] = str(image.mode)
                    record["raw_format"] = str(image.format)
                    orientation = image.getexif().get(274, 1) or 1
                    record["raw_exif_orientation"] = int(orientation)
                    raw_icc = image.info.get("icc_profile")
                    record["raw_icc_profile_present"] = bool(raw_icc)
                    description = _icc_description(raw_icc)
                    record["raw_icc_profile_description"] = (
                        description if description else pd.NA
                    )
                    record["raw_dhash64"] = dhash_hex(
                        image,
                        hash_size=int(near_policy["hash_size"]),
                        apply_exif_orientation=bool(
                            near_policy["apply_exif_orientation"]
                        ),
                    )
                record["raw_sha256"] = sha256_file(path)
            except Exception as exc:
                issues.append(f"load_failed:{type(exc).__name__}:{exc}")

        if record["image_loaded"]:
            record["width_matches_metadata"] = int(record["raw_width"]) == int(
                row.original_width
            )
            record["height_matches_metadata"] = int(record["raw_height"]) == int(
                row.original_height
            )
            record["minimum_resolution_passed"] = (
                int(record["raw_width"]) >= minimum_width
                and int(record["raw_height"]) >= minimum_height
            )
            record["format_allowed"] = record["raw_format"] in allowed_formats
            record["mode_allowed"] = record["raw_mode"] in allowed_modes
            if not record["width_matches_metadata"] or not record[
                "height_matches_metadata"
            ]:
                issues.append("metadata_dimension_mismatch")
            if not record["minimum_resolution_passed"]:
                issues.append("minimum_resolution_failed")
            if not record["format_allowed"]:
                issues.append("format_not_allowed")
            if not record["mode_allowed"]:
                issues.append("mode_not_allowed")
        record["issue"] = "|".join(issues)
        records.append(record)

    images = pd.DataFrame(records, columns=IMAGE_AUDIT_COLUMNS)
    duplicate_groups: list[tuple[str, ...]] = []
    hashes = images.dropna(subset=["raw_sha256"])
    for _, group in hashes.groupby("raw_sha256", sort=True):
        if len(group) > 1:
            members = tuple(sorted(group["painting_id"].astype(str)))
            duplicate_groups.append(members)
    exact_ids = {identifier for group in duplicate_groups for identifier in group}
    if exact_ids:
        images.loc[images["painting_id"].isin(exact_ids), "exact_duplicate"] = True

    threshold = int(near_policy["hamming_distance_threshold"])
    valid_hash_rows = images.dropna(subset=["raw_dhash64"])
    candidate_records: list[dict[str, Any]] = []
    for left, right in combinations(valid_hash_rows.to_dict("records"), 2):
        distance = hamming_distance_hex(left["raw_dhash64"], right["raw_dhash64"])
        if distance <= threshold:
            candidate_records.append(
                {
                    "painting_id_a": left["painting_id"],
                    "painting_id_b": right["painting_id"],
                    "filename_a": left["raw_filename"],
                    "filename_b": right["raw_filename"],
                    "dhash_a": left["raw_dhash64"],
                    "dhash_b": right["raw_dhash64"],
                    "hamming_distance": distance,
                    "threshold": threshold,
                    "review_status": "review_required",
                }
            )
    near_candidates = pd.DataFrame(candidate_records, columns=NEAR_DUPLICATE_COLUMNS)
    if not near_candidates.empty:
        near_ids = set(near_candidates["painting_id_a"]) | set(
            near_candidates["painting_id_b"]
        )
        images.loc[
            images["painting_id"].isin(near_ids), "near_duplicate_candidate"
        ] = True

    referenced = set(metadata["filename"].dropna().astype(str))
    available = {
        path.name
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in allowed_extensions
    }
    orphan_paths = tuple(
        to_repo_relative(directory / name, root) for name in sorted(available - referenced)
    )
    return ImageAuditResult(
        images=images,
        exact_duplicate_groups=tuple(sorted(duplicate_groups)),
        near_duplicate_candidates=near_candidates,
        orphan_image_paths=orphan_paths,
    )


def _rights_status_lookup(config: Mapping[str, Any]) -> dict[tuple[str, str], str]:
    return {
        (str(item["source"]), str(item["license"])): str(item["rights_status"])
        for item in config["validation"]["accepted_source_license_pairs"]
    }


def build_artworks_table(
    metadata: pd.DataFrame,
    image_audit: ImageAuditResult,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the normalized authoritative artwork table without writing it."""
    dataset = config["dataset"]
    metadata_settings = config["metadata"]
    validation = config["validation"]
    rights_lookup = _rights_status_lookup(config)
    exact_ids = {
        identifier
        for group in image_audit.exact_duplicate_groups
        for identifier in group
    }
    image_by_id = image_audit.images.set_index("painting_id", drop=False)
    records: list[dict[str, Any]] = []
    ordered = metadata.sort_values("painting_id", kind="stable").reset_index(drop=True)
    for index, row in enumerate(ordered.itertuples(index=False), start=1):
        painting_id = str(row.painting_id)
        image = image_by_id.loc[painting_id]
        source = str(row.source)
        license_value = str(row.license)
        rights_status = rights_lookup.get((source, license_value), "unapproved")
        prompt_fields = metadata_settings["prompt_metadata_fields"]
        prompt_count = sum(_usable(getattr(row, field)) for field in prompt_fields)
        if prompt_count == 0:
            prompt_status = "none"
        elif prompt_count == len(prompt_fields):
            prompt_status = "complete"
        else:
            prompt_status = "partial"
        completeness_fields = metadata_settings["descriptive_completeness_fields"]
        completeness_pct = round(
            100.0
            * sum(_usable(getattr(row, field)) for field in completeness_fields)
            / len(completeness_fields),
            2,
        )
        exclusion_reasons: list[str] = []
        selection_status = str(row.status).strip().lower()
        if selection_status not in set(validation["accepted_selection_statuses"]):
            exclusion_reasons.append("selection_status_not_accepted")
        if rights_status == "unapproved":
            exclusion_reasons.append("source_license_pair_not_accepted")
        if painting_id in exact_ids:
            exclusion_reasons.append("exact_duplicate_image")
        for flag, issue in (
            (image["file_exists"], "missing_image"),
            (image["image_verified"], "image_verify_failed"),
            (image["image_loaded"], "image_load_failed"),
            (image["width_matches_metadata"], "metadata_width_mismatch"),
            (image["height_matches_metadata"], "metadata_height_mismatch"),
            (image["minimum_resolution_passed"], "minimum_resolution_failed"),
            (image["extension_allowed"], "extension_not_allowed"),
            (image["format_allowed"], "format_not_allowed"),
            (image["mode_allowed"], "mode_not_allowed"),
        ):
            if not bool(flag):
                exclusion_reasons.append(issue)
        records.append(
            {
                "dataset_id": dataset["dataset_id"],
                "dataset_version": dataset["dataset_version"],
                "dataset_scope": dataset["dataset_scope"],
                "painting_id": painting_id,
                "dataset_sort_index": index,
                "title": str(row.title),
                "artist": str(row.artist),
                "date_or_period": _clean_optional(row.date),
                "style_or_period": _clean_optional(row.style_or_period),
                "category": str(row.category),
                "medium": _clean_optional(row.medium),
                "source": source,
                "source_url": str(row.source_url),
                "license": license_value,
                "rights_status": rights_status,
                "source_selection_status": selection_status,
                "raw_image_path": image["raw_image_path"],
                "raw_filename": image["raw_filename"],
                "raw_width": image["raw_width"],
                "raw_height": image["raw_height"],
                "raw_mode": image["raw_mode"],
                "raw_format": image["raw_format"],
                "raw_size_bytes": image["raw_size_bytes"],
                "raw_sha256": image["raw_sha256"],
                "raw_dhash64": image["raw_dhash64"],
                "raw_exif_orientation": image["raw_exif_orientation"],
                "raw_icc_profile_present": bool(image["raw_icc_profile_present"]),
                "raw_icc_profile_description": image[
                    "raw_icc_profile_description"
                ],
                "metadata_completeness_pct": completeness_pct,
                "prompt_metadata_field_count": prompt_count,
                "prompt_metadata_status": prompt_status,
                "selection_reason": str(row.selection_reason),
                "visual_complexity_note": str(row.visual_complexity_note),
                "source_notes": _clean_optional(row.notes),
                "acceptance_status": "excluded" if exclusion_reasons else "accepted",
                "exclusion_reason": (
                    "|".join(sorted(set(exclusion_reasons)))
                    if exclusion_reasons
                    else pd.NA
                ),
            }
        )
    frame = pd.DataFrame(records, columns=ARTWORKS_COLUMNS)
    result = validate_dataframe(frame, ARTWORKS_SCHEMA, allow_extra_columns=False)
    if not result.passed:
        raise ValueError(f"Artwork table violates schema: {result.to_dict()}")
    return frame


def dataset_content_fingerprint(
    metadata: pd.DataFrame,
    image_audit: ImageAuditResult,
    config: Mapping[str, Any],
) -> str:
    """Hash normalized ordered metadata plus ordered full image checksums."""
    dataset = config["dataset"]
    ordered_metadata = metadata.sort_values("painting_id", kind="stable").copy()
    ordered_metadata = ordered_metadata.where(pd.notna(ordered_metadata), None)
    metadata_records = json.loads(
        ordered_metadata.to_json(orient="records", force_ascii=False)
    )
    image_records = (
        image_audit.images[["painting_id", "raw_image_path", "raw_sha256"]]
        .sort_values("painting_id", kind="stable")
        .where(pd.notna, None)
        .to_dict("records")
    )
    payload = {
        "fingerprint_version": DATASET_FINGERPRINT_VERSION,
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["dataset_version"],
        "dataset_scope": dataset["dataset_scope"],
        "metadata": metadata_records,
        "images": image_records,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _hhi(counts: pd.Series) -> float:
    total = float(counts.sum())
    return float(((counts / total) ** 2).sum()) if total else float("nan")


def build_dataset_audit(
    metadata: pd.DataFrame,
    image_audit: ImageAuditResult,
    artworks: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the consolidated long-form dataset audit without writing it."""
    dataset = config["dataset"]
    records: list[dict[str, Any]] = []

    def add(
        section: str,
        metric_name: str,
        metric_value: Any = pd.NA,
        *,
        group_field: str = "",
        group_value: str = "",
        metric_unit: str = "",
        numerator: Any = pd.NA,
        denominator: Any = pd.NA,
        status: str = "observed",
        details: str = "",
    ) -> None:
        identity = "|".join(
            [section, group_field, str(group_value), metric_name]
        ).encode("utf-8")
        records.append(
            {
                "audit_row_id": "audit_" + hashlib.sha256(identity).hexdigest()[:20],
                "dataset_id": dataset["dataset_id"],
                "dataset_version": dataset["dataset_version"],
                "dataset_scope": dataset["dataset_scope"],
                "audit_section": section,
                "group_field": group_field,
                "group_value": str(group_value),
                "metric_name": metric_name,
                "metric_value": metric_value,
                "metric_unit": metric_unit,
                "numerator": numerator,
                "denominator": denominator,
                "status": status,
                "details": details,
            }
        )

    images = image_audit.images
    summary_metrics = (
        ("metadata_row_count", len(metadata)),
        ("accepted_artwork_count", (artworks["acceptance_status"] == "accepted").sum()),
        ("excluded_artwork_count", (artworks["acceptance_status"] == "excluded").sum()),
        ("referenced_image_count", len(images)),
        ("orphan_image_count", len(image_audit.orphan_image_paths)),
        ("missing_image_count", (~images["file_exists"]).sum()),
        ("unreadable_image_count", (~images["image_loaded"]).sum()),
        (
            "dimension_mismatch_count",
            (~(images["width_matches_metadata"] & images["height_matches_metadata"])).sum(),
        ),
        ("exact_duplicate_group_count", len(image_audit.exact_duplicate_groups)),
        ("near_duplicate_candidate_pair_count", len(image_audit.near_duplicate_candidates)),
        ("prompt_metadata_complete_count", (artworks["prompt_metadata_status"] == "complete").sum()),
        ("prompt_metadata_partial_count", (artworks["prompt_metadata_status"] == "partial").sum()),
        ("icc_profile_present_count", artworks["raw_icc_profile_present"].sum()),
        (
            "non_default_exif_orientation_count",
            (pd.to_numeric(artworks["raw_exif_orientation"], errors="coerce") != 1).sum(),
        ),
    )
    for name, value in summary_metrics:
        add("summary", name, int(value), metric_unit="count")

    for column in metadata.columns:
        present = int(metadata[column].map(_usable).sum())
        total = int(len(metadata))
        add(
            "metadata_completeness",
            "coverage_pct",
            round(100.0 * present / total, 2),
            group_field="metadata_field",
            group_value=column,
            metric_unit="percent",
            numerator=present,
            denominator=total,
        )

    for field in ("category", "source", "license", "style_or_period", "medium", "date"):
        values = metadata[field].dropna().astype(str)
        counts = values.value_counts().sort_index()
        for value, count in counts.items():
            add(
                "distribution",
                "painting_count",
                int(count),
                group_field=("date_or_period" if field == "date" else field),
                group_value=value,
                metric_unit="count",
                numerator=int(count),
                denominator=int(len(metadata)),
                details=f"share_pct={100.0 * int(count) / len(metadata):.2f}",
            )

    categories = list(config["expected"]["categories"])
    for category in categories:
        category_rows = artworks.loc[artworks["category"] == category]
        for prompt_status in ("complete", "partial"):
            count = int(
                (category_rows["prompt_metadata_status"] == prompt_status).sum()
            )
            add(
                "prompt_readiness",
                "painting_count",
                count,
                group_field="category_prompt_status",
                group_value=f"{category}|{prompt_status}",
                metric_unit="count",
                numerator=count,
                denominator=int(len(category_rows)),
            )

    category_counts = metadata["category"].value_counts()
    category_shares = category_counts / len(metadata)
    category_values = (
        ("category_count_max", int(category_counts.max()), "count"),
        ("category_count_min", int(category_counts.min()), "count"),
        ("category_share_max_pct", round(100 * category_shares.max(), 2), "percent"),
        ("category_share_min_pct", round(100 * category_shares.min(), 2), "percent"),
        (
            "category_max_min_ratio",
            round(float(category_counts.max() / category_counts.min()), 4),
            "ratio",
        ),
        ("category_hhi", round(_hhi(category_counts), 6), "index"),
    )
    for name, value, unit in category_values:
        add("imbalance", name, value, group_field="category", metric_unit=unit)

    source_counts = metadata["source"].value_counts()
    source_shares = source_counts / len(metadata)
    source_values = (
        ("source_count_max", int(source_counts.max()), "count"),
        ("source_count_min", int(source_counts.min()), "count"),
        ("source_share_max_pct", round(100 * source_shares.max(), 2), "percent"),
        (
            "source_max_min_ratio",
            round(float(source_counts.max() / source_counts.min()), 4),
            "ratio",
        ),
        ("source_hhi", round(_hhi(source_counts), 6), "index"),
    )
    for name, value, unit in source_values:
        add("imbalance", name, value, group_field="source", metric_unit=unit)

    for field in config["metadata"]["optional_descriptive_fields"]:
        coverage = metadata.groupby("category", sort=True)[field].apply(
            lambda series: 100.0 * series.map(_usable).sum() / len(series)
        )
        add(
            "imbalance",
            "category_coverage_range_pct",
            round(float(coverage.max() - coverage.min()), 2),
            group_field="metadata_field",
            group_value=field,
            metric_unit="percentage_points",
        )

    for note in config["bias_notes"]:
        add(
            "bias_and_limitations",
            "documented_bias_or_limitation",
            group_field=str(note["bias_category"]),
            group_value=str(note["bias_id"]),
            status="documented_limitation",
            details=f"{note['statement']} Evidence: {note['evidence_basis']}",
        )

    frame = pd.DataFrame(records, columns=DATASET_AUDIT_COLUMNS)
    result = validate_dataframe(frame, DATASET_AUDIT_SCHEMA, allow_extra_columns=False)
    if not result.passed:
        raise ValueError(f"Dataset audit violates schema: {result.to_dict()}")
    return frame


def select_preview_rows(
    artworks: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select deterministic accepted preview rows using configured rules."""
    preview = config["preview"]
    group_by = str(preview["group_by"])
    sort_by = [str(value) for value in preview["sort_by"]]
    items_per_group = int(preview["items_per_group"])
    accepted = artworks.loc[artworks["acceptance_status"] == "accepted"]
    return (
        accepted.sort_values(sort_by, kind="stable")
        .groupby(group_by, sort=True, group_keys=False)
        .head(items_per_group)
        .reset_index(drop=True)
    )


def write_dataframe_atomic(dataframe: pd.DataFrame, path: str | Path) -> Path:
    """Write a CSV atomically to an explicit caller-owned path."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        dataframe.to_csv(temporary, index=False)
        os.replace(temporary, output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return output_path
