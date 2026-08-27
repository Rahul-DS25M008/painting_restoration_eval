# Illustrative Report Structure: LaMa Restoration Performance

## Status and intended use

This document is a design reference for planning an important report before its
notebook implementation cells are generated. It demonstrates the expected
narrative quality, visual hierarchy, evidence balance, and information density of
a model-performance report.

It is **not** a mandatory template. Reports about colour, seam behaviour,
uncertainty, robustness, semantic evidence, case studies, human evaluation, model
comparison, or final thesis synthesis must use structures suited to their own
scientific questions.

All findings, values, case identifiers, thresholds, and plots described below are
**illustrative only**. They must never be copied into an implemented report or
treated as experimental evidence.

## Report definition

**Illustrative title:** Painting Restoration Evaluation Report: LaMa Restoration
Performance

**Purpose:** Give a supervisor or thesis reader a standalone five-to-ten-minute
understanding of what LaMa did, where it worked, where it failed, and what evidence
supports those conclusions.

**Audience:** Supervisor, examiner, or researcher. The reader should not need to
inspect the notebook or canonical CSV files to understand the main findings.

**Philosophy:** Results first. Include methodology only where it is necessary to
interpret the results. Keep detailed tables and provenance in canonical outputs
instead of turning the report into an exhaustive metric dump.

## Proposed narrative flow

### 1. Executive summary

**Purpose:** Give the reader the scope, main evidence-supported finding, principal
strength, principal weakness, and important caution within approximately one
screen.

**Illustrative rendering:**

> LaMa was evaluated across 410 restoration cases from 50 paintings, spanning
> canonical missing-region damage, damage-size sensitivity, mask robustness, and
> selected synthetic-degradation experiments.
>
> **Illustrative overall finding:** LaMa generally improved damaged images relative
> to their clean references. Its strongest performance occurred for localized
> missing regions, while performance weakened as damage became larger or
> structurally ambiguous.

| Illustrative KPI | Illustrative value |
|---|---:|
| Evaluated cases | 410 |
| Cases with improved LPIPS | 84% |
| Cases with improved masked-region MAE | 79% |
| Strongest damage group | Small/local loss |
| Principal weakness | Large structural loss |

No large metric table belongs here.

### 2. What was evaluated?

**Scientific purpose:** Establish the population, comparison baseline, evidence
families, and experimental coverage needed to interpret the findings.

**Planned visual:**

```text
Clean painting -> controlled damage -> LaMa -> restored image -> evaluation
```

| Illustrative dimension | Illustrative scope |
|---|---|
| Paintings | 50 |
| Restoration cases | 410 |
| Resolution | 768 x 768 |
| Experiments | Canonical, damage size, mask robustness, synthetic |
| Evidence | Classical, LPIPS, feature, texture, colour, seam/local |

Use two or three sentences to explain the clean reference, damaged baseline, and
eligible comparison population. Environment versions and checksums remain in the
technical provenance layer.

### 3. What does a restoration look like?

**Scientific purpose:** Visually establish what successful and difficult
restoration mean before introducing aggregate statistics.

**Planned visual panel:**

```text
Clean reference | Damaged input | Mask | LaMa restoration | Error map
```

Show one deterministic representative or median case and one difficult case.
Each example receives a short caption and only three to five measurements relevant
to its interpretation.

**Illustrative caption:**

> LaMa reconstructs the localized missing region while preserving surrounding
> content. Masked-region MAE decreases from 31.4 to 9.8 and LPIPS decreases from
> 0.184 to 0.071. Values are illustrative.

The images illustrate an aggregate conclusion; they do not establish it.

### 4. Overall restoration performance

**Scientific question:** Does restoration generally move damaged images toward
the clean references, and do distinct evidence families agree?

**Planned evidence:** One paired-change or distribution figure plus a compact
summary containing a small representative set of evidence families.

| Illustrative evidence family | Illustrative result |
|---|---:|
| Pixel fidelity | 79% improved |
| Structural fidelity | 74% improved |
| Perceptual similarity | 84% improved |
| Feature similarity | 81% improved |

**Illustrative interpretation:** Perceptual improvement is stronger than exact
pixel reconstruction, suggesting that locally plausible structure may be recovered
without precisely reproducing the reference pixels.

Detailed metric values remain in canonical machine-readable tables.

### 5. Where does the method work best?

**Scientific question:** How does restoration behaviour vary across damage or
experiment groups?

**Planned evidence:** A compact grouped-effect plot, eligible group counts, and at
most one representative image for each scientifically meaningful category.

| Illustrative damage group | Illustrative performance | Illustrative interpretation |
|---|---|---|
| Small loss | Strong | Local texture and context are sufficient |
| Thin scratch | Strong | Narrow missing structure is constrained |
| Mixed damage | Moderate | Reconstruction requirements are heterogeneous |
| Large loss | Weakest | Less contextual information is available |

The implemented report must retain painting-level or repeated-case dependency and
must not interpret candidate rows as independent paintings.

### 6. Damage-size response

**Scientific question:** Does performance change as damaged-content percentage
increases?

**Planned visual:** A damage-size response curve with group counts and uncertainty
or dispersion appropriate to the validated statistical unit, followed by a matched
visual sequence at small, moderate, and large damage.

```text
2% damage          10% damage         20% damage
Damaged | Restored Damaged | Restored Damaged | Restored
```

**Illustrative interpretation:** Performance remains stable for small damage but
declines beyond approximately 10-15% damaged content. This statement is
illustrative and must not be assumed during implementation.

### 7. Mask-geometry robustness

**Scientific question:** Does the conclusion remain stable across different mask
locations or geometries at comparable damage size?

**Planned evidence:** One matched case panel and one robustness summary. State the
number of paintings, mask realizations, and valid comparison groups.

**Illustrative result:** The direction of the restoration conclusion remains
stable in 87% of eligible robustness groups. This value is illustrative.

### 8. Boundary and local consistency

**Scientific question:** Does the restored area blend with its immediate
surroundings without altering unmasked content?

**Planned visual:**

```text
Damaged crop | Restored crop | Boundary overlay | Seam/error map
```

Use a small number of boundary or local-consistency measurements and explain the
spatial region for every value. Heatmaps must define scale, normalization, and
cross-panel comparability.

### 9. Failure taxonomy

**Scientific purpose:** Make recurring weaknesses and their consequences visible.

| Illustrative failure | Illustrative frequency | Illustrative severity |
|---|---:|---|
| Structural mismatch | 12% | Moderate/high |
| Texture repetition | 8% | Moderate |
| Boundary seam | 5% | Low/moderate |

Only report defensible frequencies produced by validated taxonomy evidence. If no
validated frequency exists, present qualitative examples without inventing one.

### 10. Balanced evidence gallery

**Scientific purpose:** Show a deliberately balanced and reproducibly selected set
of cases rather than a promotional gallery.

Recommended selection roles:

- representative or median eligible case;
- strong case under a predeclared multi-evidence rule;
- difficult or failure-flagged case;
- case with scientifically relevant metric disagreement;
- optional case from a distinct damage or experiment group.

Every case must state its selection rule. Avoid separate overlapping galleries for
typical examples, failures, and best/worst cases when one balanced gallery can
communicate them more efficiently.

### 11. Metric or evidence disagreement

**Scientific question:** Where do pixel, perceptual, feature, spatial, or semantic
evidence lead to different interpretations?

**Illustrative case:**

| Illustrative measurement | Illustrative change |
|---|---:|
| Masked-region MAE | 4% improvement |
| LPIPS | 31% improvement |

**Illustrative interpretation:** The restoration is perceptually coherent but does
not precisely reproduce the clean reference details. The report preserves this
disagreement instead of hiding it in a combined score.

### 12. Overall assessment

**Purpose:** Synthesize rather than repeat the executive summary.

**Illustrative synthesis:**

> The illustrative evidence supports LaMa as a fidelity-oriented method for
> localized painting damage. Large missing regions remain difficult because
> locally plausible texture does not guarantee recovery of reference structure.

Use a small strengths/cautions card if it improves readability.

### 13. Scope and limitations

Keep this short, while also placing limitations next to affected findings earlier
in the report. Possible limitations include:

- controlled or synthetic damage differs from naturally aged material;
- reference similarity is not conservation correctness;
- generic perceptual and feature metrics are not conservation-specific;
- partial model or experiment coverage restricts comparability;
- human expert evaluation remains complementary.

The report must repeat the project-level caution where required:

> Visual plausibility is not equivalent to historical or restoration
> trustworthiness.

### 14. Technical appendix and provenance

Place this at the bottom or in a collapsible section. It may include:

- run ID and validation status;
- Git commit and dirty status;
- report and model/configuration versions;
- evaluated population and exclusions;
- input artifact run IDs;
- canonical output references;
- configuration checksums where useful.

The appendix supports reproducibility without dominating the first-time reading
experience.

## Illustrative visual hierarchy

```text
+---------------------------------------------------------+
| LAMA RESTORATION PERFORMANCE                            |
| High-level evaluation report                            |
| 410 cases | 84% LPIPS improved | 79% MAE improved      |
+---------------------------------------------------------+

EXECUTIVE SUMMARY
Short evidence-supported conclusion and caution

WHAT WAS EVALUATED?
Clean -> damage -> restoration -> evaluation

WHAT DOES RESTORATION LOOK LIKE?
[Clean] [Damaged] [Mask] [Restored] [Error map]

OVERALL AND GROUPED PERFORMANCE
[Paired improvement figure] [Damage-group figure]

DAMAGE SIZE AND MASK ROBUSTNESS
[Response curve] [Matched visual examples]

BOUNDARY AND LOCAL EVIDENCE
[Restoration crop] [Boundary overlay] [Seam map]

FAILURES AND BALANCED CASES
[Representative] [Strong] [Failure] [Disagreement]

OVERALL ASSESSMENT
Supported findings | uncertainties | practical interpretation

LIMITATIONS
TECHNICAL PROVENANCE
```

## Approval checklist demonstrated by this mock-up

Before report-cell generation, the notebook-specific design should confirm:

- audience, purpose, scientific questions, and available evidence;
- proposed narrative flow and information density;
- source artifact for every planned quantitative or visual component;
- statistical unit, denominators, dependencies, and partial coverage;
- deterministic representative-case selection rules;
- appropriate successes, failures, and disagreement examples;
- report-owned assets versus upstream links;
- limitations positioned near affected findings;
- validation rules for the rendered HTML and linked assets;
- user approval of the structure.
