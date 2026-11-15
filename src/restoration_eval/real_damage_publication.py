"""D03 canonical persistence and self-contained reporting, before completion."""
from __future__ import annotations

import base64
import hashlib
import html
import io
import json
from pathlib import Path
from typing import Any, Callable, Mapping
from time import perf_counter
from urllib.parse import urlsplit

import numpy as np
import pandas as pd
import yaml
from PIL import Image

from .manifests import (artifact_records_dataframe, build_artifact_record, build_run_manifest,
                       sha256_file, sha256_path, utc_now_iso)
from .paths import notebook_output_root, require_notebook_output_path, resolve_repo_path, to_repo_relative
from .real_damage_dataset import NOTEBOOK_STEM, _require, audit_inventory_inputs, validate_binary_damage_mask
from .real_damage_eligibility import ELIGIBILITY_STAGE, refresh_eligibility_context
from .real_damage_preparation import _atomic_write
from .validation import ValidationCollector

REAL_DAMAGE_PUBLICATION_MODULE_VERSION = "1.0.0"
PUBLICATION_STAGE = "batch_7_canonical_publication"
HANDOFF_CONDITION = "requires_completed_D03_manifest"
TABLE_NAMES = ("artworks", "preprocessed_images", "masks", "mask_review", "case_registry",
               "model_eligibility", "mask_geometry", "inference_mask_audit")
ELIGIBILITY_TABLES = tuple(k for k in TABLE_NAMES if k not in {"artworks", "preprocessed_images"})


def load_publication_config(path: str | Path) -> dict[str, Any]:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    required = {"config_schema_version":"real_damage_publication_config.v1", "dataset_scope":"real_damage_10",
        "dataset_version":"2.0.0", "completion_gate_batch":8, "publication_run_status":"partial",
        "overwrite_scientific_artifacts":False, "report_embeds_images":True,
        "expected_canonical_files":34, "expected_artifact_records":14}
    _require(all(config.get(k)==v for k,v in required.items()), "Publication config changes the approved contract")
    _require(type(config.get('figure_dpi')) is int and 100<=config['figure_dpi']<=200, "Unsupported figure resolution")
    return config


def refresh_publication_context(project_root: str | Path, config_path: str | Path,
        eligibility_config_path: str | Path, publication_config_path: str | Path, *,
        previous_config: Mapping[str, Any], previous_input_checksums: Mapping[str, str],
        previous_validation: ValidationCollector) -> dict[str, Any]:
    root=Path(project_root).resolve()
    context=refresh_eligibility_context(root,config_path,eligibility_config_path,previous_config=previous_config,
        previous_input_checksums={k:v for k,v in previous_input_checksums.items() if not k.startswith('publication.')},
        previous_validation=previous_validation)
    config=load_publication_config(publication_config_path)
    output=notebook_output_root(NOTEBOOK_STEM,root)
    work=output/context['eligibility_config']['output_work_directory']
    extra={'publication.config':Path(publication_config_path).resolve(),
        'publication.helper_source':resolve_repo_path(config['inputs']['helper_source'],root),
        'publication.eligibility_checkpoint':work/'eligibility_checkpoint.json',
        **{f'publication.prepared_{key}':work/f'{key}.csv' for key in ELIGIBILITY_TABLES},
        'publication.preprocessed_checkpoint':output/context['config']['preparation']['candidate_directory']/context['config']['preparation']['preprocessing_checkpoint']}
    _,audit=audit_inventory_inputs(root,context['inputs']['inventory'],context['inputs']['inventory_run'],extra)
    _require(bool(audit.passed.all()),f"Publication inputs need current inventory: {audit.loc[~audit.passed].to_dict('records')}")
    context['inputs'].update(extra)
    context['input_checksums'].update({k:sha256_file(p) for k,p in extra.items()})
    context['input_audit']=pd.concat([context['input_audit'],audit],ignore_index=True)
    context['publication_config']=config
    return context


def _same_csv(frame: pd.DataFrame, path: Path) -> None:
    pd.testing.assert_frame_equal(pd.read_csv(path),pd.read_csv(io.StringIO(frame.to_csv(index=False))),
        check_dtype=False,check_exact=False,rtol=1e-12,atol=1e-12)


def overview_figure(images: list[Image.Image], masks: list[Image.Image], ids: list[str],
                    fractions: list[float], *, overlay: bool, dpi: int) -> bytes:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    figure=Figure(figsize=(16,8.2),dpi=dpi)
    FigureCanvasAgg(figure)
    axes=figure.subplots(2,5)
    for axis,image,mask,pid,fraction in zip(axes.flat,images,masks,ids,fractions):
        rgb=np.asarray(image).astype(float)
        if overlay:
            selected=np.asarray(mask)==255
            rgb[selected]=.42*rgb[selected]+.58*np.array([255,30,55])
        axis.imshow(rgb.astype(np.uint8))
        axis.set_title(f'{pid} | selected repair: {fraction:.2%}',fontsize=11)
        axis.axis('off')
    figure.suptitle('D03 | Approved selected repair masks' if overlay else 'D03 | Physically damaged painting inputs',fontsize=19)
    figure.text(.5,.91,'Red indicates selected repair pixels; unselected deterioration may remain.' if overlay else
        'Ten sources, two per operational category. No clean-reference images are available.',ha='center',fontsize=11)
    figure.subplots_adjust(top=.85,bottom=.12,left=.015,right=.985,hspace=.2,wspace=.06)
    figure.text(.5,.055,'rd004: Tyler Bell, CC BY 2.0 | rd005: BeakheadIntrados, CC BY-SA 4.0 | rd006: The Met, CC0 | Others: source-stated public domain.',ha='center',fontsize=8.5)
    figure.text(.5,.028,'Adaptations: resized and padded; review overlays added where shown. Full source links, credits and licences are retained in the report and artworks table.',ha='center',fontsize=8.5)
    buffer=io.BytesIO();figure.savefig(buffer,format='png',facecolor='white')
    return buffer.getvalue()


def _link(url: Any, label: str) -> str:
    value=str(url or '')
    if urlsplit(value).scheme not in {'https','http'}:return html.escape(label)
    return f'<a href="{html.escape(value,quote=True)}">{html.escape(label)}</a>'


def render_dataset_report(tables: Mapping[str,pd.DataFrame], figures: Mapping[str,bytes], *, dataset_version: str) -> str:
    """Embedded figures need no server, external stylesheet, font or JavaScript."""
    def picture(key: str,alt: str) -> str:
        return f'<img alt="{html.escape(alt)}" src="data:image/png;base64,{base64.b64encode(figures[key]).decode()}">'
    def table(frame: pd.DataFrame) -> str:return '<div class="scroll">'+frame.to_html(index=False,border=0,escape=True)+'</div>'
    art=tables['artworks']; masks=tables['masks']; geometry=tables['mask_geometry']; eligible=tables['model_eligibility']
    provenance=[]
    for r in art.to_dict('records'):
        provenance.append('<tr>'+''.join(f'<td>{value}</td>' for value in [html.escape(str(r['painting_id'])),
            html.escape(str(r['title'])),html.escape(str(r['artist'])),html.escape(str(r['source_photographer'])),
            html.escape(str(r['source_credit'])),_link(r['license_url'],str(r['license'])),_link(r['source_url'],'Source')])+'</tr>')
    descriptions=''.join(f'<article><h3>{html.escape(str(r["painting_id"]))}</h3><p>{html.escape(str(r["target_description"]))}</p></article>' for r in masks.to_dict('records'))
    summary=geometry.assign(selected_content_percent=(geometry.damaged_content_fraction*100).round(4),
        largest_component_percent=(geometry.largest_component_fraction*100).round(2))[
        ['painting_id','selected_content_percent','connected_component_count','largest_component_percent','touches_content_boundary']]
    scale=tables['inference_mask_audit'].assign(lost_selected_pixels_percent=(tables['inference_mask_audit'].disappeared_source_pixel_fraction*100).round(4),
        mask_roundtrip_iou=tables['inference_mask_audit'].roundtrip_iou.round(4))[
        ['painting_id','disappeared_component_count','lost_selected_pixels_percent','mask_roundtrip_iou','scale_review_status']]
    matrix=eligible.pivot(index='painting_id',columns='model_id',values='eligible').reset_index()
    links=''.join(f'<li><a href="../{("metrics" if key in {"mask_geometry","inference_mask_audit"} else "data")}/{key}.csv">{html.escape(key)}.csv</a></li>' for key in TABLE_NAMES)
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>D03 · Real-damage dataset preparation</title><style>
:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0;background:#eee9dd;color:#243731;font:16px/1.6 Arial,sans-serif}}
main{{max-width:1240px;margin:32px auto;padding:0 24px 48px}}header{{background:#173d37;color:#fff6e3;border-radius:12px;padding:38px}}
h1,h2,h3{{font-family:Georgia,serif;line-height:1.2}}h1{{font-size:36px;margin:8px 0}}h2{{font-size:26px;color:#21463d}}h3{{font-size:19px}}
.eyebrow{{letter-spacing:.12em;font-size:12px;text-transform:uppercase}}.stats{{display:flex;flex-wrap:wrap;gap:18px;margin-top:24px}}
.stats span{{padding:10px 18px;border-left:2px solid #d8b56c}}.stats b{{font-size:27px;display:block}}section{{background:#fffdf7;padding:28px;border-radius:10px;margin:22px 0}}
.note{{border-left:4px solid #b58b40;padding:12px 18px;background:#f5edda}}img{{display:block;width:100%;height:auto}}.scroll{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;font-size:13px}}th{{background:#e6eee7;text-align:left}}th,td{{padding:10px;border-bottom:1px solid #ddd;vertical-align:top}}
a{{color:#1c5e61}}.cards{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}}article{{padding:12px 18px;background:#f4f1e9;border-radius:6px}}article h3{{margin:4px 0}}
@media(max-width:700px){{main{{padding:0 10px}}header,section{{padding:20px}}h1{{font-size:28px}}.cards{{grid-template-columns:1fr}}}}
@media print{{body{{background:white}}main{{margin:0;padding:0}}section{{break-inside:avoid}}a{{color:inherit}}}}
</style><main><header><div class="eyebrow">D03 · Supplemental study · Cohort {html.escape(dataset_version)}</div>
<h1>Real-damage dataset preparation</h1><p>From source photographs to reviewed reconstruction targets and traceable model inputs.</p>
<div class="stats"><span><b>{len(art)}</b>paintings</span><span><b>{art.category.nunique()}</b>categories</span><span><b>{int(eligible.eligible.sum())} / {len(eligible)}</b>compatible case–model pairs</span><span><b>0</b>clean references</span></div></header>
<section><h2>Scope and completion status</h2><p>Input and mask checks establish compatibility with the four existing restoration methods. D03 does not run restoration or check model weights and runtime.</p>
<p class="note">Canonical files alone do not establish downstream readiness. The authoritative completion gate is recorded in <a href="../manifests/run_manifest.json">run_manifest.json</a>; D04 requires a completed D03 run.</p>
<p>This purposive collection contains two paintings per operational visual category. Physical damage replaces synthetic damage generation, while the 768-pixel preprocessing and existing model policies remain unchanged.</p></section>
<section><h2>The ten inputs</h2>{picture('source_overview','Ten preprocessed physically damaged painting inputs')}</section>
<section><h2>Approved repair scope</h2><p>The masks select repair targets, not every visible defect. Their acceptance precedes model outcomes. Unselected deterioration remains outside the target.</p>
{picture('mask_review_atlas','Selected repair masks overlaid in red')}<div class="cards">{descriptions}</div></section>
<section><h2>Mask geometry</h2><p>Coverage uses image content as the denominator and excludes padding. Component counts use eight-connected pixels. Similar coverage can describe very different spatial patterns.</p>{table(summary)}</section>
<section><h2>Inference-scale review</h2><p>The researcher accepted the nearest-neighbour 768-to-512 mask-resizing effects. Lost-pixel percentages below count only components disappearing entirely; surviving edges can also change. Round-trip IoU describes mask geometry, not restoration quality.</p>{table(scale)}</section>
<section><h2>Input eligibility</h2><p>True means the reviewed input and mask are compatible with that method. Runtime and model availability remain D04 checks. The existing model configurations are recorded by SHA-256 in the eligibility table.</p>{table(matrix)}</section>
<section><h2>Sources, credits and reuse conditions</h2><p>Images were resized and padded; review figures add mask overlays. Attribution and licence conditions remain attached to each source. Ancient wall paintings can include prior fills or treatment.</p>
<div class="scroll"><table><thead><tr><th>ID</th><th>Artwork</th><th>Artist</th><th>Photograph / contributor</th><th>Credit</th><th>Licence</th><th>Record</th></tr></thead><tbody>{''.join(provenance)}</tbody></table></div></section>
<section><h2>Interpretation and saved evidence</h2><p>No damaged input is a clean reference. Interior reference-fidelity scores cannot establish the unknown original content. Synthetic reference comparisons remain separate; ten purposively selected paintings do not support population-level model rankings.</p>
<ul>{links}</ul><p><a href="../manifests/artifacts.csv">Artifact hashes</a> · <a href="../validation/checks.csv">Validation checks</a> · <a href="../manifests/run_manifest.json">Run manifest</a></p>
<p>Temporary review checkpoints remain under <code>work/</code> as audit history. They are not substitutes for the canonical tables and the completed-run gate.</p></section></main></html>'''


def publish_real_damage_dataset(project_root: str | Path, config: Mapping[str,Any],
        eligibility_config: Mapping[str,Any], publication_config: Mapping[str,Any], catalog: Mapping[str,Any],
        artworks: pd.DataFrame, preprocessed_images: pd.DataFrame, prepared: Mapping[str,Any], *,
        inputs: Mapping[str,Path], input_checksums: Mapping[str,str], inventory_run_id: str,
        helper_versions: Mapping[str,str], started_at_utc: str, previous_validation: ValidationCollector,
        progress_callback: Callable[[dict[str,Any]],None] | None=None) -> dict[str,Any]:
    started=perf_counter();root=Path(project_root).resolve();output=notebook_output_root(NOTEBOOK_STEM,root)
    paths={key:require_notebook_output_path(output/rel,NOTEBOOK_STEM,root) for key,rel in config['outputs'].items()}
    previous_manifest=json.loads(paths['run_manifest'].read_text(encoding='utf-8')) if paths['run_manifest'].exists() else None
    _require(previous_manifest is None or not previous_manifest.get('completion_gate_passed'), 'D03 is already complete; publication must not downgrade a completed run')
    _require(any(c.validation_stage==ELIGIBILITY_STAGE for c in previous_validation.checks)
        and all(c.passed for c in previous_validation.checks),'Successful Batch 6 validation is required')
    collector=ValidationCollector();collector.extend(c for c in previous_validation.checks if c.validation_stage!=PUBLICATION_STAGE)
    def check(key: str,description: str,passed: bool,observed: Any,expected: Any=True) -> None:
        collector.add(validation_stage=PUBLICATION_STAGE,check_id=key,check_description=description,
            severity='blocking',passed=passed,observed=observed,expected=expected)
    work=output/eligibility_config['output_work_directory']
    checkpoint=json.loads((work/'eligibility_checkpoint.json').read_text(encoding='utf-8'))
    _require(checkpoint['helper_sha256']==sha256_file(root/eligibility_config['inputs']['helper_source']), 'Batch 6 producer changed')
    _require(checkpoint['eligibility_config_sha256']==hashlib.sha256(json.dumps(eligibility_config,sort_keys=True).encode()).hexdigest(),'Batch 6 policy changed')
    decision_path=root/eligibility_config['inputs']['scale_review_decisions']
    _require(checkpoint['scale_decisions_sha256']==sha256_file(decision_path),'Scale approval changed')
    scale_decision=json.loads(decision_path.read_text(encoding='utf-8'))
    for relative,digest in scale_decision['batch_5_files_sha256'].items():
        _require(sha256_file(output/'work/mask_review'/relative)==digest,f'Review evidence changed: {relative}')
    for key,path in inputs.items():
        _require(key in input_checksums and sha256_file(path)==input_checksums[key],f'Declared input changed since preflight: {key}')
    for name in ELIGIBILITY_TABLES:
        _require(sha256_file(work/f'{name}.csv')==checkpoint['files_sha256'][f'{name}.csv'],f'Prepared table changed: {name}')
        _same_csv(prepared[name],work/f'{name}.csv')
    _same_csv(preprocessed_images,output/config['preparation']['candidate_directory']/config['preparation']['preprocessing_checkpoint'])
    check('upstream_binding','Prepared tables, producer and review evidence remain hash-bound',True,'verified')
    ids=config['dataset']['painting_ids']
    _require(artworks.painting_id.tolist()==ids and preprocessed_images.painting_id.tolist()==ids,'Wrong ordered source population')
    _require(artworks.acceptance_status.eq('accepted').all() and artworks.source_metadata_verified.all(),'Source/provenance audit incomplete')
    for art,source in zip(artworks.to_dict('records'),catalog['records']):
        for key in ('painting_id','category','title','artist','raw_image_path','raw_sha256','source_metadata_path',
                    'source_metadata_sha256','source_url','license','license_url','source_credit','source_photographer'):
            _require(art[key]==source[key],f'Artwork/catalog mismatch: {source["painting_id"]}/{key}')
        for path_key,hash_key in (('raw_image_path','raw_sha256'),('source_metadata_path','source_metadata_sha256')):
            _require(sha256_file(root/art[path_key])==art[hash_key],f'Source provenance bytes changed: {art["painting_id"]}')
    check('source_provenance','Ten accepted source records retain credits, licences and source bindings',True,len(artworks),10)
    tables={key:prepared[key].copy(deep=True) for key in ELIGIBILITY_TABLES}
    tables.update(artworks=artworks.copy(deep=True),preprocessed_images=preprocessed_images.copy(deep=True))
    tables['masks']['artifact_state']='published'
    tables['mask_review']['candidate_is_final']=True
    tables['mask_review']['mask_path']=tables['mask_review'].mask_id.map(tables['masks'].set_index('mask_id').mask_path)
    tables['artworks']['mask_review_status']=tables['artworks'].painting_id.map(tables['mask_review'].set_index('painting_id').review_status)
    tables['artworks']['scale_review_status']=tables['artworks'].painting_id.map(tables['mask_review'].set_index('painting_id').scale_review_status)
    tables['case_registry']['status']='passed'
    tables['case_registry']['handoff_status']=HANDOFF_CONDITION
    tables['model_eligibility']['handoff_status']=HANDOFF_CONDITION
    for key in TABLE_NAMES:
        _require(len(tables[key])==(40 if key=='model_eligibility' else 10),f'Wrong canonical table cardinality: {key}')
    for key in ('artworks','preprocessed_images','case_registry'):
        _require(not tables[key].has_clean_reference.any() and tables[key].clean_image_path.isna().all(),f'Unexpected clean reference: {key}')
    check('reference_absence','Physical inputs remain explicitly without clean references',True,0,0)
    images=[];masks=[];image_payloads={}
    for geo,mask_row in zip(preprocessed_images.to_dict('records'),tables['masks'].to_dict('records')):
        pid=geo['painting_id'];_require(pid==mask_row['painting_id'],'Mask/input order changed')
        image_path=root/geo['processed_path'];candidate=root/mask_row['candidate_mask_path'];target=root/mask_row['mask_path']
        _require(image_path==paths['processed_image_template'].parent/f'{pid}.png','Unexpected canonical input path')
        expected_mask=output/config['outputs']['mask_template'].format(mask_id=mask_row['mask_id'])
        _require(target==expected_mask and target.is_relative_to(output),'Unexpected canonical mask path')
        _require(sha256_file(image_path)==geo['sha256']==mask_row['input_sha256'],'Processed image changed')
        _require(sha256_file(candidate)==mask_row['mask_sha256'],'Approved mask changed')
        with Image.open(image_path) as im:
            _require(im.mode=='RGB' and im.size==(768,768) and im.format=='PNG','Wrong processed-image format');images.append(im.copy())
        with Image.open(candidate) as im:
            box=tuple(int(geo[k]) for k in ('content_x_min','content_y_min','content_x_max','content_y_max'))
            validate_binary_damage_mask(im,content_box=box);masks.append(im.copy())
        image_payloads[target]=candidate.read_bytes()
        check(f'input:{pid}','Canonical damaged input retains its validated SHA-256',True,geo['sha256'])
    figures={key:overview_figure(images,masks,ids,tables['masks'].mask_fraction_content.tolist(),
        overlay=key=='mask_review_atlas',dpi=publication_config['figure_dpi']) for key in ('source_overview','mask_review_atlas')}
    report=render_dataset_report(tables,figures,dataset_version=config['dataset']['dataset_version'])
    payloads={paths[key]:tables[key].to_csv(index=False,lineterminator='\n').encode('utf-8') for key in TABLE_NAMES}
    payloads.update(image_payloads);payloads.update({paths[k]:v for k,v in figures.items()});payloads[paths['report']]=report.encode('utf-8')
    canonical=set(payloads)|{root/p for p in preprocessed_images.processed_path}|{paths[k] for k in ('validation','artifacts','run_manifest')}
    existing={p for p in output.rglob('*') if p.is_file() and not p.is_relative_to(output/'work')}
    _require(existing<=canonical,'Unexpected canonical files are retained for review')
    for path,content in payloads.items():
        require_notebook_output_path(path,NOTEBOOK_STEM,root)
        _require(not path.exists() or path.read_bytes()==content,f'Existing scientific artifact differs; retained: {path}')
    for index,(path,content) in enumerate(payloads.items(),1):
        _atomic_write(path,content)
        if progress_callback:progress_callback(dict(completed=index,total=len(payloads),path=to_repo_relative(path,root),elapsed_seconds=perf_counter()-started))
    for row in tables['masks'].to_dict('records'):
        check(f'mask:{row["painting_id"]}','Published mask is byte-identical to the reviewed candidate',sha256_file(root/row['mask_path'])==row['mask_sha256'],sha256_file(root/row['mask_path']),row['mask_sha256'])
    for key in TABLE_NAMES:
        _same_csv(tables[key],paths[key])
        check(f'table:{key}','Canonical CSV reload preserves the prepared records',len(tables[key])==(40 if key=='model_eligibility' else 10),len(tables[key]),40 if key=='model_eligibility' else 10)
    for key in figures:
        with Image.open(paths[key]) as im:im.verify()
        check(f'figure:{key}','Canonical overview PNG decodes',True,paths[key].name)
    saved_report=paths['report'].read_text(encoding='utf-8')
    check('standalone_report','Report embeds two figures and contains all ten case descriptions',saved_report.count('data:image/png;base64,')==2 and all(f'<h3>{pid}</h3>' in saved_report for pid in ids),2,2)
    check('canonical_count','Declared canonical publication contains exactly 34 files',len(canonical)==publication_config['expected_canonical_files'],len(canonical),34)
    collector.raise_for_blocking()
    _atomic_write(paths['validation'],collector.to_dataframe().to_csv(index=False,lineterminator='\n').encode('utf-8'))
    records=[]
    def artifact(key: str,path: Path,kind: str,role: str,schema: str,rows: int|None=None) -> None:
        records.append(build_artifact_record(artifact_key=key,producer_notebook=NOTEBOOK_STEM,path=path,
            artifact_type=kind,artifact_role=role,schema_version=schema,dataset_scope=config['dataset']['dataset_scope'],
            experiment_id=config['dataset']['experiment_id'],row_count=rows,project_root=root))
    for key in TABLE_NAMES:artifact(key,paths[key],'dataset_table','primary_downstream',config['schemas'][key],len(tables[key]))
    for key,path in (('processed_inputs',output/'images/inputs'),('reviewed_masks',output/'images/masks')):
        artifact(key,path,'image_collection','primary_downstream','real_damage_image_collection.v1',10)
    for key in figures:artifact(key,paths[key],'figure','audit_reporting','real_damage_overview.v1')
    artifact('report',paths['report'],'html_report','audit_reporting',config['schemas']['report'])
    artifact('validation',paths['validation'],'validation_table','audit_reporting','validation_checks.v1',len(collector.checks))
    artifacts=artifact_records_dataframe(records)
    _require(len(artifacts)==publication_config['expected_artifact_records'],'Unexpected artifact record count')
    _atomic_write(paths['artifacts'],artifacts.to_csv(index=False,lineterminator='\n').encode('utf-8'))
    scientific={to_repo_relative(p,root):sha256_file(p) for p in canonical if p.exists() and p not in {paths['artifacts'],paths['run_manifest'],paths['validation']}}
    fingerprint=hashlib.sha256(json.dumps(scientific,sort_keys=True).encode()).hexdigest()
    expected={'paintings':10,'paintings_per_category':2,'reviewed_masks':10,'cases':10,'model_eligibility_rows':40,'canonical_files':34,'artifact_records':14}
    category_counts=tables['artworks'].groupby('category').size()
    observed={'paintings':len(tables['artworks']),
        'paintings_per_category':int(category_counts.iloc[0]) if category_counts.nunique()==1 else category_counts.to_dict(),
        'reviewed_masks':len(tables['masks']),'cases':len(tables['case_registry']),
        'model_eligibility_rows':len(tables['model_eligibility']),'canonical_files':len(canonical),
        'artifact_records':len(artifacts),'eligible_rows':int(tables['model_eligibility'].eligible.sum()),
        'known_clean_references':int(tables['artworks'].has_clean_reference.sum())}
    if previous_manifest is None:
        config_paths=sorted({to_repo_relative(path,root) for path in inputs.values() if to_repo_relative(path,root).startswith('config/')})
        manifest=build_run_manifest(notebook_id='D03',notebook_name='Real-Damage Dataset Preparation',origin=config['notebook']['origin'],
            run_status='partial',started_at_utc=started_at_utc,completed_at_utc='',inventory_run_id=inventory_run_id,
            dataset_versions=dict(config['dataset']),configuration_paths=config_paths,
            configuration_checksums_by_path={path:sha256_file(root/path) for path in config_paths},helper_versions=helper_versions,
            inputs=[dict(input_key=key,relative_path=to_repo_relative(path,root),checksum=input_checksums[key],required=True) for key,path in inputs.items()],
            outputs=records,expected_counts=expected,observed_counts=observed,validation_summary=collector.summary(),
            known_limitations=['No clean reference exists; damaged inputs are not reference-fidelity targets.',
                'Masks cover selected repair targets; unselected deterioration may remain.',
                'Two purposively selected paintings per category do not support population-level rankings.',
                'Scale-resampling effects are accepted and retained in the inference-mask audit.',
                'Input eligibility does not establish model runtime readiness; D04 checks models and weights.'],
            project_root=root,package_names=['numpy','pandas','Pillow','PyYAML','scipy','matplotlib'],hardware={'execution_device':'CPU','gpu_required':False},
            run_id='run_d03_'+fingerprint[:24])
        manifest.update(publication_stage=7,publication_recorded_at_utc=utc_now_iso(),completion_gate_passed=False,
            downstream_ready=False,data_fingerprint=fingerprint,artifact_manifest_sha256=sha256_file(paths['artifacts']),
            canonical_file_checksums=scientific,artifact_manifest_exclusions=['run_manifest.json','artifacts.csv'],
            exclusion_reason='Run manifest pins artifacts.csv; neither manifest hashes itself.',
            retained_work_files=sum(p.is_file() for p in (output/'work').rglob('*')))
        _atomic_write(paths['run_manifest'],(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode('utf-8'))
    else:
        _require(previous_manifest.get('run_status')=='partial' and previous_manifest.get('data_fingerprint')==fingerprint
            and previous_manifest.get('artifact_manifest_sha256')==sha256_file(paths['artifacts'])
            and previous_manifest.get('validation_summary')==collector.summary(),'Existing publication manifest differs; retained')
        manifest=previous_manifest
    for row in records:_require(sha256_path(root/row['relative_path'])==row['checksum'],f'Artifact verification failed: {row["artifact_key"]}')
    _require({p for p in output.rglob('*') if p.is_file() and not p.is_relative_to(output/'work')}==canonical,'Canonical file set differs')
    _require(json.loads(paths['run_manifest'].read_text(encoding='utf-8'))==manifest,'Run manifest round-trip differs')
    return {'validation':collector,'tables':tables,'artifacts':artifacts,'run_manifest':manifest,
        'report_path':paths['report'],'source_overview_path':paths['source_overview'],'mask_review_atlas_path':paths['mask_review_atlas'],
        'run_manifest_path':paths['run_manifest'],'elapsed_seconds':perf_counter()-started,'canonical_file_count':len(canonical)}
