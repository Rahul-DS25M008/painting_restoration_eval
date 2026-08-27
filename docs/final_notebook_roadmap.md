# Final 35-Notebook Roadmap

## 1. Purpose

This roadmap defines the final dependency order and detailed responsibility of every notebook in the thesis repository:

**Trustworthy Evaluation Frameworks for AI-Assisted Painting Restoration**

It consolidates the previously planned 40-notebook roadmap into 35 stages while preserving the complete methodological, experimental, engineering, reporting, explainability, and deployment scope.

Nothing is considered complete at the start of the refactoring cycle. `Origin` records lineage only.

All notebooks follow `docs/refactoring_implementation_guidelines.md`.

## 2. Global execution model

The pipeline supports these configuration-driven scopes:

```text
smoke
controlled_50
expanded_main
```

The controlled 50-painting dataset remains the development and validation baseline. Expansion toward approximately 300 paintings uses the same notebooks and schemas through configuration.

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

## 3. Dependency overview

```text
Dataset and experiment generation: 01–08
Model restoration and candidate generation: 09–12
Unified evidence generation: 13–20
Comparative and focused analysis: 21–29
Reporting, dashboard, and packaging: 30–35
```

---

# Foundation and Experimental Datasets

## 01 — Dataset Verification

**Notebook:** `01_dataset_verification.ipynb`  
**Origin:** Existing Notebook 01  
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
- Support the controlled 50-painting and expanded-main profiles.
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

Notebooks 02, 25, 29, 32, 33, and 35.

---

## 02 — Image Preprocessing

**Notebook:** `02_image_preprocessing.ipynb`  
**Origin:** Existing Notebook 02  
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
**Output root:** `outputs/06_mask_robustness_dataset_generation/`  
**Depends on:** Notebooks 02, 03, and the matched-painting policy from 05

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
- Leave metric variance, confidence intervals, and ranking stability to Notebook 23.

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

Notebooks 08–12, 23, 25, 28, 32, and 33.

---

## 07 — Synthetic Degradation Dataset Generation

**Notebook:** `07_synthetic_degradation_dataset_generation.ipynb`  
**Origin:** Existing Notebook 07  
**Output root:** `outputs/07_synthetic_degradation_dataset_generation/`  
**Depends on:** Notebook 02

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
**Output root:** `outputs/08_experiment_contracts_and_region_policy/`  
**Depends on:** Notebooks 01–07

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
- Prepare alternative region policies for Notebook 27.
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

All notebooks 09–35.

---

# Restoration and Candidate Generation

## 09 — OpenCV Telea Restoration

**Notebook:** `09_opencv_telea_restoration.ipynb`  
**Origin:** Existing Notebook 08  
**Output root:** `outputs/09_opencv_telea_restoration/`  
**Depends on:** Notebook 08

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

---

## 11 — Stable Diffusion Restoration

**Notebook:** `11_stable_diffusion_restoration.ipynb`  
**Origin:** Existing Notebook 21; incorporates candidate generation required by uncertainty analysis  
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
- Run a paired scratch-aware prompt ablation on all 50 canonical paintings using the four frozen uncertainty seeds.
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
- Exactly 50 canonical scratch cases, four declared seeds, and two matched prompt arms.
- Exactly 400 formal scratch outcomes with both prompts present for every painting-seed pair.
- Exactly 1,330 total candidates, including 120 added generic seed controls and 200 scratch-aware candidates.
- Both the frozen base configuration and supplementary scratch-prompt configuration are checksummed.

### Downstream consumers

Notebooks 13–21 and all later analysis/reporting stages.

---

## 12 — SDXL Feasibility or Restoration

**Notebook:** `12_sdxl_feasibility_or_restoration.ipynb`  
**Origin:** Existing Previous Version of Notebook 25, Pre-refactor  
**Output root:** `outputs/12_sdxl_feasibility_or_restoration/`  
**Depends on:** Notebook 08

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

The refactored Notebook 12 uses `partial_evaluation` mode under the
versioned `sdxl_config.v2` contract. It does not imply full SDXL coverage.

- Predeclare exactly ten comparable cases nested within five paintings.
- Include four canonical cases and six synthetic-degradation cases.
- Use one primary generic prompt, seed 2026, 768 x 768 inference, and 30 steps.
- Load the pinned SDXL pipeline once in an isolated persistent batch worker.
- Enforce a 7,200-second global budget and 900-second per-case watchdog.
- Start no new case when fewer than 660 seconds remain.
- Never retry automatically, fall back to CPU, reduce resolution, or reduce steps.
- Execute in diversity-first order while retaining the original selection rank.
- Threshold canonical missing-region masks at 128 and synthetic effect masks at 13.
- Composite generated pixels only inside the thresholded mask.
- Save every completed image immediately and checkpoint all ten candidate states
  after every resolved case.
- Represent timeout, CUDA out-of-memory, model unavailability, worker failure,
  and global-budget omissions explicitly; never convert them into quality scores.
- Permit downstream metrics only for rows with `status=completed`,
  `technical_validation_passed=true`, valid 768 x 768 RGB geometry, and zero
  changed pixels outside the binary mask.
- Treat painting as the independent unit (n=5); the two cases per painting are
  nested observations, not ten independent paintings.

The exact case registry, execution order, mask policy, output contract, and
interpretation limits are frozen in
`docs/notebook_12_partial_evaluation_contract.md`.

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

Notebooks 13–35, conditional on validated availability state.

---

# Unified Evidence Generation

## 13 — Classical Metrics

**Notebook:** `13_classical_metrics.ipynb`  
**Origin:** Consolidates Existing Notebooks 09, 15, and 22  
**Output root:** `outputs/13_classical_metrics/`  
**Depends on:** Notebook 02 geometry handoff and Notebooks 08–12

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

### Canonical outputs

```text
metrics/classical_metrics.csv
figures/classical_metric_distributions.png
figures/classical_improvement_by_region.png
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## 14 — LPIPS Metrics

**Notebook:** `14_lpips_metrics.ipynb`  
**Origin:** Consolidates Existing Notebooks 11, 17, and 24  
**Output root:** `outputs/14_lpips_metrics/`  
**Depends on:** Notebooks 08–12

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
**Output root:** `outputs/15_feature_similarity/`  
**Depends on:** Notebooks 08–12

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

---

## 16 — Difference Maps and Spatial Diagnostics

**Notebook:** `16_difference_maps_and_spatial_diagnostics.ipynb`  
**Origin:** Consolidates Existing Notebooks 10, 16, and 23  
**Output root:** `outputs/16_difference_maps_and_spatial_diagnostics/`  
**Depends on:** Notebooks 08–13

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
images/maps/<model_id>/<case_id>/<map_type>.png
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
**Output root:** `outputs/17_local_consistency_metrics/`  
**Depends on:** Notebooks 08–12 and canonical regions

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

### Downstream consumers

Notebooks 19–35.

---

## 18 — Diffusion Uncertainty Analysis

**Notebook:** `18_diffusion_uncertainty_analysis.ipynb`  
**Origin:** Existing Previous Version of Notebook 27, Pre-refactor  
**Output root:** `outputs/18_diffusion_uncertainty_analysis/`  
**Depends on:** Notebooks 11–15 and conditional Notebook 12

### Purpose

Measure empirical seed-based candidate variability for diffusion models.

### Responsibilities

- Consume repeated-seed candidates; do not run model inference here.
- Validate required seed coverage.
- Compute candidate-to-candidate image variation.
- Compute per-pixel variability.
- Compute masked-region, mask-crop, boundary, outside-mask, and full-image uncertainty.
- Compute pairwise LPIPS variation.
- Compute pairwise CLIP and DINOv2 variation.
- Record seed-level reference metrics.
- Produce transparent component metrics before any combined index.
- If a combined uncertainty index is retained, document scaling, weighting, limitations, and sensitivity.
- Summarize uncertainty by model, damage type, percentage, category/style, experiment, and seed coverage.
- Compare Stable Diffusion and SDXL where full SDXL candidates exist.
- Prepare calibration data linking uncertainty to:
  - weak reference metrics;
  - texture inconsistency;
  - colour drift;
  - seam artifacts;
  - semantic drift;
  - human-review flags;
  - failure categories.
- State that uncertainty is an empirical proxy, not calibrated confidence.
- State that low uncertainty does not prove correctness.
- For deterministic models, reserve “uncertainty” for diffusion; use robustness/sensitivity terminology elsewhere.

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
**Depends on:** Notebooks 16–18

### Responsibilities

- Generate per-pixel diffusion uncertainty heatmaps for every eligible case.
- Generate full-image, masked-region, crop, boundary, and outside-mask heatmap variants.
- Use consistent normalization policies and record their scope.
- Produce raw numeric uncertainty maps where practical.
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

### Canonical outputs

```text
metrics/spatial_explanations.csv
images/uncertainty/<model_id>/<case_id>.png
images/overlays/<model_id>/<case_id>.png
figures/selected_explanation_panels/
manifests/map_images.csv
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## 20 — Semantic and Structural Consistency

**Notebook:** `20_semantic_and_structural_consistency.ipynb`  
**Origin:** New Notebook  
**Output root:** `outputs/20_semantic_and_structural_consistency/`  
**Depends on:** Notebooks 08, 11–12, 15–19

### Responsibilities

- Evaluate subject preservation.
- Evaluate composition and salient-structure preservation.
- Detect possible new semantic content.
- Detect plausible but reference-inconsistent objects.
- Evaluate painterly-style preservation diagnostically.
- Detect alteration of unmasked context.
- Inspect facial, anatomical, architectural, and object-structure drift where applicable.
- Compute patch-level DINOv2 similarity.
- Compute patch-level CLIP similarity where methodologically useful.
- Implement sliding-window/local feature comparison.
- Add local embedding maps.
- Add occlusion-sensitivity or saliency-aware analysis where feasible.
- Use structural-layout comparison where defensible.
- Record applicability by artwork/category and avoid applying facial/anatomical checks universally.
- State limitations of pretrained non-conservation-specific models.
- Produce machine-readable semantic evidence for later flags rather than assigning final flags here.

### Canonical outputs

```text
metrics/semantic_structural_metrics.csv
images/maps/<model_id>/<case_id>/semantic.png
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

- Compare OpenCV, LaMa, Stable Diffusion, and validated SDXL results.
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

## 22 — Damage-Size Sensitivity Analysis

**Notebook:** `22_damage_size_sensitivity_analysis.ipynb`  
**Origin:** New analysis stage separated from Notebook 05 generation  
**Output root:** `outputs/22_damage_size_sensitivity_analysis/`  
**Depends on:** Notebooks 05, 09–21

### Responsibilities

- Analyze all metric families against target and realized damage percentage.
- Produce performance-versus-damage curves.
- Identify nonlinear degradation points.
- Test whether model rankings change with damage size.
- Test whether uncertainty increases with damage size.
- Test interactions with category/style and mask morphology.
- Compare deterministic and generative sensitivity.
- Use paired/matched statistical methods.
- Report confidence intervals and effect sizes.
- Avoid overclaiming thresholds when sample sizes are small.

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

## 23 — Mask Robustness Analysis

**Notebook:** `23_mask_robustness_analysis.ipynb`  
**Origin:** New analysis stage separated from Notebook 06 generation  
**Output root:** `outputs/23_mask_robustness_analysis/`  
**Depends on:** Notebooks 06, 09–21

### Responsibilities

- Measure metric variance within matched robustness groups.
- Measure uncertainty due to placement and exact geometry.
- Analyze model-ranking stability.
- Analyze metric-ranking stability.
- Analyze sensitivity to location, morphology, boundary contact, and component arrangement.
- Compute confidence intervals and effect sizes.
- Compare robustness by model, style/category, and damage family.
- Distinguish stochastic candidate variation from input-mask robustness.
- Identify conclusions that depend excessively on one mask realization.

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

## 24 — Synthetic Degradation Analysis

**Notebook:** `24_synthetic_degradation_analysis.ipynb`  
**Origin:** New analysis stage separated from Notebook 07 generation  
**Output root:** `outputs/24_synthetic_degradation_analysis/`  
**Depends on:** Notebooks 07–21

### Responsibilities

- Analyze only model/degradation combinations marked eligible.
- Separate missing-region restoration from degradation correction/robustness.
- Compare individual and selected combined degradations.
- Analyze by degradation type, severity, affected area, category/style, and model.
- Use suitable reference, colour, texture, seam, semantic, and spillover evidence.
- Report excluded combinations and eligibility reasons.
- Compare quality, failure behavior, and compute.
- Reiterate that procedural degradations are not exact conservation simulations.

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

## 25 — Grouped and Statistical Analysis

**Notebook:** `25_grouped_and_statistical_analysis.ipynb`  
**Origin:** New Notebook; consolidates statistical responsibilities previously dispersed across comparisons  
**Output root:** `outputs/25_grouped_and_statistical_analysis/`  
**Depends on:** Notebooks 13–24

### Responsibilities

Analyze performance by:

- model;
- painting style;
- painting category;
- damage type;
- damage percentage;
- mask morphology;
- mask seed;
- uncertainty level;
- degradation type;
- dataset source;
- historical period where sufficiently populated;
- dataset scope.

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
- visual plausibility versus reference fidelity;
- uncertainty versus scalar performance;
- region-policy disagreement;
- cross-model disagreement.

Do not overstate results for small or imbalanced groups. Metric disagreement must remain visible rather than being averaged away.

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

## 26 — Failure Taxonomy and Trustworthiness Flags

**Notebook:** `26_failure_taxonomy_and_trustworthiness_flags.ipynb`  
**Origin:** New Notebook  
**Output root:** `outputs/26_failure_taxonomy_and_trustworthiness_flags/`  
**Depends on:** Notebooks 13–25

### Failure taxonomy

Candidate categories include:

- residual visible damage;
- excessive blur;
- structural collapse;
- semantic hallucination;
- object hallucination;
- repeated texture;
- texture smoothing;
- texture discontinuity;
- colour bleeding;
- colour drift;
- boundary seam;
- mask spillover;
- outside-mask alteration;
- composition change;
- facial distortion;
- anatomical distortion;
- unstable multi-seed completion;
- plausible but reference-inconsistent reconstruction.

### Trustworthiness flags

Independent flags include:

- high generative uncertainty;
- semantic inconsistency;
- structural inconsistency;
- texture inconsistency;
- colour inconsistency;
- visible boundary artifact;
- outside-mask alteration;
- restoration instability;
- metric disagreement;
- insufficient evidence;
- manual review required.

### Responsibilities

- Define every taxonomy category and evidence requirement.
- Generate independent flags rather than one trust score.
- Record flag name, triggering rule, supporting evidence, affected region, threshold, severity where defensible, explanation, and recommended action.
- Calibrate uncertainty against observed poor evidence and failure categories.
- Distinguish missing evidence from passing evidence.
- Test internal rule consistency.
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
reports/flag_definitions.md
figures/failure_taxonomy.png
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

---

## 27 — Metric and Region-Policy Ablation

**Notebook:** `27_metric_and_region_policy_ablation.ipynb`  
**Origin:** New Notebook; includes alternatives prepared by Previous Notebook 26  
**Output root:** `outputs/27_metric_and_region_policy_ablation/`  
**Depends on:** Notebooks 13–26

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
- style/damage subgroup changes;
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

## 28 — Explainable AI and Case Retrieval

**Notebook:** `28_explainable_ai_and_case_retrieval.ipynb`  
**Origin:** New Notebook  
**Output root:** `outputs/28_explainable_ai_and_case_retrieval/`  
**Depends on:** Notebooks 15–27

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
- generic versus style-specific prompts where applicable.

### Example-based explanations

Provide:

- representative successful cases;
- representative failed cases;
- nearest similar successful case;
- nearest similar failed case;
- examples by style, damage type, model, and flag;
- embedding-based retrieval using validated feature artifacts.

### Rule-based explanations

Every flag explanation includes rule, evidence, affected region, threshold, uncertainty, and recommended human action.

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

## 29 — Model Cards, Compute, and Scalability

**Notebook:** `29_model_cards_compute_and_scalability.ipynb`  
**Origin:** New Notebook; incorporates existing model-audit documentation  
**Output root:** `outputs/29_model_cards_compute_and_scalability/`  
**Depends on:** Notebooks 09–28 and model-audit sources

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
- projected 300-painting cost;
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

## 30 — Model Report Generation

**Notebook:** `30_model_report_generation.ipynb`  
**Origin:** Consolidates Existing Notebooks 13, 19, and 26  
**Output root:** `outputs/30_model_report_generation/`  
**Depends on:** Notebooks 09–29

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

## 31 — Case and Painting Report Generation

**Notebook:** `31_case_and_painting_report_generation.ipynb`  
**Origin:** Existing Previous Version of Notebook 33, Pre-refactor  
**Output root:** `outputs/31_case_and_painting_report_generation/`  
**Depends on:** Notebooks 09–30

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

## 32 — Final Evaluation Report

**Notebook:** `32_final_evaluation_report.ipynb`  
**Origin:** Existing Previous Version of Notebook 28, Pre-refactor  
**Output root:** `outputs/32_final_evaluation_report/`  
**Depends on:** Notebooks 21–31

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
- controlled-50 and expanded-main results;
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

## 33 — Final Streamlit Dashboard Assets

**Notebook:** `33_final_streamlit_dashboard_assets.ipynb`  
**Origin:** Consolidates Existing Previous Versions of Notebooks 29 and 34, Pre-refactor  
**Output root:** `outputs/33_final_streamlit_dashboard_assets/`  
**Depends on:** Notebooks 01–32

### Responsibilities

Prepare lightweight validated assets for:

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

The dashboard consumes prepared assets and does not rerun experiments or reconstruct project state from arbitrary outputs.

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

## 34 — Dashboard and Deployment Validation

**Notebook:** `34_dashboard_and_deployment_validation.ipynb`  
**Origin:** New Notebook  
**Output root:** `outputs/34_dashboard_and_deployment_validation/`  
**Depends on:** Notebook 33 and `streamlit_app.py`

### Purpose

Validate the dashboard as a reproducible inspection and decision-support layer.

### Responsibilities

- Validate every dashboard input path and schema.
- Validate asset-manifest completeness.
- Validate case/report/image links.
- Validate that no dashboard section depends on missing legacy global paths.
- Validate controlled and expanded scope labeling.
- Validate model availability handling.
- Validate missing/optional SDXL behavior.
- Validate figure and heatmap rendering references.
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

---

## 35 — Supervisor, Publication, and Reproducibility Package

**Notebook:** `35_supervisor_publication_reproducibility_package.ipynb`  
**Origin:** Consolidates Existing Previous Versions of Notebooks 30 and 35, Pre-refactor  
**Output root:** `outputs/35_supervisor_publication_reproducibility_package/`  
**Depends on:** Notebooks 01–34

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

Large reports should use linked images and must respect Git/LFS constraints.

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

### Final completion gate

- Every required upstream notebook has passed.
- Every package artifact exists and reloads.
- Every path is repository-relative and valid.
- Every optional omission has a documented reason.
- Package manifest counts reconcile with disk.
- Controlled and expanded results are clearly distinguished.
- Feasibility-only methods are not presented as evaluated models.
- Thesis interpretation boundaries are repeated.
- The package is ready for supervisor, thesis, publication, and reproducibility review.

---

# 4. Cross-cutting requirements matrix

| Requirement | Primary notebook(s) |
|---|---|
| Dataset licensing, completeness, duplicates, bias | 01 |
| 768 × 768 preprocessing and content bounds | 02 |
| Parameterized canonical masks and morphology | 03 |
| Canonical damaged images | 04 |
| Damage-size experimental generation and analysis | 05, 22 |
| Mask-robustness generation and analysis | 06, 23 |
| Synthetic degradation generation and analysis | 07, 24 |
| Case contracts, eligibility, and region policy | 08 |
| OpenCV, LaMa, Stable Diffusion, SDXL | 09–12 |
| Classical metrics | 13 |
| LPIPS | 14 |
| CLIP and DINOv2 | 15 |
| Difference maps | 16 |
| Texture and brushstroke proxies | 17 |
| Colour consistency | 17 |
| Seam and boundary consistency | 17 |
| Diffusion uncertainty | 18 |
| Heatmaps and spatial explanations | 19 |
| Semantic and structural consistency | 20 |
| Multi-model comparison | 21 |
| Grouped/statistical analysis and metric disagreement | 25 |
| Failure taxonomy and independent flags | 26 |
| Metric/region/threshold ablation | 27 |
| Counterfactual, example-based, and rule-based XAI | 28 |
| Model cards and compute/scalability | 29 |
| Per-model reports | 30 |
| Case and painting reports | 31 |
| Final report and publication assets | 32 |
| Dashboard assets | 33 |
| Dashboard/deployment validation | 34 |
| Supervisor/publication/reproducibility package | 35 |

## 5. Implementation sequence

The immediate sequence after approval is:

1. Perform an explicitly approved cleanup audit.
2. Update the inventory tool and foundational path/schema/manifest/validation/region helpers.
3. Refresh the inventory.
4. Define Notebook 01 batches and exact input/output contract.
5. Create Notebook 01 with Batch 1 only.
6. Continue through the approved batch workflow.

