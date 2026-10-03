# Provenance exceptions at study closeout

This ledger summarizes retained exceptions; it does not replace historical run
records or convert warnings into passes. See the [full audit](evidence_dependency_audit.md)
and the [post-publication reporting errata](errata/2026-10-03/README.md).

| Stage | Exception | What was checked | What remains uncertain | Claims affected |
|---|---|---|---|---|
| N29 | Recorded artifact-manifest hash does not match the corrected manifest | Explanation CSV, neighbour CSV, 14 counterfactual PNGs, 10 retrieval PNGs, HTML and validation CSV matched recorded hashes, sizes and file counts. Original manifest CRLF bytes matched the original run record. | Exact bytes underlying the later recorded manifest hash have not been recovered. | Packaging provenance; no numerical invalidity has been demonstrated by this discrepancy. |
| N35 | Recorded notebook-source hash differs from the saved notebook | Saved deployment outputs and subsequent N36 package records were checked. | Cause of the source mismatch and exact equivalence to the executed source are not established. | Deployment assurance and notebook-source traceability. |
| N35 | 14 warning nonpasses retained | Four dependency warnings and ten owner-accepted, unmeasured qualifications are explicitly retained in the validation record. | The unmeasured properties, including exhaustive browser/accessibility/performance checks and clean-environment/deployed-revision qualifications, remain unverified. | Deployment validation, not evidence that every browser or performance property passes. |
| N36 | Consolidation and evidence packaging, not a scientific rerun | File identities and selected source/package hashes were checked. The closeout records 859 passes, 16 warning nonpasses and zero blockers. | Independent end-to-end scientific reproduction has not been performed. | Reproducibility scope: preserved artifacts and recorded execution, not independent replication. |

Checksums establish file identity. Execution records establish that a run was
recorded. Neither alone establishes independent reproduction. “Zero blockers”
is an administrative closeout result, not a substitute for scientific validation.
N36's 16 warning nonpasses include N35's 14 plus the N29 and N35 hash discrepancies.

## Source records

- [N29 investigation and exact hashes](n35_n29_manifest_discrepancy.md).
- [N35 deployment checks](../outputs/35_dashboard_and_deployment_validation/validation/dashboard_checks.csv).
- [N35 readiness record](../outputs/35_dashboard_and_deployment_validation/reports/deployment_readiness.md).
- [N36 reproducibility appendix](../outputs/36_supervisor_publication_reproducibility_package/reports/reproducibility_appendix.md).
- [N36 closeout audit](evidence_dependency_audit.md#n36-controlled-300-closeout--2026-10-01).

The October 2026 reporting corrections preserve the original files. Updating the
N26 export source does not establish that the changed notebook was historically
executed; its saved outputs remain those of the original run.
