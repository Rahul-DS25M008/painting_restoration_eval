"""Scientific boundary checks for the supplemental real-damage input contract."""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.manifests import sha256_file
from restoration_eval.masks import calculate_mask_morphology
from restoration_eval.paths import find_project_root
from restoration_eval.real_damage_dataset import (
    PREFLIGHT_STAGE,
    SOURCE_AUDIT_STAGE,
    SMOKE_STAGE,
    audit_inference_mask,
    audit_inventory_inputs,
    audit_real_damage_sources,
    load_approved_sources,
    load_real_damage_config,
    resolve_real_damage_paths,
    run_real_damage_smoke,
    validate_approved_sources,
    validate_binary_damage_mask,
    validate_real_damage_config,
    validate_real_damage_preflight,
    validate_review_binding,
    validate_source_snapshot,
    normalize_real_damage_source,
)
from restoration_eval.validation import ValidationCollector


class RealDamageContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = find_project_root(Path(__file__))
        cls.config_path = cls.root / "config/datasets/real_damage_10.yaml"
        cls.config = load_real_damage_config(cls.config_path)
        cls.catalog = load_approved_sources(cls.root / cls.config["inputs"]["approved_sources"], cls.config)

    def test_approved_sources_and_guarded_paths(self):
        inputs, outputs = resolve_real_damage_paths(self.root, self.config, self.catalog, config_path=self.config_path)
        self.assertTrue(all(p.is_file() for p in inputs.values()))
        self.assertEqual(len(outputs), 17)
        self.assertEqual(len(self.catalog["records"]), 10)
        self.assertTrue(all(".local_work" not in p.parts for p in inputs.values()))

    def test_fake_clean_reference_is_rejected(self):
        for changes in ({"has_clean_reference": True}, {"clean_image_path": "damaged.jpg"}):
            catalog = copy.deepcopy(self.catalog)
            catalog["records"][0].update(changes)
            with self.assertRaisesRegex(ValueError, "clean reference"):
                validate_approved_sources(catalog, self.config)

    def test_unbalanced_or_duplicate_sources_are_rejected(self):
        catalog = copy.deepcopy(self.catalog)
        catalog["records"][0]["category"] = "landscape_natural"
        with self.assertRaisesRegex(ValueError, "balanced"):
            validate_approved_sources(catalog, self.config)
        catalog = copy.deepcopy(self.catalog)
        catalog["records"][1]["raw_sha256"] = catalog["records"][0]["raw_sha256"]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_approved_sources(catalog, self.config)

    def test_configuration_cannot_enable_reference_or_mask_repairs(self):
        for section, key in [("dataset", "has_clean_reference"), ("annotation", "automatic_dilation_allowed"), ("annotation", "padding_overlap_allowed")]:
            config = copy.deepcopy(self.config)
            config[section][key] = True
            with self.assertRaises(ValueError):
                validate_real_damage_config(config)

    def test_output_cannot_escape_or_depend_on_temporary_sources(self):
        for bad in ("../outside.csv", "D:/outside.csv", ".local_work/masks.csv"):
            config = copy.deepcopy(self.config)
            config["outputs"]["masks"] = bad
            with self.assertRaises(ValueError):
                validate_real_damage_config(config)

    def test_preflight_replaces_its_stage_and_detects_changed_baseline(self):
        inputs, outputs = resolve_real_damage_paths(self.root, self.config, self.catalog, config_path=self.config_path)
        previous = ValidationCollector()
        previous.add(validation_stage="batch_2", check_id="keep", check_description="Keep other batch", severity="blocking", expected=True, observed=True, passed=True)
        inventory = {"inventory_run_id": "unit_fixture", "inventory_sha256": sha256_file(inputs["inventory"])}
        audit = pd.DataFrame([{"input_key": "fixture", "details": "", "passed": True}])
        with patch("restoration_eval.real_damage_dataset.audit_inventory_inputs", return_value=(inventory, audit)):
            first = validate_real_damage_preflight(self.root, self.config, self.catalog, inputs, outputs, previous_validation=previous)
            second = validate_real_damage_preflight(self.root, self.config, self.catalog, inputs, outputs, previous_validation=first["validation"])
            self.assertTrue(second["validation"].overall_passed)
            self.assertEqual(first["validation"].summary(), second["validation"].summary())
            self.assertEqual(sum(c.validation_stage == "batch_2" for c in second["validation"].checks), 1)
            catalog = copy.deepcopy(self.catalog)
            rel = self.config["inputs"]["preprocessing_config"]
            catalog["pipeline_baseline_sha256"][rel] = "0" * 64
            changed = validate_real_damage_preflight(self.root, self.config, catalog, inputs, outputs)
            self.assertFalse(changed["validation"].overall_passed)
            self.assertIn(f"{PREFLIGHT_STAGE}:baseline:{rel}", changed["validation"].summary()["failed_check_ids"])

    def test_saved_provenance_accepts_tracking_only_url_difference(self):
        record = self.catalog["records"][0]
        snapshot = json.loads((self.root / record["source_metadata_path"]).read_text(encoding="utf-8"))
        digest = hashlib.sha1((self.root / record["raw_image_path"]).read_bytes()).hexdigest()
        result = validate_source_snapshot(record, snapshot, image_sha1=digest)
        self.assertTrue(result["source_metadata_verified"])

    def test_provenance_rejects_different_image_revision_or_rights(self):
        record = self.catalog["records"][0]
        original = json.loads((self.root / record["source_metadata_path"]).read_text(encoding="utf-8"))
        digest = hashlib.sha1((self.root / record["raw_image_path"]).read_bytes()).hexdigest()
        for mutation in ("image", "revision", "rights"):
            snapshot = copy.deepcopy(original)
            page = snapshot["query"]["pages"][str(record["source_page_id"])]
            if mutation == "image":
                page["imageinfo"][0]["url"] = "https://upload.wikimedia.org/different.jpg"
            elif mutation == "revision":
                page["revisions"][0]["revid"] += 1
            else:
                page["imageinfo"][0]["extmetadata"]["Copyrighted"]["value"] = "True"
            with self.assertRaises(ValueError):
                validate_source_snapshot(record, snapshot, image_sha1=digest)

    def test_source_audit_retains_reference_absence_and_is_rerunnable(self):
        inputs, _ = resolve_real_damage_paths(self.root, self.config, self.catalog, config_path=self.config_path)
        prior = ValidationCollector()
        prior.add(validation_stage=PREFLIGHT_STAGE, check_id="keep", check_description="Retain preflight", severity="blocking", expected=True, observed=True, passed=True)
        result = audit_real_damage_sources(self.root, self.config, self.catalog, inputs, previous_validation=prior)
        self.assertTrue(result["validation"].overall_passed, result["validation"].summary())
        self.assertEqual(len(result["artworks"]), 10)
        self.assertTrue(result["artworks"]["clean_image_path"].isna().all())
        self.assertTrue(result["artworks"]["has_clean_reference"].eq(False).all())
        self.assertTrue(result["artworks"]["raw_exif_orientation"].eq(1).all())
        self.assertTrue(result["artworks"]["colour_policy"].isin({"assume_srgb_no_pixel_conversion", "preserve_pixels_strip_profile", "convert_embedded_profile_to_srgb"}).all())
        self.assertEqual(result["artworks"].set_index("painting_id").loc["rd010", "source_normalization"], "drop_fully_opaque_alpha_rgb_unchanged")
        self.assertTrue(result["artworks"]["source_metadata_verified"].all())
        repeated = audit_real_damage_sources(self.root, self.config, self.catalog, inputs, previous_validation=result["validation"])
        self.assertEqual(result["validation"].summary(), repeated["validation"].summary())
        pd.testing.assert_frame_equal(result["artworks"], repeated["artworks"])

    def test_source_audit_keeps_failed_decode_visible(self):
        from restoration_eval.dataset_verification import ImageAuditResult, audit_image_collection
        inputs, _ = resolve_real_damage_paths(self.root, self.config, self.catalog, config_path=self.config_path)

        def failed_decode(*args, **kwargs):
            result = audit_image_collection(*args, **kwargs)
            rows = result.images.copy()
            rows.loc[0, ["image_loaded", "image_verified"]] = False
            rows.loc[0, ["raw_sha256", "raw_dhash64"]] = pd.NA
            rows.loc[0, "issue"] = "load_failed:test_failure"
            return ImageAuditResult(rows, result.exact_duplicate_groups, result.near_duplicate_candidates, result.orphan_image_paths)

        with patch("restoration_eval.dataset_verification.audit_image_collection", side_effect=failed_decode):
            result = audit_real_damage_sources(self.root, self.config, self.catalog, inputs)
        self.assertFalse(result["validation"].overall_passed)
        self.assertEqual(len(result["artworks"]), 10)
        self.assertEqual(result["artworks"].iloc[0]["acceptance_status"], "blocked")
        self.assertIn("decode:rd001", result["artworks"].iloc[0]["exclusion_reason"])

    def test_cc_attribution_and_met_snapshot_conditions(self):
        for index in (3, 4, 5):
            record = self.catalog["records"][index]
            snapshot = json.loads((self.root / record["source_metadata_path"]).read_text(encoding="utf-8"))
            digest = hashlib.sha1((self.root / record["raw_image_path"]).read_bytes()).hexdigest()
            self.assertTrue(validate_source_snapshot(record, snapshot, image_sha1=digest)["source_metadata_verified"])
            bad = copy.deepcopy(record)
            if index == 5:
                snapshot["isPublicDomain"] = False
            else:
                bad["source_photographer"] = ""
            with self.assertRaises(ValueError):
                validate_source_snapshot(bad, snapshot, image_sha1=digest)
        snapshot["isPublicDomain"] = True
        bad["source_image_url"] = "https://images.metmuseum.org/unrelated.jpg"
        with self.assertRaisesRegex(ValueError, "not in Met"):
            validate_source_snapshot(bad, snapshot, image_sha1=digest)

    def test_opaque_alpha_normalization_preserves_rgb_and_metadata(self):
        source = Image.new("RGBA", (7, 9), (17, 83, 192, 255))
        source.info["icc_profile"] = b"test profile retained for canonical processing"
        result = normalize_real_damage_source(source)
        np.testing.assert_array_equal(np.asarray(result), np.asarray(source)[..., :3])
        self.assertEqual(result.info["icc_profile"], source.info["icc_profile"])
        source.putpixel((1, 1), (17, 83, 192, 254))
        with self.assertRaisesRegex(ValueError, "transparent"):
            normalize_real_damage_source(source)


class RealDamageSmokeTests(unittest.TestCase):
    """Use synthetic fixture sources in a disposable repository, never D03 outputs."""
    def setUp(self):
        from restoration_eval.preprocessing import load_preprocessing_config
        actual = find_project_root(Path(__file__))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for rel in (".git", "src/restoration_eval", "notebooks"):
            (self.root / rel).mkdir(parents=True)
        self.config = load_real_damage_config(actual / "config/datasets/real_damage_10.yaml")
        self.catalog = load_approved_sources(actual / self.config["inputs"]["approved_sources"], self.config)
        for rel in (self.config["inputs"]["preprocessing_config"], "src/restoration_eval/preprocessing.py"):
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((actual / rel).read_bytes())
        self.prep = load_preprocessing_config(self.root / self.config["inputs"]["preprocessing_config"])
        for i, row in enumerate(self.catalog["records"]):
            # Include square, portrait, landscape and odd-padding examples.
            w, h = [(901, 1200), (1600, 1001), (1200, 1200)][i % 3]
            image = Image.new("RGB", (w, h), (20 + i * 16, 40 + i * 6, 130))
            image.paste((200, 80, 30), (w // 4, h // 4, w // 2, h // 2))
            target = self.root / row["raw_image_path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            image.save(target)
            row.update(raw_width=w, raw_height=h, raw_sha256=sha256_file(target), raw_size_bytes=target.stat().st_size)
        self.artworks = pd.DataFrame(self.catalog["records"])
        self.artworks["acceptance_status"] = "accepted"
        self.artworks["raw_exif_orientation"] = 1
        self.artworks["raw_icc_profile_present"] = False
        self.artworks["raw_icc_profile_description"] = ""
        self.artworks["colour_policy"] = "assume_srgb_no_pixel_conversion"
        self.prior = ValidationCollector()
        for stage in (PREFLIGHT_STAGE, SOURCE_AUDIT_STAGE):
            self.prior.add(validation_stage=stage, check_id="fixture", check_description="Synthetic fixture prerequisite", severity="blocking", expected=True, observed=True, passed=True)
        self.output = self.root / "outputs/d03_real_damage_dataset_preparation"

    def run_smoke(self, previous=None):
        return run_real_damage_smoke(self.root, self.config, self.catalog, self.artworks,
                                     self.prep, previous_validation=previous or self.prior)

    def test_same_pixels_as_canonical_pipeline_and_idempotent_smoke_only_writes(self):
        from restoration_eval.preprocessing import build_preprocessed_image
        result = self.run_smoke()
        self.assertTrue(result["validation"].overall_passed, result["validation"].summary())
        self.assertEqual(len(result["images"]), 5)
        self.assertEqual(len(result["images"]["category"].unique()), 5)
        self.assertEqual(result["visual_review_status"], "pending_user_inspection")
        self.assertTrue(result["images"]["clean_image_path"].isna().all())
        files = sorted(p for p in self.output.rglob("*") if p.is_file())
        self.assertEqual(len(files), 6)
        self.assertTrue(all(p.is_relative_to(self.output / "work/preprocessing_smoke") for p in files))
        times = {p: p.stat().st_mtime_ns for p in files}
        source_row = self.artworks.iloc[0].to_dict()
        with Image.open(self.root / source_row["raw_image_path"]) as raw:
            expected, _ = build_preprocessed_image(raw, source_row, self.prep)
        with Image.open(self.root / result["images"].iloc[0]["processed_path"]) as saved:
            np.testing.assert_array_equal(np.asarray(saved), np.asarray(expected))
        repeated = self.run_smoke(result["validation"])
        pd.testing.assert_frame_equal(result["images"], repeated["images"])
        self.assertEqual(result["validation"].summary(), repeated["validation"].summary())
        self.assertEqual(times, {p: p.stat().st_mtime_ns for p in files})
        self.assertEqual(sum(c.validation_stage == SMOKE_STAGE for c in repeated["validation"].checks), 35)

    def test_source_change_blocks_before_any_output(self):
        source = self.root / self.artworks.iloc[4]["raw_image_path"]
        source.write_bytes(source.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "Source changed"):
            self.run_smoke()
        self.assertFalse(self.output.exists())

    def test_stale_output_and_orphans_are_not_overwritten_or_deleted(self):
        directory = self.output / "work/preprocessing_smoke"
        directory.mkdir(parents=True)
        stale = directory / "rd001.png"
        stale.write_bytes(b"stale evidence")
        with self.assertRaisesRegex(ValueError, "Stale smoke output"):
            self.run_smoke()
        self.assertEqual(stale.read_bytes(), b"stale evidence")
        orphan = directory / "old.png"
        orphan.write_bytes(b"orphan evidence")
        with self.assertRaisesRegex(ValueError, "Unexpected smoke files"):
            self.run_smoke()
        self.assertEqual(orphan.read_bytes(), b"orphan evidence")

    def test_wrong_scope_or_stale_config_blocks_before_write(self):
        self.config["smoke"]["directory"] = "images/inputs"
        with self.assertRaisesRegex(ValueError, "Smoke outputs"):
            self.run_smoke()
        self.config["smoke"]["directory"] = "work/preprocessing_smoke"
        self.prep["processing"]["target_width"] = 512
        with self.assertRaisesRegex(ValueError, "Stale preprocessing configuration"):
            self.run_smoke()
        self.assertFalse(self.output.exists())

    def test_reloaded_pixel_corruption_is_detected(self):
        from restoration_eval.real_damage_dataset import _write_smoke_bytes

        def corrupt(path, payload):
            _write_smoke_bytes(path, payload)
            if path.name == "rd001.png":
                with Image.open(path) as image:
                    changed = image.copy()
                changed.putpixel((0, 0), (255, 255, 255))
                changed.save(path)

        with patch("restoration_eval.real_damage_dataset._write_smoke_bytes", side_effect=corrupt):
            result = self.run_smoke()
        self.assertFalse(result["validation"].overall_passed)
        failed = result["validation"].summary()["failed_check_ids"]
        self.assertIn(f"{SMOKE_STAGE}:pixels:rd001", failed)
        self.assertIn(f"{SMOKE_STAGE}:padding:rd001", failed)


class InventoryFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for rel in (".git", "notebooks", "src/restoration_eval", "outputs/inventory"):
            (self.root / rel).mkdir(parents=True, exist_ok=True)
        self.source = self.root / "source.txt"
        self.source.write_bytes(b"aaaa")
        self.inventory = self.root / "outputs/inventory/project_file_inventory.csv"
        self.manifest = self.inventory.parent / "inventory_run.json"
        row = dict(relative_path="source.txt", size_bytes=4, hash_mode="full", hash_algorithm="sha256", hash_bytes_read=4, hash_value=sha256_file(self.source), read_error_count=0, inventory_run_id="test_run")
        with self.inventory.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
        self.manifest.write_text(json.dumps({
            "run_schema_version": "inventory_run.v1", "inventory_schema_version": "project_file_inventory.v1",
            "status": "completed", "inventory_run_id": "test_run",
            "inventory_relative_path": "outputs/inventory/project_file_inventory.csv",
            "inventory_size_bytes": self.inventory.stat().st_size,
            "inventory_sha256": sha256_file(self.inventory), "summary": {"file_count": 1},
        }))
        self.inputs = {"source": self.source, "inventory": self.inventory, "inventory_run": self.manifest}

    def test_self_exclusion_and_same_size_input_change(self):
        _, audit = audit_inventory_inputs(self.root, self.inventory, self.manifest, self.inputs)
        self.assertTrue(audit["passed"].all())
        self.source.write_bytes(b"bbbb")
        _, audit = audit_inventory_inputs(self.root, self.inventory, self.manifest, self.inputs)
        self.assertFalse(audit.loc[audit["input_key"].eq("source"), "passed"].item())

    def test_missing_inventory_entry_and_tampered_inventory(self):
        extra = self.root / "extra.txt"
        extra.write_text("new")
        _, audit = audit_inventory_inputs(self.root, self.inventory, self.manifest, {**self.inputs, "extra": extra})
        self.assertIn("not indexed", audit.loc[audit["input_key"].eq("extra"), "details"].item())
        self.inventory.write_text("broken")
        with self.assertRaisesRegex(ValueError, "size differs"):
            audit_inventory_inputs(self.root, self.inventory, self.manifest, self.inputs)


class RealDamageMaskTests(unittest.TestCase):
    def test_mask_rejects_padding_nonbinary_and_empty(self):
        box = (50, 20, 700, 740)
        valid = np.zeros((768, 768), dtype=np.uint8)
        valid[100:120, 100:130] = 255
        self.assertEqual(validate_binary_damage_mask(valid, content_box=box).sum(), 600)
        for value, match in ((0, "empty"), (127, "only 0 and 255")):
            bad = np.zeros_like(valid)
            bad[100, 100] = value
            with self.assertRaisesRegex(ValueError, match):
                validate_binary_damage_mask(bad, content_box=box)
        valid[0, 0] = 255
        with self.assertRaisesRegex(ValueError, "padding"):
            validate_binary_damage_mask(valid, content_box=box)

    def test_thin_crack_can_disappear_without_dilation(self):
        tiny = np.zeros((768, 768), dtype=np.uint8)
        tiny[1, 1] = 255
        audit = audit_inference_mask(tiny, content_box=(0, 0, 768, 768))
        self.assertTrue(audit["empty_inference_mask"])
        self.assertEqual(audit["disappeared_component_count"], 1)
        self.assertEqual(tiny.sum(), 255)

    def test_scale_sampling_matches_binary_resize_and_component_policy(self):
        mask = np.zeros((768, 768), dtype=np.uint8)
        mask[150:230, 100:190] = 255
        mask[400, 400] = mask[401, 401] = 255
        audit = audit_inference_mask(mask, content_box=(0, 0, 768, 768))
        direct = np.asarray(Image.fromarray(mask).resize((512, 512), Image.Resampling.NEAREST)) > 0
        self.assertEqual(audit["inference_mask_pixels"], direct.sum())
        geometry = calculate_mask_morphology(mask, content_box=(0, 0, 768, 768))
        self.assertEqual(audit["source_component_count"], geometry["connected_component_count"])

    def test_review_does_not_survive_mask_modification(self):
        with tempfile.TemporaryDirectory() as folder:
            image, mask = Path(folder) / "input.png", Path(folder) / "mask.png"
            image.write_bytes(b"test input")
            mask.write_bytes(b"reviewed mask")
            review = {"review_status": "approved", "reviewer": "reviewer", "reviewed_at_utc": "2026-11-14T21:00:00Z", "target_description": "visible loss", "input_sha256": sha256_file(image), "mask_sha256": sha256_file(mask)}
            validate_review_binding(review, input_path=image, mask_path=mask)
            mask.write_bytes(b"changed mask")
            with self.assertRaisesRegex(ValueError, "mask changed"):
                validate_review_binding(review, input_path=image, mask_path=mask)


if __name__ == "__main__":
    unittest.main()
