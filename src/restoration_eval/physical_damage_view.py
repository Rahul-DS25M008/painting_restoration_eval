"""The approved single physical-damage hall, with in-room evidence dialogs."""
import base64
import html
import json
from urllib.parse import urlencode

import streamlit as st

from . import physical_damage as evidence
from .room_runtime import room_controller, room_html
from .trustworthiness_view import nav_images, rect

ASSETS = evidence.ROOT / "streamlit_assets"
# Inner corners (TL, TR, BR, BL) of the decorative 1672 x 941 shell.
# Only selectors receive perspective projection; inspection views stay undistorted.
APERTURES = {
    "rd001": ((470,198),(576,182),(597,261),(489,275)),
    "rd002": ((635,178),(743,165),(761,244),(652,258)),
    "rd003": ((1008,166),(1128,176),(1118,248),(996,242)),
    "rd004": ((1191,185),(1303,198),(1285,277),(1178,268)),
    "rd005": ((1468,353),(1554,403),(1537,468),(1446,447)),
    "rd006": ((1452,516),(1552,535),(1526,624),(1422,601)),
    "rd007": ((139,434),(244,395),(264,486),(159,516)),
    "rd008": ((165,582),(259,561),(287,644),(185,666)),
    "rd009": ((1079,751),(1193,739),(1205,812),(1090,823)),
    "rd010": ((1272,738),(1387,741),(1380,816),(1263,811)),
}
PLAQUES = {
    "rd001": (512,281,74,24,-8), "rd002": (675,260,76,23,-6),
    "rd003": (1017,262,78,23,4), "rd004": (1189,284,75,23,7),
    "rd005": (1458,465,67,25,15), "rd006": (1432,626,70,24,13),
    "rd007": (181,511,73,24,-15), "rd008": (211,666,71,24,-12),
    "rd009": (1116,830,74,23,-3), "rd010": (1283,824,76,24,3),
}


def frame_bounds(key):
    points = APERTURES[key]
    x, y = min(p[0] for p in points), min(p[1] for p in points)
    return x, y, max(p[0] for p in points)-x, max(p[1] for p in points)-y


def esc(value):
    return html.escape(str(value), quote=True)


def link(case, panel=""):
    query = {"room": "physical_damage_study", "pd_case": case}
    if panel:
        query["pd_panel"] = panel
    return "?" + urlencode(query)


def markup(data, navigation, shell, plaque=None):
    selected = data["case"]
    title = data["artwork"]["title"]
    plaque_style = f";--pd-plaque:url({esc(plaque)})" if plaque else ""
    parts = [f'<main class="pd-stage" aria-label="Physical Damage Study supplementary room" data-case="{selected}" style="background-image:url({esc(shell)}){plaque_style}">', nav_images(navigation)]
    for (_, label, _), (x, y, w, angle) in zip(evidence.CATEGORIES, ((474,145,278,-8),(1023,137,250,5),(1434,316,160,43),(83,354,208,-30),(1090,700,320,-3))):
        parts.append(f'<div class="pd-category" style="{rect(x,y,w,28)};--angle:{angle}deg">{label}</div>')
    x,y,w,h = frame_bounds(selected)
    # Restrained, live selection trace; never baked into an evidence image.
    cx, cy = x+w/2, y+h/2
    if y < 300:
        start, end = (cx, y+h+38), (min(max(cx,450),1250), 365)
    elif y > 700:
        start, end = (cx, y-15), (min(cx,1250), 652)
    elif x < 300:
        start, end = (x+w+25, cy), (370, min(max(cy,390),620))
    else:
        start, end = (x-20, cy), (1320, min(max(cy,390),620))
    trace = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1672 941"><path d="M {start[0]} {start[1]} L {end[0]} {end[1]}" fill="none" stroke="#f3cf75" stroke-width="3" stroke-dasharray="5 4"/><circle cx="{end[0]}" cy="{end[1]}" r="4" fill="#f3cf75"/></svg>'
    trace_uri = "data:image/svg+xml;base64," + base64.b64encode(trace.encode()).decode()
    parts.append(f'<img class="pd-trace" src="{trace_uri}" alt="" aria-hidden="true">')
    parts.append('<section class="pd-collection" aria-label="Choose one of ten paintings">')
    for item in data["collection"]:
        key = item["id"]
        x,y,w,h = frame_bounds(key)
        corners = [[(px-x)/w, (py-y)/h] for px,py in APERTURES[key]]
        polygon = ",".join(f"{px*100:.5f}% {py*100:.5f}%" for px,py in corners)
        lx,ly,lw,lh,angle = PLAQUES[key]
        plaque = f"left:{(lx-x)/w*100:.5f}%;top:{(ly-y)/h*100:.5f}%;width:{lw/w*100:.5f}%;height:{lh/h*100:.5f}%;--angle:{angle}deg"
        current = ' aria-current="true"' if key == selected else ''
        parts.append(f'<a class="pd-exhibit{" selected" if key == selected else ""}" href="{esc(link(key))}" target="_self" {current} style="{rect(x,y,w,h)}" aria-label="{esc(key+": "+item["title"])}"><div class="pd-aperture" style="clip-path:polygon({polygon})"><canvas data-exhibit="{key}" data-corners="{esc(json.dumps(corners))}" aria-hidden="true"></canvas></div><span class="pd-catalogue-label" style="{plaque}"><small>RD</small><b>{key[2:]}</b></span></a>')
    parts.append('</section><section class="pd-table" aria-label="Selected painting and four primary restorations">')
    parts.append('<header class="pd-heading"><h1>Physical Damage Study</h1><p>10 paintings · 4 methods · no clean reference</p><a href="?room=study_design" target="_self" aria-label="Return to Study Design">← Study Design</a></header>')
    parts.append(f'<h2><span>{selected}</span> {esc(title)}</h2>')
    parts.append('<div class="pd-tools"><div class="pd-view-switch" role="group" aria-label="Image region"><button type="button" data-mode="whole" aria-pressed="true">Full painting</button><button type="button" data-mode="detail" aria-pressed="false">Same detail</button></div><button type="button" data-mask aria-pressed="false">Show mask</button>')
    for panel, label in (("seeds","Four seeds"),("evidence","Evidence")):
        parts.append(f'<a href="{esc(link(selected,panel))}" target="_self">{label} ↗</a>')
    parts.append('</div><div class="pd-prints">')
    for i, item in enumerate(data["images"]):
        parts.append(f'<button type="button" class="pd-print" data-image="{i}" aria-label="Enlarge {esc(item["label"])}"><span>{esc(item["label"])}</span><canvas data-print="{i}" aria-hidden="true"></canvas></button>')
    parts.append('</div><p class="pd-table-note" aria-live="polite">Click an image to inspect · selected repair targets only · SD primary seed 2026</p>')
    parts.append('<div class="pd-room-note"><p>Real damage. Possible completions. No known original to recover.</p><div>')
    for panel, label in (("comparison","Controlled comparison"),("sources","Sources & settings"),("report","Full study report")):
        parts.append(f'<a href="{esc(link(selected,panel))}" target="_self">{label} ↗</a>')
    parts.append('</div></div></section></main>')
    return "".join(parts)


def render_physical_damage(navigation):
    case = st.query_params.get("pd_case", evidence.OPENING)
    panel = st.query_params.get("pd_panel", "")
    try:
        data = evidence.payload(case, panel)
        shell = evidence.static_media("streamlit_assets/rooms/physical_damage_study_shell_stone.png")
        plaque = evidence.static_media("streamlit_assets/rooms/physical_damage_link_plaque.png")
    except (ValueError, KeyError, OSError, StopIteration) as error:
        st.error(f"The physical-study evidence could not be verified: {error}")
        st.link_button("Return to the opening painting", link(evidence.OPENING))
        return
    css = (ASSETS / "physical_damage.css").read_text(encoding="utf-8")
    revision = room_html(f"<style>{css}</style>" + markup(data, navigation, shell, plaque))
    data["links"] = {p or "close": link(case,p) for p in evidence.PANELS}
    data["labels"] = evidence.LABELS
    serialized = json.dumps(data, ensure_ascii=True, allow_nan=False).replace("</", "<\\/")
    controller = (ASSETS / "physical_damage_controller.js").read_text(encoding="utf-8")
    room_controller(controller.replace("__PHYSICAL_DATA__", serialized), revision)


def supplementary_entry(portrait_uri, population):
    """Only the approved Study Design alcove changes; both child routes remain."""
    index = evidence.registry()
    image = evidence.media(f"{evidence.D03}/images/inputs/rd004.png", index)
    alcove = evidence.static_media("streamlit_assets/rooms/study_design_supplementary_alcove.png")
    css = (ASSETS / "physical_damage_entry.css").read_text(encoding="utf-8")
    entry = f'''<img class="pd-study-alcove-surface" src="{esc(alcove)}" alt="" aria-hidden="true">
    <aside class="portrait-audit pd-study-entry" aria-label="Supplementary studies">
      <h3>Supplementary<br>studies</h3>
      <a class="pd-study-tile pd-study-portrait" href="?room=focused_portrait_review&amp;return_room=study_design" target="_self" aria-label="Open the focused portrait review for Juan de Pareja">
        <img src="{esc(portrait_uri)}" alt="Juan de Pareja portrait"><span class="pd-study-caption"><strong>Portrait audit</strong></span></a>
      <a class="pd-study-tile pd-study-physical" href="?room=physical_damage_study" target="_self">
        <img src="{esc(image)}" alt="Physically damaged garden fresco"><span class="pd-study-caption"><strong>Physical damage</strong></span></a>
    </aside>'''
    # The parent uses st.markdown: indentation must not create a code block.
    return f"<style>{css}</style>" + "".join(line.strip() for line in entry.splitlines())
