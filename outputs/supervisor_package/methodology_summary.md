# Methodology Summary

## Dataset

The current controlled benchmark contains:

- 50 paintings,
- 5 painting categories,
- 10 paintings per category,
- 5 mask types per painting,
- 250 total damage cases,
- 200 non-zero local comparison cases.

The five painting categories are:

- portrait_figure,
- landscape_natural,
- architecture_structured,
- abstraction_surrealism,
- high_texture_brushwork.

## Synthetic damage

Five mask conditions are used:

- zero_control,
- scratch_thin,
- loss_small,
- loss_large,
- mixed_damage.

The zero-control cases are used for sanity checking. The four non-zero mask types are used for restoration comparison.

## Evaluated model stack

| model_name                  | display_name                | model_type                               | evaluation_status                         | cases_restored   |   non_zero_cases_compared | role_in_framework                        | main_interpretation                                                                                         |
|:----------------------------|:----------------------------|:-----------------------------------------|:------------------------------------------|:-----------------|--------------------------:|:-----------------------------------------|:------------------------------------------------------------------------------------------------------------|
| opencv_telea                | OpenCV Telea                | classical inpainting baseline            | fully_evaluated                           | 250              |                       200 | deterministic classical baseline         | Useful baseline for local interpolation behavior; limited semantic restoration capacity.                    |
| lama                        | LaMa                        | deep learning inpainting model           | fully_evaluated                           | 250              |                       200 | strong reference-based inpainting model  | Dominated the refined reference-based metric comparison across most cases.                                  |
| stable_diffusion_inpainting | Stable Diffusion Inpainting | latent diffusion inpainting model        | fully_evaluated_plus_uncertainty_analysis | 250              |                       200 | generative restoration candidate         | Can produce visually plausible completions but is less reference-faithful and may be unstable across seeds. |
| sdxl_inpainting             | SDXL Inpainting             | larger latent diffusion inpainting model | feasibility_audit_only                    | smoke/probe only |                         0 | excluded local full-evaluation candidate | Excluded from full local evaluation due runtime and 6GB VRAM feasibility constraints.                       |

## Final metric-region policy

| metric                        | final_local_region   | reason                                                                                       | used_in_final_comparison   |
|:------------------------------|:---------------------|:---------------------------------------------------------------------------------------------|:---------------------------|
| MSE improvement               | masked_region        | Direct pixel-error metric; suitable for sparse damaged pixels.                               | True                       |
| PSNR improvement              | masked_region        | Derived from pixel error; suitable for sparse damaged pixels.                                | True                       |
| SSIM improvement              | mask_bbox_crop       | Structural metric requiring image-like local context; sparse masked-region SSIM was invalid. | True                       |
| LPIPS improvement             | mask_bbox_crop       | Perceptual metric requiring image-like input.                                                | True                       |
| CLIP similarity improvement   | mask_bbox_crop       | Feature metric requiring image-like crop around the restored region.                         | True                       |
| DINOv2 similarity improvement | mask_bbox_crop       | Feature metric requiring image-like crop around the restored region.                         | True                       |

## Evaluation framework

The framework combines:

- classical full-reference metrics,
- perceptual LPIPS metrics,
- CLIP feature-space similarity,
- DINOv2 feature-space similarity,
- visual error-map diagnostics,
- metric-disagreement analysis,
- Stable Diffusion multi-seed uncertainty,
- SDXL feasibility auditing.

## Important methodological decision

Sparse masked-region SSIM was found to be invalid for local comparison because SSIM requires local image structure.

Final policy:

- MSE and PSNR remain on the sparse masked region.
- SSIM is evaluated on the mask-bounding-box crop.
- LPIPS, CLIP, and DINOv2 are also evaluated on the mask-bounding-box crop.

## Interpretation boundary

The project does not claim that model outputs are historically correct painting restorations.

The outputs are evaluated as candidate restorations under controlled synthetic damage with known clean references.

The purpose is to evaluate restoration trustworthiness, not to certify conservation-ready restoration.
