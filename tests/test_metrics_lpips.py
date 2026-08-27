from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.evaluation_inputs import build_evaluation_worklist
from restoration_eval.metrics_lpips import (
    LPIPS_ACTIVE_REGIONS,
    build_lpips_execution_plan,
    compute_case_lpips_metrics,
    load_latest_lpips_checkpoint,
    load_lpips_config,
    lpips_input_geometry,
    prepare_lpips_tensor,
    run_lpips_metrics,
    validate_lpips_metrics,
    write_lpips_checkpoint,
)
from restoration_eval.schemas import LPIPS_METRICS_SCHEMA, get_schema

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/evaluation/lpips.yaml"


class FakeLPIPS:
    """Fast deterministic stand-in with the LPIPS batch-output shape."""

    def __call__(self, reference, candidate):
        return (reference - candidate).abs().mean(dim=(1, 2, 3), keepdim=True)


class LPIPSMetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_lpips_config(CONFIG_PATH)

    def _small_config(self) -> dict:
        config = deepcopy(self.config)
        transform = config["lpips_metrics"]["transform"]
        transform["maximum_side_pixels"] = 64
        transform["minimum_side_pixels"] = 16
        transform["resize_policy"] = (
            "longest_side_64_preserve_aspect_min_side_16_neutral_pad"
        )
        config["lpips_metrics"]["execution"]["batch_size"] = 2
        return config

    def _case_rows(
        self, root: Path, case_id: str, *, zero: bool, candidates: int = 1,
    ) -> pd.DataFrame:
        clean = np.zeros((32, 48, 3), dtype=np.uint8)
        clean[:, :, 0] = np.arange(48, dtype=np.uint8)[None, :] * 4
        damaged = clean.copy()
        mask = np.zeros((32, 48), dtype=np.uint8)
        if not zero:
            mask[10:22, 15:31] = 255
            damaged[10:22, 15:31] = 255
        restored = clean.copy()
        paths = {}
        for name, array in {"clean": clean, "damaged": damaged, "mask": mask}.items():
            path = root / f"{case_id}_{name}.png"
            Image.fromarray(array).save(path)
            paths[name] = path.relative_to(root).as_posix()
        records = []
        for number in range(candidates):
            restored_path = root / f"{case_id}_restored_{number}.png"
            Image.fromarray(restored).save(restored_path)
            records.append({
                "candidate_id": f"candidate_{case_id}_{number}",
                "case_id": case_id,
                "model_id": "test_model",
                "candidate_index": number,
                "seed": np.nan,
                "prompt_policy_id": "",
                "prompt_variant_id": "",
                "execution_role": "primary",
                "configuration_id": "cfg",
                "restored_path": restored_path.relative_to(root).as_posix(),
                "restored_sha256": "sha",
                "mask_threshold": 128,
                "technical_validation_passed": True,
                "source_table_id": "source",
                "dataset_id": "dataset",
                "dataset_scope": "scope",
                "experiment_id": "canonical_missing_region",
                "painting_id": "p001",
                "input_image_path": paths["damaged"],
                "clean_image_path": paths["clean"],
                "mask_or_effect_id": "mask",
                "mask_or_effect_path": paths["mask"],
                "damage_or_degradation_type": "zero_control" if zero else "loss",
                "target_damage_fraction": 0.0 if zero else 0.1,
                "realized_damage_fraction": 0.0 if zero else 0.1,
                "content_x_min": 0,
                "content_y_min": 0,
                "content_x_max": 48,
                "content_y_max": 32,
                "is_zero_control": zero,
                "status": "completed",
            })
        return pd.DataFrame(records)

    def test_schema_registered_and_region_scope_exact(self) -> None:
        self.assertIs(get_schema("lpips_metrics"), LPIPS_METRICS_SCHEMA)
        self.assertEqual(LPIPS_ACTIVE_REGIONS, ("content_region", "mask_bbox_crop"))

    def test_aspect_preserving_transform_uses_only_minimal_padding(self) -> None:
        geometry = lpips_input_geometry(200, 20, self.config)
        self.assertEqual((geometry.resized_width, geometry.resized_height), (256, 26))
        self.assertEqual((geometry.input_width, geometry.input_height), (256, 64))
        tensor, observed = prepare_lpips_tensor(
            np.zeros((20, 200, 3), dtype=np.uint8), self.config
        )
        self.assertEqual(observed, geometry)
        self.assertEqual(tuple(tensor.shape), (3, 64, 256))

    def test_zero_and_nonzero_cases_follow_region_and_baseline_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            zero = self._case_rows(root, "zero", zero=True)
            nonzero = self._case_rows(root, "nonzero", zero=False, candidates=2)
            worklist = pd.concat([zero, nonzero], ignore_index=True)
            config = self._small_config()
            plan = build_lpips_execution_plan(
                worklist, project_root=root, config=config
            )
            self.assertEqual(len(plan), 5)
            self.assertEqual(plan["region_id"].value_counts().to_dict(), {
                "content_region": 3, "mask_bbox_crop": 2,
            })
            case_result = compute_case_lpips_metrics(
                nonzero,
                model=FakeLPIPS(),
                device="cpu",
                project_root=root,
                config=config,
            )
            self.assertEqual(len(case_result.metrics), 4)
            self.assertEqual(case_result.summary["baseline_pair_count"], 2)
            self.assertEqual(case_result.summary["restored_pair_count"], 4)
            self.assertTrue(case_result.metrics["status"].eq("ok").all())
            self.assertTrue((case_result.metrics["improvement_value"] > 0).all())

            run = run_lpips_metrics(
                worklist,
                model=FakeLPIPS(),
                device="cpu",
                project_root=root,
                config=config,
            )
            validation = validate_lpips_metrics(
                run.metrics,
                worklist,
                project_root=root,
                config=config,
                expected_plan=plan,
            )
            self.assertTrue(validation["passed"], validation)
            self.assertEqual(run.summary["baseline_pair_count"], 3)
            self.assertEqual(run.summary["restored_pair_count"], 5)

    def test_checkpoint_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "work" / "lpips_metrics_checkpoint.csv"
            empty = pd.DataFrame(columns=LPIPS_METRICS_SCHEMA.required_columns)
            write_result = write_lpips_checkpoint(empty, path)
            self.assertEqual(write_result["status"], "canonical")
            loaded, source = load_latest_lpips_checkpoint(path)
            self.assertEqual(source, path)
            self.assertEqual(tuple(loaded.columns), LPIPS_METRICS_SCHEMA.required_columns)

    def test_real_contract_has_exact_candidate_region_rows(self) -> None:
        inputs = self.config["lpips_metrics"]["inputs"]
        cases = pd.read_csv(ROOT / inputs["case_registry_path"])
        eligibility = pd.read_csv(ROOT / inputs["model_eligibility_path"])
        geometry = pd.read_csv(ROOT / inputs["geometry_path"])
        tables = {
            item["source_table_id"]: pd.read_csv(ROOT / item["path"])
            for item in inputs["upstream_sources"]
        }
        worklist = build_evaluation_worklist(
            cases, eligibility, geometry, tables
        ).worklist
        plan = build_lpips_execution_plan(
            worklist, project_root=ROOT, config=self.config
        )
        expected = self.config["lpips_metrics"]["expected_counts"]
        self.assertEqual(len(worklist), expected["evaluated_candidates"])
        self.assertEqual(len(plan), expected["total_metric_rows"])
        self.assertEqual(
            plan["region_id"].value_counts().to_dict(),
            {
                "content_region": expected["content_region_rows"],
                "mask_bbox_crop": expected["mask_bbox_crop_rows"],
            },
        )
        self.assertEqual(
            plan.groupby("model_id").size().to_dict(),
            expected["metric_rows_by_model"],
        )
        self.assertEqual(
            len(plan[["case_id", "region_id"]].drop_duplicates()),
            expected["damaged_baseline_pairs"],
        )


if __name__ == "__main__":
    unittest.main()
