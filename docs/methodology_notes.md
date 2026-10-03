# Methodology Guide

**Status:** current methodology for the completed Controlled-300 pipeline, reviewed 2026-10-02\
**Experimental scope:** `controlled_300` completed through Notebook 36 with disclosed deployment/provenance limitations; `controlled_50` retained as historical evidence\
**Pipeline:** completed N01–N36 including N12A; separate D01 and supplemental D02; pilot baseline remains frozen\
**Public interface:** [Controlled-300 Streamlit dashboard](https://fhtw-painting-restoration-main.streamlit.app/)

This guide explains the main scientific and engineering decisions in the
completed painting-restoration evaluation framework. It is a navigation and
interpretation document, not a replacement for producer manifests, validation
tables, configurations, reports, or the thesis methodology chapter.

The detailed prose below describes Controlled-300. The completed Controlled-50
pilot is historical evidence, recoverable at `pilot-50-complete`; it does not
define the current populations. The
[post-freeze reporting clarifications](evidence_dependency_audit.md#reporting-clarifications--2026-10-02)
explain interpretation corrections without changing executed outputs.
Notebook 31 supplies the validated five-report
Controlled-300 model-report layer. Notebook 32 run
`run_0d4ae193602944dda511bf54199105b1` now supplies the validated 300-painting,
30-deep-case and collection reporting layer. Notebook 33 run
`run_aef04267c2e44495a4e7a6249426bd4d` supplies the validated final synthesis;
Notebook 34 run `run_1e831de6e27f9ead0147bb30` supplies the validated
Controlled-300 `dashboard_package.v2` release. The new interface is now deployed
from `main`; N35 records owner acceptance and successful availability checks,
with 519 passes and 14 retained warning/nonpass records. Unmeasured performance,
platform and browser qualifications are not inferred from acceptance. N36 run
`run_e3133aca48134968896bcd1b97af72c4` completed the final Controlled-300 package:
859 checks passed, 16 warning nonpasses remain and there are zero blockers.
Its 134-file delivery preserves these distinctions, including both provenance
exceptions, without rerunning scientific experiments.

- The detailed notebook sequence is in
  [`final_notebook_roadmap.md`](final_notebook_roadmap.md).
- Validated populations and evidence boundaries are in
  [`evidence_dependency_audit.md`](evidence_dependency_audit.md) and
  [`evidence_coverage.yaml`](../config/evaluation/evidence_coverage.yaml).
- Implementation and artifact rules are in
  [`refactoring_implementation_guidelines.md`](refactoring_implementation_guidelines.md).
- Literature support is maintained separately in
  [`literature_reference_log.md`](literature_reference_log.md).
- Model provenance and selection are maintained separately in
  [`model_audit_notes.md`](model_audit_notes.md).

## 1. Research framing

The framework evaluates restoration candidates under controlled synthetic
damage where a clean reference is available. It addresses three proposal
questions:

1. What additional evidence does a region-aware, multi-metric evaluation
   framework provide beyond traditional image-similarity metrics when
   evaluating AI-assisted painting restoration?
2. How do selected inpainting methods differ in restoration quality across
   controlled artificial damage conditions, and how consistent are these
   differences across the evaluated paintings?
3. How can repeated-candidate disagreement be used to characterize the
   stability of stochastic painting restorations, and how does it relate to
   other restoration-quality diagnostics?

The implemented study extends those questions with region selection, colour,
texture, seams, spatial diagnostics, robustness, prompt sensitivity, failure
flags, explainability, compute and delivery. These additions remain evidence
components, not a universal restoration or trustworthiness score.

The central interpretation boundary is:

> Visual plausibility is not equivalent to restoration trustworthiness,
> historical correctness, authenticity, artist intent, or conservation approval.

## 2. Dataset and preprocessing

The controlled dataset contains 300 paintings, with 60 in each of five broad
visual categories:

- abstraction/surrealism;
- architecture/structured;
- high-texture/brushwork;
- landscape/natural;
- portrait/figure.

These are study strata, not independently validated art-historical styles.
Style/period is documented for 268 works and missing for 32. Metadata coverage
is field-specific; analyses must not convert the balanced visual categories
into general art-historical style effects.

Balancing five operational categories at 60 paintings each does not establish
cultural, chronological, geographic or conservation-condition representativeness.
The source institutions are concentrated: Cleveland Museum of Art contributes
109 paintings, the Metropolitan Museum of Art 55 and Statens Museum for Kunst
44, together 208/300 (69.3%). These counts come from N01's `artworks.csv`.
Artificial damage supports controlled reference-fidelity evaluation, not
generalization to real conservation conditions. The 32 missing style/period
entries further limit historical subgroup interpretation.

Notebook 02 standardizes each accepted image as a 768 × 768 RGB PNG. It preserves
aspect ratio, pads rather than distorts or center-crops, and records the exact
painting-content bounds. Padding is excluded wherever the declared region
requires painting content. Consumers use the recorded geometry rather than
estimating content from pixel colour.

## 3. Experimental case registry

Notebook 08 normalizes four experiment families into a 3,425-row case registry:

| Experiment | Cases | Design and statistical boundary |
|---|---:|---|
| Canonical missing-region damage | 1,500 | 300 paintings × five masks, including 300 identity controls |
| Damage-size sensitivity | 245 | 35 paintings × seven nested area levels; levels repeat within paintings |
| Mask robustness | 525 | 35 paintings × three fixed family/area groups × five mask variants |
| Synthetic degradation | 1,155 | 35 paintings × 33 procedural conditions; 350 cases have approved masked-removal semantics |

Canonical masks are `zero_control`, `scratch_thin`, `loss_small`, `loss_large`
and `mixed_damage`. Missing pixels are displayed as white in damaged inputs;
this is a controlled encoding, not a claim about the appearance of real damage.
Binary masks use foreground values of 255, with active pixels selected at 128.
Zero controls preserve the clean image exactly.

The damage-size experiment uses nested target levels of 2%, 4%, 6%, 8%, 10%,
15% and 20%. The robustness experiment changes mask placement or geometry while
holding its declared family/area condition fixed. Synthetic degradations model
controlled effects, not physical conservation processes or verified aging.

Model eligibility is explicit for every case–model pair. Binary missing-region
cases are inpainting tasks. Only `water_stain`, `dirt_dust`,
`partial_transparency` and `water_stain_dirt` synthetic cases are eligible as
supplementary masked-removal diagnostics. Blur, tonal change, colour change and
pigment transport are not silently reframed as missing-content restoration.
This yields 2,620 eligible restoration cases per full-coverage method: 1,500
canonical, 245 damage-size, 525 robustness and 350 synthetic-degradation cases.
Of these, 2,320 have nonzero damage and 300 are identity controls. Eligible-case
coverage and the number of applicable paired measurements are distinct counts.

## 4. Restoration methods and candidate populations

| Method | Role | Validated scope |
|---|---|---:|
| OpenCV Telea | Deterministic classical baseline; radius 3 | 2,620 cases |
| LaMa through IOPaint | Deterministic pretrained learned baseline | 2,620 cases |
| HINT Places2 | Deterministic learned transformer, selected in separate D01 | 2,620 cases in N12A |
| Stable Diffusion 1.5 Inpainting | Stochastic, prompt-conditioned baseline | 2,620 primary candidates; 8,520 N11 candidates in total |
| SDXL Inpainting | Bounded feasibility/partial-evaluation branch | 24 completed of 35 scheduled cases; 19 paintings represented |

The comparison evaluates fixed restoration pipelines, not architecture in
isolation. Telea, LaMa and HINT operate on the 768 × 768 canvas; Stable Diffusion
uses 512 × 512 inference and returns to 768 × 768 for exact-mask compositing.
Resolution, resizing, mask processing, prompts and generation settings can all
contribute to observed differences. Their individual effects were not isolated
by a matched-resolution experiment. Conclusions concern the recorded pipelines,
not every implementation of the corresponding model families.

Zero controls are identity no-ops. The nonzero restoration branches use exact
mask compositing so active pixels may change while pixels outside the approved
mask remain unchanged. Binary and synthetic masks retain their distinct active
thresholds.

Stable Diffusion uses a fixed generic primary prompt and seed 2026 for the
2,620-case comparison. Its additional N11 candidates support contextual prompt
tests, four-seed uncertainty and a paired scratch-aware prompt experiment. The
formal scratch experiment contains 2,400 outcomes: 300 paintings × four seeds ×
two prompt arms. Seeds are repeated observations within paintings, not 1,200
independent paintings. Prompt sensitivity is not seed uncertainty.

Notebook 22 owns another 735 Stable Diffusion candidates—seeds 2027–2029 for
the 245 damage-size cases. They extend uncertainty coverage without altering N11.
The four full methods contribute 10,480 matched primary candidates. The
13,879-candidate reporting/dashboard population is a validated downstream
selection, distinct from every candidate ever generated. “Approved” means
eligible for the declared analysis, not approved restoration quality.

SDXL scheduled 35 cases across 30 paintings; 24 cases across 19 paintings
completed and passed technical validation, one timed out and ten were not started
after the budget/timeout guard. One seed per completed case cannot support
seed-uncertainty estimates. Runtime or hardware limitations are not image-quality
failures. D01's 12 paired HINT/MAT cases and the supplemental D02 portrait audit
remain separate studies, not additions to the main comparison population.

## 5. Canonical spatial regions

`src/restoration_eval/regions.py` is the only authoritative region
implementation. Notebook 08 registers eleven regions:

- `full_image` and `content_region`;
- `masked_region` and `mask_bbox_crop`;
- `inner_boundary_band`, `outer_boundary_band` and symmetric `boundary_ring`;
- `outside_mask_content` and `outside_boundary_ring`;
- `degradation_support`;
- `patch_window`.

The mask-bounding-box crop uses local spatial context; the configured margin is
eight pixels. Boundary bands use the configured three-pixel width. Full-image
results can be dominated by unchanged content, masked pixels can lose spatial
structure, and boundary/outside regions answer different questions. Therefore,
region choice is part of each metric's definition, not a display preference.

SSIM, LPIPS, CLIP and DINOv2 operate on contiguous image-like regions such as
content or mask-bounding-box crops. They are not forced onto sparse masked-pixel
sets. Colour, pixel-error, spatial-map and seam measures use irregular regions
where their mathematical contract permits it.

## 6. Evidence families

No individual measure is treated as restoration ground truth. The framework
retains the following evidence separately:

- **Classical fidelity:** MSE, MAE, PSNR and SSIM relative to the clean image.
- **Perceptual similarity:** LPIPS on contiguous regions.
- **Feature similarity:** global and local CLIP and DINOv2 relationships.
- **Spatial diagnostics:** damaged/restored error, signed improvement, worsened
  pixels and outside-mask change, with inspectable maps.
- **Local consistency:** texture descriptors and maps, colour differences,
  chroma-aware evidence, boundary gradients, orientations and seam diagnostics.
- **Semantic/structural proxies:** local feature agreement, layout, affinity and
  outside-context change; these are not object, face, anatomy or iconography
  detectors.
- **Empirical diffusion uncertainty:** image-space and pairwise disagreement
  across repeated candidates with fixed case, prompt and configuration.
- **Operational evidence:** runtime, hardware, failures, retries and scalability
  projections, clearly separated from observed execution.

Texture and directional-gradient measures are brushstroke proxies only. CLIP and
DINOv2 are general pretrained representations, not conservation-specific human
ratings. CIEDE2000 and related colour evidence quantify controlled digital colour
differences; they do not establish pigment chemistry or physical treatment
suitability.

## 7. Eleven comparison anchors

The main four-method comparison retains eleven metric–region anchors:

| Evidence family | Anchor |
|---|---|
| Classical | Masked-region MAE |
| Structural | Mask-bounding-box SSIM |
| Perceptual | Mask-bounding-box LPIPS |
| Feature | Mask-bounding-box CLIP cosine similarity |
| Feature | Mask-bounding-box DINOv2 cosine similarity |
| Spatial | Masked-region mean restored error |
| Texture | Mask-bounding-box 95th-percentile local texture error |
| Colour | Masked-region mean CIEDE2000 difference |
| Seam | Boundary-ring gradient mismatch |
| Semantic/local feature | Mask-bounding-box mean local DINOv2 similarity |
| Structural affinity | Content-region reference-affinity map correlation |

Metric direction is retained for every anchor. Anchor wins count how many
saved anchors a model ranks first on; mean anchor rank describes its average
position across those same anchors. These are not counts of independent evidence
or a combined quality score. Masked MAE and masked mean restored spatial error
are the same scalar quantity apart from numerical precision: the spatial maps
add localization, but their regional mean is not independent confirmation.
Other anchors may also correlate. Individual metric values and the paired
analyses support interpretation of the retained 10/11 LaMa result.
Removing the duplicated MAE/spatial-error scalar gives nine LaMa wins among
ten distinct scalar quantities; Telea leads crop SSIM. Distinct does not mean
statistically independent.

Runtime and uncertainty are excluded from quality voting. The core coverage is
2,620 cases and four methods; a separate matched five-method view covers the
24 completed SDXL cases. The legacy identifiers `core_three_model` and
`sdxl_four_model_subset` remain unchanged for schema continuity.

For the saved N21 overall anchor rows, ten anchors have 2,320 paired nonzero
cases. Content-region structural-affinity correlation has 2,620 paired cases,
including controls. N33's T04/T05 blanket nonzero scope and coverage-based
denominator therefore require the
[documented correction](evidence_dependency_audit.md#reporting-clarifications--2026-10-02).
Use N21's `paired_case_count` for each measurement, not `population_case_count`.

## 8. Repeated-candidate stability and spatial explanation

Repeated-candidate stability analysis requires exactly seeds 2026–2029 within
a fixed case, prompt and configuration:

- N18: 780 canonical prompt-specific groups—480 generic and 300 scratch-aware—
  containing 3,120 candidates and 4,680 unordered seed pairs;
- N22: 245 damage-size groups, using 245 N11 seed-2026 candidates and 735 new
  candidates, with 1,470 unordered seed pairs;
- final coverage: 1,025 complete groups, each with four seeds and six pairs.

The transparent disagreement components include per-pixel RGB standard deviation, pairwise
RGB MAE/RMSE, LPIPS distance and CLIP/DINOv2 cosine distance. N18 also joins
reference, perceptual, feature, texture, colour and seam evidence into a
780-row association-ready table. It does not fit confidence calibration, compute
a combined uncertainty index, or use later computational flags as ground truth.

N19 stores raw numeric maps and visual overlays for N18's 780 groups; N22 owns
the 245 damage-size groups' maps. High variability identifies less stable areas where
repeated candidates disagree and closer inspection may be useful. Low
variability shows consistency, not correctness. Associations with other
restoration-quality diagnostics describe complementary evidence rather than a
validated error detector. Telea, LaMa and HINT are deterministic, so their later
analyses use robustness or sensitivity terminology instead of artificial
uncertainty values. SDXL has insufficient seed coverage.

## 9. Analysis and statistical discipline

Comparisons are case-paired whenever models share the same case. Repeated masks,
seeds, prompts and cases nested within paintings are not treated as independent
paintings. Focused extension experiments support within-study trajectories
and sensitivity descriptions, not independent category effects.

N21's overall summaries average applicable paired case-level rows. They are
case-weighted descriptions of the evaluated benchmark mixture, not equal-weight
painting averages: paintings included in extension experiments contribute more
cases. N26's painting-level inferential analyses are separate and must not be
presented as the same estimator. No new equal-painting sensitivity analysis was
performed for this documentation correction.

N26's eleven Friedman tests and 66 paired-model contrasts use only
`canonical_missing_region`: 1,200 nonzero cases (300 paintings, each with
`loss_large`, `loss_small`, `mixed_damage` and `scratch_thin`). For each anchor
and method, the median of the four direction-adjusted case values is computed
within each painting. These form 300 equally weighted painting blocks, with
one observation per method per block. The four methods are Telea, LaMa, HINT
and primary generic-prompt Stable Diffusion (seed 2026). Identity controls,
extension cases, other prompts, repeated seeds and SDXL are excluded.

The 44 quality/runtime associations use a different population: 2,320 nonzero
cases across canonical damage (1,200), damage-size sensitivity (245), mask
robustness (525) and eligible synthetic degradation (350). Quality and runtime
are separately summarized by their within-painting/model medians, then correlated
across 300 equally weighted paintings per method. Paintings outside the extension
subset have fewer constituent cases. T10 summarizes these as eleven rows, each
containing four model-specific associations. The original N26 export mislabeled
the canonical tests as all-branch results; see the
[E02 correction](errata/2026-10-03/README.md#e02--n26-and-t10-statistical-populations).

Downstream analyses preserve metric disagreement and include, where their
contracts apply:

- damage-size trajectories using target and realized damaged fraction;
- input-mask robustness across matched variants;
- synthetic-degradation behavior on eligible effect families;
- grouped effects, paired contrasts, effect sizes, uncertainty intervals and
  multiple-testing correction;
- leave-one-painting-out or other declared stability checks;
- metric/region/threshold ablation;
- prompt-arm comparisons without best-seed selection.

Descriptive results remain descriptive when sample size, nesting, corrected
tests or metric disagreement do not support stronger inference. No universal
damage threshold, model ordering or combined score is retained.

## 10. Trustworthiness flags and explainability

Notebook 27 assigns rule-derived flags and failure categories from available
computational evidence. These rules prioritize review; they are not expert
annotations, objective failure truth, calibrated risk or conservation decisions.
Consequently, the proportion of candidates with review flags is not an
objective model-failure rate. Counts must retain their declared candidate
population, available evidence and rule applicability.

Notebook 29 provides rule traces, counterfactual “what would change the flag”
explanations, and CLIP/DINOv2 neighbor retrieval. Retrieval supplies visual or
semantic context, not restoration correctness or historical proof. Complete
case catalogs retain source evidence and paths even though reports display a
smaller deterministic selection.

## 11. Reporting, dashboard and reproducibility

Important HTML reports are self-contained: report-relevant web-sized images and
figures are embedded, while full-resolution collections remain referenced by
validated paths and checksums. Report examples follow explicit, auditable
selection rules rather than informal cherry-picking. The final reporting layer
includes five model reports, 30 selected case reports, all 300 painting reports,
and a thesis-level evaluation report.

Notebook 34 prepares normalized dashboard tables and indexes. The approved
eight-page application is a read-only presentation and inspection interface. Its
later numerical views use the N34 candidate allow-list and checksum-verified
producer metrics as documented in
[`dashboard_numeric_metrics.md`](dashboard_numeric_metrics.md). The app does not
run restoration inference or recompute scientific metrics.

Notebook 36 completed a checksum-verified supervisor and reproducibility package:
123 package files (35.04 MiB), 115 byte-preserved copies, eight generated package
files, 38 upstream manifests and a 693-row delivery/omission index. The original
nine-step plan was delivered in eight batches at the owner's request.
It copies a bounded review set and indexes larger collections; it is not a full
repository clone. Historical notebook manifests and package snapshots describe
the versions actually executed or packaged and are not rewritten after later
documentation or deployment changes.

All 36 saved run manifests record Python 3.12.6. Dashboard installation uses the
root `requirements.txt`; the experimental recipe is separate and is not an exact
lock of every producer environment. Exact reproduction requires the target
producer's package versions, configuration and helper checksums, seeds, model
revisions, hardware and CUDA information. See the
[reproducibility appendix](../outputs/36_supervisor_publication_reproducibility_package/reports/reproducibility_appendix.md).

These records support traceability and reproduction; independent end-to-end
reproduction has not been demonstrated. The N29 historical-manifest and N35
notebook-source discrepancies remain unresolved, as do the disclosed unmeasured
deployment qualifications. Documentation updates neither change those hashes
nor convert accepted qualifications into passed checks.

## 12. What the methodology supports

Within this controlled benchmark, the methodology supports:

- comparing eligible methods on identical cases across complementary measures;
- locating where restoration changes, errors, seams and seed variability occur;
- testing sensitivity to damage size, mask geometry, prompts, regions and
  decision thresholds;
- exposing disagreement that a single similarity number would hide;
- tracing displayed claims and examples to versioned evidence;
- organizing human inspection through reports, visual explanations and the
  dashboard.

It does not support:

- historical reconstruction truth, authentication or artist-intent inference;
- automatic conservation approval or replacement of specialist judgement;
- generalization from synthetic effects to real physical deterioration;
- independent art-style conclusions from five broad visual categories;
- calibrated confidence from seed variability;
- treating retrieval similarity or computational flags as expert ground truth;
- a full-population SDXL conclusion;
- reporting projected scaling as executed evidence.

## 13. Canonical starting points

- [Evaluation contract](../outputs/08_experiment_contracts_and_region_policy/reports/evaluation_contract.md)
- [Multi-model comparison](../outputs/21_multi_model_comparison/reports/multi_model_comparison.html)
- [Grouped statistical analysis](../outputs/26_grouped_and_statistical_analysis/reports/statistical_analysis.html)
- [Metric and region ablation](../outputs/28_metric_and_region_policy_ablation/reports/ablation_study.html)
- [Final evaluation report](../outputs/33_final_evaluation_report/reports/final_evaluation.html)
- [Review-package README](../outputs/36_supervisor_publication_reproducibility_package/package/README.md)

These sources are the appropriate next level of detail. The methodology guide
must not be used to overwrite their counts, applicability states, warnings or
execution-time provenance.
