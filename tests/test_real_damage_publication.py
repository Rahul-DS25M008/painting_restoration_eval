"""Canonical D03 publication is tested in a disposable fixture repository."""
import copy
import json
import shutil
import unittest
from unittest.mock import patch

import test_real_damage_eligibility as fixtures
from PIL import Image
from restoration_eval.manifests import sha256_file, sha256_path
from restoration_eval.real_damage_preparation import _png_bytes
from restoration_eval.real_damage_publication import (PUBLICATION_STAGE, load_publication_config,
    publish_real_damage_dataset)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.EligibilityHandoffTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.prepared=self.fixture.prepare()
        self.f=self.fixture.f
        self.actual=self.fixture.actual
        self.config=load_publication_config(self.actual/'config/datasets/real_damage_publication.yaml')
        self.f.artworks['source_metadata_verified']=True
        for rel in [self.fixture.config['inputs']['helper_source'],
                    *self.f.artworks.source_metadata_path.tolist(),
                    'config/datasets/real_damage_publication.yaml']:
            path=self.f.root/rel;path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(self.actual/rel,path)
        self.inputs={'publication.config':self.f.root/'config/datasets/real_damage_publication.yaml',
                     'eligibility.scale_review_decisions':self.fixture.decision_path}
        self.hashes={k:sha256_file(p) for k,p in self.inputs.items()}
        self.preview_patch=patch('restoration_eval.real_damage_publication.overview_figure',
            return_value=_png_bytes(Image.new('RGB',(20,20),'white')))
        self.preview_patch.start();self.addCleanup(self.preview_patch.stop)

    def publish(self, previous=None):
        return publish_real_damage_dataset(self.f.root,self.f.config,self.fixture.config,self.config,
            self.f.catalog,self.f.artworks,self.fixture.fixture.prepared['preprocessed_images'],self.prepared,
            inputs=self.inputs,input_checksums=self.hashes,inventory_run_id='inventory_fixture',helper_versions={'fixture':'1'},
            started_at_utc='2026-11-15T00:00:00Z',previous_validation=previous or self.prepared['validation'])

    def test_publish_roundtrip_repeat_and_completion_remains_false(self):
        originals={p:sha256_file(p) for p in self.f.output.rglob('*') if p.is_file()}
        result=self.publish()
        self.assertTrue(result['validation'].overall_passed)
        self.assertEqual(sum(c.validation_stage==PUBLICATION_STAGE for c in result['validation'].checks),35)
        self.assertEqual(result['canonical_file_count'],34)
        self.assertEqual(len(result['artifacts']),14)
        self.assertEqual(result['run_manifest']['run_status'],'partial')
        self.assertFalse(result['run_manifest']['completion_gate_passed'])
        self.assertFalse(result['run_manifest']['downstream_ready'])
        self.assertEqual(originals,{p:sha256_file(p) for p in originals})
        self.assertTrue(result['tables']['artworks'].mask_review_status.eq('approved').all())
        self.assertFalse(result['tables']['artworks'].has_clean_reference.any())
        self.assertTrue(result['tables']['case_registry'].clean_image_path.isna().all())
        self.assertTrue(result['tables']['model_eligibility'].handoff_status.eq('requires_completed_D03_manifest').all())
        report=result['report_path'].read_text(encoding='utf-8')
        self.assertEqual(report.count('data:image/png;base64,'),2)
        for source in self.f.catalog['records']:
            self.assertIn(source['source_photographer'],report)
            self.assertIn(source['license'],report)
        for row in result['artifacts'].to_dict('records'):
            self.assertEqual(sha256_path(self.f.root/row['relative_path']),row['checksum'])
        times={p:p.stat().st_mtime_ns for p in self.f.output.rglob('*') if p.is_file()}
        again=self.publish(result['validation'])
        self.assertEqual(result['run_manifest'],again['run_manifest'])
        self.assertEqual(times,{p:p.stat().st_mtime_ns for p in times})
        # A changed canonical artifact is retained, never silently replaced.
        path=self.f.output/'images/masks/rdmask_rd001.png'
        path.write_bytes(b'preserve edited file')
        with self.assertRaisesRegex(ValueError,'Existing scientific artifact differs'):self.publish()
        self.assertEqual(path.read_bytes(),b'preserve edited file')

    def test_stale_tables_and_fabricated_reference_block_before_mask_publication(self):
        path=self.f.output/'work/geometry_eligibility/case_registry.csv'
        original=path.read_bytes();path.write_bytes(original+b'changed')
        with self.assertRaisesRegex(ValueError,'Prepared table changed'):self.publish()
        path.write_bytes(original)
        self.f.artworks.loc[0,'has_clean_reference']=True
        with self.assertRaisesRegex(ValueError,'Unexpected clean reference'):self.publish()
        self.assertFalse((self.f.output/'images/masks').exists())


if __name__=='__main__':unittest.main()
