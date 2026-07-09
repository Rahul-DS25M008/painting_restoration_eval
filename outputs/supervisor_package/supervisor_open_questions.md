# Supervisor Open Questions

This file lists the main decisions to confirm before expanding the thesis work further.

## 1. Controlled subset size and possible scaling

Current state:

- 50 paintings
- 5 categories
- 200 non-zero restoration cases
- 3 fully evaluated models
- SDXL feasibility-audited only

Question:

> Is the controlled 50-painting subset sufficient for the thesis, or should the framework be scaled after feedback, for example toward 300 paintings?

Recommended pre-feedback position:

> Treat the 50-painting subset as sufficient for the methodological prototype. Scale only if the supervisor explicitly requests stronger empirical coverage.

Possible post-feedback extension:

- scale from 50 to 300 paintings,
- or choose an intermediate scale if 300 paintings creates unnecessary runtime/storage burden.

## 2. Metric-region policy

Current final policy:

- MSE: masked region
- PSNR: masked region
- SSIM: mask bounding-box crop
- LPIPS: mask bounding-box crop
- CLIP: mask bounding-box crop
- DINOv2: mask bounding-box crop
- Texture metrics: mask bounding-box crop
- Brushstroke-proxy metrics: mask bounding-box crop

Question:

> Is this metric-region policy acceptable as the fixed policy for the thesis?

Recommended pre-feedback position:

> Keep this policy fixed unless the supervisor asks for ablation or comparison.

## 3. Metric-policy ablation

Possible future extension:

- compare original versus refined metric-region policy,
- compare reference-only metrics versus perceptual/feature/texture-inclusive policies,
- compare with and without texture diagnostics,
- compare majority vote against alternative vote or aggregation rules,
- test whether model conclusions change under different evaluation policies.

Question:

> Should the thesis include an ablation showing how evaluation conclusions change under different metric-region or metric-family choices?

Recommended pre-feedback position:

> This is one of the strongest framework-oriented extensions because it directly supports the claim that evaluation design affects restoration conclusions. It should be added only if the supervisor wants additional methodological depth.

## 4. Texture and brushstroke-proxy diagnostics

Current state:

- Texture metrics added in Notebook 31.
- Brushstroke-proxy orientation and directional texture diagnostics added.
- Disagreement cases between refined metrics and texture diagnostics are available.

Question:

> Should texture and brushstroke-proxy diagnostics be part of the core framework or treated as supplementary diagnostics?

Recommended pre-feedback position:

> Keep them as core diagnostic layers, but phrase them conservatively.

Important wording:

> Brushstroke-proxy metrics are directional texture proxies, not semantic brushstroke recognition, authentication, or conservation truth.

## 5. Color consistency metrics

Possible future extension:

- local Lab color difference,
- CIEDE2000-style color distance,
- local color histogram distance,
- restored-region versus surrounding-ring color shift.

Question:

> Should the framework add explicit color consistency diagnostics for restored regions?

Recommended pre-feedback position:

> This is a low-scope, painting-relevant extension. It should be considered if the supervisor wants stronger evaluation of chromatic consistency and restoration-region harmony.

## 5. Boundary and seam consistency metrics

Possible future extension:

- boundary-ring error around the mask,
- gradient discontinuity across the restoration boundary,
- color jump across the mask edge,
- texture discontinuity near the seam.

Question:

> Should the framework evaluate boundary or seam artifacts around restored regions?

Recommended pre-feedback position:

> This is a useful painting-restoration diagnostic because visually plausible restorations can still fail at the transition between restored and preserved regions.

## 6. Damage-size sensitivity analysis

Possible future extension:

- analyze performance by actual mask area,
- test whether model performance degrades with larger damage,
- test whether texture distance increases with damage size,
- test whether Stable Diffusion uncertainty increases with damage size.

Question:

> Should the thesis include damage-size sensitivity analysis based on actual mask area and damage severity?

Recommended pre-feedback position:

> This is a strong low-risk extension because mask-area metadata already exists and the analysis strengthens interpretation by damage severity.

## 7. Restoration risk scoring / diagnostic risk profiles

Possible future extension:

Create case-level diagnostic risk profiles using signals such as:

- weak reference-based performance,
- metric disagreement,
- high texture distance,
- high Stable Diffusion uncertainty,
- boundary/seam inconsistency,
- large damage size,
- possible semantic/iconographic risk if that layer is added.

Question:

> Should the framework synthesize multiple diagnostic signals into case-level restoration risk profiles?

Recommended pre-feedback position:

> This should be framed as diagnostic risk profiling, not as a universal restoration-quality score. It is useful if the supervisor wants a clearer trustworthiness synthesis layer.

## 8. Stable Diffusion uncertainty heatmaps

Current state:

- 40 cases.
- 4 seeds per case.
- 160 seed outputs.
- Spatial heatmaps generated from per-pixel variation across seed outputs.
- Summaries available by case, mask type, and category.

Question:

> Is the current 40-case uncertainty heatmap subset sufficient, or should uncertainty be expanded to all 200 non-zero cases?

Recommended pre-feedback position:

> Keep the current 40-case uncertainty subset for feedback. Expand only after supervisor approval because full expansion increases compute and storage.

Important wording:

> These heatmaps show seed-based spatial variability, not calibrated confidence.

Boundary clarification:

> The current boundary-ring metric measures an outside ring around the mask, not a symmetric inner-plus-outer boundary band.

## 9. SDXL follow-up

Current state:

- SDXL was feasibility-audited.
- Full local evaluation was not completed because of local GPU/runtime constraints.

Question:

> Should SDXL remain feasibility-audited only, or should it be retried with better hardware or cloud resources?

Recommended pre-feedback position:

> Keep SDXL as feasibility-audited only unless the supervisor considers it essential.

## 10. Semantic or iconographic consistency checks

Possible future extension:

- CLIP prompt consistency.
- Region-level description comparison.
- Manual annotation of semantic preservation.
- Iconographic mismatch analysis.

Question:

> Should the thesis include semantic/iconographic preservation checks, or would that expand the scope too far?

Recommended pre-feedback position:

> Wait. This can become subjective quickly and should be supervisor-approved before implementation.

## 11. Metadata-driven or computed visual grouping

Possible future extension:

Metadata-driven grouping:

- artist,
- medium,
- source collection,
- artwork period,
- creation century,
- genre/category.

Computed visual grouping:

- texture density,
- edge density,
- brightness,
- color variance,
- mask centrality,
- mask area.

Question:

> Should artwork metadata or computed visual properties be used as analysis dimensions?

Recommended pre-feedback position:

> Add metadata grouping only if metadata is clean enough. Computed visual grouping may be more reproducible and easier to control.

## 12. Metric-policy ablation

Possible future extension:

- old vs refined metric-region policy,
- reference metrics only vs perceptual/feature metrics,
- with vs without texture diagnostics,
- with vs without uncertainty diagnostics,
- alternative majority vote rules.

Question:

> Should the thesis include an ablation showing how evaluation conclusions change under different policy choices?

Recommended pre-feedback position:

> This is methodologically valuable, but should wait until the supervisor confirms the current framework.

## 13. Mask/input robustness analysis

Possible future extension:

- perturb masks through dilation, erosion, boundary jitter, or small spatial shifts,
- perturb damaged inputs through brightness changes, mild noise, blur, compression, or fill-strategy changes,
- evaluate whether OpenCV Telea, LaMa, and Stable Diffusion remain stable under controlled input changes.

Question:

> Should the thesis include robustness analysis for deterministic and generative models?

Recommended pre-feedback position:

> This is useful but should remain optional because perturbation experiments can multiply runtime quickly. For OpenCV and LaMa, this should be described as robustness or sensitivity analysis rather than seed-based uncertainty.

## 14. Human or expert review

Possible future extension:

- small human visual preference study,
- expert conservator review if available,
- structured rubric comparing plausibility, fidelity, and risk.

Question:

> Is a human/expert review expected, useful, or out of scope?

Recommended pre-feedback position:

> Treat it as optional. Do not start before feedback.

## 15. Dashboard role

Current state:

- Streamlit dashboard updated.
- Dashboard includes overview, model comparison, texture diagnostics, uncertainty heatmaps, case reports, key findings, reports, and debug pages.

Question:

> Should the dashboard be treated as a formal supporting artifact in the thesis submission?

Recommended pre-feedback position:

> Yes, as a supporting artifact and inspection tool, not as the primary research result.

## 16. Restoration Prompts

Possible future extension:

- compare generic restoration prompts to style-specific restoration prompts.
- Run the metrics on generic restored images and style-specific restored images to see if there's a difference.

Question:

> Does a style-specific restoration prompt improve the quality of restored image compared to a generic one?

Recommended pre-feedback position:

> It can be a nice addition to the existing research questions. Could consider adding a supllementary research question.
