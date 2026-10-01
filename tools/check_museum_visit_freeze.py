"""Freeze the approved visitor overlay without publishing or changing rooms."""
import argparse
import json
import subprocess

from check_research_archive_freeze import ROOT, digest

MANIFEST = ROOT / 'config/publication/museum_visit_freeze.json'


def freeze():
    if MANIFEST.exists():
        raise ValueError('The approved visitor freeze already exists; refusing overwrite')
    paths = [ROOT / name for name in (
        'streamlit_app.py', 'src/restoration_eval/room_runtime.py',
        'src/restoration_eval/museum_visit.py',
        'tests/museum_visit.test.cjs', 'tools/check_museum_visit_freeze.py',
        'docs/dashboard_design_finalists/museum_passport_preview.png',
        'docs/dashboard_design_finalists/museum_passport_completed.png',
        'docs/dashboard_design_finalists/explore_freely_preview.png',
    )]
    paths.extend(p for p in (ROOT / 'streamlit_assets/museum_visit').iterdir() if p.is_file())
    manifest = {
        'schema_version': 'museum_visit_freeze.v1',
        'status': 'user_approved_visual_freeze',
        'scope': 'Approved six-minute museum passport, free exploration popup, and shared app integration. Room layouts remain unchanged.',
        'research_archive_freeze': 'config/publication/research_archive_freeze.json',
        'base_git_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'deployment_note': 'Presentation approval only; not N35 deployment validation or publication.',
        'files': [digest(p) for p in sorted(paths)],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


def verify():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for record in manifest['files']:
        path = (ROOT / record['path']).resolve()
        if not path.is_relative_to(ROOT) or digest(path)['sha256'] != record['sha256']:
            raise ValueError('Approved visitor experience changed: ' + record['path'])
    print(f"PASS: {len(manifest['files'])} approved visitor-experience files unchanged")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['freeze', 'verify-local'])
    if parser.parse_args().command == 'freeze':
        freeze()
    verify()
