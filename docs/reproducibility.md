# Reproducibility and evidence records

The numbered experiments and supplements D01–D04 are complete. Current entry
points are the [notebook roadmap](final_notebook_roadmap.md),
[methods](methodology_notes.md), [evidence audit](evidence_dependency_audit.md)
and [provenance exceptions](provenance_exceptions.md).

## Reproducing a run

Use the source revision, configuration, input identities, model checkpoint and
environment recorded in that run's manifest. A dashboard installation does not
include every inference dependency. Notebooks contain the experimental sequence;
`src/restoration_eval/` contains its reusable implementation. Saved outputs are
evidence of the recorded execution, not a promise that a different environment
will produce identical results.

Each producer owns its output directory. Input checks, identity joins, eligibility
rules and output validation precede its completion gate. Manifests and artifact
indexes connect files to their sizes and hashes. Missing or mismatched evidence
must be reported explicitly; a related image or a newly calculated statistic is
not a substitute for the recorded result.

## Interpretation

Controlled-300 retains known references and explicitly defined image regions.
The physical-damage supplement has no clean reference and remains a separate
population. D04 uses targeted Stable Diffusion prompts; controlled comparators
use their recorded prompts. These comparisons are descriptive. Repeated seeds
measure disagreement, not calibrated correctness. Visual review is distinct
from independent expert assessment.

## Publication and maintenance

Use the recorded publication manifests for GitHub/Hugging Face artifact retrieval.
The Zenodo v1.0.0 release is an immutable Controlled-300 snapshot and excludes
D03/D04. Later documentation and presentation changes do not rerun experiments
or replace their historical validation results. The dated exception ledger
records known provenance limitations.

Temporary work belongs in ignored local directories. Credentials, machine-local
paths and conversational instructions are not research documentation. Refresh
the project inventory after maintained files change. Current regression checks
belong to the maintenance revision and must not be presented as the original
notebook execution.

Dated checkpoint documents, executed notebooks and checksum-pinned research
records retain their original wording and review metadata. They are archival
records, not current operating instructions. Current documentation uses neutral
research language; historical records are interpreted with the exception ledger.
