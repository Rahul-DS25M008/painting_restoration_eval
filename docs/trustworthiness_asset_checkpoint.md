# Tab 6 — approved Trustworthiness freeze and commit guide

User-approved visual/source freeze, 2026-09-30. Final reference screenshot:
`dashboard_design_finalists/trustworthiness_cosmetic_pass_09.png`.

This follows the isolated Tab 4/5 checkpoint approach: approved Trustworthiness
adapter, renderer, CSS/controller, five artwork assets (including the retained
pre-selfie source), three tests, design/provenance notes, final screenshot, and
fingerprint guard. Intermediate screenshots stay local and are not staged.

## GitHub versus Hugging Face

**GitHub only for this checkpoint. No HF upload, re-bundling, or Git LFS.**
Each artwork file is under 3 MiB and `streamlit_assets/rooms/*` explicitly disables
LFS filtering. No scientific producer output was created or changed by this freeze.

The existing publication ledger records these bulk tables as `published_verified`
and `verified` in `RahulMaddineni264/painting-restoration-eval-diagnostics`:

| Existing table | Recorded publication commit |
| --- | --- |
| N27 `failure_assignments.csv` | `b93ae7f15d6149087cf09ba483feebbd1a52f45d` |
| N27 `trustworthiness_flags.csv` | `b93ae7f15d6149087cf09ba483feebbd1a52f45d` |
| N28 `flag_stability.csv` | `57a6bd5b10f60d333dcb18bd48e1c942a28d33b9` |

These are local ledger observations, not a fresh remote download audit. Existing
candidate images and prior immutable bundles are reused; this source/artwork
checkpoint introduces no new scientific image population to publish.

## Boundaries and checks

- Local base HEAD: `d685601c0b5aac4c805b72ba91462faa4b3916ea`, branch `main`.
- The staging index was empty at preparation. Nothing was staged, committed,
  pushed, or uploaded by the assistant.
- Seven presentation tests passed during the final visual pass. This freeze
  uses lightweight content/fingerprint and chart checks, not a costly corpus run.
- The existing Tab 5 freeze still matches. Earlier scientific checks remain
  documented in `dashboard_design_finalists/trustworthiness_step03_verification.md`;
  they are historical results, not rerun for this freeze.
- Do not include dirty shared `streamlit_app.py`, `dashboard_application.py`,
  shared tests/config, metric-framework work, notebooks, inventory or outputs.
  They contain unrelated unfinished changes. N35 was not edited or executed here.
- Shared route wiring stays local for a later consolidated app checkpoint.
  This commit does not activate the tab on the hosted pilot. The current adapter
  still reads local producer tables/images; a pinned remote resolver, compact
  loading and hosted smoke test remain deployment work.
- Focused Portrait Review remains the existing placeholder route. Its link
  works; the separate subpage is not part of this completed main-room freeze.

## PowerShell commands — run in order

These guards are quick fingerprint/staged-file checks, not optional scientific
reruns. Stop on any failure. Do not use `git add .`, `git add -A`, `git commit -a`,
force push, or upload commands. Do not automatically pull/reset a dirty workspace.

### 1. Guard, check remote baseline, and stage this checkpoint only

```powershell
Set-Location 'D:\Masters\FH\Thesis\painting-restoration-eval'
$ErrorActionPreference = 'Stop'
$py = '.\.venv\Scripts\python.exe'
function Run-Checked {
    param([Parameter(Mandatory=$true)][string]$Exe,
          [Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Exe failed with exit code $LASTEXITCODE" }
}
Run-Checked $py tools/check_trustworthiness_freeze.py verify-local
$remoteMain = @(Run-Checked git ls-remote --heads origin main)
if ($remoteMain.Count -ne 1) { throw 'Expected exactly one remote main.' }
if ((Run-Checked git rev-parse HEAD) -ne ($remoteMain[0] -split '\s+')[0]) {
    throw 'HEAD differs from remote main. Stop; do not automatically pull or reset.'
}
$tab6Paths = @(Run-Checked $py tools/check_trustworthiness_freeze.py git-paths)
Run-Checked git add -- @tab6Paths
Run-Checked $py tools/check_trustworthiness_freeze.py verify-staged
Run-Checked git diff --cached --check
Run-Checked git diff --cached --stat
Run-Checked git diff --cached --name-only
```

Review the displayed file list. It must contain only the manifest's allowlist,
not any shared app, notebook or output changes.

### 2. Commit and push main only

```powershell
Run-Checked $py tools/check_trustworthiness_freeze.py verify-staged
Run-Checked git commit -m 'Freeze approved Trustworthiness artwork and isolated presentation source'
$tab6Commit = Run-Checked git rev-parse HEAD
Run-Checked git push origin main:main
$remoteAfter = @(Run-Checked git ls-remote --heads origin main)
if ($remoteAfter.Count -ne 1 -or ($remoteAfter[0] -split '\s+')[0] -ne $tab6Commit) {
    throw 'Remote main does not match the checkpoint commit.'
}
Write-Host "Verified Trustworthiness GitHub checkpoint: $tab6Commit"
Run-Checked git status --short
```

Unrelated unstaged/untracked work remaining is expected. No pilot branch is pushed.
If commit succeeds but push fails, do not commit again; resolve the push issue.
Share the final SHA/output, then proceed to Case Explorer. Keep the approved
Trustworthiness files untouched unless an explicit follow-up requests changes.
