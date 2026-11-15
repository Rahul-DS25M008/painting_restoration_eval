"""Review gates use temporary synthetic sources; no notebook is executed."""
import json
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

import test_real_damage_preparation as fixtures
from restoration_eval.manifests import sha256_file
from restoration_eval.real_damage_preparation import _png_bytes
from restoration_eval.real_damage_review import REVIEW_STAGE, inference_scale_evidence, review_real_damage_masks


class ScaleEvidenceTests(unittest.TestCase):
    def test_lost_components_are_distinct_from_all_resampling_changes(self):
        array = np.zeros((768, 768), dtype=np.uint8)
        array[301:324, 301:324] = 255
        array[100, 100] = 255  # index 100 is not sampled by 768 -> 512 nearest
        audit, reduced, lost = inference_scale_evidence(Image.fromarray(array), content_box=(50, 50, 700, 700))
        self.assertEqual(audit["source_component_count"], 2)
        self.assertEqual(audit["disappeared_component_count"], 1)
        self.assertEqual(audit["disappeared_source_pixels"], 1)
        self.assertEqual(int((np.asarray(lost) == 255).sum()), 1)
        self.assertAlmostEqual(audit["disappeared_source_pixel_fraction"], 1 / 530)
        self.assertGreater(audit["roundtrip_removed_source_pixels"], 1)
        np.testing.assert_array_equal(np.asarray(reduced), np.asarray(Image.fromarray(array).resize((512,512),Image.Resampling.NEAREST)))
        self.assertEqual(audit["inference_padding_overlap_pixels"], 0)
        self.assertFalse(audit["sd_eligible_without_review"])

    def test_vanished_mask_is_reported_without_approving_eligibility(self):
        mask = Image.new("L", (768, 768), 0)
        mask.putpixel((100, 100), 255)
        audit, _, _ = inference_scale_evidence(mask, content_box=(0, 0, 768, 768))
        self.assertTrue(audit["empty_inference_mask"])
        self.assertEqual(audit["disappeared_source_pixel_fraction"], 1)
        self.assertEqual(audit["scale_review_status"], "pending")
        self.assertEqual(audit["sd_eligibility_status"], "not_assessed")


class ReviewCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.preparation = fixtures.FullPreparationTests()
        self.preparation.setUp()
        self.addCleanup(self.preparation.doCleanups)
        self.f = self.preparation.fixture
        self.prepared = self.preparation.prepare()
        f = self.f
        work = f.output / f.config["preparation"]["candidate_directory"]
        self.decisions_path = f.root / f.config["inputs"]["mask_review_decisions"]
        self.decisions = {
            "schema_version": "real_damage_mask_review_decisions.v1", "dataset_version": "2.0.0",
            "recorded_at_utc": "2026-11-15T10:00:00+00:00", "reviewer": "unit_test",
            "review_basis": "user_accepted_saved_batch_4_previews_in_chat",
            "accepted_partial_repair_scope": True, "scale_review_status": "pending",
            "batch_4_checkpoint_sha256": {
                "preprocessed_images": sha256_file(work / "preprocessed_images.csv"),
                "mask_candidates": sha256_file(work / "candidate_masks.csv")},
            "records": [{"painting_id": r["painting_id"], "input_sha256": r["input_sha256"],
                         "mask_sha256": r["mask_sha256"], "review_status": "approved"}
                        for r in self.prepared["mask_candidates"].to_dict("records")]}
        self.write_decisions()
        self.preview_patch = patch("restoration_eval.real_damage_review.scale_review_figure",
                                   return_value=_png_bytes(Image.new("RGB", (20,20), "white")))
        self.preview_patch.start()
        self.addCleanup(self.preview_patch.stop)

    def write_decisions(self):
        self.decisions_path.write_text(json.dumps(self.decisions), encoding="utf-8")

    def review(self, previous=None):
        return review_real_damage_masks(self.f.root, self.f.config,
                                       self.prepared["preprocessed_images"], self.prepared["mask_candidates"],
                                       previous_validation=previous or self.prepared["validation"])

    def test_checkpoints_reuse_and_do_not_finalize_scale_review_or_masks(self):
        originals = {p: sha256_file(p) for p in self.f.output.rglob('*') if p.is_file()}
        result = self.review()
        self.assertTrue(result["validation"].overall_passed)
        self.assertEqual(sum(c.validation_stage == REVIEW_STAGE for c in result["validation"].checks), 43)
        self.assertTrue(result["mask_review"]["review_status"].eq("approved").all())
        self.assertTrue(result["inference_mask_audit"]["scale_review_status"].eq("pending").all())
        self.assertEqual(len(list(result["work_root"].rglob('*.png'))), 30)
        self.assertFalse((self.f.output / 'images/masks').exists())
        self.assertEqual(originals, {p: sha256_file(p) for p in originals})
        files = {p: p.stat().st_mtime_ns for p in result["work_root"].rglob('*') if p.is_file()}
        repeated = self.review(result["validation"])
        self.assertEqual(result["validation"].summary(), repeated["validation"].summary())
        self.assertEqual(files, {p: p.stat().st_mtime_ns for p in files})
        edited = result["work_root"]/'previews/rd001.png'
        edited.write_bytes(b'preserve edited evidence')
        with self.assertRaisesRegex(ValueError, 'Existing mask-review file differs'):
            self.review()
        self.assertEqual(edited.read_bytes(), b'preserve edited evidence')

    def test_changed_mask_blocks_before_review_output(self):
        row = self.prepared["mask_candidates"].iloc[3]
        path = self.f.root / row['candidate_mask_path']
        with Image.open(path) as source:
            mask=source.copy()
        mask.putpixel((400,400),255)
        mask.save(path)
        with self.assertRaisesRegex(ValueError,'Reviewed mask changed'):
            self.review()
        self.assertFalse((self.f.output/'work/mask_review').exists())

    def test_wrong_approval_and_changed_checkpoint_are_rejected(self):
        self.decisions['records'][0]['review_status']='pending'
        self.write_decisions()
        with self.assertRaisesRegex(ValueError,'has not been approved'):
            self.review()
        self.decisions['records'][0]['review_status']='approved'
        self.decisions['batch_4_checkpoint_sha256']['mask_candidates']='0'*64
        self.write_decisions()
        with self.assertRaisesRegex(ValueError,'checkpoint changed'):
            self.review()
        self.assertFalse((self.f.output/'work/mask_review').exists())


if __name__ == '__main__':
    unittest.main()
