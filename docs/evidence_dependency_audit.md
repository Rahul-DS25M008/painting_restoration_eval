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

**Completed extension review: 2026-09-06.** Notebook 37 completed as a separate
HINT-versus-MAT method-selection experiment and selected HINT for the planned
expanded benchmark. This changes no frozen Notebook 01–36 evidence. Its exact
inputs, outputs, population, source/checkpoint requirements, observed results,
and decision boundaries are recorded in Section 6.2 and the YAML registry.

**Controlled-300 transition review: 2026-09-25.** The pilot remains recoverable
at Git tag `pilot-50-complete`; the active working tree is rebuilt in dependency
order for the approved 300-painting study. Notebooks 01–30, including Notebook
12A and supplemental D02, are completed, validated Controlled-300 producers.
Notebook 27's expanded failure-taxonomy and trustworthiness run contains 13,879
union candidates, 194,306 candidate-by-category rows, 152,669
candidate-by-flag rows, 1,025 supported uncertainty groups and 167/167 passing
checks. Notebook 29 completed its explainability and case-retrieval run, report,
pilot comparison and final gate. Notebook 30 run
`run_605de239145a46e9a202fd63bbbb4e9c` completed its Controlled-300 model-card,
compute and scalability contract with 178/178 checks and is now the canonical
method-disclosure source. Notebook 31 is the next active producer. Notebooks
31–36 remain historical Controlled-50 evidence until
each producer is explicitly reopened, rerun, validated, baseline-compared and
committed. Complete local outputs remain canonical even where large evidence is
also represented by verified external publication records.

**Git LFS capacity guard: 2026-09-21.** GitHub reported 9.01 GiB used from the
10.0 GiB included LFS allowance, with a `$0` hard budget and reset date of
2026-10-01. Post-N11 bulk evidence must therefore remain local or use a
separately approved external publication gate; it must not be staged merely
because it fits below the remaining nominal allowance. The approximately
70 MiB project inventory CSV is now a local regenerated audit artifact;
`inventory_run.json` remains the compact committed record of its checksum,
size, run identity, summary, and read-error status. Exact-path staging is
required for later notebook handoffs.

**Controlled-300 storage transition review: 2026-09-13.** Commit `694dad45`
(`n11 scaled up`) is the final approved full-output Git/LFS checkpoint for the
active rerun. Its push completed with local `HEAD` and `origin/main` aligned and
no pending LFS objects. Beginning with Notebook 12, complete canonical outputs
remain local and notebook-owned, while GitHub is restricted to the compact
scientific record and verified external publication records. The approved live
asset target is a public, structured evidence store; the final full-resolution
target is a versioned Zenodo release; and the final Controlled-300 Streamlit
application will use a separate lightweight deployment repository. The two
public Hugging Face dataset repositories are configured, and the candidates
repository passed a two-file public remote-read, byte-count, and SHA-256 smoke
test on 2026-09-12. The diagnostics repository subsequently received and
remotely verified Notebook 13's first applicable bulk metric artifact; the
Zenodo record remains incomplete. Commit
`c4f1650c` applied the approved forward-only tracking boundary: exactly 14,970
historical N12–N36 image artifacts were removed from the current `main` index,
with zero unrelated deletions. Every file remains present locally, and all
14,970 remain recoverable from `pilot-50-dashboard` and the frozen pilot tag.
No Git/LFS history was rewritten. Previously verified N12/N12A/N13/N15
publication records remain valid. A later per-file LFS upload attempt for N16
hit Hugging Face's free-account API rate limit; the user removed the partial
remote repository and the local upload cache was cleared. That failed attempt
was superseded by the separately approved, verified N16 indexed-bundle release.
N17 subsequently passed its own separate full-bundle gate. Later oversized
producers may use the same indexed-bundle approach after a producer-specific
classification, capacity check and pinned remote verification. The pre-N34
review still decides the dashboard storage and access contract.

**Local-first storage and dashboard decision: 2026-09-17.** The Controlled-50
dashboard index includes all 10,050 Notebook 16 candidate maps and all 3,270
Notebook 17 candidate maps. The present application resolves local image
paths only. The 76,020 Controlled-300 N16 maps and 27,912 N17 maps remain
locally accessible through complete manifests. After N33, before Notebook 34
refactoring, compare storage options against actual evidence sizes, quotas,
cost, case-level retrieval, and dashboard feasibility. Do not assume separate
Hugging Face datasets or any other provider. Approve the storage contract
first, then approve the dashboard scope and implementation; Notebook 35 later
validates the application. The existing diagnostics repository retains its
verified N13/N15 artifacts and later N16/N17 bundle releases; the live pilot
deployment stays unchanged.

**Bounded bundle transport test (2026-09-17).**
The user initially approved a small N16 smoke test of exact-byte indexed ZIP-member
retrieval in the existing diagnostics repository. The direct-file registry
remains authoritative for already verified N12/N12A/N13/N15 assets; a new
versioned bundle record is separate. That test preceded a separately approved
full-N16 decision; the pre-N34 storage/dashboard review gate is unchanged.
The bounded N16 test did pass public exact-byte reads for 76 images and
full-SHA-256 checks for all eight temporary remote objects. Its test prefix
was removed from the current repository branch by cleanup commit
`debc818363b5271b97e9105aa77807927e493ee7`. The smoke record is retained
under `outputs/inventory/`.

**Full indexed-bundle N16 publication (2026-09-17).** The approved release
contains all 76,034 original images in 333 bundles plus indexes, metrics, and
provenance. At pinned Hugging Face diagnostics revision
`8c22aa62c5be60d8a15c9c00d9bc9a6f81557b79`, all 641 remote objects
passed SHA-256/size validation (337 LFS hashes and 304 public reads), and four
sample images passed exact-byte public retrieval. Total published bytes:
2,625,210,541. The immutable record is
`outputs/inventory/bundled_publication_n16_full.json`. This does not alter
N16 notebook science or authorize deleting local evidence.

**Full indexed-bundle N17 publication (2026-09-18).** Its separate approved
release contains all 27,926 original images (27,912 candidate maps and 14
selected panels) in 360 bundles plus the metrics table, summary figure,
indexes, and provenance. At pinned diagnostics revision
`ceac6a5aa67fe2a0f8c840c46f22306e7f606749`, all 669 remote objects
passed SHA-256/size validation (364 LFS hashes and 305 public reads), and four
sample images passed exact-byte public retrieval. Total published bytes:
5,622,373,385. The record is
`outputs/inventory/bundled_publication_n17_full.json`. All 179 Notebook 17
validation checks remain passed; local canonical evidence is not deleted.

**Controlled-300 N18 completion review (2026-09-18).** The saved notebook has
38/38 executed code cells and no error outputs. Its completed run manifest
records 780 prompt-specific Stable Diffusion groups (480 generic and 300
scratch-aware), 3,120 candidates, 4,680 unordered pairs, 124,800 normalized
uncertainty rows, 780 calibration-input rows, two readable figures, seven
canonical files, no temporary work files, and 150/150 passing checks with no
blocking or warning failures. All seven artifact types match the E: pilot
baseline; metric rows increased from 20,800 to 124,800 and calibration rows
from 130 to 780. N18 contains no spatial heatmaps (N19 owns them), no SDXL
repeated-seed estimate, and no calibrated confidence score. Its compact Git
handoff is pending. The largest of its seven files is an approximately 81 MB
CSV already tracked in Git LFS, so N18 needs no separate HF publication.
The existing machine-readable pilot coverage YAML is not
retroactively relabelled as Controlled-300 evidence.

**Downstream scale/inference decision (2026-09-18).** The binding N19–N33
Controlled-300 population table and bounded N23–N25 statistical design are in
the roadmap Section 2.2. N19–N22 preserve full linear coverage; N23–N25 keep
all 35 paintings, seven per visual category, but replace exponential pilot
enumeration with seeded painting-cluster bootstrap and batched Monte Carlo
tests. N26's adaptive method is the starting precedent. Subsequent notebooks
scale their validated candidate/report indexes and include HINT where
applicable; bounded SDXL remains separate. Large outputs may use the verified
N16/N17 indexed-bundle publication method per producer. None of these planned
N19–N33 targets is marked complete until its own validated run exists.

**Publication rationale and dashboard boundary.** The `candidates` dataset
holds model-generated restoration images: the verified N12 SDXL and N12A HINT
candidate rows. N16 and N17 instead produce spatial, colour, texture, and seam
diagnostics, selected explanatory panels, metrics, and provenance. Their
producer-owned sibling paths therefore belong in the existing `diagnostics`
dataset; no N16/N17 release was sent to `candidates`. The earlier per-image
N16 upload exceeded the free Hub API request rate, and putting all these maps
and large tables into Git/LFS would inflate the compact scientific repository.
Indexed per-painting ZIPs reduce the number of remote objects and upload/read
requests while preserving exact original bytes. `ZIP_STORED` is deliberately
uncompressed: do not imply that bundling reduces total hosted bytes.

For the later Controlled-300 Streamlit design, the preliminary option is to
ship compact indexes, resolve a selected case/map to its pinned N16/N17 release,
download only the needed bounded bundle, verify its hash, and use a bounded
cache. Avoid whole-corpus downloads or loading N17's gigabyte-scale CSV at app
startup; precompute compact numeric views or approved on-demand partitions.
Cold/warm latency, cache/memory use, quota behavior, and missing-asset fallback
still require the explicit pre-N34 storage/dashboard review and N35 validation.
The current pilot-50 deployment is unchanged.

**Controlled-300 Notebook 12 closure review: 2026-09-13.** The bounded SDXL
scope resolved all 35 predeclared rows across 30 paintings. Twenty-four
candidates completed and passed technical validation, one timed out, and ten
were explicitly skipped after the execution guard stopped further starts. The
result remains `partial_evaluation`; runtime omissions are not quality failures.
All 241 persisted validation checks pass, all five artifact checksums match, the
30-file canonical output set is exact, and no temporary work file remains. The
ten pilot candidates retain identical IDs, paths, schema, completed status, and
restored-image bytes. Complete images remain local under the Notebook 12 output
root and enter the external publication workflow before the compact GitHub
record is committed.

## 2. Original frozen baseline and completed-pipeline protection

The completed Notebook 01–36 pilot sequence and its notebook-owned evidence are
immutable at Git tag `pilot-50-complete`. The original Notebook 01–21 common
validated data-producing baseline is repository commit `0aac25ef` (`notebook 21
done`). Later documentation and active Controlled-300 reruns do not alter the
scientific population recoverable from the tag.

Notebooks 22–36 subsequently completed their own gates and now have the same
read-only protection. They retain separate provenance rather than being folded
back into the original baseline commit.

For the tagged baseline, frozen means:

- no `.ipynb` source changes;
- no rerunning or appending to any completed Notebook 01–36 output root;
- no helper/configuration change may be used to reinterpret a frozen manifest as
  if it described a newly expanded population;
- later evidence extensions own new candidates and artifacts under their own
  notebook output roots;
- consumers join frozen and extension evidence through stable identifiers and
  explicit ownership fields.

The active working tree is an approved exception to the old blanket freeze: one
numbered notebook at a time may replace its working-tree Controlled-50 outputs
with Controlled-300 evidence under the minimal-delta rules in the implementation
guidelines and roadmap. This does not modify the tagged baseline.

The frozen validation state contains no blocking validation failure. Notebook 15
retains one declared non-blocking CUDA/CuBLAS bitwise-repeatability warning;
metric validity and coverage passed.

### 2.1 Active Controlled-300 producer ledger

| Notebook | Current working-tree evidence | Validated coverage | Pilot comparison | Downstream status |
|---|---|---:|---|---|
| 01 Dataset Verification | `artworks.v1`, `dataset_audit.v1`, two canonical figures, validation and manifests | 300 artworks; 60 in each of 5 categories; 448 audit rows; 50/50 checks | All 7 pilot artifact paths retained; table schemas and artifact roles unchanged; population-dependent rows increased for the expanded dataset | Approved Controlled-300 producer for Notebook 02 |
| 02 Image Preprocessing | `preprocessed_images.v1`, 768 × 768 clean PNG collection, preprocessing audit, canonical preview, validation and manifests | 300 clean images; 60 in each of 5 categories; 45 audit rows; 50/50 consolidated checks; 27/27 completion requirements | All 7 pilot artifact paths retained; all table schemas and artifact roles unchanged; clean-image and preprocessing-table counts increased from 50 to 300; the original 50 clean PNGs and canonical preview are byte-identical | Approved Controlled-300 geometry and clean-image producer for Notebooks 03–08 and later consumers |
| 03 Canonical Mask Generation | `canonical_masks.v1`, 1,500 binary mask PNGs, normalized morphology audit, two canonical figures, protocol, validation and manifests | 300 paintings × 5 families = 1,500 masks; 300 masks per family; 105 audit rows; 50/50 consolidated checks; 24/24 completion requirements | All 258 pilot output paths retained; the 89-column canonical schema and all artifact roles are unchanged; all 250 pilot mask PNGs are byte-identical and their key scientific rows reconcile; the 1,250 additional PNGs are exactly the five configured masks for p051–p300 | Approved Controlled-300 canonical-mask producer for Notebooks 04–06, 08, and later region-aware consumers |
| 04 Canonical Damaged Images | `canonical_damage_cases.v1`, 1,500 damaged RGB PNGs, normalized damage-integrity audit, canonical figure, validation and manifests | 300 paintings × 5 families = 1,500 cases; 300 cases per family; 1,500 audit rows; 60/60 consolidated checks; 28/28 final completion requirements | All 256 pilot output paths retained; the 34-column case and 40-column audit schemas are unchanged; all 250 pilot damaged PNGs are byte-identical; the 1,250 additional PNGs are exactly the five configured cases for p051–p300 | Approved Controlled-300 damaged-image producer for Notebook 08 and later restoration/evidence consumers |
| 05 Damage-Size Sensitivity Dataset | `damage_size_cases.v1`, 245 nested mask PNGs, 245 damaged RGB PNGs, normalized generation audit, canonical progression figure, validation and manifests | 35 paintings × 7 levels = 245 matched cases; 35 cases per level; 245 audit rows; 96/96 consolidated checks; 27/27 pre-registry completion requirements | All 76 pilot artifact paths retained; the 55-column case and 67-column audit schemas and all artifact roles are unchanged; all 70 shared pilot mask/damaged PNGs are byte-identical; output count increased from 76 to 496 through 420 additional generated images; the canonical figure changed for expanded rule-selected representatives | Approved Controlled-300 damage-size producer for Notebooks 06, 08–12, 22, 25, 28, 32, and 33 |
| 06 Mask Robustness Dataset | `mask_robustness_cases.v1`, 525 binary mask PNGs, 525 damaged RGB PNGs, normalized generation audit, canonical figure, validation and manifests | 35 paintings × 3 families × 5 variants = 525 cases; 105 groups; 525 audit rows; 102/102 consolidated checks; 21/21 completion requirements | All 156 pilot artifact paths retained; the 86-column case and 63-column audit schemas and all artifact roles are unchanged; 148/151 shared PNGs are byte-identical; the `p039` `loss_small` fourth mask/damaged variant and figure changed under helper v3.1.1 morphology enforcement; output count increased from 156 to 1,056 through 900 additional generated images | Approved Controlled-300 robustness producer for Notebooks 08–12, 24, 25, 28, 32, and 33 |
| 07 Synthetic Degradation Dataset | `synthetic_degradation_cases.v1`, 1,155 grayscale effect-support PNGs, 1,155 degraded RGB PNGs, normalized generation audit, canonical figure, protocol, validation and manifests | 35 paintings × 33 degradations = 1,155 cases; 1,050 single and 105 combined cases; 66/66 consolidated checks; 20/20 completion requirements | All 337 pilot paths retained; the 65-column case, 34-column audit, 8-column validation, and 15-column artifact schemas are unchanged; all 330 shared generated PNGs are byte-identical; all 165 pilot case and audit IDs are retained; output count increased from 337 to 2,317 through 1,980 additional generated images | Approved Controlled-300 procedural-degradation producer for Notebooks 08–12, 17, 20, 24, 25, 28, 32, and 33 |
| 08 Experiment Contracts and Region Policy | `case_registry.v1`, `model_eligibility.v1`, `region_policy.v1`, five-schema registry, canonical region figure, methodology report, validation and manifests | 3,425 cases; 17,125 case-model decisions across 5 methods; 2,620 eligible cases per method; 143 policy rows; 101/101 scientific checks; 20/20 completion requirements | All 9 pilot paths and table schemas retained; all 525 pilot case rows retained with only `dataset_scope` intentionally changed; all 2,100 shared eligibility rows unchanged; region policy byte-identical; schema definitions unchanged while producer version advances to 1.1.0 | Approved Controlled-300 contract, routing, and region-policy producer for Notebooks 09–36 and 12A |
| 09 OpenCV Telea Restoration | `restorations.v1`, 2,620 restored RGB PNGs, five-row runtime summary, eight-case representative figure, validation and manifests | 2,620 eligible cases: 1,500 canonical, 245 damage-size, 525 mask-robustness, and 350 eligible synthetic-degradation cases; 300 zero controls; 2,320 nonzero cases; 72/72 scientific checks; 15/15 roadmap requirements; 2,626 canonical files | All 416 pilot paths and CSV schemas retained; 409/410 shared restoration PNGs byte-identical; sole changed shared PNG is the inherited Notebook 06 `p039` `loss_small` fourth-variant morphology correction; representative figure byte-identical; 2,210 additional restored images explain the full file-count increase | Approved Controlled-300 deterministic Telea producer for Notebooks 13–17 and later comparison, reporting, and dashboard stages |
| 10 LaMa Restoration | `restorations.v1`, 2,620 restored RGB PNGs, five-row runtime summary, eight-case representative figure, validation and manifests | 2,620 eligible cases: 1,500 canonical, 245 damage-size, 525 mask-robustness, and 350 eligible synthetic-degradation cases; 300 zero controls; 2,320 nonzero cases; 80/80 scientific checks; 16/16 roadmap requirements; 2,626 canonical files | All 416 pilot paths and CSV schemas retained; 409/410 shared restoration PNGs byte-identical; sole changed shared PNG is the inherited Notebook 06 `p039` `loss_small` fourth-variant morphology correction; representative figure byte-identical; 2,210 additional restored images explain the full file-count increase | Approved Controlled-300 deterministic learned baseline for Notebooks 13–17 and later comparison, reporting, and dashboard stages; no generative uncertainty |
| 11 Stable Diffusion Restoration | `stable_diffusion_candidates.v1`, 8,520 restored RGB PNGs, six-row prompt policy, 14-row runtime summary, 1,355-row design table, two canonical figures, method report, validation and manifests | 8,520 completed candidates: 2,620 primary, 4,460 prompt-context, and 1,440 uncertainty-extension rows; 8,220 inferences; 300 identity controls; 300 formal scratch cases and 2,400 paired outcomes; 176/176 scientific checks; 23/23 completion requirements; 8,530 canonical files | All 10 pilot non-image paths and CSV schemas retained; 1,298/1,330 pilot candidate identities retained; 1,297/1,298 shared PNGs byte-identical; one inherited Notebook 06 morphology correction; 32 exploratory p01-p04 rows transparently displaced by expanded non-metric hash-stratified selection; both figures regenerated for expanded evidence | Approved Controlled-300 Stable Diffusion producer for Notebooks 13–21, 22, and later comparison, uncertainty, reporting, and dashboard stages; 3,260 metadata-context candidates remain exploratory |
| 12 SDXL Feasibility or Restoration | `sdxl_partial_candidates.v1`, 24 technically valid restored RGB PNGs, runtime summary, feasibility report, validation and manifests | 35 predeclared cases across 30 paintings: 24 completed and technically valid, 1 timed out, and 10 explicitly skipped; 241/241 checks; 30 canonical files | All 10 pilot candidate IDs, output paths, statuses, table schema, and restored-image bytes retained; 25 cases were added under the predeclared balanced scope; runtime omissions remain exclusions rather than quality failures | Approved bounded partial-evaluation producer for compatible downstream metrics; not a full-model benchmark and not repeated-seed uncertainty evidence |
| 12A HINT Restoration | `restorations.v1`, 2,620 restored RGB PNGs, five-row runtime summary, eight-case representative figure, validation and manifests | 2,620 completed candidates: 1,500 canonical, 245 damage-size, 525 mask-robustness and 350 eligible synthetic-degradation cases; 2,320 HINT inferences; 300 identity controls; 82/82 checks; 2,626 canonical files | New production stage with no pilot output analogue; D01 is the decision baseline and its official source revision, Places2 checkpoint, native 768 × 768 adapter, mask convention, exact compositing and outside-mask invariance contract are preserved | Approved Controlled-300 deterministic learned producer for Notebooks 13–21 and later comparison, reporting and dashboard stages; candidate evidence only, not a metric conclusion |
| 13 Classical Metrics | `classical_metrics.v1`, two canonical figures, validation and manifests | 477,753 rows across 16,404 candidates, 2,620 cases and 5 methods; 262/262 checks; 6 canonical files | All 6 pilot paths and schemas retained; rows increased from 63,018 to 477,753 and candidates from 2,160 to 16,404; no artifact class or responsibility was lost | Approved Controlled-300 classical full-reference producer for downstream metric synthesis, spatial analysis, comparison, reporting and dashboard stages |
| 14 LPIPS Metrics | `lpips_metrics.v1`, diagnostic distribution figure, validation and manifests | 31,608 rows across 16,404 candidates, 2,620 cases and 5 methods; 261/261 checks; 5 canonical files | All 5 pilot paths and schemas retained; rows increased from 4,170 to 31,608; 64 displaced pilot rows map exactly to Notebook 11's 32 approved contextual-candidate replacements | Approved Controlled-300 perceptual-distance producer for downstream comparison, robustness, failure, reporting and dashboard stages |
| 15 Feature Similarity | `feature_metrics.v1`, reusable CLIP/DINOv2 embedding bundle and manifest, diagnostic figure, validation and manifests | 63,216 metric rows and 78,336 embeddings across 16,404 candidates, 2,620 cases and 5 methods; 247 checks; 0 blocking failures; 1 declared CUDA warning; 7 canonical files | All 7 pilot paths and table schemas retained; rows increased from 8,340 to 63,216 metrics and 10,700 to 78,336 embeddings; the approved N11 displacement, inherited N06 correction, and sub-micro CUDA variation fully explain shared-row differences | Approved Controlled-300 feature-evidence and reusable-embedding producer for downstream semantic, retrieval, comparison, reporting and dashboard stages; not a conservation-specific measure |
| 16 Difference Maps and Spatial Diagnostics | `spatial_diagnostics.v1`, 76,020 candidate maps, 14 selected panels, map manifest, validation and manifests | 143,247 spatial rows across 16,404 candidates and 2,620 cases; 76,034 map-manifest rows; 137/137 checks; 76,039 canonical files | All 7 pilot artifact classes and CSV schemas retained; rows increased from 18,896 to 143,247 and candidate maps from 10,050 to 76,020 | Approved Controlled-300 spatial evidence; complete local corpus plus verified diagnostics bundle; compact Git committed |
| 17 Local Consistency Metrics | `local_consistency.v1`, texture, colour and seam metrics, 27,912 candidate maps, 14 selected panels, summary figure, validation and manifests | 2,060,667 metric rows across 16,404 candidates and 2,620 cases; 27,926 map-manifest rows; 179/179 checks; 27,932 canonical files | All 3,282 pilot map-manifest paths and CSV schemas retained; rows increased from 271,988 to 2,060,667 and candidate maps from 3,270 to 27,912 | Approved Controlled-300 consistency evidence; complete local corpus plus verified diagnostics bundle; compact Git committed |
| 18 Diffusion Uncertainty Analysis | `diffusion_uncertainty.v1`, normalized uncertainty and calibration tables, two figures, validation and manifests | 780 prompt-specific groups, 3,120 candidates, 4,680 pairs, 124,800 metric rows, 780 calibration rows, 150/150 checks, seven canonical files | Same seven pilot artifact types; metrics 20,800→124,800 and calibration 130→780; both figures visually readable | Approved and Git-committed Controlled-300 scalar uncertainty evidence; N19 owns spatial maps |
| 19 Uncertainty and Spatial Explanation Maps | `spatial_explanations.v1`, 780 raw numeric maps, 2,475 owned PNGs, 3,000 validated upstream links, normalized map index, validation and manifests | 4,680 regional rows; 6,255 map-manifest rows; 149/149 checks; 20/20 roadmap requirements; 2,481 canonical files and no temporary work files | Pilot schemas and eight artifact roles retained; all 130 shared numeric arrays and 780 shared regional means exact; 411 shared PNGs intentionally rerendered under changed global scales/layout; 14 selected-panel names replaced by expanded rule selection | Approved Controlled-300 spatial explanation producer with remotely verified diagnostics release and compact Git handoff; no combined score or calibrated confidence claim |
| 20 Semantic and Structural Consistency | `semantic_structural_metrics.v1`, `semantic_numeric_maps.v1`, 9,304 rendered panels, representative figure, normalized map index, validation and manifests | 447,312 metric rows; 63,216 numeric bundles; 72,520 map-manifest rows; 181/181 checks; 22/22 roadmap requirements; 9,311 canonical files and no temporary work files | All eight pilot paths and CSV schemas retained; rows increased from 58,980 to 447,312, numeric bundles from 8,340 to 63,216, and rendered panels from 1,090 to 9,304 | Approved Controlled-300 semantic/structural proxy producer with pinned diagnostics release and compact Git handoff; not validated face, anatomy, object, iconographic, historical, or conservation assessment |
| 21 Multi-Model Comparison | `model_comparison.v1`, `metric_disagreement.v1`, representative-case index, two figures, self-contained report, validation and manifests | 10,504 selected candidates; 277,319 comparison rows; 2,181 disagreement rows; 168 representative rows; 187/187 checks; 19/19 roadmap responsibilities; 9 canonical files and no temporary work files | All nine pilot relative paths and CSV schemas retained; comparison rows 86,531→277,319, disagreement rows 839→2,181, representative rows 76→168; both figures remain readable and the report embeds 58/58 images | Approved Controlled-300 comparison evidence; full four-method scope covers 2,620 paired cases and the five-method SDXL scope remains bounded to 24 cases; the oversized comparison table is diagnostics-tier, not a combined quality score |
| D02 Portrait Skin-Tone and Hand Restoration Audit | `portrait_anatomy_screening.v1`, `portrait_anatomy_annotations.v1`, overlap and eligible-case evidence, matched hand analysis, exploratory rendered-skin-lightness analysis, blinded review, five figures, self-contained report, validation and manifests | 60 portraits; 91 annotations; 1,265 overlap rows; 292 eligible records; 45 matched cases from 20 paintings; 1,638 hand-comparison rows; 2,760 skin-lightness rows; 32 blinded reviews; 99/99 checks; 16 canonical files | No pilot output exists because D02 is a new approved supplemental Controlled-300 analysis; continuity is enforced through immutable N01–N21 inputs and registered checksums | Approved analysis-only evidence for downstream grouped analysis, failure taxonomy, XAI, reporting and dashboard stages; rendered lightness is an image property, not race, ethnicity, identity, inherent bias, historical truth or conservation approval |

**Notebook 21 publication routing (completed).** The 152,814,687-byte
`metrics/model_comparison.csv` exceeds the approved 50 MiB bulk-diagnostic
threshold. It remains the local canonical source and is routed as a single
checksum-verified object to the existing Hugging Face `diagnostics` dataset;
it does not belong in the restoration-candidate dataset and does not require
the indexed-image bundle strategy. GitHub retains the notebook, configuration
and helper changes, disagreement and representative tables, both figures, the
self-contained report, validation and run/artifact manifests, inventory, and
the external-publication registry. The remote object is published and verified
at commit `40b155f281e01c4693e983e15cc975d1b722f6bc`, with the recorded
152,814,687-byte size and SHA-256
`a55a1b41f05639bde954d59f974550137d4bc6eae5a4acd73dc7c806fc4cd76b`.

**D02 completion and publication routing.** D02 completed under run
`run_fdbd2ed6e93b4d709f5439af028a7600`. All 37 code cells are executed, the
notebook contains no saved error output, all 99 validation checks and 13
roadmap responsibilities pass, all 14 registered artifact checksums match, and
the output root contains exactly 16 canonical files with no work directory.
The five RGB PNG figures passed structural and visual inspection. The
28,222,966-byte report embeds 20 images and 17 complete CSV downloads with no
external image dependency. D02 has no E: pilot counterpart. Its complete
41,642,918-byte output root has no artifact above the 50 MiB publication
threshold, so it belongs in the compact GitHub/Git-LFS handoff; no separate
Hugging Face candidates or diagnostics publication is required.

**Notebook 19 publication routing (local and pinned remote gates passed).**
The complete local root is authoritative. Do not interpret 3,000 upstream-link
rows as Notebook 19-owned files or republish their bytes under N19. The 2,475
owned PNGs span all 300 paintings and total 1,284,143,895 bytes. Their
producer-specific indexed release is in Hugging Face `diagnostics`, not
`candidates`. Its pinned revision `e080704d57d2a10ebe09d0395f348b9da85ea8f7`
passed SHA-256/size verification for all 609 remote objects (1,329,281,895
bytes) and exact public reads of four sample images. The publication record is
`outputs/inventory/bundled_publication_n19_full.json`. GitHub keeps
the notebook, helper/configuration changes, the 780-entry 27.4 MiB numeric
archive, 4,680-row metric CSV, 6,255-row map index, 15 selected panels,
validation, run/artifact manifests, inventory, and the pinned publication
record. The 2,460 PNGs under `images/` are ignored by Git and remain locally
canonical; their remote release is now verified. The 15 selected
panels are retained both in the compact Git scientific record and in the
verified diagnostics release for self-contained public reading.

**Notebook 20 publication routing.** The complete local root contains 9,304
owned semantic-panel PNGs (13,567,464,318 bytes), a 63,216-entry numeric archive,
447,312 metric rows, a 72,520-row map manifest, the representative figure, and
validated provenance. These are derived diagnostics and therefore route to
the Hugging Face `diagnostics` repository. The complete release is remotely
verified at revision `8f849ea89e0fa6cabf309481d63c44bb3878edc3`, prefix
`bundled_assets/v1/controlled_300/20_semantic_and_structural_consistency/b29a25d740c9dea4`.
The destination is `RahulMaddineni264/painting-restoration-eval-diagnostics`,
not the restoration-candidate dataset. The indexed-bundle release preserves producer
paths, identities, sizes, hashes, and a pinned remote revision. GitHub retains
the compact scientific/control-plane artifacts and final publication record;
the complete local root remains authoritative.

| N19 canonical family | Local output | GitHub | Hugging Face |
|---|---:|---|---|
| Numeric uncertainty NPZ | 780 maps; 27.4 MiB | Yes, Git LFS | Diagnostics release may include the validated archive copy |
| Regional metric table | 4,680 rows; 4.6 MiB | Yes | Diagnostics release may include a provenance copy |
| Uncertainty and overlay images | 780 + 780 PNGs | No (`images/` ignored) | Diagnostics indexed bundles |
| Scratch-aware texture, colour, seam | 900 PNGs | No (`images/` ignored) | Diagnostics indexed bundles |
| Selected explanation panels | 15 PNGs | Yes | Diagnostics indexed bundles |
| Map, artifact, validation, run manifests | 6,255 + 8 + 149 rows and one JSON | Yes | Diagnostics provenance/index copies |

The E: pilot contains 431 canonical files versus 2,481 now. Its 130 shared
raw maps are exactly equal after loading, and its 780 shared regional mean
rows are exactly equal. All 411 shared PNG paths have different bytes because
the controlled-300 population changed global presentation scales, while the
selected-panel layout and representative selection changed. Fourteen
pilot-only panel filenames are superseded by new rule-selected paintings;
all 15 panel roles and five-per-role coverage remain. CSV column schemas and
all eight artifact roles remain unchanged.

Notebook 01's final manifest records `controlled_300`, dataset version `2.0.0`,
300 expected and observed artwork/image rows, 448 expected and observed audit
rows, five artifact records, two figures, and a passed completion gate. The
read-only artifact comparison copy is `E:/outputs/01_dataset_verification/`;
the authoritative recovery source remains Git tag `pilot-50-complete`.

The audit increase from 101 to 448 rows is wholly in distribution evidence:
the expanded registry contains more recorded dates/periods, styles/periods,
media, licences, and institutional sources. Validation remains 50 rows because
that table counts invariant checks rather than paintings.

Notebook 02's final manifest records `controlled_300`, dataset version `2.0.0`,
preprocessing version `2.1.0`, 300 expected and observed preprocessing rows and
clean PNGs, 45 audit rows, 50 consolidated validation rows, five artifact
records, one canonical preview, and a passed completion gate. Its output root
contains exactly 306 files, compared with 56 in the pilot. The 250-file increase
is entirely the additional clean-image population; audit, validation, manifest,
and figure cardinalities remain invariant. The read-only artifact comparison
copy is `E:/outputs/02_image_preprocessing/`.

All 50 pilot clean PNGs match the active outputs byte for byte, and the canonical
preview is also byte-identical. The additional ICC evidence is handled by the
approved colour policy: 261 missing profiles use the documented sRGB assumption,
19 embedded sRGB profiles preserve pixels, 20 embedded non-sRGB profiles are
converted to sRGB, and no output PNG retains an ICC profile. Recorded content
bounds remain the authoritative way for downstream notebooks to exclude padding.

Notebook 03's final manifest records `controlled_300`, dataset version `2.0.0`,
mask configuration version `1.1.0`, mask helper version `3.1.0`, and stable mask
generator version `3.0.0`. Expected and observed counts reconcile at 300 paintings,
five mask families, 1,500 canonical rows and PNGs, 105 audit rows, 50 consolidated
validation rows, seven artifact records, two figures, and one methodology report.
The output root contains exactly 1,508 files, compared with 258 in the pilot; the
1,250-file increase is wholly the added p051–p300 mask population. All 1,500 masks
passed saved-file validation and deterministic replay, with no missing, stale,
orphaned, duplicate, cross-family-equivalent, non-binary, padding-overlap, area,
or morphology failures. The read-only comparison copy is
`E:/outputs/03_canonical_mask_generation/`.

Seed-scheme continuity was intentionally preserved: the first 250 mask PNGs are
byte-identical to the pilot, and all compared pilot rows retain their mask IDs,
paths, checksums, damaged-pixel evidence, seeds, retries, and generation attempts.
The larger morphology figure now summarizes 300 masks per family, while the
deterministic representative example is selected from the expanded population.

Notebook 04's final manifest records `controlled_300`, dataset version `2.0.0`,
canonical-damage configuration version `1.1.0`, damage helper version `3.1.0`,
and stable pixel-generator version `3.0.0`. Expected and observed counts
reconcile at 300 paintings, five mask families, 1,500 canonical case rows and
damaged PNGs, 1,500 damage-audit rows, 60 consolidated validation rows, five
artifact records, one canonical figure, and a passed completion gate. The output
root contains exactly 1,506 files, compared with 256 in the pilot; the 1,250-file
increase is wholly the added p051–p300 damaged-image population. All 1,500 saved
images passed reload, format, geometry, checksum, outside-mask preservation,
inside-mask fill, and changed-pixel reconciliation checks, with no missing,
stale, orphaned, duplicate, temporary, or undeclared outputs. The read-only
comparison copy is `E:/outputs/04_canonical_damaged_image_generation/`.

All 250 pilot damaged PNGs are byte-identical to the active outputs. The pilot
case and audit rows differ only in the intended dataset version/scope and, for
the case table, configuration version; their stable identifiers, paths,
checksums, geometry, fill policy, pixel counts, and validation evidence remain
unchanged. The canonical figure retains its path and role but now uses p085 as a
deterministic representative from the expanded population, so figure-byte
identity is neither expected nor claimed.

Notebook 05's final manifest records `controlled_300`, dataset version `2.0.0`,
damage-size configuration schema `damage_size_sensitivity_config.v2`, and
generator/helper version `3.1.0`. Expected and observed counts reconcile at 35
explicitly pinned paintings, seven balanced paintings per visual category,
seven nested levels, 245 case rows, 245 mask PNGs, 245 damaged PNGs, 245 audit
rows, 96 consolidated validation rows, six artifact records, one canonical
figure, and 27 passed pre-registry completion requirements. The output root
contains exactly 496 files, compared with 76 in the pilot. The 420-file increase
is exactly 210 additional masks plus 210 corresponding damaged images. The
read-only comparison copy is
`E:/outputs/05_damage_size_sensitivity_dataset_generation/`.

All 70 pilot-generated PNGs shared by the two runs are byte-identical. The
55-column case schema, 67-column audit schema, 8-column validation schema,
15-column artifact schema, all six artifact paths, seven target levels, and five
original pilot anchors are preserved. For the 35 shared case rows, differences
are confined to the intended dataset version/scope and declared generator or
configuration versions. The progression figure retains its path and reporting
role but now uses p157, p259, and p073 as the independently derived minimum,
median, and maximum content-area representatives within the 35-painting cohort;
therefore figure-byte identity is neither expected nor claimed.

Notebook 06's final manifest records `controlled_300`, dataset version `2.0.0`,
mask-robustness configuration schema `mask_robustness_config.v2`, configuration
version `2.0.1`, and generator/helper version `3.1.1`. Expected and observed
counts reconcile at 35 explicitly pinned paintings, seven balanced paintings per
visual category, three mask families, five variants per group, 105 robustness
groups, 525 case rows, 525 mask PNGs, 525 damaged PNGs, 525 audit rows, 102
consolidated validation rows, six artifact records, one canonical figure, and 21
passed completion requirements. No case or group failed. The output root contains
exactly 1,056 files, compared with 156 in the pilot; the 900-file increase is
exactly 450 additional masks plus 450 corresponding damaged images. The
read-only comparison copy is
`E:/outputs/06_mask_robustness_dataset_generation/`.

All 156 pilot artifact paths and the 86-column case, 63-column audit, 8-column
validation, and 15-column artifact schemas are preserved. Of the 151 shared PNG
paths, 148 are byte-identical. The three intentional differences are the `p039`
`loss_small` fourth mask variant, its corresponding damaged image, and the
canonical figure that displays the corrected output. Helper v3.1.1 enforces the
configured multi-component morphology for every generated `loss_small`
candidate, closing the late-group failure found during the expanded run. This
dataset varies input mask placement, geometry, and component arrangement; its
independent unit remains the painting-mask-family group, and its evidence is
input robustness rather than generative uncertainty.

Notebook 07's final manifest records `controlled_300`, dataset version `2.0.0`,
synthetic-degradation configuration schema `synthetic_degradation_config.v2`,
generator/helper version `2.1.0`, and the shared balanced 35-painting cohort used
by Notebooks 05–07. Expected and observed counts reconcile at 1,050 single cases,
105 combined cases, 1,155 case rows, 1,155 effect-support masks, 1,155 degraded
images, 1,155 generation-audit rows, 66 consolidated validation rows, seven
artifact records, one canonical figure, one protocol, and 20 passed completion
requirements. No case, checksum, declared path, or validation check failed. The
output root contains exactly 2,317 files, compared with 337 in the pilot; the
1,980-file increase is exactly 990 added effect-support masks plus 990 matching
degraded images. The read-only comparison copy is
`E:/outputs/07_synthetic_degradation_dataset_generation/`.

All 337 pilot paths remain available. The 330 shared generated PNGs are
byte-identical, both canonical tables preserve their schemas, and all 165 pilot
case and audit identities remain present. The expanded figure and protocol
describe the larger cohort without changing the scientific boundary: these are
controlled RGB-domain proxies, effect masks encode operator influence rather
than missing pixels, severity is ordinal rather than a conservation-condition
grade, and model eligibility remains owned by Notebook 08.

Notebook 08's final manifest records `controlled_300`, dataset version `2.0.0`,
evaluation-contract configuration version `2.0.0`, contract-helper version
`1.1.0`, and canonical-region helper version `1.1.0`. Expected and observed
counts reconcile at 3,425 registered cases, 17,125 explicit case-model routing
decisions, 13,100 eligible decisions, 4,025 ineligible decisions, five models,
143 metric-region policy rows, five schema records, 101 consolidated scientific
checks, seven artifacts, and nine output files. All 20 roadmap requirements and
the final completion gate passed. The read-only comparison copy is
`E:/outputs/08_experiment_contracts_and_region_policy/`.

All nine pilot artifact paths and all CSV schemas are retained. The 525 shared
case rows preserve every stable field; only `dataset_scope` changes intentionally
from `controlled_50` to `controlled_300`. All 2,100 shared eligibility rows are
identical, the 143-row region policy is byte-identical, and the five schema
definitions are unchanged apart from the registry producer version. The larger
case and eligibility tables therefore represent explained population growth,
not a change to the approved routing or spatial methodology. SDXL remains a
bounded 35-case execution despite full methodological eligibility, while HINT is
the selected additional learned method for the complete eligible population.

Notebook 09's final manifest records `controlled_300`, dataset version `2.0.0`,
OpenCV Telea configuration version `2.0.0`, and restoration generator version
`3.0.0`. Expected and observed counts reconcile at 2,620 eligible and completed
restorations: 1,500 canonical, 245 damage-size, 525 mask-robustness, and 350
eligible synthetic-degradation cases. The population contains 300 exact
identity/no-op controls and 2,320 nonzero masks. All 72 consolidated scientific
checks, seven persistence checks, five manifest-handoff checks, four registry
checks, six final checks, and 15 roadmap requirements passed. The output root
contains 2,620 restored images and six canonical non-image artifacts, for 2,626
non-empty canonical files and no remaining work files. The recorded restoration
runtime is 1,446.741 seconds; this is environment-specific evidence, not a
universal speed benchmark. The read-only comparison copy is
`E:/outputs/09_opencv_telea_restoration/`.

All 416 pilot paths are retained, all four CSV schemas are unchanged, and the
representative figure is byte-identical. Of the 410 shared restoration PNGs,
409 are byte-identical. The sole changed path is
`images/restored/mask_robustness/mask_robustness__p039__loss_small__target_04p5pct__variant_04.png`;
that difference is inherited from Notebook 06 helper v3.1.1's documented
morphology correction. The remaining 2,210 added files are exactly the
additional Controlled-300 restoration images, so there is no unexplained loss
or reduction of pilot evidence.

Notebook 10's final manifest records `controlled_300`, dataset version `2.0.0`,
LaMa configuration version `2.0.0`, restoration helper version `3.1.0`, and
IOPaint version `1.6.0`. Expected and observed counts reconcile at 2,620 eligible
and completed restorations: 1,500 canonical, 245 damage-size, 525 mask-robustness,
and 350 eligible synthetic-degradation cases. The population contains 300 exact
identity/no-op controls and 2,320 nonzero masks. All 80 consolidated scientific
checks, seven persistence checks, five manifest-handoff checks, four registry
checks, eight final checks, and 16 roadmap requirements passed. The output root
contains 2,620 restored images and six canonical non-image artifacts, for 2,626
non-empty canonical files and no remaining work files. Full execution took
4,594.223 seconds (about 76.6 minutes); the normalized allocated runtime evidence
totals 3,570.487 seconds. Both are environment-specific rather than universal
speed benchmarks. The read-only comparison copy is
`E:/outputs/10_lama_restoration/`.

All 416 pilot paths are retained, all four CSV schemas are unchanged, and the
representative figure is byte-identical. Of the 410 shared restoration PNGs, 409
are byte-identical. The sole changed path is
`images/restored/mask_robustness/mask_robustness__p039__loss_small__target_04p5pct__variant_04.png`;
that difference is inherited from Notebook 06 helper v3.1.1's documented
morphology correction. The remaining 2,210 added files are exactly the additional
Controlled-300 restoration images, so there is no unexplained loss or reduction
of pilot evidence.

Notebook 11's final manifest records `controlled_300`, dataset version `2.0.0`,
8,520 completed candidate records and restored RGB PNGs, 8,220 Stable Diffusion
inferences, and 300 identity controls. The execution roles reconcile at 2,620
primary, 4,460 prompt-context, and 1,440 uncertainty-extension rows. The formal
scratch experiment covers all 300 paintings, four seeds, two prompt arms, 1,200
painting-seed pairs, and 2,400 outcomes. All 176 consolidated scientific checks,
nine persistence checks, five manifest-handoff checks, four registry checks,
seven final checks, and 23 completion requirements passed. The output root
contains 8,520 restored images and ten canonical non-image artifacts, for 8,530
canonical files and no remaining work files. The normalized runtime evidence
totals 71,737.586 seconds (about 19.93 hours); it is environment-specific rather
than a universal speed benchmark.

The read-only comparison copy is
`E:/outputs/11_stable_diffusion_restoration/`. All ten pilot non-image paths and
all CSV schemas remain present. The expanded deterministic design retains 1,298
of 1,330 pilot candidate identities, with 1,297 of the shared restored PNGs
byte-identical. The sole changed shared PNG is the inherited Notebook 06 `p039`
`loss_small` fourth-variant morphology correction. The 32 non-retained pilot
rows are exclusively exploratory p01-p04 prompt-context candidates displaced by
the approved non-metric hash-stratified selection over the expanded population.
No primary, formal scratch-pair, or base uncertainty responsibility was lost.
Both canonical figures were regenerated from expanded rule-selected evidence.

Notebook 12A's final manifest records `controlled_300`, dataset version `2.0.0`,
HINT configuration version `1.0.0`, and helper version `1.0.1`. All 2,620
eligible cases completed: 1,500 canonical, 245 damage-size, 525 mask-robustness,
and 350 eligible synthetic-degradation candidates. The run contains 2,320 HINT
inferences and 300 exact identity controls, 82 passing validation checks, five
artifact records, 2,620 restored PNGs, and exactly 2,626 canonical files with no
remaining work files. Its normalized allocated runtime is 16,025.750 seconds
(about 4.45 hours). N12A has no pilot output counterpart; D01 is the decision
baseline, and the official revision, Places2 checkpoint, native 768 x 768
adapter, exact-mask compositing, and outside-mask invariance contract were
preserved.

Notebook 13's final manifest records `controlled_300`, 16,404 evaluated
candidates, 2,620 cases, and 477,753 `classical_metrics.v1` rows. Metric counts
reconcile at 143,247 rows each for MSE, MAE, and PSNR and 48,012 SSIM rows.
Coverage is 2,620 candidates each for Telea, LaMa, and HINT, 8,520 Stable
Diffusion candidates, and 24 technically valid SDXL candidates. All 1,200 zero
controls and their 13,200 metric rows are retained. All 262 validation checks
passed, four downstream artifacts were registered, the two figures are valid,
the six-file output contract is exact, and no work file remains. Batch 4 took
28,705.153 seconds (about 7 h 58 m), below its conservative 18–30 hour planning
range.

The read-only comparison copy is `E:/outputs/13_classical_metrics/`. Both runs
contain the same six canonical relative paths and preserve the metric,
validation, artifact, and figure schemas. Candidate coverage increased from
2,160 to 16,404, metric rows from 63,018 to 477,753, and validation rows from
251 to 262. These increases are fully explained by the controlled-300
population, HINT inclusion, and expanded SDXL evidence; no pilot artifact class
or scientific responsibility is missing or reduced.

The canonical `classical_metrics.csv` table is approximately 144 MB and therefore crosses the approved 50 MiB bulk-diagnostic threshold. It remains the local Notebook 13 source of truth and has been published and remotely verified in the Hugging Face diagnostics repository. It is excluded from the compact GitHub scientific record. The Notebook 13 manifest, validation evidence, figures, notebook, and inventory/publication registries remain on GitHub.

Notebook 14's final manifest records `controlled_300`, 16,404 evaluated
candidates, 2,620 cases, and 31,608 `lpips_metrics.v1` rows. Coverage is 4,940
rows each for OpenCV Telea, LaMa, and HINT, 16,740 Stable Diffusion rows, and 48
rows for the 24 technically valid SDXL candidates. Region totals reconcile at
16,404 content-region and 15,204 mask-bounding-box rows. All 1,200 zero-control
candidates and all 2,400 matched scratch-prompt regional pairs are retained.
All 261 validation checks passed, three downstream artifacts were registered,
the diagnostic figure is valid and readable, the five-file output contract is
exact, and no work file remains. Full checkpointed execution took 3,341.795
seconds (about 55.7 minutes).

The read-only comparison copy is `E:/outputs/14_lpips_metrics/`. Both runs
contain the same five canonical relative paths and preserve the metric,
validation, and artifact table schemas. Candidate coverage increased from
2,160 to 16,404, metric rows from 4,170 to 31,608, and validation rows from 253
to 261. The expanded design retains 4,106 of 4,170 pilot metric identities. The
64 non-retained rows are exclusively the two-region LPIPS records belonging to
the 32 exploratory Stable Diffusion context candidates intentionally displaced
by Notebook 11's approved expanded hash-stratified selection. Recomputed
shared-row differences otherwise reflect expected LPIPS floating-point
variation plus the already documented Notebook 06 `p039` morphology correction;
they do not represent a missing evidence family.

Notebook 14's approximately 13.9 MB canonical metric table is below the approved
50 MiB bulk-diagnostic threshold. Its five compact canonical artifacts therefore
remain in the GitHub scientific record and produce no Notebook 14 Hugging Face
publication rows.

Notebook 15's final manifest records `controlled_300`, 2,620 evaluated cases,
16,404 candidates, 31,608 candidate-region evaluations, 63,216 CLIP/DINOv2
metric rows, and 78,336 reusable embedding records. The candidate population is
2,620 rows each for OpenCV Telea, LaMa, and HINT, 8,520 Stable Diffusion rows,
and 24 technically valid SDXL rows. All 4,800 scratch-prompt paired comparisons
are retained. The 247 validation checks contain zero blocking failures and one
declared warning: CUDA/CuBLAS execution is best-effort deterministic, so exact
bitwise rerun identity is not asserted. Metric validity, completeness, finite
values, persistence, and the final completion gate all passed. The output root
contains exactly seven canonical files, five registered downstream artifacts,
one valid diagnostic figure, and no temporary work files. Full feature
extraction took 6,270.909 seconds (about 1 h 44 m 31 s), followed by 199.564
seconds (about 3 m 20 s) of metric construction.

The read-only comparison copy is `E:/outputs/15_feature_similarity/`. Both runs
contain the same seven canonical relative paths and preserve all relevant table
schemas. Metric rows increased from 8,340 to 63,216 (7.58×), and embedding rows
increased from 10,700 to 78,336 (7.32×). The active run retains 8,212 shared
metric identities; the 128 displaced pilot identities correspond exactly to
the 32 exploratory Stable Diffusion context candidates replaced under Notebook
11's approved expanded selection. Twelve non-bit-identical shared rows inherit
the documented Notebook 06 `p039` morphology correction. Six more differ only
by `1.19209289550781e-07`, which is consistent with the declared best-effort
CUDA floating variation. No unexplained artifact, schema, or evidence family is
missing.

The canonical `embeddings.npz` bundle is approximately 111.9 MB and exceeds the
approved 50 MiB bulk-diagnostic threshold. It remains authoritative locally and
is classified for checksum-verified publication in the Hugging Face diagnostics
repository. The approximately 44.9 MB embedding manifest and 40.0 MB feature
metric table remain below the threshold and stay in the compact GitHub
scientific record together with the figure, validation, manifests, notebook,
and external-publication registry.

## 3. Frozen notebook evidence ledger

This table preserves the historical Controlled-50 evidence at
`pilot-50-complete`. Where a producer has completed its Controlled-300 rerun,
Section 2.1 and the machine-readable transition ledger describe the active
working-tree artifact instead.

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
approved missing-evidence generation extension. Its Controlled-50 pilot
completed at commit `547a8687` (`notebook 22 done`) with its completion gate
passed. Controlled-300 run `run_d0276a6859f74fada266936f43b7499f` now
supersedes that pilot as active evidence while retaining the E: copy for
continuity comparison.

The completed Controlled-300 run:

- reference the 245 validated Notebook 11 generic seed-2026 damage-size candidates;
- generate seeds 2027–2029 for the same 245 cases;
- own exactly 735 new restoration images;
- construct 245 complete four-seed uncertainty groups and 1,470 unique unordered
  seed pairs;
- persist 33,320 transparent RGB, LPIPS, CLIP, DINOv2, regional, pairwise, and
  reference-evidence metric rows plus 245 raw uncertainty maps and 245 overlays;
- preserved the exact four-seed and frozen-anchor contracts;
- passed all 236 validation checks and all 12 roadmap requirements with no
  blocking or warning failures;
- produced 988 canonical files with no temporary work files; and
- left every Notebook 01–21 source and output untouched.

The historical pilot record contained 35 groups, 105 new restorations, 210
pairs, 4,760 metric rows, 35 raw maps, 35 overlays, 234 passing checks, and 148
files. The active run has the same ten artifact roles and schemas; every
case-dependent count increased exactly sevenfold and the two additional checks
cover the expanded scope. The summary figure and representative 2%, 10%, and
20% overlays passed visual review.

Notebook 23 used this evidence to test generative uncertainty against target and
realized damage size. Notebook 18 remains the canonical uncertainty source for
its original canonical-case population; Notebook 22 is the canonical source for
damage-size uncertainty and is now a read-only approved upstream dependency.
Its complete 988-file tree remains authoritative locally. Git excludes the 980
generated PNGs and the 35.7 MiB numerical-map archive. The approved N22
publication contract separates 735 restoration PNGs into 35 indexed bundles in
the Hugging Face `candidates` dataset and 245 overlays plus the numerical map
archive into 35 indexed bundles and sidecars in `diagnostics`. Separate pinned
remote verification records must pass before either tier is represented as
published; local canonical evidence is retained through the pre-N34 audit.

The historical Controlled-50 run of Notebook 23,
`23_damage_size_sensitivity_analysis.ipynb`, completed the pilot damage-size
analysis with its pilot completion gate passed. It:

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

That historical run remains the pilot baseline only. Controlled-300 run
`run_e93288fc3ac847ccb699241b4b4c8be0` is now canonical: it analyzes 35
painting trajectories, 245 cases, 980 primary candidates across Telea, LaMa,
HINT and Stable Diffusion, and 245 Stable Diffusion uncertainty groups. It
persisted 7,035 unique analysis rows, including 494 inferential rows, three
canonical figures, and a self-contained report with 10 analytical views, eight
visual panels, 110 panel tiles, 18 embedded images and no external images. All
124 validation checks and 10 roadmap responsibilities passed. The eight pilot
artifact paths and schemas are retained; analysis rows increased from 1,901 to
7,035. Inference used 5,000 seeded cluster-bootstrap draws and 100,000 seeded
batched sign flips with the +1 correction rather than infeasible exhaustive
enumeration. Downstream
consumers must preserve target and realized exposure definitions, painting as
the independent unit,
metric-family disagreement, and the boundary that empirical Stable Diffusion
seed variability is not calibrated confidence. The analysis does not estimate
independent category or style effects and does not establish a universal damage
threshold or conservation approval.

Notebook 24, `24_mask_robustness_analysis.ipynb`, completed Controlled-300 run
`run_bbf68684c3ca47e5827c2b8b4b666351` with its completion gate passed. The
validated evidence comprises:

- 35 paintings balanced at seven per broad visual category, three fixed
  family–area conditions, 105 matched groups, five variants per group, 525 cases,
  and 2,100 preselected primary candidates from OpenCV Telea, LaMa, HINT and
  Stable Diffusion Inpainting;
- all 11 quality anchors retained descriptively, with the seven predeclared
  anchors used for bounded confirmatory inference;
- 44,847 unique canonical analysis rows, 139/139 passing validation checks,
  nine completed roadmap responsibilities, two reviewed figures, and a
  self-contained report containing 18 embedded images, 100 visual tiles and no
  external image dependency;
- 5,000 seeded painting-cluster bootstrap draws and 100,000 seeded batched
  sign flips with the +1 correction instead of infeasible exhaustive enumeration;
- the same seven canonical artifact paths and table schemas as the historical
  Controlled-50 baseline, with analysis rows increasing from 5,373 to 44,847.

Downstream consumers must preserve metric-family disagreement and the distinction between input-mask robustness
and stochastic candidate uncertainty. Low dispersion does not establish quality,
historical authenticity, or conservation approval; runtime remains operational.
The `scratch_thin`, `loss_small`, and `loss_large` families remain paired with
target damaged fractions of 2%, 4.5%, and 12.5%, so independent family and
damage-size effects cannot be separated. The 52.16 MB scalar table is
diagnostics-tier evidence; compact figures, report, manifests, validation and
the pinned external-publication record belong in the GitHub scientific handoff.

Notebook 25, `25_synthetic_degradation_analysis.ipynb`, completed Controlled-300
run `run_cf89ebe972364c7b8ccfefc6bf2a63ca` with its completion gate passed. The
historical Controlled-50 baseline contained 165 generated cases, 50 eligible
cases, 150 three-method primary candidates, six SDXL cases, 4,695 analysis rows,
125 passing checks and seven canonical files. The validated Controlled-300
evidence comprises:

- all 1,155 Notebook 07 procedural cases audited while restricting restoration
  comparison to the 350 localized cases approved by Notebook 08;
- 1,400 primary candidates analyzed, comprising 350 each for OpenCV Telea, LaMa,
  HINT and primary generic-prompt Stable Diffusion;
- the 11 completed synthetic-degradation SDXL candidates retained as a separate
  bounded five-method descriptive subset;
- all 11 quality anchors kept separate across 34,977 canonical rows and the
  same 17 analysis kinds, without a combined quality, efficiency,
  uncertainty or trust score;
- the 35 paintings treated as independent clusters, with cases, severities,
  models, anchors and candidates repeated or nested within paintings;
- pilot exhaustive enumeration replaced with 5,000 seeded batched
  painting-cluster bootstrap draws and 100,000 seeded batched sign flips using
  the +1 correction;
- eligibility exclusions, degradation-family and configured-severity
  analyses, affected-area evidence, paired contrasts, ordered combined-component
  comparisons, failure profiles, spillover, family-balanced ranks and runtime
  preserved;
- all seven canonical artifact paths and all three CSV schemas preserved against
  `E:`, with 129/129 passing checks and no blocking or warning failures;
- a self-contained 15-section report containing 14 analytical views, nine visual
  panels, 23 embedded images, 298 tiles and no external image dependency.

Notebook 25 does not support independent art-historical style
effects, exact physical degradation interactions, full-population SDXL claims,
historical authenticity, conservation approval, or synthetic-degradation
uncertainty. Procedural RGB effects remain controlled proxies rather than exact
simulations of material aging or treatment.

The 41.97 MB canonical analysis table is diagnostics-tier evidence and follows
the bounded external-artifact publication route. The two figures, self-contained
report, manifests and validation table form the compact GitHub handoff. The
complete local seven-file tree remains canonical.

Notebook 26, `26_grouped_and_statistical_analysis.ipynb`, completed its
Controlled-300 rerun as run `run_efc978dd6d504cdb9b138a750f6dca83`. The
completed Controlled-50 run remains a historical comparison baseline: 1,230
core candidates across 410 cases, ten bounded SDXL candidates, 165 uncertainty
groups, 4,174 statistical rows, 504 correlation rows, 258 ranking rows, 111
passing checks, three figures, and a self-contained report.

The completed Controlled-300 run:

- selects 10,480 metric-independent primary candidates across 2,620 cases:
  2,620 each for OpenCV Telea, LaMa, HINT and primary generic-prompt Stable
  Diffusion;
- keeps 1,200 canonical zero-control candidates as integrity evidence and uses
  9,280 nonzero full-method candidates for restoration-quality inference;
- keeps the 24 technically valid SDXL candidates as a separate bounded,
  descriptive population;
- normalizes 3,150,114 validated quality-evidence rows while retaining all 11
  quality anchors as separate measurements;
- combines 780 canonical and 245 damage-size prompt-specific repeated-seed
  groups without mixing generic and scratch-aware prompt arms or assigning
  artificial uncertainty to deterministic robustness/degradation evidence;
- consumes the complete 7,035-row damage-size, 44,847-row mask-robustness and
  34,977-row synthetic-degradation analysis tables;
- keeps painting as the independent unit and cases, candidates, masks, seeds,
  regions, metrics and trajectories as repeated or nested observations;
- retains bounded 5,000-draw painting-cluster bootstrap and 100,000-assignment
  Monte Carlo sign-flip procedures instead of infeasible exhaustive enumeration.

It produced 13,272 statistical-result rows, 694 correlation rows, 1,344
ranking-stability rows, three canonical figures, a self-contained report with
48 embedded images and 252 visual tiles, and 111/111 passing checks. All ten
pilot artifact paths and all eight registered artifact roles and schemas match.
The complete output tree is approximately 13.5 MiB and contains no large
producer-owned candidate or diagnostic-image collection, so Notebook 26 uses a
compact GitHub handoff and requires no separate Hugging Face release.

Notebook 26 is now the canonical Controlled-300 grouped-statistics source.
Consumers must preserve metric-family and region-policy disagreement,
prompt-arm separation, the single-dataset limitation, and the distinction
between empirical seed variability and calibrated confidence. Runtime remains
operational evidence outside quality ranking. The analysis cannot establish an
independent art-historical style effect, a between-dataset comparison, a full SDXL
comparison, historical authenticity, conservation suitability, museum approval,
or a universal quality or trust score.

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

The preceding paragraph is now the historical Controlled-50 baseline. Notebook
27 run `run_bef567ee35c1409dbcecfb71f1b4f8b4` is the canonical Controlled-300
source: 10,504 primary candidates, 4,100 candidate memberships in 1,025 complete
supported four-seed groups, a manifest-derived overlap of 725 candidates, 3,375
uncertainty-only candidates, and 13,879 unique candidates. HINT joins Telea,
LaMa, and primary Stable Diffusion as the fourth full primary method; 24 valid
SDXL candidates remain bounded descriptive evidence. The run persists 194,306
candidate-by-category rows and 152,669 candidate-by-flag rows, retains all eight
pilot paths and six artifact roles, and passes all 167 checks. Its two bulk
metric tables are diagnostics-tier Hugging Face artifacts because Git LFS is
hard-capped; the compact taxonomy, figure, report, manifests, validation ledger,
and verified publication record remain the GitHub scientific handoff.

The historical Controlled-50 Notebook 28,
`28_metric_and_region_policy_ablation.ipynb`, completed the original
evaluation-policy sensitivity analysis with its completion gate passed. It:

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

These values remain the frozen pilot baseline. Controlled-300 run
`run_4325bb483fbc4ccda670df125c40731d` is now the active Notebook 28 record. It
retained the same 23 named scenarios and eight output paths while expanding the
matched ranking grid to 2,620 cases and four core methods (Telea, LaMa, HINT,
and Stable Diffusion), the Notebook 27 flag population to 13,879 candidates,
and bounded SDXL diagnostics to the 24 completed feasibility candidates. It
persisted exactly 72 model-rank rows, 47,160 case-rank rows, 253
scenario-by-flag rows, 23 scenario summaries, 47,508 ablation-result rows, and
319,217 candidate-by-scenario flag-stability rows.

LaMa remained a winner in all 18 ranking-applicable scenarios, including a
transparent LaMa–Telea tie under the classical-only policy. This stable
model-level conclusion did not make case priorities or operational flags
policy-invariant: evidence-family removal, restricted region policies,
threshold changes, and aggregation changes produced substantial candidate-level
movement and explicit insufficient-evidence states. Lower flag counts produced
by removed evidence are not interpreted as improved restoration quality.

The run passed all 122 checks and all 13 roadmap responsibilities, registered
six checksum-matching non-self-referential artifacts, retained exactly eight
canonical files, and left no work files. Its self-contained twelve-section
report contains five analytical views, six diagnostic panels, 24 four-method
tiles, 29 embedded images, and zero external image dependencies. The observed
execution window was approximately 12 hours 20 minutes. The 165.21 MB
flag-stability table is diagnostics-tier Hugging Face evidence under the
exhausted-LFS guard; the 18.05 MB ablation table, figures, report, manifests, and
validation ledger form the ordinary-Git handoff.

The historical Controlled-50 execution of Notebook 29,
`29_explainable_ai_and_case_retrieval.ipynb`, completed the approved
explanation-catalog and case-retrieval analysis with its completion gate passed.
It remains the pilot baseline and:

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

The historical Notebook 29 output is the pilot source for downstream candidate-level
explanation discovery and selected similar-case examples. Consumers must use the
complete 1,785-row catalog when complete case coverage is required, treat the 24
visual units as report examples only, preserve DINOv2 and CLIP as separate views,
and retain retrieval exclusions and embedding-ineligibility states. Category is
the complete primary grouping; style or period is descriptive for 18 of 50
paintings. Retrieval similarity, operational recommendations, counterfactual
changes, and empirical seed variability do not establish restoration correctness,
calibrated confidence, historical authenticity, conservation approval, or
universal model superiority.

Controlled-300 run `run_ad7603b6bdb14156a140351f6ac1f241` now supersedes those
pilot counts without changing the artifact paths or schemas. It persisted the
complete 13,879-candidate Notebook 27 union across 2,620 cases and 300 paintings;
10,480 matched four-method primary candidates; 9,280 nonzero primary candidates
with local maps; 24 bounded SDXL candidates; 4,100 repeated-seed memberships in
1,025 groups; and 757 rule-defined lower-risk candidates. Each Notebook 15
feature view contains 16,404 restored-content embeddings, of which 13,144
intersect the Notebook 27 catalog in both DINOv2 and CLIP. The 735 Notebook 22
extension candidates without Notebook 15 embeddings remain explicitly
retrieval-ineligible rather than silently removed. Category metadata is complete
for 300 paintings; style/period is descriptive for 268.

The presentation layer remains deliberately bounded at ten queries, 100
neighbour rows, fourteen counterfactual panels, ten retrieval panels and 24
selected visual units. Its self-contained fourteen-section report embeds 34
images and has no external image dependency. All 146 checks and all 13 roadmap
requirements passed, all six registered artifact checksums matched, and the
final output tree contains exactly 30 files with no temporary artifacts. The
E-drive comparison preserved the pilot's complete four-CSV, 24-PNG, one-HTML and
one-JSON structure while the catalog grew from 1,785 to 13,879 rows. The complete
46.81 MB catalog is diagnostics-tier Hugging Face evidence; the bounded figures,
report, compact neighbour table, manifests and validation ledger form the
ordinary-Git handoff without consuming Git LFS.

Notebook 30, `30_model_cards_compute_and_scalability.ipynb`, completed its
Controlled-300 run as `run_605de239145a46e9a202fd63bbbb4e9c`. The completed
contract:

- persist five machine-readable and portable Markdown method cards for OpenCV
  Telea, LaMa, HINT, Stable Diffusion Inpainting, and SDXL Inpainting;
- consume 2,620 Telea, 2,620 LaMa, 2,620 HINT and 8,520 Stable Diffusion
  candidate records from the executed Controlled-300 producers;
- preserve SDXL as a bounded partial evaluation: 35 scheduled cases across 30
  paintings, with 24 completed cases across 19 paintings;
- persist 42 compute/scalability rows: 32 observed runtime summaries and ten
  projection rows across a 600-painting current-design scenario and a
  hypothetical 300-painting full-design SDXL scenario;
- retain all eleven Notebook 21 quality anchors as separate descriptive
  evidence in the stable historical population identifiers, whose actual
  memberships are now a four-method core and bounded five-method subset;
- keep observed and projected evidence separate, keep runtime outside the
  quality vote, and produce no combined quality/compute score;
- generate two canonical figures and five thirteen-section text-native cards,
  for exactly twelve physical canonical files.

Notebook 30 is now the Controlled-300 canonical downstream
source for method disclosures, observed compute and notebook-owned model storage.
Its 600-painting and full-design SDXL rows are linear sensitivity projections,
not executed experiments or confidence intervals. Recorded runtime and memory
describe one workstation; quality-anchor wins remain descriptive; and no card
establishes historical authenticity, conservation suitability, or approval for
physical treatment. All 178 validation checks, all 13 roadmap responsibilities,
all six artifact records and the exact 12-file output contract passed. Against
`E:/outputs/30_model_cards_compute_and_scalability`, every pilot relative path
is retained. The only new path is the HINT card; model cards increased 4→5,
compute rows 35→42, validation rows 165→178 and physical files 11→12. The
previous Controlled-50 outputs remain only the frozen comparison baseline.

The Notebook 31–36 records below describe the completed **historical
Controlled-50 reporting, dashboard and packaging layer**. They remain valid as
pilot evidence and recovery documentation, but they are not yet the current
Controlled-300 downstream handoff. Notebook 31 is the next eligible rerun and
must rebuild its five-method report set from the completed N09–N30 evidence
before any later reporting notebook becomes current.

Historical pilot Notebook 31 is complete and passed its completion gate. It consumed validated
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

Within the frozen pilot, Notebook 31 is the canonical source for model-report discovery
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

Historical pilot Notebook 32 is complete and passed its completion gate. It consumed validated
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

Within the frozen pilot, Notebook 32 is the canonical source for selected case-report and
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

Historical pilot Notebook 33 is complete and passed its completion gate. It consumed the frozen
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

Within the frozen pilot, Notebook 33 is the canonical final-report source for Notebook 34. Downstream
consumers must preserve its applicability boundaries: the complete comparison is
limited to Telea, LaMa, and Stable Diffusion; SDXL remains a ten-case, five-
painting feasibility population; uncertainty covers supported Stable Diffusion
repeated-seed populations only; the five-painting extensions do not estimate
independent category or style effects; and scaling projections are not executed
results or confidence intervals. Computational flags, feature similarity,
retrieval results, and visual plausibility do not establish expert ground truth,
historical authenticity, conservation approval, or a physical treatment
recommendation.

Historical pilot Notebook 34 is complete and passed its completion gate. It consumed 41 validated
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
Within the frozen pilot, Notebook 34 is the canonical dashboard-data source for Notebook 35.
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

### 6.2 Completed Notebook 37 HINT/MAT method-selection extension

Notebook 37 is a completed, separately owned scientific extension. It compared
HINT and MAT and selected HINT as the additional method for the planned expanded
benchmark. It must not be merged into the completed three-method
leaderboard or described as a fourth full-model benchmark.

| Contract element | Approved value |
|---|---|
| Output owner | `outputs/37_hint_mat_method_selection/` |
| Source population | frozen N08 canonical case registry |
| Independent unit | painting |
| Repeated/nested unit | case nested within painting |
| Paintings | `p001`, `p018`, `p026`, `p039`, `p043` |
| Comparison cases | 12 predeclared nonzero canonical cases |
| Candidates | 24 = 12 HINT + 12 MAT |
| Damage coverage | 3 each of `scratch_thin`, `loss_small`, `loss_large`, `mixed_damage` |
| Category coverage | all five categories; at least two cases per category |
| Identity QA | `canonical__p001__zero_control`, excluded from comparison counts |
| Statistical scope | paired descriptive evidence; no inferential p-values |
| Decision owner | user after complete visual and numerical review |
| Recorded decision | HINT |
| Metric-anchor result | HINT 96, MAT 6, ties 6 of 108 |
| Validation | 94 of 94 checks pass; no blocking or warning failures |

Evidence dependencies are limited to fixed paths declared in
`config/experiments/hint_mat_selection.yaml`. Notebook 37 may read frozen clean,
damaged, mask, content-geometry, region-policy, metric-definition, model-report,
and compute evidence, but all HINT/MAT outputs and metrics are newly computed and
owned by Notebook 37.

The integration boundary is explicit:

- official repositories and checkpoints remain outside the project tree;
- HINT uses its official Places2 checkpoint and completed at native 768 × 768;
- MAT uses its official Places-512 FullData checkpoint and a declared 512
  adapter;
- MAT's retained-pixel mask convention is converted from the repository's
  canonical missing-pixel convention;
- both methods return exact-mask-composited 768 × 768 RGB outputs;
- source revision, checkpoint checksum, adapter, runtime, GPU memory, license,
  failures, and fallback behavior remain visible.

Supported claims are limited to relative technical feasibility, paired metric
behavior, visible restoration strengths/failures, runtime/memory suitability,
and the evidence-backed choice of HINT for the later expanded run. Prohibited
claims include full-benchmark superiority,
painting-domain generalization, conservation suitability, human plausibility,
calibrated uncertainty, and any universal combined score.

The selection gate passed: both methods produced all twelve outputs, preserved
outside-mask pixels exactly, returned valid geometry and finite required
metrics, and resolved their runtime, dependency, and licence records. HINT ran
at native 768 × 768; MAT used the declared 512 adapter and supported PyTorch
fallback. Mean inference time was 8.26 seconds per case for HINT and 10.00
seconds for MAT; peak GPU memory was 5.06 GiB and 1.23 GiB, respectively.

HINT led 96 of 108 case-level anchors, MAT led 6, and 6 were ties. Complete
visual review also found MAT more likely to retain thin scratches or produce
pale, fragmented large-loss completions. HINT was therefore selected on the
combined technical, metric, and visual record. Its MIT licence supports later
reuse, while MAT's noncommercial licence remains a deployment constraint rather
than a hidden numerical penalty.

The reason for testing these methods was architectural coverage. The frozen
benchmark contains a classical deterministic method, one learned deterministic
method, and one stochastic prompt-conditioned method. HINT adds a second
deterministic learned family with mask-aware transformer processing and
long-range context modelling. This extends the future design without claiming
that the 12-case pilot resolves painting-domain generalization.

### 6.3 Controlled-300 research-question alignment

Before the controlled-300 rerun, the proposal questions were refined to match
the evidence contract without adding a new experiment. RQ1 now asks what
region-aware, multi-metric evidence adds beyond traditional image similarity.
RQ2 asks about method differences across controlled artificial damage and the
consistency of those differences across evaluated paintings. RQ3 asks how
repeated-candidate disagreement characterizes stochastic stability and relates
to other restoration-quality diagnostics.

This is a framing correction, not a retroactive scientific result. The
50-painting notebooks, manifests, validation records, generated reports, and
N36 package remain historical artifacts. Their wording must not be edited by
hand. During the normal controlled-300 rerun, affected report and dashboard
producers must regenerate their research-question tables and narrative from the
current proposal, roadmap, and evaluation configuration. Broad visual
categories remain descriptive subgroups, and repeated-candidate disagreement
must not be reported as a validated error detector or calibrated confidence.

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

No notebook remains unimplemented in the approved 36-stage pipeline or the
completed Notebook 37 extension. Before Batch 1 of any further explicitly
approved extension or reopening:

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
   compact `inventory_run.json` together unless an approved staged commit is
   required. The complete `project_file_inventory.csv` remains local under the
   2026-09-21 LFS capacity guard.

For documentation or application-only maintenance, update only the approved
files and use dated addenda to distinguish current delivery from original run
facts. Do not rerun notebooks, refresh checksummed packages, clear historical
warnings, or regenerate the inventory implicitly. Scientific-coverage changes
require coordinated human-ledger and YAML updates; ordinary wording corrections
do not manufacture a new scientific validation event.
