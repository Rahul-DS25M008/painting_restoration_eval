# Notebook 11 Supplement — Paired Scratch-Aware Prompt Ablation

**Status:** executed and frozen; documentation reviewed 2026-09-04\
**Refactor status:** Finished\
**Validation status:** Finished\
**Completion gate passed:** Yes\
**Parent notebook:** `11_stable_diffusion_restoration.ipynb`  
**Parent output root:** `outputs/11_stable_diffusion_restoration/`  
**Base configuration:** `config/experiments/stable_diffusion.yaml`  
**Supplementary configuration:** `config/experiments/stable_diffusion_scratch_prompt_ablation.yaml`

This supplement extends, and does not replace, the Notebook 11 contract in
`docs/final_notebook_roadmap.md`. All general rules in
`docs/refactoring_implementation_guidelines.md` remain mandatory.

This is the authored experimental contract, so it remains under `docs/`.
Executed evidence belongs to the notebook-owned output root. The scope and
expansion wording below describe the approved, completed redesign, not permission
to regenerate or modify frozen Notebook 11 artifacts.

## Completion evidence

The saved run `run_82ee1e1c09524a5da3e6fe93016d0627` completed on 2026-08-26
with all 176 consolidated validation checks passed and no blocking or warning
failures. Its manifest records:

- 1,330 candidate rows and restored images, including 50 identity zero controls;
- 1,280 model-inference candidates;
- all 400 formal paired outcomes across 50 paintings and four seeds;
- six prompt-policy rows and 210 prompt-ablation design rows;
- 1,340 canonical files, with no temporary work files left at completion.

Authoritative execution records:

- [Run manifest](../outputs/11_stable_diffusion_restoration/manifests/run_manifest.json)
- [Executed prompt policy](../outputs/11_stable_diffusion_restoration/reports/prompt_policy.md)
- [Candidate table](../outputs/11_stable_diffusion_restoration/data/candidates.csv)
- [Consolidated validation](../outputs/11_stable_diffusion_restoration/validation/checks.csv)

The later 105 damage-size seed candidates belong to Notebook 22, not this
scratch-prompt supplement. They do not increase Notebook 11's historical count.

## Purpose

Test whether damage-aware semantic conditioning reduces Stable Diffusion 1.5's
visible residual-line failure on canonical thin-scratch masks. The experiment
must distinguish a repeatable prompt effect from ordinary stochastic variation.

## Frozen factors

The paired prompt arms use the same painting, damaged input, canonical mask,
seed, model revision, scheduler, inference resolution, output resolution,
inference steps, guidance, strength, precision, device policy, mask threshold,
retry policy, and exact-mask compositing policy. Only the prompt treatment may
differ inside a pair.

The existing generic primary prompt remains the baseline. Existing primary,
contextual-prompt, uncertainty, zero-control, runtime, provenance, figure,
report, validation, and manifest responsibilities remain intact.

## Formal experimental matrix

| Factor | Approved level |
|---|---|
| Paintings | all 50 controlled canonical paintings |
| Damage | `scratch_thin` |
| Prompt arms | `p00_generic`, `p05_scratch_aware` |
| Seeds | `2026`, `2027`, `2028`, `2029` |
| Outcomes per painting | 8 |
| Painting-seed pairs | 200 |
| Formal paired outcomes | 400 |

The painting is the main independent experimental unit. Seed-level outcomes
are repeated observations nested within paintings and must not be presented as
200 independent paintings.

The existing plan already supplies 80 members of the formal matrix: all 50
primary generic candidates plus three generic extension seeds for the 10
predeclared scratch cases in the uncertainty subset. The extension adds:

- 120 missing generic seed controls;
- 200 scratch-aware candidates;
- 320 candidates in total.

Notebook 11 therefore expands from 1,010 to 1,330 candidate rows and from 960
to 1,280 model inferences. The 50 zero controls remain identity no-ops. The
canonical artifact set remains unchanged and the expected output-file count is
1,340 excluding retained failure logs.

## Prompt treatment

`p00_generic` remains byte-for-byte unchanged in the frozen base configuration.

`p05_scratch_aware` describes the desired uninterrupted repaired state in its
positive prompt. Literal scratch morphology is concentrated in its negative
extension: visible or residual scratches, artificial thin lines, grey/dark
repair lines, white gaps, seams, outlines, discontinuities, mismatched texture,
and blurry repair.

This is one controlled treatment package. It is not an optimization sweep, and
no prompt, seed, painting, candidate, or figure may be chosen using restoration
metrics. Existing `p01`–`p04` metadata-context prompts remain exploratory
context and are not part of the formal two-arm contrast.

## Required persisted representation

The existing canonical outputs and artifact keys remain unchanged. The same
tables are expanded as follows:

- `data/candidates.csv`: 1,330 rows and prompt policy `sd15_prompt_policy.v3`;
- `data/prompt_policy.csv`: six rows, including `p05_scratch_aware`;
- `metrics/prompt_ablation_design.csv`: 210 rows, including 50 predeclared
  all-painting scratch rows;
- `images/restored/`: 1,330 candidate images;
- existing runtime, figure, report, manifest, artifact, and validation outputs
  updated in place.

`stable_diffusion_candidates.v1` retains its canonical execution-role enum.
The 120 additional generic repeated seeds are represented as
`uncertainty_extension`; the 200 damage-aware prompt candidates are represented
as `prompt_context`. Their exact experimental identities are unambiguous through
`prompt_variant_id` and
`candidate_selection_policy=all_canonical_paintings_paired_non_metric.v1`.

The formal paired matrix is reconstructed using the stable key
`(case_id, seed, prompt_variant_id)`.

## Validation gates

- Exactly 50 canonical `scratch_thin` cases and 50 unique paintings.
- Exactly four declared seeds and two declared prompt arms per painting.
- Exactly 400 unique `(case_id, seed, prompt_variant_id)` matrix rows.
- Both prompt arms present for every one of the 200 painting-seed pairs.
- Exactly 120 added generic controls and 200 added scratch-aware candidates.
- No zero controls, robustness masks, synthetic degradations, or other damage
  categories in the formal matrix.
- Same input, mask, seed, model settings, and compositing policy inside each pair.
- No metric-based selection or best-seed filtering.
- Exact outside-mask preservation and valid 768 x 768 RGB output geometry.
- Candidate IDs and restored paths unique; tables and figures reload from disk.
- Both configuration files checksummed in the run manifest.

## Limitation to report

Canonical thin scratches are only a few pixels wide at 768 x 768. Their support
can shrink or fragment during 512-pixel preprocessing and latent-grid mask
resampling. Exact compositing may consequently reveal generated colour or
texture mismatch as a narrow grey/dark line. The prompt ablation tests semantic
mitigation; it cannot by itself establish that the underlying spatial-resolution
limitation has been solved.

Downstream metric producers retain candidate-level evidence for both arms;
analytical consumers own paired contrasts and painting-level summaries. Preserve
the paired case/seed identity, aggregate repeated seeds within painting where
required by the analysis contract, and retain metric direction and mask/boundary
context. This document defines the treatment and its interpretation limits; it
does not by itself establish that scratch-aware prompting improved restoration.
