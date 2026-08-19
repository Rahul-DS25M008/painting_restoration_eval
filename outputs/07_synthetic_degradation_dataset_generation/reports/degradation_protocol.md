# Synthetic Degradation Protocol

## Status and scope

- Notebook: `07_synthetic_degradation_dataset_generation`
- Dataset: `painting_restoration_eval`
- Dataset version: `1.0.0`
- Dataset scope: `controlled_50`
- Experiment: `synthetic_degradation`
- Configuration schema: `synthetic_degradation_config.v1`
- Configuration version: `2.0.0`
- Generator: `2.0.0`
- Seed scheme: `synthetic_degradation_seed.v2`
- Global seed: `20260707`
- Canonical cases: `165`
- Effect-support masks: `165`
- Degraded images: `165`

This protocol defines a controlled non-binary procedural-degradation
branch for restoration-evaluation research.

## Interpretation boundary

The generated effects are controlled procedural evaluation proxies.
They are not exact simulations of conservation damage, material aging,
pigment chemistry, varnish behavior, moisture transport, substrate
exposure, or any specific historical deterioration process.

This branch is not missing-region damage. The effect-support masks must
not be interpreted as binary missing-pixel masks, physical damage
segmentations, conservation annotations, or material-loss ground truth.

Visual plausibility is not equivalent to historical correctness,
conservation approval, or restoration trustworthiness.

## Effect-support semantics

Every effect-support mask is an 8-bit grayscale `L` PNG.

- `0` means the operator has no configured spatial influence.
- Values from `1` through `255` encode increasing spatial influence.
- The support threshold is
  `1`.
- The active threshold is
  `13`.
- Combined masks use the pixelwise maximum/union of their component
  influence masks.
- Changed pixels are required to remain inside the recorded support.
- Support is required to remain inside the Notebook 02 content box.

The mask is an algorithmic operator-influence record. It is not a claim
about real physical damage boundaries.

## Balanced five-painting cohort

| painting_id   | category                | processed_image_id   | processed_path                                       |
|:--------------|:------------------------|:---------------------|:-----------------------------------------------------|
| p001          | portrait_figure         | clean_p001           | outputs/02_image_preprocessing/images/clean/p001.png |
| p018          | landscape_natural       | clean_p018           | outputs/02_image_preprocessing/images/clean/p018.png |
| p026          | architecture_structured | clean_p026           | outputs/02_image_preprocessing/images/clean/p026.png |
| p039          | abstraction_surrealism  | clean_p039           | outputs/02_image_preprocessing/images/clean/p039.png |
| p043          | high_texture_brushwork  | clean_p043           | outputs/02_image_preprocessing/images/clean/p043.png |

## Case design

The canonical design contains:

- 10 single degradation families;
- 3 configured severity levels;
- 5 paintings;
- 150 single-degradation cases;
- 3 ordered combined degradations at the configured moderate level;
- 15 combined cases;
- 165 total cases.

Clean references remain canonical Notebook 02 inputs and are not copied,
overwritten, or modified by this notebook.

## Single-degradation operators and parameters

| family               | severity   | operator             | spatial_support      | parameters                                                                                                                   |
|:---------------------|:-----------|:---------------------|:---------------------|:-----------------------------------------------------------------------------------------------------------------------------|
| gaussian_blur        | mild       | gaussian_blur        | full_content         | {"radius": 1.5, "strength": 0.55}                                                                                            |
| gaussian_blur        | moderate   | gaussian_blur        | full_content         | {"radius": 3.0, "strength": 0.75}                                                                                            |
| gaussian_blur        | severe     | gaussian_blur        | full_content         | {"radius": 5.5, "strength": 1.0}                                                                                             |
| motion_blur          | mild       | motion_blur          | full_content         | {"angle_degrees": 18.0, "kernel_length": 5, "strength": 0.55}                                                                |
| motion_blur          | moderate   | motion_blur          | full_content         | {"angle_degrees": 32.0, "kernel_length": 11, "strength": 0.75}                                                               |
| motion_blur          | severe     | motion_blur          | full_content         | {"angle_degrees": 47.0, "kernel_length": 19, "strength": 0.95}                                                               |
| local_defocus        | mild       | local_defocus        | soft_local_blobs     | {"blob_count": 1, "coverage_fraction": 0.14, "radius": 2.0, "strength": 0.6}                                                 |
| local_defocus        | moderate   | local_defocus        | soft_local_blobs     | {"blob_count": 2, "coverage_fraction": 0.24, "radius": 4.0, "strength": 0.8}                                                 |
| local_defocus        | severe     | local_defocus        | soft_local_blobs     | {"blob_count": 3, "coverage_fraction": 0.36, "radius": 7.0, "strength": 1.0}                                                 |
| water_stain          | mild       | water_stain          | soft_ring_stain      | {"coverage_fraction": 0.1, "strength": 0.28, "tint_rgb": [145, 105, 63]}                                                     |
| water_stain          | moderate   | water_stain          | soft_ring_stain      | {"coverage_fraction": 0.18, "strength": 0.48, "tint_rgb": [135, 92, 52]}                                                     |
| water_stain          | severe     | water_stain          | soft_ring_stain      | {"coverage_fraction": 0.28, "strength": 0.68, "tint_rgb": [122, 78, 42]}                                                     |
| pigment_bleeding     | mild       | pigment_bleeding     | soft_local_blobs     | {"blob_count": 1, "channel_shift": 1, "coverage_fraction": 0.12, "radius": 1.8, "strength": 0.4}                             |
| pigment_bleeding     | moderate   | pigment_bleeding     | soft_local_blobs     | {"blob_count": 2, "channel_shift": 2, "coverage_fraction": 0.22, "radius": 3.5, "strength": 0.62}                            |
| pigment_bleeding     | severe     | pigment_bleeding     | soft_local_blobs     | {"blob_count": 3, "channel_shift": 4, "coverage_fraction": 0.34, "radius": 5.5, "strength": 0.82}                            |
| fading               | mild       | fading               | soft_broad_patch     | {"brightness_factor": 1.03, "contrast_factor": 0.94, "coverage_fraction": 0.58, "saturation_factor": 0.82, "strength": 0.22} |
| fading               | moderate   | fading               | soft_broad_patch     | {"brightness_factor": 1.07, "contrast_factor": 0.86, "coverage_fraction": 0.72, "saturation_factor": 0.62, "strength": 0.42} |
| fading               | severe     | fading               | soft_broad_patch     | {"brightness_factor": 1.12, "contrast_factor": 0.76, "coverage_fraction": 0.86, "saturation_factor": 0.4, "strength": 0.68}  |
| discolouration       | mild       | discolouration       | soft_broad_patch     | {"coverage_fraction": 0.52, "strength": 0.22, "tint_rgb": [210, 176, 112]}                                                   |
| discolouration       | moderate   | discolouration       | soft_broad_patch     | {"coverage_fraction": 0.68, "strength": 0.38, "tint_rgb": [202, 159, 88]}                                                    |
| discolouration       | severe     | discolouration       | soft_broad_patch     | {"coverage_fraction": 0.82, "strength": 0.58, "tint_rgb": [190, 139, 67]}                                                    |
| local_darkening      | mild       | local_darkening      | soft_local_blobs     | {"blob_count": 1, "coverage_fraction": 0.12, "darkness_factor": 0.78, "strength": 0.2}                                       |
| local_darkening      | moderate   | local_darkening      | soft_local_blobs     | {"blob_count": 2, "coverage_fraction": 0.22, "darkness_factor": 0.58, "strength": 0.38}                                      |
| local_darkening      | severe     | local_darkening      | soft_local_blobs     | {"blob_count": 3, "coverage_fraction": 0.34, "darkness_factor": 0.38, "strength": 0.58}                                      |
| dirt_dust            | mild       | dirt_dust            | speckles_and_streaks | {"radius_max": 2, "speck_count": 80, "streak_count": 3, "strength": 0.35}                                                    |
| dirt_dust            | moderate   | dirt_dust            | speckles_and_streaks | {"radius_max": 3, "speck_count": 180, "streak_count": 7, "strength": 0.52}                                                   |
| dirt_dust            | severe     | dirt_dust            | speckles_and_streaks | {"radius_max": 4, "speck_count": 320, "streak_count": 12, "strength": 0.7}                                                   |
| partial_transparency | mild       | partial_transparency | soft_local_blobs     | {"blob_count": 1, "coverage_fraction": 0.14, "opacity_loss": 0.18, "strength": 0.22, "substrate_rgb": [232, 226, 214]}       |
| partial_transparency | moderate   | partial_transparency | soft_local_blobs     | {"blob_count": 2, "coverage_fraction": 0.24, "opacity_loss": 0.34, "strength": 0.42, "substrate_rgb": [232, 226, 214]}       |
| partial_transparency | severe     | partial_transparency | soft_local_blobs     | {"blob_count": 3, "coverage_fraction": 0.36, "opacity_loss": 0.54, "strength": 0.66, "substrate_rgb": [232, 226, 214]}       |

## Ordered combined degradations

| combined_family       | severity   | ordered_components       |
|:----------------------|:-----------|:-------------------------|
| fading_discolouration | moderate   | fading -> discolouration |
| water_stain_dirt      | moderate   | water_stain -> dirt_dust |
| gaussian_blur_fading  | moderate   | gaussian_blur -> fading  |

Component order is part of the experimental definition. Reversing the
order would define a different transformation and is not treated as an
equivalent case.

## Determinism and provenance

Each case records:

- the global generator seed;
- a stable case seed;
- a stable effect-mask seed;
- an operator seed for every component;
- the complete operator-parameter mapping;
- the generator and configuration versions;
- the clean, effect-mask, and degraded-image SHA-256 checksums;
- content geometry inherited from Notebook 02.

Identical configuration, input checksums, helper version, and seed
scheme are expected to reproduce identical pixels and metadata.

## Recorded impact evidence

Affected area, changed pixels, RGB difference, colour distance,
luminance shift, saturation shift, gradient-energy ratio, and
Laplacian-variance ratio are descriptive generation proxies. They do
not measure conservation severity or historical fidelity.

| degradation_family    | severity   | is_combined   |   cases |   paintings |   mean_affected_content_percent |   mean_changed_content_percent |   mean_absolute_rgb_difference |   mean_rgb_colour_distance |   mean_gradient_energy_ratio |   mean_laplacian_variance_ratio |
|:----------------------|:-----------|:--------------|--------:|------------:|--------------------------------:|-------------------------------:|-------------------------------:|---------------------------:|-----------------------------:|--------------------------------:|
| gaussian_blur         | mild       | False         |       5 |           5 |                      100        |                      96.3229   |                       2.49287  |                    4.63254 |                     0.588135 |                        0.233922 |
| gaussian_blur         | moderate   | False         |       5 |           5 |                      100        |                      98.3647   |                       4.94202  |                    9.19476 |                     0.383467 |                        0.076406 |
| gaussian_blur         | severe     | False         |       5 |           5 |                      100        |                      99.4193   |                       9.12438  |                   16.9322  |                     0.179216 |                        0.006803 |
| motion_blur           | mild       | False         |       5 |           5 |                      100        |                      95.2475   |                       2.03881  |                    3.79311 |                     0.686125 |                        0.366813 |
| motion_blur           | moderate   | False         |       5 |           5 |                      100        |                      97.4021   |                       4.60086  |                    8.56083 |                     0.493639 |                        0.136747 |
| motion_blur           | severe     | False         |       5 |           5 |                      100        |                      98.4978   |                       7.44081  |                   13.8065  |                     0.355244 |                        0.053252 |
| local_defocus         | mild       | False         |       5 |           5 |                       29.6633   |                      21.1885   |                       1.91535  |                    3.58705 |                     0.722546 |                        0.473437 |
| local_defocus         | moderate   | False         |       5 |           5 |                       40.4046   |                      32.45     |                       3.81791  |                    7.09203 |                     0.560994 |                        0.294001 |
| local_defocus         | severe     | False         |       5 |           5 |                       42.0987   |                      35.8535   |                       6.13089  |                   11.3408  |                     0.430014 |                        0.26143  |
| water_stain           | mild       | False         |       5 |           5 |                       18.3285   |                      16.9875   |                       2.74966  |                    5.33666 |                     0.951673 |                        0.907245 |
| water_stain           | moderate   | False         |       5 |           5 |                       33.5793   |                      31.74     |                       4.39522  |                    8.58076 |                     0.915401 |                        0.845951 |
| water_stain           | severe     | False         |       5 |           5 |                       48.029    |                      45.8173   |                       5.79569  |                   11.3676  |                     0.880147 |                        0.786715 |
| pigment_bleeding      | mild       | False         |       5 |           5 |                       26.2315   |                      16.3954   |                       1.17991  |                    2.31562 |                     0.823719 |                        0.639928 |
| pigment_bleeding      | moderate   | False         |       5 |           5 |                       43.7885   |                      33.8567   |                       2.49729  |                    4.79436 |                     0.671704 |                        0.434339 |
| pigment_bleeding      | severe     | False         |       5 |           5 |                       51.4524   |                      43.655    |                       4.89055  |                    9.40831 |                     0.526558 |                        0.321378 |
| fading                | mild       | False         |       5 |           5 |                       73.0116   |                      46.2025   |                       0.415399 |                    0.93579 |                     0.995781 |                        0.992413 |
| fading                | moderate   | False         |       5 |           5 |                       76.2345   |                      68.0934   |                       2.2999   |                    4.64122 |                     0.977927 |                        0.960427 |
| fading                | severe     | False         |       5 |           5 |                       79.1586   |                      74.9505   |                       6.77971  |                   13.3798  |                     0.92779  |                        0.871164 |
| discolouration        | mild       | False         |       5 |           5 |                       63.7861   |                      57.4572   |                       4.09767  |                    7.61456 |                     0.952245 |                        0.907762 |
| discolouration        | moderate   | False         |       5 |           5 |                       73.1143   |                      69.0334   |                       6.62807  |                   12.7566  |                     0.910688 |                        0.836675 |
| discolouration        | severe     | False         |       5 |           5 |                       82.8051   |                      79.553    |                       8.70589  |                   17.2381  |                     0.873817 |                        0.774709 |
| local_darkening       | mild       | False         |       5 |           5 |                       26.2129   |                      19.8775   |                       1.98975  |                    3.53467 |                     0.975061 |                        0.956748 |
| local_darkening       | moderate   | False         |       5 |           5 |                       43.8322   |                      38.8593   |                       8.40319  |                   14.9402  |                     0.903528 |                        0.822168 |
| local_darkening       | severe     | False         |       5 |           5 |                       50.9641   |                      47.3136   |                      18.5434   |                   32.8453  |                     0.764223 |                        0.597851 |
| dirt_dust             | mild       | False         |       5 |           5 |                        0.830688 |                       0.489449 |                       1.9503   |                    3.62266 |                     1.08987  |                        1.01204  |
| dirt_dust             | moderate   | False         |       5 |           5 |                        2.4353   |                       1.69849  |                       3.55542  |                    6.60194 |                     1.15867  |                        1.05619  |
| dirt_dust             | severe     | False         |       5 |           5 |                        5.23567  |                       3.9798   |                       5.46143  |                   10.1101  |                     1.26357  |                        1.17431  |
| partial_transparency  | mild       | False         |       5 |           5 |                       29.7634   |                      24.7515   |                       3.02941  |                    5.33535 |                     0.97549  |                        0.95165  |
| partial_transparency  | moderate   | False         |       5 |           5 |                       38.7179   |                      35.5617   |                      11.8461   |                   20.7764  |                     0.914548 |                        0.832597 |
| partial_transparency  | severe     | False         |       5 |           5 |                       45.1445   |                      43.2568   |                      30.1073   |                   52.7925  |                     0.783311 |                        0.617716 |
| fading_discolouration | moderate   | True          |       5 |           5 |                       82.307    |                      76.6249   |                       7.14182  |                   13.423   |                     0.90801  |                        0.837541 |
| water_stain_dirt      | moderate   | True          |       5 |           5 |                       40.3159   |                      37.4418   |                       4.24432  |                    8.30885 |                     0.925484 |                        0.850802 |
| gaussian_blur_fading  | moderate   | True          |       5 |           5 |                      100        |                      98.9184   |                       5.81103  |                   10.9544  |                     0.376693 |                        0.074985 |

## Validation

All `165` canonical cases were independently
reloaded. The final reload audit found:

- `165` valid
  output contracts;
- `0`
  changed pixels outside recorded support;
- `0` missing declared paths;
- `0` stale paths;
- `0` orphan paths;
- `0` failed boolean contract fields.

## Physical and methodological limitations

1. RGB-domain operators do not model spectral reflectance, pigment
   composition, varnish layers, substrate mechanics, craquelure
   propagation, chemical reactions, humidity transport, or aging time.
2. Severity levels are configured ordinal experimental levels. They are
   not calibrated conservation-condition grades.
3. Affected-area fraction does not equal physical damage severity.
4. Influence masks encode algorithmic blending support and are not
   expert damage annotations.
5. The five-painting cohort improves controlled visual diversity but
   does not represent the full distribution of artists, periods,
   materials, techniques, or conservation conditions.
6. Combined degradations are selected ordered compositions and do not
   enumerate all real-world interactions.
7. Pixel, colour, gradient, and Laplacian statistics are descriptive
   proxies rather than evidence of historical authenticity.
8. These generated cases may expose algorithmic behavior but cannot
   certify conservation readiness.
9. Restoration-model eligibility and evaluation-region policy are
   explicitly deferred to Notebook 08.
10. Human conservation review remains necessary for any real-world
    interpretation.

## Downstream use

The normalized case manifest is prepared for Notebook 08, which decides
model eligibility and region policy. Downstream notebooks must retain
the non-binary effect-support semantics and the interpretation
boundaries stated above.
