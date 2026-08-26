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
    BatchWorkerProcessResult,
    build_batch_worker_job,
    build_partial_candidate_plan,
    derive_partial_availability_state,
    finalize_partial_execution,
    materialize_partial_input_checksums,
    run_batch_worker_process,
    select_partial_evaluation_scope,
    validate_cross_method_comparability,
    write_partial_checkpoint,
    derive_availability_state,
    inspect_local_model_cache,
    load_sdxl_config,
    run_worker_process,
    select_feasibility_case,
)
from restoration_eval.schemas import (
    SDXL_FEASIBILITY_ATTEMPTS_SCHEMA,
    SDXL_PARTIAL_CANDIDATES_SCHEMA,
    SDXL_PARTIAL_CANDIDATE_COLUMNS,
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


@unittest.skip("Legacy v1 feasibility contract retained for provenance only")
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




class SDXLPartialEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_sdxl_config(CONFIG_PATH)
        cls.worklist = build_sdxl_eligible_worklist(
            pd.read_csv(CASE_REGISTRY_PATH),
            pd.read_csv(MODEL_ELIGIBILITY_PATH),
            pd.read_csv(ARTWORKS_PATH),
            cls.config,
        )
        cls.scope = select_partial_evaluation_scope(cls.worklist, cls.config)
        cls.plan = build_partial_candidate_plan(cls.scope, cls.config)

    def test_configuration_freezes_bounded_quality_contract(self) -> None:
        execution = self.config["execution"]
        model = self.config["model"]
        memory = self.config["memory_strategy"]
        self.assertEqual(execution["mode"], "partial_evaluation")
        self.assertEqual(execution["global_budget_seconds"], 7200)
        self.assertEqual(execution["per_case_timeout_seconds"], 900)
        self.assertEqual(execution["minimum_seconds_to_start_case"], 660)
        self.assertFalse(execution["retry_failed_attempts"])
        self.assertTrue(memory["persistent_pipeline"])
        self.assertTrue(memory["model_cpu_offload"])
        self.assertFalse(memory["sequential_cpu_offload"])
        self.assertEqual((model["inference_width"], model["inference_height"]), (768, 768))
        self.assertEqual(model["num_inference_steps"], 30)
        self.assertEqual(model["seed"], 2026)
        self.assertEqual(SDXL_HELPER_VERSION, "3.0.0")

    def test_exact_scope_and_diversity_first_order(self) -> None:
        expected = [
            "canonical__p039__loss_large",
            "canonical__p018__mixed_damage",
            "synthetic_degradation__p043__partial_transparency__severe",
            "synthetic_degradation__p026__water_stain_dirt__moderate",
            "synthetic_degradation__p001__water_stain__severe",
            "synthetic_degradation__p018__dirt_dust__severe",
            "canonical__p001__loss_large",
            "canonical__p043__mixed_damage",
            "synthetic_degradation__p039__water_stain__severe",
            "synthetic_degradation__p026__dirt_dust__severe",
        ]
        self.assertEqual(len(self.worklist), 410)
        self.assertEqual(int(self.worklist["is_zero_control"].sum()), 50)
        self.assertEqual(self.scope["case_id"].tolist(), expected)
        self.assertEqual(self.scope["painting_id"].nunique(), 5)
        self.assertEqual(self.scope.groupby("painting_id").size().unique().tolist(), [2])

    def test_real_cross_method_coverage_is_exact(self) -> None:
        audit = validate_cross_method_comparability(
            self.scope,
            pd.read_csv(self.config["inputs"]["telea_restorations_path"]),
            pd.read_csv(self.config["inputs"]["lama_restorations_path"]),
            pd.read_csv(self.config["inputs"]["stable_diffusion_candidates_path"]),
        )
        self.assertEqual(len(audit), 30)
        self.assertTrue(audit["coverage_passed"].all())
        self.assertEqual(set(audit["matching_completed_rows"]), {1})

    def test_candidate_plan_schema_thresholds_and_paths(self) -> None:
        self.assertEqual(len(self.plan), 10)
        self.assertEqual(list(self.plan.columns), list(SDXL_PARTIAL_CANDIDATE_COLUMNS))
        validation = validate_dataframe(self.plan, SDXL_PARTIAL_CANDIDATES_SCHEMA)
        self.assertTrue(validation.passed, validation.to_dict())
        canonical = self.plan["experiment_id"].eq("canonical_missing_region")
        self.assertEqual(set(self.plan.loc[canonical, "mask_threshold"]), {128})
        self.assertEqual(set(self.plan.loc[~canonical, "mask_threshold"]), {13})
        self.assertTrue(self.plan["restored_path"].str.endswith(".png").all())
        self.assertEqual(self.plan["candidate_id"].nunique(), 10)

    def test_materialized_checksums_and_batch_job(self) -> None:
        checked = materialize_partial_input_checksums(
            self.plan, project_root=Path.cwd()
        )
        self.assertTrue(checked["input_sha256"].str.len().eq(64).all())
        self.assertTrue(checked["mask_sha256"].str.len().eq(64).all())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "outputs" / "12"
            payload, job_path, result_path, checkpoint_path, progress_path = (
                build_batch_worker_job(
                    checked,
                    self.config,
                    project_root=Path.cwd(),
                    notebook_output_root=output,
                )
            )
            self.assertEqual(payload["job_schema_version"], "sdxl_batch_worker_job.v1")
            self.assertEqual(len(payload["candidates"]), 10)
            self.assertTrue(payload["memory_strategy"]["persistent_pipeline"])
            self.assertEqual(job_path, output.resolve() / self.config["output"]["worker_job_path"])
            self.assertEqual(result_path, output.resolve() / self.config["output"]["worker_result_path"])
            self.assertEqual(checkpoint_path, output.resolve() / self.config["output"]["checkpoint_path"])
            self.assertEqual(progress_path, output.resolve() / self.config["output"]["progress_path"])

    def test_local_cache_inspection_remains_revision_pinned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            hub = Path(temporary) / "hub"
            model_id = self.config["model"]["hf_model_id"].replace("/", "--")
            revision = self.config["model"]["model_revision"]
            snapshot = hub / f"models--{model_id}" / "snapshots" / revision
            snapshot.mkdir(parents=True)
            (snapshot / "model_index.json").write_text("{}", encoding="utf-8")
            audit = inspect_local_model_cache(
                self.config, environment={"HUGGINGFACE_HUB_CACHE": str(hub)}
            )
            self.assertTrue(audit["snapshot_exists"])
            self.assertTrue(audit["model_index_exists"])
            self.assertEqual(audit["pinned_revision"], revision)

    def test_parent_global_watchdog_terminates_worker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            progress = Path(temporary) / "progress.json"
            result = run_batch_worker_process(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                progress_path=progress,
                global_budget_seconds=0.2,
                per_case_timeout_seconds=5,
                poll_seconds=0.05,
            )
        self.assertEqual(result.termination_reason, "global_budget_exhausted")
        self.assertTrue(result.terminated)
        self.assertLess(result.runtime_seconds, 3.0)

    def test_parent_case_watchdog_uses_worker_heartbeat(self) -> None:
        import json
        import time
        with tempfile.TemporaryDirectory() as temporary:
            progress = Path(temporary) / "progress.json"
            progress.write_text(json.dumps({
                "current_candidate_id": self.plan.iloc[0]["candidate_id"],
                "case_started_epoch_seconds": time.time() - 1,
            }), encoding="utf-8")
            result = run_batch_worker_process(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                progress_path=progress,
                global_budget_seconds=5,
                per_case_timeout_seconds=0.2,
                poll_seconds=0.05,
            )
        self.assertEqual(result.termination_reason, "runtime_guardrail")
        self.assertEqual(result.current_candidate_id, self.plan.iloc[0]["candidate_id"])

    def test_termination_reconciliation_keeps_all_rows_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkpoint = root / "candidate_checkpoint.csv"
            progress = root / "progress.json"
            write_partial_checkpoint(self.plan, checkpoint)
            progress.write_text("{}", encoding="utf-8")
            process = BatchWorkerProcessResult(
                return_code=1,
                runtime_seconds=900.0,
                termination_reason="runtime_guardrail",
                current_candidate_id=self.plan.iloc[0]["candidate_id"],
                stdout="",
                stderr="",
            )
            final = finalize_partial_execution(
                self.plan,
                process,
                checkpoint_path=checkpoint,
                progress_path=progress,
            )
        self.assertEqual(len(final), 10)
        self.assertEqual((final["status"] == "timed_out").sum(), 1)
        self.assertEqual((final["status"] == "skipped").sum(), 9)
        self.assertEqual(set(final["availability_state"]), {"feasibility_only"})
        self.assertEqual(
            derive_partial_availability_state(final), "feasibility_only"
        )

if __name__ == "__main__":
    unittest.main()
