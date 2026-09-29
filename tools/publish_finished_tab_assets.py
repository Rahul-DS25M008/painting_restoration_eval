"""Assets-only checkpoint for rooms 1-3; never runs Git writes or notebooks.

Reuses byte-exact ZIP transport. HF writes are append-only to one content-addressed
prefix, in the existing diagnostics dataset. Receipts distinguish remote content
metadata verification from optional full public-download verification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from restoration_eval.bundled_assets import (  # noqa: E402
    SCHEMA, RemoteBundleReader, atomic_json, build_bundle, json_bytes,
    safe_relative, sha256_bytes, sha256_file, verify_bundle, verify_source,
)

REPO = "RahulMaddineni264/painting-restoration-eval-diagnostics"
STAGE = ROOT / ".codex_tmp/finished_tabs_01_03"
RECEIPT = "config/publication/finished_tabs_01_03_assets.json"
SMALL = tuple("streamlit_assets/" + name for name in (
    "rooms/exhibition_foyer_shell.webp", "rooms/study_design_shell.png",
    "rooms/metric_framework_shell.png", "ornaments/arrakis_desert.png",
    "ornaments/conservation_study.svg", "ornaments/dune_archive_cover.svg",
    "ornaments/ledger_botanical.svg", "evidence/study_design/p001_loss_large.png",
    "evidence/study_design/p001_loss_small.png", "evidence/study_design/p001_mixed_damage.png",
    "evidence/study_design/p001_scratch_thin.png", "evidence/study_design/p001_zero_control.png",
))
SUPPORT = (".gitignore", ".gitattributes", "tools/publish_finished_tab_assets.py",
           "tests/test_finished_tab_publication.py", "docs/finished_tabs_asset_checkpoint.md", RECEIPT)
BULK = "streamlit_assets/evidence/metric_framework"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def describe(path, root=ROOT):
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError(f"Escaped or linked source: {path}")
    return {"original_relative_path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}


def inventory(root=ROOT, painting_ids=None):
    expected = painting_ids or [f"p{i:03}" for i in range(1, 301)]
    folders = sorted(p.name for p in (root / BULK).iterdir())
    if folders != sorted(expected):
        raise ValueError("Expected exactly p001-p300, with no unexpected bulk entries")
    small = [describe(root / name, root) for name in SMALL]
    paintings = {}
    for number, pid in enumerate(expected, 1):
        folder = root / BULK / pid
        paths = sorted(folder.iterdir())
        if (len(paths) != 38 or sum(p.suffix == ".png" for p in paths) != 36
                or not all(p.is_file() for p in paths)
                or {p.name for p in paths if p.suffix != ".png"} != {"manifest.json", "numeric.npz"}):
            raise ValueError(f"Expected 36 PNGs, manifest.json, numeric.npz: {pid}")
        rows = [describe(p, root) for p in paths]
        by_path = {r["original_relative_path"]: r for r in rows}
        meta = read(folder / "manifest.json")
        if meta["painting_id"] != pid or meta["version"] != "metric_inspection.v1":
            raise ValueError(f"Wrong painting/schema: {pid}")
        if meta["numeric_sha256"] != by_path[f"{BULK}/{pid}/numeric.npz"]["sha256"]:
            raise ValueError(f"Numeric archive hash mismatch: {pid}")
        referenced = set()
        for item in [*meta["assets"].values(), *meta["regions"].values()]:
            row = by_path[item["path"]]
            if row["sha256"] != item["sha256"]:
                raise ValueError(f"Manifest hash mismatch: {item['path']}")
            referenced.add(item["path"])
        if referenced != {r["original_relative_path"] for r in rows if r["original_relative_path"].endswith(".png")}:
            raise ValueError(f"Unindexed PNG: {pid}")
        # Source evidence stays in its existing canonical publication, not this release.
        for item in meta["sources"].values():
            source = (root / safe_relative(item["path"])).resolve()
            if not source.is_relative_to(root.resolve()) or sha256_file(source) != item["sha256"]:
                raise ValueError(f"Canonical source mismatch: {item['path']}")
        paintings[pid] = rows
        if number % 25 == 0:
            print(f"Inventory verified: {number}/{len(expected)} paintings", flush=True)
    return {"git_assets": small, "paintings": paintings}


def prepare():
    assets = inventory()
    release = sha256_bytes(json_bytes(assets))[:24]
    prefix = f"dashboard_assets/v1/finished_tabs_01_03/{release}"
    stage = STAGE / release
    catalogue = {"schema_version": SCHEMA, "prefix": prefix,
                 "release_id": release, "paintings": {}, "bundles": {}}
    objects = {}

    def register(relative):
        row = describe(stage / relative, stage)
        objects[f"{prefix}/{relative}"] = {"local_path": relative,
                                            "sha256": row["sha256"], "size_bytes": row["size_bytes"]}
        return {"path": f"{prefix}/{relative}", "sha256": row["sha256"], "size_bytes": row["size_bytes"]}

    for number, (pid, rows) in enumerate(assets["paintings"].items(), 1):
        indexed = []
        for kind in ("display", "archive"):
            group = [r for r in rows if r["original_relative_path"].endswith(".npz") == (kind == "archive")]
            relative = f"bundles/{kind}/{pid}.zip"
            build_bundle(group, ROOT, stage / relative)
            bundle = register(relative)
            catalogue["bundles"][bundle["path"]] = bundle
            indexed.extend({**r, "asset_id": Path(r["original_relative_path"]).name,
                            "bundle_path": bundle["path"], "member_path": r["original_relative_path"],
                            "role": kind} for r in group)
        relative = f"indexes/paintings/{pid}.json"
        atomic_json(stage / relative, {"schema_version": SCHEMA, "painting_id": pid, "assets": indexed})
        catalogue["paintings"][pid] = register(relative)
        if number % 25 == 0:
            print(f"Bundles verified: {number}/300 paintings", flush=True)
    atomic_json(stage / "indexes/catalogue.json", catalogue)
    register("indexes/catalogue.json")
    plan = {"repo_id": REPO, "release_id": release, "prefix": prefix,
            "inventory": assets, "objects": objects}
    atomic_json(stage / "plan.json", plan)
    atomic_json(STAGE / "current.json", {"release_id": release})
    print(f"Prepared {release}: {len(objects)} HF objects, "
          f"{sum(r['size_bytes'] for r in objects.values()):,} bytes; 12 ordinary-Git assets.")


def load():
    release = read(STAGE / "current.json")["release_id"]
    if not re.fullmatch(r"[0-9a-f]{24}", release):
        raise ValueError("Invalid release ID")
    stage = STAGE / release
    plan = read(stage / "plan.json")
    expected = sha256_bytes(json_bytes(plan["inventory"]))[:24]
    if release != expected or plan["prefix"] != f"dashboard_assets/v1/finished_tabs_01_03/{release}" or plan["repo_id"] != REPO:
        raise ValueError("Release identity mismatch")
    for remote, row in plan["objects"].items():
        relative = safe_relative(row["local_path"])
        if remote != f"{plan['prefix']}/{relative}":
            raise ValueError("Remote path outside approved release")
        verify_source({**row, "original_relative_path": relative}, stage)
    return stage, plan


def verify_local():
    stage, plan = load()
    if inventory() != plan["inventory"]:
        raise ValueError("Local assets changed; prepare a new release")
    for pid, rows in plan["inventory"]["paintings"].items():
        for kind in ("display", "archive"):
            group = [r for r in rows if r["original_relative_path"].endswith(".npz") == (kind == "archive")]
            verify_bundle(stage / f"bundles/{kind}/{pid}.zip", group)
    count = sum(len(rows) for rows in plan["inventory"]["paintings"].values())
    print(f"PASS: all {count:,} bulk sources, ZIP members and 12 Git assets verified.", flush=True)
    return stage, plan


def remote_entries(api, prefix, revision):
    try:
        return {e.path: e for e in api.list_repo_tree(REPO, path_in_repo=prefix,
                    recursive=True, expand=False, repo_type="dataset", revision=revision) if hasattr(e, "size")}
    except Exception as exc:
        if getattr(getattr(exc, "response", None), "status_code", None) == 404:
            return {}
        raise


def check_existing(entry, local, row):
    if entry.size != row["size_bytes"]:
        raise ValueError(f"Remote size conflict: {entry.path}")
    lfs = getattr(entry, "lfs", None)
    full_sha = getattr(lfs, "sha256", None)
    if full_sha:
        matches = full_sha == row["sha256"]
    else:
        # HF's ordinary Git blobs use SHA-1 with the Git blob header, not plain SHA-1.
        data = local.read_bytes()
        blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        matches = blob == entry.blob_id
    if not matches:
        raise ValueError(f"Immutable remote object differs; refusing overwrite: {entry.path}")


def upload(confirm):
    if confirm != "UPLOAD_FINISHED_TABS_01_03":
        raise ValueError("Use --confirm UPLOAD_FINISHED_TABS_01_03")
    stage, plan = verify_local()
    from huggingface_hub import CommitOperationAdd, HfApi
    api = HfApi()
    if api.whoami().get("name") != "RahulMaddineni264":
        raise PermissionError("Wrong HF account; expected RahulMaddineni264")
    revision = api.repo_info(REPO, repo_type="dataset").sha
    entries = remote_entries(api, plan["prefix"], revision)
    if set(entries) - set(plan["objects"]):
        raise ValueError("Unexpected objects already present in this release")
    for path, entry in entries.items():
        row = plan["objects"][path]
        check_existing(entry, stage / row["local_path"], row)
    # Catalogue is uploaded last. Existing releases are never changed or removed.
    pending = sorted(set(plan["objects"]) - set(entries),
                     key=lambda p: (2 if p.endswith("/catalogue.json") else int("/indexes/" in p), p))
    for offset in range(0, len(pending), 15):
        batch = pending[offset:offset + 15]
        result = api.create_commit(REPO, repo_type="dataset", revision="main", parent_commit=revision,
            operations=[CommitOperationAdd(path_in_repo=p,
                path_or_fileobj=str(stage / plan["objects"][p]["local_path"])) for p in batch],
            commit_message=f"Finished tabs 01-03 assets {plan['release_id']} batch {offset // 15 + 1}",
            num_threads=2)
        revision = result.oid
        print(f"Uploaded {min(offset + 15, len(pending))}/{len(pending)} pending objects", flush=True)
        time.sleep(3)
    # If interrupted (including an ambiguous commit), rerun upload: it rechecks
    # the remote head and hashes, and sends only missing objects, never overwrites.
    atomic_json(stage / "uploaded.json", {"revision": revision, "release_id": plan["release_id"]})
    print(f"Upload complete, NOT YET VERIFIED: {revision}")


def retry_read(operation):
    """Bounded transient retries; never restart a whole completed download pass."""
    for attempt in range(3):
        try:
            return operation()
        except Exception as exc:
            response = getattr(exc, "response", None)
            status = getattr(response, "status_code", getattr(exc, "code", None))
            if status not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            headers = getattr(response, "headers", None) or getattr(exc, "headers", {}) or {}
            hint = headers.get("Retry-After", "")
            delay = int(hint) if str(hint).isdigit() else 2 ** (attempt + 1)
            if delay > 30:
                raise RuntimeError(f"Server requests {delay}s cooldown; rerun later, completed files remain cached") from exc
            print(f"Transient HTTP {status}; retrying only failed request in {delay}s", flush=True)
            time.sleep(delay)


def verify_remote(metadata_only=False):
    # load() verifies every staged object's SHA-256 against the prepared plan;
    # avoid repeating scientific/source audits already passed before upload.
    stage, plan = load() if metadata_only else verify_local()
    for row in plan["inventory"]["git_assets"]:
        verify_source(row, ROOT)
    state = read(stage / "uploaded.json")
    revision = state["revision"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision) or state["release_id"] != plan["release_id"]:
        raise ValueError("Missing immutable upload revision")
    from huggingface_hub import HfApi
    entries = retry_read(lambda: remote_entries(HfApi(token=False), plan["prefix"], revision))
    if set(entries) != set(plan["objects"]):
        raise ValueError("Remote release object set differs")
    for path, row in plan["objects"].items():
        check_existing(entries[path], stage / row["local_path"], row)
    if metadata_only:
        write_receipt(plan, revision, metadata_only=True)
        return
    cache = stage / "public_verification"
    cache.mkdir(exist_ok=True)
    reader = RemoteBundleReader(REPO, revision, plan["prefix"], cache / "indexed_reader")
    for number, (path, row) in enumerate(sorted(plan["objects"].items()), 1):
        check_existing(entries[path], stage / row["local_path"], row)
        target = cache / sha256_bytes(f"{revision}/{path}".encode())
        if not target.exists() or target.stat().st_size != row["size_bytes"] or sha256_file(target) != row["sha256"]:
            # This deliberately uses a public HTTP request, without auth or local fallback.
            retry_read(lambda: reader._public_fetch(reader._url(path), target))
        if target.stat().st_size != row["size_bytes"] or sha256_file(target) != row["sha256"]:
            raise ValueError(f"Public download SHA-256 mismatch: {path}")
        if number % 25 == 0 or number == len(plan["objects"]):
            print(f"Public bytes verified: {number}/{len(plan['objects'])}", flush=True)
    # Exercise the same indexed reader the future application can use.
    for pid in ("p001", "p018", "p055", "p300"):
        data, _ = retry_read(lambda: reader.read_asset(pid, "manifest.json"))
        if json.loads(data)["painting_id"] != pid:
            raise ValueError(f"Remote indexed read mismatch: {pid}")
    write_receipt(plan, revision, metadata_only=False)


def write_receipt(plan, revision, metadata_only):
    catalogue = plan["objects"][f"{plan['prefix']}/indexes/catalogue.json"]
    status = "remote_metadata_verified" if metadata_only else "public_bytes_verified"
    receipt = {"schema_version": "finished_tab_assets.v1", "status": status,
        "scope": ["exhibition_foyer", "study_design", "metric_framework"],
        "excludes": ["N35 notebook and outputs", "application code", "Streamlit deployment"],
        "verified_at_utc": datetime.now(timezone.utc).isoformat(), "repo_id": REPO,
        "revision": revision, "prefix": plan["prefix"], "release_id": plan["release_id"],
        "catalogue": {k: v for k, v in catalogue.items() if k != "local_path"},
        "object_count": len(plan["objects"]), "painting_count": len(plan["inventory"]["paintings"]),
        "source_file_count": sum(len(r) for r in plan["inventory"]["paintings"].values()),
        "transport_bytes": sum(r["size_bytes"] for r in plan["objects"].values()),
        "verification": ("Every staged object SHA-256 checked against the locally validated upload plan; "
            "every remote path, size and content identity matched using HF LFS SHA-256 or Git blob SHA-1"
            if metadata_only else "Every release object anonymously downloaded and SHA-256 checked; ZIP members checked locally"),
        "full_public_download_verification": "deferred_by_user" if metadata_only else "passed",
        "git_assets": plan["inventory"]["git_assets"],
        "note": "Asset checkpoint only; canonical producer publications unchanged; remote UI wiring deferred."}
    atomic_json(ROOT / RECEIPT, receipt)
    print(f"PASS: {status}; receipt written to {RECEIPT}")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def check_git():
    if git("branch", "--show-current").decode().strip() != "main":
        raise ValueError("Must be on main; no branch switching is performed")
    expected = set(SMALL + SUPPORT)
    actual = set(git("diff", "--cached", "--name-only", "-z").decode().strip("\0").split("\0"))
    if actual != expected:
        raise ValueError(f"Staged set differs. Extra: {sorted(actual-expected)}; missing: {sorted(expected-actual)}")
    receipt = read(ROOT / RECEIPT)
    if receipt["status"] not in ("public_bytes_verified", "remote_metadata_verified") or not re.fullmatch(r"[0-9a-f]{40}", receipt["revision"]):
        raise ValueError("No completed remote verification receipt")
    if receipt["status"] == "remote_metadata_verified" and receipt.get("full_public_download_verification") != "deferred_by_user":
        raise ValueError("Metadata-only checkpoint must disclose deferred public downloads")
    release = read(STAGE / "current.json")["release_id"]
    uploaded = read(STAGE / release / "uploaded.json")
    if (receipt["release_id"] != release or receipt["revision"] != uploaded["revision"]
            or receipt["repo_id"] != REPO or receipt["painting_count"] != 300
            or receipt["source_file_count"] != 11400 or receipt["object_count"] != 901
            or {r["original_relative_path"] for r in receipt["git_assets"]} != set(SMALL)):
        raise ValueError("Receipt does not match the current complete checkpoint")
    for path in sorted(expected):
        data = git("show", f":{path}")
        if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
            raise ValueError(f"Staged Git LFS pointer forbidden: {path}")
        attr = git("check-attr", "--cached", "filter", "--", path).decode().strip().rsplit(": ", 1)[-1]
        if attr not in ("unset", "unspecified"):
            raise ValueError(f"Git filter forbidden: {path}: {attr}")
        if len(data) > 10 * 1024 * 1024:
            raise ValueError(f"Unexpectedly large ordinary Git file: {path}")
    for row in receipt["git_assets"]:
        verify_source(row, ROOT)
        if sha256_bytes(git("show", ":" + row["original_relative_path"])) != row["sha256"]:
            raise ValueError("Staged artwork differs from verified receipt")
    if json.loads(git("show", ":" + RECEIPT)) != receipt:
        raise ValueError("Staged receipt differs from the verified receipt")
    print(f"PASS: exactly {len(expected)} allowed files staged, no LFS, no N35/app changes.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify-local", "upload", "verify-remote", "git-paths", "check-git"))
    parser.add_argument("--confirm")
    parser.add_argument("--metadata-only", action="store_true",
                        help="Verify all remote content hashes/sizes without downloading every object")
    args = parser.parse_args()
    if args.command == "upload":
        upload(args.confirm)
    elif args.command == "verify-remote":
        verify_remote(metadata_only=args.metadata_only)
    elif args.command == "git-paths":
        print("\n".join(SMALL + SUPPORT))
    else:
        {"prepare": prepare, "verify-local": verify_local,
         "verify-remote": verify_remote, "check-git": check_git}[args.command]()


if __name__ == "__main__":
    main()
