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