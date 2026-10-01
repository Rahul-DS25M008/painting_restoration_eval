# N35 investigation of the N29 manifest discrepancy

N29 run `run_ad7603b6bdb14156a140351f6ac1f241` retains a historical
artifact-manifest checksum mismatch. This note documents the investigation; it
does not change N29's manifests, scientific files, or Archive disclosure.

The original commit was `24fefec4a9469e45093fc79b7801469b30151247`.
Commit `f1e4a460b64755c3ae945d8392e55ba3074bcfb6` subsequently corrected
six artifact rows' `dataset_scope` from `controlled_50` to `controlled_300`.
Their artifact identities, paths, checksums, sizes and file counts did not change.

The original CRLF artifact-manifest checksum matches the original run record:
`e578cbed4c1e53233961a719ae5d4eb54b3bf55e81c0baa1a49be31b30e4027b`.
The corrected run instead records
`5df62a9675e9b6ad214475887378d29043312ca792f33ab0c5c24a7e2ac08a60`,
which was not reproduced from the corrected file's LF/CRLF/BOM/newline variants.
The corrected file's CRLF hash is
`9ec4a9f68a49f724b4f56ed3cf259971013378c39961be2065ce13f5a0438dfa`;
its LF hash is
`c239549fe5e2a2d36ceeef746cd9a7249ef6b11c389816e35d77323fd3f4490f`.

Independent verification checked the explanation CSV, neighbour CSV,
14 counterfactual PNGs, 10 retrieval PNGs, HTML report, and validation CSV.
All six artifact groups matched their recorded checksums, byte sizes and file
counts. Batch 10 repeats those checks through `n35_final_audit.n29_provenance`.

Disposition: retain and disclose the historical manifest discrepancy; verify
the unchanged payloads independently. This is not a declaration that the
incorrect manifest checksum is valid, nor proof of scientific correctness.
Any new payload or history mismatch blocks the Batch 10 investigation gate.
