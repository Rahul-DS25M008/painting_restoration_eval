# Controlled-300 Dashboard Page Contracts

**Purpose:** Preserve the room-by-room content and interaction decisions made
before Notebook 34 packages or implements the Controlled-300 dashboard.

**Implementation boundary:** These contracts authorize design planning only.
The live Controlled-50 application remains unchanged until all eight rooms are
approved, the required remote assets are audited, Notebook 34 is rebuilt, and
Notebook 35 validates the replacement.

**Evidence authority:** Exact producer paths, row selectors, display states,
and required Notebook 34 derivations are recorded in
[`controlled_300_producer_artifact_map.md`](controlled_300_producer_artifact_map.md).
That map is binding wherever a mockup or general page description does not
identify an exact artifact. Immutable transport, checksum and missing-asset
rules are recorded in
[`controlled_300_remote_asset_audit.md`](controlled_300_remote_asset_audit.md).
Runtime loading, caching, retry, responsive-layout and degraded-mode rules are
recorded in
[`controlled_300_runtime_loading_contract.md`](controlled_300_runtime_loading_contract.md).
The final package schema, binding records, execution plan and visual-fidelity
gate are recorded in
[`controlled_300_n34_implementation_contract.md`](controlled_300_n34_implementation_contract.md).

## Shared rules

- Use clear, everyday language in the primary reading path.
- Explain necessary technical terms where they first appear or inside an
  optional detail view.
- Keep one dominant painting-first interaction per room.
- Pair every result with a nearby statement of what it does not establish.
- Never turn visual plausibility, metric performance, stability, or a review
  flag into historical correctness, conservation approval, calibrated
  confidence, or universal model superiority.
- Display exact source paintings and generated evidence in the implemented
  dashboard. Generated mock imagery is a layout reference only.
- Do not render a component classified as `unsupported_until_derived` until
  Notebook 34 creates, validates, hashes, and registers the named derivative.
  Never substitute a visually similar case or temporary file.
- Resolve remote evidence only at a full immutable Git/Hugging Face revision,
  verify its expected size and SHA-256 before display, and show an explicit
  unavailable or integrity-error state when the exact artifact cannot be
  verified. Never fall back to a neighbouring identity or mock image.
- Load only the active room and explicitly requested evidence layer. Keep the
  Foyer and explanatory context locally usable without network access; hidden
  rooms, tabs, drawers and unsubmitted selectors must not fetch remote bytes.

## Cross-page consistency gate

**Status:** Completed against the Controlled-300 repository evidence on
2026-09-28.

The canonical public name is **Painting Restoration Evidence Museum**. The
approved page-specific images define composition, atmosphere and interaction
hierarchy; they are not deployable page backgrounds or scientific records.
Their illustrative paintings, plots, labels and values must be replaced by
live components backed by registered assets. Where illustrative text differs
from this contract or a producer record, the producer record and this corrected
contract take precedence.

A checksum-pinned N35 decorative shell may reproduce architecture and lighting
only after all mock text, controls and scientific-looking content are removed.
The shell is hidden from assistive technology and all meaningful page content
is rendered as live, accessible, evidence-bound components above it.

### Fixed navigation and route state

The primary navigation is always, in this order: `Exhibition Foyer`, `Study
Design`, `Metric Framework`, `Model Gallery`, `Stability Lab`,
`Trustworthiness`, `Case Explorer`, and `Research Archive`. `D02` is the single
`Trustworthiness / Focused portrait review` subroute, never a ninth tab.

Cross-room links preserve the exact selection rather than reopening a room at
its default. The minimum portable state is `painting_id`, `case_id`,
`candidate_id`, `model_id`, optional `seed`, optional `prompt_variant_id`,
`metric_name`, `region_id`, `evidence_layer`, and `return_room`. Routes into the
focused portrait review also preserve the applicable `annotation_id`,
`hand_control_id`, `review_unit_id`, and `blind_review_code`. An unavailable destination must explain
why it is unavailable; it must never substitute a different case, model,
candidate, metric, region, report, seed, prompt, annotation, control, or review
silently.

### Fixed public vocabulary and populations

| Public label | Exact meaning |
|---|---|
| 300 paintings | The accepted collection, balanced as 60 paintings in each of five broad visual categories. |
| Five broad visual categories | `Abstraction / Surrealism`, `Architecture / Structured`, `High Texture / Brushwork`, `Landscape / Natural`, and `Portrait / Figure`; these are study groupings, not historical styles. |
| 3,425 registered experimental cases | All registered cases: 1,500 canonical, 245 damage-size, 525 mask-placement and 1,155 procedural-degradation cases. |
| 2,620 method-eligible cases | Cases completed by each of the four full-scope methods: 1,500 canonical cases, including 300 unchanged controls, plus 245 damage-size, 525 mask-placement and 350 eligible degradation cases. Public copy must explain that eligibility is computational, not conservation approval. |
| Four full-scope methods | Telea, LaMa, HINT and Stable Diffusion 1.5. Stable Diffusion's ordinary matched comparison uses `p00_generic` and seed 2026. |
| Bounded SDXL branch | 35 scheduled cases, 24 completed candidates, one timeout and ten budget skips; never a fifth full-scope method. |
| 10,504 comparison candidates | 10,480 full-scope primary candidates plus 24 bounded SDXL candidates. |
| 13,879 indexed candidates | The union used for explanation and inspection: 10,504 comparison candidates plus repeated-seed additions after removing overlap. `Indexed` or `available for inspection` must replace wording that could imply quality approval. |
| Repeated-seed population | 1,025 supported four-seed Stable Diffusion groups, 4,100 memberships and 6,150 unordered pairs; 725 candidates overlap the primary population and 3,375 are uncertainty-only. |
| N32 report population | 300 painting reports plus 30 selected detailed case reports = 330 case/painting reports; adding one collection index gives 331 browsable N32 reports. |
| Other reports | Five N31 model reports and one N33 final report remain separate from the 331 N32 records. |
| Final synthesis | N33 retains 24 final figures, 49 evidence claims, 18 limitations and 536 of 536 passed checks. |
| External publication registry | 2,653 individually published artifacts are remotely verified. Verified bundled releases use separate release records and are not included in that row count. |

Use `clean digital reference` or the compact label `clean reference` in
analytical rooms. `Original` is reserved for artwork metadata or carefully
qualified source context; the controlled clean image is not the unknowable
historical original. Use `mask placement`, not `mask position`. Do not use
copy such as `a clearer past` or `richer truth`, which can imply historical
recovery; prefer `clearer evidence`, `richer view` or similarly bounded text.

### Corrected implementation reading of the approved mockups

- The existing N34/N35 package and configs are a frozen Controlled-50 baseline,
  not a data source to relabel. N34 must rebuild the package from the completed
  Controlled-300 producers.
- Grouped Metric Framework region labels must expand to their canonical N08
  rows and roles; a group containing mixed primary and diagnostic rows cannot
  receive one misleading status colour.
- Stability Lab must distinguish the four restoration-eligible procedural
  families from generated degradation-only diagnostics.
- Trustworthiness must keep same-case comparison peers separate from the
  threshold-fitting reference stratum and expose each flag's own derivation.
- D02 must use the exact selected case, annotation, matched control, metric and
  review record; approximate charts or convenient crops are prohibited.
- Case reports are conditional: every painting has a painting report, but only
  30 selected cases have detailed case reports.
- Research Archive must resolve the real per-artifact GitHub or Hugging Face
  location. Destination labels describe common roles, not exclusive storage
  classes.

## 01 — Exhibition Foyer

**Status:** Approved and frozen on 2026-09-27  
**Visual authority:**
[03_exhibition_foyer_final.png](approved_current/03_exhibition_foyer_final.png)

### Purpose

Orient a visitor who has no prior knowledge of the thesis. The visitor should
understand what is being tested, why a visually convincing restoration is not
enough, and how to begin exploring within approximately twenty seconds.

### Approved opening

**Question:** *How should we judge an AI-restored painting?*

> This thesis tests digital restoration methods by applying controlled damage
> to 300 paintings. We compare the restored images, measure what changed and
> check whether the results stay consistent—but a convincing image is not
> automatically historically correct.

**Boundary statement:** *Visual plausibility is not the same as restoration
trustworthiness.*

### Approved scope indicators

- 300 paintings;
- five broad visual categories;
- 3,425 registered experimental cases; and
- four full-scope methods plus a bounded SDXL branch.

### Approved visual hierarchy

- The exact repository painting is the dominant exhibit. The current layout
  reference uses `p001`, *Juan de Pareja* by Diego Velázquez (1650).
- The guided-tour and free-exploration controls resemble museum exhibit
  controls rather than commercial call-to-action buttons.
- The compact collection strip and room route remain subordinate to the
  painting, leaving a visible band of museum floor above them.
- The public implementation uses a museum-catalogue display serif and a clear
  humanist sans-serif for controls and explanatory text.

### Approved route interaction

- The compact eight-room route remains visible at the bottom of the Foyer.
- Hovering or keyboard-focusing a room highlights its stop and opens a small
  preview above the route without navigating.
- The preview contains the room name, its plain-language question, a short
  explanation, one small evidence thumbnail, and an explicit `Enter room`
  action.
- Every preview reuses that room's exact approved opening question; shortened
  illustrative questions from the mockups are not separate page definitions.
- Navigation occurs only after activating `Enter room`.
- On touch devices, the first tap opens the preview and the second explicit
  action enters the room.
- The route always identifies `You are here: Exhibition Foyer`.

### Guided tour

- `Take the guided tour · about 6 min` starts a skippable in-application path
  through all eight rooms.
- `Explore freely` leaves every room directly accessible.
- The tour presents one question, one real visual, one supported takeaway, and
  one limitation per room. It is not an autoplay video.
- The Trustworthiness stop introduces the focused portrait audit and offers an
  explicit optional D02 detour. The detour does not become a ninth tour room
  and does not interrupt completion of the eight-room path.

### Deliberately excluded from the Foyer

Full metric definitions, threshold formulae, ranking tables, uncertainty
grids, D02 statistics, raw provenance, report catalogues, notebook identifiers,
and download controls remain in their relevant later rooms.

## 02 — Study Design

**Status:** Approved and frozen on 2026-09-28  
**Visual authority:**
[04_study_design_final.png](approved_current/04_study_design_final.png)

### Purpose

Explain what entered the study, how the controlled experiment branches differ,
and why equal treatment makes comparison possible. This room describes the
design; it does not reveal model winners or treat eligibility as success.

### Approved opening

**Question:** *What did we test, and how did we keep the comparison fair?*

> We started with 300 paintings, divided evenly across five broad visual
> categories. Every painting received the same core tests, while smaller
> balanced experiments examined damage size, mask placement and other image
> changes.

**Boundary statement:** *Equal category sizes make comparisons easier. They do
not make the collection representative of every artistic period, culture or
style.*

### Approved scope indicators

The following four facts appear as labelled research catalogues on the
foreground bench rather than as dashboard cards:

- 300 paintings — 60 per category;
- five core conditions — including the unchanged control;
- 3,425 registered cases; and
- 2,620 method-eligible cases — cases processed by all four full-scope
  computational methods, not paintings judged ready for conservation.

### Approved dominant interaction

`Follow one painting through the study` uses one exact repository painting as
the anchor and exposes four independent choices under `Choose a study path`:

- `Core test`;
- `Damage size`;
- `Mask placement`; and
- `Other image changes`.

These choices are parallel experiment branches, not sequential stages. They
must therefore use separate archival specimen tabs with branch-specific
conservation glyphs. Do not use a connected line, ordered dots, step numbers,
or other progress-stepper language.

The selected `Core test` view is labelled `Clean reference + five core
conditions`. It shows the clean digital reference beside one selected
controlled condition and retains a compact selector for:

- clean reference;
- unchanged control;
- thin scratch;
- small loss;
- large loss; and
- mixed damage.

The status plaque explains whether the selected case is `Suitable for
restoration testing` or `Studied as a degradation instead`, together with a
short reason. It expresses methodological routing only and must not imply that
the restoration succeeded. Do not call the generated damage `realistic`;
describe it as controlled synthetic damage valid under the registered
protocol.

### Approved collection control

`The collection` is a compact dark-timber catalogue cabinet on the lower-left
side. It contains five drawer choices, each representing 60 paintings:

- Abstraction / Surrealism;
- Architecture / Structured;
- High Texture / Brushwork;
- Landscape / Natural; and
- Portrait / Figure.

The selected drawer uses a pale archival-paper front; inactive drawers recede
into the timber. The control must remain visually subordinate to the painting
and must not stretch across the viewport.

### Study Notes

The technical explanations live in a narrow architectural card catalogue,
with only the selected drawer expanded:

- how paintings were selected;
- how images were prepared;
- how controlled damage was created;
- how focused tests work;
- why some cases are not restoration tasks; and
- how the portrait audit was designed.

Primary reading stays in plain language. Exact mask targets, preprocessing
rules, experiment counts, eligibility logic and other implementation detail
belong inside these drawers.

### Focused portrait audit

The D02 branch receives its own small recessed side alcove so it is visibly
supplemental rather than part of the 3,425-case registry. The concise label
records:

- 60 portraits screened;
- 45 matched hand cases;
- 20 paintings; and
- existing restoration results were reused.

The room points visitors to Trustworthiness for findings and to the Research
Archive for the complete protocol. It does not present D02 conclusions here.

### Approved spatial and material treatment

- Preserve a large calm central floor and strong gallery depth.
- Keep information on the perimeter and reveal detail progressively.
- Use matte plaster, lightly worn timber, linen, archival paper and restrained
  track lighting rather than a glossy luxury-showroom finish.
- Keep the painting pair as the dominant evidence and avoid an A4/report grid.
- Display the four scope facts as natural museum objects on the bench.
- Use the exact repository images in production; generated paintings in the
  mock remain layout placeholders.

### Explicit limitations

- The five visual categories are broad study groupings, not formal historical
  styles.
- Controlled synthetic damage is not physical deterioration.
- Restoration eligibility is not restoration success or conservation
  approval.
- Rendered skin lightness is not race, ethnicity or identity.

### Deliberately excluded from Study Design

Model rankings, restoration-quality conclusions, metric winners, uncertainty
findings, trustworthiness-flag prevalence and D02 outcome comparisons remain in
their corresponding later rooms.

## 03 — Metric Framework

**Status:** Approved on 2026-09-28; three-selection flow amended on 2026-09-29
**Visual authority:**
[05_metric_framework_final.png](approved_current/05_metric_framework_final.png)

### Purpose

Show why the apparent quality of one restoration can change when the visitor
asks a different measurement question or inspects a different region. This
room teaches visitors to read complementary measurements rather than collapse
them into one universal score.

### Approved opening

**Question:** *Why can the conclusion change when the metric or region
changes?*

> No single number can judge a restoration. Different measurements examine
> pixels, structure, visual similarity, texture, colour, seams and unintended
> changes. Each measure is only meaningful in the regions it was designed to
> examine.

**Boundary statement:** *Different metrics answer different questions.
Disagreement is evidence to inspect—not noise to average away.*

### Approved dominant interaction

The central painting remains the dominant exhibit. A movable inspection lens
reveals one selected diagnostic map over the same painting while the visitor
chooses exactly three public dimensions, in order:

1. a painting;
2. an evidence lens; and
3. a region for which that measurement is valid.

`p018 · mixed damage · LaMa` is the curated opening example. For every selected
painting, this room deterministically resolves the exact canonical mixed-damage
case and its canonical LaMa `c00` candidate. `Change painting` provides
searchable access to all 300 paintings and `Surprise me` advances to another
registered painting while preserving that same teaching-case rule. Resolution
is fail-closed: the room must never silently substitute another case, model or
asset.

Damage-case and model/candidate names are provenance in the `Featured case`
plaque, not additional selectors. `binary_missing_region` is internal benchmark
metadata rather than a public filter. Model comparisons such as Telea, LaMa,
HINT, Stable Diffusion and SDXL belong in Model Gallery or Case Explorer. Large
diagnostic bundles may be fetched lazily and cached per painting.

The painting itself must not carry a permanent colour scale. Interpretation
lives in the compact selected-metric plaque beside the exhibit so that the
artwork remains visually primary.

### Approved evidence lenses

Selecting a lens expands its drawer and reveals its exact measurements plus a
one- or two-line plain-language explanation:

- `Pixel difference` — MAE, MSE and PSNR;
- `Structure` — SSIM;
- `Perceptual similarity` — LPIPS;
- `Learned visual features` — CLIP and DINOv2 cosine similarity;
- `Spatial change` — absolute RGB error, signed improvement and changed-pixel
  fraction;
- `Texture, colour & seams` — LBP, Gabor and GLCM texture measures, ΔE2000 and
  boundary-gradient mismatch; and
- `Local meaning & layout` — local DINO similarity and structural-affinity
  correlation.

These seven public teaching lenses group the 13 registered N08 metric
families; they are not seven replacement metric families. Repeated-seed
uncertainty remains a separate Stability Lab concept rather than an eighth
quality lens.

The primary interface groups the available locations into understandable
choices: whole image, painting content, damaged area, damage crop, boundary,
outside repair and local patches. The literal 11-region policy remains in the
optional full ledger rather than crowding the main interaction.

Every grouped location expands to the canonical region rows and shows the role
for the active metric family. A group may not receive one role or colour when
its children differ. For `Spatial change`, N08 defines `content_region`,
`masked_region`, `boundary_ring` and `outside_mask_content` as primary;
`full_image`, `mask_bbox_crop`, `inner_boundary_band`,
`outer_boundary_band`, `outside_boundary_ring`, `patch_window` and the
synthetic-only `degradation_support` are diagnostic. The public legend reads
`Primary — headline evidence`, `Diagnostic — supporting evidence` and
`Prohibited — not defensible for this metric and region`; it must not imply
that diagnostic evidence is invalid.

### Selected-map interpretation

The opening example uses `Signed improvement`, calculated as:

`damaged reference error − restored reference error`

Its compact side plaque explains:

- blue / positive — restoration is closer to the clean digital reference;
- red / negative — restoration is farther from that reference;
- neutral / zero — the measured reference error is unchanged; and
- grey — outside the selected region or not evaluated.

The plaque must also state that this measurement cannot establish historical
correctness. Its wording remains concise and must not collide with the nearby
`Same restoration. Different question.` interpretation plaque.

### Metric-policy ledger

The open research ledger records the validated policy without presenting it as
a scorecard:

- 13 metric families;
- 11 evaluation regions;
- 143 declared metric–region combinations;
- 39 primary and 47 diagnostic combinations allowed, for 86 allowed in total;
- 57 combinations prohibited; and
- 11 quality anchors kept separate from the metric–region policy.

The previous illustrative phrase `17 evidence families` is stale and must not
return in the implementation.

### Explicit limitations

- The clean reference is the controlled pre-damage digital image, not
  historical ground truth.
- No metric can establish authenticity, artist intent or conservation
  approval.
- No universal score is calculated.
- Texture measurements are not brushstroke authentication.
- Uncertainty or disagreement is not calibrated confidence.
- Statistical conclusions treat the painting, rather than every generated
  image, as the independent unit.

### Deliberately excluded from Metric Framework

Overall model conclusions belong in Model Gallery; repeated-seed and
damage-size behaviour belongs in Stability Lab; derived warning thresholds and
flag prevalence belong in Trustworthiness; complete case inspection belongs in
Case Explorer; and equations, policy tables and full provenance belong in
Research Archive.

## 04 — Model Gallery

**Status:** Approved and frozen on 2026-09-28  
**Visual authority:**
[06_model_gallery_final.png](approved_current/06_model_gallery_final.png)

### Purpose

Let visitors compare how the four full-scope restoration methods rebuild the
same controlled loss. The room presents their different assumptions and
trade-offs without turning separate measurements into one score or declaring a
universal winner.

### Approved opening

**Question:** *How do different restoration methods rebuild the same loss?*

> The four methods receive the same damaged painting and mask, but they rebuild
> the missing region in different ways. Compare the result, inspect the local
> evidence and then open the full model record when more detail is needed.

**Boundary statement:** *A convincing completion is a candidate to inspect—not
recovered historical truth.*

### Approved spatial interaction

The page is a circular restoration rotunda, not another flat comparison grid.
A damaged painting stands on the central easel and four coloured floor routes
lead to four architectural alcoves:

- `Telea` — classical, local and deterministic;
- `LaMa` — learned, context-aware and deterministic;
- `HINT` — learned, mask-aware transformer and deterministic; and
- `Stable Diffusion` — prompt-conditioned and stochastic.

The curated opening is `p018 · mixed damage`, because exact outputs are
available for all four full-scope methods and the bounded SDXL study. Visitors
can change the painting, damage case and evidence view using tactile specimen
drawers on the foreground curator table. The selected method receives a short
plain-language record and a link to its complete configuration and evidence.

The production page must expose only cases that genuinely exist for the
selected method. Selecting a method changes the active alcove and the evidence
on the curator table; it must not silently substitute another painting,
damage condition, seed or prompt.

### Full-scope comparison

The four primary methods cover the 2,620 method-eligible Controlled-300
cases. Their roles must remain explicit:

- Telea is a fast classical neighbourhood-based baseline;
- LaMa is a learned large-mask inpainting method that uses broader image
  context;
- HINT adds a heritage-oriented, mask-aware transformer capability that was
  selected over MAT in the separate decision study; and
- Stable Diffusion tests prompt-conditioned generative restoration and retains
  its seed and prompt identity.

The headline comparison may state that LaMa led 10 of the 11 separate quality
anchors while Telea led crop SSIM in the completed comparison. It must
explain that equivalent masked MAE/spatial-error scalars correspond to nine
LaMa wins among ten distinct scalar quantities, not independent votes, and
immediately retain the qualifiers `separate comparisons` and `no combined
score`. Results remain conditional on this dataset, controlled damage, region
policy and metric family.

That headline is always labelled `Overall registered comparison — 300
paintings / 2,620 method-eligible cases`. It must remain visually separate from
the active `This case` selector and evidence. Changing the active case cannot
make the population result appear to be a score for that case.

Recorded median runtimes may be shown as operational evidence for the recorded
workstation: Telea 0.519 seconds, LaMa 1.451 seconds, HINT 6.677 seconds and
Stable Diffusion 8.620 seconds. They are not portable hardware benchmarks and
must not enter the quality ranking.

### Bounded SDXL study

SDXL is a separate low conservation-study vitrine rather than a fifth full
alcove. It records:

- 35 scheduled cases;
- 24 completed cases;
- one timed-out case; and
- ten cases skipped under the approved compute budget.

It is not included in the full-scope ranking. For a selected painting with an
SDXL result, the low angled vitrine opens and displays the exact result. For any
painting without one, the vitrine closes and explains that the evidence is
unavailable. Its position must remain below and outside the Stable Diffusion
alcove's sightline, and it must never create a fifth floor route. The recorded
median of 198.031 seconds describes only the completed bounded run on the
recorded workstation.

### Optional evidence drawers

- `Why was HINT selected?` opens the HINT-versus-MAT decision evidence without
  repeating the whole decision notebook.
- `Open full model record` reveals configuration, weights, prompt/seed where
  applicable, runtime context, licensing notes and source lineage.
- The evidence selector may show one valid local comparison such as crop SSIM,
  but detailed metric education remains in Metric Framework.

### Explicit limitations

- A plausible restoration is not proof of the original painted content.
- Metric leadership is conditional and is not universal model superiority.
- The clean image is a controlled digital reference, not historical ground
  truth.
- HINT's heritage orientation does not constitute conservation approval.
- Stable Diffusion seed variation is empirical disagreement, not calibrated
  confidence.
- SDXL is a bounded feasibility study and must not be presented as though it
  covers all 2,620 eligible cases.
- Runtime depends on hardware, environment and execution conditions.

### Deliberately excluded from Model Gallery

Repeated-seed, damage-size and mask-placement stress tests belong in Stability
Lab; warning thresholds and flag prevalence belong in Trustworthiness; complete
case-level diagnostic inspection belongs in Case Explorer; and full model
cards, checksums, notebook lineage and downloadable bundles belong in Research
Archive.

## 05 — Stability Lab

**Status:** Approved and frozen on 2026-09-28  
**Visual authority:**
[07_stability_lab_final.png](approved_current/07_stability_lab_final.png)

### Purpose

Let visitors replay controlled changes and see whether a measured restoration
behaviour remains similar. The room keeps four different ideas separate:
damage-size sensitivity, mask-placement robustness, procedural-degradation
stress and repeated-seed variability.

### Approved opening

**Question:** *How much does a restoration change when we change the test?*

> A restoration may look convincing once but behave differently when the
> damaged area grows, the mask moves, the input changes or Stable Diffusion
> uses another seed. Select one test and see what stays consistent.

**Boundary statement:** *Stable here means less change under this controlled
test—not historically correct, safe to conserve or certain.*

### Approved dominant interaction

The room is an after-hours kinetic conservation atelier, not a conventional
dashboard. The selected damaged input and restoration appear upright,
rectilinear and equally sized on a straight, front-facing conservation light
wall. The curated opening is:

`p018 · Damage size · 20% · LaMa · spatial masked error`

This is an intentionally notable observed trajectory: p018 with LaMa had the
steepest observed painting-level adverse slope for this measure. It is labelled
as an example, not a universal threshold.

Three physical test instruments remain visible around the comparison:

- a brass aperture rail with seven stops for `Damage size`;
- a five-position registration wheel for `Mask placement`; and
- a bell-jar specimen trolley for `Other image changes`.

They are parallel choices, not ordered stages. The selected aperture is
mechanically aimed at the damaged-input frame but must never cast a beam or
overlay across the painting. A separate contact-sheet drawer exposes
`Repeated seeds · Stable Diffusion only` where four-seed evidence exists.

If the active method is deterministic, the repeated-seed drawer is disabled
with `Stable Diffusion only — switch method`. Activating it requires an
explicit method change and must never substitute Stable Diffusion silently.

The bell-jar trolley names the four restoration-eligible procedural families:
`Dirt / dust`, `Partial transparency`, `Water stain`, and `Water stain + dirt`.
Other generated families such as blur, fading or colour-shift diagnostics may
appear only in a separately labelled `Not an inpainting task` drawer and must
not inherit restoration rankings.

Painting, method and evidence selectors live on a small registrar's desk rather
than directly beneath the artwork. A single clipped trajectory is shown for the
active test; the page must not display every stress-test chart at once.

### Approved evidence populations

The card-catalogue Test ledger retains the exact populations while keeping them
secondary to the visual comparison:

- **Damage size:** 35 paintings, seven per broad visual category; seven nested
  levels at 2%, 4%, 6%, 8%, 10%, 15% and 20%; 245 cases and 980 four-method
  candidates.
- **Mask placement:** 35 paintings; three fixed family/area conditions and five
  variants; 105 matched groups, 525 cases and 2,100 four-method candidates.
- **Other image changes:** 1,155 generated procedural-degradation inputs, of
  which 350 localized cases are restoration-eligible; 1,400 four-method
  candidates plus 11 bounded SDXL candidates. Both `1,155 generated` and `350
  eligible for restoration comparison` remain visible so the denominator is
  not lost.
- **Repeated seeds:** 1,025 supported four-seed Stable Diffusion groups across
  the canonical and damage-size experiments; 4,100 candidate memberships and
  6,150 unordered pairs.

The 35 paintings are the independent units for the three focused stress tests.
Their repeated cases, levels, variants and candidates are not additional
independent paintings.

### Approved concise findings

- As damage grew, LaMa had the lowest adverse slope on 5 of 11 separate quality
  anchors, Stable Diffusion on 4, Telea on 2 and HINT on 0. LaMa ranked first at
  all seven requested sizes, but metrics and paintings still disagreed.
- All five main Stable Diffusion disagreement components increased with damage
  size; four met the corrected significance rule.
- Under mask movement, LaMa had the lowest overall within-group median absolute
  deviation on 10 of 11 anchors and Telea on one. The anchor winner changed in
  625 of 1,155 group–anchor comparisons.
- Under eligible procedural degradations, LaMa led all four eligible families
  and 8 of 11 separate anchors. Exact compositing changed zero pixels outside
  effect masks, which verifies input construction rather than successful
  repair.

These statements remain separate findings. The room must not construct a
combined quality, stability, uncertainty or trust score.

### Approved spatial and material treatment

- Use a calm after-hours palette: chalky slate, muted aubergine, indigo shadow,
  worn teal cloth, oxblood accents, walnut and aged brass.
- Combine cool night-window light with small pools of warm task light; avoid a
  glossy blue control-room appearance.
- Preserve a broad empty foreground and visible window architecture.
- Keep the mask wheel, seed drawer and degradation specimens close enough to
  the main comparison for their labels to remain readable.
- Keep the full-size Test ledger on the far-right wall.
- Use the coloured book spines only as quiet micro-guides: `Observe the
  change`, `Measure the region`, `Question the result`, `Preserve the evidence`,
  `Analyse the pattern`, `Compare the methods` and `Respect the limits`.

### Explicit limitations

- Repeated-seed disagreement is an empirical variability proxy, not calibrated
  confidence; low disagreement can still mean consistently wrong output.
- Repeated-seed evidence applies only to supported Stable Diffusion groups. It
  must not be attached to deterministic methods, mask-robustness cases or
  degradation cases by association.
- Mask-placement family and area are deliberately paired, so their independent
  effects cannot be separated in this experiment.
- Procedural RGB degradation is not physical ageing, material chemistry or a
  conservation treatment simulation.
- The clean image is a controlled digital reference, not historical ground
  truth.
- Seven paintings per broad category support balanced coverage, not an
  independent art-historical style effect.
- SDXL evidence remains bounded and descriptive.

### Deliberately excluded from Stability Lab

Derived review flags and their fitted thresholds belong in Trustworthiness;
full diagnostic inspection of an individual restoration belongs in Case
Explorer; and complete statistical tables, model configuration, notebook
lineage and downloadable evidence belong in Research Archive.

## 06 — Trustworthiness

**Status:** Approved and frozen on 2026-09-28  
**Visual authority:**
[08_trustworthiness_final.png](approved_current/08_trustworthiness_final.png)

### Purpose

Explain why a restoration received an operational review flag, show the
evidence and comparison rule that produced it, and keep the recommendation
traceable. The page must never turn the flags into a universal trust score,
probability of failure, expert verdict or conservation approval.

### Approved opening

**Question:** *Why did this restoration receive a review flag?*

> Flags help us decide what to inspect. They are not probabilities, expert
> verdicts, or proof that a restoration is right or wrong.

The approved opening candidate is:

`p002 · loss_large · Stable Diffusion · seed 2026`

The exact candidate identity is
`sd15__p00__s2026__29ff258ff921`. The selected-record drawer must show it;
the shorter public label is not a substitute for identity.

Its evidence route is presented as six physical review stations rather than a
dashboard-card grid:

1. candidate evidence;
2. fair comparison group;
3. threshold;
4. failure category;
5. review flags; and
6. recommendation.

### Candidate finding and filtering

The selected clean reference, damaged input and restoration appear together
in the left evidence cabinet. Because the union contains 13,879 candidates, a
single flat candidate dropdown is prohibited. The approved angled catalogue
tray supports progressive filtering by broad category, painting, damage or
case, method and seed or prompt variant, plus direct candidate-ID search.

The implemented control may expose the more diagnostic fields `review action`,
`flag or failure category`, `experiment` and `population role` under an
optional `More filters` drawer. It must always retain the exact candidate ID
and must not silently substitute a different seed, prompt arm, case or model.

### Fair comparison and threshold scope

Two related populations must remain distinguishable:

- **Matched primary comparison:** the same `case_id`, one approved primary
  candidate for each full method, and the same experiment. Stable Diffusion is
  fixed to the canonical prompt arm and seed 2026 for this ordinary comparison;
  extra seeds and bounded SDXL remain separate.
- **Threshold-fitting stratum:** the same experiment, indicator, region and
  summary statistic. Uncertainty evidence additionally matches the prompt arm.
  Ordinary fitting uses eligible non-zero primary candidates and excludes
  bounded SDXL; uncertainty fitting uses eligible repeated-seed groups.

The interface therefore exposes two nested records rather than one ambiguous
`fair comparison` box: `Comparison peers` shows the same-case four-method
comparison, while `Threshold reference stratum` shows the population used to
fit the selected indicator boundary.

The public view may use short drawer labels such as `Same experiment`, `Same
indicator`, `Same region + statistic` and `Eligible non-zero cases`, but its
detail view must expose the exact field names and whether the unit is an
eligible candidate or an eligible seed group. The configured minimum fitting
population is 30. A declared broader fallback exists, although the completed
run did not need it.

### Approved worked threshold example

The central brass ruler must retain this real candidate example:

- indicator: `local_texture_error_p95` in the mask bounding-box crop;
- observed value: **10.05**;
- critical cutoff: **4.89**;
- direction: higher is worse; and
- result: the indicator crosses the critical boundary and contributes a
  critical `Texture smoothing` category.

The nearby explanation must say that the critical cutoff is the fitted 97.5th
percentile of the relevant comparison stratum. It is **not** a 97.5% chance of
failure. The **failure-category trigger rule** is one critical indicator or
warnings from two distinct evidence components. Derived review flags use their
own declared rules: for example instability, metric disagreement, insufficient
evidence and manual-review-required are not inferred from one universal flag
formula. Every triggered flag must link to its exact derivation. A flag remains
a screening and review-priority signal rather than a correctness judgement.

For the opening p002 candidate, the complete triggered set is `High generative
uncertainty`, `Texture inconsistency`, `Restoration instability`, `Metric
disagreement`, `Insufficient evidence`, and `Manual review required`. `Colour
inconsistency — insufficient evidence` is shown as unresolved, not as a pass.

### Approved population and rule summary

- 10,504 primary candidates: 10,480 full-method candidates plus 24 bounded
  SDXL candidates;
- 4,100 repeated-seed candidate memberships across 1,025 supported groups;
- 725 candidates shared by the primary and uncertainty populations;
- 3,375 uncertainty-only candidates;
- 13,879 unique candidates in the union;
- 14 operational failure categories and 11 review-flag types;
- 194,306 category-assignment rows and 152,669 flag-assignment rows; and
- 137 fitted threshold strata in the completed run.

These counts belong in drawers or research records rather than a large KPI
strip. Lower flag burden under these rules does not establish that a method is
more correct.

### Focused portrait-review mini room (`D02`)

The portrait audit is substantial enough to require its own detailed view,
but it is not a ninth top-level tab. The approved solution is a mini study room
opened from the recessed `Focused portrait review — separate study` alcove in
Trustworthiness.

The same canonical mini room may also be opened from:

- the compact `Focused portrait audit` summary in Study Design; and
- contextual links attached to reviewed portraits in Case Explorer.

All entrances must resolve to one subroute, for example
`Trustworthiness / Focused portrait review`, with a visible return to the
parent room. Study Design remains a brief explanation of why and how the audit
was sampled; Trustworthiness owns the full evidence and interpretation.

The mini room must contain two clearly separated investigations:

1. **Hands and visible anatomy** — show the anatomy annotation, damage mask,
   overlap eligibility, restored crop, paired evidence and blind visual-review
   outcome for a selected case.
2. **Rendered lightness context** — show the declared rendered-lightness
   grouping, matched context, adjusted estimates and uncertainty intervals.
   The interface must state that rendered lightness was studied, not race or
   ethnicity.

The opening scope record must retain:

- 60 portraits screened: 36 included for focused follow-up and 24 excluded;
- 91 manually reviewed anatomical annotations, of which 88 were retained;
- 1,265 anatomy–damage intersections;
- eligibility of at least 256 damaged anatomical pixels and 5% anatomical
  coverage, plus a viable same-case non-hand control with at least 256 damaged
  non-hand pixels;
- a final hand study of 45 cases from 20 independent paintings;
- 292 eligible case records overall;
- all 12 primary model–metric estimates worse for hands, with 10 of 12 meeting
  the corrected significance rule;
- 32 candidate review units across eight cases and four methods in a bounded
  Codex-assisted blind visual review, with 25 visible anatomical failures;
- 30 rendered-lightness painting profiles and 10 context matches; and
- 24 adjusted model–metric lightness associations: zero clearly positive,
  three chroma-error associations clearly negative and 21 intervals crossing
  zero.

The room must keep the automated N27 flag route and the manual/focused D02
study visually and conceptually separate. D02 does not create a new automated
flag family and does not justify a general inherent-bias claim.

### Approved focused portrait-review presentation

The final visual authority for this subroute is
[Final Focused Portrait Review mini room](approved_current/09_focused_portrait_review_final.png),
approved on 2026-09-28. It replaces the earlier idea of another full evidence
wall with a smaller, quieter portrait print room that is visibly subordinate
to, but compositionally distinct from, Trustworthiness.

- Keep the main museum navigation visible with `Trustworthiness` active and a
  breadcrumb/back route; do not add a ninth tab.
- Use an intimate pale-sage and warm-ivory room with cherrywood, linen, aged
  brass, daylight, an open doorway and substantial empty wall and floor space.
- Make the selected portrait investigation the central object on a low
  conservation table. Present `Clean`, `Damaged + mask`, `Restored`,
  `Difference` and `Matched control` as straight physical prints with compact
  selectors integrated into the table edge.
- Present study formation as a small salon-style constellation of portrait
  miniatures and pinned labels rather than KPI cards or a large drawer bank.
- Keep the hand-penalty evidence in one restrained frame. The primary plain-
  language conclusion is `Damaged hands were harder to restore in this
  audit`, paired with `12/12 worse for hands`, `10/12 supported after
  correction` and the bounded statement `No single method minimized all three
  hand penalties`.
- Keep blind visual review on a low folio stand with a visible-failure versus
  acceptable-counterexample control, the `25 of 32` result and the bounded
  review note; do not convert the selected review into a model leaderboard.
  The default `p269 · mixed damage · HINT` record shows review `R005`, `visible
  anatomy failure`, `high confidence`, and its recorded merged-digit,
  malformed-contour observation rather than only the aggregate result.
  Its selected left-hand annotation contains 1,196 damaged hand pixels
  (26.28% of the annotation), with a 1,196-pixel matched control crop. The
  displayed control must use the registered control design rather than a
  visually convenient substitute.
- Place rendered lightness in a physically separate compact alcove. Its
  conclusion is `No consistent overall association across 24 model–metric
  analyses`, immediately paired with `three chroma-error associations were
  negative`, `21 intervals crossed zero`, and `Rendered L* is not race or
  identity`. Use six-metric small multiples or an explicit metric selector and
  direction legend; do not plot one unnamed combined estimate.
- Integrate `D02 report`, `Annotations`, `Tables` and `Methods & limits` as
  small archival drawer-label controls rather than underlined web links.
- Retain the foreground reference books as quiet material cues with the exact
  titles `Portrait screening`, `Hand anatomy`, `Matched controls` and `Blind
  review`.

The mini room must retain generous negative space and must not inherit the
large threshold wall, stage rail, wax-seal composition or dense cabinet scale
of the parent Trustworthiness room.

### Approved spatial and material treatment

- Use a warm conservation review chamber with wine-plum plaster, dark walnut,
  moss textile, parchment and aged brass.
- Keep a broad open floor and a readable left-to-right path from candidate to
  threshold to category, flags and recommendation.
- Use archive drawers, a physical percentile ruler, wax evidence seals and a
  hanging recommendation tag instead of generic software cards or traffic
  lights.
- Keep the candidate selector on a gently angled catalogue tray integrated
  into the cabinet below the evidence frames; it must never hang from the
  painting frame.
- Use the coloured foreground books only as quiet guides: `Evidence`,
  `Thresholds`, `Failure rules`, `Uncertainty` and `Review policy`.
- The focused portrait audit remains a visibly separate recessed alcove whose
  activation opens the mini study room.

### Explicit limitations

- Thresholds are operational relative-screening boundaries, not calibrated
  probabilities or universal quality standards.
- One critical indicator can trigger a category; this prioritizes inspection
  and does not prove visible or material failure.
- Missing evidence must not count as a pass.
- Fewer flags can result from lost evidence and therefore do not necessarily
  indicate an improved candidate.
- The clean image is a controlled digital reference, not historical ground
  truth.
- D02's anatomy annotations and rendered-lightness groups are focused,
  manually reviewed evidence; they do not establish demographic identity,
  causal bias, historical correctness or conservation suitability.

### Deliberately excluded from Trustworthiness

Complete metric education belongs in Metric Framework; stress-test replay
belongs in Stability Lab; unrestricted candidate-by-candidate diagnostic
inspection belongs in Case Explorer; and full threshold tables, model cards,
checksums, notebook lineage, ablation tables and downloadable bundles belong
in Research Archive.

## 07 — Case Explorer

**Status:** Content and final visual approved on 2026-09-28  
**Visual authority:**
[Final Case Explorer](approved_current/10_case_explorer_final.png)

### Purpose

Case Explorer is the candidate-level inspection room. It lets a visitor follow
one saved restoration from controlled reference and damage through the selected
output, spatial evidence, numerical records, operational review status and
source reports. It does not calculate a new score or silently pool different
cases.

### Approved opening

Use the plain-language question:

> What evidence supports this restoration conclusion?

Follow it with one concise sentence explaining that a restoration can be
traced from controlled damage to measurements, warnings and source records.

### Candidate finding and scope

The catalogue exposes the validated N29 inspection population:

- 300 paintings;
- 2,620 method-eligible cases; and
- 13,879 indexed restoration candidates available for inspection.

Filtering may use painting, visual category, experiment, damage, model, review
status, candidate, seed and prompt where those fields apply. The interface must
not imply that every model, seed, prompt or evidence family exists for every
case. Missing evidence remains visibly unavailable rather than becoming zero or
a pass.

The approved visual anchor is `p018`, mixed damage and LaMa. The implementation
must keep its identities explicit:

- experiment: canonical missing-region (`Core test` in the compact selector);
- condition: mixed damage;
- candidate: `candidate__lama__canonical__p018__mixed_damage__c00`; and
- deterministic method, so generative uncertainty is not applicable.

The exact candidate ID remains visible in the selected-record plaque or drawer;
an ordinal such as `Candidate 1` may appear only as a secondary convenience.

The separate `p018` scratch-thin and mild dirt/dust examples may support
uncertainty and retrieval demonstrations, but the interface must never imply
that those outputs belong to the mixed-damage case.

### Approved dominant comparison

Keep five synchronized framed views as the primary evidence:

1. clean controlled reference;
2. damaged input;
3. mask;
4. selected restoration; and
5. selected evidence map.

The evidence-layer selector provides difference, boundary/seam, colour,
texture, `Semantic & structure` and uncertainty where available. Each layer
shows its availability before activation. For the deterministic opening LaMa
candidate, uncertainty is disabled with `Not applicable — deterministic
method`, not rendered as zero or as a generic warning. The clean image is a
controlled pre-damage digital reference, not historical ground truth.

### Approved saved-value example

The compact metric ledger may use these exact saved `p018` LaMa records:

- damaged-area mean Delta E 2000: `52.963 -> 4.066`, reduction `48.897`;
  lower is better;
- damage-crop LPIPS (AlexNet): `0.410 -> 0.019`, reduction `0.391`;
  lower is better; and
- damage-crop SSIM: `0.883 -> 0.969`, increase `0.086`; higher is better.

Call the LPIPS and SSIM region the damage crop or mask bounding-box crop; no
irregular masked-region record exists for those two metrics. Display saved raw
values and direction, never a combined score.

### Candidate status and trace

The approved anchor is `specialist_review_required` with manual review needed
and complete multi-family evidence. Its deterministic-method uncertainty status
is not applicable. The concise explanation is:

> One required colour indicator is missing. Missing is not a pass.

This status does not mean that the three displayed metrics worsened or that the
restoration has been proven wrong. The Trustworthiness link must open the exact
flag derivation rather than a generic definition.

### Related cases and controlled changes

The stored retrieval demonstration contains ten approved queries and 100
neighbour rows: five lower-risk and five flagged neighbours per query. DINOv2
is the primary retrieval view; CLIP remains a separate comparison. Self,
same-case and same-painting matches are excluded. Similarity supplies context,
not correctness, and 735 candidates without eligible retrieval evidence remain
visibly ineligible rather than silently removed.

The `What could change?` controls may open the 14 selected N29 panels covering
damage size, mask placement, model, metric choice, seed, prompt and removed
evidence families. These are selected counterfactual examples, not causal
proof.

### Reports, provenance and D02 route

The room links to the applicable painting report, selected case report, source
notebooks and exact saved rows. Every painting has a painting report. A detailed
case report is enabled only for the 30 selected cases; all other cases show
`Not selected for a detailed case report` and never substitute a neighbouring
report. The population is therefore 300 painting reports plus 30 detailed case
reports, while Research Archive additionally counts the N32 collection index
to reach 331 N32 reports. Eligible reviewed portraits may open the single
canonical `D02` mini room; non-portrait cases show that route as not applicable.

### Approved spatial and material treatment

- Use an enclosed verdigris conservation case room rather than a hallway or
  open model arena.
- Keep the left catalogue and right evidence-layer board as integrated museum
  fixtures.
- Embed the metric ledger, status label, provenance drawers, retrieval light
  table and controlled-change knobs into a dark-walnut workbench.
- Preserve visible wall, patterned floor and walking space; supporting evidence
  must not form a stack of white dashboard boards.
- Use aged brass catalogue symbols and muted archive books rather than modern
  app icons.

### Explicit limitations

- Case evidence measures agreement with a controlled digital reference, not
  historical correctness or material authenticity.
- A review flag is an operational inspection aid, not expert ground truth.
- Retrieval similarity does not establish restoration quality.
- Selected counterfactual panels do not establish causal effects.
- Missing evidence is neither zero nor a pass.
- The room does not make a physical-treatment recommendation.

### Deliberately excluded from Case Explorer

Full study design belongs in Study Design; metric teaching belongs in Metric
Framework; population-level model comparison belongs in Model Gallery;
stress-test populations belong in Stability Lab; threshold construction belongs
in Trustworthiness; and full run manifests, model cards, checksums, publication
locations and downloadable evidence belong in Research Archive.

## 08 — Research Archive

**Status:** Content and final visual approved on 2026-09-28  
**Visual authority:**
[Final Research Archive](approved_current/11_research_archive_final.png)

### Purpose

Research Archive is the provenance, reproducibility, publication and download
room. It records what a conclusion used, what validation passed, what remains
missing, where each artifact lives and how to reproduce the corresponding
analysis. It is not a second results dashboard.

### Approved opening

Use the plain-language introduction:

> Trace every conclusion to its saved evidence.

The archive records what was used, what passed, what is missing and where each
artifact lives.

### Approved catalogue scope

The searchable archive may expose these authoritative Controlled-300 counts:

- 300 paintings;
- 33 numbered stages from N01 through N33;
- one inserted full-production stage, N12A;
- one frozen method-selection decision, D01, and one supplemental focused
  analysis, D02;
- 3,425 unified registered cases;
- 13,879 indexed restoration candidates available for inspection;
- 331 browsable N32 reports;
- five model reports; and
- 24 final N33 figures.

N33 records 32 upstream manifests and 536 of 536 final-report checks passed.
The archive must filter by `controlled_300`; existing N34-N36 and N37
Controlled-50 records are not part of this final-room scope.

### Approved central research ledger

The archive overview presents:

- 33 numbered stages, the inserted N12A production stage, frozen D01 decision
  evidence and supplemental D02 analysis;
- 24 final figures;
- 49 evidence claims;
- 18 recorded limitations; and
- the lineage `Source -> Notebook -> Manifest -> Report -> Checksum`.

The default open record is `Final evaluation - N33`. It exposes its run ID,
notebook ID, recorded Git commit, dirty/clean state, configuration and SHA-256,
input and output checksums, Python/platform/package versions and validation
result. Its own manifest contains 32 upstream run-ID entries for N01 through
N32; D01, N12A and D02 remain separately linked project records and must not be
invented as direct N33 manifest keys. For N33, show the recorded dirty
working-tree state honestly; do not imply a pristine checkout.

### Report catalogue

Keep the report populations separate:

- 330 N32 case/painting reports: 300 painting reports and 30 selected case
  reports; one collection index brings the browsable N32 total to 331;
- five self-contained N31 model reports: Telea, LaMa, Stable Diffusion, SDXL
  and HINT; and
- one N33 final-evaluation report.

The interface must not add the model and final reports to the `331` label or
misrepresent them as the same report population.

### Painting provenance and missingness

The archive can state that all 300 paintings have a source URL, rights-status
value and raw SHA-256 record. Style/period, date/period and medium are populated
for 268 paintings; the remaining 32 retain valid image and source records but
lack those three descriptive fields. Category balance does not establish
historical representativeness.

### Publication locations

Use the exact per-artifact destination from the publication registry and bundle
release records. The public destination guide describes common roles, not
exclusive storage classes:

- GitHub stores notebooks, source code, configurations, documentation, compact
  tables, manifests, validations and indexes, plus some earlier Git/LFS
  candidate and compact report evidence;
- Hugging Face Candidates stores verified candidate releases, including the
  full HINT and bounded SDXL releases and candidate portions of later split
  releases; and
- Hugging Face Diagnostics stores maps, metrics, diagnostic bundles and the
  N32 report package, while compact N31/N33 reports remain in GitHub.

The external publication registry records 2,653 of 2,653 **individually
published** artifacts as remotely verified. A separate `Verified bundled
releases` catalogue exposes bundle count, release ID, pinned revision and
verification status; bundles must not be added to the 2,653 row count. The
2026-10-02 publication update replaces the original `planned after pipeline
freeze` label with `Zenodo published · v1.0.0` and the verified version DOI
`10.5281/zenodo.23092185`. The existing hitbox/layout remains fixed; the popup
reads the separate published-record receipt, not modified scientific partitions.

### Limits cabinet

Keep all 18 final limitations accessible and group them into four drawers:

- dataset boundary;
- model boundary;
- interpretation boundary; and
- use boundary.

The primary path must retain at least these statements: no universal quality or
trust score, no expert-rating ground truth, uncertainty is not calibrated
confidence, similarity is not correctness, and no conservation approval or
physical-treatment recommendation is provided.

### Approved spatial and material treatment

- Use a spacious, clean, ancient university rare-book room with curved oak
  shelves, stone arches, ladders, restrained brass, parchment and an open
  central research ledger.
- Preserve broad stone walking paths and architectural air around the smaller
  reading desk.
- Integrate search into a compact dark-oak card catalogue, limitations into an
  accessible glass-fronted cabinet and publication locations into a recessed
  document-box shelf.
- Use crisp letterpress, engraved labels, library stamps, leather tabs and
  restrained wax seals instead of modern colourful icons.
- Keep distant archive destinations and publication tags readable at normal
  full-screen size without turning them into bright banners.
- The atmosphere may feel mysterious and old, but the room must remain clean,
  cared for and usable rather than dirty, theatrical or fantasy-branded.

### Explicit limitations

- A successful checksum confirms file identity, not scientific correctness.
- A completed validation gate only verifies the declared computational
  contract.
- Published availability does not remove the scope limits of the underlying
  study.
- Workstation runtimes and scaling projections are not universal performance
  guarantees.
- The archive does not convert computational evidence into historical or
  conservation authority.

### Deliberately excluded from Research Archive

Do not make the archive the primary place for model ranking, stress-test replay,
flag interpretation or free-form candidate comparison. Those tasks remain in
Model Gallery, Stability Lab, Trustworthiness and Case Explorer respectively.
