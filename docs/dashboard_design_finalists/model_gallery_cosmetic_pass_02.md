# Model Gallery — lettering and conservation dossiers

## Scope

Local presentation-only iteration for the six latest browser annotations. No
scientific images, candidate selection, metrics, first-three-tab assets, or N35
notebook changes. No staging, commit, upload, or deployment was performed.

## Changes

- Slightly stronger ink on the central and SDXL plaques, without changing their
  dimensions or the approved SDXL left-high/right-low projection.
- HINT book lettering moved four reference-image pixels right; SDXL plaque and
  drawer lettering centered inside their existing projected planes.
- Four alcove title/caption groups follow their corresponding frame slopes.
  Captions remain single-line beneath the names and above the ornamental frames.
  Explicit button line-height rules fix the previous shared-style override.
- Main wall title, question, and caveat use shallow SVG text paths with the
  middle lower than both ends. Original semantic headings remain accessible.
- Model, evidence, HINT decision, and bounded-SDXL dialogs share a parchment
  dossier design with a dark-green sticky title rail, brass dividers, accession
  disclosures, recorded-value cards, numbered sections, and comparison ledgers.
- Full 768 × 768 images remain available in the evidence viewer. All original
  candidate metadata, source-report links, caveats, and controls are retained.
- Nested dialog navigation preserves the original trigger for focus restoration.

## Verification

- `tests/test_model_gallery.py`: 11 tests passed, including original report
  hashes, candidate/metric contracts, image geometry, and the N35 hash guard.
- `unittest discover -s tests -p test_dashboard_application.py -q`: 28 passed.
- Browser: opened model dossier, evidence viewer, HINT decision study, and SDXL
  bounded viewer; verified Escape close and image-view switching.
- All four captions occupy one line. Center/SDXL lettering does not overflow its
  projected box. Checked model/evidence/SDXL dialogs for horizontal overflow.
- p018 LaMa crop SSIM remains 0.96856; full comparison ledger and SDXL 0.89191
  remain recorded values, not newly computed results.
- Screenshots: `.codex_tmp/model_gallery_dossier_pass02.png` and
  `.codex_tmp/model_gallery_cosmetic_pass02.png` (local review only).
