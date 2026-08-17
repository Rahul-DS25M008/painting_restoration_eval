"""Versioned dataframe and mapping schema contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


SCHEMAS_MODULE_VERSION = "1.0.0"
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
SCHEMA_REGISTRY: dict[str, DataFrameSchema] = {
    ARTIFACT_MANIFEST_SCHEMA.name: ARTIFACT_MANIFEST_SCHEMA,
    VALIDATION_CHECKS_SCHEMA.name: VALIDATION_CHECKS_SCHEMA,
    RAW_ARTWORK_METADATA_SCHEMA.name: RAW_ARTWORK_METADATA_SCHEMA,
    ARTWORKS_SCHEMA.name: ARTWORKS_SCHEMA,
    DATASET_AUDIT_SCHEMA.name: DATASET_AUDIT_SCHEMA,
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
