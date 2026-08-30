from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.schemas import (
    SEMANTIC_MAP_ASSET_SCHEMA,
    SEMANTIC_STRUCTURAL_METRIC_SCHEMA,
    get_schema,
    validate_dataframe,
)
from restoration_eval.semantic_structural import (
    SEMANTIC_STRUCTURAL_MODULE_VERSION,
    affinity_weighted_similarity,
    affinity_layout_metrics,
    build_semantic_map_asset_record,
    build_semantic_metric_record,
    build_semantic_population,
    compute_local_semantic_bundle,
    feature_compatible_config,
    letterbox_rgb,
    letterbox_support_mask,
    load_semantic_map_archive,
    load_semantic_structural_config,
    local_worsened_fraction,
    map_agreement,
    patch_covariance_distance,
    render_semantic_panel,
    select_semantic_map_candidates,
    semantic_target_scope,
    summarize_similarity_channel,
    token_support_fraction,
    validate_semantic_map_manifest,
    validate_semantic_metrics,
    write_semantic_map_archive,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/evaluation/semantic_structural.yaml"


class SemanticStructuralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_semantic_structural_config(CONFIG_PATH)

    def _small_config(self) -> dict:
        config = deepcopy(self.config)
        expected = config["semantic_structural"]["expected_counts"]
        expected.update({
            "evaluated_cases": 2,
            "evaluated_candidates": 3,
            "nonzero_candidates": 2,
            "zero_control_candidates": 1,
            "candidates_by_model": {
                "opencv_telea": 1,
                "lama": 1,
                "stable_diffusion_inpainting": 1,
                "sdxl_inpainting": 0,
            },
            "rendered_semantic_panels": 2,
            "semantic_metric_rows": 1,
            "map_manifest_rows": 2,
        })
        return config

    @staticmethod
    def _population_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
        common = {
            "restored_sha256": "a" * 64,
            "input_image_path": "damaged.png",
            "clean_image_path": "clean.png",
            "mask_or_effect_path": "mask.png",
            "mask_threshold": 128,
            "content_x_min": 0,
            "content_y_min": 0,
            "content_x_max": 32,
            "content_y_max": 24,
            "status": "completed",
            "dataset_id": "painting_restoration_eval",
            "dataset_scope": "controlled_50",
            "experiment_id": "canonical_missing_region",
            "damage_or_degradation_type": "binary_missing_region",
            "target_damage_fraction": 0.05,
            "realized_damage_fraction": 0.05,
            "candidate_index": 0,
            "seed": 2026,
            "prompt_policy_id": "policy",
            "prompt_variant_id": "p00_generic",
        }
        worklist = pd.DataFrame([
            {
                **common,
                "case_id": "case_a",
                "candidate_id": "opencv_a",
                "model_id": "opencv_telea",
                "painting_id": "p001",
                "restored_path": "opencv.png",
                "is_zero_control": False,
                "execution_role": "deterministic_primary",
            },
            {
                **common,
                "case_id": "case_a",
                "candidate_id": "stable_a",
                "model_id": "stable_diffusion_inpainting",
                "painting_id": "p001",
                "restored_path": "stable.png",
                "is_zero_control": False,
                "execution_role": "primary",
            },
            {
                **common,
                "case_id": "case_b",
                "candidate_id": "lama_b",
                "model_id": "lama",
                "painting_id": "p002",
                "restored_path": "lama.png",
                "is_zero_control": True,
                "execution_role": "deterministic_primary",
            },
        ])
        artworks = pd.DataFrame([
            {
                "painting_id": "p001",
                "category": "portrait_figure",
                "style_or_period": "Baroque",
            },
            {
                "painting_id": "p002",
                "category": "architecture_structured",
                "style_or_period": "Modern",
            },
        ])
        return worklist, artworks

    @staticmethod
    def _metric_metadata() -> dict:
        return {
            "case_id": "case_a",
            "candidate_id": "candidate_a",
            "model_id": "lama",
            "painting_id": "p001",
            "category": "portrait_figure",
            "style_or_period": "Baroque",
            "dataset_id": "painting_restoration_eval",
            "dataset_scope": "controlled_50",
            "experiment_id": "canonical_missing_region",
            "damage_or_degradation_type": "binary_missing_region",
            "target_damage_fraction": 0.05,
            "realized_damage_fraction": 0.05,
            "candidate_index": 0,
            "seed": 2026,
            "prompt_policy_id": "deterministic",
            "prompt_variant_id": "not_applicable",
            "execution_role": "deterministic_primary",
            "is_zero_control": False,
            "semantic_target_scope": "facial_anatomical_structure_proxy",
            "applicability_status": "applicable",
        }

    def test_config_arithmetic_and_schema_registration(self) -> None:
        settings = self.config["semantic_structural"]
        self.assertEqual(SEMANTIC_STRUCTURAL_MODULE_VERSION, "1.0.3")
        self.assertEqual(settings["expected_counts"]["semantic_metric_rows"], 58980)
        self.assertEqual(settings["expected_counts"]["map_manifest_rows"], 9430)
        self.assertEqual(settings["expected_counts"]["canonical_file_count"], 1097)
        self.assertFalse(settings["evidence_policy"]["combined_semantic_score_retained"])
        self.assertIs(
            get_schema("semantic_structural_metrics"),
            SEMANTIC_STRUCTURAL_METRIC_SCHEMA,
        )
        self.assertIs(get_schema("semantic_map_assets"), SEMANTIC_MAP_ASSET_SCHEMA)
        compatible = feature_compatible_config(self.config)["feature_similarity"]
        self.assertEqual(set(compatible["models"]), {"clip_vit_b32", "dinov2_vits14"})

    def test_category_scope_and_population_selection(self) -> None:
        self.assertEqual(
            semantic_target_scope("portrait_figure", self.config),
            "facial_anatomical_structure_proxy",
        )
        worklist, artworks = self._population_inputs()
        config = self._small_config()
        population = build_semantic_population(worklist, artworks, config=config)
        self.assertEqual(len(population), 3)
        self.assertEqual(population["semantic_target_scope"].nunique(), 2)
        selected = select_semantic_map_candidates(population, config=config)
        self.assertEqual(set(selected["candidate_id"]), {"opencv_a", "stable_a"})

    def test_letterbox_and_token_support(self) -> None:
        image = np.full((12, 24, 3), 120, dtype=np.uint8)
        boxed, valid = letterbox_rgb(image, size=28, fill_rgb=(100, 101, 102))
        self.assertEqual(boxed.shape, (28, 28, 3))
        self.assertEqual(valid.shape, (28, 28))
        self.assertGreater(valid.mean(), 0.45)
        self.assertLess(valid.mean(), 0.55)
        support = token_support_fraction(valid, (7, 7))
        self.assertEqual(support.shape, (7, 7))
        self.assertTrue(((support >= 0.0) & (support <= 1.0)).all())
        active = np.zeros((12, 24), dtype=np.float32)
        active[:, :12] = 1.0
        weighted = letterbox_support_mask(active, size=28, grid_shape=(7, 7))
        self.assertEqual(weighted.shape, (7, 7))
        self.assertGreater(float(weighted.sum()), 5.0)
        self.assertLess(float(weighted.sum()), 15.0)

    def test_local_bundle_and_summaries(self) -> None:
        clean = np.zeros((2, 2, 3), dtype=np.float32)
        clean[..., 0] = 1.0
        damaged = clean.copy()
        damaged[0, 0] = np.array([0.0, 1.0, 0.0])
        restored = clean.copy()
        restored[1, 1] = np.array([0.8, 0.6, 0.0])
        valid = np.array([[True, True], [True, False]])
        bundle = compute_local_semantic_bundle(
            clean, damaged, restored, clean_global=np.array([1.0, 0.0, 0.0]),
            valid_token_mask=valid,
        )
        self.assertEqual(bundle.shape, (2, 2, 7))
        self.assertTrue(np.isnan(bundle[1, 1]).all())
        self.assertAlmostEqual(float(bundle[0, 0, 2]), 1.0, places=6)
        summary = summarize_similarity_channel(bundle[..., 1])
        self.assertAlmostEqual(summary["mean"], 1.0, places=6)
        self.assertEqual(local_worsened_fraction(bundle[..., 2]), 0.0)

    def test_layout_covariance_and_encoder_agreement(self) -> None:
        reference = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
        identical = affinity_layout_metrics(reference, reference.copy())
        self.assertAlmostEqual(identical["correlation"], 1.0, places=7)
        self.assertAlmostEqual(identical["js_divergence"], 0.0, places=7)
        self.assertAlmostEqual(identical["centroid_shift"], 0.0, places=7)
        self.assertAlmostEqual(
            affinity_weighted_similarity(reference, np.ones_like(reference)),
            1.0,
            places=7,
        )
        tokens = np.eye(4, dtype=np.float32).reshape(2, 2, 4)
        self.assertAlmostEqual(patch_covariance_distance(tokens, tokens.copy()), 0.0)
        self.assertAlmostEqual(map_agreement(reference, reference.copy()), 1.0)

    def test_metric_and_map_schema_round_trip(self) -> None:
        metadata = self._metric_metadata()
        metric = build_semantic_metric_record(
            metadata,
            evidence_family="local_semantic_preservation",
            metric_name="local_patch_cosine_similarity",
            feature_model_id="dinov2_vits14",
            region_id="content_region",
            summary_statistic="mean",
            damaged_value=0.6,
            restored_value=0.8,
            improvement_value=0.2,
            improvement_direction="restored_minus_damaged",
            value_unit="cosine_similarity",
            preprocessing_id="dinov2_letterbox_224_local_tokens.v1",
            region_policy_version="evaluation_region_policy.v1",
        )
        metric_frame = pd.DataFrame([metric])
        self.assertTrue(
            validate_dataframe(
                metric_frame, SEMANTIC_STRUCTURAL_METRIC_SCHEMA,
                allow_extra_columns=False,
            ).passed
        )
        config = self._small_config()
        self.assertTrue(validate_semantic_metrics(metric_frame, config=config)["passed"])
        numeric = build_semantic_map_asset_record(
            metadata,
            asset_kind="numeric_map_bundle",
            feature_model_id="dinov2_vits14",
            region_id="content_region",
            map_type="local_semantic_bundle",
            relative_path="outputs/20_semantic_and_structural_consistency/data/semantic_maps.npz",
            archive_key="candidate_a__dinov2_vits14__content_region",
            channel_schema="semantic_bundle_channels.v1",
            format="NPZ",
        )
        rendered = build_semantic_map_asset_record(
            metadata,
            asset_kind="rendered_semantic_panel",
            feature_model_id="multi_encoder",
            region_id="multi_region",
            map_type="semantic_panel",
            relative_path="outputs/20_semantic_and_structural_consistency/images/maps/lama/candidate_a/semantic.png",
            channel_schema="semantic_panel_layout.v1",
            sha256="b" * 64,
            size_bytes=100,
            width=800,
            height=500,
            image_mode="RGBA",
            format="PNG",
            cmap="multi_panel",
            vmin=-1.0,
            vmax=1.0,
            center=0.0,
            scale_scope="global_visualization_contract",
            normalization_policy_id="semantic_visual_scales.v1",
        )
        manifest = pd.DataFrame([numeric, rendered])
        self.assertTrue(
            validate_dataframe(
                manifest, SEMANTIC_MAP_ASSET_SCHEMA, allow_extra_columns=False
            ).passed
        )
        self.assertTrue(
            validate_semantic_map_manifest(manifest, config=config)["passed"]
        )

    def test_metric_validation_handles_declared_null_patterns(self) -> None:
        metadata = self._metric_metadata()
        config = self._small_config()

        worsening = build_semantic_metric_record(
            metadata,
            evidence_family="local_semantic_worsening",
            metric_name="local_patch_worsened_fraction",
            feature_model_id="dinov2_vits14",
            region_id="content_region",
            summary_statistic="fraction",
            damaged_value=np.nan,
            restored_value=0.25,
            improvement_value=np.nan,
            improvement_direction="lower_is_better",
            value_unit="fraction",
            preprocessing_id="dinov2_letterbox_224_local_tokens.v1",
            region_policy_version="evaluation_region_policy.v1",
        )
        worsening_result = validate_semantic_metrics(
            pd.DataFrame([worsening]), config=config
        )
        self.assertTrue(worsening_result["passed"])
        self.assertTrue(worsening_result["numeric_value_patterns_valid"])

        standard = build_semantic_metric_record(
            metadata,
            evidence_family="local_semantic_preservation",
            metric_name="local_patch_cosine_similarity",
            feature_model_id="dinov2_vits14",
            region_id="content_region",
            summary_statistic="mean",
            damaged_value=0.60,
            restored_value=0.80,
            improvement_value=0.20,
            improvement_direction="restored_minus_damaged",
            value_unit="cosine_similarity",
            preprocessing_id="dinov2_letterbox_224_local_tokens.v1",
            region_policy_version="evaluation_region_policy.v1",
        )
        outside_no_data = build_semantic_metric_record(
            metadata,
            evidence_family="outside_context_preservation",
            metric_name="outside_context_feature_change",
            feature_model_id="dinov2_vits14",
            region_id="outside_mask_patch_subset",
            summary_statistic="mean",
            damaged_value=np.nan,
            restored_value=np.nan,
            improvement_value=np.nan,
            improvement_direction="restored_minus_damaged",
            value_unit="cosine_similarity",
            preprocessing_id="dinov2_letterbox_224_local_tokens.v1",
            region_policy_version="evaluation_region_policy.v1",
            issue="not_estimable_no_outside_mask_tokens_at_encoder_grid",
        )
        config["semantic_structural"]["expected_counts"][
            "semantic_metric_rows"
        ] = 2
        outside_result = validate_semantic_metrics(
            pd.DataFrame([standard, outside_no_data]), config=config
        )
        self.assertTrue(outside_result["passed"])
        self.assertEqual(outside_result["outside_context_no_data_rows"], 1)
        self.assertTrue(
            outside_result["outside_context_no_data_issues_recorded"]
        )

        outside_no_data["issue"] = ""
        missing_issue_result = validate_semantic_metrics(
            pd.DataFrame([standard, outside_no_data]), config=config
        )
        self.assertFalse(missing_issue_result["passed"])
        self.assertFalse(
            missing_issue_result["outside_context_no_data_issues_recorded"]
        )

    def test_archive_and_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = np.linspace(-0.2, 1.0, 4 * 4 * 7, dtype=np.float32).reshape(4, 4, 7)
            archive_path = root / "semantic_maps.npz"
            write_semantic_map_archive({"bundle_a": bundle}, archive_path)
            reloaded = load_semantic_map_archive(archive_path)
            np.testing.assert_allclose(reloaded["bundle_a"], bundle, atol=5e-4)
            clean = np.full((32, 40, 3), 100, dtype=np.uint8)
            damaged = clean.copy()
            damaged[10:22, 14:26] = 230
            restored = clean.copy()
            restored[10:22, 14:26] = 110
            panel_path = root / "semantic.png"
            render_semantic_panel(
                clean, damaged, restored, bundle, bundle[:2, :2], panel_path,
                title="Synthetic semantic diagnostic",
                drift_vmax=1.0,
                improvement_absmax=0.5,
            )
            self.assertTrue(panel_path.is_file())
            with Image.open(panel_path) as image:
                self.assertEqual(image.format, "PNG")
                self.assertGreater(image.width, 1000)


if __name__ == "__main__":
    unittest.main()
