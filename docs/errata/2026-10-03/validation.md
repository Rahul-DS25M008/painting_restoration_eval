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

## Full-suite repair and current validation

The first broad run during implementation reported 575 tests, eight failures,
four errors and 28 skips. It was not green and is retained as a historical
diagnostic, not the final acceptance result. The owner requested resolution
before any Zenodo metadata handoff.

The follow-up corrects validation code and its environment, not scientific data:

| Area | Repair |
|---|---|
| N16 error maps | Pin current module 4.1.0 and Controlled-300's 143,247 diagnostic rows |
| N17 local consistency | Pin module 1.1.0, 16,404 candidates, 2,060,667 metric rows, 9,304 map candidates and 27,926 manifest rows; retain real-source worklist/arithmetic checks |
| Canonical masks | Verify nearest-median selection, declared tie-break order and shuffled-input invariance instead of a Pilot-50 painting ID |
| Model Gallery | Check actual notebook bytes before/after a gallery request instead of an early-N35 digest; historical source mismatch remains disclosed |
| N19 spatial explanations | Pin module 1.0.2 and the current 2,481-file contract |
| N20 semantic/structural | Pin 447,312 rows, 72,520 map records and 9,311 canonical files |
| N35 freeze verification | Preserve original freezes and backend receipt; separately verify exact previously approved publication/portrait changes and the current test-only correction |
| HINT discovery | Install pytest and include all five existing HINT functions in unittest discovery (import success alone did not execute them) |
| Browser fixtures | Install workflow-matched Playwright 1.62.0 and its Chromium; execute all 13 previously skipped local browser tests |
| Local web dependency drift | Restore repository-pinned Streamlit 1.56.0 instead of the locally installed 1.59.0, retaining IOPaint's FastAPI 0.108.0/Gradio 4.21.0 pins; verify dependency consistency and rerun affected tests |

Counts were checked against the current Controlled-300 configuration contracts;
the N17 integration test independently builds its population from saved source
tables. No saved output was changed to satisfy an assertion.

The two new receipts are
[`research_archive_publication_delta.json`](../../../config/publication/research_archive_publication_delta.json)
and [`n35_validation_delta.json`](../../../config/publication/n35_validation_delta.json).
The Archive receipt traces the exact changes between archived source
`2378961a8accb2ecde610ed60428879e8f52a8a8` and owner-approved
`19837d4a6376fcd1912404d8560591a4e0908358`. It also pins the three portraits,
their notice and the Zenodo publication receipt. Negative regression tests reject
modified current sources, corrupt preimages and altered assets. The separate
test-only receipt cannot normalize application code. These are later validation
records, not rewritten historical N35 results.

Complete-suite result: **594 discovered, 579 passed, 15 explicitly retired tests
skipped; zero failures and zero errors**, in 955.391 seconds. This run used the
existing Streamlit 1.59.0 process. The subsequent environment alignment restores
the repository's 1.56.0 pin; its affected-test rerun is recorded below rather than
misrepresenting the earlier run as having used that version.

Post-alignment affected-test result: **228 passed, zero skips, failures or errors**,
in 79.919 seconds. This reran dashboard/application, all affected room and N35
checks, browser fixtures, LaMa/HINT adapter checks, and exact-delta rejection
tests under Streamlit 1.56.0. The final N35 fingerprint also includes both new
delta receipts, so editing a receipt invalidates a validation checkpoint.
`python -m pip check` now reports **No broken requirements found**.
The focused repair run passed **59 checks**. All **six JavaScript controller
test files passed** (18 Node-reported tests, including two file-level assertion
scripts). These browser checks use local HTML fixtures, not the live deployment.

The 15 intentionally retired tests are eight Pilot-50 dashboard integration tests
(superseded by Controlled-300 dashboard/room tests) and seven SDXL v1 feasibility
tests (superseded by the active partial-feasibility tests in the same module).
They remain explicit skips, not passes. Missing packages or browsers are not
accepted as an explanation for any other skip.

Reproduce in the existing Python 3.12 experiment environment with saved evidence
available locally (the dashboard-only requirements are not sufficient):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements_test.txt
.\.venv\Scripts\python.exe -m playwright install chromium
$env:PYTHONPATH = Join-Path $PWD 'src'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

For this already-mixed local environment, dependency repair additionally restores
`fastapi==0.108.0` and `gradio==4.21.0`, as required by retained `iopaint==1.6.0`.
The resolver selects Starlette 0.32.0.post1 and websockets 11.0.3. A trial upgrade
of FastAPI/Gradio revealed IOPaint's exact pins and was reversed; those upgrades
are not the accepted environment. Deployment `requirements.txt` and scientific
package versions remain unchanged. This is dependency consistency, not a security
audit or reconstruction of every historical notebook environment.

Run each `tests/*.cjs` file with `node --test` as well. The local ignored logs
are `.codex_tmp/review-final-full-tests.log`,
`.codex_tmp/review-final-runtime-tests.log` and
`.codex_tmp/review-repair-focused.log`. Historical N29/N35 provenance exceptions
remain in [the exception ledger](../../provenance_exceptions.md); a successful
current regression run cannot retrospectively establish executed notebook bytes.

## Inventory and Git

The canonical inventory is refreshed after the final file edits using
`python tools/build_project_inventory.py --root . --hash-mode partial`.
Its run identity, totals, errors and checksum are recorded in the committed
[`inventory_run.json`](../../../outputs/inventory/inventory_run.json).
The inventory describes local file identity, not scientific reproduction.
