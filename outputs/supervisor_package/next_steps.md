# Recommended Next Steps

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
