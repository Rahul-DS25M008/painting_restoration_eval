"""D04 HINT orchestration around the unchanged N12A production worker.

The worker owns inference and exact compositing. This adapter binds its jobs to
the frozen D04 inputs, publishes verified PNGs and preserves per-case receipts.
"""
from __future__ import annotations

import copy
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter, sleep
from uuid import uuid4

import cv2
import numpy as np
import pandas as pd
from PIL import Image
import psutil
import yaml

from . import real_damage_restoration as d04
from . import real_damage_lama as prior
from . import real_damage_telea as telea
from . import real_damage_readiness as readiness
from . import restoration_hint as hint
from .hint_mat_selection import exact_mask_composite
from .manifests import sha256_file, utc_now_iso
from .paths import resolve_repo_path, to_repo_relative
from .real_damage_dataset import audit_inventory_inputs
from .validation import ValidationCollector

MODULE_VERSION = "1.0.0"
MODEL = "hint_places2"
STAGE = "batch_5_hint"
_read, _save, _path = prior._read, prior._save, prior._path


def _check(ctx, key, description, passed, observed, expected=True):
    checks = ValidationCollector()
    checks.extend(c for c in ctx["validation"].checks if (c.validation_stage, c.check_id) != (STAGE, key))
    checks.add(validation_stage=STAGE, check_id=key, check_description=description,
        passed=passed, observed=observed, expected=expected, severity="blocking")
    ctx["validation"] = checks


def prepare_hint(project_root, config_path):
    """Inspect saved upstream evidence and local assets; never load the generator."""
    root = Path(project_root).resolve()
    path = resolve_repo_path(config_path, root, must_exist=True)
    policy = yaml.safe_load(path.read_text(encoding="utf-8"))
    d04._require(policy["schema_version"] == "real_damage_hint_config.v1" and policy["stage"] == STAGE
        and policy["expected_candidates"] == 10 and policy["smoke_repeats"] == 2
        and policy["overwrite_unverified_outputs"] is False
        and policy["worker_overrides"] == {"progress_interval_cases":1, "checkpoint_interval_cases":1}, "Unexpected HINT stage policy")
    for key in ("helper_source", "tests", "lama_config", "baseline_config", "baseline_notebook", "shared_input_helper"):
        d04._relative(policy[key])
    for rel in policy["outputs"].values():
        d04._relative(rel)
    upstream = prior.prepare_lama(root, policy["lama_config"])
    output = upstream["output_root"]
    summary = _read(output / "work/lama/batch_summary.json")
    d04._require(summary["completed_candidates"] == 10 and summary["failed_candidates"] == 0
        and summary["execution_fingerprint"] == upstream["execution_fingerprint"]
        and summary["validation_summary"]["passed_count"] == summary["validation_summary"]["check_count"] == 134,
        "Batch 4 has not passed")
    declared = {"stage_config":path, "stage_helper":root / policy["helper_source"], "stage_tests":root / policy["tests"],
        "shared_input_helper":root / policy["shared_input_helper"], "lama_summary":output / "work/lama/batch_summary.json",
        "lama_checks":output / "work/lama/checks.csv", "baseline_notebook":root / policy["baseline_notebook"]}
    baseline_runs = []
    for cell in _read(root / policy["baseline_notebook"])["cells"]:
        for result in cell.get("outputs", []):
            text = result.get("text", "")
            for line in ("".join(text) if isinstance(text, list) else text).splitlines():
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict) and payload.get("result_schema_version") == "hint_production_worker_result.v1":
                    baseline_runs.append(payload)
    expected_load = policy["expected_load_audit"]
    d04._require(expected_load == dict(matched_state_keys=973,model_state_key_count=973,missing_state_keys=0,unexpected_state_keys=153)
        and {3,2620}.issubset({x["successful_rows"] for x in baseline_runs if x.get("status") == "completed"})
        and all(all(x["model_load_audit"][k] == v for k,v in expected_load.items()) for x in baseline_runs), "N12A saved load profile does not support the expected HINT audit")
    table = pd.read_csv(output / upstream["config"]["outputs"]["candidates"], keep_default_na=False, float_precision="round_trip")
    for row in upstream["worklist"].to_dict("records"):
        _, receipt_path = prior._locations(upstream, row, "primary")
        record = _read(receipt_path)
        prior._verify(upstream, row, record, "primary")
        match = table.loc[table.candidate_id.eq(row["candidate_id"])]
        d04._require(len(match) == 1 and all(match.iloc[0][k] == record[k]
            for k in ("model_id", "status", "restored_path", "restored_sha256", "execution_binding")), "LaMa table/receipt mismatch")
        declared[f"lama_receipt.{row['painting_id']}"] = receipt_path
    baseline = hint.load_hint_config(root / policy["baseline_config"])
    plan = pd.read_csv(output / upstream["config"]["outputs"]["candidate_plan"], keep_default_na=False)
    worklist = plan.loc[plan.model_id.eq(MODEL)].sort_values("painting_id").reset_index(drop=True)
    d04._require(len(worklist) == 10 and worklist.candidate_id.is_unique and worklist.painting_id.nunique() == 10
        and worklist.candidate_role.eq("primary").all() and worklist.mask_threshold.eq(128).all()
        and pd.to_numeric(worklist.seed).eq(2026).all()
        and worklist.model_config_sha256.eq(sha256_file(root / policy["baseline_config"])).all()
        and not worklist.has_clean_reference.any() and worklist.clean_image_path.eq("").all(), "Incorrect frozen HINT plan")
    model = baseline["model"]
    d04._require(model["seed"] == 2026 and model["precision"] == "float32" and model["requested_device"] == "cuda"
        and not model["allow_cpu_fallback"] and model["inference_width"] == model["inference_height"] == 768
        and baseline["execution"]["worker_module"] == "restoration_eval.restoration_hint_production_worker"
        and baseline["execution"]["retry_failed_attempts"] is False, "HINT production pipeline changed")
    env = _read(output / "work/readiness/runtime_environment.json")
    asset = hint.inspect_hint_asset(baseline)
    d04._require(asset["ready"] and asset["checkpoint_sha256"] == env["hint"]["checkpoint_sha256"]
        and asset["actual_repository_revision"] == env["hint"]["actual_repository_revision"], "Pinned HINT asset differs from Batch 2")
    for key in ("repository_path", "checkpoint_path"):
        d04._require(Path(asset[key]).resolve() == Path(env["hint"][key]).resolve(), f"HINT asset location differs from Batch 2: {key}")
    assets = pd.read_csv(output / "work/readiness/runtime_assets.csv", keep_default_na=False)
    assets = assets.loc[assets.model_id.eq(MODEL)].to_dict("records")
    for record in assets:
        d04._require(sha256_file(Path(record["path"])) == record["sha256"], f"HINT asset changed: {record['path']}")
    packages = {name:version(name) for name in ("torch", "torchvision", "numpy", "Pillow", "einops", "timm")}
    d04._require(all(value == env["package_versions"][name] for name,value in packages.items()), "HINT package versions differ from Batch 2")
    inventory, audit = audit_inventory_inputs(root, root / upstream["config"]["inputs"]["inventory"],
        root / upstream["config"]["inputs"]["inventory_run"], declared)
    checks = ValidationCollector()
    saved = pd.read_csv(output / "work/lama/checks.csv", keep_default_na=False)
    d04._require(len(saved) == 134 and saved.passed.all(), "Saved LaMa checks are incomplete")
    for row in saved.to_dict("records"):
        checks.add(**row)
    bindings = {to_repo_relative(p, root):sha256_file(p) for p in declared.values()}
    ctx = dict(root=root, output_root=output, policy=policy, config=upstream["config"], baseline=baseline,
        frozen=upstream["frozen"], worklist=worklist, validation=checks, inventory=inventory, asset=asset,
        assets=assets, packages=packages, stage_input_checksums=bindings, frozen_input_checksums=upstream["frozen_input_checksums"])
    ctx["execution_fingerprint"] = d04._digest(dict(stage_inputs=bindings, lama_execution=upstream["execution_fingerprint"],
        readiness=ctx["frozen"]["readiness_fingerprint"], assets=assets, packages=packages, module_version=MODULE_VERSION))
    _check(ctx, "lama_handoff", "Ten LaMa candidates retain verified receipts and outside-mask pixels", True, 10, 10)
    _check(ctx, "hint_population", "Ten frozen HINT candidates with seed 2026 and no references", True, len(worklist), 10)
    _check(ctx, "hint_assets", "Pinned source bytes and checkpoint match Batch 2", True, asset["checkpoint_sha256"])
    _check(ctx, "hint_pipeline", "Unchanged N12A worker, native 768px CUDA float32 and exact compositor", True, model["configuration_id"])
    _check(ctx, "hint_environment", "HINT dependency versions match the frozen runtime", True, packages)
    _check(ctx, "stage_inventory", "Inventory covers new HINT files and immutable LaMa handoff", bool(audit.passed.all()), audit.loc[~audit.passed].to_dict("records"), [])
    ctx["validation"].raise_for_blocking()
    return ctx


def _assert_inputs(ctx):
    for rel,digest in {**ctx["frozen_input_checksums"], **ctx["stage_input_checksums"]}.items():
        d04._require(sha256_file(ctx["root"] / rel) == digest, f"Frozen/stage input changed: {rel}")
    for asset in ctx["assets"]:
        d04._require(sha256_file(Path(asset["path"])) == asset["sha256"], f"HINT asset changed: {asset['path']}")
    for name,expected in ctx.get("packages", {}).items():
        d04._require(version(name) == expected, f"HINT package version changed: {name}")


def _inputs(ctx, row):
    for name,digest in (("input_image_path","input_image_sha256"), ("mask_path","mask_sha256")):
        d04._require(sha256_file(resolve_repo_path(row[name],ctx["root"],must_exist=True)) == row[digest], f"Candidate {name} changed")
    with Image.open(ctx["root"] / row["input_image_path"]) as pil:
        image = np.asarray(pil.convert("RGB"),dtype=np.uint8)
    with Image.open(ctx["root"] / row["mask_path"]) as pil:
        mask = np.asarray(pil.convert("L"),dtype=np.uint8)
    size = (ctx["baseline"]["model"]["inference_height"], ctx["baseline"]["model"]["inference_width"])
    d04._require(image.shape == (*size,3) and mask.shape == size and set(np.unique(mask)).issubset({0,255}) and np.any(mask), "Invalid input geometry or repair mask")
    return image,mask


def _locations(ctx, row, scope):
    d04._require(scope in ("primary","smoke"), "Unknown HINT scope")
    relative = row["restored_path"] if scope == "primary" else f"work/hint/smoke/{row['candidate_id']}.png"
    return _path(ctx,relative), _path(ctx,f"work/hint/receipts/{scope}/{row['candidate_id']}.json")


def _binding(ctx,row,scope):
    return d04._digest(dict(execution=ctx["execution_fingerprint"],candidate=row,scope=scope))


def _verify(ctx,row,record,scope):
    image,mask = _inputs(ctx,row)
    output,_ = _locations(ctx,row,scope)
    telea._verify_record(ctx,row,output,record,_binding(ctx,row,scope),cv2.cvtColor(image,cv2.COLOR_RGB2BGR),mask)
    worker_image = resolve_repo_path(record["worker_output_path"],ctx["root"],must_exist=True)
    d04._require(sha256_file(worker_image) == record["restored_sha256"], "HINT worker image checksum mismatch")


def _merge_table(path,frame):
    if path.exists():
        existing = pd.read_csv(path,keep_default_na=False,float_precision="round_trip")
        frame = pd.DataFrame([*existing.loc[existing.model_id.ne(MODEL)].to_dict("records"),*frame.to_dict("records")])
    key = "candidate_id" if "candidate_id" in frame else "model_id"
    d04._require(frame[key].is_unique,"Duplicate IDs in accumulated table")
    _save(path,frame)


def _jobs(ctx):
    index = _path(ctx,"work/hint/job_index.json")
    jobs = []
    for rel in (_read(index)["job_paths"] if index.exists() else []):
        job = _read(_path(ctx,rel))
        d04._require(job["execution_fingerprint"] == ctx["execution_fingerprint"], "Previous HINT job belongs to changed inputs/code")
        directory = _path(ctx,job["directory"])
        d04._require(sha256_file(directory / "worker_job.json") == job["worker_job_sha256"], "HINT worker job changed")
        if job.get("pid") and job["status"] == "running":
            try:
                process = psutil.Process(job["pid"])
                d04._require(abs(process.create_time()-job["process_created_at"]) > .01 or not process.is_running(), "Previous HINT process is still running")
            except psutil.NoSuchProcess:
                pass
        result_path = directory / "result.json"
        if result_path.exists():
            load = _read(result_path)["model_load_audit"]
            d04._require(all(load[k] == v for k,v in ctx["policy"]["expected_load_audit"].items()),
                "HINT state dictionary load profile differs from the executed N12A baseline")
        jobs.append(job)
    return jobs


def _make_job(ctx,rows,scope):
    directory = _path(ctx,f"work/hint/jobs/{scope}_{uuid4().hex}")
    directory.mkdir(parents=True,exist_ok=False)
    worker_rows = []
    for row in rows:
        _inputs(ctx,row)
        item = {key:"" for key in hint.HINT_WORK_COLUMNS}
        item.update(row)
        item.update(input_image_path=str((ctx["root"] / row["input_image_path"]).resolve()),
            mask_path=str((ctx["root"] / row["mask_path"]).resolve()),clean_image_path="",
            restored_path=str(directory / "images" / f"{row['candidate_id']}.png"),execution_action="hint_inpaint",
            status="planned",input_sha256=row["input_image_sha256"],seed=ctx["baseline"]["model"]["seed"])
        worker_rows.append(item)
    execution = {**ctx["baseline"]["execution"],**ctx["policy"]["worker_overrides"]}
    payload = dict(job_schema_version="hint_production_worker_job.v1", helper_version=hint.HELPER_VERSION,
        repository_path=ctx["asset"]["repository_path"],checkpoint_path=ctx["asset"]["checkpoint_path"],
        result_path=str(directory / "result.json"),checkpoint_path_csv=str(directory / "checkpoint.csv"),
        progress_path=str(directory / "progress.json"),execution=execution,model=copy.deepcopy(ctx["baseline"]["model"]),candidates=worker_rows)
    _save(directory / "worker_job.json",payload)
    job = dict(job_id=directory.name,directory=directory.relative_to(ctx["output_root"]).as_posix(),scope=scope,
        status="prepared",execution_fingerprint=ctx["execution_fingerprint"],rows=rows,
        worker_job_sha256=sha256_file(directory / "worker_job.json"))
    _save(directory / "job.json",job)
    index = _path(ctx,"work/hint/job_index.json")
    paths = _read(index)["job_paths"] if index.exists() else []
    _save(index,dict(job_paths=[*paths,job["directory"]+"/job.json"]))
    return job


def _collect(ctx,job,found,progress):
    directory = _path(ctx,job["directory"])
    checkpoint = directory / "checkpoint.csv"
    if not checkpoint.exists():
        return
    frame = pd.read_csv(checkpoint,keep_default_na=False,float_precision="round_trip")
    d04._require(frame.candidate_id.is_unique,"Duplicate worker checkpoint candidates")
    planned = {row["candidate_id"]:row for row in job["rows"]}
    d04._require(set(frame.candidate_id).issubset(planned),"Worker checkpoint contains an unplanned candidate")
    for worker in frame.to_dict("records"):
        cid = worker["candidate_id"]
        if cid in found:
            continue
        row = planned[cid]; output,receipt = _locations(ctx,row,job["scope"])
        d04._require(worker["status"] in ("completed","failed"),"Invalid worker status")
        expected_image = directory / "images" / f"{cid}.png"
        d04._require(Path(worker["restored_path"]).resolve() == expected_image.resolve()
            and worker["input_sha256"] == row["input_image_sha256"] and worker["mask_sha256"] == row["mask_sha256"]
            and Path(worker["input_image_path"]).resolve() == (ctx["root"] / row["input_image_path"]).resolve()
            and Path(worker["mask_path"]).resolve() == (ctx["root"] / row["mask_path"]).resolve()
            and int(worker["seed"]) == int(row["seed"]) and int(worker["mask_threshold"]) == int(row["mask_threshold"])
            and worker["model_id"] == MODEL and worker["configuration_id"] == row["configuration_id"], "Worker row does not match its frozen inputs/configuration")
        record = dict(row,status=worker["status"],execution_binding=_binding(ctx,row,job["scope"]),
            execution_fingerprint=ctx["execution_fingerprint"],execution_scope=job["scope"],command_group_id=job["job_id"],
            issue=worker.get("error_message","") or worker.get("issue", ""))
        if worker["status"] == "completed":
            image,mask = _inputs(ctx,row)
            d04._require(expected_image.is_file() and sha256_file(expected_image) == worker["restored_sha256"],"Worker PNG checksum mismatch")
            with Image.open(expected_image) as pil:
                d04._require(pil.mode == "RGB","Worker output must be RGB")
                restored = np.asarray(pil,dtype=np.uint8)
            technical = telea._technical(image,mask,restored)
            d04._require(technical["changed_outside_pixels"] == 0 and worker["technical_validation_passed"] is True, "HINT technical validation failed")
            content = expected_image.read_bytes()
            d04._require(not output.exists() or output.read_bytes() == content, "Unverified output differs from worker checkpoint")
            if not output.exists():
                readiness._atomic(output,content)
            record.update(schema_version="real_damage_candidates.v1",runtime_status="inference_validated",execution_action="hint_inpaint",
                readiness_fingerprint=ctx["frozen"]["readiness_fingerprint"],restored_path=to_repo_relative(output,ctx["root"]),
                restored_sha256=worker["restored_sha256"],worker_output_path=to_repo_relative(expected_image,ctx["root"]),
                checkpoint_sha256=ctx["asset"]["checkpoint_sha256"],repository_revision=ctx["asset"]["actual_repository_revision"],
                adapter_version=MODULE_VERSION,generator_version=worker["generator_version"],
                runtime_seconds=worker["runtime_seconds"],inference_seconds=worker["inference_seconds"],
                model_load_seconds=worker["model_load_seconds"],gpu_peak_memory_bytes=worker["gpu_peak_memory_bytes"],
                runtime_scope="N12A_worker_case_call_excluding_model_load",started_at_utc=worker["started_at_utc"],completed_at_utc=worker["completed_at_utc"],**technical)
        _save(receipt,record)
        if record["status"] == "completed":
            _verify(ctx,row,record,job["scope"])
        found[cid] = record
        if job["scope"] == "primary":
            _merge_table(_path(ctx,ctx["config"]["outputs"]["candidates"]),pd.DataFrame(list(found.values())))
        progress(f"HINT {job['scope']} | {row['painting_id']} | {record['status']}")


def _run_worker(ctx,job,collect,progress):
    directory = _path(ctx,job["directory"])
    command = hint.worker_command(directory / "worker_job.json")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(x for x in (str(ctx["root"] / "src"),env.get("PYTHONPATH","")) if x)
    env.update(PYTHONUTF8="1",PYTHONIOENCODING="utf-8")
    timer = last_progress = last_notice = perf_counter()
    signature = None; process = None
    execution = ctx["baseline"]["execution"]
    job.update(status="running",command=command,started_at_utc=utc_now_iso())
    try:
        with (directory / "stdout.log").open("w",encoding="utf-8") as stdout, (directory / "stderr.log").open("w",encoding="utf-8") as stderr:
            process = subprocess.Popen(command,cwd=ctx["root"],env=env,stdout=stdout,stderr=stderr,
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            job.update(pid=process.pid,process_created_at=psutil.Process(process.pid).create_time())
            _save(directory / "job.json",job)
            while process.poll() is None:
                collect()
                now = perf_counter(); progress_path = directory / "progress.json"
                if progress_path.exists():
                    stat = progress_path.stat(); current = (stat.st_size,stat.st_mtime_ns)
                    if current != signature:
                        signature = current; last_progress = now
                timeout = execution["model_load_timeout_seconds"] if signature is None else execution["per_case_timeout_seconds"]
                if now-timer > execution["full_run_budget_seconds"] or now-last_progress > timeout:
                    raise TimeoutError("HINT worker exceeded baseline startup/stall/total time limit")
                if now-last_notice >= 15:
                    progress(f"HINT {job['scope']} | worker elapsed {now-timer:.0f}s")
                    last_notice = now
                sleep(execution["progress_poll_seconds"])
            job["return_code"] = process.wait()
            collect()
            job["status"] = "completed" if job["return_code"] == 0 else "failed"
    except BaseException as exc:
        job.update(status="interrupted" if isinstance(exc,KeyboardInterrupt) else "failed",issue=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
        job.update(runtime_seconds=perf_counter()-timer,finished_at_utc=utc_now_iso())
        _save(directory / "job.json",job)


def run_scope(ctx,rows,scope="primary",progress=print,runner=None):
    _assert_inputs(ctx)
    rows = list(rows); found = {}
    jobs = [j for j in _jobs(ctx) if j["scope"] == scope]
    for row in rows:
        _inputs(ctx,row)
        _,receipt = _locations(ctx,row,scope)
        if receipt.exists():
            record = _read(receipt)
            d04._require(record["execution_binding"] == _binding(ctx,row,scope) and record["status"] in ("completed","failed"),"Existing receipt binding changed")
            if record["status"] == "completed":
                _verify(ctx,row,record,scope)
            found[row["candidate_id"]] = record
    for job in jobs:
        _collect(ctx,job,found,progress)
    for row in rows:
        output,_ = _locations(ctx,row,scope)
        d04._require(row["candidate_id"] in found or not output.exists(),"Unverified HINT output cannot be overwritten")
    reused = sum(r["status"] == "completed" for r in found.values())
    pending = [r for r in rows if r["candidate_id"] not in found]
    # As in N12A, failed attempts are retained and never automatically retried.
    blocked = any(r["status"] == "failed" for r in found.values()) or any(j["status"] == "failed" for j in jobs)
    if pending and not blocked:
        job = _make_job(ctx,pending,scope)
        collect = lambda: _collect(ctx,job,found,progress)
        try:
            (runner or _run_worker)(ctx,job,collect,progress)
        except (OSError,TimeoutError) as exc:
            progress(f"HINT worker issue: {exc}")
        collect()
        _jobs(ctx)  # Check any completed model-load audit before accepting the batch.
    records = [found.get(row["candidate_id"],dict(row,status="failed",issue="Worker stopped before a verified result; inspect work/hint/jobs logs")) for row in rows]
    if scope == "primary":
        _merge_table(_path(ctx,ctx["config"]["outputs"]["candidates"]),pd.DataFrame(records))
    return records,reused


def run_smoke(ctx,progress=print,runner=None):
    base = ctx["worklist"].loc[ctx["worklist"].painting_id.eq(ctx["policy"]["smoke_painting_id"])].iloc[0].to_dict()
    rows = [dict(base,candidate_id=f"{base['candidate_id']}__smoke_{i:02d}",candidate_role="technical_smoke") for i in (1,2)]
    records,_ = run_scope(ctx,rows,"smoke",progress,runner)
    d04._require(all(r["status"] == "completed" for r in records),"HINT smoke failed; inspect the worker logs")
    equal = records[0]["restored_sha256"] == records[1]["restored_sha256"]
    image,mask = _inputs(ctx,base)
    identity = exact_mask_composite(np.zeros_like(image),image,np.zeros_like(mask))
    _check(ctx,"smoke_repeatability","Two HINT smoke outputs have identical PNG hashes as required by N12A",equal,equal)
    _check(ctx,"smoke_outside","Smoke outputs preserve every outside-mask pixel",all(r["changed_outside_pixels"] == 0 for r in records),[r["changed_outside_pixels"] for r in records],[0,0])
    _check(ctx,"smoke_identity","An empty-mask compositor control preserves every input pixel",np.array_equal(identity,image),bool(np.array_equal(identity,image)))
    jobs = [j for j in _jobs(ctx) if j["scope"] == "smoke"]
    load_audits = [_read(_path(ctx,j["directory"]) / "result.json")["model_load_audit"] for j in jobs if (_path(ctx,j["directory"]) / "result.json").exists()]
    _check(ctx,"smoke_load","A completed smoke worker matches N12A's generator and extra-key counts",bool(load_audits),load_audits)
    ctx["smoke_summary"] = dict(stage=STAGE,execution_fingerprint=ctx["execution_fingerprint"],painting_id=base["painting_id"],
        repeat_count=2,primary_candidate_count=0,sha256_equal=equal,zero_mask_identity=bool(np.array_equal(identity,image)),model_load_audits=load_audits,records=records)
    _save(_path(ctx,ctx["policy"]["outputs"]["smoke_summary"]),ctx["smoke_summary"])
    ctx["validation"].raise_for_blocking()
    ctx["smoke_passed"] = True
    return ctx


def run_candidates(ctx,progress=print,runner=None):
    d04._require(ctx.get("smoke_passed") is True,"HINT smoke must pass first")
    records,reused = run_scope(ctx,ctx["worklist"].to_dict("records"),progress=progress,runner=runner)
    ctx.update(records=pd.DataFrame(records),reused_candidates=reused)
    return ctx


def validate_results(ctx):
    records = ctx["records"]
    for row in records.to_dict("records"):
        good = row["status"] == "completed"
        _check(ctx,f"completed:{row['painting_id']}","Primary HINT candidate completed",good,row["status"],"completed")
        if good:
            planned = ctx["worklist"].loc[ctx["worklist"].candidate_id.eq(row["candidate_id"])].iloc[0].to_dict()
            _verify(ctx,planned,row,"primary")
        _check(ctx,f"output:{row['painting_id']}","Worker PNG and published image retain verified checksums and RGB geometry",good,good)
        _check(ctx,f"outside:{row['painting_id']}","Every outside-mask pixel is preserved",good and row.get("changed_outside_pixels") == 0,row.get("changed_outside_pixels","unavailable"),0)
    complete = int(records.status.eq("completed").sum())
    _check(ctx,"primary_population","All ten frozen HINT candidates are retained",complete == 10 and set(records.candidate_id) == set(ctx["worklist"].candidate_id),complete,10)
    checks = ctx["validation"].to_dataframe()
    _save(_path(ctx,ctx["policy"]["outputs"]["stage_checks"]),checks)
    path = _path(ctx,ctx["config"]["outputs"]["validation"])
    if path.exists():
        old = pd.read_csv(path,keep_default_na=False)
        checks = pd.concat([old.loc[~old.validation_stage.isin(checks.validation_stage.unique())],checks],ignore_index=True)
    _save(path,checks)
    jobs = [j for j in _jobs(ctx) if j["scope"] == "primary"]
    summary = dict(stage=STAGE,model_id=MODEL,expected_candidates=10,completed_candidates=complete,failed_candidates=10-complete,
        reused_candidates=ctx["reused_candidates"],execution_fingerprint=ctx["execution_fingerprint"],
        recorded_case_runtime_seconds=float(pd.to_numeric(records.get("runtime_seconds",pd.Series(dtype=float)),errors="coerce").sum()),
        recorded_command_runtime_seconds=sum(float(j.get("runtime_seconds",0)) for j in jobs),command_groups=len(jobs),
        command_groups_missing_runtime=sum("runtime_seconds" not in j for j in jobs),
        runtime_scope="case_calls_exclude_model_load_command_wall_time_includes_startup_smoke_excluded",
        validation_summary=ctx["validation"].summary(),notebook_completion_gate_passed=False,recorded_at_utc=utc_now_iso())
    _save(_path(ctx,ctx["policy"]["outputs"]["stage_summary"]),summary)
    _merge_table(_path(ctx,ctx["config"]["outputs"]["runtime_summary"]),pd.DataFrame([{k:v for k,v in summary.items() if k != "validation_summary"}]))
    ctx["summary"] = summary
    ctx["validation"].raise_for_blocking()
    return ctx


def render_previews(ctx):
    import matplotlib.pyplot as plt
    ctx["validation"].raise_for_blocking()
    paths = []
    for key,start,end in (("preview_first",0,5),("preview_second",5,10)):
        fig,axes = plt.subplots(5,3,figsize=(13,16))
        for i,row in enumerate(ctx["records"].iloc[start:end].to_dict("records")):
            image,mask = _inputs(ctx,row)
            with Image.open(ctx["root"] / row["restored_path"]) as pil:
                restored = np.asarray(pil).copy()
            for j,(pixels,title) in enumerate(((image,"Damaged input"),(image,"Selected repair mask"),(restored,"HINT restoration"))):
                axes[i,j].imshow(pixels)
                if j == 1:
                    overlay = np.zeros((*mask.shape,4)); overlay[mask > 0] = [0,1,1,.4]
                    axes[i,j].imshow(overlay)
                axes[i,j].set_title(f"{row['painting_id']} | {title}",fontsize=9); axes[i,j].axis("off")
        fig.suptitle("D04 | HINT primary restorations — Places2 checkpoint, native 768px, seed 2026",fontsize=13)
        fig.text(.5,.012,"No clean references: visual inspection does not establish reconstruction accuracy.\n"
            "Source credits/licences: D03 artworks.csv; rd004 Tyler Bell CC BY 2.0; rd005 BeakheadIntrados CC BY-SA 4.0; rd006 The Met CC0.\n"
            "Other sources retain their recorded public-domain terms. Restorations, resizing and mask overlays are adaptations.",ha="center",fontsize=7)
        fig.tight_layout(rect=(0,.05,1,.97))
        path = _path(ctx,ctx["policy"]["outputs"][key]); path.parent.mkdir(parents=True,exist_ok=True)
        fig.savefig(path,dpi=130); plt.close(fig); paths.append(path)
    ctx["preview_paths"] = paths
    return paths
