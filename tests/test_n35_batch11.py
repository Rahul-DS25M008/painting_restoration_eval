"""Offline acceptance/persistence regression; never modifies canonical outputs."""
import ast
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import n35_batch11 as b11
from prepare_n35_batch11_cells import build_cells


def fixture_frame():
    rows=[dict(validation_stage="batch_10_checkpoint_gate",check_id="gate",check_description="checkpoint",
        severity="blocking",expected="True",observed="True",passed=True,details="")]
    rows += [dict(validation_stage="batch_11_qualification",check_id=k,check_description=k,
        severity="blocking",expected="verified",observed="pending_not_verified",passed=False,details="original evidence") for k in b11.b10.MANUAL_GATES]
    return pd.DataFrame(rows)


class CloseoutTests(unittest.TestCase):
    def test_cells_parse_and_do_not_run_live_checks(self):
        cells=build_cells()
        self.assertEqual(len(cells),6)
        self.assertEqual(cells[0]["cell_type"],"markdown")
        self.assertEqual(cells[-1]["cell_type"],"markdown")
        for c in cells:
            if c["cell_type"]=="code":
                ast.parse(c["source"])
                for forbidden in ("nbclient","git push","hf upload","playwright"):
                    self.assertNotIn(forbidden,c["source"])

    def test_acceptance_preserves_false_and_original_details(self):
        frame=fixture_frame()
        result=b11.accepted_checks(frame,accept_disclosed_limitations=True)
        self.assertEqual(len([c for c in result.checks if not c.passed]),10)
        self.assertEqual(len(result.blocking_failures),0)
        row=next(c for c in result.checks if not c.passed)
        self.assertEqual(row.severity,"warning")
        self.assertEqual(json.loads(row.details)["original_record"]["severity"],"blocking")
        self.assertEqual(frame.iloc[1].severity,"blocking")

    def test_no_implicit_acceptance(self):
        with self.assertRaises(ValueError): b11.accepted_checks(fixture_frame(),accept_disclosed_limitations=False)

    def test_automated_failure_not_waived(self):
        frame=fixture_frame()
        frame.loc[0,"passed"]=False
        with self.assertRaisesRegex(ValueError,"failure cannot be waived"):
            b11.accepted_checks(frame,accept_disclosed_limitations=True)

    def test_actual_manual_failure_not_waived(self):
        frame=fixture_frame()
        frame.loc[1,"observed"]="controls clipped"
        with self.assertRaisesRegex(ValueError,"actual manual failure"):
            b11.accepted_checks(frame,accept_disclosed_limitations=True)

    def test_missing_qualification_fails(self):
        with self.assertRaisesRegex(ValueError,"Missing qualification"):
            b11.accepted_checks(fixture_frame().iloc[:-1],accept_disclosed_limitations=True)

    def test_live_evidence_requires_both_successful_runs(self):
        evidence=json.loads((ROOT/b11.EVIDENCE).read_text())
        b11.verify_evidence(evidence)
        evidence["verified_actions_runs"][1]["conclusion"]="failure"
        with self.assertRaises(ValueError): b11.verify_evidence(evidence)

    def test_persistence_and_rerun_preserve_prior_records(self):
        # Copy only four compact checkpoint files into a disposable fake project.
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in (".git","src/restoration_eval","notebooks","config/publication"):
                (root/name).mkdir(parents=True,exist_ok=True)
            for name in b11.b10.FILES:
                target=root/b11.b10.OUTPUT/name
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/b11.b10.OUTPUT/name,target)
            shutil.copyfile(ROOT/b11.EVIDENCE,root/b11.EVIDENCE)
            manifest_path=root/b11.b10.OUTPUT/b11.b10.FILES[2]
            old=json.loads(manifest_path.read_text())
            before={r["path"]:r["lf_sha256"] for r in old["inputs"]}
            original_sha=b11.sha256_file(manifest_path)
            with patch.object(b11,"ROOT",root),patch.object(b11,"source_fingerprint",return_value=before), \
                    patch.object(b11.room,"notebook_source_digest",return_value="source-test"), \
                    patch.object(b11,"git_state",return_value={}):
                result=b11.persist(before=before,previous_manifest_sha=original_sha,accept_disclosed_limitations=True)
                final=json.loads(manifest_path.read_text())
                self.assertEqual(final["run_status"],"completed")
                self.assertFalse(final["deployment"]["all_planned_checks_verified"])
                self.assertEqual(final["deployment"]["tested_revision"],"")
                self.assertTrue(all(a["validation_status"]=="warning" for a in final["outputs"]))
                self.assertEqual(b11.sha256_file(Path(result["prior_run_backup"])/b11.b10.FILES[2]),original_sha)
                self.assertEqual(len(list((root/b11.b10.OUTPUT).rglob("*.csv"))),2)
                second=b11.persist(before=before,previous_manifest_sha=b11.sha256_file(manifest_path),accept_disclosed_limitations=True)
                self.assertEqual(second["summary"]["check_count"],result["summary"]["check_count"])
                with self.assertRaisesRegex(ValueError,"Checkpoint changed"):
                    b11.persist(before=before,previous_manifest_sha=original_sha,accept_disclosed_limitations=True)


if __name__=="__main__": unittest.main()
