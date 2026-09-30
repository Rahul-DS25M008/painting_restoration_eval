# Trustworthiness cosmetic pass 06

- Preserved the threshold board's existing layout, data, observed badge, shading, and numeric scale. Added amber/red triangular cutoff pointers at the exact warning/critical coordinates, with their values directly beneath and percentile labels below those. Nearby ordinary tick labels are suppressed to avoid collision; close cutoff labels are vertically staggered without moving their numeric positions.
- Station 1 shifted +2px horizontally and -3px vertically. Station 2 shifted -2px horizontally and -3px vertically (Comment 3's marked target). Stations 3–5 shifted -4px vertically. Station 6 unchanged.
- Removed the exterior assignment-status line. The recorded severity now appears inside the category seal beneath the category name.
- Added the reference caption, “The main reason for the flag.”, beneath the connector in subdued wall-colored ink.

Verification: controller syntax check, four Python presentation tests, and JavaScript chart tests passed. Chart tests cover exact pointer/value alignment, matching colors, close cutoffs, higher/lower directions, missing evidence, and preservation of recorded values.
