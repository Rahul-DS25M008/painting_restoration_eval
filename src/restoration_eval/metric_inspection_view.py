"""Presentation loader for precomputed inspection companions (no inference)."""
from __future__ import annotations
import base64
import hashlib
import json
from pathlib import Path
from PIL import Image
from .metric_inspection import VERSION, LENSES, REGIONS, public_contract


def load_inspection(root: Path, painting_id: str) -> dict:
    if not (len(painting_id)==4 and painting_id.startswith('p') and painting_id[1:].isdigit()):
        raise ValueError('Invalid painting identity')
    directory = (root/'streamlit_assets/evidence/metric_framework'/painting_id).resolve()
    manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    if manifest['painting_id'] != painting_id or manifest['version'] != VERSION:
        raise ValueError('Inspection identity/version mismatch')
    for source in manifest['sources'].values():
        path=(root/source['path']).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('Inspection source outside the local package')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=source['sha256']:
            raise ValueError(f'Inspection source changed: {path.name}')
    contract = public_contract()
    if set(manifest['regions']) != set(REGIONS):
        raise ValueError('Incomplete spatial supports')
    if set(manifest['pairs']) != set(contract):
        raise ValueError('Incomplete lens/region contract')
    for key, expected in contract.items():
        actual=manifest['pairs'][key]
        if any(actual[field] != expected[field] for field in ('lens','region','canonical_region','allowed','role')):
            raise ValueError(f'Inspection policy mismatch: {key}')
        if expected['allowed'] and not actual.get('maps'):
            raise ValueError(f'Missing spatial companion: {key}')
        if expected['allowed']:
            if actual.get('recipe')!=expected['recipe']:
                raise ValueError(f'Inspection recipe mismatch: {key}')
            if any(name not in manifest['assets'] for name in actual['maps']):
                raise ValueError(f'Unregistered spatial companion: {key}')
    for collection in ('assets','regions'):
        for asset in manifest[collection].values():
            path=(root/asset['path']).resolve()
            if not path.is_relative_to(directory) or path.suffix != '.png':
                raise ValueError('Inspection asset outside its registered exhibit')
            data=path.read_bytes()
            if hashlib.sha256(data).hexdigest()!=asset['sha256']:
                raise ValueError(f'Inspection checksum mismatch: {path.name}')
            asset['uri']='data:image/png;base64,'+base64.b64encode(data).decode('ascii')
    manifest['lenses']={k:dict(label=v[0],metrics=v[1],summary=v[2]) for k,v in LENSES.items()}
    manifest['loader_version']='metric_view.v2'
    with Image.open(root/manifest['regions']['content']['path']) as support:
        if support.size != tuple(reversed(manifest['shape'])) or support.getbbox() is None:
            raise ValueError('Invalid painting-content geometry')
        manifest['content_bbox']=list(support.getbbox())
    return manifest
