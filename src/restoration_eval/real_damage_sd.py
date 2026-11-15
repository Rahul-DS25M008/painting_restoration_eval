"""D04 targeted prompts through the unchanged N11 single-candidate executor.

Only the prompt identity and D04 output ownership differ from the baseline.
Local snapshot loading resolves already verified weights without hub requests.
Receipts checkpoint each candidate; smoke results never enter the primary table.
"""
from __future__ import annotations

import copy
import gc
import hashlib
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import cv2
import numpy as np
import pandas as pd
from PIL import Image
import yaml

from . import real_damage_hint as prior
from . import real_damage_restoration as d04
from . import real_damage_readiness as readiness
from . import real_damage_telea as telea
from . import restoration_stable_diffusion as sd
from .manifests import sha256_file, utc_now_iso
from .paths import resolve_repo_path, to_repo_relative
from .real_damage_dataset import audit_inventory_inputs
from .validation import ValidationCollector

MODULE_VERSION = "1.0.0"
MODEL = d04.SD_MODEL
STAGE = "batch_6_sd"
_read, _save, _path = prior._read, prior._save, prior._path


def _check(ctx, key, description, passed, observed, expected=True):
    checks = ValidationCollector()
    checks.extend(c for c in ctx["validation"].checks if (c.validation_stage, c.check_id) != (STAGE, key))
    checks.add(validation_stage=STAGE, check_id=key, check_description=description,
        passed=passed, observed=observed, expected=expected, severity="blocking")
    ctx["validation"] = checks


def _numeric_plan(frame):
    frame = frame.copy()
    for col in ("seed", "num_inference_steps", "inference_width", "inference_height", "output_width", "output_height", "mask_threshold"):
        values = pd.to_numeric(frame[col], errors="raise")
        d04._require(values.mod(1).eq(0).all(), f"Non-integral SD setting: {col}")
        frame[col] = values.astype(int)
    for col in ("guidance_scale", "strength"):
        frame[col] = pd.to_numeric(frame[col], errors="raise")
    return frame


def prepare_sd(project_root, config_path):
    """Read-only handoff audit; neither loads the pipeline nor performs inference."""
    root = Path(project_root).resolve()
    path = resolve_repo_path(config_path, root, must_exist=True)
    policy = yaml.safe_load(path.read_text(encoding="utf-8"))
    d04._require(policy["schema_version"] == "real_damage_sd_config.v1" and policy["stage"] == STAGE
        and policy["expected_candidates"] == 10 and policy["primary_seed"] == 2026
        and policy["smoke_seeds"] == [2026,2026,2027] and policy["overwrite_unverified_outputs"] is False
        and policy["repeat_tolerance"] == dict(maximum_absolute_difference=1,mean_absolute_difference=.005,different_pixel_fraction=.01)
        and policy["load_policy"] == "verified_local_snapshot_same_pinned_weights", "Unexpected SD stage policy")
    for key in ("helper_source", "tests", "hint_config", "baseline_config", "baseline_notebook"):
        d04._relative(policy[key])
    for rel in policy["outputs"].values():
        d04._relative(rel)
    upstream = prior.prepare_hint(root, policy["hint_config"])
    output = upstream["output_root"]
    summary = _read(output / "work/hint/batch_summary.json")
    d04._require(summary["completed_candidates"] == 10 and summary["failed_candidates"] == 0
        and summary["execution_fingerprint"] == upstream["execution_fingerprint"]
        and summary["validation_summary"]["passed_count"] == summary["validation_summary"]["check_count"] == 175,
        "Batch 5 has not passed")
    declared = {"stage_config":path, "stage_helper":root / policy["helper_source"], "stage_tests":root / policy["tests"],
        "hint_summary":output / "work/hint/batch_summary.json", "hint_checks":output / "work/hint/checks.csv",
        "baseline_notebook":root / policy["baseline_notebook"]}
    table = pd.read_csv(output / upstream["config"]["outputs"]["candidates"],keep_default_na=False,float_precision="round_trip")
    for row in upstream["worklist"].to_dict("records"):
        _,receipt = prior._locations(upstream,row,"primary")
        record = _read(receipt); prior._verify(upstream,row,record,"primary")
        match = table.loc[table.candidate_id.eq(row["candidate_id"])]
        d04._require(len(match) == 1 and all(match.iloc[0][k] == record[k]
            for k in ("model_id","status","restored_path","restored_sha256","execution_binding")), "HINT table/receipt mismatch")
        declared[f"hint_receipt.{row['painting_id']}"] = receipt
    baseline = sd.load_stable_diffusion_config(root / policy["baseline_config"])
    effective = d04.effective_model_config(baseline,MODEL,upstream["config"])
    plan = pd.read_csv(output / upstream["config"]["outputs"]["candidate_plan"],keep_default_na=False,float_precision="round_trip")
    plan = _numeric_plan(plan.loc[plan.model_id.eq(MODEL)])
    worklist = plan.loc[plan.candidate_role.eq("primary")].sort_values("painting_id").reset_index(drop=True)
    model = effective["model"]
    d04._require(len(plan) == 40 and plan.candidate_id.is_unique and len(worklist) == 10
        and worklist.painting_id.nunique() == 10 and worklist.seed.eq(2026).all()
        and plan.configuration_fingerprint.eq(d04._digest(model)).all()
        and plan.model_config_sha256.eq(sha256_file(root / policy["baseline_config"])).all()
        and not plan.has_clean_reference.any() and plan.clean_image_path.eq("").all(), "Incorrect frozen SD plan")
    fixed = dict(requested_device="cuda",allow_cpu_fallback=False,precision="float16",scheduler="DDIMScheduler",
        inference_width=512,inference_height=512,output_width=768,output_height=768,num_inference_steps=30,
        guidance_scale=7.5,strength=1.,attention_slicing=True,maximum_retries=1,retry_seed_policy="preserve_exact_seed",
        safety_checker_policy="disabled_research_dataset",compositing_policy="masked_composite_preserve_outside.v1")
    d04._require(all(model[k] == v for k,v in fixed.items()), "N11 numerical pipeline changed")
    for key in set(fixed).intersection(plan.columns):
        d04._require(plan[key].eq(fixed[key]).all(),f"Frozen SD plan differs from baseline: {key}")
    d04._require(plan.hf_model_id.eq(model["hf_model_id"]).all() and plan.model_revision.eq(model["model_revision"]).all()
        and plan.mask_threshold.eq(128).all()
        and plan.negative_prompt.eq(baseline["prompt_policy"]["negative_prompt"]).all(), "SD model/mask/negative prompt drift")
    for _,group in plan.groupby("painting_id"):
        d04._require(set(group.seed) == {2026,2027,2028,2029} and len(group) == 4
            and all(group[c].nunique() == 1 for c in ("prompt","prompt_id","prompt_record_sha256","input_image_sha256","mask_sha256")), "Seed group prompt/input mismatch")
        d04._require(all(hashlib.sha256(r.prompt.encode("utf-8")).hexdigest() == r.prompt_sha256 for r in group.itertuples()), "Targeted prompt hash mismatch")
    env = _read(output / "work/readiness/runtime_environment.json")
    asset = env["sd"]
    d04._require(asset["model_id"] == model["hf_model_id"] and asset["revision"] == model["model_revision"]
        and Path(asset["snapshot_path"]).is_dir(), "Pinned SD snapshot is unavailable")
    assets = pd.read_csv(output / "work/readiness/runtime_assets.csv",keep_default_na=False)
    assets = assets.loc[assets.model_id.eq(MODEL)].to_dict("records")
    d04._require(len(assets) == 13, "Incomplete frozen SD asset inventory")
    for record in assets:
        d04._require(sha256_file(Path(record["path"])) == record["sha256"],f"SD asset changed: {record['path']}")
    packages = {name:version(name) for name in ("torch","diffusers","transformers","accelerate","huggingface-hub","numpy","Pillow")}
    d04._require(all(v == env["package_versions"][k] for k,v in packages.items()), "SD packages differ from Batch 2")
    tokens = pd.read_csv(output / "work/readiness/tokenizer_audit.csv",keep_default_na=False)
    d04._require(len(tokens) == 11 and tokens.fits.all() and not tokens.truncation_used.any(), "Targeted prompts fail tokenizer audit")
    inventory,audit = audit_inventory_inputs(root,root / upstream["config"]["inputs"]["inventory"],
        root / upstream["config"]["inputs"]["inventory_run"],declared)
    checks = ValidationCollector()
    saved = pd.read_csv(output / "work/hint/checks.csv",keep_default_na=False)
    d04._require(len(saved) == 175 and saved.passed.all(), "HINT checks incomplete")
    for row in saved.to_dict("records"):
        checks.add(**row)
    bindings = {to_repo_relative(p,root):sha256_file(p) for p in declared.values()}
    ctx = dict(root=root,output_root=output,policy=policy,config=upstream["config"],baseline=effective,
        frozen=upstream["frozen"],worklist=worklist,validation=checks,inventory=inventory,asset=asset,assets=assets,packages=packages,
        tokenizer_audit=tokens,stage_input_checksums=bindings,frozen_input_checksums=upstream["frozen_input_checksums"])
    ctx["execution_fingerprint"] = d04._digest(dict(stage_inputs=bindings,hint_execution=upstream["execution_fingerprint"],
        readiness=ctx["frozen"]["readiness_fingerprint"],assets=assets,packages=packages,module_version=MODULE_VERSION))
    _check(ctx,"hint_handoff","Ten HINT candidates retain verified receipts and exact outside preservation",True,10,10)
    _check(ctx,"sd_population","Ten primary SD cases use seed 2026; thirty additional seeds remain separate",True,len(worklist),10)
    _check(ctx,"sd_pipeline","Pinned N11 weights and numerical settings are unchanged",True,model["configuration_id"])
    _check(ctx,"sd_prompts","Approved targeted prompts are frozen across four seeds and fit the tokenizer",True,len(tokens),11)
    _check(ctx,"sd_environment","Cached asset hashes and SD package versions match Batch 2",True,packages)
    _check(ctx,"stage_inventory","Inventory covers the SD adapter and immutable HINT handoff",bool(audit.passed.all()),audit.loc[~audit.passed].to_dict("records"),[])
    ctx["validation"].raise_for_blocking()
    return ctx


def _assert_inputs(ctx):
    for rel,digest in {**ctx["frozen_input_checksums"],**ctx["stage_input_checksums"]}.items():
        d04._require(sha256_file(ctx["root"] / rel) == digest,f"Frozen/stage input changed: {rel}")
    for asset in ctx["assets"]:
        d04._require(sha256_file(Path(asset["path"])) == asset["sha256"],f"SD asset changed: {asset['path']}")
    for name,expected in ctx.get("packages",{}).items():
        d04._require(version(name) == expected,f"SD package version changed: {name}")


def _inputs(ctx,row):
    for name,digest in (("input_image_path","input_image_sha256"),("mask_path","mask_sha256")):
        d04._require(sha256_file(resolve_repo_path(row[name],ctx["root"],must_exist=True)) == row[digest],f"Candidate {name} changed")
    with Image.open(ctx["root"] / row["input_image_path"]) as pil:
        image = np.asarray(pil.convert("RGB"),dtype=np.uint8)
    with Image.open(ctx["root"] / row["mask_path"]) as pil:
        mask = np.asarray(pil.convert("L"),dtype=np.uint8)
    d04._require(image.shape == (768,768,3) and mask.shape == (768,768)
        and set(np.unique(mask)).issubset({0,255}) and np.any(mask), "Invalid SD source or repair mask")
    return image,mask


def _locations(ctx,row,scope):
    d04._require(scope in ("primary","smoke"),"Unknown SD scope")
    relative = row["restored_path"] if scope == "primary" else f"work/sd/smoke/{row['candidate_id']}.png"
    return _path(ctx,relative),_path(ctx,f"work/sd/receipts/{scope}/{row['candidate_id']}.json")


def _binding(ctx,row,scope):
    return d04._digest(dict(execution=ctx["execution_fingerprint"],candidate=row,scope=scope))


def _verify(ctx,row,record,scope):
    image,mask = _inputs(ctx,row)
    output,_ = _locations(ctx,row,scope)
    telea._verify_record(ctx,row,output,record,_binding(ctx,row,scope),cv2.cvtColor(image,cv2.COLOR_RGB2BGR),mask)
    d04._require(sha256_file(resolve_repo_path(record["executor_output_path"],ctx["root"],must_exist=True)) == record["restored_sha256"], "SD executor image changed")
    if record.get("model_load_audit_path"):
        d04._require(sha256_file(resolve_repo_path(record["model_load_audit_path"],ctx["root"],must_exist=True)) == record["model_load_audit_sha256"], "SD model-load audit changed")


def _pipeline(ctx):
    if "pipeline" not in ctx:
        _assert_inputs(ctx)
        loading = copy.deepcopy(ctx["baseline"])
        # This changes cache resolution only; the candidate keeps the hub ID and revision.
        loading["model"]["hf_model_id"] = ctx["asset"]["snapshot_path"]
        start = perf_counter()
        pipeline,device = sd.load_stable_diffusion_pipeline(loading)
        import torch
        d04._require(device == "cuda" and type(pipeline).__name__ == "StableDiffusionInpaintPipeline"
            and type(pipeline.scheduler).__name__ == "DDIMScheduler" and pipeline.unet.dtype == torch.float16
            and pipeline.unet.config.in_channels == 9, "Unexpected loaded SD pipeline")
        for prompt in [*ctx["worklist"].prompt,ctx["baseline"]["prompt_policy"]["negative_prompt"]]:
            count = len(pipeline.tokenizer(prompt,truncation=False)["input_ids"])
            d04._require(count <= pipeline.tokenizer.model_max_length,"Loaded tokenizer would truncate a frozen prompt")
        audit = dict(loaded_at_utc=utc_now_iso(),model_load_seconds=perf_counter()-start,
            execution_fingerprint=ctx["execution_fingerprint"],canonical_hf_model_id=ctx["baseline"]["model"]["hf_model_id"],
            revision=ctx["baseline"]["model"]["model_revision"],snapshot_path=ctx["asset"]["snapshot_path"],
            runtime=sd.runtime_environment(device),scheduler=type(pipeline.scheduler).__name__,unet_in_channels=9,
            precision="float16",prompt_truncation_used=False)
        audit_path = _path(ctx,f"work/sd/loads/{uuid4().hex}.json")
        _save(audit_path,audit)
        ctx.update(pipeline=pipeline,device=device,load_audit=audit,load_audit_path=audit_path)
    return ctx["pipeline"],ctx["device"]


def release_pipeline(ctx):
    """Release only this adapter's in-kernel model, after receipts are saved."""
    pipeline = ctx.pop("pipeline",None)
    if pipeline is not None:
        del pipeline
        gc.collect()
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def _publish(ctx,row,scope,raw,result_path):
    output,receipt = _locations(ctx,row,scope)
    binding = _binding(ctx,row,scope)
    d04._require(raw["execution_binding"] == binding and raw["candidate_id"] == row["candidate_id"],"Executor checkpoint binding mismatch")
    if raw["status"] != "completed":
        record = dict(row,status="failed",issue=raw["issue"],execution_binding=binding,
            executor_result_path=to_repo_relative(result_path,ctx["root"]))
        _save(receipt,record)
        return record
    source = _path(ctx,raw["restored_path"])
    d04._require(sha256_file(source) == raw["restored_sha256"],"Executor checkpoint PNG hash mismatch")
    image,mask = _inputs(ctx,row)
    with Image.open(source) as pil:
        d04._require(pil.mode == "RGB" and pil.size == (768,768),"Invalid executor output geometry")
        restored = np.asarray(pil).copy()
    technical = telea._technical(image,mask,restored)
    d04._require(technical["changed_outside_pixels"] == 0,"SD altered outside-mask pixels")
    d04._require(not output.exists() or sha256_file(output) == raw["restored_sha256"],"Unverified published SD image cannot be overwritten")
    if not output.exists():
        readiness._atomic(output,source.read_bytes())
    record = dict(raw)
    record.update(row)
    record.update(schema_version="real_damage_candidates.v1",status="completed",runtime_status="inference_validated",
        restored_path=to_repo_relative(output,ctx["root"]),restored_sha256=raw["restored_sha256"],
        execution_scope=scope,execution_binding=binding,execution_fingerprint=ctx["execution_fingerprint"],
        readiness_fingerprint=ctx["frozen"]["readiness_fingerprint"],executor_output_path=to_repo_relative(source,ctx["root"]),
        executor_result_path=to_repo_relative(result_path,ctx["root"]),generator_version=sd.RESTORATION_GENERATOR_VERSION,
        adapter_version=MODULE_VERSION,**technical)
    _save(receipt,record)
    _verify(ctx,row,record,scope)
    return record


def execute_case(ctx,row,scope="primary",executor=None):
    """Recover receipts or raw executor checkpoints before running a new candidate."""
    _inputs(ctx,row)
    output,receipt = _locations(ctx,row,scope)
    binding = _binding(ctx,row,scope)
    if receipt.exists():
        record = _read(receipt)
        d04._require(record["execution_binding"] == binding,"Existing SD receipt belongs to different inputs or code")
        if record["status"] == "completed":
            _verify(ctx,row,record,scope)
        return record,True
    job_root = _path(ctx,f"work/sd/jobs/{scope}/{row['candidate_id']}")
    for result_path in sorted(job_root.glob("*/result.json")):
        raw = _read(result_path)
        d04._require(raw["execution_binding"] == binding,"Existing executor result belongs to different inputs or code")
        return _publish(ctx,row,scope,raw,result_path),True
    d04._require(not output.exists(),"Unverified existing SD image cannot be overwritten")
    directory = job_root / uuid4().hex
    raw_row = dict(row,restored_path=(directory / "restored.png").relative_to(ctx["output_root"]).as_posix())
    _save(directory / "request.json",dict(candidate=raw_row,execution_binding=binding,created_at_utc=utc_now_iso()))
    if executor is None:
        pipeline,device = _pipeline(ctx)
        raw = sd.run_stable_diffusion_candidate(raw_row,pipeline=pipeline,device=device,
            project_root=ctx["root"],notebook_output_root=ctx["output_root"],config=ctx["baseline"])
        raw.update(model_load_audit_path=to_repo_relative(ctx["load_audit_path"],ctx["root"]),
            model_load_audit_sha256=sha256_file(ctx["load_audit_path"]))
    else:
        raw = executor(ctx,raw_row)
    raw["execution_binding"] = binding
    _save(directory / "result.json",raw)
    return _publish(ctx,row,scope,raw,directory / "result.json"),False


def _merge_candidates(ctx,frame):
    path = _path(ctx,ctx["config"]["outputs"]["candidates"])
    if path.exists():
        old = pd.read_csv(path,keep_default_na=False,float_precision="round_trip")
        frame = pd.concat([old.loc[~old.candidate_id.isin(frame.candidate_id)],frame],ignore_index=True)
    _save(path,frame)


def _difference(a,b,mask):
    absolute = np.abs(a.astype(np.int16)-b.astype(np.int16))
    changed = np.any(absolute > 0,axis=2)
    return dict(maximum_absolute_difference=int(absolute.max()),mean_absolute_difference=float(absolute.mean()),
        different_pixel_fraction=float(changed.mean()),inside_different_pixels=int(np.count_nonzero(changed & (mask > 0))),
        outside_different_pixels=int(np.count_nonzero(changed & (mask == 0))))


def run_smoke(ctx,progress=print,executor=None):
    _assert_inputs(ctx)
    base = ctx["worklist"].loc[ctx["worklist"].painting_id.eq(ctx["policy"]["smoke_painting_id"])].iloc[0].to_dict()
    records = []
    for i,seed in enumerate(ctx["policy"]["smoke_seeds"],1):
        row = dict(base,candidate_id=f"{base['candidate_id']}__smoke_{i:02d}",candidate_role="technical_smoke",seed=seed)
        record,reused = execute_case(ctx,row,"smoke",executor)
        records.append(record); progress(f"SD smoke {i}/3: {record['status']} (reused={reused})")
    d04._require(all(r["status"] == "completed" for r in records),"SD smoke failed; inspect work/sd/jobs")
    arrays = []
    for record in records:
        with Image.open(ctx["root"] / record["restored_path"]) as pil:
            arrays.append(np.asarray(pil).copy())
    image,mask = _inputs(ctx,base)
    repeat = _difference(arrays[0],arrays[1],mask)
    alternate = _difference(arrays[0],arrays[2],mask)
    passed = all(repeat[k] <= v for k,v in ctx["policy"]["repeat_tolerance"].items()) and repeat["outside_different_pixels"] == 0
    identity = np.array_equal(sd.masked_composite(image,np.zeros_like(image),np.zeros_like(mask)),image)
    _check(ctx,"smoke_repeatability","Fixed-seed repeats meet unchanged N11 pixel tolerances",passed,repeat,ctx["policy"]["repeat_tolerance"])
    _check(ctx,"smoke_alternate_seed","Changing only the seed changes the masked output",alternate["inside_different_pixels"] > 0 and alternate["outside_different_pixels"] == 0,alternate)
    _check(ctx,"smoke_outside","Every smoke result preserves all outside-mask pixels",all(r["changed_outside_pixels"] == 0 for r in records),[r["changed_outside_pixels"] for r in records],[0,0,0])
    _check(ctx,"smoke_identity","Empty-mask compositor preserves the input exactly",bool(identity),bool(identity))
    ctx["smoke_summary"] = dict(stage=STAGE,execution_fingerprint=ctx["execution_fingerprint"],painting_id=base["painting_id"],
        primary_candidate_count=0,seeds=ctx["policy"]["smoke_seeds"],fixed_repeat=repeat,alternate_seed=alternate,
        zero_mask_identity=bool(identity),records=records)
    _save(_path(ctx,ctx["policy"]["outputs"]["smoke_summary"]),ctx["smoke_summary"])
    ctx["validation"].raise_for_blocking(); ctx["smoke_passed"] = True
    return ctx


def run_candidates(ctx,progress=print,executor=None):
    d04._require(ctx.get("smoke_passed") is True,"SD smoke must pass first")
    _assert_inputs(ctx)
    records,reused = [],0
    for i,row in enumerate(ctx["worklist"].to_dict("records"),1):
        record,cached = execute_case(ctx,row,executor=executor)
        records.append(record); reused += int(cached)
        _merge_candidates(ctx,pd.DataFrame([record]))
        progress(f"SD primary {i}/10 | {row['painting_id']} | seed {row['seed']} | {record['status']} | reused={cached}")
    ctx.update(records=pd.DataFrame(records),reused_candidates=reused)
    return ctx


def validate_results(ctx):
    records = ctx["records"]
    for row in records.to_dict("records"):
        good = row["status"] == "completed"
        _check(ctx,f"completed:{row['painting_id']}","Primary SD candidate completed",good,row["status"],"completed")
        if good:
            planned = ctx["worklist"].loc[ctx["worklist"].candidate_id.eq(row["candidate_id"])].iloc[0].to_dict()
            _verify(ctx,planned,row,"primary")
        _check(ctx,f"output:{row['painting_id']}","Executor and published images retain verified hashes and RGB geometry",good,good)
        _check(ctx,f"outside:{row['painting_id']}","Every outside-mask pixel remains unchanged",good and row.get("changed_outside_pixels") == 0,row.get("changed_outside_pixels","unavailable"),0)
    complete = int(records.status.eq("completed").sum())
    _check(ctx,"primary_population","All ten frozen primary SD candidates are retained",complete == 10 and set(records.candidate_id) == set(ctx["worklist"].candidate_id),complete,10)
    checks = ctx["validation"].to_dataframe()
    _save(_path(ctx,ctx["policy"]["outputs"]["stage_checks"]),checks)
    path = _path(ctx,ctx["config"]["outputs"]["validation"])
    if path.exists():
        old = pd.read_csv(path,keep_default_na=False)
        checks = pd.concat([old.loc[~old.validation_stage.isin(checks.validation_stage.unique())],checks],ignore_index=True)
    _save(path,checks)
    summary = dict(stage=STAGE,model_id=MODEL,expected_candidates=10,completed_candidates=complete,failed_candidates=10-complete,
        reused_candidates=ctx["reused_candidates"],execution_fingerprint=ctx["execution_fingerprint"],
        recorded_case_runtime_seconds=float(pd.to_numeric(records.get("runtime_seconds",pd.Series(dtype=float)),errors="coerce").sum()),
        runtime_scope="original_case_calls_include_baseline_retry_exclude_model_load_smoke_and_resume_validation",
        validation_summary=ctx["validation"].summary(),notebook_completion_gate_passed=False,recorded_at_utc=utc_now_iso())
    _save(_path(ctx,ctx["policy"]["outputs"]["stage_summary"]),summary)
    runtime = pd.DataFrame([{k:v for k,v in summary.items() if k != "validation_summary"}])
    path = _path(ctx,ctx["config"]["outputs"]["runtime_summary"])
    if path.exists():
        old = pd.read_csv(path,keep_default_na=False,float_precision="round_trip")
        runtime = pd.concat([old.loc[~old.model_id.eq(MODEL)],runtime],ignore_index=True)
    _save(path,runtime)
    ctx["summary"] = summary; ctx["validation"].raise_for_blocking()
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
            for j,(pixels,title) in enumerate(((image,"Damaged input"),(image,"Selected repair mask"),(restored,"Stable Diffusion restoration"))):
                axes[i,j].imshow(pixels)
                if j == 1:
                    overlay = np.zeros((*mask.shape,4)); overlay[mask > 0] = [0,1,1,.4]
                    axes[i,j].imshow(overlay)
                axes[i,j].set_title(f"{row['painting_id']} | {title}",fontsize=9); axes[i,j].axis("off")
        fig.suptitle("D04 | SD 1.5 primary restorations — targeted prompts, 512px inference, seed 2026",fontsize=13)
        fig.text(.5,.012,"No clean references: visual inspection does not establish reconstruction accuracy.\n"
            "Source credits/licences: D03 artworks.csv; rd004 Tyler Bell CC BY 2.0; rd005 BeakheadIntrados CC BY-SA 4.0; rd006 The Met CC0.\n"
            "Other sources retain their recorded public-domain terms. Restorations, resizing and mask overlays are adaptations.",ha="center",fontsize=7)
        fig.tight_layout(rect=(0,.05,1,.97))
        path = _path(ctx,ctx["policy"]["outputs"][key]); path.parent.mkdir(parents=True,exist_ok=True)
        fig.savefig(path,dpi=130); plt.close(fig); paths.append(path)
    ctx["preview_paths"] = paths
    return paths
