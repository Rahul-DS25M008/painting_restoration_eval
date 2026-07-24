# Canonical Damaged-Image Generation Report

## Experiment

- Experiment: `painting_restoration_50_subset`
- Experiment version: `1.0.0`
- Configuration version: `1.1.0`
- Generator: `canonical_damage_generator` version `2.0.0`
- Fill strategy: `white_fill`
- Fill colour: RGB `(255, 255, 255)`
- Output dimensions: `768 × 768`

## Dataset

- Paintings: 50
- Mask types: 5
- Damage cases: 250
- Damaged PNG files: 250

## Mask-type summary

- `zero_control`: 50 cases; mean damaged content area 0.0000%; mean damaged pixels 0.00
- `scratch_thin`: 50 cases; mean damaged content area 2.1363%; mean damaged pixels 9614.46
- `loss_small`: 50 cases; mean damaged content area 4.0246%; mean damaged pixels 18175.36
- `loss_large`: 50 cases; mean damaged content area 12.3288%; mean damaged pixels 56236.98
- `mixed_damage`: 50 cases; mean damaged content area 9.6600%; mean damaged pixels 43420.00

## Validation

- Every damaged output was reloaded and validated as a readable RGB PNG with dimensions 768 × 768.
- No pixels outside the canonical binary masks were changed.
- Every pixel inside each mask was set to the configured damage-fill colour.
- Damaged-pixel counts matched the canonical mask metadata.
- Zero-control outputs remained identical to their clean sources.
- SHA-256 checksums were recorded for clean images, masks, and damaged images.
- Missing, duplicate, stale, and orphaned damaged-image files were audited.

## Canonical artifacts

- Damaged images: `data\processed\masked`
- Metadata: `data\processed\metadata\metadata_damaged_images.csv`
- Audit: `outputs\04_damage_creation\damage_creation_audit.csv`
- Figures: `outputs\figures\damage_creation`
- JSON manifest: `outputs\reports\damage_creation_metadata.json`

## Interpretation note

The numerically changed-pixel count can be smaller than the
binary-mask pixel count when a clean source pixel already has
exactly the configured fill colour. This is not a generation
failure. The authoritative requirements are that all pixels
outside the mask remain unchanged and all pixels inside the mask
equal the configured fill colour.