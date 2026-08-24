"""Normalized, reproducible Stable Diffusion 1.5 inpainting execution."""

from __future__ import annotations

import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd
import yaml
from PIL import Image

from .schemas import (
    CASE_REGISTRY_SCHEMA,
    MODEL_ELIGIBILITY_SCHEMA,
    PROMPT_ABLATION_DESIGN_COLUMNS,
    PROMPT_ABLATION_DESIGN_SCHEMA,
    PROMPT_POLICY_COLUMNS,
    PROMPT_POLICY_SCHEMA,
    RESTORATION_RUNTIME_SUMMARY_COLUMNS,
    RESTORATION_RUNTIME_SUMMARY_SCHEMA,
    STABLE_DIFFUSION_CANDIDATE_COLUMNS,
    STABLE_DIFFUSION_CANDIDATES_SCHEMA,
    validate_dataframe,
)


MODEL_NAME = "stable_diffusion_inpainting"
RESTORATION_GENERATOR_NAME = "restoration_eval.restoration_stable_diffusion"
RESTORATION_GENERATOR_VERSION = "5.1.0"
CONFIG_SCHEMA_VERSION = "stable_diffusion_config.v1"
ProgressCallback = Callable[[str], None]

PROMPT_VARIANTS: tuple[dict[str, Any], ...] = (
    {
        "prompt_variant_id": "p00_generic", "variant_family": "generic",
        "requires_metadata": False, "metadata_fields": (), "template": "{generic_prompt}",
    },
    {
        "prompt_variant_id": "p01_category", "variant_family": "contextual",
        "requires_metadata": True, "metadata_fields": ("category",),
        "template": (
            "a complete aged fine-art painting in the {category} genre with seamless "
            "visual continuity, coherent composition, and a consistent colour palette, "
            "brushwork, canvas texture, lighting, and level of detail"
        ),
    },
    {
        "prompt_variant_id": "p02_artist", "variant_family": "contextual",
        "requires_metadata": True, "metadata_fields": ("artist",),
        "template": (
            "a complete aged fine-art painting by {artist} with seamless visual continuity, "
            "coherent composition, and a consistent colour palette, brushwork, canvas "
            "texture, lighting, and level of detail"
        ),
    },
    {
        "prompt_variant_id": "p03_artist_category", "variant_family": "contextual",
        "requires_metadata": True, "metadata_fields": ("artist", "category"),
        "template": (
            "a complete aged {category} painting by {artist} with seamless visual continuity, "
            "coherent composition, and a consistent colour palette, brushwork, canvas "
            "texture, lighting, and level of detail"
        ),
    },
    {
        "prompt_variant_id": "p04_full_context", "variant_family": "contextual",
        "requires_metadata": True,
        "metadata_fields": ("title", "artist", "category"),
        "template": (
            "a complete aged painting titled {title}, by {artist}, in the {category} genre "
            "with seamless visual continuity, coherent composition, and a consistent "
            "colour palette, brushwork, canvas texture, lighting, and level of detail"
        ),
    },
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def calculate_file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configuration_fingerprint(config: Mapping[str, Any]) -> str:
    encoded = json.dumps(config, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _require_keys(mapping: Mapping[str, Any], keys: set[str], *, label: str) -> None:
    missing = sorted(keys - set(mapping))
    if missing:
        raise ValueError(f"{label} is missing required keys: {missing}")


def load_stable_diffusion_config(path: str | Path) -> dict[str, Any]:
    """Load and validate the frozen Notebook 11 method contract."""
    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Stable Diffusion configuration must be a mapping.")
    _require_keys(
        config,
        {
            "config_schema_version", "config_version", "dataset", "inputs", "output",
            "model", "prompt_policy", "candidate_design", "execution", "expected",
            "smoke", "schema_versions", "known_limitations",
        },
        label="Stable Diffusion configuration",
    )
    if config["config_schema_version"] != CONFIG_SCHEMA_VERSION:
        raise ValueError(f"Unsupported configuration schema: {config['config_schema_version']!r}")
    model = config["model"]
    design = config["candidate_design"]
    execution = config["execution"]
    prompt_policy = config["prompt_policy"]
    _require_keys(
        model,
        {
            "model_id", "hf_model_id", "model_revision", "configuration_id", "scheduler",
            "requested_device", "allow_cpu_fallback", "precision", "inference_width",
            "inference_height", "output_width", "output_height", "num_inference_steps",
            "guidance_scale", "strength", "maximum_retries", "retry_seed_policy",
            "zero_control_policy", "compositing_policy", "mask_threshold_policy",
            "safety_checker_policy",
        },
        label="Stable Diffusion model configuration",
    )
    _require_keys(
        prompt_policy,
        {
            "policy_id", "primary_variant_id", "generic_prompt",
            "negative_prompt", "contextual_variant_ids",
        },
        label="Stable Diffusion prompt policy",
    )
    _require_keys(
        design,
        {
            "primary_seed", "uncertainty_seeds", "prompt_ablation_case_count",
            "prompt_ablation_required_metadata", "prompt_ablation_excluded_values",
            "uncertainty_paintings_per_category", "uncertainty_mask_types",
            "selection_policy",
        },
        label="Stable Diffusion candidate design",
    )
    if model["model_id"] != MODEL_NAME:
        raise ValueError(f"Notebook 11 must target model_id={MODEL_NAME!r}.")
    if len(str(model["model_revision"])) != 40:
        raise ValueError("model_revision must be an immutable 40-character commit hash.")
    if model["retry_seed_policy"] != "preserve_exact_seed":
        raise ValueError("Retries must preserve the exact declared candidate seed.")
    if model["zero_control_policy"] != "identity_noop":
        raise ValueError("Zero controls must use identity_noop.")
    if model["compositing_policy"] != "masked_composite_preserve_outside.v1":
        raise ValueError("Notebook 11 must preserve pixels outside the approved mask.")
    if model["scheduler"] != "DDIMScheduler":
        raise ValueError("The approved scheduler is DDIMScheduler.")
    approved_contextual_variants = [
        variant["prompt_variant_id"] for variant in PROMPT_VARIANTS
        if variant["prompt_variant_id"] != "p00_generic"
    ]
    if prompt_policy["primary_variant_id"] != "p00_generic":
        raise ValueError("The primary prompt variant must remain p00_generic.")
    if list(prompt_policy["contextual_variant_ids"]) != approved_contextual_variants:
        raise ValueError(
            "Configured contextual prompt variants do not match the approved policy."
        )
    if not 0 < float(model["strength"]) <= 1:
        raise ValueError("strength must be in (0, 1].")
    if int(execution["progress_interval_candidates"]) <= 0:
        raise ValueError("progress_interval_candidates must be positive.")
    if int(execution["checkpoint_interval_candidates"]) <= 0:
        raise ValueError("checkpoint_interval_candidates must be positive.")
    if int(design["primary_seed"]) in {int(seed) for seed in design["uncertainty_seeds"][1:]}:
        raise ValueError("Primary seed must not be repeated among extension seeds.")
    for name in ("binary_missing_region", "synthetic_degradation"):
        policy = model["mask_threshold_policy"][name]
        if policy["comparison"] != "greater_than_or_equal":
            raise ValueError(f"{name} must use an inclusive >= threshold.")
        if not 0 <= int(policy["threshold"]) <= 255:
            raise ValueError(f"Invalid threshold for {name}.")
    return config


def _coerce_bool(series: pd.Series, *, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    normalized = series.astype(str).str.strip().str.lower()
    if (~normalized.isin({"true", "false"})).any():
        raise ValueError(f"{label} contains non-boolean values.")
    return normalized.eq("true")


def build_eligible_case_worklist(
    case_registry: pd.DataFrame,
    model_eligibility: pd.DataFrame,
    artworks: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Join validated Notebook 08 cases to Notebook 01 prompt metadata."""
    validate_dataframe(case_registry, CASE_REGISTRY_SCHEMA, allow_extra_columns=True)
    validate_dataframe(model_eligibility, MODEL_ELIGIBILITY_SCHEMA, allow_extra_columns=True)
    artwork_columns = [
        "painting_id", "title", "artist", "date_or_period", "style_or_period", "category"
    ]
    missing = sorted(set(artwork_columns) - set(artworks.columns))
    if missing:
        raise ValueError(f"Artwork metadata is missing columns: {missing}")
    eligible = model_eligibility.loc[model_eligibility["model_id"].eq(MODEL_NAME)].copy()
    eligible["eligible"] = _coerce_bool(eligible["eligible"], label="eligible")
    eligible = eligible.loc[eligible["eligible"]].copy()
    worklist = case_registry.merge(
        eligible[["case_id", "eligibility_reason", "input_semantics", "mask_semantics", "restoration_objective"]],
        on="case_id", how="inner", validate="one_to_one",
    )
    worklist = worklist.merge(
        artworks[artwork_columns], on="painting_id", how="left", validate="many_to_one"
    )
    # Missing optional descriptive fields are rendered explicitly as "unknown";
    # painting_id/category linkage remains mandatory and is checked below.
    if worklist[["painting_id", "category"]].isna().any().any():
        raise ValueError("Eligible cases have missing mandatory artwork linkage metadata.")
    worklist["is_zero_control"] = (
        worklist["case_id"].astype(str).str.contains("zero_control", regex=False)
        | pd.to_numeric(worklist["realized_damage_fraction"], errors="coerce").fillna(0).eq(0)
    )
    worklist = worklist.sort_values(
        ["experiment_id", "painting_id", "case_id"], kind="stable"
    ).reset_index(drop=True)
    expected = int(config["expected"]["eligible_case_count"])
    if len(worklist) != expected:
        raise ValueError(f"Expected {expected} eligible cases, observed {len(worklist)}.")
    zero_expected = int(config["expected"]["zero_control_case_count"])
    if int(worklist["is_zero_control"].sum()) != zero_expected:
        raise ValueError("Eligible zero-control count does not match the contract.")
    return worklist


def build_prompt_policy(config: Mapping[str, Any]) -> pd.DataFrame:
    """Return the five-row frozen prompt-policy table."""
    policy = config["prompt_policy"]
    rows = []
    for order, variant in enumerate(PROMPT_VARIANTS):
        template = policy["generic_prompt"] if variant["prompt_variant_id"] == "p00_generic" else variant["template"]
        rows.append(
            {
                "prompt_policy_id": policy["policy_id"],
                "prompt_variant_id": variant["prompt_variant_id"],
                "variant_order": order,
                "variant_family": variant["variant_family"],
                "is_primary": variant["prompt_variant_id"] == policy["primary_variant_id"],
                "requires_metadata": variant["requires_metadata"],
                "metadata_fields": json.dumps(list(variant["metadata_fields"])),
                "prompt_template": template,
                "negative_prompt": policy["negative_prompt"],
                "status": "approved",
            }
        )
    result = pd.DataFrame(rows, columns=PROMPT_POLICY_COLUMNS)
    validate_dataframe(result, PROMPT_POLICY_SCHEMA)
    return result


def render_prompt(row: Mapping[str, Any], variant_id: str, config: Mapping[str, Any]) -> tuple[str, str]:
    variant = next((item for item in PROMPT_VARIANTS if item["prompt_variant_id"] == variant_id), None)
    if variant is None:
        raise KeyError(f"Unknown prompt variant: {variant_id}")
    if variant_id == "p00_generic":
        return str(config["prompt_policy"]["generic_prompt"]), "[]"
    values: dict[str, str] = {}
    used: list[str] = []
    for field in variant["metadata_fields"]:
        value = str(row.get(field, "")).strip()
        if not value or value.lower() == "nan":
            value = "unknown"
        else:
            used.append(field)
        values[field] = value.replace("_", " ")
    return variant["template"].format(**values), json.dumps(used)


def _hash_rank(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def select_prompt_ablation_cases(worklist: pd.DataFrame, config: Mapping[str, Any]) -> pd.DataFrame:
    """Select a fixed, stratified, metric-independent nonzero subset."""
    target = int(config["candidate_design"]["prompt_ablation_case_count"])
    candidates = worklist.loc[~worklist["is_zero_control"]].copy()
    required_metadata = tuple(
        str(value) for value in config["candidate_design"].get(
            "prompt_ablation_required_metadata", ()
        )
    )
    excluded_values = {
        str(value).strip().lower()
        for value in config["candidate_design"].get(
            "prompt_ablation_excluded_values", ("", "unknown", "nan")
        )
    }
    for column in required_metadata:
        if column not in candidates.columns:
            raise ValueError(f"Prompt-ablation metadata column is missing: {column}")
        normalized = candidates[column].fillna("").astype(str).str.strip().str.lower()
        candidates = candidates.loc[~normalized.isin(excluded_values)].copy()
    candidates["selection_stratum"] = (
        candidates["experiment_id"].astype(str) + "|" + candidates["category"].astype(str)
        + "|" + candidates["damage_or_degradation_type"].astype(str)
    )
    candidates["hash_rank"] = candidates["case_id"].map(lambda value: _hash_rank(f"prompt-ablation|{value}"))
    candidates = candidates.sort_values(["selection_stratum", "hash_rank"], kind="stable")
    candidates["round_index"] = candidates.groupby("selection_stratum").cumcount()
    selected = candidates.sort_values(
        ["round_index", "selection_stratum", "hash_rank"], kind="stable"
    ).head(target).copy()
    selected["selection_rank"] = range(1, len(selected) + 1)
    if len(selected) != target:
        raise ValueError(f"Could not select {target} prompt-ablation cases.")
    return selected.sort_values("selection_rank").reset_index(drop=True)


def select_uncertainty_cases(worklist: pd.DataFrame, config: Mapping[str, Any]) -> pd.DataFrame:
    """Select two paintings per category and four canonical nonzero masks each."""
    design = config["candidate_design"]
    mask_types = tuple(str(value) for value in design["uncertainty_mask_types"])
    canonical = worklist.loc[
        worklist["experiment_id"].eq("canonical_missing_region") & ~worklist["is_zero_control"]
    ].copy()
    canonical["canonical_mask_type"] = canonical["case_id"].astype(str).str.split("__").str[-1]
    canonical = canonical.loc[canonical["canonical_mask_type"].isin(mask_types)].copy()
    paintings = canonical[["painting_id", "category"]].drop_duplicates()
    paintings["hash_rank"] = paintings.apply(
        lambda row: _hash_rank(f"uncertainty|{row['category']}|{row['painting_id']}"), axis=1
    )
    paintings = paintings.sort_values(["category", "hash_rank"], kind="stable")
    chosen = paintings.groupby("category", sort=True).head(int(design["uncertainty_paintings_per_category"]))
    selected = canonical.merge(
        chosen[["painting_id", "category"]], on=["painting_id", "category"], how="inner"
    ).sort_values(["category", "painting_id", "canonical_mask_type"], kind="stable").reset_index(drop=True)
    expected = int(config["expected"]["uncertainty_case_count"])
    if len(selected) != expected:
        raise ValueError(f"Expected {expected} uncertainty cases, observed {len(selected)}.")
    selected["selection_rank"] = range(1, len(selected) + 1)
    return selected


def build_prompt_ablation_design(
    prompt_cases: pd.DataFrame, uncertainty_cases: pd.DataFrame, config: Mapping[str, Any]
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    policy = config["candidate_design"]["selection_policy"]
    for component, frame, prompt_count, seed_count in (
        ("prompt_ablation", prompt_cases, 4, 1),
        ("uncertainty", uncertainty_cases, 1, len(config["candidate_design"]["uncertainty_seeds"])),
    ):
        for _, row in frame.iterrows():
            rows.append(
                {
                    "design_row_id": f"{component}__{row['case_id']}", "case_id": row["case_id"],
                    "painting_id": row["painting_id"], "category": row["category"],
                    "experiment_id": row["experiment_id"],
                    "damage_or_degradation_type": row["damage_or_degradation_type"],
                    "design_component": component, "selection_policy": policy,
                    "selection_rank": int(row["selection_rank"]),
                    "prompt_variant_count": prompt_count, "seed_count": seed_count,
                    "included": True, "status": "approved",
                }
            )
    result = pd.DataFrame(rows, columns=PROMPT_ABLATION_DESIGN_COLUMNS)
    validate_dataframe(result, PROMPT_ABLATION_DESIGN_SCHEMA)
    expected = int(config["expected"]["prompt_ablation_design_row_count"])
    if len(result) != expected:
        raise ValueError(f"Expected {expected} design rows, observed {len(result)}.")
    return result


def _candidate_id(case_id: str, variant_id: str, seed: int, role: str) -> str:
    # case_id remains explicit in the parent directory and candidate table; a
    # 12-hex identity digest avoids unsafe Windows/Git path lengths.
    digest = _hash_rank(f"{case_id}|{variant_id}|{seed}|{role}")[:12]
    variant_token = variant_id.split("_", maxsplit=1)[0]
    return f"sd15__{variant_token}__s{seed}__{digest}"


def _mask_threshold(row: Mapping[str, Any], config: Mapping[str, Any]) -> int:
    family = "synthetic_degradation" if row["experiment_id"] == "synthetic_degradation" else "binary_missing_region"
    return int(config["model"]["mask_threshold_policy"][family]["threshold"])


def build_candidate_plan(
    worklist: pd.DataFrame,
    prompt_cases: pd.DataFrame,
    uncertainty_cases: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build the exact 1,010-row union of primary, prompt, and seed candidates."""
    prompt_ids = set(prompt_cases["case_id"])
    uncertainty_ids = set(uncertainty_cases["case_id"])
    primary_seed = int(config["candidate_design"]["primary_seed"])
    contextual_variants = tuple(config["prompt_policy"]["contextual_variant_ids"])
    extension_seeds = [
        int(seed) for seed in config["candidate_design"]["uncertainty_seeds"]
        if int(seed) != primary_seed
    ]
    fingerprint = configuration_fingerprint(config)
    model = config["model"]
    output = config["output"]
    rows: list[dict[str, Any]] = []

    def add_candidate(source: Mapping[str, Any], variant_id: str, seed: int, role: str) -> None:
        candidate_id = _candidate_id(str(source["case_id"]), variant_id, seed, role)
        prompt, metadata_fields = render_prompt(source, variant_id, config)
        relative = output["restored_path_template"].format(
            experiment_id=source["experiment_id"], case_id=source["case_id"], candidate_id=candidate_id
        )
        rows.append(
            {
                "candidate_id": candidate_id, "candidate_index": 0,
                "case_id": source["case_id"], "painting_id": source["painting_id"],
                "category": source["category"], "experiment_id": source["experiment_id"],
                "damage_or_degradation_type": source["damage_or_degradation_type"],
                "mask_or_effect_id": source["mask_or_effect_id"],
                "input_image_path": source["input_image_path"],
                "clean_image_path": source["clean_image_path"],
                "mask_or_effect_path": source["mask_or_effect_path"],
                "input_sha256": "", "mask_sha256": "", "model_id": model["model_id"],
                "hf_model_id": model["hf_model_id"], "model_revision": model["model_revision"],
                "configuration_id": model["configuration_id"],
                "prompt_policy_id": config["prompt_policy"]["policy_id"],
                "prompt_variant_id": variant_id, "prompt": prompt,
                "negative_prompt": config["prompt_policy"]["negative_prompt"],
                "prompt_metadata_fields_used": metadata_fields, "seed": seed,
                "execution_role": role, "is_primary_candidate": role == "primary",
                "is_prompt_ablation_candidate": source["case_id"] in prompt_ids,
                "is_uncertainty_candidate": source["case_id"] in uncertainty_ids,
                "candidate_selection_policy": config["candidate_design"]["selection_policy"],
                "num_inference_steps": int(model["num_inference_steps"]),
                "guidance_scale": float(model["guidance_scale"]), "strength": float(model["strength"]),
                "scheduler": model["scheduler"], "precision": model["precision"],
                "device": model["requested_device"],
                "inference_width": int(model["inference_width"]),
                "inference_height": int(model["inference_height"]),
                "output_width": int(model["output_width"]), "output_height": int(model["output_height"]),
                "mask_threshold": _mask_threshold(source, config),
                "compositing_policy": model["compositing_policy"],
                "safety_checker_policy": model["safety_checker_policy"],
                "execution_action": "pending",
                "restored_path": str(Path(output["restored_directory"]) / Path(relative)).replace("\\", "/"),
                "restored_sha256": "", "runtime_seconds": np.nan,
                "gpu_memory_before_bytes": np.nan, "gpu_memory_after_bytes": np.nan,
                "gpu_peak_memory_bytes": np.nan, "retry_count": 0, "attempt_count": 0,
                "configuration_fingerprint": fingerprint, "started_at_utc": "",
                "completed_at_utc": "", "generator_name": RESTORATION_GENERATOR_NAME,
                "generator_version": RESTORATION_GENERATOR_VERSION, "status": "planned", "issue": "",
            }
        )

    for _, source in worklist.iterrows():
        add_candidate(source, "p00_generic", primary_seed, "primary")
        if source["case_id"] in prompt_ids:
            for variant_id in contextual_variants:
                add_candidate(source, variant_id, primary_seed, "prompt_context")
        if source["case_id"] in uncertainty_ids:
            for seed in extension_seeds:
                add_candidate(source, "p00_generic", seed, "uncertainty_extension")

    result = pd.DataFrame(rows, columns=STABLE_DIFFUSION_CANDIDATE_COLUMNS)
    result["candidate_index"] = result.groupby("case_id", sort=False).cumcount()
    if result["candidate_id"].duplicated().any():
        raise ValueError("Candidate IDs are not unique.")
    expected = int(config["expected"]["candidate_count"])
    if len(result) != expected:
        raise ValueError(f"Expected {expected} candidates, observed {len(result)}.")
    counts = result.groupby("execution_role").size().to_dict()
    expected_counts = {
        "primary": int(config["expected"]["primary_candidate_count"]),
        "prompt_context": int(config["expected"]["prompt_context_candidate_count"]),
        "uncertainty_extension": int(config["expected"]["uncertainty_extension_candidate_count"]),
    }
    if counts != expected_counts:
        raise ValueError(f"Candidate role counts differ: {counts} != {expected_counts}")
    validate_dataframe(result, STABLE_DIFFUSION_CANDIDATES_SCHEMA)
    return result


def materialize_input_checksums(
    candidates: pd.DataFrame, *, project_root: str | Path,
    progress_callback: ProgressCallback | None = None,
) -> pd.DataFrame:
    """Hash each unique input and mask once and populate the candidate plan."""
    root = Path(project_root)
    result = candidates.copy()
    cache: dict[str, str] = {}
    pairs = result[["input_image_path", "mask_or_effect_path"]].drop_duplicates()
    total = len(pairs)
    for number, (_, pair) in enumerate(pairs.iterrows(), start=1):
        for column in ("input_image_path", "mask_or_effect_path"):
            relative = str(pair[column])
            if relative not in cache:
                path = Path(relative)
                resolved = path if path.is_absolute() else root / path
                if not resolved.is_file():
                    raise FileNotFoundError(resolved)
                cache[relative] = calculate_file_sha256(resolved)
        if progress_callback and (number % 10 == 0 or number == total):
            progress_callback(f"Checksummed {number}/{total} unique case input pairs")
    result["input_sha256"] = result["input_image_path"].map(cache)
    result["mask_sha256"] = result["mask_or_effect_path"].map(cache)
    return result


def binarize_mask(mask: Image.Image | np.ndarray, threshold: int) -> np.ndarray:
    array = np.asarray(mask.convert("L") if isinstance(mask, Image.Image) else mask, dtype=np.uint8)
    return np.where(array >= int(threshold), 255, 0).astype(np.uint8)


def masked_composite(source: np.ndarray, generated: np.ndarray, binary_mask: np.ndarray) -> np.ndarray:
    if source.shape != generated.shape or source.shape[:2] != binary_mask.shape:
        raise ValueError("Source, generated image, and mask geometry must agree.")
    output = source.copy()
    output[binary_mask > 0] = generated[binary_mask > 0]
    return output


def prepare_inpaint_inputs(candidate: Mapping[str, Any], *, project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root)
    input_path = Path(str(candidate["input_image_path"]))
    mask_path = Path(str(candidate["mask_or_effect_path"]))
    input_path = input_path if input_path.is_absolute() else root / input_path
    mask_path = mask_path if mask_path.is_absolute() else root / mask_path
    with Image.open(input_path) as image:
        source = image.convert("RGB")
    with Image.open(mask_path) as image:
        binary = binarize_mask(image, int(candidate["mask_threshold"]))
    output_size = (int(candidate["output_width"]), int(candidate["output_height"]))
    if source.size != output_size:
        source = source.resize(output_size, Image.Resampling.LANCZOS)
        binary = np.asarray(Image.fromarray(binary).resize(output_size, Image.Resampling.NEAREST))
    inference_size = (int(candidate["inference_width"]), int(candidate["inference_height"]))
    return {
        "source_image": source, "binary_mask": binary,
        "inference_image": source.resize(inference_size, Image.Resampling.LANCZOS),
        "inference_mask": Image.fromarray(binary, mode="L").resize(inference_size, Image.Resampling.NEAREST),
    }


def gpu_memory_snapshot(device: str) -> dict[str, int]:
    if device != "cuda":
        return {"allocated": 0, "reserved": 0, "peak": 0}
    import torch
    return {
        "allocated": int(torch.cuda.memory_allocated()),
        "reserved": int(torch.cuda.memory_reserved()),
        "peak": int(torch.cuda.max_memory_allocated()),
    }


def runtime_environment(device: str) -> dict[str, Any]:
    import torch
    packages = {}
    for name in ("torch", "diffusers", "transformers", "accelerate", "safetensors", "Pillow"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = "not-installed"
    return {
        "python_version": platform.python_version(), "platform": platform.platform(),
        "machine": platform.machine(), "processor": platform.processor(), "device": device,
        "cuda_available": bool(torch.cuda.is_available()), "cuda_version": str(torch.version.cuda or ""),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "",
        "package_versions": packages,
    }


def load_stable_diffusion_pipeline(config: Mapping[str, Any]):
    """Load the pinned Diffusers pipeline; never silently falls back to CPU."""
    import torch
    from diffusers import DDIMScheduler, StableDiffusionInpaintPipeline

    model = config["model"]
    requested = str(model["requested_device"])
    if requested == "cuda" and not torch.cuda.is_available():
        if not bool(model["allow_cpu_fallback"]):
            raise RuntimeError("CUDA is required by the Notebook 11 contract but is unavailable.")
        requested = "cpu"
    dtype = torch.float16 if model["precision"] == "float16" and requested == "cuda" else torch.float32
    pipeline = StableDiffusionInpaintPipeline.from_pretrained(
        model["hf_model_id"], revision=model["model_revision"], torch_dtype=dtype,
        safety_checker=None, requires_safety_checker=False,
    )
    pipeline.scheduler = DDIMScheduler.from_config(pipeline.scheduler.config)
    if bool(model.get("attention_slicing", False)):
        pipeline.enable_attention_slicing()
    pipeline = pipeline.to(requested)
    return pipeline, requested


def _atomic_checkpoint(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def _resume_record_valid(
    record: Mapping[str, Any], candidate: Mapping[str, Any], *, notebook_output_root: Path
) -> bool:
    exact_fields = (
        "candidate_id", "input_sha256", "mask_sha256", "hf_model_id", "model_revision",
        "configuration_fingerprint", "restored_path", "output_width", "output_height",
        "compositing_policy",
    )
    if any(str(record.get(field, "")) != str(candidate.get(field, "")) for field in exact_fields):
        return False
    if str(record.get("status", "")) != "completed":
        return False
    path = Path(str(candidate["restored_path"]))
    resolved = path if path.is_absolute() else notebook_output_root / path
    if not resolved.is_file() or not str(record.get("restored_sha256", "")):
        return False
    try:
        with Image.open(resolved) as image:
            if image.size != (int(candidate["output_width"]), int(candidate["output_height"])) or image.mode != "RGB":
                return False
        return calculate_file_sha256(resolved) == str(record["restored_sha256"])
    except OSError:
        return False


def run_stable_diffusion_candidate(
    candidate: Mapping[str, Any], *, pipeline: Any, device: str,
    project_root: str | Path, notebook_output_root: str | Path,
    config: Mapping[str, Any], generator_factory: Callable[[str, int], Any] | None = None,
) -> dict[str, Any]:
    """Execute one candidate; retries always recreate the exact declared seed."""
    record = dict(candidate)
    started = utc_now_iso()
    clock = time.perf_counter()
    prepared = prepare_inpaint_inputs(candidate, project_root=project_root)
    source_array = np.asarray(prepared["source_image"], dtype=np.uint8)
    binary = prepared["binary_mask"]
    destination = Path(str(candidate["restored_path"]))
    output_root = Path(notebook_output_root)
    destination = destination if destination.is_absolute() else output_root / destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    before = gpu_memory_snapshot(device)
    if device == "cuda":
        import torch
        torch.cuda.reset_peak_memory_stats()
    attempts = int(config["model"]["maximum_retries"]) + 1
    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            if not np.any(binary):
                composed = source_array
                action = "identity_noop"
            else:
                seed = int(candidate["seed"])
                if generator_factory is None:
                    import torch
                    generator = torch.Generator(device=device).manual_seed(seed)
                else:
                    generator = generator_factory(device, seed)
                result = pipeline(
                    prompt=str(candidate["prompt"]), negative_prompt=str(candidate["negative_prompt"]),
                    image=prepared["inference_image"], mask_image=prepared["inference_mask"],
                    num_inference_steps=int(candidate["num_inference_steps"]),
                    guidance_scale=float(candidate["guidance_scale"]), strength=float(candidate["strength"]),
                    generator=generator,
                )
                generated = result.images[0].convert("RGB").resize(
                    prepared["source_image"].size, Image.Resampling.LANCZOS
                )
                composed = masked_composite(source_array, np.asarray(generated), binary)
                action = "stable_diffusion_inpaint"
            Image.fromarray(composed, mode="RGB").save(
                destination, format="PNG", compress_level=int(config["execution"]["png_compress_level"])
            )
            after = gpu_memory_snapshot(device)
            record.update(
                {
                    "execution_action": action, "restored_sha256": calculate_file_sha256(destination),
                    "runtime_seconds": time.perf_counter() - clock,
                    "gpu_memory_before_bytes": before["allocated"],
                    "gpu_memory_after_bytes": after["allocated"],
                    "gpu_peak_memory_bytes": after["peak"], "retry_count": attempt - 1,
                    "attempt_count": attempt, "started_at_utc": started,
                    "completed_at_utc": utc_now_iso(), "device": device,
                    "status": "completed", "issue": "",
                }
            )
            return record
        except Exception as exc:  # noqa: BLE001 - candidate failures are persisted
            last_error = f"{type(exc).__name__}: {exc}"
    after = gpu_memory_snapshot(device)
    record.update(
        {
            "execution_action": "failed", "runtime_seconds": time.perf_counter() - clock,
            "gpu_memory_before_bytes": before["allocated"],
            "gpu_memory_after_bytes": after["allocated"], "gpu_peak_memory_bytes": after["peak"],
            "retry_count": attempts - 1, "attempt_count": attempts, "started_at_utc": started,
            "completed_at_utc": utc_now_iso(), "device": device, "status": "failed", "issue": last_error,
        }
    )
    return record


def run_stable_diffusion_candidates(
    candidates: pd.DataFrame, *, pipeline: Any, device: str,
    project_root: str | Path, notebook_output_root: str | Path,
    config: Mapping[str, Any], checkpoint_path: str | Path,
    progress_callback: ProgressCallback | None = print,
    generator_factory: Callable[[str, int], Any] | None = None,
) -> pd.DataFrame:
    """Run or strictly resume a plan with atomic checkpoints and progress every 10."""
    output_root = Path(notebook_output_root)
    checkpoint = Path(checkpoint_path)
    prior = pd.read_csv(checkpoint).fillna("") if checkpoint.is_file() else pd.DataFrame()
    prior_by_id = {
        str(row["candidate_id"]): row for _, row in prior.iterrows()
    } if not prior.empty and "candidate_id" in prior else {}
    records: list[dict[str, Any]] = []
    interval = int(config["execution"]["progress_interval_candidates"])
    checkpoint_interval = int(config["execution"]["checkpoint_interval_candidates"])
    total = len(candidates)
    for number, (_, candidate) in enumerate(candidates.iterrows(), start=1):
        candidate_dict = candidate.to_dict()
        prior_record = prior_by_id.get(str(candidate["candidate_id"]))
        if bool(config["execution"]["resume_enabled"]) and prior_record is not None and _resume_record_valid(
            prior_record, candidate_dict, notebook_output_root=output_root
        ):
            record = dict(prior_record)
            record["execution_action"] = "reused_validated"
        else:
            destination = Path(str(candidate["restored_path"]))
            destination = destination if destination.is_absolute() else output_root / destination
            if destination.exists() and not bool(config["execution"]["overwrite_existing"]):
                if config["execution"]["stale_file_action"] == "remove":
                    destination.unlink()
                else:
                    raise FileExistsError(f"Unvalidated stale output exists: {destination}")
            record = run_stable_diffusion_candidate(
                candidate_dict, pipeline=pipeline, device=device, project_root=project_root,
                notebook_output_root=output_root, config=config, generator_factory=generator_factory,
            )
        records.append(record)
        if number % checkpoint_interval == 0 or number == total:
            _atomic_checkpoint(pd.DataFrame(records, columns=STABLE_DIFFUSION_CANDIDATE_COLUMNS), checkpoint)
        if progress_callback and (number % interval == 0 or number == total):
            completed = sum(item["status"] == "completed" for item in records)
            failed = sum(item["status"] == "failed" for item in records)
            progress_callback(f"Stable Diffusion candidates: {number}/{total} | completed={completed} | failed={failed}")
    return pd.DataFrame(records, columns=STABLE_DIFFUSION_CANDIDATE_COLUMNS)


def validate_candidate_outputs(
    candidates: pd.DataFrame, *, project_root: str | Path, notebook_output_root: str | Path
) -> pd.DataFrame:
    """Reload every output and audit checksum, geometry, mask, and outside invariance."""
    root = Path(project_root)
    output_root = Path(notebook_output_root)
    rows: list[dict[str, Any]] = []
    for _, candidate in candidates.iterrows():
        path = Path(str(candidate["restored_path"]))
        path = path if path.is_absolute() else output_root / path
        passed = True
        details: list[str] = []
        outside_changed = -1
        inside_changed = -1
        checksum_matches = False
        geometry_valid = False
        zero_valid = False
        try:
            prepared = prepare_inpaint_inputs(candidate, project_root=root)
            source = np.asarray(prepared["source_image"], dtype=np.uint8)
            binary = prepared["binary_mask"] > 0
            with Image.open(path) as image:
                geometry_valid = (
                    image.size == (int(candidate["output_width"]), int(candidate["output_height"]))
                    and image.mode == "RGB"
                )
                restored = np.asarray(image.convert("RGB"), dtype=np.uint8)
            difference = np.any(source != restored, axis=2)
            outside_changed = int(np.count_nonzero(difference & ~binary))
            inside_changed = int(np.count_nonzero(difference & binary))
            checksum_matches = calculate_file_sha256(path) == str(candidate["restored_sha256"])
            zero_valid = bool(np.any(binary)) or not bool(np.any(difference))
            passed = geometry_valid and checksum_matches and outside_changed == 0 and zero_valid
            if not passed:
                details.append("output contract mismatch")
        except Exception as exc:  # noqa: BLE001 - validation records failure details
            passed = False
            details.append(f"{type(exc).__name__}: {exc}")
        rows.append(
            {
                "candidate_id": candidate["candidate_id"], "case_id": candidate["case_id"],
                "file_exists": path.is_file(), "geometry_valid": geometry_valid,
                "checksum_matches": checksum_matches,
                "outside_mask_changed_pixels": outside_changed,
                "inside_mask_changed_pixels": inside_changed,
                "zero_control_valid": zero_valid, "passed": passed,
                "details": "; ".join(details),
            }
        )
    return pd.DataFrame(rows)


def summarize_runtime(candidates: pd.DataFrame) -> pd.DataFrame:
    """Summarize timing overall and by experiment, execution role, and prompt."""
    rows: list[dict[str, Any]] = []

    def add(scope: str, value: str, frame: pd.DataFrame) -> None:
        runtimes = pd.to_numeric(frame["runtime_seconds"], errors="coerce").dropna()
        completed = int(frame["status"].eq("completed").sum())
        failed = int(frame["status"].eq("failed").sum())
        total = float(runtimes.sum())
        rows.append(
            {
                "summary_scope": scope, "experiment_id": value, "case_count": len(frame),
                "completed_count": completed, "failed_count": failed,
                "total_runtime_seconds": total,
                "mean_runtime_seconds": float(runtimes.mean()) if len(runtimes) else 0.0,
                "median_runtime_seconds": float(runtimes.median()) if len(runtimes) else 0.0,
                "p95_runtime_seconds": float(runtimes.quantile(0.95)) if len(runtimes) else 0.0,
                "max_runtime_seconds": float(runtimes.max()) if len(runtimes) else 0.0,
                "throughput_cases_per_second": completed / total if total > 0 else 0.0,
                "status": "completed" if failed == 0 else "has_failures",
            }
        )

    add("overall", "all", candidates)
    for scope, column in (
        ("experiment", "experiment_id"),
        ("execution_role", "execution_role"),
        ("prompt_variant", "prompt_variant_id"),
    ):
        for value, frame in candidates.groupby(column, sort=True):
            add(scope, str(value), frame)
    result = pd.DataFrame(rows, columns=RESTORATION_RUNTIME_SUMMARY_COLUMNS)
    validate_dataframe(result, RESTORATION_RUNTIME_SUMMARY_SCHEMA)
    return result
