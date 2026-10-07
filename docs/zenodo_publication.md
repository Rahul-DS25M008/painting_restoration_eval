# Controlled-300 Zenodo publication closeout

## Post-publication reporting corrections

The [2026-10-03 errata](errata/2026-10-03/README.md) corrects population labels,
aggregation descriptions and SDXL scheduled/completed coverage. It supplies
traceable replacement rows while preserving the archived files and all saved
scientific numerical results. Cite the original DOI together with a commit-pinned
errata link when using affected tables. The owner updated the public record's
description on **3 October 2026**; the public API confirms the correction notice
and its link to commit `6d24c42e1cdf47f9b4d0a266cf171fa5dee0c9f2`.

## Published release

Rahul Maddineni's **v1.0.0** research-artifact release was published on **2 October
2026**, with open access, at [Zenodo record 23092185](https://zenodo.org/records/23092185).

- Exact-version DOI: [10.5281/zenodo.23092185](https://doi.org/10.5281/zenodo.23092185).
- All-versions DOI: [10.5281/zenodo.23092184](https://doi.org/10.5281/zenodo.23092184).
- Archived source commit: `2378961a8accb2ecde610ed60428879e8f52a8a8`.
- Machine-readable publication/verification receipt:
  [`zenodo_published_record.json`](../config/publication/zenodo_published_record.json).
- Repository citation metadata: [`CITATION.cff`](../CITATION.cff).

Use the exact-version DOI for the evidence behind the completed thesis. When
using later repository code, also identify that commit. Publication is complete;
the reserved-DOI/draft wording in frozen records describes their earlier dates.

## Download and verification

The record contains **15 files, totalling 40,565,606,666 bytes**:

1. Eight binary parts, `controlled-300-v1.0.0-research-artifacts.zip.001` through
   `.zip.008`. They are parts of **one ZIP64 archive**, not independent ZIPs.
2. Seven companions: `REASSEMBLE.txt`, `SPLIT_MANIFEST.json`,
   `RELEASE_MANIFEST.json`, `RELEASE_README.txt`, `RELEASE_ADDENDUM.txt`,
   `RIGHTS_AND_REUSE_NOTICE.txt`, and `SHA256SUMS.txt`.

Download all eight parts and follow `REASSEMBLE.txt`. Concatenation in numbered
order recreates the unchanged **40,522,491,399-byte** original ZIP. Verify its
SHA-256 before extraction:

```text
3ee4f9266477213521cdd4f877c71140360125fa9d0f5badb7fb1712c701a562
```

The ZIP contains 155,563 members: 155,561 selected source files and two generated
release-context files. This is the complete selected current-study archive,
not merely the N36 review package. Environments, model weights, private working
drafts, historical pilot working trees and duplicate HF transport bundles are
not included. Their exclusion does not mean the experiments were independently
reproduced.

The full ZIP and split parts were read back locally and checked. On
2026-10-02, the **unauthenticated public record API** returned all 15 expected
filenames, byte sizes and MD5 values, matching the verified local upload set.
The receipt records the check time and local SHA-256 values. This was a remote
metadata/checksum comparison, **not a fresh 40.6 GB download** or a scientific
validation rerun. The script's complete-file checks do not imply partial
upload resumption: a failed individual part must be uploaded again.

## Recovery and frozen provenance

During archive preparation, 23 local diagnostic PNGs were restored byte-for-byte
from previously published, checksum-pinned evidence. They were not regenerated
experiments. The damaged copies and recovery logs remain local and are not
published. The recovered ZIP was completed and verified without rebuilding all
earlier entries. Splitting then changed only its delivery format.

The post-publication README, citation and dashboard updates are a later
administrative layer. **Do not rewrite notebooks, producer manifests, N35/N36
outputs, publication bundles, screenshot-based supervisor PDFs, or the archived
ZIP to remove their historical "Zenodo planned" wording.** The Research Archive
reads the new receipt separately from its frozen N34 evidence partitions. Only
the existing Zenodo plaque lettering and popup change; its hitbox and all other
room layouts remain the same. Historical screenshots and supervisor PDFs are
explained by the [supervisor status note](supervisor/README.md).

## Rights and reuse

MIT covers the author's original software; CC BY 4.0 covers original research
material only to the extent of rights held. Existing third-party rights and
public-domain status remain unchanged. The published notes and
`RIGHTS_AND_REUSE_NOTICE.txt` exclude third-party characters/franchise elements,
including decorative Genshin Impact and Dune fan artwork and embedded copies,
from those grants. No separate permission for those franchise elements was
obtained; redistribution permission remains unresolved. The owner's publication
decision and verified checksums are **not blanket rights clearance**.

### Genshin Impact policy guidance — 2026-10-07

On 7 October 2026, the owner reported that Genshin Impact support referred him
to the [Legal FAQ](https://www.hoyolab.com/article/143107) and the
[Overseas Fan-Made Merchandising Guide](https://www.hoyolab.com/article/381519),
and supplied copies of both articles for review. This date records the review,
not a verified date of the support email. The copies are the basis for the
assessment; the full email and any project-specific assurances were not supplied.

Section 2 of the supplied Legal FAQ says non-commercial personal use is not
prohibited, requires a COGNOSPHERE legal declaration, and expressly does not
transfer rights or confer legal approval. The merchandising guide primarily
addresses physical products; its quantity thresholds are not treated as website
visitor/download limits or as project-specific website authorization. Neither
supplied text explicitly resolves the treatment of AI-generated decorations.

For Genshin Impact decorative elements: **© All rights reserved by COGNOSPHERE.
Other properties belong to their respective owners.** The artwork is unofficial;
this independent project is not affiliated with, sponsored by, or endorsed by
COGNOSPHERE or HoYoverse. These elements remain excluded from the author's
MIT/CC BY grants, including embedded copies. This does not change the separate
rights assessment for Dune or other third-party material.

The owner approved documentation-only attribution: a small readable notice in
the repository README's Licensing section, the project LICENSE, and the
decorative-portrait README. No notice was added to the dashboard or video;
no image, room layout, runtime behavior or scientific evidence was changed.
Consequently, this update is not a claim that documentation-only attribution
satisfies every policy requirement to place a notice on the works themselves.
The portrait README checksum is reconciled separately, retaining its prior value.

**Zenodo action pending:** append the paragraph below to the existing record's
description, preserving the prior description, reporting errata, licence fields,
DOI, version, files and checksums. Do not create a new version or rebuild/re-upload
the archive. This metadata clarification does not insert notices into archived
files. Once published, the metadata update can be verified separately; it is not
recorded here as completed in advance.

> Genshin Impact decorative elements are unofficial fan artwork. © All rights
> reserved by COGNOSPHERE. Other properties belong to their respective owners.
> This independent research project is not affiliated with, sponsored by, or
> endorsed by COGNOSPHERE or HoYoverse. Genshin Impact support referred the author
> to the [Legal FAQ](https://www.hoyolab.com/article/143107) and
> [Overseas Fan-Made Merchandising Guide](https://www.hoyolab.com/article/381519).
> These references provide general policy guidance, not project-specific
> permission or blanket redistribution clearance. Third-party characters and
> franchise elements remain excluded from the author's MIT/CC BY licence grants;
> the existing rights qualifications remain in force. This clarification changes
> record metadata only, not the archived files or their checksums.

## Maintenance boundary

### Reporting errata and validation follow-up — 2026-10-03

The [post-publication errata](errata/2026-10-03/README.md) and its
[validation record](errata/2026-10-03/validation.md) are separate GitHub corrections
to reporting metadata and regression checks. They do not replace or alter any of
the 15 Zenodo files. **The description update is complete.** On 2026-10-03,
the unauthenticated public API confirmed the correction notice and the exact
[commit-pinned errata link](https://github.com/Rahul-DS25M008/painting_restoration_eval/blob/6d24c42e1cdf47f9b4d0a266cf171fa5dee0c9f2/docs/errata/2026-10-03/README.md).
GitHub `main` matched that commit, and the linked document returned HTTP 200.
Zenodo records the metadata update at `2026-10-03T01:16:39.048753Z`.

The exact-version DOI and `v1.0.0` remain unchanged. All 15 public filenames,
byte sizes and MD5 values still match the original publication receipt. This
was a public metadata comparison, not another payload download or scientific
rerun. The original receipt remains unchanged, preserving its earlier check
date and the dashboard's approved freeze. No further Zenodo action is pending
for this reporting-correction closeout.

No new HF upload, model run, archive rebuild or re-upload is needed for this
closeout. GitHub contains the compact publication receipt and updated source/docs;
the original ZIP, eight parts, credentials and temporary recovery files stay
outside Git under ignored `.codex_tmp/`. No access token belongs in public URLs.
The retired builder is guarded against rebuilding the published version, and
the uploader refuses a submitted record. Any future artifact revision requires
a separately approved version and rights review.

## Closeout checks

The focused offline run passed 23 archive/publication-tool tests, 17 Research
Archive tests, and three Archive-controller JavaScript tests (43 total). A local
browser fixture confirmed that the existing Zenodo plaque retains its frame,
seal and location and opens the published-release popup in place with the clean
DOI/record links. This is a local presentation check, not a new live-deployment
certification. The canonical project inventory is refreshed after these edits;
its compact `outputs/inventory/inventory_run.json` is the committed scan receipt.
