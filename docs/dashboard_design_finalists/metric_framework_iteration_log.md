# Metric Framework iteration log

Date: 2026-09-29  
Status: full spatial-inspection implementation verified and ready for inspection; visual iteration remains user-led

## Surprise tooltip cleanup and Arrakis canvas (2026-09-29)

- Removed Streamlit's optional help tooltip from Surprise me; the button's
  existing callback and painting-selection behavior remain unchanged.
- Added a decorative Arrakis painting inside the right canvas, with a warm
  sepia palette and upward-right wall perspective. No evidence assets replaced.
- Asset: `streamlit_assets/ornaments/arrakis_desert.png`, generated with the
  built-in image-generation tool and copied into the project.
- Generation prompt: "Use case: stylized-concept. Create a finished fine-art painting asset for a very narrow vertical museum wall canvas in a warm historic painting-restoration room. Subject: Arrakis from Dune, monumental sweeping ochre desert dunes, a distant sandworm crest emerging from sand, a tiny solitary cloaked traveler for scale, two faint moons high in dusty sky. Antique oil painting / sepia lithographic sensibility, expressive but restrained brush texture on aged linen, rich brown and burnt umber shadows, sandstone tan and muted honey highlights. Entire picture a unified warm brown palette, not orange neon. Composition portrait 1:3, tall cascading dunes, main readable motifs centered in narrow middle, scene extends to all edges. No frame, no room, no text, no typography, no logo, no watermark. It will appear at small size in a narrow angled canvas so favor strong simple beautiful silhouettes and atmospheric depth, not fine clutter. Generate just the painting, front-facing rectangular asset; do not apply perspective."
- 52 regression tests pass. Notebook and earlier rooms untouched.

## Plaque cleanup and Dune easter egg (2026-09-29)

- Masked the stray original gold border immediately above the angled plaque;
  its approved paper, text and angle remain unchanged.
- Added a transparent, code-native aged-gold Dune binding to the foreground
  book: Frank Herbert, Arrakis, twin moons, desert contours and Shai-Hulud.
  The existing leather stays visible; the engraving follows the cover's slope.
- Visually verified both changes in-browser; 51 tests pass. No notebooks,
  evidence behavior, earlier rooms or other approved details changed.

## Final lower-plaque direction clarification (2026-09-29)

- User explicitly requested left corners lower than right corners. The complete
  original plaque surface and its content now share one -2-degree vertical skew,
  anchored at the right edge. No other approved visual element changed.
- Verified visually in the browser; 50 regression tests pass. Browser DOM
  measurement calls timed out, so no numerical browser geometry claim is made.

## Cosmetic batch 6 — icons, board perspective and conservation sketch (2026-09-29)

- All seven icons move down .18cqw in closed and open states. Lens-label rules
  are unchanged. Cabinet heading/subheading follow the board's upward slope.
- Removed the added lower-plaque surface and skew: the shell's original border
  supplies the reference perspective, with a gentle .35-degree content slope.
- Added an original code-native sepia conservation sketch to the left canvas:
  portrait fragment, craquelure, inspection glass, brush and pigment studies.
  Its inset and perspective stay inside the existing canvas; it is decorative,
  not candidate evidence, and does not intercept any interaction.
- Browser verified all seven open states, compact/wide icon alignment, sketch
  loading and plaque containment. No console errors; 50 tests pass.
- Notebook, first two tabs, evidence calculations and lens labels untouched.

## Cosmetic batch 5 — cabinet alignment (2026-09-29)

- Open drawer paper and the lower evidence plaque follow a subtle -1.1 degree
  cabinet slope, reusing the original shell textures rather than new artwork.
- All seven labels move down by .18cqw (approximately two screen pixels), with
  their existing typography and effective angle preserved.
- Browser checked all seven open drawers at two widths: descriptions and
  collapsed evidence fit; expanded measurements scroll inside the plaque.
- 49 regression tests pass; no browser console errors. Earlier tabs, evidence
  logic, painting alignment, and the notebook are unchanged by this pass.

## Cosmetic batch 4 — evidence cabinet (2026-09-29)

- Replaced text glyphs with seven code-native, reference-style pictograms:
  mosaic, structural waves, eye, feature network, spatial sheet, woven texture,
  and framed layout.
- Warm serif headings follow the drawer's slight upward angle. Labels reserve
  clear space for the actual handles instead of drawing a second gold rectangle.
- Accordion faces are CSS views of the existing shell's closed wood drawer and
  open parchment drawer, including their original borders. All seven selections
  retain one open face and six closed faces. The open handle also reuses the shell.
- Validation caught the large data URI being dropped as a CSS custom property;
  a direct scoped stylesheet image declaration is used instead.
- Browser verified all seven open states at both desktop widths: every surface
  and handle loaded, every description fit, and no drawers overlapped. Functional
  region/lens rules and all other approved visual regions remain unchanged.

## Cosmetic batch 3 (2026-09-29)

- Quality-anchors copy is a single two-line block, centered and mapped to the
  plaque's upward baseline and slanted sides rather than separate grid items.
- Introduction uses larger leading, paragraph spacing and type, extending into
  the available wall area without changing its text.
- Seven region rows use the shell's existing ruled divisions, no additional
  separator borders. Icons show the selected painting with its actual registered
  support masks; whole-image uses the source thumbnail and patches add a grid.
- Evidence plaque uses inset bounds and warm serif type. Only named direction
  cues are colored. Metric, role, direction and limitation remain visible;
  calculation, values, source coordinates, scale and support explanation are
  retained under the keyboard-operable Measurements & support disclosure.
  Expanded content scrolls inside the plaque, never across the frame.
- Browser: all 37 enabled pairs checked at both large and compact desktop widths
  (74 layouts), with no collapsed horizontal or vertical overflow. Expanded
  content and the incompatible-region transition were verified. 47 regression
  tests pass; notebook hash unchanged. Earlier tabs and painting fit untouched.

## Cosmetic batch 2 (2026-09-29)

- Lifted selector and Surprise me by 0.35% of artboard height, so the correction
  scales with the room rather than a particular monitor's pixels.
- Metric-only navigation rules use the shared Palatino typography and remove
  browser link underlines; logo/search dimensions match the shared design.
- Ledger typography follows the left page's upward baseline and page skew.
  Current counts are preserved. The right page has its quality-anchors label,
  a code-native sepia botanical engraving, and the working archive link.
- Lower interpretation plaque uses centered warm serif text aligned with the
  plaque's tilt, with smaller type to maintain border clearance.
- Approved reference opened for this pass. Browser checks at two desktop widths;
  46 regression tests pass. Notebook checksum and first-two-tab source guards
  unchanged. Painting geometry, source assets, and evidence calculations untouched.

## Cosmetic batch 1 (2026-09-29)

Only the five approved annotations were addressed: centered italic serif case
identity on the existing plaque; transparent picker and Surprise me controls on
the shell's original plates; a parchment-toned searchable dropdown; full-canvas
frame fit; and the live inspection readout relocated into the evidence plaque.

The complete 768×768 registered canvas now maps to the rectangular frame opening
using shared horizontal/vertical display scales for the base image, evidence,
pointer and patch outlines. This is a presentation-only aspect-ratio adjustment;
no source pixels or scores are changed. Stored source padding remains visible.
Region changes no longer reframe the painting. The small lower plaque is exposed
by a notch in the painting's display clip, following its baked-in silhouette.
This supersedes the earlier fit-contain observation below for this approved batch.

Verified p018 and p055, region switching, searchable picker, Surprise me
(p055 → p092), pointer dragging, and equal image/frame bounds at two desktop
widths. All 45 regression tests pass, including first-two-tab source guards.
Notebook 35 retains SHA256
`77DBFB840B22DD590321FE11F75C8E926DBC85F02DCB797BD8BFACAFB1D7B673`.

## Spatial-inspection pass (2026-09-29)

The older "Open interaction/content questions" section below records the state
before this pass; it is not a description of the new controller.

Implemented:

- Seven lenses and seven regions with an explicit 49-pair contract: 37 enabled,
  12 prohibited. Every enabled pair resolves actual aligned spatial evidence.
- Reference/Damaged/Restored views share the selected comparison and source
  coordinate; they do not silently change the measurement definition.
- Draggable/keyboard loupe, 1.65× magnification, split CLIP/DINO and DINO/affinity
  views, exact support hatching, and snapping/outline for real local windows.
- Explicit invalid-region handling: clear old evidence, explain the incompatibility,
  recommend a compatible region, and wait for the user to select it.
- Dynamic metric names, calculations, units, directions, fixed scales, region
  summaries, window readouts and limitations.
- Exact local source/asset checksums and recipe/identity guards. No scalar-only or
  different-painting fallback. Companions are separate from frozen benchmark data.
- Painting choice retained in the URL on refresh; lens/region/view retained in
  tab-session storage. Painting changes remain fragment-scoped.

Browser checks completed so far:

- Default p018: all 37 enabled pairs in all three views (111 states); keyboard
  movement in each; all 12 prohibited pairs disabled with reasons.
- Pointer dragging in all 37 enabled pairs, including snapped patch windows.
- Incompatible transition clears old map/selection and exposes recommendation.
- Picker p018 → p001 and Surprise me p001 → p038 preserve filters and resolve the
  new painting's exact case, candidate, images and maps.
- Reload retains p001 after URL-persistence fix. Narrow/wide desktop viewport
  checks retain the source inspection position.

Functional issues found and corrected during validation:

- A hidden loupe was measured before display, creating an effectively empty canvas.
- Content geometry was not reaching the imported presentation helper consistently
  during Streamlit development reruns. The validated geometry is now an explicit
  stage attribute and the small presentation helper is refreshed independently.
- Invalid/error states could leave stale plaque metadata or an old enabled flag.
- Patch snapping lacked a visible source-window outline.
- The initial seam companion omitted the existing helper's Sobel /8 normalization;
  companion-only correction and numerical tests now enforce the convention.
- Explicit browser reload reset the painting even though filters persisted.
- Standalone navigation SVG images needed their own XML namespace and stroke styles.

Final coverage: all 300 paintings / 11,100 enabled pairs passed the data audit;
43 regression tests passed. The complete 111-state browser matrix also passed on
p001 (portrait), in addition to p018 (landscape), with source and plaque identity
checked in every state. The last registered painting p300 passed a live smoke
test. Details and limitations are recorded in `metric_framework_verification.md`.

Additional visual observations for the user-led cosmetic pass:

- Low-error maps can look nearly dark on the deliberately fixed scales; a future
  contrast treatment must disclose its mapping and preserve numeric interpretation.
- Portrait/landscape aspect ratios leave different mat space within the fixed
  main frame. Do not stretch source images to hide this.
- The current generated patch label casing (for example "Patch dINO") should be
  polished alongside the other typography work.
- The dense plaque may require scrolling at smaller sizes; keep all caveats
  accessible when improving its visual layout.

## Approved selection contract

- The room exposes exactly three public selection dimensions: **painting**, **region**, and **evidence lens**.
- Changing the painting resolves one deterministic teaching exhibit: case `canonical__{painting_id}__mixed_damage` and candidate `candidate__lama__{case_id}__c00`.
- The resolved exhibit is shown as identity in the **Featured case** plaque; case and model are not additional selectors.
- Resolution is fail-closed. A missing or ambiguous canonical case, LaMa candidate, restored image, signed-improvement map, local map, or semantic map is an application-contract error; the room must not silently substitute another case, model, or asset.
- Model comparisons such as HINT, Stable Diffusion, LaMa, and other candidate variants belong in Model Gallery or Case Explorer, not in the Metric Framework selection flow.
- The interaction order follows the approved layout: **change painting → choose an evidence lens → select a region → inspect the featured image**.

## Verified in this pass

- The room is a live `metric_framework` route, not the pending-room placeholder.
- Painting selection is populated from all 300 registered N34 paintings.
- Every painting resolves exactly one canonical mixed-damage case and its exact canonical LaMa `c00` candidate for this room.
- All 300 resolved exhibits provide a restored image, signed-improvement map, local colour map, and semantic display map.
- Changing the painting from p018 to p020 updated the image, thumbnails, case identity, and diagnostic map in place without changing the page URL or forcing a browser navigation.
- Reference, damaged, restored, and diagnostic imagery is loaded only from allowlisted producer paths; no nearest-neighbour or placeholder substitution is used.
- The decorative room shell is checksum-pinned and explicitly classified as non-scientific.
- The existing Foyer and Study Design source-fingerprint guards still pass.

## Open visual issues — intentionally not fixed yet

1. The lower portion of the introductory copy crowds the ledger/side-book area, especially at narrower desktop widths.
2. Long painting titles truncate heavily in the narrow painting selector.
3. Thumbnail captions sit close to the bench/foreground and need a clearer, consistent caption zone.
4. The expanded evidence-lens drawer competes with the selected-metric plaque at narrower widths.
5. The evidence-cabinet heading wraps more aggressively than the approved reference at narrower widths.
6. Region labels, policy legend copy, and the selected-metric plaque become too small/dense when the artboard is scaled down.
7. The fixed 1672:941 artboard leaves unused dark space below it in tall, narrow preview panes.
8. The native painting selector is a Streamlit sibling of the artboard rather than a descendant of it; its positioning can drift from the shell when the preview width changes.
9. The current sub-780px rule depends on a 760px minimum-width artboard and horizontal scrolling rather than the approved mobile reading order.

## Open interaction/content questions — intentionally deferred

1. Region selection currently changes the active region state and policy role, but it does not yet swap to a region-specific raster because those distinct display rasters are not uniformly present for every candidate.
2. Pixel, structure, perceptual, and learned-feature lenses expose the appropriate metric families but do not yet surface candidate-specific numeric rows.
3. The region, evidence-lens, and Reference/Damaged/Restored controls render in the approved locations, but live browser QA did not observe their client-only state updates after the fragment rendered. Treat those controls as not yet fully wired; do not claim that they filter evidence until the next controlled interaction pass.
4. The selected-metric plaque remains fixed to Signed improvement instead of reflecting every control choice.
5. Room copy, lens definitions, region groups, and policy-ledger counts are presently hardcoded from the approved contract rather than rendered directly from the registered policy rows.
6. Local evidence files are constrained to exact producer paths, but the file helper presently compares each file to a freshly observed hash rather than a separately recorded package checksum.

## Protected boundaries

- Do not modify or execute `notebooks/35_dashboard_and_deployment_validation.ipynb` while room implementation is in progress.
- Do not alter the approved Exhibition Foyer or Study Design source regions while iterating on Metric Framework.
- The Batch 1/2 notebook reload error remains outside this iteration by user instruction.
