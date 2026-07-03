from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image


MODEL_NAME = "lama"
IOPAINT_MODEL_NAME = "lama"
ZERO_CONTROL_MASK_TYPE = "zero_control"

REQUIRED_INPUT_COLUMNS = [
    "case_id",
    "painting_id",
    "mask_type",
    "clean_path",
    "damaged_path",
    "mask_path",
]


def require_columns(
    df: pd.DataFrame,
    required_columns: list[str],
    *,
    dataframe_name: str,
) -> None:
    """Raise a clear error if required columns are missing."""
    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

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

    if not path.is_absolute() and project_root is not None:
        path = Path(project_root) / path

    return path


def to_storage_path(
    path: Path | str,
    *,
    project_root: Path | str | None = None,
    use_relative_paths: bool = True,
) -> str:
    """Convert a filesystem path to a string for metadata storage."""
    path = Path(path)

    if use_relative_paths and project_root is not None:
        try:
            return path.relative_to(Path(project_root)).as_posix()
        except ValueError:
            return str(path)

    return str(path)


def _copy_image(source_path: Path, destination_path: Path) -> None:
    """Copy an image file, creating parent directories if needed."""
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_path)


def prepare_lama_batch_staging(
    input_metadata_df: pd.DataFrame,
    *,
    staging_root: Path | str,
    project_root: Path | str | None = None,
    zero_control_mask_type: str = ZERO_CONTROL_MASK_TYPE,
    progress_every: int | None = 25,
) -> dict[str, Any]:
    """Prepare temporary LaMa staging folders and staged metadata.

    Non-zero cases are copied into:
    - staging_root/input/{case_id}.png
    - staging_root/mask/{case_id}.png

    Zero-control rows are not staged for model inference.
    """
    require_columns(
        input_metadata_df,
        REQUIRED_INPUT_COLUMNS,
        dataframe_name="input_metadata_df",
    )

    staging_root = Path(staging_root)
    staging_input_dir = reset_directory(staging_root / "input")
    staging_mask_dir = reset_directory(staging_root / "mask")
    staging_output_dir = reset_directory(staging_root / "output")
    staging_logs_dir = reset_directory(staging_root / "logs")

    working_df = input_metadata_df.copy()

    if "status" in working_df.columns:
        working_df = working_df[working_df["status"] == "ok"].copy()

    nonzero_df = working_df[
        working_df["mask_type"] != zero_control_mask_type
    ].copy()

    zero_control_df = working_df[
        working_df["mask_type"] == zero_control_mask_type
    ].copy()

    print("Preparing LaMa staging folders")
    print(f"  Staging root: {staging_root}")
    print(f"  Non-zero cases to stage: {len(nonzero_df)}")
    print(f"  Zero-control cases skipped from staging: {len(zero_control_df)}")

    staged_rows: list[dict[str, Any]] = []
    total_nonzero = len(nonzero_df)

    for index, (_, row) in enumerate(nonzero_df.iterrows(), start=1):
        if progress_every and (
            index == 1
            or index % progress_every == 0
            or index == total_nonzero
        ):
            print(f"Staging LaMa case {index}/{total_nonzero}")

        case_id = str(row["case_id"])

        damaged_path = resolve_path(
            row["damaged_path"],
            project_root=project_root,
        )
        mask_path = resolve_path(
            row["mask_path"],
            project_root=project_root,
        )

        if not damaged_path.exists():
            raise FileNotFoundError(
                f"Damaged image not found for case {case_id}: {damaged_path}"
            )

        if not mask_path.exists():
            raise FileNotFoundError(
                f"Mask image not found for case {case_id}: {mask_path}"
            )

        staged_filename = f"{case_id}.png"
        staged_input_path = staging_input_dir / staged_filename
        staged_mask_path = staging_mask_dir / staged_filename
        staged_output_path = staging_output_dir / staged_filename

        _copy_image(damaged_path, staged_input_path)
        _copy_image(mask_path, staged_mask_path)

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

    staged_nonzero_df = pd.DataFrame(staged_rows)

    print("LaMa staging complete")
    print(f"  Staged non-zero rows: {len(staged_nonzero_df)}")
    print(f"  Staging input dir: {staging_input_dir}")
    print(f"  Staging mask dir: {staging_mask_dir}")
    print(f"  Staging output dir: {staging_output_dir}")

    return {
        "nonzero_staged_df": staged_nonzero_df,
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
    device: str = "cuda",
    executable: str = "iopaint",
    iopaint_model_name: str = IOPAINT_MODEL_NAME,
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    """Run IOPaint LaMa batch inference through subprocess."""
    staging_input_dir = Path(staging_input_dir)
    staging_mask_dir = Path(staging_mask_dir)
    staging_output_dir = Path(staging_output_dir)
    staging_logs_dir = ensure_directory(staging_logs_dir)

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

    print("Running IOPaint LaMa batch command:")
    print(" ".join(command))

    start_time = time.perf_counter()

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

    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=subprocess_env,
    )

    runtime_seconds = time.perf_counter() - start_time

    print(f"IOPaint LaMa finished with return code {completed.returncode}")
    print(f"IOPaint LaMa runtime: {runtime_seconds:.2f} seconds")

    command_log_path = staging_logs_dir / "iopaint_command.txt"
    stdout_log_path = staging_logs_dir / "iopaint_stdout.txt"
    stderr_log_path = staging_logs_dir / "iopaint_stderr.txt"

    command_log_path.write_text(" ".join(command), encoding="utf-8")
    stdout_log_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_log_path.write_text(completed.stderr or "", encoding="utf-8")

    print("IOPaint logs saved:")
    print(f"  Command: {command_log_path}")
    print(f"  Stdout:  {stdout_log_path}")
    print(f"  Stderr:  {stderr_log_path}")

    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "runtime_seconds": runtime_seconds,
        "command_log_path": str(command_log_path),
        "stdout_log_path": str(stdout_log_path),
        "stderr_log_path": str(stderr_log_path),
    }


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
    """Copy zero-control cases directly to the final restored output folder."""
    restored_output_dir = ensure_directory(restored_output_dir)

    output_rows: list[dict[str, Any]] = []
    total_zero = len(zero_control_df)

    print(f"Copying zero-control outputs directly: {total_zero} cases")

    for index, (_, row) in enumerate(zero_control_df.iterrows(), start=1):
        if progress_every and (
            index == 1
            or index % progress_every == 0
            or index == total_zero
        ):
            print(f"Copying zero-control LaMa output {index}/{total_zero}")

        case_id = str(row["case_id"])
        damaged_path = resolve_path(
            row["damaged_path"],
            project_root=project_root,
        )

        if not damaged_path.exists():
            raise FileNotFoundError(
                f"Zero-control damaged image not found for case {case_id}: {damaged_path}"
            )

        restored_filename = f"{case_id}_restored_{model_name}.png"
        restored_path = restored_output_dir / restored_filename

        _copy_image(damaged_path, restored_path)

        with Image.open(restored_path) as restored_image:
            restored_width, restored_height = restored_image.size
            restored_mode = restored_image.mode

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
                "lama_staged_input_path": "",
                "lama_staged_mask_path": "",
                "lama_staged_output_path": "",
                "device": device,
                "batch_runtime_seconds": 0.0,
                "restored_width": restored_width,
                "restored_height": restored_height,
                "restored_mode": restored_mode,
                "status": "ok",
                "issue": "zero_control copied without model inference",
            }
        )

        if output_row.get("mask_type") != zero_control_mask_type:
            raise ValueError(
                f"copy_zero_control_outputs received non-zero case: {case_id}"
            )

        output_rows.append(output_row)

    print("Zero-control copy complete")

    return pd.DataFrame(output_rows)


def collect_lama_batch_outputs(
    nonzero_staged_df: pd.DataFrame,
    *,
    staging_output_dir: Path | str,
    restored_output_dir: Path | str,
    project_root: Path | str | None = None,
    use_relative_paths: bool = True,
    model_name: str = MODEL_NAME,
    device: str = "cuda",
    batch_runtime_seconds: float | None = None,
    progress_every: int | None = 25,
) -> pd.DataFrame:
    """Collect IOPaint LaMa staged outputs into the final restored folder."""
    staging_output_dir = Path(staging_output_dir)
    restored_output_dir = ensure_directory(restored_output_dir)

    output_rows: list[dict[str, Any]] = []
    total_nonzero = len(nonzero_staged_df)

    print(f"Collecting LaMa model outputs: {total_nonzero} cases")

    for index, (_, row) in enumerate(nonzero_staged_df.iterrows(), start=1):
        if progress_every and (
            index == 1
            or index % progress_every == 0
            or index == total_nonzero
        ):
            print(f"Collecting LaMa output {index}/{total_nonzero}")

        case_id = str(row["case_id"])

        staged_output_path = staging_output_dir / f"{case_id}.png"
        restored_filename = f"{case_id}_restored_{model_name}.png"
        restored_path = restored_output_dir / restored_filename

        output_row = row.to_dict()

        if not staged_output_path.exists():
            output_row.update(
                {
                    "model_name": model_name,
                    "restoration_method": "iopaint_lama",
                    "inference_mode": "model_inference",
                    "restored_filename": restored_filename,
                    "restored_path": "",
                    "device": device,
                    "batch_runtime_seconds": batch_runtime_seconds,
                    "restored_width": np.nan,
                    "restored_height": np.nan,
                    "restored_mode": "",
                    "status": "error",
                    "issue": f"Missing staged LaMa output: {staged_output_path}",
                }
            )
            output_rows.append(output_row)
            continue

        _copy_image(staged_output_path, restored_path)

        with Image.open(restored_path) as restored_image:
            restored_width, restored_height = restored_image.size
            restored_mode = restored_image.mode

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
                "batch_runtime_seconds": batch_runtime_seconds,
                "restored_width": restored_width,
                "restored_height": restored_height,
                "restored_mode": restored_mode,
                "status": "ok",
                "issue": "",
            }
        )
        output_rows.append(output_row)

    print("LaMa output collection complete")

    return pd.DataFrame(output_rows)


def run_lama_restoration_pipeline(
    input_metadata_df: pd.DataFrame,
    *,
    restored_output_dir: Path | str,
    staging_root: Path | str,
    project_root: Path | str | None = None,
    device: str = "cuda",
    executable: str = "iopaint",
    model_name: str = MODEL_NAME,
    iopaint_model_name: str = IOPAINT_MODEL_NAME,
    use_relative_paths: bool = True,
    zero_control_mask_type: str = ZERO_CONTROL_MASK_TYPE,
    extra_iopaint_args: list[str] | None = None,
    progress_every: int | None = 25,
) -> dict[str, Any]:
    """Run the full LaMa restoration pipeline.

    Workflow:
    1. Stage non-zero cases into temporary matching filenames.
    2. Run IOPaint LaMa on staged non-zero cases.
    3. Collect restored non-zero outputs.
    4. Copy zero-control outputs directly.
    5. Return restoration metadata plus staging/run info.
    """
    restored_output_dir = ensure_directory(restored_output_dir)

    print("Starting LaMa restoration pipeline")
    print(f"  Input rows: {len(input_metadata_df)}")
    print(f"  Restored output dir: {restored_output_dir}")
    print(f"  Staging root: {staging_root}")
    print(f"  Device: {device}")
    print(f"  IOPaint executable: {executable}")
    print(f"  IOPaint model: {iopaint_model_name}")

    staging_info = prepare_lama_batch_staging(
        input_metadata_df,
        staging_root=staging_root,
        project_root=project_root,
        zero_control_mask_type=zero_control_mask_type,
        progress_every=progress_every,
    )

    nonzero_staged_df = staging_info["nonzero_staged_df"]
    zero_control_df = staging_info["zero_control_df"]

    if len(nonzero_staged_df) > 0:
        run_info = run_iopaint_lama_batch(
            staging_input_dir=staging_info["staging_input_dir"],
            staging_mask_dir=staging_info["staging_mask_dir"],
            staging_output_dir=staging_info["staging_output_dir"],
            staging_logs_dir=staging_info["staging_logs_dir"],
            device=device,
            executable=executable,
            iopaint_model_name=iopaint_model_name,
            extra_args=extra_iopaint_args,
        )

        if run_info["returncode"] != 0:
            raise RuntimeError(
                "IOPaint LaMa batch run failed.\n"
                f"Return code: {run_info['returncode']}\n"
                f"Command: {' '.join(run_info['command'])}\n"
                f"STDERR:\n{run_info['stderr']}"
            )

        inferred_df = collect_lama_batch_outputs(
            nonzero_staged_df,
            staging_output_dir=staging_info["staging_output_dir"],
            restored_output_dir=restored_output_dir,
            project_root=project_root,
            use_relative_paths=use_relative_paths,
            model_name=model_name,
            device=device,
            batch_runtime_seconds=run_info["runtime_seconds"],
            progress_every=progress_every,
        )
    else:
        run_info = {
            "command": [],
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "runtime_seconds": 0.0,
            "command_log_path": "",
            "stdout_log_path": "",
            "stderr_log_path": "",
            "skipped": True,
        }
        inferred_df = pd.DataFrame()

    zero_control_output_df = copy_zero_control_outputs(
        zero_control_df,
        restored_output_dir=restored_output_dir,
        project_root=project_root,
        use_relative_paths=use_relative_paths,
        model_name=model_name,
        device="none",
        zero_control_mask_type=zero_control_mask_type,
        progress_every=progress_every,
    )

    restoration_metadata_df = pd.concat(
        [inferred_df, zero_control_output_df],
        ignore_index=True,
    )

    if not restoration_metadata_df.empty:
        restoration_metadata_df = restoration_metadata_df.sort_values(
            ["painting_id", "mask_type"]
        ).reset_index(drop=True)

    print("LaMa restoration pipeline complete")
    print(f"  Output metadata rows: {len(restoration_metadata_df)}")
    if "inference_mode" in restoration_metadata_df.columns:
        print("  Inference mode counts:")
        print(restoration_metadata_df["inference_mode"].value_counts().to_string())
    if "status" in restoration_metadata_df.columns:
        print("  Status counts:")
        print(restoration_metadata_df["status"].value_counts().to_string())

    return {
        "restoration_metadata_df": restoration_metadata_df,
        "staging_info": staging_info,
        "run_info": run_info,
    }


def validate_lama_restoration_outputs(
    restoration_metadata_df: pd.DataFrame,
    *,
    project_root: Path | str | None = None,
    expected_size: tuple[int, int] | None = None,
    zero_control_mask_type: str = ZERO_CONTROL_MASK_TYPE,
    progress_every: int | None = 25,
) -> pd.DataFrame:
    """Validate restored LaMa outputs.

    Checks:
    - restored file exists,
    - restored image mode/size,
    - zero-control rows match damaged input exactly,
    - non-zero rows differ from damaged input.
    """
    required_columns = [
        "case_id",
        "mask_type",
        "damaged_path",
        "restored_path",
        "status",
    ]
    require_columns(
        restoration_metadata_df,
        required_columns,
        dataframe_name="restoration_metadata_df",
    )

    validation_rows: list[dict[str, Any]] = []
    total_rows = len(restoration_metadata_df)

    print(f"Validating LaMa restored outputs: {total_rows} rows")

    for index, (_, row) in enumerate(restoration_metadata_df.iterrows(), start=1):
        if progress_every and (
            index == 1
            or index % progress_every == 0
            or index == total_rows
        ):
            print(f"Validating LaMa output {index}/{total_rows}")

        case_id = str(row["case_id"])
        mask_type = str(row["mask_type"])

        damaged_path = resolve_path(
            row["damaged_path"],
            project_root=project_root,
        )
        restored_path = resolve_path(
            row["restored_path"],
            project_root=project_root,
        )

        damaged_exists = damaged_path.exists()
        restored_exists = restored_path.exists()

        restored_width = np.nan
        restored_height = np.nan
        restored_mode = ""
        exact_match_to_damaged = np.nan
        changed_from_damaged = np.nan
        max_abs_diff = np.nan
        mean_abs_diff = np.nan
        validation_passed = False
        validation_issue = ""

        if not damaged_exists:
            validation_issue = f"Missing damaged input: {damaged_path}"
        elif not restored_exists:
            validation_issue = f"Missing restored output: {restored_path}"
        else:
            with Image.open(damaged_path) as damaged_image:
                damaged_rgb = damaged_image.convert("RGB")
                damaged_array = np.array(damaged_rgb)

            with Image.open(restored_path) as restored_image:
                restored_width, restored_height = restored_image.size
                restored_mode = restored_image.mode
                restored_rgb = restored_image.convert("RGB")
                restored_array = np.array(restored_rgb)

            if damaged_array.shape != restored_array.shape:
                validation_issue = (
                    f"Shape mismatch damaged={damaged_array.shape}, "
                    f"restored={restored_array.shape}"
                )
            else:
                diff_array = np.abs(
                    restored_array.astype(np.int16)
                    - damaged_array.astype(np.int16)
                )
                max_abs_diff = float(diff_array.max())
                mean_abs_diff = float(diff_array.mean())

                exact_match_to_damaged = bool(max_abs_diff == 0.0)
                changed_from_damaged = bool(max_abs_diff > 0.0)

                size_ok = True
                if expected_size is not None:
                    size_ok = (restored_width, restored_height) == expected_size

                if expected_size is not None and not size_ok:
                    validation_issue = (
                        f"Unexpected restored size {(restored_width, restored_height)}; "
                        f"expected {expected_size}"
                    )
                elif mask_type == zero_control_mask_type:
                    validation_passed = exact_match_to_damaged
                    if not validation_passed:
                        validation_issue = (
                            "Zero-control restored image is not identical to damaged input."
                        )
                else:
                    validation_passed = changed_from_damaged
                    if not validation_passed:
                        validation_issue = (
                            "Non-zero restored image did not change from damaged input."
                        )

        validation_rows.append(
            {
                "case_id": case_id,
                "painting_id": row.get("painting_id", ""),
                "mask_type": mask_type,
                "status": row.get("status", ""),
                "damaged_exists": damaged_exists,
                "restored_exists": restored_exists,
                "restored_width": restored_width,
                "restored_height": restored_height,
                "restored_mode": restored_mode,
                "exact_match_to_damaged": exact_match_to_damaged,
                "changed_from_damaged": changed_from_damaged,
                "max_abs_diff": max_abs_diff,
                "mean_abs_diff": mean_abs_diff,
                "validation_passed": validation_passed,
                "validation_issue": validation_issue,
            }
        )

    validation_df = pd.DataFrame(validation_rows)

    print("LaMa validation complete")
    print(validation_df["validation_passed"].value_counts(dropna=False).to_string())

    failed_count = int((~validation_df["validation_passed"]).sum())
    if failed_count:
        print(f"Validation failures: {failed_count}")

    return validation_df


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
            "by_mask_type_df": empty_df,
            "by_inference_mode_df": empty_df,
        }

    overview_rows = [
        {
            "item": "total_rows",
            "value": len(restoration_metadata_df),
        },
        {
            "item": "unique_paintings",
            "value": restoration_metadata_df["painting_id"].nunique(),
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
                (restoration_metadata_df["inference_mode"] == "model_inference").sum()
            ),
        },
        {
            "item": "copied_zero_control_rows",
            "value": int(
                (restoration_metadata_df["inference_mode"] == "copied_zero_control").sum()
            ),
        },
    ]
    overview_df = pd.DataFrame(overview_rows)

    by_mask_type_df = (
        restoration_metadata_df
        .groupby("mask_type", dropna=False)
        .agg(
            cases=("case_id", "count"),
            successful_cases=("status", lambda values: int((values == "ok").sum())),
            error_cases=("status", lambda values: int((values != "ok").sum())),
            mean_batch_runtime_seconds=("batch_runtime_seconds", "mean"),
        )
        .reset_index()
        .round(5)
    )

    by_inference_mode_df = (
        restoration_metadata_df
        .groupby("inference_mode", dropna=False)
        .agg(
            cases=("case_id", "count"),
            successful_cases=("status", lambda values: int((values == "ok").sum())),
            error_cases=("status", lambda values: int((values != "ok").sum())),
        )
        .reset_index()
    )

    return {
        "overview_df": overview_df,
        "by_mask_type_df": by_mask_type_df,
        "by_inference_mode_df": by_inference_mode_df,
    }


__all__ = [
    "MODEL_NAME",
    "IOPAINT_MODEL_NAME",
    "ZERO_CONTROL_MASK_TYPE",
    "REQUIRED_INPUT_COLUMNS",
    "prepare_lama_batch_staging",
    "run_iopaint_lama_batch",
    "copy_zero_control_outputs",
    "collect_lama_batch_outputs",
    "run_lama_restoration_pipeline",
    "validate_lama_restoration_outputs",
    "summarize_lama_restoration_metadata",
]