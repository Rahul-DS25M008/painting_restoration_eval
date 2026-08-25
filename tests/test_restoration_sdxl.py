from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from restoration_eval.restoration_sdxl import (
    SDXL_HELPER_VERSION,
    build_feasibility_attempt_plan,
    build_sdxl_eligible_worklist,
    build_worker_job,
    derive_availability_state,
    inspect_local_model_cache,
    load_sdxl_config,
    run_worker_process,
    select_feasibility_case,
)
from restoration_eval.schemas import (
    SDXL_FEASIBILITY_ATTEMPTS_SCHEMA,
    get_schema,
    validate_dataframe,
)


CONFIG_PATH = Path("config/experiments/sdxl.yaml")
CASE_REGISTRY_PATH = Path(
    "outputs/08_experiment_contracts_and_region_policy/data/case_registry.csv"
)
MODEL_ELIGIBILITY_PATH = Path(
    "outputs/08_experiment_contracts_and_region_policy/data/model_eligibility.csv"
)
ARTWORKS_PATH = Path("outputs/01_dataset_verification/data/artworks.csv")


class SDXLFeasibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_sdxl_config(CONFIG_PATH)
        cls.worklist = build_sdxl_eligible_worklist(
            pd.read_csv(CASE_REGISTRY_PATH),
            pd.read_csv(MODEL_ELIGIBILITY_PATH),
            pd.read_csv(ARTWORKS_PATH),
            cls.config,
        )
        cls.selected = select_feasibility_case(cls.worklist, cls.config)
        cls.plan = build_feasibility_attempt_plan(cls.selected, cls.config)

    def test_configuration_freezes_timeout_and_quality_policy(self) -> None:
        model = self.config["model"]
        execution = self.config["execution"]
        memory = self.config["memory_strategy"]
        self.assertEqual(execution["mode"], "feasibility_only")
        self.assertEqual(execution["per_attempt_timeout_seconds"], 1500)
        self.assertEqual(execution["maximum_current_attempts"], 1)
        self.assertTrue(execution["stop_after_timeout"])
        self.assertFalse(execution["retry_failed_attempts"])
        self.assertFalse(self.config["scope"]["full_execution_authorized"])
        self.assertEqual(model["model_revision"], "115134f363124c53c7d878647567d04daf26e41e")
        self.assertEqual((model["inference_width"], model["inference_height"]), (768, 768))
        self.assertEqual(model["num_inference_steps"], 30)
        self.assertEqual(model["precision"], "float16")
        self.assertTrue(model["local_files_only"])
        self.assertTrue(memory["model_cpu_offload"])
        self.assertFalse(memory["sequential_cpu_offload"])
        self.assertEqual(memory["attention_backend"], "pytorch_sdpa")
        self.assertFalse(memory["attention_slicing"])
        self.assertTrue(memory["vae_slicing"])
        self.assertTrue(memory["vae_tiling"])
        self.assertEqual(SDXL_HELPER_VERSION, "2.0.0")

    def test_real_contract_and_predeclared_case_are_exact(self) -> None:
        self.assertEqual(len(self.worklist), 410)
        self.assertEqual(int(self.worklist["is_zero_control"].sum()), 50)
        self.assertEqual(self.selected["case_id"], "canonical__p039__loss_large")
        self.assertFalse(bool(self.selected["is_zero_control"]))
        self.assertGreater(float(self.selected["realized_damage_fraction"]), 0.0)

    def test_attempt_plan_is_single_predeclared_non_metric_probe(self) -> None:
        self.assertEqual(len(self.plan), 1)
        row = self.plan.iloc[0]
        self.assertEqual(row["evidence_origin"], "current_execution")
        self.assertEqual(row["case_id"], "canonical__p039__loss_large")
        self.assertEqual(row["timeout_seconds"], 1500)
        self.assertEqual(row["status"], "planned")
        self.assertEqual(row["failure_type"], "none")
        validation = validate_dataframe(self.plan, SDXL_FEASIBILITY_ATTEMPTS_SCHEMA)
        self.assertTrue(validation.passed, validation.to_dict())
        self.assertIs(
            get_schema("sdxl_feasibility_attempts"),
            SDXL_FEASIBILITY_ATTEMPTS_SCHEMA,
        )

    def test_worker_job_contains_pinned_execution_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work = root / "outputs" / "12" / "work" / "attempts"
            payload, job_path, result_path, output_path = build_worker_job(
                self.plan.iloc[0].to_dict(),
                self.config,
                project_root=root,
                work_directory=work,
            )
            self.assertEqual(payload["model_revision"], self.config["model"]["model_revision"])
            self.assertTrue(payload["model_cpu_offload"])
            self.assertFalse(payload["sequential_cpu_offload"])
            self.assertFalse(payload["attention_slicing"])
            self.assertEqual(payload["num_inference_steps"], 30)
            self.assertEqual((payload["inference_width"], payload["inference_height"]), (768, 768))
            self.assertEqual(job_path.parent, work.resolve())
            self.assertEqual(result_path.parent, work.resolve())
            self.assertEqual(output_path.parent, work.resolve())

    def test_local_cache_inspection_is_revision_pinned_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            hub = Path(temporary) / "hub"
            model_id = self.config["model"]["hf_model_id"].replace("/", "--")
            revision = self.config["model"]["model_revision"]
            snapshot = hub / f"models--{model_id}" / "snapshots" / revision
            snapshot.mkdir(parents=True)
            (snapshot / "model_index.json").write_text("{}", encoding="utf-8")
            audit = inspect_local_model_cache(
                self.config,
                environment={"HUGGINGFACE_HUB_CACHE": str(hub)},
            )
            self.assertTrue(audit["snapshot_exists"])
            self.assertTrue(audit["model_index_exists"])
            self.assertEqual(audit["file_count"], 1)
            self.assertEqual(audit["pinned_revision"], revision)

    def test_parent_watchdog_terminates_an_overlong_worker(self) -> None:
        result = run_worker_process(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            timeout_seconds=0.2,
        )
        self.assertTrue(result.timed_out)
        self.assertIsNotNone(result.return_code)
        self.assertLess(result.runtime_seconds, 3.0)

    def test_availability_distinguishes_hardware_from_infrastructure_failure(self) -> None:
        timed_out = self.plan.copy()
        timed_out.loc[0, ["status", "failure_type"]] = ["timed_out", "runtime_guardrail"]
        self.assertEqual(derive_availability_state(timed_out), "feasibility_only")

        oom = self.plan.copy()
        oom.loc[0, ["status", "failure_type"]] = ["failed", "cuda_out_of_memory"]
        self.assertEqual(derive_availability_state(oom), "feasibility_only")

        missing = self.plan.copy()
        missing.loc[0, ["status", "failure_type"]] = ["failed", "model_unavailable"]
        self.assertEqual(derive_availability_state(missing), "unavailable")

        broken = self.plan.copy()
        broken.loc[0, ["status", "failure_type"]] = ["failed", "worker_failure"]
        self.assertEqual(derive_availability_state(broken), "failed")


if __name__ == "__main__":
    unittest.main()
