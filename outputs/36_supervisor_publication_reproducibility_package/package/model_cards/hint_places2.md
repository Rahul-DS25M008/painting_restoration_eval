# HINT - Model Card and Compute Audit

**Evaluation status:** Fully Evaluated  
**Method role:** learned deterministic mask aware transformer  
**Dataset scope:** controlled_300  
**Decision boundary:** Digital restoration candidate method, not a conservation authority

<a id="at-a-glance"></a>
## 1. At a glance

HINT added a deterministic mask-aware transformer family with complete controlled-300 coverage, extending the learned comparison beyond LaMa's convolutional design.

- Completed candidates: **2,620 of 2,620**.
- Mean runtime: **6.12 seconds per candidate**.
- Observed notebook-owned storage: **1.79 GiB**.
- Validated anchor wins in the applicable population: **0 of 11**.

**Conclusion:** The compute and quality evidence support this method only within its declared evaluation scope. Anchor wins are descriptive Notebook 21 outcomes, not a combined quality score or conservation verdict.

<a id="identity-and-provenance"></a>
## 2. Identity and provenance

| Field | Recorded value |
|---|---|
| Model ID | `hint_places2` |
| Family | learned mask aware transformer inpainting |
| Original purpose | High-fidelity image inpainting using mask-aware transformer features and a learned general-scene prior. |
| Project implementation | Official HINT generator loaded directly |
| Implementation version | 15e867d8c8689b9d5050383fc3884537ae876145 |
| Model identifier | `hint_places2_official` |
| Model revision | `15e867d8c8689b9d5050383fc3884537ae876145` |
| Software licence | MIT |
| Weight licence | not_separately_verified_in_project_sources |

The official repository software is MIT licensed; the Places2 checkpoint terms are recorded separately and are not silently equated with the software licence.

<a id="intended-and-unsupported-use"></a>
## 3. Intended and unsupported use

Appropriate project uses:

- deterministic structure-aware learned inpainting comparison
- controlled digital restoration candidate generation
- full-scope comparison with classical, convolutional and diffusion methods

Unsupported uses:

- historically verified reconstruction
- artist authentication or conservation approval
- calibrated uncertainty estimation

<a id="training-data-and-domain-gap"></a>
## 4. Training data and painting-domain gap

The selected official checkpoint is the Places2 variant. Places2 is general-scene data rather than painting-conservation data.

**Training-data transparency status:** partial

**Domain gap:** Places2 training does not establish painting-specific, art-historical or conservation-specific competence.

**Bias and risk:** Learned scene priors may impose unsupported structure, texture or cultural regularities despite deterministic execution.

**Conclusion:** Source transparency and general-image performance do not establish painting-specific historical or conservation competence.

<a id="project-implementation"></a>
## 5. Project implementation

| Setting | Recorded value |
|---|---|
| Configuration | `hint_places2_native_768_exact_composite_v1` |
| Device | cuda |
| Backend | official_hint_direct |
| Recorded accelerator | NVIDIA GeForce RTX 3060 Laptop GPU |
| Precision | float32 |
| Inference resolution | 768 x 768 |
| Output resolution | 768 x 768 |
| Input constraints | Normalized 768 x 768 RGB painting input passed through the official HINT generator; identity zero controls bypass inference. |
| Mask constraints | Single-channel binary missing-region mask under the approved HINT threshold policy; native 768 inference; exact outside-mask compositing; no per-case tuning. |
| Deterministic | True |
| Prompt dependent | False |
| Hardware statement | Executed in float32 on the recorded RTX 3060 Laptop GPU; the project does not claim a universal minimum VRAM threshold. |

The project used a fixed predeclared configuration and exact outside-mask compositing policy where applicable. Per-case metric-guided tuning was not used.

<a id="evaluated-evidence-coverage"></a>
## 6. Evaluated evidence coverage

| Coverage field | Recorded count |
|---|---:|
| Paintings | 300 |
| Unique cases | 2,620 |
| Candidates | 2,620 |
| Model-inference candidates | 2,320 |
| Identity zero controls | 300 |

Cases and repeated candidates remain nested within paintings. Candidate rows are not treated as independent artworks.

<a id="compute-and-storage"></a>
## 7. Compute and storage

| Measure | Observed result |
|---|---:|
| Total runtime | 4.5 hours |
| Mean runtime | 6.117 s |
| Median runtime | 6.677 s |
| p95 runtime | 7.851 s |
| Failed candidates | 0 |
| Failure rate | 0.00% |
| Retries | 0 |
| Throughput | 0.1635 candidates/second |
| Candidate multiplier | 1.0000 candidates per evaluated case |
| Recorded peak GPU allocation | not applicable |
| Recorded total GPU memory | not applicable |
| Output files | 2,626 |
| Output storage | 1.79 GiB |

**Conclusion:** These measurements describe the recorded workstation and software environment. They are project evidence, not universal hardware benchmarks.

<a id="quality-evidence"></a>
## 8. Quality evidence

Applicable population: `core_three_model` (2620 cases nested within 300 paintings).

| Validated anchor | Restored mean | Rank | Winner |
|---|---:|---:|---|
| classical_masked_mae | 19.155 | 3 | lama |
| colour_masked_delta_e | 8.961 | 3 | lama |
| feature_clip_crop | 0.9257 | 3 | lama |
| feature_dino_crop | 0.81558 | 3 | lama |
| perceptual_crop_lpips | 0.17476 | 2 | lama |
| seam_boundary_gradient | 0.0092329 | 3 | lama |
| semantic_local_dino | 0.7132 | 2 | lama |
| spatial_masked_error | 19.155 | 3 | lama |
| structural_affinity_correlation | 0.90167 | 2 | lama |
| structural_crop_ssim | 0.8168 | 3 | opencv_telea |
| texture_crop_p95 | 1.2739 | 3 | lama |

The method won 0 of 11 validated anchors in this population. Its strongest displayed anchor was `perceptual_crop_lpips`.

**Conclusion:** Better or worse language applies only to the named anchor and population. Runtime is not included in the quality vote, and the anchor count is not a universal quality score.

<a id="determinism-robustness-and-uncertainty"></a>
## 9. Determinism, robustness, and uncertainty

HINT is deterministic under the evaluated fixed-checkpoint contract. Robustness and sensitivity are the relevant reliability constructs; repeated-seed generative uncertainty is not applicable.

Low variability or deterministic repetition does not prove that a reconstructed region is correct.

<a id="scalability"></a>
## 10. Scalability

| Scenario | Candidate outputs | Central runtime projection | Output-storage projection |
|---|---:|---:|---:|
| projected_600_current_design_mix | 5,240 | 8.8 hours | 3.57 GiB |
| projected_300_sdxl_full_design | not applicable | not applicable | not applicable to this model-specific projection scenario |

Raw observed median, mean, and p95 runtimes are retained in the compute table. The displayed sensitivity envelope uses the smaller of scaled median and mean as its lower value, scaled mean as its central value, and the larger of scaled p95 and mean as its upper value. These are not confidence intervals. The controlled 300-painting study was executed; only rows explicitly labelled as projections are extrapolations.

<a id="strengths-and-weaknesses"></a>
## 11. Strengths and weaknesses

Strengths:

- deterministic learned transformer family distinct from LaMa
- native 768 x 768 execution under the validated adapter
- full controlled-300 coverage

Weaknesses:

- general-scene rather than painting-specific training
- no prompt or repeated-seed uncertainty mechanism
- plausible structure may remain historically unsupported

Known project limitations:

- Runtime and memory observations describe one recorded local workstation and software environment.
- The controlled 300-painting values are executed observations; only the explicitly labelled 600-painting and full-design SDXL values are projections.
- Projected storage covers notebook-owned output artifacts and excludes model caches, environments, Git history, and downstream metric outputs.
- SDXL scheduled 35 bounded cases across 30 paintings; 24 completed, one timed out and ten were skipped under the declared budget, so it cannot support a full-scope ranking.
- LaMa per-case runtime includes transparent allocation from IOPaint batch wall-clock measurements.
- Quality-anchor wins are descriptive validated Notebook 21 evidence, not a universal quality or conservation score.
- HINT was trained on Places2 rather than conservation-restoration paintings.
- A plausible completion is not evidence of historical authenticity or conservation suitability.
- The deterministic run measures one fixed checkpoint and configuration, not model-family uncertainty.
- Eligible synthetic-degradation cases are supplementary masked-removal diagnostics.
- Runtime measurements describe the recorded local hardware and are not universal benchmarks.

<a id="human-decision-support-interpretation"></a>
## 12. Human decision-support interpretation

The method can generate and prioritize digital candidates for structured inspection. Reviewers should examine repaired structure, local texture, colour continuity, seams, uncertainty where applicable, and disagreements between evidence families.

**Decision statement:** This card supports transparent method selection and review planning. It does not approve physical treatment, establish historical truth, or replace expert conservation judgement.

<a id="reproducibility-and-provenance"></a>
## 13. Reproducibility and provenance

| Field | Recorded value |
|---|---|
| Producer notebook | `30_model_cards_compute_and_scalability.ipynb` |
| Candidate producer | Notebook 12A |
| Quality producer | Notebook 21 |
| Compute schema | `compute_scalability.v1` |
| Model-card schema | `model_cards.v1` |
| Source review date | 2026-09-02T00:00:00Z |

Primary and runtime sources:

- https://github.com/ChrisChen1023/HINT

### Final scoped verdict

HINT added a deterministic mask-aware transformer family with complete controlled-300 coverage, extending the learned comparison beyond LaMa's convolutional design. This conclusion remains limited to the controlled evidence and the recorded compute environment.
