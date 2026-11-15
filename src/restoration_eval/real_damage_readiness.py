"""D04 Batch 2: local runtime/assets, input-only comparators and frozen plans.

No inference, remote downloads, notebook edits or upstream writes occur here.
Full model loading and inference are tested by each subsequent method batch.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd
from PIL import Image
import yaml

from . import real_damage_restoration as d04
from .manifests import environment_summary, git_state, sha256_file, utc_now_iso
from .paths import resolve_repo_path, to_repo_relative, require_notebook_output_path
from .real_damage_dataset import audit_inventory_inputs
from .validation import ValidationCollector

REAL_DAMAGE_READINESS_MODULE_VERSION = "1.0.0"
STAGE = "batch_2_runtime_selection_and_freeze"
SELECTION_COLUMNS = (
    "case_id", "painting_id", "category", "title", "mask_type",
    "damaged_content_fraction", "bbox_fill_ratio", "largest_component_fraction",
    "component_density_per_100k_content_pixels", "mask_compactness",
    "connected_component_count", "mask_path", "mask_sha256",
    "processed_image_path", "processed_image_sha256",
)


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _check(checks: ValidationCollector, key: str, description: str,
           passed: bool, observed: Any, expected: Any = True) -> None:
    checks.add(validation_stage=STAGE, check_id=key, check_description=description,
               severity="blocking", passed=passed, observed=observed, expected=expected)


def load_readiness_config(path: str | Path) -> dict[str, Any]:
    policy = yaml.safe_load(Path(path).read_text(encoding="utf-8-sig"))
    d04._require(policy["schema_version"] == "real_damage_readiness_config.v1" and policy["stage"] == STAGE,
                 "Unsupported readiness configuration")
    r, s = policy["runtime"], policy["selection"]
    d04._require(r["network_downloads"] is False and r["model_inference"] is False
                 and r["cuda_required"] is True and r["cpu_fallback"] is False
                 and r["hash_local_model_files"] is True and r["tokenizer_truncation"] is False,
                 "Runtime policy must be local, read-only and without CPU fallback")
    d04._require(s["population"] == "canonical_nonzero_controlled_300" and s["expected_pool"] == 1200
                 and s["category_match_required"] is True and s["distinct_synthetic_paintings"] is True
                 and s["select_using_restored_images_or_scores"] is False
                 and s["physical_synthetic_pooling"] is False and s["prompt_policy_difference_disclosed"] is True,
                 "Comparator policy changed")
    d04._require(s["order"] == "physical_painting_id_then_score_then_synthetic_case_id"
                 and s["compact_single_target_rule"] == "largest_component_fraction_eq_1_and_bbox_fill_ratio_ge_0p8"
                 and s["compact_single_target_allowed_families"] == ["loss_small", "loss_large"],
                 "Comparator ordering or compact-target policy changed")
    d04._require(s["score"] == {"coverage_absolute_difference_scale": 0.02, "coverage_weight": 2.0,
        "bbox_fill_ratio_weight": 1.0, "largest_component_fraction_weight": 1.0,
        "log_component_density_weight": 1.0, "log_component_density_scale": 101.0,
        "compactness_weight": 1.0}, "Unexpected geometry-distance definition")
    for group in (policy["inputs"], policy["outputs"]):
        for value in group.values():
            d04._relative(value)
    for key in ("restoration_config", "helper_source", "tests"):
        d04._relative(policy[key])
    return policy


def _verified_table(root: Path, relative: str) -> tuple[pd.DataFrame, dict[str, str]]:
    path = resolve_repo_path(relative, root, must_exist=True)
    owner = path.parent.parent
    manifest_path, artifacts_path = owner / "manifests/run_manifest.json", owner / "manifests/artifacts.csv"
    manifest = _json(manifest_path)
    d04._require(manifest["run_status"] == "completed" and manifest["completion_gate_passed"] is True,
                 f"Incomplete comparator producer: {owner.name}")
    expected = [row for row in manifest["outputs"] if row["relative_path"] == relative]
    d04._require(len(expected) == 1, f"Producer does not uniquely own {relative}")
    digest = sha256_file(path)
    artifacts = pd.read_csv(artifacts_path)
    matches = artifacts.loc[artifacts.relative_path.eq(relative)]
    d04._require(len(matches) == 1 and matches.iloc[0].checksum == digest, f"Artifact record differs: {relative}")
    frame = pd.read_csv(path)
    d04._require(len(frame) == expected[0]["expected_cardinality"], f"Producer row count differs: {relative}")
    return frame, {to_repo_relative(p, root): sha256_file(p) for p in (path, manifest_path, artifacts_path)}


def prepare_readiness(project_root: str | Path, config_path: str | Path) -> dict[str, Any]:
    """Revalidate current handoff; collect verified producer tables, never results scores."""
    root = Path(project_root).resolve()
    path = resolve_repo_path(config_path, root, must_exist=True)
    policy = load_readiness_config(path)
    context = d04.audit_restoration_preflight(root, root / policy["restoration_config"])
    context["validation"].raise_for_blocking()
    sources, checksums = {}, {}
    for name, relative in policy["inputs"].items():
        sources[name], bound = _verified_table(root, relative)
        checksums.update(bound)
    checks = ValidationCollector()
    checks.extend(context["validation"].checks)
    _check(checks, "synthetic_producers", "Comparator tables match completed producer and artifact manifests",
           True, len(sources), 7)
    declared = {"readiness_config": path, "readiness_helper": root / policy["helper_source"],
                "readiness_tests": root / policy["tests"]}
    declared.update({f"comparison_source.{i}": root / rel for i, rel in enumerate(sorted(checksums))})
    inventory, audit = audit_inventory_inputs(root, context["inputs"]["inventory"], context["inputs"]["inventory_run"], declared)
    _check(checks, "readiness_inventory", "Current inventory covers Batch 2 inputs and helpers",
           bool(audit.passed.all()), audit.loc[~audit.passed].to_dict("records"), [])
    checks.raise_for_blocking()
    checksums.update({to_repo_relative(p, root): sha256_file(p) for p in declared.values()})
    context.update(root=root, readiness_policy=policy, readiness_config_path=path,
                   sources=sources, readiness_checksums=checksums, validation=checks,
                   readiness_inventory=inventory, readiness_input_audit=audit)
    return context


def select_comparators(real_geometry: pd.DataFrame, synthetic_pool: pd.DataFrame,
                       selection: Mapping[str, Any]) -> pd.DataFrame:
    """Input-only deterministic nearest geometry, within category, no painting reuse."""
    # Whitelist columns: restoration scores cannot influence selection.
    pool = synthetic_pool.loc[:, list(SELECTION_COLUMNS)].copy()
    d04._require(len(pool) == selection["expected_pool"] and pool.case_id.is_unique,
                 "Expected the 1,200 canonical nonzero synthetic cases")
    d04._require(pool.mask_type.isin(["scratch_thin", "loss_small", "loss_large", "mixed_damage"]).all()
                 and pool.damaged_content_fraction.gt(0).all(), "Only canonical nonzero masks may be selected")
    d04._require(len(real_geometry) == 10 and real_geometry.painting_id.is_unique, "Expected ten physical targets")
    geometry_columns = ["damaged_content_fraction", "bbox_fill_ratio", "largest_component_fraction",
                        "component_density_per_100k_content_pixels", "mask_compactness"]
    d04._require(np.isfinite(pool[geometry_columns].to_numpy(float)).all()
                 and np.isfinite(real_geometry[geometry_columns].to_numpy(float)).all(), "Nonfinite selection geometry")
    selected, used = [], set()
    weights = selection["score"]
    for real in real_geometry.sort_values("painting_id").itertuples():
        candidates = pool.loc[pool.category.eq(real.category) & ~pool.painting_id.isin(used)].copy()
        compact = real.largest_component_fraction == 1.0 and real.bbox_fill_ratio >= 0.8
        if compact:
            candidates = candidates.loc[candidates.mask_type.isin(selection["compact_single_target_allowed_families"])]
        d04._require(not candidates.empty, f"No comparator for {real.painting_id}")
        candidates["coverage_term"] = weights["coverage_weight"] * abs(candidates.damaged_content_fraction - real.damaged_content_fraction) / weights["coverage_absolute_difference_scale"]
        candidates["bbox_term"] = weights["bbox_fill_ratio_weight"] * abs(candidates.bbox_fill_ratio - real.bbox_fill_ratio)
        candidates["component_term"] = weights["largest_component_fraction_weight"] * abs(candidates.largest_component_fraction - real.largest_component_fraction)
        candidates["density_term"] = weights["log_component_density_weight"] * abs(np.log1p(candidates.component_density_per_100k_content_pixels) - np.log1p(real.component_density_per_100k_content_pixels)) / np.log(weights["log_component_density_scale"])
        candidates["compactness_term"] = weights["compactness_weight"] * abs(candidates.mask_compactness - real.mask_compactness)
        terms = ["coverage_term", "bbox_term", "component_term", "density_term", "compactness_term"]
        candidates["selection_distance"] = candidates[terms].sum(axis=1)
        pick = candidates.sort_values(["selection_distance", "case_id"], kind="stable").iloc[0]
        used.add(pick.painting_id)
        row = dict(schema_version="real_damage_synthetic_comparators.v1", painting_id=real.painting_id,
            real_case_id=real.case_id, category=real.category, synthetic_case_id=pick.case_id,
            synthetic_painting_id=pick.painting_id, synthetic_title=pick.title, synthetic_mask_type=pick.mask_type,
            real_damage_fraction=float(real.damaged_content_fraction), synthetic_damage_fraction=float(pick.damaged_content_fraction),
            coverage_gap_percentage_points=100 * abs(float(pick.damaged_content_fraction) - float(real.damaged_content_fraction)),
            real_component_count=int(real.connected_component_count), synthetic_component_count=int(pick.connected_component_count),
            selection_distance=float(pick.selection_distance), compact_target_filter_applied=bool(compact),
            synthetic_mask_path=pick.mask_path, synthetic_mask_sha256=pick.mask_sha256,
            synthetic_clean_image_path=pick.processed_image_path, synthetic_clean_image_sha256=pick.processed_image_sha256,
            selection_uses_restoration_scores=False, comparison_scope="descriptive_approximate_input_match",
            real_sd_prompt_policy=d04.PROMPT_POLICY_ID, synthetic_sd_prompt_variant="p00_generic",
            prompt_policy_difference=True,
            mismatch_note="Different artwork and damage origin; geometry is approximate. Targeted versus generic SD conditioning also differs.")
        row.update({key: float(pick[key]) for key in terms})
        selected.append(row)
    return pd.DataFrame(selected)


def prepare_comparators(context: dict[str, Any]) -> dict[str, Any]:
    """Select from original input geometry, then bind existing four-method outputs."""
    root, sources, checks = context["root"], context["sources"], context["validation"]
    masks = sources["masks"].loc[sources["masks"].mask_type.ne("zero_control")].copy()
    pool = masks.merge(sources["artworks"][["painting_id", "category", "title"]], on="painting_id", validate="many_to_one")
    selection = select_comparators(context["tables"]["mask_geometry"], pool, context["readiness_policy"]["selection"])
    cases = sources["cases"].set_index("case_id")
    normalized = {}
    for mid in d04.PRIMARY_MODELS:
        f = sources[mid]
        if mid == d04.SD_MODEL:
            f = f.loc[f.is_primary_candidate.eq(True) & f.prompt_variant_id.eq("p00_generic") & f.seed.eq(2026)]
        d04._require(f.case_id.is_unique, f"Ambiguous primary records for {mid}")
        normalized[mid] = f.set_index("case_id")
    candidate_sources, input_hashes = [], {}
    for index, selected in selection.iterrows():
        cid = selected.synthetic_case_id
        case = cases.loc[cid]
        d04._require(case.experiment_id == "canonical_missing_region" and case.status == "passed", "Wrong synthetic comparison scope")
        selection.loc[index, "synthetic_input_image_path"] = case.input_image_path
        d04._require(case.mask_or_effect_path == selected.synthetic_mask_path
                     and case.clean_image_path == selected.synthetic_clean_image_path, "Synthetic table joins disagree")
        input_digest = sha256_file(resolve_repo_path(case.input_image_path, root, must_exist=True))
        selection.loc[index, "synthetic_input_image_sha256"] = input_digest
        for rel, expected in ((case.input_image_path, input_digest),
                              (selected.synthetic_mask_path, selected.synthetic_mask_sha256),
                              (selected.synthetic_clean_image_path, selected.synthetic_clean_image_sha256)):
            path = resolve_repo_path(rel, root, must_exist=True)
            d04._require(sha256_file(path) == expected, f"Selected comparator input changed: {rel}")
            input_hashes[rel] = expected
        for mid in d04.PRIMARY_MODELS:
            row = normalized[mid].loc[cid]
            d04._require(row.status == "completed" and row.mask_sha256 == selected.synthetic_mask_sha256
                         and row.input_sha256 == input_digest, f"Comparator candidate input mismatch: {mid}/{cid}")
            owner = (root / context["readiness_policy"]["inputs"][mid]).parent.parent
            rel = str(row.restored_path)
            path = resolve_repo_path(rel if rel.startswith("outputs/") else owner / rel, root, must_exist=True)
            d04._require(path.is_relative_to(owner), "Comparator output escapes its producer")
            d04._require(sha256_file(path) == row.restored_sha256, f"Comparator output changed: {mid}/{cid}")
            with Image.open(path) as image:
                d04._require(image.size == (768, 768) and image.mode == "RGB", "Invalid comparator restoration")
                image.verify()
            relative = to_repo_relative(path, root)
            input_hashes[relative] = row.restored_sha256
            candidate_sources.append(dict(painting_id=selected.painting_id, synthetic_case_id=cid,
                model_id=mid, candidate_id=row.candidate_id, restored_path=relative,
                restored_sha256=row.restored_sha256, input_sha256=input_digest,
                mask_sha256=row.mask_sha256, configuration_id=row.configuration_id,
                prompt_variant="p00_generic" if mid == d04.SD_MODEL else "", seed=2026 if mid == d04.SD_MODEL else ""))
    _check(checks, "comparators", "Ten same-category comparators from ten distinct synthetic paintings",
           len(selection) == 10 and selection.synthetic_painting_id.nunique() == 10, len(selection), 10)
    _check(checks, "comparison_candidates", "Forty existing primary outputs match saved hashes and input bindings",
           len(candidate_sources) == 40, len(candidate_sources), 40)
    _check(checks, "comparison_policy", "Selection ignores restoration scores and discloses prompt-policy difference",
           not selection.selection_uses_restoration_scores.any() and selection.prompt_policy_difference.all(), "input-only selection")
    context.update(comparators=selection, comparator_candidates=pd.DataFrame(candidate_sources), selected_file_checksums=input_hashes)
    return context


def tokenize_prompts(tokenizer: Any, prompts: pd.DataFrame, negative: str) -> pd.DataFrame:
    maximum = int(tokenizer.model_max_length)
    d04._require(maximum == 77, "Unexpected SD1.5 CLIP context length")
    rows = []
    for row in prompts.itertuples():
        count = len(tokenizer(row.prompt, truncation=False, add_special_tokens=True)["input_ids"])
        rows.append(dict(painting_id=row.painting_id, prompt_id=row.prompt_id, kind="positive",
                         tokens=count, maximum_tokens=maximum, fits=count <= maximum, truncation_used=False))
    count = len(tokenizer(negative, truncation=False, add_special_tokens=True)["input_ids"])
    rows.append(dict(painting_id="all", prompt_id="unchanged_negative", kind="negative",
                     tokens=count, maximum_tokens=maximum, fits=count <= maximum, truncation_used=False))
    return pd.DataFrame(rows)


def audit_runtime_assets(context: dict[str, Any], progress: Callable[[str], None] = print) -> dict[str, Any]:
    """Inspect local runtime and hash assets; no model instantiation or downloads."""
    checks, assets = context["validation"], []
    def asset(mid: str, role: str, path: Path, digest: str | None = None) -> str:
        d04._require(path.is_file() and path.stat().st_size > 0, f"Missing local asset: {path}")
        value = digest or sha256_file(path)
        assets.append(dict(model_id=mid, asset_role=role, path=str(path.resolve()),
                           size_bytes=path.stat().st_size, sha256=value))
        return value

    progress("Checking imports and CUDA availability...")
    import torch
    import cv2
    from diffusers import StableDiffusionInpaintPipeline, DDIMScheduler
    from transformers import CLIPTokenizer
    from huggingface_hub import snapshot_download
    from .restoration_lama import get_lama_runtime_environment, validate_lama_runtime_environment
    from .restoration_hint import inspect_hint_asset
    environment = environment_summary(package_names=["torch", "torchvision", "numpy", "pandas", "Pillow", "iopaint",
        "diffusers", "transformers", "accelerate", "safetensors", "huggingface-hub", "einops", "timm"])
    environment.update(python_executable=str(Path(sys.executable).resolve()), opencv_version=cv2.__version__,
        cuda_available=bool(torch.cuda.is_available()), cuda_runtime=str(torch.version.cuda),
        gpu_name=torch.cuda.get_device_name(0) if torch.cuda.is_available() else "",
        readiness_scope="environment_assets_and_tokenizer_pending_method_smoke")
    _check(checks, "runtime_imports", "OpenCV and SD pipeline/scheduler classes import", callable(cv2.inpaint)
           and StableDiffusionInpaintPipeline is not None and DDIMScheduler is not None, "imports succeeded")
    _check(checks, "cuda", "CUDA available; no CPU substitution for the learned pipelines",
           environment["cuda_available"], environment["gpu_name"])
    progress("Checking cached LaMa checkpoint against the executed baseline...")
    lama = get_lama_runtime_environment(context["baseline_configs"]["lama"], project_root=context["root"])
    validate_lama_runtime_environment(lama)
    baseline_model = context["baseline_configs"]["lama"]["model"]
    d04._require(lama["model_artifact_url"] == baseline_model["model_artifact_url"]
                 and lama["model_artifact_expected_md5"] == baseline_model["model_artifact_expected_md5"], "LaMa environment overrides the baseline weights")
    known_lama = context["sources"]["lama"].model_artifact_sha256.dropna().unique().tolist()
    d04._require(len(known_lama) == 1, "Ambiguous historical LaMa checkpoint")
    value = asset("lama", "weights", Path(lama["model_artifact_path"]), lama["model_artifact_sha256"])
    _check(checks, "lama_checkpoint", "LaMa checkpoint equals the executed N10 checkpoint", value == known_lama[0], value, known_lama[0])
    environment["lama"] = lama

    progress("Checking pinned HINT source and Places2 checkpoint...")
    hint = inspect_hint_asset(context["baseline_configs"]["hint_places2"])
    hint_manifest = _json(context["root"] / "outputs/12a_hint_restoration/manifests/run_manifest.json")
    expected_hint = hint_manifest["execution_evidence"]["checkpoint_revision"]
    _check(checks, "hint_source", "HINT repository HEAD matches the pinned revision and required files exist",
           hint["ready"], hint["actual_repository_revision"], hint["pinned_repository_revision"])
    value = asset("hint_places2", "weights", Path(hint["checkpoint_path"]), hint["checkpoint_sha256"])
    _check(checks, "hint_checkpoint", "HINT checkpoint equals the executed N12A checkpoint", value == expected_hint, value, expected_hint)
    repository = Path(hint["repository_path"])
    source = repository / "src/networks.py"
    spec = importlib.util.spec_from_file_location("d04_hint_network_import_check", source)
    d04._require(spec is not None and spec.loader is not None, "Cannot inspect HINT generator module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _check(checks, "hint_import", "HINT generator class imports without model instantiation", hasattr(module, "HINT"), "class import")
    for file in sorted((repository / "src").rglob("*.py")):
        asset("hint_places2", "source:" + file.relative_to(repository).as_posix(), file)
    environment["hint"] = hint

    progress("Resolving the pinned local SD snapshot and hashing its model files...")
    sd = context["baseline_configs"][d04.SD_MODEL]["model"]
    snapshot = Path(snapshot_download(sd["hf_model_id"], revision=sd["model_revision"], local_files_only=True))
    d04._require(snapshot.name == sd["model_revision"], "Cached SD snapshot revision differs")
    required = ["model_index.json", "scheduler/scheduler_config.json", "text_encoder/config.json",
                "unet/config.json", "vae/config.json", "tokenizer/vocab.json", "tokenizer/merges.txt",
                "tokenizer/tokenizer_config.json", "tokenizer/special_tokens_map.json",
                "feature_extractor/preprocessor_config.json"]
    for component, name in (("text_encoder", "model"), ("unet", "diffusion_pytorch_model"), ("vae", "diffusion_pytorch_model")):
        safe = snapshot / component / ("model.safetensors" if component == "text_encoder" else name + ".safetensors")
        binary = snapshot / component / ("pytorch_model.bin" if component == "text_encoder" else name + ".bin")
        weight = safe if safe.is_file() else binary
        required.append(weight.relative_to(snapshot).as_posix())
    for relative in required:
        progress(f"SD asset: {relative}")
        asset(d04.SD_MODEL, relative, snapshot / relative)
    _check(checks, "sd_snapshot", "Required SD files available at the pinned local revision", True, snapshot.name, sd["model_revision"])
    _check(checks, "sd_inpainting_architecture", "Snapshot is the nine-channel inpainting pipeline",
           _json(snapshot / "unet/config.json")["in_channels"] == 9
           and _json(snapshot / "model_index.json")["_class_name"] == "StableDiffusionInpaintPipeline", "9-channel inpainting")
    tokenizer = CLIPTokenizer.from_pretrained(snapshot / "tokenizer", local_files_only=True)
    token_audit = tokenize_prompts(tokenizer, context["prompts"], context["baseline_configs"][d04.SD_MODEL]["prompt_policy"]["negative_prompt"])
    for row in token_audit.itertuples():
        _check(checks, f"tokens:{row.prompt_id}", "Full prompt fits the tokenizer including special tokens",
               bool(row.fits), int(row.tokens), f"<= {row.maximum_tokens}; no truncation")
    environment["sd"] = dict(snapshot_path=str(snapshot), model_id=sd["hf_model_id"], revision=sd["model_revision"],
                             file_integrity_scope="full_local_sha256_recorded_at_pinned_cache_revision")
    context.update(runtime_environment=environment, runtime_assets=pd.DataFrame(assets), tokenizer_audit=token_audit)
    return context


def build_executable_plan(context: Mapping[str, Any]) -> pd.DataFrame:
    """Supply execution fields expected by existing algorithms, preserving candidate IDs."""
    plan = context["candidate_plan"].copy()
    model_rows = []
    for row in plan.to_dict("records"):
        model = context["effective_configs"][row["model_id"]]["model"]
        row.update(input_sha256=row["input_image_sha256"], mask_or_effect_path=row["mask_path"],
            mask_or_effect_id=row["mask_id"], mask_threshold=128, mask_threshold_comparison="greater_than_or_equal",
            inference_width=int(model.get("inference_width", 768)), inference_height=int(model.get("inference_height", 768)),
            precision=model.get("precision", "uint8"), device=model.get("requested_device", "cpu"),
            runtime_status="assets_verified_smoke_pending")
        if row["model_id"] == d04.SD_MODEL:
            row.update({k: model[k] for k in ("num_inference_steps", "guidance_scale", "strength", "scheduler",
                "hf_model_id", "model_revision", "safety_checker_policy")})
            row.update(prompt_variant_id=row["prompt_variant"], compositing_policy=model["compositing_policy"])
        model_rows.append(row)
    return pd.DataFrame(model_rows).astype({"seed": "Int64"})


def render_comparison_inputs(context: Mapping[str, Any], destination: Path, first: int, last: int) -> None:
    """Input/mask panels only; no restored images or quality scores are displayed."""
    import matplotlib.pyplot as plt
    root = context["root"]
    rows = context["comparators"].iloc[first:last]
    real = context["tables"]["case_registry"].set_index("painting_id")
    fig, axes = plt.subplots(len(rows), 2, figsize=(12, len(rows) * 3.1), squeeze=False)
    for i, row in enumerate(rows.itertuples()):
        r = real.loc[row.painting_id]
        for j, (input_path, mask_path, title) in enumerate((
            (r.input_image_path, r.mask_or_effect_path, f"{row.painting_id} | physical | {100*row.real_damage_fraction:.2f}% selected"),
            (row.synthetic_input_image_path, row.synthetic_mask_path,
             f"{row.synthetic_case_id} | {100*row.synthetic_damage_fraction:.2f}%"))):
            with Image.open(root / input_path) as image, Image.open(root / mask_path) as mask:
                rgb, binary = np.array(image.convert("RGB")), np.array(mask) >= 128
            axes[i, j].imshow(rgb)
            overlay = np.zeros((*binary.shape, 4))
            overlay[binary] = [0, 1, 1, 0.40]
            axes[i, j].imshow(overlay)
            axes[i, j].set_title(title, fontsize=9)
            axes[i, j].axis("off")
    fig.suptitle("D04 | Input-based comparison selection — cyan marks repair targets", fontsize=13)
    fig.text(0.5, 0.012, "Different artworks and approximate geometry; no restoration outcomes used.\n"
        "D03: source credits/licences in artworks.csv (rd004 Tyler Bell CC BY 2.0; rd005 BeakheadIntrados CC BY-SA 4.0; rd006 The Met CC0).\n"
        "Synthetic inputs: Controlled-300 source credits in N01 artworks.csv. Resizing and mask overlays are display adaptations.",
        ha="center", fontsize=7)
    fig.tight_layout(rect=(0, .05, 1, .97))
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=130)
    plt.close(fig)


def _bytes(value: Any) -> bytes:
    if isinstance(value, pd.DataFrame):
        return value.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".d04.tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)


def freeze_readiness(context: dict[str, Any]) -> dict[str, Any]:
    """Freeze only a successful audit. Existing differing evidence is never replaced."""
    checks, root, output = context["validation"], context["root"], context["output_root"]
    checks.raise_for_blocking()
    d04._require(context["tokenizer_audit"].fits.all() and len(context["comparators"]) == 10, "Incomplete Batch 2 evidence")
    required_checks = {"synthetic_producers", "readiness_inventory", "comparators", "comparison_candidates", "comparison_policy",
                       "runtime_imports", "cuda", "lama_checkpoint", "hint_source", "hint_checkpoint", "hint_import",
                       "sd_snapshot", "sd_inpainting_architecture", "tokens:unchanged_negative"}
    d04._require(required_checks.issubset({c.check_id for c in checks.checks if c.validation_stage == STAGE})
                 and all("tokens:" + p in {c.check_id for c in checks.checks} for p in context["prompts"].prompt_id),
                 "Runtime/selection checks have not all run")
    plan = build_executable_plan(context)
    scientific = {to_repo_relative(context["inputs"][k], root): value for k, value in context["input_checksums"].items()
        if k not in {"inventory", "inventory_run", "project_paths", "evidence_audit", "evidence_coverage", "notebook_roadmap"}}
    scientific.update(context["readiness_checksums"])
    scientific.update(context["selected_file_checksums"])
    for relative, expected in scientific.items():
        d04._require(sha256_file(root / relative) == expected, f"Input changed during readiness: {relative}")
    for asset in context["runtime_assets"].itertuples():
        d04._require(Path(asset.path).is_file() and Path(asset.path).stat().st_size == asset.size_bytes, "Model asset changed during readiness")
    fingerprint = d04._digest(dict(inputs=scientific, plan=plan.astype(object).where(plan.notna(), "").to_dict("records"),
        runtime_assets=context["runtime_assets"].to_dict("records"), environment=context["runtime_environment"],
        selection=context["comparators"].to_dict("records")))
    policy = context["readiness_policy"]
    checkpoint = require_notebook_output_path(output / policy["outputs"]["checkpoint"], d04.NOTEBOOK_STEM, root)
    if checkpoint.exists():
        saved = _json(checkpoint)
        d04._require(saved["readiness_fingerprint"] == fingerprint, "Frozen readiness differs; do not overwrite or reuse old candidates")
        for relative, expected in saved["file_checksums"].items():
            d04._require(sha256_file(root / relative) == expected, f"Frozen Batch 2 artifact changed: {relative}")
        context.update(frozen_plan=plan,
                       readiness_checkpoint=saved, checkpoint_path=checkpoint, reused=True)
        return context
    provenance = []
    for mid in d04.PRIMARY_MODELS:
        assets = context["runtime_assets"].loc[context["runtime_assets"].model_id.eq(mid)]
        provenance.append(dict(model_id=mid, baseline_configuration_id=context["baseline_configs"][mid]["model"]["configuration_id"],
            configuration_id=context["effective_configs"][mid]["model"]["configuration_id"],
            asset_fingerprint=d04._digest(assets.to_dict("records")),
            device="cpu" if mid == "opencv_telea" else "cuda", readiness_scope=policy["runtime"]["readiness_scope"],
            model_inference_executed=False))
    prompt_table = context["prompts"].copy()
    prompt_table["negative_prompt"] = context["baseline_configs"][d04.SD_MODEL]["prompt_policy"]["negative_prompt"]
    prompt_table["review_status"] = "accepted_by_user_after_batch_1"
    payloads = {
        context["config"]["outputs"]["candidate_plan"]: plan,
        context["config"]["outputs"]["prompt_policy"]: prompt_table,
        context["config"]["outputs"]["model_provenance"]: pd.DataFrame(provenance),
        context["config"]["outputs"]["synthetic_comparators"]: context["comparators"],
        policy["outputs"]["runtime_environment"]: context["runtime_environment"],
        policy["outputs"]["runtime_assets"]: context["runtime_assets"],
        policy["outputs"]["tokenizer_audit"]: context["tokenizer_audit"],
        policy["outputs"]["synthetic_candidates"]: context["comparator_candidates"],
        policy["outputs"]["input_checksums"]: pd.DataFrame(sorted(scientific.items()), columns=["relative_path", "sha256"]),
        policy["outputs"]["validation"]: checks.to_dataframe(),
    }
    serialized = {require_notebook_output_path(output / rel, d04.NOTEBOOK_STEM, root): _bytes(value)
                  for rel, value in payloads.items()}
    for path, content in serialized.items():
        d04._require(not path.exists() or path.read_bytes() == content, f"Existing different evidence cannot be overwritten: {path}")
    for path, content in serialized.items():
        if not path.exists():
            _atomic(path, content)
    previews = []
    for key, first, last in (("preview_first", 0, 5), ("preview_second", 5, 10)):
        path = require_notebook_output_path(output / policy["outputs"][key], d04.NOTEBOOK_STEM, root)
        # Regenerate an interrupted preview and compare bytes before accepting it.
        temporary = path.with_name(path.stem + ".d04.tmp.png")
        try:
            render_comparison_inputs(context, temporary, first, last)
            with Image.open(temporary) as image:
                image.verify()
            content = temporary.read_bytes()
            d04._require(not path.exists() or path.read_bytes() == content,
                         f"Existing comparison preview differs: {path}")
            if not path.exists():
                _atomic(path, content)
        finally:
            temporary.unlink(missing_ok=True)
        previews.append(path)
    file_checksums = {to_repo_relative(p, root): sha256_file(p) for p in [*serialized, *previews]}
    saved = dict(schema_version="real_damage_readiness_checkpoint.v1", notebook_id="D04", stage=STAGE,
        status="ready_for_method_smoke", completion_gate_passed=False, inference_executed=False,
        recorded_at_utc=utc_now_iso(), git=git_state(root), inventory_run_id=context["inventory"]["inventory_run_id"],
        readiness_fingerprint=fingerprint, source_run_id=context["upstream_manifest"]["run_id"],
        counts={"planned_candidates": 70, "primary": 40, "additional_SD": 30, "synthetic_cases": 10,
                "synthetic_candidate_sources": 40, "prompts": 10}, validation_summary=checks.summary(),
        file_checksums=file_checksums, scientific_input_checksums=scientific,
        prompt_policy_difference_disclosed=True, selected_comparators_use_quality_scores=False)
    _atomic(checkpoint, _bytes(saved))
    context.update(frozen_plan=plan, readiness_checkpoint=saved, checkpoint_path=checkpoint, reused=False)
    return context
