# Controlled-300 Dashboard Runtime Loading Contract

**Status:** Pre-N34 Step 4 complete on 2026-09-28

**Applies to:** the eight-room Painting Restoration Evidence Museum, the D02
Focused Portrait Review subroute, Notebook 34 packaging, the Controlled-300
Streamlit implementation, and Notebook 35 deployment validation

**Evidence authority:**
[`controlled_300_producer_artifact_map.md`](controlled_300_producer_artifact_map.md)
and
[`controlled_300_remote_asset_audit.md`](controlled_300_remote_asset_audit.md)

**Next gate:** Step 5 final N34 implementation contract and asset-manifest
schema

## Decision

The application will use a **local-first catalogue with exact on-demand
evidence**. It will not clone the output corpus, load large scientific tables,
download bundle collections, or contact Hugging Face during startup.

The deployment has three runtime tiers:

1. **Bootstrap:** compact room text, headline findings, selector indexes,
   availability records, provenance, and small registered web renditions needed
   for the Exhibition Foyer. This tier is shipped with the app and is sufficient
   to explain the thesis while remote services are unavailable.
2. **Room partitions:** compact, column-pruned tables and registered web
   renditions loaded only for the active room. Hidden rooms, drawers, layers and
   selectors do not execute or fetch evidence.
3. **Exact remote evidence:** immutable GitHub/Hugging Face objects, indexed
   bundle members, and full reports fetched only when the visitor selects the
   exact identity and requests the corresponding layer or record.

No restoration model, feature encoder, scientific metric, statistical test, or
threshold fitting runs in the deployed application. The app only presents
validated saved evidence and N34 display derivatives with registered lineage.

## Why this design is necessary

Streamlit reruns an application after interactions, and ordinary tabs compute
all their content unless lazy state tracking is used. Streamlit 1.56 supports
fragments for independent reruns and dynamic containers for conditional
rendering. Its data cache returns copies to callers, so large cached dataframes
or image payloads can multiply memory use. The implementation therefore keeps
large bytes out of `st.cache_data`, avoids expensive content in ordinary hidden
tabs, and keeps session state to identifiers rather than data objects.

Streamlit Community Cloud currently documents approximate per-app resources of
690 MB–2.7 GB memory, up to two CPU cores, and up to 50 GB storage, while noting
that limits can change. Apps also hibernate after 12 hours without traffic.
The limits below deliberately leave substantial memory and disk headroom.

Official references:

- [Community Cloud app resources and hibernation](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)
- [Streamlit 1.56 data-cache semantics](https://docs.streamlit.io/1.56.0/develop/api-reference/caching-and-state/st.cache_data)
- [Streamlit 1.56 fragments](https://docs.streamlit.io/1.56.0/develop/api-reference/execution-flow/st.fragment)
- [Streamlit image sizing](https://docs.streamlit.io/1.56.0/develop/api-reference/media/st.image)
- [Static-file serving boundaries](https://docs.streamlit.io/develop/concepts/configuration/serving-static-files)

## Measured repository baseline

The frozen Controlled-50 N34 package contains 19 files and is 34.71 MiB. Its 15
eagerly loaded dataframes occupy about 90.8 MiB of deep pandas memory. On the
thesis laptop, its existing loader read every table and index in about 1.22
seconds and increased process RSS by about 26.5 MiB. The historical N35 cold
Overview render took about 4.13 seconds. That implementation is not the
Controlled-300 target because it eagerly loads the entire package, scans large
producer tables for some case metrics, and evaluates hidden `st.tabs` content.

The remotely verified Controlled-300 bundles are already bounded by the
repository's 32 MiB bundle cap. Observed staged releases have these sizes:

| Release | Median bundle | 90th percentile | Maximum |
|---|---:|---:|---:|
| N16 | 3.01 MiB | 26.38 MiB | 29.36 MiB |
| N17 | 7.44 MiB | 30.87 MiB | 31.26 MiB |
| N19 | 3.36 MiB | 7.64 MiB | 13.38 MiB |
| N20 | 26.65 MiB | 31.54 MiB | 31.83 MiB |
| N22 candidates | 14.31 MiB | 18.84 MiB | 20.49 MiB |
| N22 diagnostics | 9.55 MiB | 12.53 MiB | 12.86 MiB |

Every measured bundle stays below the implemented 32 MiB bundle ceiling. N32's
331 reports and 30 selected-case grids total about 326.94 MiB, but the largest
single report is about 1.70 MiB. N33's self-contained report is about 14.6 MiB
and therefore remains an explicit open/download action. These observations
support one 32 MiB bundle per foreground action and a 34 MiB total transfer
guard for an exact diagnostic action, including its small catalogue/index
overhead.

## Quantitative runtime budgets

These are N34/N35 acceptance gates, not universal performance claims.

| Budget | Required limit |
|---|---:|
| Boot-critical compressed data | target ≤ 8 MiB; hard gate ≤ 12 MiB |
| Complete local N34 evidence/index package, excluding code and dependencies | target ≤ 32 MiB; hard gate ≤ 64 MiB |
| Eagerly materialized bootstrap dataframe memory | ≤ 64 MiB deep memory |
| Bootstrap application-data RSS increase on the thesis laptop | ≤ 128 MiB |
| Total process RSS at Foyer-ready state | target ≤ 384 MiB; hard gate ≤ 512 MiB |
| Total process RSS during the representative heaviest single-session route | ≤ 512 MiB |
| Foyer readiness after the Python process starts, excluding platform wake/build | p95 target ≤ 3 s; hard gate ≤ 5 s |
| Warm room-navigation rerun | p95 ≤ 1.5 s |
| External startup requests | exactly 0 |
| Routine room transition using registered renditions | ≤ 4 MiB remote transfer |
| Exact diagnostic action | one new object/bundle; ≤ 32 MiB payload and ≤ 34 MiB total transfer |
| Remote concurrency | ≤ 2 requests globally; ≤ 1 bundle request |
| Session remote-transfer guard | warn at 128 MiB; pause new uncached loads at 256 MiB until explicit continuation |
| Shared verified bundle/object disk cache | 512 MiB maximum; evict to 384 MiB |
| Decoded-image memory cache | ≤ 64 MiB and ≤ 16 images |
| Per-room compact partition | ≤ 5 MiB serialized and ≤ 25 MiB measured in-memory |
| Simultaneously rendered full evidence images | ≤ 6 |
| Session-state payload | identifiers/booleans only; target ≤ 64 KiB per session |

If a future deployment receives different Community Cloud resources, N35 may
record the observed platform allocation but may not silently raise these
application budgets. A change requires an explicit contract amendment.

## Loading triggers by room

| Room | Local at entry | Remote only after explicit action |
|---|---|---|
| Exhibition Foyer | Introduction, collection counts, room map, route previews and registered thumbnails | Nothing automatically; Guided Tour loads each later stop only when reached |
| Study Design | Population summaries, study choices, focused-review summary and small examples | Full example image or linked report when opened |
| Metric Framework | Metric definitions, availability, how-to-read text and opening-case web renditions | Selected full-resolution map or exact metric record after lens/region confirmation |
| Model Gallery | Method descriptions, availability and opening-case web renditions | Exact full-resolution restoration or model report selected by the visitor |
| Stability Lab | Compact damage/mask/seed/degradation summaries and opening trajectory thumbnails | One selected diagnostic family, bundle or report at a time |
| Trustworthiness | Flag definitions, threshold explanation, compact candidate finder and opening-case renditions | Selected candidate layers, exact threshold evidence, report, or D02 mini room evidence |
| Case Explorer | Search/filter indexes and availability states | `Load this case` fetches the exact selected base views; each diagnostic layer loads separately |
| Research Archive | Provenance/publication catalogues, limitation drawers, checksums and report metadata | A report is fetched only after `Open` or `Prepare download`; large evidence bundles are never loaded merely by browsing the archive |

Selector changes must not trigger repeated full downloads while a visitor is
still choosing a painting, case, method, seed, region or layer. Remote-heavy
views use a final `Load evidence`/`Open record` action. The selected identity is
shown before the request begins.

## Cache contract

### Small trusted data

- Use `st.cache_data` only for trusted, immutable, serializable bootstrap and
  room partitions.
- The release/configuration identity is part of every cache key.
- Bootstrap cache: one entry, no persistent disk copy.
- Room/selector partitions: `max_entries=16`, `ttl=3600` seconds, global scope.
- Case-specific compact metric views: `max_entries=32`, `ttl=3600` seconds.
- Do not cache gigabyte CSVs, complete map manifests, entire report collections,
  ZIP bytes, decoded full-image arrays, or arbitrary user-provided data through
  `st.cache_data`.
- Runtime code must never hash or scan a producer-scale CSV to answer an
  interaction. N34 produces compact, display-ready, provenance-preserving
  partitions containing the displayed values plus exact producer row IDs and
  source checksums.

### Remote objects and bundles

- Use the repository's checksum-validating file cache, not `st.cache_data`, for
  remote payloads.
- The shared cache key includes transport, provider, repository, full 40-hex
  revision, path, expected size and expected SHA-256. A branch, tag, `main` or
  abbreviated revision is invalid.
- Keep a process-shared 512 MiB least-recently-used limit and evict to 384 MiB.
  Cache hits recheck size and SHA-256 before use. Immutable verified bytes have
  no time-based expiry; a new manifest/revision namespace invalidates them.
- Keep decoded images in a separate byte-aware in-memory LRU capped at 64 MiB
  and 16 entries. Never put binary payloads in session state.
- Partial files are atomically renamed only after verification. Failed partials
  are deleted. Stale `.partial` or `.lock` files older than two minutes are
  removed during reader initialization.
- Catalogue, painting-index, bundle and member checksums all derive from a
  trusted N34 root manifest. A schema-only catalogue check is insufficient.
- Every streamed response is bounded to its expected size plus one byte. Bundle
  members are limited to 8 MiB encoded and 16 million decoded pixels unless an
  explicitly reviewed manifest role defines a smaller limit.
- A shared reader/resource must be thread-safe. Use file locks for downloads and
  a bounded global semaphore of two remote requests; each visitor interaction
  starts at most one remote transfer.
- No background prefetch and no whole-release warmup are allowed.
- An immutable 404 may be negatively cached for the current session. Timeouts,
  rate limits and 5xx failures must not be negative-cached.

### Session state

Session state stores one canonical selection identity: room, painting ID, case
ID, candidate ID, model, optional seed/prompt, metric, region, evidence layer,
return room and whether the visitor explicitly requested a load. It must not
store DataFrames, report bytes, ZIP members, PIL images or NumPy arrays. If a
child option is unavailable, the requested identity remains visible with the
reason; the app must never silently select the first available neighbour.

## Request, retry and error policy

All remote reads are immutable, idempotent GET requests.

| Condition | Behaviour |
|---|---|
| Successful response | Stream to a partial file, verify size and SHA-256, atomically promote, then render |
| HTTP 404 | No retry; show `Not published for this exact evidence identity` |
| HTTP 401/403 | No automatic retry; show `Remote access unavailable` and source provenance |
| HTTP 408, 429, 500, 502, 503, 504 or network timeout/reset | At most two total attempts; honour `Retry-After` capped at 15 s, otherwise use approximately 1 s jittered backoff |
| Index/catalogue mismatch | Stop immediately; show integrity error and do not fetch the named member |
| Size/SHA mismatch or invalid ZIP/member | Delete failed bytes and allow one clean re-download; a second mismatch is a terminal integrity error and failed bytes are never displayed |
| Offline/unreachable after retry budget | Keep local room context visible and offer `Retry exact evidence` |

Connections use a five-second timeout. Small index/direct-object attempts use a
15-second read timeout; bundle attempts use a 45-second read timeout. One
foreground operation has a 60-second overall deadline. A visible status element
names the evidence being loaded; errors never expose tokens, local absolute
paths or raw tracebacks.

The renderer uses distinct machine-readable and plain-language states:
`not_applicable`, `not_published`, `not_found`, `offline_uncached`, `timeout`,
`rate_limited`, `integrity_error` and `decode_error`. Only transient network
states expose Retry.

There is no identity fallback. A packaged web rendition may stand in for its
own full-resolution source only when its N34 manifest records the same producer
identity, derivation and checksum lineage, and it is labelled as a display
rendition. It cannot stand in for another candidate or evidence type.

## Streamlit execution policy

- Keep Streamlit pinned to the explicitly tested version. N34/N35 must not rely
  on APIs introduced after that version without updating the pin and tests.
- Use room functions or `st.navigation` so only the active room renders.
- Use `st.fragment` for independent case/layer controls where it avoids a full
  museum rerun. Do not use timed automatic reruns.
- Hidden expensive content must be genuinely conditional. With Streamlit 1.56,
  ordinary tabs and closed expanders still execute their contents; use a
  segmented control/radio or dynamic container state and an explicit condition
  before fetching bytes.
- Forms group multi-field case searches so intermediate selector changes do not
  cause remote loads.
- Query parameters may encode a validated room/case/candidate/layer deep link,
  but they never bypass applicability or checksum checks.
- Fonts are packaged with the application or use a system stack. The final app
  must not make an uncontrolled font/CDN request during startup.
- Report bytes are not read merely to render a download button. `Open verified
  report` or `Prepare download` is the retrieval action.

## Responsive and accessible evidence

N34 creates registered display renditions rather than resizing the whole corpus
at runtime:

- `thumb`: 320 px long edge for routes, cards and search results; target
  ≤ 75 KiB and hard gate ≤ 125 KiB;
- `standard`: 640 px long edge for primary painting/restoration views; target
  ≤ 250 KiB and hard gate ≤ 400 KiB for colour images;
- `diagnostic_preview`: 320 px or 640 px lossless rendition; target ≤ 500 KiB
  and hard gate ≤ 750 KiB; and
- `exact`: the verified native asset, normally 768 px for preprocessed
  paintings, fetched only on explicit inspection.

Photographic painting renditions may use quality-controlled WebP/JPEG; masks,
line work, labels, heatmaps and difference maps remain lossless PNG. Use
320/640/native responsive sources, never upscale a scientific image, and load
only the visible image plus the selected route preview. Every rendition records
source path, source SHA-256, transformation, output checksum, dimensions and
role. A `View exact image` action remains available where the exact source is
remotely published.

Layout breakpoints are functional, not separate scientific views:

- desktop (`≥1200 px`): approved room composition and multi-frame comparison;
- tablet (`768–1199 px`): two-column evidence with controls above the active
  view; and
- mobile (`<768 px`): one-column reading order, simplified room map, one primary
  comparison frame at a time and no horizontal dependence.

Use `width="stretch"` or bounded integer widths rather than the deprecated
`use_container_width`. Preserve aspect ratio, do not crop away a damage region,
provide useful captions/alternative text, support keyboard focus, and preserve
readable contrast. Hover-only explanations must also be available by focus or
tap.

## Offline and degraded mode

The Foyer, route map, thesis introduction, room descriptions, headline
population counts, metric glossary, model descriptions, study boundaries,
limitations, publication catalogue and provenance metadata remain usable from
the packaged bootstrap without network access.

Remote-dependent components retain their place in the room and show:

- the exact requested identity;
- whether the evidence is not applicable, not published, temporarily
  unreachable, or failed integrity verification;
- the immutable source/provenance record when available; and
- a retry action only for transient failures.

Verified cached bytes may remain visible while offline only when their active
manifest identity, expected size and checksum still match. The app must not
switch to the local development output tree in deployment.
Development mode may use local files only through an explicit, visibly labelled
resolver selected before startup and covered by separate tests.

## N35 validation matrix

Notebook 35 must exercise at least:

1. zero-network Foyer startup and the quantitative disk, dataframe-memory, RSS
   and latency budgets;
2. cold and warm reads for one Git blob, one Git LFS payload, one HF individual
   object, one bundle member from each of N16/N17/N19/N20, both N22 tiers, and
   one N32 report;
3. cache hit, eviction from 512 MiB down to 384 MiB, concurrent same-object
   lock, stale-partial cleanup, corrupt-cache replacement and decoded-image
   cache limits;
4. 404, timeout, 429 with `Retry-After`, 503, size mismatch, checksum mismatch,
   invalid ZIP and missing-member behaviour;
5. exact-identity preservation across all eight rooms and D02;
6. no network work for hidden rooms, inactive layers, closed drawers or
   unsubmitted selector forms;
7. desktop, tablet and mobile layout checks, including keyboard/tap equivalents
   for hover interactions;
8. deep-link round-trip, cross-room identity preservation and rejection of
   unsupported identities;
9. proof that no runtime route scans or hashes a full producer-scale CSV, and
   that reports load only after an explicit action; and
10. instrumentation showing request count, downloaded bytes, cache bytes, load
   duration and user-visible outcome without exposing secrets.

Step 4 is complete only as a runtime decision. Step 5 must now translate these
rules and the Step 2 producer bindings into the final N34 schema, required
derivations, validators and exact output contract.
