"""Render complete user-pasted N35 cells 0-11; never modify/execute a notebook."""
from pathlib import Path
import ast
import hashlib
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / 'notebooks/35_dashboard_and_deployment_validation.ipynb'
DEST = ROOT / '.codex_tmp/n35_batches_1_2'


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Expected one replacement anchor: ' + old[:90])
    return source.replace(old, new, 1)


INTRO = '''# 35 — Controlled-300 Dashboard and Deployment Validation

**Presentation:** All eight principal rooms, the Focused Portrait Review, and the museum passport/free-exploration experience are user-approved. This is not deployment certification.
**Controlled-300 validation:** In progress. **N35 completion gate: No.**
**Input:** the immutable `dashboard_package.v2` N34 release.
**Outputs:** four canonical files, written only by the final consolidation batch.

The app presents existing evidence; it performs no restoration inference or scientific recomputation. The approved layouts and artwork remain frozen. These replacement cells reconcile validation with the completed application, not rebuild its rooms.

The ten-batch plan remains: (1) contract/preflight, (2) Foyer/shared shell, (3) Study Design, (4) Metric Framework, (5) Model Gallery, (6) Stability Lab, (7) Trustworthiness/D02, (8) Case Explorer, (9) Research Archive, (10) integration/deployment/readiness/persistence.

## Execution boundary

Replace the first 12 cells with this pack, preserving their Markdown/code types. Restart the kernel and run in order, stopping at the end of Batch 2. Do not use Run All: later cells/results still include historical pilot logic and will be reconciled separately. Historical “N35 complete” output is not a current result. Preserve the old notebook in Git history and clear stale saved outputs in your working notebook before this rerun.

Batch 1 checks the existing project inventory's freshness. After saving your replacement cells, refresh the inventory from the project root with `.\\.venv\\Scripts\\python.exe tools/build_project_inventory.py --root .` before running Batch 1. This is a separate user-run inventory operation, not scientific recomputation. Do not bypass inventory errors or change failed checks to pass.

Installed-version mismatches remain explicit warnings at this local gate. Missing packages or inconsistent requirements/config pins remain blocking. Deployment alignment, browser behavior, resource budgets, and remote asset availability are not certified by this pack.

Canonical outputs: `validation/dashboard_checks.csv`, `reports/deployment_readiness.md`, `manifests/run_manifest.json`, and `manifests/artifacts.csv`, all under `outputs/35_dashboard_and_deployment_validation/`.
'''

BATCH1 = '''## Batch 1 — Controlled-300 contract and runtime trust-boundary preflight

Validate the exact N34 release, package checksums, population, room order, schemas, indexed paths, governance records, source syntax, and focused helper tests. Network access is blocked during the package-read audit. This is a local preflight, not a clean deployment simulation.

The approved population is 300 paintings, 3,425 registered cases, 2,620 four-model-eligible cases, 10,480 primary four-model candidates, 13,879 indexed candidates, 24 bounded-SDXL candidates, 1,025 repeated-seed groups, and 337 indexed reports. Values are checked against the versioned contract, not rewritten.

The default deterministic LaMa candidate must never borrow another candidate's uncertainty evidence. Room-routing prose is not a numerical table. Existing typed opening records are checked here; all-selection deployed numerical parity remains a later integration gate.

These cells may create empty N35 output directories, but must not create canonical N35 files. Stale files block the run; nothing is deleted automatically. Rerunning a validation cell removes its old checks and downstream Batch 1/2 checks so an old success or failure cannot survive unnoticed. Restart from the beginning after any source/config change.
'''

BATCH2 = '''## Batch 2 — Validate the approved shared shell and Exhibition Foyer

The Foyer is already visually approved. This batch checks its current implementation without modifying the application, CSS, artwork, or frozen evidence.

Checks cover the eight-room navigation and seven previews, verified p001 hero, collection counts, pinned decorative shell, keyboard-access declarations, responsive CSS structure, and the real eight-stop/six-minute passport plus free-exploration entry points. Freeze manifests verify the approved app integration and Archive bytes.

The old exact-1050px assertion is replaced by structural checks for the existing Foyer reflow and compact navigation rules. This establishes that responsive rules exist; it does NOT prove viewport rendering, clipping, keyboard usability, Firefox reliability, or zoom/second-monitor behavior. Those browser checks remain pending for Batch 10.

The visitor guide is now a JavaScript overlay injected through a zero-height component. Streamlit AppTest can check its delivered payload, but cannot execute its JavaScript or prove its dialogs work. We therefore check the real transport rather than looking for the removed server-rendered tour card. Same-room navigation uses a dedicated component; unexpected native buttons remain a failure, not an indiscriminate exception.

Server-side Foyer smoke runs below do not start a web server or touch your manually running Streamlit process. They make no permitted network request and write no canonical notebook output. They do not establish cold-cloud startup latency, memory limits, or deployment readiness.
'''

SMOKE = r'''# Server-side smoke only: AppTest does not execute browser JavaScript.
drop_validation_stages(("batch_2_streamlit_smoke", "batch_2_final_gate"))
from streamlit.testing.v1 import AppTest
from contextlib import ExitStack
import time

def foyer_smoke(query):
    started = time.perf_counter()
    requests = []
    def reject_network(*args, **kwargs):
        requests.append("blocked network attempt")
        raise AssertionError("Batch 2 server smoke attempted network access")
    with ExitStack() as stack:
        for target in ("urllib.request.urlopen", "urllib.request.urlretrieve",
                       "socket.create_connection", "socket.socket.connect",
                       "socket.socket.connect_ex"):
            stack.enter_context(mock.patch(target, side_effect=reject_network))
        app = AppTest.from_file(str(APP_PATH), default_timeout=60)
        for key, value in query.items():
            app.query_params[key] = value
        app.run()
    markup = "\n".join(str(element.value) for element in app.markdown)
    # components.html is represented by an iframe proto, not a Markdown card.
    frames = [str(element.proto.srcdoc) for element in app.get("iframe")]
    return {
        "app": app, "markup": markup, "frames": frames,
        "errors": [str(e.value) for e in app.exception],
        "buttons": [b.label for b in app.button],
        "network_attempts": len(requests),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

INITIAL_SMOKE = foyer_smoke({"room": "exhibition_foyer"})
TOUR_SMOKE = foyer_smoke({"room": "exhibition_foyer", "tour": "1"})
INITIAL_APP_TEST, TOUR_APP_TEST = INITIAL_SMOKE["app"], TOUR_SMOKE["app"]
INITIAL_MARKDOWN, TOUR_MARKDOWN = INITIAL_SMOKE["markup"], TOUR_SMOKE["markup"]
INITIAL_EXCEPTIONS, TOUR_EXCEPTIONS = INITIAL_SMOKE["errors"], TOUR_SMOKE["errors"]
INITIAL_BUTTON_LABELS = INITIAL_SMOKE["buttons"]
EXPECTED_PRINCIPAL_LABELS = [APP_ROOM_LABELS[r] for r in PRINCIPAL_ROOM_IDS]
LOCAL_IMAGE_COUNT = INITIAL_MARKDOWN.count('src="data:image/')
ROUTE_PREVIEW_COUNT = INITIAL_MARKDOWN.count('class="route-preview"')
QUESTION_FRAGMENTS = ("How should we", "judge an AI-restored", "painting?")

def visitor_payload(smoke, legacy):
    frames = [f for f in smoke["frames"] if "MuseumVisit.install(window," in f]
    if len(frames) != 1:
        return False
    expected = dict(VISITOR_DATA, room="exhibition_foyer", legacyLaunch=legacy)
    encoded = json.dumps(expected, ensure_ascii=True).replace("</", "<\\/")
    css_encoded = json.dumps(VISITOR_CSS).replace("</", "<\\/")
    return (
        frames[0] == "<script>" + VISITOR_SCRIPT + "\nMuseumVisit.install(window,"
        + encoded + "," + css_encoded + ");</script>"
    )

APP_TEST_CHECKS = (
    ("foyer_startup", "Both Foyer server-side smoke runs have no exception",
     [], INITIAL_EXCEPTIONS + TOUR_EXCEPTIONS,
     not INITIAL_EXCEPTIONS and not TOUR_EXCEPTIONS),
    ("semantic_entry_controls", "Both approved links carry visitor-dialog hooks",
     True, all(s in INITIAL_MARKDOWN for s in (
         "Take the guided tour", "Explore freely", 'data-museum-visit="tour"',
         'data-museum-visit="free"', 'aria-haspopup="dialog"')),
     all(s in INITIAL_MARKDOWN for s in (
         "Take the guided tour", "Explore freely", 'data-museum-visit="tour"',
         'data-museum-visit="free"', 'aria-haspopup="dialog"'))),
    ("foyer_opening_copy", "The approved question, p001 and local evidence render",
     True, all(s in INITIAL_MARKDOWN for s in (*QUESTION_FRAGMENTS, "p001", "data:image/")),
     all(s in INITIAL_MARKDOWN for s in (*QUESTION_FRAGMENTS, "p001", "data:image/"))),
    ("principal_navigation", "All eight approved principal labels render",
     EXPECTED_PRINCIPAL_LABELS,
     [s for s in EXPECTED_PRINCIPAL_LABELS if s in INITIAL_MARKDOWN],
     all(s in INITIAL_MARKDOWN for s in EXPECTED_PRINCIPAL_LABELS)),
    ("route_preview_content", "Seven destination previews render", 7,
     ROUTE_PREVIEW_COUNT, ROUTE_PREVIEW_COUNT == 7),
    ("local_verified_images", "Shell, hero and seven previews use local data images",
     9, LOCAL_IMAGE_COUNT, LOCAL_IMAGE_COUNT == 9),
    ("scientific_boundary", "Trustworthiness, historical and category limits render",
     True, all(s in INITIAL_MARKDOWN for s in (
         FOYER_OPENING["boundary"], "historically correct", "not historical styles")),
     all(s in INITIAL_MARKDOWN for s in (
         FOYER_OPENING["boundary"], "historically correct", "not historical styles"))),
    ("zigzag_route_runtime", "The approved SVG route is delivered",
     True, 'class="route-line"' in INITIAL_MARKDOWN and "<polyline" in INITIAL_MARKDOWN,
     'class="route-line"' in INITIAL_MARKDOWN and "<polyline" in INITIAL_MARKDOWN),
    ("visitor_default_payload", "Default entry delivers the exact inactive visitor payload",
     True, visitor_payload(INITIAL_SMOKE, False), visitor_payload(INITIAL_SMOKE, False)),
    ("visitor_legacy_payload", "Legacy tour query delivers the exact launch payload",
     True, visitor_payload(TOUR_SMOKE, True), visitor_payload(TOUR_SMOKE, True)),
    ("no_stray_native_buttons", "The Foyer has no unexpected native Streamlit buttons",
     [], INITIAL_BUTTON_LABELS + TOUR_SMOKE["buttons"],
     not INITIAL_BUTTON_LABELS and not TOUR_SMOKE["buttons"]),
    ("server_network_attempts", "The guarded smoke makes zero network attempts",
     0, INITIAL_SMOKE["network_attempts"] + TOUR_SMOKE["network_attempts"],
     INITIAL_SMOKE["network_attempts"] + TOUR_SMOKE["network_attempts"] == 0),
)
APP_TEST_STAGE_RECORDS = [application_source_check(*r) for r in APP_TEST_CHECKS]
replace_validation_stage("batch_2_streamlit_smoke", APP_TEST_STAGE_RECORDS)
APP_TEST_RESULTS = pd.DataFrame(APP_TEST_STAGE_RECORDS)
display(APP_TEST_RESULTS)
VALIDATION.raise_for_blocking()
print("Batch 2 server-side Foyer smoke passed; browser execution is NOT tested here.")
print("Observed run seconds (not a cold-cloud/p95 benchmark):",
      INITIAL_SMOKE["elapsed_seconds"], TOUR_SMOKE["elapsed_seconds"])
'''

SOURCE_EXTRA = r'''
# Reconcile the completed visitor overlay without modifying frozen source files.
VISITOR_ROOT = PROJECT_ROOT / "streamlit_assets/museum_visit"
VISITOR_DATA = json.loads((VISITOR_ROOT / "tour.json").read_text(encoding="utf-8"))
VISITOR_SCRIPT = (VISITOR_ROOT / "controller.js").read_text(encoding="utf-8")
VISITOR_CSS = (VISITOR_ROOT / "visit.css").read_text(encoding="utf-8")
VISITOR_ROOMS = [s["room"] for s in VISITOR_DATA["stops"]]
FREEZE_AUDIT_RECORDS = []
for manifest_name in ("research_archive_freeze.json", "museum_visit_freeze.json"):
    manifest = json.loads((PROJECT_ROOT / "config/publication" / manifest_name).read_text(encoding="utf-8"))
    if not manifest["files"] or manifest["status"] != "user_approved_visual_freeze":
        raise ValueError("Missing user-approved freeze records: " + manifest_name)
    for item in manifest["files"]:
        path = (PROJECT_ROOT / item["path"]).resolve()
        safe = path.is_relative_to(PROJECT_ROOT)
        raw = path.read_bytes() if safe and path.is_file() else None
        if raw is not None and item["hash_mode"] == "lf_normalized":
            raw = raw.replace(b"\r\n", b"\n")
        observed = hashlib.sha256(raw).hexdigest() if raw is not None else "missing_or_unsafe"
        FREEZE_AUDIT_RECORDS.append({"manifest": manifest_name, "path": item["path"],
            "expected": item["sha256"], "observed": observed, "passed": observed == item["sha256"]})
FREEZE_AUDIT = pd.DataFrame(FREEZE_AUDIT_RECORDS)

VISITOR_SOURCE_CHECKS = (
    ("approved_freeze_bytes", "All approved Archive and visitor release files retain their hashes",
     0, int((~FREEZE_AUDIT["passed"]).sum()), bool(FREEZE_AUDIT["passed"].all())),
    ("visitor_room_order", "The actual visitor asset follows all eight principal rooms",
     list(PRINCIPAL_ROOM_IDS), VISITOR_ROOMS, VISITOR_ROOMS == list(PRINCIPAL_ROOM_IDS)),
    ("visitor_duration", "The suggested visit totals six minutes",
     360, sum(s["seconds"] for s in VISITOR_DATA["stops"]),
     sum(s["seconds"] for s in VISITOR_DATA["stops"]) == 360),
    ("visitor_detour", "Portrait review is optional and outside the eight stamps",
     CHILD_ROOM_ID, VISITOR_DATA["detour"]["room"],
     VISITOR_DATA["detour"]["room"] == CHILD_ROOM_ID and CHILD_ROOM_ID not in VISITOR_ROOMS),
    ("visitor_invitation_routes", "Four free-exploration invitations use known rooms",
     True, len(VISITOR_DATA["invitations"]) == 4 and all(i["room"] in VISITOR_ROOMS for i in VISITOR_DATA["invitations"]),
     len(VISITOR_DATA["invitations"]) == 4 and all(i["room"] in VISITOR_ROOMS for i in VISITOR_DATA["invitations"])),
    ("visitor_overlay_wiring", "The approved dialog hooks and renderer remain connected",
     True, all(s in APP_SOURCE for s in ('data-museum-visit="tour"', 'data-museum-visit="free"', 'render_museum_visit(room_id,')),
     all(s in APP_SOURCE for s in ('data-museum-visit="tour"', 'data-museum-visit="free"', 'render_museum_visit(room_id,'))),
    ("visitor_source_boundaries", "No automatic timer or persistent localStorage is declared",
     False, bool(re.search(r"\b(?:setTimeout|setInterval|localStorage)\b", VISITOR_SCRIPT)),
     not bool(re.search(r"\b(?:setTimeout|setInterval|localStorage)\b", VISITOR_SCRIPT))),
)
SOURCE_STAGE_RECORDS.extend(application_source_check(*r) for r in VISITOR_SOURCE_CHECKS)
display(FREEZE_AUDIT.loc[~FREEZE_AUDIT["passed"]] if not FREEZE_AUDIT["passed"].all()
        else FREEZE_AUDIT.groupby("manifest").agg(files=("path", "size"), passed=("passed", "sum")))
'''

RESPONSIVE = r'''# Inspect actual Foyer reflow rules; do not demand an obsolete exact breakpoint.
# This is source evidence only. Browser viewport rendering is a Batch 10 gate.
def css_media_blocks(source):
    blocks = []
    for match in re.finditer(r"@media\s*\(\s*max-width\s*:\s*(\d+)px\s*\)\s*\{", source):
        depth, end = 1, match.end()
        while end < len(source) and depth:
            depth += (source[end] == "{") - (source[end] == "}")
            end += 1
        if depth:
            raise ValueError("Unbalanced responsive CSS rule")
        blocks.append((int(match.group(1)), source[match.end():end - 1]))
    return blocks

RESPONSIVE_BLOCKS = css_media_blocks(APP_SOURCE)
FOYER_REFLOW_BLOCKS = [width for width, body in RESPONSIVE_BLOCKS
    if 640 < width <= 1100 and all(s in body for s in
        (".foyer-stage", ".foyer-actions", "position: relative", "height: auto"))]
COMPACT_NAV_BLOCKS = [width for width, body in RESPONSIVE_BLOCKS
    if width <= 640 and ".museum-nav" in body]
RESPONSIVE_LAYOUT_PRESENT = bool(FOYER_REFLOW_BLOCKS and COMPACT_NAV_BLOCKS)
print("Declared Foyer reflow widths:", FOYER_REFLOW_BLOCKS,
      "compact navigation widths:", COMPACT_NAV_BLOCKS)
'''


def build_cells(notebook):
    cells = [{"cell_type": c["cell_type"], "source": ''.join(c["source"])}
             for c in notebook['cells'][:12]]
    if len(cells) != 12 or cells[7]['cell_type'] != 'markdown':
        raise ValueError('Unexpected N35 cell layout')
    if 'Batch 2 local source/binding/server-smoke gate passed.' in cells[11]['source']:
        # The user may already have pasted this pack. Do not append another
        # harness or try to replace obsolete anchors a second time.
        return cells
    cells[0]['source'], cells[1]['source'], cells[7]['source'] = INTRO, BATCH1, BATCH2
    cells[2]['source'] += '''

# Only validation state is reset; no scientific or application file is changed.
import hashlib
import re

def drop_validation_stages(prefixes):
    global VALIDATION
    refreshed = ValidationCollector()
    refreshed.extend(c for c in VALIDATION.checks
                     if not c.validation_stage.startswith(tuple(prefixes)))
    VALIDATION = refreshed
'''
    prefixes = {
        3: ('batch_1_', 'batch_2_'),
        4: ('batch_1_package', 'batch_1_indexed', 'batch_1_runtime', 'batch_1_governance', 'batch_1_dependency', 'batch_1_completion', 'batch_2_'),
        5: ('batch_1_governance', 'batch_1_dependency', 'batch_1_completion', 'batch_2_'),
        6: ('batch_1_completion', 'batch_2_'),
        8: ('batch_2_',),
        9: ('batch_2_foyer_contract', 'batch_2_streamlit_smoke', 'batch_2_final_gate'),
        11: ('batch_2_final_gate',),
    }
    for i, stage_prefixes in prefixes.items():
        cells[i]['source'] = f'drop_validation_stages({stage_prefixes!r})\n\n' + cells[i]['source']

    # Keep the inventory-freshness gate blocking. Explain how to resolve it.
    cells[5]['source'] = replace_once(cells[5]['source'], 'VALIDATION.raise_for_blocking()', '''
display(pd.DataFrame([{"inventory_completed_utc": INVENTORY_COMPLETED_AT.isoformat(),
    "latest_preparation_mtime_utc": LATEST_PREPARATION_MTIME.isoformat(),
    "fresh": INVENTORY_IS_FRESH}]))
if not INVENTORY_IS_FRESH:
    print("Inventory is stale. Save notebook edits, run tools/build_project_inventory.py --root . "
          "from the project root, then rerun this cell. Do not bypass this blocking check.")
if FOCUSED_TEST_RESULT.returncode:
    print(FOCUSED_TEST_TRANSCRIPT)
VALIDATION.raise_for_blocking()''')
    # Inventory freshness must include newly deployed helpers and visitor assets.
    cells[5]['source'] = replace_once(cells[5]['source'], 'MISSING_PREPARATION_PATHS = sorted(', '''PREPARATION_PATHS.update({
    "room_runtime": PROJECT_ROOT / "src/restoration_eval/room_runtime.py",
    "visitor_renderer": PROJECT_ROOT / "src/restoration_eval/museum_visit.py",
    "visitor_controller": PROJECT_ROOT / "streamlit_assets/museum_visit/controller.js",
    "visitor_styles": PROJECT_ROOT / "streamlit_assets/museum_visit/visit.css",
    "visitor_route": PROJECT_ROOT / "streamlit_assets/museum_visit/tour.json",
    "visitor_freeze": PROJECT_ROOT / "config/publication/museum_visit_freeze.json",
    "archive_freeze": PROJECT_ROOT / "config/publication/research_archive_freeze.json",
})

MISSING_PREPARATION_PATHS = sorted(''')
    cells[6]['source'] = cells[6]['source'].replace('"Next visual gate:"', '"Next validation gate (presentation already approved):"')
    cells[6]['source'] = replace_once(cells[6]['source'], 'CANONICAL_FILES_AFTER_BATCH = (', '''REQUIRED_BATCH_1_STAGES = {
    "batch_1_contract", "batch_1_package_contract", "batch_1_package_integrity",
    "batch_1_indexed_paths", "batch_1_runtime_package", "batch_1_governance",
}
MISSING_BATCH_1_STAGES = REQUIRED_BATCH_1_STAGES - {
    c.validation_stage for c in VALIDATION.checks
}
if MISSING_BATCH_1_STAGES:
    raise RuntimeError("Run every Batch 1 cell in order. Missing stages: "
                       + str(sorted(MISSING_BATCH_1_STAGES)))

CANONICAL_FILES_AFTER_BATCH = (''')
    old = '''RESPONSIVE_LAYOUT_PRESENT = all(
    fragment in APP_SOURCE
    for fragment in (
        "@media (max-width: 1050px)",
        "@media (max-width: 640px)",
    )
)'''
    cells[8]['source'] = replace_once(cells[8]['source'], old, RESPONSIVE)
    cells[8]['source'] = cells[8]['source'].replace('"responsive_layout",', '"responsive_rules_declared",')
    cells[8]['source'] = cells[8]['source'].replace('"Batch 2 Exhibition Foyer build"', '"approved Exhibition Foyer build marker"')
    cells[8]['source'] = replace_once(cells[8]['source'], 'replace_validation_stage(\n    "batch_2_application_source",', SOURCE_EXTRA + '\nreplace_validation_stage(\n    "batch_2_application_source",')
    cells[10]['source'] = SMOKE
    # Require all stages; an empty or partial stage set is not a passing gate.
    cells[11]['source'] = replace_once(cells[11]['source'], 'PRE_FINAL_BLOCKING_FAILURES = (', '''EXPECTED_BATCH_2_STAGES = {
    "batch_2_application_source", "batch_2_foyer_contract", "batch_2_streamlit_smoke"
}
OBSERVED_BATCH_2_STAGES = set(PRE_FINAL_BATCH_2["validation_stage"])
if OBSERVED_BATCH_2_STAGES != EXPECTED_BATCH_2_STAGES:
    raise RuntimeError("Run every Batch 2 cell in order; missing/unexpected stages: "
                       + str(EXPECTED_BATCH_2_STAGES ^ OBSERVED_BATCH_2_STAGES))

PRE_FINAL_BLOCKING_FAILURES = (''')
    cells[11]['source'] = replace_once(cells[11]['source'], 'print("Batch 2 completed successfully.")', '''print("Batch 2 local source/binding/server-smoke gate passed.")
print("Presentation was previously user-approved; fresh browser validation is NOT claimed.")
print("N35 completion: NO. External deployment validation: NOT RUN.")
print("STOP HERE. Do not run the unreconciled Batch 3+ / historical pilot cells.")''')
    cells[11]['source'] += '''
PENDING_N35_GATES = pd.DataFrame([
    {"gate": label, "status": "pending_current_release_validation"}
    for label in (
        "Batches 3-9 current room validation reconciliation",
        "Browser tour/free-popup actions, focus and keyboard behavior",
        "Desktop/tablet/mobile rendering, Firefox, zoom and second monitor",
        "Clean-checkout assets and exact remote retrieval",
        "Cold/warm cache, integrity failure and retry behavior",
        "Startup/RSS/latency/concurrency budgets",
        "Deployment dependency alignment and live-site checks",
        "Batch 10 canonical readiness report and persistence",
    )
])
display(PENDING_N35_GATES)
'''
    return cells


def markdown_preview(source):
    """Small safe renderer for the plain headings/paragraphs in this cell pack."""
    def inline(value):
        value = html.escape(value)
        value = re.sub(r'`([^`]+)`', r'<code>\1</code>', value)
        return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', value)
    blocks = []
    for paragraph in source.strip().split('\n\n'):
        if paragraph.startswith('# '):
            blocks.append('<h2>' + inline(paragraph[2:]) + '</h2>')
        elif paragraph.startswith('## '):
            blocks.append('<h3>' + inline(paragraph[3:]) + '</h3>')
        else:
            blocks.append('<p>' + inline(paragraph).replace('\n', '<br>') + '</p>')
    return '<article>' + ''.join(blocks) + '</article>'


def render(cells, *, start=0, title=None, notice=None):
    # Copy controls always use the original cell source, never rendered HTML.
    sections = []
    for index, cell in enumerate(cells, start):
        source = cell['source']
        if cell['cell_type'] == 'code':
            ast.parse(source, filename=f'N35 replacement cell {index}')
        content = html.escape(source)
        preview = (markdown_preview(source) if cell['cell_type'] == 'markdown'
                   else f'<details><summary>Show complete code · {len(source.splitlines())} lines</summary><pre>{content}</pre></details>')
        sections.append(f'<section id="cell-{index}"><header><h2>Cell {index} · {cell["cell_type"]}</h2><button onclick="copyCell({index},this)">Copy complete cell</button></header>{preview}</section>')
    encoded = json.dumps(cells, ensure_ascii=True).replace('</', '<\\/')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>N35 · Complete replacement cells through Batch 2</title>
<style>body{max-width:1080px;margin:35px auto;padding:0 24px;background:#f4f1e8;color:#193e39;font:16px/1.6 system-ui}h1{font-family:Georgia}section{margin:25px 0;border:1px solid #bca778;border-radius:8px;overflow:hidden;background:white}header{display:flex;justify-content:space-between;align-items:center;padding:8px 20px;background:#193e39;color:#fff2d2}h2{font-size:17px}button{cursor:pointer;padding:8px;border:1px solid #bca778;border-radius:5px;background:#f4ebd7;color:#193e39}pre{padding:20px;margin:0;overflow:auto;font:13px/1.55 Consolas,monospace}pre.markdown{white-space:pre-wrap;font:15px/1.7 system-ui;background:#fffaf0}a{color:inherit}.notice{border-left:4px solid #b08943;padding:14px;background:#fffaf0}nav{display:flex;gap:15px;flex-wrap:wrap}</style>
<style>article{padding:15px 24px;background:#fffaf0}article h2{font-size:23px}article code{font:13px Consolas,monospace;overflow-wrap:anywhere}summary{padding:14px 20px;cursor:pointer;color:#685635}details[open] summary{border-bottom:1px solid #ddd}</style>
<h1>N35 · Batches 1–2 replacement cells</h1><p>Complete cells in notebook order. No application changes and no notebook execution.</p>
<p class="notice">Replace cells 0–11, retain their Markdown/code types, save, refresh the inventory, restart the kernel, and run in order. Stop at the end of Batch 2. Never Run All into the historical pilot cells. Source/schema checks are not browser or deployment certification.</p><nav>'''
    page += ''.join(f'<a href="#cell-{i}">{i}</a>' for i in range(start, start + len(cells))) + '</nav>'
    page += ''.join(sections)
    page += '<script>const cells=' + encoded + ''';
async function copyCell(i,b){const text=cells[i].source;try{await navigator.clipboard.writeText(text);b.textContent='Copied';}catch{const t=document.createElement('textarea');t.value=text;document.body.append(t);t.select();const ok=document.execCommand('copy');t.remove();b.textContent=ok?'Copied':'Select and copy the cell manually';}}</script></html>'''
    page = page.replace('const text=cells[i].source', f'const text=cells[i-{start}].source')
    if title is not None:
        page = re.sub(r'<title>.*?</title>', lambda _: '<title>' + html.escape(title) + '</title>', page)
        page = re.sub(r'<h1>.*?</h1>', lambda _: '<h1>' + html.escape(title) + '</h1>', page, count=1)
    if notice is not None:
        page = re.sub(r'<p class="notice">.*?</p>', lambda _: '<p class="notice">' + html.escape(notice) + '</p>', page, count=1)
    return page


def main():
    raw = NOTEBOOK.read_bytes()
    cells = build_cells(json.loads(raw))
    page = render(cells)
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / 'N35_batches_1_2_replacements.html').write_text(page, encoding='utf-8')
    text = '# Copy cells into N35. Do not run this whole file as a script.\n\n'
    for index, cell in enumerate(cells):
        text += f'# %% {"[markdown] " if cell["cell_type"] == "markdown" else ""}Cell {index}\n'
        text += ('\n'.join('# ' + line for line in cell['source'].splitlines())
                 if cell['cell_type'] == 'markdown' else cell['source']) + '\n\n'
    (DEST / 'N35_batches_1_2_replacements.py').write_text(text, encoding='utf-8')
    (DEST / 'cells.json').write_text(json.dumps(cells, indent=2), encoding='utf-8')
    assert NOTEBOOK.read_bytes() == raw, 'Notebook changed unexpectedly'
    print(f'Rendered {len(cells)} complete cells; code syntax checked, none executed.')
    print('Notebook SHA-256 unchanged:', hashlib.sha256(raw).hexdigest())
    print(DEST / 'N35_batches_1_2_replacements.html')


if __name__ == '__main__':
    main()
