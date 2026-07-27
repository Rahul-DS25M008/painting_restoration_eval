# OpenCV Telea Cross-Model Handoff

Generated: 2026-07-27 15:02:13

## Purpose

This handoff package records the OpenCV Telea baseline report outputs in a standardized form so later LaMa, Stable Diffusion, and SDXL reports can be compared against the same evidence structure.

## Model Index

| model_name | model_family | report_generated_at | markdown_report_path | html_report_path | case_count | zero_control_count | nonzero_case_count | difference_map_count | datasets | mask_types | metric_families | metric_names | regions | available_evidence | unavailable_or_preliminary_evidence | interpretation_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opencv_telea | classical_inpainting_baseline | 2026-07-27 15:02:12 | D:\Masters\FH\Thesis\painting-restoration-eval\outputs\reports\opencv_telea_report_generation.md | D:\Masters\FH\Thesis\painting-restoration-eval\outputs\reports\opencv_telea_report.html | 410 | 50 | 360 | 410 | canonical, damage_size, mask_robustness, synthetic_degradation | , loss_large, loss_small, mixed_damage, scratch_thin, zero_control | classical, feature_similarity, perceptual | clip, dinov2, lpips, mae, mean_feature_similarity, mse, psnr, ssim | boundary_region, content_region, full_image, mask_bbox_crop, masked_region, outside_mask_region | consolidate_opencv_metrics, runtime_and_failure_information, region_aware_results, difference_maps, representative_cases, standardized_report_assets, avoid_final_trustworthiness_conclusion | texture_colour_seam_evidence | baseline_diagnostic_only_not_final_trustworthiness_claim |

## Evidence Manifest Summary

- Manifest rows: 24
- File-backed assets: 18
- Missing file-backed assets: 0
- In-memory evidence tables listed: 8

## Missing File Assets

_No missing file-backed assets found._

## Next Notebook Use

Use `opencv_telea_model_report_index.csv` as the OpenCV row in the future cross-model report index.

Use `opencv_telea_cross_model_evidence_manifest.csv` as the reusable evidence manifest for locating report tables, figures, representative panels, validation outputs, and report files.

This handoff still does not make a final trustworthiness claim. It only freezes the OpenCV baseline evidence in a reusable form.
