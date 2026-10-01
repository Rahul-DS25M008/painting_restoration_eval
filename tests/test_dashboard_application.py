"""Focused tests for the Controlled-300 dashboard runtime contract."""

from __future__ import annotations

import json
import hashlib
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
    GENERAL_DYNAMIC_NUMERIC_PARITY,
    PRINCIPAL_ROOM_IDS,
    DashboardContractError,
    DashboardSelectionError,
    load_dashboard_validation_config,
    open_dashboard_package,
    resolve_display_payload,
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


def _source_function(source: str, name: str) -> str:
    """Return one top-level function exactly as stored in the app source."""

    start = source.index(f"def {name}")
    end = source.find("\ndef ", start + 4)
    if end < 0:
        end = len(source)
    return source[start:end]


def _source_between(source: str, start_marker: str, end_marker: str) -> str:
    """Return a stable source region delimited by two unique markers."""

    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


class StudyDesignInPlaceBridgeTests(unittest.TestCase):
    """Pin the fragment bridge without allowing visual regressions."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")

    def test_active_study_renderer_is_a_fragment(self) -> None:
        renderer_start = self.source.rindex("def render_study_design")
        prefix = self.source[:renderer_start].rstrip()
        self.assertTrue(
            prefix.endswith("@st.fragment"),
            "The active Study Design renderer must rerun as a fragment.",
        )

    def test_study_query_callback_uses_atomic_validated_query_updates(self) -> None:
        callback = _source_function(self.source, "apply_study_query")
        self.assertIn("st.query_params.from_dict(state)", callback)
        self.assertIn(
            '{"study_path", "study_category", "study_option"}',
            callback,
        )
        self.assertIn("if unknown:", callback)
        self.assertIn("if path_id not in STUDY_PATH_DEFAULT_OPTIONS:", callback)
        self.assertIn("if category_id not in STUDY_CATEGORY_ANCHORS:", callback)
        self.assertIn("allowed_options = {", callback)
        self.assertIn("if option_id not in allowed_options[path_id]:", callback)
        self.assertGreaterEqual(callback.count("raise DashboardContractError("), 4)

    def test_visible_selection_anchors_remain_deep_link_fallbacks(self) -> None:
        renderer = self.source[self.source.rindex("def render_study_design"):]
        self.assertIn(
            '<a class="study-specimen{selected_class}" href="{study_href(study_option=row_option)}" target="_self"',
            renderer,
        )
        self.assertIn('data-study-option="{html.escape(row_option, quote=True)}"', renderer)
        self.assertIn(
            'f\'href="{study_href(study_path=key, study_option=STUDY_PATH_DEFAULT_OPTIONS[key])}" \'',
            renderer,
        )
        self.assertIn('f\'target="_self" data-study-path="{key}" \'', renderer)
        self.assertIn(
            '<a class="collection-drawer{active}" href="{study_href(study_category=key)}" target="_self"',
            renderer,
        )
        self.assertIn('data-study-category="{key}"', renderer)

    def test_hidden_button_bridge_and_delegated_controller_are_present(self) -> None:
        renderer = self.source[self.source.rindex("def render_study_design"):]
        self.assertIn('st.container(key="study_control_bridge")', renderer)
        self.assertIn('key=f"study_bridge_path_{key}"', renderer)
        self.assertIn('key=f"study_bridge_category_{key}"', renderer)
        self.assertIn('key=f"study_bridge_option_{row_option}"', renderer)
        self.assertIn(".st-key-study_control_bridge { display:none !important; }", self.source)

        bridge_start = renderer.index("if (window.__studySelectionBridgeV1)")
        bridge_end = renderer.index("\n})();", bridge_start)
        bridge = renderer[bridge_start:bridge_end]
        self.assertIn("document.addEventListener('click', (event) => {", bridge)
        self.assertIn(
            "'.study-stage a[data-study-path], .study-stage a[data-study-category], .study-stage a[data-study-option]'",
            bridge,
        )
        self.assertIn("CSS.escape(key)", bridge)
        self.assertIn("button.click();", bridge)
        for guard in (
            "event.defaultPrevented",
            "event.button !== 0",
            "event.metaKey",
            "event.ctrlKey",
            "event.shiftKey",
            "event.altKey",
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, bridge)
        self.assertIn("event.preventDefault();", bridge)
        for forbidden in (
            "window.location",
            "location.assign",
            "location.replace",
            "location.reload",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, bridge)

    def test_approved_foyer_and_study_visual_source_is_byte_stable(self) -> None:
        # The approved visitor overlay changed only the two link attributes and
        # removed the old server-rendered tour card. Normalize that exact delta
        # before comparing the original Foyer layout fingerprint; do not bless
        # arbitrary new layout bytes by regenerating the baseline.
        foyer = _source_function(self.source, "render_exhibition_foyer")
        for mode in ("tour", "free"):
            hook = f' data-museum-visit="{mode}" aria-haspopup="dialog"'
            self.assertEqual(foyer.count(hook), 1)
            foyer = foyer.replace(hook, "", 1)
        self.assertEqual(foyer.count("</main>"), 1)
        foyer = foyer.replace("</main>", "  {guided_tour_html(package)}\n</main>", 1)
        protected_regions = {
            "navigation_html": _source_function(self.source, "navigation_html"),
            "route_html": _source_function(self.source, "route_html"),
            "render_exhibition_foyer": foyer,
            "foyer_desktop_css": _source_between(
                self.source, ".foyer-stage {", ".study-stage {"
            ),
            "study_desktop_css": _source_between(
                self.source, ".study-stage {", ".pending-shell {"
            ),
            "responsive_780_css": _source_between(
                self.source,
                "@media (max-width: 780px)",
                "@media (max-width: 640px)",
            ),
        }
        approved_sha256 = {
            "navigation_html": "6484f2e74ce29f0e91c009227c011d28510d0dd6b3e95e652bcf63e113398f89",
            "route_html": "65a68fedd2ecfc433123dc93977ec36b6161ebaec63b324a1d8cdd688a4fcee8",
            "render_exhibition_foyer": "6d00ec07764a8c4cafc7d64458899741afaeed4af1a4fa89976f324e778ee917",
            "foyer_desktop_css": "0ee3b70a03d939aedfa16ed7455f80480fb5da8c23beed3f6354a01843d6c921",
            "study_desktop_css": "b0c067e5beaff2b31b1dc67548b8aace4f039471694987798206c38215282657",
            "responsive_780_css": "40da34120bdf0ad3aa96b9cad2291847af9c44fa3365cc245e0de278ff52ef2b",
        }
        for name, region in protected_regions.items():
            with self.subTest(region=name):
                observed = hashlib.sha256(region.encode("utf-8")).hexdigest()
                self.assertEqual(observed, approved_sha256[name])

    def test_approved_visitor_overlay_replaces_legacy_tour_without_source_drift(self) -> None:
        self.assertNotIn("def guided_tour_html(", self.source)
        self.assertIn('render_museum_visit(room_id, scalar_query("tour", "0") == "1")', self.source)
        freeze = json.loads((ROOT / "config/publication/museum_visit_freeze.json").read_text(encoding="utf-8"))
        self.assertEqual(freeze["status"], "user_approved_visual_freeze")
        files = {r["path"]: r for r in freeze["files"]}
        for relative in (
            "streamlit_app.py", "src/restoration_eval/museum_visit.py",
            "streamlit_assets/museum_visit/controller.js",
            "streamlit_assets/museum_visit/tour.json",
            "streamlit_assets/museum_visit/visit.css",
        ):
            with self.subTest(path=relative):
                record = files[relative]
                raw = (ROOT / relative).read_bytes()
                if record["hash_mode"] == "lf_normalized":
                    raw = raw.replace(b"\r\n", b"\n")
                if relative == "streamlit_app.py":
                    sys.path.insert(0, str(ROOT / "tools"))
                    from n35_backend_delta import baseline_source
                    raw = baseline_source(ROOT, relative).encode()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), record["sha256"])


class MetricFrameworkSelectionContractTests(unittest.TestCase):
    """Pin Batch 4 to its approved three-dimension teaching flow."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        cls.package = open_dashboard_package(ROOT)

    def test_metric_renderer_is_fragment_scoped_and_package_driven(self) -> None:
        renderer_start = self.source.index("def render_metric_framework")
        prefix = self.source[:renderer_start].rstrip()
        self.assertTrue(prefix.endswith("@st.fragment"))
        renderer = self.source[renderer_start:]
        self.assertIn('painting_ids = tuple(lookup["painting_id"].astype(str))', renderer)
        self.assertIn('painting_payload = package.load_painting(str(painting_id))', renderer)
        self.assertIn('key="metric_painting_selector"', renderer)
        self.assertNotIn('key="metric_case_selector"', renderer)
        self.assertNotIn('key="metric_candidate_selector"', renderer)
        self.assertIn('aria-label="Select a region"', renderer)
        self.assertIn('aria-label="Choose an evidence lens"', renderer)
        self.assertIn(
            'case_id = f"canonical__{painting_id}__mixed_damage"',
            renderer,
        )
        self.assertIn(
            'expected_candidate_id = f"candidate__lama__{case_id}__c00"',
            renderer,
        )
        self.assertIn("raise DashboardContractError", renderer)
        self.assertIn('<main class="metric-stage"', renderer)
        self.assertNotIn('<main class="pending-shell"', renderer.split("def render_pending_room", 1)[0])

    def test_all_300_paintings_have_exact_canonical_lama_teaching_case(self) -> None:
        painting_ids = tuple(self.package.painting_lookup["painting_id"].astype(str))
        self.assertEqual(len(painting_ids), 300)
        self.assertEqual(len(set(painting_ids)), 300)
        for painting_id in painting_ids:
            payload = self.package.load_painting(painting_id)
            case_id = f"canonical__{painting_id}__mixed_damage"
            candidate_id = f"candidate__lama__{case_id}__c00"
            cases = [
                row
                for row in payload["cases"]
                if str(row["case_id"]) == case_id
            ]
            candidates = [
                row
                for row in payload["candidates"]
                if str(row["candidate_id"]) == candidate_id
            ]
            with self.subTest(painting_id=painting_id):
                self.assertEqual(len(cases), 1)
                self.assertEqual(len(candidates), 1)
                candidate = candidates[0]
                self.assertEqual(str(candidate["case_id"]), case_id)
                self.assertEqual(str(candidate["model_id"]), "lama")
                self.assertTrue(
                    str(candidate.get("availability_state", "")).startswith("available")
                )
                routes = candidate.get("asset_routes", {})
                self.assertTrue(routes.get("restored"))
                self.assertTrue(
                    any(
                        str(path).endswith("masked_signed_improvement.png")
                        for path in routes.get("difference", [])
                    )
                )
                self.assertTrue(
                    any(
                        str(path).endswith((".png", ".webp"))
                        for path in routes.get("colour", [])
                    )
                )
                self.assertTrue(
                    any(
                        str(path).endswith((".png", ".webp"))
                        for path in routes.get("semantic", [])
                    )
                )


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
        self.assertEqual(DASHBOARD_APPLICATION_VERSION, "2.1.0")
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

    def test_foyer_decorative_shell_is_pinned_and_non_scientific(self) -> None:
        shell = self.config["presentation"]["decorative_shells"][
            "exhibition_foyer"
        ]
        shell_path = (ROOT / shell["path"]).resolve()
        self.assertTrue(shell_path.is_relative_to(ROOT.resolve()))
        self.assertTrue(shell_path.is_file())
        observed_sha256 = hashlib.sha256(shell_path.read_bytes()).hexdigest()
        self.assertEqual(observed_sha256, shell["sha256"])
        self.assertFalse(shell["scientific_content_allowed"])
        self.assertTrue(shell["live_overlay_required"])
        self.assertFalse(
            self.config["application"]["runtime_rules"]
            ["decorative_shells_are_scientific_evidence"]
        )

        self.assertEqual(self.config["dataset"]["dataset_scope"], "controlled_300")
        self.assertEqual(
            tuple(self.config["application"]["principal_room_order"]),
            tuple(PRINCIPAL_ROOM_IDS),
        )
        self.assertEqual(self.config["application"]["child_route_count"], 1)

    def test_metric_decorative_shell_is_pinned_and_non_scientific(self) -> None:
        shell = self.config["presentation"]["decorative_shells"][
            "metric_framework"
        ]
        shell_path = (ROOT / shell["path"]).resolve()
        self.assertTrue(shell_path.is_relative_to(ROOT.resolve()))
        self.assertTrue(shell_path.is_file())
        observed_sha256 = hashlib.sha256(shell_path.read_bytes()).hexdigest()
        self.assertEqual(observed_sha256, shell["sha256"])
        self.assertEqual(shell["classification"], "n35_decorative_ambience_only")
        self.assertFalse(shell["scientific_content_allowed"])
        self.assertTrue(shell["live_overlay_required"])
        self.assertEqual(self.config["expected_package"]["package_files"], 377)
        self.assertEqual(self.config["expected_package"]["logical_assets"], 56)
        self.assertEqual(self.config["expected_package"]["renditions"], 48)
        self.assertEqual(self.config["expected_package"]["asset_locators"], 95)

    def test_study_design_shell_and_exact_opening_assets_are_pinned(self) -> None:
        presentation = self.config["presentation"]
        shell = presentation["decorative_shells"]["study_design"]
        shell_path = (ROOT / shell["path"]).resolve()
        self.assertTrue(shell_path.is_relative_to(ROOT.resolve()))
        self.assertTrue(shell_path.is_file())
        self.assertEqual(
            hashlib.sha256(shell_path.read_bytes()).hexdigest(),
            shell["sha256"],
        )
        self.assertFalse(shell["scientific_content_allowed"])
        self.assertTrue(shell["live_overlay_required"])

        opening = presentation["study_design_exact_opening_assets"]
        self.assertEqual(opening["painting_id"], "p001")
        self.assertEqual(opening["source_notebook_id"], "04")
        self.assertEqual(
            opening["evidence_classification"],
            "exact_byte_copy_not_generated",
        )
        self.assertEqual(
            set(opening["assets"]),
            {
                "zero_control",
                "scratch_thin",
                "loss_small",
                "loss_large",
                "mixed_damage",
            },
        )
        for condition_id, record in opening["assets"].items():
            with self.subTest(condition_id=condition_id):
                deployed = (ROOT / record["path"]).resolve()
                source = (ROOT / record["source_path"]).resolve()
                self.assertTrue(deployed.is_relative_to(ROOT.resolve()))
                self.assertTrue(source.is_relative_to(ROOT.resolve()))
                self.assertTrue(deployed.is_file())
                self.assertTrue(source.is_file())
                deployed_hash = hashlib.sha256(deployed.read_bytes()).hexdigest()
                source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
                self.assertEqual(deployed_hash, record["sha256"])
                self.assertEqual(source_hash, record["sha256"])

    def test_study_design_p001_branches_and_scope_are_exact(self) -> None:
        painting = self.package.load_painting("p001")
        self.assertEqual(painting["painting"]["category"], "portrait_figure")
        cases = painting["cases"]
        counts = {}
        for row in cases:
            counts[str(row["experiment_id"])] = (
                counts.get(str(row["experiment_id"]), 0) + 1
            )
        self.assertEqual(
            counts,
            {
                "canonical_missing_region": 5,
                "damage_size_sensitivity": 7,
                "mask_robustness": 15,
                "synthetic_degradation": 33,
            },
        )
        canonical = {
            str(row["case_id"]).removeprefix("canonical__p001__"): row
            for row in cases
            if str(row["experiment_id"]) == "canonical_missing_region"
        }
        self.assertEqual(
            set(canonical),
            {"zero_control", "scratch_thin", "loss_small", "loss_large", "mixed_damage"},
        )
        self.assertTrue(all(bool(row["four_method_eligible"]) for row in canonical.values()))
        self.assertEqual(self.package.population["painting_count"], 300)
        self.assertEqual(self.package.population["visual_category_count"], 5)
        self.assertEqual(self.package.population["registered_case_count"], 3425)
        self.assertEqual(self.package.population["four_model_eligible_case_count"], 2620)

    def test_study_design_source_preserves_parallel_paths_and_boundaries(self) -> None:
        source = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        self.assertIn('APP_BUILD = "n35.batch2.foyer.v4"', source)
        self.assertIn('STUDY_BUILD = "n35.batch3.study.v4"', source)
        self.assertIn("def render_study_design", source)
        self.assertIn("Controlled synthetic damage", source)
        self.assertIn("Eligibility is routing", source)
        self.assertIn("method-eligible cases", source)
        self.assertIn(
            'aria-label="Open the focused portrait review for Juan de Pareja"',
            source,
        )
        self.assertNotIn("restoration-ready", source)
        self.assertNotIn("realistic damage", source.casefold())

    def test_study_design_representatives_have_all_exact_visible_options(self) -> None:
        anchors = {
            "abstraction_surrealism": "p039",
            "architecture_structured": "p026",
            "high_texture_brushwork": "p043",
            "landscape_natural": "p018",
            "portrait_figure": "p001",
        }
        other_options = (
            "dirt_dust__mild",
            "partial_transparency__moderate",
            "water_stain__severe",
            "water_stain_dirt__moderate",
        )
        for category, painting_id in anchors.items():
            with self.subTest(category=category, painting_id=painting_id):
                payload = self.package.load_painting(painting_id)
                self.assertEqual(payload["painting"]["category"], category)
                self.assertEqual(payload["painting"]["case_count"], 60)
                by_id = {str(row["case_id"]): row for row in payload["cases"]}
                self.assertEqual(len(by_id), 60)

                visible_ids = [
                    f"canonical__{painting_id}__{condition}"
                    for condition in (
                        "zero_control",
                        "scratch_thin",
                        "loss_small",
                        "loss_large",
                        "mixed_damage",
                    )
                ]
                visible_ids.extend(
                    f"damage_size__{painting_id}__loss_large__size_{percent:02d}pct"
                    for percent in (2, 4, 6, 8, 10, 15, 20)
                )
                visible_ids.extend(
                    f"mask_robustness__{painting_id}__loss_large__target_12p5pct__variant_{number:02d}"
                    for number in range(1, 6)
                )
                visible_ids.extend(
                    f"synthetic_degradation__{painting_id}__{option}"
                    for option in other_options
                )
                self.assertEqual(len(visible_ids), 21)
                self.assertTrue(set(visible_ids).issubset(by_id))

                for case_id in visible_ids:
                    record = by_id[case_id]
                    input_path = (ROOT / str(record["input_image_path"])).resolve()
                    self.assertTrue(input_path.is_relative_to(ROOT.resolve()))
                    self.assertTrue(input_path.is_file())
                    self.assertIn(painting_id, str(record["case_id"]))
                for option in other_options:
                    record = by_id[
                        f"synthetic_degradation__{painting_id}__{option}"
                    ]
                    self.assertTrue(bool(record["four_method_eligible"]))

        source = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
        self.assertIn("def study_branch_options", source)
        self.assertIn('"study_option"', source)
        self.assertIn('data-study-path="{path_id}"', source)
        self.assertIn('popover="auto"', source)
        self.assertIn("unsafe_allow_javascript=True", source)
        self.assertIn("4 eligible families · 350 / 1,155", source)
        self.assertIn('"display_title": "Village along a River"', source)
        self.assertIn('class="caption-title"', source)
        self.assertIn('class="caption-state"', source)
        self.assertIn('class="status-rule"', source)
        self.assertIn("Eligibility does not mean success", source)
        self.assertIn("missing-region restoration case", source)
        self.assertIn("def study_artwork_svg", source)
        self.assertIn('preserveAspectRatio="xMidYMid {frame_fit}"', source)
        self.assertIn('data-content-box="{x0},{y0},{x1},{y1}"', source)
        self.assertIn('"content_box": (52, 0, 715, 768)', source)
        self.assertIn('"content_box": (0, 130, 768, 637)', source)
        self.assertGreaterEqual(source.count('"frame_fit": "slice"'), 5)
        self.assertIn('class="study-path-icon icon-{key}"', source)
        self.assertIn('data-specimen-count="{len(options)}"', source)
        for specimen_count in (4, 5, 6, 7):
            self.assertIn(
                f'.study-specimens[data-specimen-count="{specimen_count}"]',
                source,
            )
        self.assertIn('.study-specimen::before', source)
        self.assertIn('border:.24cqw ridge #5a3923', source)
        self.assertIn('class="portrait-audit-link"', source)
        self.assertIn('class="portrait-audit-caption">Juan de Pareja', source)
        self.assertIn('class="portrait-audit-stats"', source)
        self.assertIn('.study-stage .portrait-audit-stats', source)
        self.assertIn('font-size:clamp(7px,.68cqw,12px)', source)
        self.assertIn('@media (max-width: 780px)', source)
        self.assertIn('class="study-wall-emblem upper"', source)
        self.assertIn('class="study-wall-art lower"', source)
        self.assertIn(
            '.study-note-wrap:not([data-study-note-id="selection"]) .study-note',
            source,
        )
        for path_id in ("core", "damage_size", "mask_placement", "other_changes"):
            self.assertIn(f'    "{path_id}": """', source)
        active_renderer = source[source.rindex("def render_study_design"):]
        self.assertNotIn("<small>{html.escape(summary)}</small>", active_renderer)
        self.assertNotIn("Open shared mini study room", active_renderer)
        self.assertNotIn('class="study-wall-motto"', active_renderer)
        self.assertNotIn("text-overflow: ellipsis", source[source.index(".study-main-caption"):source.index(".study-status")])

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

    def test_case_explorer_default_is_exact_and_cross_experiment_safe(self) -> None:
        default = self.package.default_selection_for_room("case_explorer")
        self.assertEqual(
            default.as_identifiers(),
            {
                "room_id": "case_explorer",
                "painting_id": "p018",
                "case_id": "canonical__p018__mixed_damage",
                "candidate_id": (
                    "candidate__lama__canonical__p018__mixed_damage__c00"
                ),
                "model_id": "lama",
                "experiment_id": "canonical_missing_region",
            },
        )

        bindings = self.package.bindings_for(room_id="case_explorer")
        self.assertEqual(
            len(bindings.loc[
                bindings["slot_id"].astype(str).eq("case.anchor.views:restored")
            ]),
            1,
        )
        uncertainty_assets = bindings.loc[
            bindings["display_id"].astype(str).eq("case.anchor.uncertainty")
            & bindings["payload_ref"].astype(str).str.startswith("asset:")
        ]
        self.assertTrue(uncertainty_assets.empty)
        uncertainty_parent = bindings.loc[
            bindings["slot_id"].astype(str).eq("case.anchor.uncertainty")
        ]
        self.assertEqual(len(uncertainty_parent), 1)
        self.assertEqual(
            uncertainty_parent.iloc[0]["applicability_state"],
            "not_applicable_deterministic_method",
        )
        self.assertEqual(
            uncertainty_parent.iloc[0]["applicability_reason"],
            (
                "Not applicable — deterministic method; the exact LaMa candidate "
                "has no uncertainty group or uncertainty asset route."
            ),
        )
        self.assertEqual(
            uncertainty_parent.iloc[0]["interpretation"],
            "Not applicable — deterministic method",
        )
        self.assertTrue(
            self.package.bindings_for(display_id="case.anchor.uncertainty")
            .loc[lambda frame: frame["payload_ref"].astype(str).str.startswith("asset:")]
            .empty
        )

        partial = self.package.bindings_for(
            room_id="case_explorer",
            selection={
                "room_id": "case_explorer",
                "painting_id": "p018",
                "experiment_id": "canonical_missing_region",
            },
        )
        self.assertNotIn(
            "binding_6e69c9895f525a454ff8c7ad",
            set(partial["binding_id"].astype(str)),
        )

        with self.assertRaises(DashboardSelectionError):
            self.package.validate_selection(
                {
                    "room_id": "case_explorer",
                    "painting_id": "p018",
                    "experiment_id": "damage_size_sensitivity",
                    "case_id": "canonical__p018__mixed_damage",
                }
            )
        with self.assertRaises(DashboardSelectionError):
            self.package.bindings_for(
                room_id="case_explorer",
                selection={"room_id": "model_gallery"},
            )

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

    def test_focused_portrait_review_accepts_each_registered_entry_room(self) -> None:
        for return_room in ("study_design", "trustworthiness", "case_explorer"):
            with self.subTest(return_room=return_room):
                state = self.package.validate_selection(
                    {
                        "room_id": "focused_portrait_review",
                        "return_room": return_room,
                    }
                )
                self.assertEqual(state.return_room, return_room)

        with self.assertRaises(DashboardSelectionError):
            self.package.validate_selection(
                {
                    "room_id": "focused_portrait_review",
                    "return_room": "metric_framework",
                }
            )

    def test_curated_case_metrics_resolve_only_for_exact_p018_identity(self) -> None:
        selection = self.package.default_selection_for_room("case_explorer")
        expected = {
            "case.metric.ssim": (
                "cm__5e9144459fba36c24db0",
                "ssim",
                0.9685581155347863,
                "unitless",
                "higher_is_better",
            ),
            "case.metric.lpips": (
                "lp__124778c01f1b30a10f77",
                "lpips",
                0.019120559096336365,
                "LPIPS_distance",
                "lower_is_better",
            ),
            "case.metric.colour": (
                "lcmr_ade29e61f83f757bfee1",
                "delta_e_ciede2000_mean",
                4.066130638122559,
                "CIELAB_difference",
                "lower_is_better",
            ),
        }
        for display_id, values in expected.items():
            with self.subTest(display_id=display_id):
                payload = resolve_display_payload(
                    self.package,
                    display_id,
                    selection=selection,
                )
                record = payload.records[0].as_dict()
                self.assertEqual(payload.status, "available")
                self.assertEqual(payload.payload_kind, "curated_typed_record")
                self.assertEqual(payload.source_row_ids, (values[0],))
                self.assertEqual(record["painting_id"], "p018")
                self.assertEqual(record["case_id"], "canonical__p018__mixed_damage")
                self.assertEqual(record["metric_name"], values[1])
                self.assertAlmostEqual(record["restored_value"], values[2])
                self.assertEqual(record["value_unit"], values[3])
                self.assertEqual(record["direction"], values[4])
                self.assertRegex(payload.source_sha256 or "", r"^[0-9a-f]{64}$")

        mismatch = resolve_display_payload(
            self.package,
            "case.metric.ssim",
            selection={
                "room_id": "case_explorer",
                "painting_id": "p018",
                "case_id": "canonical__p018__mixed_damage",
                "candidate_id": "candidate__telea__canonical__p018__mixed_damage__c00",
                "model_id": "telea",
            },
        )
        self.assertEqual(mismatch.status, "unavailable")
        self.assertFalse(mismatch.records)
        self.assertFalse(mismatch.general_dynamic_numeric_parity)

    def test_curated_threshold_is_exact_and_mismatch_never_substitutes(self) -> None:
        exact = {
            "room_id": "trustworthiness",
            "painting_id": "p002",
            "case_id": "canonical__p002__loss_large",
            "candidate_id": "sd15__p00__s2026__29ff258ff921",
            "model_id": "stable_diffusion_inpainting",
            "experiment_id": "canonical_missing_region",
        }
        payload = self.package.resolve_display_payload(
            "trust.threshold.example",
            exact,
        )
        record = payload.records[0].as_dict()
        self.assertEqual(payload.status, "available")
        self.assertEqual(payload.source_row_ids, ("failure_d414420486cfac9f2b57",))
        self.assertEqual(record["metric_name"], "local_texture_error_p95")
        self.assertEqual(record["region_id"], "mask_bbox_crop")
        self.assertAlmostEqual(record["observed_value"], 10.053275680541985)
        self.assertAlmostEqual(record["warning_threshold"], 1.7923734879493693)
        self.assertAlmostEqual(record["critical_threshold"], 4.8924025321006255)
        self.assertEqual(record["direction"], "higher_is_worse")
        self.assertEqual(record["value_unit"], "normalized_unitless")

        mismatch = dict(exact, painting_id="p003")
        refused = self.package.resolve_display_payload(
            "trust.threshold.example",
            mismatch,
        )
        self.assertEqual(refused.status, "unavailable")
        self.assertFalse(refused.records)

    def test_four_derived_payloads_resolve_as_typed_n34_selections(self) -> None:
        trajectory = self.package.resolve_display_payload(
            "stability.damage.trajectory",
            {
                "room_id": "stability_lab",
                "painting_id": "p018",
                "model_id": "lama",
                "experiment_id": "damage_size_sensitivity",
                "metric_name": "restored_error_mean",
                "region_id": "masked_region",
            },
        )
        self.assertEqual(trajectory.status, "available")
        self.assertEqual(trajectory.payload_kind, "typed_parquet_selection")
        self.assertEqual(len(trajectory.records), 7)
        first = trajectory.records[0].as_dict()
        self.assertIsInstance(first["estimate"], float)
        self.assertEqual(first["value_unit"], "normalized_rgb_error")

        for display_id, expected_count in (
            ("trust.threshold.strata", 137),
            ("d02.hand.findings", 12),
            ("d02.lightness.findings", 24),
        ):
            with self.subTest(display_id=display_id):
                payload = self.package.resolve_display_payload(display_id)
                self.assertEqual(payload.status, "available")
                self.assertEqual(len(payload.records), expected_count)
                self.assertRegex(payload.source_sha256 or "", r"^[0-9a-f]{64}$")

        missing = self.package.resolve_display_payload(
            "stability.damage.trajectory",
            {"painting_id": "p300"},
        )
        self.assertEqual(missing.status, "unavailable")
        self.assertFalse(missing.records)

    def test_room_metric_rows_remain_narrative_and_are_never_number_parsed(self) -> None:
        self.assertFalse(GENERAL_DYNAMIC_NUMERIC_PARITY)
        payload = self.package.resolve_display_payload("metric.lens.pixel")
        self.assertEqual(payload.status, "narrative")
        self.assertEqual(payload.payload_kind, "narrative_or_routing_spec")
        self.assertFalse(payload.records)
        self.assertIn("not typed numeric observations", payload.message)

        source = Path(
            resolve_display_payload.__code__.co_filename
        ).read_text(encoding="utf-8")
        function_source = source[
            source.index("def resolve_display_payload("):
            source.index("\ndef _build_artifact_index", source.index("def resolve_display_payload("))
        ]
        self.assertNotIn("producer_binding", function_source)


if __name__ == "__main__":
    unittest.main()
