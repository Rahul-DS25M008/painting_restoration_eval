"""Read-only producer audit for Model Gallery planning; no app/notebook writes."""
import hashlib
import json
from pathlib import Path

import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CASE = "canonical__p018__mixed_damage"
SPECS = {
    "opencv_telea": ("09_opencv_telea_restoration", "restorations.csv"),
    "lama": ("10_lama_restoration", "restorations.csv"),
    "hint_places2": ("12a_hint_restoration", "restorations.csv"),
    "stable_diffusion_inpainting": ("11_stable_diffusion_restoration", "candidates.csv"),
    "sdxl_inpainting": ("12_sdxl_feasibility_or_restoration", "candidates.csv"),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolved(folder, value):
    p = Path(value)
    return ROOT / p if value.startswith("outputs/") else folder / p


def main():
    result = {"scope": "Model Gallery steps 1-2 only", "default_case": CASE,
              "models": {}, "default_assets": [], "issues": []}
    sets, selected_ids = [], set()
    primary_sd = None
    for model, (stem, filename) in SPECS.items():
        folder = ROOT / "outputs" / stem
        table = pd.read_csv(folder / "data" / filename)
        completed = table[table.status.eq("completed")].copy()
        primary = completed
        if model == "stable_diffusion_inpainting":
            primary = completed[completed.is_primary_candidate.eq(True)]
            primary_sd = primary
        missing = [str(v) for v in completed.restored_path if not resolved(folder, v).is_file()]
        info = {"scheduled_rows": len(table), "completed_candidates": len(completed),
                "primary_rows": len(primary), "primary_cases": primary.case_id.nunique(),
                "duplicate_primary_cases": int(primary.case_id.duplicated().sum()),
                "status_counts": table.status.value_counts().to_dict(), "missing_outputs": missing,
                "inventory": (folder / "data" / filename).relative_to(ROOT).as_posix()}
        if "failure_type" in table:
            info["failure_types"] = table.failure_type.value_counts().to_dict()
            info["completed_paintings"] = completed.painting_id.nunique()
        if model != "sdxl_inpainting":
            sets.append(set(primary.case_id))
        rows = primary[primary.case_id.eq(CASE)]
        info["default_rows"] = len(rows)
        for _, row in rows.iterrows():
            selected_ids.add(row.candidate_id)
            path = resolved(folder, row.restored_path)
            with Image.open(path) as image:
                image.load()
                shape = list(image.size)
            asset = {"model_id": model, "candidate_id": row.candidate_id,
                     "path": path.relative_to(ROOT).as_posix(), "size": shape,
                     "sha256_matches": digest(path) == row.restored_sha256}
            for field in ("seed", "prompt_variant_id", "configuration_id"):
                value = row.get(field)
                asset[field] = None if pd.isna(value) else value
            result["default_assets"].append(asset)
        result["models"][model] = info
        print(f"{model}: {len(completed)} completed files; missing={len(missing)}", flush=True)
    common = set.intersection(*sets)
    result["common_four_method_cases"] = len(common)
    result["same_case_sets"] = all(s == common for s in sets)
    result["selector_paintings"] = primary_sd.painting_id.nunique()
    result["case_groups"] = primary_sd.groupby("experiment_id").size().to_dict()
    result["default_sd_identity"] = primary_sd[primary_sd.case_id.eq(CASE)][
        ["candidate_id", "seed", "prompt_variant_id", "prompt", "input_image_path", "clean_image_path", "mask_or_effect_path"]].to_dict("records")
    for kind, relative in {
        "reference": "outputs/02_image_preprocessing/images/clean/p018.png",
        "damaged": "outputs/04_canonical_damaged_image_generation/images/damaged/p018/mixed_damage.png",
        "mask": "outputs/03_canonical_mask_generation/images/masks/p018/mixed_damage.png",
    }.items():
        path = ROOT / relative
        with Image.open(path) as im:
            im.load()
            result["default_assets"].append({"role": kind, "path": relative,
                                            "size": list(im.size), "sha256": digest(path)})
    source_missing = {}
    for column in ("input_image_path", "clean_image_path", "mask_or_effect_path"):
        paths = primary_sd[column].dropna().unique()
        source_missing[column] = [p for p in paths if not (ROOT / p).is_file()]
    result["missing_selector_sources"] = source_missing
    metrics = pd.read_csv(ROOT / "outputs/13_classical_metrics/metrics/classical_metrics.csv", low_memory=False)
    crop = metrics[metrics.metric_name.eq("ssim") & metrics.region_id.eq("mask_bbox_crop")]
    result["crop_ssim_coverage"] = {model: group.groupby("status").size().to_dict()
                                   for model, group in crop.groupby("model_id")}
    result["default_crop_ssim"] = crop[crop.candidate_id.isin(selected_ids)][
        ["candidate_id", "model_id", "damaged_value", "restored_value", "status"]].to_dict("records")
    result["default_classical_evidence_options"] = metrics[metrics.candidate_id.isin(selected_ids)].groupby(
        ["metric_name", "region_id", "status"]).size().to_dict()
    result["default_classical_evidence_options"] = [
        {"metric": key[0], "region": key[1], "status": key[2], "rows": value}
        for key, value in result["default_classical_evidence_options"].items()]
    disagreement = pd.read_csv(ROOT / "outputs/21_multi_model_comparison/metrics/metric_disagreement.csv")
    overall = disagreement[disagreement.analysis_scope.eq("overall") & disagreement.population_id.eq("core_three_model")]
    result["overall_anchor_rows"] = overall[["anchor_id", "winner_model_id", "model_rank_order", "eligible_case_count", "eligible_painting_count"]].to_dict("records")
    cards = pd.read_csv(ROOT / "outputs/30_model_cards_compute_and_scalability/data/model_cards.csv")
    result["model_cards"] = cards[["model_id", "evaluated_case_count", "completed_count", "median_runtime_seconds",
                                    "software_license", "weight_license"]].to_dict("records")
    reports = pd.read_csv(ROOT / "outputs/31_model_report_generation/data/report_index.csv")
    result["full_reports"] = [{"model_id": r.model_id, "path": r.report_path,
        "exists": (ROOT / r.report_path).is_file(), "sha256_matches": digest(ROOT / r.report_path) == r.report_sha256}
        for _, r in reports.iterrows()]
    decision_root = ROOT / "outputs/37_hint_mat_method_selection"
    result["hint_decision"] = json.loads((decision_root / "reports/selection_decision.json").read_text())
    result["hint_decision_files"] = [p.relative_to(ROOT).as_posix() for p in decision_root.rglob("*")
                                     if p.is_file() and p.name in ("method_selection_report.html", "decision_scorecard.csv")]
    package = ROOT / "outputs/34_final_streamlit_dashboard_assets"
    room = pd.read_parquet(package / "data/rooms/model_gallery.parquet")
    bindings = pd.read_csv(package / "manifests/display_components.csv")
    bindings = bindings[bindings.room_id.eq("model_gallery")]
    result["n34_room_records"] = len(room)
    result["n34_bindings"] = bindings[["display_id", "slot_id", "payload_ref", "applicability_state"]].to_dict("records")
    result["issues"] = [
        "N34 room partition contains 12 display-contract records, not a ready all-painting selector catalogue; join producer tables in step 3.",
        "Crop SSIM and most quality anchors exclude empty-mask zero controls; keep unavailable evidence disabled, never fabricate a value.",
        "Legacy population_id core_three_model contains four model IDs; do not expose that internal name as a three-method claim.",
        "SDXL availability must use exact case_id, not painting_id alone.",
        "Static reference side inscription A CLEARER PAST conflicts with the historical-truth boundary; use approved cautious copy at implementation.",
        "Only default exact assets have N34 registered renditions/locators; verify broader selection transport at the later deployment pass.",
    ]
    destination = ROOT / "docs/dashboard_design_finalists/model_gallery_readiness_audit.json"
    destination.write_text(json.dumps(result, indent=2, default=lambda value: value.item() if hasattr(value, 'item') else str(value)) + "\n", encoding="utf-8")
    print(f"Audit saved: {destination}")
    print(json.dumps({"common_cases": len(common), "paintings": result["selector_paintings"],
                      "default_asset_count": len(result["default_assets"]), "issues_logged": len(result["issues"])}, indent=2))


if __name__ == "__main__":
    main()
