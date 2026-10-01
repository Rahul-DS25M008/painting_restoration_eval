"""Case Explorer: exact N34 identities and saved evidence, with no analysis."""
import csv
import gzip
import hashlib
import json
import random
from functools import lru_cache
from pathlib import Path

from .model_gallery import ROOT, LABELS, image_uri
from .evidence_transport import available

OPENING = "candidate__lama__canonical__p018__mixed_damage__c00"
INDEX = ROOT / "streamlit_assets/evidence/case_explorer"
N29 = "outputs/29_explainable_ai_and_case_retrieval"
LAYERS = {
    "difference": ("Difference", "difference", "masked_signed_improvement.png"),
    "seam": ("Boundary / seam", "seam", "seam.png"),
    "colour": ("Colour", "colour", "colour.png"),
    "texture": ("Texture", "texture", "texture.png"),
    "semantic": ("Semantic & structure", "semantic", "semantic.png"),
    "uncertainty": ("Uncertainty", "uncertainty", ""),
}
METRICS = {
    "delta_e_ciede2000_mean": ("ΔE 2000", "Damaged area", "Lower is better"),
    "lpips": ("LPIPS · AlexNet", "Damage crop", "Lower is better"),
    "ssim": ("SSIM", "Damage crop", "Higher is better"),
}


def unique(rows, field, value):
    matches = [row for row in rows if row.get(field) == value]
    if len(matches) != 1:
        raise ValueError(f"Unknown or ambiguous {field}: {value}")
    return matches[0]


def select_record(package, painting_id="p018", candidate_id=None):
    shard = package.load_painting(painting_id)
    candidates = shard["candidates"]
    if not candidates:
        raise ValueError("No indexed candidates for this painting")
    if candidate_id is None:
        preferred = f"candidate__lama__canonical__{painting_id}__mixed_damage__c00"
        candidate_id = preferred if any(r["candidate_id"] == preferred for r in candidates) else candidates[0]["candidate_id"]
    candidate = unique(candidates, "candidate_id", candidate_id)
    case = unique(shard["cases"], "case_id", candidate["case_id"])
    if candidate["experiment_id"] != case["experiment_id"]:
        raise ValueError("Candidate and case experiment mismatch")
    return shard, candidate, case


def random_candidate(package, painting_id, chooser=random.choice):
    """Fill unspecified factors from real records, once per explicit selection."""
    candidates=package.load_painting(painting_id)["candidates"]
    if not candidates:
        raise ValueError("No saved outputs for the selected painting")
    return chooser(candidates)["candidate_id"]


@lru_cache(maxsize=1)
def counterfactual_choices():
    manifest=json.loads((INDEX/'choices_manifest.json').read_text(encoding='utf-8'))
    raw=(INDEX/'choices.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=manifest['sha256']:
        raise ValueError('Comparison-choice index checksum mismatch')
    rows=json.loads(raw)['rows']
    if len(rows)!=manifest['rows']:
        raise ValueError('Comparison-choice row count mismatch')
    return rows


def layer_state(candidate, key):
    if key not in LAYERS:
        raise ValueError("Unknown evidence layer")
    label, route, preferred = LAYERS[key]
    paths = [p for p in candidate["asset_routes"].get(route, []) if p.lower().endswith((".png", ".jpg", ".jpeg"))]
    paths.sort(key=lambda p: (not bool(preferred and p.endswith(preferred)), p))
    deterministic = candidate["model_id"] in {"lama", "opencv_telea", "hint_places2"}
    reason = ("Not applicable — deterministic method" if key == "uncertainty" and deterministic
              else "No saved image for this candidate")
    if key == "uncertainty" and deterministic:
        paths = []
    return {"key": key, "label": label, "paths": paths, "available": bool(paths),
            "reason": "Available · saved evidence" if paths else reason}


@lru_cache(maxsize=12)
def saved_maps(painting_id):
    manifest = json.loads((INDEX / "maps_manifest.json").read_text(encoding="utf-8"))
    if painting_id not in manifest["shards"]:
        return {}
    raw = (INDEX / f"{painting_id}.maps.json.gz").read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["shards"][painting_id]["sha256"]:
        raise ValueError("Map-index shard checksum mismatch")
    return json.loads(gzip.decompress(raw))


@lru_cache(maxsize=1)
def input_index():
    return json.loads((INDEX / "inputs_manifest.json").read_text(encoding="utf-8"))["images"]


def asset_uri(package, relative, painting_id=None, expected_hash=None):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("Evidence path escapes project")
    matches = package.dashboard_assets.loc[package.dashboard_assets.source_relative_path.eq(relative)]
    hashes = set(matches.source_sha256.dropna())
    if expected_hash:
        hashes.add(expected_hash)
    if not hashes and relative in input_index():
        hashes.add(input_index()[relative])
    if not hashes and relative in panel_index():
        hashes.add(panel_index()[relative])
    if not hashes and painting_id:
        row = saved_maps(painting_id).get(relative)
        if row:
            hashes.add(row["sha256"])
    if len(hashes) != 1:
        raise ValueError(f"Missing or conflicting N34 checksum: {relative}")
    return image_uri(str(path), hashes.pop())


@lru_cache(maxsize=12)
def saved_metrics(painting_id):
    manifest = json.loads((INDEX / "manifest.json").read_text(encoding="utf-8"))
    if painting_id not in manifest["shards"]:
        raise ValueError("Painting not in saved metric index")
    data = (INDEX / f"{painting_id}.json.gz").read_bytes()
    if hashlib.sha256(data).hexdigest() != manifest["shards"][painting_id]["sha256"]:
        raise ValueError("Saved metric shard checksum mismatch")
    return json.loads(gzip.decompress(data))


def candidate_metrics(painting_id, candidate):
    rows = [r for r in saved_metrics(painting_id) if r["candidate_id"] == candidate["candidate_id"]]
    for row in rows:
        if row["case_id"] != candidate["case_id"] or row["model_id"] != candidate["model_id"]:
            raise ValueError("Metric identity mismatch")
    result = []
    for metric, (label, region, direction) in METRICS.items():
        matches = [r for r in rows if r["metric_name"] == metric]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous metric record: {metric}")
        result.append({"label": label, "region": region, "direction": direction,
                       "record": matches[0] if matches else None})
    return result


@lru_cache(maxsize=4)
def source_table(relative):
    from .focused_portrait import verified_source
    with verified_source(relative).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def review_route(candidate):
    rows = source_table("outputs/d02_portrait_skin_tone_and_hand_restoration_audit/data/manual_anatomy_review.csv")
    matches = [r for r in rows if r["candidate_id"] == candidate["candidate_id"]
               and r["case_id"] == candidate["case_id"] and r["review_status"] == "completed"]
    return matches[0]["blind_review_code"] if matches else None


def reports_for(shard, case_id):
    return {"painting": shard["reports"]["painting"],
            "case": next((r for r in shard["reports"]["selected_cases"] if r["case_id"] == case_id), None)}


def payload(package, painting_id="p018", candidate_id=None, layer="difference", image_path=None):
    shard, candidate, case = select_record(package, painting_id, candidate_id)
    layers = [layer_state(candidate, key) for key in LAYERS]
    for item in layers:
        if item["paths"] and not any(available(path) for path in item["paths"]):
            item["available"] = False
            item["reason"] = "Registered evidence has no available exact asset route"
    chosen = unique(layers, "key", layer)
    if image_path is not None and image_path not in chosen["paths"]:
        raise ValueError("Map does not belong to the selected candidate and layer")
    paths = {
        "clean": case["clean_image_path"], "damaged": case["input_image_path"],
        "mask": case["mask_or_effect_path"],
        "restored": (candidate["asset_routes"].get("restored") or [None])[0],
        "evidence": image_path or (chosen["paths"][0] if chosen["paths"] else None),
    }
    images = {}
    for key, path in paths.items():
        try:
            images[key] = {"path": path, "uri": asset_uri(package, path, painting_id,
                           candidate["restored_sha256"] if key == "restored" else None) if path else None,
                           "reason": chosen["reason"] if key == "evidence" and not path else ""}
        except (ValueError, FileNotFoundError) as exc:
            images[key] = {"path": path, "uri": None, "reason": str(exc)}
    paintings = package.painting_lookup[["painting_id", "title", "category"]].to_dict("records")
    selector_rows = [{k: c.get(k) for k in ("candidate_id", "case_id", "model_id", "experiment_id", "seed", "prompt_variant_id", "recommendation_category")} for c in shard["candidates"]]
    geometry = unique(source_table("outputs/02_image_preprocessing/data/preprocessed_images.csv"), "painting_id", painting_id)
    content_bbox = [int(geometry[f"content_{axis}_{edge}"]) for axis, edge in (("x","min"),("y","min"),("x","max"),("y","max"))]
    return {"painting": shard["painting"], "candidate": candidate, "case": case,
            "content_bbox": content_bbox,
            "paintings": paintings, "selector_rows": selector_rows,
            "layers": layers, "layer": layer, "images": images,
            "map_record": saved_maps(painting_id).get(paths["evidence"]),
            "metrics": candidate_metrics(painting_id, candidate), "reports": reports_for(shard, case["case_id"]),
            "review_code": review_route(candidate), "labels": LABELS}


def retrieval_rows():
    rows = source_table(N29 + "/data/case_neighbors.csv")
    if len(rows) != 100 or len({r["query_id"] for r in rows}) != 10:
        raise ValueError("Stored retrieval population drift")
    for row in rows:
        if any(row[k].lower() == "true" for k in ("same_case", "same_painting")) or row["neighbor_candidate_id"] == row["query_candidate_id"]:
            raise ValueError("Invalid self/case/painting retrieval match")
    return rows


def saved_panels(package, family):
    prefix = N29 + "/figures/" + family + "/"
    return sorted(path for path in panel_index() if path.startswith(prefix))


@lru_cache(maxsize=1)
def panel_index():
    return json.loads((INDEX / "panels_manifest.json").read_text(encoding="utf-8"))["panels"]
