# 50-Painting Controlled Subset Scaffold

This scaffold prepares the next experimental phase after the reproducible 3-painting OpenCV Telea pilot.

## Files

- `data/model_audit/model_candidates.csv`  
  Tracks candidate restoration/inpainting models, their reproducibility status, training-data transparency, domain-gap risks, and planned experimental role.

- `data/raw/metadata/metadata_50_template.csv`  
  Template for selecting 50 public-domain/open-access paintings across five restoration-relevant categories.

- `config/experiment_50_config.yaml`  
  Configuration draft for the 50-painting controlled subset, including dataset structure, damage conditions, model candidates, metrics, and reporting.

## Recommended next order

1. Fill the model audit table using model cards, papers, and documentation.
2. Select candidate paintings and complete `metadata_50_template.csv`.
3. Rename the completed metadata file to `metadata_50.csv`.
4. Extend mask generation code to support the new damage conditions.
5. Run OpenCV Telea on the full 50-painting subset first.
6. Add LaMa only after the OpenCV baseline is stable.
7. Add diffusion/uncertainty evaluation after deterministic comparison works.
