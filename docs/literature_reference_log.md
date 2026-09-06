# Literature Reference Log

**Status:** completed-pipeline literature audit and expanded reading log\
**Reviewed:** 2026-09-06\
**Scope:** 36 completed core notebooks, completed Notebook 37 method-selection extension, controlled 50-painting study, and approved dashboard\
**Search priority:** 2020–2026, with explicitly identified foundational exceptions

This is an annotated source catalog for thesis writing, not a list of methods
that the project promises to implement. It replaces the repeated legacy
notebook notes with verified bibliographic identities, usable source links,
current notebook mappings, and explicit limits on what each citation supports.

The catalog contains **49 scholarly sources**: **35 dated 2020 onward** and
**14 foundational pre-2020 exceptions**, plus **7 technical-source groups**.
It retains/corrects 22 identifiable legacy scholarly references and adds 27
new or newly identified sources, including the formerly unnamed self-consistency work.

Read alongside the [methodology guide](methodology_notes.md),
[model audit](model_audit_notes.md),
[final roadmap](final_notebook_roadmap.md), and
[evidence dependency audit](evidence_dependency_audit.md).
Project configurations, saved manifests and reports remain authoritative for
what was actually executed. A newly added citation does not alter those records.

## 1. Selection and verification rules

- **Direct-method:** the project uses the named method, representation or
  reporting principle. This does not imply that the paper validates its use on
  this painting collection.
- **Close-topic:** the paper addresses restoration evaluation, painting/mural
  restoration, or a central thesis question, but its method or dataset differs.
- **Partial/context:** a useful transferable component, limitation or comparison.
  This deliberately includes the user's requested approximate “60% matches”.
  Relevance is qualitative; no invented numerical matching score is assigned.
- **Technical:** official implementation documentation or a checkpoint/model
  card. These establish software behavior and provenance, not peer-reviewed
  conservation effectiveness.
- **Foundational exception:** a pre-2020 original method, metric or design source
  retained because replacing it with a recent survey would obscure attribution.

The 2026-09-04 search checked legacy author/title combinations and searched
expanded topics: heritage restoration, masks and degradation, texture and
colour, diffusion sampling, uncertainty/calibration, spatial explanation,
prompt sensitivity, grouped statistics, XAI, documentation and visualization.
Searches used publisher pages, CVF/PMLR/NeurIPS/ICLR proceedings, author or
institutional repositories, arXiv and official software documentation.
This is a targeted literature update, **not an exhaustive systematic review**.

Verification means bibliographic identity and the stated relevance were checked
against the linked primary record, abstract, or accessible article sections.
It does not mean every experiment or proof in every paper was independently
reviewed. Abstract-only or access-limited use is noted where material.
Publication years are distinguished from preprint/early-online years when
verified. An arXiv entry is not silently assigned peer-reviewed status.

Related-work additions are retrospective context for a completed study; they
must not be described as sources consulted before the experiments unless an
earlier record establishes that chronology. Do not import another paper's
performance numbers into this project's results.

## 2. Corrections to the previous log

| Previous entry or claim | Audit outcome |
|---|---|
| Fontoura Júnior et al. (2023), described as a cultural-heritage inpainting study | The verified paper concerns **remote-sensing imagery and feature extraction**. Retained as cross-domain context in [H08](#h08), not heritage evidence. |
| Sun et al. (2024), title ending “Multi-Scale Feature Fusion” | Correct title ends **“contextual information”**; see [H02](#h02). |
| Liu et al. (2024), title ending “Multi-Layer Feature Fusion” | Correct title is **“Multi-Layer Feature Enhancement and Frequency Perception”**; see [H03](#h03). |
| “Cultural heritage restoration and inpainting evaluation literature” | Not a citation. Replaced with named heritage sources H01–H07. |
| “Recent inpainting self-consistency work” | Replaced with the identifiable Chen et al. paper [U05](#u05); re-inpainting is not our repeated-seed procedure. |
| Unresolved generated citation markers | Removed; references now have actual publisher, proceedings, author or software links. |
| Old notebook numbers, 40 groups/160 candidates and a combined uncertainty index | Superseded by the completed-pipeline map below. N18 has 130 groups; N22 adds 35. No combined uncertainty index is retained. |
| SDXL described as unexecuted; future 300-painting expansion treated as planned evidence | SDXL has ten completed bounded cases. Larger-population compute estimates remain projections, not executed studies. |
| RunwayML and generic SDXL references without checkpoint distinction | The model-family papers are separated from the exact SD/SDXL inpainting checkpoint records in T04. |

The old document is recoverable through Git history. Frozen reports or N36
package copies can contain earlier literature wording; this current log is the
corrected source for new thesis prose. Their historical provenance is not
rewritten by this documentation maintenance.

## 3. Literature-to-pipeline map

Source IDs below link to the annotated records. This map covers the completed
notebooks without pretending that every engineering choice comes from a paper.

| Notebook(s) | Implemented responsibility | Main literature support |
|---|---|---|
| N01 | Dataset verification, source metadata and coverage | [E07](#e07), [H01](#h01), [H07](#h07) |
| N02 | Aspect-preserving preprocessing and recorded content bounds | [M04](#m04), [Q04](#q04), [Q05](#q05), [T01](#t01); exact geometry is project-defined |
| N03–N04 | Canonical masks, damaged inputs, identity controls | [M01](#m01), [M03](#m03), [M04](#m04), [T01](#t01), [T02](#t02) |
| N05–N06 | Nested damage-size and fixed-family mask-variant designs | [M04](#m04), [M09](#m09), [E01](#e01), [E02](#e02); exact levels are project-defined |
| N07 | Controlled synthetic degradation | [H01](#h01), [H05](#h05), [H07](#h07), [M10](#m10); procedural effects are not physical aging |
| N08 | Case/model eligibility and eleven-region policy | [Q01](#q01), [Q03](#q03), [Q07](#q07), [T05](#t05); applicability rules are project-defined |
| N09 | OpenCV Telea | [M01](#m01), [T02](#t02) |
| N10 | LaMa through IOPaint | [M04](#m04), [T03](#t03) |
| N11 | Stable Diffusion and controlled prompt/seed branches | [M05](#m05), [M07](#m07), [T04](#t04); [H05](#h05), [U06](#u06) are related work |
| N12 | Bounded SDXL partial evaluation | [M06](#m06), [T04](#t04), [E02](#e02) |
| N13–N15 | Classical, LPIPS, CLIP and DINOv2 measurements | [Q01](#q01)–[Q05](#q05) |
| N16 | Error, improvement and outside-mask diagnostics | [Q01](#q01), [Q03](#q03), [Q09](#q09), [E10](#e10) |
| N17 | Texture, colour and boundary/seam evidence | [H02](#h02), [H03](#h03), [Q06](#q06)–[Q08](#q08), [Q10](#q10)–[Q11](#q11), [T05](#t05) |
| N18–N19 | Repeated-seed scalar evidence and spatial maps | [U01](#u01)–[U07](#u07), [Q03](#q03)–[Q05](#q05), [E10](#e10) |
| N20 | Local feature and structural-affinity proxies | [Q04](#q04), [Q05](#q05), [Q06](#q06); not semantic ground truth |
| N21 | Paired multi-metric model comparison | [M09](#m09), [Q09](#q09), [E01](#e01)–[E03](#e03) |
| N22 | Additional damage-size seed coverage and maps | [M07](#m07), [U01](#u01)–[U04](#u04), [E01](#e01) |
| N23–N25 | Damage-size, mask and synthetic-degradation analyses | [M09](#m09), [H05](#h05), [E01](#e01)–[E03](#e03) |
| N26 | Grouped inference, effects, associations and stability | [E01](#e01)–[E03](#e03), [T06](#t06) |
| N27–N28 | Computational flags and metric/region/threshold ablations | [U07](#u07), [E02](#e02), [E04](#e04), [Q09](#q09); flag definitions are project-owned |
| N29 | Rule traces, threshold counterfactuals and case retrieval | [E04](#e04), [E05](#e05), [Q04](#q04), [Q05](#q05) |
| N30 | Model cards, observed compute and scaling projections | [E06](#e06), [E02](#e02), [E11](#e11), model/checkpoint records |
| N31–N33 | Model, case, painting and final evaluation reports | [H01](#h01), [E06](#e06), [E08](#e08)–[E11](#e11) |
| N34–N35 | Normalized assets, eight-page dashboard and validation | [E08](#e08)–[E11](#e11), [T07](#t07) |
| N36 | Supervisor/publication/reproducibility package | [E06](#e06), [E07](#e07), [E11](#e11) |
| N37 | Paired HINT/MAT method selection and HINT expansion decision | [M11](#m11), [M12](#m12), [M09](#m09), [E02](#e02); the 12-case pilot does not establish full-benchmark superiority |

### Research-question use

1. **How can a multi-metric evaluation framework be designed to assess
   AI-generated painting restorations beyond traditional image similarity
   metrics?** Use Q01–Q11, U07 and E01–E05 to motivate complementary evidence,
   explicit regions, disagreement and inspectable explanations. The specific
   eleven-anchor design is this project's operational choice.
2. **How do selected inpainting methods differ in restoration quality across
   broad visual categories and controlled artificial damage conditions?** Use
   H01–H05 and M01–M12 for context, then cite the project's own paired results. The five
   balanced visual categories are not independently established art-historical
   styles; sparse style metadata limits that part of the question.
3. **To what extent can uncertainty estimation from multiple restoration
   candidates identify speculative or unreliable restored regions?** Use
   U01–U07 to distinguish variability, calibration, realism and correctness.
   Our evidence concerns empirical disagreement and its measured associations,
   not a validated detector of historical error.

## 4. Heritage and painting-specific sources

<a id="h01"></a>

### H01 — Van Vijle, Hacıgüzeller and Van der Snickt (2025)

**Citation:** Aster Van Vijle, Piraye Hacıgüzeller and Geert Van der Snickt.
*Machine learning for painting conservation: a state-of-the-art review.*
npj Heritage Science 13, 437.
[Publisher article](https://www.nature.com/articles/s40494-025-01924-3).
**Fit:** Close-topic; retained and verified; review article.

- **Supports:** Locating virtual restoration within the wider conservation
  workflow, alongside imaging, pigment analysis and damage research.
- **Use here:** Introduction, synthetic-to-real limits, reporting and proposal
  scope; N01, N07, N27 and N31–N36.
- **Boundary:** A review is context, not direct validation of our models,
  synthetic masks or computational trustworthiness flags. Follow its primary
  references before making detailed claims about an individual conservation study.

<a id="h02"></a>

### H02 — Sun, Lei and Wu (2024)

**Citation:** Zengguo Sun, Yanyan Lei and Xiaojun Wu.
*Ancient paintings inpainting based on dual encoders and contextual information.*
Heritage Science 12, 266.
[Publisher article](https://www.nature.com/articles/s40494-024-01391-2).
**Fit:** Close-topic; corrected legacy title; research article.

- **Supports:** Painting-specific attention to texture, line continuity,
  contextual information and colour consistency.
- **Use here:** Motivation for separate texture, colour and seam diagnostics in
  N17 and local structural evidence in N20.
- **Boundary:** Their trained architecture, colour loss and painting data differ
  from our pretrained-baseline evaluation. We did not implement their network,
  and their results do not establish our model ranking.

<a id="h03"></a>

### H03 — Liu, Wan, Wang and Wang (2024)

**Citation:** Xiaotong Liu, Jin Wan, Nan Wang and Yuting Wang.
*Ancient Painting Inpainting Based on Multi-Layer Feature Enhancement and
Frequency Perception.* Electronics 13(16), 3309.
[Publisher article](https://www.mdpi.com/2079-9292/13/16/3309).
**Fit:** Close-topic; corrected legacy title; research article.

- **Supports:** Examining high-frequency detail and texture rather than only
  global reconstruction similarity.
- **Use here:** Related work for N17's local texture descriptors/maps and N20's
  complementary structural evidence.
- **Boundary:** MFGAN is a different trained model on different painting data.
  Gabor, LBP and co-occurrence diagnostics in our project are not an
  implementation of its frequency-perception architecture.

<a id="h04"></a>

### H04 — Hu, Yu and Zhou (2025)

**Citation:** J. Hu, Y. Yu and Q. Zhou.
*GuidePaint: lossless image-guided diffusion model for ancient mural image
restoration.* npj Heritage Science 13, 118.
[Publisher article](https://www.nature.com/articles/s40494-025-01693-z).
**Fit:** Close-topic; new; research article.

- **Supports:** The relevance of damage geometry, fine detail and multiple
  possible diffusion completions in heritage imagery.
- **Use here:** Related work around N11–N12, damage-size analysis and repeated
  outputs. Useful when discussing why one restoration is not the only plausible
  completion.
- **Boundary:** Its image-guided sampling procedure is not our fixed
  Stable Diffusion inpainting pipeline. “Lossless” is the authors' method name,
  not a guarantee of historical correctness or a label for our results.

<a id="h05"></a>

### H05 — Jiang, Ren and Cheng (2025)

**Citation:** Chao Jiang, Tiantian Ren and Zhengyun Cheng.
*All-in-one mural restoration with prompt-guided residual diffusion.*
npj Heritage Science 13, 667. Published 18 December 2025.
[Publisher article](https://www.nature.com/articles/s40494-025-02232-6).
**Fit:** Close-topic; new; research article.

- **Supports:** Considering textual guidance and semi-transparent degradation,
  rather than treating every damaged pixel as completely missing.
- **Use here:** Particularly relevant to N07/N25's synthetic effects and N11's
  damage-aware prompt discussion.
- **Boundary:** This is a separately trained residual-diffusion method.
  Our masked-removal diagnostics and scratch prompt ablation do not reproduce
  it, simulate physical aging, or prove that prompting solves thin-mask geometry.

<a id="h06"></a>

### H06 — Kachkine (2025)

**Citation:** Alex Kachkine. *Physical restoration of a painting with a digitally
constructed mask.* Nature 642, 343–350.
[Publisher record and abstract](https://www.nature.com/articles/s41586-025-09045-4).
**Fit:** Partial/context; new; research article; substantive use limited to the
accessible abstract and record.

- **Supports:** Discussing the distinction between a digital reconstruction
  proposal and an actual physical restoration workflow.
- **Use here:** Introduction, limitations and supervisor-facing scope.
- **Boundary:** This project performs no physical intervention or material
  testing. Do not infer treatment safety, reversibility or conservation
  suitability from our image metrics or from this citation alone.

<a id="h07"></a>

### H07 — Almeida, Babo and Jesus (2026)

**Citation:** Leonor Almeida, Sara Babo and Rui Jesus.
*A Review of Artificial Intelligence as a Tool for Damage Detection in Paintings:
Challenges and Limitations for Contemporary Paintings.* Heritage 9(5), 204.
Published 21 May 2026.
[Author-institution record](https://novaresearch.unl.pt/en/publications/a-review-of-artificial-intelligence-as-a-tool-for-damage-detectio/).
**Fit:** Partial/context; new; review article.

- **Supports:** The importance of material diversity, irregular damage and
  domain-specific validation when discussing painting degradation.
- **Use here:** Updating the heritage context through 2026 and qualifying
  N01/N07's controlled visual categories and synthetic effects.
- **Boundary:** Damage detection is not restoration-quality evaluation.
  We did not train a crack detector, inspect physical materials or validate
  the framework on contemporary-painting degradation.

<a id="h08"></a>

### H08 — Fontoura Júnior et al. (2023)

**Citation:** C. F. M. Fontoura Júnior, G. P. Cardim, E. S. Nascimento,
M. Colnago, W. C. de O. Casaca and E. A. da Silva.
*Assessing the Effectiveness of Inpainting Techniques for Enhancing Feature
Extraction Quality in Remote Sensing Imagery.*
ISPRS Annals X-1/W1-2023, 65–72.
[Publisher article](https://isprs-annals.copernicus.org/articles/X-1-W1-2023/65/2023/).
**Fit:** Partial/context; corrected legacy attribution; proceedings paper.

- **Supports:** Evaluating inpainting through downstream feature behavior,
  rather than assuming appearance or a pixel score answers every use case.
- **Use here:** An optional cross-domain comparison for N15/N20 and the
  discussion of task-dependent evaluation.
- **Boundary:** It is **not a painting or cultural-heritage study**.
  Remote-sensing feature extraction cannot validate our CLIP/DINOv2 measures
  or conservation conclusions.

## 5. Inpainting models, sampling and surveys

<a id="m01"></a>

### M01 — Telea (2004)

**Citation:** Alexandru Telea. *An Image Inpainting Technique Based on the Fast
Marching Method.* Journal of Graphics Tools 9(1), 25–36.
[Author-institution record](https://research.rug.nl/en/publications/an-image-inpainting-technique-based-on-the-fast-marching-method/).
**Fit:** Direct-method; retained; foundational exception.

- **Supports:** The classical fast-marching inpainting baseline used by N09.
- **Use here:** Explain local propagation and the baseline's computational role.
- **Boundary:** The paper does not establish radius 3 as optimal for paintings
  or guarantee success on every scratch. Those are implementation settings and
  empirical questions for this study.

<a id="m02"></a>

### M02 — Bertalmío, Sapiro, Caselles and Ballester (2000)

**Citation:** Marcelo Bertalmío, Guillermo Sapiro, Vicent Caselles and
Coloma Ballester. *Image Inpainting.* SIGGRAPH 2000.
[Author-institution record](https://scholars.duke.edu/publication/809318).
**Fit:** Partial/context; retained; foundational exception.

- **Supports:** Historical context for structure continuation in digital
  inpainting.
- **Use here:** A short classical-method background paragraph.
- **Boundary:** Not the Telea algorithm used in N09; no claim that we benchmarked
  this PDE method. Keep the distinction explicit rather than citing the two
  classical algorithms interchangeably.

<a id="m03"></a>

### M03 — Liu et al. (2018)

**Citation:** Guilin Liu, Fitsum A. Reda, Kevin J. Shih, Ting-Chun Wang,
Andrew Tao and Bryan Catanzaro. *Image Inpainting for Irregular Holes Using
Partial Convolutions.* ECCV, 85–100.
[CVF paper record](https://openaccess.thecvf.com/content_ECCV_2018/html/Guilin_Liu_Image_Inpainting_for_ECCV_2018_paper.html).
**Fit:** Close-topic; retained; foundational exception.

- **Supports:** Irregular masks and the importance of separating valid pixels
  from missing-region substitutes.
- **Use here:** N03–N04's mask-design rationale.
- **Boundary:** Partial convolution is not an evaluated model in this project.
  This paper does not validate our masks as real crack morphology or prescribe
  our exact painting-content restriction.

<a id="m04"></a>

### M04 — Suvorov et al. (2022)

**Citation:** Roman Suvorov et al. *Resolution-Robust Large Mask Inpainting With
Fourier Convolutions.* WACV, 2149–2159.
[CVF paper record](https://openaccess.thecvf.com/content/WACV2022/html/Suvorov_Resolution-Robust_Large_Mask_Inpainting_With_Fourier_Convolutions_WACV_2022_paper.html).
**Fit:** Direct-method; retained; conference paper.

- **Supports:** LaMa's wide-context design, Fourier convolutions and large-mask
  training rationale.
- **Use here:** N10 model selection and the reason to evaluate different mask
  sizes and structures.
- **Boundary:** Its resolution results do not establish our 768-pixel padding
  policy as optimal. Our runtime wrapper, weight artifact and measured results
  are documented separately in T03 and the model audit.

<a id="m05"></a>

### M05 — Rombach et al. (2022)

**Citation:** Robin Rombach, Andreas Blattmann, Dominik Lorenz, Patrick Esser and
Björn Ommer. *High-Resolution Image Synthesis With Latent Diffusion Models.*
CVPR, 10684–10695.
[CVF paper record](https://openaccess.thecvf.com/content/CVPR2022/html/Rombach_High-Resolution_Image_Synthesis_With_Latent_Diffusion_Models_CVPR_2022_paper.html).
**Fit:** Direct-method background; retained; conference paper.

- **Supports:** Latent-space generation and conditioning as the foundation of
  Stable Diffusion.
- **Use here:** N11's model-family explanation and discussion of generated detail.
- **Boundary:** The family paper is not the exact v1.5 inpainting checkpoint
  card. It does not prove why a particular thin scratch remains visible; that
  explanation must be framed as a hypothesis informed by our diagnostics.

<a id="m06"></a>

### M06 — Podell et al. (2024; preprint 2023)

**Citation:** Dustin Podell et al. *SDXL: Improving Latent Diffusion Models for
High-Resolution Image Synthesis.* ICLR 2024.
[ICLR paper record](https://proceedings.iclr.cc/paper_files/paper/2024/hash/081b08068e4733ae3e7ad019fe8d172f-Abstract-Conference.html).
**Fit:** Direct-method background; retained with publication-version clarification.

- **Supports:** SDXL's larger architecture and additional conditioning.
- **Use here:** Explaining the resource-aware N12 branch.
- **Boundary:** Cite T04 for the inpainting checkpoint. The family paper does
  not justify ranking our ten-case branch as a full benchmark, claiming that
  SDXL is universally superior, or claiming that we used a separate refiner.

<a id="m07"></a>

### M07 — Song, Meng and Ermon (2021; preprint 2020)

**Citation:** Jiaming Song, Chenlin Meng and Stefano Ermon.
*Denoising Diffusion Implicit Models.* ICLR 2021.
[Author preprint and conference designation](https://arxiv.org/abs/2010.02502).
**Fit:** Direct-method; new; conference paper.

- **Supports:** The DDIM sampling family used in the diffusion configurations.
- **Use here:** N11, N12 and N22 sampling and runtime descriptions.
- **Boundary:** Deterministic sampling conditional on an initial noise state
  does not mean different initial seeds produce identical images. The paper's
  speedups are not our measured runtime and do not validate a universal timeout.

<a id="m08"></a>

### M08 — Lugmayr et al. (2022)

**Citation:** Andreas Lugmayr, Martin Danelljan, Andres Romero, Fisher Yu,
Radu Timofte and Luc Van Gool. *RePaint: Inpainting Using Denoising Diffusion
Probabilistic Models.* CVPR, 11461–11471.
[CVF paper record](https://openaccess.thecvf.com/content/CVPR2022/html/Lugmayr_RePaint_Inpainting_Using_Denoising_Diffusion_Probabilistic_Models_CVPR_2022_paper.html).
**Fit:** Close-topic; new; conference paper.

- **Supports:** Diffusion inpainting under diverse mask conditions and the
  existence of multiple plausible completions.
- **Use here:** Related work for masks, damage size and pluralistic restoration.
- **Boundary:** RePaint is not Stable Diffusion inpainting and was not executed.
  Its resampling procedure is not our repeated-seed uncertainty estimator.

<a id="m09"></a>

### M09 — Quan et al. (2024)

**Citation:** Weize Quan, Jiaxi Chen, Yanli Liu, Dong-Ming Yan and Peter Wonka.
*Deep Learning-Based Image and Video Inpainting: A Survey.*
International Journal of Computer Vision 132, 2367–2400.
[Author-institution record with journal DOI](https://repository.kaust.edu.sa/items/585bcf18-117a-46b3-b84d-65f2c75001c8).
**Fit:** Close-topic; retained and verified; review article.

- **Supports:** Organizing model families, mask settings and low-level versus
  perceptual evaluation.
- **Use here:** Background, baseline selection and N21/N23–N25 discussion.
- **Boundary:** A general image/video survey does not certify heritage
  appropriateness or establish the best method on our collection. Use original
  method papers for algorithm descriptions.

<a id="m10"></a>

### M10 — Li et al. (2023)

**Citation:** Xin Li et al. *Diffusion Models for Image Restoration and
Enhancement: A Comprehensive Survey.* arXiv:2308.09388.
[Author preprint](https://arxiv.org/abs/2308.09388).
**Fit:** Close-topic; retained; cited here as the verified preprint record.

- **Supports:** Distinguishing restoration tasks, conditioning designs and
  sampling-efficiency concerns across diffusion approaches.
- **Use here:** Diffusion background, N07 task eligibility and compute limits.
- **Boundary:** Do not turn all degradation into binary inpainting, or cite this
  survey as evidence that our hardware timings or uncertainty values are
  generally calibrated.

<a id="m11"></a>

### M11 — Chen, Atapour-Abarghouei and Shum (2024)

**Citation:** Shuang Chen, Amir Atapour-Abarghouei and Hubert P. H. Shum.
*HINT: High-quality INpainting Transformer with Mask-Aware Encoding and Enhanced
Attention.* IEEE Transactions on Multimedia.
[Publisher DOI](https://doi.org/10.1109/TMM.2024.3369897) ·
[Official implementation](https://github.com/ChrisChen1023/HINT).
**Fit:** Direct method for the Notebook 37 pilot; journal article and official
implementation.

- **Supports:** HINT's mask-aware pixel-shuffle downsampling and
  spatially-activated channel attention, which preserve visible information and
  model multi-scale, long-range context.
- **Use here:** Explain why HINT was a credible second deterministic learned
  family beyond Telea, LaMa, and stochastic Stable Diffusion, and why it was
  selected for the planned expanded benchmark after the paired pilot.
- **Boundary:** The released method was trained and evaluated on general-image
  datasets, including Places2. The paper does not establish conservation
  suitability, painting-domain generality, or superiority on the full thesis
  benchmark. Those claims remain limited to Notebook 37's own 12-case evidence.

<a id="m12"></a>

### M12 — Li et al. (2022)

**Citation:** Wenbo Li, Zhe Lin, Kun Zhou, Lu Qi, Yi Wang and Jiaya Jia.
*MAT: Mask-Aware Transformer for Large Hole Image Inpainting.* CVPR, 10758–10768.
[CVF paper record](https://openaccess.thecvf.com/content/CVPR2022/html/Li_MAT_Mask-Aware_Transformer_for_Large_Hole_Image_Inpainting_CVPR_2022_paper.html) ·
[Official implementation](https://github.com/fenglinglwb/MAT).
**Fit:** Direct comparator for the Notebook 37 pilot; conference paper and
official implementation.

- **Supports:** Mask-aware transformer attention and partial-valid-token
  reasoning for large-hole image inpainting.
- **Use here:** Explain why MAT was a technically credible transformer
  comparator and why the selection pilot tested architectural capability rather
  than comparing two minor variants of the same model.
- **Boundary:** MAT was not selected for the future expansion. Notebook 37
  required a declared 512 adapter and found weaker paired visual and metric
  results. Its noncommercial implementation licence is a reuse constraint, not
  a numerical quality penalty.

## 6. Metrics, texture, colour and structural evidence

<a id="q01"></a>

### Q01 — Wang et al. (2004)

**Citation:** Zhou Wang, Alan C. Bovik, Hamid R. Sheikh and Eero P. Simoncelli.
*Image Quality Assessment: From Error Visibility to Structural Similarity.*
IEEE Transactions on Image Processing 13(4), 600–612.
[Author paper and implementation page](https://ece.uwaterloo.ca/~z70wang/research/ssim/).
**Fit:** Direct-method; retained; foundational exception.

- **Supports:** SSIM as a local structural comparison to a reference.
- **Use here:** N13 and the contiguous-region rules in N08.
- **Boundary:** SSIM is not a cultural-fidelity score. Sparse, disconnected
  masked pixels cannot simply be repackaged as an ordinary image for SSIM.
  N17's sampled boundary SSIM map is a separately declared computation.

<a id="q02"></a>

### Q02 — Horé and Ziou (2010)

**Citation:** Alain Horé and Djemel Ziou. *Image Quality Metrics: PSNR vs. SSIM.*
ICPR, 2366–2369.
[IEEE record and abstract](https://ieeexplore.ieee.org/document/5596999/).
**Fit:** Partial/context; retained; foundational exception; abstract-level use.

- **Supports:** Explaining why PSNR and SSIM answer different questions and can
  respond differently to degradation.
- **Use here:** N13 metric interpretation.
- **Boundary:** This study is not about painting conservation. Its comparison
  does not establish that either metric always follows human restoration
  preference; the original SSIM and LPIPS sources remain more central.

<a id="q03"></a>

### Q03 — Zhang et al. (2018)

**Citation:** Richard Zhang, Phillip Isola, Alexei A. Efros, Eli Shechtman and
Oliver Wang. *The Unreasonable Effectiveness of Deep Features as a Perceptual
Metric.* CVPR, 586–595.
[CVF paper record](https://openaccess.thecvf.com/content_cvpr_2018/html/Zhang_The_Unreasonable_Effectiveness_CVPR_2018_paper.html).
**Fit:** Direct-method; retained; foundational exception.

- **Supports:** LPIPS as learned perceptual distance, complementing pixel error.
- **Use here:** N14 reference distances and N18 pairwise candidate disagreement.
- **Boundary:** Pairwise LPIPS measures difference between candidates, not their
  correctness. General perceptual judgments used to develop LPIPS are not
  conservation-expert ratings of this collection.

<a id="q04"></a>

### Q04 — Radford et al. (2021)

**Citation:** Alec Radford et al. *Learning Transferable Visual Models From
Natural Language Supervision.* ICML, PMLR 139, 8748–8763.
[PMLR paper record](https://proceedings.mlr.press/v139/radford21a.html).
**Fit:** Direct-method; retained; conference paper.

- **Supports:** CLIP's pretrained image-language representation.
- **Use here:** N15 feature similarity, N18 disagreement, N20 local evidence and
  N29 contextual retrieval.
- **Boundary:** Image-embedding cosine similarity is our operational use of the
  representation, not a painting-restoration quality measure validated by the
  CLIP paper. Nearest neighbors do not establish provenance or artist intent.

<a id="q05"></a>

### Q05 — Oquab et al. (2023 preprint)

**Citation:** Maxime Oquab et al. *DINOv2: Learning Robust Visual Features without
Supervision.* arXiv:2304.07193.
[Author preprint](https://arxiv.org/abs/2304.07193);
[official implementation](https://github.com/facebookresearch/dinov2).
**Fit:** Direct-method; retained; citation uses the accessible author-preprint
version. The TMLR record was browser-gated during this check.

- **Supports:** General-purpose global and patch-level visual features.
- **Use here:** N15, N18, N20 and N29 visual similarity and retrieval.
- **Boundary:** Our local affinity/correlation diagnostics are project-defined
  proxies, not a DINOv2 authenticity, anatomy or iconography detector.
  Newer variants in the live repository do not replace our saved model identity.

<a id="q06"></a>

### Q06 — Jain et al. (2023; preprint 2022)

**Citation:** Jitesh Jain, Yuqian Zhou, Ning Yu and Humphrey Shi.
*Keys To Better Image Inpainting: Structure and Texture Go Hand in Hand.*
WACV, 208–217.
[CVF paper record](https://openaccess.thecvf.com/content/WACV2023/html/Jain_Keys_To_Better_Image_Inpainting_Structure_and_Texture_Go_Hand_WACV_2023_paper.html).
**Fit:** Close-topic; retained and verified; conference paper.

- **Supports:** Distinguishing geometric continuity from high-frequency texture.
- **Use here:** N17/N20 and discussion of metric disagreement.
- **Boundary:** We did not implement the proposed generator. This motivates
  separate diagnostics but does not validate our seam thresholds or identify
  genuine historical brushstrokes.

<a id="q07"></a>

### Q07 — Sharma, Wu and Dalal (2005)

**Citation:** Gaurav Sharma, Wencheng Wu and Edul N. Dalal.
*The CIEDE2000 Color-Difference Formula: Implementation Notes, Supplementary
Test Data, and Mathematical Observations.*
Color Research & Application 30(1), 21–30.
[Author paper, test data and implementation notes](https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/).
**Fit:** Direct-method; new; foundational exception.

- **Supports:** Correct interpretation and implementation checking of CIEDE2000.
- **Use here:** N17 colour evidence under the declared sRGB-to-Lab, D65,
  2-degree-observer convention.
- **Boundary:** Digital colour difference is not pigment identification.
  Universal “visible” or “acceptable” thresholds cannot be inferred for every
  display, viewing condition and painting from this formula alone.

<a id="q08"></a>

### Q08 — Ding et al. (2020 online/preprint; journal issue 2022)

**Citation:** Keyan Ding, Kede Ma, Shiqi Wang and Eero P. Simoncelli.
*Image Quality Assessment: Unifying Structure and Texture Similarity.*
IEEE Transactions on Pattern Analysis and Machine Intelligence 44(5), 2567–2581.
[Author record](https://www.cns.nyu.edu/~lcv/pubs/makeAbs.php?loc=Ding20);
[author preprint](https://arxiv.org/abs/2004.07728).
**Fit:** Close-topic; new; DISTS research.

- **Supports:** The distinction between texture appearance and exact pixelwise
  alignment, including tolerance to texture resampling.
- **Use here:** Related work for N17 and the limitations of a single fidelity
  measure.
- **Boundary:** **DISTS is not computed by the completed pipeline.** Our
  LBP/Gabor/GLCM and local texture error measures must not be relabeled DISTS,
  including when adapting old UI mockups.

<a id="q09"></a>

### Q09 — Blau and Michaeli (2018)

**Citation:** Yochai Blau and Tomer Michaeli. *The Perception-Distortion Tradeoff.*
CVPR, 6228–6237.
[CVF paper record](https://openaccess.thecvf.com/content_cvpr_2018/html/Blau_The_Perception-Distortion_Tradeoff_CVPR_2018_paper.html).
**Fit:** Close-topic; new; foundational exception.

- **Supports:** Separating distributional perceptual realism from fidelity to a
  particular reference.
- **Use here:** RQ1, multi-metric comparison and the central thesis distinction.
- **Boundary:** The theoretical setting is not a proof that the visually better
  candidate must score worse on every metric, or that our measured model
  ordering is inevitable.

<a id="q10"></a>

### Q10 — Haralick, Shanmugam and Dinstein (1973)

**Citation:** Robert M. Haralick, K. Shanmugam and Its'hak Dinstein.
*Textural Features for Image Classification.*
IEEE Transactions on Systems, Man, and Cybernetics SMC-3(6), 610–621.
[Paper copy hosted by Stanford](https://web.stanford.edu/class/biomedin260/lectures/8/Haralick%20-%20Texture%20Features.pdf).
**Fit:** Direct-method background; new; foundational exception.

- **Supports:** Gray-level co-occurrence-based texture descriptors.
- **Use here:** N17's GLCM features; T05 documents the implemented functions.
- **Boundary:** Quantization, distances, directions and comparison rules are
  declared in our configuration. The descriptors do not identify an artist's
  brushwork or prove material continuity.

<a id="q11"></a>

### Q11 — Ojala, Pietikäinen and Mäenpää (2002)

**Citation:** Timo Ojala, Matti Pietikäinen and Topi Mäenpää.
*Multiresolution Gray-Scale and Rotation Invariant Texture Classification with
Local Binary Patterns.* IEEE TPAMI 24(7), 971–987.
[IEEE record](https://ieeexplore.ieee.org/document/1017623/).
**Fit:** Direct-method background; new; foundational exception.

- **Supports:** Uniform local binary patterns as compact texture descriptors.
- **Use here:** N17's LBP histogram comparison.
- **Boundary:** The project uses one declared local descriptor configuration,
  not the complete paper's multiresolution classification experiment.
  Descriptor agreement is not authentication.

## 7. Uncertainty, self-consistency and reliability

<a id="u01"></a>

### U01 — Hüllermeier and Waegeman (2021)

**Citation:** Eyke Hüllermeier and Willem Waegeman.
*Aleatoric and epistemic uncertainty in machine learning: an introduction to
concepts and methods.* Machine Learning.
[Publisher article](https://link.springer.com/article/10.1007/s10994-021-05946-3).
**Fit:** Partial/context; new; conceptual review.

- **Supports:** Precise uncertainty terminology and distinctions between sources
  of uncertainty.
- **Use here:** N18/N19/N22 interpretation and RQ3.
- **Boundary:** Four random seeds do not separate epistemic and aleatoric
  uncertainty. Our fixed pretrained model produces empirical sample variability,
  not a posterior over independently trained model parameters.

<a id="u02"></a>

### U02 — Angelopoulos et al. (2022)

**Citation:** Anastasios N. Angelopoulos et al.
*Image-to-Image Regression with Distribution-Free Uncertainty Quantification
and Applications in Imaging.* ICML, PMLR 162, 717–730.
[PMLR paper record](https://proceedings.mlr.press/v162/angelopoulos22a.html).
**Fit:** Partial/context; new; conference paper.

- **Supports:** Understanding what a statistically calibrated image uncertainty
  procedure requires beyond plotting candidate spread.
- **Use here:** Contrast with N18/N19/N22's uncalibrated diagnostics.
- **Boundary:** Its calibrated intervals and assumptions are not implemented
  here. We cannot claim confidence coverage from standard-deviation heatmaps
  or an association between variability and reference error.

<a id="u03"></a>

### U03 — Belhasin et al. (2023 preprint, revised 2024)

**Citation:** Omer Belhasin, Yaniv Romano, Daniel Freedman, Ehud Rivlin and
Michael Elad. *Principal Uncertainty Quantification with Spatial Correlation
for Image Restoration Problems.* arXiv:2305.10124, version 3.
[Author preprint](https://arxiv.org/abs/2305.10124).
**Fit:** Close-topic; new; cited version is the verified author preprint.

- **Supports:** The importance of spatial correlation when describing
  uncertainty in reconstructed images, including inpainting.
- **Use here:** Discussing what independent per-pixel spread maps can miss.
- **Boundary:** We did not implement PUQ, principal-component uncertainty
  regions or its coverage procedure. A four-seed RGB map is not an equivalent
  approximation with inherited guarantees.

<a id="u04"></a>

### U04 — Kou et al. (2024)

**Citation:** Siqi Kou, Lei Gan, Dequan Wang, Chongxuan Li and Zhijie Deng.
*BayesDiff: Estimating Pixel-wise Uncertainty in Diffusion via Bayesian Inference.*
ICLR 2024.
[ICLR paper record](https://proceedings.iclr.cc/paper_files/paper/2024/hash/49f42aafbcce59b2665640cb9f3d794f-Abstract-Conference.html).
**Fit:** Close-topic; new; conference paper.

- **Supports:** Pixel-level uncertainty as a meaningful object of study for
  diffusion outputs.
- **Use here:** Related work for spatial uncertainty and artifact inspection.
- **Boundary:** BayesDiff uses Bayesian machinery, including a last-layer
  Laplace approximation. It is not our across-seed variance calculation; its
  quality filtering does not validate our rule thresholds.

<a id="u05"></a>

### U05 — Chen et al. (2024)

**Citation:** Tianyi Chen, Jianfu Zhang, Yan Hong, Yiyi Zhang and Liqing Zhang.
*Assessing Image Inpainting via Re-Inpainting Self-Consistency Evaluation.*
arXiv:2405.16263.
[Author preprint](https://arxiv.org/abs/2405.16263).
**Fit:** Close-topic; replaces an unnamed legacy reference; preprint.

- **Supports:** Considering consistency-based evaluation when a single
  reference comparison favors one of several plausible completions.
- **Use here:** RQ3 related work and discussion of reference-dependent metrics.
- **Boundary:** Their procedure uses re-inpainting passes; ours compares seeds
  for an unchanged case/prompt/configuration. Neither the procedure nor their
  human-judgment validation was reproduced by our study.

<a id="u06"></a>

### U06 — Giakoumoglou et al. (2025)

**Citation:** Paschalis Giakoumoglou, Dimitrios Karageorgiou, Symeon Papadopoulos
and Panagiotis C. Petrantonakis.
*SAGI: Semantically Aligned and Uncertainty Guided AI Image Inpainting.*
ICCV, 16090–16101.
[CVF paper record](https://openaccess.thecvf.com/content/ICCV2025/html/Giakoumoglou_SAGI_Semantically_Aligned_and_Uncertainty_Guided_AI_Image_Inpainting_ICCV_2025_paper.html).
**Fit:** Close-topic; new; conference paper.

- **Supports:** Joint attention to prompt semantics, uncertainty-guided
  selection and human assessment of generated inpainting.
- **Use here:** A recent comparison for N11's prompt ablation, N18's
  variability and N27's computational review signals.
- **Boundary:** SAGI optimizes realistic manipulations and uses different
  prompt/evaluation machinery. Realism or difficulty detecting an edit is not
  fidelity to an original painting. We did not use SAGI or its dataset.

<a id="u07"></a>

### U07 — Cohen et al. (2024)

**Citation:** Regev Cohen, Idan Kligvasser, Ehud Rivlin and Daniel Freedman.
*Looks Too Good To Be True: An Information-Theoretic Analysis of Hallucinations
in Generative Restoration Models.* NeurIPS 37.
[NeurIPS paper record](https://proceedings.neurips.cc/paper_files/paper/2024/hash/2847d43f17410c5beb25b2736c3ae778-Abstract-Conference.html).
**Fit:** Close-topic; new; conference paper; high-priority discussion source.

- **Supports:** A principled distinction between perceptual quality and
  reliability, with experiments including inpainting.
- **Use here:** The central thesis argument, RQ3 and limitations of plausible
  generated detail.
- **Boundary:** Its theoretical uncertainty/perception quantities are not our
  four-seed statistics. The paper does not turn every flagged candidate into
  a proven hallucination, or establish historical truth for a reference image.

## 8. Statistics, explainability, reporting and reproducibility

<a id="e01"></a>

### E01 — Saravanan, Berman and Sober (2020)

**Citation:** Varun Saravanan, Gordon J. Berman and Samuel J. Sober.
*Application of the hierarchical bootstrap to multi-level data in neuroscience.*
Neuron, Behavior, Data Analysis, and Theory 3(5).
[Author manuscript](https://pmc.ncbi.nlm.nih.gov/articles/PMC7906290/).
**Fit:** Partial/context; new; research article.

- **Supports:** Respecting dependence in nested observations and avoiding
  inflated sample sizes.
- **Use here:** Painting-level clustering in N21/N23–N26 and repeated-seed
  comparisons.
- **Boundary:** Our painting-cluster bootstrap is not necessarily the paper's
  full multilevel resampling procedure. Five paintings do not become a large
  sample because they produce many seeds, masks or pixels.

<a id="e02"></a>

### E02 — Bouthillier et al. (2021)

**Citation:** Xavier Bouthillier et al.
*Accounting for Variance in Machine Learning Benchmarks.* MLSys 2021.
[Author preprint](https://arxiv.org/abs/2103.03098).
**Fit:** Partial/context; new; conference paper.

- **Supports:** Explicit treatment of benchmark variation and caution about
  conclusions based on one experimental realization.
- **Use here:** Matched comparisons, prompt/mask/region sensitivity, stability
  analyses and compute-aware scope.
- **Boundary:** Their training and hyperparameter experiments differ from our
  frozen pretrained inference. This citation does not justify tuning on the
  evaluation paintings or selecting the best seed after seeing its metrics.

<a id="e03"></a>

### E03 — Benjamini and Hochberg (1995)

**Citation:** Yoav Benjamini and Yosef Hochberg.
*Controlling the False Discovery Rate: A Practical and Powerful Approach to
Multiple Testing.* Journal of the Royal Statistical Society, Series B 57(1),
289–300.
[Publisher record](https://rss.onlinelibrary.wiley.com/doi/abs/10.1111/j.2517-6161.1995.tb02031.x).
**Fit:** Direct-method; new; foundational exception.

- **Supports:** The declared Benjamini–Hochberg multiple-testing correction.
- **Use here:** N26 and other analyses whose saved contract specifies this method.
- **Boundary:** Adjustment does not repair pseudoreplication or guarantee FDR
  control under arbitrary dependence. Describe testing families, dependence
  assumptions, effect sizes and uncertainty intervals, not adjusted p-values alone.

<a id="e04"></a>

### E04 — Barredo Arrieta et al. (2020)

**Citation:** Alejandro Barredo Arrieta et al.
*Explainable Artificial Intelligence (XAI): Concepts, taxonomies, opportunities
and challenges toward responsible AI.* Information Fusion 58, 82–115.
[Author-institution record](https://digibug.ugr.es/handle/10481/77982).
**Fit:** Partial/context; new; review article.

- **Supports:** Distinguishing explanation types and communicating the limits
  of transparency.
- **Use here:** N27/N29 rule-based explanations, spatial evidence and retrieval.
- **Boundary:** We explain computational decisions and their evidence, not the
  full internal reasoning of a diffusion network. No SHAP, LIME or Grad-CAM
  computation should be claimed merely because it appears in XAI literature.

<a id="e05"></a>

### E05 — Guidotti (2024 issue; online 2022)

**Citation:** Riccardo Guidotti. *Counterfactual explanations and how to find them:
literature review and benchmarking.* Data Mining and Knowledge Discovery 38,
2770–2824.
[Publisher article](https://link.springer.com/article/10.1007/s10618-022-00831-6).
**Fit:** Partial/context; new; review and benchmarking article.

- **Supports:** Explaining what change would alter a decision and distinguishing
  validity, plausibility and actionability.
- **Use here:** N29's “what would change this flag?” explanations.
- **Boundary:** Crossing a metric threshold does not establish a feasible image
  edit, causal intervention or conservation recommendation. Our counterfactuals
  concern the declared rule, not a generated alternative restoration.

<a id="e06"></a>

### E06 — Mitchell et al. (2019)

**Citation:** Margaret Mitchell et al. *Model Cards for Model Reporting.*
FAT* 2019. [Author preprint](https://arxiv.org/abs/1810.03993).
**Fit:** Direct reporting principle; retained; foundational exception.

- **Supports:** Structured disclosure of intended use, evaluation conditions,
  limitations and relevant group differences.
- **Use here:** N30 model/method cards and N31 model reports.
- **Boundary:** Our cards describe this evaluation of pretrained artifacts;
  they cannot recover undisclosed training provenance or certify safe use.
  A classical Telea method card should not invent training data.

<a id="e07"></a>

### E07 — Gebru et al. (2021)

**Citation:** Timnit Gebru et al. *Datasheets for Datasets.*
Communications of the ACM 64(12), 86–92.
[Author-institution publication record](https://www.microsoft.com/en-us/research/publication/datasheets-for-datasets/).
**Fit:** Direct documentation principle; retained; journal article.

- **Supports:** Recording dataset motivation, composition, collection,
  intended uses and limitations.
- **Use here:** N01's artwork metadata, N08 contracts and N36 reproducibility.
- **Boundary:** A source ledger is not proof of complete metadata, licensing
  clearance or representativeness. The project's 18/50 style/date/medium
  coverage must remain explicit.

<a id="e08"></a>

### E08 — Heer and Shneiderman (2012)

**Citation:** Jeffrey Heer and Ben Shneiderman.
*Interactive Dynamics for Visual Analysis.* Communications of the ACM 55(4),
45–54.
[Author-lab record](https://idl.uw.edu/papers/interactive-dynamics).
**Fit:** Partial/context; retained; foundational exception.

- **Supports:** Filtering, selection and coordinated visual exploration.
- **Use here:** N34/N35 dashboard navigation and case-to-evidence inspection.
- **Boundary:** Design principles are not a user study of this application.
  Supervisor approval of the layout is not a measured usability experiment.

<a id="e09"></a>

### E09 — Munzner (2014)

**Citation:** Tamara Munzner. *Visualization Analysis and Design.*
CRC Press/A K Peters.
[Publisher book record](https://www.routledge.com/Visualization-Analysis-and-Design/Munzner/p/book/9781466508910).
**Fit:** Partial/context; retained; foundational exception; design reference.

- **Supports:** Matching visual encodings and interactions to data and user tasks.
- **Use here:** Reports, regional diagnostics and dashboard organization.
- **Boundary:** Cited for general design framing; this audit checked the
  publisher description, not every chapter. The book does not validate the
  application's scientific claims or prove its effectiveness.

<a id="e10"></a>

### E10 — Crameri, Shephard and Heron (2020)

**Citation:** Fabio Crameri, Grace E. Shephard and Philip J. Heron.
*The misuse of colour in science communication.*
Nature Communications 11, 5444.
[Author-institution article record](https://durham-repository.worktribe.com/output/1287014/the-misuse-of-colour-in-science-communication).
**Fit:** Direct communication principle; new; research article.

- **Supports:** Avoiding misleading colour scales and considering colour-vision
  accessibility.
- **Use here:** N16/N17/N19/N22 maps, captions and dashboard interpretation.
- **Boundary:** Normalized overlays are display products, not calibrated
  probabilities. Cross-case colour comparison requires compatible scales;
  raw numeric maps and units remain the measurement source.

<a id="e11"></a>

### E11 — Pineau et al. (2021)

**Citation:** Joelle Pineau et al. *Improving Reproducibility in Machine Learning
Research (A Report from the NeurIPS 2019 Reproducibility Program).*
JMLR 22(164), 1–20.
[JMLR paper record](https://www.jmlr.org/papers/v22/20-303.html).
**Fit:** Direct reporting principle; new; journal article.

- **Supports:** Making claims inspectable through clear experimental details,
  code and reproducibility documentation.
- **Use here:** Seeds, configurations, model revisions, manifests and N36's
  bounded review package.
- **Boundary:** A clean repository, requirements recipe or successful saved
  notebook does not prove fresh-install or cross-hardware bitwise reproduction.
  Historical manifests remain evidence of their actual runs.

## 9. Technical sources and implementation provenance

These are living documentation pages, checked on 2026-09-04. Their current
package versions are **not** substitutes for the versions recorded in producer
manifests. Reuse a paper for its scientific method and a technical record for
the exact software behavior; do not confuse those roles.

<a id="t01"></a>

### T01 — Hugging Face Diffusers: inpainting

[Official inpainting guide](https://huggingface.co/docs/diffusers/en/using-diffusers/inpaint).

White mask pixels indicate the area to repaint and black pixels the retained
area. Supports input/mask interpretation and pipeline options in N03–N04 and
N11–N12. Our exact-mask compositing, thresholds and padding policy are additional
project constraints; the guide does not guarantee unchanged outside pixels for
every pipeline configuration.

<a id="t02"></a>

### T02 — OpenCV: inpainting API

[Official API](https://docs.opencv.org/4.x/d7/d8b/group__photo__inpaint.html).

Supports nonzero-mask semantics, the inpainting radius and the distinction
between INPAINT_TELEA and INPAINT_NS. N09 uses Telea; the availability of another
API flag is not evidence that the other method was evaluated.

<a id="t03"></a>

### T03 — IOPaint: runtime wrapper

[Maintainer repository](https://github.com/Sanster/IOPaint).

Supports the implementation context for the N10 LaMa wrapper. The specific
weight artifact, wrapper version and hash belong to the saved model audit and
producer manifest. A current repository README is not evidence that every
listed model ran locally.

<a id="t04"></a>

### T04 — Exact diffusion checkpoint records

- [Stable Diffusion v1.5 inpainting card](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting)
- [SDXL inpainting 0.1 card](https://huggingface.co/diffusers/stable-diffusion-xl-1.0-inpainting-0.1)

Use these with M05–M06 to distinguish a model family from the actual inpainting
checkpoint. The project's recorded revisions are
8a4288a76071f7280aedbdb3253bdb9e9d5d84bb (SD) and
115134f363124c53c7d878647567d04daf26e41e (SDXL).
Live cards establish the documented checkpoint context; saved manifests retain
the execution-time provenance. This log is not a fresh legal/license audit.

<a id="t05"></a>

### T05 — scikit-image: texture and colour APIs

- [Feature API](https://scikit-image.org/docs/stable/api/skimage.feature.html)
- [Colour API](https://scikit-image.org/docs/stable/api/skimage.color.html)

Supports local binary patterns, co-occurrence features, RGB/Lab conversion and
CIEDE2000 implementation details. The N17
[configuration](../config/evaluation/local_consistency.yaml) defines the actual
quantization, distances, windows, low-chroma hue handling, Gabor backend and
histogram-CDF approximation. Do not describe every histogram distance as the
same physical or perceptual quantity.

<a id="t06"></a>

### T06 — SciPy: statistical implementation

[Official Friedman-test documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.friedmanchisquare.html).

Supports the repeated-measure test's API and its approximation caveats.
The N26 [configuration](../config/evaluation/grouped_statistical_analysis.yaml)
and helper define painting-level aggregation, paired effects, bootstrap
procedures and correction families. SciPy documentation does not establish
validity of every small-sample or dependent-data application.

<a id="t07"></a>

### T07 — Streamlit: application execution and caching

[Official caching documentation](https://docs.streamlit.io/develop/concepts/architecture/caching).

Supports implementation discussion for a responsive read-only evidence browser.
The project's checksum-verified assets and candidate allow-list are specified in
[the numerical dashboard contract](dashboard_numeric_metrics.md).
Caching and deployment are engineering choices, not restoration-quality evidence
or a guarantee of continuous free-hosting availability.

## 10. Project-specific choices: do not invent literature support

The following are declared operational choices whose exact values come from
the repository, not prescriptions found in the papers:

- 50 paintings, five balanced broad visual categories and the available metadata;
- 768 × 768 aspect-preserving preprocessing with recorded content bounds;
- five canonical mask conditions and controlled white missing-region encoding;
- damage-size targets of 2%, 4%, 6%, 8%, 10%, 15% and 20%;
- eleven registered regions, an eight-pixel bounding-box margin and three-pixel
  boundary bands;
- exact-mask compositing and eligibility rules for synthetic masked removal;
- the generic versus scratch-aware prompt wording and four seeds 2026–2029;
- N18's 130 groups/520 candidates/780 pairs plus N22's 35 groups/210 pairs;
- the eleven separate quality anchors and their directional ranking summaries;
- rule-derived review flags, thresholds and report-example selection policies;
- SDXL's ten-case scope and bounded execution budgets.
- Notebook 37's 12 paired cases, 24 candidates, native-768 HINT run, 512-adapted
  MAT run, and the recorded HINT selection.

The full case registry has 525 rows; 410 cases are eligible per principal
restoration method. The downstream reporting population contains 1,785
candidates, not every generated output. N11 contains 1,330 SD candidates and N22
adds 105. These counts and their exclusions are explained in the methodology
guide and producer records, not justified by a citation.

Notebook 37 adds 24 separately owned pilot candidates. They are not appended to
the frozen 1,785-candidate reporting catalog or treated as a completed fourth
full-model benchmark.

In particular:

- We compute no universal combined quality, uncertainty or trustworthiness score.
- DISTS, PUQ, BayesDiff, RePaint and SAGI are related work, not executed additions.
- Feature/affinity maps and texture descriptors are not authentication tools.
- Flags request review; they are not expert failure labels or conservation approval.
- No source here makes four seeds sufficient for a general confidence guarantee.
- Comparing five-painting trajectories does not isolate independent category effects.

## 11. Reading and thesis-writing priorities

### First pass: central argument and closest recent work

Read H01, H02, H04–H05, Q09 and U07 first. Together they help position the
framework around heritage context, local consistency, prompt/degradation
differences and the distinction between plausible appearance and reliability.

Then read U02–U06 for RQ3. The most useful contrast is between our transparent,
empirical repeated-seed evidence and methods that require additional calibration,
Bayesian estimation, re-inpainting or prompt-distribution machinery.

### Second pass: methods actually used

Use M01, M04–M07, M11–M12, Q01, Q03–Q07, Q10–Q11 and T01–T06 when writing the methods.
Keep the mathematical method, package implementation and project configuration
separate. This is especially important for colour space, local regions, model
revisions and seed arithmetic.

### Third pass: inference and delivery

Use E01–E03 for dependence, variation and statistical interpretation;
E04–E05 for bounded explanations; and E06–E11 for cards, evidence presentation
and reproducibility. H06–H08 are useful partial matches, but should not carry
the thesis's main claim of conservation relevance.

Before inserting a detailed numerical claim, theorem or comparison from a
source into the thesis, read the relevant full-text section and record the
table/page and experimental conditions. Prefer the verified version of record
when accessible, retain preprint-version distinctions, and do not cite abstracts
as if they were independently reproduced findings.

**Safe contribution framing:** this project assembles and evaluates a
traceable, region-aware, multi-evidence framework on a controlled painting
benchmark, including repeated-seed and sensitivity analysis and an inspectable
dashboard. This literature search does not establish a “first-ever” claim.
