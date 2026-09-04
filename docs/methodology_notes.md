# Methodology Guide

**Status:** completed-pipeline description, reviewed 2026-09-04\
**Experimental scope:** `controlled_50`\
**Pipeline:** 36 completed and frozen notebooks\
**Public interface:** [Streamlit dashboard](https://fhtw-painting-restoration.streamlit.app/)

This guide explains the main scientific and engineering decisions in the
completed painting-restoration evaluation framework. It is a navigation and
interpretation document, not a replacement for producer manifests, validation
tables, configurations, reports, or the thesis methodology chapter.

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

1. How can a multi-metric evaluation framework be designed to assess
   AI-generated painting restorations beyond traditional image similarity
   metrics?
2. How do selected pretrained inpainting models differ in restoration quality
   across artistic styles and artificial damage types?
3. To what extent can uncertainty estimation from multiple restoration
   candidates identify speculative or unreliable restored regions?

The implemented study extends those questions with region selection, colour,
texture, seams, spatial diagnostics, robustness, prompt sensitivity, failure
flags, explainability, compute and delivery. These additions remain evidence
components, not a universal restoration or trustworthiness score.

The central interpretation boundary is:

> Visual plausibility is not equivalent to restoration trustworthiness,
> historical correctness, authenticity, artist intent, or conservation approval.

## 2. Dataset and preprocessing

The controlled dataset contains 50 paintings divided evenly across five broad
visual categories:

- abstraction/surrealism;
- architecture/structured;
- high-texture/brushwork;
- landscape/natural;
- portrait/figure.

These are study strata, not independently validated art-historical styles.
Style/period, date/period and medium are populated for only 18 of the 50 works,
so analyses must not convert the balanced visual categories into general style
effects.

Notebook 02 standardizes each accepted image as a 768 × 768 RGB PNG. It preserves
aspect ratio, pads rather than distorts or center-crops, and records the exact
painting-content bounds. Padding is excluded wherever the declared region
requires painting content. Consumers use the recorded geometry rather than
estimating content from pixel colour.

## 3. Experimental case registry

Notebook 08 normalizes four experiment families into a 525-row case registry:

| Experiment | Cases | Design and statistical boundary |
|---|---:|---|
| Canonical missing-region damage | 250 | 50 paintings × five masks, including 50 identity controls |
| Damage-size sensitivity | 35 | Five paintings × seven nested area levels; painting and category are confounded |
| Mask robustness | 75 | Five paintings × three fixed family/area groups × five mask variants |
| Synthetic degradation | 165 | Controlled procedural effects; only 50 cases have approved masked-removal semantics |

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
This yields 410 eligible restoration cases for each method: 250 canonical, 35
damage-size, 75 robustness and 50 synthetic-degradation cases.

## 4. Restoration methods and candidate populations

| Method | Role | Validated scope |
|---|---|---:|
| OpenCV Telea | Deterministic classical baseline; radius 3 | 410 cases |
| LaMa through IOPaint | Deterministic pretrained learned baseline | 410 cases |
| Stable Diffusion 1.5 Inpainting | Stochastic, prompt-conditioned baseline | 410 primary candidates; 1,330 N11 candidates in total |
| SDXL Inpainting | Bounded feasibility/partial-evaluation branch | 10 cases nested within five paintings |

Zero controls are identity no-ops. The nonzero restoration branches use exact
mask compositing so active pixels may change while pixels outside the approved
mask remain unchanged. Binary and synthetic masks retain their distinct active
thresholds.

Stable Diffusion uses a fixed generic primary prompt and seed 2026 for the
410-case comparison. Its additional N11 candidates support contextual prompt
tests, four-seed uncertainty and a paired scratch-aware prompt experiment. The
formal scratch experiment contains 400 outcomes: 50 paintings × four seeds ×
two prompt arms. Seeds are repeated observations within paintings, not 200
independent paintings. Prompt sensitivity is not seed uncertainty.

Notebook 22 owns another 105 Stable Diffusion candidates—seeds 2027–2029 for
the 35 damage-size cases. They extend uncertainty coverage without altering N11.
The 1,785-candidate reporting/dashboard population is a validated downstream
selection, distinct from every candidate ever generated. “Approved” means
eligible for the declared analysis, not approved restoration quality.

SDXL completed all ten predeclared cases, but one seed per case and five
independent paintings cannot support a full benchmark or uncertainty estimate.
Runtime or hardware limitations are not image-quality failures.

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

The main three-model comparison uses eleven metric–region anchors:

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
separate anchors a model ranks first on; mean anchor rank describes its average
position across those same anchors. Neither is a combined quality score.
Runtime and uncertainty are excluded from quality voting. The core paired
comparison covers 410 cases and three models; a separate matched four-model view
covers only the ten SDXL cases.

## 8. Uncertainty and spatial explanation

Repeated-seed uncertainty requires exactly seeds 2026–2029 within a fixed case,
prompt and configuration:

- N18: 130 canonical prompt-specific groups—80 generic and 50 scratch-aware—
  containing 520 candidates and 780 unordered seed pairs;
- N22: 35 damage-size groups, using 35 N11 seed-2026 candidates and 105 new
  candidates, with 210 unordered seed pairs;
- final coverage: 165 complete groups.

The transparent components include per-pixel RGB standard deviation, pairwise
RGB MAE/RMSE, LPIPS distance and CLIP/DINOv2 cosine distance. N18 also joins
reference, perceptual, feature, texture, colour and seam evidence into a
130-row association-ready table. It does not fit confidence calibration, compute
a combined uncertainty index, or use later computational flags as ground truth.

N19 stores raw numeric maps and visual overlays for N18's 130 groups; N22 owns
the 35 damage-size maps. High variability identifies areas where repeated
candidates disagree and closer inspection may be useful. Low variability shows
consistency, not correctness. Telea and LaMa are deterministic, so their later
analyses use robustness or sensitivity terminology instead of artificial
uncertainty values. SDXL has insufficient seed coverage.

## 9. Analysis and statistical discipline

Comparisons are case-paired whenever models share the same case. Repeated masks,
seeds, prompts and cases nested within paintings are not treated as independent
paintings. Focused five-painting experiments support within-study trajectories
and sensitivity descriptions, not independent category effects.

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
Consequently, the 1,703 flagged candidates must not be described as a 95.4%
objective model-failure rate.

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
includes four model reports, 30 selected case reports, all 50 painting reports,
and a thesis-level evaluation report.

Notebook 34 prepares normalized dashboard tables and indexes. The approved
eight-page application is a read-only presentation and inspection interface. Its
later numerical views use the N34 candidate allow-list and checksum-verified
producer metrics as documented in
[`dashboard_numeric_metrics.md`](dashboard_numeric_metrics.md). The app does not
run restoration inference or recompute scientific metrics.

Notebook 36 assembles a checksum-verified supervisor and reproducibility package.
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
