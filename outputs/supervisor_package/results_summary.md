# Results Summary

## Main thesis claim

> Visual plausibility is not the same as restoration trustworthiness.

## Key findings

| finding_id   | finding                                                     | evidence                                                                                                                                            | thesis_interpretation                                                                                               |
|:-------------|:------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------|
| F1           | Balanced controlled benchmark completed                     | 50 paintings, 5 painting categories, 250 damage cases, 200 non-zero local comparison cases.                                                         | The experiment provides a controlled basis for comparing restoration behavior across categories and damage types.   |
| F2           | LaMa dominates refined reference-based comparison           | LaMa won the refined majority vote in 155/200 non-zero cases.                                                                                       | Deep inpainting can outperform both classical interpolation and diffusion generation under reference-based metrics. |
| F3           | OpenCV Telea remains useful as deterministic baseline       | OpenCV Telea won the refined majority vote in 21/200 non-zero cases.                                                                                | Classical methods remain useful for baseline comparison and can still win some controlled cases.                    |
| F4           | Stable Diffusion rarely wins reference-based majority vote  | Stable Diffusion won the refined majority vote in 1/200 non-zero cases.                                                                             | Visual generative plausibility does not necessarily align with reference-faithful restoration.                      |
| F5           | Metric-region policy affects validity                       | Sparse masked-region SSIM was invalid and was moved to mask_bbox_crop in the refined comparison.                                                    | Evaluation frameworks must align metric choice with spatial region and metric assumptions.                          |
| F6           | Stable Diffusion uncertainty exposes generative instability | 40 cases were sampled with 4 seeds each, producing 160 outputs and multi-metric uncertainty summaries.                                              | Diffusion restoration should be evaluated for stability across seeds, not only single-output visual quality.        |
| F7           | Uncertainty and reference performance are complementary     | Uncertainty-performance quadrants distinguish unstable weak cases, unstable stronger cases, consistently weak cases, and relatively reliable cases. | Trustworthiness requires both reference-based accuracy and generative stability diagnostics.                        |
| F8           | SDXL excluded from full local evaluation                    | SDXL feasibility audit showed local 6GB VRAM/runtime constraints.                                                                                   | The final controlled comparison is limited to feasible local models; SDXL remains future remote-compute work.       |

## Refined model comparison

The final refined comparison includes 200 non-zero damage cases.

Model win summary:

| model_name                  | display_name                |   total_metric_wins |   majority_vote_cases |   majority_vote_rate |   mean_metric_wins_per_case |
|:----------------------------|:----------------------------|--------------------:|----------------------:|---------------------:|----------------------------:|
| lama                        | LaMa                        |                 924 |                   155 |                0.775 |                       4.62  |
| tie_lama_opencv_telea       | tie_lama_opencv_telea       |                 nan |                    23 |                0.115 |                     nan     |
| opencv_telea                | OpenCV Telea                |                 257 |                    21 |                0.105 |                       1.285 |
| stable_diffusion_inpainting | Stable Diffusion Inpainting |                  19 |                     1 |                0.005 |                       0.095 |

Main interpretation:

- LaMa dominates the refined reference-based metric comparison.
- OpenCV Telea remains useful as a deterministic baseline.
- Stable Diffusion Inpainting rarely wins under reference-based majority vote.
- Stable Diffusion remains important because it exposes generative plausibility and uncertainty issues.

## Metric disagreement

The refined comparison exported 124 metric-disagreement cases.

This is important because the thesis is not simply a leaderboard. Metric disagreement supports the framework argument that restoration trustworthiness depends on multiple complementary signals.

## Stable Diffusion uncertainty

Stable Diffusion uncertainty was evaluated on a balanced 40-case subset with four seeds per case.

Outputs:

- 40 uncertainty cases,
- 160 generated outputs,
- 240 pairwise LPIPS comparisons,
- 240 pairwise CLIP/DINOv2 feature comparisons.

Uncertainty-performance quadrants:

| uncertainty_performance_quadrant            |   cases |   mean_combined_uncertainty_index |   mean_sd_metric_wins |   mean_masked_std |   mean_pairwise_lpips |   mean_dinov2_uncertainty_distance |
|:--------------------------------------------|--------:|----------------------------------:|----------------------:|------------------:|----------------------:|-----------------------------------:|
| middle_region                               |      20 |                         0.159453  |                   0   |         0.0660356 |             0.0855509 |                          0.0616022 |
| low_uncertainty_low_reference_performance   |      10 |                         0.0456034 |                   0   |         0.044232  |             0.034808  |                          0.02447   |
| high_uncertainty_high_reference_performance |       5 |                         0.489374  |                   2.2 |         0.0985284 |             0.295616  |                          0.204038  |
| high_uncertainty_low_reference_performance  |       5 |                         0.562433  |                   0   |         0.10129   |             0.319016  |                          0.332678  |

Main interpretation:

Stable Diffusion uncertainty provides a diagnostic warning signal. A restoration can appear visually plausible while being unstable across seeds or weak under reference-based metrics.

## SDXL feasibility

SDXL was excluded from full local comparison because local 6GB VRAM and runtime constraints made full evaluation impractical.

This is a feasibility limitation, not a model-quality conclusion.

## Overall result

The current experiment supports the thesis framing that trustworthy AI-assisted painting restoration evaluation requires:

- reference-based metrics,
- region-aware metric policy,
- model comparison,
- visual diagnostics,
- uncertainty analysis for generative models,
- explicit model feasibility and audit notes.
