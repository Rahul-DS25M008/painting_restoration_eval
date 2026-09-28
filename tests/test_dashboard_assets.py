"""Focused preparation-layer tests for the Controlled-300 Notebook 34 package."""

from __future__ import annotations

import copy
import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from restoration_eval.dashboard_assets import (  # noqa: E402
    DASHBOARD_ASSETS_CONFIG_SCHEMA,
    DASHBOARD_PACKAGE_SCHEMA,
    DASHBOARD_RUNTIME_MANIFEST_SCHEMA,
    OUTPUT_SCHEMAS,
    PRINCIPAL_ROOM_IDS,
    atomic_write_json_gzip,
    blocking_validation_failures,
    empty_output_frame,
    is_full_git_revision,
    is_repo_relative,
    load_dashboard_config,
    load_upstream_manifests,
    manifest_specs,
    stable_id,
    validate_input_table_contracts,
    validate_declared_input_paths,
    validate_output_frame,
    validation_row,
)


class DashboardAssetsPreparationTests(unittest.TestCase):
    """Guard the v2 contract before any N34 package output is written."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.config_path = ROOT / "config/evaluation/dashboard_assets.yaml"
        cls.config = load_dashboard_config(cls.config_path)
        cls.settings = cls.config["dashboard_assets"]

    def test_real_v2_config_is_strict_and_closed(self) -> None:
        self.assertEqual(self.config["config_schema_version"], DASHBOARD_ASSETS_CONFIG_SCHEMA)
        self.assertEqual(
            self.settings["dashboard_package_schema_version"],
            DASHBOARD_PACKAGE_SCHEMA,
        )
        self.assertEqual(
            self.settings["runtime_manifest_schema_version"],
            DASHBOARD_RUNTIME_MANIFEST_SCHEMA,
        )
        self.assertFalse(self.settings["creates_new_scientific_evidence"])
        principal = [
            row["room_id"]
            for row in self.settings["rooms"]
            if row["route_kind"] == "principal"
        ]
        self.assertEqual(principal, list(PRINCIPAL_ROOM_IDS))
        child = [row for row in self.settings["rooms"] if row["route_kind"] == "child"]
        self.assertEqual(len(child), 1)
        self.assertEqual(child[0]["room_id"], "focused_portrait_review")
        self.assertEqual(child[0]["parent_room_id"], "trustworthiness")
        self.assertEqual(len(self.settings["upstream_manifests"]), 33)
        self.assertEqual(list(self.settings["supplemental_manifests"]), ["12A", "D01", "D02"])
        self.assertEqual(len(manifest_specs(self.config)), 36)
        self.assertEqual(self.settings["population"]["painting_count"], 300)
        self.assertEqual(self.settings["population"]["registered_case_count"], 3425)
        self.assertEqual(self.settings["population"]["indexed_inspectable_candidate_count"], 13879)

    def test_config_mutations_fail_closed(self) -> None:
        mutations = []

        wrong_scope = copy.deepcopy(self.config)
        wrong_scope["dashboard_assets"]["dataset_scope"] = "controlled_50"
        mutations.append(wrong_scope)

        wrong_room = copy.deepcopy(self.config)
        wrong_room["dashboard_assets"]["rooms"][0], wrong_room["dashboard_assets"]["rooms"][1] = (
            wrong_room["dashboard_assets"]["rooms"][1],
            wrong_room["dashboard_assets"]["rooms"][0],
        )
        mutations.append(wrong_room)

        wrong_parent = copy.deepcopy(self.config)
        wrong_parent["dashboard_assets"]["rooms"][6]["parent_room_id"] = "case_explorer"
        mutations.append(wrong_parent)

        missing_manifest = copy.deepcopy(self.config)
        missing_manifest["dashboard_assets"]["supplemental_manifests"].pop("D02")
        mutations.append(missing_manifest)

        unsafe_output = copy.deepcopy(self.config)
        unsafe_output["dashboard_assets"]["output"]["work_dir"] = "../outside"
        mutations.append(unsafe_output)

        unsafe_non_table_input = copy.deepcopy(self.config)
        unsafe_non_table_input["dashboard_assets"]["inputs"][
            "final_report_path"
        ] = "../outside.html"
        mutations.append(unsafe_non_table_input)

        with tempfile.TemporaryDirectory() as directory:
            for index, mutated in enumerate(mutations):
                path = Path(directory) / f"mutated_{index}.yaml"
                import yaml

                path.write_text(yaml.safe_dump(mutated, sort_keys=False), encoding="utf-8")
                with self.subTest(index=index), self.assertRaises(ValueError):
                    load_dashboard_config(path)

    def test_streaming_csv_contract_honours_embedded_newline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            table = root / "table.csv"
            table.write_text(
                'record_id,note,status\n1,"line one\nline two",passed\n2,plain,passed\n',
                encoding="utf-8",
            )
            config = {
                "dashboard_assets": {
                    "inputs": {"table_path": "table.csv"},
                    "input_table_contracts": {
                        "table_path": {
                            "rows": 2,
                            "required_columns": ["record_id", "note", "status"],
                        }
                    },
                }
            }
            summary, checks = validate_input_table_contracts(root, config, load_frames=False)
            self.assertEqual(int(summary.loc[0, "observed_rows"]), 2)
            self.assertEqual(summary.loc[0, "status"], "passed")
            self.assertTrue(blocking_validation_failures(checks).empty)
            with self.assertRaises(ValueError):
                validate_input_table_contracts(root, config, load_frames=True)

    def test_all_manifest_pins_match_completed_local_runs(self) -> None:
        manifests, checks = load_upstream_manifests(ROOT, self.config)
        self.assertEqual(len(manifests), 36)
        self.assertTrue(blocking_validation_failures(checks).empty)
        self.assertEqual(manifests["12A"]["notebook_id"], "12A")
        self.assertEqual(manifests["D01"]["notebook_id"], "37")
        self.assertEqual(manifests["D02"]["notebook_id"], "D02")

    def test_all_declared_inputs_exist_locally(self) -> None:
        checks = validate_declared_input_paths(ROOT, self.config)
        self.assertEqual(len(checks), len(self.settings["inputs"]))
        self.assertTrue(blocking_validation_failures(checks).empty)

    def test_canonical_stable_ids_are_collision_safe(self) -> None:
        first = stable_id("test", {"b": 2, "a": 1})
        second = stable_id("test", {"a": 1, "b": 2})
        self.assertEqual(first, second)
        self.assertNotEqual(stable_id("test", "a|b", "c"), stable_id("test", "a", "b|c"))
        self.assertNotEqual(stable_id("test", 1), stable_id("test", "1"))
        self.assertRegex(first, r"^test_[0-9a-f]{24}$")

    def test_safe_path_and_revision_guards(self) -> None:
        self.assertTrue(is_repo_relative("outputs/01/data.csv"))
        for invalid in ("", ".", "../escape", "C:/absolute", "https://example.test/x", "a\\b"):
            with self.subTest(invalid=invalid):
                self.assertFalse(is_repo_relative(invalid))
        self.assertTrue(is_full_git_revision("a" * 40))
        self.assertFalse(is_full_git_revision("a" * 39))
        self.assertFalse(is_full_git_revision("main"))

    def test_deterministic_gzip_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.json.gz"
            second_path = Path(directory) / "second.json.gz"
            first_meta = atomic_write_json_gzip({"b": 2, "a": [1, None]}, first_path)
            second_meta = atomic_write_json_gzip({"a": [1, None], "b": 2}, second_path)
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
            self.assertEqual(first_meta, second_meta)
            decoded = gzip.decompress(first_path.read_bytes())
            self.assertEqual(hashlib.sha256(decoded).hexdigest(), first_meta["decoded_sha256"])
            self.assertEqual(int.from_bytes(first_path.read_bytes()[4:8], "little"), 0)

    def test_output_schema_validation_reorders_and_rejects_drift(self) -> None:
        for schema_key, columns in OUTPUT_SCHEMAS.items():
            with self.subTest(schema=schema_key):
                frame = pd.DataFrame(columns=list(reversed(columns)))
                normalized = validate_output_frame(frame, schema_key)
                self.assertEqual(normalized.columns.tolist(), list(columns))
                missing = empty_output_frame(schema_key).drop(columns=[columns[-1]])
                with self.assertRaises(ValueError):
                    validate_output_frame(missing, schema_key)

    def test_blocking_checks_are_type_safe(self) -> None:
        checks = pd.DataFrame(
            [
                validation_row("test", "passes", True, True, True),
                validation_row("test", "warning", False, True, False, "warning", "warning"),
                validation_row("test", "blocks", False, True, False, "blocked"),
            ]
        )
        failures = blocking_validation_failures(checks)
        self.assertEqual(failures["check_description"].tolist(), ["blocks"])


if __name__ == "__main__":
    unittest.main()
