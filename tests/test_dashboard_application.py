"""Focused tests for the Controlled-300 dashboard runtime contract."""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from restoration_eval.dashboard_application import (  # noqa: E402
    DASHBOARD_APPLICATION_VERSION,
    DASHBOARD_PACKAGE_SCHEMA_VERSION,
    DASHBOARD_VALIDATION_CONFIG_SCHEMA_VERSION,
    PRINCIPAL_ROOM_IDS,
    DashboardContractError,
    load_dashboard_validation_config,
    open_dashboard_package,
    required_input_paths,
    safe_project_path,
    validate_input_path_templates,
)


PACKAGE_ROOT = ROOT / "outputs" / "34_final_streamlit_dashboard_assets"
BOOTSTRAP_PATH = PACKAGE_ROOT / "data" / "bootstrap" / "bootstrap.json"
RUNTIME_MANIFEST_PATH = PACKAGE_ROOT / "manifests" / "dashboard_runtime_manifest.json"
RUN_MANIFEST_PATH = PACKAGE_ROOT / "manifests" / "run_manifest.json"


def _value(record, key: str):
    """Read a field from a mapping, pandas row, or dataclass-like record."""

    if isinstance(record, dict):
        return record[key]
    try:
        return record[key]
    except (KeyError, TypeError):
        return getattr(record, key)


class DashboardApplicationV2Tests(unittest.TestCase):
    """Guard the lazy, immutable Controlled-300 application package."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_dashboard_validation_config(ROOT)
        cls.package = open_dashboard_package(ROOT)
        cls.bootstrap = json.loads(BOOTSTRAP_PATH.read_text(encoding="utf-8"))
        cls.runtime_manifest = json.loads(
            RUNTIME_MANIFEST_PATH.read_text(encoding="utf-8")
        )
        cls.run_manifest = json.loads(RUN_MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_versions_and_controlled_300_contract_are_exact(self) -> None:
        self.assertEqual(DASHBOARD_APPLICATION_VERSION, "2.0.0")
        self.assertEqual(
            DASHBOARD_VALIDATION_CONFIG_SCHEMA_VERSION,
            "dashboard_validation_config.v2",
        )
        self.assertEqual(DASHBOARD_PACKAGE_SCHEMA_VERSION, "dashboard_package.v2")
        self.assertEqual(self.config["schema_version"], "dashboard_validation_config.v2")
        self.assertEqual(self.bootstrap["dataset"]["dataset_scope"], "controlled_300")
        self.assertEqual(self.bootstrap["package_schema_version"], "dashboard_package.v2")
        self.assertEqual(
            self.bootstrap["release_id"],
            self.runtime_manifest["release_id"],
        )

        self.assertEqual(self.config["dataset"]["dataset_scope"], "controlled_300")
        self.assertEqual(
            tuple(self.config["application"]["principal_room_order"]),
            tuple(PRINCIPAL_ROOM_IDS),
        )
        self.assertEqual(self.config["application"]["child_route_count"], 1)
        self.assertEqual(self.config["expected_package"]["package_files"], 377)
        self.assertEqual(self.config["expected_package"]["logical_assets"], 56)
        self.assertEqual(self.config["expected_package"]["renditions"], 48)
        self.assertEqual(self.config["expected_package"]["asset_locators"], 95)

    def test_validation_config_resolves_all_concrete_inputs_safely(self) -> None:
        resolved = required_input_paths(self.config, ROOT)
        templates = validate_input_path_templates(self.config, ROOT)
        self.assertEqual(set(resolved), set(self.config["required_inputs"]))
        self.assertEqual(len(resolved), 30)
        self.assertEqual(
            templates,
            {
                "painting_partitions": (
                    "outputs/34_final_streamlit_dashboard_assets/"
                    "data/paintings/{painting_id}.json.gz"
                )
            },
        )
        for key, path in resolved.items():
            with self.subTest(input_key=key):
                self.assertTrue(path.exists())
                self.assertTrue(path.resolve().is_relative_to(ROOT.resolve()))
        self.assertEqual(
            resolved["painting_partitions"].resolve(),
            (PACKAGE_ROOT / "data" / "paintings").resolve(),
        )

    def test_exact_rooms_child_route_and_population(self) -> None:
        expected_rooms = (
            "exhibition_foyer",
            "study_design",
            "metric_framework",
            "model_gallery",
            "stability_lab",
            "trustworthiness",
            "case_explorer",
            "research_archive",
        )
        self.assertEqual(tuple(PRINCIPAL_ROOM_IDS), expected_rooms)
        self.assertEqual(tuple(self.bootstrap["principal_room_ids"]), expected_rooms)
        self.assertEqual(
            self.bootstrap["child_routes"],
            [
                {
                    "parent_room_id": "trustworthiness",
                    "room_id": "focused_portrait_review",
                }
            ],
        )

        population = self.runtime_manifest["population"]
        self.assertEqual(population["painting_count"], 300)
        self.assertEqual(population["registered_case_count"], 3425)
        self.assertEqual(population["indexed_inspectable_candidate_count"], 13879)
        self.assertEqual(population["four_model_eligible_case_count"], 2620)
        self.assertEqual(population["four_model_primary_candidate_count"], 10480)
        self.assertEqual(population["repeated_seed_group_count"], 1025)

        self.assertEqual(
            self.run_manifest["observed_counts"],
            {
                "asset_locators": 95,
                "child_routes": 1,
                "display_bindings": 170,
                "display_ids": 100,
                "logical_assets": 56,
                "package_files": 377,
                "paintings": 300,
                "principal_rooms": 8,
                "renditions": 48,
            },
        )

    def test_open_and_lazy_local_reads_make_no_network_request(self) -> None:
        network_error = AssertionError("dashboard package startup attempted network I/O")
        with (
            mock.patch("urllib.request.urlopen", side_effect=network_error),
            mock.patch("urllib.request.urlretrieve", side_effect=network_error),
            mock.patch("socket.create_connection", side_effect=network_error),
        ):
            package = open_dashboard_package(ROOT)
            foyer = package.load_room("exhibition_foyer")
            painting = package.load_painting("p001")
            bindings = package.bindings_for(room_id="exhibition_foyer")

        self.assertGreater(len(foyer), 0)
        self.assertEqual(painting["painting_id"], "p001")
        self.assertGreater(len(bindings), 0)

    def test_every_room_and_d02_partition_loads_exact_identity(self) -> None:
        for room_id in (*PRINCIPAL_ROOM_IDS, "focused_portrait_review"):
            with self.subTest(room_id=room_id):
                frame = self.package.load_room(room_id)
                self.assertGreater(len(frame), 0)
                if "room_id" in frame.columns:
                    self.assertEqual(set(frame["room_id"].astype(str)), {room_id})

        with self.assertRaises(DashboardContractError):
            self.package.load_room("unknown_room")

    def test_painting_partition_is_lazy_and_identity_preserving(self) -> None:
        painting = self.package.load_painting("p001")
        self.assertEqual(painting["schema_version"], "dashboard_painting_partition.v1")
        self.assertEqual(painting["release_id"], self.bootstrap["release_id"])
        self.assertEqual(painting["painting_id"], "p001")
        self.assertEqual(painting["painting"]["painting_id"], "p001")
        self.assertGreater(len(painting["cases"]), 0)
        self.assertGreater(len(painting["candidates"]), 0)

        with self.assertRaises(DashboardContractError):
            self.package.load_painting("p301")
        with self.assertRaises(DashboardContractError):
            self.package.load_painting("../p001")

    def test_safe_paths_and_manifest_checksums_fail_closed(self) -> None:
        verified = self.package.verify_relative_file(
            "data/bootstrap/bootstrap.json",
            checksum=True,
        )
        self.assertEqual(verified.resolve(), BOOTSTRAP_PATH.resolve())

        safe = safe_project_path(
            "outputs/34_final_streamlit_dashboard_assets/data/bootstrap/bootstrap.json",
            ROOT,
        )
        self.assertEqual(safe.resolve(), BOOTSTRAP_PATH.resolve())
        for unsafe in (
            "",
            ".",
            "../escape",
            "C:/absolute/path",
            "https://example.test/file",
            "data\\windows-style",
        ):
            with self.subTest(path=unsafe):
                self.assertIsNone(safe_project_path(unsafe, ROOT))

        with self.assertRaises(DashboardContractError):
            self.package.verify_relative_file("README.md", checksum=True)

    def test_asset_rendition_and_locator_apis_preserve_identity(self) -> None:
        bindings = self.package.bindings_for(room_id="exhibition_foyer")
        asset_refs = [
            str(value).split(":", 1)[1]
            for value in bindings["payload_ref"].astype(str)
            if str(value).startswith("asset:")
        ]
        self.assertTrue(asset_refs)

        local_asset_id = None
        local_path = None
        remote_asset_id = None
        remote_locators = None

        for asset_id in dict.fromkeys(asset_refs):
            record = self.package.asset_record(asset_id)
            self.assertEqual(str(_value(record, "asset_id")), asset_id)

            if local_path is None:
                candidate = self.package.local_rendition(asset_id, verify=True)
                if candidate is not None:
                    local_asset_id = asset_id
                    local_path = candidate

            if remote_locators is None:
                candidates = self.package.locator_candidates(asset_id)
                if len(candidates):
                    remote_asset_id = asset_id
                    remote_locators = candidates

        self.assertIsNotNone(local_asset_id)
        self.assertTrue(Path(local_path).is_file())
        self.assertIsNotNone(remote_asset_id)
        self.assertGreater(len(remote_locators), 0)

        remote_only = remote_locators.loc[
            ~remote_locators["transport"].astype(str).eq("local_package")
        ]
        self.assertGreater(len(remote_only), 0)
        revisions = remote_only["revision"].astype(str).tolist()
        expected_sha256 = remote_only["expected_sha256"].astype(str).tolist()
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{40}", value) for value in revisions))
        self.assertTrue(
            all(re.fullmatch(r"[0-9a-f]{64}", value) for value in expected_sha256)
        )

        with self.assertRaises(DashboardContractError):
            self.package.asset_record("asset_does_not_exist")

    def test_report_index_and_local_report_api_are_verified(self) -> None:
        catalogue = self.package.load_reports()
        reports = catalogue["reports"]
        self.assertEqual(catalogue["report_count"], 337)
        self.assertEqual(len(reports), 337)
        report_id = str(reports[0]["report_id"])
        record = self.package.report_record(report_id)
        self.assertEqual(str(_value(record, "report_id")), report_id)
        resolved = self.package.local_report_bytes(report_id)
        self.assertIsNotNone(resolved)
        payload, filename = resolved
        self.assertIsInstance(payload, bytes)
        self.assertGreater(len(payload), 0)
        self.assertEqual(filename, Path(record["report_path"]).name)


if __name__ == "__main__":
    unittest.main()
