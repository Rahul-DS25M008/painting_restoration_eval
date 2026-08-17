# Project Artifact Paths

- Schema: `project_paths.v1`
- Updated: `2026-08-17T12:14:31.021595Z`
- Registered artifacts: 5

| Artifact key | Producer | Relative path | Role | Validation |
|---|---|---|---|---|
| dataset.artworks | 01_dataset_verification | `outputs/01_dataset_verification/data/artworks.csv` | primary_downstream | passed |
| dataset.audit | 01_dataset_verification | `outputs/01_dataset_verification/metrics/dataset_audit.csv` | audit_reporting | passed |
| dataset.figure_distribution | 01_dataset_verification | `outputs/01_dataset_verification/figures/dataset_distribution.png` | reporting | passed |
| dataset.figure_preview | 01_dataset_verification | `outputs/01_dataset_verification/figures/dataset_preview.png` | qa_reporting | passed |
| validation.01_dataset_verification | 01_dataset_verification | `outputs/01_dataset_verification/validation/checks.csv` | validation | passed |
