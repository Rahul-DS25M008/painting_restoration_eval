"""Prepare complete N35 cells 28–48; never edit or execute the notebook."""
import ast
import hashlib
import json
from pathlib import Path
from textwrap import dedent

from prepare_n35_batch2_cells import render

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/35_dashboard_and_deployment_validation.ipynb"
DEST = ROOT / ".codex_tmp/n35_batches_6_9"

SETUP = r'''
# Continue in the kernel that successfully completed the replacement Batch 5.
import importlib
import re
from collections import Counter
n35 = importlib.reload(n35)
n35.required_stages(VALIDATION.checks, ["batch_5_final_gate"])
drop_validation_stages(tuple(f"batch_{i}_" for i in range(6, 11)))
VALIDATION.raise_for_blocking()
start_room_batch(6)

def room_binding_checks(room_id, display_count, binding_count):
    room = PACKAGE.load_room(room_id)
    bindings = PACKAGE.bindings_for(room_id=room_id)
    return [
        room_check(room_id + "__display_rows", display_count, len(room)),
        room_check(room_id + "__distinct_displays", display_count, room.display_id.nunique()),
        room_check(room_id + "__binding_rows", binding_count, len(bindings)),
        room_check(room_id + "__unique_slots", binding_count, bindings.slot_id.nunique()),
        room_check(room_id + "__display_coverage", set(room.display_id), set(bindings.display_id)),
    ]

def freeze_checks(name):
    rows = n35.verify_later_room_freeze(PROJECT_ROOT, name)
    expected_count = {"stability_lab": 23, "trustworthiness": 27,
                      "focused_portrait": 24, "research_archive": 52}[name]
    return [room_check(name + "__freeze_count", expected_count, len(rows))] + [
        room_check(name + "__" + row["path"], row["expected"], row["observed"])
        for row in rows]

def js_checks(paths):
    result = n35.node_checks(PROJECT_ROOT, paths)
    for row in result:
        print(row["path"], row["stdout"], row["stderr"])
    return [room_check("javascript__" + row["path"], True, row["passed"]) for row in result]

def nested_value(data, path):
    for key in path.split("."):
        data = data[key]
    return data

def render_cases(cases):
    """Fresh Python renders with exact controller JSON, not browser-JS execution."""
    result = []
    for spec in cases:
        print("Server render:", spec["name"], flush=True)
        smoke = n35.room_smoke(APP_PATH, spec["query"], timeout=180)
        app = smoke["app"]
        if "error" in spec:
            observed = dict(network=smoke["network_attempts"], exceptions=len(app.exception),
                visible_rejection=any(spec["error"] in text for text in smoke["errors"]),
                substituted_scene=bool(re.search(r'<main\b[^>]*class="' + spec["scene"] + r'"', smoke["html"])))
            expected = dict(network=[], exceptions=0, visible_rejection=True, substituted_scene=False)
        else:
            data = n35.controller_payload(app)
            observed = dict(network=smoke["network_attempts"], errors=smoke["errors"],
                scene=bool(re.search(r'<main\b[^>]*class="' + spec["scene"] + r'"', smoke["html"])),
                identity={key: nested_value(data, key) for key in spec["expect"]})
            expected = dict(network=[], errors=[], scene=True, identity=spec["expect"])
        result.append(room_check(spec["name"], expected, observed))
    return result

# Correct the earlier 1:1 assumption: child asset/map slots are separate bindings.
# Recheck against the immutable N34 package, not just the edited notebook numbers.
with n35.offline() as binding_network:
    corrected_bindings = room_binding_checks("metric_framework", 12, 21)
    corrected_bindings += room_binding_checks("model_gallery", 12, 19)
record_room_stage("batch_6_prior_binding_recheck", corrected_bindings + [
    room_check("outbound_network_attempts", [], binding_network)])

shared_freeze = n35.verify_freeze(PROJECT_ROOT, "config/publication/museum_visit_freeze.json")
record_room_stage("batch_6_source_contract", freeze_checks("stability_lab") + [
    room_check("shared_approved__" + r["path"], r["expected"], r["observed"])
    for r in shared_freeze] + room_binding_checks("stability_lab", 8, 19) + [test_record("stability")])
'''

STABILITY_DATA = r'''
from restoration_eval import stability_lab as LAB
with n35.offline() as attempts:
    cat = LAB.test_catalogue()
    groups = LAB.seed_catalogue()
    LAB_OPENING = LAB.payload({})
    LAB_SEED = LAB.payload({"stability_test": "seed", "stability_model": LAB.SD})
    p05 = next(g for g in LAB.seed_options("p018") if g["prompt"] == "p05_scratch_aware")
    p05_payload = LAB.payload({"stability_test": "seed", "stability_model": LAB.SD,
                              "stability_group": p05["id"]})
    LAB_SEED_QUERIES = {"default": LAB_SEED["seed"]["id"], "p05": p05["id"]}
    invalid_rejected = False
    try:
        LAB.selection({"stability_test": "seed", "stability_model": "lama"})
    except ValueError:
        invalid_rejected = True
record_room_stage("batch_6_saved_evidence", [
    room_check("focused_populations", (35, 245, 525, 1155, 350),
        (len(cat["paintings"]), len(cat["size"]), len(cat["mask"]), len(cat["degradation"]),
         sum(r["degradation_family"] in LAB.FAMILIES for r in cat["degradation"]))),
    room_check("seed_population", (1025, 6150),
        (len(groups), sum(len(g["pairs"]) for g in groups.values()))),
    room_check("four_seeds_per_group", True,
        all(set(g["members"]) == {2026, 2027, 2028, 2029} and len(g["pairs"]) == 6 for g in groups.values())),
    room_check("opening_identity", ("p018", "lama", "size", "damage_size__p018__loss_large__size_20pct"),
        tuple(LAB_OPENING[k] for k in ("painting", "model", "test", "selected"))),
    room_check("deterministic_seed_panel_is_unavailable", None, LAB_OPENING["seed"]),
    room_check("seed_group_identity", "ug_1de955f7e0f3d00cf0", LAB_SEED["seed"]["id"]),
    room_check("p05_candidate_not_p00", p05["members"][2026], p05_payload["current"]["candidate_id"]),
    room_check("p05_missing_overlay_not_substituted", None, p05_payload["seed"]["overlay"]),
    room_check("invalid_deterministic_seed_rejected", True, invalid_rejected),
    room_check("outbound_network_attempts", [], attempts),
])
display(pd.DataFrame([{k: p[k] for k in ("case_id", "label", "candidate_id")} | {"saved_metric": p["metric"]}
                      for p in LAB_OPENING["points"]]))
'''

STABILITY_SMOKE = r'''
STABILITY_RENDER_CASES = [
    dict(name="size_opening", query={"room": "stability_lab"}, scene="stability-stage",
         expect={"painting": "p018", "test": "size", "model": "lama", "selected": "damage_size__p018__loss_large__size_20pct", "seed": None}),
    dict(name="mask_branch", query={"room": "stability_lab", "stability_test": "mask"}, scene="stability-stage",
         expect={"test": "mask", "condition": "loss_large", "selected": "mask_robustness__p018__loss_large__target_12p5pct__variant_01"}),
    dict(name="degradation_branch", query={"room": "stability_lab", "stability_test": "degradation"}, scene="stability-stage",
         expect={"test": "degradation", "family": "dirt_dust", "selected": "synthetic_degradation__p018__dirt_dust__mild"}),
    dict(name="exact_seed_branch", query={"room": "stability_lab", "stability_test": "seed", "stability_model": LAB.SD}, scene="stability-stage",
         expect={"test": "seed", "seed.id": LAB_SEED_QUERIES["default"]}),
    dict(name="wrong_seed_method_rejected", query={"room": "stability_lab", "stability_test": "seed"}, scene="stability-stage",
         error="explicit switch to Stable Diffusion"),
]
record_room_stage("batch_6_server_smoke", render_cases(STABILITY_RENDER_CASES))
'''

TRUST_SOURCE = r'''
start_room_batch(7)
record_room_stage("batch_7_source_contract",
    freeze_checks("trustworthiness") + freeze_checks("focused_portrait")
    + room_binding_checks("trustworthiness", 7, 14)
    + room_binding_checks("focused_portrait_review", 10, 19)
    + [test_record("trust_portrait")]
    + js_checks(["tests/test_trustworthiness_chart.cjs", "tests/test_focused_portrait_chart.cjs"]))
'''

TRUST_DATA = r'''
from restoration_eval import trustworthiness as TRUST
from restoration_eval import focused_portrait as PORTRAIT
with n35.offline() as attempts:
    TRUST_OPENING = TRUST.payload(PACKAGE)
    PORTRAIT_OPENING = PORTRAIT.payload(PACKAGE)
    PORTRAIT_COUNTER = PORTRAIT.payload(PACKAGE, "R003")
    roles = Counter(r["population_role"] for r in TRUST.candidate_index().values())
    threshold = TRUST_OPENING["thresholds"]["texture_smoothing"]["local_texture_error_p95"]
    registered_returns = [PORTRAIT.return_room(p) for p in ("study_design", "trustworthiness", "case_explorer")]
record_room_stage("batch_7_saved_evidence", [
    room_check("candidate_union_roles", {"primary_and_uncertainty": 725, "uncertainty_only": 3375,
        "bounded_sdxl": 24, "primary_comparison": 9755}, dict(roles)),
    room_check("trust_exact_opening", ("sd15__p00__s2026__29ff258ff921", "canonical__p002__loss_large", 2026, "p00_generic"),
        tuple(TRUST_OPENING["candidate"][k] for k in ("candidate_id", "case_id", "seed", "prompt_variant_id"))),
    room_check("category_flag_policy_counts", (14, 11, 23, 4),
        tuple(len(TRUST_OPENING[k]) for k in ("categories", "flags", "policy", "peers"))),
    room_check("saved_threshold", (10.053275680541985, 1.7923734879493693, 4.8924025321006255, "critical"),
        tuple(threshold[k] for k in ("observed", "warning", "critical", "state"))),
    room_check("d02_review_identity", ("R005", "candidate__hint_places2__canonical__p269__mixed_damage__c00"),
        tuple(PORTRAIT_OPENING["review"][k] for k in ("blind_review_code", "candidate_id"))),
    room_check("d02_scope", (60, 45, 20, 32, 8, 25),
        tuple(PORTRAIT_OPENING["scope"][k] for k in ("screened", "hand_cases", "hand_paintings", "reviews", "review_cases", "visible_failures"))),
    room_check("matched_equal_disjoint_pixels", (1196, 1196, 0),
        (len(PORTRAIT_OPENING["hand_indices"]), len(PORTRAIT_OPENING["control_indices"]),
         len(set(PORTRAIT_OPENING["hand_indices"]) & set(PORTRAIT_OPENING["control_indices"])))),
    room_check("counterexample_is_not_failure", False, PORTRAIT_COUNTER["review"]["overall_anatomy_failure"]),
    room_check("counterexample_has_no_r005_asset_substitution", {}, PORTRAIT_COUNTER["registered"]),
    room_check("one_child_three_return_routes", ["study_design", "trustworthiness", "case_explorer"], registered_returns),
    room_check("outbound_network_attempts", [], attempts),
])
display(pd.DataFrame([TRUST_OPENING["candidate"], PORTRAIT_OPENING["review"]])[
    ["painting_id", "candidate_id", "case_id", "model_id"]])
'''

TRUST_SMOKE = r'''
TRUST_RENDER_CASES = [
    dict(name="trust_exact_opening", query={"room": "trustworthiness"}, scene="trust-stage",
         expect={"candidate.candidate_id": TRUST.OPENING, "candidate.seed": 2026}),
    dict(name="trust_invalid_candidate", query={"room": "trustworthiness", "trust_candidate": "not-a-candidate"},
         scene="trust-stage", error="nothing substituted"),
    *[dict(name="r005_return_" + parent,
         query={"room": "focused_portrait_review", "portrait_review": "R005", "return_room": parent},
         scene="fpr-stage", expect={"review.blind_review_code": "R005", "return_room": parent,
                                    "review.candidate_id": "candidate__hint_places2__canonical__p269__mixed_damage__c00"})
      for parent in ("study_design", "trustworthiness", "case_explorer")],
    dict(name="r003_counterexample", query={"room": "focused_portrait_review", "portrait_review": "R003"},
         scene="fpr-stage", expect={"review.blind_review_code": "R003", "review.overall_anatomy_failure": False, "registered": {}}),
    dict(name="invalid_review", query={"room": "focused_portrait_review", "portrait_review": "R999"},
         scene="fpr-stage", error="blind_review_code"),
]
record_room_stage("batch_7_server_smoke", render_cases(TRUST_RENDER_CASES))
'''

CASE_SOURCE = r'''
start_room_batch(8)
CASE_APPROVED_COMMIT = "e88feea5e0deb6d5e48cb12378d69ff5d63b2e11"
CASE_PINNED_PATHS = [
    "src/restoration_eval/case_explorer.py", "src/restoration_eval/case_explorer_view.py",
    "streamlit_assets/case_explorer.css", "streamlit_assets/case_explorer_controller.js",
    "streamlit_assets/rooms/case_explorer_shell.png", "streamlit_assets/rooms/case_explorer_lettering.png",
    "streamlit_assets/rooms/case_explorer_neutral_layer.png", "streamlit_assets/rooms/case_explorer_title_enhanced.png",
    "tests/test_case_explorer.py", "tests/case_explorer_controller.test.cjs",
    *["streamlit_assets/evidence/case_explorer/" + name for name in
      ("manifest.json", "maps_manifest.json", "inputs_manifest.json", "panels_manifest.json", "choices_manifest.json", "choices.json")],
]
CASE_FREEZE_ROWS = n35.verify_committed_files(PROJECT_ROOT, CASE_APPROVED_COMMIT, CASE_PINNED_PATHS)
# The default-selection API excludes the SD-only uncertainty child binding.
# Raw manifest: 40 rows. LaMa-compatible opening bindings: 39. Neither is 15.
raw_case_bindings = PACKAGE.display_components.loc[PACKAGE.display_components.room_id.eq("case_explorer")]
record_room_stage("batch_8_source_contract", [
    *[room_check("approved__" + r["path"], r["expected"], r["observed"]) for r in CASE_FREEZE_ROWS],
    room_check("raw_registered_binding_count", 40, len(raw_case_bindings)),
] + room_binding_checks("case_explorer", 15, 39) + [test_record("case")]
  + js_checks(["tests/case_explorer_controller.test.cjs", "tests/room_runtime.test.cjs"]))
'''

CASE_DATA = r'''
import csv
import hashlib
from restoration_eval import case_explorer as CASE
with n35.offline() as attempts:
    CASE_OPENING = CASE.payload(PACKAGE)
    CASE_SD = CASE.payload(PACKAGE, "p018", "sd15__p00__s2026__d0cd65cf894a")
    CASE_NA = CASE.payload(PACKAGE, layer="uncertainty")
    metric_manifest = json.loads((CASE.INDEX / "manifest.json").read_text(encoding="utf-8"))
    map_manifest = json.loads((CASE.INDEX / "maps_manifest.json").read_text(encoding="utf-8"))
    source_hashes = {r["sha256"] for r in metric_manifest["sources"]}
    expected_paintings = set(PACKAGE.painting_lookup.painting_id.astype(str))
    shard_audit, all_candidates, registered_candidates = [], set(), {}
    for pid in sorted(expected_paintings):
        # Public loaders verify each compact shard's checksum before decoding.
        rows, maps = CASE.saved_metrics(pid), CASE.saved_maps(pid)
        identities = PACKAGE.load_painting(pid)["candidates"]
        by_id = {r["candidate_id"]: r for r in identities}
        registered_candidates.update(by_id)
        exact = True
        for row in rows:
            c = by_id.get(row["candidate_id"])
            exact &= bool(c) and row["case_id"] == c["case_id"] and row["model_id"] == c["model_id"]
            exact &= row["source_sha256"] in source_hashes
            all_candidates.add(row["candidate_id"])
        keys = [(r["candidate_id"], r["metric_name"]) for r in rows]
        shard_audit.append(dict(painting_id=pid, rows=len(rows), exact_identity=bool(exact),
            unique_keys=len(keys) == len(set(keys)), maps=len(maps),
            expected_rows=metric_manifest["shards"][pid]["rows"]))
    CASE_SHARD_AUDIT = pd.DataFrame(shard_audit)
    # candidate_count is the permitted N34 universe, NOT metric availability.
    # Independently re-read the three checksum-pinned producer selections.
    # This bounded-memory validation scan is not an application runtime loader.
    selected_specs = {
        "outputs/13_classical_metrics/metrics/classical_metrics.csv": ("ssim", "mask_bbox_crop"),
        "outputs/14_lpips_metrics/metrics/lpips_metrics.csv": ("lpips", "mask_bbox_crop"),
        "outputs/17_local_consistency_metrics/metrics/local_consistency.csv": ("delta_e_ciede2000_mean", "masked_region"),
    }
    assert {s["path"] for s in metric_manifest["sources"]} == set(selected_specs)
    source_candidates = set()
    for source in metric_manifest["sources"]:
        path = n35.safe_path(PROJECT_ROOT, source["path"])
        print("Checking saved metric availability:", source["path"], flush=True)
        with path.open("rb") as handle:
            assert hashlib.file_digest(handle, "sha256").hexdigest() == source["sha256"], "Metric source checksum mismatch"
        metric_name, region_id = selected_specs[source["path"]]
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if (row["metric_name"] == metric_name and row["region_id"] == region_id
                        and (metric_name != "lpips" or row.get("network") == "alex")
                        and row["candidate_id"] in registered_candidates):
                    source_candidates.add(row["candidate_id"])
    missing_metric_ids = set(registered_candidates) - all_candidates
    CASE_METRIC_AVAILABILITY = pd.DataFrame([
        {"state": "has a saved display metric", "candidates": len(all_candidates)},
        {"state": "no selected saved metric; not zero", "candidates": len(missing_metric_ids)},
    ])
    saved_retrieval = CASE.retrieval_rows()
    choice_families = {r["family"] for r in CASE.counterfactual_choices()}
record_room_stage("batch_8_saved_evidence", [
    room_check("metric_shards", expected_paintings, set(metric_manifest["shards"])),
    room_check("map_shards", expected_paintings, set(map_manifest["shards"])),
    room_check("registered_candidate_universe", (13879, 13879),
        (metric_manifest["candidate_count"], len(registered_candidates))),
    room_check("saved_metric_population", 11944, len(all_candidates)),
    room_check("exact_source_candidate_coverage", True, source_candidates == all_candidates),
    room_check("unavailable_metric_population_not_zero", 1935, len(missing_metric_ids)),
    room_check("all_exact_candidate_joins", 300, int(CASE_SHARD_AUDIT.exact_identity.sum())),
    room_check("unique_candidate_metric_rows", 300, int(CASE_SHARD_AUDIT.unique_keys.sum())),
    room_check("saved_row_counts", True, bool((CASE_SHARD_AUDIT.rows == CASE_SHARD_AUDIT.expected_rows).all())),
    room_check("opening_candidate", CASE.OPENING, CASE_OPENING["candidate"]["candidate_id"]),
    room_check("exact_sd_seed", 2026, CASE_SD["candidate"]["seed"]),
    room_check("deterministic_uncertainty_is_unavailable_not_zero", None, CASE_NA["images"]["evidence"]["uri"]),
    room_check("retrieval_and_comparison_counts", (100, 10, 14, 7),
        (len(saved_retrieval), len(CASE.saved_panels(PACKAGE, "example_retrieval_panels")),
         len(CASE.saved_panels(PACKAGE, "counterfactual_panels")), len(choice_families))),
    room_check("outbound_network_attempts", [], attempts),
])
print("All 300 compact metric/map shards rehashed; remote raster corpus downloads and full numeric source parity are not claimed.")
display(CASE_SHARD_AUDIT.describe(include="all"))
display(CASE_METRIC_AVAILABILITY)
'''

CASE_SMOKE = r'''
CASE_RENDER_CASES = [
    dict(name="lama_opening", query={"room": "case_explorer"}, scene="ce-stage",
         expect={"candidate.candidate_id": CASE.OPENING, "layer": "difference"}),
    dict(name="lama_uncertainty_na", query={"room": "case_explorer", "ce_layer": "uncertainty"}, scene="ce-stage",
         expect={"candidate.candidate_id": CASE.OPENING, "layer": "uncertainty", "images.evidence.uri": None}),
    dict(name="sd_exact_candidate", query={"room": "case_explorer", "ce_candidate": "sd15__p00__s2026__d0cd65cf894a"}, scene="ce-stage",
         expect={"candidate.candidate_id": "sd15__p00__s2026__d0cd65cf894a", "candidate.seed": 2026}),
    dict(name="colour_saved_layer", query={"room": "case_explorer", "ce_layer": "colour"}, scene="ce-stage",
         expect={"candidate.candidate_id": CASE.OPENING, "layer": "colour"}),
    dict(name="cross_painting_rejected", query={"room": "case_explorer", "ce_painting": "p001", "ce_candidate": CASE.OPENING},
         scene="ce-stage", error="candidate"),
]
record_room_stage("batch_8_server_smoke", render_cases(CASE_RENDER_CASES))
'''

ARCHIVE_SOURCE = r'''
start_room_batch(9)
record_room_stage("batch_9_source_contract", freeze_checks("research_archive")
    + room_binding_checks("research_archive", 16, 17) + [test_record("archive")]
    + js_checks(["tests/research_archive_controller.test.cjs"]))
'''

ARCHIVE_DATA = r'''
from restoration_eval import research_archive as ARCHIVE
with n35.offline() as attempts:
    ARCHIVE_OPENING = ARCHIVE.payload(PACKAGE)
    ARCHIVE_PUBLICATIONS = ARCHIVE.payload(PACKAGE, view="publications")["publications"]
    ARCHIVE_N29 = ARCHIVE.record(PACKAGE, "N29")["summary"]
    verified_n33 = ARCHIVE.verify_manifest(PACKAGE, "N33")
    source_manifest = json.loads((ARCHIVE.INDEX / "manifest.json").read_text(encoding="utf-8"))
    for name in source_manifest["partitions"]:
        ARCHIVE.partition(name)  # Every saved compact partition verifies its own hash.
    candidate_view = ARCHIVE.payload(PACKAGE, view="candidates", painting="p018")
record_room_stage("batch_9_saved_evidence", [
    room_check("stage_set", {f"N{i:02}" for i in range(1, 34)} | {"N12A", "D01", "D02"},
        {r["id"] for r in ARCHIVE_OPENING["stages"]}),
    room_check("opening_saved_run", "run_aef04267c2e44495a4e7a6249426bd4d", ARCHIVE_OPENING["record"]["run"]["run_id"]),
    room_check("report_populations_separate", {"painting": 300, "case": 30, "collection": 1, "model": 5, "final": 1},
        dict(Counter(r["report_type"] for r in ARCHIVE_OPENING["reports"]))),
    room_check("claim_limit_figure_counts", (49, 18, 24), tuple(len(ARCHIVE_OPENING[k]) for k in ("claims", "limitations", "figures"))),
    room_check("saved_n33_checks_not_current_n35_results", {"total": 536, "passed": 536}, ARCHIVE_OPENING["checks"]),
    room_check("lazy_publications", [], ARCHIVE_OPENING["publications"]),
    room_check("individual_publication_records", (2653, {"candidates": 2644, "diagnostics": 9}),
        (len(ARCHIVE_PUBLICATIONS), dict(Counter(r["storage_tier"] for r in ARCHIVE_PUBLICATIONS)))),
    room_check("immutable_publication_revisions", True,
        all(len(r["pinned_revision"]) == 40 and "/resolve/main/" not in r["pinned_url"] for r in ARCHIVE_PUBLICATIONS)),
    room_check("registered_bundle_count", 6, len(ARCHIVE_OPENING["bundles"])),
    room_check("selected_painting_partition", {"p018"}, {r["painting_id"] for r in candidate_view["candidate_rows"]}),
    room_check("n33_run_manifest_integrity", "verified", verified_n33["state"]),
    room_check("known_n29_discrepancy_preserved", "recorded_hash_mismatch", ARCHIVE_N29["artifact_manifest_state"]),
    room_check("outbound_network_attempts", [], attempts),
])
N35_PROVENANCE_ISSUES = pd.DataFrame([{
    "stage": "N29", "issue": ARCHIVE_N29["artifact_manifest_state"],
    "expected": ARCHIVE_N29["artifact_manifest_expected_sha256"],
    "observed": ARCHIVE_N29["artifact_manifest_observed_sha256"],
    "disposition": "Investigate in Batch 10; not repaired, waived or represented as verified here.",
}])
display(N35_PROVENANCE_ISSUES)
print("2,653 publication records and six bundles are saved metadata, NOT fresh remote availability checks.")
'''

ARCHIVE_SMOKE = r'''
ARCHIVE_RENDER_CASES = [
    dict(name="n33_opening", query={"room": "research_archive"}, scene="ra-stage",
         expect={"record.summary.id": "N33", "record.run.run_id": "run_aef04267c2e44495a4e7a6249426bd4d", "publications": []}),
    dict(name="d02_saved_record", query={"room": "research_archive", "ar_record": "D02", "ar_view": "record"}, scene="ra-stage",
         expect={"record.summary.id": "D02", "open_view": "record"}),
    dict(name="p018_candidates", query={"room": "research_archive", "ar_view": "candidates", "ar_painting": "p018"}, scene="ra-stage",
         expect={"painting": "p018", "open_view": "candidates"}),
    dict(name="publication_metadata_only", query={"room": "research_archive", "ar_view": "publications_diagnostics"}, scene="ra-stage",
         expect={"open_view": "publications_diagnostics"}),
    dict(name="unknown_stage_rejected", query={"room": "research_archive", "ar_record": "N99"}, scene="ra-stage", error="Unknown stage"),
]
record_room_stage("batch_9_server_smoke", render_cases(ARCHIVE_RENDER_CASES))
'''

HANDOFF = r'''
n35.required_stages(VALIDATION.checks, [f"batch_{i}_final_gate" for i in range(2, 10)])
VALIDATION.raise_for_blocking()
assert not n35.snapshot(OUTPUT_ROOT), "Canonical persistence belongs to Batch 10 only."
N35_PENDING_GATES = pd.DataFrame([
    {"gate": "Whole-app required-asset closure", "status": "Inventory required runtime dependencies across every room/filter/report; distinguish optional and historical outputs."},
    {"gate": "Pinned remote coverage and missing assets", "status": "Check Git/HF objects and bundle members; create a deduplicated missing/mismatched list. No uploads authorized by these cells."},
    {"gate": "Deployment-safe loaders", "status": "Resolve local-only originals, producer-scale scans, report fallback and dynamic numeric-parity gaps."},
    {"gate": "Fresh environment", "status": "Clean checkout without the full local outputs tree; Linux/Python/dependency parity and bounded remote cache."},
    {"gate": "Failure/cache/performance", "status": "Cold/warm loads, missing/corrupt files, timeouts, retries, memory/startup/latency/concurrency budgets."},
    {"gate": "Browser QA", "status": "All routes, within-room versus cross-room reloads, Firefox/second monitor, keyboard/focus and three viewports."},
    {"gate": "N29 provenance discrepancy", "status": "Investigate recorded artifact-manifest mismatch; preserve historical evidence, do not silently rewrite it."},
    {"gate": "Publication and hosted verification", "status": "Explicit release step: approved missing artifacts/bundles, Git push, Streamlit deployment, then live-site smoke tests."},
    {"gate": "Batch 10 canonical output gate", "status": "Persist checks, readiness report, run manifest and artifact index only after agreed blocking gates pass; label hosted status honestly."},
])
display(N35_PENDING_GATES)
print("Batches 1–9 local room validation complete in this kernel; all eight tabs plus D02 covered.")
print("N35 is NOT complete. Canonical N35 outputs: 0. Remote publication: NOT RUN. Live deployment: NOT VERIFIED.")
print("STOP HERE. Batch 10 must be prepared next. Do not restore or execute the old pilot persistence cells.")
'''


def cell(source, kind="code"):
    return dict(cell_type=kind, source=dedent(source).strip() + "\n")


def reset(batch, suffixes):
    prefixes = tuple(f"batch_{batch}_{s}" for s in suffixes) + tuple(f"batch_{i}_" for i in range(batch + 1, 11))
    return f"drop_validation_stages({prefixes!r})\n\n"


def batch_cells(batch, title, explanation, source, evidence, smoke):
    return [
        cell(f"## Batch {batch} — {title}\n\n" + explanation, "markdown"),
        cell((reset(batch, ("",)) if batch != 6 else "") + source),
        cell(reset(batch, ("saved_evidence", "server_smoke", "final_gate"))
             + f"n35.required_stages(VALIDATION.checks, ['batch_{batch}_source_contract'])\n" + evidence),
        cell(reset(batch, ("server_smoke", "final_gate"))
             + f"n35.required_stages(VALIDATION.checks, ['batch_{batch}_saved_evidence'])\n" + smoke),
        cell(reset(batch, ("final_gate",)) + f"finish_room_batch({batch}, "
             + repr({f"batch_{batch}_source_contract", f"batch_{batch}_saved_evidence", f"batch_{batch}_server_smoke"}
                    | ({"batch_6_prior_binding_recheck"} if batch == 6 else set())) + ")\n"),
    ]


def build_cells(notebook):
    original = notebook["cells"]
    if len(original) < 49 or "## Batch 6" not in "".join(original[28]["source"]):
        raise ValueError("Unexpected notebook layout; do not replace shifted cells")
    cells = batch_cells(6, "Stability Lab — exact perturbations and seed groups", '''
<!-- N35_BATCHES_6_9_PACK -->

Validate the frozen room, not redesign it. Read saved N05/N06/N07/N18/N22 records:
35 focused paintings, 245 damage-size cases, 525 mask variants, 350 eligible degradation cases
(within 1,155 registered rows), and 1,025 four-seed groups / 6,150 unordered pairs.
Keep prompt identities separate and deterministic-method uncertainty unavailable, never zero.

The Batch 4/5 count corrections are valid: 12 displays have respectively 21 and 19 binding slots.
Recheck distinct slots and display coverage against N34 before continuing. Requires completed
replacement Batch 5 in the current kernel. Reload only the validation helper; never restart the server.

Original freeze hashes remain required. Normalize only the two approved e88feea5 non-visual
transport substitutions, and separately pin the final shared runtime. No fresh baselines are invented.
Tests load saved tables (some large), but run no inference, scientific producers or publication.
All cells in this pack are read-only with respect to the approved dashboard and canonical N35 outputs.
Python renders and offline controller unit tests are not browser/viewport or cloud certification.
''', SETUP, STABILITY_DATA, STABILITY_SMOKE)
    cells += batch_cells(7, "Trustworthiness and the shared D02 review", '''
Validate the 13,879-candidate union, separate primary/uncertainty/bounded roles, exact saved
assignments, threshold provenance and unresolved evidence. Computational flags are not expert
ground truth or conservation approval. Empirical seed disagreement is not calibrated confidence.

Validate D02's 60 screened portraits, 45 matched cases / 20 paintings and 32 blind reviews.
Keep R005's exact candidate and equal disjoint hand/control supports; retain the R003 non-failure
counterexample without borrowing R005 assets. Render the same child route from its three allowed
parents. Rendered lightness is not race or identity; do not combine the separate metrics.

Python source/data tests and dependency-free Node chart tests are local validation only. AppTest
checks exact JSON sent to controllers and visible rejection states; it cannot operate browser dialogs.
''', TRUST_SOURCE, TRUST_DATA, TRUST_SMOKE)
    cells += batch_cells(8, "Case Explorer — exact candidate and saved evidence", '''
Pin the final approved Case Explorer files to committed revision e88feea5, never the current
worktree as a new baseline. The room has 15 display records and 40 raw binding slots; the
LaMa opening API returns 39 compatible bindings because an SD-only uncertainty binding is excluded.

Verify all 300 compact metric/map shards and their exact candidate/case/model joins. Verify sampled
saved image bytes through the existing readers, keep LaMa uncertainty not applicable, preserve SD
seed identity, and reject cross-painting selections. Retrieval and counterfactuals remain recorded
examples, not automatically valid evidence for the selected case or new scientific calculations.

The 13,879 registered candidates are not 13,879 measured candidates: 11,944 have the three
selected saved metrics; 1,935 have none. Reconcile this against the exact source-table selections,
not merely observed shard counts. The streamed validation scan reads about 1.3 GB locally;
it may take a few minutes, uses bounded memory and produces no scientific outputs.

These checks do not re-download every raster or independently recalculate every scientific metric.
Full deployed source closure, required dynamic numeric parity and browser interaction stay Batch 10 gates.
''', CASE_SOURCE, CASE_DATA, CASE_SMOKE)
    cells += batch_cells(9, "Research Archive — immutable records and explicit limits", '''
Validate the frozen Archive, all compact partitions and N33's exact recorded run/commit. Keep
300 painting, 30 case, one collection, five model and one final report populations separate.
The displayed 536/536 checks belong to saved N33, not to current N35 validation.

The Archive's 2,653 individual publication records and six bundles describe saved metadata;
they are not proof that all remote objects are reachable today. The opening must stay lazy.
Preserve source provenance even where terse wall copy omits working-tree status.

N29 records an artifact-manifest checksum discrepancy. This batch verifies that it is faithfully
reported, NOT that the discrepant artifact is valid. Carry it into Batch 10 for investigation;
do not rewrite historical manifests or waive release-integrity gates to obtain a pass.

Replace ALL historical Batch 9 persistence cells with this six-cell section. No canonical files
are written here. Stop after the final pending-gates cell; Batch 10 is still to be prepared.
''', ARCHIVE_SOURCE, ARCHIVE_DATA, ARCHIVE_SMOKE)
    cells.append(cell(HANDOFF))
    assert len(cells) == 21
    for i, c in enumerate(cells, 28):
        if c["cell_type"] == "code":
            ast.parse(c["source"], filename=f"N35 cell {i}")
    return cells


def main():
    before = NOTEBOOK.read_bytes()
    cells = build_cells(json.loads(before))
    page = render(cells, start=28, title="N35 · Batches 6–9 complete replacement cells",
        notice="Replace cells 28–48 (zero-based): from the Batch 6 heading through the CURRENT END of the notebook, "
        "including ALL old Batch 9 persistence cells. Keep Markdown/code types. Leave Batches 1–5 unchanged. "
        "Continue in the successful Batch 5 kernel, or rerun the corrected Batches 1–5 first. "
        "Run these replacement cells in order, then STOP. Batch 10 and publication/deployment are not executed here.")
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "N35_batches_6_9_replacements.html").write_text(page, encoding="utf-8")
    text = "# Copy complete cells into N35; do not run this entire file as a script.\n\n"
    for i, c in enumerate(cells, 28):
        text += f'# %% {"[markdown] " if c["cell_type"] == "markdown" else ""}Cell {i}\n'
        text += ("\n".join("# " + line for line in c["source"].splitlines()) if c["cell_type"] == "markdown"
                 else c["source"]) + "\n\n"
    (DEST / "N35_batches_6_9_replacements.py").write_text(text, encoding="utf-8")
    (DEST / "cells.json").write_text(json.dumps(cells, indent=2), encoding="utf-8")
    assert NOTEBOOK.read_bytes() == before, "Notebook changed during preparation"
    print("Prepared 21 complete cells (28–48); syntax checked, none executed.")
    print("Notebook SHA-256 unchanged:", hashlib.sha256(before).hexdigest())
    print(DEST / "N35_batches_6_9_replacements.html")


if __name__ == "__main__":
    main()
