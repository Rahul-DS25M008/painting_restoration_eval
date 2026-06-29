# Supervisor Feedback and Next-Phase Plan

## Purpose

This document summarizes supervisor feedback and converts it into concrete next steps for the thesis project **Trustworthy Evaluation Frameworks for AI-Assisted Painting Restoration**.

The pilot phase has validated the basic end-to-end workflow. The next phase should use that working pipeline to build a controlled 50-painting subset and prepare for model comparison.

## Key feedback

### 1. Investigate training data and model bias

For pretrained models, the next phase should document what is known about the training data, intended use, and likely domain gaps.

This is important because many general-purpose inpainting models are trained on natural images or broad web image datasets rather than historical paintings. This may create weaknesses for:

- underrepresented art styles
- abstraction and surrealism
- non-photorealistic textures
- historical painting materials
- brushstroke-heavy surfaces
- non-Western or less common visual traditions

Planned action:

```text
Create a model audit table before adding pretrained models.
```

Candidate fields:

```text
model_name
model_family
open_or_closed
deterministic_or_stochastic
training_data_summary
painting_or_art_representation
known_domain_gap
bias_risk
input_format
mask_format
supports_seed_control
supports_multiple_outputs
reproducibility_score
access_cost_notes
selected_for_50_subset
notes
```

Initial model candidates:

```text
OpenCV Telea
LaMa
Stable Diffusion Inpainting
SDXL Inpainting
DALL-E / OpenAI Image Editing
```

## 2. Include abstraction and surrealism

The final dataset should not only contain realistic or representational images. Abstraction and surrealism may create harder cases because restoration models may not know what structure is expected.

Planned action:

```text
Include abstraction / surrealism as one of the controlled 50-painting categories.
```

Proposed 50-painting subset:

| Category | Count |
|---|---:|
| Portrait / figure | 10 |
| Landscape / natural scene | 10 |
| Architecture / structured scene | 10 |
| Abstraction / surrealism | 10 |
| High-texture / brushstroke-heavy | 10 |

## 3. Improve synthetic masks

The pilot masks were useful for testing the workflow, but the next phase needs more realistic and more controlled damage conditions.

Planned action:

```text
Replace the pilot mask types with a formal damage protocol.
```

Proposed damage conditions:

| Damage condition | Approximate area | Purpose |
|---|---:|---|
| zero_control | 0% | Measures unnecessary change or hallucination |
| scratch_thin | 1–3% | Thin cracks and scratches |
| loss_small | 3–6% | Local missing paint |
| loss_large | 10–15% | Hard missing region |
| mixed_damage | 8–15% | Combined realistic damage |

Mixed damage should combine:

- scratch lines
- irregular paint loss
- scattered small loss fragments
- optional edge damage
- rougher boundaries

## 4. Consider DALL-E / OpenAI image editing

A closed commercial model may be useful as a comparison point, but it should not become the core reproducible baseline unless the methodology clearly accounts for access, cost, and reproducibility limitations.

Planned action:

```text
Treat DALL-E / OpenAI image editing as an optional closed-model comparison.
```

Recommended model order:

```text
1. OpenCV Telea
2. LaMa
3. Stable Diffusion / SDXL Inpainting
4. Optional DALL-E / OpenAI image editing
```

## 5. Include a deployment component

The MDS project requires a deployment element. The most appropriate deployment for this thesis is likely an evaluation dashboard rather than a production restoration tool.

Planned action:

```text
Build a Streamlit-based Trustworthy Painting Restoration Evaluation Dashboard.
```

Possible dashboard features:

- select painting
- select damage condition
- compare model outputs
- show original, masked, and restored images
- show masked-region metrics
- show LPIPS / perceptual metrics
- show error maps
- show uncertainty maps for generative models
- export case-level report

## 6. 50-painting controlled subset

The next experimental phase should not jump directly to the final experiment. Instead, it should test the methodology on a controlled 50-painting subset.

Purpose of the 50-painting phase:

```text
Test dataset categories, damage protocol, metric behavior, model feasibility, and reporting workflow before finalizing the main experiment.
```

Main questions:

1. Does restoration quality vary systematically by damage type?
2. Does restoration quality vary by painting category?
3. Do local metrics and perceptual metrics provide better evidence than full-image metrics alone?
4. Do generative models introduce unnecessary changes or hallucinations?
5. Can uncertainty be measured in a useful way using multiple restoration candidates?

## Recommended next workflow

```text
1. Freeze reproducible pilot
2. Update README and documentation
3. Push cleaned pilot repo to GitHub
4. Create model audit table
5. Create metadata template for 50 paintings
6. Select candidate public-domain paintings
7. Implement improved damage masks
8. Run OpenCV Telea on the 50-painting subset
9. Add LaMa
10. Add diffusion-based inpainting model
11. Run uncertainty subset
12. Build Streamlit evaluation dashboard
13. Share 50-subset results with supervisor
14. Decide final main experiment design
```

## Current decision

The immediate next step after repository/documentation cleanup is:

```text
Create the model audit table, 50-painting metadata template, and experiment configuration file.
```

This ensures that supervisor feedback is incorporated before expanding the experiment.
