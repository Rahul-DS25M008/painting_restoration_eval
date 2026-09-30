"""Isolated initial presentation of the recorded Trustworthiness review route."""
import base64
import html
import json
import re

import streamlit as st
import streamlit.components.v1 as components

from .trustworthiness import ROOT, OPENING, payload, image_uri


def esc(value):
    return html.escape(str(value), quote=True)


def rect(x, y, w, h):
    return f"left:{x/1672*100:.5f}%;top:{y/941*100:.5f}%;width:{w/1672*100:.5f}%;height:{h/941*100:.5f}%"


def reference_window(uri, bounds):
    """Display an exact, responsive window into the approved 1672 x 941 art."""
    x, y, w, h = bounds
    return (f'<img src="{uri}" alt="" aria-hidden="true" '
            f'style="position:absolute;max-width:none;width:{1672/w*100:.8f}%;'
            f'height:{941/h*100:.8f}%;left:{-x/w*100:.8f}%;top:{-y/h*100:.8f}%">')


def portrait_alcove(reference):
    """Reference artwork and literal wall copy, with the shared D02 room link."""
    bounds = (1494, 279, 161, 374)
    copy = ("Focused portrait review — separate study. "
            "45 hand cases · 20 paintings. 12/12 estimates worse for hands. "
            "10/12 significant after correction. "
            "Rendered lightness was tested—not race or ethnicity.")
    return (f'<div class="trust-alcove-reference" style="{rect(*bounds)}">'
            + reference_window(reference, bounds)
            + f'<span class="trust-sr-only">{esc(copy)}</span></div>'
            + f'<a class="trust-alcove-portrait-link" style="{rect(1506,331,146,148)}" '
            'href="?room=focused_portrait_review&amp;return_room=trustworthiness" target="_self" '
            'aria-label="Open Focused Portrait Review — hand anatomy study"></a>')


def frame_crop(box, width, height):
    """Aspect-preserving, centred cover of recorded content, thumbnails only."""
    x0, y0, x1, y1 = box
    scale = max(width / (x1-x0), height / (y1-y0))
    return (f'position:absolute;width:{768*scale/width*100}%;height:{768*scale/height*100}%;'
            f'left:{((width-(x1-x0)*scale)/2-x0*scale)/width*100}%;'
            f'top:{((height-(y1-y0)*scale)/2-y0*scale)/height*100}%')


def book_spines():
    """Quiet foil-stamped, code-native ornaments; no change to room artwork."""
    books = (
        ("Cosmos", 622, -3, "#8b6a38", '<ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(-30 12 12)"/><circle cx="12" cy="12" r="3"/><path d="M18 2v4m-2-2h4"/>'),
        ("Animal Farm", 652, -3, "#c2aa72", '<path d="M5 15V9l5-3 5 3v8H5zm5-9V2m0 4L4 2m6 4 6-4M2 17h19M17 12h4v5h-4z"/>'),
        ("Odyssey", 680, -4, "#b6a16f", '<path d="M2 16h20l-4 4H7zm10 0V2L4 13h8m2-9 6 9h-6M2 23q3-3 6 0t6 0t6 0"/>'),
        ("Gulliver’s Travels", 709, -4, "#cfb481", '<circle cx="12" cy="12" r="9"/><path d="m16 6-2 8-6 4 2-8zM12 1v3m0 16v3M1 12h3m16 0h3"/>'),
        ("1984", 739, -5, "#bfa875", '<path d="M1 12q11-15 22 0-11 15-22 0z"/><circle cx="12" cy="12" r="4"/><path d="M12 8v8"/>'),
    )
    result = []
    for title, y, angle, ink, drawing in books:
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{ink}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">{drawing}</svg>'
        uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
        size = ".62cqw" if len(title) > 14 else ".73cqw"
        shift, lift = ("0px", "0px") if title == "Cosmos" else (("2px", "-3.5px") if title == "Animal Farm" else ("3px", "-6.5px"))
        result.append(f'<div class="trust-book trust-book-literary" style="{rect(44,y,143,17)};--book-shift:{shift};--book-lift:{lift};--book-angle:{angle}deg;--book-ink:{ink};--book-size:{size}"><img src="{uri}" alt="" aria-hidden="true"><span>{esc(title)}</span></div>')
    return "".join(result)


def plaque_icon(kind):
    drawings = {
        "rules": '<path d="M12 5C8 2 3 3 2 4v15c3-2 7-2 10 0 3-2 7-2 10 0V4c-3-2-7-2-10 1zm0 0v14"/>',
        "policy": '<path d="M2 5h6m4 0h10M2 12h12m4 0h4M2 19h4m4 0h12"/><circle cx="10" cy="5" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="8" cy="19" r="2"/>',
        "full": '<path d="M5 2h9l5 5v15H5zM14 2v6h5M8 12h8M8 16h8M8 19h5"/>',
        "inspect": '<circle cx="9.5" cy="9.5" r="7.5"/><path d="m15 15 7 7"/>',
    }
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#392815" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{drawings[kind]}</svg>'
    uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    return f'<img class="trust-plaque-icon" src="{uri}" alt="" aria-hidden="true">'


def recommendation_tag(recommendation):
    """Reference-style label; retain the selected record's recommendation."""
    wording = ("Unstable<br>candidate ·<br>inspect<br>manually"
               if recommendation.casefold() == "unstable candidate"
               else esc(recommendation.capitalize()))
    return (f'<span class="trust-recommendation-wording">{wording}</span>'
            '<span class="trust-recommendation-rule" aria-hidden="true"></span>'
            + plaque_icon("inspect"))


def nav_images(text):
    def replace(match):
        svg = match.group(0)
        stroke = "#a6232c" if "0 0 40 40" in svg else "#0085bd"
        svg = svg.replace('<svg ', f'<svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="{stroke}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" ', 1)
        return '<img alt="" src="data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode() + '">'
    return re.sub(r"<svg\b.*?</svg>", replace, text, flags=re.DOTALL)


def render_trustworthiness(package, navigation):
    try:
        data = payload(package, st.query_params.get("trust_candidate", OPENING))
    except (ValueError, KeyError, FileNotFoundError) as error:
        st.error(f"Trustworthiness cannot show this record: {error}")
        st.link_button("Return to the declared opening case", "?room=trustworthiness")
        return
    data["painting_titles"] = {r["painting_id"]: str(r.get("title") or r["painting_id"])
                               for r in package.painting_lookup.to_dict("records")}
    c = data["candidate"]
    shell = image_uri(str(ROOT / "streamlit_assets/rooms/trustworthiness_shell.png"))
    css = (ROOT / "streamlit_assets/trustworthiness.css").read_text(encoding="utf-8")
    parts = [f'<style>{css}</style><main class="trust-stage" data-version="{esc(data["version"])}" aria-label="Trustworthiness review room" style="background-image:url({shell})">', navigation]
    def text(cls, bounds, content):
        parts.append(f'<div class="{cls}" style="{rect(*bounds)}">{content}</div>')
    def button(action, bounds, label, cls="trust-plaque", aria=None):
        accessible = aria or re.sub(r"<[^>]+>", " ", label)
        parts.append(f'<button type="button" class="{cls}" style="{rect(*bounds)}" data-action="{action}" aria-label="{esc(accessible)}">{label}</button>')
    portrait = image_uri(str(ROOT / "streamlit_assets/rooms/trustworthiness_zhongli.png"))
    text("trust-side-portrait",(52,133,61,337),f'<img src="{portrait}" alt="Decorative faceless portrait of Zhongli in his brown and gold coat">')
    archons = image_uri(str(ROOT / "streamlit_assets/rooms/trustworthiness_archons_group.png"))
    text("trust-archons-frame",(1518,684,154,183),reference_window(archons,(1463,592,209,249))+'<span class="trust-sr-only">Framed faceless group portrait of the seven Archons of Teyvat in muted sepia.</span>')
    text("trust-heading", (516,129,361,73), '<h1>Trustworthiness</h1>')
    parts.append(f'<span class="trust-heading-divider" style="{rect(888,131,1.5,67)}" aria-hidden="true"></span>')
    text("trust-question", (912,132,510,72), '<h2>Why did this restoration receive a review flag?</h2><p>Flags help us decide what to inspect. They are not probabilities, expert verdicts, or proof that a restoration is right or wrong.</p>')
    button("record", (174,158,258,34), f'<strong>{esc(c["painting_id"])} · {esc(data["labels"][c["model_id"]])}</strong><small>{esc(c["case_id"].split("__",2)[-1].replace("_"," "))}'+(f' · seed {int(c["seed"])}' if c.get("seed") else '')+'</small>', "trust-plaque trust-identity", "Selected candidate record")
    for (label, uri), (x,y,w,h) in zip(data["images"].items(), ((160,225,94,237),(268,238,83,224),(364,249,77,211))):
        crop = frame_crop(data["content_bbox"], w, h)
        parts.append(f'<button class="trust-painting" data-action="images" title="Cropped cabinet preview — click for the complete image" aria-label="Inspect {label.lower()} image" style="{rect(x,y,w,h)}"><img style="{crop}" src="{uri}" alt="{label} · {esc(c["painting_id"])} · cropped preview"></button>')
    for label, x, w in (("Clean",160,94),("Damaged",268,83),("Restored",364,77)):
        text("trust-plaque trust-image-caption",(x,476,w,26),esc(label))
    button("find",(226,521,167,21),"Find a candidate",aria="Find a candidate")
    for label,x,y,w in (("Category",183,576,62),("Painting",253,575,61),("Case",322,574,60),("Method",390,573,64)):
        button("find",(x,y,w,19),label, "trust-plaque trust-catalogue-label")
    button("find",(282,607,163,20),"Seed / prompt · exact ID", "trust-plaque trust-catalogue-label")
    stations = [("evidence",487,104,"Candidate<br>evidence"),("peers",610,115,"Fair comparison<br>group"),("threshold",820,112,"Threshold"),("category",1033,107,"Failure<br>category"),("flags",1170,122,"Review flags"),("recommendation",1320,111,"Recommendation")]
    for i,(action,x,w,label) in enumerate(stations,1):
        text(f"trust-station-number trust-station-number-{i}",(x+w/2-18,226,36,33),str(i))
        button(action,(x,273,w,32),label,"trust-plaque trust-station-label")
    evidence_reference = image_uri(str(ROOT / "streamlit_assets/rooms/trustworthiness_evidence_reference.png"))
    button("evidence",(487,322,108,232),f'<img src="{evidence_reference}" alt="" aria-hidden="true"><span class="trust-sr-only">Reference illustration. Open the selected candidate’s recorded evidence.</span>',"trust-plaque trust-reference-evidence","Candidate evidence")
    text("trust-evidence-caption",(500,599,109,74),"The candidate, its<br>damage, and restoration<br>for inspection.")
    text("trust-comparison-caption",(615,599,111,65),"A fair and relevant<br>group for comparison.")
    for action,y,label in (("peers",352,"Comparison peers"),("stratum",391,"Same experiment"),("stratum",431,"Same indicator"),("stratum",470,"Region + statistic"),("stratum",522,"Fitting population")):
        button(action,(614,y,86,28),label,"trust-plaque trust-drawer")
    text("trust-ruler",(748,344,254,214),'<div class="trust-ruler-title"></div><div class="trust-ruler-chart"></div><div class="trust-ruler-note"></div>')
    button("threshold",(748,614,252,42),"How this boundary was fitted","trust-plaque trust-threshold-reference",aria="Threshold reference stratum")
    button("category",(1045,399,82,72),'<span class="trust-category-label">Texture<br>smoothing</span><span class="trust-category-severity"></span>',"trust-category-seal","Selected failure category")
    text("trust-category-caption",(1043,607,104,51),"The main reason<br>for the flag.")
    for flag,x,y,label in (("high_generative_uncertainty",1176,338,"Uncertainty"),("texture_inconsistency",1246,338,"Texture"),("restoration_instability",1176,426,"Instability"),("metric_disagreement",1246,426,"Disagreement"),("colour_inconsistency",1213,511,"Colour unresolved")):
        parts.append(f'<button class="trust-flag-seal" data-flag="{flag}" style="{rect(x,y,40,37)}" aria-label="{esc(label)}"><span aria-hidden="true">•</span></button>')
        text("trust-flag-caption",(x-10,y+44,62,26),label)
    button("flags",(1169,581,126,18),"Open all 11 flags", "trust-plaque trust-drawer")
    text("trust-flags-wall-caption",(1170,619,145,45),"Additional signals<br>that informed this review.")
    text("trust-recommendation-caption",(1320,607,114,51),"Our recommendation<br>for this case.")
    button("recommendation",(1337,391,79,145),recommendation_tag(data["recommendation"]),"trust-plaque trust-recommendation","Recorded recommendation")
    for action,x,w,label in (("rules",622,150,"How thresholds work"),("policy",807,137,"Policy sensitivity"),("full",983,157,"View full evidence")):
        content = plaque_icon(action) + f'<span>{label}</span><i class="trust-plaque-chevron" aria-hidden="true"></i>'
        button(action,(x,690,w,27),content,"trust-plaque trust-footer-control",label)
    button("boundary",(1246,682,130,30),"<span>Flags are a screening</span><span>signal, not a verdict.</span>","trust-plaque trust-reference-boundary","Interpretation boundaries")
    text("trust-alcove-heading",(1481,111,159,74),"<span>Different questions.</span><span>Richer evidence.</span><span>A more complete story.</span>")
    parts.append(portrait_alcove(evidence_reference))
    parts.append(book_spines())
    parts.append('<dialog class="trust-dialog" aria-labelledby="trust-dialog-title"><header><div><span>THE REVIEW CHAMBER · RECORDED EVIDENCE</span><h2 id="trust-dialog-title"></h2></div><button data-action="close" aria-label="Close review record">Close ×</button></header><div class="trust-dialog-body"></div></dialog><span class="trust-live" role="status" aria-live="polite"></span></main>')
    from .room_runtime import room_html, room_controller
    revision = room_html(nav_images("".join(parts)))
    js = (ROOT / "streamlit_assets/trustworthiness_controller.js").read_text(encoding="utf-8")
    serialized = json.dumps(data, ensure_ascii=True, allow_nan=False).replace("</", "<\\/")
    room_controller(js.replace("__TRUST_PAYLOAD__", serialized), revision)
