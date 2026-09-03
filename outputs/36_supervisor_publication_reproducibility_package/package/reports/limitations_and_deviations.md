# Limitations and Deviations

**Notebook:** `36_supervisor_publication_reproducibility_package.ipynb`  
**Recorded:** `2026-09-03T21:13:25Z`  
**Purpose:** Keep the limits of the final evidence visible.

## 1. Controlled synthetic scope

The study uses **50 paintings** and controlled synthetic damage. This supports repeatable comparison because a clean reference is available.

It does not establish performance on naturally aged, physically damaged, previously restored, or materially complex paintings. Results remain bounded to the evaluated collection and damage contracts.

## 2. Statistical independence

Paintings—not candidate rows—are the independent unit for grouped inference.

Repeated models, seeds, regions, masks, prompts, and damage levels remain nested within paintings or cases. These repeated observations are **not independent paintings**. Treating all **1,785 candidates** as independent paintings would overstate the evidence.

## 3. Metric limits

The framework intentionally keeps metric families and regions separate.

- Reference metrics measure pixel or structural similarity to the controlled clean image.
- LPIPS measures learned perceptual distance.
- CLIP and DINOv2 provide general feature-affinity evidence.
- Texture, colour, and seam metrics are diagnostic proxies.
- Semantic similarity is not historical authenticity.
- No universal combined score is reported.

A model can perform well on one metric while performing poorly on another. One metric must not be treated as a complete definition of restoration quality.

## 4. Model-specific limits

### OpenCV Telea

Telea is fast, deterministic, and effective for some thin or local regions. It has no semantic understanding and is not expected to reconstruct large missing structures faithfully.

### LaMa

LaMa is the strongest general benchmark baseline in this controlled study, leading **10 of 11 quality anchors**.

Its learned priors can still smooth texture or create plausible but unsupported structure. The exact licence of the downloaded converted weight artifact was not separately verified by the project.

### Stable Diffusion

Stable Diffusion produces prompt-conditioned candidates rather than historically verified reconstructions. It is more variable across metrics and seeds, and thin scratch geometry remains difficult even after the scratch-aware prompt ablation.

The **1,330 executed candidates** include supporting prompt and repeated-seed evidence. The comparative catalog retains **955 approved Stable Diffusion candidates**.

### SDXL

SDXL is a **ten-case feasibility study**, not a fourth complete benchmark. It is much slower on the recorded hardware, covers five paintings, and has only one seed per case.

## 5. Uncertainty limits

The **165 repeated-seed groups** measure empirical Stable Diffusion variability:

- 130 canonical groups;
- 35 damage-size groups;
- four seeds per group.

This is an inspection signal, **not calibrated confidence**. Low variability can occur when all candidates are consistently wrong. High variability does not by itself prove that every candidate is unusable.

Telea and LaMa are deterministic under their fixed contracts. Their input variation is therefore described as robustness or sensitivity rather than generative uncertainty.

## 6. Trustworthiness and explainability limits

Computational flags, counterfactuals, neighbours, saliency-style evidence, and spatial maps help identify where closer review is needed.

They are **not expert ground truth**.

The **1,703 of 1,785 candidates** receiving conservative review guidance should not be described as 1,703 objectively failed restorations. The rules are intentionally cautious and require expert interpretation.

Retrieval neighbours provide visual or semantic context. They do not prove that a restoration is correct.

## 7. Hardware and software deviations

- Notebook 36 ran under Python `3.12.6`.
- Python 3.11 remains the recommended fresh environment.
- Python 3.11 and 3.12 are both accepted by the project contract.
- Notebook 35 tested Streamlit `1.59.0`, while the deployment pin is `1.56.0`.
- Pillow, Plotly, PyArrow, and Streamlit differed from the declared Notebook 35 deployment pins.
- All eight dashboard pages nevertheless passed the recorded local smoke test.
- CUDA inference may not be byte-identical across GPUs, drivers, CUDA versions, or library builds.
- Observed runtimes describe one local workstation and are not universal benchmarks.

These are transparent reproducibility deviations, not hidden validation passes.

## 8. Deployment status

The Streamlit application is ready for local supervisor demonstration.

Public deployment is **not completed**. No external platform or public URL is recorded, so the project must not claim completed public availability.

## 9. Portable-package boundary

The portable package bundles compact material required for efficient review. Large or redundant collections are **indexed but not bundled**, including:

- all restoration candidates;
- raw and processed painting images;
- complete difference-map and uncertainty-map collections;
- 30 case reports and 50 painting reports;
- 30 selected-case grids;
- the complete Notebook 34 dashboard visual collection;
- model weights and local caches;
- the full executable notebook repository;
- dataset, preprocessing, mask, and experiment YAML files outside `config/evaluation`.

The reproducibility snapshot records canonical paths and checksums for critical source configurations. A full experimental rerun still requires the repository and its input data.

## 10. Compute and scalability boundary

Observed runtime and storage values come from the completed local runs.

Any 300-painting scalability scenario is a linear projection. It is not an executed experiment, performance guarantee, confidence interval, or cloud-cost estimate.

## 11. Conservation boundary

The project does not:

- authenticate artworks;
- establish original artistic intent;
- verify historical reconstruction;
- prescribe physical conservation treatment;
- replace conservator review;
- provide automatic approval for restored candidates.

Visual plausibility is not the same as restoration trustworthiness.

## 12. Final limitation conclusion

The evidence supports a transparent, region-aware, multi-metric comparison of selected pretrained methods under controlled synthetic damage.

It does not support universal model ranking, real-world conservation generality, calibrated confidence, automatic acceptance, or conservation approval.
