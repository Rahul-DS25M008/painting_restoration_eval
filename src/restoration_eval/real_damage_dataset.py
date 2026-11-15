"""D03 contracts, source audits and bounded preprocessing for real damage.

Only the smoke helper writes temporary files under D03's own work directory.
No helper runs restoration or approves annotations.
The existing preprocessing/region algorithms remain the scientific authority.
"""
from __future__ import annotations

import csv
import copy
import hashlib
import io
import json
import os
import platform
import re
import tempfile
from time import perf_counter
import unicodedata
from collections import Counter
from pathlib import Path, PureWindowsPath
from typing import Any, Callable, Mapping
from urllib.parse import unquote, urlsplit

import numpy as np
import pandas as pd
import yaml
from PIL import Image, ImageCms

from .manifests import sha256_file
from .paths import (
    notebook_output_root,
    require_notebook_output_path,
    resolve_repo_path,
    to_repo_relative,
    validate_project_paths_registry,
)
from .validation import ValidationCollector

REAL_DAMAGE_DATASET_MODULE_VERSION = "1.3.0"
CONFIG_SCHEMA_VERSION = "real_damage_preparation_config.v1"
SOURCE_SCHEMA_VERSION = "real_damage_approved_sources.v1"
NOTEBOOK_STEM = "d03_real_damage_dataset_preparation"
PREFLIGHT_STAGE = "batch_1_preflight"
SOURCE_AUDIT_STAGE = "batch_2_source_validation"
SMOKE_STAGE = "batch_3_preprocessing_smoke"
CATEGORIES = (
    "portrait_figure", "landscape_natural", "architecture_structured",
    "abstraction_surrealism", "high_texture_brushwork",
)
PRIMARY_MODELS = ("opencv_telea", "lama", "hint_places2", "stable_diffusion_inpainting")
SOURCE_REQUIRED_FIELDS = (
    "painting_id", "review_id", "dataset_id", "dataset_version", "dataset_scope",
    "title", "artist", "category", "raw_image_path", "raw_sha256",
    "raw_size_bytes", "raw_width", "raw_height", "source_url", "source_image_url",
    "source_page_id", "source_page_revision", "source_metadata_path",
    "source_metadata_sha256", "retrieved_utc", "license", "rights_basis",
    "source_selection_status", "has_clean_reference", "clean_image_path",
    "damage_observation", "annotation_cautions",
)
OUTPUT_KEYS = {
    "artworks", "preprocessed_images", "masks", "mask_review", "case_registry",
    "model_eligibility", "mask_geometry", "inference_mask_audit",
    "processed_image_template", "mask_template", "source_overview",
    "mask_review_atlas", "report", "run_manifest", "artifacts", "validation",
    "work_root",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _relative(value: Any) -> str:
    """Require normalized relative paths, including when tested on non-Windows."""
    _require(isinstance(value, str) and bool(value.strip()), "A path is missing")
    _require(
        not Path(value).is_absolute() and not PureWindowsPath(value).drive
        and "\\" not in value and ".." not in value.split("/")
        and ".codex_tmp" not in value.split("/"),
        f"Path must be repository-relative and independent of temporary review files: {value}",
    )
    return value


def load_real_damage_config(path: str | Path) -> dict[str, Any]:
    """Load the approved supplemental contract without changing core configs."""
    with Path(path).open(encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    validate_real_damage_config(config)
    return config


def validate_real_damage_config(config: Mapping[str, Any]) -> None:
    """Reject incompatible population, reference, model or annotation policies."""
    _require(isinstance(config, Mapping), "D03 config must be a mapping")
    _require(config.get("config_schema_version") == CONFIG_SCHEMA_VERSION, "Unsupported D03 config schema")
    _require(config.get("contract_status") == "approved", "D03 contract is not approved")
    for key in ("notebook", "dataset", "inputs", "preprocessing", "annotation", "downstream", "outputs", "execution", "schemas"):
        _require(isinstance(config.get(key), Mapping), f"Missing config mapping: {key}")
    nb, ds = config["notebook"], config["dataset"]
    _require(nb.get("id") == "D03" and nb.get("stem") == NOTEBOOK_STEM, "Wrong D03 notebook identity")
    _require(nb.get("output_root") == f"outputs/{NOTEBOOK_STEM}" and nb.get("batch_count") == 8, "Wrong output root or batch count")
    _require(ds.get("dataset_id") == "painting_restoration_real_damage" and ds.get("dataset_scope") == "real_damage_10", "Wrong real-damage dataset identity/scope")
    _require(ds.get("expected_paintings") == 10 and ds.get("expected_per_category") == 2, "D03 requires ten paintings, two per category")
    _require(ds.get("painting_ids") == [f"rd{i:03d}" for i in range(1, 11)], "Unexpected approved painting IDs")
    _require(ds.get("categories") == list(CATEGORIES), "Unexpected category contract")
    _require(ds.get("has_clean_reference") is False, "D03 cannot claim a clean reference")
    prep = config["preprocessing"]
    _require((prep.get("canvas_width"), prep.get("canvas_height"), prep.get("output_mode")) == (768, 768, "RGB"), "D03 must retain 768 RGB preprocessing")
    _require(prep.get("crop_content") is False and prep.get("source_pixels_modified_before_preprocessing") is False, "D03 cannot crop or alter the raw source")
    ann = config["annotation"]
    _require(ann.get("canonical_mask_mode") == "L" and ann.get("canonical_mask_values") == [0, 255] and ann.get("missing_region_value") == 255, "Wrong binary-mask convention")
    for key in ("candidate_masks_require_human_review", "requires_nonempty_mask", "reviewer_approval_binds_image_and_mask_hashes", "review_before_restoration_outcomes"):
        _require(ann.get(key) is True, f"Required annotation policy disabled: {key}")
    for key in ("padding_overlap_allowed", "automatic_dilation_allowed", "inspection_boxes_are_masks"):
        _require(ann.get(key) is False, f"Disallowed annotation policy: {key}")
    scale = ann.get("inference_scale_check", {})
    _require(scale.get("size") == 512 and scale.get("resize") == "nearest", "SD mask audit must use 512 nearest-neighbour resizing")
    downstream = config["downstream"]
    _require(downstream.get("primary_models") == list(PRIMARY_MODELS), "Wrong primary model scope")
    _require(downstream.get("planned_primary_candidates") == 40, "Wrong primary candidate target")
    _require(downstream.get("primary_seed") == 2026 and downstream.get("sd_prompt_variant") == "p00_generic", "Primary seed/prompt policy changed")
    _require(downstream.get("clean_reference_placeholder_allowed") is False and downstream.get("synthetic_comparison_metrics_pooled_with_real") is False, "Invalid reference or comparison policy")
    _require(set(config["outputs"]) == OUTPUT_KEYS, "Output declarations differ from the approved contract")
    _require(config["execution"].get("automatic_cleanup") is False, "Automatic cleanup is not approved")
    _require(config["execution"].get("smoke_painting_ids") == ["rd001", "rd003", "rd005", "rd007", "rd009"], "Unexpected representative smoke selection")
    smoke = config.get("smoke", {})
    _require(smoke.get("directory") == "work/preprocessing_smoke", "Smoke outputs must stay in work/preprocessing_smoke")
    _require(smoke.get("image_filename_template") == "{painting_id}.png" and smoke.get("preview_filename") == "preprocessing_preview.png", "Unexpected smoke filenames")
    _require(smoke.get("figure_dpi") == 150, "Unexpected smoke preview resolution")
    for key, value in config["inputs"].items():
        for candidate in value.values() if isinstance(value, Mapping) else [value]:
            _relative(candidate)
    for value in config["outputs"].values():
        _relative(value)
    _require(len(set(config["outputs"].values())) == len(OUTPUT_KEYS), "Duplicate output paths")


def load_approved_sources(path: str | Path, config: Mapping[str, Any]) -> dict[str, Any]:
    """Read source selection; this never grants mask or dataset-completion approval."""
    with Path(path).open(encoding="utf-8-sig") as handle:
        catalog = json.load(handle)
    validate_approved_sources(catalog, config)
    return catalog


def validate_approved_sources(catalog: Mapping[str, Any], config: Mapping[str, Any]) -> None:
    """Validate acquisition records before any image processing is attempted."""
    _require(catalog.get("schema_version") == SOURCE_SCHEMA_VERSION, "Unsupported source-catalog schema")
    _require(catalog.get("source_cohort_status") == "approved_by_user" and catalog.get("notebook_contract_status") == "approved", "Source cohort and notebook contract must be approved")
    ds = config["dataset"]
    for key in ("dataset_id", "dataset_version", "dataset_scope"):
        _require(catalog.get(key) == ds[key], f"Catalog mismatch: {key}")
    rows = catalog.get("records", [])
    _require(isinstance(rows, list) and len(rows) == ds["expected_paintings"], "Expected ten source records")
    _require([r.get("painting_id") for r in rows] == ds["painting_ids"], "Source IDs/order differ from approved selection")
    _require([r.get("review_id") for r in rows] == [f"D03-R{i:02d}" for i in range(1, 11)], "Review-to-painting mapping changed")
    _require(Counter(r.get("category") for r in rows) == Counter({c: 2 for c in CATEGORIES}), "Source categories are not balanced")
    _require(len({r.get("raw_sha256") for r in rows}) == 10, "Duplicate raw image hashes")
    for row in rows:
        pid = row["painting_id"]
        _require(all(k in row for k in SOURCE_REQUIRED_FIELDS), f"{pid}: source record fields missing")
        for key in ("dataset_id", "dataset_version", "dataset_scope"):
            _require(row[key] == ds[key], f"{pid}: dataset identity mismatch")
        _require(row["has_clean_reference"] is False and row["clean_image_path"] is None, f"{pid}: damaged photo must not become a clean reference")
        _require(row["source_selection_status"] == "approved_by_user", f"{pid}: source not approved")
        for key in ("title", "artist", "source_url", "source_image_url", "retrieved_utc", "license", "rights_basis", "damage_observation"):
            _require(isinstance(row[key], str) and bool(row[key].strip()), f"{pid}: empty {key}")
        for key in ("raw_sha256", "source_metadata_sha256"):
            _require(re.fullmatch(r"[0-9a-f]{64}", str(row[key])) is not None, f"{pid}: invalid {key}")
        for key in ("raw_width", "raw_height", "raw_size_bytes"):
            _require(type(row[key]) is int and row[key] > 0, f"{pid}: invalid {key}")
        _require(row["raw_image_path"] in {f"data/raw/real_damage/images/{pid}{ext}" for ext in (".jpg", ".png")}, f"{pid}: unexpected source image path")
        provider = row.get("source_provider", "commons")
        _require(provider in {"commons", "met"}, f"{pid}: unsupported provenance provider")
        _require(row["source_metadata_path"] == f"data/raw/real_damage/metadata/{provider}/{pid}.json", f"{pid}: unexpected source metadata path")
        if row.get("reviewed_mask_path"):
            _require(row["reviewed_mask_path"] == f"data/raw/real_damage/annotations/{pid}.png", f"{pid}: unexpected reviewed mask path")
            _require(re.fullmatch(r"[0-9a-f]{64}", str(row.get("reviewed_mask_sha256", ""))) is not None, f"{pid}: missing mask digest")
    required_baseline = {
        config["inputs"]["preprocessing_config"],
        *config["inputs"]["model_configs"].values(),
        "src/restoration_eval/preprocessing.py",
    }
    baseline = catalog.get("pipeline_baseline_sha256", {})
    _require(set(baseline) == required_baseline, "Incomplete pipeline baseline")
    _require(all(re.fullmatch(r"[0-9a-f]{64}", str(v)) for v in baseline.values()), "Invalid pipeline baseline digest")


def resolve_real_damage_paths(
    project_root: str | Path, config: Mapping[str, Any], catalog: Mapping[str, Any],
    *, config_path: str | Path,
) -> tuple[dict[str, Path], dict[str, Path]]:
    """Declare exact inputs/outputs, enforcing ownership without creating folders."""
    root = Path(project_root).resolve()
    inputs = {"d03_config": resolve_repo_path(config_path, root)}
    for key, value in config["inputs"].items():
        for name, rel in value.items() if isinstance(value, Mapping) else [(key, value)]:
            input_key = f"{key}.{name}" if isinstance(value, Mapping) else key
            inputs[input_key] = resolve_repo_path(_relative(rel), root)
    for row in catalog["records"]:
        for role, field in (("source_image", "raw_image_path"), ("source_metadata", "source_metadata_path")):
            inputs[f"{role}.{row['painting_id']}"] = resolve_repo_path(_relative(row[field]), root)
        if row.get("reviewed_mask_path"):
            inputs[f"reviewed_mask.{row['painting_id']}"] = resolve_repo_path(_relative(row["reviewed_mask_path"]), root)
    out = notebook_output_root(NOTEBOOK_STEM, root)
    outputs = {
        key: require_notebook_output_path(out / _relative(rel), NOTEBOOK_STEM, root)
        for key, rel in config["outputs"].items()
    }
    _require(not set(inputs.values()).intersection(outputs.values()), "An output would replace an input")
    return inputs, outputs


def audit_inventory_inputs(
    project_root: str | Path, inventory_path: str | Path,
    inventory_run_path: str | Path, inputs: Mapping[str, Path],
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Verify the inventory and only its declared input rows; never discover inputs.

    Size and recorded digest checks detect changed inputs. The inventory excludes
    its own CSV/run manifest by design; those two are checked directly instead.
    Partial inventory digests are never presented as full raw-image hashes.
    """
    root = Path(project_root).resolve()
    inventory = Path(inventory_path).resolve()
    run_path = Path(inventory_run_path).resolve()
    run = json.loads(run_path.read_text(encoding="utf-8-sig"))
    _require(run.get("run_schema_version") == "inventory_run.v1" and run.get("status") == "completed", "Inventory is not a completed supported run")
    _require(run.get("inventory_schema_version") == "project_file_inventory.v1", "Unsupported inventory schema")
    _require(run.get("inventory_relative_path") == to_repo_relative(inventory, root), "Wrong inventory CSV path")
    _require(inventory.stat().st_size == run.get("inventory_size_bytes"), "Inventory size differs from its manifest")
    _require(sha256_file(inventory) == run.get("inventory_sha256"), "Inventory checksum differs from its manifest")
    wanted = {to_repo_relative(path, root) for path in inputs.values() if path.resolve() not in {inventory, run_path}}
    selected: dict[str, dict[str, str]] = {}
    count = 0
    with inventory.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = {"relative_path", "size_bytes", "hash_mode", "hash_algorithm", "hash_bytes_read", "hash_value", "read_error_count", "inventory_run_id"}
        _require(columns.issubset(reader.fieldnames or []), "Inventory columns are incomplete")
        for row in reader:
            count += 1
            rel = row["relative_path"]
            if rel in wanted:
                _require(rel not in selected, f"Duplicate inventory row: {rel}")
                selected[rel] = row
    _require(count == run["summary"]["file_count"], "Inventory row count differs from its manifest")
    results = []
    for key, path in inputs.items():
        rel = to_repo_relative(path, root)
        issues = []
        excluded = path.resolve() in {inventory, run_path}
        if not path.is_file():
            issues.append("missing file")
        elif not excluded:
            row = selected.get(rel)
            if row is None:
                issues.append("not indexed; refresh inventory")
            else:
                if row["inventory_run_id"] != run["inventory_run_id"]:
                    issues.append("inventory row belongs to another run")
                if int(row["read_error_count"] or 0):
                    issues.append("inventory inspection error")
                size = path.stat().st_size
                if int(row["size_bytes"]) != size:
                    issues.append("size changed; refresh inventory")
                mode = row["hash_mode"]
                if mode == "full" and row["hash_algorithm"] == "sha256":
                    digest = sha256_file(path)
                elif mode == "partial" and row["hash_algorithm"] == "sha256_first_n_bytes":
                    amount = int(row["hash_bytes_read"])
                    _require(0 <= amount <= max(size, int(row["size_bytes"])), f"Invalid partial byte count: {rel}")
                    with path.open("rb") as handle:
                        digest = hashlib.sha256(handle.read(amount)).hexdigest()
                else:
                    digest = None
                    issues.append("supported inventory digest required")
                if digest is not None and digest != row["hash_value"]:
                    issues.append("content changed; refresh inventory")
        results.append({
            "input_key": key, "relative_path": rel,
            "inventory_policy": "self_excluded_manifest_verified" if excluded else "indexed_size_and_digest",
            "passed": not issues, "details": "; ".join(issues),
        })
    return run, pd.DataFrame(results)


def validate_real_damage_preflight(
    project_root: str | Path, config: Mapping[str, Any], catalog: Mapping[str, Any],
    inputs: Mapping[str, Path], outputs: Mapping[str, Path],
    *, previous_validation: ValidationCollector | None = None,
) -> dict[str, Any]:
    """Run Batch 1 checks without processing pixels, writing outputs or loading GPU models."""
    root = Path(project_root).resolve()
    collector = ValidationCollector()
    if previous_validation is not None:
        collector.extend(c for c in previous_validation.checks if c.validation_stage != PREFLIGHT_STAGE)

    def check(identifier: str, description: str, passed: bool, observed: Any, expected: Any = True) -> None:
        collector.add(validation_stage=PREFLIGHT_STAGE, check_id=identifier,
                      check_description=description, severity="blocking",
                      expected=expected, observed=observed, passed=passed)

    validate_real_damage_config(config)
    validate_approved_sources(catalog, config)
    check("approved_contract", "Approved D03 configuration and ten-source catalog", True, "approved; ten records, two/category")
    py_minor = ".".join(platform.python_version_tuple()[:2])
    supported = config["execution"]["supported_python_minors"]
    check("python", "Supported Python version", py_minor in supported, py_minor, supported)
    missing = [key for key, path in inputs.items() if not path.is_file()]
    check("input_files", "All declared inputs exist", not missing, missing, [])
    check("output_declarations", "All outputs are within the D03 root", all(
        path.is_relative_to(notebook_output_root(NOTEBOOK_STEM, root)) for path in outputs.values()
    ), len(outputs), "17 declared paths within D03")
    run: dict[str, Any] = {}
    input_audit = pd.DataFrame(columns=["input_key", "relative_path", "inventory_policy", "passed", "details"])
    try:
        run, input_audit = audit_inventory_inputs(root, inputs["inventory"], inputs["inventory_run"], inputs)
        failures = input_audit.loc[~input_audit["passed"], ["input_key", "details"]].to_dict("records")
        check("inventory", "Completed inventory and current declared input rows", not failures, failures, [])
    except (OSError, ValueError, KeyError) as exc:
        check("inventory", "Completed inventory and current declared input rows", False, f"{type(exc).__name__}: {exc}")
    try:
        registry = json.loads(inputs["project_paths"].read_text(encoding="utf-8-sig"))
        errors = validate_project_paths_registry(registry)
        check("project_paths", "Existing project-path registry is valid", not errors, errors, [])
    except (OSError, ValueError) as exc:
        check("project_paths", "Existing project-path registry is valid", False, str(exc))
    try:
        manifest = json.loads(inputs["controlled_dataset_manifest"].read_text(encoding="utf-8-sig"))
        check("n01", "N01 overlap-audit dependency completed", manifest.get("run_status") == "completed", manifest.get("run_status"), "completed")
    except (OSError, ValueError) as exc:
        check("n01", "N01 overlap-audit dependency completed", False, str(exc))
    for rel, expected in catalog["pipeline_baseline_sha256"].items():
        path = resolve_repo_path(rel, root)
        observed = sha256_file(path) if path.is_file() else "missing"
        check(f"baseline:{rel}", "Existing preprocessing/model baseline is unchanged", observed == expected, observed, expected)
    hashes = {}
    for key, path in inputs.items():
        if path.is_file():
            hashes[key] = run["inventory_sha256"] if key == "inventory" and run else sha256_file(path)
    for row in catalog["records"]:
        for role, digest_field in (("source_image", "raw_sha256"), ("source_metadata", "source_metadata_sha256")):
            key = f"{role}.{row['painting_id']}"
            check(key, "Source file matches the accepted full SHA-256", hashes.get(key) == row[digest_field], hashes.get(key, "missing"), row[digest_field])
        if row.get("reviewed_mask_path"):
            key = f"reviewed_mask.{row['painting_id']}"
            check(key, "Selected review mask matches its recorded digest", hashes.get(key) == row["reviewed_mask_sha256"], hashes.get(key, "missing"), row["reviewed_mask_sha256"])
    return {
        "validation": collector,
        "inventory": run,
        "input_audit": input_audit,
        "input_checksums": hashes,
    }


def _source_url_identity(value: str) -> tuple[str, str, str]:
    """Compare original-file URLs ignoring only encoding and tracking queries."""
    parsed = urlsplit(value)
    return parsed.scheme.lower(), parsed.netloc.lower(), unquote(parsed.path)


def _artwork_identity(artist: Any, title: Any) -> tuple[str, str]:
    def normalize(value: Any) -> str:
        text = unicodedata.normalize("NFKD", str(value)).casefold()
        text = "".join(c for c in text if not unicodedata.combining(c))
        return " ".join(re.findall(r"\w+", text))
    return normalize(artist), normalize(title)


def validate_source_snapshot(
    record: Mapping[str, Any], snapshot: Mapping[str, Any], *, image_sha1: str,
) -> dict[str, Any]:
    """Verify saved provider metadata and its recorded reuse conditions.

    Commons supplies file SHA-1; the Met snapshot supplies image membership and
    its public-domain flag, while acquisition SHA-256 binds the downloaded bytes.
    Neither is a blanket rights certification.
    """
    pid = record["painting_id"]
    if record.get("source_provider") == "met":
        _require(snapshot["objectID"] == record["source_page_id"], f"{pid}: Met object ID mismatch")
        _require(_source_url_identity(snapshot["objectURL"]) == _source_url_identity(record["source_url"]), f"{pid}: Met object URL mismatch")
        urls = [snapshot["primaryImage"], *snapshot.get("additionalImages", [])]
        _require(_source_url_identity(record["source_image_url"]) in {_source_url_identity(url) for url in urls}, f"{pid}: image not in Met snapshot")
        _require(snapshot.get("isPublicDomain") is True and record["license"] == "CC0", f"{pid}: Met public-domain/CC0 statement missing")
        _require(record.get("license_url") == "https://creativecommons.org/publicdomain/zero/1.0/", f"{pid}: incorrect CC0 URL")
        return {"painting_id": pid, "source_page_id": snapshot["objectID"],
                "source_page_revision_id": None, "source_page_revision_timestamp": None,
                "source_file_timestamp": None, "source_file_sha1": image_sha1,
                "source_license_statement": "CC0", "rights_status": "cc0_met_open_access",
                "source_identity_basis": "saved_object_image_url_and_local_acquisition_sha256",
                "source_metadata_verified": True}
    page = snapshot["query"]["pages"][str(record["source_page_id"])]
    info = page["imageinfo"][0]
    _require(page["pageid"] == record["source_page_id"], f"{pid}: source page ID mismatch")
    _require(page.get("revisions") == record["source_page_revision"] and bool(page.get("revisions")), f"{pid}: source revision mismatch")
    _require(_source_url_identity(info["descriptionurl"]) == _source_url_identity(record["source_url"]), f"{pid}: source page URL mismatch")
    _require(_source_url_identity(info["url"]) == _source_url_identity(record["source_image_url"]), f"{pid}: source image URL mismatch")
    for key, field in (("width", "raw_width"), ("height", "raw_height"), ("size", "raw_size_bytes")):
        _require(int(info[key]) == record[field], f"{pid}: source metadata {key} mismatch")
    _require(str(info["sha1"]).lower() == image_sha1.lower(), f"{pid}: original-file SHA-1 mismatch")
    metadata = info["extmetadata"]
    license_name = str(metadata.get("LicenseShortName", {}).get("value", ""))
    copyright_value = str(metadata.get("Copyrighted", {}).get("value", ""))
    restrictions = str(metadata.get("Restrictions", {}).get("value", "")).strip()
    allowed_licenses = {"public domain", "cc by 2.0", "cc by-sa 4.0"}
    _require(license_name.casefold() in allowed_licenses, f"{pid}: unsupported source reuse statement")
    if license_name.casefold() == "public domain":
        _require(copyright_value.casefold() == "false" and "public domain" in record["license"].casefold(), f"{pid}: saved public-domain statement missing or inconsistent")
    else:
        _require(record["license"].casefold() == license_name.casefold(), f"{pid}: catalog licence mismatch")
        _require(bool(record.get("source_credit")) and bool(record.get("source_photographer")), f"{pid}: attribution missing")
        _require(record.get("license_url", "").rstrip("/") == metadata.get("LicenseUrl", {}).get("value", "").rstrip("/") and bool(record.get("license_url")), f"{pid}: licence URL mismatch")
    _require(not restrictions, f"{pid}: additional source restrictions require review: {restrictions}")
    return {
        "painting_id": pid, "source_page_id": page["pageid"],
        "source_page_revision_id": page["revisions"][0]["revid"],
        "source_page_revision_timestamp": page["revisions"][0]["timestamp"],
        "source_file_timestamp": info["timestamp"], "source_file_sha1": image_sha1,
        "source_license_statement": license_name,
        "rights_status": "public_domain_as_stated_by_source" if license_name.casefold() == "public domain" else "attribution_licence_as_stated_by_source",
        "source_metadata_verified": True,
    }


def normalize_real_damage_source(image: Image.Image) -> Image.Image:
    """Drop only fully opaque alpha; never composite, recolour, crop or save raw."""
    if image.mode == "RGB":
        return image
    _require(image.mode == "RGBA" and image.getchannel("A").getextrema() == (255, 255),
             "D03 accepts RGB or fully opaque RGBA only; transparent pixels require review")
    converted = image.convert("RGB")
    converted.info.update(image.info)  # retain ICC/EXIF for unchanged canonical policy
    return converted


def audit_real_damage_sources(
    project_root: str | Path, config: Mapping[str, Any], catalog: Mapping[str, Any],
    inputs: Mapping[str, Path], *, previous_validation: ValidationCollector | None = None,
) -> dict[str, Any]:
    """Decode and audit ten sources; return normalized records without writing.

    Reuses N01's image audit, minimum-resolution policy and dHash screen. Neither
    image bytes nor notebook-owned artifacts are changed. Near-duplicate hits
    require review and are not automatically declared duplicate artworks.
    """
    from .dataset_verification import (
        audit_image_collection, hamming_distance_hex, load_dataset_config,
    )
    from .preprocessing import load_preprocessing_config

    root = Path(project_root).resolve()
    validate_real_damage_config(config)
    validate_approved_sources(catalog, config)
    collector = ValidationCollector()
    if previous_validation is not None:
        collector.extend(c for c in previous_validation.checks if c.validation_stage != SOURCE_AUDIT_STAGE)

    def check(identifier: str, description: str, passed: bool, observed: Any, expected: Any = True) -> None:
        collector.add(validation_stage=SOURCE_AUDIT_STAGE, check_id=identifier,
                      check_description=description, severity="blocking",
                      expected=expected, observed=observed, passed=passed)

    # Fail before processing if notebook globals refer to older inputs/helpers.
    for row in catalog["records"]:
        pid = row["painting_id"]
        _require(inputs[f"source_image.{pid}"] == resolve_repo_path(row["raw_image_path"], root), f"{pid}: stale source path declaration")
        _require(inputs[f"source_metadata.{pid}"] == resolve_repo_path(row["source_metadata_path"], root), f"{pid}: stale metadata path declaration")
    source_config = copy.deepcopy(load_dataset_config(inputs["controlled_dataset_config"]))
    # D03-only source formats. The Controlled-300 configuration is never edited.
    source_config["validation"].update(allowed_extensions=[".jpg", ".jpeg", ".png"],
        allowed_image_formats=["JPEG", "PNG"], allowed_image_modes=["RGB", "RGBA"])
    preprocessing_config = load_preprocessing_config(inputs["preprocessing_config"])
    raw_metadata = pd.DataFrame([
        {"painting_id": r["painting_id"], "filename": Path(r["raw_image_path"]).name,
         "original_width": r["raw_width"], "original_height": r["raw_height"]}
        for r in catalog["records"]
    ])
    source_directory = inputs[f"source_image.{catalog['records'][0]['painting_id']}"].parent
    image_result = audit_image_collection(raw_metadata, source_directory, source_config, root)
    images = image_result.images.copy()
    image_lookup = images.set_index("painting_id", drop=False)
    controlled = pd.read_csv(inputs["controlled_artworks"], dtype=str, keep_default_na=False)
    required = {"painting_id", "artist", "title", "raw_sha256", "raw_dhash64", "dataset_scope", "acceptance_status"}
    _require(required.issubset(controlled.columns), "N01 artwork columns are incomplete")
    _require(len(controlled) == 300 and controlled["painting_id"].is_unique, "Expected 300 unique N01 paintings")
    _require(controlled["dataset_scope"].eq("controlled_300").all() and controlled["acceptance_status"].eq("accepted").all(), "N01 population is not the accepted Controlled-300 set")
    _require(controlled["raw_sha256"].str.fullmatch(r"[0-9a-f]{64}").all(), "N01 full image hashes are incomplete")
    _require(controlled["raw_dhash64"].str.fullmatch(r"[0-9a-f]{16}").all(), "N01 dHash values are incomplete")
    threshold = int(source_config["validation"]["near_duplicate"]["hamming_distance_threshold"])
    check("source_count", "All approved sources remain in the image audit", len(images) == 10, len(images), 10)
    check("source_orphans", "No unregistered source images", not image_result.orphan_image_paths, list(image_result.orphan_image_paths), [])
    check("within_cohort_exact_duplicates", "No exact duplicate source files", not image_result.exact_duplicate_groups, list(image_result.exact_duplicate_groups), [])
    check("within_cohort_near_duplicates", "No unresolved near-duplicate screening hits", image_result.near_duplicate_candidates.empty, image_result.near_duplicate_candidates.to_dict("records"), [])
    provenance_rows, overlap_rows, artwork_rows = [], [], []
    for index, record in enumerate(catalog["records"], 1):
        pid = record["painting_id"]
        image = image_lookup.loc[pid].to_dict()
        image_path, metadata_path = inputs[f"source_image.{pid}"], inputs[f"source_metadata.{pid}"]
        decode_fields = ("image_verified", "image_loaded", "width_matches_metadata", "height_matches_metadata", "minimum_resolution_passed", "extension_allowed", "format_allowed", "mode_allowed")
        check(f"decode:{pid}", "JPEG/PNG decoding, dimensions, supported source mode and resolution", all(bool(image[k]) for k in decode_fields) and not image["issue"], {k: image[k] for k in decode_fields} | {"issue": image["issue"]})
        raw_matches = (
            isinstance(image["raw_sha256"], str)
            and image["raw_sha256"] == record["raw_sha256"]
            and not pd.isna(image["raw_size_bytes"])
            and image["raw_size_bytes"] == record["raw_size_bytes"]
        )
        check(f"raw_hash:{pid}", "Decoded source matches approved bytes and size", raw_matches, {"sha256": image["raw_sha256"], "size": image["raw_size_bytes"]}, {"sha256": record["raw_sha256"], "size": record["raw_size_bytes"]})
        provenance = {"painting_id": pid, "source_metadata_verified": False, "rights_status": "unverified"}
        try:
            _require(sha256_file(metadata_path) == record["source_metadata_sha256"], "Saved source metadata bytes changed")
            snapshot = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
            file_sha1 = hashlib.sha1(image_path.read_bytes()).hexdigest()
            provenance = validate_source_snapshot(record, snapshot, image_sha1=file_sha1)
            check(f"provenance:{pid}", "Snapshot revision, URLs, file identity and recorded rights statement", True, "saved source and original image agree")
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            provenance["issue"] = f"{type(exc).__name__}: {exc}"
            check(f"provenance:{pid}", "Snapshot revision, URLs, file identity and recorded rights statement", False, provenance["issue"])
        provenance_rows.append(provenance)
        orientation, icc_ok, icc_description, colour_policy = None, False, "", "unverified"
        normalization = "unverified"
        try:
            with Image.open(image_path) as original:
                mode_before = original.mode
                original = normalize_real_damage_source(original)
                normalization = "drop_fully_opaque_alpha_rgb_unchanged" if mode_before == "RGBA" else "none_rgb_input"
                orientation = int(original.getexif().get(274, 1))
                profile_bytes = original.info.get("icc_profile")
                if not profile_bytes:
                    colour_policy = preprocessing_config["color"]["missing_icc_action"]
                else:
                    profile = ImageCms.ImageCmsProfile(io.BytesIO(profile_bytes))
                    icc_description = ImageCms.getProfileDescription(profile).strip()
                    tokens = preprocessing_config["color"]["accepted_profile_description_tokens"]
                    if any(str(t).lower() in icc_description.lower() for t in tokens):
                        colour_policy = preprocessing_config["color"]["embedded_srgb_action"]
                    else:
                        ImageCms.buildTransformFromOpenProfiles(
                            profile, ImageCms.createProfile("sRGB"), original.mode, "RGB",
                            renderingIntent=ImageCms.Intent.PERCEPTUAL,
                        )
                        colour_policy = preprocessing_config["color"]["non_srgb_action"]
                icc_ok = True
            check(f"colour:{pid}", "ICC profile is readable and existing colour policy is applicable", True, colour_policy)
        except (OSError, ValueError, TypeError, ImageCms.PyCMSError) as exc:
            check(f"colour:{pid}", "ICC profile is readable and existing colour policy is applicable", False, f"{type(exc).__name__}: {exc}")
        check(f"orientation:{pid}", "EXIF orientation needs no unapproved transformation", orientation == preprocessing_config["orientation"]["expected_exif_orientation"], orientation, 1)
        exact = controlled.loc[controlled["raw_sha256"].eq(record["raw_sha256"]), "painting_id"].tolist()
        identity = _artwork_identity(record["artist"], record["title"])
        identity_hits = [r.painting_id for r in controlled.itertuples() if _artwork_identity(r.artist, r.title) == identity]
        near_hits, closest_id, closest_distance = [], "", None
        if isinstance(image["raw_dhash64"], str):
            distances = sorted((hamming_distance_hex(image["raw_dhash64"], r.raw_dhash64), r.painting_id) for r in controlled.itertuples())
            closest_distance, closest_id = distances[0]
            near_hits = [p for distance, p in distances if distance <= threshold]
        overlap = {
            "painting_id": pid, "exact_hash_matches": exact,
            "normalized_title_artist_matches": identity_hits, "near_duplicate_candidates": near_hits,
            "nearest_controlled_painting_id": closest_id, "nearest_dhash_distance": closest_distance,
            "near_duplicate_threshold": threshold,
            "prior_artwork_review": record.get("controlled_300_artwork_overlap_review", ""),
        }
        overlap_rows.append(overlap)
        check(f"overlap:{pid}", "No exact-file, title/artist or unresolved near-duplicate match in N01", not exact and not identity_hits and not near_hits and closest_distance is not None, {"exact": exact, "identity": identity_hits, "screening_candidates": near_hits}, {"exact": [], "identity": [], "screening_candidates": []})
        # Descriptive metadata stays in artworks; geometry is owned by later tables.
        artwork = {k: record.get(k) for k in (
            "dataset_id", "dataset_version", "dataset_scope", "painting_id", "review_id", "title", "artist",
            "date_or_period", "category", "medium", "source", "source_url", "source_image_url", "license",
            "license_url", "source_credit", "source_provider", "source_photographer", "derivative_notice",
            "rights_basis", "source_selection_status", "source_selection_date",
            "source_metadata_path", "source_metadata_sha256", "retrieved_utc", "damage_origin",
            "damage_observation", "condition_evidence", "selection_reason", "annotation_cautions",
            "provisional_geometry_analogy", "controlled_300_artwork_overlap_review",
        )}
        artwork.update({k: v for k, v in image.items() if k.startswith("raw_")})
        failed_ids = [c.check_id for c in collector.checks if c.validation_stage == SOURCE_AUDIT_STAGE and c.check_id.endswith(f":{pid}") and not c.passed]
        artwork.update({
            "schema_version": config["schemas"]["artworks"], "dataset_sort_index": index,
            "style_or_period": record.get("style_or_period"),
            "raw_exif_orientation": orientation, "raw_icc_profile_description": icc_description,
            "colour_policy": colour_policy, "icc_policy_valid": icc_ok,
            "source_normalization": normalization,
            "rights_status": provenance["rights_status"],
            "source_page_revision_id": provenance.get("source_page_revision_id"),
            "source_metadata_verified": provenance["source_metadata_verified"],
            "has_clean_reference": False, "clean_image_path": None,
            "mask_review_status": "not_started", "acceptance_status": "blocked" if failed_ids else "accepted",
            "exclusion_reason": ";".join(failed_ids),
            "nearest_controlled_painting_id": closest_id, "nearest_dhash_distance": closest_distance,
        })
        artwork_rows.append(artwork)
    artworks = pd.DataFrame(artwork_rows)
    check("artwork_handoff", "Ten uniquely keyed accepted source records", len(artworks) == 10 and artworks["painting_id"].is_unique and artworks["acceptance_status"].eq("accepted").all(), {"rows": len(artworks), "accepted": int(artworks["acceptance_status"].eq("accepted").sum())}, {"rows": 10, "accepted": 10})
    check("reference_absence", "Audited source records retain no clean reference", artworks["has_clean_reference"].eq(False).all() and artworks["clean_image_path"].isna().all(), "no reference" if artworks["clean_image_path"].isna().all() else "unexpected reference", "no reference")
    return {
        "validation": collector, "artworks": artworks, "image_audit": images,
        "provenance_audit": pd.DataFrame(provenance_rows),
        "overlap_audit": pd.DataFrame(overlap_rows),
        "near_duplicate_candidates": image_result.near_duplicate_candidates,
        "source_validation_policy": source_config["validation"],
        "preprocessing_config": preprocessing_config,
    }


def _write_smoke_bytes(path: Path, payload: bytes) -> None:
    """Atomically write an already-guarded smoke file; leave identical files alone."""
    if path.is_file() and path.read_bytes() == payload:
        return
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


def _smoke_preview(sources: list[Image.Image], canvases: list[Image.Image],
                   rows: list[dict[str, Any]], dpi: int) -> bytes:
    """Render source/processed pairs; the content outline is a display overlay only."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.patches import Rectangle

    figure = Figure(figsize=(10, 3.65 * len(rows) + 0.7), dpi=dpi, facecolor="white")
    FigureCanvasAgg(figure)
    axes = figure.subplots(len(rows), 2, squeeze=False)
    figure.subplots_adjust(left=0.03, right=0.97, bottom=0.025, top=0.92, hspace=0.22, wspace=0.12)
    figure.suptitle("D03 preprocessing smoke test\nOriginal source (left) / 768-pixel input (right); cyan = content bounds, not damage mask", fontsize=11)
    for index, (source, canvas, row) in enumerate(zip(sources, canvases, rows)):
        source_axis, processed_axis = axes[index]
        source_axis.imshow(source)
        processed_axis.imshow(canvas)
        source_axis.set_title(f"{row['painting_id']} | {row['category'].replace('_', ' ')}\nOriginal: {row['original_width']} x {row['original_height']}", fontsize=10)
        processed_axis.set_title(f"Processed: 768 x 768 RGB | padding {row['padding_area_fraction']:.1%}\nContent: {row['content_width']} x {row['content_height']}", fontsize=10)
        processed_axis.add_patch(Rectangle(
            (row['content_x_min'] - 0.5, row['content_y_min'] - 0.5),
            row['content_width'], row['content_height'], fill=False,
            edgecolor="#00b8d4", linewidth=1.1,
        ))
        for axis in (source_axis, processed_axis):
            axis.set_axis_off()
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=dpi, facecolor="white")
    figure.clear()
    return buffer.getvalue()


def run_real_damage_smoke(
    project_root: str | Path, config: Mapping[str, Any], catalog: Mapping[str, Any],
    artworks: pd.DataFrame, preprocessing_config: Mapping[str, Any], *,
    previous_validation: ValidationCollector,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Check five representative inputs using unchanged N02 processing.

    Writes five temporary PNGs and one QA sheet, all below work/. Existing
    images must match the fresh deterministic encoding; stale files are reported
    rather than overwritten. No masks, clean references or canonical tables are
    created. The returned gate covers numerical checks, not human visual approval.
    """
    from .preprocessing import build_preprocessed_image, load_preprocessing_config
    from .regions import content_region

    started = perf_counter()
    root = Path(project_root).resolve()
    validate_real_damage_config(config)
    validate_approved_sources(catalog, config)
    collector = ValidationCollector()
    collector.extend(c for c in previous_validation.checks if c.validation_stage != SMOKE_STAGE)
    _require(collector.overall_passed, "Resolve earlier validation failures before preprocessing")
    for stage in (PREFLIGHT_STAGE, SOURCE_AUDIT_STAGE):
        _require(any(c.validation_stage == stage for c in collector.checks), f"Missing prerequisite: {stage}")
    _require(len(artworks) == 10 and artworks["painting_id"].is_unique
             and set(artworks["painting_id"]) == set(config["dataset"]["painting_ids"])
             and artworks["acceptance_status"].eq("accepted").all(), "Batch 2 must hand off ten accepted sources")
    _require(artworks["has_clean_reference"].eq(False).all()
             and artworks["clean_image_path"].isna().all(), "Smoke inputs cannot claim a clean reference")
    prep_path = resolve_repo_path(config["inputs"]["preprocessing_config"], root)
    _require(preprocessing_config == load_preprocessing_config(prep_path), "Stale preprocessing configuration; rerun Batch 2")
    for rel in (config["inputs"]["preprocessing_config"], config["inputs"]["helper_sources"]["preprocessing"]):
        _require(sha256_file(resolve_repo_path(rel, root)) == catalog["pipeline_baseline_sha256"][rel], f"Preprocessing baseline changed: {rel}")
    smoke_ids = config["execution"]["smoke_painting_ids"]
    selected = artworks.set_index("painting_id", drop=False).loc[smoke_ids]
    _require(Counter(selected["category"]) == Counter(CATEGORIES), "Smoke requires one painting per category")
    approved = {r["painting_id"]: r for r in catalog["records"]}
    for row in selected.to_dict("records"):
        for field in ("raw_image_path", "raw_sha256", "raw_width", "raw_height", "category"):
            _require(row[field] == approved[row["painting_id"]][field], f"Stale Batch 2 record: {row['painting_id']} / {field}")

    smoke_root = require_notebook_output_path(
        notebook_output_root(NOTEBOOK_STEM, root) / config["smoke"]["directory"], NOTEBOOK_STEM, root,
    )
    expected_root = (root / "outputs" / NOTEBOOK_STEM / "work" / "preprocessing_smoke").absolute()
    _require(smoke_root == expected_root, "Smoke directory resolves outside its fixed work location")

    def output_path(name: str) -> Path:
        path = require_notebook_output_path(smoke_root / name, NOTEBOOK_STEM, root)
        _require(path.parent == smoke_root, "Smoke file resolves outside its work directory")
        return path

    targets = {pid: output_path(config["smoke"]["image_filename_template"].format(painting_id=pid)) for pid in smoke_ids}
    preview_path = output_path(config["smoke"]["preview_filename"])
    expected_files = set(targets.values()) | {preview_path}
    unexpected = [str(p) for p in smoke_root.iterdir() if p.resolve() not in expected_files] if smoke_root.exists() else []
    _require(not unexpected, f"Unexpected smoke files require review (nothing deleted): {unexpected}")

    def check(identifier: str, description: str, passed: bool, observed: Any, expected: Any = True) -> None:
        collector.add(validation_stage=SMOKE_STAGE, check_id=identifier,
                      check_description=description, severity="blocking",
                      expected=expected, observed=observed, passed=passed)

    check("selection", "Five approved representatives, one per category", True, smoke_ids, smoke_ids)
    check("processing_contract", "Unchanged N02 processing, orientation and colour policy", True, "verified")
    # Validate all sources and existing targets before writing any smoke file.
    prepared, source_previews, canvases = [], [], []
    processing = preprocessing_config["processing"]
    for source_row in selected.to_dict("records"):
        pid = source_row["painting_id"]
        raw_path = resolve_repo_path(source_row["raw_image_path"], root)
        raw_bytes = raw_path.read_bytes()
        _require(hashlib.sha256(raw_bytes).hexdigest() == source_row["raw_sha256"], f"Source changed: {pid}")
        with Image.open(io.BytesIO(raw_bytes)) as source:
            source.load()
            canvas, geometry = build_preprocessed_image(normalize_real_damage_source(source), source_row, preprocessing_config)
            preview = source.convert("RGB")
            preview.thumbnail((768, 768), Image.Resampling.LANCZOS)
        payload = io.BytesIO()
        canvas.save(payload, format="PNG", optimize=bool(processing["png_optimize"]),
                    compress_level=int(processing["png_compress_level"]))
        encoded = payload.getvalue()
        target = targets[pid]
        _require(not target.exists() or (target.is_file() and target.read_bytes() == encoded), f"Stale smoke output requires review: {target}")
        row = {
            "schema_version": "real_damage_preprocessing_smoke.v1", "artifact_role": "temporary_smoke",
            "painting_id": pid, "category": source_row["category"], "title": source_row["title"],
            "raw_image_path": source_row["raw_image_path"], "source_sha256": source_row["raw_sha256"],
            "processed_path": to_repo_relative(target, root), "sha256": hashlib.sha256(encoded).hexdigest(),
            "preprocessing_config_sha256": sha256_file(prep_path),
            "has_clean_reference": False, "clean_image_path": None, **geometry,
        }
        prepared.append((source_row, row, raw_path, target, encoded))
        source_previews.append(preview)
        canvases.append(canvas)

    rows = []
    for index, (source_row, row, raw_path, target, encoded) in enumerate(prepared):
        pid = row["painting_id"]
        reused = target.is_file()
        _write_smoke_bytes(target, encoded)
        with Image.open(target) as image:
            image.load()
            array = np.asarray(image)
            check(f"format:{pid}", "Reloaded smoke image is 768 x 768 RGB PNG", image.size == (768, 768) and image.mode == "RGB" and image.format == "PNG", [*image.size, image.mode, image.format], [768, 768, "RGB", "PNG"])
            check(f"colour:{pid}", "Expected colour policy and stripped output metadata", not image.info.get("icc_profile") and not image.getexif() and row["color_space_policy"] == source_row["colour_policy"], row["color_space_policy"], source_row["colour_policy"])
        check(f"pixels:{pid}", "PNG round trip preserves every preprocessed pixel", np.array_equal(array, np.asarray(canvases[index])) and sha256_file(target) == row["sha256"], sha256_file(target), row["sha256"])
        x0, y0, x1, y1 = [int(row[k]) for k in ("content_x_min", "content_y_min", "content_x_max", "content_y_max")]
        region = content_region((768, 768), (x0, y0, x1, y1))
        geometry_ok = (region.validity_status == "valid"
                       and (x1 - x0, y1 - y0) == (row["resized_width"], row["resized_height"])
                       and (x0, y0, 768 - x1, 768 - y1) == (row["pad_left"], row["pad_top"], row["pad_right"], row["pad_bottom"])
                       and (x1 - x0) * (y1 - y0) == row["content_area_pixels"]
                       and row["content_area_pixels"] + row["padding_area_pixels"] == 768 * 768
                       and abs(row["pad_left"] - row["pad_right"]) <= 1
                       and abs(row["pad_top"] - row["pad_bottom"]) <= 1)
        check(f"geometry:{pid}", "Exclusive content bounds, area and centred padding reconcile", geometry_ok, [x0, y0, x1, y1])
        outside = np.ones((768, 768), dtype=bool)
        outside[y0:y1, x0:x1] = False
        pad_rgb = [row[f"padding_color_{channel}"] for channel in "rgb"]
        check(f"padding:{pid}", "All padding pixels match the recorded source median", bool(np.all(array[outside] == pad_rgb)), pad_rgb, pad_rgb)
        check(f"source_unchanged:{pid}", "Original source bytes remain unchanged", sha256_file(raw_path) == row["source_sha256"], sha256_file(raw_path), row["source_sha256"])
        rows.append(row)
        if progress_callback is not None:
            progress_callback({"painting_id": pid, "completed": index + 1, "total": len(prepared), "reused": reused, "elapsed_seconds": perf_counter() - started})

    check("unique_outputs", "Five distinct processed images", len({r['sha256'] for r in rows}) == 5, len({r['sha256'] for r in rows}), 5)
    if collector.overall_passed:
        _write_smoke_bytes(preview_path, _smoke_preview(source_previews, canvases, rows, config["smoke"]["figure_dpi"]))
        with Image.open(preview_path) as preview:
            preview.verify()
        check("preview", "Source/processed QA sheet is saved and decodes", True, to_repo_relative(preview_path, root))
    actual_files = {p.resolve() for p in smoke_root.iterdir() if p.is_file()}
    check("file_set", "Only five temporary images and one preview are present", actual_files == expected_files, sorted(p.name for p in actual_files), sorted(p.name for p in expected_files))
    return {"validation": collector, "images": pd.DataFrame(rows), "preview_path": preview_path,
            "work_root": smoke_root, "elapsed_seconds": perf_counter() - started,
            "visual_review_status": "pending_user_inspection"}


def validate_binary_damage_mask(
    mask: Image.Image | np.ndarray, *, content_box: tuple[int, int, int, int],
    size: tuple[int, int] = (768, 768),
) -> np.ndarray:
    """Return a boolean reviewed-mask candidate; reject rather than repair bad masks."""
    if isinstance(mask, Image.Image):
        _require(mask.mode == "L", "Canonical mask must have mode L")
    array = np.asarray(mask)
    _require(array.dtype == np.uint8 and array.ndim == 2, "Mask must be a uint8 two-dimensional image")
    _require(array.shape == (size[1], size[0]), "Mask has incorrect dimensions")
    _require(set(np.unique(array)).issubset({0, 255}), "Mask must contain only 0 and 255; no implicit thresholding")
    x0, y0, x1, y1 = content_box
    _require(all(isinstance(x, (int, np.integer)) for x in content_box) and 0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1], "Invalid exclusive content bounds")
    binary = array == 255
    _require(bool(binary.any()), "Damage mask is empty")
    inside = np.zeros_like(binary)
    inside[y0:y1, x0:x1] = True
    _require(not bool((binary & ~inside).any()), "Damage mask overlaps padding")
    return binary


def validate_review_binding(review: Mapping[str, Any], *, input_path: str | Path, mask_path: str | Path) -> None:
    """Reject unreviewed/edited masks; approval is tied to exact file bytes."""
    _require(review.get("review_status") in {"approved", "approved_with_ambiguity"}, "Mask has not been approved")
    for key in ("reviewer", "reviewed_at_utc", "target_description"):
        _require(bool(str(review.get(key) or "").strip()), f"Review is missing {key}")
    _require(review.get("input_sha256") == sha256_file(input_path), "Reviewed input changed")
    _require(review.get("mask_sha256") == sha256_file(mask_path), "Reviewed mask changed; repeat review")


def audit_inference_mask(mask: Image.Image | np.ndarray, *, content_box: tuple[int, int, int, int]) -> dict[str, Any]:
    """Measure exact nearest-neighbour 768-to-512 loss without broadening damage.

    Eight-connected source components follow the existing morphology helper.
    Report original component IDs with zero surviving sampled pixels. Any
    geometry change is presented for review, not assigned an accuracy meaning.
    """
    from scipy.ndimage import label

    binary = validate_binary_damage_mask(mask, content_box=content_box)
    labels, count = label(binary, structure=np.ones((3, 3), dtype=np.uint8))
    sampled = np.asarray(Image.fromarray(labels.astype(np.int32)).resize((512, 512), Image.Resampling.NEAREST))
    resized = sampled > 0
    present = set(np.unique(sampled)) - {0}
    vanished = sorted(set(range(1, count + 1)) - present)
    returned = np.asarray(Image.fromarray(resized.astype(np.uint8)).resize((768, 768), Image.Resampling.NEAREST)) > 0
    union = binary | returned
    intersection = binary & returned
    return {
        "source_size": 768, "inference_size": 512,
        "source_mask_pixels": int(binary.sum()), "inference_mask_pixels": int(resized.sum()),
        "source_component_count": int(count), "disappeared_component_count": len(vanished),
        "disappeared_component_ids": vanished,
        "source_canvas_fraction": float(binary.mean()),
        "inference_canvas_fraction": float(resized.mean()),
        "roundtrip_iou": float(intersection.sum() / union.sum()),
        "empty_inference_mask": not bool(resized.any()),
        "geometry_change_requires_review": not np.array_equal(binary, returned),
        "sd_eligible_without_review": False,
        "resize_policy": "nearest_768_to_512_no_dilation",
    }
