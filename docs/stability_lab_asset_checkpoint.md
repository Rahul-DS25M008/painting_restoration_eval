# Tab 5 — approved Stability Lab freeze and commit guide

The user-approved room and popup design is frozen. This is an **isolated
24-file source/artwork checkpoint**, following the Tab 4 approach, not a
whole-app deployment or N35 completion claim.

## Verification and storage

- Local HEAD and live GitHub main at preparation: `a2bf09e882a6f9f203105875af75c179e1d070de`.
- Pilot branch unchanged: `125ea5653026ca5a17ccd991f8ef2d1f1363b62d`.
- 60 tests passed: Stability Lab 13, Gallery 11, shared dashboard adapter 28,
  indexed bundle transport 8. Controller JavaScript syntax passes.
- The previous 17-file Gallery freeze still matches. N35 was not executed or
  edited. Its current hash remains `77dbfb840b22dd590321fe11f75c8e926dbc85f02dcb797bd8bfacafb1d7b673`.
- All 12,080 distinct Tab 5 scientific image paths are accounted for: 9,980
  tracked by Git, 1,120 in verified individual HF records, and 980 in pinned HF
  bundle indexes. This is complete path coverage, not a fresh full-corpus
  download of every image. Source-table coverage is in the audit JSON.
- Live pinned N22 member-index checks and candidate/diagnostic sample reads
  reproduced local original SHA-256 hashes. N16/N22 table bytes also match
  their pinned release metadata. The public reader supports cache reuse.
- The new decorative shell is 2,167,163 bytes (about 2.07 MiB), ordinary Git,
  not Git LFS. Typography, book emblems and popup decoration are code-native;
  they introduce no external font or asset dependencies.

**HF action: none. Do not upload or re-bundle existing assets.** The N22 assets
already use 35 candidate ZIPs (735 members) and 35 diagnostic ZIPs (245 members),
with a 32-MiB bundle cap. Their pins are recorded in
`config/publication/stability_lab_publication_audit.json`. Existing N16 bundles
and individual HF tables/images remain valid; no duplicate release is needed.

Bundling preserves Streamlit compatibility: resolve an immutable catalogue,
fetch the required painting bundle into a bounded cache, verify the bundle and
member hashes, and decode the original member bytes. The existing
`RemoteBundleReader` implements this transport and its tests pass.

**Important deployment boundary:** the finished Tab 5 adapter still uses local
source paths and scans the N13/N16/N18/N22 tables. Its lazy pinned HF resolver
and compact metric lookups are not wired into the room yet. A fresh Git clone
alone therefore is not a tested cloud deployment. Keep all local evidence.
Do not delete assets or run an LFS migration. Cloud integration and an actual
hosted smoke test remain a separate explicitly authorized task.

## What this commit includes and excludes

Includes the isolated adapter/renderer, CSS/controller, shell, tests and audit
tools; the freeze manifest and publication audit; design notes and final room
and popup screenshots. All 24 paths are explicitly allowlisted and checked for
hash changes, file-size limits and forbidden Git LFS filters/pointers.

Excludes the already-dirty shared `streamlit_app.py`, dashboard adapters,
metric-framework work, notebooks and outputs. As with Tab 4, shared wiring
remains local for the later consolidated application checkpoint. Committing
the entire shared entrypoint now would also include unrelated unfinished work.
This checkpoint does not activate Tab 5 on the hosted pilot branch.

## PowerShell — run yourself, in order

Stop on any failure. Do not use `git add .`, `git add -A`, `git commit -a`,
force push, or HF upload commands. The staging index was empty at preparation.

### 1. Verify and check the remote baseline

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
Run-Checked $py tools/check_stability_lab_freeze.py verify-local
Run-Checked $py tools/check_model_gallery_freeze.py verify-local
$before = @(Run-Checked git ls-remote --heads origin main pilot-50-dashboard)
$mainLine = @($before | Where-Object { $_ -match 'refs/heads/main$' })
$pilotLine = @($before | Where-Object { $_ -match 'refs/heads/pilot-50-dashboard$' })
if ($mainLine.Count -ne 1 -or $pilotLine.Count -ne 1) { throw 'Expected branches missing.' }
$mainBefore = ($mainLine[0] -split '\s+')[0]
$pilotBefore = ($pilotLine[0] -split '\s+')[0]
if ((Run-Checked git rev-parse HEAD) -ne $mainBefore) {
    throw 'HEAD differs from remote main. Stop; do not automatically pull or reset.'
}
Run-Checked $py -m unittest discover -s tests -p test_stability_lab.py -v
Run-Checked $py -m unittest discover -s tests -p test_bundled_assets.py -v
```

Expected: local freeze passes; 13 room tests and 8 bundle tests pass.

### 2. Stage only this checkpoint, then review

```powershell
$tab5Paths = @(Run-Checked $py tools/check_stability_lab_freeze.py git-paths)
Run-Checked git add -- @tab5Paths
Run-Checked $py tools/check_stability_lab_freeze.py verify-staged
Run-Checked git diff --cached --check
Run-Checked git diff --cached --stat
Run-Checked git diff --cached --name-only
Run-Checked git diff --cached -- config/publication/stability_lab_freeze.json
```

Expected: exactly 24 checkpoint files. No `outputs/`, `notebooks/`, secrets,
shared app entrypoint, unrelated changes or LFS objects. The guard rejects
extra staged files and any change to the approved fingerprints.

### 3. After reviewing, commit and push main only

```powershell
Run-Checked $py tools/check_stability_lab_freeze.py verify-staged
Run-Checked git commit -m 'Freeze approved Stability Lab artwork and isolated presentation source'
$tab5Commit = Run-Checked git rev-parse HEAD
Run-Checked git show --stat --oneline HEAD
Run-Checked git push origin main:main
$after = @(Run-Checked git ls-remote --heads origin main pilot-50-dashboard)
$mainAfter = @($after | Where-Object { $_ -match 'refs/heads/main$' })
$pilotAfter = @($after | Where-Object { $_ -match 'refs/heads/pilot-50-dashboard$' })
if ($mainAfter.Count -ne 1 -or $pilotAfter.Count -ne 1) { throw 'Remote verification failed.' }
if (($mainAfter[0] -split '\s+')[0] -ne $tab5Commit) { throw 'Remote main does not match the commit.' }
if (($pilotAfter[0] -split '\s+')[0] -ne $pilotBefore) { throw 'Pilot changed; investigate.' }
Write-Host "Verified Tab 5 GitHub checkpoint: $tab5Commit"
Write-Host "Pilot unchanged: $pilotBefore"
Run-Checked git status --short
```

Remaining unrelated unstaged/untracked files are expected. If a push fails
after the commit succeeds, do not commit again; investigate and retry only
the push when appropriate. Share the final SHA/output before the next tab.
