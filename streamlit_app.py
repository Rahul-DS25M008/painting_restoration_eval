"""Presentation-only Streamlit dashboard for the validated Notebook 34 package."""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from restoration_eval.dashboard_application import (  # noqa: E402
    DashboardBundle,
    case_visual_paths,
    default_case_rows,
    display_label,
    filter_frame,
    json_list,
    load_dashboard_package,
    report_bytes,
    safe_project_path,
    stable_options,
    truthy,
)
from restoration_eval.dashboard_metrics import (  # noqa: E402
    METRIC_SOURCES,
    CANDIDATE_SOURCES,
    aggregate_metric_records,
    attach_candidate_identity,
    candidate_seed_metadata,
    load_case_metric_rows,
    metric_source_path,
    source_signature,
)


st.set_page_config(
    page_title="Trustworthy Painting Restoration",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


PALETTE = {
    "paper": "#f1eadb",
    "paper_light": "#faf7ef",
    "green": "#123f3a",
    "deep_green": "#0b302c",
    "umber": "#6e4b32",
    "vermilion": "#b74b32",
    "ochre": "#b88a2e",
    "charcoal": "#272623",
    "graphite": "#777064",
    "sage": "#607a6d",
}
MODEL_COLOURS = {
    "lama": PALETTE["green"],
    "opencv_telea": PALETTE["ochre"],
    "stable_diffusion_inpainting": PALETTE["vermilion"],
    "sdxl_inpainting": PALETTE["umber"],
}
PAGE_ICONS = {
    "Overview": "⌂",
    "Study Design": "▤",
    "Metric Framework": "⌁",
    "Model Performance": "▥",
    "Robustness & Uncertainty": "◇",
    "Trustworthiness & XAI": "⌕",
    "Case Explorer": "▧",
    "Reports & Reproducibility": "▱",
}


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');
:root { --paper:#f1eadb;--paper-light:#faf7ef;--green:#123f3a;--deep-green:#0b302c;--umber:#6e4b32;--vermilion:#b74b32;--ochre:#b88a2e;--charcoal:#272623;--graphite:#777064; }
.stApp { background:radial-gradient(circle at 17% 8%,rgba(92,74,45,.045) 0 1px,transparent 1.6px) 0 0/17px 19px,linear-gradient(93deg,rgba(255,255,255,.18),rgba(101,75,42,.025)),var(--paper);color:var(--charcoal);font-family:Inter,system-ui,sans-serif; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,rgba(255,255,255,.025),transparent 27%),var(--deep-green);border-right:1px solid rgba(184,138,46,.55); }
[data-testid="stSidebar"] * { color:#f2ead8; }
[data-testid="stSidebar"] .stRadio label { border:1px solid transparent;border-radius:2px;padding:.5rem .55rem;margin:.08rem 0; }
[data-testid="stSidebar"] .stRadio label:hover { border-color:rgba(184,138,46,.45);background:rgba(255,255,255,.04); }
[data-testid="stSidebar"] label:has(input:checked) { background:rgba(183,75,50,.82);border-color:rgba(241,234,219,.24); }
h1,h2,h3,.museum-title,.museum-subtitle { font-family:"Cormorant Garamond",Georgia,serif!important;color:var(--charcoal); }
p,li,label,[data-testid="stMetricValue"] { color:var(--charcoal); }
.block-container { max-width:1500px;padding-top:1.5rem;padding-bottom:2.5rem; }
.museum-kicker { color:var(--vermilion);text-transform:uppercase;letter-spacing:.22em;font-size:.75rem;font-weight:700;margin-bottom:.15rem; }
.museum-title { font-size:clamp(2rem,3vw,3.25rem);line-height:.98;font-weight:700; }
.museum-question { font-family:"Cormorant Garamond",Georgia,serif;font-style:italic;font-size:1.15rem;color:var(--umber); }
.thesis-strip { border-top:1px solid rgba(39,38,35,.38);border-bottom:1px solid rgba(39,38,35,.38);background:rgba(250,247,239,.68);padding:1rem 1.15rem;margin:.8rem 0 1.1rem;box-shadow:4px 4px 0 rgba(110,75,50,.07); }
.thesis-strip strong { font-family:"Cormorant Garamond",Georgia,serif;font-size:1.55rem;font-weight:600; }
.paper-card { min-height:118px;border:1px solid rgba(62,55,45,.30);border-radius:2px;background:rgba(250,247,239,.72);padding:.85rem 1rem;margin-bottom:.55rem;box-shadow:3px 3px 0 rgba(110,75,50,.06); }
.paper-card .eyebrow { text-transform:uppercase;letter-spacing:.1em;font-size:.66rem;color:var(--umber); }
.paper-card .value { font-family:"Cormorant Garamond",Georgia,serif;font-weight:700;color:var(--green);font-size:2rem;line-height:1; }
.paper-card .label { font-family:"Cormorant Garamond",Georgia,serif;font-size:1.05rem;line-height:1.05;margin-top:.25rem; }
.evidence-note { border-left:4px solid var(--ochre);background:rgba(250,247,239,.68);padding:.75rem .9rem;margin:.5rem 0 .8rem; }
.evidence-note.danger { border-left-color:var(--vermilion); }.evidence-note.good { border-left-color:var(--green); }
.evidence-note strong { color:var(--green);font-weight:700; }.evidence-note.danger strong { color:var(--vermilion); }
.evidence-note em { font-family:"Cormorant Garamond",Georgia,serif;font-size:1.04em; }
.smallcaps { text-transform:uppercase;letter-spacing:.12em;font-size:.7rem;color:var(--umber);font-weight:700; }
.divider { height:1px;background:rgba(39,38,35,.28);margin:.7rem 0 1rem;transform:rotate(-.04deg); }
.caption-note { font-family:"Cormorant Garamond",Georgia,serif;font-style:italic;color:var(--umber);font-size:1rem; }
.status-chip { display:inline-block;border:1px solid rgba(39,38,35,.28);padding:.18rem .5rem;margin:.08rem .2rem .08rem 0;font-size:.72rem;background:rgba(250,247,239,.72); }
.status-chip.good { color:var(--green);border-color:rgba(18,63,58,.55); }.status-chip.warn { color:#8a5b18;border-color:rgba(184,138,46,.7); }.status-chip.danger { color:var(--vermilion);border-color:rgba(183,75,50,.65); }
.visual-frame img { border:1px solid rgba(39,38,35,.35);box-shadow:4px 4px 0 rgba(18,63,58,.08); }
[data-testid="stDataFrame"] { border:1px solid rgba(39,38,35,.24); }
[data-testid="stMetric"] { border:1px solid rgba(39,38,35,.26);border-radius:2px;background:rgba(250,247,239,.72);padding:.75rem .9rem; }
.stButton>button,.stDownloadButton>button { border-radius:2px;border:1px solid var(--green);color:var(--green);background:rgba(250,247,239,.82);font-weight:600; }
.stButton>button:hover,.stDownloadButton>button:hover { background:var(--green);color:#fff8e8; }
.stTabs [data-baseweb="tab-list"] { gap:.2rem;border-bottom:1px solid rgba(39,38,35,.3); }.stTabs [data-baseweb="tab"] { border-radius:0;font-family:"Cormorant Garamond",Georgia,serif;font-size:1.05rem; }.stTabs [aria-selected="true"] { color:var(--vermilion)!important;border-bottom:2px solid var(--vermilion); }
footer { visibility:hidden; }
header[data-testid="stHeader"] { height:0;min-height:0;background:transparent; }
[data-testid="stToolbar"],[data-testid="stDecoration"] { display:none!important; }
.paper-card .label,.paper-card small { overflow-wrap:normal;word-break:normal;hyphens:none; }
@media (max-width:900px) { .block-container{padding:1rem 1rem 2rem}.museum-title{font-size:2.2rem}.paper-card{min-height:98px}.paper-card .value{font-size:1.65rem}.paper-card .label{font-size:.96rem} }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Opening the validated evidence catalogue…")
def get_bundle() -> DashboardBundle:
    return load_dashboard_package(PROJECT_ROOT)


@st.cache_data(max_entries=12, show_spinner="Reading saved case metrics…")
def get_case_metric_rows(case_id: str, source: str, signature: tuple) -> pd.DataFrame:
    return load_case_metric_rows(PROJECT_ROOT, case_id, source)


@st.cache_data(max_entries=12, show_spinner=False)
def get_case_seed_metadata(case_id: str, signatures: tuple) -> pd.DataFrame:
    return candidate_seed_metadata(PROJECT_ROOT, case_id)


def render_case_numeric_metrics(bundle: DashboardBundle, selected: pd.Series) -> None:
    st.subheader("Numerical metrics for this case")
    st.caption(
        f"Painting {selected['painting_id']} · case {selected['case_id']}. "
        "Compare saved values across models below. These controls do not change the images above. "
        "Each candidate/seed/prompt stays separate; no averages or new metrics are calculated."
    )
    candidates = bundle.indexes["case_index"]
    candidates = candidates[candidates["case_id"].eq(selected["case_id"])].copy()
    controls = st.columns(3)
    with controls[0]:
        source = st.selectbox("Metric family", list(METRIC_SOURCES), key="numeric_family")
    with controls[1]:
        scope = st.selectbox("Candidate scope", ["All candidates for this case", "Selected candidate only"], key="numeric_scope")
    with controls[2]:
        models = st.multiselect("Compare models", stable_options(candidates, "model_id"),
                                default=stable_options(candidates, "model_id"),
                                format_func=model_name, key=f"numeric_models_{selected['case_id']}")
    candidates = candidates[candidates["model_id"].isin(models)]
    if scope == "Selected candidate only":
        candidates = candidates[candidates["candidate_id"].eq(selected["candidate_id"])]
    if candidates.empty:
        st.info("Select a model that includes a candidate in this comparison scope.")
        return
    try:
        raw = get_case_metric_rows(str(selected["case_id"]), source,
                                   source_signature(PROJECT_ROOT, metric_source_path(source)))
        signatures = tuple(source_signature(PROJECT_ROOT, p) for p in CANDIDATE_SOURCES)
        seeds = get_case_seed_metadata(str(selected["case_id"]), signatures)
        values, missing = attach_candidate_identity(raw, candidates, seeds)
    except (ValueError, KeyError, OSError) as exc:
        st.error(f"Saved numerical evidence could not be verified: {exc}")
        return
    if not missing.empty:
        st.info(
            f"{len(missing)} selected candidate(s) have no saved rows in this metric family. "
            "Additional N22 damage-size seeds have group uncertainty evidence, not individual "
            "reference-quality scores. Anchor scores are never substituted."
        )
        with st.expander("Candidates without saved metrics in this family"):
            st.dataframe(missing, hide_index=True, width="stretch")
    if values.empty:
        return
    filters = st.columns(4)
    with filters[0]:
        regions = stable_options(values, "region_id")
        default_region = regions.index("masked_region") if "masked_region" in regions else 0
        region = st.selectbox("Metric region", regions, index=default_region,
                              key=f"numeric_region_{source}")
    values = values[values["region_id"].eq(region)]
    with filters[1]:
        metric = st.selectbox("Measure", ["All", *stable_options(values, "metric_name")],
                              key=f"numeric_measure_{source}_{region}")
    with filters[2]:
        seed = st.selectbox("Seed", ["All", *stable_options(values, "seed")], key="numeric_seed")
    with filters[3]:
        prompt = st.selectbox("Prompt arm", ["All", *stable_options(values, "prompt_variant_id")], key="numeric_prompt")
    shown = filter_frame(values, metric_name=metric, seed=seed, prompt_variant_id=prompt)
    shown = shown.sort_values(["metric_name", "model_id", "candidate_id", "source_record_id"], kind="stable")
    columns = ["model_id", "seed", "prompt_variant_id", "metric_name", "region_id",
               "damaged_value", "restored_value", "improvement_value", "better_direction",
               "value_unit", "status", "applicability_status", "issue", "candidate_id", "metric_family",
               "feature_model_id", "evidence_component", "summary_statistic", "semantic_target_scope"]
    st.dataframe(shown[[c for c in columns if c in shown]], hide_index=True,
                 width="stretch", height=360,
                 column_config={c: st.column_config.NumberColumn(c.replace("_", " ").title(), format="%.6f")
                                for c in ("damaged_value", "restored_value", "improvement_value")})
    st.caption(
        f"{len(shown)} saved records. Positive improvement means better than the damaged input "
        "under the stored direction. Blank/not-applicable values are not zero; infinite PSNR "
        "can represent zero reconstruction error. Rows marked not applicable must not be ranked, "
        "even if the producer retained a diagnostic number. Table display is rounded; CSV retains numeric precision. "
        "Proxy metrics do not establish conservation suitability."
    )
    st.download_button("Download displayed case metrics (CSV)", shown.to_csv(index=False).encode("utf-8"),
                       file_name=f"{selected['case_id']}_metrics.csv", mime="text/csv", key="numeric_download")
    st.caption(f"Read-only source: {metric_source_path(source)} · exact source IDs and provenance included in CSV.")


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def page_header(kicker: str, title: str, question: str) -> None:
    st.markdown(
        f'<div class="museum-kicker">{esc(kicker)}</div><div class="museum-title">{esc(title)}</div><div class="museum-question">— {esc(question)}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


def paper_card(label: str, value: Any, unit: str = "", eyebrow: str = "Evidence") -> None:
    shown = f"{value:g}" if isinstance(value, float) and value.is_integer() else str(value)
    st.markdown(
        '<div class="paper-card">'
        f'<div class="eyebrow">{esc(eyebrow)}</div><div class="value">{esc(shown)}</div><div class="label">{esc(label)}'
        + (f'<br><small>{esc(unit)}</small>' if unit else "")
        + "</div></div>",
        unsafe_allow_html=True,
    )


def evidence_note(title: str, text: str, tone: str = "") -> None:
    st.markdown(
        f'<div class="evidence-note {esc(tone)}"><span class="smallcaps">{esc(title)}</span><br>{esc(text)}</div>',
        unsafe_allow_html=True,
    )


def rich_evidence_note(title: str, trusted_html: str, tone: str = "") -> None:
    """Render authored emphasis while continuing to escape the label itself."""

    st.markdown(
        f'<div class="evidence-note {esc(tone)}"><span class="smallcaps">{esc(title)}</span><br>{trusted_html}</div>',
        unsafe_allow_html=True,
    )


def emphasize_evidence_text(value: Any) -> str:
    """Emphasise model names and numeric evidence in already-authored prose."""

    text = esc(value)
    text = re.sub(
        r"\b(Stable Diffusion|OpenCV Telea|LaMa|SDXL|Telea)\b",
        lambda match: f"<strong><em>{match.group(1)}</em></strong>",
        text,
    )
    return re.sub(
        r"(?<![\w>])(\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:%| of \d{1,3}(?:,\d{3})*)?)(?![\w<])",
        r"<strong>\1</strong>",
        text,
    )


def styled_figure(fig: go.Figure, *, height: int = 430) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=22, r=18, t=42, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(250,247,239,.36)",
        font=dict(family="Inter", color=PALETTE["charcoal"], size=12),
        title_font=dict(family="Cormorant Garamond", size=23, color=PALETTE["charcoal"]),
        legend_title_text="",
        hoverlabel=dict(bgcolor=PALETTE["paper_light"], font_color=PALETTE["charcoal"]),
    )
    fig.update_xaxes(gridcolor="rgba(62,55,45,.12)", zerolinecolor="rgba(62,55,45,.22)")
    fig.update_yaxes(gridcolor="rgba(62,55,45,.12)", zerolinecolor="rgba(62,55,45,.22)")
    return fig


def show_image(path_value: Any, caption: str, *, empty_message: str = "Asset not available") -> None:
    path = safe_project_path(path_value, PROJECT_ROOT, allowed_suffixes={".png", ".jpg", ".jpeg", ".webp"})
    if path is None:
        st.caption(empty_message)
        return
    st.markdown('<div class="visual-frame">', unsafe_allow_html=True)
    st.image(str(path), caption=caption, width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)


def show_paths(paths: Iterable[Path], *, max_items: int = 4) -> None:
    resolved = list(paths)[:max_items]
    if not resolved:
        st.caption("No applicable diagnostic image is indexed for this candidate.")
        return
    columns = st.columns(min(len(resolved), max_items))
    for column, path in zip(columns, resolved):
        with column:
            st.image(str(path), caption=path.stem.replace("_", " ").title(), width="stretch")


def select_one(label: str, options: list[str], *, key: str, all_option: bool = False) -> str:
    choices = (["All"] if all_option else []) + options
    if not choices:
        return "All" if all_option else ""
    return st.selectbox(label, choices, format_func=display_label, key=key)


def model_name(model_id: Any) -> str:
    return display_label(model_id)


def representative_case(bundle: DashboardBundle, *, key_prefix: str, compact: bool = False) -> pd.Series | None:
    cases = default_case_rows(bundle.indexes["case_index"])
    case_ids = stable_options(cases, "case_id")
    if not case_ids:
        st.warning("No approved cases are available.")
        return None
    default_case = "canonical__p001__loss_large" if "canonical__p001__loss_large" in case_ids else case_ids[0]
    chosen_case = st.selectbox("Representative case", case_ids, index=case_ids.index(default_case), key=f"{key_prefix}_case")
    group = cases[cases["case_id"] == chosen_case].sort_values(["model_id", "candidate_id"], kind="stable")
    first = group.iloc[0]
    primary = st.columns(3)
    for column, field, caption in zip(primary, ("clean_path", "damaged_path", "mask_path"), ("Original", "Damaged", "Mask")):
        with column:
            show_image(first[field], caption)
    if not compact:
        model_rows = group.drop_duplicates("model_id", keep="first")
        columns = st.columns(min(4, max(1, len(model_rows))))
        for column, (_, row) in zip(columns, model_rows.iterrows()):
            with column:
                show_image(row["restored_path"], model_name(row["model_id"]))
    return first


EXPERIMENT_EXPLANATIONS = {
    "canonical_missing_region": (
        "Five fixed conditions are applied to every painting: large loss, "
        "small loss, mixed damage, thin scratches, and an unchanged zero "
        "control. The gallery makes the input and mask geometry visible."
    ),
    "damage_size_sensitivity": (
        "The same large-loss damage grows through seven target levels: 2%, "
        "4%, 6%, 8%, 10%, 15%, and 20% of the painting. Comparing one "
        "painting across the sequence isolates sensitivity to damage extent."
    ),
    "mask_robustness": (
        "Five mask placements are tested for each selected painting, damage "
        "type, and target size. The content changes because mask location and "
        "shape change; this is robustness evidence, not generative uncertainty."
    ),
    "synthetic_degradation": (
        "Dirt and dust, partial transparency, water stain, and a combined "
        "water-stain/dirt condition test broader synthetic degradation. "
        "Mild, moderate, and severe inputs are shown where defined."
    ),
}


METRIC_FAMILY_GUIDANCE = {
    "classical_pixel": (
        "Compares restored and reference pixel values directly, including MAE, MSE, RMSE, and PSNR.",
        "Error measures are better when lower; PSNR is better when higher.",
        "Pixel agreement can reward smooth repairs that still look structurally or historically wrong.",
    ),
    "ssim": (
        "Compares local luminance, contrast, and structure between the restoration and reference.",
        "Higher SSIM means closer local structural similarity.",
        "SSIM can disagree with colour, texture, perceptual, and seam evidence.",
    ),
    "perceptual": (
        "Uses LPIPS to compare learned visual features rather than exact pixel values.",
        "Lower LPIPS means the restoration is perceptually closer to the reference.",
        "LPIPS is a learned proxy, not a conservator judgement.",
    ),
    "lpips": (
        "Measures learned perceptual distance between two contiguous image regions.",
        "Lower distance means closer learned-feature appearance.",
        "It cannot establish authenticity, iconographic correctness, or treatment suitability.",
    ),
    "feature_similarity": (
        "Uses CLIP and DINOv2 embeddings to compare broad appearance and retained visual structure.",
        "Higher cosine similarity means the selected crops remain more closely aligned.",
        "High feature similarity can coexist with invented or historically incorrect detail.",
    ),
    "clip": (
        "Uses CLIP embeddings to compare broad visual and semantic similarity.",
        "Higher cosine similarity means stronger feature alignment.",
        "CLIP similarity is not evidence of historical authenticity.",
    ),
    "dinov2": (
        "Uses DINOv2 embeddings to compare visual structure and representation-level continuity.",
        "Higher cosine similarity means stronger retained visual structure.",
        "Representation similarity does not prove that generated detail is correct.",
    ),
    "colour": (
        "Uses perceptual colour-difference evidence such as CIEDE2000 inside approved regions.",
        "Lower colour difference means closer perceived colour agreement.",
        "Good colour matching does not guarantee correct texture, edges, or subject matter.",
    ),
    "seam": (
        "Measures continuity where the repaired area meets surrounding original content.",
        "Lower mismatch means a less visible repair boundary.",
        "A clean seam does not guarantee that the repair interior is correct.",
    ),
    "texture_map": (
        "Maps local texture differences so concentrated brushwork or surface mismatches remain visible.",
        "Lower local error means closer texture continuity.",
        "Texture agreement does not establish semantic or historical correctness.",
    ),
    "texture_descriptor": (
        "Summarises local texture patterns with descriptor-based comparisons.",
        "Interpret the direction shown for the selected descriptor; closer agreement is preferred.",
        "A descriptor compresses complex brushwork and can miss visually important local failures.",
    ),
    "spatial_diagnostics": (
        "Keeps error spatially located instead of reducing the restoration to one whole-image number.",
        "Lower error or stronger improvement is preferable within the declared region.",
        "A scalar extracted from a map can still hide where the largest error occurs.",
    ),
    "semantic_patch": (
        "Compares local feature relationships in contiguous patches around the repair.",
        "Higher similarity or correlation means stronger local semantic continuity.",
        "Feature continuity cannot verify iconography or historical detail.",
    ),
    "local_semantic_preservation": (
        "Tests whether local visual meaning and feature structure are retained around the repair.",
        "Higher local similarity means better preservation of the reference feature pattern.",
        "It cannot prove that reconstructed content is historically correct.",
    ),
    "structural_layout": (
        "Compares relationships between image regions using reference-affinity structure.",
        "Higher correlation means stronger preservation of the reference layout.",
        "Layout agreement does not establish fine-detail correctness.",
    ),
    "uncertainty_pixelwise": (
        "Measures how much repeated Stable Diffusion candidates vary at each pixel.",
        "Higher variation means weaker agreement across the four seeds.",
        "Low variability can still describe several consistently wrong restorations.",
    ),
    "uncertainty_perceptual": (
        "Compares repeated candidates using perceptual feature distance.",
        "Higher pairwise distance means the seed outputs look less alike.",
        "This is empirical seed variability, not calibrated confidence.",
    ),
}


PROPOSAL_RESEARCH_QUESTIONS = {
    "rq1": "How can a multi-metric evaluation framework be designed to assess AI-generated painting restorations beyond traditional image similarity metrics?",
    "rq2": "How do selected pretrained inpainting models differ in restoration quality across artistic styles and artificial damage types?",
    "rq3": "To what extent can uncertainty estimation from multiple restoration candidates identify speculative or unreliable restored regions?",
}


def case_parameter_label(row: pd.Series) -> str:
    """Return a concise, human-readable label for one registered case."""

    case_id = str(row.get("case_id", ""))
    experiment_id = str(row.get("experiment_id", ""))
    if experiment_id == "damage_size_sensitivity":
        match = re.search(r"size_(\d+)pct", case_id)
        return f"{int(match.group(1))}% damage" if match else display_label(case_id)
    if experiment_id == "mask_robustness":
        target = re.search(r"target_(\d+)(?:p(\d+))?pct", case_id)
        variant = re.search(r"variant_(\d+)", case_id)
        if target:
            fraction = target.group(1)
            if target.group(2):
                fraction += f".{target.group(2)}"
            placement = int(variant.group(1)) if variant else "?"
            return f"{fraction}% · placement {placement}"
    if experiment_id == "synthetic_degradation":
        return f"{display_label(row.get('severity', ''))}"
    return display_label(row.get("degradation_family", case_id))


def case_sort_value(row: pd.Series) -> tuple[float, float, str]:
    """Provide stable visual ordering without changing scientific evidence."""

    case_id = str(row.get("case_id", ""))
    size = re.search(r"size_(\d+)pct", case_id)
    target = re.search(r"target_(\d+)(?:p(\d+))?pct", case_id)
    variant = re.search(r"variant_(\d+)", case_id)
    severity_order = {"mild": 1.0, "moderate": 2.0, "severe": 3.0}
    if size:
        return float(size.group(1)), 0.0, case_id
    if target:
        target_value = float(f"{target.group(1)}.{target.group(2) or '0'}")
        return target_value, float(variant.group(1)) if variant else 0.0, case_id
    return severity_order.get(str(row.get("severity", "")), 0.0), 0.0, case_id


def render_image_grid(
    rows: pd.DataFrame,
    *,
    path_field: str,
    label_field: str = "visual_label",
    max_columns: int = 4,
) -> None:
    """Render a responsive gallery from already-indexed image paths."""

    if rows.empty:
        st.info("No image is available for this exact evidence slice.")
        return
    records = list(rows.to_dict(orient="records"))
    for start in range(0, len(records), max_columns):
        group = records[start : start + max_columns]
        columns = st.columns(len(group))
        for column, record in zip(columns, group):
            with column:
                show_image(record.get(path_field), str(record.get(label_field, "Evidence")))


def summary_figure(
    bundle: DashboardBundle,
    *,
    page_id: str,
    map_type: str,
    caption: str,
) -> bool:
    """Render one exact Notebook 34 summary figure when it is indexed."""

    visuals = bundle.indexes["visual_asset_index"]
    rows = visuals[
        visuals["page_id"].eq(page_id)
        & visuals["asset_type"].eq("summary_figure")
        & visuals["map_type"].eq(map_type)
    ]
    if rows.empty:
        return False
    show_image(rows.iloc[0]["relative_path"], caption)
    return True


def render_experiment_walkthrough(
    bundle: DashboardBundle,
    *,
    experiment_id: str,
    key_prefix: str,
) -> None:
    """Translate an experiment contract into visible registered cases."""

    cases = bundle.indexes["case_index"].copy()
    cases = cases[cases["experiment_id"].eq(experiment_id)]
    if cases.empty:
        st.info("No registered cases are available for this experiment.")
        return

    evidence_note(
        "What changes",
        EXPERIMENT_EXPLANATIONS[experiment_id],
        "good",
    )

    controls = st.columns(3)
    with controls[0]:
        painting_id = select_one(
            "Painting",
            stable_options(cases, "painting_id"),
            key=f"{key_prefix}_painting",
        )
    selected = filter_frame(cases, painting_id=painting_id)

    if experiment_id == "mask_robustness":
        with controls[1]:
            damage = select_one(
                "Damage type",
                stable_options(selected, "degradation_family"),
                key=f"{key_prefix}_damage",
            )
        selected = filter_frame(selected, degradation_family=damage)
    elif experiment_id == "synthetic_degradation":
        with controls[1]:
            damage = select_one(
                "Degradation",
                stable_options(selected, "degradation_family"),
                key=f"{key_prefix}_degradation",
            )
        selected = filter_frame(selected, degradation_family=damage)
    else:
        controls[1].caption(
            "Damage condition is fixed by this experiment."
            if experiment_id == "damage_size_sensitivity"
            else "All canonical damage conditions are shown."
        )

    with controls[2]:
        layer = st.selectbox(
            "Visual layer",
            ["Damaged input", "Mask", "Restoration"],
            key=f"{key_prefix}_layer",
        )

    model_id = ""
    if layer == "Restoration":
        model_id = select_one(
            "Restoration model",
            stable_options(selected, "model_id"),
            key=f"{key_prefix}_model",
        )
        display_rows = filter_frame(selected, model_id=model_id)
        path_field = "restored_path"
    else:
        display_rows = selected
        path_field = "damaged_path" if layer == "Damaged input" else "mask_path"

    display_rows = display_rows.drop_duplicates("case_id", keep="first").copy()
    display_rows["sort_key"] = [case_sort_value(row) for _, row in display_rows.iterrows()]
    display_rows = display_rows.sort_values("sort_key", kind="stable").drop(columns="sort_key")
    display_rows["visual_label"] = [case_parameter_label(row) for _, row in display_rows.iterrows()]

    if experiment_id == "damage_size_sensitivity":
        st.caption("Seven registered levels: 2%, 4%, 6%, 8%, 10%, 15%, and 20%.")
    elif experiment_id == "mask_robustness":
        st.caption("Five placement variants are shown for the selected damage type and target size.")
    elif experiment_id == "synthetic_degradation":
        st.caption("Severity progression is shown for the selected degradation family.")
    else:
        st.caption("The five canonical conditions include the unchanged zero control.")

    render_image_grid(display_rows, path_field=path_field, max_columns=4)

    if display_rows.empty:
        return
    labels = {
        str(row.case_id): str(row.visual_label)
        for row in display_rows.itertuples(index=False)
    }
    selected_case_id = st.selectbox(
        "Inspect one condition in detail",
        list(labels),
        format_func=labels.get,
        key=f"{key_prefix}_detail_case",
    )
    detail_candidates = selected[selected["case_id"].eq(selected_case_id)]
    detail_models = stable_options(detail_candidates, "model_id")
    default_model = model_id if model_id in detail_models else (
        "lama" if "lama" in detail_models else detail_models[0]
    )
    detail_model = st.selectbox(
        "Detailed restoration model",
        detail_models,
        index=detail_models.index(default_model),
        format_func=model_name,
        key=f"{key_prefix}_detail_model",
    )
    row = detail_candidates[detail_candidates["model_id"].eq(detail_model)].iloc[0]
    detail = pd.DataFrame(
        [
            {"path": row["clean_path"], "label": "Original"},
            {"path": row["damaged_path"], "label": "Damaged input"},
            {"path": row["mask_path"], "label": "Mask"},
            {"path": row["restored_path"], "label": model_name(detail_model)},
        ]
    )
    render_image_grid(detail, path_field="path", label_field="label", max_columns=4)


def diagnostic_paths_for_metric(row: pd.Series, metric_family: str, region_id: str) -> list[Path]:
    """Select existing diagnostics that visually explain a metric-region choice."""

    paths = case_visual_paths(row, PROJECT_ROOT)
    if region_id in {"boundary_ring", "inner_boundary_band", "outer_boundary_band"}:
        keys = ["seam_paths_json", "mask_boundary_paths_json", "difference_paths_json"]
    else:
        family_keys = {
            "colour": ["colour_paths_json", "difference_paths_json"],
            "seam": ["seam_paths_json", "mask_boundary_paths_json"],
            "texture_map": ["texture_paths_json", "difference_paths_json"],
            "texture_descriptor": ["texture_paths_json", "difference_paths_json"],
            "spatial_diagnostics": ["difference_paths_json", "mask_boundary_paths_json"],
            "classical_pixel": ["difference_paths_json", "colour_paths_json"],
            "ssim": ["difference_paths_json", "semantic_paths_json"],
            "perceptual": ["difference_paths_json", "semantic_paths_json"],
            "feature_similarity": ["semantic_paths_json", "difference_paths_json"],
            "local_semantic_preservation": ["semantic_paths_json", "difference_paths_json"],
            "structural_layout": ["semantic_paths_json", "difference_paths_json"],
            "clip": ["semantic_paths_json", "difference_paths_json"],
            "dinov2": ["semantic_paths_json", "difference_paths_json"],
            "lpips": ["difference_paths_json", "semantic_paths_json"],
        }
        keys = family_keys.get(metric_family, ["difference_paths_json", "semantic_paths_json"])
    selected: list[Path] = []
    for key in keys:
        for path in paths.get(key, []):
            if path not in selected:
                selected.append(path)
    return selected


def metric_guidance(family: str) -> tuple[str, str, str]:
    """Return plain-language guidance for every selectable metric family."""

    return METRIC_FAMILY_GUIDANCE.get(
        family,
        (
            "This family records one complementary aspect of restoration evidence.",
            "Use the direction and approved region shown in the metric policy.",
            "Do not interpret one family as a complete restoration-quality verdict.",
        ),
    )


def render_performance_comparison(bundle: DashboardBundle) -> pd.Series | None:
    """Show any registered case with a user-selected restoration model."""

    cases = bundle.indexes["case_index"].copy()
    controls = st.columns(3)
    with controls[0]:
        experiment = select_one(
            "Example experiment",
            stable_options(cases, "experiment_id"),
            key="performance_example_experiment",
        )
    experiment_rows = filter_frame(cases, experiment_id=experiment)
    with controls[1]:
        painting = select_one(
            "Example painting",
            stable_options(experiment_rows, "painting_id"),
            key="performance_example_painting",
        )
    painting_rows = filter_frame(experiment_rows, painting_id=painting)
    case_ids = stable_options(painting_rows, "case_id")
    preferred = "canonical__p001__loss_large"
    default_index = case_ids.index(preferred) if preferred in case_ids else 0
    case_labels = {
        str(row.case_id): f"{display_label(row.degradation_family)} · {display_label(row.severity)}"
        for row in painting_rows.drop_duplicates("case_id").itertuples(index=False)
    }
    with controls[2]:
        case_id = st.selectbox(
            "Example case",
            case_ids,
            index=default_index,
            format_func=lambda item: case_labels.get(item, display_label(item)),
            key="performance_example_case",
        )

    group = painting_rows[painting_rows["case_id"].eq(case_id)].copy()
    model_ids = stable_options(group, "model_id")
    model_choice = st.selectbox(
        "Restoration model",
        ["all_models", *model_ids],
        format_func=lambda item: "All available models" if item == "all_models" else model_name(item),
        key="performance_example_model",
    )
    if model_choice == "all_models":
        restored_rows = group.sort_values(
            ["model_id", "prompt_variant_id", "candidate_id"], kind="stable"
        ).drop_duplicates("model_id", keep="first")
    else:
        model_rows = group[group["model_id"].eq(model_choice)].sort_values(
            ["prompt_variant_id", "candidate_id"], kind="stable"
        )
        candidate_ids = model_rows["candidate_id"].astype(str).tolist()
        candidate_id = st.selectbox(
            "Candidate / seed / prompt arm",
            candidate_ids,
            format_func=lambda item: (
                f"{item} · {display_label(model_rows.loc[model_rows['candidate_id'].eq(item), 'prompt_variant_id'].iloc[0])}"
            ),
            key="performance_example_candidate",
        )
        restored_rows = model_rows[model_rows["candidate_id"].eq(candidate_id)]

    first = group.iloc[0]
    context = pd.DataFrame(
        [
            {"path": first["clean_path"], "label": "Original reference"},
            {"path": first["damaged_path"], "label": "Damaged input"},
            {"path": first["mask_path"], "label": "Repair mask"},
        ]
    )
    render_image_grid(context, path_field="path", label_field="label", max_columns=3)
    restored_rows = restored_rows.copy()
    restored_rows["visual_label"] = [
        f"{model_name(row.model_id)} · {display_label(row.prompt_variant_id)}"
        if pd.notna(row.prompt_variant_id)
        and str(row.prompt_variant_id).strip()
        and str(row.prompt_variant_id).strip().casefold() != "nan"
        else model_name(row.model_id)
        for row in restored_rows.itertuples(index=False)
    ]
    render_image_grid(restored_rows, path_field="restored_path", max_columns=4)
    st.caption(
        f"{len(model_ids)} restoration model(s) are available for this case. "
        "All-model mode shows one indexed candidate per model; select a model to inspect its candidate, seed, or prompt arm."
    )
    return restored_rows.iloc[0] if not restored_rows.empty else None


def render_uncertainty_focus_panel(bundle: DashboardBundle) -> None:
    """Replace an unreadable multi-panel summary with one selectable explanation panel."""

    visuals = bundle.indexes["visual_asset_index"].copy()
    panels = visuals[
        visuals["page_id"].eq("robustness_uncertainty")
        & visuals["asset_type"].eq("selected_panel")
        & visuals["map_type"].isin(
            ["selected_median", "selected_boundary_concentration", "selected_prompt_difference"]
        )
    ].copy()
    if panels.empty:
        summary_figure(
            bundle,
            page_id="robustness_uncertainty",
            map_type="12_uncertainty_summary",
            caption="Validated repeated-seed uncertainty summary",
        )
        return

    panel_types = {
        "Typical uncertainty": "selected_median",
        "Boundary-concentrated uncertainty": "selected_boundary_concentration",
        "Generic vs scratch-aware prompt difference": "selected_prompt_difference",
    }
    panel_type = st.selectbox(
        "Focused uncertainty view",
        list(panel_types),
        key="robust_uncertainty_panel_type",
    )
    selected = panels[panels["map_type"].eq(panel_types[panel_type])].sort_values(
        ["painting_id", "case_id"], kind="stable"
    )
    labels = {
        str(row.visual_asset_id): (
            f"{row.painting_id} · {display_label(row.case_id)}"
        )
        for row in selected.itertuples(index=False)
    }
    visual_id = st.selectbox(
        "Focused example",
        list(labels),
        format_func=labels.get,
        key="robust_uncertainty_panel",
    )
    row = selected[selected["visual_asset_id"].eq(visual_id)].iloc[0]
    show_image(row["relative_path"], panel_type)


def render_visual_catalogue(bundle: DashboardBundle, *, key_prefix: str) -> None:
    """Expose every Notebook 34 visual record through lazy, exact filters."""

    visuals = bundle.indexes["visual_asset_index"].copy()
    filter_columns = st.columns(4)
    with filter_columns[0]:
        page_id = select_one(
            "Visual page",
            stable_options(visuals, "page_id"),
            key=f"{key_prefix}_visual_page",
            all_option=True,
        )
    page_rows = filter_frame(visuals, page_id=page_id)
    with filter_columns[1]:
        asset_type = select_one(
            "Asset type",
            stable_options(page_rows, "asset_type"),
            key=f"{key_prefix}_visual_type",
            all_option=True,
        )
    type_rows = filter_frame(page_rows, asset_type=asset_type)
    with filter_columns[2]:
        model_id = select_one(
            "Model",
            stable_options(type_rows, "model_id"),
            key=f"{key_prefix}_visual_model",
            all_option=True,
        )
    model_rows = filter_frame(type_rows, model_id=model_id)
    with filter_columns[3]:
        painting_id = select_one(
            "Painting",
            stable_options(model_rows, "painting_id"),
            key=f"{key_prefix}_visual_painting",
            all_option=True,
        )

    filtered = filter_frame(model_rows, painting_id=painting_id)
    candidate_query = st.text_input(
        "Optional candidate or case search",
        key=f"{key_prefix}_visual_search",
        placeholder="candidate ID or case ID",
    ).strip()
    if candidate_query:
        query = candidate_query.casefold()
        filtered = filtered[
            filtered["candidate_id"]
            .fillna("")
            .astype(str)
            .str.casefold()
            .str.contains(query, regex=False)
            | filtered["case_id"]
            .fillna("")
            .astype(str)
            .str.casefold()
            .str.contains(query, regex=False)
        ]

    st.caption(
        f"{len(filtered):,} of {len(visuals):,} indexed visual records match. "
        "Supporting prompt-ablation maps remain separate from the approved candidate index."
    )
    if filtered.empty:
        st.info("No visual record matches the selected filters.")
        return

    visual_ids = filtered["visual_asset_id"].astype(str).tolist()
    visual_labels = {
        str(row.visual_asset_id): (
            f"{row.asset_type} · {row.map_type} · {row.visual_asset_id}"
        )
        for row in filtered.itertuples(index=False)
    }
    selected_id = st.selectbox(
        "Visual record",
        visual_ids,
        format_func=visual_labels.get,
        key=f"{key_prefix}_visual_record",
    )
    row = filtered[filtered["visual_asset_id"] == selected_id].iloc[0]
    left, right = st.columns([1.25, 1])
    with left:
        path = safe_project_path(row["relative_path"], PROJECT_ROOT)
        if path is not None and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            show_image(
                path,
                f"{display_label(row['asset_type'])} · {display_label(row['map_type'])}",
            )
        elif path is not None:
            evidence_note(
                "Numeric visual bundle",
                "This record indexes a validated numeric map bundle. Use its path and producer metadata for reproducible downstream inspection.",
            )
            st.code(row["relative_path"])
        else:
            st.error("The selected indexed visual path is unavailable.")
    with right:
        metadata_fields = [
            "candidate_id",
            "case_id",
            "painting_id",
            "model_id",
            "experiment_id",
            "source_notebook_id",
            "asset_type",
            "map_type",
            "region_id",
            "selection_role",
            "applicability_status",
        ]
        st.dataframe(
            pd.DataFrame(
                {
                    "field": metadata_fields,
                    "value": [str(row.get(field, "")) for field in metadata_fields],
                }
            ),
            width="stretch",
            hide_index=True,
        )


def render_overview(bundle: DashboardBundle) -> None:
    page_header("Executive overview", "Trustworthy AI-Assisted Painting Restoration", "What does the complete evaluation support?")
    st.markdown(
        '<div class="thesis-strip"><span class="smallcaps">Thesis statement</span><br><strong>Visual plausibility is <em>not</em> the same as restoration trustworthiness.</strong></div>',
        unsafe_allow_html=True,
    )
    population = bundle.summary["population"]
    columns = st.columns(4)
    cards = [
        ("paintings", population["paintings"], "controlled collection"),
        ("restoration cases", population["restoration_cases"], "validated case population"),
        ("approved candidates", population["approved_candidates"], "complete filterable evidence"),
        ("SDXL cases", population["sdxl_candidates"], "bounded feasibility only"),
    ]
    for column, (label, value, unit) in zip(columns, cards):
        with column:
            paper_card(label, value, unit, "Study scope")
    findings = bundle.tables["headline_findings"].sort_values("display_order", kind="stable")
    st.subheader("What the evidence supports")
    finding_columns = st.columns(2)
    for index, (_, row) in enumerate(findings.iloc[2:7].iterrows()):
        tone_value = str(row.get("tone", "")).casefold()
        tone = "good" if tone_value in {"positive", "success"} else "danger" if tone_value in {"caution", "warning", "danger"} else ""
        with finding_columns[index % 2]:
            rich_evidence_note(
                row["title"],
                emphasize_evidence_text(row["conclusion"]),
                tone,
            )

    visual_column, reading_column = st.columns([1.55, 1])
    with visual_column:
        visuals = bundle.indexes["visual_asset_index"]
        overview = visuals[
            (visuals["page_id"] == "overview")
            & visuals["map_type"].eq("01_benchmark_summary")
        ]
        if overview.empty:
            overview = visuals[visuals["page_id"] == "overview"]
        if not overview.empty:
            show_image(overview.iloc[0]["relative_path"], "Validated thesis-level benchmark summary")
        else:
            representative_case(bundle, key_prefix="overview", compact=True)
        evidence_note(
            "Why both are shown",
            "Wins show how often a model leads; mean rank shows how consistently it performs across every anchor. Together they expose broad strength without hiding metric disagreement.",
        )
        evidence_note(
            "Reading boundary",
            "The bars summarize the three fully evaluated models. SDXL is excluded from this ranking because it has only ten bounded feasibility cases.",
            "danger",
        )
    with reading_column:
        st.subheader("How to read the comparison")
        rich_evidence_note(
            "Quality-anchor wins",
            "The count of the <strong>11 separate metric-region anchors</strong> on which a model ranks first. "
            "A higher count means broader benchmark leadership; it is <em>not</em> a combined quality score.",
            "good",
        )
        rich_evidence_note(
            "Mean anchor rank",
            "The model's average position across the same <strong>11 anchors</strong>. "
            "<strong>Lower is better</strong>: a mean rank near <strong>1</strong> means the model usually finishes first.",
        )
    st.markdown('<div class="caption-note">Evidence remains separated by metric family and region so disagreement stays visible.</div>', unsafe_allow_html=True)
    st.subheader("Three witnesses from the controlled collection")
    paintings = bundle.indexes["painting_index"].sort_values("dataset_sort_index", kind="stable")
    defaults = paintings[paintings["painting_id"].isin(["p001", "p018", "p043"])]
    if defaults.empty:
        defaults = paintings.head(3)
    columns = st.columns(len(defaults))
    for column, (_, row) in zip(columns, defaults.iterrows()):
        with column:
            show_image(row["raw_image_path"], f"{row['painting_id']} — {row['title']}")
            st.caption(f"{row['artist']} · {display_label(row['category'])}")
    evidence_note("Interpretation boundary", "Metrics are diagnostic evidence from controlled synthetic damage. They do not certify authenticity, historical correctness, or conservation approval.", "danger")


def render_study_design(bundle: DashboardBundle) -> None:
    page_header("Evidence architecture", "Study Design", "What was evaluated, and under which controlled conditions?")
    design = bundle.tables["study_design"].copy()
    experiment = select_one("Experiment", stable_options(design, "experiment_id"), key="design_exp")
    filtered = filter_frame(design, experiment_id=experiment)
    overview_rows = filtered[pd.to_numeric(filtered["value"], errors="coerce").notna()].copy()
    overview_rows["numeric_value"] = pd.to_numeric(overview_rows["value"], errors="coerce")
    columns = st.columns(4)
    for column, (_, row) in zip(columns, overview_rows.head(4).iterrows()):
        with column:
            paper_card(row["display_name"], float(row["numeric_value"]), row["value_unit"], display_label(row["section_id"]))
    left, right = st.columns([1.3, 1])
    with left:
        summary_figure(
            bundle,
            page_id="study_design",
            map_type="02_dataset_and_experiment_scope",
            caption="Validated dataset and experiment scope",
        )
    with right:
        st.subheader("Design rules")
        for text in filtered["interpretation"].dropna().astype(str).drop_duplicates().head(7):
            st.markdown(f"- {text}")
        evidence_note("Independent unit", "Paintings—not candidate rows—are the independent unit for grouped inference. Repeated seeds and model outputs remain nested evidence.", "good")

    st.subheader("See the experimental variable")
    render_experiment_walkthrough(
        bundle,
        experiment_id=experiment,
        key_prefix="study_walkthrough",
    )

    st.subheader("Collection composition")
    paintings = bundle.indexes["painting_index"].copy()
    categories = paintings.groupby("category", as_index=False).agg(paintings=("painting_id", "nunique"))
    categories = categories.sort_values("category", kind="stable")
    c1, c2 = st.columns([1, 1.7])
    with c1:
        fig = px.bar(categories, x="paintings", y="category", orientation="h", color="category", color_discrete_sequence=[PALETTE["green"], PALETTE["sage"], PALETTE["ochre"], PALETTE["umber"], PALETTE["vermilion"]], title="Paintings per visual category")
        fig.update_layout(showlegend=False)
        fig.update_yaxes(title_text="", ticktext=[display_label(value) for value in categories["category"]], tickvals=categories["category"])
        fig.update_xaxes(title_text="Paintings", dtick=2)
        st.plotly_chart(styled_figure(fig, height=330), width="stretch")
    with c2:
        category = select_one(
            "Inspect a visual category",
            stable_options(paintings, "category"),
            key="design_category",
        )
        sample = paintings[paintings["category"].eq(category)].head(4).copy()
        sample["visual_label"] = sample["painting_id"].astype(str) + " · " + sample["title"].astype(str)
        render_image_grid(sample, path_field="raw_image_path", max_columns=4)
    with st.expander("Complete 50-painting collection metadata"):
        visible = paintings[["painting_id", "title", "artist", "date_or_period", "category", "case_count", "candidate_count"]]
        st.dataframe(visible, width="stretch", hide_index=True, height=355)
    evidence_note("Scope", "The balanced 50-painting collection improves controlled comparison. It does not by itself establish performance on real damaged paintings or unseen conservation contexts.")


def render_metric_framework(bundle: DashboardBundle) -> None:
    page_header("Evidence, not a single score", "Metric Framework", "Why do regions and metric families change the conclusion?")
    framework = bundle.tables["metric_framework"].copy()
    anchors = framework[framework["record_type"] == "quality_anchor"].sort_values("display_order", kind="stable")
    columns = st.columns(3)
    cards = [("quality anchors", int(len(anchors)), "kept separate"), ("metric families", int(framework["metric_family"].replace("", pd.NA).nunique()), "complementary evidence"), ("canonical regions", int(framework["region_id"].replace("", pd.NA).nunique()), "valid spatial scopes")]
    for column, item in zip(columns, cards):
        with column:
            paper_card(*item, eyebrow="Metric policy")
    controls = st.columns(2)
    with controls[0]:
        family = select_one("Metric family", stable_options(framework, "metric_family"), key="metric_family")
    family_rows = filter_frame(framework, metric_family=family)
    region_options = stable_options(family_rows, "region_id")
    preferred_regions = stable_options(
        anchors[anchors["metric_family"].eq(family)],
        "region_id",
    )
    if preferred_regions and preferred_regions[0] in region_options:
        region_options = [preferred_regions[0]] + [
            item for item in region_options if item != preferred_regions[0]
        ]
    with controls[1]:
        region = select_one("Region to explain and visualize", region_options, key="metric_region")
    st.caption(
        "The region control is also the image selector: changing it updates the region definition, "
        "approved-policy statement, and the indexed diagnostic images below."
    )
    filtered = filter_frame(framework, metric_family=family, region_id=region)
    left, right = st.columns([1.3, 1])
    with left:
        compatible = framework[framework["record_type"] == "region_policy"].copy()
        family_policy = compatible[compatible["metric_family"].eq(family)].copy()
        approved_regions = family_policy[family_policy["compatible"].map(truthy)]["region_id"].dropna().astype(str).drop_duplicates().tolist()
        st.subheader(f"Approved regions for {display_label(family)}")
        chips = " ".join(
            f'<span class="status-chip good">{esc(display_label(item))}</span>'
            for item in approved_regions
        )
        st.markdown(chips or '<span class="status-chip warn">No compatible region recorded</span>', unsafe_allow_html=True)
        selected_policy = family_policy[family_policy["region_id"].eq(region)]
        selected_is_compatible = bool(
            not selected_policy.empty
            and selected_policy["compatible"].map(truthy).any()
        )
        evidence_note(
            "Selected spatial scope",
            f"{display_label(region)} is {'approved' if selected_is_compatible else 'not approved'} for {display_label(family)}. "
            "The mask and diagnostic images below show where that scope sits in an actual restoration.",
            "good" if selected_is_compatible else "danger",
        )
        region_rows = framework[
            framework["record_type"].eq("region_summary")
            & framework["region_id"].eq(region)
        ]
        if not region_rows.empty:
            region_row = region_rows.iloc[0]
            evidence_note(
                f"What {display_label(region)} means",
                str(region_row["interpretation"]),
            )
    with right:
        st.subheader("What this metric family measures")
        definition, reading, limitation = metric_guidance(family)
        evidence_note("Definition", definition, "good")
        evidence_note("How to interpret it", reading)
        evidence_note("What it cannot establish", limitation, "danger")
        selected_anchors = filter_frame(anchors, metric_family=family, region_id=region)
        if selected_anchors.empty:
            policy_rows = filtered[filtered["record_type"].eq("region_policy")]
            policy_text = (
                str(policy_rows.iloc[0]["interpretation"])
                if not policy_rows.empty
                else "This metric-region combination is retained as policy evidence."
            )
            evidence_note(
                "Metric-region policy",
                policy_text,
            )
        else:
            for _, row in selected_anchors.head(4).iterrows():
                direction = "lower is better" if row["comparison_direction"] == "lower_is_better" else "higher is better"
                rich_evidence_note(
                    f"Headline anchor · {display_label(row['metric_name'])}",
                    f"{esc(row['interpretation'])} <strong>Direction: {esc(direction)}.</strong>",
                )

    st.subheader("Translate the selected metric and region into images")
    cases = default_case_rows(bundle.indexes["case_index"])
    case_models = st.columns(2)
    with case_models[0]:
        visual_model = select_one(
            "Example model",
            stable_options(cases, "model_id"),
            key="metric_visual_model",
        )
    model_cases = filter_frame(cases, model_id=visual_model)
    labels = {
        str(row.candidate_id): (
            f"{row.painting_id} · {display_label(row.degradation_family)} · "
            f"{model_name(row.model_id)}"
        )
        for row in model_cases.itertuples(index=False)
    }
    with case_models[1]:
        candidate_id = st.selectbox(
            "Visual example",
            list(labels),
            format_func=labels.get,
            key="metric_visual_candidate",
        )
    row = model_cases[model_cases["candidate_id"].eq(candidate_id)].iloc[0]
    primary = pd.DataFrame(
        [
            {"path": row["clean_path"], "label": "Original reference"},
            {"path": row["mask_path"], "label": "Repair mask · white pixels are repaired"},
            {"path": row["restored_path"], "label": f"Restored · {model_name(visual_model)}"},
        ]
    )
    render_image_grid(primary, path_field="path", label_field="label", max_columns=3)
    diagnostics = diagnostic_paths_for_metric(row, family, region)
    if diagnostics:
        diagnostic_labels = [
            display_label(path.stem) for path in diagnostics
        ]
        selected_diagnostic = st.selectbox(
            "Image explaining the selected region",
            list(range(len(diagnostics))),
            format_func=lambda index: diagnostic_labels[index],
            key=f"metric_region_image_{family}_{region}",
        )
        show_image(
            diagnostics[selected_diagnostic],
            f"{display_label(region)} · {diagnostic_labels[selected_diagnostic]}",
        )
        with st.expander("Show every relevant diagnostic for this region"):
            show_paths(diagnostics, max_items=4)
    else:
        st.caption("No dedicated diagnostic image is indexed for this exact family; compare the reference, mask, and restoration directly.")
    evidence_note(
        "How the region appears here",
        f"The mask identifies the repair geometry. The diagnostic image(s) below emphasize the evidence relevant to {display_label(region)}: "
        f"{str(region_rows.iloc[0]['interpretation']) if not region_rows.empty else 'the selected approved spatial scope.'} "
        "Changing the Region control changes both this explanation and the most relevant indexed diagnostics.",
        "good",
    )
    evidence_note("Central rule", "Metric disagreement is a finding to inspect, not noise to hide inside a universal score.", "danger")

    with st.expander("Complete metric and region policy evidence"):
        shown = ["record_type", "metric_family", "metric_name", "region_id", "compatible", "comparison_direction", "interpretation", "limitation"]
        st.dataframe(filtered[shown].head(500), width="stretch", hide_index=True, height=360)


def render_model_performance(bundle: DashboardBundle) -> None:
    page_header("Conditional comparison", "Model Performance", "Which model performs better, under which conditions, and by what evidence?")
    performance = bundle.tables["performance_summary"].copy()
    core = performance[performance["population_id"].eq("core_three_model")].copy()
    compute = bundle.tables["compute_summary"]
    framework = bundle.tables["metric_framework"]
    columns = st.columns(4)
    card_rows = [("strongest general baseline", "LaMa", "10 of 11 quality anchors"), ("fast deterministic baseline", "Telea", "observed compute evidence"), ("most seed-variable model", "Stable Diffusion", "empirical variability"), ("bounded feasibility model", "SDXL", "10 cases only")]
    for column, row in zip(columns, card_rows):
        with column:
            paper_card(row[0], row[1], row[2], "Decision cue")

    controls = st.columns(3)
    scopes = stable_options(core, "analysis_scope")
    if "overall" in scopes:
        scopes = ["overall", *[item for item in scopes if item != "overall"]]
    with controls[0]:
        analysis_scope = select_one("Comparison scope", scopes, key="perf_scope")
    scoped = core[core["analysis_scope"].eq(analysis_scope)].copy()
    scope_values = stable_options(scoped, "scope_value")
    with controls[1]:
        if analysis_scope == "overall" or len(scope_values) <= 1:
            scope_value = scope_values[0] if scope_values else "all"
            st.caption(f"Condition: {display_label(scope_value)}")
        else:
            scope_value = select_one("Condition", scope_values, key="perf_condition")
    scoped = scoped[scoped["scope_value"].astype(str).eq(str(scope_value))]
    with controls[2]:
        metric = select_one("Metric", stable_options(scoped, "metric_name"), key="perf_metric")
    metric_rows = scoped[scoped["metric_name"].eq(metric)].copy()
    for source, target in (("estimate", "estimate_numeric"), ("interval_low", "low_numeric"), ("interval_high", "high_numeric")):
        metric_rows[target] = pd.to_numeric(metric_rows[source], errors="coerce")
    left, right = st.columns([1.35, 1])
    with left:
        if not metric_rows.empty:
            metric_rows["error_plus"] = (metric_rows["high_numeric"] - metric_rows["estimate_numeric"]).clip(lower=0)
            condition_label = "overall benchmark" if analysis_scope == "overall" else display_label(scope_value)
            fig = px.bar(metric_rows, x="estimate_numeric", y="model_id", orientation="h", color="model_id", color_discrete_map=MODEL_COLOURS, error_x="error_plus", title=f"{display_label(metric)} · {condition_label}", hover_data=["region_id", "comparison_direction", "rank", "case_count", "painting_count"])
            fig.update_yaxes(ticktext=[model_name(v) for v in metric_rows["model_id"]], tickvals=metric_rows["model_id"])
            fig.update_layout(showlegend=False)
            st.plotly_chart(styled_figure(fig, height=330), width="stretch")
    with right:
        st.subheader("How to read this metric")
        metric_policy = framework[
            framework["record_type"].eq("quality_anchor")
            & framework["metric_name"].eq(metric)
        ]
        if not metric_policy.empty:
            policy = metric_policy.iloc[0]
            direction = "lower is better" if policy["comparison_direction"] == "lower_is_better" else "higher is better"
            rich_evidence_note(
                f"{display_label(metric)} · {display_label(policy['region_id'])}",
                f"{esc(policy['interpretation'])} <strong>{esc(direction.capitalize())}.</strong>",
                "good",
            )
            evidence_note("Limit", str(policy["limitation"]), "danger")
        if not metric_rows.empty:
            best = metric_rows.sort_values("rank", kind="stable").iloc[0]
            rich_evidence_note(
                "Result for this slice",
                f"<strong><em>{esc(model_name(best['model_id']))}</em></strong> ranks first for "
                f"<strong>{esc(display_label(metric))}</strong> under <strong>{esc(display_label(scope_value))}</strong>. "
                "This is a conditional result, not universal model superiority.",
                "good",
            )
        st.caption("The interval bars show the stored uncertainty interval for the declared grouped summary; paintings, not candidate rows, are the independent unit.")

    with st.expander("Exact numerical values behind this plot"):
        numeric = aggregate_metric_records(metric_rows)
        st.caption(
            "The same stored estimates and intervals used by the plot—not per-painting scores. "
            "Case and painting counts show the actual denominator. Candidates and seeds are not independent paintings."
        )
        st.dataframe(numeric, hide_index=True, width="stretch")
        st.download_button("Download plotted metric values (CSV)", numeric.to_csv(index=False).encode("utf-8"),
                           file_name="model_performance_values.csv", mime="text/csv", key="performance_numeric_download")

    st.subheader("Inspect the restorations behind the comparison")
    example_row = render_performance_comparison(bundle)
    if example_row is not None and not metric_policy.empty:
        policy = metric_policy.iloc[0]
        diagnostic_paths = diagnostic_paths_for_metric(
            example_row,
            str(policy["metric_family"]),
            str(policy["region_id"]),
        )
        with st.expander(f"See {display_label(metric)} diagnostics for this example"):
            st.caption(
                f"These existing diagnostic images help connect {display_label(metric)} to "
                f"the {display_label(policy['region_id'])} evidence it summarizes."
            )
            show_paths(diagnostic_paths, max_items=4)

    st.subheader("Why model coverage differs")
    cases = bundle.indexes["case_index"]
    model_order = ["lama", "opencv_telea", "stable_diffusion_inpainting", "sdxl_inpainting"]
    experiment_order = [
        "canonical_missing_region",
        "damage_size_sensitivity",
        "mask_robustness",
        "synthetic_degradation",
    ]
    coverage = (
        cases.groupby(["experiment_id", "model_id"], as_index=False)
        .agg(
            cases=("case_id", "nunique"),
            candidates=("candidate_id", "nunique"),
            paintings=("painting_id", "nunique"),
        )
    )
    complete_grid = pd.MultiIndex.from_product(
        [experiment_order, model_order],
        names=["experiment_id", "model_id"],
    ).to_frame(index=False)
    coverage = complete_grid.merge(coverage, on=["experiment_id", "model_id"], how="left").fillna(0)
    expected_cases = coverage.groupby("experiment_id")["cases"].transform("max")
    coverage["coverage_status"] = [
        "Full experiment coverage"
        if row.cases == expected and row.cases > 0
        else "Bounded feasibility subset"
        if row.cases > 0
        else "Not evaluated in this experiment"
        for row, expected in zip(coverage.itertuples(index=False), expected_cases)
    ]
    coverage["experiment"] = coverage["experiment_id"].map(display_label)
    coverage["model"] = coverage["model_id"].map(model_name)
    coverage["cases"] = coverage["cases"].astype(int)
    coverage["candidates"] = coverage["candidates"].astype(int)
    coverage["paintings"] = coverage["paintings"].astype(int)
    st.dataframe(
        coverage[["experiment", "model", "cases", "candidates", "paintings", "coverage_status"]],
        width="stretch",
        hide_index=True,
        height=390,
    )
    explanation_columns = st.columns(3)
    with explanation_columns[0]:
        evidence_note(
            "Core models",
            "LaMa, OpenCV Telea, and Stable Diffusion cover every registered case in all four experiments. Stable Diffusion has extra candidates where repeated seeds or prompt arms were required.",
            "good",
        )
    with explanation_columns[1]:
        evidence_note(
            "Synthetic degradation",
            "This experiment is not Telea-only: LaMa, Telea, and Stable Diffusion each cover 50 cases. SDXL contributes six deliberately bounded cases.",
        )
    with explanation_columns[2]:
        evidence_note(
            "Why SDXL is absent elsewhere",
            "SDXL was retained as a ten-case runtime-feasibility study: four canonical and six synthetic cases. It was not expanded into the damage-size or mask-robustness experiments and must not be read as a fourth full benchmark.",
            "danger",
        )
    evidence_note(
        "Uncertainty applicability",
        "Repeated-seed uncertainty is reported for Stable Diffusion. LaMa and Telea are deterministic baselines, while SDXL has only one seed per case; those methods are therefore not assigned artificial uncertainty values.",
    )
    with st.expander("Observed runtime and bounded scaling evidence"):
        shown = compute[["display_name", "record_type", "scenario_id", "experiment_id", "runtime_seconds", "is_executed", "is_projected", "projection_basis", "interpretation"]]
        st.dataframe(shown, width="stretch", hide_index=True, height=340)


def render_robustness_uncertainty(bundle: DashboardBundle) -> None:
    page_header("Dependability under change", "Robustness & Uncertainty", "Where do restoration results become less dependable?")
    sensitivity = bundle.tables["sensitivity_summary"].copy()
    uncertainty = bundle.tables["uncertainty_summary"].copy()
    columns = st.columns(4)
    cards = [("canonical groups", bundle.summary["population"]["canonical_uncertainty_groups"], "four-seed Stable Diffusion"), ("damage-size groups", bundle.summary["population"]["damage_size_uncertainty_groups"], "extension evidence"), ("calibrated confidence", 0, "not claimed"), ("deterministic baselines", 2, "robustness, not uncertainty")]
    for column, item in zip(columns, cards):
        with column:
            paper_card(*item, eyebrow="Applicability")

    view_labels = {
        "Damage-size sensitivity": ("damage_size_sensitivity", "06_damage_size_sensitivity"),
        "Mask-placement robustness": ("mask_robustness", "07_mask_robustness"),
        "Synthetic-degradation sensitivity": ("synthetic_degradation", "08_synthetic_degradation"),
        "Repeated-seed uncertainty": ("repeated_seed_uncertainty", "13_spatial_uncertainty_explanations"),
    }
    view = st.selectbox("Evidence view", list(view_labels), key="robust_view")
    analysis, figure_type = view_labels[view]
    figure_column, meaning_column = st.columns([1.45, 1])
    with figure_column:
        if analysis == "repeated_seed_uncertainty":
            render_uncertainty_focus_panel(bundle)
        else:
            summary_figure(
                bundle,
                page_id="robustness_uncertainty",
                map_type=figure_type,
                caption=f"Validated {view.lower()} summary",
            )
    with meaning_column:
        st.subheader("What this test changes")
        if analysis == "damage_size_sensitivity":
            evidence_note("Controlled change", "Damage extent increases from 2% to 20% while the painting and large-loss family remain fixed.", "good")
            evidence_note("Interpretation", "A steep quality change means the model is sensitive to how much content is missing; it does not by itself identify why the repair failed.")
        elif analysis == "mask_robustness":
            evidence_note("Controlled change", "Five placements change mask geometry while painting, damage family, and target fraction remain fixed.", "good")
            evidence_note("Interpretation", "Large variation across placements means the method depends strongly on where the damage occurs.")
        elif analysis == "synthetic_degradation":
            evidence_note("Controlled change", "Degradation family and severity change over the same five-painting extension cohort.", "good")
            evidence_note("Interpretation", "This tests response to stains, dirt, and transparency effects; it is descriptive evidence from five paintings, not a population-wide style effect.")
        else:
            evidence_note("Controlled change", "Four Stable Diffusion seeds are compared within the same case and prompt arm.", "good")
            evidence_note("How to read the focused panel", "Compare the restored candidates with the uncertainty map and boundary evidence. Brighter or stronger map responses mark places where the four seeds disagree more.")
            evidence_note("Interpretation", "Higher variation means candidates agree less with one another. Low variation can still describe four consistently wrong restorations.", "danger")

    st.subheader("See the change in paintings")
    if analysis in EXPERIMENT_EXPLANATIONS:
        render_experiment_walkthrough(
            bundle,
            experiment_id=analysis,
            key_prefix="robust_walkthrough",
        )
    else:
        uncertainty_cases = bundle.indexes["case_index"].copy()
        uncertainty_cases = uncertainty_cases[
            uncertainty_cases["uncertainty_group_id"].fillna("").astype(str).ne("")
            & uncertainty_cases["uncertainty_applicability"].eq(
                "applicable_complete_repeated_seed_group"
            )
        ]
        group_labels = {
            str(row.uncertainty_group_id): (
                f"{row.painting_id} · {display_label(row.degradation_family)} · "
                f"{display_label(row.prompt_variant_id)}"
            )
            for row in uncertainty_cases.drop_duplicates("uncertainty_group_id").itertuples(index=False)
        }
        selected_group = st.selectbox(
            "Uncertainty group",
            list(group_labels),
            format_func=group_labels.get,
            key="robust_uncertainty_group",
        )
        group = uncertainty_cases[uncertainty_cases["uncertainty_group_id"].eq(selected_group)].copy()
        group = group.sort_values("candidate_id", kind="stable")
        group["visual_label"] = [f"Seed candidate {index}" for index in range(1, len(group) + 1)]
        render_image_grid(group, path_field="restored_path", max_columns=4)
        paths = case_visual_paths(group.iloc[0], PROJECT_ROOT)
        st.caption("The restorations show candidate-to-candidate variation; the maps localize where that variation occurs.")
        show_paths(paths["uncertainty_paths_json"], max_items=4)
        with st.expander("Complete multi-panel uncertainty summary"):
            st.caption("This dense figure is retained for completeness; use the focused panel above for ordinary reading.")
            summary_figure(
                bundle,
                page_id="robustness_uncertainty",
                map_type="13_spatial_uncertainty_explanations",
                caption="Complete validated spatial-uncertainty explanation figure",
            )

    with st.expander("Inspect the underlying validated numeric records"):
        if analysis == "repeated_seed_uncertainty":
            u_metric = select_one("Uncertainty measure", stable_options(uncertainty, "metric_name"), key="unc_metric")
            u_region = select_one("Region", stable_options(uncertainty[uncertainty["metric_name"] == u_metric], "region_id"), key="unc_region", all_option=True)
            detailed = filter_frame(uncertainty, metric_name=u_metric, region_id=u_region)
            st.dataframe(detailed.head(500), width="stretch", hide_index=True, height=360)
        else:
            detailed = sensitivity[sensitivity["analysis_family"].eq(analysis)].copy()
            models = stable_options(detailed, "model_id")
            model = select_one("Model", models, key="robust_detail_model", all_option=True)
            detailed = filter_frame(detailed, model_id=model)
            shown = ["analysis_kind", "condition_value", "metric_name", "region_id", "model_id", "estimate", "interval_low", "interval_high", "n_paintings", "applicability_status", "interpretation"]
            st.dataframe(detailed[shown].head(500), width="stretch", hide_index=True, height=360)
    evidence_note("Uncertainty limit", "Repeated-seed variation is empirical diffusion uncertainty, not calibrated confidence. Mask-placement and degradation changes are robustness or sensitivity evidence, not uncertainty.", "danger")


def render_trustworthiness_xai(bundle: DashboardBundle) -> None:
    page_header("Evidence behind every warning", "Trustworthiness & XAI", "Why was a candidate flagged, and what evidence supports review?")
    trust = bundle.tables["trustworthiness_summary"].copy()
    recommendations = trust[trust["record_type"] == "recommendation_summary"].copy()
    columns = st.columns(min(4, max(1, len(recommendations))))
    for column, (_, row) in zip(columns, recommendations.head(4).iterrows()):
        with column:
            paper_card(display_label(row["recommendation_category"]), float(row["value"]), row["value_unit"], "Review guidance")
    left, right = st.columns([1.25, 1])
    with left:
        failures = trust[trust["record_type"] == "failure_assignment_summary"].copy()
        failures["value_numeric"] = pd.to_numeric(failures["value"], errors="coerce")
        top = failures.dropna(subset=["value_numeric"]).sort_values("value_numeric", ascending=False).head(18)
        if not top.empty:
            fig = px.bar(top, x="value_numeric", y="display_name", color="model_id", color_discrete_map=MODEL_COLOURS, orientation="h", title="Most frequent computational failure assignments", hover_data=["model_id", "recommended_action", "limitation"])
            st.plotly_chart(styled_figure(fig, height=520), width="stretch")
    with right:
        st.subheader("How to use a flag")
        evidence_note("1 · Locate", "Use the flag to find the affected candidate, region, and metric evidence.")
        evidence_note("2 · Compare", "Inspect the restoration beside the original, damaged input, mask, and local diagnostic maps.")
        evidence_note("3 · Escalate", "Treat conservative review guidance as a reason for human inspection, not an automated verdict.", "good")
        evidence_note("Do not infer", "A computational flag is neither expert ground truth nor evidence of historical authenticity.", "danger")
    st.subheader("Visual explanation unit")
    st.caption(
        "The cards and failure-frequency chart above describe the complete approved population. "
        "The controls below filter the candidate, restoration, flags, and every diagnostic tab together."
    )
    cases = bundle.indexes["case_index"].copy()
    review_lanes = {
        "All outcomes": None,
        "Best available · preliminary inspection": "suitable_for_preliminary_inspection",
        "Specialist review required": "specialist_review_required",
        "Do not rely automatically": "do_not_rely_automatically",
        "Unstable candidates": "unstable_candidate",
    }
    filters = st.columns(3)
    with filters[0]:
        review_lane = st.selectbox("Review lane", list(review_lanes), key="xai_review_lane")
    selected_cases = cases
    category = review_lanes[review_lane]
    if category is not None:
        selected_cases = selected_cases[selected_cases["recommendation_category"].eq(category)]
    with filters[1]:
        selected_model = select_one(
            "Model",
            stable_options(selected_cases, "model_id"),
            key="xai_model",
            all_option=True,
        )
    selected_cases = filter_frame(selected_cases, model_id=selected_model)
    with filters[2]:
        selected_painting = select_one(
            "Painting",
            stable_options(selected_cases, "painting_id"),
            key="xai_painting",
            all_option=True,
        )
    selected_cases = filter_frame(selected_cases, painting_id=selected_painting)
    if selected_cases.empty:
        st.info("No candidate matches this review lane and filter combination.")
        return
    st.caption(
        f"{len(selected_cases):,} candidate(s) match the review lane, model, and painting filters. "
        "The candidate selector and every diagnostic tab below use this same filtered set."
    )
    candidate_labels = {
        str(row.candidate_id): (
            f"{row.painting_id} · {model_name(row.model_id)} · "
            f"{display_label(row.degradation_family)}"
        )
        for row in selected_cases.itertuples(index=False)
    }
    candidate_id = st.selectbox(
        "Candidate",
        list(candidate_labels),
        format_func=candidate_labels.get,
        key="xai_candidate",
    )
    row = selected_cases[selected_cases["candidate_id"] == candidate_id].iloc[0]
    if category == "suitable_for_preliminary_inspection":
        evidence_note(
            "Best available lane",
            "These candidates triggered no manual-review requirement under the operational rules. This means they are the strongest candidates for preliminary inspection—not approved conservation treatments or proof of correctness.",
            "good",
        )
    primary, diagnostics = st.columns([1, 2])
    with primary:
        show_image(row["restored_path"], f"Restored · {model_name(row['model_id'])}")
        chips = " ".join(f'<span class="status-chip danger">{esc(display_label(item))}</span>' for item in json_list(row["triggered_flag_ids_json"]))
        st.markdown(chips or '<span class="status-chip good">No triggered flag IDs</span>', unsafe_allow_html=True)
        st.caption(str(row["recommended_actions_json"]))
    with diagnostics:
        paths = case_visual_paths(row, PROJECT_ROOT)
        tabs = st.tabs(["Difference", "Seam", "Colour", "Texture", "Semantic", "Uncertainty"])
        keys = ["difference_paths_json", "seam_paths_json", "colour_paths_json", "texture_paths_json", "semantic_paths_json", "uncertainty_paths_json"]
        for tab, key in zip(tabs, keys):
            with tab:
                show_paths(paths[key], max_items=3)

    with st.expander("Complete indexed visual catalogue — all 23,964 records"):
        render_visual_catalogue(bundle, key_prefix="xai")


def render_case_explorer(bundle: DashboardBundle) -> None:
    page_header("Candidate-level evidence", "Case Explorer", "What evidence supports an individual restoration conclusion?")
    cases = bundle.indexes["case_index"].copy()
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        painting = select_one("Painting", stable_options(cases, "painting_id"), key="case_painting")
    painting_rows = filter_frame(cases, painting_id=painting)
    with f2:
        experiment = select_one("Experiment", stable_options(painting_rows, "experiment_id"), key="case_experiment", all_option=True)
    experiment_rows = filter_frame(painting_rows, experiment_id=experiment)
    with f3:
        damage = select_one("Damage", stable_options(experiment_rows, "degradation_family"), key="case_damage", all_option=True)
    damage_rows = filter_frame(experiment_rows, degradation_family=damage)
    with f4:
        model = select_one("Model", stable_options(damage_rows, "model_id"), key="case_model", all_option=True)
    filtered = filter_frame(damage_rows, model_id=model)
    if filtered.empty:
        st.warning("No candidate matches this exact filter combination.")
        return
    candidate = st.selectbox("Candidate record", filtered["candidate_id"].astype(str).tolist(), format_func=lambda item: f"{item} · {model_name(filtered.loc[filtered['candidate_id'] == item, 'model_id'].iloc[0])}", key="case_candidate")
    row = filtered[filtered["candidate_id"] == candidate].iloc[0]
    st.markdown(f'<span class="status-chip good">{esc(row["evidence_coverage_status"])}</span><span class="status-chip warn">{esc(display_label(row["recommendation_category"]))}</span><span class="status-chip">{esc(row["uncertainty_applicability"])}</span>', unsafe_allow_html=True)
    paths = case_visual_paths(row, PROJECT_ROOT)
    labels = [("clean_path", "Original"), ("damaged_path", "Damaged"), ("mask_path", "Mask"), ("restored_path", model_name(row["model_id"]))]
    columns = st.columns(4)
    for column, (field, caption) in zip(columns, labels):
        with column:
            show_image(row[field], caption)
    tabs = st.tabs(["Difference maps", "Boundary & seam", "Colour", "Texture", "Semantic", "Uncertainty"])
    tab_paths = [paths["difference_paths_json"], paths["seam_paths_json"] + paths["mask_boundary_paths_json"], paths["colour_paths_json"], paths["texture_paths_json"], paths["semantic_paths_json"], paths["uncertainty_paths_json"]]
    for tab, items in zip(tabs, tab_paths):
        with tab:
            show_paths(items, max_items=4)
    render_case_numeric_metrics(bundle, row)
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("All candidates in this filtered case set")
        visible = filtered[["candidate_id", "case_id", "model_id", "prompt_variant_id", "recommendation_category", "manual_review_required", "uncertainty_applicability", "scope_status"]]
        st.dataframe(visible, width="stretch", hide_index=True, height=310)
    with right:
        st.subheader("Provenance & reproducibility")
        st.markdown(f"- **Case:** `{row['case_id']}`")
        st.markdown(f"- **Painting:** `{row['painting_id']}`")
        st.markdown(f"- **Experiment:** `{row['experiment_id']}`")
        st.markdown(f"- **Model:** `{row['model_id']}`")
        st.markdown(f"- **Evidence notebooks:** {', '.join(json_list(row['evidence_source_notebook_ids_json']))}")
        st.markdown(f"- **Scope:** {row['scope_note']}")
        payload = report_bytes(row.get("case_report_path"), PROJECT_ROOT)
        if payload:
            data, filename = payload
            st.download_button("Download self-contained case report", data=data, file_name=filename, mime="text/html")
        painting_payload = report_bytes(row.get("painting_report_path"), PROJECT_ROOT)
        if painting_payload:
            data, filename = painting_payload
            st.download_button("Download self-contained painting report", data=data, file_name=filename, mime="text/html")


def render_reports(bundle: DashboardBundle) -> None:
    page_header("Traceable evidence", "Reports & Reproducibility", "Can each conclusion be traced to validated evidence?")
    reports = bundle.indexes["report_index"].copy()
    columns = st.columns(4)
    cards = [("reports", len(reports), "indexed and downloadable"), ("self-contained", int(reports["self_contained"].map(truthy).sum()), "portable report files"), ("source notebooks", int(reports["source_notebook_id"].nunique()), "traceable producers"), ("N34 validation checks", len(bundle.upstream_checks), "zero blocking failures")]
    for column, item in zip(columns, cards):
        with column:
            paper_card(*item, eyebrow="Reproducibility")
    st.subheader("How to find the right evidence")
    guide = st.columns(3)
    with guide[0]:
        evidence_note(
            "Thesis and analysis reports",
            "Use Final or Analysis for cross-model conclusions, sensitivity findings, uncertainty, statistics, limitations, and the complete evaluation narrative.",
            "good",
        )
    with guide[1]:
        evidence_note(
            "Model and method reports",
            "Use Model for one model's evidence and caveats. Use Method for protocols, metric definitions, and reproducible analytical procedures.",
        )
    with guide[2]:
        evidence_note(
            "Case and painting reports",
            "Use Case for one restoration situation and Painting for all indexed evidence attached to one artwork. These are the quickest routes from a claim back to images.",
        )
    st.caption("Choose a report family first, optionally narrow by model, then select and download the self-contained report. Downloaded HTML reports retain their embedded images.")
    family = select_one("Report family", stable_options(reports, "report_family"), key="report_family", all_option=True)
    model = select_one("Model", stable_options(reports, "model_id"), key="report_model", all_option=True)
    filtered = filter_frame(reports, report_family=family, model_id=model).sort_values("display_order", kind="stable")
    left, right = st.columns([1.4, 1])
    with left:
        st.subheader("Report catalogue")
        visible = filtered[["title", "report_family", "report_role", "model_id", "case_id", "painting_id", "self_contained", "size_bytes", "source_notebook_id", "applicability_status"]]
        st.dataframe(visible, width="stretch", hide_index=True, height=440)
    with right:
        st.subheader("Download one report")
        if filtered.empty:
            st.info("No report matches the selected filters.")
        else:
            options = filtered["dashboard_report_id"].astype(str).tolist()
            report_id = st.selectbox("Report", options, format_func=lambda item: filtered.loc[filtered["dashboard_report_id"] == item, "title"].iloc[0], key="report_download")
            row = filtered[filtered["dashboard_report_id"] == report_id].iloc[0]
            st.markdown(f"**{row['title']}**")
            st.write(row["description"])
            st.caption(f"Notebook {row['source_notebook_id']} · {row['scope']} · {row['format']}")
            payload = report_bytes(row["report_path"], PROJECT_ROOT)
            if payload:
                data, filename = payload
                mime = "text/html" if filename.lower().endswith(".html") else "application/octet-stream"
                st.download_button("Download self-contained report", data=data, file_name=filename, mime=mime)
            else:
                st.error("The indexed report file is unavailable.")
    st.subheader("Research-question traceability")
    rq = bundle.tables["research_question_coverage"]
    proposal_answers = {
        "rq1": [
            "The framework keeps <strong>11 quality anchors</strong>, <strong>17 selectable evidence families</strong>, and <strong>11 canonical regions</strong> explicit rather than collapsing them into one universal score.",
            "Pixel, colour, perceptual, feature, texture, seam, spatial, structural, semantic, and uncertainty evidence answer different failure questions; region policy prevents invalid comparisons.",
            "The benchmark demonstrates why this matters: <strong><em>LaMa</em> leads 10 of 11 anchors</strong>, while <strong><em>OpenCV Telea</em> leads crop SSIM</strong>. One traditional metric would therefore change the apparent winner.",
        ],
        "rq2": [
            "Across the <strong>three fully evaluated models</strong> and <strong>410 controlled restoration cases</strong>, <strong><em>LaMa</em> is the strongest general baseline</strong> with 10 of 11 anchor wins.",
            "<strong><em>OpenCV Telea</em></strong> is the fast deterministic baseline and leads crop SSIM; <strong><em>Stable Diffusion</em></strong> is more variable and can look plausible while drifting from the reference.",
            "The conditional tables expose differences by visual category, artificial damage, severity, experiment, and damage fraction. These are controlled subgroup results, <em>not</em> proof of universal performance across all artistic styles or real conservation damage.",
            "<strong><em>SDXL</em></strong> remains a bounded ten-case feasibility study and is not treated as a fourth full benchmark.",
        ],
        "rq3": [
            "Repeated-seed analysis covers <strong>130 canonical groups</strong> and <strong>35 damage-size groups</strong> for Stable Diffusion, with exactly four candidates per eligible group.",
            "Scalar variability shows <em>how much</em> candidates disagree; heatmaps and overlays show <em>where</em> disagreement concentrates, including repair interiors and boundaries.",
            "This evidence can prioritize speculative or unreliable regions for closer review. It is an <strong>empirical variability proxy</strong>, not calibrated confidence, and low variability does not prove correctness.",
        ],
    }
    formal_rows = rq[rq["research_question_id"].isin(PROPOSAL_RESEARCH_QUESTIONS)].copy()
    for rq_id in ("rq1", "rq2", "rq3"):
        row = formal_rows[formal_rows["research_question_id"].eq(rq_id)].iloc[0]
        exact_question = PROPOSAL_RESEARCH_QUESTIONS[rq_id]
        with st.expander(f"{rq_id.upper()} · {exact_question}"):
            st.markdown("**Answer from the completed evidence**")
            for answer in proposal_answers[rq_id]:
                st.markdown(f"- {answer}", unsafe_allow_html=True)
            evidence_note("Supported interpretation", str(row["supported_interpretation"]), "good")
            evidence_note("Do not infer", str(row["prohibited_interpretation"]), "danger")
            st.caption(f"Evidence notebooks: {', '.join(json_list(row['source_notebook_ids_json']))}")

    practical_rows = rq[rq["research_question_id"].eq("practical_output")]
    if not practical_rows.empty:
        row = practical_rows.iloc[0]
        with st.expander("Extended practical output · museum-oriented decision-support reporting"):
            st.markdown(
                "The proposal also identifies a practical communication objective. It is kept separate from the three formal research questions."
            )
            evidence_note("Completed output", str(row["supported_interpretation"]), "good")
            evidence_note("Boundary", str(row["prohibited_interpretation"]), "danger")
            st.caption(f"Evidence notebooks: {', '.join(json_list(row['source_notebook_ids_json']))}")
    with st.expander("Notebook 34 package provenance"):
        manifest = bundle.upstream_manifest
        st.json({"run_id": manifest.get("run_id"), "notebook": manifest.get("notebook_name"), "git_commit": manifest.get("git_commit"), "inventory_run_id": manifest.get("inventory_run_id"), "python_version": manifest.get("python_version"), "validation_summary": manifest.get("validation_summary")}, expanded=False)
    rich_evidence_note(
        "Live deployment",
        'The dashboard is publicly available on Streamlit Community Cloud: '
        '<a href="https://fhtw-painting-restoration.streamlit.app/" '
        'target="_blank" rel="noopener noreferrer">'
        'https://fhtw-painting-restoration.streamlit.app/</a>. '
        'It presents saved evaluation evidence without running restoration models or recomputing metrics.',
        "good",
    )


bundle = get_bundle()
with st.sidebar:
    st.markdown('<div class="museum-kicker" style="color:#d4af62">Evidence over assumption</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:Cormorant Garamond,Georgia,serif;font-size:1.55rem;line-height:1.05;margin:.2rem 0 1rem">Painting Restoration<br>Evaluation</div>', unsafe_allow_html=True)
    display_names = [item["display_name"] for item in bundle.summary["pages"]]
    page = st.radio("Navigate", display_names, format_func=lambda name: f"{PAGE_ICONS.get(name, '·')}  {name}", label_visibility="collapsed")
    st.markdown("---")
    st.markdown("**Controlled benchmark**  ")
    st.caption("50 paintings · 1,785 candidates · 8 evidence views")
    st.markdown('<span class="status-chip good">validated N34 package</span>', unsafe_allow_html=True)
    st.caption("Presentation and decision support only. No inference or metric recomputation.")

RENDERERS = {
    "Overview": render_overview,
    "Study Design": render_study_design,
    "Metric Framework": render_metric_framework,
    "Model Performance": render_model_performance,
    "Robustness & Uncertainty": render_robustness_uncertainty,
    "Trustworthiness & XAI": render_trustworthiness_xai,
    "Case Explorer": render_case_explorer,
    "Reports & Reproducibility": render_reports,
}
RENDERERS[page](bundle)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="caption-note">Controlled synthetic-damage evidence · Metrics support inspection; they do not replace conservation judgement.</div>', unsafe_allow_html=True)
