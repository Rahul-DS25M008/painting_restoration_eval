# Mask-Robustness Dataset Generation Report

    ## Experiment

    Notebook stage: `06_mask_robustness`

    This experiment generated controlled mask variants for evaluating sensitivity to damage geometry and placement.

    The design contains:

    - 5 paintings;
    - 3 mask families;
    - 5 variants per painting and mask family;
    - 15 robustness groups;
    - 75 total cases;
    - deterministic generation using global seed `20260606`.

    ## Selected paintings

    - `p001`
- `p018`
- `p026`
- `p039`
- `p043`

    ## Mask-family targets

    | Mask family | Cases | Target | Mean realised | Mean absolute error | Maximum absolute error |
    |---|---:|---:|---:|---:|---:|
    | `loss_large` | 25 | 12.500% | 12.5035% | 0.0110 pp | 0.0258 pp |
| `loss_small` | 25 | 4.500% | 4.4916% | 0.0113 pp | 0.1638 pp |
| `scratch_thin` | 25 | 2.000% | 1.9769% | 0.0321 pp | 0.3041 pp |

    Maximum permitted percentage error:

    `0.5` percentage points.

    Maximum observed percentage error:

    `0.304149` percentage points.

    ## Robustness controls

    Every robustness group contains five independently generated variants for the same:

    - painting;
    - mask family;
    - target damaged-area percentage.

    Variants differ through deterministic changes to geometry and placement.

    Recorded characteristics include available measures of:

    - connected-component structure;
    - largest-component fraction;
    - bounding-box geometry;
    - perimeter-to-area ratio;
    - centroid location;
    - centroid quadrant;
    - content-border contact.

    ## Validation

    The completed dataset passed checks for:

    - expected case and group counts;
    - unique case identifiers;
    - unique deterministic seeds;
    - unique masks and damaged images within every group;
    - file existence and readability;
    - image dimensions and formats;
    - binary-mask validity;
    - target-area tolerance;
    - preservation outside masks;
    - correct fill inside masks;
    - checksum consistency;
    - metadata save and reload;
    - missing, stale, orphan, non-PNG, and zero-byte files;
    - creation of all 15 robustness-group figures.

    Observed validation totals:

    - validation failures: `0`;
    - changed pixels outside masks: `0`;
    - incorrect fill pixels inside masks: `0`;
    - groups passing distinctness checks: `15/15`;
    - cases requiring more than one generation attempt: `4`.

    ## Canonical outputs

    Dataset artifacts:

    - `data/processed/masks/mask_robustness/`
    - `data/processed/damaged/mask_robustness/`
    - `data/processed/metadata/metadata_mask_robustness.csv`

    Audit:

    - `outputs/06_mask_robustness/mask_robustness_audit.csv`

    Figures:

    - `outputs/figures/mask_robustness/`

    Experiment manifest:

    - `outputs/reports/mask_robustness_manifest.json`

    ## Scope boundary

    This notebook establishes the controlled mask-robustness dataset only.

    Restoration inference, robustness metric variance, model comparisons, statistical testing, and thesis-level interpretation are intentionally deferred to later notebooks.
