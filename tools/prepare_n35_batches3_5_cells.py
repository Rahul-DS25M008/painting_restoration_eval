"""Render full N35 replacement cells 12–27; never edit/execute the notebook."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
from textwrap import dedent, indent

from prepare_n35_batch2_cells import render

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/35_dashboard_and_deployment_validation.ipynb"
DEST = ROOT / ".codex_tmp/n35_batches_3_5"

SETUP = r'''
# Shared read-only room validation harness. Requires the completed Batch 2 kernel.
import importlib
TOOLS_ROOT = str(PROJECT_ROOT / "tools")
if TOOLS_ROOT not in sys.path:
    sys.path.insert(0, TOOLS_ROOT)
import n35_room_validation as n35
n35 = importlib.reload(n35)
n35.required_stages(VALIDATION.checks, ["batch_2_final_gate"])
drop_validation_stages(tuple(f"batch_{i}_" for i in range(3, 11)))
VALIDATION.raise_for_blocking()

N35_BATCH_START = {}
N35_PROTECTED_PATHS = sorted({
    APP_PATH,
    *list((PROJECT_ROOT / "src/restoration_eval").glob("*.py")),
    *list((PROJECT_ROOT / "streamlit_assets").rglob("*.js")),
    *list((PROJECT_ROOT / "streamlit_assets").rglob("*.css")),
    PROJECT_ROOT / "streamlit_assets/room_runtime/index.html",
})

def protected_snapshot():
    return {p.relative_to(PROJECT_ROOT).as_posix(): n35.digest(p)
            for p in N35_PROTECTED_PATHS}

def start_room_batch(number):
    n35.required_stages(VALIDATION.checks, [f"batch_{number - 1}_final_gate"])
    VALIDATION.raise_for_blocking()
    if n35.snapshot(OUTPUT_ROOT):
        raise RuntimeError("Canonical N35 files must remain absent until Batch 10.")
    N35_BATCH_START[number] = (n35.snapshot(OUTPUT_ROOT), protected_snapshot())

def room_check(key, expected, observed, passed=None, description=None):
    return application_source_check(key, description or key.replace("_", " "),
        expected, observed, expected == observed if passed is None else passed)

def record_room_stage(stage, rows):
    if not rows:
        raise RuntimeError("An empty room stage cannot pass.")
    replace_validation_stage(stage, rows)
    display(pd.DataFrame(rows)[["check_id", "passed", "expected", "observed"]])
    VALIDATION.raise_for_blocking()

def test_record(group):
    print(f"Running {group} local contract tests; no inference or artifact generation.")
    result = n35.run_suite(PROJECT_ROOT, group)
    print(result["transcript"])
    print("Historical checks replaced:", result["excluded_historical_checks"])
    return room_check("focused_tests", True, result["passed"],
        description=json.dumps({k: v for k, v in result.items() if k != "transcript"}))

def finish_room_batch(number, expected_stages):
    n35.required_stages(VALIDATION.checks, expected_stages)
    observed = {c.validation_stage for c in VALIDATION.checks
                if c.validation_stage.startswith(f"batch_{number}_")
                and c.validation_stage != f"batch_{number}_final_gate"}
    if observed != set(expected_stages):
        raise RuntimeError(f"Unexpected/missing stages: {observed ^ set(expected_stages)}")
    before = N35_BATCH_START[number]
    after = (n35.snapshot(OUTPUT_ROOT), protected_snapshot())
    record_room_stage(f"batch_{number}_final_gate", [
        room_check("read_only_outputs_and_dashboard", before, after),
        room_check("canonical_files_absent", {}, after[0]),
    ])
    frame = VALIDATION.to_dataframe()
    display(frame[frame.validation_stage.str.startswith(f"batch_{number}_")]
        .groupby("validation_stage").agg(checks=("check_id", "size"), passed=("passed", "sum")))
    print(f"Batch {number}: local source/data/server checks passed. Canonical outputs: 0.")
    print("Previously approved visual layout retained. Fresh browser/Firefox/cloud validation NOT claimed.")
    print("N35 completion: NO. These cells do not certify external deployment readiness.")

start_room_batch(3)
APP_SOURCE = APP_PATH.read_text(encoding="utf-8")
APP_TREE = ast.parse(APP_SOURCE)
N35_APP_CONSTANTS = n35.literals(APP_PATH)
for name in ("STUDY_SHELL_RELATIVE_PATH", "STUDY_SHELL_SHA256", "STUDY_CLEAN_ASSET_ID",
             "STUDY_CORE_ASSETS", "STUDY_CATEGORY_LABELS", "STUDY_CATEGORY_ANCHORS",
             "STUDY_PATH_DEFAULT_OPTIONS", "STUDY_OTHER_CHANGE_OPTIONS", "STUDY_NOTE_COPY"):
    globals()["APP_" + name] = N35_APP_CONSTANTS[name]

# Existing tests normalize ONLY the approved visitor-overlay delta; no new
# fingerprints are invented to bless drift in the Foyer or Study layout.
record_room_stage("batch_3_application_source", [
    room_check("study_build", "n35.batch3.study.v4", N35_APP_CONSTANTS["STUDY_BUILD"]),
    test_record("study"),
])
'''

METRIC_SOURCE = r'''
start_room_batch(4)
from restoration_eval.metric_inspection import public_contract, LENSES, REGIONS, VERSION
from restoration_eval.metric_inspection_view import load_inspection
METRIC_POLICY = public_contract()
with n35.offline() as METRIC_SOURCE_NETWORK:
    METRIC_ROOM = PACKAGE.load_room("metric_framework")
    METRIC_BINDINGS = PACKAGE.bindings_for(room_id="metric_framework")
metric_shell = CONFIG["presentation"]["decorative_shells"]["metric_framework"]
metric_shell_path = n35.safe_path(PROJECT_ROOT, metric_shell["path"])
record_room_stage("batch_4_source_contract", [
    room_check("room_rows", 12, len(METRIC_ROOM)),
    room_check("unique_room_ids", 12, METRIC_ROOM.display_id.nunique()),
    room_check("binding_ids", set(METRIC_ROOM.display_id), set(METRIC_BINDINGS.display_id)),
    room_check("binding_count", 21, len(METRIC_BINDINGS)),
    room_check("local_package_network", [], METRIC_SOURCE_NETWORK),
    room_check("shell_checksum", metric_shell["sha256"], n35.digest(metric_shell_path)),
    room_check("shell_is_not_evidence", False, metric_shell["scientific_content_allowed"]),
    room_check("lens_region_pairs", (7, 7, 49, 37, 12),
        (len(LENSES), len(REGIONS), len(METRIC_POLICY),
         sum(p["allowed"] for p in METRIC_POLICY.values()),
         sum(not p["allowed"] for p in METRIC_POLICY.values()))),
    test_record("metric"),
])
'''

METRIC_DATA = r'''
# All 300 saved manifests: exact teaching identity and public pair policy.
# Full source/map checksums are sampled across the five category anchors below;
# this is not a claim that all corpus image bytes have been rehashed/downloaded.
METRIC_MANIFEST_AUDIT = []
with n35.offline() as METRIC_DATA_NETWORK:
    for pid in PACKAGE.painting_lookup.painting_id.astype(str):
        folder = PROJECT_ROOT / "streamlit_assets/evidence/metric_framework" / pid
        meta = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        case_id = f"canonical__{pid}__mixed_damage"
        candidate_id = f"candidate__lama__{case_id}__c00"
        identity_ok = (meta["version"] == VERSION and meta["painting_id"] == pid
                       and meta["case_id"] == case_id and meta["candidate_id"] == candidate_id)
        policy_ok = (set(meta["pairs"]) == set(METRIC_POLICY)
                     and set(meta["regions"]) == set(REGIONS))
        for key, expected in METRIC_POLICY.items():
            actual = meta["pairs"].get(key, {})
            policy_ok &= all(actual.get(k) == expected[k]
                             for k in ("lens", "region", "canonical_region", "allowed", "role"))
            if expected["allowed"]:
                policy_ok &= (actual.get("recipe") == expected["recipe"]
                              and bool(actual.get("maps"))
                              and all(k in meta["assets"] for k in actual.get("maps", [])))
            else:
                policy_ok &= not actual.get("maps")
        path_ok = all(n35.safe_path(PROJECT_ROOT, a["path"]).is_file()
                      for collection in ("sources", "assets", "regions")
                      for a in meta[collection].values())
        METRIC_MANIFEST_AUDIT.append(dict(painting_id=pid, identity=identity_ok,
                                        policy=policy_ok, local_paths=path_ok))
    METRIC_SAMPLE_AUDIT = []
    for pid in ("p001", "p018", "p026", "p039", "p043"):
        meta = load_inspection(PROJECT_ROOT, pid)
        METRIC_SAMPLE_AUDIT.append(dict(painting_id=pid, sources=len(meta["sources"]),
            maps=len(meta["assets"]), supports=len(meta["regions"]),
            candidate_id=meta["candidate_id"], loader=meta["loader_version"]))

METRIC_MANIFEST_AUDIT = pd.DataFrame(METRIC_MANIFEST_AUDIT)
record_room_stage("batch_4_saved_evidence", [
    room_check("manifest_coverage", (300, 300),
        (len(METRIC_MANIFEST_AUDIT), METRIC_MANIFEST_AUDIT.painting_id.nunique())),
    room_check("exact_identities", 300, int(METRIC_MANIFEST_AUDIT.identity.sum())),
    room_check("complete_policy", 300, int(METRIC_MANIFEST_AUDIT.policy.sum())),
    room_check("local_registered_paths", 300, int(METRIC_MANIFEST_AUDIT.local_paths.sum())),
    room_check("five_checked_samples", 5, len(METRIC_SAMPLE_AUDIT)),
    room_check("outbound_network_attempts", [], METRIC_DATA_NETWORK),
])
display(pd.DataFrame(METRIC_SAMPLE_AUDIT))
print("Saved diagnostic companions checked; no metric producer, model download or inference ran.")
'''

METRIC_RUNTIME = r'''
# A fresh in-process AppTest, not the user's running Streamlit process.
METRIC_SMOKE = n35.room_smoke(APP_PATH, {"room": "metric_framework", "metric_painting": "p018"})
METRIC_APP_TEST = METRIC_SMOKE["app"]
METRIC_RUNTIME_RECORDS = []

def capture_metric(check_id, pid, attempts):
    markup = n35.app_html(METRIC_APP_TEST)
    case_id = f"canonical__{pid}__mixed_damage"
    candidate_id = f"candidate__lama__{case_id}__c00"
    expected = {"errors": [], "network": [], "identity": True, "regions": 7,
                "lenses": 7, "selector_paintings": 300, "controller": True}
    observed = {"errors": n35.app_errors(METRIC_APP_TEST), "network": attempts,
        "identity": all(token in markup for token in (
            f'data-painting-id="{pid}"', f'data-case-id="{case_id}"',
            f'data-candidate-id="{candidate_id}"')),
        "regions": markup.count('class="metric-region"'),
        "lenses": markup.count('class="metric-lens-head"'),
        "selector_paintings": len(METRIC_APP_TEST.selectbox(key="metric_painting_selector").options),
        "controller": any("MuseumReadiness.watch" in str(e.proto.srcdoc)
                          for e in METRIC_APP_TEST.get("iframe"))}
    METRIC_RUNTIME_RECORDS.append(room_check(check_id, expected, observed))

capture_metric("opening_p018", "p018", METRIC_SMOKE["network_attempts"])
with n35.offline() as attempts:
    METRIC_APP_TEST.selectbox(key="metric_painting_selector").select("p001").run()
capture_metric("native_painting_callback", "p001", attempts)
painting_ids = tuple(PACKAGE.painting_lookup.painting_id.astype(str))
surprise_pid = painting_ids[(painting_ids.index("p001") + 37) % len(painting_ids)]
with n35.offline() as attempts:
    METRIC_APP_TEST.button(key="metric_surprise_button").click().run()
capture_metric("native_surprise_callback", surprise_pid, attempts)
record_room_stage("batch_4_server_smoke", METRIC_RUNTIME_RECORDS)
print("Three Python-rendered states verified. Lens dragging/region clicks require browser QA in Batch 10.")
'''

GALLERY_SOURCE = r'''
start_room_batch(5)
from restoration_eval import model_gallery as GALLERY
# Discard process-local read caches only; no disk cache or running server changes.
GALLERY.catalogue.cache_clear()
GALLERY.metric_index.cache_clear()
GALLERY.painting_geometry.cache_clear()
GALLERY.image_uri.cache_clear()
GALLERY_FREEZE = n35.verify_gallery_freeze(PROJECT_ROOT)
record_room_stage("batch_5_approved_source", [
    room_check("seven_gallery_files_plus_shared_transport", 8, len(GALLERY_FREEZE)),
    *[room_check("frozen__" + r["path"], r["expected"], r["observed"]) for r in GALLERY_FREEZE],
    test_record("gallery"),
])
print("The historical notebook-SHA assertion was replaced by a before/after cell-source and canonical-output check.")
print("Normal notebook output/metadata autosaves are allowed; cell-source edits are not.")
print("Its frozen test file was not edited. All scientific Gallery checks remain required.")
print("Gallery view normalization covers only the two approved e88feea5 transport substitutions.")
'''

GALLERY_DATA = r'''
with n35.offline() as GALLERY_DATA_NETWORK:
    cat = GALLERY.catalogue()
    GALLERY_ROOM = PACKAGE.load_room("model_gallery")
    GALLERY_BINDINGS = PACKAGE.bindings_for(room_id="model_gallery")
    opening = GALLERY.case_payload("canonical__p018__mixed_damage")
    without_sdxl = next(c for c in sorted(cat["cases"])
                        if c.startswith("canonical__p018__") and "zero" not in c
                        and c not in cat["models"]["sdxl_inpainting"])
    absent = GALLERY.case_payload(without_sdxl)
    zero = GALLERY.case_payload("canonical__p018__zero_control")
    sd = opening["models"]["stable_diffusion_inpainting"]["candidate"]
    empty_crop_unranked = all(
        entry["metrics"]["crop_ssim"] is None
        or entry["metrics"]["crop_ssim"]["status"] != "ok"
        or entry["metrics"]["crop_ssim"]["restored_value"] is None
        for entry in zero["models"].values())
    invalid_rejected = False
    try:
        GALLERY.selected_case("p018", "canonical__p019__mixed_damage")
    except ValueError:
        invalid_rejected = True

record_room_stage("batch_5_exact_evidence", [
    room_check("room_and_binding_count", (12, 19), (len(GALLERY_ROOM), len(GALLERY_BINDINGS))),
    room_check("binding_ids", set(GALLERY_ROOM.display_id), set(GALLERY_BINDINGS.display_id)),
    room_check("population", (300, 2620, 4), (len(cat["paintings"]), len(cat["cases"]), len(GALLERY.MAIN_MODELS))),
    room_check("sd_primary_identity", ("sd15__p00__s2026__d0cd65cf894a", 2026, True),
        (sd["candidate_id"], sd["seed"], sd["is_primary_candidate"])),
    room_check("sdxl_bounded_coverage", (24, 35, 19),
        (len(cat["models"]["sdxl_inpainting"]), len(cat["sdxl_scheduled"]),
         len({r["painting_id"] for r in cat["models"]["sdxl_inpainting"].values()}))),
    room_check("sdxl_exact_case_available", True, "sdxl_inpainting" in opening["models"]),
    room_check("sdxl_not_substituted_same_painting", False, "sdxl_inpainting" in absent["models"]),
    room_check("zero_crop_not_ranked", True, empty_crop_unranked),
    room_check("cross_painting_identity_rejected", True, invalid_rejected),
    room_check("outbound_network_attempts", [], GALLERY_DATA_NETWORK),
])
GALLERY_LOCAL_SUMMARY = pd.DataFrame([
    {"case_id": p["case_id"], "models": len(p["models"]), "sdxl_state": p["sdxl_status"]}
    for p in (opening, absent, zero)])
display(GALLERY_LOCAL_SUMMARY)
print("Candidate metrics are saved N13 rows, not newly computed scores; no combined ranking is produced.")
'''

GALLERY_RUNTIME = r'''
GALLERY_RUNTIME_RECORDS = []
for label, case_id, sdxl_available in (
    ("opening", "canonical__p018__mixed_damage", True),
    ("same_painting_no_sdxl", without_sdxl, False),
    ("zero_control", "canonical__p018__zero_control", False),
):
    smoke = n35.room_smoke(APP_PATH, {"room": "model_gallery", "gallery_painting": "p018",
        "gallery_case": case_id})
    markup = smoke["html"]
    expected = {"errors": [], "network": [], "exact_case": True,
                "four_method_titles": 4, "sdxl_available": sdxl_available, "controller": True}
    observed = {"errors": smoke["errors"], "network": smoke["network_attempts"],
        "exact_case": f'data-case-id="{case_id}"' in markup,
        "four_method_titles": markup.count('class="gallery-method-title '),
        "sdxl_available": 'aria-label="Inspect bounded SDXL result"' in markup,
        "controller": any("MuseumReadiness.watch" in str(e.proto.srcdoc)
                          for e in smoke["app"].get("iframe"))}
    GALLERY_RUNTIME_RECORDS.append(room_check(label, expected, observed))

# A mismatched deep link must visibly fail, never display a different case.
invalid = n35.room_smoke(APP_PATH, {"room": "model_gallery", "gallery_painting": "p018",
    "gallery_case": "canonical__p019__mixed_damage"})
GALLERY_RUNTIME_RECORDS.append(room_check("invalid_identity_fails_closed", True,
    not invalid["app"].exception and not invalid["network_attempts"]
    and any("does not belong" in error for error in invalid["errors"])
    and 'class="model-stage"' not in invalid["html"]))
record_room_stage("batch_5_server_smoke", GALLERY_RUNTIME_RECORDS)

finish_room_batch(5, {"batch_5_approved_source", "batch_5_exact_evidence", "batch_5_server_smoke"})
N35_PENDING_GATES = pd.DataFrame([
    {"gate": "Batches 6–9 current room validation", "status": "pending"},
    {"gate": "Browser interactions, reload boundaries, keyboard/focus and Firefox/second monitor", "status": "not tested by AppTest"},
    {"gate": "Responsive rendering at desktop/tablet/mobile viewports", "status": "pending fresh browser QA"},
    {"gate": "Gallery local originals + N13 CSV: pinned remote retrieval/compact lookup", "status": "deployment blocker; not fixed or waived here"},
    {"gate": "Clean-checkout Git/HF assets, SHA verification, failure/retry and cold/warm cache", "status": "pending"},
    {"gate": "Startup, memory, latency, concurrency and deployed dependency alignment", "status": "pending measurement"},
    {"gate": "Live Streamlit site and Batch 10 canonical readiness report", "status": "pending"},
])
display(N35_PENDING_GATES)
print("STOP HERE at the end of Batch 5. Do not run the historical Batch 6+ cells or Run All.")
print("Five of ten batch gates can be complete after your successful execution; N35 is not yet complete.")
'''


def cell(source, kind="code"):
    return {"cell_type": kind, "source": dedent(source).strip() + "\n"}


def invalidation(number, stages):
    prefixes = tuple(stages) + tuple(f"batch_{i}_" for i in range(number + 1, 11))
    return f"drop_validation_stages({prefixes!r})\n\n"


def build_cells(notebook):
    original = notebook["cells"]
    source = lambda i: "".join(original[i]["source"])
    if "## Batch 3" not in source(12) or "## Batch 6" not in source(28):
        raise ValueError("Unexpected notebook cell boundaries; do not overwrite a shifted notebook.")
    # These two complete, already-reconciled evidence cells are retained verbatim
    # except for rerun invalidation and a read-only network guard.
    evidence, relationships, runtime = source(14), source(15), source(16)
    if "N35_BATCHES_3_5_PACK" in source(12) or (
        "def finish_room_batch(" in source(13)
        and "with n35.offline() as STUDY_NETWORK_ATTEMPTS:" in runtime
        and "finish_room_batch(5," in source(27)
    ):
        return [dict(cell_type=c["cell_type"], source="".join(c["source"])) for c in original[12:28]]
    for token, content in (("STUDY_EVIDENCE_CHECKS", evidence),
                           ("EXPECTED_STUDY_ANCHORS", relationships),
                           ("capture_study_runtime_state", runtime)):
        if token not in content:
            raise ValueError(f"Missing expected Study Design cell: {token}")
    # Keep the complete existing Study interaction coverage. Guard every run,
    # including native callback transitions, against outbound network attempts.
    runtime = runtime.replace('return "\\n".join(\n        str(element.value)\n        for element in app_test.markdown\n    )',
                              'return n35.app_html(app_test)')
    runtime = runtime.replace('for exception in app_test.exception',
                              'for exception in list(app_test.exception) + list(app_test.error)')
    begin = runtime.index("STUDY_APP_TEST = AppTest.from_file(")
    end = runtime.index("replace_validation_stage(\n    \"batch_3_streamlit_fragment_smoke\"")
    runtime = (runtime[:begin] + "with n35.offline() as STUDY_NETWORK_ATTEMPTS:\n"
               + indent(runtime[begin:end], "    ")
               + '\nSTUDY_RUNTIME_RECORDS.append(room_check("outbound_network_attempts", [], STUDY_NETWORK_ATTEMPTS))\n\n'
               + runtime[end:])
    runtime = runtime.replace('"Browser same-document behavior: manually "\n    "approved; AppTest validates the native "',
                              '"Fresh browser same-document behavior: NOT checked; "\n    "AppTest validates the native "')
    cells = [
        cell('''
        ## Batch 3 — Study Design: current-release validation

        <!-- N35_BATCHES_3_5_PACK -->

        The approved dashboard is frozen. This batch validates it without changing its layout:
        13 exact N34 room records, five category representatives, 105 visible saved case routes,
        four parallel experiment paths, six Study Notes, shared D02 routing and native query callbacks.
        The current visitor-overlay freeze replaces the obsolete tour-function assertion.

        Requires successful Batches 1–2 in this kernel. Use all five code cells in order.
        Rerunning an earlier cell invalidates later gates. No notebook editing, producer execution,
        network access, server launch or canonical N35 persistence is performed by these cells.
        AppTest checks Python-rendered markup and callbacks, not browser JavaScript or visual alignment.
        The exact evidence/relationship cells are retained, with rerun and offline guards added.
        ''', "markdown"),
        cell(SETUP),
        cell(invalidation(3, ("batch_3_study_evidence", "batch_3_study_relationships", "batch_3_streamlit_fragment_smoke", "batch_3_final_gate"))
             + "n35.required_stages(VALIDATION.checks, ['batch_3_application_source'])\n"
             + "with n35.offline() as STUDY_EVIDENCE_NETWORK:\n" + indent(evidence, "    ")
             + '\nrecord_room_stage("batch_3_evidence_network", [room_check("network", [], STUDY_EVIDENCE_NETWORK)])\n'),
        cell(invalidation(3, ("batch_3_study_relationships", "batch_3_streamlit_fragment_smoke", "batch_3_final_gate"))
             + "n35.required_stages(VALIDATION.checks, ['batch_3_study_evidence', 'batch_3_evidence_network'])\n"
             + "with n35.offline() as STUDY_RELATIONSHIP_NETWORK:\n" + indent(relationships, "    ")
             + '\nrecord_room_stage("batch_3_relationship_network", [room_check("network", [], STUDY_RELATIONSHIP_NETWORK)])\n'),
        cell(invalidation(3, ("batch_3_streamlit_fragment_smoke", "batch_3_final_gate"))
             + "n35.required_stages(VALIDATION.checks, ['batch_3_study_relationships', 'batch_3_relationship_network'])\n" + runtime),
        cell(invalidation(3, ("batch_3_final_gate",)) + '''finish_room_batch(3, {
            "batch_3_application_source", "batch_3_study_evidence", "batch_3_study_relationships",
            "batch_3_evidence_network", "batch_3_relationship_network", "batch_3_streamlit_fragment_smoke"})
print("Continue with the replacement Batch 4 below, not historical pilot cells.")'''),
        cell('''
        ## Batch 4 — Metric Framework: saved diagnostic companions

        Validate the frozen teaching room: one canonical mixed-damage LaMa candidate per painting,
        7 lenses × 7 regions, 37 allowed pairs and 12 prohibited pairs. These spatial companions
        are inspection diagnostics, not replacements for frozen benchmark scalar metrics.

        Check all 300 manifests for identity, policy and local path availability. Rehash saved
        sources/maps/supports for five category representatives; use focused arithmetic and
        corruption-rejection tests on the saved p018 exhibit. No diagnostic maps are regenerated.
        Historical Controlled-50 dashboard-metrics tests are not used as evidence for this release.

        AppTest checks the opening, native painting selector and Surprise me callback. It cannot
        operate the browser-only draggable lens or certify Firefox, viewport layout or hosted assets.
        Those remain Batch 10 gates. All four code cells are required; no canonical outputs are written.
        ''', "markdown"),
        cell(invalidation(4, ("batch_4_",)) + METRIC_SOURCE),
        cell(invalidation(4, ("batch_4_saved_evidence", "batch_4_server_smoke", "batch_4_final_gate"))
             + "n35.required_stages(VALIDATION.checks, ['batch_4_source_contract'])\n" + METRIC_DATA),
        cell(invalidation(4, ("batch_4_server_smoke", "batch_4_final_gate"))
             + "n35.required_stages(VALIDATION.checks, ['batch_4_saved_evidence'])\n" + METRIC_RUNTIME),
        cell(invalidation(4, ("batch_4_final_gate",)) + '''finish_room_batch(4, {
    "batch_4_source_contract", "batch_4_saved_evidence", "batch_4_server_smoke"})
print("Continue with replacement Batch 5 below.")'''),
        cell('''
        ## Batch 5 — Model Gallery: exact saved comparisons

        Validate four primary methods across 300 paintings / 2,620 cases, their exact candidate
        and experiment identities, saved N13 measurements, empty-mask non-applicability and
        case-scoped SDXL availability (24 completed / 35 scheduled, spanning 19 paintings).
        SDXL is bounded evidence, not a fifth full-corpus ranking participant.

        The seven-file Gallery visual freeze remains mandatory. Normalize only the two approved
        non-visual transport substitutions from commit e88feea5 back to its original fingerprint;
        separately verify the shared transport against the later museum-visit freeze. No other
        changes are accepted. Its historical test asserting an old
        whole-notebook SHA is incompatible with normal user notebook edits: replace only that
        assertion with a current before/after cell-source and canonical-output snapshot (allowing
        normal execution-count/output autosaves), and report
        the replacement explicitly. Leave the frozen test file itself unchanged. Every scientific
        Gallery test still runs; skipped tests and empty suites cannot produce a passing gate.

        This room currently reads local originals and scans the saved N13 CSV (about 144 MB on disk)
        once per fresh cache. This is data loading, not metric recomputation. Remote pinned loading,
        compact lookup and deployed memory/latency remain explicit deployment gates, not waived by
        a local pass. AppTest checks three case states and an invalid-identity route, not JS dialogs.

        Run all four code cells. Stop after this batch; historical Batch 6+ cells remain unreconciled.
        ''', "markdown"),
        cell(invalidation(5, ("batch_5_",)) + GALLERY_SOURCE),
        cell(invalidation(5, ("batch_5_exact_evidence", "batch_5_server_smoke", "batch_5_final_gate"))
             + "n35.required_stages(VALIDATION.checks, ['batch_5_approved_source'])\n" + GALLERY_DATA),
        cell(invalidation(5, ("batch_5_server_smoke", "batch_5_final_gate"))
             + "n35.required_stages(VALIDATION.checks, ['batch_5_exact_evidence'])\n" + GALLERY_RUNTIME),
    ]
    # Batch 5 has three code cells plus its Markdown header in this list so far;
    # retain the original five-cell boundary by separating smoke and final gate.
    last = cells.pop()["source"]
    boundary = last.index("finish_room_batch(5,")
    cells.extend([cell(last[:boundary]), cell(invalidation(5, ("batch_5_final_gate",)) + last[boundary:])])
    assert len(cells) == 16
    for index, item in enumerate(cells, 12):
        if item["cell_type"] == "code":
            ast.parse(item["source"], filename=f"N35 cell {index}")
    return cells


def main():
    before = NOTEBOOK.read_bytes()
    cells = build_cells(json.loads(before))
    page = render(cells, start=12, title="N35 · Batches 3–5 complete replacement cells",
        notice="Replace cells 12–27 (zero-based), from the Batch 3 heading through the end of Batch 5. "
        "Keep Markdown/code types. Leave Batches 1–2 and Batch 6 onward unchanged. Continue in the "
        "kernel that passed Batch 2; otherwise rerun Batches 1–2 first. Run cells in order; STOP after "
        "Batch 5. Never Run All into historical pilot cells. No application or notebook edits are made by this pack.")
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "N35_batches_3_5_replacements.html").write_text(page, encoding="utf-8")
    text = "# Copy complete cells into N35; do not run this file as one script.\n\n"
    for index, item in enumerate(cells, 12):
        text += f'# %% {"[markdown] " if item["cell_type"] == "markdown" else ""}Cell {index}\n'
        text += ("\n".join("# " + line for line in item["source"].splitlines())
                 if item["cell_type"] == "markdown" else item["source"]) + "\n\n"
    (DEST / "N35_batches_3_5_replacements.py").write_text(text, encoding="utf-8")
    (DEST / "cells.json").write_text(json.dumps(cells, indent=2), encoding="utf-8")
    if NOTEBOOK.read_bytes() != before:
        raise RuntimeError("Notebook changed during preparation")
    print("Prepared 16 full cells (12–27), syntax checked; none executed.")
    print("Notebook unchanged:", hashlib.sha256(before).hexdigest())
    print(DEST / "N35_batches_3_5_replacements.html")


if __name__ == "__main__":
    main()
