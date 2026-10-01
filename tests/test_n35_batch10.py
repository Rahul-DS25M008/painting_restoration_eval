"""Batch 10 generation and persistence guard tests; never write canonical N35."""
import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import n35_batch10 as b10
from prepare_n35_batch10_cells import build_cells, build_checkpoint_cells
from restoration_eval.validation import ValidationCollector, ValidationFailure


class Batch10Tests(unittest.TestCase):
    def test_checkpoint_cells_parse_and_do_not_invent_passes(self):
        cells = build_checkpoint_cells({})
        self.assertEqual([c["cell_type"] for c in cells], ["markdown", "code", "code", "code", "markdown"])
        for c in cells:
            if c["cell_type"] == "code": ast.parse(c["source"])
        self.assertIn('"passed": None', cells[1]["source"])
        self.assertNotIn('b10_record("final_gate"', cells[2]["source"])

    def test_checkpoint_keeps_unknown_gates_blocking_without_mutating_collector(self):
        original = ValidationCollector()
        saved, pending = b10.qualification_record(original, {}, "User approves local behavior")
        self.assertEqual(set(pending), set(b10.MANUAL_GATES))
        self.assertEqual(len(saved.blocking_failures), len(b10.MANUAL_GATES))
        self.assertFalse(saved.summary()["overall_passed"])
        self.assertEqual(len(original.checks), 0)
        self.assertTrue(all(r.observed == "pending_not_verified" for r in saved.checks))

    def test_default_readiness_still_requires_manual_evidence(self):
        with self.assertRaisesRegex(ValueError, "unverified"):
            b10.qualification_record(ValidationCollector(), {})

    def test_user_approval_cannot_override_explicit_failure(self):
        with self.assertRaisesRegex(ValueError, "failures require resolution"):
            b10.qualification_record(ValidationCollector(),
                {b10.MANUAL_GATES[0]: {"passed":False, "evidence":"clipped controls"}}, "looks good")

    def test_automated_blocker_cannot_be_deferred(self):
        collector = ValidationCollector()
        collector.add(validation_stage="batch_10", check_id="regression", check_description="test",
            severity="blocking", expected=True, observed=False, passed=False)
        with self.assertRaises(ValidationFailure):
            b10.qualification_record(collector, {}, "looks good")

    def test_detailed_manual_pass_preserved(self):
        key = b10.MANUAL_GATES[0]
        saved, pending = b10.qualification_record(ValidationCollector(),
            {key:{"passed":True,"evidence":"Direct viewport observation"}}, "looks good")
        self.assertNotIn(key, pending)
        self.assertTrue(next(r for r in saved.checks if r.check_id==key).passed)

    def test_exact_helper_delta_reconciliation_only(self):
        before = {"streamlit_app.py":"app", "tools/n35_batch10.py":"old"}
        after = {**before, "tools/n35_batch10.py":"new"}
        with patch.object(b10, "fingerprint", return_value=after):
            current, delta = b10.checkpoint_fingerprint(before, {"tools/n35_batch10.py":["old","new"]})
            self.assertEqual(current, after)
            self.assertEqual(len(delta), 1)
            with self.assertRaises(ValueError): b10.checkpoint_fingerprint(before, {})
        with patch.object(b10, "fingerprint", return_value={**after,"streamlit_app.py":"changed"}):
            with self.assertRaises(ValueError):
                b10.checkpoint_fingerprint(before, {"tools/n35_batch10.py":["old","new"]})
            with self.assertRaises(ValueError):
                b10.checkpoint_fingerprint(before, {"streamlit_app.py":["app","changed"]})

    def test_partial_persistence_records_real_pending_state(self):
        import hashlib
        import pandas as pd
        from restoration_eval import manifests
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/"outputs/inventory").mkdir(parents=True)
            (root/"outputs/inventory/inventory_run.json").write_text('{"run_id":"test"}')
            (root/"config/evaluation").mkdir(parents=True)
            (root/"config/evaluation/dashboard_validation.yaml").write_text("test: true")
            def artifact(**kwargs):
                return {"checksum":hashlib.sha256(Path(kwargs["path"]).read_bytes()).hexdigest(),
                    "validation_status":kwargs["validation_status"]}
            def write_json(path, value): Path(path).write_text(json.dumps(value))
            def write_csv(path, value): pd.DataFrame(value).to_csv(path,index=False)
            with patch.object(b10,"ROOT",root), patch.object(b10,"fingerprint",return_value={}), \
                    patch.object(b10.room,"notebook_source_digest",return_value="notebook-source"), \
                    patch.object(manifests,"build_run_manifest",side_effect=lambda **kw:{k:v for k,v in kw.items() if k!="project_root"}), \
                    patch.object(manifests,"build_artifact_record",side_effect=artifact), \
                    patch.object(manifests,"write_run_manifest",side_effect=write_json), \
                    patch.object(manifests,"write_artifact_manifest",side_effect=write_csv):
                result = b10.persist(ValidationCollector(),
                    {"n29":{"passed":True,"disposition":"retained"}}, {}, {}, checkpoint_approval="User signoff")
            output = root/b10.OUTPUT
            run = json.loads((output/b10.FILES[2]).read_text())
            checks = pd.read_csv(output/b10.FILES[0])
            self.assertEqual(result["state"], "local_checkpoint_pending_qualification")
            self.assertEqual(run["run_status"], "partial")
            self.assertFalse(run["validation_summary"]["overall_passed"])
            self.assertFalse(run["local_checkpoint"]["n36_may_start"])
            self.assertEqual(run["deployment"]["url"], "")
            self.assertTrue(all(r["validation_status"]=="pending" for r in run["outputs"]))
            self.assertFalse(checks.passed.any())
            self.assertIn("NOT readiness-certified", (output/b10.FILES[1]).read_text())
            self.assertEqual({p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()},set(b10.FILES))

    def test_fresh_failure_keeps_structured_diagnostics(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def run(command, **kwargs):
                token = command[command.index("--request-id")+1]
                path = root/".codex_tmp/n35_batch10_audit/deployment_suite_trust_portrait.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps({"request_id":token,"passed":False,"run":28,
                    "failures":0,"errors":0,"integrity_changes":{"notebook_source_changed":True}}))
                return SimpleNamespace(returncode=1,stdout="",stderr="")
            with patch.object(b10,"ROOT",root),patch.object(b10.subprocess,"run",side_effect=run):
                result = b10.run_check("suite","trust_portrait")
            self.assertFalse(result["passed"])
            self.assertEqual(result["run"],28)
            self.assertTrue(result["integrity_changes"]["notebook_source_changed"])

    def test_stale_success_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            path=root/".codex_tmp/n35_batch10_audit/deployment_suite_trust_portrait.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"request_id":"old","passed":True}))
            with patch.object(b10,"ROOT",root),patch.object(b10.subprocess,"run",
                    return_value=SimpleNamespace(returncode=0,stdout="",stderr="")):
                self.assertFalse(b10.run_check("suite","trust_portrait")["passed"])

    def test_complete_cells_parse(self):
        cells = build_cells()
        self.assertEqual(len(cells),11)
        for cell in cells:
            if cell["cell_type"]=="code": ast.parse(cell["source"])

    def test_manual_observations_never_default_to_pass(self):
        self.assertFalse(any(r["passed"] for r in b10.manual_checks({})))
        self.assertFalse(any(r["passed"] for r in b10.manual_checks({k:{"passed":True,"evidence":""} for k in b10.MANUAL_GATES})))

    def test_original_frozen_sources_are_not_rebaselined(self):
        result = b10.visual_delta_checks()
        self.assertTrue(result["passed"],result)

    def test_no_notebook_execution_or_publication_in_cells(self):
        source="\n".join(c["source"] for c in build_cells() if c["cell_type"]=="code")
        for token in ("nbclient", "nbconvert", "git push", "hf upload", "run all"):
            self.assertNotIn(token,source.lower())
        self.assertIn('"deployment_url":""',source)

    def fixture(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        stage=root/"stage"
        for name in b10.FILES:
            path=stage/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text("new",encoding="utf-8")
        target=root/"outputs/35_dashboard_and_deployment_validation"
        (target/"reports").mkdir(parents=True)
        (target/b10.FILES[1]).write_text("old",encoding="utf-8")
        return stage,target

    def test_promotion_preserves_old_run(self):
        stage,target=self.fixture()
        backup=b10.promote_directory(stage,target)
        self.assertEqual((Path(backup)/b10.FILES[1]).read_text(),"old")
        self.assertEqual({p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()},set(b10.FILES))

    def test_incomplete_staging_never_replaces_old_run(self):
        stage,target=self.fixture()
        (stage/b10.FILES[0]).unlink()
        with self.assertRaises(ValueError): b10.promote_directory(stage,target)
        self.assertEqual((target/b10.FILES[1]).read_text(),"old")

    def test_unsafe_target_rejected(self):
        stage,target=self.fixture()
        with self.assertRaises(ValueError): b10.promote_directory(stage,target.parent)

    def test_failed_promotion_restores_prior_run(self):
        stage,target=self.fixture()
        real=b10.os.replace
        def fail(source,destination):
            if Path(source)==stage: raise OSError("injected promotion failure")
            return real(source,destination)
        with patch.object(b10.os,"replace",side_effect=fail):
            with self.assertRaises(OSError): b10.promote_directory(stage,target)
        self.assertEqual((target/b10.FILES[1]).read_text(),"old")


if __name__=="__main__": unittest.main()
