"""D03 hash-bound researcher mask review and inference-scale diagnostics.

This stage records an existing human decision at 768 pixels. It presents the
512-pixel consequences separately and never grants model eligibility.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd
from PIL import Image
from scipy.ndimage import label

from .manifests import sha256_file
from .paths import notebook_output_root, require_notebook_output_path, resolve_repo_path, to_repo_relative
from .real_damage_dataset import (
    NOTEBOOK_STEM, _require, audit_inference_mask, validate_binary_damage_mask,
    validate_real_damage_config, validate_review_binding,
)
from .real_damage_preparation import PREPARATION_STAGE, _atomic_write, _png_bytes
from .validation import ValidationCollector

REAL_DAMAGE_REVIEW_MODULE_VERSION = "1.0.0"
REVIEW_STAGE = "batch_5_mask_review_and_inference_scale"
REVIEW_WORK_DIRECTORY = "work/mask_review"


def inference_scale_evidence(mask: Image.Image, *, content_box: tuple[int, int, int, int]) -> tuple[dict[str, Any], Image.Image, Image.Image]:
    """Measure lost components and geometry, without dilation or inference.

    Round-trip IoU compares binary mask geometry, not restoration quality.
    The disappeared-pixel fraction counts only whole components with no sampled
    pixel; it is distinct from all boundary changes caused by resizing.
    """
    binary = validate_binary_damage_mask(mask, content_box=content_box)
    audit = audit_inference_mask(mask, content_box=content_box)
    labels, _ = label(binary, structure=np.ones((3, 3), dtype=np.uint8))
    lost = np.isin(labels, audit["disappeared_component_ids"])
    reduced = mask.resize((512, 512), Image.Resampling.NEAREST)
    returned = np.asarray(reduced.resize(mask.size, Image.Resampling.NEAREST)) == 255
    content = Image.new("L", mask.size, 0)
    content.paste(255, content_box)
    reduced_content = np.asarray(content.resize(reduced.size, Image.Resampling.NEAREST)) == 255
    reduced_binary = np.asarray(reduced) == 255
    x0, y0, x1, y1 = content_box
    source_fraction = float(binary.sum() / ((x1 - x0) * (y1 - y0)))
    inference_fraction = float(reduced_binary.sum() / reduced_content.sum())
    audit.update({
        "source_content_fraction": source_fraction,
        "inference_content_fraction": inference_fraction,
        "content_fraction_change_percentage_points": 100 * (inference_fraction - source_fraction),
        "disappeared_source_pixels": int(lost.sum()),
        "disappeared_source_pixel_fraction": float(lost.sum() / binary.sum()),
        "roundtrip_removed_source_pixels": int((binary & ~returned).sum()),
        "roundtrip_added_pixels": int((~binary & returned).sum()),
        "inference_padding_overlap_pixels": int((reduced_binary & ~reduced_content).sum()),
        "scale_review_status": "pending", "sd_eligibility_status": "not_assessed",
    })
    return audit, reduced, Image.fromarray(lost.astype(np.uint8) * 255)


def scale_review_figure(image: Image.Image, mask: Image.Image, reduced: Image.Image,
                        lost: Image.Image, *, painting_id: str, audit: Mapping[str, Any]) -> bytes:
    """One full-view row and one shared zoom for source and resized masks."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    source = np.asarray(mask) == 255
    roundtrip = np.asarray(reduced.resize(image.size, Image.Resampling.NEAREST)) == 255
    lost_binary = np.asarray(lost) == 255
    # RGB resizing matches the existing SD helper. Upsampling is display only.
    display_image = image.resize((512, 512), Image.Resampling.LANCZOS).resize(image.size, Image.Resampling.NEAREST)
    panels = []
    for base, selected, colour in ((image, source, (255, 35, 65)),
                                    (display_image, roundtrip, (255, 35, 65)),
                                    (image, lost_binary, (255, 155, 0))):
        rgb = np.asarray(base).astype(float)
        rgb[selected] = .32 * rgb[selected] + .68 * np.asarray(colour)
        panels.append(rgb.astype(np.uint8))
    # Select a repeatable 192-pixel tile with the most lost-component pixels,
    # or the most source-mask pixels if no component disappears.
    focus = lost_binary if lost_binary.any() else source
    coordinates = [(x, y) for y in range(0, 768, 192) for x in range(0, 768, 192)]
    x, y = max(coordinates, key=lambda xy: int(focus[xy[1]:xy[1]+192, xy[0]:xy[0]+192].sum()))
    figure = Figure(figsize=(12, 9), dpi=130)
    FigureCanvasAgg(figure)
    axes = figure.subplots(2, 3)
    titles = ("768 px: selected repair mask", "512 px: nearest-neighbour mask", "Whole components lost at 512 px")
    for col, panel in enumerate(panels):
        axes[0, col].imshow(panel)
        axes[0, col].set_title(titles[col], fontsize=10)
        axes[1, col].imshow(panel[y:y+192, x:x+192], interpolation="nearest")
        axes[1, col].set_title(f"Same detail: x={x}:{x+192}, y={y}:{y+192}", fontsize=9)
    for axis in axes.flat:
        axis.axis("off")
    figure.suptitle(
        f"D03 | {painting_id} | 512-pixel mask review pending\n"
        f"Lost components: {audit['disappeared_component_count']} / {audit['source_component_count']}"
        f" | selected source pixels in these components: {audit['disappeared_source_pixel_fraction']:.2%}\n"
        f"Mask round-trip IoU: {audit['roundtrip_iou']:.4f} (geometry, not restoration quality)", fontsize=12)
    figure.subplots_adjust(left=.03, right=.97, bottom=.07, top=.84, hspace=.24, wspace=.12)
    figure.text(.5, .01, "Red = repair target. Orange = wholly lost components; other resizing changes are not coloured orange.", ha="center", fontsize=9)
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", facecolor="white")
    return buffer.getvalue()


def review_real_damage_masks(project_root: str | Path, config: Mapping[str, Any],
                             preprocessed_images: pd.DataFrame, mask_candidates: pd.DataFrame, *,
                             previous_validation: ValidationCollector,
                             progress_callback: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """Validate saved Batch 4, bind human approval and save review checkpoints.

    All bindings and existing targets are checked before the first write.
    Canonical masks/tables and model eligibility belong to later D03 batches.
    Repeated execution reuses identical files; edited evidence is not replaced.
    """
    started = perf_counter()
    root = Path(project_root).resolve()
    validate_real_damage_config(config)
    prior = [c for c in previous_validation.checks if c.validation_stage == PREPARATION_STAGE]
    _require(bool(prior) and all(c.passed for c in previous_validation.checks), "Successful Batch 4 validation is required")
    collector = ValidationCollector()
    collector.extend(c for c in previous_validation.checks if c.validation_stage != REVIEW_STAGE)
    output = notebook_output_root(NOTEBOOK_STEM, root)
    work = require_notebook_output_path(output / REVIEW_WORK_DIRECTORY, NOTEBOOK_STEM, root)
    decision_path = resolve_repo_path(config["inputs"]["mask_review_decisions"], root)
    decisions = json.loads(decision_path.read_text(encoding="utf-8"))
    ids = config["dataset"]["painting_ids"]
    _require(decisions.get("schema_version") == "real_damage_mask_review_decisions.v1", "Wrong review-decision schema")
    _require(decisions.get("dataset_version") == config["dataset"]["dataset_version"], "Review cohort changed")
    _require(decisions.get("review_basis") == "user_accepted_saved_batch_4_previews_in_chat"
             and decisions.get("scale_review_status") == "pending"
             and decisions.get("accepted_partial_repair_scope") is True, "Review scope is not the approved Batch 4 scope")
    for frame in (preprocessed_images, mask_candidates):
        _require(frame["painting_id"].tolist() == ids, "Batch 4 rows are incomplete, duplicated or out of order")
    _require([r["painting_id"] for r in decisions["records"]] == ids, "Review decisions do not cover the ten inputs")
    candidate_dir = output / config["preparation"]["candidate_directory"]
    for name, frame, key in (("preprocessed_images", preprocessed_images, "preprocessing_checkpoint"),
                              ("mask_candidates", mask_candidates, "candidate_table")):
        path = candidate_dir / config["preparation"][key]
        _require(sha256_file(path) == decisions["batch_4_checkpoint_sha256"][name], f"Saved Batch 4 checkpoint changed: {name}")
        saved = pd.read_csv(path)
        # Compare through CSV round trip to handle booleans, floats and empty values.
        pd.testing.assert_frame_equal(saved, pd.read_csv(io.StringIO(frame.to_csv(index=False))),
                                      check_dtype=False, check_exact=False, rtol=1e-12, atol=1e-12)

    def check(identifier: str, description: str, passed: bool, observed: Any, expected: Any = True) -> None:
        collector.add(validation_stage=REVIEW_STAGE, check_id=identifier,
                      check_description=description, severity="blocking", expected=expected,
                      observed=observed, passed=passed)

    check("checkpoint_bindings", "Saved Batch 4 tables match the review and in-memory tables", True, "matched")
    review_rows, audit_rows, prepared = [], [], []
    for geometry, candidate, decision in zip(preprocessed_images.to_dict("records"), mask_candidates.to_dict("records"), decisions["records"]):
        pid = geometry["painting_id"]
        input_path = resolve_repo_path(candidate["input_path"], root)
        mask_path = resolve_repo_path(candidate["candidate_mask_path"], root)
        _require(candidate["input_path"] == geometry["processed_path"]
                 and candidate["input_sha256"] == geometry["sha256"] == decision["input_sha256"]
                 and candidate["mask_sha256"] == decision["mask_sha256"], f"Review binding differs: {pid}")
        _require(candidate["review_status"] == "pending" and not candidate["candidate_is_final"], "Batch 4 candidate status changed")
        review = dict(candidate, schema_version=config["schemas"]["mask_review"],
                      review_status=decision["review_status"], reviewer=decisions["reviewer"],
                      reviewed_at_utc=decisions["recorded_at_utc"], review_basis=decisions["review_basis"],
                      review_timestamp_basis="time_existing_chat_approval_was_recorded",
                      review_scope="selected_repair_targets_only", scale_review_status="pending",
                      all_visible_damage_covered=False, review_decisions_sha256=sha256_file(decision_path))
        validate_review_binding(review, input_path=input_path, mask_path=mask_path)
        check(f"approval_binding:{pid}", "Human approval is bound to the exact input and mask bytes", True, decision["review_status"])
        with Image.open(input_path) as source, Image.open(mask_path) as stored:
            _require(source.mode == "RGB" and source.size == (768, 768) and source.format == "PNG", f"Input format changed: {pid}")
            _require(stored.mode == "L" and stored.format == "PNG", f"Mask format changed: {pid}")
            image, mask = source.copy(), stored.copy()
        box = tuple(int(geometry[k]) for k in ("content_x_min", "content_y_min", "content_x_max", "content_y_max"))
        binary = validate_binary_damage_mask(mask, content_box=box)
        area = (box[2] - box[0]) * (box[3] - box[1])
        _require(area == int(geometry["content_area_pixels"]), f"Content bounds changed: {pid}")
        check(f"canonical_geometry:{pid}", "Nonempty binary mask excludes padding and retains its selected coverage",
              int(binary.sum()) == int(candidate["mask_pixel_count"]) and np.isclose(binary.sum()/area, candidate["mask_fraction_content"], atol=1e-12, rtol=0), int(binary.sum()), int(candidate["mask_pixel_count"]))
        audit, reduced, lost = inference_scale_evidence(mask, content_box=box)
        audit = dict(audit, schema_version=config["schemas"]["inference_mask_audit"], painting_id=pid,
                     mask_id=candidate["mask_id"], input_sha256=geometry["sha256"], mask_sha256=candidate["mask_sha256"],
                     inference_mask_path=to_repo_relative(work / "masks_512" / f"{pid}.png", root),
                     lost_component_mask_path=to_repo_relative(work / "lost_components_768" / f"{pid}.png", root),
                     preview_path=to_repo_relative(work / "previews" / f"{pid}.png", root))
        audit["disappeared_component_ids"] = json.dumps(audit["disappeared_component_ids"])
        check(f"inference_geometry:{pid}", "Exact nearest resize remains binary and excludes resized padding",
              reduced.size == (512, 512) and set(np.unique(reduced)).issubset({0, 255}) and audit["inference_padding_overlap_pixels"] == 0,
              [*reduced.size, audit["inference_padding_overlap_pixels"]], [512, 512, 0])
        check(f"scale_review_pending:{pid}", "Scale effects are measured without granting SD eligibility",
              audit["scale_review_status"] == "pending" and audit["sd_eligibility_status"] == "not_assessed" and not audit["sd_eligible_without_review"], "pending")
        payloads = {work / "masks_512" / f"{pid}.png": _png_bytes(reduced),
                    work / "lost_components_768" / f"{pid}.png": _png_bytes(lost),
                    work / "previews" / f"{pid}.png": scale_review_figure(image, mask, reduced, lost, painting_id=pid, audit=audit)}
        audit["inference_mask_sha256"] = hashlib.sha256(payloads[work / "masks_512" / f"{pid}.png"]).hexdigest()
        review_rows.append(review)
        audit_rows.append(audit)
        prepared.append((pid, payloads))
        if progress_callback:
            progress_callback({"painting_id": pid, "completed": len(prepared), "total": len(ids), "phase": "validated", "elapsed_seconds": perf_counter()-started})
    collector.raise_for_blocking()
    reviews, audits = pd.DataFrame(review_rows), pd.DataFrame(audit_rows)
    payloads = {path: content for _, group in prepared for path, content in group.items()}
    payloads[work / "mask_review.csv"] = reviews.to_csv(index=False, lineterminator="\n").encode("utf-8")
    payloads[work / "inference_mask_audit.csv"] = audits.to_csv(index=False, lineterminator="\n").encode("utf-8")
    binding = {"schema_version": "real_damage_mask_review_checkpoint.v1", "helper_version": REAL_DAMAGE_REVIEW_MODULE_VERSION,
               "helper_sha256": sha256_file(Path(__file__)),
               "config_content_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest(),
               "dataset_version": config["dataset"]["dataset_version"], "decisions_sha256": sha256_file(decision_path),
               "batch_4_checkpoint_sha256": decisions["batch_4_checkpoint_sha256"],
               "mask_review_status": "approved_at_768", "scale_review_status": "pending",
               "model_eligibility_status": "not_assessed"}
    payloads[work / "review_checkpoint.json"] = (json.dumps(binding, indent=2) + "\n").encode("utf-8")
    expected = set(payloads)
    existing = {p for p in work.rglob("*") if p.is_file()} if work.exists() else set()
    _require(existing <= expected, "Unexpected mask-review files are retained for review")
    for path, content in payloads.items():
        require_notebook_output_path(path, NOTEBOOK_STEM, root)
        _require(not path.exists() or path.read_bytes() == content, f"Existing mask-review file differs; retained: {path}")
    for path, content in payloads.items():
        _atomic_write(path, content)
    check("checkpoint_files", "Exact review file set is saved without altering Batch 4", {p for p in work.rglob('*') if p.is_file()} == expected, len(expected), 33)
    check("review_population", "Ten approved 768 masks retain ten pending inference-scale reviews", reviews["review_status"].isin(["approved", "approved_with_ambiguity"]).all() and audits["scale_review_status"].eq("pending").all(), len(reviews), len(ids))
    collector.raise_for_blocking()
    return {"validation": collector, "mask_review": reviews, "inference_mask_audit": audits,
            "work_root": work, "review_checkpoint_path": work / "review_checkpoint.json",
            "elapsed_seconds": perf_counter()-started, "scale_review_status": "pending"}
