"""Prepare one full-study ZIP64 local draft. Never uploads, tags or commits.

--preflight checks the working tree inputs without producing upload archives.
The default build requires a clean checkout and records its exact Git commit.
Frozen producer files are read, never rewritten. Only an ignored release
directory is created. All source notebooks retain their saved outputs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAN = 'config/publication/zenodo_release.json'
SHA40 = re.compile(r'[0-9a-f]{40}')
SHA64 = re.compile(r'[0-9a-f]{64}')
TOKEN = re.compile(rb'(?<![A-Za-z0-9])(?:hf_[A-Za-z0-9]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|sk-proj-[A-Za-z0-9_-]{30,})')


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(root), *args]).decode('utf-8')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_path(root: Path, relative: str) -> Path:
    path = root / relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts or path.is_symlink():
        raise ValueError(f'Unsafe or linked release path: {relative}')
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ValueError(f'Not a repository file: {relative}')
    if any(p in {'.git', '.venv', '__pycache__', '.ipynb_checkpoints'} for p in path.parts):
        raise ValueError(f'Excluded path: {relative}')
    if path.name.lower() in {'.env', 'secrets.toml'} or path.suffix.lower() in {'.pem', '.key'}:
        raise ValueError(f'Credential filename excluded: {relative}')
    return resolved


def file_record(root: Path, relative: str) -> dict:
    path = checked_path(root, relative)
    with path.open('rb') as f:
        digest, size, _ = digest_stream(f, relative)
    return {'path': relative, 'size_bytes': size, 'sha256': digest}


def digest_stream(stream, name: str, sink=None, prefix_bytes: int = 0) -> tuple[str, int, str]:
    digest = hashlib.sha256(); prefix = hashlib.sha256(); size = 0; tail = b''
    scan = Path(name).suffix.lower() in {'.py', '.ipynb', '.json', '.yaml', '.yml', '.toml', '.txt', '.md', '.csv', '.cff', '.ps1', '.sh'}
    while block := stream.read(1024 * 1024):
        if size == 0 and block.startswith(b'version https://git-lfs.github.com/spec/v1'):
            raise ValueError(f'Unmaterialized LFS pointer: {name}')
        if scan and TOKEN.search(tail + block):
            raise ValueError(f'Potential credential requires private review: {name}')
        tail = block[-256:] if scan else b''
        if size < prefix_bytes:
            prefix.update(block[:prefix_bytes-size])
        digest.update(block); size += len(block)
        if sink is not None: sink.write(block)
    return digest.hexdigest(), size, prefix.hexdigest()


def verify_n36(root: Path, plan: dict) -> list[str]:
    spec = plan['n36']; prefix = spec['root']; n36 = root / prefix
    manifest = json.loads((n36 / 'manifests/package_manifest.json').read_text(encoding='utf-8'))
    run = json.loads((n36 / 'manifests/run_manifest.json').read_text(encoding='utf-8'))
    if run['run_id'] != spec['run_id'] or run['run_status'] != 'completed':
        raise ValueError('Unexpected or incomplete N36 run')
    items = manifest['files']
    if len(items) != spec['package_file_count']:
        raise ValueError('N36 package count changed')
    for row in items:
        rec = file_record(root, f"{prefix}/package/{row['package_relative_path']}")
        if rec['sha256'] != row['sha256'] or rec['size_bytes'] != row['size_bytes']:
            raise ValueError(f"Frozen N36 mismatch: {rec['path']}")
    tree = sha('\n'.join(f"{r['package_relative_path']}\t{r['sha256']}" for r in sorted(items, key=lambda r:r['package_relative_path'])).encode())
    if tree != spec['package_tree_sha256'] or tree != manifest['tree_sha256']:
        raise ValueError('N36 package tree digest changed')
    paths = sorted(p.relative_to(root).as_posix() for p in n36.rglob('*') if p.is_file())
    if len(paths) != spec['physical_file_count']:
        raise ValueError('Unexpected N36 physical file count')
    if git(root, 'diff', 'HEAD', '--', prefix):
        raise ValueError('N36 has uncommitted changes')
    return paths


def pinned_artifact(row: dict) -> dict:
    repo = row['repository_id']; commit_url = row['publication_commit_url']
    prefix = f'https://huggingface.co/datasets/{repo}/commit/'
    if not commit_url.startswith(prefix):
        raise ValueError('Unrecognized stored publication commit URL')
    commit = commit_url[len(prefix):]
    if not SHA40.fullmatch(commit) or not SHA64.fullmatch(row['sha256']):
        raise ValueError('Invalid stored commit or content digest')
    if row['publication_status'] != 'published_verified' or row['verification_status'] != 'verified':
        raise ValueError('External artifact lacks recorded verification')
    if row['revision'] != 'main' and row['revision'] != commit:
        raise ValueError('Stored revision and publication commit disagree')
    remote_path = row['path_in_repository']
    if remote_path.startswith('/') or '..' in remote_path.split('/'):
        raise ValueError('Invalid remote artifact path')
    return {
        'artifact_id': row['artifact_id'], 'local_relative_path': row['local_relative_path'],
        'repository_id': repo, 'revision': commit, 'path_in_repository': remote_path,
        'pinned_url': f'https://huggingface.co/datasets/{repo}/resolve/{commit}/{remote_path}',
        'sha256': row['sha256'], 'size_bytes': int(row['size_bytes']),
        'verified_at_utc': row['verified_at_utc'],
        'revision_source': 'existing publication_commit_url; original registry left unchanged'
    }


def external_references(root: Path, plan: dict) -> dict:
    with (root/'outputs/inventory/external_artifact_publication.csv').open(encoding='utf-8-sig', newline='') as f:
        artifacts = [pinned_artifact(row) for row in csv.DictReader(f)]
    if len(artifacts) != plan['external_individual_artifact_count']:
        raise ValueError('Individual publication count differs from approved scope')
    config = yaml.safe_load((root/'config/publication/external_storage.yaml').read_text(encoding='utf-8'))
    bundles = config['policy']['approved_indexed_bundle_releases']
    if len(bundles) != plan['expected_bundle_release_count']:
        raise ValueError('Bundle release count differs from approved scope')
    for name, row in bundles.items():
        stored = json.loads((root/row['record']).read_text(encoding='utf-8'))
        if not SHA40.fullmatch(row['revision']) or stored['revision'] != row['revision'] or stored['status'] != 'full_remote_verified':
            raise ValueError(f'Invalid or inconsistent bundle revision: {name}')
    reports = config['policy']['verified_report_package_releases']
    for name,row in reports.items():
        if not SHA40.fullmatch(row['revision']) or row['status'] != 'full_remote_verified':
            raise ValueError(f'Invalid report-package revision: {name}')
    return {
        'schema_version': 'zenodo_external_references.v1',
        'note': 'Derived from saved publication records; no fresh network verification. Canonical local evidence is included in the single archive, not duplicated as HF transport ZIPs.',
        'individual_artifacts': artifacts,
        'indexed_bundle_releases': bundles,
        'report_package_releases': reports,
    }


def select_source(tracked: list[str], plan: dict) -> list[str]:
    selected = set(plan['source_root_files'] + plan['required_source_files'])
    for path in tracked:
        if path and not excluded(path, plan):
            selected.add(path)
    return sorted(selected)


def excluded(path: str, plan: dict) -> bool:
    parts = Path(path).parts
    return (any(p in {'.git', '.codex_tmp', '.venv', 'venv', 'env', 'node_modules', '.cache', '__pycache__', '.ipynb_checkpoints', '.pytest_cache', '.mypy_cache', '.ruff_cache'} for p in parts)
            or any(path.startswith(p) for p in plan.get('exclude_prefixes', []))
            or path in plan.get('exclude_files', [])
            or path.startswith('outputs/34_final_streamlit_dashboard_assets/work/'))


def select_records(root: Path, tracked: list[str], plan: dict) -> tuple[list[dict], dict]:
    inventory = root/'outputs/inventory/project_file_inventory.csv'
    run = json.loads((root/'outputs/inventory/inventory_run.json').read_text(encoding='utf-8'))
    if run['status'] != 'completed' or run['summary']['read_error_count']:
        raise ValueError('Refresh the inventory: the saved run is incomplete or has read errors')
    if file_record(root, 'outputs/inventory/project_file_inventory.csv')['sha256'] != run['inventory_sha256']:
        raise ValueError('Inventory CSV checksum differs from its run record')
    selected = {p: {'path': p} for p in select_source(tracked, plan)}
    with inventory.open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            p = row['relative_path']
            if not excluded(p, plan) and any(p.startswith(prefix) for prefix in plan['bulk_prefixes']):
                selected[p] = {'path': p, 'size_bytes': int(row['size_bytes']),
                               'inventory_hash': row['hash_value'], 'hash_bytes': int(row['hash_bytes_read'] or 0)}
    # Keep the original inventory as a historical catalogue, not as the archive manifest.
    selected['outputs/inventory/project_file_inventory.csv'] = {'path': 'outputs/inventory/project_file_inventory.csv'}
    selected['outputs/inventory/inventory_run.json'] = {'path': 'outputs/inventory/inventory_run.json'}
    last = time.monotonic()
    for index, rec in enumerate(selected.values(), 1):
        stat = checked_path(root, rec['path']).stat()
        if 'size_bytes' in rec and stat.st_size != rec['size_bytes']:
            raise ValueError(f"Inventory size mismatch; refresh inventory: {rec['path']}")
        rec.update(size_bytes=stat.st_size, mtime_ns=stat.st_mtime_ns)
        if time.monotonic() - last > 15 or index == len(selected):
            print(f'Preflight: checked {index:,}/{len(selected):,} local paths', flush=True)
            last = time.monotonic()
    return sorted(selected.values(), key=lambda r:r['path']), run


def write_zip(root: Path, target: Path, records: list[dict], generated: dict[str, bytes] | None = None) -> list[dict]:
    entries=[]; last = time.monotonic(); total = 0
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
        for index, rec in enumerate(records, 1):
            path = checked_path(root, rec['path']); before = path.stat()
            info=zipfile.ZipInfo(rec['path'],date_time=(2026,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_STORED if path.suffix.lower() in {'.png','.jpg','.jpeg','.gz','.npz','.pdf','.zip','.docx','.pptx'} else zipfile.ZIP_DEFLATED
            info._compresslevel = 1
            info.external_attr=0o100644 << 16
            with path.open('rb') as source, z.open(info, 'w', force_zip64=True) as sink:
                digest, size, prefix = digest_stream(source, rec['path'], sink, rec.get('hash_bytes', 0))
            after = path.stat()
            if (size != rec['size_bytes'] or before.st_mtime_ns != after.st_mtime_ns
                    or ('mtime_ns' in rec and before.st_mtime_ns != rec['mtime_ns'])
                    or ('sha256' in rec and digest != rec['sha256'])
                    or (rec.get('hash_bytes', 0) and prefix != rec['inventory_hash'])):
                raise ValueError(f"Input changed or inventory digest mismatch: {rec['path']}")
            entries.append({'path': rec['path'], 'size_bytes': size, 'sha256': digest})
            total += size
            if time.monotonic() - last > 15 or index == len(records):
                print(f'Archived {index:,}/{len(records):,} files ({total/1e9:.2f} GB read)', flush=True); last = time.monotonic()
        for name,data in sorted((generated or {}).items()):
            if name in {r['path'] for r in entries}: raise ValueError('Duplicate generated member')
            info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data); entries.append({'path':name,'size_bytes':len(data),'sha256':sha(data),'generated':True})
    verify_zip(target,entries)
    return entries


def verify_zip(path: Path, records: list[dict]) -> None:
    with zipfile.ZipFile(path) as z:
        expected={r['path']:r for r in records}
        if len(z.namelist()) != len(expected) or set(z.namelist()) != set(expected):
            raise ValueError('Archive member list mismatch')
        last = time.monotonic()
        for index, (name,r) in enumerate(expected.items(), 1):
            with z.open(name) as stream:
                digest, size, _ = digest_stream(stream, name)
            if size!=r['size_bytes'] or digest!=r['sha256']:
                raise ValueError(f'Archive verification failed: {name}')
            if time.monotonic() - last > 15 or index == len(expected):
                print(f'Verified {index:,}/{len(expected):,} archive members', flush=True); last = time.monotonic()


def build(root: Path, preflight: bool) -> dict:
    plan=json.loads((root/PLAN).read_text(encoding='utf-8'))
    if plan.get('release_status') == 'published':
        raise ValueError('This version is already published. Do not rebuild the frozen archive; a future release requires a separately approved version and plan.')
    commit=git(root,'rev-parse','HEAD').strip()
    dirty=git(root,'status','--porcelain=v1','--untracked-files=normal').strip()
    if dirty and not preflight:
        raise ValueError('Commit the reviewed release-preparation changes first. Final archives require a clean checkout. Use --preflight for working-tree checks.')
    tracked=git(root,'ls-files','-z').split('\0')
    n36_paths=verify_n36(root,plan)
    records, inventory_run = select_records(root, tracked, plan)
    selected = {r['path']: r for r in records}
    required = n36_paths + plan['supervisor_documents'] + plan['provenance_files']
    if any(p not in selected for p in required):
        raise ValueError('Required evidence or supervisor documents missing from selection')
    refs=external_references(root,plan)
    for row in refs['individual_artifacts']:
        rec = selected.get(row['local_relative_path'])
        if rec is None or rec['size_bytes'] != row['size_bytes']:
            raise ValueError(f"Published artifact missing or different size: {row['local_relative_path']}")
        rec['sha256'] = row['sha256']
    total_bytes = sum(r['size_bytes'] for r in records)
    if total_bytes + len(records)*1024 + 100_000_000 > plan['max_upload_bytes']:
        raise ValueError('Conservative archive size estimate exceeds the configured record quota')
    summary={
        'reserved_doi':plan['reserved_doi'], 'doi_status':plan['doi_status'],
        'source_commit':commit,'working_tree_dirty':bool(dirty),'mode':'preflight' if preflight else 'local_draft_archive',
        'publication_ready':False, 'rights_review':plan['rights_review'],
        'files':len(records), 'uncompressed_bytes':total_bytes,
        'inventory_run_id':inventory_run['inventory_run_id'],
        'excluded':plan['excluded'],
        'n36_package_hashes_verified':123,'n36_physical_files':len(n36_paths),
        'individual_pinned_references':len(refs['individual_artifacts']),
        'bundle_releases':len(refs['indexed_bundle_releases']),
        'fresh_remote_checks':False,
    }
    if preflight:
        return summary
    destination=root/'.codex_tmp'/'zenodo'/plan['zenodo_record_id']/plan['version']/commit[:12]
    if destination.exists(): raise ValueError(f'Release directory already exists; do not overwrite a verified build: {destination}')
    destination.mkdir(parents=True)
    target=destination/f"controlled-300-{plan['version']}-research-artifacts.zip"
    readme=f'''CONTROLLED-300 RESEARCH ARTIFACTS - {plan['version']} - LOCAL DRAFT

Author: Rahul Maddineni
Affiliation: University of Applied Sciences Technikum Wien
DOI: {plan['reserved_doi']} (reserved at build time; publication not performed by this tool)
Source commit: {commit}
Source: {plan['repository']}/tree/{commit}
Dashboard: {plan['dashboard']}

CONTENTS
One ZIP64 archive preserving repository-relative paths: current Controlled-300
raw paintings and metadata; canonical outputs throughout the experiment series,
including bulk restorations, diagnostic maps and tables; saved notebooks;
committed code, configuration, tests, tools, current documentation and supervisor
PDFs; complete dashboard assets; licensing and original publication records.
Notebook outputs and canonical evidence are retained unchanged.
Private drafts, obsolete design iterations, environments, model weights and
duplicate HF transport archives are excluded. No local source files are deleted.
RELEASE_MANIFEST.json gives full SHA-256 hashes for every archived member.
The original project inventory is a historical catalogue, NOT an archive index;
it can list intentionally excluded working files. Use RELEASE_MANIFEST.json
for the exact released selection. Archive payloads were fully read back and hashed.

Extract the single ZIP into an empty directory.
Start with outputs/36_supervisor_publication_reproducibility_package/package/README.md.
Keep the COMPLETE N36 directory: package/ alone is not the full integrity handoff.

REPRODUCTION BOUNDARY
This is the complete selected CURRENT local study, not a backup of historical
Controlled-50 working trees elsewhere. Installed environments and model weights
are not included. Follow the recorded environment and model instructions for
execution; including the files is not a fresh reproduction or deployment test.
No experimental notebook or inference job is rerun by this builder.

PINNED EXTERNAL EVIDENCE
ZENODO_EXTERNAL_REFERENCES.json in the archive covers 2,653 individual stored
publication records, six indexed-bundle releases and the N32 report package.
The individual records' legacy resolve/main links are not used as release pins:
the derived index uses each existing publication_commit_url's full commit SHA.
Original records remain unchanged. SHA-256 values and recorded verification
dates are inherited; this build did not perform new remote network checks.
Canonical local files are included, without duplicate HF transport ZIPs.
Upstream model prerequisites remain documented in the source and N36 appendix.

LICENSING AND PROVENANCE
PUBLICATION IS BLOCKED PENDING OWNER RIGHTS REVIEW. This is a LOCAL draft.
{plan['rights_review']}
Read LICENSE and LICENSES/ before reuse. Original code: MIT. Original research
material: CC BY 4.0 to the extent of the author's rights. Third-party paintings,
embedded image elements, code and model-related material retain existing terms.
Model weights and third-party software installations are not redistributed.
The N01 artwork records and model disclosures are provenance aids, not blanket
legal clearance. The licence of code is not the licence of model weights.

FROZEN RECORDS
The N36 run is {plan['n36']['run_id']}. Its 123 package members and tree digest
were verified against the frozen manifest; all 134 delivery files are included.
Historical "Zenodo planned" statements and disclosed N29/N35 qualifications
are intentionally preserved. This outer release record adds later publication
context without changing producer evidence or recorded checksums.

VERIFY
Check SHA256SUMS.txt against the three named files with SHA-256. The checksum
file does not hash itself. Check every extracted member against the manifest.
No files have been uploaded or published by the local builder.
'''
    generated = {'ZENODO_EXTERNAL_REFERENCES.json': json.dumps(refs,indent=2,ensure_ascii=False).encode('utf-8'),
                 'ZENODO_RELEASE_CONTEXT.txt': readme.encode('utf-8')}
    entries=write_zip(root,target,records,generated)
    print('Hashing the completed archive (streaming)...', flush=True)
    archive_record=file_record(root,target.relative_to(root).as_posix())
    archives=[{'filename':target.name,'size_bytes':archive_record['size_bytes'],'sha256':archive_record['sha256'],'members':entries}]
    (destination/'RELEASE_README.txt').write_text(readme,encoding='utf-8',newline='\n')
    manifest={'schema_version':'zenodo_release_manifest.v2',**summary,'title':plan['title'],'version':plan['version'],'archives':archives,'release_readme_sha256':sha(readme.encode()),'license_scope':'See root LICENSE; component-specific grants with third-party exclusions.'}
    (destination/'RELEASE_MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    outputs=sorted(destination.iterdir())
    sums=''.join(f"{archive_record['sha256'] if p == target else file_record(root,p.relative_to(root).as_posix())['sha256']}  {p.name}\n" for p in outputs)
    (destination/'SHA256SUMS.txt').write_text(sums,encoding='ascii',newline='\n')
    if git(root,'rev-parse','HEAD').strip()!=commit or git(root,'status','--porcelain=v1','--untracked-files=normal').strip():
        raise ValueError('Repository changed during build: do not upload these archives')
    for rec in records:
        # These paths were resolved and checked during selection and archiving.
        stat = (root/rec['path']).stat()
        if stat.st_size != rec['size_bytes'] or stat.st_mtime_ns != rec['mtime_ns']:
            raise ValueError(f"Input changed after archiving: {rec['path']}")
    if sum(p.stat().st_size for p in destination.iterdir()) > plan['max_upload_bytes']:
        raise ValueError('Actual release files exceed the configured record quota')
    summary['local_draft_directory']=str(destination)
    summary['local_draft_files']=[p.name for p in sorted(destination.iterdir())]
    summary['archive_sha256']=archive_record['sha256']
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight',action='store_true',help='Validate inputs without creating upload files; permits pending preparation edits.')
    args=parser.parse_args()
    print(json.dumps(build(ROOT,args.preflight),indent=2))
