"""Verify exhibit provenance and isolation from the principal museum route."""
import pytest
from urllib.parse import urljoin

from restoration_eval import physical_damage as room
from restoration_eval.physical_damage_view import markup
from restoration_eval.room_runtime import navigation_query


@pytest.mark.parametrize("base", ["http://localhost:8501/", "https://example.streamlit.app/~/+/", "http://localhost:8502/museum/"])
@pytest.mark.parametrize("registered", ["/media/example.png", "/museum/media/example.png"])
def test_media_stays_under_the_visible_app_base(base, registered):
    assert urljoin(base + "?room=study_design", room.app_media_url(registered)) == base + "media/example.png"


@pytest.mark.parametrize("url", ["https://other.test/media/a.png", "//other.test/media/a.png", "/media/../a.png", "/static/a.png"])
def test_unexpected_media_urls_are_rejected(url):
    with pytest.raises(ValueError, match="media URL"):
        room.app_media_url(url)


def checked_media(path, index, expected=None):
    room.verified_bytes(path, index, expected)
    return path


@pytest.mark.parametrize("painting", [f"rd{i:03}" for i in range(1, 11)])
def test_all_displayed_candidates_and_seed_figures_are_verified(painting):
    data = room.payload(painting, "seeds", checked_media)
    assert len(data["images"]) == 5
    assert len(data["collection"]) == 10
    assert len(data["observations"]) == 4
    assert [r["seed"] for r in data["seeds"]] == ["2026", "2027", "2028", "2029"]
    assert data["images"][-1]["candidate"] == data["seeds"][0]["candidate"]
    assert all(r["has_clean_reference"] == "False" for r in data["candidates"])


@pytest.mark.parametrize("painting", [f"rd{i:03}" for i in range(1, 11)])
def test_comparators_keep_reference_metrics_separate(painting):
    data = room.payload(painting, "comparison", checked_media)
    assert len(data["comparison_metrics"]) == 4
    assert data["comparison"]["selection_uses_restoration_scores"] == "False"
    assert data["comparison"]["prompt_policy_difference"] == "True"
    for row in data["comparison_metrics"]:
        assert row["physical_crop_lpips"] == row["physical_crop_ssim"] == row["physical_masked_mae"] == ""
        assert float(row["synthetic_crop_lpips"]) >= 0


def test_rejects_unknown_ids_panels_and_digest_mismatch():
    with pytest.raises(ValueError, match="Unknown.*painting"):
        room.payload("rd011", media_fn=checked_media)
    with pytest.raises(ValueError, match="Unknown.*panel"):
        room.payload(panel="../../private", media_fn=checked_media)
    with pytest.raises(ValueError, match="cross-reference mismatch"):
        room.verified_bytes(f"{room.D03}/data/artworks.csv", room.registry(), "0" * 64)
    with pytest.raises(ValueError, match="artifact unavailable"):
        room.local_path("../outside-the-repository")


def test_diagnostics_are_for_exact_primary_candidates():
    data = room.payload(panel="evidence", media_fn=checked_media)
    assert {r["candidate_id"] for r in data["diagnostics"]} == {r["candidate_id"] for r in data["candidates"]}
    assert all(int(r["changed_outside_pixels"]) == 0 for r in data["candidates"])
    assert all(r["expert_assessment"] == "False" for r in data["observations"])


def test_supplementary_query_boundary_and_all_ten_selectors():
    query = {"room": "physical_damage_study", "pd_case": "rd004", "pd_panel": "seeds"}
    assert navigation_query({"room":query["room"], "query":query}, query["room"]) == query
    invalid = {**query, "ar_candidate": "something"}
    assert navigation_query({"room":query["room"], "query":invalid}, query["room"]) is None
    data = room.payload(media_fn=lambda path, index, expected=None:path)
    text = markup(data, "", "shell.png")
    assert text.count('data-exhibit="') == 10
    assert text.count('data-print="') == 5
    assert '?room=study_design' in text
    assert 'data-case="rd004"' in text
    assert 'pd_panel=report' in text


def test_full_report_is_only_requested_on_demand():
    requested = []
    def spy(path, index, expected=None):
        requested.append(path)
        return path
    room.payload(media_fn=spy)
    assert not any(path.endswith(".html") for path in requested)
    result = room.payload(panel="report", media_fn=checked_media)
    assert result["report_uri"].endswith("reports/real_damage_evaluation.html")
