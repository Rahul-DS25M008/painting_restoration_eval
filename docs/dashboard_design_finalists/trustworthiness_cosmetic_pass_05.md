# Trustworthiness cosmetic pass 05

- Reduced the evidence wall caption from .78cqw to .68cqw, softened its ink to #c5b7a7, and inset it to clear the adjacent cabinet frame.
- Added the reference caption: “A fair and relevant group for comparison.”
- Raised Comparison peers 3 CSS pixels; Same experiment, Same indicator, Region + statistic, and Threshold 4 CSS pixels. Fitting population is unchanged.
- Reduced “How this boundary was fitted” by exactly 15%, from 1.02cqw to .867cqw.
- Rebuilt the threshold ruler in SVG with serif summary text, muted amber/red cutoff regions, brass end posts, fine graduations, a pinned observed-value badge, and the probability caveat. Numeric scale positions remain linear and data-driven; no median or reference-example observations are substituted.
- Retained all existing popup actions and full-precision recorded evidence.

Verification: four Python presentation tests passed; dependency-free JavaScript chart tests passed for current, critical, lower-is-worse, and missing-evidence cases; controller syntax check passed. Browser popup verified the p256/HINT values: observed 0.4709723085165021, warning 1.7923734879493693, critical 4.8924025321006255, recorded state neutral.
