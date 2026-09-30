# Stability Lab — fourth cosmetic pass

- Removed visible wheel placement numbers, retaining accessible button names,
  mask previews, selection indicators and existing click behavior.
- Test ledger and its four drawers now show only their primary titles, with
  centered, heavier warm-ink typography. Drawer numbers 01–04 retain their
  existing style and position (browser comparison within 0.02 CSS pixels).
- Removed the floor slogan and its explanatory sentence.
- Moved the test-boundaries action onto the bottom cabinet drawer. Its
  decorative face reuses the existing shell's blank fourth drawer plaque via
  CSS background registration, including the photographed frame and handle.
  No separate raster asset or deployment dependency was introduced.
- The boundaries label has no underline or arrow. Its original evidence
  dialog and scope explanation remain unchanged and accessible.

Verification: all 12 Stability Lab regression tests passed. Live browser
confirmed the relocated button opens the boundaries dialog. Shell and N35
hashes unchanged. No scientific data or controller edits; no commit or upload.

Preview: `stability_lab_cosmetic_pass_04.png`.
