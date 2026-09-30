# Model Gallery — step 3 first functional implementation

2026-09-30. Local implementation only; not a final cosmetic sign-off or a deployment.

## Scope

New isolated `model_gallery.py`, `model_gallery_view.py`, CSS and controller.
`streamlit_app.py` only gains the Model Gallery route branch in this pass.
Existing first-three-room implementations and scientific outputs were not edited.
N35 SHA-256 remains `77dbfb840b22dd590321fe11f75c8e926dbc85f02dcb797bd8bfacafb1d7b673`.
No staging, commit, push, HF upload or online Streamlit app creation.

## Implemented

- Approved rotunda shell, four live method alcoves, shared damaged input,
  perspective-projected image frames, selected-method foreground picture/plaque.
- Painting drawer: all 300 paintings with real titles. A new painting opens its
  declared canonical mixed-damage case; the caption and URL identify it.
- Damage drawer: all actual eligible cases for that painting, with experiment,
  damage-size, mask-variant and supplementary synthetic identities retained.
- Evidence drawer: recorded crop SSIM, masked MAE, whole-image SSIM and
  outside-repair MAE. Unsupported choices are disabled. When a new case cannot
  support the previous choice, a visible note and live announcement identify
  the valid replacement; no metric values are invented.
- Inspection dialog: reference / damaged / restored / mask views and a
  same-case four-method table with damaged, restored and signed-improvement values.
- Model records: complete model-card/candidate disclosures, exact seed and
  prompt, configuration and hashes; original N31 HTML report download access.
- HINT book: separate 5-painting / 12-case / 9-anchor decision pilot, original report.
- SDXL vitrine: exact-case completed result or explicit unavailable state,
  24/35 bounded scope, not a fifth method in the full-scope ranking.
- Overall N21 conclusion is separately labeled, including eligible denominators;
  it does not change into a case-specific claim when a selector changes.
- Primary SD candidates only, as approved in steps 1–2. Additional seed/prompt
  studies remain assigned to Stability Lab, not silently mixed into this gallery.

## Verification

Commands run using the existing project environment (no packages installed):

```powershell
.venv\Scripts\python.exe tests/test_model_gallery.py
.venv\Scripts\python.exe -m unittest discover -s tests -p test_dashboard_application.py -q
.venv\Scripts\python.exe -m unittest discover -s tests -p test_metric_inspection.py -q
```

- 10 new checks passed: 300 paintings / 2,620 matching four-method primary cases,
  declared defaults, rejection of mismatched identity, exact opening values,
  all 300 zero controls, full primary output existence, valid full-image evidence,
  case-scoped SDXL availability, original report hashes, experiment labels, N35 guard.
- 28 existing dashboard tests passed.
- 25 existing Metric Framework tests passed.
- Browser: all 16 combinations of the four methods and four evidence choices
  on p018 produced the expected recorded readout.
- Browser: reference/damaged/restored/mask view switching, complete SD seed/prompt
  disclosure, HINT pilot, completed SDXL and unavailable SDXL dialogs checked.
- Browser: p018 zero control disables crop SSIM and masked MAE and selects valid
  whole-image evidence; no SDXL image is substituted.
- Browser: painting drawer changed to p055; all six main projected image elements
  loaded, with the matching p055 case identity, then returned to p018.
- Browser: original-report link reaches the local report-download dialog.
  Original report contents are hash-checked; no external publication is involved.
- Browser: p018 synthetic dirt/dust mild loaded all projected images, preserved
  its supplementary masked-removal label, and showed its actual positive and
  negative signed improvements. Returned to p018 canonical mixed damage / LaMa.
- Fixed a discovered component-frame navigation restriction by using normal
  parent-document links for drawer navigation, then retested painting and case changes.

This is representative browser validation plus full data-join checks, not a claim
that every painting/case has been manually visually inspected.

## Logged for the user-led next iteration — not silently polished

1. **Painting treatment first:** the full recorded 768-square canvases are fitted
   into the physical frame quadrilaterals. Their inherent padding remains visible,
   and mapping square canvases into the reference's wide frames can compress the
   artwork visually. Inspect/choose the desired display-only crop/mat treatment
   next; the inspection dialog retains the complete source canvas.
2. Drawer labels truncate at small viewport sizes, especially long painting titles
   and case identities. Full identities remain in the option list and inspection.
3. Small-screen plaque/family-label typography is dense; font size, line breaks,
   perspective, baseline and spacing need the usual annotation-led cosmetic pass.
4. Native dropdown option menus are parchment-coloured where supported, but their
   popup geometry remains browser-dependent. A bespoke museum-styled popup can
   be considered in the cosmetic pass if needed.
5. The evidence readout sits on the foreground picture's lower edge; confirm its
   placement and size against the reference during visual review.
6. Original report download uses a standard Streamlit dialog. Museum-style polish
   for this secondary surface remains optional.
7. This first pass uses local producer assets. Broader remote-asset transport,
   deployment packaging and online loading performance remain the later hosting
   task; nothing was uploaded or deployed here.
8. Method selection currently uses the alcove title or framed picture. The floor
   routes are visual wayfinding, not separately clickable hit areas in this pass.

Next: user inspection, then step 4's image/painting corrections before cosmetics.
