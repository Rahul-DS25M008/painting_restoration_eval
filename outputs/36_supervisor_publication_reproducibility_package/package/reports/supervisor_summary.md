# Trustworthy Evaluation of AI-Assisted Painting Restoration

## Supervisor Review Summary

**Notebook:** `36_supervisor_publication_reproducibility_package.ipynb`  
**Evidence scope:** Controlled 50-painting benchmark and declared extensions  
**Generated:** `2026-09-03T21:13:24Z`  
**Package validation:** See the final Notebook 36 run manifest and validation ledger; scientific evidence is complete through Notebook 35  
**Scientific role:** Evidence synthesis and delivery only—no new metrics or restoration inference

## 1. Decision snapshot

- **Strongest general baseline:** **LaMa**, leading **10 of 11 quality anchors**.
- **Fastest evaluated baseline:** **OpenCV Telea**, with a median observed runtime of **0.424 seconds** per recorded candidate.
- **Metric disagreement matters:** Telea leads **crop SSIM**, while LaMa leads the other **10 anchors**. SSIM alone would therefore give an incomplete result.
- **Diffusion requires closer review:** Stable Diffusion leads **0 of 11 aggregate anchors** and has **165 repeated-seed uncertainty groups** available for variability analysis.
- **SDXL remains limited:** only **10 feasibility candidates** were evaluated, so it is not ranked as a fourth full benchmark.
- **Human inspection remains necessary:** **1,703 of 1,785 candidates (95.4%)** trigger conservative computational review guidance.
- **No universal score is used:** metric families, regions, uncertainty, and failure evidence remain separate.

### Central conclusion

**Visual plausibility is not the same as restoration trustworthiness.**

LaMa is the best general benchmark baseline, but no model result should be accepted from appearance or one metric alone. Restoration evidence must remain traceable across regions, metric families, uncertainty, diagnostic maps, and case-level inspection.

![Benchmark summary](../figures/publication/01_benchmark_summary.png)

## 2. What was evaluated

| Evidence component | Validated scope |
|---|---:|
| Paintings | **50** |
| Visual categories | **5**, with 10 paintings each |
| Registered experimental cases | **525** |
| Restoration cases | **410** |
| Approved comparison candidates | **1,785** |
| Fully evaluated models | **3** |
| Bounded SDXL feasibility model | **1** |
| Quality anchors | **11** |
| Repeated-seed uncertainty groups | **165** |
| Indexed visual records | **23,964** |
| Indexed reports | **104** |
| Thesis figures | **18** |
| Publication figures | **6** |

The evidence is broad enough for controlled comparison across the declared paintings, models, metrics, regions, and synthetic damage conditions. It does **not** establish performance on real conservation treatments or unseen museum collections.

## 3. Research questions

### RQ1

> How can a multi-metric evaluation framework be designed to assess AI-generated painting restorations beyond traditional image similarity metrics?

**Evidence:** Restoration quality requires complementary pixel, perceptual, feature, texture, colour, seam, spatial, and structural evidence evaluated in valid regions.

**Key evidence:** 11 separate quality anchors spanning complementary metric families and regions.

**Conclusion:** No single metric can establish restoration quality. Trustworthy comparison requires several metric families evaluated in the regions where they are meaningful, with disagreements retained.

**Boundary:** No individual metric or combined universal score is treated as conservation truth.

### RQ2

> How do selected pretrained inpainting models differ in restoration quality across artistic styles and artificial damage types?

**Evidence:** LaMa is the strongest general baseline in this controlled benchmark, while performance still changes by metric, damage condition, painting, and experimental scope.

**Key evidence:** LaMa leads 10 of 11 anchors; Telea leads crop SSIM and has the lowest observed runtime.

**Conclusion:** LaMa is the strongest general baseline in this controlled benchmark, leading 10 of 11 quality anchors. Telea is fastest and leads crop SSIM, while diffusion results require closer case-level and variability review.

**Boundary:** The result does not establish a universally best model, real-world treatment suitability, or full SDXL performance.

### RQ3

> To what extent can uncertainty estimation from multiple restoration candidates identify speculative or unreliable restored regions?

**Evidence:** Repeated-seed variability identifies diffusion cases whose outputs are less consistent and should receive closer visual review.

**Key evidence:** 165 four-seed uncertainty groups: 130 canonical and 35 damage-size groups.

**Conclusion:** Repeated-seed variability can identify Stable Diffusion cases and regions that deserve closer visual review. It cannot determine whether a restoration is correct or historically plausible.

**Boundary:** Empirical variability is not calibrated confidence, correctness, historical plausibility, or expert approval.

![Stress-test summary](../figures/publication/02_stress_test_summary.png)

## 4. Model conclusions

| Model | Evaluation status | Approved candidates | Executed candidates | Quality-anchor wins | Median runtime | Direct conclusion |
|---|---:|---:|---:|---:|---:|---|
| LaMa | fully evaluated | 410 | 410 | 10 of 11 | 1.567 s | LaMa leads 10 of 11 quality anchors and is the strongest general restoration baseline in this controlled benchmark. |
| OpenCV Telea | fully evaluated | 410 | 410 | 1 of 11 | 0.424 s | OpenCV Telea is the fastest evaluated baseline and leads crop SSIM. It is useful when speed and deterministic local filling matter, but it is not the strongest general model across the complete metric framework. |
| Stable Diffusion Inpainting | fully evaluated | 955 | 1,330 | 0 of 11 | 9.535 s | Stable Diffusion provides prompt-conditioned candidate diversity but leads none of the 11 aggregate quality anchors. Its outputs require case-level and repeated-seed inspection. |
| SDXL Inpainting | partial evaluation | 10 | 10 | Not applicable | 294.916 s | SDXL produced ten completed feasibility cases. The evidence is sufficient for bounded qualitative inspection but not for a full benchmark ranking. |

### What this means

- **LaMa:** the strongest default baseline when overall restoration evidence matters more than one isolated metric.
- **OpenCV Telea:** the practical speed baseline and competitive for thin or local filling, but weaker as a general multi-metric solution.
- **Stable Diffusion:** useful for studying prompt-conditioned and repeated-seed behaviour, but its candidates require more intensive visual and uncertainty review.
- **SDXL:** useful only as bounded feasibility evidence in the current project.

The Stable Diffusion executed total includes additional prompt and repeated-seed candidates. The **955 approved Stable Diffusion candidates** are the population retained in the 1,785-candidate comparison catalog.

## 5. Robustness and uncertainty

The project separates three different questions:

- **Damage-size sensitivity:** how results change as the damaged area increases.
- **Mask robustness:** how results change when mask geometry or placement changes.
- **Generative uncertainty:** how Stable Diffusion candidates change across repeated seeds for a fixed case and prompt configuration.

These quantities are not interchangeable. Mask variation is input robustness, and prompt variation is prompt sensitivity; neither is relabelled as generative uncertainty.

The **165 uncertainty groups** comprise:

- **130 canonical Stable Diffusion groups**;
- **35 damage-size Stable Diffusion groups**;
- four seeds per eligible group.

**Conclusion:** greater repeated-seed variation identifies cases or regions that deserve closer visual review. It does not prove that a low-variation restoration is correct.

![Uncertainty and spatial summary](../figures/publication/03_uncertainty_spatial_summary.png)

## 6. Trustworthiness and explainability

The framework keeps review evidence separate:

- reference and perceptual evidence;
- feature similarity;
- texture and brushstroke proxies;
- colour consistency;
- seam and boundary consistency;
- semantic and structural affinity;
- difference and uncertainty maps;
- counterfactual, example-based, and rule-based explanations;
- independent computational failure flags.

**1,703 of 1,785 candidates** receive conservative review guidance. This high rate does not mean that 95.4% are objectively failed restorations. It means the rules are intentionally cautious and that automatic acceptance would be inappropriate.

**Conclusion:** computational explanations can show why a candidate was flagged and where disagreement occurs, but an expert must decide whether that evidence is meaningful for conservation.

![Trustworthiness and ablation summary](../figures/publication/04_trustworthiness_ablation_summary.png)

![Explainability summary](../figures/publication/05_explainability_summary.png)

## 7. Reproducibility and delivery status

- **35 of 35** upstream notebook completion gates passed.
- **417** manifest-declared outputs currently exist.
- **218** upstream canonical artifacts were registered at Notebook 36 preflight; Notebook 36 delivery records are registered after final validation.
- The final package copy plan contains **106 files** and approximately **27.60 MiB** of source material.
- All five bundled HTML reports are designed to remain self-contained.
- All eight Streamlit pages passed the Notebook 35 runtime smoke test.
- The dashboard is **ready for local supervisor demonstration**.
- Public deployment is **not complete**.
- Notebook 35 retains non-blocking dependency-version warnings that must remain visible.

![Quality and compute summary](../figures/publication/06_quality_compute_summary.png)

## 8. Limitations that must remain visible

- The dataset contains controlled synthetic damage rather than verified physical conservation interventions.
- The 50-painting collection does not establish universal artistic or museum-domain generality.
- Repeated observations, models, and seeds sharing the same painting are not independent paintings.
- Feature similarity is not historical authenticity.
- Seed variability is not calibrated confidence.
- Computational flags are not expert annotations.
- Retrieval neighbours provide context rather than proof.
- SDXL has only ten completed cases.
- No model output constitutes a treatment recommendation or conservation approval.

## 9. Decisions requested from the supervisor

1. Is the controlled 50-painting scope sufficient for the thesis claims as currently bounded?
2. Is the multi-metric, region-aware framework an appropriate central methodological contribution?
3. Is LaMa's 10-of-11 anchor lead sufficient to describe it as the strongest general benchmark baseline?
4. Is it acceptable to retain SDXL strictly as bounded feasibility evidence?
5. Should a human or conservator review study be framed as future work rather than added to the current empirical scope?
6. Is local dashboard demonstration sufficient, or is public deployment required before submission?
7. Which figures and findings should be prioritized in the thesis defence and any publication draft?

## 10. Recommended review route

1. Read this summary.
2. Open `reports/final_evaluation.html` for the complete thesis-level narrative.
3. Open the four reports under `reports/models/` for model-specific evidence.
4. Use `tables/` for exact compact evidence and report indexes.
5. Use the Streamlit application for filtered case, image, map, and report inspection.
6. Use `provenance/reproducibility_snapshot.json` and `manifests/notebook_runs/` for audit and reproduction.

---

**Interpretation boundary:** This package supports evidence review and thesis communication. It does not authenticate paintings, approve conservation treatment, or replace expert judgement.
