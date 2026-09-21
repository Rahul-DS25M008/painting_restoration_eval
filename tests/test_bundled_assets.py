"""Offline byte-transport tests; no scientific outputs or network are touched."""

from __future__ import annotations

import hashlib
import io
import csv
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from types import ModuleType
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from restoration_eval.bundled_assets import (  # noqa: E402
    RemoteBundleReader, atomic_json, build_bundle, json_bytes,
    safe_relative, sha256_file, split_by_size, verify_bundle,
)
from bundled_artifact_publication import _classify  # noqa: E402
import bundled_artifact_publication as publisher  # noqa: E402


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()

    def asset(self, name: str, data: bytes) -> dict:
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {"asset_id": name, "original_relative_path": name,
                "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}

    def test_roundtrip_and_determinism(self):
        assets = [self.asset("é/second.png", b"second"),
                  self.asset("p001/first.png", b"first")]
        a = self.root / "a.zip"
        b = self.root / "b.zip"
        build_bundle(assets, self.source, a)
        build_bundle(list(reversed(assets)), self.source, b)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        verify_bundle(a, assets)
        with zipfile.ZipFile(a) as archive:
            self.assertEqual(archive.read("é/second.png"), b"second")
            self.assertEqual({x.compress_type for x in archive.infolist()},
                             {zipfile.ZIP_STORED})

    def test_shard_cap_and_oversize(self):
        assets = [self.asset(f"p001/{i}.png", bytes([i]) * 180_000)
                  for i in range(3)]
        parts = split_by_size(assets, max_bytes=300_000)
        self.assertEqual([len(part) for part in parts], [1, 1, 1])
        for number, part in enumerate(parts):
            metadata = build_bundle(part, self.source,
                                    self.root / f"part{number}.zip", max_bytes=300_000)
            self.assertLessEqual(metadata["size_bytes"], 300_000)
        with self.assertRaises(ValueError):
            split_by_size(assets, max_bytes=100_000)

    def test_tamper_source_and_duplicate_members(self):
        asset = self.asset("p001/a.png", b"original")
        archive = self.root / "bundle.zip"
        build_bundle([asset], self.source, archive)
        (self.source / "p001/a.png").write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "Source"):
            build_bundle([asset], self.source, self.root / "other.zip")
        with self.assertRaises(ValueError):
            build_bundle([asset, asset], self.source, self.root / "duplicate.zip")
        with self.assertRaises(ValueError):
            verify_bundle(archive, [{**asset, "sha256": "0" * 64}])
        archive.write_bytes(b"not a ZIP")
        with self.assertRaises(zipfile.BadZipFile):
            verify_bundle(archive, [asset])

    def test_unsafe_paths(self):
        for name in ("../evil", "/absolute", "C:/drive", "p\\a", "a//b", "a/./b"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_relative(name)

    def test_remote_only_cache_and_checksum(self):
        asset = self.asset("p001/a.png", b"fake-png-byte-stream")
        prefix = "publication_tests/bundled_assets/n16/test"
        archive_rel = f"{prefix}/bundles/p001/part-0001.zip"
        index_rel = f"{prefix}/indexes/paintings/p001.json"
        catalogue_rel = f"{prefix}/indexes/catalogue.json"
        repository = self.root / "remote"
        archive = repository / archive_rel
        bundle = build_bundle([asset], self.source, archive)
        row = {**asset, "bundle_path": archive_rel,
               "member_path": asset["original_relative_path"]}
        index = {"schema_version": "bundle_assets.v1", "painting_id": "p001",
                 "assets": [row]}
        index_path = repository / index_rel
        atomic_json(index_path, index)
        catalogue = {
            "schema_version": "bundle_assets.v1", "paintings": {
                "p001": {"path": index_rel, "sha256": sha256_file(index_path),
                         "size_bytes": index_path.stat().st_size}},
            "bundles": {archive_rel: {"sha256": bundle["sha256"],
                                      "size_bytes": bundle["size_bytes"]}},
        }
        atomic_json(repository / catalogue_rel, catalogue)
        downloads = []

        def mock_public_fetch(url: str, target: Path):
            remote_path = url.split("/resolve/revision-123/", 1)[1]
            downloads.append(remote_path)
            shutil.copyfile(repository / remote_path, target)

        reader = RemoteBundleReader("owner/repo", "revision-123", prefix,
                                    self.root / "cache", fetcher=mock_public_fetch)
        first, _ = reader.read_asset("p001", asset["asset_id"])
        second, _ = reader.read_asset("p001", asset["asset_id"])
        self.assertEqual(first, b"fake-png-byte-stream")
        self.assertEqual(second, first)
        self.assertEqual(len(downloads), 3)
        self.assertEqual(reader.download_count, 3)
        self.assertNotIn(str(self.source), " ".join(downloads))
        with self.assertRaises(ValueError):
            RemoteBundleReader("owner/repo", "main", prefix, self.root / "bad")
        (self.root / "cache" / reader._cache_path(archive_rel).name).write_bytes(b"tampered")
        # Changed remote object must fail, not use the source image as fallback.
        archive.write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            reader.read_asset("p001", asset["asset_id"])

    def test_retry_classification(self):
        class Response:
            def __init__(self, status):
                self.status_code = status
                self.headers = {"Retry-After": "11"}

        class Failure(Exception):
            def __init__(self, status):
                self.response = Response(status)

        self.assertEqual(_classify(Failure(429)), ("rate_limit", 11.0))
        self.assertEqual(_classify(Failure(403))[0], "permanent")
        self.assertEqual(_classify(Failure(503))[0], "transient")
        self.assertEqual(_classify(TimeoutError())[0], "ambiguous")

    def test_n22_split_publication_profiles(self):
        candidate = publisher.FULL_SPECS["22c"]
        diagnostic = publisher.FULL_SPECS["22d"]
        self.assertEqual(candidate["repo"], publisher.CANDIDATES_REPO)
        self.assertEqual(diagnostic["repo"], publisher.DIAGNOSTICS_REPO)
        self.assertEqual(candidate["publication_part"], "candidates")
        self.assertEqual(diagnostic["publication_part"], "diagnostics")
        self.assertEqual(candidate["name"], diagnostic["name"])
        self.assertNotEqual(candidate["kind"], diagnostic["kind"])

    def test_full_n16_prepare_resume_with_synthetic_producer(self):
        producer = self.root / "outputs/16_difference_maps_and_spatial_diagnostics"
        manifests = producer / "manifests"
        manifests.mkdir(parents=True)
        (producer / "metrics").mkdir()
        (producer / "validation").mkdir()
        images = []
        for painting in ("p001", "p002"):
            relative = f"outputs/16_difference_maps_and_spatial_diagnostics/images/maps/{painting}/map.png"
            source = self.root / relative
            source.parent.mkdir(parents=True)
            data = (painting + " exact bytes").encode()
            source.write_bytes(data)
            images.append({"map_image_id": f"id_{painting}", "asset_kind": "candidate_map",
                           "candidate_id": f"candidate_{painting}", "case_id": f"case_{painting}",
                           "model_id": "test_model", "painting_id": painting,
                           "map_type": "damaged_absolute_error", "selection_role": "",
                           "relative_path": relative, "sha256": hashlib.sha256(data).hexdigest(),
                           "size_bytes": str(len(data)), "width": "1", "height": "1",
                           "image_mode": "RGB", "format": "PNG", "status": "passed"})
        map_manifest = manifests / "map_images.csv"
        with map_manifest.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(images[0]))
            writer.writeheader()
            writer.writerows(images)
        metrics = producer / "metrics/spatial_diagnostics.csv"
        metrics.write_text("case_id,value\ncase_p001,1\n", encoding="utf-8")
        with (manifests / "artifacts.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "artifact_key",
                    "checksum",
                    "validation_status",
                    "dataset_scope",
                ],
            )
            writer.writeheader()
            writer.writerows([
                {"artifact_key": "spatial_diagnostics.map_manifest",
                 "checksum": sha256_file(map_manifest), "validation_status": "passed",
                 "dataset_scope": "controlled_300"},
                {"artifact_key": "spatial_diagnostics.metrics",
                 "checksum": sha256_file(metrics), "validation_status": "passed",
                 "dataset_scope": "controlled_300"},
            ])
        run_manifest = manifests / "run_manifest.json"
        run_manifest.write_text(json.dumps({"run_status": "completed", "completion_gate_passed": True,
                                            "notebook_name": "16_difference_maps_and_spatial_diagnostics",
                                            "run_id": "synthetic_run"}), encoding="utf-8")
        (producer / "validation/checks.csv").write_text("check_id,status\na,passed\n", encoding="utf-8")
        stage = self.root / ".codex_tmp/bundled_assets/full_test"
        args = SimpleNamespace(staging_dir=str(stage))
        with patch.object(publisher, "ROOT", self.root), \
             patch.object(publisher, "MANIFEST", map_manifest), \
             patch.object(publisher, "RUN_MANIFEST", run_manifest), \
             redirect_stdout(io.StringIO()):
            publisher.prepare_full(args)
            publisher.verify_full_local(stage, deep=True)
            original = sha256_file(next((stage / "bundles").rglob("*.zip")))
            publisher.prepare_full(args)
            self.assertEqual(original, sha256_file(next((stage / "bundles").rglob("*.zip"))))
            remote = {}
            commits = []
            head = ["0" * 40]
            ambiguous_once = [True]
            rate_limit_once = [True]

            class FakeOperation:
                def __init__(self, path_in_repo, path_or_fileobj):
                    self.path_in_repo = path_in_repo
                    self.path_or_fileobj = path_or_fileobj

            class FakeApi:
                def whoami(self):
                    return {"name": "RahulMaddineni264"}

                def repo_info(self, *_args, **_kwargs):
                    return SimpleNamespace(sha=head[0])

                def list_repo_tree(self, *_args, **kwargs):
                    prefix = kwargs["path_in_repo"] + "/"
                    return [SimpleNamespace(path=path, size=len(data),
                                            lfs=SimpleNamespace(sha256=hashlib.sha256(data).hexdigest()))
                            for path, data in remote.items() if path.startswith(prefix)]

                def create_commit(self, *_args, **kwargs):
                    if kwargs["parent_commit"] != head[0]:
                        raise ValueError("stale parent commit")
                    if commits and rate_limit_once[0]:
                        rate_limit_once[0] = False
                        error = RuntimeError("simulated 429")
                        error.response = SimpleNamespace(status_code=429,
                                                         headers={"Retry-After": "1"})
                        raise error
                    for operation in kwargs["operations"]:
                        remote[operation.path_in_repo] = Path(operation.path_or_fileobj).read_bytes()
                    commits.append(len(kwargs["operations"]))
                    head[0] = f"{len(commits):040x}"
                    if ambiguous_once[0]:
                        ambiguous_once[0] = False
                        raise TimeoutError("simulated accepted-but-uncertain commit")
                    return SimpleNamespace(oid=head[0])

            fake_hub = ModuleType("huggingface_hub")
            fake_hub.HfApi = FakeApi
            fake_hub.CommitOperationAdd = FakeOperation
            upload_args = SimpleNamespace(staging_dir=str(stage), confirm="UPLOAD_FULL_N16",
                                          batch_size=2, pace_seconds=0)
            with patch.dict(sys.modules, {"huggingface_hub": fake_hub}), \
                 patch.object(publisher.time, "sleep", return_value=None):
                publisher.upload_full(upload_args)
                first_commit_count = len(commits)
                publisher.upload_full(upload_args)
            self.assertEqual(len(commits), first_commit_count)
            self.assertEqual(len(remote), record_count := len(publisher._files(
                stage, publisher._full_catalogue(stage))))
            self.assertGreater(record_count, 2)
        record = json.loads((stage / "publication_record.json").read_text(encoding="utf-8"))
        self.assertEqual(record["asset_count"], 2)
        self.assertEqual(record["status"], "upload_accepted_remote_verification_pending")


if __name__ == "__main__":
    unittest.main()
