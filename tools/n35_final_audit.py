"""N35 deployment preflight. Read evidence; never publish or edit frozen inputs.

CLI receipts go only to ignored .codex_tmp/n35_batch10_audit. They are diagnostics,
not the four canonical N35 outputs, and cannot certify a hosted deployment.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import gzip
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / ".codex_tmp/n35_batch10_audit"
sys.path.insert(0, str(ROOT / "src"))
from restoration_eval.manifests import sha256_file, sha256_path, path_statistics


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def csv_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


@lru_cache(maxsize=250000)
def relative_path(value):
    value = str(value).replace("\\", "/")
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT) or Path(value).is_absolute():
        raise ValueError("Dependency outside repository")
    return path.relative_to(ROOT).as_posix()


def receipt(name, result):
    DEST.mkdir(parents=True, exist_ok=True)
    result = dict(result, checked_at_utc=datetime.now(timezone.utc).isoformat(),
                  git_commit=git("rev-parse", "HEAD").decode().strip(),
                  notebook_sha256=sha256_file(ROOT / "notebooks/35_dashboard_and_deployment_validation.ipynb"),
                  scope="read_only_preflight_not_deployment_certification")
    (DEST / name).write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return result


def n29_provenance():
    stem = "outputs/29_explainable_ai_and_case_retrieval"
    path = stem + "/manifests/artifacts.csv"
    run = read_json(ROOT / stem / "manifests/run_manifest.json")
    correction = "f1e4a460b64755c3ae945d8392e55ba3074bcfb6"
    original = git("rev-parse", "24fefec4").decode().strip()
    old_raw, corrected_raw = (git("show", revision + ":" + path) for revision in (original, correction))
    old, corrected = (list(csv.DictReader(io.StringIO(raw.decode()))) for raw in (old_raw, corrected_raw))
    current = csv_rows(ROOT / path)
    if len(old) != 6 or len(corrected) != 6 or corrected != current:
        raise ValueError("N29 history no longer matches the six recorded artifact rows")
    differences = []
    for a, b in zip(old, corrected):
        for key in a:
            if a[key] != b[key]:
                differences.append(dict(artifact_key=a["artifact_key"], field=key, before=a[key], after=b[key]))
    only_scope = len(differences) == 6 and all(
        r["field"] == "dataset_scope" and r["before"] == "controlled_50" and r["after"] == "controlled_300"
        for r in differences)
    artifacts = []
    for row in current:
        target = ROOT / relative_path(row["relative_path"])
        observed = sha256_path(target)
        stats = path_statistics(target)
        artifacts.append(dict(path=row["relative_path"], expected_sha256=row["checksum"],
            observed_sha256=observed, expected_bytes=int(row["size_bytes"]), **stats,
            passed=observed == row["checksum"] and stats["size_bytes"] == int(row["size_bytes"])
                   and stats["file_count"] == int(row["file_count"])))
    raw = (ROOT / path).read_bytes()
    lf = raw.replace(b"\r\n", b"\n")
    original_run = json.loads(git("show", original + ":" + stem + "/manifests/run_manifest.json"))
    return dict(recorded_run_id=run["run_id"], original_commit=original, correction_commit=correction,
        cause="Post-run dataset_scope metadata correction; corrected run records an unreproduced manifest checksum.",
        metadata_differences=differences, scope_only_correction=only_scope,
        artifact_checks=artifacts, all_payloads_match=all(r["passed"] for r in artifacts),
        original_checksum_matches_crlf=hashlib.sha256(old_raw.replace(b"\n", b"\r\n")).hexdigest() == original_run["artifact_manifest_checksum"],
        corrected_recorded_checksum=run["artifact_manifest_checksum"],
        current_raw_sha256=hashlib.sha256(raw).hexdigest(), current_lf_sha256=hashlib.sha256(lf).hexdigest(),
        current_checksum_matches_recorded=hashlib.sha256(raw).hexdigest() == run["artifact_manifest_checksum"],
        historical_inputs_modified=False,
        disposition="Evidence bytes checked independently. Historical checksum discrepancy remains explicit; a reviewed erratum is required, not a silent rewrite or blanket hash normalization.")


def dependency_inventory():
    """Enumerate saved selectors, layers, reports, and compact UI dependencies.

    Static/runtime loader analysis is separate: publication coverage does NOT
    prove that an application actually uses its remote transport.
    """
    from restoration_eval.dashboard_application import open_dashboard_package
    from restoration_eval import case_explorer as ce, research_archive as ar
    package = open_dashboard_package(ROOT)
    entries = {}

    def add(path, role, expected=None):
        path = relative_path(path)
        entry = entries.setdefault(path, {"path": path, "roles": set(), "expected_hashes": set()})
        entry["roles"].add(role)
        if expected:
            entry["expected_hashes"].add(expected)

    candidate_count = 0
    for pid in package.painting_lookup.painting_id:
        part = package.load_painting(pid)
        for case in part["cases"]:
            for key in ("clean_image_path", "input_image_path", "mask_or_effect_path"):
                if case.get(key): add(case[key], "case_input")
        for candidate in part["candidates"]:
            candidate_count += 1
            for layer, paths in candidate["asset_routes"].items():
                for path in paths:
                    # Whole-corpus numeric containers are registered provenance,
                    # not an instruction to eagerly download them for one PNG.
                    if path.endswith(".npz"):
                        add(path, "registered_numeric_provenance_not_routine_image")
                    else:
                        add(path, "candidate_layer_" + layer,
                            candidate.get("restored_sha256") if layer == "restored" else None)
        for path, record in ce.saved_maps(pid).items():
            if path in entries:
                add(path, "checksum_registered_map", record["sha256"])
    for path, sha in ce.input_index().items():
        if path in entries: add(path, "checksum_registered_input", sha)
    for path, sha in ce.panel_index().items(): add(path, "retrieval_counterfactual_panel", sha)
    for report in package.load_reports()["reports"]:
        add(report["report_path"], "registered_report", report["report_sha256"])
    archive = ar.catalogue(package)
    for stage in archive["stages"]:
        for file in ar.record(package, stage["id"])["files"]:
            if file.get("directory"):
                # Directory-level records expose metadata, not an invented download.
                continue
            add(file["path"], "archive_explicit_record_download", file["sha256"])
    for folder in (ROOT / "streamlit_assets", ROOT / "outputs/34_final_streamlit_dashboard_assets"):
        for file in folder.rglob("*"):
            if file.is_file(): add(file.relative_to(ROOT).as_posix(), "dashboard_local_asset")
    tracked = set(git("ls-files", "-z").decode().split("\0"))
    published = {r["local_relative_path"]: r for r in csv_rows(ROOT / "outputs/inventory/external_artifact_publication.csv")
                 if r["verification_status"] == "verified" and r["publication_status"] == "published_verified"}
    rows = []
    for path, entry in sorted(entries.items()):
        local = ROOT / path
        entry["roles"] = sorted(entry["roles"])
        entry["expected_hashes"] = sorted(entry["expected_hashes"])
        entry.update(local_exists=local.is_file(), local_size=local.stat().st_size if local.is_file() else None,
                     git_tracked=path in tracked, individual_publication_recorded=path in published,
                     checksum_conflict=len(entry["expected_hashes"]) > 1)
        rows.append(entry)
    return dict(candidates=candidate_count, paintings=len(package.painting_lookup), reports=len(package.load_reports()["reports"]),
        dependencies=rows, counts=dict(total=len(rows), local_missing=sum(not r["local_exists"] for r in rows),
            checksum_conflicts=sum(r["checksum_conflict"] for r in rows), git_tracked=sum(r["git_tracked"] for r in rows),
            recorded_individual=sum(r["individual_publication_recorded"] for r in rows)),
        scope_limit="All N34 selector/layer paths, report paths, Archive individual records and local UI/package files. Actual loader integration, optional-state behavior and fresh remote checks remain separate gates.")


def loader_findings():
    """Source-backed blockers, not a heuristic claiming complete runtime closure."""
    specs = [
        ("metric_framework", "src/restoration_eval/metric_inspection_view.py", "manifest.json", "Local-only inspection companions; published bundles are not consumed by this loader."),
        ("model_gallery", "src/restoration_eval/model_gallery.py", "classical_metrics.csv", "Scans the 144 MB N13 table in application runtime; this file is excluded from Git."),
        ("stability_lab", "src/restoration_eval/stability_lab.py", "spatial_diagnostics.csv", "Reads producer-scale spatial and seed tables; needs bounded, source-pinned selected-record access."),
        ("trustworthiness", "src/restoration_eval/trustworthiness.py", "failure_assignments.csv", "Scans N27 assignment tables per candidate; source files are excluded from Git."),
        ("all_later_room_images", "src/restoration_eval/model_gallery.py", "data = resolved.read_bytes()", "Shared image reader requires local files, with no remote fallback."),
        ("case_explorer", "src/restoration_eval/case_explorer.py", "def source_table(", "Some popup evidence still loads complete upstream tables rather than compact partitions."),
        ("research_archive", "src/restoration_eval/research_archive.py", "The exact artifact is unavailable locally", "Selected report/artifact downloads are local-only, even when the record is published."),
    ]
    result = []
    for room, path, token, finding in specs:
        text = (ROOT / path).read_text(encoding="utf-8")
        matching = [i for i, line in enumerate(text.splitlines(), 1) if token in line]
        result.append(dict(room=room, path=path, lines=matching, finding=finding,
                           source_sha256=sha256_file(ROOT / path), confirmed=bool(matching)))
    return dict(findings=result, blocking_count=sum(r["confirmed"] for r in result),
                note="Do not clear these findings by editing validation expectations. Backend remediation must preserve presentation and have its own approved source baseline.")


def public_bytes(repo, revision, path, maximum=64 * 1024 * 1024):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("A full immutable revision is required")
    if repo not in {"RahulMaddineni264/painting-restoration-eval-candidates", "RahulMaddineni264/painting-restoration-eval-diagnostics"}:
        raise ValueError("Unregistered publication repository")
    if path.startswith("/") or ".." in path.split("/"):
        raise ValueError("Invalid publication path")
    url = f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{path}"
    with urlopen(url, timeout=30) as response:
        raw = response.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError("Metadata read exceeded the declared cap")
    return raw


def remote_audit():
    """Public metadata and member-index audit; never downloads whole bundles."""
    from huggingface_hub import HfApi
    api = HfApi(token=False)
    releases, coverage, errors = [], {}, []
    paths = sorted((ROOT / "outputs/inventory").glob("bundled_publication_*_full.json"))
    paths.append(ROOT / "config/publication/finished_tabs_01_03_assets.json")
    for path in paths:
        saved = read_json(path)
        repo, revision, prefix = saved["repo_id"], saved["revision"], saved["prefix"]
        print("Checking pinned release:", path.name, flush=True)
        try:
            raw = public_bytes(repo, revision, prefix + "/indexes/catalogue.json")
            catalogue = json.loads(raw)
            if catalogue["prefix"] != prefix or catalogue["release_id"] != saved["release_id"]:
                raise ValueError("Catalogue identity mismatch")
            if "catalogue" in saved and (len(raw) != saved["catalogue"]["size_bytes"] or hashlib.sha256(raw).hexdigest() != saved["catalogue"]["sha256"]):
                raise ValueError("Catalogue checksum mismatch")
            if "source_run_id" in saved and catalogue.get("source_run_id") != saved["source_run_id"]:
                raise ValueError("Catalogue producer run mismatch")
            expected = {**catalogue["bundles"], **catalogue.get("other_objects", {}),
                        **{r["path"]: r for r in catalogue["paintings"].values()}}
            entries = {r.path: r for r in api.list_repo_tree(repo, path_in_repo=prefix,
                recursive=True, expand=False, revision=revision, repo_type="dataset") if hasattr(r, "size")}
            checks = Counter()
            bad = []
            for remote, meta in expected.items():
                found = entries.get(remote)
                if found is None:
                    bad.append({"path": remote, "issue": "missing"}); continue
                if found.size != meta["size_bytes"]:
                    bad.append({"path": remote, "issue": "size_mismatch"}); continue
                lfs = getattr(found, "lfs", None)
                if lfs:
                    sha = lfs.get("sha256") if isinstance(lfs, dict) else lfs.sha256
                    if sha != meta["sha256"]:
                        bad.append({"path": remote, "issue": "sha256_mismatch"}); continue
                    checks["lfs_sha256_and_size"] += 1
                else:
                    checks["exists_and_size_only"] += 1
            members_path = prefix + "/indexes/members.csv"
            if members_path in expected:
                meta = expected[members_path]
                members = public_bytes(repo, revision, members_path)
                if len(members) != meta["size_bytes"] or hashlib.sha256(members).hexdigest() != meta["sha256"]:
                    raise ValueError("Members index checksum mismatch")
                member_rows = csv.DictReader(io.StringIO(members.decode("utf-8-sig")))
                count = 0
                for row in member_rows:
                    count += 1
                    coverage.setdefault(row["original_relative_path"], []).append(dict(
                        repo=repo, revision=revision, prefix=prefix, sha256=row["sha256"],
                        size_bytes=int(row["size_bytes"]), transport="bundle_member"))
                if count != saved["asset_count"]:
                    raise ValueError("Members count mismatch")
            else:
                # The display release's per-painting manifests are individually
                # checksum-pinned by the publicly read catalogue.
                count = 0
                for pid, meta in catalogue["paintings"].items():
                    content = public_bytes(repo, revision, meta["path"], maximum=2 * 1024 * 1024)
                    if len(content) != meta["size_bytes"] or hashlib.sha256(content).hexdigest() != meta["sha256"]:
                        raise ValueError("Painting index checksum mismatch")
                    for row in json.loads(content)["assets"]:
                        count += 1
                        coverage.setdefault(row["original_relative_path"], []).append(dict(
                            repo=repo, revision=revision, prefix=prefix, sha256=row["sha256"],
                            size_bytes=int(row["size_bytes"]), transport="bundle_member"))
                if count != saved["source_file_count"]:
                    raise ValueError("Display release member count mismatch")
            # Exact producer sidecars are separately addressable remote objects.
            producer = saved.get("producer")
            if producer:
                for remote, meta in catalogue.get("other_objects", {}).items():
                    suffix = remote.removeprefix(prefix + "/")
                    if suffix.startswith(("data/", "metrics/", "manifests/", "validation/", "reports/")):
                        coverage.setdefault(f"outputs/{producer}/{suffix}", []).append(dict(
                            repo=repo, revision=revision, path=remote, sha256=meta["sha256"],
                            size_bytes=meta["size_bytes"], transport="bundle_release_sidecar"))
            releases.append(dict(receipt=path.relative_to(ROOT).as_posix(), repo=repo, revision=revision,
                catalog_sha256=hashlib.sha256(raw).hexdigest(), expected_objects=len(expected),
                live_checks=dict(checks), bad_objects=bad, indexed_members=count))
        except Exception as exc:
            errors.append(dict(receipt=path.name, error=f"{type(exc).__name__}: {exc}"))
            print("Release audit incomplete:", path.name, type(exc).__name__, flush=True)
    # Individuals are grouped by their publication commit, not the mutable main branch.
    individuals = [r for r in csv_rows(ROOT / "outputs/inventory/external_artifact_publication.csv")
                   if r["verification_status"] == "verified" and r["publication_status"] == "published_verified"]
    groups = {}
    for row in individuals:
        revision = row["publication_commit_url"].rstrip("/").split("/")[-1]
        if not re.fullmatch(r"[0-9a-f]{40}", revision): raise ValueError("Unpinned individual publication")
        groups.setdefault((row["repository_id"], revision), []).append(row)
    individual_checks = Counter()
    for (repo, revision), rows in groups.items():
        print("Checking individual publication group:", revision[:10], len(rows), flush=True)
        for start in range(0, len(rows), 100):
            batch = rows[start:start + 100]
            try:
                remote_rows = api.get_paths_info(repo, [r["path_in_repository"] for r in batch],
                    revision=revision, repo_type="dataset", expand=False)
                remote_by_path = {r.path: r for r in remote_rows}
                for row in batch:
                    found = remote_by_path.get(row["path_in_repository"])
                    lfs = getattr(found, "lfs", None)
                    sha = (lfs.get("sha256") if isinstance(lfs, dict) else lfs.sha256) if lfs else None
                    ok = found is not None and found.size == int(row["size_bytes"]) and sha == row["sha256"]
                    individual_checks["sha256_and_size_verified" if ok else "not_fully_verified"] += 1
                    if ok:
                        coverage.setdefault(row["local_relative_path"], []).append(dict(repo=repo,
                            revision=revision, path=row["path_in_repository"], sha256=sha,
                            size_bytes=int(row["size_bytes"]), transport="individual_object"))
                    else:
                        errors.append(dict(path=row["local_relative_path"], error="Individual metadata missing/mismatched/non-LFS; exact read still required"))
            except Exception as exc:
                errors.append(dict(repo=repo, revision=revision, count=len(batch), error=f"{type(exc).__name__}: {exc}"))
    receipt("remote_coverage.json", dict(paths=coverage))
    return dict(releases=releases, individual_checks=dict(individual_checks), errors=errors,
        coverage_paths=len(coverage), bundle_bytes_downloaded=0,
        full_remote_download_verification=False,
        scope_limit="Live immutable object metadata and checksum-verified member indexes. Small object's size-only checks are not byte verification; cold/warm member retrieval and app wiring are separate gates.")


def checkout_probe(room):
    """Fresh-process missing-untracked-file simulation, NOT a Linux certification."""
    import n35_room_validation as harness
    tracked = set(git("ls-files", "-z").decode().split("\0"))
    rejected = set()
    active = False

    def guard(event, args):
        if not active or event != "open" or not isinstance(args[0], (str, bytes)):
            return
        value = args[0].decode() if isinstance(args[0], bytes) else args[0]
        path = Path(value).resolve()
        if not path.is_relative_to(ROOT): return
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith(("outputs/", "streamlit_assets/")) and relative not in tracked:
            rejected.add(relative)
            raise FileNotFoundError("Clean-checkout simulation: file is not tracked: " + relative)

    sys.addaudithook(guard)
    active = True
    try:
        result = harness.room_smoke(ROOT / "streamlit_app.py", {"room": room}, timeout=120)
    finally:
        active = False
    return dict(room=room, rejected_local_dependencies=sorted(rejected), errors=result["errors"],
        network_attempts=result["network_attempts"], elapsed_seconds=result["elapsed_seconds"],
        passed=not result["errors"] and not rejected and not result["network_attempts"],
        scope_limit="Opening render in a fresh Python process with untracked output/asset reads denied. Tracked local LFS bytes remain present. Does not certify Linux, remote fallback, other filters, browser behavior or deployed performance.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("provenance", "inventory", "loaders", "remote", "checkout"))
    parser.add_argument("--room", choices=("exhibition_foyer", "study_design", "metric_framework", "model_gallery", "stability_lab", "trustworthiness", "focused_portrait_review", "case_explorer", "research_archive"))
    args = parser.parse_args()
    if args.action == "checkout":
        if not args.room: parser.error("checkout requires --room")
        name, result = "checkout_" + args.room, checkout_probe(args.room)
    else:
        action = {"provenance": n29_provenance, "inventory": dependency_inventory, "loaders": loader_findings, "remote": remote_audit}[args.action]
        name, result = args.action, action()
    result = receipt(name + ".json", result)
    compact = {k: v for k, v in result.items() if k not in ("dependencies",)}
    print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
