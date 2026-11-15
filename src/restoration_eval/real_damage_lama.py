"""D04 LaMa orchestration using the unchanged N10 IOPaint command and compositor.

Only orchestration differs: immutable job directories, per-image receipts and
recoverable raw PNGs. Timing belongs to a command group, not an individual image.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import subprocess
from time import perf_counter, sleep
from typing import Callable
from uuid import uuid4

import cv2
import numpy as np
import pandas as pd
from PIL import Image, UnidentifiedImageError
import psutil
import yaml

from . import real_damage_restoration as d04
from . import real_damage_telea as prior
from . import real_damage_readiness as readiness
from . import restoration_lama as lama
from .manifests import sha256_file, utc_now_iso
from .paths import resolve_repo_path, to_repo_relative
from .real_damage_dataset import audit_inventory_inputs
from .validation import ValidationCollector

MODULE_VERSION = "1.0.0"
STAGE = "batch_4_lama"
MODEL = "lama"
_read, _save, _path = prior._read, prior._save, prior._path


def _check(ctx, key, description, passed, observed, expected=True):
    # A user may rerun a display/smoke/validation cell in the same kernel.
    checks = ValidationCollector()
    checks.extend(c for c in ctx["validation"].checks if (c.validation_stage, c.check_id) != (STAGE, key))
    checks.add(validation_stage=STAGE, check_id=key, check_description=description,
               passed=passed, observed=observed, expected=expected, severity="blocking")
    ctx["validation"] = checks


def prepare_lama(project_root: str | Path, config_path: str | Path) -> dict:
    """Read-only preflight. No model loading, inference or upstream writes."""
    root = Path(project_root).resolve()
    path = resolve_repo_path(config_path, root, must_exist=True)
    policy = yaml.safe_load(path.read_text(encoding="utf-8"))
    d04._require(policy["schema_version"] == "real_damage_lama_config.v1" and policy["stage"] == STAGE
        and policy["expected_candidates"] == 10 and policy["smoke_repeats"] == 2
        and policy["overwrite_unverified_outputs"] is False and policy["checkpoint_after_each_candidate"] is True,
        "Unexpected LaMa stage policy")
    for rel in [policy["helper_source"], policy["tests"], policy["telea_config"], policy["baseline_config"], *policy["outputs"].values()]:
        d04._relative(rel)
    upstream = prior.prepare_telea(root, policy["telea_config"])
    output = upstream["output_root"]
    telea_summary = _read(output / "work/telea/batch_summary.json")
    d04._require(telea_summary["completed_candidates"] == 10 and telea_summary["failed_candidates"] == 0
        and telea_summary["execution_fingerprint"] == upstream["execution_fingerprint"]
        and telea_summary["validation_summary"]["passed_count"] == 95
        and telea_summary["validation_summary"]["check_count"] == 95, "Batch 3 has not passed")
    declared = {"stage_config": path, "stage_helper": root / policy["helper_source"],
        "stage_tests": root / policy["tests"], "telea_summary": output / "work/telea/batch_summary.json",
        "telea_checks": output / "work/telea/checks.csv"}
    table = pd.read_csv(output / upstream["config"]["outputs"]["candidates"], keep_default_na=False, float_precision="round_trip")
    for row in upstream["worklist"].to_dict("records"):
        receipt = output / f"work/telea/receipts/primary/{row['candidate_id']}.json"
        saved = _read(receipt)
        binding = d04._digest(dict(execution=upstream["execution_fingerprint"], candidate=row, scope="primary"))
        image, mask = prior._inputs(upstream, row)
        prior._verify_record(upstream, row, root / saved["restored_path"], saved, binding, image, mask)
        current = table.loc[table.candidate_id.eq(row["candidate_id"])]
        d04._require(len(current) == 1 and all(current.iloc[0][k] == saved[k]
            for k in ("model_id", "status", "restored_path", "restored_sha256", "execution_binding")), "Telea table/receipt mismatch")
        declared[f"telea_receipt.{row['painting_id']}"] = receipt
    baseline = lama.load_lama_config(root / policy["baseline_config"])
    plan = upstream["plan"]
    worklist = plan.loc[plan.model_id.eq(MODEL)].sort_values("painting_id").reset_index(drop=True)
    d04._require(len(worklist) == 10 and worklist.candidate_id.is_unique and worklist.painting_id.nunique() == 10
        and worklist.candidate_role.eq("primary").all() and worklist.mask_threshold.eq(128).all()
        and worklist.model_config_sha256.eq(sha256_file(root / policy["baseline_config"])).all()
        and not worklist.has_clean_reference.any() and worklist.clean_image_path.eq("").all(), "Incorrect frozen LaMa population/settings")
    environment = lama.get_lama_runtime_environment(baseline, project_root=root)
    lama.validate_lama_runtime_environment(environment)
    frozen_env = _read(output / "work/readiness/runtime_environment.json")["lama"]
    for key in ("iopaint_version", "torch_version", "cuda_runtime_version", "effective_device", "model_artifact_sha256", "model_revision"):
        d04._require(environment[key] == frozen_env[key], f"LaMa runtime differs from Batch 2: {key}")
    d04._require(environment["effective_device"] == "cuda" and not environment["cpu_fallback_used"], "LaMa requires the baseline CUDA execution")
    inventory, audit = audit_inventory_inputs(root, root / upstream["config"]["inputs"]["inventory"],
        root / upstream["config"]["inputs"]["inventory_run"], declared)
    checks = ValidationCollector()
    saved_checks = pd.read_csv(output / "work/telea/checks.csv", keep_default_na=False)
    d04._require(len(saved_checks) == 95 and saved_checks.passed.all(), "Saved Batch 3 validation is incomplete")
    for row in saved_checks.to_dict("records"):
        checks.add(**row)
    inputs = {to_repo_relative(p, root): sha256_file(p) for p in declared.values()}
    ctx = dict(root=root, output_root=output, config=upstream["config"], policy=policy, baseline=baseline,
        frozen=upstream["frozen"], worklist=worklist, validation=checks, environment=environment,
        inventory=inventory, stage_input_checksums=inputs, frozen_input_checksums=upstream["frozen_input_checksums"])
    ctx["execution_fingerprint"] = d04._digest(dict(stage_inputs=inputs, telea_execution=upstream["execution_fingerprint"],
        readiness=ctx["frozen"]["readiness_fingerprint"], environment={k: environment[k] for k in
        ("iopaint_version", "torch_version", "cuda_runtime_version", "effective_device", "model_artifact_sha256")}, module_version=MODULE_VERSION))
    _check(ctx, "telea_handoff", "Ten Telea receipts, images and table rows retain their bindings", True, 10, 10)
    _check(ctx, "lama_population", "Ten frozen LaMa primary candidates; no clean references", True, len(worklist), 10)
    _check(ctx, "lama_runtime", "Cached checkpoint and CUDA runtime match Batch 2", True, environment["model_artifact_sha256"])
    _check(ctx, "baseline_pipeline", "N10 config, 768px input, binary mask and compositor are retained", True, baseline["model"]["configuration_id"])
    _check(ctx, "stage_inventory", "Inventory covers new LaMa files and immutable Telea handoff", bool(audit.passed.all()), audit.loc[~audit.passed].to_dict("records"), [])
    ctx["validation"].raise_for_blocking()
    return ctx


def _assert_inputs(ctx):
    for rel, digest in {**ctx["frozen_input_checksums"], **ctx["stage_input_checksums"]}.items():
        d04._require(sha256_file(ctx["root"] / rel) == digest, f"Frozen/stage input changed: {rel}")
    env = ctx["environment"]
    d04._require(sha256_file(Path(env["model_artifact_path"])) == env["model_artifact_sha256"], "LaMa checkpoint changed")


def _inputs(ctx, row):
    image, mask = prior._inputs(ctx, row)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB), mask


def _locations(ctx, row, scope):
    d04._require(scope in ("primary", "smoke_1", "smoke_2"), "Unknown inference scope")
    relative = row["restored_path"] if scope == "primary" else f"work/lama/{scope}/{row['candidate_id']}.png"
    return _path(ctx, relative), _path(ctx, f"work/lama/receipts/{scope}/{row['candidate_id']}.json")


def _binding(ctx, row, scope):
    return d04._digest(dict(execution=ctx["execution_fingerprint"], candidate=row, scope=scope))


def _verify(ctx, row, record, scope):
    image, mask = _inputs(ctx, row)
    output, _ = _locations(ctx, row, scope)
    prior._verify_record(ctx, row, output, record, _binding(ctx, row, scope), cv2.cvtColor(image, cv2.COLOR_RGB2BGR), mask)
    raw = resolve_repo_path(record["raw_output_path"], ctx["root"], must_exist=True)
    d04._require(sha256_file(raw) == record["raw_output_sha256"], "Raw inference checksum mismatch")


def _merge_table(path, frame):
    if path.exists():
        existing = pd.read_csv(path, keep_default_na=False, float_precision="round_trip")
        other = existing.loc[existing.model_id.ne(MODEL)]
        frame = pd.DataFrame([*other.to_dict("records"), *frame.to_dict("records")])
    key = "candidate_id" if "candidate_id" in frame else "model_id"
    d04._require(frame[key].is_unique, "Duplicate IDs in accumulated table")
    _save(path, frame)


def _jobs(ctx):
    index = _path(ctx, "work/lama/job_index.json")
    paths = _read(index)["job_paths"] if index.exists() else []
    result = []
    for rel in paths:
        job = _read(_path(ctx, rel))
        d04._require(job["execution_fingerprint"] == ctx["execution_fingerprint"], "Previous LaMa job belongs to changed inputs/code")
        pid = job.get("pid")
        if pid and job["status"] == "running":
            try:
                process = psutil.Process(pid)
                d04._require(abs(process.create_time() - job["process_created_at"]) > .01 or not process.is_running(),
                    "Previous LaMa process is still running; wait for it before resuming")
            except psutil.NoSuchProcess:
                pass
        result.append(job)
    return result


def _collect(ctx, row, staged, job, scope):
    """Checkpoint a complete raw PNG. In-progress PNGs are left for the next poll."""
    output, receipt = _locations(ctx, row, scope)
    if receipt.exists():
        record = _read(receipt)
        _verify(ctx, row, record, scope)
        return record
    raw = Path(staged["raw_output_path"])
    # Reject a job index that points outside its owned raw-output directory.
    raw.resolve().relative_to(_path(ctx, job["directory"]).resolve())
    if not raw.is_file():
        return None
    try:
        with Image.open(raw) as pil:
            pil.load()
            d04._require(pil.mode == "RGB", "IOPaint output must be RGB")
            inferred = np.asarray(pil).copy()
    except (OSError, UnidentifiedImageError):
        return None
    image, mask = _inputs(ctx, row)
    restored = lama.masked_composite(image, inferred, mask)
    technical = prior._technical(image, mask, restored)
    d04._require(technical["changed_outside_pixels"] == 0, "LaMa changed pixels outside mask")
    buffer = BytesIO()
    Image.fromarray(restored).save(buffer, format="PNG", compress_level=ctx["baseline"]["execution"]["png_compress_level"])
    content = buffer.getvalue()
    d04._require(not output.exists() or output.read_bytes() == content, "Unverified existing image differs from its saved raw inference")
    if not output.exists():
        readiness._atomic(output, content)
    env = ctx["environment"]
    record = dict(row, schema_version="real_damage_candidates.v1", status="completed", runtime_status="inference_validated",
        execution_action="iopaint_lama_masked_composite", execution_scope=scope, execution_binding=_binding(ctx, row, scope),
        execution_fingerprint=ctx["execution_fingerprint"], readiness_fingerprint=ctx["frozen"]["readiness_fingerprint"],
        restored_path=to_repo_relative(output, ctx["root"]), restored_sha256=sha256_file(output),
        raw_output_path=to_repo_relative(raw, ctx["root"]), raw_output_sha256=sha256_file(raw),
        command_group_id=job["job_id"], runtime_seconds="", runtime_measurement="see_command_group_wall_time_including_startup",
        model_artifact_sha256=env["model_artifact_sha256"], iopaint_version=env["iopaint_version"], torch_version=env["torch_version"],
        effective_device=env["effective_device"], adapter_version=MODULE_VERSION,
        completed_at_utc=utc_now_iso(), issue="", **technical)
    _save(receipt, record)
    _verify(ctx, row, record, scope)
    return record


def _run_command(ctx, staged, job, collect, progress):
    """Run the baseline CLI with cleanup on interrupt and per-output checkpointing."""
    directory = _path(ctx, job["directory"])
    command = lama.build_iopaint_command(staged, ctx["baseline"], ctx["environment"])
    _save(directory / "command.json", command)
    env = lama.build_iopaint_subprocess_environment()
    env.update(LAMA_MODEL_URL=ctx["baseline"]["model"]["model_artifact_url"],
               LAMA_MODEL_MD5=ctx["baseline"]["model"]["model_artifact_expected_md5"])
    timer, process = perf_counter(), None
    job.update(status="running", started_at_utc=utc_now_iso(), command=command)
    try:
        with (directory / "logs/stdout.log").open("w", encoding="utf-8") as stdout, (directory / "logs/stderr.log").open("w", encoding="utf-8") as stderr:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, env=env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            job.update(pid=process.pid, process_created_at=psutil.Process(process.pid).create_time())
            _save(directory / "job.json", job)
            last_notice = 0.0
            while process.poll() is None:
                collect()
                elapsed = perf_counter() - timer
                if elapsed > ctx["baseline"]["execution"]["command_timeout_seconds"]:
                    raise TimeoutError("IOPaint command reached the baseline timeout")
                if elapsed - last_notice >= 15:
                    progress(f"LaMa {job['scope']} | command elapsed {elapsed:.0f}s")
                    last_notice = elapsed
                sleep(ctx["baseline"]["execution"]["progress_poll_seconds"])
            job["return_code"] = process.wait()
            collect()
            job["status"] = "completed" if job["return_code"] == 0 else "failed"
    except BaseException as exc:
        job.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed", issue=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        job.update(runtime_seconds=perf_counter() - timer, finished_at_utc=utc_now_iso())
        _save(directory / "job.json", job)


def run_scope(ctx, rows, scope="primary", progress: Callable[[str], None] = print, runner=None):
    """Reuse verified receipts and recover interrupted raw outputs before inference."""
    _assert_inputs(ctx)
    jobs = [j for j in _jobs(ctx) if j["scope"] == scope]
    rows = list(rows)
    found = {}
    for row in rows:
        output, receipt = _locations(ctx, row, scope)
        if receipt.exists():
            found[row["candidate_id"]] = _read(receipt)
            _verify(ctx, row, found[row["candidate_id"]], scope)
            continue
        for job in jobs:
            for staged in job["staged_items"]:
                if staged["candidate_id"] == row["candidate_id"]:
                    d04._require(staged["input_image_sha256"] == row["input_image_sha256"] and staged["mask_sha256"] == row["mask_sha256"], "Recovery input binding mismatch")
                    record = _collect(ctx, row, staged, job, scope)
                    if record:
                        found[row["candidate_id"]] = record
                        break
            if row["candidate_id"] in found:
                break
        d04._require(row["candidate_id"] in found or not output.exists(), "Unverified output cannot be overwritten")
    reused = len(found)
    def persist():
        if scope == "primary" and found:
            _merge_table(_path(ctx, ctx["config"]["outputs"]["candidates"]), pd.DataFrame(list(found.values())))
    persist()
    for attempt in range(1 + ctx["baseline"]["model"]["maximum_retries"]):
        pending = [r for r in rows if r["candidate_id"] not in found]
        if not pending:
            break
        prepared = lama.prepare_lama_work_items(pd.DataFrame(pending), project_root=ctx["root"], config=ctx["baseline"], progress_callback=None)
        directory = _path(ctx, f"work/lama/jobs/{scope}_{uuid4().hex}")
        d04._require(not directory.exists(), "Job directory must be new")
        staged = lama.stage_lama_batch(prepared, batch_directory=directory, work_root=_path(ctx, "work/lama/jobs"), project_root=ctx["root"], config=ctx["baseline"])
        job = dict(job_id=directory.name, scope=scope, directory=directory.relative_to(ctx["output_root"]).as_posix(),
            status="prepared", execution_fingerprint=ctx["execution_fingerprint"], attempt=attempt + 1, staged_items=staged.to_dict("records"))
        job_path = directory / "job.json"
        _save(job_path, job)
        index = _path(ctx, "work/lama/job_index.json")
        paths = _read(index)["job_paths"] if index.exists() else []
        _save(index, dict(job_paths=[*paths, job_path.relative_to(ctx["output_root"]).as_posix()]))
        def collect():
            for planned, item in ((r, s) for r in pending for s in job["staged_items"] if r["candidate_id"] == s["candidate_id"]):
                if planned["candidate_id"] not in found:
                    record = _collect(ctx, planned, item, job, scope)
                    if record:
                        found[planned["candidate_id"]] = record
                        persist()
                        progress(f"LaMa {scope} {len(found)}/{len(rows)} | {planned['painting_id']} | completed")
        try:
            (runner or _run_command)(ctx, staged, job, collect, progress)
        except (OSError, TimeoutError) as exc:
            progress(f"LaMa command issue: {exc}")
        collect()
    records = [found.get(row["candidate_id"], dict(row, status="failed", issue="No complete verified raw PNG; inspect work/lama/jobs logs")) for row in rows]
    if scope == "primary":
        _merge_table(_path(ctx, ctx["config"]["outputs"]["candidates"]), pd.DataFrame(records))
    return records, reused


def repeatability(first, second, tolerance, sha_equal):
    difference = np.abs(first.astype(np.int16) - second.astype(np.int16))
    result = dict(maximum_absolute_difference=int(difference.max()), mean_absolute_difference=float(difference.mean()),
        different_pixel_fraction=float(np.any(difference > 0, axis=2).mean()), sha256_equal=bool(sha_equal),
        measurement_region="full_768_canvas_as_in_N10")
    result["passed"] = bool(result["maximum_absolute_difference"] <= tolerance["maximum_absolute_difference"]
        and result["mean_absolute_difference"] <= tolerance["maximum_mean_absolute_difference"]
        and result["different_pixel_fraction"] <= tolerance["maximum_different_pixel_fraction"]
        and (sha_equal or not tolerance["require_sha256_equality"]))
    return result


def run_smoke(ctx, progress=print, runner=None):
    row = ctx["worklist"].loc[ctx["worklist"].painting_id.eq(ctx["policy"]["smoke_painting_id"])].iloc[0].to_dict()
    records = [run_scope(ctx, [row], scope, progress, runner)[0][0] for scope in ("smoke_1", "smoke_2")]
    d04._require(all(r["status"] == "completed" for r in records), "LaMa smoke inference failed; inspect job logs")
    arrays = [lama._load_rgb(ctx["root"] / r["restored_path"]) for r in records]
    comparison = repeatability(*arrays, ctx["baseline"]["smoke"]["repeatability_tolerance"], records[0]["restored_sha256"] == records[1]["restored_sha256"])
    image, mask = _inputs(ctx, row)
    identity = lama.masked_composite(image, np.zeros_like(image), np.zeros_like(mask))
    _check(ctx, "smoke_repeatability", "Two separate LaMa runs meet the unchanged N10 tolerance", comparison["passed"], comparison)
    _check(ctx, "smoke_outside", "Both smoke outputs preserve every outside-mask pixel", all(r["changed_outside_pixels"] == 0 for r in records), [r["changed_outside_pixels"] for r in records], [0, 0])
    _check(ctx, "smoke_zero_identity", "Empty-mask compositor control preserves the input exactly", np.array_equal(identity, image), bool(np.array_equal(identity, image)))
    ctx["smoke_summary"] = dict(stage=STAGE, execution_fingerprint=ctx["execution_fingerprint"], painting_id=row["painting_id"],
        repeat_count=2, primary_candidate_count=0, records=records, repeatability=comparison, zero_mask_identity=bool(np.array_equal(identity, image)))
    _save(_path(ctx, ctx["policy"]["outputs"]["smoke_summary"]), ctx["smoke_summary"])
    ctx["validation"].raise_for_blocking()
    ctx["smoke_passed"] = True
    return ctx


def run_candidates(ctx, progress=print, runner=None):
    d04._require(ctx.get("smoke_passed") is True, "LaMa smoke must pass first")
    records, reused = run_scope(ctx, ctx["worklist"].to_dict("records"), progress=progress, runner=runner)
    ctx.update(records=pd.DataFrame(records), reused_candidates=reused)
    return ctx


def validate_results(ctx):
    records = ctx["records"]
    for row in records.to_dict("records"):
        good = row["status"] == "completed"
        _check(ctx, f"completed:{row['painting_id']}", "Primary LaMa candidate completed", good, row["status"], "completed")
        if good:
            planned = ctx["worklist"].loc[ctx["worklist"].candidate_id.eq(row["candidate_id"])].iloc[0].to_dict()
            _verify(ctx, planned, row, "primary")
        _check(ctx, f"output:{row['painting_id']}", "Output and raw inference match their receipts and RGB geometry", good, good)
        _check(ctx, f"outside:{row['painting_id']}", "Every outside-mask pixel is preserved", good and row.get("changed_outside_pixels") == 0, row.get("changed_outside_pixels", "unavailable"), 0)
    complete = int(records.status.eq("completed").sum())
    _check(ctx, "primary_population", "All ten frozen LaMa primary candidates are retained", complete == 10 and set(records.candidate_id) == set(ctx["worklist"].candidate_id), complete, 10)
    checks = ctx["validation"].to_dataframe()
    _save(_path(ctx, ctx["policy"]["outputs"]["stage_checks"]), checks)
    path = _path(ctx, ctx["config"]["outputs"]["validation"])
    if path.exists():
        old = pd.read_csv(path, keep_default_na=False)
        checks = pd.concat([old.loc[~old.validation_stage.isin(checks.validation_stage.unique())], checks], ignore_index=True)
    _save(path, checks)
    jobs = [j for j in _jobs(ctx) if j["scope"] == "primary"]
    runtime = sum(float(j.get("runtime_seconds", 0)) for j in jobs)
    summary = dict(stage=STAGE, model_id=MODEL, expected_candidates=10, completed_candidates=complete, failed_candidates=10-complete,
        reused_candidates=ctx["reused_candidates"], execution_fingerprint=ctx["execution_fingerprint"],
        recorded_command_runtime_seconds=runtime, command_groups=len(jobs),
        command_groups_missing_runtime=sum("runtime_seconds" not in j for j in jobs),
        runtime_scope="primary_IOPaint_commands_including_startup_retries_and_checkpointing_excluding_smoke",
        individual_case_runtime_available=False, validation_summary=ctx["validation"].summary(),
        notebook_completion_gate_passed=False, recorded_at_utc=utc_now_iso())
    _save(_path(ctx, ctx["policy"]["outputs"]["stage_summary"]), summary)
    _merge_table(_path(ctx, ctx["config"]["outputs"]["runtime_summary"]), pd.DataFrame([{k:v for k,v in summary.items() if k != "validation_summary"}]))
    ctx["summary"] = summary
    ctx["validation"].raise_for_blocking()
    return ctx


def render_previews(ctx):
    """All physical inputs, selected masks and LaMa outputs; no fidelity scores."""
    import matplotlib.pyplot as plt
    ctx["validation"].raise_for_blocking()
    paths = []
    for key, start, end in (("preview_first", 0, 5), ("preview_second", 5, 10)):
        fig, axes = plt.subplots(5, 3, figsize=(13, 16))
        for i, row in enumerate(ctx["records"].iloc[start:end].to_dict("records")):
            image, mask = _inputs(ctx, row)
            restored = lama._load_rgb(ctx["root"] / row["restored_path"])
            for j, (pixels, title) in enumerate(((image, "Damaged input"), (image, "Selected repair mask"), (restored, "LaMa restoration"))):
                axes[i,j].imshow(pixels)
                if j == 1:
                    overlay = np.zeros((*mask.shape, 4)); overlay[mask > 0] = [0, 1, 1, .4]
                    axes[i,j].imshow(overlay)
                axes[i,j].set_title(f"{row['painting_id']} | {title}", fontsize=9)
                axes[i,j].axis("off")
        fig.suptitle("D04 | LaMa primary restorations — unchanged N10 pipeline and reviewed masks", fontsize=13)
        fig.text(.5, .012, "No clean references: visual inspection does not establish reconstruction accuracy.\n"
            "Source credits/licences: D03 artworks.csv; rd004 Tyler Bell CC BY 2.0; rd005 BeakheadIntrados CC BY-SA 4.0; rd006 The Met CC0.\n"
            "Other sources retain their recorded public-domain terms. Restorations, resizing and mask overlays are adaptations.", ha="center", fontsize=7)
        fig.tight_layout(rect=(0,.05,1,.97))
        path = _path(ctx, ctx["policy"]["outputs"][key]); path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=130); plt.close(fig); paths.append(path)
    ctx["preview_paths"] = paths
    return paths
