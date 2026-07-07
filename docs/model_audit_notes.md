# Model Audit Notes

This document records model-selection logic, audit concerns, current inclusion status, and interpretation boundaries for the painting-restoration evaluation framework.

It is intentionally concise.

- Literature justification belongs in `docs/literature_reference_log.md`.
- General methodology belongs in `docs/methodology_notes.md`.
- Output inventories belong in manifests, reports, or notebook outputs.
- This file focuses on model role, risks, domain gap, reproducibility, and current project decision.

---

## 1. Model-audit purpose

The thesis evaluates restoration candidates under controlled synthetic damage.

The project does not treat pretrained inpainting models as conservation-grade restoration systems. Each model is audited as a candidate method whose behavior must be measured across:

- painting category,
- damage type,
- metric family,
- local evaluation region,
- visual diagnostics,
- uncertainty where relevant.

The central audit concern is domain gap.

Most available inpainting models are trained on natural images, scene datasets, or broad web-scale image corpora, not on controlled painting-restoration data. This matters for:

- brushstroke texture,
- historical style,
- abstraction and surrealism,
- iconographic detail,
- conservation faithfulness,
- generative hallucination.

Core model-audit claim:

> A model can produce a visually plausible restoration while still failing reference fidelity, texture consistency, semantic stability, or uncertainty requirements.

---

## 2. Current model stack

| Model | Status | Role |
|---|---|---|
| OpenCV Telea | Fully evaluated | Classical deterministic baseline |
| LaMa | Fully evaluated | Pretrained learned inpainting baseline |
| Stable Diffusion Inpainting | Fully evaluated | Generative diffusion baseline |
| SDXL Inpainting | Feasibility-audited only | Higher-capacity diffusion candidate |
| DALL-E / OpenAI Image Editing | Excluded from core experiment | Optional closed commercial comparison |

Current fully evaluated local model stack:

- OpenCV Telea,
- LaMa,
- Stable Diffusion Inpainting.

SDXL is excluded from the full local comparison due hardware/runtime constraints, not because of a concluded quality failure.

---

## 3. OpenCV Telea audit

### Role

OpenCV Telea is the classical deterministic baseline.

It provides a simple, fast, reproducible non-learning reference point before evaluating learned or generative models.

### Strengths

- deterministic,
- fast,
- lightweight,
- transparent classical algorithm,
- no learned training-data bias,
- useful for thin scratches and small local damage,
- easy to reproduce across machines.

### Risks and limitations

- no semantic understanding,
- no painting-specific knowledge,
- no brushstroke or style model,
- weak on large missing regions,
- weak on structured content reconstruction,
- can interpolate locally without restoring meaningful structure.

### Project decision

OpenCV Telea remains the first baseline.

Policy:

- algorithm: `cv2.INPAINT_TELEA`,
- radius: `3`,
- no per-case tuning,
- zero-control cases retained as sanity checks.

### Interpretation boundary

OpenCV success means local numerical or visual improvement over white-filled damage. It does not imply historically correct restoration.

---

## 4. LaMa audit

### Role

LaMa is the first pretrained learned inpainting baseline.

It is included because it is designed for large-mask inpainting and can use broader image context than OpenCV Telea.

### Strengths

- open pretrained inpainting model,
- strong general inpainting baseline,
- better suited than OpenCV for larger masks,
- uses broader learned context,
- practical local execution through IOPaint,
- fully integrated into the controlled 50-painting pipeline.

### Risks and limitations

- trained for general image inpainting, not painting conservation,
- domain gap for historical paintings and painterly texture,
- may synthesize plausible but incorrect structures,
- may smooth or alter brushstroke-like details,
- output faithfulness depends on surrounding context and training priors.

### Implementation decision

Method source:

- LaMa paper and official method.

Runtime source:

- IOPaint CLI with `model=lama`.

Project wrapper:

- `src/restoration_eval/restoration_lama.py`.

Zero-control policy:

- copied directly rather than inferred through the runtime.

Reason:

- preserves the no-damage control exactly,
- avoids depending on external runtime behavior for empty masks.

### Current status

LaMa is fully evaluated for the controlled 50-painting subset.

Completed layers:

- restoration generation,
- classical metrics,
- difference/error maps,
- LPIPS,
- CLIP/DINOv2 feature similarity,
- standalone LaMa report,
- OpenCV-vs-LaMa comparison,
- three-model comparison,
- refined comparison,
- texture and brushstroke-proxy metrics.

### Interpretation boundary

LaMa’s strong reference-based performance makes it the strongest current baseline under the refined metric policy. It is still not conservation-specific and should not be described as producing historically correct restorations.

---

## 5. Stable Diffusion Inpainting audit

### Role

Stable Diffusion Inpainting is the first generative diffusion baseline.

It is included to test a prompt-conditioned generative restoration model and to support uncertainty analysis through repeated seed sampling.

### Strengths

- generative inpainting capability,
- mask-aware editing pipeline,
- prompt conditioning,
- seed-controllable outputs,
- useful for studying stochastic uncertainty,
- can generate visually plausible completions.

### Risks and limitations

- hallucination risk,
- may alter style, texture, or local content,
- may produce plausible but reference-inaccurate regions,
- prompt sensitivity,
- seed sensitivity,
- natural/web-scale training domain gap,
- weaker reference-based performance in the current 50-painting evaluation.

### Project model

Model:

`runwayml/stable-diffusion-inpainting`

Project model name:

`stable_diffusion_inpainting`

Baseline generation policy:

- fixed prompt,
- fixed negative prompt,
- fixed seed,
- fixed inference steps,
- fixed guidance scale,
- fixed inference size,
- zero-control cases copied directly.

This reduces prompt-engineering bias and keeps the model branch reproducible.

### Current status

Stable Diffusion Inpainting is fully evaluated for the controlled 50-painting subset.

Completed layers:

- restoration generation,
- classical metrics,
- difference/error maps,
- LPIPS,
- CLIP/DINOv2 feature similarity,
- standalone Stable Diffusion report,
- three-model comparison,
- refined comparison,
- multi-seed uncertainty subset,
- texture and brushstroke-proxy metrics.

### Uncertainty status

Stable Diffusion has an additional multi-seed uncertainty analysis.

Current uncertainty subset:

- 40 non-zero cases,
- 4 seeds per case,
- 160 generated outputs.

Purpose:

- measure output variability for identical damaged inputs,
- identify unstable generated restorations,
- link uncertainty to reference-based performance.

### Interpretation boundary

Stable Diffusion is useful precisely because it exposes the gap between visual plausibility and restoration trustworthiness.

A good-looking output is not automatically a faithful restoration. If multiple seeds generate different plausible completions, that instability is an audit signal.

---

## 6. SDXL Inpainting audit

### Role

SDXL Inpainting is a higher-capacity diffusion candidate.

It was considered as a possible fourth model after OpenCV Telea, LaMa, and Stable Diffusion Inpainting.

### Strengths

- stronger diffusion model family than older Stable Diffusion,
- potentially higher visual quality,
- relevant candidate for final thesis if stronger compute is available.

### Risks and limitations

- significantly higher VRAM and runtime requirements,
- local 6 GB GPU environment is insufficient for practical full evaluation,
- low-step runs produce poor restoration,
- stronger settings were too slow and showed overgeneration in local smoke tests,
- visual quality may still hide hallucination or reference mismatch.

### Feasibility decision

SDXL was feasibility-audited locally using:

`diffusers/stable-diffusion-xl-1.0-inpainting-0.1`

Local hardware:

- NVIDIA RTX 3060 Laptop GPU,
- 6 GB VRAM.

Outcome:

- model loading succeeded,
- no-offload inference caused CUDA out-of-memory,
- CPU offload made small tests possible,
- runtime-quality trade-off was not practical,
- full local evaluation was excluded.

### Project decision

SDXL is not part of the current fully evaluated model stack.

It remains future work or a remote-compute extension.

Minimum preferred compute for full SDXL evaluation:

- at least 12 GB VRAM,
- preferably 16 GB or more.

### Interpretation boundary

The SDXL result is a feasibility limitation. It must not be written as evidence that SDXL is worse than LaMa, OpenCV, or Stable Diffusion.

---

## 7. DALL-E / OpenAI Image Editing audit

### Role

DALL-E / OpenAI Image Editing was considered as an optional closed commercial comparison.

### Strengths

- strong image-editing capabilities,
- mask-guided editing,
- potentially useful as an external commercial comparison.

### Risks and limitations

- closed model,
- limited training-data transparency,
- weaker reproducibility,
- API/version behavior may change,
- prompt-guided editing may not guarantee strict restoration-region fidelity,
- less suitable for a core reproducible academic experiment.

### Project decision

DALL-E / OpenAI Image Editing is excluded from the core experiment.

It may be mentioned as optional future work, but it should not be part of the main reproducible evaluation framework.

---

## 8. Current model comparison interpretation

The refined comparison uses the final metric-region policy:

| Metric family | Region |
|---|---|
| MSE | `masked_region` |
| PSNR | `masked_region` |
| SSIM | `mask_bbox_crop` |
| LPIPS | `mask_bbox_crop` |
| CLIP | `mask_bbox_crop` |
| DINOv2 | `mask_bbox_crop` |
| Texture metrics | `mask_bbox_crop` |
| Brushstroke-proxy orientation metrics | `mask_bbox_crop` |

Current interpretation from the controlled 50-painting experiment:

- LaMa dominates the refined reference-based comparison.
- OpenCV Telea remains useful as a deterministic baseline.
- Stable Diffusion rarely wins reference-based metrics but is valuable for studying generative uncertainty.
- SDXL is excluded only because of local feasibility constraints.
- Texture and brushstroke-proxy metrics add local texture-consistency and directional-structure audit layers.
- Metric disagreement is expected and useful.

The model comparison should not be described as a simple leaderboard. It is a trustworthiness audit across metric families and model behaviors.

---

## 9. Current model-risk summary

| Risk | OpenCV Telea | LaMa | Stable Diffusion | SDXL |
|---|---|---|---|---|
| Training-data opacity | Low | Medium | High | High |
| Domain gap | High | Medium–High | High | High |
| Hallucination risk | Low | Medium | High | High |
| Large-mask ability | Low | High | Medium | Potentially high |
| Texture faithfulness risk | High | Medium | High | High |
| Reproducibility | High | High | Medium | Medium |
| Local compute burden | Low | Medium | High | Very high |
| Current evaluation status | Complete | Complete | Complete | Feasibility only |

Texture faithfulness risk includes both general local texture mismatch and brushstroke-like directional structure loss. The brushstroke-proxy metrics measure directional texture preservation, not semantic brushstroke authenticity.

---

---

## 10. Reporting and inspection policy for model audit

Model-specific reports are treated as stable audit artifacts.

Current stable model reports include:

- OpenCV Telea baseline report,
- LaMa baseline report,
- Stable Diffusion baseline report,
- refined three-model comparison report,
- Stable Diffusion uncertainty report,
- Stable Diffusion uncertainty heatmap report,
- final controlled 50-painting report,
- selected per-case diagnostic reports.

Future extensions should create targeted extended reports rather than repeatedly rewriting every historical report.

Recommended approach:

- keep old reports as provenance,
- use texture and heatmap outputs as newer diagnostic layers,
- use selected case reports for inspection examples,
- use the Streamlit dashboard as the interactive review interface,
- avoid committing giant embedded HTML reports unless handled separately.

Current report and inspection entry points:

- `outputs/reports/stable_diffusion_uncertainty_heatmap_report_50.html`
- `outputs/reports/case_diagnostics/case_report_index.html`
- `outputs/dashboard/`
- `streamlit_app.py`

The dashboard and reports should be described as inspection artifacts, not as separate experiments.

---

## 11. Stable Diffusion uncertainty audit status

Stable Diffusion has two uncertainty-related audit layers.

### Multi-seed scalar uncertainty

Notebook:

`notebooks/27_diffusion_uncertainty_analysis_cleaned.ipynb`

Current subset:

- 40 non-zero cases,
- 4 seeds per case,
- 160 generated outputs.

This layer measures:

- image-space seed variation,
- pairwise LPIPS variation,
- pairwise CLIP variation,
- pairwise DINOv2 variation,
- combined uncertainty index,
- uncertainty versus reference-performance relationship.

### Spatial uncertainty heatmaps

Notebook:

`notebooks/32_uncertainty_heatmaps_cleaned.ipynb`

This layer converts seed variation into spatial heatmaps.

The heatmaps summarize uncertainty over:

- full image,
- masked region,
- mask-bounding-box crop,
- outside-mask region,
- outside boundary ring around the mask.

Important boundary:

The boundary-ring metric currently measures an outside ring around the mask. It is not a symmetric inner-plus-outer boundary band.

Interpretation:

Stable Diffusion uncertainty is seed-based spatial variability, not calibrated confidence.

High uncertainty is an audit warning signal. It does not automatically prove poor restoration, and low uncertainty does not prove correctness. The uncertainty layer should be interpreted together with reference-based metrics, texture diagnostics, and case-level inspection.

---

## 12. Texture and brushstroke-proxy audit status

Texture and brushstroke-proxy diagnostics are now part of the model-audit framework.

Notebook:

`notebooks/31_texture_metrics_cleaned.ipynb`

These metrics evaluate local texture consistency between the clean reference crop and the restored crop.

They are computed on:

`mask_bbox_crop`

because texture descriptors require spatial context.

Implemented diagnostic families include:

- GLCM texture differences,
- Gabor response differences,
- gradient magnitude differences,
- edge/detail density difference,
- orientation coherence difference,
- orientation histogram distance,
- normalized combined texture distance.

Interpretation boundary:

Brushstroke-proxy metrics measure directional local texture structure. They do not perform semantic brushstroke recognition, artist authentication, historical verification, or conservation judgment.

Audit role:

- identify smoothing or texture mismatch,
- compare model behavior on high-texture paintings,
- expose cases where refined reference metrics and texture diagnostics disagree,
- strengthen the framework beyond pixel, perceptual, and feature-space similarity.

---

## 13. Dashboard and case-report audit status

The updated dashboard and selected case reports are now part of the model-audit inspection layer.

Dashboard assets:

`outputs/dashboard/`

Dashboard app:

`streamlit_app.py`

Case report index:

`outputs/reports/case_diagnostics/case_report_index.html`

The dashboard includes pages for:

- overview,
- model comparison,
- texture diagnostics,
- diffusion uncertainty,
- case reports,
- reports,
- debug information.

The selected case reports combine:

- clean reference,
- damaged input,
- mask,
- OpenCV Telea output,
- LaMa output,
- Stable Diffusion output,
- refined metric evidence,
- texture diagnostics where available,
- uncertainty heatmaps where available.

Audit role:

- make aggregate findings inspectable,
- support supervisor review,
- expose model behavior in selected edge cases,
- help identify thesis examples,
- reduce cherry-picking by using deterministic selection rules.

Interpretation boundary:

Case reports and dashboards do not create new model-quality evidence. They organize existing outputs for inspection.

---

## 14. Supervisor questions

Model-related questions to confirm:

- Is LaMa sufficient as the main learned inpainting baseline?
- Should SDXL be rerun if stronger university compute is available?
- Should Stable Diffusion uncertainty heatmaps be expanded to all 200 non-zero cases?
- Should the current 40-case uncertainty subset remain sufficient for the thesis?
- Should texture and brushstroke-proxy diagnostics remain part of the core model-audit framework?
- Should semantic/iconographic consistency checks be added after feedback?
- Should DALL-E / OpenAI Image Editing remain excluded from the reproducible core experiment?
- Should the Streamlit dashboard be treated as a formal supporting artifact?

---

## 15. Current conclusion

The current model stack is methodologically coherent:

1. OpenCV Telea provides a deterministic classical baseline.
2. LaMa provides a strong open pretrained learned inpainting baseline.
3. Stable Diffusion Inpainting provides a generative diffusion baseline and uncertainty target.
4. SDXL is documented as a feasibility-audited higher-capacity candidate.

The current model-audit framework now includes:

- refined reference-based comparison,
- metric-region policy,
- texture and brushstroke-proxy diagnostics,
- Stable Diffusion scalar uncertainty,
- Stable Diffusion spatial uncertainty heatmaps,
- selected per-case reports,
- Streamlit dashboard inspection.

The thesis should frame these models as restoration candidates evaluated under controlled synthetic damage.

The central model-audit conclusion is:

> No pretrained model should be treated as a ground-truth painting restoration system. The research contribution is the evaluation framework that exposes where models succeed, fail, hallucinate, smooth texture, alter brushstroke-like directional structure, or become uncertain.