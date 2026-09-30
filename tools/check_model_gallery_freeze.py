"""Read-only guard for the approved Tab 4 checkpoint. Never stages or uploads."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/publication/model_gallery_freeze.json"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def verify(staged=False):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    paths = sorted([r["path"] for r in manifest["files"]] + manifest["support_paths"])
    if len(paths) != len(set(paths)) or len(paths) != 17:
        raise ValueError("Unexpected checkpoint file list")
    if git("branch", "--show-current").decode().strip() != "main":
        raise ValueError("Expected main; no branch switching is performed")
    staged_paths = set(filter(None, git("diff", "--cached", "--name-only", "-z").decode().split("\0")))
    if staged and staged_paths != set(paths):
        raise ValueError(f"Wrong staged set. Extra: {sorted(staged_paths-set(paths))}; missing: {sorted(set(paths)-staged_paths)}")
    if not staged and staged_paths:
        raise ValueError("Index is not empty; inspect existing staged work first")
    for path in paths:
        content = git("show", f":{path}") if staged else (ROOT / path).read_bytes()
        if content.startswith(b"version https://git-lfs.github.com/spec/v1"):
            raise ValueError(f"LFS pointer is forbidden: {path}")
        if len(content) > 10 * 1024 * 1024:
            raise ValueError(f"File exceeds checkpoint size cap: {path}")
        args = ["check-attr"] + (["--cached"] if staged else []) + ["filter", "--", path]
        attr = git(*args).decode().strip().rsplit(": ", 1)[-1]
        if attr not in ("unset", "unspecified"):
            raise ValueError(f"Git filter forbidden: {path}: {attr}")
    for row in manifest["files"]:
        data = git("show", ":" + row["path"]) if staged else (ROOT / row["path"]).read_bytes()
        if row["hash_mode"] == "lf_normalized":
            data = data.replace(b"\r\n", b"\n")
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError(f"Approved freeze changed: {row['path']}")
    print(f"PASS: {'staged' if staged else 'local'} 17-file Tab 4 checkpoint; approved fingerprints match; no LFS filters/pointers")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify-local", "verify-staged", "git-paths"])
    command = parser.parse_args().command
    if command == "git-paths":
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        print("\n".join(sorted([r["path"] for r in data["files"]] + data["support_paths"])))
    else:
        verify(command == "verify-staged")
