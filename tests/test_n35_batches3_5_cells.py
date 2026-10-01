"""Test the cell pack/harness only; never execute notebook cells or the app."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import prepare_n35_batches3_5_cells as builder
import n35_room_validation as harness


class CellPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = builder.NOTEBOOK.read_bytes()
        cls.notebook = json.loads(cls.before)
        cls.cells = builder.build_cells(cls.notebook)

    def test_sixteen_complete_cells_with_original_boundaries(self):
        self.assertEqual(len(self.cells), 16)
        self.assertEqual([i + 12 for i, c in enumerate(self.cells)
                          if c["cell_type"] == "markdown"], [12, 18, 23])
        for i, c in enumerate(self.cells, 12):
            if c["cell_type"] == "code":
                ast.parse(c["source"], filename=f"cell-{i}")
        self.assertEqual(builder.NOTEBOOK.read_bytes(), self.before)

    def test_idempotent_after_user_pastes_cells(self):
        notebook = copy.deepcopy(self.notebook)
        notebook["cells"][12:28] = self.cells
        self.assertEqual(builder.build_cells(notebook), self.cells)

    def test_shifted_notebook_is_rejected(self):
        notebook = copy.deepcopy(self.notebook)
        notebook["cells"][28]["source"] = ["Different boundary"]
        with self.assertRaises(ValueError):
            builder.build_cells(notebook)

    def test_idempotent_without_invisible_markdown_marker(self):
        notebook = copy.deepcopy(self.notebook)
        notebook["cells"][12:28] = copy.deepcopy(self.cells)
        notebook["cells"][12]["source"] = self.cells[0]["source"].replace("<!-- N35_BATCHES_3_5_PACK -->", "")
        result = builder.build_cells(notebook)
        self.assertEqual(result[1:], self.cells[1:])

    def test_each_rerun_invalidates_downstream_gates(self):
        for index, c in enumerate(self.cells, 12):
            if c["cell_type"] == "code":
                self.assertIn("drop_validation_stages(", c["source"], index)
        self.assertIn("range(3, 11)", self.cells[1]["source"])
        self.assertIn("batch_10_", self.cells[-1]["source"])

    def test_replacement_final_gates_are_nonvacuous(self):
        self.assertIn("n35.required_stages(VALIDATION.checks, expected_stages)", self.cells[1]["source"])
        self.assertIn("observed != set(expected_stages)", self.cells[1]["source"])
        self.assertIn("canonical_files_absent", self.cells[1]["source"])
        self.assertIn("STOP HERE", self.cells[-1]["source"])

    def test_no_producer_execution_or_canonical_persistence(self):
        for c in self.cells:
            if c["cell_type"] != "code":
                continue
            tree = ast.parse(c["source"])
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, ("write_csv", "to_csv", "to_parquet",
                        "write_bytes", "write_text", "Popen", "system"))

    def test_complete_study_routes_preserved(self):
        self.assertIn("len(visible_case_ids) == 21", self.cells[3]["source"])
        self.assertIn("with n35.offline() as STUDY_NETWORK_ATTEMPTS", self.cells[4]["source"])
        self.assertIn("study_bridge_category_", self.cells[4]["source"])
        self.assertIn("study_bridge_option_", self.cells[4]["source"])
        self.assertNotIn('"guided_tour_html": source_function', self.cells[1]["source"])

    def test_scope_does_not_claim_browser_or_cloud_certification(self):
        final = self.cells[-1]["source"]
        self.assertIn("not tested by AppTest", final)
        self.assertIn("deployment blocker; not fixed or waived here", final)
        self.assertIn("pending fresh browser QA", final)
        self.assertIn("No other", self.cells[11]["source"])

    def test_html_copy_indexes_and_types(self):
        page = builder.render(self.cells, start=12, title="Batches 3–5", notice="Stop after Batch 5")
        self.assertEqual(page.count("Copy complete cell"), 16)
        self.assertIn('id="cell-12"', page)
        self.assertIn('id="cell-27"', page)
        self.assertNotIn('id="cell-0"', page)
        self.assertIn("const text=cells[i-12].source", page)
        self.assertIn("<title>Batches 3–5</title>", page)


class HarnessTests(unittest.TestCase):
    def test_notebook_autosave_allowed_but_source_drift_rejected(self):
        notebook = {"cells": [{"cell_type": "code", "source": ["x = 1\n"],
                               "outputs": [], "execution_count": None}]}
        with patch.object(Path, "read_text", return_value=json.dumps(notebook)):
            baseline = harness.notebook_source_digest("unused.ipynb")
        notebook["cells"][0].update(outputs=[{"text": "runtime output"}], execution_count=23)
        with patch.object(Path, "read_text", return_value=json.dumps(notebook)):
            self.assertEqual(baseline, harness.notebook_source_digest("unused.ipynb"))
        notebook["cells"][0]["source"] = ["x = 2\n"]
        with patch.object(Path, "read_text", return_value=json.dumps(notebook)):
            self.assertNotEqual(baseline, harness.notebook_source_digest("unused.ipynb"))

    def test_network_attempt_is_recorded_even_if_caught(self):
        previous = socket.create_connection
        with harness.offline() as attempts:
            with self.assertRaisesRegex(RuntimeError, "forbids outbound"):
                socket.create_connection(("example.invalid", 443))
        self.assertEqual(attempts, ["outbound_network_attempt"])
        self.assertIs(socket.create_connection, previous)

    def test_missing_and_failed_prerequisite_rejected(self):
        with self.assertRaises(RuntimeError):
            harness.required_stages([], ["batch_2_final_gate"])
        check = SimpleNamespace(validation_stage="batch_2_final_gate", severity="blocking", passed=False)
        with self.assertRaises(RuntimeError):
            harness.required_stages([check], [check.validation_stage])
        check.passed = True
        harness.required_stages([check], [check.validation_stage])

    def test_markup_includes_st_html_and_markdown(self):
        app = SimpleNamespace(markdown=[SimpleNamespace(value="legacy")],
            get=lambda name: [SimpleNamespace(proto=SimpleNamespace(body="current"))])
        self.assertEqual(harness.app_html(app), "legacy\ncurrent")

    def test_path_escape_is_rejected(self):
        with self.assertRaises(ValueError):
            harness.safe_path(ROOT, "../outside")

    def test_approved_transport_normalizes_to_original_freeze(self):
        rows = harness.verify_gallery_freeze(ROOT)
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(r["expected"] == r["observed"] for r in rows))
        view = next(r for r in rows if r["path"].endswith("model_gallery_view.py"))
        self.assertNotEqual(view["raw_observed"], view["observed"])

    def test_normalization_does_not_hide_visual_edits(self):
        path = ROOT / "src/restoration_eval/model_gallery_view.py"
        original = path.read_text(encoding="utf-8")
        altered = original.replace("A convincing completion", "Different visual copy", 1)
        self.assertNotEqual(hashlib.sha256(harness.normalize_gallery_transport(original).encode()).hexdigest(),
                            hashlib.sha256(harness.normalize_gallery_transport(altered).encode()).hexdigest())
        with self.assertRaises(ValueError):
            harness.normalize_gallery_transport(original.replace("revision = room_html(", "revision = other(", 1))


if __name__ == "__main__":
    unittest.main()
