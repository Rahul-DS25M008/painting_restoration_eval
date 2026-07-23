# Canonical Damaged-Image Generation Report

This report documents the synthetic damage-generation stage for the 50-painting controlled evaluation subset.

## Generation settings

- Generator: `canonical_damage_generator`
- Generator version: `2.0.0`
- Fill strategy: `white_fill`
- Fill colour: `(255, 255, 255)`
- Target dimensions: 768 × 768
- Paintings: 50
- Damage cases: 250

## Mask conditions

- `zero_control`: 50 cases, mean damaged content area 0.0000%
- `scratch_thin`: 50 cases, mean damaged content area 2.1363%
- `loss_small`: 50 cases, mean damaged content area 4.0246%
- `loss_large`: 50 cases, mean damaged content area 12.3288%
- `mixed_damage`: 50 cases, mean damaged content area 9.6600%

## Validation result

- All damaged images were reloaded successfully as RGB PNG files with 768 × 768 dimensions.
- No pixels outside the binary masks were changed.
- Every masked output pixel matched the configured fill colour.
- Mask-pixel counts matched canonical mask metadata.
- Zero-control outputs remained identical to their clean source images.
- Clean, mask, and damaged-image SHA-256 checksums were recorded.
- Inventory auditing found no missing, duplicate, unexpected, or orphaned damaged-image files.

## Output provenance

- Canonical metadata: `data\processed\metadata\metadata_damaged_images.csv`
- Damaged images: `data\processed\masked`
- Validation tables: `outputs\metrics`
- Figures: `outputs\figures\damage_creation`

## Interpretation note

The number of numerically changed pixels may be slightly lower than the number of masked pixels when a clean source pixel already equals the white fill colour. This does not represent a generation failure. The authoritative conditions are exact preservation outside the mask and correct fill values inside it.