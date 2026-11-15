"""Small synthetic fixtures exercise the D04 adapter without restoring study cases."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np
import pandas as pd
import yaml

from restoration_eval import real_damage_telea as r
from restoration_eval import real_damage_restoration as d04
from restoration_eval import restoration_opencv as baseline
from restoration_eval.manifests import sha256_file
from restoration_eval.validation import ValidationCollector, ValidationFailure


class RealDamageTeleaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.main = d04.load_restoration_config(cls.root / "config/experiments/real_damage_restoration.yaml")
        cls.policy = yaml.safe_load((cls.root / "config/experiments/real_damage_telea.yaml").read_text())
        cls.baseline = baseline.load_opencv_telea_config(cls.root / "config/experiments/opencv_telea.yaml")

    def context(self, root):
        for rel in (".git", "src/restoration_eval", "notebooks", "inputs"):
            (root / rel).mkdir(parents=True)
        config = copy.deepcopy(self.baseline)
        config["execution"].update(target_width=16, target_height=16)
        rows = []
        for i in range(1, 11):
            pid = f"rd{i:03d}"
            image = np.zeros((16,16,3), np.uint8)
            image[:,:,:] = np.arange(16, dtype=np.uint8)[None,:,None] * 12
            mask = np.zeros((16,16), np.uint8); mask[5:11,5:11] = 255
            image[mask > 0] = (255, 60, 10)
            input_path, mask_path = root / f"inputs/{pid}.png", root / f"inputs/{pid}_mask.png"
            cv2.imwrite(str(input_path), image); cv2.imwrite(str(mask_path), mask)
            rows.append(dict(painting_id=pid, case_id=f"case_{pid}", candidate_id=f"candidate_{pid}", model_id=r.MODEL,
                input_image_path=input_path.relative_to(root).as_posix(), mask_path=mask_path.relative_to(root).as_posix(),
                input_image_sha256=sha256_file(input_path), mask_sha256=sha256_file(mask_path), mask_threshold=128,
                restored_path=f"images/restored/{r.MODEL}/case_{pid}/candidate_{pid}.png",
                candidate_role="primary", has_clean_reference=False, reference_fidelity_metrics_applicable=False,
                clean_image_path="", configuration_id=config["model"]["configuration_id"]))
        return dict(root=root, output_root=root / "outputs" / d04.NOTEBOOK_STEM, policy=self.policy,
            config=self.main, baseline=config, worklist=pd.DataFrame(rows), validation=ValidationCollector(),
            stage_input_checksums={}, execution_fingerprint="fixture_execution", frozen={"readiness_fingerprint":"fixture_ready"})

    def test_adapter_matches_existing_algorithm_and_preserves_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
            result, reused = r.execute_case(ctx, row)
            image, mask = r._inputs(ctx, row)
            expected, _ = baseline.restore_array_with_opencv_telea(image, mask, radius=3)
            actual = cv2.imread(str(ctx["root"] / result["restored_path"]))
            np.testing.assert_array_equal(actual, expected)
            np.testing.assert_array_equal(actual[mask == 0], image[mask == 0])
            self.assertFalse(reused)
            self.assertGreater(result["changed_inside_pixels"], 0)
            self.assertEqual(result["candidate_id"], row["candidate_id"])
            self.assertFalse(result["has_clean_reference"])
            with patch.object(baseline, "restore_array_with_opencv_telea", side_effect=AssertionError("should reuse")):
                cached, reused = r.execute_case(ctx, row)
            self.assertTrue(reused); self.assertEqual(cached, result)

    def test_changed_input_output_and_code_binding_block_reuse(self):
        for mutation in ("input", "output", "code"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
                record, _ = r.execute_case(ctx, row)
                if mutation == "code":
                    ctx["execution_fingerprint"] = "different code"
                else:
                    key = row["input_image_path"] if mutation == "input" else record["restored_path"]
                    (ctx["root"] / key).write_bytes(b"corrupt")
                with self.assertRaises(ValueError):
                    r.execute_case(ctx, row)

    def test_unverified_image_and_output_escape_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
            path = ctx["output_root"] / row["restored_path"]
            path.parent.mkdir(parents=True); path.write_bytes(b"unverified")
            with self.assertRaisesRegex(ValueError, "Unverified"):
                r.execute_case(ctx, row)
            self.assertEqual(path.read_bytes(), b"unverified")
            row["restored_path"] = "../../outside.png"
            with self.assertRaises(ValueError):
                r.execute_case(ctx, row)

    def test_interrupted_image_write_resumes_only_if_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); row = ctx["worklist"].iloc[0].to_dict()
            record, _ = r.execute_case(ctx, row)
            receipt = ctx["output_root"] / f"work/telea/receipts/primary/{row['candidate_id']}.json"
            receipt.write_text(json.dumps(dict(status="started", candidate_id=row["candidate_id"], execution_binding=record["execution_binding"])))
            recovered, reused = r.execute_case(ctx, row)
            self.assertFalse(reused); self.assertEqual(record["restored_sha256"], recovered["restored_sha256"])
            receipt.write_text(json.dumps(dict(status="started", execution_binding=record["execution_binding"])))
            (ctx["root"] / record["restored_path"]).write_bytes(b"different")
            with self.assertRaisesRegex(ValueError, "Interrupted"):
                r.execute_case(ctx, row)

    def test_smoke_full_run_validation_and_other_method_rows_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp))
            candidate_path = ctx["output_root"] / self.main["outputs"]["candidates"]
            candidate_path.parent.mkdir(parents=True)
            pd.DataFrame([dict(model_id="lama",candidate_id="other_candidate",status="completed")]).to_csv(candidate_path,index=False)
            r.run_smoke(ctx); r.run_candidates(ctx, progress=lambda _:None); r.validate_results(ctx)
            self.assertEqual(ctx["summary"]["completed_candidates"], 10)
            self.assertEqual(ctx["summary"]["reused_candidates"], 0)
            self.assertFalse(ctx["summary"]["notebook_completion_gate_passed"])
            stored = pd.read_csv(candidate_path)
            self.assertEqual(len(stored), 11); self.assertIn("other_candidate", set(stored.candidate_id))
            r.run_candidates(ctx, progress=lambda _:None)
            self.assertEqual(ctx["reused_candidates"], 10)

    def test_failed_case_is_retained_without_stopping_other_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.context(Path(tmp)); r.run_smoke(ctx)
            row = ctx["worklist"].iloc[0]
            (ctx["root"] / row.input_image_path).write_bytes(b"changed after smoke")
            r.run_candidates(ctx, progress=lambda _:None)
            self.assertEqual(ctx["records"].status.value_counts().to_dict(), {"completed":9,"failed":1})
            with self.assertRaises(ValidationFailure):
                r.validate_results(ctx)
            self.assertTrue((ctx["output_root"] / f"logs/telea_{row.candidate_id}.jsonl").exists())

    def test_outside_mask_modification_is_a_technical_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx=self.context(Path(tmp)); row=ctx["worklist"].iloc[0].to_dict()
            def wrong(image, mask, **kwargs):
                output=image.copy(); output[0,0]=255
                return output, "bad_fixture"
            with patch.object(baseline,"restore_array_with_opencv_telea",wrong), self.assertRaisesRegex(ValueError,"outside-mask"):
                r.execute_case(ctx,row)
            self.assertFalse((ctx["output_root"] / row["restored_path"]).exists())


if __name__ == "__main__":
    unittest.main()
