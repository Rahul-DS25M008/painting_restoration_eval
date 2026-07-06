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

## Classical metric evaluation decision

For the OpenCV Telea baseline, classical full-reference image metrics are computed by comparing the clean reference image against both the damaged input and the restored output.

The evaluated comparisons are:

- clean image vs damaged image,
- clean image vs OpenCV-restored image.

The metrics are:

- MSE,
- MAE,
- PSNR,
- SSIM.

The purpose is to measure not only the restoration output, but also the amount of improvement over the synthetic damaged input. For error-based metrics such as MSE and MAE, lower values are better. For PSNR and SSIM, higher values are better.

The evaluation is performed across multiple regions:

- full image,
- painting content region,
- masked region,
- mask bounding-box crop.

The full-image region is retained for completeness, but it can hide restoration failures because most pixels are unchanged. The painting content region excludes preprocessing padding and better reflects the actual artwork. The masked region directly evaluates the artificially damaged target area and is therefore the most important region for MSE, MAE, and PSNR. The mask bounding-box crop preserves local spatial structure around the damaged region and is used for SSIM-style local structural evaluation.

SSIM is not computed directly on sparse masked pixels because SSIM assumes spatial image structure. Computing SSIM over isolated masked pixels would produce misleading precision. Instead, SSIM is computed for full-image, content-region, and mask bounding-box crop evaluations.

The OpenCV Telea baseline showed positive masked-region MSE improvement for all non-zero mask cases. This means that the restored outputs were numerically closer to the clean images than the white-filled damaged inputs. However, this does not imply historically correct or semantically faithful restoration. Classical pixel-level metrics are treated as one component of the evaluation framework, not as final evidence of restoration quality.

## Difference-map diagnostic evaluation decision

Difference maps are generated to complement scalar metric evaluation.

For each OpenCV restoration case, the project computes:

- clean vs damaged absolute error,
- clean vs restored absolute error,
- signed improvement after restoration.

The absolute error maps use mean absolute RGB error per pixel. The signed improvement map is computed as:

`damaged_error - restored_error`

Positive values indicate pixels where restoration reduced error compared with the damaged input. Negative values indicate pixels where the restored output is farther from the clean reference than the damaged input.

Difference maps are generated both for selected diagnostic cases and for all 250 OpenCV restoration cases. The selected cases include the strongest masked-region MSE improvements, weakest masked-region MSE improvements, and one mixed-damage case per painting category. This supports qualitative inspection before full-batch figure generation.

The purpose of these maps is not to replace scalar metrics, but to show the spatial distribution of error and improvement. This is important because scalar metrics can show that a restoration improved numerically without revealing whether the result is blurry, structurally incorrect, or visually plausible.

The OpenCV error maps confirmed that strong pixel-error improvement often corresponds to removal of the white damaged region, while residual error may remain in fine details, object boundaries, facial regions, or structured compositions.

## LPIPS perceptual metric evaluation decision

LPIPS is computed as a perceptual full-reference metric for the OpenCV Telea baseline.

The evaluated comparisons are:

- clean image vs damaged image,
- clean image vs OpenCV-restored image.

LPIPS is evaluated on image-like spatial regions only:

- full image,
- painting content region,
- mask bounding-box crop.

Sparse masked pixels are not used directly for LPIPS because LPIPS expects spatial image inputs and learned feature activations, not unordered pixel sets. The mask bounding-box crop is therefore used as the local perceptual region around the damaged area.

For LPIPS, lower values indicate higher perceptual similarity. Improvement is computed as:

`lpips_improvement = damaged_lpips - restored_lpips`

A positive value means that the restored image is perceptually closer to the clean reference than the damaged input.

LPIPS is included because classical metrics such as MSE, MAE, PSNR, and SSIM do not fully capture perceptual similarity. In this project, LPIPS is not treated as a final truth measure. Instead, it is one part of a multi-metric evaluation framework. Cases where LPIPS and pixel-level metrics disagree are especially useful because they reveal how different metric families emphasize different aspects of restoration quality.

## CLIP and DINOv2 feature-space similarity decision

CLIP and DINOv2 are used as pretrained feature-space diagnostics for the OpenCV Telea baseline.

The evaluated comparisons are:

- clean image vs damaged image,
- clean image vs restored image.

Feature similarity is computed using cosine similarity between image embeddings. Higher similarity indicates that two image regions are closer in the corresponding pretrained feature space.

Implementation note: CLIP was loaded using `use_safetensors=True` to avoid PyTorch `.bin` loading with Torch 2.5.1.

The improvement definition is:

`similarity_improvement = restored_similarity - damaged_similarity`

A positive value means that the restored output is closer to the clean reference than the damaged input in that feature space.

Feature similarity is evaluated on image-like spatial regions only:

- full image,
- painting content region,
- mask bounding-box crop.

Sparse masked pixels are not evaluated directly with CLIP or DINOv2 because these models expect spatial image inputs rather than unordered pixel sets.

### Feature-space interpretation note

The OpenCV Telea feature-similarity results show that CLIP and DINOv2 should be interpreted as diagnostic representation spaces rather than as definitive restoration-quality measures.

Large-loss mask-bounding-box crops showed weak CLIP improvement and negative average DINOv2 improvement. This suggests that OpenCV can reduce visible white damage while producing interpolated local structures that remain far from the clean reference in a self-supervised visual feature space.

This finding is important because it separates visible damage removal from faithful restoration. A restoration can look less damaged while still failing to recover the original visual structure. Therefore, feature-space metrics are used alongside classical metrics, LPIPS, and visual diagnostics rather than replacing them.

CLIP and DINOv2 are included because they represent different pretrained visual feature spaces. CLIP is trained with image-text contrastive supervision, while DINOv2 is a self-supervised visual representation model. In this project, both are used as diagnostic signals, not as final truth measures of restoration quality.

Cases where CLIP, DINOv2, LPIPS, and classical pixel metrics disagree are especially important. These disagreements show that restoration quality depends on multiple dimensions, including pixel accuracy, perceptual similarity, feature-space similarity, and visual plausibility.

## OpenCV Telea baseline report generation

An interim OpenCV Telea baseline report was generated after completing the 50-painting evaluation pipeline.

The report consolidates:

- dataset and restoration-case overview,
- mask-type summaries,
- painting-category summaries,
- classical masked-region metrics,
- LPIPS mask-bounding-box metrics,
- CLIP and DINOv2 mask-bounding-box feature similarities,
- metric correlation analysis,
- selected diagnostic cases,
- diagnostic error-map figures.

The report is intended as a baseline interpretation artifact, not as the final thesis result. It summarizes how the deterministic OpenCV Telea baseline behaves before adding pretrained and generative inpainting models.

The selected diagnostic cases are not intended to provide equal coverage across all categories. They are selected to expose strong metric improvements, weak metric improvements, feature-space disagreement, and representative category examples. The full CSV outputs remain the complete quantitative record.

For portability, the report currently embeds the selected diagnostic figures directly into the HTML file. This is acceptable because only selected cases are included. A fully linked-image report may be preferable later if larger report variants are generated.

The main baseline conclusion is that OpenCV Telea reliably improves over white-filled synthetic damage for local and scratch-like masks, but remains limited for large missing regions and cases requiring structural or semantic reconstruction. Metric disagreement between MSE, LPIPS, CLIP, DINOv2, and visual error maps is treated as a useful diagnostic signal rather than an error.

## LaMa implementation planning decision

After completing the OpenCV Telea baseline evaluation and report, LaMa is selected as the next model to add to the 50-painting controlled subset.

LaMa is used as the first pretrained open inpainting baseline. Unlike OpenCV Telea, LaMa has learned image priors and is designed for large-mask inpainting. This makes it a useful next comparison point for evaluating whether pretrained inpainting improves restoration behavior on larger and more complex damage masks.

The LaMa method source is the original LaMa paper and official project. For practical execution in this repository, the planned runtime implementation is the IOPaint command-line interface using `model=lama`.

The reason for using IOPaint is practical batch integration. The existing project already has standardized damaged images and binary masks for 250 restoration cases. IOPaint provides a command-line workflow that can process image and mask folders, which can be integrated through temporary staging folders.

The planned staging strategy is:

- copy damaged images into a temporary LaMa input folder,
- copy corresponding binary masks into a temporary LaMa mask folder,
- use matching filenames in both folders,
- run IOPaint LaMa on the staged batch,
- collect outputs into `data/processed/restored/lama/`,
- write restoration metadata to `data/processed/metadata/metadata_restored_lama.csv`.

This staging approach avoids changing the permanent project filenames to satisfy an external tool’s filename-matching convention.

LaMa outputs will be evaluated using the same metric families as OpenCV Telea:

- classical full-reference metrics,
- difference/error maps,
- LPIPS,
- CLIP and DINOv2 feature-space similarity,
- later model-comparison reports.

LaMa is not treated as a ground-truth restoration model. It is a pretrained inpainting baseline whose behavior must be evaluated against the known clean references under controlled synthetic damage. Particular attention will be paid to whether LaMa improves large-loss cases without introducing visually plausible but incorrect structures.

## LaMa restoration generation

LaMa was added as the first pretrained open inpainting baseline after the OpenCV Telea baseline.

The LaMa method source is the original LaMa paper and official project. For practical execution in this repository, LaMa was run through the IOPaint command-line runtime using `model=lama`. The CLI call is wrapped inside `src/restoration_eval/restoration_lama.py`, so the notebook still follows the same project structure as the OpenCV restoration stage.

The LaMa restoration notebook is:

`notebooks/11_lama_restoration_cleaned.ipynb`

The LaMa module is:

`src/restoration_eval/restoration_lama.py`

The module handles:

- staging damaged images and masks into temporary folders,
- matching image and mask filenames for IOPaint batch execution,
- running IOPaint LaMa through `subprocess`,
- forcing UTF-8 subprocess output to avoid Windows console/Rich progress encoding failures,
- collecting and renaming restored outputs into the project directory,
- copying zero-control cases directly without model inference,
- validating restored image existence, size, and basic behavior,
- writing restoration metadata.

A one-painting test was run first before the full batch. This test used one painting with all five mask types and confirmed that the module-level LaMa pipeline worked before scaling to the full controlled subset.

The full LaMa restoration run produced 250 restoration cases:

- 200 non-zero damage cases processed through LaMa model inference,
- 50 zero-control cases copied directly without model inference.

Zero-control cases were copied directly to preserve the no-damage control condition exactly. Although a manual IOPaint zero-mask test showed no pixel difference, the direct-copy strategy avoids depending on external runtime behavior for control cases.

The final LaMa outputs are:

- restored images: `data/processed/restored/lama/`,
- metadata: `data/processed/metadata/metadata_restored_lama.csv`.

The notebook also created selected visual inspection figures before formal metric evaluation:

- figures: `outputs/figures/lama_restoration_selected_cases/`,
- manifest: `outputs/metrics/lama_selected_visual_inspection_manifest_50.csv`.

The selected visual inspection set includes zero-control, category-representative large-loss cases, mixed-damage stress cases for abstraction/surrealism and high-texture paintings, and local-damage sanity cases. These visual checks are diagnostic only and are not treated as final quality rankings.

The next stage is to evaluate LaMa outputs using the same metric families already applied to OpenCV Telea:

- classical full-reference metrics,
- difference/error maps,
- LPIPS,
- CLIP and DINOv2 feature-space similarity,
- later model-comparison reporting.

## LaMa classical metric evaluation

Classical full-reference metrics were computed for the LaMa pretrained inpainting baseline using the same metric framework previously applied to OpenCV Telea.

The LaMa classical metrics notebook is:

`notebooks/12_metrics_classical_lama_cleaned.ipynb`

The reused metric module is:

`src/restoration_eval/metrics_classical.py`

The module was updated to include progress output during metric computation. This does not change metric definitions or output structure; it only makes long 250-case runs easier to monitor.

The LaMa metric notebook first loads:

`data/processed/metadata/metadata_restored_lama.csv`

Because LaMa restoration metadata does not permanently store painting category and content-region coordinates, the notebook enriches it from:

`data/processed/metadata/metadata_processed_clean.csv`

This enrichment step attaches:

- `category`,
- `content_x_min`,
- `content_y_min`,
- `content_x_max`,
- `content_y_max`.

The enriched metadata is then used for all metric computation. This keeps LaMa metric evaluation compatible with the existing classical metric module, which expects content-region coordinates to be present.

The computed metrics are:

- MSE,
- MAE,
- PSNR,
- SSIM.

The evaluation regions match the OpenCV Telea baseline:

- full image,
- content region,
- masked region,
- mask bounding-box crop.

The final LaMa classical metric output contains 900 rows:

- 250 full-image rows,
- 250 content-region rows,
- 200 masked-region rows,
- 200 mask-bounding-box crop rows.

Zero-control cases are included for full-image and content-region checks, but are excluded from masked-region and mask-bounding-box crop rows because they contain no damaged pixels.

The main output file is:

`outputs/metrics/classical_metrics_lama_50.csv`

Additional summary files were generated by:

- mask type,
- painting category,
- evaluation region,
- evaluation region and mask type,
- masked-region mask type.

The notebook also exports the strongest and weakest LaMa cases by absolute masked-region MSE improvement:

- `outputs/metrics/lama_strongest_masked_region_cases_50.csv`,
- `outputs/metrics/lama_weakest_masked_region_cases_50.csv`.

Metric-driven visual case figures were also generated and saved to:

`outputs/figures/lama_classical_metric_cases/`

Their manifest was saved to:

`outputs/metrics/lama_classical_metric_visual_cases_manifest_50.csv`.

These visual examples are diagnostic and tied to classical metric behavior. They are not final quality rankings. A large masked-region MSE improvement means the restored pixels are numerically closer to the clean reference, but it does not by itself prove perceptual, semantic, or historically faithful restoration quality.

This stage prepares the LaMa classical metric baseline for later direct comparison against OpenCV Telea and for later perceptual/feature-space evaluation.

## LaMa difference and error-map diagnostics

LaMa difference/error-map diagnostics were generated for the controlled 50-painting subset after LaMa classical metric computation.

Notebook:

`notebooks/13_difference_maps_lama_cleaned.ipynb`

The notebook reuses the shared error-map utility module:

`src/restoration_eval/error_maps.py`

The module generates diagnostic figures showing:

- clean reference image,
- damage mask,
- damaged input,
- restored output,
- clean-vs-damaged absolute error,
- clean-vs-restored absolute error,
- signed restoration improvement,
- masked signed restoration improvement.

The error-map module was updated so that the restored-image panel title is model-aware rather than OpenCV-specific. This allows the same diagnostic figure function to be reused for LaMa and later restoration models.

The LaMa metadata was enriched with painting category and title from:

`data/processed/metadata/metadata_processed_clean.csv`

This ensures that generated manifests and diagnostic displays preserve painting-category information.

Two sets of LaMa error-map outputs were generated:

1. selected diagnostic cases,
2. all 250 LaMa restoration cases.

The selected diagnostic set includes:

- strongest masked-region MSE improvement cases,
- weakest masked-region MSE improvement cases,
- representative mixed-damage cases across painting categories,
- one zero-control sanity case.

The all-case set includes one diagnostic figure for every LaMa restoration case.

Main outputs:

- `outputs/figures/error_maps/lama/selected_cases/`
- `outputs/figures/error_maps/lama/all_cases/`
- `outputs/metrics/error_map_manifest_selected_lama_50.csv`
- `outputs/metrics/error_map_manifest_all_lama_50.csv`
- `outputs/metrics/error_map_summary_selected_lama_50.csv`
- `outputs/metrics/error_map_summary_all_lama_50.csv`

The all-case manifest contains 250 rows, with 50 cases per mask type and 50 cases per painting category. All generated rows completed with status `ok`.

These diagnostics complement the numerical classical metrics by showing where restoration changes reduce or increase spatial error. They remain diagnostic visual evidence, not standalone proof of restoration quality.

## LaMa LPIPS perceptual metric evaluation

LaMa LPIPS perceptual-distance metrics were computed for the controlled 50-painting subset.

Notebook:

`notebooks/14_lpips_metrics_lama_cleaned.ipynb`

Metric module:

`src/restoration_eval/metrics_lpips.py`

LPIPS was computed between:

- clean reference and damaged input,
- clean reference and LaMa restored output.

The evaluated regions are:

- full image,
- content region,
- mask bounding-box crop.

Sparse masked-region LPIPS was intentionally not computed because LPIPS expects image-like spatial regions rather than unordered masked pixels.

The final LaMa LPIPS output contains 700 rows:

- 250 full-image rows,
- 250 content-region rows,
- 200 mask-bounding-box crop rows.

Zero-control cases are included for full-image and content-region LPIPS, but do not produce mask-bounding-box crop rows because they contain no damaged mask pixels.

Main output:

`outputs/metrics/lpips_metrics_lama_50.csv`

Additional summary files were generated by:

- mask type,
- painting category,
- evaluation region,
- evaluation region and mask type,
- painting category and evaluation region.

The notebook also exports strongest and weakest LaMa cases by LPIPS improvement over the damaged input:

- `outputs/metrics/lama_strongest_lpips_cases_50.csv`
- `outputs/metrics/lama_weakest_lpips_cases_50.csv`

LPIPS improvement is computed as damaged LPIPS minus restored LPIPS. Positive improvement therefore means that the restored output is perceptually closer to the clean reference than the damaged input.

These results add a perceptual similarity layer to the LaMa evaluation and prepare LaMa for later comparison with OpenCV Telea and future generative inpainting baselines.

## LaMa CLIP and DINOv2 feature-space similarity evaluation

LaMa feature-space similarity metrics were computed for the controlled 50-painting subset.

Notebook:

`notebooks/15_feature_similarity_lama_cleaned.ipynb`

Metric module:

`src/restoration_eval/metrics_feature_similarity.py`

Feature-space similarity was computed between:

- clean reference and damaged input,
- clean reference and LaMa restored output.

The evaluated feature models are:

- CLIP: `openai/clip-vit-base-patch32`,
- DINOv2: `dinov2_vits14`.

The evaluated regions are:

- full image,
- content region,
- mask bounding-box crop.

Sparse masked-region feature similarity was intentionally not computed because CLIP and DINOv2 expect image-like spatial regions rather than unordered masked pixels.

The final LaMa feature-similarity output contains 700 rows:

- 250 full-image rows,
- 250 content-region rows,
- 200 mask-bounding-box crop rows.

Zero-control cases are included for full-image and content-region feature similarity, but do not produce mask-bounding-box crop rows because they contain no damaged mask pixels.

Main output:

`outputs/metrics/feature_similarity_lama_50.csv`

Additional summary files were generated by:

- mask type,
- painting category,
- evaluation region,
- evaluation region and mask type,
- painting category and evaluation region.

The notebook also exports strongest and weakest LaMa cases by feature-space similarity improvement:

- `outputs/metrics/lama_strongest_dinov2_feature_cases_50.csv`
- `outputs/metrics/lama_weakest_dinov2_feature_cases_50.csv`
- `outputs/metrics/lama_strongest_clip_feature_cases_50.csv`
- `outputs/metrics/lama_weakest_clip_feature_cases_50.csv`

Feature-similarity improvement is computed as restored similarity minus damaged similarity. Positive improvement therefore means that the restored output is closer to the clean reference in the selected feature space.

These results complete the LaMa feature-space evaluation layer and prepare LaMa for later direct comparison with OpenCV Telea and future generative inpainting baselines.

## LaMa standalone baseline report

A standalone LaMa baseline report was generated after completing the LaMa restoration, classical metric, error-map, LPIPS, and CLIP/DINOv2 feature-similarity stages.

Notebook:

`notebooks/16_generate_report_lama_cleaned.ipynb`

Main report output:

`outputs/reports/lama_baseline_report_50.html`

Additional report outputs:

- `outputs/metrics/lama_report_dataframe_50.csv`
- `outputs/metrics/lama_report_selected_cases_50.csv`

The report consolidates the LaMa evaluation stack for the controlled 50-painting subset, including:

- LaMa restoration metadata,
- masked-region classical metrics,
- mask-bounding-box LPIPS metrics,
- mask-bounding-box CLIP and DINOv2 feature-space metrics,
- selected diagnostic error-map figures.

The report focuses on the 200 non-zero damage cases. Zero-control cases remain part of the metric validation workflow, but are excluded from the main report dataframe because they contain no damaged region.

The report uses embedded images so that the HTML file can be opened independently without relying on relative image paths. This makes the report easier to inspect and share as a standalone artifact.

The LaMa report is model-specific and uses LaMa-specific wording rather than reusing the OpenCV report text directly. This avoids conflating the deterministic OpenCV Telea baseline with the learned LaMa inpainting baseline.

This stage completes the standalone LaMa baseline evaluation and prepares the project for direct OpenCV Telea versus LaMa comparison.

## OpenCV Telea versus LaMa comparison

A direct OpenCV Telea versus LaMa comparison was generated after both baselines had completed the same evaluation stack.

Notebook:

`notebooks/17_compare_opencv_lama_cleaned.ipynb`

Main report output:

`outputs/reports/opencv_vs_lama_comparison_report_50.html`

Main comparison outputs:

- `outputs/metrics/model_pairing_opencv_lama_50.csv`
- `outputs/metrics/comparison_classical_opencv_lama_50.csv`
- `outputs/metrics/comparison_lpips_opencv_lama_50.csv`
- `outputs/metrics/comparison_feature_similarity_opencv_lama_50.csv`
- `outputs/metrics/comparison_unified_opencv_lama_50.csv`
- `outputs/metrics/comparison_summary_by_mask_type_opencv_lama_50.csv`
- `outputs/metrics/comparison_summary_by_category_opencv_lama_50.csv`
- `outputs/metrics/comparison_win_rates_opencv_lama_50.csv`
- `outputs/metrics/comparison_metric_disagreement_cases_opencv_lama_50.csv`
- `outputs/metrics/comparison_visual_cases_opencv_lama_50.csv`

Visual comparison figures:

`outputs/figures/model_comparison/opencv_vs_lama/`

The comparison is case-paired using:

- `painting_id`,
- `mask_id`,
- `mask_type`.

This ensures that OpenCV Telea and LaMa are compared on the same paintings, synthetic masks, damaged inputs, and clean references.

The unified local comparison table contains 200 non-zero damage cases. It combines:

- masked-region classical metrics,
- mask-bounding-box LPIPS metrics,
- mask-bounding-box CLIP and DINOv2 feature-space metrics.

For each case, LaMa-minus-OpenCV deltas were computed for the main improvement metrics. Winner columns were added for:

- MSE improvement,
- LPIPS improvement,
- CLIP feature-similarity improvement,
- DINOv2 feature-similarity improvement.

A compact overall metric vote was also added. This vote is used only as a diagnostic summary and is not interpreted as a conservation-level quality judgment.

Metric disagreement cases were explicitly exported. These include cases where one model wins pixel-level or perceptual metrics but loses feature-space similarity. This supports the central evaluation-framework argument that restoration behavior cannot be reliably summarized by a single scalar metric family.

The comparison report uses embedded visual figures so that it can be opened as a standalone HTML artifact.

## Stable Diffusion Inpainting restoration generation

Stable Diffusion Inpainting restoration outputs were generated for the controlled 50-painting subset.

Notebook:

`notebooks/18_stable_diffusion_restoration_cleaned.ipynb`

Module:

`src/restoration_eval/restoration_stable_diffusion.py`

Model:

`runwayml/stable-diffusion-inpainting`

Internal model name:

`stable_diffusion_inpainting`

Main restoration output directory:

`data/processed/restored/stable_diffusion_inpainting/`

Main restoration metadata output:

`data/processed/metadata/metadata_restored_stable_diffusion.csv`

The Stable Diffusion baseline was added as the first diffusion-based generative inpainting model after the deterministic OpenCV Telea baseline and the learned LaMa baseline.

A fixed prompt and fixed negative prompt were used for all paintings to reduce prompt-engineering bias.

Prompt:

`restore the missing damaged area of the painting, preserve the original style, colors, brushwork, composition, and surrounding visual context`

Negative prompt:

`modern objects, text, watermark, signature, frame, border, people added, face changed, extra objects, oversharpened, cartoon, digital art, photorealistic, unrealistic texture`

Inference settings:

- seed: `2026`
- inference steps: `30`
- guidance scale: `7.5`
- inference size: `512 × 512`
- device: CUDA GPU where available

The model inference resolution was set to 512 × 512 for memory stability. Final restored outputs were resized back to the processed image size so that downstream metrics remain comparable with OpenCV Telea and LaMa.

The final restoration metadata contains 250 rows:

- 200 non-zero damage cases processed through Stable Diffusion Inpainting,
- 50 zero-control cases copied directly from the damaged input.

Zero-control cases were not passed through the diffusion model because they contain no damaged region. This matches the policy used for LaMa and avoids introducing unnecessary generative changes.

Additional outputs:

- `outputs/metrics/stable_diffusion_restoration_overview_summary_50.csv`
- `outputs/metrics/stable_diffusion_restoration_by_mask_type_summary_50.csv`
- `outputs/metrics/stable_diffusion_restoration_by_inference_mode_summary_50.csv`
- `outputs/metrics/stable_diffusion_restoration_validation_summary_50.csv`
- `outputs/metrics/stable_diffusion_selected_visual_inspection_manifest_50.csv`
- `outputs/figures/stable_diffusion_restoration_selected_cases/`

The restored outputs were validated for file existence, expected image size, zero-control identity, and non-zero change from damaged input.

This stage prepares Stable Diffusion for the same metric stack already applied to OpenCV Telea and LaMa.

## Stable Diffusion classical metric evaluation

Classical image restoration metrics were computed for the Stable Diffusion Inpainting baseline on the controlled 50-painting subset.

Notebook:

`notebooks/19_metrics_classical_stable_diffusion_cleaned.ipynb`

Input restoration metadata:

`data/processed/metadata/metadata_restored_stable_diffusion.csv`

Main metric output:

`outputs/metrics/classical_metrics_stable_diffusion_50.csv`

The notebook computes classical metrics between:

- the clean reference and damaged input,
- the clean reference and Stable Diffusion restored output.

The same evaluation regions used for OpenCV Telea and LaMa were reused:

- `full_image`,
- `content_region`,
- `masked_region`,
- `mask_bbox_crop`.

The final output contains 900 metric rows:

- 250 full-image rows,
- 250 content-region rows,
- 200 masked-region rows,
- 200 mask-bounding-box crop rows.

Non-zero damage cases contribute four evaluation regions per case. Zero-control cases contribute only full-image and content-region rows because they contain no damaged pixels.

The notebook also generated summary tables by mask type, category, evaluation region, and evaluation-region/mask-type combination.

Additional outputs:

- `outputs/metrics/classical_metrics_summary_by_mask_type_stable_diffusion_50.csv`
- `outputs/metrics/classical_metrics_summary_by_category_stable_diffusion_50.csv`
- `outputs/metrics/classical_metrics_summary_by_region_stable_diffusion_50.csv`
- `outputs/metrics/classical_metrics_summary_by_region_mask_type_stable_diffusion_50.csv`
- `outputs/metrics/classical_metrics_masked_region_summary_stable_diffusion_50.csv`
- `outputs/metrics/stable_diffusion_strongest_masked_region_cases_50.csv`
- `outputs/metrics/stable_diffusion_weakest_masked_region_cases_50.csv`
- `outputs/metrics/stable_diffusion_classical_metric_visual_cases_manifest_50.csv`
- `outputs/figures/stable_diffusion_classical_metric_cases/`

This stage completes the pixel-level and structural classical metric layer for Stable Diffusion and prepares the model for spatial difference/error-map analysis.

## Stable Diffusion difference and error-map diagnostics

Spatial difference/error-map diagnostics were generated for the Stable Diffusion Inpainting baseline on the controlled 50-painting subset.

Notebook:

`notebooks/20_difference_maps_stable_diffusion_cleaned.ipynb`

Inputs:

- `data/processed/metadata/metadata_restored_stable_diffusion.csv`
- `outputs/metrics/classical_metrics_stable_diffusion_50.csv`

Main outputs:

- `outputs/metrics/error_map_manifest_stable_diffusion_50.csv`
- `outputs/metrics/error_map_summary_by_mask_type_stable_diffusion_50.csv`
- `outputs/metrics/error_map_summary_by_category_stable_diffusion_50.csv`
- `outputs/metrics/stable_diffusion_error_map_visual_cases_50.csv`
- `outputs/figures/error_maps/stable_diffusion_inpainting/`

The generated figures compare:

- clean reference,
- damage mask,
- damaged input,
- Stable Diffusion restored output,
- clean-vs-damaged absolute error,
- clean-vs-restored absolute error,
- signed improvement map,
- masked signed improvement map.

Positive signed improvement indicates that the restored output is closer to the clean reference than the damaged input. Negative signed improvement indicates that the restored output is farther from the clean reference than the damaged input.

A fixed diagnostic case-selection policy was used to avoid manual cherry-picking. Selected cases include:

- best cases by masked-region MSE improvement,
- worst cases by masked-region MSE improvement,
- median representative cases,
- classical metric-disagreement cases,
- category/mask representative cases.

This stage provides spatial evidence for where Stable Diffusion improves damage regions, where it fails, and where it may introduce new visual errors outside or around the mask.

## Stable Diffusion LPIPS perceptual evaluation

LPIPS perceptual-distance metrics were computed for the Stable Diffusion Inpainting baseline on the controlled 50-painting subset.

Notebook:

`notebooks/21_lpips_metrics_stable_diffusion_cleaned.ipynb`

Input restoration metadata:

`data/processed/metadata/metadata_restored_stable_diffusion.csv`

Main metric output:

`outputs/metrics/lpips_metrics_stable_diffusion_50.csv`

LPIPS was computed between:

- the clean reference and damaged input,
- the clean reference and Stable Diffusion restored output.

Lower LPIPS indicates that an image is perceptually closer to the clean reference. Positive LPIPS improvement means that the restored output is perceptually closer to the clean reference than the damaged input.

The evaluated regions were:

- `full_image`,
- `content_region`,
- `mask_bbox_crop`.

Sparse `masked_region` pixels were not used for LPIPS because LPIPS expects image-like spatial inputs rather than unordered masked pixels. The `mask_bbox_crop` region is therefore used as the local damage-region proxy.

The final LPIPS output contains 700 rows:

- 250 full-image rows,
- 250 content-region rows,
- 200 mask-bounding-box crop rows.

Additional outputs:

- `outputs/metrics/lpips_metrics_summary_by_mask_type_stable_diffusion_50.csv`
- `outputs/metrics/lpips_metrics_summary_by_category_stable_diffusion_50.csv`
- `outputs/metrics/lpips_metrics_summary_by_region_stable_diffusion_50.csv`
- `outputs/metrics/lpips_metrics_summary_by_region_mask_type_stable_diffusion_50.csv`
- `outputs/metrics/lpips_metrics_masked_region_summary_stable_diffusion_50.csv`
- `outputs/metrics/stable_diffusion_strongest_lpips_masked_region_cases_50.csv`
- `outputs/metrics/stable_diffusion_weakest_lpips_masked_region_cases_50.csv`
- `outputs/metrics/stable_diffusion_lpips_visual_cases_manifest_50.csv`
- `outputs/figures/stable_diffusion_lpips_metric_cases/`

The strongest and weakest local perceptual cases were ranked using `mask_bbox_crop` LPIPS improvement.

This stage completes the Stable Diffusion perceptual-distance metric layer and prepares the model for CLIP/DINOv2 feature-similarity evaluation.

## Stable Diffusion CLIP and DINOv2 feature-similarity evaluation

CLIP and DINOv2 feature-similarity metrics were computed for the Stable Diffusion Inpainting baseline on the controlled 50-painting subset.

Notebook:

`notebooks/22_feature_similarity_stable_diffusion_cleaned.ipynb`

Input restoration metadata:

`data/processed/metadata/metadata_restored_stable_diffusion.csv`

Main metric output:

`outputs/metrics/feature_similarity_stable_diffusion_50.csv`

Feature similarities were computed between:

- the clean reference and damaged input,
- the clean reference and Stable Diffusion restored output.

Higher cosine similarity means higher feature-space similarity to the clean reference. Positive improvement means that the restored output is closer to the clean reference in feature space than the damaged input.

The evaluated regions were:

- `full_image`,
- `content_region`,
- `mask_bbox_crop`.

Sparse `masked_region` pixels were not used because CLIP and DINOv2 expect image-like spatial inputs rather than unordered masked pixels. The `mask_bbox_crop` region is therefore used as the local damage-region proxy.

The final feature-similarity output contains 700 rows:

- 250 full-image rows,
- 250 content-region rows,
- 200 mask-bounding-box crop rows.

Additional outputs:

- `outputs/metrics/feature_similarity_summary_by_mask_type_stable_diffusion_50.csv`
- `outputs/metrics/feature_similarity_summary_by_category_stable_diffusion_50.csv`
- `outputs/metrics/feature_similarity_summary_by_region_stable_diffusion_50.csv`
- `outputs/metrics/feature_similarity_summary_by_region_mask_type_stable_diffusion_50.csv`
- `outputs/metrics/feature_similarity_mask_bbox_summary_stable_diffusion_50.csv`
- `outputs/metrics/stable_diffusion_strongest_dinov2_mask_bbox_cases_50.csv`
- `outputs/metrics/stable_diffusion_weakest_dinov2_mask_bbox_cases_50.csv`
- `outputs/metrics/stable_diffusion_strongest_clip_mask_bbox_cases_50.csv`
- `outputs/metrics/stable_diffusion_weakest_clip_mask_bbox_cases_50.csv`
- `outputs/metrics/stable_diffusion_feature_similarity_visual_cases_manifest_50.csv`
- `outputs/figures/stable_diffusion_feature_similarity_cases/`

The strongest and weakest local feature-similarity cases were ranked using `mask_bbox_crop` CLIP and DINOv2 improvement.

This stage completes the Stable Diffusion feature-space metric layer and prepares the model for its baseline report.

## Stable Diffusion baseline report

A consolidated baseline report was generated for the Stable Diffusion Inpainting model on the controlled 50-painting subset.

Notebook:

`notebooks/23_generate_report_stable_diffusion_cleaned.ipynb`

Main report output:

`outputs/reports/stable_diffusion_baseline_report_50.html`

Additional report outputs:

- `outputs/metrics/stable_diffusion_report_dataframe_50.csv`
- `outputs/metrics/stable_diffusion_report_selected_cases_50.csv`

The report combines:

- restoration metadata,
- classical metric summaries,
- LPIPS perceptual-distance summaries,
- CLIP/DINOv2 feature-similarity summaries,
- local metric outcome summaries,
- selected report cases,
- classical metric visual diagnostics,
- LPIPS visual diagnostics,
- feature-similarity visual diagnostics,
- spatial error-map diagnostics.

The local report dataframe contains 200 non-zero damage cases.

Local metric regions are handled as follows:

- classical metrics use the sparse `masked_region`,
- LPIPS uses `mask_bbox_crop`,
- CLIP/DINOv2 feature similarity uses `mask_bbox_crop`.

The report selected cases using a fixed diagnostic policy:

- highest number of improved metrics,
- lowest number of improved metrics,
- mixed metric outcomes,
- category/mask representatives.

The report explicitly notes that Stable Diffusion is a generative model and that visual plausibility is not interpreted as conservation or art-historical faithfulness.

This stage completes the Stable Diffusion model-level evaluation branch and prepares the project for multi-model comparison.

## Three-model comparison: OpenCV Telea vs LaMa vs Stable Diffusion

A three-model comparison was generated after completing the OpenCV Telea, LaMa, and Stable Diffusion Inpainting evaluation branches.

Notebook:

`notebooks/24_compare_opencv_lama_stable_diffusion_cleaned.ipynb`

Compared models:

- OpenCV Telea,
- LaMa,
- Stable Diffusion Inpainting.

Main report output:

`outputs/reports/opencv_lama_stable_diffusion_comparison_report_50.html`

Main metric outputs:

- `outputs/metrics/model_pairing_opencv_lama_stable_diffusion_50.csv`
- `outputs/metrics/comparison_classical_opencv_lama_stable_diffusion_50.csv`
- `outputs/metrics/comparison_lpips_opencv_lama_stable_diffusion_50.csv`
- `outputs/metrics/comparison_feature_similarity_opencv_lama_stable_diffusion_50.csv`
- `outputs/metrics/comparison_unified_opencv_lama_stable_diffusion_50.csv`
- `outputs/metrics/comparison_summary_by_mask_type_opencv_lama_stable_diffusion_50.csv`
- `outputs/metrics/comparison_summary_by_category_opencv_lama_stable_diffusion_50.csv`
- `outputs/metrics/comparison_win_rates_opencv_lama_stable_diffusion_50.csv`
- `outputs/metrics/comparison_metric_disagreement_cases_opencv_lama_stable_diffusion_50.csv`
- `outputs/metrics/comparison_visual_cases_opencv_lama_stable_diffusion_50.csv`

Main figure output directory:

`outputs/figures/model_comparison/opencv_lama_stable_diffusion/`

The comparison was paired by:

- `case_id`,
- `painting_id`,
- `mask_id`,
- `mask_type`.

The local comparison used 200 non-zero damage cases.

Metric-region policy:

- classical metrics use `masked_region`,
- LPIPS uses `mask_bbox_crop`,
- CLIP/DINOv2 feature similarity uses `mask_bbox_crop`.

Six local comparison metrics were used:

- MSE improvement,
- PSNR improvement,
- SSIM improvement,
- LPIPS improvement,
- CLIP similarity improvement,
- DINOv2 similarity improvement.

For each case and metric, the model with the highest improvement value was treated as the metric winner. Per-case majority votes were then calculated across the six metrics.

The comparison also identified metric-disagreement cases where different metric families preferred different models. These cases are treated as diagnostically important rather than as errors.

The report includes selected visual comparison cases using a fixed diagnostic policy:

- majority-vote cases by model,
- metric-disagreement cases,
- category/mask representatives,
- Stable Diffusion zero-metric-win cases where available.

Stable Diffusion results are interpreted cautiously because the model is generative. Metric wins do not imply conservation or art-historical correctness.

## SDXL feasibility audit

SDXL Inpainting was initially planned as a fourth restoration baseline after OpenCV Telea, LaMa, and Stable Diffusion Inpainting.

A local feasibility test was performed before launching a full controlled evaluation.

Notebook:

`notebooks/25_sdxl_restoration_cleaned.ipynb`

Planned SDXL model:

`diffusers/stable-diffusion-xl-1.0-inpainting-0.1`

Planned output location:

`data/processed/restored/sdxl_inpainting/`

Planned metadata output:

`data/processed/metadata/metadata_restored_sdxl.csv`

The local test environment used an NVIDIA GeForce RTX 3060 Laptop GPU with 6 GB VRAM.

The SDXL pipeline was technically loadable, but full local evaluation was not practical under the available hardware constraints.

Observed feasibility issues:

- running without CPU offload caused CUDA out-of-memory errors,
- 768 × 768 inference was too slow for practical evaluation,
- 512 × 512 inference with CPU offload was technically executable but slow,
- low-step settings did not produce usable restoration quality,
- stronger settings produced heavy hallucination and excessive runtime.

Two reduced smoke-test configurations were examined:

1. 6 inference steps, guidance scale 4.5, 512 × 512 inference, 768 × 768 output, CPU offload enabled.
2. 12 inference steps, guidance scale 6.0, strength 1.0, 512 × 512 inference, 768 × 768 output, CPU offload enabled.

The 6-step setting completed in approximately 4.6 minutes for one non-zero case, but the masked region was not meaningfully restored.

The 12-step setting completed in approximately 10 minutes for one non-zero case, but the result showed strong overgeneration and global visual alteration.

Given this runtime-quality trade-off, SDXL was excluded from the full local controlled evaluation.

This exclusion is treated as a computational feasibility limitation, not as a conclusion about SDXL restoration quality under adequate hardware.

The full controlled evaluation therefore remains focused on:

- OpenCV Telea,
- LaMa,
- Stable Diffusion Inpainting.

SDXL is reserved for future work or for rerunning on stronger GPU resources, preferably with at least 12–16 GB VRAM.

## Refined metric-region policy for final comparison

A refined metric-region policy was added after the initial three-model comparison revealed that sparse masked-region SSIM was not valid for local majority voting.

Notebook:

`notebooks/26_refined_metric_region_policy_cleaned.ipynb`

The initial three-model comparison used sparse `masked_region` values for MSE, PSNR, and SSIM. While this is appropriate for MSE and PSNR, it is not appropriate for SSIM because SSIM requires an image-like local neighborhood with spatial context.

SSIM was therefore retained, but moved from sparse `masked_region` to `mask_bbox_crop` for final local model comparison.

Final local metric-region policy:

- MSE improvement: `masked_region`
- PSNR improvement: `masked_region`
- SSIM improvement: `mask_bbox_crop`
- LPIPS improvement: `mask_bbox_crop`
- CLIP similarity improvement: `mask_bbox_crop`
- DINOv2 similarity improvement: `mask_bbox_crop`

This refinement rebuilds only the comparison-level outputs. Model-level metric files and model-level reports remain valid.

Main refined outputs:

- `outputs/metrics/comparison_unified_refined_opencv_lama_stable_diffusion_50.csv`
- `outputs/metrics/comparison_win_rates_refined_opencv_lama_stable_diffusion_50.csv`
- `outputs/metrics/comparison_summary_by_mask_type_refined_opencv_lama_stable_diffusion_50.csv`
- `outputs/metrics/comparison_summary_by_category_refined_opencv_lama_stable_diffusion_50.csv`
- `outputs/metrics/comparison_metric_disagreement_cases_refined_opencv_lama_stable_diffusion_50.csv`
- `outputs/metrics/comparison_old_vs_refined_metric_policy_50.csv`
- `outputs/metrics/comparison_visual_cases_refined_opencv_lama_stable_diffusion_50.csv`
- `outputs/reports/opencv_lama_stable_diffusion_refined_metric_comparison_report_50.html`

The refined comparison is the preferred comparison policy for the final controlled 50-painting report.

## Stable Diffusion multi-seed uncertainty analysis

Notebook:

`notebooks/27_diffusion_uncertainty_analysis_cleaned.ipynb`

A multi-seed uncertainty analysis was added for Stable Diffusion Inpainting.

The purpose was to evaluate whether the diffusion model produces stable restorations for the same damaged input when sampled repeatedly with different random seeds.

The analysis used a balanced diagnostic subset rather than the full non-zero benchmark:

- 5 painting categories,
- 2 paintings per category,
- 4 non-zero mask types per selected painting,
- 40 damaged cases.

For each selected case, Stable Diffusion Inpainting was run with four seeds:

- `2026`,
- `2027`,
- `2028`,
- `2029`.

This produced 160 generated restoration outputs.

The subset selection was based on the refined three-model comparison. For each painting category, one relatively stronger Stable Diffusion painting and one weaker or disagreement-prone Stable Diffusion painting were selected. All four non-zero masks were then included for each selected painting.

Uncertainty was measured using complementary indicators:

- image-space seed variation,
- masked-region seed standard deviation,
- mask-bounding-box seed variation,
- pairwise LPIPS distance between seed outputs,
- pairwise CLIP feature uncertainty distance,
- pairwise DINOv2 feature uncertainty distance,
- combined normalized uncertainty index.

The analysis was also linked back to the refined three-model comparison to evaluate uncertainty against reference-based Stable Diffusion metric performance.

The uncertainty-performance linkage produced four diagnostic cases:

- high uncertainty and low reference performance,
- high uncertainty and high reference performance,
- low uncertainty and low reference performance,
- low uncertainty and high reference performance.

The uncertainty analysis supports the thesis argument that a visually plausible diffusion restoration is not necessarily trustworthy. If repeated seeds produce different restorations for the same damaged region, then the model is sampling multiple plausible completions rather than providing a stable restoration estimate.

Main outputs:

- `outputs/metrics/stable_diffusion_uncertainty_subset_manifest_50.csv`
- `outputs/metrics/stable_diffusion_uncertainty_generations_50.csv`
- `outputs/metrics/stable_diffusion_uncertainty_image_summary_by_case_50.csv`
- `outputs/metrics/stable_diffusion_uncertainty_pairwise_lpips_50.csv`
- `outputs/metrics/stable_diffusion_uncertainty_pairwise_feature_similarity_50.csv`
- `outputs/metrics/stable_diffusion_uncertainty_combined_summary_by_case_50.csv`
- `outputs/metrics/stable_diffusion_uncertainty_vs_refined_performance_50.csv`
- `outputs/metrics/stable_diffusion_uncertainty_performance_quadrants_50.csv`
- `outputs/reports/stable_diffusion_uncertainty_report_50.html`

This notebook provides the main uncertainty component of the evaluation framework.

## Final controlled 50-painting evaluation report

Notebook:

`notebooks/28_final_controlled_50_evaluation_report_cleaned.ipynb`

A final consolidated report was created for the controlled 50-painting evaluation.

The notebook does not generate new restorations. It consolidates and validates outputs from the completed experimental pipeline:

- controlled dataset preparation,
- synthetic mask and damage generation,
- OpenCV Telea restoration,
- LaMa restoration,
- Stable Diffusion Inpainting restoration,
- SDXL feasibility audit,
- refined metric-region comparison,
- Stable Diffusion multi-seed uncertainty analysis.

The report uses the refined local metric-region policy:

- MSE improvement: `masked_region`,
- PSNR improvement: `masked_region`,
- SSIM improvement: `mask_bbox_crop`,
- LPIPS improvement: `mask_bbox_crop`,
- CLIP similarity improvement: `mask_bbox_crop`,
- DINOv2 similarity improvement: `mask_bbox_crop`.

The final comparison includes three fully evaluated models:

- OpenCV Telea,
- LaMa,
- Stable Diffusion Inpainting.

SDXL Inpainting is included only as a feasibility-audited model. It was excluded from full local evaluation because local 6GB VRAM and runtime constraints made full controlled evaluation impractical.

The final report also incorporates Stable Diffusion uncertainty analysis. This analysis evaluates whether the diffusion model produces stable restoration outputs across multiple random seeds.

Main final report:

`outputs/reports/final_controlled_50_evaluation_report.html`

Main final synthesis outputs:

- `outputs/metrics/final_controlled_50_dataset_summary.csv`
- `outputs/metrics/final_controlled_50_model_stack_summary.csv`
- `outputs/metrics/final_controlled_50_metric_policy_summary.csv`
- `outputs/metrics/final_controlled_50_key_results_summary.csv`
- `outputs/metrics/final_controlled_50_model_win_summary.csv`
- `outputs/metrics/final_controlled_50_uncertainty_summary.csv`
- `outputs/metrics/final_controlled_50_sdxl_feasibility_summary.csv`
- `outputs/metrics/final_controlled_50_visual_cases.csv`

Final interpretation:

The controlled evaluation supports a layered trustworthiness framework. Reference-based metrics are necessary but insufficient. Metric-region policy, visual inspection, model feasibility auditing, and generative uncertainty analysis are also needed.

The final thesis-level claim is:

> Visual plausibility is not the same as restoration trustworthiness.

<!-- NOTEBOOK_30_SUPERVISOR_PACKAGE -->

## Supervisor package preparation

Notebook:

`notebooks/30_supervisor_package_cleaned.ipynb`

A compact supervisor review package was generated after the final controlled 50-painting report and dashboard asset preparation.

Package directory:

`outputs/supervisor_package/`

The package includes:

- current project status,
- proposal-to-current-work alignment,
- research-question coverage,
- key results,
- methodology summary,
- limitations and deviations,
- supervisor questions,
- recommended next steps,
- selected visual figures,
- compact CSV/JSON summaries,
- references/copies of main reports.

The package maps the current work back to the remembered proposal research questions:

- RQ1: multi-metric trustworthiness evaluation,
- RQ2: pretrained model comparison across painting categories and damage types,
- RQ3: diffusion uncertainty from multiple restoration candidates.

Current interpretation:

- RQ1 is substantially answered by the multi-metric, region-aware evaluation framework.
- RQ2 is substantially answered for the controlled 50-painting subset.
- RQ3 is diagnostically answered by the balanced 40-case Stable Diffusion uncertainty subset, but scope should be confirmed with the supervisor.

Main supervisor clarification points:

- whether the 50-painting subset is sufficient,
- whether uncertainty should be expanded to all 200 non-zero cases,
- whether SDXL should remain feasibility-audited or be rerun on university compute,
- whether the refined metric-region policy is accepted,
- whether the Streamlit dashboard should be formalized as a supporting artifact.

## Candidate methodology extensions after supervisor review

The current framework includes classical metrics, perceptual metrics, feature-space metrics, visual diagnostics, metric-region refinement, model comparison, and Stable Diffusion uncertainty analysis.

Several possible extensions could strengthen the final thesis:

1. **Texture-aware evaluation**  
   Add local texture descriptors such as GLCM contrast, GLCM homogeneity, or Gabor-filter responses. This would directly support the painting-specific claim that restoration quality depends not only on pixel similarity but also on brushstroke and texture continuity.

2. **Uncertainty heatmaps**  
   Generate pixel-wise standard-deviation maps across Stable Diffusion seed outputs. These maps would make uncertainty spatially interpretable and help identify speculative restoration regions.

3. **Metric-policy ablation**  
   Treat the old-versus-refined metric-region policy comparison as a formal ablation study. This would strengthen the claim that evaluation design materially affects model ranking and trustworthiness conclusions.

4. **Metadata-driven analysis**  
   If metadata quality is sufficient, extend category-level analysis using artist, period, medium, or collection fields. Statistical testing should only be used where group sizes are meaningful.

5. **Semantic or iconographic checks**  
   Explore lightweight CLIP-based semantic consistency checks for restored regions. This should be treated carefully because semantic correctness in paintings is difficult to validate without art-historical ground truth.

6. **Per-painting reporting layer**  
   Generate standardized per-painting or per-case reports containing visual comparisons, metrics, uncertainty summaries, and trustworthiness notes.

These extensions should be prioritized with supervisor input. The strongest candidates for final methodology improvement are texture-aware metrics, uncertainty heatmaps, and metric-policy ablation.
