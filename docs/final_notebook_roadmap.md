# Final Notebook Roadmap and Controlled-300 Scale-Up Overlay

## 1. Purpose

This roadmap defines the final dependency order and detailed responsibility of every notebook in the thesis repository:

**Trustworthy Evaluation Frameworks for AI-Assisted Painting Restoration**

It consolidates the previously planned roadmap into 36 stages while preserving the supported methodological, experimental, engineering, reporting, explainability, and deployment scope.

**Status as of 2026-09-09:** the validated 50-painting implementation is preserved
at Git tag `pilot-50-complete`. The working tree now contains the approved,
balanced 300-painting raw collection and is entering a controlled minimal-delta
rerun of Notebooks 01–36. Existing notebook names, responsibilities, cell order,
schemas, stable identifiers, and output roots remain the starting contract.
Each notebook becomes current only after its 300-painting outputs pass its gate;
until then, its committed outputs remain historical 50-painting evidence.

The completed HINT-versus-MAT selection study is now identified as **Decision
Notebook D01** (`notebooks/d01_hint_mat_method_selection.ipynb`). It remains
frozen decision evidence. A new production stage, **Notebook 12A**, will run the
selected HINT method across the full eligible 300-painting benchmark without
renumbering Notebooks 13–36.

The approved eight-page dashboard is publicly deployed at
[the Streamlit application](https://fhtw-painting-restoration.streamlit.app/).
Current application delivery is recorded separately from the historical N35
validation and N36 package in the dated addendum to
`docs/evidence_dependency_audit.md`. The approved application-only numerical
views are documented in `docs/dashboard_numeric_metrics.md`.

All notebooks follow `docs/refactoring_implementation_guidelines.md`.

### 1.1 Authoritative research-question framing

The controlled-300 rerun and every regenerated report, dashboard asset, and
delivery package use these questions:

1. **RQ1:** What additional evidence does a region-aware, multi-metric
   evaluation framework provide beyond traditional image-similarity metrics
   when evaluating AI-assisted painting restoration?
2. **RQ2:** How do selected inpainting methods differ in restoration quality
   across controlled artificial damage conditions, and how consistent are
   these differences across the evaluated paintings?
3. **RQ3:** How can repeated-candidate disagreement be used to characterize the
   stability of stochastic painting restorations, and how does it relate to
   other restoration-quality diagnostics?

Visual categories remain balanced descriptive subgroups; they are not an
independently estimated art-historical effect. Repeated-candidate disagreement
is evidence about stochastic stability, not a validated detector of error,
historical unreliability, or calibrated confidence. Existing 50-painting
notebooks and outputs retain their historical wording until their normal
controlled-300 rerun; they are not hand-edited retroactively.

## 2. Global execution model

The pipeline supports these configuration-driven scopes:

```text
smoke
controlled_300
```

`controlled_300` is the only active full execution profile. Parallel 50- and
300-painting raw datasets, configs, output roots, and notebook variants are not
maintained. The prior 50-painting study remains recoverable from
`pilot-50-complete` and must not be confused with newly generated evidence.

Every notebook writes only to:

```text
outputs/<exact_notebook_stem>/
```

Every completed notebook normally produces:

```text
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

`outputs/inventory/` is the only global-output exception.

### 2.1 Controlled-300 storage and publication overlay

**Bundle-access proof approved 2026-09-17:** a narrowly bounded N16 smoke may
test whether the complete original image bytes can be retrieved individually
from immutable, indexed, uncompressed ZIP members in the existing diagnostics
dataset. This does not reopen N16 science, publish all N16/N17 assets, change
the live pilot dashboard, or remove the pre-N34 storage and dashboard review.
Full N16 and N17 publication each passed a separate user-controlled gate on
2026-09-17/18; their Git handoffs remain distinct gates.
Successful smoke records belong in
`outputs/inventory/`, separately from the legacy direct-file registry.
The N16 proof passed with 76 exact-byte public image reads, three ZIPs, and
eight remote objects at immutable revision
`02ba1d971ffdf9e855f07e5266bba18cac71b929`. The isolated test prefix was
then removed from the current diagnostics branch; only the audit record
remains. The smoke itself was transport evidence, not the full publication.

**Full N16 release verified 2026-09-17:** 76,034 original images (76,020
candidate maps and 14 selected panels) are indexed in 333 immutable ZIP
bundles. All 641 objects, 2,625,210,541 published bytes, and four public
sample image reads passed remote checks at pinned diagnostics revision
`8c22aa62c5be60d8a15c9c00d9bc9a6f81557b79`. The separate release record
is `outputs/inventory/bundled_publication_n16_full.json`. Local canonical
outputs remain authoritative. Neither release changes the pre-N34 dashboard
review.

**Full N17 release verified 2026-09-18:** 27,926 original images (27,912
candidate maps and 14 selected panels) are indexed in 360 immutable ZIP
bundles. All 669 objects, 5,622,373,385 published bytes, and four public
sample image reads passed remote checks at pinned diagnostics revision
`ceac6a5aa67fe2a0f8c840c46f22306e7f606749`. The separate release record
is `outputs/inventory/bundled_publication_n17_full.json`. Local N17 outputs
remain canonical until the compact Git handoff and beyond it.

**Why this storage split:** N16/N17 generate diagnostic maps, local-consistency
panels, metrics and provenance—not new restoration candidates. They therefore
live under sibling producer paths in the existing Hugging Face `diagnostics`
dataset. The `candidates` dataset remains for model-produced restoration
images (the verified N12 and N12A candidate releases). The earlier N16
per-image upload exceeded the free Hub API request rate, while adding all maps
and large tables to Git/LFS would swell the scientific repository. Per-painting
indexed ZIPs reduce remote object/request counts and retain exact image bytes.
They use `ZIP_STORED`: this is an access and repository-size strategy, **not**
lossless compression that materially reduces the total hosted bytes.

The scientific output contract and the Git publication contract are separate.
Every notebook still generates, validates, reloads, visually inspects, and
inventories its complete canonical output tree locally. GitHub retains the
compact scientific record. The verified N16/N17 indexed-bundle workflow is
the approved **per-producer option** for subsequent image-heavy or oversized
outputs; publication is never automatic or a prerequisite for local scientific
completion. Classify the producer's assets, check free-tier capacity, stage
bounded per-painting `ZIP_STORED` bundles plus complete indexes, verify all
remote objects and public sample member reads at a pinned revision, and retain
the complete local tree. Candidate restorations belong in `candidates`;
diagnostic maps, panels, and oversized diagnostic tables belong in
`diagnostics`. The pre-N34 review still decides the dashboard's access and
storage contract; it is not a ban on verified producer publication.

Notebook 19 passed its local Controlled-300 completion gate with 2,475 owned
PNG assets and 3,000 links to validated upstream images. Its owned images are
diagnostics-tier material. The separate per-painting release under
`bundled_assets/v1/controlled_300/19_uncertainty_and_spatial_explanation_maps/40b468a3712044dc`
in the existing `diagnostics` dataset was uploaded and remotely verified at
revision `e080704d57d2a10ebe09d0395f348b9da85ea8f7`: all 609 objects
passed pinned SHA-256/size checks and four public sample assets were read
exactly. The upstream links were not copied into that release. The 27 MiB
numeric archive, compact tables, selected panels, manifests, source, and
configuration form the GitHub scientific handoff, which remains pending the
user's commit.

Notebooks 01--11 are the final approved full-output Git/LFS checkpoint for the
Controlled-300 rerun. Beginning with Notebook 12:

- GitHub retains notebook source, helpers, configuration, compact evidence
  tables, validation, manifests, selected figures, and external-asset indexes;
- already verified N12/N12A/N13/N15 objects retain their publication records,
  and N16/N17 each have a separate complete indexed-bundle release record;
- dashboard storage and archival options are reassessed after N33 using the
  actual verified producer releases, rather than assumed in advance; and
- the final Controlled-300 Streamlit packaging and deployment approach is
  approved only after storage feasibility and dashboard scope are reviewed.

The current `pilot-50` deployment remains unchanged while the scale-up is in
progress. No already committed history is rewritten during the active rerun.
External publication is not complete merely because an upload returns success:
the remote LFS SHA-256 and byte count must match producer-validated evidence,
with stable identity and a recorded URI. The prior public-read smoke test
confirms transport; full collections are checked through remote metadata
without downloading them again. Local canonical evidence is never deleted by
the publication tooling.

**Revised local-first decision (2026-09-17).** The pilot dashboard index
included all 10,050 Notebook 16 candidate maps and all 3,270 Notebook 17
candidate maps. Preserve equivalent complete case-level access as a design
requirement, but do not assume a storage provider or upload representation
before the pre-N34 review. Notebook 16's 76,020 maps and Notebook 17's 27,912
maps remain individually accessible by local manifest paths. An attempted
per-file Hugging Face dataset upload for N16 hit the free-account API rate
limit; its partial remote repository was removed by the user and the local
upload cache was cleared. That failed per-file attempt is superseded by the
separately verified full N16 bundle release; N17 subsequently passed its own
full bundle publication gate.
Previously verified N12–N15 records remain valid.

This decision does not require the present pilot-50 deployment to change.
Notebook 34 is the **first dashboard-asset-building notebook**. After Notebook
33 and before refactoring Notebook 34 or its application helpers, pause first
for a user-approved storage-options and feasibility review, then for a separate
Controlled-300 dashboard contract review: page-by-page content and numerical
evidence, complete visual-index scope, local/remote path resolution, memory
and network feasibility, lazy image loading, fallback behavior, and validation
examples. Notebook 34 then builds the approved package; Notebook 35 validates
the app and deployment behavior.
Do not assume the pilot app's local-only image resolver will work on the
lightweight Controlled-300 deployment. The final archive remains a separate
post-freeze reproducibility release, not the interactive image backend.

The **preliminary N34/N35 bundle-access option**, subject to that review, is:
retain compact metadata and case/candidate/map indexes with the deployed app;
resolve a selected visual to a producer-owned painting index and pinned N16 or
N17 diagnostics revision; fetch only its bounded ZIP bundle on demand; verify
the bundle/member hash; and reuse a bounded cache for nearby selections. The
app must not download all 693 N16/N17 bundles at startup. Large metric CSVs
must likewise be represented by approved compact, filterable views or on-demand
partitions rather than eagerly loaded into Streamlit Community Cloud memory.
Measure cold/warm latency, cache eviction, quota behavior, missing-asset
fallback, and cross-model case coverage before this becomes the final dashboard
contract. The live pilot-50 deployment is unchanged.

### 2.2 Binding downstream Controlled-300 execution overlay (approved 2026-09-18)

This overlay governs the N19–N33 rerun. Detailed sections below also preserve
the frozen pilot and may contain pilot counts; those are historical, not new
execution targets. Each preparation layer must reconcile its YAML, helpers,
notebook cells, manifest, and report mock with this overlay. Do not shrink the
approved evidence population to solve compute or storage issues.

| Notebook | Controlled-300 execution contract |
| --- | --- |
| N18 | Completed: 780 Stable Diffusion prompt groups, 3,120 candidates, 4,680 pairs, 124,800 metric rows, 780 calibration rows, and 150/150 passing checks. |
| N19 | Scale all numeric uncertainty maps and visual variants from 130 to **780 prompt-specific groups**; preserve separate generic and scratch-aware IDs. Use the diagnostics indexed-bundle option if output size warrants it. |
| N20 | Cover **16,404 completed candidates** numerically, including HINT. Render all **9,304 nonzero primary** candidate panels (four full methods × 2,320 cases plus 24 bounded SDXL completions). Bundle large maps/panels under diagnostics if needed. |
| N21 | Compare **four full methods × 2,620 paired cases = 10,480** selected candidates. Show **24 completed SDXL** candidates only as a separate bounded subset. Preserve metric-independent selection and painting-level leave-one-out analysis. |
| N22 | Use all **245** N05 cases (35 paintings × seven levels). Reuse N11 seed 2026 by reference, generate **735** missing seeds, and obtain **245** four-seed groups with **1,470** unordered pairs. Candidate images, if externally published, belong in `candidates`. |
| N23 | Analyze all **245** size cases and **980** four-method primary candidates, retaining all seven repeated levels and 35 paintings (seven per category). Use the bounded statistical design below. |
| N24 | Analyze all **525** matched mask cases and **2,100** four-method primary candidates, preserving three families and five variants per group across 35 paintings. Use the bounded statistical design below. |
| N25 | Analyze the full **1,155-case** degradation design; only **350** masked-removal-eligible cases enter the four-method primary comparison (**1,400** candidates). The **11** completed SDXL synthetic cases remain a separate bounded comparison. Preserve explicit exclusions. |
| N26 | Retain the existing adaptive inference design; update to four full methods, 300 canonical paintings, 35-painting focused cohorts, and 780 N18 plus 245 N22 uncertainty groups. |
| N27 | Apply fixed rule families linearly to the exact validated union of primary and supported repeated-seed candidates. Derive the union from candidate IDs, not the pilot 1,785. Include HINT; never fit thresholds on duplicate seeds. |
| N28 | Keep the **23 declared ablation scenarios** fixed. Do not enumerate metric-subset powersets. Chunk the candidate-scenario joins while retaining complete traceability. |
| N29 | Scale the full explanation catalog to N27's validated candidate union. Selected retrieval and visual panels remain report subsets, not a limit on the catalog. |
| N30 | Create **five** method cards: Telea, LaMa, HINT, Stable Diffusion and bounded SDXL. Analyze observed 300-painting compute/storage rather than projecting merely to 300. |
| N31 | Generate five self-contained method reports; distinguish the four full methods from SDXL's bounded scope. No new metric inference. |
| N32 | Generate **300 painting reports** plus auditable selected case reports. Index every applicable case, candidate, report, and upstream visual even when a visual is not embedded in every report. |
| N33 | Synthesize validated Controlled-300 evidence, four full methods, bounded SDXL, focused analyses and their limitations. Do not carry pilot-50 results forward as current claims. |

**N23–N25 bounded statistical redesign.** Keep every 35-painting focused
cohort balanced at seven paintings per broad visual category. Painting is the
independent unit; damage levels, mask variants, effects, regions and seeds are
nested/repeated observations. Predeclare a small primary inference grid from
the existing anchor definitions. The primary seven are
`classical_masked_mae`, `structural_crop_ssim`,
`perceptual_crop_lpips`, `feature_dino_crop`, `texture_crop_p95`,
`colour_masked_delta_e` and `seam_boundary_gradient`: one interpretable
representative of each core evidence concern. Test matched painting-level
model contrasts on those anchors and the notebook's declared exposure
(N23 size trajectory; N24 mask-variant dispersion; N25 eligible degradation
family/severity). Retain all 11 quality anchors and all required case-level
values, curves, comparisons, figures and visual examples as descriptive
evidence. Apply Benjamini–Hochberg correction within the declared
inferential families. Use **5,000 seeded painting-cluster bootstrap draws**
for 95% intervals on cached painting summaries and **100,000 seeded, batched
Monte Carlo sign flips** (with finite-simulation correction) for 35-painting
matched contrasts. Do not enumerate `35^35` ordered bootstrap samples or
`2^35` sign assignments. Exact enumeration is allowed only when the actual
independent-cluster count and a declared budget are small. N26's adaptive
method is the precedent, but N23–N25 must independently validate methods,
provenance, numerical results and report labels. Remove all hard-coded
five-*painting* assumptions; the five-*mask-variant* design remains valid.
Seven paintings per category permit exploratory category summaries, not an
independent art-historical style-effect claim.

Benchmark representative model/anchor/painting tasks before each expensive
N23–N25 stage and log a conservative full-batch projection. Target **36 hours
or less** for the longest batch; treat **50 hours as an operational ceiling**.
If projected work exceeds the range, improve vectorization, caching, chunking
or resume checkpoints and rebenchmark; do not thin approved paintings, methods,
eligible cases, metrics or visual evidence. Print progress at least every ten
inferential tasks. The gate is a planning control, not a runtime guarantee;
material scope changes require explicit approval.

For every notebook that produces a standalone report, an explicitly approved
chat mock is the binding report blueprint. The implemented report must retain the
mock's section order, question flow, table and visual roles, deterministic case
selection, conclusion and limitation placement, and approximate narrative and
visual density. Fictional planning values are replaced by validated results, and
validated additions may extend the report, but the assistant must not silently
redesign or replace the approved structure. Material deviations require renewed
user approval and must be recorded in mock-to-final traceability and final
validation as defined by `docs/refactoring_implementation_guidelines.md`.

## 3. Dependency overview

```text
Dataset and experiment generation: 01–08
Model restoration and candidate generation: 09–12A
Unified evidence generation: 13–20
Comparison, repeated-seed extension, and focused analysis: 21–30
Reporting, dashboard, and packaging: 31–36
Completed method-selection decision evidence: D01
```

The detailed notebook sections below preserve the scientific responsibilities
and, where stated, the observed cardinalities of the tagged 50-painting run.
Those historical numbers are not active assertions for the rerun. The following
overlay is binding whenever a detailed section still contains an old count.

### 3.1 Binding controlled-300 population overlay

| Population or stage | Controlled-300 contract |
|---|---:|
| Paintings | 300, exactly 60 in each of five broad visual categories |
| Canonical cases (N03–N04) | 1,500 = 300 paintings × five mask families including zero control |
| Damage-size cases (N05) | 245 = 35 paintings × seven nested damage levels |
| Mask-robustness cases (N06) | 525 = 35 paintings × 15 variants |
| Procedural degradation cases (N07) | 1,155 = 35 paintings × 33 degradations |
| Registered cross-experiment cases (N08) | 3,425 |
| Restoration-eligible cases per full method | 2,620, including 300 zero controls and 2,320 nonzero cases |
| Eligible procedural-degradation cases | 350 = 35 paintings × ten masked-removal cases |
| OpenCV Telea primary candidates (N09) | 2,620 |
| LaMa primary candidates (N10) | 2,620 |
| Stable Diffusion approved records (N11 + N22) | 5,995 |
| Stable Diffusion executions (N11 + N22) | 9,255 |
| HINT primary candidates (new N12A) | 2,620 |
| SDXL bounded feasibility candidates (N12) | 35, one per selected case |
| Four-seed Stable Diffusion uncertainty groups | 1,025 = 780 canonical prompt-specific + 245 damage-size groups |
| Four-seed uncertainty candidates / seed pairs | 4,100 candidates / 6,150 unordered pairs |
| Approved retained candidate records across methods | 13,890 |
| Total restoration executions, including non-retained prompt work | 17,150 |

The N05–N07 focused experiments use a shared, balanced 35-painting cohort—seven
paintings per visual category—to strengthen paired interpretation. Exact IDs
must be frozen in configuration before N05 execution and then reused by N06 and
N07. N12 uses a separate balanced 35-case SDXL feasibility scope. Counts for
metric rows, maps, figures, report units, and dashboard records must be derived
from validated upstream registries and compatibility policies; they must never
be obtained by multiplying a stale 50-painting literal.

### 3.2 Minimal-delta notebook adaptation map

| Notebook(s) | Required controlled-300 change |
|---|---|
| 01–02 | Load `controlled_300`; verify and preprocess all 300 paintings. |
| 03–04 | Expand deterministic canonical masks and damaged images to 1,500 cases while preserving mask/fill policies. |
| 05–07 | Replace the five-painting extension cohort with the frozen shared 35-painting cohort; preserve experiment definitions. |
| 08 | Rebuild the registry and eligibility tables for 3,425 registered and 2,620 eligible cases. |
| 09–10 | Rerun unchanged Telea and LaMa adapters for all 2,620 eligible cases. |
| 11 | Scale the existing Stable Diffusion prompt, primary, and repeated-seed policies; preserve the four seeds and scratch ablation. |
| 12 | Increase the bounded SDXL branch from ten to 35 balanced cases; keep it feasibility-only. |
| 12A | Add the selected HINT production run for all 2,620 eligible cases using the D01-validated native 768 × 768 adapter. |
| 13–21 | Rebuild model-agnostic evidence and comparisons from declared candidates, adding HINT wherever the metric family applies. |
| 22 | Generate the three missing Stable Diffusion seeds for all 245 damage-size groups: 735 new candidates. |
| 23–30 | Rebuild sensitivity, robustness, statistics, failure, XAI, model-card, and scalability evidence from expanded registries. |
| 31–36 | Regenerate reports, dashboard assets, deployment validation, and packages only after all expanded upstream gates pass. |
| D01 | Preserve unchanged as the completed HINT/MAT selection decision; it is not part of the numbered production rerun. |

### 3.3 Controlled-300 execution-time planning ranges

The following ranges are operational planning estimates for the remaining
controlled-300 rerun on the current RTX 3060 laptop and local SSD. They are not
scientific results or runtime guarantees. They use the observed 50-painting
work, current 300-painting cardinalities, retained checkpoint policies, and the
dominant computation in each notebook. They include notebook computation and
artifact writing, but exclude user review, debugging, inventory refresh,
external upload time, and deliberate pauses between batches. Thermal throttling,
Windows background load, file-cache state, and library changes can move an
individual run outside its range.

| Notebook | Upper planning range | Dominant work and execution note |
|---|---:|---|
| 12A — HINT restoration | 4–6 hours | 2,320 GPU inferences plus 300 identity controls; ten-case resumable checkpoints. |
| 13 — Classical metrics | Observed 7 h 58 m; planning range was 18–30 hours | Region-aware full-reference metrics over the expanded multi-model candidate population; checkpointed every ten cases. The observed run finished materially below the conservative planning range. |
| 14 — LPIPS metrics | 35–90 minutes; allow a 2-hour operational ceiling | Batched GPU perceptual inference over 31,608 compatible candidate-region rows. The 4,170-row pilot compute took 263.4 seconds; the active estimate scales that observation and allows extra disk, cache, and thermal overhead. |
| 15 — Feature similarity | Observed extraction 1 h 44 m 31 s plus 3 m 20 s metric construction; planning range was 2–4 hours with a 6-hour ceiling | CLIP and DINOv2 extraction over 78,336 deduplicated embeddings dominated the run. The observed compute stayed below the planning range; the approximately 2 h 56 m wall-clock span includes model loading, persistence, validation, visualization, and user pauses between batches. |
| 16 — Difference maps and spatial diagnostics | 36–72 hours | Dense numeric maps, rendered spatial panels, compression, and high-volume disk writes; expect a multi-session resumable run. |
| 17 — Local consistency metrics | Observed 37 h 44 m elapsed wall span, including pauses; planned 24–48 hours | Texture, colour, seam, boundary, and directional evidence across compatible candidates and regions. Batch 7's two full image-manifest validation passes added substantial disk I/O after map generation. |
| 18 — Diffusion uncertainty | 1–3 hours | Vectorized seed-group and pairwise scalar analysis using saved candidates and embeddings. |
| 19 — Uncertainty and spatial explanation maps | 12–24 hours | Dense repeated-seed variability maps, overlays, and rendered heatmaps. |
| 20 — Semantic and structural consistency | 24–36 hours | Pilot completed in about 3 hours 38 minutes for 2,160 candidates and 1,090 panels; controlled-300 scales to 16,404 candidates and 9,304 panels. Local CLIP/DINOv2 grids and full panel rendering dominate; estimate assumes the same machine and excludes publication. |
| 21 — Multi-model comparison | 8–16 hours | Large evidence joins, direction-aware comparisons, ranking stability, figures, and a self-contained report. |
| D02 — Portrait audit | 2–5 compute hours, plus 3–6 review hours | Existing-evidence screening, anatomical annotation review, matched analysis, and report generation; no new inference unless separately approved. |
| 22 — Damage-size diffusion extension | 6–12 hours | 735 new Stable Diffusion candidates with resumable generation and validation. |
| 23 — Damage-size sensitivity analysis | 8–16 hours | Expanded trajectories, multi-model metric joins, statistical summaries, figures, and report generation. |
| 24 — Mask robustness analysis | 3–8 hours | Matched robustness joins, effect summaries, statistical evidence, figures, and report generation. |
| 25 — Synthetic degradation analysis | 8–16 hours | Eligible degradation comparisons across full methods, diagnostic summaries, figures, and report generation. |
| 26 — Grouped and statistical analysis | 4–10 hours | Painting-level aggregation, paired effects, intervals, corrected tests, and sensitivity analyses. |
| 27 — Failure taxonomy and trustworthiness flags | 4–10 hours | Rule application over expanded evidence, case catalogs, explanations, figures, and report generation. |
| 28 — Metric and region-policy ablation | 24–48 hours | Repeated metric-policy and region-policy evaluations; checkpoint every bounded ablation block. |
| 29 — Explainable AI and case retrieval | 6–14 hours | Full explanation catalog, counterfactual evidence, embedding retrieval, visual units, and report generation. |
| 30 — Model cards, compute, and scalability | 2–5 hours | Evidence aggregation, runtime/compute summaries, model cards, figures, and report generation. |
| 31 — Model report generation | 3–8 hours | Self-contained model reports with embedded web-sized figures and selected examples. |
| 32 — Case and painting report generation | 8–18 hours | Report generation across 300 paintings and the expanded case catalog; heavy HTML/image encoding. |
| 33 — Final evaluation report | 3–8 hours | Thesis-level evidence aggregation, final figures, embedded visual evidence, and report validation. |
| 34 — Streamlit dashboard assets | 2–6 hours | Dashboard table/materialized-view construction, asset selection, figures, and package checks. |
| 35 — Dashboard and deployment validation | 10–30 minutes | Static/package validation and local application checks; no metric or restoration recomputation. |
| 36 — Supervisor/publication package | 1–4 hours locally | Checksums, manifests, compact packaging, and publication records; remote Hugging Face or Zenodo upload time is additional. |

Every notebook preparation contract must refine its row using the latest
upstream cardinalities and measured runtimes. After completion, the observed
active-compute runtime and any material difference from this planning range
must be recorded in the notebook manifest or governing evidence audit.

---

# Foundation and Experimental Datasets

## 01 — Dataset Verification

**Notebook:** `01_dataset_verification.ipynb`  
**Origin:** Existing Notebook 01  
**Controlled-300 refactor status:** Finished\
**Validation status:** Finished\
**Completion gate passed:** Yes\
**Active validated coverage:** 300 artworks; 60 per visual category; 448 audit rows; 50 validation rows  
**Pilot comparison:** All seven pilot output paths and table schemas retained; population-dependent evidence expanded without unexplained loss  
**Output root:** `outputs/01_dataset_verification/`  
**Depends on:** raw metadata, raw images, dataset configuration, current inventory

### Purpose

Establish the authoritative artwork table and verify that every dataset scope is suitable for preprocessing and controlled evaluation.

### Required inputs

- `data/raw/metadata/<dataset metadata>.csv`
- `data/raw/images/`
- dataset configuration
- inventory CSV and inventory run manifest

### Responsibilities

- Validate required metadata columns.
- Enforce unique and deterministic `painting_id` values.
- Validate expected dataset row counts.
- Validate image existence, readability, format, dimensions, and file integrity.
- Detect duplicate metadata records.
- Detect duplicate images by checksum.
- Detect near-duplicate images where practical and document the method and threshold.
- Record source, source URL, licence, and public-domain/open-access status.
- Record artist, title, date/period, style/category, medium, and source where available.
- Quantify metadata completeness by field and dataset scope.
- Summarize distributions by category, style, source, medium, period, and other sufficiently populated groups.
- Record group imbalance.
- Record known historical, geographic, source, and representation biases.
- Validate deterministic ordering.
- Record dataset version and optional file checksums.
- Support the active `controlled_300` profile; the tagged 50-painting profile is
  historical provenance, not a parallel runtime option.
- Produce prompt-metadata readiness information without making prompt policy decisions.
- Render a compact rule-selected dataset preview.

### Canonical outputs

```text
data/artworks.csv
metrics/dataset_audit.csv
figures/dataset_distribution.png
figures/dataset_preview.png
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

Additional persisted summaries are allowed only if required downstream.

### Validation gate

- Required columns present.
- Expected unique paintings present.
- No unresolved duplicate identifiers.
- Every accepted image exists and reloads.
- Every accepted record has a valid source/licence status or a documented exclusion.
- Dataset version and deterministic sort order recorded.

### Downstream consumers

Notebooks 02, 26, 30, 33, 34, and 36.

---

## 02 — Image Preprocessing

**Notebook:** `02_image_preprocessing.ipynb`  
**Origin:** Existing Notebook 02  
**Controlled-300 refactor status:** Finished
**Validation status:** Finished
**Completion gate passed:** Yes
**Active validated coverage:** 300 clean 768 × 768 RGB PNGs; 300 preprocessing rows; 45 audit rows; 50 validation rows  
**Pilot comparison:** All 50 pilot clean PNGs and the canonical preview are byte-identical; output count increased from 56 to 306 only through the expanded clean-image population  
**Output root:** `outputs/02_image_preprocessing/`  
**Depends on:** Notebook 01

### Purpose

Create standardized clean reference images and authoritative painting-content geometry.

### Responsibilities

- Produce fixed 768 × 768 RGB PNG images.
- Preserve aspect ratio.
- Use median-RGB padding.
- Record explicit content bounding boxes.
- Record original and processed dimensions.
- Record resize scale and all padding values.
- Use deterministic processing.
- Use repository-relative paths.
- Preserve a clean reference for every accepted painting.
- Validate output mode, format, dimensions, and readability.
- Validate that content bounds are within the canvas.
- Calculate content and padding areas.
- Record preprocessing method and version.
- Detect missing, stale, duplicate, and orphaned outputs.
- Reload and verify every saved image.
- Support configuration-driven scaling.
- Add EXIF-orientation, ICC-profile, and colour-space handling only if input auditing proves they are needed.
- Record runtime statistics if they are useful for scalability analysis.
- Render representative before/after/padding previews.

### Canonical outputs

```text
data/preprocessed_images.csv
images/clean/<painting_id>.png
metrics/preprocessing_audit.csv
figures/preprocessing_preview.png
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

### Validation gate

- One validated output per accepted painting.
- All images are 768 × 768 RGB PNG.
- Aspect-ratio and padding metadata reconcile with the saved pixels.
- Content boxes are valid.
- No unexpected files remain in the notebook-owned image folder.

### Downstream consumers

Notebooks 03–08 and all later visual/reporting stages through manifests.

---

## 03 — Canonical Mask Generation

**Notebook:** `03_canonical_mask_generation.ipynb`  
**Origin:** Existing Notebook 03  
**Controlled-300 refactor status:** Finished  
**Validation status:** Finished  
**Completion gate passed:** Yes  
**Active validated coverage:** 300 paintings × 5 families = 1,500 canonical masks; 105 audit rows; 50 validation rows; 24 completion requirements  
**Pilot comparison:** All 250 pilot mask PNGs are byte-identical, the 89-column schema is unchanged, and output count increased from 258 to 1,508 only through 1,250 additional masks  
**Output root:** `outputs/03_canonical_mask_generation/`  
**Depends on:** Notebook 02

### Purpose

Generate the canonical binary missing-region masks for the main controlled experiment.

### Canonical mask families

- `zero_control`
- `scratch_thin`
- `loss_small`
- `loss_large`
- `mixed_damage`

### Responsibilities

- Implement descriptive mask families as versioned numerical presets.
- Record target, lower, and upper damaged-content fractions.
- Record generator parameters, retry tolerance, maximum attempts, morphology settings, seeds, and configuration version.
- Use deterministic global, per-painting, per-mask, and retry seeds.
- Restrict all damage to the painting-content region.
- Save masks as grayscale binary PNG with exact values 0 and 255.
- Record damaged pixel counts and percentages relative to content and full image.
- Record bounding boxes, dimensions, and fill ratio.
- Record connected-component count and component-area statistics.
- Record largest, smallest, mean, median, and variability of component areas where useful.
- Record elongation, compactness, density, and aspect indicators where useful.
- Record boundary-touch indicators and distance from the content boundary.
- Record padding overlap.
- Verify morphology expectations:
  - scratches are elongated and comparatively thin;
  - small losses are smaller than large losses;
  - large losses occupy substantially more area;
  - mixed damage combines multiple characteristics;
  - mask families are not geometrically equivalent.
- Run deterministic replay validation.
- Detect duplicate, stale, and orphaned masks.
- Reload and verify saved masks.
- Explicitly exclude blur, fading, discolouration, dirt, stains, and other non-binary degradations.

### Canonical outputs

```text
data/masks.csv
images/masks/<painting_id>/<mask_type>.png
metrics/mask_audit.csv
figures/mask_morphology.png
figures/mask_examples.png
reports/mask_protocol.md
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

### Validation gate

- Exactly one unique `(painting_id, mask_type)` row per configured case.
- Zero controls contain no damaged pixels.
- Non-zero masks contain damaged pixels.
- Every damaged pixel is within content and outside padding.
- Realized areas satisfy configured tolerances.
- Morphology-family checks pass or documented cases are excluded.
- All saved masks reload identically.

### Downstream consumers

Notebooks 04, 05, 06, 08, and all region-aware evidence stages.

---

## 04 — Canonical Damaged-Image Generation

**Notebook:** `04_canonical_damaged_image_generation.ipynb`  
**Origin:** Existing Notebook 04  
**Controlled-300 refactor status:** Finished\
**Validation status:** Finished\
**Completion gate passed:** Yes\
**Active validated coverage:** 300 paintings × 5 families = 1,500 canonical cases and damaged PNGs; 1,500 audit rows; 60 validation rows; 28 final completion requirements\
**Pilot comparison:** All 250 pilot damaged PNGs are byte-identical, the 34-column case and 40-column audit schemas are unchanged, and output count increased from 256 to 1,506 only through 1,250 additional damaged images\
**Output root:** `outputs/04_canonical_damaged_image_generation/`  
**Depends on:** Notebooks 02 and 03

### Purpose

Apply canonical masks to clean images and create the controlled baseline restoration inputs.

### Responsibilities

- Validate clean-image and mask dimensions.
- Apply the configured corruption/fill strategy.
- Retain white fill as the canonical baseline unless a later sensitivity experiment explicitly changes it.
- Verify that only masked pixels change.
- Verify changed-pixel count against the binary mask.
- Preserve zero-control images exactly.
- Record clean, mask, and damaged-image foreign keys and paths.
- Record fill strategy and parameters.
- Record optional checksums where useful.
- Validate output mode, format, size, and readability.
- Detect stale and orphaned outputs.
- Reload and verify saved outputs.
- Produce a normalized canonical case table rather than copying all artwork and mask columns.

### Canonical outputs

```text
data/cases.csv
images/damaged/<painting_id>/<mask_type>.png
metrics/damage_audit.csv
figures/damage_examples.png
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

### Validation gate

- Expected canonical case count present.
- Unique `case_id` values.
- Every output differs from clean only where permitted.
- Zero controls match clean images exactly.
- Every output reloads successfully.

### Downstream consumers

Notebook 08 and later model/evidence stages.

---

## 05 — Damage-Size Sensitivity Dataset Generation

**Notebook:** `05_damage_size_sensitivity_dataset_generation.ipynb`  
**Origin:** Existing Notebook 05  
**Controlled-300 refactor status:** Finished\
**Validation status:** Finished\
**Completion gate passed:** Yes\
**Active validated coverage:** 35 paintings × 7 nested levels = 245 matched cases, mask PNGs, damaged PNGs, and audit rows; 96 validation rows; 27 pre-registry completion requirements\
**Pilot comparison:** All 76 pilot artifact paths are retained; all 70 shared mask and damaged PNGs are byte-identical; the 55-column case and 67-column audit schemas are unchanged; output count increased from 76 to 496 through 420 additional generated images; the canonical figure changed only because its rule-selected representatives now use the expanded cohort\
**Output root:** `outputs/05_damage_size_sensitivity_dataset_generation/`  
**Depends on:** Notebooks 02 and 03

### Purpose

Create a matched experimental dataset for testing how restoration behavior changes with damaged-content percentage.

### Responsibilities

- Use candidate target levels such as 2%, 4%, 6%, 8%, 10%, 15%, and 20%.
- Permit a documented adjusted level set if compute or morphology requires it.
- Span small, moderate, and substantial damage.
- Use matched paintings.
- Preserve mask morphology and placement as far as practical while scaling area.
- Record target and realized area.
- Record scaling parameters and deterministic seeds.
- Generate masks and corresponding damaged images.
- Record morphology drift introduced by scaling.
- Produce one normalized case manifest.
- Prepare comparable cases for every eligible restoration model.
- Do not calculate final performance curves here.
- Render matched progression figures for representative paintings.

### Canonical outputs

```text
data/cases.csv
images/masks/<painting_id>/<level_id>.png
images/damaged/<painting_id>/<level_id>.png
metrics/generation_audit.csv
figures/damage_size_progression.png
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

### Validation gate

- Expected matched design present.
- Realized areas fall within tolerance.
- Morphology-preservation diagnostics are recorded.
- Unique case and mask IDs.
- Saved masks and images reload.

### Downstream consumers

Notebooks 08–12, 22, 25, 28, 32, and 33.

---

## 06 — Mask Robustness Dataset Generation

**Notebook:** `06_mask_robustness_dataset_generation.ipynb`  
**Origin:** Existing Notebook 06  
**Controlled-300 refactor status:** Finished  
**Validation status:** Finished  
**Completion gate passed:** Yes  
**Output root:** `outputs/06_mask_robustness_dataset_generation/`  
**Depends on:** Notebooks 02, 03, and the matched-painting policy from 05

**Validated active coverage:** 35 paintings balanced at seven per visual
category; three mask families; five variants per painting-family group; 105
robustness groups; 525 case rows, masks, damaged images, and audit rows; 102
validation rows; 21 passed completion requirements.

**Pilot comparison:** All 156 pilot artifact paths, table schemas, and artifact
roles are retained. Of 151 shared PNG paths, 148 are byte-identical. The active
run deliberately regenerates the `p039` `loss_small` fourth mask variant and its
damaged image because helper v3.1.1 enforces the configured multi-component
morphology for every candidate; the representative figure consequently changes.
The output count increases from 156 to 1,056 through exactly 450 additional
masks and 450 corresponding damaged images.

### Purpose

Test whether conclusions depend excessively on one favorable or unfavorable mask realization.

### Responsibilities

- Hold painting, mask family, target percentage, and broad morphology constant.
- Vary seed, location, exact geometry, and component arrangement.
- Generate multiple variants per robustness group.
- Record group IDs, seeds, location, morphology, component, and boundary statistics.
- Verify that variants are genuinely distinct.
- Generate corresponding damaged images.
- Preserve comparable target areas.
- Produce a normalized robustness case manifest.
- Prepare cases for every eligible restoration model.
- Render representative within-group comparison grids.
- Leave metric variance, confidence intervals, and ranking stability to Notebook 24.

### Canonical outputs

```text
data/cases.csv
images/masks/<robustness_group_id>/<variant_id>.png
images/damaged/<robustness_group_id>/<variant_id>.png
metrics/generation_audit.csv
figures/robustness_examples.png
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

### Validation gate

- Correct variants per group.
- Target-area tolerance satisfied.
- Variants are non-identical.
- Location and morphology variation is documented.
- No duplicate, stale, or orphaned artifacts.

### Downstream consumers

Notebooks 08–12, 24, 25, 28, 32, and 33.

---

## 07 — Synthetic Degradation Dataset Generation

**Notebook:** `07_synthetic_degradation_dataset_generation.ipynb`  
**Origin:** Existing Notebook 07
**Controlled-300 refactor status:** Finished
**Validation status:** Finished
**Completion gate passed:** Yes
**Output root:** `outputs/07_synthetic_degradation_dataset_generation/`
**Depends on:** Notebook 02

**Validated Controlled-300 result:** Reused the frozen balanced 35-painting cohort
from Notebooks 05 and 06, with seven paintings per controlled visual category.
Generated 1,050 single-degradation cases and 105 combined-degradation cases, for
1,155 normalized cases, effect-support masks, degraded images, and audit rows.
The ten operator definitions, three ordered combinations, severity parameters,
seed scheme, and representative `p039` smoke/example scope remain unchanged so
the five pilot anchors stay directly comparable. All 337 pilot artifact paths
remain present, all 330 shared generated PNGs are byte-identical, and the active
output root contains exactly 2,317 validated files.

### Purpose

Create a separate, explicitly non-binary degradation branch.

### Candidate degradation types

- Gaussian blur;
- directional/motion blur;
- local defocus;
- water-like staining;
- pigment bleeding;
- fading;
- discolouration;
- local darkening;
- dirt or dust overlays;
- partial transparency;
- selected combined degradations.

### Responsibilities

- Define every operator algorithmically.
- Retain the clean reference.
- Separate effect-support masks from degradation operators.
- Record all parameters and seeds.
- Record severity levels and combined components.
- Generate one degradation manifest with normalized core case fields.
- Record affected area, spatial support, changed pixels, colour/texture impact proxies, and operator parameters.
- Document physical limitations.
- State explicitly that procedural effects are not exact simulations of conservation damage.
- Validate individual and selected combined degradations.
- Avoid describing the output as missing-region damage.
- Prepare cases for model-eligibility decisions in Notebook 08.
- Render representative single and combined degradation examples.

### Canonical outputs

```text
data/cases.csv
images/effect_masks/<painting_id>/<degradation_id>.png
images/degraded/<painting_id>/<degradation_id>.png
metrics/generation_audit.csv
figures/degradation_examples.png
reports/degradation_protocol.md
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

### Validation gate

- Expected case design present.
- Parameters and seeds recorded.
- Effect masks and degraded images reload.
- Clean references remain unchanged.
- Degradation changes reconcile with recorded spatial support.
- Limitations and applicability remain explicit.

### Downstream consumers

Notebooks 08–12, 17, 20, 24, 25, 28, 32, and 33.

---

## 08 — Experiment Contracts and Region Policy

**Notebook:** `08_experiment_contracts_and_region_policy.ipynb`  
**Origin:** New Notebook; incorporates the methodological responsibility of Previous Notebook 26  
**Controlled-300 refactor status:** Finished\
**Validation status:** Finished\
**Completion gate passed:** Yes\
**Active validated coverage:** 3,425 registered cases; 17,125 explicit routing decisions across five methods; 2,620 eligible cases per method; 143 metric-region policy rows; 101/101 scientific checks; 20/20 final completion requirements\
**Pilot comparison:** All nine pilot artifact paths and table schemas retained; all 525 pilot case rows retained with only the intentional dataset-scope transition; all 2,100 shared case-model decisions unchanged; 143-row region policy byte-identical; five schema definitions unchanged; output-file count remains nine
**Output root:** `outputs/08_experiment_contracts_and_region_policy/`  
**Depends on:** Notebooks 01–07

**Approved Controlled-300 target:** Combine 1,500 canonical cases, 245
damage-size cases, 525 mask-robustness cases, and 1,155 procedural-degradation
cases into a 3,425-row registry. Register five methods—OpenCV Telea, LaMa,
Stable Diffusion Inpainting, bounded SDXL Inpainting, and selected full-coverage
HINT—yielding 17,125 explicit case-model decisions and 2,620 methodologically
eligible cases per model. Preserve the 11-region, 13-metric-family, 143-row
region policy and all existing schemas and artifact paths.

### Purpose

Create the normalized cross-experiment case registry, formalize model eligibility, and establish the authoritative metric-region policy before restoration and metric computation.

### Responsibilities

- Combine core case fields from canonical damage, damage-size, robustness, and synthetic degradation manifests.
- Preserve experiment-specific details in their source tables rather than widening the case registry.
- Validate stable identifiers and source-manifest references.
- Define model eligibility for each case.
- Define input semantics, mask/effect semantics, and restoration objective.
- Prevent methodologically invalid restoration routing.
- Define:
  - full image;
  - painting-content region;
  - exact masked pixels;
  - mask bounding-box crop;
  - inner boundary band;
  - outer boundary band;
  - symmetric boundary ring;
  - outside-mask content region;
  - outside boundary ring;
  - degradation-support region;
  - patch/sliding-window semantic regions.
- Define valid and invalid metric-region combinations.
- Define mask-box margin, boundary widths, threshold policies, and spatial-support metadata.
- Generate the thesis/dashboard region-policy table.
- Prepare alternative region policies for Notebook 28.
- Validate the canonical `regions.py` helper against representative masks.
- Explicitly prohibit sparse masked-pixel SSIM.

### Canonical outputs

```text
data/case_registry.csv
data/model_eligibility.csv
data/region_policy.csv
data/schema_registry.json
figures/region_definitions.png
reports/evaluation_contract.md
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

### Validation gate

- All accepted cases trace to exactly one source manifest.
- Core case identifiers are unique.
- Eligibility decisions have explicit reasons.
- Region masks are mutually consistent and remain inside permitted content support.
- Every metric-family compatibility rule is explicit.

### Downstream consumers

All notebooks 09–36.

---

# Restoration and Candidate Generation

## 09 — OpenCV Telea Restoration

**Notebook:** `09_opencv_telea_restoration.ipynb`  
**Origin:** Existing Notebook 08  
**Controlled-300 refactor status:** Finished\
**Validation status:** Finished\
**Completion gate passed:** Yes\
**Active validated coverage:** 2,620 eligible cases and restored PNGs across 300 paintings; 1,500 canonical, 245 damage-size, 525 mask-robustness, and 350 eligible synthetic-degradation cases; 300 zero controls and 2,320 nonzero cases; 72/72 scientific checks; 15/15 roadmap requirements; 2,626 canonical files\
**Pilot comparison:** All 416 pilot paths and all CSV schemas are retained; 409/410 shared restoration PNGs are byte-identical; the sole changed shared PNG is the already-documented `p039` `loss_small` fourth robustness variant inherited from Notebook 06 helper v3.1.1 morphology enforcement; the representative figure is byte-identical; output count increased from 416 to 2,626 through 2,210 additional restored images\
**Output root:** `outputs/09_opencv_telea_restoration/`  
**Depends on:** Notebook 08

**Approved Controlled-300 target:** Preserve the fixed-radius, deterministic
Telea method, threshold policies, schemas, identifiers, artifact paths, and
eight-batch notebook structure while expanding the validated worklist from 410
to 2,620 eligible cases: 1,500 canonical, 245 damage-size, 525 mask-robustness,
and 350 localized synthetic-degradation cases. Produce 2,620 restored PNGs and
2,620 normalized restoration records across 300 unique clean paintings. Keep
the five-row runtime summary, eight rule-pinned representative cases, five
artifact records, and six canonical non-image outputs unchanged in structure,
for 2,626 physical output files. The original 410 candidate identities and
paths remain continuity evidence; changed image bytes are not expected because
the Telea algorithm and its source inputs remain unchanged.

### Purpose

Produce the deterministic classical inpainting baseline for all eligible cases.

### Responsibilities

- Process canonical, damage-size, robustness, and eligible degradation cases.
- Respect the model-eligibility table.
- Use fixed, documented Telea parameters with no per-case tuning.
- Record algorithm, radius, OpenCV version, runtime, CPU environment, retry count, and status.
- Preserve zero controls according to the approved zero-control policy.
- Validate output dimensions, mode, format, and readability.
- Validate inside-mask changes and outside-mask invariance.
- Record failures without silently dropping cases.
- Use normalized restoration records rather than copying upstream tables.
- Produce representative restoration previews.

### Canonical outputs

```text
data/restorations.csv
images/restored/<experiment_id>/<case_id>.png
metrics/runtime_summary.csv
figures/restoration_examples.png
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

### Downstream consumers

Notebooks 13–17 and all later comparison/reporting stages.

---

## 10 — LaMa Restoration

**Notebook:** `10_lama_restoration.ipynb`  
**Origin:** Existing Notebook 14  
**Output root:** `outputs/10_lama_restoration/`  
**Depends on:** Notebook 08

### Purpose

Produce the learned deterministic/non-sampling inpainting baseline with standardized runtime and failure handling.

### Responsibilities

- Process every LaMa-eligible case.
- Record exact model/source implementation, IOPaint version, device, hardware, runtime, retries, commands/log references, and failure details.
- Normalize input staging without duplicating authoritative source data.
- Preserve zero controls according to policy.
- Validate mask thresholding and output geometry.
- Validate outside-mask preservation where compositing policy requires it.
- Support resumable execution.
- Record partial and failed cases explicitly.
- Generate a normalized restoration table.
- Render representative outputs and failure examples.

### Canonical outputs

```text
data/restorations.csv
images/restored/<experiment_id>/<case_id>.png
metrics/runtime_summary.csv
figures/restoration_examples.png
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
logs/<retained failure logs>
```

### Downstream consumers

Notebooks 13–17 and all later comparison/reporting stages.

### Controlled-300 completion record

Notebook 10 is complete for `controlled_300`. It produced 2,620 normalized LaMa
records and restored RGB PNGs across 1,500 canonical, 245 damage-size, 525
mask-robustness, and 350 eligible synthetic-degradation cases. The population
contains 300 exact identity/no-op controls and 2,320 learned-inference cases.
All 80 scientific checks, seven persistence checks, five manifest-handoff checks,
four registry checks, eight final checks, and 16 roadmap requirements passed.
The five-row runtime table, eight-case representative figure, five artifact
records, completed run manifest, and exact 2,626-file canonical output set were
validated; `work/` is empty. Full execution took 4,594.223 seconds on the recorded
environment.

The read-only pilot comparison at `E:/outputs/10_lama_restoration/` confirms that
all 416 pilot paths and all CSV schemas remain present. The representative figure
and 409 of 410 shared restoration PNGs are byte-identical. The sole changed shared
PNG is the inherited Notebook 06 `p039` mask-morphology correction; 2,210 added
restoration PNGs account for the complete scale-up difference.

---

## 11 — Stable Diffusion Restoration

**Notebook:** `11_stable_diffusion_restoration.ipynb`  
**Origin:** Existing Notebook 21; incorporates candidate generation required by uncertainty analysis  
**Controlled-300 refactor status:** Finished\
**Validation status:** Finished\
**Completion gate passed:** Yes\
**Active validated coverage:** 8,520 completed candidate records and restored RGB PNGs across 300 paintings; 2,620 primary, 4,460 prompt-context, and 1,440 uncertainty-extension rows; 8,220 model inferences and 300 identity controls; 1,355 design rows; 176/176 scientific checks; 23/23 completion requirements; 8,530 canonical files\
**Pilot comparison:** All ten pilot non-image output paths and all CSV schemas retained; 1,298/1,330 pilot candidate identities remain in the expanded deterministic design and 1,297/1,298 shared images are byte-identical; the sole changed shared image inherits Notebook 06's documented `p039` morphology correction; 32 exploratory p01-p04 prompt-context candidates were transparently displaced when the approved non-metric hash-stratified selection was recomputed over the 300-painting population; both figures were regenerated from expanded rule-selected evidence
**Output root:** `outputs/11_stable_diffusion_restoration/`  
**Depends on:** Notebook 08
**Supplemental contract:** `docs/notebook_11_scratch_prompt_ablation_contract.md`

### Purpose

Generate Stable Diffusion restoration candidates under fixed reproducible policies and controlled repeated seeds.

### Responsibilities

- Process every Stable-Diffusion-eligible case.
- Use a fixed documented primary prompt policy.
- Record prompt, negative prompt, prompt-policy ID, variant ID, and metadata fields used.
- Record scheduler, inference steps, guidance scale, strength, seed, model revision, precision, device, attention/memory settings, and compositing policy.
- Prevent prompt engineering from becoming an uncontrolled variable.
- Run the generic restoration prompt on the approved primary scope.
- Run style/context-specific prompt variants only as a controlled prompt-ablation experiment.
- Compare generic and style-specific prompts without selecting candidates using evaluation metrics.
- Run a paired scratch-aware prompt ablation on all 300 canonical paintings using the four frozen uncertainty seeds.
- Preserve both prompt arms for every painting-seed pair and reuse existing generic candidates rather than duplicate inference.
- Treat paintings as the independent units and seeds as repeated observations in downstream inference.
- Document thin-mask downsampling and exact-compositing residual lines as a Stable Diffusion limitation that prompting may mitigate but cannot be assumed to solve.
- Generate repeated-seed candidates for all approved uncertainty-eligible non-zero cases, subject to configured feasibility.
- Retain candidate-level outputs and stable candidate IDs.
- Record runtime, GPU memory, retries, failures, and environment.
- Validate mask thresholding and compositing.
- Validate outside-mask preservation where enforced.
- Copy or otherwise handle zero controls according to the approved policy.
- Support resume based on IDs, checksums, model revision, and configuration.
- Produce normalized candidate/restoration tables instead of wide inherited schemas.

### Canonical outputs

```text
data/candidates.csv
data/prompt_policy.csv
images/restored/<experiment_id>/<case_id>/<candidate_id>.png
metrics/runtime_summary.csv
metrics/prompt_ablation_design.csv
figures/candidate_examples.png
figures/prompt_comparison_examples.png
reports/prompt_policy.md
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

### Validation gate

- Candidate IDs unique.
- Required primary and repeated-seed candidates accounted for.
- No metric-based candidate selection.
- Prompts/settings recorded.
- Outputs reload and match expected geometry.
- Failures and omissions are explicit.
- Exactly 300 canonical scratch cases, four declared seeds, and two matched prompt arms.
- Exactly 2,400 formal scratch outcomes with both prompts present for every painting-seed pair.
- Exactly 8,520 total candidate records: 2,620 primary, 4,460 prompt-context, and 1,440 uncertainty-extension rows.
- Exactly 8,220 model-inference candidates after the 300 identity zero controls.
- Exactly 720 added generic scratch seed controls and 1,200 scratch-aware candidates.
- Both the frozen base configuration and supplementary scratch-prompt configuration are checksummed.

### Approved controlled-300 target

Preserve the six prompt variants, primary seed `2026`, uncertainty seeds
`2026`–`2029`, fixed model settings, exact compositing, checkpoint/resume policy,
and metric-independent selection rules. Build 2,620 primary records, select 815
non-zero cases for the four existing metadata-context arms, select 12 paintings
per visual category across the four canonical non-zero masks for 240 base
uncertainty cases, and complete the two-arm scratch experiment for all 300
paintings. This yields 8,520 records and 8,220 actual model inferences in N11.
The 5,260 approved downstream analysis records exclude the 3,260 exploratory
metadata-context candidates. Notebook 22 remains responsible for the separate
735-candidate damage-size seed extension.

### Controlled-300 completion record

Notebook 11 is complete for `controlled_300`. It produced 8,520 normalized
candidate records and restored RGB PNGs: 2,620 primary candidates, 4,460
prompt-context candidates, and 1,440 uncertainty-extension candidates. The
population contains 8,220 Stable Diffusion inferences and 300 exact identity
controls. All 176 consolidated scientific checks, nine persistence checks, five
manifest-handoff checks, four registry checks, seven final checks, and 23
roadmap and supplemental requirements passed. The output root contains 8,520
restored images and ten canonical non-image artifacts, for 8,530 canonical
files with no remaining work files. The normalized candidate runtime totals
71,737.586 seconds (about 19.93 hours); this is environment-specific evidence,
not a universal speed benchmark.

The read-only pilot comparison root is
`E:/outputs/11_stable_diffusion_restoration/`. All ten pilot non-image paths and
all CSV schemas are retained. Of 1,330 pilot candidate identities, 1,298 remain
in the expanded deterministic design; 1,297 of their restored PNGs are
byte-identical. The sole changed shared PNG is the inherited Notebook 06
`p039` `loss_small` fourth-variant morphology correction. The 32 intentionally
non-retained rows are exploratory p01-p04 prompt-context candidates displaced
when the approved non-metric hash-stratified selection was recomputed over the
full 300-painting population. No primary, formal scratch-pair, or base
uncertainty responsibility was lost. The candidate and prompt-comparison
figures were regenerated from expanded rule-selected evidence.

### Downstream consumers

Notebooks 13–21 and all later analysis/reporting stages.

---

## 12 — SDXL Feasibility or Restoration

**Notebook:** `12_sdxl_feasibility_or_restoration.ipynb`  
**Origin:** Existing Previous Version of Notebook 25, Pre-refactor  
**Controlled-300 refactor status:** Finished\
**Validation status:** Finished\
**Completion gate passed:** Yes\
**Approved target:** 35 predeclared single-seed cases across 30 paintings; seven cases per visual category, with 20 canonical and 15 eligible synthetic cases\
**Output root:** `outputs/12_sdxl_feasibility_or_restoration/`  
**Depends on:** Notebooks 08–11

### Purpose

Produce either a rigorous feasibility result or a fully compatible fourth-model restoration branch.

### Responsibilities

- Record attempted model, revision, precision, resolutions, device, VRAM, memory strategies, runtime, failures, and error messages.
- Distinguish hardware failure from model-quality evidence.
- Use explicit availability states:
  - `full_evaluation_complete`;
  - `partial_evaluation`;
  - `feasibility_only`;
  - `unavailable`;
  - `failed`.
- If suitable compute exists:
  - process the same eligible cases;
  - use the same candidate and prompt policies where methodologically comparable;
  - use repeated seeds;
  - produce normalized candidate records;
  - generate outputs compatible with every unified metric notebook.
- If full evaluation is infeasible:
  - retain a compact feasibility audit;
  - do not create placeholder metric rows;
  - document projected compute requirements.


### Approved bounded partial-evaluation mode

Notebook 12 remains `partial_evaluation`; it does not imply full SDXL coverage.
For `controlled_300`, it expands from the historical ten-case study to a
predeclared balanced 35-case feasibility scope with seven cases per visual
category. The exact mix must preserve meaningful canonical and eligible
synthetic-degradation coverage and be frozen before execution without using
downstream metrics for selection.

The frozen scope retains all ten pilot cases and adds 25 metric-independent
cases. It spans 30 paintings: the five pilot anchors retain two nested cases
each and 25 additional paintings contribute one case each. Every category has
four canonical and three synthetic cases. Canonical coverage is exactly five
cases per mask family; synthetic coverage is four water-stain, four dirt/dust,
four partial-transparency, and three water-stain-plus-dirt cases. The exact IDs
and diversity-first execution order are recorded in
`docs/notebook_12_partial_evaluation_contract.md` and
`config/experiments/sdxl.yaml`.

- Use one primary generic prompt, seed 2026, 768 × 768 inference, and the
  validated generation-quality settings.
- Load the pinned SDXL pipeline once in an isolated persistent batch worker.
- Use the recalculated 25,200-second global budget, 900-second per-case
  watchdog, and 660-second minimum-start reserve derived from the pilot runtime
  evidence and the previous 720-seconds-per-scheduled-case allowance.
- Never retry automatically, fall back to CPU, reduce resolution, or reduce steps.
- Execute in diversity-first order while retaining the original selection rank.
- Threshold canonical missing-region masks at 128 and synthetic effect masks at 13.
- Composite generated pixels only inside the thresholded mask.
- Save every completed image immediately and checkpoint all 35 candidate states
  after every resolved case.
- Represent timeout, CUDA out-of-memory, model unavailability, worker failure,
  and global-budget omissions explicitly; never convert them into quality scores.
- Permit downstream metrics only for rows with `status=completed`,
  `technical_validation_passed=true`, valid 768 x 768 RGB geometry, and zero
  changed pixels outside the binary mask.
- Treat painting as the independent unit; multiple cases from one painting are
  nested observations rather than independent paintings.

The exact case registry, execution order, mask policy, output contract, and
interpretation limits are frozen in
`docs/notebook_12_partial_evaluation_contract.md`.

### Controlled-300 observed result

- All 35 predeclared candidates were resolved across 30 paintings: 24 completed,
  one timed out, and ten were explicitly skipped after the bounded execution
  guard stopped further starts.
- All 24 completed outputs passed RGB 768 x 768 geometry, checksum, exact
  outside-mask preservation, and independent technical validation.
- The ten historical pilot candidates were retained with identical candidate
  IDs, output paths, table schema, completed status, and restored-image bytes.
- The final local output root contains 30 canonical files, 241 passing
  validation rows, five artifact records, and no temporary work files.
- The availability state is `partial_evaluation`; only technically validated
  completed rows are eligible for downstream metric computation.

### Canonical outputs

Full mode:

```text
data/candidates.csv
images/restored/<experiment_id>/<case_id>/<candidate_id>.png
metrics/runtime_summary.csv
```

Feasibility-only mode:

```text
data/feasibility_attempts.csv
reports/feasibility_report.md
```

Universal:

```text
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

### Downstream consumers

Notebooks 13–36, conditional on validated availability state.

---

## 12A — HINT Restoration

**Notebook:** `12a_hint_restoration.ipynb`\
**Origin:** New production notebook selected by Decision Notebook D01\
**Controlled-300 refactor status:** Finished\
**Validation status:** Finished\
**Completion gate passed:** Yes\
**Active validated coverage:** 2,620 completed candidates; 2,320 HINT inferences plus 300 identity controls; 82 validation checks; 2,626 canonical files\
**Output root:** `outputs/12a_hint_restoration/`\
**Depends on:** Notebooks 02 and 08, D01, the pinned official HINT source and
checkpoint, and the controlled-300 HINT configuration

### Purpose

Run HINT as the fourth full-coverage restoration method across all 2,620
restoration-eligible controlled-300 cases. HINT contributes a second
deterministic learned architecture with mask-aware transformer processing and
long-range context; it is not a continuation of D01's 12-case pilot.

### Responsibilities

- Preserve the D01-validated official source revision, Places2 checkpoint,
  native 768 × 768 adapter, mask convention, exact-mask compositing, and
  outside-mask invariance policy.
- Consume only N08 cases marked HINT-eligible; include the 300 zero controls and
  the complete nonzero eligible population.
- Produce exactly one deterministic primary candidate per eligible case.
- Load the model efficiently, checkpoint after bounded intervals, print progress
  at least every ten cases, and support checksum-aware resume.
- Record model/checkpoint identity, device, precision, load time, inference time,
  peak GPU memory, status, and actionable failure details.
- Validate image readability, RGB 768 × 768 geometry, exact case coverage,
  candidate uniqueness, zero-control identity, and outside-mask invariance.
- Preserve normalized candidate and runtime schemas compatible with N13–N21 and
  the downstream reports/dashboard.

### Approved batch structure

1. Contract, initialization, dependency and external-asset preflight.
2. Normalized input loading, exact 2,620-case worklist construction, path
   validation and checksum materialization.
3. One inference case plus one zero-control smoke test, including deterministic
   repeatability and exact outside-mask preservation.
4. Guarded full execution in an isolated worker, with ten-case progress,
   ten-case atomic checkpoints, checksum-aware resume and an eight-hour upper
   process budget.
5. Canonical restoration-table assembly and experiment-level runtime summary.
6. Scientific and technical validation plus the representative restoration
   figure.
7. Canonical persistence and strict reload validation.
8. Manifests, cleanup, final completion gate and roadmap traceability.

### Canonical outputs

```text
data/restorations.csv
images/restored/<experiment_id>/<case_id>.png
metrics/runtime_summary.csv
figures/restoration_examples.png
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

### Validation gate

- Exactly 2,620 eligible cases are resolved with explicit completed or failed
  states; the completion gate requires no unresolved blocking failure.
- Candidate IDs and case foreign keys are unique and complete.
- Every completed output reloads as RGB 768 × 768 and changes no pixel outside
  the permitted mask.
- All 300 zero controls are identity-preserving.
- Runtime/checkpoint records reconcile with candidates and files on disk.

### Observed controlled-300 completion

- All 2,620 eligible cases completed: 1,500 canonical, 245 damage-size, 525
  mask-robustness and 350 eligible synthetic-degradation candidates.
- The run contains 2,320 HINT inferences and 300 exact identity controls.
- All 82 consolidated checks passed; five artifacts were registered, all 2,620
  restored PNGs exist, and the completed output tree contains 2,626 files with
  no remaining work files.
- The normalized runtime table records 16,025.750 seconds of allocated work
  (about 4.45 hours), within the approved 4–6 hour planning range.
- N12A is a new production stage, so no historical N12A output counterpart
  exists at `E:/outputs/`. D01 is the method-selection baseline: the official
  HINT revision, Places2 checkpoint, native 768 × 768 adapter, compositing
  policy and technical invariants were preserved without unexplained loss.

### Downstream consumers

Notebooks 13–21 and 23–36.

---

# Unified Evidence Generation

## 13 — Classical Metrics

**Notebook:** `13_classical_metrics.ipynb`  
**Origin:** Consolidates Existing Notebooks 09, 15, and 22  
**Controlled-300 refactor status:** Finished

**Validation status:** Finished

**Completion gate passed:** Yes

**Active validated coverage:** 2,620 cases; 16,404 candidates across five methods; 477,753 metric rows; 262 validation checks

**Pilot comparison:** All six pilot output paths and schemas retained; candidate coverage increased from 2,160 to 16,404 and metric rows from 63,018 to 477,753 without unexplained loss
**Output root:** `outputs/13_classical_metrics/`  
**Depends on:** Notebook 02 geometry handoff and Notebooks 08–12A

### Purpose

Compute one standardized classical full-reference evidence table for all available models and candidates.

### Responsibilities

- Compute MSE, MAE, PSNR, and SSIM.
- Compare clean versus damaged and clean versus restored.
- Compute direction-aware restoration improvements.
- Apply only mathematically valid regions.
- Support full image, content region, exact mask, mask crop, boundary bands/rings, and outside-mask regions as valid per metric.
- Use Notebook 02 content geometry through the normalized preprocessing handoff; do not infer content bounds from image padding.
- Exclude `patch_window` here; sliding-window evidence is deferred to later local and semantic analyses.
- Reject sparse masked-pixel SSIM.
- Retain zero-control evidence.
- Record metric definitions, direction, region, version, limitations, and missing-value policy.
- Preserve infinities and missing values through explicit policies.
- Validate expected case/candidate/region row counts.
- Support all experiment and dataset scopes.
- Generate compact model/region QA plots without persisting every grouping.

### Observed controlled-300 completion

- The canonical table contains 477,753 validated rows: 143,247 each for MSE,
  MAE, and PSNR, plus 48,012 SSIM rows.
- Evidence covers 16,404 candidates across 2,620 cases: 2,620 each for Telea,
  LaMa, and HINT; 8,520 Stable Diffusion candidates; and 24 technically valid
  SDXL candidates from the bounded 35-case attempt.
- All 1,200 zero-control candidates and their 13,200 metric rows are retained.
  Intentional exact-match PSNR infinities remain explicit, while no negative
  infinity or unexpected numerical missingness is present.
- All 262 consolidated checks passed, the two canonical figures are valid and
  nonblank, four downstream artifacts are registered, and no temporary work
  file remains.
- Batch 4 completed in 28,705.153 seconds (about 7 h 58 m), below the
  conservative 18–30 hour planning range. This remains machine- and
  environment-specific runtime evidence.
- The read-only pilot comparison root is `E:/outputs/13_classical_metrics/`.
  Both runs contain the same six canonical relative paths and preserve
  `classical_metrics.v1`, the two figure schemas, and
  `validation_checks.v1`. Population growth fully explains the increased row
  counts; no pilot artifact class or responsibility was lost.

### Canonical outputs

```text
metrics/classical_metrics.csv
figures/classical_metric_distributions.png
figures/classical_improvement_by_region.png
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

### Downstream consumers

Notebooks 14, 16, 17, 21, 23–36, D02, and other explicitly registered
metric-consuming stages.

---

## 14 — LPIPS Metrics

**Notebook:** `14_lpips_metrics.ipynb`  
**Origin:** Consolidates Existing Notebooks 11, 17, and 24  
**Controlled-300 refactor status:** Finished

**Validation status:** Finished

**Completion gate passed:** Yes

**Active validated coverage:** 2,620 cases; 16,404 candidates across five methods; 31,608 LPIPS rows; 261/261 validation checks

**Pilot comparison:** All five pilot output paths and CSV schemas retained; candidate coverage increased from 2,160 to 16,404 and LPIPS rows from 4,170 to 31,608; 64 non-retained pilot rows are the two-region evidence for the 32 exploratory Stable Diffusion prompt-context candidates deliberately displaced in Notebook 11
**Output root:** `outputs/14_lpips_metrics/`  
**Depends on:** Notebook 02 geometry handoff and Notebooks 08–12A

### Responsibilities

- Compute LPIPS on spatially meaningful image-like regions.
- Support content region and mask-bounding-box crop.
- Add other regions only when methodologically valid.
- Never apply LPIPS to unordered sparse pixels.
- Compare damaged and restored images with clean references.
- Compute restoration improvement.
- Record network, package version, input size, device, region, runtime, and schema version.
- Support candidates and all eligible experiments.
- Validate expected rows and finite-value policies.
- Produce compact diagnostic plots.

### Observed controlled-300 completion

- The canonical `lpips_metrics.v1` table contains 31,608 validated rows for
  16,404 candidates across 2,620 cases.
- Model coverage is 4,940 rows each for OpenCV Telea, LaMa, and HINT; 16,740
  rows for Stable Diffusion; and 48 rows for the 24 technically valid SDXL
  candidates.
- Region coverage is 16,404 `content_region` rows and 15,204
  `mask_bbox_crop` rows. All 1,200 zero-control candidates are retained as
  exact content-region evidence.
- The 300-painting scratch-prompt ablation retains 2,400 matched
  case-seed-region pairs. Its direction remains descriptive and does not
  affect candidate inclusion or validation success.
- All 261 consolidated checks pass, all three registered artifact checksums
  agree, the five-file canonical output contract is exact, and no temporary
  work file remains.
- Full checkpointed LPIPS execution took 3,341.795 seconds (about 55.7
  minutes) on the recorded RTX 3060 laptop environment, within the approved
  planning ceiling.
- The read-only pilot comparison root is `E:/outputs/14_lpips_metrics/`. Both
  runs contain the same five canonical relative paths and preserve all CSV
  schemas. Metric rows increased from 4,170 to 31,608 and validation rows from
  253 to 261. Of 4,170 pilot metric identities, 4,106 remain in the expanded
  design; the other 64 belong exclusively to the 32 exploratory Stable
  Diffusion context candidates intentionally displaced by Notebook 11's
  approved expanded hash-stratified selection. No artifact class, primary
  candidate responsibility, formal scratch pair, or bounded SDXL evidence was
  lost.

### Canonical outputs

```text
metrics/lpips_metrics.csv
figures/lpips_distributions.png
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## 15 — Feature Similarity

**Notebook:** `15_feature_similarity.ipynb`  
**Origin:** Consolidates Existing Notebooks 12, 18, and 25  
**Refactor status:** Finished\
**Validation status:** Finished with one declared non-blocking CUDA repeatability warning\
**Completion gate passed:** Yes\
**Planned controlled-300 coverage:** 2,620 cases; 16,404 candidates across five methods; 31,608 candidate-region evaluations; 63,216 feature-metric rows; 78,336 retained embeddings  
**Observed controlled-300 coverage:** 2,620 cases; 16,404 candidates across five methods; 31,608 candidate-region evaluations; 63,216 feature-metric rows; 78,336 retained embeddings; 247 validation checks; 0 blocking failures; 1 warning failure; 7 canonical files; 5 registered artifacts\
**Output root:** `outputs/15_feature_similarity/`  
**Depends on:** Notebook 02 geometry handoff and Notebooks 08–12A

### Responsibilities

- Compute CLIP and DINOv2 similarity.
- Use content and mask-crop regions.
- Compare damaged/restored representations with clean references.
- Compute similarity improvements.
- Record exact model names, revisions, preprocessing, input size, device, and package versions.
- Retain reusable embeddings for grouped analysis, semantic localization, and example retrieval.
- Deduplicate clean and damaged embeddings where possible.
- Create an embedding manifest rather than embedding arrays in CSV.
- Treat CLIP and DINOv2 as diagnostic, non-conservation-specific models.
- Validate candidate, region, metric, and embedding coverage.

### Canonical outputs

```text
metrics/feature_metrics.csv
data/embeddings.npz
manifests/embeddings.csv
figures/feature_similarity_distributions.png
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

### Controlled-50 continuity and storage result

The active output root and the read-only pilot copy at
`E:/outputs/15_feature_similarity/` contain the same seven canonical relative
paths and preserve the metric, embedding-manifest, validation, and artifact
schemas. Feature-metric rows increased from 8,340 to 63,216 (7.58×), while
embedding rows increased from 10,700 to 78,336 (7.32×). Of the shared metric
identities, 8,212 are retained. The 128 displaced pilot identities are the
expected records associated with Notebook 11's 32 approved contextual-candidate
replacements. Twelve non-bit-identical shared rows inherit Notebook 06's
documented `p039` morphology correction; six further differences are only
`1.19209289550781e-07`, consistent with the declared best-effort CUDA floating
variation. No unexplained evidence family or artifact class is missing.

The 111.9 MB `data/embeddings.npz` bundle exceeds the approved 50 MiB
bulk-diagnostic threshold. It remains the local Notebook 15 source of truth and
is classified for checksum-verified publication in the Hugging Face diagnostics
repository. The compact tables, figure, validation evidence, manifests,
notebook, and publication registry remain in the GitHub scientific record.

---

## 16 — Difference Maps and Spatial Diagnostics

**Notebook:** `16_difference_maps_and_spatial_diagnostics.ipynb`  
**Origin:** Consolidates Existing Notebooks 10, 16, and 23  
**Refactor status:** Finished\
**Validation status:** Finished\
**Completion gate passed:** Yes\
**Observed controlled-300 coverage:** 2,620 cases; 16,404 candidates across five methods; 15,204 nonzero candidates; 143,247 spatial-diagnostic rows; 76,020 candidate maps; 14 selected panels; 76,034 map-manifest rows\
**Output root:** `outputs/16_difference_maps_and_spatial_diagnostics/`  
**Depends on:** Notebooks 02 and 08–13, including Notebook 12A

**Publication status:** Local completion is validated, and the separately
approved full indexed-bundle N16 release is remotely verified at the pinned
revision and record named in Section 2.1. All maps and the large metrics table
remain locally canonical; the compact Git record is a separate handoff. Storage
and dashboard access are still reassessed after N33 and before N34. Do not
delete the local map collection.

### Responsibilities

- Generate clean-versus-damaged absolute-error maps.
- Generate clean-versus-restored absolute-error maps.
- Generate signed restoration-improvement maps.
- Generate masked signed-improvement maps.
- Summarize maps over valid regions.
- Use standardized and explicitly documented colour scales.
- Add mask overlays.
- Add content-box and mask-box overlays.
- Add inner/outer/symmetric boundary overlays.
- Add outside-mask spillover diagnostics.
- Use one canonical region implementation.
- Separate QA-only indicators from final trustworthiness flags.
- Save scalable map images for downstream XAI and case reports.
- Render rule-selected representative panels.

### Canonical outputs

```text
metrics/spatial_diagnostics.csv
images/maps/<model_id>/<map_id>/<map_type>.png
figures/selected_spatial_panels/
manifests/map_images.csv
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## 17 — Local Consistency Metrics

**Notebook:** `17_local_consistency_metrics.ipynb`  
**Origin:** Existing Previous Version of Notebook 31, Pre-refactor, expanded with colour and seam requirements  
**Refactor status:** Finished\
**Validation status:** Finished\
**Completion gate passed:** Yes\
**Output root:** `outputs/17_local_consistency_metrics/`  
**Depends on:** Notebooks 08–12A and canonical regions

**Controlled-300 scaling status:** Local run validated, indexed-bundle diagnostics release remotely verified, and compact Git record committed. Complete evidence remains locally canonical.

**Publication status:** The complete indexed-bundle N17 release passed remote
verification at the pinned diagnostics revision and record in Section 2.1.
Keep all 27,912 candidate-map PNGs and the large metrics table locally under
Notebook 17 ownership as well. Selectable case-level colour, seam, and texture
evidence remains a requirement for the later dashboard. The verified bundle
transport is a candidate backend, not a final N34/N35 deployment decision;
that access contract is approved after N33 and before N34.

**Expected execution time:** Batch 4 metric computation is the dominant stage at approximately 18–22 hours on the validated local machine; Batch 5 map generation is expected to require approximately 11–14 hours. Both stages are checkpointed and resumable.

### Texture responsibilities

- Compute Local Binary Pattern descriptors.
- Compute Gabor response descriptors.
- Retain useful existing GLCM evidence if validated.
- Compute local texture distance.
- Compare clean, damaged, and restored mask crops.
- Compute restoration improvement relative to damaged input.
- Evaluate boundary texture consistency.
- Detect excessive smoothing.
- Detect repeated texture where defensible.
- Detect texture discontinuity and texture hallucination proxies.
- Retain brushstroke-proxy gradient, edge/detail density, orientation coherence, and orientation-histogram diagnostics.
- State explicitly that brushstroke proxies are not authentication or semantic recognition.
- Summarize by model, style/category, damage type, percentage, and experiment.

### Colour responsibilities

- Convert using a documented colour-space policy.
- Compute CIELAB differences and ΔE summary statistics.
- Prefer a documented CIEDE2000-compatible method where feasible.
- Compute mean, median, and high-percentile colour drift.
- Compute masked-region and mask-crop colour error.
- Compute boundary colour discontinuity.
- Compute histogram distance.
- Compute hue and chroma shifts.
- Compute channel-distribution differences.
- Compute restored-versus-clean improvement relative to damaged input.
- Distinguish reconstruction colour error, boundary transition error, and global spillover.
- Analyze inside-mask, boundary, and outside-mask support.

### Seam and boundary responsibilities

- Use inner boundary bands.
- Use outer boundary bands.
- Use symmetric boundary rings.
- Compute luminance discontinuity.
- Compute colour discontinuity.
- Compute gradient mismatch.
- Compute edge-orientation mismatch.
- Compute local structural difference and valid local SSIM.
- Compute transition smoothness and boundary spillover.
- Produce visible-seam severity evidence without claiming a universal perceptual threshold.
- Keep seam evidence distinct from uncertainty boundary evidence.

### Canonical outputs

```text
metrics/local_consistency.csv
images/maps/<model_id>/<case_id>/texture.png
images/maps/<model_id>/<case_id>/colour.png
images/maps/<model_id>/<case_id>/seam.png
figures/local_consistency_summary.png
figures/selected_local_consistency_panels/
manifests/map_images.csv
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

### Controlled-300 execution contract

- Evaluate 16,404 completed candidates across 2,620 unique cases: 2,620 each for OpenCV Telea, LaMa, HINT, and the primary Stable Diffusion comparison scope; additional Stable Diffusion prompt/seed candidates; and 24 completed SDXL feasibility candidates.
- Retain numeric local-consistency evidence for 15,204 non-zero candidates and 1,200 zero controls.
- Produce 2,060,667 normalized metric rows: 497,772 texture rows, 1,289,223 colour rows, and 273,672 seam rows.
- Restrict canonical map generation to 9,304 non-zero primary candidates, yielding 27,912 candidate-map PNGs.
- Render ten candidate-level review panels and four cross-model panels, yielding 27,926 final map-manifest rows.
- Treat HINT as a full comparison method and retain SDXL as a bounded 24-completion result from its declared 35-case attempt.

The completed run has 2,060,667 metric rows, 27,912 candidate maps, 14
selected panels, 27,926 map-manifest rows, and 179/179 passing validation
checks, with no temporary work files. All 3,282 pilot map-manifest paths are
retained. Their presentation PNG hashes differ because the declared global
texture, colour, and seam display scales were recomputed over the expanded
candidate population; numeric measurements remain in the canonical CSV.
Compared with the pilot, metric rows rose from 271,988 to 2,060,667 and
candidate maps from 3,270 to 27,912. Bulk maps and metrics remain locally
canonical and have a verified indexed-bundle diagnostics copy. The pre-N34
review governs dashboard access, not preservation of this release.

### Downstream consumers

Notebooks 19–36.

---

## 18 — Diffusion Uncertainty Analysis

**Notebook:** `18_diffusion_uncertainty_analysis.ipynb`  
**Origin:** Existing Previous Version of Notebook 27, Pre-refactor  
**Output root:** `outputs/18_diffusion_uncertainty_analysis/`  
**Depends on:** Notebooks 01, 02, 08, 11, 13–15, and 17; Notebook 12 for seed-coverage applicability

**Refactor status:** Finished\
**Validation status:** Finished\
**Completion gate passed:** Yes\
**Controlled-300 scaling status:** Local execution complete and validated; compact Git handoff pending.

**Observed execution time:** The recorded N18 run completed in about 39 minutes
(2026-09-17 22:40–23:19 UTC). A future rerun still needs measured progress
for its ETA; this elapsed time is not a guarantee.

### Purpose

Measure empirical repeated-seed variability for 780 prompt-specific Stable
Diffusion groups: 480 generic and 300 scratch-aware groups across 480 canonical
cases, with 3,120 candidates and 4,680 unique unordered seed pairs. Each group
contains exactly seeds 2026–2029 with a fixed case, prompt, and configuration.

Notebook 22 owns the separate damage-size uncertainty population. SDXL has only
one seed per case and is excluded from repeated-seed analysis. Mask robustness
and synthetic-degradation cases do not acquire seed uncertainty by association.

### Responsibilities

- Consume repeated-seed candidates; do not run model inference here.
- Validate required seed coverage.
- Compute candidate-to-candidate image variation.
- Compute per-pixel variability.
- Compute RGB variation over full image, content region, masked region, mask crop, boundary ring, and outside-mask content.
- Compute pairwise LPIPS variation.
- Compute pairwise CLIP and DINOv2 variation.
- Record seed-level reference metrics.
- Retain LPIPS, CLIP, and DINOv2 pairwise evidence only for contiguous content and mask-crop regions.
- Retain transparent component metrics; no combined uncertainty index is constructed.
- Summarize the eligible canonical population by damage type, realized damage fraction, category, prompt arm, and seed coverage without inferring independent style effects.
- Prepare the 780-row calibration-input table by joining seed-level reference, perceptual, feature, texture, colour, and seam evidence. This is an association-ready table, not fitted confidence calibration.
- Leave semantic evidence and computational-flag associations to their downstream producers and consumers; Notebook 18 does not compute expert ratings or failure labels.
- State that uncertainty is an empirical proxy, not calibrated confidence.
- State that low uncertainty does not prove correctness.
- For deterministic models, reserve “uncertainty” for diffusion; use robustness/sensitivity terminology elsewhere.

### Controlled-300 execution contract

- Use the 480 canonical cases that have complete four-seed Stable Diffusion coverage; keep generic and scratch-aware prompt groups separate.
- Produce 9,360 per-group RGB-variability rows, 56,160 pairwise RGB rows, 9,360 pairwise LPIPS rows, 18,720 pairwise CLIP/DINOv2 rows, and 31,200 seed-reference rows: 124,800 normalized uncertainty-evidence rows total.
- Keep the 35-case SDXL attempt and its 24 completions outside repeated-seed uncertainty because each completed case has only one seed.
- Produce two canonical figures and no persisted heatmaps; Notebook 19 owns spatial uncertainty maps.

The completed run produced 124,800 uncertainty rows, 780 calibration rows,
two readable figures, seven canonical files and 150/150 passing checks, with
no notebook error output or temporary work files. The pilot E: baseline had
the same seven artifact types but 20,800 metric rows and 130 calibration rows;
both table populations scaled exactly sixfold. This producer has no map/image
explosion: its largest file is an approximately 81 MB CSV already tracked by
Git LFS. Keep this bounded seven-file N18 output in its Git handoff; no
separate Hugging Face publication is needed for N18.

### Canonical outputs

```text
metrics/uncertainty_metrics.csv
metrics/uncertainty_calibration_inputs.csv
figures/uncertainty_distributions.png
figures/uncertainty_vs_performance.png
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## 19 — Uncertainty and Spatial Explanation Maps

**Notebook:** `19_uncertainty_and_spatial_explanation_maps.ipynb`  
**Origin:** Existing Previous Version of Notebook 32, Pre-refactor, expanded  
**Output root:** `outputs/19_uncertainty_and_spatial_explanation_maps/`  
**Depends on:** Notebooks 01, 02, 08, 11, and 16–18

**Controlled-300 execution estimate:** The 130-group pilot took about 3.4
hours end to end. With 780 groups, use roughly **18–24 hours** as an initial
whole-notebook planning range, not a promise or per-batch limit; derive a new
ETA from the first 50 completed groups and rendered assets. The 2,481 expected
canonical files include 780 uncertainty images, 780 overlays, 900 owned
scratch-aware local-component maps and 15 selected panels. The 6,255-row
manifest additionally links upstream maps without copying them. If the final
archive/images are too large for the compact Git handoff, use the verified
N16/N17 indexed-bundle diagnostics strategy after local validation.

### Responsibilities

- Generate per-pixel diffusion uncertainty heatmaps for every eligible case.
- Generate full-image, masked-region, crop, boundary, and outside-mask heatmap variants.
- Use consistent normalization policies and record their scope.
- Retain all 780 prompt-specific raw numeric uncertainty maps in the canonical compressed archive.
- Produce visual heatmaps and image overlays.
- Integrate texture-inconsistency maps.
- Integrate colour-drift maps.
- Integrate seam maps.
- Integrate absolute-error and signed-improvement maps.
- Add mask, content-box, mask-box, and boundary overlays.
- Create combined diagnostic panels without collapsing evidence into one score.
- Record map provenance, scale parameters, image paths, and completeness.
- Validate image and metadata coverage.
- Select representative maps through auditable rules.
- Prepare assets for semantic/XAI analysis, flags, case reports, and dashboard use.

### Implementation-contract clarifications

- The spatial population preserves Notebook 18's 780 prompt-specific uncertainty
  groups. Because generic and scratch-aware groups can share a `case_id`, owned
  map filenames use `uncertainty_group_id` to prevent collisions while the map
  manifest retains both identifiers.
- The per-pixel uncertainty definition is the mean RGB-channel population
  standard deviation across seeds and must reproduce Notebook 18's regional
  scalar summaries within the declared tolerance.
- One global robust visualization scale is shared across all eligible groups and
  all regional views. Numeric map values are retained separately from visually
  clipped PNG assets.
- Validated Notebook 16 and 17 component maps are linked rather than copied.
  Scratch-aware texture, colour, and seam presentation maps absent from Notebook
  17 may be rendered with the same approved helper, configuration, and global
  scales without introducing new metrics.
- Notebook 19 does not generate a standalone report. Its canonical figures and
  normalized manifests are downstream assets for later semantic, flagging,
  reporting, case-page, and dashboard stages.

### Canonical outputs

```text
metrics/spatial_explanations.csv
data/uncertainty_maps.npz
images/uncertainty/stable_diffusion_inpainting/
images/overlays/stable_diffusion_inpainting/
images/integrated_local/stable_diffusion_inpainting/
figures/selected_explanation_panels/
manifests/map_images.csv
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

### Controlled-300 completion and pilot-output comparison

The saved notebook has no error outputs; the run manifest records `completed`,
`passed`, and a passed completion gate. All 149 validation rows pass. The final
map audit checked 5,476 distinct referenced files, including upstream links,
with zero missing paths or checksum failures. The 20 roadmap checks pass, and
the temporary work directory is absent. Two inspected selected panels show
the intended uncertainty, geometry, error/improvement, and local-consistency
evidence without collapsing it into one score.

| Output family | E: pilot | Controlled-300 | Comparison |
|---|---:|---:|---|
| Numeric uncertainty maps (`uncertainty_maps.npz`) | 130 | 780 | All 130 shared arrays are byte-equivalent after loading; 650 new groups. |
| Regional spatial metrics | 780 rows | 4,680 rows | Same 47 columns; all 780 shared regional means are exactly equal. |
| Uncertainty panels | 130 PNGs | 780 PNGs | Same role; global normalization was recomputed for the expanded population. |
| Geometry/restoration overlays | 130 PNGs | 780 PNGs | Same role; global normalization was recomputed. |
| Scratch-aware texture/colour/seam maps | 150 PNGs | 900 PNGs | Same three map types; N17-derived global presentation scales changed. |
| Rule-selected explanation panels | 15 PNGs | 15 PNGs | Same five-per-role/three-per-category contract; 14 pilot-only filenames were replaced by expanded-cohort selections. |
| Normalized map manifest | 1,055 rows | 6,255 rows | Same 34 columns; 3,255 owned records plus 3,000 upstream links. |
| Artifact manifest | 8 rows | 8 rows | Same 15 columns and artifact roles. |
| Validation and run manifest | 149 rows + 1 JSON | 149 rows + 1 JSON | Same validation schema; all new checks pass. |
| Complete canonical root | 431 files | 2,481 files | +2,050 files from expanded owned PNG population; no artifact family lost. |

All 411 shared PNG paths differ at the byte level because the image rendering
uses new globally estimated colour/uncertainty limits or the selected-panel
layout and evidence population. This is not a change in the underlying shared
numeric maps: the 130 shared archive arrays are identical, and all 780 shared
regional means are identical. The E: copy remains read-only.

---

## 20 — Semantic and Structural Consistency

**Notebook:** `20_semantic_and_structural_consistency.ipynb`  
**Origin:** New Notebook  
**Output root:** `outputs/20_semantic_and_structural_consistency/`  
**Depends on:** Notebooks 01, 02, 08–12, 12A, and 15–19

### Responsibilities

- Measure reference-relative local feature and structural consistency as diagnostic proxies for content and composition preservation.
- Localize feature disagreement for visual inspection without claiming detection of new objects, faces, anatomical errors, or hallucinations.
- Use category-conditioned interpretation without claiming artist, style, or authentic-brushwork recognition.
- Measure alteration of unmasked context where the encoder grid supports it.
- Compute patch-level DINOv2 similarity.
- Compute patch-level CLIP similarity where methodologically useful.
- Implement sliding-window/local feature comparison.
- Add local embedding maps.
- Retain reference-derived feature-affinity maps as a labelled saliency proxy, not an occlusion or causal explanation.
- Use structural-layout comparison where defensible.
- Record applicability by artwork/category and region; do not imply that facial/anatomical detectors were executed.
- State limitations of pretrained non-conservation-specific models.
- Produce machine-readable semantic evidence for later flags rather than assigning final flags here.

### Implementation-contract clarifications

- Retain semantic and structural metrics for all 16,404 completed candidates,
  including zero controls, HINT, Stable Diffusion prompt/seed candidates, and
  the explicitly bounded 24-completion SDXL scope.
- Extract aligned local CLIP and DINOv2 token grids from the canonical
  `content_region` and `mask_bbox_crop`. Use reference-derived local similarity,
  feature-affinity, layout, covariance, and cross-encoder-agreement evidence as
  transparent diagnostic components; do not collapse them into a semantic or
  trustworthiness score.
- Use category-conditioned interpretation scopes for portrait/figure,
  architecture, landscape, abstraction/surrealism, and high-texture/brushwork
  works. These scopes do not assert that a face, anatomy, object, architecture,
  artist, style, or authentic brushwork was detected.
- Do not introduce a photographic face-landmark or object detector without a
  separately validated painting-domain contract. Occlusion sensitivity is not
  applicable without a stable semantic prediction target; reference-derived
  DINOv2 feature affinity may be retained only as a labelled saliency proxy.
- Retain unclipped numerical local-map bundles in a compressed archive for
  downstream flagging and XAI. Render PNG panels for all 9,304 nonzero
  primary comparison candidates; do not cut approved coverage for size.
- Use `candidate_id`, rather than `case_id`, as the owned map filename identity
  because Stable Diffusion contains multiple candidates for the same case.
- Notebook 20 produces machine-readable evidence and selected visualizations;
  it does not generate a standalone report.

### Controlled-300 completion record

- Completion gate passed with 181/181 validation checks, zero blocking
  failures, and zero warning failures.
- The evaluated population contains 16,404 candidates across 2,620 cases and
  five methods.
- Canonical evidence contains 447,312 metric rows, 63,216 numeric-map bundles,
  9,304 rendered semantic panels, 72,520 map-manifest rows, one 15-case
  representative figure, six artifact records, and 9,311 files.
- All eight pilot artifact paths and all CSV schemas are retained. Metrics
  increased from 58,980 to 447,312, numeric bundles from 8,340 to 63,216,
  rendered panels from 1,090 to 9,304, map-manifest rows from 9,430 to 72,520,
  and validation rows from 177 to 181.
- Complete local evidence remains authoritative. Bulk diagnostics use the
  established indexed-bundle workflow in the Hugging Face diagnostics dataset;
  Git retains the compact scientific handoff and pinned publication record.

### Canonical outputs

```text
metrics/semantic_structural_metrics.csv
data/semantic_maps.npz
images/maps/<model_id>/<candidate_id>/semantic.png
figures/semantic_examples.png
manifests/semantic_maps.csv
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

# Comparative and Focused Analysis

## 21 — Multi-Model Comparison

**Notebook:** `21_multi_model_comparison.ipynb`  
**Origin:** Consolidates Existing Notebook 27 and previous pairwise comparison notebooks 20 and 24  
**Output root:** `outputs/21_multi_model_comparison/`  
**Depends on:** Notebooks 09–20

### Responsibilities

- Compare OpenCV Telea, LaMa, HINT and Stable Diffusion as four full methods;
  present validated SDXL results separately as bounded feasibility evidence.
- Determine availability from validated manifests.
- Apply a documented non-metric candidate-selection policy for diffusion baseline comparison.
- Compare paired identical cases.
- Compare every metric family.
- Compare by style/category, damage type, percentage, degradation type, and experiment.
- Compare runtime and compute.
- Compare deterministic and generative failure patterns.
- Compute direction-aware winners by metric.
- Retain metric disagreement.
- Analyze classical versus LPIPS, feature, texture, colour, seam, semantic, and uncertainty divergence.
- Prepare ranking-stability evidence.
- Use majority voting only as a compact diagnostic.
- Never describe a vote as conservation truth.
- Select representative disagreement and success/failure cases through explicit rules.

### Approved comparison and reporting contract

- The full-scope paired comparison contains 2,620 identical cases for
  OpenCV Telea, LaMa, HINT and Stable Diffusion: 10,480 selected candidates.
- The SDXL comparison is a separate subset of its 24 technically completed
  cases; SDXL must never be presented as full-dataset evidence.
- Candidate selection is metric-independent. OpenCV, LaMa and HINT contribute their
  sole completed candidate; Stable Diffusion contributes only its completed
  generic `execution_role == "primary"` candidate; SDXL contributes its ten
  completed technically validated primary candidates. Prompt-ablation and
  repeated-seed candidates remain contextual evidence and cannot replace or
  overweight the baseline.
- Stable Diffusion uncertainty comprises 480 generic and 300 scratch-aware
  prompt-specific groups. It is model-specific contextual evidence, not a
  cross-model ranking dimension. Deterministic models and single-seed SDXL do
  not receive artificial uncertainty values.
- Direction-aware comparisons retain all declared evidence families. Metric
  disagreement uses predeclared anchors and a family-balanced diagnostic vote;
  families with many correlated metrics do not receive additional voting weight.
  Runtime and uncertainty are excluded from quality voting. No combined quality
  or trustworthiness score is retained.
- Ranking stability uses deterministic leave-one-painting-out analysis so the
  nested 2,620-case, 300-painting design is not treated as 2,620 independent artworks.
- The standalone report is structured around the proposal research questions
  and approved roadmap extensions. It must provide scoped section-level
  conclusions and a balanced mixture of paragraphs, finding bullets, tables,
  metrics, analytical plots, restoration grids, crops, uncertainty or semantic
  diagnostics, limitations, and thesis-level synthesis.
- The report is self-contained when downloaded alone. It embeds web-sized copies
  of every required figure and representative image, includes all 24 completed SDXL case
  panels, uses a substantial auditable core-case and diagnostic visual atlas, and
  may embed additional presentation-only views beyond the two separately saved
  canonical figures.
- Computational winners remain evidence-defined results. They are not historical
  authenticity findings, physical-treatment recommendations, museum approval,
  or substitutes for conservator judgement.

### Canonical outputs

```text
metrics/model_comparison.csv
metrics/metric_disagreement.csv
data/representative_cases.csv
figures/model_comparison.png
figures/metric_disagreement.png
reports/multi_model_comparison.html
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## D02 — Portrait Skin-Tone and Hand Restoration Audit

**Notebook:** `d02_portrait_skin_tone_and_hand_restoration_audit.ipynb`\
**Origin:** New approved supplemental analysis arising from supervisor feedback\
**Refactor status:** Not started\
**Validation status:** Not started\
**Completion gate passed:** No\
**Output root:** `outputs/d02_portrait_skin_tone_and_hand_restoration_audit/`\
**Depends on:** Notebooks 01–21, including the full-benchmark HINT producer in Notebook 12A

### Placement and execution boundary

D02 is an approved decision/analysis notebook outside the numbered production
sequence. It preserves the Notebook 01–36 numbering in the same way that D01
preserves the completed HINT-versus-MAT selection evidence. Its contract is
frozen during the Controlled-300 rerun, but it must not execute until Notebook
21 has completed, passed its gate, and been committed. The execution order is:

```text
Notebooks 01–21
D02 portrait audit
Notebooks 22–36
```

D02 must not reopen or alter the registered populations, masks, damaged images,
restorations, metrics, or outputs owned by Notebooks 01–21. Its default design
is analysis-only: first determine whether saved evidence provides adequate
anatomical overlap, then analyze only eligible existing cases. New targeted
masks or restoration inference are a fallback that requires a separate explicit
approval after the feasibility gate fails.

### Purpose and study priority

D02 addresses two related supervisor suggestions through one shared portrait
screening and anatomical-annotation layer while keeping their analyses and
conclusions separate:

1. **Primary study — hand-restoration difficulty:** test whether the evaluated
   methods reconstruct damaged hands less faithfully than closely matched
   damaged non-hand regions from the same painting and case.
2. **Secondary study — depicted-skin-tone audit:** explore whether local
   restoration evidence changes with the rendered lightness of annotated skin
   regions in this controlled portrait collection.

The hand study is the stronger and more defensible planned contribution. The
skin-tone study is exploratory because the available paintings differ in
collection source, period, medium, palette, scale, pose, lighting, and stylistic
convention. It is not a racial-bias benchmark.

### Approved evidence population and existing assets

- Screen all 60 `portrait_figure` paintings: the original `p001`–`p010` cohort
  and the added `p251`–`p300` cohort.
- Load normalized clean references from
  `outputs/02_image_preprocessing/images/clean/`.
- Load canonical masks from
  `outputs/03_canonical_mask_generation/images/masks/<painting_id>/` and
  canonical damaged images from
  `outputs/04_canonical_damaged_image_generation/images/damaged/<painting_id>/`.
- Consider Notebook 05 damage-size cases and Notebook 06 mask-robustness
  variants only after the canonical audit and only when they add relevant,
  adequately intersecting anatomical evidence.
- Treat Notebook 07 degradation cases as supplementary diagnostics rather than
  the primary anatomy-restoration population. Global or non-removal effects do
  not become inpainting tasks merely because a person is visible.
- Join eligible cases to the completed candidates and evidence owned by
  Notebooks 09–21. The primary common-method comparison covers OpenCV Telea,
  LaMa, HINT, and Stable Diffusion. Stable Diffusion seeds remain nested repeated
  observations. SDXL may appear only as descriptive evidence when an exact
  eligible case already belongs to its bounded declared population.

The focused Notebook 05–07 cohort contains seven portraits:
`p001`, `p009`, `p256`, `p259`, `p267`, `p284`, and `p294`. All show people and
visible hands, although hand scale, visibility, and damage overlap differ.

### Preliminary visually shortlisted canonical cases

The following cases were visually screened after Notebook 08. They establish
that matching damaged images already exist, but they are not final analytical
eligibility decisions. D02 must confirm exact pixel intersection against
reviewed anatomical annotations before retaining any case.

| Painting | Preliminary matching canonical cases | Why shortlisted |
|---|---|---|
| `p001` | `scratch_thin`, `loss_large`, `mixed_damage` | Damage visibly crosses the face or other exposed skin; a key darker rendered-skin example, but not a standalone subgroup. |
| `p006` | `scratch_thin`, `loss_small`, `mixed_damage` | Existing masks visibly intersect the face and hands. |
| `p007` | `scratch_thin`, `mixed_damage` | Damage visibly intersects both face and hand areas. |
| `p008` | `loss_small` | Local missing region visibly intersects a hand. |
| `p009` | `scratch_thin`, `loss_small`, `loss_large`, `mixed_damage` | Strong candidate with face damage and several large, clearly visible hands; supports both anatomy and damage-size screening. |
| `p251` | `scratch_thin`, `mixed_damage` | Damage visibly intersects face and hand regions in a non-European portrait tradition. |
| `p252` | `scratch_thin`, `mixed_damage` | Scratch evidence intersects a hand and mixed damage crosses the face. |
| `p254` | `scratch_thin`, `loss_large` | Existing masks visibly intersect hand and face areas. |
| `p255` | `scratch_thin`, `loss_large` | Existing masks visibly intersect exposed face or hand pixels. |
| `p256` | `mixed_damage` | Damage appears to intersect the extended hand or arm area; exact overlap requires annotation. |
| `p259` | `scratch_thin`, `loss_small`, `loss_large`, `mixed_damage` | Multiple existing masks visibly affect the face and hands; strong focused-cohort candidate. |
| `p267` | `scratch_thin`, possibly `mixed_damage` | Clear face intersection; possible hand intersection remains provisional. |
| `p284` | `scratch_thin`, `loss_large` | Damage visibly affects the face and hand; useful focused-cohort candidate. |
| `p294` | `loss_small`, `mixed_damage` | Local loss visibly affects a hand and mixed damage covers part of the face. |

For each listed family, the exact existing inputs follow these paths:

```text
outputs/03_canonical_mask_generation/images/masks/<painting_id>/<damage_family>.png
outputs/04_canonical_damaged_image_generation/images/damaged/<painting_id>/<damage_family>.png
```

Notebook 06 is expected to provide additional accidental hand or face overlap
because each focused painting has three mask families with five controlled
variants. That expectation is not evidence of adequacy until the overlap audit
has measured it.

### Shared anatomical annotation contract

Damage masks cannot define the anatomical target. D02 must load a separate,
manually reviewed annotation layer covering, where visible:

```text
face
visible_skin
left_hand
right_hand
other_exposed_body_part
```

Each annotation record must include at least:

- `painting_id` and stable annotation identifier;
- `region_type`;
- polygon, RLE, or binary-mask path;
- visible pixel area on the normalized 768 × 768 content canvas;
- ambiguity and occlusion fields;
- annotator, optional second reviewer, and review status; and
- a concise note for stylized, tiny, cropped, or otherwise uncertain regions.

Annotations must respect recorded content bounds and must never be inferred
silently from a photographic face, hand, race, or ethnicity detector. Any
assisted proposal mechanism requires human correction and explicit provenance.

### Hard feasibility gate

Before reading model-performance outcomes, D02 must compute the intersection of
every candidate damage mask with each reviewed anatomical region. Initial
contract thresholds are:

- at least 256 damaged anatomical pixels;
- at least 5% of the annotated anatomical region affected;
- adequate contiguous coverage for any crop-level metric; and
- valid reference, damaged image, mask, restoration, and required evidence for
  every compared method.

The preparation layer may refine these exact thresholds only before outcome
inspection and with the change recorded in the notebook contract. The
analysis-only hand study proceeds when the audit finds approximately:

- at least 12 independent paintings with usable hand intersections;
- at least 20–30 usable hand-hit cases;
- coverage from more than one damage family; and
- viable within-case non-hand controls.

If this gate fails, D02 must stop after publishing a feasibility result. A later
self-contained targeted extension may be proposed to own anatomy-constrained
masks, damaged images, four-model restorations, metrics, figures, reports,
manifests, and validation, but it is not authorized by this contract.

### Primary hand-restoration design

For each eligible damaged hand region, construct a non-hand control from the
same painting and damaged case. Match as closely as the saved mask allows on:

- damaged pixel count and damaged fraction;
- damage family and mask geometry;
- local gradient or edge density;
- texture complexity;
- boundary distance; and
- contiguous crop size where crop-based metrics are used.

Measure sparse intersection evidence only with metrics that support sparse
pixels, including MAE, RMSE, PSNR, CIEDE2000, lightness/chroma error, and
applicable boundary or seam evidence. Use SSIM, LPIPS, CLIP, DINOv2, and other
patch or feature metrics only on declared contiguous hand and matched-control
crops. Never pass disconnected pixels to a metric whose assumptions require a
spatial image patch.

Add a blinded manual anatomical review covering:

- correct visible digit count;
- missing, duplicated, or fused digits;
- broken hand contour;
- implausible articulation or pose;
- discontinuity at the wrist or arm; and
- obvious non-anatomical texture substitution.

The primary estimand is the within-case hand-minus-control performance
difference for each method. Painting is the independent unit. Stable Diffusion
seeds are collapsed within the fixed case/prompt/configuration group before
painting-level inference. Report paired effect sizes and painting-clustered
intervals; apply multiple-testing correction to a small predeclared primary
outcome family. Candidate rows, seeds, masks, and metric rows must not be treated
as independent paintings.

### Secondary depicted-skin-tone design

The approved name is **exploratory depicted-skin-tone restoration disparity
audit**. D02 must not classify race or ethnicity from appearance or describe an
observed difference as inherent model bias.

- Annotate visible face and exposed-skin regions independently of damage masks.
- Derive a continuous rendered-pixel measure, primarily median CIELAB `L*`, from
  the clean annotated skin region; retain chroma and local contrast as context.
- Use bins only for presentation and freeze their thresholds before examining
  restoration outcomes.
- Preserve explicit museum-catalog subject context where available, but do not
  infer missing identity metadata from the image.
- Analyze model-specific local errors against continuous rendered lightness and
  show individual paintings rather than relying only on group averages.
- Match or adjust descriptively for damaged fraction, visible face/skin area,
  texture, palette, source, period, medium, pose, and image scale where the data
  permit.

The visually screened collection contains only a small and heterogeneous set of
plausible darker-rendered or non-European subject examples, notably `p001` and
Mughal/Indian works `p251`, `p252`, `p254`, and `p255`. The focused seven-painting
cohort contains only `p001` as a clear darker-rendered example. Source, period,
medium, composition, and style are therefore strongly confounded with rendered
skin tone.

If fewer than roughly six sufficiently matched paintings occupy a comparison
range, or confounding cannot be reduced, D02 must retain a feasibility-only or
case-descriptive conclusion and omit a between-group bias claim. Agreement does
not establish correctness, and a local metric difference does not establish
historical, social, or conservation meaning.

### Approved batches

1. **Contract, preflight, and ethical boundaries** — freeze questions,
   exclusions, evidence sources, primary outcomes, thresholds, independent unit,
   model scope, and stop conditions.
2. **Portrait population and case loading** — load all 60 portraits, normalized
   content bounds, N03–N07 cases, masks, damaged images, and validated manifests;
   construct a complete screening table without reading model outcomes.
3. **Anatomical annotation validation** — load and validate the reviewed face,
   skin, hand, and optional exposed-body-region annotations, including visual QA.
4. **Overlap audit and hard feasibility decision** — measure exact anatomical
   intersections, apply predeclared thresholds, report coverage by painting and
   damage family, and stop cleanly when a study is unsupported.
5. **Candidate and evidence joins** — join only eligible cases to matched Telea,
   LaMa, HINT, and Stable Diffusion candidates and existing N13–N21 evidence;
   retain seed nesting and bounded SDXL status.
6. **Hand-versus-control construction and measurement** — create matched
   within-case controls, compute compatible sparse and contiguous-region
   evidence, and prepare blinded review units.
7. **Depicted-skin-tone audit** — compute the continuous rendered-lightness
   description, qualified matching/context fields, local evidence, and hard
   claim-eligibility result.
8. **Painting-level analysis and robustness checks** — estimate paired effects,
   clustered intervals, model contrasts, sensitivity to matching and thresholds,
   and corrected tests where supported.
9. **Visual evidence and report** — show all eligible-case coverage through
   canonical tables and select representative visual units by explicit rules;
   keep hand and skin-tone conclusions separate and state every limitation.
10. **Persistence, validation, and traceability** — reload canonical outputs,
    reconcile every row and file, write manifests and checks, map the approved
    contract to evidence, and clean temporary material.

### Planned canonical outputs

The final preparation layer must minimize duplication and may refine filenames,
but the owned artifact families are expected to include:

```text
data/anatomical_annotations.csv
data/anatomical_overlap_audit.csv
data/eligible_cases.csv
data/manual_anatomy_review.csv
metrics/hand_region_comparison.csv
metrics/skin_tone_audit.csv
figures/hand_vs_control.png
figures/anatomical_failure_atlas.png
figures/skin_tone_audit.png
reports/portrait_skin_tone_and_hand_audit.html
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

The completed local run passed all 137 validation checks and left no temporary
work files. Compared with the preserved Controlled-50 output copy, spatial
rows increased from 18,896 to 143,247 and candidate maps from 10,050 to
76,020. The 170 pilot-only map-manifest paths comprise 160 maps for the 32
approved displaced Notebook 11 contextual candidates and ten reselected
panels; no evidence family was lost. Bulk maps and the spatial-diagnostics
table remain locally canonical and are covered by the verified indexed-bundle
N16 diagnostics release. The pre-N34 review governs dashboard access.

The HTML report must be self-contained, provide the complete numerical coverage
through owned tables, and use selected embedded panels to explain—not replace—the
complete evidence. A missing or unsupported secondary skin-tone claim does not
invalidate a properly completed hand study, but each study requires its own
applicability and completion status.

### Final completion gate

- Notebook 21 and every direct producer have passed under Controlled-300.
- All 60 portraits were screened; exclusions have explicit reasons.
- Anatomical annotations are independent from damage masks and visibly reviewed.
- Every retained case passes the frozen intersection and evidence-completeness
  thresholds.
- Hand and matched-control construction is reproducible and auditable.
- Painting-level independence and Stable Diffusion seed nesting are preserved.
- Sparse and contiguous-region metrics are used only where valid.
- The manual anatomical rubric is complete for the retained visual-review scope.
- The depicted-skin-tone result remains exploratory and passes its separate
  claim-eligibility gate before any comparative statement is made.
- No race, ethnicity, inherent-bias, historical-correctness, or conservation-
  approval claim is inferred from computational evidence.
- All outputs remain inside the D02 root, reload successfully, reconcile with
  the artifact manifest, and pass consolidated validation.

---

## 22 — Damage-Size Diffusion Uncertainty Extension

**Notebook:** `22_damage_size_diffusion_uncertainty_extension.ipynb`\
**Origin:** New post-freeze evidence extension correcting a downstream dependency omitted from the frozen 01–21 baseline\
**Output root:** `outputs/22_damage_size_diffusion_uncertainty_extension/`\
**Depends on:** Notebooks 05, 08, 11, and validated metric/region contracts from Notebooks 13–20

### Purpose

Create the repeated-seed Stable Diffusion evidence required to analyze generative uncertainty against damage size without modifying or rerunning any frozen Notebook 01–21 artifact.

### Frozen-baseline boundary

- Treat every Notebook 01–21 notebook, output, manifest, helper contract, and validated population as read-only evidence.
- Reuse the existing Notebook 11 generic primary candidate at seed `2026` by reference; do not copy, overwrite, or relabel it.
- Generate only the missing generic-prompt candidates at seeds `2027`, `2028`, and `2029` for the 245 Notebook 05 damage-size cases.
- Own all 735 new restoration images, candidate records, uncertainty metrics, maps, checkpoints, manifests, and validation artifacts under the Notebook 22 output root.
- Keep extension candidate IDs and ownership explicit so later notebooks can combine evidence without rewriting Notebook 11 history.

### Responsibilities

- Build exactly 245 prompt-specific uncertainty groups covering 35 paintings (seven per category) and seven nested target levels: 2%, 4%, 6%, 8%, 10%, 15%, and 20%.
- Use the frozen Notebook 11 `p00_generic` prompt policy, model revision, scheduler, inference steps, guidance, strength, resolution, compositing, and mask-threshold contracts.
- Preserve the exact seed set `2026`, `2027`, `2028`, and `2029` in every group.
- Support checksum-aware resume and generate only missing extension candidates.
- Print progress at least every ten candidates and checkpoint safely on Windows.
- Validate dimensions, masks, compositing, outside-mask invariance, image readability, checksums, candidate uniqueness, and exact seed coverage.
- Compute transparent image-space and pairwise uncertainty components without constructing a combined uncertainty score:
  - per-pixel RGB standard deviation;
  - pairwise RGB MAE and RMSE;
  - pairwise LPIPS distance;
  - pairwise CLIP cosine distance;
  - pairwise DINOv2 cosine distance.
- Summarize uncertainty over the canonical full-image, content, masked, mask-crop, boundary, and outside-mask regions where methodologically valid.
- Retain raw numerical uncertainty maps and selected readable overlays.
- Join validated primary-candidate reference, perceptual, feature, texture, colour, seam, spatial, and semantic evidence for downstream association analysis; do not recompute or overwrite frozen canonical tables.
- State that repeated-seed variation is empirical generative variability, not calibrated confidence or restoration correctness.

### Exact population contract

```text
damage-size cases: 245
paintings: 35
damage levels per painting: 7
seeds per group: 4
referenced upstream candidates: 245
new extension candidates: 735
complete uncertainty groups: 245
unique unordered seed pairs: 1470
```

### Canonical outputs

```text
data/candidates.csv
data/uncertainty_maps.npz
metrics/damage_size_uncertainty.csv
images/restored/<case_id>/<candidate_id>.png
images/uncertainty/<uncertainty_group_id>.png
figures/uncertainty_extension_summary.png
manifests/map_images.csv
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## 23 — Damage-Size Sensitivity Analysis

**Notebook:** `23_damage_size_sensitivity_analysis.ipynb`\
**Origin:** New analysis stage separated from Notebook 05 generation  
**Refactor status:** Finished\
**Validation status:** Finished\
**Completion gate passed:** Yes\
**Output root:** `outputs/23_damage_size_sensitivity_analysis/`\
**Depends on:** Notebooks 05, 08–17, and 20–22

### Responsibilities

- Analyze all metric families against target and realized damage percentage.
- Produce performance-versus-damage curves.
- Identify nonlinear degradation points.
- Test whether model rankings change with damage size.
- Test whether uncertainty increases with damage size.
- Analyze painting-specific trajectories and mask-morphology relationships;
  report seven-painting-per-category summaries as exploratory, not validated
  art-historical style effects.
- Compare deterministic and generative sensitivity.
- Use paired/matched statistical methods.
- Report confidence intervals and effect sizes.
- Avoid overclaiming thresholds when sample sizes are small.

**Controlled-300 statistical contract:** 245 cases, 35 paintings, seven
matched levels, 980 four-method primary candidates. Compute painting-level
trajectories, matched model differences, effect sizes and intervals using the
bounded N23–N25 design in Section 2.2. Keep all 11 anchors descriptive;
use the seven predeclared primary inferential anchors and freeze exact contrast
and BH-family keys at preparation. Use N22's 245 repeated-seed groups only for Stable Diffusion
damage-size uncertainty. Replace pilot five-painting bootstrap/sign-flip
enumeration rather than changing a count constant.

### Canonical outputs

```text
metrics/damage_size_analysis.csv
figures/performance_vs_damage.png
figures/ranking_vs_damage.png
figures/uncertainty_vs_damage.png
reports/damage_size_analysis.html
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## 24 — Mask Robustness Analysis

**Notebook:** `24_mask_robustness_analysis.ipynb`\
**Origin:** New analysis stage separated from Notebook 06 generation  
**Output root:** `outputs/24_mask_robustness_analysis/`\
**Depends on:** Notebooks 06, 09–21

### Responsibilities

- Measure metric variance within matched robustness groups.
- Measure input-mask robustness variation due to placement and exact geometry.
- Analyze model-ranking stability.
- Analyze metric-ranking stability.
- Analyze sensitivity to location, morphology, boundary contact, and component arrangement.
- Compute confidence intervals and effect sizes.
- Compare robustness by model, painting, robustness group, target percentage, and damage family.
- Distinguish stochastic candidate variation from input-mask robustness.
- Identify conclusions that depend excessively on one mask realization.

**Controlled-300 statistical contract:** 525 cases and 2,100 four-method
primary candidates over 35 paintings, three mask families and five variants
per matched group. Preserve the five variant conditions while removing the
pilot assumption of five paintings. Aggregate variation within a painting
and family before painting-cluster inference; follow Section 2.2's bounded
bootstrap, Monte Carlo and runtime gate. Category summaries remain exploratory.

### Canonical outputs

```text
metrics/mask_robustness_analysis.csv
figures/robustness_variance.png
figures/ranking_stability.png
reports/mask_robustness_analysis.html
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## 25 — Synthetic Degradation Analysis

**Notebook:** `25_synthetic_degradation_analysis.ipynb`\
**Origin:** New analysis stage separated from Notebook 07 generation  
**Output root:** `outputs/25_synthetic_degradation_analysis/`\
**Depends on:** Notebooks 01, 07–17, 20, and 21

### Responsibilities

- Analyze only model/degradation combinations marked eligible.
- Separate missing-region restoration from degradation correction/robustness.
- Compare individual and selected combined degradations.
- Analyze by degradation type, severity, affected area, painting, and model.
- Use suitable reference, colour, texture, seam, semantic, and spillover evidence.
- Report excluded combinations and eligibility reasons.
- Compare quality, failure behavior, and compute.
- Reiterate that procedural degradations are not exact conservation simulations.
- Treat Notebooks 18 and 19 as not applicable because no repeated-seed
  synthetic-degradation uncertainty groups were generated; do not create or
  imply unavailable uncertainty evidence.

**Controlled-300 statistical contract:** 1,155 generated design cases across
35 paintings, of which 350 are eligible masked-removal cases with 1,400
four-method primary restorations. Keep the 11 completed SDXL synthetic cases
as a bounded, descriptive subset. Predeclare matched painting-level contrasts
for eligible family/severity/combination effects and use Section 2.2's bounded
resampling/test design; report all 11 quality anchors descriptively. Do not
misclassify full-image degradation effects as inpainting failures.

### Canonical outputs

```text
metrics/degradation_analysis.csv
figures/degradation_performance.png
figures/degradation_failure_examples.png
reports/synthetic_degradation_analysis.html
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## 26 — Grouped and Statistical Analysis

**Notebook:** `26_grouped_and_statistical_analysis.ipynb`\
**Origin:** New Notebook; consolidates statistical responsibilities previously dispersed across comparisons  
**Output root:** `outputs/26_grouped_and_statistical_analysis/`\
**Depends on:** Notebooks 08–25, using validated metric evidence from Notebooks 13–25

### Responsibilities

Analyze performance by:

- model;
- painting category;
- damage type;
- damage percentage;
- mask morphology;
- mask seed;
- uncertainty level;
- degradation type;
- dataset source, recorded as not applicable for comparison because the repository
  contains only the active `controlled_300` scope;

The primary cross-model population is fixed before reading metric values:
2,620 candidates for each of OpenCV Telea, LaMa, HINT and primary generic-
prompt Stable Diffusion. The 300 canonical zero-control cases per full method
remain an integrity population, so restoration-quality inference uses 2,320
nonzero cases and 9,280 full-method primary candidates. Twenty-four technically
valid SDXL candidates form a separate bounded, descriptive population.

Painting is the independent statistical unit. Cases, candidates, mask variants,
seeds, regions, and metrics are repeated or nested observations. Category-level
inference is restricted to the balanced 300-painting canonical population.
Damage-size, mask-robustness and synthetic-degradation cohorts contain seven
paintings per category; subgroup comparisons remain exploratory with painting
as the independent unit. Incomplete metadata does not support a general
independent art-historical style effect.

Generative uncertainty covers exactly 1,025 prompt-specific repeated-seed groups:
780 canonical groups from Notebook 18 and 245 damage-size groups from Notebook 22.
The generic and scratch-aware prompt arms remain separate. Mask robustness and
synthetic degradation have no repeated-seed population and must not receive
artificial uncertainty values.

Required methods:

- descriptive statistics and distributions;
- confidence intervals;
- paired comparisons;
- effect sizes;
- non-parametric tests where appropriate;
- multiple-comparison correction;
- ranking stability;
- sensitivity analysis;
- quality-versus-compute analysis;
- Pearson or Spearman correlation where suitable;
- rank correlation;
- metric-family agreement and disagreement;
- PSNR versus SSIM disagreement;
- classical versus LPIPS disagreement;
- CLIP versus DINOv2 disagreement;
- semantic versus texture disagreement;
- semantic/feature affinity versus pixel, perceptual, texture, colour, and seam reference fidelity;
- uncertainty versus scalar performance;
- region-policy disagreement;
- cross-model disagreement.

Do not overstate results for small or imbalanced groups. Metric disagreement must remain visible rather than being averaged away.
Do not retain a combined quality, efficiency, uncertainty, or trust score.
Runtime remains operational evidence outside restoration-quality ranking.
Uncertainty is empirical seed variability, not calibrated confidence. Results do
not establish historical authenticity, conservation suitability, or museum
approval.

### Canonical outputs

```text
metrics/statistical_results.csv
metrics/metric_correlations.csv
metrics/ranking_stability.csv
figures/correlation_matrix.png
figures/grouped_performance.png
figures/effect_sizes.png
reports/statistical_analysis.html
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## 27 — Failure Taxonomy and Trustworthiness Flags

**Notebook:** `27_failure_taxonomy_and_trustworthiness_flags.ipynb`\
**Origin:** New Notebook  
**Output root:** `outputs/27_failure_taxonomy_and_trustworthiness_flags/`\
**Depends on:** Notebook 08 for case identity, Notebooks 09–12A for candidate identity,
and Notebooks 13–26 for analytical evidence

### Approved population

- 10,504 primary comparison candidates: 10,480 across four full methods plus
  24 completed bounded SDXL candidates;
- 4,100 candidate memberships in complete supported repeated-seed groups:
  3,120 from N18 and 980 from N22 (including referenced N11 anchors);
- derive shared IDs and the exact union from validated source manifests rather
  than hard-code a pilot overlap or union count.

The population role must remain explicit. Uncertainty-only seeds and prompt arms
must not enter ordinary model comparison, and bounded SDXL evidence must not be
presented as full-population evidence.

### Failure taxonomy

Candidate categories include:

- residual masked-region error;
- excessive blur;
- structural-collapse proxy;
- semantic inconsistency proxy;
- repeated-texture proxy;
- texture smoothing;
- texture discontinuity;
- colour-bleeding proxy;
- colour drift;
- boundary seam;
- mask spillover;
- outside-mask alteration;
- composition-change proxy;
- unstable multi-seed completion;

### Trustworthiness flags

Independent flags include:

- high generative uncertainty;
- semantic inconsistency;
- structural inconsistency;
- texture inconsistency;
- colour inconsistency;
- visible boundary-artifact proxy;
- outside-mask alteration;
- restoration instability;
- metric disagreement;
- insufficient evidence;
- manual review required.

### Responsibilities

- Define every taxonomy category and evidence requirement.
- Generate independent flags rather than one trust score.
- Record flag name, triggering rule, supporting evidence, affected region, threshold, severity where defensible, explanation, and recommended action.
- Analyze co-occurrence between uncertainty, reference error, semantic, texture, colour, seam evidence, and rule-defined failure assignments without describing the result as calibrated confidence.
- Distinguish missing evidence from passing evidence.
- Test internal rule consistency.
- Use transparent operational warning and critical thresholds rather than
  learned failure labels: fit the initial 90th and 97.5th percentile adverse-tail
  rules on the 9,280 non-zero four-method primary candidates, exclude zero controls and
  bounded SDXL from fitting, preserve experiment and indicator strata, and keep
  prompt arms separate for uncertainty evidence.
- Apply strict adverse comparisons to percentile thresholds so observations tied
  at a zero floor or unit ceiling are not misclassified as warning or critical;
  retain inclusive comparisons for explicit absolute-tolerance rules.
- Treat percentile severity as rule strength and review priority, not
  conservation severity. Notebook 28 owns threshold and aggregation sensitivity.
- Persist the complete candidate-by-category and candidate-by-flag grids so that
  `insufficient_evidence` and `not_applicable` remain distinct from
  `not_triggered`.
- Generate recommendation categories such as:
  - suitable for preliminary inspection;
  - specialist review required;
  - unstable candidate;
  - do not rely on automatically.
- State that flags are decision-support outputs, not conservation approvals.

### Canonical outputs

```text
data/failure_taxonomy.csv
metrics/failure_assignments.csv
metrics/trustworthiness_flags.csv
reports/flag_definitions.html
figures/failure_taxonomy.png
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

The HTML report is self-contained and retains the approved mock's fifteen-section
structure, visual atlas, evidence-to-assertion conclusions, nearby limitations,
and embedded diagnostic images when downloaded without the repository.

---

## 28 — Metric and Region-Policy Ablation

**Notebook:** `28_metric_and_region_policy_ablation.ipynb`\
**Origin:** New Notebook; includes alternatives prepared by Previous Notebook 26  
**Output root:** `outputs/28_metric_and_region_policy_ablation/`\
**Depends on:** Notebooks 13–27

**Controlled-300 constraint:** Retain exactly the 23 previously approved,
explicitly named scenarios; do not form a metric-subset powerset. Process the
expanded N27 candidate union in bounded chunks, with complete case-level
outputs and provenance.

### Metric-family ablations

Evaluate:

- without classical metrics;
- without LPIPS;
- without CLIP;
- without DINOv2;
- without texture;
- without colour;
- without seam evidence;
- without uncertainty;
- with only classical metrics;
- with only perceptual metrics;
- with only semantic/feature metrics;
- with the complete multi-metric framework.

### Region-policy ablations

Compare:

- full image only;
- content region;
- masked pixels where valid;
- mask-bounding-box crop;
- boundary regions;
- outside-mask region;
- complete approved region policy.

### Threshold and aggregation sensitivity

Test:

- alternative flag thresholds;
- alternative metric subsets;
- alternative aggregation rules;
- model-ranking changes;
- case-ranking changes;
- flag changes;
- category/damage subgroup changes where the independent group count is sufficient;
- disagreement changes;
- conclusion stability.

Do not create a universal trust score.

### Canonical outputs

```text
metrics/ablation_results.csv
metrics/flag_stability.csv
figures/ablation_ranking_changes.png
figures/ablation_flag_changes.png
reports/ablation_study.html
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## 29 — Explainable AI and Case Retrieval

**Notebook:** `29_explainable_ai_and_case_retrieval.ipynb`\
**Origin:** New Notebook  
**Output root:** `outputs/29_explainable_ai_and_case_retrieval/`\
**Depends on:** Notebooks 15–28

### Spatial explanations

Assemble:

- difference maps;
- uncertainty heatmaps;
- seam maps;
- colour-drift maps;
- texture-inconsistency maps;
- semantic-drift maps;
- mask and boundary overlays.

### Metric-level explanations

For each selected/flagged case, report:

- metric values and improvements;
- evaluation regions;
- triggering evidence;
- disagreements between evidence families;
- limitations and missing evidence.

### Counterfactual explanations

Compare:

- the same painting at different damage sizes;
- the same target percentage at different placements;
- the same case across models;
- the same case under different metric subsets;
- diffusion candidates across seeds;
- the framework with one evidence family removed;
- generic versus scratch-aware damage-specific prompts where applicable.

### Example-based explanations

Provide:

- representative rule-defined lower-risk cases;
- representative rule-defined flagged cases;
- nearest similar lower-risk case;
- nearest similar flagged case;
- examples by complete artwork category and, where metadata exists, descriptive style or period;
- examples by damage type, model, and flag;
- embedding-based retrieval using validated feature artifacts.

`data/explanation_cases.csv` is the complete machine-readable explanation
catalog for the validated Controlled-300 Notebook 27 union, not only the cases
illustrated in the HTML report. It records population role, recommendation and
flag evidence, available asset/map paths, uncertainty applicability, retrieval
eligibility, report-selection roles, counterfactual-panel membership, and
explicit scope or missingness states. The report uses a deterministic 24-unit
visual subset (14 counterfactual panels and 10 retrieval queries), while the
full catalog remains available for case-by-case inspection.

Style or period metadata is descriptive and incomplete. Category coverage is
complete and is therefore the primary stratification; no independent style
effect is claimed.

### Rule-based explanations

Every flag explanation includes the rule, evidence, affected region, threshold, applicable uncertainty evidence, and recommended human action.

### Canonical outputs

```text
data/explanation_cases.csv
data/case_neighbors.csv
figures/counterfactual_panels/
figures/example_retrieval_panels/
reports/explanation_catalog.html
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## 30 — Model Cards, Compute, and Scalability

**Notebook:** `30_model_cards_compute_and_scalability.ipynb`\
**Origin:** New Notebook; incorporates existing model-audit documentation  
**Output root:** `outputs/30_model_cards_compute_and_scalability/`\
**Depends on:** Notebooks 09–29 and model-audit sources

### Model/method cards

Document for every method:

- name and exact version;
- model family;
- original purpose;
- training-data description where available;
- licence;
- input and mask constraints;
- deterministic or stochastic behavior;
- known limitations and biases;
- domain gap between photographs and paintings;
- prompt dependence;
- hardware requirements;
- fully evaluated, partially evaluated, or feasibility-only status.

OpenCV Telea receives a method card.

### Compute and scalability

Record and analyze:

- runtime per case and total runtime;
- CPU/GPU device;
- GPU model and VRAM where practical;
- inference resolution;
- storage use and file count;
- throughput;
- failure rate and retry count;
- uncertainty candidate multiplier;
- observed 300-painting cost and clearly separate projections beyond 300;
- projected SDXL cost;
- quality versus runtime, memory, storage, candidates, and dataset size.

### Canonical outputs

```text
data/model_cards.csv
metrics/compute_scalability.csv
reports/model_cards/<model_id>.md
figures/quality_vs_compute.png
figures/scaling_projection.png
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

# Reporting, Dashboard, and Packaging

## 31 — Model Report Generation

**Notebook:** `31_model_report_generation.ipynb`\
**Origin:** Consolidates Existing Notebooks 13, 19, and 26  
**Output root:** `outputs/31_model_report_generation/`\
**Depends on:** Notebooks 09–30

**Controlled-300 scope:** Five reports: four full-evaluation methods and one
clearly bounded SDXL report. Existing approved report structure remains the
blueprint; numerical results and embedded visuals come from validated new
evidence only.

### Responsibilities

Generate one parameterized report per model/method including:

- method card summary;
- eligible dataset/experiment scopes;
- runtime and failure evidence;
- classical, LPIPS, and feature metrics;
- texture, colour, and seam evidence;
- uncertainty for diffusion models;
- semantic and structural evidence;
- representative success and failure cases;
- difference and explanation maps;
- failure taxonomy and triggered flags;
- compute and scalability;
- known limitations;
- feasibility-only status where applicable.

Reports must not create new scientific evidence.

### Canonical outputs

```text
reports/<model_id>.html
data/report_index.csv
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## 32 — Case and Painting Report Generation

**Notebook:** `32_case_and_painting_report_generation.ipynb`\
**Origin:** Existing Previous Version of Notebook 33, Pre-refactor  
**Output root:** `outputs/32_case_and_painting_report_generation/`\
**Depends on:** Notebooks 09–31

**Controlled-300 scope:** Produce a report for each of the 300 paintings and
retain a complete machine-readable index of applicable cases, candidates,
metrics and visuals. Rule-selected standalone case reports are a presentation
subset; they do not limit evidence coverage.

### Responsibilities

Use rule-based auditable selection.

Each case report should include:

- clean reference;
- damaged/degraded input;
- binary mask or effect mask;
- all available model outputs;
- classical metrics;
- LPIPS;
- CLIP and DINOv2;
- texture diagnostics;
- colour diagnostics;
- seam diagnostics;
- uncertainty map where applicable;
- semantic/XAI maps;
- triggered trustworthiness flags;
- failure classifications;
- flag explanations;
- runtime/model metadata;
- known limitations;
- recommended human-review action.

Per-painting reports should summarize all relevant damage conditions, models, stability patterns, and flags.

Reports must repeat:

> Visual plausibility is not equivalent to historical or restoration trustworthiness.

### Canonical outputs

```text
data/selected_cases.csv
data/case_report_index.csv
data/painting_report_index.csv
reports/cases/<case_id>.html
reports/paintings/<painting_id>.html
reports/index.html
figures/selected_case_grids/
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## 33 — Final Evaluation Report

**Notebook:** `33_final_evaluation_report.ipynb`\
**Origin:** Existing Previous Version of Notebook 28, Pre-refactor  
**Output root:** `outputs/33_final_evaluation_report/`\
**Depends on:** Notebooks 21–32

### Responsibilities

Consolidate:

- dataset design and bias;
- damage/degradation protocols;
- model stack and availability;
- metric-region policy;
- classical, perceptual, feature, texture, colour, seam, semantic, and uncertainty evidence;
- damage-size findings;
- mask-robustness findings;
- synthetic-degradation findings;
- metric agreement/disagreement;
- ranking stability;
- grouped/statistical findings;
- failure taxonomy and flags;
- ablation findings;
- explainability findings;
- compute/scalability;
- model-card summaries;
- controlled-300 results and transparent further compute/storage projections;
- deviations, limitations, and exclusions.

Generate:

- consolidated HTML report;
- compact CSV result tables;
- LaTeX-ready tables;
- thesis-ready figures;
- publication-ready plots;
- correlation figures;
- sensitivity/robustness curves;
- uncertainty and ablation figures;
- trustworthiness summaries;
- reproducibility appendix inputs.

### Canonical outputs

```text
reports/final_evaluation.html
data/thesis_tables.csv
data/latex_tables.csv
figures/thesis/
figures/publication/
reports/limitations_and_deviations.md
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## 34 — Final Streamlit Dashboard Assets

**Notebook:** `34_final_streamlit_dashboard_assets.ipynb`\
**Origin:** Consolidates Existing Previous Versions of Notebooks 29 and 34, Pre-refactor  
**Output root:** `outputs/34_final_streamlit_dashboard_assets/`\
**Depends on:** Notebooks 01–33

### Responsibilities

Prepare lightweight validated assets for the approved eight-page application:

1. **Overview** — thesis framing, benchmark scope, headline findings, model
   roles, representative evidence, and central limitations.
2. **Study Design** — dataset and bias, canonical damage, damage-size, mask
   robustness, synthetic degradation, and the experiment pipeline.
3. **Metric Framework** — canonical regions, valid metric-region combinations,
   metric families, disagreement, ablation, and interpretation limits.
4. **Model Performance** — model stack, overall and conditional comparisons,
   local diagnostics, model cards, and compute trade-offs.
5. **Robustness & Uncertainty** — damage-size sensitivity, mask robustness,
   degradation sensitivity, repeated-seed variability, and spatial uncertainty.
6. **Trustworthiness & XAI** — failure taxonomy, separate diagnostic flags,
   difference/local/semantic maps, counterfactuals, and CLIP/DINOv2 retrieval.
7. **Case Explorer** — complete indexed case and painting populations with
   restorations, maps, evidence, provenance, and report links.
8. **Reports & Reproducibility** — final, model, case, painting, method, and
   sensitivity reports together with validation and provenance evidence.

These pages must package and expose the following validated evidence without
recomputing it:

- overview;
- dataset and bias;
- canonical damage;
- damage-size sensitivity;
- mask robustness;
- synthetic degradation;
- model stack;
- model comparison;
- metric-region policy;
- metric ablation;
- texture diagnostics;
- colour diagnostics;
- seam diagnostics;
- uncertainty summaries;
- uncertainty heatmaps;
- semantic consistency;
- XAI maps;
- trustworthiness flags;
- failure taxonomy;
- grouped/statistical analysis;
- compute/scalability;
- model cards;
- case and painting reports;
- reproducibility;
- final reports.

The application uses an authored museum-research visual language rather than a
generic corporate-dashboard treatment: aged-ivory surfaces, painting-derived
deep green/umber/vermilion/ochre accents, editorial serif headings, readable
sans-serif controls, restrained paper or canvas texture, thin graphite rules,
and sparse purposeful annotation marks. Tactile irregularity must remain subtle;
charts, filters, tables, accessibility, and presentation legibility take
priority over decoration.

Every principal page leads with a plain-language question or conclusion, then
balances headline indicators, one or two primary analytical views,
representative paintings or diagnostic images, concise evidence-backed
assertions, a nearby limitation, and expandable detail or provenance. The
approved dashboard mockups establish visual hierarchy and density only;
fictional mock values and accidental labels must never enter implementation.

Representative defaults are presentation choices, not evidence-availability
limits. The dashboard indexes must expose every applicable approved case,
painting, report, restoration, figure, and diagnostic image available from
validated upstream artifacts. Filters and direct selection provide access to
the complete indexed population.

### Mandatory Controlled-300 dashboard approval gate before refactoring

Do not edit Notebook 34, `streamlit_app.py`, or its dashboard helpers merely
because Notebook 33 has finished. First inspect the completed upstream
coverage and obtain a storage/access decision; then hold a dedicated dashboard
design review with the user. Record and obtain approval for:

- the exact evidence, metrics, plots, restorations, maps, reports, and
  conclusions on each of the eight pages, including the numerical case view;
- complete visual-index and filter coverage versus intentional presentation
  defaults, with no silently missing model or damage slice;
- a separately approved storage option and display path for each asset class,
  with a stable local-to-remote mapping and complete case-level access;
- the observed image counts and bytes by producer, storage-provider limits,
  dashboard memory/startup budget, latency, request behavior, and free-service
  feasibility, measured where possible rather than assumed;
- lazy loading and caching so a user selection fetches only its needed images,
  never the whole map corpus on app startup;
- explicit missing-asset, temporarily unavailable-storage, and optional-model
  behavior, plus a representative cross-model rendering test matrix; and
- preservation of the approved pilot layout unless the user explicitly
  approves a Controlled-300 change.

Only after that approval may Notebook 34 package the assets and the
application resolver be adapted. The existing pilot-50 branch and live app
remain unchanged through this review.

The dashboard consumes prepared assets and does not rerun experiments or
reconstruct project state from arbitrary outputs.

### Canonical outputs

```text
data/dashboard_summary.json
data/dashboard_tables/
data/dashboard_indexes/
manifests/dashboard_assets.csv
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

The Streamlit application must be updated to read this notebook-owned asset root rather than legacy `outputs/dashboard/`.

---

## 35 — Dashboard and Deployment Validation

**Notebook:** `35_dashboard_and_deployment_validation.ipynb`\
**Origin:** New Notebook  
**Refactor status:** Finished\
**Validation status:** Finished with non-blocking dependency warnings\
**Completion gate passed:** Yes\
**Output root:** `outputs/35_dashboard_and_deployment_validation/`\
**Depends on:** Notebook 34, `streamlit_app.py`,
`config/evaluation/dashboard_validation.yaml`, and
`src/restoration_eval/dashboard_application.py`

### Purpose

Validate the dashboard as a reproducible inspection and decision-support layer.

At Notebook 35 validation time, the application consumed the fixed dashboard
package under
`outputs/34_final_streamlit_dashboard_assets/`. It implements the approved
eight-page sequence: Overview, Study Design, Metric Framework, Model
Performance, Robustness & Uncertainty, Trustworthiness & XAI, Case Explorer,
and Reports & Reproducibility. Representative defaults control initial display
only; all 1,785 indexed candidates, 50 paintings, 23,964 visual records, and 104
reports remain accessible through filters or indexed downloads.

The three approved UI reference images remain external read-only planning
references and are not repository inputs or artifacts. Notebook 35 validates
mock-to-application traceability against the implemented interaction and visual
roles without copying those images into the project.

### Responsibilities

- Validate every dashboard input path and schema.
- Validate asset-manifest completeness.
- Validate case/report/image links.
- Validate that no dashboard section depends on missing legacy global paths.
- Validate controlled-scope and scaling-projection labeling.
- Validate model availability handling.
- Validate missing/optional SDXL behavior.
- Validate figure and heatmap rendering references.
- Validate that every approved visual-index path maps to an existing local
  file or a remotely verified, individually addressable image, with model,
  case, metric, and diagnostic-filter paths tested end to end.
- Validate lazy retrieval and realistic deployed memory/startup behavior;
  sample actual public image rendering across producer repositories without
  redownloading the complete corpus.
- Validate filter values and ID relationships.
- Validate that the dashboard does not recompute scientific metrics.
- Run safe import/static checks.
- Run an application smoke test when authorized.
- Record deployed URL and deployment metadata when available.
- Clearly state that the dashboard is not an experiment and not a restoration tool.

### Canonical outputs

```text
validation/dashboard_checks.csv
reports/deployment_readiness.md
manifests/run_manifest.json
manifests/artifacts.csv
```

### Historical notebook completion record

Notebook 35 completed all 14 roadmap responsibilities and persisted exactly
four canonical files. Its 582 validation checks contain zero blocking failures,
seven dependency-version warnings, and one informational result recording that
no public deployment had been performed at that run. All eight pages passed the
in-process Streamlit smoke test with zero exceptions or visible application
errors. The resulting status is
`conditionally_ready_for_local_demonstration`: the dashboard is ready for a
local supervisor demonstration. Exact dependency reconciliation and public
deployment were separate follow-up actions at the time. The final run ID is
`run_e04d0dfa163b4a15966c5420b01d74c7`.

The completed live-browser review approved all eight pages. The final interface
retains the accepted museum-research visual direction and adds explicit visual
translation where the evidence requires it: experiment walkthroughs, metric
and region explanations with a selectable diagnostic image, condition- and
model-filtered restoration comparisons, focused robustness and uncertainty
views, synchronized trustworthiness filters, complete case inspection, and the
three proposal research questions with evidence-bounded answers. Representative
defaults remain presentation choices only; the complete indexed populations
remain accessible.

### Post-notebook application delivery

The public deployment and approved numerical-metrics additions occurred after
this run. The current app retains the eight-page layout and the N34 candidate
allow-list, with read-only, checksum-verified upstream metrics exposed by the
contract in `docs/dashboard_numeric_metrics.md`. N35's recorded warnings and
not-deployed result remain historical facts, not statements about today's public
URL. Neither those records nor N36's copied application snapshot are rewritten
to claim they validated the later application revision. Current delivery
evidence is recorded in `docs/evidence_dependency_audit.md`.

---

## 36 — Supervisor, Publication, and Reproducibility Package

**Notebook:** `36_supervisor_publication_reproducibility_package.ipynb`\
**Origin:** Consolidates Existing Previous Versions of Notebooks 30 and 35, Pre-refactor  
**Refactor status:** Finished\
**Validation status:** Finished with inherited non-blocking dependency warning\
**Completion gate passed:** Yes\
**Output root:** `outputs/36_supervisor_publication_reproducibility_package/`\
**Depends on:** Notebooks 01–35

### Purpose

Assemble the final supervisor-facing, publication-facing, and reproducibility
delivery from already validated evidence. Notebook 36 is a packaging and
traceability stage: it does not rerun restoration models, recompute scientific
metrics, change upstream conclusions, or invent unavailable evidence.

### Approved evidence population

- 35 completed upstream notebook manifests;
- 50 paintings, 525 registered cases, and 410 restoration cases;
- 1,785 approved comparison candidates;
- 11 separate quality anchors;
- 165 repeated-seed uncertainty groups, comprising 130 canonical groups and 35
  damage-size groups;
- 23,964 indexed visual records and 104 indexed reports;
- ten bounded SDXL feasibility cases;
- 18 thesis figures and six publication figures;
- four self-contained model reports and one self-contained final report;
- 30 case-report records and 50 painting-report records.

### Package boundary

The portable package bundles the material required for efficient review:

- the final self-contained HTML report and four self-contained model reports;
- all 24 Notebook 33 thesis/publication figures;
- four model cards and eight compact tables or report indexes;
- all 35 upstream run manifests and all evaluation-configuration YAML snapshots;
- the two declared requirements files;
- the Notebook 35 deployment-readiness report;
- the Streamlit entry point and its read-only application helper; and
- Notebook 36 reports, indexes, manifest, and provenance snapshot.

The package indexes but does not duplicate the 30 case reports, 50 painting
reports, 30 selected-case grids, the 23,964-record dashboard visual collection,
restoration candidates, raw/map collections, model weights, or caches. Their
canonical repository-relative paths and checksums remain auditable. This keeps
the package useful when copied without duplicating the much larger report and
visual collections.

### Supervisor summary and research-question synthesis

The concise supervisor summary must contain:

- a decision snapshot and exact evaluated scope;
- the three proposal research questions reproduced verbatim;
- evidence-bounded answers to each research question;
- direct model conclusions with the supporting counts or metrics emphasized;
- robustness, uncertainty, trustworthiness, and XAI conclusions;
- reproducibility and dashboard-delivery status;
- explicit interpretation boundaries; and
- a short list of decisions or feedback requested from the supervisor.

Figures must use package-local links. Important values should be emphasized,
and factual results should be followed by a plain statement of what they imply
for restoration quality or model suitability. The summary is not a substitute
for the full self-contained reports.

### Responsibilities

Produce the final delivery package containing:

- supervisor summary;
- final HTML reports;
- compact CSV summaries;
- LaTeX-ready tables;
- thesis-ready figures;
- publication-ready figures;
- model reports;
- case and painting report indexes;
- model cards;
- experiment manifests;
- configuration snapshots;
- package versions;
- model versions/revisions;
- Git commit and dirty-state information;
- dataset versions;
- hardware information;
- seeds;
- compute/scalability summary;
- reproducibility appendix;
- limitations and deviations;
- dashboard/deployment status;
- complete artifact index;
- final package manifest.

Additionally:

- audit every Notebook 01–35 manifest for completed status, completion gate,
  unique notebook identity, and zero blocking failures;
- reconcile the package copy plan against fixed paths rather than discovering
  arbitrary files from output directories;
- preserve source bytes and verify source-to-package checksums;
- distinguish copied artifacts, generated Notebook 36 documents, and indexed
  but intentionally omitted collections;
- produce `open_questions.md` and `feedback_agenda.md` as meeting aids, not as
  new scientific claims;
- record Python, platform, hardware, package versions, Git state, dataset/config
  checksums, seeds, model revisions, observed compute, and scaling projections;
- validate package-relative links, self-contained HTML, path length, package
  size, file counts, byte counts, checksums, duplicate destinations, temporary
  files, and writes outside the notebook-owned root;
- repeat controlled-scope, SDXL, uncertainty, computational-flag, and
  conservation-approval limitations wherever a reader could otherwise
  overgeneralize the evidence.

Standalone HTML reports must follow the approved self-contained embedding policy:
required narrative figures and representative images remain visible when the HTML
is downloaded alone, while unrestricted full-resolution collections are not
embedded. Canonical sources, checksums, report size, and Git/LFS constraints must
remain auditable.

### Canonical outputs

```text
reports/supervisor_summary.md
reports/reproducibility_appendix.md
reports/limitations_and_deviations.md
data/artifact_index.csv
data/key_findings.json
data/open_questions.md
data/feedback_agenda.md
package/
manifests/package_manifest.json
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

Within `package/`, use the following stable groups:

```text
README.md
reports/
figures/thesis/
figures/publication/
tables/
model_cards/
manifests/notebook_runs/
configuration/evaluation/
environment/
application/
provenance/
```

The exact contract is versioned in
`config/evaluation/supervisor_package.yaml`; reusable package assembly and
integrity checks live in `src/restoration_eval/supervisor_package.py`.

### Final completion gate

- Every required upstream notebook has passed.
- Every package artifact exists and reloads.
- Every path is repository-relative and valid.
- Every optional omission has a documented reason.
- Package manifest counts reconcile with disk.
- Controlled results and scaling projections are clearly distinguished.
- Feasibility-only methods are not presented as evaluated models.
- Thesis interpretation boundaries are repeated.
- The package is ready for supervisor, thesis, publication, and reproducibility review.

---

# Completed method-selection decision evidence

## D01 — HINT and MAT Method Selection

**Notebook:** `d01_hint_mat_method_selection.ipynb`\
**Origin:** Completed post-pipeline method-selection decision\
**Refactor status:** Finished\
**Validation status:** Finished\
**Completion gate passed:** Yes\
**Output root:** `outputs/37_hint_mat_method_selection/`\
**Depends on:** Notebooks 01, 02, 03, 04, 08, 13–17, 19–21, 27–30, and the
governing evidence-coverage registry

### Purpose

Run a small, controlled head-to-head pilot of two candidate additions to the
expanded benchmark: HINT and MAT. D01 selected HINT for the new full production
stage N12A. D01 itself remains a 12-case selection study and must never be
presented as the full HINT benchmark.

### Approved evidence population

The comparison contains exactly twelve predeclared, nonzero canonical cases and
twenty-four outputs: one HINT and one MAT result for every case. The cases span
all five broad visual categories and contain exactly three examples of each
canonical damage family:

| Painting | Visual category | Approved cases |
|---|---|---|
| `p001` | portrait/figure | `loss_large`, `mixed_damage` |
| `p018` | landscape/natural | `loss_small`, `mixed_damage` |
| `p026` | architecture/structured | `scratch_thin`, `loss_large` |
| `p039` | abstraction/surrealism | `scratch_thin`, `loss_small`, `mixed_damage` |
| `p043` | high-texture/brushwork | `scratch_thin`, `loss_small`, `loss_large` |

The exact IDs and order are frozen in
`config/experiments/hint_mat_selection.yaml`. Selection is based on design
coverage and never on downstream metric values. The declared `p001` zero-control
case is used only to verify identity/no-op handling and is not part of the
twelve-case comparison.

### Model and adapter contract

- HINT uses the official repository revision and released Places2 checkpoint.
  It completed the pilot at the native 768 × 768 canvas; its declared 512 × 512
  fallback was not required.
- MAT uses the official repository revision and Places-512 FullData checkpoint.
  Its input is adapted from 768 × 768 to 512 × 512. The canonical mask is
  inverted because MAT's official interface uses zero for missing pixels and
  one for retained pixels.
- Both methods use seed `2026` wherever stochastic operations exist, return an
  RGB image to the 768 × 768 evaluation canvas, and replace only the canonical
  missing pixels. Every output must therefore preserve all outside-mask input
  pixels exactly.
- Released code and checkpoints remain external dependencies. Repository URLs,
  revisions, checkpoint checksums, adapters, environment, GPU, peak memory, and
  observed load/inference times must be recorded.
- Both methods passed the technical hard gates. HINT was selected from the full
  metric and visual evidence, not through the operational tie-break. MAT's
  noncommercial research license remains an additional deployment constraint.

### Evaluation responsibilities

Compute paired descriptive evidence for every completed output, reusing the
approved metric definitions and canonical region policy:

- pixel error, PSNR, and SSIM;
- LPIPS;
- CLIP and DINOv2 feature similarity;
- texture and directional/brushstroke proxies;
- colour differences including CIEDE2000;
- boundary and seam evidence;
- semantic and structural feature proxies;
- difference, error, improvement, colour, seam, and semantic/structural maps
  where applicable;
- runtime, model-load time, inference time, peak GPU memory, and failures.

No combined quality score, inferential p-value, calibrated confidence, or
conservation-suitability label may be constructed. Cases are nested within five
paintings, so the independent unit is the painting. The compact sample supports
paired descriptive method selection, not population-level inference.

### Completed human selection gate

The final choice remained explicitly human-owned. HINT was selected only after
both methods completed the required gate:

- load the official declared checkpoint;
- complete all twelve outputs;
- produce valid 768 × 768 RGB files;
- preserve every outside-mask pixel exactly;
- produce finite required metrics;
- have no unresolved runtime, memory, dependency, or license blocker; and
- pass visual inspection for missing content, blur, seams, colour shift,
  texture failure, structural drift, and implausible additions.

The final report shows the complete paired visual scope, retains separate metric
families, states why HINT is better suited to the expanded run, and explains the
important metric/visual disagreements. Batch 9 recorded the decision after the
user completed the visual review.

### Observed outcome

- All 24 candidates completed: 12 HINT and 12 MAT outputs across the exact
  predeclared cases.
- All 94 consolidated validation checks passed with no blocking or warning
  failures; every output was 768 × 768 RGB and preserved outside-mask pixels.
- HINT ran natively at 768 × 768. MAT used its declared 512 × 512 adapter and a
  supported PyTorch fallback for the optional CUDA extension.
- HINT led 96 of 108 case-level metric anchors, MAT led 6, and 6 were ties.
- Mean inference time was 8.26 seconds per case for HINT and 10.00 seconds for
  MAT. Recorded peak GPU memory was 5.06 GiB and 1.23 GiB, respectively.
- Complete visual review found that MAT often retained thin scratches and
  produced pale or fragmented large-loss completions. HINT was selected.

HINT fills a capability missing from the frozen benchmark: a second
deterministic learned method with mask-aware transformer processing and
long-range context modelling, complementing classical Telea, Fourier-convolution
LaMa, and stochastic prompt-conditioned Stable Diffusion. The selection is for
future expansion only; it does not make HINT a fourth evaluated method in the
existing leaderboard.

### Approved batches

1. Contract, environment, dependency, license, and external-asset preflight.
2. Exact population construction and 768/512 adapter validation.
3. Two-case paired smoke test covering thin and larger/mixed geometry.
4. Guarded full HINT execution with checkpointing and progress per case.
5. Guarded full MAT execution with checkpointing and progress per case.
6. Reference, perceptual, and feature metrics.
7. Texture, colour, seam, semantic/structural, and spatial diagnostics.
8. Paired descriptive analysis, complete visual atlas, and selection report.
9. Human decision record, persistence, manifests, validation, and completion.

### Canonical outputs

```text
data/selection_scope.csv
data/candidates.csv
images/restored/hint/
images/restored/mat/
metrics/metric_values.csv
metrics/runtime_summary.csv
metrics/decision_scorecard.csv
figures/smoke_comparison.png
figures/metric_comparison.png
figures/selection_atlas.png
reports/method_selection_report.html
reports/selection_decision.json
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

The output root is created by the notebook. External repositories, checkpoints,
temporary model caches, and downloaded weights are not notebook artifacts and
must not be copied into the project repository.

### Completion gate

- Exact 12-case scope and 24 paired candidates are persisted and reload.
- All four damage families have three cases and every visual category has at
  least two cases.
- HINT and MAT use the pinned official source/checkpoint identities.
- Actual adapter resolution and all fallback behavior are recorded.
- All required files, metrics, checksums, and visual comparisons exist.
- The recorded decision is `HINT` and is supported by separate technical,
  quality, runtime, license, and human-review evidence.
- No result modifies or retroactively reinterprets Notebooks 01–36.
- Governing audits and inventory are updated after completion.

---

# 4. Cross-cutting requirements matrix

| Requirement | Primary notebook(s) |
|---|---|
| Dataset licensing, completeness, duplicates, bias | 01 |
| 768 × 768 preprocessing and content bounds | 02 |
| Parameterized canonical masks and morphology | 03 |
| Canonical damaged images | 04 |
| Damage-size generation, repeated-seed extension, and analysis | 05, 22, 23 |
| Mask-robustness generation and analysis | 06, 24 |
| Synthetic degradation generation and analysis | 07, 25 |
| Case contracts, eligibility, and region policy | 08 |
| OpenCV, LaMa, Stable Diffusion, SDXL, production HINT | 09–12A |
| Classical metrics | 13 |
| LPIPS | 14 |
| CLIP and DINOv2 | 15 |
| Difference maps | 16 |
| Texture and brushstroke proxies | 17 |
| Colour consistency | 17 |
| Seam and boundary consistency | 17 |
| Diffusion uncertainty | 18, 22 |
| Heatmaps and spatial explanations | 19 |
| Semantic and structural consistency | 20 |
| Multi-model comparison | 21 |
| Grouped/statistical analysis and metric disagreement | 26 |
| Failure taxonomy and independent flags | 27 |
| Metric/region/threshold ablation | 28 |
| Counterfactual, example-based, and rule-based XAI | 29 |
| Model cards and compute/scalability | 30 |
| Per-model reports | 31 |
| Case and painting reports | 32 |
| Final report and publication assets | 33 |
| Dashboard assets | 34 |
| Dashboard/deployment validation | 35 |
| Supervisor/publication/reproducibility package | 36 |
| HINT/MAT method selection pilot and HINT decision | D01 |

## 5. Baseline preservation and controlled-300 completion boundary

The completed 50-painting sequence remains immutable at Git tag
`pilot-50-complete`. The active working tree may now reopen Notebooks 01–36 in
dependency order solely for the approved 300-painting minimal-delta rerun. D01
remains frozen; N12A is the only new production notebook presently approved.

For each numbered notebook:

1. approve a notebook-specific minimal-change contract;
2. adapt configuration/helpers before notebook text;
3. clear only that notebook's owned output root immediately before its rerun;
4. preserve existing cells and scientific behavior except for approved
   cardinality, path, dependency, HINT, and validation changes;
5. have the user paste and execute all notebook cells;
6. compare schemas, artifact roles, figures, reports, validation coverage, and
   artifact counts with both the tagged baseline and the read-only pre-scale
   output copy at `E:/outputs/<notebook_stem>/`;
7. present a before/after status table covering every old and new output, with
   row, file, manifest-record, figure, or report counts as appropriate and a
   reason for every changed count; unexplained missing or reduced evidence
   blocks completion;
8. update governing audits and inventory only after the new gate and baseline
   comparison pass; and
9. commit the notebook and compact scientific evidence before moving
   downstream; beginning with Notebook 12, complete bulk media and oversized
   tables remain locally canonical. The separately approved and verified N16/N17
   indexed-bundle releases are exceptions; other new external publication
   waits for the post-N33 storage review and explicit user approval.

`E:/outputs/` is an external read-only comparison snapshot, not a pipeline input
or a second active output root. The `pilot-50-complete` Git tag remains the
authoritative recovery point. The external snapshot exists so each refactored
notebook can demonstrate that controlled-300 preserved the approved artifact
families while increasing population-dependent counts for an explained reason.

The committed 50-painting outputs in the working tree are historical until
replaced notebook by notebook. A mixed state is therefore expected during the
transition, but no downstream notebook may treat an upstream stage as
controlled-300 until that producer's new manifest and validation gate pass.

