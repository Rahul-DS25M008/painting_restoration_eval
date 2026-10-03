"""Exact approved deltas must not hide new presentation or evidence drift."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import n35_publication_delta as delta
import n35_room_validation as rooms


class PublicationFreezeDeltaTests(unittest.TestCase):
    def test_original_freeze_and_backend_receipts_unchanged(self):
        rows = rooms.verify_committed_files(
            ROOT, "2378961a8accb2ecde610ed60428879e8f52a8a8",
            ["config/publication/research_archive_freeze.json",
             "config/publication/n35_backend_delta.json"],
        )
        self.assertTrue(all(r["expected"] == r["observed"] for r in rows))

    def test_current_archive_matches_original_plus_exact_approved_delta(self):
        rows = rooms.verify_later_room_freeze(ROOT, "research_archive")
        self.assertEqual(len(rows), 52)
        self.assertTrue(all(r["expected"] == r["observed"] for r in rows))
        delta.verify_added_files(ROOT)

    def test_every_reviewed_source_rejects_even_one_extra_character(self):
        for relative in delta.receipt(ROOT)["files"]:
            with self.subTest(path=relative), self.assertRaisesRegex(ValueError, "Unreviewed"):
                delta.publication_baseline(
                    ROOT, relative, (ROOT / relative).read_text(encoding="utf-8") + " "
                )

    def test_corrupt_preimage_is_rejected(self):
        receipt = copy.deepcopy(delta.receipt(ROOT))
        relative = next(iter(receipt["files"]))
        receipt["files"][relative]["before_source"] += " "
        with patch.object(delta, "receipt", return_value=receipt):
            with self.assertRaisesRegex(ValueError, "Corrupt"):
                delta.publication_baseline(ROOT, relative, (ROOT / relative).read_text(encoding="utf-8"))

    def test_unlisted_source_is_not_normalized(self):
        self.assertEqual(delta.publication_baseline(ROOT, "unlisted.py", "new source"), "new source")

    def test_validation_delta_is_exact_and_does_not_apply_to_app_sources(self):
        relative = "tests/test_model_gallery.py"
        current = (ROOT / relative).read_text(encoding="utf-8")
        self.assertNotEqual(delta.validation_baseline(ROOT, relative, current), current)
        with self.assertRaisesRegex(ValueError, "Unreviewed validation delta"):
            delta.validation_baseline(ROOT, relative, current + " ")
        self.assertEqual(delta.validation_baseline(ROOT, "streamlit_app.py", "new"), "new")

    def test_changed_asset_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "portrait.png").write_bytes(b"changed")
            receipt = {"added_files": {"portrait.png": {
                "hash_mode": "binary", "sha256": hashlib.sha256(b"approved").hexdigest()}}}
            with patch.object(delta, "receipt", return_value=receipt):
                with self.assertRaisesRegex(ValueError, "Unreviewed publication asset"):
                    delta.verify_added_files(root)

    def test_receipt_identifies_reviewed_commits_and_bounded_scope(self):
        receipt = delta.receipt(ROOT)
        self.assertEqual(receipt["approved_commit"], "19837d4a6376fcd1912404d8560591a4e0908358")
        self.assertEqual(len(receipt["files"]), 6)
        self.assertEqual(len(receipt["added_files"]), 5)
