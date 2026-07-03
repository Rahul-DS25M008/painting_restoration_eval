# Model Audit Notes

This document records the current model-selection logic for the 50-painting controlled subset phase of the painting restoration evaluation project.

## Purpose

The model audit exists to make model selection explicit before scaling beyond the reproducible 3-painting pilot. It records each candidate model's expected role, reproducibility status, training-data transparency, and likely painting-domain limitations.

The key concern is that many inpainting models are trained on general natural-image or web-scale image data, not on controlled painting restoration data. This creates a potential domain gap for historical paintings, brushstroke texture, abstraction, surrealism, and conservation-style restoration.

## Current model-selection decision

| Model | Current decision | Role |
|---|---|---|
| OpenCV Telea | Selected | Classical deterministic baseline |
| LaMa | Selected as next model | First pretrained open inpainting baseline |
| Stable Diffusion Inpainting | Candidate | Generative model for uncertainty analysis |
| SDXL Inpainting | Candidate later | Higher-capacity diffusion comparison |
| DALL-E / OpenAI Image Editing | Optional only | Closed commercial comparison |

## OpenCV Telea

OpenCV Telea remains the baseline model for the 50-painting subset. It is not trained on image data, so it does not introduce training-data bias in the usual machine-learning sense. Its main value is reproducibility: it is fast, deterministic, local, and already validated in the cleaned 3-painting pilot.

Its weakness is methodological. It has no semantic understanding of painting content, object structure, brushstroke intent, or historical style. The pilot already showed that it handles thin scratches well but performs worse on larger irregular missing regions, especially when structure and painterly texture must be reconstructed.

Decision: keep as the first model for the 50-painting subset.

## LaMa

LaMa is the preferred next model because it is open, pretrained, and specifically designed for large-mask image inpainting. Its paper describes Fast Fourier Convolutions, high-receptive-field perceptual loss, and large training masks as key design choices. This makes LaMa a stronger next baseline than OpenCV Telea for larger missing regions.

The main audit concern is domain gap. The reported Big LaMa training data uses a large subset of the Places-Challenge dataset, which is scene-oriented rather than painting-restoration-specific. This makes LaMa a good general inpainting baseline, but not necessarily a faithful painting restoration model.

For this project, LaMa will be treated as a pretrained open inpainting baseline rather than as a conservation-specific restoration system. It is expected to outperform OpenCV Telea on some larger masks because it has learned image priors and a larger effective receptive field. However, those same learned priors may also introduce visually plausible but historically incorrect content, especially in paintings with distinctive brushwork, abstraction, surrealism, or iconographic detail.

### Implementation decision

The LaMa method source is the original LaMa paper and official project/repository. The runtime implementation for this thesis pipeline will use the IOPaint command-line interface with `model=lama`.

This decision separates the research source from the practical execution wrapper:

- method source: LaMa paper and official implementation,
- runtime source: IOPaint LaMa CLI,
- reason: IOPaint provides a practical local batch interface for image and mask folders,
- expected benefit: easier integration with the existing 50-painting batch pipeline,
- expected risk: the wrapper may impose filename, mask-format, or input-size conventions that must be validated before full-scale execution.

The current plan is to stage damaged images and masks into temporary LaMa batch folders with matching filenames, run IOPaint on the staged batch, and then collect outputs back into the project’s standard structure.

Planned LaMa output contract:

- input metadata: `data/processed/metadata/metadata_damaged_images.csv`,
- input damaged images: `data/processed/masked/*.png`,
- input masks: `data/processed/masks/*.png`,
- staged batch input: `outputs/tmp/lama_batch/input/`,
- staged batch masks: `outputs/tmp/lama_batch/mask/`,
- staged batch outputs: `outputs/tmp/lama_batch/output/`,
- final restored images: `data/processed/restored/lama/*.png`,
- final metadata: `data/processed/metadata/metadata_restored_lama.csv`,
- model name: `lama`,
- cases: 250, including zero-control cases.

Zero-control cases should be preserved in the output metadata. If the LaMa runtime does not naturally support empty masks, zero-control outputs may be copied directly from the damaged/clean image with a documented status note rather than passed through the model.

Decision: add LaMa next, after the OpenCV 50-painting baseline and report are stable.

### Implementation status update

LaMa has now been integrated into the controlled 50-painting pipeline.

The implementation uses:

- method source: LaMa paper and official project,
- runtime source: IOPaint CLI with `model=lama`,
- wrapper module: `src/restoration_eval/restoration_lama.py`,
- notebook: `notebooks/11_lama_restoration_cleaned.ipynb`.

A manual IOPaint test was run first on a non-zero damage case and a zero-control case. The zero-control test produced exact zero pixel difference, but the final module still copies zero-control cases directly instead of passing them through the model runtime. This keeps the no-damage control condition independent of external preprocessing behavior.

The module-level notebook test was then run on one painting with all five mask types before scaling to the full subset.

Final LaMa generation output:

- total cases: 250,
- model-inference cases: 200,
- copied zero-control cases: 50,
- restored image directory: `data/processed/restored/lama/`,
- metadata file: `data/processed/metadata/metadata_restored_lama.csv`.

A Windows console encoding issue occurred when IOPaint/Rich emitted Unicode progress characters during subprocess execution. The wrapper was updated to force UTF-8 subprocess handling and reduce decorative console behavior. After this fix, the LaMa notebook test and full run completed successfully.

Current decision: LaMa restoration generation is complete. Next step is metric evaluation using the same framework already used for OpenCV Telea.

## Stable Diffusion Inpainting

Stable Diffusion Inpainting is useful because it is generative, text-conditioned, mask-aware, and seed-controllable. That makes it a strong candidate for uncertainty analysis, especially through multiple sampled restorations for the same damaged painting.

The main risk is hallucination. The model may create visually plausible content that does not match the original painting. This is especially important because the thesis uses synthetic masks, so the clean image is known ground truth. A beautiful but incorrect reconstruction is still an evaluation failure.

Decision: keep as a candidate for later uncertainty analysis, not the next immediate model.

## SDXL Inpainting

SDXL Inpainting is a higher-capacity diffusion candidate. It may produce visually stronger outputs than older Stable Diffusion models, but this can make failure harder to detect: a convincing generated patch may still be historically or structurally wrong.

Decision: keep as a later candidate. Do not add before the simpler generative setup is understood.

## DALL-E / OpenAI Image Editing

OpenAI image editing is useful as an optional closed commercial comparison because it supports masked image editing. However, it has weaker reproducibility and lower training-data transparency. Public documentation also describes mask-guided editing as prompt-based, meaning the mask may guide the edit without guaranteeing exact pixel-level replacement behavior.

Decision: keep optional. It should not be part of the core reproducible experiment.

## Practical order for the 50-painting phase

1. Run OpenCV Telea on all 50 paintings and all planned damage conditions.
2. Confirm metrics, reports, and visual outputs work at 50-painting scale.
3. Add LaMa as the first pretrained open model.
4. Compare OpenCV Telea and LaMa.
5. Add one diffusion inpainting model only after the deterministic comparison is stable.
6. Use multi-seed diffusion outputs for uncertainty analysis on a smaller subset.
7. Treat DALL-E/OpenAI image editing as optional, not required.

## Current conclusion

The thesis should not frame any pretrained model as a ground-truth restoration system. The models are restoration candidates being evaluated under controlled synthetic damage. The key research value is the evaluation framework: how classical, pretrained, and generative inpainting systems behave across painting categories, damage types, and uncertainty conditions.
