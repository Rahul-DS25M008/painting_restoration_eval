"""D04 descriptive physical/synthetic comparison; no inference or metric pooling."""
from __future__ import annotations

from pathlib import Path
from time import perf_counter
from textwrap import fill

import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage
import yaml

from . import real_damage_diagnostics as diagnostics
from . import real_damage_restoration as d04
from . import real_damage_readiness as readiness
from .manifests import sha256_file, utc_now_iso
from .paths import resolve_repo_path, to_repo_relative
from .real_damage_dataset import audit_inventory_inputs
from .validation import ValidationCollector

STAGE="batch_9_physical_synthetic_comparison"
MODULE_VERSION="1.0.0"
_read,_save,_path=diagnostics._read,diagnostics._save,diagnostics._path
MODELS=tuple(d04.PRIMARY_MODELS)
LABELS=dict(zip(MODELS,("Telea","LaMa","HINT","Stable Diffusion")))
DESCRIPTORS=("masked_edit_rgb_mean","masked_edit_rgb_p95","inside_change_fraction",
    "input_boundary_Lstar_gap","restored_boundary_Lstar_gap","input_boundary_delta_e_gap","restored_boundary_delta_e_gap")


def _csv(path):return pd.read_csv(path,keep_default_na=False,float_precision="round_trip")


def _verified_table(root,relative):
    """Accept the two existing producer cardinality fields without editing history."""
    path=resolve_repo_path(relative,root,must_exist=True);owner=path.parent.parent
    manifest_path=owner/"manifests/run_manifest.json";artifacts_path=owner/"manifests/artifacts.csv"
    manifest=_read(manifest_path);artifacts=_csv(artifacts_path)
    d04._require(manifest["run_status"]=="completed" and manifest["completion_gate_passed"] is True,"Incomplete comparison producer")
    owned=[row for row in manifest["outputs"] if row["relative_path"]==relative]
    record=artifacts.loc[artifacts.relative_path.eq(relative)]
    d04._require(len(owned)==len(record)==1,"Ambiguous comparison table ownership")
    digest=sha256_file(path);record=record.iloc[0]
    d04._require(record.checksum==digest and record.validation_status=="passed","Comparison source checksum or validation changed")
    expected=owned[0].get("expected_row_count",owned[0].get("expected_cardinality"))
    d04._require(expected is not None,"Producer does not declare table cardinality")
    frame=pd.read_csv(path,float_precision="round_trip")
    d04._require(len(frame)==int(expected)==int(record.row_count),"Comparison producer row count differs")
    return frame,{to_repo_relative(p,root):sha256_file(p) for p in (path,manifest_path,artifacts_path)}


def _check(ctx,key,description,passed,observed,expected=True):
    checks=ValidationCollector()
    checks.extend(c for c in ctx["validation"].checks if (c.validation_stage,c.check_id)!=(STAGE,key))
    checks.add(validation_stage=STAGE,check_id=key,check_description=description,severity="blocking",
        passed=bool(passed),observed=observed,expected=expected)
    ctx["validation"]=checks


def _same_table(left,right,keys):
    a=left.sort_values(keys).reset_index(drop=True).fillna("")
    b=right.loc[:,a.columns].sort_values(keys).reset_index(drop=True).fillna("")
    for name in ("seed","seed_a","seed_b"):
        if name in a:
            a[name]=pd.to_numeric(a[name].mask(a[name].eq("")),errors="raise")
            b[name]=pd.to_numeric(b[name].mask(b[name].eq("")),errors="raise")
    pd.testing.assert_frame_equal(a,b,check_dtype=False,check_exact=False,atol=1e-12,rtol=1e-10)


def verify_saved_diagnostics(upstream):
    """Read-only audit of Batch 8 checkpoints, published tables and raw maps."""
    diagnostics._assert_inputs(upstream)
    root=upstream["root"];out=upstream["output_root"];policy=upstream["policy"]
    summary_path=out/policy["outputs"]["stage_summary"];summary=_read(summary_path)
    d04._require(summary["execution_fingerprint"]==upstream["execution_fingerprint"]
        and summary["validation_summary"]["check_count"]==summary["validation_summary"]["passed_count"]==371
        and summary["pairwise_rows"]==720 and summary["group_summary_rows"]==220 and summary["map_count"]==10,"Batch 8 is incomplete or changed")
    declared={"diagnostics_summary":summary_path}
    def checkpoint(kind,key,paths):
        path=out/f"work/diagnostics/checkpoints/{kind}/{key}.json";record=_read(path)
        binding=d04._digest(dict(execution=upstream["execution_fingerprint"],kind=kind,key=key,paths=[str(p.relative_to(out)) for p in paths]))
        d04._require(record["status"]=="completed" and record["binding"]==binding
            and set(record["files"])=={to_repo_relative(p,root) for p in paths},"Batch 8 checkpoint binding changed")
        for rel,digest in record["files"].items():
            d04._require(sha256_file(root/rel)==digest,f"Batch 8 output changed: {rel}");declared[rel]=root/rel
        declared[to_repo_relative(path,root)]=path
    tech=[];desc=[]
    for row in upstream["candidates"].itertuples():
        path=out/f"work/diagnostics/candidates/{row.candidate_id}.json"
        checkpoint("candidate",row.candidate_id,[path]);record=_read(path)
        tech.append(record["technical"]);desc.append(record["diagnostics"])
    tables={}
    for key in ("technical_checks","real_damage_diagnostics","seed_pairwise","uncertainty_summary"):
        path=out/upstream["config"]["outputs"][key];tables[key]=_csv(path);declared[key]=path
    _same_table(pd.DataFrame(tech),tables["technical_checks"],["candidate_id"])
    _same_table(pd.DataFrame(desc),tables["real_damage_diagnostics"],["candidate_id"])
    d04._require(tables["technical_checks"].changed_outside_pixels.eq(0).all(),"Outside-mask preservation failed")
    maps_path=out/policy["outputs"]["map_manifest"];maps=_csv(maps_path);declared["maps"]=maps_path
    d04._require(len(maps)==10 and maps.uncertainty_group_id.is_unique,"Invalid map manifest")
    frames=[]
    for gid,group in upstream["candidates"].query("model_id == @d04.SD_MODEL").groupby("uncertainty_group_id"):
        path=out/f"work/diagnostics/groups/{gid}.csv"
        array_path=out/upstream["config"]["outputs"]["uncertainty_array_template"].format(group_id=gid)
        checkpoint("group",gid,[path,array_path]);frame=_csv(path);frames.append(frame)
        entry=maps.loc[maps.uncertainty_group_id.eq(gid)].iloc[0]
        d04._require(entry.array_path==to_repo_relative(array_path,root) and entry.array_sha256==sha256_file(array_path),"Map binding changed")
        with np.load(array_path,allow_pickle=False) as arrays:
            _,mask,regions=diagnostics.candidate_regions(upstream,group.iloc[0]);values=arrays["pixel_rgb_std"]
            d04._require(values.shape==mask.shape and np.array_equal(arrays["repair_mask"],mask)
                and np.array_equal(arrays["content_mask"],regions["content_region"].mask)
                and set(arrays["seeds"].tolist())=={2026,2027,2028,2029}
                and np.isfinite(values).all() and values.min()>=0
                and values[~mask].max()<=policy["outside_float_tolerance"],"Invalid saved variability array")
            for record in frame.loc[frame.observation_level.eq("group_summary")].to_dict("records"):
                v=values[regions[record["region_id"]].mask]
                expected=float(v.mean()) if record["metric_name"]=="pixel_rgb_std_mean" else float(np.percentile(v,95))
                d04._require(np.isclose(record["value"],expected,atol=1e-7),"Saved map and summary differ")
        preview=root/entry.preview_path
        d04._require(sha256_file(preview)==entry.preview_sha256,"Saved map preview changed");declared[entry.preview_path]=preview
    all_rows=pd.concat(frames,ignore_index=True)
    pairs=all_rows.loc[all_rows.observation_level.eq("candidate_pair")].copy()
    for col in ("seed_a","seed_b"):pairs[col]=pd.to_numeric(pairs[col]).astype(int)
    _same_table(pairs,tables["seed_pairwise"],["uncertainty_metric_id"])
    group_summary=all_rows.loc[all_rows.observation_level.eq("group_summary")].copy();aggregate=[]
    for _,frame in pairs.groupby(["uncertainty_group_id","metric_name","region_id"]):
        base=frame.iloc[0].to_dict()
        aggregate.append(diagnostics.uncertainty._metric_record(base,observation_level="group_summary",metric_family=base["metric_family"],
            metric_name=base["metric_name"],region_id=base["region_id"],summary_statistic="pair_mean",value=float(frame.value.mean()),value_unit=base["value_unit"]))
    _same_table(pd.concat([group_summary,pd.DataFrame(aggregate)],ignore_index=True),tables["uncertainty_summary"],["uncertainty_metric_id"])
    checks_path=out/policy["outputs"]["stage_checks"];checks=_csv(checks_path)
    d04._require(len(checks)==371 and checks.passed.all(),"Saved Batch 8 validation failed")
    declared["diagnostics_checks"]=checks_path
    runtime=out/policy["outputs"]["runtime"];audit=_read(runtime)
    d04._require(audit["execution_fingerprint"]==summary["execution_fingerprint"] and audit["assets"]==upstream["assets"],"LPIPS runtime receipt changed")
    declared["diagnostics_runtime"]=runtime
    for key in ("preview_first","preview_second","boundary_figure"):
        path=out/policy["outputs"][key]
        with Image.open(path) as image:image.verify()
        declared[key]=path
    return tables,checks,declared,summary


def select_reference_metrics(sources,selected,policy):
    """Exact candidate/case/model joins; values are copied, never recomputed."""
    records=[]
    for row in selected.itertuples():
        for spec in policy["anchors"]:
            source=sources[spec["source"]]
            match=source.loc[source.candidate_id.eq(row.candidate_id)&source.case_id.eq(row.synthetic_case_id)
                &source.model_id.eq(row.model_id)&source.metric_name.eq(spec["metric_name"])&source.region_id.eq(spec["region_id"])]
            d04._require(len(match)==1 and match.iloc[0].status=="ok","Missing, duplicate or failed synthetic reference metric")
            metric=match.iloc[0]
            d04._require(np.isfinite(float(metric.restored_value)),"Nonfinite synthetic reference metric")
            records.append(dict(pair_id=row.painting_id,synthetic_case_id=row.synthetic_case_id,candidate_id=row.candidate_id,
                model_id=row.model_id,anchor_id=spec["anchor_id"],metric_name=spec["metric_name"],region_id=spec["region_id"],
                value=float(metric.restored_value),units=spec["units"],direction=spec["direction"],
                metric_row_id=metric.metric_row_id,metric_version=metric.metric_version,region_policy_version=metric.region_policy_version,
                source_table=policy["inputs"][spec["source"]],value_role="saved_synthetic_reference_fidelity_not_physical_quality"))
    return pd.DataFrame(records)


def prepare_comparison(project_root,config_path,diagnostics_context=None):
    root=Path(project_root).resolve();path=resolve_repo_path(config_path,root,must_exist=True)
    policy=yaml.safe_load(path.read_text(encoding="utf-8"))
    d04._require(policy["schema_version"]=="real_damage_comparison_config.v1" and policy["stage"]==STAGE
        and policy["policy"]["use_frozen_batch_2_selection"] is True
        and policy["policy"]["disclose_targeted_vs_generic_sd_prompts"] is True
        and all(policy["policy"][k] is False for k in ("regenerate_restorations","recompute_reference_metrics",
            "pool_physical_synthetic_scores","estimate_causal_domain_effect","physical_clean_reference_available")),"Comparison policy changed")
    d04._require(policy["expected"]==dict(pairs=10,models=4,comparison_rows=40,synthetic_diagnostics=40,reference_metric_rows=120,full_panels=10,detail_panels=10),"Comparison counts changed")
    d04._require([(x["anchor_id"],x["metric_name"],x["region_id"]) for x in policy["anchors"]]
        ==[("masked_mae","mae","masked_region"),("crop_ssim","ssim","mask_bbox_crop"),("crop_lpips","lpips","mask_bbox_crop")],"Reference anchor definitions changed")
    upstream=diagnostics_context if diagnostics_context is not None else diagnostics.prepare_diagnostics(root,policy["diagnostics_config"])
    d04._require(upstream["root"]==root,"Diagnostics belong to another checkout")
    tables,checks,declared,summary=verify_saved_diagnostics(upstream)
    output=upstream["output_root"];selection_path=output/upstream["config"]["outputs"]["synthetic_comparators"]
    candidates_path=output/"work/readiness/synthetic_candidate_sources.csv";checkpoint_path=output/"work/readiness/readiness_checkpoint.json"
    frozen=_read(checkpoint_path)
    for file in (selection_path,candidates_path):
        d04._require(sha256_file(file)==frozen["file_checksums"][to_repo_relative(file,root)],"Frozen Batch 2 comparison selection changed")
    selection=_csv(selection_path);selected=_csv(candidates_path)
    d04._require(len(selection)==10 and selection.painting_id.is_unique and selection.synthetic_painting_id.nunique()==10
        and not selection.selection_uses_restoration_scores.any() and selection.prompt_policy_difference.all(),"Invalid frozen comparator population")
    expected={(s.painting_id,s.synthetic_case_id,m) for s in selection.itertuples() for m in MODELS}
    d04._require(len(selected)==40 and selected.candidate_id.is_unique
        and set(selected[["painting_id","synthetic_case_id","model_id"]].itertuples(index=False,name=None))==expected,"Incomplete four-method synthetic handoff")
    sd=selected.loc[selected.model_id.eq(d04.SD_MODEL)]
    d04._require(sd.prompt_variant.eq("p00_generic").all() and pd.to_numeric(sd.seed).eq(2026).all(),"Synthetic SD prompt/seed selection changed")
    declared.update(stage_config=path,stage_helper=root/policy["helper_source"],stage_tests=root/policy["tests"],
        selection=selection_path,synthetic_candidates=candidates_path,readiness_checkpoint=checkpoint_path,
        diagnostics_config=root/policy["diagnostics_config"])
    sources={}
    for key,rel in policy["inputs"].items():
        d04._relative(rel)
        if key=="physical_artworks":sources[key]=_csv(root/rel);declared[key]=root/rel
        else:
            sources[key],bound=_verified_table(root,rel)
            declared.update({r:root/r for r in bound})
    for row in selection.itertuples():
        for prefix in ("synthetic_input_image","synthetic_mask","synthetic_clean_image"):
            rel=getattr(row,prefix+"_path");digest=getattr(row,prefix+"_sha256")
            d04._require(sha256_file(root/rel)==digest,"Comparator source image changed");declared[rel]=root/rel
    rows=[]
    geometry=sources["synthetic_geometry"].set_index("painting_id")
    for row in selected.to_dict("records"):
        pair=selection.loc[selection.painting_id.eq(row["painting_id"])].iloc[0];geo=geometry.loc[pair.synthetic_painting_id]
        d04._require(row["input_sha256"]==pair.synthetic_input_image_sha256 and row["mask_sha256"]==pair.synthetic_mask_sha256
            and sha256_file(root/row["restored_path"])==row["restored_sha256"],"Synthetic candidate image or input binding changed")
        d04._require(geo.processed_path==pair.synthetic_clean_image_path and geo.sha256==pair.synthetic_clean_image_sha256,"Synthetic geometry/reference mismatch")
        declared[row["restored_path"]]=root/row["restored_path"]
        rows.append(dict(row,pair_id=pair.painting_id,painting_id=pair.synthetic_painting_id,case_id=pair.synthetic_case_id,
            category=pair.category,candidate_role="primary",uncertainty_group_id="",input_image_path=pair.synthetic_input_image_path,
            mask_path=pair.synthetic_mask_path,output_width=int(geo.width),output_height=int(geo.height),
            **{k:int(geo[k]) for k in ("content_x_min","content_y_min","content_x_max","content_y_max")}))
    synthetic_plan=pd.DataFrame(rows);anchors=select_reference_metrics(sources,selected,policy)
    inventory,audit=audit_inventory_inputs(root,root/upstream["config"]["inputs"]["inventory"],root/upstream["config"]["inputs"]["inventory_run"],declared)
    collector=ValidationCollector()
    for row in checks.to_dict("records"):collector.add(**row)
    bindings={**upstream["input_checksums"],**{to_repo_relative(p,root):sha256_file(p) for p in declared.values()}}
    ctx=dict(root=root,output_root=output,config=upstream["config"],policy=policy,validation=collector,inventory=inventory,
        input_checksums=bindings,assets=[],packages=upstream["packages"],diagnostics_policy=upstream["policy"],
        physical_candidates=upstream["candidates"].loc[upstream["candidates"].candidate_role.eq("primary")].copy(),
        physical_diagnostics=tables["real_damage_diagnostics"].query("candidate_role == 'primary'").copy(),
        physical_technical=tables["technical_checks"].query("candidate_role == 'primary'").copy(),selection=selection,
        synthetic_plan=synthetic_plan,reference_metrics=anchors,sources=sources,upstream_summary=summary)
    ctx["execution_fingerprint"]=d04._digest(dict(inputs=bindings,packages=ctx["packages"],module_version=MODULE_VERSION))
    _check(ctx,"batch8_handoff","Saved Batch 8 tables agree with all eighty hashed checkpoints and raw maps",True,371,371)
    _check(ctx,"frozen_selection","Ten pre-inference input matches retain forty original primary synthetic candidates",True,len(selected),40)
    _check(ctx,"saved_reference_metrics","Three exact saved reference metrics per synthetic candidate are available",len(anchors)==120,len(anchors),120)
    _check(ctx,"comparison_inventory","Inventory covers comparison code, sources and saved evidence",audit.passed.all(),audit.loc[~audit.passed].to_dict("records"),[])
    ctx["validation"].raise_for_blocking()
    return ctx


def _checkpoint(ctx,kind,key,paths,compute):
    receipt=_path(ctx,f"work/comparison/checkpoints/{kind}/{key}.json")
    binding=d04._digest(dict(execution=ctx["execution_fingerprint"],kind=kind,key=key,paths=[to_repo_relative(p,ctx["root"]) for p in paths]))
    if receipt.exists():
        state=_read(receipt);d04._require(state["binding"]==binding,"Comparison checkpoint inputs changed")
        if state["status"]=="completed":
            d04._require(set(state["files"])=={to_repo_relative(p,ctx["root"]) for p in paths}
                and all(sha256_file(ctx["root"]/rel)==v for rel,v in state["files"].items()),"Comparison output changed")
            return True
        d04._require(state["status"]=="started","Invalid comparison checkpoint state")
    else:
        d04._require(not any(p.exists() for p in paths),"Unverified comparison output cannot be overwritten")
        _save(receipt,dict(binding=binding,status="started"))
    started=perf_counter();compute()
    _save(receipt,dict(binding=binding,status="completed",runtime_seconds=perf_counter()-started,
        files={to_repo_relative(p,ctx["root"]):sha256_file(p) for p in paths},completed_at_utc=utc_now_iso()))
    return False


def _compute_pair(ctx,pair):
    technical=[];descriptors=[];comparison=[]
    for row in ctx["synthetic_plan"].loc[ctx["synthetic_plan"].pair_id.eq(pair.painting_id)].to_dict("records"):
        result=diagnostics.compute_candidate_diagnostics(dict(root=ctx["root"],policy=ctx["diagnostics_policy"]),row)
        for key in ("technical","diagnostics"):
            result[key].update(pair_id=pair.painting_id,domain="controlled_synthetic",has_clean_reference=True,
                reference_fidelity_metrics_applicable=True)
        technical.append(result["technical"]);descriptors.append(result["diagnostics"])
        physical=ctx["physical_candidates"].loc[ctx["physical_candidates"].case_id.eq(pair.real_case_id)&ctx["physical_candidates"].model_id.eq(row["model_id"])]
        d04._require(len(physical)==1,"Physical primary match is not unique");physical=physical.iloc[0]
        desc=ctx["physical_diagnostics"].loc[ctx["physical_diagnostics"].candidate_id.eq(physical.candidate_id)].iloc[0]
        entry=dict(pair_id=pair.painting_id,category=pair.category,model_id=row["model_id"],physical_case_id=pair.real_case_id,
            synthetic_case_id=pair.synthetic_case_id,synthetic_painting_id=pair.synthetic_painting_id,
            physical_candidate_id=physical.candidate_id,synthetic_candidate_id=row["candidate_id"],
            physical_restored_path=physical.restored_path,synthetic_restored_path=row["restored_path"],
            physical_restored_sha256=physical.restored_sha256,synthetic_restored_sha256=row["restored_sha256"],
            physical_clean_reference_available=False,synthetic_clean_reference_available=True,
            physical_reference_metric_status="not_applicable_no_clean_reference",
            comparison_scope="descriptive_different_paintings_and_damage_not_a_causal_domain_test",
            physical_damage_fraction=pair.real_damage_fraction,synthetic_damage_fraction=pair.synthetic_damage_fraction,
            coverage_gap_percentage_points=pair.coverage_gap_percentage_points,
            physical_component_count=pair.real_component_count,synthetic_component_count=pair.synthetic_component_count,
            physical_sd_prompt_policy=pair.real_sd_prompt_policy if row["model_id"]==d04.SD_MODEL else "not_applicable",
            synthetic_sd_prompt_variant=pair.synthetic_sd_prompt_variant if row["model_id"]==d04.SD_MODEL else "not_applicable",
            sd_prompt_policy_difference=row["model_id"]==d04.SD_MODEL,
            descriptor_interpretation="edit_magnitude_and_raw_band_contrast_not_reference_error")
        for name in DESCRIPTORS:entry[f"physical_{name}"]=desc[name];entry[f"synthetic_{name}"]=result["diagnostics"][name]
        scores=ctx["reference_metrics"].loc[ctx["reference_metrics"].candidate_id.eq(row["candidate_id"])]
        for score in scores.itertuples():
            entry[f"synthetic_{score.anchor_id}"]=score.value;entry[f"physical_{score.anchor_id}"]=""
        comparison.append(entry)
    return dict(technical=technical,diagnostics=descriptors,comparison=comparison)


def run_comparison(ctx,progress=print):
    diagnostics._assert_inputs(ctx);results=[];reused=0
    for i,pair in enumerate(ctx["selection"].sort_values("painting_id").itertuples(),1):
        path=_path(ctx,f"work/comparison/pairs/{pair.painting_id}.json")
        reused+=int(_checkpoint(ctx,"metrics",pair.painting_id,[path],lambda:_save(path,_compute_pair(ctx,pair))))
        results.append(_read(path));progress(f"Physical/synthetic comparison: {i}/10 pairs | {pair.painting_id}")
    ctx["synthetic_technical"]=pd.DataFrame([r for result in results for r in result["technical"]])
    ctx["synthetic_diagnostics"]=pd.DataFrame([r for result in results for r in result["diagnostics"]])
    ctx["comparison"]=pd.DataFrame([r for result in results for r in result["comparison"]]);ctx["reused_pairs"]=reused
    d04._require(ctx["synthetic_technical"].changed_outside_pixels.eq(0).all(),"Synthetic outside-mask preservation failed")
    for key in ("synthetic_technical","synthetic_diagnostics","reference_metrics"):_save(_path(ctx,ctx["policy"]["outputs"][key]),ctx[key])
    _save(_path(ctx,ctx["config"]["outputs"]["synthetic_comparison"]),ctx["comparison"])
    return ctx


def detail_bbox(mask,content,margin=32):
    """Input-only display focus; deliberately not an evaluation region."""
    labels,count=ndimage.label(mask,structure=np.ones((3,3),dtype=np.uint8))
    d04._require(count>0,"Empty detail mask")
    sizes=np.bincount(labels.ravel());sizes[0]=0
    yy,xx=np.where(labels==int(np.argmax(sizes)));cy,cx=np.where(content)
    return (max(int(cx.min()),int(xx.min())-margin),max(int(cy.min()),int(yy.min())-margin),
        min(int(cx.max())+1,int(xx.max())+1+margin),min(int(cy.max())+1,int(yy.max())+1+margin))


def _render_pair(ctx,pair,full_path,detail_path):
    import matplotlib.pyplot as plt
    physical=ctx["physical_candidates"].loc[ctx["physical_candidates"].painting_id.eq(pair.painting_id)].set_index("model_id")
    synthetic=ctx["synthetic_plan"].loc[ctx["synthetic_plan"].pair_id.eq(pair.painting_id)].set_index("model_id")
    physical_art=ctx["sources"]["physical_artworks"].set_index("painting_id").loc[pair.painting_id]
    synthetic_art=ctx["sources"]["synthetic_artworks"].set_index("painting_id").loc[pair.synthetic_painting_id]
    inputs=[]
    for frame in (physical,synthetic):
        row=frame.iloc[0];source,mask,regions=diagnostics.candidate_regions(ctx,row)
        images=[source]+[diagnostics.uncertainty.load_rgb_array(frame.loc[m,"restored_path"],ctx["root"]) for m in MODELS]
        inputs.append((images,mask,detail_bbox(mask,regions["content_region"].mask)))
    clean=diagnostics.uncertainty.load_rgb_array(pair.synthetic_clean_image_path,ctx["root"])
    physical_credit=str(physical_art.get("source_credit",physical_art.source)).replace("\n"," ")
    attribution=(f"Physical: {physical_credit}; {physical_art.license}. Synthetic: {synthetic_art.source}; {synthetic_art.license}. "
        "Adaptations: resizing, repair masks and restorations. Full source links and licences are retained in the panel manifest.")
    for detailed,path in ((False,full_path),(True,detail_path)):
        fig,axes=plt.subplots(2,6,figsize=(18,8.2))
        for i,(images,mask,bbox) in enumerate(inputs):
            x0,y0,x1,y1=bbox if detailed else (0,0,mask.shape[1],mask.shape[0])
            for j,array in enumerate(images):
                axes[i,j].imshow(array[y0:y1,x0:x1]);axes[i,j].axis("off")
                if j==0:
                    overlay=np.zeros((*mask.shape,4));overlay[mask]=[0,1,1,.32]
                    axes[i,j].imshow(overlay[y0:y1,x0:x1]);title="Input + selected mask"
                else:title=LABELS[MODELS[j-1]]
                axes[i,j].set_title(title,fontsize=10)
                if i==1 and j>0:
                    c=ctx["comparison"].loc[ctx["comparison"].pair_id.eq(pair.painting_id)&ctx["comparison"].model_id.eq(MODELS[j-1])].iloc[0]
                    axes[i,j].text(.5,-.06,f"Masked MAE {c.synthetic_masked_mae:.3f}\nCrop SSIM {c.synthetic_crop_ssim:.4f} | LPIPS {c.synthetic_crop_lpips:.4f}",
                        transform=axes[i,j].transAxes,ha="center",va="top",fontsize=8)
            if i==0:
                axes[i,5].text(.5,.5,"No clean reference\nPhysical fidelity\ncannot be scored",ha="center",va="center",fontsize=12)
            else:axes[i,5].imshow(clean[y0:y1,x0:x1]);axes[i,5].set_title("Known digital reference",fontsize=10)
            axes[i,5].axis("off")
        mode="Detail: independently selected largest mask component" if detailed else "Full painting context"
        fig.suptitle(f"D04 | {pair.painting_id} ↔ {pair.synthetic_painting_id} | {mode}",fontsize=15,y=.985)
        fig.text(.5,.935,fill(f"Physical: {physical_art.title} | selected coverage {100*pair.real_damage_fraction:.2f}%",120),ha="center",fontsize=10)
        fig.text(.5,.515,fill(f"Synthetic: {pair.synthetic_title} | {pair.synthetic_mask_type} | coverage {100*pair.synthetic_damage_fraction:.2f}%",120),ha="center",fontsize=10)
        fig.subplots_adjust(top=.88,bottom=.19,left=.025,right=.985,hspace=.45,wspace=.12)
        fig.text(.5,.095,"Different artworks and approximate input geometry; descriptive comparison only. SD: physical targeted prompt, synthetic generic prompt.\n"
            "Scores describe saved full evaluation regions, including in detail views. Detail crops are display aids, not corresponding subjects or new metric regions.",ha="center",fontsize=9)
        fig.text(.5,.035,fill(attribution,190),ha="center",fontsize=8)
        path.parent.mkdir(parents=True,exist_ok=True);fig.savefig(path,dpi=140);plt.close(fig)


def render_outputs(ctx,progress=print):
    import matplotlib.pyplot as plt
    diagnostics._assert_inputs(ctx);records=[];reused=0
    physical_art=ctx["sources"]["physical_artworks"].set_index("painting_id")
    synthetic_art=ctx["sources"]["synthetic_artworks"].set_index("painting_id")
    for i,pair in enumerate(ctx["selection"].sort_values("painting_id").itertuples(),1):
        full=_path(ctx,ctx["config"]["outputs"]["comparator_panel_template"].format(painting_id=pair.painting_id))
        detail=_path(ctx,ctx["policy"]["outputs"]["detail_template"].format(painting_id=pair.painting_id))
        reused+=int(_checkpoint(ctx,"panels",pair.painting_id,[full,detail],lambda:_render_pair(ctx,pair,full,detail)))
        a=physical_art.loc[pair.painting_id];b=synthetic_art.loc[pair.synthetic_painting_id]
        record=dict(pair_id=pair.painting_id,synthetic_painting_id=pair.synthetic_painting_id,
            full_panel_path=to_repo_relative(full,ctx["root"]),full_panel_sha256=sha256_file(full),
            detail_panel_path=to_repo_relative(detail,ctx["root"]),detail_panel_sha256=sha256_file(detail),
            physical_title=a.title,physical_source_url=a.source_url,physical_credit=a.source_credit,
            physical_license=a.license,physical_license_url=a.license_url,
            synthetic_title=b.title,synthetic_source_url=b.source_url,synthetic_license=b.license,
            detail_crop_policy=ctx["policy"]["policy"]["detail_crop"],detail_crop_is_metric_region=False)
        for domain,frame in (("physical",ctx["physical_candidates"].loc[ctx["physical_candidates"].painting_id.eq(pair.painting_id)]),
                             ("synthetic",ctx["synthetic_plan"].loc[ctx["synthetic_plan"].pair_id.eq(pair.painting_id)])):
            _,mask,regions=diagnostics.candidate_regions(ctx,frame.iloc[0]);bbox=detail_bbox(mask,regions["content_region"].mask)
            record.update({f"{domain}_detail_{key}":value for key,value in zip(("x0","y0","x1","y1"),bbox)})
        records.append(record);progress(f"Comparison panels: {i}/10 | {pair.painting_id}")
    selection=ctx["selection"].sort_values("painting_id");y=np.arange(10)
    fig,axes=plt.subplots(1,2,figsize=(12,7))
    for label,coverage,components,offset,color in (("Physical","real_damage_fraction","real_component_count",-.13,"#9b4a26"),
                                                 ("Synthetic","synthetic_damage_fraction","synthetic_component_count",.13,"#176c6b")):
        axes[0].scatter(100*selection[coverage],y+offset,label=label,color=color)
        axes[1].scatter(selection[components],y+offset,label=label,color=color)
    for ax in axes:
        ax.set_yticks(y,[f"{r.painting_id} / {r.synthetic_painting_id}" for r in selection.itertuples()]);ax.invert_yaxis();ax.grid(alpha=.2);ax.legend()
    axes[0].set_xlabel("Selected mask coverage (% of content)");axes[1].set_xlabel("Connected mask components (log scale)");axes[1].set_xscale("log")
    fig.suptitle("D04 | Approximate input matches retain geometric differences",fontsize=14)
    fig.text(.5,.02,"Same broad category and input-based selection do not make damage origins, fragmentation or depicted subjects equivalent.",ha="center",fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.96));path=_path(ctx,ctx["policy"]["outputs"]["matching_figure"])
    fig.savefig(path,dpi=140);plt.close(fig)
    ctx.update(panels=pd.DataFrame(records),matching_figure=path,reused_panel_pairs=reused)
    _save(_path(ctx,ctx["policy"]["outputs"]["panel_manifest"]),ctx["panels"])
    return ctx["panels"]


def validate_results(ctx):
    diagnostics._assert_inputs(ctx)
    table=ctx["comparison"];plan=ctx["synthetic_plan"];metrics=ctx["reference_metrics"]
    expected={(r.painting_id,m) for r in ctx["selection"].itertuples() for m in MODELS}
    _check(ctx,"comparison_population","Ten pairs retain exactly four primary method comparisons each",len(table)==40
        and not table.duplicated(["pair_id","model_id"]).any() and set(table[["pair_id","model_id"]].itertuples(index=False,name=None))==expected,len(table),40)
    _check(ctx,"reference_separation","Physical reference metrics are explicitly unavailable, never zero or imputed",
        not table.physical_clean_reference_available.any() and table.synthetic_clean_reference_available.all()
        and table.physical_reference_metric_status.eq("not_applicable_no_clean_reference").all()
        and table[["physical_masked_mae","physical_crop_ssim","physical_crop_lpips"]].eq("").all().all(),"physical fidelity unavailable")
    _check(ctx,"prompt_difference","Only SD rows identify the targeted versus generic conditioning difference",
        table.sd_prompt_policy_difference.eq(table.model_id.eq(d04.SD_MODEL)).all()
        and table.loc[table.model_id.eq(d04.SD_MODEL),"synthetic_sd_prompt_variant"].eq("p00_generic").all(),int(table.sd_prompt_policy_difference.sum()),10)
    _check(ctx,"synthetic_preservation","Forty synthetic candidates retain exact outside-mask preservation",len(ctx["synthetic_technical"])==40
        and ctx["synthetic_technical"].changed_outside_pixels.eq(0).all(),len(ctx["synthetic_technical"]),40)
    _check(ctx,"descriptor_values","Both sets have finite edit and raw boundary descriptors",len(ctx["synthetic_diagnostics"])==40
        and np.isfinite(table[[f"{domain}_{key}" for domain in ("physical","synthetic") for key in DESCRIPTORS]].to_numpy(float)).all(),len(ctx["synthetic_diagnostics"]),40)
    _check(ctx,"reference_rows","Three saved synthetic anchors are retained for every candidate",len(metrics)==120
        and not metrics.duplicated(["candidate_id","anchor_id"]).any() and set(metrics.candidate_id)==set(plan.candidate_id),len(metrics),120)
    _same_table(table,_csv(_path(ctx,ctx["config"]["outputs"]["synthetic_comparison"])),["pair_id","model_id"])
    for key in ("synthetic_technical","synthetic_diagnostics","reference_metrics"):
        keys=["candidate_id","anchor_id"] if key=="reference_metrics" else ["candidate_id"]
        _same_table(ctx[key],_csv(_path(ctx,ctx["policy"]["outputs"][key])),keys)
    _check(ctx,"saved_tables","Published comparison tables equal the validated in-memory evidence",True,True)
    for pair in ctx["selection"].itertuples():
        frame=table.loc[table.pair_id.eq(pair.painting_id)];good=True
        for row in frame.itertuples():
            for anchor in ("masked_mae","crop_ssim","crop_lpips"):
                expected_value=metrics.loc[metrics.candidate_id.eq(row.synthetic_candidate_id)&metrics.anchor_id.eq(anchor),"value"].iloc[0]
                good=good and getattr(row,f"synthetic_{anchor}")==expected_value
        _check(ctx,f"saved_scores:{pair.painting_id}","Displayed synthetic scores equal the original saved measurements",good,len(frame),4)
    # Every reused/generated per-pair payload remains tied to the stage fingerprint.
    for pair in ctx["selection"].itertuples():
        payload=_path(ctx,f"work/comparison/pairs/{pair.painting_id}.json")
        _checkpoint(ctx,"metrics",pair.painting_id,[payload],lambda:(_ for _ in ()).throw(ValueError("Missing completed comparison checkpoint")))
        p=ctx["panels"].loc[ctx["panels"].pair_id.eq(pair.painting_id)].iloc[0]
        paths=[ctx["root"]/p.full_panel_path,ctx["root"]/p.detail_panel_path]
        _checkpoint(ctx,"panels",pair.painting_id,paths,lambda:(_ for _ in ()).throw(ValueError("Missing completed panel checkpoint")))
        for path,digest in zip(paths,(p.full_panel_sha256,p.detail_panel_sha256)):
            d04._require(sha256_file(path)==digest,"Panel manifest checksum mismatch")
            with Image.open(path) as image:image.verify()
    _check(ctx,"panels","Ten full panels and ten input-defined detail panels retain verified hashes",len(ctx["panels"])==10,len(ctx["panels"]),10)
    checks=ctx["validation"].to_dataframe()
    _save(_path(ctx,ctx["policy"]["outputs"]["stage_checks"]),checks)
    _save(_path(ctx,ctx["config"]["outputs"]["validation"]),checks)
    artifact_paths=[_path(ctx,ctx["config"]["outputs"]["synthetic_comparison"])]
    artifact_paths += [_path(ctx,ctx["policy"]["outputs"][k]) for k in ("synthetic_diagnostics","synthetic_technical","reference_metrics","panel_manifest","matching_figure","stage_checks")]
    artifact_paths += [ctx["root"]/rel for column in ("full_panel_path","detail_panel_path") for rel in ctx["panels"][column]]
    artifact_paths += sorted((ctx["output_root"]/"work/comparison/pairs").glob("*.json"))
    artifact_paths += sorted((ctx["output_root"]/"work/comparison/checkpoints").glob("*/*.json"))
    artifacts=pd.DataFrame([dict(relative_path=to_repo_relative(p,ctx["root"]),sha256=sha256_file(p),size_bytes=p.stat().st_size) for p in artifact_paths])
    _save(_path(ctx,ctx["policy"]["outputs"]["artifacts"]),artifacts)
    ctx["summary"]=dict(stage=STAGE,execution_fingerprint=ctx["execution_fingerprint"],comparison_pairs=10,
        comparison_rows=len(table),physical_primary_candidates=40,synthetic_primary_candidates=40,
        saved_reference_metric_rows=len(metrics),full_panels=10,detail_panels=10,
        reused_metric_pairs=ctx["reused_pairs"],reused_panel_pairs=ctx["reused_panel_pairs"],
        validation_summary=ctx["validation"].summary(),artifact_count=len(artifacts),
        artifacts_sha256=sha256_file(_path(ctx,ctx["policy"]["outputs"]["artifacts"])),
        notebook_completion_gate_passed=False,completed_at_utc=utc_now_iso())
    _save(_path(ctx,ctx["policy"]["outputs"]["stage_summary"]),ctx["summary"])
    ctx["validation"].raise_for_blocking()
    return ctx["summary"]
