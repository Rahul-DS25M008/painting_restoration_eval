"""Offline, lossless display index. Copies saved rows; never computes metrics."""
import csv
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from restoration_eval.dashboard_application import open_dashboard_package

DEST = ROOT / "streamlit_assets/evidence/case_explorer"
SOURCES = (
    ("13_classical_metrics", "metrics/classical_metrics.csv", "ssim", "mask_bbox_crop"),
    ("14_lpips_metrics", "metrics/lpips_metrics.csv", "lpips", "mask_bbox_crop"),
    ("17_local_consistency_metrics", "metrics/local_consistency.csv", "delta_e_ciede2000_mean", "masked_region"),
)


def build_maps():
    """Retain registered map checksums/scales without opening any image pixels."""
    maps = defaultdict(dict)
    sources = []
    for stem, leaf in (("16_difference_maps_and_spatial_diagnostics", "map_images.csv"),
                       ("17_local_consistency_metrics", "map_images.csv"),
                       ("19_uncertainty_and_spatial_explanation_maps", "map_images.csv"),
                       ("20_semantic_and_structural_consistency", "semantic_maps.csv"),
                       ("22_damage_size_diffusion_uncertainty_extension", "map_images.csv")):
        relative = f"outputs/{stem}/manifests/{leaf}"
        path = ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        with (ROOT / "outputs" / stem / "manifests/artifacts.csv").open(encoding="utf-8-sig", newline="") as handle:
            registered = [r for r in csv.DictReader(handle) if r["relative_path"] == relative]
        if len(registered) != 1 or registered[0]["checksum"] != digest:
            raise ValueError(f"Unverified map manifest: {relative}")
        sources.append({"path": relative, "sha256": digest})
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if not row["relative_path"].lower().endswith(".png") or row["status"] != "passed":
                    continue
                target = row["relative_path"]
                if not target.startswith("outputs/"):
                    target = f"outputs/{stem}/{target}"
                maps[row["painting_id"]][target] = row
    index = {"schema": "case_explorer_saved_maps.v1", "sources": sources, "shards": {}}
    for pid, rows in maps.items():
        raw = gzip.compress(json.dumps(rows, separators=(",", ":")).encode(), mtime=0)
        (DEST / f"{pid}.maps.json.gz").write_bytes(raw)
        index["shards"][pid] = {"sha256": hashlib.sha256(raw).hexdigest(), "rows": len(rows)}
    (DEST / "maps_manifest.json").write_text(json.dumps(index, indent=2)+"\n", encoding="utf-8")
    print(f"Indexed {sum(map(len, maps.values())):,} registered image checksums; no images computed")


def build_panels():
    from restoration_eval.manifests import sha256_path
    stem = "outputs/29_explainable_ai_and_case_retrieval"
    with (ROOT / stem / "manifests/artifacts.csv").open(encoding="utf-8-sig", newline="") as handle:
        registered = list(csv.DictReader(handle))
    index = {"schema": "case_explorer_saved_panels.v1", "sources": [], "panels": {}}
    for family in ("counterfactual_panels", "example_retrieval_panels"):
        relative = stem + "/figures/" + family
        row = next(r for r in registered if r["relative_path"] == relative)
        if sha256_path(ROOT / relative) != row["checksum"]:
            raise ValueError(f"Unverified panel collection: {relative}")
        index["sources"].append({"path": relative, "sha256": row["checksum"]})
        for path in sorted((ROOT / relative).glob("*.png")):
            index["panels"][path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    (DEST / "panels_manifest.json").write_text(json.dumps(index,indent=2)+"\n",encoding="utf-8")
    print(f"Indexed {len(index['panels'])} panels from verified N29 collections")


def build_inputs():
    """Index existing case input hashes, not image bytes or directory scans."""
    index = {"schema": "case_explorer_saved_inputs.v1", "sources": [], "images": {}}
    for stem in ("04_canonical_damaged_image_generation", "05_damage_size_sensitivity_dataset_generation",
                 "06_mask_robustness_dataset_generation", "07_synthetic_degradation_dataset_generation"):
        relative = f"outputs/{stem}/data/cases.csv"
        path = ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        with (ROOT / "outputs" / stem / "manifests/artifacts.csv").open(encoding="utf-8-sig", newline="") as handle:
            record = next(r for r in csv.DictReader(handle) if r["relative_path"] == relative)
        if record["checksum"] != digest:
            raise ValueError(f"Unverified cases: {relative}")
        index["sources"].append({"path": relative, "sha256": digest})
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                for key, checksum in (("clean_image_path","clean_image_sha256"),
                                      ("damaged_image_path","damaged_image_sha256"),
                                      ("mask_path","mask_sha256"),
                                      ("input_image_path","damaged_image_sha256"),
                                      ("mask_or_effect_path","mask_sha256"),
                                      ("degraded_image_path","degraded_image_sha256"),
                                      ("effect_mask_path","effect_mask_sha256")):
                    if row.get(key) and row.get(checksum):
                        existing=index["images"].get(row[key])
                        if existing and existing != row[checksum]:
                            raise ValueError("Conflicting input checksum")
                        index["images"][row[key]]=row[checksum]
    (DEST / "inputs_manifest.json").write_text(json.dumps(index,indent=2)+"\n",encoding="utf-8")
    print(f"Indexed {len(index['images']):,} saved case-input checksums")


def build():
    package = open_dashboard_package(ROOT)
    allowed = {}
    for painting_id in package.painting_lookup.painting_id:
        for candidate in package.load_painting(painting_id)["candidates"]:
            allowed[candidate["candidate_id"]] = painting_id
    rows = defaultdict(list)
    sources = []
    for stem, leaf, metric, region in SOURCES:
        relative = f"outputs/{stem}/{leaf}"
        path = ROOT / relative
        with path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        with (ROOT / "outputs" / stem / "manifests/artifacts.csv").open(encoding="utf-8-sig", newline="") as handle:
            registered = [r for r in csv.DictReader(handle) if r["relative_path"] == relative]
        if len(registered) != 1 or registered[0]["checksum"] != digest:
            raise ValueError(f"Unverified source: {relative}")
        sources.append({"path": relative, "sha256": digest})
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row["metric_name"] != metric or row["region_id"] != region:
                    continue
                if metric == "lpips" and row.get("network") != "alex":
                    continue
                cid = row["candidate_id"]
                if cid not in allowed:
                    continue
                # Strings preserve every source decimal; conversion is display-only.
                row["source_path"] = relative
                row["source_sha256"] = digest
                rows[allowed[cid]].append(row)
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": "case_explorer_saved_rows.v1", "sources": sources,
                "candidate_count": len(allowed), "shards": {}}
    for pid in package.painting_lookup.painting_id:
        raw = json.dumps(rows[pid], separators=(",", ":"), allow_nan=False).encode()
        data = gzip.compress(raw, mtime=0)
        (DEST / f"{pid}.json.gz").write_bytes(data)
        manifest["shards"][pid] = {"sha256": hashlib.sha256(data).hexdigest(), "rows": len(rows[pid])}
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Copied {sum(map(len, rows.values())):,} saved rows for {len(allowed):,} candidates into {len(rows)} painting shards")


if __name__ == "__main__":
    if "--inputs-only" in sys.argv:
        build_inputs()
        sys.exit(0)
    if "--maps-only" not in sys.argv and "--panels-only" not in sys.argv:
        build()
    if "--panels-only" not in sys.argv:
        build_maps()
    build_panels()
    build_inputs()
    from build_case_explorer_choices import build as build_choices
    build_choices()
