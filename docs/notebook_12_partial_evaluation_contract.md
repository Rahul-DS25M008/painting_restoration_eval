# Notebook 12 SDXL bounded partial-evaluation contract

**Status:** Controlled-300 execution contract approved 2026-09-13\
**Refactor status:** In progress\
**Validation status:** Pending\
**Completion gate passed:** No

## Status and purpose

This document freezes the approved refactor contract for
`notebooks/12_sdxl_feasibility_or_restoration.ipynb`.

Notebook 12 produces a reusable but explicitly partial SDXL branch. It is not a
full-dataset evaluation, a population sample, or evidence that omitted cases
failed restoration. Its scientific contribution is a transparent comparison
asset under strict runtime limits.

The machine-readable authority is `config/experiments/sdxl.yaml`
(`sdxl_config.v3`). This document explains that contract in human-readable
form. The final notebook roadmap and refactoring implementation guidelines
remain controlling repository-wide documents.

This authored design contract remains under `docs/`; the executed report,
candidates, validation, and manifests belong to the notebook-owned output root.
The policy and batch plan below authorize the bounded Controlled-300 rerun. The
tagged `pilot-50-complete` evidence remains frozen and independently recoverable.

## Pilot evidence used to size the rerun

The frozen pilot run completed all ten predeclared cases: four canonical and six
synthetic cases across five paintings. It recorded 3,784.7 seconds total runtime,
a 378.5-second mean, a 294.9-second median, and no technical failure. Those ten
cases remain inside the expanded scope so the new execution retains a direct
bridge to the pilot.

The Controlled-300 budget is not a result claim. It scales the previous
720-seconds-per-scheduled-case allowance to 35 cases, producing a 25,200-second
global limit. The observed pilot mean projects about 3.7 hours of execution;
the seven-hour ceiling provides conservative headroom without permitting an
unbounded run.

## Frozen Controlled-300 scope

The independent unit is the painting. The 35 cases span 30 paintings and exactly
seven cases per controlled visual category. The five retained pilot anchors each
contribute two nested cases; the other 25 paintings contribute one case each.
Case rows must therefore not be interpreted as 35 independent paintings.

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
| 11 | 11 | `canonical__p251__loss_small` | canonical |
| 12 | 21 | `canonical__p261__scratch_thin` | canonical |
| 13 | 31 | `canonical__p271__mixed_damage` | canonical |
| 14 | 16 | `synthetic_degradation__p267__partial_transparency__moderate` | synthetic |
| 15 | 26 | `synthetic_degradation__p284__water_stain_dirt__moderate` | synthetic |
| 16 | 12 | `canonical__p151__loss_small` | canonical |
| 17 | 22 | `canonical__p161__scratch_thin` | canonical |
| 18 | 32 | `canonical__p171__loss_large` | canonical |
| 19 | 17 | `synthetic_degradation__p181__water_stain__moderate` | synthetic |
| 20 | 27 | `synthetic_degradation__p198__partial_transparency__severe` | synthetic |
| 21 | 13 | `canonical__p101__loss_small` | canonical |
| 22 | 23 | `canonical__p111__scratch_thin` | canonical |
| 23 | 28 | `canonical__p121__loss_large` | canonical |
| 24 | 33 | `canonical__p131__mixed_damage` | canonical |
| 25 | 18 | `synthetic_degradation__p107__water_stain_dirt__moderate` | synthetic |
| 26 | 14 | `canonical__p051__loss_small` | canonical |
| 27 | 24 | `canonical__p061__scratch_thin` | canonical |
| 28 | 34 | `canonical__p071__mixed_damage` | canonical |
| 29 | 19 | `synthetic_degradation__p052__dirt_dust__moderate` | synthetic |
| 30 | 29 | `synthetic_degradation__p073__partial_transparency__moderate` | synthetic |
| 31 | 15 | `canonical__p201__loss_small` | canonical |
| 32 | 25 | `canonical__p211__scratch_thin` | canonical |
| 33 | 35 | `canonical__p221__loss_large` | canonical |
| 34 | 20 | `synthetic_degradation__p208__water_stain__moderate` | synthetic |
| 35 | 30 | `synthetic_degradation__p210__dirt_dust__moderate` | synthetic |

Selection ranks 1–10 preserve the original scientific list, and ranks 11–35 are
the metric-independent expansion. Execution order retains the first ten pilot
orders and then cycles across categories, damage families, and experiment types
so an early bounded stop is not concentrated in one category.

The 20 canonical cases contain exactly five examples of each canonical mask
family. The 15 synthetic cases contain four water-stain, four dirt/dust, four
partial-transparency, and three water-stain-plus-dirt cases. Every visual
category contains four canonical and three synthetic cases.

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

- Global wall-clock budget: 25,200 seconds (seven hours).
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

All 35 predeclared rows persist in `data/candidates.csv`.

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
canonical count is 41 when all 35 scheduled images complete. Work files
belong under `work/partial_execution/` and are not canonical artifacts.

## Downstream eligibility

Consumers in Notebooks 13–36 must discover SDXL through the final validated manifest and
candidate table. They may consume only technically valid completed rows. They
must preserve missingness for unscheduled or failed SDXL cases and compare
models only on paired identical cases.

Downstream statistical summaries must label the SDXL branch as purposive partial
coverage and treat painting as the independent unit. Runtime guardrail failures
must never be assigned poor image-quality metrics.

Notebook 18 cannot estimate SDXL seed uncertainty because this branch has one
seed per case. Notebook 21 compares validated SDXL rows on matched cases.
Notebook 30 owns model-card and compute-limit reporting. Reports and the
dashboard must not imply full SDXL evaluation.

Technically valid completed candidates are included in downstream metric and
reporting coverage where the declared metric-region contract applies. Their single seed
does not support an SDXL uncertainty comparison in N18, N19, or N22.

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

