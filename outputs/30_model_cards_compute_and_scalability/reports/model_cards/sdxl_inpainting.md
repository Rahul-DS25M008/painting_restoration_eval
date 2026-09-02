# SDXL Inpainting - Model Card and Compute Audit

**Evaluation status:** Partial Evaluation  
**Method role:** bounded higher capacity diffusion candidate  
**Dataset scope:** controlled_50  
**Decision boundary:** Digital restoration candidate method, not a conservation authority

<a id="at-a-glance"></a>
## 1. At a glance

SDXL completed a bounded ten-case partial evaluation, providing direct local feasibility evidence without supporting a full-dataset ranking.

- Completed candidates: **10 of 10**.
- Mean runtime: **378.47 seconds per candidate**.
- Observed notebook-owned storage: **6.86 MiB**.
- Validated anchor wins in the applicable population: **0 of 11**.

**Conclusion:** The compute and quality evidence support this method only within its declared evaluation scope. Anchor wins are descriptive Notebook 21 outcomes, not a combined quality score or conservation verdict.

<a id="identity-and-provenance"></a>
## 2. Identity and provenance

| Field | Recorded value |
|---|---|
| Model ID | `sdxl_inpainting` |
| Family | prompt conditioned sdxl latent diffusion inpainting |
| Original purpose | Higher-capacity text-conditioned image generation and masked image modification. |
| Project implementation | Diffusers StableDiffusionXLInpaintPipeline |
| Implementation version | 3.0.0 |
| Model identifier | `diffusers/stable-diffusion-xl-1.0-inpainting-0.1` |
| Model revision | `115134f363124c53c7d878647567d04daf26e41e` |
| Software licence | CreativeML-OpenRAIL++-M |
| Weight licence | CreativeML-OpenRAIL++-M |

The pinned Hugging Face model card declares CreativeML Open RAIL++-M.

<a id="intended-and-unsupported-use"></a>
## 3. Intended and unsupported use

Appropriate project uses:

- bounded partial comparison
- local compute and memory feasibility evidence
- transparent SDXL scaling projection

Unsupported uses:

- full controlled-dataset ranking
- universal comparison against the three full-scope methods
- historically verified reconstruction or conservation approval

<a id="training-data-and-domain-gap"></a>
## 4. Training data and painting-domain gap

The inpainting checkpoint was initialized from SDXL base and trained for 40k steps at 1024x1024 with synthetic masks; the pinned inpainting card does not provide a complete independently auditable training corpus inventory.

**Training-data transparency status:** partial

**Domain gap:** The higher-capacity generative model remains non-conservation-specific and only partially evaluated here.

**Bias and risk:** Generative, prompt, cultural, hallucination, compositional, face, and lossy-autoencoder limitations remain.

**Conclusion:** Source transparency and general-image performance do not establish painting-specific historical or conservation competence.

<a id="project-implementation"></a>
## 5. Project implementation

| Setting | Recorded value |
|---|---|
| Configuration | `sdxl_quality_preserving_partial_evaluation_v1` |
| Device | cuda |
| Backend | recorded in upstream manifest |
| Recorded accelerator | NVIDIA GeForce RTX 3060 Laptop GPU |
| Precision | float16 |
| Inference resolution | 768 x 768 |
| Output resolution | 768 x 768 |
| Input constraints | Normalized 768 x 768 RGB painting input in the predeclared ten-case bounded scope. |
| Mask constraints | Single-channel case-semantic missing-region mask using threshold 128; exact outside-mask compositing; no empty-mask controls in the partial evaluation. |
| Deterministic | False |
| Prompt dependent | True |
| Hardware statement | Ten cases completed with model CPU offload on the recorded 6 GB RTX 3060 Laptop GPU; this does not establish a universal minimum-VRAM requirement. |

The project used a fixed predeclared configuration and exact outside-mask compositing policy where applicable. Per-case metric-guided tuning was not used.

<a id="evaluated-evidence-coverage"></a>
## 6. Evaluated evidence coverage

| Coverage field | Recorded count |
|---|---:|
| Paintings | 5 |
| Unique cases | 10 |
| Candidates | 10 |
| Model-inference candidates | 10 |
| Identity zero controls | 0 |

Cases and repeated candidates remain nested within paintings. Candidate rows are not treated as independent artworks.

<a id="compute-and-storage"></a>
## 7. Compute and storage

| Measure | Observed result |
|---|---:|
| Total runtime | 63.1 minutes |
| Mean runtime | 378.469 s |
| Median runtime | 294.916 s |
| p95 runtime | 595.271 s |
| Failed candidates | 0 |
| Failure rate | 0.00% |
| Retries | 0 |
| Throughput | 0.0026 candidates/second |
| Candidate multiplier | 1.0000 candidates per evaluated case |
| Recorded peak GPU allocation | 5.25 GiB |
| Recorded total GPU memory | 6.00 GiB |
| Output files | 16 |
| Output storage | 6.86 MiB |

**Conclusion:** These measurements describe the recorded workstation and software environment. They are project evidence, not universal hardware benchmarks.

<a id="quality-evidence"></a>
## 8. Quality evidence

Applicable population: `sdxl_four_model_subset` (10 cases nested within 5 paintings).

| Validated anchor | Restored mean | Rank | Winner |
|---|---:|---:|---|
| classical_masked_mae | 79.803 | 4 | lama |
| colour_masked_delta_e | 32.597 | 4 | lama |
| feature_clip_crop | 0.82359 | 3 | stable_diffusion_inpainting |
| feature_dino_crop | 0.74495 | 2 | stable_diffusion_inpainting |
| perceptual_crop_lpips | 0.40265 | 4 | lama |
| seam_boundary_gradient | 0.050275 | 4 | lama |
| semantic_local_dino | 0.49961 | 3 | lama |
| spatial_masked_error | 79.803 | 4 | lama |
| structural_affinity_correlation | 0.63095 | 4 | lama |
| structural_crop_ssim | 0.67774 | 4 | opencv_telea |
| texture_crop_p95 | 5.0656 | 4 | lama |

The method won 0 of 11 validated anchors in this population. Its strongest displayed anchor was `feature_dino_crop`.

**Conclusion:** Better or worse language applies only to the named anchor and population. Runtime is not included in the quality vote, and the anchor count is not a universal quality score.

<a id="determinism-robustness-and-uncertainty"></a>
## 9. Determinism, robustness, and uncertainty

SDXL has one seed per completed case. Generative uncertainty is therefore not estimable from this scope, and no artificial uncertainty value is assigned.

Low variability or deterministic repetition does not prove that a reconstructed region is correct.

<a id="scalability"></a>
## 10. Scalability

| Scenario | Candidate outputs | Central runtime projection | Output-storage projection |
|---|---:|---:|---:|
| projected_300_canonical_primary | 1,500 | 133.3 hours | 1,014.51 MiB |
| projected_300_current_design_mix | not applicable | not applicable | not applicable: bounded SDXL scope has no full current-design equivalent |

Raw observed median, mean, and p95 runtimes are retained in the compute table. The displayed sensitivity envelope uses the smaller of scaled median and mean as its lower value, scaled mean as its central value, and the larger of scaled p95 and mean as its upper value. These are not confidence intervals. No 300-painting experiment was executed.

<a id="strengths-and-weaknesses"></a>
## 11. Strengths and weaknesses

Strengths:

- higher-capacity diffusion lineage
- technically valid 768px partial outputs
- direct local feasibility evidence

Weaknesses:

- only ten purposively selected cases
- very high runtime on recorded hardware
- no repeated-seed uncertainty coverage

Known project limitations:

- Runtime and memory observations describe one recorded local workstation and software environment.
- The 300-painting values are transparent linear projections, not executed experiments.
- Projected storage covers notebook-owned output artifacts and excludes model caches, environments, Git history, and downstream metric outputs.
- SDXL has ten completed candidates nested within five paintings and cannot support a full-scope ranking.
- LaMa per-case runtime includes transparent allocation from IOPaint batch wall-clock measurements.
- Quality-anchor wins are descriptive validated Notebook 21 evidence, not a universal quality or conservation score.
- The ten cases are a predeclared purposive partial scope and do not represent a full SDXL evaluation.
- The ten case observations are nested within five paintings; downstream inference must treat painting as the independent unit.
- A timeout or CUDA out-of-memory failure is hardware/runtime evidence and must not be interpreted as poor restoration quality.
- Only technically validated completed candidates may enter downstream metric computation.
- The global two-hour budget can leave later scheduled cases explicitly unexecuted.
- SDXL outputs are plausible prompt-conditioned inpaintings, not historically verified reconstructions or conservation recommendations.

<a id="human-decision-support-interpretation"></a>
## 12. Human decision-support interpretation

The method can generate and prioritize digital candidates for structured inspection. Reviewers should examine repaired structure, local texture, colour continuity, seams, uncertainty where applicable, and disagreements between evidence families.

**Decision statement:** This card supports transparent method selection and review planning. It does not approve physical treatment, establish historical truth, or replace expert conservation judgement.

<a id="reproducibility-and-provenance"></a>
## 13. Reproducibility and provenance

| Field | Recorded value |
|---|---|
| Producer notebook | `30_model_cards_compute_and_scalability.ipynb` |
| Candidate producer | Notebook 12 |
| Quality producer | Notebook 21 |
| Compute schema | `compute_scalability.v1` |
| Model-card schema | `model_cards.v1` |
| Source review date | 2026-09-02T00:00:00Z |

Primary and runtime sources:

- https://huggingface.co/diffusers/stable-diffusion-xl-1.0-inpainting-0.1
- https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0

### Final scoped verdict

SDXL completed a bounded ten-case partial evaluation, providing direct local feasibility evidence without supporting a full-dataset ranking. This conclusion remains limited to the controlled evidence and the recorded compute environment.
