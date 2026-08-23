# Project Artifact Paths

- Schema: `project_paths.v1`
- Updated: `2026-08-23T21:41:34.937326Z`
- Registered artifacts: 48

| Artifact key | Producer | Relative path | Role | Validation |
|---|---|---|---|---|
| damage.audit | 04_canonical_damaged_image_generation | `outputs/04_canonical_damaged_image_generation/metrics/damage_audit.csv` | audit_reporting | passed |
| damage.canonical_cases | 04_canonical_damaged_image_generation | `outputs/04_canonical_damaged_image_generation/data/cases.csv` | primary_downstream | passed |
| damage.canonical_images | 04_canonical_damaged_image_generation | `outputs/04_canonical_damaged_image_generation/images/damaged` | primary_downstream | passed |
| damage.figure_examples | 04_canonical_damaged_image_generation | `outputs/04_canonical_damaged_image_generation/figures/damage_examples.png` | qa_reporting | passed |
| damage_size.cases | 05_damage_size_sensitivity_dataset_generation | `outputs/05_damage_size_sensitivity_dataset_generation/data/cases.csv` | primary_downstream | passed |
| damage_size.damaged_images | 05_damage_size_sensitivity_dataset_generation | `outputs/05_damage_size_sensitivity_dataset_generation/images/damaged` | primary_downstream | passed |
| damage_size.figure_progression | 05_damage_size_sensitivity_dataset_generation | `outputs/05_damage_size_sensitivity_dataset_generation/figures/damage_size_progression.png` | thesis_reporting | passed |
| damage_size.generation_audit | 05_damage_size_sensitivity_dataset_generation | `outputs/05_damage_size_sensitivity_dataset_generation/metrics/generation_audit.csv` | audit_reporting | passed |
| damage_size.masks | 05_damage_size_sensitivity_dataset_generation | `outputs/05_damage_size_sensitivity_dataset_generation/images/masks` | primary_downstream | passed |
| dataset.artworks | 01_dataset_verification | `outputs/01_dataset_verification/data/artworks.csv` | primary_downstream | passed |
| dataset.audit | 01_dataset_verification | `outputs/01_dataset_verification/metrics/dataset_audit.csv` | audit_reporting | passed |
| dataset.figure_distribution | 01_dataset_verification | `outputs/01_dataset_verification/figures/dataset_distribution.png` | reporting | passed |
| dataset.figure_preview | 01_dataset_verification | `outputs/01_dataset_verification/figures/dataset_preview.png` | qa_reporting | passed |
| experiment_contracts.case_registry | 08_experiment_contracts_and_region_policy | `outputs/08_experiment_contracts_and_region_policy/data/case_registry.csv` | primary_cross_experiment_registry | passed |
| experiment_contracts.figure_region_definitions | 08_experiment_contracts_and_region_policy | `outputs/08_experiment_contracts_and_region_policy/figures/region_definitions.png` | methodology_visualization | passed |
| experiment_contracts.model_eligibility | 08_experiment_contracts_and_region_policy | `outputs/08_experiment_contracts_and_region_policy/data/model_eligibility.csv` | authoritative_model_routing | passed |
| experiment_contracts.region_policy | 08_experiment_contracts_and_region_policy | `outputs/08_experiment_contracts_and_region_policy/data/region_policy.csv` | authoritative_metric_region_policy | passed |
| experiment_contracts.report | 08_experiment_contracts_and_region_policy | `outputs/08_experiment_contracts_and_region_policy/reports/evaluation_contract.md` | evaluation_contract | passed |
| experiment_contracts.schema_registry | 08_experiment_contracts_and_region_policy | `outputs/08_experiment_contracts_and_region_policy/data/schema_registry.json` | machine_readable_schema_handoff | passed |
| mask_robustness.cases | 06_mask_robustness_dataset_generation | `outputs/06_mask_robustness_dataset_generation/data/cases.csv` | primary_case_manifest | passed |
| mask_robustness.damaged_images | 06_mask_robustness_dataset_generation | `outputs/06_mask_robustness_dataset_generation/images/damaged` | damaged_image_collection | passed |
| mask_robustness.figure_examples | 06_mask_robustness_dataset_generation | `outputs/06_mask_robustness_dataset_generation/figures/robustness_examples.png` | representative_visual_evidence | passed |
| mask_robustness.generation_audit | 06_mask_robustness_dataset_generation | `outputs/06_mask_robustness_dataset_generation/metrics/generation_audit.csv` | generation_audit | passed |
| mask_robustness.masks | 06_mask_robustness_dataset_generation | `outputs/06_mask_robustness_dataset_generation/images/masks` | mask_collection | passed |
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
| synthetic_degradation.cases | 07_synthetic_degradation_dataset_generation | `outputs/07_synthetic_degradation_dataset_generation/data/cases.csv` | primary_case_manifest | passed |
| synthetic_degradation.effect_masks | 07_synthetic_degradation_dataset_generation | `outputs/07_synthetic_degradation_dataset_generation/images/effect_masks` | effect_support_collection | passed |
| synthetic_degradation.figure_examples | 07_synthetic_degradation_dataset_generation | `outputs/07_synthetic_degradation_dataset_generation/figures/degradation_examples.png` | representative_visual_evidence | passed |
| synthetic_degradation.generation_audit | 07_synthetic_degradation_dataset_generation | `outputs/07_synthetic_degradation_dataset_generation/metrics/generation_audit.csv` | generation_audit | passed |
| synthetic_degradation.images | 07_synthetic_degradation_dataset_generation | `outputs/07_synthetic_degradation_dataset_generation/images/degraded` | degraded_image_collection | passed |
| synthetic_degradation.protocol | 07_synthetic_degradation_dataset_generation | `outputs/07_synthetic_degradation_dataset_generation/reports/degradation_protocol.md` | degradation_protocol | passed |
| validation.01_dataset_verification | 01_dataset_verification | `outputs/01_dataset_verification/validation/checks.csv` | validation | passed |
| validation.02_image_preprocessing | 02_image_preprocessing | `outputs/02_image_preprocessing/validation/checks.csv` | validation | passed |
| validation.03_canonical_mask_generation | 03_canonical_mask_generation | `outputs/03_canonical_mask_generation/validation/checks.csv` | validation | passed |
| validation.04_canonical_damaged_image_generation | 04_canonical_damaged_image_generation | `outputs/04_canonical_damaged_image_generation/validation/checks.csv` | validation | passed |
| validation.05_damage_size_sensitivity_dataset_generation | 05_damage_size_sensitivity_dataset_generation | `outputs/05_damage_size_sensitivity_dataset_generation/validation/checks.csv` | validation | passed |
| validation.06_mask_robustness_dataset_generation | 06_mask_robustness_dataset_generation | `outputs/06_mask_robustness_dataset_generation/validation/checks.csv` | validation_evidence | passed |
| validation.07_synthetic_degradation_dataset_generation | 07_synthetic_degradation_dataset_generation | `outputs/07_synthetic_degradation_dataset_generation/validation/checks.csv` | validation_evidence | passed |
| validation.08_experiment_contracts_and_region_policy | 08_experiment_contracts_and_region_policy | `outputs/08_experiment_contracts_and_region_policy/validation/checks.csv` | validation_evidence | passed |
