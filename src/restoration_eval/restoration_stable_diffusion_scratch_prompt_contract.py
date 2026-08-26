"""Schema-compatible public facade for the Notebook 11 scratch extension."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .restoration_stable_diffusion_scratch_prompt import (  # noqa: F401
    SCRATCH_PROMPT_CONFIG_SCHEMA_VERSION,
    SCRATCH_PROMPT_EXTENSION_NAME,
    SCRATCH_PROMPT_EXTENSION_VERSION,
    SCRATCH_PROMPT_VARIANT_ID,
    build_effective_candidate_plan,
    build_effective_prompt_ablation_design,
    build_effective_prompt_policy,
    build_effective_stable_diffusion_config,
    load_scratch_prompt_ablation_config as _load_raw_config,
    select_paired_scratch_matrix,
    select_scratch_prompt_cases,
)


def load_scratch_prompt_ablation_config(path: str | Path) -> dict[str, Any]:
    """Load the human-readable contract and map logical roles to schema v1 roles.

    ``stable_diffusion_candidates.v1`` intentionally has only three execution
    role values.  The new experiment therefore records its precise identity via
    ``prompt_variant_id`` and ``candidate_selection_policy`` while mapping its
    logical generation roles onto the compatible prompt/uncertainty families.
    """
    config = copy.deepcopy(_load_raw_config(path))
    design = config["candidate_design"]
    design["logical_execution_roles"] = {
        "generic_extension": design["generic_extension_role"],
        "damage_prompt": design["damage_prompt_role"],
    }
    design["logical_canonical_damage_type"] = design["canonical_damage_type"]
    design["canonical_damage_type"] = "binary_missing_region"
    design["generic_extension_role"] = "uncertainty_extension"
    design["damage_prompt_role"] = "prompt_context"
    return config
