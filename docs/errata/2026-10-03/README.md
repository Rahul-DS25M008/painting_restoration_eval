# Controlled-300 post-publication reporting errata

Correction version: **2026-10-03.v1**. Applies to the original
[Zenodo v1.0.0 release, DOI 10.5281/zenodo.23092185](https://doi.org/10.5281/zenodo.23092185),
archived source commit `2378961a8accb2ecde610ed60428879e8f52a8a8`, and the frozen
N26/N33/N36 reporting copies in this repository. These corrections supersede
the affected labels below, not the archived metric measurements or test results.

The original files, manifests, execution outputs and archive remain unchanged.
No model was rerun. This is a separately identified reporting overlay, not a new
scientific run, independent end-to-end reproduction, or a claim that Zenodo's
downloaded files already contain these corrections.

## E01 — T04/T05 populations and weighting

N33 T04 used the registry's `population_case_count` in every denominator, and
T04/T05 used a blanket nonzero scope. The source N21 rows distinguish:

| Anchors | Registry coverage | Measured paired cases | Controls | Paintings | Aggregation |
|---|---:|---:|---|---:|---|
| Ten anchors other than structural affinity | 2,620 | 2,320 | Excluded | 300 | Case-weighted mean of applicable paired values |
| Content-region structural-affinity correlation | 2,620 | 2,620 | 300 identity controls included | 300 | Case-weighted mean of applicable paired values |

These are not equal-painting means. Extension paintings contribute additional
cases. T05 orders the same anchor-specific means. The correction covers all
44 T04 and eleven T05 rows, retains the means/ranks/winners, and explicitly
states the descriptive aggregation unit rather than implying a painting-balanced
estimator. The legacy identifier `core_three_model` still denotes the four
Controlled-300 core methods; it is retained for schema compatibility.

## E02 — N26 and T10 statistical populations

The N26 export's `canonical_only` set omitted `repeated_model_test` and
`paired_model_contrast`. Consequently, eleven omnibus and 66 paired-contrast
rows incorrectly reported `all_primary_experiments`, `all_nonzero_primary_core`
and 2,320 cases. Their computations actually used canonical-only observations.

**Friedman tests and paired contrasts:** 1,200 `canonical_missing_region`
nonzero cases, comprising `loss_large`, `loss_small`, `mixed_damage` and
`scratch_thin` for every painting. For each anchor and method, take the median
of the four direction-adjusted case values within each painting. The Friedman
input is a 300 × 4 matrix: one row per equally weighted painting and one column
per method (Telea, LaMa, HINT, primary generic-prompt Stable Diffusion seed 2026).
Paired contrasts subtract two method columns. Identity controls, extensions,
other prompt/seed variants and SDXL do not enter this population.

**Quality/runtime associations:** retain the original all-branch population of
2,320 nonzero cases: 1,200 canonical, 245 damage-size, 525 mask-robustness and 350
eligible synthetic-degradation cases. Quality and runtime are separately reduced
to medians within each painting/model, then correlated across 300 equally weighted
paintings per method. The extension paintings have more constituent cases.
T10's eleven runtime rows summarize 44 model-specific associations and must not
be relabeled canonical-only.

All eleven Friedman statistics, p-values and Kendall's W values were recomputed
from the saved scalar measurements and matched the saved results within numerical
tolerance. W ranges from approximately 0.6923 to 0.8189. The existing q-values
are preserved, not independently recalculated. The 66 paired contrast/bootstrap
procedures and 44 runtime correlations were traced to their source code but not
rerun in this correction. See [verification details](statistical_verification.json).

The notebook export source and current N33 producer are corrected for future
execution. Saved notebook outputs remain the original run and are explicitly
identified as such; no execution count or historical run manifest was rewritten.

## E03 — SDXL scheduled versus completed coverage

SDXL had a predeclared schedule of **35 cases across 30 paintings**.
**Twenty-four cases across 19 paintings completed and passed technical validation**;
one case timed out and ten were not started after the budget/timeout guard.
SDXL provides bounded feasibility evidence, not a fifth full benchmark ranking.
The eleven noncompleted cases are not image-quality failures.

The original N33/N36 limitations prose incorrectly attached “across 30 paintings”
to the 24 completed candidates. This correction also applies wherever that
limitation was copied into reports, tables, package copies or captions. The
original N33 row is `thesis_574b0fe3ee854259e97ac0a4` (T15, limitation 06).
Scheduled/completed counts and technical-validation statuses were checked
against N12's candidate table. No SDXL status or measurement has changed.

## Clarifications accompanying the corrections

- LaMa's ten wins among eleven saved anchors correspond to **nine wins among
  ten distinct scalar quantities**, because masked MAE and mean masked spatial
  error are equivalent scalars. Telea leads crop SSIM. Distinct quantities can
  still correlate; this is not a new ranking analysis or independent voting.
- The [provenance-exception ledger](../../provenance_exceptions.md) retains the
  N29 manifest discrepancy, N35 source mismatch and deployment warnings, and
  the limited reproduction scope of N36. None is silently closed here.
- The [framework evidence chain](../../framework_evidence_chain.md) gives an
  aggregate ablation, a case-level metric disagreement and an unchanged-winner
  counterexample, with deterministic selection rules and exact source rows.
- Dataset balance is operational, not cultural/chronological/geographic or
  conservation-condition representativeness. Cleveland (109), the Met (55)
  and SMK (44) supply 208/300 paintings (69.3%); style/period is absent for 32.
  Synthetic damage supports controlled reference evaluation, not general
  conservation validity. See [methodology](../../methodology_notes.md).

## Corrected exports and how to use them

| File | Contents |
|---|---|
| [corrected_thesis_rows.csv](corrected_thesis_rows.csv) | 78 replacements: T04 (44), T05 (11), T10 (22), T15 (one SDXL limitation) |
| [corrected_statistical_rows.csv](corrected_statistical_rows.csv) | 77 N26 rows with corrected population metadata; numeric results unchanged |
| [corrected_latex_tables.csv](corrected_latex_tables.csv) | Four affected tables, including all 18 T15 limitations; population/aggregation column made explicit |
| [correction_ledger.csv](correction_ledger.csv) | Field-level old/new values and original-to-corrected row IDs |
| [statistical_verification.json](statistical_verification.json) | Eleven saved-metric Friedman verification results |
| [framework_examples.json](framework_examples.json) | Exact candidate IDs, source row IDs, values and selection rules for the examples |
| [verification.json](verification.json) | Input/output SHA-256 hashes and correction counts |

For an affected row, use the replacement identified by the ledger's
`original_row_id`; do not append it as an additional observation. Corrected
row IDs have the prefix `errata_20261003__`. Unaffected original rows remain
valid as recorded. The LaTeX export includes complete replacement tables, not
only the changed cells. This overlay should accompany any use of the frozen
final reports, N36 package copies or supervisor PDF snapshots.

Regenerate and check locally (requires the existing saved source tables and
the project's pandas/NumPy/SciPy/PyYAML environment):

```powershell
$env:PYTHONPATH = Join-Path $PWD 'src'
.\.venv\Scripts\python.exe tools/build_reporting_errata.py
.\.venv\Scripts\python.exe -m unittest -v tests.test_reporting_errata tests.test_multi_model_comparison
```

The builder is bounded to this errata directory, hashes its scientific inputs
before/after verification, and refuses unexpected counts or altered statistical
results. It does not update the frozen manifests or published release.

## Validation and publication status

The completed check outcomes are recorded in [validation.md](validation.md).
These repository corrections require a Git push to become publicly accessible.
Adding the commit-pinned errata link to the existing Zenodo description is an
owner action, not performed by the build or commit. No new DOI or archive upload
is necessary for this explicit reporting-correction approach.
