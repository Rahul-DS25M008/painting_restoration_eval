# SDXL feasibility report

## Decision

Validated availability state: **`feasibility_only`**.

Notebook 12 remains a feasibility audit. It does not create SDXL candidate rows,
restoration manifests, or placeholder metric rows. The result is evidence about
practical execution on the recorded hardware, not a ranking of SDXL restoration quality.

## Current quality-oriented probe

- Status: `completed`
- Failure classification: `none`
- Runtime including model loading: 694.1 seconds
- Guardrail: 1500 seconds, enforced around an isolated worker
- Model: `diffusers/stable-diffusion-xl-1.0-inpainting-0.1` at revision `115134f363124c53c7d878647567d04daf26e41e`
- Configuration: 768 x 768, 30 steps, guidance 7.5, strength 1.0, seed 2026
- Memory strategy: `sdxl_model_cpu_offload_sdpa_vae_slicing_tiling.v1`
- Technical validation passed: `True`
- Error: none

## Runtime projection

Approximately 79.0 hours for 410 primary cases and 194.7 hours for 1,010 comparable candidates.

The projection is a simple wall-clock extrapolation from one probe and includes
one-time model loading, so it is deliberately conservative and is not a benchmark.

## Environment

- Hardware: cuda_available=True, gpu_name=NVIDIA GeForce RTX 3060 Laptop GPU, gpu_peak_memory_bytes=5632166912, gpu_peak_memory_fraction=0.8743, gpu_total_memory_bytes=6441926656, gpu_total_memory_gib=6.0
- Packages: Pillow 9.5.0, PyYAML 6.0.3, accelerate 1.14.0, diffusers 0.27.2, pandas 2.3.3, python 3.12.6, safetensors 0.8.0, torch 2.5.1+cu121, transformers 4.48.3

## Legacy context

The deleted pre-refactor Notebook 25 is retained only through commit
`7a99ceb4` as contextual evidence:

- `legacy_512px_6_step_probe`: 267.4 seconds; completed but region completion was insufficient.
- `legacy_512px_12_step_probe`: 594.0 seconds; completed but hallucination and global alteration were observed.

These observations are not included as current attempt rows and are not used to
claim that SDXL is intrinsically poor. They show that reduced-step 512 px probes
either under-filled the region or introduced visible unrelated changes.

## Interpretation and downstream contract

### Single-case technical and visual audit

The following observations apply only to the one predeclared case
`canonical__p039__loss_large`:

- The worker produced a valid 768 x 768 RGB result.
- The canonical missing region contains 49,001 pixels.
- Pixels changed outside the approved mask: 0.
- Fraction of masked pixels changed from the damaged input: 1.000000.
- Mean within-mask channel standard deviation: 50.937911.
- Peak allocated GPU-memory fraction: 0.8743.
- Temporary restoration SHA-256: `1f94c2292693a96638ddfeabfc1272a8b075958460af1a18c9b36188b713187f`.
- The missing region was filled with nonconstant generated content.
- The generated pale geometric forms do not reconstruct the clean
  reference's flower and internal structures.
- Local shape and tonal discontinuities remain visibly apparent.

These observations confirm technical execution and exact compositing for
one case. They cannot support model-level fidelity, historical-correctness,
artist-intent, or conservation-suitability claims.

- A timeout or CUDA out-of-memory event is classified as a hardware/runtime limitation.
- No automatic retry, CPU fallback, lower resolution, or lower step count is attempted.
- Notebooks 13-35 must include SDXL only when a future validated run reports
  `full_evaluation_complete` or an explicitly supported `partial_evaluation`.
- The present `feasibility_only` state therefore excludes SDXL from unified metric computation.

## Limitations

- The feasibility branch evaluates whether the pinned SDXL inpainting implementation is practical on the available hardware; it is not a model-quality benchmark.
- A timeout or CUDA out-of-memory failure is hardware/runtime evidence and must not be interpreted as poor restoration quality.
- One predeclared case cannot characterize SDXL output quality, robustness, or stochastic uncertainty.
- The 25-minute guardrail includes model loading and inference and intentionally prevents automatic retries or slower fallback strategies.
- Full candidates, restored-image manifests, and metric placeholder rows are prohibited in feasibility-only mode.
