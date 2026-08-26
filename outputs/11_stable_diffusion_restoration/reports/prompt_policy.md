# Stable Diffusion Prompt Policy

## Scope

This report documents the fixed Stable Diffusion prompt policy, contextual prompt ablation, paired scratch-aware prompt experiment, repeated-seed design, and known methodological limitations used by Notebook 11.

- Base configuration: `config/experiments/stable_diffusion.yaml`
- Scratch supplement: `config/experiments/stable_diffusion_scratch_prompt_ablation.yaml`
- Model: `stable-diffusion-v1-5/stable-diffusion-inpainting`
- Pinned revision: `8a4288a76071f7280aedbdb3253bdb9e9d5d84bb`
- Configuration ID: `sd15_inpaint_fixed_policy_v1`
- Effective prompt policy ID: `sd15_prompt_policy.v3`
- Scheduler: `DDIMScheduler`
- Inference steps: `30`
- Guidance scale: `7.5`
- Strength: `1.0`
- Precision/device: `float16` / `cuda`
- Primary seed: `2026`
- Frozen repeated seeds: `2026, 2027, 2028, 2029`

## Primary Generic Prompt

a complete aged fine-art painting with seamless visual continuity, coherent composition, and a consistent colour palette, brushwork, canvas texture, lighting, and level of detail

## Base Negative Prompt

modern objects, text, watermark, signature, frame, border, added people, changed faces, extra objects, oversharpened, cartoon, digital art, photorealistic replacement, unrealistic texture, harsh seams

## Scratch-Aware Treatment

The positive treatment describes the desired complete and visually continuous repaired state:

a complete undamaged aged fine-art painting with seamless visual continuity, uninterrupted brushwork and canvas texture, with the original surrounding colours, lighting, edges, forms, and structures naturally continued across the repaired area

The following morphology terms are appended to the negative prompt:

visible scratches, residual scratch marks, thin artificial lines, grey repair lines, dark repair lines, white gaps, seams, outlines, discontinuities, mismatched texture, blurry repair

## Controlled Prompt Variants

| Variant | Family | Primary | Requires metadata | Metadata fields | Template |
|---|---|---:|---:|---|---|
| p00_generic | generic | True | False | [] | a complete aged fine-art painting with seamless visual continuity, coherent composition, and a consistent colour palette, brushwork, canvas texture, lighting, and level of detail |
| p01_category | contextual | False | True | ["category"] | a complete aged fine-art painting in the {category} genre with seamless visual continuity, coherent composition, and a consistent colour palette, brushwork, canvas texture, lighting, and level of detail |
| p02_artist | contextual | False | True | ["artist"] | a complete aged fine-art painting by {artist} with seamless visual continuity, coherent composition, and a consistent colour palette, brushwork, canvas texture, lighting, and level of detail |
| p03_artist_category | contextual | False | True | ["artist", "category"] | a complete aged {category} painting by {artist} with seamless visual continuity, coherent composition, and a consistent colour palette, brushwork, canvas texture, lighting, and level of detail |
| p04_full_context | contextual | False | True | ["title", "artist", "category"] | a complete aged painting titled {title}, by {artist}, in the {category} genre with seamless visual continuity, coherent composition, and a consistent colour palette, brushwork, canvas texture, lighting, and level of detail |
| p05_scratch_aware | contextual | False | True | ["damage_or_degradation_type"] | a complete undamaged aged fine-art painting with seamless visual continuity, uninterrupted brushwork and canvas texture, with the original surrounding colours, lighting, edges, forms, and structures naturally continued across the repaired area |

## Candidate Design

- Eligible primary candidates: `410`
- Schema-compatible prompt-context candidates: `680`
- Schema-compatible uncertainty extensions: `240`
- Total candidates: `1330`
- Model inferences: `1280`
- Identity zero controls: `50`

### Formal Paired Scratch Experiment

- Paintings: `50` canonical controlled paintings.
- Damage case: `scratch_thin`.
- Prompt arms: `p00_generic`, `p05_scratch_aware`.
- Seeds: `2026`, `2027`, `2028`, `2029`.
- Painting-seed pairs: `200`.
- Formal paired outcomes: `400`.
- Added generic seed controls: `120`.
- Added scratch-aware candidates: `200`.
- Formal selection policy: `all_canonical_paintings_paired_non_metric.v1`.
- Painting is the independent experimental unit; seeds are repeated observations nested within paintings.
- Both prompt arms are preserved for every painting-seed pair. No best seed, prompt, painting, or candidate is selected using restoration-quality metrics.
- Contextual variants p01–p04 remain exploratory conditioning evidence and are not part of the formal two-arm scratch contrast.

## Selection Policies

- Base candidate-selection policy: `deterministic_hash_stratified_non_metric.v1`.
- Scratch candidate-selection policy: `all_canonical_paintings_paired_non_metric.v1`.
- Visual-selection policy: `sd15_visual_selection_hash_stratified.v2`.
- Metric columns used for selection: none.

## Execution and Compositing

- Compositing policy: `masked_composite_preserve_outside.v1`.
- Zero-control policy: `identity_noop`.
- Safety-checker policy: `disabled_research_dataset`.
- Retry policy: at most `1` retry with the exact declared seed.

## Thin-Scratch Limitation

Canonical thin scratches are only a few pixels wide at 768 × 768. Their spatial support can shrink or fragment during 512-pixel preprocessing and latent-grid mask resampling. Exact compositing can consequently reveal generated colour or texture mismatch as a narrow grey or dark line. Prompting tests semantic mitigation; it does not change or solve the underlying spatial-resolution constraint.

## Downstream Metric Responsibility

Downstream metric notebooks must compute restoration quality for both prompt arms, preserve the paired (case_id, seed) structure, aggregate the four repeated seeds within each painting, quantify painting-level consistency, and relate the results to mask and boundary geometry.

Notebook 11 performs no restoration-quality-based ranking.

## Known Limitations

- Stable Diffusion produces plausible prompt-conditioned inpainting, not historically verified reconstruction.
- The generic primary prompt and fixed inference settings are intentionally not tuned per painting or damage case.
- Contextual prompts form a controlled ablation and are not used to select primary candidates.
- Repeated seeds characterize stochastic sensitivity for a fixed predeclared subset and are not metric-selected.
- Eligible synthetic-degradation cases are supplementary masked-removal diagnostics and remain separate from missing-content claims.
- CUDA inference may not be byte-identical across hardware or software stacks; the complete environment is recorded.
- The safety checker is disabled for this fixed research dataset and that policy is explicitly recorded.
- The scratch-aware prompt is a controlled semantic-conditioning treatment and does not change the model, mask, seed, scheduler, inference resolution, compositing policy, or any other generation setting.
- Thin scratch masks can lose or fragment spatial support during 512-pixel and latent-grid downsampling; prompting cannot be assumed to resolve that geometric limitation.
- Literal scratch terminology is concentrated in the negative prompt because text encoders may not reliably interpret negation in positive prompts.
- The 200 painting-seed pairs are repeated observations nested within 50 paintings; downstream inference must not treat all seed-level pairs as independent paintings.

## Interpretation

Stable Diffusion candidates are plausible, prompt-conditioned inpaintings. They are not historically verified reconstructions and must not be treated as autonomous conservation decisions.
