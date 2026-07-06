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

## Medium priority questions

### 5. Is the thesis framing clear enough as an evaluation framework rather than as a model-training or restoration-production thesis?

**Related research question:** all

**Why this matters:** The strongest current contribution is the trustworthiness evaluation design, not a new restoration model.


### 6. Are the five synthetic damage types sufficient for the thesis scope?

**Related research question:** RQ2

**Why this matters:** The current masks cover zero control, scratches, small losses, large losses, and mixed damage, but real painting damage is more complex.


### 7. Should the final thesis emphasize the LaMa versus Stable Diffusion contrast as the main empirical result?

**Related research question:** RQ1/RQ2/RQ3

**Why this matters:** LaMa dominates reference metrics, while Stable Diffusion illustrates visual plausibility and uncertainty issues.


### 8. Should the Streamlit dashboard be included as a formal supporting artifact or kept as an internal demo?

**Related research question:** all

**Why this matters:** Dashboard assets are prepared, but the final app should reflect the supervisor-approved story.

## Low priority questions

### 9. Should the final report include full embedded HTML reports, or should large reports be kept as local artifacts with smaller linked versions for GitHub?

**Related research question:** reproducibility

**Why this matters:** Some reports and notebooks may be too large for clean GitHub storage.
