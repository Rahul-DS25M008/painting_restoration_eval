# Model Gallery — background and content readiness

Prepared 2026-09-30. Scope: approved sequence steps 1 and 2 only. No application
implementation, notebook edits, producer reruns, staging, commits or uploads.

## 1. Background shell

- Visual authority: `approved_current/06_model_gallery_final.png` (unchanged).
- New candidate: `../../streamlit_assets/rooms/model_gallery_shell.png`.
- Generation: built-in image generation, a faithful content-removal edit using
  the approved image as the edit target. Exact prompt: `model_gallery_shell_prompt.txt`.
- Both images are 1672 × 941 pixels; no aspect-ratio change.
- Shell SHA-256: `54cafbe20c496e322700445063f3bab32d707462c0241aaace397f937b891dfd`.

Visual inspection: the camera, rotunda, four alcoves, four coloured floor routes,
central easel, foreground table, information plaque, HINT book, three drawer
controls and separate low SDXL vitrine are preserved. Frame interiors, text
surfaces and navigation are blank so real evidence and live labels can be embedded.
No fifth alcove/route was introduced. Small selector thumbnails/icons will be
live overlays on the blank drawers, not baked into the background. Perspective
matching and clickable hit areas belong to step 3 and have not been implemented.
This is a candidate shell for user inspection, not a replacement of the approved reference.

## 2. Reference-to-content map

| Reference location | Embedded content | Readiness and source |
|---|---|---|
| Navigation and upper marble wall | Model Gallery title, opening question, historical-truth boundary | Approved page contract; existing shared nav pattern can be reused without editing earlier rooms |
| Central easel and caption | Exact damaged image; painting and damage identity | N04/N08 case records; default `canonical__p018__mixed_damage` exists, 768×768 |
| Four framed alcoves | Telea, LaMa, HINT, Stable Diffusion results | All four have the same 2,620 primary cases; every completed output path checked and present |
| Alcove headings | Model name, family, deterministic/stochastic description | Approved page contract plus five N30 model cards |
| Four floor routes | Model-selection hit areas and active-method indication | Static route artwork present; interaction to implement |
| Foreground slanted picture | Selected method's exact output or valid local crop | Source image and region-qualified metrics available; derive display crop at rendering time, not new inference |
| Central information plaque | Model description, strengths/cautions, coverage, recorded runtime, full-record link | N30 model cards and N31 reports available; source qualifiers retained |
| Painting drawer | Real painting selector | 300 paintings, with existing metadata and clean-reference paths |
| Damage drawer | Actual cases belonging to selected painting | 2,620 common primary case IDs; join producer metadata, not a static menu |
| Evidence drawer | Default Crop SSIM and supported alternatives | N13 exact candidate/metric/region rows; no fabricated values where unsupported |
| HINT book | Why HINT was selected | N37 decision JSON, decision scorecard and HTML report exist; separate 12-case decision study |
| Low right vitrine | Exact SDXL result or unavailable state | 24 completed cases across 19 paintings; one timeout and ten skipped among 35 scheduled |
| Table-front conclusion | LaMa 10/11 anchors, Telea crop SSIM | N21 overall registered comparison confirms it; must retain separate-comparisons/no-combined-score qualifiers |
| Side inscriptions | Cautious interpretive copy | Most source wording can be reused; flag “A clearer past” for replacement because it implies recovered history |

### Verified opening evidence

All five p018 restored images decode at 768×768 and match their recorded SHA-256.
The clean reference, damaged input and mask also decode at 768×768. Crop SSIM
rows for the exact five selected candidates all have status `ok`:

| Method | p018 mixed-damage crop SSIM |
|---|---:|
| Telea | 0.961546 |
| LaMa | 0.968558 |
| HINT | 0.948996 |
| Stable Diffusion | 0.932026 |
| SDXL, bounded study only | 0.891906 |

These are case-specific values, not the population ranking. The SD opening uses
`sd15__p00__s2026__d0cd65cf894a`, seed 2026, prompt variant `p00_generic`.
No other seed, prompt or painting may be substituted silently.

All five full model reports exist and match the N31 report-index checksums.
Recorded median runtimes match the approved labels: Telea 0.519 s, LaMa 1.451 s,
HINT 6.677 s, SD 8.620 s, bounded SDXL 198.031 s. These describe the recorded
workstation, not portable quality/performance rankings.

### Coverage and selector rules

- Four-method intersection: **2,620 cases / 300 paintings**, with no duplicated
  primary case per method. All completed output paths checked: 2,620 each for
  Telea/LaMa/HINT; 8,520 SD candidates including primary and additional runs;
  24 completed SDXL candidates. No missing output files found.
- Input/clean/mask paths needed by all primary SD case rows also exist.
- Case groups: 1,500 canonical, 245 damage-size, 525 mask-robustness and 350
  eligible synthetic-degradation cases. The damage drawer should retain these
  identities and semantics. Supplementary synthetic masked-removal cases must
  not be described as general damage removal or recovered historical content.
- Crop SSIM has 2,320 valid rows per deterministic full-scope method; the 300
  zero-control cases do not have a damage-bounding crop. Disable that evidence
  choice for those cases. Alternative evidence must have an actual valid row.
- The N21 headline is the overall registered comparison, separate from “This
  case”. Ten anchors use 2,320 eligible non-zero cases; structural affinity has
  2,620. A 2,620 population label must not imply every metric has that denominator.
- SDXL must match **case ID**, not merely painting ID. A painting with one SDXL
  result does not imply all its damage variants have results. Closed/unavailable
  vitrine states are intentional, not missing implementation assets.
- Keep the SD candidate seed/prompt visible in model details; primary candidates
  provide a deterministic opening, additional seed studies remain in Stability Lab.

### Remaining gaps before a functional first pass

1. **UI data adapter, not missing scientific data.** The N34 room file has 12
   display-contract records and 19 bindings, not a complete interactive gallery
   catalogue. Step 3 must join painting/case/candidate records and bind the drawers.
2. **Perspective and geometry.** Existing source files are square 768×768 canvases;
   the scene's frames are quadrilaterals. Plan image fitting and transformed hit
   areas together so inspection coordinates and frames agree. Not tested in-browser yet.
3. **Availability states and scientific wording.** Implement the distinctions
   above. Internal population ID `core_three_model` contains four methods and
   must not be exposed as a claim that only three were compared.
4. **Later hosting audit.** N34 registers the opening gallery images and their
   immutable locators. This pass checks local broader coverage, not every remote
   selectable case. No new HF calls, publication or Streamlit deployment attempted.

**Conclusion:** No missing core local content blocks the first implementation.
The background and opening-case evidence are ready for review; the interaction
adapter and cosmetic fitting are the next approved step, not completed work.

## Reproducibility

Audit script: `../../tools/audit_model_gallery_readiness.py`.
Detailed results: `model_gallery_readiness_audit.json`.
The audit checks existence for the full candidate population, and decodes/hashes
the opening restoration images and hashes full reports. It does not recompute
metrics, hash/decode every other candidate, or test browser interactions.
