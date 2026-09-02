# OpenCV Telea - Model Card and Compute Audit

**Evaluation status:** Fully Evaluated  
**Method role:** classical deterministic baseline  
**Dataset scope:** controlled_50  
**Decision boundary:** Digital restoration candidate method, not a conservation authority

<a id="at-a-glance"></a>
## 1. At a glance

OpenCV Telea was the fastest and most reproducible baseline, while its local interpolation remained limited for semantically demanding missing regions.

- Completed candidates: **410 of 410**.
- Mean runtime: **0.45 seconds per candidate**.
- Observed notebook-owned storage: **287.49 MiB**.
- Validated anchor wins in the applicable population: **1 of 11**.

**Conclusion:** The compute and quality evidence support this method only within its declared evaluation scope. Anchor wins are descriptive Notebook 21 outcomes, not a combined quality score or conservation verdict.

<a id="identity-and-provenance"></a>
## 2. Identity and provenance

| Field | Recorded value |
|---|---|
| Model ID | `opencv_telea` |
| Family | classical fast marching inpainting |
| Original purpose | Local image inpainting from the boundary of a masked region. |
| Project implementation | OpenCV cv2.INPAINT_TELEA |
| Implementation version | 4.11.0 |
| Model identifier | `cv2.INPAINT_TELEA` |
| Model revision | `opencv-4.11.0` |
| Software licence | Apache-2.0 |
| Weight licence | not_applicable_no_model_weights |

OpenCV software licence; the Telea method has no learned weights.

<a id="intended-and-unsupported-use"></a>
## 3. Intended and unsupported use

Appropriate project uses:

- classical deterministic restoration baseline
- small local damage and thin-scratch comparison
- reproducible candidate generation for controlled evaluation

Unsupported uses:

- historically verified reconstruction
- semantic reconstruction of large missing structures
- conservation approval

<a id="training-data-and-domain-gap"></a>
## 4. Training data and painting-domain gap

Not applicable; this is a classical non-learning algorithm.

**Training-data transparency status:** not applicable

**Domain gap:** No painting-specific knowledge, semantic model, or brushwork model.

**Bias and risk:** No learned training-data bias; locality and interpolation assumptions remain algorithmic biases.

**Conclusion:** Source transparency and general-image performance do not establish painting-specific historical or conservation competence.

<a id="project-implementation"></a>
## 5. Project implementation

| Setting | Recorded value |
|---|---|
| Configuration | `opencv_telea_r3_threshold_policy_v1` |
| Device | cpu |
| Backend | opencv_cpu |
| Recorded accelerator | not applicable (CPU execution) |
| Precision | uint8 |
| Inference resolution | 768 x 768 |
| Output resolution | 768 x 768 |
| Input constraints | Normalized 768 x 768 RGB uint8 painting input; identity zero controls bypass inference. |
| Mask constraints | Single-channel binary missing-region mask using threshold 128; fixed Telea radius 3; no per-case tuning. |
| Deterministic | True |
| Prompt dependent | False |
| Hardware statement | CPU execution; no GPU required under the evaluated contract. |

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
| Total runtime | 3.1 minutes |
| Mean runtime | 0.453 s |
| Median runtime | 0.424 s |
| p95 runtime | 0.698 s |
| Failed candidates | 0 |
| Failure rate | 0.00% |
| Retries | 0 |
| Throughput | 2.2089 candidates/second |
| Candidate multiplier | 1.0000 candidates per evaluated case |
| Recorded peak GPU allocation | not applicable |
| Recorded total GPU memory | not applicable |
| Output files | 416 |
| Output storage | 287.49 MiB |

**Conclusion:** These measurements describe the recorded workstation and software environment. They are project evidence, not universal hardware benchmarks.

<a id="quality-evidence"></a>
## 8. Quality evidence

Applicable population: `core_three_model` (410 cases nested within 50 paintings).

| Validated anchor | Restored mean | Rank | Winner |
|---|---:|---:|---|
| classical_masked_mae | 17.258 | 2 | lama |
| colour_masked_delta_e | 7.858 | 2 | lama |
| feature_clip_crop | 0.88628 | 3 | lama |
| feature_dino_crop | 0.69663 | 3 | lama |
| perceptual_crop_lpips | 0.18639 | 3 | lama |
| seam_boundary_gradient | 0.0075863 | 2 | lama |
| semantic_local_dino | 0.60301 | 3 | lama |
| spatial_masked_error | 17.258 | 2 | lama |
| structural_affinity_correlation | 0.85369 | 3 | lama |
| structural_crop_ssim | 0.87224 | 1 | opencv_telea |
| texture_crop_p95 | 0.63161 | 2 | lama |

The method won 1 of 11 validated anchors in this population. Its strongest displayed anchor was `structural_crop_ssim`.

**Conclusion:** Better or worse language applies only to the named anchor and population. Runtime is not included in the quality vote, and the anchor count is not a universal quality score.

<a id="determinism-robustness-and-uncertainty"></a>
## 9. Determinism, robustness, and uncertainty

OpenCV Telea is deterministic. Its appropriate reliability evidence is input robustness and sensitivity, not generative uncertainty.

Low variability or deterministic repetition does not prove that a reconstructed region is correct.

<a id="scalability"></a>
## 10. Scalability

| Scenario | Candidate outputs | Central runtime projection | Output-storage projection |
|---|---:|---:|---:|
| projected_300_canonical_primary | 1,500 | 10.4 minutes | 1.01 GiB |
| projected_300_current_design_mix | 2,460 | 18.6 minutes | 1.65 GiB |

Raw observed median, mean, and p95 runtimes are retained in the compute table. The displayed sensitivity envelope uses the smaller of scaled median and mean as its lower value, scaled mean as its central value, and the larger of scaled p95 and mean as its upper value. These are not confidence intervals. No 300-painting experiment was executed.

<a id="strengths-and-weaknesses"></a>
## 11. Strengths and weaknesses

Strengths:

- fast and deterministic
- transparent classical baseline
- low compute burden

Weaknesses:

- no semantic understanding
- limited large-mask reconstruction
- local interpolation may lose meaningful structure

Known project limitations:

- Runtime and memory observations describe one recorded local workstation and software environment.
- The 300-painting values are transparent linear projections, not executed experiments.
- Projected storage covers notebook-owned output artifacts and excludes model caches, environments, Git history, and downstream metric outputs.
- SDXL has ten completed candidates nested within five paintings and cannot support a full-scope ranking.
- LaMa per-case runtime includes transparent allocation from IOPaint batch wall-clock measurements.
- Quality-anchor wins are descriptive validated Notebook 21 evidence, not a universal quality or conservation score.
- OpenCV Telea is a local interpolation baseline and does not reconstruct historically verified content.
- A fixed radius of 3 is used without per-case tuning.
- Eligible synthetic-degradation cases are supplementary masked-removal diagnostics and must remain separate from missing-content claims.
- Runtime measurements describe the recorded CPU environment and are not universal benchmarks.

<a id="human-decision-support-interpretation"></a>
## 12. Human decision-support interpretation

The method can generate and prioritize digital candidates for structured inspection. Reviewers should examine repaired structure, local texture, colour continuity, seams, uncertainty where applicable, and disagreements between evidence families.

**Decision statement:** This card supports transparent method selection and review planning. It does not approve physical treatment, establish historical truth, or replace expert conservation judgement.

<a id="reproducibility-and-provenance"></a>
## 13. Reproducibility and provenance

| Field | Recorded value |
|---|---|
| Producer notebook | `30_model_cards_compute_and_scalability.ipynb` |
| Candidate producer | Notebook 09 |
| Quality producer | Notebook 21 |
| Compute schema | `compute_scalability.v1` |
| Model-card schema | `model_cards.v1` |
| Source review date | 2026-09-02T00:00:00Z |

Primary and runtime sources:

- https://docs.opencv.org/4.x/d7/d8b/group__photo__inpaint.html
- https://github.com/opencv/opencv

### Final scoped verdict

OpenCV Telea was the fastest and most reproducible baseline, while its local interpolation remained limited for semantically demanding missing regions. This conclusion remains limited to the controlled evidence and the recorded compute environment.
