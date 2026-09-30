# Stability Lab — fifth cosmetic pass

- Removed the active ledger's blue-green color and underline. All drawer
  titles share the same warm ink; keyboard focus uses a subtle brass outline.
- Heading now occupies three lines: title, a shortened single-line question,
  and the unchanged historical-correctness caveat.
- Added seven decorative book titles in the requested bottom-to-top order,
  with custom line emblems, warm foil colors and an eight-degree uphill tilt.
  No author names. Each label is registered separately to its existing spine.
- Emblems are embedded SVGs; lettering is HTML/CSS. The shell stays unchanged,
  and no new downloaded font, raster asset or deployment dependency is needed.

Verification: all 13 Stability Lab tests passed, including a new seven-title
and embedded-icon regression. Live browser confirmed all spine labels fit,
all icons load, and all four ledger titles have identical color with no
underline. Data and selection behavior unchanged. No commit, push or upload.

Preview: `stability_lab_cosmetic_pass_05.png`.
