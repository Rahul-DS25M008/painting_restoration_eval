"""Verify exact presentation wording changes against a preserved Git revision.

Scientific records and original freeze manifests are never rewritten. This
adapter is used only by historical freeze validation, not by the application.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess


RECEIPT = "config/publication/editorial_wording_delta.json"


def baseline(root, relative, current):
    root = Path(root)
    receipt = root / RECEIPT
    if not receipt.is_file():
        return current
    data = json.loads(receipt.read_text(encoding="utf-8"))
    if data.get("schema") != "editorial_wording_delta.v1":
        raise ValueError("Unknown editorial delta schema")
    entry = data["files"].get(relative)
    if entry is None:
        return current
    if hashlib.sha256(current.encode()).hexdigest() != entry["after_sha256"]:
        raise ValueError("Unreviewed editorial change: " + relative)
    revision = entry.get("base_commit", data["base_commit"])
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Invalid editorial baseline revision")
    if not (root / relative).resolve().is_relative_to(root.resolve()):
        raise ValueError("Editorial path outside repository")
    original = subprocess.check_output(
        ["git", "show", revision + ":" + relative], cwd=root
    ).decode("utf-8").replace("\r\n", "\n")
    if hashlib.sha256(original.encode()).hexdigest() != entry["before_sha256"]:
        raise ValueError("Editorial preimage mismatch: " + relative)
    return original
