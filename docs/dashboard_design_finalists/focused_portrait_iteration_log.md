# Focused Portrait Review — visual iterations

## Pass 1 — left study wall and book spines

Reference: `approved_current/09_focused_portrait_review_final.png`, checked
alongside the actual blank production shell. Addresses browser comments 1–14.

- Replaced the common 3-degree miniature rotation with five independent
  aperture bounds and four-corner clipping masks, preserving the frame mouldings.
- Images and the miniature anatomy canvas fill their apertures; the full
  annotation inspection remains unchanged and uncropped.
- Added individual plaque tilts, separate number/caption sizes, warm brown
  serif ink with subdued opacity and multiply blending into the paper.
- Matched each book spine's slope and lettering: muted gold/ivory on green,
  burgundy and blue, dark brown on the ochre Matched controls volume.
- No evidence, chart, navigation, background bitmap, or frozen-room changes.

Validation: eight focused tests passed; screening and annotation interactions
were opened and closed successfully in the browser. Screenshot:
`focused_portrait_cosmetic_pass_01.png`. This is a visual-review checkpoint,
not a freeze or publication.

## Pass 2 — original reference lettering

Addresses the subsequent nine comments requesting the details directly from
the reference. The five plaques and four book-spine labels now display actual
reference pixels, not recreated typography. A single native image is clipped
to nine disjoint regions at their original room coordinates. No recolouring,
opacity adjustment, additional rotation, or bitmap regeneration is applied.

Production asset: `streamlit_assets/rooms/focused_portrait_reference_details.png`.
It is a byte-for-byte copy of the approved reference, SHA-256:
`9dbf04cdc1d7171f72c969c34614475ab097fde86ad7b8f914ab0568fa334197`.
Only the nine requested regions are visible; the rest of the room remains live.
The previous text is retained for accessibility, and plaque buttons still open
the recorded evidence. If any corresponding recorded count changes, that
reference region is omitted and the live number is displayed instead.

Validation: nine focused tests passed, including source/asset byte equality
and stale-count fallback; the study drawer was opened successfully from a
reference plaque. Browser screenshot: `focused_portrait_cosmetic_pass_02.png`.

## Pass 3 — reference title, return sign and blind-review folio

- Extended the original-pixel overlay to the room heading/subtitles, the
  Trustworthiness return sign, Blind visual review header, four observation
  plaques, and the review selector strip including its arrows and divider.
- Retained the accessible headings and actual return anchor. Other parent-room
  routes retain live sign text rather than incorrectly displaying Trustworthiness.
- Split digits, contour, wrist, and texture into four independently clickable
  plaques, all opening the selected exact review evidence.
- Fitted both live folio canvases to the angled page interiors. The same layout
  applies across review selections; untransformed source context remains
  available in the inspection drawer.
- Replaced the overflowing result block with two reference-style summary lines
  plus a smaller live review ID/status/confidence/Codex-assisted line, aligned
  with the lower plaque. The 25/32 count remains data-bound.

Ten focused tests pass, including reference regions, parent-aware return labels,
four observation controls, folio styling hooks, and dynamic summary content.
Browser checks opened the digits review and clean-image drawer, switched to
R002 with correctly updated canvases and status, and followed the reference
return sign to the live Trustworthiness review room before restoring R005.
Trustworthiness's 28-file freeze remains unchanged. Screenshot:
`focused_portrait_cosmetic_pass_03.png`.

## Pass 4 — distinct observations, review transitions and print fitting

The four observation plaques previously opened the same general review drawer.
They now open category-specific findings: digit count/presence/fusion, contour,
wrist/arm discontinuity, or non-anatomical texture. Each view has an active
category indicator, recorded outcomes and source context. The underlying hand
crop remains shared: D02 does not supply four feature-localized masks/boxes.
The interface explicitly explains this and does not invent localized evidence.

Failure/counterexample selectors previously advanced through candidates, which
could be different models on the same painting. They now prefer another painting
within the requested recorded outcome, and open its review with ID, classification,
painting, method, damage and note. The general candidate selector still allows
all 32 exact records. Browser-verified transitions: R005 → R007 (visible failure,
p271) → R013 (acceptable, p284). Source records and classifications are unchanged.

Rendered-lightness controls now align with the angled wall heading. The findings
follow the selected metric's four recorded intervals, with subdued colour accents
for negative, zero-crossing, and positive intervals. All six metrics were checked:
chroma has three negative and one zero-crossing interval; the other five metrics
each have four intervals crossing zero. These are adjusted associations, not
demographic identity measurements or causal claims.

The five table prints have independent perspective-shaped aperture masks and
cover-fit previews; their source crop and full normalized canvas remain available
unaltered in the image drawer. All five caption plaques now use the exact reference
pixels, with matching click targets and accessible labels. The review summary has
shorter bounded lines, wrapping enabled, and an interior overflow boundary; checked
on failure and acceptable examples.

Validation: ten Python tests passed; Node tests passed for chart geometry, exact
pixel differences, distinct observation fields, class-preserving/different-painting
review transitions, and per-metric interval interpretation. Browser checks exercised
all four observation plaques, both review selectors, and all six lightness metrics.
Screenshots: `focused_portrait_cosmetic_pass_04.png` and
`focused_portrait_wrist_observation_preview.png`.

## Pass 5 — seamless heading, centred plaques and original report

Removed the rectangular reference-wall heading patch and replaced it with
transparent Times lettering matched to the reference hierarchy. The underlying
shell now supplies every wall pixel, so there is no patch boundary. Removed the
redundant breadcrumb; the door return link remains active.

The review plaque no longer says “Codex-assisted”; the full Methods & limits
drawer and original report retain the review provenance and limitations. Both
review and eligibility summaries are vertically/horizontally centred with
bounded line layouts. Eligibility uses three explicit lines rather than letting
“affected” spill out below the plaque. Resource plaques use Times typography;
Annotations and Methods & limits are reduced exactly 5% (.73 to .6935 cqw).

D02 report formerly navigated to a download beneath the room. It now replaces
the room with the complete checksum-verified original HTML report in a scrolling
frame, alongside the unchanged HTML download and a review-preserving return link.
No report content is regenerated or substituted. Browser inspection confirmed
the actual report heading, executive findings and report section navigation.

Validation: 11 Python tests, including byte-for-byte report display/download
checks; JavaScript syntax and existing Node tests pass. The 28-file
Trustworthiness freeze remains unchanged. Browser screenshots:
`focused_portrait_cosmetic_pass_05.png` and `focused_portrait_report_preview.png`.
