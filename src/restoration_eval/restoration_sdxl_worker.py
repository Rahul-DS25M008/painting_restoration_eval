"""Isolated SDXL worker invoked by the Notebook 12 parent watchdog."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from time import perf_counter
from typing import Any, Mapping

import numpy as np
from PIL import Image


WORKER_VERSION = "1.0.0"


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _load_job(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        job = json.load(handle)
    if job.get("job_schema_version") != "sdxl_worker_job.v1":
        raise ValueError("Unsupported or missing SDXL worker job schema")
    required = {
        "attempt_id", "input_path", "mask_path", "output_path", "hf_model_id",
        "model_revision", "local_files_only", "precision", "scheduler", "prompt",
        "negative_prompt", "seed", "num_inference_steps", "guidance_scale",
        "strength", "inference_width", "inference_height", "output_width",
        "output_height", "mask_threshold", "compositing_policy",
        "safety_checker_policy", "model_cpu_offload", "sequential_cpu_offload",
        "attention_slicing", "vae_slicing", "vae_tiling", "allow_tf32",
    }
    missing = sorted(required - set(job))
    if missing:
        raise ValueError(f"SDXL worker job is missing keys: {missing}")
    return job


def _default_result(attempt_id: str) -> dict[str, Any]:
    return {
        "result_schema_version": "sdxl_worker_result.v1",
        "worker_version": WORKER_VERSION,
        "attempt_id": attempt_id,
        "actual_device": "",
        "gpu_name": "",
        "gpu_total_memory_bytes": None,
        "model_load_succeeded": False,
        "inference_started": False,
        "inference_completed": False,
        "timed_out": False,
        "output_generated": False,
        "output_geometry_valid": False,
        "outside_mask_changed_pixels": None,
        "technical_validation_passed": False,
        "model_load_seconds": None,
        "inference_seconds": None,
        "gpu_peak_memory_bytes": None,
        "status": "failed",
        "failure_type": "worker_failure",
        "error_type": "",
        "error_message": "",
        "issue": "",
    }


def _classify_failure(exc: BaseException, *, phase: str) -> str:
    text = f"{type(exc).__name__}: {exc}".lower()
    if "out of memory" in text or "cuda error: out of memory" in text:
        return "cuda_out_of_memory"
    if "cuda is unavailable" in text:
        return "model_unavailable"
    if isinstance(exc, FileNotFoundError):
        return "input_validation_failure" if phase == "input_validation" else "model_unavailable"
    if phase == "model_load":
        cache_markers = (
            "local_files_only", "not found in the cached files", "couldn't connect",
            "cannot find", "no such file", "does not appear to have a file",
        )
        if any(marker in text for marker in cache_markers):
            return "model_unavailable"
        return "model_load_failure"
    if phase == "inference":
        return "inference_failure"
    return "worker_failure"


def _prepare_inputs(job: Mapping[str, Any]) -> tuple[Image.Image, Image.Image, np.ndarray, np.ndarray]:
    input_path = Path(str(job["input_path"]))
    mask_path = Path(str(job["mask_path"]))
    if not input_path.is_file():
        raise FileNotFoundError(f"Input image is missing: {input_path}")
    if not mask_path.is_file():
        raise FileNotFoundError(f"Mask image is missing: {mask_path}")
    inference_size = (int(job["inference_width"]), int(job["inference_height"]))
    output_size = (int(job["output_width"]), int(job["output_height"]))
    with Image.open(input_path) as source_handle:
        source_output = source_handle.convert("RGB").resize(output_size, Image.Resampling.LANCZOS)
        source_inference = source_handle.convert("RGB").resize(
            inference_size, Image.Resampling.LANCZOS
        )
    with Image.open(mask_path) as mask_handle:
        mask_output = mask_handle.convert("L").resize(output_size, Image.Resampling.NEAREST)
        mask_inference = mask_handle.convert("L").resize(
            inference_size, Image.Resampling.NEAREST
        )
    threshold = int(job["mask_threshold"])
    mask_inference_array = np.asarray(mask_inference, dtype=np.uint8)
    binary_inference = np.where(mask_inference_array >= threshold, 255, 0).astype(np.uint8)
    mask_output_array = np.asarray(mask_output, dtype=np.uint8)
    binary_output = np.where(mask_output_array >= threshold, 255, 0).astype(np.uint8)
    if int((binary_output > 0).sum()) == 0:
        raise ValueError("The feasibility mask is empty after thresholding")
    return (
        source_inference,
        Image.fromarray(binary_inference, mode="L"),
        np.asarray(source_output, dtype=np.uint8),
        binary_output,
    )


def execute_job(job: Mapping[str, Any]) -> dict[str, Any]:
    """Load the pinned pipeline, run one probe, and technically validate it."""
    result = _default_result(str(job["attempt_id"]))
    phase = "input_validation"
    try:
        source_inference, mask_inference, source_output, binary_output = _prepare_inputs(job)

        phase = "model_load"
        print("SDXL worker phase: model_load", flush=True)
        import torch
        from diffusers import DDIMScheduler, StableDiffusionXLInpaintPipeline

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is unavailable and CPU fallback is prohibited")
        if str(job["precision"]) != "float16":
            raise ValueError("The SDXL worker supports the pinned float16 policy only")
        result.update(
            {
                "actual_device": "cuda",
                "gpu_name": str(torch.cuda.get_device_name(0)),
                "gpu_total_memory_bytes": int(torch.cuda.get_device_properties(0).total_memory),
            }
        )
        torch.backends.cuda.matmul.allow_tf32 = bool(job["allow_tf32"])
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        load_started = perf_counter()
        pipeline = StableDiffusionXLInpaintPipeline.from_pretrained(
            str(job["hf_model_id"]),
            revision=str(job["model_revision"]),
            torch_dtype=torch.float16,
            variant="fp16",
            use_safetensors=True,
            local_files_only=bool(job["local_files_only"]),
            safety_checker=None,
            requires_safety_checker=False,
        )
        if str(job["scheduler"]) != "DDIMScheduler":
            raise ValueError(f"Unsupported scheduler: {job['scheduler']}")
        pipeline.scheduler = DDIMScheduler.from_config(pipeline.scheduler.config)
        pipeline.set_progress_bar_config(disable=True)
        if bool(job["attention_slicing"]):
            pipeline.enable_attention_slicing()
        if bool(job["vae_slicing"]):
            pipeline.enable_vae_slicing()
        if bool(job["vae_tiling"]):
            pipeline.enable_vae_tiling()
        if bool(job["sequential_cpu_offload"]):
            pipeline.enable_sequential_cpu_offload()
        elif bool(job["model_cpu_offload"]):
            pipeline.enable_model_cpu_offload()
        else:
            pipeline.to("cuda")
        result["model_load_seconds"] = round(perf_counter() - load_started, 3)
        result["model_load_succeeded"] = True

        phase = "inference"
        result["inference_started"] = True
        print("SDXL worker phase: inference", flush=True)
        generator = torch.Generator(device="cpu").manual_seed(int(job["seed"]))
        inference_started = perf_counter()
        with torch.inference_mode():
            generated = pipeline(
                prompt=str(job["prompt"]),
                negative_prompt=str(job["negative_prompt"]),
                image=source_inference,
                mask_image=mask_inference,
                num_inference_steps=int(job["num_inference_steps"]),
                guidance_scale=float(job["guidance_scale"]),
                strength=float(job["strength"]),
                generator=generator,
                height=int(job["inference_height"]),
                width=int(job["inference_width"]),
            ).images[0].convert("RGB")
        result["inference_seconds"] = round(perf_counter() - inference_started, 3)
        result["inference_completed"] = True

        output_size = (int(job["output_width"]), int(job["output_height"]))
        if generated.size != output_size:
            generated = generated.resize(output_size, Image.Resampling.LANCZOS)
        generated_array = np.asarray(generated, dtype=np.uint8)
        composite = np.where((binary_output > 0)[..., None], generated_array, source_output)
        outside_changed = int(
            np.any(composite != source_output, axis=2)[binary_output == 0].sum()
        )
        output_path = Path(str(job["output_path"]))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(composite.astype(np.uint8), mode="RGB").save(
            output_path, format="PNG", compress_level=6
        )
        with Image.open(output_path) as check:
            geometry_valid = check.size == output_size and check.mode == "RGB"
        result.update(
            {
                "output_generated": output_path.is_file(),
                "output_geometry_valid": bool(geometry_valid),
                "outside_mask_changed_pixels": outside_changed,
                "technical_validation_passed": bool(
                    output_path.is_file() and geometry_valid and outside_changed == 0
                ),
                "gpu_peak_memory_bytes": int(torch.cuda.max_memory_allocated()),
                "status": "completed",
                "failure_type": "none",
            }
        )
        if not result["technical_validation_passed"]:
            result.update(
                {
                    "status": "failed",
                    "failure_type": "inference_failure",
                    "error_type": "TechnicalValidationError",
                    "error_message": "Generated output failed geometry or outside-mask validation",
                }
            )
        print("SDXL worker phase: complete", flush=True)
        return result
    except Exception as exc:
        result.update(
            {
                "status": "failed",
                "failure_type": _classify_failure(exc, phase=phase),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "issue": f"worker_phase={phase}",
            }
        )
        try:
            import torch

            if torch.cuda.is_available():
                result["gpu_peak_memory_bytes"] = int(torch.cuda.max_memory_allocated())
        except Exception:
            pass
        return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one isolated SDXL feasibility job")
    parser.add_argument("--job", required=True)
    parser.add_argument("--result", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result_path = Path(args.result)
    try:
        job = _load_job(Path(args.job))
        result = execute_job(job)
    except Exception as exc:
        result = _default_result("unknown")
        result.update(
            {
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "issue": "worker_phase=job_loading",
            }
        )
    _atomic_write_json(result_path, result)
    return 0 if result["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
