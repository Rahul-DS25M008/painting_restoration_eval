# OpenCV Telea Restoration Report

## Experiment status

**Status:** PASSED

Generated at: 2026-07-25T20:49:06.550353+00:00

## Purpose

This notebook applies the OpenCV Telea classical inpainting baseline to normalized restoration cases from the controlled-damage pipeline.

## Method

- Model name: `opencv_telea`
- Algorithm: `cv2.INPAINT_TELEA`
- Inpainting radius: `3`
- Binary mask rule: mask intensity `> 127`
- OpenCV version: `4.11.0`
- Generator: `restoration_eval.restoration_opencv` version `2.0.0`

## Included datasets

| dataset_name | required | available | resolved_path | decision |
| --- | --- | --- | --- | --- |
| canonical | True | True | data/processed/metadata/metadata_damaged_images.csv | include |
| damage_size | True | True | data/processed/metadata/metadata_damage_size_sensitivity.csv | include |
| mask_robustness | False | True | data/processed/metadata/metadata_mask_robustness.csv | include |
| synthetic_degradation | False | True | data/processed/metadata/metadata_synthetic_degradation.csv | include |

## Dataset execution summary

| dataset_name | telea_applicability | case_count | successful_cases | failed_cases | total_runtime_seconds | mean_runtime_seconds | median_runtime_seconds | minimum_runtime_seconds | maximum_runtime_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| canonical | primary | 250 | 250 | 0 | 118.216 | 0.4729 | 0.465435 | 0.269066 | 0.83025 |
| damage_size | primary | 35 | 35 | 0 | 18.097 | 0.5171 | 0.489979 | 0.321983 | 0.822646 |
| mask_robustness | primary | 75 | 75 | 0 | 35.255 | 0.4701 | 0.441835 | 0.30395 | 0.685556 |
| synthetic_degradation | supplementary | 50 | 50 | 0 | 24.471 | 0.4894 | 0.445519 | 0.295455 | 1.181796 |

## Failure summary

| dataset_name | status | issue | failure_count |
| --- | --- | --- | --- |
| all | ok |  | 0 |

## File validation summary

| dataset_name | validated_cases | passed_cases | failed_cases | existing_files | readable_files |
| --- | --- | --- | --- | --- | --- |
| canonical | 250 | 250 | 0 | 250 | 250 |
| damage_size | 35 | 35 | 0 | 35 | 35 |
| mask_robustness | 75 | 75 | 0 | 75 | 75 |
| synthetic_degradation | 50 | 50 | 0 | 50 | 50 |

## Behavior validation summary

| dataset_name | validated_cases | passed_cases | failed_cases | total_mask_area_pixels | total_changed_inside_mask | total_changed_outside_mask |
| --- | --- | --- | --- | --- | --- | --- |
| canonical | 250 | 250 | 0 | 6372340 | 6372340 | 0 |
| damage_size | 35 | 35 | 0 | 1434579 | 1434579 | 0 |
| mask_robustness | 75 | 75 | 0 | 2093429 | 2093429 | 0 |
| synthetic_degradation | 50 | 50 | 0 | 1864448 | 1861984 | 0 |

## Deterministic regeneration audit

| dataset_name | case_id | regeneration_status | checksum_matches | determinism_passed |
| --- | --- | --- | --- | --- |
| canonical | canonical__p001_loss_large | ok | True | True |
| damage_size | damage_size__p001__loss_large__size_02pct | ok | True | True |
| mask_robustness | mask_robustness__p001__loss_large__variant_01 | ok | True | True |
| synthetic_degradation | synthetic_degradation__p001__dirt_dust__mild | ok | True | True |

## Synthetic-degradation policy

Notebook 07 synthetic-degradation masks represent effect intensity rather than binary missing content. The frozen OpenCV wrapper converts them into a Telea target using `mask intensity > 127`.

These cases are treated as supplementary method-behavior diagnostics. They are not interpreted as evidence that Telea is a physically appropriate correction method for staining, fading, dirt, transparency, blur, or colour alteration.

## Representative figures

| figure_type | dataset_name | restoration_case_id | figure_path |
| --- | --- | --- | --- |
| representative_case | canonical | opencv_telea__canonical__canonical__p001_loss_large | outputs/figures/opencv_telea/representative_cases/opencv_telea__canonical__canonical__p001_loss_large.png |
| representative_case | canonical | opencv_telea__canonical__canonical__p001_zero_control | outputs/figures/opencv_telea/representative_cases/opencv_telea__canonical__canonical__p001_zero_control.png |
| representative_case | damage_size | opencv_telea__damage_size__damage_size__p001__loss_large__size_02pct | outputs/figures/opencv_telea/representative_cases/opencv_telea__damage_size__damage_size__p001__loss_large__size_02pct.png |
| representative_case | mask_robustness | opencv_telea__mask_robustness__mask_robustness__p001__loss_large__variant_01 | outputs/figures/opencv_telea/representative_cases/opencv_telea__mask_robustness__mask_robustness__p001__loss_large__variant_01.png |
| representative_case | synthetic_degradation | opencv_telea__synthetic_degradation__synthetic_degradation__p001__dirt_dust__mild | outputs/figures/opencv_telea/representative_cases/opencv_telea__synthetic_degradation__synthetic_degradation__p001__dirt_dust__mild.png |
| synthetic_degradation_supplementary | synthetic_degradation | opencv_telea__synthetic_degradation__synthetic_degradation__p001__dirt_dust__mild | outputs/figures/opencv_telea/synthetic_degradation/opencv_telea__synthetic_degradation__synthetic_degradation__p001__dirt_dust__mild_supplementary.png |
| synthetic_degradation_supplementary | synthetic_degradation | opencv_telea__synthetic_degradation__synthetic_degradation__p001__partial_transparency__mild | outputs/figures/opencv_telea/synthetic_degradation/opencv_telea__synthetic_degradation__synthetic_degradation__p001__partial_transparency__mild_supplementary.png |
| synthetic_degradation_supplementary | synthetic_degradation | opencv_telea__synthetic_degradation__synthetic_degradation__p001__water_stain__mild | outputs/figures/opencv_telea/synthetic_degradation/opencv_telea__synthetic_degradation__synthetic_degradation__p001__water_stain__mild_supplementary.png |
| synthetic_degradation_supplementary | synthetic_degradation | opencv_telea__synthetic_degradation__synthetic_degradation__p001__water_stain_dirt__moderate | outputs/figures/opencv_telea/synthetic_degradation/opencv_telea__synthetic_degradation__synthetic_degradation__p001__water_stain_dirt__moderate_supplementary.png |

## Methodological limitations

| limitation_id | scope | limitation | reporting_consequence |
| --- | --- | --- | --- |
| telea_local_interpolation | all | OpenCV Telea fills masked regions using local image information and does not infer historically verified missing content. | Treat Telea as a classical baseline rather than a conservation-grade restoration method. |
| fixed_radius | all | A fixed inpainting radius of 3 is used for every painting and damage case. | Results measure one standardized baseline configuration rather than radius optimization. |
| mask_threshold | all | All masks are binarized using intensity > 127. | Sub-threshold grayscale mask values do not participate in Telea inpainting. |
| synthetic_effect_semantics | synthetic_degradation | Notebook 07 synthetic masks encode effect intensity rather than missing-content extent. | Synthetic-degradation cases are supplementary method-behavior diagnostics and are not pooled uncritically with primary missing-content cases. |
| appearance_not_quality | validation | File and behavior validation confirm execution mechanics but do not establish visual, stylistic, semantic, or historical restoration quality. | Quality evaluation is deferred to downstream metric and case-analysis notebooks. |
| runtime_environment | runtime | Recorded runtimes depend on the current hardware, filesystem, operating system, and process load. | Runtime is descriptive for this execution environment and not a universal benchmark. |

## Canonical artifacts

- Restored images: `data/processed/restored/opencv_telea`
- Restoration metadata: `data/processed/metadata/metadata_restored_opencv_telea.csv`
- Audit CSV: `outputs/08_opencv_telea/opencv_telea_audit.csv`
- Figure directory: `outputs/figures/opencv_telea`
- JSON manifest: `outputs/reports/opencv_telea_manifest.json`
- Markdown report: `outputs/reports/opencv_telea_report.md`

## Completion statement

Notebook 08 completed successfully. All expected OpenCV Telea restorations were generated, validated, inventoried, and documented.
