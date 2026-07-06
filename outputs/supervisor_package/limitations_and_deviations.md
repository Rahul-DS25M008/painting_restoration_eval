# Limitations and Deviations from Proposal

## 1. Dataset scale

The completed controlled evaluation uses 50 paintings.

This is smaller than the broader long-term target range discussed during thesis planning, where 300–1000 paintings were considered as a possible later scale.

Current interpretation:

- The 50-painting subset is balanced and complete.
- It covers five painting categories and five damage conditions.
- It is sufficient for a controlled methodological demonstration.
- Supervisor confirmation is needed on whether this is enough for the final thesis scope or only for the current checkpoint.

## 2. SDXL feasibility limitation

SDXL was initially considered as a fourth model candidate.

Current SDXL status:

| aspect                   | finding                                             | details                                                                                                           |
|:-------------------------|:----------------------------------------------------|:------------------------------------------------------------------------------------------------------------------|
| model                    | SDXL Inpainting feasibility audit                   | diffusers/stable-diffusion-xl-1.0-inpainting-0.1 was tested locally.                                              |
| local_hardware           | 6GB GPU limitation                                  | RTX 3060 Laptop GPU with 6GB VRAM was insufficient for practical full SDXL evaluation.                            |
| no_offload_result        | CUDA out-of-memory                                  | Pipeline loading/inference without CPU offload exceeded available local VRAM.                                     |
| cpu_offload_result       | Technically possible but too slow                   | Low-quality SDXL probe required several minutes per image, making full controlled evaluation impractical locally. |
| quality_runtime_tradeoff | Excluded from full local comparison                 | Faster low-step settings were not adequate for restoration-quality comparison; stronger settings were too slow.   |
| interpretation           | Feasibility exclusion, not model-quality conclusion | SDXL was excluded because of local compute constraints, not because of a full comparative quality evaluation.     |
| future_work              | Remote GPU possible                                 | Full SDXL evaluation can be revisited with 12GB+ VRAM, preferably 16GB+.                                          |

Interpretation:

SDXL was excluded from the full local comparison because the available local GPU could not support practical full evaluation.

This is not a claim that SDXL performs poorly under adequate compute. It is a documented feasibility limitation.

## 3. Stable Diffusion uncertainty subset

Stable Diffusion uncertainty was evaluated on a balanced 40-case diagnostic subset.

This subset includes:

- 5 painting categories,
- 2 paintings per category,
- 4 non-zero masks per selected painting,
- 4 seeds per case.

This produced 160 generated outputs.

Current interpretation:

- The subset is balanced and useful for diagnostic uncertainty analysis.
- It does not cover all 200 non-zero comparison cases.
- Supervisor confirmation is needed on whether the subset is sufficient or should be expanded.

## 4. Synthetic damage limitation

The experiment uses controlled synthetic damage rather than real restoration ground truth.

This is appropriate because the clean reference is known, enabling full-reference metrics.

However, synthetic damage does not fully represent real physical deterioration, conservation constraints, pigment aging, varnish changes, craquelure, or historical restoration complexity.

## 5. Metric limitations

The metric framework includes multiple complementary metrics, but none of them individually determines conservation validity.

Metric limitations include:

- MSE/PSNR reward pixel-level closeness but may not capture perceptual quality.
- SSIM needs image-like spatial regions and is not valid on sparse masked pixels.
- LPIPS is perceptual but not painting-conservation-specific.
- CLIP and DINOv2 are general pretrained feature spaces, not restoration-faithfulness judges.
- Visual plausibility may not equal reference faithfulness.

## 6. Model-domain limitation

OpenCV Telea, LaMa, Stable Diffusion Inpainting, and SDXL Inpainting are not painting-conservation-specific restoration systems.

LaMa and Stable Diffusion rely on general inpainting or generative priors.

This creates a domain gap for paintings, historical style, brushwork, abstraction, and conservation interpretation.

## 7. Dashboard status

Dashboard assets have been prepared under `outputs/dashboard/`.

The actual Streamlit dashboard interface is not yet built or updated.

Supervisor confirmation is useful before investing time in polishing the dashboard, especially regarding whether it should be submitted as a formal supporting artifact.
