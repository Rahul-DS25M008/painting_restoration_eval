"""Offline tests; never contact Zenodo or touch the real archive."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('split_upload', Path(__file__).resolve().parents[1] / 'tools/zenodo_split_upload.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class SplitTests(unittest.TestCase):
    def test_eight_parts_reassemble_and_preserve_original(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / 'example.zip'
            payload = bytes(range(256)) * 10 + b'end'
            source.write_bytes(payload)
            dest = Path(td) / 'split'
            records = mod.split_verified(source, dest, len(payload), hashlib.sha256(payload).hexdigest())
            self.assertEqual(len(records), 8)
            self.assertLessEqual(max(r['size'] for r in records) - min(r['size'] for r in records), 1)
            self.assertEqual(b''.join((dest / r['name']).read_bytes() for r in records), payload)
            self.assertEqual(source.read_bytes(), payload)
            with self.assertRaisesRegex(ValueError, 'refusing to overwrite'):
                mod.split_verified(source, dest, len(payload), hashlib.sha256(payload).hexdigest())

    def test_bad_original_hash_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / 'bad.zip'
            source.write_bytes(b'123456789')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                mod.split_verified(source, Path(td) / 'split', 9, '0' * 64)

    def test_server_checksum_and_size_required(self):
        rec = dict(name='part.001', size=42, md5='abc')
        self.assertTrue(mod.remote_matches(dict(key='part.001', size=42, checksum='md5:abc'), rec))
        self.assertTrue(mod.remote_matches(dict(filename='part.001', filesize='42', checksum='abc'), rec))
        self.assertFalse(mod.remote_matches(dict(filename='part.001', filesize=None), rec))
        self.assertFalse(mod.remote_matches(dict(filename='part.001', filesize=42, checksum='wrong'), rec))

    def test_upload_sequential_pause_and_resume(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td)
            companions, parts = [], []
            for index in range(9):
                path = dest / f'file{index}'
                path.write_bytes(str(index).encode())
                (companions if index == 0 else parts).append(mod.digests(path))
            (dest / 'upload-queue.local.json').write_text(json.dumps(dict(record_id=23092185,
                verified_original_sha256=mod.SHA, companions=companions, parts=parts)))
            remote = [dict(filename=r['name'], filesize=r['size'], checksum=r['md5']) for r in companions + parts]
            def fake_run(command, **kwargs):
                name = command[-1].split('/')[-1]
                rec = next(r for r in companions + parts if r['name'] == name)
                self.assertNotIn('test-secret', ' '.join(command))
                self.assertIn('test-secret', kwargs['input'])
                Path(command[command.index('--output') + 1]).write_text(json.dumps(dict(key=name, size=rec['size'], checksum='md5:' + rec['md5'])))
                return type('Result', (), {'returncode': 0})()
            # First part already uploaded: do not retransmit it or sleep for it.
            with patch.object(mod, 'DEST', dest), patch.object(mod.getpass, 'getpass', return_value='test-secret'), patch.object(mod, 'draft', side_effect=[({'files': remote[:2]}, 'https://zenodo.org/api/files/test'), ({'files': remote}, '')]), patch.object(mod.subprocess, 'run', side_effect=fake_run) as run, patch.object(mod.time, 'sleep') as sleep:
                mod.upload()
                self.assertEqual(run.call_count, 7)
                self.assertEqual(sleep.call_count, 6)
                self.assertTrue(all(call.args == (600,) for call in sleep.call_args_list))

    def test_failed_upload_stops_without_sleep_or_publication(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td)
            parts = []
            for index in range(8):
                path = dest / f'part{index}'
                path.write_bytes(b'x')
                parts.append(mod.digests(path))
            (dest / 'upload-queue.local.json').write_text(json.dumps(dict(record_id=23092185,
                verified_original_sha256=mod.SHA, companions=[], parts=parts)))
            failed = type('Result', (), {'returncode': 22})()
            with patch.object(mod, 'DEST', dest), patch.object(mod.getpass, 'getpass', return_value='test-secret'), patch.object(mod, 'draft', return_value=({'files': []}, 'https://zenodo.org/api/files/test')) as draft, patch.object(mod.subprocess, 'run', return_value=failed) as run, patch.object(mod.time, 'sleep') as sleep:
                with self.assertRaisesRegex(RuntimeError, 'Upload failed'):
                    mod.upload()
                self.assertEqual(run.call_count, 1)
                self.assertEqual(draft.call_count, 1)
                sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
