# Supervisor Feedback Agenda

This agenda is intended for the next supervisor meeting.

## 1. One-sentence project status

The project now has a working pre-feedback evaluation framework for AI-assisted painting restoration, including refined full-reference metrics, texture and brushstroke-proxy diagnostics, Stable Diffusion uncertainty heatmaps, selected per-case diagnostic reports, and an updated Streamlit dashboard.

## 2. Main artifacts to show

### A. Streamlit dashboard

Run command:

    streamlit run streamlit_app.py

Recommended pages to show:

1. Overview
2. Model Comparison
3. Texture Diagnostics
4. Diffusion Uncertainty
5. Case Reports
6. Reports

### B. Case report index

Path:

- `outputs/reports/case_diagnostics/case_report_index.html`

Purpose:

- show selected individual examples,
- compare clean/damaged/mask/model outputs,
- inspect uncertainty and texture diagnostics where available.

### C. Stable Diffusion uncertainty heatmap report

Path:

- `outputs/reports/stable_diffusion_uncertainty_heatmap_report_50.html`

Purpose:

- show seed-based spatial instability,
- explain masked, bounding-box, outside-mask, and boundary-ring uncertainty.

### D. Refined comparison output

Path:

- `outputs/metrics/comparison_unified_refined_opencv_lama_stable_diffusion_50.csv`

Purpose:

- show final reference-based model comparison under the refined metric-region policy.

## 3. Meeting goals

The meeting should answer these questions:

1. Is the 50-painting controlled subset sufficient?
2. Is the refined metric-region policy accepted?
3. Should texture and brushstroke-proxy diagnostics remain part of the core framework?
4. Is the 40-case Stable Diffusion uncertainty subset sufficient for the thesis?
5. Should uncertainty heatmaps be expanded to all 200 non-zero cases?
6. Should SDXL remain feasibility-audited only?
7. Should semantic/iconographic checks be added after feedback?
8. Should metadata-driven analysis be added after feedback?
9. Should metric-policy ablation be added after feedback?
10. Should the Streamlit dashboard be treated as a formal supporting artifact?

## 4. Recommended presentation order

### Step 1 — Thesis framing

Message:

> The thesis is not about training a better restoration model. It is about evaluating restoration trustworthiness.

Core claim:

> Visual plausibility is not the same as restoration trustworthiness.

### Step 2 — Controlled benchmark

Show:

- 50 paintings,
- 5 categories,
- 200 non-zero cases,
- 3 evaluated models,
- SDXL feasibility audit.

### Step 3 — Refined model comparison

Show:

- LaMa dominance under refined full-reference metrics,
- OpenCV as deterministic baseline,
- Stable Diffusion weak under reference metrics but important diagnostically.

### Step 4 — Metric-region policy

Explain:

- MSE/PSNR on masked region,
- SSIM/LPIPS/CLIP/DINOv2 on mask bounding-box crop,
- texture and brushstroke-proxy also on mask bounding-box crop.

### Step 5 — Texture diagnostics

Explain:

- added local texture layer,
- brushstroke-proxy is a directional texture proxy,
- not semantic recognition or authentication.

### Step 6 — Uncertainty heatmaps

Explain:

- 40 selected cases,
- 4 seeds per case,
- spatial variation across Stable Diffusion outputs,
- not calibrated confidence.

### Step 7 — Case reports

Show:

- selected examples from `case_report_index.html`,
- cases where metrics, texture, and uncertainty reveal different behavior.

### Step 8 — Ask for scope decisions

Ask supervisor to approve, reject, or prioritize:

- scaling beyond 50 paintings,
- expanding uncertainty to all 200 non-zero cases,
- SDXL follow-up,
- semantic/iconographic checks,
- metadata-driven analysis,
- metric-policy ablation,
- human/expert review.

## 5. Recommended pre-feedback stance

Do not start major new experiments before supervisor feedback.

The current package is sufficient to ask for methodological approval and scope direction.
