from __future__ import annotations

import base64
import hashlib
import html
import json
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd


ImageMode = Literal["embedded", "linked"]

REPORT_SCHEMA_VERSION = "2.0.0"
MODEL_NAME_LAMA = "lama"
ZERO_CONTROL_MASK_TYPES = {"zero_control", "empty_mask", "zero", "control"}

CLASSICAL_REPORT_REGION_PREFERENCE = (
    "masked_region",
    "mask_bbox_crop",
    "content_region",
    "full_image",
)
LPIPS_REPORT_REGION = "mask_bbox_crop"
FEATURE_REPORT_REGION = "mask_bbox_crop"

REPORT_REQUIRED_METADATA_COLUMNS = [
    "painting_id",
    "title",
    "artist",
    "category",
]

REPORT_REQUIRED_RESTORATION_COLUMNS = [
    "case_id",
    "painting_id",
    "model_name",
    "clean_path",
    "damaged_path",
    "restored_path",
    "mask_path",
    "status",
]


# ---------------------------------------------------------------------
# Basic path, JSON, validation, and HTML helpers
# ---------------------------------------------------------------------


def project_relative_path(path: Path | str, *, project_root: Path | str) -> str:
    """Return a stable project-relative path when possible."""
    path = Path(path)
    project_root = Path(project_root)

    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_project_path(value: Any, *, project_root: Path | str) -> Path | None:
    """Resolve a possibly relative path value against the project root."""
    if value is None or pd.isna(value):
        return None

    value_text = str(value).strip()

    if value_text == "":
        return None

    path = Path(value_text)

    if path.is_absolute():
        return path

    return Path(project_root) / path


def json_safe(value: Any) -> Any:
    """Convert common notebook objects to JSON-safe values."""
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if not isinstance(value, (list, tuple, dict, set)) and pd.isna(value):
        return None
    return value


def sha256_file(path: Path | str) -> str:
    """Return the SHA256 checksum for a file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_check(
    check_name: str,
    observed: Any,
    expected: Any,
    passed: bool,
    issue: str = "",
) -> dict[str, Any]:
    """Build one validation-row dictionary."""
    return {
        "check_name": check_name,
        "observed": observed,
        "expected": expected,
        "passed": bool(passed),
        "issue": "" if passed else issue,
    }


def artifact_record(
    name: str,
    path: Path | str,
    *,
    artifact_type: str,
    project_root: Path | str,
    required: bool = True,
    include_sha256: bool = True,
) -> dict[str, Any]:
    """Create a compact artifact audit record."""
    path = Path(path)
    exists = path.is_file()

    return {
        "artifact": name,
        "artifact_type": artifact_type,
        "path": project_relative_path(path, project_root=project_root),
        "required": bool(required),
        "exists": bool(exists),
        "size_bytes": int(path.stat().st_size) if exists else 0,
        "sha256": sha256_file(path) if exists and include_sha256 else "",
    }


def image_to_base64(path: Path | str) -> str:
    """Convert an image file to a base64 string for embedding in HTML."""
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"Missing image file: {path}")

    with path.open("rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")


def html_escape(value: Any) -> str:
    """Escape a value for safe HTML display."""
    if value is None or pd.isna(value):
        return ""

    return html.escape(str(value))


def format_float(value: Any, decimals: int = 4) -> str:
    """Format numeric values for compact report tables."""
    if value is None or pd.isna(value):
        return ""

    if value == float("inf"):
        return "inf"
    if value == float("-inf"):
        return "-inf"

    try:
        return f"{float(value):.{decimals}f}"
    except Exception:
        return str(value)


def dataframe_to_html_table(
    df: pd.DataFrame,
    *,
    float_decimals: int = 4,
    max_rows: int | None = None,
) -> str:
    """Convert a dataframe to a compact rounded HTML table."""
    display_df = df.copy()

    if max_rows is not None:
        display_df = display_df.head(max_rows)

    for column in display_df.columns:
        if pd.api.types.is_float_dtype(display_df[column]):
            display_df[column] = display_df[column].map(
                lambda value: format_float(value, decimals=float_decimals)
            )

    return display_df.to_html(
        index=False,
        classes="summary-table",
        escape=True,
        border=0,
    )


def image_block(
    path: Path | str,
    caption: str,
    *,
    project_root: Path | str | None = None,
    width: int = 980,
    mode: ImageMode = "linked",
) -> str:
    """Create an HTML image block for linked or embedded report images."""
    path = Path(path)

    if not path.is_file():
        return f"""
        <div class="image-block missing-image">
            <div class="missing">Missing image: {html_escape(path)}</div>
            <div class="caption">{html_escape(caption)}</div>
        </div>
        """

    if mode == "embedded":
        src = f"data:image/png;base64,{image_to_base64(path)}"
    elif mode == "linked":
        if project_root is None:
            raise ValueError("project_root must be provided when mode='linked'.")
        src = project_relative_path(path, project_root=project_root)
    else:
        raise ValueError(f"Unknown image mode: {mode}")

    return f"""
    <div class="image-block">
        <img src="{src}" width="{width}">
        <div class="caption">{html_escape(caption)}</div>
    </div>
    """


# ---------------------------------------------------------------------
# Input preparation
# ---------------------------------------------------------------------


def require_columns(
    df: pd.DataFrame,
    required_columns: list[str] | tuple[str, ...],
    *,
    dataframe_name: str,
) -> None:
    """Raise a clear error when a dataframe is missing required columns."""
    missing_columns = [column for column in required_columns if column not in df.columns]

    if missing_columns:
        raise ValueError(
            f"{dataframe_name} is missing required columns: {missing_columns}"
        )


def first_existing_column(
    df: pd.DataFrame,
    candidates: list[str] | tuple[str, ...],
) -> str | None:
    """Return the first column from candidates that exists in the dataframe."""
    for column in candidates:
        if column in df.columns:
            return column
    return None


def _normalise_key_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Create a report join key while preserving the original identifiers."""
    df = df.copy()

    if "case_id" not in df.columns:
        for candidate in [
            "restoration_case_id",
            "metric_case_id",
            "source_case_id",
            "feature_case_id",
            "lpips_case_id",
        ]:
            if candidate in df.columns:
                df["case_id"] = df[candidate]
                break

    if "case_id" not in df.columns:
        raise ValueError("Could not infer a case_id column.")

    df["case_id"] = df["case_id"].astype(str)
    return df


def infer_zero_control_flag(row: pd.Series | dict[str, Any]) -> bool:
    """Infer whether a row is a zero/empty-mask control case."""
    getter = row.get

    explicit = getter("is_zero_control", None)
    if explicit is not None and not pd.isna(explicit):
        if isinstance(explicit, str):
            return explicit.strip().lower() in {"true", "1", "yes", "y"}
        return bool(explicit)

    for column in ["mask_type", "metric_mask_type", "mask_id", "metric_mask_id", "case_id"]:
        value = getter(column, None)
        if value is None or pd.isna(value):
            continue
        value_text = str(value).strip().lower()
        if value_text in ZERO_CONTROL_MASK_TYPES or "zero_control" in value_text:
            return True

    mask_area = getter("mask_area_pixels", getter("damaged_area_pixels", None))
    if mask_area is not None and not pd.isna(mask_area):
        try:
            return float(mask_area) == 0.0
        except Exception:
            return False

    return False


def add_zero_control_flag(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure a dataframe has a robust boolean is_zero_control column."""
    df = df.copy()
    df["is_zero_control"] = df.apply(infer_zero_control_flag, axis=1)
    return df


def filter_metric_region(
    metrics_df: pd.DataFrame,
    *,
    region: str,
    dataframe_name: str,
    status_ok_only: bool = True,
) -> pd.DataFrame:
    """Filter a metric dataframe to one evaluation region."""
    metrics_df = _normalise_key_columns(metrics_df)
    require_columns(
        metrics_df,
        ["case_id", "evaluation_region"],
        dataframe_name=dataframe_name,
    )

    region_mask = metrics_df["evaluation_region"].astype(str).eq(region)

    if status_ok_only and "status" in metrics_df.columns:
        region_mask &= metrics_df["status"].astype(str).eq("ok")

    region_df = metrics_df.loc[region_mask].copy()

    if region_df.empty:
        raise ValueError(
            f"No rows found in {dataframe_name} for evaluation_region={region!r}."
        )

    return region_df


def select_first_available_region(
    metrics_df: pd.DataFrame,
    *,
    preferred_regions: tuple[str, ...],
    dataframe_name: str,
) -> tuple[str, pd.DataFrame]:
    """Select the first available metric region from a preferred list."""
    metrics_df = _normalise_key_columns(metrics_df)
    require_columns(metrics_df, ["evaluation_region"], dataframe_name=dataframe_name)
    available_regions = set(metrics_df["evaluation_region"].dropna().astype(str))

    for region in preferred_regions:
        if region in available_regions:
            return region, filter_metric_region(
                metrics_df,
                region=region,
                dataframe_name=dataframe_name,
            )

    raise ValueError(
        f"{dataframe_name} has none of the preferred regions {preferred_regions}. "
        f"Available regions: {sorted(available_regions)}"
    )


def prepare_figure_manifest_paths(
    figure_manifest_df: pd.DataFrame | None,
    *,
    project_root: Path | str,
    key_column: str = "case_id",
    output_column: str = "error_map_figure_path",
) -> pd.DataFrame:
    """Prepare case-to-figure paths from an error/difference-map manifest."""
    if figure_manifest_df is None or figure_manifest_df.empty:
        return pd.DataFrame(columns=[key_column, output_column])

    figure_manifest_df = _normalise_key_columns(figure_manifest_df)
    require_columns(figure_manifest_df, [key_column], dataframe_name="figure_manifest_df")

    path_column = first_existing_column(
        figure_manifest_df,
        [
            "figure_path",
            "error_map_figure_path",
            "difference_map_figure_path",
            "output_path",
            "output_figure_path",
            "saved_figure_path",
            "figure_file_path",
            "relative_path",
            "path",
        ],
    )

    if path_column is None:
        return figure_manifest_df[[key_column]].drop_duplicates().assign(
            **{output_column: ""}
        )

    prepared_df = figure_manifest_df[[key_column, path_column]].copy()
    prepared_df = prepared_df.rename(columns={path_column: output_column})

    prepared_df[output_column] = prepared_df[output_column].map(
        lambda value: resolve_project_path(value, project_root=project_root)
    )

    return prepared_df.drop_duplicates(subset=[key_column])


def _available_columns(
    df: pd.DataFrame,
    columns: list[str] | tuple[str, ...],
) -> list[str]:
    """Return columns that exist, preserving requested order."""
    return [column for column in columns if column in df.columns]


def _rename_metric_columns(
    df: pd.DataFrame,
    *,
    prefix: str,
    passthrough_columns: list[str],
) -> pd.DataFrame:
    """Prefix non-key metric columns after a region-specific merge."""
    rename_map = {
        column: f"{prefix}_{column}"
        for column in df.columns
        if column not in passthrough_columns and not column.startswith(f"{prefix}_")
    }
    return df.rename(columns=rename_map)


def prepare_lama_report_dataframe(
    *,
    processed_metadata_df: pd.DataFrame,
    restored_metadata_df: pd.DataFrame,
    classical_metrics_df: pd.DataFrame,
    lpips_metrics_df: pd.DataFrame,
    feature_metrics_df: pd.DataFrame,
    error_map_manifest_df: pd.DataFrame | None = None,
    project_root: Path | str = ".",
    model_name: str = MODEL_NAME_LAMA,
    include_zero_control: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build one report-ready LaMa dataframe from standardized metric outputs."""
    project_root = Path(project_root)

    require_columns(
        processed_metadata_df,
        REPORT_REQUIRED_METADATA_COLUMNS,
        dataframe_name="processed_metadata_df",
    )
    require_columns(
        restored_metadata_df,
        REPORT_REQUIRED_RESTORATION_COLUMNS,
        dataframe_name="restored_metadata_df",
    )

    restored_df = _normalise_key_columns(restored_metadata_df)
    restored_df = add_zero_control_flag(restored_df)
    restored_df = restored_df.loc[restored_df["model_name"].astype(str).eq(model_name)].copy()

    if "status" in restored_df.columns:
        restored_df = restored_df.loc[restored_df["status"].astype(str).eq("ok")].copy()

    if not include_zero_control:
        restored_df = restored_df.loc[~restored_df["is_zero_control"].astype(bool)].copy()

    if restored_df.empty:
        raise ValueError("No LaMa restoration rows available for report dataframe.")

    metadata_columns = _available_columns(
        processed_metadata_df,
        [
            "painting_id",
            "title",
            "artist",
            "date",
            "category",
            "style",
            "style_or_period",
            "medium",
            "source",
            "source_url",
            "license",
            "filename",
        ],
    )

    report_df = restored_df.merge(
        processed_metadata_df[metadata_columns].drop_duplicates("painting_id"),
        on="painting_id",
        how="left",
        validate="many_to_one",
    )

    classical_region, classical_region_df = select_first_available_region(
        classical_metrics_df,
        preferred_regions=CLASSICAL_REPORT_REGION_PREFERENCE,
        dataframe_name="classical_metrics_df",
    )

    classical_metric_columns = _available_columns(
        classical_region_df,
        [
            "case_id",
            "damaged_mse",
            "restored_mse",
            "mse_improvement",
            "damaged_mae",
            "restored_mae",
            "mae_improvement",
            "damaged_psnr",
            "restored_psnr",
            "psnr_improvement",
            "damaged_ssim",
            "restored_ssim",
            "ssim_improvement",
            "region_pixel_count",
        ],
    )

    classical_merge_df = classical_region_df[classical_metric_columns].drop_duplicates("case_id")
    report_df = report_df.merge(
        classical_merge_df,
        on="case_id",
        how="left",
        validate="one_to_one",
    )

    lpips_region_df = filter_metric_region(
        lpips_metrics_df,
        region=LPIPS_REPORT_REGION,
        dataframe_name="lpips_metrics_df",
    )

    lpips_columns = _available_columns(
        lpips_region_df,
        [
            "case_id",
            "damaged_lpips",
            "restored_lpips",
            "lpips_improvement",
            "lpips_improved",
            "region_pixel_count",
        ],
    )
    lpips_merge_df = _rename_metric_columns(
        lpips_region_df[lpips_columns].drop_duplicates("case_id"),
        prefix="lpips",
        passthrough_columns=["case_id"],
    )
    report_df = report_df.merge(
        lpips_merge_df,
        on="case_id",
        how="left",
        validate="one_to_one",
    )

    if "lpips_lpips_improvement" in report_df.columns and "lpips_improvement" not in report_df.columns:
        report_df["lpips_improvement"] = report_df["lpips_lpips_improvement"]

    feature_region_df = filter_metric_region(
        feature_metrics_df,
        region=FEATURE_REPORT_REGION,
        dataframe_name="feature_metrics_df",
    )

    feature_columns = _available_columns(
        feature_region_df,
        [
            "case_id",
            "clip_damaged_similarity",
            "clip_restored_similarity",
            "clip_similarity_improvement",
            "dinov2_damaged_similarity",
            "dinov2_restored_similarity",
            "dinov2_similarity_improvement",
            "mean_damaged_similarity",
            "mean_restored_similarity",
            "mean_similarity_improvement",
            "region_pixel_count",
        ],
    )
    feature_merge_df = _rename_metric_columns(
        feature_region_df[feature_columns].drop_duplicates("case_id"),
        prefix="feature",
        passthrough_columns=["case_id"],
    )
    report_df = report_df.merge(
        feature_merge_df,
        on="case_id",
        how="left",
        validate="one_to_one",
    )

    for column in [
        "clip_similarity_improvement",
        "dinov2_similarity_improvement",
        "mean_similarity_improvement",
    ]:
        prefixed_column = f"feature_{column}"
        if prefixed_column in report_df.columns and column not in report_df.columns:
            report_df[column] = report_df[prefixed_column]

    figure_paths_df = prepare_figure_manifest_paths(
        error_map_manifest_df,
        project_root=project_root,
    )

    if not figure_paths_df.empty:
        report_df = report_df.merge(figure_paths_df, on="case_id", how="left")
    else:
        report_df["error_map_figure_path"] = None

    for path_column in ["clean_path", "damaged_path", "restored_path", "mask_path"]:
        if path_column in report_df.columns:
            report_df[f"{path_column}_resolved"] = report_df[path_column].map(
                lambda value: resolve_project_path(value, project_root=project_root)
            )

    report_df["report_schema_version"] = REPORT_SCHEMA_VERSION
    report_df["classical_report_region"] = classical_region
    report_df["lpips_report_region"] = LPIPS_REPORT_REGION
    report_df["feature_report_region"] = FEATURE_REPORT_REGION

    required_output_columns = [
        "case_id",
        "painting_id",
        "mask_type",
        "model_name",
        "category",
        "title",
        "mse_improvement",
        "lpips_improvement",
        "clip_similarity_improvement",
        "dinov2_similarity_improvement",
    ]
    missing_output_columns = [
        column for column in required_output_columns if column not in report_df.columns
    ]

    if missing_output_columns:
        raise ValueError(
            "Prepared LaMa report dataframe is missing expected output columns: "
            f"{missing_output_columns}"
        )

    report_df = report_df.sort_values(
        ["dataset_name", "painting_id", "mask_type", "case_id"],
        kind="stable",
    ).reset_index(drop=True)

    contract = {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "model_name": model_name,
        "include_zero_control": bool(include_zero_control),
        "classical_report_region": classical_region,
        "lpips_report_region": LPIPS_REPORT_REGION,
        "feature_report_region": FEATURE_REPORT_REGION,
        "input_rows": {
            "processed_metadata": int(len(processed_metadata_df)),
            "restored_metadata": int(len(restored_metadata_df)),
            "classical_metrics": int(len(classical_metrics_df)),
            "lpips_metrics": int(len(lpips_metrics_df)),
            "feature_metrics": int(len(feature_metrics_df)),
            "error_map_manifest": int(len(error_map_manifest_df))
            if error_map_manifest_df is not None
            else 0,
        },
        "report_rows": int(len(report_df)),
        "report_dataset_counts": {
            key: int(value)
            for key, value in report_df["dataset_name"].value_counts(dropna=False).to_dict().items()
        }
        if "dataset_name" in report_df.columns
        else {},
        "report_mask_counts": {
            key: int(value)
            for key, value in report_df["mask_type"].value_counts(dropna=False).to_dict().items()
        },
    }

    return report_df, contract


# ---------------------------------------------------------------------
# Summary and diagnostic case selection
# ---------------------------------------------------------------------


def summarize_report_overview(
    *,
    processed_metadata_df: pd.DataFrame,
    restored_metadata_df: pd.DataFrame,
    report_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build a compact LaMa report overview table."""
    restored_df = add_zero_control_flag(_normalise_key_columns(restored_metadata_df))

    rows = [
        {"item": "Paintings", "value": int(processed_metadata_df["painting_id"].nunique())},
        {"item": "Painting categories", "value": int(processed_metadata_df["category"].nunique())},
        {"item": "Restoration rows", "value": int(len(restored_df))},
        {"item": "Report cases", "value": int(len(report_df))},
        {"item": "Zero-control restoration rows", "value": int(restored_df["is_zero_control"].sum())},
        {
            "item": "Datasets",
            "value": ", ".join(sorted(report_df.get("dataset_name", pd.Series(dtype=str)).dropna().astype(str).unique())),
        },
        {
            "item": "Mask types in report",
            "value": ", ".join(sorted(report_df["mask_type"].dropna().astype(str).unique())),
        },
        {
            "item": "Model",
            "value": ", ".join(sorted(report_df["model_name"].dropna().astype(str).unique())),
        },
    ]

    return pd.DataFrame(rows)


def summarize_report_by_group(
    report_df: pd.DataFrame,
    *,
    group_columns: list[str],
) -> pd.DataFrame:
    """Summarize report metrics by dataset, mask, category, or another group."""
    require_columns(report_df, group_columns, dataframe_name="report_df")

    aggregations: dict[str, tuple[str, Any]] = {
        "cases": ("case_id", "count"),
        "mean_mse_improvement": ("mse_improvement", "mean"),
        "median_mse_improvement": ("mse_improvement", "median"),
        "mean_lpips_improvement": ("lpips_improvement", "mean"),
        "median_lpips_improvement": ("lpips_improvement", "median"),
        "mean_clip_similarity_improvement": ("clip_similarity_improvement", "mean"),
        "median_clip_similarity_improvement": ("clip_similarity_improvement", "median"),
        "mean_dinov2_similarity_improvement": ("dinov2_similarity_improvement", "mean"),
        "median_dinov2_similarity_improvement": ("dinov2_similarity_improvement", "median"),
        "mean_feature_similarity_improvement": ("mean_similarity_improvement", "mean"),
        "feature_improvement_rate": (
            "mean_similarity_improvement",
            lambda values: float(pd.Series(values).gt(0).mean()),
        ),
    }

    if "runtime_seconds" in report_df.columns:
        aggregations["mean_runtime_seconds"] = ("runtime_seconds", "mean")
    elif "restoration_runtime_seconds" in report_df.columns:
        aggregations["mean_runtime_seconds"] = ("restoration_runtime_seconds", "mean")

    summary_df = (
        report_df.groupby(group_columns, dropna=False)
        .agg(**aggregations)
        .reset_index()
    )

    numeric_columns = summary_df.select_dtypes(include=[np.number]).columns
    summary_df[numeric_columns] = summary_df[numeric_columns].round(6)

    return summary_df


def summarize_report_by_dataset(report_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize report metrics by dataset."""
    return summarize_report_by_group(report_df, group_columns=["dataset_name"])


def summarize_report_by_mask_type(report_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize report metrics by mask type."""
    return summarize_report_by_group(report_df, group_columns=["mask_type"])


def summarize_report_by_category(report_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize report metrics by painting category."""
    return summarize_report_by_group(report_df, group_columns=["category"])


def summarize_report_by_dataset_mask(report_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize report metrics by dataset and mask type."""
    return summarize_report_by_group(report_df, group_columns=["dataset_name", "mask_type"])


def summarize_runtime_and_failures(restored_metadata_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize restoration runtime and failure status by dataset."""
    restored_df = _normalise_key_columns(restored_metadata_df)

    if "dataset_name" not in restored_df.columns:
        restored_df["dataset_name"] = "unknown"
    if "status" not in restored_df.columns:
        restored_df["status"] = "unknown"

    runtime_column = first_existing_column(
        restored_df,
        ["runtime_seconds", "restoration_runtime_seconds", "elapsed_seconds"],
    )

    aggregations: dict[str, tuple[str, Any]] = {
        "rows": ("case_id", "count"),
        "ok_rows": ("status", lambda values: int(pd.Series(values).astype(str).eq("ok").sum())),
        "failed_rows": (
            "status",
            lambda values: int((~pd.Series(values).astype(str).eq("ok")).sum()),
        ),
    }

    if runtime_column is not None:
        aggregations["mean_runtime_seconds"] = (runtime_column, "mean")
        aggregations["median_runtime_seconds"] = (runtime_column, "median")
        aggregations["max_runtime_seconds"] = (runtime_column, "max")

    summary_df = (
        restored_df.groupby("dataset_name", dropna=False)
        .agg(**aggregations)
        .reset_index()
    )

    numeric_columns = summary_df.select_dtypes(include=[np.number]).columns
    summary_df[numeric_columns] = summary_df[numeric_columns].round(6)

    return summary_df


def summarize_metric_correlations(report_df: pd.DataFrame) -> pd.DataFrame:
    """Return the main multi-metric correlation matrix."""
    correlation_columns = [
        "mse_improvement",
        "mae_improvement",
        "psnr_improvement",
        "ssim_improvement",
        "lpips_improvement",
        "clip_similarity_improvement",
        "dinov2_similarity_improvement",
        "mean_similarity_improvement",
    ]

    available_columns = [
        column for column in correlation_columns
        if column in report_df.columns
    ]

    if len(available_columns) < 2:
        return pd.DataFrame()

    return report_df[available_columns].apply(pd.to_numeric, errors="coerce").corr().round(4)


def _select_top_cases(
    report_df: pd.DataFrame,
    *,
    metric: str,
    label: str,
    ascending: bool,
    n: int,
) -> pd.DataFrame:
    """Select top cases for one metric and attach a selection reason."""
    if metric not in report_df.columns:
        return pd.DataFrame(columns=list(report_df.columns) + ["selection_reason", "selection_metric"])

    selected_df = (
        report_df.dropna(subset=[metric])
        .sort_values(metric, ascending=ascending, kind="stable")
        .head(n)
        .copy()
    )

    selected_df["selection_reason"] = label
    selected_df["selection_metric"] = metric

    return selected_df


def select_lama_diagnostic_cases(
    report_df: pd.DataFrame,
    *,
    n_per_signal: int = 5,
    include_dataset_examples: bool = True,
    include_category_examples: bool = True,
) -> pd.DataFrame:
    """Select representative LaMa cases for qualitative report inspection."""
    selections = [
        _select_top_cases(
            report_df,
            metric="mse_improvement",
            label="Strongest local MSE improvement",
            ascending=False,
            n=n_per_signal,
        ),
        _select_top_cases(
            report_df,
            metric="mse_improvement",
            label="Weakest local MSE improvement",
            ascending=True,
            n=n_per_signal,
        ),
        _select_top_cases(
            report_df,
            metric="lpips_improvement",
            label="Strongest local LPIPS improvement",
            ascending=False,
            n=n_per_signal,
        ),
        _select_top_cases(
            report_df,
            metric="lpips_improvement",
            label="Weakest local LPIPS improvement",
            ascending=True,
            n=n_per_signal,
        ),
        _select_top_cases(
            report_df,
            metric="mean_similarity_improvement",
            label="Strongest local feature-similarity improvement",
            ascending=False,
            n=n_per_signal,
        ),
        _select_top_cases(
            report_df,
            metric="mean_similarity_improvement",
            label="Weakest local feature-similarity improvement",
            ascending=True,
            n=n_per_signal,
        ),
    ]

    runtime_column = first_existing_column(
        report_df,
        ["runtime_seconds", "restoration_runtime_seconds", "elapsed_seconds"],
    )
    if runtime_column is not None:
        selections.append(
            _select_top_cases(
                report_df,
                metric=runtime_column,
                label="Slowest restoration runtime",
                ascending=False,
                n=n_per_signal,
            )
        )

    if include_dataset_examples and "dataset_name" in report_df.columns:
        dataset_examples = (
            report_df.sort_values("mean_similarity_improvement", ascending=False, kind="stable")
            .groupby("dataset_name", dropna=False)
            .head(1)
            .copy()
        )
        dataset_examples["selection_reason"] = "Representative high-scoring dataset example"
        dataset_examples["selection_metric"] = "mean_similarity_improvement"
        selections.append(dataset_examples)

    if include_category_examples and "category" in report_df.columns:
        category_examples = (
            report_df.sort_values("mean_similarity_improvement", ascending=False, kind="stable")
            .groupby("category", dropna=False)
            .head(1)
            .copy()
        )
        category_examples["selection_reason"] = "Representative high-scoring category example"
        category_examples["selection_metric"] = "mean_similarity_improvement"
        selections.append(category_examples)

    selected_df = pd.concat(selections, ignore_index=True)

    if selected_df.empty:
        return selected_df

    reason_df = (
        selected_df.groupby("case_id")
        .agg(
            selection_reason=("selection_reason", lambda values: "; ".join(sorted(set(values)))),
            selection_metric=("selection_metric", lambda values: "; ".join(sorted(set(values)))),
        )
        .reset_index()
    )

    base_columns = [
        column for column in selected_df.columns if column not in ["selection_reason", "selection_metric"]
    ]

    return (
        selected_df[base_columns]
        .drop_duplicates(subset=["case_id"])
        .merge(reason_df, on="case_id", how="left")
        .sort_values(["dataset_name", "painting_id", "mask_type", "case_id"], kind="stable")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------
# HTML report generation
# ---------------------------------------------------------------------


def interpret_lama_case(row: pd.Series) -> str:
    """Generate a short LaMa-specific interpretation for one selected case."""
    mask_type = str(row.get("mask_type", ""))
    dataset_name = str(row.get("dataset_name", ""))
    mse_improvement = row.get("mse_improvement", np.nan)
    lpips_improvement = row.get("lpips_improvement", np.nan)
    feature_improvement = row.get("mean_similarity_improvement", np.nan)

    comments: list[str] = []

    if dataset_name == "synthetic_degradation":
        comments.append(
            "This synthetic-degradation case checks whether LaMa remains reliable outside the canonical white-mask setup."
        )
    elif dataset_name == "damage_size":
        comments.append(
            "This damage-size case probes how local evidence changes as the damaged area changes."
        )
    elif dataset_name == "mask_robustness":
        comments.append(
            "This mask-robustness case checks whether the result is stable under mask perturbation."
        )
    else:
        comments.append(
            "This canonical case shows the baseline behavior under the standard LaMa restoration setup."
        )

    if mask_type == "scratch_thin":
        comments.append("Thin scratches mainly test local continuation and texture preservation.")
    elif mask_type == "loss_small":
        comments.append("Small losses test compact reconstruction from surrounding context.")
    elif mask_type == "loss_large":
        comments.append("Large losses are more demanding because broader structure may need reconstruction.")
    elif mask_type == "mixed_damage":
        comments.append("Mixed damage combines several degradation patterns in one case.")

    if pd.notna(mse_improvement):
        comments.append(
            "Local MSE improves." if float(mse_improvement) > 0 else "Local MSE does not improve."
        )

    if pd.notna(lpips_improvement):
        comments.append(
            "LPIPS improves." if float(lpips_improvement) > 0 else "LPIPS does not improve."
        )

    if pd.notna(feature_improvement):
        comments.append(
            "Mean feature similarity improves."
            if float(feature_improvement) > 0
            else "Mean feature similarity does not improve."
        )

    return " ".join(comments)


def build_key_findings_html(
    *,
    summary_by_dataset: pd.DataFrame,
    summary_by_mask: pd.DataFrame,
    summary_by_category: pd.DataFrame,
    correlation_df: pd.DataFrame,
    runtime_summary_df: pd.DataFrame | None = None,
) -> str:
    """Build the main LaMa textual interpretation section."""
    strongest_dataset = summary_by_dataset.sort_values(
        "mean_feature_similarity_improvement",
        ascending=False,
    ).iloc[0]

    weakest_dataset = summary_by_dataset.sort_values(
        "mean_feature_similarity_improvement",
        ascending=True,
    ).iloc[0]

    strongest_mask = summary_by_mask.sort_values(
        "mean_lpips_improvement",
        ascending=False,
    ).iloc[0]

    weakest_category = summary_by_category.sort_values(
        "mean_feature_similarity_improvement",
        ascending=True,
    ).iloc[0]

    corr_html = (
        dataframe_to_html_table(
            correlation_df.reset_index().rename(columns={"index": "metric"}),
            float_decimals=4,
        )
        if not correlation_df.empty
        else "<p>No metric correlation table was available.</p>"
    )

    runtime_html = ""
    if runtime_summary_df is not None and not runtime_summary_df.empty:
        runtime_html = f"""
        <h3>Runtime and failure summary</h3>
        {dataframe_to_html_table(runtime_summary_df, float_decimals=4)}
        """

    return f"""
    <h2>Key findings</h2>

    <p>
        The strongest average feature-similarity behavior is observed for
        <b>{html_escape(strongest_dataset['dataset_name'])}</b>, while the weakest is observed for
        <b>{html_escape(weakest_dataset['dataset_name'])}</b>. This keeps the report aligned with
        the dataset-level evidence from the metric notebooks instead of collapsing all cases into
        one undifferentiated average.
    </p>

    <p>
        The strongest average local LPIPS improvement is observed for mask type
        <b>{html_escape(strongest_mask['mask_type'])}</b>. The weakest category-level feature
        behavior is observed for <b>{html_escape(weakest_category['category'])}</b>.
    </p>

    <p>
        The correlation table shows where classical, perceptual, and feature-space signals agree
        or diverge. Disagreement is treated as useful evidence for restoration evaluation rather
        than as a reporting problem.
    </p>

    <h3>Main metric correlation matrix</h3>
    {corr_html}
    {runtime_html}
    """


def build_selected_case_sections_html(
    selected_cases_df: pd.DataFrame,
    *,
    project_root: Path | str,
    image_mode: ImageMode = "linked",
    image_width: int = 980,
) -> str:
    """Build selected LaMa diagnostic case sections using difference/error-map figures."""
    if selected_cases_df.empty:
        return "<p>No selected diagnostic cases were provided.</p>"

    sections: list[str] = []

    for _, row in selected_cases_df.iterrows():
        figure_path_value = row.get("error_map_figure_path", None)
        figure_path = (
            Path(str(figure_path_value))
            if figure_path_value is not None and not pd.isna(figure_path_value)
            else None
        )

        if figure_path is not None:
            figure_html = image_block(
                figure_path,
                caption="Difference/error-map diagnostic figure",
                project_root=project_root,
                width=image_width,
                mode=image_mode,
            )
        else:
            figure_html = "<p class=\"missing\">No diagnostic figure path available for this case.</p>"

        metric_table = pd.DataFrame(
            [
                {
                    "case_id": row.get("case_id", ""),
                    "dataset_name": row.get("dataset_name", ""),
                    "category": row.get("category", ""),
                    "mask_type": row.get("mask_type", ""),
                    "mse_improvement": row.get("mse_improvement", np.nan),
                    "lpips_improvement": row.get("lpips_improvement", np.nan),
                    "clip_improvement": row.get("clip_similarity_improvement", np.nan),
                    "dinov2_improvement": row.get("dinov2_similarity_improvement", np.nan),
                    "mean_feature_improvement": row.get("mean_similarity_improvement", np.nan),
                }
            ]
        )

        sections.append(
            f"""
            <section class="case-section">
                <h3>{html_escape(row.get("case_id", ""))}: {html_escape(row.get("title", ""))}</h3>

                <p>
                    <b>Selection reason:</b> {html_escape(row.get("selection_reason", ""))}<br>
                    <b>Painting ID:</b> {html_escape(row.get("painting_id", ""))}<br>
                    <b>Dataset:</b> {html_escape(row.get("dataset_name", ""))}<br>
                    <b>Category:</b> {html_escape(row.get("category", ""))}<br>
                    <b>Mask type:</b> {html_escape(row.get("mask_type", ""))}<br>
                    <b>Artist:</b> {html_escape(row.get("artist", ""))}<br>
                    <b>Date:</b> {html_escape(row.get("date", ""))}
                </p>

                {dataframe_to_html_table(metric_table, float_decimals=5)}

                <p><b>Interpretation:</b> {html_escape(interpret_lama_case(row))}</p>

                {figure_html}
            </section>
            """
        )

    return "\n".join(sections)


def build_lama_report_html(
    *,
    overview_df: pd.DataFrame,
    summary_by_dataset: pd.DataFrame,
    summary_by_mask: pd.DataFrame,
    summary_by_category: pd.DataFrame,
    correlation_df: pd.DataFrame,
    selected_cases_df: pd.DataFrame,
    runtime_summary_df: pd.DataFrame | None,
    project_root: Path | str,
    image_mode: ImageMode = "linked",
    title: str = "LaMa Restoration Evaluation Report",
) -> str:
    """Build the full LaMa HTML report."""
    overview_html = dataframe_to_html_table(overview_df, float_decimals=4)
    dataset_summary_html = dataframe_to_html_table(summary_by_dataset, float_decimals=5)
    mask_summary_html = dataframe_to_html_table(summary_by_mask, float_decimals=5)
    category_summary_html = dataframe_to_html_table(summary_by_category, float_decimals=5)

    key_findings_html = build_key_findings_html(
        summary_by_dataset=summary_by_dataset,
        summary_by_mask=summary_by_mask,
        summary_by_category=summary_by_category,
        correlation_df=correlation_df,
        runtime_summary_df=runtime_summary_df,
    )

    selected_cases_html = build_selected_case_sections_html(
        selected_cases_df,
        project_root=project_root,
        image_mode=image_mode,
    )

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{html_escape(title)}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 36px;
                background-color: #f8fafc;
                color: #1f2937;
                line-height: 1.55;
            }}

            h1 {{
                color: #111827;
                border-bottom: 2px solid #374151;
                padding-bottom: 10px;
            }}

            h2 {{
                margin-top: 34px;
                color: #1f2937;
            }}

            h3 {{
                margin-top: 24px;
                color: #374151;
            }}

            .summary,
            .case-section {{
                background: white;
                padding: 22px;
                border-radius: 8px;
                margin-bottom: 28px;
                border: 1px solid #d1d5db;
            }}

            .case-section {{
                page-break-inside: avoid;
            }}

            .image-block {{
                text-align: center;
                font-size: 12px;
                margin-top: 15px;
            }}

            .image-block img {{
                border: 1px solid #d1d5db;
                background: #f3f4f6;
                max-width: 100%;
                height: auto;
            }}

            .caption {{
                margin-top: 6px;
                color: #4b5563;
            }}

            .missing {{
                color: #9a3412;
                font-style: italic;
            }}

            table,
            .summary-table {{
                border-collapse: collapse;
                margin-top: 15px;
                margin-bottom: 18px;
                width: 100%;
                font-size: 13px;
                background: white;
            }}

            th,
            td,
            .summary-table th,
            .summary-table td {{
                border: 1px solid #d1d5db;
                padding: 7px;
                text-align: center;
                vertical-align: middle;
            }}

            th,
            .summary-table th {{
                background-color: #e5e7eb;
                font-weight: bold;
            }}

            .note {{
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                padding: 12px;
                border-radius: 6px;
            }}
        </style>
    </head>

    <body>
        <h1>{html_escape(title)}</h1>

        <div class="summary">
            <h2>Experiment overview</h2>
            <p>
                This report consolidates the LaMa restoration baseline across the standardized
                restoration manifest, classical metrics, LPIPS metrics, feature-similarity metrics,
                runtime/failure audit information, and selected diagnostic figures.
            </p>

            {overview_html}

            <p class="note">
                The report is a synthesis artifact. It does not replace the raw metric notebooks;
                it records the region-aware evidence needed to inspect LaMa behavior and prepare
                downstream model comparisons.
            </p>
        </div>

        <div class="summary">
            <h2>Dataset summary</h2>
            {dataset_summary_html}

            <h2>Mask summary</h2>
            {mask_summary_html}

            <h2>Category summary</h2>
            {category_summary_html}

            {key_findings_html}
        </div>

        <div class="summary">
            <h2>Selected diagnostic cases</h2>
            <p>
                The selected cases combine strongest and weakest metric outcomes, dataset examples,
                category examples, and runtime outliers when runtime data is available.
            </p>

            {selected_cases_html}
        </div>

        <div class="summary">
            <h2>Report conclusion</h2>
            <p>
                LaMa often improves damaged local regions under classical, perceptual, and feature
                metrics, but the dataset, mask, and category summaries show that the behavior is not
                uniform. The report therefore keeps metric families separate and uses selected cases
                for qualitative inspection.
            </p>

            <p>
                This handoff prepares the LaMa baseline for later grouping, comparison, risk-flag,
                and diffusion-model evaluation notebooks.
            </p>
        </div>
    </body>
    </html>
    """


# ---------------------------------------------------------------------
# Validation and handoff helpers
# ---------------------------------------------------------------------


def validate_lama_report_artifacts(
    *,
    report_df: pd.DataFrame,
    selected_cases_df: pd.DataFrame,
    output_paths: dict[str, Path | str],
    project_root: Path | str,
    expected_model_name: str = MODEL_NAME_LAMA,
    require_error_map_paths: bool = True,
) -> pd.DataFrame:
    """Validate report dataframes and saved report artifacts."""
    project_root = Path(project_root)

    artifact_records = [
        artifact_record(
            name,
            path,
            artifact_type="html" if str(path).endswith(".html") else "csv" if str(path).endswith(".csv") else "json",
            project_root=project_root,
            required=True,
            include_sha256=False,
        )
        for name, path in output_paths.items()
    ]

    missing_report_columns = [
        column
        for column in [
            "case_id",
            "painting_id",
            "dataset_name",
            "mask_type",
            "model_name",
            "category",
            "mse_improvement",
            "lpips_improvement",
            "clip_similarity_improvement",
            "dinov2_similarity_improvement",
            "mean_similarity_improvement",
        ]
        if column not in report_df.columns
    ]

    metric_columns = [
        "mse_improvement",
        "lpips_improvement",
        "clip_similarity_improvement",
        "dinov2_similarity_improvement",
        "mean_similarity_improvement",
    ]
    finite_metrics = True
    if not missing_report_columns:
        finite_metrics = bool(
            np.isfinite(
                report_df[metric_columns].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
            ).all()
        )

    if require_error_map_paths and "error_map_figure_path" in report_df.columns:
        missing_error_maps = [
            str(value)
            for value in report_df["error_map_figure_path"]
            if value is None or pd.isna(value) or not Path(str(value)).is_file()
        ]
    else:
        missing_error_maps = []

    checks = [
        build_check(
            "report_dataframe_nonempty",
            len(report_df),
            "> 0",
            len(report_df) > 0,
            "report dataframe is empty",
        ),
        build_check(
            "selected_cases_nonempty",
            len(selected_cases_df),
            "> 0",
            len(selected_cases_df) > 0,
            "selected cases dataframe is empty",
        ),
        build_check(
            "required_report_columns_present",
            missing_report_columns,
            [],
            not missing_report_columns,
            "report dataframe missing required columns",
        ),
        build_check(
            "only_lama_model_rows",
            sorted(report_df["model_name"].dropna().astype(str).unique().tolist())
            if "model_name" in report_df.columns
            else [],
            [expected_model_name],
            "model_name" in report_df.columns
            and set(report_df["model_name"].dropna().astype(str).unique()) == {expected_model_name},
            "report dataframe contains unexpected model rows",
        ),
        build_check(
            "zero_controls_excluded",
            int(report_df["is_zero_control"].astype(bool).sum())
            if "is_zero_control" in report_df.columns
            else None,
            0,
            "is_zero_control" in report_df.columns
            and int(report_df["is_zero_control"].astype(bool).sum()) == 0,
            "zero-control rows should not be in the main report dataframe",
        ),
        build_check(
            "metric_values_finite",
            finite_metrics,
            True,
            finite_metrics,
            "one or more report metric values are missing or non-finite",
        ),
        build_check(
            "selected_cases_unique",
            int(selected_cases_df["case_id"].nunique())
            if "case_id" in selected_cases_df.columns
            else 0,
            len(selected_cases_df),
            "case_id" in selected_cases_df.columns
            and int(selected_cases_df["case_id"].nunique()) == len(selected_cases_df),
            "selected cases contain duplicate case IDs",
        ),
        build_check(
            "error_map_paths_exist",
            len(missing_error_maps),
            0,
            len(missing_error_maps) == 0,
            "one or more selected/report error-map paths are missing",
        ),
        build_check(
            "output_artifacts_exist",
            {record["artifact"]: record["exists"] for record in artifact_records},
            "all true",
            all(record["exists"] for record in artifact_records),
            "one or more output artifacts are missing",
        ),
        build_check(
            "output_artifacts_nonempty",
            {record["artifact"]: record["size_bytes"] for record in artifact_records},
            "all > 0",
            all(record["size_bytes"] > 0 for record in artifact_records),
            "one or more output artifacts are empty",
        ),
    ]

    return pd.DataFrame(checks)


def build_lama_report_handoff_manifest(
    *,
    notebook_id: str,
    notebook_name: str,
    project_root: Path | str,
    input_paths: dict[str, Path | str],
    output_paths: dict[str, Path | str],
    report_contract: dict[str, Any],
    validation_df: pd.DataFrame,
    table_shapes: dict[str, dict[str, int]],
) -> dict[str, Any]:
    """Build the final JSON handoff manifest for notebook 19."""
    project_root = Path(project_root)

    return {
        "manifest_type": "lama_report_generation_handoff",
        "handoff_status": "ready_for_downstream_analysis"
        if bool(validation_df["passed"].astype(bool).all())
        else "blocked",
        "notebook": {
            "id": notebook_id,
            "name": notebook_name,
            "model_name": MODEL_NAME_LAMA,
            "report_schema_version": REPORT_SCHEMA_VERSION,
        },
        "inputs": {
            name: project_relative_path(path, project_root=project_root)
            for name, path in input_paths.items()
        },
        "outputs": {
            name: artifact_record(
                name,
                path,
                artifact_type="html" if str(path).endswith(".html") else "csv" if str(path).endswith(".csv") else "json",
                project_root=project_root,
                required=True,
            )
            for name, path in output_paths.items()
        },
        "report_contract": report_contract,
        "validation": {
            "checks_total": int(len(validation_df)),
            "checks_passed": int(validation_df["passed"].astype(bool).sum()),
            "all_checks_passed": bool(validation_df["passed"].astype(bool).all()),
        },
        "table_shapes": table_shapes,
    }


def save_json(path: Path | str, payload: dict[str, Any]) -> None:
    """Save a JSON payload with the notebook-safe encoder."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=json_safe), encoding="utf-8")


def save_html_report(path: Path | str, html_report: str) -> None:
    """Save an HTML report."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_report, encoding="utf-8")
