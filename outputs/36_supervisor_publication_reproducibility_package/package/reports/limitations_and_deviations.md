# Limitations and deviations

## The 18 limitations retained from N33

- controlled artificial damage not real material treatment (source row: thesis_725624b4eb27cc8e027bf683).
- no paired real damaged undamaged conservation dataset (source row: thesis_51c77cbe996a5cd4c0598614).
- controlled 300 balanced collection does not represent all painting traditions or conservation conditions (source row: thesis_82a27ee7468b11300fab3664).
- style or period documented for 268 of 300 paintings (source row: thesis_32f12c2ed229f5b5956d001f).
- thirty five painting extensions do not separate category from painting identity (source row: thesis_1b8b4918bb9419296cb48a63).
- sdxl bounded 35 case schedule has 24 completed candidates across 30 paintings (source row: thesis_574b0fe3ee854259e97ac0a4).
- uncertainty only for supported repeated seed populations (source row: thesis_da0ceb3d5b0a2c33e5910f69).
- uncertainty is not calibrated confidence (source row: thesis_0f33307bea5e7ea2d43a4638).
- telea lama and hint are deterministic (source row: thesis_baf9903b8385ddb298068fab).
- no human or expert rating dataset (source row: thesis_412bc378afa849c0aae6b073).
- computational flags are not expert ground truth (source row: thesis_6df3e6d569d4707119103776).
- retrieval similarity is not restoration correctness (source row: thesis_66b84b94a2a5db40b34260d2).
- feature similarity is not historical authenticity (source row: thesis_b46244f4faac917626aaaf7e).
- runtime and memory describe one workstation (source row: thesis_f979ba9751c80e014784770a).
- scaling projections are not executed results or confidence intervals (source row: thesis_e7d716e9e72ff10d9b33180f).
- context prompt candidates p01 to p04 lack complete downstream flag coverage (source row: thesis_3632f0e4400d5d4bf16a08c5).
- no combined universal quality or trust score (source row: thesis_f634f29172af1ef833160693).
- no conservation approval or physical treatment recommendation (source row: thesis_670c850d97329cc78ee66db7).

These are preserved from the [thesis tables](../tables/thesis_tables.csv).
The complete producer records and limitations remain in the provenance snapshot.

## Scope separation

D01 is a separate 12-case method-selection study. D02 is a focused portrait audit,
not demographic-bias ground truth. Rendered lightness is not race or identity.
SDXL's 35-case schedule yielded 24 completed candidates; it is not a fifth
fully evaluated benchmark method.

## Historical provenance exceptions

- N29: historical artifact-manifest mismatch, with all six payload groups checked.
- N35: recorded notebook-source hash differs from the accepted saved source.
  The exact cause was not established; the owner accepted proceeding without rerun.

These exceptions are disclosed, not repaired or converted into passed checks.
Exact recorded/observed digests appear in the
[provenance snapshot](../provenance/reproducibility_snapshot.json).

## The 14 inherited N35 warning nonpasses

### batch_1_dependency_versions / version__pillow

Observed: 9.5.0

Details: Development may continue, but the deployment environment must be reconciled before the final N35 readiness claim.

### batch_1_dependency_versions / version__plotly

Observed: 6.8.0

Details: Development may continue, but the deployment environment must be reconciled before the final N35 readiness claim.

### batch_1_dependency_versions / version__pyarrow

Observed: 24.0.0

Details: Development may continue, but the deployment environment must be reconciled before the final N35 readiness claim.

### batch_1_dependency_versions / version__streamlit

Observed: 1.59.0

Details: Development may continue, but the deployment environment must be reconciled before the final N35 readiness claim.

### batch_11_qualification / desktop_1672x941_all_rooms

Observed: owner_accepted_without_measurement

Details: {"original_record": {"validation_stage": "batch_11_qualification", "check_id": "desktop_1672x941_all_rooms", "check_description": "Browser/platform qualification; required before N35 closeout", "severity": "blocking", "expected": "Verified direct observation/measurement", "observed": "pending_not_verified", "passed": false, "details": "{\"check_id\": \"desktop_1672x941_all_rooms\", \"evidence\": \"\", \"observed_at_utc\": \"\", \"passed\": false}"}, "disposition": "Owner explicitly accepts delivery without completing this measurement; NOT a test pass."}

### batch_11_qualification / tablet_1024x1366_all_rooms

Observed: owner_accepted_without_measurement

Details: {"original_record": {"validation_stage": "batch_11_qualification", "check_id": "tablet_1024x1366_all_rooms", "check_description": "Browser/platform qualification; required before N35 closeout", "severity": "blocking", "expected": "Verified direct observation/measurement", "observed": "pending_not_verified", "passed": false, "details": "{\"check_id\": \"tablet_1024x1366_all_rooms\", \"evidence\": \"\", \"observed_at_utc\": \"\", \"passed\": false}"}, "disposition": "Owner explicitly accepts delivery without completing this measurement; NOT a test pass."}

### batch_11_qualification / mobile_390x844_all_rooms

Observed: owner_accepted_without_measurement

Details: {"original_record": {"validation_stage": "batch_11_qualification", "check_id": "mobile_390x844_all_rooms", "check_description": "Browser/platform qualification; required before N35 closeout", "severity": "blocking", "expected": "Verified direct observation/measurement", "observed": "pending_not_verified", "passed": false, "details": "{\"check_id\": \"mobile_390x844_all_rooms\", \"evidence\": \"\", \"observed_at_utc\": \"\", \"passed\": false}"}, "disposition": "Owner explicitly accepts delivery without completing this measurement; NOT a test pass."}

### batch_11_qualification / keyboard_focus_and_dialogs

Observed: owner_accepted_without_measurement

Details: {"original_record": {"validation_stage": "batch_11_qualification", "check_id": "keyboard_focus_and_dialogs", "check_description": "Browser/platform qualification; required before N35 closeout", "severity": "blocking", "expected": "Verified direct observation/measurement", "observed": "pending_not_verified", "passed": false, "details": "{\"check_id\": \"keyboard_focus_and_dialogs\", \"evidence\": \"\", \"observed_at_utc\": \"\", \"passed\": false}"}, "disposition": "Owner explicitly accepts delivery without completing this measurement; NOT a test pass."}

### batch_11_qualification / firefox_reload_and_second_monitor

Observed: owner_accepted_without_measurement

Details: {"original_record": {"validation_stage": "batch_11_qualification", "check_id": "firefox_reload_and_second_monitor", "check_description": "Browser/platform qualification; required before N35 closeout", "severity": "blocking", "expected": "Verified direct observation/measurement", "observed": "pending_not_verified", "passed": false, "details": "{\"check_id\": \"firefox_reload_and_second_monitor\", \"evidence\": \"\", \"observed_at_utc\": \"\", \"passed\": false}"}, "disposition": "Owner explicitly accepts delivery without completing this measurement; NOT a test pass."}

### batch_11_qualification / same_room_no_document_reload

Observed: owner_accepted_without_measurement

Details: {"original_record": {"validation_stage": "batch_11_qualification", "check_id": "same_room_no_document_reload", "check_description": "Browser/platform qualification; required before N35 closeout", "severity": "blocking", "expected": "Verified direct observation/measurement", "observed": "pending_not_verified", "passed": false, "details": "{\"check_id\": \"same_room_no_document_reload\", \"evidence\": \"\", \"observed_at_utc\": \"\", \"passed\": false}"}, "disposition": "Owner explicitly accepts delivery without completing this measurement; NOT a test pass."}

### batch_11_qualification / cross_room_links_and_guided_tour

Observed: owner_accepted_without_measurement

Details: {"original_record": {"validation_stage": "batch_11_qualification", "check_id": "cross_room_links_and_guided_tour", "check_description": "Browser/platform qualification; required before N35 closeout", "severity": "blocking", "expected": "Verified direct observation/measurement", "observed": "pending_not_verified", "passed": false, "details": "{\"check_id\": \"cross_room_links_and_guided_tour\", \"evidence\": \"\", \"observed_at_utc\": \"\", \"passed\": false}"}, "disposition": "Owner explicitly accepts delivery without completing this measurement; NOT a test pass."}

### batch_11_qualification / downloaded_reports_open_self_contained

Observed: owner_accepted_without_measurement

Details: {"original_record": {"validation_stage": "batch_11_qualification", "check_id": "downloaded_reports_open_self_contained", "check_description": "Browser/platform qualification; required before N35 closeout", "severity": "blocking", "expected": "Verified direct observation/measurement", "observed": "pending_not_verified", "passed": false, "details": "{\"check_id\": \"downloaded_reports_open_self_contained\", \"evidence\": \"\", \"observed_at_utc\": \"\", \"passed\": false}"}, "disposition": "Owner explicitly accepts delivery without completing this measurement; NOT a test pass."}

### batch_11_qualification / browser_warm_navigation_p95

Observed: owner_accepted_without_measurement

Details: {"original_record": {"validation_stage": "batch_11_qualification", "check_id": "browser_warm_navigation_p95", "check_description": "Browser/platform qualification; required before N35 closeout", "severity": "blocking", "expected": "Verified direct observation/measurement", "observed": "pending_not_verified", "passed": false, "details": "{\"check_id\": \"browser_warm_navigation_p95\", \"evidence\": \"\", \"observed_at_utc\": \"\", \"passed\": false}"}, "disposition": "Owner explicitly accepts delivery without completing this measurement; NOT a test pass."}

### batch_11_qualification / remote_action_budget_and_peak_memory

Observed: owner_accepted_without_measurement

Details: {"original_record": {"validation_stage": "batch_11_qualification", "check_id": "remote_action_budget_and_peak_memory", "check_description": "Browser/platform qualification; required before N35 closeout", "severity": "blocking", "expected": "Verified direct observation/measurement", "observed": "pending_not_verified", "passed": false, "details": "{\"check_id\": \"remote_action_budget_and_peak_memory\", \"evidence\": \"\", \"observed_at_utc\": \"\", \"passed\": false}"}, "disposition": "Owner explicitly accepts delivery without completing this measurement; NOT a test pass."}

## Delivery boundaries

Only selected upstream payloads were rehashed. Remote availability was not
retested here. The recorded checker revision is not proof of the deployed
server revision. Case/painting reports and bulk collections are indexed, not
duplicated. Source snapshots do not make this a runnable application clone.

Visual plausibility is not historical correctness, expert truth or conservation
approval. No universal combined quality or trustworthiness score is constructed.
