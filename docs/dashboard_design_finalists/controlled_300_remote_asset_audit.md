# Controlled-300 Remote Asset Audit

**Status:** Pre-N34 Step 3 complete on 2026-09-28

**Audited Git revision:** `503cd8bbc7afa4527069ad4c9931725ffb88ca4b`

**Scope:** GitHub, Hugging Face Candidates, Hugging Face Diagnostics, indexed
bundle releases, the N32 report package, checksums, and missing-asset behaviour

**Next gate:** Step 4 runtime policy for lazy loading, caching, startup limits,
responsive behaviour, and remote fallbacks

## Decision

The approved Controlled-300 dashboard evidence is publicly retrievable without
re-uploading the corpus. The remote integrity gate passes, subject to the
binding routing rules below. N34 must compile a new immutable asset manifest;
it must not copy the mutable `main` URLs preserved in the historical
publication registry.

The local output tree remains canonical. A remote object is a verified delivery
copy of that exact local artifact, not a replacement scientific source.

## What was verified

- Local Git `HEAD`, `origin/main`, and public GitHub all resolved to the audited
  full commit above.
- All 2,653 rows in `external_artifact_publication.csv` have a valid local path,
  exact byte size, SHA-256, `published_verified` status, verification flag,
  immutable publication commit URL, and unique local and remote identity.
- A full local re-hash reproduced all 2,653 recorded SHA-256 values. The
  population is 2.785 GiB across 2,644 candidate objects and nine diagnostic
  tables, spanning 62 pinned Hugging Face revisions.
- Representative immutable public reads from both Hugging Face repositories
  reproduced exact bytes and SHA-256 values. All nine diagnostic bulk tables
  returned the recorded sizes at their pinned revisions.
- The six indexed bundle releases—N16, N17, N19, N20, N22 Candidates and N22
  Diagnostics—retain `full_remote_verified` records. Their pinned catalogues,
  per-painting indexes, bundle/member checksums, and selected public members
  were rechecked.
- The N32 report package exposes 331 self-contained reports and 30 selected-case
  grids at its pinned diagnostics revision; an exact p018 case report was
  re-read and matched locally.
- Representative ordinary Git blobs and Git LFS payloads were retrieved at the
  audited Git commit and matched their expected full bytes.
- Deliberately nonexistent GitHub and Hugging Face paths returned HTTP 404.

This is a low-request live revalidation layered on the existing complete
publication records. It avoids re-downloading tens of gigabytes while retaining
the previous full-object verification as the authoritative release evidence.

## Immutable remote routing contract

| Storage class | Required URL form | Integrity rule | Important boundary |
|---|---|---|---|
| Ordinary Git blob | `https://raw.githubusercontent.com/Rahul-DS25M008/painting_restoration_eval/{full_git_sha}/{path}` | Verify downloaded byte count and SHA-256 recorded by N34 | Never use a branch name in a dashboard asset URL. |
| Git LFS payload | `https://media.githubusercontent.com/media/Rahul-DS25M008/painting_restoration_eval/{full_git_sha}/{path}` | Verify payload byte count and SHA-256; the media `ETag` may provide the same object hash | The GitHub raw endpoint returns the small LFS pointer, not the PNG/CSV payload. |
| HF individual object | `https://huggingface.co/datasets/{repo_id}/resolve/{full_revision}/{remote_path}` | Derive `{full_revision}` from `publication_commit_url`; verify size and SHA-256 | The registry's historical `revision=main` and `remote_uri=.../resolve/main/...` are aliases and are forbidden in N34. |
| HF indexed bundle | Pinned release record → catalogue → painting index → named bundle/member | Verify catalogue, index, bundle and member size/SHA before decoding | Fetch only the bundle needed by the selected case; never download a producer's full release at startup. |
| HF N32 report package | Pinned N32 revision plus exact report/grid path | Verify the complete HTML/PNG bytes before serving or embedding | Reports are direct retrieval units, not ZIP members. |

Git transport must be determined from the **committed object**, not from the
filename or current `.gitattributes`. N34 must classify each Git artifact as
`git_blob` or `git_lfs` by inspecting the committed bytes for the Git LFS pointer
signature and, for LFS, preserving the pointer OID and expected payload size.
This matters because older committed files can be ordinary Git blobs even when
their extensions are now covered by an LFS rule.

### Representative GitHub byte checks

These revision-pinned public payloads were checked end to end. Checksums are
for portable committed/remote bytes; Windows working-tree line-ending
conversion is not an acceptable manifest checksum source.

| Artifact | Transport | Bytes | SHA-256 |
|---|---|---:|---|
| N01 `data/artworks.csv` | `git_lfs` | 280,991 | `be5c78657a7b6cdefb432024131b61586c275edf139ce963bc2169a518ca4469` |
| N02 `images/clean/p001.png` | `git_lfs` | 723,881 | `b5852f0337c8342a1a70268f9e9f682534177581d238713f67bf28e0033482a2` |
| N03 p001 mixed mask | `git_lfs` | 8,042 | `f6032e27029707fbff5f4d3de365149466fe281b43cdc79016f4f88cb5c94eee` |
| N04 p018 mixed damaged image | `git_lfs` | 502,168 | `bb2cf0fa259c7fe58a959ad95f140bd37c64ecdf2c9f8c3b62970e38a9e14a98` |
| N05 p018 20% damaged image | `git_lfs` | 430,442 | `d71b69acdb6979968f55973cdfb9be5a501626f94616ac99e21d58faa47d40d0` |
| N08 `case_registry.csv` | `git_lfs` | 1,734,032 | `d57a7be1afb23d935c8c809fb0e6744c7ccb73dd2231c685aa137fab82efb039` |
| N10 p018 LaMa restoration | `git_lfs` | 536,639 | `b10aef3dc92f0da6de0ca87a87092b5c561c0a8d75c1b5e5dca163bb04daf5ca` |
| N11 p018 Stable Diffusion restoration | `git_lfs` | 547,697 | `aa7b83315cc9663aab8570c7c979bd5ea6fa3878a5469449d3426746f236a411` |
| Failure-taxonomy YAML | `git_blob` | 29,073 | `666a6e20a5f9f89c15ef42492d2a056105f4a86c8113b127f011ad22f3432698` |
| N29 retrieval panel 01 | `git_blob` | 1,983,301 | `c006ab46251225f08bde2a309053d16dadf9183d4170a7bd97ce2482b77a8da1` |
| N31 LaMa report | `git_blob` | 2,634,126 | `0ee00e76a6406effca6366a1d1e341c9a2b9be19065f7001b4f3a7af574904e9` |
| N33 final evaluation report | `git_blob` | 15,302,443 | `d26757e5583675d38948c6b55b3ac25383d36d3e65722adba11602891ca78698` |
| D01 selection decision | `git_blob` | 2,442 | `610f17f0fd86d5b648b361a036548f8dca032b7010ee94b7b48aacc1c7a19bdf` |
| D02 manual anatomy review | `git_lfs` | 32,506 | `f96b6638447fd0f8122b4f856bbc898f9a2bccbe2e93a38bec2e572d914d8272` |
| D02 hand-versus-control figure | `git_lfs` | 123,771 | `24b3c52e5240fa20d57c27109fdcc4e390f47fc1e63e703d365b55814754d849` |
| External publication registry | `git_blob` | 2,484,673 | `45b53149ac129c5aec5eb7737c2af7b8b29be0d91208010e0916d442a7cb5210` |

## Verified bundle releases

| Producer | Repository | Pinned revision | Assets | Bundles | Remote objects | Verified bytes |
|---|---|---|---:|---:|---:|---:|
| N16 difference/spatial diagnostics | Diagnostics | `8c22aa62c5be60d8a15c9c00d9bc9a6f81557b79` | 76,034 | 333 | 641 | 2,625,210,541 |
| N17 local consistency | Diagnostics | `ceac6a5aa67fe2a0f8c840c46f22306e7f606749` | 27,926 | 360 | 669 | 5,622,373,385 |
| N19 uncertainty/spatial explanations | Diagnostics | `e080704d57d2a10ebe09d0395f348b9da85ea8f7` | 2,475 | 300 | 609 | 1,329,281,895 |
| N20 semantic/structural consistency | Diagnostics | `8f849ea89e0fa6cabf309481d63c44bb3878edc3` | 9,304 | 513 | 823 | 14,066,563,594 |
| N22 diffusion extension candidates | Candidates | `2d4ac6312c9b68db8377da0f591006eb07dc905a` | 735 | 35 | 77 | 527,754,743 |
| N22 diffusion extension diagnostics | Diagnostics | `6c3ee0b232b2a555d401142040bf337b5e54ab33` | 245 | 35 | 80 | 407,378,583 |

The N16–N20 p018 indexes were checked for their intended map families. The N22
p018 index exposes all three additional seed candidates and the corresponding
uncertainty overlay. The existing `RemoteBundleReader` rejects mutable
revisions, validates index/bundle/member checksums, uses safe member paths and
does not silently read a local source file when a remote object fails.

## N32 report package

| Field | Verified value |
|---|---|
| Repository | `RahulMaddineni264/painting-restoration-eval-diagnostics` |
| Revision | `c33bbd87e65fe96f9a81c1c794fd4a70f7226874` |
| Prefix | `report_packages/v1/controlled_300/32_case_and_painting_report_generation/run_0d4ae193602944dda511bf54199105b1` |
| Reports | 331 |
| Selected-case grids | 30 |
| Total objects | 361 |
| Verified bytes | 342,821,662 |

## Required missing-asset and integrity behaviour

For every requested asset, N34 must use this order:

1. resolve the exact active painting/case/candidate/region/seed identity;
2. find the corresponding manifest row and immutable transport route;
3. retrieve or reuse only the exact object or bounded bundle;
4. verify expected size and SHA-256 before display; and
5. render the component only after verification succeeds.

If the identity has no applicable artifact, the URL is absent, the response is
404, a request times out after the approved retry budget, or size/checksum
verification fails, the component must show an explicit unavailable state.
That state records the requested identity, evidence type and reason. It must
never silently substitute:

- another painting, candidate, method, seed, prompt or damage condition;
- a neighbouring report or approximate crop;
- a mockup image or stale temporary work file; or
- an unverified local file that happens to share a filename.

Checksum failure is an integrity error, not an ordinary applicability state.
The UI may retry through the approved Step 4 policy, but it must not display the
failed bytes.

## HTML and browser boundary

GitHub raw/media endpoints can return HTML as `text/plain`. N34 must not depend
on a raw URL being executed as a page. HTML evidence should be displayed from
the packaged application, through a verified download/open action, or inside a
deliberately sandboxed component using already verified bytes. External links
must still point to the immutable source record.

## Corrections made by this gate

`config/publication/external_storage.yaml` now:

- records final N19, N20 and split N22 bundle releases and revisions;
- forbids mutable revisions for dashboard resolution;
- replaces `resolve/main` bases with full-revision templates;
- records that the registry's immutable revision comes from
  `publication_commit_url`; and
- marks the historical missing `external_artifact_publication_run.json` path as
  legacy instead of declaring it a current file.

## Step 4 handoff

Step 3 certifies identity and availability; it does not yet choose runtime
budgets. Step 4 must approve:

- what is packaged locally versus fetched lazily;
- cache scope, byte limit, eviction and invalidation;
- startup network and memory ceilings;
- timeout, retry and offline behaviour;
- responsive image/rendition choices; and
- the exact user-facing unavailable/error states.

Only after that decision should the final N34 implementation contract and asset
manifest schema be frozen.
