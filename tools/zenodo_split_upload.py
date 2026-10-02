"""Split the frozen ZIP without recompression; upload sequentially, never publish."""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '.codex_tmp/zenodo/23092185/v1.0.0/2378961a8acc'
DEST = SOURCE / 'split-upload'
NAME = 'controlled-300-v1.0.0-research-artifacts.zip'
SIZE = 40522491399
SHA = '3ee4f9266477213521cdd4f877c71140360125fa9d0f5badb7fb1712c701a562'
API = 'https://zenodo.org/api/deposit/depositions/23092185'
AGENT = 'Controlled300ZenodoUpload/1.0 (+https://github.com/Rahul-DS25M008/painting_restoration_eval)'
CHUNK = 8 * 1024 * 1024


def digests(path):
    sha, md5 = hashlib.sha256(), hashlib.md5()
    size = 0
    with path.open('rb') as stream:
        while data := stream.read(CHUNK):
            sha.update(data)
            md5.update(data)
            size += len(data)
    return dict(name=path.name, size=size, sha256=sha.hexdigest(), md5=md5.hexdigest())


def split_verified(source, dest, expected_size, expected_sha, count=8):
    if source.stat().st_size != expected_size:
        raise ValueError('Original archive size mismatch')
    dest.mkdir(parents=True, exist_ok=True)
    paths = [dest / f'{source.name}.{i:03d}' for i in range(1, count + 1)]
    if any(p.exists() for p in paths):
        raise ValueError('Parts already exist; refusing to overwrite. Use upload if preparation completed.')
    if shutil.disk_usage(dest).free < expected_size + 100_000_000:
        raise ValueError('Insufficient disk space for a separate split copy')
    whole = hashlib.sha256()
    base, extra = divmod(expected_size, count)
    records = []
    with source.open('rb') as stream:
        for index, path in enumerate(paths):
            remaining = base + (index < extra)
            part_sha, part_md5 = hashlib.sha256(), hashlib.md5()
            size = remaining
            with path.open('xb') as out:
                while remaining:
                    data = stream.read(min(CHUNK, remaining))
                    if not data:
                        raise ValueError('Unexpected source EOF')
                    out.write(data)
                    whole.update(data)
                    part_sha.update(data)
                    part_md5.update(data)
                    remaining -= len(data)
            records.append(dict(name=path.name, size=size, sha256=part_sha.hexdigest(), md5=part_md5.hexdigest()))
            print(f'Created part {index + 1}/{count}: {size:,} bytes', flush=True)
        if stream.read(1) or whole.hexdigest() != expected_sha:
            raise ValueError('Original archive hash mismatch. Do not upload these parts.')
    # Read the saved pieces back, rather than relying only on hashes while writing.
    joined = hashlib.sha256()
    for index, (path, rec) in enumerate(zip(paths, records)):
        if digests(path) != rec:
            raise ValueError(f'Part read-back mismatch: {path.name}')
        with path.open('rb') as stream:
            while data := stream.read(CHUNK):
                joined.update(data)
        print(f'Verified part {index + 1}/{count}', flush=True)
    if joined.hexdigest() != expected_sha:
        raise ValueError('Reassembled bytes do not match the frozen archive')
    return records


def prepare():
    parts = split_verified(SOURCE / NAME, DEST, SIZE, SHA)
    for name in ('RELEASE_MANIFEST.json', 'RIGHTS_AND_REUSE_NOTICE.txt'):
        shutil.copyfile(SOURCE / name, DEST / name)
    readme = (SOURCE / 'RELEASE_README.txt').read_text(encoding='utf-8')
    readme = readme.replace('Extract the single ZIP into an empty directory.',
        'The unchanged single ZIP is distributed as eight numbered byte parts.\n'
        'Download all .zip.001 through .zip.008 files and follow REASSEMBLE.txt\n'
        'before extracting the reassembled ZIP into an empty directory.')
    readme = readme.replace('Check SHA256SUMS.txt against the three named files with SHA-256.',
        'Check SHA256SUMS.txt against all named upload files with SHA-256.')
    (DEST / 'RELEASE_README.txt').write_text(readme, encoding='utf-8')
    addendum = (SOURCE / 'RELEASE_ADDENDUM.txt').read_text(encoding='utf-8').split('UPLOAD CONTENTS')[0]
    addendum += ('UPLOAD CONTENTS\n\nThe unchanged ZIP is delivered as eight near-equal binary parts (.zip.001\n'
        'through .zip.008) because a single large upload failed. These are NOT\n'
        'eight independent ZIP archives. No research payload was recompressed or\n'
        'modified. Concatenation restores the original ZIP byte-for-byte.\n\n'
        'Upload all eight parts, RELEASE_MANIFEST.json, RELEASE_README.txt,\n'
        'RELEASE_ADDENDUM.txt, RIGHTS_AND_REUSE_NOTICE.txt, REASSEMBLE.txt,\n'
        'SPLIT_MANIFEST.json and SHA256SUMS.txt: 15 files in the SAME record.\n'
        'Do not additionally upload the original unsplit ZIP.\n\n'
        'RELEASE_MANIFEST.json remains the original archive-member manifest.\n'
        'SPLIT_MANIFEST.json maps the upload parts to the original archive.\n'
        'SHA256SUMS.txt hashes the other 14 uploaded files, not itself.\n')
    (DEST / 'RELEASE_ADDENDUM.txt').write_text(addendum, encoding='utf-8')
    split_manifest = dict(original_name=NAME, original_size=SIZE, original_sha256=SHA,
                          format='binary concatenation in listed order; not independent ZIPs', parts=parts)
    (DEST / 'SPLIT_MANIFEST.json').write_text(json.dumps(split_manifest, indent=2) + '\n', encoding='utf-8')
    instructions = f'''REASSEMBLE THE CONTROLLED-300 ARCHIVE

Download all eight files named {NAME}.001 through .008
into the same otherwise empty working folder. They are numbered byte parts,
not independent ZIPs. Keep their exact filenames and order. The original ZIP
was not recompressed. Allow an additional 40.53 GB for the joined ZIP, plus
space for extraction. Do not concatenate a wildcard that could include output.

WINDOWS POWERSHELL (run in that folder):
$target = '{NAME}'
if (Test-Path -LiteralPath $target) {{ throw 'Output already exists; use an empty folder.' }}
$out = [System.IO.File]::Open((Join-Path $PWD $target), [System.IO.FileMode]::CreateNew)
try {{
    1..8 | ForEach-Object {{
        $part = '{{0}}.{{1:D3}}' -f $target, $_
        $inputStream = [System.IO.File]::OpenRead((Join-Path $PWD $part))
        try {{ $inputStream.CopyTo($out) }} finally {{ $inputStream.Dispose() }}
    }}
}} finally {{ $out.Dispose() }}
if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ine '{SHA}') {{
    throw 'Checksum mismatch. Do not extract; check the downloaded parts.'
}}

LINUX / macOS (run in that folder, output must not already exist):
cat {NAME}.00{{1,2,3,4,5,6,7,8}} > {NAME}
Linux: sha256sum {NAME}
macOS: shasum -a 256 {NAME}

Expected joined size: {SIZE} bytes
Expected SHA-256: {SHA}

Only after the checksum matches, extract the joined ZIP with a ZIP64-capable
extractor such as 7-Zip. The parts are retained until extraction is verified.
SPLIT_MANIFEST.json records each part's size and SHA-256; SHA256SUMS.txt also
covers companion files. RELEASE_MANIFEST.json covers individual ZIP members.
The original archive and its internal historical context remain unchanged;
read RELEASE_ADDENDUM.txt and RIGHTS_AND_REUSE_NOTICE.txt for later context.
'''
    (DEST / 'REASSEMBLE.txt').write_text(instructions, encoding='utf-8')
    names = ['RELEASE_MANIFEST.json', 'RELEASE_README.txt', 'RELEASE_ADDENDUM.txt',
             'RIGHTS_AND_REUSE_NOTICE.txt', 'REASSEMBLE.txt', 'SPLIT_MANIFEST.json']
    companions = [digests(DEST / name) for name in names]
    sums = ''.join(f"{r['sha256']}  {r['name']}\n" for r in companions + parts)
    (DEST / 'SHA256SUMS.txt').write_text(sums, encoding='utf-8')
    companions.append(digests(DEST / 'SHA256SUMS.txt'))
    # Local-only upload queue; never uploaded as a research artifact.
    queue = dict(record_id=23092185, verified_original_sha256=SHA, companions=companions, parts=parts)
    (DEST / 'upload-queue.local.json').write_text(json.dumps(queue, indent=2) + '\n', encoding='utf-8')
    print(f'READY: 8 verified parts and 7 companions in {DEST}', flush=True)


def draft(token):
    request = urllib.request.Request(API, headers={'Authorization': f'Bearer {token}', 'User-Agent': AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:
        record = json.load(response)
    if record.get('id') != 23092185 or record.get('submitted') is not False:
        raise ValueError('Not the expected unpublished draft; stopping')
    bucket = record.get('links', {}).get('bucket', '')
    import re
    if not re.fullmatch(r'https://zenodo\.org/api/files/[A-Za-z0-9-]+/?', bucket):
        raise ValueError('Unexpected bucket URL')
    if any(f.get('filename') == NAME for f in record.get('files', [])):
        raise ValueError('Remove ONLY the failed original .zip entry from the Zenodo draft, then rerun. Keep companion files.')
    return record, bucket.rstrip('/')


def remote_matches(remote, rec):
    try:
        size = int(remote.get('filesize', remote.get('size', -1)))
    except (TypeError, ValueError):
        return False
    return (remote.get('filename', remote.get('key')) == rec['name']
            and size == rec['size']
            and str(remote.get('checksum', '')).removeprefix('md5:').lower() == rec['md5'])


def upload():
    queue = json.loads((DEST / 'upload-queue.local.json').read_text(encoding='utf-8'))
    if queue['record_id'] != 23092185 or len(queue['parts']) != 8 or queue['verified_original_sha256'] != SHA:
        raise ValueError('Invalid local queue')
    for rec in queue['companions'] + queue['parts']:
        path = DEST / rec['name']
        if path.parent != DEST or path.stat().st_size != rec['size']:
            raise ValueError('Invalid local file path or size')
    token = getpass.getpass('Paste your NEW Zenodo deposit:write token (hidden): ').strip()
    if not token or any(c in token for c in '\r\n"\\'):
        raise ValueError('Invalid token')
    logdir = DEST / 'upload-responses.local'
    logdir.mkdir(exist_ok=True)
    record, bucket = draft(token)
    remote = {f['filename']: f for f in record.get('files', [])}
    for rec in queue['companions'] + queue['parts']:
        if remote_matches(remote.get(rec['name'], {}), rec):
            print(f"Already verified on Zenodo; skipping {rec['name']}", flush=True)
            continue
        path = DEST / rec['name']
        print(f"Checking local bytes: {rec['name']}", flush=True)
        if digests(path) != rec:
            raise ValueError(f"Local checksum mismatch: {rec['name']}")
        response_path = logdir / (rec['name'] + '.response.json')
        print(f"Uploading {rec['name']} ({rec['size']:,} bytes)", flush=True)
        command = ['curl.exe', '--config', '-', '--proto', '=https', '--connect-timeout', '60',
                   '--fail-with-body', '--show-error', '--user-agent', AGENT,
                   '--upload-file', str(path), '--output', str(response_path),
                   '--write-out', '\nHTTP %{http_code}; uploaded %{size_upload} bytes\n',
                   '--url', bucket + '/' + rec['name']]
        result = subprocess.run(command, input=f'header = "Authorization: Bearer {token}"\n', text=True)
        if result.returncode:
            raise RuntimeError(f'Upload failed (curl {result.returncode}). Response: {response_path}. Rerun this same command later; completed verified files will be skipped.')
        response = json.loads(response_path.read_text(encoding='utf-8'))
        if not remote_matches(response, rec):
            raise ValueError(f"Server filename/size/MD5 mismatch: {rec['name']}")
        print(f"VERIFIED on server: {rec['name']}", flush=True)
        if rec in queue['parts'] and rec != queue['parts'][-1]:
            print('Pausing 10 minutes before the next part. Keep this terminal open. Ctrl+C safely stops the queue.', flush=True)
            time.sleep(600)
    final, _ = draft(token)
    final_files = {f['filename']: f for f in final.get('files', [])}
    if not all(remote_matches(final_files.get(r['name'], {}), r) for r in queue['companions'] + queue['parts']):
        raise ValueError('Final draft verification incomplete. Do not publish yet; rerun to recheck.')
    print('DONE: all 15 files verified by server size and MD5. Draft remains UNPUBLISHED.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'upload'])
    args = parser.parse_args()
    try:
        prepare() if args.mode == 'prepare' else upload()
    except KeyboardInterrupt:
        raise SystemExit('Stopped. Completed remote files remain intact; rerun upload to skip verified files.')
