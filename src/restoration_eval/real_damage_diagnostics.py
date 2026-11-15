"""Reference-free D04 diagnostics and fixed-prompt seed disagreement.

N18/N19 compute candidate-to-candidate variability. No photograph is substituted
for a clean reference. Boundary descriptors report raw band contrasts, not the
reference-relative boundary errors used by the controlled study.
"""
from __future__ import annotations

import gc
import importlib.util
from importlib.metadata import version
from io import BytesIO
from itertools import combinations
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000
import yaml

from . import real_damage_sd_seeds as prior
from . import real_damage_restoration as d04
from . import real_damage_readiness as readiness
from . import diffusion_uncertainty as uncertainty
from . import spatial_explanations as spatial
from . import metrics_lpips as lpips_metrics
from .regions import build_standard_regions
from .manifests import sha256_file, utc_now_iso
from .paths import resolve_repo_path, to_repo_relative
from .real_damage_dataset import audit_inventory_inputs
from .validation import ValidationCollector

MODULE_VERSION = "1.0.0"
STAGE = "batch_8_diagnostics"
MODEL = d04.SD_MODEL
PIXEL_REGIONS = ("content_region","masked_region","mask_bbox_crop","boundary_ring","outside_mask_content")
_read, _save, _path = prior._read, prior._save, prior._path


def _check(ctx,key,description,passed,observed,expected=True):
    checks = ValidationCollector()
    checks.extend(c for c in ctx["validation"].checks if (c.validation_stage,c.check_id) != (STAGE,key))
    checks.add(validation_stage=STAGE,check_id=key,check_description=description,passed=passed,
        observed=observed,expected=expected,severity="blocking")
    ctx["validation"] = checks


def inspect_metric_assets():
    import torch
    spec = importlib.util.find_spec("lpips")
    d04._require(spec is not None and spec.origin is not None,"LPIPS package is unavailable")
    paths = {"alexnet_backbone":Path(torch.hub.get_dir()) / "checkpoints/alexnet-owt-7be5be79.pth",
        "lpips_alex_v01":Path(spec.origin).parent / "weights/v0.1/alex.pth"}
    records = []
    for name,path in paths.items():
        d04._require(path.is_file(),f"Required cached LPIPS asset missing; no download is attempted: {path}")
        records.append(dict(name=name,path=str(path.resolve()),sha256=sha256_file(path),size_bytes=path.stat().st_size))
    d04._require(records[0]["sha256"].startswith("7be5be79"),"AlexNet cache does not match its published hash prefix")
    return records


def _assert_inputs(ctx):
    for rel,digest in ctx["input_checksums"].items():
        d04._require(sha256_file(ctx["root"] / rel) == digest,f"Diagnostic input changed: {rel}")
    for record in ctx["assets"]:
        d04._require(sha256_file(Path(record["path"])) == record["sha256"],f"LPIPS weight changed: {record['name']}")
    for name,expected in ctx["packages"].items():
        d04._require(version(name) == expected,f"Diagnostic dependency changed: {name}")


def candidate_regions(ctx,row):
    source = uncertainty.load_rgb_array(row["input_image_path"],ctx["root"])
    mask = uncertainty.load_mask_array(row["mask_path"],ctx["root"]) >= 128
    bbox = tuple(int(row[k]) for k in ("content_x_min","content_y_min","content_x_max","content_y_max"))
    regions = build_standard_regions(mask,content_bbox=bbox,mask_bbox_margin=8,boundary_width_pixels=3)
    d04._require(mask.shape == source.shape[:2] and source.shape[:2] == (int(row["output_height"]),int(row["output_width"])),"Invalid diagnostic input geometry")
    d04._require(not np.any(mask & ~regions["content_region"].mask),"Repair mask crosses into canvas padding")
    d04._require(all(regions[k].validity_status == "valid" for k in (*PIXEL_REGIONS,"inner_boundary_band","outer_boundary_band")),"A required evaluation region is empty")
    return source,mask,regions


def prepare_diagnostics(project_root,config_path):
    """Read and verify completed restorations, geometry, metric code and local weights."""
    root = Path(project_root).resolve();path = resolve_repo_path(config_path,root,must_exist=True)
    policy = yaml.safe_load(path.read_text(encoding="utf-8"))
    d04._require(policy["schema_version"] == "real_damage_diagnostics_config.v1" and policy["stage"] == STAGE
        and policy["regions"]["pixel_regions"] == list(PIXEL_REGIONS)
        and policy["regions"]["learned_regions"] == ["content_region","mask_bbox_crop"]
        and policy["regions"]["mask_bbox_margin_pixels"] == 8 and policy["regions"]["boundary_width_pixels"] == 3
        and all(policy["evidence_policy"][k] is False for k in ("damaged_input_is_clean_reference","edit_magnitude_is_reconstruction_error",
        "boundary_gap_is_reference_error","seed_disagreement_is_calibrated_confidence","combined_score")),"Diagnostic evidence policy changed")
    expected = dict(candidates=70,primary_candidates=40,sd_candidates=40,groups=10,unique_pairs=60,
        technical_rows=70,diagnostic_rows=70,pairwise_rows=720,group_summary_rows=220,maps=10)
    d04._require(policy["expected"] == expected,"Unexpected diagnostic population")
    for rel in [policy[k] for k in ("helper_source","tests","upstream_config","geometry","cases","artworks","uncertainty_config","spatial_config","lpips_config")]+list(policy["shared_sources"].values())+list(policy["outputs"].values()):
        d04._relative(rel)
    upstream = prior.prepare_seeds(root,policy["upstream_config"]);output = upstream["output_root"]
    summary = _read(output / "work/sd_seeds/batch_summary.json")
    d04._require(summary["completed_candidates"] == 30 and summary["failed_candidates"] == 0
        and summary["execution_fingerprint"] == upstream["execution_fingerprint"]
        and summary["validation_summary"]["passed_count"] == summary["validation_summary"]["check_count"] == 325,"Batch 7 has not passed")
    declared = dict(stage_config=path,candidates=output / upstream["config"]["outputs"]["candidates"],
        seed_summary=output / "work/sd_seeds/batch_summary.json",seed_checks=output / "work/sd_seeds/checks.csv",
        seed_members=output / "work/sd_seeds/group_members.csv",seed_pairs=output / "work/sd_seeds/seed_pair_plan.csv")
    declared.update({key:root / policy[key] for key in ("helper_source","tests","geometry","cases","artworks","uncertainty_config","spatial_config","lpips_config")})
    declared.update({f"shared.{key}":root / value for key,value in policy["shared_sources"].items()})
    for row in upstream["worklist"].to_dict("records"):
        _,receipt = prior._locations(upstream,row);record = _read(receipt);prior._verify(upstream,row,record,prior.SCOPE)
        declared[f"seed_receipt.{row['candidate_id']}"] = receipt
    table = pd.read_csv(declared["candidates"],keep_default_na=False,float_precision="round_trip")
    ids = set(upstream["primary_snapshot"].candidate_id) | set(upstream["worklist"].candidate_id)
    d04._require(len(table) == 70 and table.candidate_id.is_unique and set(table.candidate_id) == ids
        and table.status.eq("completed").all() and not table.has_clean_reference.any()
        and table.clean_image_path.eq("").all(),"Incomplete candidates or unexpected clean reference")
    for row in table.to_dict("records"):
        file = resolve_repo_path(row["restored_path"],root,must_exist=True)
        d04._require(sha256_file(file) == row["restored_sha256"],"Candidate image changed")
        declared[f"candidate.{row['candidate_id']}"] = file
    members = pd.read_csv(declared["seed_members"],keep_default_na=False)
    pairs = pd.read_csv(declared["seed_pairs"],keep_default_na=False)
    sd_table = table.loc[table.model_id.eq(MODEL)]
    d04._require(len(members) == 40 and set(members.candidate_id) == set(sd_table.candidate_id)
        and len(pairs) == 60 and not pairs.duplicated(["candidate_id_a","candidate_id_b"]).any(),"Seed membership mismatch")
    for row in members.to_dict("records"):
        current = table.loc[table.candidate_id.eq(row["candidate_id"])].iloc[0]
        d04._require(current.restored_sha256 == row["restored_sha256"] and current.restored_path == row["restored_path"]
            and int(float(current.seed)) == row["seed"],"Seed-member identity mismatch")
    geometry = pd.read_csv(declared["geometry"],keep_default_na=False)
    cases = pd.read_csv(declared["cases"],keep_default_na=False)
    artworks = pd.read_csv(declared["artworks"],keep_default_na=False)
    geo_cols = ["painting_id","content_x_min","content_y_min","content_x_max","content_y_max"]
    table = table.merge(geometry[geo_cols],on="painting_id",how="left",validate="many_to_one")
    table = table.merge(cases[["case_id","damage_or_degradation_type","target_damage_fraction","realized_damage_fraction"]],on="case_id",how="left",validate="many_to_one")
    table = table.merge(artworks[["painting_id","style_or_period"]],on="painting_id",how="left",validate="many_to_one")
    table["case_label"] = table.case_id
    table["mask_or_effect_path"] = table.mask_path
    table["execution_role"] = "repeated_seed_uncertainty"
    table["seed_count"] = table["expected_seed_count"] = 4
    table["seed_coverage_status"] = "complete"
    table["style_or_period"] = table.style_or_period.replace("","unclassified")
    table.loc[table.model_id.eq(MODEL),"seed"] = pd.to_numeric(table.loc[table.model_id.eq(MODEL),"seed"]).astype(int)
    uncertainty_config = uncertainty.load_diffusion_uncertainty_config(declared["uncertainty_config"])
    spatial_config = spatial.load_spatial_explanations_config(declared["spatial_config"])
    lpips_config = lpips_metrics.load_lpips_config(declared["lpips_config"])
    d04._require(lpips_config["lpips_metrics"]["model"]["network"] == "alex"
        and lpips_config["lpips_metrics"]["model"]["lpips_version"] == "0.1","LPIPS configuration differs from N14")
    assets = inspect_metric_assets()
    packages = {name:version(name) for name in ("torch","torchvision","lpips","numpy","scipy","scikit-image","pandas","Pillow","matplotlib")}
    inventory,audit = audit_inventory_inputs(root,root / upstream["config"]["inputs"]["inventory"],root / upstream["config"]["inputs"]["inventory_run"],declared)
    bindings = {**upstream["stage_input_checksums"],**upstream["frozen_input_checksums"],**{to_repo_relative(p,root):sha256_file(p) for p in declared.values()}}
    checks = ValidationCollector();saved = pd.read_csv(declared["seed_checks"],keep_default_na=False)
    d04._require(len(saved) == 325 and saved.passed.all(),"Saved Batch 7 checks incomplete")
    for row in saved.to_dict("records"):checks.add(**row)
    ctx = dict(root=root,output_root=output,config=upstream["config"],policy=policy,candidates=table,validation=checks,inventory=inventory,
        input_checksums=bindings,assets=assets,packages=packages,uncertainty_config=uncertainty_config,spatial_config=spatial_config,
        lpips_config=lpips_config,seed_pair_plan=pairs,upstream_execution_fingerprint=upstream["execution_fingerprint"])
    ctx["execution_fingerprint"] = d04._digest(dict(inputs=bindings,assets=assets,packages=packages,module_version=MODULE_VERSION))
    region_rows = []
    for row in table.drop_duplicates("case_id").to_dict("records"):
        _,_,regions = candidate_regions(ctx,row)
        for region_id in (*PIXEL_REGIONS,"inner_boundary_band","outer_boundary_band"):
            region_rows.append(dict(case_id=row["case_id"],painting_id=row["painting_id"],**regions[region_id].to_record()))
    ctx["region_manifest"] = pd.DataFrame(region_rows)
    _check(ctx,"restoration_handoff","All seventy completed candidates retain verified images and seed receipts",True,70,70)
    _check(ctx,"reference_policy","Physical inputs are never clean references; evidence populations remain labelled",True,"40 primary; 40 SD including 30 additional")
    _check(ctx,"seed_groups","Ten fixed-prompt four-seed groups and sixty pairs are available",True,60,60)
    _check(ctx,"regions","Canonical content, mask, crop and boundary regions exclude padding",True,len(region_rows),70)
    _check(ctx,"metric_assets","N14 LPIPS configuration and required cached weights are available",True,assets)
    _check(ctx,"stage_inventory","Inventory covers diagnostic sources and frozen restoration evidence",bool(audit.passed.all()),audit.loc[~audit.passed].to_dict("records"),[])
    ctx["validation"].raise_for_blocking()
    return ctx


def render_outputs(ctx):
    """Use one display scale; preserve unmodified numerical arrays separately."""
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize

    loaded = []
    for entry in ctx["maps"].to_dict("records"):
        path = ctx["root"] / entry["array_path"]
        d04._require(sha256_file(path) == entry["array_sha256"],"Uncertainty array changed")
        with np.load(path,allow_pickle=False) as arrays:
            values = arrays["pixel_rgb_std"].copy();mask = arrays["repair_mask"].astype(bool)
        row = ctx["candidates"].loc[ctx["candidates"].uncertainty_group_id.eq(entry["uncertainty_group_id"])].sort_values("seed").iloc[0]
        source,_,regions = candidate_regions(ctx,row)
        restored = uncertainty.load_rgb_array(row.restored_path,ctx["root"])
        loaded.append((entry,row,source,restored,values,mask,regions["content_region"].mask))
    vmax = max(float(np.percentile(np.concatenate([item[4][item[5]] for item in loaded]),99)),1e-7)
    ctx["display_vmax"] = vmax
    credit = ("Source credits/licences: D03 artworks.csv; rd004 Tyler Bell CC BY 2.0; rd005 BeakheadIntrados CC BY-SA 4.0; rd006 The Met CC0.\n"
        "Other sources retain recorded public-domain terms. Resizing, restorations and mask overlays are adaptations.")

    def draw(axes,item):
        entry,row,source,restored,values,mask,content = item
        axes[0].imshow(source)
        overlay=np.zeros((*mask.shape,4));overlay[mask]=[0,1,1,.35]
        axes[0].imshow(overlay);axes[0].set_title(f"{row.painting_id} | Damaged input + repair mask",fontsize=9)
        axes[1].imshow(restored);axes[1].set_title("SD seed 2026 | same targeted prompt",fontsize=9)
        axes[2].imshow(np.ma.array(values,mask=~content),cmap="magma",vmin=0,vmax=vmax)
        axes[2].contour(mask.astype(float),levels=[.5],colors="cyan",linewidths=.45)
        axes[2].set_title("Four-seed RGB standard deviation",fontsize=9)
        for ax in axes:ax.axis("off")

    map_records=[]
    for item in loaded:
        entry=item[0];fig,axes=plt.subplots(1,3,figsize=(12,4.5))
        draw(axes,item);fig.subplots_adjust(bottom=.24,right=.92,wspace=.04)
        fig.colorbar(ScalarMappable(norm=Normalize(0,vmax),cmap="magma"),ax=axes.tolist(),fraction=.025,pad=.02,label="RGB std (0–1 units)")
        fig.text(.5,.14,"Disagreement is not error or calibrated confidence. Shared masked p99 display ceiling; raw arrays remain unclipped.",ha="center",fontsize=8)
        fig.text(.5,.04,credit,ha="center",fontsize=7)
        path=_path(ctx,ctx["config"]["outputs"]["uncertainty_preview_template"].format(group_id=entry["uncertainty_group_id"]))
        path.parent.mkdir(parents=True,exist_ok=True);fig.savefig(path,dpi=130);plt.close(fig)
        map_records.append(dict(entry,preview_path=to_repo_relative(path,ctx["root"]),preview_sha256=sha256_file(path),
            display_vmin=0.,display_vmax=vmax,display_clipped_mask_fraction=float((item[4][item[5]]>vmax).mean()),
            units="normalized_RGB_std_ddof0",interpretation="empirical_seed_disagreement_not_confidence"))
    previews=[]
    for start,key in ((0,"preview_first"),(5,"preview_second")):
        fig,axes=plt.subplots(5,3,figsize=(13,18))
        for i,item in enumerate(loaded[start:start+5]):draw(axes[i],item)
        fig.suptitle("D04 | Same targeted prompt, four seeds — empirical variability",fontsize=14)
        fig.subplots_adjust(top=.96,bottom=.10,right=.91,hspace=.12,wspace=.05)
        fig.colorbar(ScalarMappable(norm=Normalize(0,vmax),cmap="magma"),ax=axes.ravel().tolist(),fraction=.018,pad=.02,label="RGB std (0–1 units); shared scale")
        fig.text(.5,.065,"Cyan: selected repair region. Display ceiling: pooled masked p99; raw arrays are not clipped.\nVariation does not identify a correct reconstruction. Identical preserved context has approximately zero variability.",ha="center",fontsize=9)
        fig.text(.5,.025,credit,ha="center",fontsize=8)
        path=_path(ctx,ctx["policy"]["outputs"][key]);fig.savefig(path,dpi=130);plt.close(fig);previews.append(path)
    primary=ctx["diagnostics"].loc[ctx["diagnostics"].candidate_role.eq("primary")]
    pids=sorted(primary.painting_id.unique());fig,axes=plt.subplots(2,1,figsize=(12,8))
    for ax,field,label in zip(axes,("Lstar_gap","delta_e_gap"),("Absolute mean-band L* gap","CIEDE2000 between band means")):
        for i,(model,frame) in enumerate(primary.groupby("model_id",sort=True)):
            frame=frame.set_index("painting_id").loc[pids]
            ax.scatter(np.arange(10)+(i-1.5)*.12,frame[f"restored_boundary_{field}"],label=model,s=26)
        inputs=primary.drop_duplicates("painting_id").set_index("painting_id").loc[pids]
        ax.scatter(np.arange(10),inputs[f"input_boundary_{field}"],marker="x",c="black",label="damaged input",s=38)
        ax.set_xticks(np.arange(10),pids);ax.set_ylabel(label);ax.grid(axis="y",alpha=.2)
    axes[0].legend(ncol=3,fontsize=8)
    fig.suptitle("D04 | Raw boundary contrast — forty primary restorations",fontsize=14)
    fig.text(.5,.025,"Inner/outer three-pixel bands. Natural contours influence these values; lower values do not establish a better restoration.",ha="center",fontsize=9)
    fig.tight_layout(rect=(0,.055,1,.96));path=_path(ctx,ctx["policy"]["outputs"]["boundary_figure"])
    fig.savefig(path,dpi=130);plt.close(fig);previews.append(path)
    ctx.update(maps=pd.DataFrame(map_records),preview_paths=previews)
    _save(_path(ctx,ctx["policy"]["outputs"]["map_manifest"]),ctx["maps"])
    return previews


def validate_results(ctx):
    """Audit populations, pair membership, maps and resumable output provenance."""
    _assert_inputs(ctx)
    table=ctx["candidates"];tech=ctx["technical"];diag=ctx["diagnostics"]
    pairs=ctx["seed_pairwise"];summaries=ctx["uncertainty_summary"]
    _check(ctx,"candidate_tables","Both diagnostics tables cover all seventy candidates exactly once",
        len(tech)==len(diag)==70 and tech.candidate_id.is_unique and diag.candidate_id.is_unique
        and set(tech.candidate_id)==set(diag.candidate_id)==set(table.candidate_id),[len(tech),len(diag)],[70,70])
    _check(ctx,"primary_population","Forty primary candidates remain a separate analysis population",
        tech.candidate_role.eq("primary").sum()==diag.candidate_role.eq("primary").sum()==40,40,40)
    outside=tech[["changed_outside_pixels","changed_outside_content_pixels","changed_padding_pixels"]]
    _check(ctx,"preservation","All outside-mask pixels, including canvas padding, remain unchanged",outside.eq(0).all().all(),int(outside.to_numpy().max()),0)
    numeric=diag[["masked_edit_rgb_mean","masked_edit_rgb_p95","inside_change_fraction","input_boundary_Lstar_gap",
        "restored_boundary_Lstar_gap","input_boundary_delta_e_gap","restored_boundary_delta_e_gap"]]
    _check(ctx,"descriptors","Edit and raw boundary descriptors are finite and nonnegative",
        np.isfinite(numeric.to_numpy()).all() and numeric.ge(0).all().all() and numeric.iloc[:,:3].le(1).all().all(),numeric.shape)
    keys=["uncertainty_group_id","candidate_id_a","candidate_id_b","metric_name","region_id"]
    _check(ctx,"pair_rows","Sixty unordered pairs provide twelve distinct measurements each",len(pairs)==720 and not pairs.duplicated(keys).any(),len(pairs),720)
    allowed={(metric,region) for metric in ("pairwise_rgb_mae","pairwise_rgb_rmse") for region in PIXEL_REGIONS}
    allowed|={("pairwise_lpips_distance",region) for region in ("content_region","mask_bbox_crop")}
    _check(ctx,"metric_scope","Only candidate-to-candidate RGB and rectangular-crop LPIPS measurements are present",
        set(zip(pairs.metric_name,pairs.region_id))==allowed and np.isfinite(pairs.value).all() and pairs.value.ge(-1e-6).all(),sorted(set(pairs.metric_name)))
    _check(ctx,"summary_rows","Each of ten groups has twenty-two finite summary values",len(summaries)==220
        and not summaries.duplicated(["uncertainty_group_id","metric_name","region_id","summary_statistic"]).any()
        and np.isfinite(summaries.value).all(),len(summaries),220)
    for gid,group in table.loc[table.model_id.eq(MODEL)].groupby("uncertainty_group_id",sort=True):
        ordered=group.sort_values("seed");frame=pairs.loc[pairs.uncertainty_group_id.eq(gid)]
        expected={(a.candidate_id,b.candidate_id,int(a.seed),int(b.seed)) for a,b in combinations(list(ordered.itertuples()),2)}
        actual=set(frame[["candidate_id_a","candidate_id_b","seed_a","seed_b"]].itertuples(index=False,name=None))
        planned=ctx["seed_pair_plan"].loc[ctx["seed_pair_plan"].uncertainty_group_id.eq(gid)]
        planned=set(planned[["candidate_id_a","candidate_id_b","seed_a","seed_b"]].itertuples(index=False,name=None))
        complete=len(group)==4 and set(group.seed)=={2026,2027,2028,2029} and actual==expected==planned
        complete=complete and all(set(zip(part.metric_name,part.region_id))==allowed for _,part in frame.groupby(["candidate_id_a","candidate_id_b"]))
        _check(ctx,f"pairs:{gid}","Four unchanged seeds yield the six planned pairs and twelve measurements per pair",complete,len(frame),72)
        entry=ctx["maps"].loc[ctx["maps"].uncertainty_group_id.eq(gid)].iloc[0]
        array_path=ctx["root"]/entry.array_path
        d04._require(sha256_file(array_path)==entry.array_sha256,"Uncertainty array changed")
        with np.load(array_path,allow_pickle=False) as arrays:
            values=arrays["pixel_rgb_std"];mask=arrays["repair_mask"].astype(bool)
            _,expected_mask,regions=candidate_regions(ctx,ordered.iloc[0])
            map_ok=(values.shape==mask.shape==expected_mask.shape and np.isfinite(values).all() and (values>=0).all()
                and np.array_equal(mask,expected_mask) and np.array_equal(arrays["content_mask"],regions["content_region"].mask)
                and set(arrays["seeds"].tolist())=={2026,2027,2028,2029}
                and float(values[~mask].max())<=ctx["policy"]["outside_float_tolerance"])
        _check(ctx,f"map:{gid}","Raw map retains correct geometry, seeds and unchanged outside-mask context",map_ok,values.shape)
        group_summary=summaries.loc[summaries.uncertainty_group_id.eq(gid)]
        consistent=len(group_summary)==22
        for record in group_summary.to_dict("records"):
            if record["summary_statistic"]=="pair_mean":
                wanted=frame.loc[frame.metric_name.eq(record["metric_name"]) & frame.region_id.eq(record["region_id"]),"value"].mean()
            else:
                selected=values[regions[record["region_id"]].mask]
                wanted=float(selected.mean()) if record["metric_name"]=="pixel_rgb_std_mean" else float(np.percentile(selected,95))
            consistent=consistent and bool(np.isclose(record["value"],wanted,atol=1e-7,rtol=1e-6))
        _check(ctx,f"summary:{gid}","Summary values agree with raw maps or the six saved pair measurements",consistent,len(group_summary),22)
    receipts=list((ctx["output_root"]/"work/diagnostics/checkpoints").glob("*/*.json"))
    verified=len(receipts)==80
    runtimes={"candidate":0.,"group":0.}
    for path in receipts:
        receipt=_read(path);verified=verified and receipt["status"]=="completed"
        runtimes[path.parent.name]+=receipt.get("runtime_seconds",0.)
        verified=verified and all(sha256_file(ctx["root"]/rel)==digest for rel,digest in receipt.get("files",{}).items())
    _check(ctx,"checkpoints","Seventy candidate and ten seed-group checkpoints retain verified output hashes",verified,len(receipts),80)
    previews=list(ctx["preview_paths"])+[ctx["root"]/rel for rel in ctx["maps"].preview_path]
    for path in previews:
        with Image.open(path) as image:image.verify()
    _check(ctx,"figures","Ten case maps, two overview sheets and a primary boundary figure are readable",len(previews)==13,len(previews),13)
    _check(ctx,"no_reference_claim","Damaged inputs have not been labelled clean references",
        not tech.has_clean_reference.any() and not tech.reference_fidelity_metrics_applicable.any(),False,False)
    checks=ctx["validation"].to_dataframe()
    _save(_path(ctx,ctx["policy"]["outputs"]["stage_checks"]),checks)
    _save(_path(ctx,ctx["config"]["outputs"]["validation"]),checks)
    ctx["summary"]=dict(stage=STAGE,execution_fingerprint=ctx["execution_fingerprint"],
        completed_candidates=len(tech),primary_candidates=40,sd_candidates=40,completed_seed_groups=10,unique_seed_pairs=60,
        pairwise_rows=len(pairs),group_summary_rows=len(summaries),map_count=len(ctx["maps"]),
        reused_candidate_diagnostics=ctx["reused_candidate_diagnostics"],reused_uncertainty_groups=ctx["reused_uncertainty_groups"],
        candidate_processing_seconds=runtimes["candidate"],group_processing_seconds_including_first_model_load=runtimes["group"],
        display_vmax=ctx["display_vmax"],validation_summary=ctx["validation"].summary(),
        notebook_completion_gate_passed=False,completed_at_utc=utc_now_iso())
    _save(_path(ctx,ctx["policy"]["outputs"]["stage_summary"]),ctx["summary"])
    ctx["validation"].raise_for_blocking()
    return ctx["summary"]


def _checkpoint(ctx,kind,key,paths,compute):
    """Reuse hash-verified complete units; only owned started units can be recomputed."""
    receipt = _path(ctx,f"work/diagnostics/checkpoints/{kind}/{key}.json")
    binding = d04._digest(dict(execution=ctx["execution_fingerprint"],kind=kind,key=key,paths=[str(p.relative_to(ctx["output_root"])) for p in paths]))
    if receipt.exists():
        state = _read(receipt);d04._require(state["binding"] == binding,"Diagnostic checkpoint inputs changed")
        if state["status"] == "completed":
            d04._require(set(state["files"]) == {to_repo_relative(p,ctx["root"]) for p in paths},"Diagnostic checkpoint file list changed")
            for rel,digest in state["files"].items():
                d04._require(sha256_file(ctx["root"] / rel) == digest,f"Diagnostic output changed: {rel}")
            return True
        d04._require(state["status"] == "started","Unknown diagnostic checkpoint state")
    else:
        d04._require(not any(p.exists() for p in paths),"Unverified diagnostic output cannot be overwritten")
        _save(receipt,dict(binding=binding,status="started",started_at_utc=utc_now_iso()))
    started = perf_counter();compute()
    _save(receipt,dict(binding=binding,status="completed",runtime_seconds=perf_counter()-started,
        files={to_repo_relative(p,ctx["root"]):sha256_file(p) for p in paths},completed_at_utc=utc_now_iso()))
    return False


def boundary_gaps(rgb,regions):
    """Absolute contrast between band means; natural object edges can score highly."""
    lab = rgb2lab(np.asarray(rgb,dtype=np.float64))
    inner = lab[regions["inner_boundary_band"].mask].mean(axis=0)
    outer = lab[regions["outer_boundary_band"].mask].mean(axis=0)
    return float(abs(inner[0]-outer[0])),float(deltaE_ciede2000(inner,outer))


def compute_candidate_diagnostics(ctx,row):
    source,mask,regions = candidate_regions(ctx,row)
    restored = uncertainty.load_rgb_array(row["restored_path"],ctx["root"])
    d04._require(restored.shape == source.shape and np.isfinite(restored).all(),"Invalid restored image")
    changed = np.any(restored != source,axis=2)
    outside = ~mask;content_outside = regions["outside_mask_content"].mask;padding = ~regions["content_region"].mask
    base = {k:row[k] for k in ("candidate_id","painting_id","category","case_id","model_id","candidate_role","seed","uncertainty_group_id")}
    base.update(has_clean_reference=False,reference_fidelity_metrics_applicable=False)
    technical = dict(base,width=restored.shape[1],height=restored.shape[0],mask_pixels=int(mask.sum()),
        changed_inside_pixels=int(np.count_nonzero(changed & mask)),changed_outside_pixels=int(np.count_nonzero(changed & outside)),
        changed_outside_content_pixels=int(np.count_nonzero(changed & content_outside)),changed_padding_pixels=int(np.count_nonzero(changed & padding)),
        restored_sha256=sha256_file(ctx["root"] / row["restored_path"]),evidence_role="technical_preservation_not_quality")
    absolute = np.abs(restored-source).mean(axis=2)[mask]
    input_l,input_e = boundary_gaps(source,regions);restored_l,restored_e = boundary_gaps(restored,regions)
    diagnostics = dict(base,masked_edit_rgb_mean=float(absolute.mean()),masked_edit_rgb_p95=float(np.percentile(absolute,95)),
        inside_change_fraction=float(changed[mask].mean()),edit_units="normalized_rgb_0_1",edit_interpretation="magnitude_of_change_to_damaged_input_not_error",
        input_boundary_Lstar_gap=input_l,restored_boundary_Lstar_gap=restored_l,
        input_boundary_delta_e_gap=input_e,restored_boundary_delta_e_gap=restored_e,
        boundary_width_pixels=3,boundary_definition=ctx["policy"]["boundary_definition"],
        boundary_interpretation="contrast_between_band_means_not_a_reference_error_or_acceptance_threshold")
    return dict(technical=technical,diagnostics=diagnostics)


def run_diagnostics(ctx,progress=print):
    _assert_inputs(ctx);technical=[];diagnostics=[];reused=0
    for i,row in enumerate(ctx["candidates"].sort_values(["painting_id","model_id","candidate_role","candidate_id"]).to_dict("records"),1):
        path = _path(ctx,f"work/diagnostics/candidates/{row['candidate_id']}.json")
        reused += int(_checkpoint(ctx,"candidate",row["candidate_id"],[path],lambda:_save(path,compute_candidate_diagnostics(ctx,row))))
        result = _read(path);technical.append(result["technical"]);diagnostics.append(result["diagnostics"])
        if i % 10 == 0:progress(f"Reference-free candidate diagnostics: {i}/70")
    ctx.update(technical=pd.DataFrame(technical),diagnostics=pd.DataFrame(diagnostics),reused_candidate_diagnostics=reused)
    d04._require(ctx["technical"].changed_outside_pixels.eq(0).all(),"A restoration altered pixels outside its repair mask")
    _save(_path(ctx,ctx["config"]["outputs"]["technical_checks"]),ctx["technical"])
    _save(_path(ctx,ctx["config"]["outputs"]["real_damage_diagnostics"]),ctx["diagnostics"])
    _save(_path(ctx,ctx["policy"]["outputs"]["region_manifest"]),ctx["region_manifest"])
    return ctx


def _load_metric(ctx):
    if "metric_model" not in ctx:
        d04._require(inspect_metric_assets() == ctx["assets"],"LPIPS asset location or bytes changed")
        started = perf_counter()
        model,device,metadata = lpips_metrics.load_configured_lpips_model(ctx["lpips_config"])
        ctx.update(metric_model=model,metric_device=device,metric_runtime=dict(metadata,load_seconds=perf_counter()-started))
        _save(_path(ctx,ctx["policy"]["outputs"]["runtime"]),dict(execution_fingerprint=ctx["execution_fingerprint"],
            assets=ctx["assets"],packages=ctx["packages"],runtime=ctx["metric_runtime"],usage="candidate_to_candidate_LPIPS_only"))
    return ctx["metric_model"],ctx["metric_device"]


def _compute_group(ctx,group,metric_path,map_path,model=None,device="cpu"):
    pixel = uncertainty.compute_group_image_uncertainty(group,project_root=ctx["root"],config=ctx["uncertainty_config"])
    pixel = pixel.loc[pixel.region_id.isin(PIXEL_REGIONS)].copy()
    if model is None:model,device = _load_metric(ctx)
    perceptual = uncertainty.compute_group_lpips_uncertainty(group,model=model,device=device,project_root=ctx["root"],
        config=ctx["uncertainty_config"],lpips_config=ctx["lpips_config"])
    combined = pd.concat([pixel,perceptual],ignore_index=True)
    d04._require(len(combined) == 82 and np.isfinite(combined.value).all() and combined.value.ge(-1e-6).all(),"Invalid seed disagreement measurements")
    array,regions = spatial.compute_group_uncertainty_map(group,project_root=ctx["root"],config=ctx["spatial_config"])
    mask = regions["masked_region"].mask;content = regions["content_region"].mask
    d04._require(np.isfinite(array).all() and array[~mask].max() <= ctx["policy"]["outside_float_tolerance"],"Seed variability extends outside the repair mask")
    buffer = BytesIO();np.savez_compressed(buffer,pixel_rgb_std=array,repair_mask=mask,content_mask=content,seeds=np.array([2026,2027,2028,2029],dtype=np.int32))
    readiness._atomic(map_path,buffer.getvalue());_save(metric_path,combined)


def run_uncertainty(ctx,progress=print,model=None,device="cpu"):
    _assert_inputs(ctx);frames=[];maps=[];reused=0
    sd_rows = ctx["candidates"].loc[ctx["candidates"].model_id.eq(MODEL)].copy()
    sd_rows["seed"] = pd.to_numeric(sd_rows.seed).astype(int)
    try:
        for i,(gid,group) in enumerate(sd_rows.groupby("uncertainty_group_id",sort=True),1):
            metric_path = _path(ctx,f"work/diagnostics/groups/{gid}.csv")
            map_path = _path(ctx,ctx["config"]["outputs"]["uncertainty_array_template"].format(group_id=gid))
            reused += int(_checkpoint(ctx,"group",gid,[metric_path,map_path],lambda:_compute_group(ctx,group,metric_path,map_path,model,device)))
            frames.append(pd.read_csv(metric_path,keep_default_na=False,float_precision="round_trip"))
            maps.append(dict(uncertainty_group_id=gid,painting_id=group.iloc[0].painting_id,
                array_path=to_repo_relative(map_path,ctx["root"]),array_sha256=sha256_file(map_path)))
            progress(f"SD seed variability: {i}/10 groups | {group.iloc[0].painting_id}")
    finally:
        loaded = ctx.pop("metric_model",None)
        if loaded is not None:
            del loaded;gc.collect()
            import torch
            if torch.cuda.is_available():torch.cuda.empty_cache()
    metrics = pd.concat(frames,ignore_index=True)
    pairs = metrics.loc[metrics.observation_level.eq("candidate_pair")].copy()
    for column in ("seed_a","seed_b"):
        pairs[column] = pd.to_numeric(pairs[column],errors="raise").astype(int)
    summaries = metrics.loc[metrics.observation_level.eq("group_summary")].copy()
    aggregate=[]
    for _,frame in pairs.groupby(["uncertainty_group_id","metric_name","region_id"],sort=True):
        base = frame.iloc[0].to_dict()
        aggregate.append(uncertainty._metric_record(base,observation_level="group_summary",metric_family=base["metric_family"],
            metric_name=base["metric_name"],region_id=base["region_id"],summary_statistic="pair_mean",value=float(frame.value.mean()),value_unit=base["value_unit"]))
    summaries = pd.concat([summaries,pd.DataFrame(aggregate)],ignore_index=True)
    ctx.update(seed_pairwise=pairs,uncertainty_summary=summaries,maps=pd.DataFrame(maps),reused_uncertainty_groups=reused)
    _save(_path(ctx,ctx["config"]["outputs"]["seed_pairwise"]),pairs)
    _save(_path(ctx,ctx["config"]["outputs"]["uncertainty_summary"]),summaries)
    _save(_path(ctx,ctx["policy"]["outputs"]["map_manifest"]),ctx["maps"])
    return ctx
