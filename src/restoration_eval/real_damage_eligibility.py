"""D03 mask geometry and input eligibility, without restoration or fake references."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd
import yaml
from PIL import Image

from .manifests import sha256_file
from .masks import calculate_mask_morphology
from .paths import notebook_output_root, require_notebook_output_path, resolve_repo_path, to_repo_relative
from .real_damage_dataset import NOTEBOOK_STEM, _require, audit_inventory_inputs, validate_binary_damage_mask, validate_review_binding
from .real_damage_preparation import _atomic_write, refresh_preparation_context
from .real_damage_review import REVIEW_STAGE, REVIEW_WORK_DIRECTORY, inference_scale_evidence
from .regions import build_standard_regions
from .validation import ValidationCollector

REAL_DAMAGE_ELIGIBILITY_MODULE_VERSION = "1.0.0"
ELIGIBILITY_STAGE = "batch_6_geometry_and_model_eligibility"


def load_eligibility_config(path: str | Path) -> dict[str, Any]:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    expected = {"config_schema_version": "real_damage_eligibility_config.v1",
                "dataset_scope": "real_damage_10", "dataset_version": "2.0.0",
                "eligibility_scope": "input_and_mask_compatibility",
                "runtime_and_weights_check_stage": "D04", "reference_fidelity_metrics_applicable": False,
                "physical_input_is_clean_reference": False, "canonical_publication_batch": 7,
                "completion_gate_batch": 8, "output_work_directory": "work/geometry_eligibility"}
    _require(all(config.get(k) == v for k, v in expected.items()), "Eligibility configuration changes the approved D03 scope")
    return config


def refresh_eligibility_context(project_root: str | Path, config_path: str | Path,
                                eligibility_config_path: str | Path, *, previous_config: Mapping[str, Any],
                                previous_input_checksums: Mapping[str, str], previous_validation: ValidationCollector) -> dict[str, Any]:
    """Add this stage's inputs while retaining the unchanged Batch 1-5 contract."""
    root = Path(project_root).resolve()
    context = refresh_preparation_context(root, config_path, previous_config=previous_config,
        previous_input_checksums={k: v for k, v in previous_input_checksums.items() if not k.startswith("eligibility.")},
        previous_validation=previous_validation)
    config = load_eligibility_config(eligibility_config_path)
    extra = {"eligibility.config": Path(eligibility_config_path).resolve(),
             **{f"eligibility.{k}": resolve_repo_path(v, root) for k, v in config["inputs"].items()}}
    _, audit = audit_inventory_inputs(root, context["inputs"]["inventory"], context["inputs"]["inventory_run"], extra)
    _require(bool(audit["passed"].all()), f"Eligibility inputs need a current inventory: {audit.loc[~audit['passed']].to_dict('records')}")
    context["inputs"].update(extra)
    context["input_checksums"].update({k: sha256_file(p) for k, p in extra.items()})
    context["input_audit"] = pd.concat([context["input_audit"], audit], ignore_index=True)
    context["eligibility_config"] = config
    return context


def assess_input_eligibility(model_id: str, *, canonical_review_status: str,
                             scale_review_status: str, inference_mask_empty: bool) -> tuple[bool, str]:
    """Eligibility is input compatibility, not successful model execution."""
    _require(model_id in {"opencv_telea", "lama", "hint_places2", "stable_diffusion_inpainting"}, "Unsupported D03 model")
    if canonical_review_status not in {"approved", "approved_with_ambiguity"}:
        return False, "canonical_mask_not_approved"
    if model_id == "stable_diffusion_inpainting":
        if inference_mask_empty:
            return False, "empty_mask_at_512"
        if scale_review_status != "accepted":
            return False, "inference_scale_review_not_accepted"
    return True, "reviewed_input_and_mask_compatible"


def _same_table(frame: pd.DataFrame, path: Path, ids: list[str]) -> None:
    _require(frame["painting_id"].tolist() == ids, f"Unexpected population/order: {path.name}")
    pd.testing.assert_frame_equal(pd.read_csv(path), pd.read_csv(io.StringIO(frame.to_csv(index=False))),
                                  check_dtype=False, check_exact=False, rtol=1e-12, atol=1e-12)


def prepare_geometry_and_eligibility(project_root: str | Path, config: Mapping[str, Any],
                                     eligibility_config: Mapping[str, Any], catalog: Mapping[str, Any],
                                     artworks: pd.DataFrame, preprocessed_images: pd.DataFrame,
                                     mask_review: pd.DataFrame, inference_mask_audit: pd.DataFrame, *,
                                     previous_validation: ValidationCollector,
                                     progress_callback: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """Prepare six handoff tables under work; publish canonical artifacts later.

    Stored previews, approvals, inputs, derived masks and numerical scale
    diagnostics must still match. Edited evidence is retained and rejected.
    Shared morphology/region helpers and the four existing model configs are
    reused unchanged. No runtime, checkpoint or GPU availability is inferred.
    """
    started = perf_counter()
    root = Path(project_root).resolve()
    prior = [c for c in previous_validation.checks if c.validation_stage == REVIEW_STAGE]
    _require(bool(prior) and all(c.passed for c in previous_validation.checks), "Successful Batch 5 validation is required")
    validation = ValidationCollector()
    validation.extend(c for c in previous_validation.checks if c.validation_stage != ELIGIBILITY_STAGE)
    output = notebook_output_root(NOTEBOOK_STEM, root)
    work = require_notebook_output_path(output / eligibility_config["output_work_directory"], NOTEBOOK_STEM, root)
    _require(work == output / "work/geometry_eligibility", "Wrong eligibility work directory")
    review_root = output / REVIEW_WORK_DIRECTORY
    decision_path = resolve_repo_path(eligibility_config["inputs"]["scale_review_decisions"], root)
    acceptance = json.loads(decision_path.read_text(encoding="utf-8"))
    ids = config["dataset"]["painting_ids"]
    _require(acceptance.get("schema_version") == "real_damage_scale_review_decisions.v1"
             and acceptance.get("dataset_version") == config["dataset"]["dataset_version"], "Wrong scale-review cohort/schema")
    _require(acceptance.get("review_basis") == "user_accepted_saved_batch_5_previews_and_resizing_effects_in_chat"
             and acceptance.get("reviewer") and acceptance.get("recorded_at_utc"), "Missing human scale-review decision")
    _require([r["painting_id"] for r in acceptance["records"]] == ids, "Scale decisions must cover the ten sources")
    actual_files = {p.relative_to(review_root).as_posix(): sha256_file(p) for p in review_root.rglob('*') if p.is_file()}
    _require(actual_files == acceptance["batch_5_files_sha256"], "Reviewed Batch 5 evidence changed; repeat the affected review")
    checkpoint = json.loads((review_root / "review_checkpoint.json").read_text(encoding="utf-8"))
    _require(checkpoint["config_content_sha256"] == acceptance["batch_5_config_content_sha256"]
             == hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(), "Batch 5 preparation policy changed")
    _require(checkpoint["helper_sha256"] == sha256_file(root / config["inputs"]["helper_sources"]["real_damage_review"]), "Batch 5 producer changed")
    _require(checkpoint["decisions_sha256"] == sha256_file(root / config["inputs"]["mask_review_decisions"]), "Canonical approval changed")
    _same_table(preprocessed_images, output / config["preparation"]["candidate_directory"] / config["preparation"]["preprocessing_checkpoint"], ids)
    _same_table(mask_review, review_root / "mask_review.csv", ids)
    _same_table(inference_mask_audit, review_root / "inference_mask_audit.csv", ids)
    _require(artworks["painting_id"].tolist() == ids and not artworks["has_clean_reference"].any()
             and not preprocessed_images["has_clean_reference"].any()
             and preprocessed_images["clean_image_path"].isna().all(), "D03 has no clean-reference inputs")

    def check(key: str, description: str, passed: bool, observed: Any, expected: Any = True) -> None:
        validation.add(validation_stage=ELIGIBILITY_STAGE, check_id=key, check_description=description,
                       severity="blocking", passed=passed, observed=observed, expected=expected)

    check("review_evidence", "Saved Batch 5 evidence and explicit resizing acceptance remain bound", True, len(actual_files), 33)
    for rel, digest in catalog["pipeline_baseline_sha256"].items():
        _require(sha256_file(root / rel) == digest, f"Shared pipeline baseline changed: {rel}")
    model_configs = {}
    for model_id in config["downstream"]["primary_models"]:
        path = resolve_repo_path(config["inputs"]["model_configs"][model_id], root)
        model_config = yaml.safe_load(path.read_text(encoding="utf-8"))
        policy = model_config["model"]["mask_threshold_policy"]["binary_missing_region"]
        _require(model_config["model"]["model_id"] == model_id and policy == {"threshold": 128, "comparison": "greater_than_or_equal"}, "Model mask policy changed")
        model_configs[model_id] = (model_config, path, sha256_file(path))
        check(f"model_baseline:{model_id}", "Existing model configuration and binary threshold are unchanged", True, model_config["model"]["configuration_id"])
    region_path = resolve_repo_path(config["inputs"]["region_config"], root)
    region_policy = yaml.safe_load(region_path.read_text(encoding="utf-8"))["regions"]
    groups = {name: [] for name in ("masks", "mask_geometry", "mask_review", "inference_mask_audit", "case_registry", "model_eligibility")}
    for geo, review, scale, decision, art in zip(preprocessed_images.to_dict('records'), mask_review.to_dict('records'),
            inference_mask_audit.to_dict('records'), acceptance['records'], artworks.to_dict('records')):
        pid = geo["painting_id"]
        _require(all(row["painting_id"] == pid for row in (review, scale, decision, art)), "Painting join is inconsistent")
        input_path = resolve_repo_path(review["input_path"], root)
        mask_path = resolve_repo_path(review["candidate_mask_path"], root)
        validate_review_binding(review, input_path=input_path, mask_path=mask_path)
        _require(review["input_sha256"] == geo["sha256"] == decision["input_sha256"] == scale["input_sha256"]
                 and review["mask_sha256"] == decision["mask_sha256"] == scale["mask_sha256"]
                 and review["input_path"] == geo["processed_path"], f"Review/input join changed: {pid}")
        _require(sha256_file(root / geo["source_path"]) == geo["source_sha256"] == art["raw_sha256"], f"Raw source changed: {pid}")
        _require(decision["scale_review_status"] in {"accepted", "rejected"}, "Scale review is not a completed human decision")
        check(f"binding:{pid}", "Accepted canonical and scale views refer to unchanged source/input/mask", True, decision["scale_review_status"])
        with Image.open(input_path) as source, Image.open(mask_path) as stored:
            _require(source.mode == 'RGB' and source.size == (768,768) and source.format == 'PNG', f"Wrong input format: {pid}")
            mask = stored.copy()
        box = tuple(int(geo[k]) for k in ('content_x_min','content_y_min','content_x_max','content_y_max'))
        binary = validate_binary_damage_mask(mask, content_box=box)
        fresh, reduced, lost = inference_scale_evidence(mask, content_box=box)
        for key, value in fresh.items():
            observed = scale[key]
            if isinstance(value, list): observed = json.loads(observed)
            equal = np.isclose(observed, value, rtol=1e-12, atol=1e-12) if isinstance(value, float) else observed == value
            _require(bool(equal), f"Scale evidence differs for {pid}: {key}")
        _require(sha256_file(root / scale['inference_mask_path']) == scale['inference_mask_sha256'] == decision['inference_mask_sha256'], f"512 mask changed: {pid}")
        with Image.open(root / scale['inference_mask_path']) as saved:
            _require(np.array_equal(np.asarray(saved), np.asarray(reduced)), f"512 mask pixels differ: {pid}")
        with Image.open(root / scale['lost_component_mask_path']) as saved:
            _require(np.array_equal(np.asarray(saved), np.asarray(lost)), f"Lost-component map differs: {pid}")
        check(f"scale_audit:{pid}", "Saved scale diagnostics and masks equal independently recalculated geometry", True, fresh['roundtrip_iou'])
        morphology = calculate_mask_morphology(mask, content_box=box)
        check(f"morphology:{pid}", "Shared morphology agrees with selected area and 8-connected component count",
              morphology['damaged_pixel_count'] == review['mask_pixel_count']
              and morphology['connected_component_count'] == scale['source_component_count']
              and morphology['padding_overlap_pixels'] == 0, morphology['damaged_pixel_count'], review['mask_pixel_count'])
        regions = build_standard_regions(binary, content_bbox=box,
            mask_bbox_margin=region_policy['mask_bbox_margin_pixels'], boundary_width_pixels=region_policy['boundary_width_pixels'],
            include_outside_boundary=True, outside_boundary_width_pixels=region_policy['outside_ring_outer_width_pixels'])
        _require(region_policy['outside_ring_inner_offset_pixels'] == region_policy['boundary_width_pixels'], "Unsupported region offset")
        region_counts = {f"{name}_pixels": region.pixel_count for name,region in regions.items()}
        check(f"regions:{pid}", "Masked and outside-mask content partition image content; boundary regions exclude padding",
              region_counts['masked_region_pixels'] + region_counts['outside_mask_content_pixels'] == geo['content_area_pixels']
              and all(not (region.mask & ~regions['content_region'].mask).any() for name,region in regions.items() if name!='full_image'), region_counts)
        identity = [config['dataset']['dataset_version'],pid,geo['source_sha256'],geo['sha256'],review['mask_sha256']]
        case_id = f"real_damage__v{config['dataset']['dataset_version'].replace('.', '_')}__{pid}__{hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:16]}"
        base = dict(dataset_id=config['dataset']['dataset_id'], dataset_version=config['dataset']['dataset_version'],
                    dataset_scope=config['dataset']['dataset_scope'], experiment_id=config['dataset']['experiment_id'],
                    painting_id=pid, category=art['category'], case_id=case_id, mask_id=review['mask_id'])
        canonical_mask = to_repo_relative(output / config['outputs']['mask_template'].format(mask_id=review['mask_id']), root)
        coverage_percent = 100 * morphology['damaged_content_fraction']
        low,high = config['annotation']['coverage_guidance_percent']
        groups['mask_geometry'].append(dict(base, schema_version=config['schemas']['mask_geometry'], **morphology, **region_counts,
            coordinate_convention='xyxy_exclusive_zero_based', region_policy_version=region_policy['policy_version'],
            region_config_sha256=sha256_file(region_path), coverage_within_guidance=low<=coverage_percent<=high,
            coverage_upper_exception_used=coverage_percent>high and pid in config['annotation']['coverage_upper_bound_exceptions']))
        accepted_review = dict(review, **base, scale_review_status=decision['scale_review_status'],
            scale_reviewer=acceptance['reviewer'], scale_reviewed_at_utc=acceptance['recorded_at_utc'],
            scale_review_basis=acceptance['review_basis'], scale_decisions_sha256=sha256_file(decision_path),
            scale_review_timestamp_basis=acceptance['review_timestamp_basis'])
        groups['mask_review'].append(accepted_review)
        groups['masks'].append(dict(base, schema_version=config['schemas']['masks'], mask_path=canonical_mask,
            candidate_mask_path=review['candidate_mask_path'], mask_sha256=review['mask_sha256'], input_path=review['input_path'],
            input_sha256=review['input_sha256'], width=768, height=768, mode='L', missing_region_value=255,
            mask_pixel_count=review['mask_pixel_count'], mask_fraction_content=review['mask_fraction_content'],
            annotation_method=review['annotation_method'], review_status=review['review_status'],
            target_description=review['target_description'], all_visible_damage_covered=False, artifact_state='pending_canonical_publication'))
        groups['case_registry'].append(dict(base, schema_version=config['schemas']['case_registry'],
            source_kind='real_damage_reviewed_mask', input_image_path=review['input_path'], input_image_sha256=review['input_sha256'],
            source_image_sha256=geo['source_sha256'], mask_or_effect_id=review['mask_id'], mask_or_effect_path=canonical_mask,
            mask_sha256=review['mask_sha256'], damage_or_degradation_type='physical_damage_selected_repair_target',
            target_description=review['target_description'], target_damage_fraction=None, realized_damage_fraction=review['mask_fraction_content'],
            has_clean_reference=False, clean_image_path=None, clean_image_sha256=None, reference_fidelity_metrics_applicable=False,
            status='prepared_pending_D03_completion', all_visible_damage_covered=False))
        sd_eligible = False
        for model_id,(model_config,model_path,digest) in model_configs.items():
            eligible,reason = assess_input_eligibility(model_id, canonical_review_status=review['review_status'],
                scale_review_status=decision['scale_review_status'], inference_mask_empty=bool(scale['empty_inference_mask']))
            is_sd = model_id=='stable_diffusion_inpainting'
            if is_sd: sd_eligible=eligible
            groups['model_eligibility'].append(dict(base, schema_version=config['schemas']['model_eligibility'], model_id=model_id,
                configuration_id=model_config['model']['configuration_id'], model_config_path=to_repo_relative(model_path,root),
                model_config_sha256=digest, eligible=eligible, eligibility_reason=reason,
                eligibility_scope='input_and_mask_compatibility', runtime_status='not_checked_D04',
                handoff_status='pending_D03_completion', input_image_path=review['input_path'], input_image_sha256=review['input_sha256'],
                mask_path=canonical_mask, mask_sha256=review['mask_sha256'], mask_threshold=128, mask_threshold_comparison='greater_than_or_equal',
                adapter_canvas_width=768, adapter_canvas_height=768, audited_mask_width=512 if is_sd else 768,
                audited_mask_height=512 if is_sd else 768, output_width=768, output_height=768,
                scale_review_status=decision['scale_review_status'] if is_sd else 'not_required',
                primary_seed=config['downstream']['primary_seed'] if is_sd else None,
                prompt_variant=config['downstream']['sd_prompt_variant'] if is_sd else None,
                has_clean_reference=False, reference_fidelity_metrics_applicable=False))
        groups['inference_mask_audit'].append(dict(scale, **base, scale_review_status=decision['scale_review_status'],
            scale_reviewer=acceptance['reviewer'], scale_reviewed_at_utc=acceptance['recorded_at_utc'],
            scale_decisions_sha256=sha256_file(decision_path), sd_eligibility_status='eligible' if sd_eligible else 'ineligible',
            sd_eligible_after_review=sd_eligible))
        if progress_callback: progress_callback(dict(painting_id=pid,completed=len(groups['case_registry']),total=len(ids),elapsed_seconds=perf_counter()-started))
    frames = {k:pd.DataFrame(v) for k,v in groups.items()}
    cases,eligible = frames['case_registry'],frames['model_eligibility']
    check('case_population','Ten distinct version/hash-bound cases, two per category', len(cases)==10 and cases.case_id.nunique()==10 and cases.groupby('category').size().eq(2).all(), len(cases), 10)
    check('eligibility_matrix','Exactly one row for each case and each of four methods', len(eligible)==40 and not eligible.duplicated(['case_id','model_id']).any() and eligible.groupby('case_id').model_id.nunique().eq(4).all(),len(eligible),40)
    check('no_clean_reference','No damaged input is relabelled as a clean reference', cases.clean_image_path.isna().all() and not cases.has_clean_reference.any() and not eligible.reference_fidelity_metrics_applicable.any(), True)
    validation.raise_for_blocking()
    payloads={work/f'{name}.csv':frame.to_csv(index=False,lineterminator='\n').encode('utf-8') for name,frame in frames.items()}
    binding={'schema_version':'real_damage_eligibility_checkpoint.v1','helper_version':REAL_DAMAGE_ELIGIBILITY_MODULE_VERSION,
        'helper_sha256':sha256_file(Path(__file__)), 'scale_decisions_sha256':sha256_file(decision_path),
        'eligibility_config_sha256':hashlib.sha256(json.dumps(eligibility_config,sort_keys=True).encode()).hexdigest(),
        'dataset_version':config['dataset']['dataset_version'],'canonical_artifacts_persisted':False,
        'completion_gate_passed':False,'runtime_status':'not_checked_D04',
        'files_sha256':{p.name:hashlib.sha256(b).hexdigest() for p,b in payloads.items()}}
    payloads[work/'eligibility_checkpoint.json']=(json.dumps(binding,indent=2)+'\n').encode('utf-8')
    existing={p for p in work.rglob('*') if p.is_file()} if work.exists() else set()
    _require(existing<=set(payloads),'Unexpected eligibility files are retained for review')
    for path,content in payloads.items():
        require_notebook_output_path(path,NOTEBOOK_STEM,root)
        _require(not path.exists() or path.read_bytes()==content,f'Existing eligibility file differs; retained: {path}')
    for path,content in payloads.items(): _atomic_write(path,content)
    check('checkpoint_files','Six prepared tables and one checkpoint are saved under work', {p for p in work.rglob('*') if p.is_file()}==set(payloads),len(payloads),7)
    validation.raise_for_blocking()
    return {**frames,'validation':validation,'work_root':work,'checkpoint_path':work/'eligibility_checkpoint.json','elapsed_seconds':perf_counter()-started}
