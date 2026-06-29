from __future__ import annotations

import base64
from pathlib import Path
from typing import Literal

import pandas as pd


ImageMode = Literal["embedded", "linked"]


def image_to_base64(path: Path) -> str:
    """Convert an image file to a base64 string for embedding in HTML."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Missing image file: {path}")

    with path.open("rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")


def image_block(
    path: Path,
    caption: str,
    *,
    project_root: Path | None = None,
    width: int = 220,
    mode: ImageMode = "embedded",
) -> str:
    """
    Create an HTML image block.

    Parameters
    ----------
    path:
        Image path.
    caption:
        Caption shown below the image.
    project_root:
        Required for linked mode. The image path is made relative to this root.
    width:
        Display width in pixels.
    mode:
        - "embedded": stores image as base64 inside the HTML file.
        - "linked": stores a relative file path, producing a much smaller HTML file.
    """
    path = Path(path)

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
        <div class="caption">{caption}</div>
    </div>
    """


def dataframe_to_html_table(df: pd.DataFrame, float_decimals: int = 3) -> str:
    """Convert a dataframe to a compact rounded HTML table."""
    display_df = df.copy()

    for column in display_df.columns:
        if pd.api.types.is_float_dtype(display_df[column]):
            display_df[column] = display_df[column].round(float_decimals)

    return display_df.to_html(index=False, classes="summary-table")


def interpret_case(row: pd.Series) -> str:
    """Generate a short rule-based interpretation for one restoration case."""
    mask_type = row["mask_type"]
    mask_mae = row["mask_mae"]
    mask_psnr = row["mask_psnr"]
    ssim_value = row["ssim"]

    comments: list[str] = []

    if mask_type == "scratch_lines":
        comments.append(
            "The scratch-line damage is narrow and local. Restoration is expected to perform relatively well because surrounding pixels provide strong local context."
        )
    elif mask_type == "irregular_small":
        comments.append(
            "The small irregular mask creates a localized missing region. Restoration quality depends on whether the missing area contains simple texture or important structure."
        )
    elif mask_type == "irregular_large":
        comments.append(
            "The large irregular mask creates a more difficult restoration case. Blurring or loss of structure is expected for this classical baseline."
        )

    if mask_mae < 7:
        comments.append("The masked-region error is low for this pilot setting.")
    elif mask_mae < 14:
        comments.append("The masked-region error is moderate.")
    else:
        comments.append("The masked-region error is high compared with the other pilot cases.")

    if ssim_value > 0.98:
        comments.append(
            "The full-image SSIM is very high, but this should be interpreted carefully because most of the image was never damaged."
        )
    else:
        comments.append(
            "The full-image SSIM is lower here, indicating that the restoration error is more visible at the image level."
        )

    if mask_psnr < 23:
        comments.append("The masked-region PSNR suggests a weaker restoration in the damaged area.")

    if "lpips_mask_crop" in row.index:
        lpips_crop = row["lpips_mask_crop"]
        if lpips_crop < 0.05:
            comments.append("The local LPIPS score indicates very low perceptual difference around the damaged area.")
        elif lpips_crop < 0.25:
            comments.append("The local LPIPS score indicates moderate perceptual difference around the damaged area.")
        else:
            comments.append("The local LPIPS score indicates high perceptual difference around the damaged area.")

    return " ".join(comments)


def prepare_report_dataframe(
    metadata: pd.DataFrame,
    metrics_df: pd.DataFrame,
    diff_df: pd.DataFrame,
) -> pd.DataFrame:
    """Merge painting metadata, metrics, and difference-map metadata for reporting."""
    report_df = metrics_df.merge(
        diff_df[["painting_id", "mask_type", "model_name", "diff_masked_filename"]],
        on=["painting_id", "mask_type", "model_name"],
        how="left",
    )

    metadata_columns = [
        "painting_id",
        "title",
        "artist",
        "date",
        "category",
        "style_or_period",
        "medium",
        "source_url",
        "license",
        "filename",
    ]

    report_df = report_df.merge(
        metadata[metadata_columns],
        on="painting_id",
        how="left",
    )

    # Backward-compatible filename reconstruction.
    # Earlier metric CSVs do not always carry the image filenames from the
    # restoration metadata. The pilot uses a fixed naming convention, so we
    # reconstruct the filenames here when they are missing. This keeps the
    # reporting step usable with both old and cleaned metric files.
    if "clean_filename" not in report_df.columns:
        report_df["clean_filename"] = report_df["painting_id"].astype(str) + "_clean.png"

    if "mask_filename" not in report_df.columns:
        report_df["mask_filename"] = (
            report_df["painting_id"].astype(str)
            + "_"
            + report_df["mask_type"].astype(str)
            + "_mask.png"
        )

    if "masked_filename" not in report_df.columns:
        report_df["masked_filename"] = (
            report_df["painting_id"].astype(str)
            + "_"
            + report_df["mask_type"].astype(str)
            + "_masked.png"
        )

    if "restored_filename" not in report_df.columns:
        report_df["restored_filename"] = (
            report_df["painting_id"].astype(str)
            + "_"
            + report_df["mask_type"].astype(str)
            + "_restored_"
            + report_df["model_name"].astype(str)
            + ".png"
        )

    return report_df


def summarize_by_mask_type(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate metrics by mask type."""
    aggregations = {
        "cases": ("painting_id", "count"),
        "mean_mask_area_ratio": ("mask_area_ratio", "mean"),
        "mean_full_mae": ("mae", "mean"),
        "mean_full_psnr": ("psnr", "mean"),
        "mean_full_ssim": ("ssim", "mean"),
        "mean_mask_mae": ("mask_mae", "mean"),
        "mean_mask_mse": ("mask_mse", "mean"),
        "mean_mask_psnr": ("mask_psnr", "mean"),
    }

    if "lpips_full" in metrics_df.columns:
        aggregations["mean_lpips_full"] = ("lpips_full", "mean")

    if "lpips_mask_crop" in metrics_df.columns:
        aggregations["mean_lpips_mask_crop"] = ("lpips_mask_crop", "mean")

    return (
        metrics_df.groupby("mask_type")
        .agg(**aggregations)
        .reset_index()
        .sort_values("mean_mask_mae")
    )


def get_best_worst_cases(
    metrics_df: pd.DataFrame,
    *,
    metric: str = "mask_mae",
    n: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return best and worst cases according to a metric where lower is better."""
    best_cases = metrics_df.sort_values(metric, ascending=True).head(n).copy()
    worst_cases = metrics_df.sort_values(metric, ascending=False).head(n).copy()
    return best_cases, worst_cases


def generate_pilot_summary_text(summary_by_mask: pd.DataFrame) -> str:
    """Generate a short analytical summary from aggregate mask metrics."""
    easiest = summary_by_mask.sort_values("mean_mask_mae").iloc[0]
    hardest = summary_by_mask.sort_values("mean_mask_mae", ascending=False).iloc[0]

    lpips_sentence = ""
    if "mean_lpips_mask_crop" in summary_by_mask.columns:
        easiest_lpips = summary_by_mask.sort_values("mean_lpips_mask_crop").iloc[0]
        hardest_lpips = summary_by_mask.sort_values("mean_lpips_mask_crop", ascending=False).iloc[0]
        lpips_sentence = f"""
        <p>
            The local LPIPS results show the same broad pattern: 
            <b>{easiest_lpips['mask_type']}</b> has the lowest mean local perceptual difference 
            ({easiest_lpips['mean_lpips_mask_crop']:.4f}), while 
            <b>{hardest_lpips['mask_type']}</b> has the highest 
            ({hardest_lpips['mean_lpips_mask_crop']:.4f}).
        </p>
        """

    return f"""
    <p>
        The easiest mask type for the OpenCV Telea baseline was 
        <b>{easiest['mask_type']}</b>, with the lowest mean masked-region MAE 
        ({easiest['mean_mask_mae']:.2f}). The hardest mask type was 
        <b>{hardest['mask_type']}</b>, with the highest mean masked-region MAE 
        ({hardest['mean_mask_mae']:.2f}).
    </p>

    <p>
        The results show that thin scratch-like damage is easier for classical inpainting,
        while larger irregular missing regions are more difficult and often lead to blurry
        or structurally weak restorations.
    </p>

    <p>
        Full-image SSIM remains high in many cases because most of the image is unchanged.
        Therefore, masked-region metrics and localized error maps are more informative for
        evaluating restoration quality in damaged areas.
    </p>

    {lpips_sentence}
    """


def build_analysis_summary_html(
    metrics_df: pd.DataFrame,
    *,
    float_decimals: int = 4,
) -> str:
    """Build the analytical front section of the report."""
    summary_by_mask = summarize_by_mask_type(metrics_df)
    best_cases, worst_cases = get_best_worst_cases(metrics_df, metric="mask_mae", n=3)

    summary_columns = [
        "mask_type",
        "cases",
        "mean_mask_area_ratio",
        "mean_full_ssim",
        "mean_mask_mae",
        "mean_mask_psnr",
    ]

    case_columns = [
        "painting_id",
        "mask_type",
        "model_name",
        "mask_area_ratio",
        "ssim",
        "mask_mae",
        "mask_psnr",
    ]

    if "mean_lpips_full" in summary_by_mask.columns:
        summary_columns.append("mean_lpips_full")
    if "mean_lpips_mask_crop" in summary_by_mask.columns:
        summary_columns.append("mean_lpips_mask_crop")
    if "lpips_full" in metrics_df.columns:
        case_columns.append("lpips_full")
    if "lpips_mask_crop" in metrics_df.columns:
        case_columns.append("lpips_mask_crop")

    summary_table_html = dataframe_to_html_table(summary_by_mask[summary_columns], float_decimals=float_decimals)
    best_cases_html = dataframe_to_html_table(best_cases[case_columns], float_decimals=float_decimals)
    worst_cases_html = dataframe_to_html_table(worst_cases[case_columns], float_decimals=float_decimals)

    pilot_summary_text = generate_pilot_summary_text(summary_by_mask)

    return f"""
    <div class="summary">
        <h2>Experiment overview</h2>
        <p>
            This pilot evaluates a complete restoration-analysis pipeline on three selected paintings.
            Each painting was processed into a standardized clean image, artificially damaged with three
            mask types, restored using OpenCV Telea inpainting, and evaluated using full-image,
            masked-region, and perceptual metrics.
        </p>

        <ul>
            <li><b>Paintings:</b> 3</li>
            <li><b>Mask types:</b> irregular_small, scratch_lines, irregular_large</li>
            <li><b>Total restoration cases:</b> 9</li>
            <li><b>Baseline model:</b> OpenCV Telea inpainting</li>
            <li><b>Metrics:</b> MAE, MSE, PSNR, SSIM, masked-region metrics, LPIPS full, LPIPS crop</li>
        </ul>

        <h2>Aggregate summary by mask type</h2>
        {summary_table_html}

        <h2>Best cases by masked-region MAE</h2>
        {best_cases_html}

        <h2>Worst cases by masked-region MAE</h2>
        {worst_cases_html}

        <h2>Key pilot observations</h2>
        {pilot_summary_text}

        <ul>
            <li>Scratch-line masks were usually restored very well and often became nearly invisible.</li>
            <li>Small irregular masks produced mixed results depending on the local image content.</li>
            <li>Large irregular masks were the hardest cases and often produced blurry or structurally weak restorations.</li>
            <li>Masked-region metrics were more useful than full-image metrics for identifying local restoration failures.</li>
            <li>Error maps helped localize restoration errors and supported the metric-based interpretation.</li>
            <li>LPIPS confirms the same broad difficulty pattern, with scratch-line masks showing the lowest perceptual difference and large irregular masks showing the highest.</li>
            <li>Crop-based LPIPS is more sensitive to local restoration errors than full-image LPIPS, especially for large missing regions.</li>
            <li>Structured image content, such as architectural regions, was harder to restore than softer background regions.</li>
        </ul>

        <h2>Limitations of this pilot</h2>
        <ul>
            <li>The pilot uses only three paintings and is not intended as a statistically meaningful benchmark.</li>
            <li>The artificial masks are simple and still more polygon-like than real conservation damage.</li>
            <li>OpenCV Telea is only a classical baseline and not representative of modern generative inpainting models.</li>
            <li>The current error maps are locally normalized, which makes them readable but not directly comparable across all cases.</li>
            <li>The white masked images are useful for visualization, but later deep models may require model-specific input formats.</li>
            <li>For scratch-line masks, bounding-box LPIPS crops can include large unchanged regions, so future experiments should consider patch-based or dilated-mask perceptual evaluation.</li>
        </ul>

        <h2>Next steps</h2>
        <ul>
            <li>Add LaMa as a pretrained inpainting model.</li>
            <li>Compare OpenCV Telea and LaMa on the same masked inputs.</li>
            <li>Generate both local-normalized and global-scale error maps.</li>
            <li>Improve mask realism using mixed synthetic damage, rougher boundaries, scattered paint loss, edge damage, and cracks.</li>
            <li>Investigate pretrained model training data and possible bias/domain gaps.</li>
            <li>Extend the report to support multi-model comparison and uncertainty visualization.</li>
        </ul>
    </div>
    """


def build_case_sections(
    report_df: pd.DataFrame,
    *,
    project_root: Path,
    clean_dir: Path,
    mask_dir: Path,
    masked_dir: Path,
    restored_dir: Path,
    diff_map_dir: Path,
    image_mode: ImageMode = "embedded",
) -> str:
    """Build the image-by-image case sections."""
    html_sections: list[str] = []

    for painting_id in report_df["painting_id"].unique():
        painting_rows = report_df[report_df["painting_id"] == painting_id]
        first = painting_rows.iloc[0]

        section_html = f"""
        <section class="painting-section">
            <h2>{painting_id}: {first['title']}</h2>
            <p>
                <b>Artist:</b> {first['artist']}<br>
                <b>Date:</b> {first['date']}<br>
                <b>Category:</b> {first['category']}<br>
                <b>Style / period:</b> {first['style_or_period']}<br>
                <b>Medium:</b> {first['medium']}<br>
                <b>License:</b> {first['license']}<br>
                <b>Source:</b> <a href="{first['source_url']}" target="_blank">{first['source_url']}</a>
            </p>
        """

        for _, row in painting_rows.iterrows():
            clean_path = clean_dir / row["clean_filename"]
            mask_path = mask_dir / row["mask_filename"]
            masked_path = masked_dir / row["masked_filename"]
            restored_path = restored_dir / row["restored_filename"]
            diff_path = diff_map_dir / row["diff_masked_filename"]

            metric_headers = """
                <th>Mask area ratio</th>
                <th>Full MAE</th>
                <th>Full PSNR</th>
                <th>Full SSIM</th>
                <th>Masked MAE</th>
                <th>Masked PSNR</th>
            """

            metric_values = f"""
                <td>{row['mask_area_ratio']:.4f}</td>
                <td>{row['mae']:.4f}</td>
                <td>{row['psnr']:.2f}</td>
                <td>{row['ssim']:.4f}</td>
                <td>{row['mask_mae']:.2f}</td>
                <td>{row['mask_psnr']:.2f}</td>
            """

            if "lpips_full" in row.index:
                metric_headers += "<th>LPIPS full</th>"
                metric_values += f"<td>{row['lpips_full']:.4f}</td>"

            if "lpips_mask_crop" in row.index:
                metric_headers += "<th>LPIPS crop</th>"
                metric_values += f"<td>{row['lpips_mask_crop']:.4f}</td>"

            section_html += f"""
            <div class="case-block">
                <h3>Mask type: {row['mask_type']}</h3>

                <div class="image-row">
                    {image_block(clean_path, "Clean image", project_root=project_root, mode=image_mode)}
                    {image_block(mask_path, "Mask", project_root=project_root, mode=image_mode)}
                    {image_block(masked_path, "Masked image", project_root=project_root, mode=image_mode)}
                    {image_block(restored_path, "Restored image", project_root=project_root, mode=image_mode)}
                    {image_block(diff_path, "Error map", project_root=project_root, mode=image_mode)}
                </div>

                <table>
                    <tr>{metric_headers}</tr>
                    <tr>{metric_values}</tr>
                </table>

                <p><b>Interpretation:</b> {interpret_case(row)}</p>
            </div>
            """

        section_html += "</section>"
        html_sections.append(section_html)

    return "\n".join(html_sections)


def build_html_report(
    analysis_summary_html: str,
    case_sections_html: str,
    *,
    title: str = "OpenCV Telea Pilot Restoration Report",
) -> str:
    """Combine summary and case sections into a full HTML document."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                background-color: #f7f7f7;
                color: #222;
            }}

            h1 {{
                color: #111;
                border-bottom: 2px solid #333;
                padding-bottom: 10px;
            }}

            h2 {{
                margin-top: 40px;
                color: #222;
            }}

            h3 {{
                margin-top: 30px;
                color: #333;
            }}

            ul {{
                line-height: 1.6;
            }}

            .summary {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 30px;
                border: 1px solid #ddd;
            }}

            .painting-section {{
                background: white;
                padding: 24px;
                border-radius: 8px;
                margin-bottom: 40px;
                border: 1px solid #ddd;
            }}

            .case-block {{
                margin-top: 25px;
                padding-top: 15px;
                border-top: 1px solid #ddd;
            }}

            .image-row {{
                display: flex;
                flex-wrap: wrap;
                gap: 14px;
                align-items: flex-start;
                margin: 15px 0;
            }}

            .image-block {{
                text-align: center;
                font-size: 12px;
            }}

            .image-block img {{
                border: 1px solid #ccc;
                background: #eee;
            }}

            .caption {{
                margin-top: 5px;
                color: #555;
            }}

            table,
            .summary-table {{
                border-collapse: collapse;
                margin-top: 15px;
                width: 100%;
                font-size: 13px;
            }}

            th, td,
            .summary-table th,
            .summary-table td {{
                border: 1px solid #ccc;
                padding: 8px;
                text-align: center;
            }}

            th,
            .summary-table th {{
                background-color: #eee;
                font-weight: bold;
            }}
        </style>
    </head>

    <body>
        <h1>{title}</h1>

        {analysis_summary_html}

        {case_sections_html}
    </body>
    </html>
    """


def generate_opencv_report(
    *,
    metadata: pd.DataFrame,
    metrics_df: pd.DataFrame,
    diff_df: pd.DataFrame,
    project_root: Path,
    clean_dir: Path,
    mask_dir: Path,
    masked_dir: Path,
    restored_dir: Path,
    diff_map_dir: Path,
    output_path: Path,
    image_mode: ImageMode = "embedded",
) -> str:
    """Generate and save the OpenCV Telea pilot HTML report."""
    report_df = prepare_report_dataframe(metadata, metrics_df, diff_df)
    analysis_summary_html = build_analysis_summary_html(metrics_df)
    case_sections_html = build_case_sections(
        report_df,
        project_root=project_root,
        clean_dir=clean_dir,
        mask_dir=mask_dir,
        masked_dir=masked_dir,
        restored_dir=restored_dir,
        diff_map_dir=diff_map_dir,
        image_mode=image_mode,
    )
    html_report = build_html_report(analysis_summary_html, case_sections_html)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_report, encoding="utf-8")

    return html_report
