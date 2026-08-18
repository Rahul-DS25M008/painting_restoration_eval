from __future__ import annotations

import copy
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.damage import (
    DAMAGE_MODULE_VERSION,
    _copy_file_atomic,
    _expected_output_path,
    _remove_stale_files,
    apply_mask_damage,
    load_damage_config,
    resolve_damage_inputs,
    select_representative_cases,
    validate_canonical_damage_handoff,
    validate_damage_config,
    validate_saved_damage_dataset,
)
from restoration_eval.manifests import sha256_file
from restoration_eval.paths import find_project_root
from restoration_eval.schemas import (
    CANONICAL_DAMAGE_AUDIT_SCHEMA,
    CANONICAL_DAMAGE_CASES_COLUMNS,
    CANONICAL_DAMAGE_CASES_SCHEMA,
    get_schema,
)


PROJECT_ROOT = find_project_root(Path(__file__))
CONFIG_PATH = PROJECT_ROOT / "config" / "experiments" / "canonical_damage.yaml"


class CanonicalDamageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_damage_config(CONFIG_PATH)
        cls.inputs = resolve_damage_inputs(cls.config, PROJECT_ROOT)
        cls.preprocessed = pd.read_csv(cls.inputs["geometry_path"])
        cls.masks = pd.read_csv(cls.inputs["masks_path"])

    def test_configuration_and_real_upstream_handoff(self) -> None:
        self.assertEqual(validate_damage_config(self.config), [])
        self.assertEqual(
            validate_canonical_damage_handoff(
                self.preprocessed,
                self.masks,
                self.config,
                PROJECT_ROOT,
                verify_files=False,
            ),
            [],
        )
        self.assertEqual(self.config["generator"]["version"], DAMAGE_MODULE_VERSION)
        self.assertEqual(self.config["expected"]["case_count"], 250)

    def test_damage_schemas_are_registered(self) -> None:
        self.assertIs(
            get_schema("canonical_damage_cases"), CANONICAL_DAMAGE_CASES_SCHEMA
        )
        self.assertIs(
            get_schema("canonical_damage_audit"), CANONICAL_DAMAGE_AUDIT_SCHEMA
        )

    def test_representative_selection_is_stable_and_complete(self) -> None:
        selected = select_representative_cases(
            self.preprocessed, self.masks, self.config
        )
        self.assertEqual(len(selected), 5)
        self.assertEqual(selected["painting_id"].nunique(), 1)
        self.assertEqual(selected.iloc[0]["painting_id"], "p050")
        self.assertEqual(
            selected["mask_type"].tolist(), self.config["expected"]["mask_types"]
        )

    def test_mask_application_changes_only_masked_pixels(self) -> None:
        clean = np.full((4, 4, 3), 10, dtype=np.uint8)
        clean[1, 1] = 255
        mask = np.zeros((4, 4), dtype=np.uint8)
        mask[1, 1] = 255
        mask[2, 2] = 255
        damaged = np.asarray(
            apply_mask_damage(Image.fromarray(clean), Image.fromarray(mask))
        )
        changed = np.any(clean != damaged, axis=2)
        self.assertEqual(int(changed.sum()), 1)
        self.assertFalse(changed[1, 1])
        self.assertTrue(changed[2, 2])
        np.testing.assert_array_equal(damaged[mask == 0], clean[mask == 0])
        np.testing.assert_array_equal(
            damaged[mask == 255], np.full((2, 3), 255, dtype=np.uint8)
        )

    def test_mask_application_rejects_nonbinary_and_dimension_mismatch(self) -> None:
        clean = Image.new("RGB", (4, 4), (10, 20, 30))
        nonbinary = Image.new("L", (4, 4), 128)
        with self.assertRaisesRegex(ValueError, "only 0 and 255"):
            apply_mask_damage(clean, nonbinary)
        with self.assertRaisesRegex(ValueError, "dimensions differ"):
            apply_mask_damage(clean, Image.new("L", (3, 4), 0))

    def test_atomic_zero_copy_preserves_exact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            destination = root / "nested" / "zero_control.png"
            Image.new("RGB", (4, 4), (12, 34, 56)).save(source, format="PNG")
            _copy_file_atomic(source, destination)
            self.assertEqual(source.read_bytes(), destination.read_bytes())
            self.assertEqual(sha256_file(source), sha256_file(destination))
            self.assertFalse(destination.with_name(destination.name + ".tmp").exists())

    def test_stale_cleanup_is_scoped_and_expected_path_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._fake_project_root(Path(directory))
            output_root = root / "outputs" / self.config["output"]["notebook_stem"]
            expected = _expected_output_path(
                output_root, "p001", "zero_control", self.config, root
            )
            stale = output_root / "images" / "damaged" / "stale.png"
            expected.parent.mkdir(parents=True, exist_ok=True)
            expected.write_bytes(b"expected")
            stale.write_bytes(b"stale")
            removed = _remove_stale_files(
                output_root / "images" / "damaged", {expected.resolve()}, root
            )
            self.assertEqual(
                expected.relative_to(root).as_posix(),
                "outputs/04_canonical_damaged_image_generation/"
                "images/damaged/p001/zero_control.png",
            )
            self.assertTrue(expected.exists())
            self.assertFalse(stale.exists())
            self.assertEqual(len(removed), 1)

    def test_saved_validation_reconciles_already_white_mask_pixel(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._fake_project_root(Path(directory))
            config = self._small_config()
            clean = np.full((4, 4, 3), 10, dtype=np.uint8)
            clean[1, 1] = 255
            mask = np.zeros((4, 4), dtype=np.uint8)
            mask[1, 1] = 255
            mask[2, 2] = 255
            case = self._write_case(root, config, clean, mask, "scratch_thin")
            result = validate_saved_damage_dataset(case, config, root)
            self.assertTrue(result.passed, result.summary)
            row = result.case_checks.iloc[0]
            self.assertEqual(int(row["total_mask_pixels"]), 2)
            self.assertEqual(int(row["preexisting_fill_pixel_count"]), 1)
            self.assertEqual(int(row["expected_changed_pixel_count"]), 1)
            self.assertEqual(int(row["observed_changed_pixel_count"]), 1)

    def test_saved_validation_requires_zero_control_byte_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._fake_project_root(Path(directory))
            config = self._small_config()
            clean = np.full((4, 4, 3), 80, dtype=np.uint8)
            mask = np.zeros((4, 4), dtype=np.uint8)
            case = self._write_case(root, config, clean, mask, "zero_control")
            result = validate_saved_damage_dataset(case, config, root)
            self.assertTrue(result.passed, result.summary)
            row = result.case_checks.iloc[0]
            self.assertTrue(bool(row["clean_equals_damaged"]))
            self.assertTrue(bool(row["zero_control_valid"]))

    @staticmethod
    def _fake_project_root(root: Path) -> Path:
        (root / ".git").mkdir()
        (root / "src" / "restoration_eval").mkdir(parents=True)
        (root / "notebooks").mkdir()
        return root

    def _small_config(self) -> dict:
        config = copy.deepcopy(self.config)
        config["generator"]["target_width"] = 4
        config["generator"]["target_height"] = 4
        config["expected"]["painting_count"] = 1
        config["expected"]["case_count"] = 5
        config["expected"]["audit_row_count"] = 5
        self.assertEqual(validate_damage_config(config), [])
        return config

    @staticmethod
    def _write_case(
        root: Path,
        config: dict,
        clean: np.ndarray,
        mask: np.ndarray,
        mask_type: str,
    ) -> pd.DataFrame:
        clean_path = root / "upstream" / "clean.png"
        mask_path = root / "upstream" / f"{mask_type}.png"
        damaged_path = (
            root
            / "outputs"
            / config["output"]["notebook_stem"]
            / "images"
            / "damaged"
            / "p001"
            / f"{mask_type}.png"
        )
        clean_path.parent.mkdir(parents=True)
        damaged_path.parent.mkdir(parents=True)
        Image.fromarray(clean, mode="RGB").save(clean_path, format="PNG")
        Image.fromarray(mask, mode="L").save(mask_path, format="PNG")
        if mask_type == "zero_control":
            shutil.copyfile(clean_path, damaged_path)
        else:
            apply_mask_damage(
                Image.fromarray(clean, mode="RGB"), Image.fromarray(mask, mode="L")
            ).save(damaged_path, format="PNG")
        record = {
            "dataset_id": "painting_restoration_eval",
            "dataset_version": "1.0.0",
            "dataset_scope": "controlled_50",
            "experiment_id": "canonical_missing_region",
            "case_id": f"canonical__p001__{mask_type}",
            "painting_id": "p001",
            "processed_image_id": "clean_p001",
            "mask_id": f"mask__canonical__p001__{mask_type}",
            "mask_type": mask_type,
            "damaged_image_id": f"damaged__canonical__p001__{mask_type}",
            "clean_image_path": clean_path.relative_to(root).as_posix(),
            "mask_path": mask_path.relative_to(root).as_posix(),
            "damaged_image_path": damaged_path.relative_to(root).as_posix(),
            "clean_image_sha256": sha256_file(clean_path),
            "mask_sha256": sha256_file(mask_path),
            "damaged_image_sha256": sha256_file(damaged_path),
            "fill_strategy": "constant_rgb",
            "fill_color_r": 255,
            "fill_color_g": 255,
            "fill_color_b": 255,
            "mask_pixel_count": int((mask == 255).sum()),
            "damaged_filename": damaged_path.name,
            "width": 4,
            "height": 4,
            "mode": "RGB",
            "format": "PNG",
            "size_bytes": damaged_path.stat().st_size,
            "generator_name": "canonical_damage_generator",
            "generator_version": "3.0.0",
            "config_schema_version": "canonical_damage_config.v1",
            "config_version": "1.0.0",
            "generation_status": "passed",
            "status": "passed",
            "issue": "",
        }
        return pd.DataFrame([record], columns=CANONICAL_DAMAGE_CASES_COLUMNS)


if __name__ == "__main__":
    unittest.main()
