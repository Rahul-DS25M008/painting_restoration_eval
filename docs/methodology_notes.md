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