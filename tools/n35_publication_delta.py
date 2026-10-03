"""Validate the separately approved post-publication Archive delta.

Never rewrite the original freeze or accept an arbitrary current source as its
replacement. The receipt contains exact reviewed before/after identities.
"""
import hashlib
import json
from pathlib import Path

RECEIPT = "config/publication/research_archive_publication_delta.json"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def receipt(root, relative=RECEIPT):
    path = Path(root) / relative
    if not path.is_file():
        return {"files": {}, "added_files": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") not in {"research_archive_publication_delta.v1", "n35_validation_delta.v1"}:
        raise ValueError("Unknown publication-delta schema")
    return data


def publication_baseline(root, relative, current):
    entry = receipt(root)["files"].get(relative)
    if entry is None:
        return current
    if sha(current) != entry["after_sha256"]:
        raise ValueError("Unreviewed publication change: " + relative)
    if sha(entry["before_source"]) != entry["before_sha256"]:
        raise ValueError("Corrupt publication preimage: " + relative)
    return entry["before_source"]


def validation_baseline(root, relative, current):
    """Only the reviewed regression-test change, never application sources."""
    if relative != "tests/test_model_gallery.py":
        return current
    entry = receipt(root, "config/publication/n35_validation_delta.json")["files"].get(relative)
    if entry is None:
        return current
    if sha(current) != entry["after_sha256"] or sha(entry["before_source"]) != entry["before_sha256"]:
        raise ValueError("Unreviewed validation delta: " + relative)
    return entry["before_source"]


def verify_added_files(root):
    root = Path(root).resolve()
    for relative, expected in receipt(root)["added_files"].items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Publication asset outside repository")
        raw = path.read_bytes()
        if expected["hash_mode"] == "lf_normalized":
            raw = raw.replace(b"\r\n", b"\n")
        elif expected["hash_mode"] != "binary":
            raise ValueError("Unknown publication asset hash mode")
        if hashlib.sha256(raw).hexdigest() != expected["sha256"]:
            raise ValueError("Unreviewed publication asset: " + relative)
