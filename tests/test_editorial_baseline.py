"""Editorial changes are exact exceptions, not a waiver of frozen checks."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from editorial_baseline import baseline, RECEIPT


class EditorialBaselineTests(unittest.TestCase):
    def test_every_receipt_restores_original_and_rejects_unlisted_edits(self):
        data = json.loads((ROOT / RECEIPT).read_text())
        for relative in data["files"]:
            current = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative):
                self.assertNotEqual(baseline(ROOT, relative, current), current)
                with self.assertRaisesRegex(ValueError, "Unreviewed editorial"):
                    baseline(ROOT, relative, current + " ")

    def test_unlisted_content_is_never_normalized(self):
        self.assertEqual(baseline(ROOT, "unlisted.txt", "unreviewed"), "unreviewed")
