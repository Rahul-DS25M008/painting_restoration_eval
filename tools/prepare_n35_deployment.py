"""Build compact, lossless deployment projections; never recompute science.

CSV fields are copied as strings, in producer order, with exact source hashes.
The output is a separate deployment companion, not a replacement N34 release.
"""
from collections import defaultdict
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from restoration_eval.evidence_transport import digest, checked
from restoration_eval.manifests import sha256_file

DEST = ROOT / "streamlit_assets/evidence/deployment"


def save(name, raw, manifest, **details):
    path = DEST / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    manifest["files"][name] = dict(sha256=digest(raw), size_bytes=len(raw), **details)


def json_gz(name, data, manifest):
    save(name, gzip.compress(json.dumps(data, separators=(",", ":"), ensure_ascii=True).encode(), mtime=0), manifest)


def project(name, source, manifest, columns=None, predicate=lambda r: True, per_painting=False, unique=False):
    path = ROOT / source
    expected = []
    ledger = path.parents[1] / "manifests/artifacts.csv"
    with ledger.open(encoding="utf-8-sig", newline="") as stream:
        expected = [r for r in csv.DictReader(stream) if r["relative_path"] == source]
    checksum = sha256_file(path)
    if len(expected) != 1 or checksum != expected[0]["checksum"]:
        raise ValueError("Producer source checksum mismatch: " + source)
    groups = defaultdict(list)
    seen = set()
    input_rows = 0
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = columns or reader.fieldnames
        for row in reader:
            input_rows += 1
            if not predicate(row):
                continue
            values = tuple(row[c] for c in columns)
            if unique and values in seen:
                continue
            if unique:
                seen.add(values)
            groups[row["painting_id"] if per_painting else "all"].append(values)
    for key, rows in groups.items():
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)
        filename = f"tables/{name}/{key}.csv.gz" if per_painting else f"tables/{name}.csv.gz"
        save(filename, gzip.compress(output.getvalue().encode(), mtime=0), manifest,
             source=source, source_sha256=checksum, source_rows=input_rows, rows=len(rows), columns=columns)
    manifest["sources"][source] = dict(sha256=checksum, source_rows=input_rows, selected_rows=sum(map(len, groups.values())))
    print(name, input_rows, "->", sum(map(len, groups.values())), "rows", flush=True)


def tables(manifest):
    project("gallery", "outputs/13_classical_metrics/metrics/classical_metrics.csv", manifest,
        columns=["candidate_id", "metric_name", "region_id", "damaged_value", "restored_value", "improvement_value", "status", "issue", "region_pixel_count"],
        predicate=lambda r: (r["metric_name"], r["region_id"]) in {("ssim", "mask_bbox_crop"), ("mae", "masked_region"), ("ssim", "full_image"), ("mae", "outside_mask_content")})
    project("spatial", "outputs/16_difference_maps_and_spatial_diagnostics/metrics/spatial_diagnostics.csv", manifest,
        columns=["spatial_diagnostic_id", "candidate_id", "region_id", "restored_error_mean", "damaged_error_mean", "status"],
        predicate=lambda r: r["region_id"] in {"masked_region", "boundary_ring"})
    for stem, filename, name in (("18_diffusion_uncertainty_analysis", "uncertainty_metrics.csv", "seed18"), ("22_damage_size_diffusion_uncertainty_extension", "damage_size_uncertainty.csv", "seed22")):
        project(name, f"outputs/{stem}/metrics/{filename}", manifest,
            columns=["uncertainty_group_id", "case_id", "painting_id", "prompt_variant_id", "observation_level", "metric_name", "region_id", "value", "value_unit", "status", "candidate_id_a", "candidate_id_b", "seed_a", "seed_b", "uncertainty_metric_id"],
            predicate=lambda r: r["region_id"] == "masked_region" and r["metric_name"] in {"pairwise_rgb_mae", "pixel_rgb_std_mean"})
    n27 = "outputs/27_failure_taxonomy_and_trustworthiness_flags/metrics/"
    project("identities", n27 + "trustworthiness_flags.csv", manifest,
        columns=["candidate_id", "case_id", "painting_id", "model_id", "experiment_id", "prompt_variant_id", "population_role"], unique=True)
    project("flags", n27 + "trustworthiness_flags.csv", manifest, per_painting=True)
    project("categories", n27 + "failure_assignments.csv", manifest, per_painting=True)
    project("policy", "outputs/28_metric_and_region_policy_ablation/metrics/flag_stability.csv", manifest, per_painting=True)


def build_routes(manifest):
    from n35_final_audit import public_bytes
    audit = json.loads((ROOT / ".codex_tmp/n35_batch10_audit/remote.json").read_text())
    expected_catalogues = {r["receipt"]: r["catalog_sha256"] for r in audit["releases"]}
    routes = defaultdict(list)
    receipts = sorted((ROOT / "outputs/inventory").glob("bundled_publication_*_full.json")) + [ROOT / "config/publication/finished_tabs_01_03_assets.json"]
    for receipt in receipts:
        saved = json.loads(receipt.read_text())
        prefix = saved["prefix"]
        base = {"repo": saved["repo_id"], "revision": saved["revision"]}
        key = receipt.stem.removeprefix("bundled_publication_")
        staging = ROOT / ".codex_tmp/bundled_assets" / key
        if receipt.name == "finished_tabs_01_03_assets.json":
            staging = ROOT / ".codex_tmp/finished_tabs_01_03" / saved["release_id"]
        def metadata(suffix, meta=None):
            local = staging / suffix
            raw = local.read_bytes() if local.is_file() else public_bytes(base["repo"], base["revision"], prefix + "/" + suffix)
            if meta:
                checked(raw, meta)
            if not local.is_file():
                local.parent.mkdir(parents=True, exist_ok=True)
                local.write_bytes(raw)
            return raw
        raw = metadata("indexes/catalogue.json")
        if digest(raw) != expected_catalogues[receipt.relative_to(ROOT).as_posix()]:
            raise ValueError("Catalogue differs from live immutable audit")
        cat = json.loads(raw)
        mp = prefix + "/indexes/members.csv"
        if mp in cat.get("other_objects", {}):
            rows = csv.DictReader(io.StringIO(metadata("indexes/members.csv", cat["other_objects"][mp]).decode("utf-8-sig")))
        else:
            rows = []
            for item in cat["paintings"].values():
                rows.extend(json.loads(metadata(item["path"].removeprefix(prefix + "/"), item))["assets"])
        count = 0
        for row in rows:
            bundle = cat["bundles"][row["bundle_path"]]
            routes[row["original_relative_path"]].append(dict(base, sha256=row["sha256"], size_bytes=int(row["size_bytes"]), member_path=row["member_path"],
                bundle=dict(path=row["bundle_path"], sha256=bundle["sha256"], size_bytes=bundle["size_bytes"])))
            count += 1
        manifest.setdefault("releases", []).append(dict(base, prefix=prefix, catalogue_sha256=digest(raw), member_count=count))
        print(key, count, "indexed routes", flush=True)
    with (ROOT / "outputs/inventory/external_artifact_publication.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["verification_status"] == "verified" and row["publication_status"] == "published_verified":
                routes[row["local_relative_path"]].insert(0, dict(repo=row["repository_id"], revision=row["publication_commit_url"].rstrip("/").split("/")[-1], path=row["path_in_repository"], sha256=row["sha256"], size_bytes=int(row["size_bytes"])))
    # N32 reports are already independent published retrieval units, not ZIPs.
    import yaml
    config = yaml.safe_load((ROOT / "config/publication/external_storage.yaml").read_text())
    def find_record(obj):
        if isinstance(obj, dict):
            if "n32_diagnostics" in obj: return obj["n32_diagnostics"]
            for value in obj.values():
                result = find_record(value)
                if result: return result
    release = find_record(config)
    from huggingface_hub import HfApi
    objects = {r.path: r for r in HfApi(token=False).list_repo_tree(release["repository"], path_in_repo=release["release_prefix"], revision=release["revision"], recursive=True, repo_type="dataset") if hasattr(r, "size")}
    stem = "outputs/32_case_and_painting_report_generation/"
    for path in (ROOT / stem).rglob("*"):
        if not path.is_file() or path.suffix not in {".html", ".png"}: continue
        rel = path.relative_to(ROOT).as_posix()
        suffix = rel.removeprefix(stem)
        matches = [r for p, r in objects.items() if p.endswith("/" + suffix)]
        if len(matches) != 1: raise ValueError("Missing/ambiguous N32 published path: " + rel)
        obj = matches[0]
        sha = obj.lfs.sha256 if obj.lfs else digest(public_bytes(release["repository"], release["revision"], obj.path))
        if obj.size != path.stat().st_size or sha != sha256_file(path): raise ValueError("N32 publication checksum mismatch: " + rel)
        routes[rel].append(dict(repo=release["repository"], revision=release["revision"], path=obj.path, sha256=sha, size_bytes=obj.size))
    shards = {f"{i:02x}": {} for i in range(256)}
    for path, entries in routes.items(): shards[digest(path.encode())[:2]][path] = entries
    for key, entries in shards.items(): json_gz("routes/" + key + ".json.gz", entries, manifest)
    manifest["route_count"] = len(routes)


def sidecars(manifest):
    """Add published provenance/table routes without downloading large tables."""
    shards = {f"{i:02x}": json.loads(gzip.decompress((DEST/f"routes/{i:02x}.json.gz").read_bytes())) for i in range(256)}
    count = 0
    for receipt in sorted((ROOT/"outputs/inventory").glob("bundled_publication_*_full.json")):
        saved = json.loads(receipt.read_text())
        key = receipt.stem.removeprefix("bundled_publication_")
        cat_path = ROOT/".codex_tmp/bundled_assets"/key/"indexes/catalogue.json"
        raw = cat_path.read_bytes()
        release = next(r for r in manifest["releases"] if r["prefix"]==saved["prefix"])
        if digest(raw)!=release["catalogue_sha256"]: raise ValueError("Sidecar catalogue checksum mismatch")
        cat = json.loads(raw)
        stem = "outputs/"+saved["producer"]+"/"
        for remote, meta in cat.get("other_objects",{}).items():
            suffix = remote.removeprefix(saved["prefix"]+"/")
            candidates = [stem+suffix]
            if suffix.startswith("tables/"):
                candidates = [stem+folder+"/"+suffix.split("/",1)[1] for folder in ("metrics","manifests","data")]
            if suffix.startswith("provenance/"):
                filename=suffix.split("/",1)[1]
                candidates=[stem+("validation/" if filename=="checks.csv" else "manifests/")+filename]
            found = [p for p in candidates if (ROOT/p).is_file()]
            if len(found)!=1: continue
            path=found[0]
            # A sidecar is registered only when its local canonical bytes agree.
            if sha256_file(ROOT/path)!=meta["sha256"]: continue
            entry=dict(repo=saved["repo_id"],revision=saved["revision"],path=remote,sha256=meta["sha256"],size_bytes=meta["size_bytes"])
            group=shards[digest(path.encode())[:2]].setdefault(path,[])
            if entry not in group: group.append(entry); count+=1
    for key, entries in shards.items(): json_gz("routes/"+key+".json.gz",entries,manifest)
    manifest["route_count"]=sum(map(len,shards.values()))
    print("Added",count,"exact published sidecar routes (large archives remain metadata-only in the UI)")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=("tables", "routes", "sidecars", "all"), default="all")
    args = parser.parse_args()
    target = DEST / "manifest.json"
    manifest = json.loads(target.read_text()) if target.is_file() else {"schema": "deployment_companion.v1", "files": {}, "sources": {}}
    if args.part in {"tables", "all"}: tables(manifest)
    if args.part in {"routes", "all"}: build_routes(manifest)
    if args.part in {"routes", "sidecars", "all"}: sidecars(manifest)
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Companion:", len(manifest["files"]), "files;", sum(r["size_bytes"] for r in manifest["files"].values()), "bytes")


if __name__ == "__main__":
    main()
