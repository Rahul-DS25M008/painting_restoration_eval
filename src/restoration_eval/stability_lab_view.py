"""Isolated, evidence-bound antique laboratory presentation."""
import base64
import html
import json
import re

import streamlit as st
import streamlit.components.v1 as components

from .stability_lab import ROOT, MAIN_MODELS, LABELS, SD, TESTS, FAMILIES, CONDITIONS, EVIDENCE, payload, image_uri


def esc(value):
    return html.escape(str(value), quote=True)


def rect(x, y, w, h):
    return f"left:{x / 16.72:.5f}%;top:{y / 9.41:.5f}%;width:{w / 16.72:.5f}%;height:{h / 9.41:.5f}%"


def options(values, current):
    return "".join(f'<option value="{esc(key)}" {"selected" if key == current else ""}>{esc(label)}</option>' for key, label in values.items())


def painting_note(data):
    """Selection-specific prose; never extend the opening example's claim."""
    if data["test"] == "size":
        if (data["painting"], data["model"], data["evidence"]) == ("p018", "lama", "spatial_masked_error"):
            return "Steepest observed LaMa trajectory for this measure—not a universal threshold."
        return "Seven recorded sizes for this painting and method—not a universal damage threshold."
    if data["test"] == "mask":
        return "Five placements on this painting. Keep the family and target area paired."
    if data["test"] == "degradation":
        return FAMILIES[data["family"]] + " on this painting. Procedural RGB stress, not physical ageing."
    return "Four seeds for this painting and prompt. Disagreement is not calibrated confidence."


def book_spines():
    """Decorative foil lettering registered to the two photographed book stacks."""
    books = (
        ("Dune", 19, 631, 139, 22, ".72", "#d7b979", "M2 16Q8 7 14 14T26 14M2 20Q12 12 26 19M18 4a3 3 0 1 0 0 .1"),
        ("Dune Messiah", 19, 602, 139, 22, ".57", "#b69a63", "M14 3L22 12 14 21 6 12ZM14 7V17M9 12H19"),
        ("Children of Dune", 19, 574, 138, 22, ".53", "#bda273", "M10 5a4 4 0 1 0 0 .1M19 9a3 3 0 1 0 0 .1M3 21Q14 12 25 21"),
        ("God Emperor of Dune", 18, 546, 137, 22, ".47", "#c7a06b", "M4 9L8 17H21L25 9 19 12 14 4 9 12ZM8 21H21"),
        ("ChapterHouse Dune", 9, 758, 119, 24, ".46", "#b7a16a", "M4 21V11L14 3 24 11V21ZM10 21V14H18V21"),
        ("Hunters of Dune", 9, 727, 119, 24, ".49", "#c2a175", "M5 22L23 4M13 4H23V14M5 15V22H12"),
        ("Sandworms of Dune", 9, 697, 119, 24, ".46", "#b5a380", "M3 19C20 25 5 5 20 6M20 6C28 5 28 16 20 15C14 15 14 6 20 6ZM20 9V12"),
    )
    result = []
    for title, x, y, w, h, size, ink, path in books:
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 28 26" fill="none" stroke="{ink}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="{path}"/></svg>'
        icon = base64.b64encode(svg.encode()).decode()
        result.append(f'<div class="lab-book-spine" style="{rect(x,y,w,h)};--book-size:{size}cqw;--book-ink:{ink}"><img src="data:image/svg+xml;base64,{icon}" alt="" aria-hidden="true"><span>{esc(title)}</span></div>')
    return "".join(result)


def render_stability_lab(package, navigation):
    try:
        data = payload(dict(st.query_params))
    except (ValueError, FileNotFoundError, KeyError) as error:
        st.error(f"Stability Lab cannot show this evidence: {error}")
        st.link_button("Return to the declared opening case", "?room=stability_lab")
        return
    css = (ROOT / "streamlit_assets/stability_lab.css").read_text(encoding="utf-8")
    shell = image_uri(str(ROOT / "streamlit_assets/rooms/stability_lab_shell.png"))
    current = data["current"]
    painting_lookup = {r["painting_id"]: r for r in package.painting_lookup.to_dict("records")}
    painting_labels = {pid: pid + " · " + str(painting_lookup.get(pid, {}).get("title") or painting_lookup.get(pid, {}).get("category") or "Painting").replace("_", " ") for pid in data["paintings"]}
    data["painting_label"] = painting_labels[data["painting"]]
    buttons = ""
    # Each face/lamp is registered to the photographed brass instrument rather
    # than a uniform grid. Live opaque faces cover the shell's fixed 20% glow.
    rail = ((95,417,32,25,110,402),(137,415,32,25,150,400),
            (176,413,31,25,189,397),(213,411,31,25,226,394),
            (249,409,30,25,263,392),(284,405,30,26,300,390),
            (320,402,32,25,336,389))
    for size, (x,y,w,h,lx,ly) in zip((2,4,6,8,10,15,20),rail):
        active = data["test"] == "size" and current["label"] == f"{size}%"
        lamp_style = f'left:{(lx-x)/w*100:.3f}%;top:{(ly-y)/h*100:.3f}%'
        buttons += f'<button class="lab-size-stop" style="{rect(x,y,w,h)}" data-size="{size}" aria-label="Damage size {size}%" aria-pressed="{str(active).lower()}"><span class="lab-size-lamp" style="{lamp_style}" aria-hidden="true"></span><span class="lab-size-face">{size}%</span></button>'
    wheels = ""
    for i, (x, y) in enumerate(((1318,303), (1268,346), (1362,345), (1282,399), (1342,399)), 1):
        wheels += f'<button class="lab-mask-stop" style="{rect(x,y,43,43)}" data-variant="{i}" aria-label="Mask placement variant {i}"></button>'
    jars = ""
    jar_lines = {
        "dirt_dust": "Dirt /<br>dust",
        "partial_transparency": "Partial<br>transparency",
        "water_stain": "Water<br>stain",
        "water_stain_dirt": "Water stain<br>+ dirt",
    }
    for i, (family, label) in enumerate(FAMILIES.items()):
        jars += f'<button class="lab-jar" style="{rect(843+51*i,544,43,76)}" data-family="{family}" aria-label="Degradation: {esc(label)}"><span class="lab-jar-specimen specimen-{i}"></span><span class="lab-jar-label">{jar_lines[family]}</span></button>'
    jars += f'<button class="lab-jar lab-not-inpainting" style="{rect(1047,544,43,76)}" data-action="excluded" aria-label="Not an inpainting task"><span class="lab-jar-specimen specimen-4"></span><span>Other<br>effects</span></button>'
    ledger = ""
    for i, (key, label) in enumerate(TESTS.items()):
        ledger += f'<button class="lab-ledger-drawer" style="{rect(1461,289+67*i,141,49)}" data-ledger="{key}" aria-label="Open {esc(label)} ledger" aria-pressed="{str(key == data["test"]).lower()}"><span>0{i+1}</span><strong>{esc(label)}</strong></button>'
    seed_html = ""
    seed = data["seed"]
    if seed:
        for i, member in enumerate(seed["members"]):
            seed_html += f'<button class="lab-seed" style="{rect(548+44*i,546,38,53)}" data-seed="{i}" aria-label="Inspect seed {member["seed"]}"><span class="lab-mini-image"><img src="{member["uri"]}" alt="Seed {member["seed"]}"></span><small>{member["seed"]}</small></button>'
        seed_html += f'<button class="lab-seed-note" style="{rect(728,548,55,53)}" data-action="seeds"><span>Seed record</span><span>Inspect →</span></button>'
    else:
        for i in range(4):
            seed_html += f'<div class="lab-seed lab-seed-empty" style="{rect(548+44*i,546,38,53)}"><span>—</span><small>{2026+i}</small></div>'
        seed_html += f'<button class="lab-seed-note" style="{rect(728,548,55,53)}" data-action="seeds"><span>Why closed?</span><span>Read →</span></button>'
    if data["test"] == "seed":
        context = f'<label>Recorded seed group<select data-selector="group" aria-label="Recorded seed group">{options({g["id"]:g["label"] for g in data["seed_options"]},seed["id"])}</select></label>'
    elif data["test"] == "mask":
        context = f'<label>Fixed condition<select data-selector="condition" aria-label="Mask family and area condition">{options(CONDITIONS,data["condition"])}</select></label>'
    elif data["test"] == "degradation":
        context = f'<label>Recorded severity<select data-selector="case" aria-label="Degradation severity">{options({p["case_id"]:p["label"] for p in data["points"]}, data["selected"])}</select></label>'
    else:
        context = f'<label>Damage size<select data-selector="case" aria-label="Damage-size configuration">{options({p["case_id"]:p["label"] for p in data["points"]}, data["selected"])}</select></label>'
    painting_title = painting_labels[data['painting']].split(' · ',1)[-1]
    scene = f'''<style>{css}</style><main class="stability-stage" data-version="{esc(data['version'])}" style="background-image:url('{shell}')">
{navigation}
<header class="lab-heading" style="{rect(508,77,608,106)}"><h1>Stability Lab</h1><h2>How does restoration change across tests?</h2><p>Less change here does not mean historically correct.</p></header>
{book_spines()}
<button class="lab-chart-board" style="{rect(53,112,253,172)}" data-action="chart" aria-label="Inspect recorded stability chart"><strong>{esc(TESTS[data['test']])}</strong><span class="lab-chart"></span><small>{esc('Seed-pair RGB MAE · masked region' if data['test']=='seed' else EVIDENCE[data['evidence']]['label'])}</small></button>
<aside class="lab-note-board" style="{rect(337,119,139,168)}"><span class="lab-kicker">{esc(data['painting'])} · {esc(LABELS[data['model']])}</span><strong title="{esc(painting_title)}">{esc(painting_title)}</strong><div class="lab-note-configuration">{context}</div><p>{esc(painting_note(data))}</p><button data-action="chart">Read this record →</button></aside>
<div class="lab-main-caption lab-plaque" style="{rect(700,214,231,26)}">{esc(data['painting'])} · {esc(LABELS[data['model']])}<small>{esc(TESTS[data['test']])} · {esc(current['label'])}</small></div>
<div class="lab-plaque" style="{rect(580,260,166,24)}">Controlled input<small>Same recorded case</small></div>
<div class="lab-plaque" style="{rect(880,260,160,24)}">{esc(LABELS[data['model']])}<small>Recorded restoration</small></div>
<button class="lab-main-image" style="{rect(555,301,225,146)}" data-action="input" aria-label="Inspect controlled input"><img src="{current['damaged']}" alt="Controlled damaged input for {esc(current['case_id'])}"></button>
<button class="lab-main-image" style="{rect(837,301,235,146)}" data-action="restored" aria-label="Inspect recorded restoration"><img src="{current['restored']}" alt="Recorded {esc(LABELS[data['model']])} restoration"></button>
<div class="lab-damage-title lab-plaque" style="{rect(174,316,127,23)}">Damage Size</div>{buttons}
<div class="lab-context lab-plaque" style="{rect(144,450,159,28)}">Percentage of painting area masked</div>
<div class="lab-plaque lab-wheel-heading" style="{rect(1269,246,139,28)}">Mask placement</div>{wheels}
<button class="lab-plaque lab-wheel-note" style="{rect(1271,468,137,33)}" data-action="mask-condition"><span>Family + area</span><small>{esc(CONDITIONS[data['condition']])} ▾</small></button>
<div class="lab-seed-heading lab-plaque" style="{rect(560,503,220,23)}">Repeated Seeds - SD only</div>{seed_html}
<div class="lab-degradation-heading lab-plaque" style="{rect(886,501,159,23)}">Degradation stress</div>{jars}
<div class="lab-ledger-title lab-plaque" style="{rect(1466,235,140,29)}">Test ledger</div>{ledger}
<button class="lab-boundaries-drawer" style="{rect(1450,613,184,76)}" data-action="scope" aria-label="Test Boundaries"><span class="lab-boundaries-face" style="background-image:url('{shell}')" aria-hidden="true"></span><strong>Test Boundaries</strong></button>
<div class="lab-desk-control lab-desk-painting" style="{rect(172,688,68,87)}"><label><span class="lab-desk-title">Painting</span><span class="lab-desk-value">{esc(data['painting'])}</span><select data-selector="painting" aria-label="Painting" title="{esc(data['painting_label'])}">{options(painting_labels,data['painting'])}</select></label><span class="lab-desk-thumbnail" aria-hidden="true"><img src="{data['reference']}" alt=""></span></div>
<div class="lab-desk-control lab-desk-method" style="{rect(279,688,73,87)}"><label><span class="lab-desk-title">Method</span><span class="lab-desk-value {'lab-desk-value-long' if data['model']==SD else ''}">{esc(LABELS[data['model']])}</span><select data-selector="model" aria-label="Restoration method">{options({m:LABELS[m] for m in MAIN_MODELS},data['model'])}</select></label><span class="lab-desk-mask" aria-hidden="true"><img src="{current['mask']}" alt=""></span></div>
<div class="lab-desk-control lab-desk-evidence" style="{rect(388,688,78,87)}"><label><span class="lab-desk-title">Evidence</span><span class="lab-desk-value lab-desk-value-long">{esc('Seed-pair RGB MAE' if data['test']=='seed' else EVIDENCE[data['evidence']]['label'])}</span><select data-selector="evidence" aria-label="Evidence measure" {'disabled' if data['test']=='seed' else ''}>{options({k:v['label'] for k,v in EVIDENCE.items()},data['evidence'])}</select></label><span class="lab-desk-magnifier" aria-hidden="true"></span></div>
<dialog class="lab-dialog" aria-labelledby="lab-dialog-title"><div class="lab-dialog-top"><div><span>CONSERVATION LABORATORY · EVIDENCE REGISTER</span><h2 id="lab-dialog-title"></h2></div><button data-action="close" aria-label="Close evidence register">Close ×</button></div><div class="lab-dialog-body"></div></dialog>
<div class="lab-live" aria-live="polite"></div></main>'''
    def nav_svg(match):
        svg = match.group(0)
        stroke = "#a6232c" if '0 0 40 40' in svg else "#0085bd"
        svg = svg.replace('<svg ', f'<svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="{stroke}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" ', 1)
        return '<img alt="" src="data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode() + '">'
    from .room_runtime import room_html, room_controller
    revision = room_html(re.sub(r"<svg\b.*?</svg>", nav_svg, scene, flags=re.DOTALL))
    controller = (ROOT / "streamlit_assets/stability_lab_controller.js").read_text(encoding="utf-8")
    serialized = json.dumps(data, ensure_ascii=True, allow_nan=False).replace("</", "<\\/")
    room_controller(controller.replace("__STABILITY_PAYLOAD__", serialized), revision)
