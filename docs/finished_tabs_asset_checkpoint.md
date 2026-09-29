# Finished tabs 01-03: assets-only checkpoint

Scope: Exhibition Foyer, Study Design, Metric Framework. This is **not N35
completion**, an application-code checkpoint, remote-loader integration, or a
Streamlit deployment. Do not run any notebook. The existing pilot branch is
`pilot-50-dashboard`; only GitHub `main` is pushed below.

## Storage split

- Ordinary Git: three room shells, four ornaments, five Study Design PNGs
  (12 files, about 10 MiB), publication helper/tests/instructions and the verified
  HF receipt. Explicit `.gitattributes` rules bypass Git LFS for this artwork.
- HF diagnostics dataset: 300 painting packages, each with 36 display PNGs,
  one manifest and a numeric archive (11,400 files, about 1.24 GiB). Each painting
  gets separate display/archive ZIPs plus an index; 901 remote objects total.
  Numeric archives are preserved but need not be loaded to display a painting.
- Previously committed N34 assets and previously published canonical producer
  evidence stay in their existing locations. They are not duplicated here.
- No application Python/JavaScript, notebook, N35 output, inventory changes,
  unrelated documentation changes, or secrets are included.

HF uses a new content-addressed prefix under
`dashboard_assets/v1/finished_tabs_01_03/` in
`RahulMaddineni264/painting-restoration-eval-diagnostics`. No old release is
overwritten or deleted. HF may internally use large-file storage; these commands
do not use **GitHub Git LFS** or consume its exhausted allowance.

The release is already fully uploaded at HF revision
`7814540a3fd3bff7db166c35821f18d5023d4d35`. Do not upload it again.
On 2026-09-30 the user approved a metadata-verified checkpoint without requiring
full public re-downloads. All staged bytes are checked against the locally
validated plan, then all remote paths, sizes and HF SHA-256/Git blob identities
are matched at that immutable revision. This does not claim an end-to-end
download test or hosted Streamlit test. Expanded tree metadata is disabled.

The commands below document the original preparation workflow; for this existing
upload, start at the `verify-remote --metadata-only` command in section 2.
Future checkpoints should group multiple paintings into approximately 32-MiB
packages and consolidate indexes, rather than repeat this 901-object layout.
Do not repack or replace this already uploaded immutable release.
Canonical local files are never deleted, moved, repaired, or regenerated.

## Run in PowerShell, in order

Use the same terminal for all blocks. `Run-Checked` stops on native-command
failure. If anything fails, stop and inspect it; do not proceed to commit/push.
Do not use `git add .`, `git add -A`, `git commit -a`, or force push.

### 1. Preflight and local verification

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
if ((Run-Checked git branch --show-current) -ne 'main') { throw 'Stop: not on main.' }
if (Run-Checked git diff --cached --name-only) { throw 'Stop: index already contains staged work.' }
Run-Checked git status --short
$remoteBefore = @(Run-Checked git ls-remote --heads origin main pilot-50-dashboard)
$mainLine = @($remoteBefore | Where-Object { $_ -match 'refs/heads/main$' })
$pilotLine = @($remoteBefore | Where-Object { $_ -match 'refs/heads/pilot-50-dashboard$' })
if ($mainLine.Count -ne 1 -or $pilotLine.Count -ne 1) { throw 'Expected branches not found.' }
$remoteMainBefore = ($mainLine[0] -split '\s+')[0]
$pilotBefore = ($pilotLine[0] -split '\s+')[0]
if ((Run-Checked git rev-parse HEAD) -ne $remoteMainBefore) {
    throw 'Local HEAD differs from remote main. Stop and inspect; do not automatically pull/reset.'
}
Run-Checked $py -c "from huggingface_hub import HfApi; print('HF account:', HfApi().whoami()['name'])"
Run-Checked $py -m unittest tests.test_finished_tab_publication tests.test_bundled_assets
Run-Checked $py tools/audit_metric_inspection.py --require-count 300 --report .codex_tmp/finished_tabs_scientific_audit.json
Run-Checked $py tools/publish_finished_tab_assets.py prepare
Run-Checked $py tools/publish_finished_tab_assets.py verify-local
```

Expected scientific audit: `count: 300`, `passed: 300`. Publication preparation
must report 901 HF objects and 12 ordinary-Git assets. This audit reads evidence;
it does not invoke N35 or change its notebook/outputs. Do **not** add `--repair-seam`.

The existing environment has `huggingface_hub 0.25.2`; no upgrade is necessary.
If authentication is missing, run the following interactively (never paste a
token into a command, script, chat, or Git file), then retry the identity check:

```powershell
Run-Checked $py -c "from huggingface_hub import login; login(add_to_git_credential=False)"
```

### 2. Verify the existing upload without downloading it again

```powershell
Run-Checked $py tools/publish_finished_tab_assets.py verify-remote --metadata-only
Get-Content config/publication/finished_tabs_01_03_assets.json
```

Success requires `status: remote_metadata_verified`, 300 paintings, 11,400 source
files, 901 objects and a full 40-character HF revision. The receipt explicitly
records `full_public_download_verification: deferred_by_user`. ZIP member bytes
were checked against source files before upload. Only successful content-identity
verification writes the receipt; missing files or differing hashes still block it.

Optional later: omit `--metadata-only` for the full public-download test. That
mode keeps verified files cached, retries only a failed download with bounded
backoff, and records `public_bytes_verified` only when the entire test passes.
Allow an additional approximately 1.3 GiB of bandwidth and scratch space for it.

On a timeout, rate limit or interrupted upload: wait as appropriate and rerun
the failed command. Upload rechecks remote hashes and only sends missing objects;
verification resumes from hash-checked download cache. Do not delete scratch,
change the release prefix, or manually overwrite remote files to work around an
error. If local assets change, rerun `prepare` for a new content-addressed release.

### 3. Stage only this checkpoint and review it

```powershell
if (Run-Checked git diff --cached --name-only) { throw 'Stop: unexpected staged work.' }
$assetPaths = @(Run-Checked $py tools/publish_finished_tab_assets.py git-paths)
Run-Checked git add -- @assetPaths
Run-Checked $py tools/publish_finished_tab_assets.py check-git
Run-Checked git diff --cached --check
Run-Checked git diff --cached --stat
Run-Checked git diff --cached --name-only
Run-Checked git diff --cached -- .gitignore .gitattributes config/publication/finished_tabs_01_03_assets.json
```

The guard requires **exactly 18 files**: the 12 art assets, two Git policy files,
helper, helper tests, this document and the HF receipt. It rejects any extra file,
LFS pointer/filter, oversized file, or artwork byte mismatch. There must be no
`notebooks/`, `outputs/35_*`, application code, or bulk evidence in the staged set.
Existing unstaged changes will remain visible in `git status`; that is expected.

### 4. Commit and push only main

Run this only after reviewing the preceding staged diff:

```powershell
Run-Checked $py tools/publish_finished_tab_assets.py check-git
Run-Checked git commit -m 'Checkpoint finished tabs 01-03 artwork and verified HF assets'
$checkpoint = Run-Checked git rev-parse HEAD
Run-Checked git show --stat --oneline HEAD
Run-Checked git push origin main:main
$remoteAfter = @(Run-Checked git ls-remote --heads origin main pilot-50-dashboard)
$mainAfterLine = @($remoteAfter | Where-Object { $_ -match 'refs/heads/main$' })
$pilotAfterLine = @($remoteAfter | Where-Object { $_ -match 'refs/heads/pilot-50-dashboard$' })
if ($mainAfterLine.Count -ne 1 -or $pilotAfterLine.Count -ne 1) { throw 'Remote branch verification failed.' }
$remoteMainAfter = ($mainAfterLine[0] -split '\s+')[0]
$pilotAfter = ($pilotAfterLine[0] -split '\s+')[0]
if ($remoteMainAfter -ne $checkpoint) { throw 'Remote main does not match checkpoint.' }
if ($pilotAfter -ne $pilotBefore) { throw 'Pilot branch changed; investigate before continuing.' }
Write-Host "Verified GitHub main: $checkpoint"
Write-Host "Pilot branch unchanged: $pilotAfter"
Run-Checked git status --short
```

Git's object hashes verify the pushed commit and its content when the remote ref
matches. Share the HF receipt summary, checkpoint SHA and final status before
starting the next tab. No Streamlit app is created or tested in this sequence.
