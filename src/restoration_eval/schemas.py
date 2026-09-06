"""Versioned dataframe and mapping schema contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


SCHEMAS_MODULE_VERSION = "1.18.0"
SCHEMA_REGISTRY_VERSION = "schema_registry.v1"

RUN_MANIFEST_REQUIRED_KEYS = (
    "run_id",
    "notebook_id",
    "notebook_name",
    "origin",
    "run_status",
    "started_at_utc",
    "completed_at_utc",
    "git_commit",
    "git_dirty",
    "inventory_run_id",
    "dataset_versions",
    "configuration_paths",
    "configuration_checksums",
    "helper_versions",
    "python_version",
    "package_versions",
    "hardware",
    "inputs",
    "outputs",
    "expected_counts",
    "observed_counts",
    "validation_summary",
    "known_limitations",
)

ARTIFACT_MANIFEST_COLUMNS = (
    "artifact_id",
    "artifact_key",
    "producer_notebook",
    "artifact_type",
    "artifact_role",
    "relative_path",
    "format",
    "dataset_scope",
    "experiment_id",
    "schema_version",
    "row_count",
    "file_count",
    "size_bytes",
    "checksum",
    "validation_status",
)

VALIDATION_CHECK_COLUMNS = (
    "validation_stage",
    "check_id",
    "check_description",
    "severity",
    "expected",
    "observed",
    "passed",
    "details",
)

RAW_ARTWORK_METADATA_COLUMNS = (
    "painting_id", "category", "title", "artist", "date",
    "style_or_period", "medium", "source", "source_url", "license",
    "filename", "original_width", "original_height", "selection_reason",
    "visual_complexity_note", "status", "notes",
)

ARTWORKS_COLUMNS = (
    "dataset_id", "dataset_version", "dataset_scope", "painting_id",
    "dataset_sort_index", "title", "artist", "date_or_period",
    "style_or_period", "category", "medium", "source", "source_url",
    "license", "rights_status", "source_selection_status", "raw_image_path",
    "raw_filename", "raw_width", "raw_height", "raw_mode", "raw_format",
    "raw_size_bytes", "raw_sha256", "raw_dhash64", "raw_exif_orientation",
    "raw_icc_profile_present", "raw_icc_profile_description",
    "metadata_completeness_pct", "prompt_metadata_field_count",
    "prompt_metadata_status", "selection_reason", "visual_complexity_note",
    "source_notes", "acceptance_status", "exclusion_reason",
)

DATASET_AUDIT_COLUMNS = (
    "audit_row_id", "dataset_id", "dataset_version", "dataset_scope",
    "audit_section", "group_field", "group_value", "metric_name",
    "metric_value", "metric_unit", "numerator", "denominator", "status",
    "details",
)

PREPROCESSED_IMAGES_COLUMNS = (
    "dataset_id", "dataset_version", "dataset_scope", "processed_image_id",
    "painting_id", "dataset_sort_index", "source_path", "source_sha256",
    "processed_filename", "processed_path", "original_width",
    "original_height", "width", "height", "mode", "format", "size_bytes",
    "sha256", "resize_scale", "resized_width", "resized_height",
    "interpolation", "pad_left", "pad_top", "pad_right", "pad_bottom",
    "padding_method", "padding_color_r", "padding_color_g",
    "padding_color_b", "content_x_min", "content_y_min", "content_x_max",
    "content_y_max", "content_width", "content_height",
    "content_area_pixels", "padding_area_pixels", "canvas_area_pixels",
    "content_area_fraction", "padding_area_fraction", "source_orientation",
    "orientation_policy", "input_icc_profile_status", "color_space_policy",
    "output_icc_profile_present", "coordinate_convention",
    "preprocessing_method", "preprocessing_version", "status",
)

PREPROCESSING_AUDIT_COLUMNS = (
    "audit_row_id", "dataset_id", "dataset_version", "dataset_scope",
    "audit_section", "group_field", "group_value", "metric_name",
    "metric_value", "metric_unit", "numerator", "denominator", "status",
    "details",
)

CANONICAL_MASKS_COLUMNS = (
    "dataset_id", "dataset_version", "dataset_scope", "experiment_id",
    "case_id", "painting_id", "processed_image_id",
    "processed_image_path", "processed_image_sha256", "mask_id",
    "mask_type", "mask_type_index", "mask_filename", "mask_path",
    "generator_name", "generator_version", "config_schema_version",
    "config_version", "preset_id", "preset_version",
    "seed_scheme_version", "global_seed", "painting_seed", "mask_seed",
    "retry_seed", "maximum_generation_attempts", "generation_attempts",
    "accepted_attempt", "retry_policy",
    "target_damaged_content_fraction", "lower_damaged_content_fraction",
    "upper_damaged_content_fraction",
    "distance_to_target_fraction", "distance_to_allowed_range_fraction",
    "generator_parameters", "morphology_settings", "content_x_min",
    "content_y_min", "content_x_max", "content_y_max", "content_width",
    "content_height", "content_area_pixels", "padding_area_pixels",
    "canvas_area_pixels", "damaged_pixel_count",
    "damaged_content_pixel_count", "padding_overlap_pixels",
    "damaged_content_fraction", "damaged_full_fraction", "bbox_x_min",
    "bbox_y_min", "bbox_x_max", "bbox_y_max", "bbox_width",
    "bbox_height", "bbox_area_pixels", "bbox_fill_ratio",
    "bbox_aspect_ratio", "connected_component_count",
    "largest_component_pixels", "smallest_component_pixels",
    "mean_component_pixels", "median_component_pixels",
    "component_area_std_pixels", "component_area_cv",
    "largest_component_fraction",
    "component_density_per_100k_content_pixels",
    "mean_component_aspect_ratio", "maximum_component_aspect_ratio",
    "mask_perimeter_pixels", "mask_compactness", "touches_content_boundary",
    "minimum_distance_to_content_boundary_pixels", "mask_width",
    "mask_height", "mask_mode", "mask_format", "mask_size_bytes",
    "mask_sha256", "mask_unique_values", "binary_values_valid",
    "zero_control_rule_valid", "content_only_valid",
    "area_within_target_tolerance", "morphology_status",
    "generation_status", "status", "issue",
)

MASK_AUDIT_COLUMNS = (
    "audit_row_id", "dataset_id", "dataset_version", "dataset_scope",
    "experiment_id", "audit_section", "group_field", "group_value",
    "comparison_group_value", "metric_name", "metric_value",
    "metric_unit", "numerator", "denominator", "status", "details",
)

CANONICAL_DAMAGE_CASES_COLUMNS = (
    "dataset_id", "dataset_version", "dataset_scope", "experiment_id",
    "case_id", "painting_id", "processed_image_id", "mask_id",
    "mask_type", "damaged_image_id", "clean_image_path", "mask_path",
    "damaged_image_path", "clean_image_sha256", "mask_sha256",
    "damaged_image_sha256", "fill_strategy", "fill_color_r",
    "fill_color_g", "fill_color_b", "mask_pixel_count",
    "damaged_filename", "width", "height", "mode", "format",
    "size_bytes", "generator_name", "generator_version",
    "config_schema_version", "config_version", "generation_status",
    "status", "issue",
)

CANONICAL_DAMAGE_AUDIT_COLUMNS = (
    "dataset_id", "dataset_version", "dataset_scope", "experiment_id",
    "case_id", "painting_id", "mask_id", "mask_type",
    "clean_file_exists", "mask_file_exists", "damaged_file_exists",
    "reload_passed", "clean_width", "clean_height", "mask_width",
    "mask_height", "damaged_width", "damaged_height", "dimensions_match",
    "mask_unique_values", "binary_values_valid", "total_mask_pixels",
    "metadata_mask_pixels", "mask_pixel_count_difference",
    "preexisting_fill_pixel_count", "expected_changed_pixel_count",
    "observed_changed_pixel_count", "changed_pixel_count_difference",
    "outside_mask_changed_pixel_count", "inside_mask_not_fill_pixel_count",
    "clean_equals_damaged", "zero_control_valid", "clean_sha256_matches",
    "mask_sha256_matches", "damaged_sha256_matches", "damaged_mode",
    "damaged_format", "output_contract_valid", "validation_status", "issue",
)

DAMAGE_SIZE_CASES_COLUMNS = (
    "dataset_id", "dataset_version", "dataset_scope", "experiment_id",
    "case_id", "painting_id", "processed_image_id", "base_mask_id",
    "base_mask_type", "level_id", "mask_or_effect_id", "damaged_image_id",
    "input_image_path", "clean_image_path", "base_mask_path",
    "mask_or_effect_path", "target_damage_fraction", "target_damage_pixels",
    "realized_damage_fraction", "realized_damage_pixels",
    "absolute_percentage_point_error", "scale_factor",
    "pre_correction_pixels", "correction_added_pixels",
    "correction_removed_pixels", "previous_level_id", "previous_mask_id",
    "nested_with_previous", "seed_scheme_version", "global_seed", "case_seed",
    "damage_or_degradation_type", "fill_strategy", "fill_color_r",
    "fill_color_g", "fill_color_b", "clean_image_sha256", "base_mask_sha256",
    "mask_sha256", "damaged_image_sha256", "width", "height", "mask_mode",
    "damaged_mode", "format", "mask_size_bytes", "damaged_size_bytes",
    "generator_name", "generator_version", "config_schema_version",
    "config_version", "source_manifest_path", "generation_status", "status",
    "issue",
)

DAMAGE_SIZE_GENERATION_AUDIT_COLUMNS = (
    "dataset_id", "dataset_version", "dataset_scope", "experiment_id",
    "case_id", "painting_id", "level_id", "mask_or_effect_id",
    "previous_level_id", "target_damage_fraction", "target_damage_pixels",
    "realized_damage_fraction", "realized_damage_pixels",
    "absolute_percentage_point_error", "area_within_tolerance",
    "scale_factor", "pre_correction_pixels", "correction_added_pixels",
    "correction_removed_pixels", "base_centroid_x", "base_centroid_y",
    "scaled_centroid_x", "scaled_centroid_y", "centroid_shift_pixels",
    "centroid_shift_fraction_of_content_diagonal",
    "base_bbox_aspect_ratio", "scaled_bbox_aspect_ratio",
    "relative_bbox_aspect_ratio_drift", "base_bbox_fill_ratio",
    "scaled_bbox_fill_ratio", "relative_bbox_fill_ratio_drift",
    "base_mask_perimeter_pixels", "scaled_mask_perimeter_pixels",
    "base_mask_compactness", "scaled_mask_compactness",
    "relative_compactness_drift", "base_connected_component_count",
    "scaled_connected_component_count", "component_count_delta",
    "base_largest_component_fraction", "scaled_largest_component_fraction",
    "largest_component_fraction_drift", "touches_content_boundary",
    "minimum_distance_to_content_boundary_pixels", "nested_with_previous",
    "previous_pixels_removed", "pixels_added_from_previous",
    "clean_file_exists", "base_mask_file_exists", "mask_file_exists",
    "damaged_file_exists", "reload_passed", "dimensions_match",
    "mask_unique_values", "binary_values_valid", "content_only_valid",
    "metadata_mask_pixels_match", "outside_mask_changed_pixel_count",
    "inside_mask_not_fill_pixel_count", "clean_sha256_matches",
    "base_mask_sha256_matches", "mask_sha256_matches",
    "damaged_sha256_matches", "output_contract_valid",
    "morphology_preservation_status", "validation_status", "issue",
)

MASK_ROBUSTNESS_CASES_COLUMNS = (
    "dataset_id", "dataset_version", "dataset_scope", "experiment_id",
    "case_id", "robustness_group_id", "variant_id", "variant_index",
    "painting_id", "category", "processed_image_id", "mask_id",
    "mask_type", "family_index", "target_token", "damaged_image_id",
    "clean_image_path", "mask_path", "damaged_image_path",
    "target_damage_fraction", "target_damage_pixels",
    "realized_damage_fraction", "realized_damage_pixels",
    "absolute_percentage_point_error", "raw_mask_pixels", "scale_factor",
    "pre_correction_pixels", "correction_added_pixels",
    "correction_removed_pixels", "content_x_min", "content_y_min",
    "content_x_max", "content_y_max", "content_width", "content_height",
    "content_area_pixels", "centroid_x_pixels", "centroid_y_pixels",
    "centroid_x_normalized_content", "centroid_y_normalized_content",
    "centroid_quadrant", "bbox_x_min", "bbox_y_min", "bbox_x_max",
    "bbox_y_max", "bbox_width", "bbox_height", "bbox_fill_ratio",
    "bbox_aspect_ratio", "connected_component_count",
    "largest_component_fraction", "component_area_cv",
    "mask_perimeter_pixels", "mask_compactness", "touches_content_boundary",
    "minimum_distance_to_content_boundary_pixels", "seed_scheme_version",
    "global_seed", "painting_seed", "group_seed", "variant_seed",
    "generation_seed", "generation_attempt", "fill_strategy",
    "fill_color_r", "fill_color_g", "fill_color_b", "clean_image_sha256",
    "mask_pixel_sha256", "mask_sha256", "damaged_image_sha256", "width",
    "height", "mask_mode", "damaged_mode", "format", "mask_size_bytes",
    "damaged_size_bytes", "generator_name", "generator_version",
    "config_schema_version", "config_version", "source_manifest_path",
    "generation_status", "status", "issue",
)

MASK_ROBUSTNESS_GENERATION_AUDIT_COLUMNS = (
    "dataset_id", "dataset_version", "dataset_scope", "experiment_id",
    "case_id", "robustness_group_id", "variant_id", "painting_id",
    "mask_type", "target_damage_fraction", "target_damage_pixels",
    "realized_damage_fraction", "realized_damage_pixels",
    "absolute_percentage_point_error", "area_within_tolerance",
    "centroid_x_normalized_content", "centroid_y_normalized_content",
    "centroid_quadrant", "bbox_width", "bbox_height", "bbox_fill_ratio",
    "bbox_aspect_ratio", "connected_component_count",
    "largest_component_fraction", "component_area_cv",
    "mask_perimeter_pixels", "mask_compactness", "touches_content_boundary",
    "minimum_distance_to_content_boundary_pixels", "group_variant_count",
    "group_unique_pixel_sha256_count", "group_unique_mask_count_passed",
    "nearest_variant_id", "maximum_pairwise_iou", "minimum_pairwise_iou",
    "minimum_pairwise_centroid_distance_fraction",
    "group_centroid_span_fraction_of_content_diagonal",
    "group_morphology_signature_count",
    "group_component_arrangement_signature_count",
    "pairwise_iou_passed", "location_variation_passed",
    "morphology_variation_passed", "component_arrangement_variation_passed",
    "family_morphology_passed", "clean_file_exists", "mask_file_exists",
    "damaged_file_exists", "reload_passed", "dimensions_match",
    "mask_unique_values", "binary_values_valid", "content_only_valid",
    "metadata_mask_pixels_match", "outside_mask_changed_pixel_count",
    "inside_mask_not_fill_pixel_count", "clean_sha256_matches",
    "mask_pixel_sha256_matches", "mask_sha256_matches",
    "damaged_sha256_matches", "output_contract_valid", "group_gate_passed",
    "validation_status", "issue",
)

SYNTHETIC_DEGRADATION_CASES_COLUMNS = (
    "dataset_id", "dataset_version", "dataset_scope", "experiment_id",
    "case_id", "degradation_id", "painting_id", "category",
    "processed_image_id", "degradation_family", "severity",
    "severity_rank", "is_combined", "component_degradations_json",
    "component_count", "operator_sequence_json", "clean_image_path",
    "effect_mask_path", "degraded_image_path", "spatial_support_type",
    "support_threshold", "active_threshold", "content_x_min",
    "content_y_min", "content_x_max", "content_y_max", "content_width",
    "content_height", "content_area_pixels", "width", "height",
    "affected_support_pixels", "affected_active_pixels",
    "affected_content_fraction", "changed_pixels",
    "changed_content_fraction", "outside_support_changed_pixels",
    "mean_absolute_rgb_difference", "mean_rgb_colour_distance",
    "mean_luminance_shift", "mean_saturation_shift",
    "gradient_energy_ratio", "laplacian_variance_ratio",
    "seed_scheme_version", "global_seed", "case_seed",
    "effect_mask_seed", "operator_seeds_json", "operator_parameters_json",
    "clean_image_sha256", "effect_mask_sha256", "degraded_image_sha256",
    "effect_mask_size_bytes", "degraded_image_size_bytes",
    "effect_mask_mode", "degraded_mode", "format", "generator_name",
    "generator_version", "config_schema_version", "config_version",
    "source_manifest_path", "generation_status", "status", "issue",
)

SYNTHETIC_DEGRADATION_GENERATION_AUDIT_COLUMNS = (
    "dataset_id", "dataset_version", "dataset_scope", "experiment_id",
    "case_id", "degradation_id", "painting_id", "degradation_family",
    "severity", "is_combined", "clean_file_exists",
    "effect_mask_file_exists", "degraded_file_exists", "reload_passed",
    "dimensions_match", "effect_mask_mode_valid", "degraded_mode_valid",
    "format_valid", "content_only_valid", "parameters_recorded",
    "seeds_recorded", "affected_support_pixels_match",
    "affected_active_pixels_match", "changed_pixels_match",
    "changed_pixels_within_support", "outside_support_changed_pixels",
    "clean_sha256_matches", "effect_mask_sha256_matches",
    "degraded_image_sha256_matches", "clean_reference_unchanged",
    "impact_metrics_finite", "output_contract_valid",
    "validation_status", "issue",
)

CASE_REGISTRY_COLUMNS = (
    "case_id", "dataset_id", "dataset_scope", "experiment_id",
    "painting_id", "input_image_path", "clean_image_path",
    "mask_or_effect_id", "mask_or_effect_path",
    "damage_or_degradation_type", "target_damage_fraction",
    "realized_damage_fraction", "source_manifest_path", "status",
)

MODEL_ELIGIBILITY_COLUMNS = (
    "case_id", "model_id", "eligible", "eligibility_reason",
    "input_semantics", "mask_semantics", "restoration_objective",
)

RESTORATIONS_COLUMNS = (
    "restoration_id", "case_id", "model_id", "candidate_id",
    "candidate_index", "seed", "prompt_policy_id", "model_version",
    "opencv_version",
    "configuration_id", "algorithm", "inpaint_radius",
    "mask_threshold", "execution_action", "restored_path",
    "input_sha256", "mask_sha256", "restored_sha256",
    "runtime_seconds", "device", "precision", "execution_backend",
    "cpu_environment", "retry_count", "generator_name",
    "generator_version", "started_at_utc", "completed_at_utc",
    "status", "issue",
)

RESTORATION_RUNTIME_SUMMARY_COLUMNS = (
    "summary_scope", "experiment_id", "case_count", "completed_count",
    "failed_count", "total_runtime_seconds", "mean_runtime_seconds",
    "median_runtime_seconds", "p95_runtime_seconds",
    "max_runtime_seconds", "throughput_cases_per_second", "status",
)

STABLE_DIFFUSION_CANDIDATE_COLUMNS = (
    "candidate_id", "candidate_index", "case_id", "painting_id",
    "category", "experiment_id", "damage_or_degradation_type",
    "mask_or_effect_id", "input_image_path", "clean_image_path",
    "mask_or_effect_path", "input_sha256", "mask_sha256", "model_id",
    "hf_model_id", "model_revision", "configuration_id",
    "prompt_policy_id", "prompt_variant_id", "prompt", "negative_prompt",
    "prompt_metadata_fields_used", "seed", "execution_role",
    "is_primary_candidate", "is_prompt_ablation_candidate",
    "is_uncertainty_candidate", "candidate_selection_policy",
    "num_inference_steps", "guidance_scale", "strength", "scheduler",
    "precision", "device", "inference_width", "inference_height",
    "output_width", "output_height", "mask_threshold",
    "compositing_policy", "safety_checker_policy", "execution_action",
    "restored_path", "restored_sha256", "runtime_seconds",
    "gpu_memory_before_bytes", "gpu_memory_after_bytes",
    "gpu_peak_memory_bytes", "retry_count", "attempt_count",
    "configuration_fingerprint", "started_at_utc", "completed_at_utc",
    "generator_name", "generator_version", "status", "issue",
)

SDXL_FEASIBILITY_ATTEMPT_COLUMNS = (
    "attempt_id", "attempt_index", "evidence_origin", "case_id",
    "painting_id", "experiment_id", "damage_or_degradation_type",
    "input_image_path", "mask_or_effect_path", "input_sha256",
    "mask_sha256", "model_id", "hf_model_id", "model_revision",
    "configuration_id", "configuration_fingerprint", "prompt_policy_id",
    "prompt", "negative_prompt", "seed", "requested_device",
    "actual_device", "gpu_name", "gpu_total_memory_bytes", "precision",
    "inference_width", "inference_height", "output_width", "output_height",
    "num_inference_steps", "guidance_scale", "strength", "scheduler",
    "memory_strategy_id", "model_cpu_offload", "sequential_cpu_offload",
    "attention_backend", "attention_slicing", "vae_slicing", "vae_tiling",
    "local_files_only", "timeout_seconds", "model_load_succeeded",
    "inference_started", "inference_completed", "timed_out",
    "output_generated", "output_geometry_valid",
    "outside_mask_changed_pixels", "technical_validation_passed",
    "model_load_seconds", "inference_seconds", "runtime_seconds",
    "gpu_peak_memory_bytes", "projected_primary_hours",
    "projected_comparable_hours", "availability_state", "status",
    "failure_type", "worker_return_code", "error_type", "error_message",
    "issue",
)
SDXL_PARTIAL_CANDIDATE_COLUMNS = (
    "candidate_id", "candidate_index", "selection_rank", "execution_order",
    "case_id", "painting_id", "category", "experiment_id",
    "damage_or_degradation_type", "mask_or_effect_id", "input_image_path",
    "clean_image_path", "mask_or_effect_path", "input_sha256", "mask_sha256",
    "model_id", "hf_model_id", "model_revision", "configuration_id",
    "prompt_policy_id", "prompt_variant_id", "prompt", "negative_prompt",
    "prompt_metadata_fields_used", "seed", "execution_role",
    "candidate_selection_policy", "num_inference_steps", "guidance_scale",
    "strength", "scheduler", "precision", "device", "inference_width",
    "inference_height", "output_width", "output_height", "mask_policy_id",
    "mask_threshold", "compositing_policy", "safety_checker_policy",
    "execution_action", "restored_path", "restored_sha256", "runtime_seconds",
    "model_load_seconds", "inference_seconds", "gpu_total_memory_bytes",
    "gpu_memory_before_bytes", "gpu_memory_after_bytes", "gpu_peak_memory_bytes",
    "global_budget_seconds", "per_case_timeout_seconds",
    "budget_seconds_before_attempt", "budget_seconds_after_attempt",
    "output_geometry_valid", "outside_mask_changed_pixels",
    "technical_validation_passed", "retry_count", "attempt_count",
    "configuration_fingerprint", "started_at_utc", "completed_at_utc",
    "generator_name", "generator_version", "availability_state", "status",
    "failure_type", "worker_return_code", "error_type", "error_message", "issue",
)
PROMPT_POLICY_COLUMNS = (
    "prompt_policy_id", "prompt_variant_id", "variant_order",
    "variant_family", "is_primary", "requires_metadata",
    "metadata_fields", "prompt_template", "negative_prompt", "status",
)

PROMPT_ABLATION_DESIGN_COLUMNS = (
    "design_row_id", "case_id", "painting_id", "category",
    "experiment_id", "damage_or_degradation_type", "design_component",
    "selection_policy", "selection_rank", "prompt_variant_count",
    "seed_count", "included", "status",
)

REGION_POLICY_COLUMNS = (
    "policy_id", "policy_version", "metric_family", "region_id",
    "region_type", "spatial_support", "compatible",
    "compatibility_reason", "primary_role", "case_semantics",
    "parameters_json", "threshold_policy", "minimum_size_policy",
    "ablation_policy_ids_json", "status",
)
CLASSICAL_METRICS_COLUMNS = (
    "metric_row_id", "case_id", "candidate_id", "model_id",
    "metric_family", "metric_name", "region_id", "region_pixel_count",
    "damaged_value", "restored_value", "improvement_value",
    "improvement_direction", "metric_version", "region_policy_version",
    "status", "issue",
)
LPIPS_METRICS_COLUMNS = (
    "metric_row_id", "case_id", "candidate_id", "model_id",
    "metric_family", "metric_name", "region_id", "region_pixel_count",
    "region_width", "region_height", "input_width", "input_height",
    "resize_policy", "damaged_value", "restored_value", "improvement_value",
    "improvement_direction", "network", "metric_version",
    "region_policy_version", "schema_version", "device",
    "lpips_package_version", "metric_runtime_seconds", "status", "issue",
)
FEATURE_METRICS_COLUMNS = (
    "metric_row_id", "case_id", "candidate_id", "model_id",
    "metric_family", "metric_name", "feature_model_id", "region_id",
    "region_pixel_count", "region_width", "region_height",
    "damaged_embedding_id", "restored_embedding_id", "clean_embedding_id",
    "damaged_value", "restored_value", "improvement_value",
    "improvement_direction", "metric_version", "region_policy_version",
    "preprocessing_id", "input_size", "model_name", "model_revision",
    "model_checksum", "schema_version", "device", "package_version",
    "status", "issue",
)
FEATURE_EMBEDDING_MANIFEST_COLUMNS = (
    "embedding_id", "feature_model_id", "image_role", "painting_id",
    "case_id", "representative_candidate_id", "region_id", "source_path",
    "source_sha256", "array_name", "array_index", "embedding_dimension",
    "dtype", "preprocessing_id", "input_width", "input_height",
    "model_name", "model_revision", "model_checksum", "schema_version",
    "status", "issue",
)
SPATIAL_DIAGNOSTICS_COLUMNS = (
    "spatial_diagnostic_id", "case_id", "candidate_id", "model_id",
    "painting_id", "dataset_id", "dataset_scope", "experiment_id",
    "damage_or_degradation_type", "candidate_index", "seed",
    "prompt_policy_id", "prompt_variant_id", "execution_role",
    "is_zero_control", "region_id", "region_type", "spatial_support",
    "region_pixel_count", "damaged_error_mean", "damaged_error_median",
    "damaged_error_p95", "restored_error_mean", "restored_error_median",
    "restored_error_p95", "signed_improvement_mean",
    "signed_improvement_median", "signed_improvement_p05",
    "signed_improvement_p95", "improved_pixel_fraction",
    "worsened_pixel_fraction", "unchanged_pixel_fraction",
    "restoration_change_mean", "restoration_change_p95",
    "restoration_change_max", "restoration_changed_pixel_fraction",
    "evidence_role", "is_final_trustworthiness_flag",
    "diagnostic_version", "region_policy_version", "status", "issue",
)
SPATIAL_MAP_IMAGE_MANIFEST_COLUMNS = (
    "map_image_id", "asset_kind", "map_id", "candidate_id", "case_id",
    "model_id", "painting_id", "map_type", "selection_role",
    "relative_path", "sha256", "size_bytes", "width", "height",
    "image_mode", "format", "cmap", "vmin", "vmax", "center",
    "scale_scope", "quantization_policy", "no_data_policy",
    "renderer_version", "status", "issue",
)
LOCAL_CONSISTENCY_COLUMNS = (
    "local_consistency_id", "case_id", "candidate_id", "model_id",
    "painting_id", "dataset_id", "dataset_scope", "experiment_id",
    "damage_or_degradation_type", "target_damage_fraction",
    "realized_damage_fraction", "candidate_index", "seed",
    "prompt_policy_id", "prompt_variant_id", "execution_role",
    "is_zero_control", "metric_family", "metric_name",
    "evidence_component", "region_id", "region_type", "spatial_support",
    "region_pixel_count", "damaged_value", "restored_value",
    "improvement_value", "improvement_direction", "value_unit",
    "metric_version", "region_policy_version", "evidence_role",
    "is_final_trustworthiness_flag", "status", "issue",
)
LOCAL_CONSISTENCY_MAP_MANIFEST_COLUMNS = (
    "map_image_id", "asset_kind", "map_id", "candidate_id", "case_id",
    "model_id", "painting_id", "map_type", "selection_role",
    "relative_path", "sha256", "size_bytes", "width", "height",
    "image_mode", "format", "cmap", "vmin", "vmax", "center",
    "scale_scope", "quantization_policy", "no_data_policy",
    "renderer_version", "status", "issue",
)
DIFFUSION_UNCERTAINTY_COLUMNS = (
    "uncertainty_metric_id", "uncertainty_group_id", "observation_level",
    "case_id", "model_id", "painting_id", "category", "style_or_period",
    "dataset_id", "dataset_scope", "experiment_id",
    "damage_or_degradation_type", "case_label",
    "target_damage_fraction", "realized_damage_fraction",
    "configuration_id", "prompt_policy_id", "prompt_variant_id",
    "execution_role", "seed_count", "expected_seed_count",
    "seed_coverage_status", "candidate_id", "seed",
    "candidate_id_a", "candidate_id_b", "seed_a", "seed_b",
    "metric_family", "metric_name", "region_id", "summary_statistic",
    "value", "value_unit", "metric_version", "region_policy_version",
    "evidence_role", "is_combined_index", "status", "issue",
)
UNCERTAINTY_CALIBRATION_INPUTS_COLUMNS = (
    "uncertainty_group_id", "case_id", "model_id", "painting_id",
    "category", "style_or_period", "dataset_id", "dataset_scope",
    "experiment_id", "damage_or_degradation_type", "case_label",
    "target_damage_fraction", "realized_damage_fraction",
    "configuration_id", "prompt_policy_id", "prompt_variant_id",
    "execution_role", "seeds", "seed_count", "expected_seed_count",
    "seed_coverage_status",
    "rgb_std_mean_masked", "rgb_std_p95_masked",
    "rgb_pair_mae_mean_masked", "rgb_pair_rmse_mean_masked",
    "lpips_pair_mean_content", "lpips_pair_mean_crop",
    "clip_pair_distance_mean_content", "clip_pair_distance_mean_crop",
    "dino_pair_distance_mean_content", "dino_pair_distance_mean_crop",
    "reference_mae_masked_mean", "reference_mae_masked_std",
    "reference_mae_masked_worst", "reference_psnr_content_mean",
    "reference_psnr_content_std", "reference_psnr_content_worst",
    "reference_ssim_crop_mean", "reference_ssim_crop_std",
    "reference_ssim_crop_worst", "reference_lpips_crop_mean",
    "reference_lpips_crop_std", "reference_lpips_crop_worst",
    "reference_clip_crop_mean", "reference_clip_crop_std",
    "reference_clip_crop_worst", "reference_dino_crop_mean",
    "reference_dino_crop_std", "reference_dino_crop_worst",
    "texture_error_p95_crop_mean", "texture_error_p95_crop_std",
    "texture_error_p95_crop_worst", "colour_delta_e_masked_mean",
    "colour_delta_e_masked_std", "colour_delta_e_masked_worst",
    "seam_gradient_mismatch_mean", "seam_gradient_mismatch_std",
    "seam_gradient_mismatch_worst", "seam_ssim_error_mean",
    "seam_ssim_error_std", "seam_ssim_error_worst",
    "semantic_evidence_available", "human_review_flag_available",
    "failure_category_available", "combined_uncertainty_index_available",
    "calibration_scope", "schema_version", "status", "issue",
)
SPATIAL_EXPLANATIONS_COLUMNS = (
    "spatial_explanation_id", "uncertainty_group_id", "case_id",
    "model_id", "painting_id", "category", "style_or_period",
    "dataset_id", "dataset_scope", "experiment_id",
    "damage_or_degradation_type", "case_label",
    "target_damage_fraction", "realized_damage_fraction",
    "configuration_id", "prompt_policy_id", "prompt_variant_id",
    "execution_role", "seeds", "seed_count", "expected_seed_count",
    "seed_coverage_status", "representative_candidate_id",
    "representative_seed", "region_id", "region_pixel_count",
    "map_metric_name", "mean_value", "median_value", "p95_value",
    "max_value", "nonzero_fraction", "value_unit",
    "normalization_policy_id", "normalization_vmin",
    "normalization_vmax", "normalization_scope", "raw_map_key",
    "uncertainty_image_path", "overlay_image_path",
    "source_uncertainty_metric_version", "region_policy_version",
    "evidence_role", "is_calibrated_confidence",
    "is_final_trustworthiness_flag", "status", "issue",
)
SPATIAL_EXPLANATION_MAP_IMAGE_COLUMNS = (
    "map_asset_id", "asset_kind", "ownership", "uncertainty_group_id",
    "case_id", "candidate_id", "model_id", "painting_id",
    "prompt_variant_id", "map_type", "region_scope", "selection_role",
    "relative_path", "archive_key", "source_artifact_key",
    "source_map_image_id", "source_notebook", "sha256", "size_bytes",
    "width", "height", "image_mode", "format", "cmap", "vmin",
    "vmax", "center", "scale_scope", "normalization_policy_id",
    "quantization_policy", "no_data_policy", "renderer_version",
    "status", "issue",
)
SEMANTIC_STRUCTURAL_METRIC_COLUMNS = (
    "semantic_metric_id", "case_id", "candidate_id", "model_id",
    "painting_id", "category", "style_or_period", "dataset_id",
    "dataset_scope", "experiment_id", "damage_or_degradation_type",
    "target_damage_fraction", "realized_damage_fraction",
    "candidate_index", "seed", "prompt_policy_id", "prompt_variant_id",
    "execution_role", "is_zero_control", "semantic_target_scope",
    "applicability_status", "evidence_family", "metric_name",
    "feature_model_id", "region_id", "summary_statistic",
    "damaged_value", "restored_value", "improvement_value",
    "improvement_direction", "value_unit", "source_metric_row_id",
    "metric_version", "region_policy_version", "preprocessing_id",
    "evidence_role", "is_combined_score",
    "is_final_trustworthiness_flag", "status", "issue",
)
SEMANTIC_MAP_ASSET_COLUMNS = (
    "semantic_map_asset_id", "asset_kind", "ownership", "candidate_id",
    "case_id", "model_id", "painting_id", "feature_model_id",
    "region_id", "map_type", "relative_path", "archive_key",
    "channel_schema", "selection_role", "sha256", "size_bytes",
    "width", "height", "image_mode", "format", "cmap", "vmin",
    "vmax", "center", "scale_scope", "normalization_policy_id",
    "quantization_policy", "no_data_policy", "renderer_version",
    "status", "issue",
)
MODEL_COMPARISON_COLUMNS = (
    "comparison_row_id", "population_id", "analysis_scope", "scope_value",
    "source_notebook_id", "evidence_family", "metric_family", "metric_id",
    "metric_name", "feature_model_id", "region_id", "summary_statistic",
    "value_unit", "comparison_basis", "comparison_direction",
    "quality_ranking_eligible", "anchor_id", "model_id",
    "population_case_count", "paired_case_count", "paired_painting_count",
    "coverage_fraction", "damaged_mean", "damaged_median", "restored_mean",
    "restored_std", "restored_median", "restored_q25", "restored_q75",
    "improvement_mean", "improvement_median", "directional_utility_mean",
    "aggregate_rank", "winner_model_id", "winner_status", "tie_model_ids",
    "loo_replicate_count", "loo_top_rank_fraction", "loo_rank_min",
    "loo_rank_max", "selection_policy_id", "schema_version", "status",
    "issue",
)
METRIC_DISAGREEMENT_COLUMNS = (
    "disagreement_row_id", "population_id", "analysis_scope", "scope_value",
    "anchor_id", "evidence_family", "metric_id", "metric_name",
    "feature_model_id", "region_id", "summary_statistic",
    "comparison_direction", "eligible_case_count", "eligible_painting_count",
    "model_rank_order", "winner_model_id", "tie_model_ids",
    "family_consensus_winner_model_id", "agrees_with_family_consensus",
    "majority_vote_winner_model_id", "agrees_with_majority_vote",
    "family_vote_count", "family_vote_share", "distinct_metric_winner_count",
    "loo_replicate_count", "loo_winner_stability_fraction",
    "comparison_policy_id", "is_conservation_truth", "schema_version",
    "status", "issue",
)
REPRESENTATIVE_CASES_COLUMNS = (
    "representative_row_id", "selection_slot_id", "selection_role",
    "selection_priority", "population_id", "case_id", "painting_id",
    "category", "style_or_period", "experiment_id",
    "damage_or_degradation_type", "damage_type", "degradation_type",
    "severity", "model_id", "candidate_id", "candidate_selection_policy",
    "clean_image_path", "input_image_path", "mask_or_effect_path",
    "restored_path", "input_sha256", "mask_sha256", "restored_sha256",
    "selection_metric_id", "selection_score", "selection_rank",
    "selection_reason", "source_artifact_paths", "embedded_report_role",
    "path_validation_status", "schema_version", "status", "issue",
)

HINT_MAT_SELECTION_SCOPE_COLUMNS = (
    "selection_rank", "case_id", "painting_id", "category", "experiment_id",
    "damage_type", "target_damage_fraction", "realized_damage_fraction",
    "input_image_path", "clean_image_path", "mask_path", "source_manifest_path",
    "selection_policy", "status", "issue",
)

HINT_MAT_CANDIDATE_COLUMNS = (
    "candidate_id", "candidate_index", "selection_rank", "case_id",
    "painting_id", "category", "experiment_id", "damage_type",
    "realized_damage_fraction", "input_image_path", "clean_image_path",
    "mask_path", "input_sha256", "clean_sha256", "mask_sha256", "model_id",
    "model_label", "implementation", "repository_url", "repository_revision",
    "checkpoint_id", "checkpoint_path", "checkpoint_sha256", "license",
    "configuration_id", "adapter_policy", "seed", "requested_device",
    "actual_device", "precision", "inference_width", "inference_height",
    "output_width", "output_height", "compositing_policy", "execution_action",
    "restored_path", "restored_sha256", "model_load_seconds",
    "inference_seconds", "runtime_seconds", "gpu_peak_memory_bytes",
    "output_geometry_valid", "outside_mask_changed_pixels",
    "technical_validation_passed", "started_at_utc", "completed_at_utc",
    "generator_name", "generator_version", "status", "failure_type",
    "worker_return_code", "error_type", "error_message", "issue",
)

HINT_MAT_METRIC_VALUE_COLUMNS = (
    "metric_row_id", "candidate_id", "case_id", "painting_id", "category",
    "model_id", "metric_family", "metric_name", "region_id", "value",
    "preferred_direction", "metric_version", "region_policy_version",
    "status", "issue",
)

HINT_MAT_DECISION_SCORECARD_COLUMNS = (
    "scorecard_row_id", "model_id", "criterion_family", "criterion_id",
    "criterion_label", "evidence_value", "evidence_unit",
    "preferred_direction", "hard_gate", "gate_passed", "evidence_path",
    "status", "issue",
)

@dataclass(frozen=True)
class DataFrameSchema:
    """Declarative contract for one persisted or in-memory table."""

    name: str
    version: str
    required_columns: tuple[str, ...]
    primary_key: tuple[str, ...] = ()
    non_nullable: tuple[str, ...] = ()
    optional_columns: tuple[str, ...] = ()
    allowed_values: Mapping[str, frozenset[Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name or not self.version:
            raise ValueError("Schema name and version must be non-empty")
        if len(set(self.required_columns)) != len(self.required_columns):
            raise ValueError(f"Schema {self.name!r} repeats required columns")
        required = set(self.required_columns)
        unknown_key_columns = set(self.primary_key) - required
        unknown_non_nullable = set(self.non_nullable) - required
        if unknown_key_columns or unknown_non_nullable:
            raise ValueError(
                "Primary-key and non-nullable columns must also be required: "
                f"key={sorted(unknown_key_columns)}, "
                f"non_nullable={sorted(unknown_non_nullable)}"
            )


@dataclass(frozen=True)
class SchemaValidationResult:
    """Structured validation result suitable for notebook display and manifests."""

    schema_name: str
    schema_version: str
    row_count: int
    column_count: int
    missing_columns: tuple[str, ...]
    unexpected_columns: tuple[str, ...]
    duplicate_primary_key_rows: int
    null_counts: Mapping[str, int]
    invalid_value_counts: Mapping[str, int]

    @property
    def passed(self) -> bool:
        return not (
            self.missing_columns
            or self.duplicate_primary_key_rows
            or any(self.null_counts.values())
            or any(self.invalid_value_counts.values())
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "missing_columns": list(self.missing_columns),
            "unexpected_columns": list(self.unexpected_columns),
            "duplicate_primary_key_rows": self.duplicate_primary_key_rows,
            "null_counts": dict(self.null_counts),
            "invalid_value_counts": dict(self.invalid_value_counts),
            "passed": self.passed,
        }


def validate_dataframe(
    dataframe: pd.DataFrame,
    schema: DataFrameSchema,
    *,
    allow_extra_columns: bool = True,
) -> SchemaValidationResult:
    """Validate columns, key uniqueness, nullability, and enumerated values."""
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame")

    columns = set(dataframe.columns)
    missing = tuple(sorted(set(schema.required_columns) - columns))
    expected = set(schema.required_columns) | set(schema.optional_columns)
    unexpected = tuple(sorted(columns - expected)) if not allow_extra_columns else ()

    duplicate_rows = 0
    if not missing and schema.primary_key:
        duplicate_rows = int(
            dataframe.duplicated(list(schema.primary_key), keep=False).sum()
        )

    null_counts = {
        column: int(dataframe[column].isna().sum())
        for column in schema.non_nullable
        if column in dataframe.columns
    }
    for column in schema.primary_key:
        if column in dataframe.columns and column not in null_counts:
            null_counts[column] = int(dataframe[column].isna().sum())

    invalid_counts: dict[str, int] = {}
    for column, allowed in schema.allowed_values.items():
        if column not in dataframe.columns:
            continue
        values = dataframe[column].dropna()
        invalid_counts[column] = int((~values.isin(allowed)).sum())

    return SchemaValidationResult(
        schema_name=schema.name,
        schema_version=schema.version,
        row_count=int(len(dataframe)),
        column_count=int(len(dataframe.columns)),
        missing_columns=missing,
        unexpected_columns=unexpected,
        duplicate_primary_key_rows=duplicate_rows,
        null_counts=null_counts,
        invalid_value_counts=invalid_counts,
    )


def validate_mapping_keys(
    payload: Mapping[str, Any],
    required_keys: Iterable[str],
) -> tuple[str, ...]:
    """Return required mapping keys that are absent."""
    return tuple(sorted(set(required_keys) - set(payload)))


def require_mapping_keys(
    payload: Mapping[str, Any],
    required_keys: Iterable[str],
    *,
    mapping_name: str = "mapping",
) -> None:
    """Raise a compact error if required mapping keys are absent."""
    missing = validate_mapping_keys(payload, required_keys)
    if missing:
        raise ValueError(f"{mapping_name} is missing required keys: {list(missing)}")


ARTIFACT_MANIFEST_SCHEMA = DataFrameSchema(
    name="artifact_manifest",
    version="artifact_manifest.v1",
    required_columns=ARTIFACT_MANIFEST_COLUMNS,
    primary_key=("artifact_id",),
    non_nullable=(
        "artifact_id",
        "artifact_key",
        "producer_notebook",
        "artifact_type",
        "artifact_role",
        "relative_path",
        "format",
        "schema_version",
        "validation_status",
    ),
)

VALIDATION_CHECKS_SCHEMA = DataFrameSchema(
    name="validation_checks",
    version="validation_checks.v1",
    required_columns=VALIDATION_CHECK_COLUMNS,
    primary_key=("validation_stage", "check_id"),
    non_nullable=(
        "validation_stage",
        "check_id",
        "check_description",
        "severity",
        "passed",
    ),
    allowed_values={
        "severity": frozenset({"info", "warning", "error", "blocking"}),
    },
)

RAW_ARTWORK_METADATA_SCHEMA = DataFrameSchema(
    name="raw_artwork_metadata",
    version="raw_artwork_metadata.v1",
    required_columns=RAW_ARTWORK_METADATA_COLUMNS,
    primary_key=("painting_id",),
    non_nullable=(
        "painting_id", "category", "title", "artist", "source",
        "source_url", "license", "filename", "original_width",
        "original_height", "selection_reason", "visual_complexity_note",
        "status",
    ),
)

ARTWORKS_SCHEMA = DataFrameSchema(
    name="artworks",
    version="artworks.v1",
    required_columns=ARTWORKS_COLUMNS,
    primary_key=("painting_id",),
    non_nullable=(
        "dataset_id", "dataset_version", "dataset_scope", "painting_id",
        "dataset_sort_index", "title", "artist", "category", "source",
        "source_url", "license", "rights_status", "source_selection_status",
        "raw_image_path", "raw_filename", "metadata_completeness_pct",
        "prompt_metadata_field_count", "prompt_metadata_status",
        "selection_reason", "visual_complexity_note", "acceptance_status",
    ),
    allowed_values={
        "prompt_metadata_status": frozenset({"none", "partial", "complete"}),
        "acceptance_status": frozenset({"accepted", "excluded"}),
    },
)

DATASET_AUDIT_SCHEMA = DataFrameSchema(
    name="dataset_audit",
    version="dataset_audit.v1",
    required_columns=DATASET_AUDIT_COLUMNS,
    primary_key=("audit_row_id",),
    non_nullable=(
        "audit_row_id", "dataset_id", "dataset_version", "dataset_scope",
        "audit_section", "metric_name", "status",
    ),
)
PREPROCESSED_IMAGES_SCHEMA = DataFrameSchema(
    name="preprocessed_images",
    version="preprocessed_images.v1",
    required_columns=PREPROCESSED_IMAGES_COLUMNS,
    primary_key=("processed_image_id",),
    non_nullable=PREPROCESSED_IMAGES_COLUMNS,
    allowed_values={
        "mode": frozenset({"RGB"}),
        "format": frozenset({"PNG"}),
        "coordinate_convention": frozenset({"xyxy_exclusive_zero_based"}),
        "status": frozenset({"passed"}),
    },
)

PREPROCESSING_AUDIT_SCHEMA = DataFrameSchema(
    name="preprocessing_audit",
    version="preprocessing_audit.v1",
    required_columns=PREPROCESSING_AUDIT_COLUMNS,
    primary_key=("audit_row_id",),
    non_nullable=(
        "audit_row_id", "dataset_id", "dataset_version", "dataset_scope",
        "audit_section", "metric_name", "status",
    ),
)

CANONICAL_MASKS_SCHEMA = DataFrameSchema(
    name="canonical_masks",
    version="canonical_masks.v1",
    required_columns=CANONICAL_MASKS_COLUMNS,
    primary_key=("mask_id",),
    non_nullable=tuple(
        column for column in CANONICAL_MASKS_COLUMNS if column != "issue"
    ),
    allowed_values={
        "mask_mode": frozenset({"L"}),
        "mask_format": frozenset({"PNG"}),
        "binary_values_valid": frozenset({True}),
        "zero_control_rule_valid": frozenset({True}),
        "content_only_valid": frozenset({True}),
        "area_within_target_tolerance": frozenset({True}),
        "morphology_status": frozenset({"passed"}),
        "generation_status": frozenset({"passed"}),
        "status": frozenset({"passed"}),
    },
)

MASK_AUDIT_SCHEMA = DataFrameSchema(
    name="mask_audit",
    version="mask_audit.v1",
    required_columns=MASK_AUDIT_COLUMNS,
    primary_key=("audit_row_id",),
    non_nullable=(
        "audit_row_id", "dataset_id", "dataset_version", "dataset_scope",
        "experiment_id", "audit_section", "metric_name", "status",
    ),
    allowed_values={
        "status": frozenset({"passed", "failed", "informational"}),
    },
)

CANONICAL_DAMAGE_CASES_SCHEMA = DataFrameSchema(
    name="canonical_damage_cases",
    version="canonical_damage_cases.v1",
    required_columns=CANONICAL_DAMAGE_CASES_COLUMNS,
    primary_key=("case_id",),
    non_nullable=tuple(
        column for column in CANONICAL_DAMAGE_CASES_COLUMNS if column != "issue"
    ),
    allowed_values={
        "fill_strategy": frozenset({"constant_rgb"}),
        "mode": frozenset({"RGB"}),
        "format": frozenset({"PNG"}),
        "generation_status": frozenset({"passed"}),
        "status": frozenset({"passed"}),
    },
)

CANONICAL_DAMAGE_AUDIT_SCHEMA = DataFrameSchema(
    name="canonical_damage_audit",
    version="canonical_damage_audit.v1",
    required_columns=CANONICAL_DAMAGE_AUDIT_COLUMNS,
    primary_key=("case_id",),
    non_nullable=tuple(
        column for column in CANONICAL_DAMAGE_AUDIT_COLUMNS if column != "issue"
    ),
    allowed_values={
        "clean_file_exists": frozenset({True}),
        "mask_file_exists": frozenset({True}),
        "damaged_file_exists": frozenset({True}),
        "reload_passed": frozenset({True}),
        "dimensions_match": frozenset({True}),
        "binary_values_valid": frozenset({True}),
        "zero_control_valid": frozenset({True}),
        "clean_sha256_matches": frozenset({True}),
        "mask_sha256_matches": frozenset({True}),
        "damaged_sha256_matches": frozenset({True}),
        "damaged_mode": frozenset({"RGB"}),
        "damaged_format": frozenset({"PNG"}),
        "output_contract_valid": frozenset({True}),
        "validation_status": frozenset({"passed"}),
    },
)

DAMAGE_SIZE_CASES_SCHEMA = DataFrameSchema(
    name="damage_size_cases",
    version="damage_size_cases.v1",
    required_columns=DAMAGE_SIZE_CASES_COLUMNS,
    primary_key=("case_id",),
    non_nullable=tuple(
        column for column in DAMAGE_SIZE_CASES_COLUMNS
        if column not in {"previous_level_id", "previous_mask_id", "issue"}
    ),
    allowed_values={
        "base_mask_type": frozenset({"loss_large"}),
        "damage_or_degradation_type": frozenset({"binary_missing_region"}),
        "fill_strategy": frozenset({"constant_rgb"}),
        "mask_mode": frozenset({"L"}),
        "damaged_mode": frozenset({"RGB"}),
        "format": frozenset({"PNG"}),
        "nested_with_previous": frozenset({True}),
        "generation_status": frozenset({"passed"}),
        "status": frozenset({"passed"}),
    },
)

DAMAGE_SIZE_GENERATION_AUDIT_SCHEMA = DataFrameSchema(
    name="damage_size_generation_audit",
    version="damage_size_generation_audit.v1",
    required_columns=DAMAGE_SIZE_GENERATION_AUDIT_COLUMNS,
    primary_key=("case_id",),
    non_nullable=tuple(
        column for column in DAMAGE_SIZE_GENERATION_AUDIT_COLUMNS
        if column not in {"previous_level_id", "issue"}
    ),
    allowed_values={
        "area_within_tolerance": frozenset({True}),
        "nested_with_previous": frozenset({True}),
        "clean_file_exists": frozenset({True}),
        "base_mask_file_exists": frozenset({True}),
        "mask_file_exists": frozenset({True}),
        "damaged_file_exists": frozenset({True}),
        "reload_passed": frozenset({True}),
        "dimensions_match": frozenset({True}),
        "binary_values_valid": frozenset({True}),
        "content_only_valid": frozenset({True}),
        "metadata_mask_pixels_match": frozenset({True}),
        "clean_sha256_matches": frozenset({True}),
        "base_mask_sha256_matches": frozenset({True}),
        "mask_sha256_matches": frozenset({True}),
        "damaged_sha256_matches": frozenset({True}),
        "output_contract_valid": frozenset({True}),
        "morphology_preservation_status": frozenset({"passed"}),
        "validation_status": frozenset({"passed"}),
    },
)

MASK_ROBUSTNESS_CASES_SCHEMA = DataFrameSchema(
    name="mask_robustness_cases",
    version="mask_robustness_cases.v1",
    required_columns=MASK_ROBUSTNESS_CASES_COLUMNS,
    primary_key=("case_id",),
    non_nullable=tuple(
        column for column in MASK_ROBUSTNESS_CASES_COLUMNS if column != "issue"
    ),
    allowed_values={
        "mask_type": frozenset({"scratch_thin", "loss_small", "loss_large"}),
        "fill_strategy": frozenset({"constant_rgb"}),
        "mask_mode": frozenset({"L"}),
        "damaged_mode": frozenset({"RGB"}),
        "format": frozenset({"PNG"}),
        "generation_status": frozenset({"passed"}),
        "status": frozenset({"passed"}),
    },
)

MASK_ROBUSTNESS_GENERATION_AUDIT_SCHEMA = DataFrameSchema(
    name="mask_robustness_generation_audit",
    version="mask_robustness_generation_audit.v1",
    required_columns=MASK_ROBUSTNESS_GENERATION_AUDIT_COLUMNS,
    primary_key=("case_id",),
    non_nullable=tuple(
        column for column in MASK_ROBUSTNESS_GENERATION_AUDIT_COLUMNS
        if column != "issue"
    ),
    allowed_values={
        "area_within_tolerance": frozenset({True}),
        "group_unique_mask_count_passed": frozenset({True}),
        "pairwise_iou_passed": frozenset({True}),
        "location_variation_passed": frozenset({True}),
        "morphology_variation_passed": frozenset({True}),
        "component_arrangement_variation_passed": frozenset({True}),
        "family_morphology_passed": frozenset({True}),
        "clean_file_exists": frozenset({True}),
        "mask_file_exists": frozenset({True}),
        "damaged_file_exists": frozenset({True}),
        "reload_passed": frozenset({True}),
        "dimensions_match": frozenset({True}),
        "binary_values_valid": frozenset({True}),
        "content_only_valid": frozenset({True}),
        "metadata_mask_pixels_match": frozenset({True}),
        "clean_sha256_matches": frozenset({True}),
        "mask_pixel_sha256_matches": frozenset({True}),
        "mask_sha256_matches": frozenset({True}),
        "damaged_sha256_matches": frozenset({True}),
        "output_contract_valid": frozenset({True}),
        "group_gate_passed": frozenset({True}),
        "validation_status": frozenset({"passed"}),
    },
)

SYNTHETIC_DEGRADATION_CASES_SCHEMA = DataFrameSchema(
    name="synthetic_degradation_cases",
    version="synthetic_degradation_cases.v1",
    required_columns=SYNTHETIC_DEGRADATION_CASES_COLUMNS,
    primary_key=("case_id",),
    non_nullable=tuple(
        column for column in SYNTHETIC_DEGRADATION_CASES_COLUMNS
        if column != "issue"
    ),
    allowed_values={
        "severity": frozenset({"mild", "moderate", "severe"}),
        "effect_mask_mode": frozenset({"L"}),
        "degraded_mode": frozenset({"RGB"}),
        "format": frozenset({"PNG"}),
        "generation_status": frozenset({"passed"}),
        "status": frozenset({"passed"}),
    },
)

SYNTHETIC_DEGRADATION_GENERATION_AUDIT_SCHEMA = DataFrameSchema(
    name="synthetic_degradation_generation_audit",
    version="synthetic_degradation_generation_audit.v1",
    required_columns=SYNTHETIC_DEGRADATION_GENERATION_AUDIT_COLUMNS,
    primary_key=("case_id",),
    non_nullable=tuple(
        column for column in SYNTHETIC_DEGRADATION_GENERATION_AUDIT_COLUMNS
        if column != "issue"
    ),
    allowed_values={
        "clean_file_exists": frozenset({True}),
        "effect_mask_file_exists": frozenset({True}),
        "degraded_file_exists": frozenset({True}),
        "reload_passed": frozenset({True}),
        "dimensions_match": frozenset({True}),
        "effect_mask_mode_valid": frozenset({True}),
        "degraded_mode_valid": frozenset({True}),
        "format_valid": frozenset({True}),
        "content_only_valid": frozenset({True}),
        "parameters_recorded": frozenset({True}),
        "seeds_recorded": frozenset({True}),
        "affected_support_pixels_match": frozenset({True}),
        "affected_active_pixels_match": frozenset({True}),
        "changed_pixels_match": frozenset({True}),
        "changed_pixels_within_support": frozenset({True}),
        "outside_support_changed_pixels": frozenset({0}),
        "clean_sha256_matches": frozenset({True}),
        "effect_mask_sha256_matches": frozenset({True}),
        "degraded_image_sha256_matches": frozenset({True}),
        "clean_reference_unchanged": frozenset({True}),
        "impact_metrics_finite": frozenset({True}),
        "output_contract_valid": frozenset({True}),
        "validation_status": frozenset({"passed"}),
    },
)

CASE_REGISTRY_SCHEMA = DataFrameSchema(
    name="case_registry",
    version="case_registry.v1",
    required_columns=CASE_REGISTRY_COLUMNS,
    primary_key=("case_id",),
    non_nullable=tuple(
        column for column in CASE_REGISTRY_COLUMNS
        if column not in {"target_damage_fraction", "realized_damage_fraction"}
    ),
    allowed_values={"status": frozenset({"passed"})},
)

MODEL_ELIGIBILITY_SCHEMA = DataFrameSchema(
    name="model_eligibility",
    version="model_eligibility.v1",
    required_columns=MODEL_ELIGIBILITY_COLUMNS,
    primary_key=("case_id", "model_id"),
    non_nullable=MODEL_ELIGIBILITY_COLUMNS,
    allowed_values={"eligible": frozenset({True, False})},
)

RESTORATIONS_SCHEMA = DataFrameSchema(
    name="restorations",
    version="restorations.v1",
    required_columns=RESTORATIONS_COLUMNS,
    primary_key=("restoration_id",),
    non_nullable=tuple(
        column for column in RESTORATIONS_COLUMNS
        if column not in {
            "seed",
            "prompt_policy_id",
            "opencv_version",
            "inpaint_radius",
            "restored_sha256",
            "issue",
        }
    ),
    allowed_values={
        "candidate_index": frozenset({0}),
        "device": frozenset({"cpu", "cuda"}),
        "precision": frozenset({"uint8", "float16", "float32"}),
        "execution_action": frozenset(
            {
                "telea_inpaint",
                "lama_inpaint",
                "identity_noop",
                "reused_validated",
                "failed",
            }
        ),
        "status": frozenset({"completed", "failed"}),
    },
)

RESTORATION_RUNTIME_SUMMARY_SCHEMA = DataFrameSchema(
    name="restoration_runtime_summary",
    version="restoration_runtime_summary.v1",
    required_columns=RESTORATION_RUNTIME_SUMMARY_COLUMNS,
    primary_key=("summary_scope", "experiment_id"),
    non_nullable=RESTORATION_RUNTIME_SUMMARY_COLUMNS,
    allowed_values={
        "summary_scope": frozenset(
            {"overall", "experiment", "execution_role", "prompt_variant"}
        ),
        "status": frozenset({"completed", "has_failures"}),
    },
)

STABLE_DIFFUSION_CANDIDATES_SCHEMA = DataFrameSchema(
    name="stable_diffusion_candidates",
    version="stable_diffusion_candidates.v1",
    required_columns=STABLE_DIFFUSION_CANDIDATE_COLUMNS,
    primary_key=("candidate_id",),
    non_nullable=tuple(
        column for column in STABLE_DIFFUSION_CANDIDATE_COLUMNS
        if column not in {
            "restored_sha256", "runtime_seconds", "gpu_memory_before_bytes",
            "gpu_memory_after_bytes", "gpu_peak_memory_bytes",
            "started_at_utc", "completed_at_utc", "issue",
        }
    ),
    allowed_values={
        "execution_role": frozenset(
            {"primary", "prompt_context", "uncertainty_extension"}
        ),
        "execution_action": frozenset(
            {"stable_diffusion_inpaint", "identity_noop", "reused_validated", "pending", "failed"}
        ),
        "status": frozenset({"planned", "completed", "failed"}),
    },
)

SDXL_FEASIBILITY_ATTEMPTS_SCHEMA = DataFrameSchema(
    name="sdxl_feasibility_attempts",
    version="sdxl_feasibility_attempts.v1",
    required_columns=SDXL_FEASIBILITY_ATTEMPT_COLUMNS,
    primary_key=("attempt_id",),
    non_nullable=tuple(
        column for column in SDXL_FEASIBILITY_ATTEMPT_COLUMNS
        if column not in {
            "actual_device", "gpu_name", "gpu_total_memory_bytes",
            "outside_mask_changed_pixels", "model_load_seconds",
            "inference_seconds", "runtime_seconds", "gpu_peak_memory_bytes",
            "projected_primary_hours", "projected_comparable_hours",
            "worker_return_code", "error_type", "error_message", "issue",
        }
    ),
    allowed_values={
        "evidence_origin": frozenset({"current_execution"}),
        "requested_device": frozenset({"cuda"}),
        "actual_device": frozenset({"", "cuda"}),
        "precision": frozenset({"float16"}),
        "availability_state": frozenset(
            {
                "full_evaluation_complete", "partial_evaluation",
                "feasibility_only", "unavailable", "failed",
            }
        ),
        "status": frozenset(
            {"planned", "completed", "timed_out", "failed", "skipped"}
        ),
        "failure_type": frozenset(
            {
                "none", "runtime_guardrail", "cuda_out_of_memory",
                "model_unavailable", "model_load_failure",
                "inference_failure", "input_validation_failure",
                "worker_failure", "skipped_after_guardrail",
            }
        ),
    },
)
SDXL_PARTIAL_CANDIDATES_SCHEMA = DataFrameSchema(
    name="sdxl_partial_candidates",
    version="sdxl_partial_candidates.v1",
    required_columns=SDXL_PARTIAL_CANDIDATE_COLUMNS,
    primary_key=("candidate_id",),
    non_nullable=tuple(
        column for column in SDXL_PARTIAL_CANDIDATE_COLUMNS
        if column not in {
            "input_sha256", "mask_sha256", "device", "restored_sha256",
            "runtime_seconds", "model_load_seconds", "inference_seconds",
            "gpu_total_memory_bytes", "gpu_memory_before_bytes",
            "gpu_memory_after_bytes", "gpu_peak_memory_bytes",
            "budget_seconds_before_attempt", "budget_seconds_after_attempt",
            "outside_mask_changed_pixels", "started_at_utc", "completed_at_utc",
            "worker_return_code", "error_type", "error_message", "issue",
        }
    ),
    allowed_values={
        "execution_role": frozenset({"primary"}),
        "execution_action": frozenset(
            {"pending", "sdxl_inpaint", "reused_validated", "failed", "skipped"}
        ),
        "precision": frozenset({"float16"}),
        "availability_state": frozenset(
            {"partial_evaluation", "feasibility_only", "unavailable", "failed", "pending"}
        ),
        "status": frozenset(
            {"planned", "completed", "timed_out", "failed", "skipped"}
        ),
        "failure_type": frozenset(
            {
                "none", "runtime_guardrail", "global_budget_exhausted",
                "cuda_out_of_memory", "model_unavailable", "model_load_failure",
                "inference_failure", "input_validation_failure", "worker_failure",
                "skipped_after_guardrail", "not_started_global_budget",
            }
        ),
    },
)
PROMPT_POLICY_SCHEMA = DataFrameSchema(
    name="prompt_policy",
    version="prompt_policy.v1",
    required_columns=PROMPT_POLICY_COLUMNS,
    primary_key=("prompt_policy_id", "prompt_variant_id"),
    non_nullable=PROMPT_POLICY_COLUMNS,
    allowed_values={
        "variant_family": frozenset({"generic", "contextual"}),
        "status": frozenset({"approved"}),
    },
)

PROMPT_ABLATION_DESIGN_SCHEMA = DataFrameSchema(
    name="prompt_ablation_design",
    version="prompt_ablation_design.v1",
    required_columns=PROMPT_ABLATION_DESIGN_COLUMNS,
    primary_key=("design_row_id",),
    non_nullable=PROMPT_ABLATION_DESIGN_COLUMNS,
    allowed_values={
        "design_component": frozenset({"prompt_ablation", "uncertainty"}),
        "included": frozenset({True}),
        "status": frozenset({"approved"}),
    },
)

REGION_POLICY_SCHEMA = DataFrameSchema(
    name="region_policy",
    version="region_policy.v1",
    required_columns=REGION_POLICY_COLUMNS,
    primary_key=("metric_family", "region_id"),
    non_nullable=REGION_POLICY_COLUMNS,
    allowed_values={
        "compatible": frozenset({True, False}),
        "status": frozenset({"approved"}),
    },
)
CLASSICAL_METRICS_SCHEMA = DataFrameSchema(
    name="classical_metrics",
    version="classical_metrics.v1",
    required_columns=CLASSICAL_METRICS_COLUMNS,
    primary_key=("metric_row_id",),
    non_nullable=tuple(
        column for column in CLASSICAL_METRICS_COLUMNS
        if column not in {
            "damaged_value", "restored_value", "improvement_value", "issue"
        }
    ),
    allowed_values={
        "metric_family": frozenset({"classical_pixel", "ssim"}),
        "metric_name": frozenset({"mse", "mae", "psnr", "ssim"}),
        "improvement_direction": frozenset(
            {"damaged_minus_restored", "restored_minus_damaged"}
        ),
        "status": frozenset({"ok", "error"}),
    },
)
LPIPS_METRICS_SCHEMA = DataFrameSchema(
    name="lpips_metrics",
    version="lpips_metrics.v1",
    required_columns=LPIPS_METRICS_COLUMNS,
    primary_key=("metric_row_id",),
    non_nullable=tuple(
        column for column in LPIPS_METRICS_COLUMNS
        if column not in {"damaged_value", "restored_value", "improvement_value", "issue"}
    ),
    allowed_values={
        "metric_family": frozenset({"perceptual"}),
        "metric_name": frozenset({"lpips"}),
        "region_id": frozenset({"content_region", "mask_bbox_crop"}),
        "improvement_direction": frozenset({"damaged_minus_restored"}),
        "status": frozenset({"ok", "error"}),
    },
)
FEATURE_METRICS_SCHEMA = DataFrameSchema(
    name="feature_metrics",
    version="feature_metrics.v1",
    required_columns=FEATURE_METRICS_COLUMNS,
    primary_key=("metric_row_id",),
    non_nullable=tuple(
        column for column in FEATURE_METRICS_COLUMNS
        if column not in {
            "damaged_value", "restored_value", "improvement_value", "issue"
        }
    ),
    allowed_values={
        "metric_family": frozenset({"feature_similarity"}),
        "metric_name": frozenset({
            "clip_cosine_similarity", "dinov2_cosine_similarity"
        }),
        "feature_model_id": frozenset({"clip_vit_b32", "dinov2_vits14"}),
        "region_id": frozenset({"content_region", "mask_bbox_crop"}),
        "improvement_direction": frozenset({"restored_minus_damaged"}),
        "status": frozenset({"ok", "error"}),
    },
)
FEATURE_EMBEDDING_MANIFEST_SCHEMA = DataFrameSchema(
    name="feature_embedding_manifest",
    version="feature_embedding_manifest.v1",
    required_columns=FEATURE_EMBEDDING_MANIFEST_COLUMNS,
    primary_key=("embedding_id",),
    non_nullable=tuple(
        column for column in FEATURE_EMBEDDING_MANIFEST_COLUMNS
        if column not in {"case_id", "representative_candidate_id", "issue"}
    ),
    allowed_values={
        "feature_model_id": frozenset({"clip_vit_b32", "dinov2_vits14"}),
        "image_role": frozenset({"clean", "damaged", "restored"}),
        "region_id": frozenset({"content_region", "mask_bbox_crop"}),
        "array_name": frozenset({"clip_embeddings", "dinov2_embeddings"}),
        "dtype": frozenset({"float32"}),
        "status": frozenset({"ok", "error"}),
    },
)
SPATIAL_DIAGNOSTICS_SCHEMA = DataFrameSchema(
    name="spatial_diagnostics",
    version="spatial_diagnostics.v1",
    required_columns=SPATIAL_DIAGNOSTICS_COLUMNS,
    primary_key=("spatial_diagnostic_id",),
    non_nullable=tuple(
        column for column in SPATIAL_DIAGNOSTICS_COLUMNS
        if column not in {
            "seed", "prompt_policy_id", "prompt_variant_id", "issue",
            "damaged_error_mean", "damaged_error_median",
            "damaged_error_p95", "restored_error_mean",
            "restored_error_median", "restored_error_p95",
            "signed_improvement_mean", "signed_improvement_median",
            "signed_improvement_p05", "signed_improvement_p95",
            "improved_pixel_fraction", "worsened_pixel_fraction",
            "unchanged_pixel_fraction", "restoration_change_mean",
            "restoration_change_p95", "restoration_change_max",
            "restoration_changed_pixel_fraction",
        }
    ),
    allowed_values={
        "region_id": frozenset({
            "full_image", "content_region", "masked_region",
            "mask_bbox_crop", "inner_boundary_band",
            "outer_boundary_band", "boundary_ring",
            "outside_mask_content", "outside_boundary_ring",
            "degradation_support",
        }),
        "evidence_role": frozenset({"diagnostic_only"}),
        "is_final_trustworthiness_flag": frozenset({False}),
        "status": frozenset({"ok", "error"}),
    },
)
SPATIAL_MAP_IMAGE_MANIFEST_SCHEMA = DataFrameSchema(
    name="spatial_map_images",
    version="spatial_map_images.v1",
    required_columns=SPATIAL_MAP_IMAGE_MANIFEST_COLUMNS,
    primary_key=("map_image_id",),
    non_nullable=tuple(
        column for column in SPATIAL_MAP_IMAGE_MANIFEST_COLUMNS
        if column not in {
            "candidate_id", "case_id", "model_id", "painting_id",
            "selection_role", "cmap", "vmin", "vmax", "center", "issue",
        }
    ),
    allowed_values={
        "asset_kind": frozenset({"candidate_map", "selected_panel"}),
        "map_type": frozenset({
            "damaged_absolute_error", "restored_absolute_error",
            "signed_improvement", "masked_signed_improvement",
            "spatial_overlay", "candidate_spatial_panel",
            "cross_model_spatial_panel",
        }),
        "format": frozenset({"PNG"}),
        "renderer_version": frozenset({"spatial_map_renderer.v1"}),
        "status": frozenset({"passed", "error"}),
    },
)
LOCAL_CONSISTENCY_SCHEMA = DataFrameSchema(
    name="local_consistency",
    version="local_consistency.v1",
    required_columns=LOCAL_CONSISTENCY_COLUMNS,
    primary_key=("local_consistency_id",),
    non_nullable=tuple(
        column for column in LOCAL_CONSISTENCY_COLUMNS
        if column not in {
            "target_damage_fraction", "realized_damage_fraction", "seed",
            "prompt_policy_id", "prompt_variant_id", "damaged_value",
            "restored_value", "improvement_value", "issue",
        }
    ),
    allowed_values={
        "metric_family": frozenset({
            "texture_descriptor", "texture_map", "colour", "seam"
        }),
        "improvement_direction": frozenset({"damaged_minus_restored"}),
        "evidence_role": frozenset({"diagnostic_only"}),
        "is_final_trustworthiness_flag": frozenset({False}),
        "status": frozenset({"ok", "not_applicable", "error"}),
    },
)
LOCAL_CONSISTENCY_MAP_MANIFEST_SCHEMA = DataFrameSchema(
    name="local_consistency_map_images",
    version="local_consistency_map_images.v1",
    required_columns=LOCAL_CONSISTENCY_MAP_MANIFEST_COLUMNS,
    primary_key=("map_image_id",),
    non_nullable=tuple(
        column for column in LOCAL_CONSISTENCY_MAP_MANIFEST_COLUMNS
        if column not in {
            "candidate_id", "case_id", "model_id", "painting_id",
            "selection_role", "center", "issue",
        }
    ),
    allowed_values={
        "asset_kind": frozenset({"candidate_map", "selected_panel"}),
        "map_type": frozenset({
            "texture", "colour", "seam",
            "local_consistency_candidate_panel",
            "cross_model_local_consistency_panel",
        }),
        "format": frozenset({"PNG"}),
        "renderer_version": frozenset({"local_consistency_map_renderer.v1"}),
        "status": frozenset({"passed", "error"}),
    },
)
DIFFUSION_UNCERTAINTY_SCHEMA = DataFrameSchema(
    name="diffusion_uncertainty",
    version="diffusion_uncertainty.v1",
    required_columns=DIFFUSION_UNCERTAINTY_COLUMNS,
    primary_key=("uncertainty_metric_id",),
    non_nullable=tuple(
        column for column in DIFFUSION_UNCERTAINTY_COLUMNS
        if column not in {
            "target_damage_fraction", "realized_damage_fraction",
            "candidate_id", "seed", "candidate_id_a", "candidate_id_b",
            "seed_a", "seed_b", "value", "issue",
        }
    ),
    allowed_values={
        "observation_level": frozenset({
            "group_summary", "candidate_pair", "seed_reference"
        }),
        "seed_coverage_status": frozenset({"complete", "insufficient"}),
        "metric_family": frozenset({
            "pixel_variability", "pixel_pairwise", "perceptual_pairwise",
            "feature_pairwise", "classical_reference",
            "perceptual_reference", "feature_reference",
            "local_consistency_reference",
        }),
        "evidence_role": frozenset({
            "empirical_uncertainty_proxy", "calibration_reference"
        }),
        "is_combined_index": frozenset({False}),
        "status": frozenset({"ok", "not_applicable", "error"}),
    },
)
UNCERTAINTY_CALIBRATION_INPUTS_SCHEMA = DataFrameSchema(
    name="uncertainty_calibration_inputs",
    version="uncertainty_calibration_inputs.v1",
    required_columns=UNCERTAINTY_CALIBRATION_INPUTS_COLUMNS,
    primary_key=("uncertainty_group_id",),
    non_nullable=tuple(
        column for column in UNCERTAINTY_CALIBRATION_INPUTS_COLUMNS
        if column not in {"target_damage_fraction", "realized_damage_fraction", "issue"}
    ),
    allowed_values={
        "seed_coverage_status": frozenset({"complete", "insufficient"}),
        "semantic_evidence_available": frozenset({False}),
        "human_review_flag_available": frozenset({False}),
        "failure_category_available": frozenset({False}),
        "combined_uncertainty_index_available": frozenset({False}),
        "calibration_scope": frozenset({"pre_semantic_pre_human_partial"}),
        "status": frozenset({"ok", "error"}),
    },
)
SPATIAL_EXPLANATIONS_SCHEMA = DataFrameSchema(
    name="spatial_explanations",
    version="spatial_explanations.v1",
    required_columns=SPATIAL_EXPLANATIONS_COLUMNS,
    primary_key=("spatial_explanation_id",),
    non_nullable=tuple(
        column for column in SPATIAL_EXPLANATIONS_COLUMNS
        if column not in {
            "target_damage_fraction", "realized_damage_fraction", "issue",
        }
    ),
    allowed_values={
        "seed_coverage_status": frozenset({"complete"}),
        "region_id": frozenset({
            "full_image", "content_region", "masked_region",
            "mask_bbox_crop", "boundary_ring", "outside_mask_content",
        }),
        "map_metric_name": frozenset({"pixel_rgb_std_mean"}),
        "value_unit": frozenset({"normalized_rgb_0_1"}),
        "evidence_role": frozenset({"spatial_diagnostic_proxy"}),
        "is_calibrated_confidence": frozenset({False}),
        "is_final_trustworthiness_flag": frozenset({False}),
        "status": frozenset({"ok", "error"}),
    },
)
SPATIAL_EXPLANATION_MAP_IMAGE_SCHEMA = DataFrameSchema(
    name="spatial_explanation_map_images",
    version="spatial_explanation_map_images.v1",
    required_columns=SPATIAL_EXPLANATION_MAP_IMAGE_COLUMNS,
    primary_key=("map_asset_id",),
    non_nullable=tuple(
        column for column in SPATIAL_EXPLANATION_MAP_IMAGE_COLUMNS
        if column not in {
            "candidate_id", "selection_role", "relative_path",
            "archive_key", "source_artifact_key", "source_map_image_id",
            "source_notebook", "sha256", "size_bytes", "width", "height",
            "image_mode", "cmap", "vmin", "vmax", "center", "issue",
        }
    ),
    allowed_values={
        "asset_kind": frozenset({
            "uncertainty_panel", "uncertainty_overlay", "raw_numeric_map",
            "component_map", "selected_panel",
        }),
        "ownership": frozenset({"owned", "upstream_link"}),
        "map_type": frozenset({
            "uncertainty_variants", "uncertainty_overlay",
            "uncertainty_numeric", "restored_absolute_error",
            "signed_improvement", "texture", "colour", "seam",
            "selected_median", "selected_boundary_concentration",
            "selected_prompt_difference",
        }),
        "format": frozenset({"PNG", "NPZ"}),
        "renderer_version": frozenset({
            "spatial_explanation_renderer.v1",
            "spatial_explanation_renderer.v1.1",
            "spatial_map_renderer.v1",
            "local_consistency_map_renderer.v1",
        }),
        "status": frozenset({"passed", "not_available", "error"}),
    },
)
SEMANTIC_STRUCTURAL_METRIC_SCHEMA = DataFrameSchema(
    name="semantic_structural_metrics",
    version="semantic_structural_metrics.v1",
    required_columns=SEMANTIC_STRUCTURAL_METRIC_COLUMNS,
    primary_key=("semantic_metric_id",),
    non_nullable=tuple(
        column for column in SEMANTIC_STRUCTURAL_METRIC_COLUMNS
        if column not in {
            "target_damage_fraction", "realized_damage_fraction",
            "candidate_index", "seed", "prompt_policy_id",
            "prompt_variant_id", "damaged_value", "restored_value",
            "improvement_value", "source_metric_row_id", "issue",
        }
    ),
    allowed_values={
        "semantic_target_scope": frozenset({
            "facial_anatomical_structure_proxy",
            "architectural_layout_proxy",
            "natural_object_structure_proxy",
            "abstract_compositional_structure_proxy",
            "painterly_surface_structure_proxy",
        }),
        "applicability_status": frozenset({"applicable", "not_applicable"}),
        "evidence_family": frozenset({
            "subject_preservation", "local_semantic_preservation",
            "local_semantic_worsening", "outside_context_preservation",
            "structural_layout", "painterly_representation",
            "encoder_agreement",
        }),
        "feature_model_id": frozenset({
            "clip_vit_b32", "dinov2_vits14",
            "clip_vit_b32+dinov2_vits14",
        }),
        "evidence_role": frozenset({"semantic_structural_diagnostic_proxy"}),
        "is_combined_score": frozenset({False}),
        "is_final_trustworthiness_flag": frozenset({False}),
        "status": frozenset({"ok", "error"}),
    },
)
SEMANTIC_MAP_ASSET_SCHEMA = DataFrameSchema(
    name="semantic_map_assets",
    version="semantic_map_assets.v1",
    required_columns=SEMANTIC_MAP_ASSET_COLUMNS,
    primary_key=("semantic_map_asset_id",),
    non_nullable=tuple(
        column for column in SEMANTIC_MAP_ASSET_COLUMNS
        if column not in {
            "relative_path", "archive_key", "selection_role", "sha256",
            "size_bytes", "width", "height", "image_mode", "cmap",
            "vmin", "vmax", "center", "issue",
        }
    ),
    allowed_values={
        "asset_kind": frozenset({"numeric_map_bundle", "rendered_semantic_panel"}),
        "ownership": frozenset({"owned"}),
        "feature_model_id": frozenset({
            "clip_vit_b32", "dinov2_vits14", "multi_encoder",
        }),
        "map_type": frozenset({"local_semantic_bundle", "semantic_panel"}),
        "format": frozenset({"NPZ", "PNG"}),
        "renderer_version": frozenset({"semantic_map_renderer.v1"}),
        "status": frozenset({"passed", "error"}),
    },
)
MODEL_COMPARISON_SCHEMA = DataFrameSchema(
    name="model_comparison",
    version="model_comparison.v1",
    required_columns=MODEL_COMPARISON_COLUMNS,
    primary_key=("comparison_row_id",),
    non_nullable=tuple(
        column for column in MODEL_COMPARISON_COLUMNS
        if column not in {
            "feature_model_id", "anchor_id", "damaged_mean",
            "damaged_median", "improvement_mean", "improvement_median",
            "aggregate_rank", "winner_model_id", "tie_model_ids",
            "loo_top_rank_fraction", "loo_rank_min", "loo_rank_max", "issue",
        }
    ),
    allowed_values={
        "population_id": frozenset({"core_three_model", "sdxl_four_model_subset"}),
        "comparison_direction": frozenset({
            "higher_is_better", "lower_is_better", "descriptive_only",
        }),
        "quality_ranking_eligible": frozenset({True, False}),
        "winner_status": frozenset({"winner", "tied", "not_winner", "not_ranked"}),
        "selection_policy_id": frozenset({"non_metric_primary_candidate_selection.v1"}),
        "schema_version": frozenset({"model_comparison.v1"}),
        "status": frozenset({"ok", "not_applicable", "error"}),
    },
)
METRIC_DISAGREEMENT_SCHEMA = DataFrameSchema(
    name="metric_disagreement",
    version="metric_disagreement.v1",
    required_columns=METRIC_DISAGREEMENT_COLUMNS,
    primary_key=("disagreement_row_id",),
    non_nullable=tuple(
        column for column in METRIC_DISAGREEMENT_COLUMNS
        if column not in {
            "feature_model_id", "tie_model_ids",
            "family_consensus_winner_model_id", "majority_vote_winner_model_id",
            "loo_winner_stability_fraction", "issue",
        }
    ),
    allowed_values={
        "population_id": frozenset({"core_three_model", "sdxl_four_model_subset"}),
        "comparison_direction": frozenset({"higher_is_better", "lower_is_better"}),
        "agrees_with_family_consensus": frozenset({True, False}),
        "agrees_with_majority_vote": frozenset({True, False}),
        "comparison_policy_id": frozenset({"family_balanced_anchor_disagreement.v1"}),
        "is_conservation_truth": frozenset({False}),
        "schema_version": frozenset({"metric_disagreement.v1"}),
        "status": frozenset({"ok", "not_applicable", "error"}),
    },
)
REPRESENTATIVE_CASES_SCHEMA = DataFrameSchema(
    name="representative_cases",
    version="representative_cases.v1",
    required_columns=REPRESENTATIVE_CASES_COLUMNS,
    primary_key=("representative_row_id",),
    non_nullable=tuple(
        column for column in REPRESENTATIVE_CASES_COLUMNS
        if column not in {
            "style_or_period", "damage_type", "degradation_type", "severity",
            "clean_image_path", "input_image_path", "mask_or_effect_path",
            "restored_path", "input_sha256", "mask_sha256", "restored_sha256",
            "selection_metric_id", "selection_score", "selection_rank",
            "source_artifact_paths", "issue",
        }
    ),
    allowed_values={
        "population_id": frozenset({"core_three_model", "sdxl_four_model_subset"}),
        "candidate_selection_policy": frozenset({"non_metric_primary_candidate_selection.v1"}),
        "path_validation_status": frozenset({"passed", "not_available", "error"}),
        "schema_version": frozenset({"representative_cases.v1"}),
        "status": frozenset({"ok", "not_applicable", "error"}),
    },
)

HINT_MAT_SELECTION_SCOPE_SCHEMA = DataFrameSchema(
    name="hint_mat_selection_scope",
    version="hint_mat_selection_scope.v1",
    required_columns=HINT_MAT_SELECTION_SCOPE_COLUMNS,
    primary_key=("case_id",),
    non_nullable=tuple(column for column in HINT_MAT_SELECTION_SCOPE_COLUMNS if column != "issue"),
    allowed_values={
        "experiment_id": frozenset({"canonical_missing_region"}),
        "damage_type": frozenset({"scratch_thin", "loss_small", "loss_large", "mixed_damage"}),
        "selection_policy": frozenset({"predeclared_balanced_canonical_non_metric.v1"}),
        "status": frozenset({"passed"}),
    },
)

HINT_MAT_CANDIDATES_SCHEMA = DataFrameSchema(
    name="hint_mat_candidates",
    version="hint_mat_candidates.v1",
    required_columns=HINT_MAT_CANDIDATE_COLUMNS,
    primary_key=("candidate_id",),
    non_nullable=tuple(
        column for column in HINT_MAT_CANDIDATE_COLUMNS
        if column not in {
            "actual_device", "restored_sha256", "model_load_seconds",
            "inference_seconds", "runtime_seconds", "gpu_peak_memory_bytes",
            "outside_mask_changed_pixels", "started_at_utc", "completed_at_utc",
            "worker_return_code", "error_type", "error_message", "issue",
        }
    ),
    allowed_values={
        "model_id": frozenset({"hint_places2", "mat_places_512_fulldata"}),
        "requested_device": frozenset({"cuda"}),
        "status": frozenset({"planned", "completed", "failed", "not_executed"}),
        "failure_type": frozenset({
            "none", "model_unavailable", "model_load_failure", "inference_failure",
            "cuda_out_of_memory", "runtime_guardrail", "technical_validation",
        }),
    },
)

HINT_MAT_METRIC_VALUES_SCHEMA = DataFrameSchema(
    name="hint_mat_metric_values",
    version="hint_mat_metric_values.v1",
    required_columns=HINT_MAT_METRIC_VALUE_COLUMNS,
    primary_key=("metric_row_id",),
    non_nullable=tuple(column for column in HINT_MAT_METRIC_VALUE_COLUMNS if column != "issue"),
    allowed_values={
        "model_id": frozenset({"hint_places2", "mat_places_512_fulldata"}),
        "preferred_direction": frozenset({"higher_is_better", "lower_is_better", "descriptive"}),
        "status": frozenset({"ok", "not_applicable", "error"}),
    },
)

HINT_MAT_DECISION_SCORECARD_SCHEMA = DataFrameSchema(
    name="hint_mat_decision_scorecard",
    version="hint_mat_decision_scorecard.v1",
    required_columns=HINT_MAT_DECISION_SCORECARD_COLUMNS,
    primary_key=("scorecard_row_id",),
    non_nullable=tuple(column for column in HINT_MAT_DECISION_SCORECARD_COLUMNS if column != "issue"),
    allowed_values={
        "model_id": frozenset({"hint_places2", "mat_places_512_fulldata"}),
        "preferred_direction": frozenset({"higher_is_better", "lower_is_better", "pass_required", "descriptive"}),
        "status": frozenset({"ok", "warning", "failed", "not_applicable"}),
    },
)

SCHEMA_REGISTRY: dict[str, DataFrameSchema] = {
    ARTIFACT_MANIFEST_SCHEMA.name: ARTIFACT_MANIFEST_SCHEMA,
    VALIDATION_CHECKS_SCHEMA.name: VALIDATION_CHECKS_SCHEMA,
    RAW_ARTWORK_METADATA_SCHEMA.name: RAW_ARTWORK_METADATA_SCHEMA,
    ARTWORKS_SCHEMA.name: ARTWORKS_SCHEMA,
    DATASET_AUDIT_SCHEMA.name: DATASET_AUDIT_SCHEMA,
    PREPROCESSED_IMAGES_SCHEMA.name: PREPROCESSED_IMAGES_SCHEMA,
    PREPROCESSING_AUDIT_SCHEMA.name: PREPROCESSING_AUDIT_SCHEMA,
    CANONICAL_MASKS_SCHEMA.name: CANONICAL_MASKS_SCHEMA,
    MASK_AUDIT_SCHEMA.name: MASK_AUDIT_SCHEMA,
    CANONICAL_DAMAGE_CASES_SCHEMA.name: CANONICAL_DAMAGE_CASES_SCHEMA,
    CANONICAL_DAMAGE_AUDIT_SCHEMA.name: CANONICAL_DAMAGE_AUDIT_SCHEMA,
    DAMAGE_SIZE_CASES_SCHEMA.name: DAMAGE_SIZE_CASES_SCHEMA,
    DAMAGE_SIZE_GENERATION_AUDIT_SCHEMA.name: DAMAGE_SIZE_GENERATION_AUDIT_SCHEMA,
    MASK_ROBUSTNESS_CASES_SCHEMA.name: MASK_ROBUSTNESS_CASES_SCHEMA,
    MASK_ROBUSTNESS_GENERATION_AUDIT_SCHEMA.name: MASK_ROBUSTNESS_GENERATION_AUDIT_SCHEMA,
    SYNTHETIC_DEGRADATION_CASES_SCHEMA.name: SYNTHETIC_DEGRADATION_CASES_SCHEMA,
    SYNTHETIC_DEGRADATION_GENERATION_AUDIT_SCHEMA.name: SYNTHETIC_DEGRADATION_GENERATION_AUDIT_SCHEMA,
    CASE_REGISTRY_SCHEMA.name: CASE_REGISTRY_SCHEMA,
    MODEL_ELIGIBILITY_SCHEMA.name: MODEL_ELIGIBILITY_SCHEMA,
    RESTORATIONS_SCHEMA.name: RESTORATIONS_SCHEMA,
    RESTORATION_RUNTIME_SUMMARY_SCHEMA.name: RESTORATION_RUNTIME_SUMMARY_SCHEMA,
    STABLE_DIFFUSION_CANDIDATES_SCHEMA.name: STABLE_DIFFUSION_CANDIDATES_SCHEMA,
    SDXL_FEASIBILITY_ATTEMPTS_SCHEMA.name: SDXL_FEASIBILITY_ATTEMPTS_SCHEMA,
    SDXL_PARTIAL_CANDIDATES_SCHEMA.name: SDXL_PARTIAL_CANDIDATES_SCHEMA,
    PROMPT_POLICY_SCHEMA.name: PROMPT_POLICY_SCHEMA,
    PROMPT_ABLATION_DESIGN_SCHEMA.name: PROMPT_ABLATION_DESIGN_SCHEMA,
    REGION_POLICY_SCHEMA.name: REGION_POLICY_SCHEMA,
    CLASSICAL_METRICS_SCHEMA.name: CLASSICAL_METRICS_SCHEMA,
    LPIPS_METRICS_SCHEMA.name: LPIPS_METRICS_SCHEMA,
    FEATURE_METRICS_SCHEMA.name: FEATURE_METRICS_SCHEMA,
    FEATURE_EMBEDDING_MANIFEST_SCHEMA.name: FEATURE_EMBEDDING_MANIFEST_SCHEMA,
    SPATIAL_DIAGNOSTICS_SCHEMA.name: SPATIAL_DIAGNOSTICS_SCHEMA,
    SPATIAL_MAP_IMAGE_MANIFEST_SCHEMA.name: SPATIAL_MAP_IMAGE_MANIFEST_SCHEMA,
    LOCAL_CONSISTENCY_SCHEMA.name: LOCAL_CONSISTENCY_SCHEMA,
    LOCAL_CONSISTENCY_MAP_MANIFEST_SCHEMA.name: LOCAL_CONSISTENCY_MAP_MANIFEST_SCHEMA,
    DIFFUSION_UNCERTAINTY_SCHEMA.name: DIFFUSION_UNCERTAINTY_SCHEMA,
    UNCERTAINTY_CALIBRATION_INPUTS_SCHEMA.name: UNCERTAINTY_CALIBRATION_INPUTS_SCHEMA,
    SPATIAL_EXPLANATIONS_SCHEMA.name: SPATIAL_EXPLANATIONS_SCHEMA,
    SPATIAL_EXPLANATION_MAP_IMAGE_SCHEMA.name: SPATIAL_EXPLANATION_MAP_IMAGE_SCHEMA,
    SEMANTIC_STRUCTURAL_METRIC_SCHEMA.name: SEMANTIC_STRUCTURAL_METRIC_SCHEMA,
    SEMANTIC_MAP_ASSET_SCHEMA.name: SEMANTIC_MAP_ASSET_SCHEMA,
    MODEL_COMPARISON_SCHEMA.name: MODEL_COMPARISON_SCHEMA,
    METRIC_DISAGREEMENT_SCHEMA.name: METRIC_DISAGREEMENT_SCHEMA,
    REPRESENTATIVE_CASES_SCHEMA.name: REPRESENTATIVE_CASES_SCHEMA,
    HINT_MAT_SELECTION_SCOPE_SCHEMA.name: HINT_MAT_SELECTION_SCOPE_SCHEMA,
    HINT_MAT_CANDIDATES_SCHEMA.name: HINT_MAT_CANDIDATES_SCHEMA,
    HINT_MAT_METRIC_VALUES_SCHEMA.name: HINT_MAT_METRIC_VALUES_SCHEMA,
    HINT_MAT_DECISION_SCORECARD_SCHEMA.name: HINT_MAT_DECISION_SCORECARD_SCHEMA,
}


def register_schema(schema: DataFrameSchema, *, replace: bool = False) -> None:
    """Register a schema explicitly and reject accidental replacement."""
    if schema.name in SCHEMA_REGISTRY and not replace:
        raise KeyError(f"Schema already registered: {schema.name}")
    SCHEMA_REGISTRY[schema.name] = schema


def get_schema(name: str) -> DataFrameSchema:
    """Return a registered schema by stable name."""
    try:
        return SCHEMA_REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f"Unknown dataframe schema: {name}") from exc
