# Stability Lab — reference shell and content audit

## Scope and checkpoint

User authorized steps 1–3 locally after committing the approved Model Gallery.
GitHub main was verified at `a2bf09e882a6f9f203105875af75c179e1d070de`.
The pilot branch remains `125ea5653026ca5a17ccd991f8ef2d1f1363b62d`.
The 17-file Gallery freeze guard still passes. Its publication manifest records
zero new HF objects required. No staging, commit, push, upload or hosted app was
performed for this new room. N35 remains untouched.

## Step 1 — generated shell

The built-in image-generation skill edited the approved
`approved_current/07_stability_lab_final.png`, preserving the nighttime atelier,
brass instruments, frames, ledgers, bottles and registrar desk. It removed text,
plots, paintings and masks so the original evidence can be embedded separately.

- Asset: `../../streamlit_assets/rooms/stability_lab_shell.png`
- Prompt and original generated location: `stability_lab_shell_prompt.txt`
- Shell SHA-256: `81504d77921d84fe734ef5bc1a116e3dfc0602e56fe2c0fa5e2c1dd9a4b773a0`
- Reference SHA-256: `738e9a11139b8bda96d7d2f0d7f5669be0b88b5e705a8120ac08de7a5559a57d`

The shell is decorative only. Scientific pictures, masks, plots and values were
not generated or edited. In-frame display removes recorded normalization padding;
inspection shows the full original canvas.

## Step 2 — embedded content readiness

| Reference object | Recorded binding | Availability / interpretation |
| --- | --- | --- |
| Main painting pair | N02 clean reference; N05/N06/N07 input; N09/N10/N11/N12a result | All 4,480 focused-test primary candidates have local files and all three exposed metric values |
| Seven-stop damage rail | N05 cases: 2, 4, 6, 8, 10, 15, 20% | 35 paintings, 245 cases, 980 candidates; nested masks |
| Five-position mask wheel | N06 group + variant | 105 groups, 525 cases, 2,100 candidates; family and area are paired conditions |
| Degradation bottles | Four eligible N07 families | 350 of 1,155 generated cases; 1,400 primary candidates |
| Four seed thumbnails | Exact member IDs in N18/N22 pair rows, resolved to N11/N22 candidates | 1,025 groups, 4,100 memberships, 6,150 pairs; all member files exist |
| Seed overlay card | N22 map-image manifest | Recorded per-case overlays available for all 245 damage-size groups; N18 does not publish equivalent per-case images |
| Chart parchment | N16 spatial error; N13 crop SSIM; N18/N22 seed pair RGB MAE | One active measure; no combined score or freshly computed metric |
| Four ledger drawers | Approved contract and N23/N24/N25/N18/N22 findings | Counts, boundaries and original producer identities displayed separately |
| Registrar desk | Recorded painting, method, evidence selectors | 35 paintings for focused tests; actual group population for seeds |

The seed catalogue has 480 canonical generic-prompt groups, 300 canonical
scratch-aware-prompt groups and 245 generic damage-size groups. Group IDs, prompts
and candidate memberships remain separate. The misleading candidate boolean is
not used to infer membership; the published uncertainty pair rows are authoritative.

## Necessary corrections to the reference's illustrative content

- Bottles show **Dirt/dust, Partial transparency, Water stain, Water stain + dirt**.
  The fifth opens **Not an inpainting task**, explaining the excluded blur/fading/
  colour diagnostics. No repair ranking is manufactured for those effects.
- LaMa opens with the seed drawer closed. Stable Diffusion is an explicit user
  choice, never a silent switch to make the four frames look full.
- N18 numeric variability is available, but its missing per-case overlay is
  explicitly acknowledged; none is fabricated.
- Opening: p018 / LaMa / 20% / spatial masked error. This is a deliberately steep
  recorded example for that metric, not a universal damage threshold.
- The recorded default trajectory is 4.1318695438, 6.3067950775, 9.6465636489,
  9.5337827707, 13.2004297422, 30.9869134483, 39.3301701445.
- Evidence selectors expose spatial masked error, boundary error, crop SSIM.
  Seed mode instead fixes its chart to six recorded masked-region RGB-MAE pairs.
- Balanced seven-per-category focused sampling is not evidence of art-historical
  style effects. Repeated cases are not independent paintings.

## Verification boundary

`tools/audit_stability_lab_readiness.py` is read-only and prints reproducible JSON.
`tests/test_stability_lab.py` validates counts, every focused candidate's existence
and three metrics, all seed memberships, default values, prompt separation, invalid
scope rejection and selected image hashes. Images actually embedded are checked
against producer hashes where recorded; this is not an exhaustive checksum/decode
of the entire corpus. No model inference, metric recomputation or producer writes.

The local first pass is ready. Cloud deployment still needs the later shared pinned
asset resolver / compact lookups; existing bundled assets remain usable, but this
local adapter is not a claim of completed online deployment.
