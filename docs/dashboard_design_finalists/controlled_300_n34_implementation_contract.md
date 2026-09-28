# Controlled-300 Notebook 34 Implementation Contract

**Status:** Implemented and validated by Notebook 34 on 2026-09-28

**Applies to:** Notebook 34, its configuration and helper module, the
Controlled-300 dashboard package, the future Streamlit implementation, and the
Controlled-300 Notebook 35 validation run

**Package boundary:** `dashboard_package.v2`

**Validated release:** `release_c5edf0d0ec99affbfa403726` from run
`run_1e831de6e27f9ead0147bb30`

**Next step:** implement the Controlled-300 Streamlit interface against the
promoted package, then rerun Notebook 35 validation

## Decision in plain language

Notebook 34 will build a small, verified website package from the completed
scientific outputs. It will not rerun a restoration model, recompute a metric,
or copy the complete evidence corpus into the deployed application.

The package contains:

1. enough local material to open the museum and explain the thesis with no
   network connection;
2. one compact data partition for each active room;
3. small registered image renditions for navigation and opening examples;
4. exact indexes that identify where a selected image, map or report lives; and
5. checksums and provenance connecting every displayed claim back to its
   producer.

Exact large evidence remains in its verified GitHub or Hugging Face location
and is loaded only after the visitor asks for it.

## Governing authorities

Notebook 34 must satisfy all four earlier gates:

1. [`controlled_300_page_contracts.md`](controlled_300_page_contracts.md) —
   what each room explains and how identities move between rooms;
2. [`controlled_300_producer_artifact_map.md`](controlled_300_producer_artifact_map.md)
   — the exact upstream source for each image, value, report and conclusion;
3. [`controlled_300_remote_asset_audit.md`](controlled_300_remote_asset_audit.md)
   — immutable GitHub/Hugging Face routing and checksum rules; and
4. [`controlled_300_runtime_loading_contract.md`](controlled_300_runtime_loading_contract.md)
   — startup, caching, retry, responsive and degraded-mode limits.

If the historical N34 notebook, application or configuration conflicts with
these authorities, this Controlled-300 contract wins. The old
`dashboard_package.v1` remains a frozen pilot record and must not be relabelled.

## Scientific boundary

Notebook 34 is a presentation and delivery producer. It may:

- filter already validated rows;
- form deterministic summaries with recorded denominators;
- create web renditions, crops, charts and contact sheets;
- reconstruct the explicitly approved N27 and D02 display derivatives from
  frozen inputs; and
- compile verified local and remote routes.

It may not:

- run restoration inference or feature encoders;
- calculate a new scientific metric or fit a new threshold;
- change an upstream result, flag or applicability decision;
- create a combined quality or trust score;
- substitute another candidate when evidence is absent; or
- strengthen a finding beyond the producer's recorded population and limits.

The N27 threshold-stratum reconstruction applies the frozen configuration and
producer inputs exactly. It persists previously unretained fitting-population
evidence; it does not tune or refit a different rule.

## Fixed public structure

The principal room order is exact:

1. `exhibition_foyer`;
2. `study_design`;
3. `metric_framework`;
4. `model_gallery`;
5. `stability_lab`;
6. `trustworthiness`;
7. `case_explorer`; and
8. `research_archive`.

`focused_portrait_review` is the single D02 child route of
`trustworthiness`. It is never a ninth principal room.

The guided route follows the same sequence. It may offer D02 as a clearly
labelled branch from Trustworthiness, but it never loads exact remote evidence
automatically. Free exploration and the guided route use the same canonical
selection state and evidence records.

## Fixed Controlled-300 population labels

The package validates and exposes, without conflating their roles:

| Population | Required value |
|---|---:|
| Accepted paintings | 300 |
| Broad visual categories | 5, with 60 paintings each |
| Registered cases | 3,425 |
| Four-method eligible cases | 2,620 |
| Four-method primary candidates | 10,480 |
| Completed bounded SDXL candidates | 24 |
| Comparison candidates including bounded SDXL | 10,504 |
| Indexed inspectable candidates | 13,879 |
| Repeated-seed groups | 1,025 |
| Repeated-seed candidate memberships | 4,100 |
| Repeated-seed unordered pairs | 6,150 |
| N32 painting reports | 300 |
| N32 selected-case reports | 30 |
| N31 model reports | 5 |
| N33 final reports | 1 |

D02 remains a separately bounded analysis: 60 portraits screened, 36 included,
91 annotations, 88 retained annotations, 292 eligible records, 45 matched cases
from 20 paintings, and 32 blind-review units. Rendered lightness is an image
property, not race, ethnicity or identity.

## Input closure and versioning

The Controlled-300 configuration introduced and validated during Step 6 uses:

- `dashboard_assets_config.v2`;
- `dashboard_package.v2`;
- `dashboard_runtime_manifest.v1`;
- `dashboard_display_binding.v1`;
- `dashboard_asset.v1`;
- `dashboard_locator.v1`;
- `dashboard_rendition.v1`; and
- `dashboard_room_partition.v1`.

It pins the completed manifests for N01–N33 and separately registers N12A,
D01 and D02. D01, N12A and D02 are not invented as direct N33 upstream keys.
Every input manifest path, run ID, size and SHA-256 is captured in the N34 root
manifest.

`config/evaluation/dashboard_assets.yaml`,
`src/restoration_eval/dashboard_assets.py` and the Notebook 34 outputs now form
the coherent validated `v2` layer. The saved Notebook 35 output and its old
validation configuration remain historical pilot material until the
Controlled-300 application and N35 contract are rebuilt together; they must not
be relabelled or patched piecemeal.

## Required package layout

Notebook 34 keeps its established output root and atomically promotes this
versioned package:

```text
outputs/34_final_streamlit_dashboard_assets/
├── data/
│   ├── bootstrap/
│   │   ├── bootstrap.json
│   │   ├── room_catalogue.json
│   │   ├── glossary.json
│   │   ├── painting_lookup.parquet
│   │   └── filter_options.json
│   ├── rooms/
│   │   ├── exhibition_foyer.parquet
│   │   ├── study_design.parquet
│   │   ├── metric_framework.parquet
│   │   ├── model_gallery.parquet
│   │   ├── stability_lab.parquet
│   │   ├── trustworthiness.parquet
│   │   ├── focused_portrait_review.parquet
│   │   ├── case_explorer.parquet
│   │   └── research_archive.parquet
│   ├── paintings/
│   │   └── pNNN.json.gz
│   ├── reports/
│   │   └── index.json.gz
│   └── derived/
│       ├── threshold_strata.parquet
│       ├── stability_trajectories.parquet
│       ├── d02_hand_summary.parquet
│       ├── d02_lightness_summary.parquet
│       └── d02_r005_geometry.json
├── assets/
│   └── renditions/
│       ├── thumb/
│       ├── standard/
│       └── diagnostic_preview/
├── manifests/
│   ├── dashboard_runtime_manifest.json
│   ├── display_components.csv
│   ├── dashboard_assets.parquet
│   ├── asset_locators.parquet
│   ├── renditions.csv
│   ├── room_partitions.csv
│   ├── artifacts.csv
│   └── run_manifest.json
└── validation/
    └── checks.csv
```

Deterministic gzip uses `mtime=0` and records compressed and decoded
checksums/sizes. The 300 painting shards contain identity and route metadata,
not duplicated image bytes. Producer-scale CSVs and full bundle collections are
never copied into this package.

## Loading tiers

| Tier | Content | Trigger |
|---|---|---|
| `bootstrap` | Room text, route map, boundaries, headline counts, glossary, filters, painting lookup and curated opening renditions | Application startup; zero network |
| `room_partition` | Compact display rows for the active room or D02 child route | Enter the room |
| `painting_partition` | Candidate, availability and exact asset routes for one selected painting | Confirm a painting/case search |
| `exact_remote` | Exact image, diagnostic bundle member or report | Explicit `Load evidence`, `Open verified report` or `Prepare download` action |

No hidden room, tab, drawer or unsubmitted selector may load another tier.

## Root trust manifest

`dashboard_runtime_manifest.json` is the runtime trust root. It records:

- schema and package versions;
- release ID, dataset identity and `controlled_300` scope;
- N34 run ID, generation time, Git commit and dirty state;
- the eight-room order and D02 parent relationship;
- every upstream manifest path, run ID, size and SHA-256;
- the four governing contract paths and SHA-256 values;
- every local partition and rendition path, loading tier, row count, size and
  SHA-256;
- decoded checksum/size for deterministic compressed files;
- every trusted remote publication/bundle root;
- the complete expected `display_id` set;
- population and package-budget expectations;
- validation summary and known limitations; and
- the exact application schema versions it supports.

The manifest does not contain its own checksum. `artifacts.csv` hashes it, and
the Git commit supplies the outer immutable package identity.

## Display binding

Every approved image, metric, chart, report, conclusion, limitation, selector
and route has one or more rows in `display_components.csv`.

Required fields are:

- `binding_id`, `display_id`, `slot_id`, `room_id`, optional `subroute_id` and
  `display_order`;
- `component_kind`, `payload_ref`, `requiredness`, `mapping_state` and
  `loading_tier`;
- the applicable canonical identity fields;
- source-reference IDs, interpretation, limitation and denominator;
- applicability state and plain-language reason; and
- `schema_version`, `status` and `issue`.

Allowed `component_kind` values are `image`, `metric`, `chart`, `report`,
`conclusion`, `limitation`, `selector` and `route`.

Allowed mapping states remain:

- `existing_direct`;
- `existing_filtered`;
- `n34_derived_registered`; and
- `unsupported_until_derived`.

`unsupported_until_derived` is a planning state. A required component may not
retain it when Notebook 34 completes.

## Scientific identity

Identity fields are preserved exactly and case-sensitively:

- `painting_id`, `case_id`, `candidate_id`, `model_id`, `experiment_id`;
- optional `seed`, `prompt_variant_id`, `uncertainty_group_id`;
- optional `metric_name`, `region_id`, `evidence_layer`; and
- for D02, optional `annotation_id`, `hand_control_id`, `review_unit_id` and
  `blind_review_code`.

JSON uses `null`, not an empty string, for an inapplicable identity field.
Titles and filenames are labels, never primary identity.

Stable IDs derive from canonical sorted UTF-8 JSON:

```text
asset_id   = asset_<first 24 hex of SHA256(identity + source SHA + role)>
binding_id = binding_<first 24 hex of SHA256(display ID + slot + payload ref)>
locator_id = locator_<first 24 hex of SHA256(transport + repository + revision + path/member)>
```

A candidate resolves to exactly one case, painting and model. Missing evidence
never changes that identity.

## Asset and provenance records

Each logical asset in `dashboard_assets.parquet` records:

- asset ID, kind, evidence role, requiredness and mapping state;
- its canonical identity object;
- producer notebook/stem/run ID and manifest SHA-256;
- source artifact key, repository-relative path, SHA-256, bytes and MIME type;
- exact upstream row ID or a non-executable equality selector;
- image dimensions where applicable;
- displayed aggregate denominator where applicable;
- derivation type, parameters, helper version and input/output checksums;
- available rendition and remote-locator IDs;
- applicability/publication state and reason;
- concise alternative text; and
- schema, status and issue.

Allowed deterministic derivations are `none`, `filter_rows`, `aggregate`,
`resize`, `crop`, `encode_webp`, `difference_map`, `contact_sheet`,
`chart_render` and `deterministic_regeneration`. Any new derivation requires an
explicit contract amendment.

## Remote locator records

`asset_locators.parquet` supports exactly:

- `local_package`;
- `github_git_blob`;
- `github_lfs_media`;
- `huggingface_object`; and
- `huggingface_bundle_member`.

Every remote locator records provider, repository, full 40-hex revision, path,
immutable resolve URL, human provenance URL, expected size/SHA-256 and the
verified publication record. Bundle members additionally record release ID,
prefix, trusted catalogue path/size/SHA-256, painting ID, remote asset ID and
member size/SHA-256. The verified catalogue supplies the painting-index and
bundle checksum chain.

Mutable branches, tags, abbreviated revisions and `resolve/main` are invalid.
Alternative locators are allowed only when both resolve to the same exact bytes.

## Availability and failure states

Build-time availability is one of:

- `available_local`;
- `available_remote`;
- `available_local_and_remote`;
- `not_applicable`; or
- `not_published`.

Runtime state is one of:

- `ready_local`, `ready_cached`, `ready_remote`;
- `not_applicable`, `not_published`, `not_found`, `offline_uncached`;
- `timeout`, `rate_limited`, `access_denied`;
- `integrity_error`; or
- `decode_error`.

`not_applicable` and `not_published` have no fabricated locator. Only transient
network states expose Retry. An integrity failure never displays failed bytes.

## Rendition contract

N34 generates only registered renditions:

| Profile | Rule |
|---|---|
| `thumb` | Long edge ≤320 px; target ≤75 KiB; hard ≤125 KiB |
| `standard` | Long edge ≤640 px; colour target ≤250 KiB; hard ≤400 KiB |
| `diagnostic_preview` | Lossless PNG; target ≤500 KiB; hard ≤750 KiB |
| `exact` | Original verified bytes; explicit inspection only |

Every rendition stores its source checksum, transformation, dimensions, output
checksum, purpose, breakpoint role, whether it is lossless and whether it is
scientifically exact. Scientific images are never upscaled. Masks, heatmaps,
difference maps and line work remain lossless. D02 crops record exact
`[x1, y1, x2, y2]` coordinates.

A rendition can represent only its own scientific identity and is labelled as
a display rendition where it is not exact.

## Mandatory N34 derivations

Notebook 34 must persist and register all seven groups identified during the
producer-mapping gate:

1. Foyer route previews and web renditions with source checksum lineage;
2. lightweight study, metric, model and Case Explorer selector/availability
   indexes;
3. Stability Lab trajectory charts and compact contact sheets;
4. the exact N27 threshold-stratum table reconstructed from frozen inputs and
   configuration;
5. D02 hand and lightness interactive summary tables;
6. the R005 review panel, clean-versus-restored difference crop and exact
   matched-control geometry; and
7. archive catalogue rows that keep Git artifacts, individual external objects
   and indexed-bundle releases separate.

## Notebook 34 execution plan

The refactored notebook completed eight restart-safe batches:

1. load the `v2` contract and validate every upstream manifest/checksum;
2. normalize Controlled-300 identities, populations and availability;
3. build the zero-network bootstrap and room catalogue;
4. build selector, entity, applicability and per-painting route indexes;
5. build the nine room/subroute display partitions;
6. persist the threshold, stability and D02 derived tables;
7. render and validate deterministic web renditions and D02 visuals, then
   compile immutable remote locators and their checksum chains; and
8. build display bindings, asset records and the root trust manifest, then
   atomically promote the package and run schema, lineage, budget,
   completeness and rerun-safety checks.

Large producer tables are read one at a time or in bounded chunks. Checkpoints
contain normalized metadata only and may be resumed after a kernel restart.
Temporary files remain under the declared N34 work directory and are removed
only after the final atomic promotion passes.

## Application API required by the package

Step 7 replaces the eager `DashboardBundle` with APIs equivalent to:

- `load_bootstrap(release_id)`;
- `load_room_partition(room_id, subroute_id=None)`;
- `load_painting_partition(painting_id)`;
- `validate_selection_state(selection)`;
- `lookup_asset(asset_id, identity)`;
- `resolve_exact_asset(asset_id)`; and
- `open_verified_report(report_id)`.

The remote reader is shared through a thread-safe resource cache. Application
data caches include the release/manifest identity. Runtime code does not scan or
hash producer-scale CSVs.

## Visual-fidelity contract

The nine approved 1672 × 941 images in `approved_current/` are the desktop
visual references. The implementation recreates them with real HTML/CSS,
Streamlit controls and registered evidence; the PNGs are never used as a page
background or passed off as the application.

| Route | Approved desktop reference |
|---|---|
| Exhibition Foyer | [`03_exhibition_foyer_final.png`](approved_current/03_exhibition_foyer_final.png) |
| Study Design | [`04_study_design_final.png`](approved_current/04_study_design_final.png) |
| Metric Framework | [`05_metric_framework_final.png`](approved_current/05_metric_framework_final.png) |
| Model Gallery | [`06_model_gallery_final.png`](approved_current/06_model_gallery_final.png) |
| Stability Lab | [`07_stability_lab_final.png`](approved_current/07_stability_lab_final.png) |
| Trustworthiness | [`08_trustworthiness_final.png`](approved_current/08_trustworthiness_final.png) |
| Focused Portrait Review | [`09_focused_portrait_review_final.png`](approved_current/09_focused_portrait_review_final.png) |
| Case Explorer | [`10_case_explorer_final.png`](approved_current/10_case_explorer_final.png) |
| Research Archive | [`11_research_archive_final.png`](approved_current/11_research_archive_final.png) |

Desktop implementation must preserve:

- the room's dominant spatial composition and focal artwork;
- the intentional free space and relative content density;
- approved palette, texture, lighting and material character;
- typography hierarchy and compact explanatory language;
- placement and visual weight of primary controls, plaques and evidence; and
- the distinct atmosphere of every room while retaining one navigation system.

Custom CSS grid/flex layouts and small semantic HTML wrappers are expected.
Generic Streamlit columns, default metric cards, Google-font/CDN requests and a
single repeated dashboard template are not acceptable substitutes. Native
controls remain accessible and are styled to belong to the room.

The desktop target is **high visual fidelity, not literal pixel identity**.
Real evidence has different aspect ratios and text lengths, and responsive
layouts must reflow. Tablet and mobile preserve hierarchy, meaning and
interaction rather than copying desktop coordinates.

Acceptance uses:

1. a browser screenshot for all eight rooms and D02 at the 1672 × 941 reference
   viewport;
2. tablet checks at 1024 × 1366 and mobile checks at 390 × 844;
3. a component trace from every visible region to its approved reference and
   page contract;
4. keyboard/focus/tap equivalents for hover interactions;
5. checks that no text, selector, image or plaque overlaps or clips; and
6. explicit user approval of the implemented screenshots before deployment.

The approved implementation screenshots—not the concept PNG pixels—become the
future visual-regression baseline. N35 stores their checksum ledger and compact
contact sheets; full raw screenshots may remain local when Git size limits make
them unsuitable for the scientific commit.

## Blocking completion gates

Notebook 34 cannot complete unless all of the following pass:

1. exactly eight rooms occur in the approved order and D02 has the correct
   parent route;
2. every producer-map `display_id` has a binding;
3. no required binding remains `unsupported_until_derived`;
4. all seven mandatory derivation groups are persisted and registered;
5. all source paths are safe, repository-relative and checksum-valid;
6. every equality selector resolves to its required cardinality;
7. candidate, case, painting and model relationships are exact;
8. every remote revision is full 40-hex and matches a Step 3 verified record;
9. every bundle route has a complete catalogue → painting index → bundle →
   member checksum chain;
10. every rendition passes dimensions, byte limits, format, lineage and
    no-upscaling checks;
11. bootstrap operation requires zero network access;
12. Foyer route previews and explanatory content are local;
13. all N34-enforceable Step 4 package, partition and rendition budgets pass;
    N35 separately measures live-process memory and latency;
14. missing evidence never changes identity or triggers a neighbouring-file
    substitute;
15. SDXL, uncertainty, selected reports and D02 obey exact conditional
    applicability;
16. threshold counts come only from the persisted N34 threshold-stratum table;
17. decorative mockup scenery is never registered as scientific evidence;
18. no secret, token, local absolute path or mutable URL enters the package;
19. a no-reuse rerun produces the same deterministic IDs and bytes where
    environment-independent; and
20. the exact output set contains no undeclared work or stale pilot file.

## Step 6 completion and Step 7 handoff

Step 6 completed as eight restart-safe batches and atomically promoted the
Controlled-300 `dashboard_package.v2` tree. All 916 checks passed. The release
contains 377 files, 300 painting partitions, nine room partitions, 100 display
IDs, 170 bindings, 56 logical assets, 48 renditions and 95 immutable locators.
The final tree is 7,978,024 bytes and has no remaining work directory. The
frozen pilot remains recoverable from Git, the pilot dashboard branch and the
pre-scale output mirror.

The post-run portability sweep also normalized four validation-ledger values
that had serialized the local repository/staging root. The retained ledger has
916 passing rows and contains no machine-specific absolute path; this is a
presentation-only normalization and does not change any scientific artifact.

The live Controlled-50 deployment remained unchanged throughout N34 packaging.
Step 7 may now implement the approved interface, but the new interface is not
deployed until the Controlled-300 Notebook 35 validation gate passes.
