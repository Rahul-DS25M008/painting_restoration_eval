"""Recover an interrupted Zenodo ZIP without recompressing retained members.

Run before committing this helper or refreshing inventory. The original build
commit and its selected source files are preserved; this helper is a separately
hashed recovery instrument, not silently added to the original source snapshot.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import time
import zipfile
import zlib

import build_zenodo_release as base

KNOWN_IMAGE = 'outputs/17_local_consistency_metrics/images/maps/opencv_telea/lcm_215fa6dbe5de016b/texture.png'
GOOD_SHA = 'b7a53a7f53d89c170b2f69e13f293292845449894fbc3ffeb05040bc4a339a66'
BAD_SHA = 'ba7e3075394cb7d398e008cfa3ffa2dce9497ac6ef0d1dd3491a31466ad3c70e'
RECOVERY_FILES = {'tools/resume_zenodo_release.py', 'tests/test_zenodo_resume.py'}


def restore_published_image(root: Path, relative: str, dry_run: bool = False) -> dict:
    """Restore only bytes independently agreed by the producer and bundle index."""
    from PIL import Image
    producers = {
        '17_local_consistency_metrics': ('n17_full', 'map_images.csv'),
        '19_uncertainty_and_spatial_explanation_maps': ('n19_full', 'map_images.csv'),
        '20_semantic_and_structural_consistency': ('n20_full', 'semantic_maps.csv'),
        '22_damage_size_diffusion_uncertainty_extension': ('n22d_full', 'map_images.csv'),
    }
    parts = Path(relative).parts
    if len(parts) < 3 or parts[0] != 'outputs' or parts[1] not in producers or Path(relative).suffix != '.png':
        raise ValueError('Only recognized producer PNGs can be restored automatically')
    bundle_name, manifest_name = producers[parts[1]]
    bundle_root = root/'.codex_tmp/bundled_assets'/bundle_name
    with (bundle_root/'indexes/members.csv').open(encoding='utf-8-sig', newline='') as f:
        rows = [r for r in csv.DictReader(f) if r['original_relative_path'] == relative]
    with (root/'outputs'/parts[1]/'manifests'/manifest_name).open(encoding='utf-8-sig', newline='') as f:
        producer = [r for r in csv.DictReader(f)
                    if r.get('relative_path') in {relative, Path(*parts[2:]).as_posix()}]
    if len(rows) != 1 or len(producer) != 1 or rows[0]['sha256'] not in producer[0].values():
        raise ValueError('Producer and publication index do not independently agree')
    row = rows[0]
    suffix = row['bundle_path'].split('/bundles/', 1)[1]
    bundle = bundle_root/'bundles'/suffix
    if not bundle.resolve().is_relative_to(bundle_root.resolve()):
        raise ValueError('Unsafe bundle path')
    with zipfile.ZipFile(bundle) as z:
        data = z.read(row['member_path'])
    if base.sha(data) != row['sha256'] or len(data) != int(row['size_bytes']):
        raise ValueError('Recovery image does not match its frozen digest')
    Image.open(io.BytesIO(data)).verify()
    target = base.checked_path(root, relative)
    original = target.read_bytes()
    if original == data:
        return {'status': 'already_restored', 'path': relative}
    if dry_run:
        return {'status': 'verified_recovery_copy', 'path': relative,
                'old_sha256': base.sha(original), 'sha256': row['sha256'], 'source_bundle': str(bundle)}
    folder = root/'.codex_tmp/zenodo-recovery'
    folder.mkdir(parents=True, exist_ok=True)
    backup = folder/f"corrupt-{base.sha(relative.encode())[:16]}-{base.sha(original)[:16]}.png"
    if backup.exists():
        if backup.read_bytes() != original:
            raise ValueError('Diagnostic backup collision')
    else:
        with backup.open('xb') as f:
            f.write(original)
    stat = target.stat()
    temporary = target.with_name(target.name+'.zenodo-recovery-tmp')
    with temporary.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.utime(temporary, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    os.replace(temporary, target)
    if base.file_record(root, relative)['sha256'] != row['sha256']:
        raise ValueError('Restored image failed read-back verification')
    result = {'status': 'restored_exact_original', 'path': relative,
              'old_sha256': base.sha(original), 'sha256': row['sha256'],
              'backup': str(backup), 'source_bundle': str(bundle)}
    backup.with_suffix('.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result


def restore_audit(root: Path, report_path: Path) -> dict:
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if report.get('schema_version') != 'zenodo_integrity_audit.v1':
        raise ValueError('Unrecognized recovery report')
    errors = report['errors']
    if any(r['phase'] != 'source' for r in errors):
        raise ValueError('Audit contains non-source errors requiring separate review')
    # Verify all candidates before replacing any source bytes.
    for row in errors:
        relative = row['path']
        rec = row['expected']
        if rec['path'] != relative:
            raise ValueError('Audit path mismatch')
        candidate = restore_published_image(root, relative, dry_run=True)
        current = base.file_record(root, relative)['sha256']
        if candidate['status'] != 'already_restored' and current != row['observed']['sha256']:
            raise ValueError(f'Source changed since audit: {relative}')
        print(f"Verified recovery copy: {relative}", flush=True)
    results = []
    for row in errors:
        result = restore_published_image(root, row['path'])
        with base.checked_path(root, row['path']).open('rb') as f:
            validate_digest(row['expected'], *base.digest_stream(f, row['path'], prefix_bytes=row['expected'].get('hash_bytes', 0)))
        results.append(result)
        print(f"Restored and verified {len(results)}/{len(errors)}: {row['path']}", flush=True)
    summary = {'status': 'all_reported_sources_restored', 'audit_report': str(report_path),
               'restored_count': len(results), 'files': results}
    out = root/'.codex_tmp/zenodo-recovery'/f'batch-recovery-{time.time_ns()}.json'
    out.write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    return summary


def audit_records(root: Path, target: Path, records: list[dict], repair_last: str | None,
                  report_path: Path) -> dict:
    """Read every selected source and ZIP member; never mutate archive or inputs."""
    errors = []
    source_digests = {}
    last = time.monotonic()
    for index, rec in enumerate(records, 1):
        actual = {}
        try:
            path = base.checked_path(root, rec['path'])
            before = path.stat()
            with path.open('rb') as f:
                digest, size, prefix = base.digest_stream(f, rec['path'], prefix_bytes=rec.get('hash_bytes', 0))
            actual = {'sha256': digest, 'size_bytes': size, 'inventory_prefix_sha256': prefix}
            validate_digest(rec, digest, size, prefix)
            after = path.stat()
            if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
                raise ValueError('Source changed during audit')
            source_digests[rec['path']] = (digest, size)
        except (OSError, ValueError, EOFError) as exc:
            errors.append({'phase': 'source', 'path': rec['path'], 'error': str(exc),
                           'expected': rec, 'observed': actual})
        if time.monotonic() - last > 15 or index == len(records):
            print(f'Audited sources {index:,}/{len(records):,}; {len(errors):,} errors collected', flush=True)
            last = time.monotonic()
    indexed = {r['path']: r for r in records}
    pending = []
    archive_count = 0
    last = time.monotonic()
    with zipfile.ZipFile(target) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        expected = [r['path'] for r in records]
        if len(names) != len(set(names)) or names != expected[:len(names)]:
            errors.append({'phase': 'archive_structure', 'path': str(target),
                           'error': 'Archive is not a unique prefix of the original source selection'})
        if repair_last and (not names or names[-1] != repair_last):
            errors.append({'phase': 'repair_request', 'path': repair_last,
                           'error': 'Requested replacement is not the final archive member'})
        for index, info in enumerate(infos, 1):
            actual = {}
            try:
                rec = indexed.get(info.filename)
                with z.open(info) as f:
                    digest, size, prefix = base.digest_stream(f, info.filename,
                                                            prefix_bytes=rec.get('hash_bytes', 0) if rec else 0)
                actual = {'sha256': digest, 'size_bytes': size, 'inventory_prefix_sha256': prefix}
                if rec:
                    validate_digest(rec, digest, size, prefix)
                if info.filename in source_digests and (digest, size) != source_digests[info.filename]:
                    raise ValueError('Archive bytes differ from verified current source')
            except (OSError, ValueError, EOFError, zipfile.BadZipFile, RuntimeError, zlib.error) as exc:
                row = {'phase': 'archive', 'path': info.filename, 'error': str(exc), 'observed': actual}
                if (info.filename == repair_last and index == len(infos)
                        and info.filename in source_digests):
                    pending.append(row)
                else:
                    errors.append(row)
            archive_count += 1
            if time.monotonic() - last > 15 or index == len(infos):
                print(f'Audited ZIP members {index:,}/{len(infos):,}; {len(errors):,} errors collected', flush=True)
                last = time.monotonic()
    report = {'schema_version': 'zenodo_integrity_audit.v1',
              'status': 'errors_found' if errors else 'ready_to_resume',
              'publication_ready': False, 'archive_modified': False,
              'source_files_checked': len(records), 'archive_members_checked': archive_count,
              'error_count': len(errors), 'errors': errors,
              'known_final_member_pending_replacement': pending,
              'note': 'Read-only audit. No files skipped into a successful release; no final release records written.'}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(f'\nAudit complete: {len(errors)} errors. Report: {report_path}', flush=True)
    for row in errors:
        print(f"[{row['phase']}] {row['path']}: {row['error']}", flush=True)
    return report


def audit_release(root: Path, repair_last: str | None) -> dict:
    # Unlike the writer's preflight, preserve missing/size-mismatched records so
    # the audit can report them all instead of failing on the first one.
    commit = base.git(root, 'rev-parse', 'HEAD').strip()
    status = base.git(root, 'status', '--porcelain=v1', '--untracked-files=all')
    if any(line[:3] != '?? ' or line[3:] not in RECOVERY_FILES for line in status.splitlines()):
        raise ValueError('Source checkout changed; do not commit or refresh inventory before recovery')
    plan = json.loads((root/base.PLAN).read_text(encoding='utf-8'))
    run = json.loads((root/'outputs/inventory/inventory_run.json').read_text(encoding='utf-8'))
    if (run['status'] != 'completed' or run['summary']['read_error_count']
            or base.file_record(root, 'outputs/inventory/project_file_inventory.csv')['sha256'] != run['inventory_sha256']):
        raise ValueError('Cannot trust inventory; refusing an audit against invalid reference data')
    selected = {p: {'path': p} for p in base.select_source(base.git(root, 'ls-files', '-z').split('\0'), plan)}
    with (root/'outputs/inventory/project_file_inventory.csv').open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            p = row['relative_path']
            if not base.excluded(p, plan) and any(p.startswith(prefix) for prefix in plan['bulk_prefixes']):
                selected[p] = {'path': p, 'size_bytes': int(row['size_bytes']),
                               'hash_bytes': int(row['hash_bytes_read'] or 0), 'inventory_hash': row['hash_value']}
    for p in ('outputs/inventory/project_file_inventory.csv', 'outputs/inventory/inventory_run.json'):
        selected[p] = {'path': p}
    refs = base.external_references(root, plan)
    for row in refs['individual_artifacts']:
        selected.setdefault(row['local_relative_path'], {'path': row['local_relative_path']}).update(
            sha256=row['sha256'], size_bytes=row['size_bytes'])
    n36 = plan['n36']['root']
    package = json.loads((root/n36/'manifests/package_manifest.json').read_text(encoding='utf-8'))
    for row in package['files']:
        p = f"{n36}/package/{row['package_relative_path']}"
        selected.setdefault(p, {'path': p}).update(sha256=row['sha256'], size_bytes=row['size_bytes'])
    target = root/'.codex_tmp/zenodo'/plan['zenodo_record_id']/plan['version']/commit[:12]/f"controlled-300-{plan['version']}-research-artifacts.zip"
    report = root/'.codex_tmp/zenodo-recovery'/f'integrity-audit-{time.time_ns()}.json'
    return audit_records(root, target, sorted(selected.values(), key=lambda r: r['path']), repair_last, report)


def restore_known_image(root: Path) -> dict:
    """Restore exact producer bytes, preserving a diagnostic copy and timestamp."""
    from PIL import Image
    source = root/'.codex_tmp/bundled_assets/n17_full/bundles/p100/part-0001.zip'
    with zipfile.ZipFile(source) as z:
        data = z.read(KNOWN_IMAGE)
    if base.sha(data) != GOOD_SHA or len(data) != 78211:
        raise ValueError('Recovery bundle does not match the frozen N17 image digest')
    Image.open(io.BytesIO(data)).verify()
    target = base.checked_path(root, KNOWN_IMAGE)
    original = target.read_bytes()
    current = base.sha(original)
    if current == GOOD_SHA:
        return {'status': 'already_restored', 'path': KNOWN_IMAGE, 'sha256': GOOD_SHA}
    if current != BAD_SHA:
        raise ValueError('Unexpected local image bytes; refusing automatic replacement')
    backup = root/'.codex_tmp/zenodo-recovery/corrupt-texture.png'
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists():
        if backup.read_bytes() != original:
            raise ValueError('Existing diagnostic backup differs')
    else:
        with backup.open('xb') as f:
            f.write(original)
    stat = target.stat()
    temporary = target.with_name('texture.png.zenodo-recovery-tmp')
    with temporary.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.utime(temporary, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    os.replace(temporary, target)
    if base.file_record(root, KNOWN_IMAGE)['sha256'] != GOOD_SHA:
        raise ValueError('Restored image failed read-back verification')
    result = {'status': 'restored_exact_original', 'path': KNOWN_IMAGE,
              'old_sha256': BAD_SHA, 'sha256': GOOD_SHA,
              'backup': str(backup), 'source_bundle': str(source)}
    (backup.parent/'image_recovery.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result


def validate_digest(rec: dict, digest: str, size: int, prefix: str) -> None:
    if (('size_bytes' in rec and size != rec['size_bytes'])
            or ('sha256' in rec and digest != rec['sha256'])
            or (rec.get('hash_bytes', 0) and prefix != rec['inventory_hash'])):
        raise ValueError(f"Source/archive digest mismatch: {rec['path']}")


def resume_zip(root: Path, target: Path, records: list[dict], generated: dict[str, bytes],
               repair_last: str | None, backup_dir: Path) -> list[dict]:
    """Validate retained bytes first, back up the tail, then append in place."""
    if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('Archive must be an ordinary file within the repository')
    entries = []
    with zipfile.ZipFile(target) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        expected = [r['path'] for r in records] + sorted(generated)
        if len(names) != len(set(names)) or names != expected[:len(names)]:
            raise ValueError('Partial archive is not an exact, unique prefix of the selected release')
        if repair_last and (not names or names[-1] != repair_last):
            raise ValueError('Requested repair is not the final archive member; nothing changed')
        keep = len(infos) - bool(repair_last)
        if repair_last:
            # Never remove a failed member until its replacement passes the old inventory.
            rec = records[keep]
            with base.checked_path(root, rec['path']).open('rb') as f:
                validate_digest(rec, *base.digest_stream(f, rec['path'], prefix_bytes=rec.get('hash_bytes', 0)))
        last = time.monotonic()
        for index, info in enumerate(infos[:keep]):
            name = info.filename
            rec = records[index] if index < len(records) else {
                'path': name, 'size_bytes': len(generated[name]), 'sha256': base.sha(generated[name])}
            with z.open(info) as f:
                digest, size, prefix = base.digest_stream(f, name, prefix_bytes=rec.get('hash_bytes', 0))
            validate_digest(rec, digest, size, prefix)
            entry = {'path': name, 'size_bytes': size, 'sha256': digest}
            if index >= len(records):
                entry['generated'] = True
            entries.append(entry)
            if time.monotonic() - last > 15 or index + 1 == keep:
                print(f'Validated retained members {index+1:,}/{keep:,} (no recompression)', flush=True)
                last = time.monotonic()
        offset = infos[-1].header_offset if repair_last else z.start_dir
    # This preserves the original central directory and failed member for rollback.
    # Only a small tail is copied, not the already-written 20+ GB payload.
    backup_dir.mkdir(parents=True, exist_ok=True)
    tail = backup_dir/f'archive-tail-{time.time_ns()}.bin'
    with target.open('rb') as source, tail.open('xb') as sink:
        source.seek(offset)
        shutil.copyfileobj(source, sink)
    recovery = {'archive': str(target.resolve()), 'original_size': target.stat().st_size,
                'offset': offset, 'tail_backup': str(tail.resolve()),
                'retained_members': keep, 'replaced_final_member': repair_last}
    tail.with_suffix('.json').write_text(json.dumps(recovery, indent=2)+'\n', encoding='utf-8')
    print(f'Retaining {keep:,} members; writing {len(records)-min(keep,len(records)):,} source files.', flush=True)
    with zipfile.ZipFile(target, 'a', compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as z:
        if repair_last:
            z.filelist = z.filelist[:keep]
            z.NameToInfo = {i.filename: i for i in z.filelist}
            z.start_dir = offset
            z.fp.seek(offset)
            z._didModify = True
        last = time.monotonic()
        for index in range(min(keep, len(records)), len(records)):
            rec = records[index]
            path = base.checked_path(root, rec['path'])
            before = path.stat()
            info = zipfile.ZipInfo(rec['path'], date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED if path.suffix.lower() in {'.png','.jpg','.jpeg','.gz','.npz','.pdf','.zip','.docx','.pptx'} else zipfile.ZIP_DEFLATED
            info._compresslevel = 1
            info.external_attr = 0o100644 << 16
            with path.open('rb') as source, z.open(info, 'w', force_zip64=True) as sink:
                digest, size, prefix = base.digest_stream(source, rec['path'], sink, rec.get('hash_bytes', 0))
            validate_digest(rec, digest, size, prefix)
            if before.st_mtime_ns != path.stat().st_mtime_ns or before.st_mtime_ns != rec.get('mtime_ns', before.st_mtime_ns):
                raise ValueError(f"Input changed while resuming: {rec['path']}")
            entries.append({'path': rec['path'], 'size_bytes': size, 'sha256': digest})
            if time.monotonic() - last > 15 or index + 1 == len(records):
                print(f'Archived {index+1:,}/{len(records):,} source files (including retained members)', flush=True)
                last = time.monotonic()
        present = {i.filename for i in z.infolist()}
        for name, data in sorted(generated.items()):
            if name in present:
                continue
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
            entries.append({'path': name, 'size_bytes': len(data), 'sha256': base.sha(data), 'generated': True})
    base.verify_zip(target, entries)
    return entries


def resume(root: Path, repair_last: str | None) -> dict:
    commit = base.git(root, 'rev-parse', 'HEAD').strip()
    status = base.git(root, 'status', '--porcelain=v1', '--untracked-files=all')
    for line in status.splitlines():
        if line[:3] != '?? ' or line[3:] not in RECOVERY_FILES:
            raise ValueError('Source checkout changed. Do not commit or refresh inventory before this recovery.')
    plan = json.loads((root/base.PLAN).read_text(encoding='utf-8'))
    destination = root/'.codex_tmp/zenodo'/plan['zenodo_record_id']/plan['version']/commit[:12]
    target = destination/f"controlled-300-{plan['version']}-research-artifacts.zip"
    if (destination/'RELEASE_MANIFEST.json').exists() or (destination/'SHA256SUMS.txt').exists():
        raise ValueError('Final release records already exist; refusing to modify a finalized archive')
    n36 = base.verify_n36(root, plan)
    records, inventory = base.select_records(root, base.git(root, 'ls-files', '-z').split('\0'), plan)
    selected = {r['path']: r for r in records}
    for p in n36 + plan['supervisor_documents'] + plan['provenance_files']:
        if p not in selected:
            raise ValueError(f'Required release file missing: {p}')
    refs = base.external_references(root, plan)
    for row in refs['individual_artifacts']:
        rec = selected.get(row['local_relative_path'])
        if rec is None or rec['size_bytes'] != row['size_bytes']:
            raise ValueError(f"Published artifact missing or changed: {row['local_relative_path']}")
        rec['sha256'] = row['sha256']
    total = sum(r['size_bytes'] for r in records)
    if total + len(records)*1024 + 100_000_000 > plan['max_upload_bytes']:
        raise ValueError('Conservative release estimate exceeds quota')
    helper_digest = base.file_record(root, 'tools/resume_zenodo_release.py')['sha256']
    # Evaluate only the original builder's literal f-string, preserving its exact
    # release context. No source-code substitutions or weakened build gates.
    import ast
    tree = ast.parse((root/'tools/build_zenodo_release.py').read_text(encoding='utf-8'))
    build_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'build')
    readme_node = next(n.value for n in build_node.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == 'readme' for t in n.targets))
    readme = eval(compile(ast.Expression(readme_node), '<original release readme>', 'eval'),
                  {'__builtins__': {}}, {'plan': plan, 'commit': commit})
    generated = {'ZENODO_EXTERNAL_REFERENCES.json': json.dumps(refs, indent=2, ensure_ascii=False).encode('utf-8'),
                 'ZENODO_RELEASE_CONTEXT.txt': readme.encode('utf-8')}
    entries = resume_zip(root, target, records, generated, repair_last, root/'.codex_tmp/zenodo-recovery')
    print('Hashing completed ZIP (streaming, no recompression)...', flush=True)
    archive = base.file_record(root, target.relative_to(root).as_posix())
    if (base.git(root, 'rev-parse', 'HEAD').strip() != commit
            or base.git(root, 'status', '--porcelain=v1', '--untracked-files=all') != status
            or base.file_record(root, 'tools/resume_zenodo_release.py')['sha256'] != helper_digest):
        raise ValueError('Repository or recovery helper changed during recovery; do not upload')
    for rec in records:
        stat = (root/rec['path']).stat()
        if stat.st_size != rec['size_bytes'] or stat.st_mtime_ns != rec['mtime_ns']:
            raise ValueError(f"Source changed during recovery: {rec['path']}")
    summary = {'reserved_doi': plan['reserved_doi'], 'doi_status': plan['doi_status'],
               'source_commit': commit, 'working_tree_dirty': False, 'mode': 'resumed_local_draft_archive',
               'publication_ready': False, 'rights_review': plan['rights_review'],
               'files': len(records), 'uncompressed_bytes': total,
               'inventory_run_id': inventory['inventory_run_id'], 'excluded': plan['excluded'],
               'n36_package_hashes_verified': plan['n36']['package_file_count'], 'n36_physical_files': len(n36),
               'individual_pinned_references': len(refs['individual_artifacts']),
               'bundle_releases': len(refs['indexed_bundle_releases']), 'fresh_remote_checks': False,
               'recovery': {'helper_sha256': helper_digest, 'helper_not_in_original_source_commit': True,
                            'untracked_recovery_files': sorted(RECOVERY_FILES), 'replaced_final_member': repair_last}}
    manifest = {'schema_version': 'zenodo_release_manifest.v2', **summary,
                'title': plan['title'], 'version': plan['version'],
                'archives': [{'filename': target.name, 'size_bytes': archive['size_bytes'],
                              'sha256': archive['sha256'], 'members': entries}],
                'release_readme_sha256': base.sha(readme.encode()),
                'license_scope': 'See root LICENSE; component-specific grants with third-party exclusions.'}
    (destination/'RELEASE_README.txt').write_text(readme, encoding='utf-8', newline='\n')
    (destination/'RELEASE_MANIFEST.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n', encoding='utf-8', newline='\n')
    outputs = sorted(destination.iterdir())
    sums = ''.join(f"{archive['sha256'] if p == target else base.file_record(root,p.relative_to(root).as_posix())['sha256']}  {p.name}\n" for p in outputs)
    (destination/'SHA256SUMS.txt').write_text(sums, encoding='ascii', newline='\n')
    if sum(p.stat().st_size for p in destination.iterdir()) > plan['max_upload_bytes']:
        raise ValueError('Final upload size exceeds quota; do not upload')
    return {**summary, 'local_draft_directory': str(destination), 'archive_sha256': archive['sha256']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore-known-image', action='store_true')
    parser.add_argument('--restore-n17-image', help='Restore a producer-verified image from its retained N17 bundle')
    parser.add_argument('--restore-audit', type=Path, help='Restore all source errors from a saved audit using verified original publication bundles')
    parser.add_argument('--audit-all', action='store_true', help='Read-only scan of all sources and existing ZIP members; report all file errors together')
    parser.add_argument('--repair-last', help='Exact final member to replace from verified local source')
    args = parser.parse_args()
    if args.restore_known_image:
        result = restore_known_image(base.ROOT)
    elif args.restore_n17_image:
        result = restore_published_image(base.ROOT, args.restore_n17_image)
    elif args.restore_audit:
        result = restore_audit(base.ROOT, args.restore_audit)
    elif args.audit_all:
        result = audit_release(base.ROOT, args.repair_last)
        print(f"Result: {result['status']}. The ZIP was not modified.")
        raise SystemExit(2 if result['error_count'] else 0)
    else:
        result = resume(base.ROOT, args.repair_last)
    print(json.dumps(result, indent=2))
