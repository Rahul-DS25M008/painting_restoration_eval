"""Read-only, post-N35 numerical inspection of fixed validated metric artifacts.

No metrics are calculated here. N34 remains the approved candidate allow-list;
producer CSVs supply original values. All joins retain case/candidate/model IDs.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from .manifests import sha256_file
from .paths import resolve_repo_path


METRIC_SOURCES = {
    "Classical metrics": ("13_classical_metrics", "metrics/classical_metrics.csv", "metric_row_id"),
    "LPIPS": ("14_lpips_metrics", "metrics/lpips_metrics.csv", "metric_row_id"),
    "Feature similarity": ("15_feature_similarity", "metrics/feature_metrics.csv", "metric_row_id"),
    "Colour, seam & texture": ("17_local_consistency_metrics", "metrics/local_consistency.csv", "local_consistency_id"),
    "Semantic & structural": ("20_semantic_and_structural_consistency", "metrics/semantic_structural_metrics.csv", "semantic_metric_id"),
}
CANDIDATE_SOURCES = (
    "outputs/11_stable_diffusion_restoration/data/candidates.csv",
    "outputs/12_sdxl_feasibility_or_restoration/data/candidates.csv",
    "outputs/22_damage_size_diffusion_uncertainty_extension/data/candidates.csv",
)
IDENTITY = ["candidate_id", "case_id", "model_id"]
VALUE_COLUMNS = ["damaged_value", "restored_value", "improvement_value"]
DETAIL_COLUMNS = [
    "metric_family", "evidence_family", "metric_name", "region_id",
    "improvement_direction", "value_unit", "feature_model_id",
    "evidence_component", "summary_statistic", "semantic_target_scope",
    "applicability_status", "metric_version", "region_policy_version", "status", "issue",
]


def metric_source_path(source: str) -> str:
    notebook, relative, _ = METRIC_SOURCES[source]
    return f"outputs/{notebook}/{relative}"


def source_signature(root: str | Path, relative: str) -> tuple:
    path = resolve_repo_path(relative, root, must_exist=True)
    manifest = path.parents[1] / "manifests" / "artifacts.csv"
    return (str(path), path.stat().st_size, path.stat().st_mtime_ns,
            str(manifest), manifest.stat().st_size, manifest.stat().st_mtime_ns)


@lru_cache(maxsize=16)
def _verify_source(signature: tuple) -> None:
    path = Path(signature[0])
    manifest = pd.read_csv(signature[3], dtype=str, keep_default_na=False)
    relative = f"outputs/{path.parents[1].name}/{path.parent.name}/{path.name}"
    row = manifest[manifest["relative_path"].eq(relative)]
    if len(row) != 1 or row.iloc[0]["validation_status"] not in {"passed", "warning"}:
        raise ValueError(f"No unique validated artifact record for {relative}")
    if sha256_file(path) != row.iloc[0]["checksum"]:
        raise ValueError(f"Checksum mismatch for {relative}; numerical display stopped.")


def load_case_metric_rows(root: str | Path, case_id: str, source: str) -> pd.DataFrame:
    """Read bounded chunks, retaining only one case; no full-table cache."""
    relative = metric_source_path(source)
    signature = source_signature(root, relative)
    _verify_source(signature)
    row_id = METRIC_SOURCES[source][2]
    header = pd.read_csv(signature[0], nrows=0).columns.tolist()
    required = [*IDENTITY, *VALUE_COLUMNS, "metric_name", "region_id",
                "improvement_direction", "status", row_id]
    if missing := sorted(set(required) - set(header)):
        raise ValueError(f"Missing metric columns in {relative}: {missing}")
    columns = [c for c in dict.fromkeys([*required, *DETAIL_COLUMNS]) if c in header]
    selected = []
    for chunk in pd.read_csv(signature[0], usecols=columns, dtype=str,
                             keep_default_na=False, chunksize=10000):
        selected.append(chunk.loc[chunk["case_id"].eq(case_id)].copy())
    frame = pd.concat(selected, ignore_index=True) if selected else pd.DataFrame(columns=columns)
    if frame[row_id].duplicated().any():
        raise ValueError(f"Duplicate metric record IDs in {relative}")
    frame = frame.rename(columns={row_id: "source_record_id"})
    for col in VALUE_COLUMNS:
        frame[col] = pd.to_numeric(frame[col], errors="raise")
    if "metric_family" not in frame:
        frame["metric_family"] = frame["evidence_family"]
    frame["better_direction"] = frame["improvement_direction"].map({
        "damaged_minus_restored": "Lower is better",
        "restored_minus_damaged": "Higher is better",
    }).fillna("See metric definition")
    # Producers sometimes retain a diagnostic value even when applicability
    # fails (e.g. hue shift in low-chroma regions). Never imply it can be ranked.
    unavailable = frame["status"].ne("ok")
    if "applicability_status" in frame:
        unavailable |= frame["applicability_status"].str.startswith("not_applicable")
    frame.loc[unavailable, "better_direction"] = "Not applicable — do not rank"
    if "value_unit" not in frame:
        frame["value_unit"] = frame["metric_name"].map({
            "mse": "squared RGB levels (0–255)", "mae": "RGB levels (0–255)",
            "psnr": "dB", "ssim": "unitless", "lpips": "LPIPS distance",
            "clip_cosine_similarity": "cosine similarity",
            "dinov2_cosine_similarity": "cosine similarity",
        }).fillna("See metric definition")
    frame["source_path"] = relative
    return frame


def candidate_seed_metadata(root: str | Path, case_id: str) -> pd.DataFrame:
    records = []
    for relative in CANDIDATE_SOURCES:
        signature = source_signature(root, relative)
        _verify_source(signature)
        frame = pd.read_csv(signature[0], dtype=str, keep_default_na=False,
                            usecols=[*IDENTITY, "seed", "prompt_variant_id"])
        records.append(frame.loc[frame["case_id"].eq(case_id)])
    result = pd.concat(records, ignore_index=True)
    if result["candidate_id"].duplicated().any():
        raise ValueError("Candidate IDs are not unique across the seed manifests.")
    return result


def attach_candidate_identity(metrics: pd.DataFrame, catalog: pd.DataFrame,
                              seeds: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Use the N34 allow-list; do not pool seeds or infer an anchor's values."""
    columns = [*IDENTITY, "painting_id", "experiment_id", "prompt_variant_id"]
    candidates = catalog[columns].copy()
    if candidates["candidate_id"].duplicated().any():
        raise ValueError("The approved candidate catalog contains duplicate IDs.")
    joined = candidates.merge(seeds, on=IDENTITY, how="left", validate="one_to_one",
                              suffixes=("", "_source"))
    diffusion = joined["model_id"].isin(["stable_diffusion_inpainting", "sdxl_inpainting"])
    if joined.loc[diffusion, "seed"].isna().any():
        raise ValueError("A diffusion candidate lacks exact seed provenance.")
    if not joined.loc[diffusion, "prompt_variant_id"].fillna("").eq(
        joined.loc[diffusion, "prompt_variant_id_source"].fillna("")
    ).all():
        raise ValueError("Prompt identity disagrees with the producing candidate table.")
    joined["seed"] = joined["seed"].fillna("Not applicable")
    joined = joined.drop(columns="prompt_variant_id_source")
    values = metrics.merge(joined, on=IDENTITY, how="inner", validate="many_to_one")
    missing = joined.loc[~joined["candidate_id"].isin(values["candidate_id"])].copy()
    return values, missing


def aggregate_metric_records(frame: pd.DataFrame) -> pd.DataFrame:
    """Expose stored estimates, intervals, denominators and provenance unchanged."""
    columns = ["analysis_scope", "scope_value", "model_id", "metric_name", "region_id",
               "summary_statistic", "estimate", "interval_low", "interval_high",
               "comparison_direction", "rank", "case_count", "painting_count",
               "coverage_fraction", "population_id", "applicability_status",
               "source_paths_json"]
    return frame[[c for c in columns if c in frame]].copy()
