# What the additional evidence changes

These examples use saved Controlled-300 measurements, not new restorations or
retrospective expert labels. The full candidate identifiers, all four methods'
values and exact metric-row identifiers are in the
[machine-readable evidence](errata/2026-10-03/framework_examples.json).

## 1. Aggregate conclusion changes: a tie becomes separable

In N28, `only_classical` retains two anchors: masked MAE and crop SSIM. LaMa
wins MAE and Telea wins SSIM, producing `lama|opencv_telea` under the saved
family-balanced comparison policy. `complete_approved_framework` retains eleven
anchors across ten families and produces `lama`. This is an aggregate comparison,
so no single case or candidate ID applies.

The exact N28 source rows are `ablation_1ac0cd489f68a3d6d826` (classical only)
and `ablation_07676bcaa7871b5746bc` (complete framework), in
[`ablation_results.csv`](../outputs/28_metric_and_region_policy_ablation/metrics/ablation_results.csv).
Their 2,620-case count describes coverage: ten constituent anchors use 2,320
nonzero cases, while structural affinity includes 300 identity controls. The
policy outcome is not a universal quality score or independent evidence that
the richer policy is always correct. MAE and mean spatial error are equivalent
scalars; family labels do not make them independent measurements.

## 2. A high structural score hides a relative perceptual disadvantage

Case: `canonical__p009__loss_small`. Candidate:
`candidate__opencv_telea__canonical__p009__loss_small__c00`.

| Method | Crop SSIM ↑ | Crop LPIPS ↓ | Masked MAE ↓ | Masked CIEDE2000 ↓ |
|---|---:|---:|---:|---:|
| Telea | **0.95848** | 0.04945 | 22.92087 | 9.35715 |
| LaMa | 0.95719 | **0.01582** | **18.74647** | **8.08399** |
| HINT | 0.95073 | 0.02097 | 22.00343 | 9.55205 |
| Stable Diffusion | 0.94595 | 0.03955 | 28.31119 | 11.14451 |

SSIM alone places Telea first with a high score. Adding LPIPS shows Telea last
among these four candidates, with approximately 3.13 times LaMa's LPIPS error.
LaMa also has lower masked pixel and colour error. Thus “highest SSIM” does not
mean “best on perceptual or colour fidelity.” This is a measured relative
disadvantage, not an asserted visual defect or expert rejection threshold.

Selection rule: among the 1,200 canonical nonzero cases, retain candidates with
SSIM ≥ 0.9, SSIM rank 1 and LPIPS rank 4 within the four primary methods. Select
the first case ID/candidate ID in lexicographic order. There were 82 qualifying
candidates. The threshold is an illustrative selection rule, not a validated
quality-acceptance threshold. Stable Diffusion uses its preselected generic
prompt, seed 2026; no best-seed search was used.

## 3. Counterexample: richer evidence leaves the conclusion unchanged

Case: `canonical__p002__loss_large`. Candidate:
`candidate__lama__canonical__p002__loss_large__c00`.

| Method | Crop SSIM ↑ | Crop LPIPS ↓ | Masked MAE ↓ | Masked CIEDE2000 ↓ |
|---|---:|---:|---:|---:|
| LaMa | **0.79148** | **0.23599** | **24.03544** | **9.21658** |
| Telea | 0.77649 | 0.32379 | 28.82129 | 11.01603 |
| HINT | 0.69014 | 0.33641 | 31.84892 | 13.00569 |
| Stable Diffusion | 0.69063 | 0.28219 | 34.36687 | 13.77354 |

LaMa wins both SSIM and LPIPS, and the added masked pixel/colour measurements
agree. Here, additional evidence corroborates the simpler ordering rather than
changing it. Agreement among metrics still does not establish historical
authenticity.

Selection rule: first canonical nonzero case ID/candidate ID in lexicographic
order with both SSIM rank 1 and LPIPS rank 1 (416 qualifying candidates).
Ranks use the minimum rank for ties. Neither example estimates how frequently
a trained conservator would change a decision.

## Traceability

The case examples use the same saved measurement sources underlying N21:
N13 `classical_metrics.csv` (SSIM and MAE), N14 `lpips_metrics.csv`, and N17
`local_consistency.csv` (CIEDE2000). The linked JSON lists each exact source
path and row ID for all sixteen measurements per example. Input SHA-256 hashes
and the deterministic selection implementation are recorded in the
[errata verification receipt](errata/2026-10-03/verification.json) and
[`build_reporting_errata.py`](../tools/build_reporting_errata.py).
