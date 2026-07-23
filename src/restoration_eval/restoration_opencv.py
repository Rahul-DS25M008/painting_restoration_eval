"""OpenCV Telea restoration pipeline for painting restoration experiments."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any

import cv2
import numpy as np
import pandas as pd
from PIL import Image


DEFAULT_OPENCV_MODEL_NAME = "opencv_telea"
DEFAULT_TELEA_RADIUS = 3
RESTORATION_GENERATOR_NAME = "restoration_eval.restoration_opencv"
RESTORATION_GENERATOR_VERSION = "2.0.0"

_REQUIRED_INPUT_COLUMNS = {
    "dataset_name",
    "case_id",
    "painting_id",
    "clean_path",
    "damaged_path",
    "mask_path",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalise_path(path_value: Any, project_root: Path | None) -> Path:
    path = Path(str(path_value))
    if path.is_absolute() or project_root is None:
        return path
    return (project_root / path).resolve()


def _relative_or_absolute(path: Path, project_root: Path | None) -> str:
    path = path.resolve()
    if project_root is None:
        return str(path)

    project_root = project_root.resolve()
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def calculate_file_sha256(
    file_path: Path,
    chunk_size: int = 1024 * 1024,
) -> str:
    """Return the SHA-256 checksum of a file."""
    digest = sha256()

    with Path(file_path).open("rb") as file_handle:
        while True:
            chunk = file_handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def restore_with_opencv_telea(
    damaged_image_path: Path,
    mask_path: Path,
    radius: int = DEFAULT_TELEA_RADIUS,
) -> Image.Image:
    """Restore one damaged image with OpenCV Telea inpainting."""
    if radius <= 0:
        raise ValueError("Telea inpainting radius must be greater than zero.")

    damaged_bgr = cv2.imread(
        str(damaged_image_path),
        cv2.IMREAD_COLOR,
    )
    mask_gray = cv2.imread(
        str(mask_path),
        cv2.IMREAD_GRAYSCALE,
    )

    if damaged_bgr is None:
        raise FileNotFoundError(
            f"Could not read damaged image: {damaged_image_path}"
        )

    if mask_gray is None:
        raise FileNotFoundError(
            f"Could not read mask: {mask_path}"
        )

    if damaged_bgr.shape[:2] != mask_gray.shape[:2]:
        raise ValueError(
            "Damaged image and mask dimensions differ: "
            f"image={damaged_bgr.shape[:2]}, mask={mask_gray.shape[:2]}"
        )

    _, mask_binary = cv2.threshold(
        mask_gray,
        127,
        255,
        cv2.THRESH_BINARY,
    )

    restored_bgr = cv2.inpaint(
        damaged_bgr,
        mask_binary,
        inpaintRadius=float(radius),
        flags=cv2.INPAINT_TELEA,
    )

    restored_rgb = cv2.cvtColor(
        restored_bgr,
        cv2.COLOR_BGR2RGB,
    )
    return Image.fromarray(restored_rgb)


def validate_restoration_input_manifest(
    restoration_input: pd.DataFrame,
) -> None:
    """Validate the normalized manifest consumed by the restoration pipeline."""
    missing_columns = sorted(
        _REQUIRED_INPUT_COLUMNS
        - set(restoration_input.columns)
    )
    if missing_columns:
        raise ValueError(
            "Restoration input manifest is missing required columns: "
            f"{missing_columns}"
        )

    if restoration_input.empty:
        raise ValueError("Restoration input manifest is empty.")

    if restoration_input["case_id"].isna().any():
        raise ValueError("Restoration input manifest contains null case IDs.")

    duplicate_mask = restoration_input["case_id"].astype(str).duplicated(
        keep=False
    )
    if duplicate_mask.any():
        duplicates = (
            restoration_input.loc[duplicate_mask, "case_id"]
            .astype(str)
            .tolist()
        )
        raise ValueError(
            "Restoration input manifest contains duplicate case IDs: "
            f"{duplicates[:20]}"
        )

    null_path_columns = [
        column
        for column in ("clean_path", "damaged_path", "mask_path")
        if restoration_input[column].isna().any()
    ]
    if null_path_columns:
        raise ValueError(
            "Restoration input manifest contains null paths in: "
            f"{null_path_columns}"
        )


def create_opencv_restoration_dataset(
    restoration_input: pd.DataFrame,
    restored_root_dir: Path,
    project_root: Path | None = None,
    model_name: str = DEFAULT_OPENCV_MODEL_NAME,
    radius: int = DEFAULT_TELEA_RADIUS,
    overwrite: bool = False,
    compute_checksums: bool = True,
) -> pd.DataFrame:
    """Restore all rows in a normalized multi-dataset input manifest."""
    validate_restoration_input_manifest(restoration_input)

    restored_root_dir = Path(restored_root_dir)
    restored_root_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []

    ordered_input = restoration_input.copy()
    ordered_input["_case_sort"] = ordered_input["case_id"].astype(str)
    ordered_input = (
        ordered_input
        .sort_values(["dataset_name", "_case_sort"])
        .drop(columns="_case_sort")
        .reset_index(drop=True)
    )

    for _, row in ordered_input.iterrows():
        source_record = row.to_dict()

        dataset_name = str(row["dataset_name"])
        source_case_id = str(row["case_id"])
        restoration_case_id = (
            f"{model_name}__{dataset_name}__{source_case_id}"
        )

        dataset_output_dir = restored_root_dir / dataset_name
        dataset_output_dir.mkdir(parents=True, exist_ok=True)

        restored_filename = (
            f"{source_case_id}_restored_{model_name}.png"
        )
        restored_path = dataset_output_dir / restored_filename

        damaged_path = _normalise_path(
            row["damaged_path"],
            project_root,
        )
        mask_path = _normalise_path(
            row["mask_path"],
            project_root,
        )

        status = "ok"
        issue = ""
        restored_checksum = ""
        output_written = False
        started_at_utc = _utc_now_iso()
        timer_start = perf_counter()

        try:
            if restored_path.exists() and not overwrite:
                output_written = False
            else:
                restored_image = restore_with_opencv_telea(
                    damaged_image_path=damaged_path,
                    mask_path=mask_path,
                    radius=radius,
                )
                restored_image.save(restored_path, format="PNG")
                output_written = True

            if not restored_path.exists():
                raise FileNotFoundError(
                    f"Restoration output was not created: {restored_path}"
                )

            if compute_checksums:
                restored_checksum = calculate_file_sha256(restored_path)

        except Exception as exc:
            status = "error"
            issue = f"{type(exc).__name__}: {exc}"

        runtime_seconds = perf_counter() - timer_start
        completed_at_utc = _utc_now_iso()

        source_record.update(
            {
                "source_case_id": source_case_id,
                "restoration_case_id": restoration_case_id,
                "model_name": model_name,
                "algorithm": "cv2.INPAINT_TELEA",
                "inpaint_radius": int(radius),
                "opencv_version": cv2.__version__,
                "restoration_generator_name": RESTORATION_GENERATOR_NAME,
                "restoration_generator_version": RESTORATION_GENERATOR_VERSION,
                "restored_filename": restored_filename,
                "restored_path": _relative_or_absolute(
                    restored_path,
                    project_root,
                ),
                "restored_sha256": restored_checksum,
                "runtime_seconds": float(runtime_seconds),
                "started_at_utc": started_at_utc,
                "completed_at_utc": completed_at_utc,
                "output_written": bool(output_written),
                "status": status,
                "issue": issue,
            }
        )
        records.append(source_record)

    return pd.DataFrame(records)


def validate_restored_images(
    restored_metadata: pd.DataFrame,
    project_root: Path | None = None,
    target_size: int = 768,
) -> pd.DataFrame:
    """Validate restoration files, dimensions, mode, and checksums."""
    required_columns = {
        "restoration_case_id",
        "dataset_name",
        "case_id",
        "painting_id",
        "restored_path",
        "status",
    }
    missing_columns = sorted(required_columns - set(restored_metadata.columns))
    if missing_columns:
        raise ValueError(
            "Restored metadata is missing required columns: "
            f"{missing_columns}"
        )

    validation_rows: list[dict[str, Any]] = []

    for _, row in restored_metadata.iterrows():
        restored_path = _normalise_path(
            row["restored_path"],
            project_root,
        )

        file_exists = restored_path.is_file()
        readable = False
        width = None
        height = None
        mode = None
        checksum_matches = None
        issue_parts: list[str] = []

        if str(row["status"]) != "ok":
            issue_parts.append("generation_status_not_ok")

        if not file_exists:
            issue_parts.append("missing_restored_file")
        else:
            try:
                with Image.open(restored_path) as image:
                    image.load()
                    readable = True
                    width, height = image.size
                    mode = image.mode

                if (width, height) != (target_size, target_size):
                    issue_parts.append("wrong_restored_size")

                if mode != "RGB":
                    issue_parts.append("wrong_color_mode")

                expected_checksum = str(
                    row.get("restored_sha256", "")
                ).strip()
                if expected_checksum:
                    observed_checksum = calculate_file_sha256(restored_path)
                    checksum_matches = observed_checksum == expected_checksum
                    if not checksum_matches:
                        issue_parts.append("restored_checksum_mismatch")

            except Exception as exc:
                issue_parts.append(
                    "unreadable_restored_file: "
                    f"{type(exc).__name__}: {exc}"
                )

        validation_rows.append(
            {
                "restoration_case_id": row["restoration_case_id"],
                "dataset_name": row["dataset_name"],
                "case_id": row["case_id"],
                "painting_id": row["painting_id"],
                "restored_path": str(restored_path),
                "file_exists": file_exists,
                "readable": readable,
                "width": width,
                "height": height,
                "mode": mode,
                "checksum_matches": checksum_matches,
                "validation_passed": len(issue_parts) == 0,
                "issue": "; ".join(issue_parts),
            }
        )

    return pd.DataFrame(validation_rows)


def validate_opencv_restoration_behavior(
    restored_metadata: pd.DataFrame,
    project_root: Path | None = None,
    target_size: int = 768,
) -> pd.DataFrame:
    """Validate basic inpainting behavior without judging visual quality."""
    required_columns = {
        "restoration_case_id",
        "dataset_name",
        "case_id",
        "painting_id",
        "clean_path",
        "damaged_path",
        "mask_path",
        "restored_path",
        "status",
    }
    missing_columns = sorted(required_columns - set(restored_metadata.columns))
    if missing_columns:
        raise ValueError(
            "Restored metadata is missing required behavior columns: "
            f"{missing_columns}"
        )

    validation_rows: list[dict[str, Any]] = []

    for _, row in restored_metadata.iterrows():
        issue_parts: list[str] = []
        mask_area_pixels = None
        changed_pixels_vs_damaged = None
        changed_pixels_inside_mask = None
        changed_pixels_outside_mask = None
        outside_mask_preserved = None
        empty_mask_unchanged = None
        nonempty_mask_changed = None

        try:
            clean_path = _normalise_path(row["clean_path"], project_root)
            damaged_path = _normalise_path(row["damaged_path"], project_root)
            mask_path = _normalise_path(row["mask_path"], project_root)
            restored_path = _normalise_path(row["restored_path"], project_root)

            with Image.open(clean_path) as image:
                clean_array = np.asarray(image.convert("RGB"))
            with Image.open(damaged_path) as image:
                damaged_array = np.asarray(image.convert("RGB"))
            with Image.open(mask_path) as image:
                mask_array = np.asarray(image.convert("L")) > 127
            with Image.open(restored_path) as image:
                restored_array = np.asarray(image.convert("RGB"))

            expected_shape = (target_size, target_size, 3)
            if (
                clean_array.shape != expected_shape
                or damaged_array.shape != expected_shape
                or restored_array.shape != expected_shape
                or mask_array.shape != expected_shape[:2]
            ):
                issue_parts.append("image_shape_mismatch")
            else:
                changed_map = np.any(
                    damaged_array != restored_array,
                    axis=2,
                )
                mask_area_pixels = int(mask_array.sum())
                changed_pixels_vs_damaged = int(changed_map.sum())
                changed_pixels_inside_mask = int(
                    np.logical_and(changed_map, mask_array).sum()
                )
                changed_pixels_outside_mask = int(
                    np.logical_and(changed_map, ~mask_array).sum()
                )

                outside_mask_preserved = changed_pixels_outside_mask == 0
                if not outside_mask_preserved:
                    issue_parts.append("pixels_changed_outside_mask")

                if mask_area_pixels == 0:
                    empty_mask_unchanged = bool(
                        np.array_equal(damaged_array, restored_array)
                    )
                    if not empty_mask_unchanged:
                        issue_parts.append("empty_mask_changed_image")
                else:
                    nonempty_mask_changed = changed_pixels_inside_mask > 0
                    if not nonempty_mask_changed:
                        issue_parts.append("nonempty_mask_did_not_change")

        except Exception as exc:
            issue_parts.append(f"{type(exc).__name__}: {exc}")

        validation_rows.append(
            {
                "restoration_case_id": row["restoration_case_id"],
                "dataset_name": row["dataset_name"],
                "case_id": row["case_id"],
                "painting_id": row["painting_id"],
                "mask_area_pixels": mask_area_pixels,
                "changed_pixels_vs_damaged": changed_pixels_vs_damaged,
                "changed_pixels_inside_mask": changed_pixels_inside_mask,
                "changed_pixels_outside_mask": changed_pixels_outside_mask,
                "outside_mask_preserved": outside_mask_preserved,
                "empty_mask_unchanged": empty_mask_unchanged,
                "nonempty_mask_changed": nonempty_mask_changed,
                "behavior_validation_passed": len(issue_parts) == 0,
                "issue": "; ".join(issue_parts),
            }
        )

    return pd.DataFrame(validation_rows)


def audit_opencv_restoration_inventory(
    restored_metadata: pd.DataFrame,
    restored_root_dir: Path,
    project_root: Path | None = None,
) -> pd.DataFrame:
    """Compare metadata-referenced outputs with observed PNG files."""
    required_columns = {
        "restoration_case_id",
        "dataset_name",
        "restored_path",
    }
    missing_columns = sorted(required_columns - set(restored_metadata.columns))
    if missing_columns:
        raise ValueError(
            "Restored metadata is missing inventory columns: "
            f"{missing_columns}"
        )

    expected_paths = {
        _normalise_path(path_value, project_root).resolve()
        for path_value in restored_metadata["restored_path"]
    }
    observed_paths = {
        path.resolve()
        for path in Path(restored_root_dir).rglob("*.png")
        if path.is_file()
    }

    rows: list[dict[str, Any]] = []

    for _, row in restored_metadata.iterrows():
        restored_path = _normalise_path(
            row["restored_path"],
            project_root,
        ).resolve()
        exists = restored_path in observed_paths
        rows.append(
            {
                "record_type": "expected",
                "restoration_case_id": row["restoration_case_id"],
                "dataset_name": row["dataset_name"],
                "restored_path": str(restored_path),
                "exists": exists,
                "unexpected": False,
                "inventory_passed": exists,
                "issue": "" if exists else "missing_restored_file",
            }
        )

    for unexpected_path in sorted(observed_paths - expected_paths, key=str):
        rows.append(
            {
                "record_type": "unexpected",
                "restoration_case_id": "",
                "dataset_name": "",
                "restored_path": str(unexpected_path),
                "exists": True,
                "unexpected": True,
                "inventory_passed": False,
                "issue": "unexpected_restored_file",
            }
        )

    return pd.DataFrame(rows)


def summarize_opencv_restoration(
    restored_metadata: pd.DataFrame,
) -> pd.DataFrame:
    """Create a dataset-level restoration execution summary."""
    return (
        restored_metadata
        .groupby("dataset_name", dropna=False)
        .agg(
            input_cases=("case_id", "count"),
            successful_cases=(
                "status",
                lambda values: int((values == "ok").sum()),
            ),
            failed_cases=(
                "status",
                lambda values: int((values != "ok").sum()),
            ),
            total_runtime_seconds=("runtime_seconds", "sum"),
            mean_runtime_seconds=("runtime_seconds", "mean"),
            median_runtime_seconds=("runtime_seconds", "median"),
            max_runtime_seconds=("runtime_seconds", "max"),
        )
        .reset_index()
    )
