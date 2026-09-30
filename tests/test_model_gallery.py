"""Contract checks for the read-only Model Gallery joins."""
import hashlib
import json

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from restoration_eval.model_gallery import (
    ROOT, MAIN_MODELS, catalogue, candidate_metrics, selected_case,
    case_payload, project_path, case_label, painting_geometry,
)


def test_four_methods_share_all_primary_cases(cat):
    assert len(cat["paintings"]) == 300
    assert len(cat["cases"]) == 2620
    assert all(set(cat["models"][m]) == set(cat["cases"]) for m in MAIN_MODELS)
    assert sum(len(c) for c in cat["paintings"].values()) == 2620


def test_all_paintings_have_declared_opening(cat):
    for painting in cat["paintings"]:
        assert selected_case(painting, None) == f"canonical__{painting}__mixed_damage"


def test_invalid_identity_never_silently_substituted():
    with unittest.TestCase().assertRaises(ValueError):
        selected_case("p018", "canonical__p019__mixed_damage")
    with unittest.TestCase().assertRaises(ValueError):
        selected_case("unknown", None)
    with unittest.TestCase().assertRaises(ValueError):
        project_path("../outside.png")


def test_default_matches_registered_candidates_and_measurements(cat):
    payload = case_payload("canonical__p018__mixed_damage")
    expected = [.961546, .968558, .948996, .932026, .891906]
    for (model, entry), value in zip(payload["models"].items(), expected):
        assert abs(entry["metrics"]["crop_ssim"]["restored_value"] - value) < .0000006
        assert entry["candidate"]["case_id"] == payload["case_id"]
        assert entry["uri"].startswith("data:image/png;base64,")
    sd = payload["models"]["stable_diffusion_inpainting"]["candidate"]
    assert sd["seed"] == 2026
    assert sd["candidate_id"] == "sd15__p00__s2026__d0cd65cf894a"
    assert sd["is_primary_candidate"] is True
    json.dumps(payload, allow_nan=False)


def test_no_empty_mask_crop_values_are_invented(cat):
    zeros = [c for c in cat["cases"] if "zero" in c]
    assert len(zeros) == 300
    for case in zeros:
        for model in MAIN_MODELS:
            metrics = candidate_metrics(cat["models"][model][case]["candidate_id"])
            row = metrics["crop_ssim"]
            assert row is None or row["status"] != "ok" or row["restored_value"] is None
            assert metrics["whole_ssim"]["status"] == "ok"


def test_every_case_has_valid_evidence_and_existing_images(cat):
    for model in MAIN_MODELS:
        for case, row in cat["models"][model].items():
            assert project_path(row["resolved_path"]).is_file()
            assert candidate_metrics(row["candidate_id"])["whole_ssim"]["status"] == "ok"
            assert row["case_id"] == case


def test_sdxl_availability_is_case_scoped(cat):
    assert len(cat["models"]["sdxl_inpainting"]) == 24
    assert len(cat["sdxl_scheduled"]) == 35
    assert "canonical__p018__mixed_damage" in cat["models"]["sdxl_inpainting"]
    assert any(c.startswith("canonical__p018__") and c not in cat["models"]["sdxl_inpainting"] for c in cat["cases"])
    assert len({r["painting_id"] for r in cat["models"]["sdxl_inpainting"].values()}) == 19


def test_source_reports_retain_recorded_hashes(cat):
    for report in cat["reports"].values():
        assert hashlib.sha256(project_path(report["report_path"]).read_bytes()).hexdigest() == report["report_sha256"]


def test_cases_keep_experiment_identity(cat):
    groups = {r["experiment_id"] for r in cat["cases"].values()}
    assert len(groups) == 4
    for case, row in cat["cases"].items():
        label = case_label(case)
        assert label
        if row["experiment_id"] == "synthetic_degradation":
            assert "Synthetic masked removal" in label


def test_frame_content_geometry_is_recorded_and_valid():
    boxes = painting_geometry()
    assert len(boxes) == 300
    assert boxes["p018"] == [0, 130, 768, 637]
    assert boxes["p055"] == [0, 103, 768, 664]
    for x0, y0, x1, y1 in boxes.values():
        assert 0 <= x0 < x1 <= 768
        assert 0 <= y0 < y1 <= 768
    assert case_payload("canonical__p018__mixed_damage")["content_bbox"] == boxes["p018"]


def test_notebook_is_not_modified_by_gallery_work():
    notebooks = list((ROOT / "notebooks").glob("35_*.ipynb"))
    assert len(notebooks) == 1
    assert hashlib.sha256(notebooks[0].read_bytes()).hexdigest() == "77dbfb840b22dd590321fe11f75c8e926dbc85f02dcb797bd8bfacafb1d7b673"


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    for name, function in list(globals().items()):
        if name.startswith("test_") and callable(function):
            def run(fn=function):
                fn(catalogue()) if fn.__code__.co_argcount else fn()
            suite.addTest(unittest.FunctionTestCase(run, description=name))
    return suite


if __name__ == "__main__":
    unittest.main()
