# Pilot Experiment Notes

## 1. Objective

This pilot experiment tests the complete evaluation pipeline for the thesis topic: **AI-assisted painting restoration**.

The goal of the pilot is not to produce final benchmark results. The goal is to check whether the proposed workflow can run end-to-end on a small, controlled set of paintings and produce interpretable outputs.

The tested workflow is:

```text
clean painting image
→ preprocessing
→ artificial damage mask
→ masked image
→ restoration output
→ metric evaluation
→ difference/error map
→ comparison grid
→ restoration report
```

## 2. Dataset

The pilot uses three public-domain / open-access paintings from The Metropolitan Museum of Art collection. The images were selected to represent visually different restoration situations.

| ID | Category | Description |
|---|---|---|
| p001 | Portrait / figure | Figure-heavy image for testing semantic and facial/structural restoration difficulty |
| p002 | Landscape / fresco | Softer landscape/fresco-style image for testing broad texture and atmospheric restoration |
| p003 | Structured / brushstroke-heavy | Painting with buildings and visible painterly texture, useful for testing structure and texture continuity |

All images are converted to RGB and standardized to **768 × 768 pixels** using resize and center crop.

## 3. Artificial damage masks

Three mask types were generated for each painting:

| Mask type | Purpose |
|---|---|
| `irregular_small` | Small localized missing-paint region |
| `scratch_lines` | Thin scratch/crack-like damage |
| `irregular_large` | Larger missing region and harder restoration case |

This produces:

```text
3 paintings × 3 mask types = 9 masked inputs
```

The masks are suitable for a first pilot but are still simplified. Future versions should use more realistic damage patterns, including:

- rougher boundaries
- scattered paint loss
- edge damage
- crack-plus-paint-loss combinations
- mixed damage masks
- better control of mask area ratio

## 4. Restoration baseline

OpenCV Telea inpainting is used as the first baseline restoration method.

It was selected because it is:

- fast
- deterministic
- simple to run locally
- useful as a classical non-learning baseline

It is not intended to represent the final model comparison. Later phases should include pretrained and generative inpainting models such as:

- LaMa
- Stable Diffusion Inpainting / SDXL Inpainting
- possibly DALL-E / OpenAI image editing as a closed-model comparison

## 5. Metrics

The following metrics are computed:

| Metric | Level | Purpose |
|---|---|---|
| MAE | Full image | Basic pixel-level error |
| MSE | Full image | Squared pixel-level error |
| PSNR | Full image and masked region | Traditional image restoration baseline |
| SSIM | Full image | Structural similarity |
| MAE / MSE | Masked region | Local restoration error inside damaged area |
| LPIPS | Full image and crop around mask | Perceptual similarity |

Masked-region and crop-based metrics are important because full-image metrics can hide local restoration failures when most of the image remains unchanged.

## 6. Visual outputs

The pilot generates:

- difference maps
- masked-only difference maps
- comparison grids
- embedded HTML report
- lightweight HTML report

The visual outputs are not only presentation material. They are part of the evaluation framework because they help explain why specific metric values are high or low.

## 7. Main observations

1. **Scratch-line masks were restored very well by OpenCV Telea.**  
   In several cases, the restored result was visually close to the original image.

2. **Small irregular masks produced mixed results.**  
   Some restorations were acceptable, while others showed blur or loss of local texture.

3. **Large irregular masks were the hardest cases.**  
   These restorations often became blurry or structurally weak, especially when the missing region overlapped important image structure.

4. **The p003 large irregular mask was the clearest weak case.**  
   The restoration struggled with architectural structure and painterly texture continuity.

5. **Full-image SSIM remained high even when local restoration quality was poor.**  
   This supports the need for masked-region metrics and localized error maps.

6. **LPIPS confirmed the broad difficulty pattern.**  
   Scratch-line masks generally had the lowest perceptual difference, while large irregular masks had the highest.

7. **Error maps were useful for localizing restoration failures.**  
   They helped visually explain why certain restorations were weaker.

8. **Restoration difficulty depends on both damage type and image content.**  
   The same mask type can be easier or harder depending on whether it covers smooth texture, architecture, faces, or brushstroke-heavy regions.

## 8. Important limitations

1. The pilot uses only three paintings and is not statistically meaningful.

2. The artificial masks are simple and not yet realistic enough for the final thesis experiment.

3. OpenCV Telea is only a classical baseline. It is useful for comparison but not sufficient as the main restoration model.

4. Current error maps are useful for readability, but local normalization can make cross-case comparison difficult. Future outputs should include both local-normalized and globally scaled maps.

5. White masked images are useful for visualization and OpenCV, but deep inpainting models may require different input formats.

6. For scratch-line masks, the LPIPS crop can become very large because line damage may span much of the image. Future perceptual evaluation may need patch-based, dilated-mask, or component-based evaluation.

7. The pilot does not yet include model training-data analysis or model-card bias/domain-gap review.

8. The pilot does not yet include uncertainty analysis from multiple generative outputs.

## 9. Reproducibility update

The pilot has now been refactored and rerun successfully from raw inputs.

The cleaned project includes:

- reusable source modules in `src/restoration_eval/`
- cleaned notebooks with a fixed run order
- regenerated processed images, masks, restorations, metrics, figures, and reports
- documented expected outputs

This confirms that the pilot is reproducible enough to serve as the foundation for the 50-painting controlled subset phase.

## 10. Implications for the 50-painting phase

The pilot supports the following design choices for the next phase:

1. Use a stratified 50-painting subset rather than a random image set.

2. Include painting categories that are restoration-relevant:
   - portrait / figure
   - landscape / natural scene
   - architecture / structured scene
   - abstraction / surrealism
   - high-texture / brushstroke-heavy

3. Add a zero-control condition to measure unnecessary model changes or hallucination when no damage is present.

4. Replace simple pilot masks with a more formal damage protocol:
   - scratch-thin
   - small paint loss
   - large paint loss
   - mixed damage
   - optional edge damage

5. Run OpenCV Telea on the 50-painting subset first, before adding pretrained models.

6. Add LaMa as the first pretrained inpainting model after the OpenCV baseline is stable.

7. Add diffusion-based or closed commercial inpainting models only after input/output handling and evaluation metrics are stable.

8. Plan uncertainty analysis separately, using a smaller subset and multiple seeds/candidates.

## 11. Questions carried into the next phase

The original supervisor-facing questions remain useful, but they are now refined into next-phase decisions:

1. Which pretrained restoration models should be prioritized after OpenCV Telea?

2. How much emphasis should be placed on closed commercial models such as DALL-E / OpenAI image editing?

3. Should the final experiment prioritize fewer paintings with deeper analysis or more paintings with a lighter metric set?

4. How should synthetic mask realism be balanced against experimental control?

5. Should expert feedback be treated as optional qualitative validation or planned as a formal evaluation component?

6. Which deployment format is most appropriate for the MDS requirement: Streamlit dashboard, static report generator, or both?
