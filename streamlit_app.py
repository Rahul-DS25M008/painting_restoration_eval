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
DASHBOARD_DATA_DIR = DASHBOARD_DIR / "data"          # legacy Notebook 29/30 location
DASHBOARD_MANIFEST_DIR = DASHBOARD_DIR / "manifests" # legacy Notebook 29/30 location

METRICS_DIR = PROJECT_ROOT / "outputs" / "metrics"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"


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

    path_text = str(path_value).strip()

    if not path_text:
        return None

    path = Path(path_text)

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def project_relative(path: Path | None) -> str:
    if path is None:
        return ""

    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def path_exists(path_value: str | Path | None) -> bool:
    resolved = resolve_project_path(path_value)
    return bool(resolved is not None and resolved.exists())


# =============================================================================
# Manifest-aware asset loading
# =============================================================================

# New Notebook 34 assets live directly in outputs/dashboard/.
dashboard_summary = load_json(str(DASHBOARD_DIR / "dashboard_summary.json"))
dashboard_asset_manifest = load_json(str(DASHBOARD_DIR / "dashboard_asset_manifest.json"))

# Legacy assets from earlier dashboard-prep notebooks are still supported so the
# current UI does not lose sections if old assets are present.
overview = load_json(str(DASHBOARD_MANIFEST_DIR / "dashboard_overview_summary.json"))
assets_manifest = load_json(str(DASHBOARD_MANIFEST_DIR / "dashboard_assets_manifest.json"))
key_findings_manifest = load_json(str(DASHBOARD_MANIFEST_DIR / "dashboard_key_findings.json"))
reports_manifest = load_json(str(DASHBOARD_MANIFEST_DIR / "dashboard_reports_manifest.json"))


def build_legacy_asset_lookup(manifest: dict[str, Any]) -> dict[str, Path]:
    """
    Build a flexible lookup from legacy dashboard_assets_manifest.json.

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


def build_notebook34_asset_lookup(manifest: dict[str, Any]) -> dict[str, Path]:
    """Build lookup from Notebook 34 dashboard_asset_manifest.json."""
    lookup: dict[str, Path] = {}

    for asset_key, asset_metadata in manifest.get("assets", {}).items():
        path_value = asset_metadata.get("path")

        if path_value:
            resolved_path = resolve_project_path(path_value)

            if resolved_path is not None:
                lookup[str(asset_key)] = resolved_path

    return lookup


LEGACY_ASSET_LOOKUP = build_legacy_asset_lookup(assets_manifest)
DASHBOARD34_ASSET_LOOKUP = build_notebook34_asset_lookup(dashboard_asset_manifest)
ASSET_LOOKUP = {**LEGACY_ASSET_LOOKUP, **DASHBOARD34_ASSET_LOOKUP}


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
    Load a CSV using:
    1. Notebook 34 asset manifest keys,
    2. legacy asset manifest keys,
    3. outputs/dashboard/ filenames,
    4. outputs/dashboard/data fallback filenames,
    5. outputs/metrics fallback filenames.
    """
    candidate_paths: list[Path] = []

    for key in asset_keys:
        if key in ASSET_LOOKUP:
            candidate_paths.append(ASSET_LOOKUP[key])

    for filename in fallback_filenames:
        candidate_paths.append(DASHBOARD_DIR / filename)
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

# Notebook 34 outputs.
dashboard_model_winner_summary_df = load_asset_csv(
    ["dashboard_model_winner_summary"],
    ["dashboard_model_winner_summary.csv"],
    label="dashboard model winner summary",
)

dashboard_metric_vote_summary_df = load_asset_csv(
    ["dashboard_metric_vote_summary"],
    ["dashboard_metric_vote_summary.csv"],
    label="dashboard metric vote summary",
)

dashboard_texture_summary_df = load_asset_csv(
    ["dashboard_texture_summary"],
    ["dashboard_texture_summary.csv"],
    label="dashboard texture summary",
)

dashboard_texture_disagreements_df = load_asset_csv(
    ["dashboard_texture_disagreements"],
    ["dashboard_texture_disagreements.csv"],
    label="dashboard texture disagreements",
)

dashboard_uncertainty_summary_df = load_asset_csv(
    ["dashboard_uncertainty_summary"],
    ["dashboard_uncertainty_summary.csv"],
    label="dashboard uncertainty summary",
)

dashboard_uncertainty_selected_cases_df = load_asset_csv(
    ["dashboard_uncertainty_selected_cases"],
    ["dashboard_uncertainty_selected_cases.csv"],
    label="dashboard uncertainty selected cases",
)

dashboard_case_report_manifest_df = load_asset_csv(
    ["dashboard_case_report_manifest"],
    ["dashboard_case_report_manifest.csv"],
    label="dashboard case report manifest",
)

dashboard_selected_cases_df = load_asset_csv(
    ["dashboard_selected_cases"],
    ["dashboard_selected_cases.csv"],
    label="dashboard selected cases",
)

dashboard_figure_manifest_df = load_asset_csv(
    ["dashboard_figure_manifest"],
    ["dashboard_figure_manifest.csv"],
    label="dashboard figure manifest",
)

# Legacy/pre-existing outputs retained for current sections.
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
    ["dashboard_model_comparison_cases.csv", "comparison_unified_refined_opencv_lama_stable_diffusion_50.csv"],
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

# Legacy diffusion uncertainty tables plus Notebook 32 heatmap tables.
uncertainty_summary_df = load_asset_csv(
    ["uncertainty_summary_csv"],
    ["final_controlled_50_uncertainty_summary.csv"],
    label="uncertainty summary",
)

uncertainty_cases_df = load_asset_csv(
    ["uncertainty_cases_csv"],
    ["dashboard_uncertainty_cases.csv", "stable_diffusion_uncertainty_heatmap_summary_by_case_50.csv"],
    label="uncertainty cases",
)

uncertainty_by_mask_type_df = load_asset_csv(
    ["uncertainty_by_mask_type_csv"],
    ["stable_diffusion_uncertainty_heatmap_summary_by_mask_type_50.csv", "stable_diffusion_uncertainty_combined_summary_by_mask_type_50.csv"],
    label="uncertainty by mask type",
)

uncertainty_by_category_df = load_asset_csv(
    ["uncertainty_by_category_csv"],
    ["stable_diffusion_uncertainty_heatmap_summary_by_category_50.csv", "stable_diffusion_uncertainty_combined_summary_by_category_50.csv"],
    label="uncertainty by category",
)

uncertainty_vs_performance_df = load_asset_csv(
    ["uncertainty_vs_performance_csv"],
    ["stable_diffusion_uncertainty_heatmap_vs_refined_performance_50.csv", "stable_diffusion_uncertainty_vs_refined_performance_50.csv"],
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


def readable_float(value: Any, fallback: str = "Not available", digits: int = 4) -> str:
    if value is None:
        return fallback

    try:
        if pd.isna(value):
            return fallback
    except TypeError:
        pass

    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def readable_uncertainty_value(value: Any) -> str:
    return readable_float(value, fallback="Not part of uncertainty subset")


def readable_metric_vote(value: Any) -> str:
    return readable_value(value, fallback="No refined vote recorded for this visual case")


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


def split_dashboard_summary_by_section(df: pd.DataFrame, section: str) -> pd.DataFrame:
    if df.empty or "dashboard_section" not in df.columns:
        return pd.DataFrame()

    return df[df["dashboard_section"] == section].dropna(axis=1, how="all").copy()


def render_local_asset_link(label: str, path_value: str | Path | None) -> None:
    resolved_path = resolve_project_path(path_value)

    if resolved_path is None:
        st.markdown(f"- **{label}**: `not available`")
        return

    exists = resolved_path.exists()
    st.markdown(
        f"- **{label}**: `{project_relative(resolved_path)}` "
        f"{'✅ local file exists' if exists else '⚠️ missing locally'}"
    )


def render_image_from_path(path_value: str | Path | None, caption: str | None = None) -> None:
    resolved_path = resolve_project_path(path_value)

    if resolved_path and resolved_path.exists():
        st.image(str(resolved_path), use_container_width=True)
        st.caption(caption or project_relative(resolved_path))
    else:
        st.warning("Image file not found.")


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
        "Texture Diagnostics",
        "Diffusion Uncertainty",
        "Case Reports",
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
            "models behave under controlled synthetic damage, region-aware metrics, texture diagnostics, "
            "and seed-based uncertainty analysis."
        ),
    )

    summary_dataset = dashboard_summary.get("dataset", {})
    summary_models = dashboard_summary.get("models", {})
    summary_case_reports = dashboard_summary.get("case_reports", {})

    controlled_subset = overview.get("controlled_subset", {})
    refined_comparison = overview.get("refined_comparison", {})
    uncertainty_analysis = overview.get("uncertainty_analysis", {})
    legacy_models = overview.get("models", {})

    paintings = summary_dataset.get("controlled_paintings", controlled_subset.get("paintings", "NA"))
    non_zero_cases = summary_dataset.get("non_zero_cases", controlled_subset.get("non_zero_comparison_cases", "NA"))
    categories = summary_dataset.get("painting_categories", [])
    mask_types = summary_dataset.get("mask_types_non_zero", [])

    st.markdown("### Controlled benchmark")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Paintings", paintings)
    col2.metric("Non-zero cases", non_zero_cases)
    col3.metric("Categories", len(categories) if categories else controlled_subset.get("painting_categories", "NA"))
    col4.metric("Non-zero mask types", len(mask_types) if mask_types else "NA")

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

    total_cases = refined_comparison.get("total_non_zero_cases", non_zero_cases)

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

    if not dashboard_model_winner_summary_df.empty:
        simple_bar(
            dashboard_model_winner_summary_df,
            x="refined_winner",
            y="cases",
            title="Refined Winner Cases by Model",
        )
    elif not model_win_summary_df.empty:
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

    st.markdown("### Final diagnostic layers")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Selected case reports", summary_case_reports.get("selected_cases", len(dashboard_selected_cases_df)))
    col2.metric(
        "Cases with heatmaps",
        summary_case_reports.get("selected_cases_with_uncertainty_heatmaps", "NA"),
    )
    col3.metric(
        "Texture disagreement cases",
        summary_case_reports.get("selected_cases_with_texture_disagreement", "NA"),
    )
    col4.metric(
        "Dashboard assets",
        len(dashboard_asset_manifest.get("assets", {})) if dashboard_asset_manifest else "NA",
    )

    st.markdown("### Stable Diffusion uncertainty headline")

    col1, col2, col3 = st.columns(3)
    col1.metric("Uncertainty cases", uncertainty_analysis.get("cases", 40))
    col2.metric("Seed outputs", uncertainty_analysis.get("seed_outputs", 160))
    col3.metric("Seeds per case", uncertainty_analysis.get("seeds_per_case", 4))

    explain_box(
        "Why uncertainty is subset-based",
        (
            "Uncertainty analysis was run on a balanced 40-case subset rather than all 200 non-zero cases. "
            "This keeps the experiment computationally practical while still covering all painting categories "
            "and non-zero damage types. Expanding this to all 200 non-zero cases is one possible post-feedback "
            "extension for the supervisor to prioritize."
        ),
        kind="warning",
    )

    st.markdown("### Model stack")

    col1, col2 = st.columns(2)

    fully_evaluated = summary_models.get("evaluated_models", legacy_models.get("fully_evaluated", []))
    feasibility_audited = summary_models.get(
        "feasibility_audited_not_fully_evaluated",
        legacy_models.get("feasibility_audited", []),
    )

    with col1:
        st.markdown("**Fully evaluated**")
        for model in fully_evaluated:
            st.markdown(f"- `{model}`")

    with col2:
        st.markdown("**Feasibility audited**")
        for model in feasibility_audited:
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
            "damage types. The refined comparison and the case reports focus on the 200 non-zero cases."
        ),
    )

    col1, col2 = st.columns(2)

    with col1:
        dataframe_block("Dataset summary", dataset_summary_df)

    with col2:
        dataframe_block("Damage summary", damage_summary_df)

    if dataset_summary_df.empty:
        dataset_from_summary_df = pd.DataFrame(
            {
                "field": ["controlled_paintings", "non_zero_cases", "painting_categories", "mask_types_non_zero"],
                "value": [
                    dashboard_summary.get("dataset", {}).get("controlled_paintings", "NA"),
                    dashboard_summary.get("dataset", {}).get("non_zero_cases", "NA"),
                    ", ".join(dashboard_summary.get("dataset", {}).get("painting_categories", [])),
                    ", ".join(dashboard_summary.get("dataset", {}).get("mask_types_non_zero", [])),
                ],
            }
        )
        dataframe_block("Dataset summary from Notebook 34", dataset_from_summary_df)

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

    if model_stack_df.empty:
        fallback_model_df = pd.DataFrame(
            {
                "model": [
                    "OpenCV Telea",
                    "LaMa",
                    "Stable Diffusion Inpainting",
                    "SDXL Inpainting",
                ],
                "evaluation_status": [
                    "fully_evaluated",
                    "fully_evaluated",
                    "fully_evaluated",
                    "feasibility_audited_only",
                ],
                "role": [
                    "deterministic classical baseline",
                    "learning-based inpainting baseline",
                    "generative inpainting and uncertainty target",
                    "resource feasibility audit",
                ],
            }
        )
        dataframe_block("Model stack from final dashboard state", fallback_model_df, height=260)

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

    if metric_policy_df.empty:
        fallback_policy_df = pd.DataFrame(
            {
                "metric_family": ["MSE", "PSNR", "SSIM", "LPIPS", "CLIP", "DINOv2", "Texture / brushstroke-proxy"],
                "final_region": ["masked_region", "masked_region", "mask_bbox_crop", "mask_bbox_crop", "mask_bbox_crop", "mask_bbox_crop", "mask_bbox_crop"],
                "reason": [
                    "pixel-error metric targeted to damaged pixels",
                    "pixel-fidelity metric targeted to damaged pixels",
                    "requires local spatial context",
                    "perceptual crop comparison requires context",
                    "feature comparison requires context",
                    "feature comparison requires context",
                    "local texture descriptors require spatial context",
                ],
            }
        )
        dataframe_block("Fallback final metric-region policy", fallback_policy_df, height=300)

    explain_box(
        "Final policy interpretation",
        (
            "No single metric is treated as absolute truth. The framework combines pixel fidelity, structural similarity, "
            "perceptual similarity, feature-space similarity, texture diagnostics, visual inspection, and uncertainty analysis."
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

    if not dashboard_model_winner_summary_df.empty:
        simple_bar(
            dashboard_model_winner_summary_df,
            x="refined_winner",
            y="cases",
            title="Refined Winner Cases by Model",
        )
    else:
        simple_bar(
            model_win_summary_df,
            x="model",
            y="majority_vote_cases",
            title="Refined Majority-Vote Cases by Model",
        )

    if not dashboard_metric_vote_summary_df.empty:
        simple_bar(
            dashboard_metric_vote_summary_df,
            x="model",
            y="total_metric_votes",
            title="Total Refined Metric Votes by Model",
        )

    comparison_source_df = model_comparison_cases_df.copy()

    if not comparison_source_df.empty:
        vote_col = pick_first_existing_column(
            comparison_source_df,
            ["refined_overall_metric_vote", "overall_metric_vote", "refined_winner"],
        )

        if vote_col:
            count_bar(
                comparison_source_df,
                column=vote_col,
                title="Case-Level Refined Metric Vote Distribution",
            )

        col1, col2 = st.columns(2)
        with col1:
            if "mask_type" in comparison_source_df.columns:
                count_bar(
                    comparison_source_df,
                    column="mask_type",
                    title="Compared Cases by Damage Type",
                )
        with col2:
            if "category" in comparison_source_df.columns:
                count_bar(
                    comparison_source_df,
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

    with st.expander("Model winner summary", expanded=True):
        dataframe_block("Notebook 34 winner summary", dashboard_model_winner_summary_df, height=220)
        if dashboard_model_winner_summary_df.empty:
            dataframe_block("Legacy model win summary", model_win_summary_df, height=260)

    with st.expander("Metric vote summary", expanded=True):
        dataframe_block("Notebook 34 metric vote summary", dashboard_metric_vote_summary_df, height=260)

    with st.expander("Per-metric winner summary", expanded=False):
        dataframe_block("Per-metric winner summary", per_metric_winner_summary_df)

    with st.expander("Summary by mask type", expanded=False):
        dataframe_block("Comparison by mask type", comparison_by_mask_type_df)

    with st.expander("Summary by painting category", expanded=False):
        dataframe_block("Comparison by category", comparison_by_category_df)

    st.markdown("### Case-level explorer")

    if comparison_source_df.empty:
        st.info("No case-level comparison table available.")
    else:
        filtered_df = comparison_source_df.copy()

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
                ["refined_overall_metric_vote", "overall_metric_vote", "refined_winner"],
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
            "refined_opencv_metric_wins",
            "refined_lama_metric_wins",
            "refined_stable_diffusion_metric_wins",
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
# Page: Texture Diagnostics
# =============================================================================

elif page == "Texture Diagnostics":
    st.header("Texture & Brushstroke-Proxy Diagnostics")

    explain_box(
        "What this section adds",
        (
            "Texture diagnostics inspect local surface-like structure that reference metrics may not capture cleanly. "
            "The brushstroke-proxy layer uses gradient and orientation descriptors as a directional texture proxy. "
            "It is not semantic brushstroke recognition, artist authentication, or conservation truth."
        ),
        kind="warning",
    )

    texture_winner_section_df = split_dashboard_summary_by_section(
        dashboard_texture_summary_df,
        "texture_winner_summary_nonzero",
    )
    brushstroke_section_df = split_dashboard_summary_by_section(
        dashboard_texture_summary_df,
        "brushstroke_proxy_summary_by_model",
    )
    high_texture_section_df = split_dashboard_summary_by_section(
        dashboard_texture_summary_df,
        "high_texture_brushwork_summary",
    )

    col1, col2 = st.columns(2)

    with col1:
        dataframe_block("Texture winner summary", texture_winner_section_df, height=280)

    with col2:
        dataframe_block("Brushstroke-proxy summary by model", brushstroke_section_df, height=280)

    dataframe_block("High-texture brushwork focus", high_texture_section_df, height=260)

    st.markdown("### Texture/refined disagreement cases")

    if dashboard_texture_disagreements_df.empty:
        st.info("No texture disagreement cases available.")
    else:
        filtered_df = dashboard_texture_disagreements_df.copy()

        col1, col2 = st.columns(2)
        with col1:
            if "category" in filtered_df.columns:
                categories = sorted(filtered_df["category"].dropna().unique())
                selected_categories = st.multiselect(
                    "Texture category filter",
                    categories,
                    default=categories,
                )
                filtered_df = filtered_df[filtered_df["category"].isin(selected_categories)]

        with col2:
            if "mask_type" in filtered_df.columns:
                masks = sorted(filtered_df["mask_type"].dropna().unique())
                selected_masks = st.multiselect(
                    "Texture mask filter",
                    masks,
                    default=masks,
                )
                filtered_df = filtered_df[filtered_df["mask_type"].isin(selected_masks)]

        st.caption(f"Filtered texture disagreement cases: {len(filtered_df)}")

        compact_table(
            filtered_df,
            [
                "case_id",
                "painting_id",
                "category",
                "mask_type",
                "refined_winner",
                "overall_metric_vote",
                "texture_winner",
                "texture_winner_model",
                "combined_texture_distance_winner",
                "brushstroke_proxy_distance_mean_winner",
                "texture_refined_agreement",
            ],
            height=420,
        )

        if "texture_winner_model" in filtered_df.columns:
            count_bar(
                filtered_df,
                column="texture_winner_model",
                title="Texture Disagreement Cases by Texture Winner",
            )

    explain_box(
        "Thesis interpretation",
        (
            "This layer supports the trustworthiness framework by showing that a restoration can look acceptable "
            "under aggregate reference metrics while still behaving differently under local texture diagnostics. "
            "This is especially relevant for high-texture brushwork cases."
        ),
        kind="success",
    )


# =============================================================================
# Page: Diffusion Uncertainty
# =============================================================================

elif page == "Diffusion Uncertainty":
    st.header("Stable Diffusion Uncertainty")

    explain_box(
        "What uncertainty means here",
        (
            "Stable Diffusion can generate different restorations for the same damaged image depending on the random seed. "
            "The uncertainty heatmap analysis measures spatial variation across seed outputs. High uncertainty does not "
            "automatically mean bad restoration, but it is a warning signal that the model is unstable for that case."
        ),
    )

    dataframe_block("Dashboard uncertainty summary", dashboard_uncertainty_summary_df, height=260)

    uncertainty_mask_section_df = split_dashboard_summary_by_section(
        dashboard_uncertainty_summary_df,
        "uncertainty_by_mask_type",
    )
    uncertainty_category_section_df = split_dashboard_summary_by_section(
        dashboard_uncertainty_summary_df,
        "uncertainty_by_category",
    )

    col1, col2 = st.columns(2)

    with col1:
        dataframe_block("Uncertainty by mask type", uncertainty_mask_section_df if not uncertainty_mask_section_df.empty else uncertainty_by_mask_type_df)

    with col2:
        dataframe_block("Uncertainty by category", uncertainty_category_section_df if not uncertainty_category_section_df.empty else uncertainty_by_category_df)

    st.markdown("### Highest uncertainty / selected heatmap cases")

    selected_uncertainty_source_df = dashboard_uncertainty_selected_cases_df.copy()

    if selected_uncertainty_source_df.empty:
        selected_uncertainty_source_df = uncertainty_cases_df.copy()

    if not selected_uncertainty_source_df.empty:
        uncertainty_sort_col = pick_first_existing_column(
            selected_uncertainty_source_df,
            [
                "masked_mean_uncertainty",
                "uncertainty_masked_mean_uncertainty",
                "combined_uncertainty_index",
            ],
        )

        if uncertainty_sort_col:
            highest_uncertainty_df = (
                selected_uncertainty_source_df
                .sort_values(uncertainty_sort_col, ascending=False)
                .head(15)
            )
        else:
            highest_uncertainty_df = selected_uncertainty_source_df.head(15)

        compact_table(
            highest_uncertainty_df,
            [
                "case_id",
                "painting_id",
                "category",
                "mask_type",
                "selection_reasons",
                "selection_count",
                "masked_mean_uncertainty",
                "boundary_mean_uncertainty",
                "outside_mask_mean_uncertainty",
                "combined_uncertainty_index",
                "heatmap_png_path",
                "overlay_png_path",
            ],
            height=380,
        )

        if uncertainty_sort_col:
            x_col = pick_first_existing_column(highest_uncertainty_df, ["case_id", "original_case_id"])
            if x_col:
                simple_bar(
                    highest_uncertainty_df,
                    x=x_col,
                    y=uncertainty_sort_col,
                    color="mask_type",
                    title="Top Stable Diffusion Uncertainty Cases",
                )

    st.markdown("### Uncertainty heatmap preview")

    preview_df = dashboard_uncertainty_selected_cases_df.copy()

    if preview_df.empty:
        st.info("No selected uncertainty heatmap cases available.")
    else:
        label_col = pick_first_existing_column(preview_df, ["case_id", "original_case_id", "painting_id"])

        selected_index = st.selectbox(
            "Select uncertainty case",
            preview_df.index,
            format_func=lambda idx: (
                f"{preview_df.loc[idx].get(label_col, idx)}"
                f" | {preview_df.loc[idx].get('category', 'unknown')}"
                f" | {preview_df.loc[idx].get('mask_type', 'unknown')}"
            ),
        )

        selected_row = preview_df.loc[selected_index]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Heatmap**")
            render_image_from_path(selected_row.get("heatmap_png_path"), caption="Seed-variation heatmap")
        with col2:
            st.markdown("**Overlay**")
            render_image_from_path(selected_row.get("overlay_png_path"), caption="Uncertainty overlay")

        with st.expander("Selected uncertainty case details"):
            st.dataframe(selected_row.to_frame(name="value"), use_container_width=True, height=420)

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
        x_col = pick_first_existing_column(
            uncertainty_vs_performance_df,
            ["masked_mean_uncertainty", "combined_uncertainty_index"],
        )
        y_col = pick_first_existing_column(
            uncertainty_vs_performance_df,
            [
                "refined_stable_diffusion_metric_wins",
                "stable_diffusion_metric_wins",
                "sd_metric_wins",
            ],
        )

        if x_col and y_col:
            simple_scatter(
                uncertainty_vs_performance_df,
                x=x_col,
                y=y_col,
                color="mask_type" if "mask_type" in uncertainty_vs_performance_df.columns else None,
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
# Page: Case Reports
# =============================================================================

elif page == "Case Reports":
    st.header("Selected Case Diagnostic Reports")

    explain_box(
        "Purpose of case reports",
        (
            "Notebook 33 generated selected case-level reports that combine clean/damaged/mask inputs, all three "
            "model restorations, refined metric summaries, texture diagnostics, and uncertainty heatmaps when available. "
            "These are inspection artifacts, not new metric computations."
        ),
    )

    if dashboard_selected_cases_df.empty and dashboard_case_report_manifest_df.empty:
        st.info("No selected case report assets available.")
    else:
        source_df = dashboard_selected_cases_df.copy()

        if source_df.empty:
            source_df = dashboard_case_report_manifest_df.copy()

        col1, col2, col3 = st.columns(3)
        with col1:
            if "category" in source_df.columns:
                categories = sorted(source_df["category"].dropna().unique())
                selected_categories = st.multiselect("Case category", categories, default=categories)
                source_df = source_df[source_df["category"].isin(selected_categories)]
        with col2:
            if "mask_type" in source_df.columns:
                masks = sorted(source_df["mask_type"].dropna().unique())
                selected_masks = st.multiselect("Case mask type", masks, default=masks)
                source_df = source_df[source_df["mask_type"].isin(selected_masks)]
        with col3:
            reason_text = st.text_input("Filter selection reason contains", value="")
            if reason_text and "selection_reasons" in source_df.columns:
                source_df = source_df[
                    source_df["selection_reasons"].astype(str).str.contains(reason_text, case=False, na=False)
                ]

        st.caption(f"Filtered selected case reports: {len(source_df)}")

        if "has_uncertainty_heatmap" in source_df.columns or "has_texture_disagreement" in source_df.columns:
            col1, col2 = st.columns(2)
            with col1:
                if "has_uncertainty_heatmap" in source_df.columns:
                    count_bar(source_df, "has_uncertainty_heatmap", "Selected Cases with Uncertainty Heatmaps")
            with col2:
                if "has_texture_disagreement" in source_df.columns:
                    count_bar(source_df, "has_texture_disagreement", "Selected Cases with Texture Disagreement")

        compact_table(
            source_df,
            [
                "case_id",
                "category",
                "mask_type",
                "selection_reasons",
                "selection_count",
                "has_uncertainty_heatmap",
                "has_texture_disagreement",
                "uncertainty_masked_mean_uncertainty",
                "uncertainty_boundary_mean_uncertainty",
                "case_report_html_path",
                "case_diagnostic_grid_path",
            ],
            height=360,
        )

        if not source_df.empty:
            label_col = pick_first_existing_column(source_df, ["case_id", "painting_id"])
            selected_index = st.selectbox(
                "Select diagnostic case",
                source_df.index,
                format_func=lambda idx: (
                    f"{source_df.loc[idx].get(label_col, idx)}"
                    f" | {source_df.loc[idx].get('category', 'unknown')}"
                    f" | {source_df.loc[idx].get('mask_type', 'unknown')}"
                ),
            )

            selected_row = source_df.loc[selected_index]

            detail_col, image_col = st.columns([1, 2])

            with detail_col:
                st.markdown("### Case details")
                st.markdown(f"**Case ID:** {readable_value(selected_row.get('case_id'))}")
                st.markdown(f"**Category:** {readable_value(selected_row.get('category'))}")
                st.markdown(f"**Mask type:** {readable_value(selected_row.get('mask_type'))}")
                st.markdown(f"**Selection reasons:** {readable_value(selected_row.get('selection_reasons'))}")
                st.markdown(
                    f"**Masked uncertainty:** {readable_uncertainty_value(selected_row.get('uncertainty_masked_mean_uncertainty'))}"
                )
                st.markdown(
                    f"**Boundary uncertainty:** {readable_uncertainty_value(selected_row.get('uncertainty_boundary_mean_uncertainty'))}"
                )

                st.markdown("### Local report files")
                render_local_asset_link("HTML case report", selected_row.get("case_report_html_path"))
                render_local_asset_link("Diagnostic grid", selected_row.get("case_diagnostic_grid_path"))

                report_path = resolve_project_path(selected_row.get("case_report_html_path"))
                if report_path and report_path.exists():
                    st.caption("Open the HTML path locally from the repository if the browser blocks file links.")

            with image_col:
                st.markdown("### Diagnostic grid preview")
                render_image_from_path(selected_row.get("case_diagnostic_grid_path"), caption="Notebook 33 selected case grid")

            with st.expander("Raw selected case row"):
                st.dataframe(selected_row.to_frame(name="value"), use_container_width=True, height=460)

    st.markdown("### Case report index")
    render_local_asset_link(
        "Case report index",
        dashboard_summary.get("case_reports", {}).get("case_report_index")
        or dashboard_summary.get("reports", {}).get("case_report_index")
        or "outputs/reports/case_diagnostics/case_report_index.html",
    )


# =============================================================================
# Page: Visual Explorer
# =============================================================================

elif page == "Visual Explorer":
    st.header("Visual Case Explorer")

    explain_box(
        "What changed",
        (
            "The original visual explorer is retained for older dashboard visual cases. "
            "For the final pre-feedback case reports, use the new Case Reports page. "
        ),
    )

    if visual_cases_df.empty:
        st.info("No legacy visual cases available. Use the Case Reports page for Notebook 33 diagnostic reports.")
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

    if findings:
        for finding in findings:
            finding_id = finding.get("finding_id", "")
            title = finding.get("title", "")
            summary = finding.get("summary", "")
            evidence = finding.get("evidence", "")

            with st.expander(f"{finding_id}: {title}", expanded=True):
                st.markdown(summary)

                if evidence:
                    st.caption(f"Evidence: {evidence}")
    else:
        st.markdown("### Pre-feedback findings")
        st.success(
            """
1. The controlled 50-painting benchmark is complete for 200 non-zero restoration cases.
2. LaMa dominates the refined reference-based comparison.
3. OpenCV Telea remains a useful deterministic baseline.
4. Stable Diffusion rarely wins under reference metrics but is important for studying plausibility and instability.
5. Texture and brushstroke-proxy diagnostics add a local-structure layer beyond aggregate reference metrics.
6. Stable Diffusion heatmaps show seed-based spatial variability, not calibrated confidence.
7. Selected case reports make disagreement and instability inspectable at the individual-case level.
"""
        )

    st.markdown("### Thesis contribution summary")

    st.success(
        """
The current experiment supports the thesis framing that AI-assisted painting restoration requires
a trustworthiness evaluation framework.

The strongest contribution is not that one model wins. The stronger contribution is showing that
reference metrics, visual plausibility, metric-region policy, texture diagnostics, model uncertainty,
and feasibility constraints can point to different conclusions.
"""
    )

    st.markdown("### Supervisor confirmation still needed")

    st.warning(
        """
Open points:

1. Is the 50-painting controlled subset sufficient?
2. Should the final experiment scale toward 300 paintings?
3. Is the refined metric-region policy accepted?
4. Should texture and brushstroke-proxy diagnostics remain part of the core framework?
5. Is the 40-case Stable Diffusion uncertainty subset sufficient?
6. Should uncertainty heatmaps be expanded to all 200 non-zero cases?
7. Should SDXL remain feasibility-audited only?
8. Should metric-policy ablation be added after feedback?
9. Should color consistency metrics be added?
10. Should boundary/seam consistency metrics be added?
11. Should damage-size sensitivity analysis be added?
12. Should restoration risk scoring or diagnostic risk profiles be added?
13. Should metadata-driven or computed visual grouping be added?
14. Should mask/input robustness analysis be added?
15. Should semantic/iconographic checks be added after feedback?
16. Should the Streamlit dashboard become a formal supporting artifact?
17. Should generic restoration prompts be supllemented by style-specific restoration prompts?
"""
    )


# =============================================================================
# Page: Reports
# =============================================================================

elif page == "Reports":
    st.header("Reports & Reproducibility")

    st.markdown("### Final report links")

    render_local_asset_link(
        "Stable Diffusion uncertainty heatmap report",
        dashboard_summary.get("reports", {}).get("uncertainty_heatmap_report")
        or "outputs/reports/stable_diffusion_uncertainty_heatmap_report_50.html",
    )
    render_local_asset_link(
        "Selected case report index",
        dashboard_summary.get("reports", {}).get("case_report_index")
        or "outputs/reports/case_diagnostics/case_report_index.html",
    )

    if not dashboard_figure_manifest_df.empty:
        dataframe_block("Figure and report manifest", dashboard_figure_manifest_df, height=420)

    st.markdown("### Legacy reports manifest")

    if not reports:
        st.info("No legacy reports manifest available.")
    else:
        reports_df = pd.DataFrame(reports)
        st.dataframe(reports_df, use_container_width=True, height=260)

        for report in reports:
            label = report.get("label") or report.get("name") or "Report"
            path_value = report.get("path") or report.get("project_relative_path") or ""

            if path_value:
                render_local_asset_link(label, path_value)

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

    st.markdown("### Notebook 34 dashboard summary")
    st.json(dashboard_summary if dashboard_summary else {"status": "dashboard_summary.json not found"})

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
        st.warning("Asset lookup is empty. Check dashboard_asset_manifest.json or legacy dashboard_assets_manifest.json.")

    st.markdown("### Loaded dataframe shapes")

    loaded_shapes = pd.DataFrame(
        [
            {"name": "dashboard_model_winner_summary_df", "rows": len(dashboard_model_winner_summary_df), "columns": len(dashboard_model_winner_summary_df.columns)},
            {"name": "dashboard_metric_vote_summary_df", "rows": len(dashboard_metric_vote_summary_df), "columns": len(dashboard_metric_vote_summary_df.columns)},
            {"name": "dashboard_texture_summary_df", "rows": len(dashboard_texture_summary_df), "columns": len(dashboard_texture_summary_df.columns)},
            {"name": "dashboard_texture_disagreements_df", "rows": len(dashboard_texture_disagreements_df), "columns": len(dashboard_texture_disagreements_df.columns)},
            {"name": "dashboard_uncertainty_summary_df", "rows": len(dashboard_uncertainty_summary_df), "columns": len(dashboard_uncertainty_summary_df.columns)},
            {"name": "dashboard_uncertainty_selected_cases_df", "rows": len(dashboard_uncertainty_selected_cases_df), "columns": len(dashboard_uncertainty_selected_cases_df.columns)},
            {"name": "dashboard_case_report_manifest_df", "rows": len(dashboard_case_report_manifest_df), "columns": len(dashboard_case_report_manifest_df.columns)},
            {"name": "dashboard_selected_cases_df", "rows": len(dashboard_selected_cases_df), "columns": len(dashboard_selected_cases_df.columns)},
            {"name": "dashboard_figure_manifest_df", "rows": len(dashboard_figure_manifest_df), "columns": len(dashboard_figure_manifest_df.columns)},
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

    st.dataframe(loaded_shapes, use_container_width=True, height=620)

    st.markdown("### Dashboard directories")

    st.code(
        f"""
PROJECT_ROOT={PROJECT_ROOT}
DASHBOARD_DIR={DASHBOARD_DIR}
DASHBOARD_DATA_DIR={DASHBOARD_DATA_DIR}
DASHBOARD_MANIFEST_DIR={DASHBOARD_MANIFEST_DIR}
METRICS_DIR={METRICS_DIR}
REPORTS_DIR={REPORTS_DIR}
FIGURES_DIR={FIGURES_DIR}
        """.strip(),
        language="text",
    )
