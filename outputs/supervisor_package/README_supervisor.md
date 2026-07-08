# Supervisor Review Package

Project:

**Trustworthy Evaluation Frameworks for AI-Assisted Painting Restoration**

Core claim:

> Visual plausibility is not the same as restoration trustworthiness.

This folder contains the current supervisor-facing review package for the pre-feedback thesis checkpoint.

The package is generated/refreshed by:

- `notebooks/35_refresh_supervisor_package_cleaned.ipynb`

The files in this folder are refreshed in place. Duplicate `v2`, `final_final`, or parallel summary files are intentionally avoided.

## Main files to review

### 1. Supervisor summary

- `supervisor_summary.md`

Start here.

This file summarizes:

- current experiment status,
- what was added since the original package,
- refined model comparison,
- texture and brushstroke-proxy diagnostics,
- Stable Diffusion uncertainty heatmaps,
- per-case diagnostic reports,
- updated Streamlit dashboard,
- remaining work after supervisor feedback.

### 2. Feedback agenda

- `supervisor_feedback_agenda.md`

Use this for the meeting structure.

It lists the recommended presentation order and the main decisions to ask the supervisor.

### 3. Open questions

- `supervisor_open_questions.md`

This file lists the unresolved scope decisions, including:

- whether the 50-painting controlled subset is sufficient,
- whether the final experiment should scale toward 300 paintings,
- whether uncertainty should be expanded to all 200 non-zero cases,
- whether SDXL should remain feasibility-audited only,
- whether metric-policy ablation should be added,
- whether metadata-driven or computed visual grouping should be added,
- whether color consistency metrics should be added,
- whether boundary/seam consistency metrics should be added,
- whether damage-size sensitivity analysis should be added,
- whether restoration risk scoring or diagnostic risk profiles should be added,
- whether mask/input robustness analysis should be added,
- whether semantic/iconographic checks should be added,
- whether the dashboard should be treated as a formal supporting artifact.

### 4. Artifact index

- `supervisor_artifact_index.csv`

This file lists the main notebooks, reports, metrics, and dashboard artifacts relevant for supervisor review.

### 5. Key findings

- `supervisor_key_findings.json`

This machine-readable file stores the main thesis-facing findings and the supervisor decisions needed for each.

### 6. Package manifest

- `supervisor_package_manifest.json`

This file records package metadata, source artifacts, output files, and the current feedback-ready status.

## Main artifacts outside this folder

### Streamlit dashboard

Run from the repository root:

    streamlit run streamlit_app.py

Recommended pages to show:

1. Overview
2. Model Comparison
3. Texture Diagnostics
4. Diffusion Uncertainty
5. Case Reports
6. Reports

### Case report index

- `outputs/reports/case_diagnostics/case_report_index.html`

This is the main entry point for selected per-case diagnostic reports.

### Stable Diffusion uncertainty heatmap report

- `outputs/reports/stable_diffusion_uncertainty_heatmap_report_50.html`

This shows spatial seed-based uncertainty heatmaps for selected Stable Diffusion cases.

### Dashboard assets

- `outputs/dashboard/`

Prepared by:

- `notebooks/34_prepare_final_dashboard_assets_cleaned.ipynb`

These files are consumed by the Streamlit dashboard.

## Current experiment status

The current controlled evaluation includes:

- 50 paintings,
- 5 painting categories,
- 200 non-zero restoration comparison cases,
- OpenCV Telea fully evaluated,
- LaMa fully evaluated,
- Stable Diffusion Inpainting fully evaluated,
- SDXL Inpainting feasibility-audited only.

Additional diagnostic layers now included:

- texture and brushstroke-proxy diagnostics,
- Stable Diffusion uncertainty heatmaps,
- selected per-case diagnostic reports,
- final dashboard assets,
- updated Streamlit dashboard.

## Interpretation boundaries

Stable Diffusion uncertainty heatmaps show seed-based spatial variability, not calibrated confidence.

Brushstroke-proxy metrics are directional texture proxies, not semantic brushstroke recognition, authentication, or conservation truth.

Case reports are inspection artifacts, not new metric computations.

The dashboard is a review interface, not the primary research result.

## Post-feedback extension policy

The current baseline is frozen for supervisor review.

The following extension directions are recorded as possible post-feedback work, not as committed implementation tasks:

### Framework-strengthening extensions

- metric-policy ablation,
- color consistency metrics,
- boundary/seam consistency metrics,
- damage-size sensitivity analysis,
- restoration risk scoring / diagnostic risk profiles.

### Empirical-expansion extensions

- scaling from 50 to 300 paintings,
- expanding Stable Diffusion uncertainty from the current 40-case subset to all 200 non-zero cases,
- metadata-driven or computed visual grouping.

### Conditional model and robustness extensions

- SDXL full evaluation if stronger compute is available,
- mask/input robustness analysis,
- semantic/iconographic consistency checks,
- human/expert review if available.

The supervisor should decide which, if any, of these are necessary for the final thesis scope.

## Files intentionally removed

Older standalone notes were removed after Notebook 35 because their content is now consolidated into the refreshed supervisor package files.

Removed/obsolete files:

- `limitations_and_deviations.md`
- `methodology_summary.md`
- `proposal_alignment.md`
- `results_summary.md`

Their current replacements are:

- `supervisor_summary.md`
- `supervisor_open_questions.md`
- `supervisor_feedback_agenda.md`
- `supervisor_key_findings.json`
- `supervisor_artifact_index.csv`
- `supervisor_package_manifest.json`
