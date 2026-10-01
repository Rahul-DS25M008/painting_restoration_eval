# Controlled-300 review package

## Begin here

1. [Supervisor summary](reports/supervisor_summary.md)
2. [Full self-contained evaluation report](reports/final_evaluation.html)
3. [Reproducibility appendix](reports/reproducibility_appendix.md)
4. [Limitations and deviations](reports/limitations_and_deviations.md)
5. [Deployment readiness](reports/deployment_readiness.md)

## Model reports

- [OpenCV Telea](reports/models/opencv_telea.html)
- [LaMa](reports/models/lama.html)
- [HINT](reports/models/hint_places2.html)
- [Stable Diffusion Inpainting](reports/models/stable_diffusion_inpainting.html)
- [SDXL Inpainting](reports/models/sdxl_inpainting.html)

## Meeting and evidence aids

- [Key findings](data/key_findings.json)
- [Open questions](data/open_questions.md)
- [Feedback agenda](data/feedback_agenda.md)
- [Thesis tables](tables/thesis_tables.csv)
- [Case report index](tables/case_report_index.csv)
- [Painting report index](tables/painting_report_index.csv)
- [Provenance snapshot](provenance/reproducibility_snapshot.json)

## Included

The package carries six self-contained scientific HTML reports, 24 figures,
five model cards, eight compact tables/indexes, 38 upstream run manifests,
evaluation configurations, requirements files and provenance documents.
D01 and D02 retain their separate scopes.

## Intentionally absent

The 30 detailed case reports, 300 painting reports, selected-case grids,
full dashboard visuals, raw/restored image collections, diagnostic maps,
model weights and caches are not duplicated. Repository paths inside copied
tables/manifests are provenance references, not promises of package-local files.
Use the full repository and pinned publication records for those assets.

Application files are source snapshots only: **this is not a runnable clone**.
Zenodo publication remains planned; no new upload is performed by N36.

## Integrity handoff

Distribute the full N36 delivery directory, including package, data, reports,
manifests and validation. The manifest is ../manifests/package_manifest.json;
the artifact index is ../data/artifact_index.csv. Accept this delivery only when
../manifests/run_manifest.json records completed status and a passed completion gate.

For an accepted release, compare the package manifest's package-relative paths,
byte sizes and SHA-256 values against every bundled file. The tree digest is
computed from sorted package-relative-path, tab, file-hash records joined by
newlines. Integrity does not imply scientific correctness or conservation approval.

## Limits travel with the evidence

N35's 14 warning nonpasses and the N29/N35 provenance exceptions remain explicit.
Repeated-seed variability is not calibrated confidence. SDXL is bounded
feasibility evidence, not a fifth complete benchmark method.
