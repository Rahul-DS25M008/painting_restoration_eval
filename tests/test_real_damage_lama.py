"""D04 LaMa adapter tests use tiny synthetic PNGs; no study inference or weights."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
from PIL import Image
import yaml

from restoration_eval import real_damage_lama as r
from restoration_eval import real_damage_restoration as d04
from restoration_eval.manifests import sha256_file
from restoration_eval.validation import ValidationCollector, ValidationFailure


class RealDamageLamaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.main = d04.load_restoration_config(root / "config/experiments/real_damage_restoration.yaml")
        cls.policy = yaml.safe_load((root / "config/experiments/real_damage_lama.yaml").read_text())
        cls.baseline = r.lama.load_lama_config(root / "config/experiments/lama.yaml")

    def context(self, root):
        for rel in (".git", "src/restoration_eval", "notebooks", "inputs"):
            (root / rel).mkdir(parents=True)
        baseline = copy.deepcopy(self.baseline)
        baseline["execution"].update(target_width=16, target_height=16)
        rows = []
        for i in range(1, 11):
            pid = f"rd{i:03d}"
            image = np.full((16,16,3), (10, 90, 150), np.uint8)
            mask = np.zeros((16,16), np.uint8); mask[5:11,5:11] = 255
            ip, mp = root / f"inputs/{pid}.png", root / f"inputs/{pid}_mask.png"
            Image.fromarray(image).save(ip); Image.fromarray(mask).save(mp)
            rows.append(dict(painting_id=pid, case_id=f"case_{pid}", candidate_id=f"candidate_{pid}", model_id=r.MODEL,
                experiment_id="real_damage_10", input_image_path=ip.relative_to(root).as_posix(),
                mask_path=mp.relative_to(root).as_posix(), mask_or_effect_path=mp.relative_to(root).as_posix(),
                input_image_sha256=sha256_file(ip), mask_sha256=sha256_file(mp), mask_threshold=128,
                restored_path=f"images/restored/lama/case_{pid}/candidate_{pid}.png", candidate_role="primary",
                has_clean_reference=False, clean_image_path="", configuration_id=baseline["model"]["configuration_id"]))
        weight = root / "inputs/fake_weight.txt"; weight.write_text("fixture never loaded")
        return dict(root=root, output_root=root / "outputs" / d04.NOTEBOOK_STEM, policy=self.policy,
            baseline=baseline, config=self.main, worklist=pd.DataFrame(rows), validation=ValidationCollector(),
            stage_input_checksums={}, frozen_input_checksums={}, execution_fingerprint="fixture_execution",
            frozen={"readiness_fingerprint":"fixture_ready"}, environment=dict(model_artifact_path=str(weight),
                model_artifact_sha256=sha256_file(weight), iopaint_version="fixture", torch_version="fixture", effective_device="cuda"))

    @staticmethod
    def backend(ctx, staged, job, collect, progress):
        for row in staged.to_dict("records"):
            Image.fromarray(np.full((16,16,3), (200, 50, 30), np.uint8)).save(row["raw_output_path"])
            collect()
        job.update(status="completed", runtime_seconds=1.5, return_code=0)
        r._save(r._path(ctx, job["directory"]) / "job.json", job)

    def test_same_compositor_outside_preservation_and_verified_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
            records, reused = r.run_scope(ctx, [row], runner=self.backend, progress=lambda _:None)
            self.assertEqual(reused, 0)
            image, mask = r._inputs(ctx, row)
            expected = r.lama.masked_composite(image, np.full_like(image, (200,50,30)), mask)
            record = records[0]; actual = r.lama._load_rgb(ctx["root"] / record["restored_path"])
            np.testing.assert_array_equal(expected, actual)
            self.assertEqual(record["changed_outside_pixels"], 0)
            self.assertEqual(record["runtime_seconds"], "")
            self.assertFalse(record["has_clean_reference"])
            records2, reused = r.run_scope(ctx, [row], runner=Mock(side_effect=AssertionError("must reuse")))
            self.assertEqual(records, records2); self.assertEqual(reused, 1)

    def test_changed_input_output_raw_weight_and_code_block_resume(self):
        for mutation in ("input", "output", "raw", "weight", "code"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
                records, _ = r.run_scope(ctx, [row], runner=self.backend, progress=lambda _:None)
                record = records[0]
                if mutation == "code":
                    ctx["execution_fingerprint"] = "changed"
                else:
                    path = {"input": ctx["root"] / row["input_image_path"], "output": ctx["root"] / record["restored_path"],
                        "raw":ctx["root"] / record["raw_output_path"], "weight":Path(ctx["environment"]["model_artifact_path"])}[mutation]
                    path.write_bytes(b"tampered")
                with self.assertRaises(ValueError):
                    r.run_scope(ctx, [row], runner=Mock(side_effect=AssertionError("must not rerun")))

    def test_raw_and_image_recovered_after_interrupt_without_new_inference(self):
        for image_written in (False, True):
            with self.subTest(image_written=image_written), tempfile.TemporaryDirectory() as tmp:
                ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
                def interrupted(ctx, staged, job, collect, progress):
                    Image.fromarray(np.full((16,16,3), 120, np.uint8)).save(staged.iloc[0].raw_output_path)
                    if image_written:
                        original = r._save
                        def fail_receipt(path, value):
                            if "receipts" in path.parts:
                                raise KeyboardInterrupt()
                            original(path, value)
                        with patch.object(r, "_save", side_effect=fail_receipt):
                            collect()
                    raise KeyboardInterrupt()
                with self.assertRaises(KeyboardInterrupt):
                    r.run_scope(ctx, [row], runner=interrupted)
                records, reused = r.run_scope(ctx, [row], runner=Mock(side_effect=AssertionError("raw must recover")))
                self.assertEqual(records[0]["status"], "completed"); self.assertEqual(reused, 1)

    def test_unverified_output_and_path_escape_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
            output, _ = r._locations(ctx, row, "primary")
            output.parent.mkdir(parents=True); output.write_bytes(b"unknown")
            with self.assertRaisesRegex(ValueError, "Unverified"):
                r.run_scope(ctx, [row], runner=self.backend)
            self.assertEqual(output.read_bytes(), b"unknown")
            row["restored_path"] = "../../escape.png"
            with self.assertRaises(ValueError):
                r.run_scope(ctx, [row], runner=self.backend)

    def test_partial_failure_only_retries_unfinished_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); rows = ctx["worklist"].iloc[:2].to_dict("records")
            calls = []
            def partial(ctx, staged, job, collect, progress):
                calls.append(staged.candidate_id.tolist())
                self.backend(ctx, staged.iloc[:1], job, collect, progress)
            records, _ = r.run_scope(ctx, rows, runner=partial, progress=lambda _:None)
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[1], [rows[1]["candidate_id"]])
            self.assertTrue(all(x["status"] == "completed" for x in records))

    def test_full_stage_preserves_telea_and_logs_group_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp))
            path = r._path(ctx, self.main["outputs"]["candidates"])
            r._save(path, pd.DataFrame([dict(model_id="opencv_telea", candidate_id="telea_fixture", status="completed", restored_sha256="preserved", runtime_seconds=.123)]))
            r.run_smoke(ctx, runner=self.backend, progress=lambda _:None)
            r.run_candidates(ctx, runner=self.backend, progress=lambda _:None)
            r.validate_results(ctx)
            stored = pd.read_csv(path)
            self.assertEqual(len(stored), 11)
            self.assertEqual(stored.loc[stored.model_id.eq("opencv_telea"), "restored_sha256"].item(), "preserved")
            self.assertEqual(ctx["summary"]["recorded_command_runtime_seconds"], 1.5)
            self.assertEqual(ctx["summary"]["command_groups"], 1)
            self.assertEqual(ctx["summary"]["completed_candidates"], 10)
            self.assertFalse(ctx["summary"]["notebook_completion_gate_passed"])
            r.run_smoke(ctx, runner=Mock(side_effect=AssertionError("must reuse")), progress=lambda _:None)
            r.run_candidates(ctx, runner=Mock(side_effect=AssertionError("must reuse")), progress=lambda _:None)
            r.validate_results(ctx)
            self.assertEqual(ctx["summary"]["reused_candidates"], 10)
            self.assertEqual(ctx["summary"]["recorded_command_runtime_seconds"], 1.5)

    def test_missing_raw_outputs_fail_gate_with_bounded_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); ctx["smoke_passed"] = True
            backend = Mock()
            r.run_candidates(ctx, runner=backend, progress=lambda _:None)
            self.assertEqual(backend.call_count, 2)
            self.assertTrue(ctx["records"].status.eq("failed").all())
            with self.assertRaises(ValidationFailure):
                r.validate_results(ctx)

    def test_repeatability_uses_full_canvas_and_baseline_tolerance(self):
        a = np.zeros((16,16,3), np.uint8); b = a.copy(); b[0,0,0] = 1
        tolerance = self.baseline["smoke"]["repeatability_tolerance"]
        result = r.repeatability(a,b,tolerance,False)
        self.assertTrue(result["passed"])
        self.assertEqual(result["different_pixel_fraction"], 1/256)
        b[0,0,0] = 2
        self.assertFalse(r.repeatability(a,b,tolerance,False)["passed"])
        b[:] = 1
        self.assertFalse(r.repeatability(a,b,tolerance,False)["passed"])

    def test_running_prior_job_blocks_second_gpu_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
            r.run_scope(ctx, [row], runner=self.backend, progress=lambda _:None)
            job = r._jobs(ctx)[0]; job.update(status="running", pid=123, process_created_at=456.)
            r._save(r._path(ctx, job["directory"]) / "job.json", job)
            process = Mock(); process.create_time.return_value = 456.; process.is_running.return_value = True
            with patch.object(r.psutil, "Process", return_value=process), self.assertRaisesRegex(ValueError, "still running"):
                r.run_scope(ctx, [row], runner=Mock(side_effect=AssertionError("blocked")))

    def test_command_interrupt_stops_own_child_and_records_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp))
            directory = r._path(ctx, "work/lama/jobs/interrupt_fixture")
            (directory / "logs").mkdir(parents=True)
            job = dict(directory="work/lama/jobs/interrupt_fixture", job_id="interrupt_fixture", scope="primary")
            child = Mock(); child.pid = 123; child.poll.return_value = None
            inspector = Mock(); inspector.create_time.return_value = 456.
            with patch.object(r.lama, "build_iopaint_command", return_value=["fixture"]), patch.object(r.subprocess, "Popen", return_value=child), patch.object(r.psutil, "Process", return_value=inspector):
                with self.assertRaises(KeyboardInterrupt):
                    r._run_command(ctx, pd.DataFrame(), job, Mock(side_effect=KeyboardInterrupt()), lambda _:None)
            child.terminate.assert_called_once()
            self.assertEqual(r._read(directory / "job.json")["status"], "interrupted")
            self.assertIn("runtime_seconds", job)


if __name__ == "__main__":
    unittest.main()
