# Metric Framework verification — spatial inspection pass

Date: 2026-09-29

## Final approved-design sweep (2026-09-29)

No new blockers found. Verification only: no application or notebook edits.

- 53 dashboard/inspection regression tests passed, including the source-stability
  guards for Foyer, Study Design and shared navigation.
- Live p018 browser sweep: all 37 enabled lens/region pairs reached ready state,
  with matching evidence identity, visible inspection lens and contained plaque.
  All 12 prohibited combinations were disabled.
- Reference/Damaged/Restored switching and keyboard lens movement passed.
  A screenshot-grounded pointer drag changed inspection coordinates.
- Expanded Measurements & support scrolls inside the evidence plaque.
- Surprise me changed p018 to p055 while preserving spatial/damaged filters.
  The picker selected p001; its portrait and all room images loaded correctly.
  Reload retained p001 and the active filters.
- Compact and wide desktop views were inspected. No missing images, new visible
  clipping or browser console errors were found. The removed Surprise tooltip
  has no title/description tooltip hooks on its button container.
- Fresh scientific integrity sample audit: p001, p018, p055 and p300 passed
  (`.codex_tmp/metric_final_sample_audit.json`). The earlier 300-painting audit
  remains separate historical coverage, not a new full-collection run.
- Restored p018 with spatial/damaged filters and the Restored image view.
- Notebook SHA256 remains unchanged at the value recorded below.

Known scope boundary: desktop widths were checked; this is not a fresh mobile
redesign or a repeat of every painting through every browser combination.

## Scope

This pass implements the approved seven-lens/seven-region inspection interaction.
It does not execute or edit notebooks, modify frozen benchmark results, redesign
the first two rooms, or implement the other museum tabs.

## Browser verification

Performed in the live local Streamlit application, not only against static HTML.

| Check | Result |
|---|---|
| p018: 37 enabled pairs × Reference/Damaged/Restored | 111 ready states; passed |
| p018: keyboard movement in those states | 111 passed |
| p018: pointer drag in every enabled pair | 37 passed |
| Prohibited lens/region pairs | All 12 disabled with explanations |
| p001 portrait: 37 enabled pairs × three image views | 111 ready states; passed |
| p001 source image versus selected thumbnail | All 111 matched |
| p001 plaque versus active evidence identity | All 111 matched |
| Invalid region after lens switch | Old map hidden, region cleared, reason and recommendation shown |
| Painting picker p018 → p001 | Correct painting/case/candidate and preserved filters |
| Surprise me p001 → p038 | Correct new exhibit and preserved filters |
| Explicit reload after selecting p001 | Painting, lens, region and view retained |
| Narrow and wide desktop viewport requests | State and source-coordinate position retained |
| Repeated rapid valid/invalid filter transitions | Final map/plaque/source identity consistent |
| Final imported presentation helper | `metric_view.v2`, ready state |
| Final collection entry p300 | Correct exact candidate, ready map, no error alert |

The browser matrix was exercised on both a landscape and a portrait. This does
not claim that every one of the 300 paintings was manually dragged through all
111 states; collection-wide coverage is checked by the separate data audit.

Browser automation initially had a viewport/click-coordinate mismatch. Those
attempts were not counted as passes. The full keyboard matrix and subsequent
screenshot-grounded pointer tests above verified the actual controls and results.
Early development console errors from missing geometry were corrected before the
recorded successful matrix runs.

## Automated regression tests

- `python -m unittest discover -s tests -p 'test_dashboard_application.py'`: 28 passed.
- `python -m unittest discover -s tests -p 'test_metric_inspection.py'`: 15 passed.
- `git diff --check` on the implementation files: no whitespace errors.

The tests cover exact canonical painting/case/candidate resolution, the public
49-pair policy, source-space projection, real patch ownership, normalized seam
gradients, pixel/signed-improvement arithmetic, content geometry, source hashes,
and rejection of changed sources, changed maps and incorrect recipes.

## Full-collection audit

**Complete: all 300 paintings passed**, covering 11,100 enabled inspection pairs
and 3,600 prohibited policy entries. Both 150-painting audit processes exited
successfully. The two reports contain 300 unique painting IDs and no failures.

Audit outputs:

- `.codex_tmp/metric_first150_audit.json`
- `.codex_tmp/metric_last150_audit.json`
- `.codex_tmp/metric_browser_validation_20260929.json` (observed browser records)
- `.codex_tmp/metric_framework_verified_20260929.png` (default-case screenshot)

For each painting the audit checks:

1. Exact painting/case/candidate/version and all 49 policy entries.
2. Source, region and map checksums and registered image geometry.
3. Complementary damaged/outside masks and boundary restricted to content.
4. Numeric archive checksum, nonempty valid support, and no float16 infinities.
5. Pixel error, signed improvement and outside alteration against source images.
6. Boundary-gradient mismatch against the existing normalized Sobel convention.
7. Every enabled pair's map, finite values and region summary.
8. Map transparency matches numerical no-data support.
9. Patch colours correspond to genuine recorded window scores, not invented pixels.

## Preserved work

The existing byte-stability tests for the approved Foyer, Study Design and shared
navigation regions pass. The notebook was not edited or executed in this pass.
Its SHA256 remains:

`77DBFB840B22DD590321FE11F75C8E926DBC85F02DCB797BD8BFACAFB1D7B673`

Existing unrelated dirty files and the earlier notebook error were left alone.
New diagnostic companions are kept under
`streamlit_assets/evidence/metric_framework/`, not inside the frozen output tables.

## Limits and next iteration

- Spatial learned responses and their means are inspection companions, not blanket
  claims of parity with all frozen scalar benchmark metrics.
- Grey hatching means unsupported/not evaluated, not a zero score.
- Fixed scales can make small errors look dark; scales are not auto-stretched.
- Feature/layout maps do not establish historical correctness or semantic truth.
- Typography, cabinet alignment, caption space, contrast choices and mobile layout
  remain in the user-led cosmetic iteration log.

See `metric_framework_inspection_guide.md` for all combinations and usage examples.
