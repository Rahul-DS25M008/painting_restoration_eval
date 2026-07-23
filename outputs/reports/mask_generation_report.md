# Canonical Mask Generation Report

Generated at: `2026-07-23T08:20:07.450572+00:00`

## Experiment

- Experiment name: `painting_restoration_50_subset`
- Experiment version: `1.0.0`
- Configuration version: `1.1.0`
- Target image size: `768 × 768`
- Processed paintings: `50`
- Generated masks: `250`

## Generator

- Generator name: `canonical_synthetic_damage_masks`
- Generator version: `2.0.0`
- Global seed: `20260630`
- Maximum generation attempts: `30`
- Seed strategy: stable SHA-256 hierarchy using global, painting, mask, and retry seeds.

## Mask Types

| mask_type    |   target_area_pct |   min_area_pct |   max_area_pct | description                                                                    |
|:-------------|------------------:|---------------:|---------------:|:-------------------------------------------------------------------------------|
| zero_control |               0   |              0 |              0 | No damage. Used to measure unnecessary model changes or hallucination.         |
| scratch_thin |               2   |              1 |              3 | Thin elongated scratch or crack-like damage.                                   |
| loss_small   |               4.5 |              3 |              6 | Small localized irregular missing-paint regions.                               |
| loss_large   |              12.5 |             10 |             15 | Large irregular missing region representing a difficult restoration case.      |
| mixed_damage |              11.5 |              8 |             15 | Combination of scratches, irregular losses, scattered losses, and edge damage. |

## Area Statistics

| mask_type    |   count |   target_area_pct |   target_area_min_pct |   target_area_max_pct |   mean_actual_area_pct |   std_actual_area_pct |   min_actual_area_pct |   max_actual_area_pct |   mean_area_error_pct |   max_area_error_pct |   mean_actual_area_pixels |
|:-------------|--------:|------------------:|----------------------:|----------------------:|-----------------------:|----------------------:|----------------------:|----------------------:|----------------------:|---------------------:|--------------------------:|
| zero_control |      50 |               0   |                     0 |                     0 |                 0      |                0      |                0      |                0      |                0      |               0      |                      0    |
| scratch_thin |      50 |               2   |                     1 |                     3 |                 2.1363 |                0.4984 |                1.1081 |                2.9782 |                0.4296 |               0.9782 |                   9614.46 |
| loss_small   |      50 |               4.5 |                     3 |                     6 |                 4.0246 |                0.6469 |                3.0869 |                5.5021 |                0.6743 |               1.4131 |                  18175.4  |
| loss_large   |      50 |              12.5 |                    10 |                    15 |                12.3288 |                1.3686 |               10.1506 |               14.9143 |                1.1736 |               2.4143 |                  56237    |
| mixed_damage |      50 |              11.5 |                     8 |                    15 |                 9.66   |                1.3449 |                8.084  |               13.2845 |                2.0755 |               3.416  |                  43420    |

## Connected-Component Statistics

| mask_type    |   count |   mean_connected_components |   median_connected_components |   min_connected_components |   max_connected_components |   mean_largest_component_pixels |   mean_component_pixels |   mean_largest_component_fraction |   mean_component_density |   mean_component_aspect_ratio |   maximum_component_aspect_ratio |
|:-------------|--------:|----------------------------:|------------------------------:|---------------------------:|---------------------------:|--------------------------------:|------------------------:|----------------------------------:|-------------------------:|------------------------------:|---------------------------------:|
| zero_control |      50 |                        0    |                             0 |                          0 |                          0 |                            0    |                    0    |                            0      |                   0      |                        0      |                           0      |
| scratch_thin |      50 |                        6.1  |                             6 |                          3 |                         11 |                         4513.02 |                 1711.56 |                            0.4696 |                   1.349  |                        2.8847 |                          29.7    |
| loss_small   |      50 |                        5.94 |                             6 |                          3 |                          8 |                         4584.96 |                 3137.2  |                            0.2563 |                   1.3177 |                        1.2246 |                           2.7576 |
| loss_large   |      50 |                        1.12 |                             1 |                          1 |                          2 |                        51888.4  |                51717.4  |                            0.9423 |                   0.2453 |                        1.1487 |                           1.625  |
| mixed_damage |      50 |                        8.08 |                             8 |                          3 |                         13 |                        27038.3  |                 5938.01 |                            0.6221 |                   1.7741 |                        2.5839 |                         241      |

## Bounding-Box and Border Statistics

| mask_type    |   count |   mean_bbox_area_pixels |   mean_bbox_width |   mean_bbox_height |   mean_bbox_fill_ratio |   mean_bbox_aspect_ratio |   mean_minimum_distance_to_border_pixels |   touching_border_count |   touching_border_percentage |
|:-------------|--------:|------------------------:|------------------:|-------------------:|-----------------------:|-------------------------:|-----------------------------------------:|------------------------:|-----------------------------:|
| zero_control |      50 |                       0 |              0    |               0    |                 0      |                   0      |                                   nan    |                       0 |                            0 |
| scratch_thin |      50 |                  430885 |            677    |             645.6  |                 0.0226 |                   1.3101 |                                     0    |                      50 |                          100 |
| loss_small   |      50 |                  250862 |            510.04 |             495.64 |                 0.0791 |                   1.4187 |                                    31.1  |                       0 |                            0 |
| loss_large   |      50 |                  105827 |            325    |             321.62 |                 0.5605 |                   1.2031 |                                    59.68 |                       0 |                            0 |
| mixed_damage |      50 |                  441639 |            687.48 |             652.68 |                 0.0996 |                   1.3153 |                                     0    |                      50 |                          100 |

## Validation Summary

| mask_type    |   count |   generation_success_count |   saved_file_validation_success_count |   binary_success_count |   content_only_success_count |   area_tolerance_success_count |   padding_overlap_mask_count |   total_validation_issues |   generation_success_percentage |   saved_file_validation_success_percentage |   binary_success_percentage |   content_only_success_percentage |   area_tolerance_success_percentage |
|:-------------|--------:|---------------------------:|--------------------------------------:|-----------------------:|-----------------------------:|-------------------------------:|-----------------------------:|--------------------------:|--------------------------------:|-------------------------------------------:|----------------------------:|----------------------------------:|------------------------------------:|
| zero_control |      50 |                         50 |                                    50 |                     50 |                           50 |                             50 |                            0 |                         0 |                             100 |                                        100 |                         100 |                               100 |                                 100 |
| scratch_thin |      50 |                         50 |                                    50 |                     50 |                           50 |                             50 |                            0 |                         0 |                             100 |                                        100 |                         100 |                               100 |                                 100 |
| loss_small   |      50 |                         50 |                                    50 |                     50 |                           50 |                             50 |                            0 |                         0 |                             100 |                                        100 |                         100 |                               100 |                                 100 |
| loss_large   |      50 |                         50 |                                    50 |                     50 |                           50 |                             50 |                            0 |                         0 |                             100 |                                        100 |                         100 |                               100 |                                 100 |
| mixed_damage |      50 |                         50 |                                    50 |                     50 |                           50 |                             50 |                            0 |                         0 |                             100 |                                        100 |                         100 |                               100 |                                 100 |

## Generation Attempt Statistics

| mask_type    |   count |   mean_generation_attempts |   median_generation_attempts |   min_generation_attempts |   max_generation_attempts |   first_attempt_success_count |   retry_required_count |   generation_warning_count |   first_attempt_success_percentage |   retry_required_percentage |
|:-------------|--------:|---------------------------:|-----------------------------:|--------------------------:|--------------------------:|------------------------------:|-----------------------:|---------------------------:|-----------------------------------:|----------------------------:|
| zero_control |      50 |                       1    |                            1 |                         1 |                         1 |                            50 |                      0 |                          0 |                                100 |                           0 |
| scratch_thin |      50 |                       1.32 |                            1 |                         1 |                         4 |                            39 |                     11 |                          0 |                                 78 |                          22 |
| loss_small   |      50 |                       1.42 |                            1 |                         1 |                         5 |                            35 |                     15 |                          0 |                                 70 |                          30 |
| loss_large   |      50 |                       3.46 |                            2 |                         1 |                        24 |                            19 |                     31 |                          0 |                                 38 |                          62 |
| mixed_damage |      50 |                       1.78 |                            1 |                         1 |                        24 |                            39 |                     11 |                          0 |                                 78 |                          22 |

## Inventory Audit

| audit                     |   issue_rows | passed   |
|:--------------------------|-------------:|:---------|
| duplicate_case_rows       |            0 | True     |
| duplicate_mask_id_rows    |            0 | True     |
| duplicate_filename_rows   |            0 | True     |
| duplicate_path_rows       |            0 | True     |
| missing_file_rows         |            0 | True     |
| orphan_file_rows          |            0 | True     |
| missing_mask_type_rows    |            0 | True     |
| unexpected_mask_type_rows |            0 | True     |

## Validation Conclusions

- Generation-valid masks: `250` of `250`.
- Saved-file validation passes: `250` of `250`.
- Masks with padding overlap: `0`.
- Orphan PNG files: `0`.
- Missing mask files: `0`.
- Duplicate case rows: `0`.

The canonical mask set passed deterministic replay, binary-value, size, content-region, area-tolerance, metadata-consistency, completeness, and file-inventory checks.

## Generated Figures

- `outputs\figures\masks\mask_area_percentage_distribution.png`
- `outputs\figures\masks\mask_connected_component_distribution.png`
- `outputs\figures\masks\mask_bbox_fill_ratio_distribution.png`
- `outputs\figures\masks\mask_largest_component_fraction_distribution.png`
- `outputs\figures\masks\mask_border_touch_percentage.png`
- `outputs\figures\masks\mask_generation_attempts_histogram.png`
- `outputs\figures\masks\p001_canonical_mask_overlays.png`

## Canonical Outputs

- Mask metadata: `data\processed\metadata\metadata_masks.csv`
- JSON manifest: `outputs\reports\mask_generation_metadata.json`
- Area summary: `outputs\metrics\mask_area_summary_50.csv`
- Component summary: `outputs\metrics\mask_component_summary_50.csv`
- Bounding-box summary: `outputs\metrics\mask_bbox_summary_50.csv`
- Validation summary: `outputs\metrics\mask_validation_summary_50.csv`
- Generation statistics: `outputs\metrics\mask_generation_statistics.csv`
- Validation records: `outputs\metrics\mask_validation_records_50.csv`
- Inventory audit: `outputs\metrics\mask_inventory_audit_summary_50.csv`
