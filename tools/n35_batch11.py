"""User-run N35 acceptance closeout. No browser checks, publication or inference."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import uuid
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import n35_batch10 as b10
import n35_room_validation as room
from restoration_eval.validation import ValidationCollector
from restoration_eval.manifests import (build_artifact_record, write_artifact_manifest,
    write_run_manifest, sha256_file, git_state)

EVIDENCE = "config/publication/n35_live_acceptance.json"
EXTRA = ("tools/n35_batch11.py", "tools/prepare_n35_batch11_cells.py",
         "tests/test_n35_batch11.py", EVIDENCE)


def source_fingerprint():
    return {**b10.fingerprint(), **{p:room.digest(ROOT/p, "lf_normalized") for p in EXTRA}}


def verify_evidence(evidence):
    if evidence["url"] != "https://fhtw-painting-restoration-main.streamlit.app/":
        raise ValueError("Unexpected accepted deployment URL")
    runs = evidence["verified_actions_runs"]
    if {r["event"] for r in runs} != {"push", "workflow_dispatch"}:
        raise ValueError("Both push and scheduled-dispatch evidence are required")
    for r in runs:
        if r["conclusion"] != "success" or r["branch"] != "main" or r["head_sha"] != evidence["reference_revision"]:
            raise ValueError("Failed or mismatched workflow evidence")
        if r["checker_status"] != "ready" or r["case_status"] != "ready":
            raise ValueError("Live readiness was not verified")
    if not evidence["user_acceptance"]["stop_further_checks"] or not evidence["remaining_limitations"]:
        raise ValueError("Explicit owner acceptance and limitations must be retained")


def accepted_checks(frame, *, accept_disclosed_limitations):
    """Only known unverified manual qualifications may become acceptance warnings."""
    if accept_disclosed_limitations is not True:
        raise ValueError("Owner acceptance of disclosed limitations is required")
    result = ValidationCollector()
    for row in frame.fillna("").to_dict("records"):
        if row["validation_stage"] == "batch_11_closeout":
            continue  # Rerun replaces only this helper's previous closeout checks.
        passed = str(row["passed"]).lower() == "true"
        known = row["validation_stage"] == "batch_11_qualification" and row["check_id"] in b10.MANUAL_GATES
        if known and not passed:
            if row["observed"] not in {"pending_not_verified", "owner_accepted_without_measurement"}:
                raise ValueError("An actual manual failure cannot be waived as missing evidence")
            if row["observed"] == "pending_not_verified":
                row["details"] = json.dumps({"original_record":row.copy(),
                    "disposition":"Owner explicitly accepts delivery without completing this measurement; NOT a test pass."})
            row.update(severity="warning", observed="owner_accepted_without_measurement")
        elif not passed and row["severity"] in {"blocking", "error"}:
            raise ValueError("An automated/unrecognized failure cannot be waived: " + row["check_id"])
        row["passed"] = passed
        result.add(**row)
    stages = {c.validation_stage for c in result.checks if c.passed}
    if "batch_10_checkpoint_gate" not in stages and "batch_10_final_gate" not in stages:
        raise ValueError("Successful Batch 10 prerequisite missing")
    for key in b10.MANUAL_GATES:
        if not any(c.validation_stage=="batch_11_qualification" and c.check_id==key for c in result.checks):
            raise ValueError("Missing qualification record: " + key)
    return result


def load_checkpoint():
    import pandas as pd
    base = ROOT / b10.OUTPUT
    if {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()} != set(b10.FILES):
        raise ValueError("Expected exactly four canonical N35 files")
    run = json.loads((base/b10.FILES[2]).read_text(encoding="utf-8"))
    if sha256_file(base/b10.FILES[3]) != run["artifact_manifest_checksum"]:
        raise ValueError("Prior artifact manifest checksum mismatch")
    expected = {b10.OUTPUT+"/"+b10.FILES[0], b10.OUTPUT+"/"+b10.FILES[1]}
    if {r["relative_path"] for r in run["outputs"]} != expected:
        raise ValueError("Unexpected checkpoint artifacts")
    for artifact in run["outputs"]:
        if sha256_file(ROOT/artifact["relative_path"]) != artifact["checksum"]:
            raise ValueError("Prior artifact checksum mismatch: " + artifact["relative_path"])
    current = source_fingerprint()
    for item in run["inputs"]:
        if current.get(item["path"]) != item["lf_sha256"]:
            raise ValueError("Validated source changed: " + item["path"])
    if set(current)-{r["path"] for r in run["inputs"]}-set(EXTRA):
        raise ValueError("Unexpected new validation/application inputs")
    evidence = json.loads((ROOT/EVIDENCE).read_text(encoding="utf-8"))
    verify_evidence(evidence)
    return run, pd.read_csv(base/b10.FILES[0], keep_default_na=False), evidence


def persist(*, before, previous_manifest_sha, accept_disclosed_limitations):
    """Atomically replace four owned files; preserve the entire previous run."""
    if source_fingerprint() != before:
        raise ValueError("Sources changed since Batch 11 setup")
    prior_path = ROOT/b10.OUTPUT/b10.FILES[2]
    if sha256_file(prior_path) != previous_manifest_sha:
        raise ValueError("Checkpoint changed since Batch 11 setup; rerun setup")
    old, frame, evidence = load_checkpoint()
    checks = accepted_checks(frame, accept_disclosed_limitations=accept_disclosed_limitations)
    for key, detail in (("checkpoint_integrity","Prior artifacts and validated sources match"),
                        ("live_availability","Push and scheduled-dispatch logs verify the limited live smoke"),
                        ("owner_acceptance","Owner accepted delivery with the explicitly unmeasured checks disclosed")):
        checks.add(validation_stage="batch_11_closeout", check_id=key, check_description=detail,
            severity="blocking", expected=True, observed=True, passed=True, details=evidence if key=="live_availability" else detail)
    checks.raise_for_blocking()
    now = datetime.now(timezone.utc).isoformat()
    parent = ROOT/".codex_tmp/n35_persistence"
    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="batch11-", dir=parent))
    for name in b10.FILES: (stage/name).parent.mkdir(parents=True, exist_ok=True)
    checks.to_dataframe().to_csv(stage/b10.FILES[0], index=False)
    report = "# N35 deployment acceptance closeout\n\nStatus: completed with disclosed limitations; not an all-tests-passed certificate.\n\n"
    report += "Accepted live URL: " + evidence["url"] + "\n\nRepository/checker reference: `" + evidence["reference_revision"] + "`. Server checkout SHA not independently attested.\n\n"
    report += "The owner accepted live functionality and requested further interactive testing stop. Known unmeasured qualification rows remain **false**, with warning severity and their original records preserved. This is an explicit acceptance exception, not measured compliance with the original validation plan.\n\n"
    report += "## Remaining limitations\n\n" + "\n".join("- "+x for x in evidence["remaining_limitations"]) + "\n\n"
    report += "## Deployment and acceptance evidence\n\n```json\n" + json.dumps(evidence,indent=2) + "\n```\n\n"
    report += "## Batch 10 record (preserved)\n\n" + (ROOT/b10.OUTPUT/b10.FILES[1]).read_text(encoding="utf-8") if old.get("origin")!="user_executed_batch_11" else "\nPrevious closeout is preserved in the transactional backup.\n"
    (stage/b10.FILES[1]).write_text(report,encoding="utf-8")
    artifacts=[]
    for key,name,schema in (("dashboard_checks",b10.FILES[0],"validation_checks.v1"),("deployment_readiness",b10.FILES[1],"deployment_readiness_report.v2")):
        row=build_artifact_record(artifact_key=key,producer_notebook="35",path=stage/name,
            artifact_type="validation" if key=="dashboard_checks" else "report",artifact_role="accepted_deployment_with_limitations",
            schema_version=schema,dataset_scope="controlled_300",validation_status="warning",project_root=ROOT)
        row["relative_path"]=b10.OUTPUT+"/"+name
        row["artifact_id"]="artifact_"+hashlib.sha256(f'{key}|{row["relative_path"]}|{row["checksum"]}'.encode()).hexdigest()[:20]
        artifacts.append(row)
    write_artifact_manifest(stage/b10.FILES[3],artifacts)
    run=copy.deepcopy(old)
    run.update(run_id="run_"+uuid.uuid4().hex,origin="user_executed_batch_11",run_status="completed",
        started_at_utc=now,completed_at_utc=now,outputs=artifacts,validation_summary=checks.summary(),
        inputs=[{"path":p,"lf_sha256":h} for p,h in before.items()],
        artifact_manifest_checksum=sha256_file(stage/b10.FILES[3]),
        notebook_source_sha256=room.notebook_source_digest(ROOT/"notebooks/35_dashboard_and_deployment_validation.ipynb"))
    run.update(git_state(ROOT))
    run["helper_versions"]["n35_batch11"]="1"
    run["known_limitations"]=list(dict.fromkeys(evidence["remaining_limitations"] +
        [x for x in old["known_limitations"] if "Historical manifest" in x or "Computational evidence" in x]))
    run["previous_run"]={"run_id":old["run_id"],"manifest_sha256":previous_manifest_sha,"run_status":old["run_status"]}
    run["deployment"]={"state":"owner_accepted_live_smoke_verified", "url":evidence["url"],
        "tested_revision":"", "reference_revision":evidence["reference_revision"],
        "server_revision_verified":False,"revision_basis":evidence["revision_basis"],
        "actions_runs":evidence["verified_actions_runs"],"all_planned_checks_verified":False}
    run["local_checkpoint"]["historical_only"]=True
    run["closeout"]={"state":"completed_with_disclosed_limitations", "owner_acceptance":evidence["user_acceptance"],
        "n35_delivery_complete":True,"n36_may_start":True,
        "n36_condition":"Preserve warnings, explicit acceptance exceptions and historical records; do not upgrade to full validation."}
    write_run_manifest(stage/b10.FILES[2],run)
    for item in artifacts:
        if sha256_file(stage/item["relative_path"].removeprefix(b10.OUTPUT+"/"))!=item["checksum"]:
            raise ValueError("Staged artifact drift")
    if source_fingerprint()!=before or sha256_file(prior_path)!=previous_manifest_sha:
        raise ValueError("Source/checkpoint changed while staging; nothing promoted")
    backup=b10.promote_directory(stage,ROOT/b10.OUTPUT)
    return {"run_id":run["run_id"],"status":run["run_status"],"closeout":run["closeout"]["state"],
        "url":evidence["url"],"summary":run["validation_summary"],"prior_run_backup":backup,
        "canonical_files":list(b10.FILES),"n36_may_start":True}
