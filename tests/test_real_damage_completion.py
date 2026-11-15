"""Finalization tests on copies of the accepted Batch 7 evidence, never originals."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from restoration_eval import real_damage_completion as completion
from restoration_eval.manifests import build_artifact_record, sha256_file


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.actual = Path(__file__).resolve().parents[1]
        self.temp = tempfile.TemporaryDirectory(prefix="d03-completion-", dir=self.actual / ".codex_tmp")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / ".git").mkdir()
        (self.root / "notebooks").mkdir()
        (self.root / "src/restoration_eval").mkdir(parents=True)
        self.relative = Path("outputs/d03_real_damage_dataset_preparation")
        self.output = self.root / self.relative
        shutil.copytree(self.actual / self.relative, self.output)
        # Tests start from Batch 7 even if the user has subsequently completed D03.
        journal = self.output / "work/completion_commit"
        if (journal / "transaction.json").exists():
            for name in completion.METADATA_PATHS:
                shutil.copyfile(journal / "before" / name, self.output / name)
            shutil.rmtree(journal)
        self.manifest = json.loads((self.output / completion.METADATA_PATHS[2]).read_text(encoding="utf-8"))
        for row in self.manifest["inputs"]:
            target = self.root / row["relative_path"]
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if row["input_key"] == "inventory":
                target.write_text("test inventory\n", encoding="utf-8")
            else:
                shutil.copyfile(self.actual / row["relative_path"], target)
        for relative in ("config/datasets/real_damage_completion.yaml", "src/restoration_eval/real_damage_completion.py"):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.actual / relative, target)
        self.policy = self.root / "config/datasets/real_damage_completion.yaml"
        # Production inventory integration is verified separately on the live saved inputs.
        self.inventory = patch.object(completion, "audit_inventory_inputs", return_value=(
            {"inventory_run_id": "inventory_test"}, pd.DataFrame([{"passed": True}])))
        self.inventory.start()
        self.addCleanup(self.inventory.stop)

    def test_completion_preserves_science_and_is_idempotent(self):
        immutable = {p: sha256_file(self.root / p) for p in self.manifest["canonical_file_checksums"]}
        result = completion.complete_real_damage_dataset(self.root, self.policy)
        self.assertEqual(result["validation"].summary()["passed_count"], 379)
        self.assertEqual(result["run_manifest"]["run_status"], "completed")
        self.assertTrue(result["run_manifest"]["completion_gate_passed"])
        self.assertTrue(result["run_manifest"]["downstream_ready"])
        self.assertEqual(result["run_manifest"]["run_id"], self.manifest["run_id"])
        self.assertEqual(result["run_manifest"]["data_fingerprint"], self.manifest["data_fingerprint"])
        self.assertEqual(immutable, {p: sha256_file(self.root / p) for p in immutable})
        validation = result["artifacts"].set_index("artifact_key").loc["validation"]
        fresh = build_artifact_record(artifact_key="validation", producer_notebook="d03_real_damage_dataset_preparation",
            path=self.output / "validation/checks.csv", artifact_type="validation_table", artifact_role="audit_reporting",
            schema_version="validation_checks.v1", dataset_scope="real_damage_10", experiment_id="real_damage_reviewed_mask",
            row_count=379, project_root=self.root)
        self.assertEqual(validation["checksum"], fresh["checksum"])
        self.assertEqual(validation["artifact_id"], fresh["artifact_id"])
        times = {p: p.stat().st_mtime_ns for p in self.output.rglob("*") if p.is_file()}
        again = completion.complete_real_damage_dataset(self.root, self.policy)
        self.assertEqual(result["run_manifest"], again["run_manifest"])
        self.assertEqual(times, {p: p.stat().st_mtime_ns for p in times})
        self.assertEqual(sum(p.is_file() for p in (self.output / "work").rglob("*")), again["run_manifest"]["retained_work_files"])

    def test_tampering_blocks_without_metadata_changes(self):
        before = {p: (self.output / p).read_bytes() for p in completion.METADATA_PATHS}
        target = self.output / "images/masks/rdmask_rd001.png"
        data = target.read_bytes()
        target.write_bytes(data + b"tampered")
        with self.assertRaisesRegex(ValueError, "Scientific artifact changed"):
            completion.complete_real_damage_dataset(self.root, self.policy)
        target.write_bytes(data)
        target = self.root / "config/experiments/lama.yaml"
        target.write_bytes(target.read_bytes() + b"\n# changed\n")
        with self.assertRaisesRegex(ValueError, "scientific input changed"):
            completion.complete_real_damage_dataset(self.root, self.policy)
        self.assertEqual(before, {p: (self.output / p).read_bytes() for p in before})

    def test_interrupted_metadata_write_rolls_back_and_retries(self):
        before = {p: (self.output / p).read_bytes() for p in completion.METADATA_PATHS}
        original_replace = completion._replace
        failed = False

        def fail_once(path, content):
            nonlocal failed
            if path == self.output / "manifests/artifacts.csv" and not failed:
                failed = True
                raise OSError("simulated disk interruption")
            original_replace(path, content)

        with patch.object(completion, "_replace", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "simulated"):
                completion.complete_real_damage_dataset(self.root, self.policy)
        self.assertEqual(before, {p: (self.output / p).read_bytes() for p in before})
        # Simulate a process exit after replacing only validation metadata.
        recovery = self.output / "work/completion_commit"
        shutil.copyfile(recovery / "after/validation/checks.csv", self.output / "validation/checks.csv")
        result = completion.complete_real_damage_dataset(self.root, self.policy)
        self.assertTrue(result["run_manifest"]["completion_gate_passed"])


if __name__ == "__main__":
    unittest.main()
