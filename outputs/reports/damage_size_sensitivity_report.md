# Damage-Size Sensitivity Dataset Generation Report

    ## Experiment

    Notebook stage: `05_damage_size_sensitivity`

    The experiment generated matched synthetic-damage cases at multiple damage-area levels while retaining the same canonical `loss_large` base-mask morphology for each painting.

    The generated dataset contains:

    - 5 paintings;
    - 7 target damage levels;
    - 35 total cases;
    - target levels of 2%, 4%, 6%, 8%, 10%, 15%, 20%;
    - deterministic generation using global seed `20260505`;
    - constant RGB damage fill `(255, 255, 255)`.

    ## Selected paintings

    - `p001`
- `p018`
- `p026`
- `p039`
- `p043`

    ## Generation accuracy

    | Target | Cases | Mean realised | Mean absolute error | Maximum absolute error |
    |---:|---:|---:|---:|---:|
    | 2% | 5 | 2.0023% | 0.0045 pp | 0.0070 pp |
| 4% | 5 | 3.9942% | 0.0060 pp | 0.0152 pp |
| 6% | 5 | 5.9994% | 0.0094 pp | 0.0157 pp |
| 8% | 5 | 7.9974% | 0.0106 pp | 0.0137 pp |
| 10% | 5 | 10.0036% | 0.0090 pp | 0.0207 pp |
| 15% | 5 | 14.9906% | 0.0110 pp | 0.0217 pp |
| 20% | 5 | 20.0070% | 0.0124 pp | 0.0256 pp |

    Maximum permitted percentage error:

    `0.5` percentage points.

    Maximum observed percentage error:

    `0.025570` percentage points.

    ## Validation

    The completed dataset passed the following checks:

    - expected case count;
    - unique case identifiers;
    - expected painting and target-level distribution;
    - successful generation status;
    - target-area tolerance;
    - binary-mask validation;
    - preserved pixels outside the mask;
    - correct fill inside the mask;
    - image and mask checksum validation;
    - missing-file detection;
    - orphan-file detection;
    - zero-byte-file detection;
    - metadata save-and-reload validation.

    Observed validation totals:

    - failed cases: `0`;
    - changed pixels outside masks: `0`;
    - incorrect fill pixels inside masks: `0`;
    - checksum failures: `0`.

    ## Canonical outputs

    Dataset artifacts:

    - `data/processed/masks/damage_size_sensitivity/`
    - `data/processed/damaged/damage_size_sensitivity/`
    - `data/processed/metadata/metadata_damage_size_sensitivity.csv`

    Audit:

    - `outputs/05_damage_size_sensitivity/damage_size_sensitivity_audit.csv`

    Figures:

    - `outputs/figures/damage_size_sensitivity/`

    Experiment manifest:

    - `outputs/reports/damage_size_sensitivity_manifest.json`

    ## Interpretation boundary

    This notebook establishes the controlled damage-size sensitivity dataset only.

    It does not compare restoration models or make claims about restoration performance. Restoration generation, metric curves, statistical comparisons, and thesis-level interpretation will be performed in later analysis notebooks.
