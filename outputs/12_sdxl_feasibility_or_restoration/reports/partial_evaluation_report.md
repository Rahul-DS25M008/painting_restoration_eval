# SDXL bounded partial-evaluation report

## Decision

Validated availability state: **`partial_evaluation`**.

The notebook predeclared ten cases nested within five paintings, used one generic
prompt and seed 2026, and enforced a 7,200-second global budget plus a 900-second
per-case watchdog. This is a purposive partial evaluation, not a full SDXL branch.

## Execution result

- Scheduled rows: 10
- Technically valid completed rows: 10
- Status counts: `{'completed': 10}`
- Runtime: 3784.7 seconds total; median 294.9 seconds
- Persistent pipeline: `True`
- Automatic retries: `False`
- Environment: cuda_available=True, gpu_name=NVIDIA GeForce RTX 3060 Laptop GPU, gpu_peak_memory_bytes=5632166912, gpu_total_memory_bytes=6441926656, requested_device=cuda
- Packages: accelerate 1.14.0, cuda_runtime 12.1, diffusers 0.27.2, matplotlib 3.11.0, numpy 1.26.4, pandas 2.3.3, pillow 9.5.0, python 3.12.6, pyyaml 6.0.3, safetensors 0.8.0, torch 2.5.1+cu121, transformers 4.48.3

Only completed rows with exact output geometry and zero changed pixels outside
the binary mask are eligible for downstream metrics. Timeout, out-of-memory,
and budget omissions are runtime evidence, never restoration-quality failures.

## Statistical boundary

The independent unit is the painting (n=5). The two cases per painting are
nested observations and must not be presented as ten independent paintings.
No population-level SDXL claim is supported by this purposive scope.

## Limitations

- The ten cases are a predeclared purposive partial scope and do not represent a full SDXL evaluation.
- The ten case observations are nested within five paintings; downstream inference must treat painting as the independent unit.
- A timeout or CUDA out-of-memory failure is hardware/runtime evidence and must not be interpreted as poor restoration quality.
- Only technically validated completed candidates may enter downstream metric computation.
- The global two-hour budget can leave later scheduled cases explicitly unexecuted.
- SDXL outputs are plausible prompt-conditioned inpaintings, not historically verified reconstructions or conservation recommendations.

## Descriptive visual-review boundary

The notebook renders every completed case using the clean reference, damaged
input, active restoration region, and technically validated SDXL output.

A preliminary descriptive inspection identified visible prompt-conditioned
substitutions or hallucinated content in several broad-mask cases, together
with persistent seams, lines, or speckling in some sparse-mask cases. These
observations are retained as restoration-quality evidence rather than treated
as pipeline failures.

No subjective quality score, historical-authenticity claim, or conservation
recommendation is assigned in this notebook. Formal metric computation and
expert or structured human review remain downstream tasks.
