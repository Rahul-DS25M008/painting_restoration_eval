# Canonical Binary Missing-Region Mask Protocol

- Configuration schema: `canonical_mask_config.v1`
- Configuration version: `1.0.0`
- Generator: `canonical_synthetic_damage_masks` version `3.0.0`
- Seed scheme: `canonical_mask_seed.v1`
- Global seed: `20260630`
- Retry policy: `closed_range_then_nearest_range_and_target`
- Maximum attempts: 30
- Spatial convention: `xyxy_exclusive_zero_based`
- Area denominator: painting-content pixels from Notebook 02
- Saved values: grayscale PNG with exact values 0 and 255

## Canonical mask families

| Family | Lower | Target | Upper | Description |
|---|---:|---:|---:|---|
| `zero_control` | 0.000 | 0.000 | 0.000 | No missing-region damage; measures unnecessary model alteration. |
| `scratch_thin` | 0.010 | 0.020 | 0.030 | Thin elongated scratch- or crack-like missing-region damage. |
| `loss_small` | 0.030 | 0.045 | 0.060 | Several small localized irregular missing-paint regions. |
| `loss_large` | 0.100 | 0.125 | 0.150 | One or two large irregular missing regions. |
| `mixed_damage` | 0.080 | 0.115 | 0.150 | Combined scratches, scattered losses, a medium loss, and edge loss. |

## Morphology expectations

| Family | Rule | Status |
|---|---|---|
| `zero_control` | `zero_control_empty` | passed |
| `scratch_thin` | `scratch_thin_elongated` | passed |
| `loss_small` | `loss_small_multicomponent` | passed |
| `loss_large` | `loss_large_substantially_larger` | passed |
| `mixed_damage` | `mixed_damage_combined_characteristics` | passed |

## Explicit exclusions

This notebook models binary missing-region damage only. It does not model:

- `blur`
- `fading`
- `discolouration`
- `dirt`
- `dust`
- `stains`
- `partial_transparency`
- `other_non_binary_degradation`

## Interpretation boundary

These masks are controlled synthetic evaluation instruments. They do not claim to reproduce the full material, historical, chemical, or conservation complexity of real painting damage.
Padding belongs to the technical model canvas and is never eligible for damage.
Runtime, run identifiers, timestamps, and environment metadata are run-dependent; mask pixels and canonical geometry are deterministic under the recorded configuration and seeds.
