# Recommended Next Steps

## Candidate final-scope extensions

The following extensions are possible next steps after supervisor review. They are not all required; they should be prioritized based on thesis scope, available time, and supervisor feedback.

### Recommended high-priority extensions

1. **Texture-aware metrics**  
   Add local texture descriptors such as GLCM contrast/homogeneity or Gabor-filter responses. This would strengthen the style-aware painting-restoration claim, especially for high-texture and brushstroke-heavy cases.

2. **Uncertainty heatmaps**  
   Extend Stable Diffusion uncertainty analysis from scalar summaries to pixel-wise uncertainty heatmaps. Add the heatmaps to selected visual reports and the Streamlit dashboard.

3. **Metric-policy ablation**  
   Formalize the old-versus-refined metric-region comparison as an ablation study. This directly supports the thesis argument that evaluation policy affects restoration conclusions.

### Medium-priority extensions

4. **Per-painting report template**  
   Generate standardized case-level HTML or PDF reports with original, mask, damaged input, restorations, key metrics, uncertainty summaries, and interpretation notes.

5. **Metadata-driven analysis**  
   Enrich analysis using available metadata such as artist, period, medium, or source collection. Add descriptive statistics or statistical tests if group sizes are meaningful.

6. **Dashboard expansion**  
   Improve the Streamlit dashboard with a stronger uncertainty explorer, richer filters, and report-generation features.

### Lower-priority or future-work extensions

7. **Semantic/iconographic consistency layer**  
   Explore CLIP-based concept consistency checks or qualitative hallucination flags. Full art-domain object detection should remain future work unless appropriate models or annotations are available.

### Suggested supervisor decision

The supervisor should decide whether the final thesis should prioritize:

- evaluation-methodology depth,
- dashboard/reporting polish,
- larger experimental scale,
- semantic/iconographic analysis,
- or uncertainty visualization.

The strongest methodological additions are likely texture-aware metrics, uncertainty heatmaps, and metric-policy ablation.

## Immediate next step

Review this supervisor package and discuss the open questions with the supervisor.

The most important decisions are:

1. whether the current 50-painting controlled subset is sufficient,
2. whether the 40-case Stable Diffusion uncertainty subset is sufficient,
3. whether SDXL should remain feasibility-audited or be revisited on university compute,
4. whether the refined metric-region policy is accepted,
5. whether the dashboard should be included as a formal artifact.

## If the supervisor accepts the current experimental scope

Proceed with:

1. building or updating the Streamlit dashboard using `outputs/dashboard/`,
2. preparing thesis-ready methods/results assets,
3. drafting the methodology chapter,
4. drafting the results chapter,
5. drafting the limitations and future work section.

## If the supervisor asks for larger uncertainty coverage

Create an additional notebook:

`27b_full_stable_diffusion_uncertainty_sweep_cleaned.ipynb`

Recommended scope:

- all 200 non-zero Stable Diffusion cases,
- 4 seeds per case,
- approximately 800 generated outputs.

This would extend the current 40-case diagnostic uncertainty subset.

## If the supervisor asks for SDXL comparison

Request university or external compute.

Minimum recommended hardware:

- 12GB VRAM minimum,
- 16GB+ VRAM preferred.

Then create optional remote-compute notebooks:

- `32_sdxl_full_restoration_remote_cleaned.ipynb`,
- `33_sdxl_metrics_remote_cleaned.ipynb`,
- `34_four_model_comparison_remote_cleaned.ipynb`.

## If the supervisor asks for dataset scaling

Extend the controlled dataset beyond 50 paintings.

Suggested path:

1. preserve the current 50-painting subset as a validated benchmark,
2. scale preprocessing and masks to a larger dataset,
3. rerun feasible models first,
4. treat heavier diffusion and uncertainty work selectively if compute is limited.

## Dashboard next step

The dashboard should be built after supervisor feedback.

Reason:

The dashboard should reflect the approved thesis story. Building the UI before confirming the framing risks polishing the wrong narrative.

The dashboard should use only:

`outputs/dashboard/`

and should avoid loading raw experimental files directly.

## Thesis asset next step

After the dashboard decision, create:

`31_thesis_methods_assets_cleaned.ipynb`

This notebook should generate thesis-ready:

- tables,
- figures,
- captions,
- methodology snippets,
- results snippets,
- limitations snippets,
- reproducibility notes.
