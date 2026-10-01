"""Read-only Tab 6 bindings: recorded assignments, never a new trust score.

The first-pass local adapter deliberately uses canonical producer files. It does
not run N27, refit thresholds, recompute metrics, or infer missing assignments.
"""
from __future__ import annotations

import hashlib
import json
import math
from functools import lru_cache

import pandas as pd
from .evidence_transport import table

from .model_gallery import ROOT, MAIN_MODELS, LABELS, catalogue, project_path, image_uri, painting_geometry

OPENING = "sd15__p00__s2026__29ff258ff921"
N27 = "outputs/27_failure_taxonomy_and_trustworthiness_flags"
IDENTITY = ("candidate_id", "case_id", "painting_id", "model_id", "experiment_id", "prompt_variant_id", "population_role")
BOUNDARY = "Flags help us decide what to inspect. They are not probabilities, expert verdicts, or proof that a restoration is right or wrong."


def rows(frame):
    # Unlike DataFrame.to_json's default precision, retain full recorded floats.
    return frame.astype(object).where(pd.notna(frame), None).to_dict("records")


@lru_cache(maxsize=8)
def verified(relative):
    path = ROOT / N27 / relative
    manifest = pd.read_csv(ROOT / N27 / "manifests/artifacts.csv")
    entry = manifest[manifest.relative_path.eq(path.relative_to(ROOT).as_posix())]
    if len(entry) != 1 or entry.iloc[0].validation_status != "passed":
        raise ValueError("N27 artifact is not uniquely registered")
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    if digest != entry.iloc[0].checksum:
        raise ValueError(f"N27 checksum mismatch: {relative}")
    return path


@lru_cache(maxsize=1)
def candidate_index():
    frame = table("tables/identities.csv.gz", usecols=list(IDENTITY), dtype=str).fillna("")
    frame = frame.drop_duplicates()
    if frame.candidate_id.duplicated().any() or len(frame) != 13879:
        raise ValueError("N27 union identity/count drift")
    sources = {r["candidate_id"]: r for model in catalogue()["models"].values() for r in model.values()}
    for stem in ("11_stable_diffusion_restoration", "22_damage_size_diffusion_uncertainty_extension"):
        f = pd.read_csv(ROOT / "outputs" / stem / "data/candidates.csv", low_memory=False)
        for row in rows(f[f.status.eq("completed")]):
            row["resolved_path"] = str(project_path(row["restored_path"], f"outputs/{stem}"))
            sources[row["candidate_id"]] = row
    result = {}
    for identity in rows(frame):
        cid = identity["candidate_id"]
        if cid not in sources:
            raise ValueError(f"N27 candidate has no exact restoration: {cid}")
        original = sources[cid]
        case = catalogue()["cases"].get(original["case_id"])
        if case is None:
            raise ValueError("Restoration lacks a registered case")
        source = {key: case[key] for key in ("painting_id", "category", "experiment_id")}
        source.update(original)
        for key in ("case_id", "painting_id", "model_id", "experiment_id"):
            if source[key] != identity[key]:
                raise ValueError(f"Candidate identity mismatch: {cid} / {key}")
        result[cid] = dict(source, **identity)
    return result


@lru_cache(maxsize=24)
def assignment_records(candidate_id):
    if candidate_id not in candidate_index():
        raise ValueError("Candidate is outside the recorded N27 union; nothing substituted")
    result = {}
    for kind, filename, expected, idkey in (
        ("categories", "failure_assignments.csv", 14, "category_id"),
        ("flags", "trustworthiness_flags.csv", 11, "flag_id"),
    ):
        selected = []
        painting = candidate_index()[candidate_id]["painting_id"]
        for chunk in table(f"tables/{kind}/{painting}.csv.gz", chunksize=40000, keep_default_na=False):
            selected.extend(rows(chunk[chunk.candidate_id.eq(candidate_id)]))
        if len(selected) != expected or len({r[idkey] for r in selected}) != expected:
            raise ValueError("Incomplete or duplicate N27 assignment set")
        for row in selected:
            if row["status"] != "ok":
                raise ValueError("Recorded assignment is not ready")
            for key in IDENTITY:
                if row[key] != candidate_index()[candidate_id][key]:
                    raise ValueError("Assignment identity mismatch")
            for key in list(row):
                if key.endswith("_json"):
                    row[key[:-5]] = json.loads(row.pop(key) or "null")
        result[kind] = selected
    return result


def threshold_record(category, indicator, frame):
    observed = category["observed_value_summary"].get(indicator)
    cutoff = category["threshold_summary"].get(indicator)
    if observed is None or not cutoff:
        return None
    # N34's compact table omits experiment/prompt columns. Never guess them from
    # counts: require the exact indicator AND both full-precision N27 cutoffs to
    # identify one and only one registered stratum, otherwise disclose absence.
    # Reuse the exact 137 saved rows during this payload render. Repeated pandas
    # row-wise apply calls needlessly dominated warm filter latency.
    if "n35_saved_strata" not in frame.attrs:
        frame.attrs["n35_saved_strata"] = rows(frame)
    match = [r for r in frame.attrs["n35_saved_strata"] if r["indicator_id"] == indicator
             and math.isclose(r["warning_threshold"], cutoff["warning"], abs_tol=1e-12, rel_tol=1e-12)
             and math.isclose(r["critical_threshold"], cutoff["critical"], abs_tol=1e-12, rel_tol=1e-12)]
    stratum = match[0] if len(match) == 1 else None
    return {"indicator": indicator, "observed": observed, **cutoff,
            "state": category["indicator_states"].get(indicator, "missing"),
            "stratum": stratum, "experiment_id": category["experiment_id"],
            "prompt_variant_id": category["prompt_variant_id"] if indicator.startswith("uncertainty_") else "",
            "fitting_unit": "eligible seed groups" if indicator.startswith("uncertainty_") else "eligible non-zero primary candidates",
            "source_assignment_id": category["assignment_id"]}


@lru_cache(maxsize=12)
def policy_records(candidate_id):
    selected = []
    painting = candidate_index()[candidate_id]["painting_id"]
    for chunk in table(f"tables/policy/{painting}.csv.gz", chunksize=50000, keep_default_na=False):
        selected.extend(rows(chunk[chunk.candidate_id.eq(candidate_id)]))
    return selected


def payload(package, candidate_id=OPENING):
    package.load_room("trustworthiness")
    index = candidate_index()
    if candidate_id not in index:
        raise ValueError("Exact candidate ID is not in this recorded release; nothing substituted")
    candidate = index[candidate_id]
    assignments = assignment_records(candidate_id)
    categories = assignments["categories"]
    frame = pd.read_parquet(package.verify_relative_file("data/derived/threshold_strata.parquet"))
    thresholds = {r["category_id"]: {i: threshold_record(r, i, frame) for i in r["indicator_states"]}
                  for r in categories}
    peers = []
    for model in MAIN_MODELS:
        peer = catalogue()["models"][model].get(candidate["case_id"])
        if peer:
            peer = index[peer["candidate_id"]]
        if peer and peer["experiment_id"] == candidate["experiment_id"]:
            peers.append({"model": LABELS[model], "candidate_id": peer["candidate_id"],
                          "case_id": peer["case_id"], "experiment_id": peer["experiment_id"],
                          "seed": peer.get("seed"), "prompt_variant_id": peer.get("prompt_variant_id")})
    source = catalogue()["cases"].get(candidate["case_id"])
    if source is None:
        raise ValueError("Selected candidate has no registered input case")
    flags = assignments["flags"]
    actions = {r["recommended_action"] for r in flags}
    if len(actions) != 1:
        raise ValueError("Recorded recommendation is inconsistent across flag rows")
    catalogue_rows = [{k: r.get(k) for k in (*IDENTITY, "category", "seed")} for r in index.values()]
    return {"candidate": {k: candidate.get(k) for k in (*IDENTITY, "category", "seed")},
            "categories": categories, "thresholds": thresholds, "flags": flags,
            "peers": peers, "catalogue": catalogue_rows, "recommendation": next(iter(actions)),
            "policy": policy_records(candidate_id), "labels": LABELS, "boundary": BOUNDARY,
            "images": {"Clean": image_uri(str(project_path(source["clean_image_path"]))),
                       "Damaged": image_uri(str(project_path(source["input_image_path"])), source["input_sha256"]),
                       "Restored": image_uri(candidate["resolved_path"], candidate["restored_sha256"])},
            "content_bbox": painting_geometry()[candidate["painting_id"]],
            "version": "trust-v1:" + candidate_id,
            "source": N27, "population": {"primary": 10504, "full_method_primary": 10480,
            "bounded_sdxl": 24, "seed_memberships": 4100, "seed_groups": 1025, "overlap": 725,
            "uncertainty_only": 3375, "union": len(index), "categories": 14, "flag_types": 11,
            "category_rows": 194306, "flag_rows": 152669, "threshold_strata": 137}}
