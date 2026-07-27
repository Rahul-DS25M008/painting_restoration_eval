"""LaMa restoration pipeline helpers for painting restoration experiments.

The Notebook 14 LaMa stage mirrors the OpenCV restoration contract: it consumes
one normalized multi-dataset manifest, writes restored PNGs under a model root,
and returns one restoration metadata table with execution, hardware, runtime,
failure, retry, and validation-friendly fields.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time
from datetime import datetime, timezone
from hashlib import sha256
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image


MODEL_NAME = "lama"
IOPAINT_MODEL_NAME = "lama"
ZERO_CONTROL_MASK_TYPE = "zero_control"
RESTORATION_GENERATOR_NAME = "restoration_eval.restoration_lama"
RESTORATION_GENERATOR_VERSION = "2.0.0"

DEFAULT_DEVICE = "cuda"
DEFAULT_TARGET_SIZE = 768
DEFAULT_MASK_THRESHOLD = 127

REQUIRED_INPUT_COLUMNS = [
    "dataset_name",
    "case_id",
    "painting_id",
    "clean_path",
    "damaged_path",
    "mask_path",
]

LEGACY_REQUIRED_INPUT_COLUMNS = [
    "case_id",
    "painting_id",
    "mask_type",
    "clean_path",
    "damaged_path",
    "mask_path",
]

_DAMAGED_PATH_ALIASES = [
    "damaged_path",
    "degraded_path",
    "synthetic_degraded_path",
    "masked_path",
]

_MASK_PATH_ALIASES = [
    "mask_path",
    "sensitivity_mask_path",
    "effect_mask_path",
    "synthetic_effect_mask_path",
]

_CLEAN_PATH_ALIASES = [
    "clean_path",
    "processed_path",
    "processed_image_path",
    "image_path",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_columns(
    df: pd.DataFrame,
    required_columns: list[str] | set[str],
    *,
    dataframe_name: str,
) -> None:
    """Raise a clear error if required columns are missing."""
    missing_columns = sorted(
        column for column in required_columns if column not in df.columns
    )
    if missing_columns:
        raise ValueError(
            f"{dataframe_name} is missing required columns: {missing_columns}"
        )


def ensure_directory(path: Path | str) -> Path:
    """Create a directory if it does not exist and return it as Path."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def reset_directory(path: Path | str) -> Path:
    """Delete a directory if it exists, recreate it, and return it as Path."""
    path = Path(path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_path(
    path_value: str | Path,
    *,
    project_root: Path | str | None = None,
) -> Path:
    """Resolve a possibly relative path against project_root."""
    path = Path(str(path_value))
    if path.is_absolute() or project_root is None:
        return path
    return (Path(project_root) / path).resolve()


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


def to_storage_path(
    path: Path | str,
    *,
    project_root: Path | str | None = None,
    use_relative_paths: bool = True,
) -> str:
    """Convert a filesystem path to a string for metadata storage."""
    path = Path(path).resolve()

    if use_relative_paths and project_root is not None:
        try:
            return path.relative_to(Path(project_root).resolve()).as_posix()
        except ValueError:
            return str(path)

    return str(path)


def calculate_file_sha256(
    file_path: Path | str,
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


def _safe_case_filename(case_id: str) -> str:
    safe_chars = []
    for character in str(case_id):
        if character.isalnum() or character in {"-", "_", "."}:
            safe_chars.append(character)
        else:
            safe_chars.append("_")
    safe_name = "".join(safe_chars).strip("._")
    return safe_name or "case"


def _first_existing_column(
    df: pd.DataFrame,
    candidates: list[str],
    *,
    purpose: str,
) -> str:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    raise ValueError(
        f"Could not find a {purpose} column. Tried: {candidates}"
    )


def _package_version(package_name: str) -> str:
    try:
        return importlib_metadata.version(package_name)
    except importlib_metadata.PackageNotFoundError:
        return ""


def _detect_torch_environment() -> dict[str, Any]:
    environment = {
        "torch_version": "",
        "cuda_available": False,
        "cuda_device_count": 0,
        "cuda_device_name": "",
        "cuda_runtime_version": "",
    }
    try:
        import torch  # type: ignore

        environment["torch_version"] = str(torch.__version__)
        environment["cuda_available"] = bool(torch.cuda.is_available())
        environment["cuda_device_count"] = int(torch.cuda.device_count())
        environment["cuda_runtime_version"] = str(
            getattr(torch.version, "cuda", "") or ""
        )
        if torch.cuda.is_available() and torch.cuda.device_count() > 0:
            environment["cuda_device_name"] = str(torch.cuda.get_device_name(0))
    except Exception:
        pass
    return environment


def get_lama_runtime_environment(
    *,
    device: str = DEFAULT_DEVICE,
    executable: str = "iopaint",
    iopaint_model_name: str = IOPAINT_MODEL_NAME,
) -> dict[str, Any]:
    """Capture reproducibility metadata for LaMa restoration runs."""
    environment = {
        "model_name": MODEL_NAME,
        "iopaint_model_name": iopaint_model_name,
        "iopaint_package_version": _package_version("iopaint"),
        "lama_model_version": _package_version("iopaint") or "iopaint_lama",
        "iopaint_executable": executable,
        "execution_device": device,
        "execution_backend": "iopaint",
        "operating_system": platform.platform(),
        "processor": platform.processor(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
    }
    environment.update(_detect_torch_environment())
    return environment


def _copy_image(source_path: Path, destination_path: Path) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_path)


def _write_rgb_png(source_path: Path, destination_path: Path) -> tuple[int, int, str]:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as image:
        rgb_image = image.convert("RGB")
        width, height = rgb_image.size
        rgb_image.save(destination_path, format="PNG")
    return width, height, "RGB"


def _write_binary_mask_png(
    source_path: Path,
    destination_path: Path,
    *,
    threshold: int = DEFAULT_MASK_THRESHOLD,
) -> int:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as image:
        mask_array = np.asarray(image.convert("L"))
    binary_array = np.where(mask_array > threshold, 255, 0).astype(np.uint8)
    Image.fromarray(binary_array, mode="L").save(destination_path, format="PNG")
    return int((binary_array > 0).sum())


def _target_size_tuple(target_size: int | tuple[int, int]) -> tuple[int, int]:
    if isinstance(target_size, int):
        return (target_size, target_size)
    return (int(target_size[0]), int(target_size[1]))


def _read_rgb_array(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        image.load()
        return np.asarray(image.convert("RGB"))


def _read_mask_bool_array(
    path: Path,
    *,
    threshold: int = DEFAULT_MASK_THRESHOLD,
) -> np.ndarray:
    with Image.open(path) as image:
        image.load()
        return np.asarray(image.convert("L")) > threshold


def _is_zero_control_row(
    row: pd.Series,
    *,
    zero_control_mask_type: str = ZERO_CONTROL_MASK_TYPE,
) -> bool:
    for column in ("mask_type", "base_mask_type", "report_mask_type"):
        if column in row.index and str(row[column]) == zero_control_mask_type:
            return True

    for column in (
        "mask_area_pixels",
        "mask_pixels",
        "damaged_pixels",
        "realized_damage_pixels",
    ):
        if column in row.index and pd.notna(row[column]):
            try:
                return float(row[column]) == 0.0
            except (TypeError, ValueError):
                continue

    return False


def normalize_lama_restoration_input_manifest(
    source_df: pd.DataFrame,
    *,
    dataset_name: str,
    source_metadata_path: Path | str | None = None,
    damaged_path_column: str | None = None,
    mask_path_column: str | None = None,
    clean_path_column: str | None = None,
    case_id_prefix: str | None = None,
) -> pd.DataFrame:
    """Normalize one upstream metadata table for LaMa restoration.

    The returned table always contains the Notebook 14 restoration columns
    required by :func:`create_lama_restoration_dataset`, while preserving
    upstream columns for later traceability.
    """
    if source_df.empty:
        return pd.DataFrame(columns=REQUIRED_INPUT_COLUMNS)

    working_df = source_df.copy()

    if "status" in working_df.columns:
        working_df = working_df[working_df["status"].astype(str).eq("ok")].copy()

    clean_column = clean_path_column or _first_existing_column(
        working_df,
        _CLEAN_PATH_ALIASES,
        purpose="clean image path",
    )
    damaged_column = damaged_path_column or _first_existing_column(
        working_df,
        _DAMAGED_PATH_ALIASES,
        purpose="damaged/degraded image path",
    )
    mask_column = mask_path_column or _first_existing_column(
        working_df,
        _MASK_PATH_ALIASES,
        purpose="mask/effect-mask path",
    )

    if "case_id" not in working_df.columns:
        raise ValueError(
            "source_df must contain case_id before LaMa restoration normalization."
        )

    if "painting_id" not in working_df.columns:
        raise ValueError(
            "source_df must contain painting_id before LaMa restoration normalization."
        )

    normalized_df = working_df.copy()
    original_case_id = normalized_df["case_id"].astype(str)
    if case_id_prefix:
        normalized_df["case_id"] = (
            case_id_prefix.rstrip("_") + "__" + original_case_id
        )
    else:
        normalized_df["case_id"] = original_case_id

    normalized_df["dataset_name"] = dataset_name
    normalized_df["source_case_id_original"] = original_case_id
    normalized_df["clean_path"] = normalized_df[clean_column].astype(str)
    normalized_df["damaged_path"] = normalized_df[damaged_column].astype(str)
    normalized_df["mask_path"] = normalized_df[mask_column].astype(str)
    normalized_df["source_metadata_path"] = (
        "" if source_metadata_path is None else str(source_metadata_path)
    )

    if "source_mask_semantics" not in normalized_df.columns:
        if dataset_name == "synthetic_degradation":
            normalized_df["source_mask_semantics"] = "synthetic_effect_mask"
        else:
            normalized_df["source_mask_semantics"] = "inpainting_mask"

    if "lama_applicability" not in normalized_df.columns:
        normalized_df["lama_applicability"] = "primary"

    leading_columns = [
        "dataset_name",
        "case_id",
        "source_case_id_original",
        "painting_id",
        "clean_path",
        "damaged_path",
        "mask_path",
        "source_mask_semantics",
        "lama_applicability",
        "source_metadata_path",
    ]
    remaining_columns = [
        column for column in normalized_df.columns if column not in leading_columns
    ]
    return normalized_df[leading_columns + remaining_columns].reset_index(drop=True)


def _coerce_legacy_input_manifest(
    input_metadata_df: pd.DataFrame,
    *,
    dataset_name: str = "canonical",
) -> pd.DataFrame:
    working_df = input_metadata_df.copy()
    if "dataset_name" not in working_df.columns:
        working_df["dataset_name"] = dataset_name
    if "source_case_id_original" not in working_df.columns and "case_id" in working_df:
        working_df["source_case_id_original"] = working_df["case_id"].astype(str)
    if "source_mask_semantics" not in working_df.columns:
        working_df["source_mask_semantics"] = "inpainting_mask"
    if "lama_applicability" not in working_df.columns:
        working_df["lama_applicability"] = "primary"
    if "source_metadata_path" not in working_df.columns:
        working_df["source_metadata_path"] = ""
    return working_df


def validate_restoration_input_manifest(
    restoration_input: pd.DataFrame,
) -> None:
    """Validate the normalized manifest consumed by the LaMa pipeline."""
    require_columns(
        restoration_input,
        REQUIRED_INPUT_COLUMNS,
        dataframe_name="restoration_input",
    )

    if restoration_input.empty:
        raise ValueError("Restoration input manifest is empty.")

    if restoration_input["case_id"].isna().any():
        raise ValueError("Restoration input manifest contains null case IDs.")

    duplicate_mask = (
        restoration_input["dataset_name"].astype(str)
        + "__"
        + restoration_input["case_id"].astype(str)
    ).duplicated(keep=False)
    if duplicate_mask.any():
        duplicates = (
            restoration_input.loc[duplicate_mask, ["dataset_name", "case_id"]]
            .astype(str)
            .agg("__".join, axis=1)
            .tolist()
        )
        raise ValueError(
            "Restoration input manifest contains duplicate dataset/case IDs: "
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


def _build_iopaint_command(
    *,
    staging_input_dir: Path,
    staging_mask_dir: Path,
    staging_output_dir: Path,
    device: str,
    executable: str,
    iopaint_model_name: str,
    extra_args: list[str] | None,
) -> list[str]:
    command = [
        executable,
        "run",
        "--model",
        iopaint_model_name,
        "--device",
        device,
        "--image",
        str(staging_input_dir),
        "--mask",
        str(staging_mask_dir),
        "--output",
        str(staging_output_dir),
    ]
    if extra_args:
        command.extend(extra_args)
    return command


def _run_subprocess_with_logs(
    command: list[str],
    *,
    logs_dir: Path,
    log_stem: str,
) -> dict[str, Any]:
    logs_dir.mkdir(parents=True, exist_ok=True)

    subprocess_env = os.environ.copy()
    subprocess_env.update(
        {
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "NO_COLOR": "1",
            "FORCE_COLOR": "0",
            "TERM": "dumb",
        }
    )

    started_at_utc = _utc_now_iso()
    timer_start = time.perf_counter()
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=subprocess_env,
    )
    runtime_seconds = time.perf_counter() - timer_start
    completed_at_utc = _utc_now_iso()

    command_log_path = logs_dir / f"{log_stem}_command.txt"
    stdout_log_path = logs_dir / f"{log_stem}_stdout.txt"
    stderr_log_path = logs_dir / f"{log_stem}_stderr.txt"

    command_log_path.write_text(" ".join(command), encoding="utf-8")
    stdout_log_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_log_path.write_text(completed.stderr or "", encoding="utf-8")

    return {
        "command": command,
        "command_text": " ".join(command),
        "returncode": int(completed.returncode),
        "stdout": completed.stdout or "",
        "stderr": completed.stderr or "",
        "runtime_seconds": float(runtime_seconds),
        "started_at_utc": started_at_utc,
        "completed_at_utc": completed_at_utc,
        "command_log_path": str(command_log_path),
        "stdout_log_path": str(stdout_log_path),
        "stderr_log_path": str(stderr_log_path),
    }


def _find_iopaint_output(
    output_dir: Path,
    expected_filename: str,
) -> Path | None:
    expected_path = output_dir / expected_filename
    if expected_path.exists():
        return expected_path

    png_paths = sorted(path for path in output_dir.glob("*.png") if path.is_file())
    if len(png_paths) == 1:
        return png_paths[0]
    return None


def _run_lama_case_with_retries(
    *,
    restoration_case_id: str,
    safe_case_id: str,
    damaged_path: Path,
    mask_path: Path,
    staging_root: Path,
    logs_dir: Path,
    device: str,
    executable: str,
    iopaint_model_name: str,
    extra_iopaint_args: list[str] | None,
    mask_threshold: int,
    max_retries: int,
    retry_delay_seconds: float,
) -> dict[str, Any]:
    case_staging_root = staging_root / "cases" / safe_case_id
    input_dir = reset_directory(case_staging_root / "input")
    mask_dir = reset_directory(case_staging_root / "mask")
    output_dir = reset_directory(case_staging_root / "output")

    staged_filename = f"{safe_case_id}.png"
    staged_input_path = input_dir / staged_filename
    staged_mask_path = mask_dir / staged_filename

    _write_rgb_png(damaged_path, staged_input_path)
    mask_area_pixels = _write_binary_mask_png(
        mask_path,
        staged_mask_path,
        threshold=mask_threshold,
    )

    command = _build_iopaint_command(
        staging_input_dir=input_dir,
        staging_mask_dir=mask_dir,
        staging_output_dir=output_dir,
        device=device,
        executable=executable,
        iopaint_model_name=iopaint_model_name,
        extra_args=extra_iopaint_args,
    )

    attempts: list[dict[str, Any]] = []
    for attempt_index in range(max_retries + 1):
        if attempt_index > 0 and retry_delay_seconds > 0:
            time.sleep(retry_delay_seconds)

        log_stem = f"{safe_case_id}_attempt_{attempt_index + 1:02d}"
        run_info = _run_subprocess_with_logs(
            command,
            logs_dir=logs_dir,
            log_stem=log_stem,
        )
        attempts.append(run_info)

        output_path = _find_iopaint_output(output_dir, staged_filename)
        if run_info["returncode"] == 0 and output_path is not None:
            return {
                "status": "ok",
                "issue": "",
                "staged_input_path": staged_input_path,
                "staged_mask_path": staged_mask_path,
                "staged_output_path": output_path,
                "mask_area_pixels": mask_area_pixels,
                "attempts": attempts,
            }

    last_attempt = attempts[-1] if attempts else {}
    stderr_tail = str(last_attempt.get("stderr", "")).strip().splitlines()[-5:]
    issue = "IOPaint LaMa failed"
    if stderr_tail:
        issue += ": " + " | ".join(stderr_tail)
    elif attempts:
        issue += f" with return code {last_attempt.get('returncode')}"

    return {
        "status": "error",
        "issue": issue,
        "staged_input_path": staged_input_path,
        "staged_mask_path": staged_mask_path,
        "staged_output_path": "",
        "mask_area_pixels": mask_area_pixels,
        "attempts": attempts,
    }


def _leading_restoration_columns() -> list[str]:
    return [
        "restoration_case_id",
        "model_name",
        "iopaint_model_name",
        "iopaint_package_version",
        "lama_model_version",
        "restoration_method",
        "inference_mode",
        "restoration_generator_name",
        "restoration_generator_version",
        "execution_device",
        "execution_backend",
        "operating_system",
        "processor",
        "machine",
        "python_version",
        "torch_version",
        "cuda_available",
        "cuda_device_count",
        "cuda_device_name",
        "cuda_runtime_version",
        "retry_count",
        "attempt_count",
        "iopaint_returncode",
        "iopaint_command",
        "iopaint_command_log_path",
        "iopaint_stdout_log_path",
        "iopaint_stderr_log_path",
        "dataset_name",
        "source_case_id",
        "source_case_id_original",
        "case_id",
        "painting_id",
        "lama_applicability",
        "source_mask_semantics",
        "mask_threshold",
        "mask_area_pixels",
        "clean_path",
        "damaged_path",
        "mask_path",
        "restored_filename",
        "restored_path",
        "restored_sha256",
        "restored_width",
        "restored_height",
        "restored_mode",
        "runtime_seconds",
        "started_at_utc",
        "completed_at_utc",
        "output_written",
        "status",
        "issue",
        "source_metadata_path",
    ]


def _reorder_restoration_columns(df: pd.DataFrame) -> pd.DataFrame:
    leading_columns = [
        column for column in _leading_restoration_columns() if column in df.columns
    ]
    remaining_columns = [
        column for column in df.columns if column not in leading_columns
    ]
    return df[leading_columns + remaining_columns]


def create_lama_restoration_dataset(
    restoration_input: pd.DataFrame,
    restored_root_dir: Path | str,
    *,
    staging_root: Path | str,
    project_root: Path | str | None = None,
    model_name: str = MODEL_NAME,
    iopaint_model_name: str = IOPAINT_MODEL_NAME,
    device: str = DEFAULT_DEVICE,
    executable: str = "iopaint",
    extra_iopaint_args: list[str] | None = None,
    zero_control_mask_type: str = ZERO_CONTROL_MASK_TYPE,
    mask_threshold: int = DEFAULT_MASK_THRESHOLD,
    overwrite: bool = False,
    max_retries: int = 0,
    retry_delay_seconds: float = 0.0,
    compute_checksums: bool = True,
    cleanup_staging: bool = False,
    progress_every: int | None = 25,
) -> pd.DataFrame:
    """Restore all rows in a normalized multi-dataset LaMa input manifest."""
    restoration_input = _coerce_legacy_input_manifest(restoration_input)
    validate_restoration_input_manifest(restoration_input)

    project_root_path = None if project_root is None else Path(project_root).resolve()
    restored_root_dir = Path(restored_root_dir)
    staging_root = Path(staging_root)
    restored_root_dir.mkdir(parents=True, exist_ok=True)
    staging_root.mkdir(parents=True, exist_ok=True)
    logs_dir = ensure_directory(staging_root / "logs")

    runtime_environment = get_lama_runtime_environment(
        device=device,
        executable=executable,
        iopaint_model_name=iopaint_model_name,
    )

    ordered_input = restoration_input.copy()
    ordered_input["_case_sort"] = ordered_input["case_id"].astype(str)
    ordered_input = (
        ordered_input.sort_values(["dataset_name", "_case_sort"])
        .drop(columns="_case_sort")
        .reset_index(drop=True)
    )

    records: list[dict[str, Any]] = []
    total_rows = len(ordered_input)

    for index, (_, row) in enumerate(ordered_input.iterrows(), start=1):
        if progress_every and (
            index == 1 or index % progress_every == 0 or index == total_rows
        ):
            print(f"Running LaMa restoration case {index}/{total_rows}")

        source_record = row.to_dict()
        dataset_name = str(row["dataset_name"])
        source_case_id = str(row["case_id"])
        source_case_id_original = str(
            row.get("source_case_id_original", source_case_id)
        )
        restoration_case_id = f"{model_name}__{dataset_name}__{source_case_id}"
        safe_case_id = _safe_case_filename(restoration_case_id)

        dataset_output_dir = restored_root_dir / dataset_name
        dataset_output_dir.mkdir(parents=True, exist_ok=True)
        restored_filename = f"{source_case_id}_restored_{model_name}.png"
        restored_path = dataset_output_dir / restored_filename

        clean_path = _normalise_path(row["clean_path"], project_root_path)
        damaged_path = _normalise_path(row["damaged_path"], project_root_path)
        mask_path = _normalise_path(row["mask_path"], project_root_path)

        status = "ok"
        issue = ""
        output_written = False
        restored_checksum = ""
        restored_width = np.nan
        restored_height = np.nan
        restored_mode = ""
        started_at_utc = _utc_now_iso()
        completed_at_utc = ""
        runtime_seconds = 0.0
        retry_count = 0
        attempt_count = 0
        iopaint_returncode = 0
        iopaint_command = ""
        command_log_path = ""
        stdout_log_path = ""
        stderr_log_path = ""
        restoration_method = "iopaint_lama"
        inference_mode = "model_inference"
        staged_input_path = ""
        staged_mask_path = ""
        staged_output_path = ""
        mask_area_pixels = np.nan

        try:
            if not clean_path.exists():
                raise FileNotFoundError(f"Clean image not found: {clean_path}")
            if not damaged_path.exists():
                raise FileNotFoundError(f"Damaged/degraded image not found: {damaged_path}")
            if not mask_path.exists():
                raise FileNotFoundError(f"Mask/effect mask not found: {mask_path}")

            zero_control = _is_zero_control_row(
                row,
                zero_control_mask_type=zero_control_mask_type,
            )

            if zero_control:
                restoration_method = "zero_control_copy"
                inference_mode = "copied_zero_control"
                with Image.open(mask_path) as image:
                    mask_area_pixels = int(
                        (np.asarray(image.convert("L")) > mask_threshold).sum()
                    )
                if overwrite or not restored_path.exists():
                    _write_rgb_png(damaged_path, restored_path)
                    output_written = True
            elif restored_path.exists() and not overwrite:
                inference_mode = "existing_output_reused"
            else:
                case_result = _run_lama_case_with_retries(
                    restoration_case_id=restoration_case_id,
                    safe_case_id=safe_case_id,
                    damaged_path=damaged_path,
                    mask_path=mask_path,
                    staging_root=staging_root,
                    logs_dir=logs_dir,
                    device=device,
                    executable=executable,
                    iopaint_model_name=iopaint_model_name,
                    extra_iopaint_args=extra_iopaint_args,
                    mask_threshold=mask_threshold,
                    max_retries=max_retries,
                    retry_delay_seconds=retry_delay_seconds,
                )
                attempts = case_result["attempts"]
                attempt_count = len(attempts)
                retry_count = max(0, attempt_count - 1)
                runtime_seconds = float(
                    sum(float(attempt["runtime_seconds"]) for attempt in attempts)
                )
                last_attempt = attempts[-1] if attempts else {}
                iopaint_returncode = int(last_attempt.get("returncode", -1))
                iopaint_command = str(last_attempt.get("command_text", ""))
                command_log_path = str(last_attempt.get("command_log_path", ""))
                stdout_log_path = str(last_attempt.get("stdout_log_path", ""))
                stderr_log_path = str(last_attempt.get("stderr_log_path", ""))
                staged_input_path = str(case_result["staged_input_path"])
                staged_mask_path = str(case_result["staged_mask_path"])
                staged_output_path = str(case_result["staged_output_path"])
                mask_area_pixels = int(case_result["mask_area_pixels"])

                if case_result["status"] != "ok":
                    raise RuntimeError(case_result["issue"])

                _write_rgb_png(Path(case_result["staged_output_path"]), restored_path)
                output_written = True

            if not restored_path.exists():
                raise FileNotFoundError(
                    f"Restoration output was not created: {restored_path}"
                )

            with Image.open(restored_path) as restored_image:
                restored_image.load()
                restored_width, restored_height = restored_image.size
                restored_mode = restored_image.mode

            if compute_checksums:
                restored_checksum = calculate_file_sha256(restored_path)

        except Exception as exc:
            status = "error"
            issue = f"{type(exc).__name__}: {exc}"

        completed_at_utc = _utc_now_iso()

        source_record.update(
            {
                "restoration_case_id": restoration_case_id,
                "model_name": model_name,
                "iopaint_model_name": iopaint_model_name,
                "iopaint_package_version": runtime_environment[
                    "iopaint_package_version"
                ],
                "lama_model_version": runtime_environment["lama_model_version"],
                "restoration_method": restoration_method,
                "inference_mode": inference_mode,
                "restoration_generator_name": RESTORATION_GENERATOR_NAME,
                "restoration_generator_version": RESTORATION_GENERATOR_VERSION,
                "execution_device": device,
                "execution_backend": runtime_environment["execution_backend"],
                "operating_system": runtime_environment["operating_system"],
                "processor": runtime_environment["processor"],
                "machine": runtime_environment["machine"],
                "python_version": runtime_environment["python_version"],
                "torch_version": runtime_environment["torch_version"],
                "cuda_available": runtime_environment["cuda_available"],
                "cuda_device_count": runtime_environment["cuda_device_count"],
                "cuda_device_name": runtime_environment["cuda_device_name"],
                "cuda_runtime_version": runtime_environment["cuda_runtime_version"],
                "retry_count": int(retry_count),
                "attempt_count": int(attempt_count),
                "iopaint_returncode": int(iopaint_returncode),
                "iopaint_command": iopaint_command,
                "iopaint_command_log_path": command_log_path,
                "iopaint_stdout_log_path": stdout_log_path,
                "iopaint_stderr_log_path": stderr_log_path,
                "dataset_name": dataset_name,
                "source_case_id": source_case_id,
                "source_case_id_original": source_case_id_original,
                "case_id": source_case_id,
                "painting_id": row["painting_id"],
                "lama_applicability": row.get("lama_applicability", "primary"),
                "source_mask_semantics": row.get(
                    "source_mask_semantics",
                    "inpainting_mask",
                ),
                "mask_threshold": int(mask_threshold),
                "mask_area_pixels": mask_area_pixels,
                "clean_path": _relative_or_absolute(clean_path, project_root_path),
                "damaged_path": _relative_or_absolute(damaged_path, project_root_path),
                "mask_path": _relative_or_absolute(mask_path, project_root_path),
                "lama_staged_input_path": to_storage_path(
                    staged_input_path,
                    project_root=project_root_path,
                )
                if staged_input_path
                else "",
                "lama_staged_mask_path": to_storage_path(
                    staged_mask_path,
                    project_root=project_root_path,
                )
                if staged_mask_path
                else "",
                "lama_staged_output_path": to_storage_path(
                    staged_output_path,
                    project_root=project_root_path,
                )
                if staged_output_path
                else "",
                "restored_filename": restored_filename,
                "restored_path": _relative_or_absolute(
                    restored_path,
                    project_root_path,
                ),
                "restored_sha256": restored_checksum,
                "restored_width": restored_width,
                "restored_height": restored_height,
                "restored_mode": restored_mode,
                "runtime_seconds": float(runtime_seconds),
                "started_at_utc": started_at_utc,
                "completed_at_utc": completed_at_utc,
                "output_written": bool(output_written),
                "status": status,
                "issue": issue,
            }
        )
        records.append(source_record)

    if cleanup_staging:
        shutil.rmtree(staging_root, ignore_errors=True)

    return _reorder_restoration_columns(pd.DataFrame(records))


def validate_restored_images(
    restored_metadata: pd.DataFrame,
    project_root: Path | str | None = None,
    target_size: int | tuple[int, int] = DEFAULT_TARGET_SIZE,
) -> pd.DataFrame:
    """Validate LaMa restoration files, dimensions, mode, and checksums."""
    required_columns = {
        "restoration_case_id",
        "dataset_name",
        "case_id",
        "painting_id",
        "restored_path",
        "status",
    }
    require_columns(
        restored_metadata,
        required_columns,
        dataframe_name="restored_metadata",
    )

    project_root_path = None if project_root is None else Path(project_root).resolve()
    expected_size = _target_size_tuple(target_size)
    validation_rows: list[dict[str, Any]] = []

    for _, row in restored_metadata.iterrows():
        restored_path = _normalise_path(row["restored_path"], project_root_path)

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

                if (width, height) != expected_size:
                    issue_parts.append("wrong_restored_size")

                if mode != "RGB":
                    issue_parts.append("wrong_color_mode")

                expected_checksum = str(row.get("restored_sha256", "")).strip()
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


def validate_lama_restoration_behavior(
    restored_metadata: pd.DataFrame,
    *,
    project_root: Path | str | None = None,
    target_size: int | tuple[int, int] = DEFAULT_TARGET_SIZE,
    mask_threshold: int = DEFAULT_MASK_THRESHOLD,
    zero_control_mask_type: str = ZERO_CONTROL_MASK_TYPE,
    enforce_outside_mask_preservation: bool = False,
) -> pd.DataFrame:
    """Validate basic LaMa behavior without judging visual quality.

    Outside-mask changes are measured for every case. They are not considered a
    failure by default because neural inpainting wrappers may apply final-image
    compositing differently from deterministic OpenCV Telea.
    """
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
    require_columns(
        restored_metadata,
        required_columns,
        dataframe_name="restored_metadata",
    )

    project_root_path = None if project_root is None else Path(project_root).resolve()
    expected_size = _target_size_tuple(target_size)
    expected_shape = (expected_size[1], expected_size[0], 3)
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
            clean_path = _normalise_path(row["clean_path"], project_root_path)
            damaged_path = _normalise_path(row["damaged_path"], project_root_path)
            mask_path = _normalise_path(row["mask_path"], project_root_path)
            restored_path = _normalise_path(row["restored_path"], project_root_path)

            clean_array = _read_rgb_array(clean_path)
            damaged_array = _read_rgb_array(damaged_path)
            mask_array = _read_mask_bool_array(mask_path, threshold=mask_threshold)
            restored_array = _read_rgb_array(restored_path)

            if (
                clean_array.shape != expected_shape
                or damaged_array.shape != expected_shape
                or restored_array.shape != expected_shape
                or mask_array.shape != expected_shape[:2]
            ):
                issue_parts.append("image_shape_mismatch")
            else:
                changed_map = np.any(damaged_array != restored_array, axis=2)
                mask_area_pixels = int(mask_array.sum())
                changed_pixels_vs_damaged = int(changed_map.sum())
                changed_pixels_inside_mask = int(
                    np.logical_and(changed_map, mask_array).sum()
                )
                changed_pixels_outside_mask = int(
                    np.logical_and(changed_map, ~mask_array).sum()
                )
                outside_mask_preserved = changed_pixels_outside_mask == 0

                if (
                    enforce_outside_mask_preservation
                    and not outside_mask_preserved
                ):
                    issue_parts.append("pixels_changed_outside_mask")

                zero_control = _is_zero_control_row(
                    row,
                    zero_control_mask_type=zero_control_mask_type,
                )
                if zero_control or mask_area_pixels == 0:
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
                "outside_mask_preservation_enforced": bool(
                    enforce_outside_mask_preservation
                ),
                "behavior_validation_passed": len(issue_parts) == 0,
                "issue": "; ".join(issue_parts),
            }
        )

    return pd.DataFrame(validation_rows)


def audit_lama_restoration_inventory(
    restored_metadata: pd.DataFrame,
    restored_root_dir: Path | str,
    *,
    project_root: Path | str | None = None,
) -> pd.DataFrame:
    """Compare metadata-referenced LaMa outputs with observed PNG files."""
    required_columns = {
        "restoration_case_id",
        "dataset_name",
        "restored_path",
    }
    require_columns(
        restored_metadata,
        required_columns,
        dataframe_name="restored_metadata",
    )

    project_root_path = None if project_root is None else Path(project_root).resolve()
    expected_paths = {
        _normalise_path(path_value, project_root_path).resolve()
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
            project_root_path,
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


def summarize_lama_restoration(
    restored_metadata: pd.DataFrame,
) -> pd.DataFrame:
    """Create a dataset-level LaMa restoration execution summary."""
    if restored_metadata.empty:
        return pd.DataFrame(
            columns=[
                "dataset_name",
                "input_cases",
                "successful_cases",
                "failed_cases",
                "total_runtime_seconds",
                "mean_runtime_seconds",
                "median_runtime_seconds",
                "max_runtime_seconds",
                "total_retries",
            ]
        )

    return (
        restored_metadata.groupby("dataset_name", dropna=False)
        .agg(
            input_cases=("case_id", "count"),
            successful_cases=("status", lambda values: int((values == "ok").sum())),
            failed_cases=("status", lambda values: int((values != "ok").sum())),
            total_runtime_seconds=("runtime_seconds", "sum"),
            mean_runtime_seconds=("runtime_seconds", "mean"),
            median_runtime_seconds=("runtime_seconds", "median"),
            max_runtime_seconds=("runtime_seconds", "max"),
            total_retries=("retry_count", "sum"),
        )
        .reset_index()
    )


def build_lama_restoration_audit_table(
    *,
    restored_metadata: pd.DataFrame,
    file_validation: pd.DataFrame | None = None,
    behavior_validation: pd.DataFrame | None = None,
    inventory_audit: pd.DataFrame | None = None,
    expected_dataset_names: list[str] | None = None,
    notebook: str = "14_lama_restoration",
    model_name: str = MODEL_NAME,
) -> pd.DataFrame:
    """Build one compact audit CSV table for Notebook 14."""
    generated_at_utc = _utc_now_iso()
    rows: list[dict[str, Any]] = []

    def add(section: str, check: str, observed: Any, expected: Any, passed: bool) -> None:
        rows.append(
            {
                "notebook": notebook,
                "model_name": model_name,
                "generated_at_utc": generated_at_utc,
                "audit_section": section,
                "check": check,
                "observed": observed,
                "expected": expected,
                "passed": bool(passed),
            }
        )

    add("restoration_execution", "total_rows", len(restored_metadata), ">=1", len(restored_metadata) > 0)
    add(
        "restoration_execution",
        "failed_rows",
        int((restored_metadata["status"] != "ok").sum()) if "status" in restored_metadata else "",
        0,
        "status" in restored_metadata
        and int((restored_metadata["status"] != "ok").sum()) == 0,
    )

    if expected_dataset_names is not None and "dataset_name" in restored_metadata:
        observed_datasets = sorted(restored_metadata["dataset_name"].astype(str).unique())
        add(
            "restoration_execution",
            "dataset_names",
            observed_datasets,
            sorted(expected_dataset_names),
            observed_datasets == sorted(expected_dataset_names),
        )

    if file_validation is not None and not file_validation.empty:
        add(
            "file_validation",
            "failed_file_validations",
            int((~file_validation["validation_passed"].astype(bool)).sum()),
            0,
            bool(file_validation["validation_passed"].astype(bool).all()),
        )

    if behavior_validation is not None and not behavior_validation.empty:
        add(
            "behavior_validation",
            "failed_behavior_validations",
            int((~behavior_validation["behavior_validation_passed"].astype(bool)).sum()),
            0,
            bool(behavior_validation["behavior_validation_passed"].astype(bool).all()),
        )

    if inventory_audit is not None and not inventory_audit.empty:
        add(
            "inventory",
            "failed_inventory_rows",
            int((~inventory_audit["inventory_passed"].astype(bool)).sum()),
            0,
            bool(inventory_audit["inventory_passed"].astype(bool).all()),
        )

    return pd.DataFrame(rows)


# Backwards-compatible wrappers for the old Notebook 11 API.

def prepare_lama_batch_staging(
    input_metadata_df: pd.DataFrame,
    *,
    staging_root: Path | str,
    project_root: Path | str | None = None,
    zero_control_mask_type: str = ZERO_CONTROL_MASK_TYPE,
    progress_every: int | None = 25,
) -> dict[str, Any]:
    """Prepare old-style batch staging folders for non-zero LaMa cases."""
    working_df = _coerce_legacy_input_manifest(input_metadata_df)
    require_columns(
        working_df,
        LEGACY_REQUIRED_INPUT_COLUMNS,
        dataframe_name="input_metadata_df",
    )

    staging_root = Path(staging_root)
    staging_input_dir = reset_directory(staging_root / "input")
    staging_mask_dir = reset_directory(staging_root / "mask")
    staging_output_dir = reset_directory(staging_root / "output")
    staging_logs_dir = reset_directory(staging_root / "logs")

    nonzero_df = working_df[
        ~working_df.apply(
            lambda row: _is_zero_control_row(
                row,
                zero_control_mask_type=zero_control_mask_type,
            ),
            axis=1,
        )
    ].copy()
    zero_control_df = working_df.drop(nonzero_df.index).copy()

    staged_rows: list[dict[str, Any]] = []
    total_nonzero = len(nonzero_df)
    for index, (_, row) in enumerate(nonzero_df.iterrows(), start=1):
        if progress_every and (
            index == 1 or index % progress_every == 0 or index == total_nonzero
        ):
            print(f"Staging LaMa case {index}/{total_nonzero}")

        case_id = str(row["case_id"])
        safe_case_id = _safe_case_filename(case_id)
        staged_filename = f"{safe_case_id}.png"
        staged_input_path = staging_input_dir / staged_filename
        staged_mask_path = staging_mask_dir / staged_filename
        staged_output_path = staging_output_dir / staged_filename

        damaged_path = resolve_path(row["damaged_path"], project_root=project_root)
        mask_path = resolve_path(row["mask_path"], project_root=project_root)
        _write_rgb_png(damaged_path, staged_input_path)
        _write_binary_mask_png(mask_path, staged_mask_path)

        staged_row = row.to_dict()
        staged_row["lama_staged_input_path"] = to_storage_path(
            staged_input_path,
            project_root=project_root,
        )
        staged_row["lama_staged_mask_path"] = to_storage_path(
            staged_mask_path,
            project_root=project_root,
        )
        staged_row["lama_staged_output_path"] = to_storage_path(
            staged_output_path,
            project_root=project_root,
        )
        staged_rows.append(staged_row)

    return {
        "nonzero_staged_df": pd.DataFrame(staged_rows),
        "zero_control_df": zero_control_df.reset_index(drop=True),
        "staging_root": staging_root,
        "staging_input_dir": staging_input_dir,
        "staging_mask_dir": staging_mask_dir,
        "staging_output_dir": staging_output_dir,
        "staging_logs_dir": staging_logs_dir,
    }


def run_iopaint_lama_batch(
    *,
    staging_input_dir: Path | str,
    staging_mask_dir: Path | str,
    staging_output_dir: Path | str,
    staging_logs_dir: Path | str,
    device: str = DEFAULT_DEVICE,
    executable: str = "iopaint",
    iopaint_model_name: str = IOPAINT_MODEL_NAME,
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    """Run old-style IOPaint LaMa batch inference through subprocess."""
    command = _build_iopaint_command(
        staging_input_dir=Path(staging_input_dir),
        staging_mask_dir=Path(staging_mask_dir),
        staging_output_dir=Path(staging_output_dir),
        device=device,
        executable=executable,
        iopaint_model_name=iopaint_model_name,
        extra_args=extra_args,
    )
    return _run_subprocess_with_logs(
        command,
        logs_dir=ensure_directory(staging_logs_dir),
        log_stem="iopaint_batch",
    )


def copy_zero_control_outputs(
    zero_control_df: pd.DataFrame,
    *,
    restored_output_dir: Path | str,
    project_root: Path | str | None = None,
    use_relative_paths: bool = True,
    model_name: str = MODEL_NAME,
    device: str = "none",
    zero_control_mask_type: str = ZERO_CONTROL_MASK_TYPE,
    progress_every: int | None = 25,
) -> pd.DataFrame:
    """Copy zero-control cases directly to a flat restored output folder."""
    working_df = _coerce_legacy_input_manifest(zero_control_df)
    restored_output_dir = ensure_directory(restored_output_dir)
    records: list[dict[str, Any]] = []
    total_zero = len(working_df)

    for index, (_, row) in enumerate(working_df.iterrows(), start=1):
        if progress_every and (
            index == 1 or index % progress_every == 0 or index == total_zero
        ):
            print(f"Copying zero-control LaMa output {index}/{total_zero}")

        if not _is_zero_control_row(row, zero_control_mask_type=zero_control_mask_type):
            raise ValueError(
                f"copy_zero_control_outputs received non-zero case: {row['case_id']}"
            )

        case_id = str(row["case_id"])
        damaged_path = resolve_path(row["damaged_path"], project_root=project_root)
        restored_filename = f"{case_id}_restored_{model_name}.png"
        restored_path = restored_output_dir / restored_filename
        width, height, mode = _write_rgb_png(damaged_path, restored_path)

        output_row = row.to_dict()
        output_row.update(
            {
                "model_name": model_name,
                "restoration_method": "zero_control_copy",
                "inference_mode": "copied_zero_control",
                "restored_filename": restored_filename,
                "restored_path": to_storage_path(
                    restored_path,
                    project_root=project_root,
                    use_relative_paths=use_relative_paths,
                ),
                "device": device,
                "runtime_seconds": 0.0,
                "batch_runtime_seconds": 0.0,
                "restored_width": width,
                "restored_height": height,
                "restored_mode": mode,
                "status": "ok",
                "issue": "zero_control copied without model inference",
            }
        )
        records.append(output_row)

    return pd.DataFrame(records)


def collect_lama_batch_outputs(
    nonzero_staged_df: pd.DataFrame,
    *,
    staging_output_dir: Path | str,
    restored_output_dir: Path | str,
    project_root: Path | str | None = None,
    use_relative_paths: bool = True,
    model_name: str = MODEL_NAME,
    device: str = DEFAULT_DEVICE,
    batch_runtime_seconds: float | None = None,
    progress_every: int | None = 25,
) -> pd.DataFrame:
    """Collect old-style staged IOPaint outputs into a flat output folder."""
    staging_output_dir = Path(staging_output_dir)
    restored_output_dir = ensure_directory(restored_output_dir)
    records: list[dict[str, Any]] = []
    total_nonzero = len(nonzero_staged_df)

    for index, (_, row) in enumerate(nonzero_staged_df.iterrows(), start=1):
        if progress_every and (
            index == 1 or index % progress_every == 0 or index == total_nonzero
        ):
            print(f"Collecting LaMa output {index}/{total_nonzero}")

        case_id = str(row["case_id"])
        safe_case_id = _safe_case_filename(case_id)
        staged_output_path = _find_iopaint_output(
            staging_output_dir,
            f"{safe_case_id}.png",
        )
        restored_filename = f"{case_id}_restored_{model_name}.png"
        restored_path = restored_output_dir / restored_filename

        output_row = row.to_dict()
        if staged_output_path is None:
            output_row.update(
                {
                    "model_name": model_name,
                    "restoration_method": "iopaint_lama",
                    "inference_mode": "model_inference",
                    "restored_filename": restored_filename,
                    "restored_path": "",
                    "device": device,
                    "runtime_seconds": batch_runtime_seconds,
                    "batch_runtime_seconds": batch_runtime_seconds,
                    "restored_width": np.nan,
                    "restored_height": np.nan,
                    "restored_mode": "",
                    "status": "error",
                    "issue": f"Missing staged LaMa output for case {case_id}",
                }
            )
            records.append(output_row)
            continue

        width, height, mode = _write_rgb_png(staged_output_path, restored_path)
        output_row.update(
            {
                "model_name": model_name,
                "restoration_method": "iopaint_lama",
                "inference_mode": "model_inference",
                "restored_filename": restored_filename,
                "restored_path": to_storage_path(
                    restored_path,
                    project_root=project_root,
                    use_relative_paths=use_relative_paths,
                ),
                "device": device,
                "runtime_seconds": batch_runtime_seconds,
                "batch_runtime_seconds": batch_runtime_seconds,
                "restored_width": width,
                "restored_height": height,
                "restored_mode": mode,
                "status": "ok",
                "issue": "",
            }
        )
        records.append(output_row)

    return pd.DataFrame(records)


def run_lama_restoration_pipeline(
    input_metadata_df: pd.DataFrame,
    *,
    restored_output_dir: Path | str,
    staging_root: Path | str,
    project_root: Path | str | None = None,
    device: str = DEFAULT_DEVICE,
    executable: str = "iopaint",
    model_name: str = MODEL_NAME,
    iopaint_model_name: str = IOPAINT_MODEL_NAME,
    use_relative_paths: bool = True,
    zero_control_mask_type: str = ZERO_CONTROL_MASK_TYPE,
    extra_iopaint_args: list[str] | None = None,
    progress_every: int | None = 25,
) -> dict[str, Any]:
    """Run the old public pipeline name using the Notebook 14 implementation."""
    _ = use_relative_paths
    restoration_metadata_df = create_lama_restoration_dataset(
        input_metadata_df,
        restored_root_dir=restored_output_dir,
        staging_root=staging_root,
        project_root=project_root,
        model_name=model_name,
        iopaint_model_name=iopaint_model_name,
        device=device,
        executable=executable,
        extra_iopaint_args=extra_iopaint_args,
        zero_control_mask_type=zero_control_mask_type,
        progress_every=progress_every,
    )
    return {
        "restoration_metadata_df": restoration_metadata_df,
        "staging_info": {"staging_root": Path(staging_root)},
        "run_info": {
            "runtime_seconds": float(
                restoration_metadata_df.get("runtime_seconds", pd.Series(dtype=float))
                .fillna(0)
                .sum()
            ),
            "returncode": 0
            if (
                "status" in restoration_metadata_df
                and restoration_metadata_df["status"].astype(str).eq("ok").all()
            )
            else 1,
        },
    }


def validate_lama_restoration_outputs(
    restoration_metadata_df: pd.DataFrame,
    *,
    project_root: Path | str | None = None,
    expected_size: tuple[int, int] | None = None,
    zero_control_mask_type: str = ZERO_CONTROL_MASK_TYPE,
    progress_every: int | None = 25,
) -> pd.DataFrame:
    """Backwards-compatible validation wrapper for old notebook cells."""
    _ = progress_every
    file_validation_df = validate_restored_images(
        restoration_metadata_df,
        project_root=project_root,
        target_size=expected_size or DEFAULT_TARGET_SIZE,
    )

    if {
        "clean_path",
        "damaged_path",
        "mask_path",
    }.issubset(restoration_metadata_df.columns):
        behavior_validation_df = validate_lama_restoration_behavior(
            restoration_metadata_df,
            project_root=project_root,
            target_size=expected_size or DEFAULT_TARGET_SIZE,
            zero_control_mask_type=zero_control_mask_type,
        )
        merged_df = file_validation_df.merge(
            behavior_validation_df[
                [
                    "restoration_case_id",
                    "changed_pixels_vs_damaged",
                    "changed_pixels_inside_mask",
                    "changed_pixels_outside_mask",
                    "empty_mask_unchanged",
                    "nonempty_mask_changed",
                    "behavior_validation_passed",
                    "issue",
                ]
            ].rename(columns={"issue": "behavior_issue"}),
            on="restoration_case_id",
            how="left",
        )
        merged_df["validation_passed"] = (
            merged_df["validation_passed"].astype(bool)
            & merged_df["behavior_validation_passed"].fillna(True).astype(bool)
        )
        return merged_df

    return file_validation_df


def summarize_lama_restoration_metadata(
    restoration_metadata_df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Build compact summary tables for LaMa restoration metadata."""
    if restoration_metadata_df.empty:
        overview_df = pd.DataFrame(
            [
                {"item": "total_rows", "value": 0},
                {"item": "successful_rows", "value": 0},
                {"item": "error_rows", "value": 0},
            ]
        )
        empty_df = pd.DataFrame()
        return {
            "overview_df": overview_df,
            "by_dataset_df": empty_df,
            "by_mask_type_df": empty_df,
            "by_inference_mode_df": empty_df,
        }

    overview_rows = [
        {"item": "total_rows", "value": len(restoration_metadata_df)},
        {
            "item": "unique_paintings",
            "value": restoration_metadata_df["painting_id"].nunique()
            if "painting_id" in restoration_metadata_df
            else "",
        },
        {
            "item": "successful_rows",
            "value": int((restoration_metadata_df["status"] == "ok").sum()),
        },
        {
            "item": "error_rows",
            "value": int((restoration_metadata_df["status"] != "ok").sum()),
        },
        {
            "item": "model_inference_rows",
            "value": int(
                (
                    restoration_metadata_df.get(
                        "inference_mode",
                        pd.Series(dtype=str),
                    )
                    == "model_inference"
                ).sum()
            ),
        },
        {
            "item": "copied_zero_control_rows",
            "value": int(
                (
                    restoration_metadata_df.get(
                        "inference_mode",
                        pd.Series(dtype=str),
                    )
                    == "copied_zero_control"
                ).sum()
            ),
        },
    ]
    overview_df = pd.DataFrame(overview_rows)
    by_dataset_df = summarize_lama_restoration(restoration_metadata_df)

    if "mask_type" in restoration_metadata_df:
        by_mask_type_df = (
            restoration_metadata_df.groupby("mask_type", dropna=False)
            .agg(
                cases=("case_id", "count"),
                successful_cases=("status", lambda values: int((values == "ok").sum())),
                error_cases=("status", lambda values: int((values != "ok").sum())),
                mean_runtime_seconds=("runtime_seconds", "mean"),
            )
            .reset_index()
            .round(5)
        )
    else:
        by_mask_type_df = pd.DataFrame()

    if "inference_mode" in restoration_metadata_df:
        by_inference_mode_df = (
            restoration_metadata_df.groupby("inference_mode", dropna=False)
            .agg(
                cases=("case_id", "count"),
                successful_cases=("status", lambda values: int((values == "ok").sum())),
                error_cases=("status", lambda values: int((values != "ok").sum())),
            )
            .reset_index()
        )
    else:
        by_inference_mode_df = pd.DataFrame()

    return {
        "overview_df": overview_df,
        "by_dataset_df": by_dataset_df,
        "by_mask_type_df": by_mask_type_df,
        "by_inference_mode_df": by_inference_mode_df,
    }


__all__ = [
    "MODEL_NAME",
    "IOPAINT_MODEL_NAME",
    "ZERO_CONTROL_MASK_TYPE",
    "RESTORATION_GENERATOR_NAME",
    "RESTORATION_GENERATOR_VERSION",
    "REQUIRED_INPUT_COLUMNS",
    "LEGACY_REQUIRED_INPUT_COLUMNS",
    "calculate_file_sha256",
    "ensure_directory",
    "reset_directory",
    "resolve_path",
    "to_storage_path",
    "get_lama_runtime_environment",
    "normalize_lama_restoration_input_manifest",
    "validate_restoration_input_manifest",
    "create_lama_restoration_dataset",
    "validate_restored_images",
    "validate_lama_restoration_behavior",
    "audit_lama_restoration_inventory",
    "summarize_lama_restoration",
    "build_lama_restoration_audit_table",
    "prepare_lama_batch_staging",
    "run_iopaint_lama_batch",
    "copy_zero_control_outputs",
    "collect_lama_batch_outputs",
    "run_lama_restoration_pipeline",
    "validate_lama_restoration_outputs",
    "summarize_lama_restoration_metadata",
]
