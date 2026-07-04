## 1. Preprocessing

### Decision supported

For the 50-painting controlled subset, raw paintings are resized while preserving their original aspect ratio, padded to 768 × 768 using the image median RGB color, and saved as PNG. The actual painting-content region inside the padded square is recorded for each image.

This decision supports standardized multi-model evaluation while avoiding two problematic alternatives:

1. direct resizing to a square, which geometrically distorts the artwork;
2. center cropping, which may remove real painting content and alter composition.

Later mask generation is restricted to the recorded painting-content region, so artificial damage is applied only to painting pixels rather than padding.

Later metrics should be computed across multiple regions:

- full image,
- painting-content region,
- masked region,
- mask-centered crop.

---

### References

#### Suvorov et al. — LaMa: Resolution-Robust Large Mask Inpainting with Fourier Convolutions

- Source: Suvorov, R. et al. “Resolution-Robust Large Mask Inpainting with Fourier Convolutions.”
- Type: research paper.
- Relevant point: LaMa is designed for large-mask inpainting and emphasizes resolution robustness, large receptive fields, and large-mask training. This supports the need for a preprocessing strategy that keeps input resolution controlled while preserving enough visual detail for larger missing regions.
- How it influenced this project: The project uses 768 × 768 standardized clean images so LaMa and later models can be evaluated under consistent image-size conditions. The preprocessing keeps the whole painting composition visible instead of cropping content away.

---

#### Hugging Face Diffusers / Stable Diffusion documentation and blog

- Source: Hugging Face Stable Diffusion and Diffusers documentation.
- Type: technical documentation.
- Relevant point: Stable Diffusion-style pipelines generally expect image dimensions that are compatible with the model architecture, commonly multiples of 8. Controlled image dimensions are therefore practical for diffusion-based inpainting experiments.
- How it influenced this project: The target size of 768 × 768 was selected because it is divisible by 8, preserves more painting detail than 512 × 512, and remains more computationally manageable than 1024 × 1024 for later Stable Diffusion, SDXL, and uncertainty experiments.

---

#### OpenAI CLIP preprocessing behavior

- Source: OpenAI CLIP implementation and related preprocessing discussions.
- Type: model implementation / technical reference.
- Relevant point: CLIP-style image preprocessing commonly involves resizing and center cropping to a fixed square input size. Such preprocessing can discard parts of non-square images if applied blindly.
- How it influenced this project: Because paintings may have portrait, landscape, or unusual aspect ratios, the project avoids center cropping during the main preprocessing stage. Instead, it preserves the complete artwork and records the content region. Later CLIP-based similarity should be computed carefully, especially on content-region or mask-centered crops, rather than assuming full-image square preprocessing is always meaningful.

---

#### DINOv2 preprocessing considerations

- Source: DINOv2 paper and Hugging Face / Transformers preprocessing discussions.
- Type: research paper and implementation reference.
- Relevant point: DINOv2 provides strong visual features, but model preprocessing often involves fixed crop sizes. This creates the same risk as CLIP when evaluating non-square artworks: important regions may be ignored or cropped if preprocessing is not controlled.
- How it influenced this project: DINOv2 similarity will later be computed with awareness of the painting-content region and mask-centered crop. The preprocessing metadata records the content bounding box so feature-based metrics can be applied more meaningfully.

---

### Project decision

The project rejects direct square resizing because it distorts paintings. It also rejects center cropping because it can remove actual artwork content and change the composition being evaluated.

The selected preprocessing strategy is:

- resize while preserving aspect ratio,
- pad to 768 × 768 using median RGB padding,
- save as PNG,
- record the painting-content bounding box,
- restrict later mask generation to the content region,
- compute later metrics over full image, content region, masked region, and mask-centered crop.

This strategy balances artwork preservation, reproducibility, and compatibility with OpenCV, LaMa, Stable Diffusion Inpainting, SDXL Inpainting, LPIPS, CLIP, DINOv2, visual diagnostics, and uncertainty analysis.

---

### Notes for final thesis writing

This section can later support the methodology chapter rather than the main related-work chapter. The key argument is not that padding is universally superior, but that it is a defensible compromise for this project because the study compares multiple restoration and inpainting systems under a shared evaluation framework.

Possible thesis wording:

> To avoid geometric distortion and prevent loss of painting content, each raw image was resized while preserving its original aspect ratio and padded to a fixed resolution of 768 × 768 pixels. The valid painting-content region within the padded image was recorded and used in later mask generation and metric computation. This ensured that artificial damage was applied only to painting content, while still providing standardized inputs for classical, deep learning, diffusion-based, and feature-based evaluation methods.

---

### Follow-up references to add later

- Final Stable Diffusion Inpainting model card used in the experiment.
- Final SDXL Inpainting model card used in the experiment.
- Final CLIP model variant used for feature similarity.
- Final DINOv2 model variant used for feature similarity.
- Any painting/cultural-heritage restoration paper used to justify preserving full artwork composition.

## 2. Mask Generation

### Decision supported

For the 50-painting controlled subset, five reproducible binary mask types are generated per painting:

- `zero_control`
- `scratch_thin`
- `loss_small`
- `loss_large`
- `mixed_damage`

All masks are generated only inside the recorded painting-content region, not on padded areas. Mask area is measured relative to the painting-content region and also recorded relative to the full 768 × 768 image.

The mask values follow the standard inpainting convention:

- 0 = preserved/original region,
- 255 = damaged/inpaint region.

---

### References

#### Liu et al. — Image Inpainting for Irregular Holes Using Partial Convolutions

- Source: Liu, G. et al. “Image Inpainting for Irregular Holes Using Partial Convolutions.” ECCV 2018.
- Type: research paper.
- Relevant point: The paper focuses on image inpainting with irregular holes rather than only rectangular missing regions. It motivates the use of irregular mask shapes when evaluating inpainting methods.
- How it influenced this project: The project uses irregular blob-like masks for `loss_small`, `loss_large`, and parts of `mixed_damage`, rather than simple rectangular or circular holes.

---

#### Suvorov et al. — LaMa: Resolution-Robust Large Mask Inpainting with Fourier Convolutions

- Source: Suvorov, R. et al. “Resolution-Robust Large Mask Inpainting with Fourier Convolutions.” WACV 2022.
- Type: research paper.
- Relevant point: LaMa is explicitly designed for large-mask inpainting and emphasizes performance on large missing regions.
- How it influenced this project: The project includes a `loss_large` mask type with a target area of 10–18% of the painting-content region. This creates a harder condition that can expose differences between classical, deep learning, and diffusion-based methods.

---

#### Hugging Face Diffusers inpainting documentation

- Source: Hugging Face Diffusers inpainting documentation.
- Type: technical documentation.
- Relevant point: Diffusion inpainting pipelines commonly use binary masks where white pixels indicate regions to repaint and black pixels indicate regions to preserve.
- How it influenced this project: The project saves masks as binary grayscale PNG files using 255 for damaged/inpaint regions and 0 for preserved regions. This keeps the masks compatible with OpenCV, LaMa, Stable Diffusion Inpainting, and SDXL Inpainting workflows.

---

#### Cultural heritage and mural restoration literature

- Source: cultural heritage image restoration and mural restoration studies.
- Type: research literature.
- Relevant point: Cultural heritage images often contain scratches, cracks, missing regions, fragmented damage, and texture-sensitive degradation. Restoration evaluation should therefore not rely only on generic rectangular or blob masks.
- How it influenced this project: The project includes `scratch_thin` and `mixed_damage` masks in addition to small and large missing-region masks. The mixed condition combines scratches, scattered losses, larger missing areas, and edge-adjacent damage to better approximate compound deterioration.

---

### Project decision

The project rejects using only simple rectangular masks because they do not reflect the variety of damage patterns relevant to painting restoration. Instead, it uses five mask types:

- `zero_control` for sanity checking,
- `scratch_thin` for crack/scratch-like damage,
- `loss_small` for small missing-paint regions,
- `loss_large` for larger missing regions,
- `mixed_damage` for compound deterioration.

The generated masks are reproducible through deterministic seeds. Each mask records target area, actual area relative to content region, actual area relative to full image, bounding box information, and whether it touches the content-region border.

The notebook uses red overlays only for visual inspection. The saved masks themselves remain binary grayscale images. Overlay colors may be changed in final report figures to improve readability against different painting palettes.

---

### Notes for final thesis writing

This section can later support the methodology chapter by explaining why the artificial damage setup uses multiple controlled damage types rather than a single generic mask.

Possible thesis wording:

> Artificial damage was simulated using five mask conditions: no damage, thin scratches, small losses, large losses, and mixed damage. The masks were generated only inside the recorded painting-content region to avoid applying artificial damage to padded areas introduced during preprocessing. This enabled controlled comparison across restoration difficulty levels while maintaining compatibility with classical, deep learning, and diffusion-based inpainting methods.

## 3. Damage Image Creation

### Decision supported

For each generated binary mask, a damaged RGB image is created by replacing masked pixels with white RGB(255, 255, 255). The binary mask remains the authoritative definition of the region to restore.

The damaged image is used as a controlled visual/input representation of synthetic damage. The mask is retained separately for restoration models and evaluation.

---

### References

#### OpenCV inpainting documentation

- Source: OpenCV inpainting documentation.
- Type: technical documentation.
- Relevant point: OpenCV inpainting expects an input image and a single-channel mask where non-zero mask pixels indicate the region to be inpainted.
- How it influenced this project: The project saves damaged images together with binary masks. The damaged image provides the visible corrupted input, while the mask tells OpenCV Telea which region to restore.

---

#### Hugging Face Diffusers inpainting documentation

- Source: Hugging Face Diffusers inpainting documentation.
- Type: technical documentation.
- Relevant point: Diffusion inpainting pipelines commonly use masks where white pixels indicate regions to repaint and black pixels indicate regions to preserve.
- How it influenced this project: The project keeps binary mask files separate from damaged images. This preserves compatibility with later Stable Diffusion Inpainting and SDXL Inpainting experiments.

---

#### LaMa / simple-lama inpainting usage

- Source: LaMa-related implementations and simple-lama-inpainting usage.
- Type: implementation reference.
- Relevant point: LaMa-style inpainting workflows use an image and a binary mask to define the missing region.
- How it influenced this project: The project stores both damaged images and binary masks so later LaMa integration can use the same controlled mask cases as OpenCV and diffusion models.

---

### Project decision

The project uses white-fill damaged images for the 50-painting controlled subset. This is not intended to simulate every possible physical appearance of real painting damage. Instead, it provides a controlled synthetic corruption representation while the binary mask defines the exact restoration target.

For each case, metadata records the clean image path, mask path, damaged image path, fill strategy, fill color, damaged area in pixels, damaged area relative to the painting-content region, and damaged area relative to the full 768 × 768 image.

---

### Notes for final thesis writing

This section can support the methodology chapter by clarifying the distinction between artificial damage masks and damaged input images.

Possible thesis wording:

> For each artificial damage mask, a damaged input image was created by replacing masked pixels with white RGB values while preserving all unmasked pixels exactly. The binary mask remained the authoritative definition of the restoration region and was stored separately. This ensured that all restoration methods were evaluated using the same controlled damage cases while preserving compatibility with OpenCV, LaMa, and diffusion-based inpainting workflows.

## 4. OpenCV Telea Restoration Baseline

### Decision supported

OpenCV Telea is used as the first restoration baseline for the 50-painting controlled subset.

The method is included as a deterministic classical inpainting baseline. It is not treated as a painting-specific restoration model. Its purpose is to provide a simple reference point before evaluating learned inpainting models.

---

### Research papers

#### Telea (2004) — Fast Marching Method inpainting

- Reference: Telea, A. (2004). *An Image Inpainting Technique Based on the Fast Marching Method.*
- Type: classical inpainting method paper.
- Relevant point: Telea proposes a fast marching method for digital inpainting, filling damaged regions progressively from their boundaries using nearby image information.
- How it influenced this project: This is the core method behind the OpenCV Telea baseline used in the project. The method is suitable as a fast deterministic baseline for local inpainting, especially for smaller missing regions.

#### Bertalmio et al. (2000) — foundational image inpainting

- Reference: Bertalmio, M., Sapiro, G., Caselles, V., & Ballester, C. (2000). *Image Inpainting.*
- Type: foundational inpainting paper.
- Relevant point: The paper frames digital inpainting as the automatic filling of user-selected missing or damaged regions by propagating surrounding image information into the target area.
- How it influenced this project: This supports the general framing of the task as controlled image inpainting over known damaged regions.

#### Bertalmio, Bertozzi, and Sapiro (2001) — Navier-Stokes inpainting

- Reference: Bertalmio, M., Bertozzi, A. L., & Sapiro, G. (2001). *Navier-Stokes, Fluid Dynamics, and Image and Video Inpainting.*
- Type: classical PDE-based inpainting paper.
- Relevant point: The paper connects inpainting with fluid-dynamics/PDE-based propagation of image structures.
- How it influenced this project: This paper helps position OpenCV-style classical inpainting methods as pre-deep-learning restoration baselines.

#### Quan et al. (2024) — deep learning inpainting survey

- Reference: Quan, W., Chen, J., Liu, Y., Yan, D.-M., & Wonka, P. (2024). *Deep Learning-based Image and Video Inpainting: A Survey.*
- Type: survey paper.
- Relevant point: The survey reviews modern deep learning inpainting methods, including CNN, GAN, VAE, transformer, and diffusion-based approaches, as well as common evaluation settings and challenges.
- How it influenced this project: This supports the project’s staged comparison between a classical baseline and later learned inpainting methods.

---

### Technical documentation

#### OpenCV inpainting documentation

- Source: OpenCV inpainting documentation.
- Type: technical documentation.
- Relevant point: OpenCV inpainting uses an input image and a single-channel mask where non-zero mask pixels indicate the region to be inpainted.
- How it influenced this project: This confirms the implementation convention used in the OpenCV Telea notebook: damaged image plus binary mask, with mask value 255 defining the restoration area.

---

### Project decision

The project uses OpenCV Telea as the first restoration baseline with a fixed radius of 3. The same radius is applied across all 50 paintings and all five mask types to ensure deterministic and comparable baseline results.

The baseline is expected to perform better on small local scratches and small missing regions than on large losses or mixed damage. This expected limitation is useful because the project evaluates not only restoration quality, but also when and where each model type fails.

---

### Notes for final thesis writing

Possible thesis wording:

> OpenCV Telea was included as a deterministic classical inpainting baseline. The method is based on Telea’s fast marching approach, where missing regions are filled progressively from their boundaries using nearby image information. Classical inpainting methods provide useful non-learning reference points because they are fast, deterministic, and reproducible, but they are not expected to recover large semantic structures or painting-specific stylistic details. In this thesis, OpenCV Telea therefore serves as a baseline for comparing later learned inpainting models.

## 5. Classical Metric Evaluation

### Decision supported

Classical full-reference image metrics are used to evaluate the OpenCV Telea baseline against the clean reference images.

The project computes MSE, MAE, PSNR, and SSIM for both damaged and restored images. Metrics are evaluated across multiple regions because full-image scores can hide restoration failures when the damaged area is small.

---

### Research papers

#### Wang et al. (2004) — SSIM

- Reference: Wang, Z., Bovik, A. C., Sheikh, H. R., & Simoncelli, E. P. (2004). *Image Quality Assessment: From Error Visibility to Structural Similarity.*
- Type: image quality assessment paper.
- Relevant point: The paper introduces SSIM as a structural similarity metric designed to move beyond simple pixel-error visibility.
- How it influenced this project: SSIM is included as a classical structural metric alongside MSE, MAE, and PSNR. The project computes SSIM only on spatial image regions, not on sparse masked pixels.

#### Zhang et al. (2018) — LPIPS and limitations of shallow metrics

- Reference: Zhang, R., Isola, P., Efros, A. A., Shechtman, E., & Wang, O. (2018). *The Unreasonable Effectiveness of Deep Features as a Perceptual Metric.*
- Type: perceptual metric paper.
- Relevant point: The paper shows that traditional metrics such as PSNR and SSIM do not always align with human perceptual similarity.
- How it influenced this project: Classical metrics are treated as necessary but insufficient. This motivates the later use of perceptual and feature-based metrics such as LPIPS, CLIP, and DINOv2.

#### Horé and Ziou (2010) — PSNR and SSIM relationship

- Reference: Horé, A., & Ziou, D. (2010). *Image Quality Metrics: PSNR vs. SSIM.*
- Type: image quality metric comparison paper.
- Relevant point: The paper discusses differences between PSNR and SSIM as image quality measures.
- How it influenced this project: The project includes both distortion-based and structural metrics rather than relying on a single score.

---

### Project decision

The project reports classical metrics across multiple evaluation regions:

- full image,
- content region,
- masked region,
- mask bounding-box crop.

The masked region is especially important because it corresponds directly to the restoration target. Full-image metrics are retained but interpreted cautiously because unchanged pixels can dominate the score.

SSIM is not computed over sparse masked pixels. Instead, SSIM is computed on image-like spatial regions, including the full image, the content region, and the mask bounding-box crop.

---

### Notes for final thesis writing

Possible thesis wording:

> Classical full-reference metrics were computed to quantify pixel-level and structural similarity between the clean reference paintings, damaged inputs, and restored outputs. MSE, MAE, PSNR, and SSIM were evaluated across full-image, content-region, masked-region, and mask-bounding-box regions. The masked region directly measures the artificial restoration target, while the content region avoids distortion from preprocessing padding. SSIM was not computed on sparse masked pixels because it assumes local spatial image structure. These classical metrics provide useful baseline measurements, but they are not treated as sufficient evidence of perceptual or art-historical restoration quality.

## 6. Difference-Map Diagnostic Evaluation

### Decision supported

Difference maps are used as visual diagnostics to complement scalar full-reference metrics.

Scalar metrics such as MSE, MAE, PSNR, and SSIM summarize restoration quality numerically, but they do not show where errors occur. Difference maps visualize the spatial distribution of damaged-input error, restored-output error, and restoration improvement.

---

### Research connection

This step builds on the image-quality assessment motivation discussed in the classical metrics section. Full-reference metrics provide useful numerical summaries, but visual diagnostics are needed to interpret spatial error patterns.

Relevant references remain:

- Wang et al. (2004), for structural similarity and the motivation to move beyond simple error visibility.
- Zhang et al. (2018), for the argument that traditional pixel-level metrics do not always align with perceptual similarity.
- Horé and Ziou (2010), for comparison of PSNR and SSIM as image quality metrics.

---

### Project decision

For each OpenCV restoration case, the project computes mean absolute RGB error maps:

- clean vs damaged,
- clean vs restored.

A signed improvement map is then computed as:

`damaged_error - restored_error`

Positive values indicate reduced error after restoration. Negative values indicate worsened pixels.

Diagnostic figures are generated for selected cases first, then for all 250 OpenCV restoration cases. The selected diagnostic cases include strongest and weakest masked-region MSE-improvement cases, plus one mixed-damage case per painting category.

---

### Notes for final thesis writing

Possible thesis wording:

> Difference maps were generated to complement scalar full-reference metrics by visualizing where restoration errors remained or improved. For each case, absolute error maps were computed between the clean reference and both the damaged and restored images. A signed improvement map was then computed by subtracting restored error from damaged-input error. This allowed inspection of whether numerical improvement corresponded to meaningful local restoration or merely to replacement of high-contrast synthetic damage with smoother interpolated regions.

## 7. LPIPS Perceptual Metric Evaluation

### Decision supported

LPIPS is used as a perceptual full-reference metric to complement classical pixel-level and structural metrics.

The project computes LPIPS between:

- clean reference and damaged input,
- clean reference and OpenCV-restored output.

LPIPS is evaluated over full images, painting content regions, and mask bounding-box crops.

---

### Research papers

#### Zhang et al. (2018) — LPIPS

- Reference: Zhang, R., Isola, P., Efros, A. A., Shechtman, E., & Wang, O. (2018). *The Unreasonable Effectiveness of Deep Features as a Perceptual Metric.*
- Type: perceptual image similarity paper.
- Relevant point: The paper shows that distances in deep feature spaces can better align with human perceptual similarity than traditional low-level metrics such as PSNR and SSIM.
- How it influenced this project: LPIPS is included to complement classical full-reference metrics and to test whether OpenCV restoration outputs are perceptually closer to the clean reference than the damaged inputs.

---

### Project decision

LPIPS is computed only on image-like spatial regions:

- full image,
- content region,
- mask bounding-box crop.

The project does not compute LPIPS directly on sparse masked pixels because LPIPS depends on spatial feature activations. The mask bounding-box crop is used as the local perceptual comparison region around the damaged area.

LPIPS improvement is computed as:

`damaged_lpips - restored_lpips`

Positive improvement indicates that the restored output is perceptually closer to the clean reference than the damaged input.

---

### Notes for final thesis writing

Possible thesis wording:

> LPIPS was included as a perceptual full-reference metric to complement classical pixel-level and structural measures. Unlike MSE, MAE, PSNR, and SSIM, LPIPS compares images in a learned feature space and has been shown to better reflect perceptual similarity in many image-comparison settings. In this thesis, LPIPS was computed for full images, painting content regions, and mask-bounding-box crops. Sparse masked pixels were not used directly because LPIPS assumes spatial image inputs. The resulting LPIPS scores were compared with classical metric rankings to identify cases where pixel-level improvement and perceptual similarity diverged.

## 8. CLIP and DINOv2 Feature-Space Similarity

### Decision supported

CLIP and DINOv2 are used as pretrained feature-space diagnostics to complement classical metrics and LPIPS.

The project computes cosine similarity between image embeddings for:

- clean reference vs damaged input,
- clean reference vs restored output.

The feature-space improvement is computed as:

`restored_similarity - damaged_similarity`

Positive improvement indicates that the restored output is closer to the clean reference in the corresponding pretrained feature space.

---

### Interpretation limitation

CLIP and DINOv2 are not painting-restoration-specific evaluation models. Their embeddings are useful as pretrained feature-space diagnostics, but they do not determine historical correctness, conservation validity, or restoration faithfulness.

Observed disagreement between CLIP, DINOv2, LPIPS, and classical metrics is therefore not treated as an error. Instead, disagreement is used diagnostically to identify cases where pixel-level recovery, perceptual similarity, and feature-space similarity diverge.

In the OpenCV Telea baseline, large-loss mask-bounding-box crops showed weak CLIP improvement and negative average DINOv2 improvement. This is interpreted as a diagnostic signal that OpenCV can remove obvious visible damage while still failing to recover original local visual structure in a pretrained self-supervised feature space.

### Research papers

#### Radford et al. (2021) — CLIP

- Reference: Radford, A., Kim, J. W., Hallacy, C., Ramesh, A., Goh, G., Agarwal, S., Sastry, G., Askell, A., Mishkin, P., Clark, J., Krueger, G., & Sutskever, I. (2021). *Learning Transferable Visual Models From Natural Language Supervision.*
- Type: image-text contrastive representation learning paper.
- Relevant point: CLIP learns transferable image representations through contrastive learning on image-text pairs.
- How it influenced this project: CLIP image embeddings are used as a broad semantic/visual feature-space signal for comparing damaged and restored image regions against the clean reference.

#### Oquab et al. (2023) — DINOv2

- Reference: Oquab, M., Darcet, T., Moutakanni, T., Vo, H. V., Szafraniec, M., Khalidov, V., Fernandez, P., HAZIZA, D., Massa, F., El-Nouby, A., Assran, M., Ballas, N., Galuba, W., Howes, R., Huang, P.-Y., Li, S.-W., Misra, I., Rabbat, M., Sharma, V., Synnaeve, G., Xu, H., Jegou, H., Mairal, J., Labatut, P., Joulin, A., & Bojanowski, P. (2023). *DINOv2: Learning Robust Visual Features without Supervision.*
- Type: self-supervised visual foundation model paper.
- Relevant point: DINOv2 provides strong general-purpose visual features without relying on language supervision.
- How it influenced this project: DINOv2 embeddings are used as an additional visual feature-space diagnostic, distinct from CLIP and LPIPS.

---

### Project decision

Feature similarity is computed only on image-like spatial regions:

- full image,
- content region,
- mask bounding-box crop.

The project does not compute CLIP or DINOv2 similarity directly on sparse masked pixels because both models expect spatial image inputs.

The mask bounding-box crop is used as the local feature-comparison region around the damaged area.

---

### Notes for final thesis writing

Possible thesis wording:

> CLIP and DINOv2 feature similarities were included to complement classical full-reference metrics and LPIPS. CLIP provides an image-text-supervised representation space, while DINOv2 provides a self-supervised visual representation space. In this thesis, both were used as diagnostic feature spaces rather than final restoration-quality judges. Similarity was computed between clean and damaged regions and between clean and restored regions. Improvement was defined as restored similarity minus damaged similarity. Cases where CLIP, DINOv2, LPIPS, and classical metric rankings diverged were treated as important diagnostic examples, because they show that restoration quality cannot be fully captured by any single metric family.

## 9. OpenCV Baseline Report Interpretation

### Decision supported

The OpenCV Telea baseline report consolidates the first complete 50-painting evaluation pass.

The report is used to interpret the deterministic classical baseline before introducing pretrained or generative inpainting models. It combines classical metrics, LPIPS, CLIP/DINOv2 feature similarities, error-map figures, and diagnostic case selection.

---

### Project decision

The report does not treat any single metric as the final measure of restoration quality. Instead, it compares multiple metric families and selected visual examples.

The report emphasizes that OpenCV Telea can reduce obvious synthetic white damage while still failing to recover faithful local structure, especially for large-loss cases.

Metric disagreement is interpreted as part of the evaluation framework. Cases where pixel-level metrics, perceptual metrics, feature-space metrics, and visual diagnostics diverge are useful for identifying restoration failure modes.

---

### Notes for final thesis writing

Possible thesis wording:

> An interim OpenCV Telea baseline report was generated after the full 50-painting evaluation pass. The report consolidates classical metrics, LPIPS, CLIP and DINOv2 feature similarities, diagnostic error maps, and selected cases. The baseline showed reliable improvement over white-filled synthetic damage, especially for scratch-like and local masks. However, large missing regions remained difficult, and feature-space metrics revealed cases where visible damage removal did not correspond to faithful structural recovery. These findings support the thesis argument that trustworthy evaluation of AI-assisted painting restoration requires multiple complementary metrics and visual diagnostics rather than a single scalar score.

## 10. LaMa Implementation Planning

### Decision supported

LaMa is selected as the next restoration model after the OpenCV Telea baseline.

OpenCV Telea provides a deterministic classical interpolation baseline. LaMa provides the next step: a pretrained open inpainting model designed for larger and more complex masks.

---

### Research paper

#### Suvorov et al. — LaMa

- Reference: Suvorov, R., Logacheva, E., Mashikhin, A., Remizova, A., Ashukha, A., Silvestrov, A., Kong, N., Goka, H., Park, K., & Lempitsky, V. *Resolution-robust Large Mask Inpainting with Fourier Convolutions.*
- Type: pretrained image inpainting model.
- Relevant point: LaMa uses architectural and training choices intended to improve large-mask inpainting, including Fast Fourier Convolutions and large-mask training.
- How it influenced this project: LaMa is selected as the first pretrained open inpainting baseline after OpenCV Telea because it is expected to handle larger missing regions better than a purely local classical method.

---

### Implementation decision

The LaMa paper and official project are treated as the method source. For practical execution in this repository, the planned runtime implementation is IOPaint with `model=lama`.

This implementation choice is made for reproducibility and batch integration. IOPaint provides a command-line workflow for processing image and mask folders, which fits the project’s existing 50-painting pipeline.

The repository will use temporary staging folders with matched image and mask filenames before collecting outputs into the project’s standard restored-image directory.

---

### Interpretation limitation

LaMa is not painting-restoration-specific. It is trained as a general image inpainting model and may rely on natural-image priors that do not fully match historical paintings, brushstroke texture, abstraction, surrealism, or conservation-style restoration.

A visually plausible LaMa output is not necessarily a historically faithful restoration. Since this project uses synthetic damage, the clean reference is known, allowing LaMa outputs to be evaluated against ground truth using the same multi-metric framework already applied to OpenCV Telea.

Possible thesis wording:

> LaMa was selected as the first pretrained open inpainting baseline after OpenCV Telea. Its architecture is designed for large-mask inpainting and therefore provides a useful comparison against the local classical OpenCV baseline. However, LaMa is not trained specifically for painting restoration, so its outputs are evaluated as candidate restorations rather than assumed faithful reconstructions. The implementation uses a practical IOPaint command-line workflow while retaining the LaMa paper and official project as the methodological source.

## 11. LaMa Restoration Runtime Integration

### Decision supported

LaMa was implemented as the first pretrained open inpainting baseline after OpenCV Telea.

The LaMa paper and official project remain the methodological source. The practical runtime used in this repository is IOPaint with `model=lama`, wrapped through `src/restoration_eval/restoration_lama.py`.

---

### Implementation relevance

The LaMa runtime integration supports the thesis framework by adding a learned pretrained inpainting model after a deterministic classical baseline.

This allows the evaluation framework to compare:

- a local classical inpainting method: OpenCV Telea,
- a pretrained learned inpainting method: LaMa.

This comparison is important because the models have different expected behavior. OpenCV Telea mainly performs local interpolation from surrounding pixels. LaMa uses learned image priors and a larger effective receptive field, so it may better handle larger missing regions but may also introduce plausible yet incorrect content.

---

### Reproducibility note

The repository does not call LaMa manually from notebook cells. Instead, the LaMa runtime is wrapped in `src/restoration_eval/restoration_lama.py`.

The module stages damaged images and masks into temporary folders with matching filenames, runs IOPaint LaMa through a controlled subprocess call, collects outputs into the project’s standard restored-image folder, and writes restoration metadata.

The subprocess environment forces UTF-8 output and disables decorative terminal behavior where possible. This was necessary because IOPaint/Rich progress output produced a Windows console encoding issue during notebook execution.

---

### Interpretation limitation

LaMa outputs are not treated as historically faithful restoration. LaMa is a general pretrained inpainting model, not a painting-conservation-specific model.

The generated images are therefore candidate restorations under controlled synthetic damage. Their quality must be evaluated against the known clean references using the same multi-metric framework applied to OpenCV Telea.

The selected visual inspection figures generated in Notebook 11 are diagnostic sanity checks only. They are not final quality rankings.

Possible thesis wording:

> LaMa was integrated as the first pretrained learned inpainting baseline after OpenCV Telea. The implementation uses IOPaint as a practical batch runtime while retaining the LaMa paper and official project as the methodological source. Outputs are evaluated as candidate restorations rather than assumed faithful reconstructions, since LaMa is not trained specifically for painting conservation.

## 12. LaMa Classical Metric Evaluation

### Decision supported

LaMa outputs were evaluated using the same classical full-reference metric framework previously applied to OpenCV Telea.

This supports direct model comparison because the two baselines are evaluated under the same controlled synthetic damage conditions, using the same clean references, masks, and evaluation regions.

---

### Metrics used

The classical metrics are:

- MSE,
- MAE,
- PSNR,
- SSIM.

These metrics measure pixel-level or structure-based similarity between the clean reference and the damaged/restored images.

The metric regions are:

- full image,
- content region,
- masked region,
- mask bounding-box crop.

The masked-region rows focus on the actual damaged pixels. The mask-bounding-box crop provides an image-like local region around the damage, allowing SSIM to be computed in a spatially meaningful way.

---

### Interpretation limitation

Classical metrics are useful for controlled synthetic restoration because the clean reference is known. However, they are not sufficient as standalone restoration-quality measures.

A high MSE or MAE improvement indicates numerical closeness to the clean reference, especially within masked pixels. It does not necessarily mean the restoration is perceptually convincing, semantically correct, or historically faithful.

This is especially important for LaMa because it is a learned pretrained inpainting model. It may generate visually plausible content that reduces pixel error in some cases, while still altering painterly texture, structure, or historical detail.

The classical metric results should therefore be interpreted together with:

- visual diagnostic examples,
- LPIPS perceptual similarity,
- CLIP and DINOv2 feature-space similarity,
- model-comparison analysis.

Possible thesis wording:

> Classical full-reference metrics were computed for LaMa using the same region-based framework applied to OpenCV Telea. These metrics quantify numerical similarity to the known clean reference under controlled synthetic damage. However, classical metric improvement is not treated as sufficient evidence of faithful restoration, especially for learned inpainting models that may generate plausible but incorrect content.

## 13. LaMa Difference/Error-Map Diagnostics

### Decision supported

Spatial error-map diagnostics were generated for LaMa using the same visual diagnostic framework previously applied to OpenCV Telea.

This supports direct comparison between restoration models because the same clean references, damaged inputs, masks, and visualization structure are used.

---

### Diagnostic maps generated

Each diagnostic figure contains:

- clean reference image,
- binary damage mask,
- damaged input,
- restored output,
- clean-vs-damaged absolute error,
- clean-vs-restored absolute error,
- signed restoration improvement,
- masked signed restoration improvement.

The signed improvement map is computed by subtracting the restored error map from the damaged error map. Positive values indicate that restoration reduced error relative to the damaged input. Negative values indicate regions where the restored image became farther from the clean reference.

---

### Interpretation limitation

Error maps provide spatial diagnostic evidence, but they are not final restoration-quality judgments.

They help reveal where a model reduces pixel-level error, where residual errors remain, and where restoration may worsen local differences. However, they do not directly measure historical correctness, conservation validity, or semantic faithfulness.

Possible thesis wording:

> Error-map diagnostics were used to spatially localize restoration behavior. Positive signed-improvement regions indicate areas where the restored output became numerically closer to the clean reference, while negative regions identify local degradation relative to the damaged input. These maps complement scalar metrics by showing where errors occur, but they are interpreted as diagnostic evidence rather than standalone measures of restoration quality.

## 14. LaMa LPIPS Perceptual Metric Evaluation

### Decision supported

LaMa was evaluated with LPIPS using the same perceptual metric framework previously applied to OpenCV Telea.

This supports direct model comparison because both models are evaluated against the same clean references, damaged inputs, masks, and spatial evaluation regions.

---

### Metric interpretation

LPIPS measures perceptual distance between two images using deep neural network feature activations. Lower LPIPS indicates higher perceptual similarity.

For this project, LPIPS is computed for:

- clean reference versus damaged input,
- clean reference versus restored output.

LPIPS improvement is defined as:

`damaged_lpips - restored_lpips`

A positive value indicates that the restoration moved the image closer to the clean reference in LPIPS space.

---

### Evaluation regions

LPIPS is computed over image-like regions:

- full image,
- content region,
- mask bounding-box crop.

Sparse masked pixels are not evaluated directly with LPIPS because LPIPS expects spatial image patches rather than unordered pixel sets. The mask bounding-box crop provides a local image region around the damage while preserving spatial structure.

---

### Interpretation limitation

LPIPS provides a perceptual similarity signal, but it is not a conservation-specific or historically grounded restoration metric.

A better LPIPS score does not necessarily mean that a restoration is historically accurate, semantically faithful, or acceptable for conservation use. It indicates perceptual closeness to the known clean reference under controlled synthetic damage.

Possible thesis wording:

> LPIPS was included to complement pixel-level metrics with a perceptual similarity measure. Since LPIPS operates on spatial image patches, it was computed over the full image, content region, and mask-bounding-box crop rather than sparse masked pixels. The resulting scores help identify whether restoration outputs are perceptually closer to the clean reference, but they are interpreted alongside classical metrics, feature-space metrics, and visual diagnostics rather than as standalone evidence of restoration quality.

## 15. LaMa CLIP and DINOv2 Feature-Space Similarity Evaluation

### Decision supported

LaMa was evaluated with CLIP and DINOv2 feature-space similarity using the same framework previously applied to OpenCV Telea.

This supports direct model comparison because both baselines are evaluated against the same clean references, damaged inputs, masks, and spatial evaluation regions.

---

### Metrics used

The feature-space metrics are based on cosine similarity between feature embeddings.

For each evaluated region, similarities are computed for:

- clean reference versus damaged input,
- clean reference versus restored output.

Feature-similarity improvement is defined as:

`restored_similarity - damaged_similarity`

A positive value indicates that the restored output moved closer to the clean reference in the selected feature space.

---

### Models used

The feature models are:

- CLIP: `openai/clip-vit-base-patch32`,
- DINOv2: `dinov2_vits14`.

CLIP provides a broad image-text pretrained visual representation. DINOv2 provides a self-supervised visual representation that can be useful for structural and visual similarity analysis.

---

### Evaluation regions

Feature-space similarity is computed over image-like regions:

- full image,
- content region,
- mask bounding-box crop.

Sparse masked pixels are not evaluated directly because CLIP and DINOv2 expect spatial image inputs rather than unordered pixel sets. The mask bounding-box crop provides a local image region around the damage while preserving spatial structure.

---

### Interpretation limitation

CLIP and DINOv2 similarities provide feature-space evidence, but they are not conservation-specific measures.

Higher feature similarity does not necessarily mean that a restoration is historically accurate, semantically faithful, or acceptable for conservation use. These metrics are interpreted together with classical metrics, LPIPS, spatial error maps, and selected visual diagnostics.

Possible thesis wording:

> CLIP and DINOv2 feature-space similarities were included to complement pixel-level and perceptual metrics with pretrained visual representations. Similarity improvements indicate whether restored outputs move closer to the clean reference in feature space. However, these models are not trained specifically for painting conservation, so their scores are interpreted as diagnostic signals rather than standalone evidence of restoration quality.

## 16. LaMa Standalone Baseline Report

### Decision supported

A standalone LaMa baseline report was generated to consolidate the model's evaluation results across classical, perceptual, feature-space, and visual diagnostic evidence.

This report supports the broader evaluation-framework goal by showing how one learned inpainting baseline behaves across multiple metric families and painting categories.

---

### Report scope

The LaMa report focuses on the 200 non-zero damage cases from the controlled 50-painting subset.

The report combines:

- masked-region classical metrics,
- mask-bounding-box LPIPS metrics,
- mask-bounding-box CLIP and DINOv2 feature-space metrics,
- selected diagnostic error-map figures,
- summaries by mask type and painting category,
- metric correlation analysis,
- selected strongest and weakest diagnostic cases.

Zero-control cases are excluded from the main report dataframe because they contain no damaged region, but they remain part of the metric validation notebooks.

---

### Interpretation limitation

The standalone report is a diagnostic summary, not a final restoration-quality judgment.

LaMa is treated as a learned pretrained inpainting baseline. The report does not claim that LaMa produces historically faithful painting restoration. Instead, it evaluates whether the framework can reveal where LaMa improves, fails, or produces disagreement across metric families.

Possible thesis wording:

> The LaMa baseline report consolidates scalar metrics and spatial diagnostics into a single model-specific artifact. It is used to inspect learned inpainting behavior across damage types and painting categories, while preserving the distinction between numerical improvement, perceptual similarity, feature-space alignment, and conservation-level restoration faithfulness.

## 17. OpenCV Telea versus LaMa Comparison

### Decision supported

A direct comparison between OpenCV Telea and LaMa was generated to evaluate two different restoration paradigms under the same controlled experimental setup.

The compared model families are:

- deterministic local interpolation: OpenCV Telea,
- learned pretrained inpainting: LaMa.

This comparison supports the thesis goal of building a trustworthy evaluation framework rather than only reporting isolated model scores.

---

### Comparison design

The comparison is case-paired. Each OpenCV Telea output is matched to the corresponding LaMa output using:

- `painting_id`,
- `mask_id`,
- `mask_type`.

This ensures that both models are evaluated on identical paintings, masks, damaged inputs, and clean references.

The main local comparison uses:

- masked-region classical metrics,
- mask-bounding-box LPIPS metrics,
- mask-bounding-box CLIP and DINOv2 feature-space metrics.

The resulting unified comparison table contains 200 non-zero damage cases.

---

### Metric deltas and winners

For each paired case, LaMa-minus-OpenCV deltas were computed for the main metric improvements.

Winner columns were added for:

- masked-region MSE improvement,
- mask-bounding-box LPIPS improvement,
- mask-bounding-box CLIP similarity improvement,
- mask-bounding-box DINOv2 similarity improvement.

A compact overall metric vote was computed from these winner columns. This vote is interpreted only as a diagnostic summary, not as a final restoration-quality label.

---

### Metric disagreement analysis

Metric disagreement cases were exported separately.

These cases include examples where:

- LaMa improves MSE more than OpenCV but loses DINOv2 feature similarity,
- LaMa improves LPIPS more than OpenCV but loses DINOv2 feature similarity,
- the two models split wins across metric families,
- the overall metric vote is mixed or tied.

These cases are especially important for the thesis because they show that pixel-level, perceptual, and feature-space metrics can expose different restoration behaviors.

Possible thesis wording:

> The OpenCV Telea versus LaMa comparison demonstrates why AI-assisted painting restoration should not be evaluated with a single scalar metric. A model may improve local pixel error while failing to improve perceptual or feature-space similarity. The framework therefore treats metric disagreement as diagnostic evidence rather than noise.