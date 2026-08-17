from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from restoration_eval.manifests import (
    artifact_records_dataframe,
    build_artifact_record,
    build_run_manifest,
    sha256_file,
)
from restoration_eval.paths import (
    PROJECT_PATHS_SCHEMA_VERSION,
    empty_project_paths_registry,
    render_project_paths_markdown,
    require_notebook_output_path,
    upsert_project_path_artifacts,
    validate_notebook_stem,
    validate_project_paths_registry,
)
from restoration_eval.regions import (
    boundary_region,
    build_standard_regions,
    full_image_region,
    mask_bbox_region,
    metric_region_is_valid,
    outside_mask_content_region,
    patch_regions,
)
from restoration_eval.schemas import DataFrameSchema, validate_dataframe
from restoration_eval.validation import ValidationCollector, ValidationFailure


class PathsTests(unittest.TestCase):
    def test_notebook_stem_and_output_guard(self) -> None:
        self.assertEqual(
            validate_notebook_stem("01_dataset_verification"),
            "01_dataset_verification",
        )
        with self.assertRaises(ValueError):
            validate_notebook_stem("1 Dataset Verification")
        allowed = require_notebook_output_path(
            Path.cwd() / "outputs" / "01_dataset_verification" / "data" / "x.csv",
            "01_dataset_verification",
        )
        self.assertTrue(str(allowed).endswith("x.csv"))
        with self.assertRaises(ValueError):
            require_notebook_output_path(
                Path.cwd() / "outputs" / "02_image_preprocessing" / "x.csv",
                "01_dataset_verification",
            )

    def test_empty_registry(self) -> None:
        registry = empty_project_paths_registry()
        self.assertEqual(
            registry["registry_schema_version"],
            PROJECT_PATHS_SCHEMA_VERSION,
        )
        self.assertEqual(validate_project_paths_registry(registry), [])
        self.assertIn(
            "No validated notebook artifacts",
            render_project_paths_markdown(registry),
        )
        updated = upsert_project_path_artifacts(
            registry,
            [
                {
                    "artifact_key": "dataset.artworks",
                    "producer_notebook": "01_dataset_verification",
                    "relative_path": (
                        "outputs/01_dataset_verification/data/artworks.csv"
                    ),
                    "artifact_type": "table",
                    "artifact_role": "primary",
                    "schema_version": "artworks.v1",
                    "dataset_scope": "controlled_50",
                    "experiment_id": "",
                    "validation_status": "passed",
                    "row_count": 50,
                    "file_count": 1,
                    "checksum": "abc",
                }
            ],
        )
        self.assertEqual(len(updated["artifacts"]), 1)
        self.assertEqual(
            validate_project_paths_registry(updated),
            [],
        )


class SchemaTests(unittest.TestCase):
    def test_dataframe_schema(self) -> None:
        schema = DataFrameSchema(
            name="example",
            version="example.v1",
            required_columns=("id", "status"),
            primary_key=("id",),
            non_nullable=("id",),
            allowed_values={"status": frozenset({"ok", "failed"})},
        )
        valid = validate_dataframe(
            pd.DataFrame([{"id": "a", "status": "ok"}]),
            schema,
        )
        self.assertTrue(valid.passed)

        invalid = validate_dataframe(
            pd.DataFrame(
                [
                    {"id": "a", "status": "ok"},
                    {"id": "a", "status": "unknown"},
                ]
            ),
            schema,
        )
        self.assertFalse(invalid.passed)
        self.assertEqual(invalid.duplicate_primary_key_rows, 2)
        self.assertEqual(invalid.invalid_value_counts["status"], 1)


class ValidationTests(unittest.TestCase):
    def test_collector_and_blocking_failure(self) -> None:
        collector = ValidationCollector()
        collector.add(
            validation_stage="preflight",
            check_id="inventory_present",
            check_description="Inventory exists",
            severity="blocking",
            expected=True,
            observed=True,
            passed=True,
        )
        self.assertTrue(collector.overall_passed)
        self.assertEqual(len(collector.to_dataframe()), 1)

        failed = ValidationCollector()
        failed.add(
            validation_stage="preflight",
            check_id="input_present",
            check_description="Required input exists",
            severity="blocking",
            expected=True,
            observed=False,
            passed=False,
        )
        with self.assertRaises(ValidationFailure):
            failed.raise_for_blocking()


class RegionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mask = np.zeros((10, 12), dtype=bool)
        self.mask[3:6, 4:8] = True

    def test_standard_regions_and_exclusive_bbox(self) -> None:
        regions = build_standard_regions(
            self.mask,
            content_bbox=(1, 1, 11, 9),
            mask_bbox_margin=1,
            boundary_width_pixels=1,
            include_outside_boundary=True,
        )
        self.assertEqual(regions["full_image"].pixel_count, 120)
        self.assertEqual(regions["masked_region"].pixel_count, 12)
        self.assertEqual(regions["mask_bbox_crop"].bbox, (3, 2, 9, 7))
        self.assertEqual(
            regions["outside_mask_content"].pixel_count,
            (10 * 8) - 12,
        )
        self.assertTrue(
            np.all(
                ~(
                    regions["inner_boundary_band"].mask
                    & regions["outer_boundary_band"].mask
                )
            )
        )

    def test_sparse_ssim_is_rejected(self) -> None:
        sparse = boundary_region(self.mask, width_pixels=1, mode="both")
        valid, _ = metric_region_is_valid("damaged_ssim", sparse)
        self.assertFalse(valid)
        valid, _ = metric_region_is_valid("clip_cosine_similarity", sparse)
        self.assertFalse(valid)
        full = full_image_region(self.mask.shape)
        valid, _ = metric_region_is_valid("ssim", full)
        self.assertTrue(valid)

    def test_patch_order(self) -> None:
        regions = patch_regions(
            (8, 8),
            patch_size=4,
            stride=4,
        )
        self.assertEqual(
            [region.region_id for region in regions],
            [
                "patch_y0000_x0000",
                "patch_y0000_x0004",
                "patch_y0004_x0000",
                "patch_y0004_x0004",
            ],
        )


class ManifestTests(unittest.TestCase):
    def test_artifact_and_run_manifests(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            artifact_path = Path(directory) / "artifact.csv"
            artifact_path.write_text("id,value\na,1\n", encoding="utf-8")
            record = build_artifact_record(
                artifact_key="example",
                producer_notebook="01_dataset_verification",
                path=artifact_path,
                artifact_type="table",
                artifact_role="primary",
                schema_version="example.v1",
                dataset_scope="controlled_50",
                row_count=1,
            )
            self.assertEqual(record["checksum"], sha256_file(artifact_path))
            self.assertEqual(len(artifact_records_dataframe([record])), 1)

        manifest = build_run_manifest(
            notebook_id="01",
            notebook_name="01_dataset_verification",
            origin="Existing Notebook 01",
            run_status="completed",
            started_at_utc="2026-01-01T00:00:00Z",
            completed_at_utc="2026-01-01T00:01:00Z",
            inventory_run_id="inventory_test",
            dataset_versions={"controlled_50": "test"},
            configuration_paths=[],
            configuration_checksums_by_path={},
            helper_versions={"paths": "1.0.0"},
            inputs=[],
            outputs=[],
            expected_counts={"paintings": 50},
            observed_counts={"paintings": 50},
            validation_summary={"overall_passed": True},
            known_limitations=[],
        )
        self.assertIn("git_commit", manifest)
        self.assertEqual(manifest["notebook_id"], "01")


if __name__ == "__main__":
    unittest.main()
