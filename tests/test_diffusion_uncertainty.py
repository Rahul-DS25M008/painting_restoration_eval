from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.diffusion_uncertainty import (
    DIFFUSION_UNCERTAINTY_MODULE_VERSION,
    build_seed_reference_rows,
    build_uncertainty_calibration_inputs,
    build_uncertainty_pair_plan,
    build_uncertainty_population,
    compute_feature_pairwise_uncertainty,
    compute_group_image_uncertainty,
    compute_group_lpips_uncertainty,
    load_diffusion_uncertainty_config,
    load_latest_checkpoint,
    render_uncertainty_distributions,
    render_uncertainty_vs_performance,
    validate_uncertainty_calibration_inputs,
    validate_uncertainty_metrics,
    write_dataframe_checkpoint,
)
from restoration_eval.metrics_lpips import load_lpips_config
from restoration_eval.schemas import (
    DIFFUSION_UNCERTAINTY_SCHEMA,
    UNCERTAINTY_CALIBRATION_INPUTS_SCHEMA,
    get_schema,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/evaluation/diffusion_uncertainty.yaml"
LPIPS_CONFIG_PATH = ROOT / "config/evaluation/lpips.yaml"


class FakeLPIPS:
    def __call__(self, reference, candidate):
        return (reference - candidate).abs().mean(dim=(1, 2, 3), keepdim=True)


class DiffusionUncertaintyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_diffusion_uncertainty_config(CONFIG_PATH)
        cls.lpips_config = load_lpips_config(LPIPS_CONFIG_PATH)

    def _small_config(self) -> dict:
        config = deepcopy(self.config)
        expected = config["diffusion_uncertainty"]["expected_counts"]
        expected.update({
            "uncertainty_groups": 1,
            "unique_cases": 1,
            "candidates": 4,
            "unordered_candidate_pairs": 6,
            "generic_prompt_groups": 1,
            "scratch_aware_prompt_groups": 0,
            "pixel_group_summary_rows": 12,
            "pixel_pair_rows": 72,
            "lpips_pair_rows": 12,
            "feature_pair_rows": 24,
            "seed_reference_rows": 40,
            "uncertainty_metric_rows": 160,
            "calibration_rows": 1,
        })
        return config

    @staticmethod
    def _write_population_inputs(root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
        height, width = 32, 40
        yy, xx = np.mgrid[:height, :width]
        clean = np.stack([
            (xx * 5 + yy * 2) % 256,
            (yy * 7 + 20) % 256,
            ((xx + yy) * 4 + 30) % 256,
        ], axis=2).astype(np.uint8)
        mask = np.zeros((height, width), dtype=np.uint8)
        mask[9:24, 12:29] = 255
        damaged = clean.copy()
        damaged[mask > 0] = 245
        common_paths = {}
        for name, array in {"clean": clean, "damaged": damaged, "mask": mask}.items():
            path = root / f"{name}.png"
            Image.fromarray(array).save(path)
            common_paths[name] = path.relative_to(root).as_posix()

        records = []
        for candidate_index, seed in enumerate((2026, 2027, 2028, 2029)):
            restored = clean.copy().astype(np.int16)
            restored[mask > 0] = np.clip(
                restored[mask > 0] + candidate_index * 4, 0, 255
            )
            restored = restored.astype(np.uint8)
            restored_path = root / f"restored_{seed}.png"
            Image.fromarray(restored).save(restored_path)
            records.append({
                "candidate_id": f"candidate_{seed}",
                "case_id": "canonical__p001__scratch_thin",
                "model_id": "stable_diffusion_inpainting",
                "candidate_index": candidate_index,
                "seed": seed,
                "prompt_policy_id": "sd15_prompt_policy.v3",
                "prompt_variant_id": "p00_generic",
                "execution_role": "primary" if seed == 2026 else "uncertainty_extension",
                "configuration_id": "sd15_inpaint_fixed_policy_v1",
                "restored_path": restored_path.relative_to(root).as_posix(),
                "restored_sha256": f"sha{seed}",
                "mask_threshold": 128,
                "technical_validation_passed": True,
                "source_table_id": "notebook_11_stable_diffusion",
                "dataset_id": "painting_restoration_eval",
                "dataset_scope": "controlled_50",
                "experiment_id": "canonical_missing_region",
                "painting_id": "p001",
                "input_image_path": common_paths["damaged"],
                "clean_image_path": common_paths["clean"],
                "mask_or_effect_id": "mask_p001",
                "mask_or_effect_path": common_paths["mask"],
                "damage_or_degradation_type": "binary_missing_region",
                "target_damage_fraction": 0.05,
                "realized_damage_fraction": 0.06,
                "content_x_min": 0,
                "content_y_min": 0,
                "content_x_max": width,
                "content_y_max": height,
                "is_zero_control": False,
                "status": "completed",
            })
        artworks = pd.DataFrame([{
            "painting_id": "p001", "category": "portrait_figure",
            "style_or_period": "Baroque",
        }])
        return pd.DataFrame(records), artworks

    @staticmethod
    def _embedding_evidence(population: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
        records = []
        arrays: dict[str, list[np.ndarray]] = {
            "clip_embeddings": [], "dinov2_embeddings": [],
        }
        model_specs = {
            "clip_vit_b32": ("clip_embeddings", 6),
            "dinov2_vits14": ("dinov2_embeddings", 5),
        }
        for model_id, (array_name, dimension) in model_specs.items():
            for candidate_number, candidate in enumerate(population.itertuples(index=False)):
                for region_number, region_id in enumerate(("content_region", "mask_bbox_crop")):
                    vector = np.arange(1, dimension + 1, dtype=np.float32)
                    vector[(candidate_number + region_number) % dimension] += candidate_number * 0.2
                    vector /= np.linalg.norm(vector)
                    array_index = len(arrays[array_name])
                    arrays[array_name].append(vector)
                    records.append({
                        "feature_model_id": model_id,
                        "image_role": "restored",
                        "representative_candidate_id": candidate.candidate_id,
                        "region_id": region_id,
                        "array_name": array_name,
                        "array_index": array_index,
                        "status": "ok",
                    })
        matrices = {
            name: np.stack(vectors).astype(np.float32)
            for name, vectors in arrays.items()
        }
        return pd.DataFrame(records), matrices

    @staticmethod
    def _reference_sources(population: pd.DataFrame) -> dict[str, pd.DataFrame]:
        classical, lpips, feature, local = [], [], [], []
        for number, candidate in enumerate(population.itertuples(index=False), start=1):
            base = {"candidate_id": candidate.candidate_id, "status": "ok", "metric_version": "test.v1"}
            for metric_name, region_id, value in (
                ("mae", "masked_region", 10.0 + number),
                ("psnr", "content_region", 30.0 - number),
                ("ssim", "mask_bbox_crop", 0.9 - number * 0.01),
            ):
                classical.append({**base, "metric_name": metric_name, "region_id": region_id, "restored_value": value})
            lpips.append({**base, "metric_name": "lpips", "region_id": "mask_bbox_crop", "restored_value": 0.1 + number * 0.01})
            for metric_name, value in (
                ("clip_cosine_similarity", 0.8 - number * 0.01),
                ("dinov2_cosine_similarity", 0.75 - number * 0.01),
            ):
                feature.append({**base, "metric_name": metric_name, "region_id": "mask_bbox_crop", "restored_value": value})
            for metric_name, region_id, value, unit in (
                ("local_texture_error_p95", "mask_bbox_crop", 0.2 + number * 0.01, "normalized_error"),
                ("delta_e_ciede2000_mean", "masked_region", 2.0 + number * 0.1, "CIELAB_difference"),
                ("boundary_gradient_mismatch", "boundary_ring", 0.1 + number * 0.01, "normalized_error"),
                ("boundary_local_ssim_map_error", "boundary_ring", 0.05 + number * 0.01, "ssim_error"),
            ):
                local.append({**base, "metric_name": metric_name, "region_id": region_id, "restored_value": value, "value_unit": unit})
        return {
            "classical": pd.DataFrame(classical),
            "lpips": pd.DataFrame(lpips),
            "feature": pd.DataFrame(feature),
            "local_consistency": pd.DataFrame(local),
        }

    def test_config_and_schemas_are_registered(self) -> None:
        self.assertEqual(DIFFUSION_UNCERTAINTY_MODULE_VERSION, "1.0.3")
        self.assertIs(get_schema("diffusion_uncertainty"), DIFFUSION_UNCERTAINTY_SCHEMA)
        self.assertIs(
            get_schema("uncertainty_calibration_inputs"),
            UNCERTAINTY_CALIBRATION_INPUTS_SCHEMA,
        )
        settings = self.config["diffusion_uncertainty"]
        self.assertFalse(settings["metrics"]["combined_index"]["retained"])
        self.assertEqual(
            settings["population"]["sdxl_policy"],
            "not_applicable_insufficient_seed_coverage",
        )

    def test_complete_transparent_metric_and_calibration_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worklist, artworks = self._write_population_inputs(root)
            config = self._small_config()
            population = build_uncertainty_population(worklist, artworks, config=config)
            self.assertEqual(len(population), 4)
            pairs = build_uncertainty_pair_plan(population)
            self.assertEqual(len(pairs), 6)

            image_metrics = compute_group_image_uncertainty(
                population, project_root=root, config=config
            )
            self.assertEqual(len(image_metrics), 84)
            lpips_metrics = compute_group_lpips_uncertainty(
                population, model=FakeLPIPS(), device="cpu", project_root=root,
                config=config, lpips_config=self.lpips_config,
            )
            self.assertEqual(len(lpips_metrics), 12)
            manifest, arrays = self._embedding_evidence(population)
            feature_metrics = compute_feature_pairwise_uncertainty(
                population, embedding_manifest=manifest, embedding_arrays=arrays,
                config=config,
            )
            self.assertEqual(len(feature_metrics), 24)
            reference_metrics = build_seed_reference_rows(
                population, self._reference_sources(population), config=config
            )
            self.assertEqual(len(reference_metrics), 40)

            metrics = pd.concat(
                [image_metrics, lpips_metrics, feature_metrics, reference_metrics],
                ignore_index=True,
            )
            validation = validate_uncertainty_metrics(metrics, population, config=config)
            self.assertTrue(validation["passed"], validation)
            calibration = build_uncertainty_calibration_inputs(
                population, metrics, config=config
            )
            self.assertEqual(len(calibration), 1)
            calibration_validation = validate_uncertainty_calibration_inputs(
                calibration, config=config
            )
            self.assertTrue(calibration_validation["passed"], calibration_validation)
            self.assertFalse(calibration["combined_uncertainty_index_available"].any())

            calibration_path = root / "calibration_round_trip.csv"
            calibration.to_csv(calibration_path, index=False)
            reloaded_calibration = pd.read_csv(calibration_path, low_memory=False)
            round_trip_validation = validate_uncertainty_calibration_inputs(
                reloaded_calibration, config=config
            )
            self.assertTrue(round_trip_validation["passed"], round_trip_validation)

    def test_checkpoint_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "checkpoint.csv"
            frame = pd.DataFrame(columns=DIFFUSION_UNCERTAINTY_SCHEMA.required_columns)
            result = write_dataframe_checkpoint(frame, target)
            self.assertEqual(result["status"], "canonical")
            loaded, path = load_latest_checkpoint(target)
            self.assertEqual(path, target)
            self.assertEqual(tuple(loaded.columns), DIFFUSION_UNCERTAINTY_SCHEMA.required_columns)

    def test_distribution_figure_uses_current_matplotlib_boxplot_api(self) -> None:
        calibration = pd.DataFrame({
            "prompt_variant_id": [
                "p00_generic", "p00_generic",
                "p05_scratch_aware", "p05_scratch_aware",
            ],
            "rgb_std_mean_masked": [0.01, 0.02, 0.015, 0.018],
            "rgb_pair_mae_mean_masked": [0.02, 0.03, 0.021, 0.025],
            "lpips_pair_mean_crop": [0.04, 0.05, 0.043, 0.047],
            "clip_pair_distance_mean_crop": [0.06, 0.07, 0.063, 0.068],
            "dino_pair_distance_mean_crop": [0.08, 0.09, 0.082, 0.087],
            "seam_gradient_mismatch_mean": [0.10, 0.11, 0.103, 0.108],
        })
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "distributions.png"
            rendered = render_uncertainty_distributions(calibration, target)
            self.assertEqual(rendered, target)
            with Image.open(rendered) as image:
                image.load()
                self.assertEqual(image.format, "PNG")
                self.assertGreater(image.width, 0)
                self.assertGreater(image.height, 0)

    def test_performance_figure_renders_with_reserved_title_and_legend_space(self) -> None:
        calibration = pd.DataFrame({
            "prompt_variant_id": [
                "p00_generic", "p00_generic",
                "p05_scratch_aware", "p05_scratch_aware",
            ],
            "rgb_pair_mae_mean_masked": [0.02, 0.03, 0.021, 0.025],
            "reference_mae_masked_mean": [20.0, 25.0, 21.0, 24.0],
            "lpips_pair_mean_crop": [0.04, 0.05, 0.043, 0.047],
            "reference_lpips_crop_mean": [0.10, 0.12, 0.11, 0.115],
            "clip_pair_distance_mean_crop": [0.006, 0.007, 0.0063, 0.0068],
            "reference_clip_crop_mean": [0.95, 0.96, 0.955, 0.958],
            "rgb_std_mean_masked": [0.01, 0.02, 0.015, 0.018],
            "seam_gradient_mismatch_mean": [0.03, 0.04, 0.032, 0.038],
        })
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "performance.png"
            rendered = render_uncertainty_vs_performance(calibration, target)
            self.assertEqual(rendered, target)
            with Image.open(rendered) as image:
                image.load()
                self.assertEqual(image.format, "PNG")
                self.assertGreater(image.width, 0)
                self.assertGreater(image.height, 0)


if __name__ == "__main__":
    unittest.main()
