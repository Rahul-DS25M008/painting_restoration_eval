# OpenCV Telea Classical Metric Findings

Primary ranking region: `masked_region`.
Primary ranking metric: `mse_improvement`.

## Improvement rates by dataset

- canonical: 100.00% of valid cases improved in masked-region MSE (200/200).
- damage_size: 100.00% of valid cases improved in masked-region MSE (35/35).
- mask_robustness: 100.00% of valid cases improved in masked-region MSE (75/75).
- synthetic: 2.00% of valid cases improved in masked-region MSE (1/50).

## Strongest cases

- Rank 1: mask_robustness / p001__scratch_thin__variant_01 — Telea improved the masked region, with an MSE change of 54865.073723 and PSNR change of 30.922 dB.
- Rank 2: canonical / p001_loss_small — Telea improved the masked region, with an MSE change of 54255.765160 and PSNR change of 28.997 dB.
- Rank 3: canonical / p006_scratch_thin — Telea improved the masked region, with an MSE change of 53493.311543 and PSNR change of 29.374 dB.
- Rank 4: mask_robustness / p001__loss_small__variant_03 — Telea improved the masked region, with an MSE change of 52637.539597 and PSNR change of 27.209 dB.
- Rank 5: mask_robustness / p001__scratch_thin__variant_04 — Telea improved the masked region, with an MSE change of 51804.468445 and PSNR change of 25.426 dB.
- Rank 6: mask_robustness / p001__scratch_thin__variant_02 — Telea improved the masked region, with an MSE change of 51131.006096 and PSNR change of 26.873 dB.
- Rank 7: mask_robustness / p001__loss_small__variant_01 — Telea improved the masked region, with an MSE change of 50518.258011 and PSNR change of 23.143 dB.
- Rank 8: mask_robustness / p001__loss_small__variant_04 — Telea improved the masked region, with an MSE change of 50467.876328 and PSNR change of 25.042 dB.
- Rank 9: mask_robustness / p001__loss_small__variant_05 — Telea improved the masked region, with an MSE change of 50456.341522 and PSNR change of 22.483 dB.
- Rank 10: canonical / p001_mixed_damage — Telea improved the masked region, with an MSE change of 50310.963135 and PSNR change of 19.345 dB.

## Weakest cases

- Rank 1: synthetic / p039__partial_transparency__severe — Telea worsened the masked region, with an MSE change of -1060.510345 and PSNR change of -6.107 dB.
- Rank 2: synthetic / p039__partial_transparency__moderate — Telea worsened the masked region, with an MSE change of -1033.796829 and PSNR change of -9.787 dB.
- Rank 3: synthetic / p043__partial_transparency__severe — Telea worsened the masked region, with an MSE change of -941.627258 and PSNR change of -4.346 dB.
- Rank 4: synthetic / p026__partial_transparency__severe — Telea worsened the masked region, with an MSE change of -635.748093 and PSNR change of -5.834 dB.
- Rank 5: synthetic / p018__partial_transparency__severe — Telea worsened the masked region, with an MSE change of -584.121460 and PSNR change of -3.116 dB.
- Rank 6: synthetic / p018__water_stain__mild — Telea worsened the masked region, with an MSE change of -504.709290 and PSNR change of -14.990 dB.
- Rank 7: synthetic / p043__partial_transparency__moderate — Telea worsened the masked region, with an MSE change of -491.415497 and PSNR change of -7.433 dB.
- Rank 8: synthetic / p039__water_stain__moderate — Telea worsened the masked region, with an MSE change of -464.983009 and PSNR change of -8.627 dB.
- Rank 9: synthetic / p039__partial_transparency__mild — Telea worsened the masked region, with an MSE change of -283.953956 and PSNR change of -15.688 dB.
- Rank 10: synthetic / p043__partial_transparency__mild — Telea worsened the masked region, with an MSE change of -279.298096 and PSNR change of -10.114 dB.