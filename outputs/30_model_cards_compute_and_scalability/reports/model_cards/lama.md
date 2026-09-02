# LaMa - Model Card and Compute Audit

**Evaluation status:** Fully Evaluated  
**Method role:** learned deterministic inpainting baseline  
**Dataset scope:** controlled_50  
**Decision boundary:** Digital restoration candidate method, not a conservation authority

<a id="at-a-glance"></a>
## 1. At a glance

LaMa provided the strongest broad reference-based baseline under the validated full-scope anchor policy.

- Completed candidates: **410 of 410**.
- Mean runtime: **1.60 seconds per candidate**.
- Observed notebook-owned storage: **284.69 MiB**.
- Validated anchor wins in the applicable population: **10 of 11**.

**Conclusion:** The compute and quality evidence support this method only within its declared evaluation scope. Anchor wins are descriptive Notebook 21 outcomes, not a combined quality score or conservation verdict.

<a id="identity-and-provenance"></a>
## 2. Identity and provenance

| Field | Recorded value |
|---|---|
| Model ID | `lama` |
| Family | learned fourier convolution inpainting |
| Original purpose | Resolution-robust large-mask image inpainting using Fourier convolutions. |
| Project implementation | IOPaint CLI model=lama |
| Implementation version | 1.6.0 |
| Model identifier | `big-lama.pt` |
| Model revision | `iopaint_lama_default` |
| Software licence | Apache-2.0_method_and_runtime_code |
| Weight licence | not_separately_verified_in_project_sources |

The LaMa and IOPaint code are Apache-2.0; the downloaded Big-LaMa weight artifact is not assigned a separate project-verified licence claim.

<a id="intended-and-unsupported-use"></a>
## 3. Intended and unsupported use

Appropriate project uses:

- learned large-mask inpainting baseline
- controlled digital restoration candidate generation
- quality and robustness comparison against classical and diffusion methods

Unsupported uses:

- historically verified reconstruction
- artist authentication or semantic brushstroke recognition
- conservation approval

<a id="training-data-and-domain-gap"></a>
## 4. Training data and painting-domain gap

Official LaMa documentation describes Places365/Places-based training; the exact IOPaint-converted checkpoint-to-training-run mapping is not independently verified here.

**Training-data transparency status:** partial

**Domain gap:** General-scene inpainting training does not establish painting-specific or conservation-specific competence.

**Bias and risk:** Learned priors may smooth texture or synthesize plausible but unsupported structures.

**Conclusion:** Source transparency and general-image performance do not establish painting-specific historical or conservation competence.

<a id="project-implementation"></a>
## 5. Project implementation

| Setting | Recorded value |
|---|---|
| Configuration | `lama_iopaint_masked_composite_v1` |
| Device | cuda |
| Backend | iopaint |
| Recorded accelerator | NVIDIA GeForce RTX 3060 Laptop GPU |
| Precision | float32 |
| Inference resolution | 768 x 768 |
| Output resolution | 768 x 768 |
| Input constraints | Normalized 768 x 768 RGB painting input passed through the pinned IOPaint LaMa runtime; identity zero controls bypass inference. |
| Mask constraints | Single-channel binary missing-region mask using threshold 128; exact outside-mask compositing; no per-case tuning. |
| Deterministic | True |
| Prompt dependent | False |
| Hardware statement | Executed with CUDA on the recorded RTX 3060 Laptop GPU; no experimentally validated minimum VRAM threshold is claimed. |

The project used a fixed predeclared configuration and exact outside-mask compositing policy where applicable. Per-case metric-guided tuning was not used.

<a id="evaluated-evidence-coverage"></a>
## 6. Evaluated evidence coverage

| Coverage field | Recorded count |
|---|---:|
| Paintings | 50 |
| Unique cases | 410 |
| Candidates | 410 |
| Model-inference candidates | 360 |
| Identity zero controls | 50 |

Cases and repeated candidates remain nested within paintings. Candidate rows are not treated as independent artworks.

<a id="compute-and-storage"></a>
## 7. Compute and storage

| Measure | Observed result |
|---|---:|
| Total runtime | 10.9 minutes |
| Mean runtime | 1.598 s |
| Median runtime | 1.567 s |
| p95 runtime | 2.395 s |
| Failed candidates | 0 |
| Failure rate | 0.00% |
| Retries | 0 |
| Throughput | 0.6259 candidates/second |
| Candidate multiplier | 1.0000 candidates per evaluated case |
| Recorded peak GPU allocation | not applicable |
| Recorded total GPU memory | not applicable |
| Output files | 416 |
| Output storage | 284.69 MiB |

**Conclusion:** These measurements describe the recorded workstation and software environment. They are project evidence, not universal hardware benchmarks.

<a id="quality-evidence"></a>
## 8. Quality evidence

Applicable population: `core_three_model` (410 cases nested within 50 paintings).

| Validated anchor | Restored mean | Rank | Winner |
|---|---:|---:|---|
| classical_masked_mae | 14.537 | 1 | lama |
| colour_masked_delta_e | 6.931 | 1 | lama |
| feature_clip_crop | 0.95654 | 1 | lama |
| feature_dino_crop | 0.87159 | 1 | lama |
| perceptual_crop_lpips | 0.1251 | 1 | lama |
| seam_boundary_gradient | 0.0064142 | 1 | lama |
| semantic_local_dino | 0.79993 | 1 | lama |
| spatial_masked_error | 14.537 | 1 | lama |
| structural_affinity_correlation | 0.95578 | 1 | lama |
| structural_crop_ssim | 0.8704 | 2 | opencv_telea |
| texture_crop_p95 | 0.43333 | 1 | lama |

The method won 10 of 11 validated anchors in this population. Its strongest displayed anchor was `classical_masked_mae`.

**Conclusion:** Better or worse language applies only to the named anchor and population. Runtime is not included in the quality vote, and the anchor count is not a universal quality score.

<a id="determinism-robustness-and-uncertainty"></a>
## 9. Determinism, robustness, and uncertainty

LaMa is deterministic under the evaluated contract. Mask robustness and damage sensitivity are the relevant reliability constructs; repeated-seed generative uncertainty is not applicable.

Low variability or deterministic repetition does not prove that a reconstructed region is correct.

<a id="scalability"></a>
## 10. Scalability

| Scenario | Candidate outputs | Central runtime projection | Output-storage projection |
|---|---:|---:|---:|
| projected_300_canonical_primary | 1,500 | 33.2 minutes | 1,023.50 MiB |
| projected_300_current_design_mix | 2,460 | 65.5 minutes | 1.63 GiB |

Raw observed median, mean, and p95 runtimes are retained in the compute table. The displayed sensitivity envelope uses the smaller of scaled median and mean as its lower value, scaled mean as its central value, and the larger of scaled p95 and mean as its upper value. These are not confidence intervals. No 300-painting experiment was executed.

<a id="strengths-and-weaknesses"></a>
## 11. Strengths and weaknesses

Strengths:

- broad learned context
- practical large-mask baseline
- deterministic under the evaluated contract

Weaknesses:

- general-scene rather than painting-specific training
- possible texture smoothing
- plausible content may remain historically incorrect

Known project limitations:

- Runtime and memory observations describe one recorded local workstation and software environment.
- The 300-painting values are transparent linear projections, not executed experiments.
- Projected storage covers notebook-owned output artifacts and excludes model caches, environments, Git history, and downstream metric outputs.
- SDXL has ten completed candidates nested within five paintings and cannot support a full-scope ranking.
- LaMa per-case runtime includes transparent allocation from IOPaint batch wall-clock measurements.
- Quality-anchor wins are descriptive validated Notebook 21 evidence, not a universal quality or conservation score.
- LaMa produces plausible learned inpainting, not historically verified reconstruction.
- IOPaint batch execution exposes group wall-clock runtime; per-case inference runtimes are transparently allocated estimates.
- The fixed model and mask policies are not tuned per painting or per damage case.
- Eligible synthetic-degradation cases are supplementary masked-removal diagnostics and remain separate from missing-content claims.
- Exact model-weight provenance depends on the locally resolved IOPaint cache artifact and is recorded when discoverable.
- CUDA inference is evaluated for tightly bounded numerical repeatability rather than byte-identical output; the configured smoke tolerance permits at most one 8-bit channel level of deviation while outside-mask invariance remains exact.
- Runtime measurements describe the recorded hardware and software environment and are not universal benchmarks.

<a id="human-decision-support-interpretation"></a>
## 12. Human decision-support interpretation

The method can generate and prioritize digital candidates for structured inspection. Reviewers should examine repaired structure, local texture, colour continuity, seams, uncertainty where applicable, and disagreements between evidence families.

**Decision statement:** This card supports transparent method selection and review planning. It does not approve physical treatment, establish historical truth, or replace expert conservation judgement.

<a id="reproducibility-and-provenance"></a>
## 13. Reproducibility and provenance

| Field | Recorded value |
|---|---|
| Producer notebook | `30_model_cards_compute_and_scalability.ipynb` |
| Candidate producer | Notebook 10 |
| Quality producer | Notebook 21 |
| Compute schema | `compute_scalability.v1` |
| Model-card schema | `model_cards.v1` |
| Source review date | 2026-09-02T00:00:00Z |

Primary and runtime sources:

- https://github.com/advimman/lama
- https://github.com/Sanster/IOPaint/blob/main/iopaint/model/lama.py
- https://github.com/Sanster/IOPaint

### Final scoped verdict

LaMa provided the strongest broad reference-based baseline under the validated full-scope anchor policy. This conclusion remains limited to the controlled evidence and the recorded compute environment.
