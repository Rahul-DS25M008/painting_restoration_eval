# Reproducibility appendix

## What this delivery reproduces

N36 consolidates validated saved artifacts and verifies copied bytes.
It does not repeat restoration inference, metric computation or statistical tests.
The bundle is not a complete runnable checkout; application files are source snapshots.

## Packaging environment and revision

- Python: 3.12.6
- Platform: Windows-11-10.0.26200-SP0
- Git commit: dfe8d13cb564b17b14b64ba901cf328e0d3561cd
- Git branch: main
- Uncommitted changes present: True
- Inventory record: inventory_20261001T153815Z_9074bd08

| package | version |
| --- | --- |
| pandas | 2.3.3 |
| numpy | 1.26.4 |
| pyyaml | 6.0.3 |
| pillow | 9.5.0 |

The recorded commit identifies HEAD, not every uncommitted byte.
The [snapshot](../provenance/reproducibility_snapshot.json) records exact
selected-source hashes and preserves upstream environments. This packaging
environment is not proof of a clean Linux app installation or a reproduction of
all GPU experiments.

## Model revisions, seeds and hardware

| model_id | model_identifier | model_revision | seed_policy | execution_device | precision |
| --- | --- | --- | --- | --- | --- |
| opencv_telea | cv2.INPAINT_TELEA | opencv-4.11.0 | not_applicable | cpu | uint8 |
| lama | big-lama.pt | iopaint_lama_default | not_applicable | cuda | float32 |
| hint_places2 | hint_places2_official | 15e867d8c8689b9d5050383fc3884537ae876145 | not_applicable | cuda | float32 |
| stable_diffusion_inpainting | stable-diffusion-v1-5/stable-diffusion-inpainting | 8a4288a76071f7280aedbdb3253bdb9e9d5d84bb | 2026 | cuda | float16 |
| sdxl_inpainting | diffusers/stable-diffusion-xl-1.0-inpainting-0.1 | 115134f363124c53c7d878647567d04daf26e41e | 2026 | cuda | float16 |

The five [model cards](../tables/model_cards.csv), their complete records
in the snapshot and the 38 copied run manifests retain model identifiers,
revisions, seeds, configuration, dataset and hardware evidence as recorded.
Missing upstream fields remain missing; no revision or seed is invented.

## Compute and scaling

Saved compute/scalability records are included in the snapshot with their
original scenario and observation/projection fields. Projections are not executed
measurements or confidence intervals. Runtime and memory characterize recorded
hardware and producer-specific populations, not deployment latency.
The legacy experiment requirements and current dashboard requirements have
different scopes; neither is silently substituted for recorded producer versions.

## Upstream acceptance

| notebook_id | run_id | completion_basis | ledger_hash_state |
| --- | --- | --- | --- |
| 01 | run_49a7e3c485394878ab4323ce661f3ef5 | producer_gate | not_declared_by_producer |
| 02 | run_ca94012bb1e54bf5bf57c1fdabb01480 | producer_gate | not_declared_by_producer |
| 03 | run_dd51e1b1ca374f3aad16d22b0cd12c99 | producer_gate | not_declared_by_producer |
| 04 | run_92d2030511e14f108bd9ef46f8c3110a | producer_gate | not_declared_by_producer |
| 05 | run_fb717ad978394227944ef6bf99919f08 | producer_gate | not_declared_by_producer |
| 06 | run_cd2601a25a2d4794aba0745ec6beed5c | producer_gate | not_declared_by_producer |
| 07 | run_ad90292d5fb8462eb6241b8123a779d6 | producer_gate | not_declared_by_producer |
| 08 | run_b83466f07ebb4b55928229587922334a | producer_gate | not_declared_by_producer |
| 09 | run_350786ea88014b67b0cf9efec7fac23c | producer_gate | not_declared_by_producer |
| 10 | run_6f81083a17804d36b1495e4932db4e03 | producer_gate | not_declared_by_producer |
| 11 | run_4385124a0cca4d758d357de654a33f13 | producer_gate | not_declared_by_producer |
| 12 | run_1f7af9d329354a56b4275c4af3cd3f75 | producer_gate | not_declared_by_producer |
| 12A | run_f6c9353c31ce4ed9be5e5502571d635d | producer_gate | not_declared_by_producer |
| 13 | run_41b9c87a3c034f19b6f28868127b3c89 | producer_gate | not_declared_by_producer |
| 14 | run_27cb11ae9aa94133ad474b2f38cab122 | producer_gate | not_declared_by_producer |
| 15 | run_50c1bb5f25b44111a76df998329d69ed | producer_gate | not_declared_by_producer |
| 16 | run_99b0d8d1af1b43bd8e8cb3d6ae754868 | producer_gate | not_declared_by_producer |
| 17 | run_ed15508895b542e6ac0733c49704ad26 | producer_gate | not_declared_by_producer |
| 18 | run_7c1d7195ed8447c1a878259360b1f5f2 | producer_gate | matched |
| 19 | run_7384c7fb8d4c4efe98264a660ac12a75 | producer_gate | matched |
| 20 | run_8c94e988fd4c4d7cae0acd8c3a64fbe6 | producer_gate | matched |
| 21 | run_86f7f46183634889aa050ee2a9f33b56 | producer_gate | matched |
| 22 | run_d0276a6859f74fada266936f43b7499f | producer_gate | matched |
| 23 | run_e93288fc3ac847ccb699241b4b4c8be0 | producer_gate | matched |
| 24 | run_bbf68684c3ca47e5827c2b8b4b666351 | producer_gate | matched |
| 25 | run_cf89ebe972364c7b8ccfefc6bf2a63ca | producer_gate | matched |
| 26 | run_efc978dd6d504cdb9b138a750f6dca83 | producer_gate | matched |
| 27 | run_bef567ee35c1409dbcecfb71f1b4f8b4 | producer_gate | matched |
| 28 | run_4325bb483fbc4ccda670df125c40731d | producer_gate | matched |
| 29 | run_ad7603b6bdb14156a140351f6ac1f241 | producer_gate | historical_exception |
| 30 | run_605de239145a46e9a202fd63bbbb4e9c | producer_gate | matched |
| 31 | run_430fd1355d3a4011bedc55b571d9544c | producer_gate | matched |
| 32 | run_0d4ae193602944dda511bf54199105b1 | producer_gate | matched |
| 33 | run_aef04267c2e44495a4e7a6249426bd4d | producer_gate | matched |
| 34 | run_1e831de6e27f9ead0147bb30 | producer_gate | matched |
| 35 | run_3d52ae7863c44fb1b7f56a99ea0c01fa | accepted_closeout | matched |
| D02 | run_fdbd2ed6e93b4d709f5439af028a7600 | producer_gate | matched |
| 37 | run_6583cb070ead425b91e0bf738f1822ea | producer_gate | matched |

N35 uses its accepted closeout, not an invented completion_gate_passed field.
A ledger hash not declared by an early producer is labelled accordingly.
Selected payload groups were independently checked; this is not a claim that
every upstream image or remote object was rehashed by N36.

## Known exceptions and deployment qualification

N29's historical artifact-ledger checksum differs from its recorded value.
All six payload groups were independently checked; the historical record is unchanged.
N35's recorded notebook-source digest differs from the accepted saved source.
Both digests and the owner's accepted disposition are retained in the snapshot.

N35 records 519 passes and 14 warning nonpasses: four dependency warnings and ten
unmeasured qualifications. Availability success is not p95 latency or peak-memory
measurement. The server checkout revision remains independently unattested.
See [deployment readiness](../reports/deployment_readiness.md) and
[limitations](../reports/limitations_and_deviations.md).

## Publication references

- [Github](https://github.com/Rahul-DS25M008/painting_restoration_eval)
- [Hf Candidates](https://huggingface.co/datasets/RahulMaddineni264/painting-restoration-eval-candidates)
- [Hf Diagnostics](https://huggingface.co/datasets/RahulMaddineni264/painting-restoration-eval-diagnostics)
- [Dashboard](https://fhtw-painting-restoration-main.streamlit.app/)

N34 records 2,653
individually published artifacts and
6 bundle releases.
These are inherited records, not new remote checks. Immutable revisions and
checksums must be taken from the original release records, not a floating URL.
Zenodo remains planned after pipeline freeze; N36 does not claim a deposit or DOI.

## Reproduction route

1. Use the full repository and the exact producer manifests, not this review bundle alone.
2. Resolve the required local/remote assets through their pinned publication records.
3. Recreate each producer's documented environment, model revisions and configuration.
4. Follow the numbered dependency order, keeping D01 and D02 scopes separate.
5. Compare identifiers, dimensions, byte checksums and validation evidence.
6. Treat the disclosed provenance and deployment qualifications as unresolved limits.

## Integrity and portability

Copied sources must match their frozen SHA-256 digests.
N36-generated documents are identified separately from copied sources.
Consult the companion package manifest and completed run record for final integrity.
The original nine-step plan was delivered in eight batches: the last two combine
indexing, portability, completion and promotion without omitting those checks.
