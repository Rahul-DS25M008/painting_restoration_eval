"""Isolated full-benchmark HINT worker for Notebook 12A."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from time import perf_counter, sleep
from typing import Any, Mapping

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.hint_mat_selection import (
    calculate_file_sha256,
    exact_mask_composite,
    prepare_model_inputs,
    validate_restored_output,
)
from restoration_eval.restoration_hint import (
    HINT_WORK_COLUMNS,
    atomic_write_csv,
    atomic_write_json,
    utc_now_iso,
)


WORKER_VERSION = "1.0.1"


def _load_job(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        job = json.load(handle)
    if job.get("job_schema_version") != "hint_production_worker_job.v1":
        raise ValueError("Unsupported production-HINT worker job schema")
    return job


def _load_generator(
    repository: Path, checkpoint: Path, device: Any,
) -> tuple[Any, dict[str, Any]]:
    import torch

    if str(repository) not in sys.path:
        sys.path.insert(0, str(repository))
    from src.networks import HINT

    started = perf_counter()
    generator = HINT().to(device).eval().requires_grad_(False)
    try:
        payload = torch.load(checkpoint, map_location=device, weights_only=False)
    except TypeError:
        payload = torch.load(checkpoint, map_location=device)
    state = payload.get("generator", payload) if isinstance(payload, Mapping) else payload
    if not isinstance(state, Mapping):
        raise TypeError("The HINT checkpoint has no generator state mapping")
    normalized = {
        (str(key)[7:] if str(key).startswith("module.") else str(key)): value
        for key, value in state.items()
    }
    incompatibility = generator.load_state_dict(normalized, strict=False)
    model_keys = len(generator.state_dict())
    matched = model_keys - len(incompatibility.missing_keys)
    if matched <= 0:
        raise ValueError("No HINT generator weights matched the architecture")
    return generator, {
        "model_load_seconds": round(perf_counter() - started, 3),
        "matched_state_keys": matched,
        "model_state_key_count": model_keys,
        "missing_state_keys": len(incompatibility.missing_keys),
        "unexpected_state_keys": len(incompatibility.unexpected_keys),
    }


def _infer(
    generator: Any, row: Mapping[str, Any], device: Any,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    import torch
    import torch.nn.functional as torch_f

    threshold = int(row["mask_threshold"])
    image, missing, missing_768, source_768 = prepare_model_inputs(
        row["input_image_path"], row["mask_path"],
        inference_size=768, mask_threshold=threshold,
    )
    image_tensor = (
        torch.from_numpy(image.transpose(2, 0, 1).copy())
        .float().unsqueeze(0).to(device) / 255.0
    )
    mask_tensor = (
        torch.from_numpy(missing.copy()).float()
        .unsqueeze(0).unsqueeze(0).to(device)
    )
    masked = image_tensor * (1.0 - mask_tensor) + mask_tensor
    mask_half = torch_f.interpolate(mask_tensor, scale_factor=0.5, mode="nearest")
    mask_quarter = torch_f.interpolate(mask_tensor, scale_factor=0.25, mode="nearest")
    mask_tiny = torch_f.interpolate(mask_tensor, scale_factor=0.125, mode="nearest")
    with torch.inference_mode():
        output = generator(masked, mask_tensor, mask_half, mask_quarter, mask_tiny)
    generated = (
        output[0].detach().clamp(0, 1).mul(255).round().byte()
        .permute(1, 2, 0).cpu().numpy()
    )
    return generated, missing_768, source_768


def _load_resume(job: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if not bool(job["execution"].get("resume_enabled", False)):
        return {}
    checkpoint = Path(str(job["checkpoint_path_csv"]))
    if not checkpoint.is_file():
        return {}
    frame = pd.read_csv(checkpoint, keep_default_na=False)
    allowed = {str(row["candidate_id"]) for row in job["candidates"]}
    retain_failed = not bool(
        job["execution"].get("retry_failed_attempts", False)
    )
    retained: dict[str, dict[str, Any]] = {}
    for record in frame.to_dict("records"):
        candidate_id = str(record.get("candidate_id", ""))
        status = str(record.get("status", ""))
        if candidate_id not in allowed:
            continue
        if status == "failed" and retain_failed:
            retained[candidate_id] = record
            continue
        if status != "completed":
            continue
        output = Path(str(record.get("restored_path", "")))
        if output.is_file() and str(record.get("restored_sha256", "")):
            if calculate_file_sha256(output) == str(record["restored_sha256"]):
                retained[candidate_id] = record
    return retained


def _save_rgb(array: np.ndarray, path: Path, compress_level: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.png")
    try:
        Image.fromarray(array.astype(np.uint8), mode="RGB").save(
            temporary, format="PNG", compress_level=compress_level
        )
        for attempt in range(8):
            try:
                os.replace(temporary, path)
                return
            except PermissionError:
                if attempt == 7:
                    raise
                sleep(0.15 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


def execute_job(job: Mapping[str, Any]) -> dict[str, Any]:
    import torch

    repository = Path(str(job["repository_path"]))
    checkpoint = Path(str(job["checkpoint_path"]))
    if not repository.is_dir() or not checkpoint.is_file():
        raise FileNotFoundError("The pinned HINT source or checkpoint is unavailable")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable and CPU fallback is prohibited")

    seed = int(job["model"]["seed"])
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    device = torch.device("cuda")
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    generator, load_audit = _load_generator(repository, checkpoint, device)

    atomic_write_json(job["progress_path"], {
        "stage": "model_loaded",
        "resolved_cases": 0,
        "total_cases": len(job["candidates"]),
        "successful_cases": 0,
        "updated_at_utc": utc_now_iso(),
    })

    rows = [dict(item) for item in job["candidates"]]
    records = _load_resume(job)
    resumed_count = len(records)
    progress_interval = int(job["execution"]["progress_interval_cases"])
    checkpoint_interval = int(job["execution"]["checkpoint_interval_cases"])
    compress_level = int(job["execution"]["png_compress_level"])
    started_all = perf_counter()

    for number, row in enumerate(rows, start=1):
        candidate_id = str(row["candidate_id"])
        if candidate_id in records:
            atomic_write_json(job["progress_path"], {
                "stage": "case_resolved",
                "resolved_cases": number,
                "total_cases": len(rows),
                "successful_cases": sum(
                    item.get("status") == "completed" for item in records.values()
                ),
                "current_case_id": str(row["case_id"]),
                "updated_at_utc": utc_now_iso(),
            })
            if number % progress_interval == 0 or number == len(rows):
                print(f"HINT progress {number}/{len(rows)}: resumed", flush=True)
            continue

        row["started_at_utc"] = utc_now_iso()
        row["model_load_seconds"] = load_audit["model_load_seconds"] if not records else 0.0
        case_started = perf_counter()
        output_path = Path(str(row["restored_path"]))
        try:
            if str(row["execution_action"]) == "identity_noop":
                with Image.open(row["input_image_path"]) as handle:
                    composite = np.asarray(handle.convert("RGB"), dtype=np.uint8)
                inference_seconds = 0.0
            else:
                inference_started = perf_counter()
                generated, missing_768, source_768 = _infer(generator, row, device)
                inference_seconds = round(perf_counter() - inference_started, 3)
                composite = exact_mask_composite(generated, source_768, missing_768)
            _save_rgb(composite, output_path, compress_level)
            technical = validate_restored_output(
                output_path, row["input_image_path"], row["mask_path"],
                mask_threshold=int(row["mask_threshold"]),
            )
            row.update(technical)
            row["restored_sha256"] = calculate_file_sha256(output_path)
            row["inference_seconds"] = inference_seconds
            row["runtime_seconds"] = round(perf_counter() - case_started, 3)
            row["gpu_peak_memory_bytes"] = int(torch.cuda.max_memory_allocated())
            row["completed_at_utc"] = utc_now_iso()
            row["status"] = "completed" if technical["technical_validation_passed"] else "failed"
            row["failure_type"] = "none" if row["status"] == "completed" else "technical_validation"
        except Exception as exc:
            row.update({
                "runtime_seconds": round(perf_counter() - case_started, 3),
                "completed_at_utc": utc_now_iso(), "status": "failed",
                "failure_type": "cuda_out_of_memory" if "out of memory" in str(exc).lower() else "inference_failure",
                "error_type": type(exc).__name__, "error_message": str(exc),
                "issue": "production_worker_failure",
            })
        row["generator_version"] = WORKER_VERSION
        records[candidate_id] = row

        resolved = [
            records[str(item["candidate_id"])]
            for item in rows if str(item["candidate_id"]) in records
        ]
        should_checkpoint = (
            number % checkpoint_interval == 0
            or number == len(rows)
            or row["status"] != "completed"
        )
        if should_checkpoint:
            atomic_write_csv(
                pd.DataFrame(resolved).reindex(columns=HINT_WORK_COLUMNS),
                job["checkpoint_path_csv"],
            )
        atomic_write_json(job["progress_path"], {
            "stage": "case_resolved",
            "resolved_cases": len(resolved), "total_cases": len(rows),
            "successful_cases": sum(item["status"] == "completed" for item in resolved),
            "current_case_id": str(row["case_id"]),
            "updated_at_utc": utc_now_iso(),
        })
        if number % progress_interval == 0 or number == len(rows) or row["status"] != "completed":
            print(
                f"HINT progress {number}/{len(rows)}: {row['case_id']} -> {row['status']}",
                flush=True,
            )
        if row["status"] != "completed" and bool(job["execution"]["stop_after_model_failure"]):
            break
        if float(row["runtime_seconds"] or 0) > float(job["execution"]["per_case_timeout_seconds"]):
            break

    payload = {
        "result_schema_version": "hint_production_worker_result.v1",
        "worker_version": WORKER_VERSION,
        "model_load_audit": load_audit,
        "runtime_seconds": round(perf_counter() - started_all, 3),
        "resolved_rows": len(records),
        "successful_rows": sum(item.get("status") == "completed" for item in records.values()),
        "resumed_rows": resumed_count,
        "status": "completed" if len(records) == len(rows) and all(
            item.get("status") == "completed" for item in records.values()
        ) else "partial_or_failed",
        "completed_at_utc": utc_now_iso(),
    }
    atomic_write_json(job["result_path"], payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    args = parser.parse_args()
    try:
        result = execute_job(_load_job(Path(args.job)))
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 0 if result["status"] == "completed" else 1
    except Exception as exc:
        print(f"HINT worker failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
