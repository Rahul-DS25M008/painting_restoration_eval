"""Bounded D02 source/presentation checks; no scientific recomputation."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from restoration_eval.dashboard_application import open_dashboard_package
from restoration_eval.focused_portrait import ROOT, D02, REPORT, verified_source, payload, report_tables, table, return_room
from restoration_eval.focused_portrait_view import room_markup, render_original_report


class FocusedPortraitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = open_dashboard_package(ROOT)
        cls.data = payload(cls.package)

    def test_exact_opening_and_registered_control(self):
        d = self.data
        self.assertEqual(d["review"]["blind_review_code"], "R005")
        self.assertEqual(d["review"]["candidate_id"], "candidate__hint_places2__canonical__p269__mixed_damage__c00")
        self.assertEqual(d["crop"], [617,81,716,215])
        self.assertEqual(d["control_crop"], [605,576,704,710])
        self.assertEqual(len(d["hand_indices"]), 1196)
        self.assertEqual(len(d["control_indices"]), 1196)
        self.assertFalse(set(d["hand_indices"]) & set(d["control_indices"]))
        self.assertAlmostEqual(d["overlap"]["anatomical_fraction_affected"], .26279938475060427)
        self.assertEqual(len(d["registered"]), 3)

    def test_recorded_scope_not_annotation_case_conflation(self):
        self.assertEqual(self.data["scope"], dict(screened=60,included=36,excluded=24,
            annotations=91,retained=88,intersections=1265,eligible=292,hand_cases=45,
            hand_paintings=20,reviews=32,review_cases=8,visible_failures=25,profiles=30,context_matches=10))
        self.assertEqual(len(report_tables()["hand_control_design.csv"]), 53)

    def test_hand_and_lightness_summaries_keep_metrics_separate(self):
        h,l = self.data["hand"],self.data["light"]
        self.assertEqual(len(h), 12)
        self.assertEqual(sum(r["estimate"]>0 for r in h), 12)
        self.assertEqual(sum(r["q_value"]<.05 for r in h), 10)
        self.assertEqual(len({r["metric_name"] for r in l}), 6)
        self.assertEqual(sum(r["interval_high"]<0 for r in l), 3)
        self.assertEqual(sum(r["interval_low"]<=0<=r["interval_high"] for r in l), 21)
        self.assertTrue(all(r["metric_name"]=="chroma_error_mean" for r in l if r["interval_high"]<0))

    def test_blind_review_exact_note_and_counterexample(self):
        r = self.data["review"]
        self.assertTrue(r["overall_anatomy_failure"])
        self.assertEqual(r["reviewer_confidence"], "high")
        self.assertEqual(r["review_notes"], "Upper digits merge into an irregular form with malformed contours.")
        counter = payload(self.package, "R003")
        self.assertFalse(counter["review"]["overall_anatomy_failure"])
        self.assertEqual(counter["review"]["painting_id"], "p260")
        self.assertFalse(counter["registered"], "Never substitute R005 assets for another review")

    def test_mask_variant_keeps_exact_case_and_control(self):
        reviews = table("data/manual_anatomy_review.csv")
        row = reviews[reviews.case_id.str.startswith("mask_robustness__")].iloc[0]
        d = payload(self.package, row.blind_review_code)
        self.assertEqual(d["review"]["case_id"], row.case_id)
        self.assertEqual(d["control"]["case_id"], row.case_id)
        self.assertEqual(d["control"]["hand_control_id"], row.hand_control_id)

    def test_invalid_identity_and_return_route_rejected(self):
        with self.assertRaises(ValueError): payload(self.package, "R999")
        with self.assertRaises(ValueError): return_room("metric_framework")
        for parent in ("study_design", "trustworthiness", "case_explorer"):
            self.assertEqual(return_room(parent), parent)

    def test_retained_lightness_context_and_adjustments(self):
        d = self.data
        self.assertEqual(len(d["profiles"]),30)
        self.assertEqual(len(d["matches"]),10)
        self.assertEqual(len(d["associations"]),24)
        self.assertTrue(all(r["adjusted_context_fields"]=="damaged_skin_fraction|median_clean_region_chroma|clean_region_lstar_contrast" for r in d["associations"]))

    def test_reference_details_use_original_pixels_and_guard_recorded_counts(self):
        import hashlib
        source = ROOT / "docs/dashboard_design_finalists/approved_current/09_focused_portrait_review_final.png"
        asset = ROOT / "streamlit_assets/rooms/focused_portrait_reference_details.png"
        self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), hashlib.sha256(asset.read_bytes()).digest())
        markup = room_markup(self.data, "<nav>Test</nav>", "shell", "reference-pixels")
        self.assertIn('src="reference-pixels"', markup)
        self.assertIn('data-reference-regions="18"', markup)
        self.assertEqual(markup.count(' fpr-original-detail'), 22)
        changed = {**self.data, "scope": {**self.data["scope"], "screened": 61}}
        markup = room_markup(changed, "", "shell", "reference-pixels")
        self.assertIn('data-reference-regions="17"', markup)
        self.assertNotIn('fpr-formation-screened fpr-original-detail', markup)
        self.assertIn('class="fpr-count">61</span>', markup)

    def test_review_folio_reference_and_live_navigation(self):
        markup = room_markup(self.data, "", "shell", "reference-pixels")
        self.assertNotIn('fpr-title fpr-original-detail', markup)
        self.assertNotIn('fpr-breadcrumb', markup)
        self.assertIn('fpr-door fpr-original-detail', markup)
        self.assertIn('href="?room=trustworthiness"', markup)
        self.assertEqual(markup.count('fpr-observation-plaque'), 4)
        for key in ("clean", "restored"):
            self.assertIn('fpr-folio-'+key, markup)
        self.assertIn('R005 · failure · high confidence', markup)
        self.assertIn('25 of 32: visible anatomy failure', markup)
        self.assertIn('Model names hidden during review.', markup)
        self.assertNotIn('Codex-assisted', markup)
        self.assertIn('class="fpr-plaque fpr-eligibility"', markup)
        self.assertIn('<span>1,196 damaged hand pixels</span><span>26.28% affected</span>', markup)
        self.assertEqual(markup.count('fpr-resource-label'), 4)
        for theme in ("digits", "contour", "wrist", "texture"):
            self.assertIn('data-action="observation:'+theme+'"', markup)
        for kind in ("clean", "damaged", "restored", "difference", "control"):
            self.assertIn('fpr-table-'+kind, markup)
        self.assertEqual(markup.count('fpr-print-caption'), 5)
        self.assertIn('fpr-lightness-reading', markup)
        other = {**self.data, "return_room": "study_design"}
        markup = room_markup(other, "", "shell", "reference-pixels")
        self.assertNotIn('fpr-door fpr-original-detail', markup)
        self.assertIn('href="?room=study_design"', markup)
        self.assertIn('data-reference-regions="17"', markup)

    def test_report_displays_and_downloads_exact_verified_original(self):
        from unittest.mock import patch
        report = verified_source(D02+"/"+REPORT).read_bytes()
        with patch('restoration_eval.focused_portrait_view.st') as ui, \
             patch('restoration_eval.focused_portrait_view.components.html') as frame:
            render_original_report("R005", "trustworthiness")
        frame.assert_called_once_with(report.decode('utf-8'), height=760, scrolling=True)
        self.assertEqual(ui.download_button.call_args.args[1], report)
        self.assertIn('portrait_review=R005', ui.html.call_args.args[0])
        self.assertIn('return_room=trustworthiness', ui.html.call_args.args[0])

    def test_markup_prints_return_and_accessible_controls(self):
        markup = room_markup(self.data,"<nav>Trustworthiness</nav>","test-shell")
        self.assertIn('href="?room=trustworthiness"',markup)
        self.assertIn('role="status"',markup)
        self.assertIn('aria-labelledby="fpr-dialog-title"',markup)
        self.assertIn('class="fpr-dialog-context"',markup)
        self.assertIn('aria-label="Close portrait evidence"',markup)
        for key in ("clean","damaged","restored","difference","control"):
            self.assertIn('data-canvas="'+key+'"',markup)
        self.assertIn('aria-label="Rendered lightness metric"',markup)
        self.assertIn('aria-label="Hand penalty metric"',markup)
        self.assertIn('Rendered L* is not race or identity.',markup)
        self.assertIn('Matched controls',markup)
        for frame in ("upper", "middle", "lower", "right", "anatomy"):
            self.assertIn('fpr-frame-'+frame, markup)
        for plaque in ("screened", "regions", "cases", "paintings", "reviews"):
            self.assertIn('fpr-formation-'+plaque, markup)
        for book in ("screening", "anatomy", "controls", "review"):
            self.assertIn('fpr-book-'+book, markup)


if __name__ == "__main__": unittest.main()
