# Pilot Reproducibility Note

## Purpose

This note records the reproducibility status of the cleaned pilot pipeline for the thesis project **Trustworthy Evaluation Frameworks for AI-Assisted Painting Restoration**.

The purpose of this checkpoint is to confirm that the pilot can be regenerated from raw inputs using the cleaned notebooks and reusable source modules.

## Reproducibility checkpoint

The pilot project was refactored into a cleaner repository structure with:

- a dedicated virtual environment
- a `requirements.txt` dependency file
- reusable source modules under `src/restoration_eval/`
- cleaned notebooks with a fixed execution order
- organized input, processed data, metrics, figures, and report folders

After cleanup, generated outputs were deleted and the full notebook sequence was rerun from the raw input images and metadata.

## Raw inputs retained

The following inputs were kept:

```text
data/raw/images/
data/raw/metadata/metadata_pilot.csv
```

These files were sufficient to regenerate all downstream pilot outputs.

## Notebook run order

The validated run order is:

```text
01_dataset_verification.ipynb
02_preprocessing.ipynb
03_mask_generation.ipynb
04_opencv_restoration.ipynb
05_metrics_classical.ipynb
06_difference_maps.ipynb
07_lpips_metrics.ipynb
08_generate_report_opencv.ipynb
```

## Regenerated outputs

The full rerun successfully regenerated:

```text
outputs/dataset_verification_summary.csv

data/processed/clean/
data/processed/masks/
data/processed/masked/
data/processed/restored/opencv_telea/
data/processed/metadata/

outputs/metrics/
outputs/figures/difference_maps/
outputs/figures/comparison_grids/
outputs/reports/
```

Expected counts:

| Output type | Expected count |
|---|---:|
| Clean processed images | 3 |
| Synthetic masks | 9 |
| Masked images | 9 |
| OpenCV Telea restorations | 9 |
| Difference map images | 18 |
| Comparison grids | 9 |

Expected metric/report files:

```text
outputs/metrics/metrics_opencv_telea_classical.csv
outputs/metrics/difference_map_summary_opencv_telea.csv
outputs/metrics/metrics_opencv_telea_lpips.csv
outputs/metrics/metrics_opencv_telea_with_lpips.csv

outputs/reports/opencv_telea_report_v3_lpips.html
outputs/reports/opencv_telea_report_v3_lpips_light.html
```

## Result

The pilot cleanup and reproducibility test were successful.

The current repository state is suitable as a baseline before moving into the 50-painting controlled subset phase.

## Notes

Generated outputs are useful for inspection and reporting, but the core reproducibility of the project depends on:

- raw images
- metadata
- source modules
- notebooks
- configuration
- dependency list

The virtual environment, cache files, and notebook checkpoints should not be committed to version control.
