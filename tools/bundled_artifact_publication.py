"""Resumable diagnostic indexed-bundle publication; no notebook or Git execution.

The bounded smoke commands remain N16-only. Full uploads require explicit
confirmation and a completed, checksum-validated producer run.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import random
import shutil
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from restoration_eval.bundled_assets import (  # noqa: E402
    MAX_BUNDLE_BYTES, SCHEMA, RemoteBundleReader, atomic_json,
    build_bundle, json_bytes, safe_relative, sha256_bytes, sha256_file,
    split_by_size, verify_bundle, verify_source,
)

REPO = "RahulMaddineni264/painting-restoration-eval-diagnostics"
MANIFEST = ROOT / "outputs/16_difference_maps_and_spatial_diagnostics/manifests/map_images.csv"
RUN_MANIFEST = ROOT / "outputs/16_difference_maps_and_spatial_diagnostics/manifests/run_manifest.json"
MAX_SMOKE_BUNDLES = 4
MAX_SMOKE_BUNDLE_BYTES = 128 * 1024 * 1024

FULL_SPECS = {
    "16": {
        "name": "16_difference_maps_and_spatial_diagnostics",
        "metric_file": "spatial_diagnostics.csv",
        "metric_key": "spatial_diagnostics.metrics",
        "map_key": "spatial_diagnostics.map_manifest",
        "kind": "n16_full_controlled_300",
    },
    "17": {
        "name": "17_local_consistency_metrics",
        "metric_file": "local_consistency.csv",
        "metric_key": "local_consistency.metrics",
        "map_key": "local_consistency.map_manifest",
        "kind": "n17_full_controlled_300",
    },
    "19": {
        "name": "19_uncertainty_and_spatial_explanation_maps",
        "manifest_file": "map_images.csv",
        "metric_file": "spatial_explanations.csv",
        "metric_key": "spatial_explanations.metrics",
        "map_key": "spatial_explanations.map_manifest",
        "kind": "n19_full_controlled_300",
    },
    "20": {
        "name": "20_semantic_and_structural_consistency",
        "manifest_file": "semantic_maps.csv",
        "metric_file": "semantic_structural_metrics.csv",
        "metric_key": "semantic_structural.metrics",
        "map_key": "semantic_structural.map_manifest",
        "numeric_file": "semantic_maps.npz",
        "numeric_key": "semantic_structural.numeric_maps",
        "figure_file": "semantic_examples.png",
        "figure_key": "semantic_structural.examples",
        "kind": "n20_full_controlled_300",
    },
}
FULL_NOTEBOOK = "16"


def _full_spec() -> dict:
    return FULL_SPECS[FULL_NOTEBOOK]


def _rows(manifest: Path = MANIFEST) -> list[dict]:
    with manifest.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    identity_field = {
        "19": "map_asset_id",
        "20": "semantic_map_asset_id",
    }.get(FULL_NOTEBOOK, "map_image_id")
    if not rows or len({row[identity_field] for row in rows}) != len(rows):
        raise ValueError(f"Map manifest empty or has duplicate {identity_field}")
    return rows


def _select() -> list[dict]:
    """25 maps from each of two fixed IDs and one panel-bearing painting."""
    rows = _rows()
    panels = sorted(
        (row for row in rows if row["asset_kind"] == "selected_panel"
         and row["painting_id"] and row["status"] == "passed"),
        key=lambda row: (row["painting_id"], row["map_image_id"]),
    )
    if not panels:
        raise ValueError("No validated N16 selected panel exists")
    panel = next(
        (row for row in panels if row["painting_id"] not in {"p001", "p002"}),
        None,
    )
    if panel is None:
        raise ValueError("No panel belongs to a third painting")
    paintings = list(dict.fromkeys(["p001", "p002", panel["painting_id"]]))
    if len(paintings) != 3:
        raise ValueError("Smoke cohort must cover three distinct paintings")
    selected = []
    for painting in paintings:
        maps = [row for row in rows if row["painting_id"] == painting
                and row["asset_kind"] == "candidate_map" and row["status"] == "passed"]
        by_type: dict[str, list[dict]] = defaultdict(list)
        for row in maps:
            by_type[row["map_type"]].append(row)
        if len(by_type) < 5:
            raise ValueError(f"Insufficient map-type coverage for {painting}")
        for map_type in sorted(by_type):
            selected.extend(sorted(by_type[map_type],
                                   key=lambda row: row["map_image_id"])[:5])
    selected.append(panel)
    if len(selected) != 76 or len({row["map_image_id"] for row in selected}) != 76:
        raise ValueError("Smoke selection must be 75 maps plus one panel")
    return selected


def _asset(row: dict) -> dict:
    return {
        "asset_id": (
            row.get("map_image_id")
            or row.get("map_asset_id")
            or row.get("semantic_map_asset_id")
        ),
        "original_relative_path": safe_relative(row["relative_path"]),
        "painting_id": row["painting_id"],
        "case_id": row["case_id"],
        "candidate_id": row["candidate_id"],
        "model_id": row["model_id"],
        "map_type": row["map_type"],
        "asset_kind": row["asset_kind"],
        "selection_role": row["selection_role"],
        "sha256": row["sha256"],
        "size_bytes": int(row["size_bytes"]),
        "width": int(row["width"]),
        "height": int(row["height"]),
        "image_mode": row["image_mode"],
        "format": row["format"],
    }


def _stage(args: argparse.Namespace) -> Path:
    stage = Path(args.staging_dir).resolve()
    if stage == ROOT or stage.is_relative_to(ROOT / "outputs"):
        raise ValueError("Staging may not be inside canonical outputs")
    if stage.is_relative_to(ROOT) and not stage.is_relative_to(ROOT / ".codex_tmp"):
        raise ValueError("In-repository staging must be inside ignored .codex_tmp")
    return stage


def prepare(args: argparse.Namespace) -> None:
    stage = _stage(args)
    source_rows = _select()
    assets = [_asset(row) for row in source_rows]
    for number, asset in enumerate(assets, 1):
        verify_source(asset, ROOT)
        if number % 20 == 0 or number == len(assets):
            print(f"Source hash preflight {number}/{len(assets)}", flush=True)
    run = json.loads(RUN_MANIFEST.read_text(encoding="utf-8"))
    if run.get("run_status") != "completed":
        raise ValueError("N16 producer run is not completed")
    manifest_hash = sha256_file(MANIFEST)
    selection_hash = sha256_bytes(json_bytes({"assets": assets,
                                             "source_run_id": run["run_id"],
                                             "manifest_sha256": manifest_hash,
                                             "max_bundle_bytes": args.max_bundle_mib * 1024 * 1024}))
    test_id = selection_hash[:16]
    prefix = f"publication_tests/bundled_assets/n16/{test_id}"
    max_bytes = args.max_bundle_mib * 1024 * 1024
    grouped: dict[str, list[dict]] = defaultdict(list)
    for asset in assets:
        grouped[asset["painting_id"]].append(asset)
    bundles = {}
    painting_indexes = {}
    for painting, group in sorted(grouped.items()):
        for part_number, part in enumerate(split_by_size(group, max_bytes), 1):
            remote_path = f"{prefix}/bundles/{painting}/part-{part_number:04d}.zip"
            local_path = stage / "bundles" / painting / f"part-{part_number:04d}.zip"
            metadata = build_bundle(part, ROOT, local_path, max_bytes)
            bundles[remote_path] = {key: metadata[key] for key in
                                    ("size_bytes", "sha256", "member_count")}
            for asset in part:
                asset["bundle_path"] = remote_path
                asset["member_path"] = asset["original_relative_path"]
            print(f"Built {painting} part {part_number}: {metadata['size_bytes']:,} B, "
                  f"{len(part)} members", flush=True)
    if len(bundles) > MAX_SMOKE_BUNDLES:
        raise ValueError("Smoke selection exceeds four bundles")
    total_bundle_bytes = sum(row["size_bytes"] for row in bundles.values())
    if total_bundle_bytes > MAX_SMOKE_BUNDLE_BYTES:
        raise ValueError("Smoke selection exceeds 128 MiB")
    for painting, group in sorted(grouped.items()):
        remote_path = f"{prefix}/indexes/paintings/{painting}.json"
        payload = {"schema_version": SCHEMA, "painting_id": painting,
                   "assets": sorted(group, key=lambda x: x["asset_id"])}
        content = json_bytes(payload)
        local = stage / "indexes" / "paintings" / f"{painting}.json"
        local.parent.mkdir(parents=True, exist_ok=True)
        if local.exists() and local.read_bytes() != content:
            raise ValueError(f"Immutable painting index differs: {local}")
        local.write_bytes(content)
        painting_indexes[painting] = {"path": remote_path,
                                      "size_bytes": len(content),
                                      "sha256": sha256_bytes(content)}
    catalogue = {
        "schema_version": SCHEMA,
        "kind": "n16_bounded_smoke_not_production",
        "repo_id": REPO, "prefix": prefix, "test_id": test_id,
        "source_run_id": run["run_id"], "source_manifest_sha256": manifest_hash,
        "producer": run["notebook_name"], "asset_count": len(assets),
        "bundles": bundles, "paintings": painting_indexes,
        "bundle_cap_bytes": max_bytes,
    }
    atomic_json(stage / "indexes" / "catalogue.json", catalogue)
    atomic_json(stage / "indexes" / "bundles.json",
                {"schema_version": SCHEMA, "bundles": bundles})
    # A local-only record tracks pinning; it is not uploaded into its own commit.
    record = {"schema_version": SCHEMA, "stage": str(stage), "repo_id": REPO,
              "prefix": prefix, "test_id": test_id,
              "source_manifest_sha256": manifest_hash,
              "source_run_id": run["run_id"], "asset_count": len(assets),
              "bundle_count": len(bundles), "bundle_bytes": total_bundle_bytes,
              "revision": None, "status": "prepared_not_uploaded"}
    record_path = stage / "publication_record.json"
    if record_path.exists():
        old = json.loads(record_path.read_text(encoding="utf-8"))
        for key in ("source_manifest_sha256", "source_run_id", "test_id"):
            if old[key] != record[key]:
                raise ValueError("Existing staging record has a different source/config")
        record["revision"] = old.get("revision")
        record["status"] = old.get("status", record["status"])
    atomic_json(record_path, record)
    verify_local(stage)
    if sha256_file(MANIFEST) != manifest_hash:
        raise ValueError("Producer manifest changed during smoke packaging")
    print(json.dumps(record, indent=2), flush=True)


def _catalogue(stage: Path) -> dict:
    payload = json.loads((stage / "indexes" / "catalogue.json").read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA or payload.get("kind") != "n16_bounded_smoke_not_production":
        raise ValueError("This CLI accepts only the N16 smoke catalogue")
    return payload


def _files(stage: Path, catalogue: dict) -> dict[str, Path]:
    prefix = catalogue["prefix"]
    result = {}
    for path in stage.rglob("*"):
        if path.is_file() and path.name not in ("publication_record.json",) and not path.name.endswith(".tmp"):
            if path.relative_to(stage).parts[0] not in ("bundles", "indexes", "tables", "data", "provenance", "figures"):
                continue
            result[f"{prefix}/{path.relative_to(stage).as_posix()}"] = path
    return result


def verify_local(stage: Path) -> None:
    catalogue = _catalogue(stage)
    seen = set()
    asset_count = 0
    for painting, entry in catalogue["paintings"].items():
        local = stage / Path(entry["path"]).relative_to(catalogue["prefix"])
        if local.stat().st_size != entry["size_bytes"] or sha256_file(local) != entry["sha256"]:
            raise ValueError(f"Painting index differs: {painting}")
        painting_index = json.loads(local.read_text(encoding="utf-8"))
        for asset in painting_index["assets"]:
            if asset["asset_id"] in seen:
                raise ValueError("Duplicate asset ID")
            seen.add(asset["asset_id"])
            verify_source(asset, ROOT)
            asset_count += 1
    for remote_path, metadata in catalogue["bundles"].items():
        local = stage / Path(remote_path).relative_to(catalogue["prefix"])
        if local.stat().st_size != metadata["size_bytes"] or sha256_file(local) != metadata["sha256"]:
            raise ValueError(f"Bundle file differs: {remote_path}")
        members = []
        for entry in catalogue["paintings"].values():
            index_path = stage / Path(entry["path"]).relative_to(catalogue["prefix"])
            members.extend(row for row in json.loads(index_path.read_text(encoding="utf-8"))["assets"]
                           if row["bundle_path"] == remote_path)
        verify_bundle(local, members)
    if asset_count != catalogue["asset_count"] or len(seen) != asset_count:
        raise ValueError("Catalogue coverage count differs")
    if len(catalogue["bundles"]) > MAX_SMOKE_BUNDLES:
        raise ValueError("Too many smoke bundles")
    if sum(x["size_bytes"] for x in catalogue["bundles"].values()) > MAX_SMOKE_BUNDLE_BYTES:
        raise ValueError("Smoke bundles exceed byte cap")
    print(f"Local smoke package verified: {asset_count} assets, "
          f"{len(catalogue['bundles'])} bundles, "
          f"{len(_files(stage, catalogue))} remote objects", flush=True)


def _public_bytes(repo: str, revision: str, path: str) -> bytes:
    from urllib.parse import quote
    encoded = "/".join(quote(part, safe="") for part in safe_relative(path).split("/"))
    url = f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{encoded}"
    request = urllib.request.Request(url, headers={"User-Agent": "painting-eval-bundle-smoke/1"})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def _remote_paths(api, prefix: str, revision: str = "main") -> set[str]:
    try:
        return {entry.path for entry in api.list_repo_tree(
            repo_id=REPO, path_in_repo=prefix, recursive=True,
            repo_type="dataset", revision=revision,
        ) if hasattr(entry, "size")}
    except Exception as exc:
        # A not-yet-existing prefix is expected; other errors must remain visible.
        response = getattr(exc, "response", None)
        if getattr(response, "status_code", None) in (400, 404):
            return set()
        raise


def _classify(exc: Exception) -> tuple[str, float]:
    if isinstance(exc, (ValueError, TypeError, PermissionError)):
        return "permanent", 0.0
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if status == 429:
        headers = response.headers
        retry = headers.get("Retry-After") or headers.get("ratelimit-reset") or "300"
        try:
            wait = min(600.0, max(1.0, float(retry)))
        except ValueError:
            wait = 300.0
        return "rate_limit", wait
    if status in (500, 502, 503, 504):
        return "transient", 15.0
    if status in (401, 402, 403, 413):
        return "permanent", 0.0
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return "ambiguous", 15.0
    if status is None:
        return "ambiguous", 15.0
    return "permanent", 0.0


def upload(args: argparse.Namespace) -> None:
    if args.confirm != "UPLOAD_N16_SMOKE_ONLY":
        raise ValueError("Explicit --confirm UPLOAD_N16_SMOKE_ONLY is required")
    stage = _stage(args)
    verify_local(stage)
    catalogue = _catalogue(stage)
    expected = _files(stage, catalogue)
    from huggingface_hub import CommitOperationAdd, HfApi

    api = HfApi()
    identity = api.whoami()
    print(f"Authenticated Hub account: {identity.get('name', '(unknown)')}", flush=True)
    # The test prefix is immutable: existing names are accepted only if bytes match.
    started = time.monotonic()
    for attempt in range(1, 5):
        present = _remote_paths(api, catalogue["prefix"])
        unexpected = present - set(expected)
        if unexpected:
            raise ValueError(f"Unexpected files in immutable smoke prefix: {sorted(unexpected)}")
        for path in sorted(present):
            remote = _public_bytes(REPO, "main", path)
            if len(remote) != expected[path].stat().st_size or sha256_bytes(remote) != sha256_file(expected[path]):
                raise ValueError(f"Existing remote object differs: {path}")
        missing = [path for path in sorted(expected) if path not in present]
        print(f"Upload pass {attempt}: verified existing {len(present)}, "
              f"remaining {len(missing)}, elapsed {time.monotonic()-started:.1f}s", flush=True)
        if not missing:
            revision = api.repo_info(REPO, repo_type="dataset").sha
            break
        # Smoke package is at most four bundles + compact indexes; one modest commit.
        operations = [CommitOperationAdd(path_in_repo=path, path_or_fileobj=str(expected[path]))
                      for path in missing]
        try:
            result = api.create_commit(
                repo_id=REPO, repo_type="dataset", revision="main",
                operations=operations, commit_message=f"N16 bounded bundle smoke {catalogue['test_id']}",
                num_threads=1,
            )
            revision = result.oid
            print(f"Commit accepted: {revision}", flush=True)
            accepted = _remote_paths(api, catalogue["prefix"], revision)
            if set(expected) - accepted:
                raise RuntimeError("Commit returned but some smoke objects are not visible")
            break
        except Exception as exc:
            kind, delay = _classify(exc)
            print(f"Upload attempt {attempt} {kind}: {type(exc).__name__}; "
                  "checking remote state before any retry", flush=True)
            if kind == "permanent" or attempt == 4:
                raise
            time.sleep(delay + random.uniform(0, 2))
            continue
    else:
        raise RuntimeError("Upload retry budget exhausted")
    record_path = stage / "publication_record.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record.update({"revision": revision, "status": "upload_accepted_remote_verification_pending"})
    atomic_json(record_path, record)
    print(f"Pinned revision: {revision}; next run verify-remote", flush=True)


def verify_remote(args: argparse.Namespace) -> None:
    stage = _stage(args)
    catalogue = _catalogue(stage)
    record_path = stage / "publication_record.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    revision = record.get("revision")
    if not revision:
        raise ValueError("No pinned revision; run upload-smoke first")
    expected = _files(stage, catalogue)
    from huggingface_hub import HfApi
    visible = _remote_paths(HfApi(), catalogue["prefix"], revision)
    if visible != set(expected):
        raise ValueError(f"Pinned remote object set differs: missing={sorted(set(expected)-visible)}, "
                         f"unexpected={sorted(visible-set(expected))}")
    total = 0
    started = time.monotonic()
    for number, (path, local) in enumerate(sorted(expected.items()), 1):
        data = _public_bytes(REPO, revision, path)
        if len(data) != local.stat().st_size or sha256_bytes(data) != sha256_file(local):
            raise ValueError(f"Remote object SHA-256/size differs: {path}")
        total += len(data)
        print(f"Public SHA-256 {number}/{len(expected)}: {path} "
              f"({len(data):,} B)", flush=True)
    record.update({"status": "smoke_remote_objects_verified", "remote_verified_objects": len(expected),
                   "remote_verified_bytes": total, "verification_seconds": round(time.monotonic()-started, 2)})
    atomic_json(record_path, record)
    print(f"Remote verification complete at {revision}: {len(expected)} objects, "
          f"{total:,} bytes. Run smoke-read next.", flush=True)


def smoke_read(args: argparse.Namespace) -> None:
    from PIL import Image
    stage = _stage(args)
    record_path = stage / "publication_record.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if record.get("status") not in ("smoke_remote_objects_verified", "smoke_reader_verified"):
        raise ValueError("Run verify-remote before smoke-read")
    catalogue = _catalogue(stage)
    cache = Path(args.cache_dir).resolve()
    if any(cache.iterdir()) if cache.exists() else False:
        raise ValueError("Use a fresh empty cache directory for the cold-read test")
    reader = RemoteBundleReader(REPO, record["revision"], catalogue["prefix"], cache)
    started = time.monotonic()
    count = 0
    for painting, entry in sorted(catalogue["paintings"].items()):
        local_index = stage / Path(entry["path"]).relative_to(catalogue["prefix"])
        assets = json.loads(local_index.read_text(encoding="utf-8"))["assets"]
        for asset in assets:
            data, remote_row = reader.read_asset(painting, asset["asset_id"])
            if sha256_bytes(data) != asset["sha256"] or data != verify_source(asset, ROOT).read_bytes():
                raise ValueError(f"Remote member differs from source: {asset['asset_id']}")
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                if (image.width, image.height, image.mode) != (
                    asset["width"], asset["height"], asset["image_mode"]
                ):
                    raise ValueError(f"Decoded image geometry/mode differs: {asset['asset_id']}")
            count += 1
        print(f"Public reader {painting}: {len(assets)} exact images", flush=True)
    cold_seconds = time.monotonic() - started
    # Warm access to a second image in the same bundle must not re-download it.
    painting = sorted(catalogue["paintings"])[0]
    index = reader.painting(painting, reader.catalogue())
    before = reader.download_count
    warm_start = time.monotonic()
    reader.read_asset(painting, index["assets"][1]["asset_id"])
    warm_seconds = time.monotonic() - warm_start
    if reader.download_count != before:
        raise ValueError("Warm read unexpectedly downloaded a bundle")
    record.update({"status": "smoke_reader_verified", "public_read_assets": count,
                   "cold_read_seconds": round(cold_seconds, 3),
                   "warm_read_seconds": round(warm_seconds, 3),
                   "downloaded_objects": reader.download_count,
                   "downloaded_bytes": reader.download_bytes,
                   "cache_bytes": sum(p.stat().st_size for p in cache.iterdir() if p.is_file())})
    atomic_json(record_path, record)
    inventory = ROOT / "outputs/inventory/bundled_publication_n16_smoke.json"
    atomic_json(inventory, record)
    print(json.dumps(record, indent=2), flush=True)
    print(f"Compact smoke record: {inventory}", flush=True)


def inspect(args: argparse.Namespace) -> None:
    stage = _stage(args)
    catalogue = _catalogue(stage)
    painting = args.painting_id or sorted(catalogue["paintings"])[0]
    entry = catalogue["paintings"][painting]
    index = json.loads((stage / Path(entry["path"]).relative_to(catalogue["prefix"])).read_text(encoding="utf-8"))
    matches = [row for row in index["assets"] if not args.asset_id or row["asset_id"] == args.asset_id]
    print(json.dumps(matches[:5], indent=2), flush=True)


def _full_context(max_bundle_bytes: int = MAX_BUNDLE_BYTES) -> dict:
    spec = _full_spec()
    producer_root = ROOT / "outputs" / spec["name"]
    manifest = producer_root / "manifests" / spec.get(
        "manifest_file", "map_images.csv"
    )
    run_manifest = producer_root / "manifests/run_manifest.json"
    manifest_rows = _rows(manifest)
    if any(row["status"] != "passed" for row in manifest_rows):
        raise ValueError(f"N{FULL_NOTEBOOK} map manifest contains non-passed images")
    if FULL_NOTEBOOK in ("19", "20"):
        # N19 registers repeated/upstream paths and N20 registers repeated NPZ
        # paths. Only producer-owned PNGs are original bundle members.
        rows = [row for row in manifest_rows
                if row["ownership"] == "owned" and row["format"] == "PNG"]
    else:
        rows = manifest_rows
    assets = [_asset(row) for row in rows]
    paths = [row["original_relative_path"] for row in assets]
    if len(paths) != len(set(paths)):
        raise ValueError(f"N{FULL_NOTEBOOK} map manifest contains duplicate image paths")
    run = json.loads(run_manifest.read_text(encoding="utf-8"))
    if run.get("run_status") != "completed" or run.get("completion_gate_passed") is not True:
        raise ValueError(f"N{FULL_NOTEBOOK} completion gate did not pass")
    if run.get("notebook_name") != spec["name"]:
        raise ValueError("Producer run manifest does not match the selected notebook")
    if FULL_NOTEBOOK == "19":
        expected = run["expected_counts"]
        expected_images = sum(int(expected[key]) for key in (
            "uncertainty_panels", "overlay_panels",
            "owned_scratch_aware_local_component_maps", "selected_panels"))
        if len(assets) != expected_images:
            raise ValueError("N19 owned image coverage differs from the run contract")
    if FULL_NOTEBOOK == "20":
        expected_images = int(run["expected_counts"]["rendered_semantic_panels"])
        if len(assets) != expected_images:
            raise ValueError("N20 owned image coverage differs from the run contract")
    metrics = producer_root / "metrics" / spec["metric_file"]
    artifact_manifest = producer_root / "manifests/artifacts.csv"
    with artifact_manifest.open("r", encoding="utf-8-sig", newline="") as stream:
        artifact_rows = {row["artifact_key"]: row for row in csv.DictReader(stream)}
    if any(
        row.get("dataset_scope") != "controlled_300"
        for row in artifact_rows.values()
    ):
        raise ValueError(
            f"N{FULL_NOTEBOOK} artifact manifest is not labelled controlled_300"
        )
    manifest_sha = sha256_file(manifest)
    metrics_sha = sha256_file(metrics)
    for key, actual in ((spec["map_key"], manifest_sha),
                        (spec["metric_key"], metrics_sha)):
        if artifact_rows[key]["checksum"] != actual or artifact_rows[key]["validation_status"] != "passed":
            raise ValueError(f"N{FULL_NOTEBOOK} artifact-manifest checksum/status mismatch: {key}")
    numeric_maps = None
    if spec.get("numeric_file"):
        numeric_maps = producer_root / "data" / spec["numeric_file"]
        archive_record = artifact_rows[spec["numeric_key"]]
        if (archive_record["checksum"] != sha256_file(numeric_maps)
                or archive_record["validation_status"] != "passed"):
            raise ValueError(
                f"N{FULL_NOTEBOOK} numeric-map archive checksum/status mismatch"
            )
    if FULL_NOTEBOOK == "17":
        summary = producer_root / "figures/local_consistency_summary.png"
        summary_record = artifact_rows["local_consistency.summary_figure"]
        if (summary_record["checksum"] != sha256_file(summary)
                or summary_record["validation_status"] != "passed"):
            raise ValueError("N17 summary-figure artifact checksum/status mismatch")
    grouped: dict[str, list[dict]] = defaultdict(list)
    for asset in assets:
        grouped[asset["painting_id"]].append(asset)
    if not all(grouped):
        raise ValueError(f"N{FULL_NOTEBOOK} painting group missing")
    payload = {"schema_version": SCHEMA, "producer": run["notebook_name"],
               "source_run_id": run["run_id"], "source_manifest_sha256": manifest_sha,
               "metrics_sha256": metrics_sha, "max_bundle_bytes": max_bundle_bytes}
    release_id = sha256_bytes(json_bytes(payload))[:16]
    prefix = f"bundled_assets/v1/controlled_300/{run['notebook_name']}/{release_id}"
    return {"assets": assets, "groups": grouped, "run": run,
            "producer_root": producer_root, "manifest": manifest,
            "metrics": metrics, "manifest_sha": manifest_sha,
            "metrics_sha": metrics_sha, "numeric_maps": numeric_maps,
            "release_id": release_id,
            "prefix": prefix, "max_bundle_bytes": max_bundle_bytes}


def plan_full(args: argparse.Namespace) -> None:
    context = _full_context()
    parts = sum(len(split_by_size(group, context["max_bundle_bytes"]))
                for group in context["groups"].values())
    original_bytes = sum(row["size_bytes"] for row in context["assets"])
    print(json.dumps({
        "producer": context["run"]["notebook_name"],
        "release_id": context["release_id"], "prefix": context["prefix"],
        "original_image_assets": len(context["assets"]),
        "paintings": len(context["groups"]),
        "planned_bundle_count_conservative": parts,
        "original_image_bytes": original_bytes,
        "large_metric_table_bytes": context["metrics"].stat().st_size,
        "numeric_archive_bytes": (context["numeric_maps"].stat().st_size
                                  if context["numeric_maps"] else 0),
        "bundle_cap_bytes": context["max_bundle_bytes"],
        "note": "Planning reads manifests/hashes only; exact ZIP bytes are measured by prepare-full",
    }, indent=2), flush=True)


def _write_immutable(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"Immutable staged index differs: {path}")
        return
    temp = path.with_name(path.name + ".tmp")
    try:
        temp.write_bytes(content)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _copy_immutable(source: Path, destination: Path) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    expected = sha256_file(source)
    if destination.exists():
        if destination.stat().st_size != source.stat().st_size or sha256_file(destination) != expected:
            raise ValueError(f"Immutable staged table/provenance differs: {destination}")
    else:
        temp = destination.with_name(destination.name + ".tmp")
        try:
            shutil.copyfile(source, temp)
            if sha256_file(temp) != expected:
                raise ValueError(f"Staged copy differs from producer: {source}")
            os.replace(temp, destination)
        finally:
            temp.unlink(missing_ok=True)
    return {"size_bytes": destination.stat().st_size, "sha256": expected}


def prepare_full(args: argparse.Namespace) -> None:
    stage = _stage(args)
    context = _full_context()
    spec = _full_spec()
    prior_path = stage / "publication_record.json"
    if prior_path.exists():
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        if prior.get("release_id") != context["release_id"]:
            raise ValueError("Existing full-release staging belongs to another immutable release")
    prefix = context["prefix"]
    bundles: dict[str, dict] = {}
    painting_indexes: dict[str, dict] = {}
    all_assets: list[dict] = []
    total_parts = sum(len(split_by_size(group, context["max_bundle_bytes"]))
                      for group in context["groups"].values())
    completed = 0
    newly_built = 0
    started = time.monotonic()
    for painting, group in sorted(context["groups"].items()):
        for part_number, part in enumerate(split_by_size(group, context["max_bundle_bytes"]), 1):
            remote_path = f"{prefix}/bundles/{painting}/part-{part_number:04d}.zip"
            local = stage / "bundles" / painting / f"part-{part_number:04d}.zip"
            reused = local.exists()
            metadata = build_bundle(part, ROOT, local, context["max_bundle_bytes"])
            if not reused:
                newly_built += 1
            bundles[remote_path] = {key: metadata[key] for key in
                                    ("size_bytes", "sha256", "member_count")}
            for asset in part:
                asset["bundle_path"] = remote_path
                asset["member_path"] = asset["original_relative_path"]
            completed += 1
            if completed % 10 == 0 or completed == total_parts:
                elapsed = time.monotonic() - started
                eta = elapsed / newly_built * (total_parts - completed) if newly_built else float("nan")
                print(f"Bundle {completed}/{total_parts}; elapsed {elapsed/60:.1f} min; "
                      f"new {newly_built}; measured ETA {eta/60:.1f} min", flush=True)
        all_assets.extend(group)
        index_path = f"{prefix}/indexes/paintings/{painting}.json"
        content = json_bytes({"schema_version": SCHEMA, "painting_id": painting,
                              "assets": sorted(group, key=lambda row: row["asset_id"])})
        local_index = stage / "indexes" / "paintings" / f"{painting}.json"
        _write_immutable(local_index, content)
        painting_indexes[painting] = {"path": index_path,
                                      "size_bytes": len(content),
                                      "sha256": sha256_bytes(content)}
    if len(all_assets) != len(context["assets"]) or len({x["asset_id"] for x in all_assets}) != len(all_assets):
        raise ValueError(f"N{FULL_NOTEBOOK} asset coverage or uniqueness failed")
    _write_immutable(stage / "indexes" / "bundles.json",
                     json_bytes({"schema_version": SCHEMA, "bundles": bundles}))
    # Complete flat membership ledger supplements the partitioned painting indexes.
    ledger = stage / "indexes" / "members.csv"
    fields = ("asset_id", "painting_id", "case_id", "candidate_id", "model_id",
              "map_type", "asset_kind", "original_relative_path", "bundle_path",
              "member_path", "sha256", "size_bytes", "width", "height", "image_mode")
    ledger_temp = ledger.with_name(ledger.name + ".tmp")
    with ledger_temp.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for asset in sorted(all_assets, key=lambda row: row["asset_id"]):
            writer.writerow({field: asset.get(field, "") for field in fields})
    if ledger.exists():
        if sha256_file(ledger) != sha256_file(ledger_temp):
            raise ValueError("Immutable membership ledger differs")
        ledger_temp.unlink()
    else:
        os.replace(ledger_temp, ledger)
    ledgers = {f"{prefix}/indexes/members.csv":
               {"size_bytes": ledger.stat().st_size, "sha256": sha256_file(ledger)}}
    source_files = {
        f"tables/{spec['metric_file']}": context["metrics"],
        f"tables/{spec.get('manifest_file', 'map_images.csv')}": context["manifest"],
        "provenance/artifacts.csv": context["producer_root"] / "manifests/artifacts.csv",
        "provenance/run_manifest.json": context["producer_root"] / "manifests/run_manifest.json",
        "provenance/checks.csv": context["producer_root"] / "validation/checks.csv",
    }
    if FULL_NOTEBOOK == "17":
        source_files["figures/local_consistency_summary.png"] = (
            context["producer_root"] / "figures/local_consistency_summary.png"
        )
    if spec.get("numeric_file"):
        source_files[f"data/{spec['numeric_file']}"] = context["numeric_maps"]
    if spec.get("figure_file"):
        figure = context["producer_root"] / "figures" / spec["figure_file"]
        artifact_rows = None
        with (context["producer_root"] / "manifests/artifacts.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as stream:
            artifact_rows = {row["artifact_key"]: row for row in csv.DictReader(stream)}
        record = artifact_rows[spec["figure_key"]]
        if (record["checksum"] != sha256_file(figure)
                or record["validation_status"] != "passed"):
            raise ValueError(
                f"N{FULL_NOTEBOOK} figure checksum/status mismatch"
            )
        source_files[f"figures/{spec['figure_file']}"] = figure
    additional = {}
    for relative, source in source_files.items():
        metadata = _copy_immutable(source, stage / relative)
        additional[f"{prefix}/{relative}"] = metadata
    catalogue = {
        "schema_version": SCHEMA, "kind": spec["kind"],
        "repo_id": REPO, "prefix": prefix, "release_id": context["release_id"],
        "producer": context["run"]["notebook_name"],
        "source_run_id": context["run"]["run_id"],
        "source_manifest_sha256": context["manifest_sha"],
        "asset_count": len(all_assets), "bundle_cap_bytes": context["max_bundle_bytes"],
        "bundles": bundles, "paintings": painting_indexes,
        "other_objects": {**ledgers, **additional},
    }
    _write_immutable(stage / "indexes" / "catalogue.json", json_bytes(catalogue))
    record = {"schema_version": SCHEMA, "producer": catalogue["producer"],
              "repo_id": REPO, "prefix": prefix, "release_id": context["release_id"],
              "source_run_id": catalogue["source_run_id"],
              "source_manifest_sha256": catalogue["source_manifest_sha256"],
              "asset_count": len(all_assets), "bundle_count": len(bundles),
              "bundle_bytes": sum(item["size_bytes"] for item in bundles.values()),
              "object_count": len(_files(stage, catalogue)),
              "status": "prepared_not_uploaded", "revision": None}
    if prior_path.exists():
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        record.update({key: prior[key] for key in ("status", "revision", "uploaded_object_count")
                       if key in prior})
    atomic_json(prior_path, record)
    if sha256_file(context["manifest"]) != context["manifest_sha"] or sha256_file(context["metrics"]) != context["metrics_sha"]:
        raise ValueError(f"N{FULL_NOTEBOOK} producer changed during packaging")
    verify_full_local(stage, deep=False)
    print(json.dumps(record, indent=2), flush=True)


def _full_catalogue(stage: Path) -> dict:
    payload = json.loads((stage / "indexes" / "catalogue.json").read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA or payload.get("kind") != _full_spec()["kind"]:
        raise ValueError(f"Not a prepared full-N{FULL_NOTEBOOK} catalogue")
    return payload


def verify_full_local(stage: Path, deep: bool = True) -> None:
    catalogue = _full_catalogue(stage)
    spec = _full_spec()
    manifest = (
        ROOT
        / "outputs"
        / spec["name"]
        / "manifests"
        / spec.get("manifest_file", "map_images.csv")
    )
    if sha256_file(manifest) != catalogue["source_manifest_sha256"]:
        raise ValueError(f"N{FULL_NOTEBOOK} source manifest changed after packaging")
    seen_ids: set[str] = set()
    member_groups: dict[str, list[dict]] = defaultdict(list)
    for painting, entry in catalogue["paintings"].items():
        local = stage / Path(entry["path"]).relative_to(catalogue["prefix"])
        if local.stat().st_size != entry["size_bytes"] or sha256_file(local) != entry["sha256"]:
            raise ValueError(f"Full-release painting index differs: {painting}")
        index = json.loads(local.read_text(encoding="utf-8"))
        for asset in index["assets"]:
            if asset["asset_id"] in seen_ids or asset["painting_id"] != painting:
                raise ValueError("Duplicate or misgrouped bundle asset")
            if deep:
                verify_source(asset, ROOT)
            seen_ids.add(asset["asset_id"])
            member_groups[asset["bundle_path"]].append(asset)
    if len(seen_ids) != catalogue["asset_count"] or set(member_groups) != set(catalogue["bundles"]):
        raise ValueError("Full-release asset coverage differs")
    for number, (remote_path, metadata) in enumerate(sorted(catalogue["bundles"].items()), 1):
        local = stage / Path(remote_path).relative_to(catalogue["prefix"])
        if local.stat().st_size != metadata["size_bytes"] or sha256_file(local) != metadata["sha256"]:
            raise ValueError(f"Full-release bundle SHA-256/size differs: {remote_path}")
        if metadata["member_count"] != len(member_groups[remote_path]):
            raise ValueError(f"Full-release bundle member count differs: {remote_path}")
        if deep:
            verify_bundle(local, member_groups[remote_path])
        if number % 25 == 0 or number == len(catalogue["bundles"]):
            print(f"Local bundle check {number}/{len(catalogue['bundles'])}", flush=True)
    expected = _files(stage, catalogue)
    for remote_path, metadata in catalogue["other_objects"].items():
        local = expected[remote_path]
        if local.stat().st_size != metadata["size_bytes"] or sha256_file(local) != metadata["sha256"]:
            raise ValueError(f"Full-release table/index differs: {remote_path}")
    if catalogue["bundle_cap_bytes"] != MAX_BUNDLE_BYTES:
        raise ValueError("Unapproved bundle cap")
    print(f"Full N{FULL_NOTEBOOK} local package verified: {len(seen_ids):,} original images, "
          f"{len(catalogue['bundles'])} bundles, {len(expected)} remote objects; "
          f"deep_member_check={deep}", flush=True)


def _full_expected(stage: Path, catalogue: dict) -> dict[str, dict]:
    files = _files(stage, catalogue)
    expected = {**catalogue["bundles"], **catalogue["other_objects"]}
    expected.update({entry["path"]: {"size_bytes": entry["size_bytes"],
                                     "sha256": entry["sha256"]}
                     for entry in catalogue["paintings"].values()})
    for name in ("bundles.json", "catalogue.json"):
        remote = f"{catalogue['prefix']}/indexes/{name}"
        local = stage / "indexes" / name
        expected[remote] = {"size_bytes": local.stat().st_size,
                            "sha256": sha256_file(local)}
    if set(expected) != set(files):
        raise ValueError(f"Full-release staged object set differs: "
                         f"missing={sorted(set(expected)-set(files))}, "
                         f"extra={sorted(set(files)-set(expected))}")
    return expected


def _hub_read_retry(action, description: str):
    for attempt in range(1, 5):
        try:
            return action()
        except Exception as exc:
            kind, delay = _classify(exc)
            if kind == "permanent" or attempt == 4:
                raise
            print(f"{description}: {kind} on attempt {attempt}; "
                  f"waiting {delay:.0f}s before retry", flush=True)
            time.sleep(delay + random.uniform(0, 2))
    raise RuntimeError("Unreachable retry state")


def _full_remote_entries(api, prefix: str, revision: str = "main") -> dict:
    def read():
        try:
            return {entry.path: entry for entry in api.list_repo_tree(
                repo_id=REPO, path_in_repo=prefix, recursive=True,
                expand=True, repo_type="dataset", revision=revision,
            ) if hasattr(entry, "size")}
        except Exception as exc:
            response = getattr(exc, "response", None)
            if getattr(response, "status_code", None) == 404:
                return {}
            raise
    return _hub_read_retry(read, "HF remote listing")


def _check_remote_object(path: str, entry, metadata: dict, revision: str) -> str:
    if int(entry.size) != int(metadata["size_bytes"]):
        raise ValueError(f"Remote byte count differs: {path}")
    lfs = getattr(entry, "lfs", None)
    full_sha = getattr(lfs, "sha256", None)
    if full_sha:
        if full_sha != metadata["sha256"]:
            raise ValueError(f"Remote LFS full SHA-256 differs: {path}")
        return "lfs_sha256"
    # Git blob IDs are SHA-1, not content SHA-256. Read the small object.
    data = _hub_read_retry(lambda: _public_bytes(REPO, revision, path),
                           f"Public object {path}")
    if len(data) != metadata["size_bytes"] or sha256_bytes(data) != metadata["sha256"]:
        raise ValueError(f"Remote public-read SHA-256 differs: {path}")
    return "public_read_sha256"


def _full_upload_order(path: str) -> tuple[int, str]:
    if "/bundles/" in path:
        return (0, path)
    if "/tables/" in path:
        return (1, path)
    if "/data/" in path:
        return (1, path)
    if "/figures/" in path:
        return (1, path)
    if "/provenance/" in path:
        return (2, path)
    if "/indexes/paintings/" in path:
        return (3, path)
    if path.endswith("/indexes/members.csv"):
        return (4, path)
    if path.endswith("/indexes/bundles.json"):
        return (5, path)
    if path.endswith("/indexes/catalogue.json"):
        return (6, path)
    raise ValueError(f"Unexpected release object: {path}")


def upload_full(args: argparse.Namespace) -> None:
    expected_confirmation = f"UPLOAD_FULL_N{FULL_NOTEBOOK}"
    if args.confirm != expected_confirmation:
        raise ValueError(f"Explicit --confirm {expected_confirmation} is required")
    stage = _stage(args)
    verify_full_local(stage, deep=False)
    catalogue = _full_catalogue(stage)
    expected = _full_expected(stage, catalogue)
    local_files = _files(stage, catalogue)
    from huggingface_hub import CommitOperationAdd, HfApi

    api = HfApi()
    identity = _hub_read_retry(lambda: api.whoami(), "HF authentication")
    if identity.get("name") != "RahulMaddineni264":
        raise PermissionError("Authenticated HF account does not match approved owner")
    print(f"Authenticated Hub account: {identity['name']}", flush=True)
    head = _hub_read_retry(lambda: api.repo_info(REPO, repo_type="dataset").sha,
                           "HF repository head")
    present = _full_remote_entries(api, catalogue["prefix"], head)
    unexpected = set(present) - set(expected)
    if unexpected:
        raise ValueError(f"Unknown objects in immutable release: {sorted(unexpected)}")
    for number, path in enumerate(sorted(present), 1):
        _check_remote_object(path, present[path], expected[path], head)
        if number % 25 == 0 or number == len(present):
            print(f"Existing remote objects verified {number}/{len(present)}", flush=True)
    accepted = set(present)
    initial_bytes = sum(expected[path]["size_bytes"] for path in accepted)
    ordered = sorted((path for path in expected if path not in accepted), key=_full_upload_order)
    started = time.monotonic()
    total_bytes = sum(meta["size_bytes"] for meta in expected.values())
    record_path = stage / "publication_record.json"
    revision = head
    print(f"Full N{FULL_NOTEBOOK} pending: {len(ordered)}/{len(expected)} objects; "
          f"{total_bytes:,} total staged bytes", flush=True)
    for offset in range(0, len(ordered), args.batch_size):
        batch = ordered[offset:offset + args.batch_size]
        pending = list(batch)
        for attempt in range(1, 5):
            try:
                result = api.create_commit(
                    repo_id=REPO, repo_type="dataset", revision="main",
                    parent_commit=revision,
                    operations=[CommitOperationAdd(path_in_repo=path,
                                                   path_or_fileobj=str(local_files[path]))
                                for path in pending],
                    commit_message=f"N{FULL_NOTEBOOK} bundle release {catalogue['release_id']} "
                                   f"objects {offset+1}-{offset+len(batch)}",
                    num_threads=2,
                )
                revision = result.oid
                accepted.update(pending)
                break
            except Exception as exc:
                kind, delay = _classify(exc)
                print(f"Full-N{FULL_NOTEBOOK} commit {offset//args.batch_size+1} attempt {attempt}: "
                      f"{kind} ({type(exc).__name__}); checking remote state", flush=True)
                current = _hub_read_retry(lambda: api.repo_info(REPO, repo_type="dataset").sha,
                                          "HF repository head after uncertain commit")
                entries = _full_remote_entries(api, catalogue["prefix"], current)
                for path in batch:
                    if path in entries:
                        _check_remote_object(path, entries[path], expected[path], current)
                        accepted.add(path)
                pending = [path for path in batch if path not in accepted]
                revision = current
                if not pending:
                    print("Ambiguous commit was accepted; resuming without re-upload", flush=True)
                    break
                if kind == "permanent" or attempt == 4:
                    raise
                time.sleep(delay + random.uniform(0, 2))
        else:
            raise RuntimeError("Full-release commit retry budget exhausted")
        elapsed = max(time.monotonic() - started, 0.001)
        completed_bytes = sum(expected[path]["size_bytes"] for path in accepted)
        rate = max(0, completed_bytes - initial_bytes) / elapsed
        eta = (total_bytes - completed_bytes) / rate if rate else 0.0
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record.update({"status": "upload_in_progress", "revision": revision,
                       "uploaded_object_count": len(accepted),
                       "uploaded_bytes": completed_bytes})
        atomic_json(record_path, record)
        print(f"Full N{FULL_NOTEBOOK} uploaded/verified {len(accepted)}/{len(expected)} objects; "
              f"{completed_bytes/2**30:.2f}/{total_bytes/2**30:.2f} GiB; "
              f"elapsed {elapsed/60:.1f} min; measured ETA {eta/60:.1f} min", flush=True)
        if offset + len(batch) < len(ordered):
            time.sleep(args.pace_seconds)
    if len(accepted) != len(expected):
        raise ValueError("Full-release upload did not cover every expected object")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record.update({"status": "upload_accepted_remote_verification_pending",
                   "revision": revision, "uploaded_object_count": len(accepted),
                   "uploaded_bytes": total_bytes})
    atomic_json(record_path, record)
    print(f"Full N{FULL_NOTEBOOK} upload accepted at {revision}; now run verify-full-remote", flush=True)


def verify_full_remote(args: argparse.Namespace) -> None:
    from huggingface_hub import HfApi
    from PIL import Image

    stage = _stage(args)
    catalogue = _full_catalogue(stage)
    expected = _full_expected(stage, catalogue)
    record_path = stage / "publication_record.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    revision = record.get("revision")
    if not revision or record.get("status") not in (
        "upload_accepted_remote_verification_pending", "full_remote_verified"
    ):
        raise ValueError("A complete uploaded release with a pinned revision is required")
    api = HfApi()
    entries = _full_remote_entries(api, catalogue["prefix"], revision)
    if set(entries) != set(expected):
        raise ValueError(f"Pinned N{FULL_NOTEBOOK} remote object set differs: "
                         f"missing={len(set(expected)-set(entries))}, "
                         f"extra={len(set(entries)-set(expected))}")
    methods: dict[str, int] = defaultdict(int)
    started = time.monotonic()
    for number, path in enumerate(sorted(expected), 1):
        methods[_check_remote_object(path, entries[path], expected[path], revision)] += 1
        if number % 25 == 0 or number == len(expected):
            print(f"Pinned remote SHA-256/size {number}/{len(expected)}; "
                  f"elapsed {(time.monotonic()-started)/60:.1f} min", flush=True)
    cache = Path(args.cache_dir).resolve()
    if cache.exists() and any(cache.iterdir()):
        raise ValueError("Use a fresh empty sample cache for public-read verification")
    reader = RemoteBundleReader(REPO, revision, catalogue["prefix"], cache)
    samples = []
    for painting in ("p001", "p150", "p300"):
        if painting not in catalogue["paintings"]:
            raise ValueError(f"Missing representative painting {painting}")
        entry = catalogue["paintings"][painting]
        local = stage / Path(entry["path"]).relative_to(catalogue["prefix"])
        index = json.loads(local.read_text(encoding="utf-8"))
        samples.append((painting, index["assets"][0]))
    panel = next((asset for painting in sorted(catalogue["paintings"])
                  for asset in json.loads((stage / Path(catalogue["paintings"][painting]["path"])
                                           .relative_to(catalogue["prefix"])).read_text(encoding="utf-8"))["assets"]
                  if asset["asset_kind"] == "selected_panel"), None)
    if panel is None and FULL_NOTEBOOK == "20":
        painting = sorted(catalogue["paintings"])[0]
        local = stage / Path(catalogue["paintings"][painting]["path"]).relative_to(
            catalogue["prefix"]
        )
        panel = json.loads(local.read_text(encoding="utf-8"))["assets"][-1]
    if panel is None:
        raise ValueError("No fourth public sample exists in full release")
    samples.append((panel["painting_id"], panel))
    sample_started = time.monotonic()
    for painting, asset in samples:
        data, _ = reader.read_asset(painting, asset["asset_id"])
        if sha256_bytes(data) != asset["sha256"] or data != verify_source(asset, ROOT).read_bytes():
            raise ValueError(f"Public sample bytes differ: {asset['asset_id']}")
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            if (image.width, image.height, image.mode) != (
                asset["width"], asset["height"], asset["image_mode"]
            ):
                raise ValueError(f"Public sample geometry differs: {asset['asset_id']}")
        print(f"Public sample passed: {painting} {asset['asset_id']} {asset['map_type']}", flush=True)
    record.update({"status": "full_remote_verified", "remote_verified_object_count": len(expected),
                   "remote_verified_bytes": sum(meta["size_bytes"] for meta in expected.values()),
                   "remote_verification_methods": dict(methods),
                   "remote_verification_seconds": round(time.monotonic()-started, 2),
                   "public_sample_asset_count": len(samples),
                   "public_sample_seconds": round(time.monotonic()-sample_started, 2),
                   "public_sample_downloaded_bytes": reader.download_bytes,
                   "public_sample_downloaded_objects": reader.download_count})
    atomic_json(record_path, record)
    inventory = ROOT / "outputs/inventory" / f"bundled_publication_n{FULL_NOTEBOOK}_full.json"
    atomic_json(inventory, record)
    print(json.dumps(record, indent=2), flush=True)
    print(f"Full N{FULL_NOTEBOOK} release record: {inventory}", flush=True)


def main() -> None:
    global FULL_NOTEBOOK
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare-smoke", "verify-local", "upload-smoke", "verify-remote",
                 "smoke-read", "inspect", "plan-full", "prepare-full",
                 "verify-full-local", "upload-full", "verify-full-remote"):
        command = sub.add_parser(name)
        command.add_argument("--staging-dir", required=True)
        if name in ("plan-full", "prepare-full", "verify-full-local",
                    "upload-full", "verify-full-remote"):
            command.add_argument(
                "--notebook", choices=("16", "17", "19", "20"), default="16"
            )
        if name == "prepare-smoke":
            command.add_argument("--max-bundle-mib", type=int, default=32, choices=range(1, 33), metavar="1..32")
        if name == "upload-smoke":
            command.add_argument("--confirm", required=True)
        if name == "upload-full":
            command.add_argument("--confirm", required=True)
            command.add_argument("--batch-size", type=int, default=15,
                                 choices=range(1, 26), metavar="1..25")
            command.add_argument("--pace-seconds", type=float, default=3.0)
        if name == "verify-full-remote":
            command.add_argument("--cache-dir", required=True)
        if name == "smoke-read":
            command.add_argument("--cache-dir", required=True)
        if name == "inspect":
            command.add_argument("--painting-id")
            command.add_argument("--asset-id")
    args = parser.parse_args()
    if hasattr(args, "notebook"):
        FULL_NOTEBOOK = args.notebook
    stage = _stage(args)
    if args.command == "prepare-smoke":
        prepare(args)
    elif args.command == "verify-local":
        verify_local(stage)
    elif args.command == "upload-smoke":
        upload(args)
    elif args.command == "verify-remote":
        verify_remote(args)
    elif args.command == "smoke-read":
        smoke_read(args)
    elif args.command == "plan-full":
        plan_full(args)
    elif args.command == "prepare-full":
        prepare_full(args)
    elif args.command == "verify-full-local":
        verify_full_local(stage, deep=True)
    elif args.command == "upload-full":
        upload_full(args)
    elif args.command == "verify-full-remote":
        verify_full_remote(args)
    else:
        inspect(args)


if __name__ == "__main__":
    main()
