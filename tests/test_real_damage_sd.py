"""Test the unchanged N11 executor with a fake pipeline, never study inference."""
import copy
import sys
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
from PIL import Image
import yaml

from restoration_eval import real_damage_sd as r
from restoration_eval.validation import ValidationCollector, ValidationFailure


class RealDamageSDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.main = r.d04.load_restoration_config(root / "config/experiments/real_damage_restoration.yaml")
        cls.policy = yaml.safe_load((root / "config/experiments/real_damage_sd.yaml").read_text())
        cls.baseline = r.d04.effective_model_config(r.sd.load_stable_diffusion_config(root / "config/experiments/stable_diffusion.yaml"),r.MODEL,cls.main)
        plan = pd.read_csv(root / "outputs/d04_real_damage_restoration_and_evaluation/data/candidate_plan.csv",keep_default_na=False,float_precision="round_trip")
        cls.plan = r._numeric_plan(plan.loc[plan.model_id.eq(r.MODEL) & plan.candidate_role.eq("primary")]).sort_values("painting_id").reset_index(drop=True)

    def context(self,root):
        for rel in (".git","src/restoration_eval","notebooks","inputs"):
            (root / rel).mkdir(parents=True)
        frame = self.plan.copy()
        for i,row in frame.iterrows():
            image = np.full((768,768,3),(40,90,170),np.uint8)
            mask = np.zeros((768,768),np.uint8); mask[100:180,100:180] = 255
            ip = root / f"inputs/{row.painting_id}.png"; mp = root / f"inputs/{row.painting_id}_mask.png"
            Image.fromarray(image).save(ip); Image.fromarray(mask).save(mp)
            frame.loc[i,"input_image_path"] = ip.relative_to(root).as_posix()
            frame.loc[i,"mask_path"] = frame.loc[i,"mask_or_effect_path"] = mp.relative_to(root).as_posix()
            frame.loc[i,"input_image_sha256"] = frame.loc[i,"input_sha256"] = r.sha256_file(ip)
            frame.loc[i,"mask_sha256"] = r.sha256_file(mp)
        weight = root / "weight.bin"; weight.write_bytes(b"fixture weight")
        source = root / "source.py"; source.write_bytes(b"fixture code")
        return dict(root=root,output_root=root / "outputs" / r.d04.NOTEBOOK_STEM,policy=copy.deepcopy(self.policy),
            config=copy.deepcopy(self.main),baseline=copy.deepcopy(self.baseline),worklist=frame,
            frozen=dict(readiness_fingerprint="fixture"),execution_fingerprint="fixture",validation=ValidationCollector(),
            stage_input_checksums={"source.py":r.sha256_file(source)},frozen_input_checksums={},
            assets=[dict(path=str(weight),sha256=r.sha256_file(weight))],packages={})

    def backend(self,ctx,row,pipeline=None):
        if pipeline is None:
            pipeline = lambda **kw: SimpleNamespace(images=[Image.new("RGB",(512,512),(int(kw["generator"]) % 230,70,20))])
        return r.sd.run_stable_diffusion_candidate(row,pipeline=pipeline,device="cpu",project_root=ctx["root"],
            notebook_output_root=ctx["output_root"],config=ctx["baseline"],generator_factory=lambda device,seed:seed)

    def test_original_executor_gets_exact_prompt_seed_geometry_and_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
            calls = []
            def pipeline(**kw):
                calls.append(kw)
                return SimpleNamespace(images=[Image.new("RGB",(512,512),(190,70,20))])
            record,cached = r.execute_case(ctx,row,executor=lambda c,x:self.backend(c,x,pipeline))
            self.assertFalse(cached); self.assertEqual(record["status"],"completed")
            self.assertEqual(len(calls),1); call = calls[0]
            for key in ("prompt","negative_prompt","num_inference_steps","guidance_scale","strength"):
                self.assertEqual(call[key],row[key])
            self.assertEqual(call["generator"],2026); self.assertEqual(call["image"].size,(512,512))
            self.assertEqual(call["mask_image"].size,(512,512))
            image,mask = r._inputs(ctx,row)
            with Image.open(ctx["root"] / record["restored_path"]) as pil:
                out = np.asarray(pil)
            np.testing.assert_array_equal(out[mask == 0],image[mask == 0])
            self.assertTrue(np.all(out[mask > 0] == [190,70,20]))
            self.assertEqual(record["changed_outside_pixels"],0)
            repeat,cached = r.execute_case(ctx,row,executor=Mock(side_effect=AssertionError("must reuse")))
            self.assertTrue(cached); self.assertEqual(repeat,record)

    def test_baseline_retry_preserves_exact_seed_and_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
            pipeline = Mock(side_effect=[RuntimeError("temporary failure"),SimpleNamespace(images=[Image.new("RGB",(512,512))])])
            record,_ = r.execute_case(ctx,row,executor=lambda c,x:self.backend(c,x,pipeline))
            self.assertEqual(record["attempt_count"],2); self.assertEqual(record["retry_count"],1)
            self.assertEqual([c.kwargs["generator"] for c in pipeline.call_args_list],[2026,2026])
            self.assertEqual([c.kwargs["prompt"] for c in pipeline.call_args_list],[row["prompt"]]*2)

    def test_failed_execution_is_retained_without_unbounded_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
            pipeline = Mock(side_effect=RuntimeError("fixture OOM"))
            record,_ = r.execute_case(ctx,row,executor=lambda c,x:self.backend(c,x,pipeline))
            self.assertEqual(record["status"],"failed"); self.assertEqual(pipeline.call_count,2)
            repeat,cached = r.execute_case(ctx,row,executor=Mock(side_effect=AssertionError("no third attempt")))
            self.assertTrue(cached); self.assertEqual(repeat,record)

    def test_checkpoint_recovers_before_or_after_published_image(self):
        for published in (False,True):
            with self.subTest(published=published), tempfile.TemporaryDirectory() as tmp:
                ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict(); save = r._save
                def interrupted(path,value):
                    if published and "receipts" in path.parts:
                        raise KeyboardInterrupt()
                    save(path,value)
                    if not published and path.name == "result.json":
                        raise KeyboardInterrupt()
                with patch.object(r,"_save",side_effect=interrupted), self.assertRaises(KeyboardInterrupt):
                    r.execute_case(ctx,row,executor=self.backend)
                record,cached = r.execute_case(ctx,row,executor=Mock(side_effect=AssertionError("checkpoint must recover")))
                self.assertTrue(cached); self.assertEqual(record["status"],"completed")

    def test_prompt_seed_input_image_or_code_drift_block_resume(self):
        for kind in ("prompt","seed","input","output","executor_output","code","weight"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
                record,_ = r.execute_case(ctx,row,executor=self.backend)
                if kind == "prompt": row["prompt"] += " changed"
                elif kind == "seed": row["seed"] = 999
                elif kind == "code": ctx["execution_fingerprint"] = "changed"
                elif kind == "weight": Path(ctx["assets"][0]["path"]).write_bytes(b"changed")
                else:
                    rel = dict(input=row["input_image_path"],output=record["restored_path"],executor_output=record["executor_output_path"])[kind]
                    (ctx["root"] / rel).write_bytes(b"changed")
                with self.assertRaises(ValueError):
                    r._assert_inputs(ctx)
                    r.execute_case(ctx,row,executor=Mock(side_effect=AssertionError("must block")))

    def test_smoke_counts_and_full_stage_preserve_other_methods_and_future_seeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); path = r._path(ctx,ctx["config"]["outputs"]["candidates"])
            old = pd.DataFrame([dict(model_id=m,candidate_id=m+"_fixture",status="completed",restored_sha256=m+"_hash") for m in ("opencv_telea","lama","hint_places2",r.MODEL)])
            r._save(path,old)
            r.run_smoke(ctx,executor=self.backend,progress=lambda _:None)
            self.assertEqual(len(pd.read_csv(path)),4)
            self.assertEqual(ctx["smoke_summary"]["primary_candidate_count"],0)
            self.assertEqual(ctx["smoke_summary"]["fixed_repeat"]["maximum_absolute_difference"],0)
            self.assertGreater(ctx["smoke_summary"]["alternate_seed"]["inside_different_pixels"],0)
            r.run_candidates(ctx,executor=self.backend,progress=lambda _:None); r.validate_results(ctx)
            current = pd.read_csv(path); self.assertEqual(len(current),14)
            self.assertTrue(set(old.candidate_id).issubset(current.candidate_id))
            self.assertEqual(ctx["summary"]["completed_candidates"],10)
            self.assertFalse(ctx["summary"]["notebook_completion_gate_passed"])
            r.run_candidates(ctx,executor=Mock(side_effect=AssertionError("must reuse")),progress=lambda _:None)
            r.validate_results(ctx); self.assertEqual(ctx["summary"]["reused_candidates"],10)

    def test_unknown_image_and_escaped_paths_are_not_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
            output,_ = r._locations(ctx,row,"primary"); output.parent.mkdir(parents=True); output.write_bytes(b"unknown")
            with self.assertRaisesRegex(ValueError,"Unverified"):
                r.execute_case(ctx,row,executor=self.backend)
            self.assertEqual(output.read_bytes(),b"unknown")
            row["restored_path"] = "../../escape.png"
            with self.assertRaises(ValueError): r.execute_case(ctx,row,executor=self.backend)

    def test_same_seed_drift_blocks_smoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); counter = 0
            def bad(ctx,row):
                nonlocal counter
                counter += 1
                return self.backend(ctx,row,lambda **kw:SimpleNamespace(images=[Image.new("RGB",(512,512),(counter*60,0,0))]))
            with self.assertRaises(ValidationFailure): r.run_smoke(ctx,executor=bad,progress=lambda _:None)
            self.assertNotIn("smoke_passed",ctx)

    def test_numeric_csv_settings_are_normalised_without_truncation(self):
        frame = self.plan.iloc[:1].copy(); frame["num_inference_steps"] = "30.0"
        self.assertEqual(r._numeric_plan(frame).num_inference_steps.item(),30)
        frame["num_inference_steps"] = "30.5"
        with self.assertRaises(ValueError): r._numeric_plan(frame)

    def test_loading_uses_verified_local_snapshot_without_changing_recorded_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); ctx["asset"] = dict(snapshot_path=str(Path(tmp) / "snapshot"))
            class Tokenizer:
                model_max_length = 77
                def __call__(self,text,**kwargs): return dict(input_ids=[1,2,3])
            pipeline = type("StableDiffusionInpaintPipeline",(),{})()
            pipeline.scheduler = type("DDIMScheduler",(),{})()
            pipeline.unet = SimpleNamespace(dtype="float16",config=SimpleNamespace(in_channels=9))
            pipeline.tokenizer = Tokenizer()
            before = copy.deepcopy(ctx["baseline"])
            with patch.dict(sys.modules,{"torch":SimpleNamespace(float16="float16")}), patch.object(r.sd,"load_stable_diffusion_pipeline",return_value=(pipeline,"cuda")) as loader, patch.object(r.sd,"runtime_environment",return_value=dict(device="cuda")):
                actual,device = r._pipeline(ctx)
                self.assertIs(actual,pipeline); self.assertEqual(device,"cuda")
                load_config = loader.call_args.args[0]
                self.assertEqual(load_config["model"]["hf_model_id"],ctx["asset"]["snapshot_path"])
                expected = copy.deepcopy(before); expected["model"]["hf_model_id"] = ctx["asset"]["snapshot_path"]
                self.assertEqual(load_config,expected); self.assertEqual(ctx["baseline"],before)
                self.assertTrue(ctx["load_audit_path"].exists())
                r._pipeline(ctx); self.assertEqual(loader.call_count,1)


if __name__ == "__main__":
    unittest.main()
