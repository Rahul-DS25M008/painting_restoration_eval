"""Report evidence binding, numerical provenance and safe completion tests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from restoration_eval import real_damage_report as r
from restoration_eval import real_damage_report_content as content
from restoration_eval.validation import ValidationCollector

ROOT=Path(__file__).resolve().parents[1]


class RealDamageReportTests(unittest.TestCase):
    def review_fixture(self):
        catalog=json.loads((ROOT/'config/evaluation/real_damage_visual_observations.json').read_text(encoding='utf-8'))
        candidates=pd.DataFrame(catalog['records']).assign(candidate_role='primary')
        return catalog,candidates

    def test_review_is_complete_and_bound_to_images_not_expert_ratings(self):
        catalog,candidates=self.review_fixture()
        self.assertEqual(len(r.validate_observations(catalog,candidates)),40)
        for field in ('restored_sha256','input_image_sha256','mask_sha256','model_id'):
            bad=copy.deepcopy(catalog);bad['records'][0][field]='changed'
            with self.assertRaisesRegex(ValueError,'binding'):r.validate_observations(bad,candidates)
        for field in ('expert_assessment','numeric_ratings'):
            bad=copy.deepcopy(catalog);bad[field]=True
            with self.assertRaisesRegex(ValueError,'authority'):r.validate_observations(bad,candidates)
        with self.assertRaisesRegex(ValueError,'Incomplete'):r.validate_observations(catalog,candidates.iloc[:-1])

    def test_claims_rounding_scaling_filtering_and_changed_values(self):
        frame=pd.DataFrame({'case':['a','b'],'value':[.012345,4.0]})
        ctx={'root':ROOT,'canonical_output_root':ROOT,'tables':{'saved':frame},'table_hashes':{'saved':'hash'}}
        renderer=content.Report(ctx)
        text=renderer.number('saved','value',{'case':'a'},decimals=2,scale=100)
        text+=renderer.number('saved',operation='count')
        text+=renderer.number('saved','case',operation='nunique')
        text+=renderer.number('saved','value',operation='sum',decimals=6)
        claims=pd.DataFrame(renderer.claims);parsed=r.ReportHTML(text)
        r.validate_claims(ctx,claims,parsed)
        with self.assertRaisesRegex(ValueError,'changed'):
            r.validate_claims(ctx,claims,r.ReportHTML(text.replace('1.23','1.24')))
        ctx['tables']['saved'].loc[0,'value']=.02
        with self.assertRaisesRegex(ValueError,'changed'):r.validate_claims(ctx,claims,parsed)

    def test_ambiguous_scalar_and_duplicate_html_claim_rejected(self):
        ctx={'root':ROOT,'canonical_output_root':ROOT,'tables':{'saved':pd.DataFrame({'x':[1,2]})},'table_hashes':{'saved':'hash'}}
        with self.assertRaisesRegex(ValueError,'Ambiguous'):content.Report(ctx).number('saved','x')
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            r.ReportHTML('<span data-claim="a">1</span><span data-claim="a">1</span>')

    def test_parser_detects_external_dependencies_and_preserves_sections(self):
        parsed=r.ReportHTML('<section id="a" data-report-section="a"><img src="https://example.invalid/i.png"><a href="#missing">x</a></section>')
        self.assertEqual(parsed.external,['https://example.invalid/i.png']);self.assertEqual(parsed.sections,['a'])
        self.assertNotIn(parsed.links[0][1:],parsed.ids)

    def completion_fixture(self,root):
        (root/'src/restoration_eval').mkdir(parents=True);(root/'notebooks').mkdir();(root/'.git').mkdir()
        (root/'pyproject.toml').write_text('[project]\nname="painting-restoration-eval"\n')
        out=root/'outputs/d04_real_damage_restoration_and_evaluation';out.mkdir(parents=True)
        config=r.yaml.safe_load((ROOT/'config/experiments/real_damage_restoration.yaml').read_text())
        policy=r.yaml.safe_load((ROOT/'config/evaluation/real_damage_report.yaml').read_text())
        report=out/config['outputs']['report'];report.parent.mkdir();report.write_text('test fixture')
        receipt=out/policy['outputs']['receipt']
        r.save(receipt,{'files':{report.relative_to(root).as_posix():r.sha256_file(report)}})
        v=ValidationCollector();v.add(validation_stage='fixture',check_id='test',check_description='Fixture',severity='blocking',passed=True,expected=1,observed=1)
        ctx=dict(root=root,output_root=out,canonical_output_root=out,config=config,policy=policy,validation=v,
                 inventory={'inventory_run_id':'fixture'},input_checksums={},packages={},execution_fingerprint='fixture_hash',
                 started_at_utc=r.utc_now_iso())
        result={'validation_summary':v.summary(),'report_path':report.relative_to(root).as_posix()}
        return ctx,result

    def test_completion_roundtrip_idempotent_and_detects_artifact_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx,result=self.completion_fixture(Path(tmp))
            with patch.object(r,'validate_report',return_value=result):
                final=r.finalize_report(ctx);self.assertTrue(final['completion_gate_passed'])
                manifest=r.path(ctx,ctx['config']['outputs']['run_manifest']);before=manifest.read_bytes()
                self.assertEqual(final,r.finalize_report(ctx));self.assertEqual(before,manifest.read_bytes())
            r.path(ctx,ctx['config']['outputs']['report']).write_text('tampered')
            with self.assertRaisesRegex(ValueError,'artifact changed'):r.audit_completed_report(ctx['root'])

    def test_preview_cannot_finalize(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx,result=self.completion_fixture(Path(tmp));ctx['output_root']=ctx['root']/'preview'
            with patch.object(r,'validate_report') as validator:
                with self.assertRaisesRegex(ValueError,'Preview'):r.finalize_report(ctx)
                validator.assert_not_called()

    def test_failed_validation_writes_no_completed_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx,result=self.completion_fixture(Path(tmp))
            with patch.object(r,'validate_report',side_effect=ValueError('gate failed')):
                with self.assertRaisesRegex(ValueError,'gate failed'):r.finalize_report(ctx)
            self.assertFalse(r.path(ctx,ctx['config']['outputs']['run_manifest']).exists())

    def test_final_audit_failure_restores_previous_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx,result=self.completion_fixture(Path(tmp))
            prior=r.path(ctx,ctx['config']['outputs']['validation']);prior.parent.mkdir();prior.write_bytes(b'previous\n')
            with patch.object(r,'validate_report',return_value=result),patch.object(r,'audit_completed_report',side_effect=ValueError('audit failed')):
                with self.assertRaisesRegex(ValueError,'audit failed'):r.finalize_report(ctx)
            self.assertEqual(prior.read_bytes(),b'previous\n')
            self.assertFalse(r.path(ctx,ctx['config']['outputs']['run_manifest']).exists())
            self.assertFalse(r.path(ctx,ctx['config']['outputs']['artifacts']).exists())


if __name__=='__main__': unittest.main()
