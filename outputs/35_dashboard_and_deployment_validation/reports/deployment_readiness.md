# N35 local deployment readiness

Status: Partial local checkpoint; NOT readiness-certified. Required qualifications remain pending.

Deployment URL: (not yet validated).

Batch 11 must resolve every pending qualification and record the deployed revision, public URL, clean Linux runtime and live checks before N35 closeout or N36.

## Local user signoff (qualitative only)

User reported: 'everything works perfectly, no need to change anything'. Qualitative local approval only; no per-check measurement or observation time inferred.

No exact viewport, timing, resource or individual checklist pass is inferred from a general approval.

## Pending qualifications (not passed)

- desktop_1672x941_all_rooms
- tablet_1024x1366_all_rooms
- mobile_390x844_all_rooms
- keyboard_focus_and_dialogs
- firefox_reload_and_second_monitor
- same_room_no_document_reload
- cross_room_links_and_guided_tour
- downloaded_reports_open_self_contained
- browser_warm_navigation_p95
- remote_action_budget_and_peak_memory

## Automated receipts

```json
{
  "visual_delta": {
    "passed": true,
    "scoped_backend_files": [
      "streamlit_app.py",
      "src/restoration_eval/model_gallery.py",
      "src/restoration_eval/model_gallery_view.py",
      "src/restoration_eval/stability_lab.py",
      "src/restoration_eval/trustworthiness.py",
      "src/restoration_eval/focused_portrait.py",
      "src/restoration_eval/metric_inspection_view.py",
      "src/restoration_eval/research_archive.py",
      "src/restoration_eval/case_explorer.py",
      "src/restoration_eval/dashboard_application.py"
    ],
    "freeze_failures": [],
    "note": "Original visual freezes retained; exact backend deltas are separately fingerprinted and AST-scoped"
  },
  "companion": {
    "passed": true,
    "files": 1161,
    "bytes": 54083706,
    "route_count": 131165,
    "populations": {
      "flags": 152669,
      "categories": 194306,
      "policy": 319217
    },
    "source_hashes": {
      "outputs/13_classical_metrics/metrics/classical_metrics.csv": {
        "sha256": "a9a1250c7ecd1339dbb4150d8f42336ea3d1b0567648f6f03cf7f7e6f23e337c",
        "source_rows": 477753,
        "selected_rows": 63216
      },
      "outputs/16_difference_maps_and_spatial_diagnostics/metrics/spatial_diagnostics.csv": {
        "sha256": "7f8155aaee2b4eaaad7cba004bf28f38500fc45c4f3690ea60d65f3de04badab",
        "source_rows": 143247,
        "selected_rows": 30408
      },
      "outputs/18_diffusion_uncertainty_analysis/metrics/uncertainty_metrics.csv": {
        "sha256": "0adb83c77a6cc66b585b2f7168e718cba340e3f0c0af0dd2778e2da1137b528a",
        "source_rows": 124800,
        "selected_rows": 5460
      },
      "outputs/22_damage_size_diffusion_uncertainty_extension/metrics/damage_size_uncertainty.csv": {
        "sha256": "e386491f50166fa64d105e375a67994bbeb01c2a9214b604249b017f946d7c5e",
        "source_rows": 33320,
        "selected_rows": 1715
      },
      "outputs/27_failure_taxonomy_and_trustworthiness_flags/metrics/trustworthiness_flags.csv": {
        "sha256": "a582c7a100caeffca7f34d9a8588eb09e19c8762007ec6a8aa035c68b8ed7aca",
        "source_rows": 152669,
        "selected_rows": 152669
      },
      "outputs/27_failure_taxonomy_and_trustworthiness_flags/metrics/failure_assignments.csv": {
        "sha256": "1c998f42fde3bacc22e0901ef264e99d085f85cc332ccfa3ad3626f34333f5f2",
        "source_rows": 194306,
        "selected_rows": 194306
      },
      "outputs/28_metric_and_region_policy_ablation/metrics/flag_stability.csv": {
        "sha256": "9e72d08b807fa142c655112734a7d2360cd3f25aa89dfec94327e8ef79b37cd7",
        "source_rows": 319217,
        "selected_rows": 319217
      }
    }
  },
  "closure": {
    "passed": true,
    "candidates": 13879,
    "reports": 337,
    "missing": [],
    "scope": "All N34 case inputs, candidate asset routes and report paths; remote byte samples are a separate gate"
  },
  "transport": {
    "passed": true,
    "returncode": 0,
    "stdout": "",
    "stderr": "test_bundle_and_missing_member (test_evidence_transport.TransportTests.test_bundle_and_missing_member) ... ok\ntest_changed_local_bytes_do_not_fall_back (test_evidence_transport.TransportTests.test_changed_local_bytes_do_not_fall_back) ... ok\ntest_cold_warm_and_corrupt_cache (test_evidence_transport.TransportTests.test_cold_warm_and_corrupt_cache) ... ok\ntest_concurrent_same_object_is_downloaded_once (test_evidence_transport.TransportTests.test_concurrent_same_object_is_downloaded_once) ... ok\ntest_encoded_image_cache_is_byte_bounded (test_evidence_transport.TransportTests.test_encoded_image_cache_is_byte_bounded) ... ok\ntest_eviction (test_evidence_transport.TransportTests.test_eviction) ... ok\ntest_git_newline_reconstruction_requires_exact_hash (test_evidence_transport.TransportTests.test_git_newline_reconstruction_requires_exact_hash) ... ok\ntest_http_404_does_not_retry (test_evidence_transport.TransportTests.test_http_404_does_not_retry) ... ok\ntest_invalid_zip (test_evidence_transport.TransportTests.test_invalid_zip) ... ok\ntest_mutable_revision_rejected_before_request (test_evidence_transport.TransportTests.test_mutable_revision_rejected_before_request) ... ok\ntest_oversize_stream_fails_and_cleans_partial (test_evidence_transport.TransportTests.test_oversize_stream_fails_and_cleans_partial) ... ok\ntest_retry_statuses_and_timeout_are_bounded (test_evidence_transport.TransportTests.test_retry_statuses_and_timeout_are_bounded) ... ok\ntest_stale_lock_and_partial_cleanup (test_evidence_transport.TransportTests.test_stale_lock_and_partial_cleanup) ... ok\ntest_traversal_rejected (test_evidence_transport.TransportTests.test_traversal_rejected) ... ok\ntest_wrong_hash_fails_closed (test_evidence_transport.TransportTests.test_wrong_hash_fails_closed) ... ok\n\n----------------------------------------------------------------------\nRan 15 tests in 0.551s\n\nOK\n"
  },
  "persistence_tests": {
    "passed": true,
    "returncode": 0,
    "stdout": "Running suite trust_portrait\nNotebook SOURCE changed during validation. Save all cells, then rerun without editing.\nRunning suite trust_portrait\n",
    "stderr": "test_complete_cells_parse (test_n35_batch10.Batch10Tests.test_complete_cells_parse) ... ok\ntest_failed_promotion_restores_prior_run (test_n35_batch10.Batch10Tests.test_failed_promotion_restores_prior_run) ... ok\ntest_fresh_failure_keeps_structured_diagnostics (test_n35_batch10.Batch10Tests.test_fresh_failure_keeps_structured_diagnostics) ... ok\ntest_incomplete_staging_never_replaces_old_run (test_n35_batch10.Batch10Tests.test_incomplete_staging_never_replaces_old_run) ... ok\ntest_manual_observations_never_default_to_pass (test_n35_batch10.Batch10Tests.test_manual_observations_never_default_to_pass) ... ok\ntest_no_notebook_execution_or_publication_in_cells (test_n35_batch10.Batch10Tests.test_no_notebook_execution_or_publication_in_cells) ... ok\ntest_original_frozen_sources_are_not_rebaselined (test_n35_batch10.Batch10Tests.test_original_frozen_sources_are_not_rebaselined) ... ok\ntest_promotion_preserves_old_run (test_n35_batch10.Batch10Tests.test_promotion_preserves_old_run) ... ok\ntest_stale_success_receipt_is_rejected (test_n35_batch10.Batch10Tests.test_stale_success_receipt_is_rejected) ... ok\ntest_unsafe_target_rejected (test_n35_batch10.Batch10Tests.test_unsafe_target_rejected) ... ok\n\n----------------------------------------------------------------------\nRan 10 tests in 1.803s\n\nOK\n"
  },
  "tests_study": {
    "group": "study",
    "run": 29,
    "skipped": 0,
    "failures": 0,
    "errors": 0,
    "excluded_historical_checks": [],
    "current_notebook_source_and_canonical_outputs_unchanged": true,
    "integrity_changes": {
      "notebook_source_changed": false,
      "notebook_source_before": "fb8419577344692a09ca829e81a2449b5b96e5c30c0c66075fe5210c77754522",
      "notebook_source_after": "fb8419577344692a09ca829e81a2449b5b96e5c30c0c66075fe5210c77754522",
      "canonical_output_changes": []
    },
    "remediation": "",
    "network_attempts": [],
    "transcript": "test_asset_rendition_and_locator_apis_preserve_identity (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_asset_rendition_and_locator_apis_preserve_identity) ... ok\ntest_case_explorer_default_is_exact_and_cross_experiment_safe (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_case_explorer_default_is_exact_and_cross_experiment_safe) ... ok\ntest_curated_case_metrics_resolve_only_for_exact_p018_identity (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_curated_case_metrics_resolve_only_for_exact_p018_identity) ... ok\ntest_curated_threshold_is_exact_and_mismatch_never_substitutes (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_curated_threshold_is_exact_and_mismatch_never_substitutes) ... ok\ntest_every_room_and_d02_partition_loads_exact_identity (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_every_room_and_d02_partition_loads_exact_identity) ... ok\ntest_exact_rooms_child_route_and_population (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_exact_rooms_child_route_and_population) ... ok\ntest_focused_portrait_review_accepts_each_registered_entry_room (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_focused_portrait_review_accepts_each_registered_entry_room) ... ok\ntest_four_derived_payloads_resolve_as_typed_n34_selections (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_four_derived_payloads_resolve_as_typed_n34_selections) ... ok\ntest_foyer_decorative_shell_is_pinned_and_non_scientific (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_foyer_decorative_shell_is_pinned_and_non_scientific) ... ok\ntest_metric_decorative_shell_is_pinned_and_non_scientific (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_metric_decorative_shell_is_pinned_and_non_scientific) ... ok\ntest_open_and_lazy_local_reads_make_no_network_request (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_open_and_lazy_local_reads_make_no_network_request) ... ok\ntest_painting_partition_is_lazy_and_identity_preserving (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_painting_partition_is_lazy_and_identity_preserving) ... ok\ntest_report_index_and_local_report_api_are_verified (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_report_index_and_local_report_api_are_verified) ... ok\ntest_room_metric_rows_remain_narrative_and_are_never_number_parsed (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_room_metric_rows_remain_narrative_and_are_never_number_parsed) ... ok\ntest_safe_paths_and_manifest_checksums_fail_closed (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_safe_paths_and_manifest_checksums_fail_closed) ... ok\ntest_study_design_p001_branches_and_scope_are_exact (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_study_design_p001_branches_and_scope_are_exact) ... ok\ntest_study_design_representatives_have_all_exact_visible_options (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_study_design_representatives_have_all_exact_visible_options) ... ok\ntest_study_design_shell_and_exact_opening_assets_are_pinned (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_study_design_shell_and_exact_opening_assets_are_pinned) ... ok\ntest_study_design_source_preserves_parallel_paths_and_boundaries (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_study_design_source_preserves_parallel_paths_and_boundaries) ... ok\ntest_validation_config_resolves_all_concrete_inputs_safely (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_validation_config_resolves_all_concrete_inputs_safely) ... ok\ntest_versions_and_controlled_300_contract_are_exact (n35_checks_test_dashboard_application.DashboardApplicationV2Tests.test_versions_and_controlled_300_contract_are_exact) ... ok\ntest_all_300_paintings_have_exact_canonical_lama_teaching_case (n35_checks_test_dashboard_application.MetricFrameworkSelectionContractTests.test_all_300_paintings_have_exact_canonical_lama_teaching_case) ... ok\ntest_metric_renderer_is_fragment_scoped_and_package_driven (n35_checks_test_dashboard_application.MetricFrameworkSelectionContractTests.test_metric_renderer_is_fragment_scoped_and_package_driven) ... ok\ntest_active_study_renderer_is_a_fragment (n35_checks_test_dashboard_application.StudyDesignInPlaceBridgeTests.test_active_study_renderer_is_a_fragment) ... ok\ntest_approved_foyer_and_study_visual_source_is_byte_stable (n35_checks_test_dashboard_application.StudyDesignInPlaceBridgeTests.test_approved_foyer_and_study_visual_source_is_byte_stable) ... ok\ntest_approved_visitor_overlay_replaces_legacy_tour_without_source_drift (n35_checks_test_dashboard_application.StudyDesignInPlaceBridgeTests.test_approved_visitor_overlay_replaces_legacy_tour_without_source_drift) ... ok\ntest_hidden_button_bridge_and_delegated_controller_are_present (n35_checks_test_dashboard_application.StudyDesignInPlaceBridgeTests.test_hidden_button_bridge_and_delegated_controller_are_present) ... ok\ntest_study_query_callback_uses_atomic_validated_query_updates (n35_checks_test_dashboard_application.StudyDesignInPlaceBridgeTests.test_study_query_callback_uses_atomic_validated_query_updates) ... ok\ntest_visible_selection_anchors_remain_deep_link_fallbacks (n35_checks_test_dashboard_application.StudyDesignInPlaceBridgeTests.test_visible_selection_anchors_remain_deep_link_fallbacks) ... ok\n\n----------------------------------------------------------------------\nRan 29 tests in 3.607s\n\nOK\n",
    "passed": true,
    "request_id": "f6b718d9e027405f8e6187f62bff40b0",
    "subprocess_returncode": 0
  },
  "tests_metric": {
    "group": "metric",
    "run": 25,
    "skipped": 0,
    "failures": 0,
    "errors": 0,
    "excluded_historical_checks": [],
    "current_notebook_source_and_canonical_outputs_unchanged": true,
    "integrity_changes": {
      "notebook_source_changed": false,
      "notebook_source_before": "fb8419577344692a09ca829e81a2449b5b96e5c30c0c66075fe5210c77754522",
      "notebook_source_after": "fb8419577344692a09ca829e81a2449b5b96e5c30c0c66075fe5210c77754522",
      "canonical_output_changes": []
    },
    "remediation": "",
    "network_attempts": [],
    "transcript": "test_arrakis_art_and_surprise_tooltip_cleanup_are_decorative (n35_checks_test_metric_inspection.InspectionControllerTests.test_arrakis_art_and_surprise_tooltip_cleanup_are_decorative) ... ok\ntest_cabinet_icons_and_conservation_study_are_scoped (n35_checks_test_metric_inspection.InspectionControllerTests.test_cabinet_icons_and_conservation_study_are_scoped) ... ok\ntest_cabinet_paper_angles_and_label_offset_are_scoped (n35_checks_test_metric_inspection.InspectionControllerTests.test_cabinet_paper_angles_and_label_offset_are_scoped) ... ok\ntest_cabinet_reuses_shell_drawers_and_reference_style_icons (n35_checks_test_metric_inspection.InspectionControllerTests.test_cabinet_reuses_shell_drawers_and_reference_style_icons) ... ok\ntest_controller_has_fail_closed_state_and_patch_geometry (n35_checks_test_metric_inspection.InspectionControllerTests.test_controller_has_fail_closed_state_and_patch_geometry) ... ok\ntest_dune_binding_is_decorative_and_perspective_aligned (n35_checks_test_metric_inspection.InspectionControllerTests.test_dune_binding_is_decorative_and_perspective_aligned) ... ok\ntest_full_canvas_framing_is_independent_of_selected_region (n35_checks_test_metric_inspection.InspectionControllerTests.test_full_canvas_framing_is_independent_of_selected_region) ... ok\ntest_metric_cosmetics_use_shell_plates_and_scoped_dropdown (n35_checks_test_metric_inspection.InspectionControllerTests.test_metric_cosmetics_use_shell_plates_and_scoped_dropdown) ... ok\ntest_region_icons_and_plaque_content_are_scoped_and_contained (n35_checks_test_metric_inspection.InspectionControllerTests.test_region_icons_and_plaque_content_are_scoped_and_contained) ... ok\ntest_requested_region_icons_keep_grayscale_painting_detail (n35_checks_test_metric_inspection.InspectionControllerTests.test_requested_region_icons_keep_grayscale_painting_detail) ... ok\ntest_second_cosmetic_batch_is_scoped_to_metric_room (n35_checks_test_metric_inspection.InspectionControllerTests.test_second_cosmetic_batch_is_scoped_to_metric_room) ... ok\ntest_changed_map_is_rejected_without_fallback (n35_checks_test_metric_inspection.InspectionExhibitTests.test_changed_map_is_rejected_without_fallback) ... ok\ntest_changed_source_is_rejected_without_fallback (n35_checks_test_metric_inspection.InspectionExhibitTests.test_changed_source_is_rejected_without_fallback) ... ok\ntest_content_geometry_and_sources_are_pinned (n35_checks_test_metric_inspection.InspectionExhibitTests.test_content_geometry_and_sources_are_pinned) ... ok\ntest_every_enabled_pair_has_aligned_evidence_and_nonempty_support (n35_checks_test_metric_inspection.InspectionExhibitTests.test_every_enabled_pair_has_aligned_evidence_and_nonempty_support) ... ok\ntest_invalid_identity_is_rejected (n35_checks_test_metric_inspection.InspectionExhibitTests.test_invalid_identity_is_rejected) ... ok\ntest_mismatched_recipe_is_rejected_without_fallback (n35_checks_test_metric_inspection.InspectionExhibitTests.test_mismatched_recipe_is_rejected_without_fallback) ... ok\ntest_pixel_and_improvement_arithmetic_matches_source_images (n35_checks_test_metric_inspection.InspectionExhibitTests.test_pixel_and_improvement_arithmetic_matches_source_images) ... ok\ntest_all_49_pairs_have_explicit_roles (n35_checks_test_metric_inspection.InspectionPolicyTests.test_all_49_pairs_have_explicit_roles) ... ok\ntest_named_submeasure_is_region_specific (n35_checks_test_metric_inspection.InspectionPolicyTests.test_named_submeasure_is_region_specific) ... ok\ntest_patch_display_uses_real_scores_without_blurring (n35_checks_test_metric_inspection.InspectionPolicyTests.test_patch_display_uses_real_scores_without_blurring) ... ok\ntest_projection_never_stretches_into_another_region (n35_checks_test_metric_inspection.InspectionPolicyTests.test_projection_never_stretches_into_another_region) ... ok\ntest_seam_uses_the_existing_normalized_gradient_convention (n35_checks_test_metric_inspection.InspectionPolicyTests.test_seam_uses_the_existing_normalized_gradient_convention) ... ok\ntest_shared_patch_assignment_matches_dense_nearest_windows (n35_checks_test_metric_inspection.InspectionPolicyTests.test_shared_patch_assignment_matches_dense_nearest_windows) ... ok\ntest_spatial_supports_are_canonical_and_distinct (n35_checks_test_metric_inspection.InspectionPolicyTests.test_spatial_supports_are_canonical_and_distinct) ... ok\n\n----------------------------------------------------------------------\nRan 25 tests in 1.214s\n\nOK\n",
    "passed": true,
    "request_id": "8a63a9680d664786a4d092990c8d1782",
    "subprocess_returncode": 0
  },
  "tests_gallery": {
    "group": "gallery",
    "run": 10,
    "skipped": 0,
    "failures": 0,
    "errors": 0,
    "excluded_historical_checks": [
      "test_notebook_is_not_modified_by_gallery_work"
    ],
    "current_notebook_source_and_canonical_outputs_unchanged": true,
    "integrity_changes": {
      "notebook_source_changed": false,
      "notebook_source_before": "fb8419577344692a09ca829e81a2449b5b96e5c30c0c66075fe5210c77754522",
      "notebook_source_after": "fb8419577344692a09ca829e81a2449b5b96e5c30c0c66075fe5210c77754522",
      "canonical_output_changes": []
    },
    "remediation": "",
    "network_attempts": [],
    "transcript": "unittest.case.FunctionTestCase (run)\ntest_four_methods_share_all_primary_cases ... ok\nunittest.case.FunctionTestCase (run)\ntest_all_paintings_have_declared_opening ... ok\nunittest.case.FunctionTestCase (run)\ntest_invalid_identity_never_silently_substituted ... ok\nunittest.case.FunctionTestCase (run)\ntest_default_matches_registered_candidates_and_measurements ... ok\nunittest.case.FunctionTestCase (run)\ntest_no_empty_mask_crop_values_are_invented ... ok\nunittest.case.FunctionTestCase (run)\ntest_every_case_has_valid_evidence_and_existing_images ... ok\nunittest.case.FunctionTestCase (run)\ntest_sdxl_availability_is_case_scoped ... ok\nunittest.case.FunctionTestCase (run)\ntest_source_reports_retain_recorded_hashes ... ok\nunittest.case.FunctionTestCase (run)\ntest_cases_keep_experiment_identity ... ok\nunittest.case.FunctionTestCase (run)\ntest_frame_content_geometry_is_recorded_and_valid ... ok\n\n----------------------------------------------------------------------\nRan 10 tests in 18.447s\n\nOK\n",
    "passed": true,
    "request_id": "151c78b3ba2348aa99103d55e7b071a1",
    "subprocess_returncode": 0
  },
  "tests_stability": {
    "group": "stability",
    "run": 13,
    "skipped": 0,
    "failures": 0,
    "errors": 0,
    "excluded_historical_checks": [],
    "current_notebook_source_and_canonical_outputs_unchanged": true,
    "integrity_changes": {
      "notebook_source_changed": false,
      "notebook_source_before": "fb8419577344692a09ca829e81a2449b5b96e5c30c0c66075fe5210c77754522",
      "notebook_source_after": "fb8419577344692a09ca829e81a2449b5b96e5c30c0c66075fe5210c77754522",
      "canonical_output_changes": []
    },
    "remediation": "",
    "network_attempts": [],
    "transcript": "test_all_focused_selectors_are_complete (n35_checks_test_stability_lab.StabilityLabTests.test_all_focused_selectors_are_complete) ... ok\ntest_damage_seed_overlays_exist (n35_checks_test_stability_lab.StabilityLabTests.test_damage_seed_overlays_exist) ... ok\ntest_declared_default (n35_checks_test_stability_lab.StabilityLabTests.test_declared_default) ... ok\ntest_decorative_book_spines (n35_checks_test_stability_lab.StabilityLabTests.test_decorative_book_spines) ... ok\ntest_default_disabled_and_explicit_seed_payload (n35_checks_test_stability_lab.StabilityLabTests.test_default_disabled_and_explicit_seed_payload) ... ok\ntest_every_primary_candidate_exists (n35_checks_test_stability_lab.StabilityLabTests.test_every_primary_candidate_exists) ... ok\ntest_opening_trajectory_golden_values (n35_checks_test_stability_lab.StabilityLabTests.test_opening_trajectory_golden_values) ... ok\ntest_p05_uses_the_exact_group_candidate (n35_checks_test_stability_lab.StabilityLabTests.test_p05_uses_the_exact_group_candidate) ... ok\ntest_painting_note_claim_is_selection_specific (n35_checks_test_stability_lab.StabilityLabTests.test_painting_note_claim_is_selection_specific) ... ok\ntest_prompt_groups_are_not_merged (n35_checks_test_stability_lab.StabilityLabTests.test_prompt_groups_are_not_merged) ... ok\ntest_rejects_invalid_scope (n35_checks_test_stability_lab.StabilityLabTests.test_rejects_invalid_scope) ... ok\ntest_seed_membership_is_exact (n35_checks_test_stability_lab.StabilityLabTests.test_seed_membership_is_exact) ... ok\ntest_source_populations (n35_checks_test_stability_lab.StabilityLabTests.test_source_populations) ... ok\n\n----------------------------------------------------------------------\nRan 13 tests in 19.810s\n\nOK\n",
    "passed": true,
    "request_id": "1c129a5340ac47998aaa521b050e32e7",
    "subprocess_returncode": 0
  },
  "tests_trust_portrait": {
    "group": "trust_portrait",
    "run": 28,
    "skipped": 0,
    "failures": 0,
    "errors": 0,
    "excluded_historical_checks": [],
    "current_notebook_source_and_canonical_outputs_unchanged": true,
    "integrity_changes": {
      "notebook_source_changed": false,
      "notebook_source_before": "fb8419577344692a09ca829e81a2449b5b96e5c30c0c66075fe5210c77754522",
      "notebook_source_after": "fb8419577344692a09ca829e81a2449b5b96e5c30c0c66075fe5210c77754522",
      "canonical_output_changes": []
    },
    "remediation": "",
    "network_attempts": [],
    "transcript": "test_all_six_flags_and_unresolved_colour (n35_checks_test_trustworthiness.TrustworthinessTests.test_all_six_flags_and_unresolved_colour) ... ok\ntest_complete_assignment_provenance (n35_checks_test_trustworthiness.TrustworthinessTests.test_complete_assignment_provenance) ... ok\ntest_complete_union_roles (n35_checks_test_trustworthiness.TrustworthinessTests.test_complete_union_roles) ... ok\ntest_exact_opening_identity (n35_checks_test_trustworthiness.TrustworthinessTests.test_exact_opening_identity) ... ok\ntest_exact_threshold_and_registered_stratum (n35_checks_test_trustworthiness.TrustworthinessTests.test_exact_threshold_and_registered_stratum) ... ok\ntest_missing_and_ambiguous_threshold_do_not_pass (n35_checks_test_trustworthiness.TrustworthinessTests.test_missing_and_ambiguous_threshold_do_not_pass) ... ok\ntest_policy_and_images_are_recorded (n35_checks_test_trustworthiness.TrustworthinessTests.test_policy_and_images_are_recorded) ... ok\ntest_primary_peers_exclude_extra_seeds_and_sdxl (n35_checks_test_trustworthiness.TrustworthinessTests.test_primary_peers_exclude_extra_seeds_and_sdxl) ... ok\ntest_seed_identity_is_preserved (n35_checks_test_trustworthiness.TrustworthinessTests.test_seed_identity_is_preserved) ... ok\ntest_unknown_candidate_rejected (n35_checks_test_trustworthiness.TrustworthinessTests.test_unknown_candidate_rejected) ... ok\ntest_book_text_and_icons_share_requested_offsets (n35_checks_test_trustworthiness_presentation.PresentationTests.test_book_text_and_icons_share_requested_offsets) ... ok\ntest_five_titles_and_code_native_icons (n35_checks_test_trustworthiness_presentation.PresentationTests.test_five_titles_and_code_native_icons) ... ok\ntest_portrait_alcove_uses_exact_reference_and_shared_route (n35_checks_test_trustworthiness_presentation.PresentationTests.test_portrait_alcove_uses_exact_reference_and_shared_route) ... ok\ntest_portrait_landscape_square_cover_without_stretching (n35_checks_test_trustworthiness_presentation.PresentationTests.test_portrait_landscape_square_cover_without_stretching) ... ok\ntest_recommendation_tag_keeps_record_and_reference_inspection_icon (n35_checks_test_trustworthiness_presentation.PresentationTests.test_recommendation_tag_keeps_record_and_reference_inspection_icon) ... ok\ntest_reference_window_retains_scene_alignment (n35_checks_test_trustworthiness_presentation.PresentationTests.test_reference_window_retains_scene_alignment) ... ok\ntest_three_reference_button_icons (n35_checks_test_trustworthiness_presentation.PresentationTests.test_three_reference_button_icons) ... ok\ntest_blind_review_exact_note_and_counterexample (n35_checks_test_focused_portrait.FocusedPortraitTests.test_blind_review_exact_note_and_counterexample) ... ok\ntest_exact_opening_and_registered_control (n35_checks_test_focused_portrait.FocusedPortraitTests.test_exact_opening_and_registered_control) ... ok\ntest_hand_and_lightness_summaries_keep_metrics_separate (n35_checks_test_focused_portrait.FocusedPortraitTests.test_hand_and_lightness_summaries_keep_metrics_separate) ... ok\ntest_invalid_identity_and_return_route_rejected (n35_checks_test_focused_portrait.FocusedPortraitTests.test_invalid_identity_and_return_route_rejected) ... ok\ntest_markup_prints_return_and_accessible_controls (n35_checks_test_focused_portrait.FocusedPortraitTests.test_markup_prints_return_and_accessible_controls) ... ok\ntest_mask_variant_keeps_exact_case_and_control (n35_checks_test_focused_portrait.FocusedPortraitTests.test_mask_variant_keeps_exact_case_and_control) ... ok\ntest_recorded_scope_not_annotation_case_conflation (n35_checks_test_focused_portrait.FocusedPortraitTests.test_recorded_scope_not_annotation_case_conflation) ... ok\ntest_reference_details_use_original_pixels_and_guard_recorded_counts (n35_checks_test_focused_portrait.FocusedPortraitTests.test_reference_details_use_original_pixels_and_guard_recorded_counts) ... ok\ntest_report_displays_and_downloads_exact_verified_original (n35_checks_test_focused_portrait.FocusedPortraitTests.test_report_displays_and_downloads_exact_verified_original) ... ok\ntest_retained_lightness_context_and_adjustments (n35_checks_test_focused_portrait.FocusedPortraitTests.test_retained_lightness_context_and_adjustments) ... ok\ntest_review_folio_reference_and_live_navigation (n35_checks_test_focused_portrait.FocusedPortraitTests.test_review_folio_reference_and_live_navigation) ... ok\n\n----------------------------------------------------------------------\nRan 28 tests in 21.044s\n\nOK\n",
    "passed": true,
    "request_id": "265163ebe74a4bc4925e39aa57bb7590",
    "subprocess_returncode": 0
  },
  "tests_case": {
    "group": "case",
    "run": 21,
    "skipped": 0,
    "failures": 0,
    "errors": 0,
    "excluded_historical_checks": [],
    "current_notebook_source_and_canonical_outputs_unchanged": true,
    "integrity_changes": {
      "notebook_source_changed": false,
      "notebook_source_before": "fb8419577344692a09ca829e81a2449b5b96e5c30c0c66075fe5210c77754522",
      "notebook_source_after": "fb8419577344692a09ca829e81a2449b5b96e5c30c0c66075fe5210c77754522",
      "canonical_output_changes": []
    },
    "remediation": "",
    "network_attempts": [],
    "transcript": "test_all_five_opening_images_verified (n35_checks_test_case_explorer.CaseExplorerTests.test_all_five_opening_images_verified) ... ok\ntest_compact_diffusion_ledger_labels_and_neutral_layer_patch (n35_checks_test_case_explorer.CaseExplorerTests.test_compact_diffusion_ledger_labels_and_neutral_layer_patch) ... ok\ntest_content_crop_is_recorded_and_inspection_remains_full_image (n35_checks_test_case_explorer.CaseExplorerTests.test_content_crop_is_recorded_and_inspection_remains_full_image) ... ok\ntest_deterministic_uncertainty_not_zero (n35_checks_test_case_explorer.CaseExplorerTests.test_deterministic_uncertainty_not_zero) ... ok\ntest_each_comparison_choice_is_bound_to_its_saved_candidate (n35_checks_test_case_explorer.CaseExplorerTests.test_each_comparison_choice_is_bound_to_its_saved_candidate) ... ok\ntest_every_original_study_panel_is_present_and_verified (n35_checks_test_case_explorer.CaseExplorerTests.test_every_original_study_panel_is_present_and_verified) ... ok\ntest_exact_report_availability (n35_checks_test_case_explorer.CaseExplorerTests.test_exact_report_availability) ... ok\ntest_exact_review_route (n35_checks_test_case_explorer.CaseExplorerTests.test_exact_review_route) ... ok\ntest_layers_are_distinct_saved_candidate_routes (n35_checks_test_case_explorer.CaseExplorerTests.test_layers_are_distinct_saved_candidate_routes) ... ok\ntest_no_identity_or_map_substitution (n35_checks_test_case_explorer.CaseExplorerTests.test_no_identity_or_map_substitution) ... ok\ntest_opening_identity_and_exact_rows (n35_checks_test_case_explorer.CaseExplorerTests.test_opening_identity_and_exact_rows) ... ok\ntest_other_model_and_diffusion_seed_remain_exact (n35_checks_test_case_explorer.CaseExplorerTests.test_other_model_and_diffusion_seed_remain_exact) ... ok\ntest_random_completion_returns_an_exact_existing_candidate (n35_checks_test_case_explorer.CaseExplorerTests.test_random_completion_returns_an_exact_existing_candidate) ... ok\ntest_reference_control_families_and_shared_thumbnail_source (n35_checks_test_case_explorer.CaseExplorerTests.test_reference_control_families_and_shared_thumbnail_source) ... ok\ntest_reference_lettering_preserves_accessible_controls (n35_checks_test_case_explorer.CaseExplorerTests.test_reference_lettering_preserves_accessible_controls) ... ok\ntest_retrieval_and_counterfactual_population (n35_checks_test_case_explorer.CaseExplorerTests.test_retrieval_and_counterfactual_population) ... ok\ntest_room_has_explicit_limits_and_enabled_exact_reports (n35_checks_test_case_explorer.CaseExplorerTests.test_room_has_explicit_limits_and_enabled_exact_reports) ... ok\ntest_each_room_accepts_only_its_own_query_namespace (n35_checks_test_room_runtime.RoomRuntimeTests.test_each_room_accepts_only_its_own_query_namespace) ... ok\ntest_navigation_is_consumed_once_and_acknowledged (n35_checks_test_room_runtime.RoomRuntimeTests.test_navigation_is_consumed_once_and_acknowledged) ... ok\ntest_render_stamp_is_the_only_markup_change (n35_checks_test_room_runtime.RoomRuntimeTests.test_render_stamp_is_the_only_markup_change) ... ok\ntest_transport_rejects_cross_room_and_malformed_values (n35_checks_test_room_runtime.RoomRuntimeTests.test_transport_rejects_cross_room_and_malformed_values) ... ok\n\n----------------------------------------------------------------------\nRan 21 tests in 3.496s\n\nOK\n",
    "passed": true,
    "request_id": "d2f7f73a8a724f38ab4de3af90f69b7c",
    "subprocess_returncode": 0
  },
  "tests_archive": {
    "group": "archive",
    "run": 16,
    "skipped": 0,
    "failures": 0,
    "errors": 0,
    "excluded_historical_checks": [],
    "current_notebook_source_and_canonical_outputs_unchanged": true,
    "integrity_changes": {
      "notebook_source_changed": false,
      "notebook_source_before": "fb8419577344692a09ca829e81a2449b5b96e5c30c0c66075fe5210c77754522",
      "notebook_source_after": "fb8419577344692a09ca829e81a2449b5b96e5c30c0c66075fe5210c77754522",
      "canonical_output_changes": []
    },
    "remediation": "",
    "network_attempts": [],
    "transcript": "test_all_partitions_check_their_saved_hash (n35_checks_test_research_archive.ResearchArchiveTests.test_all_partitions_check_their_saved_hash) ... ok\ntest_claim_limit_figure_and_check_counts (n35_checks_test_research_archive.ResearchArchiveTests.test_claim_limit_figure_and_check_counts) ... ok\ntest_collections_and_large_files_are_not_materialized (n35_checks_test_research_archive.ResearchArchiveTests.test_collections_and_large_files_are_not_materialized) ... ok\ntest_corrupt_selected_file_fails_closed (n35_checks_test_research_archive.ResearchArchiveTests.test_corrupt_selected_file_fails_closed) ... ok\ntest_exact_figure_bytes_verified (n35_checks_test_research_archive.ResearchArchiveTests.test_exact_figure_bytes_verified) ... ok\ntest_exact_stage_scope_and_default_record (n35_checks_test_research_archive.ResearchArchiveTests.test_exact_stage_scope_and_default_record) ... ok\ntest_invalid_selections_never_fall_back (n35_checks_test_research_archive.ResearchArchiveTests.test_invalid_selections_never_fall_back) ... ok\ntest_lettering_is_the_original_reference_not_regenerated (n35_checks_test_research_archive.ResearchArchiveTests.test_lettering_is_the_original_reference_not_regenerated) ... ok\ntest_markup_and_navigation_contract (n35_checks_test_research_archive.ResearchArchiveTests.test_markup_and_navigation_contract) ... ok\ntest_n33_upstream_identity_is_not_augmented (n35_checks_test_research_archive.ResearchArchiveTests.test_n33_upstream_identity_is_not_augmented) ... ok\ntest_one_painting_partition_only (n35_checks_test_research_archive.ResearchArchiveTests.test_one_painting_partition_only) ... ok\ntest_provenance_and_missingness (n35_checks_test_research_archive.ResearchArchiveTests.test_provenance_and_missingness) ... ok\ntest_publications_are_lazy_and_pinned (n35_checks_test_research_archive.ResearchArchiveTests.test_publications_are_lazy_and_pinned) ... ok\ntest_reference_counts_match_the_frozen_archive (n35_checks_test_research_archive.ResearchArchiveTests.test_reference_counts_match_the_frozen_archive) ... ok\ntest_report_populations_stay_separate (n35_checks_test_research_archive.ResearchArchiveTests.test_report_populations_stay_separate) ... ok\ntest_saved_manifest_verification_and_discrepancy (n35_checks_test_research_archive.ResearchArchiveTests.test_saved_manifest_verification_and_discrepancy) ... ok\n\n----------------------------------------------------------------------\nRan 16 tests in 0.498s\n\nOK\n",
    "passed": true,
    "request_id": "717e991bf13d4347b77a66c6ca8bb7f7",
    "subprocess_returncode": 0
  },
  "n29": {
    "recorded_run_id": "run_ad7603b6bdb14156a140351f6ac1f241",
    "original_commit": "24fefec4a9469e45093fc79b7801469b30151247",
    "correction_commit": "f1e4a460b64755c3ae945d8392e55ba3074bcfb6",
    "cause": "Post-run dataset_scope metadata correction; corrected run records an unreproduced manifest checksum.",
    "metadata_differences": [
      {
        "artifact_key": "explainable_case_retrieval.explanation_cases",
        "field": "dataset_scope",
        "before": "controlled_50",
        "after": "controlled_300"
      },
      {
        "artifact_key": "explainable_case_retrieval.case_neighbors",
        "field": "dataset_scope",
        "before": "controlled_50",
        "after": "controlled_300"
      },
      {
        "artifact_key": "explainable_case_retrieval.counterfactual_panels",
        "field": "dataset_scope",
        "before": "controlled_50",
        "after": "controlled_300"
      },
      {
        "artifact_key": "explainable_case_retrieval.retrieval_panels",
        "field": "dataset_scope",
        "before": "controlled_50",
        "after": "controlled_300"
      },
      {
        "artifact_key": "explainable_case_retrieval.report",
        "field": "dataset_scope",
        "before": "controlled_50",
        "after": "controlled_300"
      },
      {
        "artifact_key": "validation.29_explainable_ai_and_case_retrieval",
        "field": "dataset_scope",
        "before": "controlled_50",
        "after": "controlled_300"
      }
    ],
    "scope_only_correction": true,
    "artifact_checks": [
      {
        "path": "outputs/29_explainable_ai_and_case_retrieval/data/explanation_cases.csv",
        "expected_sha256": "4118b8c573dcb7013751de2e3b1279d8824176eb05ad7656c4007ab24ae37f8b",
        "observed_sha256": "4118b8c573dcb7013751de2e3b1279d8824176eb05ad7656c4007ab24ae37f8b",
        "expected_bytes": 46809964,
        "file_count": 1,
        "size_bytes": 46809964,
        "passed": true
      },
      {
        "path": "outputs/29_explainable_ai_and_case_retrieval/data/case_neighbors.csv",
        "expected_sha256": "6cc63587363dfadd249c32d01dcae76e8ee82d707126a2dbe263c1771ec695fb",
        "observed_sha256": "6cc63587363dfadd249c32d01dcae76e8ee82d707126a2dbe263c1771ec695fb",
        "expected_bytes": 78782,
        "file_count": 1,
        "size_bytes": 78782,
        "passed": true
      },
      {
        "path": "outputs/29_explainable_ai_and_case_retrieval/figures/counterfactual_panels",
        "expected_sha256": "226c15b618afdc9eb60050eb59f68edb698496c21b4c26779a736fb5181a0897",
        "observed_sha256": "226c15b618afdc9eb60050eb59f68edb698496c21b4c26779a736fb5181a0897",
        "expected_bytes": 32660414,
        "file_count": 14,
        "size_bytes": 32660414,
        "passed": true
      },
      {
        "path": "outputs/29_explainable_ai_and_case_retrieval/figures/example_retrieval_panels",
        "expected_sha256": "f5d036698a186dab1284c0172a498b1a0e01edf1980db5ca18c146beec33896e",
        "observed_sha256": "f5d036698a186dab1284c0172a498b1a0e01edf1980db5ca18c146beec33896e",
        "expected_bytes": 27821699,
        "file_count": 10,
        "size_bytes": 27821699,
        "passed": true
      },
      {
        "path": "outputs/29_explainable_ai_and_case_retrieval/reports/explanation_catalog.html",
        "expected_sha256": "135ea78afd827d891093fa636dd493a66ebef8064c63e27d9554fb729005e85d",
        "observed_sha256": "135ea78afd827d891093fa636dd493a66ebef8064c63e27d9554fb729005e85d",
        "expected_bytes": 7795286,
        "file_count": 1,
        "size_bytes": 7795286,
        "passed": true
      },
      {
        "path": "outputs/29_explainable_ai_and_case_retrieval/validation/checks.csv",
        "expected_sha256": "cc104cf4c5f67d21464ed8c6e874a8729a831d3a86601a1c6024276f492f2ddc",
        "observed_sha256": "cc104cf4c5f67d21464ed8c6e874a8729a831d3a86601a1c6024276f492f2ddc",
        "expected_bytes": 37482,
        "file_count": 1,
        "size_bytes": 37482,
        "passed": true
      }
    ],
    "all_payloads_match": true,
    "original_checksum_matches_crlf": true,
    "corrected_recorded_checksum": "5df62a9675e9b6ad214475887378d29043312ca792f33ab0c5c24a7e2ac08a60",
    "current_raw_sha256": "9ec4a9f68a49f724b4f56ed3cf259971013378c39961be2065ce13f5a0438dfa",
    "current_lf_sha256": "c239549fe5e2a2d36ceeef746cd9a7249ef6b11c389816e35d77323fd3f4490f",
    "current_checksum_matches_recorded": false,
    "historical_inputs_modified": false,
    "disposition": "Historical manifest discrepancy retained. All six payload groups independently verified; no historical checksum rewritten.",
    "passed": true
  },
  "remote": {
    "passed": true,
    "samples": [
      {
        "sample": "16_difference_maps_and_spatial_diagnostics",
        "path": "outputs/16_difference_maps_and_spatial_diagnostics/images/maps/stable_diffusion_inpainting/spm_93f2653d2b0f0d3d/spatial_overlay.png",
        "sha256": "9d0042c24811cfde9b09e80bdbbe1df3e31e1432333695207d259267a9cd4788",
        "expected": "9d0042c24811cfde9b09e80bdbbe1df3e31e1432333695207d259267a9cd4788",
        "passed": true,
        "request_count": 1,
        "downloaded_bytes": 1851881,
        "elapsed_seconds": 1.094
      },
      {
        "sample": "17_local_consistency_metrics",
        "path": "outputs/17_local_consistency_metrics/images/maps/stable_diffusion_inpainting/lcm_eaedbf71364d3618/seam.png",
        "sha256": "234a19b20b2c5b15a88a1ba99a08ea2a1772199d9f0f5d998aa37b4497dcb0aa",
        "expected": "234a19b20b2c5b15a88a1ba99a08ea2a1772199d9f0f5d998aa37b4497dcb0aa",
        "passed": true,
        "request_count": 1,
        "downloaded_bytes": 156318,
        "elapsed_seconds": 0.828
      },
      {
        "sample": "19_uncertainty_and_spatial_explanation_maps",
        "path": "outputs/19_uncertainty_and_spatial_explanation_maps/images/overlays/stable_diffusion_inpainting/ug_be1aa74f6a1e2d4110.png",
        "sha256": "ae8cb1eb1b0cc410ceccae53cd7a4b12fa1436be8745239993eb01e551288c99",
        "expected": "ae8cb1eb1b0cc410ceccae53cd7a4b12fa1436be8745239993eb01e551288c99",
        "passed": true,
        "request_count": 1,
        "downloaded_bytes": 1664805,
        "elapsed_seconds": 0.906
      },
      {
        "sample": "20_semantic_and_structural_consistency",
        "path": "outputs/20_semantic_and_structural_consistency/images/maps/stable_diffusion_inpainting/sd15__p00__s2026__f432b593be16/semantic.png",
        "sha256": "9001d42c8848bb8c7e59cf758ff4f3c84237df58fbb8cd369eeb6cfa210fabf5",
        "expected": "9001d42c8848bb8c7e59cf758ff4f3c84237df58fbb8cd369eeb6cfa210fabf5",
        "passed": true,
        "request_count": 1,
        "downloaded_bytes": 1838707,
        "elapsed_seconds": 1.032
      },
      {
        "sample": "22_damage_size_diffusion_uncertainty_extension_candidate",
        "path": "outputs/22_damage_size_diffusion_uncertainty_extension/images/restored/damage_size__p123__loss_large__size_15pct/sd15dsu__61f59b2559115e8e.png",
        "sha256": "198139434aac7a91385efdb446a222fc9c3d92d358f8e8fc9e768807f3271de0",
        "expected": "198139434aac7a91385efdb446a222fc9c3d92d358f8e8fc9e768807f3271de0",
        "passed": true,
        "request_count": 1,
        "downloaded_bytes": 9049282,
        "elapsed_seconds": 1.218
      },
      {
        "sample": "22_damage_size_diffusion_uncertainty_extension_diagnostic",
        "path": "outputs/22_damage_size_diffusion_uncertainty_extension/images/uncertainty/ug_68c527381c82bc61f8.png",
        "sha256": "73964db1d2d3b40d44ed53f72cd3e9a5462335e461e17c0b6a84435adc45daff",
        "expected": "73964db1d2d3b40d44ed53f72cd3e9a5462335e461e17c0b6a84435adc45daff",
        "passed": true,
        "request_count": 1,
        "downloaded_bytes": 5987098,
        "elapsed_seconds": 1.141
      },
      {
        "sample": "individual",
        "path": "outputs/16_difference_maps_and_spatial_diagnostics/manifests/artifacts.csv",
        "sha256": "2ce015c934585847131637c0c38116ba0a5fd43236f43c51af79431f0d4da924",
        "expected": "2ce015c934585847131637c0c38116ba0a5fd43236f43c51af79431f0d4da924",
        "passed": true,
        "request_count": 1,
        "downloaded_bytes": 2152,
        "elapsed_seconds": 0.406
      },
      {
        "sample": "metric_companions",
        "path": "streamlit_assets/evidence/metric_framework/p074/seam.png",
        "sha256": "7ca0b5e300fe414fbaa8c342328fb49a20be53b2c48a8401cc842e9874681bde",
        "expected": "7ca0b5e300fe414fbaa8c342328fb49a20be53b2c48a8401cc842e9874681bde",
        "passed": true,
        "request_count": 1,
        "downloaded_bytes": 717315,
        "elapsed_seconds": 0.766
      },
      {
        "sample": "n32_report",
        "path": "outputs/32_case_and_painting_report_generation/reports/index.html",
        "sha256": "9fe8de9540abe566eef5ca1212d6af8deb93c71849ca7ccfebbe4d5a2f066518",
        "expected": "9fe8de9540abe566eef5ca1212d6af8deb93c71849ca7ccfebbe4d5a2f066518",
        "passed": true,
        "request_count": 1,
        "downloaded_bytes": 339916,
        "elapsed_seconds": 0.281
      }
    ],
    "scope": "Selected HF immutable reads; Git/LFS checkout and live-site behavior require separate checks",
    "request_id": "c67a5eb9922c42a9bb330f0d4e5800ac",
    "subprocess_returncode": 0
  },
  "github": {
    "passed": true,
    "samples": [
      {
        "sample": "git_blob",
        "path": "requirements.txt",
        "revision": "cf64ab2b4e8b3b90598dbd4b3b6a7ee983eb35f8",
        "sha256": "3a84f6c0d53234f791dad31818d6bd989f4ddbc92bb94bfc52cb1fe0b38d78da",
        "expected": "3a84f6c0d53234f791dad31818d6bd989f4ddbc92bb94bfc52cb1fe0b38d78da",
        "passed": true
      },
      {
        "sample": "git_lfs",
        "path": "outputs/02_image_preprocessing/images/clean/p018.png",
        "revision": "cf64ab2b4e8b3b90598dbd4b3b6a7ee983eb35f8",
        "sha256": "3e223322b3ca2c6f52ebe54a266991be897dd8d6c670ad52393f3262e15574ac",
        "expected": "3e223322b3ca2c6f52ebe54a266991be897dd8d6c670ad52393f3262e15574ac",
        "passed": true
      }
    ],
    "scope": "Pinned public Git blob and LFS-byte availability; not a Linux checkout or new deployment",
    "request_id": "9218ef5578a848fdbb5698bde13ded7a",
    "subprocess_returncode": 0
  },
  "opening_exhibition_foyer": {
    "room": "exhibition_foyer",
    "passed": true,
    "errors": [],
    "elapsed_seconds": 3.39,
    "simulated_missing_paths": [],
    "network_attempts": [],
    "remote_enabled": true,
    "request_count": 0,
    "downloaded_bytes": 0,
    "scope": "Fresh-process Python render; not browser, Linux, or live-deployment certification",
    "request_id": "455cdf1aa9534b088730e66cf311d10e",
    "subprocess_returncode": 0
  },
  "opening_study_design": {
    "room": "study_design",
    "passed": true,
    "errors": [],
    "elapsed_seconds": 3.875,
    "simulated_missing_paths": [],
    "network_attempts": [],
    "remote_enabled": true,
    "request_count": 0,
    "downloaded_bytes": 0,
    "scope": "Fresh-process Python render; not browser, Linux, or live-deployment certification",
    "request_id": "1ca461c5368046b4b55253129a16510a",
    "subprocess_returncode": 0
  },
  "opening_metric_framework": {
    "room": "metric_framework",
    "passed": true,
    "errors": [],
    "elapsed_seconds": 4.891,
    "simulated_missing_paths": [
      "streamlit_assets/evidence/metric_framework/p018/affinity_content.png",
      "streamlit_assets/evidence/metric_framework/p018/affinity_crop.png",
      "streamlit_assets/evidence/metric_framework/p018/affinity_patches.png",
      "streamlit_assets/evidence/metric_framework/p018/affinity_whole.png",
      "streamlit_assets/evidence/metric_framework/p018/change.png",
      "streamlit_assets/evidence/metric_framework/p018/clip_content.png",
      "streamlit_assets/evidence/metric_framework/p018/clip_crop.png",
      "streamlit_assets/evidence/metric_framework/p018/clip_patches.png",
      "streamlit_assets/evidence/metric_framework/p018/clip_whole.png",
      "streamlit_assets/evidence/metric_framework/p018/colour.png",
      "streamlit_assets/evidence/metric_framework/p018/dino_content.png",
      "streamlit_assets/evidence/metric_framework/p018/dino_crop.png",
      "streamlit_assets/evidence/metric_framework/p018/dino_patches.png",
      "streamlit_assets/evidence/metric_framework/p018/dino_whole.png",
      "streamlit_assets/evidence/metric_framework/p018/improvement.png",
      "streamlit_assets/evidence/metric_framework/p018/improvement_patches.png",
      "streamlit_assets/evidence/metric_framework/p018/lpips_content.png",
      "streamlit_assets/evidence/metric_framework/p018/lpips_crop.png",
      "streamlit_assets/evidence/metric_framework/p018/lpips_patches.png",
      "streamlit_assets/evidence/metric_framework/p018/lpips_whole.png",
      "streamlit_assets/evidence/metric_framework/p018/manifest.json",
      "streamlit_assets/evidence/metric_framework/p018/pixel.png",
      "streamlit_assets/evidence/metric_framework/p018/pixel_patches.png",
      "streamlit_assets/evidence/metric_framework/p018/seam.png",
      "streamlit_assets/evidence/metric_framework/p018/ssim_content.png",
      "streamlit_assets/evidence/metric_framework/p018/ssim_crop.png",
      "streamlit_assets/evidence/metric_framework/p018/ssim_patches.png",
      "streamlit_assets/evidence/metric_framework/p018/ssim_whole.png",
      "streamlit_assets/evidence/metric_framework/p018/support_boundary.png",
      "streamlit_assets/evidence/metric_framework/p018/support_content.png",
      "streamlit_assets/evidence/metric_framework/p018/support_crop.png",
      "streamlit_assets/evidence/metric_framework/p018/support_damaged.png",
      "streamlit_assets/evidence/metric_framework/p018/support_outside.png",
      "streamlit_assets/evidence/metric_framework/p018/support_patches.png",
      "streamlit_assets/evidence/metric_framework/p018/support_whole.png",
      "streamlit_assets/evidence/metric_framework/p018/texture.png",
      "streamlit_assets/evidence/metric_framework/p018/texture_patches.png"
    ],
    "network_attempts": [],
    "remote_enabled": true,
    "request_count": 0,
    "downloaded_bytes": 0,
    "scope": "Fresh-process Python render; not browser, Linux, or live-deployment certification",
    "request_id": "175bb531b06c40a78fba65acf4c77ce3",
    "subprocess_returncode": 0
  },
  "opening_model_gallery": {
    "room": "model_gallery",
    "passed": true,
    "errors": [],
    "elapsed_seconds": 14.0,
    "simulated_missing_paths": [
      "outputs/12_sdxl_feasibility_or_restoration/images/restored/canonical_missing_region/canonical__p018__mixed_damage/sdxl__5d3f1bc4bed2__p00_generic__seed2026.png",
      "outputs/12a_hint_restoration/images/restored/canonical_missing_region/canonical__p018__mixed_damage.png"
    ],
    "network_attempts": [],
    "remote_enabled": true,
    "request_count": 0,
    "downloaded_bytes": 0,
    "scope": "Fresh-process Python render; not browser, Linux, or live-deployment certification",
    "request_id": "aeea7e01007c4aaab7d702b09bdd3221",
    "subprocess_returncode": 0
  },
  "opening_stability_lab": {
    "room": "stability_lab",
    "passed": true,
    "errors": [],
    "elapsed_seconds": 13.047,
    "simulated_missing_paths": [],
    "network_attempts": [],
    "remote_enabled": true,
    "request_count": 0,
    "downloaded_bytes": 0,
    "scope": "Fresh-process Python render; not browser, Linux, or live-deployment certification",
    "request_id": "1de77581297c46beb75e55002a7e44b2",
    "subprocess_returncode": 0
  },
  "opening_trustworthiness": {
    "room": "trustworthiness",
    "passed": true,
    "errors": [],
    "elapsed_seconds": 21.89,
    "simulated_missing_paths": [],
    "network_attempts": [],
    "remote_enabled": true,
    "request_count": 0,
    "downloaded_bytes": 0,
    "scope": "Fresh-process Python render; not browser, Linux, or live-deployment certification",
    "request_id": "cd3bce8826bd43ada384116c119ce449",
    "subprocess_returncode": 0
  },
  "opening_focused_portrait_review": {
    "room": "focused_portrait_review",
    "passed": true,
    "errors": [],
    "elapsed_seconds": 5.281,
    "simulated_missing_paths": [
      "outputs/12a_hint_restoration/images/restored/canonical_missing_region/canonical__p269__mixed_damage.png"
    ],
    "network_attempts": [],
    "remote_enabled": true,
    "request_count": 0,
    "downloaded_bytes": 0,
    "scope": "Fresh-process Python render; not browser, Linux, or live-deployment certification",
    "request_id": "467c7766596c40d2b035709a65c20107",
    "subprocess_returncode": 0
  },
  "opening_case_explorer": {
    "room": "case_explorer",
    "passed": true,
    "errors": [],
    "elapsed_seconds": 4.64,
    "simulated_missing_paths": [
      "outputs/16_difference_maps_and_spatial_diagnostics/images/maps/lama/spm_e5f9511cc6c7d95a/masked_signed_improvement.png"
    ],
    "network_attempts": [],
    "remote_enabled": true,
    "request_count": 0,
    "downloaded_bytes": 0,
    "scope": "Fresh-process Python render; not browser, Linux, or live-deployment certification",
    "request_id": "57b6a7e3654d4c90bdd75b5e26cd3f7b",
    "subprocess_returncode": 0
  },
  "opening_research_archive": {
    "room": "research_archive",
    "passed": true,
    "errors": [],
    "elapsed_seconds": 3.5,
    "simulated_missing_paths": [],
    "network_attempts": [],
    "remote_enabled": true,
    "request_count": 0,
    "downloaded_bytes": 0,
    "scope": "Fresh-process Python render; not browser, Linux, or live-deployment certification",
    "request_id": "289dd1d35aea4d9cad8e0efb03214db7",
    "subprocess_returncode": 0
  },
  "performance_exhibition_foyer": {
    "passed": true,
    "room": "exhibition_foyer",
    "cold_seconds": 3.0,
    "warm_seconds": [
      0.4370000000053551,
      0.4379999999946449,
      0.4370000000053551,
      0.46900000001187436,
      0.4379999999946449
    ],
    "warm_p95_seconds": 0.46900000001187436,
    "max_sampled_rss_bytes": 166346752,
    "errors": [],
    "network_attempts": [],
    "scope": "Fresh local Python process, five same-room warm rerenders; sampled RSS, not OS peak RSS or browser navigation p95",
    "request_id": "aca84385f098445cb78fbd395c820b06",
    "subprocess_returncode": 0
  },
  "performance_study_design": {
    "passed": true,
    "room": "study_design",
    "cold_seconds": 3.48499999998603,
    "warm_seconds": [
      0.875,
      0.8900000000139698,
      0.9059999999881256,
      0.9070000000065193,
      0.875
    ],
    "warm_p95_seconds": 0.9070000000065193,
    "max_sampled_rss_bytes": 235708416,
    "errors": [],
    "network_attempts": [],
    "scope": "Fresh local Python process, five same-room warm rerenders; sampled RSS, not OS peak RSS or browser navigation p95",
    "request_id": "c89616f3d1be4e32994f843214afa3fc",
    "subprocess_returncode": 0
  },
  "performance_metric_framework": {
    "passed": true,
    "room": "metric_framework",
    "cold_seconds": 4.078000000008615,
    "warm_seconds": [
      1.312999999994645,
      1.3589999999967404,
      1.2969999999913853,
      1.3440000000118744,
      1.327999999979511
    ],
    "warm_p95_seconds": 1.3589999999967404,
    "max_sampled_rss_bytes": 268963840,
    "errors": [],
    "network_attempts": [],
    "scope": "Fresh local Python process, five same-room warm rerenders; sampled RSS, not OS peak RSS or browser navigation p95",
    "request_id": "3de9cf4f96924b6c9c8712b35a8d66f4",
    "subprocess_returncode": 0
  },
  "performance_model_gallery": {
    "passed": true,
    "room": "model_gallery",
    "cold_seconds": 13.719000000011874,
    "warm_seconds": [
      0.7969999999913853,
      0.7969999999913853,
      0.8120000000053551,
      0.8440000000118744,
      0.8129999999946449
    ],
    "warm_p95_seconds": 0.8440000000118744,
    "max_sampled_rss_bytes": 328790016,
    "errors": [],
    "network_attempts": [],
    "scope": "Fresh local Python process, five same-room warm rerenders; sampled RSS, not OS peak RSS or browser navigation p95",
    "request_id": "0153a5e141c04013827f717a72717b62",
    "subprocess_returncode": 0
  },
  "performance_stability_lab": {
    "passed": true,
    "room": "stability_lab",
    "cold_seconds": 12.875,
    "warm_seconds": [
      1.0780000000086147,
      1.0939999999827705,
      1.0780000000086147,
      1.0940000000118744,
      1.1089999999967404
    ],
    "warm_p95_seconds": 1.1089999999967404,
    "max_sampled_rss_bytes": 332148736,
    "errors": [],
    "network_attempts": [],
    "scope": "Fresh local Python process, five same-room warm rerenders; sampled RSS, not OS peak RSS or browser navigation p95",
    "request_id": "9a8af001646f415d9f998537e63593f0",
    "subprocess_returncode": 0
  },
  "performance_trustworthiness": {
    "passed": true,
    "room": "trustworthiness",
    "cold_seconds": 21.40600000001723,
    "warm_seconds": [
      1.3599999999860302,
      1.3429999999934807,
      1.375,
      1.360000000015134,
      1.375
    ],
    "warm_p95_seconds": 1.375,
    "max_sampled_rss_bytes": 391913472,
    "errors": [],
    "network_attempts": [],
    "scope": "Fresh local Python process, five same-room warm rerenders; sampled RSS, not OS peak RSS or browser navigation p95",
    "request_id": "80d7923e4123414f99a51f4096ff1af3",
    "subprocess_returncode": 0
  },
  "performance_focused_portrait_review": {
    "passed": true,
    "room": "focused_portrait_review",
    "cold_seconds": 4.797000000020489,
    "warm_seconds": [
      1.0159999999741558,
      1.0,
      1.0,
      0.9840000000258442,
      1.0
    ],
    "warm_p95_seconds": 1.0159999999741558,
    "max_sampled_rss_bytes": 265375744,
    "errors": [],
    "network_attempts": [],
    "scope": "Fresh local Python process, five same-room warm rerenders; sampled RSS, not OS peak RSS or browser navigation p95",
    "request_id": "c5e87f6ea34645979ec4c95aba5c8005",
    "subprocess_returncode": 0
  },
  "performance_case_explorer": {
    "passed": true,
    "room": "case_explorer",
    "cold_seconds": 3.9690000000118744,
    "warm_seconds": [
      1.2339999999967404,
      1.2339999999967404,
      1.2039999999979045,
      1.2030000000086147,
      1.2179999999934807
    ],
    "warm_p95_seconds": 1.2339999999967404,
    "max_sampled_rss_bytes": 279068672,
    "errors": [],
    "network_attempts": [],
    "scope": "Fresh local Python process, five same-room warm rerenders; sampled RSS, not OS peak RSS or browser navigation p95",
    "request_id": "2f039f7bdf6e4db48cb0a92d2935d022",
    "subprocess_returncode": 0
  },
  "performance_research_archive": {
    "passed": true,
    "room": "research_archive",
    "cold_seconds": 3.125,
    "warm_seconds": [
      0.5309999999881256,
      0.5310000000172295,
      0.5309999999881256,
      0.5320000000065193,
      0.5150000000139698
    ],
    "warm_p95_seconds": 0.5320000000065193,
    "max_sampled_rss_bytes": 200151040,
    "errors": [],
    "network_attempts": [],
    "scope": "Fresh local Python process, five same-room warm rerenders; sampled RSS, not OS peak RSS or browser navigation p95",
    "request_id": "6f677c2df2794d08a17c02f3448aeae7",
    "subprocess_returncode": 0
  },
  "checkpoint_helper_tests": {
    "passed": true,
    "returncode": 0,
    "stdout": "Running suite trust_portrait\nNotebook SOURCE changed during validation. Save all cells, then rerun without editing.\nRunning suite trust_portrait\n",
    "stderr": "test_automated_blocker_cannot_be_deferred (test_n35_batch10.Batch10Tests.test_automated_blocker_cannot_be_deferred) ... ok\ntest_checkpoint_cells_parse_and_do_not_invent_passes (test_n35_batch10.Batch10Tests.test_checkpoint_cells_parse_and_do_not_invent_passes) ... ok\ntest_checkpoint_keeps_unknown_gates_blocking_without_mutating_collector (test_n35_batch10.Batch10Tests.test_checkpoint_keeps_unknown_gates_blocking_without_mutating_collector) ... ok\ntest_complete_cells_parse (test_n35_batch10.Batch10Tests.test_complete_cells_parse) ... ok\ntest_default_readiness_still_requires_manual_evidence (test_n35_batch10.Batch10Tests.test_default_readiness_still_requires_manual_evidence) ... ok\ntest_detailed_manual_pass_preserved (test_n35_batch10.Batch10Tests.test_detailed_manual_pass_preserved) ... ok\ntest_exact_helper_delta_reconciliation_only (test_n35_batch10.Batch10Tests.test_exact_helper_delta_reconciliation_only) ... ok\ntest_failed_promotion_restores_prior_run (test_n35_batch10.Batch10Tests.test_failed_promotion_restores_prior_run) ... ok\ntest_fresh_failure_keeps_structured_diagnostics (test_n35_batch10.Batch10Tests.test_fresh_failure_keeps_structured_diagnostics) ... ok\ntest_incomplete_staging_never_replaces_old_run (test_n35_batch10.Batch10Tests.test_incomplete_staging_never_replaces_old_run) ... ok\ntest_manual_observations_never_default_to_pass (test_n35_batch10.Batch10Tests.test_manual_observations_never_default_to_pass) ... ok\ntest_no_notebook_execution_or_publication_in_cells (test_n35_batch10.Batch10Tests.test_no_notebook_execution_or_publication_in_cells) ... ok\ntest_original_frozen_sources_are_not_rebaselined (test_n35_batch10.Batch10Tests.test_original_frozen_sources_are_not_rebaselined) ... ok\ntest_partial_persistence_records_real_pending_state (test_n35_batch10.Batch10Tests.test_partial_persistence_records_real_pending_state) ... ok\ntest_promotion_preserves_old_run (test_n35_batch10.Batch10Tests.test_promotion_preserves_old_run) ... ok\ntest_stale_success_receipt_is_rejected (test_n35_batch10.Batch10Tests.test_stale_success_receipt_is_rejected) ... ok\ntest_unsafe_target_rejected (test_n35_batch10.Batch10Tests.test_unsafe_target_rejected) ... ok\ntest_user_approval_cannot_override_explicit_failure (test_n35_batch10.Batch10Tests.test_user_approval_cannot_override_explicit_failure) ... ok\n\n----------------------------------------------------------------------\nRan 18 tests in 1.947s\n\nOK\n",
    "scope": "Current closeout helper tests only; earlier runtime receipts retained",
    "original_validation_fingerprint": {
      "streamlit_app.py": "8b726d82161065132989345fbc1b701b96416161882353c041fdfda7dcb90b3e",
      "src/restoration_eval/__init__.py": "5f29d3f8445de0380f1501edf13f36337ee9af31ad6e5780afc32e309cddbf89",
      "src/restoration_eval/bundled_assets.py": "780cc8a3d1c617baf125810b7af0a385568ecd6916f132a256d827ba8ab5a1a0",
      "src/restoration_eval/case_explorer.py": "f40c13d0b68954c7cc1213524c44ccde46b1d9d8db6e3ab1088d43232993e7f6",
      "src/restoration_eval/case_explorer_view.py": "8f917e3a5ad9ab0acaa44c487f9a59e212c2028643a7079c58015536788f84c4",
      "src/restoration_eval/case_painting_reports.py": "db7165757dfa39ed611b31ceb750f3ecc4e991e9e25082327c127e2ad58e5f5d",
      "src/restoration_eval/damage.py": "94038b352241f811597b2b9d65aa247ca0e6a88391385c6c10facc2788dc87d3",
      "src/restoration_eval/damage_sensitivity.py": "7620138fa523da6b5e9d0a7b9059f5be3e44fcc5a3ca599753820e9f8756a463",
      "src/restoration_eval/damage_size_analysis.py": "0889208c6f46c7bb1d3c83c2b7c5ade7367e22aa6b5485db4d528fa38059f553",
      "src/restoration_eval/damage_size_diffusion_uncertainty.py": "086feeb40c61188037596f76200c9d071637048ca2f31c1843fdb36b233d0c02",
      "src/restoration_eval/dashboard_application.py": "a0f33a133a04ef14f84ab1ff32054e0153573d792e246529b72c50aa66815cd4",
      "src/restoration_eval/dashboard_assets.py": "33211dd1a067e5cd61fd783db2542f6af5a88bf7a88c1c70f3ed056ec7eaca2b",
      "src/restoration_eval/dashboard_metrics.py": "ed09e64486621fd2e9fedf0adaa5335ccd5ba4e8ae4c9bc1c1e0fccb685c7cec",
      "src/restoration_eval/dataset_verification.py": "4536eff1568fbb38f488e58364e9e6ff8a729a31430a94d78117c84f20a9e268",
      "src/restoration_eval/diffusion_uncertainty.py": "34837b12a5b89394f717f70dcaefb6d53e2e3d86b9f241a1028c260e2f1bbc14",
      "src/restoration_eval/error_maps.py": "594e116fb5a03df3d3de4cb6300ed8dbbea72793941dc995930fc2c92add0de3",
      "src/restoration_eval/evaluation_inputs.py": "b2f1c46df69f0ebdf9fa78dee1449f08bac54de0c4b4e3f096b4d981d57e13cb",
      "src/restoration_eval/evidence_transport.py": "5e042a76eb5c74621e125af565a29318bd798688356bf3d0d9840c79bb5c887d",
      "src/restoration_eval/experiment_contracts.py": "040095c1c3c4a7eb9d25c9db42608e9c0a55d8956a3faba4dcefa939bbb18434",
      "src/restoration_eval/explainable_case_retrieval.py": "66c4dedd7d95255d58bab136b7d21f3df67c9778ac39cf572c7875ef894a25fb",
      "src/restoration_eval/failure_taxonomy.py": "8dde75496a95df675383527be752f67778275d90cd87fc81d3844a062d01e0a5",
      "src/restoration_eval/final_evaluation_report.py": "9113f6a2f1295ed4bbcf64d11ce9d602902835d9d84c7074aa422efedfba3daf",
      "src/restoration_eval/focused_portrait.py": "61a8885c8e80b39b4dcf534eac56da6484c68d07d2ef2849595d9f081300038b",
      "src/restoration_eval/focused_portrait_view.py": "cd6754bbfd58a4c891291d108756608d5a5beaaf67b88b8df3a3e4b7d2676f5a",
      "src/restoration_eval/grouped_statistical_analysis.py": "9d10d40f64df02f8df93aa6faf0df4014c87853a65611c5407291be8930521d0",
      "src/restoration_eval/hint_mat_selection.py": "a7ba0bd8bceba45cd70a55f53c5243a4d218f3bc9eb1ce2cfd6ebdab9c942e31",
      "src/restoration_eval/io_utils.py": "3a10563e1e84470d70c97fb5f22cf0c8efabc084c0f2107e90240585c35dafb1",
      "src/restoration_eval/local_consistency.py": "e7ec4e23c5b79d3f8cac789f7b847cfa1e44fa489ecc1f4be9ff61582dfc676b",
      "src/restoration_eval/manifests.py": "8ba9846539a63ca14becdf5bb5488204917476169e847233489f0012d5703217",
      "src/restoration_eval/mask_robustness.py": "3983614098b5e393a4999de461341893a00a2098bc735780400bcdc65a48e451",
      "src/restoration_eval/mask_robustness_analysis.py": "1679e7e64a062beeae3a039e931953de1a7797859d00a9974b8dcf57b5be1f21",
      "src/restoration_eval/masks.py": "8d6b99b42a878d516c353723b2ba8a34b6067299e9c42924d3f448cc2f653a7d",
      "src/restoration_eval/metric_inspection.py": "c7e3173b7be2822e4ae81d8193777494712d94b6b7365afc67416c5f990ce5a0",
      "src/restoration_eval/metric_inspection_view.py": "095f6c5443daa560b7bed5f13c42fba9ef62471aae3c35d13a0ab166cb412f25",
      "src/restoration_eval/metric_region_ablation.py": "88edf517092e66cc5acaccbbc6ee2e6c129d4069267e5747d3c3ef006916f821",
      "src/restoration_eval/metrics_classical.py": "67f709cf69706e342d9c65913600d67aa0fe7f506c1910cd3e65007379401b3e",
      "src/restoration_eval/metrics_feature_similarity.py": "3d35cef889c390cadd0a1e7bc8a442f769c31293757fa9e70f7fe684a466976c",
      "src/restoration_eval/metrics_lpips.py": "489d55d55300fb2b51aa9620ddc03990e78dba60f7f9490532948ff35e26a633",
      "src/restoration_eval/model_cards_compute.py": "0dc2c6084bb7aa49d1e2e9cf382f7bd54f50faf33a7d3416fc058057b7670447",
      "src/restoration_eval/model_gallery.py": "1dab2158f28106a7a751e0eb9a6571fc3b3a631901f13c08c6472b575c3e30fb",
      "src/restoration_eval/model_gallery_view.py": "a52f9050b8307bb5fd11b9bc4dd3ddf64ff2c4f28b9bd8da4b3b348a7c2952e3",
      "src/restoration_eval/model_report_generation.py": "1ff753f2a3e60c1731ef311c503a4050ee3d4d9d8288d7f5e81402bdd6c56a15",
      "src/restoration_eval/multi_model_comparison.py": "8a05cfecaf3681d0190a6e19dc7292d7bec8ba79892340ac0726c59d3647d879",
      "src/restoration_eval/museum_visit.py": "1633327079215c8543b0d525408a9900b4fa6823da0485be54e3680b6e36328b",
      "src/restoration_eval/paths.py": "d84d77df3fa24870289700c0bd06c00dda425a43fdd960b175b897ec1e9adf0a",
      "src/restoration_eval/portrait_anatomy_audit.py": "73e67d7f3a388b05029422fcd99ecb924fa395e285e606215bfa48a4295ad174",
      "src/restoration_eval/preprocessing.py": "74a8f2ed7d3ce178075b8c6ba13804baa6be9b558a95eb76b17e1d06b1f3d4cd",
      "src/restoration_eval/regions.py": "8b0c9d413ecba9e5056b3b8f6cd89147d4cfd044291290e31ebc78b882a16e9d",
      "src/restoration_eval/reporting.py": "97c7655aa321066f74c2130eac4afce6dffd342d9ff837d8bc7270e79fe6577a",
      "src/restoration_eval/research_archive.py": "3268afdd28f0b11df9187df308b4eb29ee0263dd6356a15e3fb4c96deb37c975",
      "src/restoration_eval/research_archive_view.py": "cdd5328fbcefd56f391eae162561ad1410b01047141f5c2d23c5cfd803977d9c",
      "src/restoration_eval/restoration_hint.py": "33e57571e1ac811829c629dbabb79c52e39e0ecdf82c58cd800d4696dff3f610",
      "src/restoration_eval/restoration_hint_production_worker.py": "e6d6ac8ca12363d2234e521107336a076c025279a40f23fccf6afe6ee2a8d644",
      "src/restoration_eval/restoration_hint_worker.py": "0fdde724c5aac6e3dc946497875b7e73df54fbc3d7a9aa855df11997c1377a1a",
      "src/restoration_eval/restoration_lama.py": "f2a44e47d4acc195eb275f197613d6c230dd71711fc8461686a008c37e24846c",
      "src/restoration_eval/restoration_mat_worker.py": "7acb77175c995d0c9740ef3221b203749f4414878668956797ce41ff9b1b22c4",
      "src/restoration_eval/restoration_opencv.py": "85279e42cb1ae222a3d5714af616d952923f3344065658eb1cba60e963d641fc",
      "src/restoration_eval/restoration_sdxl.py": "dfb951fb2153072393ecafc504827a2666871dcfcee67329261e1e4e77a11fd1",
      "src/restoration_eval/restoration_sdxl_worker.py": "73ecc945547afa58fb94d16c263a22537d0cea4465e454473be50a049361740f",
      "src/restoration_eval/restoration_stable_diffusion.py": "15a3490dec0b430c9ee2236ad8e612bef839d82bce59b6528738ab2c3e5a682d",
      "src/restoration_eval/restoration_stable_diffusion_scratch_prompt.py": "0696c58cf2bdd91c5ba6ca3725a3a7bb6bb84462e929ae1198fe4d24af3f8102",
      "src/restoration_eval/restoration_stable_diffusion_scratch_prompt_contract.py": "de7acc78bb3fcfaab1c747028693a68f1d41256afbfe8f79ba6ebdf5c699ff2a",
      "src/restoration_eval/room_runtime.py": "16d7110776c7f2d97365eddb397e5fc1056f8bbdfc493c637bb2dbd355f43a28",
      "src/restoration_eval/schemas.py": "9f9de787e5958f71d097e9f4ddd83a4f6cbdde7744aa82c1690082e93e87951a",
      "src/restoration_eval/semantic_structural.py": "2281f784b073ed57c97998ffefcd904a6ec5ee8a2e79590f04e56be050e91893",
      "src/restoration_eval/spatial_explanations.py": "0d702c46be109cadaf752f75f211e5be088e817123a4c027b23d4a5947e124e9",
      "src/restoration_eval/stability_lab.py": "ecec922e722db3065d91db21ba06afcccfb08718d2dba9d8ce9ee0cbe321b8ea",
      "src/restoration_eval/stability_lab_view.py": "e9adeb931173b8f6e9e12344a15c58423af0e178934b460860deb293f7fba0b8",
      "src/restoration_eval/supervisor_package.py": "2bb895394d22696b8dc24c5c0f7c97449f28cde55ba9eabcbe19f663f364716f",
      "src/restoration_eval/synthetic_degradation.py": "f563d2eb11084bbbcc82a78cdb4133e2eea9f71023b7739d1b58b101f1d452f8",
      "src/restoration_eval/synthetic_degradation_analysis.py": "dbda379613bdc7eaa71957f216a6ab8ee73c4c5060a4b8f7c11a4c4abfa08756",
      "src/restoration_eval/trustworthiness.py": "a56d99fbc826426fd667fe761c909c10f880a04f58fabae76c7a3c984ae5c377",
      "src/restoration_eval/trustworthiness_view.py": "e477503061e07d9000bfad2e706774ede31bb9524c85136f99e0a07e3053451e",
      "src/restoration_eval/validation.py": "1311f816879b60e8314364686e2136eb906ff3718ccf7b6106a3e73f04e09a10",
      "streamlit_assets/case_explorer.css": "9ac66f2c9eeaadf871bc27bc93bf7b0615bac60f8f272037733bc34d51929079",
      "streamlit_assets/focused_portrait.css": "2e2d4a39023e2a6fa6b5c0d5141bd6477a093c03d3759487177ac22ee700d23a",
      "streamlit_assets/model_gallery.css": "e15922f2231df238a406b3818ddc7a966569f2d5132c6536e2f69b7953a9c3e4",
      "streamlit_assets/museum_visit/visit.css": "bf6de1fb52bf9a92db0d37dbc309526f31fad2a879ba27b060a8dd0c82fe7414",
      "streamlit_assets/research_archive.css": "5e136d3002eeaf87f0f0c1c0f16eaa5d944b904d1377846d89f50039a24b8891",
      "streamlit_assets/stability_lab.css": "af9d9c185f6c91c8e501b5587011faa00b38bbb66f8128b55d6020ee57720ed1",
      "streamlit_assets/trustworthiness.css": "2aad3dc52e5cc2d28230c5e3b08f4b2a46144b8da44cd8f4fe094af34f5210b0",
      "streamlit_assets/case_explorer_controller.js": "614228b7b780129db55ed15a5f86920cd51ca7d5165c91a8309ce032223fcd13",
      "streamlit_assets/focused_portrait_controller.js": "e15b9e153e9dabca707195c982f0c482673acc4fbe14ca0ee7a096c41fe5b694",
      "streamlit_assets/metric_controller.js": "78a72abcc96886ffe361844d55ad331803b3b97a6ed86ff03db5994ed7eb3d5c",
      "streamlit_assets/model_gallery_controller.js": "827fd2a683f6d722d7867e98c1a7bf49d76241a916a6a047d86684ab40324419",
      "streamlit_assets/museum_visit/controller.js": "955e39cde0e79a8b7f873ffae3f9a1d9db126d982578aa02c8aaef74456b48c5",
      "streamlit_assets/research_archive_controller.js": "156373e66dcaa824c3fc1c0939d0334b926dcd3c0dd341879ee68e77aed39121",
      "streamlit_assets/room_runtime/navigation.js": "68e3c21042254d694bb94c97cc1fb1b32a6637f259e4d0c97aeb400907e3e2f8",
      "streamlit_assets/room_runtime/readiness.js": "499370c3d43fc54efbd4b0eb180b11b626c8581dd42bbb4b8067c31680e8ad85",
      "streamlit_assets/stability_lab_controller.js": "80efc9f2ce57d7ae8f07e5975b718eb502f69cdf38c03e6d6af1664c4038e4b1",
      "streamlit_assets/trustworthiness_controller.js": "575f2c62e7baefaa85824609404fba1d5827002467c0d6b0155b125f4d187c0e",
      "streamlit_assets/evidence/deployment/manifest.json": "78409827803363a5129108e5814ef97d8ae0bf6676e8b032b149cac772549866",
      "config/publication/n35_backend_delta.json": "c5e3110cf227d5a0ada46493e243f28f0074f5a02fb39c476f929c17765ba6a9",
      "requirements.txt": "3a84f6c0d53234f791dad31818d6bd989f4ddbc92bb94bfc52cb1fe0b38d78da",
      "config/evaluation/dashboard_validation.yaml": "7dcd490c3d3cb3cc5b8f804026b7dc15e503ee53e7e9173de0feb27513badad2",
      "tools/n35_backend_delta.py": "0445451cb46ff048af1ebfbd60068c46ef57135341bca10f3f79c42be529d1f5",
      "tools/n35_batch10.py": "9e38fc65f3a165ee95f28cd14703180ce04e4bcca40bfc027342c926a9054a1c",
      "tools/n35_deployment_checks.py": "b4de0b92ad45f1fd3c0ca068d01601749910dab6e1b616404c2a21d10cc1d082",
      "tools/n35_final_audit.py": "6a70507160f2a6097a9c7e29c6003ceda2c6133384eed5d97e2962b74be3b8a5",
      "tools/n35_room_validation.py": "8aa8de90e33921e9eb7618c5f2aeac8ab95d1724432ef67a736454965fd2b985",
      "tools/prepare_n35_batch10_cells.py": "46fd5961778c910daa251a56f39116233ba3cb74a6e49d238276da5ffb9e6706",
      "tools/prepare_n35_batch2_cells.py": "de69b1c0e1111c2f2c4b2270ca708588ca99cc101d1246717ceda791660e63f8",
      "tools/prepare_n35_batches3_5_cells.py": "722ad83e151ab89c508427e10832294126c4ae5588df9c7beae42973003794cf",
      "tools/prepare_n35_batches6_9_cells.py": "a9b4b8508fd72137795de0ec83505220ad5388661fda754850c6b206d3f22339",
      "tools/prepare_n35_deployment.py": "53333df84dba046f5ebf31c70d84143fe793684617fe50ec29089018974cb76e",
      "tests/test_evidence_transport.py": "5349ee8dcc51b9314cd7d8f346bc12b4febe608a8c7f2e02966f3f776f2ca4b6",
      "tests/test_n35_batch10.py": "5d91214154e566b484207bab2c3fcfc9aca614033d0b108d8788e6d38bfadafc"
    },
    "closeout_helper_delta": {
      "tests/test_n35_batch10.py": [
        "5d91214154e566b484207bab2c3fcfc9aca614033d0b108d8788e6d38bfadafc",
        "17227a72ab8d7d745f81f75ce7cf389019324c67a3c08315393fbfc2a8627680"
      ],
      "tools/n35_batch10.py": [
        "9e38fc65f3a165ee95f28cd14703180ce04e4bcca40bfc027342c926a9054a1c",
        "b161b504970c3e5013bb2d29309eaf1bfee2149b73de19e289f7efd49019bf90"
      ],
      "tools/prepare_n35_batch10_cells.py": [
        "46fd5961778c910daa251a56f39116233ba3cb74a6e49d238276da5ffb9e6706",
        "c89cb430459a676a2115b273e3f483015d8fd65feb42155cdb8eccee838ebbe0"
      ]
    }
  },
  "checkpoint_gate": {
    "passed": true,
    "scope": "Automated receipt completeness and partial checkpoint eligibility ONLY",
    "user_approval": "User reported: 'everything works perfectly, no need to change anything'. Qualitative local approval only; no per-check measurement or observation time inferred.",
    "pending_qualifications": [
      "desktop_1672x941_all_rooms",
      "tablet_1024x1366_all_rooms",
      "mobile_390x844_all_rooms",
      "keyboard_focus_and_dialogs",
      "firefox_reload_and_second_monitor",
      "same_room_no_document_reload",
      "cross_room_links_and_guided_tour",
      "downloaded_reports_open_self_contained",
      "browser_warm_navigation_p95",
      "remote_action_budget_and_peak_memory"
    ],
    "all_qualifications_passed": false,
    "deployment_state": "not_yet_validated",
    "deployment_url": "",
    "next_batch": 11
  }
}
```

## Browser/platform observations

```json
{
  "desktop_1672x941_all_rooms": {
    "passed": null,
    "evidence": "",
    "observed_at_utc": ""
  },
  "tablet_1024x1366_all_rooms": {
    "passed": null,
    "evidence": "",
    "observed_at_utc": ""
  },
  "mobile_390x844_all_rooms": {
    "passed": null,
    "evidence": "",
    "observed_at_utc": ""
  },
  "keyboard_focus_and_dialogs": {
    "passed": null,
    "evidence": "",
    "observed_at_utc": ""
  },
  "firefox_reload_and_second_monitor": {
    "passed": null,
    "evidence": "",
    "observed_at_utc": ""
  },
  "same_room_no_document_reload": {
    "passed": null,
    "evidence": "",
    "observed_at_utc": ""
  },
  "cross_room_links_and_guided_tour": {
    "passed": null,
    "evidence": "",
    "observed_at_utc": ""
  },
  "downloaded_reports_open_self_contained": {
    "passed": null,
    "evidence": "",
    "observed_at_utc": ""
  },
  "browser_warm_navigation_p95": {
    "passed": null,
    "evidence": "",
    "observed_at_utc": ""
  },
  "remote_action_budget_and_peak_memory": {
    "passed": null,
    "evidence": "",
    "observed_at_utc": ""
  }
}
```
