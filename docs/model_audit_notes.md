# Model Audit Notes

This document records the current model roles, evidence boundaries, reproducibility risks, and project decisions used by Notebook 30.

- Literature justification belongs in `docs/literature_reference_log.md`.
- General methodology belongs in `docs/methodology_notes.md`.
- Executed counts and artifacts belong in notebook-owned manifests and canonical tables.
- Notebook 30 turns this audit into four portable Markdown model cards and a transparent compute/scalability table.

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

| Model | Evaluation status | Methodological role | Executed candidates |
|---|---|---|---:|
| OpenCV Telea | Fully evaluated | Classical deterministic baseline | 410 |
| LaMa | Fully evaluated | Learned deterministic inpainting baseline | 410 |
| Stable Diffusion Inpainting | Fully evaluated | Prompt-conditioned stochastic baseline | 1,330 |
| SDXL Inpainting | Partial evaluation | Bounded higher-capacity diffusion candidate | 10 |

OpenCV Telea, LaMa, and Stable Diffusion share the complete controlled 50-painting scope. SDXL is restricted to ten predeclared cases across five paintings and must not be presented as a full-scope comparison.

DALL-E/OpenAI Image Editing remains outside the reproducible core experiment because its closed, changeable service contract would weaken local reproducibility and training-data transparency.

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
- avoids learned training-data bias.

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

### Evidence population

- 410 restoration cases;
- 1,330 persisted candidates;
- 1,280 model inferences and 50 zero controls;
- 80 unique restoration cases in the repeated-seed uncertainty population;
- 130 prompt-specific uncertainty groups;
- 520 repeated-seed candidates using seeds `2026`, `2027`, `2028`, and `2029`;
- 50 scratch-aware groups paired with generic-prompt groups for controlled thin-scratch prompt ablation.

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

### Evidence population

- ten completed candidates;
- five paintings;
- canonical and synthetic/degradation cases selected for cross-method comparison;
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

Retain SDXL as `partial_evaluation`, not feasibility-only and not fully evaluated. Notebook 30 may project the common 300-painting canonical-primary scenario from its four executed canonical non-zero cases, but must mark the complete current-design projection not applicable.

## 7. Quality evidence policy

Notebook 30 reuses Notebook 21’s eleven validated anchors:

- classical masked MAE, PSNR, and SSIM;
- LPIPS;
- CLIP and DINOv2 feature evidence;
- semantic CLIP and DINOv2 evidence;
- structure edge-overlap F1;
- local colour difference;
- local seam energy.

Two populations remain separate:

- `core_three_model`: all 410 shared cases for Telea, LaMa, and Stable Diffusion;
- `sdxl_four_model_subset`: the bounded 10-case four-model subset.

Anchor wins are descriptive counts across validated evidence views. They are not a weighted score, conservation ranking, or substitute for case-level inspection. Runtime is never added to the quality vote.

## 8. Uncertainty and robustness terminology

- Stable Diffusion receives empirical repeated-seed uncertainty because four candidates exist per approved group.
- SDXL has insufficient repeated-seed coverage and receives no artificial uncertainty value.
- Telea and LaMa are deterministic under the evaluated contract; later analyses use robustness or sensitivity terminology.
- Notebook 18 owns scalar and pairwise uncertainty evidence.
- Notebook 19 owns numeric uncertainty maps, heatmaps, and spatial overlays.
- Notebook 22 owns the damage-size repeated-seed extension.

Uncertainty is an empirical variability proxy, not calibrated confidence.

## 9. Texture, colour, seam, semantic, and structural evidence

Notebook 17 owns local consistency evidence, including texture, directional structure, colour, and seam diagnostics. Notebook 20 owns semantic and structural consistency. Notebook 21 combines only the approved anchors while preserving family identities and disagreement.

Texture and brushstroke-proxy measures do not authenticate an artist, date a work, or verify semantic brushstroke intent. Colour and seam measures diagnose local transitions; they do not alone determine restoration quality.

## 10. Compute and scalability policy

Notebook 30 records observed runtime summaries exactly as produced by Notebooks 09–12. These values describe one workstation, software stack, cache state, and execution policy.

Two transparent 300-painting sensitivity scenarios are allowed:

1. `projected_300_canonical_primary`: 1,500 candidate outputs per model, consisting of 1,200 inferred non-zero cases and 300 zero controls.
2. `projected_300_current_design_mix`: six times the executed complete design—2,460 Telea candidates, 2,460 LaMa candidates, and 7,980 Stable Diffusion candidates. SDXL is not applicable because no full-design SDXL basis exists.

Projection rules:

- median, mean, and p95 observed per-candidate runtimes form sensitivity values;
- these values are not confidence intervals;
- no 300-painting experiment was executed;
- projected storage covers notebook-owned artifacts only;
- caches, environments, Git history, downstream metrics, energy, and carbon are excluded;
- no universal runtime or hardware benchmark is claimed.

## 11. Model-card reporting policy

Notebook 30 produces four standalone Markdown cards. Each card must:

- follow the approved thirteen-section structure;
- state scope and evaluation status near the top;
- separate observed measurements from projections;
- name intended and excluded uses;
- disclose training-data transparency, domain gap, licences, and sources;
- include simple scoped conclusions after key facts;
- include no image dependency or base64 payload;
- remain portable when downloaded alone.

Notebook 31 owns image-heavy model reports. Notebook 32 owns case- and painting-level reports. Notebook 34 owns final dashboard assets. Notebook 36 owns the supervisor/publication/reproducibility package.

## 12. Model-risk summary

| Risk | Telea | LaMa | Stable Diffusion | SDXL |
|---|---|---|---|---|
| Training-data opacity | Not applicable | Medium | High | High |
| Painting-domain gap | High | Medium–high | High | High |
| Hallucination risk | Low | Medium | High | High |
| Large-mask capability | Low | High | Medium | Not fully established here |
| Texture-faithfulness risk | High | Medium | High | High |
| Reproducibility | High | High | Medium | Medium |
| Local compute burden | Low | Medium | High | Very high |
| Evaluation status | Full | Full | Full | Partial |

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
