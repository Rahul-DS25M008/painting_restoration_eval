# Methodology Notes

## Preprocessing decision

The 50-painting controlled subset uses aspect-ratio-preserving resizing followed by median-RGB padding to 768 × 768 pixels. This preserves the full artwork composition without geometric distortion or center-crop content loss.

For each processed image, the actual painting-content region inside the padded square is recorded. Later mask generation is restricted to this region so artificial damage is applied only to painting pixels and not padding.

Later metrics should be computed across multiple regions:

- full image,
- content region,
- masked region,
- mask-centered crop.

This design supports consistent inputs across OpenCV, LaMa, Stable Diffusion Inpainting, SDXL Inpainting, LPIPS, CLIP, DINOv2, visual diagnostics, and uncertainty analysis.

## Mask generation decision

For the 50-painting controlled subset, five masks are generated per processed painting:

- `zero_control`
- `scratch_thin`
- `loss_small`
- `loss_large`
- `mixed_damage`

All masks are binary grayscale PNG files at 768 × 768 pixels. Pixel value 0 represents preserved image regions, while 255 represents the damaged region to be restored. Masks are generated only inside the recorded painting-content region from preprocessing, so artificial damage is never applied to padded areas.

The current target area ranges are defined relative to the painting-content region:

- `zero_control`: 0%
- `scratch_thin`: 1–3%
- `loss_small`: 3–6%
- `loss_large`: 10–18%
- `mixed_damage`: 8–15%

This design supports controlled comparison across damage types. The zero-control condition acts as a sanity check, while the remaining masks represent increasingly complex restoration conditions: thin cracks/scratches, small paint losses, large losses, and combined degradation.

During visual inspection of the 50-painting pilot masks, `scratch_thin` masks often touched the painting-content boundary. This is acceptable for the pilot because scratches and cracks can extend across large portions of a painting, but it should be reviewed again before scaling to the final dataset.

The red mask overlay used in notebooks is only a diagnostic visualization choice. Saved masks remain binary grayscale files. In final report figures, overlay colors may be adjusted for readability depending on the painting palette.

## Damage image creation decision

For the 50-painting controlled subset, damaged images are created by applying each binary mask to its corresponding processed clean painting.

The binary mask remains the authoritative definition of the damaged/inpaint region:

- 0 = preserved/original region
- 255 = damaged/inpaint region

For each mask case, pixels inside the damaged region are filled with white RGB(255, 255, 255), while all pixels outside the mask are preserved exactly. This creates one RGB damaged PNG image per mask case.

The white-fill strategy is used because it provides a clear visual representation of synthetic damage and is compatible with the OpenCV Telea baseline. Later model pipelines may use the damaged image, the mask, or both depending on their input requirements.

The zero-control condition produces a damaged image identical to the processed clean image. This acts as a sanity check for later restoration and evaluation stages.

Validation checks confirmed that:

- all 250 damaged images were generated,
- all damaged images are RGB PNG files at 768 × 768 pixels,
- zero-control damaged images are identical to their clean originals,
- non-zero mask cases change only pixels inside the mask,
- all masked pixels are set to the configured white fill color,
- no pixels outside the mask are modified.

## OpenCV Telea baseline restoration decision

For the 50-painting controlled subset, OpenCV Telea was used as the first restoration baseline.

OpenCV Telea is treated as a deterministic classical inpainting method rather than a painting-specific restoration model. Its role in this project is to provide a simple non-learning baseline against which later learned inpainting methods can be compared.

The baseline uses:

- input image: white-filled damaged RGB image,
- mask: binary grayscale mask where 255 indicates the inpainting region,
- algorithm: `cv2.INPAINT_TELEA`,
- radius: 3,
- model name recorded in metadata: `opencv_telea`.

A single fixed radius is used for all paintings and mask types. This avoids per-image tuning and keeps the baseline deterministic, reproducible, and comparable across categories and damage conditions.

Zero-control cases are also passed through OpenCV Telea. Since these masks contain no damaged pixels, the restored output is expected to remain identical to the clean/damaged input. This acts as a sanity check for the restoration pipeline.

Validation checks confirmed that:

- all 250 OpenCV-restored images were generated,
- all restored images are RGB PNG files at 768 × 768 pixels,
- zero-control restored images remained unchanged,
- non-zero mask cases produced outputs different from the damaged inputs,
- restoration metadata was saved for downstream metric evaluation.

The OpenCV Telea baseline is not expected to reconstruct large semantic structures or painting-specific stylistic content reliably. Its main purpose is to establish a classical baseline before evaluating learned models such as LaMa, Stable Diffusion Inpainting, and SDXL Inpainting.