"""Isolated official-MAT batch worker for Notebook 37."""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import random
import sys
from time import perf_counter
from typing import Any, Mapping

import numpy as np
from PIL import Image

from restoration_eval.hint_mat_selection import (
    CANDIDATE_COLUMNS,
    atomic_write_csv,
    atomic_write_json,
    calculate_file_sha256,
    exact_mask_composite,
    load_resumable_candidate_records,
    prepare_model_inputs,
    utc_now_iso,
    validate_restored_output,
)


WORKER_VERSION = "1.0.2"


def _load_job(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        job = json.load(handle)
    if job.get("job_schema_version") != "hint_mat_worker_job.v1":
        raise ValueError("Unsupported MAT worker job schema")
    if job.get("model_key") != "mat":
        raise ValueError("The MAT worker received a non-MAT job")
    return job


def _load_generator(repo: Path, checkpoint: Path, device: Any) -> tuple[Any, float]:
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    import dnnlib
    import legacy

    started = perf_counter()
    with dnnlib.util.open_url(str(checkpoint)) as handle:
        generator = legacy.load_network_pkl(handle)["G_ema"].to(device).eval().requires_grad_(False)
    return generator, round(perf_counter() - started, 3)


def _infer(
    generator: Any,
    row: Mapping[str, Any],
    job: Mapping[str, Any],
    device: Any,
) -> tuple[np.ndarray, dict[str, Any]]:
    import torch

    size = int(job["model"]["inference_size"])
    image, retained_mask, _, _ = prepare_model_inputs(
        row["input_image_path"], row["mask_path"], inference_size=size,
        mat_mask_semantics=True,
    )
    image_tensor = (
        torch.from_numpy(image.transpose(2, 0, 1).copy()).float().unsqueeze(0).to(device) / 127.5 - 1.0
    )
    mask_tensor = torch.from_numpy(retained_mask.copy()).float().unsqueeze(0).unsqueeze(0).to(device)
    rng = np.random.RandomState(int(job["model"]["seed"]))
    latent = torch.from_numpy(rng.randn(1, generator.z_dim)).float().to(device)
    label = torch.zeros([1, generator.c_dim], device=device)
    captured_stdout = StringIO()
    captured_stderr = StringIO()
    with redirect_stdout(captured_stdout), redirect_stderr(captured_stderr):
        with torch.inference_mode():
            output = generator(
                image_tensor, mask_tensor, latent, label,
                truncation_psi=float(job["model"]["truncation_psi"]),
                noise_mode=str(job["model"]["noise_mode"]),
            )
    stdout_text = captured_stdout.getvalue()
    stderr_text = captured_stderr.getvalue()
    diagnostics = stdout_text + "\n" + stderr_text
    audit = {
        "optional_extension_fallback_used": "Failed!" in diagnostics,
        "captured_stdout_line_count": len(stdout_text.splitlines()),
        "captured_stderr_line_count": len(stderr_text.splitlines()),
    }
    result = (
        output[0].detach().permute(1, 2, 0).mul(127.5).add(127.5)
        .round().clamp(0, 255).byte().cpu().numpy()
    )
    return result, audit


def execute_job(job: Mapping[str, Any]) -> dict[str, Any]:
    import pandas as pd
    import torch

    repo = Path(str(job["repository_path"]))
    checkpoint = Path(str(job["checkpoint_path"]))
    if not repo.is_dir() or not checkpoint.is_file():
        raise FileNotFoundError("MAT repository or checkpoint is unavailable")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable and CPU fallback is not authorized")
    seed = int(job["model"]["seed"])
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    device = torch.device("cuda")
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    generator, model_load_seconds = _load_generator(repo, checkpoint, device)

    rows = [dict(item) for item in job["candidates"]]
    records_by_id = load_resumable_candidate_records(job)
    optional_extension_fallback_cases = 0
    captured_diagnostic_lines = 0
    started_all = perf_counter()
    total = len(rows)
    executed_count = 0
    for number, row in enumerate(rows, start=1):
        candidate_id = str(row["candidate_id"])
        if candidate_id in records_by_id:
            resumed = records_by_id[candidate_id]
            print(
                f"MAT progress {number}/{total}: {row['case_id']} -> "
                f"resumed_{resumed.get('status', 'unknown')}",
                flush=True,
            )
            continue
        executed_count += 1
        row["started_at_utc"] = utc_now_iso()
        row["actual_device"] = "cuda"
        row["model_load_seconds"] = model_load_seconds if executed_count == 1 else 0.0
        case_started = perf_counter()
        try:
            inference_started = perf_counter()
            generated, inference_audit = _infer(generator, row, job, device)
            optional_fallback = bool(
                inference_audit["optional_extension_fallback_used"]
            )
            optional_extension_fallback_cases += int(optional_fallback)
            captured_diagnostic_lines += int(
                inference_audit["captured_stdout_line_count"]
                + inference_audit["captured_stderr_line_count"]
            )
            row["inference_seconds"] = round(perf_counter() - inference_started, 3)
            size = int(job["model"]["inference_size"])
            _, _, missing_768, source_768 = prepare_model_inputs(
                row["input_image_path"], row["mask_path"], inference_size=size,
                mat_mask_semantics=True,
            )
            composite = exact_mask_composite(generated, source_768, missing_768)
            output_path = Path(str(row["restored_path"]))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(composite, mode="RGB").save(output_path, format="PNG", compress_level=6)
            technical = validate_restored_output(
                output_path, row["input_image_path"], row["mask_path"]
            )
            row.update(technical)
            row["restored_sha256"] = calculate_file_sha256(output_path)
            row["output_width"] = int(composite.shape[1])
            row["output_height"] = int(composite.shape[0])
            row["runtime_seconds"] = round(perf_counter() - case_started, 3)
            row["gpu_peak_memory_bytes"] = int(torch.cuda.max_memory_allocated())
            row["generator_name"] = type(generator).__name__
            row["issue"] = (
                "optional_cuda_extension_build_failed_pytorch_fallback_used"
                if optional_fallback
                else ""
            )
            row["status"] = "completed" if technical["technical_validation_passed"] else "failed"
            row["failure_type"] = "none" if row["status"] == "completed" else "technical_validation"
        except Exception as exc:
            row.update(
                {
                    "runtime_seconds": round(perf_counter() - case_started, 3),
                    "status": "failed",
                    "failure_type": "cuda_out_of_memory" if "out of memory" in str(exc).lower() else "inference_failure",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )
        row["completed_at_utc"] = utc_now_iso()
        row["generator_version"] = WORKER_VERSION
        records_by_id[candidate_id] = row
        ordered_records = [
            records_by_id[str(item["candidate_id"])]
            for item in rows
            if str(item["candidate_id"]) in records_by_id
        ]
        frame = pd.DataFrame(ordered_records).reindex(columns=CANDIDATE_COLUMNS)
        atomic_write_csv(frame, job["checkpoint_path_csv"])
        atomic_write_json(
            job["progress_path"],
            {
                "model_key": "mat", "completed_cases": len(records_by_id), "total_cases": total,
                "successful_cases": sum(
                    item.get("status") == "completed"
                    for item in records_by_id.values()
                ),
                "updated_at_utc": utc_now_iso(),
            },
        )
        print(f"MAT progress {number}/{total}: {row['case_id']} -> {row['status']}", flush=True)
        if row["status"] != "completed" and bool(job["execution"]["stop_after_model_failure"]):
            break
        if float(row["runtime_seconds"] or 0) > float(job["execution"]["per_case_timeout_seconds"]):
            break

    payload = {
        "result_schema_version": "hint_mat_worker_result.v1",
        "worker_version": WORKER_VERSION,
        "model_key": "mat",
        "model_load_seconds": model_load_seconds,
        "actual_inference_size": int(job["model"]["inference_size"]),
        "runtime_seconds": round(perf_counter() - started_all, 3),
        "completed_rows": len(records_by_id),
        "successful_rows": sum(
            item.get("status") == "completed"
            for item in records_by_id.values()
        ),
        "resumed_rows": len(records_by_id) - executed_count,
        "optional_extension_fallback_cases": optional_extension_fallback_cases,
        "captured_diagnostic_lines": captured_diagnostic_lines,
        "status": "completed" if len(records_by_id) == total and all(
            item.get("status") == "completed"
            for item in records_by_id.values()
        ) else "failed",
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
        print(f"MAT worker failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
