from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.damage_size_diffusion_uncertainty import (
    DIFFUSION_UNCERTAINTY_COLUMNS,
    MAP_IMAGE_COLUMNS,
    METRIC_VERSION,
    MODULE_VERSION,
    build_anchor_reference_rows,
    build_complete_uncertainty_worklist,
    build_effective_generation_config,
    build_extension_candidate_plan,
    build_extension_restored_embedding_plan,
    build_uncertainty_adapter_config,
    combine_anchor_and_extension_embeddings,
    compute_rgb_std_maps,
    load_damage_size_uncertainty_config,
    select_frozen_damage_size_anchors,
    validate_extension_candidate_plan,
    write_uncertainty_map_bundle,
)
from restoration_eval.diffusion_uncertainty import build_uncertainty_population
from restoration_eval.metrics_feature_similarity import load_feature_similarity_config
from restoration_eval.restoration_stable_diffusion import load_stable_diffusion_config


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/evaluation/damage_size_diffusion_uncertainty_extension.yaml"
BASE_CONFIG_PATH = ROOT / "config/experiments/stable_diffusion.yaml"


class DamageSizeDiffusionUncertaintyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_damage_size_uncertainty_config(CONFIG_PATH)
        cls.base_config = load_stable_diffusion_config(BASE_CONFIG_PATH)
        cls.cases = pd.read_csv(
            ROOT / "outputs/05_damage_size_sensitivity_dataset_generation/data/cases.csv"
        )
        cls.candidates = pd.read_csv(
            ROOT / "outputs/11_stable_diffusion_restoration/data/candidates.csv"
        )
        cls.geometry = pd.read_csv(
            ROOT / "outputs/02_image_preprocessing/data/preprocessed_images.csv"
        )
        cls.artworks = pd.read_csv(
            ROOT / "outputs/01_dataset_verification/data/artworks.csv"
        )
        cls.anchors = select_frozen_damage_size_anchors(
            cls.cases, cls.candidates, config=cls.config,
        )

    def test_contract_and_effective_generation_settings_are_frozen(self) -> None:
        self.assertEqual(MODULE_VERSION, "1.0.0")
        self.assertEqual(METRIC_VERSION, "damage_size_empirical_seed_uncertainty.v1")
        self.assertEqual(len(MAP_IMAGE_COLUMNS), 18)
        effective = build_effective_generation_config(self.base_config, self.config)
        settings = self.config["damage_size_diffusion_uncertainty_extension"]
        generation = settings["generation_contract"]
        population = settings["population"]
        for key in (
            "hf_model_id", "model_revision", "scheduler", "num_inference_steps",
            "guidance_scale", "strength", "precision", "requested_device",
            "inference_width", "inference_height", "output_width", "output_height",
            "compositing_policy", "safety_checker_policy",
        ):
            self.assertEqual(effective["model"][key], generation[key])
        self.assertEqual(effective["prompt_policy"]["policy_id"], "sd15_prompt_policy.v3")
        self.assertEqual(effective["prompt_policy"]["primary_variant_id"], "p00_generic")
        self.assertEqual(effective["prompt_policy"]["generic_prompt"], generation["prompt"])
        self.assertEqual(population["generated_seeds"], [2027, 2028, 2029])
        self.assertFalse(settings["frozen_boundary"]["may_write_frozen_outputs"])
        self.assertFalse(settings["frozen_boundary"]["copy_anchor_images"])

    def test_real_frozen_anchors_and_extension_plan_have_exact_population(self) -> None:
        self.assertEqual(len(self.anchors), 35)
        self.assertEqual(self.anchors["case_id"].nunique(), 35)
        self.assertEqual(self.anchors["painting_id"].nunique(), 5)
        self.assertEqual(set(self.anchors["seed"].astype(int)), {2026})
        self.assertTrue(self.anchors["status"].eq("completed").all())
        plan = build_extension_candidate_plan(self.anchors, config=self.config)
        validation = validate_extension_candidate_plan(
            plan, config=self.config, require_completed=False,
        )
        self.assertTrue(validation["passed"], validation)
        self.assertEqual(len(plan), 105)
        self.assertEqual(plan["case_id"].nunique(), 35)
        self.assertEqual(set(plan["seed"].astype(int)), {2027, 2028, 2029})
        self.assertEqual(plan.groupby("case_id")["seed"].nunique().unique().tolist(), [3])
        self.assertTrue(plan["candidate_id"].str.startswith("sd15dsu__").all())
        self.assertTrue(plan["restored_path"].str.startswith("images/restored/").all())
        self.assertFalse(plan["restored_path"].str.contains("outputs/11_").any())

    def test_combined_worklist_builds_35_complete_four_seed_groups(self) -> None:
        extension = build_extension_candidate_plan(self.anchors, config=self.config)
        extension["status"] = "completed"
        extension["execution_action"] = "stable_diffusion_inpaint"
        extension["restored_sha256"] = "a" * 64
        extension["runtime_seconds"] = 1.0
        extension["gpu_memory_before_bytes"] = 0
        extension["gpu_memory_after_bytes"] = 0
        extension["gpu_peak_memory_bytes"] = 0
        extension["attempt_count"] = 1
        extension["started_at_utc"] = "2026-01-01T00:00:00Z"
        extension["completed_at_utc"] = "2026-01-01T00:00:01Z"
        worklist = build_complete_uncertainty_worklist(
            self.anchors, extension, self.cases, self.geometry, config=self.config,
        )
        self.assertEqual(len(worklist), 140)
        self.assertEqual(worklist.groupby("source_owner").size().to_dict(), {
            "extension_owned": 105, "frozen_reference": 35,
        })
        self.assertTrue(
            worklist.loc[worklist["source_owner"].eq("frozen_reference"), "restored_path"]
            .str.startswith("outputs/11_stable_diffusion_restoration/").all()
        )
        self.assertTrue(
            worklist.loc[worklist["source_owner"].eq("extension_owned"), "restored_path"]
            .str.startswith("outputs/22_damage_size_diffusion_uncertainty_extension/").all()
        )
        adapter = build_uncertainty_adapter_config(self.config)
        population = build_uncertainty_population(worklist, self.artworks, config=adapter)
        self.assertEqual(len(population), 140)
        self.assertEqual(population["uncertainty_group_id"].nunique(), 35)
        self.assertTrue(population.groupby("uncertainty_group_id")["seed"].nunique().eq(4).all())

        feature_config = load_feature_similarity_config(
            ROOT / "config/evaluation/feature_similarity.yaml"
        )
        embedding_plan = build_extension_restored_embedding_plan(
            worklist, project_root=ROOT, feature_config=feature_config,
        )
        self.assertEqual(len(embedding_plan), 420)
        self.assertEqual(embedding_plan.groupby("feature_model_id").size().to_dict(), {
            "clip_vit_b32": 210, "dinov2_vits14": 210,
        })
        self.assertTrue(embedding_plan["image_role"].eq("restored").all())
        self.assertTrue(
            embedding_plan["representative_candidate_id"].isin(
                extension["candidate_id"]
            ).all()
        )
        extension_manifests = []
        extension_arrays = {}
        dimensions = {"clip_vit_b32": 512, "dinov2_vits14": 384}
        for model_id, model_plan in embedding_plan.groupby("feature_model_id", sort=True):
            manifest = model_plan.copy()
            manifest["status"] = "ok"
            manifest["issue"] = ""
            array_name = str(manifest["array_name"].iloc[0])
            matrix = np.ones((len(manifest), dimensions[str(model_id)]), dtype=np.float32)
            matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
            extension_manifests.append(manifest)
            extension_arrays[array_name] = matrix
        frozen_manifest = pd.read_csv(
            ROOT / "outputs/15_feature_similarity/manifests/embeddings.csv",
            low_memory=False,
        )
        with np.load(ROOT / "outputs/15_feature_similarity/data/embeddings.npz") as bundle:
            frozen_arrays = {key: bundle[key] for key in bundle.files}
        combined_manifest, combined_arrays = combine_anchor_and_extension_embeddings(
            population,
            frozen_manifest,
            frozen_arrays,
            extension_manifests,
            extension_arrays,
            config=self.config,
        )
        self.assertEqual(len(combined_manifest), 560)
        self.assertEqual(
            set(combined_arrays),
            {
                "clip_embeddings", "dinov2_embeddings",
                "clip_extension_embeddings", "dinov2_extension_embeddings",
            },
        )

    def test_real_anchor_reference_evidence_resolves_exactly(self) -> None:
        extension = build_extension_candidate_plan(self.anchors, config=self.config)
        extension["status"] = "completed"
        extension["execution_action"] = "stable_diffusion_inpaint"
        extension["restored_sha256"] = "b" * 64
        extension["runtime_seconds"] = 1.0
        extension["gpu_memory_before_bytes"] = 0
        extension["gpu_memory_after_bytes"] = 0
        extension["gpu_peak_memory_bytes"] = 0
        extension["attempt_count"] = 1
        extension["started_at_utc"] = "2026-01-01T00:00:00Z"
        extension["completed_at_utc"] = "2026-01-01T00:00:01Z"
        worklist = build_complete_uncertainty_worklist(
            self.anchors, extension, self.cases, self.geometry, config=self.config,
        )
        population = build_uncertainty_population(
            worklist, self.artworks, config=build_uncertainty_adapter_config(self.config),
        )
        sources = {
            "classical": pd.read_csv(ROOT / "outputs/13_classical_metrics/metrics/classical_metrics.csv"),
            "lpips": pd.read_csv(ROOT / "outputs/14_lpips_metrics/metrics/lpips_metrics.csv"),
            "feature": pd.read_csv(ROOT / "outputs/15_feature_similarity/metrics/feature_metrics.csv"),
            "spatial": pd.read_csv(ROOT / "outputs/16_difference_maps_and_spatial_diagnostics/metrics/spatial_diagnostics.csv"),
            "local_consistency": pd.read_csv(
                ROOT / "outputs/17_local_consistency_metrics/metrics/local_consistency.csv",
                low_memory=False,
            ),
            "semantic": pd.read_csv(
                ROOT / "outputs/20_semantic_and_structural_consistency/metrics/semantic_structural_metrics.csv",
                low_memory=False,
            ),
        }
        references = build_anchor_reference_rows(population, sources, config=self.config)
        self.assertEqual(list(references.columns), list(DIFFUSION_UNCERTAINTY_COLUMNS))
        self.assertEqual(len(references), 560)
        self.assertEqual(references["uncertainty_group_id"].nunique(), 35)
        self.assertEqual(references.groupby("uncertainty_group_id").size().unique().tolist(), [16])
        self.assertTrue(references["evidence_role"].eq("frozen_anchor_reference").all())
        self.assertTrue(np.isfinite(pd.to_numeric(references["value"])).all())

    def test_rgb_map_bundle_is_one_float32_map_per_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            records = []
            for seed, value in zip((2026, 2027, 2028, 2029), (20, 40, 60, 80)):
                path = root / f"seed_{seed}.png"
                Image.fromarray(np.full((12, 16, 3), value, dtype=np.uint8)).save(path)
                records.append({
                    "uncertainty_group_id": "ug_test",
                    "seed": seed,
                    "restored_path": path.name,
                })
            maps = compute_rgb_std_maps(
                pd.DataFrame(records), project_root=root, progress_callback=None,
            )
            self.assertEqual(set(maps), {"ug_test"})
            self.assertEqual(maps["ug_test"].shape, (12, 16))
            self.assertEqual(maps["ug_test"].dtype, np.float32)

            config = {
                "damage_size_diffusion_uncertainty_extension": {
                    **self.config["damage_size_diffusion_uncertainty_extension"],
                    "expected_counts": {
                        **self.config["damage_size_diffusion_uncertainty_extension"]["expected_counts"],
                        "raw_uncertainty_maps": 1,
                    },
                }
            }
            destination = root / "maps.npz"
            write_uncertainty_map_bundle(maps, destination, config=config)
            self.assertTrue(destination.is_file())
            with np.load(destination) as bundle:
                self.assertEqual(bundle.files, ["ug_test"])
                np.testing.assert_allclose(bundle["ug_test"], maps["ug_test"])


if __name__ == "__main__":
    unittest.main()
