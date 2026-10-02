"""Read-only Research Archive, bound to compact saved-data partitions."""
import gzip
import hashlib
import io
import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode
from .evidence_transport import read_bytes

ROOT=Path(__file__).resolve().parents[2]
INDEX=ROOT/'streamlit_assets/evidence/research_archive'
VIEWS={'search','paintings','cases','candidates','reports','models','runs','record','sources','checksums','figures','claims','limits','publications','publications_candidates','publications_diagnostics','bundles','destinations','zenodo'}


@lru_cache(maxsize=16)
def _partition(name, manifest_revision):
    manifest=json.loads((INDEX/'manifest.json').read_text(encoding='utf-8'))
    entry=manifest['partitions'].get(name)
    if not entry: raise ValueError('Unknown Archive partition')
    raw=(INDEX/name).read_bytes()
    if len(raw)!=entry['size_bytes'] or hashlib.sha256(raw).hexdigest()!=entry['sha256']:
        raise ValueError('Archive partition failed integrity verification')
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        decoded=stream.read(8*1024*1024+1)
    if len(decoded)>8*1024*1024: raise ValueError('Archive metadata exceeds its bounded size')
    return json.loads(decoded)


def partition(name):
    return _partition(name,(INDEX/'manifest.json').stat().st_mtime_ns)


def catalogue(package):
    data=partition('catalogue.json.gz')
    if data['release_id']!=package.release_id or data['scope']!='controlled_300':
        raise ValueError('Archive release or scope mismatch')
    return data


def record(package, identity='N33'):
    data=catalogue(package)
    if identity not in {r['id'] for r in data['stages']}:
        raise ValueError('Unknown stage; no record substituted')
    result=partition(identity+'.json.gz')
    if result['summary']['id']!=identity: raise ValueError('Archive stage identity mismatch')
    return result


def href(**selection):
    return '?'+urlencode({'room':'research_archive',**{'ar_'+k:str(v) for k,v in selection.items() if v is not None}})


def payload(package, identity='N33', view='', painting=None):
    if view and view not in VIEWS: raise ValueError('Unknown Archive view')
    data=catalogue(package)
    # Later publication metadata is a separate receipt, not a rewrite of frozen N34 partitions.
    zenodo=json.loads((ROOT/'config/publication/zenodo_published_record.json').read_text(encoding='utf-8'))
    result={**data,'zenodo':zenodo,'record':record(package,identity),'open_view':view,'painting':painting,'publications':[], 'case_rows':[], 'candidate_rows':[]}
    if view.startswith('publications'): result['publications']=partition('publications.json.gz')
    if painting:
        if painting not in {p['painting_id'] for p in data['paintings']}: raise ValueError('Unknown painting')
        if view in ('cases','candidates'):
            shard=package.load_painting(painting)
            result['case_rows']=[{**{k:r.get(k) for k in ('case_id','experiment_id','condition_id','severity','status')},'painting_id':painting} for r in shard['cases']]
            result['candidate_rows']=[{**{k:r.get(k) for k in ('candidate_id','case_id','model_id','experiment_id','seed','prompt_variant_id','status')},'painting_id':painting} for r in shard['candidates']]
    return result


def selected_file(package, identity, relative):
    files=record(package,identity)['files']
    matches=[r for r in files if r['path']==relative]
    if len(matches)!=1: raise ValueError('Unknown or ambiguous saved artifact')
    item=matches[0]
    if item.get('directory'): raise ValueError('This is a collection; select its published release, not an invented ZIP')
    if item['size_bytes']>32*1024*1024: raise ValueError('Large evidence is outside the bounded local download limit; inspect publication metadata')
    path=(ROOT/relative).resolve()
    if not path.is_relative_to(ROOT.resolve()): raise ValueError('Invalid artifact path')
    raw=read_bytes(path,item['sha256'],item['size_bytes'],root=ROOT)
    if hashlib.sha256(raw).hexdigest()!=item['sha256']: raise ValueError('Saved artifact checksum mismatch')
    return raw,item


def verify_manifest(package, identity):
    item=record(package,identity)['summary']
    relative=item['manifest_path']
    raw,file=selected_file(package,identity,relative)
    return {'state':'verified','path':relative,'sha256':file['sha256'],
            'meaning':'Exact saved run-manifest bytes match the Archive index. This does not verify scientific correctness or all upstream files.',
            'artifact_manifest_state':item['artifact_manifest_state']}
