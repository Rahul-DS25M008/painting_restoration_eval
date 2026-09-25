# Stable Diffusion Inpainting - Model Card and Compute Audit

**Evaluation status:** Fully Evaluated  
**Method role:** prompt conditioned stochastic inpainting baseline  
**Dataset scope:** controlled_300  
**Decision boundary:** Digital restoration candidate method, not a conservation authority

<a id="at-a-glance"></a>
## 1. At a glance

Stable Diffusion added prompt-conditioned and repeated-seed evidence, but required far more candidates and did not lead the full-scope reference-based anchor comparison.

- Completed candidates: **8,520 of 8,520**.
- Mean runtime: **8.42 seconds per candidate**.
- Observed notebook-owned storage: **5.76 GiB**.
- Validated anchor wins in the applicable population: **0 of 11**.

**Conclusion:** The compute and quality evidence support this method only within its declared evaluation scope. Anchor wins are descriptive Notebook 21 outcomes, not a combined quality score or conservation verdict.

<a id="identity-and-provenance"></a>
## 2. Identity and provenance

| Field | Recorded value |
|---|---|
| Model ID | `stable_diffusion_inpainting` |
| Family | prompt conditioned latent diffusion inpainting |
| Original purpose | Text-conditioned image generation and masked image modification. |
| Project implementation | Diffusers StableDiffusionInpaintPipeline |
| Implementation version | 1.1.0 |
| Model identifier | `stable-diffusion-v1-5/stable-diffusion-inpainting` |
| Model revision | `8a4288a76071f7280aedbdb3253bdb9e9d5d84bb` |
| Software licence | CreativeML-OpenRAIL-M |
| Weight licence | CreativeML-OpenRAIL-M |

The pinned Hugging Face model card declares CreativeML OpenRAIL-M.

<a id="intended-and-unsupported-use"></a>
## 3. Intended and unsupported use

Appropriate project uses:

- prompt-conditioned generative inpainting baseline
- repeated-seed variability analysis
- controlled prompt-sensitivity analysis for thin scratches

Unsupported uses:

- historically verified reconstruction
- calibrated confidence estimation
- unreviewed conservation decisions

<a id="training-data-and-domain-gap"></a>
## 4. Training data and painting-domain gap

Stable Diffusion v1 lineage uses LAION-derived data; the inpainting checkpoint was further trained at 512x512 on LAION Aesthetics v2 5+ with synthetic masks.

**Training-data transparency status:** documented but not fully auditable

**Domain gap:** Web-scale and natural-image priors are not painting-conservation training.

**Bias and risk:** Prompt, language, web-data, cultural, memorization, hallucination, and lossy-autoencoder risks apply.

**Conclusion:** Source transparency and general-image performance do not establish painting-specific historical or conservation competence.

<a id="project-implementation"></a>
## 5. Project implementation

| Setting | Recorded value |
|---|---|
| Configuration | `sd15_inpaint_fixed_policy_v1` |
| Device | cuda |
| Backend | diffusers_stable_diffusion_inpaint |
| Recorded accelerator | NVIDIA GeForce RTX 3060 Laptop GPU |
| Precision | float16 |
| Inference resolution | 512 x 512 |
| Output resolution | 768 x 768 |
| Input constraints | Normalized 768 x 768 RGB painting input resized to 512 x 512 for inference and returned to 768 x 768 for persistence. |
| Mask constraints | Single-channel missing-region mask using threshold 128; exact outside-mask compositing; empty masks copied; fixed generic or approved scratch-aware prompt policy. |
| Deterministic | False |
| Prompt dependent | True |
| Hardware statement | Executed in float16 on the recorded RTX 3060 Laptop GPU; observed peak allocation is reported without claiming a universal minimum. |

The project used a fixed predeclared configuration and exact outside-mask compositing policy where applicable. Per-case metric-guided tuning was not used.

<a id="evaluated-evidence-coverage"></a>
## 6. Evaluated evidence coverage

| Coverage field | Recorded count |
|---|---:|
| Paintings | 300 |
| Unique cases | 2,620 |
| Candidates | 8,520 |
| Model-inference candidates | 8,220 |
| Identity zero controls | 300 |

Cases and repeated candidates remain nested within paintings. Candidate rows are not treated as independent artworks.

<a id="compute-and-storage"></a>
## 7. Compute and storage

| Measure | Observed result |
|---|---:|
| Total runtime | 19.9 hours |
| Mean runtime | 8.420 s |
| Median runtime | 8.620 s |
| p95 runtime | 9.476 s |
| Failed candidates | 0 |
| Failure rate | 0.00% |
| Retries | 0 |
| Throughput | 0.1188 candidates/second |
| Candidate multiplier | 3.2519 candidates per evaluated case |
| Recorded peak GPU allocation | 2.62 GiB |
| Recorded total GPU memory | not applicable |
| Output files | 8,530 |
| Output storage | 5.76 GiB |

**Conclusion:** These measurements describe the recorded workstation and software environment. They are project evidence, not universal hardware benchmarks.

<a id="quality-evidence"></a>
## 8. Quality evidence

Applicable population: `core_three_model` (2620 cases nested within 300 paintings).

| Validated anchor | Restored mean | Rank | Winner |
|---|---:|---:|---|
| classical_masked_mae | 30.606 | 4 | lama |
| colour_masked_delta_e | 13.267 | 4 | lama |
| feature_clip_crop | 0.94232 | 2 | lama |
| feature_dino_crop | 0.83309 | 2 | lama |
| perceptual_crop_lpips | 0.19717 | 3 | lama |
| seam_boundary_gradient | 0.02085 | 4 | lama |
| semantic_local_dino | 0.66544 | 3 | lama |
| spatial_masked_error | 30.606 | 4 | lama |
| structural_affinity_correlation | 0.85096 | 3 | lama |
| structural_crop_ssim | 0.81233 | 4 | opencv_telea |
| texture_crop_p95 | 2.1169 | 4 | lama |

The method won 0 of 11 validated anchors in this population. Its strongest displayed anchor was `feature_clip_crop`.

**Conclusion:** Better or worse language applies only to the named anchor and population. Runtime is not included in the quality vote, and the anchor count is not a universal quality score.

<a id="determinism-robustness-and-uncertainty"></a>
## 9. Determinism, robustness, and uncertainty

Stable Diffusion is stochastic. Repeated seeds measure empirical candidate variability, and the scratch-aware arm measures damage-specific prompt sensitivity; neither is calibrated confidence.

Low variability or deterministic repetition does not prove that a reconstructed region is correct.

<a id="scalability"></a>
## 10. Scalability

| Scenario | Candidate outputs | Central runtime projection | Output-storage projection |
|---|---:|---:|---:|
| projected_600_current_design_mix | 17,040 | 39.8 hours | 11.50 GiB |
| projected_300_sdxl_full_design | not applicable | not applicable | not applicable to this model-specific projection scenario |

Raw observed median, mean, and p95 runtimes are retained in the compute table. The displayed sensitivity envelope uses the smaller of scaled median and mean as its lower value, scaled mean as its central value, and the larger of scaled p95 and mean as its upper value. These are not confidence intervals. The controlled 300-painting study was executed; only rows explicitly labelled as projections are extrapolations.

<a id="strengths-and-weaknesses"></a>
## 11. Strengths and weaknesses

Strengths:

- prompt-conditioned generative completion
- seed-controllable stochastic candidates
- supports empirical variability analysis

Weaknesses:

- high hallucination and prompt-sensitivity risk
- higher compute and candidate multiplier
- thin-mask geometry can remain visible after compositing

Known project limitations:

- Runtime and memory observations describe one recorded local workstation and software environment.
- The controlled 300-painting values are executed observations; only the explicitly labelled 600-painting and full-design SDXL values are projections.
- Projected storage covers notebook-owned output artifacts and excludes model caches, environments, Git history, and downstream metric outputs.
- SDXL scheduled 35 bounded cases across 30 paintings; 24 completed, one timed out and ten were skipped under the declared budget, so it cannot support a full-scope ranking.
- LaMa per-case runtime includes transparent allocation from IOPaint batch wall-clock measurements.
- Quality-anchor wins are descriptive validated Notebook 21 evidence, not a universal quality or conservation score.
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
- The 1,200 painting-seed pairs are repeated observations nested within 300 paintings; downstream inference must not treat all seed-level pairs as independent paintings.

<a id="human-decision-support-interpretation"></a>
## 12. Human decision-support interpretation

The method can generate and prioritize digital candidates for structured inspection. Reviewers should examine repaired structure, local texture, colour continuity, seams, uncertainty where applicable, and disagreements between evidence families.

**Decision statement:** This card supports transparent method selection and review planning. It does not approve physical treatment, establish historical truth, or replace expert conservation judgement.

<a id="reproducibility-and-provenance"></a>
## 13. Reproducibility and provenance

| Field | Recorded value |
|---|---|
| Producer notebook | `30_model_cards_compute_and_scalability.ipynb` |
| Candidate producer | Notebook 11 |
| Quality producer | Notebook 21 |
| Compute schema | `compute_scalability.v1` |
| Model-card schema | `model_cards.v1` |
| Source review date | 2026-09-02T00:00:00Z |

Primary and runtime sources:

- https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting
- https://arxiv.org/abs/2112.10752

### Final scoped verdict

Stable Diffusion added prompt-conditioned and repeated-seed evidence, but required far more candidates and did not lead the full-scope reference-based anchor comparison. This conclusion remains limited to the controlled evidence and the recorded compute environment.
