# Notebook 07 — Synthetic Degradation Dataset Generation

    ## Status

    **Result:** Passed

    **Generated at:** `2026-07-25T19:09:34.149352+00:00`

    **Generator:** `synthetic_degradation` version `1.0.0`

    **Configuration:** `config/experiment_50_config.yaml`

    ## Purpose

    This notebook generates a controlled synthetic-degradation dataset for the canonical five-painting subset established by Notebook 05.

    The dataset extends the missing-content experiments with visual degradation families that preserve a clean reference, an effect-intensity mask, deterministic generation metadata, and a corresponding degraded image.

    These outputs support later evaluation of model and metric sensitivity under known image-space transformations.

    ## Input dependencies

    - Processed-image metadata: `data/processed/metadata/metadata_processed_clean.csv`
    - Notebook 05 damage-size metadata: `data/processed/metadata/metadata_damage_size_sensitivity.csv`
    - Generator module: `src/restoration_eval/synthetic_degradation.py`

    Notebook 05 metadata is used only to recover the canonical five painting IDs.

    Notebook 06 is not a data dependency.

    ## Experiment design

    - Paintings: **5**
    - Image size: **768 × 768**
    - Global seed: **20260707**
    - Single degradation families: **6**
    - Severity levels: **3**
    - Combined degradation families: **3**
    - Single-effect cases: **90**
    - Combined cases: **15**
    - Total cases: **105**

    ### Single degradation families

    `blur`, `water_stain`, `fading`, `discolouration`, `dirt_dust`, `partial_transparency`

    ### Severity levels

    `mild`, `moderate`, `severe`

    ### Combined degradation families

    | degradation_type | components | operator_order | effect_mask_source_operator |
| --- | --- | --- | --- |
| fading_discolouration | fading\|discolouration | fading → discolouration | fading |
| water_stain_dirt | water_stain\|dirt_dust | water_stain → dirt_dust | water_stain |
| blur_fading | blur\|fading | blur → fading | blur |

    ## Effect-mask interpretation

    Effect masks are grayscale intensity masks rather than binary missing-content masks.

    - **Effect support:** mask intensity greater than zero.
    - **Active effect region:** mask intensity at or above 13.
    - **Changed pixels:** RGB pixels differing from the clean reference.
    - **Combined cases:** one shared effect mask generated from the first configured component.
    - **Outside-support policy:** pixels outside effect support must remain unchanged.

    ## Deterministic generation

    Every case records:

    - global seed;
    - deterministic case seed;
    - deterministic effect-mask seed;
    - deterministic operator seeds;
    - component order;
    - complete operator parameters;
    - clean, effect-mask, and degraded-image checksums.

    The determinism audit regenerated **21** cases for painting `p001`.

    Determinism failures: **0**

    ## Dataset validation

    - Validated cases: **105**
    - Validation failures: **0**
    - Outside-effect changed pixels: **0**
    - Effect-mask files: **105**
    - Degraded-image files: **105**
    - Canonical metadata rows: **105**

    ### Validation summary

    | check | observed | expected | passed |
| --- | --- | --- | --- |
| validation_row_count | 105 | 105 | True |
| validation_case_coverage | 105 | 105 | True |
| clean_exists | 105 | 105 | True |
| effect_mask_exists | 105 | 105 | True |
| degraded_exists | 105 | 105 | True |
| readable | 105 | 105 | True |
| dimensions_valid | 105 | 105 | True |
| effect_mask_mode_valid | 105 | 105 | True |
| degraded_mode_valid | 105 | 105 | True |
| effect_mask_format_valid | 105 | 105 | True |
| degraded_format_valid | 105 | 105 | True |
| effect_mask_range_valid | 105 | 105 | True |
| effect_nonempty | 105 | 105 | True |
| degradation_nonempty | 105 | 105 | True |
| outside_effect_preserved | 105 | 105 | True |
| metadata_counts_match | 105 | 105 | True |
| checksum_valid | 105 | 105 | True |
| validation_passed | 105 | 105 | True |
| outside_effect_changed_pixel_count | 0 | 0 | True |
| validation_failure_count | 0 | 0 | True |

    ## Single-effect severity summary

    | degradation_type | severity | case_count | mean_effect_percentage_content | mean_changed_percentage_full | mean_absolute_difference_effect | maximum_absolute_difference |
| --- | --- | --- | --- | --- | --- | --- |
| blur | mild | 5 | 16.1886 | 7.2495 | 0.6730 | 34 |
| blur | moderate | 5 | 44.0429 | 26.8082 | 1.9212 | 71 |
| blur | severe | 5 | 76.6424 | 53.5202 | 3.6499 | 98 |
| water_stain | mild | 5 | 12.2081 | 9.6673 | 3.5229 | 20 |
| water_stain | moderate | 5 | 19.7394 | 16.0983 | 4.4583 | 26 |
| water_stain | severe | 5 | 27.8050 | 23.1968 | 5.5594 | 33 |
| fading | mild | 5 | 13.4847 | 7.3589 | 0.8228 | 19 |
| fading | moderate | 5 | 39.9105 | 29.4561 | 3.0876 | 55 |
| fading | severe | 5 | 73.9447 | 57.3308 | 5.7952 | 91 |
| discolouration | mild | 5 | 13.1131 | 7.7156 | 0.9942 | 11 |
| discolouration | moderate | 5 | 43.3686 | 31.3588 | 2.5867 | 25 |
| discolouration | severe | 5 | 71.1738 | 53.7406 | 6.0689 | 46 |
| dirt_dust | mild | 5 | 15.9254 | 0.2494 | 0.0079 | 2 |
| dirt_dust | moderate | 5 | 16.9319 | 2.8054 | 0.1207 | 6 |
| dirt_dust | severe | 5 | 27.0469 | 11.0540 | 0.4063 | 13 |
| partial_transparency | mild | 5 | 14.0353 | 10.7561 | 3.0149 | 19 |
| partial_transparency | moderate | 5 | 43.3251 | 35.7102 | 7.2584 | 46 |
| partial_transparency | severe | 5 | 70.7358 | 58.2037 | 17.8366 | 75 |

    ## Severity progression diagnostics

    Severity progression is treated as a descriptive diagnostic rather than a calibrated physical deterioration scale.

    Procedural mask geometry may lead to small non-monotonic differences in observed area or aggregate intensity even when operator severity settings increase.

    ### Non-monotonic progression flags

    | degradation_type | metric | mild_mean | moderate_mean | severe_mean | mild_to_moderate_change | moderate_to_severe_change |
| --- | --- | --- | --- | --- | --- | --- |
| water_stain | effect_mean_intensity | 109.5023 | 100.7295 | 89.4654 | -8.7728 | -11.2641 |

    ## Combined-effect summary

    Combined degradation cases use a shared spatial mask and apply their component operators sequentially in configured order.

    | degradation_type | severity | component_degradations | case_count | mean_effect_percentage_content | mean_changed_percentage_full | mean_absolute_difference_effect |
| --- | --- | --- | --- | --- | --- | --- |
| blur_fading | moderate | blur\|fading | 5 | 40.9147 | 30.7337 | 3.6044 |
| fading_discolouration | moderate | fading\|discolouration | 5 | 42.2980 | 31.9455 | 2.9958 |
| water_stain_dirt | moderate | water_stain\|dirt_dust | 5 | 16.7260 | 13.9351 | 5.5227 |

    ## Physical and methodological limitations

    ### Single degradation families

    | degradation_type | visual_process_simulated | controlled_mechanism | not_modelled | interpretation_boundary |
| --- | --- | --- | --- | --- |
| blur | Local loss of sharpness and spatial detail. | Gaussian blur blended through a grayscale effect-intensity mask. | Craquelure, pigment displacement, optical scattering, varnish layers, abrasion geometry, or material-specific diffusion. | A controlled image-space blur, not a physical model of paint or varnish deterioration. |
| water_stain | Brownish local staining with darker ring-like boundaries. | Elliptical grayscale support blended with a brown colour field and an edge-darkening term. | Moisture transport, capillary action, tide lines, substrate swelling, pigment bleeding, mould, or drying dynamics. | A visual stain analogue, not a conservation-science simulation of water damage. |
| fading | Local reduction of colour saturation and contrast with a slight brightness increase. | Colour, contrast, and brightness transforms blended through a grayscale effect mask. | Pigment-specific lightfastness, wavelength-dependent exposure, binder ageing, cumulative dose, or selective chemical fading. | A controlled RGB fading effect, not a predictive photochemical ageing model. |
| discolouration | Local channel-dependent colour shift. | Severity-dependent RGB channel scaling blended through a grayscale effect mask. | Pigment reactions, varnish oxidation, fluorescence, metamerism, binder chemistry, or spectral response. | An RGB colour-cast simulation rather than a material-specific discolouration model. |
| dirt_dust | Scattered particles and low-frequency surface grime. | Procedural particle masks combined with diffuse low-frequency support and dark-colour blending. | Particle adhesion, electrostatic deposition, surface topography, cleaning history, embedded dirt, or biological contamination. | A controlled surface-dirt appearance, not a physical deposition or soiling model. |
| partial_transparency | Local visual mixing between the painting and a light substrate-like colour. | Severity-dependent substrate-colour blending through a grayscale effect mask. | Layer thickness, refractive index, scattering, glazing, ground layers, support texture, or wavelength-dependent transparency. | An image-space opacity analogue rather than an optical paint-layer model. |

    ### Combined degradation families

    | degradation_type | components | operator_order | effect_mask_source_operator | interpretation_boundary |
| --- | --- | --- | --- | --- |
| fading_discolouration | fading\|discolouration | fading → discolouration | fading | Component operators are applied sequentially through one shared effect-intensity mask. The case does not model independent spatial supports, physical interactions, reaction kinetics, or causal deterioration sequences. |
| water_stain_dirt | water_stain\|dirt_dust | water_stain → dirt_dust | water_stain | Component operators are applied sequentially through one shared effect-intensity mask. The case does not model independent spatial supports, physical interactions, reaction kinetics, or causal deterioration sequences. |
| blur_fading | blur\|fading | blur → fading | blur | Component operators are applied sequentially through one shared effect-intensity mask. The case does not model independent spatial supports, physical interactions, reaction kinetics, or causal deterioration sequences. |

    ### Experiment-wide scope boundaries

    | scope_area | statement |
| --- | --- |
| material validity | The degradations are controlled visual simulations rather than material or chemical deterioration models. |
| spatial support | Single cases use procedural grayscale effect masks restricted to the processed painting content region. |
| combined cases | Combined cases share one effect mask generated from the first configured component. |
| severity | Severity controls operator parameters and mask generation settings, but does not represent a calibrated physical deterioration scale. |
| ground truth | The clean processed image is retained as the experimental reference, not asserted to be an original historical state. |
| evaluation use | The dataset supports controlled metric and model sensitivity experiments under known synthetic transformations. |

    ## Interpretation boundary

    The generated cases are controlled visual simulations.

    They do not constitute physically complete models of:

    - pigment chemistry;
    - varnish ageing;
    - moisture transport;
    - substrate deformation;
    - biological contamination;
    - spectral response;
    - layered optical behaviour;
    - prior conservation interventions;
    - historical deterioration processes.

    The clean processed images serve as experimental references. They are not claimed to represent verified original historical states.

    ## Canonical figures

    | figure_type | degradation_type | figure_path | file_size_bytes |
| --- | --- | --- | --- |
| severity_grid | blur | outputs/figures/synthetic_degradation/severity_grids/blur__severity_grid.png | 8504707 |
| severity_grid | water_stain | outputs/figures/synthetic_degradation/severity_grids/water_stain__severity_grid.png | 8850300 |
| severity_grid | fading | outputs/figures/synthetic_degradation/severity_grids/fading__severity_grid.png | 8814849 |
| severity_grid | discolouration | outputs/figures/synthetic_degradation/severity_grids/discolouration__severity_grid.png | 8889676 |
| severity_grid | dirt_dust | outputs/figures/synthetic_degradation/severity_grids/dirt_dust__severity_grid.png | 8884907 |
| severity_grid | partial_transparency | outputs/figures/synthetic_degradation/severity_grids/partial_transparency__severity_grid.png | 8773725 |
| combined_grid | fading_discolouration | outputs/figures/synthetic_degradation/combined_grids/fading_discolouration__combined_grid.png | 4456331 |
| combined_grid | water_stain_dirt | outputs/figures/synthetic_degradation/combined_grids/water_stain_dirt__combined_grid.png | 4310229 |
| combined_grid | blur_fading | outputs/figures/synthetic_degradation/combined_grids/blur_fading__combined_grid.png | 4365342 |

    Operator-inspection figures:

    - `outputs/figures/synthetic_degradation/operator_inspection/p001__single_effect_operator_inspection.png`
    - `outputs/figures/synthetic_degradation/operator_inspection/p001__fading_discolouration__operator_inspection.png`

    ## Canonical outputs

    ```text
    data/processed/metadata/metadata_synthetic_degradation.csv
    outputs/07_synthetic_degradation/synthetic_degradation_audit.csv
    data/processed/masks/synthetic_degradation/
    data/processed/degraded/synthetic_degradation/
    outputs/figures/synthetic_degradation/
    outputs/reports/synthetic_degradation_manifest.json
    outputs/reports/synthetic_degradation_report.md
    ```

    ## Permanent CSV policy

    Notebook 07 writes exactly two permanent CSV artifacts:

    1. `metadata_synthetic_degradation.csv`
    2. `synthetic_degradation_audit.csv`

    Severity summaries, progression diagnostics, combined-effect summaries, validation details, determinism details, limitations, and figure manifests remain in memory and are consolidated into the JSON manifest and this Markdown report.

    ## Final result

    Notebook 07 successfully generated and validated **105** deterministic synthetic-degradation cases across **5** paintings.

    All canonical validation, inventory, checksum, preservation, and determinism gates passed.
