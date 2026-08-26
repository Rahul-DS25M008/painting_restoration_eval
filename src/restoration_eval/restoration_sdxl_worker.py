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




# ---------------------------------------------------------------------------
# Persistent batch worker used by the v2 partial-evaluation contract.
# ---------------------------------------------------------------------------

BATCH_WORKER_VERSION = "2.0.0"


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Atomic JSON write with bounded Windows lock retries."""
    path.parent.mkdir(parents=True, exist_ok=True)
    last_error: OSError | None = None
    for number in range(1, 13):
        temporary = path.with_name(
            f"{path.name}.tmp.{os.getpid()}.{__import__('time').time_ns()}"
        )
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            os.replace(temporary, path)
            return
        except OSError as exc:
            last_error = exc
            if temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass
            if number < 12:
                __import__("time").sleep(0.25)
    raise PermissionError(f"Could not atomically replace {path}") from last_error


def _load_batch_job(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        job = json.load(handle)
    if job.get("job_schema_version") != "sdxl_batch_worker_job.v1":
        raise ValueError("Unsupported or missing SDXL batch-worker job schema")
    required = {
        "project_root", "notebook_output_root", "result_path",
        "checkpoint_path", "progress_path", "model", "memory_strategy",
        "execution", "candidates",
    }
    missing = sorted(required - set(job))
    if missing:
        raise ValueError(f"SDXL batch-worker job is missing keys: {missing}")
    if len(job["candidates"]) != 10:
        raise ValueError("The bounded SDXL worker requires exactly ten candidate rows")
    return job


def _sha256(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_checkpoint(rows: list[dict[str, Any]], path: Path, resolved: int) -> Path:
    """Write canonical checkpoint, falling back to a new immutable recovery file."""
    import pandas as pd
    from restoration_eval.schemas import SDXL_PARTIAL_CANDIDATE_COLUMNS

    frame = pd.DataFrame(rows).reindex(columns=SDXL_PARTIAL_CANDIDATE_COLUMNS)
    path.parent.mkdir(parents=True, exist_ok=True)
    last_error: OSError | None = None
    for number in range(1, 13):
        temporary = path.with_name(
            f"{path.name}.tmp.{os.getpid()}.{__import__('time').time_ns()}"
        )
        try:
            frame.to_csv(temporary, index=False)
            os.replace(temporary, path)
            return path
        except OSError as exc:
            last_error = exc
            if temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass
            if number < 12:
                __import__("time").sleep(0.25)
    recovery = path.with_name(f"{path.stem}.recovery_{resolved:02d}{path.suffix}")
    frame.to_csv(recovery, index=False)
    print(
        f"Canonical checkpoint was locked; recovery checkpoint written: {recovery}",
        flush=True,
    )
    if not recovery.is_file():
        raise PermissionError(f"Could not write SDXL checkpoint {path}") from last_error
    return recovery


def _write_progress(
    path: Path,
    *,
    status: str,
    resolved: int,
    total: int,
    current_candidate_id: str = "",
    case_started_epoch_seconds: float | None = None,
    latest_checkpoint_path: str = "",
    issue: str = "",
) -> None:
    _atomic_write_json(path, {
        "progress_schema_version": "sdxl_batch_progress.v1",
        "worker_version": BATCH_WORKER_VERSION,
        "status": status,
        "resolved_count": int(resolved),
        "total_count": int(total),
        "current_candidate_id": current_candidate_id,
        "case_started_epoch_seconds": case_started_epoch_seconds,
        "latest_checkpoint_path": latest_checkpoint_path,
        "updated_at_utc": _utc_now(),
        "issue": issue,
    })


def _load_persistent_pipeline(model: Mapping[str, Any], memory: Mapping[str, Any]):
    import torch
    from diffusers import DDIMScheduler, StableDiffusionXLInpaintPipeline

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable and CPU fallback is prohibited")
    if str(model["precision"]) != "float16":
        raise ValueError("The SDXL batch worker supports float16 only")
    torch.backends.cuda.matmul.allow_tf32 = bool(memory["allow_tf32"])
    torch.cuda.empty_cache()
    load_started = perf_counter()
    pipeline = StableDiffusionXLInpaintPipeline.from_pretrained(
        str(model["hf_model_id"]),
        revision=str(model["model_revision"]),
        torch_dtype=torch.float16,
        variant="fp16",
        use_safetensors=True,
        local_files_only=bool(model["local_files_only"]),
        safety_checker=None,
        requires_safety_checker=False,
    )
    if str(model["scheduler"]) != "DDIMScheduler":
        raise ValueError(f"Unsupported scheduler: {model['scheduler']}")
    pipeline.scheduler = DDIMScheduler.from_config(pipeline.scheduler.config)
    pipeline.set_progress_bar_config(disable=True)
    if bool(memory["attention_slicing"]):
        pipeline.enable_attention_slicing()
    if bool(memory["vae_slicing"]):
        pipeline.enable_vae_slicing()
    if bool(memory["vae_tiling"]):
        pipeline.enable_vae_tiling()
    if bool(memory["sequential_cpu_offload"]):
        pipeline.enable_sequential_cpu_offload()
    elif bool(memory["model_cpu_offload"]):
        pipeline.enable_model_cpu_offload()
    else:
        pipeline.to("cuda")
    return pipeline, torch, round(perf_counter() - load_started, 3)


def _prepare_batch_inputs(
    row: Mapping[str, Any],
    project_root: Path,
) -> tuple[Image.Image, Image.Image, np.ndarray, np.ndarray, Path, Path]:
    input_path = project_root / str(row["input_image_path"])
    mask_path = project_root / str(row["mask_or_effect_path"])
    if not input_path.is_file() or not mask_path.is_file():
        raise FileNotFoundError(f"Missing input or mask: {input_path} / {mask_path}")
    inference_size = (int(row["inference_width"]), int(row["inference_height"]))
    output_size = (int(row["output_width"]), int(row["output_height"]))
    with Image.open(input_path) as handle:
        source_output = handle.convert("RGB").resize(output_size, Image.Resampling.LANCZOS)
        source_inference = handle.convert("RGB").resize(
            inference_size, Image.Resampling.LANCZOS
        )
    with Image.open(mask_path) as handle:
        mask_output = handle.convert("L").resize(output_size, Image.Resampling.NEAREST)
        mask_inference = handle.convert("L").resize(
            inference_size, Image.Resampling.NEAREST
        )
    threshold = int(row["mask_threshold"])
    binary_inference = np.where(
        np.asarray(mask_inference, dtype=np.uint8) >= threshold, 255, 0
    ).astype(np.uint8)
    binary_output = np.where(
        np.asarray(mask_output, dtype=np.uint8) >= threshold, 255, 0
    ).astype(np.uint8)
    if int((binary_output > 0).sum()) == 0:
        raise ValueError("Mask is empty after the configured semantic threshold")
    return (
        source_inference,
        Image.fromarray(binary_inference, mode="L"),
        np.asarray(source_output, dtype=np.uint8),
        binary_output,
        input_path,
        mask_path,
    )


def _classify_batch_failure(exc: BaseException, phase: str) -> str:
    text = f"{type(exc).__name__}: {exc}".lower()
    if "out of memory" in text:
        return "cuda_out_of_memory"
    if "cuda is unavailable" in text:
        return "model_unavailable"
    if isinstance(exc, FileNotFoundError):
        return "input_validation_failure" if phase == "input" else "model_unavailable"
    if phase == "model_load":
        cache_markers = (
            "local_files_only", "not found in the cached files",
            "couldn't connect", "cannot find", "no such file",
            "does not appear to have a file",
        )
        if any(marker in text for marker in cache_markers):
            return "model_unavailable"
        return "model_load_failure"
    if phase == "inference":
        return "inference_failure"
    return "worker_failure"


def _mark_remaining_skipped(
    rows: list[dict[str, Any]],
    *,
    failure_type: str,
    issue: str,
) -> None:
    for row in rows:
        if str(row.get("status")) == "planned":
            row.update({
                "execution_action": "skipped",
                "status": "skipped",
                "failure_type": failure_type,
                "error_type": "",
                "error_message": "",
                "issue": issue,
            })


def execute_batch_job(job: Mapping[str, Any]) -> dict[str, Any]:
    """Load SDXL once and resolve the approved candidates in diversity-first order."""
    project_root = Path(str(job["project_root"]))
    checkpoint_path = Path(str(job["checkpoint_path"]))
    progress_path = Path(str(job["progress_path"]))
    rows = sorted(
        [dict(item) for item in job["candidates"]],
        key=lambda item: int(item["execution_order"]),
    )
    total = len(rows)
    execution = job["execution"]
    global_budget = float(execution["global_budget_seconds"])
    minimum_start = float(execution["minimum_seconds_to_start_case"])
    batch_started = perf_counter()
    resolved = sum(str(row.get("status")) != "planned" for row in rows)
    latest = _write_checkpoint(rows, checkpoint_path, resolved)
    _write_progress(
        progress_path, status="model_loading", resolved=resolved, total=total,
        latest_checkpoint_path=str(latest),
    )

    pipeline = None
    torch = None
    model_load_seconds = None
    stop_failure = ""
    stop_issue = ""
    try:
        pipeline, torch, model_load_seconds = _load_persistent_pipeline(
            job["model"], job["memory_strategy"]
        )
        print(f"SDXL persistent pipeline loaded in {model_load_seconds:.1f}s", flush=True)
    except Exception as exc:
        stop_failure = _classify_batch_failure(exc, "model_load")
        stop_issue = f"model_load: {type(exc).__name__}: {exc}"
        first = next((row for row in rows if str(row.get("status")) == "planned"), None)
        if first is not None:
            first.update({
                "execution_action": "failed",
                "device": "cuda",
                "model_load_seconds": model_load_seconds,
                "attempt_count": 1,
                "status": "failed",
                "failure_type": stop_failure,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "issue": "worker_phase=model_load",
            })
            resolved += 1

    if not stop_failure:
        for row in rows:
            if str(row.get("status")) != "planned":
                continue
            elapsed = perf_counter() - batch_started
            remaining = global_budget - elapsed
            if remaining < minimum_start:
                stop_failure = "not_started_global_budget"
                stop_issue = (
                    f"Remaining global budget {remaining:.1f}s was below the "
                    f"{minimum_start:.1f}s minimum required to start another case"
                )
                break
            candidate_id = str(row["candidate_id"])
            case_started_epoch = __import__("time").time()
            _write_progress(
                progress_path, status="running_case", resolved=resolved, total=total,
                current_candidate_id=candidate_id,
                case_started_epoch_seconds=case_started_epoch,
                latest_checkpoint_path=str(latest),
            )
            print(
                f"SDXL case {resolved + 1}/{total}: {row['case_id']} "
                f"(execution_order={row['execution_order']}, budget={remaining:.1f}s)",
                flush=True,
            )
            phase = "input"
            case_started = perf_counter()
            row.update({
                "device": "cuda",
                "budget_seconds_before_attempt": round(remaining, 3),
                "attempt_count": 1,
                "started_at_utc": _utc_now(),
            })
            try:
                (
                    source_inference, mask_inference, source_output, binary_output,
                    input_path, mask_path,
                ) = _prepare_batch_inputs(row, project_root)
                row["input_sha256"] = _sha256(input_path)
                row["mask_sha256"] = _sha256(mask_path)
                phase = "inference"
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
                before = int(torch.cuda.memory_allocated())
                inference_started = perf_counter()
                generator = torch.Generator(device="cpu").manual_seed(int(row["seed"]))
                with torch.inference_mode():
                    generated = pipeline(
                        prompt=str(row["prompt"]),
                        negative_prompt=str(row["negative_prompt"]),
                        image=source_inference,
                        mask_image=mask_inference,
                        num_inference_steps=int(row["num_inference_steps"]),
                        guidance_scale=float(row["guidance_scale"]),
                        strength=float(row["strength"]),
                        generator=generator,
                        height=int(row["inference_height"]),
                        width=int(row["inference_width"]),
                    ).images[0].convert("RGB")
                inference_seconds = round(perf_counter() - inference_started, 3)
                output_size = (int(row["output_width"]), int(row["output_height"]))
                if generated.size != output_size:
                    generated = generated.resize(output_size, Image.Resampling.LANCZOS)
                generated_array = np.asarray(generated, dtype=np.uint8)
                composite = np.where(
                    (binary_output > 0)[..., None], generated_array, source_output
                ).astype(np.uint8)
                outside_changed = int(
                    np.any(composite != source_output, axis=2)[binary_output == 0].sum()
                )
                output_path = project_root / str(row["restored_path"])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = output_path.with_name(
                    f"{output_path.stem}.tmp.{os.getpid()}.png"
                )
                Image.fromarray(composite, mode="RGB").save(
                    temporary, format="PNG", compress_level=6
                )
                os.replace(temporary, output_path)
                with Image.open(output_path) as check:
                    geometry_valid = check.mode == "RGB" and check.size == output_size
                technical = bool(geometry_valid and outside_changed == 0)
                if not technical:
                    raise RuntimeError(
                        "Output failed geometry or exact outside-mask preservation"
                    )
                after = int(torch.cuda.memory_allocated())
                peak = int(torch.cuda.max_memory_allocated())
                row.update({
                    "execution_action": "sdxl_inpaint",
                    "restored_sha256": _sha256(output_path),
                    "runtime_seconds": round(perf_counter() - case_started, 3),
                    "model_load_seconds": model_load_seconds if resolved == 0 else 0.0,
                    "inference_seconds": inference_seconds,
                    "gpu_total_memory_bytes": int(
                        torch.cuda.get_device_properties(0).total_memory
                    ),
                    "gpu_memory_before_bytes": before,
                    "gpu_memory_after_bytes": after,
                    "gpu_peak_memory_bytes": peak,
                    "budget_seconds_after_attempt": round(
                        max(0.0, global_budget - (perf_counter() - batch_started)), 3
                    ),
                    "output_geometry_valid": True,
                    "outside_mask_changed_pixels": outside_changed,
                    "technical_validation_passed": True,
                    "completed_at_utc": _utc_now(),
                    "status": "completed",
                    "failure_type": "none",
                    "worker_return_code": 0,
                    "error_type": "",
                    "error_message": "",
                    "issue": "",
                })
            except Exception as exc:
                failure = _classify_batch_failure(exc, phase)
                row.update({
                    "execution_action": "failed",
                    "runtime_seconds": round(perf_counter() - case_started, 3),
                    "model_load_seconds": model_load_seconds if resolved == 0 else 0.0,
                    "budget_seconds_after_attempt": round(
                        max(0.0, global_budget - (perf_counter() - batch_started)), 3
                    ),
                    "completed_at_utc": _utc_now(),
                    "status": "failed",
                    "failure_type": failure,
                    "worker_return_code": 2,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "issue": f"worker_phase={phase}",
                })
                if failure == "cuda_out_of_memory" and bool(execution["stop_after_cuda_oom"]):
                    stop_failure = failure
                    stop_issue = f"{candidate_id}: {type(exc).__name__}: {exc}"
                elif failure in {"model_unavailable", "model_load_failure"} and bool(
                    execution["stop_after_model_failure"]
                ):
                    stop_failure = failure
                    stop_issue = f"{candidate_id}: {type(exc).__name__}: {exc}"
            resolved += 1
            latest = _write_checkpoint(rows, checkpoint_path, resolved)
            _write_progress(
                progress_path, status="case_checkpointed", resolved=resolved, total=total,
                latest_checkpoint_path=str(latest),
            )
            print(
                f"SDXL progress: {resolved}/{total} rows resolved; "
                f"status={row['status']}; runtime={row.get('runtime_seconds')}s",
                flush=True,
            )
            if stop_failure:
                break

    if stop_failure:
        skip_type = (
            "not_started_global_budget"
            if stop_failure == "not_started_global_budget"
            else "skipped_after_guardrail"
        )
        _mark_remaining_skipped(rows, failure_type=skip_type, issue=stop_issue)
    valid_count = sum(
        str(row.get("status")) == "completed"
        and bool(row.get("technical_validation_passed"))
        for row in rows
    )
    availability = (
        "partial_evaluation" if valid_count
        else "unavailable" if stop_failure == "model_unavailable"
        else "failed" if stop_failure in {"model_load_failure", "worker_failure"}
        else "feasibility_only"
    )
    for row in rows:
        row["availability_state"] = availability
    resolved = sum(str(row.get("status")) != "planned" for row in rows)
    latest = _write_checkpoint(rows, checkpoint_path, resolved)
    _write_progress(
        progress_path, status="complete", resolved=resolved, total=total,
        latest_checkpoint_path=str(latest), issue=stop_issue,
    )
    return {
        "result_schema_version": "sdxl_batch_worker_result.v1",
        "worker_version": BATCH_WORKER_VERSION,
        "availability_state": availability,
        "resolved_count": resolved,
        "valid_completed_count": valid_count,
        "runtime_seconds": round(perf_counter() - batch_started, 3),
        "latest_checkpoint_path": str(latest),
        "stop_failure": stop_failure,
        "issue": stop_issue,
        "status": "completed" if resolved == total else "failed",
    }

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one isolated SDXL feasibility job")
    parser.add_argument("--job", required=True)
    parser.add_argument("--result", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result_path = Path(args.result)
    try:
        with Path(args.job).open("r", encoding="utf-8-sig") as handle:
            schema_version = json.load(handle).get("job_schema_version")
        if schema_version == "sdxl_batch_worker_job.v1":
            job = _load_batch_job(Path(args.job))
            result = execute_batch_job(job)
        else:
            job = _load_job(Path(args.job))
            result = execute_job(job)
    except Exception as exc:
        if "schema_version" in locals() and schema_version == "sdxl_batch_worker_job.v1":
            result = {
                "result_schema_version": "sdxl_batch_worker_result.v1",
                "worker_version": BATCH_WORKER_VERSION,
                "availability_state": "failed",
                "resolved_count": 0,
                "valid_completed_count": 0,
                "runtime_seconds": None,
                "latest_checkpoint_path": "",
                "stop_failure": "worker_failure",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "issue": "worker_phase=job_loading",
                "status": "failed",
            }
        else:
            result = _default_result("unknown")
            result.update({
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "issue": "worker_phase=job_loading",
            })
    _atomic_write_json(result_path, result)
    return 0 if result["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
