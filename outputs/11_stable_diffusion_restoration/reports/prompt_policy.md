# Stable Diffusion Prompt Policy

## Scope

This report documents the fixed Stable Diffusion prompt policy, controlled contextual ablation, repeated-seed design, and known methodological limitations used by Notebook 11.

- Configuration: `stable_diffusion_config.v1` / `1.1.0`
- Model: `stable-diffusion-v1-5/stable-diffusion-inpainting`
- Pinned revision: `8a4288a76071f7280aedbdb3253bdb9e9d5d84bb`
- Configuration ID: `sd15_inpaint_fixed_policy_v1`
- Prompt policy ID: `sd15_prompt_policy.v2`
- Scheduler: `DDIMScheduler`
- Inference steps: `30`
- Guidance scale: `7.5`
- Strength: `1.0`
- Precision/device: `float16` / `cuda`
- Primary seed: `2026`
- Uncertainty seeds: `2026, 2027, 2028, 2029`

## Primary Prompt

a complete aged fine-art painting with seamless visual continuity, coherent composition, and a consistent colour palette, brushwork, canvas texture, lighting, and level of detail

## Negative Prompt

modern objects, text, watermark, signature, frame, border, added people, changed faces, extra objects, oversharpened, cartoon, digital art, photorealistic replacement, unrealistic texture, harsh seams

## Controlled Prompt Variants

| Variant | Family | Primary | Requires metadata | Metadata fields | Template |
|---|---|---:|---:|---|---|
| p00_generic | generic | True | False | [] | a complete aged fine-art painting with seamless visual continuity, coherent composition, and a consistent colour palette, brushwork, canvas texture, lighting, and level of detail |
| p01_category | contextual | False | True | ["category"] | a complete aged fine-art painting in the {category} genre with seamless visual continuity, coherent composition, and a consistent colour palette, brushwork, canvas texture, lighting, and level of detail |
| p02_artist | contextual | False | True | ["artist"] | a complete aged fine-art painting by {artist} with seamless visual continuity, coherent composition, and a consistent colour palette, brushwork, canvas texture, lighting, and level of detail |
| p03_artist_category | contextual | False | True | ["artist", "category"] | a complete aged {category} painting by {artist} with seamless visual continuity, coherent composition, and a consistent colour palette, brushwork, canvas texture, lighting, and level of detail |
| p04_full_context | contextual | False | True | ["title", "artist", "category"] | a complete aged painting titled {title}, by {artist}, in the {category} genre with seamless visual continuity, coherent composition, and a consistent colour palette, brushwork, canvas texture, lighting, and level of detail |

## Candidate Design

- Eligible primary cases: `410`
- Contextual prompt candidates: `480`
- Repeated-seed extensions: `120`
- Total candidates: `1010`
- Candidate-selection policy: `deterministic_hash_stratified_non_metric.v1`
- Visual-selection policy: `sd15_visual_selection_hash_stratified.v1`
- Metric columns used for selection: none.
- Contextual prompts are controlled ablations and are not used to replace or select the generic primary candidate.
- Repeated seeds characterize stochastic sensitivity and are not ranked or selected using restoration metrics.

## Execution and Compositing

- Compositing policy: `masked_composite_preserve_outside.v1`
- Zero-control policy: `identity_noop`
- Safety-checker policy: `disabled_research_dataset`
- Retry policy: at most `1` retry with the exact seed.

## Known Limitations

- Stable Diffusion produces plausible prompt-conditioned inpainting, not historically verified reconstruction.
- The generic primary prompt and fixed inference settings are intentionally not tuned per painting or damage case.
- Contextual prompts form a controlled ablation and are not used to select primary candidates.
- Repeated seeds characterize stochastic sensitivity for a fixed predeclared subset and are not metric-selected.
- Eligible synthetic-degradation cases are supplementary masked-removal diagnostics and remain separate from missing-content claims.
- CUDA inference may not be byte-identical across hardware or software stacks; the complete environment is recorded.
- The safety checker is disabled for this fixed research dataset and that policy is explicitly recorded.

## Interpretation

Stable Diffusion candidates are plausible, prompt-conditioned inpaintings. They are not historically verified reconstructions and must not be treated as autonomous conservation decisions.
