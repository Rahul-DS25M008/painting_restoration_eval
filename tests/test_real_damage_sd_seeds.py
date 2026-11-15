"""Additional-seed contract tests use the N11 executor with a fake generator."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import pandas as pd
import yaml

import test_real_damage_sd as fixtures
from restoration_eval import real_damage_sd_seeds as r
from restoration_eval.validation import ValidationCollector


class RealDamageSDSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.RealDamageSDTests.setUpClass()
        cls.fixture = fixtures.RealDamageSDTests()
        root = Path(__file__).resolve().parents[1]
        cls.policy = yaml.safe_load((root / "config/experiments/real_damage_sd_seeds.yaml").read_text())

    def context(self,root):
        pctx = self.fixture.context(root)
        primaries = [r.primary.execute_case(pctx,row,executor=self.fixture.backend)[0] for row in pctx["worklist"].to_dict("records")]
        other = []
        for model in ("opencv_telea","lama","hint_places2"):
            for record in primaries:
                other.append(dict(record,model_id=model,candidate_id=model+"_"+record["painting_id"]))
        table = pd.DataFrame(other+primaries)
        r._save(r._path(pctx,pctx["config"]["outputs"]["candidates"]),table)
        rows = []
        for row in pctx["worklist"].to_dict("records"):
            rows.append(dict(row))
            for seed in (2027,2028,2029):
                cid = row["candidate_id"]+"_"+str(seed)
                rows.append(dict(row,candidate_id=cid,seed=seed,candidate_role="additional_seed",
                    restored_path=Path(row["restored_path"]).with_name(cid+".png").as_posix()))
        plan = pd.DataFrame(rows)
        ctx = {k:v for k,v in pctx.items() if k not in ("worklist","policy","validation","execution_fingerprint")}
        ctx.update(policy=copy.deepcopy(self.policy),worklist=r.audit_seed_design(plan),seed_plan=plan,
            primary_context=pctx,primary_records=pd.DataFrame(primaries),validation=ValidationCollector(),
            primary_snapshot=table[["candidate_id","model_id","candidate_role","status","restored_path","restored_sha256","execution_binding"]],
            execution_fingerprint="seed-fixture")
        return ctx

    def test_full_run_preserves_primary_table_and_completes_all_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp))
            raw_calls = []
            def executor(c,row):
                raw_calls.append(row.copy())
                return self.fixture.backend(c,row)
            r.run_candidates(ctx,executor=executor,progress=lambda _:None);r.validate_results(ctx)
            self.assertEqual(len(raw_calls),30)
            self.assertEqual({x["seed"] for x in raw_calls},{2027,2028,2029})
            for row in raw_calls:
                original = ctx["primary_context"]["worklist"].loc[ctx["primary_context"]["worklist"].painting_id.eq(row["painting_id"])].iloc[0]
                for field in ("prompt","negative_prompt","input_image_sha256","mask_sha256","configuration_fingerprint"):
                    self.assertEqual(row[field],original[field])
            self.assertEqual(len(ctx["group_members"]),40);self.assertEqual(len(ctx["seed_pair_plan"]),60)
            self.assertTrue(ctx["seed_pair_plan"].seed_a.lt(ctx["seed_pair_plan"].seed_b).all())
            self.assertEqual(ctx["summary"]["completed_candidates"],30)
            self.assertEqual(ctx["summary"]["completed_seed_groups"],10)
            self.assertFalse(ctx["summary"]["notebook_completion_gate_passed"])
            self.assertFalse(r._path(ctx,ctx["config"]["outputs"]["seed_pairwise"]).exists())
            r.run_candidates(ctx,executor=Mock(side_effect=AssertionError("must reuse")),progress=lambda _:None)
            r.validate_results(ctx);self.assertEqual(ctx["summary"]["reused_candidates"],30)
            paths = r.render_previews(ctx);self.assertEqual(len(paths),2)
            self.assertTrue(all(p.exists() for p in paths))

    def test_group_design_rejects_prompt_mask_setting_and_seed_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp));plan = ctx["seed_plan"]
            for field,value in (("prompt","changed"),("mask_sha256","changed"),("guidance_scale",8.),("seed",2026)):
                with self.subTest(field=field):
                    changed = plan.copy();changed.loc[1,field] = value
                    with self.assertRaises(ValueError):r.audit_seed_design(changed)

    def test_checkpoint_recovers_without_rerunning_a_completed_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp));row = ctx["worklist"].iloc[0].to_dict();save = r._save
            def interrupted(path,value):
                save(path,value)
                if path.name == "result.json":raise KeyboardInterrupt()
            with patch.object(r,"_save",side_effect=interrupted),self.assertRaises(KeyboardInterrupt):
                r.execute_case(ctx,row,executor=self.fixture.backend)
            record,cached = r.execute_case(ctx,row,executor=Mock(side_effect=AssertionError("recover checkpoint")))
            self.assertTrue(cached);self.assertEqual(record["execution_scope"],"additional_seed")
            self.assertEqual(record["changed_outside_pixels"],0)

    def test_changed_receipt_binding_and_unknown_output_block_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp));row = ctx["worklist"].iloc[0].to_dict()
            r.execute_case(ctx,row,executor=self.fixture.backend)
            changed = dict(row,prompt=row["prompt"]+" changed")
            with self.assertRaisesRegex(ValueError,"different inputs"):
                r.execute_case(ctx,changed,executor=self.fixture.backend)
            next_row = ctx["worklist"].iloc[1].to_dict();output,_ = r._locations(ctx,next_row)
            output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(b"unknown")
            with self.assertRaisesRegex(ValueError,"Unverified"):
                r.execute_case(ctx,next_row,executor=self.fixture.backend)
            self.assertEqual(output.read_bytes(),b"unknown")

    def test_seed_2026_cannot_be_regenerated_through_this_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp));row = ctx["primary_context"]["worklist"].iloc[0].to_dict()
            with self.assertRaisesRegex(ValueError,"Only additional"):
                r.execute_case(ctx,row,executor=Mock(side_effect=AssertionError("no primary inference")))

    def test_primary_image_or_table_tampering_blocks_execution(self):
        for kind in ("image","table"):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
                ctx = self.context(Path(tmp))
                if kind == "image":
                    (ctx["root"] / ctx["primary_records"].iloc[0].restored_path).write_bytes(b"changed")
                else:
                    path = r._path(ctx,ctx["config"]["outputs"]["candidates"])
                    table = pd.read_csv(path,keep_default_na=False);table.loc[0,"execution_binding"] = "changed";r._save(path,table)
                with self.assertRaises(ValueError):
                    r.run_candidates(ctx,executor=Mock(side_effect=AssertionError("primary drift must block")))


if __name__ == "__main__":
    unittest.main()
