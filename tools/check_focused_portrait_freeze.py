"""Check the approved portrait-room checkpoint; never stage, commit or upload."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = "config/publication/focused_portrait_freeze.json"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def paths(manifest):
    selected = sorted([row["path"] for row in manifest["files"]] + manifest["support_paths"])
    if len(selected) != manifest["file_count"] or len(set(selected)) != len(selected):
        raise ValueError("Checkpoint path count or uniqueness mismatch")
    for path in selected:
        if not (ROOT / path).resolve().is_relative_to(ROOT) or not path.startswith((
            "src/restoration_eval/focused_portrait", "streamlit_assets/focused_portrait",
            "streamlit_assets/rooms/focused_portrait", "tests/test_focused_portrait",
            "docs/dashboard_design_finalists/focused_portrait",
            "tools/check_focused_portrait_freeze.py", MANIFEST_PATH,
        )):
            raise ValueError(f"Forbidden checkpoint path: {path}")
    return selected


def verify(manifest, staged=False):
    selected = paths(manifest)
    if git("branch", "--show-current").decode().strip() != "main":
        raise ValueError("Expected main; no branch switching performed")
    index = set(filter(None, git("diff", "--cached", "--name-only", "-z").decode().split("\0")))
    if staged and index != set(selected):
        raise ValueError(f"Wrong staged set. Extra: {sorted(index-set(selected))}; missing: {sorted(set(selected)-index)}")
    if not staged and index:
        raise ValueError("Index is not empty; inspect existing staged work first")
    if staged and json.loads(git("show", ":" + MANIFEST_PATH)) != manifest:
        raise ValueError("Staged manifest differs from approved checkpoint")
    rows = {row["path"]: row for row in manifest["files"]}
    total = 0
    for path in selected:
        content = git("show", ":" + path) if staged else (ROOT / path).read_bytes()
        total += len(content)
        if content.startswith(b"version https://git-lfs.github.com/spec/v1") or len(content) > 10*1024*1024:
            raise ValueError(f"LFS pointer or oversized file: {path}")
        args = ["check-attr"] + (["--cached"] if staged else []) + ["filter", "--", path]
        if git(*args).decode().strip().rsplit(": ", 1)[-1] not in ("unset", "unspecified"):
            raise ValueError(f"Git filter forbidden: {path}")
        if path in rows:
            row = rows[path]
            if row["hash_mode"] == "lf_normalized":
                content = content.replace(b"\r\n", b"\n")
            if hashlib.sha256(content).hexdigest() != row["sha256"]:
                raise ValueError(f"Approved freeze changed: {path}")
    print(f"PASS: {'staged' if staged else 'local'} {len(selected)}-file portrait freeze; fingerprints match; no LFS; {total/1024/1024:.2f} MiB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify-local", "verify-staged", "git-paths"])
    command = parser.parse_args().command
    manifest = json.loads((ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    if command == "git-paths":
        print("\n".join(paths(manifest)))
    else:
        verify(manifest, command == "verify-staged")
