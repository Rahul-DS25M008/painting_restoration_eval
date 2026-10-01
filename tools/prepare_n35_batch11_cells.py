"""Render complete user-pasted Batch 11 cells; never edit or run a notebook."""
import ast
import hashlib
from pathlib import Path
from textwrap import dedent
from prepare_n35_batch2_cells import render

ROOT=Path(__file__).resolve().parents[1]


def cell(text, kind="code"):
    return {"cell_type":kind,"source":dedent(text).strip()+"\n"}


def build_cells():
    return [cell('''
    ## Batch 11 — live deployment acceptance and N35 closeout

    Batch 10 is complete as a saved local checkpoint. The owner tested the live
    full-version app, accepted its functionality, requested further interactive
    testing stop, and confirmed successful scheduled availability maintenance.
    GitHub independently records successful push and workflow-dispatch runs on main.

    This batch closes N35 **with disclosed limitations**, not by claiming every
    original qualification was measured. Its explicit acceptance exception changes
    only the known unmeasured manual qualification rows from blocking to warning;
    their `passed` values remain false and their original records remain in details.
    Actual failures and automated regressions cannot be waived by this mechanism.
    The four local dependency-version warnings also remain. The original numerical
    limits in the validation configuration are unchanged.

    Live URL: https://fhtw-painting-restoration-main.streamlit.app/
    Repository/checker reference: e2b54a695a99ace715adbaee8a7ff21f7a407780.
    This reference is not independent attestation of the server's checkout SHA.
    Actions verified the Foyer, visitor dialog and Case Explorer evidence in Linux
    Chromium; this is not a full clean-Linux reproduction of the application.
    The old pilot URL has not been renamed or redirected.

    Replace the empty trailing cell 60 with this Markdown cell and append 61–65.
    Keep 60 and 65 as Markdown. Save before executing 61–64. No earlier notebook
    batch needs rerunning; these cells load the persisted checkpoint, not old kernel
    variables. No live browser tests, uploads, commits or scientific recomputation
    are performed by these cells.
    ''',"markdown"),cell('''
    import importlib
    import json
    import subprocess
    import sys
    from pathlib import Path
    import pandas as pd

    B11_ROOT = Path.cwd().resolve()
    if B11_ROOT.name == "notebooks":
        B11_ROOT = B11_ROOT.parent
    if not (B11_ROOT / "tools/n35_batch11.py").is_file():
        raise RuntimeError("Run from the project root or its notebooks directory.")
    sys.path.insert(0, str(B11_ROOT / "tools"))
    import n35_batch11 as b11
    b11 = importlib.reload(b11)
    B11_PRIOR, B11_FRAME, B11_EVIDENCE = b11.load_checkpoint()
    B11_BEFORE = b11.source_fingerprint()
    B11_PRIOR_SHA = b11.sha256_file(B11_ROOT / b11.b10.OUTPUT / b11.b10.FILES[2])
    print("Verified checkpoint:", B11_PRIOR["run_id"], B11_PRIOR["run_status"])
    print("Accepted live URL:", B11_EVIDENCE["url"])
    display(pd.DataFrame(B11_EVIDENCE["verified_actions_runs"])[
        ["id", "event", "branch", "conclusion", "checker_status", "url"]])
    '''),cell('''
    # Explicit owner-directed acceptance; this is NOT a claim that missing tests passed.
    B11_ACCEPT_DISCLOSED_LIMITATIONS = True
    B11_REVIEW = b11.accepted_checks(B11_FRAME,
        accept_disclosed_limitations=B11_ACCEPT_DISCLOSED_LIMITATIONS)
    print(B11_EVIDENCE["user_acceptance"]["disposition"])
    for limitation in B11_EVIDENCE["remaining_limitations"]:
        print("-", limitation)
    display(B11_REVIEW.to_dataframe().query("passed == False")[[
        "validation_stage", "check_id", "severity", "observed", "passed"]])
    print("False warning rows are intentionally retained; automated blocking failures still stop closeout.")
    '''),cell('''
    # Small offline closeout tests only: temporary files, no live dashboard sweep.
    B11_TESTS = subprocess.run([sys.executable, "-m", "unittest", "discover",
        "-s", "tests", "-p", "test_n35_batch11.py", "-v"],
        cwd=B11_ROOT, capture_output=True, text=True, timeout=120)
    print(B11_TESTS.stdout)
    print(B11_TESTS.stderr)
    if B11_TESTS.returncode != 0:
        raise RuntimeError("Closeout-helper tests failed; no canonical files written.")
    if b11.source_fingerprint() != B11_BEFORE:
        raise RuntimeError("Source changed since setup; inspect before continuing.")
    B11_REVIEW.raise_for_blocking()
    print("Closeout helper passed. Ready for owner-executed persistence with disclosed limitations.")
    '''),cell('''
    if B11_TESTS.returncode != 0:
        raise RuntimeError("Run the closeout tests successfully first.")
    B11_PERSISTED = b11.persist(before=B11_BEFORE, previous_manifest_sha=B11_PRIOR_SHA,
        accept_disclosed_limitations=B11_ACCEPT_DISCLOSED_LIMITATIONS)
    display(B11_PERSISTED)
    print("N35 completed with disclosed limitations. Four canonical outputs saved; previous run backed up.")
    print("Save this notebook, refresh the inventory, then prepare the scoped closeout commit.")
    print("N36 may consolidate the accepted record, retaining all warnings and acceptance exceptions.")
    '''),cell('''
    ## N35 handoff — completed with disclosed limitations

    The closeout manifest records `run_status: completed`, the accepted live URL,
    successful availability runs and the owner's acceptance. Artifacts have
    `validation_status: warning`; `all_planned_checks_verified` remains false.
    Completion means accepted delivery, not perfect measured compliance. N36
    must preserve that distinction, the prior checkpoint and the N29 historical
    discrepancy; no scientific evidence is recomputed or retrospectively rewritten.

    Save the notebook after cell 64. From the project root, use the existing
    project environment to run `python -c "import yaml; print(yaml.__version__)"`
    then `python tools/build_project_inventory.py --root . --out-dir outputs/inventory`.
    Require both `summary.read_error_file_count` and `summary.read_error_count`
    to be zero. Use the incremental default; do not request a full no-reuse scan.
    Share cell 64's result and the inventory summary before the scoped commit.

    No new HF bundle is created by closeout. Next: commit the N35 record, then
    prepare N36's Controlled-300 consolidation. N36 has not been executed or
    certified here. Minor cleanup and README work can follow that consolidation.
    ''',"markdown")]


def main():
    notebook=ROOT/"notebooks/35_dashboard_and_deployment_validation.ipynb"
    original=notebook.read_bytes()
    cells=build_cells()
    for i,c in enumerate(cells,60):
        if c["cell_type"]=="code": ast.parse(c["source"],filename=f"N35 cell {i}")
    target=ROOT/".codex_tmp/n35_batch11/N35_batch11_cells_60_65.html"
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(render(cells,start=60,title="N35 · Batch 11 acceptance closeout · cells 60–65",
        notice="Replace the empty trailing cell 60, then append 61–65. Keep 60 and 65 as Markdown. Save, then execute 61–64. No earlier batch rerun. Closeout preserves unmeasured qualifications as false warning rows under explicit owner acceptance."),encoding="utf-8")
    assert notebook.read_bytes()==original
    print(target)
    print("Notebook unchanged:",hashlib.sha256(original).hexdigest())


if __name__=="__main__": main()
