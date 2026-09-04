# Evidence Dependency Audit

## 1. Status and authority

This document is the human-readable evidence-coverage ledger for the completed
36-notebook pipeline and the gate for any later extension. It must be read together with:

- `docs/refactoring_implementation_guidelines.md`;
- `docs/final_notebook_roadmap.md`;
- `config/evaluation/evidence_coverage.yaml`.

The machine-readable YAML is authoritative for automated preflight. This file
explains the scientific meaning of that registry and records the decisions that
must not be silently reversed during later notebook planning.

**Maintenance review: 2026-09-04.** All 36 saved run manifests record
`run_status: completed` and `completion_gate_passed: true`. All completed
notebooks and their canonical outputs are now frozen. Sections 2–4 preserve the
original Notebook 01–21 baseline; Sections 5–6 record completed extensions and
delivery. Section 6.1 records later application delivery separately from those
execution-time records. Non-blocking warnings are retained, not silently cleared.

The subsequent maintenance batch added a separate
`post_completion_maintenance` record to `config/evaluation/evidence_coverage.yaml`
(configuration version 1.0.1). Existing producer records, counts, warnings, and
N35/N36 `external_deployment_recorded: false` fields remain unchanged: those
fields describe the original runs, not the later public deployment. No scientific
coverage changed. The executed N11/N12 contracts now link to their completion
evidence, and the experimental requirements header distinguishes its legacy
recipe from the actual saved environments without changing dependency pins.

## 2. Original frozen baseline and completed-pipeline protection

Notebooks 01–21 and their notebook-owned canonical outputs are frozen. Their
last common validated data-producing baseline is repository commit `0aac25ef`
(`notebook 21 done`). Later documentation and governing-file commits do not
change the scientific population recorded by those manifests.

Notebooks 22–36 subsequently completed their own gates and now have the same
read-only protection. They retain separate provenance rather than being folded
back into the original baseline commit.

Frozen means:

- no `.ipynb` source changes;
- no rerunning or appending to any completed Notebook 01–36 output root;
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

## 4. Original Notebook 01–21 population facts

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
completed restoration candidates in Notebooks 09–12: 2,160
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

### Final delivery population, distinct from the original baseline

| Population | Count | Ownership and interpretation |
|---|---:|---|
| Controlled paintings | 50 | Five balanced visual categories; not independently established art-historical style effects |
| Registered cases | 525 | Notebook 08; includes cases outside restoration eligibility |
| Restoration-eligible cases | 410 | Includes 50 zero controls and 360 nonzero cases |
| N09–N12 completed restoration candidates | 2,160 | Original generation scope, not the final reporting denominator |
| N22 additional candidates | 105 | Three additional seeds for each of 35 damage-size cases; separately owned |
| Retained reporting/dashboard candidates | 1,785 | Approved downstream selection, not every generated candidate and not expert quality approval |
| Complete repeated-seed groups | 165 | 130 canonical groups from N18 plus 35 damage-size groups from N22 |
| Bounded SDXL candidates | 10 | Included in the retained population; one seed per case, not repeated-seed uncertainty |

The additional 105 N22 candidates do not have individual reference-quality rows
in the frozen N13/N14/N15/N17/N20 tables. Their group uncertainty evidence remains
available; consumers must not substitute the seed-2026 anchor's quality values.
Notebook 18 contains no combined uncertainty index, no fitted confidence
calibration, and no SDXL repeated-seed comparison. N19 owns the original 130-group
spatial uncertainty archive; N22 owns the damage-size uncertainty maps.

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

Notebook 23 used this evidence to test generative uncertainty against target and
realized damage size. Notebook 18 remains the canonical uncertainty source for
its original canonical-case population; Notebook 22 is the canonical source for damage-size
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

Notebook 28, `28_metric_and_region_policy_ablation.ipynb`, subsequently
completed the approved evaluation-policy sensitivity analysis with its completion
gate passed. It:

- evaluated exactly 23 controlled scenarios: the complete-framework baseline,
  eleven alternative metric-family configurations, six alternative region
  policies, two threshold alternatives, and three flag-aggregation alternatives;
- retained the matched 1,230-candidate, 410-case three-model population for the
  18 ranking-applicable scenarios and the complete 1,785-candidate Notebook 27
  union for flag-stability analysis, with the ten bounded SDXL candidates limited
  to separate flag diagnostics;
- persisted 7,710 canonical ablation rows comprising 54 model-rank rows, 7,380
  case-priority-rank rows, 253 scenario-by-flag summaries, and 23 scenario
  summaries, plus 41,055 compact candidate-by-scenario flag-stability rows;
- retained one equal contribution per available evidence family, kept runtime
  and deterministic artificial uncertainty outside quality ranking, preserved
  explicit insufficient-evidence states, and did not construct a continuous
  quality, case-trust, or universal trust score;
- found that LaMa remained a winner in all 18 ranking-applicable scenarios, with
  a transparent LaMa–Telea tie under the classical-only policy, while diagnostic
  case priorities were strongly policy-sensitive: outside-mask-only and
  boundary-only case-rank correlations with the complete framework were 0.097
  and 0.381, respectively;
- showed that stable model-level conclusions do not imply stable candidate-level
  screening: removing DINOv2-derived evidence changed at least one flag for
  1,773 of 1,785 candidates, and single-family or region-restricted policies often
  created substantial insufficient-evidence populations rather than genuine
  improvements;
- retained six supported descriptive subgroup dimensions with a minimum of five
  independent paintings and explicitly labelled painting-category summaries as
  controlled and confounded;
- produced two canonical figures and a self-contained 12-section HTML report
  with five analytical views, six diagnostic panels, 18 diagnostic tiles, 23
  embedded images, and no external image dependency;
- passed all 122 validation checks and all 13 roadmap traceability requirements
  with zero blocking or warning failures;
- registered exactly six non-self-referential artifacts and eight canonical files
  under `outputs/28_metric_and_region_policy_ablation/`, with no retained runtime
  checkpoint files.

Notebook 29, `29_explainable_ai_and_case_retrieval.ipynb`, subsequently
completed the approved explanation-catalog and case-retrieval analysis with its
completion gate passed. It:

- persisted the complete approved 1,785-candidate, 410-case Notebook 27 union in
  `data/explanation_cases.csv`, rather than restricting the canonical table to
  the 24 report-selected visual units;
- retained 7,140 resolving clean, damaged, mask, and restored-image references,
  eleven independent flag records per candidate, applicable map families,
  uncertainty membership, evidence provenance, affected regions, recommended
  actions, explicit missingness, and report-selection traceability;
- recorded 1,680 candidates with both restored-content DINOv2 and CLIP evidence
  and kept the 105-candidate damage-size extension explicitly retrieval-ineligible
  because Notebook 15 did not compute embeddings for that later extension;
- selected ten deterministic queries spanning lower-risk and flagged examples in
  all five complete artwork categories, then persisted 100 neighbour rows: five
  rule-defined lower-risk and five flagged neighbours per query;
- used DINOv2 as the primary retrieval view and CLIP as a separate secondary view,
  never combined the feature scores, and excluded self, same-case, and
  same-painting leakage;
- generated fourteen counterfactual panels, two each for damage size, mask
  placement, cross-model behaviour, metric subsets, diffusion seeds,
  evidence-family removal, and generic versus scratch-aware damage-specific
  prompting, plus ten case-retrieval panels;
- retained exactly 660 candidate members in 165 supported repeated-seed groups
  and preserved deterministic and single-seed non-applicability rather than
  assigning artificial uncertainty;
- produced a self-contained 14-section HTML report with fourteen counterfactual
  panels, ten retrieval panels, five analytical views, 34 embedded images, and no
  external image dependency while preserving the approved mock structure;
- passed all 145 validation checks and all 13 roadmap traceability requirements
  with zero blocking or warning failures;
- registered exactly six non-self-referential artifacts and 30 physical files
  under `outputs/29_explainable_ai_and_case_retrieval/`, with no temporary files.

Notebook 29 is now the canonical source for downstream candidate-level
explanation discovery and selected similar-case examples. Consumers must use the
complete 1,785-row catalog when complete case coverage is required, treat the 24
visual units as report examples only, preserve DINOv2 and CLIP as separate views,
and retain retrieval exclusions and embedding-ineligibility states. Category is
the complete primary grouping; style or period is descriptive for 18 of 50
paintings. Retrieval similarity, operational recommendations, counterfactual
changes, and empirical seed variability do not establish restoration correctness,
calibrated confidence, historical authenticity, conservation approval, or
universal model superiority.

Notebook 30, `30_model_cards_compute_and_scalability.ipynb`, subsequently
completed the approved model-card and compute/scalability stage with its
completion gate passed. It:

- persisted four machine-readable method cards and four portable standalone
  Markdown cards for OpenCV Telea, LaMa, Stable Diffusion Inpainting, and SDXL
  Inpainting;
- recorded exact implementation identity, versions and revisions, licences,
  available training-data disclosure, intended and unsupported uses, input and
  mask constraints, painting-domain gaps, limitations, hardware, and evaluation
  status for every method;
- retained the full evaluated populations of 410 Telea, 410 LaMa, and 1,330
  Stable Diffusion candidates, while keeping SDXL explicitly bounded to ten
  candidates from five paintings;
- persisted 35 compute/scalability rows: 27 observed execution summaries and
  eight transparent 300-painting projection rows;
- kept observed and projected records separate, retained seven applicable
  projection rows, and marked the SDXL current-design projection
  `not_applicable_no_full_design_basis`;
- retained all eleven Notebook 21 quality anchors as separate descriptive
  evidence in two population-matched views, without constructing a combined
  quality/compute score or including runtime in the quality vote;
- generated two canonical figures and four thirteen-section text-native method
  cards with no image dependency;
- passed all 165 validation checks and all 13 roadmap traceability requirements
  with zero blocking or warning failures;
- registered six non-self-referential artifacts and exactly eleven physical
  files under `outputs/30_model_cards_compute_and_scalability/`.

Notebook 30 is now the canonical downstream source for method-card disclosures,
observed model compute, notebook-owned model output storage, and transparent
300-painting scalability projections. Notebook 31 must preserve the distinction
between the complete three-model population and the bounded SDXL subset, between
observed and projected evidence, and between separate quality anchors and runtime.
The projections are linear sensitivity estimates rather than executed experiments
or confidence intervals. Recorded runtime and memory describe one workstation,
quality-anchor wins are descriptive rather than a universal score, and the cards
do not establish historical authenticity, conservation suitability, or approval
for physical treatment.

Notebook 31 is complete and passed its completion gate. It consumed validated
Notebook 09--30 artifacts and produced four standalone, self-contained HTML
reports plus a four-row report index. All four reports preserve the approved
executive summary plus fourteen-section structure. Together they contain 63
embedded report images and 298 embedded visual tiles: 16 images and 76 tiles for
Telea, 16 and 76 for LaMa, 19 and 90 for Stable Diffusion, and 12 and 56 for
SDXL. No report contains an external image dependency or planning-mock residue.

The completed report layer passed all 324 validation checks, all 13 roadmap
responsibilities, and all 39 mock-to-final traceability roles with zero blocking
or warning failures. Six non-self-referential artifacts and exactly eight
physical files were registered under `outputs/31_model_report_generation/`.
The reports are presentation and synthesis artifacts only: they select examples,
format validated values, create presentation-only plots, and embed web-sized
visuals, but they do not create new metrics, statistical tests, rankings,
exclusions, composite scores, or scientific evidence.

Notebook 31 is now the canonical downstream source for model-report discovery
and provenance through `data/report_index.csv`. Complete machine-readable
evidence remains in the producing upstream tables, including Notebook 29's
1,785-row explanation catalog; embedded report examples are auditable
illustrations rather than the full evidence population or independent
observations. Consumers must retain the method-specific applicability rules:
Telea and LaMa are deterministic and have no repeated-seed uncertainty, Stable
Diffusion reports canonical and damage-size seed variability plus the controlled
scratch-prompt ablation, and SDXL remains a ten-case, five-painting partial
evaluation with insufficient seed coverage for uncertainty. The reports do not
establish historical authenticity, conservation approval, calibrated confidence,
or universal model superiority.

Notebook 32 is complete and passed its completion gate. It consumed validated
Notebook 01 and Notebook 09--31 artifacts and produced 81 self-contained HTML
reports: 30 deterministically selected deep case reports, one report for each of
all 50 paintings, and one collection index. It also persisted 30 selected-case
diagnostic grids. The 50 painting reports retain all 410 evaluated cases and all
1,785 approved candidates in their evidence tables: each of the 45 standard
paintings has five canonical cases, while p001, p018, p026, p039, and p043 each
have 37 canonical and extension cases. The selected deep case reports remain
auditable illustrations rather than the complete case population.

The completed report package contains 632 embedded report images and 2,146
embedded visual tiles with zero external image dependencies. All 80 case and
painting reports are individually portable; the collection index provides 80
validated package-relative links for navigation. The run registered eight
artifacts and exactly 117 physical output files, passed all 1,806 validation
checks, all 12 roadmap responsibilities, and all 67 mock-to-final traceability
roles with zero blocking or warning failures. All eight persisted artifact
checksums and all 80 individual report checksums were independently reverified.

The authoritative report-candidate population remains Notebook 29's 1,785
approved candidates: 410 Telea, 410 LaMa, 955 Stable Diffusion, and ten SDXL
candidates. The 480 completed Notebook 11 context-prompt candidates from prompt
variants p01--p04 remain outside the report population because they do not have
the complete Notebook 27/29 failure, flag, and explanation contract. This is an
explicit evidence-scope exclusion, not missing execution or complete downstream
evaluation.

Notebook 32 is now the canonical downstream source for selected case-report and
complete painting-report discovery through `data/case_report_index.csv` and
`data/painting_report_index.csv`; `reports/index.html` is the package entry point.
The report layer groups, sorts, formats, selects declared illustrations, builds
presentation-only plots, and embeds web-sized visuals, but creates no new
metrics, statistical tests, exclusions, rankings, composite scores, or scientific
evidence. Candidate rows remain nested within cases and paintings; only 18
paintings have documented style or period, and the five-painting extension
cohorts remain descriptive. Telea and LaMa are deterministic, Stable Diffusion
uncertainty is limited to the canonical and damage-size repeated-seed
populations, and SDXL remains a ten-case partial evaluation with insufficient
seed coverage. Computational flags and review actions are not expert annotations,
historical-authenticity evidence, or physical conservation advice.

Notebook 33 is complete and passed its completion gate. It consumed the frozen
methodology and validated Notebook 21--32 synthesis artifacts without running
restoration inference, recomputing scientific metrics, creating new statistical
tests, or constructing a universal combined score. It persisted 293 canonical
thesis-table rows across 15 tables, 15 LaTeX-ready table records, 106 evidence-
catalog records, 18 thesis figures, six publication figures, one standalone HTML
report, and one explicit limitations report.

The final HTML preserves all 19 approved sections, 48 evidence-backed claim
positions, and 18 explicit limitations. It embeds 68 images representing 281
analytical or restoration tiles, contains no external image dependency, and is
portable as a single 13.46 MiB file. Twelve selected case grids support detailed
visual discussion, while complete case and painting evidence remains available
through Notebook 32 and complete machine-readable candidate evidence remains in
the canonical producing notebooks.

The completed synthesis passed all 535 stage-scoped validation checks, all 21
roadmap responsibilities, and all 125 approved mock-to-final traceability roles
with zero blocking or warning failures. Eight artifact groups and exactly 32
physical files were registered under `outputs/33_final_evaluation_report/`; all
artifact checksums, the artifact-manifest checksum, and the manifest-declared
physical-file set were independently reverified.

Notebook 33 is now the canonical final-report source for Notebook 34. Downstream
consumers must preserve its applicability boundaries: the complete comparison is
limited to Telea, LaMa, and Stable Diffusion; SDXL remains a ten-case, five-
painting feasibility population; uncertainty covers supported Stable Diffusion
repeated-seed populations only; the five-painting extensions do not estimate
independent category or style effects; and scaling projections are not executed
results or confidence intervals. Computational flags, feature similarity,
retrieval results, and visual plausibility do not establish expert ground truth,
historical authenticity, conservation approval, or a physical treatment
recommendation.

Notebook 34 is complete and passed its completion gate. It consumed 41 validated
input tables and all 33 completed upstream run manifests without running
restoration inference, recomputing scientific metrics, creating new statistical
tests, or constructing a universal combined score. It persisted nine normalized
dashboard tables, five indexes, one dashboard summary, one dashboard-asset
manifest, one validation table, one artifact manifest, and one run manifest under
`outputs/34_final_streamlit_dashboard_assets/`.

The completed package preserves the approved eight-page structure: Overview,
Study Design, Metric Framework, Model Performance, Robustness & Uncertainty,
Trustworthiness & XAI, Case Explorer, and Reports & Reproducibility. Its indexes
retain all 1,785 approved candidates, all 50 paintings, 23,964 visual records, and
104 reports. Representative cases control initial presentation only; they do not
limit filtered evidence access. Model, case, painting, method, and final reports
remain discoverable through validated repository-relative paths.

The normalized table layer contains 8 headline findings, 35 study-design rows,
178 metric-framework rows, 1,241 performance rows, 18,951 sensitivity and
statistical rows, 1,723 uncertainty rows, 284 trustworthiness rows, 35 compute
rows, and four research-question rows. The 18,951-row analysis table explicitly
includes all Notebook 26 grouped/statistical results, both measures from every
metric-correlation record, and all recorded ranking-stability measures. This
closes the preparation-stage packaging gap without modifying frozen Notebooks
01--33 or recomputing their evidence.

Notebook 34 passed all 410 validation checks and all 25 roadmap responsibilities
with zero blocking or warning failures. Fifteen dashboard assets and 17 universal
artifact records were registered across exactly 19 physical files; their
checksums and the manifest-declared output set were independently reverified.
Notebook 34 is now the canonical dashboard-data source for Notebook 35.
Downstream consumers must preserve nested observation units, bounded SDXL
applicability, separate uncertainty/robustness/prompt-sensitivity terminology,
and the limits of computational flags and retrieval evidence. The approved
human-editorial visual language affects presentation only and cannot alter
scientific evidence.

Notebook 28 is now the canonical source for downstream evaluation-policy
sensitivity and metric/region ablation evidence. Consumers must distinguish the
stable model-level winner from policy-sensitive case priorities and flags, retain
metric-family and region disagreement, and never interpret lower flag counts
caused by removed evidence as improved restoration quality. Its ranks are
transparent ordinal diagnostics, thresholds are operational rather than
calibrated probabilities, and five-painting subgroup findings are descriptive.
The analysis does not establish independent style effects, universal model
superiority, historical authenticity, conservation approval, or a full SDXL
comparison.

The historical Notebook 35 run is complete against the fixed Notebook 34
dashboard package and the versioned contract in
`config/evaluation/dashboard_validation.yaml`. The legacy
Streamlit application was replaced in full by an eight-page, presentation-only
consumer of the Notebook 34 root. `src/restoration_eval/dashboard_application.py`
owns shared read-only loading, repository-safe indexed-path resolution, package
checks, and static application checks. Neither component scans arbitrary output
folders, runs restoration inference, nor computes scientific metrics.

The completed notebook loaded all nine dashboard tables, four CSV indexes, and
the filter index at their approved counts. It validated all 1,785 candidates,
50 paintings, 23,964 visual records, 104 reports, 10 bounded SDXL candidates,
130 canonical uncertainty groups, and 35 damage-size uncertainty groups. All
eight pages passed Streamlit's in-process application test with zero exceptions
or visible application errors. The complete 582-check ledger contains zero
blocking failures, seven dependency-version warnings, and one informational
not-deployed result at execution time. All 14 roadmap responsibilities passed,
and the exact four canonical Notebook 35 outputs and two registered artifact checksums were
independently reverified. The external UI reference images remain read-only
files outside the repository.

The final validation run is
`run_e04d0dfa163b4a15966c5420b01d74c7`. The tested Python 3.12 environment
uses Streamlit 1.59.0 while the repository requirements target Streamlit
1.56.0; Pillow, Plotly, and PyArrow also differ from their declared pins. The
application passed the full smoke test despite those differences, so that run
supports conditional local demonstration readiness, not exact environment
reproduction or completed public deployment. No public URL was recorded in the
run. This historical result is preserved; see Section 6.1 for later delivery.

Manual browser review is complete. All eight pages were approved after the
final interface pass. The accepted application includes an explicit
metric-region image selector, condition- and model-filtered restoration
comparisons, focused uncertainty views, proposal-aligned research-question
traceability, and balanced overview explanations. These are presentation and
inspection improvements over the fixed Notebook 34 evidence package; they do
not alter or recompute the scientific results.

## 6. Final-package evidence gate

| Notebook | Supported evidence contract | Required scope discipline |
|---|---|---|
| 36 Reproducibility package | 35 completed manifests; N30 model cards; N31 model reports; N32 report indexes; N33 report, figures, and tables; N34 indexes; N35 deployment readiness | package only validated evidence; distinguish copied material from indexed omissions; do not recompute or strengthen scientific claims |

### Notebook 36 approved contract and completion

Notebook 36 is a delivery and traceability consumer. It creates no new
scientific evidence. The approved population is fixed at 50 paintings, 525
registered cases, 410 restoration cases, 1,785 approved candidates, 11 quality
anchors, 165 uncertainty groups, 23,964 visual records, 104 report records, and
ten bounded SDXL feasibility cases.

The curated package copies the final self-contained HTML report, four
self-contained model reports, 24 final figures, four model cards, eight compact
tables/indexes, 35 run manifests, evaluation configurations, environment files,
and dashboard delivery documentation. It records canonical paths and checksums
without duplicating the 30 case reports, 50 painting reports, selected-case
grids, complete dashboard visual package, restoration/map collections, model
weights, or caches.

The package must answer the three proposal research questions only within the
validated controlled benchmark. It must preserve these boundaries: no universal
combined score, no calibrated-confidence claim, no expert-ground-truth claim,
no full-benchmark SDXL claim, and no inference from controlled synthetic damage
to conservation approval or historical correctness.

The preparation audit also found that the global project-path registry ended at
Notebook 33. Notebook 34 contributes 17 canonical dashboard records and
Notebook 35 contributes two completion records with non-blocking warning status.
Those records were normalized and registered before Notebook 36 Batch 1,
bringing the preflight registry to 218 artifacts. Overlapping artifact keys
were namespaced without rewriting the frozen upstream manifests.

Notebook 36 is complete under run `run_4e221aa9405d4d5cbeb7ae120dfad71a`.
The saved opening metadata reads Finished / Finished / Yes, all 16 roadmap
responsibilities passed, and the 182-row validation ledger contains 181 passes,
zero blocking failures, and one inherited Notebook 35 dependency-alignment
warning. That record summarizes the upstream warning state; it is not a new
scientific failure or a claim that Notebook 35 had only one individual warning.

The final output root contains exactly 125 files. The 114-file review package
contains 106 byte-preserved copies and eight Notebook 36-generated files,
totalling 29,021,450 bytes (27.677 MiB). Its 120-row artifact index distinguishes
those 114 files from six intentionally indexed but unbundled collections.
Twelve canonical artifact records are registered, bringing the global registry
to 230 records, with the inherited warning status preserved.

Independent final inspection verified the saved code syntax, absence of saved
cell errors, artifact and run-output checksums, every packaged file checksum,
package-tree checksum, all 22 local Markdown links, and all 24 PNG files.
The notebook also validated all five self-contained HTML reports. The supervisor
summary and meeting agenda now refer to the final validation records rather
than incorrectly describing package assembly as still in progress.

The bundle retains 25 execution-time evaluation-configuration snapshots and
indexes 13 additional source configurations. These historical snapshots, the
preflight 218-record registry count, and the recorded pre-commit Git state must
not be rewritten merely because the governing audit files and global registry
are updated after completion. Their recorded checksums describe the inputs
actually consumed by the run, not the later administrative completion state.

The package is ready for supervisor and thesis review. It is not a complete
executable repository clone; omitted image collections, model weights, and
the full dashboard assets still require the repository. Its dashboard snapshot
records conditional local demonstration readiness, not the subsequent public
deployment. No upstream notebook, scientific result, or approved application
was changed during this final packaging audit.

### 6.1 Post-notebook application delivery — recorded 2026-09-04

The user approved the completed eight-page dashboard, its later numerical
evidence views, and the public deployment at
[https://fhtw-painting-restoration.streamlit.app/](https://fhtw-painting-restoration.streamlit.app/).
The root README and application's Reports & Reproducibility page link to this
deployment. These delivery facts do not change any experimental population.

- **Read-only numerical views:** Case Explorer displays original source values,
  applicability, units, and candidate/seed/prompt identity from fixed,
  checksum-verified producer tables. Model Performance exposes the existing
  N34 chart estimates and intervals. The input, display, and verification
  contract is `docs/dashboard_numeric_metrics.md`; its implementation and focused
  tests are `src/restoration_eval/dashboard_metrics.py` and
  `tests/test_dashboard_metrics.py`. N34 remains the candidate allow-list.
- **Availability workflow:** commit `4f285808` adds
  `.github/workflows/streamlit-availability.yml`,
  `tools/check_streamlit_availability.py`, and
  `tests/test_streamlit_availability.py`. It is configured for a public browser
  visit every four hours and manual dispatch. The original minute-17 schedule
  was changed to minute 43 in commit `e111bbf3` as a scheduling diagnostic; the
  workflow file on the default branch is the timing authority. The previously
  verified [manual run 33819253480](https://github.com/Rahul-DS25M008/painting_restoration_eval/actions/runs/33819253480)
  passed both the browser fixtures and live content/image readiness check. This
  is a dated availability observation, not an uptime guarantee or proof that
  hibernation can never recur. No additional live service test was performed for
  this documentation maintenance pass.
- **Version boundary:** N35 validated the application revision recorded by its
  manifest. N36 preserved its own checksummed source and environment snapshots.
  Neither is retroactively claimed to have tested or packaged the later UI,
  public deployment, or availability workflow.
- **Environment boundary:** the current dashboard setup uses Python 3.12 and
  root `requirements.txt`; all 36 saved notebook manifests record Python 3.12.6.
  Exact experimental reproduction still requires the producer-specific recorded
  environments. Deployment success does not clear the historical N35 dependency
  warnings inherited by N36.

The current deployment record is separate from automated scientific coverage
and is now mirrored in YAML under `post_completion_maintenance`. The prior
manual run verifies browser-check execution, not automatic scheduling; scheduled
execution was still unverified at this maintenance review. Historical N35/N36
flags and their checksummed outputs remain unchanged and must not be rewritten
to imply that the original runs deployed the app.

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

No notebook remains unimplemented in the approved 36-stage pipeline. Before
Batch 1 of any explicitly approved extension or reopening:

1. Resolve every responsibility to an entry in
   `config/evaluation/evidence_coverage.yaml`.
2. Confirm exact source paths, row/file counts, population filters, and ownership.
3. Confirm the independent statistical unit and repeated/nested observations.
4. Remove any result or report claim that lacks validated evidence.
5. Add planned outputs and checks to the consumer contract.

At completion of that approved notebook work:

1. Update the YAML with actual counts and the new manifest path.
2. Update this document's completion ledger and affected dependency contracts.
3. Refresh `outputs/inventory/`.
4. The user commits the notebook, owned outputs, governing-file updates, and
   inventory together unless an approved staged commit is required.

For documentation or application-only maintenance, update only the approved
files and use dated addenda to distinguish current delivery from original run
facts. Do not rerun notebooks, refresh checksummed packages, clear historical
warnings, or regenerate the inventory implicitly. Scientific-coverage changes
require coordinated human-ledger and YAML updates; ordinary wording corrections
do not manufacture a new scientific validation event.
