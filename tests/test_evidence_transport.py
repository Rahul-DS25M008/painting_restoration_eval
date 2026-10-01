"""Deterministic offline transport tests; no real HTTP and no scientific writes."""
import io
from pathlib import Path
import sys
import tempfile
import os
import time
from concurrent.futures import ThreadPoolExecutor
import unittest
from urllib.error import HTTPError
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from restoration_eval.evidence_transport import Reader, EvidenceUnavailable, digest, read_bytes, image_cache, MIB


def route(data=b"saved", path="evidence/a.png"):
    return dict(repo="RahulMaddineni264/painting-restoration-eval-diagnostics", revision="a" * 40,
                path=path, sha256=digest(data), size_bytes=len(data))


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name)

    def reader(self, data=b"saved", **kwargs):
        return Reader(self.cache, opener=lambda *a, **k: io.BytesIO(data), **kwargs)

    def test_cold_warm_and_corrupt_cache(self):
        reader = self.reader()
        path = reader.object(route())
        self.assertEqual(reader.request_count, 1)
        self.assertEqual(reader.object(route()).read_bytes(), b"saved")
        self.assertEqual(reader.request_count, 1)
        path.write_bytes(b"wrong")
        self.assertEqual(reader.object(route()).read_bytes(), b"saved")
        self.assertEqual(reader.request_count, 2)

    def test_oversize_stream_fails_and_cleans_partial(self):
        with self.assertRaises(EvidenceUnavailable): self.reader(b"saved-too-large").object(route())
        self.assertFalse(list(self.cache.glob("*.partial")))
        self.assertFalse(list(self.cache.glob("*.lock")))

    def test_wrong_hash_fails_closed(self):
        with self.assertRaises(EvidenceUnavailable): self.reader(b"wrong").object(route())
        self.assertFalse(list(self.cache.iterdir()))

    def test_mutable_revision_rejected_before_request(self):
        reader = self.reader()
        with self.assertRaises(EvidenceUnavailable): reader.object({**route(), "revision": "main"})
        self.assertEqual(reader.request_count, 0)

    def test_traversal_rejected(self):
        with self.assertRaises(ValueError): self.reader().object(route(path="../private"))

    def test_http_404_does_not_retry(self):
        def fail(*a, **k): raise HTTPError("url", 404, "missing", {}, None)
        reader = Reader(self.cache, opener=fail)
        with self.assertRaisesRegex(EvidenceUnavailable, "404"): reader.object(route())
        self.assertEqual(reader.request_count, 1)

    def test_retry_statuses_and_timeout_are_bounded(self):
        for status in (429, 503, "timeout"):
            def fail(*a, **k):
                if status == "timeout": raise TimeoutError()
                raise HTTPError("url", status, "unavailable", {"Retry-After": "0"}, None)
            reader = Reader(self.cache, opener=fail)
            with self.assertRaises(EvidenceUnavailable): reader.object(route())
            self.assertEqual(reader.request_count, 2)

    def test_bundle_and_missing_member(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("exact.png", b"saved")
        raw = output.getvalue()
        entry = {**route(), "member_path": "exact.png", "bundle": route(raw, "bundle.zip")}
        reader = self.reader(raw)
        self.assertEqual(reader.read(entry), b"saved")
        with self.assertRaisesRegex(EvidenceUnavailable, "missing"):
            reader.read({**entry, "member_path": "missing.png"})

    def test_invalid_zip(self):
        entry = {**route(), "member_path": "exact.png", "bundle": route()}
        with self.assertRaisesRegex(EvidenceUnavailable, "invalid"): self.reader().read(entry)

    def test_eviction(self):
        reader = self.reader(max_cache=9, low_water=5)
        first = reader.object(route(path="first.png"))
        second = reader.object(route(path="second.png"))
        self.assertFalse(first.exists())
        self.assertTrue(second.exists())

    def test_git_newline_reconstruction_requires_exact_hash(self):
        path = self.cache / "record.csv"
        path.write_bytes(b"one,two\n1,2\n")
        recorded = b"one,two\r\n1,2\r\n"
        self.assertEqual(read_bytes(path, digest(recorded), len(recorded), root=self.cache), recorded)
        with self.assertRaises(EvidenceUnavailable): read_bytes(path, "0" * 64, root=self.cache)

    def test_changed_local_bytes_do_not_fall_back(self):
        path = self.cache / "image.png"
        path.write_bytes(b"wrong")
        with self.assertRaises(EvidenceUnavailable): read_bytes(path, digest(b"saved"), root=self.cache)

    def test_concurrent_same_object_is_downloaded_once(self):
        def fetch(*a, **k):
            time.sleep(.08)
            return io.BytesIO(b"saved")
        reader = Reader(self.cache, opener=fetch)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: reader.object(route()).read_bytes(), range(2)))
        self.assertEqual(results, [b"saved", b"saved"])
        self.assertEqual(reader.request_count, 1)

    def test_stale_lock_and_partial_cleanup(self):
        reader = self.reader()
        target = self.cache / digest(reader.url(route()).encode())
        target.with_suffix(".partial").write_bytes(b"unfinished")
        target.with_suffix(".lock").touch()
        os.utime(target.with_suffix(".lock"), (time.time()-130, time.time()-130))
        self.assertEqual(reader.object(route()).read_bytes(), b"saved")
        self.assertFalse(list(self.cache.glob("*.partial")))
        self.assertFalse(list(self.cache.glob("*.lock")))

    def test_encoded_image_cache_is_byte_bounded(self):
        @image_cache
        def image(key): return str(key) + "x" * (5*MIB)
        for i in range(17): image(i)
        self.assertLessEqual(image.cache_bytes(), 64*MIB)
        image.cache_clear()
        self.assertEqual(image.cache_bytes(), 0)


if __name__ == "__main__": unittest.main()
