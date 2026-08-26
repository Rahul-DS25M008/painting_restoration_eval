"""Paired all-painting scratch-prompt extension for Notebook 11.

This module deliberately wraps the frozen Stable Diffusion 1.5 preparation
layer.  It preserves the existing 1,010 candidates and adds only the missing
members of a 50-painting x 4-seed x 2-prompt paired scratch experiment.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
import yaml

from .restoration_stable_diffusion import (
    build_candidate_plan,
    build_prompt_ablation_design,
    build_prompt_policy,
    configuration_fingerprint,
)
from .schemas import (
    PROMPT_ABLATION_DESIGN_COLUMNS,
    PROMPT_ABLATION_DESIGN_SCHEMA,
    PROMPT_POLICY_COLUMNS,
    PROMPT_POLICY_SCHEMA,
    STABLE_DIFFUSION_CANDIDATE_COLUMNS,
    STABLE_DIFFUSION_CANDIDATES_SCHEMA,
    validate_dataframe,
)


SCRATCH_PROMPT_EXTENSION_NAME = (
    "restoration_eval.restoration_stable_diffusion_scratch_prompt"
)
SCRATCH_PROMPT_EXTENSION_VERSION = "1.0.0"
SCRATCH_PROMPT_CONFIG_SCHEMA_VERSION = (
    "stable_diffusion_scratch_prompt_ablation_config.v1"
)
SCRATCH_PROMPT_VARIANT_ID = "p05_scratch_aware"


def _require_keys(mapping: Mapping[str, Any], keys: set[str], *, label: str) -> None:
    missing = sorted(keys - set(mapping))
    if missing:
        raise ValueError(f"{label} is missing required keys: {missing}")


def load_scratch_prompt_ablation_config(path: str | Path) -> dict[str, Any]:
    """Load and validate the supplementary paired scratch-prompt contract."""
    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Scratch-prompt ablation configuration must be a mapping.")
    _require_keys(
        config,
        {
            "config_schema_version", "config_version", "base_config_path",
            "effective_prompt_policy", "candidate_design", "expected", "smoke",
            "known_limitations",
        },
        label="Scratch-prompt ablation configuration",
    )
    if config["config_schema_version"] != SCRATCH_PROMPT_CONFIG_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported scratch-prompt schema: {config['config_schema_version']!r}"
        )
    prompt = config["effective_prompt_policy"]
    design = config["candidate_design"]
    expected = config["expected"]
    _require_keys(
        prompt,
        {
            "policy_id", "prompt_variant_id", "variant_family", "metadata_fields",
            "positive_prompt", "negative_prompt_extension",
        },
        label="Scratch-aware prompt policy",
    )
    _require_keys(
        design,
        {
            "experiment_id", "canonical_damage_type", "case_id_suffix",
            "painting_count", "prompt_variant_ids", "seeds", "selection_policy",
            "design_component", "generic_extension_role", "damage_prompt_role",
            "prohibit_metric_selection",
        },
        label="Scratch-prompt candidate design",
    )
    _require_keys(
        expected,
        {
            "scratch_case_count", "prompt_arm_count", "seed_count",
            "paired_outcome_count", "existing_generic_outcome_count",
            "generic_extension_candidate_count", "damage_prompt_candidate_count",
            "additional_candidate_count", "effective_candidate_count",
            "effective_model_inference_candidate_count", "effective_restored_file_count",
            "effective_prompt_policy_row_count",
            "effective_prompt_ablation_design_row_count",
            "effective_artifact_record_count",
            "effective_total_output_file_count_without_failure_logs",
        },
        label="Scratch-prompt expected counts",
    )
    if prompt["prompt_variant_id"] != SCRATCH_PROMPT_VARIANT_ID:
        raise ValueError(f"Prompt variant must be {SCRATCH_PROMPT_VARIANT_ID!r}.")
    if prompt["variant_family"] != "damage_aware":
        raise ValueError("Supplementary prompt family must be damage_aware.")
    if list(design["prompt_variant_ids"]) != ["p00_generic", SCRATCH_PROMPT_VARIANT_ID]:
        raise ValueError("Prompt arms must be p00_generic and p05_scratch_aware.")
    seeds = [int(seed) for seed in design["seeds"]]
    if len(seeds) != len(set(seeds)) or len(seeds) != int(expected["seed_count"]):
        raise ValueError("Scratch-prompt seeds must be unique and match seed_count.")
    if not bool(design["prohibit_metric_selection"]):
        raise ValueError("Metric-based selection must remain prohibited.")
    paired = (
        int(expected["scratch_case_count"])
        * int(expected["prompt_arm_count"])
        * int(expected["seed_count"])
    )
    if int(expected["paired_outcome_count"]) != paired:
        raise ValueError("Paired outcome count is internally inconsistent.")
    additional = (
        int(expected["generic_extension_candidate_count"])
        + int(expected["damage_prompt_candidate_count"])
    )
    if int(expected["additional_candidate_count"]) != additional:
        raise ValueError("Additional candidate count is internally inconsistent.")
    return config


def build_effective_stable_diffusion_config(
    base_config: Mapping[str, Any], scratch_config: Mapping[str, Any]
) -> dict[str, Any]:
    """Build manifest/report expectations without mutating the frozen base config."""
    merged = copy.deepcopy(dict(base_config))
    extension = copy.deepcopy(dict(scratch_config))
    design = extension["candidate_design"]
    expected = extension["expected"]
    if [int(seed) for seed in merged["candidate_design"]["uncertainty_seeds"]] != [
        int(seed) for seed in design["seeds"]
    ]:
        raise ValueError("Scratch-prompt seeds must reuse the frozen uncertainty seeds.")
    if int(merged["candidate_design"]["primary_seed"]) != int(design["seeds"][0]):
        raise ValueError("The first scratch-prompt seed must be the primary seed.")
    merged["scratch_prompt_ablation"] = extension
    merged["prompt_policy"]["policy_id"] = extension["effective_prompt_policy"][
        "policy_id"
    ]
    merged["expected"].update(
        {
            "scratch_prompt_case_count": int(expected["scratch_case_count"]),
            "scratch_seed_control_extension_candidate_count": int(
                expected["generic_extension_candidate_count"]
            ),
            "scratch_damage_prompt_candidate_count": int(
                expected["damage_prompt_candidate_count"]
            ),
            "scratch_prompt_paired_outcome_count": int(expected["paired_outcome_count"]),
            "candidate_count": int(expected["effective_candidate_count"]),
            "model_inference_candidate_count": int(
                expected["effective_model_inference_candidate_count"]
            ),
            "restored_file_count": int(expected["effective_restored_file_count"]),
            "prompt_policy_row_count": int(expected["effective_prompt_policy_row_count"]),
            "prompt_ablation_design_row_count": int(
                expected["effective_prompt_ablation_design_row_count"]
            ),
            "artifact_record_count": int(expected["effective_artifact_record_count"]),
            "total_output_file_count_without_failure_logs": int(
                expected["effective_total_output_file_count_without_failure_logs"]
            ),
        }
    )
    merged["known_limitations"] = list(merged["known_limitations"]) + list(
        extension["known_limitations"]
    )
    return merged


def select_scratch_prompt_cases(
    worklist: pd.DataFrame, scratch_config: Mapping[str, Any]
) -> pd.DataFrame:
    """Select every canonical scratch case; this is enumeration, not ranking."""
    design = scratch_config["candidate_design"]
    selected = worklist.loc[
        worklist["experiment_id"].eq(str(design["experiment_id"]))
        & worklist["case_id"].astype(str).str.endswith(str(design["case_id_suffix"]))
        & worklist["damage_or_degradation_type"].eq(
            str(design["canonical_damage_type"])
        )
        & ~worklist["is_zero_control"].astype(bool)
    ].copy()
    selected = selected.sort_values(["painting_id", "case_id"], kind="stable").reset_index(
        drop=True
    )
    selected["selection_rank"] = range(1, len(selected) + 1)
    expected = int(scratch_config["expected"]["scratch_case_count"])
    if len(selected) != expected:
        raise ValueError(f"Expected {expected} canonical scratch cases, observed {len(selected)}.")
    if selected["painting_id"].nunique() != int(design["painting_count"]):
        raise ValueError("Canonical scratch cases do not cover all declared paintings.")
    if selected.groupby("painting_id").size().max() != 1:
        raise ValueError("Each painting must contribute exactly one canonical scratch case.")
    return selected


def _combined_negative_prompt(
    base_config: Mapping[str, Any], scratch_config: Mapping[str, Any]
) -> str:
    return (
        str(base_config["prompt_policy"]["negative_prompt"]).rstrip(" ,")
        + ", "
        + str(scratch_config["effective_prompt_policy"]["negative_prompt_extension"])
        .strip(" ,")
    )


def build_effective_prompt_policy(
    base_config: Mapping[str, Any], scratch_config: Mapping[str, Any]
) -> pd.DataFrame:
    """Append the approved scratch-aware treatment to the frozen five-row policy."""
    result = build_prompt_policy(base_config).copy()
    prompt = scratch_config["effective_prompt_policy"]
    policy_id = str(prompt["policy_id"])
    result["prompt_policy_id"] = policy_id
    # prompt_policy.v1 names all non-primary conditioning variants contextual;
    # the explicit p05 ID and metadata field retain the damage-aware semantics.
    row = {
        "prompt_policy_id": policy_id,
        "prompt_variant_id": SCRATCH_PROMPT_VARIANT_ID,
        "variant_order": len(result),
        "variant_family": "contextual",
        "is_primary": False,
        "requires_metadata": True,
        "metadata_fields": json.dumps(list(prompt["metadata_fields"])),
        "prompt_template": str(prompt["positive_prompt"]),
        "negative_prompt": _combined_negative_prompt(base_config, scratch_config),
        "status": "approved",
    }
    result = pd.concat(
        [result, pd.DataFrame([row], columns=PROMPT_POLICY_COLUMNS)], ignore_index=True
    )
    validate_dataframe(result, PROMPT_POLICY_SCHEMA)
    expected = int(scratch_config["expected"]["effective_prompt_policy_row_count"])
    if len(result) != expected:
        raise ValueError(f"Expected {expected} effective prompt-policy rows.")
    return result


def build_effective_prompt_ablation_design(
    prompt_cases: pd.DataFrame,
    uncertainty_cases: pd.DataFrame,
    scratch_cases: pd.DataFrame,
    base_config: Mapping[str, Any],
    scratch_config: Mapping[str, Any],
) -> pd.DataFrame:
    """Extend the existing design table with 50 predeclared paired scratch rows."""
    result = build_prompt_ablation_design(
        prompt_cases, uncertainty_cases, base_config
    ).copy()
    design = scratch_config["candidate_design"]
    rows = []
    for _, row in scratch_cases.iterrows():
        rows.append(
            {
                "design_row_id": f"scratch_prompt_ablation__{row['case_id']}",
                "case_id": row["case_id"],
                "painting_id": row["painting_id"],
                "category": row["category"],
                "experiment_id": row["experiment_id"],
                "damage_or_degradation_type": row["damage_or_degradation_type"],
                # prompt_ablation is the compatible prompt_ablation_design.v1 enum;
                # selection_policy distinguishes this all-painting paired component.
                "design_component": "prompt_ablation",
                "selection_policy": design["selection_policy"],
                "selection_rank": int(row["selection_rank"]),
                "prompt_variant_count": len(design["prompt_variant_ids"]),
                "seed_count": len(design["seeds"]),
                "included": True,
                "status": "approved",
            }
        )
    result = pd.concat(
        [result, pd.DataFrame(rows, columns=PROMPT_ABLATION_DESIGN_COLUMNS)],
        ignore_index=True,
    )
    validate_dataframe(result, PROMPT_ABLATION_DESIGN_SCHEMA)
    expected = int(
        scratch_config["expected"]["effective_prompt_ablation_design_row_count"]
    )
    if len(result) != expected:
        raise ValueError(f"Expected {expected} effective prompt-design rows.")
    return result


def _candidate_id(case_id: str, variant_id: str, seed: int, role: str) -> str:
    digest = hashlib.sha256(
        f"{case_id}|{variant_id}|{seed}|{role}".encode("utf-8")
    ).hexdigest()[:12]
    return f"sd15__{variant_id.split('_', maxsplit=1)[0]}__s{seed}__{digest}"


def build_effective_candidate_plan(
    worklist: pd.DataFrame,
    prompt_cases: pd.DataFrame,
    uncertainty_cases: pd.DataFrame,
    scratch_cases: pd.DataFrame,
    base_config: Mapping[str, Any],
    scratch_config: Mapping[str, Any],
) -> pd.DataFrame:
    """Preserve 1,010 candidates and add the 320 missing paired outcomes."""
    result = build_candidate_plan(
        worklist, prompt_cases, uncertainty_cases, base_config
    ).copy()
    effective = build_effective_stable_diffusion_config(base_config, scratch_config)
    design = scratch_config["candidate_design"]
    expected = scratch_config["expected"]
    scratch_ids = set(scratch_cases["case_id"].astype(str))
    seeds = [int(seed) for seed in design["seeds"]]
    policy_id = str(scratch_config["effective_prompt_policy"]["policy_id"])
    fingerprint = configuration_fingerprint(effective)
    result["prompt_policy_id"] = policy_id
    result["configuration_fingerprint"] = fingerprint
    result["generator_name"] = SCRATCH_PROMPT_EXTENSION_NAME
    result["generator_version"] = SCRATCH_PROMPT_EXTENSION_VERSION
    p00_scratch = result["case_id"].isin(scratch_ids) & result[
        "prompt_variant_id"
    ].eq("p00_generic")
    result.loc[p00_scratch, "is_prompt_ablation_candidate"] = True

    primary_by_case = {
        str(row["case_id"]): row.to_dict()
        for _, row in result.loc[
            result["is_primary_candidate"] & result["case_id"].isin(scratch_ids)
        ].iterrows()
    }
    existing = {
        (str(row["case_id"]), str(row["prompt_variant_id"]), int(row["seed"]))
        for _, row in result.iterrows()
    }
    added: list[dict[str, Any]] = []

    def add_from_primary(
        primary: Mapping[str, Any], variant_id: str, seed: int, role: str
    ) -> None:
        row = dict(primary)
        case_id = str(primary["case_id"])
        candidate_id = _candidate_id(case_id, variant_id, seed, role)
        relative = base_config["output"]["restored_path_template"].format(
            experiment_id=primary["experiment_id"],
            case_id=case_id,
            candidate_id=candidate_id,
        )
        row.update(
            {
                "candidate_id": candidate_id,
                "candidate_index": 0,
                "prompt_policy_id": policy_id,
                "prompt_variant_id": variant_id,
                "seed": int(seed),
                "execution_role": role,
                "is_primary_candidate": False,
                "is_prompt_ablation_candidate": True,
                "candidate_selection_policy": design["selection_policy"],
                "execution_action": "pending",
                "restored_path": str(
                    Path(base_config["output"]["restored_directory"]) / Path(relative)
                ).replace("\\", "/"),
                "restored_sha256": "",
                "runtime_seconds": np.nan,
                "gpu_memory_before_bytes": np.nan,
                "gpu_memory_after_bytes": np.nan,
                "gpu_peak_memory_bytes": np.nan,
                "retry_count": 0,
                "attempt_count": 0,
                "configuration_fingerprint": fingerprint,
                "started_at_utc": "",
                "completed_at_utc": "",
                "generator_name": SCRATCH_PROMPT_EXTENSION_NAME,
                "generator_version": SCRATCH_PROMPT_EXTENSION_VERSION,
                "status": "planned",
                "issue": "",
            }
        )
        if variant_id == SCRATCH_PROMPT_VARIANT_ID:
            row["prompt"] = scratch_config["effective_prompt_policy"]["positive_prompt"]
            row["negative_prompt"] = _combined_negative_prompt(
                base_config, scratch_config
            )
            row["prompt_metadata_fields_used"] = json.dumps(
                list(scratch_config["effective_prompt_policy"]["metadata_fields"])
            )
        else:
            row["prompt"] = base_config["prompt_policy"]["generic_prompt"]
            row["negative_prompt"] = base_config["prompt_policy"]["negative_prompt"]
            row["prompt_metadata_fields_used"] = "[]"
        added.append(row)

    generic_role = str(design["generic_extension_role"])
    damage_role = str(design["damage_prompt_role"])
    for case_id in sorted(scratch_ids):
        primary = primary_by_case[case_id]
        for seed in seeds:
            if (case_id, "p00_generic", seed) not in existing:
                add_from_primary(primary, "p00_generic", seed, generic_role)
            add_from_primary(primary, SCRATCH_PROMPT_VARIANT_ID, seed, damage_role)

    added_frame = pd.DataFrame(added, columns=STABLE_DIFFUSION_CANDIDATE_COLUMNS)
    result = pd.concat([result, added_frame], ignore_index=True)
    result["candidate_index"] = result.groupby("case_id", sort=False).cumcount()
    if result["candidate_id"].duplicated().any():
        raise ValueError("Effective Stable Diffusion candidate IDs are not unique.")
    if len(added_frame.loc[added_frame["execution_role"].eq(generic_role)]) != int(
        expected["generic_extension_candidate_count"]
    ):
        raise ValueError("Generic scratch seed-control extension count differs.")
    if len(added_frame.loc[added_frame["execution_role"].eq(damage_role)]) != int(
        expected["damage_prompt_candidate_count"]
    ):
        raise ValueError("Scratch-aware candidate count differs.")
    if len(result) != int(expected["effective_candidate_count"]):
        raise ValueError("Effective candidate count differs from the approved contract.")
    validate_dataframe(result, STABLE_DIFFUSION_CANDIDATES_SCHEMA)
    return result


def select_paired_scratch_matrix(
    candidates: pd.DataFrame, scratch_config: Mapping[str, Any]
) -> pd.DataFrame:
    """Return and strictly validate the formal 400-outcome analysis matrix."""
    design = scratch_config["candidate_design"]
    result = candidates.loc[
        candidates["experiment_id"].eq(str(design["experiment_id"]))
        & candidates["case_id"].astype(str).str.endswith(str(design["case_id_suffix"]))
        & candidates["prompt_variant_id"].isin(design["prompt_variant_ids"])
        & pd.to_numeric(candidates["seed"], errors="coerce").isin(design["seeds"])
    ].copy()
    key = ["case_id", "seed", "prompt_variant_id"]
    if result.duplicated(key).any():
        raise ValueError("Paired scratch matrix contains duplicate case-seed-prompt rows.")
    expected = int(scratch_config["expected"]["paired_outcome_count"])
    if len(result) != expected:
        raise ValueError(f"Expected {expected} paired scratch outcomes, observed {len(result)}.")
    counts = result.groupby(["case_id", "seed"])["prompt_variant_id"].nunique()
    if not counts.eq(len(design["prompt_variant_ids"])).all():
        raise ValueError("Every scratch case-seed pair must contain both prompt arms.")
    return result.sort_values(key, kind="stable").reset_index(drop=True)
