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