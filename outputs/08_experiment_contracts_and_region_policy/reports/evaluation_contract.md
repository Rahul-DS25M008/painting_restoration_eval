# Evaluation Contract and Region Policy

## Status and scope

- Notebook: `08_experiment_contracts_and_region_policy`
- Dataset: `painting_restoration_eval`
- Dataset version: `1.0.0`
- Dataset scope: `controlled_50`
- Contract configuration: `evaluation_contract_config.v1`
- Contract version: `1.0.0`
- Eligibility policy: `model_eligibility_policy.v1`
- Region policy: `evaluation_region_policy.v1`
- Experiment-contract helper: `1.0.0`
- Canonical-region helper: `1.1.0`
- Normalized cases: `525`
- Model decisions: `2100`
- Metric-region decisions: `143`

This report defines the authoritative experimental routing and spatial
evaluation contract for Notebooks 09-35.

## Interpretation boundary

Visual plausibility is not equivalent to historical correctness,
conservation approval, or restoration trustworthiness.

The framework evaluates algorithmic outputs under controlled synthetic
missing-region damage and controlled procedural degradation. It does
not certify a restoration for conservation use, infer artist intent,
establish historical authenticity, or replace expert human review.

No universal trust score is defined. Reference fidelity, perceptual
similarity, feature-space consistency, texture, colour, seam,
outside-mask alteration, semantic evidence, and uncertainty remain
distinct forms of evidence.

## Normalized case registry

The registry contains only stable cross-experiment identifiers, paths,
core case semantics, damage/effect fractions, source-manifest lineage,
and status. Experiment-specific generation details remain in their
source tables.

Every accepted case traces to exactly one immediate source run manifest.

| experiment_id            |   case_count |   painting_count |   input_file_count |   mask_or_effect_file_count |
|:-------------------------|-------------:|-----------------:|-------------------:|----------------------------:|
| canonical_missing_region |          250 |               50 |                250 |                         250 |
| damage_size_sensitivity  |           35 |                5 |                 35 |                          35 |
| mask_robustness          |           75 |                5 |                 75 |                          75 |
| synthetic_degradation    |          165 |                5 |                165 |                         165 |

The normalized registry contains:

- 360 binary missing-region cases;
- 165 synthetic-degradation cases;
- 50 canonical zero controls;
- 525 unique case identifiers;
- repository-relative clean, input, and mask/effect paths.

Zero controls are explicit identity/no-op controls. Empty target,
bounding-box, and boundary regions are valid expected states for these
cases rather than missing data.

## Model eligibility and restoration semantics

Methodological eligibility is recorded independently for every
`(case_id, model_id)` combination. Runtime availability, installed
weights, hardware availability, execution success, and model
feasibility are separate from methodological eligibility.

| model_id                    |   decision_count |   eligible_count |   painting_count |   experiment_count |   ineligible_count |
|:----------------------------|-----------------:|-----------------:|-----------------:|-------------------:|-------------------:|
| lama                        |              525 |              410 |               50 |                  4 |                115 |
| opencv_telea                |              525 |              410 |               50 |                  4 |                115 |
| sdxl_inpainting             |              525 |              410 |               50 |                  4 |                115 |
| stable_diffusion_inpainting |              525 |              410 |               50 |                  4 |                115 |

The eligibility table contains one explicit decision for each of four
model identities and each of 525 cases.

| eligible   | input_semantics                                 | mask_semantics                                                            | restoration_objective                                                          |   decision_count |   model_count |
|:-----------|:------------------------------------------------|:--------------------------------------------------------------------------|:-------------------------------------------------------------------------------|-----------------:|--------------:|
| True       | rgb_image_with_synthetic_missing_content        | binary_missing_region_mask; foreground >= 128                             | reconstruct deliberately removed painting content                              |             1240 |             4 |
| True       | rgb_image_with_controlled_synthetic_degradation | grayscale_effect_intensity; restoration target >= source active_threshold | supplementary masked-removal diagnostic; not a physical conservation treatment |              200 |             4 |
| True       | rgb_image_with_synthetic_missing_content        | binary_missing_region_mask; foreground >= 128                             | identity/no-op control; preserve the input exactly                             |              200 |             4 |
| False      | rgb_image_with_controlled_synthetic_degradation | grayscale_effect_intensity; restoration target >= source active_threshold | supplementary masked-removal diagnostic; not a physical conservation treatment |              460 |             4 |

All binary missing-region cases are eligible for inpainting evaluation.
For non-binary synthetic degradations, only localized water stain, dirt
and dust, partial transparency, and combined water stain/dirt cases are
eligible for supplementary masked-removal diagnostics.

That supplementary objective is not a physical conservation treatment
and must not be presented as one.

| degradation_family    |   source_case_count | expected_eligible   | policy_group                      | configured_reason                                                                                |
|:----------------------|--------------------:|:--------------------|:----------------------------------|:-------------------------------------------------------------------------------------------------|
| dirt_dust             |                  15 | True                | eligible_supplementary_inpainting | Approved supplementary localized degradation diagnostic.                                         |
| discolouration        |                  15 | False               | colour_or_tonal_change            | Tonal or colour change is not a missing-region inpainting problem.                               |
| fading                |                  15 | False               | colour_or_tonal_change            | Tonal or colour change is not a missing-region inpainting problem.                               |
| fading_discolouration |                   5 | False               | colour_or_tonal_change            | Tonal or colour change is not a missing-region inpainting problem.                               |
| gaussian_blur         |                  15 | False               | blur_or_defocus                   | Blur or defocus is not missing content and requires a degradation-specific correction objective. |
| gaussian_blur_fading  |                   5 | False               | blur_or_defocus                   | Blur or defocus is not missing content and requires a degradation-specific correction objective. |
| local_darkening       |                  15 | False               | colour_or_tonal_change            | Tonal or colour change is not a missing-region inpainting problem.                               |
| local_defocus         |                  15 | False               | blur_or_defocus                   | Blur or defocus is not missing content and requires a degradation-specific correction objective. |
| motion_blur           |                  15 | False               | blur_or_defocus                   | Blur or defocus is not missing content and requires a degradation-specific correction objective. |
| partial_transparency  |                  15 | True                | eligible_supplementary_inpainting | Approved supplementary localized degradation diagnostic.                                         |
| pigment_bleeding      |                  15 | False               | pigment_transport                 | Pigment bleeding is a colour/structure transport effect, not removable missing content.          |
| water_stain           |                  15 | True                | eligible_supplementary_inpainting | Approved supplementary localized degradation diagnostic.                                         |
| water_stain_dirt      |                   5 | True                | eligible_supplementary_inpainting | Approved supplementary localized degradation diagnostic.                                         |

Ineligible cases remain in the eligibility table with explicit reasons;
they are not silently discarded.

## Canonical region definitions

All spatial regions are constructed by the single authoritative
`src/restoration_eval/regions.py` helper.

| region_id             | region_type        | spatial_support   | case_semantics        | parameters_json                                                            | threshold_policy                     |
|:----------------------|:-------------------|:------------------|:----------------------|:---------------------------------------------------------------------------|:-------------------------------------|
| full_image            | full_image         | rectangle         | all_cases             | {}                                                                         | not_applicable                       |
| content_region        | content            | rectangle         | all_cases             | {}                                                                         | not_applicable                       |
| masked_region         | mask               | irregular_pixels  | mask_or_effect        | {}                                                                         | >= 128 for binary masks              |
| mask_bbox_crop        | mask_bbox          | rectangle         | mask_or_effect        | {"margin_pixels":8}                                                        | >= 128 for binary masks              |
| inner_boundary_band   | boundary           | irregular_pixels  | mask_or_effect        | {"width_pixels":3}                                                         | >= 128 for binary masks              |
| outer_boundary_band   | boundary           | irregular_pixels  | mask_or_effect        | {"width_pixels":3}                                                         | >= 128 for binary masks              |
| boundary_ring         | boundary           | irregular_pixels  | mask_or_effect        | {"width_pixels":3}                                                         | >= 128 for binary masks              |
| outside_mask_content  | outside_mask       | irregular_pixels  | mask_or_effect        | {}                                                                         | >= 128 for binary masks              |
| outside_boundary_ring | outside_boundary   | irregular_pixels  | mask_or_effect        | {"inner_offset_pixels":3,"outer_width_pixels":8}                           | >= 128 for binary masks              |
| degradation_support   | degradation_effect | irregular_pixels  | synthetic_degradation | {}                                                                         | source support_threshold (inclusive) |
| patch_window          | patch              | rectangle         | all_cases             | {"minimum_content_fraction":0.5,"patch_size":[224,224],"stride":[112,112]} | not_applicable                       |

The approved spatial parameters are:

- binary mask foreground: values greater than or equal to
  `128`;
- mask bounding-box margin: `8` pixels;
- inner boundary width: `3` pixels;
- outer boundary width: `3` pixels;
- symmetric boundary ring: union of the disjoint inner and outer bands;
- outside spillover ring: pixels from
  `3` through
  `8` pixels outside the mask, excluding the
  immediate outer band;
- patch size: `224 x 224`;
- patch stride: `112 x 112`;
- minimum patch content fraction:
  `0.50`;
- mask crops, boundaries, outside-mask regions, and patch support are
  clipped to permitted painting-content support.

For synthetic degradations, effect support and active support are
distinct:

1. degradation support uses the inclusive source
   `support_threshold`;
2. active support uses the inclusive source `active_threshold`;
3. active support must remain inside degradation support;
4. the grayscale effect mask remains an operator-influence record, not
   a physical conservation annotation.

## Representative validation

The region helper was applied to all 525 normalized cases. This created
4,890 applicable case-region records:

- nine standard regions for every case;
- one additional degradation-support region for each of the 165
  synthetic-degradation cases.

The patch-window contract was additionally validated on the balanced
five-painting synthetic cohort.

The methodology figure uses the following cases selected before
rendering:

| case_id                                                       | selection_role        | selection_rule                                        | experiment_id            | painting_id   | damage_or_degradation_type   |   realized_damage_fraction |
|:--------------------------------------------------------------|:----------------------|:------------------------------------------------------|:-------------------------|:--------------|:-----------------------------|---------------------------:|
| canonical__p001__zero_control                                 | zero_control          | Pinned p001 canonical empty-mask control.             | canonical_missing_region | p001          | binary_missing_region        |                  0         |
| canonical__p001__scratch_thin                                 | thin_irregular_mask   | Pinned p001 canonical thin-scratch geometry.          | canonical_missing_region | p001          | binary_missing_region        |                  0.0217171 |
| canonical__p001__loss_large                                   | compact_large_mask    | Pinned p001 canonical large-loss geometry.            | canonical_missing_region | p001          | binary_missing_region        |                  0.13903   |
| damage_size__p001__loss_large__size_20pct                     | large_damage_fraction | Largest p001 damage-size target, then stable case ID. | damage_size_sensitivity  | p001          | binary_missing_region        |                  0.2       |
| mask_robustness__p001__loss_large__target_12p5pct__variant_01 | robustness_geometry   | Lexicographically first p001 mask-robustness case.    | mask_robustness          | p001          | binary_missing_region        |                  0.125     |
| synthetic_degradation__p001__water_stain__moderate            | localized_soft_effect | Pinned moderate localized water-stain support.        | synthetic_degradation    | p001          | water_stain                  |                  0.417262  |
| synthetic_degradation__p001__gaussian_blur__moderate          | full_content_effect   | Pinned moderate full-content Gaussian-blur support.   | synthetic_degradation    | p001          | gaussian_blur                |                  1         |

The selection rules are explicit to reduce cherry-picking. The figure
also displays the complete 13-by-11 metric-region policy.

## Metric-region compatibility

Every combination of 13 metric families and 11 canonical region
identities is retained as an explicit primary, diagnostic, or
prohibited decision.

| metric_family          |   compatible_regions |   primary_regions |   diagnostic_regions |   prohibited_regions |
|:-----------------------|---------------------:|------------------:|---------------------:|---------------------:|
| classical_pixel        |                   11 |                 5 |                    6 |                    0 |
| clip                   |                    4 |                 2 |                    2 |                    7 |
| colour                 |                   11 |                 5 |                    6 |                    0 |
| dinov2                 |                    4 |                 2 |                    2 |                    7 |
| lpips                  |                    4 |                 2 |                    2 |                    7 |
| seam                   |                    4 |                 2 |                    2 |                    7 |
| semantic_patch         |                    4 |                 3 |                    1 |                    7 |
| spatial_diagnostics    |                   11 |                 4 |                    7 |                    0 |
| ssim                   |                    4 |                 2 |                    2 |                    7 |
| texture_descriptor     |                    4 |                 3 |                    1 |                    7 |
| texture_map            |                   10 |                 3 |                    7 |                    1 |
| uncertainty_perceptual |                    4 |                 2 |                    2 |                    7 |
| uncertainty_pixelwise  |                   11 |                 4 |                    7 |                    0 |

The compact matrix below uses `P` for primary, `D` for diagnostic, and
`-` for prohibited.

| metric_family          | full_image   | content_region   | masked_region   | mask_bbox_crop   | inner_boundary_band   | outer_boundary_band   | boundary_ring   | outside_mask_content   | outside_boundary_ring   | degradation_support   | patch_window   |
|:-----------------------|:-------------|:-----------------|:----------------|:-----------------|:----------------------|:----------------------|:----------------|:-----------------------|:------------------------|:----------------------|:---------------|
| classical_pixel        | D            | P                | P               | P                | D                     | D                     | P               | P                      | D                       | D                     | D              |
| ssim                   | D            | P                | -               | P                | -                     | -                     | -               | -                      | -                       | -                     | D              |
| lpips                  | D            | P                | -               | P                | -                     | -                     | -               | -                      | -                       | -                     | D              |
| clip                   | D            | P                | -               | P                | -                     | -                     | -               | -                      | -                       | -                     | D              |
| dinov2                 | D            | P                | -               | P                | -                     | -                     | -               | -                      | -                       | -                     | D              |
| spatial_diagnostics    | D            | P                | P               | D                | D                     | D                     | P               | P                      | D                       | D                     | D              |
| texture_descriptor     | D            | P                | -               | P                | -                     | -                     | -               | -                      | -                       | -                     | P              |
| texture_map            | -            | D                | P               | D                | D                     | D                     | P               | P                      | D                       | D                     | D              |
| colour                 | D            | P                | P               | P                | D                     | D                     | P               | P                      | D                       | D                     | D              |
| seam                   | -            | -                | -               | -                | D                     | D                     | P               | -                      | P                       | -                     | -              |
| uncertainty_pixelwise  | D            | D                | P               | P                | D                     | D                     | P               | P                      | D                       | D                     | D              |
| uncertainty_perceptual | D            | P                | -               | P                | -                     | -                     | -               | -                      | -                       | -                     | D              |
| semantic_patch         | D            | P                | -               | P                | -                     | -                     | -               | -                      | -                       | -                     | P              |

### Refined local comparison policy

| metric_family   | region_id             | compatible   | primary_role   | compatibility_reason                                                 |
|:----------------|:----------------------|:-------------|:---------------|:---------------------------------------------------------------------|
| classical_pixel | masked_region         | True         | primary        | Approved for this metric family under the declared region semantics. |
| ssim            | mask_bbox_crop        | True         | primary        | Approved for this metric family under the declared region semantics. |
| lpips           | mask_bbox_crop        | True         | primary        | Approved for this metric family under the declared region semantics. |
| clip            | mask_bbox_crop        | True         | primary        | Approved for this metric family under the declared region semantics. |
| dinov2          | mask_bbox_crop        | True         | primary        | Approved for this metric family under the declared region semantics. |
| seam            | boundary_ring         | True         | primary        | Approved for this metric family under the declared region semantics. |
| seam            | outside_boundary_ring | True         | primary        | Approved for this metric family under the declared region semantics. |

The refined local comparison therefore uses:

- exact masked pixels for local MAE, MSE, PSNR, and related pixelwise
  diagnostics;
- mask bounding-box crops for SSIM, LPIPS, CLIP, and DINOv2;
- immediate boundary rings and outside spillover rings for seam
  diagnostics;
- outside-mask content for unintended-edit diagnostics.

Sparse masked-pixel SSIM is prohibited. SSIM requires an image-like
rectangular support and must not be computed on flattened or sparse
masked pixels merely to populate a result column.

The same image-like restriction applies to LPIPS, CLIP, DINOv2,
texture descriptors, perceptual uncertainty, and semantic patch
metrics where configured.

## Notebook 27 region-policy alternatives

Notebook 27 receives seven declared alternatives for region ablation.
An ablation never makes a mathematically incompatible metric-region
combination valid.

| ablation_policy_id        |   configured_region_count | configured_regions                                                                                                                                                                                 |   metric_region_rows |   compatible_metric_region_rows |   metric_family_count |
|:--------------------------|--------------------------:|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------:|--------------------------------:|----------------------:|
| boundary_regions          |                         4 | inner_boundary_band, outer_boundary_band, boundary_ring, outside_boundary_ring                                                                                                                     |                   52 |                              24 |                    13 |
| complete_approved_policy  |                        11 | full_image, content_region, masked_region, mask_bbox_crop, inner_boundary_band, outer_boundary_band, boundary_ring, outside_mask_content, outside_boundary_ring, degradation_support, patch_window |                  143 |                              86 |                    13 |
| content_region_only       |                         1 | content_region                                                                                                                                                                                     |                   13 |                              12 |                    13 |
| full_image_only           |                         1 | full_image                                                                                                                                                                                         |                   13 |                              11 |                    13 |
| mask_bbox_only            |                         1 | mask_bbox_crop                                                                                                                                                                                     |                   13 |                              12 |                    13 |
| masked_pixels_where_valid |                         2 | masked_region, degradation_support                                                                                                                                                                 |                   26 |                              10 |                    13 |
| outside_mask_only         |                         2 | outside_mask_content, outside_boundary_ring                                                                                                                                                        |                   26 |                              11 |                    13 |

The complete approved policy preserves all eleven canonical region
identities. Restricted ablations change spatial scope transparently
without creating a universal trust score.

## Input contract

| input_key                             | producer                                      | relative_path                                                                     | required   | format   | schema_version                 |   expected_cardinality | applicability            |
|:--------------------------------------|:----------------------------------------------|:----------------------------------------------------------------------------------|:-----------|:---------|:-------------------------------|-----------------------:|:-------------------------|
| evaluation_contract_config            | project configuration                         | config/experiments/evaluation_contract.yaml                                       | True       | yaml     | evaluation_contract_config.v1  |                      1 | all_cases                |
| project_inventory                     | tools/build_project_inventory.py              | outputs/inventory/project_file_inventory.csv                                      | True       | csv      | project_file_inventory.v1      |                  11129 | repository               |
| inventory_run                         | tools/build_project_inventory.py              | outputs/inventory/inventory_run.json                                              | True       | json     | inventory_run.v1               |                      1 | repository               |
| project_paths_registry                | validated notebook handoffs                   | outputs/inventory/project_paths.json                                              | True       | json     | project_paths.v1               |                      1 | repository               |
| preprocessed_geometry                 | 02_image_preprocessing                        | outputs/02_image_preprocessing/data/preprocessed_images.csv                       | True       | csv      | preprocessed_images.v1         |                     50 | all_cases                |
| canonical_masks                       | 03_canonical_mask_generation                  | outputs/03_canonical_mask_generation/data/masks.csv                               | True       | csv      | canonical_masks.v1             |                    250 | canonical_missing_region |
| canonical_missing_region_cases        | 04_canonical_damaged_image_generation         | outputs/04_canonical_damaged_image_generation/data/cases.csv                      | True       | csv      | canonical_damage_cases.v1      |                    250 | canonical_missing_region |
| canonical_missing_region_run_manifest | 04_canonical_damaged_image_generation         | outputs/04_canonical_damaged_image_generation/manifests/run_manifest.json         | True       | json     | run_manifest.v1                |                      1 | canonical_missing_region |
| damage_size_sensitivity_cases         | 05_damage_size_sensitivity_dataset_generation | outputs/05_damage_size_sensitivity_dataset_generation/data/cases.csv              | True       | csv      | damage_size_cases.v1           |                     35 | damage_size_sensitivity  |
| damage_size_sensitivity_run_manifest  | 05_damage_size_sensitivity_dataset_generation | outputs/05_damage_size_sensitivity_dataset_generation/manifests/run_manifest.json | True       | json     | run_manifest.v1                |                      1 | damage_size_sensitivity  |
| mask_robustness_cases                 | 06_mask_robustness_dataset_generation         | outputs/06_mask_robustness_dataset_generation/data/cases.csv                      | True       | csv      | mask_robustness_cases.v1       |                     75 | mask_robustness          |
| mask_robustness_run_manifest          | 06_mask_robustness_dataset_generation         | outputs/06_mask_robustness_dataset_generation/manifests/run_manifest.json         | True       | json     | run_manifest.v1                |                      1 | mask_robustness          |
| synthetic_degradation_cases           | 07_synthetic_degradation_dataset_generation   | outputs/07_synthetic_degradation_dataset_generation/data/cases.csv                | True       | csv      | synthetic_degradation_cases.v1 |                    165 | synthetic_degradation    |
| synthetic_degradation_run_manifest    | 07_synthetic_degradation_dataset_generation   | outputs/07_synthetic_degradation_dataset_generation/manifests/run_manifest.json   | True       | json     | run_manifest.v1                |                      1 | synthetic_degradation    |

## Output and downstream contract

| output_key          | relative_path                                                                    | format   | schema_version               |   expected_cardinality | downstream_consumers                        |
|:--------------------|:---------------------------------------------------------------------------------|:---------|:-----------------------------|-----------------------:|:--------------------------------------------|
| case_registry       | outputs/08_experiment_contracts_and_region_policy/data/case_registry.csv         | csv      | case_registry.v1             |                    525 | Notebooks 09-35                             |
| model_eligibility   | outputs/08_experiment_contracts_and_region_policy/data/model_eligibility.csv     | csv      | model_eligibility.v1         |                   2100 | Notebooks 09-12 and all later analyses      |
| region_policy       | outputs/08_experiment_contracts_and_region_policy/data/region_policy.csv         | csv      | region_policy.v1             |                    143 | Notebooks 13-35                             |
| schema_registry     | outputs/08_experiment_contracts_and_region_policy/data/schema_registry.json      | json     | schema_registry.v1           |                      1 | Notebooks 09-35                             |
| region_definitions  | outputs/08_experiment_contracts_and_region_policy/figures/region_definitions.png | png      | figure.region_definitions.v1 |                      1 | thesis and dashboard                        |
| evaluation_contract | outputs/08_experiment_contracts_and_region_policy/reports/evaluation_contract.md | markdown | evaluation_contract.v1       |                      1 | thesis, dashboard, and downstream notebooks |
| validation_checks   | outputs/08_experiment_contracts_and_region_policy/validation/checks.csv          | csv      | validation_checks.v1         |                      1 | all downstream consumers                    |
| artifact_manifest   | outputs/08_experiment_contracts_and_region_policy/manifests/artifacts.csv        | csv      | artifact_manifest.v1         |                      7 | inventory and downstream notebooks          |
| run_manifest        | outputs/08_experiment_contracts_and_region_policy/manifests/run_manifest.json    | json     | run_manifest.v1              |                      1 | inventory and downstream notebooks          |

Downstream notebooks must consume the declared normalized artifacts
rather than scanning folders for plausible files.

Restoration notebooks must:

1. join cases by stable `case_id`;
2. join routing decisions by `(case_id, model_id)`;
3. skip ineligible execution routes with the recorded reason;
4. preserve zero controls as identity/no-op controls;
5. keep synthetic-degradation diagnostics distinct from missing-content
   restoration claims;
6. record runtime availability separately from methodological
   eligibility.

Metric notebooks must:

1. join the policy by `(metric_family, region_id)`;
2. reject prohibited combinations;
3. preserve region identifiers and threshold semantics;
4. use image-like rectangular support where required;
5. avoid reconstructing region masks with notebook-local logic.

## Validation evidence

Before this report was written:

- 525 cases passed registry and path validation;
- 2,100 model decisions passed schema and routing validation;
- 143 metric-region decisions passed compatibility validation;
- all 525 mask/effect files reloaded with canonical geometry;
- all exact support remained inside painting content;
- all mask crops remained inside content and contained their masks;
- all inner, outer, symmetric, and spillover relationships passed;
- all five patch-cohort paintings produced valid deterministic windows;
- all seven rule-selected representative payloads were available;
- 91 cumulative blocking checks had passed.

The normalized tables and consolidated validation evidence are
persisted and independently reloaded in Batch 7.

## Limitations

1. Region geometry is algorithmically defined and is not expert
   conservation annotation.
2. Boundary width, crop margin, effect thresholds, patch size, and
   stride are declared analysis parameters rather than physical
   properties of a painting.
3. Synthetic missing regions and procedural degradations simplify
   real deterioration processes.
4. A model being methodologically eligible does not mean that its
   runtime is available or that its result will be trustworthy.
5. Supplementary degradation inpainting does not represent a physical
   conservation intervention.
6. Pixelwise, perceptual, feature, texture, colour, seam, semantic, and
   uncertainty metrics each expose limited evidence.
7. Metric agreement does not establish historical correctness.
8. Metric disagreement must remain visible rather than being hidden by
   a universal aggregate score.
9. The controlled-50 dataset and balanced five-painting subsets do not
   represent the full distribution of artists, periods, materials,
   techniques, or conservation conditions.
10. Human conservation review remains necessary for real-world
    interpretation.

## Methodological conclusion

This contract separates case identity, methodological model routing,
spatial support, and metric compatibility into explicit normalized
handoffs. It prevents invalid restoration routes and prohibited
metric-region computations from being inferred implicitly by later
notebooks.

Visual plausibility remains evidence for inspection, not evidence of
historical or restoration trustworthiness.
