"""D04 Telea orchestration; calls the unchanged N09 array implementation."""
from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

import cv2
import numpy as np
import pandas as pd
from PIL import Image
import yaml

from . import real_damage_restoration as d04
from . import real_damage_readiness as readiness
from . import restoration_opencv as telea
from .manifests import sha256_file, utc_now_iso
from .paths import resolve_repo_path, to_repo_relative, require_notebook_output_path
from .real_damage_dataset import audit_inventory_inputs
from .validation import ValidationCollector

MODULE_VERSION = "1.0.0"
STAGE = "batch_3_telea"
MODEL = "opencv_telea"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, value: Any) -> None:
    readiness._atomic(path, readiness._bytes(value))


def _path(context: dict, relative: str) -> Path:
    return require_notebook_output_path(context["output_root"] / relative, d04.NOTEBOOK_STEM, context["root"])


def _check(context: dict, key: str, description: str, passed: bool, observed: Any, expected: Any = True) -> None:
    context["validation"].add(validation_stage=STAGE, check_id=key, check_description=description,
        passed=passed, severity="blocking", observed=observed, expected=expected)


def prepare_telea(project_root: str | Path, config_path: str | Path) -> dict:
    """Read-only handoff validation; do not re-freeze or rewrite Batch 2."""
    root = Path(project_root).resolve()
    path = resolve_repo_path(config_path, root, must_exist=True)
    policy = yaml.safe_load(path.read_text(encoding="utf-8"))
    d04._require(policy["schema_version"] == "real_damage_telea_config.v1" and policy["stage"] == STAGE
        and policy["expected_candidates"] == 10 and policy["smoke_repeats"] == 2
        and policy["overwrite_unverified_outputs"] is False and policy["checkpoint_after_each_candidate"] is True,
        "Unexpected Telea stage policy")
    for rel in [policy["helper_source"], policy["tests"], policy["readiness_checkpoint"], policy["baseline_config"], *policy["outputs"].values()]:
        d04._relative(rel)
    checkpoint_path = resolve_repo_path(policy["readiness_checkpoint"], root, must_exist=True)
    frozen = _read(checkpoint_path)
    d04._require(frozen["status"] == "ready_for_method_smoke" and frozen["notebook_id"] == "D04"
        and frozen["validation_summary"]["check_count"] == 55 and frozen["validation_summary"]["passed_count"] == 55
        and frozen["validation_summary"]["blocking_failure_count"] == 0, "Batch 2 is not ready")
    hashes = {**frozen["scientific_input_checksums"], **frozen["file_checksums"]}
    for rel, digest in hashes.items():
        d04._require(sha256_file(resolve_repo_path(rel, root, must_exist=True)) == digest, f"Frozen input/artifact changed: {rel}")
    main = d04.load_restoration_config(root / "config/experiments/real_damage_restoration.yaml")
    output = root / main["notebook"]["output_root"]
    plan = pd.read_csv(output / main["outputs"]["candidate_plan"], keep_default_na=False)
    worklist = plan.loc[plan.model_id.eq(MODEL)].sort_values("painting_id").reset_index(drop=True)
    d04._require(len(plan) == 70 and len(worklist) == 10 and worklist.painting_id.nunique() == 10
        and worklist.candidate_id.is_unique and worklist.candidate_role.eq("primary").all(), "Incorrect frozen Telea population")
    baseline = telea.load_opencv_telea_config(root / policy["baseline_config"])
    d04._require(baseline["model"]["inpaint_radius"] == 3
        and baseline["model"]["mask_threshold_policy"]["binary_missing_region"]["threshold"] == 128
        and worklist.model_config_sha256.eq(sha256_file(root / policy["baseline_config"])).all()
        and not worklist.has_clean_reference.any() and worklist.clean_image_path.eq("").all(), "Telea settings or reference scope changed")
    env = _read(output / "work/readiness/runtime_environment.json")
    d04._require(env["opencv_version"] == cv2.__version__, "OpenCV version differs from frozen readiness")
    declared = {"stage_config": path, "stage_helper": root / policy["helper_source"],
        "stage_tests": root / policy["tests"], "readiness_checkpoint": checkpoint_path}
    declared.update({f"readiness_artifact.{i}": root / rel for i, rel in enumerate(frozen["file_checksums"])})
    inventory, audit = audit_inventory_inputs(root, root / main["inputs"]["inventory"], root / main["inputs"]["inventory_run"], declared)
    checks = ValidationCollector()
    saved_checks = pd.read_csv(output / "work/readiness/checks.csv", keep_default_na=False)
    for row in saved_checks.to_dict("records"):
        checks.add(**row)
    binding = {to_repo_relative(p, root): sha256_file(p) for p in declared.values()}
    context = dict(root=root, output_root=output, policy=policy, config=main, baseline=baseline,
        frozen=frozen, plan=plan, worklist=worklist, validation=checks, inventory=inventory,
        stage_input_checksums=binding, frozen_input_checksums=hashes)
    context["execution_fingerprint"] = d04._digest(dict(stage_inputs=binding,
        readiness_fingerprint=frozen["readiness_fingerprint"], opencv_version=cv2.__version__, module_version=MODULE_VERSION))
    _check(context, "readiness_integrity", "Frozen Batch 2 artifacts and scientific inputs retain their checksums", True, len(hashes), 153)
    _check(context, "telea_population", "Ten primary Telea candidates retain the frozen IDs", True, len(worklist), 10)
    _check(context, "baseline_settings", "N09 configuration and algorithm are unchanged; physical references are unavailable", True, "radius=3; threshold=128; CPU; 768px")
    _check(context, "opencv_version", "OpenCV matches the Batch 2 environment", True, cv2.__version__, env["opencv_version"])
    _check(context, "stage_inventory", "Current inventory covers stage inputs and frozen readiness artifacts", bool(audit.passed.all()), audit.loc[~audit.passed].to_dict("records"), [])
    checks.raise_for_blocking()
    return context


def _inputs(context: dict, row: dict) -> tuple[np.ndarray, np.ndarray]:
    root, baseline = context["root"], context["baseline"]
    for key, digest in (("input_image_path", "input_image_sha256"), ("mask_path", "mask_sha256")):
        d04._require(sha256_file(resolve_repo_path(row[key], root, must_exist=True)) == row[digest], f"Candidate {key} changed: {row['candidate_id']}")
    image = cv2.imread(str(root / row["input_image_path"]), cv2.IMREAD_COLOR)
    mask = cv2.imread(str(root / row["mask_path"]), cv2.IMREAD_GRAYSCALE)
    shape = (baseline["execution"]["target_height"], baseline["execution"]["target_width"])
    d04._require(image is not None and mask is not None and image.shape == (*shape, 3) and mask.shape == shape,
                 "Input/mask dimensions do not match the unchanged pipeline")
    d04._require(set(np.unique(mask)).issubset({0, 255}) and np.any(mask), "Expected a nonempty reviewed binary repair mask")
    return image, telea.binarize_restoration_mask(mask, int(row["mask_threshold"]))


def _technical(image: np.ndarray, mask: np.ndarray, restored: np.ndarray) -> dict:
    d04._require(restored.shape == image.shape and restored.dtype == np.uint8, "Invalid restored image array")
    changed = np.any(image != restored, axis=2)
    inside = mask > 0
    return dict(width=int(restored.shape[1]), height=int(restored.shape[0]), output_mode="RGB",
        mask_pixels=int(inside.sum()), changed_inside_pixels=int((changed & inside).sum()),
        changed_outside_pixels=int((changed & ~inside).sum()),
        inside_change_fraction=float((changed & inside).sum() / inside.sum()),
        diagnostic_scope="pixel_preservation_and_edit_magnitude_not_reference_accuracy")


def _verify_record(context: dict, row: dict, output: Path, record: dict, binding: str,
                   image: np.ndarray, mask: np.ndarray) -> None:
    d04._require(record["execution_binding"] == binding and record["status"] == "completed"
        and record["candidate_id"] == row["candidate_id"], "Candidate receipt binding changed")
    d04._require(output.is_file() and sha256_file(output) == record["restored_sha256"], "Restoration checksum mismatch")
    with Image.open(output) as pil:
        d04._require(pil.mode == "RGB" and pil.size == (image.shape[1], image.shape[0]), "Invalid PNG encoding")
        pil.verify()
    technical = _technical(image, mask, cv2.imread(str(output), cv2.IMREAD_COLOR))
    d04._require(technical == {k: record[k] for k in technical} and technical["changed_outside_pixels"] == 0,
                 "Restoration technical evidence mismatch")


def execute_case(context: dict, row: dict, *, scope: str = "primary") -> tuple[dict, bool]:
    """Resume only checksum-bound results; interrupted writes must reproduce exactly."""
    image, mask = _inputs(context, row)
    relative = row["restored_path"] if scope == "primary" else f"work/telea/{scope}/{row['candidate_id']}.png"
    output = _path(context, relative)
    receipt = _path(context, f"work/telea/receipts/{scope}/{row['candidate_id']}.json")
    binding = d04._digest(dict(execution=context["execution_fingerprint"], candidate=row, scope=scope))
    previous = _read(receipt) if receipt.exists() else None
    if previous:
        d04._require(previous["execution_binding"] == binding, "Existing receipt belongs to different inputs or code")
        if previous["status"] == "completed":
            _verify_record(context, row, output, previous, binding, image, mask)
            return previous, True
        d04._require(previous["status"] == "started", "Unrecognized candidate receipt state")
    else:
        d04._require(not output.exists(), "Unverified existing image cannot be overwritten")
        _save(receipt, dict(status="started", candidate_id=row["candidate_id"], execution_binding=binding,
                            started_at_utc=utc_now_iso()))
    started, timer = utc_now_iso(), perf_counter()
    restored, action = telea.restore_array_with_opencv_telea(image, mask, radius=context["baseline"]["model"]["inpaint_radius"])
    technical = _technical(image, mask, restored)
    d04._require(technical["changed_outside_pixels"] == 0, "Telea modified outside-mask pixels")
    ok, encoded = cv2.imencode(".png", restored, [cv2.IMWRITE_PNG_COMPRESSION, context["baseline"]["execution"]["png_compress_level"]])
    d04._require(ok, "PNG encoding failed")
    content = encoded.tobytes()
    d04._require(not output.exists() or output.read_bytes() == content, "Interrupted candidate image differs from deterministic reconstruction")
    if not output.exists():
        readiness._atomic(output, content)
    record = dict(row)
    record.update(schema_version="real_damage_candidates.v1", status="completed", runtime_status="inference_validated",
        execution_action=action, execution_scope=scope, execution_binding=binding,
        execution_fingerprint=context["execution_fingerprint"], readiness_fingerprint=context["frozen"]["readiness_fingerprint"],
        restored_path=to_repo_relative(output, context["root"]), restored_sha256=sha256_file(output),
        opencv_version=cv2.__version__, generator_name=telea.RESTORATION_GENERATOR_NAME,
        generator_version=telea.RESTORATION_GENERATOR_VERSION, adapter_version=MODULE_VERSION,
        inpaint_radius=context["baseline"]["model"]["inpaint_radius"], **technical,
        runtime_seconds=perf_counter() - timer, started_at_utc=started, completed_at_utc=utc_now_iso(), issue="")
    _save(receipt, record)
    _verify_record(context, row, output, record, binding, image, mask)
    return record, False


def run_smoke(context: dict) -> dict:
    row = context["worklist"].loc[context["worklist"].painting_id.eq(context["policy"]["smoke_painting_id"])].iloc[0].to_dict()
    first, _ = execute_case(context, row, scope="smoke_1")
    second, _ = execute_case(context, row, scope="smoke_2")
    image, _ = _inputs(context, row)
    identity, action = telea.restore_array_with_opencv_telea(image, np.zeros(image.shape[:2], np.uint8),
        radius=context["baseline"]["model"]["inpaint_radius"])
    _check(context, "smoke_repeatability", "Two identical-input smoke runs produce identical PNG hashes", first["restored_sha256"] == second["restored_sha256"], first["restored_sha256"], second["restored_sha256"])
    _check(context, "smoke_outside", "Both smoke runs preserve every outside-mask pixel", first["changed_outside_pixels"] == second["changed_outside_pixels"] == 0, [first["changed_outside_pixels"], second["changed_outside_pixels"]], [0, 0])
    _check(context, "smoke_shape", "Smoke PNG dimensions and RGB mode match the input", first["width"] == second["width"] == image.shape[1] and first["height"] == second["height"] == image.shape[0], [first["width"], first["height"]])
    _check(context, "smoke_zero_identity", "Empty-mask technical control preserves all pixels", action == "identity_noop" and np.array_equal(identity, image), action, "identity_noop")
    context["smoke_records"] = [first, second]
    summary = dict(stage=STAGE, execution_fingerprint=context["execution_fingerprint"], painting_id=row["painting_id"],
        repeat_count=2, primary_candidate_count=0, records=[first, second], zero_mask_identity=bool(np.array_equal(identity, image)))
    _save(_path(context, context["policy"]["outputs"]["smoke_summary"]), summary)
    context["validation"].raise_for_blocking()
    context["smoke_passed"] = True
    return context


def _merge_table(path: Path, frame: pd.DataFrame) -> None:
    if path.exists():
        existing = pd.read_csv(path, keep_default_na=False, float_precision="round_trip")
        other = existing.loc[existing.model_id.ne(MODEL)]
        if not other.empty:
            frame = pd.DataFrame([*other.to_dict("records"), *frame.to_dict("records")])
    d04._require(not frame.candidate_id.duplicated().any() if "candidate_id" in frame else not frame.model_id.duplicated().any(),
                 "Duplicate IDs in accumulated table")
    _save(path, frame)


def run_candidates(context: dict, progress: Callable[[str], None] = print) -> dict:
    d04._require(context.get("smoke_passed") is True, "Telea smoke checks must pass first")
    # Catch edits made between setup, smoke and the full run.
    for rel, digest in context["stage_input_checksums"].items():
        d04._require(sha256_file(context["root"] / rel) == digest, f"Stage input changed: {rel}")
    records, reused = [], 0
    for i, row in enumerate(context["worklist"].to_dict("records"), 1):
        try:
            record, cached = execute_case(context, row)
            reused += int(cached)
            action = "reused" if cached else "completed"
        except Exception as exc:
            record = {**row, "status": "failed", "issue": f"{type(exc).__name__}: {exc}"}
            log = _path(context, f"logs/telea_{row['candidate_id']}.jsonl")
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(dict(recorded_at_utc=utc_now_iso(), **record)) + "\n")
            action = "failed"
        records.append(record)
        # Receipts are authoritative, with one accumulated table updated per candidate.
        _merge_table(_path(context, context["config"]["outputs"]["candidates"]), pd.DataFrame(records))
        progress(f"Telea {i}/{len(context['worklist'])} | {row['painting_id']} | {action}")
    context.update(records=pd.DataFrame(records), reused_candidates=reused)
    return context


def validate_results(context: dict) -> dict:
    records, checks = context["records"], context["validation"]
    for row in records.to_dict("records"):
        good = row["status"] == "completed"
        _check(context, f"completed:{row['painting_id']}", "Primary Telea candidate completed", good, row["status"], "completed")
        valid = preserved = False
        if good:
            planned = context["worklist"].loc[context["worklist"].candidate_id.eq(row["candidate_id"])].iloc[0].to_dict()
            image, mask = _inputs(context, planned)
            output = resolve_repo_path(row["restored_path"], context["root"], must_exist=True)
            binding = d04._digest(dict(execution=context["execution_fingerprint"], candidate=planned, scope="primary"))
            _verify_record(context, planned, output, row, binding, image, mask)
            valid, preserved = True, row["changed_outside_pixels"] == 0
        _check(context, f"output:{row['painting_id']}", "Saved output matches its input/configuration binding, checksum and RGB dimensions", valid, valid)
        _check(context, f"outside:{row['painting_id']}", "Every outside-mask pixel is preserved", preserved, row.get("changed_outside_pixels", "unavailable"), 0)
    complete = int(records.status.eq("completed").sum())
    _check(context, "primary_population", "All ten frozen Telea primary candidates are retained", complete == 10 and set(records.candidate_id) == set(context["worklist"].candidate_id), complete, 10)
    _save(_path(context, context["policy"]["outputs"]["stage_checks"]), checks.to_dataframe())
    cumulative_path = _path(context, context["config"]["outputs"]["validation"])
    cumulative = checks.to_dataframe()
    if cumulative_path.exists():
        previous = pd.read_csv(cumulative_path, keep_default_na=False)
        previous = previous.loc[~previous.validation_stage.isin(cumulative.validation_stage.unique())]
        if not previous.empty:
            cumulative = pd.concat([previous, cumulative], ignore_index=True)
    _save(cumulative_path, cumulative)
    summary = dict(model_id=MODEL, stage=STAGE, expected_candidates=10, completed_candidates=complete,
        failed_candidates=10-complete, reused_candidates=context["reused_candidates"],
        recorded_case_runtime_seconds=float(pd.to_numeric(records.get("runtime_seconds", pd.Series(dtype=float)), errors="coerce").sum()),
        runtime_scope="original_primary_case_calls_excluding_smoke_review_and_resume_validation",
        execution_fingerprint=context["execution_fingerprint"], validation_summary=checks.summary(),
        notebook_completion_gate_passed=False, recorded_at_utc=utc_now_iso())
    _save(_path(context, context["policy"]["outputs"]["stage_summary"]), summary)
    runtime = pd.DataFrame([{k:v for k,v in summary.items() if k != "validation_summary"}])
    _merge_table(_path(context, context["config"]["outputs"]["runtime_summary"]), runtime)
    context["summary"] = summary
    checks.raise_for_blocking()
    return context


def render_previews(context: dict) -> list[Path]:
    """Show all physical inputs, masks and primary outputs; no accuracy scores."""
    import matplotlib.pyplot as plt
    context["validation"].raise_for_blocking()
    paths = []
    for key, start, end in (("preview_first", 0, 5), ("preview_second", 5, 10)):
        fig, axes = plt.subplots(5, 3, figsize=(13, 16))
        for i, row in enumerate(context["records"].iloc[start:end].to_dict("records")):
            image, mask = _inputs(context, row)
            restored = cv2.imread(str(context["root"] / row["restored_path"]), cv2.IMREAD_COLOR)
            for j, (pixels, title) in enumerate(((image, "Damaged input"), (image, "Selected repair mask"), (restored, "Telea restoration"))):
                axes[i,j].imshow(cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB))
                if j == 1:
                    overlay = np.zeros((*mask.shape, 4)); overlay[mask > 0] = [0, 1, 1, .4]
                    axes[i,j].imshow(overlay)
                axes[i,j].set_title(f"{row['painting_id']} | {title}", fontsize=9)
                axes[i,j].axis("off")
        fig.suptitle("D04 | Telea primary restorations — radius 3, unchanged reviewed masks", fontsize=13)
        fig.text(.5, .012, "No clean references: visual inspection does not establish reconstruction accuracy.\n"
            "Source credits/licences: D03 artworks.csv; rd004 Tyler Bell CC BY 2.0; rd005 BeakheadIntrados CC BY-SA 4.0; rd006 The Met CC0.\n"
            "Other sources retain their recorded public-domain terms. Restorations, resizing and mask overlays are adaptations.", ha="center", fontsize=7)
        fig.tight_layout(rect=(0,.05,1,.97))
        path = _path(context, context["policy"]["outputs"][key]); path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=130); plt.close(fig); paths.append(path)
    context["preview_paths"] = paths
    return paths
