from pathlib import Path
import shutil
import time
from typing import Optional

import pandas as pd
from PIL import Image
import torch
from diffusers import StableDiffusionXLInpaintPipeline


MODEL_NAME = "sdxl_inpainting"
HF_MODEL_ID = "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"

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


def require_columns(df: pd.DataFrame, required_columns: list[str], context: str) -> None:
    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(f"{context} missing required columns: {missing_columns}")


def ensure_directory(path: Path, *, reset: bool = False) -> Path:
    path = Path(path)

    if reset and path.exists():
        shutil.rmtree(path)

    path.mkdir(parents=True, exist_ok=True)

    return path


def resolve_path(project_root: Path, path_value: str | Path) -> Path:
    path = Path(str(path_value))

    if path.is_absolute():
        return path

    return project_root / path


def to_storage_path(project_root: Path, path_value: str | Path) -> str:
    path = Path(path_value)

    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def get_device(prefer_cuda: bool = True) -> str:
    if prefer_cuda and torch.cuda.is_available():
        return "cuda"

    return "cpu"


def _load_rgb_image(path: Path, *, output_size: int) -> Image.Image:
    image = Image.open(path).convert("RGB")
    image = image.resize((output_size, output_size), Image.Resampling.LANCZOS)
    return image


def _load_mask_image(path: Path, *, output_size: int) -> Image.Image:
    mask = Image.open(path).convert("L")
    mask = mask.resize((output_size, output_size), Image.Resampling.NEAREST)
    return mask


def _prepare_inpaint_inputs(
    damaged_path: Path,
    mask_path: Path,
    *,
    inference_size: int,
) -> tuple[Image.Image, Image.Image]:
    damaged_image = _load_rgb_image(damaged_path, output_size=inference_size)
    mask_image = _load_mask_image(mask_path, output_size=inference_size)

    return damaged_image, mask_image


def _copy_image(source_path: Path, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)


def load_sdxl_inpaint_pipeline(
    *,
    model_id: str = HF_MODEL_ID,
    device: Optional[str] = None,
    use_cpu_offload: bool = True,
) -> StableDiffusionXLInpaintPipeline:
    if device is None:
        device = get_device(prefer_cuda=True)

    torch_dtype = torch.float16 if device == "cuda" else torch.float32

    pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
        model_id,
        torch_dtype=torch_dtype,
        variant="fp16" if device == "cuda" else None,
        use_safetensors=True,
    )

    pipe.set_progress_bar_config(disable=True)

    if hasattr(pipe, "enable_attention_slicing"):
        pipe.enable_attention_slicing()

    if hasattr(pipe, "enable_vae_slicing"):
        pipe.enable_vae_slicing()

    if hasattr(pipe, "enable_vae_tiling"):
        pipe.enable_vae_tiling()

    if device == "cuda" and use_cpu_offload:
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to(device)

    return pipe


def run_sdxl_single_case(
    *,
    pipe: StableDiffusionXLInpaintPipeline,
    damaged_path: Path,
    mask_path: Path,
    output_path: Path,
    prompt: str = DEFAULT_PROMPT,
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT,
    seed: int = 2026,
    num_inference_steps: int = 30,
    guidance_scale: float = 7.5,
    strength: float = 1.0,
    inference_size: int = 768,
    output_size: int = 768,
    device: Optional[str] = None,
) -> dict:
    if device is None:
        device = get_device(prefer_cuda=True)

    damaged_image, mask_image = _prepare_inpaint_inputs(
        damaged_path,
        mask_path,
        inference_size=inference_size,
    )

    generator_device = "cuda" if device == "cuda" and torch.cuda.is_available() else "cpu"
    generator = torch.Generator(device=generator_device).manual_seed(seed)

    start_time = time.time()

    with torch.inference_mode():
        result = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            image=damaged_image,
            mask_image=mask_image,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            strength=strength,
            generator=generator,
        )

    restored_image = result.images[0].convert("RGB")

    if restored_image.size != (output_size, output_size):
        restored_image = restored_image.resize(
            (output_size, output_size),
            Image.Resampling.LANCZOS,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    restored_image.save(output_path)

    elapsed_seconds = time.time() - start_time

    if device == "cuda":
        torch.cuda.empty_cache()

    return {
        "status": "ok",
        "inference_mode": "model_inference",
        "elapsed_seconds": elapsed_seconds,
        "seed": seed,
        "num_inference_steps": num_inference_steps,
        "guidance_scale": guidance_scale,
        "strength": strength,
        "inference_size": inference_size,
        "output_size": output_size,
    }


def run_sdxl_restoration_pipeline(
    *,
    damaged_metadata_path: Path,
    output_metadata_path: Path,
    output_dir: Path,
    project_root: Path,
    prompt: str = DEFAULT_PROMPT,
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT,
    seed: int = 2026,
    num_inference_steps: int = 30,
    guidance_scale: float = 7.5,
    strength: float = 1.0,
    inference_size: int = 768,
    output_size: int = 768,
    reset_output_dir: bool = False,
    progress_every: int = 10,
    use_cpu_offload: bool = True,
) -> pd.DataFrame:
    damaged_metadata_path = Path(damaged_metadata_path)
    output_metadata_path = Path(output_metadata_path)
    output_dir = ensure_directory(Path(output_dir), reset=reset_output_dir)
    project_root = Path(project_root)

    damaged_df = pd.read_csv(damaged_metadata_path)

    require_columns(
        damaged_df,
        [
            "case_id",
            "painting_id",
            "mask_id",
            "mask_type",
            "clean_path",
            "damaged_path",
            "mask_path",
        ],
        "Damaged metadata",
    )

    device = get_device(prefer_cuda=True)

    print("SDXL device:", device)
    print("SDXL model:", HF_MODEL_ID)
    print("Use CPU offload:", use_cpu_offload)
    print("Inference size:", inference_size)
    print("Output size:", output_size)

    pipe = load_sdxl_inpaint_pipeline(
        model_id=HF_MODEL_ID,
        device=device,
        use_cpu_offload=use_cpu_offload,
    )

    restored_rows = []
    total_rows = len(damaged_df)

    for index, row in damaged_df.iterrows():
        case_id = row["case_id"]
        mask_type = row["mask_type"]

        damaged_path = resolve_path(project_root, row["damaged_path"])
        mask_path = resolve_path(project_root, row["mask_path"])

        output_path = output_dir / f"{case_id}.png"

        output_row = row.to_dict()
        output_row["model_name"] = MODEL_NAME
        output_row["model_id"] = HF_MODEL_ID
        output_row["prompt"] = prompt
        output_row["negative_prompt"] = negative_prompt
        output_row["restored_path"] = to_storage_path(project_root, output_path)

        try:
            if mask_type == ZERO_CONTROL_MASK_TYPE:
                _copy_image(damaged_path, output_path)

                output_row.update(
                    {
                        "status": "ok",
                        "inference_mode": "copied_zero_control",
                        "elapsed_seconds": 0.0,
                        "seed": seed,
                        "num_inference_steps": 0,
                        "guidance_scale": 0.0,
                        "strength": 0.0,
                        "inference_size": output_size,
                        "output_size": output_size,
                    }
                )
            else:
                result_info = run_sdxl_single_case(
                    pipe=pipe,
                    damaged_path=damaged_path,
                    mask_path=mask_path,
                    output_path=output_path,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    seed=seed,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    strength=strength,
                    inference_size=inference_size,
                    output_size=output_size,
                    device=device,
                )

                output_row.update(result_info)

        except Exception as exc:
            output_row.update(
                {
                    "status": "error",
                    "error_message": repr(exc),
                    "inference_mode": "error",
                    "elapsed_seconds": None,
                    "seed": seed,
                    "num_inference_steps": num_inference_steps,
                    "guidance_scale": guidance_scale,
                    "strength": strength,
                    "inference_size": inference_size,
                    "output_size": output_size,
                }
            )

        restored_rows.append(output_row)

        if (index + 1) % progress_every == 0 or (index + 1) == total_rows:
            print(f"Processed {index + 1}/{total_rows} SDXL cases...")

    restored_df = pd.DataFrame(restored_rows)

    output_metadata_path.parent.mkdir(parents=True, exist_ok=True)
    restored_df.to_csv(output_metadata_path, index=False)

    print("Saved SDXL restoration metadata:", output_metadata_path)
    print("Rows:", len(restored_df))
    print("Status counts:")
    print(restored_df["status"].value_counts(dropna=False))

    return restored_df


def validate_sdxl_restoration_outputs(
    restoration_metadata: pd.DataFrame,
    *,
    project_root: Path,
    expected_rows: int = 250,
    expected_model_name: str = MODEL_NAME,
) -> pd.DataFrame:
    require_columns(
        restoration_metadata,
        [
            "case_id",
            "mask_type",
            "model_name",
            "restored_path",
            "status",
            "inference_mode",
        ],
        "SDXL restoration metadata",
    )

    validation_rows = []

    if len(restoration_metadata) != expected_rows:
        validation_rows.append(
            {
                "check": "expected_row_count",
                "status": "failed",
                "details": f"Expected {expected_rows}, found {len(restoration_metadata)}",
            }
        )
    else:
        validation_rows.append(
            {
                "check": "expected_row_count",
                "status": "passed",
                "details": f"Found {expected_rows} rows",
            }
        )

    unexpected_models = sorted(
        set(restoration_metadata["model_name"].dropna()) - {expected_model_name}
    )

    if unexpected_models:
        validation_rows.append(
            {
                "check": "model_name",
                "status": "failed",
                "details": f"Unexpected model names: {unexpected_models}",
            }
        )
    else:
        validation_rows.append(
            {
                "check": "model_name",
                "status": "passed",
                "details": expected_model_name,
            }
        )

    non_ok_rows = restoration_metadata[restoration_metadata["status"] != "ok"]

    if len(non_ok_rows) > 0:
        validation_rows.append(
            {
                "check": "status_ok",
                "status": "failed",
                "details": f"{len(non_ok_rows)} rows are not ok",
            }
        )
    else:
        validation_rows.append(
            {
                "check": "status_ok",
                "status": "passed",
                "details": "All rows ok",
            }
        )

    missing_files = []

    for path_value in restoration_metadata["restored_path"]:
        path = resolve_path(project_root, path_value)

        if not path.exists():
            missing_files.append(str(path))

    if missing_files:
        validation_rows.append(
            {
                "check": "restored_files_exist",
                "status": "failed",
                "details": f"Missing files: {missing_files[:10]}",
            }
        )
    else:
        validation_rows.append(
            {
                "check": "restored_files_exist",
                "status": "passed",
                "details": "All restored files exist",
            }
        )

    return pd.DataFrame(validation_rows)


def summarize_sdxl_restoration_metadata(
    restoration_metadata: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    summary_by_mask_type = (
        restoration_metadata
        .groupby("mask_type", dropna=False)
        .agg(
            cases=("case_id", "count"),
            ok_cases=("status", lambda values: int((values == "ok").sum())),
            mean_elapsed_seconds=("elapsed_seconds", "mean"),
        )
        .reset_index()
        .sort_values("mask_type")
    )

    summary_by_inference_mode = (
        restoration_metadata
        .groupby("inference_mode", dropna=False)
        .agg(
            cases=("case_id", "count"),
            mean_elapsed_seconds=("elapsed_seconds", "mean"),
        )
        .reset_index()
        .sort_values("inference_mode")
    )

    return {
        "summary_by_mask_type": summary_by_mask_type,
        "summary_by_inference_mode": summary_by_inference_mode,
    }