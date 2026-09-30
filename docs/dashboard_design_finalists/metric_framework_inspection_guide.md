# Metric Framework: how to inspect the evidence

This room has three selection dimensions: **painting → evidence lens → region**.
Reference, Damaged and Restored change the image underneath the diagnostic, not
the restoration case being evaluated. There is no additional model or mask picker.

## What the selected painting means

**Change painting** searches all 300 registered paintings by ID or title. Each
painting resolves its own canonical mixed-damage case and the canonical LaMa c00
restoration. The identity appears in the featured-case plaque. This stable case
is intentional: the room teaches how a measurement changes the interpretation
of the same restoration. Comparing models belongs in Model Gallery/Case Explorer.

**Surprise me** advances through the registered collection using the existing
deterministic sequence. It does not invent an image, change the model, or pick an
unrelated damage case. It preserves the current lens, valid region and image view.

The fresh-session default is p018, Restored, Spatial change & improvement,
Damaged area. Lens/region/view selections are remembered within the browser tab.
The selected painting is recorded in the URL so an explicit reload keeps it.
Painting changes rerender only the Metric Framework fragment; lens, region and
image-view changes are client-side and do not reload the browser.

## Reference, Damaged and Restored

- **Reference:** the clean digital image used by the evaluation.
- **Damaged:** that painting's controlled mixed-damage input.
- **Restored:** the corresponding recorded LaMa restoration.

These are three contextual views of one case. The diagnostic is deliberately
held constant when switching views, and the magnifier keeps its source position.
For example, Pixel difference always measures **restored versus reference**, even
when Damaged is the background. This lets you compare the same measured error
with the original content and the damage that prompted the repair. Selecting
Reference does not turn the diagnostic into a zero-error reference/self comparison.

Signed improvement additionally uses the damaged image as its baseline. Outside
change compares restored with damaged, not restored with reference.

## What each region selects

| Region | Evaluated support | Why choose it? |
|---|---|---|
| Whole image | Entire registered image, including preprocessing padding | Diagnostic overview; see why padding/unchanged area can dilute an average |
| Painting content | Recorded content rectangle, excluding preprocessing padding | Assess the painting rather than the surrounding canvas |
| Damaged area | Exact missing-region mask intersected with painting content | Examine what was repaired without averaging in untouched pixels |
| Damage crop | Rectangular damage bounding box plus 8 source pixels, clipped to content | Give image/feature metrics usable context around the repair |
| Boundary | Existing 3-pixel-width inner/outer boundary-band convention, clipped to content | Inspect a repair's transition into its surroundings |
| Outside repair | Painting content minus the damage mask | Find unintended edits away from the repair |
| Local patches | Actual 224×224 source windows, stride 112, at least 50% content | Compare local neighbourhoods using genuine window measurements |

The irregular mask is not interchangeable with its rectangular crop. Metrics
that require a contiguous image cannot be meaningfully evaluated by treating a
disconnected selection of pixels as a new picture. Those combinations are disabled.

## Every lens/region combination

P = primary evidence for this question; D = diagnostic/supporting evidence;
— = prohibited. These labels are measurement-policy roles, not quality grades.

| Evidence lens | Whole image | Painting content | Damaged area | Damage crop | Boundary | Outside repair | Local patches |
|---|---|---|---|---|---|---|---|
| Pixel difference | RGB error · D | RGB error · P | RGB error · P | RGB error · P | RGB error · P | RGB error · P | Window RGB error · D |
| Structure | SSIM deficit · D | SSIM deficit · P | — | SSIM deficit · P | — | — | Window SSIM deficit · D |
| Perceptual similarity | Spatial LPIPS · D | Spatial LPIPS · P | — | Spatial LPIPS · P | — | — | Window LPIPS · D |
| Learned visual features | CLIP/DINO · D | CLIP/DINO · P | — | CLIP/DINO · P | — | — | Window CLIP/DINO · D |
| Spatial change & improvement | Signed improvement · D | Signed improvement · P | Signed improvement · P | Signed improvement · D | Signed improvement · P | Outside alteration · P | Window improvement · D |
| Texture, colour & seams | ΔE2000 · D | Texture residual · P | ΔE2000 · P | Texture residual · P | Gradient mismatch · P | ΔE2000 · P | Window texture residual · P |
| Local meaning & layout | DINO/affinity · D | DINO/affinity · P | — | DINO/affinity · P | — | — | Window DINO/affinity · P |

That is seven lenses, seven regions, 37 enabled combinations and 12 prohibited
combinations. Signed improvement is a named measurement within the Spatial lens,
not an eighth lens.

When a lens makes the current region invalid, the old region is deselected and
the magnifier disappears. A reason is displayed and a compatible region is
recommended. Nothing silently substitutes another region: choose the recommendation
or another enabled region to continue. Disabled controls cannot be selected.

## What dragging the magnifier actually shows

The image outside the magnifier stays unmodified. Inside it, an aligned diagnostic
is overlaid on a 1.65× view of the same source location. Dragging moves that location;
it does not run a new restoration or change the measured case. Arrow keys also move
the magnifier; Shift moves faster. With Local patches, movement snaps between real
window centres and the dashed rectangle outlines the selected 224×224 window.

- **Pixel difference:** mean absolute RGB error at each source pixel, normalized
  to 0–1. MAE, MSE and PSNR are related region summaries (available in the plaque's
  tooltip), not separate pixel-level PSNR heatmaps.
- **Structure:** local `1 − SSIM`, using RGB, a 7-pixel window and data range 255.
  The unsupported 3-pixel edge is not presented as measured evidence.
- **Perceptual similarity:** the spatial LPIPS AlexNet v0.1 response, registered
  back to source coordinates after aspect-preserving resizing and removal of
  model padding. It is a coarse learned response; upsampling is not extra detail.
- **Learned visual features:** a split lens: local CLIP cosine distance on the
  left, local DINOv2 cosine distance on the right. Token cells remain visibly
  coarse; the two representations are not averaged into one score.
- **Spatial change & improvement:** damaged-to-reference error minus
  restored-to-reference error. Blue is improvement, red is worsening, pale is
  unchanged. In Outside repair, this switches to absolute restored-versus-damaged
  RGB alteration, because unintended change is the relevant question there.
- **Texture, colour & seams:** the region selects the appropriate measure.
  ΔE2000 measures digital colour difference, texture residual measures local
  energy difference, and Boundary uses normalized Sobel-gradient magnitude
  mismatch against the reference. These are three distinct questions, explicitly
  named in the plaque; they are not interchangeable scores.
- **Local meaning & layout:** a split lens: DINO local representation distance
  on the left and drift in token affinity to the reference's global representation
  on the right. This is a representation/layout proxy, not proof that a face,
  object, story, or historical meaning has been correctly reconstructed.

For Local patches, the colour encodes the actual window score nearest that
location. It is not a pixel attribution. The readout changes to the selected
window number and its measurement(s); overlapping windows are expected.

## Reading the display correctly

- **Grey hatching means not evaluated**, usually outside the chosen support or
  an unsupported model/window border. It does not mean zero error, good quality,
  or a failed restoration. A narrow boundary or sparse damaged mask can therefore
  occupy only a small part of the circular lens.
- Except for signed improvement, darker colours mean lower difference and brighter
  colours mean higher difference. The plaque states the fixed scale and units.
  Scales do not auto-stretch per painting, so a good restoration can look nearly
  dark under an error lens. This is not a broken or unchanged selector.
- The plaque's mean summarizes the selected support. The patch readout describes
  the currently selected window; those values need not equal the overall mean.
- Content/crop selection does not mean the entire painting is replaced by an
  enlarged crop: the support is applied to the aligned diagnostic. Whole image
  also shows the complete registered canvas so preprocessing padding is explicit.
- A map is evidence about a specified mathematical comparison, not a verdict on
  artistic quality or historical correctness. No universal quality score is made.

## Useful inspection sequences

1. **Did the repair help?** Spatial → Damaged area. Compare the same spot across
   Reference/Damaged/Restored; look for red as well as blue. Then choose Boundary
   to check whether improvement stops cleanly at the repair edge.
2. **Did it alter untouched content?** Spatial → Outside repair. Bright areas
   mean the restoration changed pixels outside the intended missing region.
3. **Why do pixel and perceptual results disagree?** Compare Pixel → Damage crop
   with Perceptual → Damage crop and Features → Damage crop. Keep the painting and
   image view fixed. Each metric captures a different type of discrepancy.
4. **Is the surface locally consistent?** Texture, colour & seams → Damage crop
   for texture; switch to Damaged area for colour, then Boundary for seams.
5. **Where did local layout change?** Local meaning & layout → Local patches.
   Move between outlined windows and compare both halves, then inspect the raw
   Reference and Restored views to interpret what the learned difference reflects.

## Data provenance and preservation

The source paintings, damaged/restored images, masks and evaluation tables already
exist locally. The new files under `streamlit_assets/evidence/metric_framework/`
are separately stored spatial inspection companions needed for this interaction.
They do not replace or modify frozen benchmark outputs or notebooks.

Each painting has a manifest with its exact painting/case/candidate identity,
source checksums, region supports, model/configuration provenance, asset checksums,
map scales and summaries, plus a numeric archive. The presentation loader refuses
missing, changed or mismatched evidence instead of silently substituting another
painting or showing a scalar as if it were a spatial map.

Spatial LPIPS/token-map means and window summaries are inspection diagnostics,
not claims of exact equivalence with every frozen benchmark scalar. Numeric
archives use float16 storage; summaries were computed before that quantization.
Colour-map displays may saturate at their stated limits; manifests record the
fraction beyond the display limits. Original measurements remain separate.

## Deferred to the user-led visual iteration

This pass establishes data/interaction correctness. Cabinet alignment, typography,
small-screen layout, selector width, caption space, plaque density and visual
contrast remain separately logged in `metric_framework_iteration_log.md` rather
than being treated as permission for another broad design pass.
