"""D04 readiness/selection and isolated freeze regressions; never infer images."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from PIL import Image

from restoration_eval import real_damage_readiness as ready
from restoration_eval import real_damage_restoration as d04
from restoration_eval.manifests import sha256_file
from restoration_eval.validation import ValidationCollector, ValidationFailure
import test_real_damage_restoration as fixtures


class RealDamageReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.RealDamageRestorationTests.setUpClass()
        cls.fixture = fixtures.RealDamageRestorationTests()
        cls.root = cls.fixture.root
        cls.policy = ready.load_readiness_config(cls.root / "config/experiments/real_damage_readiness.yaml")
        cls.geometry = pd.read_csv(cls.root / "outputs/d03_real_damage_dataset_preparation/metrics/mask_geometry.csv")
        masks = pd.read_csv(cls.root / cls.policy["inputs"]["masks"])
        artworks = pd.read_csv(cls.root / cls.policy["inputs"]["artworks"])
        cls.pool = masks.loc[masks.mask_type.ne("zero_control")].merge(
            artworks[["painting_id", "category", "title"]], on="painting_id", validate="many_to_one")

    def selection(self, pool=None, real=None):
        return ready.select_comparators(self.geometry if real is None else real,
            self.pool if pool is None else pool, self.policy["selection"])

    def test_selection_ignores_row_order_and_outcome_columns(self):
        altered = self.pool.sample(frac=1, random_state=5).copy()
        altered["masked_mae"] = range(len(altered))
        altered["restored_path"] = "never/read/this.png"
        pd.testing.assert_frame_equal(self.selection(), self.selection(altered, self.geometry.iloc[::-1]))

    def test_selection_keeps_categories_distinct_paintings_and_compact_losses(self):
        selected = self.selection()
        self.assertEqual(selected.synthetic_painting_id.nunique(), 10)
        self.assertTrue(selected.category.eq(selected.synthetic_painting_id.map(self.pool.drop_duplicates("painting_id").set_index("painting_id").category)).all())
        compact = selected.loc[selected.painting_id.eq("rd006")].iloc[0]
        self.assertTrue(compact.compact_target_filter_applied)
        self.assertIn(compact.synthetic_mask_type, ["loss_small", "loss_large"])
        self.assertTrue(selected.prompt_policy_difference.all())
        self.assertFalse(selected.selection_uses_restoration_scores.any())

    def test_invalid_pools_block(self):
        for mutation in ("missing", "zero", "nan"):
            pool = self.pool.copy()
            if mutation == "missing":
                pool = pool.iloc[:-1]
            elif mutation == "zero":
                pool.loc[pool.index[0], "mask_type"] = "zero_control"
            else:
                pool.loc[pool.index[0], "damaged_content_fraction"] = float("nan")
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.selection(pool)

    def test_completed_producer_tables_match_artifact_checksums(self):
        for key, relative in self.policy["inputs"].items():
            with self.subTest(producer=key):
                frame, checksums = ready._verified_table(self.root, relative)
                self.assertFalse(frame.empty)
                self.assertEqual(checksums[relative], sha256_file(self.root / relative))
                self.assertEqual(len(checksums), 3)

    def test_tokenizer_reports_overflow_without_truncation(self):
        class Tokenizer:
            model_max_length = 77
            def __call__(self, text, *, truncation, add_special_tokens):
                assert truncation is False and add_special_tokens is True
                return {"input_ids": list(range(len(text.split()) + 2))}
        prompts = pd.DataFrame([dict(painting_id="rd001", prompt_id="test", prompt="word " * 76)])
        audit = ready.tokenize_prompts(Tokenizer(), prompts, "short negative")
        self.assertFalse(audit.iloc[0].fits)
        self.assertTrue(audit.iloc[1].fits)
        self.assertFalse(audit.truncation_used.any())

    def plan_context(self):
        return dict(candidate_plan=self.fixture.plan(), effective_configs={m: d04.effective_model_config(b, m, self.fixture.config)
            for m, b in self.fixture.baselines.items()})

    def test_executable_plan_retains_ids_missing_reference_and_fixed_sd_settings(self):
        context = self.plan_context()
        result = ready.build_executable_plan(context)
        self.assertEqual(result.candidate_id.tolist(), context["candidate_plan"].candidate_id.tolist())
        self.assertEqual(result.candidate_role.value_counts().to_dict(), {"primary": 40, "additional_seed": 30})
        self.assertFalse(result.has_clean_reference.any())
        self.assertTrue(result.clean_image_path.eq("").all())
        sd = result.loc[result.model_id.eq(d04.SD_MODEL)]
        self.assertTrue(sd.inference_width.eq(512).all())
        self.assertTrue(sd.num_inference_steps.eq(30).all())
        self.assertTrue(sd.guidance_scale.eq(7.5).all())
        self.assertTrue(result.mask_threshold.eq(128).all())
        self.assertTrue(result.runtime_status.eq("assets_verified_smoke_pending").all())

    def frozen_context(self, root):
        for path in (root / ".git", root / "src/restoration_eval", root / "notebooks"):
            path.mkdir(parents=True)
        source = root / "fixture_input.txt"
        source.write_text("immutable input", encoding="utf-8")
        asset = root / "fixture_model.bin"
        asset.write_bytes(b"isolated test asset; not model weights")
        checks = ValidationCollector()
        keys = ["synthetic_producers", "readiness_inventory", "comparators", "comparison_candidates", "comparison_policy",
            "runtime_imports", "cuda", "lama_checkpoint", "hint_source", "hint_checkpoint", "hint_import", "sd_snapshot",
            "sd_inpainting_architecture", "tokens:unchanged_negative"]
        keys += ["tokens:" + p for p in self.fixture.prompts().prompt_id]
        for key in keys:
            ready._check(checks, key, "Isolated fixture check", True, True)
        context = self.plan_context()
        context.update(root=root, output_root=root / "outputs" / d04.NOTEBOOK_STEM, config=self.fixture.config,
            readiness_policy=self.policy, inputs={"fixture": source}, input_checksums={"fixture": sha256_file(source)},
            readiness_checksums={}, selected_file_checksums={}, validation=checks,
            tokenizer_audit=pd.DataFrame([dict(fits=True)]), comparators=self.selection(),
            comparator_candidates=pd.DataFrame([dict(candidate_id="synthetic-test")]),
            runtime_environment={"test_fixture": True},
            runtime_assets=pd.DataFrame([dict(model_id="lama", asset_role="weights", path=str(asset),
                size_bytes=asset.stat().st_size, sha256=sha256_file(asset))]),
            baseline_configs=self.fixture.baselines, prompts=self.fixture.prompts(),
            upstream_manifest=self.fixture.manifest, inventory={"inventory_run_id": "isolated_test"})
        return context

    @staticmethod
    def preview(context, destination, first, last):
        destination.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (8, 8), (first, last, 20)).save(destination)

    def test_freeze_roundtrip_resume_and_future_validation_are_safe(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(ready, "render_comparison_inputs", self.preview):
            context = self.frozen_context(Path(temporary))
            ready.freeze_readiness(context)
            first = context["checkpoint_path"].read_bytes()
            self.assertFalse(context["reused"])
            self.assertFalse(context["readiness_checkpoint"]["inference_executed"])
            # Later batches own the cumulative check file; this does not alter Batch 2.
            cumulative = context["output_root"] / context["config"]["outputs"]["validation"]
            cumulative.parent.mkdir(parents=True)
            cumulative.write_text("future checks", encoding="utf-8")
            ready.freeze_readiness(context)
            self.assertTrue(context["reused"])
            self.assertEqual(context["checkpoint_path"].read_bytes(), first)
            self.assertEqual(len(context["frozen_plan"]), 70)

    def test_freeze_rejects_changed_inputs_and_existing_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(ready, "render_comparison_inputs", self.preview):
            context = self.frozen_context(Path(temporary))
            ready.freeze_readiness(context)
            plan_path = context["output_root"] / context["config"]["outputs"]["candidate_plan"]
            plan_path.write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "artifact changed"):
                ready.freeze_readiness(context)
            context["inputs"]["fixture"].write_text("changed input", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Input changed"):
                ready.freeze_readiness(context)

    def test_interrupted_freeze_resumes_and_rejects_unrelated_preview(self):
        with tempfile.TemporaryDirectory() as temporary:
            context = self.frozen_context(Path(temporary))
            def interrupt(context, destination, first, last):
                if first == 5:
                    raise RuntimeError("simulated interruption")
                self.preview(context, destination, first, last)
            with patch.object(ready, "render_comparison_inputs", interrupt), self.assertRaisesRegex(RuntimeError, "interruption"):
                ready.freeze_readiness(context)
            with patch.object(ready, "render_comparison_inputs", self.preview):
                ready.freeze_readiness(context)
            self.assertTrue(context["checkpoint_path"].is_file())
        with tempfile.TemporaryDirectory() as temporary, patch.object(ready, "render_comparison_inputs", self.preview):
            context = self.frozen_context(Path(temporary))
            preview = context["output_root"] / self.policy["outputs"]["preview_first"]
            preview.parent.mkdir(parents=True)
            Image.new("RGB", (8, 8), "red").save(preview)
            with self.assertRaisesRegex(ValueError, "preview differs"):
                ready.freeze_readiness(context)

    def test_failed_or_missing_runtime_checks_prevent_freeze(self):
        with tempfile.TemporaryDirectory() as temporary:
            context = self.frozen_context(Path(temporary))
            ready._check(context["validation"], "failed_test", "Deliberate test failure", False, False)
            with self.assertRaises(ValidationFailure):
                ready.freeze_readiness(context)
            context["validation"] = ValidationCollector()
            with self.assertRaisesRegex(ValueError, "not all run"):
                ready.freeze_readiness(context)
            self.assertFalse(context["output_root"].exists())


if __name__ == "__main__":
    unittest.main()
