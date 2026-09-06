from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from restoration_eval.hint_mat_selection import (
    CANDIDATE_COLUMNS,
    DECISION_SCORECARD_COLUMNS,
    METRIC_VALUE_COLUMNS,
    SELECTION_SCOPE_COLUMNS,
    build_candidate_plan,
    build_selection_scope,
    exact_mask_composite,
    inspect_external_assets,
    load_selection_config,
    prepare_model_inputs,
    run_worker_process,
    validate_candidate_table,
    validate_restored_output,
    validate_zero_control_qa,
    worker_command,
)
from restoration_eval.schemas import (
    HINT_MAT_CANDIDATES_SCHEMA,
    HINT_MAT_CANDIDATE_COLUMNS,
    HINT_MAT_DECISION_SCORECARD_COLUMNS,
    HINT_MAT_METRIC_VALUE_COLUMNS,
    HINT_MAT_SELECTION_SCOPE_COLUMNS,
    get_schema,
    validate_dataframe,
)


CONFIG_PATH = PROJECT_ROOT / "config" / "experiments" / "hint_mat_selection.yaml"
CASE_REGISTRY_PATH = (
    PROJECT_ROOT / "outputs" / "08_experiment_contracts_and_region_policy"
    / "data" / "case_registry.csv"
)
ARTWORKS_PATH = PROJECT_ROOT / "outputs" / "01_dataset_verification" / "data" / "artworks.csv"


class HintMatContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_selection_config(CONFIG_PATH)
        cls.case_registry = pd.read_csv(CASE_REGISTRY_PATH)
        cls.artworks = pd.read_csv(ARTWORKS_PATH)
        cls.scope = build_selection_scope(cls.case_registry, cls.artworks, cls.config)
        cls.candidates = build_candidate_plan(cls.scope, cls.config)

    def test_exact_scope_and_balance(self) -> None:
        self.assertEqual(len(self.scope), 12)
        self.assertEqual(self.scope["case_id"].nunique(), 12)
        self.assertEqual(self.scope["damage_type"].value_counts().to_dict(), {
            "loss_large": 3,
            "mixed_damage": 3,
            "loss_small": 3,
            "scratch_thin": 3,
        })
        self.assertGreaterEqual(int(self.scope.groupby("category").size().min()), 2)
        self.assertEqual(list(self.scope.columns), list(SELECTION_SCOPE_COLUMNS))
        self.assertEqual(tuple(SELECTION_SCOPE_COLUMNS), tuple(HINT_MAT_SELECTION_SCOPE_COLUMNS))

    def test_zero_control_is_qa_only(self) -> None:
        row = validate_zero_control_qa(self.case_registry, self.config)
        self.assertEqual(row["case_id"], "canonical__p001__zero_control")
        self.assertNotIn(row["case_id"], set(self.scope["case_id"]))

    def test_candidate_plan_is_paired_and_non_metric(self) -> None:
        self.assertEqual(len(self.candidates), 24)
        self.assertEqual(self.candidates["candidate_id"].nunique(), 24)
        self.assertEqual(set(self.candidates["model_id"]), {
            "hint_places2", "mat_places_512_fulldata"
        })
        self.assertTrue(self.candidates.groupby("case_id")["model_id"].nunique().eq(2).all())
        self.assertEqual(list(self.candidates.columns), list(CANDIDATE_COLUMNS))
        self.assertEqual(tuple(CANDIDATE_COLUMNS), tuple(HINT_MAT_CANDIDATE_COLUMNS))
        validate_candidate_table(self.candidates)
        result = validate_dataframe(self.candidates, HINT_MAT_CANDIDATES_SCHEMA)
        self.assertTrue(result.passed, result.to_dict())

    def test_schema_registry_contains_all_n37_contracts(self) -> None:
        self.assertIs(get_schema("hint_mat_candidates"), HINT_MAT_CANDIDATES_SCHEMA)
        self.assertEqual(tuple(METRIC_VALUE_COLUMNS), tuple(HINT_MAT_METRIC_VALUE_COLUMNS))
        self.assertEqual(
            tuple(DECISION_SCORECARD_COLUMNS), tuple(HINT_MAT_DECISION_SCORECARD_COLUMNS)
        )

    def test_external_asset_audit_uses_environment_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hint_repo = root / "HINT"
            mat_repo = root / "MAT"
            for relative in ("src/networks.py", "src/models.py", "LICENSE"):
                path = hint_repo / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("test", encoding="utf-8")
            (hint_repo / ".git").mkdir(parents=True)
            (hint_repo / ".git" / "HEAD").write_text(
                self.config["external_assets"]["hint"]["repository_revision"],
                encoding="utf-8",
            )
            for relative in ("generate_image.py", "legacy.py", "networks/mat.py", "LICENSE"):
                path = mat_repo / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("test", encoding="utf-8")
            (mat_repo / ".git").mkdir(parents=True)
            (mat_repo / ".git" / "HEAD").write_text(
                self.config["external_assets"]["mat"]["repository_revision"],
                encoding="utf-8",
            )
            hint_checkpoint = root / "hint.pth"
            mat_checkpoint = root / "mat.pkl"
            hint_checkpoint.write_bytes(b"hint")
            mat_checkpoint.write_bytes(b"mat")
            environment = {
                "HINT_REPO_ROOT": str(hint_repo),
                "HINT_CHECKPOINT_PATH": str(hint_checkpoint),
                "MAT_REPO_ROOT": str(mat_repo),
                "MAT_CHECKPOINT_PATH": str(mat_checkpoint),
            }
            audit = inspect_external_assets(self.config, environment=environment)
            self.assertTrue(audit["ready"].all())
            self.assertTrue(audit["repository_revision_matches"].all())
            self.assertTrue(audit["checkpoint_sha256"].str.len().eq(64).all())

    def test_adapter_mask_semantics_and_exact_composite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_path = root / "input.png"
            mask_path = root / "mask.png"
            output_path = root / "output.png"
            source = np.full((768, 768, 3), 40, dtype=np.uint8)
            mask = np.zeros((768, 768), dtype=np.uint8)
            mask[100:200, 300:450] = 255
            Image.fromarray(source, mode="RGB").save(input_path)
            Image.fromarray(mask, mode="L").save(mask_path)

            _, hint_mask, missing, source_768 = prepare_model_inputs(
                input_path, mask_path, inference_size=512
            )
            _, mat_mask, _, _ = prepare_model_inputs(
                input_path, mask_path, inference_size=512, mat_mask_semantics=True
            )
            self.assertTrue(np.array_equal(mat_mask, 1 - hint_mask))
            generated = np.full((512, 512, 3), 210, dtype=np.uint8)
            composite = exact_mask_composite(generated, source_768, missing)
            Image.fromarray(composite, mode="RGB").save(output_path)
            audit = validate_restored_output(output_path, input_path, mask_path)
            self.assertTrue(audit["technical_validation_passed"])
            self.assertEqual(audit["outside_mask_changed_pixels"], 0)
            self.assertTrue((composite[missing.astype(bool)] == 210).all())

    def test_worker_watchdog_and_commands(self) -> None:
        result = run_worker_process(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            timeout_seconds=0.2,
        )
        self.assertTrue(result.timed_out)
        self.assertLess(result.runtime_seconds, 3.0)
        self.assertIn("restoration_hint_worker", " ".join(worker_command("hint", CONFIG_PATH)))
        self.assertIn("restoration_mat_worker", " ".join(worker_command("mat", CONFIG_PATH)))


if __name__ == "__main__":
    unittest.main()
