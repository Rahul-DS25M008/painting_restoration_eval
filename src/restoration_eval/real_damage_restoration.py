"""D04 preparation: immutable D03 handoff and targeted-prompt candidate contracts.

Batch 1 is read-only. It does not import inference frameworks, load weights,
execute a notebook, or publish a run. Runtime checks and plan freezing belong
to Batch 2; method-specific inference remains in the existing model helpers.
"""
from __future__ import annotations

import copy
import hashlib
import json
import platform
from pathlib import Path, PureWindowsPath
from time import perf_counter
from typing import Any, Mapping

import pandas as pd
import yaml

from .manifests import sha256_file
from .paths import (find_project_root, notebook_output_root, resolve_repo_path,
                    to_repo_relative, validate_project_paths_registry)
from .real_damage_completion import audit_completion
from .real_damage_dataset import CATEGORIES, PRIMARY_MODELS, audit_inventory_inputs
from .validation import ValidationCollector

REAL_DAMAGE_RESTORATION_MODULE_VERSION = "1.0.0"
NOTEBOOK_STEM = "d04_real_damage_restoration_and_evaluation"
PREFLIGHT_STAGE = "batch_1_handoff_and_prompt_preflight"
SD_MODEL = "stable_diffusion_inpainting"
PROMPT_POLICY_ID = "d04_sd15_targeted_visible_context.v1"
PROMPT_VARIANT = "p05_real_damage_targeted"
SD_CONFIGURATION_ID = "sd15_inpaint_targeted_real_damage_v1"
PAINTING_IDS = tuple(f"rd{i:03d}" for i in range(1, 11))
MODEL_CONFIG_PATHS = dict(zip(PRIMARY_MODELS, (
    "config/experiments/opencv_telea.yaml", "config/experiments/lama.yaml",
    "config/experiments/hint.yaml", "config/experiments/stable_diffusion.yaml")))
OUTPUT_KEYS = frozenset({
    "candidate_plan", "candidates", "prompt_policy", "model_provenance",
    "synthetic_comparators", "case_observations", "runtime_summary",
    "technical_checks", "real_damage_diagnostics", "seed_pairwise",
    "uncertainty_summary", "synthetic_comparison", "restored_template",
    "uncertainty_array_template", "uncertainty_preview_template",
    "case_panel_template", "comparator_panel_template", "seed_panel_template",
    "report", "run_manifest", "artifacts", "validation", "work_root", "logs_root",
})


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _relative(value: Any) -> str:
    _require(isinstance(value, str) and bool(value.strip()), "Missing relative path")
    _require(not Path(value).is_absolute() and not PureWindowsPath(value).drive
             and not PureWindowsPath(value).root
             and "\\" not in value and ".." not in value.split("/")
             and ".codex_tmp" not in value.split("/"), f"Unsafe repository path: {value}")
    return value


def load_restoration_config(path: str | Path) -> dict[str, Any]:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8-sig"))
    validate_restoration_config(config)
    return config


def validate_restoration_config(config: Mapping[str, Any]) -> None:
    _require(isinstance(config, Mapping), "D04 configuration must be a mapping")
    _require(config.get("config_schema_version") == "real_damage_restoration_config.v1"
             and config.get("contract_status") == "approved", "D04 contract is not approved/supported")
    nb, ds, plan = config["notebook"], config["dataset"], config["candidate_design"]
    _require(nb == {"id": "D04", "stem": NOTEBOOK_STEM,
                     "output_root": f"outputs/{NOTEBOOK_STEM}", "batch_count": 10}, "Wrong notebook ownership")
    _require(ds == {"dataset_id": "painting_restoration_real_damage", "dataset_scope": "real_damage_10",
        "dataset_version": "2.0.0", "experiment_id": "real_damage_targeted_restoration",
        "has_clean_reference": False, "expected_paintings": 10, "expected_per_category": 2}, "Wrong D04 population")
    _require(config["models"] == MODEL_CONFIG_PATHS, "The four baseline model configurations must be retained")
    _require(plan == {"primary_candidates": 40, "primary_seed": 2026,
        "sd_seeds": [2026, 2027, 2028, 2029], "additional_sd_candidates": 30,
        "total_candidates": 70, "uncertainty_groups": 10, "unique_seed_pairs": 60}, "Candidate design changed")
    policy = config["prompt_policy"]
    required = {"policy_id": PROMPT_POLICY_ID, "effective_configuration_id": SD_CONFIGURATION_ID,
        "variant_id": PROMPT_VARIANT, "selection": "one_prompt_per_painting_from_damaged_input_and_reviewed_mask",
        "negative_prompt": "inherit_unchanged_sd15_baseline", "fixed_across_seeds": True,
        "freeze_before_inference": True, "outcome_based_tuning": False, "known_clean_image_used": False,
        "tokenizer_length_check_batch": 2, "reject_silent_prompt_truncation": True,
        "d03_generic_prompt_declaration": "superseded_for_D04_only_by_user_approved_targeted_policy",
        "synthetic_comparison_prompt_policy": "different_from_existing_generic_SD_comparators"}
    _require(policy == required, "Targeted SD prompt policy changed")
    ev, comparison, execution = config["evaluation"], config["comparison"], config["execution"]
    _require(ev["input_as_clean_reference"] is False
             and ev["physical_reference_fidelity_metrics_applicable"] is False, "Physical input cannot be a clean reference")
    _require(comparison["synthetic_cases"] == 10 and comparison["selection_stage"] == 2
             and comparison["selection_before_D04_restoration_outcomes"] is True
             and comparison["select_using_restoration_scores"] is False
             and comparison["pool_real_and_synthetic_metrics"] is False
             and comparison["same_prompt_domain_effect_claim_allowed"] is False, "Invalid synthetic comparison policy")
    _require(execution["assistant_executes_notebook"] is False
             and execution["user_creates_and_edits_notebook"] is True
             and execution["automatic_cleanup"] is False
             and execution["checkpoint_after_each_candidate"] is True
             and execution["resume_requires_matching_inputs_configuration_prompt_and_output_hashes"] is True,
             "Execution/resume policy changed")
    _require([b["number"] for b in config["batches"]] == list(range(1, 11)), "Expected ten ordered batches")
    _require(set(config["outputs"]) == OUTPUT_KEYS, "Output contract is incomplete")
    _require(len(set(config["outputs"].values())) == len(OUTPUT_KEYS), "Output paths must be unique")
    for group in (config["inputs"], config["models"], config["inference_helpers"], config["outputs"]):
        for value in group.values():
            _relative(value)
    for key in ("manifest", "completion_config"):
        _relative(config["upstream"][key])


def load_prompt_catalog(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8-sig"))


def validate_prompt_catalog(catalog: Mapping[str, Any], cases: pd.DataFrame,
                            manifest: Mapping[str, Any], config: Mapping[str, Any]) -> pd.DataFrame:
    """Bind context-authored prompts to exact inputs; never substitute clean images."""
    required = {"schema_version": "real_damage_sd_prompt_catalog.v1", "policy_id": PROMPT_POLICY_ID,
        "record_status": "prepared_before_inference", "known_clean_images_consulted": False,
        "restoration_outputs_consulted": False, "fixed_across_seeds": True,
        "source_run_id": manifest["run_id"], "source_data_fingerprint": manifest["data_fingerprint"],
        "negative_prompt_source": "config/experiments/stable_diffusion.yaml:prompt_policy.negative_prompt"}
    _require(all(catalog.get(k) == v for k, v in required.items()), "Prompt provenance/policy mismatch")
    records = catalog.get("records", [])
    _require([r.get("painting_id") for r in records] == list(PAINTING_IDS), "Expected one ordered prompt per painting")
    _require(cases.painting_id.is_unique and set(cases.painting_id) == set(PAINTING_IDS), "Cases are not unique/complete")
    lookup = cases.set_index("painting_id")
    ids, prompts = set(), set()
    for row in records:
        pid = row["painting_id"]
        case = lookup.loc[pid]
        for field, case_field in (("case_id", "case_id"), ("category", "category"),
            ("input_image_path", "input_image_path"), ("input_image_sha256", "input_image_sha256"),
            ("mask_path", "mask_or_effect_path"), ("mask_sha256", "mask_sha256")):
            _require(row[field] == case[case_field], f"Prompt {pid} has wrong {field} binding")
        text = row.get("prompt", "")
        _require(isinstance(text, str) and text == text.strip() and 15 <= len(text.split()) <= 65
                 and "\n" not in text and "\r" not in text and "{" not in text and "}" not in text,
                 f"Invalid targeted prompt text: {pid}")
        _require(hashlib.sha256(text.encode("utf-8")).hexdigest() == row["prompt_sha256"], f"Prompt digest mismatch: {pid}")
        _require(row["prompt_id"] == f"d04_targeted_{pid}_v1" and row["prompt_id"] not in ids,
                 "Prompt identifiers must be unique and painting-specific")
        _require(text not in prompts, "Generic prompt repeated across paintings")
        _require(row["prompt_variant"] == config["prompt_policy"]["variant_id"], "Wrong prompt variant")
        _require(bool(row.get("visible_damage_observation", "").strip()), "Missing visible-damage rationale")
        _relative(row["input_image_path"])
        _relative(row["mask_path"])
        ids.add(row["prompt_id"])
        prompts.add(text)
    return pd.DataFrame(copy.deepcopy(records))


def effective_model_config(baseline: Mapping[str, Any], model_id: str,
                           config: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy with SD prompt identity changed; numerical model settings stay exact.

    This is a model-settings snapshot, not the historical notebook's worklist.
    D04 adapters must supply their own scoped worklists/output roots. SD's existing
    per-candidate executor receives the explicit prompt from the candidate row.
    """
    _require(model_id in PRIMARY_MODELS and baseline["model"]["model_id"] == model_id, "Model identity mismatch")
    effective = copy.deepcopy(baseline)
    if model_id == SD_MODEL:
        _require(baseline["prompt_policy"]["primary_variant_id"] == "p00_generic", "Unexpected SD baseline prompt")
        effective["model"]["configuration_id"] = config["prompt_policy"]["effective_configuration_id"]
        effective["prompt_policy"] = {
            "policy_id": config["prompt_policy"]["policy_id"],
            "primary_variant_id": config["prompt_policy"]["variant_id"],
            "negative_prompt": baseline["prompt_policy"]["negative_prompt"],
            "prompt_source": config["inputs"]["prompt_catalog"],
            "requires_explicit_candidate_prompt": True,
        }
    return effective


def build_candidate_plan(cases: pd.DataFrame, eligibility: pd.DataFrame, prompts: pd.DataFrame,
                         baselines: Mapping[str, Any], config: Mapping[str, Any]) -> pd.DataFrame:
    """Build a deterministic in-memory plan. Freezing and execution are later stages."""
    _require(len(cases) == 10 and cases.case_id.is_unique and cases.painting_id.is_unique
             and set(cases.painting_id) == set(PAINTING_IDS), "Expected ten unique real cases")
    _require(len(eligibility) == 40 and not eligibility.duplicated(["case_id", "model_id"]).any()
             and set(zip(eligibility.case_id, eligibility.model_id)) ==
             {(c, m) for c in cases.case_id for m in PRIMARY_MODELS}, "Eligibility is not the complete 10 by 4 matrix")
    _require(eligibility.eligible.map(lambda x: x is True or type(x).__name__ == "bool_" and bool(x)).all(),
             "An ineligible case cannot enter the candidate plan")
    _require(len(prompts) == 10 and prompts.painting_id.is_unique
             and set(prompts.painting_id) == set(PAINTING_IDS), "Incomplete prompt table")
    rows = []
    prompt_lookup = prompts.set_index("painting_id")
    eligible = eligibility.set_index(["case_id", "model_id"])
    for case in cases.sort_values("painting_id").itertuples():
        _require(not bool(case.has_clean_reference) and not bool(case.reference_fidelity_metrics_applicable),
                 "Real cases cannot claim reference fidelity")
        for model_id in PRIMARY_MODELS:
            e = eligible.loc[(case.case_id, model_id)]
            _require(e.input_image_sha256 == case.input_image_sha256 and e.mask_sha256 == case.mask_sha256,
                     "Eligibility input/mask binding mismatch")
            baseline = baselines[model_id]
            _require(e.configuration_id == baseline["model"]["configuration_id"], "Baseline configuration mismatch")
            effective = effective_model_config(baseline, model_id, config)
            is_sd = model_id == SD_MODEL
            prompt_record = prompt_lookup.loc[case.painting_id].to_dict() if is_sd else {}
            if is_sd:
                _require(prompt_record["case_id"] == case.case_id
                         and prompt_record["input_image_sha256"] == case.input_image_sha256
                         and prompt_record["mask_sha256"] == case.mask_sha256, "Candidate prompt binding mismatch")
            model_fingerprint = _digest(effective["model"])
            negative = effective["prompt_policy"]["negative_prompt"] if is_sd else ""
            seeds = config["candidate_design"]["sd_seeds"] if is_sd else [2026 if model_id == "hint_places2" else None]
            group_binding = dict(case_id=case.case_id, model_id=model_id, model_config_sha256=e.model_config_sha256,
                configuration_fingerprint=model_fingerprint, input_image_sha256=case.input_image_sha256,
                mask_sha256=case.mask_sha256, prompt_record_sha256=_digest(prompt_record) if is_sd else "",
                negative_prompt=negative)
            group_id = "d04_sdgroup_" + _digest(group_binding)[:20] if is_sd else ""
            for seed in seeds:
                cid = "d04_candidate_" + _digest({**group_binding, "seed": seed})[:24]
                row = dict(schema_version="real_damage_candidate_plan.v1", **config["dataset"])
                row.pop("expected_paintings")
                row.pop("expected_per_category")
                row.update(painting_id=case.painting_id, category=case.category, case_id=case.case_id,
                    mask_id=case.mask_id, source_experiment_id=case.experiment_id, model_id=model_id,
                    baseline_configuration_id=e.configuration_id,
                    configuration_id=effective["model"]["configuration_id"],
                    model_config_path=e.model_config_path, model_config_sha256=e.model_config_sha256,
                    configuration_fingerprint=model_fingerprint, input_image_path=case.input_image_path,
                    input_image_sha256=case.input_image_sha256, mask_path=case.mask_or_effect_path,
                    mask_sha256=case.mask_sha256, candidate_id=cid, seed=seed,
                    candidate_role="additional_seed" if is_sd and seed != 2026 else "primary",
                    uncertainty_group_id=group_id, prompt_id=prompt_record.get("prompt_id", ""),
                    prompt_variant=PROMPT_VARIANT if is_sd else "", prompt=prompt_record.get("prompt", ""),
                    prompt_sha256=prompt_record.get("prompt_sha256", ""),
                    prompt_record_sha256=group_binding["prompt_record_sha256"], negative_prompt=negative,
                    prompt_policy_id=PROMPT_POLICY_ID if is_sd else "",
                    reference_fidelity_metrics_applicable=False, clean_image_path="", clean_image_sha256="",
                    output_width=768, output_height=768, runtime_status="pending_batch_2",
                    status="planned_not_executed")
                row["restored_path"] = config["outputs"]["restored_template"].format(**row)
                rows.append(row)
    plan = pd.DataFrame(rows)
    plan["seed"] = plan.seed.astype("Int64")
    _require(len(plan) == 70 and plan.candidate_id.is_unique and plan.restored_path.is_unique, "Candidate identity collision")
    _require(plan.candidate_role.value_counts().to_dict() == {"primary": 40, "additional_seed": 30}, "Wrong candidate roles")
    return plan


def audit_restoration_preflight(project_root: str | Path, config_path: str | Path) -> dict[str, Any]:
    """Read-only Batch 1 audit including full D03 integrity and current inventory."""
    started = perf_counter()
    root = Path(project_root).resolve()
    _require(find_project_root(root) == root, "Wrong repository root")
    path = resolve_repo_path(config_path, root, must_exist=True)
    config = load_restoration_config(path)
    output = notebook_output_root(NOTEBOOK_STEM, root)
    inputs = {key: resolve_repo_path(value, root, must_exist=True) for key, value in config["inputs"].items()}
    inputs["d04_config"] = path
    for group in ("models", "inference_helpers"):
        inputs.update({f"{group}.{k}": resolve_repo_path(v, root, must_exist=True) for k, v in config[group].items()})
    for key in ("completion_config", "manifest"):
        inputs[f"d03.{key}"] = resolve_repo_path(config["upstream"][key], root, must_exist=True)
    outputs = {k: resolve_repo_path(output / v, root) for k, v in config["outputs"].items()}
    _require(all(p.is_relative_to(output) for p in outputs.values()), "An output escapes D04")
    _require(not set(inputs.values()).intersection(outputs.values()), "Output would overwrite an input")

    d03 = audit_completion(root, inputs["d03.completion_config"])
    manifest, tables = d03["run_manifest"], d03["tables"]
    _require(manifest["completion_gate_passed"] is True and manifest["downstream_ready"] is True
             and manifest["run_status"] == "completed", "D03 is not completed and ready")
    _require(manifest["run_id"] == config["upstream"]["expected_run_id"]
             and manifest["data_fingerprint"] == config["upstream"]["expected_data_fingerprint"], "Wrong D03 run/fingerprint")
    _require(manifest["validation_summary"]["passed_count"] == config["upstream"]["expected_passed_checks"]
             and manifest["validation_summary"]["failed_count"] == 0, "D03 validation incomplete")
    _require(json.loads(inputs["d03.manifest"].read_text(encoding="utf-8")) == manifest, "Wrong declared D03 manifest")
    for i, relative in enumerate(sorted(manifest["canonical_file_checksums"])):
        inputs[f"d03.canonical.{i}"] = resolve_repo_path(relative, root, must_exist=True)
    inventory, input_audit = audit_inventory_inputs(root, inputs["inventory"], inputs["inventory_run"], inputs)
    checks = ValidationCollector()

    def check(identifier: str, description: str, passed: bool, observed: Any, expected: Any = True) -> None:
        checks.add(validation_stage=PREFLIGHT_STAGE, check_id=identifier, check_description=description,
                   severity="blocking", passed=passed, observed=observed, expected=expected)

    check("contract", "Approved ten-batch contract and D04-owned output paths", True, len(outputs), len(OUTPUT_KEYS))
    py_minor = ".".join(platform.python_version_tuple()[:2])
    check("python", "Supported Python minor version", py_minor in config["execution"]["supported_python_minors"],
          py_minor, config["execution"]["supported_python_minors"])
    check("d03_completion", "Completed D03 scientific files, producers, reviews and baseline checks remain valid",
          True, manifest["validation_summary"]["passed_count"], 379)
    check("inventory", "Current inventory covers D04 preparation and D03 canonical evidence",
          bool(input_audit.passed.all()), input_audit.loc[~input_audit.passed].to_dict("records"), [])
    registry_errors = validate_project_paths_registry(json.loads(inputs["project_paths"].read_text(encoding="utf-8-sig")))
    check("project_paths", "Existing artifact registry remains valid", not registry_errors, registry_errors, [])
    cases, eligibility = tables["case_registry"], tables["model_eligibility"]
    check("category_balance", "Ten paintings, two in each operational category",
          cases.groupby("category").size().to_dict() == {c: 2 for c in CATEGORIES}, cases.groupby("category").size().to_dict())
    check("no_clean_reference", "Physical inputs have no clean references or fidelity metric applicability",
          not cases.has_clean_reference.any() and not cases.reference_fidelity_metrics_applicable.any()
          and cases.clean_image_path.isna().all(), "physical-reference metrics unavailable")
    catalog = load_prompt_catalog(inputs["prompt_catalog"])
    prompts = validate_prompt_catalog(catalog, cases, manifest, config)
    for row in prompts.itertuples():
        check(f"prompt:{row.painting_id}", "One visible-context prompt bound to this exact image and reviewed mask",
              sha256_file(root / row.input_image_path) == row.input_image_sha256
              and sha256_file(root / row.mask_path) == row.mask_sha256, row.prompt_id)
    baselines = {mid: yaml.safe_load(inputs[f"models.{mid}"].read_text(encoding="utf-8-sig")) for mid in PRIMARY_MODELS}
    effective = {}
    for mid, baseline in baselines.items():
        rows = eligibility.loc[eligibility.model_id.eq(mid)]
        check(f"baseline:{mid}", "Baseline configuration bytes match D03 eligibility",
              rows.model_config_sha256.eq(sha256_file(inputs[f"models.{mid}"])).all(), len(rows), 10)
        effective[mid] = effective_model_config(baseline, mid, config)
        model = copy.deepcopy(effective[mid]["model"])
        model["configuration_id"] = baseline["model"]["configuration_id"]
        check(f"model_settings:{mid}", "Numerical model settings unchanged; SD effective identity records targeted prompts",
              model == baseline["model"], effective[mid]["model"]["configuration_id"])
    plan = build_candidate_plan(cases, eligibility, prompts, baselines, config)
    check("candidate_population", "40 primary and 30 additional SD candidates", len(plan) == 70, len(plan), 70)
    primary = plan.loc[plan.candidate_role.eq("primary")]
    check("primary_cartesian", "Every painting has one primary candidate per method",
          len(primary) == 40 and not primary.duplicated(["case_id", "model_id"]).any(), len(primary), 40)
    sd = plan.loc[plan.model_id.eq(SD_MODEL)]
    check("fixed_prompt_seed_groups", "Each painting has four seeds with exactly one prompt and negative prompt",
          len(sd) == 40 and sd.groupby("painting_id").seed.apply(lambda s: set(s) == {2026, 2027, 2028, 2029}).all()
          and sd.groupby("painting_id").prompt.nunique().eq(1).all()
          and sd.groupby("painting_id").negative_prompt.nunique().eq(1).all(), sd.uncertainty_group_id.nunique(), 10)
    check("negative_prompt", "Original SD negative prompt retained for every SD candidate",
          sd.negative_prompt.eq(baselines[SD_MODEL]["prompt_policy"]["negative_prompt"]).all(), "unchanged baseline")
    check("prompt_override_disclosed", "D03 generic policy remains historical; D04 explicitly selects targeted conditioning",
          eligibility.loc[eligibility.model_id.eq(SD_MODEL), "prompt_variant"].eq("p00_generic").all()
          and sd.prompt_variant.eq(PROMPT_VARIANT).all(), "p00_generic -> p05_real_damage_targeted in D04 only")
    check("planned_not_inferred", "Plans contain no successful inference or runtime-readiness claims",
          plan.status.eq("planned_not_executed").all() and plan.runtime_status.eq("pending_batch_2").all(), "runtime pending")
    input_checksums = {k: inventory["inventory_sha256"] if k == "inventory" else sha256_file(p) for k, p in inputs.items()}
    return dict(config=config, inputs=inputs, outputs=outputs, output_root=output,
        upstream_manifest=manifest, tables=tables, prompt_catalog=catalog, prompts=prompts,
        baseline_configs=baselines, effective_configs=effective, candidate_plan=plan,
        inventory=inventory, input_audit=input_audit, input_checksums=input_checksums,
        validation=checks, elapsed_seconds=perf_counter() - started,
        runtime_status="pending_batch_2", tokenizer_status="pending_batch_2",
        candidate_plan_status="preview_not_frozen")
