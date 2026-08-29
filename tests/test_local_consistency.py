from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.evaluation_inputs import build_evaluation_worklist
from restoration_eval.local_consistency import (
    LOCAL_CONSISTENCY_MODULE_VERSION,
    MAP_TYPES,
    compute_case_local_consistency,
    compute_display_scales,
    expected_metric_row_count,
    load_local_consistency_config,
    make_map_id,
    render_candidate_review_panel,
    run_local_consistency_maps,
    run_local_consistency_metrics,
    save_candidate_map_assets,
    select_map_candidates,
    validate_local_consistency_metrics,
    validate_map_manifest,
    write_dataframe_atomic,
)
from restoration_eval.schemas import (
    LOCAL_CONSISTENCY_MAP_MANIFEST_SCHEMA,
    LOCAL_CONSISTENCY_SCHEMA,
    get_schema,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/evaluation/local_consistency.yaml"


class LocalConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_local_consistency_config(CONFIG_PATH)

    @staticmethod
    def _write_case(root: Path, case_id: str, *, kind: str) -> pd.DataFrame:
        height = width = 32
        yy, xx = np.mgrid[:height, :width]
        clean = np.stack([
            (xx * 7 + yy * 2) % 256,
            (yy * 8 + 40) % 256,
            ((xx + yy) * 5 + 20) % 256,
        ], axis=2).astype(np.uint8)
        damaged = clean.copy()
        restored = clean.copy()
        mask = np.zeros((height, width), dtype=np.uint8)
        experiment = "canonical_missing_region"
        threshold = 128
        zero = kind == "zero"
        if kind == "binary":
            mask[10:22, 9:23] = 255
            damaged[10:22, 9:23] = np.array([245, 245, 245], dtype=np.uint8)
        elif kind == "synthetic":
            experiment = "synthetic_degradation"
            threshold = 13
            mask[10:22, 9:23] = 40
            damaged[10:22, 9:23, 0] = np.clip(
                damaged[10:22, 9:23, 0].astype(int) + 45, 0, 255
            ).astype(np.uint8)
        paths = {}
        for name, array in {
            "clean": clean,
            "damaged": damaged,
            "restored": restored,
            "mask": mask,
        }.items():
            path = root / f"{case_id}_{name}.png"
            Image.fromarray(array).save(path)
            paths[name] = path.relative_to(root).as_posix()
        return pd.DataFrame([{
            "candidate_id": f"candidate_{case_id}",
            "case_id": case_id,
            "model_id": "lama",
            "candidate_index": 0,
            "seed": np.nan,
            "prompt_policy_id": "none",
            "prompt_variant_id": "none",
            "execution_role": "primary",
            "restored_path": paths["restored"],
            "mask_threshold": threshold,
            "dataset_id": "painting_restoration_eval",
            "dataset_scope": "controlled_50",
            "experiment_id": experiment,
            "painting_id": "p001",
            "input_image_path": paths["damaged"],
            "clean_image_path": paths["clean"],
            "mask_or_effect_path": paths["mask"],
            "damage_or_degradation_type": (
                "zero_control" if zero else
                "water_stain" if kind == "synthetic" else
                "binary_missing_region"
            ),
            "target_damage_fraction": 0.0 if zero else 0.1,
            "realized_damage_fraction": 0.0 if zero else 0.1,
            "content_x_min": 0,
            "content_y_min": 0,
            "content_x_max": width,
            "content_y_max": height,
            "is_zero_control": zero,
        }])

    def test_config_schema_ids_and_counts(self) -> None:
        self.assertEqual(LOCAL_CONSISTENCY_MODULE_VERSION, "1.0.3")
        self.assertIs(get_schema("local_consistency"), LOCAL_CONSISTENCY_SCHEMA)
        self.assertIs(
            get_schema("local_consistency_map_images"),
            LOCAL_CONSISTENCY_MAP_MANIFEST_SCHEMA,
        )
        settings = self.config["local_consistency"]
        self.assertEqual(tuple(settings["visualization"]["map_types"]), MAP_TYPES)
        self.assertEqual(settings["expected_counts"]["total_metric_rows"], 271988)
        self.assertEqual(settings["expected_counts"]["map_manifest_rows"], 3282)
        first = make_map_id("candidate_with_a_long_identifier")
        second = make_map_id("candidate_with_a_long_identifier")
        self.assertEqual(first, second)
        self.assertEqual(len(first), 20)

    def test_zero_binary_and_synthetic_metric_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            zero_work = self._write_case(root, "zero", kind="zero")
            binary_work = self._write_case(root, "binary", kind="binary")
            synthetic_work = self._write_case(root, "synthetic", kind="synthetic")
            zero = compute_case_local_consistency(
                zero_work, project_root=root, config=self.config
            )
            binary = compute_case_local_consistency(
                binary_work, project_root=root, config=self.config
            )
            synthetic = compute_case_local_consistency(
                synthetic_work, project_root=root, config=self.config
            )
            self.assertEqual(len(zero), 27)
            self.assertEqual(len(binary), 131)
            self.assertEqual(len(synthetic), 144)
            combined = pd.concat([zero, binary, synthetic], ignore_index=True)
            worklist = pd.concat(
                [zero_work, binary_work, synthetic_work], ignore_index=True
            )
            self.assertEqual(expected_metric_row_count(worklist), 302)
            validation = validate_local_consistency_metrics(
                combined, worklist, expected_rows=302
            )
            self.assertTrue(validation["passed"], validation)
            self.assertFalse(combined["is_final_trustworthiness_flag"].any())
            self.assertTrue(
                binary.loc[binary["status"].eq("ok"), "improvement_value"].ge(0).all()
            )
            self.assertFalse(
                combined.loc[
                    combined["metric_name"].str.contains("ssim", case=False)
                ]["region_id"].isin({"masked_region", "degradation_support"}).any()
            )

    def test_missing_prompt_metadata_is_not_serialized_as_nan_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worklist = self._write_case(root, "binary", kind="binary")
            worklist["prompt_policy_id"] = np.nan
            worklist["prompt_variant_id"] = np.nan

            metrics = compute_case_local_consistency(
                worklist, project_root=root, config=self.config
            )

            self.assertTrue(metrics["prompt_policy_id"].eq("").all())
            self.assertTrue(metrics["prompt_variant_id"].eq("").all())
            self.assertFalse(metrics["prompt_policy_id"].eq("nan").any())
            self.assertFalse(metrics["prompt_variant_id"].eq("nan").any())

    def test_map_assets_scales_and_review_panel(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worklist = self._write_case(root, "binary", kind="binary")
            metrics = compute_case_local_consistency(
                worklist, project_root=root, config=self.config
            )
            scales = compute_display_scales(metrics, config=self.config)
            manifest = save_candidate_map_assets(
                worklist.iloc[0],
                project_root=root,
                maps_root=root / "outputs/maps",
                config=self.config,
                scales=scales,
            )
            self.assertEqual(set(manifest["map_type"]), set(MAP_TYPES))
            map_validation = validate_map_manifest(
                manifest, project_root=root, verify_checksums=True
            )
            self.assertTrue(map_validation["passed"], map_validation)
            for row in manifest.itertuples(index=False):
                with Image.open(root / row.relative_path) as image:
                    self.assertEqual(image.mode, "RGBA")
                    self.assertEqual(image.width, 32 * 3)
                    self.assertEqual(image.height, 32 + 24)
            panel_path = root / "outputs/review.png"
            figure = render_candidate_review_panel(
                worklist.iloc[0], project_root=root, config=self.config,
                scales=scales, output_path=panel_path, selection_role="unit_test",
            )
            plt.close(figure)
            self.assertTrue(panel_path.is_file())
            self.assertGreater(panel_path.stat().st_size, 0)
            checkpoint = root / "outputs/work/maps.csv"
            first = run_local_consistency_maps(
                worklist, project_root=root, maps_root=root / "outputs/maps_resume",
                config=self.config, scales=scales, checkpoint_path=checkpoint,
            )
            second = run_local_consistency_maps(
                worklist, project_root=root, maps_root=root / "outputs/maps_resume",
                config=self.config, scales=scales, checkpoint_path=checkpoint,
            )
            self.assertEqual(first.completed_candidates, 1)
            self.assertEqual(second.reused_candidates, 1)
            self.assertEqual(len(second.map_images), 3)

    def test_checkpoint_resume_and_atomic_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worklist = pd.concat([
                self._write_case(root, "zero", kind="zero"),
                self._write_case(root, "binary", kind="binary"),
            ], ignore_index=True)
            checkpoint = root / "outputs/work/local.csv"
            first = run_local_consistency_metrics(
                worklist, project_root=root, config=self.config,
                checkpoint_path=checkpoint,
            )
            second = run_local_consistency_metrics(
                worklist, project_root=root, config=self.config,
                checkpoint_path=checkpoint,
            )
            self.assertEqual(first.completed_candidates, 2)
            self.assertEqual(second.reused_candidates, 2)
            self.assertEqual(len(first.metrics), len(second.metrics))
            replacement = root / "replacement.csv"
            write_dataframe_atomic(pd.DataFrame({"value": [1]}), replacement)
            write_dataframe_atomic(pd.DataFrame({"value": [2]}), replacement)
            self.assertEqual(pd.read_csv(replacement)["value"].tolist(), [2])

    def test_real_worklist_analytical_counts_and_map_population(self) -> None:
        inputs = self.config["local_consistency"]["inputs"]
        cases = pd.read_csv(ROOT / inputs["case_registry_path"])
        eligibility = pd.read_csv(ROOT / inputs["model_eligibility_path"])
        geometry = pd.read_csv(ROOT / inputs["geometry_path"])
        tables = {
            item["source_table_id"]: pd.read_csv(ROOT / item["path"])
            for item in inputs["upstream_sources"]
        }
        source_roots = {
            item["source_table_id"]: Path(item["path"]).parent.parent.as_posix()
            for item in inputs["upstream_sources"]
        }
        worklist = build_evaluation_worklist(
            cases, eligibility, geometry, tables,
            candidate_source_roots=source_roots,
        ).worklist
        self.assertEqual(len(worklist), 2160)
        self.assertEqual(expected_metric_row_count(worklist), 271988)
        selected = select_map_candidates(worklist)
        self.assertEqual(len(selected), 1090)
        self.assertFalse(selected["is_zero_control"].any())
        self.assertFalse(selected.duplicated(["case_id", "model_id"]).any())
        self.assertEqual(
            len(selected) * len(MAP_TYPES),
            self.config["local_consistency"]["expected_counts"][
                "candidate_map_images"
            ],
        )


if __name__ == "__main__":
    unittest.main()
