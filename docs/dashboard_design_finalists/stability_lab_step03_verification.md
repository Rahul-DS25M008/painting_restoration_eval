# Stability Lab — initial implementation handoff

Status: steps 1–3 complete locally; **not visually frozen**. Step 4 awaits the
user's morning review. No other room was started.

## Open the preview

`http://localhost:8501/?room=stability_lab`

Opening: p018, LaMa, damage-size sensitivity, 20%, spatial masked error.
The browser is left on this declared opening, not on a test/debug state.

## Implemented

- Approved-reference-derived blank-content nighttime atelier shell.
- Exact input/restoration pair; full original input, restoration, reference and
  mask available through the inspection register.
- Seven nested damage-size stops; five exact mask placements and three fixed
  family–area conditions; four eligible degradation families and their recorded
  severities; a fifth bottle explaining excluded non-inpainting diagnostics.
- Four recorded seed thumbnails and six-pair chart after an explicit SD switch.
  Canonical generic and scratch-aware prompt groups remain separate. N22 uses
  the original rendered overlay; N18 clearly states no per-case overlay exists.
- Painting/method/evidence selectors and case-scoped URLs.
- One chart at a time, original values and row IDs, no combined score.
- Four parchment-style ledger dialogs with counts, findings and boundaries.
- Native dialog focus handling / Escape dismissal, semantic buttons, keyboard
  operation and accessible chart value summaries.
- Stage scales to available viewport height; native aspect ratio retained.

## Local checks

| Check | Result |
| --- | --- |
| Stability Lab tests | 11 passed |
| Frozen Model Gallery tests | 11 passed |
| Existing dashboard runtime / approved-room contract tests | 28 passed |
| JS syntax (`node --check`) | Passed |
| 17-file Model Gallery freeze guard | Passed; no LFS filters/pointers |
| N35 fingerprint | Unchanged: `77dbfb840b22dd590321fe11f75c8e926dbc85f02dcb797bd8bfacafb1d7b673` |

Data coverage includes all 4,480 focused primary candidates, each with all three
exposed measures; all 1,025 four-seed groups and their exact prompt-specific
memberships; existence of all 245 N22 overlay images. Embedded images are checked
against producer checksums where available. No scientific values are recomputed.

### Browser checks performed

- Opening seven-point LaMa trajectory and source-row table.
- 20% → 2% changes the input and selected case.
- Mask wheel position 5 selects variant 05, not a fallback variant.
- Switching large loss / 12.5% to thin scratches / 2% changes the whole fixed
  condition correctly and selects its first recorded variant.
- Water stain + dirt offers only its actual Moderate severity.
- Excluded-task bottle explains non-inpainting boundary.
- LaMa seed drawer requires explicit Stable Diffusion switch.
- Repeated-seed ledger opens the actual 2026–2029 group, all four thumbnails,
  six-pair chart, recorded 0.128265… standard deviation and original N22 overlay.
- Scratch-aware canonical group shows `p05_scratch_aware`, its own members and
  explicit absence of an N18 per-case overlay; nothing fabricated.
- Crop SSIM changes the plotted evidence and restoration inspection displays
  its recorded 0.76905… default-case value and correct higher-is-better direction.
- Full-canvas image inspector, dialog dismissal, broken-image count zero.
- Default and height-constrained viewport checks: complete stage remains within
  the available CSS viewport. Temporary viewport override reset afterward.
  Browser zoom / display scaling was not changed or claimed to be 100%.
- Heading-to-plaque clearance checked after the initial fit adjustment.

## Files and boundaries

New isolated adapter/view: `src/restoration_eval/stability_lab.py` and
`stability_lab_view.py`. New CSS/controller/shell under `streamlit_assets`.
The only shared app edit in this turn is the `stability_lab` route with the same
source-mtime refresh pattern used by Gallery. Existing dirty work was preserved.
The first four approved tabs' presentation files were not edited.

Reference/content audit: `stability_lab_steps_01_02.md` and
`stability_lab_readiness_audit.json`. Built-in image-generation final prompt and
output path: `stability_lab_shell_prompt.txt`.

Preview screenshots: `stability_lab_initial_preview.png` and
`stability_lab_seed_preview.png`.

This remains an initial local preview, not a freeze or cloud-readiness claim.
Long selector labels, small brass labels, exact lettering/perspective and any
painting-fit refinements are the next user-led step 4. Local CSV scans and image
reads still need the later shared pinned remote asset resolver / compact lookup
integration before hosting. No new Streamlit deployment, commit, GitHub push,
HF upload or N35 edit was performed.
