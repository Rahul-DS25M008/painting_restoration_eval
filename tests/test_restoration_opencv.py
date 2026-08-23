from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from restoration_eval.restoration_opencv import (
    RESTORATION_GENERATOR_VERSION,
    binarize_restoration_mask,
    build_eligible_case_worklist,
    load_opencv_telea_config,
    restore_array_with_opencv_telea,
    run_opencv_telea_case,
    run_opencv_telea_cases,
    summarize_restoration_runtime,
    validate_restoration_outputs,
    validate_restoration_records,
)


CONFIG_PATH = Path("config/experiments/opencv_telea.yaml")
CASE_REGISTRY_PATH = Path(
    "outputs/08_experiment_contracts_and_region_policy/data/case_registry.csv"
)
MODEL_ELIGIBILITY_PATH = Path(
    "outputs/08_experiment_contracts_and_region_policy/data/model_eligibility.csv"
)


class OpenCvTeleaRestorationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_opencv_telea_config(CONFIG_PATH)

    def test_configuration_freezes_approved_thresholds_and_progress(self) -> None:
        policies = self.config["model"]["mask_threshold_policy"]
        self.assertEqual(policies["binary_missing_region"]["threshold"], 128)
        self.assertEqual(policies["synthetic_degradation"]["threshold"], 13)
        self.assertEqual(
            policies["synthetic_degradation"]["comparison"],
            "greater_than_or_equal",
        )
        self.assertEqual(self.config["execution"]["progress_interval_cases"], 10)
        self.assertEqual(self.config["model"]["zero_control_policy"], "identity_noop")
        self.assertEqual(RESTORATION_GENERATOR_VERSION, "3.0.0")

    def test_real_upstream_contract_builds_exact_410_case_worklist(self) -> None:
        cases = pd.read_csv(CASE_REGISTRY_PATH)
        eligibility = pd.read_csv(MODEL_ELIGIBILITY_PATH)
        worklist = build_eligible_case_worklist(cases, eligibility, self.config)
        self.assertEqual(len(worklist), 410)
        self.assertTrue(worklist["case_id"].is_unique)
        self.assertEqual(
            worklist.groupby("experiment_id").size().to_dict(),
            self.config["expected"]["eligible_case_count_by_experiment"],
        )

    def test_inclusive_threshold_and_zero_control_identity(self) -> None:
        mask = np.array([[12, 13], [127, 128]], dtype=np.uint8)
        binary = binarize_restoration_mask(mask, 13)
        np.testing.assert_array_equal(
            binary,
            np.array([[0, 255], [255, 255]], dtype=np.uint8),
        )
        image = np.arange(8 * 8 * 3, dtype=np.uint8).reshape(8, 8, 3)
        restored, action = restore_array_with_opencv_telea(
            image,
            np.zeros((8, 8), dtype=np.uint8),
        )
        self.assertEqual(action, "identity_noop")
        np.testing.assert_array_equal(restored, image)

    def _small_config(self) -> dict:
        config = copy.deepcopy(self.config)
        config["execution"]["target_width"] = 16
        config["execution"]["target_height"] = 16
        config["execution"]["progress_interval_cases"] = 1
        return config

    def _write_case_inputs(self, root: Path, case_id: str, *, zero: bool) -> dict:
        input_dir = root / "inputs"
        input_dir.mkdir(parents=True, exist_ok=True)
        image = np.zeros((16, 16, 3), dtype=np.uint8)
        for column in range(16):
            image[:, column, :] = column * 12
        mask = np.zeros((16, 16), dtype=np.uint8)
        if not zero:
            mask[5:11, 5:11] = 255
            image[5:11, 5:11, :] = 255
        input_path = input_dir / f"{case_id}_input.png"
        mask_path = input_dir / f"{case_id}_mask.png"
        self.assertTrue(cv2.imwrite(str(input_path), image))
        self.assertTrue(cv2.imwrite(str(mask_path), mask))
        return {
            "case_id": case_id,
            "experiment_id": "canonical_missing_region",
            "input_image_path": input_path.relative_to(root).as_posix(),
            "mask_or_effect_path": mask_path.relative_to(root).as_posix(),
        }

    def test_case_execution_validation_resume_and_runtime_summary(self) -> None:
        config = self._small_config()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            restored_root = root / "outputs" / "images" / "restored"
            nonzero = self._write_case_inputs(root, "case_nonzero", zero=False)
            zero = self._write_case_inputs(root, "case_zero", zero=True)
            worklist = pd.DataFrame([nonzero, zero])
            messages: list[str] = []
            checkpoints: list[int] = []
            records = run_opencv_telea_cases(
                worklist,
                restored_root=restored_root,
                project_root=root,
                config=config,
                progress_callback=messages.append,
                checkpoint_callback=lambda frame: checkpoints.append(len(frame)),
            )
            validate_restoration_records(records)
            self.assertEqual(records["status"].tolist(), ["completed", "completed"])
            self.assertEqual(
                set(records["execution_action"]),
                {"telea_inpaint", "identity_noop"},
            )
            self.assertEqual(len(messages), 2)
            self.assertEqual(checkpoints, [1, 2])

            audit = validate_restoration_outputs(
                records,
                worklist,
                project_root=root,
                config=config,
            )
            self.assertTrue(audit["validation_passed"].all())
            self.assertTrue(audit["outside_invariance_valid"].all())
            self.assertTrue(audit["zero_control_valid"].all())

            resume_record = records.loc[
                records["case_id"].eq("case_nonzero")
            ].iloc[0].to_dict()
            reused = run_opencv_telea_case(
                nonzero,
                restored_root=restored_root,
                project_root=root,
                config=config,
                resume_record=resume_record,
            )
            self.assertEqual(reused["execution_action"], "reused_validated")
            self.assertEqual(reused["restored_sha256"], resume_record["restored_sha256"])

            summary_worklist = worklist.copy()
            summary_worklist.loc[
                summary_worklist["case_id"].eq("case_zero"), "experiment_id"
            ] = "damage_size_sensitivity"
            summary = summarize_restoration_runtime(records, summary_worklist)
            self.assertEqual(len(summary), 3)
            self.assertEqual(summary.iloc[0]["summary_scope"], "overall")
            self.assertEqual(int(summary.iloc[0]["case_count"]), 2)

    def test_failures_are_recorded_without_silent_drop(self) -> None:
        config = self._small_config()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            case = {
                "case_id": "missing_case",
                "experiment_id": "canonical_missing_region",
                "input_image_path": "inputs/missing.png",
                "mask_or_effect_path": "inputs/missing_mask.png",
            }
            record = run_opencv_telea_case(
                case,
                restored_root=root / "outputs" / "restored",
                project_root=root,
                config=config,
            )
            self.assertEqual(record["status"], "failed")
            self.assertEqual(record["execution_action"], "failed")
            self.assertIn("FileNotFoundError", record["issue"])


if __name__ == "__main__":
    unittest.main()
