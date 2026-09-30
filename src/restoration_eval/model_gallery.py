"""Read-only joins for the Model Gallery; no inference or metric computation."""
from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SPECS = {
    "opencv_telea": ("09_opencv_telea_restoration", "restorations.csv"),
    "lama": ("10_lama_restoration", "restorations.csv"),
    "hint_places2": ("12a_hint_restoration", "restorations.csv"),
    "stable_diffusion_inpainting": ("11_stable_diffusion_restoration", "candidates.csv"),
    "sdxl_inpainting": ("12_sdxl_feasibility_or_restoration", "candidates.csv"),
}
MAIN_MODELS = tuple(SPECS)[:4]
LABELS = dict(zip(SPECS, ("Telea", "LaMa", "HINT", "Stable Diffusion", "SDXL")))
EVIDENCE = {
    "crop_ssim": {"label": "Crop SSIM", "metric": "ssim", "region": "mask_bbox_crop", "direction": "Higher is better", "explanation": "Structural similarity in the damage bounding-box crop, including its surrounding context."},
    "masked_mae": {"label": "Masked MAE", "metric": "mae", "region": "masked_region", "direction": "Lower is better", "explanation": "Mean absolute pixel error inside the recorded missing-region mask."},
    "whole_ssim": {"label": "Whole-image SSIM", "metric": "ssim", "region": "full_image", "direction": "Higher is better", "explanation": "Structural similarity over the complete normalized canvas, including its padding."},
    "outside_mae": {"label": "Outside-repair MAE", "metric": "mae", "region": "outside_mask_content", "direction": "Lower is better", "explanation": "Mean absolute pixel error in painting content outside the repair mask."},
}


def project_path(value: str, folder: str = "") -> Path:
    relative = Path(value)
    path = (ROOT / relative if value.replace("\\", "/").startswith("outputs/") else ROOT / folder / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("Gallery asset escapes the project")
    return path


def records(frame):
    return json.loads(frame.to_json(orient="records"))


@lru_cache(maxsize=1)
def catalogue():
    models = {}
    scheduled_sdxl = {}
    for model, (stem, filename) in SPECS.items():
        frame = pd.read_csv(ROOT / "outputs" / stem / "data" / filename, low_memory=False)
        if model == "sdxl_inpainting":
            scheduled_sdxl = {r["case_id"]: r for r in records(frame)}
        frame = frame[frame.status.eq("completed")]
        if model == "stable_diffusion_inpainting":
            frame = frame[frame.is_primary_candidate.eq(True)]
        if frame.case_id.duplicated().any():
            raise ValueError(f"Ambiguous primary candidates for {model}")
        models[model] = {}
        for row in records(frame):
            row["resolved_path"] = str(project_path(row["restored_path"], f"outputs/{stem}"))
            models[model][row["case_id"]] = row
    common = set(models[MAIN_MODELS[0]])
    if any(set(models[m]) != common for m in MAIN_MODELS):
        raise ValueError("Four-method primary case coverage differs; do not silently intersect")
    cases = models["stable_diffusion_inpainting"]
    by_painting = {}
    for case, row in cases.items():
        by_painting.setdefault(row["painting_id"], []).append(case)
    for case_ids in by_painting.values():
        case_ids.sort()
    cards = pd.read_csv(ROOT / "outputs/30_model_cards_compute_and_scalability/data/model_cards.csv")
    reports = pd.read_csv(ROOT / "outputs/31_model_report_generation/data/report_index.csv")
    return {"models": models, "cases": cases, "paintings": by_painting,
            "cards": {r["model_id"]: r for r in records(cards)},
            "reports": {r["model_id"]: r for r in records(reports)}, "sdxl_scheduled": scheduled_sdxl}


@lru_cache(maxsize=1)
def metric_index():
    columns = ["candidate_id", "metric_name", "region_id", "damaged_value", "restored_value", "improvement_value", "status", "issue", "region_pixel_count"]
    selected = []
    for chunk in pd.read_csv(ROOT / "outputs/13_classical_metrics/metrics/classical_metrics.csv", usecols=columns, chunksize=100000):
        keep = pd.Series(False, index=chunk.index)
        for spec in EVIDENCE.values():
            keep |= chunk.metric_name.eq(spec["metric"]) & chunk.region_id.eq(spec["region"])
        selected.append(chunk[keep])
    result = {}
    for row in records(pd.concat(selected, ignore_index=True)):
        key = (row["candidate_id"], row["metric_name"], row["region_id"])
        if key in result:
            raise ValueError(f"Duplicate metric row: {key}")
        result[key] = row
    return result


def candidate_metrics(candidate_id):
    index = metric_index()
    return {key: index.get((candidate_id, spec["metric"], spec["region"])) for key, spec in EVIDENCE.items()}


def case_label(case_id: str) -> str:
    row = catalogue()["cases"][case_id]
    group = {"canonical_missing_region": "Canonical", "damage_size_sensitivity": "Damage size", "mask_robustness": "Mask variant", "synthetic_degradation": "Synthetic masked removal"}.get(row["experiment_id"], row["experiment_id"])
    parts = case_id.split("__")
    identity = " · ".join(p.replace("_", " ") for p in parts[2:])
    return f"{group} · {identity}"


def selected_case(painting_id: str, case_id: str | None):
    available = catalogue()["paintings"]
    if painting_id not in available:
        raise ValueError(f"Unknown painting: {painting_id}")
    if case_id is None:
        default = f"canonical__{painting_id}__mixed_damage"
        if default not in available[painting_id]:
            raise ValueError("No declared opening case for this painting")
        return default
    if case_id not in available[painting_id]:
        raise ValueError("Selected case does not belong to this painting; nothing was substituted")
    return case_id


@lru_cache(maxsize=40)
def image_uri(path: str, expected_hash: str | None = None):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError("Image outside project")
    data = resolved.read_bytes()
    if expected_hash and hashlib.sha256(data).hexdigest() != expected_hash:
        raise ValueError(f"Recorded image checksum mismatch: {resolved.name}")
    mime = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(data).decode()


def case_payload(case_id):
    cat = catalogue()
    source = cat["cases"][case_id]
    models = {}
    for model in SPECS:
        row = cat["models"][model].get(case_id)
        if row:
            models[model] = {"label": LABELS[model], "candidate": row,
                             "metrics": candidate_metrics(row["candidate_id"]),
                             "uri": image_uri(row["resolved_path"], row["restored_sha256"]),
                             "card": cat["cards"][model]}
    scheduled = cat["sdxl_scheduled"].get(case_id)
    geometry = painting_geometry()[source["painting_id"]]
    return {"case_id": case_id, "painting_id": source["painting_id"], "case_label": case_label(case_id),
            "content_bbox": geometry,
            "experiment": source["experiment_id"], "models": models, "evidence": EVIDENCE,
            "reference": image_uri(str(project_path(source["clean_image_path"]))),
            "damaged": image_uri(str(project_path(source["input_image_path"])), source["input_sha256"]),
            "mask": image_uri(str(project_path(source["mask_or_effect_path"])), source["mask_sha256"]),
            "sdxl_status": scheduled["status"] if scheduled else "not_scheduled",
            "sdxl_reason": (scheduled.get("failure_type") or scheduled.get("issue") or "") if scheduled else "This exact case was not included in the bounded study.",
            "hint": json.loads((ROOT / "outputs/37_hint_mat_method_selection/reports/selection_decision.json").read_text(encoding="utf-8"))}


@lru_cache(maxsize=1)
def painting_geometry():
    """Recorded content support; used only to hide normalization padding in frames."""
    frame = pd.read_csv(ROOT / "outputs/02_image_preprocessing/data/preprocessed_images.csv")
    result = {}
    for row in records(frame):
        box = [int(row[f"content_{axis}_{edge}"]) for axis, edge in (("x", "min"), ("y", "min"), ("x", "max"), ("y", "max"))]
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= 768 and 0 <= y0 < y1 <= 768):
            raise ValueError(f"Invalid recorded content geometry: {row['painting_id']}")
        result[row["painting_id"]] = box
    return result
