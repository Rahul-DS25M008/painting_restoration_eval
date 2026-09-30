# Stability Lab — second cosmetic pass

Applied the ten annotated refinements without changing evidence, metrics, source
assets or selection rules.

- Note-board record link moved up 3 CSS pixels; other board content unchanged.
- Damage Size reduced exactly 10% (1.26 → 1.134 cqw); tilt refined to -4.7°.
- Painting-area caption moved up 3.5 CSS pixels, retaining its existing tilt.
- Registrar desk uses heavier Palatino-style headings and selected values.
  Painting shows its short ID plus the real clean-reference thumbnail; Method
  shows the selected name plus the actual case mask; Evidence shows its measure
  plus a brass-style magnifier. Requested helper lines removed. Native selects
  retain complete option labels, accessibility names and keyboard operation.
- Bottle labels use explicit line breaks, heavier ink, and per-label sizing for
  long words. Browser checks confirmed all five labels fit in both dimensions
  (`scrollWidth <= clientWidth`, `scrollHeight <= clientHeight`).
- Single-line centered headings: `Degradation stress` and
  `Repeated Seeds - SD only`.
- Seed card has compact line spacing and darker, slightly heavier lettering in
  both closed and available states.

Verification: 12 Stability Lab tests passed; JavaScript syntax passed. Live
Method selection changed LaMa to Stable Diffusion and showed the available seed
card; the Evidence selector remained operational. No broken scene images.
Default opening restored after checks.

Shell and N35 hashes still match the prior checks. Frozen Model Gallery files
remain unmodified. No staging, commit, push, upload or deployment performed.

Preview: `stability_lab_cosmetic_pass_02.png`.
