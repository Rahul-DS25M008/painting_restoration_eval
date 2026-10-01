"""Read-only Stability Lab bindings. No inference or scientific recomputation."""
from __future__ import annotations

from functools import lru_cache
import pandas as pd
from .evidence_transport import table

from .model_gallery import (ROOT, MAIN_MODELS, LABELS, catalogue, image_uri,
                            project_path, painting_geometry, records, candidate_metrics)

SD = "stable_diffusion_inpainting"
SIZE_STEM = "05_damage_size_sensitivity_dataset_generation"
MASK_STEM = "06_mask_robustness_dataset_generation"
DEGRADATION_STEM = "07_synthetic_degradation_dataset_generation"
SEED_STEMS = ("18_diffusion_uncertainty_analysis", "22_damage_size_diffusion_uncertainty_extension")
TESTS = {"size": "Damage size", "mask": "Mask placement", "degradation": "Degradation stress", "seed": "Repeated seeds"}
FAMILIES = {"dirt_dust": "Dirt / dust", "partial_transparency": "Partial transparency",
            "water_stain": "Water stain", "water_stain_dirt": "Water stain + dirt"}
CONDITIONS = {"scratch_thin": "Thin scratches · 2%", "loss_small": "Small loss · 4.5%", "loss_large": "Large loss · 12.5%"}
EVIDENCE = {
    "spatial_masked_error": {"label": "Spatial masked error", "region": "masked_region", "direction": "Lower is better", "unit": "Recorded RGB error"},
    "boundary_error": {"label": "Boundary error", "region": "boundary_ring", "direction": "Lower is better", "unit": "Recorded RGB error"},
    "crop_ssim": {"label": "Crop SSIM", "region": "mask_bbox_crop", "direction": "Higher is better", "unit": "SSIM"},
}
NOTES = {
    "size": ("Change the loss, not the painting", "Seven nested masks: 2–20% of painting content. This is one painting’s recorded trajectory, not a universal damage threshold."),
    "mask": ("Same condition, five placements", "Compare placements within a fixed family–area condition. Family and area are paired; their effects cannot be separated here."),
    "degradation": ("Controlled RGB stress", "Four eligible masked-removal families. These procedural image changes are not physical ageing chemistry or conservation treatments."),
    "seed": ("Four seeds, one fixed policy", "Six unordered pairs per group. Empirical disagreement is not calibrated confidence; consistently similar results can still be wrong."),
}
LEDGER = {
    "size": {"title": "Damage-size sensitivity", "counts": "35 paintings · 245 cases · 980 primary candidates", "finding": "Across 11 separate quality anchors, LaMa had the lowest adverse slope on 5, Stable Diffusion on 4, Telea on 2 and HINT on 0. LaMa ranked first at all seven aggregate size levels; anchors and individual paintings still disagree.", "boundary": "The opening p018 / LaMa example has the steepest observed painting-level adverse slope for spatial masked error. This is not a universal failure threshold.", "source": "N23 · damage_size_analysis.csv"},
    "mask": {"title": "Mask-placement robustness", "counts": "35 paintings · 105 groups · 525 cases · 2,100 candidates", "finding": "LaMa had the lowest within-group MAD on 10 of 11 separate anchors; Telea on 1. The winning method changed in 625 of 1,155 group–anchor comparisons.", "boundary": "Only five variants in each fixed family–area condition. Cases are repeated observations, not independent paintings.", "source": "N24 · mask_robustness_analysis.csv"},
    "degradation": {"title": "Procedural degradation stress", "counts": "1,155 generated · 350 eligible cases · 1,400 primary candidates", "finding": "LaMa led all four eligible families on 8 of 11 separate anchors. Eleven SDXL candidates are a bounded descriptive subset, not part of a full ranking.", "boundary": "Zero changed pixels outside the effect mask checks construction of the input—not correctness of the repair. Blur, fading and colour effects are not inpainting rankings.", "source": "N25 · degradation_analysis.csv"},
    "seed": {"title": "Repeated-seed variability", "counts": "1,025 four-seed groups · 4,100 memberships · 6,150 pairs", "finding": "780 canonical prompt-specific groups and 245 damage-size groups. Each group fixes the input and prompt policy, changing only its recorded seed.", "boundary": "Empirical variability is not probability, calibrated uncertainty, historical truth or conservation safety. Deterministic methods have no seed drawer.", "source": "N18 + N22 · recorded uncertainty metrics"},
}


@lru_cache(maxsize=1)
def test_catalogue():
    result = {}
    for kind, stem in (("size", SIZE_STEM), ("mask", MASK_STEM), ("degradation", DEGRADATION_STEM)):
        frame = pd.read_csv(ROOT / "outputs" / stem / "data/cases.csv")
        result[kind] = records(frame)
    result["paintings"] = sorted({r["painting_id"] for r in result["size"]})
    return result


@lru_cache(maxsize=1)
def spatial_index():
    columns = ["spatial_diagnostic_id", "candidate_id", "region_id", "restored_error_mean", "damaged_error_mean", "status"]
    selected = []
    for chunk in table("tables/spatial.csv.gz", usecols=columns, chunksize=100000):
        selected.extend(records(chunk[chunk.region_id.isin(["masked_region", "boundary_ring"])]))
    index = {}
    for row in selected:
        key = (row["candidate_id"], row["region_id"])
        if key in index:
            raise ValueError(f"Duplicate spatial evidence: {key}")
        index[key] = row
    return index


def metric(candidate_id, evidence):
    if evidence == "crop_ssim":
        row = candidate_metrics(candidate_id)["crop_ssim"]
        return {"value": row["restored_value"] if row and row["status"] == "ok" else None,
                "input_value": row.get("damaged_value") if row else None,
                "source": "N13 · classical_metrics.csv", "row_id": candidate_id + " / ssim / mask_bbox_crop"}
    row = spatial_index().get((candidate_id, EVIDENCE[evidence]["region"]))
    return {"value": row["restored_error_mean"] if row and row["status"] == "ok" else None,
            "input_value": row.get("damaged_error_mean") if row else None,
            "source": "N16 · spatial_diagnostics.csv", "row_id": row["spatial_diagnostic_id"] if row else "missing"}


@lru_cache(maxsize=1)
def seed_catalogue():
    """Group by producer group ID, never by case alone (two canonical prompts)."""
    groups = {}
    for stem, filename in zip(SEED_STEMS, ("uncertainty_metrics.csv", "damage_size_uncertainty.csv")):
        cols = ["uncertainty_group_id", "case_id", "painting_id", "prompt_variant_id", "observation_level", "metric_name", "region_id", "value", "value_unit", "status", "candidate_id_a", "candidate_id_b", "seed_a", "seed_b", "uncertainty_metric_id"]
        name = "seed18" if stem == SEED_STEMS[0] else "seed22"
        for chunk in table(f"tables/{name}.csv.gz", usecols=cols, chunksize=50000):
            keep = chunk.region_id.eq("masked_region") & chunk.metric_name.isin(["pairwise_rgb_mae", "pixel_rgb_std_mean"])
            for row in records(chunk[keep]):
                gid = row["uncertainty_group_id"]
                group = groups.setdefault(gid, {"id": gid, "case_id": row["case_id"], "painting_id": row["painting_id"], "prompt": row["prompt_variant_id"], "stem": stem, "pairs": [], "members": {}, "std": None})
                if row["observation_level"] == "candidate_pair":
                    group["pairs"].append(row)
                    for suffix in ("a", "b"):
                        group["members"][int(row["seed_" + suffix])] = row["candidate_id_" + suffix]
                elif row["status"] == "ok":
                    group["std"] = row["value"]
    for group in groups.values():
        if len(group["members"]) != 4 or len(group["pairs"]) != 6:
            raise ValueError(f"Incomplete seed group: {group['id']}")
    return groups


@lru_cache(maxsize=1)
def seed_candidates():
    result = {}
    for stem in ("11_stable_diffusion_restoration", SEED_STEMS[1]):
        frame = pd.read_csv(ROOT / "outputs" / stem / "data/candidates.csv", low_memory=False)
        for row in records(frame[frame.status.eq("completed")]):
            row["resolved_path"] = str(project_path(row["restored_path"], f"outputs/{stem}"))
            result[row["candidate_id"]] = row
    return result


def seed_options(painting):
    return sorted((g for g in seed_catalogue().values() if g["painting_id"] == painting), key=lambda g: (g["case_id"], g["prompt"]))


def group_for_case(case):
    return next((g for g in seed_catalogue().values() if g["case_id"] == case and g["prompt"] == "p00_generic"), None)


def seed_payload(group):
    members = []
    for seed, cid in sorted(group["members"].items()):
        row = seed_candidates()[cid]
        if row["case_id"] != group["case_id"] or row["prompt_variant_id"] != group["prompt"]:
            raise ValueError("Seed-group membership does not match its recorded case/prompt")
        members.append({"seed": seed, "candidate_id": cid, "uri": image_uri(row["resolved_path"], row["restored_sha256"])})
    result = dict(group, members=members, overlay=None)
    if group["stem"] == SEED_STEMS[1]:
        maps = pd.read_csv(ROOT / "outputs" / SEED_STEMS[1] / "manifests/map_images.csv")
        rows = records(maps[maps.uncertainty_group_id.eq(group["id"])])
        if len(rows) == 1:
            row = rows[0]
            result["overlay"] = image_uri(str(project_path(row["relative_path"], "outputs/" + SEED_STEMS[1])), row["sha256"])
    return result


def selection(query):
    kind = query.get("stability_test", "size")
    model = query.get("stability_model", "lama")
    painting = query.get("stability_painting", "p018")
    evidence = query.get("stability_evidence", "spatial_masked_error")
    if kind not in TESTS or model not in MAIN_MODELS or evidence not in EVIDENCE:
        raise ValueError("Unknown Stability Lab test, method or evidence selection")
    allowed = sorted({g["painting_id"] for g in seed_catalogue().values()}) if kind == "seed" else test_catalogue()["paintings"]
    if painting not in allowed:
        raise ValueError("Painting is not in this recorded test population")
    if kind == "seed" and model != SD:
        raise ValueError("Repeated seeds requires an explicit switch to Stable Diffusion")
    rows = [r for r in test_catalogue().get(kind, []) if r["painting_id"] == painting]
    condition = query.get("stability_condition", "loss_large")
    family = query.get("stability_family", "dirt_dust")
    if condition not in CONDITIONS or family not in FAMILIES:
        raise ValueError("Unknown mask condition or eligible degradation family")
    group = None
    if kind == "size":
        rows.sort(key=lambda r: r["target_damage_fraction"])
        labels = [f"{r['target_damage_fraction'] * 100:g}%" for r in rows]
    elif kind == "mask":
        rows = sorted((r for r in rows if r["mask_type"] == condition), key=lambda r: r["variant_index"])
        labels = [f"Variant {int(r['variant_index']):02}" for r in rows]
    elif kind == "degradation":
        rows = sorted((r for r in rows if r["degradation_family"] == family), key=lambda r: r["severity_rank"])
        labels = [r["severity"].title() for r in rows]
    else:
        options = seed_options(painting)
        gid = query.get("stability_group")
        group = seed_catalogue().get(gid) if gid else group_for_case(f"damage_size__{painting}__loss_large__size_20pct") or options[0]
        if not group or group["painting_id"] != painting:
            raise ValueError("Seed group is not recorded for this painting")
        rows, labels = [{"case_id": group["case_id"]}], [group["case_id"].split("__")[-1].replace("_", " ")]
    if not rows:
        raise ValueError("No recorded cases for this selection")
    ids = [r["case_id"] for r in rows]
    selected = query.get("stability_case") or (ids[-1] if kind == "size" else ids[0])
    if selected not in ids:
        raise ValueError("Case does not belong to this test selection; nothing substituted")
    return {"test": kind, "model": model, "painting": painting, "evidence": evidence, "condition": condition, "family": family, "rows": rows, "labels": labels, "selected": selected, "group": group, "paintings": allowed}


def payload(query):
    selected = selection(query)
    cat = catalogue()
    points = []
    for source, label in zip(selected["rows"], selected["labels"]):
        case = source["case_id"]
        inputs = cat["cases"][case]
        candidate = cat["models"][selected["model"]][case]
        # A seed-group view uses its exact seed-2026 candidate, including p05.
        if selected["group"]:
            candidate = seed_candidates()[selected["group"]["members"][2026]]
        points.append({"case_id": case, "label": label, "x": source.get("target_damage_fraction"),
                       "candidate_id": candidate["candidate_id"], "metric": metric(candidate["candidate_id"], selected["evidence"]),
                       "damaged": image_uri(str(project_path(inputs["input_image_path"])), inputs["input_sha256"]),
                       "mask": image_uri(str(project_path(inputs["mask_or_effect_path"])), inputs["mask_sha256"]),
                       "restored": image_uri(candidate["resolved_path"], candidate["restored_sha256"])})
    current = next(p for p in points if p["case_id"] == selected["selected"])
    seed_group = selected["group"] or (group_for_case(selected["selected"]) if selected["model"] == SD else None)
    source = cat["cases"][selected["selected"]]
    masks = [r for r in sorted(test_catalogue()["mask"], key=lambda r:r["variant_index"]) if r["painting_id"] == selected["painting"] and r["mask_type"] == selected["condition"]]
    mask_previews = []
    for row in masks:
        inputs = cat["cases"][row["case_id"]]
        mask_previews.append(image_uri(str(project_path(inputs["mask_or_effect_path"])), inputs["mask_sha256"]))
    return {k: v for k, v in selected.items() if k not in ("rows", "group")} | {
        "points": points, "reference": image_uri(str(project_path(source["clean_image_path"]))),
        "content_bbox": painting_geometry()[selected["painting"]], "evidence_spec": EVIDENCE[selected["evidence"]],
        "focused_paintings": test_catalogue()["paintings"],
        "mask_cases": [r["case_id"] for r in masks], "mask_previews": mask_previews,
        "seed": seed_payload(seed_group) if seed_group else None,
        "seed_options": [{"id": g["id"], "label": g["case_id"].split("__", 2)[-1].replace("_", " ") + " · " + g["prompt"]} for g in seed_options(selected["painting"])],
        "current": current, "ledger": LEDGER, "notes": NOTES,
        "version": "stability-v1:" + ":".join(str(selected[k]) for k in ("test", "painting", "model", "evidence", "selected")) + ":" + (seed_group["id"] if seed_group else "no-seed")}
