"""Live, evidence-bound overlays for the approved D02 portrait print room."""
import html
import json
from urllib.parse import urlencode

import streamlit as st
import streamlit.components.v1 as components

from .focused_portrait import ROOT, OPENING, RETURN_ROOMS, D02, REPORT, payload, verified_source
from .model_gallery import image_uri
from .trustworthiness_view import rect, nav_images


def esc(value):
    return html.escape(str(value), quote=True)


REFERENCE_PLAQUES = {
    "screened": ("screened", 60, "100,214 178,223 178,282 101,278"),
    "regions": ("annotations", 91, "303,307 374,313 374,381 303,377"),
    "cases": ("hand_cases", 45, "220,369 290,371 290,428 220,426"),
    "paintings": ("hand_paintings", 20, "166,461 238,461 238,517 166,517"),
    "reviews": ("reviews", 32, "273,511 351,509 351,560 273,563"),
}
REFERENCE_BOOKS = (
    "64,757 280,738 283,777 66,796",
    "82,794 262,775 265,813 85,834",
    "83,839 300,810 303,850 86,879",
    "86,876 247,852 251,893 90,918",
)
REFERENCE_REVIEW_DETAILS = (
    "1384,494 1577,494 1577,524 1384,524",  # Blind-review heading plaque.
    "1570,533 1633,535 1624,640 1558,638",  # Four observation plaques.
    "1312,644 1607,654 1605,683 1307,672",  # Review selector, divider, arrows.
)
REFERENCE_RETURN_SIGN = "1166,146 1316,157 1316,212 1166,202"
REFERENCE_PRINT_CAPTIONS = (
    "418,622 521,623 520,648 417,647",
    "561,623 665,623 665,648 560,648",
    "700,623 803,623 803,648 700,648",
    "843,623 947,623 947,648 843,648",
    "988,623 1102,623 1102,648 989,648",
)


def room_markup(data, navigation, shell, reference=None):
    r, s = data["review"], data["scope"]
    parent = data["return_room"]
    reference_keys = {key for key,(field,count,_) in REFERENCE_PLAQUES.items()
                      if reference and s[field] == count}
    parts = [f'<main class="fpr-stage" data-version="{esc(data["version"])}" aria-label="Focused Portrait Review mini room" style="background-image:url({shell})">', nav_images(navigation)]
    if reference:
        # Show unaltered reference pixels only in the requested regions.
        # A changed recorded count falls back to live text, never stale artwork.
        polygons = [points for key,(_,_,points) in REFERENCE_PLAQUES.items() if key in reference_keys]
        polygons.extend(REFERENCE_BOOKS)
        polygons.extend(REFERENCE_REVIEW_DETAILS)
        polygons.extend(REFERENCE_PRINT_CAPTIONS)
        if parent == "trustworthiness":
            polygons.append(REFERENCE_RETURN_SIGN)
        # One image, disjoint polygons; doubled zero-width bridges keep
        # the gaps transparent without repeating the full bitmap.
        clips = ['0% 0%']
        for points in polygons:
            vertices = [tuple(map(int, point.split(','))) for point in points.split()]
            clips.extend(f'{x/1672*100:.6f}% {y/941*100:.6f}%' for x,y in vertices + vertices[:1])
            clips.append('0% 0%')
        clip = ','.join(clips)
        parts.append(f'<img class="fpr-reference-details" alt="" aria-hidden="true" src="{esc(reference)}" data-reference-regions="{len(polygons)}" style="clip-path:polygon(evenodd,{clip})">')
    def text(cls, bounds, content):
        parts.append(f'<div class="{cls}" style="{rect(*bounds)}">{content}</div>')
    def button(action, bounds, content, label, cls="fpr-plaque"):
        parts.append(f'<button type="button" class="{cls}" style="{rect(*bounds)}" data-action="{action}" aria-label="{esc(label)}">{content}</button>')
    # Live, transparent lettering: reference wall pixels leave a visible seam
    # against the cleaned shell, even when their rectangular edge is softened.
    text("fpr-title", (477,111,605,109), '<h1>Focused Portrait Review</h1><h2>Are damaged hands harder to restore?</h2><p>A focused audit using existing portrait restorations.</p>')
    original_return = " fpr-original-detail" if reference and parent == "trustworthiness" else ""
    parts.append(f'<a class="fpr-back fpr-door{original_return}" style="{rect(1166,146,150,66)}" href="?room={parent}" target="_self"><span>← Back to<br>{RETURN_ROOMS[parent]}</span></a>')
    text("fpr-study-title", (107,144,282,49), "How the study was formed")
    for key,bounds,count,label in (
        ("screened",(107,228,65,44),s["screened"],"portraits"),
        ("regions",(308,318,63,58),s["annotations"],"reviewed<br>regions"),
        ("cases",(222,379,66,41),s["hand_cases"],"hand cases"),
        ("paintings",(171,469,65,43),s["hand_paintings"],"paintings"),
        ("reviews",(278,517,72,39),s["reviews"],"blind reviews"),
    ):
        original = " fpr-original-detail" if key in reference_keys else ""
        button("formation",bounds,f'<span class="fpr-count">{count}</span><span class="fpr-count-caption">{label}</span>',"How the study was formed",f"fpr-plaque fpr-formation-label fpr-formation-{key}{original}")
    # Bounds and corner masks follow the actual inner apertures of the shell,
    # not the outer mouldings. Each frame has its own perspective.
    for item, key, bounds in zip(data["miniatures"],("upper","middle","lower","right"),((190,198,58,90),(131,308,78,111),(96,456,58,79),(306,248,53,65))):
        button("formation", bounds, f'<img src="{item["uri"]}" alt="Screened portrait {item["painting_id"]}">', "Inspect portrait screening", f"fpr-miniature fpr-frame-{key}")
    button("annotation", (305,420,59,86), '<canvas data-canvas="annotation-mini"></canvas>', "Inspect the selected anatomical annotation", "fpr-miniature fpr-frame-anatomy")
    text("fpr-hand-title", (478,248,396,29), "Hand penalty · damaged vs. matched control")
    button("hand", (477,282,377,135), '<div class="fpr-hand-chart"></div>', "Inspect hand penalties and uncertainty intervals", "fpr-chart-button")
    text("fpr-findings", (880,253,185,143), f'<h3>Key findings</h3><p><strong>{sum(x["estimate"]>0 for x in data["hand"])}/12</strong> worse for hands</p><p><strong>{sum(x["q_value"]<.05 for x in data["hand"])}/12</strong> supported<br>after correction</p><small>No single method minimized<br>all three hand penalties.</small>')
    text("fpr-hand-selector", (880,397,190,28), '<label>Metric <select aria-label="Hand penalty metric"><option value="mae">RGB MAE</option><option value="delta_e_ciede2000_mean">CIEDE2000</option><option value="ssim">SSIM penalty</option></select></label>')
    button("hand", (551,438,405,19), "Damaged hands were harder to restore in this audit.", "Read the hand-study conclusion")
    original = " fpr-original-detail" if reference else ""
    for key,label,bounds,caption in (
        ("clean","Clean",(411,501,130,121),(418,623,103,24)),
        ("damaged","Damaged + mask",(555,501,121,120),(561,623,104,25)),
        ("restored","Restored",(697,501,113,120),(700,623,103,25)),
        ("difference","Difference",(835,501,119,120),(843,623,104,25)),
        ("control","Matched control",(973,501,135,120),(988,623,114,25)),
    ):
        button("image:"+key,bounds,f'<canvas data-canvas="{key}" aria-label="{label} · selected review crop"></canvas>',"Inspect "+label.lower(),"fpr-print fpr-table-print fpr-table-"+key)
        button("image:"+key,caption,f'<span>{label}</span>',"Inspect "+label.lower(),"fpr-plaque fpr-print-caption"+original)
    button("previous",(606,661,27,26),"◀","Previous recorded review")
    button("select",(638,661,226,27),f'{esc(r["painting_id"])} · {esc(r["damage_family"].replace("_"," "))} · {esc(data["labels"][r["model_id"]])}',"Select portrait, case and method")
    button("next",(867,661,25,26),"▶","Next recorded review")
    button("eligibility",(425,723,245,44),f'<span>Why this case counts</span><span>{data["overlap"]["damaged_anatomical_pixels"]:,} damaged hand pixels</span><span>{data["overlap"]["anatomical_fraction_affected"]:.2%} affected</span>',"Inspect eligibility and matched control","fpr-plaque fpr-eligibility")
    for action,x,w,label in (("report",781,63,"D02 report"),("annotation",862,67,"Annotations"),("tables",945,52,"Tables"),("methods",1016,88,"Methods & limits")):
        button(action,(x,736,w,22),f'<span>{label}</span>',label,"fpr-plaque fpr-resource-label")
    text("fpr-lightness-title",(1386,153,241,46),'Rendered lightness<span>Exploratory associations</span>')
    text("fpr-lightness-selector",(1396,204,222,23),'<label><span>View</span><select aria-label="Rendered lightness metric"><option value="chroma_error_mean">Chroma error</option><option value="delta_e_ciede2000_mean">CIEDE2000</option><option value="lightness_error_mean">Lightness error</option><option value="mae">RGB MAE</option><option value="psnr">PSNR (oriented)</option><option value="rmse">RGB RMSE</option></select></label>')
    button("lightness",(1392,240,231,117),'<div class="fpr-lightness-chart"></div>',"Inspect adjusted lightness associations","fpr-chart-button")
    button("lightness",(1395,368,230,77),'<span class="fpr-lightness-reading"></span><span class="fpr-lightness-counts"></span><small class="fpr-lightness-scope">Selected metric · 4 methods</small><strong>Rendered L* is not race or identity.</strong>',"Read rendered-lightness findings and context","fpr-plaque fpr-lightness-findings")
    original = " fpr-original-detail" if reference else ""
    text("fpr-review-title"+original,(1392,502,174,22),"<span>Blind visual review</span>")
    button("image:clean",(1362,533,96,108),'<canvas data-canvas="blind-clean"></canvas>',"Inspect clean anatomy crop","fpr-print fpr-folio-print fpr-folio-clean")
    button("review",(1471,534,94,107),'<canvas data-canvas="blind-restored"></canvas>',"Inspect restored anatomy and blind review","fpr-print fpr-folio-print fpr-folio-restored")
    for label,bounds in (("digits",(1570,535,61,26)),("contour",(1567,561,61,25)),("wrist",(1564,586,61,26)),("texture",(1561,612,61,25))):
        button("observation:"+label,bounds,f'<span>{label}</span>',f"Read exact recorded anatomical observations: {label}","fpr-plaque fpr-observation-plaque"+original)
    button("failure",(1313,648,124,27),"<span>◀ &nbsp; Visible failure</span>","Select a visible-failure review","fpr-plaque fpr-review-choice"+original)
    button("counterexample",(1440,653,164,28),"<span>Acceptable counterexample &nbsp; ▶</span>","Select an acceptable counterexample","fpr-plaque fpr-review-choice"+original)
    selected_status = "failure" if r["overall_anatomy_failure"] else "acceptable"
    text("fpr-review-result",(1339,714,237,45),f'<span class="fpr-review-summary">{s["visible_failures"]} of {s["reviews"]}: visible anatomy failure<br>Model names hidden during review.</span><small>{esc(r["blind_review_code"])} · {selected_status} · {esc(r["reviewer_confidence"])} confidence</small>')
    for key,title,bounds in (("screening","Portrait screening",(70,751,216,32)),("anatomy","Hand anatomy",(84,794,186,31)),("controls","Matched controls",(85,834,226,32)),("review","Blind review",(91,877,178,32))):
        original = " fpr-original-detail" if reference else ""
        text(f"fpr-book fpr-book-{key}{original}",bounds, f'<span>{title}</span>')
    parts.append('<dialog class="fpr-dialog" aria-labelledby="fpr-dialog-title"><header><div><small>THE PORTRAIT PRINT ROOM</small><h2 id="fpr-dialog-title"></h2><p class="fpr-dialog-context"></p></div><button data-action="close" aria-label="Close portrait evidence">Close <span aria-hidden="true">×</span></button></header><div class="fpr-dialog-body"></div></dialog><span class="fpr-sr" role="status" aria-live="polite"></span></main>')
    return "".join(parts)


def render_original_report(code, parent):
    """Display the complete checksum-verified report, not a substitute summary."""
    report = verified_source(D02+"/"+REPORT).read_bytes()
    return_url = "?"+urlencode({"room":"focused_portrait_review","return_room":parent,"portrait_review":code})
    st.html(f'<div style="padding:12px 18px;color:#f3ead7;font-family:Georgia,serif"><a style="color:#e8ce96" href="{esc(return_url)}" target="_self">← Return to the mini room</a><p style="color:#f3ead7;margin:8px 0 0;font-size:14px">Original D02 report · complete recorded tables and source visuals · no new analysis</p></div>')
    st.download_button("Download D02 report (HTML)", report,
                       file_name="D02_portrait_audit.html", mime="text/html")
    components.html(report.decode("utf-8"), height=760, scrolling=True)


def render_focused_portrait(package, navigation):
    code = str(st.query_params.get("portrait_review", OPENING))
    parent = str(st.query_params.get("return_room", "trustworthiness"))
    try:
        data = payload(package, code, parent)
    except (ValueError, OSError, KeyError) as error:
        st.error(f"Focused Portrait Review cannot show this record: {error}")
        st.link_button("Return to the declared opening review", "?room=focused_portrait_review&return_room=trustworthiness")
        return
    if st.query_params.get("portrait_resource") == "report":
        render_original_report(code, data["return_room"])
        return
    css = (ROOT / "streamlit_assets/focused_portrait.css").read_text(encoding="utf-8")
    shell = image_uri(str(ROOT / "streamlit_assets/rooms/focused_portrait_review_shell.png"))
    reference = image_uri(str(ROOT / "streamlit_assets/rooms/focused_portrait_reference_details.png"))
    from .room_runtime import room_html, room_controller
    revision = room_html(f'<style>{css}</style>'+room_markup(data,navigation,shell,reference))
    js = (ROOT / "streamlit_assets/focused_portrait_controller.js").read_text(encoding="utf-8")
    serialized = json.dumps(data,ensure_ascii=True,allow_nan=False).replace("</","<\\/")
    room_controller(js.replace('__PORTRAIT_PAYLOAD__',serialized), revision)
