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

### Classical metric evaluation status

LaMa classical metric evaluation has been completed for the controlled 50-painting subset.

Notebook:

`notebooks/12_metrics_classical_lama_cleaned.ipynb`

Main metric output:

`outputs/metrics/classical_metrics_lama_50.csv`

The evaluation produced 900 metric rows using the same region structure as OpenCV Telea:

- 250 full-image rows,
- 250 content-region rows,
- 200 masked-region rows,
- 200 mask-bounding-box crop rows.

The LaMa restoration metadata was enriched with category and content-region coordinates from `metadata_processed_clean.csv` before metric computation. This was necessary because the LaMa restoration metadata focuses on restoration output paths and inference status rather than carrying all processed-image metadata fields.

The classical metric module was updated with progress printing for long 250-case metric runs. Metric definitions were not changed.

Additional outputs include summary CSVs by mask type, category, region, region-mask type, and masked-region mask type. Strongest and weakest LaMa cases by masked-region MSE improvement were also exported.

Metric-driven visual examples were generated and saved to:

`outputs/figures/lama_classical_metric_cases/`

Current interpretation: LaMa classical metrics are now available for later direct comparison against OpenCV Telea. These results should not be interpreted alone as proof of restoration quality, because classical pixel metrics do not fully capture perceptual plausibility, semantic correctness, or conservation faithfulness.

### Difference/error-map diagnostic status

LaMa difference/error-map diagnostics have been completed for the controlled 50-painting subset.

Notebook:

`notebooks/13_difference_maps_lama_cleaned.ipynb`

Main outputs:

- `outputs/figures/error_maps/lama/selected_cases/`
- `outputs/figures/error_maps/lama/all_cases/`
- `outputs/metrics/error_map_manifest_selected_lama_50.csv`
- `outputs/metrics/error_map_manifest_all_lama_50.csv`
- `outputs/metrics/error_map_summary_selected_lama_50.csv`
- `outputs/metrics/error_map_summary_all_lama_50.csv`

The selected diagnostic set contains 16 cases. These include strongest and weakest masked-region MSE improvement examples, representative mixed-damage examples across categories, and one zero-control sanity case.

The all-case LaMa error-map manifest contains 250 rows, one for each LaMa restoration case. All rows completed with status `ok`.

The shared error-map module was updated to make the restored-output panel title model-aware, so the same plotting function can now be reused for LaMa and later restoration models.

Current interpretation: LaMa now has spatial diagnostic outputs aligned with the OpenCV Telea baseline. These figures will support later model comparison and help identify where scalar metrics hide spatially localized restoration behavior.

### LPIPS perceptual metric status

LaMa LPIPS perceptual metric evaluation has been completed for the controlled 50-painting subset.

Notebook:

`notebooks/14_lpips_metrics_lama_cleaned.ipynb`

Main output:

`outputs/metrics/lpips_metrics_lama_50.csv`

The evaluation produced 700 LPIPS rows:

- 250 full-image rows,
- 250 content-region rows,
- 200 mask-bounding-box crop rows.

The evaluated LPIPS regions match the OpenCV Telea LPIPS setup, enabling later direct model comparison.

Additional outputs include summary CSVs by mask type, category, region, region-mask type, and category-region grouping. Strongest and weakest LaMa cases by mask-bounding-box LPIPS improvement were also exported.

Current interpretation: LaMa now has a perceptual similarity evaluation layer in addition to classical metrics and spatial error-map diagnostics. These LPIPS results will support later comparison against OpenCV Telea and future diffusion-based inpainting models.

### CLIP and DINOv2 feature-space similarity status

LaMa CLIP and DINOv2 feature-space similarity evaluation has been completed for the controlled 50-painting subset.

Notebook:

`notebooks/15_feature_similarity_lama_cleaned.ipynb`

Main output:

`outputs/metrics/feature_similarity_lama_50.csv`

The evaluation produced 700 feature-similarity rows:

- 250 full-image rows,
- 250 content-region rows,
- 200 mask-bounding-box crop rows.

The evaluated feature models are:

- CLIP: `openai/clip-vit-base-patch32`,
- DINOv2: `dinov2_vits14`.

The evaluated regions match the OpenCV Telea feature-similarity setup, enabling later direct model comparison.

Additional outputs include summary CSVs by mask type, category, region, region-mask type, and category-region grouping. Strongest and weakest LaMa cases were exported separately for DINOv2 and CLIP feature-similarity improvement.

Current interpretation: LaMa now has classical metrics, spatial error-map diagnostics, LPIPS perceptual metrics, and CLIP/DINOv2 feature-space metrics. This makes the LaMa evaluation stack nearly parallel with the completed OpenCV Telea baseline and prepares both models for direct comparison.

### Standalone report status

The standalone LaMa baseline report has been completed for the controlled 50-painting subset.

Notebook:

`notebooks/16_generate_report_lama_cleaned.ipynb`

Main report output:

`outputs/reports/lama_baseline_report_50.html`

Additional outputs:

- `outputs/metrics/lama_report_dataframe_50.csv`
- `outputs/metrics/lama_report_selected_cases_50.csv`

The report consolidates the completed LaMa evaluation stack:

- restoration outputs,
- classical metrics,
- difference/error-map diagnostics,
- LPIPS perceptual metrics,
- CLIP and DINOv2 feature-space metrics.

The report focuses on the 200 non-zero damage cases and excludes zero-control cases from the main report dataframe. Zero-control cases remain part of the validation workflow.

The HTML report uses embedded images so that diagnostic figures display correctly when the report is opened independently.

Current interpretation: LaMa now has a standalone baseline report parallel to the OpenCV Telea report. The next methodological step is direct OpenCV Telea versus LaMa comparison using the aligned metric outputs and diagnostic case selections.

### OpenCV Telea versus LaMa comparison status

The direct OpenCV Telea versus LaMa comparison has been completed for the controlled 50-painting subset.

Notebook:

`notebooks/17_compare_opencv_lama_cleaned.ipynb`

Main report:

`outputs/reports/opencv_vs_lama_comparison_report_50.html`

The comparison produced paired outputs for:

- restoration metadata alignment,
- classical metrics,
- LPIPS metrics,
- CLIP and DINOv2 feature-space metrics,
- unified local-region comparison,
- metric disagreement cases,
- selected visual comparison cases,
- standalone HTML comparison report.

The unified local comparison table contains 200 non-zero damage cases and compares:

- masked-region classical metrics,
- mask-bounding-box LPIPS metrics,
- mask-bounding-box CLIP/DINOv2 metrics.

The comparison explicitly tracks metric winners and disagreements. This allows the project to identify cases where OpenCV and LaMa differ not only in aggregate performance but also across metric families.

Current interpretation: the project now has its first direct cross-model comparison between a deterministic classical interpolation baseline and a learned pretrained inpainting baseline. This is the first major framework-level result and prepares the project for the next model-family extension: diffusion-based inpainting.

## Stable Diffusion Inpainting

Stable Diffusion Inpainting is useful because it is generative, text-conditioned, mask-aware, and seed-controllable. That makes it a strong candidate for uncertainty analysis, especially through multiple sampled restorations for the same damaged painting.

The main risk is hallucination. The model may create visually plausible content that does not match the original painting. This is especially important because the thesis uses synthetic masks, so the clean image is known ground truth. A beautiful but incorrect reconstruction is still an evaluation failure.

Decision: keep as a candidate for later uncertainty analysis, not the next immediate model.

### Stable Diffusion Inpainting restoration status

Stable Diffusion Inpainting restoration generation has been completed for the controlled 50-painting subset.

Notebook:

`notebooks/18_stable_diffusion_restoration_cleaned.ipynb`

Module:

`src/restoration_eval/restoration_stable_diffusion.py`

Model:

`runwayml/stable-diffusion-inpainting`

Internal model name:

`stable_diffusion_inpainting`

Main outputs:

- `data/processed/restored/stable_diffusion_inpainting/`
- `data/processed/metadata/metadata_restored_stable_diffusion.csv`
- `outputs/metrics/stable_diffusion_restoration_overview_summary_50.csv`
- `outputs/metrics/stable_diffusion_restoration_by_mask_type_summary_50.csv`
- `outputs/metrics/stable_diffusion_restoration_by_inference_mode_summary_50.csv`
- `outputs/metrics/stable_diffusion_restoration_validation_summary_50.csv`
- `outputs/metrics/stable_diffusion_selected_visual_inspection_manifest_50.csv`
- `outputs/figures/stable_diffusion_restoration_selected_cases/`

The restoration metadata contains 250 rows:

- 200 model-inference rows,
- 50 copied zero-control rows.

All restored outputs passed validation for:

- restored file existence,
- expected output size,
- zero-control identity against damaged input,
- non-zero output change from damaged input.

The Stable Diffusion baseline uses a fixed prompt and negative prompt for all paintings. This keeps the run reproducible and reduces prompt-engineering bias.

Current interpretation: the project now includes a third model family: diffusion-based generative inpainting. The next step is to apply the same metric stack used for OpenCV Telea and LaMa: classical metrics, difference/error maps, LPIPS, and CLIP/DINOv2 feature similarity.

### Stable Diffusion classical metric status

Classical metric evaluation has been completed for the Stable Diffusion Inpainting baseline.

Notebook:

`notebooks/19_metrics_classical_stable_diffusion_cleaned.ipynb`

Input:

`data/processed/metadata/metadata_restored_stable_diffusion.csv`

Main output:

`outputs/metrics/classical_metrics_stable_diffusion_50.csv`

The final classical metric output contains 900 rows:

- 250 full-image rows,
- 250 content-region rows,
- 200 masked-region rows,
- 200 mask-bounding-box crop rows.

Summary outputs:

- `outputs/metrics/classical_metrics_summary_by_mask_type_stable_diffusion_50.csv`
- `outputs/metrics/classical_metrics_summary_by_category_stable_diffusion_50.csv`
- `outputs/metrics/classical_metrics_summary_by_region_stable_diffusion_50.csv`
- `outputs/metrics/classical_metrics_summary_by_region_mask_type_stable_diffusion_50.csv`
- `outputs/metrics/classical_metrics_masked_region_summary_stable_diffusion_50.csv`

Diagnostic outputs:

- `outputs/metrics/stable_diffusion_strongest_masked_region_cases_50.csv`
- `outputs/metrics/stable_diffusion_weakest_masked_region_cases_50.csv`
- `outputs/metrics/stable_diffusion_classical_metric_visual_cases_manifest_50.csv`
- `outputs/figures/stable_diffusion_classical_metric_cases/`

Final gates confirmed:

- all expected metric files exist,
- the metric table contains 900 rows,
- all metric rows have status `ok`,
- all expected evaluation-region counts are present,
- mask-type/evaluation-region counts match the experiment design,
- summary and ranking files have expected row counts,
- selected visual figures exist.

Current interpretation: Stable Diffusion now has completed restoration generation and classical metric evaluation. The next step is Stable Diffusion difference/error maps.

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
