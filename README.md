# Trustworthy Evaluation Frameworks for AI-Assisted Painting Restoration

This repository contains the reproducible implementation for the master thesis project:

**Trustworthy Evaluation Frameworks for AI-Assisted Painting Restoration**

The project builds and evaluates a controlled framework for assessing AI-assisted painting restoration. The focus is **not** to train a new restoration model or to claim conservation-ready restoration. The focus is to test whether different evaluation signals can reveal when restoration outputs are faithful, unstable, metric-dependent, or only visually plausible.

> **Core thesis claim:** visual plausibility is not the same as restoration trustworthiness.

---

## Current status

The project has progressed beyond the initial OpenCV pilot. The current repository contains a controlled 50-painting evaluation pipeline, final comparison reports, supervisor review package, and a working Streamlit dashboard.

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
- final controlled 50-painting evaluation report,
- dashboard asset preparation,
- supervisor review package,
- working Streamlit dashboard.

The current evaluated model stack is:

| Model | Status | Role |
|---|---|---|
| OpenCV Telea | Fully evaluated | Deterministic classical inpainting baseline |
| LaMa | Fully evaluated | Strong learned inpainting baseline |
| Stable Diffusion Inpainting | Fully evaluated | Generative inpainting model and uncertainty target |
| SDXL Inpainting | Feasibility audited | Not fully evaluated locally because of GPU/runtime constraints |

---

## Thesis framing

The thesis is framed as an **evaluation framework** for AI-assisted painting restoration.

It does **not** claim that the generated restorations are historically correct, conservation-approved, or suitable for real restoration practice. The experiment uses controlled synthetic damage because clean reference images are available, allowing full-reference metric analysis.

The central contribution is a reproducible framework that combines:

- controlled painting categories,
- synthetic damage types,
- multiple restoration paradigms,
- region-aware metric policy,
- perceptual and feature-space metrics,
- visual diagnostics,
- metric disagreement analysis,
- generative uncertainty analysis,
- feasibility documentation for heavier models.

---

## Research questions

The current project is organized around the following research questions.

### RQ1: Multi-metric trustworthiness evaluation

Can multi-metric evaluation provide a more trustworthy assessment of AI-assisted painting restoration than relying on PSNR/SSIM or a single score alone?

Current answer:

- Substantially answered for the controlled 50-painting subset.
- The framework uses MSE, PSNR, SSIM, LPIPS, CLIP, DINOv2, difference maps, comparison grids, and metric-disagreement analysis.
- The project found that metric-region policy matters, especially because sparse masked-region SSIM is not valid.

### RQ2: Model comparison across painting and damage conditions

How do pretrained restoration/inpainting models compare across painting categories and synthetic damage types?

Current answer:

- Substantially answered for the controlled 50-painting subset.
- OpenCV Telea, LaMa, and Stable Diffusion Inpainting were fully evaluated on 200 non-zero damage cases.
- Results are summarized by model, metric, mask type, and painting category.

### RQ3: Diffusion uncertainty from multiple candidates

Can uncertainty estimated from multiple diffusion restoration candidates identify cases where a generative restoration should be treated cautiously?

Current answer:

- Answered diagnostically using a balanced Stable Diffusion uncertainty subset.
- The uncertainty analysis uses 40 cases and 4 seeds per case, producing 160 outputs.
- The current result supports uncertainty as a complementary warning signal, not as a replacement for reference metrics.

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

5. **Metric disagreement supports the framework argument.**  
   The result is not just a model leaderboard. Different metric families can point to different interpretations.

6. **Uncertainty analysis is useful for generative models.**  
   Stable Diffusion can produce different outputs for the same damaged input depending on seed. This instability is useful as a caution signal.

7. **SDXL requires stronger compute for fair full evaluation.**  
   SDXL was feasibility-audited locally, but full evaluation was excluded because local 6GB VRAM did not provide a practical runtime-quality balance.

8. **The strongest thesis claim is methodological.**  
   The project demonstrates why restoration trustworthiness requires multiple evaluation signals instead of visual inspection alone.

---

## Supervisor review package

A supervisor-facing review package has been created at:

```powershell
outputs/supervisor_package/
```

Important files:

```powershell
outputs/supervisor_package/README_supervisor.md
outputs/supervisor_package/proposal_alignment.md
outputs/supervisor_package/methodology_summary.md
outputs/supervisor_package/results_summary.md
outputs/supervisor_package/limitations_and_deviations.md
outputs/supervisor_package/supervisor_questions.md
outputs/supervisor_package/next_steps.md
outputs/supervisor_package/package_manifest.json
```

The most important file for supervisor discussion is:

```powershell
outputs/supervisor_package/supervisor_questions.md
```

It asks for clarification on:

1. whether the controlled 50-painting subset is sufficient,
2. whether the 40-case uncertainty subset is sufficient,
3. whether SDXL should remain feasibility-audited only,
4. whether university GPU resources should be requested for full SDXL comparison,
5. whether the refined metric-region policy is accepted,
6. whether the Streamlit dashboard should be included as a formal supporting artifact,
7. whether the final thesis should emphasize the LaMa versus Stable Diffusion contrast,
8. whether the final thesis should scale dataset size, uncertainty analysis, or model coverage.

Large copied HTML reports are intentionally not committed inside `outputs/supervisor_package/reports/` because they exceed GitHub size limits. The package references the main generated reports instead.

The final report as well as other important reports however can still be accessed in the folder:

```powershell
outputs/reports/final_controlled_50_evaluation_report.html
outputs/reports/
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
- Diffusion Uncertainty,
- Visual Explorer,
- Key Findings,
- Reports,
- Debug.

The dashboard is designed for review and presentation. It does not rerun models, recompute metrics, or load large HTML reports.

Recommended full setup is described below.

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

---


### Run the dashboard

From the repository root:

```powershell
streamlit run streamlit_app.py
```

If Streamlit is missing:

```powershell
pip install streamlit plotly
```

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
```

Planned or optional next notebooks:

```text
31_thesis_methods_assets_cleaned.ipynb
32_sdxl_full_restoration_remote_cleaned.ipynb
33_sdxl_metrics_remote_cleaned.ipynb
34_four_model_comparison_remote_cleaned.ipynb
```

The SDXL notebooks are optional and depend on access to stronger GPU resources.

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

Reason:

- MSE and PSNR can be computed directly on sparse masked pixels.
- SSIM is not valid on sparse masked pixels because it requires local spatial structure.
- LPIPS, CLIP, and DINOv2 are more meaningful on image-like cropped regions around the damage.

---

## Important outputs

Main reports:

```text
outputs/reports/final_controlled_50_evaluation_report.html
outputs/reports/opencv_lama_stable_diffusion_refined_metric_comparison_report_50.html
outputs/reports/stable_diffusion_uncertainty_report_50.html
```

Dashboard assets:

```text
outputs/dashboard/data/
outputs/dashboard/manifests/
```

Supervisor package:

```text
outputs/supervisor_package/
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
      data/
      manifests/
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
| metrics | Classical, LPIPS, CLIP, DINOv2, and comparison metrics |
| visualization | Difference maps, comparison grids, uncertainty grids |
| reporting | HTML reports and final summaries |
| dashboard preparation | Dashboard-ready CSV/JSON assets |

---

## Future scope and supervisor review

The current framework is complete enough for supervisor review, but several candidate extensions could strengthen the final thesis.

Recommended high-priority extensions:

- **Texture-aware metrics:** add local texture descriptors such as GLCM contrast/homogeneity or Gabor-filter responses to better evaluate brushstroke and surface continuity.
- **Uncertainty heatmaps:** generate pixel-wise uncertainty maps across Stable Diffusion seed outputs and add them to selected reports and the dashboard.
- **Metric-policy ablation:** formalize the old-versus-refined metric-region comparison as an ablation study.

Possible medium-priority extensions:

- **Per-painting report templates:** generate standardized case-level reports with original, damaged, restored, metric, uncertainty, and trustworthiness summaries.
- **Metadata-driven analysis:** enrich analysis using artist, period, medium, or collection metadata where available.
- **Dashboard expansion:** add richer model/category/damage filters, uncertainty exploration, and report-generation features.

Exploratory future work:

- **Semantic/iconographic consistency checks:** use lightweight CLIP-based concept consistency or qualitative hallucination flags to identify possible semantic inventions in generative restoration outputs.

These additions should be prioritized with supervisor input. The strongest candidates for final thesis methodology are texture-aware metrics, uncertainty heatmaps, and metric-policy ablation.

## Future work

Current likely next steps:

1. Supervisor reviews the package in `outputs/supervisor_package/`.
2. Confirm whether the 50-painting subset is sufficient.
3. Confirm whether Stable Diffusion uncertainty should be expanded from 40 to 200 non-zero cases.
4. Confirm whether SDXL should remain feasibility-audited or be rerun on university GPU.
5. Decide whether the Streamlit dashboard should be included as a formal supporting artifact.
6. Prepare `31_thesis_methods_assets_cleaned.ipynb`.
7. Generate thesis-ready tables, captions, methodology text, and result figures.
8. Draft methodology, results, limitations, and future work sections.

Possible experimental extensions:

- scale beyond 50 paintings,
- expand uncertainty analysis to all non-zero Stable Diffusion cases,
- rerun SDXL on stronger GPU,
- perform four-model comparison if SDXL becomes feasible,
- add additional painting categories or damage patterns,
- add human/expert review if available.

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

Use `outputs/supervisor_package/reports/README_reports.md` for report references instead.

---

## Quick commands

Run dashboard:

```powershell
streamlit run streamlit_app.py
```
