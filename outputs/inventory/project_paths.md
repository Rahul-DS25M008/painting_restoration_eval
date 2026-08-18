# Project Artifact Paths

- Schema: `project_paths.v1`
- Updated: `2026-08-18T11:19:24.175226Z`
- Registered artifacts: 17

| Artifact key | Producer | Relative path | Role | Validation |
|---|---|---|---|---|
| dataset.artworks | 01_dataset_verification | `outputs/01_dataset_verification/data/artworks.csv` | primary_downstream | passed |
| dataset.audit | 01_dataset_verification | `outputs/01_dataset_verification/metrics/dataset_audit.csv` | audit_reporting | passed |
| dataset.figure_distribution | 01_dataset_verification | `outputs/01_dataset_verification/figures/dataset_distribution.png` | reporting | passed |
| dataset.figure_preview | 01_dataset_verification | `outputs/01_dataset_verification/figures/dataset_preview.png` | qa_reporting | passed |
| masks.audit | 03_canonical_mask_generation | `outputs/03_canonical_mask_generation/metrics/mask_audit.csv` | audit_reporting | passed |
| masks.canonical | 03_canonical_mask_generation | `outputs/03_canonical_mask_generation/data/masks.csv` | primary_downstream | passed |
| masks.canonical_images | 03_canonical_mask_generation | `outputs/03_canonical_mask_generation/images/masks` | primary_downstream | passed |
| masks.figure_examples | 03_canonical_mask_generation | `outputs/03_canonical_mask_generation/figures/mask_examples.png` | qa_reporting | passed |
| masks.figure_morphology | 03_canonical_mask_generation | `outputs/03_canonical_mask_generation/figures/mask_morphology.png` | thesis_reporting | passed |
| masks.protocol | 03_canonical_mask_generation | `outputs/03_canonical_mask_generation/reports/mask_protocol.md` | methodology_reporting | passed |
| preprocessing.audit | 02_image_preprocessing | `outputs/02_image_preprocessing/metrics/preprocessing_audit.csv` | audit_reporting | passed |
| preprocessing.clean_images | 02_image_preprocessing | `outputs/02_image_preprocessing/images/clean` | primary_downstream | passed |
| preprocessing.figure_preview | 02_image_preprocessing | `outputs/02_image_preprocessing/figures/preprocessing_preview.png` | qa_reporting | passed |
| preprocessing.geometry | 02_image_preprocessing | `outputs/02_image_preprocessing/data/preprocessed_images.csv` | primary_downstream | passed |
| validation.01_dataset_verification | 01_dataset_verification | `outputs/01_dataset_verification/validation/checks.csv` | validation | passed |
| validation.02_image_preprocessing | 02_image_preprocessing | `outputs/02_image_preprocessing/validation/checks.csv` | validation | passed |
| validation.03_canonical_mask_generation | 03_canonical_mask_generation | `outputs/03_canonical_mask_generation/validation/checks.csv` | validation | passed |
