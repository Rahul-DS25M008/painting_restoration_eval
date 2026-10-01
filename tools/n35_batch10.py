"""N35 Batch 10 gates and transactional persistence. Called by user-run cells."""
from __future__ import annotations
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import n35_room_validation as room
from n35_backend_delta import ALLOWED, baseline_source
from restoration_eval.evidence_transport import manifest, partition

OUTPUT = "outputs/35_dashboard_and_deployment_validation"
FILES = ("validation/dashboard_checks.csv", "reports/deployment_readiness.md", "manifests/run_manifest.json", "manifests/artifacts.csv")
MANUAL_GATES = ("desktop_1672x941_all_rooms", "tablet_1024x1366_all_rooms", "mobile_390x844_all_rooms",
    "keyboard_focus_and_dialogs", "firefox_reload_and_second_monitor", "same_room_no_document_reload",
    "cross_room_links_and_guided_tour", "downloaded_reports_open_self_contained", "browser_warm_navigation_p95",
    "remote_action_budget_and_peak_memory")


def fingerprint():
    paths = [ROOT / "streamlit_app.py", *sorted((ROOT / "src/restoration_eval").glob("*.py")),
             *sorted((ROOT / "streamlit_assets").rglob("*.css")), *sorted((ROOT / "streamlit_assets").rglob("*.js")),
             ROOT / "streamlit_assets/evidence/deployment/manifest.json", ROOT / "config/publication/n35_backend_delta.json",
             ROOT / "requirements.txt", ROOT / "config/evaluation/dashboard_validation.yaml",
             *sorted((ROOT / "tools").glob("n35*.py")), *sorted((ROOT / "tools").glob("prepare_n35*.py")),
             ROOT / "tests/test_evidence_transport.py", ROOT / "tests/test_n35_batch10.py"]
    return {p.relative_to(ROOT).as_posix(): room.digest(p, "lf_normalized") for p in paths}


def visual_delta_checks():
    checked = []
    for relative in ALLOWED:
        baseline_source(ROOT, relative)
        checked.append(relative)
    failures = []
    for name in ("model_gallery", "stability_lab", "trustworthiness", "focused_portrait", "research_archive", "museum_visit"):
        rows = room.verify_gallery_freeze(ROOT) if name == "model_gallery" else room.verify_later_room_freeze(ROOT, name) if name in {"stability_lab", "trustworthiness", "focused_portrait", "research_archive"} else room.verify_freeze(ROOT, f"config/publication/{name}_freeze.json")
        failures.extend(r for r in rows if r["expected"] != r["observed"])
    return dict(passed=not failures, scoped_backend_files=checked, freeze_failures=failures,
                note="Original visual freezes retained; exact backend deltas are separately fingerprinted and AST-scoped")


def run_check(action, room_id=None, missing_local=False, remote=False):
    request_id = uuid.uuid4().hex
    command = [sys.executable, str(ROOT / "tools/n35_deployment_checks.py"), action,
               "--request-id", request_id]
    if room_id: command += ["--group" if action=="suite" else "--room", room_id]
    if missing_local: command.append("--missing-local")
    if remote: command.append("--remote")
    print("Running", action, room_id or "", flush=True)
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=240)
    name = "deployment_" + (room_id if action == "opening" else action + ("_"+room_id if room_id else ""))
    path = ROOT / ".codex_tmp/n35_batch10_audit" / (name + ".json")
    # A failed check still has useful structured diagnostics. Accept them only
    # when tied to this invocation; an older successful receipt cannot pass.
    if path.is_file():
        result = json.loads(path.read_text())
        if result.get("request_id") == request_id:
            result["subprocess_returncode"] = process.returncode
            result["passed"] = bool(result.get("passed")) and process.returncode == 0
            if result.get("integrity_changes", {}).get("notebook_source_changed"):
                print("Notebook SOURCE changed during validation. Save all cells, then rerun without editing.", flush=True)
            return result
    if process.returncode:
        return dict(passed=False, action=action, room=room_id, error=process.stderr[-2500:], output=process.stdout[-3500:])
    return dict(passed=False, action=action, room=room_id,
                error="Subprocess did not produce a receipt for this invocation; stale evidence rejected")


def n29_check():
    from n35_final_audit import n29_provenance
    record = n29_provenance()
    record["passed"] = record["scope_only_correction"] and record["all_payloads_match"] and record["original_checksum_matches_crlf"]
    record["disposition"] = "Historical manifest discrepancy retained. All six payload groups independently verified; no historical checksum rewritten."
    return record


def closure_check():
    """Current N34 candidate routes and registered report closure; no whole-raster download."""
    from restoration_eval.dashboard_application import open_dashboard_package
    package = open_dashboard_package(ROOT)
    tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0"))
    registered = set()
    for name in manifest()["files"]:
        if name.startswith("routes/"): registered.update(partition(name))
    missing = set()
    candidates = 0
    for i in range(1, 301):
        shard = package.load_painting(f"p{i:03d}")
        for candidate in shard["candidates"]:
            candidates += 1
            for paths in candidate.get("asset_routes", {}).values():
                for path in paths:
                    if path not in tracked and path not in registered: missing.add(path)
        for case in shard["cases"]:
            for key in ("clean_image_path", "input_image_path", "mask_or_effect_path"):
                path = case.get(key)
                if path and path not in tracked and path not in registered: missing.add(path)
    reports = package.load_reports()["reports"]
    for report in reports:
        path = report.get("report_path")
        if path and path not in tracked and path not in registered: missing.add(path)
    return dict(passed=not missing and candidates==13879, candidates=candidates, reports=len(reports), missing=sorted(missing),
                scope="All N34 case inputs, candidate asset routes and report paths; remote byte samples are a separate gate")


def manual_checks(observations):
    result = []
    for key in MANUAL_GATES:
        value = observations.get(key, {})
        result.append(dict(check_id=key, passed=value.get("passed") is True and bool(value.get("evidence", "").strip()),
            evidence=value.get("evidence", ""), observed_at_utc=value.get("observed_at_utc", "")))
    return result


def checkpoint_fingerprint(before, approved_changes):
    """Reuse runtime receipts only across this exact validation-only closeout edit."""
    allowed = {"tools/n35_batch10.py", "tools/prepare_n35_batch10_cells.py", "tests/test_n35_batch10.py"}
    if set(approved_changes) - allowed:
        raise ValueError("Checkpoint reconciliation cannot approve application/configuration changes")
    current = fingerprint()
    changed = {p for p in set(before) | set(current) if before.get(p) != current.get(p)}
    for path in changed:
        if path not in approved_changes or approved_changes[path] != [before.get(path), current.get(path)]:
            raise ValueError("Unvalidated source change; rerun affected validation: " + path)
    return current, {p: approved_changes[p] for p in sorted(changed)}


def qualification_record(collector, manual, checkpoint_approval=None):
    """Pending qualifications stay blocking/false in the saved partial record."""
    from restoration_eval.validation import ValidationCollector
    collector.raise_for_blocking()
    failed = [k for k in MANUAL_GATES if manual.get(k, {}).get("passed") is False]
    if failed:
        raise ValueError("Reported browser/platform failures require resolution: " + repr(failed))
    observations = manual_checks(manual)
    pending = [r["check_id"] for r in observations if not r["passed"]]
    if pending and not (checkpoint_approval or "").strip():
        raise ValueError("Browser/platform observations remain unverified")
    saved = ValidationCollector()
    saved.extend(collector.checks)
    for row in observations:
        saved.add(validation_stage="batch_11_qualification", check_id=row["check_id"],
            check_description="Browser/platform qualification; required before N35 closeout",
            severity="blocking", expected="Verified direct observation/measurement",
            observed="verified" if row["passed"] else "pending_not_verified",
            passed=row["passed"], details=row)
    return saved, pending


def promote_directory(stage, destination):
    """Commit one complete directory; preserve the prior run for recovery."""
    stage, destination = Path(stage).resolve(), Path(destination).resolve()
    if destination.name != "35_dashboard_and_deployment_validation" or destination.parent.name != "outputs":
        raise ValueError("Persistence destination is not the exact N35 output directory")
    if {p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()} != set(FILES):
        raise ValueError("Expected exactly the four canonical N35 files")
    backup = stage.parent / ("previous-n35-" + uuid.uuid4().hex)
    destination.parent.mkdir(parents=True, exist_ok=True)
    existed = destination.exists()
    if existed:
        unexpected = {p.relative_to(destination).as_posix() for p in destination.rglob("*") if p.is_file()} - set(FILES)
        if unexpected: raise ValueError("Refusing to move unexpected N35 files: " + repr(unexpected))
        os.replace(destination, backup)
    try:
        os.replace(stage, destination)
    except BaseException:
        if existed: os.replace(backup, destination)
        raise
    return str(backup) if existed else None


def persist(collector, receipts, before, manual, *, checkpoint_approval=None):
    """Only explicit user execution invokes this; no publication or deployment."""
    from restoration_eval.manifests import build_run_manifest, build_artifact_record, write_run_manifest, write_artifact_manifest, sha256_file
    collector.raise_for_blocking()
    if fingerprint() != before: raise ValueError("Application changed during Batch 10; rerun validation")
    if not receipts or any(not r.get("passed") for r in receipts.values()): raise ValueError("Incomplete/failed automated gates")
    saved, pending = qualification_record(collector, manual, checkpoint_approval)
    stamp = datetime.now(timezone.utc).isoformat()
    run_id = "run_" + uuid.uuid4().hex
    staging_parent = ROOT / ".codex_tmp/n35_persistence"
    staging_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="staged-", dir=staging_parent))
    for path in FILES: (stage / path).parent.mkdir(parents=True, exist_ok=True)
    saved.to_dataframe().to_csv(stage / FILES[0], index=False)
    state = "local_checkpoint_pending_qualification" if pending else "local_ready_live_validation_pending"
    status = "Partial local checkpoint; NOT readiness-certified. Required qualifications remain pending." if pending else "Ready for deployment validation; NOT live-site certified."
    report = "# N35 local deployment readiness\n\nStatus: " + status + "\n\nDeployment URL: (not yet validated).\n\nBatch 11 must resolve every pending qualification and record the deployed revision, public URL, clean Linux runtime and live checks before N35 closeout or N36.\n\n"
    report += "## Local user signoff (qualitative only)\n\n" + (checkpoint_approval or "See direct observations below.") + "\n\nNo exact viewport, timing, resource or individual checklist pass is inferred from a general approval.\n\n"
    report += "## Pending qualifications (not passed)\n\n" + ("\n".join("- " + key for key in pending) or "None; live validation still pending.") + "\n\n"
    report += "## Automated receipts\n\n```json\n" + json.dumps(receipts, indent=2, default=str) + "\n```\n\n## Browser/platform observations\n\n```json\n" + json.dumps(manual, indent=2) + "\n```\n"
    (stage / FILES[1]).write_text(report, encoding="utf-8")
    artifacts = []
    for key, name, schema in (("dashboard_checks", FILES[0], "validation_checks.v1"), ("deployment_readiness", FILES[1], "deployment_readiness_report.v2")):
        row = build_artifact_record(artifact_key=key, producer_notebook="35", path=stage/name, artifact_type="validation" if key=="dashboard_checks" else "report", artifact_role="local_checkpoint" if pending else "local_deployment_readiness", schema_version=schema, dataset_scope="controlled_300", validation_status="pending" if pending else "passed", project_root=ROOT)
        row["relative_path"] = OUTPUT + "/" + name
        row["artifact_id"] = "artifact_" + hashlib.sha256(f'{key}|{row["relative_path"]}|{row["checksum"]}'.encode()).hexdigest()[:20]
        artifacts.append(row)
    write_artifact_manifest(stage/FILES[3], artifacts)
    inventory = json.loads((ROOT/"outputs/inventory/inventory_run.json").read_text())
    run = build_run_manifest(notebook_id="35", notebook_name="35_dashboard_and_deployment_validation", origin="user_executed_batch_10", run_status="partial", started_at_utc=stamp, completed_at_utc=stamp,
        inventory_run_id=inventory.get("inventory_run_id", inventory.get("run_id", "")), dataset_versions={"scope":"controlled_300","n34_release":"release_c5edf0d0ec99affbfa403726"},
        configuration_paths=["config/evaluation/dashboard_validation.yaml"], configuration_checksums_by_path={"config/evaluation/dashboard_validation.yaml":sha256_file(ROOT/"config/evaluation/dashboard_validation.yaml")},
        helper_versions={"n35_batch10":"2"}, inputs=[{"path":p,"lf_sha256":h} for p,h in before.items()], outputs=artifacts,
        expected_counts={"rooms":9,"candidates":13879,"canonical_files":4}, observed_counts={"rooms":9,"candidates":13879,"canonical_files":4}, validation_summary=saved.summary(),
        known_limitations=["Live deployment and clean Linux runtime untested; Batch 11 pending.", "Pending required qualifications: " + repr(pending), receipts["n29"]["disposition"], "Computational evidence is not conservation approval or historical truth."], project_root=ROOT,
        package_names=("streamlit","pandas","numpy","pyarrow","Pillow","PyYAML"), run_id=run_id)
    run["artifact_manifest_checksum"] = sha256_file(stage/FILES[3])
    run["notebook_source_sha256"] = room.notebook_source_digest(ROOT/"notebooks/35_dashboard_and_deployment_validation.ipynb")
    run["deployment"] = {"state":"not_yet_validated","url":"","tested_revision":"","next_batch":11}
    run["local_checkpoint"] = {"state":state, "user_approval":checkpoint_approval,
        "pending_qualifications":pending, "n35_complete":False, "n36_may_start":False}
    write_run_manifest(stage/FILES[2], run)
    # Verify all staged references before any canonical path is changed.
    for row in artifacts:
        name = row["relative_path"].removeprefix(OUTPUT+"/")
        if sha256_file(stage/name)!=row["checksum"]: raise ValueError("Staged artifact checksum drift")
    backup = promote_directory(stage, ROOT/OUTPUT)
    return dict(run_id=run_id, canonical_files=list(FILES), prior_run_backup=backup,
        state=state, pending_qualifications=pending, n35_complete=False)
