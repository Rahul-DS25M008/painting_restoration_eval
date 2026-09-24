# Controlled-300 Dashboard Design Direction

**Status:** Current primary layout and interaction direction approved by the
user on 2026-09-24  
**Mandatory review point:** After Notebook 33 and immediately before Notebook
34 or any Controlled-300 Streamlit implementation begins  
**Scope:** Navigation, interaction, visual hierarchy, information flow, and
presentation references only

## Approved current direction

The two boards below are the current design authority for the future
Controlled-300 dashboard:

1. [Interactive Museum Rooms 01–04](approved_current/01_interactive_museum_rooms_01_to_04.png):
   Exhibition Foyer, Study Design, Metric Framework, and Model Gallery.
2. [Interactive Museum Rooms 05–08](approved_current/02_interactive_museum_rooms_05_to_08.png):
   Stability Lab, Trustworthiness, Case Explorer, and Research Archive.

Together they define a chromatic, tactile, painting-first museum that remains a
usable website. The approved interaction language includes illuminated room
routes, exhibit scrubbers, movable inspection lenses, before/after dividers,
spatial model carousels, synchronized seed and damage-size controls, explicit
flag-derivation paths, sliding evidence drawers, and provenance trails. Motion
must remain restrained and curatorial rather than futuristic or decorative.

The eight-room structure is now fixed as the primary navigation:

1. Exhibition Foyer;
2. Study Design;
3. Metric Framework;
4. Model Gallery;
5. Stability Lab;
6. Trustworthiness;
7. Case Explorer; and
8. Research Archive.

The exact tab content may be refined when the final Controlled-300 evidence is
available. Such refinement may replace illustrative values and reorganize
content within a room, but it must not silently replace the approved room
sequence, museum identity, interaction grammar, or progressive introduction
from orientation to detailed evidence.

The boards contain illustrative paintings, labels, counts, metrics, and claims.
They are not scientific outputs. Implementation must replace every fictional
value with validated upstream evidence and must preserve the dashboard's
approved scientific boundaries.

## Alternative concept archive

All earlier selected boards remain under [`alternatives/`](alternatives/) as a
separate reference archive. They are not competing primary layouts. At the
mandatory pre-Notebook-34 review, a useful component may be borrowed from one
of these boards only when the decision is explicitly recorded and remains
visually coherent with the approved current direction.

### Archived boards and the qualities to retain

| # | Reference | Why it was selected | Reusable design strengths |
|---:|---|---|---|
| 1 | [Evidence Newsroom](alternatives/01_evidence_newsroom.png) | Good presentation | Claim-first editorial hierarchy; findings are paired with sources, caveats, counterexamples, and reproducibility; strong typography makes dense evidence readable. |
| 2 | [Evidence Mobile](alternatives/02_evidence_mobile.png) | Good panels and information presentation | Independent evidence families remain visibly separate; panels have clear roles; the case comparison and stability view explain complex evidence without collapsing it into one score. |
| 3 | [Geometric Evidence Composition](alternatives/03_geometric_evidence_composition.png) | Great divisions and unique design | Bold compositional divisions, strong contrast, memorable category geometry, and a genuinely interactive visual grammar rather than a conventional dashboard grid. |
| 4 | [Quiet Kintsugi Trace](alternatives/04_quiet_kintsugi_trace.png) | Clean presentation and good information flow | Restrained museum tone, generous whitespace, calm reading order, visible limitations, and a clean transition from overview to comparison to uncertainty and provenance. |
| 5 | [Question Journey and Decision Trace](alternatives/05_question_journey_decision_trace.png) | Journey presentation is a good idea | Question-led navigation, case storytelling, an explicit evidence journey, and a transparent decision trace that shows how measurements lead to bounded conclusions. |
| 6 | [Exhibition Gallery](alternatives/06_exhibition_gallery.png) | Art exhibition is a great idea | Immersive museum spatial metaphor, models presented as exhibits, a dedicated evidence room, and a guided-tour mode suitable for supervisor presentations. |
| 7 | [Conservation Light Table](alternatives/07_conservation_light_table.png) | Good flow; reproducibility tab is especially strong | Painting-first inspection, tactile comparison tools, magnified local evidence, and reproducibility organized as a first-class sequence of provenance, notebook, model, seeds, checksums, and artifacts. |
| 8 | [Pipeline, Alternate Futures, and Replay](alternatives/08_pipeline_alternate_futures_replay.png) | Useful, though less preferred than the other finalists | Temporal pipeline replay, branching model futures, synchronized damage-size exploration, and direct visual connection between process stages and changing results. |
| 9 | [Living Pigment Museum foundation](alternatives/09_living_pigment_museum_selected_direction.png) | Established the selected palette and spatial museum identity | Chromatic room-based navigation, tactile materials, painting-first exhibits, and an identifiable visual world rather than a generic dashboard. |
| 10 | [Live-evidence content study](alternatives/10_live_evidence_content_layout_mock.png) | Grounded the museum direction in the deployed application's content | Useful content mapping and progressive disclosure, retained as a planning reference rather than the approved final composition. |

## What the selection reveals

The final interface should combine creativity with legibility. Across the
finalists, the preferred qualities are consistent:

- one strong organizing metaphor that improves navigation rather than merely
  decorating the page;
- paintings, restorations, crops, and diagnostic maps as the primary visual
  evidence, with plots and tables supporting them;
- question-, claim-, journey-, or room-based navigation instead of a sequence
  of report-like pages;
- clear visual divisions and deliberate information flow, including memorable
  page compositions that do not default to identical rounded cards;
- direct conclusions paired with their numerical evidence, limitations,
  provenance, and source links;
- tactile museum, conservation, editorial, or exhibition character with human
  imperfections, restrained annotation, and strong typography;
- complete case inspection through synchronized views, magnification, region
  selection, method comparison, and numerical evidence;
- uncertainty presented as repeated-candidate disagreement or stability
  evidence, never as calibrated confidence or proof of correctness;
- reproducibility treated as a principal destination with provenance, model
  configuration, seeds, checksums, notebook lineage, artifacts, and downloads;
  and
- a useful presentation mode or guided path for explaining the thesis to a
  supervisor without removing exploratory access for technical users.

## Mandatory pre-Notebook-34 review

Before Notebook 34 is refactored, review the two approved boards against the
completed Controlled-300 evidence and confirm:

1. the eight-room navigation and primary interaction assigned to each room;
2. any explicitly approved component borrowed from the alternatives archive;
3. the page-by-page evidence, controls, conclusions, and limitations;
4. the responsive and accessible representation of the chosen visual system;
5. the supervisor-guided presentation path and the free exploration path; and
6. the local/remote asset-loading contract established by the storage review.

Notebook 34 then packages only the assets required by that confirmed contract.
Notebook 35 validates fidelity, functionality, evidence coverage, and deployed
access. The mockups' illustrative text and imagery are not substitutes for
those gates, and the currently deployed 50-painting application remains
unchanged until the approved Controlled-300 implementation is ready.
