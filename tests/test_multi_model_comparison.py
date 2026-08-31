from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.multi_model_comparison import (
    MULTI_MODEL_COMPARISON_MODULE_VERSION,
    attach_case_metadata,
    build_metric_disagreement,
    build_model_comparison,
    build_representative_case_rows,
    derive_case_dimensions,
    image_grid_to_data_uri,
    image_path_to_data_uri,
    load_multi_model_comparison_config,
    normalise_runtime_evidence,
    normalise_standard_metric_table,
    select_comparison_candidates,
    validate_metric_disagreement,
    validate_model_comparison,
    validate_representative_cases,
    validate_self_contained_report_html,
    validate_upstream_run_manifests,
)
from restoration_eval.schemas import (
    METRIC_DISAGREEMENT_SCHEMA,
    MODEL_COMPARISON_SCHEMA,
    REPRESENTATIVE_CASES_SCHEMA,
    get_schema,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/evaluation/multi_model_comparison.yaml"


class MultiModelComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_multi_model_comparison_config(CONFIG_PATH)

    def _small_config(self) -> dict:
        config = deepcopy(self.config)
        settings = config["multi_model_comparison"]
        settings["populations"]["core_three_model"].update({
            "exact_case_count": 2,
            "exact_candidate_count": 6,
        })
        settings["populations"]["four_model_subset"].update({
            "exact_case_count": 1,
            "exact_candidate_count": 4,
        })
        settings["expected_counts"].update({
            "selected_candidates": 7,
            "selected_candidates_by_model": {
                "opencv_telea": 2,
                "lama": 2,
                "stable_diffusion_inpainting": 2,
                "sdxl_inpainting": 1,
            },
            "unique_cases": 2,
            "core_case_count": 2,
            "core_candidate_count": 6,
            "four_model_case_count": 1,
            "four_model_candidate_count": 4,
        })
        settings["analysis_scopes"] = [{"scope_id": "overall", "column": None}]
        settings["ranking"]["minimum_paintings_for_stability"] = 2
        settings["report"]["minimum_embedded_analytical_views"] = 1
        settings["report"]["minimum_embedded_restoration_or_diagnostic_panels"] = 1
        return config

    @staticmethod
    def _candidate_inputs(root: Path) -> tuple[pd.DataFrame, ...]:
        cases = ["canonical__p001__scratch_thin", "canonical__p002__loss_large"]
        assets = {}
        for index, case_id in enumerate(cases, start=1):
            image = np.full((24, 32, 3), 50 * index, dtype=np.uint8)
            mask = np.zeros((24, 32), dtype=np.uint8)
            mask[8:16, 10:22] = 255
            for kind, array in {
                "clean": image,
                "damaged": np.where(mask[..., None] > 0, 240, image).astype(np.uint8),
                "mask": mask,
            }.items():
                path = root / f"{case_id}_{kind}.png"
                Image.fromarray(array).save(path)
                assets[(case_id, kind)] = path.relative_to(root).as_posix()

        def deterministic(model_id: str) -> pd.DataFrame:
            rows = []
            for index, case_id in enumerate(cases):
                restored = root / f"{model_id}_{index}.png"
                Image.new("RGB", (32, 24), (80 + index * 20, 90, 100)).save(restored)
                rows.append({
                    "restoration_id": f"restoration_{model_id}_{index}",
                    "case_id": case_id,
                    "model_id": model_id,
                    "candidate_id": f"candidate_{model_id}_{index}",
                    "restored_path": restored.relative_to(root).as_posix(),
                    "restored_sha256": f"{index + 1:064x}",
                    "runtime_seconds": 0.1 + index,
                    "status": "completed",
                })
            return pd.DataFrame(rows)

        sd_rows = []
        for index, case_id in enumerate(cases):
            restored = (
                root
                / "outputs/11_stable_diffusion_restoration"
                / "images/restored"
                / f"sd_{index}.png"
            )
            restored.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (32, 24), (100, 110 + index * 10, 120)).save(restored)
            sd_rows.append({
                "case_id": case_id,
                "painting_id": f"p00{index + 1}",
                "category": "portrait_figure" if index == 0 else "landscape_natural",
                "experiment_id": "canonical_missing_region",
                "damage_or_degradation_type": "binary_missing_region",
                "mask_or_effect_id": f"mask_{index}",
                "input_image_path": assets[(case_id, "damaged")],
                "clean_image_path": assets[(case_id, "clean")],
                "mask_or_effect_path": assets[(case_id, "mask")],
                "input_sha256": f"{10 + index:064x}",
                "mask_sha256": f"{20 + index:064x}",
                "candidate_id": f"candidate_sd_{index}",
                "model_id": "stable_diffusion_inpainting",
                "execution_role": "primary",
                "prompt_variant_id": "p00_generic",
                "restored_path": restored.relative_to(
                    root / "outputs/11_stable_diffusion_restoration"
                ).as_posix(),
                "restored_sha256": f"{30 + index:064x}",
                "runtime_seconds": 10.0 + index,
                "status": "completed",
            })
        sdxl_restored = root / "sdxl_0.png"
        Image.new("RGB", (32, 24), (130, 140, 150)).save(sdxl_restored)
        sdxl = pd.DataFrame([{
            **sd_rows[0],
            "candidate_id": "candidate_sdxl_0",
            "model_id": "sdxl_inpainting",
            "prompt_variant_id": "p00_generic",
            "technical_validation_passed": True,
            "restored_path": sdxl_restored.relative_to(root).as_posix(),
            "runtime_seconds": 50.0,
        }])
        return deterministic("opencv_telea"), deterministic("lama"), pd.DataFrame(sd_rows), sdxl

    @staticmethod
    def _semantic_metadata(selected: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for candidate in selected.itertuples(index=False):
            rows.append({
                "case_id": candidate.case_id,
                "painting_id": candidate.painting_id,
                "category": candidate.category,
                "style_or_period": "Baroque" if candidate.painting_id == "p001" else "not_recorded",
                "dataset_id": "painting_restoration_eval",
                "dataset_scope": "controlled_50",
                "experiment_id": candidate.experiment_id,
                "damage_or_degradation_type": candidate.damage_or_degradation_type,
                "target_damage_fraction": 0.02 if "scratch" in candidate.case_id else 0.125,
                "realized_damage_fraction": 0.021 if "scratch" in candidate.case_id else 0.13,
                "is_zero_control": False,
            })
        return pd.DataFrame(rows).drop_duplicates()

    def test_config_and_schema_registration(self) -> None:
        self.assertEqual(MULTI_MODEL_COMPARISON_MODULE_VERSION, "1.0.0")
        settings = self.config["multi_model_comparison"]
        self.assertEqual(settings["expected_counts"]["selected_candidates"], 1240)
        self.assertEqual(settings["expected_counts"]["four_model_case_count"], 10)
        self.assertTrue(settings["report"]["self_contained_html"])
        self.assertFalse(settings["ranking"]["combined_quality_score_retained"])
        self.assertIs(get_schema("model_comparison"), MODEL_COMPARISON_SCHEMA)
        self.assertIs(get_schema("metric_disagreement"), METRIC_DISAGREEMENT_SCHEMA)
        self.assertIs(get_schema("representative_cases"), REPRESENTATIVE_CASES_SCHEMA)

    def test_upstream_manifest_gate(self) -> None:
        manifests = {
            str(index): {
                "run_status": "completed",
                "validation_status": "passed",
                "completion_gate_passed": True,
            }
            for index in range(9, 21)
        }
        audit = validate_upstream_run_manifests(manifests)
        self.assertEqual(len(audit), 12)
        self.assertTrue(audit["passed"].all())
        manifests["15"]["completion_gate_passed"] = False
        self.assertFalse(validate_upstream_run_manifests(manifests)["passed"].all())

    def test_candidate_selection_and_case_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = self._candidate_inputs(root)
            selected = select_comparison_candidates(*inputs, config=self._small_config())
            self.assertEqual(len(selected), 7)
            self.assertEqual(selected["case_id"].nunique(), 2)
            self.assertEqual(
                selected.groupby("model_id").size().to_dict(),
                {
                    "lama": 2,
                    "opencv_telea": 2,
                    "sdxl_inpainting": 1,
                    "stable_diffusion_inpainting": 2,
                },
            )
            metadata = self._semantic_metadata(selected)
            enriched = attach_case_metadata(selected, metadata)
            scratch = enriched.loc[enriched["case_id"].str.contains("scratch")].iloc[0]
            self.assertEqual(scratch["damage_type"], "scratch_thin")
            self.assertEqual(scratch["target_damage_fraction_label"], "2%")
            self.assertEqual(enriched["style_or_period"].nunique(), 2)
            sd_paths = enriched.loc[
                enriched["model_id"].eq("stable_diffusion_inpainting"),
                "restored_path",
            ]
            self.assertTrue(
                sd_paths.str.startswith(
                    "outputs/11_stable_diffusion_restoration/images/"
                ).all()
            )

    def test_metric_normalization_comparison_and_disagreement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._small_config()
            selected = select_comparison_candidates(
                *self._candidate_inputs(root), config=config
            )
            selected = attach_case_metadata(selected, self._semantic_metadata(selected))
            rows = []
            model_penalty = {
                "opencv_telea": 0.2,
                "lama": 0.1,
                "stable_diffusion_inpainting": 0.3,
                "sdxl_inpainting": 0.15,
            }
            for candidate in selected.itertuples(index=False):
                rows.append({
                    "metric_row_id": f"mae_{candidate.candidate_id}",
                    "case_id": candidate.case_id,
                    "candidate_id": candidate.candidate_id,
                    "model_id": candidate.model_id,
                    "metric_family": "classical_pixel",
                    "metric_name": "mae",
                    "region_id": "masked_region",
                    "damaged_value": 0.5,
                    "restored_value": model_penalty[candidate.model_id],
                    "improvement_value": 0.5 - model_penalty[candidate.model_id],
                    "status": "ok",
                    "issue": "",
                })
            evidence = normalise_standard_metric_table(
                pd.DataFrame(rows), selected, source_key="classical", config=config
            )
            comparison = build_model_comparison(evidence, selected, config=config)
            validation = validate_model_comparison(comparison)
            self.assertTrue(validation["passed"], validation)
            overall_core = comparison.loc[
                comparison["population_id"].eq("core_three_model")
                & comparison["analysis_scope"].eq("overall")
            ]
            self.assertEqual(len(overall_core), 3)
            self.assertEqual(overall_core.iloc[0]["winner_model_id"], "lama")
            disagreement = build_metric_disagreement(comparison, config=config)
            disagreement_validation = validate_metric_disagreement(disagreement)
            self.assertTrue(disagreement_validation["passed"], disagreement_validation)
            self.assertTrue((~disagreement["is_conservation_truth"]).all())

    def test_comparison_preserves_exact_match_psnr_without_nan_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._small_config()
            selected = select_comparison_candidates(
                *self._candidate_inputs(root), config=config
            )
            selected = attach_case_metadata(selected, self._semantic_metadata(selected))
            values = {
                "opencv_telea": [np.inf, 50.0],
                "lama": [45.0, 45.0],
                "stable_diffusion_inpainting": [40.0, 40.0],
                "sdxl_inpainting": [42.0],
            }
            offsets = {model: 0 for model in values}
            rows = []
            for candidate in selected.itertuples(index=False):
                offset = offsets[candidate.model_id]
                restored = values[candidate.model_id][offset]
                offsets[candidate.model_id] += 1
                rows.append({
                    "metric_row_id": f"psnr_{candidate.candidate_id}",
                    "case_id": candidate.case_id,
                    "candidate_id": candidate.candidate_id,
                    "model_id": candidate.model_id,
                    "metric_family": "classical_pixel",
                    "metric_name": "psnr",
                    "region_id": "content_region",
                    "damaged_value": 20.0,
                    "restored_value": restored,
                    "improvement_value": restored - 20.0,
                    "status": "ok",
                    "issue": "",
                })
            evidence = normalise_standard_metric_table(
                pd.DataFrame(rows), selected, source_key="classical", config=config
            )
            comparison = build_model_comparison(evidence, selected, config=config)
            validation = validate_model_comparison(comparison)
            self.assertTrue(validation["passed"], validation)
            opencv = comparison.loc[
                comparison["population_id"].eq("core_three_model")
                & comparison["analysis_scope"].eq("overall")
                & comparison["model_id"].eq("opencv_telea")
            ].iloc[0]
            self.assertTrue(np.isposinf(opencv["restored_mean"]))
            self.assertTrue(np.isposinf(opencv["restored_std"]))
            self.assertFalse(pd.isna(opencv["restored_median"]))
            self.assertEqual(opencv["winner_status"], "winner")

    def test_runtime_is_paired_but_never_quality_ranked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._small_config()
            selected = select_comparison_candidates(
                *self._candidate_inputs(root), config=config
            )
            selected = attach_case_metadata(selected, self._semantic_metadata(selected))
            runtime = normalise_runtime_evidence(selected, config=config)
            self.assertEqual(set(runtime["source_notebook_id"]), {"09-12"})
            comparison = build_model_comparison(runtime, selected, config=config)
            validation = validate_model_comparison(comparison)
            self.assertTrue(validation["passed"], validation)
            overall = comparison.loc[comparison["analysis_scope"].eq("overall")]
            self.assertEqual(
                overall.groupby("population_id").size().to_dict(),
                {"core_three_model": 3, "sdxl_four_model_subset": 4},
            )
            self.assertFalse(comparison["quality_ranking_eligible"].any())
            self.assertTrue(comparison["aggregate_rank"].isna().all())
            self.assertTrue(comparison["winner_status"].eq("not_ranked").all())

    def test_representatives_and_self_contained_visuals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._small_config()
            selected = select_comparison_candidates(
                *self._candidate_inputs(root), config=config
            )
            selected = attach_case_metadata(selected, self._semantic_metadata(selected))
            slots = pd.DataFrame([{
                "selection_slot_id": "slot_01",
                "selection_role": "scratch_thin_deterministic_advantage",
                "selection_priority": 1,
                "population_id": "core_three_model",
                "case_id": "canonical__p001__scratch_thin",
                "selection_metric_id": "metric_mae",
                "selection_score": 1.0,
                "selection_rank": 1,
                "selection_reason": "deterministic test rule",
                "source_artifact_paths": "",
            }])
            representatives = build_representative_case_rows(
                slots, selected, config=config, project_root=root
            )
            validation = validate_representative_cases(representatives)
            self.assertTrue(validation["passed"], validation)
            self.assertEqual(len(representatives), 3)
            clean_path = root / representatives.iloc[0]["clean_image_path"]
            data_uri = image_path_to_data_uri(clean_path, max_dimension=100)
            self.assertTrue(data_uri.startswith("data:image/jpeg;base64,"))
            grid_uri = image_grid_to_data_uri(
                [("Clean", clean_path), ("Restored", root / representatives.iloc[0]["restored_path"])],
                columns=2,
            )
            self.assertTrue(grid_uri.startswith("data:image/jpeg;base64,"))
            html = (
                "<html><body><h1>RQ1 RQ2 RQ3</h1><h2>Conclusion</h2>"
                "<p>Limitation</p>"
                f'<img src="{data_uri}"><img src="{grid_uri}">'
                "</body></html>"
            )
            checks = validate_self_contained_report_html(html, config=config)
            self.assertTrue(checks["passed"].all(), checks.to_dict("records"))

    def test_synthetic_degradation_dimension(self) -> None:
        frame = pd.DataFrame([{
            "case_id": "synthetic_degradation__p001__water_stain__severe",
            "damage_or_degradation_type": "water_stain",
            "mask_or_effect_id": "water_stain__severe",
            "target_damage_fraction": np.nan,
        }])
        derived = derive_case_dimensions(frame).iloc[0]
        self.assertEqual(derived["damage_type"], "not_applicable")
        self.assertEqual(derived["degradation_type"], "water_stain")
        self.assertEqual(derived["severity"], "severe")


if __name__ == "__main__":
    unittest.main()
