# Tab 4 — approved Model Gallery freeze

The visual design is frozen at the user's final Arrakis position. This is a
**17-file isolated Tab 4 checkpoint**, not a whole-app or N35 completion claim.
The shell, CSS, controller, renderer (including SVG engravings), data adapter,
tests, audit helper, and review documentation are preserved in ordinary Git.
Shared `streamlit_app.py` wiring and other unfinished local files are excluded.
Those files remain local for the consolidated application checkpoint later.

## Checked storage state

- Local HEAD and live GitHub main both equal
  `e5d733225718d27cec780d77ad43036d1cde8210` at preparation time.
- Existing pilot deployment branch is `pilot-50-dashboard`, observed at
  `125ea5653026ca5a17ccd991f8ef2d1f1363b62d`.
- All 16,044 distinct Gallery image paths are accounted for: 13,400 tracked in
  Git and 2,644 in verified HF publication records. This is complete path
  coverage, not a fresh download verification of every remote object.
- Live pinned metadata checks matched HINT/SDXL image hashes and the N13 metrics
  hash. Existing Git LFS clean/LaMa payloads returned HTTP 200 with matching ETags.
- The new shell is 2,096,154 bytes and its existing attribute is `filter: unset`.
  CSS/JavaScript/Python files have no LFS filter. The approved reference is already
  tracked. No new bulk evidence was created by Tab 4.

**No HF upload is needed for this checkpoint.** Do not re-upload the 01–03
release or duplicate already-published scientific images. Do not run the older
901-object upload command. Existing bundles preserve exact member bytes and
indexes. Future genuinely new bulk assets should be grouped into bounded
approximately 32-MiB ZIPs with consolidated indexes, immutable revision pins,
member paths and hashes, rather than one remote object per image.

Bundling does not prevent Streamlit deployment: fetch/cache only the required
bundle and decode its verified member bytes. However, the present Gallery
adapter still reads local originals and scans the N13 CSV. Lazy pinned remote
loading and a compact metric lookup remain to be integrated before cloud use.
No app creation, hosted test, notebook execution, or deployment happens here.

## PowerShell commands — run these yourself, in order

Use one terminal. Stop if a command fails. Do not use `git add .`, `git add -A`,
`git commit -a`, force push, or an LFS migration. These instructions intentionally
leave unrelated dirty files untouched.

### 1. Preflight and verify the frozen local files

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
Run-Checked $py tools/check_model_gallery_freeze.py verify-local
$before = @(Run-Checked git ls-remote --heads origin main pilot-50-dashboard)
$mainLine = @($before | Where-Object { $_ -match 'refs/heads/main$' })
$pilotLine = @($before | Where-Object { $_ -match 'refs/heads/pilot-50-dashboard$' })
if ($mainLine.Count -ne 1 -or $pilotLine.Count -ne 1) { throw 'Expected branches missing.' }
$mainBefore = ($mainLine[0] -split '\s+')[0]
$pilotBefore = ($pilotLine[0] -split '\s+')[0]
if ((Run-Checked git rev-parse HEAD) -ne $mainBefore) {
    throw 'Local HEAD differs from remote main. Stop; do not automatically pull or reset.'
}
Run-Checked $py tests/test_model_gallery.py
```

Expected: 17-file local guard passes, and 11 Gallery tests pass. The tests include
the N35 hash guard but do not run or modify the notebook.

### 2. Stage only the frozen checkpoint and inspect it

```powershell
$tab4Paths = @(Run-Checked $py tools/check_model_gallery_freeze.py git-paths)
Run-Checked git add -- @tab4Paths
Run-Checked $py tools/check_model_gallery_freeze.py verify-staged
Run-Checked git diff --cached --check
Run-Checked git diff --cached --stat
Run-Checked git diff --cached --name-only
Run-Checked git diff --cached -- config/publication/model_gallery_freeze.json
```

The guard rejects extra/missing staged files, LFS filters/pointers, changed
approved fingerprints, and files above 10 MiB. The expected set is exactly 17
files. No `notebooks/`, `outputs/`, `streamlit_app.py`, first-three-tab files,
secrets, or unrelated changes should be staged.

### 3. After reviewing the staged list, commit and push only main

```powershell
Run-Checked $py tools/check_model_gallery_freeze.py verify-staged
Run-Checked git commit -m 'Freeze approved Model Gallery artwork and isolated presentation source'
$tab4Commit = Run-Checked git rev-parse HEAD
Run-Checked git show --stat --oneline HEAD
Run-Checked git push origin main:main
$after = @(Run-Checked git ls-remote --heads origin main pilot-50-dashboard)
$mainAfter = @($after | Where-Object { $_ -match 'refs/heads/main$' })
$pilotAfter = @($after | Where-Object { $_ -match 'refs/heads/pilot-50-dashboard$' })
if ($mainAfter.Count -ne 1 -or $pilotAfter.Count -ne 1) { throw 'Remote verification failed.' }
if (($mainAfter[0] -split '\s+')[0] -ne $tab4Commit) { throw 'Remote main does not match the commit.' }
if (($pilotAfter[0] -split '\s+')[0] -ne $pilotBefore) { throw 'Pilot branch changed; investigate.' }
Write-Host "Verified Tab 4 GitHub checkpoint: $tab4Commit"
Write-Host "Pilot unchanged: $pilotBefore"
Run-Checked git status --short
```

Unrelated unstaged changes remaining in the final status are expected. No new
HF receipt is required because this checkpoint uploads zero HF objects. If the
push fails after a successful commit, do not commit again; inspect the failure
and retry only the push when appropriate. Share the final commit SHA and output
before starting the next tab. Stop for the night after this checkpoint.
