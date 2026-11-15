"""D03 final gate: audit published evidence and finalize only its metadata."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd
import yaml
from PIL import Image

from .manifests import (artifact_records_dataframe,
                        sha256_file, sha256_path, utc_now_iso)
from .paths import find_project_root, notebook_output_root, resolve_repo_path, to_repo_relative
from .real_damage_dataset import (NOTEBOOK_STEM, _require, audit_inventory_inputs,
    load_approved_sources, load_real_damage_config, validate_binary_damage_mask)
from .real_damage_publication import HANDOFF_CONDITION, TABLE_NAMES
from .validation import ValidationCollector

REAL_DAMAGE_COMPLETION_MODULE_VERSION = "1.0.0"
COMPLETION_STAGE = "batch_8_final_completion_gate"
ADMINISTRATIVE_INPUTS = frozenset({"inventory", "inventory_run", "evidence_audit",
                                 "notebook_roadmap", "evidence_coverage", "project_paths"})
PRIOR_STAGE_COUNTS = {
    "batch_1_preflight": 43, "batch_2_source_validation": 66,
    "batch_3_preprocessing_smoke": 35, "batch_4_preprocessing_and_mask_candidates": 63,
    "batch_5_mask_review_and_inference_scale": 43,
    "batch_6_geometry_and_model_eligibility": 49, "batch_7_canonical_publication": 35,
}
METADATA_PATHS = ("validation/checks.csv", "manifests/artifacts.csv", "manifests/run_manifest.json")


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def _collector(frame: pd.DataFrame) -> ValidationCollector:
    result = ValidationCollector()
    for row in frame.fillna("").to_dict("records"):
        _require(type(row["passed"]) is bool, "Validation passed values must be Boolean")
        result.add(**row)
    return result


def _replace(path: Path, content: bytes) -> None:
    """Atomic single-file metadata replacement; multi-file rollback is below."""
    if path.is_file() and path.read_bytes() == content:
        return
    temporary = path.with_name(path.name + ".completion.tmp")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_completion_config(path: str | Path) -> dict[str, Any]:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    fixed = {"config_schema_version": "real_damage_completion_config.v1",
        "dataset_scope": "real_damage_10", "dataset_version": "2.0.0",
        "completion_gate_batch": 8, "expected_canonical_files": 34,
        "expected_artifact_records": 14, "expected_prior_checks": 334,
        "scientific_artifacts_immutable": True, "runtime_and_weights_check_stage": "D04"}
    _require(all(config.get(k) == v for k, v in fixed.items()), "Completion policy changes the approved contract")
    _require(set(config["refreshable_administrative_inputs"]) == ADMINISTRATIVE_INPUTS,
             "Only explicit administrative inputs may change after publication")
    return config


def audit_completion(project_root: str | Path, completion_config_path: str | Path) -> dict[str, Any]:
    """Read-only final audit; no notebook execution or artifact modification."""
    started = perf_counter()
    root = Path(project_root).resolve()
    _require(find_project_root(root) == root, "Explicit project root must identify the intended repository")
    output = notebook_output_root(NOTEBOOK_STEM, root)
    config_path = resolve_repo_path(completion_config_path, root)
    policy = load_completion_config(config_path)
    config = load_real_damage_config(root / "config/datasets/real_damage_10.yaml")
    manifest = _json(output / METADATA_PATHS[2])
    done = manifest.get("completion_gate_passed") is True
    _require(manifest["notebook_id"] == "D03" and manifest["dataset_versions"] == config["dataset"], "Wrong D03 population")
    _require(manifest["run_status"] == ("completed" if done else "partial")
             and manifest.get("downstream_ready") is done, "Inconsistent completion state")
    if done:
        _require(bool(manifest.get("completed_at_utc")), "Completed timestamp missing")
        for record in manifest["completion_inputs"]:
            _require(sha256_file(root / record["relative_path"]) == record["checksum"], "Completion producer or policy changed")
    artifacts_path = output / METADATA_PATHS[1]
    _require(sha256_file(artifacts_path) == manifest["artifact_manifest_sha256"], "Artifact manifest digest mismatch")
    artifacts = pd.read_csv(artifacts_path).fillna("")
    artifact_records_dataframe(artifacts.to_dict("records"))
    _require(len(artifacts) == policy["expected_artifact_records"], "Wrong artifact count")
    _require(artifacts.to_dict("records") == pd.DataFrame(manifest["outputs"]).fillna("").to_dict("records"), "Run/artifact records disagree")
    scientific = manifest["canonical_file_checksums"]
    fingerprint = hashlib.sha256(json.dumps(scientific, sort_keys=True).encode()).hexdigest()
    _require(len(scientific) == 31 and fingerprint == manifest["data_fingerprint"], "Scientific file-set fingerprint mismatch")
    for relative, digest in scientific.items():
        path = resolve_repo_path(relative, root)
        _require(path.is_relative_to(output) and not path.is_relative_to(output / "work"), "Invalid canonical artifact path")
        _require(sha256_file(path) == digest, f"Scientific artifact changed: {relative}")
    expected_files = {root / p for p in scientific} | {output / p for p in METADATA_PATHS}
    actual_files = {p for p in output.rglob("*") if p.is_file() and not p.is_relative_to(output / "work")}
    _require(actual_files == expected_files and len(actual_files) == 34, "Canonical file set differs")
    for row in artifacts.to_dict("records"):
        _require(sha256_path(root / row["relative_path"]) == row["checksum"], f"Artifact changed: {row['artifact_key']}")
    saved_validation = pd.read_csv(output / METADATA_PATHS[0])
    saved_collector = _collector(saved_validation)
    _require(saved_collector.summary() == manifest["validation_summary"] and saved_validation.passed.all(), "Published validation is inconsistent")
    prior = saved_validation.loc[saved_validation.validation_stage.ne(COMPLETION_STAGE)]
    _require(prior.groupby("validation_stage").size().to_dict() == PRIOR_STAGE_COUNTS, "Earlier batch coverage is incomplete")
    collector = _collector(prior)

    def check(key: str, description: str, passed: bool, observed: Any, expected: Any = True) -> None:
        collector.add(validation_stage=COMPLETION_STAGE, check_id=key, check_description=description,
                      severity="blocking", passed=passed, observed=observed, expected=expected)

    check("prior_validation", "All seven earlier stages passed with their declared coverage", True, len(prior), 334)
    check("canonical_integrity", "Canonical paths and scientific SHA-256 values match publication", True, len(actual_files), 34)
    check("artifact_integrity", "All artifact hashes and both manifest records agree", True, len(artifacts), 14)
    completion_inputs = {"completion.config": config_path,
                         "completion.helper_source": root / policy["helper_source"]}
    current_inputs = {r["input_key"]: resolve_repo_path(r["relative_path"], root) for r in manifest["inputs"]}
    administrative_changes = []
    for record in manifest["inputs"]:
        digest = sha256_file(current_inputs[record["input_key"]])
        if digest != record["checksum"]:
            _require(record["input_key"] in ADMINISTRATIVE_INPUTS, f"Published scientific input changed: {record['input_key']}")
            administrative_changes.append(dict(input_key=record["input_key"], relative_path=record["relative_path"],
                                               publication_sha256=record["checksum"], completion_sha256=digest))
    check("upstream_binding", "Published scientific inputs and producer configurations remain unchanged", True, "verified")
    audit_inputs = {**current_inputs, **completion_inputs,
                    **{f"canonical.{i}": root / p for i, p in enumerate(sorted(scientific))}}
    inventory, input_audit = audit_inventory_inputs(root, current_inputs["inventory"], current_inputs["inventory_run"], audit_inputs)
    check("inventory", "Current inventory covers scientific outputs and completion inputs", bool(input_audit.passed.all()),
          input_audit.loc[~input_audit.passed].to_dict("records"), [])
    catalog = load_approved_sources(root / config["inputs"]["approved_sources"], config)
    check("pipeline_baseline", "Approved shared preprocessing and model baselines remain unchanged",
          all(sha256_file(root / p) == h for p, h in catalog["pipeline_baseline_sha256"].items()), "hash comparison")
    tables = {key: pd.read_csv(output / config["outputs"][key]) for key in TABLE_NAMES}
    ids = config["dataset"]["painting_ids"]
    models = config["downstream"]["primary_models"]
    for key, frame in tables.items():
        valid = len(frame) == (40 if key == "model_eligibility" else 10)
        valid &= set(frame.painting_id) == set(ids)
        if key != "model_eligibility":
            valid &= frame.painting_id.is_unique and frame.painting_id.tolist() == ids
        valid &= frame.dataset_scope.eq("real_damage_10").all() and frame.dataset_version.eq("2.0.0").all()
        check(f"table:{key}", "Canonical table retains its exact population and scope", bool(valid), len(frame))
    art = tables["artworks"].set_index("painting_id")
    images = tables["preprocessed_images"].set_index("painting_id")
    masks = tables["masks"].set_index("painting_id")
    reviews = tables["mask_review"].set_index("painting_id")
    cases = tables["case_registry"].set_index("painting_id")
    scale = tables["inference_mask_audit"].set_index("painting_id")
    geometry = tables["mask_geometry"].set_index("painting_id")
    eligible = tables["model_eligibility"]
    check("category_balance", "Five operational categories contain two paintings each",
          art.groupby("category").size().to_dict() == {c: 2 for c in config["dataset"]["categories"]}, art.groupby("category").size().to_dict())
    absent = all(not frame.has_clean_reference.any() for frame in tables.values() if "has_clean_reference" in frame)
    absent &= all(frame.clean_image_path.isna().all() for frame in tables.values() if "clean_image_path" in frame)
    absent &= not cases.reference_fidelity_metrics_applicable.any() and not eligible.reference_fidelity_metrics_applicable.any()
    check("no_fabricated_reference", "No clean target or interior reference-fidelity applicability is claimed", bool(absent), "no clean reference")
    check("case_identifiers", "Cases and masks retain unique versioned identifiers", cases.case_id.is_unique and masks.mask_id.is_unique
          and cases.case_id.str.startswith("real_damage__v2_0_0__").all(), len(cases), 10)
    check("cartesian_model_coverage", "Each case occurs exactly once for each of the four methods",
          not eligible.duplicated(["case_id", "model_id"]).any()
          and set(zip(eligible.case_id, eligible.model_id)) == {(c, m) for c in cases.case_id for m in models}, len(eligible), 40)
    check("eligibility_boundary", "All 40 pairs are input-compatible; runtime is explicitly deferred to D04",
          bool(eligible.eligible.all() and eligible.runtime_status.eq("not_checked_D04").all()
               and eligible.handoff_status.eq(HANDOFF_CONDITION).all() and cases.handoff_status.eq(HANDOFF_CONDITION).all()), "input/mask eligibility only")
    for pid in ids:
        im, mask, review, case, sc, geo = (f.loc[pid] for f in (images, masks, reviews, cases, scale, geometry))
        with Image.open(root / im.processed_path) as image, Image.open(root / mask.mask_path) as binary:
            _require(image.mode == "RGB" and image.size == (768, 768), f"Invalid processed input: {pid}")
            box = tuple(int(im[k]) for k in ("content_x_min", "content_y_min", "content_x_max", "content_y_max"))
            pixels = validate_binary_damage_mask(binary, content_box=box)
        binding = (sha256_file(root / im.processed_path) == im.sha256 == mask.input_sha256 == review.input_sha256 == case.input_image_sha256
            and sha256_file(root / mask.mask_path) == mask.mask_sha256 == review.mask_sha256 == case.mask_sha256
            and sha256_file(root / mask.candidate_mask_path) == mask.mask_sha256
            and case.input_image_path == im.processed_path and case.mask_or_effect_path == mask.mask_path
            and case.mask_id == mask.mask_id == review.mask_id and case.case_id == mask.case_id == review.case_id == geo.case_id == sc.case_id)
        check(f"binding:{pid}", "Canonical input, reviewed mask and stable case identifiers agree", bool(binding), pid)
        reviewed = review.review_status in {"approved", "approved_with_ambiguity"} and review.scale_review_status == "accepted"
        reviewed &= bool(review.candidate_is_final) and pd.notna(review.reviewer) and pd.notna(review.scale_reviewer)
        reviewed &= sha256_file(root / sc.inference_mask_path) == sc.inference_mask_sha256 and not sc.empty_inference_mask
        reviewed &= int(np.count_nonzero(pixels)) == int(mask.mask_pixel_count) == int(geo.damaged_pixel_count)
        check(f"review:{pid}", "Researcher review, accepted 512-pixel mask and selected area remain bound", bool(reviewed), review.scale_review_status)
    for model in models:
        rows = eligible.loc[eligible.model_id.eq(model)]
        match = all(sha256_file(root / r.model_config_path) == r.model_config_sha256
                    and r.input_image_path == images.loc[r.painting_id].processed_path
                    and r.input_image_sha256 == images.loc[r.painting_id].sha256
                    and r.mask_path == masks.loc[r.painting_id].mask_path
                    and r.mask_sha256 == masks.loc[r.painting_id].mask_sha256
                    for r in rows.itertuples())
        check(f"model:{model}", "Existing method configuration and image/mask joins are unchanged", match, len(rows), 10)
    report = (output / config["outputs"]["report"]).read_text(encoding="utf-8")
    check("illustrated_report", "Report embeds both figures and retains source credits and links", report.count("data:image/png;base64,") == 2
          and all(str(r.source_url).replace("&", "&amp;") in report for r in art.itertuples()), "embedded figures and provenance")
    for key in ("source_overview", "mask_review_atlas"):
        with Image.open(output / config["outputs"][key]) as image:
            image.verify()
    check("figure_integrity", "Both saved overview figures decode", True, 2, 2)
    collector.raise_for_blocking()
    return dict(validation=collector, saved_validation=saved_collector, tables=tables, artifacts=artifacts,
        run_manifest=manifest, config=config, completion_config=policy, completion_inputs=completion_inputs,
        input_audit=input_audit, inventory_run=inventory, administrative_changes=administrative_changes,
        elapsed_seconds=perf_counter() - started, output_root=output)


def _recover_metadata(output: Path) -> None:
    """Roll back an interrupted commit before auditing; never change scientific files."""
    journal = output / "work/completion_commit"
    plan_path = journal / "transaction.json"
    if not plan_path.exists():
        return
    plan = _json(plan_path)
    _require(set(plan["files"]) == set(METADATA_PATHS), "Unexpected completion transaction targets")
    for relative, versions in plan["files"].items():
        _require(sha256_file(output / relative) in {versions["before"], versions["after"]}, "Metadata changed outside completion transaction")
        for state in ("before", "after"):
            _require(sha256_file(journal / state / relative) == versions[state], "Completion recovery copy changed")
        temporary = (output / relative).with_name(Path(relative).name + ".completion.tmp")
        temporary.unlink(missing_ok=True)
    if all(sha256_file(output / p) == v["after"] for p, v in plan["files"].items()):
        return
    for relative in METADATA_PATHS:
        _replace(output / relative, (journal / "before" / relative).read_bytes())
    # All three originals are restored. Retire this plan before staging a retry,
    # so a process exit during new backup writes cannot leave an obsolete plan.
    plan_path.unlink()


def complete_real_damage_dataset(project_root: str | Path, completion_config_path: str | Path) -> dict[str, Any]:
    """Verify everything first, then commit validation/artifact/run metadata last."""
    started = perf_counter()
    root = Path(project_root).resolve()
    _require(find_project_root(root) == root, "Explicit project root must identify the intended repository")
    output = notebook_output_root(NOTEBOOK_STEM, root)
    _recover_metadata(output)
    result = audit_completion(root, completion_config_path)
    manifest = result["run_manifest"]
    if manifest["completion_gate_passed"]:
        result["validation"] = result["saved_validation"]
        result["elapsed_seconds"] = perf_counter() - started
        return result
    manifest = copy.deepcopy(manifest)
    validation_bytes = _csv_bytes(result["validation"].to_dataframe())
    records = result["artifacts"].to_dict("records")
    validation_record = next(r for r in records if r["artifact_key"] == "validation")
    digest = hashlib.sha256(validation_bytes).hexdigest()
    identity = f"validation|{validation_record['relative_path']}|{digest}".encode()
    validation_record.update(checksum=digest, artifact_id="artifact_" + hashlib.sha256(identity).hexdigest()[:20],
                             row_count=len(result["validation"].checks), size_bytes=len(validation_bytes))
    artifacts = artifact_records_dataframe(records)
    artifact_bytes = _csv_bytes(artifacts)
    completion_inputs = [dict(input_key=k, relative_path=to_repo_relative(p, root), checksum=sha256_file(p))
                         for k, p in result["completion_inputs"].items()]
    manifest.update(run_status="completed", completed_at_utc=utc_now_iso(), completion_gate_passed=True,
        downstream_ready=True, completion_stage=8, validation_summary=result["validation"].summary(),
        outputs=records, artifact_manifest_sha256=hashlib.sha256(artifact_bytes).hexdigest(),
        completion_inputs=completion_inputs, completion_inventory_run_id=result["inventory_run"]["inventory_run_id"],
        completion_administrative_input_changes=result["administrative_changes"],
        completion_handoff={"next_stage": "D04", "cases": 10, "eligible_pairs": 40,
            "scope": "dataset_inputs_and_reviewed_masks", "inference_executed": False,
            "runtime_and_weights_verified": False, "d04_contract_approval_required": True},
        publication_review={"reviewer": "Rahul Maddineni",
            "basis": "user_accepted_saved_batch_7_figures_and_report_in_chat",
            "reviewed_data_fingerprint": manifest["data_fingerprint"]},
        publication_retained_work_files=manifest["retained_work_files"],
        retained_work_files=sum(p.is_file() for p in (output / "work").rglob("*")
                                if not p.is_relative_to(output / "work/completion_commit")) + 7,
        completion_record_version="real_damage_completion.v1")
    manifest["helper_versions"]["real_damage_completion"] = REAL_DAMAGE_COMPLETION_MODULE_VERSION
    payloads = dict(zip(METADATA_PATHS, (validation_bytes, artifact_bytes, _json_bytes(manifest))))
    journal = output / "work/completion_commit"
    plan = {"schema_version": "d03_metadata_transaction.v1", "files": {}}
    for relative, content in payloads.items():
        before = (output / relative).read_bytes()
        for state, data in (("before", before), ("after", content)):
            backup = journal / state / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            _replace(backup, data)
        plan["files"][relative] = {"before": hashlib.sha256(before).hexdigest(), "after": hashlib.sha256(content).hexdigest()}
    _replace(journal / "transaction.json", _json_bytes(plan))
    try:
        for relative, content in payloads.items():
            _replace(output / relative, content)
        _require(_json(output / METADATA_PATHS[2]) == manifest, "Completion manifest round-trip failed")
        for row in records:
            _require(sha256_path(root / row["relative_path"]) == row["checksum"], "Completed artifact checksum mismatch")
    except BaseException:
        for relative in METADATA_PATHS:
            _replace(output / relative, (journal / "before" / relative).read_bytes())
        raise
    result.update(run_manifest=manifest, artifacts=artifacts, elapsed_seconds=perf_counter() - started)
    return result
