# Reproducibility Appendix

**Notebook:** `36_supervisor_publication_reproducibility_package.ipynb`  
**Snapshot generated:** `2026-09-03T21:13:25Z`  
**Dataset:** `controlled_50` version `1.0.0`  
**Scientific role:** packaging and traceability only; no new scientific evidence is created.

## 1. Reproducibility boundary

This appendix records how the completed evidence was produced and how it can be audited.

The portable Notebook 36 package is a **review bundle**, not a complete executable clone of the repository. It contains validated reports, figures, compact tables, model cards, evaluation configurations, environment declarations, manifests, application entry points, and provenance.

A full experimental rerun additionally requires:

- the repository notebooks and helper modules;
- the controlled source paintings and metadata;
- dataset, preprocessing, mask, and experiment configurations;
- locally available model weights or caches;
- sufficient storage and compatible CPU or GPU hardware.

The package republishes validated evidence. It does not rerun restoration inference or recompute metrics.

## 2. Recommended reproduction sequence

1. Check out the repository at the recorded Git revision.
2. Create Python 3.11 or 3.12 environments as appropriate.
3. Install `requirements_experiments.txt` for notebook reproduction.
4. Confirm the controlled dataset configuration and raw image availability.
5. Run Notebooks 01–36 in numeric order.
6. Clear only the current notebook's owned output directory before a complete rerun.
7. Inspect each notebook's validation table and run manifest before continuing.
8. Refresh `outputs/inventory/` after the final validated notebook.
9. Use `requirements.txt` for the read-only Streamlit dashboard.
10. Do not interpret a successful run as conservation approval.

## 3. Dataset identity

- Dataset ID: **painting_restoration_eval**
- Dataset version: **1.0.0**
- Dataset scope: **controlled_50**
- Expected paintings: **50**
- Configuration schema: `dataset_config.v1`
- Configuration path: `config/datasets/controlled_50.yaml`
- Configuration SHA-256: `5568dd93bf606d627e791ff52c2c6c2af3b8a06bfd94f0a78e2a8d245fc86345`

This identity refers to the controlled 50-painting collection. It does not claim coverage of real conservation treatments or unseen museum collections.

## 4. Recorded Git and runtime state

- Git commit before the final Notebook 36 commit: `ba720c143b74179ceafa2264cd1d9808bfc48944`
- Git branch: `main`
- Git dirty state during notebook execution: `True`
- Git inspection error: `none`
- Python: `CPython 3.12.6`
- Accepted project Python minors: `3.11, 3.12`
- Platform: `Windows-11-10.0.26200-SP0`
- Machine: `AMD64`

A dirty state is expected while the current notebook and its outputs are awaiting the user's final commit. The final repository commit should be recorded separately after validation.

## 5. Model identities and revisions

| Model | Evaluation status | Implementation | Version | Identifier | Revision | Configuration | Primary seed | Device | Precision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LaMa | fully_evaluated | IOPaint CLI model=lama | 1.6.0 | big-lama.pt | iopaint_lama_default | lama_iopaint_masked_composite_v1 | not_applicable | cuda | float32 |
| OpenCV Telea | fully_evaluated | OpenCV cv2.INPAINT_TELEA | 4.11.0 | cv2.INPAINT_TELEA | opencv-4.11.0 | opencv_telea_r3_threshold_policy_v1 | not_applicable | cpu | uint8 |
| SDXL Inpainting | partial_evaluation | Diffusers StableDiffusionXLInpaintPipeline | 3.0.0 | diffusers/stable-diffusion-xl-1.0-inpainting-0.1 | 115134f363124c53c7d878647567d04daf26e41e | sdxl_quality_preserving_partial_evaluation_v1 | 2026 | cuda | float16 |
| Stable Diffusion Inpainting | fully_evaluated | Diffusers StableDiffusionInpaintPipeline | 1.0.0 | stable-diffusion-v1-5/stable-diffusion-inpainting | 8a4288a76071f7280aedbdb3253bdb9e9d5d84bb | sd15_inpaint_fixed_policy_v1 | 2026 | cuda | float16 |

### Interpretation

- OpenCV Telea and LaMa are deterministic under their fixed project contracts.
- Stable Diffusion uses a fixed primary seed and repeated-seed subsets for uncertainty analysis.
- SDXL uses one seed across ten bounded feasibility cases and has no empirical repeated-seed uncertainty estimate.
- Model revision identifiers improve traceability but do not guarantee byte-identical GPU results across hardware and software stacks.

## 6. Seed policies

| Scope | Model | Seed or seeds | Policy |
| --- | --- | --- | --- |
| OpenCV Telea benchmark | opencv_telea | not applicable | deterministic classical algorithm |
| LaMa benchmark | lama | not applicable | deterministic learned baseline |
| Stable Diffusion primary comparison | stable_diffusion_inpainting | 2026 | fixed primary candidate seed |
| Canonical Stable Diffusion uncertainty | stable_diffusion_inpainting | 2026, 2027, 2028, 2029 | four exact seeds per eligible group |
| Damage-size Stable Diffusion uncertainty | stable_diffusion_inpainting | 2026, 2027, 2028, 2029 | seed 2026 reused as the frozen anchor; 2027–2029 generated by Notebook 22 |
| SDXL bounded feasibility | sdxl_inpainting | 2026 | one fixed seed per selected feasibility case |

Repeated seeds are nested observations within paintings and cases. They must not be counted as independent paintings.

## 7. Observed compute evidence

| Model | Candidates | Completed | Total seconds | Median seconds | P95 seconds | Applicability |
| --- | --- | --- | --- | --- | --- | --- |
| LaMa | 410.0 | 410.0 | 655.093 | 1.567 | 2.395 | applicable_executed |
| OpenCV Telea | 410.0 | 410.0 | 185.614 | 0.424 | 0.698 | applicable_executed |
| SDXL Inpainting | 10.0 | 10.0 | 3784.687 | 294.916 | 595.271 | applicable_executed |
| Stable Diffusion Inpainting | 1330.0 | 1330.0 | 12269.501 | 9.535 | 10.149 | applicable_executed |

These are recorded upstream observations from the local execution environment. They are not universal speed benchmarks. Any 300-painting scalability values elsewhere in the project are transparent projections rather than executed experiments.

## 8. Environment declarations

| Environment file | Bytes | SHA-256 |
| --- | --- | --- |
| requirements.txt | 107 | 0d66b4c3bb24e5c03647df89121bd50e76167d6cde0970c027b4545bf660638f |
| requirements_experiments.txt | 848 | fca385c534df4623f15d058f5b7d188034a6aeb01add4bb0b13aeca6b366dfa5 |

The dashboard environment and experiment environment are intentionally separated. The exact tested Notebook 35 dashboard environment contained four dependency-version differences from the deployment pins; despite those differences, all eight pages passed the local runtime smoke test.

### Packages observed in the Notebook 36 kernel

| Package | Recorded notebook environment | Status |
| --- | --- | --- |
| Pillow | 9.5.0 | installed |
| PyYAML | 6.0.3 | installed |
| accelerate | 1.14.0 | installed |
| diffusers | 0.27.2 | installed |
| iopaint | 1.6.0 | installed |
| jmespath | 1.1.0 | installed |
| lpips | 0.1.4 | installed |
| matplotlib | 3.11.0 | installed |
| numpy | 1.26.4 | installed |
| opencv-python | 4.11.0.86 | installed |
| pandas | 2.3.3 | installed |
| plotly | 6.8.0 | installed |
| pyarrow | 24.0.0 | installed |
| safetensors | 0.8.0 | installed |
| scikit-image | 0.24.0 | installed |
| scipy | 1.17.1 | installed |
| streamlit | 1.59.0 | installed |
| torch | 2.5.1+cu121 | installed |
| torchvision | 0.20.1+cu121 | installed |
| transformers | 4.48.3 | installed |

An installed version of `not_installed` means the package was not required for this packaging notebook. It does not imply that the package was absent from the environment used by its producing notebook.

## 9. Configuration and manifest traceability

- Bundled evaluation configurations: **25**
- Indexed source configurations: **13**
- Upstream run manifests: **35**
- Completed upstream gates: **35 of 35**
- Upstream blocking failures: **0**
- Upstream warning failures: **1**

The 25 bundled YAMLs are the approved `config/evaluation` snapshots. The 13 indexed source configurations record the dataset, preprocessing, canonical mask, and current experiment contracts needed by a full repository rerun. Their paths and SHA-256 checksums are retained in the reproducibility snapshot.

## 10. Hardware record

The model cards retain the observed execution hardware:

- **OpenCV Telea:** CPU execution.
- **LaMa:** NVIDIA GeForce RTX 3060 Laptop GPU using CUDA and IOPaint.
- **Stable Diffusion:** NVIDIA GeForce RTX 3060 Laptop GPU using CUDA and float16 Diffusers inference.
- **SDXL:** the same 6 GB laptop GPU with model CPU offload.

These observations document the completed runs. They do not establish universal minimum hardware requirements.

## 11. Dashboard reproduction

From the repository root:

```text
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

The dashboard reads the fixed Notebook 34 presentation package. The Notebook 36 portable review bundle includes the application entry point and helper for inspection, but it does not duplicate the complete Notebook 34 dashboard asset collection.
Notebook 35 validated all eight pages for local demonstration. No completed public deployment URL is recorded.

## 12. Verification route

A reviewer can verify the package by:
    1. reading the package manifest;
    2. comparing the declared file count and byte count with disk;
    3. recalculating individual SHA-256 values;
    4. checking the package-tree checksum;
    5. confirming that all five HTML reports are self-contained;
    6. checking all 35 upstream run manifests;
    7. reviewing the limitations and intentional omissions;
    8. tracing an indexed artifact back to its canonical repository-relative path.

## 13. Interpretation boundary

Reproducibility means that inputs, configurations, versions, seeds, outputs, and known deviations are recorded transparently.

It does not mean that:
- GPU diffusion results are guaranteed to be byte-identical on every machine;
- synthetic damage represents every real conservation condition;
- metric agreement establishes historical correctness;
- uncertainty is calibrated confidence;
- computational flags are expert ground truth;
- a model output is approved for conservation treatment.
  