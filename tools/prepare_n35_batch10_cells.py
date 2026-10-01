"""Render copy-ready N35 Batch 10 cells; never edit or execute the notebook."""
import ast
import hashlib
import json
from pathlib import Path
from textwrap import dedent
from prepare_n35_batch2_cells import render

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/35_dashboard_and_deployment_validation.ipynb"
DEST = ROOT / ".codex_tmp/n35_batch10"


def cell(text, kind="code"): return {"cell_type":kind,"source":dedent(text).strip()+"\n"}


def build_cells():
    return [cell('''
    ## Batch 10 — local integration and deployment readiness

    Continue after the successful Batch 9 gate. Replace the old pending-gates cell
    48 and everything after it with this section. Do not run the entire notebook.
    The optional replacement for cell 8 is only for a future clean-kernel rerun.

    This batch validates the nonvisual deployment adapters, exact saved-row
    projections, all candidate/report routes, missing-local-file fallbacks,
    immutable public samples, cache/failure behavior and local performance.
    It performs no inference, scientific recomputation, upload, commit or deployment.
    Network cells explicitly fetch small selected public evidence samples.

    Original visual baselines are not replaced. Ten precisely fingerprinted backend
    deltas are checked separately; CSS, controllers, artwork and layout remain frozen.
    N29's historical manifest discrepancy remains visible, with independent byte
    verification of all six artifact groups, rather than rewriting its history.

    Browser, Firefox and responsive observations cannot be manufactured
    by AppTest. Enter real evidence in the manual-gates cell; empty entries stop the
    release gate. Local checks do not certify the hosted site. Batch 11 records the
    deployed revision, URL, clean Linux runtime and live results after the deployment commit.
    ''', "markdown"), cell('''
    import importlib
    import json
    import subprocess
    import sys
    from pathlib import Path
    sys.path.insert(0, str(PROJECT_ROOT / "tools"))
    import n35_room_validation as n35
    import n35_batch10 as b10
    import n35_deployment_checks as deploy_checks
    n35 = importlib.reload(n35)
    b10 = importlib.reload(b10)
    n35.required_stages(VALIDATION.checks, [f"batch_{i}_final_gate" for i in range(2,10)])
    drop_validation_stages(("batch_10_", "batch_11_"))
    VALIDATION.raise_for_blocking()
    B10_BEFORE = b10.fingerprint()
    B10_RECEIPTS = {}

    def b10_record(name, result):
        B10_RECEIPTS[name] = result
        record_room_stage("batch_10_" + name, [room_check(name, True, result["passed"],
            description=json.dumps(result, default=str))])

    def b10_command(arguments):
        process = subprocess.run([sys.executable, *arguments], cwd=PROJECT_ROOT,
            capture_output=True, text=True, timeout=300)
        print(process.stdout)
        print(process.stderr)
        return {"passed": process.returncode==0, "returncode":process.returncode,
                "stdout":process.stdout, "stderr":process.stderr}

    print("Batch 10 initialized. No canonical output written and no deployment performed.")
    '''), cell('''
    # Current source/data regression, not a reuse of pre-backend-change passes.
    b10_record("visual_delta", b10.visual_delta_checks())
    b10_record("companion", deploy_checks.companion_check())
    b10_record("closure", b10.closure_check())
    b10_record("transport", b10_command(["-m", "unittest", "discover", "-s", "tests", "-p", "test_evidence_transport.py", "-v"]))
    b10_record("persistence_tests", b10_command(["-m", "unittest", "discover", "-s", "tests", "-p", "test_n35_batch10.py", "-v"]))
    for group in ("study", "metric", "gallery", "stability", "trust_portrait", "case", "archive"):
        print("Room regression:", group, flush=True)
        result = b10.run_check("suite", group)
        print(result.get("transcript", result))
        b10_record("tests_"+group, result)
    b10_record("n29", b10.n29_check())
    print("N29: payloads verified; historical manifest checksum discrepancy retained and disclosed.")
    '''), cell('''
    # Explicit public reads. This does not download every image or upload anything.
    b10_record("remote", b10.run_check("remote"))
    b10_record("github", b10.run_check("github"))
    print("Exact-byte cold/warm HF samples and immutable Git/Git LFS samples checked.")
    '''), cell('''
    # Each render runs in a new process. Untracked scientific files are hidden;
    # the new compact deployment companion is explicitly included for staging.
    # These are server-side renders, not browser interaction or Linux certification.
    for room_id in deploy_checks.ROOMS:
        b10_record("opening_"+room_id, b10.run_check("opening", room_id,
            missing_local=True, remote=True))
    '''), cell('''
    # Existing psutil is needed for local sampled RSS; no automatic installation.
    # Five warm rerenders per room. A failure is not permission to raise the budget.
    for room_id in deploy_checks.ROOMS:
        b10_record("performance_"+room_id, b10.run_check("performance", room_id))
    print("Local Python timing/memory checked. Browser navigation p95 remains separate.")
    '''), cell('''
    ## Browser and platform evidence — required, not auto-passed

    Use the existing local server. Check all nine routes at 1672×941, 1024×1366,
    and 390×844; inspect readable controls, no clipping, dialogs and keyboard focus.
    In Firefox, repeat filters and reloads on the second monitor. Confirm same-room
    actions do not reload the document and cross-room links do. Exercise the tour,
    free exploration and self-contained report downloads.

    Record a real warm-navigation sample and compare its p95 with 1.5 seconds.
    The post-commit clean Linux/LFS validation belongs to Batch 11. Record local peak process memory
    and per-action remote totals against the configured limits (512 MiB RAM,
    34 MiB foreground transfer, at most two requests/one bundle, 60 seconds).

    Do not mark these passed based solely on Python renders or old screenshots.
    If any observation is missing or fails, stop here and share its result. The
    canonical persistence cell is deliberately locked until evidence is supplied.
    ''', "markdown"), cell('''
    # Fill ONLY after actually observing the check. Example value:
    # {"passed": True, "evidence": "browser/version, viewport, exact actions,
    # screenshot/log path and measured result", "observed_at_utc": "..."}
    # Preserve this dictionary when rerunning cells; do not erase your observations.
    if "B10_BROWSER_OBSERVATIONS" not in globals():
        B10_BROWSER_OBSERVATIONS = {key: {"passed": None, "evidence": "", "observed_at_utc": ""}
                                    for key in b10.MANUAL_GATES}
    display(pd.DataFrame(b10.manual_checks(B10_BROWSER_OBSERVATIONS)))
    '''), cell('''
    required = {"visual_delta", "companion", "closure", "transport", "persistence_tests", "n29", "remote", "github"}
    required |= {"tests_"+g for g in ("study", "metric", "gallery", "stability", "trust_portrait", "case", "archive")}
    required |= {prefix+r for prefix in ("opening_", "performance_") for r in deploy_checks.ROOMS}
    missing = sorted(required-set(B10_RECEIPTS))
    if missing: raise RuntimeError("Run missing Batch 10 stages first: " + repr(missing))
    observations = b10.manual_checks(B10_BROWSER_OBSERVATIONS)
    pending = [r["check_id"] for r in observations if not r["passed"]]
    if pending: raise RuntimeError("Unverified browser/platform gates — do not commit as ready: " + repr(pending))
    b10_record("browser_platform", {"passed":True,"observations":observations})
    b10_record("final_gate", {"passed": b10.fingerprint()==B10_BEFORE and all(r["passed"] for r in B10_RECEIPTS.values()),
        "deployment_state":"not_yet_validated", "deployment_url":"", "next_batch":11})
    VALIDATION.raise_for_blocking()
    print("Batch 10 local gates passed. Ready to persist local-readiness records, not live certification.")
    '''), cell('''
    n35.required_stages(VALIDATION.checks, ["batch_10_final_gate"])
    B10_PERSISTED = b10.persist(VALIDATION, B10_RECEIPTS, B10_BEFORE, B10_BROWSER_OBSERVATIONS)
    display(B10_PERSISTED)
    print("Four canonical N35 files persisted. Prior outputs, if any, are preserved in the reported backup.")
    print("STOP: next is commit/publish → deployment → Batch 11 live verification → N36.")
    '''), cell('''
    ## Batch 10 handoff

    The run remains `partial` because N35's live verification is not complete.
    The public URL and tested deployment revision remain blank. Do not reuse the
    old pilot URL as proof of this release. Share the final cell output before we
    prepare the precise GitHub commit and any genuinely needed publication.

    No new scientific images were generated. Existing HF bundles and report
    objects are reused. The separate compact deployment companion is intended
    for ordinary Git; it does not replace or change the immutable N34 package.
    ''', "markdown")]


def build_checkpoint_cells(approved_changes):
    """Focused replacement for the current notebook's cells 55-59."""
    setup = cell('''
    import importlib
    b10 = importlib.reload(b10)
    # Exact old/new hashes apply ONLY to the three closeout-helper/test files.
    # Application, assets, requirements and configuration cannot be reconciled here.
    B10_CHECKPOINT_BEFORE, B10_CLOSEOUT_DELTA = b10.checkpoint_fingerprint(
        B10_BEFORE, APPROVED_CLOSEOUT_CHANGES)
    result = b10_command(["-m", "unittest", "discover", "-s", "tests", "-p", "test_n35_batch10.py", "-v"])
    result["scope"] = "Current closeout helper tests only; earlier runtime receipts retained"
    result["original_validation_fingerprint"] = B10_BEFORE
    result["closeout_helper_delta"] = B10_CLOSEOUT_DELTA
    b10_record("checkpoint_helper_tests", result)
    B10_LOCAL_APPROVAL = "User reported: 'everything works perfectly, no need to change anything'. Qualitative local approval only; no per-check measurement or observation time inferred."
    if "B10_BROWSER_OBSERVATIONS" not in globals():
        B10_BROWSER_OBSERVATIONS = {key: {"passed": None, "evidence": "", "observed_at_utc": ""}
                                    for key in b10.MANUAL_GATES}
    display(pd.DataFrame(b10.manual_checks(B10_BROWSER_OBSERVATIONS)))
    print("Missing detailed observations remain pending, not passed. Existing observations preserved.")
    ''')
    setup["source"] = setup["source"].replace("APPROVED_CLOSEOUT_CHANGES", repr(approved_changes))
    return [cell('''
    ## Batch 10 — partial local checkpoint, not release certification

    Local user approval: “everything works perfectly, no need to change anything.”
    The dashboard remains frozen. Automated receipts are retained, and the revised
    closeout helper receives a short targeted test run. No full notebook rerun is needed.

    This closes Batch 10 as an evidence checkpoint, not as an all-gates-passed release.
    General approval does not establish exact viewport, keyboard, navigation,
    download, timing or resource measurements. Existing detailed observations are
    preserved; missing ones are saved as blocking, false, pending-not-verified rows.
    Any explicitly reported failure still stops checkpoint creation.

    Batch 11 must resolve the pending checklist, including all nine routes at
    1672×941, 1024×1366 and 390×844, accessibility, Firefox/second-monitor behavior,
    document reload behavior, tour, downloads, browser warm p95 ≤1.5 s, peak process
    memory ≤512 MiB and foreground remote totals ≤34 MiB, two requests/one bundle,
    60 seconds. No configured limits are relaxed. Clean Linux and the actual hosted
    revision/URL must also be verified. N35 remains partial and N36 is not cleared.
    ''', "markdown"), setup, cell('''
    required = {"visual_delta", "companion", "closure", "transport", "persistence_tests", "n29", "remote", "github", "checkpoint_helper_tests"}
    required |= {"tests_"+g for g in ("study", "metric", "gallery", "stability", "trust_portrait", "case", "archive")}
    required |= {prefix+r for prefix in ("opening_", "performance_") for r in deploy_checks.ROOMS}
    missing = sorted(required-set(B10_RECEIPTS))
    if missing: raise RuntimeError("Run missing Batch 10 stages first: " + repr(missing))
    if not all(r.get("passed") for r in B10_RECEIPTS.values()):
        raise RuntimeError("A recorded automated failure remains; no checkpoint allowed.")
    if b10.fingerprint() != B10_CHECKPOINT_BEFORE:
        raise RuntimeError("Source changed after closeout helper checks; stop and inspect.")
    _, B10_PENDING_QUALIFICATIONS = b10.qualification_record(
        VALIDATION, B10_BROWSER_OBSERVATIONS, B10_LOCAL_APPROVAL)
    b10_record("checkpoint_gate", {"passed":True,
        "scope":"Automated receipt completeness and partial checkpoint eligibility ONLY",
        "user_approval":B10_LOCAL_APPROVAL,
        "pending_qualifications":B10_PENDING_QUALIFICATIONS,
        "all_qualifications_passed":not B10_PENDING_QUALIFICATIONS,
        "deployment_state":"not_yet_validated", "deployment_url":"", "next_batch":11})
    print("Partial checkpoint eligible. Pending qualification IDs:", B10_PENDING_QUALIFICATIONS)
    '''), cell('''
    n35.required_stages(VALIDATION.checks, ["batch_10_checkpoint_gate"])
    B10_PERSISTED = b10.persist(VALIDATION, B10_RECEIPTS, B10_CHECKPOINT_BEFORE,
        B10_BROWSER_OBSERVATIONS, checkpoint_approval=B10_LOCAL_APPROVAL)
    display(B10_PERSISTED)
    print("Four canonical N35 checkpoint files saved; any prior run is preserved in the reported backup.")
    print("N35 remains PARTIAL. Pending checks were saved as blocking/not passed, not waived.")
    print("Next: scoped GitHub/HF publication review → commit → test deployment and pending gates in Batch 11 → N36.")
    '''), cell('''
    ## Batch 10 checkpoint handoff

    Share the persistence result before preparing the commit. Do not rerun Batches
    1–9, restart the kernel, or mark empty observations True just to pass a gate.
    Only cells 55–59 are replaced here; keep 55 and 59 as Markdown.

    N35 is partial, not certified ready. The saved CSV and manifest explicitly
    retain pending qualifications; the public URL and tested revision remain blank.
    Batch 11 must close those items and validate the hosted site before N36.
    Existing HF bundles are reused unless the publication review finds a real gap.
    No dashboard code, visual assets, layout, or scientific output is changed here.
    ''', "markdown")]


def render_checkpoint():
    old = {
        "tools/n35_batch10.py":"9e38fc65f3a165ee95f28cd14703180ce04e4bcca40bfc027342c926a9054a1c",
        "tools/prepare_n35_batch10_cells.py":"46fd5961778c910daa251a56f39116233ba3cb74a6e49d238276da5ffb9e6706",
        "tests/test_n35_batch10.py":"5d91214154e566b484207bab2c3fcfc9aca614033d0b108d8788e6d38bfadafc",
    }
    raw = NOTEBOOK.read_bytes()
    changes = {p:[h, hashlib.sha256((ROOT/p).read_bytes().replace(b"\r\n",b"\n")).hexdigest()]
               for p,h in old.items()}
    cells = build_checkpoint_cells(changes)
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / "N35_batch10_checkpoint_cells_55_59.html"
    target.write_text(render(cells, start=55, title="N35 · Batch 10 partial checkpoint · cells 55–59",
        notice="Replace only cells 55–59. Keep 55 and 59 as Markdown. Save, then execute 56, 57, 58 in the existing kernel. No dashboard changes or notebook execution by this preparation. Pending qualifications remain blocking/not passed in the saved record."), encoding="utf-8")
    assert NOTEBOOK.read_bytes() == raw
    print(target)
    print("Notebook unchanged:", hashlib.sha256(raw).hexdigest())


def main():
    raw = NOTEBOOK.read_bytes()
    notebook = json.loads(raw)
    cells = build_cells()
    for i, c in enumerate(cells,48):
        if c["cell_type"]=="code": ast.parse(c["source"],filename=f"N35 cell {i}")
    DEST.mkdir(parents=True,exist_ok=True)
    page = render(cells,start=48,title="N35 · Batch 10 local deployment readiness",
        notice="Replace cell 48 through the notebook end with cells 48–58 below. Continue in your successful Batch 9 kernel. No notebook cells have been executed by this preparation. Browser/platform gates require real observations and block persistence until supplied.")
    page = page.replace("Complete cells in notebook order. No application changes and no notebook execution.",
        "Complete cells in notebook order. Backend fixes are installed; notebook execution remains yours. Original visual layouts are preserved.")
    (DEST/"N35_batch10_replacements.html").write_text(page,encoding="utf-8")
    (DEST/"cells.json").write_text(json.dumps(cells,indent=2),encoding="utf-8")
    # Future fresh-kernel compatibility: keep the original cell's checks, but
    # compare the original visual baseline only after validating the exact delta.
    source = "".join(notebook["cells"][8]["source"])
    needle = '        observed = hashlib.sha256(raw).hexdigest() if raw is not None else "missing_or_unsafe"'
    if source.count(needle)!=1: raise ValueError("Cell 8 freeze block changed; inspect before replacing")
    replacement = '''        if raw is not None and item["path"].endswith(".py") and item["hash_mode"] == "lf_normalized":
            sys.path.insert(0, str(PROJECT_ROOT / "tools"))
            from n35_backend_delta import baseline_source
            raw = baseline_source(PROJECT_ROOT, item["path"]).encode()
'''+needle
    source = source.replace(needle,replacement)
    ast.parse(source)
    (DEST/"N35_cell8_backend_compatibility.html").write_text(render([cell(source)],start=8,title="N35 · Optional cell 8 compatibility replacement",
        notice="Only needed when restarting the kernel and rerunning Batches 1–9. The original visual freeze stays unchanged; exact backend deltas are validated separately. Not needed to continue directly into Batch 10."),encoding="utf-8")
    assert NOTEBOOK.read_bytes()==raw
    print("Prepared",len(cells),"complete cells (48–58); syntax checked, none executed.")
    print("Notebook unchanged:",hashlib.sha256(raw).hexdigest())
    print(DEST/"N35_batch10_replacements.html")


if __name__=="__main__": main()
