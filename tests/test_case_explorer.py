"""Bounded step-3 checks: identities, saved values, availability and routes."""
import json
from pathlib import Path
import unittest

from restoration_eval.case_explorer import (
    OPENING, ROOT, payload, select_record, candidate_metrics, layer_state,
    reports_for, review_route, retrieval_rows, saved_panels, asset_uri,
    source_table, random_candidate, counterfactual_choices,
)
from restoration_eval.dashboard_application import open_dashboard_package
from restoration_eval.case_explorer_view import room_markup


class CaseExplorerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = open_dashboard_package(ROOT)
        cls.shard, cls.candidate, cls.case = select_record(cls.package)

    def test_opening_identity_and_exact_rows(self):
        self.assertEqual(self.candidate["candidate_id"], OPENING)
        expected = [(52.962928771972656,4.066130638122559),
                    (0.40980759263038635,0.019120559096336365),
                    (0.8827221511372411,0.9685581155347863)]
        for item, values in zip(candidate_metrics("p018",self.candidate),expected):
            row=item["record"]
            self.assertEqual((float(row["damaged_value"]),float(row["restored_value"])),values)
            self.assertEqual(row["candidate_id"],OPENING)
            self.assertTrue(row["source_sha256"])
        self.assertEqual(self.candidate["insufficient_flag_ids"],["colour_inconsistency"])

    def test_all_five_opening_images_verified(self):
        data=payload(self.package)
        self.assertEqual(len(data["images"]),5)
        for key,item in data["images"].items():
            self.assertTrue(item["uri"],(key,item["reason"]))

    def test_layers_are_distinct_saved_candidate_routes(self):
        paths=[]
        for key in ("difference","seam","colour","texture","semantic"):
            data=payload(self.package,layer=key)
            self.assertTrue(data["images"]["evidence"]["uri"],data["images"]["evidence"]["reason"])
            paths.append(data["images"]["evidence"]["path"])
        self.assertEqual(len(set(paths)),5)

    def test_deterministic_uncertainty_not_zero(self):
        state=layer_state(self.candidate,"uncertainty")
        self.assertFalse(state["available"])
        self.assertIn("Not applicable",state["reason"])
        self.assertIsNone(payload(self.package,layer="uncertainty")["images"]["evidence"]["uri"])
        for model in ("opencv_telea","hint_places2"):
            candidate=next(c for c in self.shard["candidates"] if c["model_id"]==model)
            self.assertIn("deterministic",layer_state(candidate,"uncertainty")["reason"])

    def test_exact_review_route(self):
        review=next(r for r in source_table("outputs/d02_portrait_skin_tone_and_hand_restoration_audit/data/manual_anatomy_review.csv") if r["blind_review_code"]=="R005")
        _,candidate,_=select_record(self.package,review["painting_id"],review["candidate_id"])
        self.assertEqual(review_route(candidate),"R005")

    def test_no_identity_or_map_substitution(self):
        with self.assertRaises(ValueError):
            select_record(self.package,"p018","candidate__lama__canonical__p001__mixed_damage__c00")
        with self.assertRaises(ValueError):
            payload(self.package,image_path="outputs/arbitrary.png")
        with self.assertRaises(ValueError):
            payload(self.package,layer="invented")

    def test_other_model_and_diffusion_seed_remain_exact(self):
        alternatives=[next(c for c in self.shard["candidates"] if c["case_id"]==self.case["case_id"] and c["model_id"]!="lama"),
                      next(c for c in self.shard["candidates"] if c.get("prompt_variant_id") and c.get("seed") is not None),
                      next(c for c in self.shard["candidates"] if c["experiment_id"]=="synthetic_degradation")]
        for candidate in alternatives:
            _,chosen,case=select_record(self.package,"p018",candidate["candidate_id"])
            self.assertEqual(chosen,candidate)
            self.assertEqual(case["case_id"],candidate["case_id"])
            for item in candidate_metrics("p018",candidate):
                if item["record"]:
                    self.assertEqual(item["record"]["candidate_id"],candidate["candidate_id"])
            data=payload(self.package,"p018",candidate["candidate_id"])
            for key in ("clean","damaged","mask","restored"):
                self.assertTrue(data["images"][key]["uri"],(key,data["images"][key]["reason"]))

    def test_exact_report_availability(self):
        report=reports_for(self.shard,self.case["case_id"])
        self.assertEqual(report["case"]["case_id"],self.case["case_id"])
        self.assertIsNotNone(report["painting"])
        selected={r["case_id"] for r in self.shard["reports"]["selected_cases"]}
        other=next(c for c in self.shard["cases"] if c["case_id"] not in selected)
        self.assertIsNone(reports_for(self.shard,other["case_id"])["case"])
        self.assertIsNone(review_route(self.candidate))

    def test_retrieval_and_counterfactual_population(self):
        rows=retrieval_rows()
        self.assertEqual(len(rows),100)
        for query in {r["query_id"] for r in rows}:
            selected=[r for r in rows if r["query_id"]==query]
            self.assertEqual(len(selected),10)
            for lane in {r["lane"] for r in selected}:
                self.assertEqual(sum(r["lane"]==lane for r in selected),5)
        self.assertEqual(len(saved_panels(self.package,"counterfactual_panels")),14)
        self.assertEqual(len(saved_panels(self.package,"example_retrieval_panels")),10)

    def test_room_has_explicit_limits_and_enabled_exact_reports(self):
        markup=room_markup(payload(self.package),"","shell.png")
        self.assertIn("Missing is not a pass",markup)
        self.assertIn("Not applicable — deterministic method",markup)
        self.assertIn('data-action="report:case"',markup)
        self.assertEqual(markup.count('class="ce-print"'),5)

    def test_reference_control_families_and_shared_thumbnail_source(self):
        data=payload(self.package)
        data["retrieval_sheet_uri"]="data:image/png;base64,registered-sheet"
        markup=room_markup(data,"","shell.png")
        for action in ("category","painting","experiment","damage","model","candidate"):
            self.assertIn(f'data-action="catalogue:{action}"',markup)
        for family in ("damage_size","mask_placement","cross_model","metric_subset","diffusion_seed","prompt_policy","evidence_family_removal"):
            self.assertIn(f'data-action="counterfactual:{family}"',markup)
        self.assertEqual(markup.count('class="ce-neighbour-mini"'),10)
        self.assertEqual(markup.count("registered-sheet"),1)
        self.assertIn("not this case",markup)
        self.assertIn('data-action="sources"',markup)
        self.assertIn('aria-labelledby="ce-dialog-title"',markup)
        for lane in ('lower_risk','flagged'):
            for rank in range(1,6):
                self.assertIn(f'data-action="neighbour:{lane}:{rank}"',markup)

    def test_random_completion_returns_an_exact_existing_candidate(self):
        cid=random_candidate(self.package,'p001',chooser=lambda rows:rows[-1])
        _,candidate,case=select_record(self.package,'p001',cid)
        self.assertEqual(candidate['candidate_id'],cid)
        self.assertEqual(candidate['case_id'],case['case_id'])

    def test_reference_lettering_preserves_accessible_controls(self):
        markup=room_markup(payload(self.package),"","shell.png","approved-lettering.png")
        self.assertEqual(markup.count('src="approved-lettering.png"'),1)
        self.assertEqual(markup.count('class="ce-reference-window"'),15)
        self.assertEqual(markup.count('ce-reference-window ce-static-art'),6)
        self.assertNotIn('Framed detail views',markup)
        for action in ('report:painting','report:case','sources','metrics','portrait','surprise','record'):
            self.assertIn(f'data-action="{action}"',markup)
        for name in ('category','painting','experiment','damage','model','candidate'):
            self.assertIn(f'aria-label="Select {name}"',markup)
        for name in ('cases','metrics','flags','records'):
            self.assertIn(f'aria-label="Open {name}"',markup)
        import hashlib
        from restoration_eval.case_explorer import ROOT
        source=ROOT/'docs/dashboard_design_finalists/approved_current/10_case_explorer_final.png'
        bundled=ROOT/'streamlit_assets/rooms/case_explorer_lettering.png'
        self.assertEqual(hashlib.sha256(source.read_bytes()).digest(),hashlib.sha256(bundled.read_bytes()).digest())

    def test_compact_diffusion_ledger_labels_and_neutral_layer_patch(self):
        from copy import deepcopy
        from html.parser import HTMLParser
        class ModelCells(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_model=False
                self.cells=[]
            def handle_starttag(self,tag,attrs):
                if tag=='small' and 'title' in dict(attrs):
                    self.in_model=True
            def handle_endtag(self,tag):
                if tag=='small':
                    self.in_model=False
            def handle_data(self,text):
                if self.in_model:
                    self.cells.append(text)
        for model,expected in [('stable_diffusion_inpainting','SD'),('sdxl_inpainting','SDXL')]:
            data=deepcopy(payload(self.package))
            data['candidate']['model_id']=model
            markup=room_markup(data,'','shell.png','lettering.png','neutral.png')
            cells=ModelCells()
            cells.feed(markup)
            self.assertEqual(cells.cells,[expected]*3)
            self.assertIn(f'>{expected} Restoration</button>',markup)
            self.assertIn('class="ce-neutral-layer"',markup)
            self.assertIn('background-image:url(neutral.png)',markup)

    def test_each_comparison_choice_is_bound_to_its_saved_candidate(self):
        rows=counterfactual_choices()
        self.assertEqual(len({r['family'] for r in rows}),7)
        keys=[(r['family'],r['value'],r['candidate_id'],r['panel_path']) for r in rows]
        self.assertEqual(len(keys),len(set(keys)))
        for row in rows:
            _,candidate,case=select_record(self.package,row['painting_id'],row['candidate_id'])
            self.assertEqual(case['case_id'],row['case_id'])
            self.assertEqual(candidate['model_id'],row['model_id'])
            self.assertIn(row['panel_path'],saved_panels(self.package,'counterfactual_panels'))
            if row['family']=='damage_size':
                self.assertEqual(float(row['value']),float(case['target_damage_fraction']))
            elif row['family']=='diffusion_seed':
                self.assertEqual(row['value'],str(candidate['seed']))
            elif row['family']=='prompt_policy':
                self.assertEqual(row['value'],candidate['prompt_variant_id'])
            elif 'record' in row:
                self.assertEqual(row['record']['candidate_id'],row['candidate_id'])
                self.assertEqual(row['record']['scenario_id'],row['value'])

    def test_content_crop_is_recorded_and_inspection_remains_full_image(self):
        data=payload(self.package)
        self.assertEqual(len(data["content_bbox"]),4)
        x0,y0,x1,y1=data["content_bbox"]
        self.assertTrue(0<=x0<x1<=768)
        self.assertTrue(0<=y0<y1<=768)
        for key in ("clean","damaged","mask","restored","evidence"):
            self.assertIn(f'data-action="compare:{key}"',room_markup(data,"","shell.png"))

    def test_every_original_study_panel_is_present_and_verified(self):
        for folder in ("example_retrieval_panels","counterfactual_panels"):
            for path in saved_panels(self.package,folder):
                self.assertTrue(asset_uri(self.package,path).startswith("data:image/"),path)


if __name__ == "__main__":
    unittest.main()
