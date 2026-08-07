from __future__ import annotations

import gc
import hashlib
import platform
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from PIL import Image


MODEL_NAME = "stable_diffusion_inpainting"
HF_MODEL_ID = "runwayml/stable-diffusion-inpainting"
ZERO_CONTROL_MASK_TYPE = "zero_control"
RESTORATION_GENERATOR_NAME = "notebook_21_stable_diffusion_restoration"
RESTORATION_GENERATOR_VERSION = "4.2_soft_mask_nonzero_fallback"

DEFAULT_PROMPT_POLICY_ID = "sd_inpaint_prompt_ablation_v1"
GENERIC_PROMPT_VARIANT_ID = "p00_generic"
DEFAULT_MASK_BINARY_THRESHOLD = 128
DEFAULT_FILENAME_HASH_LENGTH = 10
DEFAULT_RESTORED_FILENAME_MAX_STEM_LENGTH = 120

DEFAULT_GENERIC_PROMPT = (
    "restore the damaged or missing area of the painting while preserving the "
    "original composition, colour palette, brushwork, texture, lighting, age, "
    "and surrounding visual context"
)

# Backward-compatible alias for older notebook cells.
DEFAULT_PROMPT = DEFAULT_GENERIC_PROMPT

DEFAULT_NEGATIVE_PROMPT = (
    "modern objects, text, watermark, signature, frame, border, added people, "
    "changed faces, extra objects, oversharpened, cartoon, digital art, "
    "photorealistic replacement, unrealistic texture, harsh seams"
)

DEFAULT_PROMPT_VARIANT_SPECS: list[dict[str, Any]] = [
        {
            "prompt_variant_id": "p00_generic",
            "prompt_template_name": "generic_restoration",
            "variant_family": "generic",
            "is_generic_baseline": True,
            "applies_to_all_cases": True,
            "requires_metadata": False,
            "prompt_template": DEFAULT_GENERIC_PROMPT,
            "uses_artist": False,
            "uses_style_period": False,
            "uses_title": False,
            "uses_category": False,
    },
    {
            "prompt_variant_id": "p01_style_period",
            "prompt_template_name": "style_period_context",
            "variant_family": "contextual",
            "is_generic_baseline": False,
            "applies_to_all_cases": False,
            "requires_metadata": True,
            "prompt_template": (
                "restore the damaged or missing area of this {style_period_clause} "
                "painting while preserving the original composition, colour palette, "
                "brushwork, texture, lighting, age, and surrounding visual context"
        ),
        "uses_artist": False,
        "uses_style_period": True,
        "uses_title": False,
        "uses_category": False,
    },
    {
            "prompt_variant_id": "p02_artist",
            "prompt_template_name": "artist_context",
            "variant_family": "contextual",
            "is_generic_baseline": False,
            "applies_to_all_cases": False,
            "requires_metadata": True,
            "prompt_template": (
                "restore the damaged or missing area of this painting {artist_clause} "
                "while preserving the original composition, colour palette, "
                "brushwork, texture, lighting, age, and surrounding visual context"
        ),
        "uses_artist": True,
        "uses_style_period": False,
        "uses_title": False,
        "uses_category": False,
    },
    {
            "prompt_variant_id": "p03_artist_style_period",
            "prompt_template_name": "artist_style_period_context",
            "variant_family": "contextual",
            "is_generic_baseline": False,
            "applies_to_all_cases": False,
            "requires_metadata": True,
            "prompt_template": (
                "restore the damaged or missing area of this {style_period_clause} "
                "painting {artist_clause} while preserving the original composition, "
                "colour palette, brushwork, texture, lighting, age, and surrounding "
            "visual context"
        ),
        "uses_artist": True,
        "uses_style_period": True,
        "uses_title": False,
        "uses_category": False,
    },
    {
            "prompt_variant_id": "p04_full_context",
            "prompt_template_name": "artwork_full_context",
            "variant_family": "contextual",
            "is_generic_baseline": False,
            "applies_to_all_cases": False,
            "requires_metadata": True,
            "prompt_template": (
                "restore the damaged or missing area of this painting "
                "{artwork_context_clause} while preserving the original composition, "
                "colour palette, brushwork, texture, lighting, age, and surrounding "
            "visual context"
        ),
        "uses_artist": True,
        "uses_style_period": True,
        "uses_title": True,
        "uses_category": True,
    },
]

ARTIST_COLUMNS = ("artist_name", "artist", "creator", "author", "painter")
TITLE_COLUMNS = ("artwork_title", "painting_title", "title", "object_title")
STYLE_PERIOD_COLUMNS = (
    "style_period_summary",
    "style_period",
    "period",
    "art_style",
    "style",
    "movement",
)
CATEGORY_COLUMNS = ("category", "painting_category", "genre", "object_type", "classification")

SOURCE_REQUIRED_COLUMNS = [
    "dataset_name",
    "source_case_key",
    "source_case_id",
    "case_id",
    "painting_id",
    "mask_type",
    "clean_path",
    "damaged_path",
    "mask_path",
]

PROMPT_POLICY_REQUIRED_COLUMNS = [
    "prompt_policy_id",
    "prompt_variant_id",
    "prompt_template_name",
    "variant_family",
    "variant_order",
    "is_generic_baseline",
    "applies_to_all_cases",
    "requires_metadata",
    "prompt_template",
    "negative_prompt",
]

CANDIDATE_REQUIRED_COLUMNS = [
    *SOURCE_REQUIRED_COLUMNS,
    "candidate_id",
    "candidate_index",
    "candidate_seed",
    "restoration_case_id",
    "restored_path",
    "prompt_policy_id",
    "prompt_variant_id",
    "prompt_template_name",
    "prompt",
    "negative_prompt",
    "prompt_metadata_fields_used",
    "prompt_metadata_missing_fields",
    "scheduler_name",
    "num_inference_steps",
    "guidance_scale",
    "strength",
    "inference_size",
    "model_name",
    "hf_model_id",
    "model_revision",
    "precision",
    "zero_control_behavior",
]


@dataclass(frozen=True)
class StableDiffusionInpaintConfig:
    model_name: str = MODEL_NAME
    hf_model_id: str = HF_MODEL_ID
    model_revision: str = "main"
    prompt_policy_id: str = DEFAULT_PROMPT_POLICY_ID
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT
    base_seed: int = 2026
    scheduler_name: str = "pipeline_default"
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    strength: float = 1.0
    inference_size: int = 512
    precision: str = "float16"
    prefer_cuda: bool = True
    enable_attention_slicing: bool = True
    disable_safety_checker: bool = True
    zero_control_mask_type: str = ZERO_CONTROL_MASK_TYPE
    zero_control_behavior: str = "copy_without_inference"
    mask_binary_threshold: int = DEFAULT_MASK_BINARY_THRESHOLD
    preserve_unmasked_pixels: bool = True
    restored_filename_hash_length: int = DEFAULT_FILENAME_HASH_LENGTH
    restored_filename_max_stem_length: int = DEFAULT_RESTORED_FILENAME_MAX_STEM_LENGTH
    max_retries: int = 1
    retry_delay_seconds: float = 2.0
    clear_cuda_cache_every: int = 10


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_directory(path: Path | str) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and np.isnan(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null", "<na>"} else text


def safe_slug(value: Any) -> str:
    text = safe_text(value).lower()
    slug = []
    previous_was_sep = False
    for char in text:
        if char.isalnum():
            slug.append(char)
            previous_was_sep = False
        elif not previous_was_sep:
            slug.append("_")
            previous_was_sep = True
    return "".join(slug).strip("_") or "unknown"


def short_hash(value: Any, *, length: int = DEFAULT_FILENAME_HASH_LENGTH) -> str:
    text = safe_text(value)
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return digest[: max(6, int(length))]


def compact_slug(value: Any, *, max_length: int = 32) -> str:
    slug = safe_slug(value)
    max_length = max(8, int(max_length))
    if len(slug) <= max_length:
        return slug
    return slug[: max_length].rstrip("_")


def compact_dataset_code(dataset_name: Any) -> str:
    dataset_slug = safe_slug(dataset_name)
    mapping = {
        "canonical": "can",
        "main": "main",
        "damage_size_sensitivity": "dsz",
        "mask_robustness": "mrob",
        "synthetic_degradation": "syn",
        "zero_control": "zero",
    }
    return mapping.get(dataset_slug, compact_slug(dataset_slug, max_length=16))


def compact_mask_code(mask_type: Any, source_case_key: Any = "") -> str:
    mask_slug = safe_slug(mask_type)
    source_slug = safe_slug(source_case_key)
    if mask_slug == "zero_control":
        return "zero"
    if mask_slug in {"loss_large", "loss_small", "scratch_thin", "mixed_damage"}:
        return mask_slug

    size_token = ""
    for token in source_slug.split("_"):
        if token.endswith("pct") and token[:-3].isdigit():
            size_token = token
            break
    if size_token and size_token not in mask_slug:
        return compact_slug(f"{mask_slug}_{size_token}", max_length=28)
    return compact_slug(mask_slug, max_length=28)


def compact_restored_filename(
    *,
    dataset_name: Any,
    painting_id: Any,
    mask_type: Any,
    source_case_key: Any,
    prompt_variant_id: Any,
    seed: int,
    model_name: Any,
    max_stem_length: int = DEFAULT_RESTORED_FILENAME_MAX_STEM_LENGTH,
    hash_length: int = DEFAULT_FILENAME_HASH_LENGTH,
) -> tuple[str, str, str]:
    """Return compact candidate/restoration IDs and a git-safe filename."""
    dataset_code = compact_dataset_code(dataset_name)
    painting_slug = compact_slug(painting_id, max_length=18)
    mask_code = compact_mask_code(mask_type, source_case_key)
    prompt_slug = compact_slug(prompt_variant_id, max_length=18)
    model_slug = compact_slug(model_name, max_length=28)
    digest_source = "||".join(
        [
            safe_text(dataset_name),
            safe_text(painting_id),
            safe_text(mask_type),
            safe_text(source_case_key),
            safe_text(prompt_variant_id),
            str(int(seed)),
            safe_text(model_name),
        ]
    )
    digest = short_hash(digest_source, length=hash_length)
    candidate_id = f"sd__{dataset_code}__{painting_slug}__{mask_code}__{prompt_slug}__s{int(seed)}__{digest}"
    restoration_case_id = candidate_id
    stem = f"{candidate_id}__restored_{model_slug}"
    max_stem_length = max(64, int(max_stem_length))
    if len(stem) > max_stem_length:
        prefix_length = max_stem_length - len(digest) - 2
        stem = f"{stem[:prefix_length].rstrip('_')}__{digest}"
    return candidate_id, restoration_case_id, f"{stem}.png"


def json_list_text(values: Iterable[Any]) -> str:
    cleaned = [safe_text(value) for value in values if safe_text(value)]
    return "[" + ", ".join(cleaned) + "]"


def require_columns(df: pd.DataFrame, columns: Iterable[str], *, dataframe_name: str) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"{dataframe_name} is missing required columns: {missing}")


def resolve_path(path_value: Any, *, project_root: Path | str | None = None) -> Path:
    text = safe_text(path_value)
    if not text:
        return Path("")
    path = Path(text)
    if not path.is_absolute() and project_root is not None:
        path = Path(project_root) / path
    return path


def to_storage_path(
    path: Path | str,
    *,
    project_root: Path | str | None = None,
    use_relative_paths: bool = True,
) -> str:
    path = Path(path)
    if use_relative_paths and project_root is not None:
        try:
            return path.relative_to(Path(project_root)).as_posix()
        except ValueError:
            return str(path)
    return str(path)


def sha256_file(path: Path | str, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def first_existing_column(row: pd.Series | Mapping[str, Any], columns: Iterable[str]) -> Any:
    for column in columns:
        if column in row and safe_text(row[column]):
            return row[column]
    return ""


def metadata_value(row: pd.Series | Mapping[str, Any], columns: Iterable[str]) -> str:
    return safe_text(first_existing_column(row, columns))


def metadata_context(row: pd.Series | Mapping[str, Any]) -> dict[str, str]:
    return {
        "artist": metadata_value(row, ARTIST_COLUMNS),
        "title": metadata_value(row, TITLE_COLUMNS),
        "style_period": metadata_value(row, STYLE_PERIOD_COLUMNS),
        "category": metadata_value(row, CATEGORY_COLUMNS),
    }


def style_period_clause(style_period: str) -> str:
    text = safe_text(style_period)
    return text if text else "historical artwork"


def artist_clause(artist: str) -> str:
    text = safe_text(artist)
    return f"by {text}" if text else "with an unknown artist"


def artwork_context_clause(context: Mapping[str, str]) -> str:
    parts: list[str] = []
    if safe_text(context.get("title")):
        parts.append(f"titled {context['title']}")
    if safe_text(context.get("artist")):
        parts.append(f"by {context['artist']}")
    if safe_text(context.get("style_period")):
        parts.append(f"from the {context['style_period']} style or period")
    if safe_text(context.get("category")):
        parts.append(f"categorized as {context['category']}")
    return ", ".join(parts) if parts else "using available artwork context"


def build_stable_diffusion_prompt_policy_df(
    *,
    config: StableDiffusionInpaintConfig,
    prompt_variant_specs: Sequence[Mapping[str, Any]] | None = None,
) -> pd.DataFrame:
    """Return the fixed prompt-ablation policy used by Notebook 21."""
    specs = list(prompt_variant_specs or DEFAULT_PROMPT_VARIANT_SPECS)
    rows: list[dict[str, Any]] = []
    for order, spec in enumerate(specs):
        record = dict(spec)
        metadata_flags = [
            bool(record.get("uses_artist", False)),
            bool(record.get("uses_style_period", False)),
            bool(record.get("uses_title", False)),
            bool(record.get("uses_category", False)),
        ]
        record.setdefault("requires_metadata", any(metadata_flags))
        record.setdefault("applies_to_all_cases", bool(record.get("is_generic_baseline", False)))
        record.update(
            {
                "prompt_policy_id": config.prompt_policy_id,
                "variant_order": int(order),
                "negative_prompt": config.negative_prompt,
                "policy_created_at_utc": utc_now_iso(),
            }
        )
        rows.append(record)

    prompt_policy_df = pd.DataFrame(rows)
    require_columns(
        prompt_policy_df,
        PROMPT_POLICY_REQUIRED_COLUMNS,
        dataframe_name="prompt_policy_df",
    )
    return prompt_policy_df.sort_values("variant_order").reset_index(drop=True)


def render_stable_diffusion_prompt(
    row: pd.Series | Mapping[str, Any],
    prompt_policy_row: pd.Series | Mapping[str, Any],
) -> dict[str, Any]:
    """Render one prompt variant and record which metadata fields were useful."""
    context = metadata_context(row)
    template = safe_text(prompt_policy_row["prompt_template"])
    rendered = template.format(
        artist_clause=artist_clause(context["artist"]),
        style_period_clause=style_period_clause(context["style_period"]),
        artwork_context_clause=artwork_context_clause(context),
    )

    used_fields: list[str] = []
    missing_fields: list[str] = []
    for flag_column, field_name in [
        ("uses_artist", "artist"),
        ("uses_style_period", "style_period"),
        ("uses_title", "title"),
        ("uses_category", "category"),
    ]:
        uses_field = bool(prompt_policy_row.get(flag_column, False))
        if not uses_field:
            continue
        if safe_text(context.get(field_name)):
            used_fields.append(field_name)
        else:
            missing_fields.append(field_name)

    return {
        "prompt": " ".join(rendered.split()),
        "negative_prompt": safe_text(prompt_policy_row["negative_prompt"]),
        "prompt_metadata_fields_used": json_list_text(used_fields),
        "prompt_metadata_missing_fields": json_list_text(missing_fields),
        "prompt_artist_value": context["artist"],
        "prompt_title_value": context["title"],
        "prompt_style_period_value": context["style_period"],
        "prompt_category_value": context["category"],
    }


def standardize_stable_diffusion_source_cases(
    input_df: pd.DataFrame,
    *,
    dataset_name: str,
    source_metadata_path: str | Path = "",
    include_zero_control: bool = True,
    source_case_id_columns: Iterable[str] = (
        "source_case_id",
        "restoration_case_id",
        "case_id",
    ),
) -> pd.DataFrame:
    """Convert one source metadata table to the Notebook 21 source-case schema."""
    if input_df.empty:
        return pd.DataFrame(columns=SOURCE_REQUIRED_COLUMNS)

    rows: list[dict[str, Any]] = []
    for _, row in input_df.iterrows():
        mask_type = safe_text(first_existing_column(row, ["mask_type", "base_mask_type", "degradation_type"]))
        if not include_zero_control and mask_type == ZERO_CONTROL_MASK_TYPE:
            continue

        source_case_id = safe_text(first_existing_column(row, source_case_id_columns))
        case_id = safe_text(first_existing_column(row, ["case_id", "source_case_id_original", "source_case_id"]))
        painting_id = safe_text(row.get("painting_id"))
        dataset_slug = safe_slug(dataset_name)
        source_id = source_case_id or case_id or f"row_{len(rows):05d}"
        source_case_key = f"{dataset_slug}__{safe_slug(source_id)}"

        clean_path = first_existing_column(row, ["clean_path", "clean_image_path", "original_path"])
        damaged_path = first_existing_column(row, ["damaged_path", "degraded_path", "input_path"])
        mask_path = first_existing_column(
            row,
            ["mask_path", "sensitivity_mask_path", "effect_mask_path", "base_mask_path"],
        )

        record = row.to_dict()
        record.update(
            {
                "dataset_name": dataset_name,
                "source_metadata_path": safe_text(source_metadata_path),
                "source_case_key": source_case_key,
                "source_case_id": source_id,
                "source_case_id_original": safe_text(row.get("source_case_id_original")) or case_id,
                "case_id": case_id or source_id,
                "painting_id": painting_id,
                "mask_type": mask_type,
                "clean_path": clean_path,
                "damaged_path": damaged_path,
                "mask_path": mask_path,
            }
        )
        rows.append(record)

    source_df = pd.DataFrame(rows)
    require_columns(source_df, SOURCE_REQUIRED_COLUMNS, dataframe_name="source_df")

    for column in SOURCE_REQUIRED_COLUMNS:
        source_df[column] = source_df[column].map(safe_text)

    source_df["source_row_status"] = np.where(
        source_df[["clean_path", "damaged_path", "mask_path"]].ne("").all(axis=1),
        "ok",
        "missing_required_path",
    )

    duplicated_keys = source_df["source_case_key"].duplicated(keep=False)
    if duplicated_keys.any():
        occurrence = source_df.groupby("source_case_key").cumcount() + 1
        source_df.loc[duplicated_keys, "source_case_key"] = (
            source_df.loc[duplicated_keys, "source_case_key"]
            + "__dup"
            + occurrence.loc[duplicated_keys].astype(str).str.zfill(3)
        )

    sort_columns = [
        column
        for column in ["dataset_name", "painting_id", "mask_type", "case_id", "source_case_key"]
        if column in source_df.columns
    ]
    return source_df.sort_values(sort_columns).reset_index(drop=True)


def select_prompt_ablation_subset(
    source_cases_df: pd.DataFrame,
    *,
    target_source_cases: int = 120,
    min_source_cases: int = 100,
    random_state: int = 2026,
    stratify_columns: Sequence[str] = (
        "dataset_name",
        "mask_type",
        "damage_family",
        "category",
        "style_period_summary",
    ),
) -> pd.DataFrame:
    """Select a deterministic, stratified source subset for contextual prompts."""
    require_columns(source_cases_df, SOURCE_REQUIRED_COLUMNS, dataframe_name="source_cases_df")
    if len(source_cases_df) < min_source_cases:
        raise ValueError(
            f"Not enough source cases for prompt ablation: {len(source_cases_df)} < {min_source_cases}"
        )

    target = min(int(target_source_cases), int(len(source_cases_df)))
    available_strata = [column for column in stratify_columns if column in source_cases_df.columns]
    working_df = source_cases_df.copy().reset_index(drop=True)

    if not available_strata:
        selected_df = working_df.sample(n=target, random_state=random_state)
    else:
        working_df["_prompt_stratum"] = (
            working_df[available_strata]
            .fillna("unknown")
            .astype(str)
            .agg(" | ".join, axis=1)
        )
        strata = working_df["_prompt_stratum"].value_counts().rename_axis("_prompt_stratum").reset_index(name="count")
        strata["quota"] = np.maximum(1, np.floor(strata["count"] / len(working_df) * target).astype(int))

        selected_parts: list[pd.DataFrame] = []
        for _, stratum_row in strata.iterrows():
            stratum_value = stratum_row["_prompt_stratum"]
            quota = int(stratum_row["quota"])
            pool = working_df[working_df["_prompt_stratum"] == stratum_value]
            selected_parts.append(pool.sample(n=min(quota, len(pool)), random_state=random_state))

        selected_df = pd.concat(selected_parts, ignore_index=False).drop_duplicates("source_case_key")
        if len(selected_df) < target:
            remaining_df = working_df[~working_df["source_case_key"].isin(selected_df["source_case_key"])]
            needed = min(target - len(selected_df), len(remaining_df))
            if needed > 0:
                selected_df = pd.concat(
                    [
                        selected_df,
                        remaining_df.sample(n=needed, random_state=random_state + 1),
                    ],
                    ignore_index=False,
                )
        elif len(selected_df) > target:
            selected_df = selected_df.sample(n=target, random_state=random_state + 2)

    selected_df = selected_df.drop(columns=["_prompt_stratum"], errors="ignore").copy()
    selected_df["prompt_ablation_subset"] = True
    selected_df["prompt_ablation_subset_target"] = int(target_source_cases)
    selected_df["prompt_ablation_subset_minimum"] = int(min_source_cases)
    selected_df["prompt_ablation_random_state"] = int(random_state)
    return selected_df.sort_values(["dataset_name", "painting_id", "mask_type", "source_case_key"]).reset_index(drop=True)


def build_stable_diffusion_candidate_manifest(
    source_cases_df: pd.DataFrame,
    *,
    restored_root_dir: Path | str,
    config: StableDiffusionInpaintConfig,
    project_root: Path | str | None = None,
    prompt_policy_df: pd.DataFrame | None = None,
    prompt_subset_cases_df: pd.DataFrame | None = None,
    candidate_seeds: Iterable[int] | None = None,
    generic_prompt_variant_id: str = "p00_generic",
    use_relative_paths: bool = True,
) -> pd.DataFrame:
    """Expand sources into generic all-case plus contextual subset candidates."""
    require_columns(source_cases_df, SOURCE_REQUIRED_COLUMNS, dataframe_name="source_cases_df")

    if prompt_policy_df is None:
        prompt_policy_df = build_stable_diffusion_prompt_policy_df(config=config)
    require_columns(
        prompt_policy_df,
        PROMPT_POLICY_REQUIRED_COLUMNS,
        dataframe_name="prompt_policy_df",
    )

    if candidate_seeds is None:
        candidate_seeds = [config.base_seed]

    prompt_policy_df = prompt_policy_df.sort_values("variant_order").reset_index(drop=True)
    generic_policy_df = prompt_policy_df[prompt_policy_df["prompt_variant_id"] == generic_prompt_variant_id]
    if generic_policy_df.empty:
        raise ValueError(f"Generic prompt variant not found: {generic_prompt_variant_id}")

    subset_keys: set[str] = set()
    if prompt_subset_cases_df is not None and not prompt_subset_cases_df.empty:
        require_columns(prompt_subset_cases_df, ["source_case_key"], dataframe_name="prompt_subset_cases_df")
        subset_keys = set(prompt_subset_cases_df["source_case_key"].astype(str))

    restored_root_dir = ensure_directory(restored_root_dir)
    rows: list[dict[str, Any]] = []
    candidate_index = 0

    for _, row in source_cases_df.iterrows():
        source_key = safe_text(row["source_case_key"])
        source_is_subset = source_key in subset_keys
        policies_for_source = [generic_policy_df.iloc[0]]
        if source_is_subset:
            contextual_rows = prompt_policy_df[prompt_policy_df["prompt_variant_id"] != generic_prompt_variant_id]
            policies_for_source.extend([policy_row for _, policy_row in contextual_rows.iterrows()])

        for policy_row in policies_for_source:
            prompt_render = render_stable_diffusion_prompt(row, policy_row)
            prompt_variant_id = safe_text(policy_row["prompt_variant_id"])
            prompt_variant_slug = safe_slug(prompt_variant_id)

            for seed in candidate_seeds:
                candidate_index += 1
                dataset_slug = safe_slug(row["dataset_name"])
                candidate_id, restoration_case_id, restored_filename = compact_restored_filename(
                    dataset_name=row["dataset_name"],
                    painting_id=row.get("painting_id", ""),
                    mask_type=row.get("mask_type", ""),
                    source_case_key=row.get("source_case_key", ""),
                    prompt_variant_id=prompt_variant_id,
                    seed=int(seed),
                    model_name=config.model_name,
                    max_stem_length=int(config.restored_filename_max_stem_length),
                    hash_length=int(config.restored_filename_hash_length),
                )
                restored_path = restored_root_dir / dataset_slug / prompt_variant_slug / restored_filename

                candidate_row = row.to_dict()
                candidate_row.update(
                    {
                        "candidate_id": candidate_id,
                        "candidate_index": int(candidate_index),
                        "candidate_seed": int(seed),
                        "restoration_case_id": restoration_case_id,
                        "restored_filename": restored_filename,
                        "restored_path": to_storage_path(
                            restored_path,
                            project_root=project_root,
                            use_relative_paths=use_relative_paths,
                        ),
                        "prompt_ablation_subset": bool(source_is_subset),
                        "model_name": config.model_name,
                        "restoration_method": "stable_diffusion_inpainting",
                        "hf_model_id": config.hf_model_id,
                        "model_revision": config.model_revision,
                        "prompt_policy_id": safe_text(policy_row["prompt_policy_id"]),
                        "prompt_variant_id": prompt_variant_id,
                        "prompt_template_name": safe_text(policy_row["prompt_template_name"]),
                        "prompt_variant_family": safe_text(policy_row.get("variant_family")),
                        "prompt_variant_order": int(policy_row.get("variant_order", 0)),
                        "prompt_template": safe_text(policy_row["prompt_template"]),
                        **prompt_render,
                        "scheduler_name": config.scheduler_name,
                        "num_inference_steps": int(config.num_inference_steps),
                        "guidance_scale": float(config.guidance_scale),
                        "strength": float(config.strength),
                        "inference_size": int(config.inference_size),
                        "precision": config.precision,
                        "mask_binary_threshold": int(config.mask_binary_threshold),
                        "preserve_unmasked_pixels": bool(config.preserve_unmasked_pixels),
                        "zero_control_behavior": config.zero_control_behavior,
                        "restoration_generator_name": RESTORATION_GENERATOR_NAME,
                        "restoration_generator_version": RESTORATION_GENERATOR_VERSION,
                        "candidate_created_at_utc": utc_now_iso(),
                    }
                )
                rows.append(candidate_row)

    candidate_df = pd.DataFrame(rows)
    require_columns(candidate_df, CANDIDATE_REQUIRED_COLUMNS, dataframe_name="candidate_df")
    return candidate_df.sort_values(
        ["dataset_name", "painting_id", "mask_type", "source_case_key", "prompt_variant_order", "candidate_seed"]
    ).reset_index(drop=True)


def get_device(prefer_cuda: bool = True) -> str:
    import torch

    if prefer_cuda and torch.cuda.is_available():
        return "cuda"
    return "cpu"


def torch_dtype_from_precision(precision: str, *, device: str):
    import torch

    precision = safe_text(precision).lower()
    if precision in {"float16", "fp16", "half"} and device == "cuda":
        return torch.float16
    if precision in {"bfloat16", "bf16"} and device == "cuda":
        return torch.bfloat16
    return torch.float32


def torch_memory_snapshot(*, device: str) -> dict[str, Any]:
    if device != "cuda":
        return {
            "cuda_memory_allocated_bytes": np.nan,
            "cuda_memory_reserved_bytes": np.nan,
            "cuda_max_memory_allocated_bytes": np.nan,
        }

    import torch

    return {
        "cuda_memory_allocated_bytes": int(torch.cuda.memory_allocated()),
        "cuda_memory_reserved_bytes": int(torch.cuda.memory_reserved()),
        "cuda_max_memory_allocated_bytes": int(torch.cuda.max_memory_allocated()),
    }


def runtime_environment_info(*, device: str) -> dict[str, Any]:
    import torch

    info = {
        "python_version": platform.python_version(),
        "operating_system": platform.platform(),
        "processor": platform.processor(),
        "torch_version": torch.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_device_count": int(torch.cuda.device_count()) if torch.cuda.is_available() else 0,
        "cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "",
        "execution_device": device,
    }
    try:
        import diffusers

        info["diffusers_version"] = diffusers.__version__
    except Exception:
        info["diffusers_version"] = ""
    return info


def load_stable_diffusion_inpaint_pipeline(
    *,
    config: StableDiffusionInpaintConfig,
    device: str,
):
    """Load the diffusers inpainting pipeline with audit-friendly defaults."""
    from diffusers import StableDiffusionInpaintPipeline

    torch_dtype = torch_dtype_from_precision(config.precision, device=device)
    revision = None if config.model_revision in {"", "main"} else config.model_revision

    pipe = StableDiffusionInpaintPipeline.from_pretrained(
        config.hf_model_id,
        revision=revision,
        torch_dtype=torch_dtype,
    )

    if config.disable_safety_checker:
        pipe.safety_checker = None
        pipe.requires_safety_checker = False

    if config.enable_attention_slicing:
        pipe.enable_attention_slicing()

    pipe = pipe.to(device)
    pipe.set_progress_bar_config(disable=True)
    return pipe


def _load_rgb_image(path: Path) -> Image.Image:
    if not path.exists():
        raise FileNotFoundError(f"Missing RGB image file: {path}")
    return Image.open(path).convert("RGB")


def _load_mask_image(path: Path) -> Image.Image:
    if not path.exists():
        raise FileNotFoundError(f"Missing mask image file: {path}")
    return Image.open(path).convert("L")


def mask_effective_binary_array(
    mask_image: Image.Image,
    *,
    threshold: int = DEFAULT_MASK_BINARY_THRESHOLD,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Return the effective SD binary mask without modifying the stored mask file.

    Most masks are hard masks and pass the configured threshold directly. Some
    synthetic water-stain masks are soft effect masks whose maximum value can sit
    below 128; for those, thresholding would create an empty inpainting mask even
    though the mask has real non-zero support. In that specific case, use the
    non-zero support as the effective mask and record the policy in audit output.
    """
    threshold = int(threshold)
    mask_array = np.asarray(mask_image.convert("L"))
    thresholded_mask = mask_array >= threshold
    raw_nonzero_mask = mask_array > 0

    raw_nonzero_pixel_count = int(raw_nonzero_mask.sum())
    thresholded_pixel_count = int(thresholded_mask.sum())
    if thresholded_pixel_count == 0 and raw_nonzero_pixel_count > 0:
        effective_mask = raw_nonzero_mask
        threshold_policy = "fallback_nonzero_support_from_soft_mask"
    else:
        effective_mask = thresholded_mask
        threshold_policy = "configured_threshold"

    stats = {
        "mask_raw_nonzero_pixel_count": raw_nonzero_pixel_count,
        "mask_thresholded_pixel_count": thresholded_pixel_count,
        "effective_mask_pixel_count": int(effective_mask.sum()),
        "effective_mask_threshold_policy": threshold_policy,
        "mask_gray_min": int(mask_array.min()) if mask_array.size else 0,
        "mask_gray_max": int(mask_array.max()) if mask_array.size else 0,
        "mask_gray_unique_count": int(np.unique(mask_array).size) if mask_array.size else 0,
    }
    return effective_mask, stats


def binarize_mask_image(mask_image: Image.Image, *, threshold: int = DEFAULT_MASK_BINARY_THRESHOLD) -> Image.Image:
    effective_mask, _ = mask_effective_binary_array(mask_image, threshold=int(threshold))
    return Image.fromarray((effective_mask.astype(np.uint8) * 255), mode="L")


def prepare_inpaint_inputs(
    damaged_path: Path,
    mask_path: Path,
    *,
    inference_size: int,
    mask_binary_threshold: int = DEFAULT_MASK_BINARY_THRESHOLD,
    return_stats: bool = False,
) -> tuple[Image.Image, Image.Image, tuple[int, int]] | tuple[Image.Image, Image.Image, tuple[int, int], dict[str, Any]]:
    damaged_image = _load_rgb_image(damaged_path)
    mask_image = _load_mask_image(mask_path)
    original_size = damaged_image.size

    damaged_resized = damaged_image.resize(
        (int(inference_size), int(inference_size)),
        resample=Image.Resampling.LANCZOS,
    )
    mask_resized = mask_image.resize(
        (int(inference_size), int(inference_size)),
        resample=Image.Resampling.NEAREST,
    )
    mask_resized, resized_mask_stats = binarize_mask_image_with_stats(
        mask_resized,
        threshold=int(mask_binary_threshold),
    )
    stats = {
        f"inference_{key}": value for key, value in resized_mask_stats.items()
    }
    if return_stats:
        return damaged_resized, mask_resized, original_size, stats
    return damaged_resized, mask_resized, original_size


def binarize_mask_image_with_stats(
    mask_image: Image.Image,
    *,
    threshold: int = DEFAULT_MASK_BINARY_THRESHOLD,
) -> tuple[Image.Image, dict[str, Any]]:
    effective_mask, stats = mask_effective_binary_array(mask_image, threshold=int(threshold))
    return Image.fromarray((effective_mask.astype(np.uint8) * 255), mode="L"), stats


def composite_generated_with_damaged(
    *,
    generated_image: Image.Image,
    damaged_path: Path,
    mask_path: Path,
    mask_binary_threshold: int = DEFAULT_MASK_BINARY_THRESHOLD,
    return_stats: bool = False,
) -> Image.Image | tuple[Image.Image, dict[str, Any]]:
    damaged_image = _load_rgb_image(damaged_path)
    mask_image = _load_mask_image(mask_path)
    original_size = damaged_image.size

    generated_image = generated_image.convert("RGB")
    if generated_image.size != original_size:
        generated_image = generated_image.resize(
            original_size,
            resample=Image.Resampling.LANCZOS,
        )

    if mask_image.size != original_size:
        mask_image = mask_image.resize(
            original_size,
            resample=Image.Resampling.NEAREST,
        )
    mask_binary, composite_mask_stats = binarize_mask_image_with_stats(
        mask_image,
        threshold=int(mask_binary_threshold),
    )
    restored_image = Image.composite(generated_image, damaged_image, mask_binary)
    stats = {
        f"composite_{key}": value for key, value in composite_mask_stats.items()
    }
    if return_stats:
        return restored_image, stats
    return restored_image


def validate_mask_composited_image(
    *,
    damaged_path: Path,
    mask_path: Path,
    restored_path: Path,
    mask_binary_threshold: int = DEFAULT_MASK_BINARY_THRESHOLD,
) -> dict[str, Any]:
    """Verify conservation-style compositing invariants for one saved output."""
    with Image.open(damaged_path) as damaged_image:
        damaged_array = np.asarray(damaged_image.convert("RGB"))
    with Image.open(mask_path) as mask_image:
        mask_image = mask_image.convert("L")
        if mask_image.size != (damaged_array.shape[1], damaged_array.shape[0]):
            mask_image = mask_image.resize(
                (damaged_array.shape[1], damaged_array.shape[0]),
                resample=Image.Resampling.NEAREST,
            )
        mask_binary, validation_mask_stats = binarize_mask_image_with_stats(
            mask_image,
            threshold=int(mask_binary_threshold),
        )
        mask_array = np.asarray(mask_binary) > 0
    with Image.open(restored_path) as restored_image:
        restored_array = np.asarray(restored_image.convert("RGB"))

    if damaged_array.shape != restored_array.shape:
        return {
            "mask_composite_validation_passed": False,
            "mask_composite_validation_issue": (
                f"Shape mismatch damaged={damaged_array.shape}, restored={restored_array.shape}"
            ),
        }

    diff = np.abs(restored_array.astype(np.int16) - damaged_array.astype(np.int16))
    mask_pixel_count = int(mask_array.sum())
    outside_mask = ~mask_array
    outside_mask_pixel_count = int(outside_mask.sum())

    inside_mask_max_abs_diff = 0.0
    outside_mask_max_abs_diff = 0.0
    inside_mask_changed = False
    outside_mask_exact_match = True

    if mask_pixel_count > 0:
        inside_diff = diff[mask_array]
        inside_mask_max_abs_diff = float(inside_diff.max())
        inside_mask_changed = bool(inside_mask_max_abs_diff > 0.0)

    if outside_mask_pixel_count > 0:
        outside_diff = diff[outside_mask]
        outside_mask_max_abs_diff = float(outside_diff.max())
        outside_mask_exact_match = bool(outside_mask_max_abs_diff == 0.0)

    validation_passed = bool(inside_mask_changed) and bool(outside_mask_exact_match)
    if validation_passed:
        issue = ""
    elif not outside_mask_exact_match:
        issue = "Model output changed pixels outside the binary mask."
    else:
        issue = "Model output did not change any pixels inside the binary mask."

    return {
        "mask_composite_validation_passed": bool(validation_passed),
        "mask_composite_validation_issue": issue,
        **validation_mask_stats,
        "mask_pixel_count": int(mask_pixel_count),
        "outside_mask_pixel_count": int(outside_mask_pixel_count),
        "inside_mask_changed": bool(inside_mask_changed),
        "inside_mask_max_abs_diff": float(inside_mask_max_abs_diff),
        "outside_mask_exact_match": bool(outside_mask_exact_match),
        "outside_mask_max_abs_diff": float(outside_mask_max_abs_diff),
    }


def _copy_image(source_path: Path, destination_path: Path) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_path)


def run_stable_diffusion_candidate(
    row: pd.Series,
    *,
    pipe: Any,
    config: StableDiffusionInpaintConfig,
    project_root: Path | str | None = None,
    device: str,
    use_relative_paths: bool = True,
) -> dict[str, Any]:
    """Run or copy one candidate row and return a complete audit record."""
    import torch

    require_columns(pd.DataFrame([row]), CANDIDATE_REQUIRED_COLUMNS, dataframe_name="candidate_row")

    output_row = row.to_dict()
    restored_path = resolve_path(row["restored_path"], project_root=project_root)
    damaged_path = resolve_path(row["damaged_path"], project_root=project_root)
    mask_path = resolve_path(row["mask_path"], project_root=project_root)

    mask_type = safe_text(row["mask_type"])
    is_zero_control = mask_type == config.zero_control_mask_type
    should_copy_zero_control = is_zero_control and config.zero_control_behavior != "model_inference"
    start_time = time.perf_counter()
    started_at_utc = utc_now_iso()
    before_memory = torch_memory_snapshot(device=device)

    status = "error"
    issue = ""
    inference_mode = "model_inference"
    retry_count = 0
    effective_candidate_seed = int(row.get("effective_candidate_seed", row["candidate_seed"]))
    mask_composite_stats: dict[str, Any] = {}

    try:
        if should_copy_zero_control:
            inference_mode = "copied_zero_control"
            _copy_image(damaged_path, restored_path)
        else:
            if pipe is None:
                raise ValueError("Stable Diffusion pipeline is required for model inference rows.")

            damaged_resized, mask_resized, original_size, inference_mask_stats = prepare_inpaint_inputs(
                damaged_path,
                mask_path,
                inference_size=int(row["inference_size"]),
                mask_binary_threshold=int(row.get("mask_binary_threshold", config.mask_binary_threshold)),
                return_stats=True,
            )
            mask_composite_stats.update(inference_mask_stats)
            generator = torch.Generator(device=device).manual_seed(int(effective_candidate_seed))

            with torch.inference_mode():
                result = pipe(
                    prompt=safe_text(row["prompt"]),
                    negative_prompt=safe_text(row["negative_prompt"]),
                    image=damaged_resized,
                    mask_image=mask_resized,
                    num_inference_steps=int(row["num_inference_steps"]),
                    guidance_scale=float(row["guidance_scale"]),
                    strength=float(row["strength"]),
                    generator=generator,
                )

            generated_image = result.images[0].convert("RGB")
            if config.preserve_unmasked_pixels:
                restored_image, composite_mask_stats = composite_generated_with_damaged(
                    generated_image=generated_image,
                    damaged_path=damaged_path,
                    mask_path=mask_path,
                    mask_binary_threshold=int(row.get("mask_binary_threshold", config.mask_binary_threshold)),
                    return_stats=True,
                )
                mask_composite_stats.update(composite_mask_stats)
            else:
                restored_image = generated_image
            if restored_image.size != original_size:
                restored_image = restored_image.resize(
                    original_size,
                    resample=Image.Resampling.LANCZOS,
                )
            restored_path.parent.mkdir(parents=True, exist_ok=True)
            restored_image.save(restored_path)

            if config.preserve_unmasked_pixels:
                validation_mask_stats = validate_mask_composited_image(
                    damaged_path=damaged_path,
                    mask_path=mask_path,
                    restored_path=restored_path,
                    mask_binary_threshold=int(row.get("mask_binary_threshold", config.mask_binary_threshold)),
                )
                mask_composite_stats = {
                    **inference_mask_stats,
                    **mask_composite_stats,
                    **validation_mask_stats,
                }
                if not bool(mask_composite_stats.get("mask_composite_validation_passed", False)):
                    raise RuntimeError(mask_composite_stats.get("mask_composite_validation_issue", "Mask-composite validation failed."))

        status = "ok"
        issue = "zero_control copied without model inference" if should_copy_zero_control else ""
    except Exception as error:
        issue = repr(error)

    runtime_seconds = time.perf_counter() - start_time
    completed_at_utc = utc_now_iso()
    after_memory = torch_memory_snapshot(device=device)
    output_written = restored_path.is_file()

    restored_width = np.nan
    restored_height = np.nan
    restored_mode = ""
    restored_sha256 = ""
    if output_written:
        with Image.open(restored_path) as image:
            restored_width, restored_height = image.size
            restored_mode = image.mode
        restored_sha256 = sha256_file(restored_path)

    output_row.update(
        {
            "inference_mode": inference_mode,
            "execution_device": device,
            "execution_backend": "diffusers",
            "scheduler_class": pipe.scheduler.__class__.__name__ if pipe is not None else "",
            "retry_count": int(retry_count),
            "effective_candidate_seed": int(effective_candidate_seed),
            "runtime_seconds": float(runtime_seconds),
            "started_at_utc": started_at_utc,
            "completed_at_utc": completed_at_utc,
            "output_written": bool(output_written),
            "restored_path": to_storage_path(
                restored_path,
                project_root=project_root,
                use_relative_paths=use_relative_paths,
            ),
            "restored_sha256": restored_sha256,
            "restored_width": restored_width,
            "restored_height": restored_height,
            "restored_mode": restored_mode,
            "mask_binary_threshold": int(row.get("mask_binary_threshold", config.mask_binary_threshold)),
            "preserve_unmasked_pixels": bool(config.preserve_unmasked_pixels),
            "restoration_generator_name": RESTORATION_GENERATOR_NAME,
            "restoration_generator_version": RESTORATION_GENERATOR_VERSION,
            "status": status,
            "issue": issue,
            **mask_composite_stats,
            **{f"before_{key}": value for key, value in before_memory.items()},
            **{f"after_{key}": value for key, value in after_memory.items()},
            **runtime_environment_info(device=device),
        }
    )
    return output_row


def run_stable_diffusion_candidates(
    candidate_df: pd.DataFrame,
    *,
    restored_root_dir: Path | str,
    config: StableDiffusionInpaintConfig,
    project_root: Path | str | None = None,
    pipe: Any | None = None,
    device: str | None = None,
    use_relative_paths: bool = True,
    resume_existing: bool = True,
    progress_every: int = 10,
) -> dict[str, Any]:
    """Run a candidate manifest with retries and resumable output checks."""
    import torch

    require_columns(candidate_df, CANDIDATE_REQUIRED_COLUMNS, dataframe_name="candidate_df")
    ensure_directory(restored_root_dir)

    if device is None:
        device = get_device(prefer_cuda=config.prefer_cuda)

    owns_pipe = pipe is None
    model_rows_df = candidate_df[
        ~(
            (candidate_df["mask_type"].astype(str) == config.zero_control_mask_type)
            & (config.zero_control_behavior != "model_inference")
        )
    ]
    needs_model = bool(len(model_rows_df) > 0)
    if pipe is None and needs_model:
        pipe = load_stable_diffusion_inpaint_pipeline(config=config, device=device)

    output_rows: list[dict[str, Any]] = []
    run_started = utc_now_iso()
    start_time = time.perf_counter()

    for index, (_, row) in enumerate(candidate_df.iterrows(), start=1):
        if progress_every and (index == 1 or index % progress_every == 0 or index == len(candidate_df)):
            print(f"Stable Diffusion candidate {index}/{len(candidate_df)}: {row['restoration_case_id']}")

        restored_path = resolve_path(row["restored_path"], project_root=project_root)
        if resume_existing and restored_path.is_file():
            with Image.open(restored_path) as image:
                width, height = image.size
                mode = image.mode
            resumed_output = row.to_dict()
            resumed_output.update(
                {
                    "inference_mode": "resumed_existing_output",
                    "execution_device": device,
                    "execution_backend": "diffusers",
                    "scheduler_class": pipe.scheduler.__class__.__name__ if pipe is not None else "",
                    "retry_count": 0,
                    "attempt_count": 0,
                    "runtime_seconds": 0.0,
                    "started_at_utc": utc_now_iso(),
                    "completed_at_utc": utc_now_iso(),
                    "output_written": True,
                    "restored_width": width,
                    "restored_height": height,
                    "restored_mode": mode,
                    "restored_sha256": sha256_file(restored_path),
                    "restoration_generator_name": RESTORATION_GENERATOR_NAME,
                    "restoration_generator_version": RESTORATION_GENERATOR_VERSION,
                    "status": "ok",
                    "issue": "resumed existing output",
                    **runtime_environment_info(device=device),
                }
            )
            output_rows.append(resumed_output)
            continue

        last_output: dict[str, Any] | None = None
        for attempt_index in range(1, int(config.max_retries) + 2):
            attempt_row = row.copy()
            attempt_row["effective_candidate_seed"] = int(row["candidate_seed"]) + int(attempt_index - 1)
            last_output = run_stable_diffusion_candidate(
                attempt_row,
                pipe=pipe,
                config=config,
                project_root=project_root,
                device=device,
                use_relative_paths=use_relative_paths,
            )
            last_output["attempt_count"] = int(attempt_index)
            last_output["retry_count"] = int(attempt_index - 1)
            if last_output.get("status") == "ok":
                break
            if attempt_index <= int(config.max_retries):
                time.sleep(float(config.retry_delay_seconds))

        output_rows.append(last_output or row.to_dict())

        if device == "cuda" and config.clear_cuda_cache_every and index % int(config.clear_cuda_cache_every) == 0:
            torch.cuda.empty_cache()

    total_runtime_seconds = time.perf_counter() - start_time
    if owns_pipe and pipe is not None:
        del pipe
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()

    restoration_metadata_df = pd.DataFrame(output_rows)
    run_info = {
        **asdict(config),
        "restoration_generator_name": RESTORATION_GENERATOR_NAME,
        "restoration_generator_version": RESTORATION_GENERATOR_VERSION,
        "run_started_at_utc": run_started,
        "run_completed_at_utc": utc_now_iso(),
        "total_runtime_seconds": float(total_runtime_seconds),
        "input_candidates": int(len(candidate_df)),
        "output_rows": int(len(restoration_metadata_df)),
        "successful_rows": int((restoration_metadata_df.get("status", "") == "ok").sum()),
        "error_rows": int((restoration_metadata_df.get("status", "") != "ok").sum()),
        "device_effective": device,
        "prompt_variant_counts": restoration_metadata_df.get(
            "prompt_variant_id",
            pd.Series(dtype=object),
        ).value_counts(dropna=False).to_dict(),
    }
    return {"restoration_metadata_df": restoration_metadata_df, "run_info": run_info}


def validate_stable_diffusion_restoration_outputs(
    restoration_metadata_df: pd.DataFrame,
    *,
    project_root: Path | str | None = None,
    expected_size: tuple[int, int] | None = None,
    zero_control_mask_type: str = ZERO_CONTROL_MASK_TYPE,
    zero_control_behavior: str = "copy_without_inference",
    mask_binary_threshold: int = DEFAULT_MASK_BINARY_THRESHOLD,
    progress_every: int = 25,
) -> pd.DataFrame:
    require_columns(
        restoration_metadata_df,
        [
            "restoration_case_id",
            "candidate_id",
            "prompt_variant_id",
            "case_id",
            "mask_type",
            "damaged_path",
            "mask_path",
            "restored_path",
            "status",
        ],
        dataframe_name="restoration_metadata_df",
    )

    validation_rows: list[dict[str, Any]] = []
    for index, (_, row) in enumerate(restoration_metadata_df.iterrows(), start=1):
        if progress_every and (index == 1 or index % progress_every == 0 or index == len(restoration_metadata_df)):
            print(f"Validating Stable Diffusion output {index}/{len(restoration_metadata_df)}")

        damaged_path = resolve_path(row["damaged_path"], project_root=project_root)
        mask_path = resolve_path(row["mask_path"], project_root=project_root)
        restored_path = resolve_path(row["restored_path"], project_root=project_root)
        mask_type = safe_text(row["mask_type"])

        damaged_exists = damaged_path.is_file()
        mask_exists = mask_path.is_file()
        restored_exists = restored_path.is_file()
        validation_passed = False
        validation_issue = ""
        restored_width = np.nan
        restored_height = np.nan
        restored_mode = ""
        exact_match_to_damaged = np.nan
        changed_from_damaged = np.nan
        mean_abs_diff = np.nan
        max_abs_diff = np.nan
        mask_pixel_count = np.nan
        outside_mask_pixel_count = np.nan
        inside_mask_mean_abs_diff = np.nan
        inside_mask_max_abs_diff = np.nan
        outside_mask_mean_abs_diff = np.nan
        outside_mask_max_abs_diff = np.nan
        outside_mask_exact_match = np.nan
        inside_mask_changed = np.nan
        validation_mask_stats = {
            "mask_raw_nonzero_pixel_count": np.nan,
            "mask_thresholded_pixel_count": np.nan,
            "effective_mask_pixel_count": np.nan,
            "effective_mask_threshold_policy": "",
            "mask_gray_min": np.nan,
            "mask_gray_max": np.nan,
            "mask_gray_unique_count": np.nan,
        }

        if not damaged_exists:
            validation_issue = f"Missing damaged input: {damaged_path}"
        elif not mask_exists:
            validation_issue = f"Missing mask input: {mask_path}"
        elif not restored_exists:
            validation_issue = f"Missing restored output: {restored_path}"
        else:
            with Image.open(damaged_path) as damaged_image:
                damaged_array = np.asarray(damaged_image.convert("RGB"))
            with Image.open(mask_path) as mask_image:
                mask_image = mask_image.convert("L")
                if mask_image.size != (damaged_array.shape[1], damaged_array.shape[0]):
                    mask_image = mask_image.resize(
                        (damaged_array.shape[1], damaged_array.shape[0]),
                        resample=Image.Resampling.NEAREST,
                )
                row_threshold = int(row.get("mask_binary_threshold", mask_binary_threshold))
                mask_binary, validation_mask_stats = binarize_mask_image_with_stats(
                    mask_image,
                    threshold=row_threshold,
                )
                mask_array = np.asarray(mask_binary) > 0
            with Image.open(restored_path) as restored_image:
                restored_width, restored_height = restored_image.size
                restored_mode = restored_image.mode
                restored_array = np.asarray(restored_image.convert("RGB"))

            if damaged_array.shape != restored_array.shape:
                validation_issue = f"Shape mismatch damaged={damaged_array.shape}, restored={restored_array.shape}"
            elif expected_size is not None and (restored_width, restored_height) != expected_size:
                validation_issue = f"Unexpected restored size {(restored_width, restored_height)}; expected {expected_size}"
            else:
                diff = np.abs(restored_array.astype(np.int16) - damaged_array.astype(np.int16))
                max_abs_diff = float(diff.max())
                mean_abs_diff = float(diff.mean())
                exact_match_to_damaged = bool(max_abs_diff == 0.0)
                changed_from_damaged = bool(max_abs_diff > 0.0)
                mask_pixel_count = int(mask_array.sum())
                outside_mask = ~mask_array
                outside_mask_pixel_count = int(outside_mask.sum())
                if mask_pixel_count > 0:
                    inside_diff = diff[mask_array]
                    inside_mask_mean_abs_diff = float(inside_diff.mean())
                    inside_mask_max_abs_diff = float(inside_diff.max())
                    inside_mask_changed = bool(inside_mask_max_abs_diff > 0.0)
                else:
                    inside_mask_changed = False
                if outside_mask_pixel_count > 0:
                    outside_diff = diff[outside_mask]
                    outside_mask_mean_abs_diff = float(outside_diff.mean())
                    outside_mask_max_abs_diff = float(outside_diff.max())
                    outside_mask_exact_match = bool(outside_mask_max_abs_diff == 0.0)
                else:
                    outside_mask_exact_match = True

                if mask_type == zero_control_mask_type and zero_control_behavior != "model_inference":
                    validation_passed = exact_match_to_damaged
                    validation_issue = "" if validation_passed else "Copied zero-control output differs from damaged input."
                else:
                    validation_passed = bool(inside_mask_changed) and bool(outside_mask_exact_match)
                    if validation_passed:
                        validation_issue = ""
                    elif not bool(outside_mask_exact_match):
                        validation_issue = "Model output changed pixels outside the binary mask."
                    else:
                        validation_issue = "Model output did not change any pixels inside the binary mask."

        validation_rows.append(
            {
                "restoration_case_id": row["restoration_case_id"],
                "candidate_id": row.get("candidate_id", ""),
                "prompt_policy_id": row.get("prompt_policy_id", ""),
                "prompt_variant_id": row.get("prompt_variant_id", ""),
                "prompt_ablation_subset": row.get("prompt_ablation_subset", False),
                "dataset_name": row.get("dataset_name", ""),
                "source_case_key": row.get("source_case_key", ""),
                "source_case_id": row.get("source_case_id", ""),
                "case_id": row["case_id"],
                "painting_id": row.get("painting_id", ""),
                "mask_type": mask_type,
                "status": row.get("status", ""),
                "damaged_exists": bool(damaged_exists),
                "mask_exists": bool(mask_exists),
                "restored_exists": bool(restored_exists),
                "restored_width": restored_width,
                "restored_height": restored_height,
                "restored_mode": restored_mode,
                "mask_binary_threshold": int(row.get("mask_binary_threshold", mask_binary_threshold)),
                **validation_mask_stats,
                "mask_pixel_count": mask_pixel_count,
                "outside_mask_pixel_count": outside_mask_pixel_count,
                "exact_match_to_damaged": exact_match_to_damaged,
                "changed_from_damaged": changed_from_damaged,
                "mean_abs_diff": mean_abs_diff,
                "max_abs_diff": max_abs_diff,
                "inside_mask_changed": inside_mask_changed,
                "inside_mask_mean_abs_diff": inside_mask_mean_abs_diff,
                "inside_mask_max_abs_diff": inside_mask_max_abs_diff,
                "outside_mask_exact_match": outside_mask_exact_match,
                "outside_mask_mean_abs_diff": outside_mask_mean_abs_diff,
                "outside_mask_max_abs_diff": outside_mask_max_abs_diff,
                "validation_passed": bool(validation_passed),
                "validation_issue": validation_issue,
            }
        )

    return pd.DataFrame(validation_rows)


def summarize_stable_diffusion_restoration_metadata(restoration_metadata_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if restoration_metadata_df.empty:
        empty = pd.DataFrame()
        return {
            "overview_df": empty,
            "by_dataset_df": empty,
            "by_dataset_mask_df": empty,
            "by_prompt_variant_df": empty,
            "by_inference_mode_df": empty,
        }

    status = restoration_metadata_df.get("status", pd.Series(index=restoration_metadata_df.index, dtype=object)).astype(str)
    overview_df = pd.DataFrame(
        [
            {"item": "total_rows", "value": int(len(restoration_metadata_df))},
            {
                "item": "unique_source_cases",
                "value": int(restoration_metadata_df["source_case_key"].nunique())
                if "source_case_key" in restoration_metadata_df
                else np.nan,
            },
            {
                "item": "unique_candidates",
                "value": int(restoration_metadata_df["candidate_id"].nunique())
                if "candidate_id" in restoration_metadata_df
                else np.nan,
            },
            {"item": "successful_rows", "value": int(status.eq("ok").sum())},
            {"item": "error_rows", "value": int((~status.eq("ok")).sum())},
            {
                "item": "mean_runtime_seconds",
                "value": float(pd.to_numeric(restoration_metadata_df.get("runtime_seconds"), errors="coerce").mean()),
            },
        ]
    )

    def grouped_summary(group_columns: list[str]) -> pd.DataFrame:
        available = [column for column in group_columns if column in restoration_metadata_df.columns]
        if not available:
            return pd.DataFrame()
        return (
            restoration_metadata_df.groupby(available, dropna=False)
            .agg(
                candidates=("restoration_case_id", "count"),
                source_cases=("source_case_key", "nunique"),
                successful_candidates=("status", lambda values: int((values.astype(str) == "ok").sum())),
                error_candidates=("status", lambda values: int((values.astype(str) != "ok").sum())),
                mean_runtime_seconds=("runtime_seconds", lambda values: pd.to_numeric(values, errors="coerce").mean()),
                median_runtime_seconds=("runtime_seconds", lambda values: pd.to_numeric(values, errors="coerce").median()),
            )
            .reset_index()
        )

    return {
        "overview_df": overview_df,
        "by_dataset_df": grouped_summary(["dataset_name"]),
        "by_dataset_mask_df": grouped_summary(["dataset_name", "mask_type"]),
        "by_prompt_variant_df": grouped_summary(["prompt_variant_id"]),
        "by_inference_mode_df": grouped_summary(["inference_mode"]),
    }


__all__ = [
    "MODEL_NAME",
    "HF_MODEL_ID",
    "ZERO_CONTROL_MASK_TYPE",
    "RESTORATION_GENERATOR_NAME",
    "RESTORATION_GENERATOR_VERSION",
    "DEFAULT_PROMPT_POLICY_ID",
    "GENERIC_PROMPT_VARIANT_ID",
    "DEFAULT_MASK_BINARY_THRESHOLD",
    "DEFAULT_FILENAME_HASH_LENGTH",
    "DEFAULT_RESTORED_FILENAME_MAX_STEM_LENGTH",
    "DEFAULT_PROMPT",
    "DEFAULT_GENERIC_PROMPT",
    "DEFAULT_NEGATIVE_PROMPT",
    "DEFAULT_PROMPT_VARIANT_SPECS",
    "ARTIST_COLUMNS",
    "TITLE_COLUMNS",
    "STYLE_PERIOD_COLUMNS",
    "CATEGORY_COLUMNS",
    "SOURCE_REQUIRED_COLUMNS",
    "PROMPT_POLICY_REQUIRED_COLUMNS",
    "CANDIDATE_REQUIRED_COLUMNS",
    "StableDiffusionInpaintConfig",
    "ensure_directory",
    "safe_text",
    "safe_slug",
    "short_hash",
    "compact_slug",
    "compact_dataset_code",
    "compact_mask_code",
    "compact_restored_filename",
    "require_columns",
    "resolve_path",
    "to_storage_path",
    "sha256_file",
    "metadata_context",
    "build_stable_diffusion_prompt_policy_df",
    "render_stable_diffusion_prompt",
    "standardize_stable_diffusion_source_cases",
    "select_prompt_ablation_subset",
    "build_stable_diffusion_candidate_manifest",
    "get_device",
    "torch_dtype_from_precision",
    "torch_memory_snapshot",
    "runtime_environment_info",
    "load_stable_diffusion_inpaint_pipeline",
    "mask_effective_binary_array",
    "binarize_mask_image",
    "binarize_mask_image_with_stats",
    "prepare_inpaint_inputs",
    "composite_generated_with_damaged",
    "run_stable_diffusion_candidate",
    "run_stable_diffusion_candidates",
    "validate_stable_diffusion_restoration_outputs",
    "summarize_stable_diffusion_restoration_metadata",
]
