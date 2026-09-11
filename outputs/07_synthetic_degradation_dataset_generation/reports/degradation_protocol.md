# Synthetic Degradation Protocol

## Status and scope

- Notebook: `07_synthetic_degradation_dataset_generation`
- Dataset: `painting_restoration_eval`
- Dataset version: `2.0.0`
- Dataset scope: `controlled_300`
- Experiment: `synthetic_degradation`
- Configuration schema: `synthetic_degradation_config.v2`
- Configuration version: `2.1.0`
- Generator: `2.1.0`
- Seed scheme: `synthetic_degradation_seed.v2`
- Global seed: `20260707`
- Canonical cases: `1155`
- Effect-support masks: `1155`
- Degraded images: `1155`

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

## Balanced 35-painting cohort

| painting_id   | category                | processed_image_id   | processed_path                                       |
|:--------------|:------------------------|:---------------------|:-----------------------------------------------------|
| p001          | portrait_figure         | clean_p001           | outputs/02_image_preprocessing/images/clean/p001.png |
| p267          | portrait_figure         | clean_p267           | outputs/02_image_preprocessing/images/clean/p267.png |
| p294          | portrait_figure         | clean_p294           | outputs/02_image_preprocessing/images/clean/p294.png |
| p259          | portrait_figure         | clean_p259           | outputs/02_image_preprocessing/images/clean/p259.png |
| p009          | portrait_figure         | clean_p009           | outputs/02_image_preprocessing/images/clean/p009.png |
| p284          | portrait_figure         | clean_p284           | outputs/02_image_preprocessing/images/clean/p284.png |
| p256          | portrait_figure         | clean_p256           | outputs/02_image_preprocessing/images/clean/p256.png |
| p018          | landscape_natural       | clean_p018           | outputs/02_image_preprocessing/images/clean/p018.png |
| p157          | landscape_natural       | clean_p157           | outputs/02_image_preprocessing/images/clean/p157.png |
| p178          | landscape_natural       | clean_p178           | outputs/02_image_preprocessing/images/clean/p178.png |
| p198          | landscape_natural       | clean_p198           | outputs/02_image_preprocessing/images/clean/p198.png |
| p181          | landscape_natural       | clean_p181           | outputs/02_image_preprocessing/images/clean/p181.png |
| p173          | landscape_natural       | clean_p173           | outputs/02_image_preprocessing/images/clean/p173.png |
| p199          | landscape_natural       | clean_p199           | outputs/02_image_preprocessing/images/clean/p199.png |
| p026          | architecture_structured | clean_p026           | outputs/02_image_preprocessing/images/clean/p026.png |
| p124          | architecture_structured | clean_p124           | outputs/02_image_preprocessing/images/clean/p124.png |
| p139          | architecture_structured | clean_p139           | outputs/02_image_preprocessing/images/clean/p139.png |
| p123          | architecture_structured | clean_p123           | outputs/02_image_preprocessing/images/clean/p123.png |
| p115          | architecture_structured | clean_p115           | outputs/02_image_preprocessing/images/clean/p115.png |
| p140          | architecture_structured | clean_p140           | outputs/02_image_preprocessing/images/clean/p140.png |
| p107          | architecture_structured | clean_p107           | outputs/02_image_preprocessing/images/clean/p107.png |
| p039          | abstraction_surrealism  | clean_p039           | outputs/02_image_preprocessing/images/clean/p039.png |
| p100          | abstraction_surrealism  | clean_p100           | outputs/02_image_preprocessing/images/clean/p100.png |
| p089          | abstraction_surrealism  | clean_p089           | outputs/02_image_preprocessing/images/clean/p089.png |
| p077          | abstraction_surrealism  | clean_p077           | outputs/02_image_preprocessing/images/clean/p077.png |
| p093          | abstraction_surrealism  | clean_p093           | outputs/02_image_preprocessing/images/clean/p093.png |
| p052          | abstraction_surrealism  | clean_p052           | outputs/02_image_preprocessing/images/clean/p052.png |
| p073          | abstraction_surrealism  | clean_p073           | outputs/02_image_preprocessing/images/clean/p073.png |
| p043          | high_texture_brushwork  | clean_p043           | outputs/02_image_preprocessing/images/clean/p043.png |
| p208          | high_texture_brushwork  | clean_p208           | outputs/02_image_preprocessing/images/clean/p208.png |
| p223          | high_texture_brushwork  | clean_p223           | outputs/02_image_preprocessing/images/clean/p223.png |
| p235          | high_texture_brushwork  | clean_p235           | outputs/02_image_preprocessing/images/clean/p235.png |
| p246          | high_texture_brushwork  | clean_p246           | outputs/02_image_preprocessing/images/clean/p246.png |
| p220          | high_texture_brushwork  | clean_p220           | outputs/02_image_preprocessing/images/clean/p220.png |
| p210          | high_texture_brushwork  | clean_p210           | outputs/02_image_preprocessing/images/clean/p210.png |

## Case design

The canonical design contains:

- 10 single degradation families;
- 3 configured severity levels;
- 35 paintings, with seven from each controlled visual category;
- 1,050 single-degradation cases;
- 3 ordered combined degradations at the configured moderate level;
- 105 combined cases;
- 1,155 total cases.

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
| gaussian_blur         | mild       | False         |      35 |          35 |                      100        |                      94.99     |                       2.84578  |                    5.20538 |                     0.57899  |                        0.235631 |
| gaussian_blur         | moderate   | False         |      35 |          35 |                      100        |                      97.3088   |                       5.44347  |                    9.99991 |                     0.36227  |                        0.077907 |
| gaussian_blur         | severe     | False         |      35 |          35 |                      100        |                      98.4656   |                       9.53722  |                   17.5138  |                     0.155987 |                        0.008895 |
| motion_blur           | mild       | False         |      35 |          35 |                      100        |                      94.1072   |                       2.3555   |                    4.31242 |                     0.681508 |                        0.363227 |
| motion_blur           | moderate   | False         |      35 |          35 |                      100        |                      97.0805   |                       5.18144  |                    9.52107 |                     0.48002  |                        0.152187 |
| motion_blur           | severe     | False         |      35 |          35 |                      100        |                      97.9435   |                       8.02033  |                   14.7244  |                     0.338941 |                        0.06244  |
| local_defocus         | mild       | False         |      35 |          35 |                       29.7271   |                      20.9844   |                       2.15828  |                    3.98646 |                     0.71237  |                        0.479212 |
| local_defocus         | moderate   | False         |      35 |          35 |                       42.0287   |                      33.9331   |                       4.2238   |                    7.76154 |                     0.56087  |                        0.345649 |
| local_defocus         | severe     | False         |      35 |          35 |                       50.6127   |                      43.1704   |                       6.6104   |                   12.1263  |                     0.429202 |                        0.263958 |
| water_stain           | mild       | False         |      35 |          35 |                       18.35     |                      16.9779   |                       2.72154  |                    5.20381 |                     0.950504 |                        0.904763 |
| water_stain           | moderate   | False         |      35 |          35 |                       33.1369   |                      31.3186   |                       4.56096  |                    8.77591 |                     0.912559 |                        0.834966 |
| water_stain           | severe     | False         |      35 |          35 |                       48.9359   |                      46.8523   |                       6.51168  |                   12.5235  |                     0.876033 |                        0.773613 |
| pigment_bleeding      | mild       | False         |      35 |          35 |                       26.2793   |                      16.9976   |                       1.39003  |                    2.6775  |                     0.81741  |                        0.638243 |
| pigment_bleeding      | moderate   | False         |      35 |          35 |                       37.8033   |                      29.626    |                       3.13281  |                    5.90437 |                     0.660314 |                        0.435362 |
| pigment_bleeding      | severe     | False         |      35 |          35 |                       45.2845   |                      38.3284   |                       5.24421  |                    9.94962 |                     0.529475 |                        0.321391 |
| fading                | mild       | False         |      35 |          35 |                       69.5048   |                      43.8714   |                       0.458942 |                    1.02595 |                     0.995482 |                        0.991883 |
| fading                | moderate   | False         |      35 |          35 |                       74.5115   |                      66.3044   |                       2.5557   |                    5.11655 |                     0.976371 |                        0.955041 |
| fading                | severe     | False         |      35 |          35 |                       79.1096   |                      74.7166   |                       7.39711  |                   14.555   |                     0.925617 |                        0.861143 |
| discolouration        | mild       | False         |      35 |          35 |                       65.0981   |                      58.6623   |                       4.00564  |                    7.44351 |                     0.952915 |                        0.909058 |
| discolouration        | moderate   | False         |      35 |          35 |                       72.3189   |                      67.7599   |                       6.60877  |                   12.6215  |                     0.913161 |                        0.8361   |
| discolouration        | severe     | False         |      35 |          35 |                       78.832    |                      75.3653   |                       9.15951  |                   17.9678  |                     0.866478 |                        0.754985 |
| local_darkening       | mild       | False         |      35 |          35 |                       26.1933   |                      20.1945   |                       2.34517  |                    4.17221 |                     0.97505  |                        0.952892 |
| local_darkening       | moderate   | False         |      35 |          35 |                       40.5652   |                      35.9237   |                       8.59918  |                   15.2826  |                     0.907149 |                        0.829955 |
| local_darkening       | severe     | False         |      35 |          35 |                       49.4881   |                      46.3041   |                      20.6393   |                   36.5903  |                     0.775053 |                        0.616079 |
| dirt_dust             | mild       | False         |      35 |          35 |                        0.847025 |                       0.518037 |                       2.31956  |                    4.21835 |                     1.07081  |                        1.00636  |
| dirt_dust             | moderate   | False         |      35 |          35 |                        2.42989  |                       1.72106  |                       4.2655   |                    7.71729 |                     1.15008  |                        1.06601  |
| dirt_dust             | severe     | False         |      35 |          35 |                        5.38264  |                       4.16873  |                       6.6613   |                   12.0398  |                     1.25276  |                        1.23194  |
| partial_transparency  | mild       | False         |      35 |          35 |                       29.6745   |                      24.2629   |                       3.13272  |                    5.49609 |                     0.976988 |                        0.954718 |
| partial_transparency  | moderate   | False         |      35 |          35 |                       40.808    |                      37.1021   |                      12.0626   |                   21.1341  |                     0.911868 |                        0.834485 |
| partial_transparency  | severe     | False         |      35 |          35 |                       51.2773   |                      49.0041   |                      29.8536   |                   52.3432  |                     0.778572 |                        0.613156 |
| fading_discolouration | moderate   | True          |      35 |          35 |                       83.4491   |                      77.9385   |                       7.13355  |                   13.4469  |                     0.905215 |                        0.824981 |
| water_stain_dirt      | moderate   | True          |      35 |          35 |                       36.654    |                      34.2664   |                       4.70969  |                    9.03103 |                     0.926578 |                        0.847563 |
| gaussian_blur_fading  | moderate   | True          |      35 |          35 |                      100        |                      98.5332   |                       6.31704  |                   11.7735  |                     0.355896 |                        0.07636  |

## Validation

All `1155` canonical cases were independently
reloaded. The final reload audit found:

- `1155` valid
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
5. The balanced 35-painting cohort improves controlled visual diversity but
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
