from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from restoration_eval.explainable_case_retrieval import (
    CASE_NEIGHBOR_COLUMNS,
    CONFIG_SCHEMA_VERSION,
    EXPLANATION_CASE_COLUMNS,
    EXPLANATION_SCHEMA_VERSION,
    NEIGHBOR_SCHEMA_VERSION,
    atomic_write_csv,
    coerce_explanation_cases,
    load_embedding_index,
    load_explainable_case_retrieval_config,
    resolve_explainable_case_retrieval_inputs,
    retrieve_neighbors,
    validate_case_neighbors,
    validate_explanation_cases,
    validate_explanation_report_html,
    validate_upstream_completion,
)
from restoration_eval.paths import find_project_root


PROJECT_ROOT = find_project_root(Path(__file__))
CONFIG_PATH = PROJECT_ROOT / "config" / "evaluation" / "explainable_case_retrieval.yaml"


class ExplainableCaseRetrievalTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_explainable_case_retrieval_config(CONFIG_PATH)
        cls.inputs = resolve_explainable_case_retrieval_inputs(cls.config, PROJECT_ROOT)

    def test_config_and_exact_output_contract(self) -> None:
        self.assertEqual(self.config["config_schema_version"], CONFIG_SCHEMA_VERSION)
        settings = self.config["explainable_case_retrieval"]
        self.assertEqual(settings["explanation_schema_version"], EXPLANATION_SCHEMA_VERSION)
        self.assertEqual(settings["neighbor_schema_version"], NEIGHBOR_SCHEMA_VERSION)
        self.assertEqual(settings["output"]["root"], "outputs/29_explainable_ai_and_case_retrieval")
        self.assertEqual(settings["expected_counts"]["explanation_rows"], 1785)
        self.assertEqual(settings["expected_counts"]["neighbor_rows"], 100)
        self.assertEqual(settings["expected_counts"]["selected_report_units"], 24)
        self.assertTrue(settings["catalog"]["full_population_required"])
        self.assertTrue(settings["catalog"]["selection_does_not_filter_persisted_rows"])
        self.assertFalse(settings["retrieval"]["combine_feature_scores"])
        self.assertEqual(len(self.inputs), len(settings["inputs"]))

    def test_upstream_manifests_are_complete(self) -> None:
        manifests = {
            f"{number:02d}": json.loads(
                self.inputs[f"manifest_{number:02d}_path"].read_text(encoding="utf-8")
            )
            for number in range(15, 29)
        }
        checks = validate_upstream_completion(manifests)
        self.assertEqual(len(checks), 14)
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))

    def test_actual_embedding_views_load_and_align(self) -> None:
        settings = self.config["explainable_case_retrieval"]["retrieval"]
        for feature_model_id in (
            settings["primary_feature_model_id"],
            settings["secondary_feature_model_id"],
        ):
            manifest, vectors = load_embedding_index(
                self.inputs["embedding_manifest_path"],
                self.inputs["embedding_archive_path"],
                feature_model_id=feature_model_id,
                image_role=settings["image_role"],
                region_id=settings["region_id"],
            )
            self.assertEqual(len(manifest), 2160)
            self.assertEqual(len(vectors), 2160)
            self.assertTrue(np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5))

    @staticmethod
    def _catalog() -> pd.DataFrame:
        rows = []
        candidates = [
            ("q", "case_q", "p001", "lama", "specialist_review_required", True),
            ("a", "case_a", "p002", "lama", "suitable_for_preliminary_inspection", False),
            ("b", "case_b", "p003", "opencv_telea", "suitable_for_preliminary_inspection", False),
            ("c", "case_c", "p004", "stable_diffusion_inpainting", "suitable_for_preliminary_inspection", False),
            ("d", "case_d", "p005", "lama", "suitable_for_preliminary_inspection", False),
            ("e", "case_e", "p006", "opencv_telea", "suitable_for_preliminary_inspection", False),
            ("f", "case_f", "p007", "stable_diffusion_inpainting", "specialist_review_required", True),
            ("g", "case_g", "p008", "lama", "do_not_rely_automatically", True),
            ("h", "case_h", "p009", "opencv_telea", "specialist_review_required", True),
            ("i", "case_i", "p010", "stable_diffusion_inpainting", "unstable_candidate", True),
            ("j", "case_j", "p011", "lama", "specialist_review_required", True),
        ]
        for candidate, case_id, painting_id, model_id, recommendation, review in candidates:
            rows.append({
                "candidate_id": candidate,
                "case_id": case_id,
                "painting_id": painting_id,
                "model_id": model_id,
                "recommendation_category": recommendation,
                "manual_review_required": review,
                "category": "portrait_figure" if candidate in {"q", "a"} else "landscape_natural",
                "degradation_family": "scratch_thin",
                "scope_status": "supported",
                "evidence_coverage_status": "complete",
            })
        return coerce_explanation_cases(rows)

    def test_retrieval_enforces_leakage_and_lane_semantics(self) -> None:
        catalog = self._catalog()
        ids = catalog["candidate_id"].tolist()
        manifest = pd.DataFrame({
            "embedding_id": [f"emb_{item}" for item in ids],
            "representative_candidate_id": ids,
            "image_role": "restored",
            "region_id": "content_region",
        })
        rng = np.random.default_rng(29)
        vectors = rng.normal(size=(len(ids), 8)).astype(np.float32)
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        secondary = rng.normal(size=(len(ids), 6)).astype(np.float32)
        secondary /= np.linalg.norm(secondary, axis=1, keepdims=True)
        secondary_manifest = manifest.copy()
        secondary_manifest["embedding_id"] = [f"clip_{item}" for item in ids]
        kwargs = {
            "feature_model_id": "dinov2_vits14",
            "secondary_embedding_manifest": secondary_manifest,
            "secondary_normalized_vectors": secondary,
            "secondary_feature_model_id": "clip_vit_b32",
            "top_k": 5,
        }
        lower = retrieve_neighbors("q", catalog, manifest, vectors, lane="lower_risk", **kwargs)
        flagged = retrieve_neighbors("q", catalog, manifest, vectors, lane="flagged", **kwargs)
        self.assertEqual(len(lower), 5)
        self.assertEqual(len(flagged), 5)
        self.assertTrue(lower["neighbor_recommendation_category"].eq("suitable_for_preliminary_inspection").all())
        self.assertFalse(lower["neighbor_manual_review_required"].any())
        self.assertFalse(flagged["neighbor_recommendation_category"].eq("suitable_for_preliminary_inspection").any())
        combined = pd.concat([lower, flagged], ignore_index=True)
        self.assertTrue(combined["secondary_feature_model_id"].eq("clip_vit_b32").all())
        self.assertTrue(np.isfinite(combined["secondary_cosine_similarity"]).all())
        checks = validate_case_neighbors(combined, config=self.config, require_complete=False)
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))

    def test_catalog_schema_is_full_population_not_report_only(self) -> None:
        frame = self._catalog()
        self.assertEqual(list(frame.columns), list(EXPLANATION_CASE_COLUMNS))
        self.assertEqual(len(frame), 11)
        self.assertFalse(frame["report_selected"].any())
        checks = validate_explanation_cases(frame, config=self.config, require_complete=False)
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))

    def test_report_validator_enforces_mock_and_embedded_assets(self) -> None:
        report = self.config["explainable_case_retrieval"]["report"]
        sections = "".join(
            f'<section id="{section_id}"><h2>{section_id}</h2></section>'
            for section_id in report["required_section_ids"]
        )
        analytical = "".join(
            f'<div data-analytical-view="view-{index}"></div>'
            for index in range(report["minimum_embedded_analytical_views"])
        )
        counterfactuals = "".join(
            f'<div data-counterfactual-panel="cf-{index}"></div>'
            for index in range(report["counterfactual_panel_count"])
        )
        retrievals = "".join(
            f'<div data-retrieval-panel="retrieval-{index}"></div>'
            for index in range(report["retrieval_panel_count"])
        )
        images = "".join(
            '<img src="data:image/png;base64,AA==" alt="embedded evidence">'
            for _ in range(report["minimum_embedded_images"])
        )
        html = (
            "<html><body>"
            f"<h1>{report['title']}</h1><p>{report['subtitle']}</p>"
            + sections + analytical + counterfactuals + retrievals + images
            + "<p>The complete catalog contains 1,785 candidate rows.</p>"
            + ("validated evidence and direct assertion " * 100)
            + "</body></html>"
        )
        checks = validate_explanation_report_html(html, config=self.config)
        self.assertTrue(checks["passed"].all(), checks.to_dict("records"))

    def test_atomic_csv_write_leaves_no_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "table.csv"
            atomic_write_csv(pd.DataFrame({"value": [1, 2]}), path)
            self.assertEqual(pd.read_csv(path)["value"].tolist(), [1, 2])
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
