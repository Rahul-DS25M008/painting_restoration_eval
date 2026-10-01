"""Offline metadata-only Archive index. Never recompute scientific evidence."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import quote
import yaml

from restoration_eval.dashboard_application import open_dashboard_package
from restoration_eval.manifests import sha256_file, sha256_path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'streamlit_assets/evidence/research_archive'
GITHUB = 'https://github.com/Rahul-DS25M008/painting_restoration_eval'


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def build():
    package = open_dashboard_package(ROOT)
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    DEST.mkdir(parents=True,exist_ok=True)
    partitions = {}
    sources = {}
    def source(path):
        relative = path.relative_to(ROOT).as_posix()
        sources[relative] = sha256_file(path)
        return relative
    def save(name, value):
        raw = gzip.compress(json.dumps(value,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode(),mtime=0)
        (DEST/name).write_bytes(raw)
        partitions[name] = {'sha256':hashlib.sha256(raw).hexdigest(),'size_bytes':len(raw)}
    stages=[]
    stage_records={}
    final_run=json.loads((ROOT/'outputs/33_final_evaluation_report/manifests/run_manifest.json').read_text(encoding='utf-8'))
    upstream=final_run['dataset_versions']['upstream_run_ids']
    for run_path in sorted((ROOT/'outputs').glob('*/manifests/run_manifest.json')):
        folder=run_path.parents[1].name
        match=re.match(r'^(\d{2})_',folder)
        key='N'+match[1] if match and 1<=int(match[1])<=33 else None
        if folder=='12a_hint_restoration': key='N12A'
        if folder=='37_hint_mat_method_selection': key='D01'
        if folder=='d02_portrait_skin_tone_and_hand_restoration_audit': key='D02'
        if not key: continue
        run=json.loads(run_path.read_text(encoding='utf-8'))
        scope=run.get('dataset_versions',{}).get('dataset_scope','')
        manifest=run_path.with_name('artifacts.csv')
        expected=run.get('artifact_manifest_checksum')
        observed_manifest=sha256_file(manifest)
        manifest_state='matches_recorded_run' if expected==observed_manifest else 'recorded_hash_mismatch' if expected else 'not_recorded_in_run'
        artifacts=read_csv(manifest)
        if not scope and {r['dataset_scope'] for r in artifacts}=={'controlled_300'}:
            scope='controlled_300'
        if key.startswith('N') and key[1:] in upstream:
            if run['run_id']!=upstream[key[1:]]: raise ValueError(f'{key}: not the N33 upstream run')
            # Older producers use analytical scope labels, not dataset IDs.
            scope=scope or 'controlled_300 (exact N33 upstream run)'
        elif key!='D01' and scope!='controlled_300':
            raise ValueError(f'{key}: not Controlled-300: {scope}')
        run_relative=source(run_path)
        source(manifest)
        summary={'id':key,'title':folder.split('_',1)[-1].replace('_',' ').capitalize(),
                 'run_id':run['run_id'],'scope':scope,'status':run['run_status'],
                 'git_commit':run.get('git_commit'),'git_dirty':run.get('git_dirty'),
                 'manifest_path':run_relative,'manifest_sha256':sources[run_relative],
                 'artifact_manifest_state':manifest_state,'artifact_manifest_expected_sha256':expected,
                 'artifact_manifest_observed_sha256':observed_manifest,
                 'artifact_count':len(artifacts),'linkage':'Frozen method-selection decision (separate pilot)' if key=='D01' else 'Separate project record' if key in ('D02','N12A') else 'Primary numbered stage'}
        record={'summary':summary,'run':run,'artifacts':artifacts,'files':[]}
        # Metadata and exact source downloads are bounded, explicit actions.
        for path in (run_path,manifest):
            record['files'].append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha256_file(path),'size_bytes':path.stat().st_size,'role':'Recorded metadata'})
        for row in artifacts:
            record['files'].append({'path':row['relative_path'],'sha256':row['checksum'],
                                   'size_bytes':int(row['size_bytes']),'role':row['artifact_role'],'directory':row['format']=='directory'})
        notebook_id='37' if key=='D01' else 'd02' if key=='D02' else key[1:].lower()
        notebooks=list((ROOT/'notebooks').glob(notebook_id+'_*.ipynb'))
        for path in notebooks:
            record['files'].append({'path':source(path),'sha256':sha256_file(path),'size_bytes':path.stat().st_size,
                                   'role':'Source notebook at Archive build; not an assertion of byte identity with the dirty producer run'})
        for relative,expected_hash in run.get('configuration_checksums',{}).items():
            path=ROOT/relative
            if path.is_file():
                record['files'].append({'path':relative,'sha256':expected_hash,'size_bytes':path.stat().st_size,
                                       'role':'Configuration expected by the recorded run; current bytes must match before download'})
        stage_records[key]=record
        stages.append(summary)
        save(key+'.json.gz',record)
    if len(stages)!=36: raise ValueError('Expected N01–N33 plus N12A, D01, D02')
    n33=stage_records['N33']
    def verified_table(suffix):
        row=next(r for r in n33['artifacts'] if r['relative_path'].endswith(suffix))
        path=ROOT/row['relative_path']
        if sha256_file(path)!=row['checksum']: raise ValueError('N33 source mismatch: '+suffix)
        source(path)
        return read_csv(path)
    tables=verified_table('/thesis_tables.csv')
    claims=[r for r in verified_table('/report_evidence_catalog.csv') if r['record_type']=='claim']
    checks=verified_table('/checks.csv')
    limitations=[]
    # Display grouping only; original limitation text and row IDs stay intact.
    groups={'Dataset':{1,2,3,4,5},'Models':{6,9,16},'Interpretation':{7,8,10,11,12,13,17},'Use':{14,15,18}}
    for r in tables:
        if r['table_id']=='t15_limitations':
            number=int(r['row_key'].split('_')[-1])
            limitations.append({**r,'group':next(g for g,ids in groups.items() if number in ids)})
    figures=[]
    for row in n33['artifacts']:
        if row['artifact_type'].endswith('figure_collection'):
            path=ROOT/row['relative_path']
            if sha256_path(path)!=row['checksum']: raise ValueError('Figure collection mismatch')
            for image in sorted(path.glob('*.png')):
                figures.append({'path':image.relative_to(ROOT).as_posix(),'sha256':sha256_file(image),
                                'size_bytes':image.stat().st_size,'role':row['artifact_role'],'collection_checksum':row['checksum']})
    n33['files'].extend(figures)
    save('N33.json.gz',n33)
    provenance_path=ROOT/'outputs/01_dataset_verification/data/artworks.csv'
    n01row=next(r for r in stage_records['N01']['artifacts'] if r['relative_path']==provenance_path.relative_to(ROOT).as_posix())
    if sha256_file(provenance_path)!=n01row['checksum']: raise ValueError('Provenance checksum mismatch')
    source(provenance_path)
    fields=['painting_id','title','artist','source','source_url','rights_status','license','raw_sha256','date_or_period','style_or_period','medium','category']
    paintings=[{k:r[k] for k in fields} for r in read_csv(provenance_path) if r['dataset_scope']=='controlled_300']
    for p in paintings:
        lookup=package.painting_lookup.loc[package.painting_lookup.painting_id.eq(p['painting_id'])].iloc[0]
        p.update(case_count=int(lookup.case_count),candidate_count=int(lookup.candidate_count))
    publications_path=ROOT/'outputs/inventory/external_artifact_publication.csv'
    publications=read_csv(publications_path)
    for row in publications:
        match=re.search(r'/commit/([0-9a-f]{40})(?:$|/)',row['publication_commit_url'])
        if not match or row['verification_status']!='verified': raise ValueError('Unpinned publication')
        row['pinned_revision']=match[1]
        row['pinned_url']='https://huggingface.co/datasets/'+row['repository_id']+'/resolve/'+match[1]+'/'+quote(row['path_in_repository'],safe='/')
    source(publications_path)
    save('publications.json.gz',publications)
    bundles=[]
    for path in sorted((ROOT/'outputs/inventory').glob('bundled_publication_*_full.json')):
        record=json.loads(path.read_text(encoding='utf-8'))
        if record['status']!='full_remote_verified' or not re.fullmatch('[0-9a-f]{40}',record['revision']): raise ValueError('Invalid bundle release')
        record['record_path']=source(path)
        record['pinned_url']='https://huggingface.co/datasets/'+record['repo_id']+'/tree/'+record['revision']+'/'+record['prefix']
        bundles.append(record)
    reports=package.load_reports()['reports']
    for r in reports:
        loc=package.asset_locators.loc[package.asset_locators.expected_sha256.eq(r['report_sha256'])]
        r['publication_routes']=json.loads(loc.to_json(orient='records'))
        if r['report_type'] in ('model','final'):
            blob=subprocess.run(['git','show',revision+':'+r['report_path']],cwd=ROOT,capture_output=True)
            if blob.returncode==0 and hashlib.sha256(blob.stdout).hexdigest()==r['report_sha256']:
                r['publication_routes']=[{'provider':'github','revision':revision,'expected_sha256':r['report_sha256'],
                    'immutable_resolve_url':GITHUB+'/blob/'+revision+'/'+quote(r['report_path'],safe='/')}]
    publication_config=ROOT/'config/publication/external_storage.yaml'
    source(publication_config)
    config=yaml.safe_load(publication_config.read_text(encoding='utf-8'))
    # Locate the existing named release rather than duplicate its revision in code.
    def report_releases(value):
        if isinstance(value,dict):
            if 'verified_report_package_releases' in value: return value['verified_report_package_releases']
            for child in value.values():
                found=report_releases(child)
                if found: return found
        return None
    report_package=report_releases(config)['n32_diagnostics']
    assert report_package['status']=='full_remote_verified'
    overview={'schema_version':'research_archive.v1','release_id':package.release_id,'git_revision':revision,
              'scope':'controlled_300','population':package.population,'stages':stages,'paintings':paintings,
              'reports':reports,'limitations':limitations,'claims':claims,'figures':figures,'bundles':bundles,
              'artifact_index':[{'stage':key,'path':r['path'],'role':r['role']} for key,record in stage_records.items() for r in record['files']],
              'checks':{'total':len(checks),'passed':sum(r['passed'].lower()=='true' for r in checks)},
              'individual_publications':len(publications),
              'n32_package':{**report_package,'repo_id':report_package['repository'],'prefix':report_package['release_prefix'],
                             'reports':report_package['report_files'],'objects':report_package['publication_files'],'source':source(publication_config)}}
    assert (len(paintings),len(claims),len(limitations),len(figures),len(publications),len(bundles))==(300,49,18,24,2653,6)
    assert overview['checks']=={'total':536,'passed':536}
    save('catalogue.json.gz',overview)
    (DEST/'manifest.json').write_text(json.dumps({'schema_version':'research_archive_index.v1','release_id':package.release_id,'sources':sources,'partitions':partitions},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'partitions':len(partitions),'compressed_bytes':sum(v['size_bytes'] for v in partitions.values()),'stages':len(stages),'reports':len(reports),'claims':len(claims),'limitations':len(limitations)}))


if __name__=='__main__': build()
