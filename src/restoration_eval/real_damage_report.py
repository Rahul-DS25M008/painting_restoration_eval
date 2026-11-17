"""D04 approved evidence report and final gate. No inference or new metrics.

The user executes the notebook. Preparation is read-only; presentation assets
are separately checkpointed. A completed universal manifest is written last.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
from pathlib import Path
from time import perf_counter
from html.parser import HTMLParser

import numpy as np
import pandas as pd
from PIL import Image, ImageOps
import yaml

from . import real_damage_comparison as comparison
from . import real_damage_restoration as d04
from . import real_damage_report_content as content
from .manifests import (sha256_file, utc_now_iso, build_artifact_record,
    artifact_records_dataframe, build_run_manifest)
from .paths import resolve_repo_path, to_repo_relative
from .real_damage_dataset import audit_inventory_inputs
from .validation import ValidationCollector

VERSION = '1.0.0'
STAGE = 'batch_10_reporting_and_completion'
MODELS = comparison.MODELS
LABELS = comparison.LABELS
SECTIONS = (
    'findings_and_scope', 'physical_cases_and_four_method_restorations',
    'repair_boundaries_and_preserved_context', 'fixed_prompt_seed_variability',
    'descriptive_synthetic_comparisons_with_prompt_difference_disclosed',
    'limitations_provenance_and_expert_study_handoff',
)
read, save, csv = comparison._read, comparison._save, comparison._csv
require = d04._require


def path(ctx, rel):
    d04._relative(rel)
    return ctx['output_root'] / rel


def check(ctx, key, description, passed, observed, expected=True):
    collector = ValidationCollector()
    collector.extend(c for c in ctx['validation'].checks
                     if (c.validation_stage, c.check_id) != (STAGE, key))
    collector.add(validation_stage=STAGE, check_id=key, check_description=description,
                  severity='blocking', passed=bool(passed), observed=observed, expected=expected)
    ctx['validation'] = collector


def verify_comparison(upstream):
    """Audit saved Batch 9 without calling its writers or recomputing metrics."""
    comparison.diagnostics._assert_inputs(upstream)
    root, out = upstream['root'], upstream['output_root']
    policy = upstream['policy']; declared = {}
    summary_path = out / policy['outputs']['stage_summary']
    summary = read(summary_path)
    require(summary['execution_fingerprint'] == upstream['execution_fingerprint'], 'Batch 9 fingerprint changed')
    require(summary['validation_summary']['check_count'] == summary['validation_summary']['passed_count'] == 393
            and summary['validation_summary']['overall_passed'] is True, 'Batch 9 is not complete')
    af = out / policy['outputs']['artifacts']; artifacts = csv(af)
    require(sha256_file(af) == summary['artifacts_sha256'] and len(artifacts) == 57, 'Batch 9 artifact manifest changed')
    for r in artifacts.itertuples():
        p = resolve_repo_path(r.relative_path, root, must_exist=True)
        require(p.is_relative_to(out) and sha256_file(p) == r.sha256 and p.stat().st_size == int(r.size_bytes),
                f'Batch 9 artifact changed: {r.relative_path}')
        declared[r.relative_path] = p
    declared.update({to_repo_relative(p, root): p for p in (af, summary_path)})
    frames = {'comparison': csv(out / upstream['config']['outputs']['synthetic_comparison'])}
    for key in ('synthetic_technical', 'synthetic_diagnostics', 'reference_metrics', 'panel_manifest'):
        frames[key] = csv(out / policy['outputs'][key])
    for kind in ('metrics', 'panels'):
        for row in frames['panel_manifest'].itertuples():
            paths = [out / f'work/comparison/pairs/{row.pair_id}.json'] if kind == 'metrics' else [root / row.full_panel_path, root / row.detail_panel_path]
            receipt = read(out / f'work/comparison/checkpoints/{kind}/{row.pair_id}.json')
            binding = d04._digest(dict(execution=summary['execution_fingerprint'], kind=kind,
                key=row.pair_id, paths=[to_repo_relative(p, root) for p in paths]))
            require(receipt['status'] == 'completed' and receipt['binding'] == binding
                    and receipt['files'] == {to_repo_relative(p, root): sha256_file(p) for p in paths}, 'Batch 9 receipt changed')
    payloads = [read(out / f'work/comparison/pairs/{p}.json') for p in sorted(frames['comparison'].pair_id.unique())]
    for name, key in [('comparison','comparison'), ('synthetic_technical','technical'), ('synthetic_diagnostics','diagnostics')]:
        comparison._same_table(pd.DataFrame([r for v in payloads for r in v[key]]), frames[name], ['pair_id','model_id'])
    comparison._same_table(upstream['reference_metrics'], frames['reference_metrics'], ['candidate_id','anchor_id'])
    checks = csv(out / policy['outputs']['stage_checks'])
    require(len(checks) == 393 and checks.passed.eq(True).all(), 'Saved Batch 9 checks failed')
    table = frames['comparison']
    require(len(table) == 40 and not table.duplicated(['pair_id','model_id']).any()
            and table[['physical_masked_mae','physical_crop_ssim','physical_crop_lpips']].eq('').all().all()
            and table.physical_clean_reference_available.eq(False).all()
            and table.sd_prompt_policy_difference.eq(table.model_id.eq(d04.SD_MODEL)).all(), 'Comparison population or evidence separation failed')
    return frames, checks, declared, summary


def validate_observations(catalog, candidates):
    require(catalog['schema_version'] == 'real_damage_visual_observations.v1'
            and catalog['review_status'] == 'user_approved'
            and catalog['expert_assessment'] is False and catalog['numeric_ratings'] is False,
            'Visual review authority or scope changed')
    frame = pd.DataFrame(catalog['records'])
    primary = candidates.loc[candidates.candidate_role.eq('primary')].set_index('candidate_id')
    require(len(frame) == 40 and frame.candidate_id.is_unique and set(frame.candidate_id) == set(primary.index), 'Incomplete visual review')
    for r in frame.itertuples():
        saved = primary.loc[r.candidate_id]
        require(all(str(getattr(r,k)) == str(saved[k]) for k in
                    ('painting_id','model_id','restored_sha256','input_image_sha256','mask_sha256')), 'Visual review image binding changed')
        require(bool(r.observation.strip()) and bool(r.case_conclusion.strip()), 'Empty visual observation')
    require(frame.groupby('painting_id').case_conclusion.nunique().eq(1).all(), 'Inconsistent case conclusions')
    return frame.assign(review_method=catalog['review_method'], review_status=catalog['review_status'],
                        expert_assessment=False, numeric_rating_available=False)


def prepare_report(project_root, config_path, comparison_context=None):
    root = Path(project_root).resolve(); cp = resolve_repo_path(config_path, root, must_exist=True)
    policy = yaml.safe_load(cp.read_text(encoding='utf-8'))
    require(policy['schema_version'] == 'real_damage_report_config.v1' and policy['stage'] == STAGE
            and tuple(s['id'] for s in policy['sections']) == SECTIONS, 'Approved report structure changed')
    require(all(policy['policy'][k] is False for k in ('new_inference','new_scientific_metrics',
        'physical_reference_metrics','combined_quality_score','expert_validation','best_seed_selection'))
        and policy['policy']['primary_seed'] == 2026, 'Report interpretation policy changed')
    upstream = comparison_context if comparison_context is not None else comparison.prepare_comparison(root, policy['comparison_config'])
    require(upstream['root'] == root, 'Wrong report project root')
    tables, checks, declared, summary = verify_comparison(upstream)
    out = upstream['output_root']; config = upstream['config']
    table_paths = {'comparison': out / config['outputs']['synthetic_comparison']}
    table_paths.update({key: out / upstream['policy']['outputs'][key] for key in
        ('synthetic_technical','synthetic_diagnostics','reference_metrics','panel_manifest')})
    for key in ('candidates','candidate_plan','prompt_policy','model_provenance','runtime_summary',
                'technical_checks','real_damage_diagnostics','seed_pairwise','uncertainty_summary'):
        p = out / config['outputs'][key]; tables[key] = csv(p); declared[key] = p; table_paths[key] = p
    candidates = tables['candidates']
    require(len(candidates) == 70 and candidates.candidate_id.is_unique
            and candidates.candidate_role.eq('primary').sum() == 40
            and tables['technical_checks'].changed_outside_pixels.eq(0).all(), 'Physical candidate population or preservation failed')
    for r in candidates.itertuples():
        for rel, digest in [(r.restored_path,r.restored_sha256),(r.input_image_path,r.input_image_sha256),(r.mask_path,r.mask_sha256)]:
            p = root / rel; require(sha256_file(p) == digest, f'Physical image changed: {rel}'); declared[rel] = p
    for key in ('helper_source','report_source','tests','observations','proposal','comparison_config'):
        declared[key] = resolve_repo_path(policy[key], root, must_exist=True)
    declared['report_config'] = cp
    catalog = read(declared['observations']); observations = validate_observations(catalog, candidates)
    # Existing plots and maps remain original evidence; report transforms are display-only.
    for rel in ('work/diagnostics/primary_boundary_descriptors.png','work/diagnostics/uncertainty_maps_01.png',
                'work/diagnostics/uncertainty_maps_02.png','work/diagnostics/maps.csv',
                'work/diagnostics/batch_summary.json','work/diagnostics/runtime_and_assets.json',
                'work/sd_seeds/batch_summary.json'):
        p = out / rel; require(p.is_file(), f'Missing report evidence: {p}'); declared[rel] = p
    maps = csv(out / 'work/diagnostics/maps.csv')
    for r in maps.itertuples():
        for rel, digest in ((r.array_path,r.array_sha256),(r.preview_path,r.preview_sha256)):
            require(sha256_file(root / rel) == digest, 'Variability map changed'); declared[rel] = root / rel
    inventory, audit = audit_inventory_inputs(root, root / config['inputs']['inventory'], root / config['inputs']['inventory_run'], declared)
    collector = ValidationCollector()
    for r in checks.to_dict('records'): collector.add(**r)
    bindings = {**upstream['input_checksums'], **{to_repo_relative(p,root):sha256_file(p) for p in declared.values()}}
    ctx = dict(root=root, output_root=out, canonical_output_root=out, config=config, policy=policy,
        tables=tables, observations=observations, validation=collector, inventory=inventory,
        model_order=MODELS, table_paths=table_paths,
        table_hashes={key: sha256_file(p) for key,p in table_paths.items()},
        input_checksums=bindings, packages=upstream['packages'], assets=[], maps=maps,
        physical_artworks=upstream['sources']['physical_artworks'].copy(),
        synthetic_artworks=upstream['sources']['synthetic_artworks'].copy(),
        selection=upstream['selection'].copy(), upstream_summary=summary,
        started_at_utc=utc_now_iso())
    ctx['execution_fingerprint'] = d04._digest(dict(inputs=bindings, packages=ctx['packages'], module_version=VERSION))
    check(ctx,'batch9_handoff','Batch 9 payloads, scores, panels and checkpoint bindings verified',True,393,393)
    check(ctx,'approved_review','Forty approved qualitative observations match exact primary images',True,len(observations),40)
    check(ctx,'inventory','Inventory covers report producers, review and evidence',audit.passed.all(),audit.loc[~audit.passed].to_dict('records'),[])
    ctx['validation'].raise_for_blocking()
    return ctx


def _panel(rows, destination, title, column_positions=None):
    """Each row contains labelled image arrays; geometry is never stretched."""
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    width = 2400; cell = 400; row_height = 430
    height=80+row_height*len(rows)
    canvas = Image.new('RGB',(width,height), '#f9f6ec'); labels=[]
    for i,tiles in enumerate(rows):
        for j,(label,array) in enumerate(tiles):
            column=column_positions[i][j] if column_positions else j
            im = Image.fromarray(np.asarray(array,dtype=np.uint8))
            im = ImageOps.contain(im,(384,375),Image.Resampling.LANCZOS)
            y = 80+i*row_height
            labels.append((column*cell+10,y,label))
            canvas.paste(im,(column*cell+(cell-im.width)//2,y+35+(375-im.height)//2))
    fig=Figure(figsize=(width/100,height/100),dpi=100);FigureCanvasAgg(fig)
    ax=fig.add_axes([0,0,1,1]);ax.imshow(canvas);ax.set_axis_off()
    ax.text(20,18,title,color='#173b36',fontsize=18,va='top')
    for x,y,label in labels: ax.text(x,y,label,color='#203e3a',fontsize=13.5,va='top')
    destination.parent.mkdir(parents=True,exist_ok=True);fig.savefig(destination,dpi=100);fig.clear()


def _rgb(root, rel):
    with Image.open(root / rel) as im: return np.array(im.convert('RGB'))


def _crop(array, box):
    x0,y0,x1,y1 = map(int,box); return array[y0:y1,x0:x1]


def render_figures(ctx, progress=print):
    """Generate only declared presentation panels; all source pixels are saved evidence."""
    root=ctx['root']; rows=[]; panels=ctx['tables']['panel_manifest'].set_index('pair_id')
    candidates=ctx['tables']['candidates']; overview=[]
    def register(key, relative, tiles, sources):
        p=path(ctx,relative)
        rows.append(dict(figure_id=key,relative_path=to_repo_relative(p,root),sha256=sha256_file(p),
            tile_count=tiles,sources_json=json.dumps(sorted(set(sources))),role=key.split('_')[0]))
    for pid, group in candidates.groupby('painting_id',sort=True):
        primary=group.loc[group.candidate_role.eq('primary')].set_index('model_id')
        first=primary.iloc[0]; source=_rgb(root,first.input_image_path)
        with Image.open(root / first.mask_path) as m: mask=np.array(m)>=128
        overlay=source.copy(); overlay[mask]=(source[mask]*.65+np.array([0,255,255])*.35).astype('uint8')
        images=[source]+[_rgb(root,primary.loc[m,'restored_path']) for m in MODELS]
        labels=['Damaged input']+[LABELS[m] for m in MODELS]
        box=[panels.loc[pid,'physical_detail_'+k] for k in ('x0','y0','x1','y1')]
        all_rows=[[('Damaged input',source),('Selected mask',overlay)]+list(zip(labels[1:],images[1:])),
                  [(label+' | detail',_crop(im,box)) for label,im in zip(labels,images)]]
        extra=ctx['policy']['visuals']['secondary_detail'].get(pid)
        if extra: all_rows.append([(label+' | arm boundary',_crop(im,extra)) for label,im in zip(labels,images)])
        rel=ctx['config']['outputs']['case_panel_template'].format(painting_id=pid)
        _panel(all_rows,path(ctx,rel),f'{pid} | Four primary restorations | display crops, not metric regions',
               [list(range(6))]+[[0,2,3,4,5] for _ in all_rows[1:]])
        src=[first.input_image_path,first.mask_path]+primary.restored_path.tolist()
        register('case_'+pid,rel,sum(map(len,all_rows)),src)
        sd=group.loc[group.model_id.eq(d04.SD_MODEL)].sort_values('seed')
        seed_tiles=[('Damaged input',source)]+[(f'SD seed {int(r.seed)}',_rgb(root,r.restored_path)) for r in sd.itertuples()]
        rel=ctx['config']['outputs']['seed_panel_template'].format(painting_id=pid)
        _panel([seed_tiles,[(label+' | detail',_crop(im,box)) for label,im in seed_tiles]],path(ctx,rel),
               f'{pid} | Fixed targeted prompt | all four seeds, no best-seed selection')
        register('seed_'+pid,rel,10,[first.input_image_path]+sd.restored_path.tolist())
        overview.append((pid,overlay)); progress(f'Report presentation panels: {len(overview)}/10 paintings | {pid}')
    _panel([overview[:5],overview[5:]],path(ctx,ctx['policy']['outputs']['overview']),
           'Ten physical paintings | cyan marks selected repair targets, not all deterioration')
    register('overview',ctx['policy']['outputs']['overview'],10,
             candidates.input_image_path.tolist()+candidates.mask_path.tolist())
    import matplotlib.pyplot as plt
    u=ctx['tables']['uncertainty_summary']; fig,axes=plt.subplots(1,2,figsize=(11,4.8))
    specs=[('pixel_rgb_std_mean','masked_region','Mean masked RGB standard deviation (0–1)'),
           ('pairwise_lpips_distance','mask_bbox_crop','Mean pairwise crop LPIPS')]
    for ax,(metric,region,label) in zip(axes,specs):
        selected=u.loc[u.metric_name.eq(metric)&u.region_id.eq(region)].sort_values('painting_id')
        ax.barh(selected.painting_id,pd.to_numeric(selected.value),color='#21574e')
        ax.set_xlabel(label); ax.invert_yaxis(); ax.grid(axis='x',alpha=.2)
    fig.suptitle('Different variability measures describe different differences')
    fig.tight_layout(); rel=ctx['policy']['outputs']['variability_plot']; fig.savefig(path(ctx,rel),dpi=150);plt.close(fig)
    register('variability_measures',rel,2,[to_repo_relative(ctx['canonical_output_root']/ctx['config']['outputs']['uncertainty_summary'],root)])
    result=pd.DataFrame(rows); save(path(ctx,ctx['policy']['outputs']['figure_catalog']),result)
    ctx['figures']=result;return result


def build_report(ctx, progress=print):
    comparison.diagnostics._assert_inputs(ctx)
    receipt_path=path(ctx,ctx['policy']['outputs']['receipt'])
    if receipt_path.exists():
        receipt=read(receipt_path)
        require(receipt['execution_fingerprint']==ctx['execution_fingerprint'],'Report producer or evidence changed after build')
        if receipt['status']=='completed':
            require(all(sha256_file(ctx['root']/p)==h for p,h in receipt['files'].items()),'Completed report output changed')
            ctx['figures']=csv(path(ctx,ctx['policy']['outputs']['figure_catalog']))
            ctx['metadata']=read(path(ctx,ctx['policy']['outputs']['report_metadata']))
            progress('Reused the verified completed report presentation build.')
            return ctx['metadata']
        require(receipt['status']=='started','Invalid report receipt state')
    else:
        require(not path(ctx,ctx['config']['outputs']['report']).exists(),'Unverified report already exists')
        save(receipt_path,dict(status='started',execution_fingerprint=ctx['execution_fingerprint']))
    started=perf_counter()
    save(path(ctx,ctx['config']['outputs']['case_observations']),ctx['observations'])
    render_figures(ctx,progress)
    html,assets,claims,traceability=content.render(ctx)
    report=path(ctx,ctx['config']['outputs']['report']);report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(html,encoding='utf-8')
    for key,frame in [('asset_catalog',assets),('claim_catalog',claims),('traceability',traceability)]:
        save(path(ctx,ctx['policy']['outputs'][key]),frame)
    metadata=dict(schema_version='real_damage_report_metadata.v1',execution_fingerprint=ctx['execution_fingerprint'],
        report_path=to_repo_relative(report,ctx['root']),report_sha256=sha256_file(report),
        embedded_images=len(assets),embedded_tiles=int(assets.tile_count.sum()),section_order=list(SECTIONS),
        numerical_claims=len(claims),approved_mock_elements=len(traceability),
        visual_review='reviewed automated visual inspection; model identities visible; not external expert ratings',
        report_size_bytes=report.stat().st_size,build_seconds=perf_counter()-started)
    save(path(ctx,ctx['policy']['outputs']['report_metadata']),metadata);ctx['metadata']=metadata
    files=[report,path(ctx,ctx['config']['outputs']['case_observations'])]
    files += [path(ctx,ctx['policy']['outputs'][k]) for k in ('asset_catalog','claim_catalog','traceability','figure_catalog','report_metadata')]
    files += [ctx['root']/r for r in ctx['figures'].relative_path]
    save(receipt_path,dict(status='completed',execution_fingerprint=ctx['execution_fingerprint'],
        completed_at_utc=utc_now_iso(),files={to_repo_relative(p,ctx['root']):sha256_file(p) for p in files}))
    return metadata


class ReportHTML(HTMLParser):
    """Extract report structure and embedded payloads without browser execution."""
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids=[]; self.sections=[]; self.images={}; self.links=[]; self.external=[]
        self.claims={}; self.active_claim=None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if a.get('id'): self.ids.append(a['id'])
        if a.get('data-report-section'): self.sections.append(a['data-report-section'])
        if tag=='a': self.links.append(a.get('href',''))
        if tag=='img' and a.get('data-asset'):
            require(a['data-asset'] not in self.images,'Duplicate embedded asset')
            self.images[a['data-asset']]=a
        if tag in ('img','script','link'):
            url=a.get('src',a.get('href',''))
            if url and not url.startswith('data:'): self.external.append(url)
        if a.get('data-claim'):
            self.active_claim=a['data-claim']
            require(self.active_claim not in self.claims,'Duplicate numerical claim')
            self.claims[self.active_claim]=''

    def handle_endtag(self, tag):
        if tag=='span': self.active_claim=None

    def handle_data(self, data):
        if self.active_claim: self.claims[self.active_claim]+=data


def validate_claims(ctx, claims, parsed):
    require(claims.claim_id.is_unique and set(claims.claim_id)==set(parsed.claims),'Report claim coverage changed')
    for r in claims.itertuples():
        frame=ctx['tables'][r.table]
        for k,v in json.loads(r.filters_json).items(): frame=frame.loc[frame[k].eq(v)]
        if r.operation=='count': value=len(frame)
        elif r.operation=='nunique': value=frame[r.field].nunique()
        elif r.operation=='sum': value=pd.to_numeric(frame[r.field]).sum()
        else:
            require(r.operation=='value' and len(frame)==1,'Ambiguous numerical claim')
            value=float(frame.iloc[0][r.field])
        value=float(value)
        expected=f'{value*float(r.display_scale):,.{int(r.decimals)}f}'
        require(np.isfinite(value) and np.isclose(value,float(r.value),rtol=0,atol=1e-12)
                and expected==str(r.display_value)==parsed.claims[r.claim_id]
                and r.source_table_sha256==ctx['table_hashes'][r.table],f'Numerical claim changed: {r.claim_id}')


def validate_report(ctx):
    """Read-only gate; never repairs evidence or silently replaces a report."""
    comparison.diagnostics._assert_inputs(ctx)
    receipt=read(path(ctx,ctx['policy']['outputs']['receipt']))
    require(receipt['status']=='completed' and receipt['execution_fingerprint']==ctx['execution_fingerprint'],
            'Report build is incomplete or stale')
    require(all((ctx['root']/p).is_file() and sha256_file(ctx['root']/p)==h for p,h in receipt['files'].items()),
            'Report build output changed')
    check(ctx,'report_receipt','Report outputs match completed producer receipt',True,len(receipt['files']))
    tables=ctx['tables'];expected=ctx['policy']['expected']
    sizes={'total_candidates':len(tables['candidates']),'primary_candidates':int(tables['candidates'].candidate_role.eq('primary').sum()),
           'paintings':tables['candidates'].painting_id.nunique(),'comparison_rows':len(tables['comparison']),
           'seed_pairwise_rows':len(tables['seed_pairwise']),'uncertainty_summary_rows':len(tables['uncertainty_summary']),
           'synthetic_reference_metric_rows':len(tables['reference_metrics']),'observations':len(ctx['observations'])}
    require(all(n==expected[k] for k,n in sizes.items()),'Report population changed')
    sd=tables['candidates'].loc[tables['candidates'].model_id.eq(d04.SD_MODEL)]
    require(sd.uncertainty_group_id.nunique()==10 and sd.groupby('painting_id').seed.apply(lambda x:set(pd.to_numeric(x))=={2026,2027,2028,2029}).all(),
            'Four-seed population changed')
    check(ctx,'populations','All primary and repeated candidates and saved measurement rows retained',True,sizes)
    saved_observations=csv(path(ctx,ctx['config']['outputs']['case_observations']))
    comparison._same_table(ctx['observations'],saved_observations,['candidate_id'])
    check(ctx,'observation_export','Approved descriptions exported without altered bindings',True,len(saved_observations))
    outputs=ctx['policy']['outputs']
    figures=csv(path(ctx,outputs['figure_catalog']));assets=csv(path(ctx,outputs['asset_catalog']))
    claims=csv(path(ctx,outputs['claim_catalog']));trace=csv(path(ctx,outputs['traceability']))
    required_figures={'overview','variability_measures'}|{f'{role}_rd{i:03}' for role in ('case','seed') for i in range(1,11)}
    require(figures.figure_id.is_unique and set(figures.figure_id)==required_figures,'Report figure roles incomplete')
    for row in figures.itertuples():
        require(sha256_file(ctx['root']/row.relative_path)==row.sha256,'Figure changed')
        with Image.open(ctx['root']/row.relative_path) as im: im.verify()
        for src in json.loads(row.sources_json): require((ctx['root']/src).is_file(),f'Figure source missing: {src}')
    report=path(ctx,ctx['config']['outputs']['report']);text=report.read_text(encoding='utf-8');parsed=ReportHTML(text)
    require(parsed.sections==list(SECTIONS) and len(parsed.ids)==len(set(parsed.ids)),'Report structure differs from approved outline')
    require(not parsed.external and all(url[1:] in parsed.ids for url in parsed.links if url.startswith('#')),
            'Report contains external required assets or broken internal navigation')
    require(all(url not in ('','nan','None') for url in parsed.links),'Missing source link')
    check(ctx,'structure_and_offline','Six approved sections, unique anchors and self-contained assets',True,parsed.sections)
    require(assets.asset_id.is_unique and set(assets.asset_id)==set(parsed.images),'Image catalog differs from report')
    require(len(assets)==ctx['policy']['visuals']['expected_images'] and int(assets.tile_count.sum())==ctx['policy']['visuals']['expected_tiles'],
            'Approved image or tile count changed')
    for row in assets.itertuples():
        a=parsed.images[row.asset_id]
        require(a['src'].startswith('data:image/jpeg;base64,'),'Unexpected report image encoding')
        raw=base64.b64decode(a['src'].split(',',1)[1],validate=True)
        require(hashlib.sha256(raw).hexdigest()==row.embedded_sha256 and len(raw)==row.embedded_size_bytes
                and sha256_file(ctx['root']/row.source_path)==row.source_sha256,'Embedded image or source changed')
        with Image.open(io.BytesIO(raw)) as im:
            require(im.size==(int(row.width),int(row.height)),'Embedded image dimensions changed');im.verify()
        require(bool(a.get('alt')),'Image alternative text missing')
    require(report.stat().st_size<=ctx['policy']['visuals']['max_report_bytes'],'Report exceeds approved size allowance')
    check(ctx,'all_visuals','All declared figures and embedded image payloads verified',True,dict(images=len(assets),tiles=int(assets.tile_count.sum())))
    validate_claims(ctx,claims,parsed)
    check(ctx,'numerical_claims','Each displayed quantitative claim agrees with its saved table and filters',True,len(claims))
    required_roles={'section_'+str(i) for i in range(1,7)}|required_figures
    required_roles|={f'case_findings_rd{i:03}' for i in range(1,11)}
    required_roles|={f'comparison_{kind}_rd{i:03}' for kind in ('full','detail') for i in range(1,11)}
    required_roles|={'extended_'+x for x in ctx['policy']['visuals']['extended_case_discussions']}
    required_roles|={'synthetic_story_'+x for x in ctx['policy']['visuals']['prominent_synthetic_pairs']}
    required_roles|={'opening_findings','boundary_examples','variability_examples','thesis_synthesis','limitations','expert_handoff','provenance'}
    require(trace.mock_element_id.is_unique and required_roles<=set(trace.mock_element_id)
            and trace.implementation_status.isin(['preserved','upgraded_additively']).all()
            and trace.mock_section.eq(trace.final_section).all() and trace.deviation_reason.eq('').all(),
            'Approved report elements missing or silently deviated')
    for row in trace.itertuples():
        for source in row.canonical_evidence_source.split('; '):
            target=ctx['root']/source
            if target.is_relative_to(ctx['canonical_output_root']):
                preview=ctx['output_root']/target.relative_to(ctx['canonical_output_root'])
                if preview.is_file(): target=preview
            require(target.is_file(),f'Traceability source missing: {source}')
    require(all(f'id="case-rd{i:03}"' in text for i in range(1,11)),'Case gallery incomplete')
    check(ctx,'mock_traceability','Approved sections, findings, examples and visual roles preserved',True,len(trace))
    require('expert ratings' in text and 'generic prompt' in text and 'no clean' in text.lower(), 'Required interpretation boundaries missing')
    check(ctx,'evidence_boundaries','Non-expert review, no physical reference and differing prompt policies disclosed',True,True)
    ctx['validation'].raise_for_blocking()
    return dict(validation_summary=ctx['validation'].summary(),report_path=to_repo_relative(report,ctx['root']),
                embedded_images=len(assets),embedded_tiles=int(assets.tile_count.sum()),numerical_claims=len(claims),
                completion_gate_passed=False,notebook_status='report_validated_finalization_pending')


def finalize_report(ctx):
    """Write the authoritative completion record last, after all evidence gates."""
    require(ctx['output_root']==ctx['canonical_output_root'],'Preview contexts cannot finalize a notebook')
    result=validate_report(ctx)
    manifest_path=path(ctx,ctx['config']['outputs']['run_manifest'])
    if manifest_path.exists():
        old=read(manifest_path)
        require(old.get('execution_fingerprint')==ctx['execution_fingerprint'],'A different completed D04 manifest exists')
        return audit_completed_report(ctx['root'],ctx['config']['notebook']['output_root'])
    outputs=ctx['policy']['outputs']; checks=ctx['validation'].to_dataframe()
    target_paths=[path(ctx,outputs['stage_checks']),path(ctx,ctx['config']['outputs']['validation']),
                  path(ctx,outputs['summary']),path(ctx,ctx['config']['outputs']['artifacts']),manifest_path]
    backups={p:p.read_bytes() if p.exists() else None for p in target_paths}
    try:
        save(target_paths[0],checks);save(target_paths[1],checks)
        completed=utc_now_iso()
        summary=dict(result,stage=STAGE,completed_at_utc=completed,execution_fingerprint=ctx['execution_fingerprint'],
            completion_gate_passed=True,notebook_status='completed',new_inference=False,new_scientific_metrics=False)
        save(target_paths[2],summary)
        receipt=read(path(ctx,outputs['receipt']))
        owned={ctx['root']/p for p in ctx['input_checksums'] if (ctx['root']/p).is_relative_to(ctx['canonical_output_root'])}
        owned.update(ctx['root']/p for p in receipt['files'])
        owned.update(target_paths[:3]);owned.add(path(ctx,outputs['receipt']))
        records=[]
        for p in sorted(owned):
            relative=p.relative_to(ctx['output_root']).as_posix()
            kind='report' if p.suffix=='.html' else 'figure' if p.suffix=='.png' else 'table' if p.suffix=='.csv' else 'evidence'
            records.append(build_artifact_record(artifact_key='D04:'+relative,producer_notebook='D04',path=p,
                artifact_type=kind,artifact_role='saved_physical_restoration_evidence' if 'report' not in relative else 'approved_report',
                schema_version='d04_evidence.v1',dataset_scope='real_damage_10',
                experiment_id=ctx['config']['dataset']['experiment_id'],project_root=ctx['root']))
        artifacts=artifact_records_dataframe(records);save(target_paths[3],artifacts)
        configuration={p:h for p,h in ctx['input_checksums'].items() if p.startswith('config/')}
        manifest=build_run_manifest(notebook_id='D04',notebook_name=ctx['config']['notebook']['stem'],
            origin='user_executed_notebook',run_status='completed',started_at_utc=ctx['started_at_utc'],completed_at_utc=completed,
            inventory_run_id=ctx['inventory']['inventory_run_id'],dataset_versions=ctx['config']['dataset'],
            configuration_paths=sorted(configuration),configuration_checksums_by_path=configuration,
            helper_versions={'real_damage_report':VERSION,'real_damage_report_content':content.VERSION},
            inputs=[dict(relative_path=p,checksum=h) for p,h in sorted(ctx['input_checksums'].items())],outputs=records,
            expected_counts=ctx['policy']['expected'],observed_counts=dict(total_candidates=70,primary_candidates=40,
                paintings=10,sd_groups=10,comparison_rows=40,seed_pairwise_rows=720,uncertainty_summary_rows=220,
                synthetic_reference_metric_rows=120,observations=40,batch9_checks=393),
            validation_summary=ctx['validation'].summary(),known_limitations=[
                'No clean reference for physical paintings; no physical fidelity metrics or correctness claims.',
                'Ten purposively selected paintings, two per operational category; non-exhaustive masks.',
                'Qualitative automated visual inspection reviewed during the study; identities visible; no expert ratings.',
                'Targeted physical SD prompts differ from generic synthetic prompts; descriptive comparison only.',
                'Outside-mask preservation is enforced by compositing; disagreement is not calibrated confidence.'],
            project_root=ctx['root'],package_names=ctx['packages'],run_id='run_d04_'+ctx['execution_fingerprint'][:24])
        manifest.update(completion_gate_passed=True,downstream_ready=True,execution_fingerprint=ctx['execution_fingerprint'],
            data_fingerprint=ctx['execution_fingerprint'],artifacts_sha256=sha256_file(target_paths[3]),
            evidence_scope='physical_no_reference_and_separate_frozen_synthetic_context',report=result['report_path'])
        # Atomic JSON replacement is the final commit marker; rollback on failure.
        save(manifest_path,manifest)
        return audit_completed_report(ctx['root'],ctx['config']['notebook']['output_root'])
    except BaseException:
        for p,raw in backups.items():
            if raw is None: p.unlink(missing_ok=True)
            else: p.write_bytes(raw)
        raise


def audit_completed_report(project_root, output_root='outputs/d04_real_damage_restoration_and_evaluation'):
    """Read-only audit of the published local completion record and every artifact."""
    root=Path(project_root).resolve();out=root/output_root
    manifest=read(out/'manifests/run_manifest.json')
    require(manifest['run_status']=='completed' and manifest['completion_gate_passed'] is True
            and manifest['validation_summary']['overall_passed'] is True,'D04 completion gate is not passed')
    ap=out/'manifests/artifacts.csv';require(sha256_file(ap)==manifest['artifacts_sha256'],'Artifact manifest changed')
    artifacts=csv(ap)
    require(len(artifacts)==len(manifest['outputs']) and artifacts.relative_path.is_unique,'Artifact cardinality changed')
    for r in artifacts.itertuples():
        p=resolve_repo_path(r.relative_path,root,must_exist=True)
        require(p.is_relative_to(out) and sha256_file(p)==r.checksum and p.stat().st_size==int(r.size_bytes),
                f'Completed D04 artifact changed: {r.relative_path}')
    for r in manifest['inputs']:
        require(sha256_file(resolve_repo_path(r['relative_path'],root,must_exist=True))==r['checksum'],
                f'Completed D04 input changed: {r["relative_path"]}')
    require(set(artifacts.relative_path)=={r['relative_path'] for r in manifest['outputs']},'Manifest output registration differs')
    return dict(run_id=manifest['run_id'],completion_gate_passed=True,run_status='completed',
        validation_summary=manifest['validation_summary'],artifact_count=len(artifacts),report_path=manifest['report'])
