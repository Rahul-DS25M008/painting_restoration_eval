"""D03 eligibility checks use disposable sources; notebooks remain user-executed."""
import json
import shutil
import unittest
from pathlib import Path

import test_real_damage_review as fixtures
from restoration_eval.manifests import sha256_file
from restoration_eval.paths import find_project_root
from restoration_eval.real_damage_eligibility import (
    ELIGIBILITY_STAGE, assess_input_eligibility, load_eligibility_config,
    prepare_geometry_and_eligibility,
)


class EligibilityPolicyTests(unittest.TestCase):
    def test_scale_review_and_empty_mask_block_sd_only(self):
        for model in ('opencv_telea','lama','hint_places2','stable_diffusion_inpainting'):
            accepted, _ = assess_input_eligibility(model,canonical_review_status='approved',
                scale_review_status='pending',inference_mask_empty=False)
            self.assertEqual(accepted,model!='stable_diffusion_inpainting')
        self.assertEqual(assess_input_eligibility('stable_diffusion_inpainting',canonical_review_status='approved',
            scale_review_status='accepted',inference_mask_empty=True),(False,'empty_mask_at_512'))
        self.assertTrue(assess_input_eligibility('stable_diffusion_inpainting',canonical_review_status='approved',
            scale_review_status='accepted',inference_mask_empty=False)[0])

    def test_unapproved_canonical_masks_and_unknown_models(self):
        for model in ('opencv_telea','lama','hint_places2','stable_diffusion_inpainting'):
            self.assertFalse(assess_input_eligibility(model,canonical_review_status='excluded',
                scale_review_status='accepted',inference_mask_empty=False)[0])
        with self.assertRaisesRegex(ValueError,'Unsupported'):
            assess_input_eligibility('sdxl_inpainting',canonical_review_status='approved',
                scale_review_status='accepted',inference_mask_empty=False)


class EligibilityHandoffTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ReviewCheckpointTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f=self.fixture.f
        self.reviewed=self.fixture.review()
        self.actual=find_project_root(Path(__file__))
        self.config=load_eligibility_config(self.actual/'config/datasets/real_damage_eligibility.yaml')
        paths=set(self.f.catalog['pipeline_baseline_sha256']) | {
            self.f.config['inputs']['region_config'],self.f.config['inputs']['helper_sources']['real_damage_review']}
        for relative in paths:
            dest=self.f.root/relative;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(self.actual/relative,dest)
        w=self.reviewed['work_root']
        checkpoint=json.loads((w/'review_checkpoint.json').read_text())
        self.decision={'schema_version':'real_damage_scale_review_decisions.v1','dataset_version':'2.0.0',
            'reviewer':'fixture','recorded_at_utc':'2026-11-15T12:00:00+00:00',
            'review_timestamp_basis':'time_existing_chat_approval_was_recorded',
            'review_basis':'user_accepted_saved_batch_5_previews_and_resizing_effects_in_chat',
            'batch_5_files_sha256':{p.relative_to(w).as_posix():sha256_file(p) for p in w.rglob('*') if p.is_file()},
            'batch_5_config_content_sha256':checkpoint['config_content_sha256'],
            'records':[dict(painting_id=r['painting_id'],input_sha256=r['input_sha256'],mask_sha256=r['mask_sha256'],
                inference_mask_sha256=r['inference_mask_sha256'],scale_review_status='accepted')
                for r in self.reviewed['inference_mask_audit'].to_dict('records')]}
        self.decision_path=self.f.root/self.config['inputs']['scale_review_decisions']
        self.decision_path.write_text(json.dumps(self.decision),encoding='utf-8')

    def prepare(self,previous=None):
        return prepare_geometry_and_eligibility(self.f.root,self.f.config,self.config,self.f.catalog,self.f.artworks,
            self.fixture.prepared['preprocessed_images'],self.reviewed['mask_review'],self.reviewed['inference_mask_audit'],
            previous_validation=previous or self.reviewed['validation'])

    def test_ten_cases_forty_rows_no_clean_reference_and_safe_repeat(self):
        originals={p:sha256_file(p) for p in self.f.output.rglob('*') if p.is_file()}
        result=self.prepare()
        self.assertTrue(result['validation'].overall_passed)
        self.assertEqual(sum(c.validation_stage==ELIGIBILITY_STAGE for c in result['validation'].checks),49)
        self.assertEqual(len(result['case_registry']),10)
        self.assertEqual(len(result['model_eligibility']),40)
        self.assertTrue(result['model_eligibility'].eligible.all())
        self.assertTrue(result['model_eligibility'].runtime_status.eq('not_checked_D04').all())
        self.assertTrue(result['case_registry'].clean_image_path.isna().all())
        self.assertFalse(result['case_registry'].has_clean_reference.any())
        self.assertTrue(result['mask_review'].scale_review_status.eq('accepted').all())
        self.assertTrue(self.reviewed['mask_review'].scale_review_status.eq('pending').all())
        self.assertFalse((self.f.output/'images/masks').exists())
        self.assertEqual(originals,{p:sha256_file(p) for p in originals})
        times={p:p.stat().st_mtime_ns for p in result['work_root'].rglob('*') if p.is_file()}
        repeat=self.prepare(result['validation'])
        self.assertEqual(result['validation'].summary(),repeat['validation'].summary())
        self.assertEqual(times,{p:p.stat().st_mtime_ns for p in times})
        edited=result['work_root']/'case_registry.csv';edited.write_text('preserve this edit')
        with self.assertRaisesRegex(ValueError,'Existing eligibility file differs'):self.prepare()
        self.assertEqual(edited.read_text(),'preserve this edit')

    def test_changed_preview_and_model_config_block_before_publication(self):
        path=self.reviewed['work_root']/'previews/rd001.png'
        original=path.read_bytes();path.write_bytes(original+b'edited')
        with self.assertRaisesRegex(ValueError,'Batch 5 evidence changed'):self.prepare()
        path.write_bytes(original)
        model=self.f.root/self.f.config['inputs']['model_configs']['lama']
        model.write_bytes(model.read_bytes()+b'\n# changed\n')
        with self.assertRaisesRegex(ValueError,'baseline changed'):self.prepare()
        self.assertFalse((self.f.output/'work/geometry_eligibility').exists())


if __name__=='__main__':unittest.main()
