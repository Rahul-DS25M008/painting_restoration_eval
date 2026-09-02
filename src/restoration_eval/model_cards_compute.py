"""Model-card, compute, and transparent scaling utilities for Notebook 30.

The module consumes validated Notebook 09--29 artifacts.  It performs no model
inference, does not modify upstream outputs, and never presents projections as
executed results or runtime-adjusted anchor counts as a quality score.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml

from .paths import find_project_root, resolve_repo_path


MODULE_NAME = "restoration_eval.model_cards_compute"
MODULE_VERSION = "1.0.0"
CONFIG_SCHEMA_VERSION = "model_cards_compute_config.v1"
MODEL_CARD_SCHEMA_VERSION = "model_cards.v1"
COMPUTE_SCHEMA_VERSION = "compute_scalability.v1"

MODEL_CARD_COLUMNS = (
    "model_card_id", "model_id", "display_name", "evaluation_status",
    "model_family", "methodological_role", "original_purpose",
    "implementation", "implementation_version", "model_identifier",
    "model_revision", "configuration_id", "software_license",
    "weight_license", "license_scope_note", "training_data_description",
    "training_data_transparency", "intended_uses_json", "excluded_uses_json",
    "deterministic", "stochastic", "prompt_dependent", "seed_policy",
    "domain_gap", "bias_notes", "known_limitations_json",
    "strengths_json", "weaknesses_json", "hardware_requirements",
    "observed_hardware_json", "execution_device", "execution_backend",
    "precision", "inference_width", "inference_height", "output_width",
    "output_height", "input_constraints", "mask_constraints",
    "evaluated_painting_count", "evaluated_case_count",
    "evaluated_candidate_count", "model_inference_count",
    "zero_control_count", "completed_count", "failed_count", "retry_count",
    "failure_rate", "total_runtime_seconds", "mean_runtime_seconds",
    "median_runtime_seconds", "p95_runtime_seconds",
    "throughput_candidates_per_second", "gpu_peak_memory_bytes",
    "gpu_total_memory_bytes", "output_file_count", "output_storage_bytes",
    "restored_image_file_count", "restored_image_storage_bytes",
    "source_ids_json", "source_urls_json", "source_checked_at_utc",
    "schema_version", "status", "issue",
)

COMPUTE_COLUMNS = (
    "compute_row_id", "model_id", "evaluation_status", "record_type",
    "scenario_id", "summary_scope", "experiment_id", "dataset_scope",
    "painting_count", "case_count", "candidate_count", "inference_count",
    "zero_control_count", "completed_count", "failed_count", "retry_count",
    "failure_rate", "total_runtime_seconds", "mean_runtime_seconds",
    "median_runtime_seconds", "p95_runtime_seconds", "max_runtime_seconds",
    "throughput_candidates_per_second", "runtime_lower_seconds",
    "runtime_central_seconds", "runtime_upper_seconds", "projection_multiplier",
    "projection_basis", "sensitivity_is_confidence_interval",
    "gpu_peak_memory_bytes", "gpu_total_memory_bytes", "output_file_count",
    "output_storage_bytes", "projected_output_file_count",
    "projected_output_storage_bytes", "candidate_multiplier",
    "inference_width", "inference_height", "output_width", "output_height",
    "applicability_status", "is_executed", "is_projected", "schema_version",
    "status", "issue",
)


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    return config.get("model_cards_compute", config)


def _normalized_relative_path(value: Any) -> bool:
    text = str(value).strip()
    return bool(text) and not Path(text).is_absolute() and "\\" not in text


def _stable_id(prefix: str, *parts: Any) -> str:
    material = "|".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(material.encode('utf-8')).hexdigest()[:20]}"


def _as_bool(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if value is None or (not isinstance(value, (list, tuple, dict)) and pd.isna(value)):
        return False
    return str(value).strip().lower() in {"true", "1", "1.0", "yes", "y"}


def _json_list(value: Any) -> str:
    if value is None:
        return "[]"
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return "[]"
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            value = [text]
    if isinstance(value, Mapping):
        value = list(value)
    if not isinstance(value, (list, tuple, set)):
        value = [value]
    return json.dumps([str(item) for item in value if str(item).strip()], separators=(",", ":"))


def _first_nonempty(frame: pd.DataFrame, column: str, default: str = "") -> str:
    if column not in frame:
        return default
    values = frame[column].dropna().astype(str).str.strip()
    values = values[values.ne("")]
    return values.iloc[0] if len(values) else default


def _number(value: Any, default: float = np.nan) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if np.isfinite(number) else default


def _model_specs(config: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(item["model_id"]): item for item in _settings(config)["models"]}


def _source_lookup(config: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(item["source_id"]): item
        for item in _settings(config)["sources"]["records"]
    }


def load_model_cards_compute_config(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate the approved Notebook 30 contract."""

    with Path(path).open("r", encoding="utf-8-sig") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict) or config.get("config_schema_version") != CONFIG_SCHEMA_VERSION:
        raise ValueError("Unsupported model-cards/compute config schema")
    settings = _settings(config)
    required = {
        "notebook_id", "notebook_stem", "dataset_id", "dataset_version",
        "dataset_scope", "model_card_schema_version", "compute_schema_version",
        "inputs", "output", "models", "sources", "quality", "projections",
        "report", "expected_counts", "evidence_policy", "known_limitations",
    }
    missing = sorted(required - set(settings))
    if missing:
        raise ValueError(f"Model-cards/compute config is missing keys: {missing}")
    if settings["notebook_id"] != "30" or settings["notebook_stem"] != "30_model_cards_compute_and_scalability":
        raise ValueError("Notebook 30 identity contract changed")
    if settings["model_card_schema_version"] != MODEL_CARD_SCHEMA_VERSION:
        raise ValueError("Model-card schema differs from helper")
    if settings["compute_schema_version"] != COMPUTE_SCHEMA_VERSION:
        raise ValueError("Compute schema differs from helper")
    for key, value in settings["inputs"].items():
        if not _normalized_relative_path(value):
            raise ValueError(f"inputs.{key} must be a normalized repository-relative path")

    exact_output = {
        "root": "outputs/30_model_cards_compute_and_scalability",
        "model_cards_path": "data/model_cards.csv",
        "compute_scalability_path": "metrics/compute_scalability.csv",
        "model_card_reports_dir": "reports/model_cards",
        "quality_vs_compute_figure_path": "figures/quality_vs_compute.png",
        "scaling_projection_figure_path": "figures/scaling_projection.png",
        "run_manifest_path": "manifests/run_manifest.json",
        "artifacts_path": "manifests/artifacts.csv",
        "validation_path": "validation/checks.csv",
    }
    for key, expected in exact_output.items():
        if settings["output"].get(key) != expected:
            raise ValueError(f"output.{key} must equal {expected!r}")

    model_ids = [str(item["model_id"]) for item in settings["models"]]
    expected_model_ids = [
        "opencv_telea", "lama", "stable_diffusion_inpainting", "sdxl_inpainting"
    ]
    if model_ids != expected_model_ids or len(set(model_ids)) != 4:
        raise ValueError("The four-card model order or identity changed")
    source_ids = set(_source_lookup(config))
    for model in settings["models"]:
        missing_sources = set(model["source_ids"]) - source_ids
        if missing_sources:
            raise ValueError(f"Unknown sources for {model['model_id']}: {sorted(missing_sources)}")

    expected = settings["expected_counts"]
    runtime_total = sum(int(expected[key]) for key in (
        "telea_runtime_rows", "lama_runtime_rows",
        "stable_diffusion_runtime_rows", "sdxl_runtime_rows",
    ))
    if runtime_total != int(expected["observed_compute_rows"]):
        raise ValueError("Observed compute-row arithmetic is inconsistent")
    if int(expected["compute_rows"]) != int(expected["observed_compute_rows"]) + int(expected["projection_rows"]):
        raise ValueError("Total compute-row arithmetic is inconsistent")
    if int(expected["quality_anchor_rows"]) != int(settings["quality"]["anchor_count"]) * int(expected["quality_populations"]):
        raise ValueError("Quality-anchor arithmetic is inconsistent")
    if int(expected["model_card_report_count"]) != len(model_ids):
        raise ValueError("Model-card report arithmetic is inconsistent")
    if len(settings["report"]["required_section_ids"]) != 13:
        raise ValueError("The approved model-card structure must retain thirteen sections")
    if not settings["report"]["self_contained_text"] or not settings["report"]["approved_mock_structure_locked"]:
        raise ValueError("The approved portable Markdown card structure must remain locked")
    if settings["report"]["required_external_image_dependencies"] != 0:
        raise ValueError("Model cards may not require external images")
    if settings["quality"]["combined_quality_score_retained"] or settings["quality"]["runtime_in_quality_vote"]:
        raise ValueError("Runtime-adjusted or combined quality scores are prohibited")
    if settings["projections"]["sensitivity_is_confidence_interval"]:
        raise ValueError("Projection sensitivity bounds may not be called confidence intervals")
    expected_runtime_rules = {
        "runtime_lower_rule": "minimum_of_scaled_median_and_scaled_mean",
        "runtime_central_rule": "scaled_mean",
        "runtime_upper_rule": "maximum_of_scaled_p95_and_scaled_mean",
    }
    for field, expected_rule in expected_runtime_rules.items():
        if settings["projections"].get(field) != expected_rule:
            raise ValueError(f"projections.{field} must equal {expected_rule!r}")
    scenarios = {
        str(item["scenario_id"]): item
        for item in settings["projections"]["scenarios"]
    }
    expected_scenarios = {
        "projected_300_canonical_primary",
        "projected_300_current_design_mix",
    }
    if set(scenarios) != expected_scenarios:
        raise ValueError("The two approved projection scenarios changed")
    for scenario_id, scenario in scenarios.items():
        for field in (
            "target_case_count", "target_candidates",
            "target_inference_candidates", "target_zero_controls",
        ):
            if set(scenario.get(field, {})) != set(model_ids):
                raise ValueError(f"{scenario_id}.{field} must cover all four models")
        for model_id in model_ids:
            target = scenario["target_candidates"][model_id]
            inference = scenario["target_inference_candidates"][model_id]
            zero = scenario["target_zero_controls"][model_id]
            case_target = scenario["target_case_count"][model_id]
            values = (target, inference, zero, case_target)
            if all(value is None for value in values):
                continue
            if any(value is None for value in values):
                raise ValueError(f"{scenario_id}.{model_id} has partial projection arithmetic")
            if int(inference) + int(zero) != int(target):
                raise ValueError(f"{scenario_id}.{model_id} inference/zero arithmetic changed")
    canonical = scenarios["projected_300_canonical_primary"]
    if any(int(canonical["target_case_count"][model_id]) != 1500 for model_id in model_ids):
        raise ValueError("Canonical projection must retain 1,500 unique cases per model")
    current = scenarios["projected_300_current_design_mix"]
    if current["target_case_count"] != {
        "opencv_telea": 2460,
        "lama": 2460,
        "stable_diffusion_inpainting": 2460,
        "sdxl_inpainting": None,
    }:
        raise ValueError("Current-design projected case counts changed")
    if any(bool(value) for value in settings["evidence_policy"].values()):
        raise ValueError("A prohibited Notebook 30 evidence interpretation is enabled")
    return config


def resolve_model_cards_compute_inputs(
    config: Mapping[str, Any],
    project_root: str | Path | None = None,
    *,
    must_exist: bool = True,
) -> dict[str, Path]:
    """Resolve every declared input without latest-file or glob discovery."""

    root = find_project_root(project_root)
    return {
        str(key): resolve_repo_path(value, root, must_exist=must_exist)
        for key, value in _settings(config)["inputs"].items()
    }


def validate_upstream_completion(
    manifests: Mapping[str, Mapping[str, Any]],
    *,
    expected_notebook_ids: Sequence[str] = tuple(f"{n:02d}" for n in range(9, 30)),
) -> pd.DataFrame:
    """Return one strict completion row for every Notebook 09--29 producer."""

    rows = []
    for notebook_id in expected_notebook_ids:
        manifest = manifests.get(notebook_id)
        present = isinstance(manifest, Mapping)
        run_status = str(manifest.get("run_status", "")) if present else ""
        gate = bool(manifest.get("completion_gate_passed", False)) if present else False
        rows.append({
            "notebook_id": notebook_id,
            "manifest_present": present,
            "run_status": run_status,
            "completion_gate_passed": gate,
            "passed": present and gate and run_status.lower() in {"completed", "complete", "finished"},
            "details": f"run={run_status}; gate={gate}",
        })
    return pd.DataFrame(rows)


def summarize_output_storage(
    inventory: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Summarize notebook-owned files and restored-image storage per model."""

    required = {"relative_path", "size_bytes", "read_error_count"}
    missing = sorted(required - set(inventory.columns))
    if missing:
        raise ValueError(f"Inventory is missing columns: {missing}")
    paths = inventory["relative_path"].fillna("").astype(str).str.replace("\\", "/", regex=False)
    sizes = pd.to_numeric(inventory["size_bytes"], errors="coerce").fillna(0).astype("int64")
    errors = pd.to_numeric(inventory["read_error_count"], errors="coerce").fillna(0).astype(int)
    rows = []
    for model_id, spec in _model_specs(config).items():
        prefix = str(spec["output_root"]).rstrip("/") + "/"
        owned = paths.str.startswith(prefix)
        restored = owned & paths.str.contains("/images/restored/", regex=False)
        rows.append({
            "model_id": model_id,
            "output_root": spec["output_root"],
            "output_file_count": int(owned.sum()),
            "output_storage_bytes": int(sizes[owned].sum()),
            "restored_image_file_count": int(restored.sum()),
            "restored_image_storage_bytes": int(sizes[restored].sum()),
            "fixed_file_count": int(owned.sum() - restored.sum()),
            "fixed_storage_bytes": int(sizes[owned].sum() - sizes[restored].sum()),
            "read_error_count": int(errors[owned].sum()),
        })
    return pd.DataFrame(rows)


def build_model_cards(
    candidate_tables: Mapping[str, pd.DataFrame],
    runtime_tables: Mapping[str, pd.DataFrame],
    manifests: Mapping[str, Mapping[str, Any]],
    storage: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the four-row canonical model-card table from observed evidence."""

    settings = _settings(config)
    sources = _source_lookup(config)
    storage_lookup = storage.set_index("model_id").to_dict("index")
    manifest_ids = {
        "opencv_telea": "09", "lama": "10",
        "stable_diffusion_inpainting": "11", "sdxl_inpainting": "12",
    }
    rows = []
    for spec in settings["models"]:
        model_id = str(spec["model_id"])
        candidates = candidate_tables[model_id].copy()
        runtime = runtime_tables[model_id].copy()
        manifest = manifests[manifest_ids[model_id]]
        overall = runtime.loc[
            runtime["summary_scope"].astype(str).eq("overall")
            & runtime["experiment_id"].astype(str).eq("all")
        ]
        if len(overall) != 1:
            raise ValueError(f"{model_id} must have exactly one overall runtime row")
        overall_row = overall.iloc[0]
        completed = int(candidates.get("status", pd.Series(dtype=str)).astype(str).str.lower().eq("completed").sum())
        failed = int(len(candidates) - completed)
        retries = int(pd.to_numeric(candidates.get("retry_count", 0), errors="coerce").fillna(0).sum())
        hardware = dict(manifest.get("hardware", {}))
        package_versions = dict(manifest.get("package_versions", {}))
        implementation_version_field = str(spec["implementation_version_field"])
        implementation_version = _first_nonempty(candidates, implementation_version_field)
        if not implementation_version:
            implementation_version = str(package_versions.get("opencv-python", package_versions.get("IOPaint", "")))
        source_ids = list(spec["source_ids"])
        source_urls = [str(sources[source_id]["url"]) for source_id in source_ids]
        storage_row = storage_lookup[model_id]
        known = list(settings["known_limitations"])
        manifest_known = manifest.get("known_limitations", [])
        if isinstance(manifest_known, list):
            known.extend(str(item) for item in manifest_known)
        gpu_peak = _number(hardware.get("maximum_gpu_peak_bytes"))
        gpu_total = np.nan
        if "gpu_total_memory_bytes" in candidates:
            values = pd.to_numeric(candidates["gpu_total_memory_bytes"], errors="coerce").dropna()
            if len(values):
                gpu_total = float(values.max())
        row = {
            "model_card_id": _stable_id("model_card", model_id, MODEL_CARD_SCHEMA_VERSION),
            "model_id": model_id,
            "display_name": spec["display_name"],
            "evaluation_status": spec["evaluation_status"],
            "model_family": spec["model_family"],
            "methodological_role": spec["methodological_role"],
            "original_purpose": spec["original_purpose"],
            "implementation": spec["implementation"],
            "implementation_version": implementation_version,
            "model_identifier": spec["model_identifier"],
            "model_revision": _first_nonempty(candidates, "model_revision", _first_nonempty(candidates, "model_version")),
            "configuration_id": _first_nonempty(candidates, "configuration_id"),
            "software_license": spec["software_license"],
            "weight_license": spec["weight_license"],
            "license_scope_note": spec["license_scope_note"],
            "training_data_description": spec["training_data_description"],
            "training_data_transparency": spec["training_data_transparency"],
            "intended_uses_json": _json_list(spec["intended_uses"]),
            "excluded_uses_json": _json_list(spec["excluded_uses"]),
            "deterministic": bool(spec["deterministic"]),
            "stochastic": bool(spec["stochastic"]),
            "prompt_dependent": bool(spec["prompt_dependent"]),
            "seed_policy": "not_applicable" if not spec["stochastic"] else _first_nonempty(candidates, "seed", "configured_seed_policy"),
            "domain_gap": spec["domain_gap"],
            "bias_notes": spec["bias_notes"],
            "known_limitations_json": _json_list(known),
            "strengths_json": _json_list(spec["strengths"]),
            "weaknesses_json": _json_list(spec["weaknesses"]),
            "hardware_requirements": spec["hardware_requirements"],
            "observed_hardware_json": json.dumps(hardware, sort_keys=True, separators=(",", ":")),
            "execution_device": _first_nonempty(candidates, "device", str(hardware.get("execution_device", ""))),
            "execution_backend": _first_nonempty(candidates, "execution_backend", str(hardware.get("execution_backend", ""))),
            "precision": _first_nonempty(candidates, "precision"),
            "inference_width": spec.get("inference_width", np.nan),
            "inference_height": spec.get("inference_height", np.nan),
            "output_width": spec.get("output_width", np.nan),
            "output_height": spec.get("output_height", np.nan),
            "input_constraints": spec["input_constraints"],
            "mask_constraints": spec["mask_constraints"],
            "evaluated_painting_count": int(spec["evaluated_painting_count"]),
            "evaluated_case_count": int(spec["evaluated_case_count"]),
            "evaluated_candidate_count": int(spec["evaluated_candidate_count"]),
            "model_inference_count": int(spec["model_inference_count"]),
            "zero_control_count": int(spec["zero_control_count"]),
            "completed_count": completed,
            "failed_count": failed,
            "retry_count": retries,
            "failure_rate": float(failed / len(candidates)) if len(candidates) else np.nan,
            "total_runtime_seconds": _number(overall_row["total_runtime_seconds"]),
            "mean_runtime_seconds": _number(overall_row["mean_runtime_seconds"]),
            "median_runtime_seconds": _number(overall_row["median_runtime_seconds"]),
            "p95_runtime_seconds": _number(overall_row["p95_runtime_seconds"]),
            "throughput_candidates_per_second": _number(overall_row["throughput_cases_per_second"]),
            "gpu_peak_memory_bytes": gpu_peak,
            "gpu_total_memory_bytes": gpu_total,
            "output_file_count": int(storage_row["output_file_count"]),
            "output_storage_bytes": int(storage_row["output_storage_bytes"]),
            "restored_image_file_count": int(storage_row["restored_image_file_count"]),
            "restored_image_storage_bytes": int(storage_row["restored_image_storage_bytes"]),
            "source_ids_json": _json_list(source_ids),
            "source_urls_json": _json_list(source_urls),
            "source_checked_at_utc": settings["sources"]["checked_at_utc"],
            "schema_version": MODEL_CARD_SCHEMA_VERSION,
            "status": "ok",
            "issue": "",
        }
        rows.append(row)
    return pd.DataFrame(rows, columns=MODEL_CARD_COLUMNS)


def collect_observed_compute(
    runtime_tables: Mapping[str, pd.DataFrame],
    model_cards: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Normalize all 27 upstream runtime-summary rows."""

    card_lookup = model_cards.set_index("model_id").to_dict("index")
    rows = []
    for model_id in _model_specs(config):
        card = card_lookup[model_id]
        for source in runtime_tables[model_id].to_dict("records"):
            overall = str(source["summary_scope"]) == "overall" and str(source["experiment_id"]) == "all"
            case_count = int(float(source["case_count"]))
            row = {
                "compute_row_id": _stable_id("compute", model_id, "observed", source["summary_scope"], source["experiment_id"]),
                "model_id": model_id,
                "evaluation_status": card["evaluation_status"],
                "record_type": "observed",
                "scenario_id": f"observed_{source['summary_scope']}_{source['experiment_id']}",
                "summary_scope": source["summary_scope"],
                "experiment_id": source["experiment_id"],
                "dataset_scope": _settings(config)["dataset_scope"],
                "painting_count": int(card["evaluated_painting_count"]) if overall else np.nan,
                "case_count": case_count,
                "candidate_count": case_count,
                "inference_count": int(card["model_inference_count"]) if overall else np.nan,
                "zero_control_count": int(card["zero_control_count"]) if overall else np.nan,
                "completed_count": int(float(source["completed_count"])),
                "failed_count": int(float(source["failed_count"])),
                "retry_count": int(card["retry_count"]) if overall else np.nan,
                "failure_rate": float(source["failed_count"]) / case_count if case_count else np.nan,
                "total_runtime_seconds": _number(source["total_runtime_seconds"]),
                "mean_runtime_seconds": _number(source["mean_runtime_seconds"]),
                "median_runtime_seconds": _number(source["median_runtime_seconds"]),
                "p95_runtime_seconds": _number(source["p95_runtime_seconds"]),
                "max_runtime_seconds": _number(source["max_runtime_seconds"]),
                "throughput_candidates_per_second": _number(source["throughput_cases_per_second"]),
                "runtime_lower_seconds": np.nan,
                "runtime_central_seconds": np.nan,
                "runtime_upper_seconds": np.nan,
                "projection_multiplier": np.nan,
                "projection_basis": "executed upstream runtime summary",
                "sensitivity_is_confidence_interval": False,
                "gpu_peak_memory_bytes": card["gpu_peak_memory_bytes"] if overall else np.nan,
                "gpu_total_memory_bytes": card["gpu_total_memory_bytes"] if overall else np.nan,
                "output_file_count": int(card["output_file_count"]) if overall else np.nan,
                "output_storage_bytes": int(card["output_storage_bytes"]) if overall else np.nan,
                "projected_output_file_count": np.nan,
                "projected_output_storage_bytes": np.nan,
                "candidate_multiplier": float(card["evaluated_candidate_count"] / card["evaluated_case_count"]) if overall else np.nan,
                "inference_width": card["inference_width"],
                "inference_height": card["inference_height"],
                "output_width": card["output_width"],
                "output_height": card["output_height"],
                "applicability_status": "applicable_executed",
                "is_executed": True,
                "is_projected": False,
                "schema_version": COMPUTE_SCHEMA_VERSION,
                "status": "ok",
                "issue": "",
            }
            rows.append(row)
    return pd.DataFrame(rows, columns=COMPUTE_COLUMNS)


def _runtime_distribution(frame: pd.DataFrame) -> dict[str, float]:
    values = pd.to_numeric(frame["runtime_seconds"], errors="coerce").dropna().to_numpy(dtype=float)
    if not len(values) or not np.isfinite(values).all():
        raise ValueError("Projection basis contains no finite runtime values")
    return {
        "count": float(len(values)),
        "total": float(values.sum()),
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "p95": float(np.quantile(values, 0.95)),
        "max": float(values.max()),
    }


def _canonical_projection_basis(model_id: str, frame: pd.DataFrame) -> pd.DataFrame:
    if "experiment_id" in frame.columns:
        canonical = frame["experiment_id"].astype(str).eq("canonical_missing_region")
    elif "case_id" in frame.columns:
        # Notebook 09/10 restoration schemas predate the explicit experiment_id
        # field. Their normalized case IDs retain the exact experiment boundary.
        canonical = frame["case_id"].astype(str).str.startswith("canonical__")
    else:
        raise ValueError(f"{model_id} candidate table has no experiment discriminator")
    result = frame.loc[canonical].copy()
    if model_id == "stable_diffusion_inpainting":
        result = result.loc[result["is_primary_candidate"].map(_as_bool)]
    if model_id == "sdxl_inpainting":
        result = result.loc[result["status"].astype(str).str.lower().eq("completed")]
    return result


def build_scaling_projections(
    candidate_tables: Mapping[str, pd.DataFrame],
    model_cards: pd.DataFrame,
    storage: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build eight transparent 300-painting projection rows."""

    settings = _settings(config)
    card_lookup = model_cards.set_index("model_id").to_dict("index")
    storage_lookup = storage.set_index("model_id").to_dict("index")
    rows = []
    for scenario in settings["projections"]["scenarios"]:
        scenario_id = str(scenario["scenario_id"])
        for model_id in _model_specs(config):
            card = card_lookup[model_id]
            storage_row = storage_lookup[model_id]
            case_target = scenario["target_case_count"].get(model_id)
            target = scenario["target_candidates"].get(model_id)
            inference_target = scenario["target_inference_candidates"].get(model_id)
            zero_target = scenario["target_zero_controls"].get(model_id)
            applicable = target is not None
            if applicable:
                if scenario_id == "projected_300_canonical_primary":
                    basis = _canonical_projection_basis(model_id, candidate_tables[model_id])
                    dist = _runtime_distribution(basis)
                    if model_id == "sdxl_inpainting":
                        runtime_factor_count = int(inference_target)
                        multiplier = float(inference_target / dist["count"])
                        basis_text = "four executed SDXL canonical non-zero cases scaled to 1,200 inference cases; zero controls assigned no inference runtime"
                    else:
                        runtime_factor_count = int(target)
                        multiplier = float(target / dist["count"])
                        basis_text = f"{int(dist['count'])} executed canonical primary candidates scaled to {int(target)} candidates"
                    scaled_median = dist["median"] * runtime_factor_count
                    central = dist["mean"] * runtime_factor_count
                    scaled_p95 = dist["p95"] * runtime_factor_count
                    lower = min(scaled_median, central)
                    upper = max(scaled_p95, central)
                else:
                    basis = candidate_tables[model_id]
                    dist = _runtime_distribution(basis)
                    runtime_factor_count = int(target)
                    multiplier = float(settings["projections"]["scale_multiplier"])
                    scaled_median = dist["median"] * runtime_factor_count
                    central = dist["mean"] * runtime_factor_count
                    scaled_p95 = dist["p95"] * runtime_factor_count
                    lower = min(scaled_median, central)
                    upper = max(scaled_p95, central)
                    basis_text = f"complete executed design multiplied by {settings['projections']['scale_multiplier']}"
                restored_count = int(storage_row["restored_image_file_count"])
                average_image_bytes = (
                    float(storage_row["restored_image_storage_bytes"]) / restored_count
                    if restored_count else 0.0
                )
                projected_storage = int(round(average_image_bytes * int(target) + float(storage_row["fixed_storage_bytes"])))
                projected_files = int(target) + int(storage_row["fixed_file_count"])
                status = "ok"
                issue = ""
                applicability = "applicable_projection"
            else:
                dist = {key: np.nan for key in ("mean", "median", "p95", "max")}
                multiplier = np.nan
                lower = central = upper = np.nan
                projected_storage = projected_files = np.nan
                basis_text = "not applicable: bounded SDXL scope has no full current-design equivalent"
                status = "not_applicable"
                issue = basis_text
                applicability = "not_applicable_no_full_design_basis"
            rows.append({
                "compute_row_id": _stable_id("compute", model_id, "projection", scenario_id),
                "model_id": model_id,
                "evaluation_status": card["evaluation_status"],
                "record_type": "projection",
                "scenario_id": scenario_id,
                "summary_scope": "projection",
                "experiment_id": "canonical_missing_region" if scenario_id.endswith("canonical_primary") else "current_design_mix",
                "dataset_scope": "projected_300",
                "painting_count": int(settings["projections"]["target_painting_count"]),
                "case_count": case_target if case_target is not None else np.nan,
                "candidate_count": target if target is not None else np.nan,
                "inference_count": inference_target if inference_target is not None else np.nan,
                "zero_control_count": zero_target if zero_target is not None else np.nan,
                "completed_count": np.nan,
                "failed_count": np.nan,
                "retry_count": np.nan,
                "failure_rate": np.nan,
                "total_runtime_seconds": np.nan,
                "mean_runtime_seconds": dist["mean"],
                "median_runtime_seconds": dist["median"],
                "p95_runtime_seconds": dist["p95"],
                "max_runtime_seconds": dist["max"],
                "throughput_candidates_per_second": np.nan,
                "runtime_lower_seconds": lower,
                "runtime_central_seconds": central,
                "runtime_upper_seconds": upper,
                "projection_multiplier": multiplier,
                "projection_basis": basis_text,
                "sensitivity_is_confidence_interval": False,
                "gpu_peak_memory_bytes": card["gpu_peak_memory_bytes"],
                "gpu_total_memory_bytes": card["gpu_total_memory_bytes"],
                "output_file_count": np.nan,
                "output_storage_bytes": np.nan,
                "projected_output_file_count": projected_files,
                "projected_output_storage_bytes": projected_storage,
                "candidate_multiplier": float(target / case_target) if target is not None and case_target is not None else np.nan,
                "inference_width": card["inference_width"],
                "inference_height": card["inference_height"],
                "output_width": card["output_width"],
                "output_height": card["output_height"],
                "applicability_status": applicability,
                "is_executed": False,
                "is_projected": True,
                "schema_version": COMPUTE_SCHEMA_VERSION,
                "status": status,
                "issue": issue,
            })
    return pd.DataFrame(rows, columns=COMPUTE_COLUMNS)


def prepare_quality_evidence(
    model_comparison: pd.DataFrame,
    metric_disagreement: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Select the 22 validated anchors and build descriptive win counts."""

    quality = _settings(config)["quality"]
    anchors = list(quality["anchors"])
    selected_disagreement = metric_disagreement.loc[
        metric_disagreement["population_id"].isin(quality["populations"])
        & metric_disagreement["analysis_scope"].astype(str).eq("overall")
        & metric_disagreement["scope_value"].astype(str).eq("all")
        & metric_disagreement["anchor_id"].isin(anchors)
    ].copy()
    if len(selected_disagreement) != len(anchors) * len(quality["populations"]):
        raise ValueError("Validated quality-anchor population is incomplete")
    for population_id in quality["populations"]:
        observed = set(selected_disagreement.loc[selected_disagreement["population_id"].eq(population_id), "anchor_id"])
        if observed != set(anchors):
            raise ValueError(f"Anchor mismatch for {population_id}")

    values = model_comparison.loc[
        model_comparison["population_id"].isin(quality["populations"])
        & model_comparison["analysis_scope"].astype(str).eq("overall")
        & model_comparison["scope_value"].astype(str).eq("all")
        & model_comparison["anchor_id"].isin(anchors)
    ].copy()
    expected_value_rows = sum(
        len(spec["model_ids"]) * len(anchors)
        for spec in quality["populations"].values()
    )
    if len(values) != expected_value_rows:
        raise ValueError(f"Expected {expected_value_rows} model-anchor values, observed {len(values)}")

    summary_rows = []
    for population_id, population in quality["populations"].items():
        subset = selected_disagreement.loc[selected_disagreement["population_id"].eq(population_id)]
        for model_id in population["model_ids"]:
            wins = int(subset["winner_model_id"].astype(str).eq(model_id).sum())
            summary_rows.append({
                "population_id": population_id,
                "model_id": model_id,
                "anchor_win_count": wins,
                "anchor_count": len(anchors),
                "case_count": int(population["case_count"]),
                "painting_count": int(population["painting_count"]),
                "interpretation": "descriptive_validated_anchor_count_not_combined_quality_score",
            })
    return values.reset_index(drop=True), pd.DataFrame(summary_rows)


def coerce_compute_scalability(
    observed: pd.DataFrame,
    projections: pd.DataFrame,
) -> pd.DataFrame:
    frame = pd.concat([observed, projections], ignore_index=True)
    for column in COMPUTE_COLUMNS:
        if column not in frame:
            frame[column] = ""
    frame["schema_version"] = COMPUTE_SCHEMA_VERSION
    return frame.loc[:, COMPUTE_COLUMNS].copy()


def validate_model_cards(frame: pd.DataFrame, *, config: Mapping[str, Any]) -> pd.DataFrame:
    expected = _settings(config)["expected_counts"]
    model_ids = list(_model_specs(config))
    checks = [
        ("exact_columns", list(frame.columns) == list(MODEL_CARD_COLUMNS), f"columns={len(frame.columns)}"),
        ("row_count", len(frame) == int(expected["model_card_rows"]), f"expected={expected['model_card_rows']}; observed={len(frame)}"),
        ("model_ids", frame["model_id"].tolist() == model_ids, str(frame["model_id"].tolist())),
        ("unique_ids", not frame["model_card_id"].duplicated().any() and not frame["model_id"].duplicated().any(), "card/model IDs"),
        ("schema_version", frame["schema_version"].eq(MODEL_CARD_SCHEMA_VERSION).all(), MODEL_CARD_SCHEMA_VERSION),
        ("completed_counts", frame["completed_count"].eq(frame["evaluated_candidate_count"]).all(), "all executed candidates complete"),
        ("zero_failures", frame["failed_count"].eq(0).all(), str(frame.set_index("model_id")["failed_count"].to_dict())),
        ("sdxl_partial", frame.loc[frame["model_id"].eq("sdxl_inpainting"), "evaluation_status"].eq("partial_evaluation").all(), "ten-case partial scope"),
        ("other_models_full", frame.loc[frame["model_id"].ne("sdxl_inpainting"), "evaluation_status"].eq("fully_evaluated").all(), "three full-scope methods"),
        ("no_storage_errors", frame["output_file_count"].gt(0).all() and frame["output_storage_bytes"].gt(0).all(), "positive owned storage"),
        ("sources_present", frame["source_urls_json"].map(lambda value: len(json.loads(value)) > 0).all(), "at least one primary source per card"),
        ("no_conservation_claim", ~frame["excluded_uses_json"].str.lower().str.contains("not applicable").any(), "explicit excluded uses retained"),
    ]
    return pd.DataFrame(checks, columns=["check_id", "passed", "details"])


def validate_compute_scalability(frame: pd.DataFrame, *, config: Mapping[str, Any]) -> pd.DataFrame:
    expected = _settings(config)["expected_counts"]
    observed = frame.loc[frame["record_type"].eq("observed")]
    projected = frame.loc[frame["record_type"].eq("projection")]
    sdxl_current = projected.loc[
        projected["model_id"].eq("sdxl_inpainting")
        & projected["scenario_id"].eq("projected_300_current_design_mix")
    ]
    applicable = projected.loc[projected["applicability_status"].eq("applicable_projection")]
    checks = [
        ("exact_columns", list(frame.columns) == list(COMPUTE_COLUMNS), f"columns={len(frame.columns)}"),
        ("row_count", len(frame) == int(expected["compute_rows"]), f"expected={expected['compute_rows']}; observed={len(frame)}"),
        ("observed_rows", len(observed) == int(expected["observed_compute_rows"]), f"observed={len(observed)}"),
        ("projection_rows", len(projected) == int(expected["projection_rows"]), f"observed={len(projected)}"),
        ("unique_ids", not frame["compute_row_id"].duplicated().any(), f"rows={len(frame)}"),
        ("schema_version", frame["schema_version"].eq(COMPUTE_SCHEMA_VERSION).all(), COMPUTE_SCHEMA_VERSION),
        ("executed_flags", observed["is_executed"].map(_as_bool).all() and ~observed["is_projected"].map(_as_bool).any(), "observed only"),
        ("projected_flags", projected["is_projected"].map(_as_bool).all() and ~projected["is_executed"].map(_as_bool).any(), "projected only"),
        ("projection_values", applicable[["runtime_lower_seconds", "runtime_central_seconds", "runtime_upper_seconds"]].notna().all().all(), f"applicable={len(applicable)}"),
        ("projection_order", ((applicable["runtime_lower_seconds"] <= applicable["runtime_central_seconds"]) & (applicable["runtime_central_seconds"] <= applicable["runtime_upper_seconds"])).all(), "lower <= central <= upper sensitivity"),
        ("sdxl_current_na", len(sdxl_current) == 1 and sdxl_current["status"].eq("not_applicable").all() and sdxl_current["runtime_central_seconds"].isna().all(), "no fabricated full-design SDXL projection"),
        ("not_confidence_interval", ~frame["sensitivity_is_confidence_interval"].map(_as_bool).any(), "sensitivity bounds only"),
        ("no_executed_300", ~observed["dataset_scope"].eq("projected_300").any(), "300-painting scope is projected only"),
    ]
    return pd.DataFrame(checks, columns=["check_id", "passed", "details"])


def _format_seconds(value: Any) -> str:
    number = _number(value)
    if not np.isfinite(number):
        return "not applicable"
    if number < 120:
        return f"{number:,.2f} seconds"
    if number < 7200:
        return f"{number / 60:,.1f} minutes"
    return f"{number / 3600:,.1f} hours"


def _format_bytes(value: Any) -> str:
    number = _number(value)
    if not np.isfinite(number):
        return "not applicable"
    if number < 1024**3:
        return f"{number / 1024**2:,.2f} MiB"
    return f"{number / 1024**3:,.2f} GiB"


def _bullets(json_text: str) -> str:
    return "\n".join(f"- {item}" for item in json.loads(json_text))


def render_model_card_markdown(
    model_row: Mapping[str, Any],
    compute: pd.DataFrame,
    quality_values: pd.DataFrame,
    quality_summary: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> str:
    """Render one evidence-populated portable Markdown model card."""

    model_id = str(model_row["model_id"])
    display = str(model_row["display_name"])
    overall = compute.loc[
        compute["model_id"].eq(model_id)
        & compute["record_type"].eq("observed")
        & compute["summary_scope"].eq("overall")
    ].iloc[0]
    projections = compute.loc[
        compute["model_id"].eq(model_id) & compute["record_type"].eq("projection")
    ]
    population_id = "sdxl_four_model_subset" if model_id == "sdxl_inpainting" else "core_three_model"
    summary = quality_summary.loc[
        quality_summary["population_id"].eq(population_id)
        & quality_summary["model_id"].eq(model_id)
    ].iloc[0]
    values = quality_values.loc[
        quality_values["population_id"].eq(population_id)
        & quality_values["model_id"].eq(model_id)
    ].sort_values("anchor_id")
    best_anchor = values.sort_values("aggregate_rank").iloc[0]
    status_text = str(model_row["evaluation_status"]).replace("_", " ")
    if model_id == "lama":
        headline = "LaMa provided the strongest broad reference-based baseline under the validated full-scope anchor policy."
        reliability = "LaMa is deterministic under the evaluated contract. Mask robustness and damage sensitivity are the relevant reliability constructs; repeated-seed generative uncertainty is not applicable."
    elif model_id == "opencv_telea":
        headline = "OpenCV Telea was the fastest and most reproducible baseline, while its local interpolation remained limited for semantically demanding missing regions."
        reliability = "OpenCV Telea is deterministic. Its appropriate reliability evidence is input robustness and sensitivity, not generative uncertainty."
    elif model_id == "stable_diffusion_inpainting":
        headline = "Stable Diffusion added prompt-conditioned and repeated-seed evidence, but required far more candidates and did not lead the full-scope reference-based anchor comparison."
        reliability = "Stable Diffusion is stochastic. Repeated seeds measure empirical candidate variability, and the scratch-aware arm measures damage-specific prompt sensitivity; neither is calibrated confidence."
    else:
        headline = "SDXL completed a bounded ten-case partial evaluation, providing direct local feasibility evidence without supporting a full-dataset ranking."
        reliability = "SDXL has one seed per completed case. Generative uncertainty is therefore not estimable from this scope, and no artificial uncertainty value is assigned."
    projection_lines = []
    for row in projections.to_dict("records"):
        if row["status"] == "not_applicable":
            projection_lines.append(f"| {row['scenario_id']} | not applicable | not applicable | {row['projection_basis']} |")
        else:
            projection_lines.append(
                f"| {row['scenario_id']} | {int(row['candidate_count']):,} | {_format_seconds(row['runtime_central_seconds'])} | {_format_bytes(row['projected_output_storage_bytes'])} |"
            )
    quality_rows = []
    for row in values.to_dict("records"):
        quality_rows.append(
            f"| {row['anchor_id']} | {float(row['restored_mean']):.5g} | {int(float(row['aggregate_rank']))} | {row['winner_model_id']} |"
        )
    source_urls = json.loads(str(model_row["source_urls_json"]))
    source_lines = "\n".join(f"- {url}" for url in source_urls)
    observed_hardware = json.loads(str(model_row["observed_hardware_json"]))
    accelerator_name = str(
        observed_hardware.get(
            "cuda_device_name",
            "not applicable (CPU execution)"
            if not observed_hardware.get("gpu_required", False)
            else "not separately recorded",
        )
    )
    report = f"""# {display} - Model Card and Compute Audit

**Evaluation status:** {status_text.title()}  
**Method role:** {str(model_row['methodological_role']).replace('_', ' ')}  
**Dataset scope:** {_settings(config)['dataset_scope']}  
**Decision boundary:** Digital restoration candidate method, not a conservation authority

<a id="at-a-glance"></a>
## 1. At a glance

{headline}

- Completed candidates: **{int(model_row['completed_count']):,} of {int(model_row['evaluated_candidate_count']):,}**.
- Mean runtime: **{float(model_row['mean_runtime_seconds']):,.2f} seconds per candidate**.
- Observed notebook-owned storage: **{_format_bytes(model_row['output_storage_bytes'])}**.
- Validated anchor wins in the applicable population: **{int(summary['anchor_win_count'])} of {int(summary['anchor_count'])}**.

**Conclusion:** The compute and quality evidence support this method only within its declared evaluation scope. Anchor wins are descriptive Notebook 21 outcomes, not a combined quality score or conservation verdict.

<a id="identity-and-provenance"></a>
## 2. Identity and provenance

| Field | Recorded value |
|---|---|
| Model ID | `{model_id}` |
| Family | {str(model_row['model_family']).replace('_', ' ')} |
| Original purpose | {model_row['original_purpose']} |
| Project implementation | {model_row['implementation']} |
| Implementation version | {model_row['implementation_version'] or 'not separately recorded'} |
| Model identifier | `{model_row['model_identifier']}` |
| Model revision | `{model_row['model_revision'] or 'not applicable'}` |
| Software licence | {model_row['software_license']} |
| Weight licence | {model_row['weight_license']} |

{model_row['license_scope_note']}

<a id="intended-and-unsupported-use"></a>
## 3. Intended and unsupported use

Appropriate project uses:

{_bullets(str(model_row['intended_uses_json']))}

Unsupported uses:

{_bullets(str(model_row['excluded_uses_json']))}

<a id="training-data-and-domain-gap"></a>
## 4. Training data and painting-domain gap

{model_row['training_data_description']}

**Training-data transparency status:** {str(model_row['training_data_transparency']).replace('_', ' ')}

**Domain gap:** {model_row['domain_gap']}

**Bias and risk:** {model_row['bias_notes']}

**Conclusion:** Source transparency and general-image performance do not establish painting-specific historical or conservation competence.

<a id="project-implementation"></a>
## 5. Project implementation

| Setting | Recorded value |
|---|---|
| Configuration | `{model_row['configuration_id']}` |
| Device | {model_row['execution_device']} |
| Backend | {model_row['execution_backend'] or 'recorded in upstream manifest'} |
| Recorded accelerator | {accelerator_name} |
| Precision | {model_row['precision']} |
| Inference resolution | {int(model_row['inference_width'])} x {int(model_row['inference_height'])} |
| Output resolution | {int(model_row['output_width'])} x {int(model_row['output_height'])} |
| Input constraints | {model_row['input_constraints']} |
| Mask constraints | {model_row['mask_constraints']} |
| Deterministic | {bool(model_row['deterministic'])} |
| Prompt dependent | {bool(model_row['prompt_dependent'])} |
| Hardware statement | {model_row['hardware_requirements']} |

The project used a fixed predeclared configuration and exact outside-mask compositing policy where applicable. Per-case metric-guided tuning was not used.

<a id="evaluated-evidence-coverage"></a>
## 6. Evaluated evidence coverage

| Coverage field | Recorded count |
|---|---:|
| Paintings | {int(model_row['evaluated_painting_count']):,} |
| Unique cases | {int(model_row['evaluated_case_count']):,} |
| Candidates | {int(model_row['evaluated_candidate_count']):,} |
| Model-inference candidates | {int(model_row['model_inference_count']):,} |
| Identity zero controls | {int(model_row['zero_control_count']):,} |

Cases and repeated candidates remain nested within paintings. Candidate rows are not treated as independent artworks.

<a id="compute-and-storage"></a>
## 7. Compute and storage

| Measure | Observed result |
|---|---:|
| Total runtime | {_format_seconds(overall['total_runtime_seconds'])} |
| Mean runtime | {float(overall['mean_runtime_seconds']):,.3f} s |
| Median runtime | {float(overall['median_runtime_seconds']):,.3f} s |
| p95 runtime | {float(overall['p95_runtime_seconds']):,.3f} s |
| Failed candidates | {int(overall['failed_count'])} |
| Failure rate | {float(model_row['failure_rate']):.2%} |
| Retries | {int(model_row['retry_count'])} |
| Throughput | {float(model_row['throughput_candidates_per_second']):,.4f} candidates/second |
| Candidate multiplier | {float(overall['candidate_multiplier']):,.4f} candidates per evaluated case |
| Recorded peak GPU allocation | {_format_bytes(model_row['gpu_peak_memory_bytes'])} |
| Recorded total GPU memory | {_format_bytes(model_row['gpu_total_memory_bytes'])} |
| Output files | {int(model_row['output_file_count']):,} |
| Output storage | {_format_bytes(model_row['output_storage_bytes'])} |

**Conclusion:** These measurements describe the recorded workstation and software environment. They are project evidence, not universal hardware benchmarks.

<a id="quality-evidence"></a>
## 8. Quality evidence

Applicable population: `{population_id}` ({int(summary['case_count'])} cases nested within {int(summary['painting_count'])} paintings).

| Validated anchor | Restored mean | Rank | Winner |
|---|---:|---:|---|
{chr(10).join(quality_rows)}

The method won {int(summary['anchor_win_count'])} of {int(summary['anchor_count'])} validated anchors in this population. Its strongest displayed anchor was `{best_anchor['anchor_id']}`.

**Conclusion:** Better or worse language applies only to the named anchor and population. Runtime is not included in the quality vote, and the anchor count is not a universal quality score.

<a id="determinism-robustness-and-uncertainty"></a>
## 9. Determinism, robustness, and uncertainty

{reliability}

Low variability or deterministic repetition does not prove that a reconstructed region is correct.

<a id="scalability"></a>
## 10. Scalability

| Scenario | Candidate outputs | Central runtime projection | Output-storage projection |
|---|---:|---:|---:|
{chr(10).join(projection_lines)}

Raw observed median, mean, and p95 runtimes are retained in the compute table. The displayed sensitivity envelope uses the smaller of scaled median and mean as its lower value, scaled mean as its central value, and the larger of scaled p95 and mean as its upper value. These are not confidence intervals. No 300-painting experiment was executed.

<a id="strengths-and-weaknesses"></a>
## 11. Strengths and weaknesses

Strengths:

{_bullets(str(model_row['strengths_json']))}

Weaknesses:

{_bullets(str(model_row['weaknesses_json']))}

Known project limitations:

{_bullets(str(model_row['known_limitations_json']))}

<a id="human-decision-support-interpretation"></a>
## 12. Human decision-support interpretation

The method can generate and prioritize digital candidates for structured inspection. Reviewers should examine repaired structure, local texture, colour continuity, seams, uncertainty where applicable, and disagreements between evidence families.

**Decision statement:** This card supports transparent method selection and review planning. It does not approve physical treatment, establish historical truth, or replace expert conservation judgement.

<a id="reproducibility-and-provenance"></a>
## 13. Reproducibility and provenance

| Field | Recorded value |
|---|---|
| Producer notebook | `30_model_cards_compute_and_scalability.ipynb` |
| Candidate producer | Notebook { {'opencv_telea':'09','lama':'10','stable_diffusion_inpainting':'11','sdxl_inpainting':'12'}[model_id] } |
| Quality producer | Notebook 21 |
| Compute schema | `{COMPUTE_SCHEMA_VERSION}` |
| Model-card schema | `{MODEL_CARD_SCHEMA_VERSION}` |
| Source review date | {model_row['source_checked_at_utc']} |

Primary and runtime sources:

{source_lines}

### Final scoped verdict

{headline} This conclusion remains limited to the controlled evidence and the recorded compute environment.
"""
    return report.strip() + "\n"


def validate_model_card_markdown(
    markdown: str,
    *,
    model_id: str,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    report = _settings(config)["report"]
    section_ids = list(report["required_section_ids"])
    positions = [markdown.find(f'<a id="{section_id}"></a>') for section_id in section_ids]
    image_tokens = len(re.findall(r"!\[[^\]]*\]\([^)]*\)|<img\b", markdown, flags=re.I))
    checks = [
        ("report_nonempty", len(markdown.encode("utf-8")) > 4000, f"bytes={len(markdown.encode('utf-8'))}"),
        ("model_id_present", f"`{model_id}`" in markdown, model_id),
        ("required_sections", all(position >= 0 for position in positions), f"required={len(section_ids)}"),
        ("section_order", positions == sorted(positions), "approved mock order"),
        ("no_image_dependencies", image_tokens == 0, f"image_tokens={image_tokens}"),
        ("no_file_uri", "file://" not in markdown.lower(), "file URI prohibited"),
        ("not_planning_mock", not any(token in markdown.lower() for token in ("illustrative", "fictional", "placeholder")), "real evidence only"),
        ("projection_scope", "No 300-painting experiment was executed" in markdown, "projection boundary"),
        ("conservation_boundary", "does not approve physical treatment" in markdown, "human decision support"),
        ("quality_boundary", "not a universal quality score" in markdown, "anchor count boundary"),
    ]
    return pd.DataFrame(checks, columns=["check_id", "passed", "details"])


def atomic_write_csv(
    frame: pd.DataFrame,
    output_path: str | Path,
    *,
    attempts: int = 5,
    retry_seconds: float = 0.2,
) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.{time.time_ns()}.tmp")
    frame.to_csv(temporary, index=False)
    try:
        for attempt in range(attempts):
            try:
                os.replace(temporary, target)
                return target
            except PermissionError:
                if attempt + 1 >= attempts:
                    raise
                time.sleep(retry_seconds * (attempt + 1))
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def atomic_write_text(
    text: str,
    output_path: str | Path,
    *,
    attempts: int = 5,
    retry_seconds: float = 0.2,
) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.{time.time_ns()}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    try:
        for attempt in range(attempts):
            try:
                os.replace(temporary, target)
                return target
            except PermissionError:
                if attempt + 1 >= attempts:
                    raise
                time.sleep(retry_seconds * (attempt + 1))
    finally:
        if temporary.exists():
            temporary.unlink()
    return target
