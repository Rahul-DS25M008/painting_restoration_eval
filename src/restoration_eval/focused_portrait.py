"""Read-only D02 mini-room bindings. No fitting, inference, or new flags."""
from functools import lru_cache
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
import base64
import hashlib
import json

import pandas as pd

from .model_gallery import ROOT, LABELS, image_uri
from .evidence_transport import verified_path

D02 = "outputs/d02_portrait_skin_tone_and_hand_restoration_audit"
OPENING = "R005"
RETURN_ROOMS = {"study_design": "Study Design", "trustworthiness": "Trustworthiness", "case_explorer": "Case Explorer"}
REPORT = "reports/portrait_skin_tone_and_hand_audit.html"


def records(frame):
    return frame.astype(object).where(pd.notna(frame), None).to_dict("records")


@lru_cache(maxsize=32)
def verified_source(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Source escapes the project")
    producer = Path(relative).parts[1]
    ledger = pd.read_csv(ROOT / "outputs" / producer / "manifests/artifacts.csv")
    match = ledger[ledger.relative_path.eq(relative)]
    if len(match) != 1 or match.iloc[0].validation_status != "passed":
        raise ValueError(f"Unregistered source: {relative}")
    return verified_path(path, match.iloc[0].checksum, int(match.iloc[0].size_bytes))


@lru_cache(maxsize=16)
def table(relative):
    return pd.read_csv(verified_source(D02 + "/" + relative), keep_default_na=False)


@lru_cache(maxsize=1)
def report_tables():
    """Recover retained CSVs from the source-verified report, not cleaned work/."""
    class Tables(HTMLParser):
        def __init__(self):
            super().__init__()
            self.tables = {}

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "a" and attrs.get("download", "").endswith(".csv"):
                href = attrs.get("href", "")
                if href.startswith("data:") and ";base64," in href:
                    raw = base64.b64decode(href.split(",", 1)[1]).decode("utf-8-sig")
                    self.tables[attrs["download"]] = pd.read_csv(StringIO(raw), keep_default_na=False)
    parser = Tables()
    parser.feed(verified_source(D02 + "/" + REPORT).read_text(encoding="utf-8"))
    required = {"hand_control_design.csv", "skin_profiles.csv", "skin_context_matches.csv", "skin_lightness_associations.csv"}
    if not required.issubset(parser.tables):
        raise ValueError("D02 report lacks required retained tables")
    return parser.tables


def one(frame, column, value):
    match = frame[frame[column].eq(value)]
    if len(match) != 1:
        raise ValueError(f"Missing or ambiguous {column}: {value}")
    return records(match)[0]


def return_room(value):
    if value not in RETURN_ROOMS:
        raise ValueError("Invalid portrait-review return room")
    return value


@lru_cache(maxsize=4)
def producer_cases(stem):
    return pd.read_csv(verified_source(f"outputs/{stem}/data/cases.csv"), keep_default_na=False)


def payload(package, review_code=OPENING, parent="trustworthiness"):
    return_room(parent)
    package.load_room("focused_portrait_review")
    reviews = table("data/manual_anatomy_review.csv")
    if len(reviews) != 32 or reviews.blind_review_code.duplicated().any():
        raise ValueError("D02 blind-review population drift")
    review = one(reviews, "blind_review_code", review_code)
    if review["review_status"] != "completed":
        raise ValueError("Review is not completed")
    painting = package.load_painting(review["painting_id"])
    candidates = [r for r in painting["candidates"] if r["candidate_id"] == review["candidate_id"]
                  and r["case_id"] == review["case_id"] and r["model_id"] == review["model_id"]]
    if len(candidates) != 1 or review["restored_path"] not in candidates[0]["asset_routes"]["restored"]:
        raise ValueError("Review/restoration identity mismatch")
    annotation = one(table("data/anatomical_annotations.csv"), "annotation_id", review["annotation_id"])
    overlaps = table("data/anatomical_overlap_audit.csv")
    overlaps = overlaps[overlaps.case_id.eq(review["case_id"])]
    overlap = one(overlaps, "annotation_id", review["annotation_id"])
    retained = report_tables()
    control = one(retained["hand_control_design.csv"], "hand_control_id", review["hand_control_id"])
    for key in ("case_id", "painting_id", "annotation_id"):
        if control[key] != review[key]:
            raise ValueError("Matched control belongs to another review")
    hand_indices = json.loads(control["hand_flat_indices_json"])
    control_indices = json.loads(control["control_flat_indices_json"])
    if len(hand_indices) != control["hand_pixel_count"] or len(control_indices) != control["control_pixel_count"]:
        raise ValueError("Control geometry/count mismatch")
    if len(set(hand_indices)) != len(hand_indices) or len(set(control_indices)) != len(control_indices) or set(hand_indices) & set(control_indices):
        raise ValueError("Control and hand pixels must be unique and disjoint")
    stem = "04_canonical_damaged_image_generation" if review["case_id"].startswith("canonical__") else "06_mask_robustness_dataset_generation"
    case = one(producer_cases(stem), "case_id", review["case_id"])
    images = {}
    for name, key, digest_key in (("clean", "clean_image_path", "clean_image_sha256"),
                                  ("damaged", "damaged_image_path", "damaged_image_sha256"),
                                  ("mask", "mask_path", "mask_sha256")):
        if case[key] != review[key]:
            raise ValueError("Source image path differs from reviewed evidence")
        images[name] = image_uri(str(ROOT / case[key]), case[digest_key])
    images["restored"] = image_uri(str(ROOT / review["restored_path"]), candidates[0]["restored_sha256"])
    registered = {}
    if review_code == OPENING:
        geometry = json.loads(package.verify_relative_file("data/derived/d02_r005_geometry.json").read_text())
        if geometry["hand_control_id"] != control["hand_control_id"] or set(geometry["control_flat_indices"]) != set(control_indices):
            raise ValueError("Retained report control differs from registered N34 geometry")
        for role in ("d02_r005_difference_crop", "d02_r005_matched_control", "d02_r005_review_panel"):
            match = package.dashboard_assets[package.dashboard_assets.evidence_role.eq(role)]
            if len(match) != 1:
                raise ValueError("Missing registered R005 rendition")
            asset = match.iloc[0]
            path = package.local_rendition(asset.asset_id)
            if path is None:
                raise ValueError("Registered R005 rendition unavailable")
            registered[role] = {"uri": image_uri(str(path)), "asset_id": asset.asset_id,
                                "sha256": asset.output_sha256}
    hand = records(pd.read_parquet(package.verify_relative_file("data/derived/d02_hand_summary.parquet")))
    light = records(pd.read_parquet(package.verify_relative_file("data/derived/d02_lightness_summary.parquet")))
    if len(hand) != 12 or len(light) != 24 or any(r["status"] != "ok" for r in hand+light):
        raise ValueError("D02 summary population/schema drift")
    metrics = table("metrics/hand_region_comparison.csv")
    metrics = metrics[metrics.candidate_id.eq(review["candidate_id"]) & metrics.hand_control_id.eq(control["hand_control_id"])]
    screening = table("data/portrait_screening.csv")
    annotations = table("data/anatomical_annotations.csv")
    scope = {"screened": len(screening), "included": int(screening.screening_status.eq("included").sum()),
             "excluded": int(screening.screening_status.eq("excluded").sum()), "annotations": len(annotations),
             "retained": int(annotations.review_status.isin(["approved", "approved_with_ambiguity"]).sum()),
             "intersections": len(table("data/anatomical_overlap_audit.csv")),
             "eligible": len(table("data/eligible_cases.csv")), "hand_cases": int(retained["hand_control_design.csv"].case_id.nunique()),
             "hand_paintings": int(retained["hand_control_design.csv"].painting_id.nunique()),
             "reviews": len(reviews), "review_cases": int(reviews.case_id.nunique()),
             "visible_failures": int(reviews.overall_anatomy_failure.eq(True).sum()),
             "profiles": len(retained["skin_profiles.csv"]), "context_matches": len(retained["skin_context_matches.csv"])}
    preprocessing = pd.read_csv(verified_source("outputs/02_image_preprocessing/data/preprocessed_images.csv"))
    miniatures = []
    for pid in ("p001", "p002", "p269", "p260"):
        row = one(preprocessing, "painting_id", pid)
        miniatures.append({"painting_id": pid, "uri": image_uri(str(ROOT / row["processed_path"]), row["sha256"])})
    return {"version": "portrait-v1:" + review_code + ":" + parent, "review": review,
            "title": painting["painting"]["title"], "annotation": annotation,
            "polygon": json.loads(annotation["polygon_json"]), "overlap": overlap,
            "control": control, "hand_indices": hand_indices, "control_indices": control_indices,
            "crop": [review[k] for k in ("crop_x_min", "crop_y_min", "crop_x_max", "crop_y_max")],
            "control_crop": [control["control_crop_"+k] for k in ("x_min", "y_min", "x_max", "y_max")],
            "images": images, "registered": registered, "hand": hand, "light": light,
            "metrics": records(metrics), "scope": scope, "labels": LABELS,
            "catalogue": records(reviews), "return_room": parent,
            "profiles": records(retained["skin_profiles.csv"]),
            "matches": records(retained["skin_context_matches.csv"]),
            "associations": records(retained["skin_lightness_associations.csv"]),
            "miniatures": miniatures, "source": D02, "release_id": package.release_id}
