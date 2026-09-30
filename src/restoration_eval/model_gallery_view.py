"""Isolated Model Gallery presentation. Does not modify scientific artifacts."""
import base64
import html
import json
import re

import streamlit as st
import streamlit.components.v1 as components

from .model_gallery import ROOT, MAIN_MODELS, LABELS, catalogue, case_label, selected_case, case_payload, image_uri, project_path

FAMILIES = ("Classical · deterministic", "Learned · deterministic", "Mask-aware transformer · deterministic", "Prompted · stochastic")
QUADS = (
    [[166,333],[345,349],[345,488],[165,489]],
    [[479,355],[650,359],[650,488],[479,488]],
    [[1023,361],[1195,358],[1195,488],[1023,489]],
    [[1338,351],[1522,339],[1522,488],[1338,489]],
)


def escaped(value):
    return html.escape(str(value), quote=True)


def picture(uri, quad, label, attributes=""):
    return f'<button class="gallery-projected" data-quad="{escaped(json.dumps(quad))}" aria-label="{escaped(label)}" {attributes}><img src="{uri}" alt="{escaped(label)}" draggable="false"></button>'


def stone_engraving(kind):
    """Original vector fan-art ornaments; separate from all scientific imagery."""
    drawings = {
        "arrakis": ("0 0 80 140", "Arrakis: two moons, dunes and a sandworm engraving", '''
<circle cx="25" cy="23" r="11"/><circle cx="56" cy="15" r="5"/>
<path d="M8 55Q35 33 73 54M8 62Q48 45 73 61M8 101Q29 81 73 95M8 111Q45 91 73 106"/>
<path d="M24 96C49 77 13 67 33 51C55 37 66 60 49 67C39 71 35 64 39 59"/>
<ellipse cx="43" cy="56" rx="12" ry="10"/>
<path d="M34 50L40 54M39 47L42 53M46 47L45 53M52 51L47 55M52 58L47 57M46 65L44 59M36 63L40 58M31 56L38 56M32 74L42 72M34 80L45 77M30 87L43 84"/>
<text x="40" y="130" text-anchor="middle" font-size="10" letter-spacing="2">ARRAKIS</text>'''),
        "zhongli": ("0 0 80 130", "Zhongli-inspired amber stone and geometric Geo seal", '''
<path d="M40 9L64 34L40 59L16 34ZM40 18L55 34L40 50L25 34Z"/>
<path d="M40 2V18M40 50V68M9 34H25M55 34H71M26 20L40 34L54 20M26 48L40 34L54 48"/>
<path d="M13 99V76L23 70L32 77V99M35 99V69L45 63L55 70V99M58 99V82L66 76L73 82V99M7 104H75M23 70V96M45 63V96M66 76V96"/>
<text x="40" y="119" text-anchor="middle" font-size="9" letter-spacing="1.4">ZHONGLI</text>'''),
        "dune_seal": ("0 0 120 78", "Dune desert archive seal", '''
<path d="M6 8H114M6 70H114M10 12V66M110 12V66"/>
<circle cx="35" cy="28" r="9"/><circle cx="84" cy="23" r="4"/>
<path d="M17 42Q46 28 65 40T103 38M17 47Q66 34 103 45"/>
<text x="60" y="61" text-anchor="middle" font-size="14" letter-spacing="5">DUNE</text>'''),
        "morax_seal": ("0 0 80 98", "Morax memory in stone seal", '''
<path d="M40 6L66 33L40 60L14 33ZM40 15L57 33L40 50L23 33ZM40 15V50M23 33H57"/>
<path d="M8 66H72M8 92H72"/>
<text x="40" y="79" text-anchor="middle" font-size="11" letter-spacing="2">MORAX</text>
<text x="40" y="88" text-anchor="middle" font-size="5.5" letter-spacing=".5">MEMORY IN STONE</text>'''),
    }
    viewbox, label, drawing = drawings[kind]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" fill="none" stroke="#604529" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><style>text{{fill:#604529;stroke:none;font-family:Georgia,serif;font-weight:600}}</style>{drawing}</svg>'''
    uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    return f'<img class="gallery-stone-engraving" src="{uri}" alt="{label}" draggable="false">'


def render_model_gallery(package, navigation):
    try:
        cat = catalogue()
        painting = st.query_params.get("gallery_painting", "p018")
        case = selected_case(painting, st.query_params.get("gallery_case"))
        payload = case_payload(case)
    except (ValueError, FileNotFoundError) as error:
        st.error(f"Model Gallery could not load the requested evidence: {error}")
        st.link_button("Return to the declared opening case", "?room=model_gallery")
        return
    model = st.query_params.get("gallery_model", "lama")
    payload["initial_model"] = model if model in MAIN_MODELS else "lama"
    payload["initial_evidence"] = st.query_params.get("gallery_evidence", "crop_ssim")
    painting_rows = package.painting_lookup.to_dict("records")
    lookup = {r["painting_id"]: r for r in painting_rows}
    def painting_label(pid):
        row = lookup.get(pid, {})
        title = row.get("title") or row.get("category") or "Painting"
        return f"{pid} · {str(title).replace('_', ' ')}"
    def options(values, current, label):
        return "".join(f'<option value="{escaped(v)}" {"selected" if v == current else ""}>{escaped(label(v))}</option>' for v in values)
    painting_options = options(sorted(cat["paintings"]), painting, painting_label)
    case_options = options(cat["paintings"][painting], case, case_label)
    payload["painting_label"] = painting_label(painting)
    payload["version"] = f"gallery-v1:{case}"
    shell = image_uri(str(ROOT / "streamlit_assets/rooms/model_gallery_shell.png"))
    css = (ROOT / "streamlit_assets/model_gallery.css").read_text(encoding="utf-8")
    alcoves = ""
    for i, method in enumerate(MAIN_MODELS):
        candidate = payload["models"][method]
        alcoves += f'<button class="gallery-method-title method-{i}" data-model="{method}" aria-label="Select {LABELS[method]}"><strong>{LABELS[method]}</strong><span>{FAMILIES[i]}</span></button>'
        alcoves += picture(candidate["uri"], QUADS[i], f'Select {LABELS[method]} restoration', f'data-model="{method}"')
    center = picture(payload["damaged"], [[707,340],[958,340],[958,508],[707,508]], "Inspect shared damaged input", 'data-action="damaged"')
    table = picture(payload["models"][payload["initial_model"]]["uri"], [[540,618],[751,615],[743,726],[512,726]], "Inspect selected restoration", 'data-action="inspect" data-table-image="true"')
    sdxl = payload["models"].get("sdxl_inpainting")
    vitrine = picture(sdxl["uri"], [[1381,584],[1544,606],[1522,676],[1330,654]], "Inspect bounded SDXL result", 'data-action="sdxl"') if sdxl else '<div class="gallery-vitrine-closed">No result for this case<br><small>Bounded study only</small></div>'
    scene = f'''<style>{css}</style><main class="model-stage" data-case-id="{escaped(case)}" style="background-image:url('{shell}')">
{navigation}<header class="gallery-heading"><h1>Model Gallery</h1><h2>How do different restoration methods rebuild the same loss?</h2><p>A convincing completion is a candidate to inspect—not recovered historical truth.</p></header>
{alcoves}{center}{table}{vitrine}
<div class="gallery-case-caption">Shared starting point · {escaped(painting)} · {escaped(case_label(case))}</div>
<aside class="gallery-model-plaque"><h3 data-model-name>LaMa</h3><p data-model-coverage></p><p data-model-runtime></p><p data-model-strength></p><p data-model-caution></p><button data-action="record">Open full model record →</button><small>Runtime reflects the recorded workstation.</small></aside>
<button class="gallery-hint-book" data-action="hint">Why was<br>HINT selected?<span>Open the decision study</span></button>
<div class="gallery-painting-drawer gallery-drawer"><img src="{payload['reference']}" alt=""><label for="gallery-painting">Change painting</label><select id="gallery-painting" aria-label="Change painting">{painting_options}</select></div>
<div class="gallery-case-drawer gallery-drawer"><img src="{payload['mask']}" alt=""><label for="gallery-case">Change damage</label><select id="gallery-case" aria-label="Change damage">{case_options}</select></div>
<div class="gallery-evidence-drawer gallery-drawer"><span class="gallery-magnifier" aria-hidden="true">⌕</span><label for="gallery-evidence">Evidence</label><select id="gallery-evidence" aria-label="Evidence"></select></div>
<button class="gallery-evidence-readout" data-action="inspect" aria-label="Inspect recorded evidence"><span data-evidence-readout></span><small data-evidence-note></small></button>
<div class="gallery-sdxl-plaque">SDXL · Bounded study<br><span>24 completed / 35 scheduled</span><br><small>Not included in the full ranking</small></div>
<button class="gallery-sdxl-drawer" data-action="sdxl">{('Available · Open bounded view →' if sdxl else 'Unavailable · See study coverage →')}</button>
<div class="gallery-left-inscription">{stone_engraving('arrakis')}</div><div class="gallery-right-inscription">{stone_engraving('zhongli')}</div>
<div class="gallery-left-plinth">{stone_engraving('dune_seal')}</div><div class="gallery-right-plinth">{stone_engraving('morax_seal')}</div>
<footer class="gallery-conclusion">LaMa led 10 of 11 separate quality anchors · Telea led crop SSIM<span>Overall registered comparison · separate comparisons · no combined score</span><small>300 paintings · 2,620 cases; most anchors use 2,320 non-zero cases, structural affinity uses 2,620.</small></footer>
<p class="gallery-live" role="status" aria-live="polite"></p>
<dialog class="gallery-dialog" aria-labelledby="gallery-dialog-title"><div class="gallery-dialog-top"><h2 id="gallery-dialog-title"></h2><button data-close aria-label="Close inspection">×</button></div><div class="gallery-dialog-body"></div></dialog>
</main>'''
    def svg_image(match):
        svg = match.group(0)
        stroke = "#a6232c" if '0 0 40 40' in svg else "#0085bd"
        svg = svg.replace('<svg ', f'<svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="{stroke}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" ', 1)
        return '<img alt="" src="data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode() + '">'
    st.html(re.sub(r"<svg\b.*?</svg>", svg_image, scene, flags=re.DOTALL))
    controller = (ROOT / "streamlit_assets/model_gallery_controller.js").read_text(encoding="utf-8")
    serialized = json.dumps(payload, ensure_ascii=True, allow_nan=False).replace("</", "<\\/")
    components.html("<script>" + controller.replace("__GALLERY_PAYLOAD__", serialized) + "</script>", height=0, scrolling=False)
    document = st.query_params.get("gallery_document")
    if document in cat["reports"] or document == "hint_decision":
        def dismiss_document():
            if "gallery_document" in st.query_params:
                del st.query_params["gallery_document"]
        @st.dialog("Source report", width="large", on_dismiss=dismiss_document)
        def show_report():
            import hashlib
            if document == "hint_decision":
                path = ROOT / "outputs/37_hint_mat_method_selection/reports/method_selection_report.html"
            else:
                record = cat["reports"][document]
                path = project_path(record["report_path"])
                if hashlib.sha256(path.read_bytes()).hexdigest() != record["report_sha256"]:
                    st.error("Source report checksum mismatch; download withheld.")
                    return
            st.write("Download the original, self-contained HTML report. It includes the full recorded evidence and can be opened in your browser. No analysis is recomputed here.")
            st.download_button("Download original HTML report", path.read_bytes(), file_name=path.name, mime="text/html")
            if st.button("Return to gallery"):
                dismiss_document()
                st.rerun()
        show_report()
