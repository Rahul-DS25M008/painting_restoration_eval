"""Versioned dataframe and mapping schema contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


SCHEMAS_MODULE_VERSION = "1.6.0"
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

REGION_POLICY_COLUMNS = (
    "policy_id", "policy_version", "metric_family", "region_id",
    "region_type", "spatial_support", "compatible",
    "compatibility_reason", "primary_role", "case_semantics",
    "parameters_json", "threshold_policy", "minimum_size_policy",
    "ablation_policy_ids_json", "status",
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
    REGION_POLICY_SCHEMA.name: REGION_POLICY_SCHEMA,
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
