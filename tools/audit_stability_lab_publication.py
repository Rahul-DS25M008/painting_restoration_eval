"""Read-only publication coverage and pinned HF download checks; never uploads."""
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from restoration_eval.stability_lab import (
    test_catalogue, seed_catalogue, seed_candidates, catalogue, FAMILIES, MAIN_MODELS,
)
from restoration_eval.model_gallery import project_path, SPECS
from restoration_eval.bundled_assets import RemoteBundleReader


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def remote(repo, revision, path):
    url = f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{path}"
    with urllib.request.urlopen(url, timeout=90) as response:
        return response.read()


def audit():
    tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0"))
    with (ROOT / "outputs/inventory/external_artifact_publication.csv").open(newline="", encoding="utf-8") as stream:
        published = {r["local_relative_path"]: r for r in csv.DictReader(stream)
                     if r["verification_status"] == "verified" and r["publication_status"] == "published_verified"}
    bundled = {}
    bundled_tables = {}
    releases = []
    for name in ("n22c", "n22d", "n16"):
        receipt = json.loads((ROOT / f"outputs/inventory/bundled_publication_{name}_full.json").read_text())
        assert receipt["status"] == "full_remote_verified"
        cat = json.loads(remote(receipt["repo_id"], receipt["revision"], receipt["prefix"] + "/indexes/catalogue.json"))
        if name != "n16":
            entry = cat["other_objects"][receipt["prefix"] + "/indexes/members.csv"]
            members = remote(receipt["repo_id"], receipt["revision"], receipt["prefix"] + "/indexes/members.csv")
            assert len(members) == entry["size_bytes"] and hashlib.sha256(members).hexdigest() == entry["sha256"]
            rows = list(csv.DictReader(io.StringIO(members.decode())))
            assert len(rows) == receipt["asset_count"]
            bundled.update({r["original_relative_path"]: r for r in rows})
        releases.append({"name": name, "repo_id": receipt["repo_id"], "revision": receipt["revision"],
                         "prefix": receipt["prefix"], "assets": cat["asset_count"],
                         "bundles": len(cat["bundles"]), "bundle_cap_bytes": cat["bundle_cap_bytes"]})
        # Match needed table bytes against the immutable remote release metadata.
        for path, entry in cat.get("other_objects", {}).items():
            filename = Path(path).name
            if filename in ("candidates.csv", "damage_size_uncertainty.csv", "spatial_diagnostics.csv"):
                folder = "data" if filename == "candidates.csv" else "metrics"
                local = ROOT / "outputs" / receipt["producer"] / folder / filename
                assert local.stat().st_size == entry["size_bytes"] and digest(local) == entry["sha256"], str(local)
                bundled_tables[local.relative_to(ROOT).as_posix()] = entry

    tables = [f"outputs/{stem}/data/{filename}" for stem, filename in SPECS.values()]
    tables += [f"outputs/{stem}/data/cases.csv" for stem in (
        "05_damage_size_sensitivity_dataset_generation", "06_mask_robustness_dataset_generation",
        "07_synthetic_degradation_dataset_generation")]
    tables += ["outputs/02_image_preprocessing/data/preprocessed_images.csv",
               "outputs/30_model_cards_compute_and_scalability/data/model_cards.csv",
               "outputs/31_model_report_generation/data/report_index.csv",
               "outputs/13_classical_metrics/metrics/classical_metrics.csv",
               "outputs/16_difference_maps_and_spatial_diagnostics/metrics/spatial_diagnostics.csv",
               "outputs/18_diffusion_uncertainty_analysis/metrics/uncertainty_metrics.csv",
               "outputs/22_damage_size_diffusion_uncertainty_extension/metrics/damage_size_uncertainty.csv",
               "outputs/22_damage_size_diffusion_uncertainty_extension/data/candidates.csv",
               "outputs/22_damage_size_diffusion_uncertainty_extension/manifests/map_images.csv"]
    table_coverage = {}
    for rel in tables:
        if rel in tracked:
            table_coverage[rel] = "git_tracked"
        elif rel in bundled_tables:
            table_coverage[rel] = "verified_pinned_hf_table"
        elif rel in published:
            assert digest(ROOT / rel) == published[rel]["sha256"], rel
            table_coverage[rel] = "verified_hf_individual"
        else:
            raise ValueError("Unaccounted table: " + rel)

    tc, groups, models = test_catalogue(), seed_catalogue(), catalogue()
    focused = {r["case_id"] for r in tc["size"] + tc["mask"] + [r for r in tc["degradation"] if r["degradation_family"] in FAMILIES]}
    cases = focused | {g["case_id"] for g in groups.values()}
    assets = {}
    def add(path, sha=None):
        rel = Path(path).resolve().relative_to(ROOT).as_posix()
        if rel in assets and assets[rel] and sha:
            assert assets[rel] == sha
        assets[rel] = sha or assets.get(rel)
    for case in cases:
        row = models["cases"][case]
        for key, sha in (("clean_image_path", None), ("input_image_path", "input_sha256"), ("mask_or_effect_path", "mask_sha256")):
            add(project_path(row[key]), row.get(sha) if sha else None)
        if case in focused:
            for model in MAIN_MODELS:
                row = models["models"][model][case]
                add(row["resolved_path"], row["restored_sha256"])
    sc = seed_candidates()
    for group in groups.values():
        for cid in group["members"].values():
            add(sc[cid]["resolved_path"], sc[cid]["restored_sha256"])
    import pandas as pd
    maps = pd.read_csv(ROOT / "outputs/22_damage_size_diffusion_uncertainty_extension/manifests/map_images.csv")
    for row in maps.to_dict("records"):
        add(project_path(row["relative_path"], "outputs/22_damage_size_diffusion_uncertainty_extension"), row["sha256"])
    counts = {"git_tracked": 0, "verified_hf_individual": 0, "verified_hf_bundle_member": 0}
    missing = []
    for rel, sha in assets.items():
        local = ROOT / rel
        if not local.is_file():
            missing.append(rel + " (local missing)")
        elif rel in tracked:
            counts["git_tracked"] += 1
        elif rel in published:
            row = published[rel]
            assert local.stat().st_size == int(row["size_bytes"]) and (not sha or sha == row["sha256"]), rel
            counts["verified_hf_individual"] += 1
        elif rel in bundled:
            row = bundled[rel]
            assert local.stat().st_size == int(row["size_bytes"]) and (not sha or sha == row["sha256"]), rel
            counts["verified_hf_bundle_member"] += 1
        else:
            missing.append(rel)
    samples = []
    for release in releases[:2]:
        reader = RemoteBundleReader(release["repo_id"], release["revision"], release["prefix"],
                                    ROOT / ".codex_tmp/stability_lab_release_check" / release["name"])
        index = reader.painting("p018", reader.catalogue())
        # Diagnostic map filenames can be opaque IDs; select an explicit
        # indexed p018 member rather than infer case identity from its name.
        chosen = sorted(index["assets"], key=lambda r: r["asset_id"])[0]
        content, row = reader.read_asset("p018", chosen["asset_id"])
        assert hashlib.sha256(content).hexdigest() == digest(ROOT / row["original_relative_path"])
        samples.append({"release": release["name"], "path": row["original_relative_path"],
                        "sha256": row["sha256"], "bytes": len(content),
                        "downloaded_objects": reader.download_count, "downloaded_bytes": reader.download_bytes})
    return {"status": "pass" if not missing else "blocked", "unique_images": len(assets),
            "coverage": counts, "unaccounted": missing, "table_coverage": table_coverage, "releases": releases,
            "live_exact_byte_samples": samples,
            "verification_scope": "Complete image path coverage against Git and verified publication records; live pinned N22 member indexes, table hashes and two exact-image roundtrips, not a fresh full-corpus download.",
            "new_hf_upload_needed": bool(missing)}


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
