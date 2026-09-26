# Painting Restoration Thesis Refactoring and Implementation Guidelines

## 1. Document status

This document is the approved project-wide implementation contract for refactoring and extending the repository for the thesis:

**Trustworthy Evaluation Frameworks for AI-Assisted Painting Restoration**

It governs notebook design, helper modules, configuration, paths, generated artifacts, validation, manifests, reporting, dashboard preparation, reproducibility, and migration from the current repository layout.

The repository's validated 50-painting implementation is preserved at Git tag
`pilot-50-complete`. As of 2026-09-09, the working tree contains the approved
balanced 300-painting raw collection and has entered a controlled minimal-delta
rerun of Notebooks 01–36. Existing notebook structure, helper APIs, schemas,
stable identifiers, output roots, evidence separation, and interpretation
boundaries remain binding unless a notebook-specific contract explicitly
justifies a change.

The completed HINT-versus-MAT method-selection study is identified as Decision
Notebook D01. It remains frozen 12-case decision evidence. HINT is introduced to
the full benchmark only through the new production Notebook 12A; D01 is not
rerun or relabelled as a full evaluation.

The approved eight-page dashboard remains publicly deployed at
[the Streamlit application](https://fhtw-painting-restoration.streamlit.app/),
but it continues to represent the tagged 50-painting evidence until the entire
controlled-300 dependency chain, dashboard validation, and package rerun pass.
Mixed 50/300 claims must never be shown as one completed study.

The central methodological boundary remains:

> Visual plausibility is not equivalent to historical correctness, conservation approval, or restoration trustworthiness.

## 2. Approved architectural decisions

The following decisions are approved:

1. The production pipeline retains Notebooks 01–36 and adds only Notebook 12A
   to the numbered production dependency chain for full HINT restoration.
   Decision Notebook D01 remains a separately owned, completed method-selection
   study. The approved supplemental Decision/Analysis Notebook D02 is likewise
   outside the production numbering and executes after Notebook 21 under its
   roadmap contract; it does not renumber or reopen Notebooks 01–36.
2. Authoritative generated content belongs to notebook-owned output folders; retired `data/processed/` and legacy global output paths must not be reintroduced.
3. `outputs/inventory/` is the sole global output exception.
4. Restoration notebooks remain model-specific.
5. Metric notebooks are model-agnostic and organized by evidence family.
6. Handoffs use normalized manifests joined by stable identifiers rather than progressively wider tables.
7. One canonical region helper defines every evaluation region used throughout the project.
8. Notebook 35 remains a separate dashboard and deployment validation stage.
9. The 50-painting sources and outputs are immutable at `pilot-50-complete`.
   Working-tree notebooks may be reopened one at a time only for the approved
   controlled-300 minimal-delta rerun and only after an explicit contract.
10. The dashboard setup uses Python 3.12 with `requirements.txt`. All 36 saved run manifests record Python 3.12.6. Full experimental reproduction requires a separate environment and producer-specific version records; the legacy Python 3.11 recipe documented in `requirements_experiments.txt` is not the current dashboard setup or a description of the executed runs. See Section 26.

## 3. Scope and interpretation boundaries

The framework evaluates candidate restoration outputs under controlled synthetic damage and algorithmically defined synthetic degradation.

It does not:

- certify conservation-ready restoration;
- establish historical reconstruction correctness;
- infer artist intent;
- authenticate brushstrokes or authorship;
- treat visual realism as evidence of fidelity;
- treat any individual metric as ground truth;
- interpret seed variation as calibrated confidence;
- convert multiple signals into a universal conservation score.

The framework must keep these evidence families distinct but comparable:

- reference fidelity;
- perceptual similarity;
- feature-space and semantic consistency;
- texture and brushstroke-proxy consistency;
- colour consistency;
- seam and boundary consistency;
- outside-mask alteration;
- generative uncertainty;
- failure modes;
- compute and scalability;
- human-review requirements.

## 4. Truth-source hierarchy

When project sources disagree, use this precedence:

1. The user's latest explicit instruction.
2. The approved master additions and implementation checklist.
3. This implementation guideline.
4. The governing evidence audit and machine-readable evidence-coverage registry.
5. The approved detailed notebook roadmap.
6. The approved notebook-specific batch and input/output contract.
7. Versioned configuration and schema definitions.
8. Validated upstream manifests.
9. The current project inventory.
10. Existing notebooks, helpers, reports, and generated outputs.

Existing code and outputs provide evidence about prior behavior. They do not override the approved design.

This is a design-decision hierarchy, not permission to override measured facts.
Claims about completed work must match validated artifacts and execution-time
manifests. If an older design statement conflicts with the evidence, correct the
documentation or seek approval for new work; never rewrite the evidence to make
the original promise appear fulfilled.

## 5. Notebook lineage and status

`Origin` records lineage only. It does not indicate completion.

Allowed origin descriptions:

- **Existing Notebook (number):** a recently refactored notebook that may still require minor or major changes.
- **Existing Previous Version of Notebook (number), Pre-refactor:** an original working notebook that requires substantial refactoring.
- **Consolidates Existing Previous Versions of Notebooks (numbers), Pre-refactor:** a new consolidated stage replacing multiple older notebooks.
- **New Notebook:** a stage introduced by the final architecture.

Each roadmap entry and notebook manifest must separately record:

- `refactor_status`;
- `validation_status`;
- `origin`;
- `depends_on`;
- `applicable_dataset_scopes`;
- `applicable_experiment_scopes`;
- `expensive_execution`;
- `completion_gate_passed`.

No notebook may be labelled complete until its final completion gate passes under the current approved contract.

## 6. Standard refactoring workflow

This workflow applies when a new notebook or a specific reopening is explicitly
approved. No notebook remains awaiting implementation in the completed cycle.

The workflow for each approved notebook is:

1. Refresh the project inventory.
2. Inspect `docs/evidence_dependency_audit.md` and `config/evaluation/evidence_coverage.yaml`.
3. Inspect the latest inventory, approved requirements, upstream manifests, current notebook, relevant helpers, and current configuration.
4. Resolve every roadmap responsibility to exact evidence and remove unsupported promises.
5. Determine whether helpers require no change, targeted changes, or complete replacement.
6. Define every planned cell batch before generating notebook code.
7. Define and approve the exact input/output contract before Batch 1 is generated.
   The same preparation contract must include an expected execution-time range,
   the evidence used to estimate it, the dominant expensive stage, and the
   checkpoint/resume boundary for any notebook expected to exceed one hour.
8. The user creates the correctly numbered, named, and otherwise blank notebook.
9. Provide Batch 1 and every later batch as complete, separately labelled
   Markdown and code cells in chat for manual insertion, execution, and testing
   by the user.
10. Inspect the executed final notebook and generated artifacts.
11. Validate the notebook against the approved truth sources and input/output contract.
12. Provide targeted replacement cells or helper changes when issues are isolated.
    Before proposing any notebook correction, inspect the complete current
    notebook, including every Markdown and code cell, so the correction list is
    exhaustive and already-valid cells remain untouched. If a cell requires
    more than three edits, provide that entire corrected cell in chat. Never
    ask the user to find and replace repeated cardinalities, identifiers, or
    phrases scattered through a long cell. For one to three genuinely local
    edits, identify the exact cell and a unique surrounding code block; if the
    location is not unambiguous, provide the complete cell instead.
13. The user reruns the required cells; the assistant then inspects the saved results and repeats validation.
14. After the completion gate passes, the user updates the notebook's opening
    metadata to `Refactor status: Finished`, `Validation status: Finished`, and
    `Completion gate passed: Yes`; the assistant verifies that these fields agree
    with the run manifest and validation evidence.
15. Update both governing evidence-audit sources after every completed notebook:
    `docs/evidence_dependency_audit.md` for the human-readable evidence ledger and
    `config/evaluation/evidence_coverage.yaml` for the machine-readable coverage
    state. Record the validated population, canonical evidence, interpretation
    boundaries, completion status, and any downstream contract change. Also
    verify the completed notebook's entries in the project paths registry. These
    updates occur only after the notebook passes its completion gate.
16. Refresh the project inventory again so the next notebook receives the validated state.
17. Perform a repository-wide documentation freshness sweep before handoff. Search
    the completed notebook ID and stem across the roadmap, evidence audit,
    `evidence_coverage.yaml`, project-path registries, methodology/model notes and
    any downstream status summary. Remove stale `planned`, `preparation_complete`,
    `pending`, pilot-only population and obsolete `next notebook` claims wherever
    they refer to the newly completed producer. Confirm that the top-level
    `completed through` and `next eligible` summaries agree with the detailed
    notebook record and canonical run manifest; checking only the notebook's own
    section is insufficient.

### 6.1 Execution-time planning and closure

- Before Batch 1, state an upper operational runtime range for the complete
  notebook on the current hardware. Base it on validated upstream cardinality,
  observed pilot or 50-painting timings, per-case measurements where available,
  expected image/map writes, and known model-loading overhead.
- Separate active notebook computation from user review, debugging, inventory,
  remote uploads, and pauses between manually executed batches.
- Identify the likely longest cell before it is supplied. Any run expected to
  exceed one hour must provide visible progress, bounded checkpointing, safe
  resume, and an explicit stall or total-runtime guard where technically
  applicable.
- Prefer a defensible range over a falsely precise duration. Revise the estimate
  during preparation whenever preceding controlled-300 notebooks provide better
  throughput evidence.
- At the completion sweep, record observed active runtime where the notebook
  measures it, explain material divergence from the estimate, and use that
  observation to refine the remaining roadmap ranges.

### 6.2 Manual notebook editing policy

- The assistant must not create, replace, patch, or otherwise edit an `.ipynb`
  file directly.
- The assistant must not insert Batch 1 or any later cells into a notebook file.
- Every proposed notebook cell, including a replacement for an erroneous cell,
  is delivered in chat as a complete cell for the user to copy and paste.
- Replacement planning must be based on the saved notebook as a whole, not on
  an isolated error excerpt or a blind search for legacy numbers. Audit both
  Markdown and code, distinguish configuration keys from stale scientific
  claims, and list only cells that actually require modification.
- When one cell needs more than three changes, or repeated literals make manual
  navigation error-prone, return one complete corrected replacement cell. Do
  not distribute a multi-change repair as a checklist of search-and-replace
  operations. One to three small edits may be given as exact uniquely anchored
  snippets only when the user can locate them without searching through
  repeated occurrences.
- Markdown cells and code cells are labelled separately and preserve the linear
  structure already established by the successfully refactored notebooks.
- The user alone executes notebook cells and saves the notebook.
- The assistant may read and inspect the user-saved notebook, its rendered
  outputs, and its generated files, but inspection does not authorize notebook
  modification or cell execution.
- Helper modules, configuration files, tests, documentation, inventory files,
  and project-path registries may still be edited when explicitly within the
  approved preparation or completion workflow.

#### 6.2.1 Mandatory opening Markdown contract cell

Every refactored notebook must begin with one standalone Markdown cell that
identifies the notebook and summarizes its scientific and artifact contract.
This cell must appear before the first batch heading. It must not be merged with
`## Batch 1`, code, generated output, or execution instructions.

Before Batch 1 is generated, the assistant must provide this complete opening
Markdown cell in chat for the user to paste as the notebook's first cell. The
assistant must verify its presence and structure during the final notebook
sweep. Inspecting only the status fields is insufficient.

The cell begins with the following metadata block, in this order:

```markdown
# NN — Notebook Title

**Origin:** Approved lineage description  
**Refactor status:** In progress  
**Validation status:** Pending  
**Completion gate passed:** No  
**Output root:** `outputs/NN_notebook_name/`  
**Depends on:** Declared upstream notebooks or `None`
```

At completion, the same opening cell is updated to `Refactor status: Finished`,
`Validation status: Finished`, and `Completion gate passed: Yes` only after the
corresponding final checks have passed. These human-readable fields must agree
with the canonical run manifest and validation evidence.

After the metadata block, the opening cell must contain a tailored, concise
scientific overview. Use the successfully refactored notebooks, especially the
later metric and analysis notebooks, as structural references. The overview
must include:

- `## Purpose`;
- the approved evidence population, candidate scope, or dataset scope when
  applicable, including important inclusion and exclusion rules;
- the principal methods, evidence components, or responsibilities when they
  materially help define the notebook;
- the notebook-specific interpretation limits and scientific boundaries;
- `## Canonical outputs`, listing the declared persisted outputs; and
- an explicit statement declaring the standalone report path or stating that
  the notebook does not generate a standalone report.

Section names between `Purpose` and `Canonical outputs` are notebook-specific.
For example, a restoration notebook may explain its inference scope and prompt
policy, while an uncertainty, colour, seam, semantic, or human-evaluation
notebook needs different evidence and interpretation sections. Do not force one
scientific subsection template onto every notebook.

The opening cell must be understandable without reading Batch 1. Batch 1 then
starts in a separate Markdown cell and owns executable contract, dependency,
path, configuration, schema, and preflight details.

### 6.3 Notebooks that generate important reports

For any notebook that generates an important end-to-end or standalone report,
the assistant must design and present the proposed report structure during batch
planning, before generating any notebook cells that implement the report.

This requirement applies to all HTML reports planned in the notebook roadmap and
to any additional report intended to communicate a substantial experiment,
analysis, comparison, or thesis-level result as a standalone document.

#### Report purpose and scientific narrative

- The report structure must be tailored to the scientific purpose of the
  producing notebook. These guidelines do not impose fixed report sections:
  restoration-model performance, comparative analysis, uncertainty, colour,
  seam, robustness, semantic evidence, human evaluation, failure analysis, and
  final synthesis require different scientific narratives.
- Before designing the structure, explicitly identify the intended audience,
  purpose, principal scientific questions, and evidence available to the report.
  Organize the report around answering those questions rather than reproducing
  notebook-cell order or listing every generated metric.
- The report must function as a standalone high-level account. A reader should
  understand the principal findings, supporting evidence, important limitations,
  and overall interpretation without opening the notebook or manually inspecting
  canonical CSV files.
- Reports should lead with important findings and interpretations rather than
  implementation detail. Include methodology only where it is necessary to
  interpret the evidence. Detailed configuration, dependency, environment,
  checksum, and provenance information normally belongs in canonical manifests
  or a compact technical/provenance section.
- The report should end with a concise synthesis of what the evidence supports,
  what remains uncertain, and how the analysis contributes to the wider thesis
  or evaluation pipeline. Its wording and structure must suit the notebook rather
  than follow a fixed conclusion template.

#### Thesis-question alignment and conclusion density

- Before planning any important report, inspect the current thesis proposal under
  `docs/proposal/` and the current notebook roadmap. Treat the proposal's central
  research questions as thematic anchors and the approved roadmap and
  implementation contracts as the authoritative expanded scope. The proposal is
  intentionally earlier and may not describe later additions such as region-aware
  colour and seam evidence, robustness and sensitivity analysis, failure flags,
  XAI, human evaluation, model cards, deployment, or reproducibility packaging.
- Reports must explicitly show which thesis research question, practical output,
  or approved scope extension each major analysis helps answer. This may use a
  concise research-question orientation near the beginning, section-level
  question labels, conclusion callouts, and a final contribution-to-thesis
  synthesis. Do not force unrelated evidence into a research question merely to
  complete a template.
- The recurring thesis themes are trustworthy and museum-oriented evaluation;
  the additional evidence provided by region-aware metrics beyond traditional
  image similarity; conditional method behaviour across controlled damage
  conditions and its consistency across evaluated paintings; repeated-candidate
  disagreement as evidence of stochastic stability and its relationship with
  other restoration-quality diagnostics; transparent metric disagreement; and
  support for human conservation judgement rather than replacement of that
  judgement. Broad visual categories remain descriptive subgroup information,
  not independently estimated art-historical effects. Report emphasis must be
  adapted to the producing notebook while remaining visibly connected to these
  themes.
- Reports should draw as many defensible conclusions as the validated evidence
  supports. Do not stop at listing metric values or repeatedly defer all
  interpretation to a later notebook. A conclusion should normally state the
  observed result, its metric-defined interpretation, the population and scope
  to which it applies, an important nearby limitation, and its relevance to the
  notebook's thesis question or approved extension.
- Conclusions must remain proportionate to the evidence. Computational metrics
  may support conclusions about measured fidelity, perceptual similarity,
  feature consistency, texture, colour, seams, spatial change, uncertainty, or
  other declared constructs. They must not be escalated into claims of historical
  authenticity, physical conservation suitability, or museum approval unless
  suitable evidence later exists for those claims.
- Use clear, direct, and concise language even when the underlying analysis is
  technically detailed. Prefer wording such as "LaMa had the lowest deterioration
  slope on 6 of 11 measures" over denser phrases such as "LaMa had the shallowest
  adverse slope on 6 of 11 anchors." Retain exact statistical terminology in
  methods, tables, captions, and provenance where it is needed for precision, but
  explain the main finding in plain language first.

#### Evidence selection and interpretation

- Reports must remain clear without becoming artificially terse. Use a healthy
  mixture of quantitative results, conclusions, plain-language interpretation,
  short paragraphs, finding bullets, tables, plots, source and restoration
  images, diagnostic visualizations, captions, and concise methodological
  context. Paragraphs should carry connected reasoning and synthesis; bullets
  should improve scanning of findings, conditions, strengths, weaknesses, and
  limitations rather than replace narrative entirely.
- Use as many scientifically useful images, restoration panels, crops, plots,
  heatmaps, overlays, and comparison views as the evidence and report purpose can
  support without repetitive padding. Prefer visual evidence over another block
  of prose when it makes a spatial, perceptual, comparative, or failure-pattern
  conclusion easier to inspect. Do not enforce a low arbitrary visual cap, but
  every included visual must have a declared question, auditable selection rule,
  readable caption, and interpretive role.
- Avoid both extremes: do not create a text-heavy report with only token figures,
  and do not create an unexplained image gallery or exhaustive metric dump. Group
  related restorations into readable panels, alternate analytical and visual
  sections, and explain what each visual adds beyond its accompanying metrics.
- Select main-narrative quantitative results because they answer a scientific
  question or represent a distinct evidence family, not merely because a metric
  exists. Where several metrics capture substantially similar behaviour, use a
  small representative set in the report and retain detailed results in canonical
  machine-readable outputs.
- Every major quantitative result must have enough interpretation for a reader to
  understand its experimental meaning. Clearly distinguish descriptive
  observations, statistical evidence, and conclusions supported by that evidence.
- Quantitative claims in prose, KPI cards, captions, tables, and figures must be
  programmatically derived from validated canonical evidence from the current
  run. Important claims must be traceable to their source artifact, fields,
  filters, statistical unit, and denominator. Experimental values must not be
  manually copied into report templates.
- When a conclusion concerns visual or spatial behaviour, show appropriate visual
  evidence alongside numerical evidence where practical. Examples include
  clean/damaged/restored comparisons, masks, crops, heatmaps, boundary views,
  uncertainty maps, semantic maps, and other notebook-appropriate diagnostics.
- Present strengths and weaknesses where supported by the evidence. Relevant
  failure cases, difficult cases, counterexamples, and limitations must not be
  hidden merely to produce a cleaner narrative.
- Select representative examples using explicit, reproducible, and auditable
  rules. Do not cherry-pick visually attractive successes or unusually poor
  failures. Suitable strategies include representative or median cases,
  predeclared examples, extremes under a stated metric, metric-disagreement cases,
  distinct experiment groups, or other deterministic notebook-appropriate rules.
- Preserve and explain scientifically relevant disagreement between metrics or
  evidence families instead of forcing agreement through a single ranking or
  score. The completed pipeline retains no universal combined quality,
  uncertainty, or trust score. Existing anchor-win and rank summaries describe
  performance across separate measures; they are not combined quality scores.
  Introducing a new combined measure would require a separately approved
  methodological extension, not a report or dashboard maintenance change.
- Respect the statistical unit and dependency structure of the experiment.
  Candidate observations, repeated seeds, prompt variants, multiple cases from
  one painting, partial model coverage, and other repeated or nested observations
  must not be presented as independent evidence when they are not.
- State partial or unavailable experimental coverage explicitly. Do not imply
  full-dataset comparability when a model, metric, experiment, or analysis covers
  only a subset.
- State important limitations close enough to affected conclusions for correct
  interpretation. A short consolidated limitations section may also be included.

#### Evidence-to-assertion rule

Reports must not stop at factual observations, metric values, or descriptions of
plot direction. Every important result in the main narrative must be followed by
one or two short, plain-language assertions explaining what the result means for
the evaluated restoration behaviour and, where the comparison supports it, which
model was better, worse, more stable, less stable, stronger, or weaker within the
stated scope.

For example, a statement such as "thin scratches produced the smallest variation
for Telea and LaMa" must be followed by an interpretation such as: "Both methods
were therefore dependable for this controlled thin-scratch population. If LaMa's
dispersion was lower on the relevant local metrics, LaMa was the more robust of
the two for thin scratches; if their uncertainty interval or effect evidence did
not resolve the difference, the comparison remains inconclusive."

Apply this rule as follows:

- state the factual result first, then the practical assertion;
- name the relevant model, metric or evidence family, region, experiment, and
  population when needed to prevent the assertion from sounding universal;
- use direct comparative language such as `better`, `worse`, `more robust`, or
  `less stable` when the validated direction and evidence support it;
- explicitly say `inconclusive` or `no clear difference` when sampling limits,
  intervals, corrected tests, ties, or metric disagreement do not support a
  binary conclusion;
- explain the likely restoration consequence in simple terms, such as stronger
  boundary continuity, worse colour matching, more variable structure, or more
  dependable reconstruction under the tested condition;
- avoid merely restating the number in different words and avoid adding generic
  conclusions that are not specific to the displayed evidence;
- preserve nearby uncertainty and scope limits, and never turn a metric-specific
  better/worse assertion into historical-authenticity, conservation-approval,
  or universal model-superiority language.

The approved mock should reserve these assertion or conclusion positions, and
the final report must populate them from validated canonical evidence rather
than weakening them into descriptive commentary or replacing them with a new
narrative structure.

#### Canonical evidence and permitted report processing

- Conclusions must derive only from validated canonical evidence produced by the
  current or upstream notebooks. Displayed examples may illustrate a conclusion
  but must not independently determine it. The report layer must not become a
  second informal analysis pipeline.
- Report generation may perform presentation-only transformations such as
  selecting an approved population, sorting, formatting, calculating explicitly
  defined display percentages from canonical counts, preparing plotting layouts,
  generating thumbnails, and assembling image panels.
- Report generation must not introduce new metrics, undocumented exclusions,
  post-hoc statistical tests, alternative aggregation rules, rankings, composite
  scores, or scientific conclusions that were not validated by the producing or
  an upstream analysis notebook.

#### Report assets, readability, and portability

- Report planning must define how figures and images are supplied. Unless the
  user explicitly approves a multi-file report package, a canonical standalone
  HTML report must be self-contained: downloading and opening that HTML file by
  itself must preserve every narrative figure and representative image required
  to understand the report.
- Self-contained HTML reports may embed declared, report-relevant figures and
  resized representative images as data URIs. Do not embed unrestricted
  full-resolution image collections. Prepare web-sized display copies in memory,
  retain aspect ratio, use an appropriate browser-supported format and quality,
  and keep the resulting report size proportionate to its scientific purpose.
- Canonical figures remain separately persisted and registered even when a
  display copy is also embedded in the HTML. The report should record source
  artifact paths and checksums for traceability, while optional links to
  full-resolution originals may supplement—but must not replace—the visible
  embedded evidence.
- A small canonical figure list does not cap the number of visuals inside the
  report. Additional presentation-only plots, crops, restoration grids,
  thumbnails, and diagnostic composites may be generated in memory from
  validated canonical evidence and embedded directly in the standalone HTML
  without becoming separate output files. Declare and count these embedded
  views in report metadata so their evidence sources and construction rules
  remain auditable.
- Report-specific composites, thumbnails, or presentation figures may be stored
  under the producing notebook's output root when they are declared canonical
  report assets. Upstream artifacts used to construct embedded display images
  must be recorded as report dependencies. Do not silently duplicate large
  upstream image collections as additional persistent files.
- Figures and tables must use readable labels, units, metric directionality,
  legends, captions, and colour scales. Important visual evidence needs concise
  alternative text or an equivalent descriptive caption.
- Use colour palettes that remain interpretable under common colour-vision
  deficiencies. Heatmaps must state their scale, normalization, spatial meaning,
  and whether values are comparable across panels.
- Detailed provenance must remain available without dominating the report. A
  compact technical appendix or provenance summary may include the run ID, Git
  commit, model/configuration versions, evaluated population, validation status,
  and canonical artifact references.

#### Report structure approval before implementation

- During batch planning, the assistant must present a notebook-specific report
  skeleton for user review before generating report-implementation cells.
- After the skeleton, the assistant must also render a realistic chat-only mock
  report at approximately the intended final verbosity and visual density. Do
  not create or save a mock-report file in the repository.
- The chat mock report must show how the report will actually read, not merely
  repeat its headings. It must include representative prose, explanations after
  quantitative results, captions, limitations near affected claims, and the
  proposed placement and approximate number of tables, figures, plots, and
  restoration or diagnostic images.
- The mock report must demonstrate the intended mixture of paragraphs, bullet
  points, tables, metric summaries, conclusion callouts, plots, restorations, and
  diagnostic images. It must contain enough plausible section-level conclusions
  for the user to judge interpretive depth rather than showing only one executive
  summary and mostly placeholders.
- The mock report must identify the proposal research question or approved scope
  extension addressed by each major results section and must demonstrate how the
  final synthesis will connect notebook-specific findings back to the central
  thesis narrative.
- Before real results exist, use clearly labelled fictional metric values and
  numbered visual placeholders such as `Image 1`, `Figure 2`, or `Plot 3`.
  Placeholders should state what would be visible—for example clean, damaged,
  restored, mask, crop, heatmap, or multi-model panel—so the user can judge the
  proposed image density and narrative flow. These fictional values and
  placeholders are planning aids only and must never be copied into the
  implemented report.
- Report approval therefore covers both scientific organization and presentation
  density: the user may request more or less explanation, images, plots, tables,
  captions, or technical detail before implementation begins.
- The skeleton must show the intended narrative flow rather than only generic
  headings. For every proposed section it should state:
  - the scientific question or communication purpose;
  - the principal canonical evidence to be presented;
  - the planned tables, plots, figures, images, diagnostic panels, or other visual
    elements;
  - the approximate level of numerical detail;
  - the interpretation logic and important limitations.
- When results are not yet known, the skeleton must not assume the direction of
  the eventual conclusion. It should state the question that the evidence will
  resolve rather than pre-write the finding.
- Include realistic illustrative examples showing how important sections could
  appear. Creative made-up values, mock tables, placeholder figures, and
  hypothetical interpretations may demonstrate presentation and narrative style,
  but must be explicitly labelled illustrative. They must never enter the
  implemented report or be treated as experimental evidence.
- The mock-up should demonstrate intended information density and visual
  hierarchy, including separation of headline findings, supporting evidence,
  visual examples, detailed analysis, limitations, and technical provenance.
- Identify sections that appear redundant, excessively detailed, unsupported by
  available evidence, or better represented by a canonical table or figure.
- The user may add, remove, reorder, merge, or redefine sections during approval.
- Structure approval is design approval only. It does not authorize notebook
  modification or execution and does not override the manual notebook editing
  policy in Section 6.2.
- Only after approval may the assistant generate report-implementation cells.
- If implementation later reveals that an approved section lacks validated
  evidence, or that a materially different structure is scientifically preferable,
  surface the issue and obtain approval rather than silently changing the report.

#### Approved mock-to-final fidelity contract

Once the user approves a notebook-specific mock report, that mock becomes the
binding structural and editorial baseline for the implemented report. It is not
merely an example, mood board, checklist of topics, or permission to design a
different report from scratch. The final report must be an evidence-populated,
scientifically corrected, and where useful expanded version of the approved mock.

The implemented report must preserve the approved mock's recognizable identity,
including all applicable elements below:

- title and subtitle framing;
- executive-summary order, headline indicators, and main-conclusion placement;
- section sequence, section numbering, scientific questions, and narrative flow;
- the role and approximate location of each approved table, canonical figure,
  report-only plot, restoration panel, diagnostic panel, and visual atlas;
- declared visual-selection rules and the kinds of cases represented;
- section-level conclusion placement and nearby limitation placement;
- the balance between paragraphs, bullets, tables, metrics, visuals, conclusions,
  supported claims, unsupported claims, and final thesis synthesis; and
- approximately the approved explanation depth, visual density, and tile count.

Implementation replaces fictional values, illustrative model winners, invented
confidence intervals, placeholder captions, and hypothetical conclusions with
values and conclusions derived from validated canonical evidence. That required
replacement does not authorize deleting, merging, renaming, reordering, or
substantially rewriting approved sections and visual roles.

Upgrades are normally additive. The assistant may improve accessibility,
responsive layout, provenance, traceability, captions, concise wording, or add
validated supporting evidence while retaining the approved structure. An upgrade
must not displace an approved section, reduce the agreed analytical or visual
density, or turn the report into a different narrative design.

Before generating the report-implementation cells, the assistant must create an
in-memory mock-to-final traceability table with at least:

```text
mock_element_id
mock_section
approved_role
final_section
canonical_evidence_source
implementation_status
deviation_reason
```

`implementation_status` must be one of:

```text
preserved
upgraded_additively
approved_deviation
```

Every approved section, table role, figure or plot role, image-panel role,
conclusion block, limitation block, and final synthesis element must appear in
this traceability table. The notebook's final validation must confirm that:

- all approved mock elements are represented;
- the final section order matches the approved order;
- every required visual and table role is present;
- actual embedded-image and tile counts meet the approved density;
- all report values and directional claims come from validated evidence; and
- every deviation carries prior user approval and a recorded reason.

If validated evidence contradicts a fictional mock result, keep the approved
section and replace its fictional result with the real result. If evidence cannot
support an approved element, or implementation requires a material structural
change, stop before generating or replacing report cells and obtain explicit user
approval. Never silently substitute a new report structure because it is easier
to implement or appears cleaner after results are known.

#### Rendered-report validation

Before notebook completion, validate at minimum:

- expected report paths and report counts;
- non-empty HTML content and expected high-level components;
- successful rendering of every intended embedded figure and representative
  image when the HTML is opened without its original output directory;
- absence of unintended, undeclared, malformed, or excessively large embedded
  payloads, together with validation of expected payload counts and MIME types;
- no required narrative image or figure that depends only on a local filesystem
  path or repository-relative link;
- valid internal links where applicable;
- recorded input dependencies and source run identifiers;
- artifact-manifest registration for the report and its owned assets;
- consistency between displayed counts, denominators, coverage statements, and
  canonical evidence;
- traceable alignment between major report conclusions and the relevant proposal
  research question, practical output, or documented roadmap extension;
- validated mock-to-final traceability showing that the approved section order,
  tables, visual roles, selection rules, conclusion placement, limitations,
  narrative density, and thesis synthesis were preserved or changed only through
  an explicitly approved deviation;
- a balanced rendered mixture of narrative, finding bullets, tables, plots,
  restorations or diagnostic images, captions, and scoped conclusions, without
  long avoidable text walls or unexplained visual galleries;
- clear separation between scientific validation failures and HTML/rendering
  failures.

The illustrative LaMa model-performance mock-up in
[`report_structure_mock_lama.md`](report_structure_mock_lama.md) is a design
reference for narrative quality and information density. It is not a mandatory
section template for model reports or for other report categories.

### 6.4 Dashboard design, mock fidelity, and implementation boundary

Notebook 34 and `streamlit_app.py` follow the same approval discipline used for
important reports, adapted for an interactive application. Before dashboard
asset or application implementation, the assistant must render chat-only visual
mockups that demonstrate navigation, hierarchy, density, plots, paintings,
restorations, diagnostic maps, conclusions, limitations, filters, and
provenance. These planning images remain outside the repository unless the user
explicitly requests that they be retained as project artifacts.

The user made that explicit retention decision on 2026-09-23 and approved the
current primary direction on 2026-09-24. The two governing boards are stored in
[`docs/dashboard_design_finalists/approved_current/`](dashboard_design_finalists/README.md).
They cover all eight approved rooms and bind the future Controlled-300 UI's
navigation, spatial museum identity, progressive evidence flow, and interaction
grammar. Earlier selected boards remain under `alternatives/` for potential
component reuse, not as competing layouts. All boards' illustrative labels,
counts, metrics, painting IDs, and conclusions are not scientific evidence and
must never be copied into the application without validation.

Once the user approves the dashboard architecture and visual direction, the
approved mockups become a binding interaction and presentation baseline. The
implemented application may correct fictional values, replace illustrative
painting IDs, improve responsive behaviour, and make evidence-driven additions,
but it must not silently replace the approved navigation, hierarchy, visual
density, or conservator-facing question flow. Material redesign requires renewed
approval.

The primary composition is now selected. At the pre-N34 review, verify its
feasibility and map final Controlled-300 content into each room before changing
the application. Any borrowed alternative component must be explicitly named
and must preserve one coherent navigation, typography, spacing, and interaction
system. The traceability table must cite one of the two approved boards for
each page or major interaction and separately identify any approved exception.

The approved application contains no more than ten principal pages. The current
approved structure contains eight:

1. Overview;
2. Study Design;
3. Metric Framework;
4. Model Performance;
5. Robustness & Uncertainty;
6. Trustworthiness & XAI;
7. Case Explorer;
8. Reports & Reproducibility.

Dashboard presentation rules:

- Lead each page with one plain-language question or supported conclusion.
- Use two to four headline indicators, one or two primary analytical views,
  representative visual evidence, short interpretive bullets, and one nearby
  limitation where applicable.
- Prefer concise assertions that explain what a result means for restoration or
  model behaviour; do not stop at descriptive metric statements.
- Keep raw tables, full provenance, and technical diagnostics accessible through
  expanders or drill-down views rather than making them the initial visual focus.
- Use representative cases for initial presentation while preserving direct
  filtered access to the complete applicable indexed population.
- Keep visual comparisons synchronized and explicitly label original, damaged,
  mask, restoration, difference, uncertainty, seam, semantic, and retrieval
  views.
- Treat retrieval as supporting context, uncertainty as empirical variation, and
  flags as diagnostic rules rather than proof, calibrated confidence, or
  conservation ground truth.

Approved visual language:

- an authored museum-research and exhibition-catalogue character rather than a
  glossy corporate or generic AI-generated dashboard;
- aged-ivory surfaces with subtle paper or canvas texture;
- a restrained palette derived from painting pigments: deep bottle green, raw
  umber, faded vermilion, ochre, parchment, and charcoal;
- editorial serif headings paired with readable sans-serif controls and tables;
- thin graphite-like dividers, modest spacing variation, archival labels, and
  sparse purposeful pencil-style circles, arrows, or underlines;
- limited corner rounding, shadows, icon medallions, gradients, and decorative
  symmetry;
- no scrapbook clutter, torn-paper overload, ornamental props, illegible
  handwriting, or decoration that competes with scientific evidence;
- accessibility, chart clarity, responsive layout, and thesis-presentation
  readability override stylistic imperfection.

The approved boards add the following positive requirements to that visual
language: painting-first evidence; an introductory Exhibition Foyer; room-led
navigation; distinctive page divisions rather than repeated generic cards;
direct pairing of conclusions with sources and limitations; tactile exhibit
scrubbers and comparison controls; case-level magnification and synchronized
comparison; an explicit visual derivation from evidence to review flag;
reproducibility as the Research Archive; and an optional guided presentation
path that does not remove free exploration. Use one dominant interaction per
room rather than placing every pattern on every page.

Scientific and technical boundaries:

- Notebook 34 packages validated upstream evidence into normalized dashboard
  tables, indexes, summaries, and manifests. It does not recompute scientific
  metrics or rerun restoration inference.
- Notebook 34 is the dashboard's primary package and candidate allow-list.
  The approved post-notebook numerical view also reads exact, checksum-verified
  metric tables from Notebooks 13, 14, 15, 17, and 20, plus candidate identity
  tables from Notebooks 11, 12, and 22, through
  `src/restoration_eval/dashboard_metrics.py`. Its fixed input and display
  contract is `docs/dashboard_numeric_metrics.md`. No arbitrary output scan or
  retired global path such as `outputs/dashboard/` may select inputs.
- The application may aggregate, filter, reshape, or format already validated
  dashboard assets for presentation, but it must not import experiment,
  restoration, or metric-computation workflows.
- Upstream images and self-contained reports may be resolved through validated
  repository-relative paths recorded by Notebook 34. For the lightweight
  Controlled-300 deployment, a validated local-first, direct-remote-second
  resolver must preserve each indexed image's identity when its local bulk
  output is absent. Default selections do not restrict complete evidence
  access. Bulk archives are not the interactive image backend.
- Standalone HTML reports offered by the application remain individually
  downloadable and self-contained according to Section 6.3.
- The dashboard is an inspection and decision-support interface, not an
  experiment runner, restoration tool, authenticity assessment, historical-truth
  claim, or conservation approval system.

Before Notebook 35 validation, create an in-memory dashboard-mock-to-app
traceability table covering every approved page, major content block, chart role,
image-panel role, conclusion position, limitation, filter family, drill-down,
and provenance view. Notebook 35 must validate this traceability together with
schema, path, relationship, optional-model, static-import, and application-smoke
checks.

For the Controlled-300 rerun, **stop after Notebook 33 and before editing
Notebook 34 or `streamlit_app.py`**. The user must approve a renewed,
evidence-specific dashboard contract first. Audit the proposed content of all
eight pages, numerical case tables, complete visual-index population, public
producer repositories, direct-image URLs, local-to-remote registry mapping,
lazy fetching and caching, startup memory, network latency, free-service
feasibility, fallback behavior, and cross-model/case rendering tests. Use the
actual completed producer manifests and image counts rather than pilot
assumptions. Do not reduce accessible evidence to a representative gallery
without explicit approval. Notebook 34 builds the agreed assets; Notebook 35
tests both local and deployed-style access. Keep the live pilot-50 application
unchanged until the new deployment passes its own validation.

The inventory refresh is a controlled write operation. During explicitly read-only phases, the existing inventory may be inspected but must not be regenerated.

Before every inventory refresh, run it from the same project environment used by
the notebooks and confirm that `import yaml` succeeds. The inventory treats YAML
metadata inspection as optional at runtime: if PyYAML is unavailable, the scan can
finish while recording `PyYAML is not installed; YAML metadata is unavailable` as
a per-file read error. A printed `status: completed` is therefore not sufficient.

Required inventory sequence:

```powershell
python -c "import yaml; print(yaml.__version__)"
python .\tools\build_project_inventory.py --root . --out-dir .\outputs\inventory
```

After the refresh, inspect `outputs/inventory/inventory_run.json` and require both
`summary.read_error_file_count` and `summary.read_error_count` to equal zero. Also
confirm that the current notebook and governing YAML records have zero
`read_error_count` in `project_file_inventory.csv`. Do not use
`--no-reuse-existing` merely to correct a missing-PyYAML runtime: a full scan must
reopen more than 20,000 files and several gigabytes of generated evidence. First
restore PyYAML in the execution environment, then rerun incrementally; use a full
no-reuse scan only when the verified reuse cache itself is invalid or a complete
reinspection is explicitly required.

### 6.5 Tagged baseline and controlled-300 evidence-dependency gate

The complete 50-painting study is immutable at Git tag `pilot-50-complete`.
Notebooks 01–36 may now be adapted in dependency order for `controlled_300`, but
this permission is narrow: scale population, add the approved HINT dependency,
and update exact validations while preserving the validated scientific design.
D01 and its 12-case outputs remain frozen.

Rules for the active rerun:

- Maintain one active raw dataset, dataset configuration, notebook sequence, and
  set of output roots. Do not create `controlled_50`/`controlled_300` notebook,
  helper, YAML, or output variants side by side.
- Treat the tagged commit—not duplicate working-tree files—as the recovery point
  and comparison baseline for the 50-painting study.
- A read-only copy of the pre-scale notebook outputs is retained outside the
  repository at `E:/outputs/`. For Notebook `NN_name`, compare the completed
  controlled-300 output tree with `E:/outputs/NN_name/` after the notebook gate
  passes and before the final inventory refresh. The Git tag remains the
  authoritative recovery baseline; the external copy is the convenient
  artifact-level comparison source and must never be modified by the pipeline.
- Reopen only the next notebook whose direct producers have passed their
  controlled-300 gates. Never run a downstream notebook against a silent mixture
  of old and new upstream artifacts.
- Before editing a notebook, approve a minimal-change contract that enumerates
  every changed input path, cardinality, dependency, validation assertion,
  output expectation, and unavoidable new cell.
- Preserve notebook cell order and cell contents wherever behavior remains valid.
  Edit existing cells in place; add cells only when the approved responsibility
  cannot be expressed safely in the existing structure.
- Notebook cells are supplied in chat, pasted by the user, and executed by the
  user. The assistant must never edit or execute an `.ipynb` directly.
- Clear only the current notebook's output root immediately before its full
  controlled-300 rerun. Upstream roots are read-only inputs; downstream roots
  remain untouched until their turn.
- Preserve normalized schemas and artifact roles. Derive expected row counts
  from configuration and validated upstream registries, not global replacement
  of the number 50 and not filesystem scans.
- Compare the new notebook with its tagged counterpart for cell responsibility,
  schema, artifact roles, figures/reports, validation coverage, and exclusions.
  Changed row counts are expected; silently missing evidence families are not.
- Present an end-of-notebook baseline-comparison table that covers every
  pre-scale output and every new output. At minimum, record the relative path or
  artifact family, pre-scale existence and count, controlled-300 existence and
  count, status, and the reason for every changed count. Count rows for canonical
  tables, files for collections, records for manifests, and applicable rendered
  units for figures or reports. Mark unchanged structural counts explicitly and
  distinguish expected scale growth from schema drift, missing evidence, and
  deliberately retired artifacts.
- In the same final sweep, add a publication-destination table for **every
  canonical output family**: exact local path, file/row count and bytes where
  relevant, GitHub inclusion, Hugging Face `candidates` or `diagnostics`
  inclusion (or an explicit deferred decision), and the reason. Distinguish
  local scientific completion from Git staging and remote verification. Check
  `.gitignore` and currently tracked pilot paths before writing scoped user
  commands; include removals of superseded selected-figure paths, but never
  stage editor lock files or unrelated changes. Give the user ordered,
  producer-specific Hugging Face and Git commands after the inventory audit.
  The assistant does not run `git add`, `git commit`, or `git push` for the user.
- A committed output remains historical 50-painting evidence until its producer
  has a controlled-300 run manifest and passed completion gate. Do not rewrite a
  historical manifest to pretend that later files were part of its run.
- Notebook 12A is the only approved new production notebook. It owns full HINT
  outputs under `outputs/12a_hint_restoration/`. D01 remains the selection source
  and must not be rerun as production.
- After Notebook 21 completes its Controlled-300 gate and is committed, pause the
  numbered rerun and implement
  `d02_portrait_skin_tone_and_hand_restoration_audit.ipynb` before beginning
  Notebook 22. D02 must first apply its annotation-overlap feasibility gate to
  existing evidence. It may finish with a documented feasibility-only result,
  but it must not generate new targeted masks or restorations without a separate
  explicit approval. After D02 passes its applicable completion gate, resume the
  unchanged numbered sequence at Notebook 22.

#### Active Controlled-300 completion status

Updated 2026-09-25. This compact status is a navigation aid; the human evidence
audit and machine-readable coverage registry remain authoritative for counts,
checksums, limitations, and downstream eligibility.

| Notebook | Refactor | Validation | Gate | Validated active population | Pilot continuity |
|---|---|---|---|---|---|
| 01 Dataset Verification | Finished | Finished | Yes | 300 artworks; 448 audit rows | All pilot artifact paths and schemas retained |
| 02 Image Preprocessing | Finished | Finished | Yes | 300 clean images and preprocessing rows | First 50 PNGs and preview byte-identical |
| 03 Canonical Mask Generation | Finished | Finished | Yes | 1,500 masks across 300 paintings and five families | All 250 pilot masks byte-identical; schema unchanged |
| 04 Canonical Damaged Images | Finished | Finished | Yes | 1,500 cases and damaged PNGs across 300 paintings and five families | All 250 pilot damaged PNGs byte-identical; case and audit schemas unchanged |
| 05 Damage-Size Sensitivity Dataset | Finished | Finished | Yes | 35 paintings × 7 nested levels = 245 matched cases, masks, damaged images, and audit rows | All 70 shared pilot images byte-identical; schemas and artifact paths unchanged; figure updated for expanded representatives |
| 06 Mask Robustness Dataset | Finished | Finished | Yes | 35 paintings × 3 families × 5 variants = 525 cases; 105 groups; 525 masks, damaged images, and audit rows | All pilot paths and schemas retained; 148/151 shared PNGs byte-identical; one `p039` `loss_small` variant and the figure updated for helper v3.1.1 morphology enforcement |
| 07 Synthetic Degradation Dataset | Finished | Finished | Yes | Balanced 35-painting cohort; 1,050 single plus 105 combined cases = 1,155 cases, effect-support masks, degraded images, and audit rows | All 337 pilot paths retained; all 330 shared generated PNGs byte-identical; table schemas and 165 pilot case/audit IDs retained; output count increased from 337 to 2,317 through the expanded cohort |
| 08 Experiment Contracts and Region Policy | Finished | Finished | Yes | 3,425 registered cases; 17,125 decisions across 5 models including `hint_places2`; 2,620 eligible cases per model; 143 policy rows; 101/101 scientific checks; 20/20 completion requirements | All 9 pilot paths and schemas retained; 525 pilot cases retained with only intentional scope change; 2,100 shared eligibility rows unchanged; region policy byte-identical; schema definitions unchanged |
| 09 OpenCV Telea Restoration | Finished | Finished | Yes | 2,620 eligible cases and restored PNGs; 300 zero controls; 2,320 nonzero cases; 72/72 scientific checks; 15/15 roadmap requirements; 2,626 canonical files | All 416 pilot paths and CSV schemas retained; 409/410 shared restoration PNGs byte-identical; sole changed shared PNG inherits Notebook 06's documented `p039` morphology correction; representative figure byte-identical |
| 10 LaMa Restoration | Finished | Finished | Yes | 2,620 eligible cases and restored PNGs; 300 zero controls; 2,320 nonzero cases; 80/80 scientific checks; 16/16 roadmap requirements; 2,626 canonical files; 4,594.223-second full execution | All 416 pilot paths and CSV schemas retained; 409/410 shared restoration PNGs byte-identical; sole changed shared PNG inherits Notebook 06's documented `p039` morphology correction; representative figure byte-identical |
| 11 Stable Diffusion Restoration | Finished | Finished | Yes | 8,520 completed candidate rows and restored PNGs; 2,620 primary, 4,460 prompt-context, and 1,440 uncertainty-extension rows; 8,220 inferences; 300 identity controls; 176/176 scientific checks; 23/23 completion requirements; 8,530 canonical files | All 10 pilot non-image paths and CSV schemas retained; 1,298/1,330 candidate identities retained; 1,297/1,298 shared PNGs byte-identical; one inherited Notebook 06 morphology correction; 32 exploratory contextual rows displaced by the approved expanded hash-stratified selection |
| 12 SDXL Bounded Partial Evaluation | Finished | Finished | Yes | 35 scheduled rows across 30 paintings; 24 technically valid completed candidates, 1 timed-out row, and 10 explicit budget skips; 241/241 validation checks; 19/19 roadmap requirements; 30 canonical files; 0 work files | All 10 pilot candidates retained with identical IDs, paths, completed status, schema, and restored-image bytes; bounded scope expanded from 10 to 35 without converting runtime omissions into quality failures |
| 12A HINT Restoration | Finished | Finished | Yes | 2,620 candidates across all eligible cases; 2,320 HINT inferences and 300 identity controls; 82/82 validation checks; 2,626 canonical files; 0 work files | New production method selected by D01; no historical pilot output counterpart; decision, adapter, checkpoint, and exact-compositing contracts preserved |
| 13 Classical Metrics | Finished | Finished | Yes | 477,753 rows for 16,404 candidates across five methods and 2,620 cases; 262/262 validation checks; 6 canonical files; 28,705.153-second execution | All 6 pilot paths and CSV schemas retained; rows increased from 63,018 to 477,753 without unexplained missing evidence; bulk metric table externally published and verified |
| 14 LPIPS Metrics | Finished | Finished | Yes | 31,608 rows for 16,404 candidates across five methods and 2,620 cases; 2,400 matched scratch-prompt regional pairs; 261/261 validation checks; 5 canonical files; 3,341.795-second execution | All 5 pilot paths and CSV schemas retained; rows increased from 4,170 to 31,608; 64 pilot rows map exactly to the 32 approved N11 contextual-candidate displacements; no unexplained loss |
| 15 Feature Similarity | Finished | Finished with one non-blocking CUDA warning | Yes | 63,216 CLIP/DINOv2 metric rows and 78,336 embeddings for 16,404 candidates across five methods and 2,620 cases; 247 checks; 7 canonical files; 6,270.909-second extraction and 199.564-second metric construction | All 7 pilot paths and table schemas retained; metric rows increased from 8,340 to 63,216 and embeddings from 10,700 to 78,336; expected N11 candidate displacement and inherited N06 morphology differences fully accounted for; bulk NPZ classified for diagnostics-tier publication |
| 16 Difference Maps and Spatial Diagnostics | Finished | Finished | Yes | 143,247 spatial rows, 76,020 candidate map PNGs, 14 selected panels and 76,034 map-manifest rows for 16,404 candidates and 2,620 cases; 137/137 checks; 76,039 canonical files | All 7 pilot artifact classes and CSV schemas retained; complete maps and oversized metrics are local and in the verified diagnostics indexed-bundle release; compact Git committed |
| 17 Local Consistency Metrics | Finished | Finished | Yes | 2,060,667 texture, colour, and seam metric rows; 27,912 candidate-map PNGs, 14 selected panels and 27,926 map-manifest rows for 16,404 candidates and 2,620 cases; 179/179 checks; 27,932 canonical files | Pilot schemas/paths retained; complete maps and oversized metrics are local and in the verified diagnostics indexed-bundle release; compact Git committed |
| 18 Diffusion Uncertainty Analysis | Finished | Finished | Yes | 780 prompt-specific groups, 3,120 candidates, 4,680 pairs, 124,800 metric rows, 780 calibration rows, two figures and 150/150 passing checks | Same seven artifact classes as the E: pilot baseline; metric/calibration rows scaled sixfold from 20,800/130; no failed checks, work files or saved notebook errors; compact Git committed |
| 19 Uncertainty and Spatial Explanation Maps | Finished | Finished | Yes | 780 numeric maps, 4,680 spatial rows, 2,475 owned PNGs, 6,255 map-manifest rows, 149/149 passing checks, and 2,481 canonical files | Pilot schemas and eight artifact roles retained; all 130 shared raw maps and 780 shared regional means are exact; globally normalized PNGs were intentionally rerendered and 14 selected-panel filenames changed under expanded rule selection; diagnostics release and compact Git handoff verified |
| 20 Semantic and Structural Consistency | Finished | Finished | Yes | 447,312 metric rows, 63,216 numeric-map bundles, 9,304 rendered semantic panels, 72,520 map-manifest rows, 181/181 passing checks, and 9,311 canonical files | All eight pilot artifact paths and CSV schemas retained; metrics increased from 58,980 to 447,312, numeric bundles from 8,340 to 63,216, and rendered panels from 1,090 to 9,304; representative figure visually reviewed; diagnostics release and compact Git handoff verified |
| 21 Multi-Model Comparison | Finished | Finished | Yes | 10,504 selected candidates; 277,319 comparison rows; 2,181 disagreement rows; 168 representative rows; self-contained 58-image report; 187/187 passing checks; 9 canonical files | All nine pilot paths and CSV schemas retained; comparison/disagreement/representative rows increased from 86,531/839/76 to 277,319/2,181/168; both figures and the report were reviewed; the oversized comparison table is diagnostics-tier evidence while the other eight artifacts form the compact Git handoff |
| D02 Portrait Skin-Tone and Hand Restoration Audit | Finished | Finished | Yes | 60 portraits screened; 91 anatomical annotations; 1,265 overlap rows; 292 eligible records; 45 matched hand cases from 20 paintings; 1,638 hand-comparison rows; 2,760 exploratory rendered-skin-lightness rows; 32 blinded review units; 99/99 checks; 16 canonical files | New supplemental Controlled-300 analysis with no pilot output counterpart; all evidence is derived from frozen N01–N21 inputs, the 20-visual/17-table report is self-contained, all 14 registered checksums pass, and the complete 41.64 MB record stays in GitHub/Git LFS without a separate Hugging Face release |
| 22 Damage-Size Diffusion Uncertainty Extension | Finished | Finished | Yes | 245 cases across 35 paintings; 735 new candidates; 245 four-seed groups; 1,470 unordered pairs; 33,320 metric rows; 245 numerical maps; 245 overlays; 236/236 checks; 988 canonical files | All ten pilot artifact roles and schemas retained; case-dependent rows and images increased exactly sevenfold from the 35-case pilot; candidate images and diagnostic maps are split across their verified Hugging Face repositories while compact records remain in Git |
| 23 Damage-Size Sensitivity Analysis | Finished | Finished | Yes | 35 paintings (seven/category), 245 matched cases, 980 four-method primary candidates, 245 Stable Diffusion uncertainty groups, 7,035 canonical analysis rows, 494 inferential rows, 124/124 passing checks, 10 analytical views, eight visual panels and eight canonical files | All eight pilot paths and schemas retained; analysis rows increased from 1,901 to 7,035, the report remains self-contained with 18 embedded and zero external images, and bounded inference replaces infeasible exhaustive enumeration |
| 24 Mask Robustness Analysis | Finished | Finished | Yes | 35 paintings (seven/category), 105 matched groups, 525 cases, 2,100 four-method primary candidates, 44,847 canonical analysis rows, 139/139 passing checks, 10 analytical views, eight visual panels and seven canonical files | All seven pilot paths and schemas retained; analysis rows increased from 5,373 to 44,847; the report remains self-contained with 18 embedded and zero external images; bounded painting-level inference replaces infeasible exhaustive enumeration |
| 25 Synthetic Degradation Analysis | Finished | Finished | Yes | 35 paintings (seven/category), 1,155 generated cases, 350 eligible localized cases, 1,400 four-method primary candidates, 11 bounded SDXL candidates, 34,977 canonical analysis rows, 129/129 passing checks, 14 analytical views, nine visual panels and seven canonical files | All seven pilot paths and schemas retained; analysis rows increased from 4,695 to 34,977; the report remains self-contained with 23 embedded and zero external images and 298 tiles; bounded painting-level inference replaces infeasible exhaustive enumeration |
| 26 Grouped and Statistical Analysis | Finished | Finished | Yes | 300 paintings; 10,480 four-method core candidates across 2,620 cases; 24 bounded SDXL candidates; 1,025 uncertainty groups; 13,272 statistical rows; 694 correlation rows; 1,344 ranking rows; 111/111 checks; 10 canonical files | All ten pilot paths and all eight artifact roles and schemas retained; statistical, correlation and ranking rows increased from 4,174, 504 and 258 respectively; the self-contained report contains 48 embedded images, 252 tiles and no external image dependency; compact GitHub handoff requires no separate Hugging Face release |
| 27 Failure Taxonomy and Trustworthiness Flags | Finished | Finished | Yes | 13,879 unique candidates; 10,504 primary candidates; 4,100 repeated-seed memberships in 1,025 groups; 194,306 assignment rows; 152,669 flag rows; 167/167 checks; 8 canonical files; 4-hour-49-minute execution window | All eight pilot paths and six artifact roles retained; assignment/flag grids increased from 24,990/19,635; the report embeds 56 images with no external dependency; both bulk metric tables route to Hugging Face diagnostics while the six compact artifacts stay in ordinary Git under the exhausted-LFS guard |
| 28 Metric and Region-Policy Ablation | Finished | Finished | Yes | 23 fixed scenarios; 10,480 four-method core candidates across 2,620 cases; 13,879 flag candidates; 47,508 ablation rows; 319,217 flag-stability rows; 759 subgroup rows; 122/122 checks; 8 canonical files; 12-hour-20-minute execution window | All eight pilot paths, table schemas, and six artifact roles retained; ablation rows increased from 7,710 to 47,508 and flag-stability rows from 41,055 to 319,217; report tiles increased from 18 three-method to 24 four-method tiles with HINT; the 165.21 MB flag-stability table routes to Hugging Face diagnostics while the remaining scientific handoff stays in ordinary Git under the exhausted-LFS guard |
| 29 Explainable AI and Case Retrieval | Finished | Finished | Yes | 13,879 candidates across 2,620 cases and 300 paintings; 10,480 four-method primary candidates; 24 bounded SDXL candidates; 4,100 repeated-seed members in 1,025 groups; 13,144 dual-view retrieval-eligible candidates; 100 neighbour rows; 24 bounded visual units; 146/146 checks; 30 canonical files | All 30 pilot paths and six artifact roles retained; catalog rows increased from 1,785 to 13,879 while neighbour and panel counts remained intentionally bounded; report embeds 34 images with no external dependency; complete catalog routes to Hugging Face diagnostics and the bounded handoff stays in ordinary Git without LFS |
| 30 Model Cards, Compute, and Scalability | Finished | Finished | Yes | Five model cards; 32 observed and 10 projected compute rows; 11 quality anchors in two populations; two figures; 178/178 checks; 13/13 roadmap responsibilities; 12 canonical files | All 11 pilot paths retained; HINT card added as the sole new path; cards 4→5, compute rows 35→42, validation rows 165→178 and files 11→12; compact outputs stay in ordinary Git and require no Hugging Face release |
| 31 Model Report Generation | Finished | Finished | Yes | Five self-contained reports; 75 sections; 79 embedded images; 374 embedded tiles; five index rows; seven artifact records; 346/346 checks; 13/13 roadmap responsibilities; nine canonical files | All eight pilot paths retained; HINT report added as the sole new path; reports/sections/images/tiles increased 4→5, 60→75, 63→79 and 298→374; compact ~13 MiB handoff stays in ordinary Git without LFS or a Hugging Face release |
| 32 Case and Painting Report Generation | Finished | Finished | Yes | 25 manifests; 41 input tables; 300 paintings; 2,620 cases; 13,879 approved candidates; 30 bounded deep-case reports; 300 painting reports; 331 total reports; 30 grids; 2,132 embedded images; 10,622 tiles; 5,819/5,819 checks; 367 files; 5-hour-38-minute execution window | All seven pilot artifact classes, eight artifact keys/types and CSV schemas retained; the painting-report role label correctly scales from `fifty_complete_painting_reports` to `three_hundred_complete_painting_reports`; deterministic selection intentionally supersedes 42 pilot-only report/grid paths while adding 292 paths; the 361-file, 326.94 MiB reports/grids package routes to Hugging Face diagnostics and compact indexes/manifests/validation stay in ordinary Git without LFS |
| 33 Final Evaluation Report | Finished | Finished | Yes | 32 upstream manifests; 33 current input tables; 300 paintings; 3,425 registered cases; 2,620 evaluated cases; 10,480 four-method primary candidates; 13,879 approved report candidates; 1,025 uncertainty groups; 15 tables/352 rows; 24 figures; 49 claims; 18 limitations; 536/536 checks; 32 canonical files; 17-minute-18.552-second execution window | All 32 pilot paths, eight artifact roles and CSV schemas retained; table/catalogue/claim/traceability/check rows increased 293→352, 106→107, 48→49, 125→126 and 535→536; HINT is included wherever applicable, bounded SDXL remains separate, and the compact 17.69 MiB handoff stays in ordinary Git without a duplicate Hugging Face release |

Notebooks 01–33, including Notebook 12A and supplemental D02, are completed
Controlled-300 producers. Notebook 33 is the canonical Controlled-300 final
synthesis; Notebooks 34–36 remain historical Controlled-50 evidence until
individually reopened and rerun after the pre-N34 storage/access and dashboard-
design approval gate. Notebook 20's producer-specific diagnostics bundle
and compact Git handoff are remotely and locally verified. Notebook 21 passed
its completion gate for 10,504 selected candidates, 3,160,618 normalized
evidence rows, 277,319 comparison rows and 2,181 family-balanced disagreement
rows. Notebook 22 passed all 236 checks for 245 four-seed damage-size groups,
735 owned candidates, 33,320 metric rows, and 245 numerical maps. Notebook 23
passed its completion gate with 7,035 canonical analysis rows, 494 inferential
rows, 124 passing checks and a self-contained report. Notebook 24 run
`run_bbf68684c3ca47e5827c2b8b4b666351` passed its completion gate with 35
paintings, 105 groups, 525 cases, 2,100 four-method candidates, 44,847 analysis
rows, and 139 passing checks. It used 5,000 seeded painting-cluster bootstrap
draws and 100,000 seeded batched sign flips; exhaustive `35^35` bootstrap or
`2^35` sign enumeration remained prohibited. Notebook 25 run
`run_cf89ebe972364c7b8ccfefc6bf2a63ca` subsequently passed its completion gate
with 35 paintings, 1,155 generated cases, 350 eligible localized cases, 1,400
four-method primary candidates, 11 bounded SDXL candidates, 34,977 analysis
rows, and 129 passing checks. It used 5,000 seeded painting-cluster bootstrap
draws and 100,000 seeded batched sign flips, preserved every pilot artifact path
and CSV schema, and produced a self-contained 23-image report. Notebook 26 run
`run_efc978dd6d504cdb9b138a750f6dca83` subsequently passed its completion gate.
It consumed 2,620 cases per full method, 10,480 core candidates across OpenCV
Telea, LaMa, HINT and primary Stable Diffusion, 24 bounded SDXL candidates,
9,280 nonzero core quality candidates, 1,025 supported uncertainty groups and
3,150,114 normalized quality-evidence rows. It produced 13,272 statistical
rows, 694 correlation rows, 1,344 ranking rows, three figures, a self-contained
report with 48 embedded images and 252 tiles, and 111/111 passing checks. The
observed execution window was approximately 2 hours 32 minutes before final
wording QA. All ten pilot paths and all eight registered artifact roles and
schemas were retained.

Notebook 32 run `run_0d4ae193602944dda511bf54199105b1` binds 25 upstream
manifests and 41 tabular inputs to
300 paintings, 2,620 cases and 13,879 approved candidates. It retains the
pilot's bounded 30-case presentation subset, but scales complete coverage to 300
painting reports, 331 reports overall and 367 validated physical files. The
method population is 2,620 candidates each for Telea, LaMa and HINT, 5,995
report-eligible Stable Diffusion candidates and 24 completed bounded-SDXL
candidates. Stable Diffusion uncertainty covers 725 cases and 1,025 groups;
uncertainty is not applicable to deterministic methods. The 3,260 p01–p04
context-prompt candidates remain explicitly excluded because they lack the
complete N27/N29 contract. The observed execution window was approximately 5
hours 38 minutes. All 5,819 checks, 12 roadmap responsibilities, 67
mock-traceability rows and eight artifact records passed; the 331 reports contain
2,132 embedded images and 10,622 tiles with no external image dependency. Large
self-contained reports and grids use the diagnostics-tier Hugging Face handoff;
compact tables, indexes, manifests and validation stay in ordinary Git. Final
application consumption remains subject to the pre-N34 Streamlit/storage audit.

Notebook 27's Controlled-300 execution is complete and validated. Its binding union is
10,504 primary candidates plus 3,375 uncertainty-only candidates, producing
13,879 unique candidates after retaining the 725-candidate overlap only once.
The supported repeated-seed population contains 4,100 candidates in 1,025
four-seed groups. HINT is a full deterministic primary method; uncertainty
remains not applicable to Telea, LaMa, and HINT rather than zero. The canonical
complete ledgers contain 194,306 candidate-by-category rows and 152,669
candidate-by-flag rows. Run `run_bef567ee35c1409dbcecfb71f1b4f8b4`
retains all eight pilot paths and six registered artifact roles, passes all 167
checks, and produces a self-contained 56-image report without inventing new
failure categories, threshold combinations, or a combined score. Its observed
execution window was approximately 4 hours 49 minutes.

Notebook 28 run `run_4325bb483fbc4ccda670df125c40731d` is complete and
validated. It retains the fixed 23-scenario catalogue rather than enumerating a
metric powerset, analyzes 10,480 four-method core candidates across 2,620
matched cases, and applies every scenario to the complete 13,879-candidate flag
population. It persists 47,508 ablation rows, 319,217 flag-stability rows, 759
supported subgroup rows, two analytical figures, and a self-contained report
with 29 embedded images and no external dependencies. All 122 checks and all 13
roadmap responsibilities pass, all six artifact checksums match, and the
observed execution window is approximately 12 hours 20 minutes. The 165.21 MB
flag-stability table is a diagnostics-tier Hugging Face artifact; the 18.05 MB
ablation table and remaining compact evidence stay in ordinary Git.

Notebook 29 run `run_ad7603b6bdb14156a140351f6ac1f241` is complete and
validated. It persists the complete 13,879-candidate Notebook 27 union across
2,620 cases and 300 paintings, keeps 13,144 dual-view retrieval-eligible
candidates and 735 explicit retrieval-ineligible extension candidates, and
retains 4,100 repeated-seed members in 1,025 groups. Its intentionally bounded
presentation layer contains 100 neighbour rows, fourteen counterfactual panels,
ten retrieval panels, five analytical views and a self-contained report with 34
embedded images. All 146 checks and all 13 roadmap responsibilities pass; all
six artifact checksums match; and the final tree contains 30 files. The 46.81 MB
complete explanation catalogue is diagnostics-tier Hugging Face evidence. The
bounded panels, report, neighbour table, manifests and validation ledger stay in
ordinary Git under the exhausted-LFS guard.

A post-run metadata audit found that Notebook 29's artifact-registration cell
had retained the literal `controlled_50` even though its tables, figures, report,
run manifest and validated population are Controlled-300. The six canonical
artifact-manifest and project-path registry records are corrected to
`controlled_300`; no scientific payload or checksum of a registered target
artifact changed. Future artifact records must derive `dataset_scope` from the
active configuration or validated upstream scope and must never copy a pilot
literal into a completed Controlled-300 handoff.

Notebook 30 run `run_605de239145a46e9a202fd63bbbb4e9c` is complete and validated.
It adds HINT as the fifth card, consumes 32 observed runtime summaries from
N09–N12A, and replaces the obsolete 50-to-300 projections with ten explicitly
future rows: a 600-painting current-design scenario plus a hypothetical
full-design SDXL scenario. It passed 178 checks and all 13 roadmap requirements,
registered six artifact groups and produced exactly 12 files. All 11 pilot paths
remain; the HINT card is the sole added path. Its compact tables, five Markdown
cards, figures and control records belong in ordinary Git, not Hugging Face.

Notebook 31 run `run_430fd1355d3a4011bedc55b571d9544c` is complete and
validated. It adds HINT as a fifth self-contained model report, consumes 23
upstream manifests (N09–N30 plus N12A), and preserves the 40 canonical CSV
row/schema contracts. Its five reports retain the executive summary plus
fourteen report sections and all 39 traceability roles. The final contract is
five reports, five index rows, seven artifact records, 346 passing checks and
nine physical files; all report/index/artifact checksums match, no external
image dependencies or prohibited mock terms remain, and the E-drive comparison
shows no missing pilot role. The compact approximately 13 MiB handoff belongs
in ordinary Git under explicit `.gitattributes` exceptions. Do not publish a
duplicate Hugging Face release for this notebook.

Notebook 25's 41.97 MB canonical scalar table is diagnostics-tier evidence and
is published through the bounded external-artifact workflow. Its two figures,
self-contained report, manifests and validation table form the compact GitHub
handoff. The complete seven-file canonical tree remains authoritative locally.
Notebook 21 retains `core_three_model` and `sdxl_four_model_subset` as stable
historical schema identifiers so downstream consumers do not require a
gratuitous identifier migration. Their displayed labels and validated
memberships must still state the actual four-method core and five-method
bounded scopes.
No later notebook may describe its
historical Controlled-50 outputs as Controlled-300 evidence until that notebook
has been explicitly reopened, rerun, validated, baseline-compared, and committed.

Two governing files make downstream evidence availability explicit:

```text
docs/evidence_dependency_audit.md
config/evaluation/evidence_coverage.yaml
```

For N19–N33, the binding Controlled-300 population and method overlay in
`docs/final_notebook_roadmap.md` Section 2.2 supersedes pilot counts retained
in old notebooks/configuration. N19–N22 scale linearly with complete approved
coverage; N23–N25 are the explicit exception to cell-preservation: their
exhaustive five-painting statistical loops must be replaced by bounded,
painting-cluster methods without reducing cases, methods, visual categories,
quality anchors or report evidence. Never merely change `5` to `35` in a
`n^n` bootstrap or `2^n` sign-flip path. Use N26's adaptive 5,000-draw and
100,000-assignment design as the starting implementation precedent, validate
its numerical/provenance outputs for each notebook, and label Monte Carlo
results honestly. Benchmark a representative task before full execution;
target a longest batch no longer than 36 hours and use 50 hours as an
operational ceiling. Optimize or checkpoint and rebenchmark if above this
limit; do not silently thin approved scientific coverage. Later notebooks
remain bounded/linear as specified in that roadmap. Existing pilot YAML and
helpers are changed one producer at a time during its preparation layer,
not bulk-edited ahead of validated upstream outputs.

Before approving any new or explicitly reopened notebook contract, the assistant must:

1. Read both governing files together with this guideline and the roadmap.
2. Map every proposed responsibility, result, figure, report conclusion, and
   canonical output to an exact validated source artifact or to an explicitly
   approved notebook-owned computation.
3. Record the evidence population, coverage, independent statistical unit,
   supported interpretation, and prohibited interpretation.
4. Remove unsupported promises from the planned notebook rather than generating
   placeholder analyses or repeatedly advertising evidence that was never
   collected.
5. Block Batch 1 when a required responsibility has no valid evidence mapping.
6. Update both governing files whenever a controlled-300 notebook completes, an
   extension is approved, or a future responsibility is materially changed.

Completion checks inside a producer notebook are necessary but not sufficient.
The preparation layer for each consumer must also validate that the producer's
actual population and fields satisfy the consumer's downstream requirement.

Availability terminology must remain construct-specific:

- repeated-seed variation is generative uncertainty;
- variation across mask placements or geometries is input robustness;
- variation across prompts is prompt sensitivity;
- feature or semantic affinity is not a human visual-plausibility rating;
- rule-derived flags are not independent human or conservation ground truth.

### 6.6 Final supervisor and reproducibility package

Notebook 36 owns the only final delivery package. It is a packaging and
traceability notebook, not a new experiment. Its preparation layer must freeze a
versioned copy plan before Batch 1 and map every bundled or indexed item to an
exact validated source.

Final-package rules:

- copy only fixed approved paths; do not select inputs by scanning arbitrary
  output folders;
- preserve copied bytes and verify source-to-destination SHA-256 checksums;
- keep every generated file under
  `outputs/36_supervisor_publication_reproducibility_package/`;
- include the final self-contained report, five self-contained model reports,
  24 final figures, five model cards, the approved compact tables/indexes, all upstream
  run manifests, evaluation configurations, environment files, dashboard
  delivery documentation, and Notebook 36 provenance;
- index rather than duplicate the full case/painting report collection,
  selected-case grids, complete dashboard visual collection, restoration/map
  collections, model weights, and caches;
- distinguish `copied`, `generated_by_notebook_36`, and
  `indexed_not_bundled` records in the final artifact index;
- produce a concise supervisor summary using the exact proposal research
  questions, validated numbers, direct evidence-bounded conclusions, package-
  local figure links, limitations, and explicit decisions requested;
- record package size, file count, path lengths, package-relative links,
  self-contained HTML status, environment, Git state, versions, seeds, model
  revisions, compute evidence, and intentional omissions;
- reject duplicate destinations, repository escapes, stale temporary files,
  checksum mismatches, broken required links, blocking upstream failures, and
  unregistered scientific claims;
- do not relabel a non-blocking upstream warning as a pass; preserve it in the
  package provenance and explain its scope.

The package manifest must allow a reviewer to verify the bundle without the
notebook. The package README must explain where to begin, what is included, what
is indexed but absent, how to verify checksums, and what cannot be concluded.

### 6.7 Post-completion maintenance

- Documentation updates and approved application-only fixes do not require a
  notebook rerun. Keep changes within the explicitly agreed files and scope.
- Preserve approved dashboard layouts and interactions unless the user requests
  a change. New read-only views must map to exact validated sources, retain
  candidate identity and applicability, and receive focused application checks.
- Record current delivery facts in dated documentation separately from original
  run facts. A later deployment or successful application test does not clear
  Notebook 35 dependency warnings or revise Notebook 36's copied snapshots.
- Never modify a checksummed package, historical manifest, or generated report
  merely to update a URL, administrative status, or source-document wording.
- Update both governing evidence files when scientific coverage or a notebook
  completion state changes. For staged documentation-only updates, identify any
  corresponding registry work still pending rather than claim it was completed.
- Inventory refresh is a separate controlled write at the agreed handoff point;
  a documentation edit does not silently trigger it. The user commits unless
  explicitly requesting otherwise.

## 7. Repository layout

The intended high-level structure is:

```text
painting-restoration-eval/
  config/
  data/
    raw/
    model_audit/
  docs/
  notebooks/
  outputs/
    inventory/
    <notebook-owned folders>/
  src/
    restoration_eval/
  tools/
  tests/
  streamlit_app.py
  requirements.txt
  requirements_experiments.txt
```

### 7.1 Source data

`data/` contains externally acquired or manually curated inputs only:

```text
data/
  raw/
    images/
    metadata/
  model_audit/
```

Source inputs must not be overwritten by notebooks.

### 7.2 Generated data

All generated datasets, images, metrics, figures, reports, and validation outputs belong under the exact producing notebook stem:

```text
outputs/<notebook_stem>/
```

Examples:

```text
outputs/02_image_preprocessing/images/clean/
outputs/03_canonical_mask_generation/images/masks/
outputs/04_canonical_damaged_image_generation/images/damaged/
outputs/09_opencv_telea_restoration/images/restored/
outputs/13_classical_metrics/metrics/classical_metrics.csv
```

Any generated content found under `data/processed/` is legacy material, not an
authoritative input. Inspect it read-only and establish ownership before an
explicitly approved cleanup; do not infer that such a folder must still exist.

### 7.3 Sole global output exception

`outputs/inventory/` is the only project-level output folder not owned by a numbered notebook.

It contains:

```text
outputs/inventory/
  project_file_inventory.csv
  inventory_run.json
  project_paths.json
  project_paths.md
```

Legacy global folders such as these are retired after validated migration:

```text
outputs/metrics/
outputs/figures/
outputs/reports/
outputs/validation/
outputs/manifests/
outputs/dashboard/
outputs/supervisor_package/
```

## 8. Notebook-owned output structure

A notebook may create only the subfolders it needs:

```text
outputs/<notebook_stem>/
  data/
  images/
  metrics/
  figures/
  reports/
  manifests/
  validation/
  logs/
  work/
```

Definitions:

- `data/`: canonical non-metric tabular outputs and registries.
- `images/`: generated masks, damaged images, degraded images, restorations, candidates, and map images.
- `metrics/`: canonical quantitative evidence tables.
- `figures/`: selected human-facing plots, grids, and diagnostic panels.
- `reports/`: HTML, Markdown, or other stage reports.
- `manifests/`: run, artifact, candidate, embedding, and handoff manifests.
- `validation/`: final validation checks and compact failure details.
- `logs/`: logs required for audit or debugging.
- `work/`: resumable temporary state for expensive computation; never a canonical downstream input.

Rules:

- Do not create empty subfolders.
- A notebook writes only within its own output root.
- Upstream notebook folders are read-only inputs.
- Downstream code consumes declared artifacts rather than scanning directories for plausible files.
- Temporary test outputs must be isolated under the current notebook's `work/` folder.

## 9. Configuration structure

The monolithic configuration should be migrated gradually toward:

```text
config/
  project.yaml
  datasets/
    controlled_300.yaml
  experiments/
    canonical_damage.yaml
    damage_size.yaml
    mask_robustness.yaml
    synthetic_degradation.yaml
  models/
    opencv_telea.yaml
    lama.yaml
    stable_diffusion.yaml
    sdxl.yaml
    hint.yaml
  evaluation/
    regions.yaml
    metrics.yaml
    flags.yaml
  reporting.yaml
```

Configuration requirements:

- Every file has a schema/configuration version.
- Paths are repository-relative.
- Seeds and numerical policies are explicit.
- Scientific defaults are configuration values, not hidden notebook literals.
- Model availability and experiment applicability are explicit states.
- A configuration snapshot and checksum are recorded in each run manifest.

Supported execution profiles:

```text
smoke
controlled_300
```

`controlled_300` is the sole active full profile. The old 50-painting
configuration is recoverable from `pilot-50-complete` and must not be retained as
a parallel active file. Until a producer notebook completes its controlled-300
rerun, its working-tree outputs and dashboard claims remain historical
50-painting evidence.

### 9.1 Controlled-300 population constants

These are the approved top-level contracts; lower-level metric and artifact row
counts must still be derived from the corresponding registries and policies:

| Contract | Expected count |
|---|---:|
| Paintings | 300 |
| Paintings per broad visual category | 60 |
| Shared focused-experiment paintings | 35, seven per category |
| Canonical cases | 1,500 |
| Damage-size cases | 245 |
| Mask-robustness cases | 525 |
| Procedural degradation cases | 1,155 |
| Registered cases | 3,425 |
| Restoration-eligible cases per full method | 2,620 |
| Bounded SDXL cases | 35 |
| Full methods | Telea, LaMa, Stable Diffusion primary coverage, and HINT |
| Four-seed uncertainty groups | 1,025 |
| Approved retained candidate records | 13,890 |
| Total restoration executions | 17,150 |

Stable Diffusion retains seeds `2026`, `2027`, `2028`, and `2029`, the generic
and scratch-aware prompt separation, 780 canonical prompt-specific uncertainty
groups, and 245 damage-size uncertainty groups. HINT is deterministic and must
use robustness/sensitivity terminology rather than repeated-seed uncertainty.
SDXL remains a one-seed bounded feasibility branch and must not appear as a
full-coverage method.

## 10. Project inventory contract

The inventory remains a discovery, audit, and path-verification tool. It must not dynamically choose notebook inputs.

The updated inventory should:

- exclude Git metadata, environments, caches, checkpoints, and its own generated files;
- record a schema version and inventory run ID;
- record generation timestamp and repository root;
- record repository-relative normalized paths;
- support CSV, TSV, JSON, YAML, Parquet, notebooks, HTML, Markdown, text, and image formats;
- record file type, size, modification time, and depth;
- record CSV row count, column count, and columns;
- record JSON top-level type and keys where practical;
- record image dimensions, mode, and format;
- record notebook cell counts and saved error-output counts where practical;
- make full or partial hashing configurable;
- record read errors without aborting the full inventory;
- produce a compact summary inside `inventory_run.json` rather than a second summary CSV unless a CSV is proven necessary.

Each notebook reads the inventory in Batch 1 and records:

- inventory path;
- inventory run ID;
- inventory checksum;
- inventory generation time;
- whether every declared input appears in the inventory.

Notebooks must not save notebook-local inventory snapshots.

## 11. Project paths registry

`project_paths.json` is the machine-readable authoritative registry. `project_paths.md` is generated from it for human review.

The registry is updated only after a notebook passes its completion gate.

Each registered artifact records:

```text
artifact_key
producer_notebook
relative_path
artifact_type
artifact_role
schema_version
dataset_scope
experiment_scope
validation_status
row_count
file_count
checksum
```

The registry must not contain temporary, failed, stale, or QA-only artifacts unless they are deliberately retained for audit. A completed upstream artifact with a documented non-blocking warning may be registered with `validation_status: warning`; the warning must not be rewritten as `passed`.

## 12. Input/output contract

Before Batch 1, every notebook requires an approved contract containing:

| Field | Requirement |
|---|---|
| Input key | Stable logical identifier |
| Producer | Source data, configuration, tool, or upstream notebook |
| Relative path | Exact expected path |
| Required | Required or optional |
| Format | CSV, JSON, YAML, PNG, NPZ, HTML, etc. |
| Schema version | Required schema identifier |
| Required columns/keys | Exact minimum schema |
| Expected cardinality | Expected rows, files, cases, candidates, or regions |
| Applicability | Dataset, experiment, model, and candidate scopes |
| Output key | Stable artifact identifier |
| Output path | Exact notebook-owned path |
| Artifact role | Primary, downstream, reporting, QA, or temporary |
| Downstream consumers | Notebooks or application components using it |

Notebook code should declare explicit `INPUTS` and `OUTPUTS` mappings. It must not select files by modification time, filename similarity, or an unqualified “latest” convention.

## 13. Canonical identifiers

Identifiers must be stable, deterministic, compact, and independent of filesystem locations.

Required identifier families include:

```text
dataset_id
dataset_version
dataset_scope
experiment_id
configuration_id
painting_id
case_id
mask_id
degradation_id
restoration_id
model_id
candidate_id
region_id
metric_row_id
artifact_id
run_id
```

Identifiers must not encode long prompts, titles, artist names, or full configuration prose.

## 14. Normalized data contracts

The repository must not propagate all upstream columns into every downstream table.

### 14.1 Artwork table

Owns artwork identity and metadata:

```text
painting_id
dataset_id
category
style_or_period
artist
date_or_period
medium
source
source_url
license
metadata_completeness
raw_image_path
```

### 14.2 Processed-image table

Owns preprocessing information:

```text
painting_id
processed_image_id
processed_path
width
height
content_x_min
content_y_min
content_x_max
content_y_max
padding values
preprocessing_version
status
```

### 14.3 Mask/degradation tables

Own generator parameters, seeds, morphology, spatial support, target/realized area, and paths. Canonical damage, damage-size, robustness, and synthetic degradation remain separate experiment tables with a shared minimum case schema.

### 14.4 Unified case registry

Contains only core cross-experiment fields and foreign keys:

```text
case_id
dataset_id
dataset_scope
experiment_id
painting_id
input_image_path
clean_image_path
mask_or_effect_id
mask_or_effect_path
damage_or_degradation_type
target_damage_fraction
realized_damage_fraction
source_manifest_path
status
```

### 14.5 Model eligibility table

Defines whether a case/method combination is methodologically valid:

```text
case_id
model_id
eligible
eligibility_reason
input_semantics
mask_semantics
restoration_objective
```

This is particularly important for non-binary degradations. “Where applicable” must be replaced with auditable eligibility rules.

### 14.6 Restoration/candidate table

Contains model-specific execution evidence without copying all upstream metadata:

```text
restoration_id
case_id
model_id
candidate_id
candidate_index
seed
prompt_policy_id
model_version
configuration_id
restored_path
runtime_seconds
device
precision
retry_count
status
issue
```

### 14.7 Canonical metric table

Metric-family outputs use a consistent long-form interface:

```text
metric_row_id
case_id
candidate_id
model_id
metric_family
metric_name
region_id
damaged_value
restored_value
improvement_value
improvement_direction
metric_version
status
issue
```

Metadata needed for grouped analysis is joined through stable identifiers.

## 15. Universal manifest and validation outputs

Every completed notebook normally produces:

```text
manifests/run_manifest.json
manifests/artifacts.csv
validation/checks.csv
```

### 15.1 Run manifest

Minimum fields:

```text
run_id
notebook_id
notebook_name
origin
run_status
started_at_utc
completed_at_utc
git_commit
git_dirty
inventory_run_id
dataset_versions
configuration_paths
configuration_checksums
helper_versions
python_version
package_versions
hardware
inputs
outputs
expected_counts
observed_counts
validation_summary
known_limitations
```

### 15.2 Artifact manifest

Minimum fields:

```text
artifact_id
artifact_key
producer_notebook
artifact_type
artifact_role
relative_path
format
dataset_scope
experiment_id
schema_version
row_count
file_count
size_bytes
checksum
validation_status
```

### 15.3 Validation table

Use one compact table instead of one CSV per batch:

```text
validation_stage
check_id
check_description
severity
expected
observed
passed
details
```

Batch-level validation may exist in memory. Only the consolidated final table is persisted unless a separate failure table is required downstream.

Every cell that registers validation checks must be safe to rerun in the same
kernel. Before adding checks for its own `validation_stage`, the cell must rebuild
the `ValidationCollector` while retaining checks from every other stage and
removing any existing checks from the stage it is about to recompute. It must
then register the complete stage again. This stage-replacement pattern prevents
duplicate-key failures without hiding accidental duplicates within one execution
of the cell. It applies to all notebooks and all validation stages, including
preflight, loading, smoke-test, execution, scientific-validation, persistence,
analysis, manifest, and completion-gate cells.

Final persistence and cleanup cells must also be safe to rerun after successful
completion. An already-absent notebook-owned work directory and already-closed
memory maps are valid completed states, not missing-input failures. A rerun must
still reject unexpected work files, partial cleanup states, or missing canonical
artifacts before rewriting the completed manifest and final validation evidence.

The approved pattern is:

```python
validation_stage = "batch_n_stage_name"
retained_checks = [
    check
    for check in VALIDATION.checks
    if check.validation_stage != validation_stage
]
VALIDATION = ValidationCollector()
VALIDATION.extend(retained_checks)
```

After this reset, the cell adds all checks for `validation_stage` normally. A
rerun must produce the same stage keys, check count, and outcomes as the first
run. Do not suppress `ValueError` from `ValidationCollector.add`, use
`drop_duplicates` as a substitute, or retain partially rebuilt stage checks.

## 16. Output minimization

Persist an artifact only if it is:

- the canonical output of the notebook;
- a declared downstream input;
- required for reproducibility;
- required for a report, dashboard, thesis, or publication;
- a deliberately retained audit artifact.

Do not persist:

- every in-memory grouping;
- multiple differently named copies of the same table;
- per-batch inventory snapshots;
- redundant validation CSVs;
- temporary smoke-test tables after final validation;
- ad hoc “final”, “latest”, “new”, “fixed”, or “v2” copies.

## 17. Filename and path rules

- Use lowercase ASCII `snake_case`.
- Notebook folders use the exact notebook stem.
- Do not repeat the full notebook name inside every filename.
- Prefer filenames shorter than 80 characters.
- Prefer repository-relative paths shorter than 180 characters.
- Use compact stable IDs for per-case assets.
- Never embed prompt text, artwork titles, or artist names in filenames.
- Avoid ambiguous suffixes such as `final`, `latest`, `new`, and `fixed`.
- Version scientific schemas and algorithms inside manifests/configuration, not filenames.
- Persist repository-relative paths using forward slashes.

## 18. Shared helper policy

Notebooks orchestrate; helpers compute, validate, and persist reusable structures.

Helpers must:

- accept paths and configuration explicitly;
- avoid hardcoded repository output paths;
- avoid hidden writes;
- return structured results;
- use deterministic seeds when relevant;
- validate important arguments;
- provide docstrings and type hints;
- expose algorithm/schema versions where scientifically relevant;
- separate computation from display and reporting;
- preserve error details instead of silently dropping failed cases.

Foundation modules should include:

```text
paths.py
schemas.py
regions.py
manifests.py
validation.py
```

Substantial incompatible helper redesign allows full-file replacement. Isolated defects should receive targeted changes.

## 19. Canonical region helper

`src/restoration_eval/regions.py` is the only authoritative spatial-region implementation.

It must support:

- full image;
- painting-content region;
- exact masked pixels;
- mask bounding-box crop with configurable margin;
- inner boundary band;
- outer boundary band;
- symmetric inner-plus-outer boundary ring;
- outside-mask content region;
- optional outside boundary ring;
- degradation/effect support region;
- patch/sliding-window regions for semantic analysis.

Every region object records:

```text
region_id
region_type
spatial_support
x_min
y_min
x_max
y_max
pixel_count
width
height
parameters
validity_status
```

Metric helpers must reject mathematically invalid metric-region combinations. Sparse masked-pixel SSIM must never be reintroduced simply to populate a dataframe column.

## 20. Metric architecture

Restoration remains model-specific because inference, hardware, prompts, failures, retries, and candidates differ by model.

Evaluation is model-agnostic:

- one classical-metric notebook;
- one LPIPS notebook;
- one CLIP/DINOv2 notebook;
- one spatial-diagnostics notebook;
- one local-consistency notebook;
- one uncertainty notebook;
- one semantic/structural notebook.

All validated model manifests are passed through the same helper implementation and region policy.

Optional SDXL availability is determined from a validated result manifest, not from the presence of source code or a notebook.

Allowed availability states:

```text
full_evaluation_complete
partial_evaluation
feasibility_only
unavailable
failed
```

## 21. Notebook batch design

Before code generation, define every batch and approve its inputs, outputs, side effects, expected cardinality, and validation checks.

### Batch 1 — Contract and initialization

- purpose, scope, exclusions, and research responsibility;
- imports and environment checks;
- repository-root resolution;
- configuration loading;
- inventory loading;
- explicit `INPUTS` and `OUTPUTS` declarations;
- output-root validation;
- expected schemas and counts;
- preflight validation;
- dry-run summary.

### Batch 2 — Input loading and validation

- load declared inputs;
- validate schema versions and keys;
- validate unique identifiers;
- validate file references;
- validate input/output scope compatibility;
- stop on blocking failures.

### Batch 3 — Smoke or representative test

- run a deterministic bounded example where applicable;
- validate outputs and invariants;
- render compact visual inspection;
- keep temporary outputs under `work/`.

### Batch 4 - Full execution

- run approved dataset and experiment scopes;
- support resume/checkpoint behavior for expensive stages;
- report progress after every 10 completed cases and after the final case for
  long case-generation stages;
- include completed/total counts, percentage, elapsed time, throughput, and the
  latest stable case or group identifier in each progress message;
- keep the progress interval configurable through the notebook-owned
  experiment configuration, with `10` as the default;
- record failures and retries;
- never silently skip cases.

### Batch 5 — Scientific and filesystem validation

- verify row and file counts;
- verify unique keys;
- verify output dimensions and formats;
- detect stale and orphaned files;
- reload persisted outputs;
- evaluate experiment-specific invariants.

### Batch 6 — Analysis and visualization

- generate necessary summaries;
- render representative cases selected by explicit rules;
- save only downstream or thesis-relevant figures;
- use standardized labels, scales, palettes, and captions.

### Batch 7 — Persistence and handoff

- save canonical outputs;
- write run and artifact manifests;
- write consolidated validation checks;
- confirm every persisted path belongs to the notebook output root.

### Batch 8 — Completion gate

- map every truth-source requirement to implementation evidence;
- verify all declared inputs and outputs;
- identify optional omissions and reasons;
- confirm rerun/idempotence behavior;
- produce a final pass/fail table.

Not every notebook needs eight batches. Expensive inference notebooks may subdivide execution, but the final notebook must remain linear and coherent.

## 22. Notebook quality requirements

A final notebook must:

- run top to bottom in a fresh kernel;
- contain clear Markdown sections explaining purpose, methods, inputs, outputs, and limitations;
- contain no hotfix, repair, duplicate, or replacement cells;
- contain no undeclared dependency on prior interactive state;
- avoid repeated imports and repeated helper definitions;
- keep reusable computation out of local notebook functions;
- use project-relative persisted paths;
- validate inputs before expensive work;
- reload and verify persisted outputs;
- present concise tables rather than unbounded dataframe dumps;
- render selected representative visuals;
- save full-resolution visual artifacts externally;
- avoid excessive embedded image output;
- end with the completion-gate table.

For an explicitly approved new refactoring cycle, inherited completion labels
must be reset and revalidated. During the controlled-300 rerun, reset only the
current notebook after its contract is approved; do not bulk-change downstream
headers or imply that their historical 50-painting outputs are current.

## 23. Visualization policy

Visual evidence is mandatory where it materially supports interpretation.

Requirements:

- standardized plot dimensions, fonts, palettes, labels, and captions;
- comparable error-map and heatmap normalization where comparison is intended;
- explicit indication when normalization is global, per-model, per-case, or percentile-clipped;
- mask, content-box, mask-box, and boundary overlays where relevant;
- rule-based case selection to reduce cherry-picking;
- selected low-resolution previews may remain rendered in notebooks;
- full-resolution assets are saved externally and registered;
- large galleries must not be embedded into notebooks.

## 24. Stale and orphaned artifacts

Default behavior is detect and report.

Automatic cleanup is permitted only when:

- an explicit cleanup flag is enabled;
- the resolved target is the current notebook's exact output root;
- the target is printed and validated before removal;
- upstream, source, Git, environment, and project-root paths are excluded;
- cleanup actions are recorded in validation output.

Migration cleanup of legacy folders is a separate explicitly approved operation and must not occur implicitly inside a notebook.

## 25. Expensive execution and resume policy

Restoration, LPIPS, feature extraction, uncertainty, SDXL, and large-scale map generation may use resumable execution.

Resume rules:

- completion is determined by validated IDs and checksums, not file existence alone;
- existing successful candidates may be reused only when configuration, model revision, helper version, and input checksums match;
- failed and partial cases remain visible in manifests;
- checkpoints live under the notebook's `work/` folder;
- canonical outputs are consolidated only after the approved scope completes.

Progress reporting is required even when resume support is unnecessary. It is
observational only: reporting must not alter seeds, case ordering, generated
artifacts, validation outcomes, or reproducibility.

## 26. Reproducibility environment

There are separate dashboard and experimental environments:

- The root README specifies Python 3.12 and `requirements.txt` for dashboard use.
- All 36 completed notebook run manifests record Python 3.12.6. Their recorded
  package, device, CUDA, model, and configuration versions describe the actual
  runs; a recommended interpreter in a requirements-file comment does not.
- `requirements_experiments.txt` is the separate experimental dependency file,
  not the dashboard install target or an exact lock of every executed producer.
  Its reviewed header labels the original Python 3.11 recipe, uses a separate
  `.venv-experiments` environment, and installs the correct experimental file.
  Dependency specifications are preserved; a fresh install and exact version
  reconciliation have not been validated by documentation maintenance.
- Notebook 35 recorded dependency-version differences, inherited by Notebook 36.
  Subsequent public deployment does not establish exact reproduction of those
  historical environments or retroactively remove their warnings.

Before any explicitly approved experimental reproduction:

- reconcile conflicting package pins;
- verify model and CUDA compatibility;
- keep dashboard and experimental dependencies in separate environments;
- record exact package versions;
- record Python, operating system, CPU, GPU, CUDA, and VRAM;
- record Git commit and dirty-state information;
- record configuration and helper checksums;
- record all relevant seeds and model revisions.

Any future interpreter or dependency change requires targeted compatibility
evidence. Preserve historical version records and document the new environment
separately; do not rerun models merely to reconcile documentation.

## 27. Version control and large artifacts

- Preserve existing user changes unless explicitly instructed otherwise.
- Do not commit environments, caches, notebook checkpoints, replaceable temporary files, or unnecessary logs.
- Notebooks 01--11 of the Controlled-300 rerun form the final approved
  full-output Git/LFS checkpoint. Their committed evidence is not rewritten or
  removed during the active rerun.
- Beginning with Notebook 12, the complete canonical output tree remains local
  and notebook-owned, but bulk generated evidence is not automatically a Git
  publication requirement. GitHub is the compact scientific repository;
  later large producers may use the verified N16/N17 indexed-bundle method
  after a separate producer-level publication gate. The pre-N34 approval gate
  still governs the dashboard's final storage and access design.
- After migration, no authoritative generated images should remain under `data/processed/`.
- Standalone HTML reports may embed declared web-sized figures and
  representative images so the report remains usable when downloaded alone.
  Avoid embedding unrestricted full-resolution collections, and register the
  canonical source artifacts and checksums used to construct each embedded
  display image.
- Notebook sizes should remain reviewable; very large embedded outputs must be reduced.

### 27.1 Controlled-300 storage and publication boundary

**Dated indexed-bundle exception (2026-09-17).** The user first approved a
bounded N16 proof of indexed, byte-exact ZIP-member retrieval in the existing
public diagnostics repository. This is a proposed access method, not completed
N16/N17 publication or approval of the final dashboard backend by itself. An image may
be individually retrievable either as a direct remote object or as a validated
indexed ZIP member; a separate remote object per image is not required. Its
original bytes, scientific identity, producer path, and provenance must remain
available. The approved smoke is limited to four bundles and 128 MiB under an
isolated test prefix. Full N16 and then N17 require separate approval and
hash-verified release records. Existing N12/N12A/N13/N15 direct-file records
and all canonical local scientific artifacts remain unchanged. The N33-to-N34
storage/dashboard review gate remains in force; the pilot deployment is not
modified by this smoke. The implementation lives in
`tools/bundled_artifact_publication.py` and
`src/restoration_eval/bundled_assets.py`; the old direct-file publisher is not
reused for N16 maps.

The bounded test subsequently passed: 76 indexed images from three paintings
were read publicly and matched their source hashes; three ZIPs and eight
remote objects passed byte-count/full-SHA-256 checks at pinned revision
`02ba1d971ffdf9e855f07e5266bba18cac71b929`. Its temporary objects were
removed from the current diagnostics branch by cleanup commit
`debc818363b5271b97e9105aa77807927e493ee7`; the smoke record is retained.
The user then separately approved and completed the full N16 release: 76,034
original images in 333 bundles, 641 remotely verified objects totaling
2,625,210,541 bytes at pinned diagnostics revision
`8c22aa62c5be60d8a15c9c00d9bc9a6f81557b79`. Four public sample image
reads matched the local originals. The full record is
`outputs/inventory/bundled_publication_n16_full.json`. The smoke alone was not
proof of full publication; the full record is. N17 subsequently passed its
own separate full-release gate: 27,926 images in 360 bundles, 669 remotely
verified objects totaling 5,622,373,385 bytes at pinned diagnostics revision
`ceac6a5aa67fe2a0f8c840c46f22306e7f606749`. Its record is
`outputs/inventory/bundled_publication_n17_full.json`. Both releases retain
their original images and oversized tables locally.

The `diagnostics` dataset owns these releases because N16/N17 create maps,
local texture/colour/seam evidence, selected panels, metrics and provenance.
The `candidates` dataset owns model-generated restorations such as the verified
N12 SDXL and N12A HINT outputs; it received no N16/N17 bundle release. Indexed
per-painting `ZIP_STORED` bundles addressed the failed per-image Hub rate-limit
path and keep bulk images/tables out of Git/LFS. They reduce object/request
counts, not total hosted bytes by compression. The member index must retain
producer path, asset identity, byte count, hash and pinned revision.

Notebook 19 has passed its local Controlled-300 gate. Its 2,475 owned
presentation PNGs (780 uncertainty panels, 780 overlays, 900 scratch-aware
local-component maps, and 15 selected panels) are diagnostic assets, so its
verified indexed-bundle destination is the existing Hugging Face
`diagnostics` dataset, not `candidates`. Its 3,000 upstream manifest links
remain links and must not be republished as Notebook 19-owned images. The
780-entry numeric NPZ, compact CSVs, 15 selected panels, validation and
manifests remain in the GitHub scientific handoff; the remote bundle may also
contain validated copies for self-contained diagnostic access. The user ran
the separate upload and pinned verification gates. The record
`outputs/inventory/bundled_publication_n19_full.json` pins revision
`e080704d57d2a10ebe09d0395f348b9da85ea8f7`: all 609 objects and
1,329,281,895 remote bytes passed verification, as did four public sample
members. This establishes Hugging Face availability independently of the
still-pending compact Git commit.

Notebook 20 has passed its local Controlled-300 gate with 447,312 transparent
semantic/structural metric rows, 63,216 numeric bundles, 9,304 rendered panels,
72,520 map-manifest rows, 181 passing checks, and no temporary work directory.
Its diagnostic panels, numeric archive, large metric table, normalized map
manifest, representative figure, and provenance use the same indexed
per-painting bundle contract as Notebooks 16, 17, and 19. The destination is
Hugging Face `diagnostics`, not `candidates`, because Notebook 20 produces
derived diagnostic evidence rather than restoration candidates. Git retains
the notebook, helper/configuration changes, compact manifests and validation,
the representative figure, inventory, and the pinned publication record.
The verified release is pinned at revision
`8f849ea89e0fa6cabf309481d63c44bb3878edc3` under
`bundled_assets/v1/controlled_300/20_semantic_and_structural_consistency/b29a25d740c9dea4`.

The storage change does not alter notebook science, output ownership, schemas,
validation, or the requirement to generate and inspect every approved canonical
artifact locally. Every notebook continues to write its complete evidence to
`outputs/<exact_notebook_stem>/`, and the project inventory continues to index
the complete local tree.

The current storage tiers are:

1. **GitHub scientific repository:** notebooks, helpers, configuration,
   documentation, compact canonical tables, validation, manifests, selected
   figures, and remote-asset indexes.
2. **Complete local evidence:** all notebook-owned images, maps, restorations,
   large numeric tables, and source manifests remain under their exact local
   `outputs/<notebook_stem>/` roots. This is the authoritative active corpus.
3. **Verified external evidence:** N12, N12A, N13, N15, and the separately
   approved N16/N17/N19 bundle releases retain their records. Later large
   producers may use the same indexed-bundle workflow after notebook-specific
   classification, capacity checks, full remote verification, and a separate
   user-controlled upload gate. This does not decide the dashboard backend.
4. **Future storage and deployment:** after N33 and before changing N34, review
   the complete local evidence, prospective storage options, costs, public
   access, and dashboard feasibility with the user. Only an approved storage
   contract may feed the N34 dashboard design and later deployment. Zenodo
   archival release remains a separate post-freeze decision.

**Git LFS quota guard (2026-09-21).** GitHub reported 9.01 GiB of the included
10.0 GiB LFS allowance used (90%), with a `$0` hard budget that blocks further
usage rather than permitting overage, and an allowance reset on 2026-10-01.
The remaining allowance is an emergency margin, not a publication target.
Until the reset and a fresh quota check:

- never stage a complete post-N11 image tree or another large numerical archive
  to Git/LFS;
- use exact-path Git staging rather than `git add .`;
- keep `outputs/inventory/project_file_inventory.csv` local and regenerate it
  after every notebook, while committing the compact `inventory_run.json` that
  records its SHA-256, byte count, run ID, summary, and read-error count;
- publish N22's 735 owned restoration PNGs as 35 per-painting indexed bundles
  in the Hugging Face `candidates` dataset, and publish its 245 uncertainty
  overlays plus `data/uncertainty_maps.npz` as 35 indexed bundles and complete
  diagnostic sidecars in the Hugging Face `diagnostics` dataset;
- keep N22's compact tables, manifests, validation and representative figure
  in GitHub, while preserving the complete local canonical tree until the
  pre-N34 storage/dashboard audit explicitly approves any cleanup;
- do not make scientific completion depend on external publication, and do not
  publish mixed candidate and diagnostic assets under one misleading class.

**Git LFS hard-cap state (2026-09-22).** The included Git LFS allowance is now
fully exhausted. This supersedes the remaining-margin wording above until the
allowance resets and a fresh billing check confirms usable capacity. During the
hard-cap state:

- stage **no new LFS-filtered object**, even when it is small; run
  `git check-attr filter -- <path>` before staging any generated CSV, HTML, or
  image and require `filter: unset` for the compact Git handoff;
- add exact `.gitattributes` ordinary-Git overrides only for explicitly approved
  compact artifacts, never for bulk tables or image trees;
- add every bulk table or media tree to `.gitignore`, publish it through the
  approved Hugging Face tier with full SHA-256/size verification, and commit only
  its compact publication record after verification;
- use exact-path `git add` commands and verify `git lfs status` contains no new
  objects before committing; `git add .` remains prohibited;
- Notebook 27 routes its 213.50 MiB failure-assignment table and 115.27 MiB flag
  table to Hugging Face `diagnostics`. Its taxonomy, canonical figure,
  self-contained report, manifests, and validation ledger form the ordinary-Git
  scientific handoff.
- Notebook 28 routes its 165.21 MB candidate-by-scenario flag-stability table to
  Hugging Face `diagnostics`. Its 18.05 MB canonical ablation table, two figures,
  self-contained report, manifests, and validation ledger are explicitly
  de-filtered from Git LFS and form the ordinary-Git scientific handoff.

N22 candidate restorations are candidate-class evidence; its uncertainty maps
and overlays are diagnostic-class evidence. The approved split publication uses
the same producer name under separate `candidates` and `diagnostics` repository
prefixes, complete painting indexes, bounded ZIP members and pinned remote
verification records. This split does not lose cross-tier identity: both sides
retain the same source run ID, case IDs, painting IDs, checksums and producer
provenance. All N22 artifacts remain complete and authoritative locally until
the pre-N34 storage and Streamlit audit verifies consumption from both tiers.

The currently deployed `pilot-50` application remains unchanged during the
Controlled-300 rerun. No history rewrite, branch deletion, Git/LFS purge, or
bulk-output untracking is permitted during the active transition without a
separate exact-target review and explicit user approval.

Before a local bulk artifact may ever be deleted or represented as remotely
available, its external copy must be verified against a publication record
containing at least:

```text
artifact_id
producer_notebook
local_relative_path
storage_tier
remote_uri
sha256
size_bytes
media_role
publication_status
published_at_utc
```

For already published N12–N15 artifacts, the recorded remote SHA-256 and byte
counts remain the evidence of the completed publication gate. A URL or matching
size alone is not verification. A failed or incomplete upload never authorizes
local deletion. Do not infer publication of N16 or later notebooks from the
existence of a Hugging Face repository, a partial transfer, or old records.
N16 and N17 claims rest only on their separate complete pinned-release records.

The machine-readable historical provider and classification contract is
`config/publication/external_storage.yaml`. Its N12/N12A/N13/N15 verified
records remain valid. Do not restore the failed N16 per-file image uploader for
N16/N17 or later image-heavy producers. A narrowly scoped exception is allowed
for a producer with only one or a few oversized tabular or array artifacts:
`tools/external_artifact_publication.py` may publish those bounded objects after
full local hashing and must verify each by a complete remote read. Notebook 24's
single 52.16 MB scalar CSV is the reference case for this exception; its figures,
report, manifests and validation remain in the compact GitHub handoff. The N16
per-file LFS attempt exhausted Hugging Face's
free-account Hub API request limit; the user removed its partial remote
repository and its local upload cache was cleared. Separate bundled N16 and
N17 releases subsequently passed full remote verification; canonical evidence
still remains fully local.

The local project inventory and the publication registry have different
responsibilities. The inventory describes what exists in the executing local
repository. The publication registry describes where approved evidence is
available outside that working tree. Neither file may silently stand in for
the other.

During N16–N33, finish one notebook at a time using its complete local
outputs. Refresh the inventory, inspect every read error, and reconcile each
producer's paths, counts, SHA-256 values, and completion manifest. Repair an
isolated invalid artifact from its recorded inputs when it can reproduce the
original manifest checksum; otherwise stop and disclose the mismatch. Do not
rerun expensive stages merely to address a single corrupted presentation file.

N16's 76,020 candidate maps and N17's 27,912 candidate maps stay local and
individually accessible by their producer manifests. Their full numeric CSVs
also stay local: N16 is about 82 MB and N17 about 1.15 GB, so neither is an
ordinary compact GitHub table. N16's complete maps and metric table are also
available in its verified indexed-bundle release; N17's maps, summary figure,
and metrics are available in its own verified indexed-bundle release.
Before the N16/N17 compact Git commits, the user must
remove the still-tracked pilot versions of these two CSVs and their selected
figure PNGs from the Git index with exact-path `git rm --cached` commands;
the local files remain intact. GitHub commits may contain notebooks,
configuration, helpers, compact tables, validation records, and manifests;
no newly generated images are staged during this phase. Existing verified
N12–N15 external objects remain untouched.

After N33, before N34 preparation, perform a separate storage review using
actual producer sizes, file counts, license constraints, retrieval needs,
free-tier limits, and the complete proposed dashboard visual index. Compare
at least direct-object access and bounded on-demand packaging; do not assume
Hugging Face datasets, buckets, Git LFS, or Zenodo solves the problem. Test one
representative public write/read path and its cost/quota behavior before any
bulk migration. Obtain user approval for the storage contract first, then for
the N34 dashboard scope and UI; N35 validates the implemented application.
The live 50-painting dashboard stays on its existing branch and deployment.

Use the two governing boards in
[`docs/dashboard_design_finalists/approved_current/`](dashboard_design_finalists/README.md)
during that UI review. Confirm each room's content, evidence source, dominant
interaction, accessibility fallback, responsive behavior, and remote-asset
requirements. Record every approved deviation or borrowed alternative
component; silence is not approval to redesign the selected system.

**Preliminary Streamlit bundle access, not yet a deployment contract.** N34
may include compact metadata plus local-to-remote case/candidate/map indexes.
A selection would resolve to a painting index under a pinned N16/N17 revision,
download only the needed bounded ZIP, validate the bundle and exact member,
then reuse it in a size-limited cache. Never enumerate/download every bundle
or ingest the N17 gigabyte CSV at startup. Compact filterable numeric views or
on-demand partitions must be designed separately; they cannot silently omit
applicable cases. Before implementation, test public cold/warm retrieval,
cache eviction, Streamlit memory/network budgets, missing-asset behavior, and
representative cross-model views with the user. The pre-N34 storage and page
design approval gate and N35 validation remain mandatory.

For each completed notebook before that review, provide scoped **GitHub
scientific-record commands** and, if large outputs warrant publication,
separate **Hugging Face indexed-bundle commands** using the validated N16/N17
strategy. Classify every asset as candidate restoration (`candidates`) or
diagnostic/map/panel/oversized derived evidence (`diagnostics`); do not create
one remote object per image. Include local staging verification, progress,
resumable upload, full pinned-revision remote object/hash verification, public
sample member reads, and a compact publication record. Check quota and object
count before upload; keep complete local evidence. State exactly which large
artifacts are excluded from Git and why. Do not make scientific Git completion
depend on a pending external upload. The assistant never runs
`git add`, commit, or push;
those actions belong to the user. All local evidence remains intact unless
the user separately approves exact-target cleanup.

When one producer owns both candidate and diagnostic bulk evidence, do not
force both classes into one repository and do not leave either class local-only.
Use separate, explicitly named publication profiles and records. Notebook 22 is
the reference implementation: `22c` publishes 735 restorations to `candidates`;
`22d` publishes 245 overlays, the numeric uncertainty archive, and diagnostic
sidecars to `diagnostics`. Each profile uses 35 per-painting bundles and must
complete pinned remote verification before its record is included in Git.

## 28. Error correction workflow

When a final notebook has isolated issues, provide:

1. The affected cell number and heading.
2. The reason it fails or violates the contract.
3. A complete replacement cell.
4. The cells that must be rerun before it.
5. The cells that must be rerun after it.
6. Expected validation evidence after rerun.

When a helper has isolated issues, provide targeted changes. Replace the whole helper only when its API or structure is fundamentally incompatible with the approved design.

## 29. Completion gate

A notebook is complete only when all applicable checks pass:

- every approved responsibility is implemented;
- every required input exists and matches its schema;
- every required output exists and reloads successfully;
- expected row and file counts match;
- primary keys are unique;
- paths are repository-relative and valid;
- no writes occurred outside the notebook output root;
- stale/orphan detection passed or has documented approved exceptions;
- scientific invariants passed;
- visual QA was completed where applicable;
- run, artifact, and validation manifests are complete;
- the opening notebook metadata reads `Finished`, `Finished`, and `Yes` and agrees
  with the canonical run manifest;
- the human evidence dependency audit and machine-readable evidence-coverage
  registry record the completed notebook's validated evidence and limitations;
- project paths registry was updated;
- the completed output tree was compared with the read-only pre-scale copy at
  `E:/outputs/<notebook_stem>/`, and the artifact/count comparison table contains
  no unexplained missing or reduced evidence;
- inventory was refreshed after completion;
- limitations and deviations are documented;
- the notebook runs linearly from a clean kernel.

Only after this gate passes may the notebook become an approved upstream dependency.

## 30. Cleanup sequencing

Repository cleanup occurs only after this guideline and the detailed roadmap are accepted.

Recommended cleanup order:

1. Create a read-only cleanup inventory of legacy and current artifacts.
2. Classify each path as source input, notebook source, helper/configuration, authoritative artifact, reproducibility evidence, replaceable generated output, stale duplicate, or temporary material.
3. Preserve all source inputs, notebooks, helpers, configurations, documentation, Git metadata, and necessary deployment files.
4. Present the exact proposed deletion/migration list for approval.
5. Perform approved cleanup using exact resolved targets.
6. Refresh the inventory.
7. For a new approved notebook, create only its required preparation folders.
8. Let each notebook create its own output subfolders during execution.

### 30.1 Post-generation output closure audit

After the last dataset-generation, restoration, or metric-production notebook
needed by the remaining analytical stages has completed, perform another
read-only output audit before continuing. This audit must:

- compare every numbered notebook-owned output tree with its final artifact
  manifest and approved contract;
- identify legacy global `outputs/figures/`, `outputs/metrics/`,
  `outputs/reports/`, `outputs/manifests/`, and `outputs/validation/` trees;
- identify empty or replaceable `work/`, checkpoint, temporary, cache, and smoke-
  test material;
- preserve `outputs/inventory/` as the sole global output exception;
- preserve every declared canonical artifact and every upstream input required by
  future notebooks;
- present exact resolved deletion targets and file counts before deletion; and
- refresh the inventory after the user completes or explicitly authorizes the
  cleanup.

The audit is read-only by default. Do not delete legacy or temporary material
automatically merely because the pipeline has moved past its producing notebook.

Broad pre-creation of all 36 output trees is discouraged because it creates empty and misleading folders.

## 31. Completed Decision Notebook D01 and production HINT boundary

Decision Notebook D01 is the completed HINT-versus-MAT selection study that
preceded the controlled-300 rerun. These rules supplement, and do not replace,
the general implementation contract:

- D01 and its outputs remain frozen and read-only.
- D01 owns every HINT/MAT pilot candidate, metric, figure, report,
  manifest, validation record, checkpoint, and temporary file under
  `outputs/37_hint_mat_method_selection/`.
- The exact twelve-case population, two methods, adapters, source revisions,
  checkpoint identities, runtime guards, metrics, and decision rules are frozen
  in `config/experiments/hint_mat_selection.yaml` before Batch 1.
- Official HINT and MAT repositories and checkpoints remain external assets.
  Resolve them through the declared environment variables or configured local
  defaults; never vendor them, their caches, or their weights into this repo.
- External asset preflight must inspect paths, required source files, declared
  revision, checkpoint existence and checksum, and license. It must not import
  the models or allocate GPU memory.
- HINT must call the released generator directly rather than the repository's
  dataset/W&B test wrapper. MAT must invert the canonical missing-region mask to
  its official retained-pixel convention before inference.
- HINT attempts 768 × 768 first and may use only the declared 512 adapter after
  a recorded technical failure. MAT uses its declared 512 adapter. Both return
  to the 768 canvas and use exact canonical-mask compositing.
- Run model code in isolated workers. Record load time, inference time, total
  runtime, actual resolution, CUDA device, peak GPU memory, status, and failure.
  Persist progress after every case using the bounded Windows-safe atomic-write
  retry helper.
- The zero-control case is identity/no-op QA only; it must not be counted among
  the twelve comparison cases or twenty-four restoration candidates.
- Retain separate evidence families. Do not construct a combined score, run
  inferential tests on the small nested sample, or select a winner by a single
  metric.
- Batch 8 must show the complete paired visual scope, not only favorable
  representatives. Batch 9 must not write the final selection until the user has
  inspected the atlas and explicitly chosen HINT, MAT, or neither.
- HINT's operational preference is only a tie-break after both methods pass all
  technical, quality, runtime, and license gates. MAT's noncommercial license is
  a decision constraint, not a quality penalty hidden inside a numeric score.
- Notebook cells remain user-pasted and user-executed. Preparation work may edit
  configs, helpers, tests, and governing documentation, but must never insert or
  execute notebook cells directly.

Notebook 12A is the only production consumer of the D01 decision. It must use
the validated HINT source/checkpoint/adapter contract, generate one primary
candidate for every controlled-300 eligible case, and write only to
`outputs/12a_hint_restoration/`. It may cite D01's selection rationale but must
not copy pilot candidates into the production population or report the pilot's
12-case metrics as full-benchmark evidence.

After completion, update both evidence ledgers with observed counts, selected
method and limitations, set the notebook header to `Finished`, `Finished`, and
`Yes`, refresh `outputs/inventory/`, and commit the notebook, owned outputs,
governing files, and compact inventory run record together. The regenerated
`project_file_inventory.csv` remains local under the active LFS quota guard.

### 31.1 D01 completion record

D01 completed the exact 12-case, 24-candidate paired comparison. Both
methods passed the hard technical gates and all 94 consolidated validation
checks. HINT ran natively at 768 × 768; MAT used the declared 512 adapter and a
supported PyTorch fallback for its optional CUDA extension. HINT led 96 of 108
case-level metric anchors, MAT led 6, and 6 were ties. Complete visual review
favoured HINT, particularly because MAT often retained thin scratches and
produced pale or fragmented large-loss completions. HINT was selected.

The extension existed to add a missing capability, not simply another model
name. HINT provides a second deterministic learned architecture with mask-aware
transformer processing and multi-scale, long-range context. It complements the
tagged baseline's classical Telea, Fourier-convolution LaMa, and stochastic
prompt-conditioned Stable Diffusion families. MAT remains an auditable pilot
comparator; its 512 adapter and noncommercial licence also reduce its suitability
for the planned expanded benchmark.

This result does not alter the tagged 50-painting leaderboard or dashboard.
Future documentation may identify HINT as the selected expansion method only
when it also states that the evidence comes from a 12-case method-selection
pilot, not a completed fourth full-model benchmark.
