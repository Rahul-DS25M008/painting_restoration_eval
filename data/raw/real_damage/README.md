# D03 real-damage acquisition inputs — cohort v2.0.0

The researcher accepted these ten sources on 2026-11-15. `metadata/approved_sources.json`
is the acquisition authority. Preserve each original image and its saved source
metadata. A source hash and dataset version are required when joining reused rd IDs.
The previous v1.0.0 cohort and unfinished outputs remain in ignored local recovery
storage; old notebook execution results are not evidence for these replacements.

`annotations/` contains the selected binary repair masks shown during source review.
They are bound to the unchanged 768-pixel canonical image by SHA-256 in the annotation
recipe. They are not clean references, complete condition maps or final D04 masks.
D03 still validates them and audits the 512-pixel representation before handoff.
No artificial damage was added. Remaining unselected deterioration is outside the
chosen repair target. Prior neutral fills on ancient painted panels are recorded.

| ID | Source | Source-image reuse statement |
|---|---|---|
| rd001 | Portrait of Antonio van Diemen | Public domain, as recorded by Commons |
| rd002 | Diotti, Antigone before restoration | Public domain, as recorded by Commons |
| rd003 | Pasini, Horse pasture in Algeria | Public domain, as recorded by Commons |
| rd004 | Garden fresco, House of the Golden Bracelet; photo Tyler Bell | CC BY 2.0 |
| rd005 | Landscape with maritime villa; photo BeakheadIntrados | CC BY-SA 4.0 |
| rd006 | Cubiculum wall, Boscoreale; The Metropolitan Museum of Art | CC0 Open Access |
| rd007 | Malevich, Black Square | Public domain, as recorded by Commons |
| rd008 | Master of the Fertility of the Egg, Watermelon Regatta | Public domain, as recorded by Commons |
| rd009 | Rubens, Tarquinius and Lucretia, damaged state | Public domain, as recorded by Commons |
| rd010 | Hidaka Yasunori, Nude before restoration | Public domain, as recorded by Commons |

Individual source-page URLs, original-image URLs, creators/photographers, credits,
licence links, acquisition hashes and source revision metadata are in the catalog.
For rd004 retain Tyler Bell's attribution, the CC BY 2.0 link and a modification
notice. For rd005 retain BeakheadIntrados's attribution, the CC BY-SA 4.0 link and
a modification notice; adapted images carry CC BY-SA 4.0. These image conditions
are not replaced by the repository's software licence. The Met snapshot records
the selected image among object 247017's additional images and its public-domain
flag; original-byte identity is the local acquisition SHA-256, not a Met checksum.

The rd010 PNG has fully opaque alpha. D03 drops that channel in memory, retaining
RGB values and ICC metadata for the existing preprocessing policy. No raw image
is overwritten, cropped, recoloured or padded before canonical preprocessing.

Antigone's selected area is 3.4994% after adding missed soldier/cliff flaking.
Its explicit user-approved exception permits more than 15% if tracing requires
it; no mask is enlarged to reach an area target. Other masks remain roughly 2–15%.
