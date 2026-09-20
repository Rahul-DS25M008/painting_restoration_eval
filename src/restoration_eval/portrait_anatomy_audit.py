"""Outcome-gated portrait anatomy and depicted-skin-tone audit support.

This module supports Decision/Analysis Notebook D02. It keeps human-reviewed
anatomical annotations separate from damage masks and prevents model outcomes
from entering the workflow until the annotation-overlap feasibility gate has
been evaluated.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml
from PIL import Image, ImageDraw, ImageFont


PORTRAIT_ANATOMY_MODULE_NAME = "restoration_eval.portrait_anatomy_audit"
PORTRAIT_ANATOMY_MODULE_VERSION = "1.0.0"
PORTRAIT_SCREENING_SCHEMA_VERSION = "portrait_anatomy_screening.v1"
ANNOTATION_SCHEMA_VERSION = "portrait_anatomy_annotations.v1"
OVERLAP_SCHEMA_VERSION = "portrait_anatomy_overlap.v1"

PORTRAIT_SCREENING_COLUMNS = [
    "painting_id", "dataset_sort_index", "title", "artist", "date_or_period",
    "style_or_period", "medium", "source", "clean_image_path",
    "content_x_min", "content_y_min", "content_x_max", "content_y_max",
    "canonical_case_count", "damage_size_case_count", "robustness_case_count",
    "degradation_case_count", "focused_experiment_painting",
    "preliminary_shortlist", "preliminary_shortlist_families",
    "screening_status", "visible_face", "visible_skin", "visible_left_hand",
    "visible_right_hand", "other_exposed_body_part", "screening_notes",
    "exclusion_reason", "schema_version",
]

ANNOTATION_COLUMNS = [
    "annotation_id", "painting_id", "region_type", "polygon_json",
    "binary_mask_path", "visible_pixel_count", "ambiguity_level",
    "occlusion_status", "annotator", "reviewer", "review_status", "notes",
    "schema_version",
]

OVERLAP_COLUMNS = [
    "overlap_id", "painting_id", "case_id", "experiment_id", "damage_family",
    "annotation_id", "region_type", "mask_path", "anatomical_pixel_count",
    "damaged_anatomical_pixels", "anatomical_fraction_affected",
    "damage_fraction_inside_anatomy", "passes_pixel_threshold",
    "passes_fraction_threshold", "passes_overlap_thresholds", "status", "issue",
    "schema_version",
]


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    settings = config.get("portrait_anatomy_audit", config)
    if not isinstance(settings, Mapping):
        raise TypeError("portrait_anatomy_audit settings must be a mapping")
    return settings


def _stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join("" if part is None else str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


def _resolve(project_root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(project_root) / path


def load_portrait_anatomy_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the D02 configuration contract."""

    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Portrait anatomy configuration must be a mapping")
    if config.get("config_schema_version") != "portrait_anatomy_audit_config.v1":
        raise ValueError("Unsupported portrait anatomy configuration schema")
    settings = _settings(config)
    required = {
        "notebook_id", "notebook_stem", "dataset_scope", "inputs", "output",
        "population", "annotations", "overlap_gate", "models", "analysis",
        "skin_tone", "report", "evidence_policy", "downstream_consumers",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"Portrait anatomy configuration is missing keys: {missing}")
    if str(settings["notebook_id"]) != "D02":
        raise ValueError("D02 configuration must retain notebook_id='D02'")
    policy = settings["evidence_policy"]
    if not bool(policy["annotation_independent_of_damage_masks"]):
        raise ValueError("Anatomical annotations must remain independent of damage masks")
    if not bool(policy["outcome_blind_screening_required"]):
        raise ValueError("Outcome-blind screening is mandatory")
    if bool(policy["new_masks_or_restoration_inference_authorized"]):
        raise ValueError("D02 is analysis-only unless separately approved")
    if not bool(settings["report"]["self_contained_html"]):
        raise ValueError("The D02 report must remain self-contained")
    gate = settings["overlap_gate"]
    if int(gate["minimum_damaged_anatomical_pixels"]) <= 0:
        raise ValueError("The anatomical overlap pixel threshold must be positive")
    fraction = float(gate["minimum_anatomical_fraction_affected"])
    if not 0.0 < fraction <= 1.0:
        raise ValueError("The anatomical overlap fraction threshold must be in (0, 1]")
    return config


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def validate_upstream_manifests(
    manifests: Mapping[str, Mapping[str, Any]],
    expected_ids: Sequence[str],
) -> pd.DataFrame:
    """Return one strict completion-gate audit row per upstream notebook."""

    rows: list[dict[str, Any]] = []
    for notebook_id in expected_ids:
        manifest = manifests.get(str(notebook_id))
        present = isinstance(manifest, Mapping)
        run_status = str(manifest.get("run_status", "")) if present else ""
        validation_status = str(manifest.get("validation_status", "")) if present else ""
        gate = bool(manifest.get("completion_gate_passed", False)) if present else False
        passed = present and run_status == "completed" and validation_status == "passed" and gate
        rows.append({
            "notebook_id": str(notebook_id),
            "manifest_present": present,
            "run_status": run_status,
            "validation_status": validation_status,
            "completion_gate_passed": gate,
            "passed": passed,
            "issue": "" if passed else "missing or incomplete validated upstream run",
        })
    return pd.DataFrame(rows)


def _count_cases(frame: pd.DataFrame, painting_ids: pd.Series) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype="int64")
    ids = set(painting_ids.astype(str))
    subset = frame[frame["painting_id"].astype(str).isin(ids)]
    return subset.groupby("painting_id")["case_id"].nunique().astype("int64")


def build_portrait_screening_population(
    artworks: pd.DataFrame,
    preprocessing: pd.DataFrame,
    canonical_cases: pd.DataFrame,
    damage_size_cases: pd.DataFrame,
    robustness_cases: pd.DataFrame,
    degradation_cases: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the complete outcome-blind 60-painting screening population."""

    settings = _settings(config)
    population = settings["population"]
    portraits = artworks[
        artworks["category"].astype(str).eq(str(population["portrait_category"]))
    ].copy()
    if portraits["painting_id"].duplicated().any():
        raise ValueError("Portrait artwork rows must be unique by painting_id")
    pre_cols = [
        "painting_id", "processed_path", "content_x_min", "content_y_min",
        "content_x_max", "content_y_max",
    ]
    pre = preprocessing[pre_cols].copy().rename(
        columns={"processed_path": "clean_image_path"}
    )
    if pre["painting_id"].duplicated().any():
        raise ValueError("Preprocessing rows must be unique by painting_id")
    columns = [
        "painting_id", "dataset_sort_index", "title", "artist", "date_or_period",
        "style_or_period", "medium", "source",
    ]
    result = portraits[columns].merge(
        pre, on="painting_id", how="left", validate="one_to_one"
    )
    ids = result["painting_id"].astype(str)
    count_sources = {
        "canonical_case_count": canonical_cases,
        "damage_size_case_count": damage_size_cases,
        "robustness_case_count": robustness_cases,
        "degradation_case_count": degradation_cases,
    }
    for output_column, source in count_sources.items():
        counts = _count_cases(source, ids)
        result[output_column] = result["painting_id"].map(counts).fillna(0).astype(int)
    focused = set(map(str, population["focused_painting_ids"]))
    shortlist = {
        str(key): tuple(map(str, value))
        for key, value in population["preliminary_case_shortlist"].items()
    }
    result["focused_experiment_painting"] = result["painting_id"].isin(focused)
    result["preliminary_shortlist"] = result["painting_id"].isin(shortlist)
    result["preliminary_shortlist_families"] = result["painting_id"].map(
        lambda value: "|".join(shortlist.get(str(value), ()))
    )
    result["screening_status"] = "pending_manual_review"
    for column in (
        "visible_face", "visible_skin", "visible_left_hand", "visible_right_hand",
        "other_exposed_body_part",
    ):
        result[column] = pd.NA
    result["screening_notes"] = ""
    result["exclusion_reason"] = ""
    result["schema_version"] = PORTRAIT_SCREENING_SCHEMA_VERSION
    result = result.sort_values("dataset_sort_index", kind="stable").reset_index(drop=True)
    return result[PORTRAIT_SCREENING_COLUMNS]


def validate_portrait_screening(
    screening: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    require_reviewed: bool = False,
) -> list[str]:
    """Return screening-contract errors without modifying the table."""

    expected = int(_settings(config)["population"]["exact_portrait_count"])
    errors: list[str] = []
    missing = sorted(set(PORTRAIT_SCREENING_COLUMNS) - set(screening.columns))
    if missing:
        return [f"missing screening columns: {missing}"]
    if len(screening) != expected:
        errors.append(f"expected {expected} portrait rows, found {len(screening)}")
    if screening["painting_id"].duplicated().any():
        errors.append("painting_id values are not unique")
    if screening["clean_image_path"].isna().any():
        errors.append("one or more portrait rows lack a clean image path")
    if require_reviewed:
        allowed = {"included", "excluded"}
        observed = set(screening["screening_status"].dropna().astype(str))
        if not observed.issubset(allowed) or not observed:
            errors.append("screening_status must be included or excluded after review")
        unresolved = screening["screening_status"].astype(str).eq(
            "pending_manual_review"
        ).sum()
        if unresolved:
            errors.append(f"{unresolved} portrait rows remain pending manual review")
    return errors


def empty_annotation_table() -> pd.DataFrame:
    """Return an empty, schema-correct annotation table for manual population."""

    return pd.DataFrame(columns=ANNOTATION_COLUMNS)


def parse_polygon_json(value: Any) -> list[tuple[float, float]]:
    """Parse a JSON polygon encoded as [[x, y], ...]."""

    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    text = str(value).strip()
    if not text:
        return []
    payload = json.loads(text)
    if not isinstance(payload, list) or len(payload) < 3:
        raise ValueError("polygon_json must contain at least three [x, y] points")
    points: list[tuple[float, float]] = []
    for item in payload:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("Every polygon point must be [x, y]")
        points.append((float(item[0]), float(item[1])))
    return points


def _text_or_empty(value: Any) -> str:
    """Normalize nullable scalar text without evaluating ``pd.NA`` as bool."""

    if value is None:
        return ""
    try:
        if bool(pd.isna(value)):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def annotation_mask(
    annotation: Mapping[str, Any],
    *,
    project_root: str | Path,
    width: int,
    height: int,
) -> np.ndarray:
    """Rasterize one approved polygon or load its declared binary mask."""

    mask_path_value = _text_or_empty(annotation.get("binary_mask_path", ""))
    polygon_value = annotation.get("polygon_json", "")
    has_polygon = bool(_text_or_empty(polygon_value))
    if bool(mask_path_value) == bool(has_polygon):
        raise ValueError("Exactly one of polygon_json or binary_mask_path is required")
    if mask_path_value:
        path = _resolve(project_root, mask_path_value)
        if not path.is_file():
            raise FileNotFoundError(f"Annotation mask does not exist: {path}")
        with Image.open(path) as image:
            mask = np.asarray(image.convert("L"), dtype=np.uint8) >= 128
        if mask.shape != (height, width):
            raise ValueError(f"Annotation mask geometry {mask.shape} != {(height, width)}")
        return mask
    points = parse_polygon_json(polygon_value)
    if any(x < 0 or x >= width or y < 0 or y >= height for x, y in points):
        raise ValueError("Annotation polygon extends outside the declared canvas")
    image = Image.new("1", (width, height), 0)
    ImageDraw.Draw(image).polygon(points, outline=1, fill=1)
    return np.asarray(image, dtype=bool)


def validate_annotations(
    annotations: pd.DataFrame,
    screening: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    project_root: str | Path,
) -> tuple[pd.DataFrame, list[str]]:
    """Validate reviewed annotations and return measured pixel counts."""

    settings = _settings(config)
    contract = settings["annotations"]
    errors: list[str] = []
    missing = sorted(set(ANNOTATION_COLUMNS) - set(annotations.columns))
    if missing:
        return annotations.copy(), [f"missing annotation columns: {missing}"]
    result = annotations[ANNOTATION_COLUMNS].copy()
    if result.empty:
        return result, ["no anatomical annotations have been recorded"]
    if result["annotation_id"].astype(str).duplicated().any():
        errors.append("annotation_id values are not unique")
    screening_lookup = screening.set_index("painting_id", drop=False)
    painting_ids = set(screening["painting_id"].astype(str))
    unknown = sorted(set(result["painting_id"].astype(str)) - painting_ids)
    if unknown:
        errors.append(f"annotations reference unknown portrait IDs: {unknown}")
    allowed_regions = set(map(str, contract["allowed_region_types"]))
    invalid_regions = sorted(set(result["region_type"].astype(str)) - allowed_regions)
    if invalid_regions:
        errors.append(f"unsupported anatomical region types: {invalid_regions}")
    allowed_status = set(map(str, contract["allowed_review_statuses"]))
    invalid_status = sorted(set(result["review_status"].astype(str)) - allowed_status)
    if invalid_status:
        errors.append(f"unsupported review statuses: {invalid_status}")
    width = int(contract["canvas_width"])
    height = int(contract["canvas_height"])
    measured_counts: list[int] = []
    for index, row in result.iterrows():
        if str(row["review_status"]) == "excluded":
            has_polygon = bool(_text_or_empty(row.get("polygon_json", "")))
            has_mask = bool(_text_or_empty(row.get("binary_mask_path", "")))
            if has_polygon or has_mask:
                errors.append(
                    f"row {index}: excluded annotations must not retain geometry"
                )
            measured_counts.append(0)
            continue
        try:
            mask = annotation_mask(
                row, project_root=project_root, width=width, height=height
            )
            count = int(mask.sum())
            measured_counts.append(count)
            if count <= 0 and str(row["review_status"]) != "excluded":
                errors.append(f"row {index} has an empty approved annotation")
            painting_id = str(row["painting_id"])
            if painting_id in screening_lookup.index:
                screen = screening_lookup.loc[painting_id]
                content = np.zeros((height, width), dtype=bool)
                content[
                    int(screen["content_y_min"]):int(screen["content_y_max"]),
                    int(screen["content_x_min"]):int(screen["content_x_max"]),
                ] = True
                outside_pixels = int((mask & ~content).sum())
                if outside_pixels:
                    errors.append(
                        f"row {index} extends {outside_pixels} pixels outside "
                        "the recorded painting-content bounds"
                    )
        except Exception as exc:
            measured_counts.append(0)
            errors.append(f"row {index}: {type(exc).__name__}: {exc}")
    result["visible_pixel_count"] = measured_counts
    result["schema_version"] = ANNOTATION_SCHEMA_VERSION
    return result, errors


def _write_csv_atomic_retry(
    frame: pd.DataFrame,
    path: str | Path,
    *,
    attempts: int = 8,
    delay_seconds: float = 0.25,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    for attempt in range(1, attempts + 1):
        try:
            frame.to_csv(temporary, index=False)
            os.replace(temporary, target)
            return target
        except PermissionError:
            temporary.unlink(missing_ok=True)
            if attempt == attempts:
                raise
            time.sleep(delay_seconds * attempt)
    raise RuntimeError(f"Could not write {target}")


def run_polygon_annotation_session(
    worklist: pd.DataFrame,
    annotations: pd.DataFrame,
    screening: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    project_root: str | Path,
    annotations_path: str | Path,
    worklist_path: str | Path,
    annotator: str,
    reviewer: str = "",
    reset_regions: Sequence[tuple[str, str]] = (),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run a resumable OpenCV polygon-review session.

    The native window records reviewed polygons on the normalized canvas. It
    never displays damaged images, restorations, or metric outcomes.
    """

    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required for polygon review") from exc

    root = Path(project_root)
    settings = _settings(config)
    contract = settings["annotations"]
    width = int(contract["canvas_width"])
    height = int(contract["canvas_height"])
    reviewed_worklist = worklist.copy()
    reviewed_annotations = annotations.copy()
    for column in ANNOTATION_COLUMNS:
        if column not in reviewed_annotations.columns:
            reviewed_annotations[column] = pd.Series(dtype="object")
    reviewed_annotations = reviewed_annotations[ANNOTATION_COLUMNS]

    required_worklist = {
        "painting_id", "region_type", "clean_image_path", "annotation_status"
    }
    missing_worklist = sorted(required_worklist - set(reviewed_worklist.columns))
    if missing_worklist:
        raise ValueError(f"Annotation worklist is missing columns: {missing_worklist}")
    if not str(annotator).strip():
        raise ValueError("annotator must be non-empty")

    reset = {(str(painting), str(region)) for painting, region in reset_regions}
    if reset:
        known = set(
            zip(
                reviewed_worklist["painting_id"].astype(str),
                reviewed_worklist["region_type"].astype(str),
            )
        )
        unknown = sorted(reset - known)
        if unknown:
            raise ValueError(f"Unknown reset regions: {unknown}")
        for painting_id, region_type in reset:
            match = (
                reviewed_worklist["painting_id"].astype(str).eq(painting_id)
                & reviewed_worklist["region_type"].astype(str).eq(region_type)
            )
            reviewed_worklist.loc[match, "annotation_status"] = "pending_polygon_review"
            keep = ~(
                reviewed_annotations["painting_id"].astype(str).eq(painting_id)
                & reviewed_annotations["region_type"].astype(str).eq(region_type)
            )
            reviewed_annotations = reviewed_annotations.loc[keep].reset_index(drop=True)

    screening_lookup = screening.set_index("painting_id", drop=False)
    ambiguity_values = ("none", "low", "moderate", "high")
    occlusion_values = ("none", "partial", "substantial")
    top_margin = 118
    window_name = "D02 outcome-blind anatomical polygon review"
    current_points: list[tuple[int, int]] = []
    active_bounds = [(0, 0, width, height)]

    def checkpoint() -> None:
        _write_csv_atomic_retry(reviewed_annotations, annotations_path)
        _write_csv_atomic_retry(reviewed_worklist, worklist_path)

    def mouse_callback(event: int, x: int, y: int, flags: int, param: Any) -> None:
        del flags, param
        image_y = y - top_margin
        if event == cv2.EVENT_RBUTTONDOWN:
            if current_points:
                current_points.pop()
            return
        if event != cv2.EVENT_LBUTTONDOWN or image_y < 0:
            return
        x_min, y_min, x_max, y_max = active_bounds[0]
        if not (x_min <= x < x_max and y_min <= image_y < y_max):
            return
        current_points.append((int(x), int(image_y)))

    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(window_name, mouse_callback)

    try:
        while True:
            pending = reviewed_worklist[
                reviewed_worklist["annotation_status"].astype(str).eq(
                    "pending_polygon_review"
                )
            ]
            if pending.empty:
                checkpoint()
                print("Polygon annotation worklist complete.")
                break

            row_index = pending.index[0]
            row = reviewed_worklist.loc[row_index]
            painting_id = str(row["painting_id"])
            region_type = str(row["region_type"])
            screen = screening_lookup.loc[painting_id]
            active_bounds[0] = (
                int(screen["content_x_min"]),
                int(screen["content_y_min"]),
                int(screen["content_x_max"]),
                int(screen["content_y_max"]),
            )
            image_path = _resolve(root, str(row["clean_image_path"]))
            with Image.open(image_path) as image:
                rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
            if rgb.shape != (height, width, 3):
                raise ValueError(f"Unexpected clean-image geometry: {rgb.shape}")
            base_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            current_points.clear()
            ambiguity_index = 0
            occlusion_index = 0

            while True:
                frame = np.full(
                    (height + top_margin, width, 3),
                    (244, 239, 228),
                    dtype=np.uint8,
                )
                frame[top_margin:, :, :] = base_bgr
                x_min, y_min, x_max, y_max = active_bounds[0]
                cv2.rectangle(
                    frame,
                    (x_min, y_min + top_margin),
                    (x_max - 1, y_max - 1 + top_margin),
                    (40, 150, 80),
                    1,
                )

                existing = reviewed_annotations[
                    reviewed_annotations["painting_id"].astype(str).eq(painting_id)
                    & reviewed_annotations["region_type"].astype(str).eq(region_type)
                    & reviewed_annotations["review_status"].astype(str).isin(
                        {"approved", "approved_with_ambiguity"}
                    )
                ]
                for _, existing_row in existing.iterrows():
                    points = parse_polygon_json(existing_row["polygon_json"])
                    polygon = np.asarray(
                        [[int(x), int(y) + top_margin] for x, y in points],
                        dtype=np.int32,
                    )
                    cv2.polylines(frame, [polygon], True, (60, 200, 60), 2)

                if current_points:
                    shifted = np.asarray(
                        [[x, y + top_margin] for x, y in current_points],
                        dtype=np.int32,
                    )
                    if len(shifted) > 1:
                        cv2.polylines(frame, [shifted], False, (0, 180, 255), 2)
                    for x, y in shifted:
                        cv2.circle(frame, (int(x), int(y)), 4, (0, 80, 255), -1)

                completed_count = int(
                    reviewed_worklist["annotation_status"].astype(str).isin(
                        {"completed", "excluded"}
                    ).sum()
                )
                lines = [
                    f"{painting_id} | {region_type} | {completed_count + 1}/{len(reviewed_worklist)}",
                    "Left click: vertex | Right click: undo | Enter: save + next | A: save + add another",
                    "N: finish with saved polygon | U: remove last saved | X: exclude | Q: save + quit",
                    f"M: ambiguity={ambiguity_values[ambiguity_index]} | O: occlusion={occlusion_values[occlusion_index]}",
                ]
                for line_number, text in enumerate(lines):
                    cv2.putText(
                        frame,
                        text,
                        (10, 24 + line_number * 25),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.53,
                        (28, 63, 55),
                        1,
                        cv2.LINE_AA,
                    )
                cv2.imshow(window_name, frame)
                key = cv2.waitKeyEx(20)
                if key < 0:
                    continue
                key = key & 0xFF

                if key == ord("q"):
                    checkpoint()
                    print(
                        "Polygon checkpoint saved; rerun the cell to resume. "
                        f"Completed {completed_count}/{len(reviewed_worklist)} regions."
                    )
                    return reviewed_worklist, reviewed_annotations
                if key == ord("m"):
                    ambiguity_index = (ambiguity_index + 1) % len(ambiguity_values)
                    continue
                if key == ord("o"):
                    occlusion_index = (occlusion_index + 1) % len(occlusion_values)
                    continue
                if key == ord("u"):
                    matching = reviewed_annotations[
                        reviewed_annotations["painting_id"].astype(str).eq(painting_id)
                        & reviewed_annotations["region_type"].astype(str).eq(region_type)
                        & ~reviewed_annotations["review_status"].astype(str).eq("excluded")
                    ]
                    if not matching.empty:
                        reviewed_annotations = reviewed_annotations.drop(
                            index=matching.index[-1]
                        ).reset_index(drop=True)
                        checkpoint()
                    continue
                if key == ord("x"):
                    excluded_row = {
                        "annotation_id": _stable_id(
                            "anatomy", painting_id, region_type, "excluded"
                        ),
                        "painting_id": painting_id,
                        "region_type": region_type,
                        "polygon_json": "",
                        "binary_mask_path": "",
                        "visible_pixel_count": 0,
                        "ambiguity_level": ambiguity_values[ambiguity_index],
                        "occlusion_status": occlusion_values[occlusion_index],
                        "annotator": str(annotator).strip(),
                        "reviewer": str(reviewer).strip(),
                        "review_status": "excluded",
                        "notes": "Declared visible during screening but excluded during polygon review.",
                        "schema_version": ANNOTATION_SCHEMA_VERSION,
                    }
                    reviewed_annotations = pd.concat(
                        [reviewed_annotations, pd.DataFrame([excluded_row])],
                        ignore_index=True,
                    )
                    reviewed_worklist.loc[row_index, "annotation_status"] = "excluded"
                    checkpoint()
                    break

                save_and_stay = key == ord("a")
                save_and_next = key in {10, 13}
                finish_existing = key == ord("n")
                if finish_existing and not existing.empty and not current_points:
                    reviewed_worklist.loc[row_index, "annotation_status"] = "completed"
                    checkpoint()
                    break
                if not (save_and_stay or save_and_next):
                    continue
                if len(current_points) < 3:
                    continue
                sequence = int(len(existing)) + 1
                polygon_json = json.dumps(
                    [[int(x), int(y)] for x, y in current_points],
                    separators=(",", ":"),
                )
                review_status = (
                    "approved_with_ambiguity"
                    if ambiguity_values[ambiguity_index] in {"moderate", "high"}
                    else "approved"
                )
                new_row = {
                    "annotation_id": _stable_id(
                        "anatomy", painting_id, region_type, sequence, polygon_json
                    ),
                    "painting_id": painting_id,
                    "region_type": region_type,
                    "polygon_json": polygon_json,
                    "binary_mask_path": "",
                    "visible_pixel_count": 0,
                    "ambiguity_level": ambiguity_values[ambiguity_index],
                    "occlusion_status": occlusion_values[occlusion_index],
                    "annotator": str(annotator).strip(),
                    "reviewer": str(reviewer).strip(),
                    "review_status": review_status,
                    "notes": "",
                    "schema_version": ANNOTATION_SCHEMA_VERSION,
                }
                mask = annotation_mask(
                    new_row,
                    project_root=root,
                    width=width,
                    height=height,
                )
                new_row["visible_pixel_count"] = int(mask.sum())
                reviewed_annotations = pd.concat(
                    [reviewed_annotations, pd.DataFrame([new_row])],
                    ignore_index=True,
                )
                current_points.clear()
                checkpoint()
                if save_and_next:
                    reviewed_worklist.loc[row_index, "annotation_status"] = "completed"
                    checkpoint()
                    break
    finally:
        cv2.destroyAllWindows()

    return reviewed_worklist, reviewed_annotations


def normalize_case_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize N04-N07 case registries for the outcome-blind overlap audit."""

    result = frame.copy()
    aliases = {
        "mask_path": ("mask_path", "mask_or_effect_path", "effect_mask_path"),
        "damage_family": (
            "mask_type", "base_mask_type", "degradation_family",
            "damage_or_degradation_type",
        ),
        "input_image_path": (
            "damaged_image_path", "input_image_path", "degraded_image_path",
        ),
    }
    for target, candidates in aliases.items():
        if target in result.columns:
            continue
        source = next((name for name in candidates if name in result.columns), None)
        result[target] = result[source] if source else pd.NA
    required = {"painting_id", "case_id", "experiment_id", "mask_path", "damage_family"}
    missing = sorted(required - set(result.columns))
    if missing:
        raise ValueError(f"Case registry cannot be normalized; missing {missing}")
    return result


def compute_anatomical_overlap_audit(
    cases: pd.DataFrame,
    annotations: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    project_root: str | Path,
) -> pd.DataFrame:
    """Measure damage-mask overlap without loading restoration outcomes."""

    settings = _settings(config)
    annotation_contract = settings["annotations"]
    gate = settings["overlap_gate"]
    normalized = normalize_case_table(cases)
    approved = annotations[
        annotations["review_status"].astype(str).isin(
            {"approved", "approved_with_ambiguity"}
        )
    ].copy()
    width = int(annotation_contract["canvas_width"])
    height = int(annotation_contract["canvas_height"])
    threshold = int(gate["mask_threshold"])
    minimum_pixels = int(gate["minimum_damaged_anatomical_pixels"])
    minimum_fraction = float(gate["minimum_anatomical_fraction_affected"])
    annotation_masks = {
        str(row["annotation_id"]): annotation_mask(
            row, project_root=project_root, width=width, height=height
        )
        for _, row in approved.iterrows()
    }
    rows: list[dict[str, Any]] = []
    for painting_id, painting_annotations in approved.groupby("painting_id", sort=True):
        painting_cases = normalized[
            normalized["painting_id"].astype(str).eq(str(painting_id))
        ]
        for _, case in painting_cases.iterrows():
            mask_path = _resolve(project_root, str(case["mask_path"]))
            if not mask_path.is_file():
                raise FileNotFoundError(f"Damage mask does not exist: {mask_path}")
            with Image.open(mask_path) as image:
                damage_mask = np.asarray(image.convert("L"), dtype=np.uint8) >= threshold
            if damage_mask.shape != (height, width):
                raise ValueError(f"Damage mask geometry {damage_mask.shape} != {(height, width)}")
            damage_pixels = int(damage_mask.sum())
            for _, annotation in painting_annotations.iterrows():
                annotation_id = str(annotation["annotation_id"])
                anatomy = annotation_masks[annotation_id]
                anatomy_pixels = int(anatomy.sum())
                overlap = int(np.logical_and(damage_mask, anatomy).sum())
                anatomy_fraction = overlap / anatomy_pixels if anatomy_pixels else 0.0
                damage_fraction = overlap / damage_pixels if damage_pixels else 0.0
                pixel_pass = overlap >= minimum_pixels
                fraction_pass = anatomy_fraction >= minimum_fraction
                rows.append({
                    "overlap_id": _stable_id(
                        "anatomy_overlap", case["case_id"], annotation_id
                    ),
                    "painting_id": str(painting_id),
                    "case_id": str(case["case_id"]),
                    "experiment_id": str(case["experiment_id"]),
                    "damage_family": str(case["damage_family"]),
                    "annotation_id": annotation_id,
                    "region_type": str(annotation["region_type"]),
                    "mask_path": str(case["mask_path"]),
                    "anatomical_pixel_count": anatomy_pixels,
                    "damaged_anatomical_pixels": overlap,
                    "anatomical_fraction_affected": anatomy_fraction,
                    "damage_fraction_inside_anatomy": damage_fraction,
                    "passes_pixel_threshold": pixel_pass,
                    "passes_fraction_threshold": fraction_pass,
                    "passes_overlap_thresholds": pixel_pass and fraction_pass,
                    "status": "ok",
                    "issue": "",
                    "schema_version": OVERLAP_SCHEMA_VERSION,
                })
    return pd.DataFrame(rows, columns=OVERLAP_COLUMNS)


def summarize_hand_feasibility(
    overlap: pd.DataFrame,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the frozen D02 hand-analysis stop/go gate."""

    gate = _settings(config)["overlap_gate"]
    hand = overlap[
        overlap["region_type"].astype(str).isin({"left_hand", "right_hand"})
        & overlap["passes_overlap_thresholds"].fillna(False).astype(bool)
    ].copy()
    checks = {
        "independent_hand_paintings": {
            "observed": int(hand["painting_id"].nunique()),
            "required": int(gate["minimum_independent_hand_paintings"]),
        },
        "usable_hand_cases": {
            "observed": int(hand["case_id"].nunique()),
            "required": int(gate["minimum_usable_hand_cases"]),
        },
        "hand_damage_families": {
            "observed": int(hand["damage_family"].nunique()),
            "required": int(gate["minimum_hand_damage_families"]),
        },
    }
    for value in checks.values():
        value["passed"] = value["observed"] >= value["required"]
    passed = all(value["passed"] for value in checks.values())
    return {
        "hand_analysis_feasible": passed,
        "stop_after_feasibility": bool(gate["stop_if_failed"]) and not passed,
        "checks": checks,
        "eligible_hand_painting_ids": sorted(hand["painting_id"].astype(str).unique()),
        "eligible_hand_case_ids": sorted(hand["case_id"].astype(str).unique()),
    }


def create_annotation_qa_atlas(
    screening: pd.DataFrame,
    annotations: pd.DataFrame,
    output_path: str | Path,
    *,
    project_root: str | Path,
    columns: int = 5,
    tile_size: int = 220,
) -> Path:
    """Render approved anatomical polygons over every included clean painting."""

    approved = annotations[
        annotations["review_status"].astype(str).isin(
            {"approved", "approved_with_ambiguity"}
        )
    ].copy()
    if approved.empty:
        raise ValueError("Cannot render annotation QA without approved polygons")

    included = screening[
        screening["screening_status"].astype(str).eq("included")
    ].copy()
    included = included[
        included["painting_id"].astype(str).isin(
            approved["painting_id"].astype(str)
        )
    ].sort_values("dataset_sort_index", kind="stable")
    if included.empty:
        raise ValueError("No included paintings match the approved annotations")

    palette = {
        "face": (216, 82, 48, 92),
        "visible_skin": (225, 171, 55, 92),
        "left_hand": (32, 111, 92, 105),
        "right_hand": (54, 104, 168, 105),
        "other_exposed_body_part": (126, 79, 153, 100),
    }
    label_height = 54
    row_count = int(math.ceil(len(included) / columns))
    canvas = Image.new(
        "RGB",
        (columns * tile_size, row_count * (tile_size + label_height)),
        "#f4efe4",
    )
    draw = ImageDraw.Draw(canvas)
    try:
        label_font = ImageFont.truetype("DejaVuSans.ttf", 12)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 10)
    except OSError:
        label_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    for index, (_, screen) in enumerate(included.iterrows()):
        painting_id = str(screen["painting_id"])
        x = (index % columns) * tile_size
        y = (index // columns) * (tile_size + label_height)
        path = _resolve(project_root, str(screen["clean_image_path"]))
        with Image.open(path) as image:
            source = image.convert("RGBA")
        overlay = Image.new("RGBA", source.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        painting_annotations = approved[
            approved["painting_id"].astype(str).eq(painting_id)
        ]
        for _, annotation in painting_annotations.iterrows():
            points = parse_polygon_json(annotation["polygon_json"])
            colour = palette.get(str(annotation["region_type"]), (180, 90, 40, 96))
            outline = colour[:3] + (255,)
            overlay_draw.polygon(points, fill=colour, outline=outline, width=3)
        composite = Image.alpha_composite(source, overlay).convert("RGB")
        composite.thumbnail((tile_size - 8, tile_size - 8), Image.Resampling.LANCZOS)
        left = x + (tile_size - composite.width) // 2
        top = y + (tile_size - composite.height) // 2
        canvas.paste(composite, (left, top))

        region_summary = ", ".join(
            sorted(painting_annotations["region_type"].astype(str).unique())
        )
        title = f"{painting_id} | {str(screen['title'])[:25]}"
        draw.text((x + 6, y + tile_size + 4), title, fill="#173f37", font=label_font)
        draw.text(
            (x + 6, y + tile_size + 24),
            region_summary[:40],
            fill="#5a554b",
            font=small_font,
        )

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target, format="PNG", optimize=True)
    return target


def create_screening_atlas(
    screening: pd.DataFrame,
    output_path: str | Path,
    *,
    project_root: str | Path,
    columns: int = 6,
    tile_size: int = 180,
) -> Path:
    """Render all portraits for outcome-blind anatomical screening."""

    rows = int(math.ceil(len(screening) / columns))
    label_height = 34
    canvas = Image.new(
        "RGB", (columns * tile_size, rows * (tile_size + label_height)), "#f4efe4"
    )
    draw = ImageDraw.Draw(canvas)
    try:
        label_font = ImageFont.truetype("DejaVuSans.ttf", 12)
    except OSError:
        label_font = ImageFont.load_default()
    for index, row in screening.reset_index(drop=True).iterrows():
        x = (index % columns) * tile_size
        y = (index // columns) * (tile_size + label_height)
        path = _resolve(project_root, str(row["clean_image_path"]))
        with Image.open(path) as image:
            thumb = image.convert("RGB")
            thumb.thumbnail((tile_size - 8, tile_size - 8), Image.Resampling.LANCZOS)
        left = x + (tile_size - thumb.width) // 2
        top = y + (tile_size - thumb.height) // 2
        canvas.paste(thumb, (left, top))
        label = f"{row['painting_id']}  {str(row['title'])[:22]}"
        try:
            draw.text(
                (x + 6, y + tile_size + 5),
                label,
                fill="#173f37",
                font=label_font,
            )
        except UnicodeEncodeError:
            safe_label = label.encode("ascii", errors="replace").decode("ascii")
            draw.text(
                (x + 6, y + tile_size + 5),
                safe_label,
                fill="#173f37",
                font=ImageFont.load_default(),
            )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target, format="PNG", optimize=True)
    return target


__all__ = [
    "ANNOTATION_COLUMNS", "ANNOTATION_SCHEMA_VERSION", "OVERLAP_COLUMNS",
    "OVERLAP_SCHEMA_VERSION", "PORTRAIT_ANATOMY_MODULE_NAME",
    "PORTRAIT_ANATOMY_MODULE_VERSION", "PORTRAIT_SCREENING_COLUMNS",
    "PORTRAIT_SCREENING_SCHEMA_VERSION", "annotation_mask",
    "build_portrait_screening_population", "compute_anatomical_overlap_audit",
    "create_annotation_qa_atlas", "create_screening_atlas",
    "empty_annotation_table", "load_json",
    "load_portrait_anatomy_config", "normalize_case_table", "parse_polygon_json",
    "run_polygon_annotation_session", "summarize_hand_feasibility",
    "validate_annotations",
    "validate_portrait_screening", "validate_upstream_manifests",
]
