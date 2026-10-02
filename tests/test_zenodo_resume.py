"""Offline recovery tests; never operate on the real research archive."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
import json
import io
import csv

sys.path.insert(0, str(Path(__file__).parents[1]/'tools'))
import resume_zenodo_release as mod


class ResumeTests(unittest.TestCase):
    def record(self, name, data):
        return {'path': name, 'size_bytes': len(data), 'hash_bytes': len(data),
                'inventory_hash': mod.base.sha(data)}

    def test_repairs_last_and_retains_original_payload(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a, b, c = b'first original'*200, b'good png bytes', b'last original'*300
            records = [self.record('a.txt', a), self.record('b.png', b), self.record('c.txt', c)]
            for row, data in zip(records, (a, b, c)):
                (root/row['path']).write_bytes(data)
            target = root/'partial.zip'
            with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr('a.txt', a)
                z.writestr('b.png', b'corrupt bytes')
            with zipfile.ZipFile(target) as z:
                offset = z.getinfo('b.png').header_offset
            original = target.read_bytes()
            entries = mod.resume_zip(root, target, records, {'context.txt': b'context'}, 'b.png', root/'backup')
            self.assertEqual(target.read_bytes()[:offset], original[:offset])
            self.assertEqual(next((root/'backup').glob('*.bin')).read_bytes(), original[offset:])
            with zipfile.ZipFile(target) as z:
                self.assertEqual(z.namelist(), ['a.txt', 'b.png', 'c.txt', 'context.txt'])
                self.assertEqual(z.read('b.png'), b)
                self.assertIsNone(z.testzip())
            self.assertEqual(len(entries), 4)

    def test_bad_replacement_does_not_modify_zip(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); target = root/'partial.zip'
            (root/'a.png').write_bytes(b'bad')
            with zipfile.ZipFile(target, 'w') as z:
                z.writestr('a.png', b'bad')
            before = target.read_bytes()
            with self.assertRaises(ValueError):
                mod.resume_zip(root, target, [self.record('a.png', b'yes')], {}, 'a.png', root/'backup')
            self.assertEqual(target.read_bytes(), before)

    def test_invalid_retained_hash_does_not_modify_zip(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); target = root/'partial.zip'
            with zipfile.ZipFile(target, 'w') as z:
                z.writestr('a.txt', b'wrong')
            before = target.read_bytes()
            with self.assertRaises(ValueError):
                mod.resume_zip(root, target, [self.record('a.txt', b'right')], {}, None, root/'backup')
            self.assertEqual(target.read_bytes(), before)

    def test_wrong_repair_target_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); target = root/'partial.zip'
            with zipfile.ZipFile(target, 'w') as z:
                z.writestr('a.txt', b'a')
            with self.assertRaises(ValueError):
                mod.resume_zip(root, target, [self.record('a.txt', b'a')], {}, 'other.txt', root/'backup')

    def test_valid_prefix_resumes_without_replacement(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); target = root/'partial.zip'
            (root/'b.txt').write_bytes(b'b')
            with zipfile.ZipFile(target, 'w') as z:
                z.writestr('a.txt', b'a')
            rows = [self.record('a.txt', b'a'), self.record('b.txt', b'b')]
            mod.resume_zip(root, target, rows, {'context': b'c'}, None, root/'backup')
            # Retry after a completed archive but before sidecar finalization.
            entries = mod.resume_zip(root, target, rows, {'context': b'c'}, None, root/'backup')
            self.assertEqual(len(entries), 3)
            with zipfile.ZipFile(target) as z:
                self.assertEqual(z.namelist(), ['a.txt', 'b.txt', 'context'])

    def test_nonprefix_archive_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); target = root/'partial.zip'
            with zipfile.ZipFile(target, 'w') as z:
                z.writestr('b.txt', b'b')
            with self.assertRaises(ValueError):
                mod.resume_zip(root, target, [self.record('a.txt', b'a')], {}, None, root/'backup')

    def test_audit_collects_all_errors_and_leaves_archive_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); target = root/'partial.zip'
            rows = [self.record('a.txt', b'good-a'), self.record('b.txt', b'good-b'),
                    self.record('c.txt', b'good-c'), self.record('d.txt', b'good-d')]
            (root/'a.txt').write_bytes(b'bad-a')
            (root/'b.txt').write_bytes(b'bad-b')
            (root/'d.txt').write_bytes(b'good-d')
            with zipfile.ZipFile(target, 'w') as z:
                z.writestr('a.txt', b'bad-a')
                z.writestr('b.txt', b'bad-b')
            before = target.read_bytes()
            report = mod.audit_records(root, target, rows, None, root/'audit.json')
            self.assertEqual(report['source_files_checked'], 4)
            self.assertEqual(report['archive_members_checked'], 2)
            self.assertEqual(report['error_count'], 5)
            self.assertEqual(report['status'], 'errors_found')
            self.assertFalse(report['publication_ready'])
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(json.loads((root/'audit.json').read_text())['error_count'], 5)
            self.assertFalse((root/'RELEASE_MANIFEST.json').exists())

    def test_audit_identifies_verified_final_repair_without_hiding_other_errors(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); target = root/'partial.zip'
            rows = [self.record('a.txt', b'good'), self.record('b.txt', b'good')]
            (root/'a.txt').write_bytes(b'good')
            (root/'b.txt').write_bytes(b'wrong')
            with zipfile.ZipFile(target, 'w') as z:
                z.writestr('a.txt', b'bad')
            report = mod.audit_records(root, target, rows, 'a.txt', root/'audit.json')
            self.assertEqual(report['error_count'], 1)
            self.assertEqual(report['errors'][0]['path'], 'b.txt')
            self.assertEqual(len(report['known_final_member_pending_replacement']), 1)

    def test_clean_audit_does_not_append_missing_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); target = root/'partial.zip'
            (root/'a.txt').write_bytes(b'a'); (root/'b.txt').write_bytes(b'b')
            with zipfile.ZipFile(target, 'w') as z:
                z.writestr('a.txt', b'a')
            before = target.read_bytes()
            report = mod.audit_records(root, target, [self.record('a.txt', b'a'), {'path': 'b.txt'}], None, root/'audit.json')
            self.assertEqual(report['status'], 'ready_to_resume')
            self.assertEqual(report['error_count'], 0)
            self.assertEqual(target.read_bytes(), before)

    def test_restores_producer_relative_path_and_preserves_corrupt_backup(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            prefix = 'outputs/22_damage_size_diffusion_uncertainty_extension'
            name = prefix+'/images/uncertainty/example.png'
            target = root/name
            target.parent.mkdir(parents=True)
            target.write_bytes(b'corrupt')
            original_mtime = target.stat().st_mtime_ns
            stream = io.BytesIO(); Image.new('RGB', (2, 2)).save(stream, format='PNG')
            data = stream.getvalue()
            bundle_root = root/'.codex_tmp/bundled_assets/n22d_full'
            (bundle_root/'indexes').mkdir(parents=True)
            (bundle_root/'bundles/p001').mkdir(parents=True)
            with zipfile.ZipFile(bundle_root/'bundles/p001/part-0001.zip', 'w') as z:
                z.writestr(name, data)
            row = {'original_relative_path': name, 'bundle_path': 'release/bundles/p001/part-0001.zip',
                   'member_path': name, 'sha256': mod.base.sha(data), 'size_bytes': len(data)}
            with (bundle_root/'indexes/members.csv').open('w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=list(row)); w.writeheader(); w.writerow(row)
            (root/prefix/'manifests').mkdir()
            producer = {'relative_path': 'images/uncertainty/example.png', 'sha256': mod.base.sha(data)}
            with (root/prefix/'manifests/map_images.csv').open('w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=list(producer)); w.writeheader(); w.writerow(producer)
            result = mod.restore_published_image(root, name, dry_run=True)
            self.assertEqual(result['status'], 'verified_recovery_copy')
            self.assertEqual(target.read_bytes(), b'corrupt')
            result = mod.restore_published_image(root, name)
            self.assertEqual(target.read_bytes(), data)
            self.assertEqual(Path(result['backup']).read_bytes(), b'corrupt')
            self.assertEqual(target.stat().st_mtime_ns, original_mtime)


if __name__ == '__main__':
    unittest.main()
