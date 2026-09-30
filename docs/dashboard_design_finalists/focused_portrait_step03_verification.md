# Focused Portrait Review — step 3 local verification

Preview: `http://localhost:8501/?room=focused_portrait_review&return_room=trustworthiness`

## Implementation

The room is implemented as a live child route with a blank generated shell,
five inspectable evidence prints, exact review selection, anatomical annotation
and matched-control inspection, separate hand/lightness metric selectors,
recorded uncertainty intervals, blind review, acceptable counterexamples,
source-row details, CSV downloads, and the original self-contained D02 report.
The four foreground books retain the approved titles.

Files: `focused_portrait.py`, `focused_portrait_view.py`,
`focused_portrait.css`, `focused_portrait_controller.js`, plus the shared route.
No frozen Trustworthiness source or asset was edited. Pre-existing unrelated
working-tree changes were preserved.

## Automated checks

- Eight focused Python tests passed (2.055 seconds on the final evidence run).
- Node chart-domain and exact absolute-RGB pixel tests passed.
- JavaScript syntax checks passed; Python modules and route compiled.
- `git diff --check` passed; only existing line-ending notices were reported.
- Trustworthiness: 28-file local freeze passed, fingerprints unchanged,
  no LFS, 10.62 MiB.

Tests cover exact R005 identity and original control pixels, study counts,
separate summary metrics, recorded note and counterexample, a mask-variant case,
invalid-ID/return-route rejection, retained lightness context/covariates, and
accessible room controls. These are bounded local checks, not a new N35 run.

## Browser checks

- Room and live image canvases load with exact R005 evidence.
- Hand selector switches to SSIM; detailed intervals and source rows remain
  available. The axis explicitly reads control minus hand for SSIM.
- Lightness selector switches to error-oriented PSNR and preserves uncertainty.
- Context profiles show recorded p001–p004 and p284–p295 matches; values update
  when the profile changes. A click-event/default-argument defect was fixed.
- Eligibility drawer displays 1,196 hand pixels, 4,551 anatomical pixels,
  1,196 control pixels, and zero overlap.
- Blind-review drawer displays the exact R005 note and clean/restored crops.
- Acceptable-counterexample navigation loads R002 with its distinct preserved-
  anatomy observation. Painting/method selectors return to R005 p269 HINT.
- Navigation uses a parent-document anchor, matching the existing application
  pattern; direct iframe parent-location assignment was corrected.
- Original D02 HTML report download control is available without recomputing
  analysis. The 28 MB download itself was not repeated.
- Report return is a same-tab link.

Screenshots: `focused_portrait_initial_preview.png` and
`focused_portrait_blind_review_preview.png`.

## Remaining boundary

This completes the initial local steps 1–3 implementation, not final visual
approval or freezing. The adapter currently requires verified local producer
files and the N34 package. HF packaging and deployment validation remain
separate future work. No deployment, new inference, statistical refit, or
scientific-output rewrite was performed.
