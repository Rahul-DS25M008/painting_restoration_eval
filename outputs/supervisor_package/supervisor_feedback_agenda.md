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
2. Should the final experiment scale toward 300 paintings?
3. Is the refined metric-region policy accepted?
4. Should texture and brushstroke-proxy diagnostics remain part of the core framework?
5. Is the 40-case Stable Diffusion uncertainty subset sufficient for the thesis?
6. Should uncertainty heatmaps be expanded to all 200 non-zero cases?
7. Should SDXL remain feasibility-audited only?
8. Should metric-policy ablation be added after feedback?
9. Should color consistency metrics be added?
10. Should boundary/seam consistency metrics be added?
11. Should damage-size sensitivity analysis be added?
12. Should restoration risk scoring or diagnostic risk profiles be added?
13. Should metadata-driven or computed visual grouping be added?
14. Should mask/input robustness analysis be added?
15. Should semantic/iconographic checks be added after feedback?
16. Should the Streamlit dashboard be treated as a formal supporting artifact?

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

Ask the supervisor to approve, reject, or prioritize the frozen post-feedback extension menu.

Framework-strengthening options:

- metric-policy ablation,
- color consistency metrics,
- boundary/seam consistency metrics,
- damage-size sensitivity analysis,
- restoration risk scoring / diagnostic risk profiles.

Empirical-expansion options:

- scaling from 50 to 300 paintings,
- expanding Stable Diffusion uncertainty from 40 cases to all 200 non-zero cases,
- metadata-driven or computed visual grouping.

Conditional model and robustness options:

- SDXL full evaluation if stronger compute is available,
- mask/input robustness analysis,
- semantic/iconographic consistency checks,
- human/expert review if available.

## 5. Recommended pre-feedback stance

Do not start major new experiments before supervisor feedback.

The current package is sufficient to ask for methodological approval and scope direction.

Recommended framing:

> The current baseline is complete and frozen for supervisor review. Future work should either strengthen the evaluation framework or expand empirical coverage, but not both indiscriminately.

Preferred post-feedback direction, unless the supervisor requests otherwise:

1. Prioritize framework-strengthening extensions first.
2. Add empirical expansion only if the supervisor wants stronger coverage.
3. Add SDXL only if compute is available and the supervisor considers a fourth model necessary.
4. Treat semantic/iconographic checks and human/expert review as optional because they can expand scope quickly.
