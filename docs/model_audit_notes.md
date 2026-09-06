# Model Audit Notes

**Status:** completed-pipeline audit notes with completed N37 extension addendum;
reviewed 2026-09-06.

This document records model selection, implementation provenance, evidence
boundaries and reproducibility risks. Notebook 30 consumed an earlier version
when producing its completed model cards. This maintenance update does not
rewrite those cards, their source checksums or any historical run manifest.

- Literature justification belongs in [the literature log](literature_reference_log.md).
- General methodology belongs in [the methodology guide](methodology_notes.md).
- Executed counts and artifacts belong in notebook-owned manifests and canonical tables.
- Notebook 30 produced four portable Markdown model cards and a 35-row
  compute/scalability table: 27 observed summaries and eight projection records.
  Detailed results belong in those outputs, not duplicated here.

---

## 1. Audit purpose

The thesis evaluates restoration candidates under controlled synthetic damage. It does not treat any pretrained inpainting method as a conservation-grade restoration system.

Each method is audited across:

- painting category and damage condition;
- reference, perceptual, feature, local-consistency, semantic, and structural evidence;
- local evaluation region;
- failure and robustness evidence;
- empirical seed variability where repeated candidates exist;
- observed runtime, memory, and storage under the recorded environment.

The central risk is domain gap. General-image or web-scale training does not establish painting-specific, historically correct, or conservation-safe behaviour.

> Visual plausibility is not the same as reference fidelity, historical authenticity, calibrated confidence, or approval for physical treatment.

## 2. Evaluated model stack

| Model | Evaluation status | Methodological role | N09–N12 completed candidates |
|---|---|---|---:|
| OpenCV Telea | Fully evaluated | Classical deterministic baseline | 410 |
| LaMa | Fully evaluated | Learned deterministic inpainting baseline | 410 |
| Stable Diffusion Inpainting | Fully evaluated | Prompt-conditioned stochastic baseline | 1,330 |
| SDXL Inpainting | Partial evaluation | Bounded higher-capacity diffusion candidate | 10 |

OpenCV Telea, LaMa, and Stable Diffusion share all 410 eligible restoration cases
across 50 paintings, including 50 zero controls per primary branch. They do not
restore all 525 registered cases. SDXL is restricted to ten predeclared cases
across five paintings and must not be presented as a full-scope comparison.

Notebook 22 separately owns 105 additional Stable Diffusion damage-size
candidates. N11 and N22 therefore contain 1,435 Stable Diffusion candidates in
total, but N30's original generation/runtime basis remains the 1,330 N11 rows.
The downstream 1,785-candidate reporting population is a selection across models
and experiments, not the number of Stable Diffusion outputs or all generated
outputs. Selection approval is not restoration-quality approval.

API-only image-editing services are outside the executed model stack. No
comparative performance claim about an unexecuted service follows from this
project's selection decision.

## 3. OpenCV Telea

### Role and implementation

- implementation: `cv2.INPAINT_TELEA`;
- fixed radius: `3`;
- execution: CPU;
- learned weights: none;
- zero controls: copied without inpainting.

### Strengths

- deterministic, fast, and lightweight;
- transparent classical baseline;
- useful for local interpolation and thin damage;
- has no learned training-data dependence; locality and interpolation still impose algorithmic assumptions.

### Limitations

- no semantic or painting-specific knowledge;
- weak reconstruction of large missing structures;
- local interpolation can lose meaningful structure and painterly texture;
- numerical improvement does not establish historical correctness.

### Project decision

Retain Telea as the reproducible low-compute baseline. Its results define what can be achieved without learned or generative priors.

## 4. LaMa

### Role and implementation

- method: LaMa large-mask inpainting;
- runtime: IOPaint CLI with `model=lama`;
- project wrapper: `src/restoration_eval/restoration_lama.py`;
- evaluated execution: CUDA on the recorded RTX 3060 Laptop GPU;
- zero controls: copied without model inference.

The configured artifact is `big-lama.pt`, identified by the expected MD5
`e3aa4aaa15225a33ec84f9f4bc47e500` and revision label
`iopaint_lama_default`. This identifies the configured artifact contract, not an
independently reconstructed checkpoint-to-training-run history. See
[the LaMa configuration](../config/experiments/lama.yaml).

### Strengths

- uses broader learned context than Telea;
- practical open learned baseline for large masks;
- deterministic under the evaluated contract;
- strongest model on 10 of the 11 validated Notebook 21 anchors for the complete three-model population.

### Limitations

- general-scene rather than painting-conservation training;
- can smooth texture or synthesize plausible but unsupported structure;
- the exact IOPaint-converted checkpoint-to-training-run mapping is not independently verified;
- reference-based strength is not historical or conservation truth.

### Project decision

Retain LaMa as the main learned deterministic baseline. Describe its 10/11 anchor result as a scoped descriptive finding, not a universal combined quality score.

## 5. Stable Diffusion Inpainting

### Role and implementation

- model: `stable-diffusion-v1-5/stable-diffusion-inpainting`;
- runtime: Diffusers `StableDiffusionInpaintPipeline`;
- inference size: 512 × 512;
- persisted output size: 768 × 768;
- prompt-conditioned and seed-controlled;
- zero controls: copied without model inference.

The pinned model revision is `8a4288a76071f7280aedbdb3253bdb9e9d5d84bb`.
The primary policy uses DDIM, 30 denoising steps, guidance 7.5, strength 1.0,
float16 CUDA inference and exact-mask compositing. The historical `runwayml`
identifier records lineage; the configured source is the model identifier above.
The effective six-variant prompt policy includes the separately configured
scratch-aware supplement. See the
[executed N11 prompt contract](notebook_11_scratch_prompt_ablation_contract.md).

### Original N11 and N18 evidence population

- 410 restoration cases;
- 1,330 persisted candidates;
- 1,280 model inferences and 50 zero controls;
- 80 unique restoration cases in the repeated-seed uncertainty population;
- 130 prompt-specific uncertainty groups;
- 520 repeated-seed candidates using seeds `2026`, `2027`, `2028`, and `2029`;
- 50 scratch-aware groups paired with generic-prompt groups for controlled thin-scratch prompt ablation.

The completed N22 extension adds 35 damage-size four-seed groups by combining
35 N11 seed-2026 candidates with its own 105 additional candidates. Final
uncertainty coverage is 165 groups: 130 canonical groups from N18 and 35
damage-size groups from N22. Prompt arms remain separate within each group.

The additional N22 candidates do not inherit individual reference-quality rows
from their N11 anchors. Their group uncertainty evidence is available separately;
the frozen N13/N14/N15/N17/N20 tables are not expanded by documentation changes.

### Strengths

- generative masked completion;
- controlled prompt and seed variation;
- supports empirical variability and prompt-sensitivity analysis;
- exposes a useful contrast between plausible synthesis and reference fidelity.

### Limitations

- hallucination, prompt, language, cultural, and web-data bias risks;
- higher compute and candidate multiplier than deterministic methods;
- thin scratch geometry can remain visible after exact compositing;
- repeated-seed similarity is not calibrated confidence;
- weaker scoped reference-based results in the current experiment.

### Project decision

Retain Stable Diffusion as the fully evaluated stochastic baseline and uncertainty target. Do not interpret low variability as correctness or high variability as automatic failure.

## 6. SDXL Inpainting

### Role and implementation

- model: `diffusers/stable-diffusion-xl-1.0-inpainting-0.1`;
- runtime: Diffusers `StableDiffusionXLInpaintPipeline`;
- evaluated size: 768 × 768;
- execution: bounded partial evaluation on the recorded 6 GB RTX 3060 Laptop GPU.

The pinned revision is `115134f363124c53c7d878647567d04daf26e41e`.
The execution used a 7,200-second global budget, a 900-second per-case watchdog,
seed 2026, 30 DDIM steps and exact-mask compositing. All ten selected cases
completed; timeout and unstarted states in the contract are guardrail policies,
not observed failures in this run. See the
[executed N12 contract](notebook_12_partial_evaluation_contract.md).

### Evidence population

- ten completed candidates;
- five paintings;
- four canonical and six synthetic-degradation cases selected for cross-method comparison;
- one seed per case, so no seed-based uncertainty estimate.

### Strengths

- higher-capacity diffusion comparison;
- provides observed local runtime and memory evidence;
- ten persisted outputs permit a bounded four-model comparison.

### Limitations

- not evaluated on the complete 410-case design;
- one seed per case;
- high local runtime and memory burden;
- insufficient evidence for a full-scope ranking or current-design projection;
- no experimentally validated universal minimum VRAM requirement is claimed.

### Project decision

Retain SDXL as `partial_evaluation`, not a no-output feasibility result and not
fully evaluated. Notebook 30 projected the common 300-painting canonical-primary
scenario from its four executed canonical nonzero cases and marked the complete
current-design projection not applicable. The narrow extrapolation basis must
remain visible; it is not evidence that SDXL would finish a larger experiment.

## 7. Quality evidence policy

Notebook 30 reused the eleven anchors defined in
[`multi_model_comparison.yaml`](../config/evaluation/multi_model_comparison.yaml):

| Anchor | Region |
|---|---|
| MAE | Masked region |
| SSIM | Mask-bounding-box crop |
| LPIPS | Mask-bounding-box crop |
| CLIP cosine similarity | Mask-bounding-box crop |
| DINOv2 cosine similarity | Mask-bounding-box crop |
| Mean restored error | Masked region |
| 95th-percentile local texture error | Mask-bounding-box crop |
| Mean CIEDE2000 colour difference | Masked region |
| Boundary-gradient mismatch | Boundary ring |
| Mean local DINOv2 patch similarity | Mask-bounding-box crop |
| Reference-affinity map correlation | Content region |

PSNR and other valid measurements remain in the wider evidence, but they are not
additional members of this fixed eleven-anchor set. Sparse masked-pixel SSIM,
edge-overlap F1 and generic “seam energy” must not replace the actual anchors.

Two populations remain separate:

- `core_three_model`: all 410 shared cases for Telea, LaMa, and Stable Diffusion;
- `sdxl_four_model_subset`: the bounded 10-case four-model subset.

Anchor wins are descriptive counts across validated evidence views. They are not
a weighted score, conservation ranking, or substitute for case-level inspection.
Neither runtime nor repeated-seed uncertainty enters cross-model quality voting.

## 8. Uncertainty and robustness terminology

- Stable Diffusion receives empirical repeated-seed uncertainty because four candidates exist per approved group.
- SDXL has insufficient repeated-seed coverage and receives no artificial uncertainty value.
- Telea and LaMa are deterministic under the evaluated contract; later analyses use robustness or sensitivity terminology.
- Notebook 18 owns scalar and pairwise uncertainty for the 130 canonical groups.
- Notebook 19 owns their numeric uncertainty maps, heatmaps and spatial overlays.
- Notebook 22 owns the damage-size extension, including its 35-group scalar and spatial uncertainty evidence.

Uncertainty is an empirical variability proxy, not calibrated confidence.

## 9. Texture, colour, seam, semantic, and structural evidence

Notebook 17 owns local consistency evidence, including texture, directional structure, colour, and seam diagnostics. Notebook 20 owns semantic and structural consistency. Notebook 21 combines only the approved anchors while preserving family identities and disagreement.

Texture and brushstroke-proxy measures do not authenticate an artist, date a work, or verify semantic brushstroke intent. Colour and seam measures diagnose local transitions; they do not alone determine restoration quality.

## 10. Compute and scalability policy

Notebook 30 records observed runtime summaries from Notebooks 09–12. These values
describe one workstation, software stack, cache state and execution policy; they
are not an end-to-end runtime total for all 36 notebooks. The N22 additional-seed
execution is not included in this N09–N12 runtime basis.

Two transparent 300-painting sensitivity scenarios were retained:

1. `projected_300_canonical_primary`: 1,500 candidate outputs per model, consisting of 1,200 inferred non-zero cases and 300 zero controls.
2. `projected_300_current_design_mix`: six times the N09–N12 generation design—2,460 Telea candidates, 2,460 LaMa candidates, and 7,980 Stable Diffusion candidates. Despite the historical scenario name, this does not scale the later N22 extension or the final 1,785-candidate reporting selection. SDXL is not applicable because no full-design SDXL basis exists.

Projection rules:

- median, mean, and p95 observed per-candidate runtimes form sensitivity values;
- these values are not confidence intervals;
- no 300-painting experiment was executed;
- projected storage covers notebook-owned artifacts only;
- caches, environments, Git history, downstream metrics, energy, and carbon are excluded;
- no universal runtime or hardware benchmark is claimed.

## 11. Model-card reporting policy

Notebook 30 produced four standalone Markdown cards under its approved structure.
They separate observed measurements from projections, record intended/excluded
uses and provenance limitations, and remain readable without image dependencies.
They are historical generated artifacts, not files to regenerate during this
documentation update.

Training-data and licence disclosures in those cards retain the qualifications
recorded by their producer. In particular, a software licence must not be silently
treated as a separately verified weight licence. This maintenance pass does not
perform a new legal or external training-data audit; source verification belongs
to the separate literature/provenance review.

Canonical cards:

- [OpenCV Telea](../outputs/30_model_cards_compute_and_scalability/reports/model_cards/opencv_telea.md)
- [LaMa](../outputs/30_model_cards_compute_and_scalability/reports/model_cards/lama.md)
- [Stable Diffusion](../outputs/30_model_cards_compute_and_scalability/reports/model_cards/stable_diffusion_inpainting.md)
- [SDXL](../outputs/30_model_cards_compute_and_scalability/reports/model_cards/sdxl_inpainting.md)
- [Compute/scalability table](../outputs/30_model_cards_compute_and_scalability/metrics/compute_scalability.csv)

Notebook 31 owns image-heavy model reports. Notebook 32 owns case- and painting-level reports. Notebook 34 owns final dashboard assets. Notebook 36 owns the supervisor/publication/reproducibility package.

## 12. Reproducibility and risk checks

This audit does not assign unvalidated low/medium/high risk scores. The actionable
cautions are:

- **Telea:** no learned weights, but local interpolation can miss meaningful
  structures; deterministic output is not proof of appropriate restoration.
- **LaMa:** record the exact IOPaint runtime and weight artifact; learned context
  can preserve measured structure while still introducing unsupported content.
- **Stable Diffusion:** record revision, prompt arm, seed, scheduler, inference
  size and compositing. Resampling a razor-thin mask can leave residual lines;
  prompt treatment alone does not establish that the geometry problem is solved.
- **SDXL:** retain the purposive ten-case scope, hardware and stopping policy.
  All ten completing does not establish full-dataset feasibility or a universal
  minimum VRAM requirement.
- **All methods:** retain per-run package/device records. All 36 saved manifests
  record Python 3.12.6, but dependency versions differ from the legacy
  experimental recipe. Determinism under the evaluated contract is not a promise
  of bitwise identity across different hardware or software stacks.

## 13. Human and conservation boundary

The framework supports human review; it does not replace conservators. None of the following is established by a model card, metric, projection, or visual report:

- historical authenticity;
- recovery of the artist’s true intent;
- material compatibility;
- reversibility of physical treatment;
- safety of intervention;
- approval for conservation action.

## 14. Current conclusion

The model stack is methodologically coherent:

1. Telea supplies a transparent classical baseline.
2. LaMa supplies the strongest scoped learned deterministic baseline.
3. Stable Diffusion supplies a stochastic generative baseline and uncertainty target.
4. SDXL supplies a bounded higher-capacity partial comparison.

The thesis contribution is the evaluation framework that shows where these restoration candidates improve, fail, disagree, hallucinate, smooth texture, create seams, alter structure, or vary across seeds—not a claim that any model reconstructs conservation truth.

## 15. Completed HINT/MAT selection extension

Notebook 37 compared HINT and MAT on the same twelve predeclared canonical cases
and selected HINT for the future expanded run. This is a method-selection pilot,
not an update to the completed full-benchmark stack above.

| Candidate | Released checkpoint | Observed adapter | Licence consideration | Outcome |
|---|---|---|---|---|
| HINT | official Places2 | native 768 × 768 | MIT software; checkpoint terms recorded separately | selected for the future expansion |
| MAT | official Places-512 FullData | 512 input, returned to exact-mask-composited 768 output | CC BY-NC 4.0, research-only constraint | retained as the pilot comparator; not selected |

Both candidates produced all 12 required outputs and passed all 94 consolidated
validation checks. HINT led 96 of 108 case-level metric anchors; MAT led 6 and 6
were ties. Mean inference time was 8.26 seconds per case for HINT and 10.00
seconds for MAT. Peak GPU memory was 5.06 GiB and 1.23 GiB, respectively.
Complete visual review found that MAT often retained thin scratches and produced
pale or fragmented large-loss completions, whereas HINT was more consistent
across the paired scope.

The comparison addressed a specific missing capability rather than adding a
near-duplicate model. Telea is classical and deterministic, LaMa is a learned
deterministic Fourier-convolution method, and Stable Diffusion is stochastic and
prompt-conditioned. HINT adds a second deterministic learned family with
mask-aware pixel-shuffle processing and spatially activated channel attention
for multi-scale, long-range context. MAT supplied a credible transformer
comparator but required a 512 adapter and carried a noncommercial licence.

HINT and MAT are trained on general image/scene data, not conservation paintings.
The selection therefore improves architectural coverage for the future
benchmark without removing the domain gap or establishing conservation
suitability. See the [complete selection report](../outputs/37_hint_mat_method_selection/reports/method_selection_report.html)
and [recorded decision](../outputs/37_hint_mat_method_selection/reports/selection_decision.json).
