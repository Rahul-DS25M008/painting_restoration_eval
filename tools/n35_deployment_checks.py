"""Fresh-process deployment checks and explicit, bounded public sample reads."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from restoration_eval import evidence_transport as transport

ROOMS = ("exhibition_foyer", "study_design", "metric_framework", "model_gallery", "stability_lab", "trustworthiness", "focused_portrait_review", "case_explorer", "research_archive")


def companion_check():
    manifest = transport.manifest()
    total = 0
    for name, meta in manifest["files"].items():
        raw = transport.checked((transport.INDEX / name).read_bytes(), meta)
        total += len(raw)
    identities = transport.table("tables/identities.csv.gz", dtype=str).fillna("")
    if len(identities) != 13879 or identities.candidate_id.duplicated().any():
        raise ValueError("Compact candidate population drift")
    counts = {key: sum(r.get("rows", 0) for name, r in manifest["files"].items() if name.startswith("tables/" + key + "/")) for key in ("flags", "categories", "policy")}
    if counts != {"flags": 152669, "categories": 194306, "policy": 319217}:
        raise ValueError("Compact assignment population drift")
    return dict(passed=True, files=len(manifest["files"]), bytes=total, route_count=manifest["route_count"], populations=counts,
                source_hashes=manifest["sources"])


def opening(room, missing_local=False, remote=False):
    """No notebook execution, no scientific output mutation, no server required."""
    from streamlit.testing.v1 import AppTest
    from n35_room_validation import app_errors, app_html, offline
    tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0"))
    denied = set()
    original = Path.open
    def guarded(path, *args, **kwargs):
        resolved = path.resolve()
        if missing_local and resolved.is_relative_to(ROOT):
            rel = resolved.relative_to(ROOT).as_posix()
            if rel.startswith(("outputs/", "streamlit_assets/")) and rel not in tracked and not rel.startswith("streamlit_assets/evidence/deployment/"):
                denied.add(rel)
                raise FileNotFoundError("Simulated clean checkout: " + rel)
        return original(path, *args, **kwargs)
    @contextmanager
    def connected(): yield []
    start = time.monotonic()
    with patch.object(Path, "open", guarded), (connected() if remote else offline()) as attempts:
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=120)
        app.query_params["room"] = room
        app.run()
        errors = app_errors(app)
        markup = app_html(app)
    return dict(room=room, passed=not errors and bool(markup), errors=errors, elapsed_seconds=round(time.monotonic()-start, 3),
        simulated_missing_paths=sorted(denied), network_attempts=attempts, remote_enabled=remote,
        request_count=transport.READER.request_count, downloaded_bytes=transport.READER.downloaded_bytes,
        scope="Fresh-process Python render; not browser, Linux, or live-deployment certification")


def remote_samples():
    """Ten representative immutable reads, not the full scientific population."""
    with tempfile.TemporaryDirectory(prefix="n35-remote-") as cache:
        reader = transport.Reader(cache)
        manifest = transport.manifest()
        selected = {}
        for name in sorted(manifest["files"]):
            if not name.startswith("routes/"): continue
            for relative, routes in transport.partition(name).items():
                for route in routes:
                    if "member_path" in route:
                        producer = relative.split("/")[1] if relative.startswith("outputs/") else "metric_companions"
                        if producer.startswith("22_"): producer += "_candidate" if "/restored/" in relative else "_diagnostic"
                        cost = route["bundle"]["size_bytes"]
                    else:
                        producer = "n32_report" if relative.startswith("outputs/32_") else "individual"
                        if producer == "n32_report" and not relative.endswith(".html"): continue
                        cost = route["size_bytes"]
                    if cost > 32 * transport.MIB or ("member_path" not in route and cost > 4 * transport.MIB): continue
                    if producer not in selected or cost < selected[producer][0]: selected[producer] = (cost, relative, route)
        results = []
        for key, (_, relative, route) in sorted(selected.items()):
            print("Cold/warm exact-byte sample:", key, flush=True)
            before_requests, before_bytes = reader.request_count, reader.downloaded_bytes
            start = time.monotonic()
            cold = reader.read(route)
            requests_after_cold = reader.request_count
            warm = reader.read(route)
            results.append(dict(sample=key, path=relative, sha256=transport.digest(cold), expected=route["sha256"],
                passed=cold == warm and transport.digest(cold) == route["sha256"] and requests_after_cold == reader.request_count,
                request_count=reader.request_count-before_requests, downloaded_bytes=reader.downloaded_bytes-before_bytes,
                elapsed_seconds=round(time.monotonic()-start,3)))
        return dict(passed=bool(results) and all(r["passed"] for r in results), samples=results,
                    scope="Selected HF immutable reads; Git/LFS checkout and live-site behavior require separate checks")


def github_samples():
    """Verify Git text and LFS content at an immutable existing commit."""
    from urllib.request import urlopen
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    repo = "Rahul-DS25M008/painting_restoration_eval"
    paths = [("git_blob", "requirements.txt"), ("git_lfs", "outputs/02_image_preprocessing/images/clean/p018.png")]
    result = []
    for kind, relative in paths:
        blob = subprocess.check_output(["git", "show", revision + ":" + relative], cwd=ROOT)
        if kind == "git_lfs":
            if not blob.startswith(b"version https://git-lfs.github.com/spec/v1"): raise ValueError("Expected a Git LFS pointer")
            expected = next(line.split(b":",1)[1].decode() for line in blob.splitlines() if line.startswith(b"oid sha256:"))
            url = f"https://media.githubusercontent.com/media/{repo}/{revision}/{relative}"
        else:
            expected = transport.digest(blob)
            url = f"https://raw.githubusercontent.com/{repo}/{revision}/{relative}"
        with urlopen(url, timeout=15) as response: raw = response.read(4*transport.MIB+1)
        result.append(dict(sample=kind, path=relative, revision=revision, sha256=transport.digest(raw), expected=expected,
                           passed=len(raw)<=4*transport.MIB and transport.digest(raw)==expected))
    return dict(passed=all(r["passed"] for r in result), samples=result,
                scope="Pinned public Git blob and LFS-byte availability; not a Linux checkout or new deployment")


def performance(room):
    import psutil
    import math
    from streamlit.testing.v1 import AppTest
    from n35_room_validation import offline, app_errors
    process = psutil.Process()
    with offline() as attempts:
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=120)
        app.query_params["room"] = room
        start = time.monotonic()
        app.run()
        cold = time.monotonic()-start
        rss = [process.memory_info().rss]
        errors = app_errors(app)
        samples = []
        for _ in range(5):
            start = time.monotonic()
            app.run()
            samples.append(time.monotonic()-start)
            rss.append(process.memory_info().rss)
            errors.extend(app_errors(app))
    p95 = sorted(samples)[math.ceil(.95*len(samples))-1]
    passed = not errors and not attempts and max(rss)<=512*transport.MIB and p95<=1.5 and (room!="exhibition_foyer" or cold<=5)
    return dict(passed=passed, room=room, cold_seconds=cold, warm_seconds=samples, warm_p95_seconds=p95,
                max_sampled_rss_bytes=max(rss), errors=errors, network_attempts=attempts,
                scope="Fresh local Python process, five same-room warm rerenders; sampled RSS, not OS peak RSS or browser navigation p95")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("companion", "opening", "remote", "github", "performance", "suite"))
    parser.add_argument("--group", choices=("study", "metric", "gallery", "stability", "trust_portrait", "case", "archive"))
    parser.add_argument("--room", choices=ROOMS)
    parser.add_argument("--missing-local", action="store_true")
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--request-id", default="")
    args = parser.parse_args()
    if args.action == "suite" and not args.group: parser.error("--group required")
    if args.action in {"opening", "performance"} and not args.room: parser.error("--room required")
    if args.action == "suite":
        from n35_room_validation import run_suite
        result = run_suite(ROOT,args.group)
    else:
        result = companion_check() if args.action == "companion" else remote_samples() if args.action == "remote" else github_samples() if args.action == "github" else performance(args.room) if args.action == "performance" else opening(args.room, args.missing_local, args.remote)
    result["request_id"] = args.request_id
    dest = ROOT / ".codex_tmp/n35_batch10_audit"
    dest.mkdir(parents=True, exist_ok=True)
    name = "deployment_" + (args.room if args.action == "opening" else args.action + ("_"+args.room if args.room else ""))
    if args.group: name += "_"+args.group
    (dest / (name + ".json")).write_text(json.dumps(result,indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not result["passed"]: raise SystemExit(1)


if __name__ == "__main__": main()
