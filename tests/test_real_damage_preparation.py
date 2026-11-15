"""D03 preparation tests use disposable synthetic sources, not notebook execution."""
import copy
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

import test_real_damage_dataset as fixtures
from restoration_eval.manifests import sha256_file
from restoration_eval.preprocessing import build_preprocessed_image
from restoration_eval.real_damage_dataset import load_approved_sources, load_real_damage_config, resolve_real_damage_paths
from restoration_eval.real_damage_preparation import (
    PREPARATION_STAGE, _png_bytes, build_assisted_damage_mask,
    prepare_real_damage_inputs, refresh_preparation_context,
)
from restoration_eval.paths import find_project_root
from restoration_eval.validation import ValidationCollector


class CandidateMaskTests(unittest.TestCase):
    def test_reviewed_raster_keeps_exact_pixels_and_rejects_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in (".git", "src/restoration_eval", "notebooks"):
                (root / relative).mkdir(parents=True)
            path = root / "selected.png"
            mask = Image.new("L", (768, 768), 0)
            mask.paste(255, (230, 250, 240, 260))
            mask.save(path)
            record = {"reviewed_mask_path": "selected.png", "reviewed_mask_sha256": sha256_file(path)}
            image = Image.new("RGB", (768, 768))
            result = build_assisted_damage_mask(image, record, content_box=(100, 100, 700, 700), project_root=root)
            np.testing.assert_array_equal(np.asarray(result), np.asarray(mask))
            mask.putpixel((250, 250), 255)
            mask.save(path)
            with self.assertRaisesRegex(ValueError, "checksum changed"):
                build_assisted_damage_mask(image, record, content_box=(100, 100, 700, 700), project_root=root)

    def test_ridge_rules_select_defects_without_changing_input(self):
        array = np.full((768, 768, 3), 100, dtype=np.uint8)
        array[200:202, 210:260] = 230
        array[300:302, 210:260] = 20
        image = Image.fromarray(array)
        record = {"regions": [
            {"polygon_xy": [[205, 195], [265, 195], [265, 205], [205, 205]], "selector": "bright_ridge", "window": 7, "contrast_min": 30, "min_component_pixels": 3},
            {"polygon_xy": [[205, 295], [265, 295], [265, 305], [205, 305]], "selector": "dark_ridge", "window": 7, "contrast_min": 30, "min_component_pixels": 3},
        ]}
        mask = build_assisted_damage_mask(image, record, content_box=(50, 50, 700, 700))
        expected = np.zeros((768, 768), dtype=np.uint8)
        expected[200:202, 210:260] = 255
        expected[300:302, 210:260] = 255
        np.testing.assert_array_equal(np.asarray(mask), expected)
        np.testing.assert_array_equal(np.asarray(image), array)

    def test_mask_must_not_cover_padding_or_be_empty(self):
        image = Image.new("RGB", (768, 768), (80, 80, 80))
        record = {"regions": [{"polygon_xy": [[1, 1], [8, 1], [8, 8]], "selector": "polygon"}]}
        with self.assertRaisesRegex(ValueError, "padding"):
            build_assisted_damage_mask(image, record, content_box=(50, 50, 700, 700))
        record["regions"][0].update(selector="colour", r_min=240)
        with self.assertRaisesRegex(ValueError, "empty"):
            build_assisted_damage_mask(image, record, content_box=(0, 0, 768, 768))


class FullPreparationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.RealDamageSmokeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        f.artworks["dataset_sort_index"] = range(1, 11)
        self.smoke = f.run_smoke()
        recipe = {"schema_version": "real_damage_annotation_recipe.v1", "recipe_version": "fixture",
                  "coordinate_space": "preprocessed_768_canvas", "automatic_dilation": False,
                  "all_visible_damage_covered": False, "annotation_method": "synthetic_fixture",
                  "prepared_by": "unit_test", "records": []}
        for source in f.artworks.to_dict("records"):
            with Image.open(f.root / source["raw_image_path"]) as raw:
                canvas, _ = build_preprocessed_image(raw, source, f.prep)
            import hashlib
            recipe["records"].append({"painting_id": source["painting_id"],
                "source_sha256": source["raw_sha256"], "processed_sha256": hashlib.sha256(_png_bytes(canvas)).hexdigest(),
                "review_status": "pending", "target_description": "Synthetic fixture target",
                "selection_notes": "Not research evidence",
                "regions": [{"polygon_xy": [[330, 330], [350, 330], [350, 350], [330, 350]], "selector": "polygon"}]})
        self.recipe_path = f.root / f.config["inputs"]["annotation_recipe"]
        self.recipe_path.parent.mkdir(parents=True, exist_ok=True)
        self.recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
        self.preview_patch = patch("restoration_eval.real_damage_preparation.candidate_review_preview", return_value=_png_bytes(Image.new("RGB", (20, 20), "white")))
        self.preview_patch.start()
        self.addCleanup(self.preview_patch.stop)

    def prepare(self, previous=None):
        f = self.fixture
        return prepare_real_damage_inputs(f.root, f.config, f.catalog, f.artworks, f.prep,
                                         self.smoke["images"], previous_validation=previous or self.smoke["validation"])

    def test_full_preparation_and_repeat_preserve_images_and_pending_review(self):
        result = self.prepare()
        self.assertTrue(result["validation"].overall_passed, result["validation"].summary())
        self.assertEqual(sum(c.validation_stage == PREPARATION_STAGE for c in result["validation"].checks), 63)
        self.assertEqual(len(result["preprocessed_images"]), 10)
        self.assertEqual(len(result["mask_candidates"]), 10)
        self.assertTrue(result["mask_candidates"]["review_status"].eq("pending").all())
        self.assertTrue(result["preprocessed_images"]["clean_image_path"].isna().all())
        self.assertFalse((self.fixture.output / "images/masks").exists())
        files = [p for p in self.fixture.output.rglob("*") if p.is_file()]
        self.assertEqual(len(files), 40)  # six smoke + ten inputs + 24 preparation files
        times = {p: p.stat().st_mtime_ns for p in files}
        repeated = self.prepare(result["validation"])
        self.assertEqual(result["validation"].summary(), repeated["validation"].summary())
        self.assertEqual(times, {p: p.stat().st_mtime_ns for p in files})

    def test_mismatched_recipe_blocks_before_inputs_are_written(self):
        recipe = json.loads(self.recipe_path.read_text())
        recipe["records"][4]["processed_sha256"] = "0" * 64
        self.recipe_path.write_text(json.dumps(recipe))
        with self.assertRaisesRegex(ValueError, "different processed image"):
            self.prepare()
        self.assertFalse((self.fixture.output / "images/inputs").exists())

    def test_candidate_edits_are_preserved_and_block_replacement(self):
        directory = self.fixture.output / "work/annotation_candidates/masks"
        directory.mkdir(parents=True)
        edited = directory / "rd001.png"
        edited.write_bytes(b"manual revision must not be overwritten")
        with self.assertRaisesRegex(ValueError, "Existing file differs"):
            self.prepare()
        self.assertEqual(edited.read_bytes(), b"manual revision must not be overwritten")
        self.assertFalse((self.fixture.output / "images/inputs").exists())


class ContextRefreshTests(unittest.TestCase):
    def test_refresh_retains_prior_evidence_but_rejects_scientific_drift(self):
        root = find_project_root(Path(__file__))
        path = root / "config/datasets/real_damage_10.yaml"
        config = load_real_damage_config(path)
        catalog = load_approved_sources(root / config["inputs"]["approved_sources"], config)
        inputs, _ = resolve_real_damage_paths(root, config, catalog, config_path=path)
        checksums = {key: sha256_file(inputs[key]) for key in ("approved_sources", "preprocessing_config", "source_image.rd001")}
        prior = ValidationCollector()
        with patch("restoration_eval.real_damage_preparation.validate_real_damage_preflight", return_value={"validation": prior}):
            result = refresh_preparation_context(root, path, previous_config=config, previous_input_checksums=checksums, previous_validation=prior)
            self.assertIs(result["validation"], prior)
            downstream_update = dict(checksums, **{"helper_sources.real_damage_preparation": "0" * 64})
            refreshed = refresh_preparation_context(root, path, previous_config=config, previous_input_checksums=downstream_update, previous_validation=prior)
            self.assertIs(refreshed["validation"], prior)
            upstream_update = dict(checksums, **{"helper_sources.real_damage_dataset": "0" * 64})
            with self.assertRaisesRegex(ValueError, "Earlier scientific input changed"):
                refresh_preparation_context(root, path, previous_config=config, previous_input_checksums=upstream_update, previous_validation=prior)
            stale = dict(checksums, preprocessing_config="0" * 64)
            with self.assertRaisesRegex(ValueError, "Earlier scientific input changed"):
                refresh_preparation_context(root, path, previous_config=config, previous_input_checksums=stale, previous_validation=prior)
            old_config = copy.deepcopy(config)
            old_config["preprocessing"]["canvas_width"] = 512
            with self.assertRaisesRegex(ValueError, "Earlier batch policy changed"):
                refresh_preparation_context(root, path, previous_config=old_config, previous_input_checksums=checksums, previous_validation=prior)


if __name__ == "__main__":
    unittest.main()
