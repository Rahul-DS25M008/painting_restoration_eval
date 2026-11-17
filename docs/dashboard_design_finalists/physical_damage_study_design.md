# Physical Damage Study — Approved Design

**Design approved:** 2026-11-16  
**Implementation:** Completed and validated through a separate Streamlit test deployment.  
**Production deployment:** Integrated into the existing museum on 2026-11-17 without changing its public URL.  
**Starting commit:** `a9ce94ad0728ffa89e11f9da80e49e3cbbe91ecc`

The Study Design entrance and Physical Damage Study room were reviewed and approved separately. The final implementation follows the approved single-room composition and interaction requirements. Earlier workbench, gallery, desk, storage, theatre, mobile, atlas, and separate collection concepts are retained only as superseded alternatives. Image filename numbers refer to design-catalogue indices, not additional principal rooms.

## Visual authority

- [Single overhead room](approved_current/12_physical_damage_study_final.png).
- [Study Design supplementary-study entrance](approved_current/13_study_design_supplementary_entry.png).

The user approved the Study Design placement separately, then approved the
single-room refinement. Earlier workbench, gallery, desk, storage, theatre,
mobile, atlas and separate collection/immersive-view concepts are not approved
implementation references. The image filename numbers are design-catalogue
indices, not new principal-room numbers.

The approved layout is one continuous, open museum hall viewed from above at
an oblique angle. Five category displays sit around the perimeter; a shared
inspection table occupies the centre. The entrance, warm stone, walnut floor,
green display bases and brass selection trace belong to this composition.
Do not replace it with a front-facing room or a collection page followed by a
separate inspection page.

The reference images were created with the built-in image-generation tool.
Their artwork previews, decorative rendering, typography and example values
are illustrative. Bind actual artwork, labels, controls and measurements to
the saved evidence; never use generated restoration pixels as study evidence.
Do not crop or distort the scientific images to fit a decorative aperture.
The entrance reference authorizes the right-hand alcove change only, not any
incidental differences elsewhere in the generated Study Design image.

## One-room interaction

All ten painting selectors remain part of the room. The centre shows the
selected damaged input and its four primary reconstructions: Telea, LaMa,
HINT and Stable Diffusion. Selecting a painting highlights its frame and
updates the central table in place. A restrained brass trace connects the
selected exhibit to the table.

| Perimeter category | Case selectors |
| --- | --- |
| Portrait / figure | rd001, rd002 |
| Landscape | rd003, rd004 |
| Architecture | rd005, rd006 |
| Abstraction | rd007, rd008 |
| Texture / brushwork | rd009, rd010 |

Use the canonical category identifiers and source metadata behind these
short display labels. These are five areas inside one room, not five routes.
The reference shows rd004 as the opening example; obtain its actual title,
images and case identity from the saved producer records.

| Interaction | Required behaviour |
| --- | --- |
| Select a perimeter painting | Update the selected case, five table images and associated evidence together; preserve the room view. |
| Full painting / Same detail | Switch all five images to whole-image views or the same registered display crop. Display crops are not automatically metric regions. |
| Show mask | Show the reviewed repair targets with an unobscured view available. These masks do not cover every visible defect. |
| Click an image | Open an enlarged inspection popup; closing it restores the same case and table state. |
| Four seeds | Show the four saved SD outputs and their recorded seed identities; identify the primary candidate. |
| Evidence | Open saved observations, boundary/outside-region diagnostics, controlled comparisons, sources, settings and the report through in-room panels or popups. |

No mandatory navigation to another viewer is part of the approved design.
Use the existing museum's dialog, selection and return-link conventions.
Provide keyboard-accessible controls, meaningful labels, visible focus and a
readable narrow-screen arrangement of the same content. Large imagery and
reports should load on demand rather than all at room startup.

### Physical-room typography and frame refinement — 2026-11-16

Following the final annotated design review, the main heading, selected
artwork title and interpretation note sit on the central marble table, clear
of the architecture and doorway. Dark, bold small-cap serif lettering replaces
the floating cream text; category names follow the wall surfaces. The return
link has a walnut/brass plaque on the table. Three matching evidence plaques
sit in the clear floor strip below it, above the doorway. One
full-width live navigation bar covers the background's empty header strip.

The ten selector previews are aligned to measured inner frame quadrilaterals,
with each identifier centered on its own plaque. Whole painting content is
contained in a dark mat, then projected into the decorative frame plane.
This perspective applies only to the selectors; table images and enlarged
scientific inspections retain their original proportions. Narrow screens
use ordinary rectangular selectors. No source artwork, candidate, mask,
metric or decorative shell file was changed in this refinement.

The follow-up lettering pass references the Research Archive's furniture
plaques and Study Design's study-path labels. Catalogue identifiers use a
small RD prefix and heavier three-digit number, while their actual case IDs
and destinations remain unchanged. Controls use brass bevels and rivet details;
the selected control uses the museum's dark red-brown book colour.

Reusable plaque asset: `streamlit_assets/rooms/physical_damage_link_plaque.png`,
created with the built-in image-generation tool. Prompt: one wide antique
museum label holder, dark walnut backing, narrow aged brass inset border,
blank warm ivory face, two slotted brass screws, shallow depth and soft contact
shadow, viewed almost front-on with warm light from above left; transparent
surroundings, no text or artwork. Labels and destinations are live HTML.

## Approved placement

The Study Design room's existing right-hand portrait-audit alcove becomes a
compact "Supplementary studies" area with two directly clickable tiles:

1. **Portrait audit** — preserves access to the existing portrait review.
2. **Physical damage** — opens this room, showing the ten-painting/four-method scope.

The new room has a return link to Study Design. The eight principal tabs,
their order, tour numbering and core-study population figures remain intact.
Extra entry points in Trustworthiness or Case Explorer were proposed but have
not been approved. They are not included in this design approval.

### Alcove styling refinement — 2026-11-16

The entrance was refined to blend into the
original wall rather than sit on a flat beige panel. The heading is dark serif
lettering directly on plaster; each link occupies a small antique-gold frame
with a caption plaque. Follow-up review removed both scope/count lines,
shifted the heading slightly left with its second line centered, and fitted
the Physical damage label inside its plaque. Both destinations are unchanged.

Decorative asset: `streamlit_assets/rooms/study_design_supplementary_alcove.png`.
Created with the built-in image-generation tool, editing the original Study
Design shell. Prompt: preserve the existing room, texture, light and objects;
replace only the far-right alcove's single blank frame and plaque with two
vertically stacked small antique-gold frames and blank plaques, seamlessly
repairing the plaster around them; no enclosing panel, artwork or text.
The implementation masks this generated image to the edited alcove only, so
the original shell remains intact. Actual recorded images and live labels
fill the two frames; no generated painting is presented as research evidence.

### Final backdrop and plaque alignment — 2026-11-16

The three evidence plaques are centered on the inspection table, with a small
gap beneath its lower edge. Narrow screens retain the centered wrapping layout.
The exterior green blueprint ground is replaced by warm limestone museum
flooring. The oval room, ten frame positions and inspection table retain the
approved composition; the original shell remains available as a reference.

Active asset: `streamlit_assets/rooms/physical_damage_study_shell_stone.png`.
Generated with the built-in image-generation tool, editing
`streamlit_assets/rooms/physical_damage_study_shell.png`.

Final generation prompt:

> Precise background-only edit of the supplied museum website background. Replace ONLY the dark green exterior ground and gold blueprint linework OUTSIDE the oval stone-walled room with realistic warm muted taupe and limestone museum floor tiles. Large understated stone slabs, subtle joints receding with the existing overhead perspective, softly shadowed beside the outer walls, warm museum light. Remove every blueprint line. Keep the oval room and EVERYTHING inside it EXACTLY unchanged at the SAME pixel coordinates: all ten empty gold frames, blank plaques, walls, plants, lights, wooden floor, central cream stone table, entrance arch and green carpet. Keep the original 1672 by 941 composition, camera, scale, geometry, crop and canvas aspect ratio unchanged. No camera changes, no rescaling, no new decorations, no text, no images inside the blank frames, no changes to the interior. The narrow blank dark navigation strip along the very top can remain dark. This is a production web background with existing interactive overlays aligned precisely to the current frame/table positions; exact preservation of those positions is essential. Only replace the exterior green surrounding backdrop with tasteful warm stone museum flooring.

## Evidence binding and interpretation

Use the completed D03/D04 outputs without new inference, new notebooks or
scientific-output rewriting. D04 contains ten paintings, forty primary
reconstructions and thirty additional SD candidates: seventy candidates in
total, including ten four-seed groups. The main comparison uses the fixed
primary SD seed 2026, not a best-looking seed selected for the exhibit.

The producer evidence roots are:

- `outputs/d03_real_damage_dataset_preparation/`
- `outputs/d04_real_damage_restoration_and_evaluation/`

The D04 report configuration, approved visual observations and producer
manifests govern the content. Relevant configuration records are
`config/evaluation/real_damage_report.yaml` and
`config/evaluation/real_damage_visual_observations.json`.

Physical cases have no clean reference. Boundary descriptors, preserved
outside-mask pixels and seed differences are not clean-reference fidelity
scores or probabilities of correctness. The qualitative observations are
AI-assisted qualitative visual inspection, reviewed before inclusion; not an external expert survey.

Controlled examples are separate artworks, not matched clean versions of the
physical cases. Show their reference metrics only in their own context.
Disclose that physical SD used targeted painting-specific prompts while the
controlled examples retain their original recorded configurations. Retain
source attribution and the distinction between selected repair targets and
all physical deterioration.

## Implementation sequence

1. Bind the approved room and entrance composition to exact source assets and
   stable case identities on the feature branch.
2. Implement the room, entrance and evidence popups; preserve existing rooms.
3. Test locally, including selection consistency, images, source bindings,
   popup behaviour, narrow screens and existing-room navigation.
4. Complete the final visual approval, then push the branch and deploy
   a separate Streamlit test app following the agreed workflow.
5. Verify the cloud app; merge only after final deployment validation and approval. Keep the
   existing main application URL when the main branch updates.

Local implementation and testing are recorded in
[the validation record](physical_damage_study_validation.md). This does not
claim a remote upload, publication, commit, deployment or merge.

## Approved image integrity

The approved previews were copied byte-for-byte from the generated originals.

| File | SHA-256 |
| --- | --- |
| `12_physical_damage_study_final.png` | `bd552b30e01f87935a4e890bf6b755782c83537a7b238c8426e8fd5625cbdd2d` |
| `13_study_design_supplementary_entry.png` | `69a88b9dc25d0ef20f457724dcf29416a1511221661cf0dc50c1673138bc3b69` |
