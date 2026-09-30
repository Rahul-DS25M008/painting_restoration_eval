"""Audit local inspection companions without touching notebooks or benchmark data.

--repair-seam only updates the new inspection companions made with the initial
unnormalized Sobel convention. No neural inference is repeated.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image
from matplotlib import colormaps

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from restoration_eval.metric_inspection import public_contract, VERSION
from build_metric_inspection import seam_difference


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pixels(path,mode=None):
    with Image.open(path) as image:
        return np.asarray(image.convert(mode) if mode else image).copy()


def repair_seam(folder,meta):
    if meta['provenance'].get('seam_gradient_divisor')==8:
        return False
    ref=pixels(ROOT/meta['sources']['reference']['path'],'RGB')
    out=pixels(ROOT/meta['sources']['restored']['path'],'RGB')
    values=seam_difference(ref,out)
    png=folder/'seam.png'
    rgba=colormaps['magma'](np.clip(values,0,1),bytes=True)
    Image.fromarray(rgba).save(png)
    with np.load(folder/'numeric.npz') as saved:
        maps={key:saved[key] for key in saved.files}
    maps['seam']=values.astype(np.float16)
    np.savez_compressed(folder/'numeric.npz',**maps)
    meta['assets']['seam']['sha256']=digest(png)
    meta['assets']['seam']['clipped_fraction']=float(np.mean(values>1))
    mask=pixels(ROOT/meta['regions']['boundary']['path'])>=128
    sampled=values[mask]
    meta['pairs']['local:boundary']['summary']=[dict(mean=float(sampled.mean()),p95=float(np.percentile(sampled,95)))]
    meta['numeric_sha256']=digest(folder/'numeric.npz')
    meta['provenance']['seam_gradient_divisor']=8
    meta['provenance']['seam']='absolute difference of normalized Sobel luminance-gradient magnitude'
    (folder/'manifest.json').write_text(json.dumps(meta,allow_nan=False,separators=(',',':')),encoding='utf-8')
    return True


def audit(folder,repair=False):
    meta=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    if repair:repair_seam(folder,meta)
    assert meta['painting_id']==folder.name and meta['version']==VERSION
    assert meta['candidate_id']==f"candidate__lama__canonical__{folder.name}__mixed_damage__c00"
    policy=public_contract()
    assert set(meta['pairs'])==set(policy)
    for source in meta['sources'].values():
        assert digest(ROOT/source['path'])==source['sha256']
    for collection in ('assets','regions'):
        for record in meta[collection].values():
            path=(ROOT/record['path']).resolve()
            assert path.is_relative_to(folder.resolve())
            assert digest(path)==record['sha256']
            with Image.open(path) as image:
                assert image.size==tuple(meta['shape'][::-1])
    assert digest(folder/'numeric.npz')==meta['numeric_sha256']
    masks={key:pixels(ROOT/value['path'])>=128 for key,value in meta['regions'].items()}
    assert not np.any(masks['outside']&masks['damaged'])
    assert np.all((masks['outside']|masks['damaged'])==masks['content'])
    assert np.all(masks['boundary']<=masks['content'])
    ref=pixels(ROOT/meta['sources']['reference']['path'],'RGB').astype(np.float32)/255
    restored=pixels(ROOT/meta['sources']['restored']['path'],'RGB').astype(np.float32)/255
    damaged=pixels(ROOT/meta['sources']['damaged']['path'],'RGB').astype(np.float32)/255
    error=np.abs(ref-restored).mean(-1)
    baseline=np.abs(ref-damaged).mean(-1)
    with np.load(folder/'numeric.npz') as maps:
        for key in maps.files:
            assert not np.isinf(maps[key]).any(), f'Float16 overflow: {key}'
        for name,expected in [('pixel',error),('improvement',baseline-error),('change',np.abs(restored-damaged).mean(-1))]:
            np.testing.assert_allclose(maps[name],expected,atol=.0005)
        np.testing.assert_allclose(maps['seam'],seam_difference(ref,restored),atol=.0003)
        for key,spec in meta['pairs'].items():
            assert spec['allowed']==policy[key]['allowed'] and spec['role']==policy[key]['role']
            if not spec['allowed']:
                assert 'maps' not in spec
                continue
            support=masks[spec['region']]
            for index,name in enumerate(spec['maps']):
                numeric=maps[name].astype(np.float32)
                assert numeric.shape==tuple(meta['shape'])
                values=numeric[support & np.isfinite(numeric)]
                assert len(values)>0, f'Empty evidence {key}'
                np.testing.assert_allclose(values.mean(),spec['summary'][index]['mean'],rtol=.001,atol=.0006)
                alpha=pixels(ROOT/meta['assets'][name]['path'],'RGBA')[...,3]>0
                assert np.array_equal(alpha,np.isfinite(numeric))
                if spec['region']=='patches':
                    choices=np.array(spec['patch_values'][index],dtype=np.float16)
                    assert set(np.unique(numeric[np.isfinite(numeric)]))<=set(choices.astype(np.float32))
                    assert len(choices)==len(meta['patches'])
    return dict(painting=folder.name,enabled=37,disabled=12,status='passed')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repair-seam',action='store_true')
    parser.add_argument('--paintings',nargs='*')
    parser.add_argument('--require-count',type=int,default=300)
    parser.add_argument('--wait-for-build',action='store_true')
    parser.add_argument('--report',default='.codex_tmp/metric_inspection_audit.json')
    args=parser.parse_args()
    root=ROOT/'streamlit_assets/evidence/metric_framework'
    folders=[root/p for p in args.paintings] if args.paintings else sorted(p.parent for p in root.glob('p*/manifest.json'))
    results=[]
    deadline=time.monotonic()+3600
    for folder in folders:
        while args.wait_for_build and not (folder/'manifest.json').exists():
            if time.monotonic()>deadline:raise TimeoutError(f'Inspection build did not finish: {folder.name}')
            time.sleep(1)
        try:result=audit(folder,args.repair_seam)
        except Exception as exc:result=dict(painting=folder.name,status='failed',error=f'{type(exc).__name__}: {exc}')
        results.append(result)
        if result['status']!='passed' or len(results)%25==0:print(result if result['status']!='passed' else f'{len(results)}/{len(folders)} audited',flush=True)
    report=dict(version=VERSION,count=len(results),expected=args.require_count,passed=sum(r['status']=='passed' for r in results),results=results)
    path=ROOT/args.report;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key!='results'}),flush=True)
    if report['passed']!=args.require_count or len(results)!=args.require_count:raise SystemExit(1)


if __name__=='__main__':main()
