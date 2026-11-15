"""D04 additional SD seeds with unchanged N11 inference and frozen prompts.

The small execution adapter is stage-owned so the already executed Batch 6
source, receipts and fingerprints remain immutable. Scientific algorithms are
imported from the original executor, not reimplemented here.
"""
from __future__ import annotations

import copy
from itertools import combinations
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import cv2
import numpy as np
import pandas as pd
from PIL import Image
import yaml

from . import real_damage_sd as primary
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
STAGE = "batch_7_sd_seeds"
SCOPE = "additional_seed"
_read, _save, _path = primary._read, primary._save, primary._path
_inputs, _assert_inputs = primary._inputs, primary._assert_inputs
release_pipeline = primary.release_pipeline


def _check(ctx,key,description,passed,observed,expected=True):
    checks = ValidationCollector()
    checks.extend(c for c in ctx["validation"].checks if (c.validation_stage,c.check_id) != (STAGE,key))
    checks.add(validation_stage=STAGE,check_id=key,check_description=description,
        passed=passed,observed=observed,expected=expected,severity="blocking")
    ctx["validation"] = checks


def audit_seed_design(plan):
    """Check exactly ten complete groups; the seed alone varies within a group."""
    d04._require(len(plan) == 40 and plan.candidate_id.is_unique and plan.restored_path.is_unique
        and plan.painting_id.nunique() == plan.uncertainty_group_id.nunique() == 10,"Wrong SD group population")
    invariants = sorted(set(plan.columns) - {"candidate_id","seed","candidate_role","restored_path"})
    for _,group in plan.groupby("uncertainty_group_id",sort=True):
        d04._require(len(group) == 4 and set(group.seed) == {2026,2027,2028,2029}
            and group.painting_id.nunique() == 1,"Incomplete or duplicate SD seed group")
        d04._require(all(group[c].nunique(dropna=False) == 1 for c in invariants),"Prompt, input or settings vary within a seed group")
        d04._require(group.loc[group.seed.eq(2026),"candidate_role"].eq("primary").all()
            and group.loc[~group.seed.eq(2026),"candidate_role"].eq(SCOPE).all(),"Incorrect SD seed roles")
    return plan.loc[plan.candidate_role.eq(SCOPE)].sort_values(["painting_id","seed"]).reset_index(drop=True)


def _verify_primaries(ctx):
    pctx = ctx["primary_context"]
    table = pd.read_csv(_path(ctx,ctx["config"]["outputs"]["candidates"]),keep_default_na=False,float_precision="round_trip")
    for row in pctx["worklist"].to_dict("records"):
        record = ctx["primary_records"].loc[ctx["primary_records"].candidate_id.eq(row["candidate_id"])].iloc[0].to_dict()
        primary._verify(pctx,row,record,"primary")
        match = table.loc[table.candidate_id.eq(row["candidate_id"])]
        d04._require(len(match) == 1 and all(match.iloc[0][k] == record[k] for k in
            ("model_id","status","restored_path","restored_sha256","execution_binding","prompt","negative_prompt","prompt_sha256","configuration_id"))
            and int(float(match.iloc[0]["seed"])) == 2026,"Primary SD table/receipt mismatch")
    for row in ctx["primary_snapshot"].to_dict("records"):
        match = table.loc[table.candidate_id.eq(row["candidate_id"])]
        d04._require(len(match) == 1 and all(match.iloc[0][k] == row[k] for k in ctx["primary_snapshot"].columns),"An existing primary candidate row changed")
        d04._require(sha256_file(resolve_repo_path(row["restored_path"],ctx["root"],must_exist=True)) == row["restored_sha256"],"An existing primary image changed")


def prepare_seeds(project_root,config_path):
    """Verify the completed primary run; construct a separate 30-candidate worklist."""
    root = Path(project_root).resolve()
    path = resolve_repo_path(config_path,root,must_exist=True)
    policy = yaml.safe_load(path.read_text(encoding="utf-8"))
    d04._require(policy["schema_version"] == "real_damage_sd_seeds_config.v1" and policy["stage"] == STAGE
        and policy["expected_candidates"] == 30 and policy["expected_groups"] == 10
        and policy["seeds"] == [2026,2027,2028,2029] and policy["additional_seeds"] == [2027,2028,2029]
        and policy["reuse_primary"] is True and policy["reuse_verified_batch_6_smoke_gate"] is True
        and policy["overwrite_unverified_outputs"] is False,"Unexpected additional-seed policy")
    for key in ("helper_source","tests","primary_config"):
        d04._relative(policy[key])
    for rel in policy["outputs"].values():
        d04._relative(rel)
    upstream = primary.prepare_sd(root,policy["primary_config"])
    output = upstream["output_root"]
    summary = _read(output / "work/sd/batch_summary.json")
    d04._require(summary["completed_candidates"] == 10 and summary["failed_candidates"] == 0
        and summary["execution_fingerprint"] == upstream["execution_fingerprint"]
        and summary["validation_summary"]["passed_count"] == summary["validation_summary"]["check_count"] == 216,"Batch 6 has not passed")
    declared = dict(stage_config=path,stage_helper=root / policy["helper_source"],stage_tests=root / policy["tests"],
        primary_summary=output / "work/sd/batch_summary.json",primary_checks=output / "work/sd/checks.csv",
        primary_smoke=output / "work/sd/smoke_summary.json")
    primary_records = []
    for row in upstream["worklist"].to_dict("records"):
        _,receipt = primary._locations(upstream,row,"primary")
        record = _read(receipt); primary._verify(upstream,row,record,"primary")
        d04._require(record.get("model_load_audit_path"),"Primary SD model-load audit missing")
        primary_records.append(record); declared[f"primary_receipt.{row['painting_id']}"] = receipt
        declared[f"primary_load.{row['painting_id']}"] = root / record["model_load_audit_path"]
    smoke = _read(declared["primary_smoke"])
    d04._require(smoke["execution_fingerprint"] == upstream["execution_fingerprint"] and smoke["seeds"] == [2026,2026,2027]
        and smoke["zero_mask_identity"] is True and smoke["primary_candidate_count"] == 0,"Invalid Batch 6 smoke handoff")
    smoke_base = upstream["worklist"].loc[upstream["worklist"].painting_id.eq(smoke["painting_id"])].iloc[0].to_dict()
    arrays = []
    for i,(seed,record) in enumerate(zip(smoke["seeds"],smoke["records"],strict=True),1):
        row = dict(smoke_base,candidate_id=f"{smoke_base['candidate_id']}__smoke_{i:02d}",candidate_role="technical_smoke",seed=seed)
        primary._verify(upstream,row,record,"smoke")
        with Image.open(root / record["restored_path"]) as pil:
            arrays.append(np.asarray(pil).copy())
    _,mask = _inputs(upstream,smoke_base)
    repeat,alternate = primary._difference(arrays[0],arrays[1],mask),primary._difference(arrays[0],arrays[2],mask)
    d04._require(repeat == smoke["fixed_repeat"] and alternate == smoke["alternate_seed"]
        and all(repeat[k] <= v for k,v in upstream["policy"]["repeat_tolerance"].items())
        and repeat["outside_different_pixels"] == alternate["outside_different_pixels"] == 0
        and alternate["inside_different_pixels"] > 0,"Saved SD smoke statistics failed revalidation")
    plan = pd.read_csv(output / upstream["config"]["outputs"]["candidate_plan"],keep_default_na=False,float_precision="round_trip")
    plan = primary._numeric_plan(plan.loc[plan.model_id.eq(MODEL)]).sort_values(["painting_id","seed"]).reset_index(drop=True)
    worklist = audit_seed_design(plan)
    table = pd.read_csv(output / upstream["config"]["outputs"]["candidates"],keep_default_na=False,float_precision="round_trip")
    snapshot = table.loc[table.candidate_role.eq("primary"),["candidate_id","model_id","candidate_role","status","restored_path","restored_sha256","execution_binding"]].copy()
    d04._require(len(snapshot) == 40 and snapshot.candidate_id.is_unique and snapshot.status.eq("completed").all()
        and snapshot.groupby("model_id").size().to_dict() == {m:10 for m in d04.PRIMARY_MODELS},"Primary population is incomplete")
    inventory,audit = audit_inventory_inputs(root,root / upstream["config"]["inputs"]["inventory"],
        root / upstream["config"]["inputs"]["inventory_run"],declared)
    checks = ValidationCollector()
    saved = pd.read_csv(output / "work/sd/checks.csv",keep_default_na=False)
    d04._require(len(saved) == 216 and saved.passed.all(),"Saved Batch 6 checks incomplete")
    for row in saved.to_dict("records"):
        checks.add(**row)
    bindings = {**upstream["stage_input_checksums"],**{to_repo_relative(p,root):sha256_file(p) for p in declared.values()}}
    ctx = dict(root=root,output_root=output,config=upstream["config"],policy=policy,baseline=upstream["baseline"],
        frozen=upstream["frozen"],frozen_input_checksums=upstream["frozen_input_checksums"],stage_input_checksums=bindings,
        assets=upstream["assets"],asset=upstream["asset"],packages=upstream["packages"],inventory=inventory,
        worklist=worklist,seed_plan=plan,primary_records=pd.DataFrame(primary_records),primary_context=upstream,
        primary_snapshot=snapshot,validation=checks)
    ctx["execution_fingerprint"] = d04._digest(dict(stage_inputs=bindings,primary_execution=upstream["execution_fingerprint"],
        readiness=ctx["frozen"]["readiness_fingerprint"],assets=ctx["assets"],packages=ctx["packages"],module_version=MODULE_VERSION))
    _verify_primaries(ctx)
    _check(ctx,"primary_handoff","Ten seed-2026 images and saved SD smoke checks remain valid",True,10,10)
    _check(ctx,"seed_population","Thirty additional candidates complete ten predeclared four-seed groups",True,len(worklist),30)
    _check(ctx,"fixed_conditions","Only the seed varies within each group; approved prompts and inputs stay fixed",True,10,10)
    _check(ctx,"pipeline_continuity","Pinned weights, original executor and numerical settings match Batch 6",True,ctx["baseline"]["model"]["configuration_id"])
    _check(ctx,"stage_inventory","Inventory covers additional-seed files and immutable primary evidence",bool(audit.passed.all()),audit.loc[~audit.passed].to_dict("records"),[])
    ctx["validation"].raise_for_blocking()
    return ctx


def _locations(ctx,row,scope=SCOPE):
    d04._require(scope == SCOPE and row["candidate_role"] == SCOPE and int(row["seed"]) in (2027,2028,2029),"Only additional SD seeds belong to Batch 7")
    return _path(ctx,row["restored_path"]),_path(ctx,f"work/sd_seeds/receipts/{row['candidate_id']}.json")


def _binding(ctx,row,scope=SCOPE):
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
        audit_path = _path(ctx,f"work/sd_seeds/loads/{uuid4().hex}.json")
        _save(audit_path,audit)
        ctx.update(pipeline=pipeline,device=device,load_audit=audit,load_audit_path=audit_path)
    return ctx["pipeline"],ctx["device"]


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


def execute_case(ctx,row,scope=SCOPE,executor=None):
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
    job_root = _path(ctx,f"work/sd_seeds/jobs/{scope}/{row['candidate_id']}")
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


def run_candidates(ctx,progress=print,executor=None):
    _assert_inputs(ctx)
    _verify_primaries(ctx)
    records,reused = [],0
    for i,row in enumerate(ctx["worklist"].to_dict("records"),1):
        record,cached = execute_case(ctx,row,executor=executor)
        records.append(record); reused += int(cached)
        primary._merge_candidates(ctx,pd.DataFrame([record]))
        progress(f"SD additional {i}/30 | {row['painting_id']} | seed {row['seed']} | {record['status']} | reused={cached}")
    ctx.update(records=pd.DataFrame(records),reused_candidates=reused)
    return ctx


def _group_tables(ctx):
    columns = ["painting_id","category","case_id","uncertainty_group_id","candidate_id","candidate_role","seed",
        "prompt_id","prompt_sha256","negative_prompt","configuration_fingerprint","input_image_sha256","mask_sha256",
        "restored_path","restored_sha256","status"]
    all_sd = pd.concat([ctx["primary_records"],ctx["records"]],ignore_index=True)
    members = all_sd.loc[all_sd.status.eq("completed"),columns].sort_values(["painting_id","seed"]).reset_index(drop=True)
    pairs = []
    for group_id,plan in ctx["seed_plan"].groupby("uncertainty_group_id",sort=True):
        group = members.loc[members.uncertainty_group_id.eq(group_id)].sort_values("seed")
        complete = len(group) == 4 and set(group.seed) == {2026,2027,2028,2029} and set(group.candidate_id) == set(plan.candidate_id)
        _check(ctx,f"group:{group_id}","Four distinct predeclared seeds are present for this painting",complete,len(group),4)
        if complete:
            for a,b in combinations(group.to_dict("records"),2):
                pairs.append(dict(uncertainty_group_id=group_id,painting_id=a["painting_id"],case_id=a["case_id"],
                    candidate_id_a=a["candidate_id"],candidate_id_b=b["candidate_id"],seed_a=a["seed"],seed_b=b["seed"],
                    restored_path_a=a["restored_path"],restored_path_b=b["restored_path"],
                    restored_sha256_a=a["restored_sha256"],restored_sha256_b=b["restored_sha256"],
                    purpose="predeclared_pair_membership_no_variability_metric_computed"))
    pair_table = pd.DataFrame(pairs)
    _check(ctx,"pair_population","Ten groups contain six unique unordered pairs each",len(pairs) == 60,len(pairs),60)
    return members,pair_table


def validate_results(ctx):
    records = ctx["records"]
    for row in records.to_dict("records"):
        good = row["status"] == "completed"
        _check(ctx,f"completed:{row['candidate_id']}","Additional SD candidate completed",good,row["status"],"completed")
        if good:
            planned = ctx["worklist"].loc[ctx["worklist"].candidate_id.eq(row["candidate_id"])].iloc[0].to_dict()
            _verify(ctx,planned,row,SCOPE)
        _check(ctx,f"output:{row['candidate_id']}","Published PNG, executor PNG and load audit retain verified hashes",good,good)
        _check(ctx,f"outside:{row['candidate_id']}","Every outside-mask pixel remains unchanged",good and row.get("changed_outside_pixels") == 0,row.get("changed_outside_pixels","unavailable"),0)
    complete = int(records.status.eq("completed").sum())
    _check(ctx,"additional_population","All thirty frozen additional candidates are retained",complete == 30 and set(records.candidate_id) == set(ctx["worklist"].candidate_id),complete,30)
    _verify_primaries(ctx)
    _check(ctx,"primary_preservation","The forty primary candidates and images remain unchanged",True,len(ctx["primary_snapshot"]),40)
    members,pairs = _group_tables(ctx)
    table = pd.read_csv(_path(ctx,ctx["config"]["outputs"]["candidates"]),keep_default_na=False,float_precision="round_trip")
    ids = set(ctx["primary_snapshot"].candidate_id) | set(ctx["worklist"].candidate_id)
    _check(ctx,"total_population","The table contains exactly forty primary and thirty additional candidates",len(table) == 70
        and table.candidate_id.is_unique and set(table.candidate_id) == ids and table.status.eq("completed").all(),len(table),70)
    _save(_path(ctx,ctx["policy"]["outputs"]["group_members"]),members)
    _save(_path(ctx,ctx["policy"]["outputs"]["seed_pair_plan"]),pairs)
    checks = ctx["validation"].to_dataframe()
    _save(_path(ctx,ctx["policy"]["outputs"]["stage_checks"]),checks)
    path = _path(ctx,ctx["config"]["outputs"]["validation"])
    if path.exists():
        old = pd.read_csv(path,keep_default_na=False)
        checks = pd.concat([old.loc[~old.validation_stage.isin(checks.validation_stage.unique())],checks],ignore_index=True)
    _save(path,checks)
    summary = dict(stage=STAGE,model_id=MODEL,expected_candidates=30,completed_candidates=complete,failed_candidates=30-complete,
        reused_candidates=ctx["reused_candidates"],reused_primary_candidates=10,execution_fingerprint=ctx["execution_fingerprint"],
        recorded_case_runtime_seconds=float(pd.to_numeric(records.get("runtime_seconds",pd.Series(dtype=float)),errors="coerce").sum()),
        runtime_scope="additional_seed_case_calls_only_excludes_model_load_primary_calls_and_resume_validation",
        completed_seed_groups=int(len(pairs)//6),planned_unique_seed_pairs=60,
        validation_summary=ctx["validation"].summary(),notebook_completion_gate_passed=False,recorded_at_utc=utc_now_iso())
    _save(_path(ctx,ctx["policy"]["outputs"]["stage_summary"]),summary)
    # The model-level primary runtime table remains the four-method comparison.
    _save(_path(ctx,ctx["policy"]["outputs"]["runtime"]),pd.DataFrame([{k:v for k,v in summary.items() if k != "validation_summary"}]))
    ctx.update(summary=summary,group_members=members,seed_pair_plan=pairs)
    ctx["validation"].raise_for_blocking()
    return ctx


def render_previews(ctx):
    import matplotlib.pyplot as plt
    ctx["validation"].raise_for_blocking()
    paths = []
    painting_ids = sorted(ctx["group_members"].painting_id.unique())
    for key,start,end in (("preview_first",0,5),("preview_second",5,10)):
        fig,axes = plt.subplots(5,5,figsize=(19,17))
        for i,pid in enumerate(painting_ids[start:end]):
            group = ctx["group_members"].loc[ctx["group_members"].painting_id.eq(pid)].sort_values("seed")
            planned = ctx["worklist"].loc[ctx["worklist"].painting_id.eq(pid)].iloc[0].to_dict()
            source,mask = _inputs(ctx,planned)
            axes[i,0].imshow(source)
            overlay = np.zeros((*mask.shape,4)); overlay[mask > 0] = [0,1,1,.4]
            axes[i,0].imshow(overlay); axes[i,0].set_title(f"{pid} | Input + repair mask",fontsize=10)
            for j,row in enumerate(group.to_dict("records"),1):
                with Image.open(ctx["root"] / row["restored_path"]) as pil:
                    axes[i,j].imshow(np.asarray(pil).copy())
                axes[i,j].set_title(f"{pid} | Seed {int(row['seed'])}",fontsize=10)
            for ax in axes[i]: ax.axis("off")
        fig.suptitle("D04 | Fixed targeted prompt, four SD seeds per painting — seed 2026 reused from Batch 6",fontsize=14)
        fig.text(.5,.012,"Repeated outputs describe variability, not correctness or calibrated confidence. No best-seed selection.\n"
            "Source credits/licences: D03 artworks.csv; rd004 Tyler Bell CC BY 2.0; rd005 BeakheadIntrados CC BY-SA 4.0; rd006 The Met CC0.\n"
            "Other sources retain their recorded public-domain terms. Restorations, resizing and mask overlays are adaptations.",ha="center",fontsize=8)
        fig.tight_layout(rect=(0,.05,1,.97))
        path = _path(ctx,ctx["policy"]["outputs"][key]); path.parent.mkdir(parents=True,exist_ok=True)
        fig.savefig(path,dpi=130); plt.close(fig); paths.append(path)
    ctx["preview_paths"] = paths
    return paths
