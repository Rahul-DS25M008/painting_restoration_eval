# Stability Lab — final drawer and popup polish

- Trimmed the stray edge from the decorative drawer-face registration with a
  narrow angled CSS clip; no shell repainting or new raster asset.
- Renamed the control to Test Boundaries, using the same .93 cqw bold warm
  lettering and 1.6-degree tilt as the ledger labels, clear of the handle.
- Restyled the shared evidence dialog: deep-green/brass sticky header,
  parchment surface, numbered chapter cards, restrained study-stat cards,
  warm boundary callouts, framed charts and images, styled tables and seed
  cards, brass buttons, visible keyboard focus and reduced-motion support.
- Scientific text, numbers, images, controls and controller behavior are
  unchanged. All popup types inherit the same design, including guard states.

Verification: 13 Stability Lab tests passed; controller JavaScript syntax
passed. Live browser checks covered boundaries, ledger interpretation,
trajectory/table, image inspection, closed seeds, mask conditions, exclusions,
and the available four-seed view. Checked dialogs had no horizontal overflow;
all four seed cards and their images loaded. Opening case restored afterward.
Shell and N35 hashes remain unchanged. No commit, push, upload or deployment.

Previews: `stability_lab_cosmetic_pass_06.png` (room) and
`stability_lab_popup_pass_06.png` (boundaries register).
