# Notebook 14 - LaMa Restoration Report

## Scope

This notebook applies LaMa restoration to the eligible restoration cases prepared upstream.

Processed case families:

- `canonical`
- `damage_size`
- `mask_robustness`
- `synthetic_degradation`

## Inputs

- Canonical metadata: `data/processed/metadata/metadata_damaged_images.csv`
- Damage-size metadata: `data/processed/metadata/metadata_damage_size_sensitivity.csv`
- Mask-robustness metadata: `data/processed/metadata/metadata_mask_robustness.csv`
- Synthetic-degradation metadata: `data/processed/metadata/metadata_synthetic_degradation.csv`

## Outputs

- Main LaMa restoration metadata: `data/processed/metadata/metadata_restored_lama.csv`
- Consolidated audit table: `outputs/14_lama_restoration/lama_restoration_audit.csv`
- Figure manifest: `outputs/figures/lama/lama_figure_manifest.csv`
- JSON manifest: `outputs/reports/lama_restoration_manifest.json`
- Restored image root: `data/processed/restored/lama`

## Execution Summary

- Expected eligible cases: `410`
- Restored metadata rows: `410`
- Successful cases: `410`
- Failed cases: `0`
- Total runtime seconds: `525.94`
- Total runtime minutes: `8.77`
- Total retries: `0`
- Requested device: `cuda`
- Effective device: `cuda`
- IOPaint model: `lama`

## Dataset Summary

| dataset_name          |   input_cases |   successful_cases |   failed_cases |   total_runtime_seconds |   mean_runtime_seconds |   median_runtime_seconds |   max_runtime_seconds |   total_retries |
|:----------------------|--------------:|-------------------:|---------------:|------------------------:|-----------------------:|-------------------------:|----------------------:|----------------:|
| canonical             |           250 |                250 |              0 |                292.188  |                1.16875 |                  1.46094 |               1.46094 |               0 |
| damage_size           |            35 |                 35 |              0 |                 51.1328 |                1.46094 |                  1.46094 |               1.46094 |               0 |
| mask_robustness       |            75 |                 75 |              0 |                109.57   |                1.46094 |                  1.46094 |               1.46094 |               0 |
| synthetic_degradation |            50 |                 50 |              0 |                 73.0469 |                1.46094 |                  1.46094 |               1.46094 |               0 |

## Runtime Summary

| dataset_name          |   case_count |   total_runtime_seconds |   mean_runtime_seconds |   median_runtime_seconds |   max_runtime_seconds |   total_retries |
|:----------------------|-------------:|------------------------:|-----------------------:|-------------------------:|----------------------:|----------------:|
| canonical             |          250 |                292.188  |                1.16875 |                  1.46094 |               1.46094 |               0 |
| damage_size           |           35 |                 51.1328 |                1.46094 |                  1.46094 |               1.46094 |               0 |
| mask_robustness       |           75 |                109.57   |                1.46094 |                  1.46094 |               1.46094 |               0 |
| synthetic_degradation |           50 |                 73.0469 |                1.46094 |                  1.46094 |               1.46094 |               0 |

## Audit Summary

| notebook            | model_name   | generated_at_utc                 | audit_section         | check                       | observed                                                                 | expected                                                                 | passed   |
|:--------------------|:-------------|:---------------------------------|:----------------------|:----------------------------|:-------------------------------------------------------------------------|:-------------------------------------------------------------------------|:---------|
| 14_lama_restoration | lama         | 2026-07-27T23:01:04.055449+00:00 | restoration_execution | total_rows                  | 410                                                                      | >=1                                                                      | True     |
| 14_lama_restoration | lama         | 2026-07-27T23:01:04.055449+00:00 | restoration_execution | failed_rows                 | 0                                                                        | 0                                                                        | True     |
| 14_lama_restoration | lama         | 2026-07-27T23:01:04.055449+00:00 | restoration_execution | dataset_names               | ['canonical', 'damage_size', 'mask_robustness', 'synthetic_degradation'] | ['canonical', 'damage_size', 'mask_robustness', 'synthetic_degradation'] | True     |
| 14_lama_restoration | lama         | 2026-07-27T23:01:04.055449+00:00 | file_validation       | failed_file_validations     | 0                                                                        | 0                                                                        | True     |
| 14_lama_restoration | lama         | 2026-07-27T23:01:04.055449+00:00 | behavior_validation   | failed_behavior_validations | 0                                                                        | 0                                                                        | True     |
| 14_lama_restoration | lama         | 2026-07-27T23:01:04.055449+00:00 | inventory             | failed_inventory_rows       | 0                                                                        | 0                                                                        | True     |

## Synthetic-Degradation Eligibility

LaMa is used only where the synthetic-degradation case can be interpreted as an inpainting-style restoration problem with a concrete mask. Cases outside this policy are excluded from Notebook 14 rather than treated as LaMa failures.

## Method Notes

- Case identifiers are standardized as `lama__<dataset_name>__<case_id>`.
- Zero-control rows are copied without model inference and explicitly marked in the metadata.
- Runtime, retry count, attempt count, model name, device, restored path, and validation outcomes are recorded.
- This notebook intentionally saves a small number of tabular outputs: the main metadata CSV, one audit CSV, and one figure manifest CSV.
- All restored image files are saved under the LaMa restored root.
