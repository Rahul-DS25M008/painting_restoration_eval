# Validation record

Work began from clean commit `19837d4a6376fcd1912404d8560591a4e0908358`.
This record describes local checks on the reporting-correction working tree;
it does not attest the deployed app or rewrite a historical N35/N36 check.
The containing Git commit identifies the completed correction source.

## Correction-specific checks

- Builder: 78 corrected thesis rows, 77 corrected statistical rows, four
  complete affected LaTeX tables, and a field-level mapping ledger generated.
- Saved scientific numerical fields preserved. CSV numeric input uses
  round-trip parsing to retain full stored floating-point precision.
- Eleven Friedman statistics, p-values and Kendall's W values independently
  reconstructed from the saved scalar measurements: all matched.
- All scientific input hashes were unchanged before/after the builder.
- SDXL: 35 scheduled cases/30 paintings; 24 technically validated completions/
  19 paintings; one timeout; ten skipped after the guard.
- Deterministic illustrative examples include both a changed interpretation
  and an unchanged winner, with sixteen exact measurement-row references each.
- Focused suite: **16 tests passed** (nine multi-model tests, seven errata
  tests), including current N33 producer construction from all 33 saved input
  tables and agreement with the corrected population/aggregation fields.
- Production candidate-selection validation was not weakened. A missing HINT
  source is tested as a blocking error; the fixture includes four core methods
  and the bounded fifth-method subset.
- No room layout, original scientific output, N33/N36 package, historical
  artifact manifest or published archive was changed.

Focused command:

```powershell
$env:PYTHONPATH = Join-Path $PWD 'src'
.\.venv\Scripts\python.exe -m unittest -v tests.test_reporting_errata tests.test_multi_model_comparison
```

## Complete-suite run and remaining limitations

Command: `python -m unittest discover -s tests -v` using the existing project
environment. The broad run during implementation executed **575 tests in
960.190 seconds**, reporting **eight failures, four errors and 28 skips**.
The new errata test module was added after that run's discovery and was checked
separately. This was not a fully green repository-wide validation.

Two implementation-time issues were addressed in subsequent focused runs:
the new missing-HINT negative test expected a later error rather than the
correct earlier candidate-count rejection; an optional Model Gallery tooltip
tripped the freeze gate and was removed completely. The gallery-specific freeze
test then passed. The broader freeze test still encounters the pre-existing
Research Archive mismatch described below.

The remaining failures/errors are outside the reviewed multi-model module and
are recorded rather than silently rebaselined:

| Test area | Observed issue | Disposition |
|---|---|---|
| N16 error maps | Version assertion expects 4.0.1; module is 4.1.0 | Existing assertion drift; unchanged |
| N17 local consistency | Version assertion expects 1.0.3; module is 1.1.0 | Existing assertion drift; unchanged |
| N17 local consistency population | Test expects 2,160 candidates; current worklist has 16,404 | Pilot-era population expectation; unchanged |
| Canonical mask representative selection | Expected `p050`; current selected painting is `p085` | Requires a separate selection-contract review; unchanged |
| Model Gallery historical N35 source hash | Fixed early notebook digest differs from the current saved N35 notebook | Existing source-hash expectation; not rebaselined |
| N20 semantic/structural | Expected 58,980 metric rows; current contract declares 447,312 | Pilot-era population expectation; unchanged |
| N19 spatial explanations | Expected module 1.0.1; current module 1.0.2 | Existing assertion drift; unchanged |
| Two N35 freeze tests | `research_archive.py` no longer matches the old backend-delta receipt after the separately approved publication/UI changes | Existing freeze-receipt mismatch; not concealed or rebaselined |
| HINT test-module import | Project environment has no `pytest` installed | Environment/test-runner gap; no package installation attempted |

The 28 skips include explicitly historical Controlled-50 tests and browser
checks skipped because Playwright is unavailable. Skipped tests are not passes.
The saved broad log is `.codex_tmp/review-full-tests.log`; the final focused
log is `.codex_tmp/review-focused-tests.log` (local ignored diagnostics).

Thus the approved reporting corrections and repaired multi-model tests are
validated, but **a clean full-suite claim remains unavailable**. None of the
remaining failures authorizes changing scientific evidence to fit old assertions.
The full suite was not rerun after the focused corrections; no inferred green
total is substituted for the actual run above.

## Inventory and Git

The canonical inventory is refreshed after the final file edits using
`python tools/build_project_inventory.py --root . --hash-mode partial`.
Its run identity, totals, errors and checksum are recorded in the committed
[`inventory_run.json`](../../../outputs/inventory/inventory_run.json).
The inventory describes local file identity, not scientific reproduction.
