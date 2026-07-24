# Mask Generation Report

## Experiment

- Experiment: painting_restoration_50_subset
- Version: 1.0.0
- Generator: canonical_synthetic_damage_masks
- Generator version: 2.0.0
- Config version: 1.1.0

## Dataset

- Paintings: 50
- Mask types: 5
- Expected masks: 250
- Generated masks: 250

## Validation

- Metadata validation: PASS
- Saved-mask validation: PASS
- Inventory validation: PASS
- Deterministic replay: PASS

## Output artifacts

Metadata:
- data\processed\metadata\metadata_masks.csv

Audit:
- outputs\03_mask_generation\mask_generation_audit.csv

Figures:
- outputs\figures\masks\mask_area_percentage_distribution.png
- outputs\figures\masks\mask_connected_component_distribution.png
- outputs\figures\masks\mask_bbox_fill_ratio_distribution.png
- outputs\figures\masks\mask_largest_component_fraction_distribution.png
- outputs\figures\masks\mask_border_touch_percentage.png
- outputs\figures\masks\mask_generation_attempt_distribution.png
- outputs\figures\masks\representative_mask_overlays.png