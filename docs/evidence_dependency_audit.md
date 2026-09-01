# Evidence Dependency Audit

## 1. Status and authority

This document is the human-readable evidence-coverage gate for the remaining
notebook pipeline. It must be read together with:

- `docs/refactoring_implementation_guidelines.md`;
- `docs/final_notebook_roadmap.md`;
- `config/evaluation/evidence_coverage.yaml`.

The machine-readable YAML is authoritative for automated preflight. This file
explains the scientific meaning of that registry and records the decisions that
must not be silently reversed during later notebook planning.

## 2. Frozen baseline

Notebooks 01–21 and their notebook-owned canonical outputs are frozen. Their
last common validated data-producing baseline is repository commit `0aac25ef`
(`notebook 21 done`). Later documentation and governing-file commits do not
change the scientific population recorded by those manifests.

Frozen means:

- no `.ipynb` source changes;
- no rerunning or appending to Notebook 01–21 output roots;
- no helper/configuration change may be used to reinterpret a frozen manifest as
  if it described a newly expanded population;
- later evidence extensions own new candidates and artifacts under their own
  notebook output roots;
- consumers join frozen and extension evidence through stable identifiers and
  explicit ownership fields.

The frozen validation state contains no blocking validation failure. Notebook 15
retains one declared non-blocking CUDA/CuBLAS bitwise-repeatability warning;
metric validity and coverage passed.

## 3. Frozen notebook evidence ledger

| Notebook | Frozen evidence | Validated coverage | Downstream interpretation boundary |
|---|---|---:|---|
| 01 Dataset Verification | artwork registry and dataset audit | 50 controlled artworks; 5 balanced visual categories | `style_or_period`, `date_or_period`, and `medium` are populated for 18/50 artworks; category is complete; no expanded dataset exists |
| 02 Image Preprocessing | 768×768 clean references and content geometry | 50 paintings | content bounds, resize, and padding are authoritative; later notebooks must not infer bounds from padding colour |
| 03 Canonical Mask Generation | binary mask families and morphology | 250 masks | deterministic controlled masks; synthetic masks are not physical conservation damage |
| 04 Canonical Damaged Images | canonical case table and damaged images | 250 cases | 50 zero controls and 200 non-zero binary missing-region cases |
| 05 Damage-Size Dataset | nested masks, damaged images, and generation audit | 35 cases = 5 paintings × 7 levels | one painting per category; category and painting identity are confounded |
| 06 Mask Robustness Dataset | matched mask variants and geometry | 75 cases = 15 groups × 5 variants | variation is input-mask robustness, not diffusion seed uncertainty; one painting per category |
| 07 Synthetic Degradation Dataset | procedural degradation cases and operator audit | 165 generated cases | 50 cases are restoration-eligible; one painting per category; operators are controlled simulations, not exact conservation damage |
| 08 Experiment Contracts | case registry, model eligibility, region policy, schema registry | 525 cases; 2,100 eligibility rows; 143 metric-region rows | 410 cases are eligible for each restoration method; region ablation memberships are encoded in `ablation_policy_ids_json` |
| 09 OpenCV Telea | deterministic restorations and runtime | 410 completed candidates | fixed classical baseline; no generative uncertainty |
| 10 LaMa | deterministic restorations and runtime | 410 completed candidates | deterministic learned baseline; no generative uncertainty |
| 11 Stable Diffusion | primary, prompt-context, scratch-aware, and repeated-seed candidates | 1,330 completed candidates; 410 primary | complete four-seed groups exist only for canonical cases; all 35 damage-size cases have one seed |
| 12 SDXL | technically validated partial candidates | 10 completed cases | partial evaluation only: 4 canonical and 6 synthetic cases; one seed per case |
| 13 Classical Metrics | MSE, MAE, PSNR, SSIM | 63,018 rows | reference-based metrics do not establish semantic or conservation correctness |
| 14 LPIPS | perceptual distance | 4,170 rows | content and mask-crop regions only; sparse masked pixels are not treated as images |
| 15 Feature Similarity | CLIP/DINOv2 metrics and reusable embeddings | 8,340 metric rows; 10,700 embeddings | diagnostic pretrained features; one non-blocking CUDA bitwise-repeatability warning |
| 16 Spatial Diagnostics | error/improvement metrics and maps | 18,896 rows; 10,062 image assets | spatial error evidence is distinct from uncertainty and final trustworthiness flags |
| 17 Local Consistency | texture, colour, seam, and brushstroke-proxy evidence | 271,988 rows; 3,282 image assets | 3,308 chroma rows are legitimately `not_applicable` where no sufficiently chromatic pixels exist; brushstroke proxies are not authentication |
| 18 Diffusion Uncertainty | repeated-seed scalar and calibration-ready components | 130 groups; 20,800 metric rows | 80 generic and 50 scratch-aware canonical groups only; no damage-size, robustness, or synthetic groups |
| 19 Spatial Explanations | uncertainty maps and integrated diagnostic panels | 780 scalar rows; 1,055 map assets | spatial uncertainty is available only for the 130 frozen Notebook 18 groups |
| 20 Semantic/Structural Consistency | patch-level semantic and structural proxies | 58,980 rows; 9,430 map assets | category-conditioned proxies are not validated face, anatomy, object, iconographic, or conservation detectors; 118 outside-context values are not estimable at the encoder grid |
| 21 Multi-Model Comparison | comparison, disagreement, representative cases, self-contained report | 86,531 comparison rows; 839 disagreement rows | three-model comparison covers 410 paired cases; four-model comparison covers the 10-case SDXL subset; uncertainty is contextual, not a cross-model quality vote |

## 4. Validated population facts

```text
dataset scope: controlled_50
artworks: 50
case registry: 525
eligible restoration cases: 410
Telea candidates: 410
LaMa candidates: 410
Stable Diffusion primary candidates: 410
Stable Diffusion total candidates: 1,330
SDXL candidates: 10
all evaluated candidates: 2,160
frozen complete uncertainty groups: 130
frozen damage-size uncertainty groups: 0
```

Stable Diffusion complete four-seed groups in the frozen baseline:

| Scope | Generic groups | Scratch-aware groups |
|---|---:|---:|
| Canonical missing-region | 80 | 50 |
| Damage-size sensitivity | 0 | 0 |
| Mask robustness | 0 | 0 |
| Synthetic degradation | 0 | 0 |

Prompt variants at a single seed measure prompt sensitivity and cannot be used as
a replacement for repeated-seed uncertainty.

## 5. Completed post-freeze evidence and analysis stages

Notebook 22, `22_damage_size_diffusion_uncertainty_extension.ipynb`, is the only
approved missing-evidence generation extension. It completed at commit
`547a8687` (`notebook 22 done`) with its completion gate passed.

It:

- referenced the 35 frozen Notebook 11 generic seed-2026 damage-size candidates;
- generated seeds 2027–2029 for the same 35 cases;
- owns exactly 105 new restoration images;
- constructed 35 complete four-seed uncertainty groups and 210 unique unordered
  seed pairs;
- persisted 4,760 transparent RGB, LPIPS, CLIP, DINOv2, regional, pairwise, and
  reference-evidence metric rows plus 35 raw uncertainty maps and 35 overlays;
- passed all 234 validation checks and all 12 roadmap traceability requirements;
- left every Notebook 01–21 source and output untouched.

Notebook 23 may therefore test generative uncertainty against target and realized
damage size. Notebook 18 remains the canonical uncertainty source for its original
canonical-case population; Notebook 22 is the canonical source for damage-size
uncertainty. Notebook 22 is now a read-only approved upstream dependency.

Notebook 23, `23_damage_size_sensitivity_analysis.ipynb`, subsequently completed
the approved damage-size analysis with its completion gate passed. It:

- analyzed five matched painting trajectories at seven nested target levels using
  35 cases and 105 primary candidates from OpenCV Telea, LaMa, and Stable
  Diffusion Inpainting;
- retained 11 quality anchors as separate evidence and used both target and
  realized damaged fractions rather than constructing a combined quality score;
- persisted 1,901 canonical analysis rows, including 646 rows with inferential
  evidence, and retained painting as the independent unit;
- covered painting-level adverse slopes, adjacent deterioration, paired model
  contrasts, evaluated-baseline contrasts, family-balanced rankings,
  leave-one-painting-out stability, uncertainty trends, and exploratory
  size-adjusted morphology associations;
- produced three canonical figures and a self-contained 13-section HTML report
  with 10 analytical views, eight restoration or diagnostic panels, 18 embedded
  images, 95 panel tiles, and no external image dependency;
- passed all 115 validation checks and all 10 roadmap traceability requirements
  with zero blocking or warning failures;
- registered exactly six non-self-referential artifacts and eight canonical files
  under `outputs/23_damage_size_sensitivity_analysis/`.

Notebook 23 is now the canonical scalar and report source for the controlled
damage-size sensitivity experiment. Downstream consumers must preserve target
and realized exposure definitions, the five-painting dependency structure,
metric-family disagreement, and the boundary that empirical Stable Diffusion
seed variability is not calibrated confidence. The analysis does not estimate
independent category or style effects and does not establish a universal damage
threshold or conservation approval.

Notebook 24, `24_mask_robustness_analysis.ipynb`, subsequently completed the
approved input-mask robustness analysis with its completion gate passed. It:

- analyzed five paintings, three fixed family–area conditions, 15 matched
  robustness groups, five mask variants per group, 75 cases, and 225 preselected
  primary candidates from OpenCV Telea, LaMa, and Stable Diffusion Inpainting;
- retained 11 quality anchors as separate evidence and persisted 5,373 unique
  canonical rows covering variant quality, within-group dispersion, paired model
  contrasts, family-balanced ranks, winner stability, morphology associations,
  painting and fixed family–area profiles, and operational runtime dispersion;
- treated paintings as the independent units and mask variants as repeated
  observations nested within painting–family groups;
- found LaMa to be the broadest descriptive robustness leader, while none of the
  132 paired model contrasts or 297 exploratory morphology associations survived
  FDR correction;
- preserved the design boundary that `scratch_thin`, `loss_small`, and
  `loss_large` are paired with target damaged fractions of 2%, 4.5%, and 12.5%,
  so independent mask-family and damage-size effects cannot be separated;
- produced two canonical figures and a self-contained 13-section HTML report
  with 10 analytical views, eight restoration or diagnostic panels, 18 embedded
  images, 149 panel tiles, and no external image dependency;
- passed all 136 validation checks and all nine roadmap traceability requirements
  with zero blocking or warning failures;
- registered exactly five non-self-referential artifacts and seven canonical
  files under `outputs/24_mask_robustness_analysis/`.

Notebook 24 is now the canonical scalar and report source for the controlled
mask-placement robustness experiment. Downstream consumers must preserve the
matched five-variant grouping, the five-painting dependency structure, metric-
family disagreement, and the distinction between input-mask robustness and
stochastic candidate uncertainty. Low dispersion does not establish restoration
quality, historical authenticity, or conservation approval. Runtime remains
operational evidence and must not enter quality ranking.

Notebook 25, `25_synthetic_degradation_analysis.ipynb`, subsequently completed
the approved synthetic-degradation analysis with its completion gate passed. It:

- audited all 165 Notebook 07 procedural cases while restricting model comparison
  to the 50 localized cases approved by Notebook 08;
- analyzed 150 primary core candidates, comprising 50 OpenCV Telea, 50 LaMa, and
  50 Stable Diffusion Inpainting candidates, plus a separate bounded six-case
  SDXL subset;
- retained 11 quality anchors as separate evidence and persisted 4,695 unique
  canonical rows across 17 analysis kinds without creating a combined quality,
  efficiency, uncertainty, or trust score;
- covered eligibility and exclusions, degradation family, configured severity,
  affected area, painting-level slopes, paired model contrasts, ordered combined-
  component contrasts, failure profiles, spillover, family-balanced ranks, runtime,
  and the bounded SDXL subset;
- found LaMa to have the best overall family-balanced rank, to lead all four
  eligible degradation families, and to lead eight of 11 individual anchors;
  no paired core-model, severity, or affected-area result survived FDR correction;
- preserved the boundaries that procedural RGB effects are not exact material-
  conservation simulations, painting and category are confounded, the ordered
  water-stain-and-dirt condition is not a physical interaction experiment, and
  repeated-seed synthetic-degradation uncertainty is unavailable;
- produced two canonical figures and a self-contained 15-section HTML report
  with 14 analytical views, nine restoration or diagnostic panels, 23 embedded
  images, 238 panel tiles, and no external image dependency;
- passed all 125 validation checks and all nine roadmap traceability requirements
  with zero blocking or warning failures;
- registered exactly five non-self-referential artifacts and seven canonical
  files under `outputs/25_synthetic_degradation_analysis/`.

Notebook 25 is now the canonical scalar and report source for the controlled
synthetic-degradation experiment. Downstream consumers must use its eligibility
ledger rather than treating excluded objectives as model failures, retain painting
as the independent unit, keep runtime separate from quality, and preserve metric-
family disagreement. Its six-case SDXL evidence is descriptive only. It does not
support independent category or style effects, physical degradation interaction,
historical authenticity, conservation approval, or synthetic-degradation
uncertainty.

Notebook 26, `26_grouped_and_statistical_analysis.ipynb`, subsequently completed
the approved cross-experiment statistical synthesis with its completion gate
passed. It:

- selected 1,230 metric-independent primary core candidates across 410 cases and
  kept the ten completed SDXL candidates as a separate bounded descriptive subset;
- excluded 150 canonical zero-control candidates from restoration-quality
  inference, leaving 1,080 nonzero core candidates while retaining the controls as
  integrity evidence;
- retained 11 quality anchors as separate evidence and persisted 4,174 statistical
  result rows across 14 result kinds, 504 metric-correlation rows across five
  correlation kinds, and 258 ranking-stability rows across six sensitivity kinds;
- used painting as the independent unit while preserving cases, candidates,
  mask variants, seeds, regions, metrics, and within-painting trajectories as
  repeated or nested evidence;
- combined the 130 canonical and 35 damage-size prompt-specific repeated-seed
  groups without pooling the generic and scratch-aware prompt arms, and did not
  assign artificial uncertainty to mask robustness or synthetic degradation;
- covered descriptive statistics, confidence intervals, paired comparisons,
  matched effect sizes, non-parametric tests, FDR correction, metric and region
  disagreement, uncertainty associations, ranking sensitivity, and operational
  quality-versus-compute associations without creating a combined score;
- found LaMa to be the strongest overall computational model across ten of the
  eleven retained quality anchors, while keeping metric-specific exceptions,
  disagreement, and the faster operational Telea baseline visible;
- produced three canonical figures and a self-contained 15-section HTML report
  with 12 analytical views, 22 restoration panels, 34 embedded images, 132 panel
  tiles, and no external image dependency;
- passed all 111 validation checks and all 12 roadmap traceability requirements
  with zero blocking or warning failures;
- registered exactly eight non-self-referential artifacts and ten canonical files
  under `outputs/26_grouped_and_statistical_analysis/`.

Notebook 26 is now the canonical grouped-statistics source for downstream failure
taxonomy, ablation, reporting, dashboard, and thesis-synthesis stages. Consumers
must preserve metric-family and region-policy disagreement, the independent-unit
boundary, prompt-arm separation, the single-dataset limitation, and the distinction
between empirical seed variability and calibrated confidence. Runtime remains
operational evidence outside quality ranking. The analysis does not establish an
independent style effect, a between-dataset comparison, a full SDXL comparison,
historical authenticity, conservation suitability, museum approval, or a universal
quality or trust score.

Notebook 27, `27_failure_taxonomy_and_trustworthiness_flags.ipynb`, subsequently
completed the approved failure-taxonomy and trustworthiness-flag analysis with its
completion gate passed. It:

- assembled the exact 1,785-candidate union containing 1,240 primary candidates,
  660 candidates in 165 complete four-seed groups, 115 candidates shared by the
  primary and uncertainty populations, and 545 uncertainty-only candidates;
- persisted a 14-row versioned failure taxonomy, the complete 24,990-row
  candidate-by-category assignment grid, and the complete 19,635-row
  candidate-by-flag grid;
- retained `triggered`, `not_triggered`, `insufficient_evidence`, and
  `not_applicable` as distinct states and did not treat missing evidence as a
  passing result;
- applied transparent experiment-stratified warning and critical thresholds,
  excluded zero controls and bounded SDXL from threshold fitting, kept prompt arms
  separate, and used strict adverse comparisons for percentile ties while retaining
  inclusive explicit absolute tolerances;
- generated 11 independent flags, candidate-level co-occurrence and disagreement
  evidence, and exactly one of four review recommendations for every candidate
  without constructing a combined trust score;
- limited stochastic uncertainty to the 165 supported repeated-seed groups,
  recorded deterministic-method uncertainty as not applicable, and recorded the
  bounded ten-case single-seed SDXL subset as insufficient for uncertainty;
- produced one canonical four-panel figure and a self-contained 15-section HTML
  report with seven analytical views, seven rule-selected diagnostic panels, 49
  diagnostic tiles, 56 embedded images, and no external image dependency;
- passed all 167 validation checks, all 12 roadmap requirements, and all 29
  mock-to-final traceability rows with zero blocking or warning failures;
- registered exactly six non-self-referential artifacts and eight canonical files
  under `outputs/27_failure_taxonomy_and_trustworthiness_flags/`.

Notebook 27 is now the canonical source for downstream failure categories,
candidate-category assignments, independent trustworthiness flags, and transparent
review recommendations. Consumers must preserve population roles, prompt-arm
separation, missingness, proxy language, threshold provenance, and the distinction
between empirical seed variability and calibrated confidence. The flags and
recommendations are operational decision support. They do not establish historical
authenticity, physical-treatment suitability, conservation approval, a full SDXL
comparison, or a universal trust score.

## 6. Remaining-notebook evidence gate

| Notebook | Supported evidence contract | Required scope discipline |
|---|---|---|
| 28 Metric/region ablation | N08 ablation memberships, N21 rankings, N27 rules | preserve metric-family disagreement; do not create a universal trust score |
| 29 XAI/retrieval | embeddings, numeric maps, counterfactual experiment structures, rule-defined flags | retrieval labels are rule-defined; seed comparisons use only complete uncertainty groups |
| 30 Model cards/compute | model manifests, runtimes, hardware, inventory, primary model sources | larger-dataset and SDXL costs are projections, not executed results |
| 31 Model reports | N09–30 evidence | report model and experiment coverage exactly; uncertainty appears only where supported |
| 32 Case/painting reports | N09–31 evidence | include only evidence applicable to each case and model |
| 33 Final evaluation report | N21–32 plus frozen methodology artifacts | report controlled-50 results and transparent projections; no human or conservation validation claim |
| 34 Dashboard assets | N01–33 canonical outputs | package evidence without recomputation and retain scope labels |
| 35 Dashboard/deployment validation | N34 assets and application | validate paths, schemas, rendering, and deployment state; do not recompute metrics |
| 36 Reproducibility package | N01–35 manifests and selected artifacts | reconcile package contents with the controlled evidence and declared projections |

## 7. Removed unsupported promises

The following items were removed from the future roadmap and must not be silently
reintroduced without new evidence and an updated audit:

- inferential category/style interactions in the five-painting damage-size,
  robustness, and synthetic-degradation cohorts;
- treating feature or semantic affinity as an independent human visual-
  plausibility rating;
- automatic verified face, anatomy, or object-hallucination detection;
- describing associations with rule-derived computational flags as uncertainty
  calibration or calibrated confidence;
- presenting expanded-main or approximately 300-painting experimental results;
- describing prompt sensitivity or mask-placement robustness as generative
  uncertainty.

## 8. Repository ownership debt

The scientific freeze does not make legacy global output folders canonical.
`outputs/inventory/` remains the sole approved global exception.

The post-Notebook-26 audit identified 56 tracked legacy files under:

```text
outputs/figures/
outputs/metrics/
outputs/reports/
outputs/manifests/
outputs/validation/
```

It also found legacy notebooks whose numbers overlap later roadmap stages. They
remain non-canonical until a separate exact-path migration/deletion audit is
approved. No future notebook may consume them merely because they exist.

The user removed all 56 files and the five empty non-canonical runtime directories
under the output roots of Notebooks 10, 11, 12, 25, and 26 in commit `bbb2c6fc`.
The cleanup was verified with a clean, synchronized Git worktree: no legacy global
output tree remains, every numbered Notebook 01--26 output root remains present,
and `outputs/inventory/` remains the sole global output exception.

## 9. Update protocol

Before Batch 1 of every remaining notebook:

1. Resolve every responsibility to an entry in
   `config/evaluation/evidence_coverage.yaml`.
2. Confirm exact source paths, row/file counts, population filters, and ownership.
3. Confirm the independent statistical unit and repeated/nested observations.
4. Remove any result or report claim that lacks validated evidence.
5. Add planned outputs and checks to the consumer contract.

At completion:

1. Update the YAML with actual counts and the new manifest path.
2. Update this document's ledger and remaining-notebook table.
3. Refresh `outputs/inventory/`.
4. Commit the notebook, owned outputs, governing-file updates, and inventory
   together unless an approved staged commit is required.
