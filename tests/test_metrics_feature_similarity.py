from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.evaluation_inputs import build_evaluation_worklist
from restoration_eval.metrics_feature_similarity import (
    FEATURE_ACTIVE_REGIONS,
    build_feature_embedding_plan,
    build_feature_execution_plan,
    construct_feature_metrics,
    extract_feature_model_embeddings,
    feature_model_specs,
    load_feature_embedding_bundle,
    load_feature_similarity_config,
    load_latest_embedding_checkpoint,
    populate_missing_source_checksums,
    save_feature_embedding_bundle,
    validate_feature_embedding_manifest,
    validate_feature_metrics,
    write_embedding_checkpoint_manifest,
)
from restoration_eval.schemas import (
    FEATURE_EMBEDDING_MANIFEST_SCHEMA,
    FEATURE_METRICS_SCHEMA,
    get_schema,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/evaluation/feature_similarity.yaml"


class FeatureSimilarityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_feature_similarity_config(CONFIG_PATH)

    def _small_worklist(self, root: Path) -> pd.DataFrame:
        clean = np.zeros((32, 48, 3), dtype=np.uint8)
        clean[:, :, 0] = np.arange(48, dtype=np.uint8)[None, :] * 4
        damaged = clean.copy()
        damaged[10:22, 15:31] = 255
        mask = np.zeros((32, 48), dtype=np.uint8)
        mask[10:22, 15:31] = 255
        zero_mask = np.zeros_like(mask)
        arrays = {
            "clean.png": clean,
            "damaged.png": damaged,
            "mask.png": mask,
            "zero_mask.png": zero_mask,
            "restored_zero.png": clean,
            "restored_1.png": clean,
            "restored_2.png": clean,
        }
        for name, array in arrays.items():
            Image.fromarray(array).save(root / name)
        records = []
        for candidate_id, case_id, restored, zero in (
            ("candidate_zero", "case_zero", "restored_zero.png", True),
            ("candidate_1", "case_damage", "restored_1.png", False),
            ("candidate_2", "case_damage", "restored_2.png", False),
        ):
            records.append({
                "candidate_id": candidate_id, "case_id": case_id,
                "model_id": "test_model", "painting_id": "p001",
                "mask_threshold": 128,
                "mask_or_effect_path": "zero_mask.png" if zero else "mask.png",
                "content_x_min": 0, "content_y_min": 0,
                "content_x_max": 48, "content_y_max": 32,
                "clean_image_path": "clean.png",
                "input_image_path": "clean.png" if zero else "damaged.png",
                "restored_path": restored, "restored_sha256": "",
                "is_zero_control": zero,
            })
        return pd.DataFrame(records)

    @staticmethod
    def _fake_encoder(dimension: int):
        def encode(images):
            rows = []
            for image in images:
                values = np.asarray(image, dtype=np.float32)
                vector = np.zeros(dimension, dtype=np.float32)
                vector[0] = float(values.mean()) + 1.0
                vector[1] = float(values.std()) + 1.0
                rows.append(vector)
            return np.stack(rows)
        return encode

    def test_schemas_registered_and_region_scope_exact(self) -> None:
        self.assertIs(get_schema("feature_metrics"), FEATURE_METRICS_SCHEMA)
        self.assertIs(
            get_schema("feature_embedding_manifest"),
            FEATURE_EMBEDDING_MANIFEST_SCHEMA,
        )
        self.assertEqual(FEATURE_ACTIVE_REGIONS, ("content_region", "mask_bbox_crop"))

    def test_deduplicated_plans_and_fake_end_to_end_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worklist = self._small_worklist(root)
            execution = build_feature_execution_plan(
                worklist, project_root=root, config=self.config
            )
            self.assertEqual(len(execution), 5)
            self.assertEqual(execution["region_id"].value_counts().to_dict(), {
                "content_region": 3, "mask_bbox_crop": 2,
            })
            plan = build_feature_embedding_plan(execution, config=self.config)
            self.assertEqual(len(plan), 20)
            self.assertEqual(
                plan.groupby(["feature_model_id", "image_role"]).size().to_dict(),
                {
                    ("clip_vit_b32", "clean"): 2,
                    ("clip_vit_b32", "damaged"): 3,
                    ("clip_vit_b32", "restored"): 5,
                    ("dinov2_vits14", "clean"): 2,
                    ("dinov2_vits14", "damaged"): 3,
                    ("dinov2_vits14", "restored"): 5,
                },
            )
            plan = populate_missing_source_checksums(plan, project_root=root)
            manifests = []
            arrays = {}
            for spec in feature_model_specs(self.config).values():
                result = extract_feature_model_embeddings(
                    plan, spec=spec, encode_batch=self._fake_encoder(
                        spec.embedding_dimension
                    ), project_root=root, config=self.config,
                )
                manifests.append(result.manifest)
                arrays[spec.array_name] = np.asarray(result.matrix)
            manifest = pd.concat(manifests, ignore_index=True)
            embedding_validation = validate_feature_embedding_manifest(
                manifest, arrays, config=self.config, expected_plan=plan
            )
            self.assertTrue(embedding_validation["passed"], embedding_validation)
            metrics = construct_feature_metrics(
                execution, manifest, arrays, config=self.config,
                device="cpu", package_versions={"transformers": "test", "torch": "test"},
            )
            metric_validation = validate_feature_metrics(
                metrics, execution, manifest, config=self.config
            )
            self.assertTrue(metric_validation["passed"], metric_validation)
            self.assertEqual(len(metrics), 10)
            damaged = metrics.loc[metrics["case_id"].eq("case_damage")]
            self.assertTrue((damaged["improvement_value"] > 0).all())

    def test_embedding_bundle_and_checkpoint_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            arrays = {
                "clip_embeddings": np.ones((2, 512), dtype=np.float32),
                "dinov2_embeddings": np.ones((2, 384), dtype=np.float32),
            }
            path = save_feature_embedding_bundle(arrays, root / "embeddings.npz")
            loaded = load_feature_embedding_bundle(path)
            self.assertEqual(set(loaded), set(arrays))
            self.assertEqual(loaded["clip_embeddings"].dtype, np.float32)

            checkpoint = pd.DataFrame(columns=FEATURE_EMBEDDING_MANIFEST_SCHEMA.required_columns)
            result = write_embedding_checkpoint_manifest(
                checkpoint, root / "work" / "embedding_checkpoint.csv"
            )
            self.assertEqual(result["status"], "canonical")
            reloaded, source = load_latest_embedding_checkpoint(result["path"])
            self.assertEqual(source, result["path"])
            self.assertEqual(tuple(reloaded.columns),
                             FEATURE_EMBEDDING_MANIFEST_SCHEMA.required_columns)

    def test_real_contract_has_exact_candidate_region_and_embedding_counts(self) -> None:
        settings = self.config["feature_similarity"]
        inputs = settings["inputs"]
        cases = pd.read_csv(ROOT / inputs["case_registry_path"])
        eligibility = pd.read_csv(ROOT / inputs["model_eligibility_path"])
        geometry = pd.read_csv(ROOT / inputs["geometry_path"])
        tables = {
            item["source_table_id"]: pd.read_csv(ROOT / item["path"])
            for item in inputs["upstream_sources"]
        }
        worklist = build_evaluation_worklist(
            cases, eligibility, geometry, tables
        ).worklist
        execution = build_feature_execution_plan(
            worklist, project_root=ROOT, config=self.config
        )
        embedding_plan = build_feature_embedding_plan(
            execution, config=self.config
        )
        expected = settings["expected_counts"]
        self.assertEqual(len(worklist), expected["evaluated_candidates"])
        self.assertEqual(len(execution), expected["candidate_region_evaluations"])
        self.assertEqual(execution["region_id"].value_counts().to_dict(), {
            "content_region": expected["content_region_evaluations"],
            "mask_bbox_crop": expected["mask_bbox_region_evaluations"],
        })
        self.assertEqual(len(embedding_plan), expected["total_embedding_rows"])
        self.assertEqual(
            embedding_plan.groupby("image_role").size().to_dict(),
            expected["embeddings_by_role_across_models"],
        )
        self.assertEqual(
            embedding_plan.groupby("feature_model_id").size().to_dict(),
            {model_id: expected["embeddings_per_feature_model"]
             for model_id in ("clip_vit_b32", "dinov2_vits14")},
        )


if __name__ == "__main__":
    unittest.main()
