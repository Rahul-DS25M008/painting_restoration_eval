"""Damaged-image creation utilities for painting restoration evaluation."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from PIL import Image


GENERATOR_NAME = "canonical_damage_generator"
GENERATOR_VERSION = "2.0.0"

DEFAULT_DAMAGE_FILL_COLOR: tuple[int, int, int] = (255, 255, 255)
DEFAULT_DAMAGE_FILL_STRATEGY = "white_fill"

SUPPORTED_DAMAGE_FILL_STRATEGIES: tuple[str, ...] = (
    "white_fill",
)


def compute_file_sha256(
    path: Path,
    chunk_size: int = 1024 * 1024,
) -> str:
    """Compute the SHA-256 checksum of a file.

    Parameters
    ----------
    path:
        File whose checksum should be calculated.
    chunk_size:
        Number of bytes read per iteration.

    Returns
    -------
    str
        Lowercase hexadecimal SHA-256 digest.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Cannot compute SHA-256 because the file does not exist: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Cannot compute SHA-256 because the path is not a file: {path}"
        )

    digest = hashlib.sha256()

    with path.open("rb") as file_handle:
        while chunk := file_handle.read(chunk_size):
            digest.update(chunk)

    return digest.hexdigest()


def _normalise_fill_color(
    fill_color: Iterable[int],
) -> tuple[int, int, int]:
    """Validate and normalise an RGB fill colour."""
    values = tuple(int(value) for value in fill_color)

    if len(values) != 3:
        raise ValueError(
            "Damage fill colour must contain exactly three RGB values."
        )

    if any(value < 0 or value > 255 for value in values):
        raise ValueError(
            "Damage fill colour values must be integers between 0 and 255."
        )

    return values


def _resolve_existing_path(
    path_value: str | Path,
    project_root: Path | None = None,
) -> Path:
    """Resolve an existing absolute or project-relative path."""
    path = Path(path_value)

    if path.is_absolute():
        return path

    if path.exists():
        return path

    if project_root is not None:
        candidate = Path(project_root) / path

        if candidate.exists():
            return candidate

    return path


def _safe_relative_string(
    path: Path,
    project_root: Path | None = None,
) -> str:
    """Return a project-relative path where possible."""
    path = Path(path)

    if project_root is not None:
        try:
            return str(path.resolve().relative_to(Path(project_root).resolve()))
        except ValueError:
            pass

    return str(path)


def apply_mask_damage(
    clean_image: Image.Image,
    mask: Image.Image,
    fill_color: tuple[int, int, int] = DEFAULT_DAMAGE_FILL_COLOR,
) -> Image.Image:
    """Apply a binary damage mask to a clean RGB image.

    Pixels where the mask is non-zero are replaced with ``fill_color``.
    Pixels outside the mask are preserved exactly.

    Mask convention
    ---------------
    - ``0``: preserved/original region
    - ``255``: damaged/inpainting region
    """
    validated_fill_color = _normalise_fill_color(fill_color)

    clean_rgb = clean_image.convert("RGB")
    mask_l = mask.convert("L")

    if clean_rgb.size != mask_l.size:
        raise ValueError(
            "Clean image and mask dimensions differ: "
            f"clean={clean_rgb.size}, mask={mask_l.size}"
        )

    clean_array = np.asarray(clean_rgb, dtype=np.uint8).copy()
    mask_array = np.asarray(mask_l, dtype=np.uint8) > 0

    clean_array[mask_array] = np.asarray(
        validated_fill_color,
        dtype=np.uint8,
    )

    return Image.fromarray(
        clean_array,
        mode="RGB",
    )


def create_damaged_images_for_dataset(
    processed_metadata: pd.DataFrame,
    mask_metadata: pd.DataFrame,
    clean_dir: Path,
    damaged_dir: Path,
    fill_color: tuple[int, int, int] = DEFAULT_DAMAGE_FILL_COLOR,
    fill_strategy: str = DEFAULT_DAMAGE_FILL_STRATEGY,
    project_root: Path | None = None,
    overwrite: bool = True,
    compute_checksums: bool = True,
) -> pd.DataFrame:
    """Create one damaged image for every canonical mask case.

    Parameters
    ----------
    processed_metadata:
        Canonical processed-image metadata.
    mask_metadata:
        Canonical mask metadata produced by Notebook 03.
    clean_dir:
        Directory containing processed clean images.
    damaged_dir:
        Output directory for damaged images.
    fill_color:
        RGB colour inserted in masked pixels.
    fill_strategy:
        Human-readable name of the damage-fill strategy.
    project_root:
        Optional project root used for resolving and recording paths.
    overwrite:
        Whether existing damaged files should be regenerated.
    compute_checksums:
        Whether SHA-256 checksums should be recorded.

    Returns
    -------
    pandas.DataFrame
        One metadata row per mask case.
    """
    clean_dir = Path(clean_dir)
    damaged_dir = Path(damaged_dir)
    project_root = (
        Path(project_root)
        if project_root is not None
        else None
    )

    damaged_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    validated_fill_color = _normalise_fill_color(fill_color)

    if fill_strategy not in SUPPORTED_DAMAGE_FILL_STRATEGIES:
        raise ValueError(
            f"Unsupported damage fill strategy: {fill_strategy}. "
            f"Supported strategies: {SUPPORTED_DAMAGE_FILL_STRATEGIES}"
        )

    required_processed_columns = [
        "painting_id",
        "processed_filename",
    ]

    required_mask_columns = [
        "case_id",
        "painting_id",
        "mask_id",
        "mask_type",
        "mask_filename",
        "mask_path",
        "actual_mask_area_pixels",
        "actual_mask_area_percentage_content",
        "actual_mask_area_percentage_full",
    ]

    missing_processed_columns = [
        column
        for column in required_processed_columns
        if column not in processed_metadata.columns
    ]

    missing_mask_columns = [
        column
        for column in required_mask_columns
        if column not in mask_metadata.columns
    ]

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

    if processed_metadata["painting_id"].duplicated().any():
        duplicate_ids = (
            processed_metadata.loc[
                processed_metadata["painting_id"].duplicated(
                    keep=False
                ),
                "painting_id",
            ]
            .astype(str)
            .unique()
            .tolist()
        )

        raise ValueError(
            "Processed metadata contains duplicate painting IDs: "
            f"{duplicate_ids[:10]}"
        )

    if mask_metadata["case_id"].duplicated().any():
        duplicate_case_ids = (
            mask_metadata.loc[
                mask_metadata["case_id"].duplicated(
                    keep=False
                ),
                "case_id",
            ]
            .astype(str)
            .unique()
            .tolist()
        )

        raise ValueError(
            "Mask metadata contains duplicate case IDs: "
            f"{duplicate_case_ids[:10]}"
        )

    processed_lookup = (
        processed_metadata
        .set_index("painting_id")
        .to_dict(orient="index")
    )

    generated_at_utc = datetime.now(
        timezone.utc
    ).isoformat()

    records: list[dict[str, Any]] = []

    sorted_mask_metadata = mask_metadata.sort_values(
        ["painting_id", "mask_type", "case_id"],
        kind="stable",
    )

    for _, mask_row in sorted_mask_metadata.iterrows():
        painting_id = mask_row["painting_id"]
        case_id = str(mask_row["case_id"])
        mask_id = mask_row["mask_id"]
        mask_type = str(mask_row["mask_type"])

        if painting_id not in processed_lookup:
            raise ValueError(
                "Painting ID from mask metadata was not found in "
                f"processed metadata: {painting_id}"
            )

        processed_row = processed_lookup[painting_id]

        clean_filename = str(
            processed_row["processed_filename"]
        )

        if (
            "processed_path" in processed_row
            and pd.notna(processed_row["processed_path"])
            and str(processed_row["processed_path"]).strip()
        ):
            clean_path = _resolve_existing_path(
                processed_row["processed_path"],
                project_root=project_root,
            )
        else:
            clean_path = clean_dir / clean_filename

        mask_path = _resolve_existing_path(
            mask_row["mask_path"],
            project_root=project_root,
        )

        damaged_filename = f"{case_id}_damaged.png"
        damaged_path = damaged_dir / damaged_filename

        status = "ok"
        issue = ""
        generation_action = "generated"

        width: int | None = None
        height: int | None = None
        mode: str | None = None
        format_name: str | None = None
        damaged_file_size_bytes: int | None = None

        clean_sha256: str | None = None
        mask_sha256: str | None = None
        damaged_sha256: str | None = None

        try:
            if not clean_path.exists():
                raise FileNotFoundError(
                    f"Clean image does not exist: {clean_path}"
                )

            if not mask_path.exists():
                raise FileNotFoundError(
                    f"Mask image does not exist: {mask_path}"
                )

            if damaged_path.exists() and not overwrite:
                generation_action = "reused_existing"
            else:
                with Image.open(clean_path) as clean_image:
                    clean_rgb = clean_image.convert("RGB")
                    clean_rgb.load()

                with Image.open(mask_path) as mask_image:
                    mask_l = mask_image.convert("L")
                    mask_l.load()

                damaged_image = apply_mask_damage(
                    clean_image=clean_rgb,
                    mask=mask_l,
                    fill_color=validated_fill_color,
                )

                damaged_image.save(
                    damaged_path,
                    format="PNG",
                )

            with Image.open(damaged_path) as saved_image:
                saved_image.load()
                width, height = saved_image.size
                mode = saved_image.mode
                format_name = saved_image.format

            damaged_file_size_bytes = (
                damaged_path.stat().st_size
            )

            if compute_checksums:
                clean_sha256 = compute_file_sha256(
                    clean_path
                )
                mask_sha256 = compute_file_sha256(
                    mask_path
                )
                damaged_sha256 = compute_file_sha256(
                    damaged_path
                )

        except Exception as exception:
            status = "error"
            issue = (
                f"{type(exception).__name__}: "
                f"{exception}"
            )

        records.append(
            {
                "case_id": case_id,
                "painting_id": painting_id,
                "mask_id": mask_id,
                "mask_type": mask_type,
                "generator_name": GENERATOR_NAME,
                "generator_version": GENERATOR_VERSION,
                "generated_at_utc": generated_at_utc,
                "generation_action": generation_action,
                "clean_filename": clean_filename,
                "clean_path": _safe_relative_string(
                    clean_path,
                    project_root=project_root,
                ),
                "mask_filename": str(
                    mask_row["mask_filename"]
                ),
                "mask_path": _safe_relative_string(
                    mask_path,
                    project_root=project_root,
                ),
                "damaged_filename": damaged_filename,
                "damaged_path": _safe_relative_string(
                    damaged_path,
                    project_root=project_root,
                ),
                "damage_fill_strategy": fill_strategy,
                "damage_fill_r": validated_fill_color[0],
                "damage_fill_g": validated_fill_color[1],
                "damage_fill_b": validated_fill_color[2],
                "damaged_area_pixels": int(
                    mask_row[
                        "actual_mask_area_pixels"
                    ]
                ),
                "damaged_area_percentage_content": float(
                    mask_row[
                        "actual_mask_area_percentage_content"
                    ]
                ),
                "damaged_area_percentage_full": float(
                    mask_row[
                        "actual_mask_area_percentage_full"
                    ]
                ),
                "width": width,
                "height": height,
                "mode": mode,
                "format": format_name,
                "damaged_file_size_bytes": (
                    damaged_file_size_bytes
                ),
                "clean_sha256": clean_sha256,
                "mask_sha256": mask_sha256,
                "damaged_sha256": damaged_sha256,
                "status": status,
                "issue": issue,
            }
        )

    return pd.DataFrame(records)


def validate_damaged_images(
    damaged_metadata: pd.DataFrame,
    target_size: int = 768,
    project_root: Path | None = None,
    verify_checksums: bool = True,
) -> pd.DataFrame:
    """Validate saved damaged-image files after reloading them.

    Checks include:

    - file existence;
    - file readability;
    - PNG format;
    - RGB mode;
    - expected dimensions;
    - metadata filename consistency;
    - metadata size consistency;
    - optional SHA-256 checksum consistency.
    """
    project_root = (
        Path(project_root)
        if project_root is not None
        else None
    )

    required_columns = [
        "case_id",
        "painting_id",
        "mask_type",
        "damaged_filename",
        "damaged_path",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in damaged_metadata.columns
    ]

    if missing_columns:
        raise ValueError(
            "Damaged metadata is missing required columns: "
            f"{missing_columns}"
        )

    validation_rows: list[dict[str, Any]] = []

    for _, row in damaged_metadata.iterrows():
        damaged_path = _resolve_existing_path(
            row["damaged_path"],
            project_root=project_root,
        )

        issues: list[str] = []

        file_exists = damaged_path.exists()
        readable = False

        width: int | None = None
        height: int | None = None
        mode: str | None = None
        format_name: str | None = None
        file_size_bytes: int | None = None
        calculated_sha256: str | None = None

        filename_matches_metadata = (
            damaged_path.name
            == str(row["damaged_filename"])
        )

        if not filename_matches_metadata:
            issues.append(
                "damaged_filename_mismatch"
            )

        if not file_exists:
            issues.append(
                "missing_damaged_file"
            )
        else:
            try:
                file_size_bytes = (
                    damaged_path.stat().st_size
                )

                with Image.open(damaged_path) as image:
                    image.load()
                    readable = True
                    width, height = image.size
                    mode = image.mode
                    format_name = image.format

                if width != target_size or height != target_size:
                    issues.append(
                        "wrong_damaged_size"
                    )

                if mode != "RGB":
                    issues.append(
                        "wrong_color_mode"
                    )

                if format_name != "PNG":
                    issues.append(
                        "wrong_image_format"
                    )

                if (
                    "damaged_file_size_bytes"
                    in damaged_metadata.columns
                    and pd.notna(
                        row.get(
                            "damaged_file_size_bytes"
                        )
                    )
                    and int(
                        row[
                            "damaged_file_size_bytes"
                        ]
                    )
                    != file_size_bytes
                ):
                    issues.append(
                        "damaged_file_size_mismatch"
                    )

                if verify_checksums:
                    calculated_sha256 = (
                        compute_file_sha256(
                            damaged_path
                        )
                    )

                    expected_checksum = row.get(
                        "damaged_sha256"
                    )

                    if (
                        pd.notna(expected_checksum)
                        and str(expected_checksum).strip()
                        and calculated_sha256
                        != str(expected_checksum)
                    ):
                        issues.append(
                            "damaged_sha256_mismatch"
                        )

            except Exception as exception:
                issues.append(
                    "unreadable_damaged_file: "
                    f"{type(exception).__name__}: "
                    f"{exception}"
                )

        validation_rows.append(
            {
                "case_id": row["case_id"],
                "painting_id": row["painting_id"],
                "mask_type": row["mask_type"],
                "damaged_path": str(
                    damaged_path
                ),
                "file_exists": file_exists,
                "readable": readable,
                "width": width,
                "height": height,
                "mode": mode,
                "format": format_name,
                "file_size_bytes": file_size_bytes,
                "filename_matches_metadata": (
                    filename_matches_metadata
                ),
                "calculated_damaged_sha256": (
                    calculated_sha256
                ),
                "issue_count": len(issues),
                "validation_passed": (
                    len(issues) == 0
                ),
                "issue": "; ".join(issues),
            }
        )

    return pd.DataFrame(validation_rows)


def validate_damage_application(
    damaged_metadata: pd.DataFrame,
    target_size: int = 768,
    project_root: Path | None = None,
    verify_source_checksums: bool = True,
) -> pd.DataFrame:
    """Validate exact pixel-level damage application.

    Checks include:

    - damaged and clean image dimensions match;
    - mask dimensions match the images;
    - no pixels outside the mask changed;
    - all mask pixels equal the configured fill colour;
    - the loaded mask-pixel count matches metadata;
    - the observed changed-pixel count is recorded;
    - zero-control images remain identical to clean images;
    - non-zero masks contain damaged pixels;
    - optional clean and mask checksum consistency.

    Notes
    -----
    ``changed_pixel_count`` may be smaller than ``total_mask_pixels`` when a
    clean source pixel already equals the configured fill colour. This is not
    an application error. The stricter and correct checks are that every
    masked output pixel equals the fill colour and every unmasked pixel remains
    unchanged.
    """
    project_root = (
        Path(project_root)
        if project_root is not None
        else None
    )

    required_columns = [
        "case_id",
        "painting_id",
        "mask_type",
        "clean_path",
        "mask_path",
        "damaged_path",
        "damage_fill_r",
        "damage_fill_g",
        "damage_fill_b",
        "damaged_area_pixels",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in damaged_metadata.columns
    ]

    if missing_columns:
        raise ValueError(
            "Damaged metadata is missing required columns: "
            f"{missing_columns}"
        )

    validation_rows: list[dict[str, Any]] = []

    for _, row in damaged_metadata.iterrows():
        clean_path = _resolve_existing_path(
            row["clean_path"],
            project_root=project_root,
        )

        mask_path = _resolve_existing_path(
            row["mask_path"],
            project_root=project_root,
        )

        damaged_path = _resolve_existing_path(
            row["damaged_path"],
            project_root=project_root,
        )

        issues: list[str] = []

        outside_mask_changed_pixels: int | None = None
        inside_mask_not_fill_pixels: int | None = None
        total_mask_pixels: int | None = None
        metadata_mask_pixels: int | None = None
        mask_pixel_count_difference: int | None = None

        changed_pixel_count: int | None = None
        unchanged_mask_pixel_count: int | None = None
        expected_changeable_mask_pixels: int | None = None
        changed_pixel_count_difference: int | None = None

        clean_equals_damaged: bool | None = None
        fill_application_valid: bool | None = None
        outside_preservation_valid: bool | None = None

        calculated_clean_sha256: str | None = None
        calculated_mask_sha256: str | None = None

        fill_color = np.asarray(
            [
                int(row["damage_fill_r"]),
                int(row["damage_fill_g"]),
                int(row["damage_fill_b"]),
            ],
            dtype=np.uint8,
        )

        try:
            with Image.open(clean_path) as clean_image:
                clean_array = np.asarray(
                    clean_image.convert("RGB"),
                    dtype=np.uint8,
                )

            with Image.open(mask_path) as mask_image:
                raw_mask_array = np.asarray(
                    mask_image.convert("L"),
                    dtype=np.uint8,
                )
                mask_array = raw_mask_array > 0

            with Image.open(damaged_path) as damaged_image:
                damaged_array = np.asarray(
                    damaged_image.convert("RGB"),
                    dtype=np.uint8,
                )

            if clean_array.shape != damaged_array.shape:
                issues.append(
                    "clean_and_damaged_shape_mismatch"
                )

            if mask_array.shape != clean_array.shape[:2]:
                issues.append(
                    "mask_and_image_shape_mismatch"
                )

            if clean_array.shape[:2] != (
                target_size,
                target_size,
            ):
                issues.append(
                    "wrong_clean_shape"
                )

            if not issues:
                outside_mask = ~mask_array

                pixel_difference_map = np.any(
                    clean_array != damaged_array,
                    axis=2,
                )

                outside_mask_changed_pixels = int(
                    pixel_difference_map[
                        outside_mask
                    ].sum()
                )

                changed_pixel_count = int(
                    pixel_difference_map.sum()
                )

                total_mask_pixels = int(
                    mask_array.sum()
                )

                metadata_mask_pixels = int(
                    row["damaged_area_pixels"]
                )

                mask_pixel_count_difference = (
                    total_mask_pixels
                    - metadata_mask_pixels
                )

                if total_mask_pixels > 0:
                    inside_mask_not_fill_pixels = int(
                        np.any(
                            damaged_array[
                                mask_array
                            ]
                            != fill_color,
                            axis=1,
                        ).sum()
                    )

                    clean_inside_already_fill = np.all(
                        clean_array[mask_array]
                        == fill_color,
                        axis=1,
                    )

                    unchanged_mask_pixel_count = int(
                        clean_inside_already_fill.sum()
                    )

                    expected_changeable_mask_pixels = int(
                        total_mask_pixels
                        - unchanged_mask_pixel_count
                    )

                else:
                    inside_mask_not_fill_pixels = 0
                    unchanged_mask_pixel_count = 0
                    expected_changeable_mask_pixels = 0

                changed_pixel_count_difference = int(
                    changed_pixel_count
                    - expected_changeable_mask_pixels
                )

                clean_equals_damaged = bool(
                    np.array_equal(
                        clean_array,
                        damaged_array,
                    )
                )

                outside_preservation_valid = (
                    outside_mask_changed_pixels == 0
                )

                fill_application_valid = (
                    inside_mask_not_fill_pixels == 0
                )

                if outside_mask_changed_pixels != 0:
                    issues.append(
                        "pixels_changed_outside_mask"
                    )

                if inside_mask_not_fill_pixels != 0:
                    issues.append(
                        "mask_pixels_not_set_to_fill_color"
                    )

                if mask_pixel_count_difference != 0:
                    issues.append(
                        "mask_pixel_count_metadata_mismatch"
                    )

                if changed_pixel_count_difference != 0:
                    issues.append(
                        "changed_pixel_count_mismatch"
                    )

                if (
                    row["mask_type"] == "zero_control"
                    and not clean_equals_damaged
                ):
                    issues.append(
                        "zero_control_changed_image"
                    )

                if (
                    row["mask_type"] != "zero_control"
                    and total_mask_pixels <= 0
                ):
                    issues.append(
                        "nonzero_mask_has_no_pixels"
                    )

            if verify_source_checksums:
                calculated_clean_sha256 = (
                    compute_file_sha256(
                        clean_path
                    )
                )

                calculated_mask_sha256 = (
                    compute_file_sha256(
                        mask_path
                    )
                )

                expected_clean_checksum = row.get(
                    "clean_sha256"
                )

                expected_mask_checksum = row.get(
                    "mask_sha256"
                )

                if (
                    pd.notna(expected_clean_checksum)
                    and str(expected_clean_checksum).strip()
                    and calculated_clean_sha256
                    != str(expected_clean_checksum)
                ):
                    issues.append(
                        "clean_sha256_mismatch"
                    )

                if (
                    pd.notna(expected_mask_checksum)
                    and str(expected_mask_checksum).strip()
                    and calculated_mask_sha256
                    != str(expected_mask_checksum)
                ):
                    issues.append(
                        "mask_sha256_mismatch"
                    )

        except Exception as exception:
            issues.append(
                f"{type(exception).__name__}: "
                f"{exception}"
            )

        validation_rows.append(
            {
                "case_id": row["case_id"],
                "painting_id": row["painting_id"],
                "mask_type": row["mask_type"],
                "outside_mask_changed_pixels": (
                    outside_mask_changed_pixels
                ),
                "inside_mask_not_fill_pixels": (
                    inside_mask_not_fill_pixels
                ),
                "total_mask_pixels": total_mask_pixels,
                "metadata_mask_pixels": (
                    metadata_mask_pixels
                ),
                "mask_pixel_count_difference": (
                    mask_pixel_count_difference
                ),
                "changed_pixel_count": (
                    changed_pixel_count
                ),
                "unchanged_mask_pixel_count": (
                    unchanged_mask_pixel_count
                ),
                "expected_changeable_mask_pixels": (
                    expected_changeable_mask_pixels
                ),
                "changed_pixel_count_difference": (
                    changed_pixel_count_difference
                ),
                "clean_equals_damaged": (
                    clean_equals_damaged
                ),
                "outside_preservation_valid": (
                    outside_preservation_valid
                ),
                "fill_application_valid": (
                    fill_application_valid
                ),
                "calculated_clean_sha256": (
                    calculated_clean_sha256
                ),
                "calculated_mask_sha256": (
                    calculated_mask_sha256
                ),
                "issue_count": len(issues),
                "validation_passed": (
                    len(issues) == 0
                ),
                "issue": "; ".join(issues),
            }
        )

    return pd.DataFrame(validation_rows)


def audit_damaged_inventory(
    damaged_metadata: pd.DataFrame,
    damaged_dir: Path,
    expected_case_ids: Iterable[str] | None = None,
    filename_pattern: str = "*_damaged.png",
    project_root: Path | None = None,
) -> dict[str, pd.DataFrame]:
    """Audit damaged-image metadata against files on disk.

    The audit detects:

    - duplicate case IDs;
    - duplicate damaged filenames;
    - duplicate damaged paths;
    - missing expected case IDs;
    - unexpected metadata case IDs;
    - metadata rows whose files are missing;
    - orphan PNG files not represented in metadata;
    - filename/path inconsistencies.
    """
    damaged_dir = Path(damaged_dir)
    project_root = (
        Path(project_root)
        if project_root is not None
        else None
    )

    required_columns = [
        "case_id",
        "damaged_filename",
        "damaged_path",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in damaged_metadata.columns
    ]

    if missing_columns:
        raise ValueError(
            "Damaged metadata is missing required audit columns: "
            f"{missing_columns}"
        )

    metadata = damaged_metadata.copy()

    metadata["case_id"] = (
        metadata["case_id"].astype(str)
    )

    metadata["damaged_filename"] = (
        metadata["damaged_filename"].astype(str)
    )

    metadata["resolved_damaged_path"] = (
        metadata["damaged_path"]
        .map(
            lambda value: str(
                _resolve_existing_path(
                    value,
                    project_root=project_root,
                ).resolve()
            )
        )
    )

    duplicate_case_rows = metadata.loc[
        metadata["case_id"].duplicated(
            keep=False
        )
    ].copy()

    duplicate_filename_rows = metadata.loc[
        metadata["damaged_filename"].duplicated(
            keep=False
        )
    ].copy()

    duplicate_path_rows = metadata.loc[
        metadata["resolved_damaged_path"].duplicated(
            keep=False
        )
    ].copy()

    missing_file_rows = metadata.loc[
        ~metadata["resolved_damaged_path"]
        .map(lambda value: Path(value).exists())
    ].copy()

    filename_mismatch_rows = metadata.loc[
        metadata.apply(
            lambda row: (
                Path(
                    row[
                        "resolved_damaged_path"
                    ]
                ).name
                != row["damaged_filename"]
            ),
            axis=1,
        )
    ].copy()

    metadata_case_ids = set(
        metadata["case_id"]
    )

    if expected_case_ids is None:
        expected_case_id_set = metadata_case_ids
    else:
        expected_case_id_set = {
            str(case_id)
            for case_id in expected_case_ids
        }

    missing_case_ids = sorted(
        expected_case_id_set
        - metadata_case_ids
    )

    unexpected_case_ids = sorted(
        metadata_case_ids
        - expected_case_id_set
    )

    expected_resolved_paths = {
        Path(path_value).resolve()
        for path_value in metadata[
            "resolved_damaged_path"
        ]
    }

    disk_paths = {
        path.resolve()
        for path in damaged_dir.glob(
            filename_pattern
        )
        if path.is_file()
    }

    orphan_paths = sorted(
        disk_paths
        - expected_resolved_paths,
        key=lambda path: str(path),
    )

    orphan_file_rows = pd.DataFrame(
        [
            {
                "damaged_filename": path.name,
                "damaged_path": str(path),
            }
            for path in orphan_paths
        ],
        columns=[
            "damaged_filename",
            "damaged_path",
        ],
    )

    missing_case_rows = pd.DataFrame(
        {
            "case_id": missing_case_ids,
        }
    )

    unexpected_case_rows = pd.DataFrame(
        {
            "case_id": unexpected_case_ids,
        }
    )

    audit_summary_rows = [
        {
            "check": "duplicate_case_ids",
            "issue_count": len(
                duplicate_case_rows
            ),
            "passed": (
                len(duplicate_case_rows) == 0
            ),
        },
        {
            "check": "duplicate_damaged_filenames",
            "issue_count": len(
                duplicate_filename_rows
            ),
            "passed": (
                len(duplicate_filename_rows) == 0
            ),
        },
        {
            "check": "duplicate_damaged_paths",
            "issue_count": len(
                duplicate_path_rows
            ),
            "passed": (
                len(duplicate_path_rows) == 0
            ),
        },
        {
            "check": "missing_expected_case_ids",
            "issue_count": len(
                missing_case_rows
            ),
            "passed": (
                len(missing_case_rows) == 0
            ),
        },
        {
            "check": "unexpected_metadata_case_ids",
            "issue_count": len(
                unexpected_case_rows
            ),
            "passed": (
                len(unexpected_case_rows) == 0
            ),
        },
        {
            "check": "missing_damaged_files",
            "issue_count": len(
                missing_file_rows
            ),
            "passed": (
                len(missing_file_rows) == 0
            ),
        },
        {
            "check": "orphan_damaged_files",
            "issue_count": len(
                orphan_file_rows
            ),
            "passed": (
                len(orphan_file_rows) == 0
            ),
        },
        {
            "check": "filename_path_consistency",
            "issue_count": len(
                filename_mismatch_rows
            ),
            "passed": (
                len(filename_mismatch_rows) == 0
            ),
        },
    ]

    summary_df = pd.DataFrame(
        audit_summary_rows
    )

    return {
        "summary": summary_df,
        "duplicate_case_rows": (
            duplicate_case_rows
        ),
        "duplicate_filename_rows": (
            duplicate_filename_rows
        ),
        "duplicate_path_rows": (
            duplicate_path_rows
        ),
        "missing_case_rows": (
            missing_case_rows
        ),
        "unexpected_case_rows": (
            unexpected_case_rows
        ),
        "missing_file_rows": (
            missing_file_rows
        ),
        "orphan_file_rows": (
            orphan_file_rows
        ),
        "filename_mismatch_rows": (
            filename_mismatch_rows
        ),
    }