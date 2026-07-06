from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


# =============================================================================
# Page config
# =============================================================================

st.set_page_config(
    page_title="Painting Restoration Evaluation",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# Paths
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent

DASHBOARD_DIR = PROJECT_ROOT / "outputs" / "dashboard"
DASHBOARD_DATA_DIR = DASHBOARD_DIR / "data"
DASHBOARD_MANIFEST_DIR = DASHBOARD_DIR / "manifests"

METRICS_DIR = PROJECT_ROOT / "outputs" / "metrics"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"


# =============================================================================
# Basic loading helpers
# =============================================================================

@st.cache_data(show_spinner=False)
def load_json(path: str) -> dict[str, Any]:
    path_obj = Path(path)

    if not path_obj.exists():
        return {}

    with open(path_obj, "r", encoding="utf-8") as file:
        return json.load(file)


@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    path_obj = Path(path)

    if not path_obj.exists():
        return pd.DataFrame()

    return pd.read_csv(path_obj)


def resolve_project_path(path_value: str | Path | None) -> Path | None:
    if path_value is None:
        return None

    try:
        if pd.isna(path_value):
            return None
    except TypeError:
        pass

    path = Path(str(path_value))

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def project_relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


# =============================================================================
# Manifest-aware asset loading
# =============================================================================

overview = load_json(str(DASHBOARD_MANIFEST_DIR / "dashboard_overview_summary.json"))
assets_manifest = load_json(str(DASHBOARD_MANIFEST_DIR / "dashboard_assets_manifest.json"))
key_findings_manifest = load_json(str(DASHBOARD_MANIFEST_DIR / "dashboard_key_findings.json"))
reports_manifest = load_json(str(DASHBOARD_MANIFEST_DIR / "dashboard_reports_manifest.json"))


def build_asset_lookup(manifest: dict[str, Any]) -> dict[str, Path]:
    """
    Build a flexible lookup from dashboard_assets_manifest.json.

    Supports multiple possible key/path field names because generated manifests
    are not always polite enough to use one schema forever.
    """
    lookup: dict[str, Path] = {}

    for asset in manifest.get("assets", []):
        asset_key = (
            asset.get("asset_id")
            or asset.get("asset_name")
            or asset.get("name")
            or asset.get("key")
            or asset.get("label")
        )

        path_value = (
            asset.get("path")
            or asset.get("file_path")
            or asset.get("relative_path")
            or asset.get("project_relative_path")
        )

        if asset_key and path_value:
            resolved_path = resolve_project_path(path_value)

            if resolved_path is not None:
                lookup[str(asset_key)] = resolved_path

    return lookup


ASSET_LOOKUP = build_asset_lookup(assets_manifest)


def find_existing_file(candidate_paths: list[Path]) -> Path | None:
    for path in candidate_paths:
        if path.exists():
            return path

    return None


def load_asset_csv(
    asset_keys: list[str],
    fallback_filenames: list[str],
    *,
    label: str,
    show_warning: bool = False,
) -> pd.DataFrame:
    """
    Load a dashboard CSV using:
    1. asset manifest keys,
    2. outputs/dashboard/data fallback filenames,
    3. outputs/metrics fallback filenames.
    """
    candidate_paths: list[Path] = []

    for key in asset_keys:
        if key in ASSET_LOOKUP:
            candidate_paths.append(ASSET_LOOKUP[key])

    for filename in fallback_filenames:
        candidate_paths.append(DASHBOARD_DATA_DIR / filename)
        candidate_paths.append(METRICS_DIR / filename)

    existing_path = find_existing_file(candidate_paths)

    if existing_path is None:
        if show_warning:
            st.warning(f"Could not find `{label}`.")
        return pd.DataFrame()

    return load_csv(str(existing_path))


# =============================================================================
# Load data
# =============================================================================

dataset_summary_df = load_asset_csv(
    ["dataset_summary_csv"],
    ["final_controlled_50_dataset_summary.csv"],
    label="dataset summary",
)

damage_summary_df = load_asset_csv(
    ["damage_summary_csv"],
    ["dashboard_damage_summary.csv", "final_controlled_50_damage_summary.csv"],
    label="damage summary",
)

model_stack_df = load_asset_csv(
    ["model_stack_csv"],
    ["final_controlled_50_model_stack_summary.csv"],
    label="model stack",
)

metric_policy_df = load_asset_csv(
    ["metric_policy_csv"],
    ["final_controlled_50_metric_policy_summary.csv"],
    label="metric policy",
)

model_win_summary_df = load_asset_csv(
    ["model_win_summary_csv"],
    ["final_controlled_50_model_win_summary.csv"],
    label="model win summary",
)

per_metric_winner_summary_df = load_asset_csv(
    ["per_metric_winner_summary_csv"],
    ["final_controlled_50_per_metric_winner_summary.csv"],
    label="per metric winner summary",
)

model_comparison_cases_df = load_asset_csv(
    ["model_comparison_cases_csv"],
    ["dashboard_model_comparison_cases.csv"],
    label="model comparison cases",
)

comparison_by_mask_type_df = load_asset_csv(
    ["model_comparison_by_mask_type_csv"],
    ["comparison_summary_by_mask_type_refined_opencv_lama_stable_diffusion_50.csv"],
    label="comparison by mask type",
)

comparison_by_category_df = load_asset_csv(
    ["model_comparison_by_category_csv"],
    ["comparison_summary_by_category_refined_opencv_lama_stable_diffusion_50.csv"],
    label="comparison by category",
)

uncertainty_summary_df = load_asset_csv(
    ["uncertainty_summary_csv"],
    ["final_controlled_50_uncertainty_summary.csv"],
    label="uncertainty summary",
)

uncertainty_cases_df = load_asset_csv(
    ["uncertainty_cases_csv"],
    ["dashboard_uncertainty_cases.csv"],
    label="uncertainty cases",
)

uncertainty_by_mask_type_df = load_asset_csv(
    ["uncertainty_by_mask_type_csv"],
    ["stable_diffusion_uncertainty_combined_summary_by_mask_type_50.csv"],
    label="uncertainty by mask type",
)

uncertainty_by_category_df = load_asset_csv(
    ["uncertainty_by_category_csv"],
    ["stable_diffusion_uncertainty_combined_summary_by_category_50.csv"],
    label="uncertainty by category",
)

uncertainty_vs_performance_df = load_asset_csv(
    ["uncertainty_vs_performance_csv"],
    ["stable_diffusion_uncertainty_vs_refined_performance_50.csv"],
    label="uncertainty vs performance",
)

uncertainty_quadrants_df = load_asset_csv(
    ["uncertainty_quadrants_csv"],
    ["stable_diffusion_uncertainty_performance_quadrants_50.csv"],
    label="uncertainty quadrants",
)

visual_cases_df = load_asset_csv(
    ["visual_cases_csv"],
    ["dashboard_visual_cases.csv", "final_controlled_50_visual_cases.csv"],
    label="visual cases",
)

findings = key_findings_manifest.get("findings", [])
reports = reports_manifest.get("reports", [])


# =============================================================================
# UI helpers
# =============================================================================

def dataframe_block(title: str, df: pd.DataFrame, height: int = 320) -> None:
    st.markdown(f"### {title}")

    if df.empty:
        st.info("No data available for this table.")
    else:
        st.dataframe(df, use_container_width=True, height=height)


def compact_table(df: pd.DataFrame, columns: list[str], height: int = 260) -> None:
    if df.empty:
        st.info("No data available.")
        return

    available_columns = [column for column in columns if column in df.columns]

    if available_columns:
        st.dataframe(df[available_columns], use_container_width=True, height=height)
    else:
        st.dataframe(df, use_container_width=True, height=height)


def explain_box(title: str, text: str, kind: str = "info") -> None:
    markdown_text = f"**{title}**\n\n{text}"

    if kind == "info":
        st.info(markdown_text)
    elif kind == "success":
        st.success(markdown_text)
    elif kind == "warning":
        st.warning(markdown_text)
    else:
        st.markdown(markdown_text)


def pick_first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column

    return None


def simple_bar(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str | None = None,
) -> None:
    if df.empty or x not in df.columns or y not in df.columns:
        return

    fig = px.bar(
        df,
        x=x,
        y=y,
        color=color if color and color in df.columns else None,
        text=y,
        title=title,
    )

    fig.update_layout(
        xaxis_title=x.replace("_", " ").title(),
        yaxis_title=y.replace("_", " ").title(),
        margin=dict(l=20, r=20, t=60, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)


def count_bar(
    df: pd.DataFrame,
    column: str,
    title: str,
    top_n: int | None = None,
) -> None:
    if df.empty or column not in df.columns:
        return

    count_df = (
        df[column]
        .fillna("missing")
        .value_counts()
        .reset_index()
    )

    count_df.columns = [column, "count"]

    if top_n is not None:
        count_df = count_df.head(top_n)

    fig = px.bar(
        count_df,
        x=column,
        y="count",
        text="count",
        title=title,
    )

    fig.update_layout(
        xaxis_title=column.replace("_", " ").title(),
        yaxis_title="Count",
        margin=dict(l=20, r=20, t=60, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)


def numeric_histogram(
    df: pd.DataFrame,
    column: str,
    title: str,
    color: str | None = None,
) -> None:
    if df.empty or column not in df.columns:
        return

    plot_df = df.dropna(subset=[column]).copy()

    if plot_df.empty:
        return

    fig = px.histogram(
        plot_df,
        x=column,
        color=color if color and color in plot_df.columns else None,
        nbins=20,
        title=title,
    )

    fig.update_layout(
        xaxis_title=column.replace("_", " ").title(),
        yaxis_title="Cases",
        margin=dict(l=20, r=20, t=60, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)


def simple_scatter(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str | None = None,
    hover_columns: list[str] | None = None,
) -> None:
    if df.empty or x not in df.columns or y not in df.columns:
        return

    fig = px.scatter(
        df,
        x=x,
        y=y,
        color=color if color and color in df.columns else None,
        hover_data=hover_columns,
        title=title,
    )

    fig.update_layout(
        xaxis_title=x.replace("_", " ").title(),
        yaxis_title=y.replace("_", " ").title(),
        margin=dict(l=20, r=20, t=60, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)


def readable_value(value: Any, fallback: str = "Not available") -> str:
    if value is None:
        return fallback

    try:
        if pd.isna(value):
            return fallback
    except TypeError:
        pass

    return str(value)


def readable_uncertainty_value(value: Any) -> str:
    if value is None:
        return "Not part of uncertainty subset"

    try:
        if pd.isna(value):
            return "Not part of uncertainty subset"
    except TypeError:
        pass

    if isinstance(value, float):
        return f"{value:.4f}"

    return str(value)


def readable_metric_vote(value: Any) -> str:
    if value is None:
        return "No refined vote recorded for this visual case"

    try:
        if pd.isna(value):
            return "No refined vote recorded for this visual case"
    except TypeError:
        pass

    return str(value)


def visual_reason_explanation(reason: str | None) -> str:
    explanations = {
        "old_vs_refined_vote_changed": (
            "This case was selected because the final refined metric-region policy changed "
            "the interpretation compared with the earlier metric policy."
        ),
        "metric_disagreement": (
            "This case was selected because different metrics disagreed, making it useful "
            "for explaining why a single score is insufficient."
        ),
        "high_uncertainty": (
            "This case was selected because Stable Diffusion produced high variation across seeds."
        ),
        "uncertainty_performance_quadrant": (
            "This case was selected to illustrate the relationship between uncertainty and "
            "reference-based performance."
        ),
        "representative_case": (
            "This case was selected as a representative visual example."
        ),
    }

    if reason is None:
        return "No specific visual-selection reason was recorded."

    try:
        if pd.isna(reason):
            return "No specific visual-selection reason was recorded."
    except TypeError:
        pass

    return explanations.get(
        str(reason),
        "This case was selected for visual review based on the final visual-case sampling policy.",
    )


# =============================================================================
# Sidebar navigation
# =============================================================================

st.sidebar.title("Painting Restoration")
st.sidebar.caption("Thesis evaluation dashboard")

page = st.sidebar.radio(
    "Navigate",
    [
        "Overview",
        "Dataset & Damage",
        "Model Stack",
        "Metric Policy",
        "Model Comparison",
        "Diffusion Uncertainty",
        "Visual Explorer",
        "Key Findings",
        "Reports",
        "Debug",
    ],
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Core claim**")
st.sidebar.markdown(
    "> Visual plausibility is not the same as restoration trustworthiness."
)

st.sidebar.markdown("**Data source**")
st.sidebar.code("outputs/dashboard/", language="text")


# =============================================================================
# Header
# =============================================================================

st.title("Trustworthy Evaluation Frameworks for AI-Assisted Painting Restoration")

st.caption(
    "Controlled 50-painting evaluation dashboard. Built from prepared dashboard assets, "
    "not raw notebooks or giant HTML reports."
)


# =============================================================================
# Page: Overview
# =============================================================================

if page == "Overview":
    st.header("Overview")

    explain_box(
        "Dashboard purpose",
        (
            "This dashboard summarizes the controlled 50-painting thesis experiment. "
            "It is not a restoration tool. It is a review interface for checking how different "
            "models behave under controlled synthetic damage, region-aware metrics, and uncertainty diagnostics."
        ),
    )

    controlled_subset = overview.get("controlled_subset", {})
    refined_comparison = overview.get("refined_comparison", {})
    uncertainty_analysis = overview.get("uncertainty_analysis", {})
    models = overview.get("models", {})

    st.markdown("### Controlled benchmark")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Paintings", controlled_subset.get("paintings", "NA"))
    col2.metric("Damage cases", controlled_subset.get("damage_cases", "NA"))
    col3.metric("Non-zero cases", controlled_subset.get("non_zero_comparison_cases", "NA"))
    col4.metric("Categories", controlled_subset.get("painting_categories", "NA"))

    explain_box(
        "Why zero-control and non-zero cases are separated",
        (
            "Zero-control cases are sanity checks where no damage is applied. "
            "The main model comparison uses the 200 non-zero cases, because those are the cases "
            "where restoration behavior can actually be evaluated."
        ),
    )

    st.markdown("### Refined model comparison headline")

    col1, col2, col3 = st.columns(3)

    total_cases = refined_comparison.get("total_non_zero_cases", "NA")

    col1.metric(
        "LaMa majority wins",
        f"{refined_comparison.get('lama_majority_cases', 'NA')}/{total_cases}",
    )
    col2.metric(
        "OpenCV Telea majority wins",
        f"{refined_comparison.get('opencv_telea_majority_cases', 'NA')}/{total_cases}",
    )
    col3.metric(
        "Stable Diffusion majority wins",
        f"{refined_comparison.get('stable_diffusion_inpainting_majority_cases', 'NA')}/{total_cases}",
    )

    if not model_win_summary_df.empty:
        simple_bar(
            model_win_summary_df,
            x="model",
            y="majority_vote_cases",
            title="Refined Majority-Vote Cases by Model",
        )

    explain_box(
        "Interpretation",
        (
            "LaMa dominates the refined reference-based comparison. OpenCV Telea remains useful as a deterministic "
            "baseline. Stable Diffusion rarely wins under reference-based metrics, but remains important because "
            "it exposes the difference between visual plausibility and trustworthy restoration."
        ),
        kind="success",
    )

    st.markdown("### Stable Diffusion uncertainty headline")

    col1, col2, col3 = st.columns(3)
    col1.metric("Uncertainty cases", uncertainty_analysis.get("cases", "NA"))
    col2.metric("Seed outputs", uncertainty_analysis.get("seed_outputs", "NA"))
    col3.metric("Seeds per case", uncertainty_analysis.get("seeds_per_case", "NA"))

    explain_box(
        "Why uncertainty is subset-based",
        (
            "Uncertainty analysis was run on a balanced 40-case subset rather than all 200 non-zero cases. "
            "This keeps the experiment computationally practical while still covering all painting categories "
            "and non-zero damage types. This is one of the points to confirm with the supervisor."
        ),
        kind="warning",
    )

    if not visual_cases_df.empty:
        count_bar(
            visual_cases_df,
            column="final_visual_source",
            title="Visual Cases by Source",
        )

    st.markdown("### Model stack")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Fully evaluated**")
        for model in models.get("fully_evaluated", []):
            st.markdown(f"- `{model}`")

    with col2:
        st.markdown("**Feasibility audited**")
        for model in models.get("feasibility_audited", []):
            st.markdown(f"- `{model}`")


# =============================================================================
# Page: Dataset & Damage
# =============================================================================

elif page == "Dataset & Damage":
    st.header("Dataset & Damage")

    explain_box(
        "Dataset design",
        (
            "The benchmark uses a controlled 50-painting subset with five painting categories. "
            "Each painting receives five mask conditions, including a zero-control case and four non-zero "
            "damage types."
        ),
    )

    col1, col2 = st.columns(2)

    with col1:
        dataframe_block("Dataset summary", dataset_summary_df)

    with col2:
        dataframe_block("Damage summary", damage_summary_df)

    if not damage_summary_df.empty:
        x_col = pick_first_existing_column(
            damage_summary_df,
            ["mask_type", "damage_type", "mask_name"],
        )
        y_col = pick_first_existing_column(
            damage_summary_df,
            ["cases", "rows", "count", "damage_cases"],
        )

        if x_col and y_col:
            simple_bar(
                damage_summary_df,
                x=x_col,
                y=y_col,
                title="Damage Cases by Mask Type",
            )

    explain_box(
        "Methodological boundary",
        (
            "Synthetic damage is useful because it gives a known clean reference image. "
            "That makes full-reference metrics possible. It does not fully reproduce real conservation damage "
            "such as pigment aging, varnish effects, craquelure, prior restorations, or historical uncertainty."
        ),
        kind="warning",
    )


# =============================================================================
# Page: Model Stack
# =============================================================================

elif page == "Model Stack":
    st.header("Model Stack")

    dataframe_block("Evaluated and audited models", model_stack_df, height=420)

    explain_box(
        "Model interpretation",
        (
            "OpenCV Telea is the deterministic classical baseline. LaMa is the strongest reference-based "
            "inpainting model in the controlled experiment. Stable Diffusion Inpainting is used to study "
            "generative plausibility and uncertainty. SDXL is feasibility-audited only because local hardware "
            "made full evaluation impractical."
        ),
        kind="info",
    )

    if not model_stack_df.empty and "evaluation_status" in model_stack_df.columns:
        status_df = (
            model_stack_df["evaluation_status"]
            .value_counts()
            .reset_index()
        )
        status_df.columns = ["evaluation_status", "count"]

        simple_bar(
            status_df,
            x="evaluation_status",
            y="count",
            title="Model Evaluation Status",
        )


# =============================================================================
# Page: Metric Policy
# =============================================================================

elif page == "Metric Policy":
    st.header("Metric Policy")

    explain_box(
        "Why metric-region policy matters",
        (
            "The region where a metric is computed changes what the metric means. A sparse masked-pixel metric "
            "is useful for MSE and PSNR, but not for SSIM, because SSIM needs local spatial structure. "
            "This is why the final policy uses mask-bounding-box crops for SSIM and feature/perceptual metrics."
        ),
    )

    dataframe_block("Final metric-region policy", metric_policy_df, height=420)

    explain_box(
        "Final policy interpretation",
        (
            "No single metric is treated as absolute truth. The framework combines pixel fidelity, structural similarity, "
            "perceptual similarity, feature-space similarity, visual diagnostics, and uncertainty analysis."
        ),
        kind="success",
    )


# =============================================================================
# Page: Model Comparison
# =============================================================================

elif page == "Model Comparison":
    st.header("Model Comparison")

    explain_box(
        "What is being compared?",
        (
            "This section compares OpenCV Telea, LaMa, and Stable Diffusion Inpainting on the 200 non-zero "
            "damage cases. The final comparison uses the refined metric-region policy: MSE/PSNR on the masked "
            "pixels, and SSIM/LPIPS/CLIP/DINOv2 on the mask bounding-box crop."
        ),
    )

    simple_bar(
        model_win_summary_df,
        x="model",
        y="majority_vote_cases",
        title="Refined Majority-Vote Cases by Model",
    )

    if not model_comparison_cases_df.empty:
        vote_col = pick_first_existing_column(
            model_comparison_cases_df,
            ["refined_overall_metric_vote", "overall_metric_vote"],
        )

        if vote_col:
            count_bar(
                model_comparison_cases_df,
                column=vote_col,
                title="Case-Level Refined Metric Vote Distribution",
            )

        if "mask_type" in model_comparison_cases_df.columns:
            count_bar(
                model_comparison_cases_df,
                column="mask_type",
                title="Compared Cases by Damage Type",
            )

        if "category" in model_comparison_cases_df.columns:
            count_bar(
                model_comparison_cases_df,
                column="category",
                title="Compared Cases by Painting Category",
            )

    explain_box(
        "Why majority vote is used",
        (
            "Each metric captures a different idea of similarity. Majority voting is used as a compact summary, "
            "not as absolute truth. The important result is not merely that one model wins, but that different "
            "metrics can disagree, which supports the thesis argument for multi-metric evaluation."
        ),
    )

    with st.expander("Model win summary", expanded=True):
        dataframe_block("Model win summary", model_win_summary_df, height=260)

    with st.expander("Per-metric winner summary", expanded=False):
        dataframe_block("Per-metric winner summary", per_metric_winner_summary_df)

    with st.expander("Summary by mask type", expanded=False):
        dataframe_block("Comparison by mask type", comparison_by_mask_type_df)

    with st.expander("Summary by painting category", expanded=False):
        dataframe_block("Comparison by category", comparison_by_category_df)

    st.markdown("### Case-level explorer")

    if model_comparison_cases_df.empty:
        st.info("No case-level comparison table available.")
    else:
        filtered_df = model_comparison_cases_df.copy()

        col1, col2, col3 = st.columns(3)

        with col1:
            if "category" in filtered_df.columns:
                categories = sorted(filtered_df["category"].dropna().unique())
                selected_categories = st.multiselect(
                    "Category",
                    categories,
                    default=categories,
                )
                filtered_df = filtered_df[filtered_df["category"].isin(selected_categories)]

        with col2:
            if "mask_type" in filtered_df.columns:
                masks = sorted(filtered_df["mask_type"].dropna().unique())
                selected_masks = st.multiselect(
                    "Mask type",
                    masks,
                    default=masks,
                )
                filtered_df = filtered_df[filtered_df["mask_type"].isin(selected_masks)]

        with col3:
            vote_col = pick_first_existing_column(
                filtered_df,
                ["refined_overall_metric_vote", "overall_metric_vote"],
            )

            if vote_col:
                votes = sorted(filtered_df[vote_col].dropna().unique())
                selected_votes = st.multiselect(
                    "Metric vote",
                    votes,
                    default=votes,
                )
                filtered_df = filtered_df[filtered_df[vote_col].isin(selected_votes)]

        st.caption(f"Filtered cases: {len(filtered_df)}")

        preferred_columns = [
            "case_id",
            "painting_id",
            "category",
            "mask_type",
            "title",
            "refined_overall_metric_vote",
            "overall_metric_vote",
            "opencv_telea_metric_wins",
            "lama_metric_wins",
            "stable_diffusion_inpainting_metric_wins",
            "mixed_metric_outcome",
            "all_metrics_same_winner",
        ]

        compact_table(filtered_df, preferred_columns, height=460)

        with st.expander("Show all case-level columns"):
            st.dataframe(filtered_df, use_container_width=True, height=460)


# =============================================================================
# Page: Diffusion Uncertainty
# =============================================================================

elif page == "Diffusion Uncertainty":
    st.header("Stable Diffusion Uncertainty")

    explain_box(
        "What uncertainty means here",
        (
            "Stable Diffusion can generate different restorations for the same damaged image depending on the random seed. "
            "The uncertainty analysis measures how much those outputs vary. High uncertainty does not automatically mean "
            "bad restoration, but it is a warning signal that the model is unstable for that case."
        ),
    )

    dataframe_block("Uncertainty summary", uncertainty_summary_df, height=220)

    if not uncertainty_cases_df.empty:
        col1, col2 = st.columns(2)

        with col1:
            numeric_histogram(
                uncertainty_cases_df,
                column="combined_uncertainty_index",
                title="Distribution of Combined Uncertainty Index",
                color="mask_type" if "mask_type" in uncertainty_cases_df.columns else None,
            )

        with col2:
            if "mask_type" in uncertainty_cases_df.columns:
                count_bar(
                    uncertainty_cases_df,
                    column="mask_type",
                    title="Uncertainty Subset Cases by Damage Type",
                )

    col1, col2 = st.columns(2)

    with col1:
        dataframe_block("Uncertainty by mask type", uncertainty_by_mask_type_df)

    with col2:
        dataframe_block("Uncertainty by category", uncertainty_by_category_df)

    st.markdown("### Highest uncertainty cases")

    if not uncertainty_cases_df.empty and "combined_uncertainty_index" in uncertainty_cases_df.columns:
        highest_uncertainty_df = (
            uncertainty_cases_df
            .sort_values("combined_uncertainty_index", ascending=False)
            .head(15)
        )

        compact_table(
            highest_uncertainty_df,
            [
                "case_id",
                "painting_id",
                "category",
                "mask_type",
                "title",
                "combined_uncertainty_index",
                "masked_std_mean",
                "mean_pairwise_lpips",
                "mean_dinov2_uncertainty_distance",
            ],
            height=380,
        )

        x_col = pick_first_existing_column(
            highest_uncertainty_df,
            ["case_id", "original_case_id"],
        )

        if x_col:
            simple_bar(
                highest_uncertainty_df,
                x=x_col,
                y="combined_uncertainty_index",
                color="mask_type",
                title="Top Stable Diffusion Uncertainty Cases",
            )

    st.markdown("### Uncertainty vs reference performance")

    explain_box(
        "How to read this",
        (
            "This comparison checks whether Stable Diffusion cases with high uncertainty also perform poorly "
            "under the refined reference-based metric comparison. The relationship is not expected to be perfect. "
            "That is the point: uncertainty and reference fidelity are complementary diagnostic signals."
        ),
    )

    if not uncertainty_vs_performance_df.empty:
        x_col = "combined_uncertainty_index"
        y_col = pick_first_existing_column(
            uncertainty_vs_performance_df,
            [
                "refined_stable_diffusion_metric_wins",
                "stable_diffusion_metric_wins",
                "sd_metric_wins",
            ],
        )

        if y_col:
            simple_scatter(
                uncertainty_vs_performance_df,
                x=x_col,
                y=y_col,
                color="uncertainty_performance_quadrant",
                hover_columns=[
                    col
                    for col in ["case_id", "original_case_id", "category", "mask_type", "title"]
                    if col in uncertainty_vs_performance_df.columns
                ],
                title="Uncertainty vs Stable Diffusion Reference-Metric Performance",
            )

    with st.expander("Uncertainty vs performance table"):
        dataframe_block("Uncertainty vs performance", uncertainty_vs_performance_df)

    with st.expander("Uncertainty-performance quadrants"):
        dataframe_block("Quadrants", uncertainty_quadrants_df, height=280)

    explain_box(
        "Thesis interpretation",
        (
            "The uncertainty analysis supports the trustworthiness framing: generative restoration should not be judged "
            "only by whether it looks plausible. Instability across seeds can reveal cases where the model is inventing "
            "rather than faithfully restoring."
        ),
        kind="success",
    )


# =============================================================================
# Page: Visual Explorer
# =============================================================================

elif page == "Visual Explorer":
    st.header("Visual Case Explorer")

    explain_box(
        "Why some fields are unavailable",
        (
            "Visual cases come from different sources. Some are selected from refined model comparison, some from "
            "uncertainty analysis, and some from uncertainty-performance quadrants. Therefore, not every visual case "
            "has every field. For example, a model-comparison case may not have a Stable Diffusion uncertainty index "
            "because uncertainty was only computed for a balanced 40-case subset."
        ),
    )

    if visual_cases_df.empty:
        st.info("No visual cases available.")
    else:
        filtered_df = visual_cases_df.copy()

        if "final_figure_exists" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["final_figure_exists"] == True]

        col1, col2, col3 = st.columns(3)

        with col1:
            if "final_visual_source" in filtered_df.columns:
                sources = sorted(filtered_df["final_visual_source"].dropna().unique())
                selected_sources = st.multiselect(
                    "Visual source",
                    sources,
                    default=sources,
                )
                filtered_df = filtered_df[filtered_df["final_visual_source"].isin(selected_sources)]

        with col2:
            if "category" in filtered_df.columns:
                categories = sorted(filtered_df["category"].dropna().unique())
                selected_categories = st.multiselect(
                    "Category",
                    categories,
                    default=categories,
                )
                filtered_df = filtered_df[filtered_df["category"].isin(selected_categories)]

        with col3:
            if "mask_type" in filtered_df.columns:
                masks = sorted(filtered_df["mask_type"].dropna().unique())
                selected_masks = st.multiselect(
                    "Mask type",
                    masks,
                    default=masks,
                )
                filtered_df = filtered_df[filtered_df["mask_type"].isin(selected_masks)]

        st.caption(f"Available visual cases: {len(filtered_df)}")

        if not filtered_df.empty and "final_visual_source" in filtered_df.columns:
            count_bar(
                filtered_df,
                column="final_visual_source",
                title="Filtered Visual Cases by Source",
            )

        if filtered_df.empty:
            st.info("No visual cases match the selected filters.")
        else:
            label_col = pick_first_existing_column(
                filtered_df,
                ["original_case_id", "case_id", "painting_id"],
            )

            selected_index = st.selectbox(
                "Select case",
                filtered_df.index,
                format_func=lambda idx: (
                    f"{filtered_df.loc[idx].get(label_col, idx)}"
                    f" | {filtered_df.loc[idx].get('category', 'unknown')}"
                    f" | {filtered_df.loc[idx].get('mask_type', 'unknown')}"
                ),
            )

            selected_row = filtered_df.loc[selected_index]

            detail_col, image_col = st.columns([1, 2])

            with detail_col:
                st.markdown("### Case details")

                visual_reason = selected_row.get("final_visual_reason", None)

                display_details = {
                    "Original case ID": readable_value(selected_row.get("original_case_id", None)),
                    "Case ID": readable_value(selected_row.get("case_id", None)),
                    "Painting ID": readable_value(selected_row.get("painting_id", None)),
                    "Title": readable_value(selected_row.get("title", None)),
                    "Category": readable_value(selected_row.get("category", None)),
                    "Mask type": readable_value(selected_row.get("mask_type", None)),
                    "Visual source": readable_value(selected_row.get("final_visual_source", None)),
                    "Selection reason": readable_value(visual_reason),
                    "Refined metric vote": readable_metric_vote(
                        selected_row.get("refined_overall_metric_vote", None)
                    ),
                    "Combined uncertainty index": readable_uncertainty_value(
                        selected_row.get("combined_uncertainty_index", None)
                    ),
                    "Uncertainty quadrant": readable_uncertainty_value(
                        selected_row.get("uncertainty_performance_quadrant", None)
                    ),
                }

                for key, value in display_details.items():
                    st.markdown(f"**{key}:** {value}")

                st.markdown("### Why this case is shown")
                st.info(visual_reason_explanation(visual_reason))

                if pd.isna(selected_row.get("combined_uncertainty_index", None)):
                    st.caption(
                        "Note: this case does not have uncertainty values because it was not part of "
                        "the Stable Diffusion multi-seed uncertainty subset."
                    )

                if pd.isna(selected_row.get("refined_overall_metric_vote", None)):
                    st.caption(
                        "Note: this visual record does not include a refined overall metric vote. "
                        "It may have been selected for visual-policy comparison or another diagnostic reason."
                    )

            with image_col:
                figure_path = resolve_project_path(selected_row.get("final_figure_path"))

                if figure_path and figure_path.exists():
                    st.image(str(figure_path), use_container_width=True)
                    st.caption(project_relative(figure_path))
                else:
                    st.warning("Figure file not found.")

            with st.expander("Show raw row"):
                raw_row_df = selected_row.to_frame(name="value")
                st.dataframe(raw_row_df, use_container_width=True, height=420)


# =============================================================================
# Page: Key Findings
# =============================================================================

elif page == "Key Findings":
    st.header("Key Findings")

    explain_box(
        "How to read these findings",
        (
            "These are thesis-facing findings, not just dashboard notes. They summarize what the controlled "
            "experiment supports and what still needs supervisor confirmation."
        ),
    )

    if not findings:
        st.info("No key findings manifest available.")
    else:
        for finding in findings:
            finding_id = finding.get("finding_id", "")
            title = finding.get("title", "")
            summary = finding.get("summary", "")
            evidence = finding.get("evidence", "")

            with st.expander(f"{finding_id}: {title}", expanded=True):
                st.markdown(summary)

                if evidence:
                    st.caption(f"Evidence: {evidence}")

    st.markdown("### Thesis contribution summary")

    st.success(
        """
The current experiment supports the thesis framing that AI-assisted painting restoration requires 
a trustworthiness evaluation framework.

The strongest contribution is not that one model wins. The stronger contribution is showing that
reference metrics, visual plausibility, metric-region policy, model uncertainty, and feasibility constraints
can point to different conclusions.
"""
    )

    st.markdown("### Supervisor confirmation still needed")

    st.warning(
        """
Open points:

1. Is the 50-painting controlled subset sufficient?
2. Is the 40-case uncertainty subset sufficient?
3. Should SDXL remain feasibility-audited only?
4. Is the refined metric-region policy accepted?
5. Should the Streamlit dashboard become a formal supporting artifact?
"""
    )


# =============================================================================
# Page: Reports
# =============================================================================

elif page == "Reports":
    st.header("Reports & Reproducibility")

    st.markdown("### Reports")

    if not reports:
        st.info("No reports manifest available.")
    else:
        reports_df = pd.DataFrame(reports)
        st.dataframe(reports_df, use_container_width=True, height=260)

        for report in reports:
            label = report.get("label") or report.get("name") or "Report"
            path_value = report.get("path") or report.get("project_relative_path") or ""

            if path_value:
                report_path = resolve_project_path(path_value)
                exists = report_path.exists() if report_path else False

                st.markdown(
                    f"- **{label}**: `{path_value}` "
                    f"{'✅ local file exists' if exists else '⚠️ missing locally'}"
                )

    st.markdown("### Reproducibility note")

    st.info(
        """
This dashboard reads prepared dashboard assets from `outputs/dashboard/`.

It does not rerun restoration models, recompute metrics, or load giant HTML reports.
That separation is intentional: the dashboard summarizes the experiment, while notebooks remain the
reproducible execution record.
"""
    )

    st.markdown("### Suggested run command")

    st.code("streamlit run streamlit_app.py", language="powershell")


# =============================================================================
# Page: Debug
# =============================================================================

elif page == "Debug":
    st.header("Dashboard Debug")

    st.markdown("### Manifest asset lookup")

    if ASSET_LOOKUP:
        asset_lookup_df = pd.DataFrame(
            [
                {
                    "asset_key": key,
                    "resolved_path": str(path),
                    "exists": path.exists(),
                }
                for key, path in ASSET_LOOKUP.items()
            ]
        )
        st.dataframe(asset_lookup_df, use_container_width=True, height=500)
    else:
        st.warning("Asset lookup is empty. Check dashboard_assets_manifest.json.")

    st.markdown("### Loaded dataframe shapes")

    loaded_shapes = pd.DataFrame(
        [
            {"name": "dataset_summary_df", "rows": len(dataset_summary_df), "columns": len(dataset_summary_df.columns)},
            {"name": "damage_summary_df", "rows": len(damage_summary_df), "columns": len(damage_summary_df.columns)},
            {"name": "model_stack_df", "rows": len(model_stack_df), "columns": len(model_stack_df.columns)},
            {"name": "metric_policy_df", "rows": len(metric_policy_df), "columns": len(metric_policy_df.columns)},
            {"name": "model_win_summary_df", "rows": len(model_win_summary_df), "columns": len(model_win_summary_df.columns)},
            {"name": "per_metric_winner_summary_df", "rows": len(per_metric_winner_summary_df), "columns": len(per_metric_winner_summary_df.columns)},
            {"name": "model_comparison_cases_df", "rows": len(model_comparison_cases_df), "columns": len(model_comparison_cases_df.columns)},
            {"name": "comparison_by_mask_type_df", "rows": len(comparison_by_mask_type_df), "columns": len(comparison_by_mask_type_df.columns)},
            {"name": "comparison_by_category_df", "rows": len(comparison_by_category_df), "columns": len(comparison_by_category_df.columns)},
            {"name": "uncertainty_summary_df", "rows": len(uncertainty_summary_df), "columns": len(uncertainty_summary_df.columns)},
            {"name": "uncertainty_cases_df", "rows": len(uncertainty_cases_df), "columns": len(uncertainty_cases_df.columns)},
            {"name": "uncertainty_by_mask_type_df", "rows": len(uncertainty_by_mask_type_df), "columns": len(uncertainty_by_mask_type_df.columns)},
            {"name": "uncertainty_by_category_df", "rows": len(uncertainty_by_category_df), "columns": len(uncertainty_by_category_df.columns)},
            {"name": "uncertainty_vs_performance_df", "rows": len(uncertainty_vs_performance_df), "columns": len(uncertainty_vs_performance_df.columns)},
            {"name": "uncertainty_quadrants_df", "rows": len(uncertainty_quadrants_df), "columns": len(uncertainty_quadrants_df.columns)},
            {"name": "visual_cases_df", "rows": len(visual_cases_df), "columns": len(visual_cases_df.columns)},
        ]
    )

    st.dataframe(loaded_shapes, use_container_width=True, height=500)

    st.markdown("### Dashboard directories")

    st.code(
        f"""
PROJECT_ROOT={PROJECT_ROOT}
DASHBOARD_DATA_DIR={DASHBOARD_DATA_DIR}
DASHBOARD_MANIFEST_DIR={DASHBOARD_MANIFEST_DIR}
METRICS_DIR={METRICS_DIR}
REPORTS_DIR={REPORTS_DIR}
        """.strip(),
        language="text",
    )