# Post-notebook dashboard addition: numerical metrics

Approved scope (2026-09-04): add exact numerical evidence to Case Explorer and
Model Performance while preserving all other page functions and existing layouts.
This is an application-only, read-only extension. It creates no scientific
outputs and does not require editing or rerunning any notebook.

The user verified and approved the numerical additions on 2026-09-04 and
confirmed the public deployment at https://fhtw-painting-restoration.streamlit.app/.
The only subsequent Reports & Reproducibility change replaces its outdated
not-deployed note with that clickable public URL. Historical notebook outputs
are not rewritten to describe this later deployment state.

## Input contract

The fixed Notebook 34 `case_index.csv` is the candidate allow-list. The new
`src/restoration_eval/dashboard_metrics.py` reads only these explicit sources:

| View | Producer-owned metric table |
|---|---|
| Classical | `outputs/13_classical_metrics/metrics/classical_metrics.csv` |
| LPIPS | `outputs/14_lpips_metrics/metrics/lpips_metrics.csv` |
| Feature similarity | `outputs/15_feature_similarity/metrics/feature_metrics.csv` |
| Colour, seam and texture | `outputs/17_local_consistency_metrics/metrics/local_consistency.csv` |
| Semantic and structural | `outputs/20_semantic_and_structural_consistency/metrics/semantic_structural_metrics.csv` |

Exact diffusion seeds and prompt variants come from the `data/candidates.csv`
tables owned by Notebooks 11, 12, and 22. Each source is checked against its
producer's `manifests/artifacts.csv` SHA-256 before use. No arbitrary directory
scan selects input files. Source changes invalidate the bounded application cache.

Model Performance uses the existing Notebook 34 `performance_summary.csv` rows
already selected for the chart. No aggregate estimates or intervals are computed.

## Display contract

- Case Explorer adds a numeric section below its existing diagnostic-image tabs.
- Its independent controls select metric source, model(s), selected-candidate or
  same-case scope, region, measure, seed, and prompt arm.
- A row represents one original source observation, not a pooled model score.
- Identity joins use case ID, candidate ID and model ID with checked cardinality.
  Painting, seed, prompt, source record ID and source path remain traceable.
- Damaged, restored and improvement values are displayed with their direction,
  units and applicability/status. Additional descriptor, statistic and semantic
  target fields distinguish multiple observations; no pivot averages duplicates.
- Not-applicable records are retained, not converted to zero. Some producers
  retain diagnostic numbers under a not-applicable status; these are explicitly
  labelled "do not rank". Infinite PSNR is not silently replaced or discarded.
- The 105 N22 additional-seed candidates have no individual reference-quality
  rows in these tables. They retain group uncertainty evidence. The application
  lists them without borrowing their seed-2026 anchor's metric values.
- CSV downloads include all currently filtered rows and their source provenance.
  Numeric display rounding does not impose matching rounding on CSV exports.
- Model Performance adds a collapsed table directly before the existing image
  comparison. It exposes the chart's estimates, intervals, direction, rank,
  denominators, applicability, scope and source paths, with a CSV download.
- Large metric tables are read in chunks; only bounded per-case slices are cached.

## Historical notebook records

Notebooks 01–36, all notebook-owned outputs, N34's fixed package, N35's historical
validation record, and N36's copied application snapshot remain unchanged.
N35 and N36 describe the versions they tested or packaged, not this later UI
addition. Verify this change through the application tests and subsequent manual
review; do not silently rewrite frozen manifests to claim they tested new code.

The root README now includes the approved dashboard overview, numerical-metrics
features, live deployment link, and report navigation. The temporary approved draft
was removed after promotion.

## Verification

`tests/test_dashboard_metrics.py` checks exact source-value preservation, the
candidate allow-list, seed/prompt identity, missing extension scores, duplicate
identity rejection, non-applicability/infinity, unchanged aggregate values, and
unchanged existing functions outside the two approved pages. Streamlit in-process
tests additionally exercise the new controls and the existing page routes.
