"""Evidence and scope regressions for the isolated Stability Lab preview."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from restoration_eval.stability_lab import (test_catalogue, selection, seed_catalogue,
    seed_candidates, seed_options, group_for_case, payload, metric, catalogue, MAIN_MODELS,
    FAMILIES, ROOT, CONDITIONS, EVIDENCE)


class StabilityLabTests(unittest.TestCase):
    def test_decorative_book_spines(self):
        from restoration_eval.stability_lab_view import book_spines
        from html.parser import HTMLParser

        class SpineParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.titles = []
                self.icons = 0

            def handle_starttag(self, tag, attrs):
                if tag == "img":
                    self.icons += 1
                    self_attrs = dict(attrs)
                    assert self_attrs["alt"] == ""
                    assert self_attrs["src"].startswith("data:image/svg+xml;base64,")

            def handle_data(self, data):
                self.titles.append(data)

        parser = SpineParser()
        parser.feed(book_spines())
        self.assertEqual(parser.titles, ["Dune", "Dune Messiah", "Children of Dune",
            "God Emperor of Dune", "ChapterHouse Dune", "Hunters of Dune", "Sandworms of Dune"])
        self.assertEqual(parser.icons, 7)

    def test_painting_note_claim_is_selection_specific(self):
        from restoration_eval.stability_lab_view import painting_note
        opening={"test":"size","painting":"p018","model":"lama","evidence":"spatial_masked_error"}
        self.assertIn("Steepest observed",painting_note(opening))
        for update in ({"painting":"p001"},{"model":"hint_places2"},{"evidence":"crop_ssim"}):
            self.assertNotIn("Steepest",painting_note(opening | update))
        self.assertIn("Water stain",painting_note(opening | {"test":"degradation","family":"water_stain"}))
        self.assertIn("Four seeds",painting_note(opening | {"test":"seed"}))

    def test_declared_default(self):
        s = selection({})
        self.assertEqual((s["painting"],s["test"],s["model"],s["evidence"]), ("p018","size","lama","spatial_masked_error"))
        self.assertEqual(s["labels"], ["2%","4%","6%","8%","10%","15%","20%"])
        self.assertTrue(s["selected"].endswith("size_20pct"))

    def test_source_populations(self):
        cat=test_catalogue()
        self.assertEqual(len(cat["paintings"]),35)
        self.assertEqual(len(cat["size"]),245)
        self.assertEqual(len(cat["mask"]),525)
        self.assertEqual(len(cat["degradation"]),1155)
        self.assertEqual(sum(r["degradation_family"] in FAMILIES for r in cat["degradation"]),350)

    def test_every_primary_candidate_exists(self):
        c=test_catalogue(); primary=catalogue()["models"]
        cases=c["size"]+c["mask"]+[r for r in c["degradation"] if r["degradation_family"] in FAMILIES]
        for row in cases:
            for model in MAIN_MODELS:
                candidate=primary[model][row["case_id"]]
                self.assertTrue(Path(candidate["resolved_path"]).is_file(), candidate["resolved_path"])
                for evidence in EVIDENCE:
                    self.assertIsNotNone(metric(candidate["candidate_id"],evidence)["value"],(candidate["candidate_id"],evidence))

    def test_all_focused_selectors_are_complete(self):
        for painting in test_catalogue()["paintings"]:
            self.assertEqual(len(selection({"stability_painting":painting})["rows"]),7)
            for condition in CONDITIONS:
                rows=selection({"stability_painting":painting,"stability_test":"mask","stability_condition":condition})["rows"]
                self.assertEqual(len(rows),5)
                self.assertEqual(len({r["robustness_group_id"] for r in rows}),1)
            for family in FAMILIES:
                rows=selection({"stability_painting":painting,"stability_test":"degradation","stability_family":family})["rows"]
                self.assertEqual(len(rows),1 if family=="water_stain_dirt" else 3)

    def test_rejects_invalid_scope(self):
        for query in ({"stability_test":"seed"},{"stability_painting":"p002"},
                      {"stability_case":"canonical__p018__mixed_damage"},
                      {"stability_family":"gaussian_blur"},{"stability_evidence":"combined_score"},
                      {"stability_model":"sdxl_inpainting"},{"stability_test":"unknown"}):
            with self.assertRaises(ValueError): selection(query)

    def test_opening_trajectory_golden_values(self):
        expected=[4.1318695438,6.3067950775,9.6465636489,9.5337827707,13.2004297422,30.9869134483,39.3301701445]
        c=catalogue()["models"]["lama"]
        for row,value in zip(selection({})["rows"],expected):
            self.assertAlmostEqual(metric(c[row["case_id"]]["candidate_id"],"spatial_masked_error")["value"],value,places=8)

    def test_seed_membership_is_exact(self):
        groups=seed_catalogue(); candidates=seed_candidates()
        self.assertEqual(len(groups),1025)
        self.assertEqual(sum(len(g["pairs"]) for g in groups.values()),6150)
        for group in groups.values():
            self.assertEqual(set(group["members"]),{2026,2027,2028,2029})
            self.assertEqual(len(group["pairs"]),6)
            for seed,cid in group["members"].items():
                row=candidates[cid]
                self.assertEqual((row["seed"],row["case_id"],row["prompt_variant_id"]),(seed,group["case_id"],group["prompt"]))
                self.assertTrue(Path(row["resolved_path"]).is_file())

    def test_prompt_groups_are_not_merged(self):
        groups=[g for g in seed_options("p018") if g["case_id"]=="canonical__p018__scratch_thin"]
        self.assertEqual({g["prompt"] for g in groups},{"p00_generic","p05_scratch_aware"})
        self.assertEqual(len({g["id"] for g in groups}),2)

    def test_damage_seed_overlays_exist(self):
        import pandas as pd
        folder=ROOT / "outputs/22_damage_size_diffusion_uncertainty_extension"
        rows=pd.read_csv(folder / "manifests/map_images.csv")
        self.assertEqual(len(rows),245)
        self.assertEqual(rows.uncertainty_group_id.nunique(),245)
        for row in rows.itertuples():
            self.assertTrue((folder / row.relative_path).is_file())

    def test_default_disabled_and_explicit_seed_payload(self):
        p=payload({});self.assertIsNone(p["seed"])
        self.assertEqual(len(p["mask_previews"]),5)
        p=payload({"stability_model":"stable_diffusion_inpainting","stability_test":"seed"})
        self.assertEqual(p["seed"]["id"],"ug_1de955f7e0f3d00cf0")
        self.assertEqual(len(p["seed"]["members"]),4)
        self.assertTrue(p["seed"]["overlay"].startswith("data:image/png;base64,"))
        self.assertEqual(p["content_bbox"],[0,130,768,637])

    def test_p05_uses_the_exact_group_candidate(self):
        group=next(g for g in seed_options("p018") if g["prompt"]=="p05_scratch_aware")
        p=payload({"stability_test":"seed","stability_model":"stable_diffusion_inpainting","stability_group":group["id"]})
        self.assertEqual(p["current"]["candidate_id"],group["members"][2026])
        self.assertIsNone(p["seed"]["overlay"])


if __name__ == "__main__":
    unittest.main()
