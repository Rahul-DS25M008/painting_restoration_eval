# Supervisor Questions

The questions below are intended to guide the next supervisor discussion.

They focus on whether the current work sufficiently answers the proposal research questions and whether any additional final experiments are needed.

## High priority questions

### 1. Is the current 50-painting controlled subset sufficient for the current thesis checkpoint, or should the final thesis experiment scale beyond 50 paintings?

**Related research question:** RQ2

**Why this matters:** The current subset is balanced and complete, but earlier planning mentioned possible scaling toward 300–1000 paintings.


### 2. Is the 40-case Stable Diffusion uncertainty subset sufficient, or should uncertainty be expanded to all 200 non-zero damage cases?

**Related research question:** RQ3

**Why this matters:** The current uncertainty analysis is balanced and diagnostic, but it does not cover every non-zero case.


### 3. Is it acceptable to keep SDXL as feasibility-audited only, or should university GPU resources be requested for a full SDXL restoration and four-model comparison?

**Related research question:** RQ2/RQ3

**Why this matters:** SDXL was planned as a possible higher-capacity diffusion comparison, but local 6GB VRAM made full evaluation impractical.


### 4. Is the refined metric-region policy acceptable, especially the decision to move SSIM from sparse masked_region to mask_bbox_crop?

**Related research question:** RQ1

**Why this matters:** The initial sparse masked-region SSIM comparison was invalid. The refined policy keeps SSIM but evaluates it on an image-like crop.

### 5. Texture-aware evaluation

Should the final evaluation include dedicated texture metrics such as GLCM contrast/homogeneity, Gabor filter responses, or other local texture descriptors?

**Why this matters:**  
The thesis evaluates painting restoration, where brushstroke continuity, local texture, and surface-like visual consistency are important. Current metrics include pixel, perceptual, and feature-space similarity, but they are not explicitly texture-focused.

**Possible implementation:**  
Compute texture descriptors between original and restored images inside the masked region or mask bounding-box crop, then compare model behavior across high-texture paintings and damage types.

**Priority:** High candidate extension.

### 6. Uncertainty heatmaps

Should the Stable Diffusion uncertainty analysis be extended with per-case pixel-wise uncertainty heatmaps?

**Why this matters:**  
The current uncertainty analysis summarizes variation across seeds. Pixel-wise uncertainty maps would make speculative or unstable regions visually interpretable.

**Possible implementation:**  
For each multi-seed case, compute per-pixel standard deviation across generated restorations, save uncertainty heatmaps, and add them to the dashboard/reporting layer.

**Priority:** High candidate extension if RQ3 remains central.

### 7. Ablation and sensitivity studies

Should the final thesis include ablation studies on metric-region policy and mask design?

**Why this matters:**  
The project already found that metric-region policy affects interpretation, especially for SSIM. A formal sensitivity study would strengthen the methodology claim.

**Possible implementation:**  
Compare rankings under old vs. refined metric-region policies, test alternative mask bounding-box margins, and optionally evaluate additional mask variations.

**Priority:** High candidate extension because it directly supports the evaluation-framework contribution.


## Medium priority questions

### 8. Is the thesis framing clear enough as an evaluation framework rather than as a model-training or restoration-production thesis?

**Related research question:** all

**Why this matters:** The strongest current contribution is the trustworthiness evaluation design, not a new restoration model.


### 9. Are the five synthetic damage types sufficient for the thesis scope?

**Related research question:** RQ2

**Why this matters:** The current masks cover zero control, scratches, small losses, large losses, and mixed damage, but real painting damage is more complex.


### 10. Should the final thesis emphasize the LaMa versus Stable Diffusion contrast as the main empirical result?

**Related research question:** RQ1/RQ2/RQ3

**Why this matters:** LaMa dominates reference metrics, while Stable Diffusion illustrates visual plausibility and uncertainty issues.


### 11. Should the Streamlit dashboard be included as a formal supporting artifact or kept as an internal demo?

**Related research question:** all

**Why this matters:** Dashboard assets are prepared, but the final app should reflect the supervisor-approved story.

### 12. Semantic or iconographic consistency checks

Should the framework include a lightweight semantic consistency layer, such as CLIP-based concept checks or object/context consistency flags?

**Why this matters:**  
Generative models may hallucinate plausible but historically or semantically inappropriate content. Current reference and feature metrics may not fully capture iconographic inconsistency.

**Possible implementation:**  
Use CLIP-based similarity or concept prompts to flag cases where restored regions introduce unexpected semantic content. Full object detection on art datasets should be treated as optional or future work unless suitable models and annotations are available.

**Priority:** Medium, potentially ambitious.

### 13. Standardized per-painting report template

Should the final framework include a standardized per-painting report template?

**Why this matters:**  
A museum-facing or supervisor-facing framework benefits from case-level summaries, not only aggregate tables.

**Possible implementation:**  
Generate one HTML or PDF-style case report per painting or selected case, including original, damaged image, mask, model restorations, key metrics, uncertainty map if available, and a trustworthiness summary.

**Priority:** Medium to high for presentation value.

### 14. Metadata-driven analysis

Should the analysis be extended using available metadata such as artist, period, medium, or collection source?

**Why this matters:**  
The current controlled categories are manually defined. Metadata-driven analysis could reveal whether restoration behavior varies by historical period, medium, or artist style.

**Possible implementation:**  
Enrich the case metadata and run descriptive or statistical comparisons across available metadata fields. Statistical tests such as ANOVA may be useful if group sizes are sufficient.

**Priority:** Medium, depends on metadata completeness.

### 15. Dashboard expansion

Should the Streamlit dashboard be treated as a formal thesis artifact and expanded further?

**Why this matters:**  
The dashboard already works as an interactive review interface. Further expansion could make the framework more usable for supervisor review or museum-oriented exploration.

**Possible implementation:**  
Add stronger filtering by model/category/damage type, uncertainty heatmap views, report export links, and case-level report generation.

**Priority:** Medium. Useful, but should not replace core methodology work.

## Low priority questions

### 16. Should the final report include full embedded HTML reports, or should large reports be kept as local artifacts with smaller linked versions for GitHub?

**Related research question:** reproducibility

**Why this matters:** Some reports and notebooks may be too large for clean GitHub storage.

## Candidate methodology extensions for supervisor prioritization

The following additions could strengthen the final thesis, but they should be prioritized with supervisor input to avoid unnecessary scope expansion.
