# Model Gallery — annotated cosmetic pass 1

2026-09-30. Implements the eight annotations on p018 and applies the rules to
all paintings. No notebook/scientific-asset changes, staging, commits or uploads.

## Changes

- All seven scene image slots map the recorded painting-content rectangle onto
  the inner frame quadrilateral. This hides only the preprocessing padding in
  the gallery presentation; the original PNGs, full-canvas inspection views and
  metric regions/values are unchanged. The SDXL frame corner coordinates were
  also corrected to the actual vitrine opening.
- Central plaque, HINT book, SDXL plaque and availability drawer use Georgia
  lettering in restrained ink/aged-gold colours and four-corner perspective
  transforms matched to their surfaces.
- The evidence readout moved from the gap between frames onto the bottom of the
  central information plaque; it remains clickable and follows model/evidence
  selection. Its short qualifier distinguishes this-case values.
- SDXL lettering explicitly descends from the left end to the right end, on
  both the main plaque and lower drawer.
- The lower table inscription contains only the reference's two lines, rendered
  on shallow curves matching the bowed table front. The overall-population
  qualifier and denominators remain in the model record/accessibility label.
- The complete scene fits both available width and available viewport height,
  with a bottom safety margin. Wider/shorter windows now leave side margins
  instead of cutting off the table inscription.
- A Gallery-only source-mtime check refreshes its imported modules when their
  files change. This addresses the local launcher's stale imports without a
  server restart or changes to the completed rooms.

## Validation

- 11 Model Gallery checks passed, including all 300 recorded content bounds,
  exact default values/identities, zero-control policy and the notebook hash guard.
- 28 existing dashboard tests passed.
- Browser: p018 images use `[0,130,768,637]`, the recorded content rectangle.
- Tested wide/short and laptop-height viewport overrides (requested 1920×900
  and 1366×768); the actual CSS viewport may differ with the app's display
  scaling. The full scene and lower inscription remain within the measured
  viewport. Temporary overrides were reset after testing.
- Browser measurements confirm both SDXL text planes have a higher left edge
  and lower right edge, with no content-height overflow.
- Checked all four model selections and the relocated evidence readout.
- Checked p055's horizontal padding (`[0,103,768,664]`) and p001's side padding
  (`[52,0,715,768]`); all displayed restoration slots loaded and used the same
  case-specific geometry. The inspection image has no display-crop styles.
- After the final spacing adjustment, the central plaque reports 132 px content
  height within its 132 px source plane. Returned to p018 / LaMa / crop SSIM.

No claim is made that every painting has been visually inspected. Geometry is
validated for all 300; browser checks are representative. Remaining unannotated
issues, such as alcove subtitle spacing and drawer-label truncation, are left
for the next user-directed iteration.
