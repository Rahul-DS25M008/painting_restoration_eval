"""Museum presentation for the candidate-level Case Explorer room."""
import html
import json
from pathlib import Path
from urllib.parse import urlencode, quote

import streamlit as st
import streamlit.components.v1 as components

from .case_explorer import (ROOT, LAYERS, payload, asset_uri, retrieval_rows,
                            saved_panels, select_record, reports_for, candidate_metrics, random_candidate, counterfactual_choices)
from .model_gallery import image_uri
from .trustworthiness_view import nav_images, rect, frame_crop


def icon(kind):
    """Small code-native catalogue symbols, never scientific map imagery."""
    drawings = {
        "difference": '<defs><linearGradient id="d"><stop stop-color="#a351e9"/><stop offset=".5" stop-color="#ff658b"/><stop offset="1" stop-color="#f2c659"/></linearGradient></defs><path d="M3 17l4-9 5 5 4-9 5 11M5 20l4-6 7 2 4-8" stroke="url(#d)" stroke-width="3"/>',
        "seam": '<rect x="5" y="4" width="14" height="16" stroke-dasharray="3 2"/>',
        "colour": '<circle cx="9" cy="10" r="5" fill="#b66646" fill-opacity=".7"/><circle cx="15" cy="10" r="5" fill="#d4a755" fill-opacity=".7"/><circle cx="12" cy="15" r="5" fill="#577a83" fill-opacity=".8"/>',
        "texture": '<path d="M3 6q3-4 6 0t6 0t6 0M3 12q3-4 6 0t6 0t6 0M3 18q3-4 6 0t6 0t6 0"/>',
        "semantic": '<g stroke="#304b58"><path d="M5 5l14 14M5 19L19 5"/><circle cx="5" cy="5" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><circle cx="12" cy="12" r="2"/></g>',
        "uncertainty": '<path d="M12 3L2 21h20z" fill="#32474b" stroke="#ba9652"/><path d="M12 8v6m0 3v1" stroke="#efd784" stroke-width="2"/>',
        "shield": '<path d="M12 2l8 3v7q-1 6-8 10q-7-4-8-10V5z" fill="#ab8746"/><path d="M8 12l3 3 5-7" stroke="#f2deb0" stroke-width="2"/>',
        "info": '<circle cx="12" cy="12" r="10" fill="#96753c"/><path d="M12 10v8m0-12v1" stroke="#f7e1ac" stroke-width="2"/>',
        "database": '<ellipse cx="12" cy="5" rx="7" ry="3"/><path d="M5 5v13c0 4 14 4 14 0V5M5 11c0 4 14 4 14 0"/>',
        "person": '<circle cx="12" cy="7" r="4" fill="#657072"/><path d="M4 21v-3a8 8 0 0116 0v3z" fill="#657072"/>',
        "record": '<path d="M6 3h9l4 4v14H6zM14 3v5h5M9 12h7m-7 4h7"/>',
        "review": '<circle cx="10" cy="10" r="6"/><path d="M15 15l6 6"/>',
        "book": '<path d="M3 4q5-2 9 1q4-3 9-1v15q-5-2-9 1q-4-3-9-1zM12 5v15"/>',
        "retrieval": '<rect x="2" y="6" width="8" height="13"/><rect x="14" y="4" width="8" height="13"/><path d="M10 11h4"/>',
    }
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#775428" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{drawings.get(kind, drawings["record"])}</svg>'
    return f'<img class="ce-icon" alt="" aria-hidden="true" src="data:image/svg+xml,{quote(svg)}">'


def thumbnail_style(column, lane):
    """CSS window into query-03's original panel; no new evidence bitmap."""
    # Normalized to the inspected 1888 x 1335 view of the 3209 x 2270 source.
    x, y, w, h = (22 + column * 381.5, 626, 318, 218) if lane == "lower_risk" else (60 + column * 381.5, 989, 249, 333)
    target_w, target_h = 36, 35
    scale = max(target_w / w, target_h / h)
    sw, sh = 1888 * scale, 1335 * scale
    left = (target_w-w*scale)/2-x*scale
    top = (target_h-h*scale)/2-y*scale
    return f'background-size:{sw/target_w*100:.4f}% {sh/target_h*100:.4f}%;background-position:{left/(target_w-sw)*100:.4f}% {top/(target_h-sh)*100:.4f}%'


def esc(value):
    return html.escape(str(value), quote=True)


def number(value):
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "Unavailable"


def resource_header(painting, selected, title, description):
    """Consistent archive presentation without altering a saved report's bytes."""
    state={"room":"case_explorer","ce_painting":painting,"ce_candidate":selected["candidate_id"],
           "ce_layer":str(st.query_params.get("ce_layer","difference"))}
    if st.query_params.get("ce_map"):
        state["ce_map"]=str(st.query_params["ce_map"])
    back="?"+urlencode(state)
    st.html(f'''<style>.ce-resource{{margin:20px auto 22px;padding:26px 30px;background:linear-gradient(120deg,#103b35,#092625);border:1px solid #8c7546;border-radius:5px;color:#eadcba;font:16px/1.5 Georgia,serif}}.ce-resource a{{color:#d2b87e!important;text-decoration:none!important;font-size:14px}}.ce-resource h1{{font:normal 29px/1.2 Georgia,serif;color:#f1e4c9;margin:18px 0 10px}}.ce-resource p{{margin:0 0 9px;color:#d7ddcc;max-width:80ch}}.ce-resource small{{font:11px/1.4 system-ui,sans-serif;letter-spacing:.07em;color:#bcaa82}}</style><header class="ce-resource"><a href="{esc(back)}" target="_self">← Return to this candidate</a><h1>{esc(title)}</h1><p>{esc(description)}</p><small>{esc(painting)} · {esc(selected["model_id"])} · ORIGINAL SAVED SOURCE</small></header>''')


def reference_window(bounds):
    """A lossless CSS window into the approved 1672 × 941 lettering artwork."""
    x, y, w, h = bounds
    return f'background-size:{1672/w*100:.6f}% {941/h*100:.6f}%;background-position:{x/(1672-w)*100:.6f}% {y/(941-h)*100:.6f}%'


def room_markup(data, navigation, shell, lettering=None, neutral_layer=None, title_art=None):
    c, p, case = data["candidate"], data["painting"], data["case"]
    parts = [f'<main class="ce-stage" aria-label="Case Explorer evidence room" style="background-image:url({shell})">', nav_images(navigation)]
    if lettering:
        parts.append(f'<img class="ce-lettering-source" src="{esc(lettering)}" alt="" hidden>')
    if title_art:
        parts.append(f'<img class="ce-title-source" src="{esc(title_art)}" alt="" hidden>')
    if neutral_layer:
        # Only the repaired top-row window is used; the rest of the shell stays original.
        patch=(1368,207,234,76)
        parts.append(f'<div class="ce-neutral-layer" aria-hidden="true" style="{rect(*patch)};{reference_window(patch)};background-image:url({neutral_layer})"></div>')
    def text(bounds, content, cls="ce-copy"):
        parts.append(f'<div class="{cls}" style="{rect(*bounds)}">{content}</div>')
    def artwork(bounds, content, cls):
        parts.append(f'<div class="{cls} ce-reference-window ce-static-art" style="{rect(*bounds)};{reference_window(bounds)}"><div>{content}</div></div>')
    def button(action, bounds, content, label=None, cls="ce-button", disabled=False):
        parts.append(f'<button type="button" class="{cls}" data-action="{esc(action)}" style="{rect(*bounds)}" aria-label="{esc(label or action)}" title="{esc(label or action)}" {"disabled" if disabled else ""}>{content}</button>')
    def art_button(action, bounds, label, cls, disabled=False):
        content=f'<span class="ce-reference-window" style="{reference_window(bounds)}">{esc(label)}</span>'
        button(action,bounds,content,label,cls+" ce-art-button",disabled)
    condition = case["case_id"].split(p["painting_id"]+"__")[-1].replace("__"," · ").replace("_"," ")
    model = data["labels"].get(c["model_id"],c["model_id"])
    ledger_model = "SDXL" if "sdxl" in c["model_id"].lower() else "SD" if "stable" in model.lower() or "sd15" in c["model_id"].lower() else model
    artwork((612,115,450,64), '<h1>Case Explorer</h1><h2>What evidence supports this restoration conclusion?</h2><p>Follow one restoration from controlled damage to measurements, warnings and source records.</p>', "ce-title")
    button("record",(697,195,278,27),f'{esc(p["painting_id"])} · {esc(condition)} · {esc(model)}',"Inspect exact candidate identity","ce-record-plaque")
    text((77,144,207,69),'<h3>Find a case</h3><p>Explore the collection by<br>navigating the<br>experimental factors.</p>',"ce-heading ce-catalogue-heading")
    categories = {"landscape_natural":"Landscape", "portrait_figure":"Portrait / figure", "architecture_structured":"Architecture", "high_texture_brushwork":"Texture / brushwork", "abstraction_surrealism":"Abstraction"}
    labels = (("Category",categories.get(p["category"],p["category"])),("Painting",p["painting_id"]),
              ("Experiment", {"canonical_missing_region":"Core test","synthetic_degradation":"Degradation","mask_robustness":"Mask variants","damage_size_sensitivity":"Damage size"}.get(c["experiment_id"],c["experiment_id"])),
              ("Damage",condition),("Model", model),
              ("Candidate", "Seed "+str(c["seed"]) if c.get("seed") is not None else "#1 (selected)"))
    for index,(label,value) in enumerate(labels):
        y = (225,267,309,350,390,430)[index]
        label_style = reference_window((87,y,82,45))
        button("catalogue:"+label.lower(),(87,y,201,45),f'<b class="ce-reference-window" style="{label_style}">{label}</b><span>{esc(value)}</span><i aria-hidden="true">▾</i>',"Select "+label.lower(),"ce-selector")
    text((78,490,202,38),'300 paintings · 2,620 cases<br>13,879 indexed candidates',"ce-scope")
    for i,(action,key,label) in enumerate((("limits","book","Review guidance"),("availability","info","Evidence available"),("uncertainty","uncertainty","Uncertainty"),("retrieval","review","Retrieval"))):
        button(action,(80,532+i*28,199,25),icon(key)+f'<span>{label}</span>',label,"ce-guide")
    for key,label,box,caption in (
        ("clean","Clean reference",(380,280,155,172),(382,245,152,29)),
        ("damaged","Damaged input",(567,286,159,164),(568,251,157,29)),
        ("mask","Mask",(758,287,154,162),(756,253,157,29)),
        ("restored",model+" restoration",(943,285,158,165),(944,250,158,29)),
        ("evidence",LAYERS[data["layer"]][0],(1131,281,157,171),(1134,245,154,29)),
    ):
        item = data["images"][key]
        spatial_map = key == "evidence" and data.get("map_record") and str(data["map_record"].get("width"))=="768" and str(data["map_record"].get("height"))=="768"
        crop = frame_crop(data["content_bbox"],box[2],box[3]) if key != "evidence" or spatial_map else ""
        content = f'<img style="{crop}" src="{esc(item["uri"])}" alt="{esc(label)} for {esc(c["candidate_id"])}">' if item["uri"] else '<span class="ce-unavailable">No saved view<br><small>Open for details</small></span>'
        button("compare:"+key,box,content,"Inspect "+label.lower()+" · full image and comparison","ce-print")
        caption_label=ledger_model+" Restoration" if key=="restored" and ledger_model in ("SD","SDXL") else label
        button("compare:"+key,caption,esc(caption_label),"Inspect "+label.lower(),"ce-caption")
    artwork((516,486,630,32),'Painting · Experiment · Damage · Model · Candidate · Surprise me · Record ID',"ce-toolbar-art")
    for action,x,w,label in (("catalogue:painting",528,64,"Painting"),("catalogue:experiment",599,87,"Experiment"),("catalogue:damage",697,72,"Damage"),("catalogue:model",781,62,"Model"),("catalogue:candidate",852,80,"Candidate"),("surprise",942,88,"Surprise me"),("record",1050,85,"Record ID ▾")):
        button(action,(x,489,w,25),label,label,"ce-toolbar-label ce-art-hit")
    artwork((1400,141,184,78),'<h3>Evidence layers</h3><p>Pull a layer over the restoration<br>to explore different evidence.</p>',"ce-heading ce-evidence-heading")
    for i,item in enumerate(data["layers"]):
        selected = " is-active" if item["key"]==data["layer"] else ""
        short_label = {"seam":"Boundary", "semantic":"Semantic"}.get(item["key"],item["label"])
        content = icon(item["key"])+f'<span>{esc(short_label)}</span><small>{"Selected" if selected else ("Not applicable" if "deterministic" in item["reason"] else "Unavailable" if not item["available"] else "")}</small>'
        button("layer:"+item["key"],(1394,236+41*i,185,36),content,item["label"]+" · "+item["reason"],"ce-layer ce-layer-row-"+str(i)+selected, not item["available"])
    text((1406,493,180,35),'Unavailable stays unavailable.<br>Not applicable is not zero.',"ce-layer-note")
    missing = c.get("insufficient_flag_ids", [])
    explanation = ("One required colour indicator is missing. Missing is not a pass." if missing == ["colour_inconsistency"] else
                   (f"{len(missing)} required indicators are missing. Missing is not a pass." if missing else "Recorded status, not expert ground truth."))
    deterministic = "deterministic" in data["layers"][-1]["reason"]
    text((347,560,194,163),f'<h3>Selected candidate</h3><p class="ce-status-line">{icon("review")}<span>{esc(c["recommendation_category"].replace("_"," ").capitalize())}</span></p><p class="ce-status-line">{icon("shield")}<span>{"Required evidence incomplete" if missing else "Required evidence recorded"}</span></p><p class="ce-status-line">{icon("uncertainty")}<span>{"Manual review required" if c["manual_review_required"] else "No manual-review flag"}</span></p><p class="ce-status-line">{icon("info")}<span>{"Uncertainty: N/A (deterministic)" if deterministic else "Uncertainty: "+("saved group" if data["layers"][-1]["available"] else "unavailable")}</span></p><div class="ce-why"><strong>{"Why review?" if c["manual_review_required"] else "Recorded status"}</strong><p>{esc(explanation)}</p></div>',"ce-status")
    button("trust",(350,733,187,24),"Open Trustworthiness trace →","Open exact Trustworthiness candidate","ce-trust-link")
    text((649,594,465,23),'Metric snapshot <span>(saved values only)</span>',"ce-ledger-title")
    ledger = []
    for item, family, region, measure in zip(data["metrics"],("Colour","Perceptual","Structure"),("Masked","Mask box","Mask box"),("ΔE 2000","LPIPS","SSIM")):
        row = item["record"]
        valid = row and row["status"]=="ok"
        ledger.append(f'<div><span>{family}</span><small>{region}</small><span>{measure}</span><small title="{esc(model)}">{esc(ledger_model)}</small><strong>{number(row["damaged_value"]) if valid else "—"}</strong><strong>{number(row["restored_value"]) if valid else "—"}</strong><strong>{number(row["improvement_value"]) if valid else "—"}</strong><small>{"↑ higher better" if item["direction"].startswith("Higher") else "↓ lower better"}</small></div>')
    header='<div class="ce-ledger-columns"><span>Metric family</span><span>Region</span><span>Measure</span><span>Model</span><span>Damaged</span><span>Restored</span><span>Improvement</span><span>Units / direction</span></div>'
    button("metrics",(646,620,477,64),header+"".join(ledger),"Inspect exact saved metric rows","ce-ledger")
    text((648,685,475,16),'Saved values only · no combined score. <span>Select the ledger for exact rows.</span>',"ce-ledger-note")
    artwork((1220,554,187,25),"Reports and provenance","ce-reports-heading")
    for i,(action,label) in enumerate((("report:painting","Painting report"),("report:case","Case report"),("sources","Source notebooks"),("metrics","Exact saved rows"))):
        unavailable = action=="report:case" and not data["reports"]["case"]
        art_button(action,(1243,(586,618,649,681)[i],146,28),"Not selected for a detailed case report" if unavailable else label,"ce-drawer",unavailable)
    if data["review_code"]:
        button("portrait",(1222,719,177,26),icon("person")+"Focused portrait review", "Open exact D02 reviewed candidate","ce-drawer")
    else:
        art_button("portrait",(1219,716,186,31),"No completed D02 review for this candidate","ce-drawer",True)
    button("retrieval:2",(620,772,493,18),'Stored example retrieval <span>· p018 dirt / dust · HINT · not this case</span>',"Open stored p018 retrieval example","ce-retrieval-heading")
    text((611,790,244,14),'Lower-risk neighbours',"ce-lane-label")
    text((869,790,242,14),'Flagged neighbours',"ce-lane-label ce-lane-flagged")
    sheet=data.get("retrieval_sheet_uri")
    if sheet:
        parts.append(f'<div class="ce-retrieval-sheet" style="{rect(0,0,1672,941)}"><img class="ce-sheet-source" src="{esc(sheet)}" alt="" hidden>')
        for lane in ("lower_risk","flagged"):
            for i in range(5):
                x=614+i*51+(255 if lane=="flagged" else 0)
                parts.append(f'<button type="button" class="ce-neighbour-mini" data-action="neighbour:{lane}:{i+1}" style="{rect(x,805,36,35)};{thumbnail_style(i,lane)}" aria-label="Inspect stored {lane.replace("_"," ")} neighbour {i+1}" title="Stored p018 dirt/dust example · not the active candidate"></button>')
        parts.append('</div>')
    else:
        button("retrieval",(613,805,495,35),"Open the 10 stored retrieval queries →","Open stored retrieval examples","ce-query-tile")
    artwork((1180,784,322,80),'What could change? Damage size · Mask placement · Model · Metric choice · Seed · Prompt · Evidence removed. Selected examples only – not causal proof.',"ce-knob-art")
    for i,(family,label) in enumerate((("damage_size","Damage size"),("mask_placement","Mask placement"),("cross_model","Model"),("metric_subset","Metric choice"),("diffusion_seed","Seed"),("prompt_policy","Prompt"),("evidence_family_removal","Evidence removed"))):
        button("counterfactual:"+family,(1182+i*46,808,38,43),f'<span>{label}</span>',"Inspect stored "+label.lower()+" comparison","ce-knob ce-art-hit")
    artwork((1510,566,76,126),'SAME<br>EVIDENCE.<br>DIFFERENT<br>QUESTIONS.<br>A CLEARER<br>PAST.',"ce-motto")
    for label,bounds in (("CASES",(107,712,69,27)),("METRICS",(109,739,76,26)),("FLAGS",(110,766,65,28)),("RECORDS",(110,791,81,26))):
        lettering_window=f'<span class="ce-reference-window" style="{reference_window(bounds)}">{label}</span>'
        button("record" if label=="RECORDS" else "metrics" if label=="METRICS" else "trust" if label=="FLAGS" else "catalogue",bounds,lettering_window,"Open "+label.lower(),"ce-book")
    parts.append('</main><nav class="ce-access-bar" aria-label="Case Explorer quick controls"><button data-action="catalogue">Find a case</button><button data-action="compare">Compare images</button><button data-action="metrics">Saved measurements</button><button data-action="availability">Evidence layers</button><button data-action="retrieval">Related cases</button><button data-action="record">Record & reports</button></nav><dialog class="ce-dialog" aria-labelledby="ce-dialog-title"><header><div><small>CONSERVATION CASE FILE</small><h2 id="ce-dialog-title"></h2><p class="ce-dialog-context"></p></div><button data-close aria-label="Close evidence details">×</button></header><div class="ce-dialog-body"></div></dialog><div class="ce-sr" role="status" aria-live="polite"></div>')
    return "".join(parts)


def render_case_explorer(package, navigation):
    painting = str(st.query_params.get("ce_painting", "p018"))
    candidate = st.query_params.get("ce_candidate")
    if st.query_params.get("ce_random") == "1":
        st.query_params["ce_candidate"]=random_candidate(package,painting)
        del st.query_params["ce_random"]
        st.rerun()
    export_kind=st.query_params.get("ce_export")
    if export_kind:
        _,selected,_=select_record(package,painting,candidate)
        resource_header(painting,selected,"Download saved evidence","Original recorded values, with their full precision and source identities. No metrics are recalculated for this export.")
        if export_kind not in ("metrics","retrieval"):
            st.error("Unknown export. No other records have been substituted.")
            return
        rows=([item["record"] for item in candidate_metrics(painting,selected) if item["record"]]
              if export_kind=="metrics" else retrieval_rows())
        filename=(selected["candidate_id"]+"-metrics.json" if export_kind=="metrics" else "N29-recorded-neighbours.json")
        serialized=json.dumps(rows,ensure_ascii=False,allow_nan=False,indent=2)
        st.caption(f"{len(rows)} saved rows · "+("this exact candidate" if export_kind=="metrics" else "all 10 stored retrieval queries, not only the active candidate"))
        st.download_button("Save JSON file",serialized.encode("utf-8"),file_name=filename,mime="application/json")
        with st.expander("Preview the exact exported records"):
            st.code(serialized,language="json")
        return
    notebook_id = st.query_params.get("ce_notebook")
    if notebook_id:
        _, selected, _ = select_record(package, painting, candidate)
        resource_header(painting,selected,"Source notebook","Inspect or download the recorded source. This view never executes a notebook or recomputes evidence.")
        if notebook_id not in selected["source_notebook_ids"]:
            st.error("This notebook is not a recorded source for the selected candidate.")
            return
        paths = list((ROOT / "notebooks").glob(str(notebook_id) + "_*.ipynb"))
        if len(paths) != 1:
            st.error("The exact source notebook is unavailable locally.")
            return
        st.subheader(paths[0].stem.replace("_", " "))
        st.download_button("Download source notebook", paths[0].read_bytes(), file_name=paths[0].name, mime="application/x-ipynb+json")
        return
    report_kind = st.query_params.get("ce_report")
    if report_kind:
        shard, selected, case = select_record(package, painting, candidate)
        resource_header(painting,selected,"Painting report" if report_kind=="painting" else "Detailed case report","The original saved HTML report is shown below, unchanged. Its scope and identities belong to the report, not a newly generated summary.")
        reports = reports_for(shard,case["case_id"])
        if report_kind not in reports or reports[report_kind] is None:
            st.error("Not selected for a detailed case report. No other report has been substituted.")
            return
        result = package.local_report_bytes(reports[report_kind]["report_id"])
        if result is None:
            st.warning("The exact registered report is not available locally. No report has been substituted.")
            return
        data, filename = result
        st.download_button("Download original saved report",data,file_name=filename,mime="text/html")
        components.html(data.decode("utf-8"),height=780,scrolling=True)
        return
    try:
        data = payload(package,painting,candidate,str(st.query_params.get("ce_layer","difference")),st.query_params.get("ce_map"))
    except (ValueError,FileNotFoundError) as exc:
        st.error(f"Case Explorer cannot display this selection: {exc}")
        return
    panel = st.query_params.get("ce_panel")
    if panel:
        allowed = saved_panels(package,"example_retrieval_panels")+saved_panels(package,"counterfactual_panels")
        if panel not in allowed:
            st.error("Unknown stored study panel; no substitute selected.")
            return
        data["open_panel"]={"path":panel,"uri":asset_uri(package,panel)}
    data["retrieval"] = retrieval_rows()
    data["counterfactual_choices"]=counterfactual_choices()
    if st.query_params.get('ce_cf'):
        matches=[row for row in data['counterfactual_choices']
                 if row['family']==st.query_params['ce_cf'] and row['value']==st.query_params.get('ce_value')
                 and row['candidate_id']==data['candidate']['candidate_id']
                 and row['panel_path']==st.query_params.get('ce_cf_panel')]
        if len(matches)!=1:
            st.error('No exact saved comparison matches this selection. No substitute was used.')
            return
        data['selected_comparison']=matches[0]
    data["source_notebooks"] = []
    for notebook_id in data["candidate"]["source_notebook_ids"]:
        files=list((ROOT/"notebooks").glob(str(notebook_id)+"_*.ipynb"))
        data["source_notebooks"].append({"id":notebook_id,"title":files[0].stem.split("_",1)[-1].replace("_"," ") if len(files)==1 else "Recorded notebook", "available":len(files)==1})
    data["open_view"] = str(st.query_params.get("ce_view",""))
    # One original stored panel supplies all ten thumbnail windows; it is not
    # evidence for the active candidate and is labelled as a different case.
    retrieval_sheet = "outputs/29_explainable_ai_and_case_retrieval/figures/example_retrieval_panels/query_03_landscape_natural_lower_risk.png"
    try:
        data["retrieval_sheet_uri"] = asset_uri(package,retrieval_sheet)
    except (ValueError,FileNotFoundError):
        data["retrieval_sheet_uri"] = None
    data["counterfactual_panels"] = saved_panels(package,"counterfactual_panels")
    data["retrieval_panels"] = saved_panels(package,"example_retrieval_panels")
    css=(ROOT/"streamlit_assets/case_explorer.css").read_text(encoding="utf-8")
    from .room_runtime import room_html, room_controller
    revision = room_html('<style>'+css+'</style>'+room_markup(data,navigation,image_uri(str(ROOT/"streamlit_assets/rooms/case_explorer_shell.png")),image_uri(str(ROOT/"streamlit_assets/rooms/case_explorer_lettering.png")),image_uri(str(ROOT/"streamlit_assets/rooms/case_explorer_neutral_layer.png")),image_uri(str(ROOT/"streamlit_assets/rooms/case_explorer_title_enhanced.png"))))
    data.pop("retrieval_sheet_uri",None)  # already present once in the room CSS
    js=(ROOT/"streamlit_assets/case_explorer_controller.js").read_text(encoding="utf-8")
    serialized=json.dumps(data,ensure_ascii=False,allow_nan=False).replace("</","<\\/")
    room_controller(js.replace("__CASE_EXPLORER_PAYLOAD__",serialized), revision)
