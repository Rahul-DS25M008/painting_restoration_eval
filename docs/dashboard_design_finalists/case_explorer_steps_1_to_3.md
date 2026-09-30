# Case Explorer implementation through step 3

Case Explorer is available as a local, evidence-bound room at
`http://localhost:8501/?room=case_explorer`. This checkpoint covers the blank
production shell, exact saved-data bindings, and the first working room with
bounded checks. It does not claim deployment readiness or final visual approval.

The preceding Focused Portrait Review freeze, commit
`b560727635972fd392ce73324eb01b7af45d22e7`, was confirmed on GitHub `main` before
this work. Its 25-file local freeze check passed. No frozen portrait source or
artwork was changed for Case Explorer.

## Step 1 blank production shell

The approved reference is
`approved_current/10_case_explorer_final.png`. The built-in image-generation
editor produced `streamlit_assets/rooms/case_explorer_shell.png`, preserving the
enclosed verdigris room and walnut furniture while clearing its text and
scientific imagery. Live text, controls and original evidence are overlaid in
code. No generated painting or heat map is used as scientific evidence.

The final edit prompt was:

> Use case: precise-object-edit. Image 1 is the edit target: the approved Case Explorer room. Create a blank production background shell for this interactive web page. Preserve EXACT composition, 16:9 canvas, camera, architecture, enclosed verdigris walls, ceiling skylight, lighting, brass fixtures, walnut furniture, frame placement, plants, marble bust, bottles, books, floor and shadows. Remove ALL text, letters, numbers, icons, logos, graphs, dropdown arrows and scientific imagery. Top navigation becomes plain dark teal. Make the five central framed picture interiors blank warm ivory paper, including their title strips. Left catalogue board and its six physical horizontal selector rows stay in the exact same positions but with blank parchment interiors; preserve their brass hardware. Right evidence-layer board retains all physical hanging strips and one dark green selected strip but no symbols or text. Keep central record plaque and long toolbar plaque blank. Bottom-left selected-candidate frame becomes blank parchment. Desk metric ledger becomes blank ivory paper with no lines or numerals. Bottom retrieval table has blank paper and ten tiny empty photo frames. Right report drawers and lower seven brass knobs remain physically identical but unlabelled. Blank book spines and small side motto board. Do not move, resize or invent objects. No paintings, masks, heat maps, UI lettering, text or replacement symbols anywhere; scientific evidence will be overlaid in code. Photorealistic museum illustration matching original. Opaque background.

## Step 2 exact saved evidence

The opening is `candidate__lama__canonical__p018__mixed_damage__c00` in the
canonical missing-region experiment. N34 remains the candidate allow-list and
painting-selection authority. The room never selects candidates by scanning
image folders.

The offline index builder copies existing producer rows and checksums into
`streamlit_assets/evidence/case_explorer`. It does not compute metrics or
generate scientific maps. Its sources are checked against their artifact
manifests before indexing:

- 35,832 metric rows from N13, N14 and N17, partitioned into 300 painting shards;
- 115,984 image checksums and recorded scale metadata from N16, N17, N19, N20
  and N22 map manifests;
- 7,150 existing input-image checksums from the four N04–N07 case tables; and
- 24 N29 panels from two checksum-verified collections: 10 retrieval panels
  and 14 selected counterfactual panels.

During normal room interaction, only the selected painting's metric and map
shards are decoded. The four base views and the selected evidence image are
checked against recorded SHA-256 values when displayed. The N34 restoration
checksum binds each output to its selected candidate. Original reports are
loaded only after explicit selection and use the existing verified report
adapter.

The opening ledger retains the saved full-precision rows behind these rounded
display values:

| Metric | Region | Damaged | Restored | Preferred direction |
| --- | --- | --- | --- | --- |
| Delta E 2000 | Damaged area | 52.963 | 4.066 | Lower |
| LPIPS AlexNet | Mask bounding-box crop | 0.410 | 0.019 | Lower |
| SSIM | Mask bounding-box crop | 0.883 | 0.969 | Higher |

No combined score is produced. The recorded specialist-review requirement and
missing colour indicator remain visible even though these three metric rows
improve. Deterministic uncertainty is explicitly not applicable.

## Step 3 working room

The live room provides a painting/category catalogue and within-painting
filters for experiment, case, model, review status, seed and prompt. Explicit
candidate selections are validated; an invalid candidate or map never falls
back to another record. After an explicit painting change, the documented
initial-selection policy chooses its saved mixed-damage LaMa record where
available, otherwise its first indexed candidate.

Five framed views open a shared zoom-and-pan comparison. Evidence controls
switch between saved difference, seam, colour, texture, semantic and uncertainty
images where available. The map drawer exposes recorded variants, scales,
renderer metadata and source paths. Multi-panel producer images retain their
original layout; their legend pixels are not treated as registered painting
coordinates.

The workbench provides exact metric rows, JSON downloads, candidate provenance,
source-notebook downloads, the original painting report and the exact selected
case report when one exists. Unselected case reports remain disabled. The
Trustworthiness route carries the candidate ID. D02 opens only a completed
review of that exact candidate, not an arbitrary portrait.

The retrieval drawer preserves all 100 recorded neighbour rows, their separate
DINOv2 and CLIP similarities, exclusions and exact neighbour links. Stored
queries and counterfactual panels are explicitly labelled as different study
examples when they do not represent the active room selection.

## Focused verification

The Python tests cover exact opening values, all five opening images, distinct
evidence layers, deterministic uncertainty, rejection of invalid identities,
alternate-model and diffusion-seed inputs, synthetic degradation, report
availability, the exact R005 D02 route, and the stored retrieval/panel counts.
Two Node tests cover seed/prompt filtering and clean candidate-specific URLs.
All 13 Python tests and both Node tests passed after the visual iteration.
The added tests cover the reference control families, shared thumbnail source,
recorded content bounds, and verification of every original N29 study panel.

Run the bounded checks from the repository root:

```powershell
$env:PYTHONPATH = 'src'
.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_case_explorer.py -v
node --test tests/case_explorer_controller.test.cjs
```

Browser checks covered LaMa, Telea and Stable Diffusion selections, a painting
change to p001 and back, a zero-match seed filter, layer changes, map-variant
reopening, zoom/reset, Escape dismissal with focus restoration, all seven
controlled-change families and all ten retrieval queries. Each query displayed
ten stored neighbours; each comparison family exposed two original panels.
The original detailed case report and saved retrieval panels loaded. Report,
notebook and export return links retain the candidate and evidence layer.

The JSON export uses Streamlit's normal download mechanism and offers an exact
record preview. A downloaded three-row metrics file was confirmed. Its opening
Delta E values remain 52.962928771972656 and 4.066130638122559.

The catalogue was checked at a narrow-screen viewport; it stayed within the
dialog without horizontal overflow. The viewport was reset afterward. This is
not an exhaustive accessibility, all-candidate or deployment-performance audit.

## Visual iteration against the approved reference

The room now uses the reference's six catalogue fields, seven toolbar actions,
six evidence layers, eight-column metric ledger, ten retrieval miniatures and
seven controlled-change knobs. Serif typography, red board headings, blue-grey
catalogue copy, compact brass-coloured icons and angled labels follow the
reference's visual hierarchy. Only the selected evidence layer has the active
green treatment. Dynamic identity labels fit their plaque, and long missing-
indicator lists use a bounded count on the room plaque with full detail in the
record drawer. Text containment was checked on the opening, Telea, diffusion
and portrait selections during the iteration.

The small painting frames show details cropped using recorded content bounds;
the inspection popup always preserves the full original saved image. The ten
retrieval miniatures are CSS windows into one verified original N29 panel,
explicitly labelled as a separate p018 HINT dirt/dust example. No scientific
image was generated or altered. Popups use a consistent parchment and green
case-file treatment, readable value cards and expandable provenance. Narrow
screens also receive larger quick-access controls below the room.

The result is a close implementation, not a claim of pixel-identical artwork.
The blank generated shell, reconstructed SVG icons and available serif fonts
remain approximations to the raster reference. Real evidence and availability
take priority where the reference's illustrative content differs: the missing
required colour indicator is not labelled complete, and unrelated retrieval
examples are not presented as evidence for the active candidate. Final visual
approval remains with the user.

Final preview: `case_explorer_visual_iteration_preview.png`.
The Model Gallery, Stability Lab, Trustworthiness and Focused Portrait Review
freeze checks all passed again, with their approved fingerprints unchanged.

## Deferred work

Remote asset fallback, Hugging Face bundling/publication, full N35 validation,
deployment performance budgets and the final cosmetic approval remain outside
steps 1–3. Missing local files are disclosed rather than replaced. No inference,
metric recomputation, notebook execution, commit, push or upload was performed.
Existing unrelated shared-app and notebook edits were preserved.
