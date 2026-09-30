# Trustworthiness — initial local preview verification

Preview: `http://localhost:8501/?room=trustworthiness`

## Implemented

Six clickable physical review stations, exact candidate identity drawer, clean /
damaged / restored evidence inspection, progressive category → painting → case →
method → seed/prompt finder, exact-ID search, comparison peers, recorded threshold
ruler, failure-category/indicator switching, complete flag derivations, recorded
recommendation, N28 policy sensitivity and source-row evidence register.

The visual shell uses blank decorative surfaces. Data and controls are live HTML,
CSS and JavaScript. Dialogues use a plum-and-parchment archival style, Escape/close
controls, modal focus and restoration to the invoking control. Scientific values
are not baked into generated artwork.

## Automated checks

- `test_trustworthiness.py`: **10 tests passed in 32.368 seconds**. Tables loaded
  once; no per-painting inference loop.
- Python syntax: new data/view modules and shared route compile successfully.
- Shared dashboard regression suite: **28 tests passed in 6.473 seconds**.
- Tab 5: **24-file freeze passes**.
- Tab 4: **17-file freeze passes**.
- `git diff --check`: no whitespace errors (pre-existing CRLF notices only).
- N35 SHA-256 unchanged:
  `77dbfb840b22dd590321fe11f75c8e926dbc85f02dcb797bd8bfacafb1d7b673`.

Tests cover exact opening identity, all union roles, primary peer separation,
full-precision cutoffs, registered fitting stratum, six triggered flags, unresolved
colour, category/flag source linkage, missing/ambiguous stratum behavior, invalid
ID rejection, distinct seed identities, selected image hashes and policy rows.

## Browser smoke checks

- Main scene and controller load; current museum navigation preserved.
- Threshold drawer displays exact values and percentile/probability caveat.
- Stratum drawer displays the matching 4,800-record reference population.
- Comparison, policy sensitivity, full evidence, recommendation and D02 scope
  drawers open and close correctly.
- Finder rejects an unknown exact ID without changing the current record.
- Switching to Colour drift and inspecting the missing hue-shift indicator
  displays unavailable evidence, with no invented value or passing state.
- Explicit selection of seed 2027 loads
  `sd15__p00__s2027__392cb1f3e897` and its own observed value
  `6.910241436958308`, not the seed-2026 value.
- Returned to the approved seed-2026 opening for the handoff.

Screenshots: `trustworthiness_initial_preview.png` and
`trustworthiness_threshold_preview.png`.

This is the initial main-room preview, not a freeze or deployment approval. D02's
dedicated mini-room and publication packaging remain outstanding, as noted in
`trustworthiness_steps_01_02.md`.
