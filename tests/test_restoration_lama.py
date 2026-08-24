from __future__ import annotations

import copy
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.restoration_lama import (
    RESTORATION_GENERATOR_VERSION,
    binarize_restoration_mask,
    build_eligible_case_worklist,
    build_iopaint_subprocess_environment,
    calculate_file_sha256,
    discover_lama_model_artifact,
    load_lama_config,
    masked_composite,
    prepare_lama_work_items,
    run_lama_cases,
    summarize_restoration_runtime,
    validate_restoration_outputs,
    validate_restoration_records,
)


CONFIG_PATH = Path("config/experiments/lama.yaml")
CASE_REGISTRY_PATH = Path(
    "outputs/08_experiment_contracts_and_region_policy/data/case_registry.csv"
)
MODEL_ELIGIBILITY_PATH = Path(
    "outputs/08_experiment_contracts_and_region_policy/data/model_eligibility.csv"
)


class LamaRestorationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_lama_config(CONFIG_PATH)

    def test_configuration_freezes_approved_methodological_policies(self) -> None:
        model = self.config["model"]
        execution = self.config["execution"]
        self.assertEqual(self.config["config_version"], "1.1.0")
        self.assertEqual(model["model_id"], "lama")
        self.assertEqual(model["requested_device"], "cuda")
        self.assertFalse(model["allow_cpu_fallback"])
        self.assertEqual(model["maximum_retries"], 1)
        self.assertEqual(
            model["model_artifact_url"],
            "https://github.com/Sanster/models/releases/download/"
            "add_big_lama/big-lama.pt",
        )
        self.assertEqual(
            model["model_artifact_expected_md5"],
            "e3aa4aaa15225a33ec84f9f4bc47e500",
        )
        self.assertEqual(model["zero_control_policy"], "identity_noop")
        self.assertEqual(
            model["compositing_policy"],
            "masked_composite_preserve_outside.v1",
        )
        self.assertEqual(
            model["mask_threshold_policy"]["binary_missing_region"]["threshold"],
            128,
        )
        self.assertEqual(
            model["mask_threshold_policy"]["synthetic_degradation"]["threshold"],
            13,
        )
        self.assertEqual(execution["progress_interval_cases"], 10)
        self.assertEqual(execution["batch_grouping"], "experiment_id")
        self.assertEqual(
            self.config["smoke"]["repeatability_tolerance"],
            {
                "maximum_absolute_difference": 1,
                "maximum_mean_absolute_difference": 0.005,
                "maximum_different_pixel_fraction": 0.01,
                "require_sha256_equality": False,
            },
        )
        self.assertEqual(RESTORATION_GENERATOR_VERSION, "3.1.0")

    def test_configured_model_artifact_is_resolved_and_hashed(self) -> None:
        config = copy.deepcopy(self.config)
        config["model"]["model_artifact_path"] = "models/big-lama.pt"
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            artifact_path = root / "models" / "big-lama.pt"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_bytes(b"test-lama-checkpoint")

            artifact = discover_lama_model_artifact(
                config,
                project_root=root,
            )

            self.assertEqual(
                artifact["model_artifact_path"],
                str(artifact_path.resolve()),
            )
            self.assertEqual(
                artifact["model_artifact_sha256"],
                calculate_file_sha256(artifact_path),
            )
            self.assertEqual(
                artifact["model_artifact_discovery_method"],
                "configured_path",
            )

    def test_blank_model_artifact_uses_iopaint_cache_api(self) -> None:
        config = copy.deepcopy(self.config)
        config["model"]["model_artifact_path"] = ""
        with tempfile.TemporaryDirectory() as temporary_directory:
            artifact_path = Path(temporary_directory) / "big-lama.pt"
            artifact_path.write_bytes(b"cached-lama-checkpoint")

            iopaint_package = types.ModuleType("iopaint")
            iopaint_package.__path__ = []
            helper_module = types.ModuleType("iopaint.helper")
            helper_module.get_cache_path_by_url = lambda _url: artifact_path
            config["model"]["model_artifact_url"] = (
                "https://example.test/big-lama.pt"
            )
            config["model"]["model_artifact_expected_md5"] = "test-md5"

            module_overrides = {
                "iopaint": iopaint_package,
                "iopaint.helper": helper_module,
            }
            with mock.patch.dict(sys.modules, module_overrides):
                artifact = discover_lama_model_artifact(config)

            self.assertEqual(
                artifact["model_artifact_path"],
                str(artifact_path.resolve()),
            )
            self.assertEqual(
                artifact["model_artifact_sha256"],
                calculate_file_sha256(artifact_path),
            )
            self.assertEqual(
                artifact["model_artifact_discovery_method"],
                "iopaint_cache_api",
            )
            self.assertEqual(
                artifact["model_artifact_url"],
                "https://example.test/big-lama.pt",
            )
            self.assertEqual(
                artifact["model_artifact_expected_md5"],
                "test-md5",
            )

    def test_iopaint_subprocess_environment_is_utf8_and_noninteractive(self) -> None:
        environment = build_iopaint_subprocess_environment(
            {"PATH": "test-path", "KEEP_ME": "preserved"}
        )
        self.assertEqual(environment["PATH"], "test-path")
        self.assertEqual(environment["KEEP_ME"], "preserved")
        self.assertEqual(environment["PYTHONUTF8"], "1")
        self.assertEqual(environment["PYTHONIOENCODING"], "utf-8")
        self.assertEqual(environment["TERM"], "dumb")
        self.assertEqual(environment["NO_COLOR"], "1")
        self.assertEqual(environment["RICH_NO_COLOR"], "1")

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

    def test_inclusive_threshold_and_masked_composite(self) -> None:
        mask = np.array([[12, 13], [127, 128]], dtype=np.uint8)
        binary = binarize_restoration_mask(mask, 13)
        np.testing.assert_array_equal(
            binary,
            np.array([[0, 255], [255, 255]], dtype=np.uint8),
        )
        source = np.zeros((2, 2, 3), dtype=np.uint8)
        inferred = np.full((2, 2, 3), 200, dtype=np.uint8)
        composed = masked_composite(source, inferred, binary)
        np.testing.assert_array_equal(composed[0, 0], source[0, 0])
        np.testing.assert_array_equal(composed[0, 1], inferred[0, 1])

    def _small_config(self) -> dict:
        config = copy.deepcopy(self.config)
        config["execution"]["target_width"] = 16
        config["execution"]["target_height"] = 16
        config["execution"]["progress_interval_cases"] = 1
        return config

    @staticmethod
    def _runtime_environment() -> dict:
        return {
            "iopaint_executable": "fake-iopaint",
            "iopaint_executable_path": "fake-iopaint",
            "iopaint_version": "test-version",
            "iopaint_model_name": "lama",
            "model_revision": "test-revision",
            "model_artifact_path": "",
            "model_artifact_sha256": "",
            "requested_device": "cuda",
            "effective_device": "cuda",
            "cpu_fallback_used": False,
            "python_version": "test",
            "python_implementation": "CPython",
            "platform": "test-platform",
            "machine": "test-machine",
            "processor": "test-processor",
            "torch_version": "test-torch",
            "cuda_available": True,
            "cuda_device_count": 1,
            "cuda_device_name": "test-gpu",
            "cuda_runtime_version": "test-cuda",
        }

    def _write_case_inputs(
        self,
        root: Path,
        case_id: str,
        *,
        zero: bool,
        experiment_id: str,
    ) -> dict:
        input_dir = root / "inputs"
        input_dir.mkdir(parents=True, exist_ok=True)
        image = np.zeros((16, 16, 3), dtype=np.uint8)
        for column in range(16):
            image[:, column, :] = column * 10
        mask = np.zeros((16, 16), dtype=np.uint8)
        if not zero:
            mask[5:11, 5:11] = 255
            image[5:11, 5:11, :] = 255
        input_path = input_dir / f"{case_id}_input.png"
        mask_path = input_dir / f"{case_id}_mask.png"
        Image.fromarray(image, mode="RGB").save(input_path)
        Image.fromarray(mask, mode="L").save(mask_path)
        return {
            "case_id": case_id,
            "experiment_id": experiment_id,
            "input_image_path": input_path.relative_to(root).as_posix(),
            "mask_or_effect_path": mask_path.relative_to(root).as_posix(),
        }

    @staticmethod
    def _successful_fake_runner(staged_items: pd.DataFrame, **kwargs) -> dict:
        for _, item in staged_items.iterrows():
            with Image.open(item["staged_input_path"]) as image:
                input_rgb = np.asarray(image.convert("RGB")).copy()
            with Image.open(item["staged_mask_path"]) as image:
                mask = np.asarray(image.convert("L")) > 0
            input_rgb[mask] = 64
            Image.fromarray(input_rgb, mode="RGB").save(item["raw_output_path"])
        return {
            "batch_id": kwargs["batch_id"],
            "case_count": len(staged_items),
            "generated_count": len(staged_items),
            "return_code": 0,
            "runtime_seconds": float(len(staged_items)),
            "started_at_utc": "2026-01-01T00:00:00Z",
            "completed_at_utc": "2026-01-01T00:00:01Z",
            "timed_out": False,
            "issue": "",
            "command": ["fake-iopaint"],
            "command_text": "fake-iopaint",
            "command_log_path": "",
            "stdout_log_path": "",
            "stderr_log_path": "",
        }

    @staticmethod
    def _failing_fake_runner(staged_items: pd.DataFrame, **kwargs) -> dict:
        return {
            "batch_id": kwargs["batch_id"],
            "case_count": len(staged_items),
            "generated_count": 0,
            "return_code": 1,
            "runtime_seconds": 0.5,
            "started_at_utc": "2026-01-01T00:00:00Z",
            "completed_at_utc": "2026-01-01T00:00:01Z",
            "timed_out": False,
            "issue": "simulated_failure",
            "command": ["fake-iopaint"],
            "command_text": "fake-iopaint",
            "command_log_path": "",
            "stdout_log_path": "",
            "stderr_log_path": "",
        }

    def test_execution_validation_runtime_and_resume_without_iopaint(self) -> None:
        config = self._small_config()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nonzero = self._write_case_inputs(
                root,
                "case_nonzero",
                zero=False,
                experiment_id="canonical_missing_region",
            )
            zero = self._write_case_inputs(
                root,
                "case_zero",
                zero=True,
                experiment_id="damage_size_sensitivity",
            )
            worklist = pd.DataFrame([nonzero, zero])
            prepared = prepare_lama_work_items(
                worklist,
                project_root=root,
                config=config,
                progress_callback=None,
            )
            messages: list[str] = []
            records, batch_runs = run_lama_cases(
                prepared,
                restored_root=root / "outputs" / "images" / "restored",
                work_root=root / "outputs" / "work",
                project_root=root,
                config=config,
                runtime_environment=self._runtime_environment(),
                progress_callback=messages.append,
                batch_runner=self._successful_fake_runner,
            )
            validate_restoration_records(records)
            self.assertEqual(records["status"].tolist(), ["completed", "completed"])
            self.assertEqual(
                set(records["execution_action"]),
                {"lama_inpaint", "identity_noop"},
            )
            self.assertEqual(len(batch_runs), 1)
            self.assertTrue(messages)

            audit = validate_restoration_outputs(
                records,
                prepared,
                project_root=root,
                config=config,
            )
            self.assertTrue(audit["validation_passed"].all())
            self.assertTrue(audit["outside_invariance_valid"].all())
            self.assertTrue(audit["zero_control_valid"].all())

            summary = summarize_restoration_runtime(records, prepared)
            self.assertEqual(len(summary), 3)
            self.assertEqual(summary.iloc[0]["summary_scope"], "overall")

            resumed, resumed_runs = run_lama_cases(
                prepared,
                restored_root=root / "outputs" / "images" / "restored",
                work_root=root / "outputs" / "work",
                project_root=root,
                config=config,
                runtime_environment=self._runtime_environment(),
                resume_records=records,
                progress_callback=None,
                batch_runner=self._failing_fake_runner,
            )
            self.assertTrue(resumed["execution_action"].eq("reused_validated").all())
            self.assertTrue(resumed_runs.empty)

    def test_failed_outputs_remain_explicit_after_retry(self) -> None:
        config = self._small_config()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            case = self._write_case_inputs(
                root,
                "case_failure",
                zero=False,
                experiment_id="canonical_missing_region",
            )
            prepared = prepare_lama_work_items(
                pd.DataFrame([case]),
                project_root=root,
                config=config,
                progress_callback=None,
            )
            records, batch_runs = run_lama_cases(
                prepared,
                restored_root=root / "outputs" / "images" / "restored",
                work_root=root / "outputs" / "work",
                project_root=root,
                config=config,
                runtime_environment=self._runtime_environment(),
                progress_callback=None,
                batch_runner=self._failing_fake_runner,
            )
            self.assertEqual(len(batch_runs), 2)
            self.assertEqual(records.iloc[0]["status"], "failed")
            self.assertEqual(records.iloc[0]["execution_action"], "failed")
            self.assertEqual(int(records.iloc[0]["retry_count"]), 1)
            self.assertIn("simulated_failure", records.iloc[0]["issue"])


if __name__ == "__main__":
    unittest.main()
