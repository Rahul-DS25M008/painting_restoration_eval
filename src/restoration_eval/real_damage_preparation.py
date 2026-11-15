"""D03 full preprocessing and assistant-prepared mask candidates.

These masks are proposed repair targets, not labels of all physical damage.
Preparation never grants review approval or starts restoration inference.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from scipy.ndimage import grey_closing, grey_opening, label

from .manifests import sha256_file
from .paths import notebook_output_root, require_notebook_output_path, resolve_repo_path, to_repo_relative
from .preprocessing import build_preprocessed_image, load_preprocessing_config
from .real_damage_dataset import (
    NOTEBOOK_STEM, SMOKE_STAGE, _require, validate_approved_sources,
    validate_binary_damage_mask, validate_real_damage_config, load_real_damage_config,
    load_approved_sources, resolve_real_damage_paths, validate_real_damage_preflight,
    normalize_real_damage_source, _relative,
)
from .schemas import PREPROCESSED_IMAGES_SCHEMA, validate_dataframe
from .validation import ValidationCollector

REAL_DAMAGE_PREPARATION_MODULE_VERSION = "1.1.1"
PREPARATION_STAGE = "batch_4_preprocessing_and_mask_candidates"
RECIPE_SCHEMA = "real_damage_annotation_recipe.v1"


def refresh_preparation_context(
    project_root: str | Path, config_path: str | Path, *,
    previous_config: Mapping[str, Any], previous_input_checksums: Mapping[str, str],
    previous_validation: ValidationCollector,
) -> dict[str, Any]:
    """Refresh additive configuration/inventory without restarting the kernel.

    Earlier source/smoke evidence is retained only if its scientific inputs and
    policies are unchanged. An upstream change requires rerunning its producer.
    """
    root = Path(project_root).resolve()
    config = load_real_damage_config(config_path)
    for section in ("dataset", "preprocessing", "annotation", "downstream", "schemas", "outputs", "smoke", "execution"):
        _require(config[section] == previous_config[section], f"Earlier batch policy changed ({section}); rerun the affected batches")
    catalog = load_approved_sources(resolve_repo_path(config["inputs"]["approved_sources"], root), config)
    inputs, outputs = resolve_real_damage_paths(root, config, catalog, config_path=Path(config_path))
    # This producer's helper is first used in Batch 4. Earlier source/smoke
    # results depend on real_damage_dataset and preprocessing, still protected.
    refreshable = {"d03_config", "inventory", "inventory_run", "evidence_audit", "notebook_roadmap",
                   "helper_sources.real_damage_preparation"}
    for key, digest in previous_input_checksums.items():
        if key not in refreshable:
            _require(key in inputs and inputs[key].is_file() and sha256_file(inputs[key]) == digest,
                     f"Earlier scientific input changed ({key}); rerun the affected batches")
    preflight = validate_real_damage_preflight(root, config, catalog, inputs, outputs,
                                             previous_validation=previous_validation)
    preflight["validation"].raise_for_blocking()
    return {"config": config, "catalog": catalog, "inputs": inputs, "outputs": outputs, **preflight}


def load_annotation_recipe(path: str | Path, config: Mapping[str, Any],
                           catalog: Mapping[str, Any]) -> dict[str, Any]:
    recipe = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    _require(recipe.get("schema_version") == RECIPE_SCHEMA, "Wrong annotation recipe schema")
    _require(recipe.get("coordinate_space") == "preprocessed_768_canvas", "Wrong annotation coordinate space")
    _require(recipe.get("automatic_dilation") is False and recipe.get("all_visible_damage_covered") is False,
             "Candidate recipe cannot broaden masks or claim exhaustive damage annotation")
    rows = recipe.get("records", [])
    _require([r.get("painting_id") for r in rows] == config["dataset"]["painting_ids"], "Recipe must contain the ten approved paintings")
    approved = {r["painting_id"]: r for r in catalog["records"]}
    for row in rows:
        pid = row["painting_id"]
        _require(row.get("source_sha256") == approved[pid]["raw_sha256"], f"Recipe source hash differs: {pid}")
        _require(row.get("review_status") == "pending", "A recipe is not a review approval")
        _require(bool(row.get("target_description")) and bool(row.get("selection_notes")), f"Missing target interpretation: {pid}")
        _require(isinstance(row.get("regions"), list) and bool(row["regions"]), f"Missing selected regions: {pid}")
        if row.get("reviewed_mask_path"):
            _require(row["reviewed_mask_path"] == approved[pid].get("reviewed_mask_path")
                     and row.get("reviewed_mask_sha256") == approved[pid].get("reviewed_mask_sha256"),
                     f"Reviewed raster differs from approved catalog: {pid}")
    return recipe


def build_assisted_damage_mask(image: Image.Image, record: Mapping[str, Any], *,
                               content_box: tuple[int, int, int, int],
                               project_root: str | Path | None = None) -> Image.Image:
    """Apply explicit polygons and optional pixel selectors, with no dilation.

    Polygons limit the selection; local-contrast and colour rules select pixels
    inside them. Small-component filtering only removes pixels. Source pixels
    are never modified. Region-specific thresholds are saved in the recipe.
    """
    _require(image.mode == "RGB" and image.size == (768, 768), "Candidate masks require the unchanged 768 RGB input")
    if record.get("reviewed_mask_path"):
        _require(project_root is not None, "Reviewed raster requires a project root")
        path = resolve_repo_path(_relative(record["reviewed_mask_path"]), Path(project_root).resolve())
        _require(sha256_file(path) == record["reviewed_mask_sha256"], "Reviewed raster checksum changed")
        with Image.open(path) as stored:
            _require(stored.format == "PNG" and stored.size == image.size, "Reviewed raster must be a 768 PNG")
            result = stored.copy()
        validate_binary_damage_mask(result, content_box=content_box)
        return result
    rgb = np.asarray(image).astype(np.float32)
    red, green, blue = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    selected = np.zeros((768, 768), dtype=bool)
    for region in record["regions"]:
        points = region["polygon_xy"]
        _require(len(points) >= 3 and all(len(p) == 2 and all(type(v) is int and 0 <= v < 768 for v in p) for p in points), "Invalid 768-canvas polygon")
        support_image = Image.new("L", (768, 768), 0)
        ImageDraw.Draw(support_image).polygon([tuple(p) for p in points], fill=255)
        candidate = np.asarray(support_image) > 0
        selector = region["selector"]
        _require(selector in {"polygon", "colour", "bright_ridge", "dark_ridge"}, "Unsupported candidate selector")
        if selector == "colour":
            fields = {"r_min": red, "g_min": green, "b_min": blue,
                      "r_minus_b_min": red - blue, "r_minus_g_min": red - green}
            for key, values in fields.items():
                if key in region:
                    candidate &= values >= float(region[key])
        elif selector in {"bright_ridge", "dark_ridge"}:
            window = region["window"]
            _require(type(window) is int and 3 <= window <= 15 and window % 2 == 1, "Local-contrast window must be odd and bounded")
            _require(float(region["contrast_min"]) > 0, "Contrast threshold must be positive")
            contrast = (luminance - grey_opening(luminance, size=window)) if selector == "bright_ridge" else (grey_closing(luminance, size=window) - luminance)
            candidate &= contrast >= float(region["contrast_min"])
            candidate &= luminance >= float(region.get("luma_min", 0))
            candidate &= luminance <= float(region.get("luma_max", 255))
        minimum = region.get("min_component_pixels", 1)
        _require(type(minimum) is int and minimum >= 1, "Invalid minimum component size")
        if minimum > 1:
            components, _ = label(candidate, structure=np.ones((3, 3), dtype=np.uint8))
            counts = np.bincount(components.ravel())
            keep = counts >= minimum
            keep[0] = False
            candidate &= keep[components]
        selected |= candidate
    result = Image.fromarray(selected.astype(np.uint8) * 255)
    validate_binary_damage_mask(result, content_box=content_box)
    return result


def _png_bytes(image: Image.Image, *, compress_level: int = 6, optimize: bool = False) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", compress_level=compress_level, optimize=optimize)
    return buffer.getvalue()


def _atomic_write(path: Path, payload: bytes, *, protect_existing: bool = True) -> None:
    if path.exists():
        _require(path.is_file(), f"Expected a file: {path}")
        if path.read_bytes() == payload:
            return
        _require(not protect_existing, f"Existing file differs; retained for review: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def candidate_review_preview(image: Image.Image, mask: Image.Image, record: Mapping[str, Any]) -> bytes:
    """Full input and overlay, followed by one close-up pair per selected region."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    array = np.asarray(image)
    overlay = array.astype(float).copy()
    target = np.asarray(mask) == 255
    overlay[target] = 0.55 * overlay[target] + 0.45 * np.array([255, 20, 60])
    overlay = overlay.astype(np.uint8)
    regions = record["regions"]
    figure_height = 3.5 * (len(regions) + 1) + 0.6
    figure = Figure(figsize=(10, figure_height), dpi=120, facecolor="white")
    FigureCanvasAgg(figure)
    axes = figure.subplots(len(regions) + 1, 2, squeeze=False)
    figure.subplots_adjust(left=0.035, right=0.965, bottom=0.025, top=1 - 1.05 / figure_height, hspace=0.23, wspace=0.12)
    figure.suptitle(f"{record['painting_id']} | Candidate repair mask — review pending\nOriginal input / red overlay: selected pixels, not all physical damage", fontsize=11)
    for index, pair in enumerate(axes):
        pair[0].imshow(array)
        pair[1].imshow(overlay)
        for axis in pair:
            axis.set_axis_off()
        if index == 0:
            pair[0].set_title("Full 768-pixel input", fontsize=10)
            pair[1].set_title(f"Candidate: {int(target.sum()):,} pixels", fontsize=10)
        else:
            points = np.asarray(regions[index - 1]["polygon_xy"])
            x0, y0 = np.maximum(points.min(axis=0) - 8, 0)
            x1, y1 = np.minimum(points.max(axis=0) + 8, 767)
            for axis in pair:
                axis.set_xlim(x0 - 0.5, x1 + 0.5)
                axis.set_ylim(y1 + 0.5, y0 - 0.5)
            pair[0].set_title(f"Target {index}: input close-up", fontsize=10)
            pair[1].set_title("Same close-up with candidate overlay", fontsize=10)
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=120)
    figure.clear()
    return buffer.getvalue()


def _candidate_atlas(images: list[Image.Image], masks: list[Image.Image], rows: list[dict[str, Any]]) -> bytes:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(12, 5.8), dpi=150, facecolor="white")
    FigureCanvasAgg(figure)
    axes = figure.subplots(2, 5)
    figure.subplots_adjust(left=0.015, right=0.985, bottom=0.035, top=0.85, wspace=0.09, hspace=0.23)
    figure.suptitle("D03 | Ten candidate repair masks — review pending\nRed marks selected reconstruction pixels; other physical damage may remain outside these targets.", fontsize=11)
    for axis, image, mask, row in zip(axes.flat, images, masks, rows):
        overlay = np.asarray(image).astype(float).copy()
        selected = np.asarray(mask) == 255
        overlay[selected] = 0.45 * overlay[selected] + 0.55 * np.array([255, 20, 60])
        axis.imshow(overlay.astype(np.uint8))
        axis.set_title(f"{row['painting_id']} | {row['mask_pixel_count']:,} px\n{row['mask_fraction_content']:.3%} of content", fontsize=9)
        axis.set_axis_off()
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=150)
    figure.clear()
    return buffer.getvalue()


def prepare_real_damage_inputs(
    project_root: str | Path, config: Mapping[str, Any], catalog: Mapping[str, Any],
    artworks: pd.DataFrame, preprocessing_config: Mapping[str, Any], smoke_images: pd.DataFrame, *,
    previous_validation: ValidationCollector,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Prepare all ten unchanged-pipeline inputs and pending mask candidates.

    Writes input PNGs to images/inputs and all candidate/checkpoint material to
    work/annotation_candidates. Canonical masks, review approvals, registry and
    eligibility records are reserved for subsequent batches. No model is loaded.
    """
    started = perf_counter()
    root = Path(project_root).resolve()
    validate_real_damage_config(config)
    validate_approved_sources(catalog, config)
    collector = ValidationCollector()
    collector.extend(c for c in previous_validation.checks if c.validation_stage != PREPARATION_STAGE)
    _require(collector.overall_passed and any(c.validation_stage == SMOKE_STAGE for c in collector.checks), "Pass Batch 3 before full preparation")
    _require(len(artworks) == 10 and artworks["painting_id"].is_unique
             and set(artworks["painting_id"]) == set(config["dataset"]["painting_ids"])
             and artworks["acceptance_status"].eq("accepted").all(), "Expected ten accepted source records")
    _require(artworks["has_clean_reference"].eq(False).all() and artworks["clean_image_path"].isna().all(), "Real damaged inputs cannot be clean references")
    _require(len(smoke_images) == 5 and smoke_images["painting_id"].is_unique
             and set(smoke_images["painting_id"]) == set(config["execution"]["smoke_painting_ids"]), "Invalid Batch 3 smoke handoff")
    smoke_by_id = smoke_images.set_index("painting_id").to_dict("index")
    prep_path = resolve_repo_path(config["inputs"]["preprocessing_config"], root)
    _require(preprocessing_config == load_preprocessing_config(prep_path), "Preprocessing policy changed since Batch 2")
    for rel in (config["inputs"]["preprocessing_config"], "src/restoration_eval/preprocessing.py"):
        _require(sha256_file(resolve_repo_path(rel, root)) == catalog["pipeline_baseline_sha256"][rel], f"Preprocessing baseline changed: {rel}")
    contract = config["preparation"]
    expected = {
        "candidate_directory": "work/annotation_candidates", "candidate_mask_template": "masks/{painting_id}.png",
        "candidate_preview_template": "previews/{painting_id}.png", "candidate_table": "candidate_masks.csv",
        "preprocessing_checkpoint": "preprocessed_images.csv", "candidate_atlas": "mask_candidates_atlas.png",
        "recipe_snapshot": "annotation_recipe.json", "candidate_masks_are_final": False,
        "user_drawing_required": False, "human_review_required_before_inference": True,
        "prior_visual_review": contract.get("prior_visual_review"),
    }
    _require(contract.get("prior_visual_review") in {
        "user_accepted_batch_3_previews_in_chat",
        "user_accepted_revised_ten_2026-11-15; canonical_preprocessing_and_scale_checks_pending_rerun",
    }, "Missing recorded source/target visual review")
    _require(contract == expected, "Preparation output/review contract changed")
    _require(config["outputs"]["processed_image_template"] == "images/inputs/{painting_id}.png", "Unexpected canonical input location")
    output_root = notebook_output_root(NOTEBOOK_STEM, root)

    def target(relative: str) -> Path:
        path = require_notebook_output_path(output_root / relative, NOTEBOOK_STEM, root)
        _require(path == (root / "outputs" / NOTEBOOK_STEM / relative).absolute(), "Output path redirects through a link")
        return path

    work_relative = contract["candidate_directory"]
    work = target(work_relative)
    input_targets = {pid: target(f"images/inputs/{pid}.png") for pid in config["dataset"]["painting_ids"]}
    mask_targets = {pid: target(f"{work_relative}/masks/{pid}.png") for pid in input_targets}
    preview_targets = {pid: target(f"{work_relative}/previews/{pid}.png") for pid in input_targets}
    auxiliary = {key: target(f"{work_relative}/{contract[key]}") for key in
                 ("candidate_table", "preprocessing_checkpoint", "candidate_atlas", "recipe_snapshot")}
    expected_work_files = set(mask_targets.values()) | set(preview_targets.values()) | set(auxiliary.values())
    for folder, allowed in ((output_root / "images/inputs", set(input_targets.values())), (work, expected_work_files)):
        unexpected = [str(p) for p in folder.rglob("*") if p.is_file() and p.resolve() not in allowed] if folder.exists() else []
        _require(not unexpected, f"Unexpected preparation files retained for review: {unexpected}")
    recipe_path = resolve_repo_path(config["inputs"]["annotation_recipe"], root)
    recipe = load_annotation_recipe(recipe_path, config, catalog)
    recipe_bytes = recipe_path.read_bytes()
    recipe_hash = sha256_file(recipe_path)
    recipe_by_id = {r["painting_id"]: r for r in recipe["records"]}
    source_by_id = {r["painting_id"]: r for r in catalog["records"]}
    selected = artworks.set_index("painting_id", drop=False).loc[config["dataset"]["painting_ids"]]

    def check(identifier: str, description: str, passed: bool, observed: Any, expected_value: Any = True) -> None:
        collector.add(validation_stage=PREPARATION_STAGE, check_id=identifier,
                      check_description=description, severity="blocking", expected=expected_value,
                      observed=observed, passed=passed)

    check("population", "Ten accepted real-damage inputs; no clean references", True, 10, 10)
    check("preprocessing_policy", "Existing N02 preprocessing and user-accepted smoke policy retained", True, "unchanged")
    check("recipe", "Ten hash-bound candidate recipes, all pending review", True, recipe_hash)
    # Construct and validate all candidates before writing any output.
    prepared = []
    for source in selected.to_dict("records"):
        pid = source["painting_id"]
        for field in ("raw_image_path", "raw_sha256", "raw_width", "raw_height", "category"):
            _require(source[field] == source_by_id[pid][field], f"Stale artwork record: {pid}/{field}")
        source_path = resolve_repo_path(source["raw_image_path"], root)
        raw = source_path.read_bytes()
        _require(hashlib.sha256(raw).hexdigest() == source["raw_sha256"], f"Source changed: {pid}")
        with Image.open(io.BytesIO(raw)) as original:
            original.load()
            canvas, geometry = build_preprocessed_image(normalize_real_damage_source(original), source, preprocessing_config)
        processing = preprocessing_config["processing"]
        encoded = _png_bytes(canvas, compress_level=int(processing["png_compress_level"]), optimize=bool(processing["png_optimize"]))
        image_hash = hashlib.sha256(encoded).hexdigest()
        rec = recipe_by_id[pid]
        _require(image_hash == rec["processed_sha256"], f"Candidate coordinates are bound to a different processed image: {pid}")
        if pid in smoke_by_id:
            smoke = smoke_by_id[pid]
            _require(smoke["sha256"] == image_hash and sha256_file(resolve_repo_path(smoke["processed_path"], root)) == image_hash,
                     f"Smoke image changed or differs from full preprocessing: {pid}")
        box = tuple(int(geometry[k]) for k in ("content_x_min", "content_y_min", "content_x_max", "content_y_max"))
        candidate = build_assisted_damage_mask(canvas, rec, content_box=box, project_root=root)
        mask_bytes = _png_bytes(candidate)
        mask_hash = hashlib.sha256(mask_bytes).hexdigest()
        image_row = {
            "schema_version": config["schemas"]["preprocessed_images"],
            **{key: source[key] for key in ("dataset_id", "dataset_version", "dataset_scope", "painting_id", "dataset_sort_index", "category")},
            "processed_image_id": f"input_{pid}", "source_path": source["raw_image_path"],
            "source_sha256": source["raw_sha256"], "processed_filename": input_targets[pid].name,
            "processed_path": to_repo_relative(input_targets[pid], root), **geometry,
            "size_bytes": len(encoded), "sha256": image_hash, "status": "passed",
            "has_clean_reference": False, "clean_image_path": None,
            "preprocessing_config_sha256": sha256_file(prep_path),
        }
        count = int(np.count_nonzero(np.asarray(candidate)))
        candidate_row = {
            "schema_version": "real_damage_mask_candidates.v1", "painting_id": pid,
            "mask_id": f"rdmask_{pid}", "dataset_scope": config["dataset"]["dataset_scope"],
            "input_path": image_row["processed_path"], "input_sha256": image_hash,
            "candidate_mask_path": to_repo_relative(mask_targets[pid], root), "mask_sha256": mask_hash,
            "mask_mode": "L", "mask_width": 768, "mask_height": 768,
            "mask_pixel_count": count, "mask_fraction_content": count / geometry["content_area_pixels"],
            "annotation_method": recipe["annotation_method"], "prepared_by": recipe["prepared_by"],
            "recipe_sha256": recipe_hash, "recipe_version": recipe["recipe_version"],
            "target_description": rec["target_description"], "selection_notes": rec["selection_notes"],
            "review_status": "pending", "reviewer": "", "reviewed_at_utc": "",
            "candidate_is_final": False, "all_visible_damage_covered": False,
            "preview_path": to_repo_relative(preview_targets[pid], root),
        }
        for path, payload in ((input_targets[pid], encoded), (mask_targets[pid], mask_bytes), (auxiliary["recipe_snapshot"], recipe_bytes)):
            _require(not path.exists() or (path.is_file() and path.read_bytes() == payload), f"Existing file differs; retained for review: {path}")
        prepared.append((source_path, canvas, candidate, rec, image_row, candidate_row, encoded, mask_bytes))

    images, candidates, canvases, masks = [], [], [], []
    for number, (source_path, canvas, candidate, rec, image_row, candidate_row, encoded, mask_bytes) in enumerate(prepared, 1):
        pid = image_row["painting_id"]
        image_path, mask_path = input_targets[pid], mask_targets[pid]
        reused = image_path.is_file() and mask_path.is_file()
        _atomic_write(image_path, encoded)
        _atomic_write(mask_path, mask_bytes)
        with Image.open(image_path) as saved:
            saved.load()
            array = np.asarray(saved)
            image_ok = saved.size == (768, 768) and saved.mode == "RGB" and saved.format == "PNG" and not saved.info.get("icc_profile") and not saved.getexif()
        check(f"input:{pid}", "Reloaded input format, hash and pixels match unchanged preprocessing", image_ok and sha256_file(image_path) == image_row["sha256"] and np.array_equal(array, np.asarray(canvas)), sha256_file(image_path), image_row["sha256"])
        x0, y0, x1, y1 = [int(image_row[k]) for k in ("content_x_min", "content_y_min", "content_x_max", "content_y_max")]
        outside = np.ones((768, 768), dtype=bool)
        outside[y0:y1, x0:x1] = False
        pad_colour = [image_row[f"padding_color_{c}"] for c in "rgb"]
        geometry_ok = (0 <= x0 < x1 <= 768 and 0 <= y0 < y1 <= 768
                       and (x1 - x0, y1 - y0) == (image_row["resized_width"], image_row["resized_height"])
                       and (x0, y0, 768 - x1, 768 - y1) == (image_row["pad_left"], image_row["pad_top"], image_row["pad_right"], image_row["pad_bottom"])
                       and (x1 - x0) * (y1 - y0) == image_row["content_area_pixels"]
                       and int(outside.sum()) == image_row["padding_area_pixels"]
                       and bool(np.all(array[outside] == pad_colour)))
        check(f"geometry:{pid}", "Content bounds and median-colour padding reconcile", geometry_ok, [x0, y0, x1, y1])
        with Image.open(mask_path) as saved_mask:
            saved_mask.load()
            binary = validate_binary_damage_mask(saved_mask, content_box=(x0, y0, x1, y1))
            mask_ok = saved_mask.format == "PNG" and np.array_equal(np.asarray(saved_mask), np.asarray(candidate))
        check(f"candidate:{pid}", "Reloaded candidate is nonempty, binary, inside content and hash-matched", mask_ok and sha256_file(mask_path) == candidate_row["mask_sha256"] and int(binary.sum()) == candidate_row["mask_pixel_count"], int(binary.sum()), candidate_row["mask_pixel_count"])
        check(f"source:{pid}", "Original photograph is unchanged", sha256_file(source_path) == image_row["source_sha256"], sha256_file(source_path), image_row["source_sha256"])
        _atomic_write(preview_targets[pid], candidate_review_preview(canvas, candidate, rec), protect_existing=False)
        with Image.open(preview_targets[pid]) as preview:
            preview.verify()
        check(f"preview:{pid}", "Candidate review sheet saved and decodes", True, to_repo_relative(preview_targets[pid], root))
        if pid in smoke_by_id:
            check(f"smoke:{pid}", "Full input is byte-identical to the accepted Batch 3 smoke image", image_row["sha256"] == smoke_by_id[pid]["sha256"], image_row["sha256"], smoke_by_id[pid]["sha256"])
        images.append(image_row); candidates.append(candidate_row); canvases.append(canvas); masks.append(candidate)
        if progress_callback:
            elapsed = perf_counter() - started
            progress_callback({"completed": number, "total": 10, "percentage": number * 10,
                               "painting_id": pid, "elapsed_seconds": elapsed,
                               "throughput_per_second": number / elapsed, "reused": reused})

    image_table, candidate_table = pd.DataFrame(images), pd.DataFrame(candidates)
    schema = validate_dataframe(image_table, PREPROCESSED_IMAGES_SCHEMA)
    check("preprocessing_schema", "Preprocessing handoff retains the existing common columns and types", schema.passed, schema.to_dict())
    check("image_count", "Ten unique processed inputs", len(image_table) == 10 and image_table["sha256"].is_unique, len(image_table), 10)
    check("candidate_count", "Ten distinct candidate masks, one per input", len(candidate_table) == 10 and candidate_table["painting_id"].is_unique and candidate_table["mask_id"].is_unique, len(candidate_table), 10)
    check("review_pending", "Candidates grant no final mask approval or clean reference", candidate_table["review_status"].eq("pending").all() and candidate_table["candidate_is_final"].eq(False).all() and image_table["clean_image_path"].isna().all(), "pending user review")
    if collector.overall_passed:
        _atomic_write(auxiliary["recipe_snapshot"], recipe_bytes)
        _atomic_write(auxiliary["candidate_atlas"], _candidate_atlas(canvases, masks, candidates), protect_existing=False)
        for key, table in (("candidate_table", candidate_table), ("preprocessing_checkpoint", image_table)):
            _atomic_write(auxiliary[key], table.to_csv(index=False, lineterminator="\n").encode("utf-8"))
        observed_work = {p.resolve() for p in work.rglob("*") if p.is_file()}
        observed_inputs = {p.resolve() for p in (output_root / "images/inputs").iterdir() if p.is_file()}
        check("file_set", "Ten inputs and exactly 24 candidate/checkpoint files", observed_inputs == set(input_targets.values()) and observed_work == expected_work_files, [len(observed_inputs), len(observed_work)], [10, 24])
    return {"validation": collector, "preprocessed_images": image_table, "mask_candidates": candidate_table,
            "atlas_path": auxiliary["candidate_atlas"], "work_root": work,
            "elapsed_seconds": perf_counter() - started, "recipe_sha256": recipe_hash,
            "review_status": "pending", "preprocessing_visual_review": contract["prior_visual_review"]}
