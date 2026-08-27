from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from restoration_eval.evaluation_inputs import (
    build_evaluation_worklist,
    validate_evaluation_worklist,
)
from restoration_eval.metrics_classical import load_classical_metrics_config

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/evaluation/metrics.yaml"


class EvaluationInputsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_classical_metrics_config(CONFIG_PATH)

    def _real_bundle(self):
        inputs = self.config["classical_metrics"]["inputs"]
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
        return build_evaluation_worklist(
            cases,
            eligibility,
            geometry,
            tables,
            candidate_source_roots=source_roots,
        )

    def test_real_handoffs_normalize_to_approved_candidate_universe(self) -> None:
        bundle = self._real_bundle()
        worklist = bundle.worklist
        validation = validate_evaluation_worklist(worklist)
        self.assertTrue(validation["passed"], validation)
        self.assertEqual(len(worklist), 2160)
        self.assertEqual(int(worklist["is_zero_control"].sum()), 150)
        self.assertEqual(len(bundle.exclusions), 0)
        self.assertEqual(
            worklist["model_id"].value_counts().to_dict(),
            {
                "stable_diffusion_inpainting": 1330,
                "opencv_telea": 410,
                "lama": 410,
                "sdxl_inpainting": 10,
            },
        )
        sdxl = worklist.loc[worklist["model_id"].eq("sdxl_inpainting")]
        self.assertEqual(len(sdxl), 10)
        self.assertEqual(sdxl["experiment_id"].value_counts().to_dict(), {
            "synthetic_degradation": 6,
            "canonical_missing_region": 4,
        })
        self.assertTrue(sdxl["technical_validation_passed"].all())
        self.assertTrue(
            worklist["restored_path"].map(lambda value: (ROOT / value).is_file()).all()
        )
        stable_diffusion = worklist.loc[
            worklist["model_id"].eq("stable_diffusion_inpainting")
        ]
        self.assertTrue(
            stable_diffusion["restored_path"].str.startswith(
                "outputs/11_stable_diffusion_restoration/images/restored/"
            ).all()
        )

    def test_noncompleted_and_technical_failures_are_explicit_exclusions(self) -> None:
        cases = pd.DataFrame([{
            "case_id": "case", "dataset_id": "dataset", "dataset_scope": "scope",
            "experiment_id": "canonical_missing_region", "painting_id": "p001",
            "input_image_path": "input.png", "clean_image_path": "clean.png",
            "mask_or_effect_id": "mask", "mask_or_effect_path": "mask.png",
            "damage_or_degradation_type": "binary_missing_region",
            "target_damage_fraction": 0.1, "realized_damage_fraction": 0.1,
            "status": "passed",
        }])
        eligibility = pd.DataFrame([{
            "case_id": "case", "model_id": "model", "eligible": True,
        }])
        geometry = pd.DataFrame([{
            "painting_id": "p001", "content_x_min": 0, "content_y_min": 0,
            "content_x_max": 16, "content_y_max": 16, "status": "passed",
        }])
        candidates = pd.DataFrame([
            {"candidate_id": "failed", "case_id": "case", "model_id": "model",
             "candidate_index": 0, "configuration_id": "cfg",
             "restored_path": "", "restored_sha256": "", "mask_threshold": 128,
             "technical_validation_passed": False, "status": "failed"},
        ])
        bundle = build_evaluation_worklist(
            cases, eligibility, geometry, {"source": candidates}
        )
        self.assertEqual(len(bundle.worklist), 0)
        self.assertEqual(len(bundle.exclusions), 1)
        self.assertEqual(
            bundle.exclusions.iloc[0]["exclusion_reason"],
            "source_status_not_completed",
        )


if __name__ == "__main__":
    unittest.main()
