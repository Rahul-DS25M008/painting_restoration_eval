# Trustworthy Evaluation Frameworks for AI-Assisted Painting Restoration

This repository contains the reproducible implementation for the master thesis project:

**Trustworthy Evaluation Frameworks for AI-Assisted Painting Restoration**

The project builds and evaluates a controlled framework for assessing AI-assisted painting restoration. The focus is **not** to train a new restoration model or to claim conservation-ready restoration. The focus is to test whether different evaluation signals can reveal when restoration outputs are faithful, unstable, metric-dependent, texture-inconsistent, or only visually plausible.

> **Core thesis claim:** visual plausibility is not the same as restoration trustworthiness.

> **Deployment Link:** https://fhtw-painting-restoration.streamlit.app/

---

## Current status

The project has progressed beyond the initial OpenCV pilot. The current repository contains a controlled 50-painting evaluation pipeline, refined three-model comparison, texture diagnostics, Stable Diffusion uncertainty heatmaps, selected per-case diagnostic reports, a refreshed supervisor review package, and a working Streamlit dashboard.

Current completed stages:

- cleaned pilot pipeline,
- controlled 50-painting subset,
- synthetic damage generation,
- OpenCV Telea restoration baseline,
- LaMa restoration evaluation,
- Stable Diffusion Inpainting evaluation,
- SDXL feasibility audit,
- classical metrics,
- LPIPS perceptual metrics,
- CLIP and DINOv2 feature similarity,
- difference maps and comparison grids,
- refined metric-region policy,
- final three-model comparison,
- Stable Diffusion multi-seed uncertainty analysis,
- texture and brushstroke-proxy diagnostics,
- Stable Diffusion uncertainty heatmaps,
- selected per-case diagnostic reports,
- final controlled 50-painting evaluation report,
- final dashboard asset preparation,
- updated Streamlit dashboard,
- refreshed supervisor review package.

The current evaluated model stack is:

| Model | Status | Role |
|---|---|---|
| OpenCV Telea | Fully evaluated | Deterministic classical inpainting baseline |
| LaMa | Fully evaluated | Strong learned inpainting baseline |
| Stable Diffusion Inpainting | Fully evaluated | Generative inpainting model and uncertainty target |
| SDXL Inpainting | Feasibility audited | Not fully evaluated locally because of GPU/runtime constraints |

Current pre-feedback checkpoint:

- The framework is ready for supervisor review.
- No further experiments are planned before feedback.
- The current baseline is frozen as the supervisor-review checkpoint.
- Future extensions are listed as post-feedback options, not committed work.
- The supervisor should help prioritize which extensions, if any, are necessary for the final thesis scope.

---

## Thesis framing

The thesis is framed as an **evaluation framework** for AI-assisted painting restoration.

It does **not** claim that the generated restorations are historically correct, conservation-approved, or suitable for real restoration practice. The experiment uses controlled synthetic damage because clean reference images are available, allowing full-reference metric analysis.

The central contribution is a reproducible framework that combines:

- controlled painting categories,
- synthetic damage types,
- multiple restoration paradigms,
- region-aware metric policy,
- classical, perceptual, and feature-space metrics,
- texture and brushstroke-proxy diagnostics,
- visual diagnostics,
- metric disagreement analysis,
- generative uncertainty analysis,
- spatial uncertainty heatmaps,
- selected case-level inspection reports,
- feasibility documentation for heavier models,
- dashboard-based review and reproducibility support.

Important interpretation boundaries:

- The project evaluates candidate restoration outputs under controlled synthetic damage.
- It does not certify conservation-ready restoration.
- It does not claim historical reconstruction correctness.
- It does not treat any single metric as ground truth.
- It treats visual plausibility, reference fidelity, texture consistency, and uncertainty as separate but complementary signals.

---

## Research questions

The current project is organized around the following research questions.

### RQ1: Multi-metric trustworthiness evaluation

Can multi-metric evaluation provide a more trustworthy assessment of AI-assisted painting restoration than relying on PSNR/SSIM or a single score alone?

Current answer:

- Substantially answered for the controlled 50-painting subset.
- The framework uses MSE, PSNR, SSIM, LPIPS, CLIP, DINOv2, texture diagnostics, brushstroke-proxy diagnostics, difference maps, comparison grids, and metric-disagreement analysis.
- The project found that metric-region policy matters, especially because sparse masked-region SSIM is not valid.
- Texture and brushstroke-proxy diagnostics add a local-structure layer beyond the original metric stack.
- Case-level reports make metric disagreement and diagnostic divergence inspectable.

### RQ2: Model comparison across painting and damage conditions

How do pretrained restoration/inpainting models compare across painting categories and synthetic damage types?

Current answer:

- Substantially answered for the controlled 50-painting subset.
- OpenCV Telea, LaMa, and Stable Diffusion Inpainting were fully evaluated on 200 non-zero damage cases.
- Results are summarized by model, metric, mask type, painting category, texture behavior, and selected diagnostic cases.
- SDXL was feasibility-audited but not fully evaluated locally because of hardware/runtime constraints.

### RQ3: Diffusion uncertainty from multiple candidates

Can uncertainty estimated from multiple diffusion restoration candidates identify cases where a generative restoration should be treated cautiously?

Current answer:

- Answered diagnostically using a balanced Stable Diffusion uncertainty subset.
- The uncertainty analysis uses 40 cases and 4 seeds per case, producing 160 outputs.
- Scalar uncertainty summaries and spatial uncertainty heatmaps are available.
- The current result supports uncertainty as a complementary warning signal, not as a replacement for reference metrics.
- Supervisor feedback is needed on whether uncertainty should be expanded to all 200 non-zero cases.

---

## Current conclusions

Current conclusions from the controlled 50-painting experiment:

1. **LaMa dominates the refined reference-based comparison.**  
   Under the final refined metric-region policy, LaMa wins most non-zero comparison cases.

2. **OpenCV Telea remains a useful deterministic baseline.**  
   It is not the strongest learned method, but it gives a stable classical comparison point.

3. **Stable Diffusion rarely wins under reference-based metrics.**  
   Its outputs may look plausible, but reference fidelity and seed stability are weaker.

4. **Metric-region policy is critical.**  
   Sparse masked-region SSIM was found to be invalid. The final policy evaluates SSIM on the mask bounding-box crop.

5. **Texture and brushstroke-proxy diagnostics add local structure evidence.**  
   These metrics help inspect whether restorations preserve local texture and brushstroke-like directional structure. They do not perform semantic brushstroke recognition, artist authentication, or conservation validation.

6. **Metric disagreement supports the framework argument.**  
   The result is not just a model leaderboard. Different metric families can point to different interpretations.

7. **Uncertainty analysis is useful for generative models.**  
   Stable Diffusion can produce different outputs for the same damaged input depending on seed. This instability is useful as a caution signal.

8. **Uncertainty heatmaps make instability spatially inspectable.**  
   The heatmap layer shows where seed-based Stable Diffusion variation occurs inside the mask, around the mask, and outside the mask.

9. **Per-case reports make aggregate results inspectable.**  
   Selected diagnostic reports combine clean/damaged/mask/model outputs, refined metrics, texture diagnostics, and uncertainty heatmaps where available.

10. **SDXL requires stronger compute for fair full evaluation.**  
    SDXL was feasibility-audited locally, but full evaluation was excluded because local 6GB VRAM did not provide a practical runtime-quality balance.

11. **The strongest thesis claim is methodological.**  
    The project demonstrates why restoration trustworthiness requires multiple evaluation signals instead of visual inspection alone.

---

## Supervisor review package

A supervisor-facing review package has been refreshed at:

```powershell
outputs/supervisor_package/
```

The package is generated/refreshed by:

```text
notebooks/35_refresh_supervisor_package_cleaned.ipynb
```

Important files:

```powershell
outputs/supervisor_package/README_supervisor.md
outputs/supervisor_package/supervisor_summary.md
outputs/supervisor_package/supervisor_artifact_index.csv
outputs/supervisor_package/supervisor_key_findings.json
outputs/supervisor_package/supervisor_open_questions.md
outputs/supervisor_package/supervisor_feedback_agenda.md
outputs/supervisor_package/supervisor_package_manifest.json
```

The most important files for supervisor discussion are:

```powershell
outputs/supervisor_package/supervisor_summary.md
outputs/supervisor_package/supervisor_feedback_agenda.md
outputs/supervisor_package/supervisor_open_questions.md
```

The supervisor package asks for clarification on:

1. whether the controlled 50-painting subset is sufficient,
2. whether the final experiment should scale toward 300 paintings,
3. whether the 40-case Stable Diffusion uncertainty subset is sufficient,
4. whether uncertainty heatmaps should be expanded to all 200 non-zero cases,
5. whether SDXL should remain feasibility-audited only,
6. whether university GPU resources should be requested for full SDXL comparison,
7. whether the refined metric-region policy is accepted,
8. whether metric-policy ablation should be added after feedback,
9. whether texture and brushstroke-proxy diagnostics should remain core diagnostics,
10. whether metadata-driven or computed visual grouping should be added,
11. whether color consistency metrics should be added,
12. whether boundary/seam consistency metrics should be added,
13. whether damage-size sensitivity analysis should be added,
14. whether restoration risk scoring or diagnostic risk profiles should be added,
15. whether mask/input robustness analysis should be added,
16. whether semantic/iconographic checks should be added after feedback,
17. whether the Streamlit dashboard should be included as a formal supporting artifact.

Large copied HTML reports are intentionally not committed inside `outputs/supervisor_package/reports/` because they can exceed GitHub size limits. The package references the main generated reports instead.

Important reports can be accessed in:

```powershell
outputs/reports/
```

Key report entry points:

```powershell
outputs/reports/final_controlled_50_evaluation_report.html
outputs/reports/opencv_lama_stable_diffusion_refined_metric_comparison_report_50.html
outputs/reports/stable_diffusion_uncertainty_heatmap_report_50.html
outputs/reports/case_diagnostics/case_report_index.html
```

---

## Streamlit dashboard

A working Streamlit dashboard is available at:

```powershell
streamlit_app.py
```

The dashboard uses prepared assets from:

```powershell
outputs/dashboard/
```

It includes:

- Overview,
- Dataset & Damage,
- Model Stack,
- Metric Policy,
- Model Comparison,
- Texture Diagnostics,
- Diffusion Uncertainty,
- Case Reports,
- Visual Explorer,
- Key Findings,
- Reports,
- Debug.

The dashboard is designed for review and presentation. It does not rerun models, recompute metrics, or load large HTML reports.

Run from the repository root:

```powershell
streamlit run streamlit_app.py
```

The dashboard is a supporting inspection artifact. It is not treated as the primary research result, because apparently even dashboards need existential boundaries now.

---

## Setup from a fresh GitHub clone

Clone the repository.

```powershell
git clone https://github.com/Rahul-DS25M008/painting_restoration_eval.git
cd painting_restoration_eval
```

Create and activate a Python virtual environment.

```powershell
winget install -e --id Python.Python.3.11
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies.

```powershell
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Optional but recommended for notebook work:

```powershell
python -m ipykernel install --user --name painting-restoration-eval --display-name "Painting Restoration Eval"
```

Run the dashboard.

```powershell
streamlit run streamlit_app.py
```

Start Jupyter if the notebooks need to be inspected or rerun.

```powershell
jupyter notebook
```

If Streamlit is missing:

```powershell
pip install streamlit plotly
```

---

## Reproducibility notes

The dashboard can be used directly if the generated dashboard assets are present in the cloned repository.

If generated outputs are missing, the notebooks must be rerun in order. The current project has many generated artifacts, including model outputs, metrics, figures, and reports. Some large HTML reports may be local-only or Git LFS-managed depending on the repository state.

For full experimental reproduction, the most important requirements are:

- Python environment from `requirements.txt`,
- raw painting images and metadata,
- notebook execution in the validated order,
- sufficient local storage,
- NVIDIA GPU for Stable Diffusion experiments,
- stronger GPU if SDXL is to be rerun fully.

The Streamlit dashboard itself does **not** require a GPU. It only reads prepared CSV, JSON, and figure files.

Generated outputs are intentionally separated by purpose:

- `outputs/metrics/` stores CSV metric and manifest files,
- `outputs/figures/` stores generated visual artifacts,
- `outputs/reports/` stores HTML reports,
- `outputs/dashboard/` stores dashboard-ready assets,
- `outputs/supervisor_package/` stores supervisor-facing summaries and manifests.

Large HTML files should be handled carefully because GitHub has regular file-size limits. Linked-image HTML reports are preferred over embedded base64 reports whenever possible.

---

## Current notebook pipeline

The cleaned notebook pipeline is currently organized as follows.

```text
01_dataset_verification_cleaned.ipynb
02_preprocessing_cleaned.ipynb
03_mask_generation_cleaned.ipynb
04_damage_creation_cleaned.ipynb
05_opencv_restoration_cleaned.ipynb
06_metrics_classical_cleaned.ipynb
07_difference_maps_cleaned.ipynb
08_lpips_metrics_cleaned.ipynb
09_feature_similarity_cleaned.ipynb
10_generate_report_opencv_cleaned.ipynb

11_lama_restoration_cleaned.ipynb
12_metrics_classical_lama_cleaned.ipynb
13_difference_maps_lama_cleaned.ipynb
14_lpips_metrics_lama_cleaned.ipynb
15_feature_similarity_lama_cleaned.ipynb
16_generate_report_lama_cleaned.ipynb
17_compare_opencv_lama_cleaned.ipynb

18_stable_diffusion_restoration_cleaned.ipynb
19_metrics_classical_stable_diffusion_cleaned.ipynb
20_difference_maps_stable_diffusion_cleaned.ipynb
21_lpips_metrics_stable_diffusion_cleaned.ipynb
22_feature_similarity_stable_diffusion_cleaned.ipynb
23_generate_report_stable_diffusion_cleaned.ipynb
24_compare_opencv_lama_stable_diffusion_cleaned.ipynb

25_sdxl_feasibility_audit_cleaned.ipynb
26_refined_metric_region_policy_cleaned.ipynb
27_diffusion_uncertainty_analysis_cleaned.ipynb
28_final_controlled_50_evaluation_report_cleaned.ipynb
29_prepare_streamlit_dashboard_assets_cleaned.ipynb
30_supervisor_package_cleaned.ipynb

31_texture_metrics_cleaned.ipynb
32_uncertainty_heatmaps_cleaned.ipynb
33_case_report_generation_cleaned.ipynb
34_prepare_final_dashboard_assets_cleaned.ipynb
35_refresh_supervisor_package_cleaned.ipynb
```

Potential post-feedback notebooks may include:

```text
36_metric_policy_ablation_cleaned.ipynb
37_color_boundary_damage_sensitivity_cleaned.ipynb
38_diagnostic_risk_profiles_cleaned.ipynb
39_uncertainty_expansion_full_cleaned.ipynb
40_metadata_visual_grouping_cleaned.ipynb
41_scaling_300_paintings_audit_cleaned.ipynb
42_sdxl_followup_or_remote_feasibility_cleaned.ipynb
43_mask_input_robustness_analysis_cleaned.ipynb
44_semantic_iconographic_consistency_cleaned.ipynb
```

These are not started before supervisor feedback unless approved. The notebook names are provisional and represent possible extension directions, not committed implementation work.

---

## Controlled dataset design

The current controlled subset contains:

- 50 paintings,
- 5 painting categories,
- 10 paintings per category,
- 5 mask conditions per painting,
- 250 total damage cases,
- 200 non-zero restoration comparison cases.

Painting categories:

| Category | Purpose |
|---|---|
| `portrait_figure` | Human figures and semantic facial/body structure |
| `landscape_natural` | Natural scenery and atmospheric regions |
| `architecture_structured` | Geometric and structured visual content |
| `abstraction_surrealism` | Non-literal or abstract/surreal content |
| `high_texture_brushwork` | Strong texture, brushwork, and local detail |

Mask conditions:

| Mask type | Purpose |
|---|---|
| `zero_control` | Sanity check with no damage |
| `scratch_thin` | Thin scratch-like damage |
| `loss_small` | Small localized paint loss |
| `loss_large` | Larger missing region |
| `mixed_damage` | Combined scratch and loss pattern |

The zero-control cases are used for sanity checking. The main refined model comparison uses the 200 non-zero cases, because those are the cases where restoration behavior can actually be evaluated.

---

## Final metric-region policy

The final local evaluation policy is:

| Metric family | Final region |
|---|---|
| MSE | `masked_region` |
| PSNR | `masked_region` |
| SSIM | `mask_bbox_crop` |
| LPIPS | `mask_bbox_crop` |
| CLIP similarity | `mask_bbox_crop` |
| DINOv2 similarity | `mask_bbox_crop` |
| GLCM texture metrics | `mask_bbox_crop` |
| Gabor texture metrics | `mask_bbox_crop` |
| Brushstroke-proxy orientation metrics | `mask_bbox_crop` |

Reason:

- MSE and PSNR can be computed directly on sparse masked pixels.
- SSIM is not valid on sparse masked pixels because it requires local spatial structure.
- LPIPS, CLIP, and DINOv2 are more meaningful on image-like cropped regions around the damage.
- Texture and brushstroke-proxy metrics require local spatial structure and are therefore also computed on the mask bounding-box crop.

Interpretation boundary:

- Brushstroke-proxy metrics measure directional local texture structure.
- They do not perform semantic brushstroke recognition, artist authentication, historical verification, or conservation judgment.
- Possible post-feedback metric additions include color consistency and boundary/seam consistency diagnostics. These would extend the current metric policy without changing the existing refined comparison baseline.

---

## Stable Diffusion uncertainty policy

Stable Diffusion uncertainty is evaluated using repeated generation for selected cases.

Current uncertainty subset:

- 40 non-zero cases,
- 4 seeds per case,
- 160 generated outputs.

Uncertainty layers:

- scalar multi-seed uncertainty summaries,
- pairwise LPIPS uncertainty,
- pairwise CLIP/DINOv2 uncertainty,
- combined uncertainty index,
- spatial uncertainty heatmaps.

Uncertainty heatmaps summarize seed-based spatial variability over:

- full image,
- masked region,
- mask-bounding-box crop,
- outside-mask region,
- outside boundary ring around the mask.

Interpretation boundary:

- Stable Diffusion uncertainty is seed-based variability, not calibrated model confidence.
- High uncertainty is a warning signal, not automatic proof of poor restoration.
- Low uncertainty does not prove historical or conservation correctness.
- The current boundary-ring metric measures an outside ring around the mask, not a symmetric inner-plus-outer boundary band.
- For deterministic models such as OpenCV Telea and the current LaMa runtime, repeated inference with the same input and settings does not produce seed-based variation. For those models, uncertainty-like analysis should be framed as robustness or sensitivity analysis, such as mask perturbation, input perturbation, or configuration sensitivity.
  
---

## Per-case diagnostic reports

Selected per-case diagnostic reports were generated to make the framework inspectable at the individual-case level.

Main entry point:

```text
outputs/reports/case_diagnostics/case_report_index.html
```

Main files:

```text
outputs/metrics/case_diagnostic_selected_cases_50.csv
outputs/metrics/case_diagnostic_report_manifest_50.csv
outputs/reports/case_diagnostics/selected_cases/
outputs/figures/case_diagnostics/selected_case_grids/
```

Each selected case can include:

- clean reference,
- damaged input,
- binary mask,
- OpenCV Telea output,
- LaMa output,
- Stable Diffusion output,
- refined reference metric evidence,
- texture and brushstroke-proxy diagnostics where available,
- Stable Diffusion uncertainty heatmap evidence where available.

Selection criteria include:

- high Stable Diffusion masked-region uncertainty,
- high boundary-ring uncertainty,
- texture/refined disagreement,
- high-texture brushwork representation,
- Stable Diffusion low metric-win cases,
- OpenCV and LaMa strong cases,
- category representatives,
- non-zero mask-type representatives.

The case reports are inspection artifacts. They do not create new metric evidence.

---

## Important outputs

Main reports:

```text
outputs/reports/final_controlled_50_evaluation_report.html
outputs/reports/opencv_lama_stable_diffusion_refined_metric_comparison_report_50.html
outputs/reports/stable_diffusion_uncertainty_heatmap_report_50.html
outputs/reports/case_diagnostics/case_report_index.html
```

Dashboard assets:

```text
outputs/dashboard/dashboard_summary.json
outputs/dashboard/dashboard_model_winner_summary.csv
outputs/dashboard/dashboard_metric_vote_summary.csv
outputs/dashboard/dashboard_texture_summary.csv
outputs/dashboard/dashboard_texture_disagreements.csv
outputs/dashboard/dashboard_uncertainty_summary.csv
outputs/dashboard/dashboard_uncertainty_selected_cases.csv
outputs/dashboard/dashboard_case_report_manifest.csv
outputs/dashboard/dashboard_selected_cases.csv
outputs/dashboard/dashboard_figure_manifest.csv
outputs/dashboard/dashboard_asset_manifest.json
```

Supervisor package:

```text
outputs/supervisor_package/README_supervisor.md
outputs/supervisor_package/supervisor_summary.md
outputs/supervisor_package/supervisor_artifact_index.csv
outputs/supervisor_package/supervisor_key_findings.json
outputs/supervisor_package/supervisor_open_questions.md
outputs/supervisor_package/supervisor_feedback_agenda.md
outputs/supervisor_package/supervisor_package_manifest.json
```

Final controlled summary files:

```text
outputs/metrics/final_controlled_50_dataset_summary.csv
outputs/metrics/final_controlled_50_model_stack_summary.csv
outputs/metrics/final_controlled_50_metric_policy_summary.csv
outputs/metrics/final_controlled_50_key_results_summary.csv
outputs/metrics/final_controlled_50_model_win_summary.csv
outputs/metrics/final_controlled_50_uncertainty_summary.csv
outputs/metrics/final_controlled_50_sdxl_feasibility_summary.csv
```

Texture and brushstroke-proxy outputs:

```text
outputs/metrics/comparison_texture_unified_50.csv
outputs/metrics/comparison_texture_case_winners_nonzero_50.csv
outputs/metrics/comparison_texture_winner_summary_nonzero_50.csv
outputs/metrics/comparison_texture_disagreement_cases_50.csv
outputs/metrics/comparison_texture_high_texture_brushwork_summary_50.csv
outputs/metrics/comparison_brushstroke_proxy_summary_by_model_50.csv
```

Uncertainty heatmap outputs:

```text
outputs/metrics/stable_diffusion_uncertainty_heatmap_manifest_50.csv
outputs/metrics/stable_diffusion_uncertainty_heatmap_summary_by_case_50.csv
outputs/metrics/stable_diffusion_uncertainty_heatmap_summary_by_mask_type_50.csv
outputs/metrics/stable_diffusion_uncertainty_heatmap_summary_by_category_50.csv
outputs/metrics/stable_diffusion_uncertainty_heatmap_vs_refined_performance_50.csv
outputs/metrics/stable_diffusion_uncertainty_heatmap_selected_cases_50.csv
```

Case diagnostic outputs:

```text
outputs/metrics/case_diagnostic_selected_cases_50.csv
outputs/metrics/case_diagnostic_report_manifest_50.csv
outputs/reports/case_diagnostics/case_report_index.html
outputs/reports/case_diagnostics/selected_cases/
outputs/figures/case_diagnostics/selected_case_grids/
```

---

## Repository structure

High-level structure:

```text
painting-restoration-eval/
  config/
    experiment_50_config.yaml
    pilot_config.yaml

  data/
    raw/
      images/
      metadata/
    processed/
      clean/
      masks/
      masked/
      restored/
      metadata/

  docs/
    literature_reference_log.md
    methodology_notes.md
    model_audit_notes.md

  notebooks/
    *_cleaned.ipynb

  outputs/
    dashboard/
    figures/
    metrics/
    reports/
    supervisor_package/

  src/
    restoration_eval/

  streamlit_app.py
  requirements.txt
  README.md
```

---

## Source modules

Reusable code lives in:

```text
src/restoration_eval/
```

Key module groups include:

| Module area | Purpose |
|---|---|
| path/config helpers | Centralized project paths and configuration |
| preprocessing | Clean image generation and metadata preparation |
| masks/damage | Synthetic mask and damaged-image generation |
| restoration | OpenCV, LaMa, Stable Diffusion, and SDXL audit helpers |
| metrics | Classical, LPIPS, CLIP, DINOv2, texture, and comparison metrics |
| visualization | Difference maps, comparison grids, uncertainty grids, case diagnostics |
| reporting | HTML reports, final summaries, case reports, supervisor package |
| dashboard preparation | Dashboard-ready CSV/JSON assets |

---

## Future scope and supervisor review

The current framework is complete enough for supervisor review.

Completed before supervisor feedback:

- controlled 50-painting benchmark,
- OpenCV Telea, LaMa, and Stable Diffusion evaluation,
- SDXL feasibility audit,
- refined metric-region policy,
- texture-aware and brushstroke-proxy metrics,
- Stable Diffusion multi-seed uncertainty subset,
- Stable Diffusion uncertainty heatmaps,
- selected per-case diagnostic reports,
- updated Streamlit dashboard,
- refreshed supervisor package.

The following items are frozen as **possible post-feedback extensions**. They are not commitments. The supervisor should decide which, if any, are required for the final thesis scope.

### Framework-strengthening extensions

These extensions strengthen the evaluation methodology without necessarily adding a new restoration model.

- **Metric-policy ablation:** compare old versus refined metric-region policies, reference-only versus perceptual/feature/texture-inclusive policies, and alternative vote rules.
- **Color consistency metrics:** add local color-difference or color-harmony diagnostics, such as Lab color difference, CIEDE2000-style distance, or local color histogram shifts.
- **Boundary/seam consistency metrics:** evaluate visible transition artifacts around restoration boundaries using boundary-ring error, gradient discontinuity, color jump, or texture discontinuity.
- **Damage-size sensitivity analysis:** analyze whether model performance, texture distance, and uncertainty change with mask area or damage severity.
- **Restoration risk scoring / diagnostic risk profiles:** combine reference performance, metric disagreement, texture distance, uncertainty, boundary behavior, and damage size into interpretable case-level risk flags.

### Empirical-expansion extensions

These extensions increase empirical coverage or provide stronger subgroup analysis.

- **Scale from 50 to 300 paintings:** expand the controlled dataset if the supervisor wants stronger empirical coverage.
- **Full Stable Diffusion uncertainty expansion:** expand uncertainty heatmaps from the current 40-case subset to all 200 non-zero cases.
- **Metadata-driven or computed visual grouping:** analyze behavior by available metadata such as artist, period, medium, source, or by computed visual properties such as texture density, edge density, brightness, color variance, and mask centrality.

### Conditional model and robustness extensions

These extensions are useful only if supervisor priority, compute, and time allow.

- **SDXL full evaluation:** rerun SDXL as a fourth model if stronger GPU resources are available and the supervisor considers it necessary.
- **Mask/input robustness analysis:** test how OpenCV, LaMa, and Stable Diffusion respond to controlled mask perturbations, fill strategies, brightness/noise changes, or other input variations.
- **Semantic/iconographic consistency checks:** evaluate whether generative outputs preserve high-level content or introduce semantic inventions. This should remain optional because it can become subjective quickly.
- **Human/expert review protocol:** add structured human or expert evaluation only if available and clearly in scope.

Recommended post-feedback framing:

> The current baseline is complete. Future work should either strengthen the evaluation framework or expand empirical coverage, but not both indiscriminately.

The current pre-feedback package intentionally avoids further scope expansion before supervisor feedback.

## Future work

Current likely next steps:

1. Supervisor reviews the package in `outputs/supervisor_package/`.
2. Confirm whether the 50-painting subset is sufficient.
3. Confirm whether the final experiment should scale toward 300 paintings.
4. Confirm whether Stable Diffusion uncertainty should be expanded from 40 to 200 non-zero cases.
5. Confirm whether SDXL should remain feasibility-audited or be rerun on university GPU.
6. Confirm whether the refined metric-region policy is accepted.
7. Confirm whether texture and brushstroke-proxy diagnostics should remain part of the core framework.
8. Decide whether metric-policy ablation should be added after feedback.
9. Decide whether color consistency and boundary/seam metrics should be added.
10. Decide whether damage-size sensitivity analysis should be added.
11. Decide whether restoration risk scoring or diagnostic risk profiles should be added.
12. Decide whether metadata-driven or computed visual grouping is in scope.
13. Decide whether mask/input robustness analysis is in scope.
14. Decide whether semantic/iconographic consistency checks are in scope.
15. Decide whether the Streamlit dashboard should be included as a formal supporting artifact.
16. Prepare thesis-ready tables, captions, methodology text, and result figures.
17. Draft methodology, results, limitations, and future work sections.

Frozen possible experimental extensions:

- scale from 50 to 300 paintings,
- expand Stable Diffusion uncertainty analysis to all 200 non-zero cases,
- rerun SDXL on stronger GPU,
- perform four-model comparison if SDXL becomes feasible,
- add metric-policy ablation,
- add metadata-driven or computed visual grouping,
- add color consistency metrics,
- add boundary/seam consistency metrics,
- add damage-size sensitivity analysis,
- add restoration risk scoring or diagnostic risk profiles,
- add mask/input robustness analysis,
- add semantic/iconographic checks,
- add human/expert review if available.

These extensions should be treated as supervisor-prioritized options, not as guaranteed next steps.

---

## Version control notes

The virtual environment, cache files, notebook checkpoints, and generated temporary files should not be committed.

Typical ignored files/folders:

```text
.venv/
__pycache__/
*.pyc
.ipynb_checkpoints/
```

Large HTML reports can exceed GitHub's regular file-size limits. If they are needed in the remote repository, use Git LFS deliberately. Otherwise, keep large reports local and commit compact summaries, markdown notes, dashboard assets, and selected figures.

The supervisor package intentionally avoids committing copied giant HTML reports under:

```text
outputs/supervisor_package/reports/
```

## Quick commands

Run dashboard:

```powershell
streamlit run streamlit_app.py
```
