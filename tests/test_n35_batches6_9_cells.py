"""Regression tests for N35 Batches 6–9 preparation, not notebook execution."""
import ast
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import prepare_n35_batches6_9_cells as builder
import prepare_n35_batches3_5_cells as prior
import n35_room_validation as harness


class LaterCellPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = builder.NOTEBOOK.read_bytes()
        cls.notebook = json.loads(cls.before)
        cls.cells = builder.build_cells(cls.notebook)

    def test_original_boundaries_and_complete_syntax(self):
        self.assertEqual(len(self.cells), 21)
        self.assertEqual([i+28 for i,c in enumerate(self.cells) if c["cell_type"] == "markdown"], [28,33,38,43])
        for i,c in enumerate(self.cells,28):
            if c["cell_type"] == "code":
                ast.parse(c["source"], filename=f"cell-{i}")
        self.assertEqual(builder.NOTEBOOK.read_bytes(), self.before)

    def test_no_old_persistence_cells_survive(self):
        code = "\n".join(c["source"] for c in self.cells if c["cell_type"] == "code")
        for forbidden in ("FINAL_RELOADED_VALIDATION", "MANIFEST_INPUT_PATHS", "os.replace(",
                          ".write_csv(", ".write_text(", ".to_csv(", "hf upload", "git push"):
            self.assertNotIn(forbidden, code)
        self.assertIn("STOP HERE", self.cells[-1]["source"])
        self.assertIn("N35 is NOT complete", self.cells[-1]["source"])

    def test_four_gates_and_rerun_invalidation(self):
        for batch,index in ((6,4),(7,9),(8,14),(9,19)):
            self.assertIn(f"finish_room_batch({batch},", self.cells[index]["source"])
            self.assertIn(f"batch_{batch}_source_contract", self.cells[index]["source"])
            self.assertIn(f"batch_{batch}_saved_evidence", self.cells[index]["source"])
            self.assertIn(f"batch_{batch}_server_smoke", self.cells[index]["source"])
        for c in self.cells[:-1]:
            if c["cell_type"] == "code":
                self.assertIn("drop_validation_stages(", c["source"])

    def test_binding_counts_distinguish_displays_and_slots(self):
        self.assertIn('room_check("binding_count", 21,', prior.METRIC_SOURCE)
        self.assertIn('"room_and_binding_count", (12, 19)', prior.GALLERY_DATA)
        self.assertIn('room_binding_checks("metric_framework", 12, 21)', builder.SETUP)
        self.assertIn('room_binding_checks("model_gallery", 12, 19)', builder.SETUP)
        self.assertIn('"raw_registered_binding_count", 40', builder.CASE_SOURCE)
        self.assertIn('room_binding_checks("case_explorer", 15, 39)', builder.CASE_SOURCE)

    def test_exact_n29_discrepancy_remains_pending(self):
        self.assertIn('"known_n29_discrepancy_preserved", "recorded_hash_mismatch"', builder.ARCHIVE_DATA)
        self.assertIn("not repaired, waived", builder.ARCHIVE_DATA)
        self.assertIn("N29 provenance discrepancy", builder.HANDOFF)
        self.assertIn("not_current_n35_results", builder.ARCHIVE_DATA)

    def test_metric_availability_is_checked_against_saved_sources(self):
        self.assertIn('"registered_candidate_universe", (13879, 13879)', builder.CASE_DATA)
        self.assertIn('source_candidates == all_candidates', builder.CASE_DATA)
        self.assertIn('hashlib.file_digest(handle, "sha256")', builder.CASE_DATA)
        self.assertIn('"unavailable_metric_population_not_zero", 1935', builder.CASE_DATA)

    def test_no_remote_or_browser_pass_invented(self):
        self.assertIn("not browser-JS execution", builder.SETUP)
        self.assertIn("No uploads authorized", builder.HANDOFF)
        self.assertIn("Live deployment: NOT VERIFIED", builder.HANDOFF)
        self.assertIn("dynamic numeric-parity gaps", builder.HANDOFF)

    def test_render_numbering_and_copy_controls(self):
        page=builder.render(self.cells,start=28,title="Batches 6–9",notice="Stop")
        self.assertEqual(page.count("Copy complete cell"),21)
        self.assertIn('id="cell-48"',page)
        self.assertIn("const text=cells[i-28].source",page)

    def test_safe_regeneration_after_paste(self):
        notebook=copy.deepcopy(self.notebook)
        notebook["cells"][28:49]=self.cells
        self.assertEqual(builder.build_cells(notebook),self.cells)

    def test_shifted_cells_rejected(self):
        notebook=copy.deepcopy(self.notebook)
        notebook["cells"][28]["source"]=["Other heading"]
        with self.assertRaises(ValueError):builder.build_cells(notebook)


class LaterHarnessTests(unittest.TestCase):
    def test_all_original_room_freezes_still_match(self):
        for name,count in (("stability_lab",23),("trustworthiness",27),("focused_portrait",24),("research_archive",52)):
            with self.subTest(room=name):
                rows=harness.verify_later_room_freeze(ROOT,name)
                self.assertEqual(len(rows),count)
                self.assertTrue(all(r["expected"]==r["observed"] for r in rows))

    def test_controller_json_is_parsed_not_executed(self):
        expected={"candidate":{"candidate_id":"exact; tricky } id"},"missing":None}
        source="MuseumReadiness.watch(window, 'x', function(){const data="+json.dumps(expected)+",doc=window.parent.document;throw Error('never run');});"
        app=SimpleNamespace(get=lambda _: [SimpleNamespace(proto=SimpleNamespace(srcdoc=source))])
        self.assertEqual(harness.controller_payload(app),expected)

    def test_missing_and_duplicate_controller_payloads_fail(self):
        for frames in ([],["const data={};"],["MuseumReadiness.watch();const data={};"]*2):
            app=SimpleNamespace(get=lambda _: [SimpleNamespace(proto=SimpleNamespace(srcdoc=s)) for s in frames])
            with self.assertRaises(ValueError):harness.controller_payload(app)

    def test_git_baseline_requires_immutable_revision(self):
        with self.assertRaises(ValueError):harness.verify_committed_files(ROOT,"HEAD",[])
        rows=harness.verify_committed_files(ROOT,"e88feea5e0deb6d5e48cb12378d69ff5d63b2e11",
            ["src/restoration_eval/case_explorer.py","src/restoration_eval/case_explorer_view.py"])
        self.assertTrue(all(r["expected"]==r["observed"] for r in rows))


if __name__=="__main__":unittest.main()
