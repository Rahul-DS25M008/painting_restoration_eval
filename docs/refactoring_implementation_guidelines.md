# Painting Restoration Thesis Refactoring and Implementation Guidelines

## 1. Document status

This document is the approved project-wide implementation contract for refactoring and extending the repository for the thesis:

**Trustworthy Evaluation Frameworks for AI-Assisted Painting Restoration**

It governs notebook design, helper modules, configuration, paths, generated artifacts, validation, manifests, reporting, dashboard preparation, reproducibility, and migration from the current repository layout.

The repository will be rebuilt from Notebook 01 onward. No existing notebook is treated as complete merely because it was previously refactored or executed successfully.

The central methodological boundary remains:

> Visual plausibility is not equivalent to historical correctness, conservation approval, or restoration trustworthiness.

## 2. Approved architectural decisions

The following decisions are approved:

1. The final pipeline uses the consolidated 35-notebook architecture documented in `docs/final_notebook_roadmap.md`.
2. Generated content will migrate from `data/processed/` and legacy global output folders into notebook-owned output folders.
3. `outputs/inventory/` is the sole global output exception.
4. Restoration notebooks remain model-specific.
5. Metric notebooks are model-agnostic and organized by evidence family.
6. Handoffs use normalized manifests joined by stable identifiers rather than progressively wider tables.
7. One canonical region helper defines every evaluation region used throughout the project.
8. Notebook 34 remains a separate dashboard and deployment validation stage.
9. Python 3.11 is the provisional default because it is recommended by `requirements_experiments.txt` and used in the README setup instructions. Python 3.12 may be adopted later only after compatibility is verified during execution.

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
4. The approved detailed notebook roadmap.
5. The approved notebook-specific batch and input/output contract.
6. Versioned configuration and schema definitions.
7. Validated upstream manifests.
8. The current project inventory.
9. Existing notebooks, helpers, reports, and generated outputs.

Existing code and outputs provide evidence about prior behavior. They do not override the approved design.

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

The workflow for every notebook is:

1. Refresh the project inventory.
2. Inspect the latest inventory, approved requirements, upstream manifests, current notebook, relevant helpers, and current configuration.
3. Determine whether helpers require no change, targeted changes, or complete replacement.
4. Define every planned cell batch before generating notebook code.
5. Define and approve the exact input/output contract before Batch 1 is generated.
6. The user creates the correctly numbered, named, and otherwise blank notebook.
7. Provide Batch 1 and every later batch as complete, separately labelled
   Markdown and code cells in chat for manual insertion, execution, and testing
   by the user.
8. Inspect the executed final notebook and generated artifacts.
9. Validate the notebook against the approved truth sources and input/output contract.
10. Provide targeted replacement cells or helper changes when issues are isolated.
11. Rerun the required cells and repeat validation.
12. Update the project paths registry only after the notebook passes its completion gate.
13. Refresh the project inventory again so the next notebook receives the validated state.

### 6.1 Manual notebook editing policy

- The assistant must not create, replace, patch, or otherwise edit an `.ipynb`
  file directly.
- The assistant must not insert Batch 1 or any later cells into a notebook file.
- Every proposed notebook cell, including a replacement for an erroneous cell,
  is delivered in chat as a complete cell for the user to copy and paste.
- Markdown cells and code cells are labelled separately and preserve the linear
  structure already established by the successfully refactored notebooks.
- The user alone executes notebook cells and saves the notebook.
- The assistant may read and inspect the user-saved notebook, its rendered
  outputs, and its generated files, but inspection does not authorize notebook
  modification or cell execution.
- Helper modules, configuration files, tests, documentation, inventory files,
  and project-path registries may still be edited when explicitly within the
  approved preparation or completion workflow.

#### 6.1.1 Mandatory opening Markdown contract cell

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

### 6.2 Notebooks that generate important reports

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
  evidence beyond traditional image similarity; conditional model behaviour
  across paintings, styles, damage geometries, and degradations; uncertainty and
  speculative restoration regions; transparent metric disagreement; and support
  for human conservation judgement rather than replacement of that judgement.
  Report emphasis must be adapted to the producing notebook while remaining
  visibly connected to these themes.
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
  score. A combined score is allowed only when its construction, scaling,
  weighting, interpretation, and limitations have already been methodologically
  justified and validated.
- Respect the statistical unit and dependency structure of the experiment.
  Candidate observations, repeated seeds, prompt variants, multiple cases from
  one painting, partial model coverage, and other repeated or nested observations
  must not be presented as independent evidence when they are not.
- State partial or unavailable experimental coverage explicitly. Do not imply
  full-dataset comparability when a model, metric, experiment, or analysis covers
  only a subset.
- State important limitations close enough to affected conclusions for correct
  interpretation. A short consolidated limitations section may also be included.

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
  policy in Section 6.1.
- Only after approval may the assistant generate report-implementation cells.
- If implementation later reveals that an approved section lacks validated
  evidence, or that a materially different structure is scientifically preferable,
  surface the issue and obtain approval rather than silently changing the report.

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
- a balanced rendered mixture of narrative, finding bullets, tables, plots,
  restorations or diagnostic images, captions, and scoped conclusions, without
  long avoidable text walls or unexplained visual galleries;
- clear separation between scientific validation failures and HTML/rendering
  failures.

The illustrative LaMa model-performance mock-up in
[`report_structure_mock_lama.md`](report_structure_mock_lama.md) is a design
reference for narrative quality and information density. It is not a mandatory
section template for model reports or for other report categories.

The inventory refresh is a controlled write operation. During explicitly read-only phases, the existing inventory may be inspected but must not be regenerated.

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

Generated content currently under `data/processed/` is legacy material. It remains read-only during migration until notebook-owned replacements are validated. It may be removed only during an explicitly approved cleanup stage.

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
    controlled_50.yaml
    expanded_main.yaml
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
controlled_50
expanded_main
```

Scaling from 50 paintings toward approximately 300 is an execution profile, not a duplicate notebook pipeline.

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

The registry must not contain temporary, failed, stale, or QA-only artifacts unless they are deliberately retained for audit.

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

Notebook status Markdown inherited from older files must be reset. A previous `Status: Complete` label is not accepted for the new refactoring cycle.

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

Python 3.11 is the provisional default.

Before final model reruns:

- reconcile conflicting package pins;
- verify model and CUDA compatibility;
- separate dashboard-only dependencies if necessary;
- record exact package versions;
- record Python, operating system, CPU, GPU, CUDA, and VRAM;
- record Git commit and dirty-state information;
- record configuration and helper checksums;
- record all relevant seeds and model revisions.

If Python 3.12 is adopted, the change must be documented with compatibility evidence and environment declarations must be updated consistently.

## 27. Version control and large artifacts

- Preserve existing user changes unless explicitly instructed otherwise.
- Do not commit environments, caches, notebook checkpoints, replaceable temporary files, or unnecessary logs.
- Generated images under notebook-owned `outputs/` are covered by existing Git LFS patterns.
- After migration, no authoritative generated images should remain under `data/processed/`.
- Standalone HTML reports may embed declared web-sized figures and
  representative images so the report remains usable when downloaded alone.
  Avoid embedding unrestricted full-resolution collections, and register the
  canonical source artifacts and checksums used to construct each embedded
  display image.
- Notebook sizes should remain reviewable; very large embedded outputs must be reduced.

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
- project paths registry was updated;
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
7. Create only foundational folders required before Notebook 01.
8. Let each notebook create its own output subfolders during execution.

Broad pre-creation of all 35 output trees is discouraged because it creates empty and misleading folders.
