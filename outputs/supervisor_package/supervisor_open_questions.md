# Supervisor Open Questions

This file lists the main decisions to confirm before expanding the thesis work further.

## 1. Controlled subset size

Current state:

- 50 paintings
- 5 categories
- 200 non-zero restoration cases
- 3 fully evaluated models
- SDXL feasibility-audited only

Question:

> Is the controlled 50-painting subset sufficient for the thesis, or should the framework be scaled after feedback?

Recommended pre-feedback position:

> Treat the 50-painting subset as sufficient for the methodological prototype. Scale only if the supervisor explicitly requests stronger empirical coverage.

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

## 3. Texture and brushstroke-proxy diagnostics

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

## 4. Stable Diffusion uncertainty heatmaps

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

## 5. SDXL follow-up

Current state:

- SDXL was feasibility-audited.
- Full local evaluation was not completed because of local GPU/runtime constraints.

Question:

> Should SDXL remain feasibility-audited only, or should it be retried with better hardware or cloud resources?

Recommended pre-feedback position:

> Keep SDXL as feasibility-audited only unless the supervisor considers it essential.

## 6. Semantic or iconographic consistency checks

Possible future extension:

- CLIP prompt consistency.
- Region-level description comparison.
- Manual annotation of semantic preservation.
- Iconographic mismatch analysis.

Question:

> Should the thesis include semantic/iconographic preservation checks, or would that expand the scope too far?

Recommended pre-feedback position:

> Wait. This can become subjective quickly and should be supervisor-approved before implementation.

## 7. Metadata-driven analysis

Possible future extension:

- analyze results by artist,
- medium,
- source collection,
- artwork period,
- creation century,
- genre/category.

Question:

> Should artwork metadata be used as an analysis dimension?

Recommended pre-feedback position:

> Only add this if metadata is clean enough and the supervisor wants a stronger art-historical framing.

## 8. Metric-policy ablation

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

## 9. Human or expert review

Possible future extension:

- small human visual preference study,
- expert conservator review if available,
- structured rubric comparing plausibility, fidelity, and risk.

Question:

> Is a human/expert review expected, useful, or out of scope?

Recommended pre-feedback position:

> Treat it as optional. Do not start before feedback.

## 10. Dashboard role

Current state:

- Streamlit dashboard updated.
- Dashboard includes overview, model comparison, texture diagnostics, uncertainty heatmaps, case reports, key findings, reports, and debug pages.

Question:

> Should the dashboard be treated as a formal supporting artifact in the thesis submission?

Recommended pre-feedback position:

> Yes, as a supporting artifact and inspection tool, not as the primary research result.
