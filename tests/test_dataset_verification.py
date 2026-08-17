from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd
from PIL import Image

from restoration_eval.dataset_verification import (
    IMAGE_AUDIT_COLUMNS,
    NEAR_DUPLICATE_COLUMNS,
    ImageAuditResult,
    build_artworks_table,
    build_dataset_audit,
    dataset_content_fingerprint,
    dhash_hex,
    hamming_distance_hex,
    load_dataset_config,
    load_raw_metadata,
    metadata_contract_report,
    validate_dataset_config,
)
from restoration_eval.paths import find_project_root
from restoration_eval.schemas import (
    ARTWORKS_SCHEMA,
    DATASET_AUDIT_SCHEMA,
    RAW_ARTWORK_METADATA_SCHEMA,
    get_schema,
    validate_dataframe,
)


PROJECT_ROOT = find_project_root(Path(__file__))
CONFIG_PATH = PROJECT_ROOT / "config" / "datasets" / "controlled_50.yaml"
METADATA_PATH = PROJECT_ROOT / "data" / "raw" / "metadata" / "metadata_50.csv"


class DatasetVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_dataset_config(CONFIG_PATH)
        cls.metadata = load_raw_metadata(METADATA_PATH)

    def test_controlled_configuration_contract(self) -> None:
        self.assertEqual(validate_dataset_config(self.config), [])
        self.assertEqual(self.config["expected"]["total_paintings"], 50)
        self.assertEqual(self.config["expected"]["audit_row_count"], 101)

    def test_metadata_contract_matches_controlled_scope(self) -> None:
        report = metadata_contract_report(self.metadata, self.config)
        self.assertTrue(report["schema"]["passed"])
        self.assertEqual(report["row_count"], 50)
        self.assertEqual(report["duplicate_painting_id_rows"], 0)
        self.assertEqual(report["duplicate_filename_rows"], 0)
        self.assertEqual(report["duplicate_full_rows"], 0)
        self.assertEqual(report["filename_id_mismatches"], [])
        self.assertEqual(report["invalid_source_urls"], [])
        self.assertEqual(report["invalid_source_license_pairs"], [])
        self.assertEqual(report["invalid_selection_statuses"], [])
        self.assertTrue(report["category_counts_match"])
        self.assertTrue(report["source_counts_match"])
        self.assertTrue(report["source_order_is_deterministic"])

    def test_dhash_is_fixed_width_and_deterministic(self) -> None:
        black = Image.new("RGB", (32, 32), "black")
        white = Image.new("RGB", (32, 32), "white")
        left = dhash_hex(black)
        right = dhash_hex(black.copy())
        flat_white = dhash_hex(white)
        self.assertEqual(len(left), 16)
        self.assertEqual(left, right)
        self.assertEqual(hamming_distance_hex(left, right), 0)
        self.assertEqual(hamming_distance_hex(left, flat_white), 0)

    def test_normalized_tables_validate_and_have_expected_rows(self) -> None:
        image_records = []
        for index, row in enumerate(self.metadata.itertuples(index=False), start=1):
            image_records.append(
                {
                    "painting_id": str(row.painting_id),
                    "raw_filename": str(row.filename),
                    "raw_image_path": f"data/raw/images/{row.filename}",
                    "file_exists": True,
                    "image_verified": True,
                    "image_loaded": True,
                    "raw_width": int(row.original_width),
                    "raw_height": int(row.original_height),
                    "raw_mode": "RGB",
                    "raw_format": "JPEG",
                    "raw_size_bytes": 1000 + index,
                    "raw_sha256": f"{index:064x}",
                    "raw_dhash64": f"{index:016x}",
                    "raw_exif_orientation": 1,
                    "raw_icc_profile_present": False,
                    "raw_icc_profile_description": pd.NA,
                    "width_matches_metadata": True,
                    "height_matches_metadata": True,
                    "minimum_resolution_passed": True,
                    "extension_allowed": True,
                    "format_allowed": True,
                    "mode_allowed": True,
                    "exact_duplicate": False,
                    "near_duplicate_candidate": False,
                    "issue": "",
                }
            )
        image_audit = ImageAuditResult(
            images=pd.DataFrame(image_records, columns=IMAGE_AUDIT_COLUMNS),
            exact_duplicate_groups=(),
            near_duplicate_candidates=pd.DataFrame(columns=NEAR_DUPLICATE_COLUMNS),
            orphan_image_paths=(),
        )
        artworks = build_artworks_table(self.metadata, image_audit, self.config)
        audit = build_dataset_audit(
            self.metadata,
            image_audit,
            artworks,
            self.config,
        )
        self.assertTrue(validate_dataframe(artworks, ARTWORKS_SCHEMA).passed)
        self.assertTrue(validate_dataframe(audit, DATASET_AUDIT_SCHEMA).passed)
        self.assertEqual(len(artworks), 50)
        self.assertEqual(len(audit), self.config["expected"]["audit_row_count"])
        self.assertEqual(set(artworks["acceptance_status"]), {"accepted"})
        first = dataset_content_fingerprint(self.metadata, image_audit, self.config)
        second = dataset_content_fingerprint(self.metadata, image_audit, self.config)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_dataset_schemas_are_registered(self) -> None:
        self.assertIs(get_schema("raw_artwork_metadata"), RAW_ARTWORK_METADATA_SCHEMA)
        self.assertIs(get_schema("artworks"), ARTWORKS_SCHEMA)
        self.assertIs(get_schema("dataset_audit"), DATASET_AUDIT_SCHEMA)


if __name__ == "__main__":
    unittest.main()
