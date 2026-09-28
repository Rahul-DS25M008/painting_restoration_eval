# Notebook Revision and Defence Q&A

## Purpose

This is the cumulative revision guide for the completed research pipeline. It
starts again from Notebook 01 and will be extended only after each notebook quiz
has been answered and verified against repository evidence.

Every notebook section must distinguish four things:

1. **Method** — what was actually done and how it was checked.
2. **Population** — exactly which paintings, cases, candidates, regions, or
   records the result covers.
3. **Strongest defensible claim** — the most that the evidence supports.
4. **Limitation** — what the evidence does not establish.

Technical terms are explained in plain language so this file can be used for
revision, supervisor discussions, and thesis-defence preparation.

## Progress

| Notebook | Topic | Quiz status |
|---|---|---|
| 01–12 | Dataset construction, contracts, and initial restoration producers | Completed and verified |
| D01 | HINT-versus-MAT method selection | Completed with reference answers |
| 12A | Full HINT restoration | Completed with reference answers |
| 13–21 | Metrics, diagnostics, uncertainty, semantics, and model comparison | Completed and verified |
| D02 | Portrait, hand, and rendered-skin-tone audit | Completed with reference answers |
| 22–30 | Extensions, stress tests, statistics, flags, XAI, and model cards | Completed and verified |
| 31–33 | Model, case, painting, and final evaluation reports | Completed with reference answers |

---

## 01 — Dataset Verification

### Repository evidence

- Notebook: `notebooks/01_dataset_verification.ipynb`
- Dataset configuration: `config/datasets/controlled_300.yaml`
- Accepted artwork registry:
  `outputs/01_dataset_verification/data/artworks.csv`
- Scientific audit:
  `outputs/01_dataset_verification/metrics/dataset_audit.csv`
- Validation checks:
  `outputs/01_dataset_verification/validation/checks.csv`
- Run manifest:
  `outputs/01_dataset_verification/manifests/run_manifest.json`

### Key terms

- **Operational visual category:** a broad grouping created for this study so
  that visually different paintings can be sampled in equal numbers. It is not
  a validated art-historical style, movement, period, or genre taxonomy.
- **SHA-256:** a cryptographic fingerprint of the file bytes. Matching SHA-256
  values provide the byte-level exact-duplicate test used in N01.
- **dHash:** a small perceptual fingerprint. N01 applies EXIF orientation,
  converts the image to grayscale, resizes it to a 9 × 8 grid, and encodes 64
  horizontal neighbour comparisons. It therefore represents relative
  luminance-gradient structure rather than exact colour or pixel equality.
- **Hamming distance:** the number of bit positions at which two hashes differ.
  A smaller distance means more similar hashes. N01 sent pairs with a 64-bit
  dHash distance of **5 or less** to near-duplicate review.
- **Provenance:** the recorded source and rights information associated with an
  artwork. Recording provenance is not the same as issuing a universal legal
  guarantee.

### Q1. What was the exact N01 population, how was it balanced, and what do the
categories represent?

**Your answer**

> The population contained 300 paintings, balanced using exactly 60 unique
> paintings across five categories. The categories are broad visual categories,
> not historical styles, artwork styles, or periods.

**Assessment: Correct.**

**Verified reference answer**

N01 accepted **300 unique paintings**, with **60 paintings in each of five
broad operational visual categories**:

- portrait/figure;
- landscape/natural;
- architecture/structured;
- abstraction/surrealism; and
- high-texture/brushwork.

The categories are complete within-study grouping variables. They are not
independently validated art-historical styles and do not make the collection
representative of painting history, periods, movements, geography, or real
conservation populations.

### Q2. How did SHA-256 and dHash serve different purposes, what threshold was
used, and why does dHash distance zero not establish byte identity?

**Your answer**

> SHA-256 tests exact byte-level equality. dHash checks image brightness
> patterns, and a Hamming distance of five or less means a pair is near
> identical in brightness.

**Assessment: Mostly correct, with one important overclaim corrected.**

**Verified reference answer**

- **SHA-256** was used to detect exact byte-identical files.
- **64-bit dHash** was used as a perceptual near-duplicate screening method. It
  mainly represents relative luminance-gradient structure rather than exact
  colours or exact pixels.
- A **Hamming distance of 5 or less** marked a pair as a near-duplicate
  *candidate requiring review under the declared rule*.
- A distance of zero means the two dHash values are identical. It does not prove
  that the underlying files are byte-identical; SHA-256 performs that test.

Therefore, the threshold does not prove that two paintings are near-identical
in brightness. It identifies unusually similar perceptual hashes. dHash may be
tolerant of minor compression, resizing, or tonal changes, but it can also miss
similarity created by crops, rotations, composition changes, or semantic
redundancy.

### Q3. What did the duplicate checks find, and what is the strongest conclusion
allowed by those findings?

**Your answer**

> There were zero exact duplicates and zero near duplicates.

**Assessment: Correct finding; the conclusion needs the declared-method
boundary.**

**Verified reference answer**

N01 found:

- **zero exact-duplicate groups** using SHA-256; and
- **zero near-duplicate candidate pairs** at the declared dHash Hamming-distance
  threshold of 5 or less.

The strongest defensible conclusion is that **the declared tests found no exact
or threshold-defined near-duplicate issue**. It would be too strong to say that
every conceivable kind of visual, semantic, cropped, rotated, or
composition-level redundancy has been ruled out.

### Q4. How complete was the historical metadata, why did missing values not
invalidate paintings, and why is visual category the complete grouping
variable?

**Your answer**

> Historical metadata were complete for 268 paintings. The other paintings are
> still valid because missing metadata does not mean that the image is damaged
> or not representative of its assigned category. It is not a roadblock. Visual
> category is complete for all 300 paintings and was the organizing feature used
> while gathering the collection.

**Assessment: Correct, with one wording refinement.**

**Verified reference answer**

Date or period, style or period, and medium were recorded for **268 of 300
paintings**; 32 paintings had only partial prompt/historical metadata. Those
missing optional fields do not invalidate the digital files or their use in the
controlled restoration benchmark. They limit analyses that depend on those
fields.

Visual category is the complete grouping variable because it is populated for
all 300 paintings and the collection was deliberately sampled at 60 paintings
per category. Missing metadata is not evidence that an artwork is invalid, but
neither should it be treated as evidence that the artwork increases diversity
or representativeness.

### Q5. What did the source audit find, and what does it imply for
representativeness?

**Your answer**

> There were 32 source labels, and the largest source contributed 109 paintings.
> The collection does not establish historical representation because it only
> has technical category balance.

**Assessment: Correct.**

**Verified reference answer**

The registry contains **32 recorded source labels**, but the largest source,
the Cleveland Museum of Art, contributes **109 of 300 paintings**. Source
coverage is therefore broader than a single-institution collection but remains
concentrated.

Equal visual-category counts do not establish equal institutional, historical,
geographical, cultural, or period representation. Selection was also restricted
to material with usable digitization and public-domain/open-access rights
information, creating an acquisition-availability bias.

### Q6. What rights/provenance claim is supported, and what legal overclaim must
be avoided?

**Your answer**

> The paintings are open source and free to use, but we should avoid claiming
> that we are free to do whatever we want with them.

**Assessment: Correct boundary in spirit, but “open source” and “free to use”
are too broad.**

**Verified reference answer**

N01 records the available source, licence, and rights-category information and
checks each accepted source/licence pair against the declared configuration.
The records use labels such as public domain, CC0, Public Domain Mark, and open
access.

The images should not collectively be described as “open source,” and the audit
does not prove unrestricted use in every setting. It is **recorded provenance
and rights information**, not a blanket legal conclusion for every
jurisdiction, redistribution channel, derivative use, commercial use, or future
downstream application.

### Q7. State the strongest defensible N01 claim and the main limitations that
must accompany it.

**Your answer**

> The collection is complete, duplicate-checked, and exactly category-balanced,
> but it does not represent all painting traditions. It does not establish
> historical-period coverage, art-style variety, or complete freedom of use.

**Assessment: Good core claim, expanded below so the principal limitations are
not lost.**

**Verified reference answer**

> The Controlled-300 collection passed the declared technical integrity,
> metadata-to-file correspondence, provenance-field, and duplicate-screening
> checks and is exactly balanced across five operational visual categories.

This claim must retain the following limitations:

- The categories are not validated art-historical styles, movements, or
  periods.
- The collection is not population-representative of painting history,
  geography, cultures, source institutions, or real conservation conditions.
- Date/period, style/period, and medium remain incomplete for 32 paintings.
- Source representation remains concentrated despite the 32 recorded labels.
- Duplicate screening is limited to exact SHA-256 comparison and the declared
  dHash review rule; it does not rule out every form of semantic or transformed
  redundancy.
- Rights fields are recorded provenance categories, not universal legal
  certification.
- Dataset verification establishes technical and metadata suitability for this
  controlled computational study; it does not establish historical
  authenticity, conservation suitability, or museum-professional validation.

### N01 defence summary

| Required distinction | Verified answer |
|---|---|
| Method | Validate metadata-to-file correspondence, image readability and declared constraints; check exact duplicates with SHA-256; screen near duplicates with 64-bit dHash at Hamming distance ≤5; audit metadata, sources, rights fields, and category distribution. |
| Population | 300 accepted paintings, exactly 60 in each of five operational visual categories. |
| Strongest defensible claim | The exact Controlled-300 collection passed all declared N01 technical, correspondence, provenance-field, and duplicate-screening checks and is category-balanced for within-study evaluation. |
| Limitation | The study does not establish population-level historical, geographic, stylistic, cultural, institutional, legal, conservation, or museum-validity claims. |

### N01 result

**Completed.** The learner correctly understands the population, category
contract, metadata boundary, source concentration, and overall claim. The two
important corrections to retain are that dHash is a screening method rather
than proof of visual identity, and that recorded public-domain/open-access
metadata are not a universal legal guarantee.

---

## 02 — Image Preprocessing

### Repository evidence

- Notebook: `notebooks/02_image_preprocessing.ipynb`
- Configuration: `config/preprocessing/canonical_768.yaml`
- Preprocessed-image registry:
  `outputs/02_image_preprocessing/data/preprocessed_images.csv`
- Preprocessing audit:
  `outputs/02_image_preprocessing/metrics/preprocessing_audit.csv`
- Validation checks:
  `outputs/02_image_preprocessing/validation/checks.csv`
- Run manifest:
  `outputs/02_image_preprocessing/manifests/run_manifest.json`

### Key terms

- **EXIF orientation:** camera/file metadata describing how stored pixels should
  be rotated or mirrored for display. N02 accepts orientation 1, meaning the
  stored pixels already have the expected orientation, and blocks non-default
  orientations rather than silently transforming them.
- **ICC profile:** embedded metadata describing how stored colour values should
  be interpreted. A profile is not another image format.
- **sRGB:** the common target colour space used by this pipeline.
- **Lanczos interpolation:** a high-quality resampling method used to estimate
  pixel values when an image is resized. It is still a lossy transformation.
- **Round half up:** the explicit dimension-rounding rule: a fractional value
  ending in .5 is rounded upward rather than using banker's rounding.
- **Median-RGB padding:** artificial canvas filled using the median red, green,
  and blue values of the working source pixels. It is technical canvas content,
  not part of the painting.
- **`xyxy` exclusive:** a box stored as minimum x/y and maximum x/y coordinates,
  where the maximum coordinates sit just outside the included region. Width is
  therefore `x_max - x_min`, and height is `y_max - y_min`.

### Q1. What population entered N02, and what exact outputs were produced?

**Your answer**

> Three hundred paintings entered. Outputs were 767/768, RGB PNG files, with one
> output for every painting except one that did not need processing.

**Assessment: Partly correct. The canvas size and exception statement required
correction.**

**Verified reference answer**

All **300 N01-accepted paintings** entered N02. N02 produced:

- **300 output images**;
- every image exactly **768 × 768 pixels**;
- RGB colour mode;
- PNG format; and
- one `preprocessed_images.v1` table row per painting.

All 300 sources were downscaled. One square source, p036, required no padding,
but it was not excluded from processing: it was downscaled from 3000 × 3000 to
768 × 768 and received a validated RGB PNG output and geometry record. The
**resized source-image dimension** may sometimes be 767 pixels along one axis
because of aspect-ratio fitting and explicit rounding, but the final canvas is
always 768 × 768.

### Q2. What was the complete transformation method?

**Your answer**

> EXIF is checked first; orientation 1 passes and another value fails. The ICC
> profile is checked: missing is assumed sRGB, sRGB is retained, and a different
> profile is converted to sRGB. Lanczos resizing preserves the width/height
> ratio, the image is centred in a 768 × 768 canvas, borders use median RGB, and
> extra pixels go to the right or bottom.

**Assessment: Substantially correct; the exact scale and rounding rules were
missing.**

**Verified reference answer**

For an oriented working image of width `W` and height `H`, N02:

1. verifies that EXIF orientation is 1;
2. applies the configured ICC branch and obtains an RGB working image;
3. computes the fit-inside scale as `min(768 / W, 768 / H)`;
4. computes resized dimensions using explicit round-half-up behaviour;
5. resizes with Pillow Lanczos interpolation;
6. preserves aspect ratio without cropping or stretching;
7. computes the per-channel median RGB colour from the working source pixels;
8. creates a 768 × 768 canvas in that colour;
9. centres the resized image on the canvas; and
10. assigns any indivisible one-pixel padding remainder to the right or bottom.

The declared method is `aspect_ratio_resize_median_rgb_pad`, version `2.1.0`.
Output metadata and ICC profiles are stripped, and PNG compression settings are
fixed by configuration.

### Q3. What geometry was recorded, and why is it authoritative downstream?

**Your answer**

> N02 recorded resize scale, four padding amounts, and the `xyxy` content box.
> Downstream notebooks use this to identify painting pixels for mask generation,
> restoration, and metric calculation.

**Assessment: Correct core idea, but the record and coordinate contract are
broader than stated.**

**Verified reference answer**

For every painting, N02 records:

- original width and height;
- resize scale and resized width and height;
- top, bottom, left, and right padding;
- padding RGB colour;
- content and padding areas and fractions;
- canvas dimensions; and
- the exact painting-content bounding box.

The box is zero-based `xyxy` with **exclusive maximum coordinates**. It marks
the pasted resized source-image rectangle, not a semantic segmentation of the
physical painting. Later notebooks must use these stored bounds so that masks
remain inside source-image support and region-sensitive metrics exclude
artificial padding. Inferring the boundary from padding colour would be unsafe
because genuine source-image pixels may happen to resemble that colour.

### Q4. How were EXIF orientation and ICC colour profiles handled?

**Your answer**

> Default EXIF passes and non-default EXIF fails. Without ICC, assume sRGB; with
> embedded sRGB, retain the pixels and strip the profile; with non-sRGB, convert
> to sRGB.

**Assessment: Correct policy, with counts and the scientific limitation added
below.**

**Verified reference answer**

- All 300 sources had EXIF orientation 1. A non-default value would block the
  run rather than trigger an undocumented rotation.
- **261 images without an embedded ICC profile:** assumed sRGB with no pixel
  conversion.
- **19 images with an embedded sRGB profile:** pixels preserved and profile
  stripped from the output.
- **20 images with an embedded non-sRGB profile:** converted to sRGB using a
  perceptual rendering intent.
- All outputs are RGB PNG files with output ICC metadata removed.

This proves that the run followed a declared and validated colour-management
policy. It does **not** prove perfect colourimetric fidelity. In particular, the
261 missing-profile images rely on an assumption rather than verified source
colour-space metadata.

### Q5. What evidence demonstrated successful preprocessing?

**Your answer**

> All 300 paintings produced 300 outputs and the validation checks passed.

**Assessment: Correct but far too incomplete for a defence answer.**

**Verified reference answer**

The completed run recorded:

- 300 accepted inputs, 300 preprocessing rows, and 300 clean PNG files;
- exactly 768 × 768 RGB PNG output for every painting;
- **50 of 50 consolidated validation checks passed**;
- 45 audit rows and a passed 23-requirement completion gate;
- zero failed, missing, stale, or orphaned outputs;
- zero reload, dimension, mode, format, saved-checksum, or duplicate-output-hash
  failures;
- zero source-reference, resize-scale, resized-dimension, padding-dimension,
  content-box, area-fraction, or padding-pixel reconciliation failures; and
- zero orientation/colour-policy failures.

Padding orientation was left/right for 138 images, top/bottom for 161, and
absent for one image. The recorded image-processing runtime was approximately
325.3 seconds on the documented machine, with one finite positive runtime per
painting. Runtime is operational evidence, not a portable performance promise.

The 50/50 result establishes compliance with the **declared repository
contract for this exact run**. It does not validate historical appearance,
aesthetic quality, physical conservation correctness, or universal suitability
of the preprocessing method.

### Q6. What is the strongest defensible claim, and why are two tempting
interpretations invalid?

**Your answer**

> Every painting is now technically processed and validated. Not every pixel is
> painting content because resizing can add a boundary. The clean image is not
> historical ground truth because we processed it.

**Assessment: Right direction, but the claim needed exact scope and the
historical-ground-truth explanation needed correction.**

**Verified reference answer**

> For the exact Controlled-300 population and declared configuration, N02
> deterministically produced one contract-compliant 768 × 768 RGB PNG and one
> authoritative content-geometry record per accepted source, with all declared
> technical integrity and reconciliation checks passing.

Two stronger interpretations are invalid:

1. **“Every output pixel is painting content.”** False. Aspect-ratio-preserving
   fitting creates artificial median-RGB padding for 299 of the 300 images. The
   recorded content box separates painting content from technical canvas.
2. **“The clean image is historical ground truth.”** False. It is a normalized
   digital reference derived from the supplied museum/open-access digitization.
   Neither the source file nor this transformation establishes the physical
   painting's original historical appearance, material authenticity, complete
   extent, or correct conservation treatment. The problem is not simply that
   N02 processed the file.

### Q7. What are the principal N02 limitations?

**Your answer**

> No answer provided.

**Assessment: Supplied below as required revision material.**

**Verified reference answer**

- All 300 sources were downsampled. Lanczos resampling is lossy and cannot
  reconstruct discarded source detail; it may also alter high-frequency texture
  or introduce interpolation effects.
- “No crop or stretch” describes treatment of the supplied digital file; it
  does not prove that the digitization contains the complete physical painting.
- Median-RGB padding is artificial and must be excluded using the stored content
  bounds.
- The 261 missing-profile images rely on an sRGB assumption rather than verified
  source colourimetry.
- Conversion to sRGB and profile stripping demonstrate consistent policy, not
  perfect preservation of perceived or measured colour.
- The clean PNG is a standardized computational reference, not historical or
  physical ground truth and not conservation validation.
- Recorded runtimes depend on the current CPU, storage, software environment,
  and system load.
- N02 inherits N01's sampling, source-concentration, metadata, provenance, and
  representativeness limitations.

### N02 defence summary

| Required distinction | Verified answer |
|---|---|
| Method | Apply the declared EXIF and ICC policy, fit each source inside 768 × 768 with round-half-up dimensions and Lanczos interpolation, centre it on per-channel median-RGB padding, strip output metadata, and validate pixels, files, geometry, checksums, audit evidence, and handoffs. |
| Population | All 300 N01-accepted paintings; 300 validated RGB PNGs and 300 authoritative geometry records. |
| Strongest defensible claim | The exact Controlled-300 sources were deterministically normalized into contract-compliant 768 × 768 computational references with all declared technical and reconciliation checks passing. |
| Limitation | Technical normalization does not establish perfect colour fidelity, historical truth, physical completeness, aesthetic quality, conservation suitability, or representativeness beyond N01. |

### N02 result

**Completed with corrections.** The learner understands the main processing
sequence, aspect-ratio preservation, padding policy, geometry handoff, and ICC
branches. The important additions are the exact 768 × 768 output contract,
round-half-up rule, exclusive-coordinate convention, ICC population counts,
full validation evidence, scoped scientific claim, and explicit limitations.

---

## 03 — Canonical Mask Generation

### Repository evidence

- Notebook: `notebooks/03_canonical_mask_generation.ipynb`
- Configuration: `config/masks/canonical_binary.yaml`
- Canonical mask registry:
  `outputs/03_canonical_mask_generation/data/masks.csv`
- Mask collection:
  `outputs/03_canonical_mask_generation/images/masks/`
- Scientific audit:
  `outputs/03_canonical_mask_generation/metrics/mask_audit.csv`
- Method protocol:
  `outputs/03_canonical_mask_generation/reports/mask_protocol.md`
- Validation checks:
  `outputs/03_canonical_mask_generation/validation/checks.csv`
- Run manifest:
  `outputs/03_canonical_mask_generation/manifests/run_manifest.json`

### Key terms

- **Binary mask:** a grayscale image containing only 0 and 255. Here, 0 means
  unaffected background and 255 identifies the synthetic missing region.
- **Damaged-content fraction:** damaged pixels divided by pixels inside N02's
  recorded source-image content box. It is not divided by the complete padded
  768 × 768 canvas.
- **Connected component:** one contiguous group of damaged pixels. Component
  counts help distinguish scattered losses from one large loss.
- **Bounding-box fill ratio:** the fraction of a mask's bounding rectangle that
  is actually filled by damaged pixels. A long thin scratch normally has a low
  fill ratio.
- **Component aspect ratio:** how elongated a connected region is. Higher values
  provide evidence of scratch-like geometry.
- **Deterministic replay:** regeneration using the recorded configuration,
  implementation, seed hierarchy, and retry evidence to test whether the same
  mask pixels are reproduced.
- **Synthetic evaluation instrument:** deliberately generated test geometry used
  for controlled comparison. It is not an annotation of observed physical
  damage.

### Q1. What was the exact N03 population, and why are not all 1,500 masks
damaged cases?

**Your answer**

> There were 300 paintings, five mask families, 300 masks per family, and 1,500
> masks overall. Three hundred are zero controls, so calling all 1,500 damaged
> would be incorrect.

**Assessment: Correct.**

**Verified reference answer**

N03 creates exactly one uniquely identified mask for every painting–family pair:

- 300 paintings;
- five mask families;
- 300 masks per family; and
- 1,500 masks overall.

The population contains **300 empty zero controls** and **1,200 nonzero
synthetic-damage masks**. Therefore, 1,500 is the mask/case count, not the count
of nonzero damaged masks.

### Q2. What are the five mask families, how are they generated, and what are
their area contracts?

**Your answer**

> The families are scratch thin, zero control, loss small, loss large, and
> mixed. Scratch thin uses thin long lines, loss small uses several small blobs,
> loss large uses one or two large blobs, and mixed combines scratches and
> losses. The approximate targets are 2%, 4%, 12%, and 11%.

**Assessment: Family concepts were understood, but the exact targets, permitted
ranges, and mixed composition required correction.**

**Verified reference answer**

| Family | Generator design | Lower bound | Target | Upper bound |
|---|---|---:|---:|---:|
| `zero_control` | Empty all-zero mask | 0% | 0% | 0% |
| `scratch_thin` | 8–16 thin polyline scratches, each with 3–6 segments and width 2–5 pixels | 1% | 2% | 3% |
| `loss_small` | 4–8 localized irregular polygonal blobs | 3% | 4.5% | 6% |
| `loss_large` | 1–2 large irregular polygonal blobs | 10% | 12.5% | 15% |
| `mixed_damage` | Binary union of scratches, scattered small losses, one medium loss, and one edge-touching loss | 8% | 11.5% | 15% |

The target is an aim, not an exact required result. A generated mask passes when
its damaged-content fraction lies inside its closed lower–upper interval. N03
also records a separate fraction relative to the full canvas.

The mixed family does not simply paste the canonical `loss_small` and
`loss_large` masks together. It independently generates its configured scratch,
small-loss, medium-loss, and boundary-loss components and unions them.

### Q3. How was generation made reproducible, and what does deterministic
replay establish?

**Your answer**

> Seeds 2026–2029 are used so masks are reproducible. There are 30 maximum
> generation attempts, and deterministic replay proves that masks cover the
> same pixels when execution is repeated.

**Assessment: The retry count and replay idea were correct, but the seed values
belonged to a later Stable Diffusion experiment.**

**Verified reference answer**

N03 uses:

- global seed **20260630**;
- a deterministic painting seed;
- a deterministic family/mask seed; and
- a deterministic retry seed for each attempt.

Seeds 2026–2029 belong to the later Stable Diffusion repeated-candidate design,
not canonical mask generation.

Each nonzero mask receives up to **30 attempts**. The first candidate inside its
closed permitted area interval is accepted. If no valid candidate is found,
generation blocks rather than silently accepting an invalid mask. In the
completed run, one `loss_large` mask reached the 30th attempt, but there were
zero generation failures.

All 1,500 deterministic replays matched their stored pixels, seeds, parameters,
and retry evidence. This establishes reproducibility under the recorded
generator version, configuration, and software method. It does not prove that
the masks are realistic, historically correct, or byte-identical under every
possible future implementation or environment. Run identifiers, timestamps,
and runtimes are intentionally run-dependent.

### Q4. How did N03 use N02 geometry, what is the damage denominator, and why is
padding excluded?

**Your answer**

> Reference answer requested rather than a learner answer.

**Verified reference answer**

N03 consumes N02's authoritative zero-based `xyxy` exclusive content box for
each painting. Candidate geometry is clipped to this rectangle, which denotes
resized source-image support rather than a semantic segmentation of the
physical painting.

`damaged_content_fraction` is:

> damaged pixels inside the content box ÷ total pixels inside the content box.

The full-canvas damage fraction is recorded separately. Technical median-RGB
padding is never eligible for damage because it was introduced by N02 and is not
source-image evidence. Using the full canvas would make damage percentages vary
with aspect ratio and could place synthetic loss in artificial padding. The
completed run recorded zero padding-overlap failures.

### Q5. What are the file and morphology contracts, and how were families shown
to differ?

**Your answer**

> Reference answer requested rather than a learner answer.

**Verified reference answer**

Every saved mask must be:

- exactly 768 × 768 pixels;
- PNG format;
- grayscale mode `L`;
- composed only of values 0 and 255;
- restricted to N02 content support; and
- stored at the deterministic path
  `images/masks/<painting_id>/<mask_type>.png`.

N03 records connected-component counts and sizes, perimeter, compactness,
bounding boxes, fill ratios, aspect ratios, variability, largest-component
fraction, and distance/touching relationships to the content boundary.

The full-population family checks included:

- scratch median bounding-box fill ratio ≤ 0.05 and median maximum component
  aspect ratio ≥ 3;
- small-loss median component count ≥ 3;
- large-loss median damaged fraction at least twice that of small loss and
  median largest-component fraction ≥ 0.75;
- mixed median component count ≥ 4, boundary-touch fraction ≥ 0.80, and median
  maximum component aspect ratio ≥ 2; and
- zero pixel-equivalent family pairs for the same painting.

All configured expectations passed. These checks show that the implemented
families satisfy deliberately different technical morphology contracts. They do
not prove resemblance to the real-world frequency or physics of painting
damage.

### Q6. What does the zero control establish, and why does it not prove that
models avoid hallucination?

**Your answer**

> Reference answer requested rather than a learner answer.

**Verified reference answer**

Each zero control is an all-zero mask with:

- zero damaged pixels;
- zero connected components; and
- no missing-region corruption.

N03 establishes only that 300 correctly encoded empty controls exist and are
paired with the correct paintings. It does not run a restoration model, alter
an image, or demonstrate model behaviour.

Conceptually, running a model with an empty mask could test unnecessary
alteration. However, the implemented downstream restoration pipeline treats
zero controls as identity/no-op baselines and bypasses restoration inference,
carrying the clean reference forward. Consequently, these controls validate
case accounting and the identity baseline; they do **not** empirically show
that Telea, LaMa, Stable Diffusion, HINT, or SDXL refrain from hallucinating when
given an empty mask.

### Q7. What evidence supports completion, what is the strongest claim, and
what limitations must be retained?

**Your answer**

> Reference answer requested rather than a learner answer.

**Verified reference answer — evidence**

The completed run contains:

- 1,500 registry rows and 1,500 mask PNGs;
- 300 masks in each of five families;
- 105 scientific-audit rows;
- 50 validation rows, with **50 of 50 checks passed**;
- a passed 24-requirement completion gate;
- seven artifact records, two figures, and one methodology protocol; and
- zero failed generations, missing, stale, orphaned, nonbinary,
  padding-overlapping, area-out-of-range, morphology-failing,
  checksum-mismatched, deterministic-replay-failing, duplicate-nonzero, or
  cross-family-equivalent masks.

The recorded generation runtime was approximately 1,124.4 seconds, or 18.7
minutes, on the documented machine. This is environment-specific operational
evidence.

**Strongest defensible claim**

> For the exact Controlled-300 population, N03 produced one versioned,
> deterministic binary synthetic missing-region mask for every painting–family
> pair. All 1,500 masks were restricted to N02 source-image support, satisfied
> their configured area and family-morphology rules, and passed saved-file and
> deterministic-replay validation.

**Principal limitations**

- The masks are controlled synthetic evaluation instruments, not annotations of
  observed or historically verified damage.
- Configured family shapes and thresholds enable controlled comparison; they
  are not an empirical model of the real distribution of conservation damage.
- The binary protocol intentionally excludes blur, fading, discolouration,
  dirt, dust, stains, partial transparency, and other non-binary or
  material-specific degradation.
- Geometry is content-box constrained but not conditioned on depicted objects,
  brushwork, material chemistry, crack mechanics, or conservation history.
- One canonical realization per painting–family pair cannot establish
  robustness to alternative placements and shapes; the later bounded mask
  robustness experiment addresses that separate question.
- Morphology validation is a technical sanity check, not proof of visual,
  physical, historical, or conservation realism.
- N03 inherits N01's sampling, source, metadata, rights, and representativeness
  limitations and N02's digitization, downsampling, colour-policy, and padding
  limitations.
- Runtime is specific to the recorded CPU, storage, software environment, and
  system load.

### N03 defence summary

| Required distinction | Verified answer |
|---|---|
| Method | Generate five versioned mask families with a hierarchical deterministic seed scheme, content-box clipping, bounded area retries, binary encoding, morphology audits, saved-file reconciliation, and full deterministic replay. |
| Population | 300 paintings × five families = 1,500 masks: 300 empty controls and 1,200 nonzero synthetic-damage masks. |
| Strongest defensible claim | The exact Controlled-300 run produced a complete, deterministic, content-constrained canonical synthetic-mask benchmark satisfying every declared technical area, morphology, file-integrity, and replay rule. |
| Limitation | Contract compliance and reproducibility do not establish real-damage prevalence, physical realism, historical correctness, robustness to every mask placement, or conservation validity. |

### N03 result

**Completed with taught reference answers.** The learner correctly identified
the population and broad family concepts. The seed hierarchy, exact target
ranges, N02 geometry contract, morphology validation, zero-control boundary,
strongest claim, and limitations were supplied and corrected from repository
evidence for later revision.

---

## 04 — Canonical Damaged-Image Generation

### Repository evidence

- Notebook: `notebooks/04_canonical_damaged_image_generation.ipynb`
- Configuration: `config/experiments/canonical_damage.yaml`
- Case registry: `outputs/04_canonical_damaged_image_generation/data/cases.csv`
- Damage audit:
  `outputs/04_canonical_damaged_image_generation/metrics/damage_audit.csv`
- Validation checks:
  `outputs/04_canonical_damaged_image_generation/validation/checks.csv`
- Run manifest:
  `outputs/04_canonical_damaged_image_generation/manifests/run_manifest.json`

### Q1. What was the population and output?

- 300 N02 clean images × five N03 mask families.
- 1,500 cases and 1,500 damaged RGB PNGs, all 768 × 768.
- 300 cases per family: 300 zero controls and 1,200 nonzero cases.
- Output path: `images/damaged/<painting_id>/<mask_type>.png`.

### Q2. How was damage applied?

- Where mask = 255, set output RGB to `(255, 255, 255)`.
- Where mask = 0, preserve the clean-image pixel exactly.
- No new random sampling occurs in N04; N03 already fixed mask geometry.
- White fill is a controlled baseline, not a model of real exposed material or
  a conservation recommendation.

### Q3. Why can changed pixels be fewer than mask pixels?

- Some clean pixels inside a mask were already pure white.
- Formula: `changed = mask pixels - pre-existing white masked pixels`.
- Total mask pixels: 37,996,554.
- Pre-existing white masked pixels: 13,185.
- Expected and observed changed pixels: 37,983,369 in both cases.
- The difference is expected and is not a failed corruption.

### Q4. What does the zero control establish?

- Each zero-control mask is empty.
- All 300 zero-control outputs are byte-identical copies of their clean images.
- This validates the identity baseline and case accounting.
- It does not test model hallucination: N04 runs no model, and later restoration
  notebooks bypass inference for zero-control identity candidates.

### Q5. How was lineage preserved?

- Every case retains painting, processed-image, mask, and case identifiers.
- Clean, mask, and damaged-image paths and SHA-256 values are recorded.
- N02 and N03 schemas, manifests, checksums, and foreign keys are validated.
- Case IDs, damaged-image IDs, and output paths are unique.
- N04 has no random generator or seed: outputs are determined by the clean
  image, mask, constant-fill configuration, and implementation.
- Five p085 smoke cases passed in-memory replay; all 1,500 persisted cases passed
  independent reload/audit; 250 pilot-overlap outputs remained byte-identical.
- This does not prove universal byte identity across unrecorded encoders or
  environments and does not establish physical realism.

### Q6. What validation evidence passed?

- 1,500 case rows, 1,500 damaged PNGs, and 1,500 audit rows.
- All 1,500 per-case audits passed.
- 60/60 consolidated validation checks passed.
- 24/24 completion requirements passed.
- With the four post-gate requirements, the final handoff passed 28/28.
- Zero failed, missing, orphaned, malformed, or checksum-invalid outputs.
- Zero outside-mask changes and zero inside-mask fill failures.
- Expected and observed changed-pixel totals matched exactly.
- All 250 outputs shared with the 50-painting pilot remained byte-identical.
- One validated 20-panel example figure covers all five families.
- Generation runtime: approximately 557.9 seconds (9.3 minutes), specific to
  the recorded machine and environment.

### Q7. What is the claim and what are the limitations?

**Strongest defensible claim**

- For all 1,500 canonical cases, N04 applied the correct N03 mask to the correct
  N02 image using the versioned white-fill rule, with every pixel rule,
  identifier, checksum, output, and count passing validation.

**Limitations**

- Synthetic white-filled inputs are not historically verified damage.
- White fill is not a physical model of loss, ground, canvas, dirt, fading, or
  conservation treatment and may create artificial high-contrast boundaries.
- Binary corruption excludes blur, fading, discolouration, stains, dirt, dust,
  partial transparency, and other non-binary degradation.
- The cases are not conditioned on subject matter, brushwork, pigment chemistry,
  material layers, or physical damage mechanisms.
- N04 inherits the N01 sampling, N02 digitization/colour, and N03 synthetic-mask
  limitations.
- One example figure is quality-assurance evidence, not exhaustive visual proof.
- Runtime is machine- and environment-specific.

### N04 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Replace pixels selected by each binary mask with constant white; preserve every unmasked pixel; copy zero controls byte-for-byte; audit all outputs. |
| Population | 300 paintings × five mask families = 1,500 cases, including 300 controls and 1,200 nonzero cases. |
| Strongest defensible claim | Synthetic corruption was applied exactly and reproducibly according to the declared N04 contract. |
| Limitation | Correct application does not make white-filled binary corruption a realistic model of physical or historical painting damage. |

---

## 05 — Damage-Size Sensitivity Dataset Generation

### Repository evidence

- Notebook: `notebooks/05_damage_size_sensitivity_dataset_generation.ipynb`
- Configuration: `config/experiments/damage_size_sensitivity.yaml`
- Outputs: `outputs/05_damage_size_sensitivity_dataset_generation/`

### Q1. What population was used?

- 35 pinned paintings: seven per visual category.
- One pilot anchor plus six metadata-complete additions per category.
- Selected to span N02 content-area fractions.
- Only the canonical `loss_large` family was scaled.
- Focused matched cohort, not the complete 300-painting population.

### Q2. What size levels were generated?

- Targets: 2%, 4%, 6%, 8%, 10%, 15%, and 20% of N02 content support.
- 35 paintings × seven levels = 245 cases.
- Outputs: 245 masks and 245 white-filled damaged images.
- Percentages exclude technical padding.

### Q3. How were masks scaled?

- Start from each painting's N03 `loss_large` mask.
- Scale isotropically around its centroid with nearest-neighbour sampling.
- Enforce strict nesting: each larger level retains all earlier pixels.
- Apply deterministic radial correction to reach the rounded target.
- Global seed: 20260505; all 245 case seeds are unique.
- Area tolerance: ≤0.01 percentage points; observed maximum ≈0.000175.
- The levels are nested versions of one shape, not independent placements.

### Q4. What geometry rules applied?

- Stay within N02 content support and avoid technical padding/boundary contact.
- Preserve connected-component count.
- Centroid shift ≤2 pixels.
- Bounding-box aspect-ratio drift ≤15%.
- Compactness drift ≤35%.
- Observed: zero removed earlier-level pixels, zero boundary contacts, zero
  component-count changes, and maximum centroid shift ≈1.96 pixels.
- Passing these rules does not establish physical realism.

### Q5. How were damaged images made?

- Masks: 768 × 768 grayscale PNG, values 0/255.
- Damaged outputs: 768 × 768 RGB PNG.
- Masked pixels become white `(255,255,255)`.
- Unmasked pixels remain unchanged.
- Zero outside-mask changes and zero inside-mask fill failures.

### Q6. What validation evidence passed?

- 245 cases, masks, damaged images, and independent audit rows.
- 96/96 validation checks passed.
- 27/27 completion requirements passed.
- Zero failed, missing, orphaned, duplicate, or checksum-invalid cases.
- Target and realized pixel totals both equal 10,108,296.
- One progression figure covers three paintings across all seven levels.
- Generation runtime ≈80 seconds on the recorded machine.

### Q7. What is the claim and what are the limitations?

**Strongest defensible claim**

- N05 produced a validated, deterministic, strictly nested seven-level
  `loss_large` sensitivity dataset for the pinned 35-painting cohort.

**Limitations**

- Covers 35 paintings, not all 300.
- Covers only `loss_large`, not every damage family.
- Levels are nested, not independent mask placements.
- White fill is synthetic, not a physical model of paint loss.
- Input generation does not itself measure restoration quality or thresholds.
- Inherits N01–N03 sampling, digitization, colour, and synthetic-mask limits.
- Runtime is machine- and environment-specific.

### N05 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Scale each selected `loss_large` mask into seven nested content-relative sizes and create corresponding white-filled inputs. |
| Population | 35 paintings × seven damage sizes = 245 cases. |
| Strongest defensible claim | The focused dataset satisfies its area, nesting, geometry, morphology, integrity, and reproducibility contracts. |
| Limitation | It is not a full-300, all-family, independent-placement, or physically realistic damage experiment. |

---

## 06 — Mask Robustness Dataset Generation

### Repository evidence

- Notebook: `notebooks/06_mask_robustness_dataset_generation.ipynb`
- Configuration: `config/experiments/mask_robustness.yaml`
- Case registry: `outputs/06_mask_robustness_dataset_generation/data/cases.csv`
- Generation audit:
  `outputs/06_mask_robustness_dataset_generation/metrics/generation_audit.csv`
- Validation checks:
  `outputs/06_mask_robustness_dataset_generation/validation/checks.csv`
- Run manifest:
  `outputs/06_mask_robustness_dataset_generation/manifests/run_manifest.json`

### Q1. What population and experimental structure does N06 use?

- 35 paintings inherited from N05: seven per visual category.
- Three families: `scratch_thin`, `loss_small`, and `loss_large`.
- Five masks per painting–family group.
- 105 robustness groups and 525 cases in total.
- Focused balanced cohort, not all 300 paintings or a population-representative
  sample.

### Q2. What stays fixed, and what changes within a group?

- Fixed: painting, mask family, target percentage, broad family morphology,
  content geometry, and fill policy.
- Varied: seed, location, exact shape, component arrangement, and boundary
  relationship.
- Content-relative targets: 2% for `scratch_thin`, 4.5% for `loss_small`, and
  12.5% for `loss_large`.
- Five variants represent different placements/geometries at approximately the
  same area, not five damage sizes.

### Q3. How are variants generated reproducibly?

- Global seed: 20260606, with deterministic painting, group, variant, and
  generation seeds.
- Up to 30 generation attempts are allowed per variant.
- Generated masks are scaled with nearest-neighbour sampling and corrected
  deterministically to the rounded target-pixel count.
- Damage is restricted to the N02 content support; technical padding is
  excluded.
- Masked pixels use constant white `(255,255,255)` and unmasked pixels are
  preserved.
- These are input-mask seeds, not Stable Diffusion uncertainty seeds.

### Q4. How does N06 establish that variants are distinct?

- Five unique mask-pixel hashes are required per group.
- Pairwise IoU must remain below 0.99.
- Centroid span must be at least 2% of the content-region diagonal.
- At least two morphology signatures and two component-arrangement signatures
  are required.
- Broad family-morphology rules must pass.
- Observed maximum pairwise IoU: approximately 0.7003.
- Observed minimum centroid span: approximately 0.0841.
- Observed minimum morphology and component-signature counts: five.

**Simple definitions**

- IoU measures overlap between two masks; 1.0 means identical overlap.
- A centroid is the approximate centre of a mask.
- A morphology signature summarizes shape, compactness, and bounding-box
  properties.
- A component-arrangement signature summarizes how separate mask regions are
  distributed.

### Q5. What exactly did N06 produce and validate?

- 525 binary mask PNGs and 525 corresponding damaged RGB PNGs.
- 525 case records and 525 generation-audit rows.
- 105 robustness groups and one representative comparison figure.
- 1,056 total output files.
- 102/102 consolidated validation checks passed.
- 21/21 completion requirements passed.
- Zero failed cases or groups and zero missing, duplicate, stale, or orphaned
  outputs.
- Zero changes outside masks and zero inside-mask white-fill failures.
- Target and realized totals both equal 14,773,680 pixels.
- These are controlled experimental inputs, not restoration results.

### Q6. What does reproducibility mean here?

- The same configuration and seed hierarchy reproduce the same identities,
  masks, damaged pixels, and hashes in the recorded environment.
- A non-persisting smoke test verified deterministic replay without altering the
  saved collection.
- Persisted masks and damaged images were reloaded and checked against their
  metadata and checksums.
- This does not guarantee byte-identical output under every future library,
  encoder, operating system, or platform version.

### Q7. What is the claim and what are the limitations?

**Strongest defensible claim**

- N06 produced a complete, deterministic, area-accurate, and validated set of
  525 controlled mask-realization cases.
- Within each group, family and target area are fixed while location and exact
  geometry vary sufficiently for later robustness analysis.

**Limitations**

- N06 does not establish that any restoration model is robust or unreliable.
- Metric dispersion, confidence intervals, and ranking stability belong to
  N24, not N06.
- The 35-painting cohort does not automatically generalize to all 300 paintings.
- Only three binary families at one fixed area each are covered.
- Mask family and target size are paired, so their effects cannot be separated
  using N06 alone.
- Synthetic masks and white fill do not represent the distribution or physical
  appearance of real historical damage.
- Geometric distinctness does not establish conservation realism.

### N06 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Deterministically generate five spatially distinct masks at a controlled area for each painting–family group and create corresponding white-filled inputs. |
| Population | 35 balanced paintings × three families × five variants = 525 cases in 105 groups. |
| Strongest defensible claim | The controlled mask-variation dataset was generated completely and passed every declared area, integrity, distinctness, morphology, and reproducibility gate. |
| Limitation | N06 creates synthetic robustness inputs; it does not itself measure model robustness, ranking stability, historical realism, or conservation validity. |

---

## 07 — Synthetic Degradation Dataset Generation

### Repository evidence

- Notebook: `notebooks/07_synthetic_degradation_dataset_generation.ipynb`
- Configuration: `config/experiments/synthetic_degradation.yaml`
- Case registry: `outputs/07_synthetic_degradation_dataset_generation/data/cases.csv`
- Generation audit:
  `outputs/07_synthetic_degradation_dataset_generation/metrics/generation_audit.csv`
- Degradation protocol:
  `outputs/07_synthetic_degradation_dataset_generation/reports/degradation_protocol.md`
- Validation checks:
  `outputs/07_synthetic_degradation_dataset_generation/validation/checks.csv`
- Run manifest:
  `outputs/07_synthetic_degradation_dataset_generation/manifests/run_manifest.json`

### Q1. What population and experimental design does N07 use?

- 35 paintings inherited from N05–N06: seven per visual category.
- 30 single-degradation conditions plus three combined conditions per painting.
- 35 × 33 = 1,155 cases.
- Focused balanced cohort, not all 300 paintings or a population-representative
  deterioration sample.

### Q2. Which degradation conditions were generated?

- Ten single families: Gaussian blur, motion blur, local defocus, water stain,
  pigment bleeding, fading, discolouration, local darkening, dirt/dust, and
  partial transparency.
- Every single family has mild, moderate, and severe settings.
- 35 × ten families × three levels = 1,050 single cases.
- Three ordered moderate combinations: fading → discolouration, water stain →
  dirt/dust, and Gaussian blur → fading.
- 35 × three combinations = 105 combined cases.
- Severity labels are configured ordinal settings, not calibrated conservation
  grades.

### Q3. How do effect-support maps differ from N03 masks?

- N03 masks are binary missing-region masks with values 0 or 255.
- N07 maps are grayscale operator-influence records.
- Zero means no influence; values 1–255 represent increasing configured
  influence.
- Support threshold: 1; active-influence threshold for summaries: 13.
- Supports remain inside N02 content geometry and exclude technical padding.
- Combined supports use the pixelwise maximum of their component maps.
- They are not missing-region masks, physical damage segmentations, or expert
  annotations.

### Q4. How are cases generated reproducibly?

- Global seed: 20260707.
- Each case records deterministic case, support-map, and component-operator
  seeds.
- Parameters are fixed by family and severity.
- Combined operators are applied in a fixed order; reversing that order defines
  a different transformation.
- Clean references are never overwritten.
- Every case produces one 768 × 768 grayscale support PNG and one 768 × 768 RGB
  degraded PNG.
- A non-persisting 13-case `p039` smoke set was generated twice for deterministic
  replay.
- Reproducibility is conditional on the recorded inputs, configuration, helper,
  seed scheme, and environment.

### Q5. Do all 1,155 cases become inpainting tasks?

- No. N07 generates the complete degradation collection; N08 decides model
  eligibility and region policy.
- Four localized families are later approved for supplementary inpainting
  diagnostics: water stain, dirt/dust, partial transparency, and
  water-stain-plus-dirt.
- These account for 350 eligible cases.
- The remaining 805 cases remain valid degradation evidence but are not treated
  as missing-region inpainting tasks.
- N25 later analyses the complete 1,155-case degradation design.

### Q6. What validation evidence passed?

- 1,155 case rows, support PNGs, degraded PNGs, and audit rows.
- 66/66 consolidated checks passed.
- 20/20 completion requirements passed.
- 2,317 total output files.
- Zero failed cases and zero missing, stale, or orphaned files.
- Zero changed pixels outside recorded support.
- All clean references remained unchanged.
- All 330 shared pilot-generated PNGs remained byte-identical.
- Generation took approximately 1,056 seconds and reload validation about 114
  seconds on the recorded machine.

### Q7. What is the claim and what are the limitations?

**Strongest defensible claim**

- N07 produced a complete, deterministic, traceable, and validated procedural-
  degradation dataset containing ten single families at three configured levels
  and three ordered combinations for a balanced 35-painting cohort.
- Every saved case satisfied its declared support, integrity, checksum, and
  reproducibility rules.

**Limitations**

- RGB operators do not simulate pigment chemistry, varnish, moisture, substrate
  mechanics, aging, or actual conservation processes.
- Severity labels are not calibrated condition grades.
- Support size does not equal physical damage severity.
- Only three selected combinations are covered.
- Pixel, colour, gradient, and Laplacian proxies do not establish historical
  correctness or restoration trustworthiness.
- N07 does not evaluate restoration models or conservation readiness.

### N07 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Apply deterministic RGB-domain degradation operators within recorded content support and save their influence maps. |
| Population | 35 balanced paintings × 33 conditions = 1,155 cases. |
| Strongest defensible claim | The complete procedural-degradation dataset passed every declared generation, support, integrity, checksum, and reproducibility requirement. |
| Limitation | These are synthetic evaluation proxies, not calibrated or historically verified conservation damage. |

---

## 08 — Experiment Contracts and Region Policy

### Repository evidence

- Notebook: `notebooks/08_experiment_contracts_and_region_policy.ipynb`
- Configuration: `config/experiments/evaluation_contract.yaml`
- Case registry:
  `outputs/08_experiment_contracts_and_region_policy/data/case_registry.csv`
- Model eligibility:
  `outputs/08_experiment_contracts_and_region_policy/data/model_eligibility.csv`
- Region policy:
  `outputs/08_experiment_contracts_and_region_policy/data/region_policy.csv`
- Schema registry:
  `outputs/08_experiment_contracts_and_region_policy/data/schema_registry.json`
- Methodology report:
  `outputs/08_experiment_contracts_and_region_policy/reports/evaluation_contract.md`
- Validation checks:
  `outputs/08_experiment_contracts_and_region_policy/validation/checks.csv`
- Run manifest:
  `outputs/08_experiment_contracts_and_region_policy/manifests/run_manifest.json`

### Q1. What is N08's purpose?

- Combine N04–N07 into one normalized case registry.
- Record whether each model–case combination is methodologically valid.
- Define where each metric family may be calculated.
- Register stable schemas and downstream contracts.
- N08 does not run restoration models or calculate restoration quality.

### Q2. What population enters the case registry?

- N04 canonical cases: 1,500.
- N05 damage-size cases: 245.
- N06 mask-robustness cases: 525.
- N07 synthetic-degradation cases: 1,155.
- Total: 3,425 unique cases.
- Composition: 2,270 binary missing-region cases, 1,155 synthetic-degradation
  cases, and 300 canonical zero controls.
- These are experimental cases derived from 300 paintings, not 3,425 different
  paintings.

### Q3. Which models are registered, and what does eligibility mean?

- Models: OpenCV Telea, LaMa, Stable Diffusion Inpainting, SDXL Inpainting, and
  HINT Places2.
- 3,425 decisions per model and 17,125 decisions overall.
- Per model: 2,620 methodologically eligible and 805 ineligible cases.
- Overall: 13,100 eligible and 4,025 ineligible decisions.
- Eligibility states that a case fits the declared method; it does not establish
  installed weights, runtime feasibility, successful execution, or quality.
- SDXL remains a bounded feasibility evaluation despite registry-wide
  methodological decisions.

### Q4. How is eligibility decided?

- All 2,270 binary missing-region cases are eligible for each model.
- The 300 zero controls use an identity/no-operation objective.
- Only water stain, dirt/dust, partial transparency, and
  water-stain-plus-dirt are eligible synthetic families.
- These provide 350 eligible synthetic cases per model.
- Blur/defocus needs a degradation-specific correction objective.
- Fading, discolouration, and darkening are tonal/colour problems.
- Pigment bleeding is a transport effect rather than missing content.
- Inpainting is therefore not treated as appropriate for every degradation.

### Q5. Which spatial regions are defined?

- Global: full image and painting-content region.
- Target: masked pixels, mask bounding-box crop, and degradation support.
- Boundary: inner band, outer band, and combined boundary ring.
- Preservation: outside-mask content and outside-boundary ring.
- Patch: sliding patch window.
- Eleven region identities in total.
- Main settings: binary threshold 128, bounding-box margin 8 pixels, boundary
  width 3 pixels, outside-ring inner offset 3 pixels and outer width 8 pixels,
  224 × 224 patches, stride 112, and minimum 50% painting content.
- These dimensions are declared analysis choices, not physical painting
  properties.

### Q6. Why can every metric not use every region?

- 13 metric families × 11 regions = 143 explicit policy rows.
- 86 combinations are compatible and 57 are prohibited.
- Pixel, colour, and spatial diagnostics can use irregular pixel regions.
- SSIM, LPIPS, CLIP, and DINOv2 require image-like rectangular crops.
- Seam metrics belong on boundary and spillover rings.
- Outside-mask regions diagnose unintended changes away from the target.
- Sparse masked-pixel SSIM is prohibited because irregular flattened pixels are
  not a valid image window.
- Compatibility provides a defensible calculation, not proof of historical or
  conservation validity.

### Q7. What outputs and validation evidence support N08?

- A 3,425-row case registry.
- A 17,125-row model-eligibility table.
- A 143-row metric–region policy.
- Five registered schemas: case registry, model eligibility, region policy,
  artifact manifest, and validation checks.
- Region construction was checked across all 3,425 cases, producing 31,980
  applicable case–region records.
- 101/101 consolidated checks passed.
- 20/20 completion requirements passed.
- Nine canonical output files.
- Zero missing cases, orphan decisions, or unclassified degradation families.

### Q8. What is the claim and what are the limitations?

**Strongest defensible claim**

- N08 produced a complete and validated governance layer connecting all 3,425
  cases to explicit model eligibility, spatial regions, metric compatibility,
  and versioned schemas.
- Invalid routes are explicitly rejected rather than silently included.

**Limitations**

- Eligibility does not establish availability, successful execution, or quality.
- Region dimensions and thresholds are analytical choices.
- Algorithmic regions are not expert conservation annotations.
- Metric compatibility does not establish historical authenticity.
- No universal trust score is defined.
- Visual plausibility is not conservation suitability, and human interpretation
  remains necessary.

### N08 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Normalize cases, record model eligibility, and predeclare valid metric–region combinations. |
| Population | 3,425 cases, five models, 17,125 eligibility decisions, and 143 region-policy rows. |
| Strongest defensible claim | The downstream experiment-routing and spatial-evaluation contract is complete, explicit, and validated. |
| Limitation | A valid contract prevents invalid comparisons but does not prove model quality, historical correctness, or conservation readiness. |

---

## 09 — OpenCV Telea Restoration

### Repository evidence

- Notebook: `notebooks/09_opencv_telea_restoration.ipynb`
- Configuration: `config/experiments/opencv_telea.yaml`
- Implementation: `src/restoration_eval/restoration_opencv.py`
- Restoration registry:
  `outputs/09_opencv_telea_restoration/data/restorations.csv`
- Runtime summary:
  `outputs/09_opencv_telea_restoration/metrics/runtime_summary.csv`
- Validation checks:
  `outputs/09_opencv_telea_restoration/validation/checks.csv`
- Run manifest:
  `outputs/09_opencv_telea_restoration/manifests/run_manifest.json`

### Q1. What method does N09 use, and why is it included?

- OpenCV `cv2.INPAINT_TELEA`, used as a classical deterministic baseline.
- CPU execution with 8-bit image values.
- Fixed inpainting radius of 3 pixels for every case.
- Zero retries and no per-case tuning.
- Telea propagates nearby image information inward from the mask boundary.
- It uses no training data, learned weights, prompt, or semantic understanding.
- Local interpolation does not establish historically correct reconstruction.

### Q2. What population was restored?

- 1,500 canonical missing-region cases.
- 245 damage-size cases.
- 525 mask-robustness cases.
- 350 eligible synthetic-degradation cases.
- Total: 2,620 cases representing 300 unique paintings.
- 300 cases are zero controls; 2,320 execute actual inpainting.
- These are experimental cases, not 2,620 independent paintings.

### Q3. How are masks handled?

- Binary missing-region masks use pixels greater than or equal to 128.
- Eligible synthetic effect-support maps use pixels greater than or equal to 13,
  matching N07's active threshold.
- Grayscale source maps are converted into binary restoration masks.
- Empty masks use an identity/no-operation path.
- Telea consumes the damaged/degraded input and mask; it does not use the clean
  reference to synthesize its output.
- Synthetic-degradation results remain supplementary removal diagnostics rather
  than physical conservation treatments.

### Q4. How are zero controls and spatial invariance handled?

- All 300 zero controls bypass Telea and remain pixel-identical to their inputs.
- Every one of the 2,320 nonempty-mask cases changed at least one masked pixel.
- Zero pixels changed outside the mask across all 2,620 cases.
- Every persisted output checksum matched its recorded checksum.
- Repeating the configured smoke case produced identical pixels and checksums.
- A change inside the mask proves execution, not correctness of the replacement.

### Q5. What outputs and validation evidence were produced?

- 2,620 normalized restoration records and restored RGB PNGs.
- Five runtime-summary rows.
- Eight representative cases in one comparison figure.
- Five artifact-manifest records.
- 2,626 canonical output files.
- 72/72 consolidated checks passed.
- 15/15 completion requirements passed.
- Zero failed, missing, empty, unexpected, or orphaned restorations.
- Zero temporary work files remained.
- Of 410 shared pilot restorations, 409 were byte-identical; the single change
  inherited N06's corrected `p039` mask rather than a changed Telea method.

### Q6. How fast was Telea?

- Summed case-execution time: approximately 1,446.7 seconds, or 24.1 minutes.
- Mean per case: approximately 0.552 seconds.
- Median: approximately 0.519 seconds.
- 95th percentile: approximately 0.925 seconds.
- Maximum: approximately 1.429 seconds.
- Validation, checksums, loading, saving, and figure rendering add further
  notebook wall time.
- Timings describe the recorded CPU, storage, and software environment rather
  than a universal benchmark.

### Q7. What is the claim and what are the limitations?

**Strongest defensible claim**

- N09 completed the entire approved 2,620-case Telea worklist using one fixed,
  deterministic configuration.
- Every output satisfied the declared mask dispatch, file-integrity,
  zero-control identity, and outside-mask invariance contracts.
- The outputs provide a reproducible classical baseline for later metrics.

**Limitations**

- Telea is local interpolation without learned semantic understanding.
- Radius three was fixed without per-case tuning.
- Technical completion does not establish visual quality or historical
  correctness.
- N09 itself calculates no restoration-quality metrics.
- Complex or large missing regions may require information unavailable from
  nearby pixels.
- Synthetic-degradation results remain supplementary diagnostics.
- Runtime is machine-specific.

### N09 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Deterministic OpenCV Telea interpolation with radius three and policy-defined binary masks. |
| Population | 2,620 eligible cases: 300 identity controls and 2,320 actual inpainting executions. |
| Strongest defensible claim | The complete approved Telea baseline was executed and passed every declared technical and spatial-integrity check. |
| Limitation | Successful local interpolation does not prove plausible, historically correct, or conservation-ready restoration. |

---

## 10 — LaMa Restoration

### Repository evidence

- Notebook: `notebooks/10_lama_restoration.ipynb`
- Configuration: `config/experiments/lama.yaml`
- Implementation: `src/restoration_eval/restoration_lama.py`
- Restoration registry: `outputs/10_lama_restoration/data/restorations.csv`
- Runtime summary: `outputs/10_lama_restoration/metrics/runtime_summary.csv`
- Validation checks: `outputs/10_lama_restoration/validation/checks.csv`
- Run manifest: `outputs/10_lama_restoration/manifests/run_manifest.json`

### Q1. What method does N10 use, and why is it included?

- LaMa through IOPaint 1.6.0, used as a learned inpainting baseline.
- CUDA execution with float32 precision and a fixed model configuration.
- No text prompts, seed sweep, or per-painting tuning.
- Unlike Telea's local interpolation, LaMa uses learned image context to fill a
  missing region.
- Learned completion still does not establish historical truth.

### Q2. What population was processed?

- 1,500 canonical cases.
- 245 damage-size cases.
- 525 mask-robustness cases.
- 350 eligible synthetic-degradation cases.
- Total: 2,620 cases representing 300 paintings.
- 300 zero controls use identity/no-operation processing.
- 2,320 cases require actual LaMa inference.
- One LaMa candidate is produced per eligible case.

### Q3. How are masks and final outputs handled?

- Masks are converted to binary support before inference.
- LaMa receives the damaged/degraded image and approved mask.
- Predicted pixels are retained only inside the mask.
- Pixels outside the mask are copied exactly from the input image.
- Outputs are 768 × 768 RGB PNG files.
- The clean reference is not supplied to LaMa to construct the restoration.
- Exact outside-mask preservation is enforced by the adapter, not proved as an
  inherent property of raw LaMa output.

### Q4. What do zero controls and the repeatability test establish?

- All 300 zero controls remained exact pixel identities.
- The selected smoke case was inferred twice.
- Its CUDA outputs were not byte-identical but stayed within the approved
  tolerance.
- Maximum channel difference: 1.
- Mean absolute difference: approximately 0.0025.
- Different-pixel fraction: approximately 0.0070.
- The defensible description is tightly bounded numerical repeatability, not
  perfect bitwise determinism.

### Q5. What validation evidence was produced?

- 2,620/2,620 cases completed with no failures.
- 300/300 zero controls preserved exact identity.
- Every nonempty-mask case changed at least one masked pixel.
- Zero changed pixels were found outside approved masks.
- Every output was readable, RGB, 768 × 768, and checksum-matched.
- 80/80 consolidated validation checks passed.
- 16/16 completion requirements passed.

### Q6. How long did N10 take?

- Full notebook execution: approximately 4,594.2 seconds, or 76.6 minutes.
- Allocated restoration runtime: approximately 3,570.5 seconds, or 59.5
  minutes.
- Mean allocated runtime: approximately 1.36 seconds per case.
- IOPaint exposes batch wall-clock time, which is allocated across cases rather
  than independently timing every restoration.
- Runtime is specific to the recorded hardware and software environment.

### Q7. What is the claim and what are the limitations?

**Strongest defensible claim**

- N10 produced a complete, validated, and provenance-traced LaMa candidate set
  for all 2,620 eligible cases.
- Its adapter enforced exact outside-mask preservation, and the repeated CUDA
  smoke test showed tightly bounded numerical variation.

**Limitations**

- LaMa generates plausible content, not verified historical truth.
- N10 does not prove that LaMa is the best-performing method.
- Quality metrics and cross-model comparisons occur later in the pipeline.
- Only one fixed LaMa configuration and one candidate per case were evaluated.
- Learned completion can introduce plausible but unsupported details.
- Synthetic-degradation results remain supplementary diagnostics.
- Runtime is machine-specific.

### N10 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Fixed LaMa inference through IOPaint, followed by exact masked compositing. |
| Population | 2,620 eligible cases: 300 identity controls and 2,320 actual inferences. |
| Strongest defensible claim | The complete LaMa baseline was generated and passed every declared technical, provenance, and spatial-integrity check. |
| Limitation | A learned, visually plausible fill is not proof of the painting's original missing content or historical correctness. |

---

## 11 — Stable Diffusion Restoration

### Repository evidence

- Notebook: `notebooks/11_stable_diffusion_restoration.ipynb`
- Base configuration: `config/experiments/stable_diffusion.yaml`
- Scratch supplement:
  `config/experiments/stable_diffusion_scratch_prompt_ablation.yaml`
- Candidate registry: `outputs/11_stable_diffusion_restoration/data/candidates.csv`
- Executed prompt policy:
  `outputs/11_stable_diffusion_restoration/reports/prompt_policy.md`
- Runtime summary:
  `outputs/11_stable_diffusion_restoration/metrics/runtime_summary.csv`
- Validation checks:
  `outputs/11_stable_diffusion_restoration/validation/checks.csv`
- Run manifest:
  `outputs/11_stable_diffusion_restoration/manifests/run_manifest.json`

### Q1. Which model and fixed generation settings were used?

- Stable Diffusion 1.5 Inpainting through Diffusers.
- Pinned model revision: `8a4288a76071f7280aedbdb3253bdb9e9d5d84bb`.
- DDIM scheduler, 30 inference steps, guidance scale 7.5, and strength 1.0.
- CUDA execution with float16 precision.
- Primary seed 2026; repeated seeds 2026, 2027, 2028, and 2029.
- No per-painting parameter tuning.
- These are fixed experimental settings, not proven optimal settings.

### Q2. How were the 768 × 768 images processed by the model?

- Each normalized image was resized to 512 × 512 for inference.
- Masks were resized using nearest-neighbour interpolation.
- Generated results were resized back to 768 × 768.
- Generated pixels were retained only inside the original approved mask.
- Original input pixels were copied back outside the mask.
- Thin scratches can shrink or fragment during 512-pixel and latent-space
  processing.

### Q3. What was the complete candidate population?

- 2,620 primary candidates: 300 identity controls and 2,320 model inferences.
- 4,460 prompt-context candidates: 3,260 metadata-context candidates and 1,200
  scratch-aware candidates.
- 1,440 uncertainty-extension candidates.
- Total: 8,520 candidates and restored images.
- Actual Stable Diffusion executions: 8,220.
- All candidates derive from 300 paintings, not 8,520 independent paintings.

### Q4. What prompt variants were tested?

- `p00_generic`: fixed primary restoration prompt.
- `p01_category`: adds visual category.
- `p02_artist`: adds artist.
- `p03_artist_category`: adds artist and category.
- `p04_full_context`: adds title, artist, and category.
- `p05_scratch_aware`: targets continuity across thin scratches.
- The four metadata variants were tested on 815 cases, balanced at 163 per
  visual category.
- Cases were selected deterministically without restoration-quality metrics.
- More context does not automatically make a prompt historically accurate.

### Q5. How did the repeated-seed and scratch-prompt designs work?

- The base uncertainty design contains 240 cases and four seeds.
- It adds 720 candidates beyond the primary seed outputs.
- The scratch experiment covers all 300 paintings, two prompt arms, and four
  identical seeds per painting.
- This gives 1,200 painting–seed pairs and 2,400 matched outcomes.
- Painting is the independent unit; seeds are repeated observations within it.
- The 1,200 seed-level pairs are not 1,200 independent paintings.

### Q6. What did technical validation establish?

- 8,520/8,520 candidates completed with no failures.
- All 300 zero controls remained exact identities.
- Every nonzero candidate changed at least one masked pixel.
- No candidate changed pixels outside its approved mask.
- All 8,520 files matched their recorded checksums.
- Repeating the same seed and settings reproduced the smoke output exactly.
- Changing the seed or prompt changed pixels inside the mask.
- 176/176 scientific checks and 23/23 completion requirements passed.
- A changed output is not necessarily a better restoration.

### Q7. How long did generation take?

- Summed candidate runtime: approximately 71,737.6 seconds, or 19.93 hours.
- Mean: approximately 8.42 seconds per candidate.
- Median: approximately 8.62 seconds.
- 95th percentile: approximately 9.48 seconds.
- Maximum: approximately 11.37 seconds.
- This is environment-specific accumulated evidence, not a universal benchmark
  or necessarily one uninterrupted session.

### Q8. What is the claim and what are the limitations?

**Strongest defensible claim**

- N11 generated the complete predeclared Stable Diffusion candidate population
  with fixed settings, controlled prompts and seeds, metric-independent
  selection, exact outside-mask compositing, and complete provenance.

**Limitations**

- Stable Diffusion produces plausible content, not verified historical truth.
- N11 does not determine the best prompt or candidate; quality analysis occurs
  later.
- Seed variation is empirical disagreement, not calibrated confidence.
- Prompting cannot guarantee correction of thin-mask spatial limitations.
- The model can introduce plausible but unsupported details.
- Synthetic-degradation results remain supplementary diagnostics.
- The safety checker was disabled for this fixed research dataset.
- Runtime and exact reproducibility can vary across environments.

### N11 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Fixed Stable Diffusion 1.5 inpainting with controlled prompts, seeds, and exact masked compositing. |
| Population | 8,520 candidates from 300 paintings, including 8,220 model executions and 300 controls. |
| Strongest defensible claim | The complete planned stochastic candidate design was generated, validated, and recorded without metric-based selection. |
| Limitation | Plausible content, prompt effects, and seed consistency do not establish historical correctness or conservation suitability. |

---

## 12 — SDXL Bounded Partial Evaluation

### Repository evidence

- Notebook: `notebooks/12_sdxl_feasibility_or_restoration.ipynb`
- Configuration: `config/experiments/sdxl.yaml`
- Candidate registry:
  `outputs/12_sdxl_feasibility_or_restoration/data/candidates.csv`
- Runtime summary:
  `outputs/12_sdxl_feasibility_or_restoration/metrics/runtime_summary.csv`
- Executed report:
  `outputs/12_sdxl_feasibility_or_restoration/reports/partial_evaluation_report.md`
- Validation checks:
  `outputs/12_sdxl_feasibility_or_restoration/validation/checks.csv`
- Run manifest:
  `outputs/12_sdxl_feasibility_or_restoration/manifests/run_manifest.json`

### Q1. Which model and fixed settings were used?

- SDXL Inpainting through `StableDiffusionXLInpaintPipeline`.
- Model: `diffusers/stable-diffusion-xl-1.0-inpainting-0.1`.
- Pinned revision: `115134f363124c53c7d878647567d04daf26e41e`.
- DDIM scheduler, 30 steps, guidance 7.5, and strength 1.0.
- Native 768 × 768 inference and output.
- CUDA float16, generic prompt, and seed 2026.
- Model CPU offload and VAE slicing/tiling supported the 6 GB GPU.
- These settings are fixed, not proven optimal.

### Q2. What population was scheduled?

- The broader eligible frame contained 2,620 cases, including 300 controls.
- N12 predeclared 35 nonzero cases across 30 paintings.
- Exactly seven scheduled cases came from each visual category.
- The scope contained 20 canonical and 15 eligible synthetic cases.
- Five retained pilot paintings contributed two nested cases each; 25 other
  paintings contributed one case each.
- Selection was frozen before execution and used no quality metrics.
- The 35 cases are neither 35 independent paintings nor a representative
  population sample.

### Q3. How were comparisons, masks, and outputs controlled?

- Every selected case already had matching Telea, LaMa, and primary Stable
  Diffusion results.
- Canonical mask threshold: 128.
- Synthetic-effect threshold: 13.
- Generated pixels were retained only inside the active mask.
- Source pixels were copied exactly outside the mask.
- Technical validity required a readable 768 × 768 RGB PNG, nonempty mask,
  matching checksum, and zero outside-mask changes.
- Exact boundary preservation does not prove restoration quality.

### Q4. How was execution bounded, and what happened?

- Global budget: 25,200 seconds, or seven hours.
- Per-case watchdog: 900 seconds.
- No automatic retries or CPU fallback.
- Each resolved case was checkpointed immediately.
- Results: 24 completed, one timed out, and ten skipped after the timeout guard.
- The timed-out case was `canonical__p211__scratch_thin`.
- The per-case watchdog, not the global budget, stopped further execution.
- “Run completed” means all scheduled rows received explicit terminal states,
  not that all 35 images were generated.

### Q5. What usable SDXL population remained?

- 24 technically valid outputs across 19 paintings.
- 13 canonical and 11 synthetic-degradation cases.
- Completed category counts: 5, 5, 4, 5, and 5.
- Only the 24 completed outputs can enter downstream metrics.
- Timeout and skipped cases remain missing evidence, not poor-quality scores.
- Availability state: `partial_evaluation`.

### Q6. What validation evidence was produced?

- All 35 scheduled rows remained in the candidate registry.
- All 24 completed images passed checksum, RGB, geometry, inside-mask change,
  and exact outside-mask preservation checks.
- 241/241 persisted validation checks passed.
- Five artifact records and 30 canonical files were retained.
- No temporary work files remained.
- Technical validation does not establish visual, historical, or conservation
  correctness.

### Q7. How long did N12 take?

- Completed-candidate runtime: approximately 4,788.5 seconds, or 79.8 minutes.
- Mean completed-case runtime: approximately 199.5 seconds.
- Median: approximately 198.0 seconds.
- 95th percentile: approximately 206.6 seconds.
- Maximum completed-case runtime: approximately 221.4 seconds.
- Full parent-worker runtime: approximately 5,741.1 seconds, or 95.7 minutes.
- The parent runtime includes startup, overhead, and the timed-out attempt.
- Runtime is specific to the recorded hardware and environment.

### Q8. What is the claim and what are the limitations?

**Strongest defensible claim**

- Under a predeclared resource-bounded protocol, N12 produced 24 technically
  valid and traceable SDXL candidates suitable for matched downstream analysis.
- SDXL must remain labelled as a bounded partial evaluation.

**Limitations**

- It is not a full SDXL benchmark.
- Only 24 cases across 19 paintings completed, and the completed subset is not
  perfectly category-balanced.
- Only one prompt and one seed were used; N12 supplies no SDXL uncertainty
  analysis.
- Guardrail omissions cannot be interpreted as restoration failures.
- Some outputs showed substitutions, hallucinated content, seams, or speckling.
- Plausible content is not verified historical reconstruction.
- Formal quality metrics occur in later notebooks.

### N12 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Fixed 768 × 768 SDXL inpainting under strict GPU, timeout, and compositing controls. |
| Population | 35 scheduled cases across 30 paintings; 24 technically valid outputs across 19 paintings. |
| Strongest defensible claim | SDXL was feasible for a bounded subset and produced 24 validated candidates for matched downstream analysis. |
| Limitation | The partial, purposive, and single-seed results cannot support full-population SDXL performance or historical-correctness claims. |

---

## 13 — Classical Metrics

### Repository evidence

- Notebook: `notebooks/13_classical_metrics.ipynb`
- Configuration: `config/evaluation/metrics.yaml`
- Implementation: `src/restoration_eval/metrics_classical.py`
- Metric table: `outputs/13_classical_metrics/metrics/classical_metrics.csv`
- Validation checks: `outputs/13_classical_metrics/validation/checks.csv`
- Run manifest: `outputs/13_classical_metrics/manifests/run_manifest.json`

### Q1. What does N13 calculate?

- It evaluates existing restorations; it does not generate images.
- It compares the clean reference with the damaged input and restored output.
- It calculates MSE, MAE, PSNR, and SSIM.
- It records direction-normalized improvement for every valid metric–region pair.
- The clean reference is the pre-damage experimental image, not verified
  historical ground truth.

### Q2. What do the four metrics mean?

- MSE: average squared pixel error; lower is better.
- MAE: average absolute pixel error; lower is better.
- PSNR: logarithmic pixel-fidelity measure; higher is better.
- SSIM: structural similarity of rectangular image regions; higher is better.
- MSE/MAE improvement equals damaged value minus restored value.
- PSNR/SSIM improvement equals restored value minus damaged value.
- Positive means closer to the clean reference under that metric and region.
- Metric improvement does not prove historical or conservation correctness.

### Q3. Which spatial regions are evaluated?

- Pixel metrics can use the full image, content region, exact mask, mask crop,
  inner and outer boundary bands, combined boundary ring, outside-mask content,
  outside-boundary ring, and synthetic-degradation support.
- Mask-box margin: 8 pixels.
- Boundary width: 3 pixels.
- Outside-ring inner offset: 3 pixels; outer width: 8 pixels.
- SSIM is restricted to the full image, content region, and mask-box crop.
- Sparse masked-pixel SSIM is prohibited.
- Sliding patch analysis is deferred to later notebooks.

### Q4. What population was evaluated?

- 300 paintings and 2,620 unique cases.
- 16,404 technically valid candidates:
  - Telea: 2,620
  - LaMa: 2,620
  - HINT: 2,620
  - Stable Diffusion: 8,520
  - SDXL: 24
- Eleven unresolved SDXL rows were omitted without placeholders: ten skipped and
  one timed out.
- Candidates, prompts, seeds, and cases are nested within 300 paintings; they
  are not independent paintings.

### Q5. How large is the metric evidence table?

- 477,753 metric–region rows.
- MSE: 143,247 rows.
- MAE: 143,247 rows.
- PSNR: 143,247 rows.
- SSIM: 48,012 rows.
- A zero control contributes 11 rows, an ordinary nonzero case 30 rows, and a
  synthetic-degradation case 33 rows.
- Row counts differ because not every region exists or is valid for every case.

### Q6. What do the controls and improvement counts show?

- 1,200 zero-control candidates produced 13,200 metric rows.
- Exact controls have MSE=0, MAE=0, SSIM=1, PSNR=positive infinity, and
  improvement=0.
- Positive infinity is deliberately preserved for exact equality.
- Row-level outcomes: 261,919 improved, 150,036 unchanged, and 65,798 worsened.
- Negative improvement is valid evidence, not a pipeline failure.
- These counts describe metric–region rows, not numbers of restorations.

### Q7. What validation and runtime evidence was recorded?

- All 477,753 rows completed without computation errors.
- 262/262 validation checks passed.
- No unexpected missing values or negative infinity values occurred.
- 85,564 positive-infinity numeric values were intentionally retained.
- Two descriptive figures were generated.
- Full CPU execution took approximately 28,705.2 seconds, or 7 hours 58
  minutes.
- Six canonical files were retained, with no temporary work files remaining.
- This is metric-computation time, not restoration-generation time.

### Q8. What is the claim and what are the limitations?

**Strongest defensible claim**

- N13 produced a complete and validated region-aware classical full-reference
  evidence table for every technically valid upstream candidate.

**Limitations**

- The metrics measure similarity to the experimental clean reference.
- They do not directly establish semantic plausibility or historical truth.
- Pixel metrics can penalize plausible but pixel-different restorations.
- Results depend on the selected spatial region.
- Stable Diffusion prompts and seeds are repeated observations.
- SDXL contributes only 24 completed cases.
- Unequal and nested candidate counts prevent naïve model ranking.
- The figures are descriptive, not inferential evidence.

### N13 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Region-aware MSE, MAE, PSNR, and SSIM comparisons against the experimental clean reference. |
| Population | 477,753 metric rows from 16,404 candidates, 2,620 cases, and 300 paintings across five methods. |
| Strongest defensible claim | All technically valid upstream candidates received complete classical evidence under the declared region policy. |
| Limitation | Reference similarity is not equivalent to perceptual quality, historical accuracy, or conservation suitability. |

---

## 14 — LPIPS Metrics

### Repository evidence

- Notebook: `notebooks/14_lpips_metrics.ipynb`
- Configuration: `config/evaluation/lpips.yaml`
- Implementation: `src/restoration_eval/metrics_lpips.py`
- Metric table: `outputs/14_lpips_metrics/metrics/lpips_metrics.csv`
- Validation checks: `outputs/14_lpips_metrics/validation/checks.csv`
- Run manifest: `outputs/14_lpips_metrics/manifests/run_manifest.json`

### Q1. What does N14 calculate?

- LPIPS: Learned Perceptual Image Patch Similarity using learned visual features.
- It compares clean–damaged and clean–restored image regions.
- Lower LPIPS means greater similarity to the experimental clean reference.
- Improvement equals damaged LPIPS minus restored LPIPS.
- Positive improvement means closer under LPIPS, not proven historical or visual superiority.

### Q2. Which model and preprocessing are fixed?

- LPIPS package 0.1.4, model version 0.1, with the AlexNet backbone.
- RGB crops are resized bicubically while preserving aspect ratio.
- Longest side: 256 pixels; minimum side: 64 pixels.
- Narrow crops receive neutral-value-127 padding when required.
- Inputs are normalized to `[-1, 1]`.
- Deterministic CUDA inference was used on the recorded RTX 3060 Laptop GPU.
- Inputs are not blindly stretched to 256 × 256; padding can affect elongated crops.

### Q3. Which regions are evaluated?

- `content_region`.
- `mask_bbox_crop` with an 8-pixel margin inside the content bounds.
- Full-image evaluation is excluded because unchanged pixels and canvas padding
  could dilute local effects.
- Sparse masked pixels are prohibited because LPIPS needs contiguous image-like
  inputs.
- Empty zero-control masks receive content-region evidence only.

### Q4. What population was evaluated?

- 300 paintings and 2,620 unique cases.
- 16,404 technically valid candidates:
  - Telea: 2,620
  - LaMa: 2,620
  - HINT: 2,620
  - Stable Diffusion: 8,520
  - SDXL: 24
- Eleven unresolved SDXL records were omitted without placeholders.
- 31,608 candidate–region rows:
  - Content region: 16,404
  - Mask-box crop: 15,204
- Candidates, prompts, seeds, and cases are nested within 300 paintings.

### Q5. How were baselines and zero controls handled?

- Damaged LPIPS was calculated once for each unique case–region and reused.
- This produced 4,940 damaged case–region baselines.
- The 1,200 zero-control candidates have content-region evidence only.
- Every control produced damaged LPIPS=0, restored LPIPS=0, and improvement=0.
- Controls validate identity handling and metric arithmetic, not restoration quality.

### Q6. What were the main descriptive outcomes?

- Improved candidate–region rows: 25,118.
- Unchanged zero-control rows: 1,200.
- Worsened candidate–region rows: 5,290.
- Scratch prompting supplied 2,400 matched case–seed–region comparisons.
- Scratch-aware prompting was better in 419/1,200 content-region and 427/1,200
  mask-crop pairs.
- These are descriptive nested rows, not independent paintings or proof that
  scratch-aware prompting is generally better.

### Q7. What validation and runtime evidence was recorded?

- All 31,608 rows completed with zero computation errors.
- 261/261 validation checks passed.
- Three registered artifact checksums passed.
- Full checkpointed execution took approximately 3,341.8 seconds, or 55 minutes
  42 seconds.
- Batch-allocated row runtimes must not be summed as independent wall time.

### Q8. What is the claim and what are the limitations?

**Strongest defensible claim**

- N14 produced complete, validated, region-aware LPIPS evidence for every
  technically valid upstream candidate under one fixed policy.

**Limitations**

- LPIPS is a learned similarity proxy, not a conservation-specific judgment.
- The clean image is experimental pre-damage evidence, not historical truth.
- LPIPS may disagree with pixel, colour, texture, feature, or human assessment.
- Resizing and padding can influence values.
- Candidate counts are unequal and nested; SDXL has only 24 completed candidates.
- Formal grouped comparisons belong to later notebooks.

### N14 defence summary

| Required distinction | Short answer |
|---|---|
| Method | AlexNet LPIPS on clean–damaged and clean–restored content and mask-box crops. |
| Population | 31,608 rows from 16,404 candidates, 2,620 cases, and 300 paintings across five methods. |
| Strongest defensible claim | Every technically valid upstream candidate received validated LPIPS evidence under the declared policy. |
| Limitation | Learned perceptual similarity is not historical accuracy, conservation suitability, or expert judgment. |

---

## 15 — Feature Similarity

### Repository evidence

- Notebook: `notebooks/15_feature_similarity.ipynb`
- Configuration: `config/evaluation/feature_similarity.yaml`
- Implementation: `src/restoration_eval/metrics_feature_similarity.py`
- Metric table: `outputs/15_feature_similarity/metrics/feature_metrics.csv`
- Embedding bundle: `outputs/15_feature_similarity/data/embeddings.npz`
- Embedding index: `outputs/15_feature_similarity/manifests/embeddings.csv`
- Validation checks: `outputs/15_feature_similarity/validation/checks.csv`
- Run manifest: `outputs/15_feature_similarity/manifests/run_manifest.json`

### Q1. What does N15 measure?

- An embedding is a compact numerical description of an image region.
- CLIP ViT-B/32 produces 512-value general visual-semantic embeddings.
- DINOv2 ViT-S/14 produces 384-value learned visual-structure embeddings.
- Cosine similarity compares the direction of two normalized embeddings; values
  nearer 1 are more similar.
- Improvement equals restored-clean similarity minus damaged-clean similarity.
- Positive improvement means closer in that feature space, not historically
  correct or universally better.

### Q2. How were the feature encoders configured?

- Exact model revisions and weight checksums were pinned.
- All embeddings were L2-normalized.
- CLIP used its native 224 × 224 processor.
- DINOv2 used bicubic resize to a 256-pixel shorter side, a 224 × 224 centre
  crop, and its official normalization.
- CUDA extraction used checkpointed and resumable batches.
- Resizing and centre-cropping can suppress evidence near crop edges.

### Q3. Which regions were evaluated?

- `content_region`: actual painting content without canvas padding.
- `mask_bbox_crop`: damage bounding box with an 8-pixel margin.
- Full canvas was excluded because unchanged pixels and padding could dilute the
  restoration effect.
- Sparse mask pixels were excluded because the encoders require an ordered
  image-like input.
- Empty zero-control masks therefore have only a content-region result.

### Q4. What population was evaluated?

- 300 paintings and 2,620 eligible cases.
- 16,404 technically valid candidates:
  - Telea: 2,620
  - LaMa: 2,620
  - HINT: 2,620
  - Stable Diffusion: 8,520
  - SDXL: 24
- 31,608 candidate-region evaluations.
- Two encoders produced 63,216 metric rows.
- Eleven unresolved SDXL cases were omitted without placeholders.
- Candidate rows are nested observations, not independent paintings.

### Q5. How were 78,336 embeddings reused?

- Each encoder retained 39,168 embeddings; together they retained 78,336.
- Per encoder:
  - Clean embeddings: 2,620
  - Damaged embeddings: 4,940
  - Restored embeddings: 31,608
- Clean and damaged embeddings were reused where their source region was
  identical.
- Restored embeddings remained candidate-and-region specific.
- The bundle supports later uncertainty, retrieval, and semantic analyses.

### Q6. What did the controls and descriptive results show?

- 1,200 zero-control candidates produced 2,400 rows across both encoders.
- Their damaged and restored similarity values were 1 and improvement was 0.
- Positive-improvement rows: 46,538.
- Negative-improvement rows: 14,256.
- Zero-improvement rows: 2,422.
- CLIP–DINOv2 agreement was Pearson 0.805 and Spearman 0.727.
- The encoders broadly agree but are not interchangeable.

### Q7. What did the scratch-aware prompt comparison show?

- 1,200 generic-versus-scratch-aware candidate pairs covered 300 paintings and
  four seeds.
- Two regions and two encoders produced 4,800 paired comparisons.
- Scratch-aware win rates ranged from approximately 44.0% to 46.9%.
- Mean paired differences were slightly negative in all four groups.
- Scratch-aware prompting showed no consistent feature-similarity advantage and
  did not control candidate selection.

### Q8. What was validated, and what can N15 claim?

- Feature extraction took approximately 6,270.9 seconds, or 1 hour 44 minutes
  31 seconds.
- Metric construction took approximately 199.6 seconds, or 3 minutes 20 seconds.
- 246/247 checks passed with zero blocking failures.
- Seven canonical files and five registered artifacts were completed.
- The single warning records best-effort CUDA/CuBLAS determinism; exact bitwise
  rerun identity is not asserted.

**Strongest defensible claim**

- N15 produced complete, validated, and reusable CLIP/DINOv2 feature-similarity
  evidence for every technically valid candidate under the fixed two-region policy.

**Limitations**

- CLIP and DINOv2 are general-purpose encoders, not conservation-quality judges.
- They can miss colour, texture, seam, and historical-plausibility problems.
- The clean image is an experimental reference, not historical ground truth.
- SDXL contributes only 24 completed candidates.
- Nested and unequal observations prevent a universal ranking from N15 alone.

### N15 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Normalized CLIP and DINOv2 embeddings with clean-reference cosine-similarity improvement on two contiguous regions. |
| Population | 63,216 metric rows and 78,336 embeddings from 16,404 candidates, 2,620 cases, and 300 paintings. |
| Strongest defensible claim | Every technically valid candidate received validated two-encoder feature evidence under the declared policy. |
| Limitation | General-purpose feature similarity is not conservation quality, local defect detection, or historical truth. |

---

## 16 — Difference Maps and Spatial Diagnostics

### Repository evidence

- Notebook: `notebooks/16_difference_maps_and_spatial_diagnostics.ipynb`
- Configuration: `config/evaluation/spatial_diagnostics.yaml`
- Implementation: `src/restoration_eval/error_maps.py`
- Diagnostic table: `outputs/16_difference_maps_and_spatial_diagnostics/metrics/spatial_diagnostics.csv`
- Map index: `outputs/16_difference_maps_and_spatial_diagnostics/manifests/map_images.csv`
- Validation checks: `outputs/16_difference_maps_and_spatial_diagnostics/validation/checks.csv`
- Run manifest: `outputs/16_difference_maps_and_spatial_diagnostics/manifests/run_manifest.json`

### Q1. What does N16 calculate?

- Damaged absolute error is the mean RGB difference between clean and damaged
  pixels.
- Restored absolute error is the mean RGB difference between clean and restored
  pixels.
- Signed improvement equals damaged error minus restored error.
- Positive signed improvement means reduced reference error; negative means
  increased reference error.
- Restoration change shows where restored and damaged images differ, not whether
  the change is correct.
- Each nonzero candidate receives damaged-error, restored-error, signed,
  mask-only signed, and spatial-overlay views.

### Q2. Which regions are analysed?

- Full image and actual painting content.
- Active mask and its bounding box with an 8-pixel margin.
- Inner and outer 3-pixel boundary bands and their combined ring.
- Content outside the mask and the outside-boundary spillover ring.
- Synthetic-degradation support where applicable.
- Ordinary masks use threshold 128; synthetic effects use threshold 13.
- Empty regions are omitted and patch windows are deferred.

### Q3. What population was evaluated?

- 300 paintings, 2,620 cases, and 16,404 valid candidates.
- Candidate counts:
  - Telea: 2,620
  - LaMa: 2,620
  - HINT: 2,620
  - Stable Diffusion: 8,520
  - SDXL: 24
- 15,204 candidates are nonzero and 1,200 are zero controls.
- 2,811 candidates belong to synthetic degradation.
- Eleven unavailable SDXL cases were omitted without placeholders.
- The final table contains 143,247 candidate-region rows.

### Q4. How were heatmap colours standardized?

- One population-wide scale was calibrated across all 16,404 candidates.
- Up to 4,096 content pixels per candidate were sampled deterministically.
- Absolute-error display range: 0 to approximately 210.67.
- Signed-improvement display range: −213 to +213.
- Both use a 99.5th-percentile display limit so isolated extremes do not dominate.
- Clipping affects PNG colours only; the CSV retains unclipped numeric summaries.

### Q5. What statistics are recorded for each region?

- Mean, median, and 95th-percentile damaged and restored error.
- Mean, median, 5th-percentile, and 95th-percentile signed improvement.
- Fractions of improved, worsened, and unchanged pixels.
- Restoration-change mean, 95th percentile, maximum, and changed-pixel fraction.
- A pixel counts as changed when restoration-versus-damaged channel error exceeds
  0.5.
- These are descriptive QA indicators, not final trustworthiness flags.

### Q6. How many maps and review panels were produced?

- Five maps for each of 15,204 nonzero candidates: 76,020 maps.
- Zero controls retain numeric rows, but redundant all-zero PNGs are omitted.
- Fourteen rule-selected panels were retained:
  - Ten candidate panels: median masked improvement and highest masked worsening
    for each model.
  - Four cross-model panels covering localized loss, thin scratch, structural
    loss, and synthetic degradation.
- The map manifest contains 76,034 rows.
- Difficult selected panels illustrate behaviour; they do not estimate average
  population performance.

### Q7. Was N16 validated and published successfully?

- 137/137 checks passed with zero blocking or warning failures.
- No temporary work files remained.
- 76,039 canonical files and five registered artifact groups were completed.
- The recorded completion span was approximately 2 hours 24 minutes 33 seconds.
- That run reused 13,100 checkpointed candidates, so it is not a clean
  full-from-scratch runtime estimate.
- All 76,034 images were remotely verified in 333 indexed Hugging Face
  diagnostics bundles; local evidence remains canonical.

### Q8. What is the claim and what are the limitations?

**Strongest defensible claim**

- N16 produced complete, validated, and consistently scaled spatial error and
  change evidence for every technically valid candidate under the declared
  region policy.

**Limitations**

- Pixel-aligned reference error is not perceptual, semantic, conservation, or
  historical correctness.
- Positive local error reduction can coexist with hallucinated content.
- The clean image is an experimental reference, not historical ground truth.
- Indexed PNGs are clipped display assets, not source numeric evidence.
- Stable Diffusion observations are nested and SDXL remains bounded to 24 cases.
- N16 alone cannot rank models or assign final trustworthiness.

### N16 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Pixelwise absolute-error, signed-improvement, change, region-summary, and geometry-overlay diagnostics. |
| Population | 143,247 region rows and 76,020 maps from 16,404 candidates, 2,620 cases, and 300 paintings. |
| Strongest defensible claim | Every valid candidate received complete spatial diagnostics under one standardized map and region policy. |
| Limitation | Reduced pixel error does not establish semantic plausibility, conservation suitability, or historical truth. |

---

## 17 — Local Consistency Metrics

### Q1. What does N17 measure?

- Texture, colour, and restoration-seam consistency.
- Compares damaged and restored regions against the experimental clean reference.
- Improvement = damaged error minus restored error.
- Positive improvement means the restoration reduced that particular error.
- It does not prove overall or historical correctness.

### Q2. Which texture diagnostics are used?

- Local Binary Patterns (LBP), Gabor responses, and GLCM features.
- Gradient, edge, and orientation comparisons.
- Repeated-pattern and smoothing proxies.
- Local maps use a nine-pixel window.
- These are texture proxies, not brushwork authentication.

### Q3. Which colour and seam diagnostics are used?

- CIEDE2000, hue, chroma, and Lab-distribution differences.
- Wasserstein distance and Lab histograms.
- Seam luminance, colour, gradient, orientation, local SSIM, transition roughness, and spillover.
- Colour is interpreted in CIELAB under D65 after N02 sRGB preprocessing.

### Q4. Which regions are examined?

- Full image and painting-content region.
- Active mask and mask bounding box with an eight-pixel margin.
- Three-pixel inner and outer boundary bands.
- Outside-mask content, spillover, and degradation support where applicable.

### Q5. What population and evidence volume were evaluated?

- 300 paintings, 2,620 cases, and 16,404 restoration candidates.
- Telea: 2,620; LaMa: 2,620; HINT: 2,620; Stable Diffusion: 8,520; SDXL: 24.
- 2,060,667 diagnostic rows.
- These are nested metrics, not two million independent restorations.

### Q6. What maps and visual examples were produced?

- 9,304 nonzero primary candidates.
- Three maps per candidate: texture, colour, and seam.
- Total maps: 27,912.
- Panels contrast damaged error, restored error, and signed improvement.
- Zero controls retain numeric evidence but do not receive these maps.
- Selected panels illustrate cases; they are not population averages.

### Q7. What was validated, and how long did it take?

- 179/179 checks passed with no blockers or warnings.
- Applicable metric directions: 1,026,534 positive, 585,473 unchanged, and 415,691 negative.
- Metrics took about 15 hours 29 minutes; maps took about 11 hours 57 minutes.
- Full recorded span was about 37 hours 44 minutes, including pauses and validation.

### Q8. What is the claim and what are the limitations?

**Strongest defensible claim**

- Complete, validated, region-aware texture, colour, and seam diagnostics were produced for every technically valid candidate.

**Limitations**

- Metrics are diagnostic proxies, not expert judgments.
- CIEDE2000 does not establish historical colour accuracy.
- Smoothing or excess-detail proxies do not prove hallucination.
- There is no universal seam-failure threshold.
- Stable Diffusion candidates are nested by prompt and seed; SDXL remains bounded to 24 candidates.

### N17 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Region-aware texture, colour, seam, and signed-improvement diagnostics. |
| Population | 2,060,667 diagnostic rows from 16,404 candidates, 2,620 cases, and 300 paintings. |
| Strongest defensible claim | Every valid candidate received complete local-consistency evidence under one declared region policy. |
| Limitation | Local proxy improvement does not establish correctness, authenticity, or conservation suitability. |

---

## 18 — Diffusion Uncertainty Analysis

### Q1. What does uncertainty mean in N18?

- Empirical disagreement across repeated Stable Diffusion outputs.
- Case, prompt, and generation settings stay fixed; only seeds 2026–2029 vary.
- Higher variation means the outputs disagree more.
- It is not calibrated confidence, correctness, or historical uncertainty.

### Q2. What is an uncertainty group?

- Four outputs for the same case, prompt arm, and generation configuration.
- One output per seed creates six unordered seed pairs.
- Seeds and prompts are nested observations, not independent paintings.

### Q3. What population was included?

- 480 unique nonzero cases, 780 prompt-specific groups, and 3,120 candidates.
- 480 generic-prompt groups and 300 additional scratch-aware groups.
- Each visual category contains 156 groups.
- Case-label groups: scratch thin 600; loss small 60; loss large 60; mixed 60.

### Q4. Why are other models excluded?

- Telea, LaMa, and HINT are deterministic in this experiment.
- They are assessed through robustness or sensitivity, not repeated-seed uncertainty.
- SDXL has only one completion per case.
- Synthetic degradations are outside this repeated-seed population.

### Q5. Which uncertainty metrics are calculated?

- Pixel RGB standard-deviation mean and 95th percentile.
- Pairwise RGB MAE and RMSE.
- LPIPS, CLIP, and DINOv2 pairwise distances.
- Lower disagreement means greater consistency, not necessarily greater correctness.

### Q6. What does calibration-ready mean?

- 780 group-level rows.
- Ten uncertainty components linked to ten reference-performance metrics.
- Reference metrics are summarized across seeds using mean, sample standard deviation, and worst value.
- The table can support later calibration analysis; uncertainty is not already calibrated.

### Q7. What evidence and validation were produced?

- 93,600 uncertainty rows and 31,200 seed-reference rows: 124,800 total.
- A 300-painting generic-versus-scratch-aware prompt comparison and two summary figures.
- 150/150 checks passed with no failures or warnings.
- Recorded runtime: about 38 minutes 56 seconds.
- Spatial heatmaps are deferred to N19.

### Q8. What is the claim and what are the limitations?

**Strongest defensible claim**

- Complete, validated, multi-metric seed-disagreement evidence was produced for every eligible four-seed Stable Diffusion group.

**Limitations**

- Consistency is not correctness; four similar outputs may all be wrong.
- High disagreement indicates instability, not which output is best.
- The clean reference is experimental rather than historical ground truth.
- No combined uncertainty index or final trustworthiness flag is assigned.

### N18 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Repeated-seed pixel, perceptual, and feature disagreement with case and prompt held fixed. |
| Population | 780 groups, 3,120 candidates, and 480 unique nonzero cases. |
| Strongest defensible claim | Every eligible four-seed Stable Diffusion group received complete empirical-disagreement evidence. |
| Limitation | Empirical disagreement measures consistency, not calibrated confidence or correctness. |

---

## 19 — Uncertainty and Spatial Explanation Maps

### Q1. What does N19 calculate?

- Reuses N18 results and performs no new restoration inference.
- Calculates per-pixel standard deviation across four seed outputs and averages the RGB-channel deviations.
- Values use normalized RGB scale 0–1.
- Higher values indicate stronger spatial disagreement, not calibrated confidence.

### Q2. What population is included?

- 480 unique nonzero cases, 780 prompt-specific groups, and 3,120 Stable Diffusion candidates.
- 480 generic groups and 300 scratch-aware groups.
- The group count exceeds the case count because scratch cases have two prompt arms.

### Q3. Which regions and summaries are used?

- Six regions: full image, painting content, active mask, mask bounding box plus eight pixels, three-pixel boundary ring, and content outside the mask.
- Each records mean, median, 95th percentile, maximum, and nonzero-pixel fraction.
- Total: 4,680 spatial-summary rows.

### Q4. How are maps normalized and stored?

- Computed in float32 and archived in compressed float16.
- Maximum permitted quantization difference: 0.0005.
- Shared display scale uses the content-region 99.5th percentile: 0.1348427.
- Clipping affects visual PNGs only; numeric evidence remains unclipped.

### Q5. What other evidence appears in the panels?

- Seed-variability maps and region overlays.
- N16 absolute-error and signed-improvement maps.
- N17 texture, colour, seam, and scratch-aware local maps.
- Outputs include 780 numeric maps, 780 uncertainty panels, 780 overlays, 900 scratch-aware maps, and 6,255 manifest records.
- Evidence is brought together visually but not collapsed into one score.

### Q6. How were representative panels selected?

- Fifteen panels: three selections for each of five visual categories.
- Median generic masked uncertainty.
- Highest generic boundary concentration.
- Largest generic-versus-scratch-aware prompt difference.
- Seed 2026 supplies the displayed restoration.
- These are rule-selected examples, not average cases.

### Q7. What was validated and published?

- 149/149 checks passed with no blockers or warnings.
- 2,481 canonical files; recorded runtime about 3 hours 3 minutes.
- HF diagnostics: 2,475 visual assets, 300 bundles, 609 remote objects, and about 1.33 GB verified.

### Q8. What is the claim and what are the limitations?

**Strongest defensible claim**

- Complete and consistently scaled spatial maps of empirical seed disagreement were produced for all 780 eligible Stable Diffusion groups.

**Limitations**

- Only Stable Diffusion 1.5 has four-seed evidence; synthetic degradations and SDXL are excluded.
- Low disagreement can accompany consistently incorrect outputs.
- High disagreement identifies sensitivity, not the correct restoration.
- Bright heatmap colours are not universal failure thresholds.
- No final explanation score or trustworthiness flag is assigned.

### N19 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Per-pixel four-seed RGB disagreement, six-region summaries, and linked spatial diagnostics. |
| Population | 780 prompt groups, 3,120 candidates, and 480 unique nonzero cases. |
| Strongest defensible claim | Every eligible group received complete, consistently scaled spatial disagreement evidence. |
| Limitation | A disagreement map localizes instability; it does not identify correctness or calibrated confidence. |

---

## 20 — Semantic and Structural Consistency

### Q1. What does N20 evaluate?

- Reference-relative semantic and structural representation changes.
- Global and local similarity, worsened-patch fraction, outside-mask change, structural affinity, painterly-representation proxy, and CLIP–DINOv2 agreement.
- These are proxies, not direct measures of meaning, authenticity, or conservation quality.

### Q2. Which encoders are used?

- CLIP ViT-B/32: 512-dimensional features and a coarse 7×7 token grid.
- DINOv2 ViT-S/14: 384-dimensional features and a finer 16×16 token grid.
- Both use 224×224 aspect-preserving letterboxing.
- Padded tokens are excluded and mask overlap is area weighted.

### Q3. What population is evaluated?

- 300 paintings, 2,620 cases, and 16,404 candidates.
- Telea: 2,620; LaMa: 2,620; HINT: 2,620; Stable Diffusion: 8,520; SDXL: 24.
- 15,204 nonzero and 1,200 zero-control candidates.
- 31,608 candidate-region evaluations per encoder and 78,336 source-token records.

### Q4. How is the metric table constructed?

- 447,312 total rows.
- Global subject preservation: 32,808.
- Local similarity: 189,648; worsened fraction: 63,216; outside-context change: 32,808.
- Structural layout: 65,616; painterly representation: 31,608; encoder agreement: 31,608.
- These are nested diagnostic rows, not independent observations.

### Q5. What do the main metrics mean?

- Local cosine similarity: aligned feature similarity.
- Worsened fraction: share of patches moved farther from the reference.
- Outside-context change: changes beyond the mask.
- Affinity correlation, Jensen–Shannon divergence, and centroid shift: preservation of spatial relationships.
- Patch-covariance distance: change in DINOv2 feature relationships.
- Encoder agreement: correspondence between CLIP and DINOv2 evidence.

### Q6. What maps and examples are retained?

- 63,216 numeric seven-channel map bundles and 9,304 rendered panels.
- Channels cover damaged-clean, restored-clean, signed improvement, restored-damaged, and clean/damaged/restored affinity.
- Zero controls remain in scalar tables but are not rendered.
- Fifteen representative cases span the five visual categories.

### Q7. What was validated and published?

- 181/181 checks passed with no blockers.
- 9,311 canonical files and six registered artifacts.
- Recorded span: about 2 hours 8 minutes; checkpoint reuse means this is not a cold-run benchmark.
- HF diagnostics: 9,304 assets, 513 bundles, 823 remote objects, and about 14.07 GB verified.

### Q8. What is the claim and what are the limitations?

**Strongest defensible claim**

- Complete, validated, reference-relative semantic and structural proxy evidence was produced for every technically valid candidate.

**Limitations**

- CLIP and DINOv2 are not conservation-specific.
- Similarity does not prove identity, plausibility, or historical correctness.
- CLIP localization is coarse; DINOv2 affinity is not causal attribution or eye tracking.
- No face, anatomy, architecture, or object detector is used.
- Patch covariance does not authenticate brushwork, artist, or style.
- SDXL remains bounded to 24 candidates; no combined semantic score or final flag is assigned.

### N20 defence summary

| Required distinction | Short answer |
|---|---|
| Method | CLIP- and DINOv2-based global, local, structural, and cross-encoder proxy diagnostics. |
| Population | 447,312 metric rows from 16,404 candidates, 2,620 cases, and 300 paintings. |
| Strongest defensible claim | Every valid candidate received complete reference-relative semantic and structural proxy evidence. |
| Limitation | General-purpose feature similarity does not establish semantic truth, authenticity, or conservation suitability. |

---

## 21 — Multi-Model Comparison

### Q1. What method does N21 use?

- Read-only synthesis of previously calculated evidence.
- Selects candidates independently of their metric results.
- Compares models with 11 separate quality anchors and one balanced vote per evidence family.
- Uses leave-one-painting-out analysis to test ranking stability.
- Performs no new restoration inference.

### Q2. What population is compared?

- 300 paintings and 2,620 cases: 1,500 canonical, 245 damage-size, 525 mask-robustness, and 350 eligible synthetic-degradation cases.
- Four full-coverage methods produce 10,480 candidates.
- Adding 24 SDXL candidates gives 10,504 selected candidates.

### Q3. What evidence and outputs are produced?

- 3,160,618 normalized evidence rows across 17 evidence families and 352 metric IDs.
- 277,319 model-comparison rows and 2,181 disagreement rows.
- 168 representative rows across 36 case slots.
- The report contains 58 embedded images.
- No combined quality score is created.

### Q4. What did the overall comparison find?

- LaMa led 10/11 overall quality anchors and 9/10 evidence-family outcomes.
- Telea led crop SSIM and one evidence family.
- Most anchors covered 2,320 nonzero cases; structural affinity covered all 2,620.
- This supports scoped reference-relative performance, not universal model superiority.

### Q5. What is the bounded SDXL comparison?

- 24 cases from 19 paintings.
- Five methods are available, giving 120 matched candidate-case rows.
- This is a descriptive subset, not a full-dataset SDXL benchmark.

### Q6. What did disagreement and stability show?

- 161/201 scope groups had divided evidence-family results.
- Different metrics frequently preferred different methods.
- The median overall winner survived 100% of leave-one-painting-out repetitions.
- Ranking stability does not prove historical or conservation correctness.

### Q7. What was validated, and what can N21 claim?

- 187/187 checks and all 19 roadmap responsibilities passed.
- Nine canonical files; runtime approximately 59 minutes 34 seconds.
- The main comparison CSV was remotely published and checksum-verified.
- **Claim:** LaMa had the strongest overall reference-relative balance within the declared population and evidence framework.
- **Limits:** no authenticity, calibrated confidence, conservation approval, universal best-model claim, or combined quality score.

### N21 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Metric-independent, direction-aware synthesis with balanced evidence-family voting and leave-one-painting-out stability. |
| Population | 10,504 selected candidates from 2,620 cases and 300 paintings, including 24 bounded SDXL candidates. |
| Strongest defensible claim | LaMa showed the strongest scoped reference-relative balance across the declared anchors. |
| Limitation | Stable or majority-supported rankings do not establish authenticity, universal superiority, or conservation approval. |

---

## 22 — Damage-Size Diffusion Uncertainty Extension

### Q1. What does N22 do?

- Extends the damage-size experiment to four Stable Diffusion seeds.
- Reuses seed 2026 from N11 and generates only seeds 2027–2029.
- Holds the model, DDIM settings, generic prompt, and compositing policy fixed.
- It does not modify earlier notebook evidence.

### Q2. What is the exact population?

- 35 paintings: seven per visual category.
- Seven nested damage levels: 2%, 4%, 6%, 8%, 10%, 15%, and 20%.
- 245 cases and uncertainty groups.
- Four seeds per group produce 980 candidates and 1,470 unordered seed pairs.
- 735 candidates were newly generated.

### Q3. Which uncertainty measurements are used?

- Pixel RGB standard deviation and pairwise RGB MAE/RMSE.
- LPIPS, CLIP, and DINOv2 distances.
- Pixel evidence uses six regions; learned metrics use content and mask bounding-box crop.
- No combined uncertainty index is created.

### Q4. How do the metric rows break down?

- 20,580 image-space rows.
- 2,940 LPIPS rows.
- 5,880 CLIP/DINOv2 rows.
- 3,920 seed-2026 reference rows.
- Total: 33,320 rows.
- Only seed 2026 has joined reference, spatial, local, and semantic evidence.

### Q5. What outputs and runtime were recorded?

- 735 restoration images, 245 numeric maps, and 245 overlay PNGs.
- A 735-row candidate table and 245-row map manifest.
- 988 canonical files overall.
- Generation took about 108 minutes; median 9.053 seconds per new candidate, with no retries.

### Q6. What was validated and published?

- 236/236 checks and all 12 roadmap duties passed.
- Candidate and diagnostic assets were separately published and verified.
- CUDA execution on another system may not be byte-identical.

### Q7. What is the claim and what are the limitations?

- **Claim:** N22 completed four-seed empirical-variability evidence across seven matched damage levels for 35 Stable Diffusion painting trajectories.
- **Limits:** N22 enables later association analysis but does not itself prove variability rises with damage; 35 paintings are independent, not 245; variability is not calibrated confidence; low variability can still be consistently wrong; balanced categories do not establish style effects.

### N22 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Fixed-condition four-seed Stable Diffusion disagreement across seven nested damage levels. |
| Population | 35 paintings, 245 groups, 980 candidates, and 1,470 seed pairs. |
| Strongest defensible claim | Complete empirical-variability evidence exists for every declared damage-size trajectory. |
| Limitation | The notebook measures repeated-seed disagreement, not calibrated confidence or correctness. |

---

## 23 — Damage-Size Sensitivity Analysis

### Q1. What statistical method does N23 use?

- Controlled within-painting damage-size analysis.
- Theil–Sen slopes estimate robust trends per additional ten percentage points of damage.
- Painting-cluster bootstrap resamples paintings 5,000 times.
- Paired sign-flip tests use 100,000 simulations with a +1 correction.
- Rank-biserial effects and Benjamini–Hochberg correction support paired inference.
- Seven anchors are confirmatory; four remain descriptive.

### Q2. What is the exact population?

- 35 independent paintings: five categories × seven paintings.
- Seven levels: 2%, 4%, 6%, 8%, 10%, 15%, and 20%.
- 245 cases and 980 candidates from Telea, LaMa, HINT, and Stable Diffusion 1.5.
- Stable Diffusion uses the generic prompt and seed 2026.
- Four-seed uncertainty contains 245 groups and 1,470 seed pairs.
- SDXL is excluded because no matched population exists.

### Q3. What evidence is retained?

- Eleven separate anchors covering MAE, SSIM, LPIPS, CLIP/DINOv2, spatial error, texture, colour, seam, local semantics, and structural affinity.
- 7,035 analysis rows, including 494 inferential rows.
- Performance, ranking, and uncertainty figures plus a self-contained report.
- Runtime remains separate from quality ranking; no combined score is created.

### Q4. What were the main damage-size results?

- All 245 masks preserved the intended nested design.
- Maximum target-versus-realized area error: 0.0002 percentage points.
- Lowest adverse slope: LaMa 5/11 anchors, Stable Diffusion 4/11, Telea 2/11, HINT 0/11.
- LaMa ranked first under the family-balanced summary at all seven levels.
- This does not establish LaMa as universally best.

### Q5. What happened to Stable Diffusion disagreement?

- All five main uncertainty components had positive slopes.
- Four of five met the corrected q ≤ 0.05 rule; DINOv2 pairwise distance did not.
- Increasing disagreement means increasing empirical variability, not decreasing calibrated confidence.

### Q6. What was validated?

- 124/124 checks passed with no blocking or warning failures.
- Eight canonical files and six registered artifacts.
- Runtime approximately 5 hours 27 minutes; no restoration inference occurred.
- All compact canonical files are Git-tracked.

### Q7. What is the claim and what are the limitations?

- **Claim:** controlled damage size changed measured restoration behaviour, conditional on model, metric, painting, and uncertainty source.
- **Limits:** only 35 independent paintings; synthetic missing regions; no universal damage threshold; no independent category/style, authenticity, conservation, or model-class effect.

### N23 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Painting-level robust slopes, clustered resampling, paired tests, and separate quality anchors. |
| Population | 35 paintings, 245 cases, 980 primary candidates, and 245 four-seed uncertainty groups. |
| Strongest defensible claim | Damage size was associated with conditional changes in measured model behaviour. |
| Limitation | The controlled trends do not define a universal failure threshold or prove causal effects beyond this population. |

---

## 24 — Mask Robustness Analysis

### Q1. What does N24 measure?

- Sensitivity to valid changes in mask placement, geometry, and component layout.
- Compares five matched mask variants.
- Median absolute deviation (MAD) is the primary stability measure; standard deviation and range are descriptive.
- This measures input-mask robustness, not repeated-seed uncertainty.

### Q2. What is the exact population?

- 35 paintings: five categories × seven paintings.
- Three fixed family-area conditions: thin scratch 2%, small loss 4.5%, and large loss 12.5%.
- 105 painting-condition groups × five variants = 525 cases.
- Four methods per case produce 2,100 candidates.
- The independent sample size is 35 paintings, not 525 masks.

### Q3. What statistical design is used?

- Within-group MAD, standard deviation, and range.
- 5,000 painting-cluster bootstrap draws and 100,000 paired sign flips with +1 correction.
- Rank-biserial effects and Benjamini–Hochberg correction.
- One balanced ranking vote per evidence family.
- Within-group-centred Spearman morphology associations remain exploratory and non-causal.

### Q4. What evidence and outputs are retained?

- Eleven quality anchors; seven confirmatory and four descriptive.
- 44,847 analysis rows across dispersion, contrasts, ranks, winner stability, morphology, and runtime.
- Two figures, a self-contained report, manifests, and validation.
- Runtime is excluded from quality ranking; no combined quality or trust score is produced.

### Q5. Which method appeared most stable?

- LaMa had the lowest overall MAD on 10/11 anchors; Telea led the texture anchor.
- LaMa ranked first in 369/525 family-balanced variant comparisons.
- Five cases had tied winners.
- Low variability means stability, not necessarily high restoration quality.

### Q6. Did changing the mask change conclusions?

- The anchor winner changed in 625/1,155 group-anchor combinations.
- Median changed anchors: thin scratch 7/11; small loss 5/11; large loss 5/11.
- 86 paired contrasts met corrected-q and confidence-interval rules.
- 77/396 morphology associations met those rules but remain non-causal.

### Q7. What was validated, and what can N24 claim?

- 139/139 checks passed; seven canonical files and five registered artifacts.
- Runtime approximately 1 hour 45 minutes.
- The 52.16 MB metric table is published and verified on Hugging Face.
- **Claim:** valid mask placement and geometry changes can alter measured quality and the preferred method.
- **Limits:** family and area are confounded; variants are synthetic; one fixed Stable Diffusion candidate is used; stability does not establish authenticity or conservation suitability.

### N24 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Five-variant within-group dispersion, paired inference, rankings, and exploratory mask-morphology analysis. |
| Population | 35 paintings, 105 matched groups, 525 cases, and 2,100 candidates. |
| Strongest defensible claim | Mask realization can change measured performance and preferred method in the controlled population. |
| Limitation | Robustness is not quality, and the paired family-area design cannot separate independent family and size effects. |

---

## 25 — Synthetic Degradation Analysis

### Q1. What method and population does N25 use?

- Eligibility-gated analysis of procedural RGB degradations.
- Candidate selection occurred before metric inspection; no restoration inference or upstream metric recomputation occurs.
- 1,155 procedural cases were generated across 35 paintings.
- Only 350 approved localized cases enter comparison: 315 single-degradation and 35 combined cases.
- Excluded combinations are scope decisions, not model failures.

### Q2. Which cases and candidates are compared?

- Dirt/dust, partial transparency, and water stain at mild, moderate, and severe levels.
- Water-stain-plus-dirt at the moderate level.
- Telea, LaMa, HINT, and Stable Diffusion each contribute 350 candidates.
- Eleven bounded SDXL candidates give 1,411 selected candidates overall.
- Stable Diffusion uses the generic prompt and seed 2026.

### Q3. What statistical and metric design is used?

- Painting is the independent unit: n = 35; cases, severities, models, and anchors are nested.
- Eleven quality anchors remain separate with one balanced vote per evidence family per case.
- 5,000 painting-cluster bootstrap draws and 100,000 paired sign flips with +1 correction.
- Theil–Sen severity slopes and within-family Spearman area associations.
- Runtime and spillover are excluded from quality ranking; no combined score is created.

### Q4. What were the main model findings?

- Mean family-balanced ranks: LaMa 1.505, Telea 2.548, Stable Diffusion 2.921, HINT 3.026.
- LaMa led all four eligible degradation families, all 35 painting summaries, and 8/11 anchors.
- Stable Diffusion led CLIP and DINOv2 feature anchors; Telea led crop SSIM; HINT led none.
- This is a scoped computational result, not a universal model ranking.

### Q5. What did severity and combined-degradation analysis show?

- No universal rule showed that greater configured severity or affected area worsened every model.
- Water stain showed the clearest adverse tendency; other families were mixed or non-monotonic.
- Water-stain-plus-dirt was harder than dirt/dust for all four methods but harder than water stain for only one.
- These are computational contrasts, not physical interaction or material synergy.

### Q6. What outputs, validation, and publication evidence exist?

- 34,977 analysis rows across 17 analysis types.
- Two figures and a self-contained 15-section report.
- Seven canonical files and five registered artifact groups.
- 129/129 checks passed; runtime approximately 2 hours 38 minutes 57 seconds.
- The 41.97 MB table is published and verified in HF diagnostics; compact outputs form the GitHub handoff.

### Q7. What is the claim and what are the limitations?

- **Claim:** within the approved 350-case procedural population, LaMa had the strongest overall reference-aligned correction balance across the 11 anchors.
- **Limits:** procedural RGB effects are not exact material ageing; severity is ordinal; area associations are non-causal; no repeated-seed synthetic uncertainty exists; the 11-case SDXL subset is incomplete; no style, authenticity, or conservation claim is supported; zero outside-mask change proves containment, not successful repair.

### N25 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Eligibility-gated, painting-level analysis of localized procedural degradation with separate evidence anchors. |
| Population | 35 paintings, 350 eligible cases, 1,400 primary candidates, and 11 bounded SDXL candidates. |
| Strongest defensible claim | LaMa had the strongest scoped reference-aligned balance for the approved procedural population. |
| Limitation | Procedural stress tests and computational proxies do not establish physical damage, authenticity, or conservation approval. |

---

## 26 — Grouped and Statistical Analysis

### Q1. What method does N26 use?

- Read-only statistical synthesis with no restoration or metric inference.
- Painting is the independent unit; cases, masks, seeds, regions, and metrics are repeated observations.
- Eleven anchors remain separate across ten evidence families with one balanced vote per family.
- Uses 5,000 painting-cluster bootstrap samples, paired sign flips, effect sizes, and multiple-testing correction.
- No combined quality, uncertainty, efficiency, or trust score.

### Q2. What is the exact population?

- 300 paintings and 2,620 cases: 1,500 canonical, 245 damage-size, 525 mask-robustness, and 350 synthetic-degradation cases.
- Four full methods produce 10,480 candidates.
- Quality inference uses 2,320 nonzero cases and 9,280 candidates.
- The 1,200 zero-control candidates are integrity evidence.
- Twenty-four SDXL candidates form a bounded subset; 10,504 candidates are selected overall.

### Q3. What evidence and uncertainty are included?

- 3,150,114 normalized evidence rows and 102,344 nonzero candidate-anchor rows.
- Eleven anchors cover pixel, perceptual, feature, spatial, texture, colour, seam, semantic, and structural evidence.
- Stable Diffusion uncertainty contains 1,025 four-seed groups: 780 canonical plus 245 damage-size.
- Mask robustness is input sensitivity, not seed uncertainty; synthetic degradation has no repeated-seed population.

### Q4. What were the main model results?

- Family-balanced ranks: LaMa 1.10, HINT 2.50, Telea 2.55, Stable Diffusion 3.85.
- LaMa won 10/11 anchors; Telea won crop SSIM.
- 63/66 paired comparisons remained significant after correction.
- LaMa led all five visual categories, but this is category evidence, not an independent historical-style effect.
- Thin scratches differed: Telea led 6/11 anchors, HINT 3/11, and LaMa 2/11.

### Q5. What did stability and uncertainty analysis show?

- LaMa remained first across all leave-one-painting, leave-one-family, supported region-policy, and 5,000 bootstrap repetitions.
- Zero controls tied on their only applicable integrity anchor.
- 64/140 uncertainty-performance associations remained significant after correction.
- Variability is an instability signal, not calibrated confidence or correctness.

### Q6. What outputs and validation evidence exist?

- 13,272 statistical rows, 694 correlation rows, and 1,344 ranking-stability rows.
- Three figures and a self-contained 15-section report.
- Ten canonical files and eight artifacts; 111/111 checks passed.
- Final runtime approximately 3 hours 9 minutes 35 seconds.
- All outputs are Git-tracked.

### Q7. What is the claim and what are the limitations?

- **Claim:** within the declared nonzero Controlled-300 population, LaMa had the strongest and most stable overall family-balanced performance.
- **Limits:** one controlled dataset; 24-case SDXL subset; focused experiments have 35 independent paintings; uncertainty covers only supported Stable Diffusion groups; no universal superiority, authenticity, conservation approval, calibrated confidence, or style effect.

### N26 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Painting-level grouped statistics, separate anchors, clustered resampling, paired inference, and ranking stability. |
| Population | 300 paintings, 2,620 cases, 10,480 full-method candidates, and 24 bounded SDXL candidates. |
| Strongest defensible claim | LaMa had the strongest and most stable overall balance under the declared framework. |
| Limitation | Stable controlled-dataset ranks do not establish universal superiority or conservation truth. |

---

## 27 — Failure Taxonomy and Trustworthiness Flags

### Q1. What method does N27 use?

- Applies transparent rules to validated evidence without new inference.
- Defines 14 operational failure categories and 11 independent review flags.
- Assigns one review recommendation per candidate.
- One critical indicator or warnings from two distinct components triggers a category.
- Missing evidence remains insufficient; no combined trust or confidence score is created.

### Q2. What population is screened?

- 10,504 primary candidates: 10,480 full-method plus 24 bounded SDXL candidates.
- 4,100 repeated-seed candidates across 1,025 groups.
- Primary/uncertainty overlap: 725; uncertainty-only: 3,375.
- Exact union: 13,879 unique candidates.
- Uncertainty-only candidates cannot inflate model comparison.

### Q3. How are thresholds defined?

- Fitted only on 9,280 nonzero four-method primary candidates.
- Higher-is-worse warning/critical thresholds: 90th and 97.5th adverse percentiles.
- Lower-is-worse thresholds: 10th and 2.5th percentiles.
- Thresholds are stratified by experiment, indicator, region, and statistic.
- Outside-mask warning/critical tolerances: 5e-7 and 5e-6.
- These are relative screening rules, not probabilities or conservation grades.

### Q4. What categories, flags, and rows are produced?

- Categories cover residual error, blur, structure/semantics, texture repetition, smoothing, colour drift, seams, spillover, and instability.
- Flags cover uncertainty, semantic, structural, texture, colour, boundary, outside-mask, disagreement, missingness, and manual review.
- 194,306 assignment rows and 152,669 flag rows.
- Triggered assignments: 16,840; triggered flags: 41,315.
- Other states remain not-triggered, insufficient, or not-applicable.

### Q5. What were the main screening findings?

- Mean triggered-category fraction: LaMa 0.033, HINT 0.045, Telea 0.116, Stable Diffusion 0.160.
- 4,844 candidates triggered metric disagreement.
- High uncertainty occurred in 126 groups; stricter instability in 60.
- Recommendations: 10,573 specialist review; 2,366 do not rely automatically; 183 unstable; 757 preliminary inspection only.
- Fewer flags mean lower burden under these rules, not proven correctness.

### Q6. What was validated and published?

- 167/167 checks passed; eight canonical files and six artifacts.
- Final runtime approximately 5 hours 14 minutes 15 seconds.
- Compact files are Git-tracked.
- Large assignment and flag ledgers are published and checksum-verified on HF diagnostics.

### Q7. What is the claim and what are the limitations?

- **Claim:** N27 supplies a reproducible screening system for exposing adverse evidence, disagreement, uncertainty, and missingness so human review can be prioritized.
- **Limits:** rules are not conservator-trained labels; cutoffs are population-relative; deterministic uncertainty is not-applicable rather than zero; single-seed SDXL is insufficient; flags cannot certify authenticity, safety, conservation suitability, or automatic acceptance.

### N27 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Transparent adverse-tail rules, complete assignment/flag ledgers, and explicit missingness states. |
| Population | 13,879 unique primary and supported repeated-seed candidates. |
| Strongest defensible claim | The rules provide reproducible evidence screening and review prioritization. |
| Limitation | Operational flags are not calibrated probabilities, expert labels, or conservation approval. |

---

## 28 — Metric and Region-Policy Ablation

### Q1. What method does N28 use?

- Read-only evaluation-policy sensitivity analysis.
- Tests 23 fixed scenarios: 12 metric, six region, two threshold, and three aggregation scenarios.
- Eighteen metric/region scenarios support ranking.
- Uses painting-level, evidence-family-balanced ordinal ranks.
- Performs no inference and creates no combined quality/trust score.

### Q2. What is the exact population?

- 300 paintings, 2,620 matched cases, and 10,480 full-method candidates.
- Ranking uses 2,320 nonzero cases and 9,280 candidates.
- The 300 zero controls and 1,200 candidates remain explicit but unranked.
- Flag sensitivity uses all 13,879 candidates.
- Twenty-four SDXL candidates remain a bounded branch.

### Q3. Which threshold and aggregation alternatives are tested?

- Baseline warning/critical percentiles: 90/97.5.
- More-sensitive policy: 80/95.
- More-specific policy: 95/99.
- Aggregation alternatives: one warning, three warnings, or critical-only.
- Missing evidence always remains insufficient.

### Q4. How stable were model and case rankings?

- LaMa was first or joint first in all 18 ranking scenarios.
- Classical-only evidence tied LaMa and Telea.
- HINT and Telea changed positions.
- Stable Diffusion ranked fourth in 17 scenarios and tied Telea at rank 3.5 once.
- Case-rank correlation with baseline: mask-bbox-only 0.967, boundary-only 0.533, outside-mask-only 0.095.
- Only LaMa's top/co-top status was invariant; the full ordering was not.

### Q5. How sensitive were the flags?

- Removing CLIP changed 62 candidates, or 0.4%.
- Removing DINOv2-derived evidence changed 13,834, or 99.7%.
- More-sensitive thresholds added 9,770 triggered rows and changed 6,877 candidates.
- More-specific thresholds removed 6,453 rows and changed 4,790 candidates.
- Fewer flags after removing evidence can indicate evidence loss, not improvement.

### Q6. What outputs and validation evidence exist?

- 47,508 ablation rows and 319,217 candidate-scenario stability rows.
- Two figures and a self-contained 12-section report.
- Eight canonical files; 122/122 checks passed.
- Runtime approximately 12 hours 20 minutes.
- The 165.21 MB stability table is HF-verified; other outputs are Git-tracked.

### Q7. What is the claim and what are the limitations?

- **Claim:** LaMa's first-place conclusion survived every declared policy scenario, while case priorities and operational flags were materially policy-sensitive.
- **Limits:** thresholds are not calibrated probabilities or expert labels; features are proxies; results cover a controlled synthetic-damage population; no authenticity, conservation approval, external generalization, or universal superiority claim.

### N28 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Twenty-three fixed metric, region, threshold, and aggregation policy ablations. |
| Population | 300 paintings, 10,480 core candidates for ranking, and 13,879 candidates for flag sensitivity. |
| Strongest defensible claim | LaMa's top status was robust, but case ranks and flags depended materially on policy choices. |
| Limitation | Policy robustness does not calibrate flags or establish universal model correctness. |

---

## 29 — Explainable AI and Case Retrieval

### Q1. What method does N29 use?

- Builds a traceable explanation catalogue from N15–N28 evidence.
- Connects identity, assets, flags, triggering evidence, regions, missingness, and review actions.
- Adds selected counterfactual explanations and embedding-based similar-case retrieval.
- Performs no restoration, feature, or metric inference.

### Q2. What is the exact population?

- 13,879 candidates across 2,620 cases and 300 paintings.
- 10,480 matched primary candidates; 9,280 nonzero primary candidates have local-map coverage.
- 4,100 repeated-seed candidates in 1,025 groups.
- Twenty-four bounded SDXL candidates.
- 13,144 candidates are eligible in both retrieval views.
- The 735 N22 extension candidates lack N15 embeddings and remain retrieval-ineligible.
- Style/period metadata is descriptive for 268 paintings.

### Q3. How does similar-case retrieval work?

- Ten queries: one lower-risk and one flagged query for each category.
- Five lower-risk and five flagged neighbours per query: 100 rows total.
- DINOv2 restored-content cosine similarity ranks neighbours; CLIP remains separate.
- Self, same-case, and same-painting matches are excluded; the pool can cross methods.
- There is no correctness threshold.

### Q4. How are explanations and counterfactuals organized?

- Fourteen panels: two each for damage size, mask placement, model, metric subset, seed, evidence-family removal, and prompt policy.
- Prompt comparison is generic versus scratch-aware, not style-specific.
- Twenty-four selected visual units illustrate the complete catalogue; they do not filter it.
- Missing and non-applicable evidence stay explicit.

### Q5. What did the catalogue and retrieval show?

- 757 lower-risk candidates and 13,122 requiring manual review.
- Lower-risk shares: LaMa 11.1%, HINT 10.2%, Telea 7.0%, Stable Diffusion 0.3%, SDXL 0%.
- Frequent signals: insufficient evidence 84.8%, metric disagreement 34.9%, structural inconsistency 20.8%.
- Visual resemblance crossed risk categories.
- Similarity and lower-risk status do not establish correctness.

### Q6. What outputs and validation evidence exist?

- 13,879-row explanation catalogue and 100-row neighbour table.
- Fourteen counterfactual and ten retrieval panels.
- Self-contained 14-section report with 34 embedded images.
- Thirty physical files; 146/146 checks passed.
- Runtime approximately 1 hour 18 minutes.
- The 46.81 MB catalogue is HF-verified; other files are Git-tracked.

### Q7. What is the claim and what are the limitations?

- **Claim:** N29 provides a complete, traceable screening catalogue where recommendations can be investigated through rules, spatial evidence, counterfactuals, and similar precedents.
- **Limits:** retrieval is resemblance, not correctness; flags are not expert ground truth; selected panels are not causal estimates; uncertainty is seed variability rather than confidence; no authenticity, approval, style-effect, or universal model claim.

### N29 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Candidate-level explanation catalogue, rule traces, counterfactual panels, and DINOv2/CLIP retrieval. |
| Population | 13,879 candidates, with 13,144 eligible for both retrieval views. |
| Strongest defensible claim | Every candidate has a traceable screening record, and eligible cases can be inspected against similar precedents. |
| Limitation | Explanation and similarity support review; they do not prove causality, correctness, or authenticity. |

---

## 30 — Model Cards, Compute, and Scalability

### Q1. What does N30 do?

- Consolidates model provenance, limitations, and compute evidence.
- Produces five model cards and summarizes observed runtime, memory, storage, and throughput.
- Creates explicitly labelled scaling projections.
- Performs no restoration inference; projections are not executed experiments.

### Q2. What model population is documented?

- Telea, LaMa, and HINT: 2,620 completed candidates each.
- Stable Diffusion: 8,520 completed candidates.
- SDXL: 35 scheduled cases across 30 paintings; 24 completed, one timed out, and ten skipped under the budget.
- The first four methods are full-scope; SDXL remains partial.

### Q3. What does each model card contain?

- Exact version, method family, purpose, training-data information, and licences.
- Input/mask constraints; deterministic, stochastic, and prompt behaviour.
- Domain gap, bias risks, known limits, hardware, strengths, weaknesses, and excluded uses.
- Evaluation status.
- Each card contains 13 structured sections.

### Q4. What observed compute results are recorded?

- Median seconds per candidate: Telea 0.519, LaMa 1.451, HINT 6.677, Stable Diffusion 8.620, SDXL 198.032.
- Stable Diffusion peak allocation approximately 2.81 GB; SDXL approximately 5.63 GB.
- Stable Diffusion produced about 6.19 GB of owned outputs.
- Runtime describes one recorded workstation, not universal speed.

### Q5. What does the 600-painting projection estimate?

- Central generation runtime: Telea 0.73 h, LaMa 1.92 h, HINT 8.81 h, Stable Diffusion 39.78 h.
- Model-owned storage: approximately 3.73, 3.78, 3.84, and 12.35 GB respectively.
- Projections exclude caches, environments, Git history, and downstream metrics.

### Q6. What does the full-design SDXL projection estimate?

- 2,620 cases, including 2,320 inference calls and 300 zero controls.
- Central runtime approximately 128.6 hours, or 5.36 days.
- Sensitivity range approximately 127.6–133.1 hours; this is not a confidence interval.
- Projected model-owned storage approximately 1.84 GB.
- The estimate is extrapolated from only 24 completed cases.

### Q7. What was validated, and what can N30 claim?

- Five cards, 42 compute rows (32 observed and ten projected), two figures, 12 files, and six artifact records.
- 178/178 checks passed; runtime approximately one hour.
- **Claim:** N30 provides traceable model scope, provenance, observed operational cost, and clearly separated projections.
- **Limits:** projections are not executed; runtime is hardware-specific; storage excludes downstream products; anchor wins are descriptive; cards are not conservation approval; SDXL cannot support full-scope ranking.

### N30 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Structured model documentation plus observed compute summaries and clearly labelled projections. |
| Population | Four full-scope methods plus a 35-scheduled/24-completed bounded SDXL branch. |
| Strongest defensible claim | The project documents model provenance and operational scaling transparently. |
| Limitation | Hardware-specific observations and extrapolations are not universal benchmarks or executed results. |

---

## D01 — HINT versus MAT Method Selection

### Q1. What method did D01 use?

- Paired method-selection experiment comparing HINT and MAT on the same cases.
- Cases were selected before reading performance results.
- Nine separate metric anchors plus visual inspection were used.
- No combined quality score was constructed.

### Q2. What was the population?

- 12 cases from five paintings.
- All five visual categories and four damage families were represented.
- Two candidates per case: one HINT and one MAT.
- 24 restoration candidates and 108 paired case–metric comparisons.

### Q3. How were the different input resolutions handled?

- HINT ran natively at 768 × 768.
- MAT ran at its supported 512 × 512 resolution.
- MAT inputs were resized to 512, restored, returned to 768, and exactly composited inside the original mask.
- Observed pixels outside the mask were preserved.

### Q4. What result selected HINT?

- HINT won 96 of 108 case–metric comparisons.
- MAT won six; six were ties.
- HINT was especially stronger on thin scratches and local continuity.
- MAT often retained scratches or introduced pale fragmented structures.
- HINT remained imperfect on some large and mixed losses.

### Q5. Did licensing influence the choice?

- HINT software uses the permissive MIT licence.
- MAT uses CC-BY-NC-4.0 and is restricted to non-commercial use.
- Checkpoint terms must still be reviewed separately from code licences.

### Q6. What was validated?

- All 24 candidates completed.
- 94/94 checks passed.
- Runtime was approximately 56 minutes.
- Metrics, diagnostic maps, figures, report, decision record, and manifests were retained.

### Q7. What is the claim and what are the limitations?

- **Claim:** HINT was the better candidate for expansion within this paired selection study.
- **Limits:** only 12 purposively selected cases from five paintings were tested.
- D01 does not prove that HINT universally outperforms MAT or other methods.

### D01 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Paired HINT/MAT comparison using nine separate anchors and visual review. |
| Population | 12 cases, five paintings, four damage families, and 24 candidates. |
| Strongest defensible claim | HINT was the better additional method to expand under this selection design. |
| Limitation | The purposive pilot does not establish full-benchmark or universal superiority. |

---

## 12A — Full HINT Restoration

### Q1. What restoration method does N12A use?

- Official HINT generator with the Places2 checkpoint.
- Deterministic learned, mask-aware inpainting.
- Native 768 × 768 inference validated by D01.
- Exact-mask compositing preserves pixels outside the missing region.

### Q2. What population was restored?

- 2,620 eligible cases: 1,500 canonical, 245 damage-size, 525 mask-robustness, and 350 eligible synthetic-degradation cases.
- 2,320 model inferences.
- 300 zero controls copied as identity outputs.

### Q3. Why were only 350 synthetic-degradation cases eligible?

- HINT is used for masked missing-region restoration.
- Only degradations with a valid removal/inpainting interpretation entered this branch.
- Full-image colour, blur, and similar effects were not relabelled as missing-region tasks.

### Q4. How was reproducibility protected?

- Fixed checkpoint, configuration, and deterministic execution.
- Canonical mask convention: one means missing.
- Checksum-aware resume prevented duplicate work.
- Outside-mask pixels were checked for exact invariance.

### Q5. What runtime and outputs were recorded?

- 2,620 restored RGB PNGs.
- Model-processing time: 16,025.75 seconds, approximately 4 hours 27 minutes.
- Complete notebook wall time: approximately 5 hours 54 minutes.
- Mean runtime: approximately 6.12 seconds per eligible case.
- 82/82 validation checks passed.

### Q6. What did HINT add to the benchmark?

- A fourth fully evaluated core method.
- Learned long-range, mask-aware completion without text prompting.
- A useful contrast with Telea, LaMa, and prompt-conditioned Stable Diffusion.

### Q7. What is the claim and what are the limitations?

- **Claim:** HINT completed the declared 2,620-case population reproducibly and passed its technical contracts.
- **Limits:** its checkpoint was trained on Places2 rather than conservation paintings; one deterministic configuration does not measure model uncertainty.
- Plausible HINT output is not proof of historical authenticity or conservation suitability.

### N12A defence summary

| Required distinction | Short answer |
|---|---|
| Method | Deterministic native-768 HINT inference with exact-mask compositing. |
| Population | 2,620 eligible cases: 2,320 inferences and 300 identity controls. |
| Strongest defensible claim | HINT is a technically validated fourth full-scope benchmark method. |
| Limitation | Places2 training and one configuration do not establish authenticity, suitability, or model-family uncertainty. |

---

## D02 — Portrait, Hand, and Rendered-Skin-Tone Audit

### Q1. What questions does D02 investigate?

- Primary: are damaged hands harder to restore than matched non-hand regions?
- Secondary: do restoration measurements vary with rendered skin lightness?
- It reuses completed N01–N21 evidence and generates no new restorations.

### Q2. How was anatomical eligibility established?

- All 60 portrait-category paintings were screened.
- 91 manually reviewed anatomical annotations and 1,265 anatomy–damage intersections.
- Required at least 256 damaged anatomical pixels and 5% anatomical coverage.
- Final hand study: 45 cases from 20 independent paintings.
- 292 eligible case-region records overall.

### Q3. How was the hand comparison designed?

- Each damaged hand region was matched with a damaged non-hand control from the same case.
- Matching considered damage size, geometry, texture, edges, and boundary location.
- Sparse-pixel and crop-based metrics were used only where valid.
- Painting was the independent unit; Stable Diffusion seeds were collapsed before painting-level inference.

### Q4. What did the hand analysis find?

- All 12 primary model–metric estimates indicated worse hand performance.
- Ten of 12 remained significant after Benjamini–Hochberg correction.
- Stable Diffusion had the lowest observed hand penalty for RGB MAE and CIEDE2000.
- Telea had the lowest observed hand penalty for SSIM.
- There was no universal model winner.

### Q5. What did blinded visual review find?

- 32 candidates were reviewed without exposing model identity.
- 25 contained at least one visible anatomical failure.
- Failures included missing or fused digits, broken contours, wrist discontinuity, and non-anatomical texture.
- Region-average metrics did not capture every visible anatomical defect.

### Q6. What did the skin-tone branch find?

- Used rendered CIELAB lightness, not inferred race or ethnicity.
- Thirty painting profiles and ten context matches were retained.
- Of 24 adjusted associations, zero were clearly positive, three clearly negative, and 21 crossed zero.
- The evidence does not support a general inherent-bias claim.

### Q7. What is the claim and what are the limitations?

- **Claim:** damaged hands were generally harder than matched non-hand controls in this controlled population.
- **Limits:** rendered lightness is confounded by source, period, medium, palette, lighting, and style.
- D02 does not classify identity, race, or ethnicity and cannot establish historical correctness or inherent model bias.
- 99/99 checks passed.

### D02 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Within-case hand-versus-control analysis plus an exploratory rendered-lightness audit. |
| Population | 60 portraits screened; primary hand evidence covers 45 cases from 20 paintings. |
| Strongest defensible claim | Hands were generally harder than matched non-hand controls under the declared metrics. |
| Limitation | The heterogeneous collection cannot support a general racial-bias or inherent-bias claim. |

---

## 31 — Model Report Generation

### Q1. What does N31 do?

- Converts validated N09–N30 evidence into five model-specific reports.
- Filters, joins, formats, and visualizes existing evidence.
- Performs no restoration inference, metric computation, statistical testing, or new ranking.

### Q2. What population is reported?

- 16,404 completed model candidates: 2,620 each for Telea, LaMa, and HINT; 8,520 Stable Diffusion; and 24 completed SDXL.
- Approved report population: 13,879 candidates.
- Primary matched comparison: 10,480 candidates across four full-scope methods.
- 1,025 supported Stable Diffusion uncertainty groups.

### Q3. How are representative examples selected?

- Forty deterministic panels: eight each for Telea, LaMa, and HINT; ten for Stable Diffusion; six for SDXL.
- Quotas cover review categories and prefer distinct paintings.
- Stable Diffusion examples include generic and scratch-aware prompts.
- Panels illustrate the evidence; they are not the statistical population.

### Q4. What findings do the reports preserve?

- Family-balanced order: LaMa, HINT, Telea, Stable Diffusion.
- LaMa led 10/11 quality anchors.
- Telea led the remaining structural anchor.
- SDXL remained a bounded partial evaluation.
- Flags remain review signals, not proof that outputs are wrong.

### Q5. What outputs were created?

- Five self-contained HTML model reports and one five-row report index.
- 75 report sections, 29 analytical views, 40 representative panels, and ten atlases.
- Zero external image dependencies.

### Q6. What validation and runtime evidence exists?

- 346/346 checks passed.
- Nine physical files, all Git-tracked.
- Runtime approximately 1 hour 26 minutes.
- No duplicate Hugging Face release was needed.

### Q7. What is the claim and what are the limitations?

- **Claim:** N31 provides portable and reproducible model-specific reporting without creating new scientific evidence.
- **Limits:** examples are illustrative, runtime is hardware-specific, and SDXL is partial.
- A stale report phrase says “three full-scope methods”; the canonical design has four.

### N31 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Presentation-only synthesis into five self-contained model reports. |
| Population | 13,879 approved report candidates with four full-scope methods and bounded SDXL. |
| Strongest defensible claim | Validated model evidence is exposed consistently without generating new results. |
| Limitation | Illustrative examples, workstation timing, and bounded SDXL do not support universal conclusions. |

---

## 32 — Case and Painting Report Generation

### Q1. What does N32 do?

- Builds case-level, painting-level, and collection-level reports from validated evidence.
- Selects illustrative deep cases by fixed quotas.
- Runs no restoration, metric, statistical test, composite score, or new ranking.

### Q2. What is the reporting population?

- 300 paintings, 2,620 restoration cases, and 13,879 approved candidates.
- Candidates: 2,620 each for Telea, LaMa, and HINT; 5,995 report-eligible Stable Diffusion; and 24 SDXL.
- 3,260 context-prompt candidates are excluded because downstream flag and explanation coverage is incomplete.

### Q3. How do case and painting reports differ?

- Thirty deep-case reports are deterministic illustrations.
- Fixed lanes include lower-risk, flagged, disagreement, uncertainty, prompt sensitivity, extensions, SDXL, and zero controls.
- All 300 painting reports retain every applicable case and candidate in their tables.
- The 30 selected cases cannot estimate population-wide failure prevalence.

### Q4. How is traceability maintained?

- Twenty-five upstream manifests and 41 tabular inputs are bound.
- Indexes store report paths, hashes, evidence paths, and upstream run IDs.
- Sixty-seven traceability roles map report sections to canonical evidence.
- Missing evidence remains explicit instead of being treated as success.

### Q5. What outputs were produced?

- 30 case reports, 300 painting reports, one collection index, and 30 diagnostic grids.
- 331 self-contained HTML reports and 367 physical files.
- 2,132 embedded images and 10,622 visual tiles.

### Q6. What validation and publication evidence exists?

- 5,819/5,819 checks passed.
- Runtime from manifest timestamps: approximately 5 hours 54 minutes.
- Reports and grids: approximately 326.94 MiB, remotely verified on HF diagnostics.
- Compact indexes and manifests remain Git-tracked.

### Q7. What is the claim and what are the limitations?

- **Claim:** N32 provides a complete, auditable reporting layer for the declared 300-painting population.
- **Limits:** deep cases are selected illustrations; uncertainty is not calibrated confidence; SDXL is partial; flags are not expert labels.
- Stale text mentioning ten SDXL cases across five paintings should be read as 24 completed cases across 19 paintings from a 35-case schedule.

### N32 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Presentation-only case, painting, and collection reporting with deterministic case selection. |
| Population | 300 paintings, 2,620 cases, and 13,879 approved candidates. |
| Strongest defensible claim | The declared reporting population is covered by portable, traceable reports. |
| Limitation | Selected deep cases illustrate evidence but cannot estimate prevalence or certify correctness. |

---

## 33 — Final Evaluation Report

### Q1. What method does N33 use?

- Final read-only synthesis of completed upstream evidence.
- Binds 32 upstream manifests and 33 input tables.
- Creates thesis tables, figures, claims, limitations, and a self-contained report.
- Performs no restoration inference, new metric, or new statistical test.

### Q2. What population does the final report describe?

- 300 paintings and 3,425 registered cases.
- 2,620 restoration-eligible cases.
- 10,480 primary four-method candidates.
- 13,879 approved report candidates.
- 1,025 supported Stable Diffusion uncertainty groups.
- 24 completed SDXL candidates.

### Q3. How is quality summarized?

- Eleven separate quality anchors.
- Evidence includes classical, perceptual, feature, texture, colour, seam, spatial, semantic, and structural measurements.
- Metric direction and valid region remain attached to every result.
- No combined quality or trustworthiness score is constructed.

### Q4. What are the main final findings?

- LaMa ranked first on 10/11 quality anchors.
- Telea led the remaining structural anchor.
- Damage size, mask placement, and degradation family changed model behaviour.
- Repeated-seed disagreement, metric disagreement, and flags identify cases requiring review.
- None establishes historical correctness.

### Q5. How does N33 answer the research questions?

- RQ1: complementary region-aware evidence goes beyond basic similarity.
- RQ2: method performance changes with damage condition, painting, and metric.
- RQ3: repeated Stable Diffusion candidates reveal empirical disagreement and stochastic stability.
- Practical output: evidence is exposed through traceable model, case, and painting reports.

### Q6. What outputs and validation evidence exist?

- Fifteen thesis tables containing 352 rows.
- Eighteen thesis figures and six publication figures.
- Nineteen report sections, 49 evidence claims, and 18 limitation records.
- 536/536 checks passed.
- Runtime approximately 17 minutes 19 seconds.
- Thirty-two compact canonical files remain in ordinary Git.

### Q7. What is the claim and what are the limitations?

- **Claim:** under the declared controlled design and metric framework, LaMa has the strongest overall core-model result while method behaviour remains condition- and metric-dependent.
- **Limits:** synthetic damage, incomplete metadata, no expert ratings, hardware-specific runtime, partial SDXL, and no calibrated uncertainty.
- This is not proof of a universally best model, authentic reconstruction, treatment safety, or conservation approval.

### N33 defence summary

| Required distinction | Short answer |
|---|---|
| Method | Read-only thesis-wide synthesis of validated upstream evidence. |
| Population | 300 paintings, 3,425 cases, 2,620 eligible cases, and 13,879 approved candidates. |
| Strongest defensible claim | LaMa leads overall under the declared anchors, while conclusions remain metric- and condition-dependent. |
| Limitation | The controlled digital benchmark cannot prove historical authenticity or physical conservation safety. |
