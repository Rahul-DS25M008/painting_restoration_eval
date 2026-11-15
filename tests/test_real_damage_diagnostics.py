"""Small synthetic-image tests; no study metrics, inference or weight downloads."""
from itertools import combinations
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import numpy as np
import pandas as pd
from PIL import Image
import yaml

from restoration_eval import real_damage_diagnostics as r
from restoration_eval.validation import ValidationCollector, ValidationFailure

ROOT=Path(__file__).resolve().parents[1]


class FakeLPIPS:
    def __init__(self):self.calls=0
    def __call__(self,a,b):
        self.calls+=1
        return (a-b).abs().mean(dim=(1,2,3),keepdim=True)


def context(root):
    (root/'.git').mkdir(exist_ok=True)
    (root/'pyproject.toml').write_text('[project]\nname="painting-restoration-eval"\n')
    (root/'src/restoration_eval').mkdir(parents=True,exist_ok=True)
    (root/'notebooks').mkdir(exist_ok=True)
    (root/'config').mkdir(exist_ok=True)
    policy=yaml.safe_load((ROOT/'config/evaluation/real_damage_diagnostics.yaml').read_text())
    main=yaml.safe_load((ROOT/'config/experiments/real_damage_restoration.yaml').read_text())
    rows=[];pairs=[]
    mask=np.zeros((32,32),np.uint8);mask[12:20,12:20]=255
    source=np.full((32,32,3),80,np.uint8);source[:4]=0;source[28:]=0
    source[mask>0]=240
    Image.fromarray(source).save(root/'input.png');Image.fromarray(mask).save(root/'mask.png')
    for i in range(10):
        pid=f'rd{i+1:03d}';gid=f'group_{pid}'
        for j,(model,seed) in enumerate([('opencv_telea',''),('lama',''),('hint_places2','')]+[(r.MODEL,s) for s in range(2026,2030)]):
            cid=f'{pid}_{j}';array=source.copy();array[mask>0]=100+(j-3)*10
            filename=f'{cid}.png';Image.fromarray(array).save(root/filename)
            row={key:'synthetic_fixture' for key in r.uncertainty.GROUP_METADATA_COLUMNS}
            row.update(candidate_id=cid,painting_id=pid,case_id=f'case_{pid}',category=f'category_{i//2}',model_id=model,
                seed=seed,candidate_role='primary' if j<4 else 'additional_seed',uncertainty_group_id=gid if model==r.MODEL else '',
                input_image_path='input.png',mask_path='mask.png',mask_or_effect_path='mask.png',mask_threshold=128,
                restored_path=filename,restored_sha256=r.sha256_file(root/filename),output_width=32,output_height=32,
                content_x_min=0,content_y_min=4,content_x_max=32,content_y_max=28,seed_count=4,expected_seed_count=4,
                seed_coverage_status='complete',target_damage_fraction='',realized_damage_fraction=64/768,
                has_clean_reference=False,clean_image_path='')
            rows.append(row)
        for a,b in combinations(rows[-4:],2):
            pairs.append(dict(uncertainty_group_id=gid,candidate_id_a=a['candidate_id'],candidate_id_b=b['candidate_id'],seed_a=a['seed'],seed_b=b['seed']))
    table=pd.DataFrame(rows)
    ctx=dict(root=root,output_root=root/main['notebook']['output_root'],config=main,policy=policy,
        candidates=table,validation=ValidationCollector(),input_checksums={},assets=[],packages={},
        execution_fingerprint='test_only',seed_pair_plan=pd.DataFrame(pairs),region_manifest=pd.DataFrame(),
        uncertainty_config=r.uncertainty.load_diffusion_uncertainty_config(ROOT/policy['uncertainty_config']),
        spatial_config=r.spatial.load_spatial_explanations_config(ROOT/policy['spatial_config']),
        lpips_config=r.lpips_metrics.load_lpips_config(ROOT/policy['lpips_config']))
    ctx['input_checksums']={row.restored_path:row.restored_sha256 for row in table.itertuples()}
    return ctx


class RealDamageDiagnosticsTests(unittest.TestCase):
    def test_full_population_analytic_values_render_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx=context(Path(tmp));fake=FakeLPIPS()
            r.run_diagnostics(ctx,progress=lambda _:None)
            r.run_uncertainty(ctx,model=fake,progress=lambda _:None)
            self.assertEqual(fake.calls,20)
            pair=ctx['seed_pairwise'].query("metric_name == 'pairwise_rgb_mae' and region_id == 'masked_region' and seed_a == 2026 and seed_b == 2027")
            np.testing.assert_allclose(pair.value,10/255,atol=1e-7)
            std=ctx['uncertainty_summary'].query("metric_name == 'pixel_rgb_std_mean' and region_id == 'masked_region'")
            np.testing.assert_allclose(std.value,np.std([100,110,120,130])/255,atol=1e-7)
            self.assertTrue(ctx['technical'].changed_outside_pixels.eq(0).all())
            self.assertTrue(ctx['diagnostics'].masked_edit_rgb_mean.gt(0).all())
            self.assertNotIn('full_image',set(ctx['seed_pairwise'].region_id))
            r.render_outputs(ctx);summary=r.validate_results(ctx)
            self.assertEqual(summary['pairwise_rows'],720);self.assertEqual(summary['group_summary_rows'],220)
            self.assertFalse(summary['notebook_completion_gate_passed'])
            r.run_diagnostics(ctx,progress=lambda _:None)
            r.run_uncertainty(ctx,model=Mock(side_effect=AssertionError('must reuse')),progress=lambda _:None)
            self.assertEqual(ctx['reused_candidate_diagnostics'],70);self.assertEqual(ctx['reused_uncertainty_groups'],10)
            r.render_outputs(ctx)
            ctx['seed_pair_plan'].loc[0,'candidate_id_a']='wrong_candidate'
            with self.assertRaises(ValidationFailure):r.validate_results(ctx)

    def test_identical_seed_outputs_have_zero_disagreement_but_nonzero_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx=context(Path(tmp));group=ctx['candidates'].query('model_id == @r.MODEL').iloc[:4].copy()
            group['restored_path']=group.iloc[0].restored_path
            pixels=r.uncertainty.compute_group_image_uncertainty(group,project_root=ctx['root'],config=ctx['uncertainty_config'])
            self.assertTrue(pixels.value.le(1e-7).all())
            result=r.compute_candidate_diagnostics(ctx,group.iloc[0])
            self.assertGreater(result['diagnostics']['masked_edit_rgb_mean'],0)

    def test_padding_masks_and_changed_outside_pixels_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx=context(Path(tmp));row=ctx['candidates'].iloc[0].copy()
            bad=np.zeros((32,32),np.uint8);bad[0:18,12:20]=255;Image.fromarray(bad).save(ctx['root']/'badmask.png')
            row['mask_path']='badmask.png'
            with self.assertRaisesRegex(ValueError,'padding'):r.candidate_regions(ctx,row)
            path=ctx['root']/ctx['candidates'].iloc[0].restored_path
            array=np.asarray(Image.open(path)).copy();array[0,0]=255;Image.fromarray(array).save(path)
            ctx['input_checksums'][path.name]=r.sha256_file(path)
            with self.assertRaisesRegex(ValueError,'outside'):r.run_diagnostics(ctx,progress=lambda _:None)

    def test_checkpoint_interruption_recovers_but_tampering_and_unknown_files_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx=context(Path(tmp));path=r._path(ctx,'work/diagnostics/unit.txt')
            def interrupted():
                path.write_text('partial');raise KeyboardInterrupt()
            with self.assertRaises(KeyboardInterrupt):r._checkpoint(ctx,'candidate','a',[path],interrupted)
            self.assertFalse(r._checkpoint(ctx,'candidate','a',[path],lambda:path.write_text('complete')))
            self.assertTrue(r._checkpoint(ctx,'candidate','a',[path],Mock(side_effect=AssertionError())))
            path.write_text('tampered')
            with self.assertRaisesRegex(ValueError,'changed'):r._checkpoint(ctx,'candidate','a',[path],lambda:None)
            unknown=r._path(ctx,'work/diagnostics/unknown.txt');unknown.write_text('unowned')
            with self.assertRaisesRegex(ValueError,'Unverified'):r._checkpoint(ctx,'candidate','b',[unknown],lambda:None)

    def test_incomplete_seed_group_is_rejected_before_model_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx=context(Path(tmp));group=ctx['candidates'].query('model_id == @r.MODEL').iloc[:3]
            with self.assertRaisesRegex(ValueError,'seed set'):
                r._compute_group(ctx,group,r._path(ctx,'work/test.csv'),r._path(ctx,'work/test.npz'),Mock(side_effect=AssertionError()))

    def test_boundary_contrast_is_not_a_reference_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx=context(Path(tmp));row=ctx['candidates'].iloc[3]
            source,mask,regions=r.candidate_regions(ctx,row)
            lstar,delta_e=r.boundary_gaps(source,regions)
            self.assertGreater(lstar,0);self.assertGreater(delta_e,0)
            # Even a perfectly preserved natural edge has a nonzero raw band gap.
            source[mask]=source[~mask][100]
            self.assertLess(r.boundary_gaps(source,regions)[0],lstar)


if __name__=='__main__':unittest.main()
