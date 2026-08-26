# Notebook 12 SDXL bounded partial-evaluation contract

## Status and purpose

This document freezes the approved refactor contract for
`notebooks/12_sdxl_feasibility_or_restoration.ipynb`.

Notebook 12 produces a reusable but explicitly partial SDXL branch. It is not a
full-dataset evaluation, a population sample, or evidence that omitted cases
failed restoration. Its scientific contribution is a transparent comparison
asset under strict runtime limits.

The machine-readable authority is `config/experiments/sdxl.yaml`
(`sdxl_config.v2`). This document explains that contract in human-readable
form. The final notebook roadmap and refactoring implementation guidelines
remain controlling repository-wide documents.

## Frozen scope

The independent unit is the painting. Five paintings are represented, each by
two nested cases. The ten case rows must not be analyzed as ten independent
paintings.

| Selection rank | Execution order | Case ID | Family |
|---:|---:|---|---|
| 1 | 7 | `canonical__p001__loss_large` | canonical |
| 2 | 1 | `canonical__p039__loss_large` | canonical |
| 3 | 2 | `canonical__p018__mixed_damage` | canonical |
| 4 | 8 | `canonical__p043__mixed_damage` | canonical |
| 5 | 5 | `synthetic_degradation__p001__water_stain__severe` | synthetic |
| 6 | 9 | `synthetic_degradation__p039__water_stain__severe` | synthetic |
| 7 | 6 | `synthetic_degradation__p018__dirt_dust__severe` | synthetic |
| 8 | 10 | `synthetic_degradation__p026__dirt_dust__severe` | synthetic |
| 9 | 3 | `synthetic_degradation__p043__partial_transparency__severe` | synthetic |
| 10 | 4 | `synthetic_degradation__p026__water_stain_dirt__moderate` | synthetic |

Selection rank preserves the originally approved scientific list. Execution
order is diversity-first so a prematurely bounded run is less concentrated in
one damage family or painting.

Every case must have exactly one completed comparable row in the canonical
OpenCV Telea, LaMa, and Stable Diffusion primary branches before SDXL execution
is authorized. Stable Diffusion comparability means the completed
`p00_generic`, seed-2026 candidate.

## Model and generation policy

- Model: `diffusers/stable-diffusion-xl-1.0-inpainting-0.1`.
- Revision: `115134f363124c53c7d878647567d04daf26e41e`.
- Pipeline: `StableDiffusionXLInpaintPipeline`.
- Scheduler: `DDIMScheduler`.
- Device: CUDA only; no CPU fallback.
- Precision: float16.
- Inference and output geometry: 768 x 768.
- Denoising steps: 30.
- Guidance scale: 7.5.
- Strength: 1.0.
- Seed: 2026.
- Prompt variant: `p00_generic`.
- Pipeline loading: once per isolated batch worker.
- Memory policy: model CPU offload, PyTorch SDPA, VAE slicing and tiling.
- No xFormers, compilation, attention slicing, or sequential CPU offload.

The generic prompt is retained to preserve cross-method and Notebook 11 primary
candidate comparability. Notebook 12 does not add a prompt ablation or repeated
seeds.

## Mask and compositing policy

Canonical missing-region masks use threshold 128. Synthetic degradation effect
masks use threshold 13, matching the synthetic generator's active-effect
semantics.

Masks are resized with nearest-neighbour interpolation. Source images and model
outputs use the frozen 768 x 768 geometry. The final image is an exact masked
composite: generated pixels may replace only active mask pixels. A technically
valid result therefore has:

- an existing decodable RGB PNG;
- geometry exactly 768 x 768;
- a non-empty thresholded mask;
- zero changed pixels outside that mask;
- a recorded SHA-256 checksum.

## Execution and stopping rules

The parent notebook starts one isolated persistent worker.

- Global wall-clock budget: 7,200 seconds.
- Per-case heartbeat watchdog: 900 seconds.
- Minimum remaining budget required to start a case: 660 seconds.
- Progress polling: every second.
- Candidate checkpointing: after every resolved case.
- Automatic retries: prohibited.
- Completed images: preserved immediately.
- Timeout, CUDA out-of-memory, and model-loading guardrails stop later work.
- A globally exhausted budget leaves later rows explicitly unstarted.
- Parent-enforced termination reconciles the active row separately from later
  unstarted rows.

The worker uses bounded retry logic for Windows atomic-replacement locks. If the
canonical work checkpoint remains locked, it writes a new recovery checkpoint
and advertises that exact path in the atomic progress contract. This avoids
losing completed cases or aborting inference because a CSV was briefly locked.

## Candidate-state semantics

All ten predeclared rows persist in `data/candidates.csv`.

Allowed terminal states include:

- `completed` / `none`: technically valid saved output;
- `timed_out` / `runtime_guardrail`: active case exceeded 900 seconds;
- `failed` / `cuda_out_of_memory`: hardware memory limitation;
- `failed` / `model_unavailable` or `model_load_failure`;
- `failed` / `inference_failure`, `input_validation_failure`, or
  `worker_failure`;
- `skipped` / `not_started_global_budget`;
- `skipped` / `skipped_after_guardrail`.

No placeholder restoration path may be treated as a generated image. No metric
row may be synthesized for a non-completed candidate.

Availability is:

- `partial_evaluation` when at least one technically valid image exists;
- `feasibility_only` when runtime, OOM, or budget evidence exists but no valid
  image exists;
- `unavailable` when the pinned model is absent;
- `failed` for infrastructure failure without valid output.

`full_evaluation_complete` is not authorized by this contract.

## Canonical outputs

All outputs except the global inventory are owned by
`outputs/12_sdxl_feasibility_or_restoration/`.

```text
data/candidates.csv
images/restored/<experiment_id>/<case_id>/<candidate_id>.png
metrics/runtime_summary.csv
reports/partial_evaluation_report.md
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

The fixed canonical file count is six excluding restored images. The maximum
canonical count is sixteen when all ten scheduled images complete. Work files
belong under `work/partial_execution/` and are not canonical artifacts.

## Downstream eligibility

Notebooks 13-35 must discover SDXL through the final validated manifest and
candidate table. They may consume only technically valid completed rows. They
must preserve missingness for unscheduled or failed SDXL cases and compare
models only on paired identical cases.

Downstream statistical summaries must label the SDXL branch as purposive partial
coverage and treat painting as the independent unit. Runtime guardrail failures
must never be assigned poor image-quality metrics.

Notebook 18 cannot estimate SDXL seed uncertainty because this branch has one
seed per case. Notebook 21 may compare validated SDXL rows on matched cases.
Notebook 29 must report the partial coverage and compute limits. Reports and the
dashboard must not imply full SDXL evaluation.

## Notebook batches

1. Contract bootstrap, path discovery, imports, config, output directories, and
   preflight validation.
2. Exact scope selection, real cross-method comparability audit, and normalized
   candidate planning.
3. Checksum materialization, model-cache audit, worker contract inspection,
   checkpoint/resume validation, and non-GPU watchdog dry runs.
4. One bounded persistent-worker execution.
5. Reloaded technical validation of every row and every completed image.
6. Runtime summary, status coverage, representative rendered panels, and
   partial-evaluation report.
7. Canonical persistence, artifact manifest, and run manifest.
8. Completion gate, registry/path updates, work cleanup, and final audit.

Every notebook cell is supplied in chat for manual paste and execution. Automated
repository preparation may edit helpers, schemas, configuration, tests, and
documentation, but must not edit or execute the notebook.

