from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.evaluation_inputs import build_evaluation_worklist
from restoration_eval.metrics_classical import (
    compute_case_classical_metrics,
    compute_improvement,
    expected_metric_row_count,
    load_classical_metrics_config,
    validate_classical_metrics,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/evaluation/metrics.yaml"


class ClassicalMetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_classical_metrics_config(CONFIG_PATH)

    def _write_case(self, root: Path, case_id: str, *, kind: str) -> pd.DataFrame:
        image = np.zeros((16, 16, 3), dtype=np.uint8)
        for x in range(16):
            image[:, x, :] = 10 * x
        damaged = image.copy()
        restored = image.copy()
        mask = np.zeros((16, 16), dtype=np.uint8)
        experiment = "canonical_missing_region"
        threshold = 128
        zero = kind == "zero"
        if kind == "binary":
            mask[5:11, 5:11] = 255
            damaged[5:11, 5:11] = 255
        elif kind == "synthetic":
            experiment = "synthetic_degradation"
            threshold = 13
            mask[5:11, 5:11] = 20
            damaged[5:11, 5:11] = np.clip(
                damaged[5:11, 5:11].astype(int) + 40, 0, 255
            ).astype(np.uint8)
        paths = {}
        for name, array in {
            "clean": image, "damaged": damaged,
            "restored": restored, "mask": mask,
        }.items():
            path = root / f"{case_id}_{name}.png"
            Image.fromarray(array).save(path)
            paths[name] = path.relative_to(root).as_posix()
        return pd.DataFrame([{
            "candidate_id": f"candidate_{case_id}", "case_id": case_id,
            "model_id": "model", "candidate_index": 0, "seed": np.nan,
            "prompt_policy_id": "", "prompt_variant_id": "",
            "execution_role": "primary", "configuration_id": "cfg",
            "restored_path": paths["restored"], "restored_sha256": "sha",
            "mask_threshold": threshold, "technical_validation_passed": True,
            "source_table_id": "source", "dataset_id": "dataset",
            "dataset_scope": "scope", "experiment_id": experiment,
            "painting_id": "p001", "input_image_path": paths["damaged"],
            "clean_image_path": paths["clean"], "mask_or_effect_id": "mask",
            "mask_or_effect_path": paths["mask"],
            "damage_or_degradation_type": (
                "water_stain" if kind == "synthetic" else "binary_missing_region"
            ),
            "target_damage_fraction": 0.0 if zero else 0.1,
            "realized_damage_fraction": 0.0 if zero else 0.1,
            "content_x_min": 0, "content_y_min": 0,
            "content_x_max": 16, "content_y_max": 16,
            "is_zero_control": zero, "status": "completed",
        }])

    def test_direction_aware_infinity_policy(self) -> None:
        self.assertEqual(
            compute_improvement(math.inf, math.inf, "restored_minus_damaged"),
            0.0,
        )
        self.assertEqual(compute_improvement(10.0, 4.0, "damaged_minus_restored"), 6.0)
        self.assertEqual(compute_improvement(4.0, 10.0, "restored_minus_damaged"), 6.0)

    def test_zero_binary_and_synthetic_region_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            zero = compute_case_classical_metrics(
                self._write_case(root, "zero", kind="zero"),
                project_root=root, config=self.config,
            )
            binary = compute_case_classical_metrics(
                self._write_case(root, "binary", kind="binary"),
                project_root=root, config=self.config,
            )
            synthetic = compute_case_classical_metrics(
                self._write_case(root, "synthetic", kind="synthetic"),
                project_root=root, config=self.config,
            )
            self.assertEqual(len(zero), 11)
            self.assertEqual(len(binary), 30)
            self.assertEqual(len(synthetic), 33)
            self.assertFalse(
                pd.concat([zero, binary, synthetic]).query(
                    "metric_name == 'ssim'"
                )["region_id"].isin({"masked_region", "boundary_ring"}).any()
            )
            self.assertEqual(
                len(synthetic.query("region_id == 'degradation_support'")), 3
            )
            zero_psnr = zero.query("metric_name == 'psnr'")
            self.assertTrue(np.isposinf(zero_psnr["damaged_value"]).all())
            self.assertTrue(np.isposinf(zero_psnr["restored_value"]).all())
            self.assertTrue(zero_psnr["improvement_value"].eq(0.0).all())
            combined = pd.concat([zero, binary, synthetic], ignore_index=True)
            combined_worklist = pd.concat([
                self._write_case(root, "zero", kind="zero"),
                self._write_case(root, "binary", kind="binary"),
                self._write_case(root, "synthetic", kind="synthetic"),
            ], ignore_index=True)
            self.assertEqual(
                expected_metric_row_count(
                    combined_worklist, project_root=root, config=self.config
                ),
                74,
            )
            validation = validate_classical_metrics(
                combined, combined_worklist, expected_rows=74,
            )
            self.assertTrue(validation["passed"], validation)

    def test_real_contract_has_exact_rows_and_sdxl_evidence(self) -> None:
        inputs = self.config["classical_metrics"]["inputs"]
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
        nonzero = worklist.loc[~worklist["is_zero_control"]]
        synthetic = nonzero.loc[nonzero["experiment_id"].eq("synthetic_degradation")]
        analytical_rows = (
            len(nonzero) * 30
            + int(worklist["is_zero_control"].sum()) * 11
            + len(synthetic) * 3
        )
        self.assertEqual(analytical_rows, 63018)
        self.assertEqual(
            analytical_rows,
            self.config["classical_metrics"]["expected_counts"]["total_metric_rows"],
        )
        sdxl = worklist.loc[worklist["model_id"].eq("sdxl_inpainting")]
        self.assertEqual(len(sdxl), 10)
        self.assertEqual(len(sdxl.query("experiment_id == 'synthetic_degradation'")), 6)
        self.assertEqual(len(sdxl) * 30 + 6 * 3, 318)


if __name__ == "__main__":
    unittest.main()
