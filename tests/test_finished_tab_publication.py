"""Offline safety/transport tests for the assets-only checkpoint."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import publish_finished_tab_assets as pub


class FinishedAssetsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for relative in pub.SMALL:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"small-artwork")
        self.folder = self.root / pub.BULK / "p001"
        self.folder.mkdir(parents=True)
        assets = {}
        for i in range(36):
            target = self.folder / f"map{i:02}.png"
            target.write_bytes(f"test pixels {i}".encode())
            assets[str(i)] = {"path": target.relative_to(self.root).as_posix(),
                              "sha256": pub.sha256_file(target)}
        (self.folder / "numeric.npz").write_bytes(b"numeric-archive")
        source = self.root / "source.png"
        source.write_bytes(b"source-evidence")
        self.meta = {"painting_id": "p001", "version": "metric_inspection.v1",
            "assets": assets, "regions": {"whole": assets["0"]},
            "sources": {"reference": {"path": "source.png", "sha256": pub.sha256_file(source)}},
            "numeric_sha256": pub.sha256_file(self.folder / "numeric.npz")}
        pub.atomic_json(self.folder / "manifest.json", self.meta)

    def inventory(self):
        return pub.inventory(self.root, ["p001"])

    def test_exact_inventory(self):
        result = self.inventory()
        self.assertEqual(len(result["git_assets"]), 12)
        self.assertEqual(len(result["paintings"]["p001"]), 38)

    def test_rejects_changed_png(self):
        (self.folder / "map00.png").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Manifest hash mismatch"):
            self.inventory()

    def test_rejects_changed_archive(self):
        (self.folder / "numeric.npz").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Numeric archive hash"):
            self.inventory()

    def test_rejects_changed_source(self):
        (self.root / "source.png").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Canonical source mismatch"):
            self.inventory()

    def test_rejects_unexpected_files(self):
        (self.folder / "secret.txt").write_text("not an asset")
        with self.assertRaisesRegex(ValueError, "Expected 36 PNGs"):
            self.inventory()

    def test_rejects_missing_painting(self):
        with self.assertRaisesRegex(ValueError, "Expected exactly"):
            pub.inventory(self.root, ["p001", "p002"])

    def test_remote_conflict_never_overwrites(self):
        local = self.folder / "numeric.npz"
        row = pub.describe(local, self.root)
        entry = SimpleNamespace(path="bundle.zip", size=row["size_bytes"],
                                lfs=SimpleNamespace(sha256="0" * 64))
        with self.assertRaisesRegex(ValueError, "refusing overwrite"):
            pub.check_existing(entry, local, row)
        entry.lfs.sha256 = row["sha256"]
        pub.check_existing(entry, local, row)

    def test_small_remote_git_blob_identity(self):
        local = self.folder / "numeric.npz"
        data = local.read_bytes()
        entry = SimpleNamespace(path="small.json", size=len(data), lfs=None,
                    blob_id=hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest())
        pub.check_existing(entry, local, pub.describe(local, self.root))
        entry.size += 1
        with self.assertRaisesRegex(ValueError, "size conflict"):
            pub.check_existing(entry, local, pub.describe(local, self.root))

    def test_upload_requires_explicit_confirmation(self):
        with self.assertRaisesRegex(ValueError, "Use --confirm"):
            pub.upload(None)

    def test_listing_does_not_expand(self):
        from unittest.mock import Mock
        api = Mock()
        api.list_repo_tree.return_value = []
        self.assertEqual(pub.remote_entries(api, "prefix", "a" * 40), {})
        self.assertFalse(api.list_repo_tree.call_args.kwargs["expand"])

    def test_metadata_receipt_without_any_download(self):
        snapshot = self.inventory()
        with patch.object(pub, "ROOT", self.root), patch.object(pub, "STAGE", self.root / "staging"), \
                patch.object(pub, "inventory", return_value=snapshot):
            pub.prepare()
            stage, plan = pub.load()
            pub.atomic_json(stage / "uploaded.json", {"revision": "b" * 40, "release_id": plan["release_id"]})
            entries = {p: SimpleNamespace(path=p, size=r["size_bytes"],
                       lfs=SimpleNamespace(sha256=r["sha256"])) for p, r in plan["objects"].items()}
            with patch.object(pub, "remote_entries", return_value=entries), \
                    patch.object(pub.RemoteBundleReader, "_public_fetch") as fetch:
                pub.verify_remote(metadata_only=True)
                fetch.assert_not_called()
                receipt = pub.read(self.root / pub.RECEIPT)
                self.assertEqual(receipt["status"], "remote_metadata_verified")
                self.assertEqual(receipt["full_public_download_verification"], "deferred_by_user")
                next(iter(entries.values())).lfs.sha256 = "0" * 64
                with self.assertRaisesRegex(ValueError, "refusing overwrite"):
                    pub.verify_remote(metadata_only=True)

    def test_transient_retry_is_bounded(self):
        from unittest.mock import Mock
        from urllib.error import HTTPError
        transient = HTTPError("https://example.com", 429, "busy", {}, None)
        operation = Mock(side_effect=[transient, "ok"])
        with patch.object(pub.time, "sleep"):
            self.assertEqual(pub.retry_read(operation), "ok")
            self.assertEqual(operation.call_count, 2)
            operation = Mock(side_effect=transient)
            with self.assertRaises(HTTPError):
                pub.retry_read(operation)
            self.assertEqual(operation.call_count, 3)

    def test_prepare_roundtrip_determinism_and_tamper_guard(self):
        snapshot = self.inventory()
        stage_root = self.root / "staging"
        with patch.object(pub, "ROOT", self.root), patch.object(pub, "STAGE", stage_root), \
                patch.object(pub, "inventory", return_value=snapshot):
            pub.prepare()
            stage, plan = pub.load()
            first_plan = (stage / "plan.json").read_bytes()
            pub.prepare()
            self.assertEqual(first_plan, (stage / "plan.json").read_bytes())
            self.assertEqual(len(plan["objects"]), 4)
            pub.verify_local()
            fetched = []

            def fetch(url, target):
                relative = url.split(plan["prefix"] + "/", 1)[1]
                fetched.append(relative)
                target.write_bytes((stage / relative).read_bytes())

            reader = pub.RemoteBundleReader(pub.REPO, "a" * 40, plan["prefix"],
                                             self.root / "cache", fetcher=fetch)
            data, row = reader.read_asset("p001", "manifest.json")
            self.assertEqual(json.loads(data)["painting_id"], "p001")
            self.assertEqual(row["role"], "display")
            self.assertFalse(any("/archive/" in p for p in fetched))
            data, row = reader.read_asset("p001", "numeric.npz")
            self.assertEqual(data, b"numeric-archive")
            self.assertEqual(row["role"], "archive")
            (stage / "bundles/display/p001.zip").write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                pub.load()

    def test_staging_allowlist_excludes_notebook_app_and_bulk(self):
        allowed = pub.SMALL + pub.SUPPORT
        self.assertEqual(len(allowed), 18)
        self.assertFalse(any(p.startswith(("notebooks/", "outputs/", "src/", pub.BULK)) for p in allowed))
        self.assertNotIn("streamlit_app.py", allowed)

    def test_check_git_refuses_foreign_staged_file(self):
        def fake_git(*args):
            if args[0] == "branch":
                return b"main\n"
            return ("\0".join(pub.SMALL + pub.SUPPORT + ("notebooks/35_example.ipynb",)) + "\0").encode()
        with patch.object(pub, "git", side_effect=fake_git):
            with self.assertRaisesRegex(ValueError, "Staged set differs"):
                pub.check_git()

    def test_upload_is_scoped_and_resumes_without_rewriting(self):
        snapshot = self.inventory()
        stage_root = self.root / "staging"
        with patch.object(pub, "ROOT", self.root), patch.object(pub, "STAGE", stage_root), \
                patch.object(pub, "inventory", return_value=snapshot):
            pub.prepare()
            stage, plan = pub.load()
            with patch("huggingface_hub.HfApi") as api_cls, patch.object(pub.time, "sleep"), \
                    patch.object(pub, "remote_entries", return_value={}):
                api = api_cls.return_value
                api.whoami.return_value = {"name": "RahulMaddineni264"}
                api.repo_info.return_value = SimpleNamespace(sha="a" * 40)
                api.create_commit.return_value = SimpleNamespace(oid="b" * 40)
                pub.upload("UPLOAD_FINISHED_TABS_01_03")
                call = api.create_commit.call_args
                self.assertEqual(call.args, (pub.REPO,))
                self.assertEqual(call.kwargs["parent_commit"], "a" * 40)
                operations = call.kwargs["operations"]
                self.assertEqual({o.path_in_repo for o in operations}, set(plan["objects"]))
                self.assertTrue(operations[-1].path_in_repo.endswith("/indexes/catalogue.json"))
                self.assertTrue(all(type(o).__name__ == "CommitOperationAdd" for o in operations))
                self.assertEqual(pub.read(stage / "uploaded.json")["revision"], "b" * 40)
                entries = {p: SimpleNamespace(path=p, size=r["size_bytes"],
                            lfs=SimpleNamespace(sha256=r["sha256"])) for p, r in plan["objects"].items()}
                api.create_commit.reset_mock()
                with patch.object(pub, "remote_entries", return_value=entries):
                    pub.upload("UPLOAD_FINISHED_TABS_01_03")
                api.create_commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
