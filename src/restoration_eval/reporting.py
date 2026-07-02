from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd


ImageMode = Literal["embedded", "linked"]


# ---------------------------------------------------------------------
# Basic HTML helpers
# ---------------------------------------------------------------------


def image_to_base64(path: Path) -> str:
    """Convert an image file to a base64 string for embedding in HTML."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Missing image file: {path}")

    with path.open("rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")


def html_escape(value: Any) -> str:
    """Escape a value for safe HTML display."""
    if pd.isna(value):
        return ""

    return html.escape(str(value))


def format_float(value: Any, decimals: int = 4) -> str:
    """Format numeric values for compact HTML tables."""
    if pd.isna(value):
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
    path: Path,
    caption: str,
    *,
    project_root: Path | None = None,
    width: int = 920,
    mode: ImageMode = "linked",
) -> str:
    """Create an HTML image block."""
    path = Path(path)

    if not path.exists():
        return f"""
        <div class="image-block missing-image">
            <div class="missing">Missing image: {html_escape(path)}</div>
            <div class="caption">{html_escape(caption)}</div>
        </div>
        """

    if mode == "embedded":
        encoded = image_to_base64(path)
        src = f"data:image/png;base64,{encoded}"
    elif mode == "linked":
        if project_root is None:
            raise ValueError("project_root must be provided when mode='linked'.")
        src = path.relative_to(project_root).as_posix()
    else:
        raise ValueError(f"Unknown image mode: {mode}")

    return f"""
    <div class="image-block">
        <img src="{src}" width="{width}">
        <div class="caption">{html_escape(caption)}</div>
    </div>
    """


# ---------------------------------------------------------------------
# Input validation and dataframe preparation
# ---------------------------------------------------------------------


def require_columns(
    df: pd.DataFrame,
    required_columns: list[str],
    *,
    dataframe_name: str,
) -> None:
    """Raise a clear error when a dataframe is missing required columns."""
    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{dataframe_name} is missing required columns: {missing_columns}"
        )


def _first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the first column from candidates that exists in the dataframe."""
    for column in candidates:
        if column in df.columns:
            return column

    return None


def _filter_metric_region(
    metrics_df: pd.DataFrame,
    *,
    region: str,
    dataframe_name: str,
) -> pd.DataFrame:
    """Filter a metric dataframe to one evaluation region and ok rows."""
    require_columns(
        metrics_df,
        ["case_id", "evaluation_region", "status"],
        dataframe_name=dataframe_name,
    )

    region_df = metrics_df[
        (metrics_df["evaluation_region"] == region)
        & (metrics_df["status"] == "ok")
    ].copy()

    if region_df.empty:
        raise ValueError(
            f"No rows found in {dataframe_name} for evaluation_region={region!r}."
        )

    return region_df


def _prepare_error_manifest(
    error_map_manifest_df: pd.DataFrame | None,
    *,
    project_root: Path,
) -> pd.DataFrame:
    """Prepare error-map manifest paths when available."""
    if error_map_manifest_df is None or error_map_manifest_df.empty:
        return pd.DataFrame(columns=["case_id", "error_map_figure_path"])

    require_columns(
        error_map_manifest_df,
        ["case_id"],
        dataframe_name="error_map_manifest_df",
    )

    path_column = _first_existing_column(
        error_map_manifest_df,
        [
            "figure_path",
            "error_map_figure_path",
            "output_path",
            "output_figure_path",
            "saved_figure_path",
            "figure_file_path",
        ],
    )

    if path_column is None:
        return error_map_manifest_df[["case_id"]].assign(error_map_figure_path="")

    prepared_df = error_map_manifest_df[["case_id", path_column]].copy()
    prepared_df = prepared_df.rename(columns={path_column: "error_map_figure_path"})

    prepared_df["error_map_figure_path"] = prepared_df["error_map_figure_path"].map(
        lambda value: "" if pd.isna(value) else str(value)
    )

    def resolve_path(value: str) -> str:
        if value == "":
            return ""

        path = Path(value)

        if path.is_absolute():
            return str(path)

        return str(project_root / path)

    prepared_df["error_map_figure_path"] = prepared_df["error_map_figure_path"].map(resolve_path)

    return prepared_df


def prepare_opencv_50_report_dataframe(
    *,
    processed_metadata_df: pd.DataFrame,
    restored_metadata_df: pd.DataFrame,
    classical_metrics_df: pd.DataFrame,
    lpips_metrics_df: pd.DataFrame,
    feature_metrics_df: pd.DataFrame,
    error_map_manifest_df: pd.DataFrame | None = None,
    project_root: Path | str = ".",
    include_zero_control: bool = False,
) -> pd.DataFrame:
    """Build one report-ready dataframe for the OpenCV 50-painting baseline."""
    project_root = Path(project_root)

    require_columns(
        processed_metadata_df,
        [
            "painting_id",
            "title",
            "artist",
            "date",
            "category",
            "style_or_period",
            "medium",
            "source",
            "source_url",
            "license",
            "filename",
        ],
        dataframe_name="processed_metadata_df",
    )

    require_columns(
        restored_metadata_df,
        [
            "case_id",
            "painting_id",
            "mask_id",
            "mask_type",
            "model_name",
            "clean_path",
            "damaged_path",
            "restored_path",
            "mask_path",
            "status",
        ],
        dataframe_name="restored_metadata_df",
    )

    classical_masked_df = _filter_metric_region(
        classical_metrics_df,
        region="masked_region",
        dataframe_name="classical_metrics_df",
    )

    lpips_mask_bbox_df = _filter_metric_region(
        lpips_metrics_df,
        region="mask_bbox_crop",
        dataframe_name="lpips_metrics_df",
    )

    feature_mask_bbox_df = _filter_metric_region(
        feature_metrics_df,
        region="mask_bbox_crop",
        dataframe_name="feature_metrics_df",
    )

    if not include_zero_control:
        restored_base_df = restored_metadata_df[
            restored_metadata_df["mask_type"] != "zero_control"
        ].copy()
    else:
        restored_base_df = restored_metadata_df.copy()

    restored_base_df = restored_base_df[
        restored_base_df["status"] == "ok"
    ].copy()

    metadata_columns = [
        "painting_id",
        "title",
        "artist",
        "date",
        "category",
        "style_or_period",
        "medium",
        "source",
        "source_url",
        "license",
        "filename",
    ]

    report_df = restored_base_df.merge(
        processed_metadata_df[metadata_columns],
        on="painting_id",
        how="left",
        validate="many_to_one",
    )

    classical_columns = [
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
    ]

    available_classical_columns = [
        column for column in classical_columns
        if column in classical_masked_df.columns
    ]

    report_df = report_df.merge(
        classical_masked_df[available_classical_columns],
        on="case_id",
        how="left",
        validate="one_to_one",
    )

    lpips_columns = [
        "case_id",
        "damaged_lpips",
        "restored_lpips",
        "lpips_improvement",
    ]

    available_lpips_columns = [
        column for column in lpips_columns
        if column in lpips_mask_bbox_df.columns
    ]

    report_df = report_df.merge(
        lpips_mask_bbox_df[available_lpips_columns],
        on="case_id",
        how="left",
        validate="one_to_one",
    )

    feature_columns = [
        "case_id",
        "clip_damaged_similarity",
        "clip_restored_similarity",
        "clip_similarity_improvement",
        "dinov2_damaged_similarity",
        "dinov2_restored_similarity",
        "dinov2_similarity_improvement",
    ]

    available_feature_columns = [
        column for column in feature_columns
        if column in feature_mask_bbox_df.columns
    ]

    report_df = report_df.merge(
        feature_mask_bbox_df[available_feature_columns],
        on="case_id",
        how="left",
        validate="one_to_one",
    )

    error_manifest_prepared_df = _prepare_error_manifest(
        error_map_manifest_df,
        project_root=project_root,
    )

    if not error_manifest_prepared_df.empty:
        report_df = report_df.merge(
            error_manifest_prepared_df,
            on="case_id",
            how="left",
        )
    else:
        report_df["error_map_figure_path"] = ""

    for column in [
        "damaged_area_pixels",
        "damaged_area_percentage_content",
        "damaged_area_percentage_full",
    ]:
        if column not in report_df.columns:
            report_df[column] = np.nan

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
        column for column in required_output_columns
        if column not in report_df.columns
    ]

    if missing_output_columns:
        raise ValueError(
            f"Prepared report dataframe is missing expected output columns: "
            f"{missing_output_columns}"
        )

    return report_df.sort_values(["painting_id", "mask_type"]).reset_index(drop=True)


# ---------------------------------------------------------------------
# Summary tables
# ---------------------------------------------------------------------


def summarize_report_overview(
    *,
    processed_metadata_df: pd.DataFrame,
    restored_metadata_df: pd.DataFrame,
    report_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build a compact experiment overview table."""
    rows = [
        {"item": "Paintings", "value": processed_metadata_df["painting_id"].nunique()},
        {"item": "Painting categories", "value": processed_metadata_df["category"].nunique()},
        {"item": "Restoration cases generated", "value": len(restored_metadata_df)},
        {"item": "Non-zero report cases", "value": len(report_df)},
        {"item": "Mask types", "value": restored_metadata_df["mask_type"].nunique()},
        {
            "item": "Baseline model",
            "value": ", ".join(sorted(restored_metadata_df["model_name"].dropna().unique())),
        },
    ]

    return pd.DataFrame(rows)


def summarize_report_by_mask_type(report_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize report metrics by damage/mask type."""
    return (
        report_df
        .groupby("mask_type", dropna=False)
        .agg(
            cases=("case_id", "count"),
            mean_damage_area_content_pct=("damaged_area_percentage_content", "mean"),
            mean_mse_improvement=("mse_improvement", "mean"),
            mean_restored_mse=("restored_mse", "mean"),
            mean_lpips_improvement=("lpips_improvement", "mean"),
            mean_restored_lpips=("restored_lpips", "mean"),
            mean_clip_improvement=("clip_similarity_improvement", "mean"),
            clip_improvement_rate=("clip_similarity_improvement", lambda values: (values > 0).mean()),
            mean_dinov2_improvement=("dinov2_similarity_improvement", "mean"),
            dinov2_improvement_rate=("dinov2_similarity_improvement", lambda values: (values > 0).mean()),
        )
        .reset_index()
        .round(5)
    )


def summarize_report_by_category(report_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize report metrics by painting category."""
    return (
        report_df
        .groupby("category", dropna=False)
        .agg(
            cases=("case_id", "count"),
            mean_mse_improvement=("mse_improvement", "mean"),
            mean_lpips_improvement=("lpips_improvement", "mean"),
            mean_clip_improvement=("clip_similarity_improvement", "mean"),
            mean_dinov2_improvement=("dinov2_similarity_improvement", "mean"),
            dinov2_negative_rate=("dinov2_similarity_improvement", lambda values: (values < 0).mean()),
        )
        .reset_index()
        .round(5)
    )


def summarize_metric_correlations(report_df: pd.DataFrame) -> pd.DataFrame:
    """Return the main multi-metric correlation matrix."""
    correlation_columns = [
        "mse_improvement",
        "mae_improvement",
        "psnr_improvement",
        "lpips_improvement",
        "clip_similarity_improvement",
        "dinov2_similarity_improvement",
    ]

    available_columns = [
        column for column in correlation_columns
        if column in report_df.columns
    ]

    return report_df[available_columns].corr().round(4)


# ---------------------------------------------------------------------
# Diagnostic case selection
# ---------------------------------------------------------------------


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
        return pd.DataFrame(columns=list(report_df.columns) + ["selection_reason"])

    selected_df = (
        report_df
        .dropna(subset=[metric])
        .sort_values(metric, ascending=ascending)
        .head(n)
        .copy()
    )

    selected_df["selection_reason"] = label
    selected_df["selection_metric"] = metric

    return selected_df


def select_opencv_50_diagnostic_cases(
    report_df: pd.DataFrame,
    *,
    n_per_group: int = 3,
    include_category_examples: bool = True,
) -> pd.DataFrame:
    """Select representative diagnostic cases for the report."""
    selections = [
        _select_top_cases(
            report_df,
            metric="mse_improvement",
            label="Strongest masked-region MSE improvement",
            ascending=False,
            n=n_per_group,
        ),
        _select_top_cases(
            report_df,
            metric="mse_improvement",
            label="Weakest masked-region MSE improvement",
            ascending=True,
            n=n_per_group,
        ),
        _select_top_cases(
            report_df,
            metric="lpips_improvement",
            label="Strongest mask-bbox LPIPS improvement",
            ascending=False,
            n=n_per_group,
        ),
        _select_top_cases(
            report_df,
            metric="lpips_improvement",
            label="Weakest mask-bbox LPIPS improvement",
            ascending=True,
            n=n_per_group,
        ),
        _select_top_cases(
            report_df,
            metric="dinov2_similarity_improvement",
            label="Strongest DINOv2 feature improvement",
            ascending=False,
            n=n_per_group,
        ),
        _select_top_cases(
            report_df,
            metric="dinov2_similarity_improvement",
            label="Weakest DINOv2 feature improvement",
            ascending=True,
            n=n_per_group,
        ),
    ]

    if include_category_examples and "category" in report_df.columns:
        category_examples = (
            report_df
            .sort_values("mse_improvement", ascending=False)
            .groupby("category", dropna=False)
            .head(1)
            .copy()
        )
        category_examples["selection_reason"] = "Strong category example by MSE improvement"
        category_examples["selection_metric"] = "mse_improvement"
        selections.append(category_examples)

    selected_df = pd.concat(selections, ignore_index=True)

    if selected_df.empty:
        return selected_df

    reason_df = (
        selected_df
        .groupby("case_id")
        .agg(
            selection_reason=("selection_reason", lambda values: "; ".join(sorted(set(values)))),
            selection_metric=("selection_metric", lambda values: "; ".join(sorted(set(values)))),
        )
        .reset_index()
    )

    base_columns = [
        column for column in selected_df.columns
        if column not in ["selection_reason", "selection_metric"]
    ]

    deduped_df = (
        selected_df[base_columns]
        .drop_duplicates(subset=["case_id"])
        .merge(reason_df, on="case_id", how="left")
        .sort_values(["painting_id", "mask_type"])
        .reset_index(drop=True)
    )

    return deduped_df


# ---------------------------------------------------------------------
# Interpretation helpers
# ---------------------------------------------------------------------


def interpret_case(row: pd.Series) -> str:
    """Generate a short report interpretation for one selected case."""
    mask_type = row.get("mask_type", "")
    mse_improvement = row.get("mse_improvement", np.nan)
    lpips_improvement = row.get("lpips_improvement", np.nan)
    dinov2_improvement = row.get("dinov2_similarity_improvement", np.nan)

    comments: list[str] = []

    if mask_type == "scratch_thin":
        comments.append(
            "This thin scratch case is favorable for OpenCV Telea because nearby pixels provide local interpolation context."
        )
    elif mask_type == "loss_small":
        comments.append(
            "This small-loss case tests whether local interpolation can recover a compact missing region without disrupting nearby structure."
        )
    elif mask_type == "loss_large":
        comments.append(
            "This large-loss case is difficult for OpenCV Telea because the missing region may require structural or semantic reconstruction."
        )
    elif mask_type == "mixed_damage":
        comments.append(
            "This mixed-damage case combines multiple damage patterns and tests whether the baseline remains stable under less uniform degradation."
        )

    if pd.notna(mse_improvement):
        if mse_improvement > 10_000:
            comments.append(
                "The masked-region MSE improvement is large, showing that restoration strongly reduces pixel error compared with the white-filled damaged input."
            )
        elif mse_improvement > 0:
            comments.append(
                "The masked-region MSE improvement is positive, but more modest than the strongest baseline cases."
            )
        else:
            comments.append(
                "The masked-region MSE improvement is non-positive, indicating a failure under this pixel-level metric."
            )

    if pd.notna(lpips_improvement):
        if lpips_improvement > 0:
            comments.append(
                "LPIPS also improves, indicating that the restored crop is closer to the clean reference in learned perceptual feature space."
            )
        else:
            comments.append(
                "LPIPS does not improve, suggesting that pixel-level restoration did not translate into local perceptual improvement."
            )

    if pd.notna(dinov2_improvement):
        if dinov2_improvement > 0:
            comments.append(
                "DINOv2 feature similarity improves, suggesting better alignment with the clean local visual structure in this pretrained representation space."
            )
        else:
            comments.append(
                "DINOv2 feature similarity decreases, suggesting that the filled region may remain structurally inconsistent with the clean reference despite visible damage removal."
            )

    return " ".join(comments)


def build_key_findings_html(
    *,
    summary_by_mask: pd.DataFrame,
    summary_by_category: pd.DataFrame,
    correlation_df: pd.DataFrame,
) -> str:
    """Build the main textual interpretation section."""
    hardest_mask_by_dino = summary_by_mask.sort_values(
        "mean_dinov2_improvement",
        ascending=True,
    ).iloc[0]

    easiest_mask_by_mse = summary_by_mask.sort_values(
        "mean_mse_improvement",
        ascending=False,
    ).iloc[0]

    weakest_category_by_dino = summary_by_category.sort_values(
        "mean_dinov2_improvement",
        ascending=True,
    ).iloc[0]

    corr_html = dataframe_to_html_table(
        correlation_df.reset_index().rename(columns={"index": "metric"}),
        float_decimals=4,
    )

    return f"""
    <h2>Key findings</h2>

    <p>
        OpenCV Telea consistently reduces the obvious white-mask damage, especially for
        local and scratch-like damage. The strongest average masked-region MSE improvement
        was observed for <b>{html_escape(easiest_mask_by_mse['mask_type'])}</b>.
    </p>

    <p>
        However, pixel-level improvement does not imply faithful restoration. The weakest
        DINOv2 feature-space behavior was observed for <b>{html_escape(hardest_mask_by_dino['mask_type'])}</b>,
        with mean DINOv2 improvement of
        <b>{format_float(hardest_mask_by_dino['mean_dinov2_improvement'], 5)}</b>.
        This indicates that OpenCV can fill a visibly damaged region while still failing
        to recover local visual structure in a pretrained self-supervised feature space.
    </p>

    <p>
        Category-level behavior also varies. The weakest average DINOv2 improvement was
        observed for <b>{html_escape(weakest_category_by_dino['category'])}</b>.
        This supports the project decision to evaluate restoration behavior across
        multiple painting categories rather than treating all artworks as a single
        homogeneous image set.
    </p>

    <p>
        The metric correlations show that classical, perceptual, and feature-space metrics
        are related but not redundant. This supports the central evaluation-framework
        argument: restoration quality cannot be judged using one scalar metric family.
    </p>

    <h3>Main metric correlation matrix</h3>
    {corr_html}
    """


# ---------------------------------------------------------------------
# HTML report generation
# ---------------------------------------------------------------------


def build_selected_case_sections_html(
    selected_cases_df: pd.DataFrame,
    *,
    project_root: Path,
    image_mode: ImageMode = "linked",
    image_width: int = 980,
) -> str:
    """Build selected diagnostic case sections using error-map figures."""
    if selected_cases_df.empty:
        return "<p>No selected diagnostic cases were provided.</p>"

    sections: list[str] = []

    for _, row in selected_cases_df.iterrows():
        figure_path_value = row.get("error_map_figure_path", "")

        if pd.notna(figure_path_value) and str(figure_path_value).strip() != "":
            figure_html = image_block(
                Path(str(figure_path_value)),
                caption="Diagnostic error-map figure",
                project_root=project_root,
                width=image_width,
                mode=image_mode,
            )
        else:
            figure_html = """
            <p class="missing">
                No error-map figure path available for this case.
            </p>
            """

        metric_table = pd.DataFrame(
            [
                {
                    "case_id": row.get("case_id", ""),
                    "category": row.get("category", ""),
                    "mask_type": row.get("mask_type", ""),
                    "mse_improvement": row.get("mse_improvement", np.nan),
                    "lpips_improvement": row.get("lpips_improvement", np.nan),
                    "clip_improvement": row.get("clip_similarity_improvement", np.nan),
                    "dinov2_improvement": row.get("dinov2_similarity_improvement", np.nan),
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
                    <b>Category:</b> {html_escape(row.get("category", ""))}<br>
                    <b>Mask type:</b> {html_escape(row.get("mask_type", ""))}<br>
                    <b>Artist:</b> {html_escape(row.get("artist", ""))}<br>
                    <b>Date:</b> {html_escape(row.get("date", ""))}
                </p>

                {dataframe_to_html_table(metric_table, float_decimals=5)}

                <p><b>Interpretation:</b> {html_escape(interpret_case(row))}</p>

                {figure_html}
            </section>
            """
        )

    return "\n".join(sections)


def build_opencv_50_report_html(
    *,
    overview_df: pd.DataFrame,
    summary_by_mask: pd.DataFrame,
    summary_by_category: pd.DataFrame,
    correlation_df: pd.DataFrame,
    selected_cases_df: pd.DataFrame,
    project_root: Path,
    image_mode: ImageMode = "linked",
    title: str = "OpenCV Telea 50-Painting Baseline Report",
) -> str:
    """Build the full OpenCV 50-painting HTML report."""
    overview_html = dataframe_to_html_table(overview_df, float_decimals=4)
    mask_summary_html = dataframe_to_html_table(summary_by_mask, float_decimals=5)
    category_summary_html = dataframe_to_html_table(summary_by_category, float_decimals=5)

    key_findings_html = build_key_findings_html(
        summary_by_mask=summary_by_mask,
        summary_by_category=summary_by_category,
        correlation_df=correlation_df,
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
                margin: 40px;
                background-color: #f7f7f7;
                color: #222;
                line-height: 1.55;
            }}

            h1 {{
                color: #111;
                border-bottom: 2px solid #333;
                padding-bottom: 10px;
            }}

            h2 {{
                margin-top: 38px;
                color: #222;
            }}

            h3 {{
                margin-top: 26px;
                color: #333;
            }}

            .summary,
            .case-section {{
                background: white;
                padding: 22px;
                border-radius: 8px;
                margin-bottom: 30px;
                border: 1px solid #ddd;
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
                border: 1px solid #ccc;
                background: #eee;
                max-width: 100%;
                height: auto;
            }}

            .caption {{
                margin-top: 6px;
                color: #555;
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
                border: 1px solid #ccc;
                padding: 7px;
                text-align: center;
                vertical-align: middle;
            }}

            th,
            .summary-table th {{
                background-color: #eee;
                font-weight: bold;
            }}

            .note {{
                background: #fff7ed;
                border: 1px solid #fed7aa;
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
                This report consolidates the OpenCV Telea baseline evaluation for the
                controlled 50-painting subset. It summarizes restoration behavior across
                synthetic damage types, painting categories, and multiple metric families.
            </p>

            {overview_html}

            <p class="note">
                OpenCV Telea is used here as a deterministic classical baseline. The goal is
                not to claim faithful restoration, but to establish how a local interpolation
                method behaves under the proposed evaluation framework.
            </p>
        </div>

        <div class="summary">
            <h2>Summary by mask type</h2>
            {mask_summary_html}

            <h2>Summary by painting category</h2>
            {category_summary_html}

            {key_findings_html}
        </div>

        <div class="summary">
            <h2>Selected diagnostic cases</h2>
            <p>
                The following cases were selected from strongest and weakest metric outcomes,
                feature-space failures, and category examples. They are intended for qualitative
                inspection, not as a replacement for the full metric tables.
            </p>

            {selected_cases_html}
        </div>

        <div class="summary">
            <h2>Baseline conclusion</h2>
            <p>
                The OpenCV Telea baseline reliably improves over white-filled synthetic damage
                for local and scratch-like masks, but it remains limited for large missing
                regions and cases requiring semantic or structural reconstruction.
            </p>

            <p>
                The disagreement between MSE, LPIPS, CLIP, DINOv2, and visual error maps is a
                core finding rather than a problem. It shows that restoration quality has to be
                evaluated through complementary metric families and visual diagnostics.
            </p>

            <p>
                This baseline therefore provides a useful reference point before introducing
                pretrained or generative inpainting models such as LaMa, Stable Diffusion
                Inpainting, and SDXL Inpainting.
            </p>
        </div>
    </body>
    </html>
    """


def generate_opencv_50_report(
    *,
    processed_metadata_df: pd.DataFrame,
    restored_metadata_df: pd.DataFrame,
    classical_metrics_df: pd.DataFrame,
    lpips_metrics_df: pd.DataFrame,
    feature_metrics_df: pd.DataFrame,
    error_map_manifest_df: pd.DataFrame | None,
    project_root: Path | str,
    output_path: Path | str,
    selected_cases_output_path: Path | str | None = None,
    image_mode: ImageMode = "linked",
) -> dict[str, pd.DataFrame | str]:
    """Generate and save the OpenCV 50-painting baseline report."""
    project_root = Path(project_root)
    output_path = Path(output_path)

    report_df = prepare_opencv_50_report_dataframe(
        processed_metadata_df=processed_metadata_df,
        restored_metadata_df=restored_metadata_df,
        classical_metrics_df=classical_metrics_df,
        lpips_metrics_df=lpips_metrics_df,
        feature_metrics_df=feature_metrics_df,
        error_map_manifest_df=error_map_manifest_df,
        project_root=project_root,
        include_zero_control=False,
    )

    overview_df = summarize_report_overview(
        processed_metadata_df=processed_metadata_df,
        restored_metadata_df=restored_metadata_df,
        report_df=report_df,
    )

    summary_by_mask_df = summarize_report_by_mask_type(report_df)
    summary_by_category_df = summarize_report_by_category(report_df)
    correlation_df = summarize_metric_correlations(report_df)

    selected_cases_df = select_opencv_50_diagnostic_cases(report_df)

    if selected_cases_output_path is not None:
        selected_cases_output_path = Path(selected_cases_output_path)
        selected_cases_output_path.parent.mkdir(parents=True, exist_ok=True)
        selected_cases_df.to_csv(selected_cases_output_path, index=False)

    html_report = build_opencv_50_report_html(
        overview_df=overview_df,
        summary_by_mask=summary_by_mask_df,
        summary_by_category=summary_by_category_df,
        correlation_df=correlation_df,
        selected_cases_df=selected_cases_df,
        project_root=project_root,
        image_mode=image_mode,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_report, encoding="utf-8")

    return {
        "report_df": report_df,
        "overview_df": overview_df,
        "summary_by_mask_df": summary_by_mask_df,
        "summary_by_category_df": summary_by_category_df,
        "correlation_df": correlation_df,
        "selected_cases_df": selected_cases_df,
        "html_report": html_report,
    }
