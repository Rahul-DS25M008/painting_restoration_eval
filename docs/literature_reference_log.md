# Literature Reference Log

This document records the literature and technical references that support each notebook-level decision in the project.

---

## 1. Preprocessing

### Decision supported

The preprocessing notebook standardizes all paintings for the controlled 50-painting experiment.

Raw painting images are resized while preserving aspect ratio, padded to a fixed 768 × 768 canvas using the median RGB color of the image, and saved as PNG. The valid painting-content region inside the padded image is recorded in metadata.

This supports a shared input format for OpenCV, LaMa, Stable Diffusion, SDXL feasibility testing, LPIPS, CLIP, DINOv2, visual diagnostics, and later uncertainty analysis.

The decision avoids two problematic alternatives:

1. direct square resizing, which geometrically distorts the artwork;
2. center cropping, which can remove real painting content and alter composition.

Later mask generation is restricted to the recorded painting-content region so that synthetic damage is applied only to actual painting pixels, not padding.

### References

#### Suvorov et al. (2022) — Resolution-Robust Large Mask Inpainting with Fourier Convolutions

Relevant point:  
LaMa is designed for large-mask inpainting and uses Fast Fourier Convolutions, high receptive field losses, and large training masks to support wider contextual reasoning. The paper emphasizes that inpainting performance is affected by mask size, context, and image resolution handling. :contentReference[oaicite:1]{index=1}

How Notebook 1 uses it:  
Notebook 1 prepares standardized 768 × 768 images so that later LaMa evaluation can operate under controlled and reproducible image-size conditions. The preprocessing preserves the complete painting composition rather than center-cropping away context that LaMa may need for large-mask inpainting.

#### Hugging Face Diffusers inpainting documentation

Relevant point:  
Diffusers inpainting pipelines use image and mask inputs, and the documentation states that white mask pixels represent the region to inpaint while black pixels represent the region to preserve. It also implies the practical need for controlled input image and mask dimensions in diffusion-based workflows. :contentReference[oaicite:2]{index=2}

How Notebook 1 uses it:  
Notebook 1 standardizes images to a fixed square size that is compatible with later Stable Diffusion and SDXL inpainting workflows. The chosen 768 × 768 size is divisible by 8, preserves more detail than 512 × 512, and remains more practical than 1024 × 1024 on the local hardware.

#### Radford et al. (2021) — CLIP

Relevant point:  
CLIP uses fixed image preprocessing when computing image embeddings. In standard use, this can involve resizing and cropping behavior that may not preserve the full composition of non-square artworks.

How Notebook 1 uses it:  
Notebook 1 records the valid painting-content region so that later CLIP similarity can be interpreted carefully. The project does not rely only on full padded images; later feature metrics are also computed on content regions and mask-bounding-box crops.

#### Oquab et al. (2023) — DINOv2

Relevant point:  
DINOv2 provides strong general-purpose visual features, but like other vision foundation models, it operates on fixed-size spatial image inputs.

How Notebook 1 uses it:  
Notebook 1 stores content-region metadata so that later DINOv2 similarity can be computed and interpreted on meaningful image regions rather than blindly evaluating padded areas or cropped-away painting content.

### Project decision

The project uses aspect-ratio-preserving resize plus median-color padding to 768 × 768.

The notebook records:

- processed image path,
- original dimensions,
- resized dimensions,
- padding offsets,
- painting-content bounding box,
- category metadata.

The preprocessing strategy is selected because it balances:

- preservation of artwork composition,
- reproducibility,
- compatibility with multiple restoration models,
- compatibility with multiple metric families,
- later region-aware evaluation.

### Notes for final thesis writing

This section should be used in the methodology chapter.

Possible thesis wording:

> To avoid geometric distortion and prevent loss of painting content, each painting was resized while preserving its original aspect ratio and padded to a fixed resolution of 768 × 768 pixels. The valid painting-content region inside the padded image was recorded and later used for mask generation and region-specific metric computation. This created standardized model inputs while preserving the complete painting composition.

### Potential improvements / supervisor feedback

- If SDXL is later run on stronger hardware, consider whether SDXL should use 768 × 768 or a larger native resolution.
- Consider adding a small figure in the thesis showing original image, padded image, and recorded content region.

---

## 2. Mask Generation

### Decision supported

The mask-generation notebook creates five deterministic synthetic damage masks per painting:

- `zero_control`,
- `scratch_thin`,
- `loss_small`,
- `loss_large`,
- `mixed_damage`.

Masks are generated only inside the recorded painting-content region. Padded regions are excluded.

The notebook records mask area relative to:

- the painting-content region,
- the full 768 × 768 image.

Mask values follow the standard inpainting convention:

- `0` = preserved/original region,
- `255` = damaged/inpaint region.

### References

#### Liu et al. (2018) — Image Inpainting for Irregular Holes Using Partial Convolutions

Relevant point:  
The paper focuses on inpainting irregular holes rather than only simple rectangular missing regions. It proposes partial convolutions conditioned on valid pixels and uses irregular masks for inpainting evaluation. :contentReference[oaicite:3]{index=3}

How Notebook 2 uses it:  
Notebook 2 uses irregular blob-like masks for `loss_small`, `loss_large`, and parts of `mixed_damage`. This makes the controlled damage setup more realistic than simple rectangles while keeping the mask generation reproducible.

#### Suvorov et al. (2022) — LaMa

Relevant point:  
LaMa is designed for large-mask inpainting and uses large training masks to exploit broader context. The paper reports strong behavior in challenging scenarios involving large missing regions and repeated structures. :contentReference[oaicite:4]{index=4}

How Notebook 2 uses it:  
Notebook 2 includes a `loss_large` condition to test whether models can handle larger missing regions rather than only thin scratches or small local holes. This makes the later OpenCV vs LaMa vs Stable Diffusion comparison more informative.

#### Hugging Face Diffusers inpainting documentation

Relevant point:  
Diffusers inpainting uses white pixels in the mask as the region to repaint and black pixels as the region to preserve. :contentReference[oaicite:5]{index=5}

How Notebook 2 uses it:  
Notebook 2 saves masks as binary grayscale PNG files with `255` for damaged/inpaint pixels and `0` for preserved pixels. This keeps the same mask files compatible with OpenCV, LaMa, Stable Diffusion, SDXL feasibility testing, and evaluation routines.

#### Cultural heritage restoration and inpainting evaluation literature

Relevant point:  
Cultural heritage restoration commonly involves varied degradation patterns such as cracks, scratches, missing paint, fragmented losses, and compound damage. This makes a single generic rectangular mask insufficient for evaluating restoration behavior.

How Notebook 2 uses it:  
Notebook 2 creates multiple synthetic damage families rather than a single mask type. The `scratch_thin` and `mixed_damage` masks are included to approximate crack-like and compound damage patterns, while `loss_small` and `loss_large` provide controlled missing-region difficulty levels.

### Project decision

The project rejects using only rectangular or circular holes.

The selected mask design creates a controlled benchmark with five difficulty conditions:

- `zero_control` for sanity checking and pipeline validation,
- `scratch_thin` for thin crack/scratch-like damage,
- `loss_small` for small missing regions,
- `loss_large` for larger missing regions,
- `mixed_damage` for compound deterioration.

All masks are deterministic through seeded generation. Each mask stores area statistics, content-region relation, bounding-box information, and border-touch information.

### Notes for final thesis writing

This section should explain why the experiment uses several synthetic damage types rather than one generic mask.

Possible thesis wording:

> Artificial damage was simulated using five deterministic mask conditions: no damage, thin scratches, small losses, large losses, and mixed damage. Masks were generated only inside the recorded painting-content region to avoid damaging padded areas introduced during preprocessing. This enabled controlled comparison across damage difficulty while preserving compatibility with all restoration models and metric families.

### Potential improvements / supervisor feedback

- Ask whether the mask types are sufficient for the final thesis experiment or whether additional real-damage-inspired masks should be added.
- Consider adding mask examples in the methodology chapter.
- Consider reporting exact mask area ranges for each damage type in a table.
- If the final dataset scales to 300 paintings, confirm whether the same five mask types should be retained unchanged.

---

## 3. Damage Image Creation

### Decision supported

The damage-creation notebook generates damaged RGB inputs from the clean processed images and binary masks.

For each mask, masked pixels are replaced with white RGB values:

`RGB(255, 255, 255)`

The binary mask remains the authoritative definition of the restoration region.

The damaged image is therefore a controlled input representation of synthetic damage, while the separate mask defines exactly what the models should restore.

### References

#### OpenCV inpainting documentation

Relevant point:  
OpenCV inpainting expects an input image and a single-channel mask where non-zero mask pixels indicate the region to be inpainted.

How Notebook 3 uses it:  
Notebook 3 stores the damaged image and binary mask separately so that Notebook 5 can pass both into OpenCV Telea. The damaged image shows the corrupted input, while the mask tells OpenCV which pixels to restore.

#### Hugging Face Diffusers inpainting documentation

Relevant point:  
Diffusers inpainting workflows use white mask pixels for the region to repaint and black pixels for the region to preserve. :contentReference[oaicite:6]{index=6}

How Notebook 3 uses it:  
Notebook 3 keeps the binary mask as a separate file instead of relying only on the visible white-filled image. This preserves compatibility with later Stable Diffusion and SDXL inpainting pipelines.

#### LaMa / IOPaint implementation conventions

Relevant point:  
LaMa-style inpainting workflows use paired image and mask inputs, where the mask defines the unknown region.

How Notebook 3 uses it:  
Notebook 3 writes standardized damaged images and masks that can later be staged into the IOPaint LaMa runtime. This allows OpenCV, LaMa, and diffusion-based models to use the same controlled cases.

### Project decision

The project uses white-fill synthetic damage for the controlled 50-painting subset.

This is not intended to simulate every physical appearance of real painting deterioration. It is a controlled corruption strategy where:

- the clean reference remains known,
- the damaged pixels are visually obvious,
- the binary mask defines the restoration target,
- all models receive matched image/mask cases.

The notebook records:

- clean image path,
- mask path,
- damaged image path,
- fill strategy,
- fill color,
- damaged area in pixels,
- damaged area relative to content region,
- damaged area relative to full image.

### Notes for final thesis writing

This section should clarify the distinction between synthetic visible damage and the actual evaluation mask.

Possible thesis wording:

> For each synthetic mask, a damaged input image was created by replacing masked pixels with white RGB values while leaving all unmasked pixels unchanged. The binary mask was stored separately and remained the authoritative definition of the restoration target. This ensured that all restoration methods were evaluated on identical controlled damage cases.

### Potential improvements / supervisor feedback

- Ask whether white-fill damage is acceptable as the main controlled corruption strategy.
- Consider testing one additional fill strategy later, such as noise-fill or neutral-color fill, if the supervisor wants input-condition sensitivity.
- Explain clearly in the thesis that white-fill is a controlled synthetic corruption, not a claim that all real painting damage appears white.
- Consider adding a limitation that real degradation can include transparency, discoloration, cracks, flaking, stains, and uneven material loss.

---

## 4. OpenCV Telea Restoration Baseline

### Decision supported

The OpenCV restoration notebook uses OpenCV Telea as the first restoration baseline.

OpenCV Telea is included as a deterministic classical inpainting method. It is not treated as painting-specific or conservation-grade.

Its role is to provide a simple, fast, reproducible baseline before evaluating learned and generative inpainting models.

### References

#### Telea (2004) — An Image Inpainting Technique Based on the Fast Marching Method

Relevant point:  
Telea proposes a fast marching method for digital inpainting, where missing regions are filled progressively from their boundaries using nearby image information. The method is fast, simple to implement, and suitable for filling small damaged image regions. :contentReference[oaicite:7]{index=7}

How Notebook 4 uses it:  
Notebook 4 uses OpenCV’s implementation of the Telea method as the deterministic classical baseline. A fixed radius is used across all cases to keep the baseline reproducible and comparable.

#### Bertalmio et al. (2000) — Image Inpainting

Relevant point:  
This foundational paper frames image inpainting as filling user-selected missing regions by propagating surrounding image information into the target area.

How Notebook 4 uses it:  
Notebook 4 uses this general inpainting framing: the binary synthetic damage mask defines the missing region, and the algorithm attempts to fill that known target area.

#### Quan et al. (2024) — Deep Learning-based Image and Video Inpainting: A Survey

Relevant point:  
The survey reviews modern inpainting methods and helps position classical inpainting methods relative to CNN-, GAN-, transformer-, and diffusion-based approaches.

How Notebook 4 uses it:  
Notebook 4 uses OpenCV Telea as the pre-deep-learning baseline before later adding LaMa and Stable Diffusion. This supports the staged model stack: classical baseline first, then learned inpainting, then generative diffusion inpainting.

#### OpenCV inpainting documentation

Relevant point:  
OpenCV’s inpainting function accepts an input image and an inpainting mask, with non-zero mask pixels indicating the area to be restored.

How Notebook 4 uses it:  
Notebook 4 passes the white-filled damaged image and binary mask into OpenCV Telea. The same mask convention used in earlier notebooks is preserved.

### Project decision

The project uses OpenCV Telea with a fixed inpainting radius of `3`.

The same radius is applied to all:

- 50 paintings,
- 5 mask types,
- 250 total damage cases.

Zero-control cases are passed through the same metadata pipeline for consistency, while non-zero masks provide the actual restoration baseline.

OpenCV Telea is expected to behave better on thin scratches and small local damage than on large missing regions or complex mixed damage. This limitation is useful because the thesis evaluates where different restoration methods succeed or fail.

### Notes for final thesis writing

This section should introduce the classical baseline.

Possible thesis wording:

> OpenCV Telea was included as a deterministic classical inpainting baseline. The method fills missing regions progressively from their boundaries using nearby image information. It provides a fast and reproducible non-learning reference point, but it is not expected to recover large semantic structures or painting-specific stylistic detail. In this thesis, OpenCV Telea therefore serves as the first baseline against which learned and generative inpainting methods are compared.

### Potential improvements / supervisor feedback

- Ask whether OpenCV Navier-Stokes should also be included as a second classical baseline or whether Telea alone is sufficient.
- Consider a small radius-sensitivity check for OpenCV Telea, for example radius 1, 3, and 5, but only if the supervisor wants baseline ablation.
- In the final thesis, use OpenCV results mainly to show why classical local interpolation is insufficient for large or complex painting damage.

## 5. Classical Metric Evaluation

### Decision supported

The classical metric notebook evaluates OpenCV Telea outputs against the clean reference paintings using full-reference image quality metrics.

The decision supported by this notebook is to include classical pixel-level and structural metrics as the first quantitative evaluation layer.

The metrics are:

- MSE,
- MAE,
- PSNR,
- SSIM.

The notebook evaluates metrics across multiple regions:

- full image,
- painting-content region,
- masked region,
- mask bounding-box crop.

This region-aware design is important because full-image metrics can hide restoration failures when the damaged region is small.

### References

#### Wang et al. (2004) — Image Quality Assessment: From Error Visibility to Structural Similarity

Relevant point:  
Wang et al. introduce SSIM as a structural image-quality metric designed to move beyond simple pixel-error visibility. SSIM compares local luminance, contrast, and structure, so it assumes spatial image neighborhoods.

How Notebook 5 uses it:  
Notebook 5 includes SSIM as the structural metric in the classical metric stack. SSIM is computed only on image-like spatial regions: full image, content region, and mask bounding-box crop. It is not treated as suitable for unordered sparse masked pixels.

#### Hore and Ziou (2010) — Image Quality Metrics: PSNR vs. SSIM

Relevant point:  
This paper compares PSNR and SSIM and highlights that distortion-based and structural metrics capture different aspects of image quality.

How Notebook 5 uses it:  
Notebook 5 includes both PSNR and SSIM rather than relying on only one classical metric. PSNR provides a signal based on pixel-error magnitude, while SSIM provides a structural similarity signal.

#### Zhang et al. (2018) — The Unreasonable Effectiveness of Deep Features as a Perceptual Metric

Relevant point:  
Zhang et al. show that traditional metrics such as PSNR and SSIM do not always align with human perceptual similarity.

How Notebook 5 uses it:  
Notebook 5 treats classical metrics as necessary but insufficient. The notebook establishes the classical metric baseline, while later notebooks add LPIPS, CLIP, and DINOv2 to address perceptual and feature-space limitations.

#### Quan et al. (2024) — Deep Learning-based Image and Video Inpainting: A Survey

Relevant point:  
The survey discusses modern inpainting methods and common evaluation practices, including the continued use of full-reference metrics alongside perceptual and learned metrics.

How Notebook 5 uses it:  
Notebook 5 uses classical metrics as the first evaluation layer before later model comparisons. The metrics are retained because the project uses synthetic damage, so the clean reference is known.

### Project decision

The project computes MSE, MAE, PSNR, and SSIM for OpenCV Telea results.

The main local interpretation uses:

- masked-region MSE and PSNR for direct damaged-pixel comparison,
- mask-bounding-box SSIM for local structural comparison,
- full-image and content-region scores as secondary context.

Full-image scores are interpreted cautiously because unchanged pixels dominate the result.

SSIM is treated differently from MSE and PSNR because it requires spatial context. This decision later becomes important in Notebook 26, where the final metric-region policy is refined.

### Notes for final thesis writing

This section should explain why classical metrics are included but not treated as final restoration truth.

Possible thesis wording:

> Classical full-reference metrics were computed to quantify pixel-level and structural similarity between clean reference paintings, damaged inputs, and restored outputs. MSE, MAE, and PSNR were used as distortion-based measures, while SSIM was used as a structural similarity measure. Metrics were computed across full-image, content-region, masked-region, and mask-bounding-box regions to avoid hiding local restoration failures behind mostly unchanged image areas. Classical metrics were treated as useful but insufficient, motivating later perceptual and feature-space evaluation layers.

### Potential improvements / supervisor feedback

- Consider adding a short metric-region-policy figure in the thesis.
- Consider including a limitation that classical full-reference metrics are possible only because the experiment uses synthetic damage with known clean references.

---

## 6. Difference-Map Diagnostic Evaluation

### Decision supported

The difference-map notebook adds visual diagnostic evaluation for OpenCV Telea results.

The decision supported by this notebook is that scalar metrics alone are not enough. Difference maps are needed to show where restoration errors remain, improve, or worsen.

The notebook generates spatial maps for:

- clean vs damaged absolute error,
- clean vs restored absolute error,
- signed restoration improvement,
- masked signed restoration improvement.

### References

#### Wang et al. (2004) — SSIM

Relevant point:  
Wang et al. motivate image-quality assessment beyond direct pixel-error visibility, but scalar metrics still summarize quality into compact scores.

How Notebook 6 uses it:  
Notebook 6 complements scalar structural and pixel metrics with spatial diagnostics. Where SSIM and MSE summarize quality numerically, difference maps show where local errors occur.

#### Zhang et al. (2018) — LPIPS

Relevant point:  
Zhang et al. show that traditional pixel-level metrics may not align with perceptual similarity.

How Notebook 6 uses it:  
Notebook 6 uses visual error maps to inspect cases where scalar pixel metrics may not tell the full story. This prepares the framework for later perceptual and feature-space metrics.

#### Quan et al. (2024) — Deep Learning-based Image and Video Inpainting: A Survey

Relevant point:  
Modern inpainting evaluation often combines quantitative metrics with qualitative examples because inpainting quality is spatially and perceptually complex.

How Notebook 6 uses it:  
Notebook 6 formalizes the qualitative diagnostic layer rather than relying on manually selected “nice-looking” examples. Diagnostic cases are selected based on metric behavior.

### Project decision

The project generates difference-map diagnostics for OpenCV Telea restoration outputs.

For each selected or generated case, the notebook shows:

- clean reference,
- binary mask,
- damaged input,
- restored output,
- clean-vs-damaged error,
- clean-vs-restored error,
- restoration improvement map.

The signed improvement map is computed as:

`damaged_error - restored_error`

Positive values indicate that restoration reduced error relative to the damaged input. Negative values indicate that the restored output became farther from the clean reference.

### Notes for final thesis writing

This section should support the argument that the framework combines scalar and spatial evidence.

Possible thesis wording:

> Difference maps were generated to complement scalar full-reference metrics by visualizing where restoration errors remained or improved. Absolute error maps were computed between the clean reference and both the damaged and restored images. A signed improvement map was then calculated by subtracting restored error from damaged-input error. This enabled inspection of whether numerical improvement corresponded to meaningful local restoration behavior.

### Potential improvements / supervisor feedback

- Consider standardizing the difference-map color scale across all models for fair visual comparison.
- Consider adding side-by-side difference maps to the final per-case report template.
- Consider adding texture/error overlays after Notebook 31, especially for cases where texture metrics disagree with pixel metrics.

---

## 7. LPIPS Perceptual Metric Evaluation

### Decision supported

The LPIPS notebook adds a perceptual full-reference metric to the OpenCV Telea evaluation branch.

The decision supported by this notebook is to include learned perceptual similarity as a complementary metric family because classical pixel-level and structural metrics are not sufficient for restoration evaluation.

The notebook computes LPIPS between:

- clean reference and damaged input,
- clean reference and restored output.

LPIPS improvement is computed as:

`damaged_lpips - restored_lpips`

Positive improvement means the restoration is perceptually closer to the clean reference than the damaged input.

### References

#### Zhang et al. (2018) — The Unreasonable Effectiveness of Deep Features as a Perceptual Metric

Relevant point:  
Zhang et al. introduce LPIPS and show that distances in deep feature spaces can better align with human perceptual judgments than traditional metrics such as PSNR and SSIM.

How Notebook 7 uses it:  
Notebook 7 computes LPIPS as a perceptual-distance metric for restoration outputs. It is used to test whether OpenCV-restored regions are closer to the clean reference in learned perceptual feature space.

#### Quan et al. (2024) — Deep Learning-based Image and Video Inpainting: A Survey

Relevant point:  
The survey discusses modern inpainting evaluation and the need to evaluate generated outputs with multiple metric types rather than only pixel-level measures.

How Notebook 7 uses it:  
Notebook 7 adds LPIPS as the next metric family after classical metrics, supporting the project’s multi-metric evaluation design.

#### Fontoura Júnior et al. (2023) — Assessing the Effectiveness of Inpainting Techniques in Cultural Heritage

Relevant point:  
The paper evaluates image inpainting in a cultural heritage context and supports the need for careful assessment beyond simple visual inspection or one metric.

How Notebook 7 uses it:  
Notebook 7 uses LPIPS as a perceptual metric in a controlled cultural-heritage-inspired restoration benchmark. The notebook does not claim LPIPS is conservation-specific, but uses it as one diagnostic layer.

### Project decision

The project computes LPIPS on image-like regions only:

- full image,
- content region,
- mask bounding-box crop.

LPIPS is not computed directly on sparse masked pixels because LPIPS depends on spatial feature activations from image patches.

The mask-bounding-box crop acts as the local perceptual comparison region around the damaged area.

### Notes for final thesis writing

This section should explain why perceptual similarity is added after classical metrics.

Possible thesis wording:

> LPIPS was included as a learned perceptual-distance metric to complement classical pixel-level and structural measures. Since LPIPS operates on spatial image inputs, it was computed on the full image, painting-content region, and mask-bounding-box crop rather than on sparse masked pixels. The mask-bounding-box crop provided a local perceptual comparison region around the damaged area. LPIPS scores were interpreted as perceptual diagnostic evidence, not as proof of conservation correctness.

### Potential improvements / supervisor feedback

- Consider comparing LPIPS behavior against texture metrics after Notebook 31.
- Consider reporting LPIPS disagreement cases where perceptual improvement conflicts with MSE or DINOv2.

---

## 8. CLIP and DINOv2 Feature-Space Similarity

### Decision supported

The feature-similarity notebook adds pretrained visual feature-space diagnostics to the OpenCV Telea evaluation branch.

The decision supported by this notebook is to evaluate restoration outputs not only through pixel, structural, and perceptual metrics, but also through broader pretrained visual representations.

The notebook computes cosine similarity between embeddings for:

- clean reference vs damaged input,
- clean reference vs restored output.

Feature-space improvement is computed as:

`restored_similarity - damaged_similarity`

Positive improvement means the restored output is closer to the clean reference in that feature space.

### References

#### Radford et al. (2021) — Learning Transferable Visual Models From Natural Language Supervision

Relevant point:  
CLIP learns transferable visual representations through contrastive image-text training.

How Notebook 8 uses it:  
Notebook 8 uses CLIP image embeddings as a broad semantic/visual feature-space diagnostic. CLIP is not used as a conservation judge. It is used to detect whether restored outputs move closer to the clean reference in a pretrained visual representation space.

#### Oquab et al. (2023) — DINOv2: Learning Robust Visual Features without Supervision

Relevant point:  
DINOv2 learns robust general-purpose visual features through self-supervised learning and is designed to provide strong visual representations without language supervision.

How Notebook 8 uses it:  
Notebook 8 uses DINOv2 embeddings as a complementary feature-space diagnostic distinct from CLIP. DINOv2 provides a self-supervised visual representation, while CLIP provides an image-text-supervised representation.

#### Zhang et al. (2018) — LPIPS

Relevant point:  
LPIPS motivates the use of deep features for perceptual similarity and shows why shallow pixel metrics may be insufficient.

How Notebook 8 uses it:  
Notebook 8 extends the deep-feature evaluation idea beyond LPIPS by using pretrained foundation-model embeddings as diagnostic feature spaces.

#### Fontoura Júnior et al. (2023) — Assessing the Effectiveness of Inpainting Techniques in Cultural Heritage

Relevant point:  
The cultural heritage inpainting evaluation context supports using several complementary criteria to assess inpainting results.

How Notebook 8 uses it:  
Notebook 8 adds CLIP and DINOv2 as additional non-conservation-specific but useful diagnostic signals in the controlled restoration framework.

### Project decision

The project computes CLIP and DINOv2 similarity on image-like spatial regions:

- full image,
- content region,
- mask bounding-box crop.

Sparse masked pixels are not used directly because CLIP and DINOv2 expect spatial image inputs.

The mask-bounding-box crop is used as the local feature-space comparison region around the damaged area.

The selected feature models are:

- CLIP: `openai/clip-vit-base-patch32`,
- DINOv2: project helper model `dinov2_vitb14`.

### Notes for final thesis writing

This section should explain why CLIP and DINOv2 are diagnostic feature spaces, not final restoration authorities.

Possible thesis wording:

> CLIP and DINOv2 feature similarities were included to complement classical and LPIPS metrics with pretrained visual representations. CLIP provides an image-text-supervised representation space, while DINOv2 provides a self-supervised visual representation space. Similarity was computed between clean and damaged regions and between clean and restored regions. Improvements were interpreted as diagnostic evidence of feature-space closeness to the known clean reference, not as proof of historical or conservation faithfulness.

### Potential improvements / supervisor feedback

- Consider adding a semantic/iconographic consistency layer after supervisor feedback, but keep it separate from this feature-similarity notebook.
- Consider comparing DINOv2 and texture metrics for high-texture brushwork paintings.
- Consider reporting cases where CLIP improves but DINOv2 worsens, because this may indicate semantic plausibility without local structural fidelity.

---

## 9. OpenCV Baseline Report Interpretation

### Decision supported

The OpenCV baseline report consolidates the first complete model-specific evaluation branch.

The decision supported by this notebook is to treat OpenCV Telea as a fully evaluated baseline, not only as a restoration-output generator.

The report combines:

- classical metrics,
- LPIPS,
- CLIP and DINOv2 feature similarity,
- difference-map diagnostics,
- selected visual cases,
- mask-type summaries,
- category summaries.

### References

#### Telea (2004) — Fast Marching Method inpainting

Relevant point:  
Telea defines the classical inpainting method behind the OpenCV baseline.

How Notebook 9 uses it:  
Notebook 9 interprets OpenCV Telea results as a deterministic classical baseline. The report does not treat Telea as painting-specific or conservation-grade.

#### Wang et al. (2004) — SSIM

Relevant point:  
SSIM motivates structural image-quality assessment beyond pixel error.

How Notebook 9 uses it:  
Notebook 9 includes SSIM results as part of the classical metric summary and interprets them alongside MSE, PSNR, LPIPS, CLIP, and DINOv2.

#### Zhang et al. (2018) — LPIPS

Relevant point:  
LPIPS motivates perceptual similarity evaluation using deep features.

How Notebook 9 uses it:  
Notebook 9 includes LPIPS summaries to show whether OpenCV-restored outputs improve perceptual closeness to the clean reference.

#### Radford et al. (2021) — CLIP

Relevant point:  
CLIP provides transferable image representations learned through image-text supervision.

How Notebook 9 uses it:  
Notebook 9 uses CLIP summaries as a broad feature-space diagnostic, not as a restoration-quality verdict.

#### Oquab et al. (2023) — DINOv2

Relevant point:  
DINOv2 provides robust self-supervised visual representations.

How Notebook 9 uses it:  
Notebook 9 uses DINOv2 summaries as a visual feature-space diagnostic that complements CLIP and LPIPS.

#### Fontoura Júnior et al. (2023) — Cultural heritage inpainting evaluation

Relevant point:  
The paper supports careful, multi-criteria evaluation of inpainting in cultural heritage contexts.

How Notebook 9 uses it:  
Notebook 9 frames the OpenCV report as a multi-layer diagnostic report rather than a single-score evaluation.

### Project decision

The project generates a standalone OpenCV Telea report as the first complete model-level artifact.

The report does not treat any single metric as definitive. Instead, it uses disagreement between metric families as diagnostic evidence.

The report emphasizes that OpenCV Telea can reduce obvious white synthetic damage, especially in scratch-like or small-loss cases, but often fails to recover faithful local structure in larger or more complex damage cases.

### Notes for final thesis writing

This section should support the thesis argument that even a simple baseline can appear improved under some metrics while still failing under others.

Possible thesis wording:

> The OpenCV Telea baseline report consolidated the first complete evaluation branch. It combined classical metrics, LPIPS, CLIP and DINOv2 feature similarities, and spatial diagnostic maps. The results showed that OpenCV can reduce obvious synthetic damage, particularly for thin scratches and small local masks, but it is limited for larger missing regions. Metric disagreement in the report supports the thesis argument that restoration trustworthiness cannot be summarized by a single scalar score.

### Potential improvements / supervisor feedback

- Ask whether OpenCV report figures should remain as model-specific appendix material or be merged into the final consolidated report.
- Consider adding texture metric summaries to an extended OpenCV report after Notebook 31.
- Consider using OpenCV examples in the final thesis as a clear baseline failure/success comparison.
- Avoid over-updating the old OpenCV report; preserve it as a stable intermediate artifact and add new texture-aware interpretation in the extended final report.

## 10. LaMa Implementation Planning

### Decision supported

The LaMa planning notebook selects LaMa as the first pretrained learned inpainting baseline after the OpenCV Telea classical baseline.

This notebook supports the decision to extend the model stack from:

- deterministic local interpolation: OpenCV Telea,

to:

- pretrained learned image inpainting: LaMa.

LaMa is selected because it is specifically designed for large-mask inpainting and can use broader image context than local classical interpolation methods.

### References

#### Suvorov et al. (2022) — Resolution-Robust Large Mask Inpainting with Fourier Convolutions

Relevant point:  
LaMa introduces a resolution-robust inpainting approach based on Fast Fourier Convolutions, large receptive fields, and training strategies intended to improve large-mask inpainting.

How Notebook 10 uses it:  
Notebook 10 uses the LaMa paper as the methodological reason for adding LaMa after OpenCV Telea. Since the controlled benchmark includes `loss_large` and `mixed_damage` masks, LaMa provides a stronger learned baseline for cases where local interpolation is expected to struggle.

#### Quan et al. (2024) — Deep Learning-based Image and Video Inpainting: A Survey

Relevant point:  
The survey places modern learned inpainting approaches in the broader progression from classical methods to CNN-, GAN-, transformer-, and diffusion-based systems.

How Notebook 10 uses it:  
Notebook 10 uses this broader survey context to justify the staged model stack: classical baseline first, learned pretrained inpainting second, diffusion-based inpainting later.

#### Fontoura Júnior et al. (2023) — Assessing the Effectiveness of Inpainting Techniques in Cultural Heritage

Relevant point:  
The paper evaluates inpainting techniques in a cultural heritage context and supports careful comparison of inpainting methods instead of assuming one model family is universally superior.

How Notebook 10 uses it:  
Notebook 10 frames LaMa as a candidate restoration model to be evaluated under controlled painting damage, not as an automatically trustworthy restoration system.

### Project decision

The project selects LaMa as the second restoration model in the controlled 50-painting experiment.

The implementation is planned through IOPaint using `model=lama`, while the LaMa paper remains the methodological source.

This practical runtime decision is made because IOPaint supports batch-oriented command-line execution and fits the existing project structure.

### Notes for final thesis writing

This section should introduce LaMa as the first learned pretrained inpainting baseline.

Possible thesis wording:

> LaMa was selected as the first pretrained learned inpainting baseline after OpenCV Telea. Its architecture was designed for large-mask inpainting and therefore provides a useful comparison against a deterministic local interpolation baseline. Since LaMa is not trained specifically for painting conservation, its outputs are evaluated as candidate restorations rather than assumed faithful reconstructions.

### Potential improvements / supervisor feedback

- Ask whether LaMa is sufficient as the main non-diffusion learned baseline or whether another modern inpainting model should be added.
- Clarify in the thesis that IOPaint is the runtime wrapper, while the LaMa paper is the method reference.
- Consider documenting LaMa’s domain gap more explicitly, since it is trained for general image inpainting rather than painting conservation.
- If final compute allows, compare LaMa against a more recent transformer or diffusion inpainting model, but only if this does not derail the thesis.

---

## 11. LaMa Restoration Runtime Integration

### Decision supported

The LaMa runtime notebook integrates LaMa into the project pipeline as a reproducible batch restoration method.

This notebook supports the decision to treat LaMa as a fully operational restoration baseline, not just as a planned model.

The practical implementation uses:

- IOPaint runtime,
- `model=lama`,
- temporary staging folders,
- standardized image and mask filenames,
- project metadata output.

### References

#### Suvorov et al. (2022) — LaMa

Relevant point:  
The LaMa paper defines the inpainting method being evaluated.

How Notebook 11 uses it:  
Notebook 11 generates restoration outputs using an implementation of LaMa so that the method can be evaluated under the same controlled synthetic damage cases as OpenCV Telea.

#### IOPaint documentation and implementation

Relevant point:  
IOPaint provides a practical runtime interface for LaMa and supports command-line batch inpainting workflows.

How Notebook 11 uses it:  
Notebook 11 uses IOPaint as the execution layer. The notebook stages damaged images and masks into temporary folders with matching filenames, invokes IOPaint through a subprocess, and collects outputs into the project’s standardized restored-image directory.

#### Hugging Face / general inpainting mask conventions

Relevant point:  
Modern inpainting runtimes generally require paired image and binary mask inputs, with the mask identifying the inpaint region.

How Notebook 11 uses it:  
Notebook 11 reuses the same damaged image and binary mask files generated earlier in the pipeline. This preserves model comparability because LaMa receives the same controlled damage cases as OpenCV.

### Project decision

The project integrates LaMa through a wrapper module:

`src/restoration_eval/restoration_lama.py`

The wrapper:

- stages input images and masks,
- ensures filename matching,
- runs IOPaint LaMa through a controlled subprocess call,
- collects restored outputs,
- writes standardized restoration metadata,
- handles Windows console encoding issues by forcing UTF-8 output where needed.

Zero-control cases are handled consistently with the project’s metadata pipeline.

### Notes for final thesis writing

This section should describe the implementation choice without overclaiming.

Possible thesis wording:

> LaMa was executed through IOPaint as a practical batch runtime. Damaged images and binary masks were staged into temporary folders with matching filenames, processed using the LaMa model, and collected into the project’s standardized output structure. This implementation choice allowed LaMa outputs to be evaluated using the same metadata, masks, and metric framework as OpenCV Telea.

### Potential improvements / supervisor feedback

None

---

## 12. LaMa Classical Metric Evaluation

### Decision supported

The LaMa classical metric notebook evaluates LaMa outputs using the same classical full-reference metric framework used for OpenCV Telea.

This supports direct model comparison because both models are evaluated against:

- the same clean references,
- the same damaged inputs,
- the same masks,
- the same evaluation regions,
- the same metric definitions.

### References

#### Wang et al. (2004) — SSIM

Relevant point:  
SSIM measures structural similarity using local spatial image neighborhoods.

How Notebook 12 uses it:  
Notebook 12 computes SSIM for LaMa outputs on spatial image-like regions, including the mask-bounding-box crop. This keeps SSIM interpretation consistent with the OpenCV metric notebook.

#### Hore and Ziou (2010) — PSNR vs. SSIM

Relevant point:  
PSNR and SSIM measure different aspects of image quality: pixel-error distortion and structural similarity.

How Notebook 12 uses it:  
Notebook 12 computes both PSNR and SSIM for LaMa so that LaMa can be compared to OpenCV across classical metric families.

#### Zhang et al. (2018) — LPIPS

Relevant point:  
LPIPS shows that classical metrics may not align with perceptual similarity.

How Notebook 12 uses it:  
Notebook 12 treats classical metrics as one evaluation layer only. The notebook prepares the LaMa branch for later LPIPS and feature-space evaluation.

#### Suvorov et al. (2022) — LaMa

Relevant point:  
LaMa is designed for learned large-mask inpainting.

How Notebook 12 uses it:  
Notebook 12 evaluates whether LaMa’s expected strength on larger masks is reflected in full-reference classical metrics under the controlled painting benchmark.

### Project decision

The project computes MSE, MAE, PSNR, and SSIM for LaMa outputs.

The same region structure used for OpenCV is retained:

- full image,
- content region,
- masked region,
- mask bounding-box crop.

Masked-region MSE and PSNR directly evaluate the damaged pixels. Mask-bounding-box SSIM provides local structural comparison using spatial context.

### Notes for final thesis writing

This section should emphasize paired evaluation consistency.

Possible thesis wording:

> LaMa outputs were evaluated using the same classical metric framework as OpenCV Telea. This enabled paired comparison across identical paintings, masks, and damage conditions. Classical metrics quantified numerical similarity to the known clean reference, but they were not treated as sufficient evidence of restoration quality because LaMa may generate plausible content that is not necessarily perceptually or historically faithful.

### Potential improvements / supervisor feedback

- Consider adding a classical-metric comparison table showing LaMa vs OpenCV by mask type.
- Consider reporting whether LaMa’s advantage increases with larger mask types.
- Preserve the interpretation that classical metrics are valid under synthetic damage but unavailable in real restoration cases without clean references.

---

## 13. LaMa Difference/Error-Map Diagnostics

### Decision supported

The LaMa difference-map notebook generates spatial diagnostic figures for LaMa outputs using the same visual diagnostic framework used for OpenCV Telea.

This supports direct qualitative and spatial comparison between models.

The notebook visualizes:

- clean reference,
- binary mask,
- damaged input,
- LaMa restoration,
- clean-vs-damaged absolute error,
- clean-vs-restored absolute error,
- signed restoration improvement,
- masked signed improvement.

### References

#### Wang et al. (2004) — SSIM and image quality assessment

Relevant point:  
Scalar image-quality measures summarize image similarity but do not localize errors visually.

How Notebook 13 uses it:  
Notebook 13 complements scalar metrics with spatial maps so that LaMa’s local behavior can be inspected visually.

#### Zhang et al. (2018) — LPIPS

Relevant point:  
Perceptual similarity may diverge from direct pixel-level error.

How Notebook 13 uses it:  
Notebook 13 uses difference maps as a diagnostic bridge between classical metrics and later perceptual metrics. It helps identify cases where numerical error reduction may still look visually problematic.

#### Fontoura Júnior et al. (2023) — Cultural heritage inpainting evaluation

Relevant point:  
Cultural heritage inpainting assessment benefits from careful visual and quantitative evaluation because restoration quality cannot be reduced to a single measure.

How Notebook 13 uses it:  
Notebook 13 creates visual diagnostics for LaMa so that the report can discuss where learned inpainting succeeds, fails, or changes local structure.

### Project decision

The project generates LaMa error-map diagnostics with the same structure as OpenCV diagnostics.

The signed improvement map is computed as:

`damaged_error - restored_error`

Positive values indicate reduced error after restoration. Negative values indicate that the restored image became farther from the clean reference.

The notebook uses selected diagnostic cases rather than relying only on manually pleasing examples.

### Notes for final thesis writing

This section should support the visual-diagnostic part of the methodology.

Possible thesis wording:

> Spatial error-map diagnostics were generated for LaMa using the same structure as the OpenCV baseline. These maps localized where LaMa reduced or increased error relative to the damaged input. The maps were interpreted as diagnostic evidence rather than final restoration judgments, because visual plausibility and reference similarity can diverge in learned inpainting outputs.

### Potential improvements / supervisor feedback

- Ask whether LaMa and OpenCV diagnostic maps should be shown side-by-side in the final thesis.
- Consider adding texture-aware overlays after Notebook 31 for selected LaMa cases.
- Consider standardizing all error-map scales across OpenCV, LaMa, and Stable Diffusion for fair visual comparison.
- Use LaMa error maps to identify thesis examples where learned inpainting improves metrics but smooths texture.

---

## 14. LaMa LPIPS Perceptual Metric Evaluation

### Decision supported

The LaMa LPIPS notebook evaluates LaMa outputs with the same perceptual metric framework used for OpenCV Telea.

This supports direct comparison between a classical method and a learned inpainting model in perceptual feature space.

The notebook computes LPIPS between:

- clean reference and damaged input,
- clean reference and LaMa-restored output.

LPIPS improvement is computed as:

`damaged_lpips - restored_lpips`

Positive improvement means the restoration is perceptually closer to the clean reference.

### References

#### Zhang et al. (2018) — LPIPS

Relevant point:  
LPIPS uses deep feature distances and was shown to align better with perceptual similarity than traditional metrics such as PSNR and SSIM in many image comparison settings.

How Notebook 14 uses it:  
Notebook 14 computes LPIPS for LaMa outputs to evaluate whether LaMa restorations are perceptually closer to the clean reference than the damaged inputs.

#### Suvorov et al. (2022) — LaMa

Relevant point:  
LaMa is a learned inpainting model designed to synthesize missing image content, especially for larger masks.

How Notebook 14 uses it:  
Notebook 14 uses LPIPS to test whether LaMa’s learned completions improve perceptual similarity, not only pixel-level similarity.

#### Quan et al. (2024) — Deep Learning-based Image and Video Inpainting: A Survey

Relevant point:  
Modern inpainting evaluation commonly uses multiple metric families, including perceptual metrics, because generated outputs can differ from reference images in complex ways.

How Notebook 14 uses it:  
Notebook 14 adds LPIPS as the perceptual evaluation layer for LaMa, matching the multi-metric design already applied to OpenCV.

### Project decision

The project computes LPIPS for LaMa on image-like spatial regions:

- full image,
- content region,
- mask bounding-box crop.

Sparse masked pixels are not used because LPIPS expects spatial image patches.

The mask-bounding-box crop is used as the local perceptual comparison region around the damage.

### Notes for final thesis writing

This section should explain that LPIPS is reused consistently across model branches.

Possible thesis wording:

> LPIPS was computed for LaMa using the same region policy as the OpenCV baseline: full image, painting-content region, and mask-bounding-box crop. The metric provides a learned perceptual-distance signal and helps identify whether LaMa outputs are perceptually closer to the clean reference. It is interpreted as a diagnostic metric, not as a conservation-specific judgment.

### Potential improvements / supervisor feedback

- Consider analyzing cases where LaMa improves LPIPS but worsens DINOv2 or texture distance.
- Add a limitation that LPIPS is not trained specifically for painting conservation.
- Consider reporting LPIPS results mainly on the mask-bounding-box crop in the final thesis.

---

## 15. LaMa CLIP and DINOv2 Feature-Space Similarity Evaluation

### Decision supported

The LaMa feature-similarity notebook evaluates LaMa outputs using CLIP and DINOv2 embeddings.

This supports model comparison in pretrained visual feature spaces and matches the feature-evaluation framework already applied to OpenCV Telea.

The notebook computes cosine similarity between:

- clean reference vs damaged input,
- clean reference vs LaMa-restored output.

Feature-space improvement is computed as:

`restored_similarity - damaged_similarity`

Positive improvement indicates that the restoration moved closer to the clean reference in the selected feature space.

### References

#### Radford et al. (2021) — CLIP

Relevant point:  
CLIP provides transferable image representations learned through image-text contrastive training.

How Notebook 15 uses it:  
Notebook 15 uses CLIP image embeddings as a broad semantic/visual feature-space diagnostic for LaMa outputs. CLIP is not used as a conservation-specific restoration metric.

#### Oquab et al. (2023) — DINOv2

Relevant point:  
DINOv2 provides robust self-supervised visual features that can capture visual structure without language supervision.

How Notebook 15 uses it:  
Notebook 15 uses DINOv2 embeddings as a complementary self-supervised visual feature space for evaluating LaMa restoration similarity.

#### Zhang et al. (2018) — LPIPS

Relevant point:  
LPIPS supports the broader idea that learned deep feature spaces can be useful for perceptual comparison.

How Notebook 15 uses it:  
Notebook 15 extends learned-feature evaluation beyond LPIPS by using foundation-model embeddings for diagnostic similarity.

#### Fontoura Júnior et al. (2023) — Cultural heritage inpainting evaluation

Relevant point:  
Cultural heritage inpainting requires careful multi-criteria assessment.

How Notebook 15 uses it:  
Notebook 15 adds CLIP and DINOv2 as complementary evidence in the controlled painting restoration framework, while keeping their limitations explicit.

### Project decision

The project computes CLIP and DINOv2 similarity for LaMa on:

- full image,
- content region,
- mask bounding-box crop.

Sparse masked pixels are not used because both feature models expect spatial image inputs.

The selected feature models are:

- CLIP: `openai/clip-vit-base-patch32`,
- DINOv2: project helper model `dinov2_vitb14`.

### Notes for final thesis writing

This section should explain that CLIP and DINOv2 are reused consistently across model branches.

Possible thesis wording:

> CLIP and DINOv2 feature-space similarities were computed for LaMa outputs using the same region policy as the OpenCV baseline. These metrics provide diagnostic feature-space evidence but do not determine restoration correctness. Disagreement between CLIP, DINOv2, LPIPS, and classical metrics was retained because it reveals different restoration behavior across metric families.

### Potential improvements / supervisor feedback

- Consider reporting CLIP/DINOv2 disagreements as qualitative diagnostic examples.
- After Notebook 31, compare DINOv2 similarity with texture metrics for high-texture paintings.
- Later semantic/iconographic checks should be separated from this feature-similarity metric, because CLIP similarity alone is not an iconographic validation method.

---

## 16. LaMa Standalone Baseline Report

### Decision supported

The LaMa report notebook consolidates the full LaMa evaluation branch into a standalone report.

This supports the decision to evaluate LaMa as a complete model baseline across multiple evidence layers before comparing it against other models.

The report combines:

- restoration metadata,
- classical metrics,
- LPIPS,
- CLIP and DINOv2 feature similarity,
- difference-map diagnostics,
- mask-type summaries,
- category summaries,
- selected visual examples.

### References

#### Suvorov et al. (2022) — LaMa

Relevant point:  
LaMa provides the method basis for the learned inpainting baseline.

How Notebook 16 uses it:  
Notebook 16 interprets LaMa results as outputs from a learned pretrained inpainting model designed for large-mask scenarios, while still treating them as candidates requiring evaluation.

#### Zhang et al. (2018) — LPIPS

Relevant point:  
LPIPS supports perceptual similarity evaluation beyond classical metrics.

How Notebook 16 uses it:  
Notebook 16 includes LPIPS summaries to interpret LaMa behavior in perceptual feature space.

#### Radford et al. (2021) — CLIP

Relevant point:  
CLIP provides a broad transferable image representation.

How Notebook 16 uses it:  
Notebook 16 includes CLIP feature-similarity summaries as diagnostic evidence.

#### Oquab et al. (2023) — DINOv2

Relevant point:  
DINOv2 provides robust self-supervised visual features.

How Notebook 16 uses it:  
Notebook 16 includes DINOv2 summaries to complement CLIP and LPIPS.

#### Fontoura Júnior et al. (2023) — Cultural heritage inpainting evaluation

Relevant point:  
The paper supports multi-criteria assessment of inpainting in heritage-related contexts.

How Notebook 16 uses it:  
Notebook 16 frames the LaMa report as a diagnostic multi-metric artifact rather than a single-score model judgment.

### Project decision

The project creates a standalone LaMa report for the 200 non-zero damage cases.

Zero-control cases remain part of the validation pipeline but are excluded from the main report dataframe because they contain no damaged region.

The report emphasizes that LaMa is a learned pretrained inpainting baseline, not a painting-conservation-specific model.

### Notes for final thesis writing

This section should describe LaMa’s report as an intermediate model-level artifact.

Possible thesis wording:

> A standalone LaMa report was generated to consolidate its evaluation across classical, perceptual, feature-space, and visual diagnostic layers. The report supports model-level interpretation while preserving the distinction between numerical improvement, perceptual similarity, feature-space alignment, and restoration faithfulness.

### Potential improvements / supervisor feedback

- Ask whether standalone model reports should be included in the thesis appendix or only summarized in the final consolidated report.
- Consider generating an extended LaMa report after texture metrics are available.
- Avoid rewriting the stable old LaMa report unless necessary; use the extended final report for new texture/heatmap additions.
- Consider using LaMa report cases as examples where learned inpainting outperforms classical interpolation.

---

## 17. OpenCV Telea versus LaMa Comparison

### Decision supported

The OpenCV-versus-LaMa comparison notebook directly compares two restoration paradigms under identical controlled damage conditions.

The compared paradigms are:

- deterministic local interpolation: OpenCV Telea,
- pretrained learned inpainting: LaMa.

This notebook supports the broader thesis goal of evaluating restoration behavior through a framework rather than isolated model scores.

### References

#### Telea (2004) — Fast Marching Method inpainting

Relevant point:  
Telea provides the classical deterministic baseline.

How Notebook 17 uses it:  
Notebook 17 compares OpenCV Telea’s local interpolation behavior against LaMa’s learned inpainting behavior.

#### Suvorov et al. (2022) — LaMa

Relevant point:  
LaMa provides the learned inpainting baseline designed for larger and more complex masks.

How Notebook 17 uses it:  
Notebook 17 tests whether LaMa’s expected advantage over a local classical method appears under the controlled 50-painting synthetic damage setup.

#### Wang et al. (2004) — SSIM

Relevant point:  
SSIM provides structural similarity evaluation.

How Notebook 17 uses it:  
Notebook 17 includes structural similarity as one component of the local metric comparison, while respecting that SSIM requires an image-like region.

#### Zhang et al. (2018) — LPIPS

Relevant point:  
LPIPS provides perceptual-distance comparison in learned feature space.

How Notebook 17 uses it:  
Notebook 17 uses LPIPS as one metric family in the paired OpenCV-LaMa comparison.

#### Radford et al. (2021) — CLIP

Relevant point:  
CLIP provides image-text-supervised visual feature representations.

How Notebook 17 uses it:  
Notebook 17 uses CLIP similarity improvement as one diagnostic feature-space comparison between OpenCV and LaMa.

#### Oquab et al. (2023) — DINOv2

Relevant point:  
DINOv2 provides self-supervised visual feature representations.

How Notebook 17 uses it:  
Notebook 17 uses DINOv2 similarity improvement as a second diagnostic feature-space comparison.

#### Fontoura Júnior et al. (2023) — Cultural heritage inpainting evaluation

Relevant point:  
Cultural heritage inpainting assessment benefits from multi-metric comparison and careful interpretation.

How Notebook 17 uses it:  
Notebook 17 treats metric disagreement between OpenCV and LaMa as diagnostic evidence, not as noise to remove.

### Project decision

The project performs a paired case-level comparison between OpenCV Telea and LaMa.

Pairing is based on shared case identity:

- `case_id`,
- `painting_id`,
- `mask_type`.

The main local comparison uses:

- masked-region classical metrics,
- mask-bounding-box LPIPS,
- mask-bounding-box CLIP similarity,
- mask-bounding-box DINOv2 similarity.

For each metric, winner columns are computed. A compact overall metric vote is then derived from these metric winners.

The vote is interpreted as a diagnostic summary, not as final restoration truth.

### Notes for final thesis writing

This section should support the thesis argument that different model types fail differently.

Possible thesis wording:

> The OpenCV Telea versus LaMa comparison paired both models on identical paintings, masks, and damage cases. This enabled direct comparison between deterministic local interpolation and learned pretrained inpainting. Metric disagreement was retained as diagnostic evidence because one model may improve local pixel error while another performs better in perceptual or feature-space similarity.

### Potential improvements / supervisor feedback

- Ask whether the two-model comparison should remain as an intermediate result or be folded into the final three-/four-model comparison chapter.
- After Notebook 31, compare texture winners against the OpenCV-LaMa metric vote.
- Consider reporting model behavior by mask type, especially whether LaMa gains more over OpenCV for `loss_large` and `mixed_damage`.
- Keep the overall metric vote clearly labeled as a diagnostic summary, not a conservation-quality score.

## 18. Stable Diffusion Inpainting Restoration Generation

### Decision supported

The Stable Diffusion restoration notebook adds the first diffusion-based generative inpainting model to the controlled 50-painting framework.

This extends the evaluated model stack from:

- deterministic local interpolation: OpenCV Telea,
- pretrained learned inpainting: LaMa,

to:

- prompt-conditioned diffusion-based inpainting: Stable Diffusion Inpainting.

The notebook supports the decision to evaluate generative inpainting separately from classical and learned deterministic baselines because diffusion models can produce visually plausible but non-reference-faithful completions.

### References

#### Rombach et al. (2022) — High-Resolution Image Synthesis with Latent Diffusion Models

Relevant point:  
Latent Diffusion Models perform image generation in a compressed latent space, enabling high-resolution image synthesis and image editing tasks with lower computational cost than pixel-space diffusion.

How Notebook 18 uses it:  
Notebook 18 uses Stable Diffusion Inpainting as the diffusion-based restoration baseline. The notebook builds on the latent-diffusion model family by testing how a prompt-conditioned generative model behaves on controlled painting damage.

#### Hugging Face Diffusers Stable Diffusion Inpainting documentation

Relevant point:  
The Diffusers inpainting pipeline uses an input image, a binary mask, and a text prompt to guide inpainting. White mask pixels indicate the region to repaint and black pixels indicate the region to preserve.

How Notebook 18 uses it:  
Notebook 18 uses the project’s existing damaged images and binary masks with the Stable Diffusion inpainting pipeline. The notebook keeps the same mask convention used by OpenCV and LaMa, supporting fair paired evaluation.

#### RunwayML Stable Diffusion Inpainting model card

Relevant point:  
The `runwayml/stable-diffusion-inpainting` model is a Stable Diffusion model adapted for image inpainting.

How Notebook 18 uses it:  
Notebook 18 uses this model as the project’s Stable Diffusion baseline. The same model, prompt, negative prompt, inference steps, guidance scale, seed, and inference resolution are applied across all painting cases to reduce prompt-engineering bias.

#### Li et al. (2023) — Diffusion Models for Image Restoration and Enhancement: A Comprehensive Survey

Relevant point:  
The survey reviews diffusion models for restoration and enhancement tasks and highlights their ability to generate plausible image content while also requiring careful evaluation.

How Notebook 18 uses it:  
Notebook 18 treats Stable Diffusion as a generative restoration candidate rather than a restoration authority. The outputs are generated for later evaluation through reference metrics, visual diagnostics, and uncertainty analysis.

#### Fontoura Júnior et al. (2023) — Assessing the Effectiveness of Inpainting Techniques in Cultural Heritage

Relevant point:  
The paper supports careful evaluation of inpainting in cultural heritage contexts and warns against relying only on visual plausibility.

How Notebook 18 uses it:  
Notebook 18 applies Stable Diffusion to painting restoration under controlled synthetic damage but keeps interpretation cautious. The generated completions are evaluated as candidate outputs, not accepted as conservation-grade restoration.

### Project decision

The project uses:

`runwayml/stable-diffusion-inpainting`

The notebook uses a fixed prompt and fixed negative prompt for all paintings.

The fixed prompt asks the model to restore the damaged painting area while preserving style, color, brushwork, composition, and surrounding context.

The fixed negative prompt discourages:

- modern objects,
- text,
- watermarks,
- altered faces,
- extra objects,
- cartoon-like outputs,
- digital-art artifacts,
- unrealistic texture.

Inference settings:

- seed: `2026`,
- inference steps: `30`,
- guidance scale: `7.5`,
- inference size: `512 × 512`,
- output size: `768 × 768`.

Zero-control cases are copied directly instead of being passed through Stable Diffusion. This preserves their sanity-check role and avoids arbitrary generative changes where no damage exists.

### Notes for final thesis writing

This section should introduce Stable Diffusion as the first generative model in the model stack.

Possible thesis wording:

> Stable Diffusion Inpainting was included as a prompt-conditioned diffusion baseline. Unlike OpenCV Telea and LaMa, Stable Diffusion is generative and can produce multiple plausible completions for the same damaged region. A fixed prompt policy was used across all paintings to reduce prompt-engineering bias. The generated outputs were evaluated as candidate restorations rather than treated as historically or conservation-faithful reconstructions.

### Potential improvements / supervisor feedback

- Ask whether the fixed prompt policy is acceptable for the final thesis or whether category-specific prompts should be tested as an ablation.
- Consider documenting the exact prompt and negative prompt in the appendix.
- Consider whether inference size should be increased if stronger compute becomes available.
- For the final 300-painting experiment, confirm whether Stable Diffusion should be rerun with the same seed/settings or tuned after supervisor feedback.

---

## 19. Stable Diffusion Classical Metric Evaluation

### Decision supported

The Stable Diffusion classical metric notebook evaluates Stable Diffusion outputs using the same classical metric structure applied to OpenCV Telea and LaMa.

This supports model-agnostic comparison across:

- deterministic inpainting,
- learned pretrained inpainting,
- generative diffusion inpainting.

The notebook computes full-reference classical metrics between:

- clean reference and damaged input,
- clean reference and Stable Diffusion restored output.

### References

#### Wang et al. (2004) — SSIM

Relevant point:  
SSIM measures structural similarity using local spatial neighborhoods.

How Notebook 19 uses it:  
Notebook 19 includes SSIM as the structural component of the classical metric stack for Stable Diffusion. Because SSIM requires spatial structure, it is interpreted most meaningfully on image-like regions such as the mask-bounding-box crop.

#### Hore and Ziou (2010) — PSNR vs. SSIM

Relevant point:  
PSNR and SSIM capture different aspects of image quality, so both can be useful in full-reference image evaluation.

How Notebook 19 uses it:  
Notebook 19 computes both pixel-error-based metrics and structural metrics for Stable Diffusion outputs. This allows comparison with earlier OpenCV and LaMa metric branches.

#### Zhang et al. (2018) — LPIPS

Relevant point:  
LPIPS shows that traditional metrics such as PSNR and SSIM may not align with perceptual similarity.

How Notebook 19 uses it:  
Notebook 19 treats classical metrics as one diagnostic layer only. It prepares the Stable Diffusion branch for later LPIPS and feature-space evaluation.

#### Li et al. (2023) — Diffusion Models for Image Restoration and Enhancement: A Comprehensive Survey

Relevant point:  
Diffusion restoration outputs can be visually plausible but may not match a reference exactly, making careful metric interpretation necessary.

How Notebook 19 uses it:  
Notebook 19 interprets classical metrics cautiously for Stable Diffusion because generative outputs may alter texture, color, or local structure while still appearing plausible.

### Project decision

The project computes classical metrics for Stable Diffusion over:

- full image,
- content region,
- masked region,
- mask bounding-box crop.

The final metric table contains 900 rows:

- non-zero damage cases contribute four region rows,
- zero-control cases contribute full-image and content-region rows only.

Masked-region metrics are used for direct damaged-pixel evaluation. SSIM is later moved to the mask-bounding-box crop in the refined metric-region policy because sparse masked pixels do not provide an appropriate structural image neighborhood.

### Notes for final thesis writing

This section should explain that classical metrics remain useful for diffusion outputs but are not sufficient.

Possible thesis wording:

> Stable Diffusion outputs were evaluated using the same classical full-reference metrics as the earlier baselines. These metrics quantify numerical closeness to the known clean reference under synthetic damage. However, because Stable Diffusion is generative, classical metric interpretation requires caution: a visually coherent completion can still deviate from the original painting in color, texture, or structure.

### Potential improvements / supervisor feedback

- Ask whether Stable Diffusion classical metrics should be interpreted separately from deterministic model metrics because the model is stochastic.
- Consider adding a short discussion that pixel-level metrics may penalize plausible but non-reference-identical generations.
- Keep masked-region MSE and PSNR as direct restoration-target metrics.

---

## 20. Stable Diffusion Difference and Error-Map Diagnostics

### Decision supported

The Stable Diffusion difference-map notebook adds spatial diagnostics for Stable Diffusion outputs.

This supports interpretation beyond scalar metrics by showing where the generative restoration improved or worsened relative to the clean reference.

This diagnostic layer is especially important for generative inpainting because a completion may look coherent while changing valid painting structure, texture, or color.

### References

#### Wang et al. (2004) — SSIM and structural similarity

Relevant point:  
Scalar structural similarity metrics summarize image quality but do not localize where errors occur.

How Notebook 20 uses it:  
Notebook 20 complements structural and pixel metrics with visual error maps, allowing spatial inspection of Stable Diffusion’s restoration behavior.

#### Zhang et al. (2018) — LPIPS

Relevant point:  
Perceptual similarity can diverge from pixel-level error.

How Notebook 20 uses it:  
Notebook 20 uses spatial error maps as a bridge between classical metrics and later perceptual evaluation. It helps identify cases where Stable Diffusion may improve appearance but remain far from the reference.

#### Li et al. (2023) — Diffusion restoration survey

Relevant point:  
Diffusion models can generate visually plausible restorations, but generated outputs require careful evaluation because plausibility does not guarantee faithfulness.

How Notebook 20 uses it:  
Notebook 20 uses difference maps to expose local deviations that may be hidden by visual plausibility.

#### Fontoura Júnior et al. (2023) — Cultural heritage inpainting evaluation

Relevant point:  
Heritage inpainting evaluation should combine quantitative and qualitative evidence.

How Notebook 20 uses it:  
Notebook 20 creates standardized diagnostic visualizations for Stable Diffusion rather than relying on manually chosen attractive examples.

### Project decision

The project generates Stable Diffusion error-map diagnostics using the same structure as earlier model branches.

Each diagnostic figure contains:

- clean reference,
- binary mask,
- damaged input,
- restored output,
- damaged absolute error,
- restored absolute error,
- signed improvement,
- masked signed improvement.

Signed improvement is computed as:

`damaged_error - restored_error`

Positive values indicate that restoration reduced error relative to the damaged input. Negative values indicate that restoration increased error relative to the clean reference.

### Notes for final thesis writing

This section should support the argument that visual plausibility and reference fidelity can diverge.

Possible thesis wording:

> Spatial error-map diagnostics were generated for Stable Diffusion to localize where generative restoration reduced or increased error relative to the clean reference. This was important because diffusion outputs can appear visually coherent while still deviating from the original painting. Difference maps therefore helped separate visual plausibility from reference-based restoration fidelity.

### Potential improvements / supervisor feedback

- Ask whether Stable Diffusion error maps should be shown alongside uncertainty heatmaps after Notebook 32.
- Consider using error maps to select examples where Stable Diffusion appears plausible but performs poorly against the clean reference.
- Standardize visual scales across OpenCV, LaMa, and Stable Diffusion for final thesis figures.
- Consider adding per-case report pages that include both error maps and uncertainty heatmaps.

---

## 21. Stable Diffusion LPIPS Perceptual Evaluation

### Decision supported

The Stable Diffusion LPIPS notebook evaluates Stable Diffusion outputs using learned perceptual distance.

This supports the multi-metric framework by adding perceptual similarity to the Stable Diffusion branch, matching the evaluation structure already applied to OpenCV and LaMa.

The notebook computes LPIPS between:

- clean reference and damaged input,
- clean reference and Stable Diffusion restored output.

LPIPS improvement is computed as:

`damaged_lpips - restored_lpips`

Positive improvement means the restoration is perceptually closer to the clean reference.

### References

#### Zhang et al. (2018) — LPIPS

Relevant point:  
LPIPS compares images using deep feature distances and can align better with human perceptual judgments than traditional metrics such as PSNR and SSIM.

How Notebook 21 uses it:  
Notebook 21 computes LPIPS for Stable Diffusion outputs to evaluate whether generated restorations become perceptually closer to the clean reference.

#### Li et al. (2023) — Diffusion Models for Image Restoration and Enhancement: A Comprehensive Survey

Relevant point:  
Diffusion restoration outputs can be plausible and high quality, but they need evaluation beyond visual inspection.

How Notebook 21 uses it:  
Notebook 21 uses LPIPS as one perceptual diagnostic for Stable Diffusion, while acknowledging that perceptual similarity does not prove restoration faithfulness.

#### Fontoura Júnior et al. (2023) — Cultural heritage inpainting evaluation

Relevant point:  
Cultural heritage inpainting evaluation benefits from multiple complementary metrics.

How Notebook 21 uses it:  
Notebook 21 adds LPIPS to the Stable Diffusion evaluation branch as one metric family in the broader trustworthiness framework.

### Project decision

The project computes LPIPS for Stable Diffusion on image-like regions:

- full image,
- content region,
- mask bounding-box crop.

Sparse masked-region pixels are not used because LPIPS expects spatial image patches.

The final output contains 700 rows:

- 250 full-image rows,
- 250 content-region rows,
- 200 mask-bounding-box crop rows.

### Notes for final thesis writing

This section should explain why LPIPS is useful but limited for diffusion outputs.

Possible thesis wording:

> LPIPS was used as a learned perceptual-distance metric for Stable Diffusion Inpainting. Since LPIPS operates on spatial image patches, it was computed on full-image, content-region, and mask-bounding-box regions rather than sparse masked pixels. For diffusion outputs, LPIPS was interpreted cautiously because a perceptually plausible result may still hallucinate content or alter painting-specific details.

### Potential improvements / supervisor feedback

- After Notebook 31, compare LPIPS and texture distance disagreement cases.
- Consider using LPIPS to select perceptual-success but reference-failure examples for the thesis.
- Note clearly that LPIPS is not a conservation-specific metric.

---

## 22. Stable Diffusion CLIP and DINOv2 Feature-Similarity Evaluation

### Decision supported

The Stable Diffusion feature-similarity notebook evaluates Stable Diffusion outputs using CLIP and DINOv2 embeddings.

This supports semantic and visual feature-space diagnostics beyond classical and LPIPS metrics.

The notebook computes cosine similarity between:

- clean reference vs damaged input,
- clean reference vs Stable Diffusion restored output.

Feature-space improvement is computed as:

`restored_similarity - damaged_similarity`

Positive improvement means the restored output is closer to the clean reference in the selected feature space.

### References

#### Radford et al. (2021) — CLIP

Relevant point:  
CLIP learns transferable visual representations using image-text contrastive training.

How Notebook 22 uses it:  
Notebook 22 uses CLIP embeddings as a broad semantic/visual feature-space diagnostic for Stable Diffusion outputs. This is useful because diffusion outputs may look semantically plausible while still diverging from the clean reference.

#### Oquab et al. (2023) — DINOv2

Relevant point:  
DINOv2 provides robust self-supervised visual features and does not rely on image-text supervision.

How Notebook 22 uses it:  
Notebook 22 uses DINOv2 as a complementary visual representation to CLIP. This helps diagnose structural and visual feature-space similarity separately from language-supervised CLIP behavior.

#### Li et al. (2023) — Diffusion restoration survey

Relevant point:  
Diffusion restoration requires careful evaluation because generated outputs can be plausible without being reference-faithful.

How Notebook 22 uses it:  
Notebook 22 uses feature-space metrics to audit Stable Diffusion beyond pixel and perceptual scores.

#### Fontoura Júnior et al. (2023) — Cultural heritage inpainting evaluation

Relevant point:  
Heritage inpainting evaluation should use multiple forms of evidence rather than visual plausibility alone.

How Notebook 22 uses it:  
Notebook 22 adds CLIP and DINOv2 as additional diagnostic evidence for a painting-restoration-inspired benchmark.

### Project decision

The project computes CLIP and DINOv2 similarity for Stable Diffusion on:

- full image,
- content region,
- mask bounding-box crop.

Sparse masked pixels are not used because both models expect spatial image inputs.

The selected models are:

- CLIP: `openai/clip-vit-base-patch32`,
- DINOv2: project helper model `dinov2_vitb14`.

The feature-space metrics are interpreted as diagnostics, not as evidence of conservation correctness.

### Notes for final thesis writing

This section should emphasize that feature similarity is helpful for diffusion auditing but not definitive.

Possible thesis wording:

> CLIP and DINOv2 feature similarities were computed for Stable Diffusion outputs to complement classical and LPIPS metrics. These pretrained feature spaces helped diagnose whether restorations moved closer to the clean reference in broad visual representation space. Because Stable Diffusion is generative, feature-space improvement was interpreted as one diagnostic signal rather than proof of faithful restoration.

### Potential improvements / supervisor feedback

- Consider separating semantic consistency from feature similarity after supervisor feedback.
- Compare DINOv2 and texture metrics after Notebook 31, especially for high-texture brushwork.
- Use cases where CLIP improves but DINOv2 or texture metrics worsen as examples of metric disagreement.

---

## 23. Stable Diffusion Baseline Report

### Decision supported

The Stable Diffusion report notebook consolidates the full Stable Diffusion evaluation branch into a model-specific diagnostic report.

This supports model-level interpretation before the three-model comparison.

The report combines:

- restoration metadata,
- classical metric summaries,
- LPIPS summaries,
- CLIP and DINOv2 feature-similarity summaries,
- local metric outcome summaries,
- visual diagnostic examples,
- spatial error-map examples.

### References

#### Rombach et al. (2022) — Latent Diffusion Models

Relevant point:  
Latent Diffusion Models provide the foundation for Stable Diffusion-style generative image synthesis and editing.

How Notebook 23 uses it:  
Notebook 23 interprets Stable Diffusion as a generative inpainting model, meaning its outputs require different caution than deterministic interpolation methods.

#### Zhang et al. (2018) — LPIPS

Relevant point:  
LPIPS provides learned perceptual similarity.

How Notebook 23 uses it:  
Notebook 23 includes LPIPS summaries as part of the Stable Diffusion report’s perceptual evidence.

#### Radford et al. (2021) — CLIP

Relevant point:  
CLIP provides transferable image-text-supervised visual features.

How Notebook 23 uses it:  
Notebook 23 includes CLIP feature-similarity summaries as diagnostic evidence.

#### Oquab et al. (2023) — DINOv2

Relevant point:  
DINOv2 provides robust self-supervised visual features.

How Notebook 23 uses it:  
Notebook 23 includes DINOv2 summaries as a complementary visual feature-space signal.

#### Li et al. (2023) — Diffusion Models for Image Restoration and Enhancement

Relevant point:  
The survey motivates careful evaluation of diffusion restoration outputs because generated content can be visually plausible without being reference-faithful.

How Notebook 23 uses it:  
Notebook 23 explicitly separates visual plausibility from restoration faithfulness when interpreting Stable Diffusion results.

#### Fontoura Júnior et al. (2023) — Cultural heritage inpainting evaluation

Relevant point:  
Cultural heritage inpainting assessment requires careful, multi-criteria evaluation.

How Notebook 23 uses it:  
Notebook 23 frames the Stable Diffusion report as a diagnostic artifact rather than a model-quality verdict.

### Project decision

The project creates a standalone Stable Diffusion report after completing:

- restoration generation,
- classical metrics,
- difference/error maps,
- LPIPS,
- CLIP and DINOv2 feature similarity.

The report uses the local metric policy:

- classical metrics: masked region,
- LPIPS: mask bounding-box crop,
- CLIP/DINOv2: mask bounding-box crop.

Selected report cases are chosen using a fixed diagnostic policy:

- highest number of improved metrics,
- lowest number of improved metrics,
- mixed metric outcomes,
- category/mask representatives.

This reduces cherry-picking risk.

### Notes for final thesis writing

This section should introduce the Stable Diffusion report as a model-level diagnostic summary.

Possible thesis wording:

> A standalone Stable Diffusion report was generated to consolidate quantitative and visual diagnostics for the generative inpainting baseline. Because Stable Diffusion can produce visually persuasive but non-reference-faithful completions, the report separated visual plausibility from measured similarity and later motivated multi-seed uncertainty analysis.

### Potential improvements / supervisor feedback

- Ask whether the old Stable Diffusion report should remain as a model-specific appendix artifact.
- Add texture metric summaries only in the extended final report rather than rewriting this old report.
- Add uncertainty heatmap links after Notebook 32 in the new uncertainty heatmap report.
- Use selected Stable Diffusion cases to demonstrate the thesis claim that visual plausibility is not restoration trustworthiness.

---

## 24. Three-Model Comparison: OpenCV Telea, LaMa, and Stable Diffusion

### Decision supported

The three-model comparison notebook compares the first completed model stack:

- OpenCV Telea,
- LaMa,
- Stable Diffusion Inpainting.

This notebook supports the central thesis direction: building a trustworthy evaluation framework for AI-assisted painting restoration rather than only reporting isolated model scores.

The comparison evaluates deterministic, learned, and generative inpainting models under identical controlled damage conditions.

### References

#### Telea (2004) — Fast Marching Method inpainting

Relevant point:  
Telea provides the deterministic classical baseline.

How Notebook 24 uses it:  
Notebook 24 includes OpenCV Telea as the local interpolation baseline in the three-model comparison.

#### Suvorov et al. (2022) — LaMa

Relevant point:  
LaMa provides the learned pretrained inpainting baseline designed for larger missing regions.

How Notebook 24 uses it:  
Notebook 24 includes LaMa as the learned inpainting baseline and compares whether it outperforms OpenCV and Stable Diffusion under the controlled benchmark.

#### Rombach et al. (2022) — Latent Diffusion Models

Relevant point:  
Latent diffusion provides the generative model foundation for Stable Diffusion.

How Notebook 24 uses it:  
Notebook 24 includes Stable Diffusion as the prompt-conditioned generative inpainting baseline.

#### Wang et al. (2004) — SSIM

Relevant point:  
SSIM provides structural similarity but requires spatial image neighborhoods.

How Notebook 24 uses it:  
Notebook 24 initially includes SSIM in the local metric comparison. The later Notebook 26 refinement corrects the region policy by moving SSIM to the mask-bounding-box crop.

#### Zhang et al. (2018) — LPIPS

Relevant point:  
LPIPS provides learned perceptual-distance comparison.

How Notebook 24 uses it:  
Notebook 24 uses LPIPS as a perceptual metric family in the three-model local comparison.

#### Radford et al. (2021) — CLIP

Relevant point:  
CLIP provides image-text-supervised visual feature representations.

How Notebook 24 uses it:  
Notebook 24 uses CLIP similarity improvement as one feature-space metric in the three-model comparison.

#### Oquab et al. (2023) — DINOv2

Relevant point:  
DINOv2 provides self-supervised visual feature representations.

How Notebook 24 uses it:  
Notebook 24 uses DINOv2 similarity improvement as another feature-space metric in the three-model comparison.

#### Li et al. (2023) — Diffusion restoration survey

Relevant point:  
Diffusion restoration models require careful evaluation because generative plausibility and reference fidelity can diverge.

How Notebook 24 uses it:  
Notebook 24 interprets Stable Diffusion results cautiously and treats metric disagreement as meaningful evidence.

#### Fontoura Júnior et al. (2023) — Cultural heritage inpainting evaluation

Relevant point:  
Cultural heritage inpainting should be evaluated with multiple complementary criteria.

How Notebook 24 uses it:  
Notebook 24 compares multiple metric families and explicitly records disagreement cases.

### Project decision

The project performs a paired three-model comparison over the 200 non-zero damage cases.

Pairing is based on:

- `case_id`,
- `painting_id`,
- `mask_type`.

The initial local comparison policy uses:

- classical metrics: masked region,
- LPIPS: mask bounding-box crop,
- CLIP/DINOv2: mask bounding-box crop.

Metric winners are computed for:

- MSE improvement,
- PSNR improvement,
- SSIM improvement,
- LPIPS improvement,
- CLIP similarity improvement,
- DINOv2 similarity improvement.

A compact majority vote is computed across metric winners.

Metric disagreement cases are exported separately because disagreement between pixel, structural, perceptual, and feature-space metrics is central to the thesis argument.

### Notes for final thesis writing

This section should explain the first full model comparison and prepare the reader for Notebook 26’s refined metric-region policy.

Possible thesis wording:

> The three-model comparison evaluated OpenCV Telea, LaMa, and Stable Diffusion Inpainting on identical non-zero damage cases. Each model was compared across classical, perceptual, and feature-space metrics. Metric winners and majority votes were used as diagnostic summaries, not as conservation-quality labels. Cases of metric disagreement were retained because they reveal that restoration quality cannot be reliably captured by a single metric family.

### Potential improvements / supervisor feedback

- Keep Notebook 24 as an initial comparison checkpoint, not the final comparison, because Notebook 26 refines the metric-region policy.
- Ask whether the majority-vote approach is acceptable as a compact diagnostic summary.
- Consider adding texture metrics from Notebook 31 to an extended comparison report.
- Consider adding SDXL later if stronger compute is available.
- Consider reporting disagreement cases prominently because they are more thesis-interesting than yet another leaderboard pretending to be wisdom.

## 25. SDXL Feasibility Audit

### Decision supported

The SDXL feasibility notebook evaluates whether SDXL Inpainting can be included as a fourth full restoration baseline in the local controlled experiment.

The decision supported by this notebook is to exclude SDXL from the full local 50-painting evaluation because the available hardware does not support a practical balance between runtime, memory use, and restoration quality.

This is recorded as a feasibility limitation, not as a model-quality conclusion.

### References

#### Podell et al. (2023) — SDXL: Improving Latent Diffusion Models for High-Resolution Image Synthesis

Relevant point:  
SDXL improves latent diffusion image generation using a larger architecture and refined conditioning design. It is a stronger and more recent diffusion model family than the earlier Stable Diffusion baseline.

How Notebook 25 uses it:  
Notebook 25 treats SDXL Inpainting as a reasonable candidate fourth model because it represents a stronger diffusion-based inpainting family. The notebook does not fully evaluate SDXL quality; it tests whether the model is feasible on the local machine.

#### Hugging Face Diffusers SDXL Inpainting documentation and model card

Relevant point:  
The SDXL Inpainting pipeline is significantly more memory-intensive than earlier Stable Diffusion inpainting pipelines and often requires memory-saving techniques such as CPU offload, reduced precision, reduced inference size, or other optimizations.

How Notebook 25 uses it:  
Notebook 25 uses Diffusers SDXL Inpainting with memory-saving settings to test whether local execution is possible on the available 6 GB RTX 3060 Laptop GPU.

#### Li et al. (2023) — Diffusion Models for Image Restoration and Enhancement: A Comprehensive Survey

Relevant point:  
The survey positions diffusion models as powerful restoration candidates, but also highlights the need for practical evaluation and careful interpretation.

How Notebook 25 uses it:  
Notebook 25 uses this context to justify trying SDXL as a diffusion restoration candidate, while treating local feasibility as a necessary condition before adding it to the full model comparison.

#### Rombach et al. (2022) — High-Resolution Image Synthesis with Latent Diffusion Models

Relevant point:  
Latent diffusion models make high-resolution generation more tractable than pixel-space diffusion, but still require substantial compute for larger or more advanced models.

How Notebook 25 uses it:  
Notebook 25 frames SDXL as part of the latent-diffusion model family and tests whether the local hardware can support it under the thesis experiment constraints.

### Project decision

The project tested:

`diffusers/stable-diffusion-xl-1.0-inpainting-0.1`

Local hardware:

- NVIDIA GeForce RTX 3060 Laptop GPU,
- 6 GB VRAM.

Findings:

- SDXL pipeline import and loading were possible.
- Running without CPU offload caused CUDA out-of-memory errors.
- CPU offload made execution possible but too slow for full controlled evaluation.
- A 6-step 512 × 512 smoke test completed but did not produce meaningful restoration.
- A 12-step stronger smoke test completed but required roughly 10 minutes for one case and showed overgeneration/global alteration.

The project therefore excludes SDXL from the full local controlled evaluation.

This exclusion is recorded as:

- a hardware/runtime feasibility limitation,
- not a conclusion that SDXL is worse than the other models.

### Notes for final thesis writing

This section should be used to explain why SDXL is not part of the final fully evaluated local model stack.

Possible thesis wording:

> SDXL Inpainting was considered as a fourth restoration baseline, but local feasibility testing showed that the available 6 GB GPU environment could not support a practical full evaluation. Low-step settings were technically executable but did not produce meaningful restoration, while stronger settings caused excessive runtime and visible overgeneration. SDXL was therefore excluded from the full local controlled evaluation and retained as future work for a stronger compute environment.

### Potential improvements / supervisor feedback

- Ask whether SDXL must be included in the final thesis if university GPU resources become available.
- If SDXL is required, request access to at least 12 GB VRAM, preferably 16 GB or more.
- If remote compute becomes available, rerun SDXL as a fourth full model using the same controlled masks and metric framework.
- Keep the current SDXL result framed as a feasibility audit, not as model comparison evidence.

---

## 26. Refined Metric-Region Policy

### Decision supported

The refined metric-region notebook corrects the local comparison policy after the initial three-model comparison revealed that sparse masked-region SSIM was invalid or not meaningful.

The decision supported by this notebook is to keep SSIM in the framework, but evaluate it on the mask-bounding-box crop instead of sparse masked pixels.

This notebook is important because it shows the framework is not blindly collecting metrics. It audits whether each metric is being applied to a region type that matches the metric’s assumptions. Miraculous, really: metrics being used where they make sense.

### References

#### Wang et al. (2004) — Image Quality Assessment: From Error Visibility to Structural Similarity

Relevant point:  
SSIM is based on local luminance, contrast, and structural comparisons. It assumes spatial neighborhoods and image-like regions.

How Notebook 26 uses it:  
Notebook 26 uses this assumption to justify moving SSIM from sparse masked pixels to the mask-bounding-box crop. Sparse masked pixels do not preserve the local spatial neighborhood required for meaningful structural similarity.

#### Hore and Ziou (2010) — Image Quality Metrics: PSNR vs. SSIM

Relevant point:  
PSNR and SSIM measure different forms of image quality. PSNR is based on pixel-error magnitude, while SSIM compares structural properties.

How Notebook 26 uses it:  
Notebook 26 separates the region policy for pixel-error metrics and structural metrics. MSE and PSNR remain on the sparse masked region, while SSIM is moved to the mask-bounding-box crop.

#### Zhang et al. (2018) — LPIPS

Relevant point:  
LPIPS depends on spatial feature activations from image patches.

How Notebook 26 uses it:  
Notebook 26 aligns SSIM with the same local image-like region already used for LPIPS: the mask-bounding-box crop. This supports a coherent local region policy for spatial/feature-based metrics.

#### Radford et al. (2021) — CLIP

Relevant point:  
CLIP image embeddings are computed from spatial image inputs, not sparse unordered pixel sets.

How Notebook 26 uses it:  
Notebook 26 keeps CLIP local comparison on the mask-bounding-box crop, consistent with the metric’s image-input assumptions.

#### Oquab et al. (2023) — DINOv2

Relevant point:  
DINOv2 also operates on spatial image inputs and produces visual representations from image patches.

How Notebook 26 uses it:  
Notebook 26 keeps DINOv2 local comparison on the mask-bounding-box crop, matching the policy used for CLIP and LPIPS.

#### Fontoura Júnior et al. (2023) — Cultural heritage inpainting evaluation

Relevant point:  
Cultural heritage inpainting evaluation requires careful metric interpretation and should avoid overclaiming from inappropriate metrics.

How Notebook 26 uses it:  
Notebook 26 implements this principle by auditing the metric-region policy and correcting SSIM usage instead of keeping invalid sparse-region SSIM values.

### Project decision

The final refined local metric-region policy is:

- MSE improvement: `masked_region`,
- PSNR improvement: `masked_region`,
- SSIM improvement: `mask_bbox_crop`,
- LPIPS improvement: `mask_bbox_crop`,
- CLIP similarity improvement: `mask_bbox_crop`,
- DINOv2 similarity improvement: `mask_bbox_crop`.

Rationale:

- MSE and PSNR can be computed directly over sparse damaged pixels.
- SSIM requires local spatial structure, so it is computed on the mask-bounding-box crop.
- LPIPS, CLIP, and DINOv2 require image-like spatial inputs, so they remain on the mask-bounding-box crop.

The refined comparison is saved separately rather than overwriting the earlier three-model comparison. This preserves an audit trail from the initial comparison to the corrected final policy.

### Notes for final thesis writing

This section should be one of the strongest methodology sections because it shows region-aware metric design.

Possible thesis wording:

> After the initial three-model comparison, the local metric-region policy was refined because sparse masked-region SSIM did not provide meaningful comparison values. SSIM was retained, but moved to the mask-bounding-box crop where local spatial context is preserved. MSE and PSNR remained on the masked region because they directly measure pixel-level error over the restoration target. LPIPS, CLIP, and DINOv2 were also evaluated on the mask-bounding-box crop because they require image-like spatial inputs. This refinement demonstrates that metric selection and metric-region selection are both part of trustworthy restoration evaluation.

### Potential improvements / supervisor feedback

- Ask whether the final thesis should include a formal metric-region policy table.
- Ask whether the refined policy should be treated as the only final ranking policy, with the initial comparison retained only as an audit trail.
- Consider adding metric-policy ablation after supervisor feedback.
- Consider testing bbox margin sensitivity, for example 16, 32, and 64 pixels.
- After Notebook 31, add GLCM and Gabor texture metrics to the same region-policy table.

---

## 27. Diffusion Uncertainty Analysis

### Decision supported

The diffusion uncertainty notebook adds multi-seed uncertainty analysis for Stable Diffusion Inpainting.

The decision supported by this notebook is that a single Stable Diffusion output is not enough to characterize model behavior because diffusion inpainting is stochastic.

Repeated generation with different seeds can reveal whether the model produces stable restorations or multiple inconsistent plausible completions for the same damaged input.

### References

#### Rombach et al. (2022) — High-Resolution Image Synthesis with Latent Diffusion Models

Relevant point:  
Latent diffusion models generate images through stochastic sampling in latent space. This makes output variability an inherent part of diffusion-based generation.

How Notebook 27 uses it:  
Notebook 27 evaluates Stable Diffusion with multiple seeds for the same painting and mask to measure output variability instead of relying on one generated sample.

#### Li et al. (2023) — Diffusion Models for Image Restoration and Enhancement: A Comprehensive Survey

Relevant point:  
Diffusion restoration models can generate high-quality outputs but require careful evaluation because generated results may vary and visual plausibility does not guarantee reference fidelity.

How Notebook 27 uses it:  
Notebook 27 treats uncertainty as a trustworthiness issue. If multiple seeds produce inconsistent restorations, this becomes diagnostic evidence even if one output looks plausible.

#### Zhang et al. (2018) — LPIPS

Relevant point:  
LPIPS provides perceptual distance between image patches using learned feature activations.

How Notebook 27 uses it:  
Notebook 27 computes pairwise LPIPS distances between multiple seed outputs. Higher pairwise LPIPS indicates greater perceptual variability across generated restorations.

#### Radford et al. (2021) — CLIP

Relevant point:  
CLIP provides a pretrained image representation space.

How Notebook 27 uses it:  
Notebook 27 computes pairwise CLIP similarity between seed outputs to measure feature-space stability across generations.

#### Oquab et al. (2023) — DINOv2

Relevant point:  
DINOv2 provides robust self-supervised visual features.

How Notebook 27 uses it:  
Notebook 27 computes pairwise DINOv2 similarity between seed outputs as a complementary feature-space uncertainty signal.

#### Recent inpainting self-consistency work

Relevant point:  
Recent inpainting-evaluation work has proposed consistency-based evaluation ideas, where repeated or re-inpainted outputs can be assessed for stability rather than relying only on one output.

How Notebook 27 uses it:  
Notebook 27 applies a related idea in a simpler form: repeated Stable Diffusion outputs for the same damaged input are compared to quantify seed-based variability.

### Project decision

The project runs Stable Diffusion uncertainty analysis on a balanced diagnostic subset:

- 5 painting categories,
- 2 paintings per category,
- 4 non-zero mask types,
- 40 total cases.

Each case is generated with four seeds:

- `2026`,
- `2027`,
- `2028`,
- `2029`.

This produces 160 uncertainty-generation outputs.

The notebook computes:

Image-space indicators:

- pixel-wise standard deviation across seeds,
- masked-region standard deviation,
- mask-bounding-box standard deviation,
- mean absolute deviation from the seed-mean output.

Perceptual indicators:

- pairwise LPIPS distance between seed outputs.

Feature-space indicators:

- pairwise CLIP similarity,
- pairwise DINOv2 similarity,
- CLIP uncertainty distance,
- DINOv2 uncertainty distance.

A combined uncertainty index is created by min-max normalizing selected uncertainty indicators and averaging them.

The uncertainty results are linked back to the refined reference-based model comparison.

### Notes for final thesis writing

This section should support RQ3 and the trustworthiness argument.

Possible thesis wording:

> Since diffusion-based inpainting is stochastic, a single generated restoration cannot fully characterize model behavior. Multi-seed uncertainty analysis was therefore used to measure whether Stable Diffusion produced stable or variable restorations for identical damaged inputs. High seed variability was interpreted as a trustworthiness warning, particularly when paired with weak reference-based performance.

Another possible thesis wording:

> The uncertainty analysis shows that visual plausibility and output stability are separate evaluation dimensions. A generated restoration may appear coherent while still being one of several inconsistent completions sampled by the same model for the same damaged region.

### Potential improvements / supervisor feedback

- Ask whether the 40-case uncertainty subset is sufficient for the thesis or whether the full 200 non-zero cases should be run. (Most likely, full can be run.)
- Add uncertainty heatmaps in Notebook 32 to show where seed variability occurs spatially.
- If SDXL is later evaluated, repeat uncertainty analysis for SDXL.
- Consider testing whether four seeds are enough or whether six/eight seeds are needed for final reporting.
- Treat uncertainty as diagnostic, not as a complete probabilistic confidence estimate.

---

## 28. Final Controlled Evaluation Report

### Decision supported

The final controlled report notebook consolidates the completed 50-painting pilot framework into one thesis-ready artifact.

The decision supported by this notebook is to synthesize the model stack, metric framework, refined region policy, SDXL feasibility audit, Stable Diffusion uncertainty, and final interpretation into a single report.

This report is the main supervisor-facing summary before later extensions.

### References

#### Telea (2004) — Fast Marching Method inpainting

Relevant point:  
Telea provides the deterministic classical baseline.

How Notebook 28 uses it:  
Notebook 28 includes OpenCV Telea as the classical baseline in the final controlled evaluation summary.

#### Suvorov et al. (2022) — LaMa

Relevant point:  
LaMa provides the learned pretrained inpainting baseline.

How Notebook 28 uses it:  
Notebook 28 summarizes LaMa as the strongest model under the refined reference-based comparison in the 50-painting benchmark.

#### Rombach et al. (2022) — Latent Diffusion Models

Relevant point:  
Latent diffusion provides the generative foundation for Stable Diffusion-style inpainting.

How Notebook 28 uses it:  
Notebook 28 interprets Stable Diffusion as a generative restoration candidate that requires caution and uncertainty analysis.

#### Podell et al. (2023) — SDXL

Relevant point:  
SDXL represents a stronger and more recent diffusion model family.

How Notebook 28 uses it:  
Notebook 28 records SDXL as feasibility-audited but excluded from full local evaluation due compute limitations.

#### Wang et al. (2004) — SSIM

Relevant point:  
SSIM requires spatial image neighborhoods.

How Notebook 28 uses it:  
Notebook 28 reports the refined metric-region policy where SSIM is evaluated on the mask-bounding-box crop.

#### Zhang et al. (2018) — LPIPS

Relevant point:  
LPIPS provides learned perceptual-distance evaluation.

How Notebook 28 uses it:  
Notebook 28 includes LPIPS as one of the local metric families used in the refined model comparison.

#### Radford et al. (2021) — CLIP

Relevant point:  
CLIP provides image-text-supervised feature-space diagnostics.

How Notebook 28 uses it:  
Notebook 28 includes CLIP similarity as a feature-space metric in the final controlled evaluation.

#### Oquab et al. (2023) — DINOv2

Relevant point:  
DINOv2 provides self-supervised feature-space diagnostics.

How Notebook 28 uses it:  
Notebook 28 includes DINOv2 similarity as a second feature-space metric in the final controlled evaluation.

#### Li et al. (2023) — Diffusion restoration survey

Relevant point:  
Diffusion restoration outputs require careful evaluation because visual plausibility, stability, and reference fidelity can diverge.

How Notebook 28 uses it:  
Notebook 28 uses this framing to interpret Stable Diffusion’s low reference-based win rate together with multi-seed uncertainty results.

#### Fontoura Júnior et al. (2023) — Cultural heritage inpainting evaluation

Relevant point:  
Cultural heritage inpainting requires multi-criteria evaluation and cautious interpretation.

How Notebook 28 uses it:  
Notebook 28 frames the entire 50-painting experiment as a trustworthiness evaluation framework rather than a restoration-quality leaderboard.

#### Van Vijle et al. (2025) — Machine Learning for Painting Conservation: A State-of-the-Art Review

Relevant point:  
The review identifies virtual restoration as an important machine-learning application in painting conservation and emphasizes reliability and data limitations.

How Notebook 28 uses it:  
Notebook 28 uses this painting-conservation context to support the project’s cautious claim: the framework evaluates restoration trustworthiness, not conservation truth.

### Project decision

The final controlled report synthesizes:

- 50 paintings,
- 5 painting categories,
- 5 mask types,
- 250 total cases,
- 200 non-zero damage cases,
- OpenCV Telea,
- LaMa,
- Stable Diffusion Inpainting,
- SDXL feasibility audit,
- refined metric-region policy,
- three-model comparison,
- Stable Diffusion uncertainty analysis,
- uncertainty-performance linkage,
- visual examples,
- final interpretation.

The final report emphasizes:

> Visual plausibility is not the same as restoration trustworthiness.

The report does not claim that any model performs historically correct painting restoration. It shows how a framework can reveal differences between pixel fidelity, structural similarity, perceptual similarity, feature similarity, model feasibility, and generative uncertainty.

### Notes for final thesis writing

This section should become the backbone of the final experimental-results chapter.

Possible thesis wording:

> The controlled 50-painting evaluation demonstrates that AI-assisted painting restoration should be evaluated through multiple complementary lenses. Reference-based similarity remains important, but it does not capture all relevant trustworthiness concerns. Generative models require additional uncertainty analysis because different seeds may produce different plausible completions for the same damaged region. The experiment therefore supports the thesis claim that visual plausibility is not equivalent to restoration trustworthiness.

Another possible thesis wording:

> LaMa achieved the strongest reference-based performance in the controlled benchmark, while Stable Diffusion highlighted the distinction between visual plausibility and restoration trustworthiness. Its outputs can appear coherent, but multi-seed analysis shows that diffusion-based restoration may be unstable across repeated generations.

### Potential improvements / supervisor feedback

- Ask whether SDXL must be included if stronger compute is available.
- Ask whether the uncertainty subset should be expanded from 40 cases to all 200 non-zero cases.
- Add Notebook 31 texture metrics to the extended final report.
- Add Notebook 32 uncertainty heatmaps to make spatial uncertainty visible.
- Add Notebook 33 per-case/per-painting report templates to strengthen the framework artifact.
- After feedback, consider semantic consistency, metadata analysis, and metric-policy ablation.

## 29. Streamlit Dashboard Asset Preparation

### Decision supported

The dashboard asset-preparation notebook converts the completed 50-painting evaluation outputs into lightweight dashboard-ready files.

The decision supported by this notebook is to treat the Streamlit dashboard as a structured inspection interface for the evaluation framework, not as a separate experiment.

The notebook prepares dashboard assets from:

- final controlled dataset summaries,
- refined three-model comparison outputs,
- Stable Diffusion uncertainty outputs,
- selected visual case metadata,
- key findings,
- report manifests.

This supports reproducible exploration of the controlled experiment without forcing the dashboard to directly load every raw metric file and intermediate artifact.

### References

#### Heer and Shneiderman (2012) — Interactive Dynamics for Visual Analysis

Relevant point:  
The paper describes principles for interactive visual analysis, including filtering, selection, coordination, and exploration across views.

How Notebook 29 uses it:  
Notebook 29 prepares dashboard tables and manifest files so that the Streamlit interface can support interactive inspection of models, mask types, categories, uncertainty cases, visual examples, and report outputs.

#### Munzner (2014) — Visualization Analysis and Design

Relevant point:  
Munzner emphasizes designing visualization systems around tasks, data types, and intended analytical use rather than simply plotting available data.

How Notebook 29 uses it:  
Notebook 29 organizes the dashboard around thesis-relevant inspection tasks: understanding dataset design, comparing models, reviewing metric-region policy, inspecting uncertainty, exploring visual cases, and accessing reports.

#### Fontoura Júnior et al. (2023) — Assessing the Effectiveness of Inpainting Techniques in Cultural Heritage

Relevant point:  
Cultural heritage inpainting evaluation benefits from careful multi-criteria assessment and visual inspection.

How Notebook 29 uses it:  
Notebook 29 prepares dashboard assets that expose multiple evaluation layers rather than a single ranking. This supports the cultural-heritage evaluation principle that inpainting results should be inspected through several complementary forms of evidence.

#### Van Vijle et al. (2025) — Machine Learning for Painting Conservation: A State-of-the-Art Review

Relevant point:  
The review emphasizes reliability and careful interpretation in machine-learning applications for painting conservation.

How Notebook 29 uses it:  
Notebook 29 supports reliability-aware inspection by making metric results, uncertainty outputs, and visual examples accessible in one dashboard structure.

### Project decision

The project creates a dashboard-ready asset layer under:

`outputs/dashboard/`

The notebook produces:

- dashboard overview summary,
- dashboard asset manifest,
- key findings JSON,
- report manifest JSON,
- model comparison dashboard CSV,
- uncertainty cases dashboard CSV,
- visual case dashboard CSV.

The dashboard is designed around sections for:

- overview,
- dataset and damage design,
- model stack,
- metric-region policy,
- final model comparison,
- Stable Diffusion uncertainty,
- visual case explorer,
- key findings,
- reports and reproducibility.

### Notes for final thesis writing

This section should describe the dashboard as a framework artifact.

Possible thesis wording:

> A Streamlit dashboard was prepared as an interactive inspection layer for the evaluation framework. Dashboard-ready CSV and JSON assets were generated from the completed metric, uncertainty, and report outputs. The dashboard was designed to support structured exploration of dataset design, model comparison, metric-region policy, uncertainty behavior, visual examples, and final reports. It is not treated as an additional experiment, but as a reproducibility and interpretation interface for the controlled evaluation.

### Potential improvements / supervisor feedback

- Ask whether the dashboard should be included as a formal thesis artifact.
- Add texture metrics to the dashboard after Notebook 31.
- Add uncertainty heatmaps to the dashboard after Notebook 32.
- Add per-case and per-painting report links after Notebook 33.
- After supervisor feedback, add semantic consistency, metadata analysis, and ablation-study pages if those extensions are approved.

---

## 30. Supervisor Package and Proposal Alignment

### Decision supported

The supervisor-package notebook creates a compact review package that connects the completed controlled experiment back to the thesis proposal.

The decision supported by this notebook is to make the current framework reviewable before scaling or adding scope-heavy extensions.

The package emphasizes that the thesis contribution is an evaluation framework, not a new restoration model.

### References

#### Van Vijle et al. (2025) — Machine Learning for Painting Conservation: A State-of-the-Art Review

Relevant point:  
The review identifies virtual restoration as an important machine-learning application in painting conservation and emphasizes reliability, data limitations, and careful validation.

How Notebook 30 uses it:  
Notebook 30 frames the supervisor package around trustworthy evaluation rather than restoration claims. It supports the project’s cautious position that the framework evaluates model behavior under controlled synthetic damage, not conservation truth.

#### Fontoura Júnior et al. (2023) — Assessing the Effectiveness of Inpainting Techniques in Cultural Heritage

Relevant point:  
The paper supports multi-criteria evaluation of inpainting methods in cultural heritage contexts.

How Notebook 30 uses it:  
Notebook 30 organizes the package around the multi-layer evaluation framework: dataset, damage design, model stack, metric policy, model comparison, uncertainty, limitations, and supervisor questions.

#### Li et al. (2023) — Diffusion Models for Image Restoration and Enhancement: A Comprehensive Survey

Relevant point:  
The survey motivates careful evaluation of diffusion restoration outputs and highlights the need to interpret generative restoration cautiously.

How Notebook 30 uses it:  
Notebook 30 uses this framing when explaining Stable Diffusion uncertainty and SDXL feasibility to the supervisor.

#### Suvorov et al. (2022) — LaMa

Relevant point:  
LaMa provides the learned inpainting baseline in the evaluated model stack.

How Notebook 30 uses it:  
Notebook 30 summarizes LaMa as part of the fully evaluated model stack and links it to the proposal’s pretrained-model comparison direction.

#### Rombach et al. (2022) — Latent Diffusion Models

Relevant point:  
Latent diffusion provides the generative basis for Stable Diffusion.

How Notebook 30 uses it:  
Notebook 30 explains why diffusion outputs require uncertainty analysis and careful interpretation.

#### Podell et al. (2023) — SDXL

Relevant point:  
SDXL represents a stronger diffusion-model family that was considered for full evaluation.

How Notebook 30 uses it:  
Notebook 30 records SDXL as feasibility-audited but not fully evaluated due to local hardware constraints.

### Project decision

The project creates a supervisor review package under:

`outputs/supervisor_package/`

The package includes:

- `README_supervisor.md`,
- `proposal_alignment.md`,
- `methodology_summary.md`,
- `results_summary.md`,
- `limitations_and_deviations.md`,
- `supervisor_questions.md`,
- `next_steps.md`,
- `package_manifest.json`,
- compact data summaries,
- selected figures,
- copied methodology and model-audit notes.

The package maps the current work to three thesis research directions:

1. multi-metric restoration trustworthiness,
2. pretrained model comparison across painting and damage conditions,
3. diffusion uncertainty from multiple restoration candidates.

The package identifies the main supervisor decisions still needed:

- final dataset scale,
- whether SDXL is required,
- whether uncertainty should be expanded,
- whether the dashboard should become a formal artifact,
- which extensions should be included before final thesis execution.

### Notes for final thesis writing

This section should support the transition from pilot experiment to final thesis planning.

Possible thesis wording:

> A supervisor review package was prepared after the controlled 50-painting experiment. The package linked the completed implementation back to the proposal’s research questions and summarized methodology, results, limitations, deviations, and next-step decisions. This review package was used to clarify final scope before scaling the experiment or adding further extensions.

### Potential improvements / supervisor feedback

- Ask whether the current 50-painting framework is sufficient as a validated pilot or whether the final thesis must scale to 300 paintings. (Scaling up needed most probably)
- Ask whether SDXL must be evaluated on stronger hardware.
- Ask whether the Stable Diffusion uncertainty subset is sufficient or should be expanded.
- Ask whether semantic consistency, metadata analysis, and metric-policy ablation should be included after feedback.
- Consider creating `outputs/supervisor_package_extended/` after Notebooks 31–35 instead of overwriting the current stable package.

---

## 31. Texture Metrics

### Decision supported

The texture-metrics notebook adds a dedicated texture-aware evaluation layer to the controlled 50-painting framework.

The decision supported by this notebook is to evaluate whether restored local regions preserve texture structure relative to the clean reference.

This extends the existing metric stack beyond:

- pixel fidelity,
- structural similarity,
- perceptual similarity,
- CLIP feature similarity,
- DINOv2 feature similarity,

by adding local texture-continuity diagnostics.

The notebook computes texture and brushstroke-proxy metrics on the `mask_bbox_crop` region because these descriptors require spatial image structure.

The brushstroke-proxy metrics do not perform semantic brushstroke recognition. They measure directional local texture structure using gradient magnitude, edge/detail density, orientation coherence, and orientation histogram similarity.

### References

#### Jain et al. (2023) — Keys To Better Image Inpainting: Structure and Texture Go Hand in Hand

Relevant point:  
The paper argues that image inpainting quality depends on both structure generation and texture synthesis.

How Notebook 31 uses it:  
Notebook 31 operationalizes this structure-texture motivation by adding texture and brushstroke-proxy metrics to the restoration evaluation framework. The notebook does not implement Jain et al.’s model and does not claim semantic brushstroke recognition. Instead, it uses the paper’s structure-texture argument to justify measuring local texture preservation and directional brushstroke-like continuity as separate diagnostic layers beyond PSNR, SSIM, LPIPS, CLIP, and DINOv2.

#### Sun et al. (2024) — Ancient Paintings Inpainting Based on Dual Encoders and Multi-Scale Feature Fusion

Relevant point:  
The paper treats texture and detail extraction as important for ancient painting inpainting.

How Notebook 31 uses it:  
Notebook 31 uses this as painting-specific support for evaluating local texture preservation. This is especially relevant for high-texture brushwork, large losses, and mixed damage cases.

#### Liu et al. (2024) — Ancient Painting Inpainting Based on Multi-Layer Feature Fusion

Relevant point:  
The paper discusses detail preservation and frequency-domain or multi-layer feature enhancement for ancient painting inpainting.

How Notebook 31 uses it:  
Notebook 31 uses this as support for including frequency- and orientation-aware texture descriptors. Gabor responses provide a lightweight way to measure local frequency/orientation texture differences between clean and restored crops.

#### Van Vijle et al. (2025) — Machine Learning for Painting Conservation: A State-of-the-Art Review

Relevant point:  
The review identifies virtual restoration as an active machine-learning application in painting conservation and emphasizes reliability, data limitations, and validation concerns.

How Notebook 31 uses it:  
Notebook 31 frames texture metrics as an additional reliability-oriented diagnostic layer. The texture scores are not treated as conservation truth, but as evidence about local texture consistency under controlled synthetic damage.

#### Fontoura Júnior et al. (2023) — Assessing the Effectiveness of Inpainting Techniques in Cultural Heritage

Relevant point:  
The paper supports careful evaluation of inpainting in cultural heritage contexts using multiple criteria.

How Notebook 31 uses it:  
Notebook 31 adds texture-aware evaluation as another criterion in the controlled restoration framework. This supports the project’s broader claim that restoration trustworthiness requires several complementary signals.

#### Zhang et al. (2018) — LPIPS

Relevant point:  
LPIPS motivates learned perceptual similarity and shows that pixel-level metrics are insufficient for perceptual evaluation.

How Notebook 31 uses it:  
Notebook 31 complements LPIPS rather than replacing it. LPIPS gives learned perceptual distance, while GLCM and Gabor provide more explicit local texture descriptors.

#### Oquab et al. (2023) — DINOv2

Relevant point:  
DINOv2 provides robust visual features but does not explicitly isolate local texture preservation.

How Notebook 31 uses it:  
Notebook 31 adds texture metrics as a complementary local descriptor layer. This is useful for cases where DINOv2 feature similarity and explicit texture-distance metrics disagree.

### Project decision

Texture metrics are computed on:

`mask_bbox_crop`

This region is selected because:

- GLCM requires spatial gray-level co-occurrence structure,
- Gabor responses require local spatial frequency/orientation information,
- sparse masked pixels do not form a stable texture-analysis domain,
- the choice aligns texture metrics with the refined SSIM, LPIPS, CLIP, and DINOv2 local-region policy.

The notebook computes:

- GLCM contrast difference,
- GLCM homogeneity difference,
- GLCM energy difference,
- GLCM correlation difference,
- Gabor response descriptor differences,
- brushstroke-proxy gradient magnitude differences,
- brushstroke-proxy edge/detail density difference,
- brushstroke-proxy orientation coherence difference,
- brushstroke-proxy orientation histogram distance,
- normalized combined texture distance.

Lower texture distance means that the restored crop is closer to the clean reference crop in local texture structure.

The texture metrics are computed for:

- OpenCV Telea,
- LaMa,
- Stable Diffusion Inpainting.

The outputs include:

- per-model texture metric files,
- unified texture and brushstroke-proxy comparison,
- summary by model,
- summary by mask type,
- summary by painting category,
- high-texture brushwork focused summary,
- non-zero-only texture winner summary,
- brushstroke-proxy summary by model,
- texture disagreement cases against the refined metric vote.

### Notes for final thesis writing

This section should support the claim that trustworthy restoration evaluation should include local texture continuity.

Possible thesis wording:

> A texture-aware and brushstroke-proxy metric layer was added to evaluate whether restored regions preserve local surface structure, directional texture, and brushstroke-like detail. GLCM, Gabor, and gradient-orientation descriptors were computed on the mask-bounding-box crop because these descriptors require spatial context. This layer was interpreted as diagnostic evidence of local texture consistency rather than as brushstroke authentication or conservation correctness.

Another possible thesis wording:

> Texture metrics complement the existing metric stack by targeting a restoration failure mode that may not be fully captured by pixel, perceptual, or feature-space similarity: local smoothing or alteration of brushstroke-like structure. The resulting texture distance values were therefore used as diagnostic evidence of local texture preservation.

### Potential improvements / supervisor feedback

- Consider adding LBP if the supervisor wants a broader texture descriptor set.
- Consider adding structure-tensor visualization if the supervisor wants stronger visual explanation of brushstroke-proxy orientation behavior.
- Use the `high_texture_brushwork` focused summary when discussing texture-heavy paintings.
- Consider adding visual examples where texture or brushstroke-proxy metrics disagree with LPIPS, DINOv2, or the refined model vote.
- Consider adding texture overlays, orientation maps, or texture-difference maps to the per-case reports.

---

## 32. Stable Diffusion Uncertainty Heatmaps

### Decision supported

The uncertainty-heatmap notebook converts the Stable Diffusion multi-seed uncertainty outputs from Notebook 27 into spatial uncertainty visualizations.

The decision supported by this notebook is to make diffusion uncertainty visually inspectable rather than only reporting case-level scalar uncertainty values.

Notebook 27 already generated repeated Stable Diffusion Inpainting outputs for the same damaged inputs using four random seeds. Notebook 32 does not rerun Stable Diffusion. It reuses the existing 40-case uncertainty subset and computes per-pixel variation across seed outputs.

This supports the thesis argument that visual plausibility is not equivalent to restoration trustworthiness. A diffusion model may generate plausible-looking completions while still being spatially unstable across repeated generations.

### References

#### Rombach et al. (2022) — Latent Diffusion Models

Relevant point:  
Latent diffusion models provide the generative basis for Stable Diffusion and enable stochastic image generation through sampling.

How Notebook 32 uses it:  
Notebook 32 interprets repeated Stable Diffusion outputs as seed-based samples from a generative restoration process. The notebook visualizes where those sampled completions differ spatially for the same damaged input.

#### Li et al. (2023) — Diffusion Models for Image Restoration and Enhancement: A Comprehensive Survey

Relevant point:  
Diffusion restoration outputs require careful evaluation because visual plausibility, reference fidelity, and output stability can diverge.

How Notebook 32 uses it:  
Notebook 32 extends the uncertainty analysis by showing spatial variability maps. These maps support the thesis claim that diffusion-based restoration should not be evaluated using only a single generated output or a single reference-based score.

#### Fontoura Júnior et al. (2023) — Assessing the Effectiveness of Inpainting Techniques in Cultural Heritage

Relevant point:  
Cultural heritage inpainting evaluation benefits from multi-criteria assessment and visual inspection.

How Notebook 32 uses it:  
Notebook 32 adds a visual diagnostic layer for uncertainty. The heatmaps make it possible to inspect where the generative model varies across seeds, complementing scalar metrics and selected case reports.

#### Van Vijle et al. (2025) — Machine Learning for Painting Conservation: A State-of-the-Art Review

Relevant point:  
Painting-conservation applications require careful validation and cautious interpretation of machine-learning outputs.

How Notebook 32 uses it:  
Notebook 32 treats uncertainty heatmaps as reliability diagnostics, not as proof of conservation correctness. The notebook supports the broader framework goal of evaluating model behavior rather than claiming historical restoration truth.

### Project decision

Notebook 32 reuses the existing Stable Diffusion uncertainty subset:

- 40 non-zero damaged cases,
- 4 seeds per case,
- 160 generated Stable Diffusion outputs.

The notebook computes per-pixel standard deviation across seed outputs and summarizes uncertainty over:

- full image,
- masked region,
- mask-bounding-box crop,
- outside-mask region,
- outside boundary ring around the mask.

The boundary-ring summary is used as a transition/spillover diagnostic. It measures instability around the outside edge of the mask and should not be described as a complete inside-and-outside boundary analysis unless the implementation is later extended.

Main outputs include:

- `outputs/metrics/stable_diffusion_uncertainty_heatmap_manifest_50.csv`
- `outputs/metrics/stable_diffusion_uncertainty_heatmap_summary_by_case_50.csv`
- `outputs/metrics/stable_diffusion_uncertainty_heatmap_summary_by_mask_type_50.csv`
- `outputs/metrics/stable_diffusion_uncertainty_heatmap_summary_by_category_50.csv`
- `outputs/metrics/stable_diffusion_uncertainty_heatmap_vs_refined_performance_50.csv`
- `outputs/metrics/stable_diffusion_uncertainty_heatmap_selected_cases_50.csv`
- `outputs/reports/stable_diffusion_uncertainty_heatmap_report_50.html`

The report links to image files rather than embedding all images directly, so it should be opened within the repository output structure.

### Notes for final thesis writing

This section should support the uncertainty and trustworthiness chapter.

Possible thesis wording:

> Spatial uncertainty heatmaps were generated from multi-seed Stable Diffusion outputs by computing per-pixel variation across repeated generations for the same damaged input. These heatmaps visualize where the diffusion model produced unstable completions. Masked-region, mask-bounding-box, outside-mask, and boundary-ring uncertainty summaries were computed to distinguish instability inside the restoration target from transition-region and spillover behavior. The resulting maps were interpreted as seed-based variability diagnostics, not calibrated confidence estimates.

Another possible thesis wording:

> The heatmap analysis shows that Stable Diffusion uncertainty is spatially structured. Larger losses produced the highest masked-region variability, while boundary-ring variability exposed transition instability around some damage regions. This supports the thesis claim that generative plausibility, reference fidelity, and output stability are separate evaluation dimensions.

### Potential improvements / supervisor feedback

- Ask whether the 40-case heatmap subset is sufficient or whether uncertainty heatmaps should be expanded to all 200 non-zero cases.
- Consider adding a symmetric inner-plus-outer boundary band if the supervisor wants a stricter boundary-transition analysis.
- Add uncertainty heatmap links to the Streamlit dashboard in Notebook 34.
- Use selected high-uncertainty cases in Notebook 33 per-case reports.
