"""Exercise the real N12A worker protocol with a fake generator, never study inference."""
import copy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
from PIL import Image
import yaml

from restoration_eval import real_damage_hint as r
from restoration_eval import restoration_hint_production_worker as worker
from restoration_eval.validation import ValidationCollector, ValidationFailure


class RealDamageHintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.main = r.d04.load_restoration_config(root / "config/experiments/real_damage_restoration.yaml")
        cls.policy = yaml.safe_load((root / "config/experiments/real_damage_hint.yaml").read_text())
        cls.baseline = r.hint.load_hint_config(root / "config/experiments/hint.yaml")

    def context(self,root):
        for rel in (".git","src/restoration_eval","notebooks","inputs","fake_repository"):
            (root / rel).mkdir(parents=True)
        rows = []
        image = np.full((768,768,3),(40,90,170),np.uint8)
        mask = np.zeros((768,768),np.uint8); mask[100:180,100:180] = 255
        for i in range(1,11):
            pid = f"rd{i:03d}"; ip = root / f"inputs/{pid}.png"; mp = root / f"inputs/{pid}_mask.png"
            Image.fromarray(image).save(ip); Image.fromarray(mask).save(mp)
            rows.append(dict(painting_id=pid,case_id=f"case_{pid}",candidate_id=f"candidate_{pid}",model_id=r.MODEL,
                experiment_id="real_damage",input_image_path=ip.relative_to(root).as_posix(),mask_path=mp.relative_to(root).as_posix(),
                input_image_sha256=r.sha256_file(ip),mask_sha256=r.sha256_file(mp),mask_threshold=128,seed="2026",
                restored_path=f"images/restored/hint_places2/case_{pid}/candidate_{pid}.png",candidate_role="primary",
                has_clean_reference=False,clean_image_path="",configuration_id=self.baseline["model"]["configuration_id"]))
        weight = root / "inputs/fake_weight.txt"; weight.write_text("fixture never loaded")
        asset = dict(repository_path=str(root / "fake_repository"),checkpoint_path=str(weight),
            checkpoint_sha256=r.sha256_file(weight),actual_repository_revision="fixture_revision")
        policy = copy.deepcopy(self.policy)
        policy["expected_load_audit"] = {k:v for k,v in self.load_audit().items() if k != "model_load_seconds"}
        return dict(root=root,output_root=root / "outputs" / r.d04.NOTEBOOK_STEM,policy=policy,
            config=self.main,baseline=copy.deepcopy(self.baseline),worklist=pd.DataFrame(rows),asset=asset,
            assets=[dict(path=str(weight),sha256=r.sha256_file(weight))],stage_input_checksums={},frozen_input_checksums={},
            validation=ValidationCollector(),execution_fingerprint="fixture_execution",frozen={"readiness_fingerprint":"fixture_ready"})

    @staticmethod
    def fake_torch():
        return SimpleNamespace(manual_seed=lambda _:None,device=lambda x:x,
            cuda=SimpleNamespace(is_available=lambda:True,manual_seed_all=lambda _:None,empty_cache=lambda:None,
                reset_peak_memory_stats=lambda:None,max_memory_allocated=lambda:1234),
            backends=SimpleNamespace(cudnn=SimpleNamespace(benchmark=False,deterministic=True)))

    @staticmethod
    def infer(generator,row,device):
        with Image.open(row["input_image_path"]) as pil:
            source = np.asarray(pil.convert("RGB"))
        with Image.open(row["mask_path"]) as pil:
            missing = (np.asarray(pil) >= int(row["mask_threshold"])).astype(np.uint8)
        return np.full_like(source,(180,70,20)),missing,source

    @staticmethod
    def load_audit():
        return dict(model_load_seconds=.1,matched_state_keys=2,model_state_key_count=2,missing_state_keys=0,unexpected_state_keys=0)

    def backend(self,ctx,job,collect,progress):
        directory = r._path(ctx,job["directory"])
        payload = r._read(directory / "worker_job.json")
        with patch.dict(sys.modules,{"torch":self.fake_torch()}), patch.object(worker,"_load_generator",return_value=(object(),self.load_audit())), patch.object(worker,"_infer",side_effect=self.infer), patch("builtins.print"):
            result = worker.execute_job(payload)
        job.update(status="completed" if result["status"] == "completed" else "failed",runtime_seconds=1.5,return_code=0 if result["status"] == "completed" else 1)
        r._save(directory / "job.json",job)
        collect()

    def test_existing_worker_protocol_and_compositor_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
            records,reused = r.run_scope(ctx,[row],runner=self.backend,progress=lambda _:None)
            self.assertEqual(reused,0); record = records[0]
            image,mask = r._inputs(ctx,row)
            expected = r.exact_mask_composite(np.full_like(image,(180,70,20)),image,(mask > 0).astype(np.uint8))
            with Image.open(ctx["root"] / record["restored_path"]) as pil:
                np.testing.assert_array_equal(np.asarray(pil),expected)
            self.assertEqual(record["changed_outside_pixels"],0)
            self.assertEqual(record["generator_version"],worker.WORKER_VERSION)
            job = r._jobs(ctx)[0]; payload = r._read(r._path(ctx,job["directory"]) / "worker_job.json")
            self.assertEqual(payload["model"],self.baseline["model"])
            self.assertEqual(payload["candidates"][0]["clean_image_path"],"")
            self.assertEqual(payload["candidates"][0]["seed"],2026)
            self.assertEqual(payload["execution"],{**self.baseline["execution"],**self.policy["worker_overrides"]})
            cached,reused = r.run_scope(ctx,[row],runner=Mock(side_effect=AssertionError("must reuse")))
            self.assertEqual(cached,records); self.assertEqual(reused,1)

    def test_source_output_worker_weight_and_code_changes_block_reuse(self):
        for mutation in ("input","output","worker","weight","code","job"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
                records,_ = r.run_scope(ctx,[row],runner=self.backend,progress=lambda _:None)
                record = records[0]
                if mutation == "code":
                    ctx["execution_fingerprint"] = "changed"
                else:
                    target = {"input":ctx["root"] / row["input_image_path"],"output":ctx["root"] / record["restored_path"],
                        "worker":ctx["root"] / record["worker_output_path"],"weight":Path(ctx["asset"]["checkpoint_path"]),
                        "job":r._path(ctx,r._jobs(ctx)[0]["directory"]) / "worker_job.json"}[mutation]
                    target.write_bytes(b"changed")
                with self.assertRaises(ValueError):
                    r.run_scope(ctx,[row],runner=Mock(side_effect=AssertionError("must block")))

    def test_worker_checkpoint_recovers_missing_adapter_receipt(self):
        for output_written in (False,True):
            with self.subTest(output_written=output_written), tempfile.TemporaryDirectory() as tmp:
                ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
                def interrupted(ctx,job,collect,progress):
                    self.backend(ctx,job,lambda:None,progress)
                    if output_written:
                        save = r._save
                        def stop_receipt(path,value):
                            if "receipts" in path.parts:
                                raise KeyboardInterrupt()
                            save(path,value)
                        with patch.object(r,"_save",side_effect=stop_receipt):
                            collect()
                    raise KeyboardInterrupt()
                with self.assertRaises(KeyboardInterrupt):
                    r.run_scope(ctx,[row],runner=interrupted)
                records,reused = r.run_scope(ctx,[row],runner=Mock(side_effect=AssertionError("checkpoint must recover")),progress=lambda _:None)
                self.assertEqual(records[0]["status"],"completed"); self.assertEqual(reused,1)

    def test_failure_is_retained_without_automatic_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); rows = ctx["worklist"].iloc[:2].to_dict("records")
            def failing(ctx,job,collect,progress):
                with patch.object(self,"infer",side_effect=RuntimeError("fixture CUDA out of memory")):
                    self.backend(ctx,job,collect,progress)
            runner = Mock(side_effect=failing)
            records,_ = r.run_scope(ctx,rows,runner=runner,progress=lambda _:None)
            self.assertEqual(runner.call_count,1)
            self.assertTrue(all(x["status"] == "failed" for x in records))
            again,_ = r.run_scope(ctx,rows,runner=Mock(side_effect=AssertionError("no automatic retry")),progress=lambda _:None)
            self.assertTrue(all(x["status"] == "failed" for x in again))

    def test_full_stage_preserves_both_previous_methods_and_smoke_is_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); path = r._path(ctx,ctx["config"]["outputs"]["candidates"])
            r._save(path,pd.DataFrame([dict(model_id=m,candidate_id=m+"_fixture",status="completed",restored_sha256=m+"_hash") for m in ("opencv_telea","lama")]))
            r.run_smoke(ctx,runner=self.backend,progress=lambda _:None)
            self.assertEqual(len(pd.read_csv(path)),2)
            r.run_candidates(ctx,runner=self.backend,progress=lambda _:None); r.validate_results(ctx)
            table = pd.read_csv(path); self.assertEqual(len(table),12)
            self.assertEqual(table.loc[table.model_id.eq("lama"),"restored_sha256"].item(),"lama_hash")
            self.assertEqual(ctx["summary"]["completed_candidates"],10)
            self.assertEqual(ctx["summary"]["recorded_command_runtime_seconds"],1.5)
            self.assertFalse(ctx["summary"]["notebook_completion_gate_passed"])
            r.run_smoke(ctx,runner=Mock(side_effect=AssertionError("must reuse")),progress=lambda _:None)
            r.run_candidates(ctx,runner=Mock(side_effect=AssertionError("must reuse")),progress=lambda _:None); r.validate_results(ctx)
            self.assertEqual(ctx["summary"]["reused_candidates"],10)

    def test_bad_model_load_audit_and_changed_pixels_block_acceptance(self):
        for kind in ("audit","outside"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
                if kind == "audit":
                    audit = self.load_audit(); audit.update(matched_state_keys=1,missing_state_keys=1)
                    with patch.object(self,"load_audit",return_value=audit), self.assertRaisesRegex(ValueError,"state dictionary"):
                        r.run_scope(ctx,[row],runner=self.backend,progress=lambda _:None)
                else:
                    def wrong(generated,source,mask):
                        return np.zeros_like(source)
                    with patch.object(worker,"exact_mask_composite",side_effect=wrong):
                        records,_ = r.run_scope(ctx,[row],runner=self.backend,progress=lambda _:None)
                    self.assertEqual(records[0]["status"],"failed")

    def test_recorded_extra_checkpoint_keys_are_accepted_but_drift_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
            ctx["policy"]["expected_load_audit"]["unexpected_state_keys"] = 153
            audit = self.load_audit(); audit["unexpected_state_keys"] = 153
            with patch.object(self,"load_audit",return_value=audit):
                records,_ = r.run_scope(ctx,[row],runner=self.backend,progress=lambda _:None)
            self.assertEqual(records[0]["status"],"completed")
            ctx["policy"]["expected_load_audit"]["unexpected_state_keys"] = 152
            with self.assertRaisesRegex(ValueError,"load profile"):
                r._jobs(ctx)

    def test_unknown_image_and_escape_paths_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
            output,_ = r._locations(ctx,row,"primary"); output.parent.mkdir(parents=True); output.write_bytes(b"unknown")
            with self.assertRaisesRegex(ValueError,"Unverified"):
                r.run_scope(ctx,[row],runner=self.backend)
            self.assertEqual(output.read_bytes(),b"unknown")
            row["restored_path"] = "../../escape.png"
            with self.assertRaises(ValueError):
                r.run_scope(ctx,[row],runner=self.backend)

    def test_active_process_and_interrupt_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
            job = r._make_job(ctx,[row],"primary")
            child = Mock(); child.pid = 123; child.poll.return_value = None
            inspector = Mock(); inspector.create_time.return_value = 456.; inspector.is_running.return_value = True
            with patch.object(r.subprocess,"Popen",return_value=child), patch.object(r.psutil,"Process",return_value=inspector):
                with self.assertRaises(KeyboardInterrupt):
                    r._run_worker(ctx,job,Mock(side_effect=KeyboardInterrupt()),lambda _:None)
                child.terminate.assert_called_once()
                self.assertEqual(r._read(r._path(ctx,job["directory"]) / "job.json")["status"],"interrupted")
                job["status"] = "running"; r._save(r._path(ctx,job["directory"]) / "job.json",job)
                with self.assertRaisesRegex(ValueError,"still running"):
                    r.run_scope(ctx,[row],runner=self.backend)


if __name__ == "__main__":
    unittest.main()
