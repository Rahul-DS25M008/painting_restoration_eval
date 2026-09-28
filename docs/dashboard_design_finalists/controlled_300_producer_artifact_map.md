# Controlled-300 Dashboard Producer-Artifact Map

**Status:** Pre-N34 Step 2 complete on 2026-09-28  
**UI authority:** `controlled_300_page_contracts.md`  
**Scope:** eight public rooms plus the D02 focused portrait-review subroute  
**Next gate:** remote URL, revision, checksum and missing-asset verification

## Purpose

This map binds every approved displayed image, measurement, report population
and conclusion to the repository artifact that produced it. It prevents N34
from treating illustrative mockup content as scientific evidence or from
silently substituting another painting, case, candidate, region, seed, prompt
or report.

The path and row selectors below are the scientific source of truth. N34 may
resize, crop, tile or summarize them for the web, but every derived dashboard
asset must retain these producer references and source checksums.

## Mapping states

| State | Meaning |
|---|---|
| `existing_direct` | The exact image, figure or report already exists. |
| `existing_filtered` | The display is a saved row or deterministic filter over an existing table. |
| `n34_derived_registered` | N34 must create a lightweight view from named existing evidence and register its lineage and checksum. |
| `unsupported_until_derived` | Required source information exists, but the exact display artifact was not retained and must be rebuilt before use. |

Conditional availability is orthogonal to those mapping states. A conditionally
available component still records whether its evidence is direct, filtered or
derived; the UI then shows it only when the exact active identity has that
supporting record.

Remote repositories, revisions, URLs and checksum reads are intentionally not
certified here; that is Step 3. Publication hints in this file only determine
which registry or bundle record Step 3 must verify.

## Producer-root register

Every shortened path in the room tables is relative to the named producer root
below. This keeps the tables readable without making a producer reference
ambiguous.

| Producer | Repository-relative output root |
|---|---|
| N01–N08 | `outputs/01_dataset_verification`, `outputs/02_image_preprocessing`, `outputs/03_canonical_mask_generation`, `outputs/04_canonical_damaged_image_generation`, `outputs/05_damage_size_sensitivity_dataset_generation`, `outputs/06_mask_robustness_dataset_generation`, `outputs/07_synthetic_degradation_dataset_generation`, `outputs/08_experiment_contracts_and_region_policy` |
| N09–N12 | `outputs/09_opencv_telea_restoration`, `outputs/10_lama_restoration`, `outputs/11_stable_diffusion_restoration`, `outputs/12_sdxl_feasibility_or_restoration` |
| N12A–N17 | `outputs/12a_hint_restoration`, `outputs/13_classical_metrics`, `outputs/14_lpips_metrics`, `outputs/15_feature_similarity`, `outputs/16_difference_maps_and_spatial_diagnostics`, `outputs/17_local_consistency_metrics` |
| N18–N22 | `outputs/18_diffusion_uncertainty_analysis`, `outputs/19_uncertainty_and_spatial_explanation_maps`, `outputs/20_semantic_and_structural_consistency`, `outputs/21_multi_model_comparison`, `outputs/22_damage_size_diffusion_uncertainty_extension` |
| N23–N27 | `outputs/23_damage_size_sensitivity_analysis`, `outputs/24_mask_robustness_analysis`, `outputs/25_synthetic_degradation_analysis`, `outputs/26_grouped_and_statistical_analysis`, `outputs/27_failure_taxonomy_and_trustworthiness_flags` |
| N28–N33 | `outputs/28_metric_and_region_policy_ablation`, `outputs/29_explainable_ai_and_case_retrieval`, `outputs/30_model_cards_compute_and_scalability`, `outputs/31_model_report_generation`, `outputs/32_case_and_painting_report_generation`, `outputs/33_final_evaluation_report` |
| D01 | `outputs/37_hint_mat_method_selection` |
| D02 | `outputs/d02_portrait_skin_tone_and_hand_restoration_audit` |

## Shared identity and image rules

Every interactive record is keyed by the applicable combination of
`painting_id`, `case_id`, `candidate_id`, `model_id`, `seed`,
`prompt_variant_id`, `metric_name`, `region_id` and `evidence_layer`. D02 adds
`annotation_id`, `hand_control_id`, `review_unit_id` and the user-facing
`blind_review_code`.

The common image lookup is:

| Display role | Producer and exact source |
|---|---|
| Painting metadata and provenance | N01 `outputs/01_dataset_verification/data/artworks.csv`, selected by `painting_id` |
| Clean controlled reference | N02 `outputs/02_image_preprocessing/images/clean/{painting_id}.png` |
| Canonical mask | N03 `outputs/03_canonical_mask_generation/images/masks/{painting_id}/{mask_type}.png` |
| Canonical damaged input | N04 `outputs/04_canonical_damaged_image_generation/images/damaged/{painting_id}/{mask_type}.png` |
| Case identity and routing | N08 `outputs/08_experiment_contracts_and_region_policy/data/case_registry.csv` and `model_eligibility.csv` |
| Telea restoration | N09 `images/restored/{experiment_id}/{case_id}.png` and `data/restorations.csv` |
| LaMa restoration | N10 `images/restored/{experiment_id}/{case_id}.png` and `data/restorations.csv` |
| Stable Diffusion restoration | N11 `data/candidates.csv`, using its exact `restored_path`, seed and prompt identity |
| Bounded SDXL restoration | N12 `data/candidates.csv`, shown only when `status=completed` |
| HINT restoration | N12A `images/restored/{experiment_id}/{case_id}.png` and `data/restorations.csv` |
| Candidate evidence index | N29 `outputs/29_explainable_ai_and_case_retrieval/data/explanation_cases.csv` |

## 01 — Exhibition Foyer

| Display ID | Display | Producer binding | State / handoff |
|---|---|---|---|
| `foyer.hero.p001` | Dominant *Juan de Pareja* exhibit | N02 `images/clean/p001.png`; N01 `artworks.csv`, `painting_id=p001` supplies title, artist, date, category, source and rights | `existing_direct`; current Git/LFS source |
| `foyer.scope.paintings` | 300 paintings | N01 `dataset_audit.csv`, `audit_section=summary`, `metric_name=accepted_artwork_count`; cross-check 300 accepted N01 artwork rows | `existing_filtered` |
| `foyer.scope.categories` | Five categories, 60 each | N01 `dataset_audit.csv`, distribution rows grouped by `category`; N01 `artworks.csv` is the record population | `existing_filtered` |
| `foyer.scope.cases` | 3,425 registered cases | N08 `case_registry.csv`; 1,500 canonical + 245 damage-size + 525 mask-robustness + 1,155 degradation cases | `existing_filtered` |
| `foyer.scope.methods` | Four full-scope methods plus bounded SDXL | N09, N10 and N12A `restorations.csv`; N11 and N12 `candidates.csv`; exact counts are 2,620 per full method and 35 scheduled/24 completed SDXL | `existing_filtered` |
| `foyer.route.previews` | Seven destination-room preview thumbnails and text | Use one exact artifact from each room's binding below; N34 creates small web renditions and stores the producer path/checksum | `n34_derived_registered`; no mockup painting may be used |
| `foyer.tour.frames` | One visual, takeaway and limitation per room | Visuals come from this map; takeaways and limits come from the approved page contract and N33 `thesis_tables.csv`/limitations report | `n34_derived_registered` |

The architecture, collection furniture and floor map in the approved raster are
design references only. They have no scientific producer and must not be
catalogued as evidence.

## 02 — Study Design

The production default is `p001`, selected because it has registered examples
in every study branch. Changing the painting must resolve through the same
tables and may expose only cases that actually exist.

| Display ID | Display | Producer binding | State / handoff |
|---|---|---|---|
| `study.anchor.clean` | Selected clean reference | N02 `images/clean/{painting_id}.png`; default `p001.png` | `existing_direct` |
| `study.core.conditions` | Unchanged control, scratch, small loss, large loss and mixed damage | N03 `masks.csv` plus mask images; N04 `cases.csv` plus damaged images, selected by painting and condition | `existing_direct`; five conditions, while the clean reference remains separate |
| `study.branch.damage_size` | Seven damage-size levels | N05 `data/cases.csv`, `images/masks` and `images/damaged`; 245 cases | `existing_direct`; N34 builds selector/index |
| `study.branch.mask_placement` | Five valid mask variants for three family-area conditions | N06 `data/cases.csv`, masks and damaged images; 525 cases | `existing_direct`; N34 builds selector/index |
| `study.branch.other_changes` | Procedural degradation specimens | N07 `data/cases.csv`, effect masks and degraded images; 1,155 generated cases | `existing_direct`; N34 builds selector/index |
| `study.routing.status` | Suitable for restoration testing / studied as degradation | N08 `model_eligibility.csv`, using `eligible` and `eligibility_reason` for the active case and method | `n34_derived_registered`; wording is explanatory, not a saved success label |
| `study.scope.catalogues` | 300, five conditions, 3,425 and 2,620 | N01 audit, N03/N04 design, N08 case registry and eligibility table | `existing_filtered` |
| `study.collection.drawers` | Five category drawers | N01 `artworks.csv`, grouped by the canonical category values; 60 each | `n34_derived_registered` |
| `study.notes.selection` | Selection and metadata drawer | N01 `artworks.csv`, `dataset_audit.csv` and validation | `existing_filtered`; N34 plain-language summary |
| `study.notes.preprocessing` | Preparation drawer | N02 `preprocessed_images.csv`, `preprocessing_audit.csv` and validation | `existing_filtered`; N34 plain-language summary |
| `study.notes.damage` | Mask and damage drawer | N03 `mask_protocol.md`, `mask_audit.csv`; N04 `damage_audit.csv`; N05–N07 generation audits | `existing_filtered`; N34 plain-language summary |
| `study.notes.policy` | Eligibility and region-policy drawer | N08 `evaluation_contract.md`, `case_registry.csv`, `model_eligibility.csv`, `region_policy.csv` | `existing_filtered` |
| `study.d02.plaque` | 60 screened, 45 matched cases, 20 paintings, reused restorations | D02 `portrait_screening.csv`; D02 `eligible_cases.csv` filtered by `primary_hand_eligible=True`; source candidate paths in D02 tables | `n34_derived_registered`; D02 produced no new restoration |

## 03 — Metric Framework

The curated opening is case `canonical__p018__mixed_damage`, candidate
`candidate__lama__canonical__p018__mixed_damage__c00`.

| Display ID | Display | Producer binding | State / handoff |
|---|---|---|---|
| `metric.anchor.images` | Clean, mask, damaged and LaMa result | N02 `clean/p018.png`; N03 `p018/mixed_damage.png`; N04 `p018/mixed_damage.png`; N10 `canonical__p018__mixed_damage.png` | `existing_direct` |
| `metric.anchor.signed_improvement` | Opening inspection map | N16 `images/maps/lama/spm_e5f9511cc6c7d95a/masked_signed_improvement.png`; exact index row in N16 `manifests/map_images.csv` | `existing_direct`; verified N16 diagnostics bundle is the remote candidate for Step 3 |
| `metric.lens.pixel` | MAE, MSE, PSNR | N13 `classical_metrics.csv`, `metric_family=classical_pixel` and exact `metric_name`/`region_id` | `existing_filtered` |
| `metric.lens.structure` | SSIM | N13 table, `metric_family=ssim`, `metric_name=ssim` | `existing_filtered` |
| `metric.lens.perceptual` | LPIPS AlexNet | N14 `lpips_metrics.csv`, `metric_name=lpips`, `network=alex` | `existing_filtered` |
| `metric.lens.features` | CLIP and DINOv2 cosine similarity | N15 `feature_metrics.csv`, exact feature `metric_name` and region | `existing_filtered` |
| `metric.lens.spatial` | Absolute error, signed improvement and changed-pixel fractions | N16 `spatial_diagnostics.csv` plus `map_images.csv` | `existing_filtered` / map `existing_direct` |
| `metric.lens.local` | Texture, colour and seam evidence | N17 `local_consistency.csv` and `map_images.csv`; p018 maps are `lcm_e5f9511cc6c7d95a/{texture,colour,seam}.png` | `existing_filtered` / maps `existing_direct` |
| `metric.lens.semantic` | Local semantic and structural evidence | N20 `semantic_structural_metrics.csv` and `semantic_maps.csv`; p018 panel is `images/maps/lama/candidate__lama__canonical__p018__mixed_damage__c00/semantic.png` | `existing_filtered` / map `existing_direct` |
| `metric.policy.ledger` | 13 families × 11 regions; 39 primary, 47 diagnostic, 57 prohibited | N08 `region_policy.csv`, grouped by `metric_family`, `region_id`, `compatible` and `primary_role` | `existing_filtered` |
| `metric.quality.anchors` | Eleven separate quality anchors | N21 `metric_disagreement.csv`, overall full-scope comparison rows; never merge with the N08 policy counts | `existing_filtered` |
| `metric.ui.grouped_regions` | Public grouped-region choices and availability | Deterministic mapping over N08 policy plus candidate availability in N29 | `n34_derived_registered` |

For the selected signed-improvement map, colour interpretation is metadata from
the N16 map index and the saved formula `damaged reference error - restored
reference error`; it is not inferred from the approved mockup.

## 04 — Model Gallery

The opening case is `canonical__p018__mixed_damage`.

| Display ID | Display | Producer binding | State / handoff |
|---|---|---|---|
| `models.anchor.input` | Damaged painting and mask | N04 `images/damaged/p018/mixed_damage.png`; N03 `images/masks/p018/mixed_damage.png` | `existing_direct` |
| `models.output.telea` | Telea restoration | N09 `images/restored/canonical_missing_region/canonical__p018__mixed_damage.png`; candidate `candidate__opencv_telea__canonical__p018__mixed_damage__c00` | `existing_direct` |
| `models.output.lama` | LaMa restoration | N10 equivalent path; candidate `candidate__lama__canonical__p018__mixed_damage__c00` | `existing_direct` |
| `models.output.hint` | HINT restoration | N12A equivalent path; candidate `candidate__hint_places2__canonical__p018__mixed_damage__c00` | `existing_direct`; HF Candidates publication candidate for Step 3 |
| `models.output.sd15` | Stable Diffusion restoration | N11 `canonical__p018__mixed_damage/sd15__p00__s2026__d0cd65cf894a.png` | `existing_direct` |
| `models.output.sdxl` | Conditional SDXL vitrine | N12 `canonical__p018__mixed_damage/sdxl__5d3f1bc4bed2__p00_generic__seed2026.png`; show only a completed exact row | `existing_direct`; availability is conditional; HF Candidates publication candidate for Step 3 |
| `models.records` | Method descriptions and complete records | N30 `model_cards.csv`; N31 `report_index.csv` and five HTML reports | `existing_direct` / `existing_filtered` |
| `models.conclusion.anchors` | LaMa led 10/11 separate anchors; Telea led crop SSIM | N21 `metric_disagreement.csv`, overall rows; crop-SSIM row has `anchor_id=structural_crop_ssim`, `region_id=mask_bbox_crop` | `existing_filtered`; always show no-combined-score qualifier |
| `models.runtime` | Recorded median runtimes | N09, N10, N11, N12 and N12A runtime summaries, or their lineage-preserving N30 model-card fields | `existing_filtered`; workstation-specific |
| `models.sdxl.coverage` | 35 scheduled, 24 completed, one timeout, ten skipped | N12 `candidates.csv`, grouped by `status` and failure type | `existing_filtered` |
| `models.hint.decision` | Why HINT was selected | D01 record in `outputs/37_hint_mat_method_selection/reports/selection_decision.json`, scorecard and HTML report | `existing_direct`; separate decision evidence, not a full-scope model result |
| `models.case.metric` | Optional active crop SSIM | N13 `classical_metrics.csv`, exact candidate + `metric_name=ssim` + `region_id=mask_bbox_crop` | `existing_filtered` |

## 05 — Stability Lab

The opening replay is `p018`, 20% damage size and LaMa.

| Display ID | Display | Producer binding | State / handoff |
|---|---|---|---|
| `stability.anchor.images` | Clean, 20% damaged input, mask and LaMa restoration | N02 `clean/p018.png`; N05 `images/{damaged,masks}/p018/size_20pct.png`; N10 `damage_size__p018__loss_large__size_20pct.png` | `existing_direct` |
| `stability.damage.trajectory` | Seven-level p018 LaMa spatial-error trajectory | N23 `damage_size_analysis.csv`, row family selected by `painting_id=p018`, `model_id=lama`, `analysis_kind=painting_trajectory`, `analysis_family_id=spatial_masked_error`, `metric_name=restored_error_mean`, `region_id=masked_region`, target exposure; slope row `dsa_527855f8f9ddbd91251d` | `n34_derived_registered` from exact N23/N16 rows |
| `stability.damage.summary` | 35 paintings, 245 cases, 980 candidates and damage-size findings | N05 design plus N23 `damage_size_analysis.csv`, figures and report | `existing_filtered` |
| `stability.mask.summary` | 35 paintings, 105 groups, 525 cases, 2,100 candidates and mask-placement findings | N06 design plus N24 `mask_robustness_analysis.csv`, figures and report | `existing_filtered`; N24 bulk table is a diagnostics publication candidate |
| `stability.degradation.summary` | 1,155 generated, 350 eligible, 1,400 primary and 11 bounded SDXL candidates | N07 design; N25 `degradation_analysis.csv` filtered to `dirt_dust`, `partial_transparency`, `water_stain`, `water_stain_dirt` | `existing_filtered`; N25 bulk table is a diagnostics publication candidate |
| `stability.seed.group` | p018 20% four-seed Stable Diffusion group | Seed 2026 N11 candidate `sd15__p00__s2026__bc46647b2698`; seeds 2027–2029 N22 candidates `sd15dsu__eb31376e152c1244`, `sd15dsu__b82cbfb9b3d389fc`, `sd15dsu__2b547cbdd68b2f6e`; group `ug_1de955f7e0f3d00cf0` | `existing_direct` / `existing_filtered` |
| `stability.seed.overlay` | Selected uncertainty overlay | N22 `images/uncertainty/ug_1de955f7e0f3d00cf0.png` and its map-manifest row | `existing_direct`; split N22 diagnostics bundle candidate for Step 3 |
| `stability.seed.population` | 1,025 groups, 4,100 candidates and 6,150 seed pairs | N18/N22 uncertainty tables and N26/N27 registered population summaries | `existing_filtered` |

Case-level contact sheets and compact replay charts are N34 display derivatives;
the statistical conclusions remain the saved N23–N25 results.

## 06 — Trustworthiness

The opening candidate is
`sd15__p00__s2026__29ff258ff921` for
`canonical__p002__loss_large`.

| Display ID | Display | Producer binding | State / handoff |
|---|---|---|---|
| `trust.anchor.triad` | Clean, damaged and Stable Diffusion result | N02 `clean/p002.png`; N04 `p002/loss_large.png`; N11 `canonical__p002__loss_large/sd15__p00__s2026__29ff258ff921.png` | `existing_direct` |
| `trust.anchor.peers` | Same-case Telea, LaMa, HINT and SD peers | Exact N09, N10, N12A and N11 rows for `canonical__p002__loss_large` | `existing_direct`; comparison peers are not threshold-fitting rows |
| `trust.threshold.example` | Texture-smoothing critical example | N27 `failure_assignments.csv`, row `failure_d414420486cfac9f2b57`; indicator `local_texture_error_p95`, observed 10.05327568054, critical 4.89240253210, warning 1.79237348795, region `mask_bbox_crop`, higher is worse | `existing_filtered` |
| `trust.threshold.rules` | Quantile and assignment rules | `config/evaluation/failure_taxonomy.yaml`: warning .90, critical .975, minimum fitting population 30, exclusions and fallbacks | `existing_direct` |
| `trust.flags.selected` | Six triggered flags and recommendation | N27 `trustworthiness_flags.csv`: `flag_d11ef4dd5b24221a81b0`, `flag_35370e7756e408d131b2`, `flag_8e919e5938a6a29634c4`, `flag_036f2a416f2763eb15de`, `flag_93698eb3791c43ac7699`, `flag_96a087e2b01e4a398884` | `existing_filtered`; colour flag `flag_1383445834f464de1e9d` is insufficient evidence, not a pass |
| `trust.population.summary` | N27 candidate, assignment, flag and category counts | N27 run manifest plus failure/flag tables; compact display summary must retain run ID and denominator | `n34_derived_registered`; no threshold-stratum count may be inferred from these files |
| `trust.threshold.strata` | Threshold reference population and fitting count | Rebuild deterministically from N27 inputs and `failure_taxonomy.yaml`; the original complete threshold-fit table existed only in memory | `unsupported_until_derived`; must be persisted by N34 before exact fitting counts are displayed |

N27's failure-category rule such as one critical or two warnings must not be
presented as a universal rule for every trustworthiness flag.

## D02 — Focused Portrait Review

| Display ID | Display | Producer binding | State / handoff |
|---|---|---|---|
| `d02.funnel` | 60 screened, 36 included/24 excluded, 91 annotations, 88 retained, 292 eligible records, 45 matched cases from 20 paintings and 32 review units | D02 canonical data tables and run manifest | `existing_filtered` |
| `d02.anchor.identity` | p269 HINT review R005 | `manual_anatomy_review.csv`, `blind_review_code=R005`, review unit `anatomy_review_813d89c1fcfdc670b64a`, annotation `anatomy_7726c759861cf33baba7`, control `hand_control_43e40122b45c717bc8b6`, candidate `candidate__hint_places2__canonical__p269__mixed_damage__c00` | `existing_filtered` |
| `d02.anchor.images` | Clean, damaged, mask and HINT restoration | N02 p269; N04 p269 mixed damage; N03 p269 mixed mask; N12A p269 mixed restoration | Full images `existing_direct`; review crop `[617,81,716,215]` is `n34_derived_registered` only after hashing and registration |
| `d02.anchor.difference` | Clean-versus-restored review crop | Deterministic difference of the exact N02 clean crop and N12A HINT crop for R005 | `unsupported_until_derived`; no retained canonical D02 difference image exists |
| `d02.anchor.review` | Malformed merged digits, high-confidence anatomy failure | Exact boolean fields and note in D02 `manual_anatomy_review.csv`, R005 row | `existing_filtered` |
| `d02.anchor.overlap` | 1,196 damaged hand pixels, 26.28% affected and matched 1,196-pixel control | D02 `anatomical_overlap_audit.csv`, row `anatomy_overlap_43e40122b45c717bc8b6`, and `hand_region_comparison.csv` | `existing_filtered` |
| `d02.hand.findings` | 12/12 positive penalties, 10/12 BH-supported; no one method minimized all three; 25/32 visible failures | D02 `hand_region_comparison.csv`, `manual_anatomy_review.csv`, `figures/hand_vs_control.png`, failure atlas and self-contained report | Static figures `existing_direct`; interactive aggregate table `n34_derived_registered` |
| `d02.lightness.findings` | 24 model-metric associations: zero clearly positive, three negative chroma-error associations and 21 crossing zero | D02 `skin_tone_audit.csv`, `figures/skin_tone_audit.png` and report | Static figure `existing_direct`; interactive coefficient table `n34_derived_registered` |
| `d02.r005.panel` | R005 blind-review panel to reconstruct | D02 `manual_anatomy_review.csv` retains its former path, but temporary `work/manual_review_panels/R005.png` was cleaned | `unsupported_until_derived`; regenerate from immutable inputs and register checksum |
| `d02.r005.control` | Exact matched-control print/mask | Temporary `work/hand_control_design.csv` was cleaned; canonical metric table retains `hand_control_id` and the 1,196-pixel count but not geometry | `unsupported_until_derived`; deterministically rebuild and confirm the same control ID before display |

Rendered lightness is an image property, not race, ethnicity or identity. D02
review is a bounded Codex-assisted blind review, not expert or conservator
ground truth.

## 07 — Case Explorer

The opening candidate is
`candidate__lama__canonical__p018__mixed_damage__c00`.

| Display ID | Display | Producer binding | State / handoff |
|---|---|---|---|
| `case.catalogue` | 300 paintings, 2,620 method-eligible cases and 13,879 inspectable candidates | N29 `explanation_cases.csv`; N08 case registry supplies registered/eligibility context | `existing_filtered` |
| `case.anchor.views` | Clean, damaged, mask and LaMa restoration | Exact paths stored in N29 row `explanation_e5f9511cc6c7d95a087e` | `existing_direct` |
| `case.anchor.difference` | Difference/signed-improvement/overlay views | N29 `difference_paths_json` and N16 map-manifest rows for `spm_e5f9511cc6c7d95a` | `existing_direct`; availability is conditional on an exact path |
| `case.anchor.local` | Colour, texture and seam views | N29 colour/texture/seam JSON fields and N17 `lcm_e5f9511cc6c7d95a` map-manifest rows | `existing_direct`; availability is conditional on an exact path |
| `case.anchor.semantic` | Semantic and structure view | N29 semantic paths plus N20 semantic-map index for the exact candidate | `existing_direct`; availability is conditional on an exact path |
| `case.anchor.uncertainty` | Uncertainty view | N29 `uncertainty_applicability=not_applicable_deterministic_method`; no image is rendered for LaMa | `existing_filtered`; explicit N/A state |
| `case.metric.colour` | Masked mean Delta E 2000 | N17 `local_consistency.csv`, row `lcmr_ade29e61f83f757bfee1`: 52.96292877 to 4.06613064, improvement 48.89679813 | `existing_filtered` |
| `case.metric.lpips` | Damage-crop LPIPS | N14 row `lp__124778c01f1b30a10f77`: 0.40980759 to 0.01912056, improvement 0.39068703 | `existing_filtered` |
| `case.metric.ssim` | Damage-crop SSIM | N13 row `cm__5e9144459fba36c24db0`: 0.88272215 to 0.96855812, improvement 0.08583596 | `existing_filtered` |
| `case.status` | Specialist review required; missing colour evidence | N29 opening row plus N27 `insufficient_evidence` and `manual_review_required` rows for the candidate | `existing_filtered` |
| `case.retrieval` | Ten queries and 100 neighbour rows | N29 `case_neighbors.csv` and ten `example_retrieval_panels`; DINOv2 primary, CLIP secondary | `existing_direct` / `existing_filtered` |
| `case.counterfactuals` | Fourteen controlled-change panels | N29 `figures/counterfactual_panels` and `counterfactual_panel_ids_json` | `existing_direct`; selected examples are not causal proof |
| `case.painting.report` | Painting report | N32 `painting_report_index.csv`; exact `painting_id` path, always present | `existing_direct` with exact report ID/path |
| `case.case.report` | Detailed case report | N32 `case_report_index.csv`; enabled only for 30 selected cases; p018 mixed report is exact | `existing_direct`; availability is conditional and no neighbour substitution is allowed |
| `case.provenance` | Source, rights and checksums | N01 `artworks.csv`; report indexes and producer manifests | `existing_filtered` |

## 08 — Research Archive

| Display ID | Display | Producer binding | State / handoff |
|---|---|---|---|
| `archive.scope.paintings` | 300 paintings | N01 `artworks.csv` and audit | `existing_filtered` |
| `archive.scope.stages` | N01–N33, N12A, D01 and D02 | Notebook/output manifests plus project paths; N33 itself binds 32 N01–N32 upstream run IDs | `n34_derived_registered` catalogue |
| `archive.scope.cases` | 3,425 registered cases | N08 `case_registry.csv` | `existing_filtered` |
| `archive.scope.candidates` | 13,879 inspectable candidates | N29 `explanation_cases.csv` | `existing_filtered` |
| `archive.scope.n32_reports` | 331 browsable N32 records | N32: 300 rows in `painting_report_index.csv`, 30 in `case_report_index.csv`, plus `reports/index.html` | `existing_direct` / `existing_filtered` |
| `archive.scope.model_reports` | Five model reports | N31 `report_index.csv` and five HTML files | `existing_direct` |
| `archive.scope.figures` | 24 final N33 figures | N33 `manifests/artifacts.csv`: 18 thesis plus six publication figures | `existing_direct` |
| `archive.scope.claims_limits` | 49 claims and 18 limitations | N33 `thesis_tables.csv`, `report_evidence_catalog.csv` and `limitations_and_deviations.md` | `existing_filtered` |
| `archive.n33.ledger` | Run identity, Git state, configuration, environment, checksums, validation and 32 upstream run IDs | N33 `manifests/run_manifest.json`, `artifacts.csv` and `validation/checks.csv` | `existing_direct` / `existing_filtered`; preserve recorded dirty state |
| `archive.d01.record` | Frozen HINT-versus-MAT decision | `outputs/37_hint_mat_method_selection` decision JSON, scorecard, report and manifest | `existing_direct`; separately linked, not invented as an N33 upstream key |
| `archive.n12a.record` | Inserted HINT full-production stage | N12A manifest, restoration index and report lineage | `existing_direct` |
| `archive.d02.record` | Supplemental portrait audit | D02 manifest, 16 canonical artifacts and report | `existing_direct` |
| `archive.provenance` | Source URL, rights status and raw SHA for all 300; descriptive completeness 268/32 | N01 `artworks.csv`, exact provenance and metadata columns | `existing_filtered` |
| `archive.publication.individual` | 2,653 individually published, remotely verified rows | `outputs/inventory/external_artifact_publication.csv`; do not add bundles | `existing_filtered`; Step 3 verifies every remote URI/revision/checksum |
| `archive.publication.bundles` | Verified large bundle releases | `outputs/inventory/bundled_publication_*_full.json`; keep release count and identity separate from 2,653 | `existing_direct`; Step 3 verifies remote records |
| `archive.limits` | Four drawers containing all 18 final limitations | N33 `thesis_tables.csv`, `table_id=t15_limitations`, and limitations report | `n34_derived_registered` grouping; text is existing evidence |

GitHub, Hugging Face Candidates and Hugging Face Diagnostics are mixed
per-artifact destinations. The interface must resolve the exact publication
registry or bundle record instead of assigning a whole notebook to one
provider. Zenodo remains planned and has no DOI.

## Required N34 derivations exposed by Step 2

The following are implementation inputs, not optional enhancements:

1. web renditions and thumbnails for the foyer route, with exact producer
   path and checksum lineage;
2. lightweight selector/index tables for study branches, metric availability,
   model availability and Case Explorer routing;
3. compact case-level trajectory/contact-sheet views for Stability Lab;
4. a persisted threshold-stratum table rebuilt from the exact N27 inputs and
   failure-taxonomy configuration;
5. persisted D02 hand-aggregate and lightness-association selector tables if
   the room is interactive rather than static-figure-only;
6. deterministic regeneration and registration of the R005 review panel,
   clean-versus-restored difference crop and exact matched-control geometry;
   and
7. archive catalogue rows that keep individual publications, bundle releases
   and Git artifacts distinct.

No dashboard element may become available merely because a nearby file exists.
Availability must be established by the exact identity and source row recorded
in the final N34 asset manifest.
