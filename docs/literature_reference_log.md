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