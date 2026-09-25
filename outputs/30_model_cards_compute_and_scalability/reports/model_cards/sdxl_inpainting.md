# SDXL Inpainting - Model Card and Compute Audit

**Evaluation status:** Partial Evaluation  
**Method role:** bounded higher capacity diffusion candidate  
**Dataset scope:** controlled_300  
**Decision boundary:** Digital restoration candidate method, not a conservation authority

<a id="at-a-glance"></a>
## 1. At a glance

SDXL completed 24 of 35 scheduled cases in a bounded partial evaluation, providing local feasibility and cost evidence without supporting a full-dataset ranking.

- Completed candidates: **24 of 35**.
- Mean runtime: **199.52 seconds per candidate**.
- Observed notebook-owned storage: **16.19 MiB**.
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
| Implementation version | 3.1.0 |
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
| Input constraints | Normalized 768 x 768 RGB painting input in the predeclared 35-case bounded scope across 30 paintings. |
| Mask constraints | Single-channel case-semantic missing-region mask using threshold 128; exact outside-mask compositing; no empty-mask controls in the partial evaluation. |
| Deterministic | False |
| Prompt dependent | True |
| Hardware statement | Ten cases completed with model CPU offload on the recorded 6 GB RTX 3060 Laptop GPU; this does not establish a universal minimum-VRAM requirement. |

The project used a fixed predeclared configuration and exact outside-mask compositing policy where applicable. Per-case metric-guided tuning was not used.

<a id="evaluated-evidence-coverage"></a>
## 6. Evaluated evidence coverage

| Coverage field | Recorded count |
|---|---:|
| Paintings | 30 |
| Unique cases | 35 |
| Candidates | 35 |
| Model-inference candidates | 35 |
| Identity zero controls | 0 |

Cases and repeated candidates remain nested within paintings. Candidate rows are not treated as independent artworks.

<a id="compute-and-storage"></a>
## 7. Compute and storage

| Measure | Observed result |
|---|---:|
| Total runtime | 79.8 minutes |
| Mean runtime | 199.519 s |
| Median runtime | 198.031 s |
| p95 runtime | 206.559 s |
| Failed candidates | 11 |
| Failure rate | 31.43% |
| Retries | 0 |
| Throughput | 0.0050 candidates/second |
| Candidate multiplier | 1.0000 candidates per evaluated case |
| Recorded peak GPU allocation | 5.25 GiB |
| Recorded total GPU memory | 6.00 GiB |
| Output files | 30 |
| Output storage | 16.19 MiB |

**Conclusion:** These measurements describe the recorded workstation and software environment. They are project evidence, not universal hardware benchmarks.

<a id="quality-evidence"></a>
## 8. Quality evidence

Applicable population: `sdxl_four_model_subset` (24 cases nested within 19 paintings).

| Validated anchor | Restored mean | Rank | Winner |
|---|---:|---:|---|
| classical_masked_mae | 72.627 | 5 | lama |
| colour_masked_delta_e | 29.611 | 5 | lama |
| feature_clip_crop | 0.86598 | 4 | stable_diffusion_inpainting |
| feature_dino_crop | 0.77602 | 3 | stable_diffusion_inpainting |
| perceptual_crop_lpips | 0.31078 | 5 | lama |
| seam_boundary_gradient | 0.046617 | 5 | lama |
| semantic_local_dino | 0.51293 | 5 | lama |
| spatial_masked_error | 72.627 | 5 | lama |
| structural_affinity_correlation | 0.67215 | 5 | lama |
| structural_crop_ssim | 0.75834 | 5 | opencv_telea |
| texture_crop_p95 | 3.5998 | 5 | lama |

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
| projected_600_current_design_mix | not applicable | not applicable | not applicable to this model-specific projection scenario |
| projected_300_sdxl_full_design | 2,620 | 128.6 hours | 1.71 GiB |

Raw observed median, mean, and p95 runtimes are retained in the compute table. The displayed sensitivity envelope uses the smaller of scaled median and mean as its lower value, scaled mean as its central value, and the larger of scaled p95 and mean as its upper value. These are not confidence intervals. The controlled 300-painting study was executed; only rows explicitly labelled as projections are extrapolations.

<a id="strengths-and-weaknesses"></a>
## 11. Strengths and weaknesses

Strengths:

- higher-capacity diffusion lineage
- technically valid 768px partial outputs
- direct local feasibility evidence

Weaknesses:

- only 35 purposively selected cases, of which 24 completed
- very high runtime on recorded hardware
- no repeated-seed uncertainty coverage

Known project limitations:

- Runtime and memory observations describe one recorded local workstation and software environment.
- The controlled 300-painting values are executed observations; only the explicitly labelled 600-painting and full-design SDXL values are projections.
- Projected storage covers notebook-owned output artifacts and excludes model caches, environments, Git history, and downstream metric outputs.
- SDXL scheduled 35 bounded cases across 30 paintings; 24 completed, one timed out and ten were skipped under the declared budget, so it cannot support a full-scope ranking.
- LaMa per-case runtime includes transparent allocation from IOPaint batch wall-clock measurements.
- Quality-anchor wins are descriptive validated Notebook 21 evidence, not a universal quality or conservation score.
- The 35 cases are a predeclared balanced purposive scope and do not represent a full SDXL evaluation.
- The 35 case observations span 30 paintings; repeated cases from five retained pilot anchors are nested observations.
- A timeout or CUDA out-of-memory failure is hardware/runtime evidence and must not be interpreted as poor restoration quality.
- Only technically validated completed candidates may enter downstream metric computation.
- The global seven-hour budget can leave later scheduled cases explicitly unexecuted.
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

SDXL completed 24 of 35 scheduled cases in a bounded partial evaluation, providing local feasibility and cost evidence without supporting a full-dataset ranking. This conclusion remains limited to the controlled evidence and the recorded compute environment.
