# Supervisor Review Package

Generated: 2026-07-06 19:01:57

Project:

**Trustworthy Evaluation Frameworks for AI-Assisted Painting Restoration**

## Purpose of this package

This package summarizes the current state of the thesis experiment without requiring review of every notebook and intermediate artifact.

The work is framed as an **evaluation framework**, not as a proposal for a new restoration model.

The central thesis claim is:

> Visual plausibility is not the same as restoration trustworthiness.

## Current experiment status

The controlled evaluation currently includes:

- 50 paintings,
- 5 painting categories,
- 250 total synthetic damage cases,
- 200 non-zero restoration comparison cases.

Fully evaluated models:

- OpenCV Telea,
- LaMa,
- Stable Diffusion Inpainting.

Feasibility-audited model:

- SDXL Inpainting.

## Main quantitative finding

Under the refined metric-region comparison:

- LaMa majority-vote wins: 155/200,
- OpenCV Telea majority-vote wins: 21/200,
- Stable Diffusion Inpainting majority-vote wins: 1/200.

This supports the current interpretation that LaMa is strongest under reference-based metrics, while Stable Diffusion may produce visually plausible but less reference-faithful restorations.

## Stable Diffusion uncertainty

Stable Diffusion was evaluated with multi-seed uncertainty analysis:

- 40 balanced diagnostic cases,
- 160 generated seed outputs,
- 4 seeds per case.

The highest uncertainty case in the current subset is:

- `p011_loss_large`,
- mask type: `loss_large`,
- combined uncertainty index: 0.9834.

## SDXL status

SDXL Inpainting was tested locally but excluded from full local evaluation because the available 6GB GPU did not provide a practical runtime-quality balance.

This is documented as a computational feasibility limitation, not as a full model-quality conclusion about SDXL.

## Important files in this package

### Main summaries

- `data/final_controlled_50_key_results_summary.csv`
- `data/research_question_coverage_summary.csv`
- `data/final_controlled_50_model_stack_summary.csv`
- `data/final_controlled_50_metric_policy_summary.csv`
- `data/final_controlled_50_model_win_summary.csv`
- `data/final_controlled_50_uncertainty_summary.csv`
- `data/final_controlled_50_sdxl_feasibility_summary.csv`

### Main reports

- `reports/final_controlled_50_evaluation_report.html`
- `reports/opencv_lama_stable_diffusion_refined_metric_comparison_report_50.html`
- `reports/stable_diffusion_uncertainty_report_50.html`

### Supervisor-facing notes

- `proposal_alignment.md`
- `methodology_summary.md`
- `results_summary.md`
- `limitations_and_deviations.md`
- `supervisor_questions.md`
- `next_steps.md`

### Selected figures

- `selected_figures/`

## Requested supervisor feedback

The most important feedback points are:

1. Whether the current research-question coverage is sufficient.
2. Whether the 50-painting controlled subset is sufficient for the next thesis checkpoint.
3. Whether the 40-case Stable Diffusion uncertainty subset is sufficient or should be expanded.
4. Whether SDXL feasibility-only treatment is acceptable.
5. Whether the refined metric-region policy is acceptable.
6. Whether the thesis framing should emphasize evaluation-framework trustworthiness rather than model ranking.
