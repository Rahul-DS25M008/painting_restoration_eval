"""Fingerprint the approved Archive; never stage, commit, upload, or run producers."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'config/publication/research_archive_freeze.json'


def digest(path):
    raw=path.read_bytes()
    mode='lf_normalized' if path.suffix in {'.py','.js','.cjs','.css','.json','.txt','.md'} else 'binary'
    return {'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(raw.replace(b'\r\n',b'\n') if mode=='lf_normalized' else raw).hexdigest(),'hash_mode':mode,'size_bytes':len(raw)}


def freeze():
    if MANIFEST.exists():
        raise ValueError('An approved freeze already exists; it will not be overwritten')
    patterns=['src/restoration_eval/research_archive*.py','streamlit_assets/research_archive*',
              'streamlit_assets/rooms/research_archive*','streamlit_assets/evidence/research_archive/*',
              'tests/test_research_archive.py','tests/research_archive_controller.test.cjs',
              'tools/build_research_archive.py','tools/check_research_archive_freeze.py',
              'docs/dashboard_design_finalists/research_archive_steps_1_to_3.md',
              'docs/dashboard_design_finalists/research_archive_seal_complete.png']
    paths=sorted({p for pattern in patterns for p in ROOT.glob(pattern) if p.is_file()})
    manifest={'schema_version':'research_archive_freeze.v1','status':'user_approved_visual_freeze',
              'scope':'Research Archive final local presentation and saved metadata. Shared app wiring and opt-in museum-tour overlay are separate.',
              'base_git_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'deployment_note':'Visual completion is not N35 deployment validation. No publication or scientific recomputation performed.',
              'files':[digest(p) for p in paths]}
    MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')


def verify():
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    for record in manifest['files']:
        path=(ROOT/record['path']).resolve()
        if not path.is_relative_to(ROOT) or digest(path)['sha256']!=record['sha256']:
            raise ValueError('Approved Archive changed: '+record['path'])
    print(f"PASS: {len(manifest['files'])} approved Research Archive files unchanged")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['freeze','verify-local'])
    if parser.parse_args().command=='freeze': freeze()
    verify()
