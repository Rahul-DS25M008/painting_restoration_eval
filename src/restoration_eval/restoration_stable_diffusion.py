from __future__ import annotations

import gc
import shutil
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from diffusers import StableDiffusionInpaintPipeline
from PIL import Image


MODEL_NAME = "stable_diffusion_inpainting"
HF_MODEL_ID = "runwayml/stable-diffusion-inpainting"
ZERO_CONTROL_MASK_TYPE = "zero_control"

DEFAULT_PROMPT = (
    "restore the missing damaged area of the painting, preserve the original style, "
    "colors, brushwork, composition, and surrounding visual context"
)

DEFAULT_NEGATIVE_PROMPT = (
    "modern objects, text, watermark, signature, frame, border, people added, "
    "face changed, extra objects, oversharpened, cartoon, digital art, "
    "photorealistic, unrealistic texture"
)

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


def _load_rgb_image(path: Path) -> Image.Image:
    """Load an RGB image."""
    if not path.exists():
        raise FileNotFoundError(f"Missing image file: {path}")

    return Image.open(path).convert("RGB")


def _load_mask_image(path: Path) -> Image.Image:
    """Load a single-channel inpainting mask."""
    if not path.exists():
        raise FileNotFoundError(f"Missing mask file: {path}")

    return Image.open(path).convert("L")


def _prepare_inpaint_inputs(
    damaged_path: Path,
    mask_path: Path,
    *,
    inference_size: int,
) -> tuple[Image.Image, Image.Image, tuple[int, int]]:
    """Load and resize damaged image and mask for Stable Diffusion inpainting."""
    damaged_image = _load_rgb_image(damaged_path)
    mask_image = _load_mask_image(mask_path)

    original_size = damaged_image.size

    damaged_resized = damaged_image.resize(
        (inference_size, inference_size),
        resample=Image.Resampling.LANCZOS,
    )

    mask_resized = mask_image.resize(
        (inference_size, inference_size),
        resample=Image.Resampling.NEAREST,
    )

    # Stable Diffusion inpainting expects white mask pixels to be repainted.
    mask_resized = mask_resized.point(lambda value: 255 if value > 0 else 0)

    return damaged_resized, mask_resized, original_size


def get_device(prefer_cuda: bool = True) -> str:
    """Return the selected torch device string."""
    if prefer_cuda and torch.cuda.is_available():
        return "cuda"

    return "cpu"


def load_stable_diffusion_inpaint_pipeline(
    *,
    model_id: str = HF_MODEL_ID,
    device: str = "cuda",
    torch_dtype: torch.dtype | None = None,
    enable_attention_slicing: bool = True,
    disable_safety_checker: bool = True,
) -> StableDiffusionInpaintPipeline:
    """Load a Stable Diffusion inpainting pipeline with memory-conscious defaults."""
    if torch_dtype is None:
        torch_dtype = torch.float16 if device == "cuda" else torch.float32

    print("Loading Stable Diffusion inpainting pipeline")
    print(f"  Model id: {model_id}")
    print(f"  Device: {device}")
    print(f"  Torch dtype: {torch_dtype}")

    pipe = StableDiffusionInpaintPipeline.from_pretrained(
        model_id,
        torch_dtype=torch_dtype,
    )

    if disable_safety_checker:
        # The dataset consists of artworks. The safety checker can replace
        # legitimate painting outputs with black images, which would confound
        # restoration evaluation.
        pipe.safety_checker = None
        pipe.requires_safety_checker = False

    if enable_attention_slicing:
        pipe.enable_attention_slicing()

    pipe = pipe.to(device)
    pipe.set_progress_bar_config(disable=True)

    print("Stable Diffusion inpainting pipeline loaded")

    return pipe


def run_stable_diffusion_single_case(
    row: pd.Series,
    *,
    pipe: StableDiffusionInpaintPipeline,
    restored_output_dir: Path | str,
    project_root: Path | str | None = None,
    use_relative_paths: bool = True,
    model_name: str = MODEL_NAME,
    prompt: str = DEFAULT_PROMPT,
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT,
    seed: int = 2026,
    num_inference_steps: int = 30,
    guidance_scale: float = 7.5,
    inference_size: int = 512,
    device: str = "cuda",
) -> dict[str, Any]:
    """Run Stable Diffusion inpainting for one non-zero restoration case."""
    restored_output_dir = ensure_directory(restored_output_dir)

    case_id = str(row["case_id"])

    damaged_path = resolve_path(
        row["damaged_path"],
        project_root=project_root,
    )
    mask_path = resolve_path(
        row["mask_path"],
        project_root=project_root,
    )

    restored_filename = f"{case_id}_restored_{model_name}.png"
    restored_path = restored_output_dir / restored_filename

    output_row = row.to_dict()

    try:
        damaged_resized, mask_resized, original_size = _prepare_inpaint_inputs(
            damaged_path,
            mask_path,
            inference_size=inference_size,
        )

        generator = torch.Generator(device=device).manual_seed(seed)

        start_time = time.perf_counter()

        with torch.inference_mode():
            result = pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                image=damaged_resized,
                mask_image=mask_resized,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator,
            )

        runtime_seconds = time.perf_counter() - start_time

        restored_image = result.images[0].convert("RGB")

        if restored_image.size != original_size:
            restored_image = restored_image.resize(
                original_size,
                resample=Image.Resampling.LANCZOS,
            )

        restored_path.parent.mkdir(parents=True, exist_ok=True)
        restored_image.save(restored_path)

        restored_width, restored_height = restored_image.size
        restored_mode = restored_image.mode

        output_row.update(
            {
                "model_name": model_name,
                "restoration_method": "stable_diffusion_inpainting",
                "hf_model_id": HF_MODEL_ID,
                "inference_mode": "model_inference",
                "restored_filename": restored_filename,
                "restored_path": to_storage_path(
                    restored_path,
                    project_root=project_root,
                    use_relative_paths=use_relative_paths,
                ),
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "seed": seed,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "inference_size": inference_size,
                "device": device,
                "case_runtime_seconds": runtime_seconds,
                "restored_width": restored_width,
                "restored_height": restored_height,
                "restored_mode": restored_mode,
                "status": "ok",
                "issue": "",
            }
        )

    except Exception as error:
        output_row.update(
            {
                "model_name": model_name,
                "restoration_method": "stable_diffusion_inpainting",
                "hf_model_id": HF_MODEL_ID,
                "inference_mode": "model_inference",
                "restored_filename": restored_filename,
                "restored_path": "",
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "seed": seed,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "inference_size": inference_size,
                "device": device,
                "case_runtime_seconds": np.nan,
                "restored_width": np.nan,
                "restored_height": np.nan,
                "restored_mode": "",
                "status": "error",
                "issue": repr(error),
            }
        )

    return output_row


def copy_zero_control_outputs(
    zero_control_df: pd.DataFrame,
    *,
    restored_output_dir: Path | str,
    project_root: Path | str | None = None,
    use_relative_paths: bool = True,
    model_name: str = MODEL_NAME,
    device: str = "none",
    zero_control_mask_type: str = ZERO_CONTROL_MASK_TYPE,
    prompt: str = DEFAULT_PROMPT,
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT,
    seed: int = 2026,
    num_inference_steps: int = 30,
    guidance_scale: float = 7.5,
    inference_size: int = 512,
    progress_every: int | None = 25,
) -> pd.DataFrame:
    """Copy zero-control cases directly to the final restored output folder."""
    restored_output_dir = ensure_directory(restored_output_dir)

    output_rows: list[dict[str, Any]] = []
    total_zero = len(zero_control_df)

    print(f"Copying Stable Diffusion zero-control outputs directly: {total_zero} cases")

    for index, (_, row) in enumerate(zero_control_df.iterrows(), start=1):
        if progress_every and (
            index == 1
            or index % progress_every == 0
            or index == total_zero
        ):
            print(f"Copying zero-control Stable Diffusion output {index}/{total_zero}")

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
                "hf_model_id": HF_MODEL_ID,
                "inference_mode": "copied_zero_control",
                "restored_filename": restored_filename,
                "restored_path": to_storage_path(
                    restored_path,
                    project_root=project_root,
                    use_relative_paths=use_relative_paths,
                ),
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "seed": seed,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "inference_size": inference_size,
                "device": device,
                "case_runtime_seconds": 0.0,
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

    print("Stable Diffusion zero-control copy complete")

    return pd.DataFrame(output_rows)


def run_stable_diffusion_restoration_pipeline(
    input_metadata_df: pd.DataFrame,
    *,
    restored_output_dir: Path | str,
    project_root: Path | str | None = None,
    pipe: StableDiffusionInpaintPipeline | None = None,
    device: str = "cuda",
    model_id: str = HF_MODEL_ID,
    model_name: str = MODEL_NAME,
    prompt: str = DEFAULT_PROMPT,
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT,
    seed: int = 2026,
    num_inference_steps: int = 30,
    guidance_scale: float = 7.5,
    inference_size: int = 512,
    use_relative_paths: bool = True,
    zero_control_mask_type: str = ZERO_CONTROL_MASK_TYPE,
    disable_safety_checker: bool = True,
    progress_every: int | None = 25,
    clear_cuda_cache_every: int | None = 25,
) -> dict[str, Any]:
    """Run the full Stable Diffusion restoration pipeline.

    Workflow:
    1. Filter valid rows.
    2. Run diffusion inpainting for non-zero cases.
    3. Copy zero-control outputs directly.
    4. Return restoration metadata and run information.
    """
    require_columns(
        input_metadata_df,
        REQUIRED_INPUT_COLUMNS,
        dataframe_name="input_metadata_df",
    )

    restored_output_dir = ensure_directory(restored_output_dir)

    working_df = input_metadata_df.copy()

    if "status" in working_df.columns:
        working_df = working_df[working_df["status"] == "ok"].copy()

    nonzero_df = working_df[
        working_df["mask_type"] != zero_control_mask_type
    ].copy()

    zero_control_df = working_df[
        working_df["mask_type"] == zero_control_mask_type
    ].copy()

    print("Starting Stable Diffusion restoration pipeline")
    print(f"  Input rows: {len(input_metadata_df)}")
    print(f"  Valid working rows: {len(working_df)}")
    print(f"  Non-zero model inference rows: {len(nonzero_df)}")
    print(f"  Zero-control copy rows: {len(zero_control_df)}")
    print(f"  Restored output dir: {restored_output_dir}")
    print(f"  Device: {device}")
    print(f"  Model id: {model_id}")
    print(f"  Prompt: {prompt}")
    print(f"  Negative prompt: {negative_prompt}")
    print(f"  Seed: {seed}")
    print(f"  Steps: {num_inference_steps}")
    print(f"  Guidance scale: {guidance_scale}")
    print(f"  Inference size: {inference_size}")

    owns_pipe = pipe is None

    if pipe is None and len(nonzero_df) > 0:
        pipe = load_stable_diffusion_inpaint_pipeline(
            model_id=model_id,
            device=device,
            disable_safety_checker=disable_safety_checker,
        )

    output_rows: list[dict[str, Any]] = []
    total_nonzero = len(nonzero_df)

    start_time = time.perf_counter()

    for index, (_, row) in enumerate(nonzero_df.iterrows(), start=1):
        if progress_every and (
            index == 1
            or index % progress_every == 0
            or index == total_nonzero
        ):
            print(f"Running Stable Diffusion case {index}/{total_nonzero}")

        output_row = run_stable_diffusion_single_case(
            row,
            pipe=pipe,
            restored_output_dir=restored_output_dir,
            project_root=project_root,
            use_relative_paths=use_relative_paths,
            model_name=model_name,
            prompt=prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            inference_size=inference_size,
            device=device,
        )

        output_rows.append(output_row)

        if (
            device == "cuda"
            and clear_cuda_cache_every
            and index % clear_cuda_cache_every == 0
        ):
            torch.cuda.empty_cache()

    inferred_df = pd.DataFrame(output_rows)

    zero_control_output_df = copy_zero_control_outputs(
        zero_control_df,
        restored_output_dir=restored_output_dir,
        project_root=project_root,
        use_relative_paths=use_relative_paths,
        model_name=model_name,
        device="none",
        zero_control_mask_type=zero_control_mask_type,
        prompt=prompt,
        negative_prompt=negative_prompt,
        seed=seed,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        inference_size=inference_size,
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

    total_runtime_seconds = time.perf_counter() - start_time

    if owns_pipe and pipe is not None:
        del pipe
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()

    run_info = {
        "model_id": model_id,
        "model_name": model_name,
        "device": device,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "seed": seed,
        "num_inference_steps": num_inference_steps,
        "guidance_scale": guidance_scale,
        "inference_size": inference_size,
        "total_runtime_seconds": total_runtime_seconds,
        "nonzero_rows": len(nonzero_df),
        "zero_control_rows": len(zero_control_df),
    }

    print("Stable Diffusion restoration pipeline complete")
    print(f"  Output metadata rows: {len(restoration_metadata_df)}")
    print(f"  Total runtime seconds: {total_runtime_seconds:.2f}")

    if "inference_mode" in restoration_metadata_df.columns:
        print("  Inference mode counts:")
        print(restoration_metadata_df["inference_mode"].value_counts().to_string())

    if "status" in restoration_metadata_df.columns:
        print("  Status counts:")
        print(restoration_metadata_df["status"].value_counts().to_string())

    return {
        "restoration_metadata_df": restoration_metadata_df,
        "run_info": run_info,
    }


def validate_stable_diffusion_restoration_outputs(
    restoration_metadata_df: pd.DataFrame,
    *,
    project_root: Path | str | None = None,
    expected_size: tuple[int, int] | None = None,
    zero_control_mask_type: str = ZERO_CONTROL_MASK_TYPE,
    progress_every: int | None = 25,
) -> pd.DataFrame:
    """Validate restored Stable Diffusion outputs.

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

    print(f"Validating Stable Diffusion restored outputs: {total_rows} rows")

    for index, (_, row) in enumerate(restoration_metadata_df.iterrows(), start=1):
        if progress_every and (
            index == 1
            or index % progress_every == 0
            or index == total_rows
        ):
            print(f"Validating Stable Diffusion output {index}/{total_rows}")

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

    print("Stable Diffusion validation complete")
    print(validation_df["validation_passed"].value_counts(dropna=False).to_string())

    failed_count = int((~validation_df["validation_passed"]).sum())
    if failed_count:
        print(f"Validation failures: {failed_count}")

    return validation_df


def summarize_stable_diffusion_restoration_metadata(
    restoration_metadata_df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Build compact summary tables for Stable Diffusion restoration metadata."""
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
        {
            "item": "mean_case_runtime_seconds",
            "value": float(
                restoration_metadata_df.loc[
                    restoration_metadata_df["inference_mode"] == "model_inference",
                    "case_runtime_seconds",
                ].mean()
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
            mean_case_runtime_seconds=("case_runtime_seconds", "mean"),
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
            mean_case_runtime_seconds=("case_runtime_seconds", "mean"),
        )
        .reset_index()
        .round(5)
    )

    return {
        "overview_df": overview_df,
        "by_mask_type_df": by_mask_type_df,
        "by_inference_mode_df": by_inference_mode_df,
    }


__all__ = [
    "MODEL_NAME",
    "HF_MODEL_ID",
    "ZERO_CONTROL_MASK_TYPE",
    "DEFAULT_PROMPT",
    "DEFAULT_NEGATIVE_PROMPT",
    "REQUIRED_INPUT_COLUMNS",
    "get_device",
    "load_stable_diffusion_inpaint_pipeline",
    "run_stable_diffusion_single_case",
    "copy_zero_control_outputs",
    "run_stable_diffusion_restoration_pipeline",
    "validate_stable_diffusion_restoration_outputs",
    "summarize_stable_diffusion_restoration_metadata",
]