"""Verify the approved Tab 5 checkpoint. Does not stage, commit or upload."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/publication/stability_lab_freeze.json"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def paths(manifest):
    selected = sorted([r["path"] for r in manifest["files"]] + manifest["support_paths"])
    if len(selected) != 24 or len(set(selected)) != 24:
        raise ValueError("Expected exactly 24 unique checkpoint paths")
    for path in selected:
        if not (ROOT / path).resolve().is_relative_to(ROOT) or path.startswith(("outputs/", "notebooks/", ".")):
            raise ValueError(f"Forbidden checkpoint path: {path}")
    return selected


def verify(manifest, staged):
    selected = paths(manifest)
    if git("branch", "--show-current").decode().strip() != "main":
        raise ValueError("Expected main; no branch switching performed")
    index = set(filter(None, git("diff", "--cached", "--name-only", "-z").decode().split("\0")))
    if staged and index != set(selected):
        raise ValueError(f"Wrong staged set. Extra: {sorted(index-set(selected))}; missing: {sorted(set(selected)-index)}")
    if not staged and index:
        raise ValueError("Index is not empty; inspect existing staged work first")
    rows = {r["path"]: r for r in manifest["files"]}
    for path in selected:
        content = git("show", ":" + path) if staged else (ROOT / path).read_bytes()
        if content.startswith(b"version https://git-lfs.github.com/spec/v1") or len(content) > 10*1024*1024:
            raise ValueError(f"LFS pointer or oversized file: {path}")
        arguments = ["check-attr"] + (["--cached"] if staged else []) + ["filter", "--", path]
        if git(*arguments).decode().strip().rsplit(": ", 1)[-1] not in ("unset", "unspecified"):
            raise ValueError(f"Git filter forbidden: {path}")
        if path in rows:
            row = rows[path]
            if row["hash_mode"] == "lf_normalized":
                content = content.replace(b"\r\n", b"\n")
            if hashlib.sha256(content).hexdigest() != row["sha256"]:
                raise ValueError(f"Approved freeze changed: {path}")
    print(f"PASS: {'staged' if staged else 'local'} 24-file Tab 5 freeze; fingerprints match; no LFS filters/pointers")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify-local", "verify-staged", "git-paths"])
    command = parser.parse_args().command
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if command == "git-paths":
        print("\n".join(paths(manifest)))
    else:
        verify(manifest, command == "verify-staged")
