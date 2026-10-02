# Research Archive implementation through step 3

Research Archive, the final principal museum tab, is available locally at
`http://localhost:8501/?room=research_archive`. This checkpoint completes the
blank production shell, saved-evidence bindings, and first working room with
bounded checks. It is not final cosmetic approval or deployment readiness.

The preceding Case Explorer and room-runtime checkpoint is
`e88feea5e0deb6d5e48cb12378d69ff5d63b2e11`, on local HEAD and origin/main when
this work began. Earlier room implementations and artwork were not edited.
The only existing application-code changes are the Research Archive route in
`streamlit_app.py` and its `ar_` query namespace in `room_runtime.py`.
Pre-existing documentation, inventory and N35 working-tree changes were left
in place and are not part of this implementation.

## Step 1 — blank production shell

The approved reference is `approved_current/11_research_archive_final.png`.
The built-in image editor produced
`streamlit_assets/rooms/research_archive_shell.png`, preserving the library,
furniture, plaques and lighting while clearing interface lettering. The exact
edit prompt is saved beside it in `research_archive_shell.prompt.txt`.

Live labels, counts and controls are code overlays. Decorative paintings in
the architecture are atmosphere, not scientific evidence. Scientific figures
are displayed only from their original saved, checksum-verified files.

## Step 2 — exact saved-evidence bindings

`tools/build_research_archive.py` builds metadata-only partitions under
`streamlit_assets/evidence/research_archive`. The 38 compressed partitions total
493,662 bytes. The manifest records their sizes, SHA-256 values and source-file
hashes. No metrics, restorations or scientific plots are recomputed.

The default record is N33, run
`run_aef04267c2e44495a4e7a6249426bd4d`. Its recorded commit is
`97c9a3208b765bd9ef4d649b75cf3a2c0f5d8f03`; its working tree was recorded as
dirty. This remains visible and is not presented as a clean reproducible run.

The index preserves these distinct populations:

| Record family | Saved population |
| --- | --- |
| Painting provenance | 300; 268 with descriptive date, style and medium, 32 incomplete |
| Case / candidate indexes | 3,425 registered cases; 13,879 indexed candidates |
| Pipeline records | N01–N33, plus separately linked N12A, D01 and D02 |
| N33 upstream run IDs | Exactly 32, N01–N32; linked records are not added |
| N32 reports | 300 painting, 30 selected-case, one collection: 331 total |
| Other reports | Five N31 model reports and one N33 final report |
| N33 evidence | 24 figures, 49 claim-registry entries, 18 limitations |
| N33 saved checks | 536 / 536 passed; not a new validation run |
| Individual publications | 2,653 saved verified records: 2,644 candidate-tier and nine diagnostic-tier objects |
| Bundle releases | Six separate verified release records, not added to individual publications |
| N32 direct report package | Separately recorded 361 objects: 331 reports and 30 grids |

D01 is explicitly a frozen Controlled-50 method-selection decision linked for
provenance; it is not another Controlled-300 results population. Claim entries
retain their original source keys and report anchors. Their full prose remains
in the original final report, not newly generated summaries.

Publication routes use recorded full commit revisions. N31/N33 GitHub report
routes are emitted only when bytes at the recorded code checkpoint match the
report index. N32 links to its pinned package folder; an unrecorded per-object
remote URL is not guessed. Zenodo was planned at Step 3; the 2026-10-02
publication closeout adds the verified DOI `10.5281/zenodo.23092185` through a
separate publication receipt without changing frozen Step-3 evidence partitions.
The receipt records a later public-API size/MD5 check; historical HF verification
is not described as a fresh network check.

### Integrity caveat retained, not repaired

N29's current artifact-manifest hash differs from the value in its run record:

- Recorded: `5df62a9675e9b6ad214475887378d29043312ca792f33ab0c5c24a7e2ac08a60`
- Observed: `9ec4a9f68a49f724b4f56ed3cf259971013378c39961be2065ce13f5a0438dfa`

Both are retained and the N29 run and checksum views show an integrity warning.
No producer record was rewritten to make them agree. Older runs lacking that
hash field are marked as not recorded, rather than falsely verified or failed.
Build-time notebook snapshots are labelled separately from the dirty producer
run. Configuration downloads must match the run-recorded checksum; changed
current configuration bytes fail closed.

## Step 3 — working room and bounded verification

The room provides searchable provenance, run and artifact catalogues; exact
report selection; upstream lineage; original figures; claim source keys;
four limitation drawers; pinned publication records; and separate bundle
metadata. Dialogs use readable text and tables, pagination, keyboard closing,
and quick-access controls below the scene.

Only the requested publication index or selected painting partition loads on
demand. Actual report/artifact bytes require an explicit Open or Prepare
action. Selected local files must pass their exact checksum and size checks.
Directory collections are not turned into invented ZIPs. Local artifact
preparation is bounded to 32 MiB; metadata decompression is bounded to 8 MiB.
Missing, mismatched and unknown selections do not silently substitute data.
Remote fallback is deferred, and no large bundle is fetched automatically.

Within-room query changes use the existing Streamlit transport. Cross-room
links retain ordinary document navigation. Browser checks confirmed the same
document identity across painting-specific candidate loading, N29 selection,
N33 manifest verification, and opening the original p018 mixed-damage report.

Completed checks:

- 18 Python tests: 14 Archive tests and four existing room-runtime tests.
- Seven Node tests: three Archive-controller tests and four room-runtime tests.
- Browser: literal search, p018 source provenance and its 178 exact indexed
  candidates, 32-entry N33 lineage, N29 warning, N33 checksum result, 337-record
  report catalogue, original N32 report rendering, original verified N33 figure,
  diagnostic-tier publication filtering, and six separate bundle records.
- Desktop and narrow-screen layouts; no dialog/document horizontal overflow in
  the narrow-screen check; 18 limitations and the three-record Models subset;
  Escape closing and normal viewport restoration.

Re-run the bounded automated checks from the repository root in PowerShell:

```powershell
$env:PYTHONPATH = 'src'
.venv\Scripts\python.exe -m unittest tests.test_research_archive tests.test_room_runtime
node --test tests/research_archive_controller.test.cjs tests/room_runtime.test.cjs
```

The clean local preview is `research_archive_step3_preview.png`. This pass did
not execute N35, validate a hosted deployment or Firefox, republish evidence,
upload bundles, commit, or push. Next is user visual review and the usual
cosmetic refinement; deployment-wide validation remains a later gate.
