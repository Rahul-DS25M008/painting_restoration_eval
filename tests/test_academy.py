"""Validate the offline course contract and its physical-damage evidence."""
import base64
import io
import json
from pathlib import Path
import re
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "docs/academy/source.html").read_text(encoding="utf-8")
COURSE = json.loads(re.search(r"const COURSE = (.*);", SOURCE)[1])
ASSETS = json.loads(re.search(r"const ASSETS = (.*);", SOURCE)[1])


class AcademyTests(unittest.TestCase):
    def test_complete_course_and_question_contract(self):
        chapters = COURSE["chapters"]
        self.assertEqual(len(chapters), 39)
        self.assertEqual(len({c["key"] for c in chapters}), 39)
        self.assertEqual([c["key"] for c in chapters[-3:]], ["n36", "d03", "d04"])
        questions = []
        for chapter in chapters:
            self.assertIn(chapter["phase"], COURSE["phases"])
            group = [chapter["lab"], *chapter["practice"], chapter["check"], *chapter["quiz"]]
            self.assertEqual(len(group), 5, chapter["key"])
            questions.extend(group)
        self.assertEqual(len(questions), 195)
        for question in questions:
            self.assertIn(question["answer"], range(len(question["choices"])))
            self.assertTrue(question["why"])

    def test_new_evidence_decodes_and_sources_exist(self):
        for chapter in COURSE["chapters"][-2:]:
            self.assertTrue((ROOT / chapter["source"]).is_file())
            keys = [chapter["asset"], *[f["asset"] for f in chapter.get("extra_figures", [])]]
            for key in keys:
                with Image.open(io.BytesIO(base64.b64decode(ASSETS[key], validate=True))) as image:
                    image.load()
                    self.assertEqual(image.format, "WEBP")
                    self.assertGreater(image.width, 700)
                    self.assertGreater(image.height, 400)
        self.assertEqual(len(COURSE["chapters"][-1]["extra_figures"]), 1)

    def test_export_contains_current_source_and_stays_within_pages_budget(self):
        publication = (ROOT / "docs/academy/index.html").read_text(encoding="utf-8")
        self.assertIn(SOURCE, publication)
        self.assertLess(len(publication.encode()), 2_000_000)
        self.assertNotIn("window.openai", publication)
        self.assertIn("connect-src 'none'", publication)
        self.assertIn("localStorage.setItem(STORAGE_KEY", publication)



if __name__ == "__main__":
    unittest.main()
