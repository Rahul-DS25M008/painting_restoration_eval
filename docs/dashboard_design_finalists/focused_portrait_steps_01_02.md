# Focused Portrait Review — steps 1 and 2

Status: initial local implementation, ready for visual review; not frozen.

## Scope and checkpoint

The GitHub `main` checkpoint was confirmed as
`8f0c3a44190aae8097c16382bcae63870822b0f6`. The 28-file Trustworthiness
freeze remains unchanged. This mini room is a child route, not a ninth main tab.
It keeps Trustworthiness active and supports return to Trustworthiness, Study
Design, or Case Explorer. No N35, inference, statistical refit, commit, upload,
or publication was performed.

## Step 1 — production shell

Reference: `approved_current/09_focused_portrait_review_final.png`.
Saved asset: `streamlit_assets/rooms/focused_portrait_review_shell.png`.
Mode: imagegen precise-object-edit of the approved reference, opaque background.
The shell retains architecture and furniture while scientific content is live.

Generation prompt:

> Use case: precise-object-edit. Create a blank production background shell from this approved Focused Portrait Review museum mini-room reference. Preserve the EXACT room composition, canvas aspect, camera perspective, daylight, warm ivory/pale sage plaster, cherrywood conservation table, open doorway, brass fittings, empty floor, foreground books, chair and tufted bench. This is an interactive website background, so REMOVE ALL text, letters, numbers, navigation branding, chart marks, data plots and labels from every surface, leaving clean naturally textured blank material. Make the top navigation bar empty dark teal. Keep every physical frame, label plaque, paper print, book spine, light and table-edge selector in its exact position and size. Blank the five central portrait print image interiors to warm ivory paper, preserve their print borders and lighting. Blank the large upper central hand-penalty frame and the upper-right lightness frame to parchment. Blank the two drawing pages on the right blind-review stand. Remove the miniature portrait and hand drawing contents on the left wall to aged ivory paper but keep the mini frames. Preserve all furniture and architectural edges. No text anywhere, no replacement symbols or scientific imagery, no extra objects or panels. Match original reference as closely as possible outside these blanked content areas.

## Step 2 — exact evidence binding

The opening is R005: p269, HINT, canonical mixed damage, candidate
`candidate__hint_places2__canonical__p269__mixed_damage__c00`.
The original hand/control geometry contains 1,196 pixels in each support, with
zero overlap. Review crop: `[617,81,716,215]`; control crop:
`[605,576,704,710]`. Registered N34 R005 difference, review-panel, and
matched-control renditions are verified, never substituted for another review.

All 32 reviewed candidates retain their exact candidate, case, annotation,
control, and source-image joins. Clean, damaged, mask, and restored image bytes
are checked against producer hashes. D02 CSVs and its self-contained report are
verified against the producer artifact manifest. Original control designs,
lightness profiles, context matches, and adjusted associations are read from the
report's retained embedded CSVs, not reconstructed from a convenient region.

Recorded scope:

- 60 portraits screened, 36 included, 24 excluded.
- 91 annotations reviewed, 88 retained, 3 excluded.
- 1,265 anatomy–damage intersections; 292 eligible records.
- 45 distinct matched hand cases from 20 paintings; 53 annotation-control
  designs are not conflated with the 45 distinct cases.
- 12/12 worse-oriented primary hand estimates; 10/12 with BH q < .05.
- 32 blind review units from eight cases and four methods; 25 visible failures.
- 30 rendered-lightness profiles, 10 context matches, 24 adjusted associations:
  three negative chroma-error associations, 21 intervals crossing zero, and
  zero clearly positive associations.

Hand and lightness metrics have separate selectors. SSIM is control minus hand;
error metrics are hand minus control. PSNR lightness associations are
error-oriented. Full precision is retained in source details and CSV downloads.

Rendered lightness is not race, ethnicity, or identity. This audit does not
establish inherent model bias, conservation correctness, or expert validation.
The Codex-assisted blind review is explicitly bounded and separate from N27
automated flagging. Browser difference previews are exact absolute RGB
differences of verified source pixels, not new scientific measurements.
