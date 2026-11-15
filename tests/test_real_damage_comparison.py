"""Synthetic fixtures test joins, evidence boundaries, figures and safe resume."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import yaml

import test_real_damage_diagnostics as fixtures
from restoration_eval import real_damage_comparison as r
from restoration_eval.validation import ValidationCollector, ValidationFailure

ROOT=Path(__file__).resolve().parents[1]


def context(root):
    base=fixtures.context(root)
    policy=yaml.safe_load((ROOT/'config/evaluation/real_damage_comparison.yaml').read_text())
    physical=base['candidates'].query("candidate_role == 'primary'").copy()
    desc=[];tech=[]
    for row in physical.to_dict('records'):
        record=r.diagnostics.compute_candidate_diagnostics(base,row);desc.append(record['diagnostics']);tech.append(record['technical'])
    selection=[];synthetic=[];selected=[];classic=[];lpips=[];physical_art=[];synthetic_art=[]
    for i,(pid,group) in enumerate(physical.groupby('painting_id')):
        spid=f'p{i+1:03d}';scase=f'canonical__{spid}__loss_small'
        selection.append(dict(painting_id=pid,real_case_id=group.iloc[0].case_id,category=group.iloc[0].category,
            synthetic_painting_id=spid,synthetic_case_id=scase,synthetic_title=f'Test synthetic painting {i}',
            synthetic_mask_type='loss_small',synthetic_clean_image_path='input.png',real_damage_fraction=.05,
            synthetic_damage_fraction=.055,coverage_gap_percentage_points=.5,real_component_count=30,synthetic_component_count=3,
            real_sd_prompt_policy=r.d04.PROMPT_POLICY_ID,synthetic_sd_prompt_variant='p00_generic'))
        common=dict(source='Synthetic unit-test fixture',license='CC0',source_url='https://example.invalid/test')
        physical_art.append(dict(common,painting_id=pid,title=f'Test physical painting {i}',source_credit='Test fixture',license_url='https://example.invalid/license'))
        synthetic_art.append(dict(common,painting_id=spid,title=f'Test synthetic painting {i}'))
        for j,row in enumerate(group.to_dict('records')):
            cid='synthetic_'+row['candidate_id']
            synthetic.append(dict(row,pair_id=pid,painting_id=spid,case_id=scase,candidate_id=cid))
            selected.append(dict(painting_id=pid,synthetic_case_id=scase,model_id=row['model_id'],candidate_id=cid))
            for metric,region,value in (('mae','masked_region',10+i+j),('ssim','mask_bbox_crop',.8-j*.01),('lpips','mask_bbox_crop',.1+j*.01)):
                record=dict(metric_row_id=cid+'_'+metric,candidate_id=cid,case_id=scase,model_id=row['model_id'],
                    metric_name=metric,region_id=region,restored_value=value,status='ok',metric_version='fixture',region_policy_version='fixture')
                (lpips if metric=='lpips' else classic).append(record)
    sources=dict(classical_metrics=pd.DataFrame(classic),lpips_metrics=pd.DataFrame(lpips),
        physical_artworks=pd.DataFrame(physical_art),synthetic_artworks=pd.DataFrame(synthetic_art))
    return dict(base,policy=policy,diagnostics_policy=base['policy'],validation=ValidationCollector(),
        physical_candidates=physical,physical_diagnostics=pd.DataFrame(desc),physical_technical=pd.DataFrame(tech),
        selection=pd.DataFrame(selection),synthetic_plan=pd.DataFrame(synthetic),sources=sources,
        selected=pd.DataFrame(selected),reference_metrics=r.select_reference_metrics(sources,pd.DataFrame(selected),policy))


class RealDamageComparisonTests(unittest.TestCase):
    def test_both_existing_manifest_cardinality_fields_and_checksum_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);owner=root/'outputs/13_classical_metrics';(owner/'metrics').mkdir(parents=True);(owner/'manifests').mkdir()
            (root/'.git').mkdir();(root/'notebooks').mkdir();(root/'src/restoration_eval').mkdir(parents=True)
            path=owner/'metrics/example.csv';pd.DataFrame({'value':[1,2]}).to_csv(path,index=False)
            rel=path.relative_to(root).as_posix()
            pd.DataFrame([dict(relative_path=rel,checksum=r.sha256_file(path),validation_status='passed',row_count=2)]).to_csv(owner/'manifests/artifacts.csv',index=False)
            for name in ('expected_cardinality','expected_row_count'):
                manifest=dict(run_status='completed',completion_gate_passed=True,outputs=[dict(relative_path=rel,**{name:2})])
                (owner/'manifests/run_manifest.json').write_text(json.dumps(manifest))
                frame,hashes=r._verified_table(root,rel)
                self.assertEqual(len(frame),2);self.assertEqual(len(hashes),3)
            path.write_text('value\n9\n')
            with self.assertRaisesRegex(ValueError,'checksum'):r._verified_table(root,rel)

    def test_full_pipeline_reference_separation_saved_values_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx=context(Path(tmp));r.run_comparison(ctx,progress=lambda _:None)
            self.assertEqual(len(ctx['comparison']),40);self.assertEqual(len(ctx['reference_metrics']),120)
            self.assertTrue(ctx['comparison'][['physical_masked_mae','physical_crop_ssim','physical_crop_lpips']].eq('').all().all())
            self.assertTrue(ctx['synthetic_technical'].changed_outside_pixels.eq(0).all())
            self.assertEqual(int(ctx['comparison'].sd_prompt_policy_difference.sum()),10)
            r.render_outputs(ctx,progress=lambda _:None);summary=r.validate_results(ctx)
            self.assertEqual(summary['artifact_count'],57);self.assertFalse(summary['notebook_completion_gate_passed'])
            with patch.object(r,'_compute_pair',side_effect=AssertionError('must reuse')),patch.object(r,'_render_pair',side_effect=AssertionError('must reuse')):
                r.run_comparison(ctx,progress=lambda _:None);r.render_outputs(ctx,progress=lambda _:None)
            self.assertEqual(ctx['reused_pairs'],10);self.assertEqual(ctx['reused_panel_pairs'],10)
            r.validate_results(ctx)
            ctx['comparison'].loc[0,'synthetic_masked_mae']+=1
            with self.assertRaises((ValidationFailure,AssertionError)):
                r.validate_results(ctx)

    def test_csv_seed_types_normalize_without_concealing_changed_seeds(self):
        left=pd.DataFrame({'candidate_id':['a','b'],'seed':[2026,''],'value':[.2,.3]})
        right=left.copy();right['seed']=['2026','']
        r._same_table(left,right,['candidate_id'])
        right.loc[0,'seed']='2027'
        with self.assertRaises(AssertionError):r._same_table(left,right,['candidate_id'])

    def test_reference_joins_reject_duplicate_wrong_case_and_failed_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx=context(Path(tmp))
            for kind in ('duplicate','wrong_case','failed'):
                sources=dict(ctx['sources']);frame=sources['classical_metrics'].copy()
                if kind=='duplicate':frame=pd.concat([frame,frame.iloc[[0]]],ignore_index=True)
                elif kind=='wrong_case':frame.loc[0,'case_id']='different_case'
                else:frame.loc[0,'status']='failed'
                sources['classical_metrics']=frame
                with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'reference metric'):
                    r.select_reference_metrics(sources,ctx['selected'],ctx['policy'])

    def test_reference_metric_values_and_units_are_not_rescaled(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx=context(Path(tmp));metrics=ctx['reference_metrics']
            self.assertEqual(metrics.iloc[0].value,10)
            self.assertEqual(metrics.iloc[0].units,'RGB_0_255')
            self.assertEqual(metrics.iloc[1].value,.8)
            self.assertTrue(metrics.source_table.str.startswith('outputs/').all())

    def test_detail_crop_is_input_only_largest_component_and_content_clipped(self):
        mask=np.zeros((100,100),bool);mask[10:15,10:15]=True;mask[50:70,50:70]=True
        content=np.zeros_like(mask);content[5:95,5:95]=True
        self.assertEqual(r.detail_bbox(mask,content,margin=8),(42,42,78,78))
        self.assertEqual(r.detail_bbox(mask,content,margin=40),(10,10,95,95))

    def test_checkpoint_recovers_started_units_and_rejects_changed_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx=context(Path(tmp));path=r._path(ctx,'work/comparison/example.json')
            def interrupted():
                r._save(path,{'partial':True});raise KeyboardInterrupt()
            with self.assertRaises(KeyboardInterrupt):r._checkpoint(ctx,'metrics','test',[path],interrupted)
            self.assertFalse(r._checkpoint(ctx,'metrics','test',[path],lambda:r._save(path,{'complete':True})))
            self.assertTrue(r._checkpoint(ctx,'metrics','test',[path],Mock(side_effect=AssertionError())))
            path.write_text('changed')
            with self.assertRaisesRegex(ValueError,'output changed'):r._checkpoint(ctx,'metrics','test',[path],lambda:None)
            with self.assertRaisesRegex(ValueError,'Unverified'):r._checkpoint(ctx,'metrics','unknown',[path],lambda:None)


if __name__=='__main__':unittest.main()
