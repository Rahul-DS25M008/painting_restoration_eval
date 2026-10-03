"""Build the bounded 2026-10-03 correction overlay; never overwrite frozen outputs.

Run with PYTHONPATH=src. Reads saved evidence only; no model execution, downloads,
or modification of N26/N33/N36, their manifests, or the Zenodo archive.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import yaml
from scipy.stats import friedmanchisquare

from restoration_eval.final_evaluation_report import (
    build_final_latex_tables, load_final_evaluation_config, quality_population_metadata,
    SDXL_COMPLETION_NOTE,
)

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/errata/2026-10-03"
N21 = "outputs/21_multi_model_comparison"
N26 = "outputs/26_grouped_and_statistical_analysis"
N33 = "outputs/33_final_evaluation_report"
MODELS = ["opencv_telea", "lama", "hint_places2", "stable_diffusion_inpainting"]
SDXL_TEXT = SDXL_COMPLETION_NOTE


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def correct_tables(thesis, comparison, disagreement, statistics):
    """Correct reporting metadata only; retain source identities in a change ledger."""
    corrected = thesis.copy(deep=True)
    ledger = []
    overall = comparison.loc[
        comparison.population_id.eq("core_three_model")
        & comparison.analysis_scope.eq("overall") & comparison.scope_value.eq("all")
        & comparison.anchor_id.notna()
    ].set_index("comparison_row_id", verify_integrity=True)
    disagreements = disagreement.set_index("disagreement_row_id", verify_integrity=True)
    assert len(overall) == 44
    for idx, row in thesis.iterrows():
        table = row.table_id
        values = json.loads(row.values_json)
        sources = json.loads(row.source_row_ids_json)
        issue = None
        if table in {"t04_quality_anchor_summary", "t05_metric_disagreement"}:
            issue = "E01"
            if table.startswith("t04"):
                source = overall.loc[sources[0]]
                cases, paintings = int(source.paired_case_count), int(source.paired_painting_count)
                values["eligible_case_count"] = cases
            else:
                source = disagreements.loc[sources[0]]
                cases, paintings = int(source.eligible_case_count), int(source.eligible_painting_count)
            population = quality_population_metadata(str(source.anchor_id), cases, paintings, 2620)
            assert cases == (2620 if population["values"]["controls_included"] else 2320)
            assert paintings == 300
            values.update(population["values"])
            corrected.at[idx, "scope"] = population["scope"]
            corrected.at[idx, "denominator"] = population["denominator"]
            corrected.at[idx, "independent_unit"] = "case (descriptive mean; clustered by painting)"
        elif table == "t10_grouped_statistics":
            issue = "E02"
            omnibus = row.row_key.startswith("omnibus__")
            values.update(n_cases=1200 if omnibus else 2320, controls_included=False)
            if omnibus:
                values["aggregation_rule"] = "median_over_four_canonical_damage_cases_per_painting_and_model"
                corrected.at[idx, "scope"] = "canonical_nonzero_core"
                corrected.at[idx, "denominator"] = "1200 canonical nonzero cases; 300 equally weighted painting blocks; four cases per painting/model"
            else:
                values["aggregation_rule"] = "separate_quality_and_runtime_medians_over_all_nonzero_cases_per_painting_and_model"
                corrected.at[idx, "denominator"] = "2320 nonzero cases across four experiment branches; 300 equally weighted paintings per model; within-painting medians"
        elif table == "t15_limitations" and "sdxl_bounded_35" in row.values_json:
            issue = "E03"
            values["limitation_id"] = "sdxl_scheduled_35_cases_across_30_paintings_completed_24_across_19_one_timeout_ten_not_started"
            corrected.at[idx, "row_label"] = SDXL_TEXT
            corrected.at[idx, "source_row_ids_json"] = json.dumps([values["limitation_id"]])
        if issue:
            corrected.at[idx, "values_json"] = json.dumps(values, sort_keys=True)
            corrected.at[idx, "table_row_id"] = "errata_20261003__" + row.table_row_id
            for field in thesis.columns:
                old, new = row[field], corrected.at[idx, field]
                if pd.isna(old) and pd.isna(new):
                    continue
                if str(old) != str(new):
                    ledger.append(dict(erratum=issue, source_path=f"{N33}/data/thesis_tables.csv",
                                       original_row_id=row.table_row_id, corrected_row_id=corrected.at[idx, "table_row_id"],
                                       field=field, before=str(old), after=str(new)))
    changed = statistics.loc[statistics.result_kind.isin(["repeated_model_test", "paired_model_contrast"])].copy()
    assert changed.result_kind.value_counts().to_dict() == {"paired_model_contrast": 66, "repeated_model_test": 11}
    assert changed.scope_value.eq("canonical_nonzero_balanced_300").all()
    for idx, row in changed.iterrows():
        updates = dict(experiment_id="canonical_missing_region", population_id="canonical_nonzero_core",
                       n_cases=1200, result_id="errata_20261003__" + row.result_id)
        for field, value in updates.items():
            changed.at[idx, field] = value
            ledger.append(dict(erratum="E02", source_path=f"{N26}/metrics/statistical_results.csv",
                               original_row_id=row.result_id, corrected_row_id=updates["result_id"],
                               field=field, before=str(row[field]), after=str(value)))
    return corrected, changed, pd.DataFrame(ledger)


def saved_anchors(root, source_hashes):
    """Independent narrow extraction of the eleven saved scalars, not metric recomputation."""
    config = yaml.safe_load((root / "config/evaluation/grouped_statistical_analysis.yaml").read_text())
    settings = config["grouped_statistical_analysis"]
    sd_path = root / settings["inputs"]["stable_diffusion_candidates_path"]
    sd = pd.read_csv(sd_path, low_memory=False)
    sd_ids = set(sd.loc[sd.execution_role.eq("primary") & sd.prompt_variant_id.eq("p00_generic")
                        & sd.seed.eq(2026) & sd.status.eq("completed"), "candidate_id"])
    source_hashes[sd_path.relative_to(root).as_posix()] = digest(sd_path)
    families = {
        "classical_metrics_path": ["classical_masked_mae", "structural_crop_ssim"],
        "lpips_metrics_path": ["perceptual_crop_lpips"],
        "feature_metrics_path": ["feature_clip_crop", "feature_dino_crop"],
        "spatial_metrics_path": ["spatial_masked_error"],
        "local_metrics_path": ["texture_crop_p95", "colour_masked_delta_e", "seam_boundary_gradient"],
        "semantic_metrics_path": ["semantic_local_dino", "structural_affinity_correlation"],
    }
    specs = {a["anchor_id"]: a for a in settings["quality_anchors"]}
    parts = []
    for key, anchor_ids in families.items():
        path = root / settings["inputs"][key]
        print(f"Checking saved anchors: {path.name}", flush=True)
        source_hashes[path.relative_to(root).as_posix()] = digest(path)
        for chunk in pd.read_csv(path, chunksize=100000, low_memory=False):
            admitted = chunk.model_id.isin(MODELS) & chunk.status.isin(["ok", "passed"])
            admitted &= ~chunk.model_id.eq("stable_diffusion_inpainting") | chunk.candidate_id.isin(sd_ids)
            chunk = chunk.loc[admitted]
            for anchor in anchor_ids:
                spec = specs[anchor]
                mask = chunk.region_id.eq(spec["region_id"])
                for field in ["metric_name", "feature_model_id", "summary_statistic"]:
                    if field in spec and field in chunk:
                        mask &= chunk[field].eq(spec[field])
                sub = chunk.loc[mask].copy()
                id_column = next(c for c in ["metric_row_id", "spatial_diagnostic_id", "local_consistency_id", "semantic_metric_id"] if c in sub)
                value_column = "restored_error_mean" if key == "spatial_metrics_path" else "restored_value"
                sub = sub[["case_id", "candidate_id", "model_id", id_column, value_column]].rename(columns={id_column: "source_row_id", value_column: "value"})
                sub["anchor_id"] = anchor
                sub["source_path"] = path.relative_to(root).as_posix()
                parts.append(sub)
    anchors = pd.concat(parts, ignore_index=True)
    anchors["painting_id"] = anchors.case_id.str.extract(r"(?:^|__)(p\d+)(?:__|$)", expand=False)
    if anchors.duplicated(["candidate_id", "anchor_id"]).any():
        raise ValueError("Anchor extraction produced duplicate candidate/anchor rows")
    return anchors


def verify_statistics(anchors, statistics):
    canonical = anchors.loc[anchors.case_id.str.match(r"^canonical__p\d+__(loss_large|loss_small|mixed_damage|scratch_thin)$")]
    checks = []
    config = yaml.safe_load((ROOT / "config/evaluation/grouped_statistical_analysis.yaml").read_text())
    specs = {a["anchor_id"]: a for a in config["grouped_statistical_analysis"]["quality_anchors"]}
    for anchor, group in canonical.groupby("anchor_id"):
        assert group.case_id.nunique() == 1200
        assert group.groupby(["painting_id", "model_id"]).size().eq(4).all()
        pivot = group.groupby(["painting_id", "model_id"]).value.median().unstack("model_id")[MODELS]
        assert pivot.shape == (300, 4) and pivot.notna().all().all()
        stat, p = friedmanchisquare(*(pivot[m].to_numpy() for m in MODELS))
        spec = specs[anchor]
        saved = statistics.loc[statistics.result_kind.eq("repeated_model_test")
                               & statistics.metric_name.eq(spec["metric_name"])
                               & statistics.region_id.eq(spec["region_id"])]
        assert len(saved) == 1, (anchor, len(saved))
        row = saved.iloc[0]
        w = stat / (300 * 3)
        assert np.isclose(stat, row.test_statistic, rtol=1e-10, atol=1e-10)
        assert np.isclose(w, row.effect_size, rtol=1e-10, atol=1e-10)
        assert np.isclose(p, row.p_value, rtol=1e-8, atol=0)
        checks.append(dict(anchor_id=anchor, source_result_id=row.result_id, n_cases=1200,
                           n_paintings=300, cases_per_painting_model=4,
                           friedman_statistic=float(stat), kendalls_w=float(w),
                           p_value=float(p), saved_q_value=float(row.q_value), matches_saved=True))
    assert len(checks) == 11
    return checks


def evidence_examples(anchors, root, source_hashes):
    # Restrict the illustrative case search to the balanced canonical experiment.
    selected = anchors.loc[anchors.case_id.str.match(r"^canonical__p\d+__(loss_large|loss_small|mixed_damage|scratch_thin)$")]
    pivot = selected.pivot(index=["case_id", "candidate_id", "model_id"], columns="anchor_id", values="value").reset_index()
    pivot["ssim_rank"] = pivot.groupby("case_id").structural_crop_ssim.rank(ascending=False, method="min")
    pivot["lpips_rank"] = pivot.groupby("case_id").perceptual_crop_lpips.rank(ascending=True, method="min")
    # First lexicographic case/candidate satisfying the declared conditions. No handpicked extrema.
    hidden = pivot.loc[pivot.ssim_rank.eq(1) & pivot.lpips_rank.eq(4) & pivot.structural_crop_ssim.ge(.9)].sort_values(["case_id", "candidate_id"])
    agreement = pivot.loc[pivot.ssim_rank.eq(1) & pivot.lpips_rank.eq(1)].sort_values(["case_id", "candidate_id"])
    assert not hidden.empty and not agreement.empty
    result = {}
    for label, pool in [("structural_perceptual_disagreement", hidden), ("unchanged_winner", agreement)]:
        row = pool.iloc[0]
        peers = pivot.loc[pivot.case_id.eq(row.case_id)]
        ids = set(peers.candidate_id)
        evidence = selected.loc[selected.candidate_id.isin(ids) & selected.anchor_id.isin(["structural_crop_ssim", "perceptual_crop_lpips", "colour_masked_delta_e", "classical_masked_mae"])]
        result[label] = dict(case_id=row.case_id, candidate_id=row.candidate_id, model_id=row.model_id,
                             qualifying_candidates=len(pool),
                             selection_rule=("first case_id/candidate_id in lexicographic order with crop SSIM >= 0.9 and SSIM rank 1 but LPIPS rank 4" if label.startswith("structural") else "first case_id/candidate_id in lexicographic order with SSIM rank 1 and LPIPS rank 1"),
                             candidate_comparison=peers[["candidate_id", "model_id", "structural_crop_ssim", "perceptual_crop_lpips", "classical_masked_mae", "colour_masked_delta_e"]].to_dict("records"),
                             source_rows=evidence[["source_path", "source_row_id", "candidate_id", "anchor_id", "value"]].to_dict("records"))
    path = root / "outputs/28_metric_and_region_policy_ablation/metrics/ablation_results.csv"
    ablation = pd.read_csv(path, low_memory=False)
    source_hashes[path.relative_to(root).as_posix()] = digest(path)
    summaries = ablation.loc[ablation.result_kind.eq("scenario_summary") & ablation.scenario_id.isin(["complete_approved_framework", "only_classical"])]
    assert len(summaries) == 2
    result["aggregate_ablation"] = summaries[["result_id", "scenario_id", "baseline_winner_id", "scenario_winner_id", "available_family_count", "available_anchor_count", "n_cases", "n_paintings"]].to_dict("records")
    return result


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    source_hashes = {}
    def read(relative):
        path = ROOT / relative
        source_hashes[relative] = digest(path)
        return pd.read_csv(path, low_memory=False, float_precision="round_trip")
    thesis = read(f"{N33}/data/thesis_tables.csv")
    comparison = read(f"{N21}/metrics/model_comparison.csv")
    disagreement = read(f"{N21}/metrics/metric_disagreement.csv")
    statistics = read(f"{N26}/metrics/statistical_results.csv")
    corrected, stats, ledger = correct_tables(thesis, comparison, disagreement, statistics)
    affected = corrected.loc[corrected.table_row_id.str.startswith("errata_20261003__")]
    assert len(affected) == 78
    latex = build_final_latex_tables(corrected, load_final_evaluation_config(ROOT / "config/evaluation/final_evaluation_report.yaml"))
    latex = latex.loc[latex.table_id.isin(affected.table_id)]
    # Numerical fields must remain identical for every corrected statistical row.
    numeric = ["estimate", "ci_lower", "ci_upper", "effect_size", "test_statistic", "p_value", "q_value"]
    pd.testing.assert_frame_equal(stats[numeric], statistics.loc[stats.index, numeric])
    for idx, row in affected.iterrows():
        old, new = json.loads(thesis.at[idx, "values_json"]), json.loads(row.values_json)
        for key, value in old.items():
            if key not in {"eligible_case_count", "limitation_id"}:
                assert new[key] == value, (row.table_row_id, key)
    anchors = saved_anchors(ROOT, source_hashes)
    statistical_checks = verify_statistics(anchors, statistics)
    examples = evidence_examples(anchors, ROOT, source_hashes)
    sdxl = read("outputs/12_sdxl_feasibility_or_restoration/data/candidates.csv")
    complete = sdxl.loc[sdxl.status.eq("completed")]
    assert len(sdxl) == 35 and sdxl.painting_id.nunique() == 30
    assert len(complete) == 24 and complete.painting_id.nunique() == 19
    assert complete.technical_validation_passed.astype(str).str.lower().eq("true").all()
    assert sdxl.status.value_counts().to_dict() == {"completed": 24, "skipped": 10, "timed_out": 1}
    for filename, frame in [("corrected_thesis_rows.csv", affected), ("corrected_latex_tables.csv", latex),
                            ("corrected_statistical_rows.csv", stats), ("correction_ledger.csv", ledger)]:
        frame.to_csv(DEST / filename, index=False, lineterminator="\n")
    for filename, payload in [("statistical_verification.json", statistical_checks), ("framework_examples.json", examples)]:
        (DEST / filename).write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    for relative, checksum in source_hashes.items():
        assert digest(ROOT / relative) == checksum, f"Input changed: {relative}"
    outputs = {p.name: digest(p) for p in DEST.iterdir() if p.suffix in {".csv", ".json"} and p.name != "verification.json"}
    receipt = dict(correction_version="2026-10-03.v1", corrected_thesis_rows=78, corrected_statistical_rows=77,
                   corrected_latex_tables=4, unchanged_scientific_numbers=True, matched_friedman_tests=11,
                   original_inputs_unchanged=True, scientific_model_runs=0, source_sha256=source_hashes, output_sha256=outputs)
    (DEST / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in receipt.items() if not k.endswith("sha256")}, indent=2))


if __name__ == "__main__":
    main()
