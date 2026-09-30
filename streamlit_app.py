"""Controlled-300 Painting Restoration Evidence Museum.

Read-only presentation over the immutable Notebook 34 dashboard package.
Notebook 35 implements the approved museum rooms one room at a time; no
scientific metric or restoration is computed in this application.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from restoration_eval.dashboard_application import (  # noqa: E402
    PRINCIPAL_ROOM_IDS,
    DashboardContractError,
    DashboardPackage,
    load_dashboard_validation_config,
    open_dashboard_package,
)


APP_BUILD = "n35.batch2.foyer.v4"
STUDY_BUILD = "n35.batch3.study.v4"
METRIC_BUILD = "n35.batch4.metric.v2"

ROOM_LABELS = {
    "exhibition_foyer": "Exhibition Foyer",
    "study_design": "Study Design",
    "metric_framework": "Metric Framework",
    "model_gallery": "Model Gallery",
    "stability_lab": "Stability Lab",
    "trustworthiness": "Trustworthiness",
    "case_explorer": "Case Explorer",
    "research_archive": "Research Archive",
    "focused_portrait_review": "Focused Portrait Review",
}

ROOM_BATCHES = {
    "study_design": 3,
    "metric_framework": 4,
    "model_gallery": 5,
    "stability_lab": 6,
    "trustworthiness": 7,
    "case_explorer": 8,
    "research_archive": 9,
}

# Destination room -> (room owning the source binding, exact asset id).
ROUTE_PREVIEW_ASSETS = {
    "study_design": ("exhibition_foyer", "asset_51c9c8fd90b375cfcdcc0934"),
    "metric_framework": ("metric_framework", "asset_e8837231a30b63c6cda95404"),
    "model_gallery": ("model_gallery", "asset_0b881fb2b09b7b805308cb18"),
    "stability_lab": ("stability_lab", "asset_9dee66286e792c92af5d7200"),
    "trustworthiness": ("trustworthiness", "asset_abecb3b93925d2ed8d45aa07"),
    "case_explorer": ("case_explorer", "asset_1c9654b8fe6387ee4a4e6bc8"),
    "research_archive": ("research_archive", "asset_d8b3392fc1c1f8e2612c7212"),
}

FOYER_SHELL_RELATIVE_PATH = "streamlit_assets/rooms/exhibition_foyer_shell.webp"
FOYER_SHELL_PATH = PROJECT_ROOT / FOYER_SHELL_RELATIVE_PATH
FOYER_SHELL_SHA256 = (
    "9863260cc04a7b664d7438564063b001a47dac2bf96bce4ed74726e6c7add630"
)

STUDY_SHELL_RELATIVE_PATH = "streamlit_assets/rooms/study_design_shell.png"
STUDY_SHELL_PATH = PROJECT_ROOT / STUDY_SHELL_RELATIVE_PATH
STUDY_SHELL_SHA256 = (
    "3e34fdb9645e01ce272a308d0b324862f87d2dbb750737706f1efb22b900c329"
)

METRIC_SHELL_RELATIVE_PATH = "streamlit_assets/rooms/metric_framework_shell.png"
METRIC_SHELL_PATH = PROJECT_ROOT / METRIC_SHELL_RELATIVE_PATH
METRIC_SHELL_SHA256 = (
    "a5182c9f6eb136b1c4be215d5477a40a8eeb0b33e6f156214d8a350617b15d8a"
)
METRIC_OPENING_ASSETS = {
    "reference": "asset_1c9654b8fe6387ee4a4e6bc8",
    "damaged": "asset_719d76fbfd3cc7b1f3609b8d",
    "restored": "asset_0b881fb2b09b7b805308cb18",
    "signed_improvement": "asset_e8837231a30b63c6cda95404",
}

METRIC_LENSES: Mapping[str, Mapping[str, object]] = {
    "pixel": {
        "label": "Pixel difference",
        "metrics": "MAE · MSE · PSNR",
        "summary": "Compares per-pixel reference error without describing structure or meaning.",
    },
    "structure": {
        "label": "Structure",
        "metrics": "SSIM",
        "summary": "Compares local luminance, contrast and structural pattern.",
    },
    "perceptual": {
        "label": "Perceptual similarity",
        "metrics": "LPIPS · AlexNet",
        "summary": "Compares learned visual similarity in the registered crop.",
    },
    "features": {
        "label": "Learned visual features",
        "metrics": "CLIP · DINOv2 cosine similarity",
        "summary": "Compares complementary pretrained feature spaces; neither proves correctness.",
    },
    "spatial": {
        "label": "Spatial change",
        "metrics": "Absolute RGB error · Signed improvement · Changed-pixel fraction",
        "summary": "Shows where restoration reduced, increased or left reference error unchanged.",
    },
    "local": {
        "label": "Texture, colour & seams",
        "metrics": "LBP · Gabor · GLCM · ΔE2000 · Boundary-gradient mismatch",
        "summary": "Examines local surface, colour and repair-boundary evidence separately.",
    },
    "semantic": {
        "label": "Local meaning & layout",
        "metrics": "Local DINO similarity · Structural-affinity correlation",
        "summary": "Checks local representation and layout without claiming historical meaning.",
    },
}

METRIC_REGIONS = (
    ("whole", "Whole image", "diagnostic"),
    ("content", "Painting content", "primary"),
    ("damaged", "Damaged area", "primary"),
    ("crop", "Damage crop", "diagnostic"),
    ("boundary", "Boundary", "primary"),
    ("outside", "Outside repair", "primary"),
    ("patches", "Local patches", "diagnostic"),
)
STUDY_CLEAN_ASSET_ID = "asset_51c9c8fd90b375cfcdcc0934"
STUDY_CORE_ASSETS: Mapping[str, Mapping[str, str]] = {
    "zero_control": {
        "label": "Control",
        "case_id": "canonical__p001__zero_control",
        "source_path": (
            "outputs/04_canonical_damaged_image_generation/images/damaged/"
            "p001/zero_control.png"
        ),
        "path": "streamlit_assets/evidence/study_design/p001_zero_control.png",
        "sha256": "b5852f0337c8342a1a70268f9e9f682534177581d238713f67bf28e0033482a2",
    },
    "scratch_thin": {
        "label": "Scratch",
        "case_id": "canonical__p001__scratch_thin",
        "source_path": (
            "outputs/04_canonical_damaged_image_generation/images/damaged/"
            "p001/scratch_thin.png"
        ),
        "path": "streamlit_assets/evidence/study_design/p001_scratch_thin.png",
        "sha256": "aa28fe11ad325c143cb952d46883b2cbb1c1d5627e1f49d69f9eb3f58bc24cd9",
    },
    "loss_small": {
        "label": "Small loss",
        "case_id": "canonical__p001__loss_small",
        "source_path": (
            "outputs/04_canonical_damaged_image_generation/images/damaged/"
            "p001/loss_small.png"
        ),
        "path": "streamlit_assets/evidence/study_design/p001_loss_small.png",
        "sha256": "7683f8017f2d0f846e07ac5d4746564a233f681205650052f142f21df5030241",
    },
    "loss_large": {
        "label": "Large loss",
        "case_id": "canonical__p001__loss_large",
        "source_path": (
            "outputs/04_canonical_damaged_image_generation/images/damaged/"
            "p001/loss_large.png"
        ),
        "path": "streamlit_assets/evidence/study_design/p001_loss_large.png",
        "sha256": "95c2dca591d41cd5d5462a5f8d52e815a9d907698128f1ffe649b4b1ca0462fe",
    },
    "mixed_damage": {
        "label": "Mixed",
        "case_id": "canonical__p001__mixed_damage",
        "source_path": (
            "outputs/04_canonical_damaged_image_generation/images/damaged/"
            "p001/mixed_damage.png"
        ),
        "path": "streamlit_assets/evidence/study_design/p001_mixed_damage.png",
        "sha256": "4272fe588bb1af895fc4da909794688fcb105353051720faad4652900aa57b52",
    },
}

STUDY_CATEGORY_LABELS = {
    "abstraction_surrealism": "Abstraction / Surrealism",
    "architecture_structured": "Architecture / Structured",
    "high_texture_brushwork": "High Texture / Brushwork",
    "landscape_natural": "Landscape / Natural",
    "portrait_figure": "Portrait / Figure",
}

# Fixed, predeclared category representatives.  These are the five historical
# pilot anchors, not cases selected because of a downstream score.  Every one
# has the complete 60-case Study Design branch population (5 + 7 + 15 + 33).
STUDY_CATEGORY_ANCHORS: Mapping[str, Mapping[str, object]] = {
    "abstraction_surrealism": {
        "painting_id": "p039",
        "title": "Painting with Troika",
        "display_title": "Painting with Troika",
        "artist": "Wassily Kandinsky",
        "clean_sha256": "adc7c740921e37111c263492b14ccf28e00ec71749fd54ff92a6a8b1440b58f2",
        "content_box": (0, 102, 768, 666),
        "matte_rgb": (137, 113, 93),
        "frame_fit": "slice",
    },
    "architecture_structured": {
        "painting_id": "p026",
        "title": "View of a Village along a River",
        "display_title": "Village along a River",
        "artist": "Attributed to Jan Brueghel I",
        "clean_sha256": "48819acb8a3147c0230f636c58eaaa127b2bdde3b71bb7e4f101b4e2ac97b3ee",
        "content_box": (0, 119, 768, 648),
        "matte_rgb": (86, 111, 93),
        "frame_fit": "slice",
    },
    "high_texture_brushwork": {
        "painting_id": "p043",
        "title": "The Card Players",
        "display_title": "The Card Players",
        "artist": "Paul Cézanne",
        "clean_sha256": "e18e79fb0a876169e1a315935be5e67a403e0c089c60841a2f34e1b6ba3b3fcd",
        "content_box": (0, 78, 768, 689),
        "matte_rgb": (82, 79, 73),
        "frame_fit": "slice",
    },
    "landscape_natural": {
        "painting_id": "p018",
        "title": "Classical Landscape with Figures",
        "display_title": "Landscape with Figures",
        "artist": "Henri Mauperché",
        "clean_sha256": "3e223322b3ca2c6f52ebe54a266991be897dd8d6c670ad52393f3262e15574ac",
        "content_box": (0, 130, 768, 637),
        "matte_rgb": (90, 74, 44),
        "frame_fit": "slice",
    },
    "portrait_figure": {
        "painting_id": "p001",
        "title": "Juan de Pareja",
        "display_title": "Juan de Pareja",
        "artist": "Diego Velázquez",
        "clean_sha256": "b5852f0337c8342a1a70268f9e9f682534177581d238713f67bf28e0033482a2",
        "content_box": (52, 0, 715, 768),
        "matte_rgb": (33, 28, 20),
        "frame_fit": "slice",
    },
}


STUDY_PATH_ICONS = {
    "core": """
<svg viewBox="0 0 64 34" aria-hidden="true" focusable="false">
  <rect x="6" y="5" width="8" height="24" rx=".6" fill="#c8bba5"/>
  <rect x="17" y="5" width="8" height="24" rx=".6" fill="#aa9c87"/>
  <rect x="28" y="5" width="8" height="24" rx=".6" fill="#7d6d59"/>
  <rect x="39" y="5" width="8" height="24" rx=".6" fill="#5c4a38"/>
  <rect x="50" y="5" width="8" height="24" rx=".6" fill="#413426"/>
</svg>
""",
    "damage_size": """
<svg viewBox="0 0 64 34" aria-hidden="true" focusable="false">
  <path d="M8 18c0-5 3-9 8-10 5-1 9 3 10 8 1 5-2 10-7 11-6 2-11-3-11-9Z" fill="#857968"/>
  <path d="M24 14c1-6 6-10 12-9 5 1 9 6 8 12 0 6-5 10-11 10-6-1-10-6-9-13Z" fill="#706454"/>
  <path d="M41 17c0-7 5-11 11-10 6 1 9 7 7 13-1 6-7 9-12 7-5-1-8-5-6-10Z" fill="#584838"/>
</svg>
""",
    "mask_placement": """
<svg viewBox="0 0 64 34" aria-hidden="true" focusable="false">
  <rect x="13" y="5" width="23" height="20" fill="#887967" fill-opacity=".48" stroke="#675948" stroke-width="1.2"/>
  <rect x="22" y="9" width="23" height="20" fill="#766754" fill-opacity=".52" stroke="#5e503f" stroke-width="1.2"/>
  <rect x="31" y="13" width="21" height="17" fill="#554839" fill-opacity=".36" stroke="#4d4032" stroke-width="1.2"/>
</svg>
""",
    "other_changes": """
<svg viewBox="0 0 64 34" aria-hidden="true" focusable="false">
  <rect x="7" y="6" width="22" height="21" fill="#b8aa94" fill-opacity=".44"/>
  <rect x="17" y="4" width="24" height="23" fill="#91816d" fill-opacity=".48"/>
  <rect x="27" y="8" width="24" height="21" fill="#665746" fill-opacity=".54"/>
  <rect x="37" y="11" width="20" height="17" fill="#493c2f" fill-opacity=".42"/>
</svg>
""",
}

STUDY_PATH_DEFAULT_OPTIONS = {
    "core": "mixed_damage",
    "damage_size": "size_10pct",
    "mask_placement": "variant_01",
    "other_changes": "dirt_dust__mild",
}

# These four examples are pinned in the method experiment configurations.
# They represent the only synthetic-degradation families approved by the
# evaluation policy for restoration-method routing; the other nine families
# remain accessible through the Research Archive rather than being implied to
# be inpainting tasks here.
STUDY_OTHER_CHANGE_OPTIONS = (
    ("dirt_dust__mild", "Dirt / dust", "mild"),
    ("partial_transparency__moderate", "Partial transparency", "moderate"),
    ("water_stain__severe", "Water stain", "severe"),
    ("water_stain_dirt__moderate", "Water stain + dirt", "moderate"),
)

STUDY_NOTE_COPY = {
    "selection": (
        "How paintings were selected",
        "300 works were duplicate-checked and balanced at 60 per broad visual category. "
        "These are study groups, not historical styles.",
    ),
    "preprocessing": (
        "How images were prepared",
        "Orientation and colour handling were standardized, then each image was fitted "
        "to 768 × 768 while preserving its recorded painting-content boundary.",
    ),
    "damage": (
        "How controlled damage was created",
        "Deterministic masks create an unchanged control, thin scratch, small loss, "
        "large loss and mixed damage inside the valid painting region.",
    ),
    "focused_tests": (
        "How focused tests work",
        "Balanced subsets separately test damage size, mask placement and other image "
        "changes. They are parallel questions, not sequential stages.",
    ),
    "non_restoration": (
        "Why some cases are not restoration tasks",
        "The unchanged control and procedural degradations test behaviour, but they are "
        "not missing-region restoration cases.",
    ),
    "portrait_audit": (
        "How the portrait audit was designed",
        "A separate manual audit screened 60 portraits and reused existing restoration "
        "results for 45 matched hand cases across 20 paintings.",
    ),
}


st.set_page_config(
    page_title="Painting Restoration Evidence Museum",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource(max_entries=1, show_spinner=False)
def load_application() -> tuple[dict[str, Any], DashboardPackage]:
    """Load only local configuration and the immutable N34 package."""

    config = load_dashboard_validation_config(PROJECT_ROOT)
    package = open_dashboard_package(PROJECT_ROOT)
    return config, package


@st.cache_data(max_entries=48, show_spinner=False)
def file_data_uri(path_text: str, expected_sha256: str) -> str:
    """Return one checksum-verified local file as a data URI."""

    path = Path(path_text)
    payload = path.read_bytes()
    observed_sha256 = hashlib.sha256(payload).hexdigest()
    if observed_sha256.casefold() != expected_sha256.casefold():
        raise DashboardContractError(
            f"Checksum mismatch for {path}: "
            f"expected {expected_sha256}, observed {observed_sha256}"
        )
    mime = {
        ".png": "image/png",
        ".webp": "image/webp",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(path.suffix.casefold(), "application/octet-stream")
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime};base64,{encoded}"


@st.cache_data(max_entries=256, show_spinner=False)
def recorded_study_image_uri(path_text: str) -> str:
    """Read one exact image path carried by an immutable N34 painting shard.

    N34 records scientific identity and the producer-relative input path.  This
    guard deliberately accepts only the five Study Design producer roots and
    never searches for a neighbour when a path is absent.
    """

    path = (PROJECT_ROOT / path_text).resolve()
    allowed_roots = tuple(
        (PROJECT_ROOT / relative).resolve()
        for relative in (
            "outputs/02_image_preprocessing/images/clean",
            "outputs/04_canonical_damaged_image_generation/images/damaged",
            "outputs/05_damage_size_sensitivity_dataset_generation/images/damaged",
            "outputs/06_mask_robustness_dataset_generation/images/damaged",
            "outputs/07_synthetic_degradation_dataset_generation/images/degraded",
        )
    )
    if not any(path.is_relative_to(root) for root in allowed_roots):
        raise DashboardContractError(
            f"Study Design image is outside the approved producer roots: {path_text}"
        )
    if path.suffix.casefold() != ".png" or not path.is_file():
        raise DashboardContractError(
            f"Exact Study Design image is unavailable: {path_text}"
        )
    observed_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    return file_data_uri(str(path), observed_sha256)


@st.cache_data(max_entries=96, show_spinner=False)
def recorded_metric_image_uri(path_text: str) -> str:
    """Read one exact image path carried by an immutable N34 metric selection."""

    path = (PROJECT_ROOT / path_text).resolve()
    allowed_roots = tuple(
        (PROJECT_ROOT / relative).resolve()
        for relative in (
            "outputs/02_image_preprocessing/images/clean",
            "outputs/04_canonical_damaged_image_generation/images/damaged",
            "outputs/05_damage_size_sensitivity_dataset_generation/images/damaged",
            "outputs/06_mask_robustness_dataset_generation/images/damaged",
            "outputs/07_synthetic_degradation_dataset_generation/images/degraded",
            "outputs/09_opencv_telea_restoration/images/restored",
            "outputs/10_lama_restoration/images/restored",
            "outputs/11_stable_diffusion_restoration/images/restored",
            "outputs/12_sdxl_feasibility_or_restoration/images/restored",
            "outputs/12a_hint_restoration/images/restored",
            "outputs/16_difference_maps_and_spatial_diagnostics/images/maps",
            "outputs/17_local_consistency_metrics/images/maps",
            "outputs/20_semantic_and_structural_consistency/images/maps",
        )
    )
    if not any(path.is_relative_to(root) for root in allowed_roots):
        raise DashboardContractError(
            f"Metric Framework image is outside approved producer roots: {path_text}"
        )
    if path.suffix.casefold() not in {".png", ".webp", ".jpg", ".jpeg"} or not path.is_file():
        raise DashboardContractError(
            f"Exact Metric Framework image is unavailable: {path_text}"
        )
    return file_data_uri(str(path), hashlib.sha256(path.read_bytes()).hexdigest())


def advance_metric_painting(painting_ids: tuple[str, ...]) -> None:
    current = str(st.session_state.get("metric_painting_selector", "p018"))
    index = painting_ids.index(current) if current in painting_ids else -1
    st.session_state["metric_painting_selector"] = painting_ids[(index + 37) % len(painting_ids)]
    remember_metric_painting()


def remember_metric_painting() -> None:
    """Keep this room's painting stable on reload without navigating the browser."""
    st.query_params["metric_painting"] = str(st.session_state["metric_painting_selector"])


def study_artwork_svg(
    data_uri: str,
    alt_text: str,
    anchor: Mapping[str, object],
) -> tuple[str, str]:
    """Fit one exact Study Design image from its registered N02 content box.

    The source data URI remains the checksum-verified producer PNG.  The SVG
    viewBox removes only N02's recorded padding.  The registered painting
    content is then fitted without distortion into the fixed approved frame;
    clean and altered states always use the identical crop transform.
    """

    content_box = anchor.get("content_box")
    matte_rgb = anchor.get("matte_rgb")
    frame_fit = str(anchor.get("frame_fit", "meet"))
    if (
        not isinstance(content_box, tuple)
        or len(content_box) != 4
        or not all(isinstance(value, int) for value in content_box)
    ):
        raise DashboardContractError("Study Design anchor has no valid content box")
    if (
        not isinstance(matte_rgb, tuple)
        or len(matte_rgb) != 3
        or not all(isinstance(value, int) and 0 <= value <= 255 for value in matte_rgb)
    ):
        raise DashboardContractError("Study Design anchor has no valid matte colour")
    if frame_fit not in {"meet", "slice"}:
        raise DashboardContractError(f"Unsupported Study Design frame fit: {frame_fit}")

    x0, y0, x1, y1 = content_box
    if not (0 <= x0 < x1 <= 768 and 0 <= y0 < y1 <= 768):
        raise DashboardContractError(
            f"Study Design content box is outside the 768-pixel canvas: {content_box}"
        )
    view_box = f"{x0} {y0} {x1 - x0} {y1 - y0}"
    matte = f"rgb({matte_rgb[0]} {matte_rgb[1]} {matte_rgb[2]})"
    label = html.escape(alt_text, quote=True)
    svg = f"""
<svg class="study-art study-art-{frame_fit}" viewBox="{view_box}"
     preserveAspectRatio="xMidYMid {frame_fit}" role="img" aria-label="{label}"
     data-content-box="{x0},{y0},{x1},{y1}" data-frame-fit="{frame_fit}">
  <image href="{data_uri}" x="0" y="0" width="768" height="768"
         preserveAspectRatio="xMidYMid meet"></image>
</svg>
"""
    return svg, matte


def scalar_query(name: str, default: str) -> str:
    value: Any = st.query_params.get(name, default)
    if isinstance(value, Sequence) and not isinstance(value, str):
        value = value[-1] if value else default
    return str(value)


def active_room(config: Mapping[str, Any]) -> str:
    requested = scalar_query(
        "room",
        str(config["application"]["default_room_id"]),
    )
    allowed = set(PRINCIPAL_ROOM_IDS) | {"focused_portrait_review"}
    return requested if requested in allowed else "exhibition_foyer"


def local_asset_uri(
    package: DashboardPackage,
    asset_id: str,
    *,
    profiles: Sequence[str] = ("thumb", "standard", "diagnostic_preview"),
) -> tuple[str, str]:
    """Resolve one exact registered rendition without neighbour substitution."""

    record = package.asset_record(asset_id)
    path = package.local_rendition(asset_id, profiles=profiles, verify=True)
    if path is None:
        raise DashboardContractError(
            f"Required local rendition is unavailable for {asset_id}"
        )
    relative = path.relative_to(package.package_root).as_posix()
    rows = package.renditions.loc[
        package.renditions["asset_id"].astype(str).eq(asset_id)
        & package.renditions["relative_path"].astype(str).eq(relative)
    ]
    if len(rows) != 1:
        raise DashboardContractError(
            f"Local rendition identity is not unique for {asset_id}"
        )
    rendition = rows.iloc[0]
    return (
        file_data_uri(str(path), str(rendition["sha256"])),
        str(record["alternative_text"]),
    )


def bound_asset_id(
    package: DashboardPackage,
    *,
    display_id: str,
    room_id: str,
) -> str:
    bindings = package.bindings_for(display_id=display_id, room_id=room_id)
    assets = bindings.loc[
        bindings["payload_ref"].astype(str).str.startswith("asset:")
    ]
    if len(assets) != 1:
        raise DashboardContractError(
            f"{display_id} must resolve to exactly one asset"
        )
    return str(assets.iloc[0]["payload_ref"]).removeprefix("asset:")


def verify_route_preview_asset(
    package: DashboardPackage,
    source_room_id: str,
    asset_id: str,
) -> None:
    references = set(
        package.bindings_for(room_id=source_room_id)["payload_ref"].astype(str)
    )
    if f"asset:{asset_id}" not in references:
        raise DashboardContractError(
            f"Route preview asset {asset_id} is not registered to {source_room_id}"
        )


def museum_mark_svg() -> str:
    return """
<svg viewBox="0 0 40 40" aria-hidden="true">
  <path d="M5 15h30L20 5 5 15Zm4 3h4v12H9V18Zm9 0h4v12h-4V18Zm9 0h4v12h-4V18ZM5 33h30v3H5v-3Z"/>
</svg>
"""


def search_svg() -> str:
    return """
<svg viewBox="0 0 32 32" aria-hidden="true">
  <circle cx="13.5" cy="13.5" r="8.5"/><path d="m20 20 8 8"/>
</svg>
"""


def collection_icon_svg(kind: str) -> str:
    icons = {
        "paintings": '<rect x="4" y="5" width="28" height="26" rx="1"/><path d="m8 27 7-8 5 5 4-6 5 9H8Z"/>',
        "visual_categories": '<path d="M19 5c-8 0-14 5-14 12 0 8 7 14 15 14h3c3 0 5-2 5-5 0-2-2-4-4-4h-1c-1 0-2-1-2-2 0-2 2-3 4-3h3c3 0 5-2 5-5 0-5-6-7-14-7Z"/><circle cx="12" cy="14" r="1.6"/><circle cx="17" cy="10" r="1.6"/><circle cx="23" cy="11" r="1.6"/><circle cx="10" cy="20" r="1.6"/>',
        "registered_cases": '<path d="M9 4h17l5 5v25H9V4Z"/><path d="M26 4v6h6M14 15h12M14 21h12M14 27h9"/>',
        "methods": '<circle cx="18" cy="18" r="6"/><path d="m18 3 2 5 5 1 4-3 4 7-4 3v5l4 3-4 7-5-2-4 4-2-5-5-1-4 3-4-7 4-3v-5l-4-3 4-7 5 2 4-4Z"/>',
    }
    return f'<svg viewBox="0 0 38 38" aria-hidden="true">{icons[kind]}</svg>'


def navigation_html(room_id: str) -> str:
    links = []
    for candidate in PRINCIPAL_ROOM_IDS:
        active = " active" if candidate == room_id else ""
        current = ' aria-current="page"' if candidate == room_id else ""
        links.append(
            f'<a class="room-link{active}" href="?room={candidate}" target="_self"{current}>'
            f'{html.escape(ROOM_LABELS[candidate])}</a>'
        )
    return f"""
<nav class="museum-nav" aria-label="Museum rooms">
  <a class="museum-brand" href="?room=exhibition_foyer" target="_self" aria-label="Painting Restoration Evidence Museum home">
    <span class="museum-mark">{museum_mark_svg()}</span>
    <span>Painting Restoration<br>Evidence Museum</span>
  </a>
  <div class="museum-navlinks">{''.join(links)}</div>
  <a class="museum-search" href="?room=case_explorer" target="_self" aria-label="Open Case Explorer">{search_svg()}</a>
  <span class="museum-seal" aria-label="Restoration Evidence">RE</span>
</nav>
"""


def collection_html(package: DashboardPackage) -> str:
    indicators = {
        str(item["indicator_id"]): item
        for item in package.bootstrap["scope_indicators"]
    }
    cards = (
        ("paintings", "Paintings"),
        ("visual_categories", "Visual categories"),
        ("registered_cases", "Registered cases"),
        ("methods", "Full-scope methods + bounded SDXL"),
    )
    rendered = []
    for key, label in cards:
        item = indicators[key]
        rendered.append(
            f"""
<div class="scope-item" title="{html.escape(str(item['explanation']), quote=True)}">
  <span class="scope-icon">{collection_icon_svg(key)}</span>
  <span class="scope-copy"><strong>{int(item['value']):,}</strong><span>{label}</span></span>
</div>
"""
        )
    return f"""
<section class="collection-block" aria-label="Collection in numbers">
  <h2>The collection in numbers</h2>
  <div class="scope-items">{''.join(rendered)}</div>
</section>
"""


def route_html(package: DashboardPackage) -> str:
    previews = {
        str(item["room_id"]): item
        for item in package.bootstrap["route_previews"]
    }
    stops = [
        """
<div class="route-stop current" aria-current="step">
  <span class="route-pin" aria-hidden="true"></span>
  <span class="route-dot"></span>
  <span class="route-name"><strong>You are here:</strong><br>Exhibition Foyer</span>
</div>
"""
    ]
    for room_id in PRINCIPAL_ROOM_IDS[1:]:
        item = previews[room_id]
        source_room_id, asset_id = ROUTE_PREVIEW_ASSETS[room_id]
        verify_route_preview_asset(package, source_room_id, asset_id)
        uri, alt = local_asset_uri(package, asset_id, profiles=("thumb", "standard"))
        stops.append(
            f"""
<div class="route-stop" tabindex="0">
  <span class="route-dot"></span>
  <span class="route-name">{html.escape(ROOM_LABELS[room_id])}</span>
  <article class="route-preview" aria-label="{html.escape(ROOM_LABELS[room_id])} preview">
    <img src="{uri}" alt="{html.escape(alt, quote=True)}" loading="lazy">
    <div><strong>{html.escape(ROOM_LABELS[room_id])}</strong>
      <p>{html.escape(str(item['question']))}</p>
      <span>{html.escape(str(item['summary']))}</span>
      <a href="?room={room_id}" target="_self">Enter room <b aria-hidden="true">→</b></a>
    </div>
  </article>
</div>
"""
        )
    return f"""
<section class="museum-route" id="museum-route" aria-label="Museum room map">
  <div class="route-track">
    <svg class="route-line" viewBox="0 0 824 40" preserveAspectRatio="none" aria-hidden="true">
      <polyline points="62,8 174,22 274,7 374,19 474,9 574,20 674,10 774,15"></polyline>
    </svg>
    {''.join(stops)}
  </div>
</section>
"""


def guided_tour_html(package: DashboardPackage) -> str:
    if scalar_query("tour", "0") != "1":
        return ""
    opening = package.bootstrap["opening"]
    return f"""
<aside class="tour-card" role="dialog" aria-label="Guided tour, stop one of eight">
  <div class="tour-step">Guided tour · 1 / 8</div>
  <strong>{html.escape(str(opening['question']))}</strong>
  <p>Start with the study design, then follow the same evidence through measurements, methods, stability and review flags.</p>
  <div class="tour-actions">
    <a href="?room=study_design&amp;tour=1" target="_self">Next: Study Design →</a>
    <a class="quiet" href="?room=exhibition_foyer" target="_self">Exit tour</a>
  </div>
</aside>
"""


def room_catalogue_record(
    package: DashboardPackage,
    room_id: str,
) -> Mapping[str, Any]:
    matches = [
        row
        for row in package.room_catalogue["rooms"]
        if str(row.get("room_id")) == room_id
    ]
    if len(matches) != 1:
        raise DashboardContractError(
            f"Room catalogue must contain exactly one {room_id!r} record"
        )
    return matches[0]


def study_href(**changes: str) -> str:
    state = {
        "room": "study_design",
        "study_path": scalar_query("study_path", "core"),
        "study_category": scalar_query("study_category", "portrait_figure"),
        "study_option": scalar_query("study_option", "mixed_damage"),
    }
    state.update(changes)
    return "?" + "&amp;".join(
        f"{html.escape(key, quote=True)}={html.escape(value, quote=True)}"
        for key, value in state.items()
    )


def apply_study_query(**changes: str) -> None:
    """Apply one validated Study Design selection without browser navigation."""

    unknown = set(changes).difference(
        {"study_path", "study_category", "study_option"}
    )
    if unknown:
        raise DashboardContractError(
            f"Unsupported Study Design query changes: {sorted(unknown)}"
        )
    state = {
        "room": "study_design",
        "study_path": scalar_query("study_path", "core"),
        "study_category": scalar_query("study_category", "portrait_figure"),
        "study_option": scalar_query("study_option", "mixed_damage"),
    }
    state.update({key: str(value) for key, value in changes.items()})
    path_id = state["study_path"]
    category_id = state["study_category"]
    option_id = state["study_option"]
    if path_id not in STUDY_PATH_DEFAULT_OPTIONS:
        raise DashboardContractError(f"Unknown Study Design path: {path_id}")
    if category_id not in STUDY_CATEGORY_ANCHORS:
        raise DashboardContractError(
            f"Unknown Study Design category: {category_id}"
        )
    allowed_options = {
        "core": {
            "clean_reference",
            "zero_control",
            "scratch_thin",
            "loss_small",
            "loss_large",
            "mixed_damage",
        },
        "damage_size": {
            "size_02pct",
            "size_04pct",
            "size_06pct",
            "size_08pct",
            "size_10pct",
            "size_15pct",
            "size_20pct",
        },
        "mask_placement": {
            "variant_01",
            "variant_02",
            "variant_03",
            "variant_04",
            "variant_05",
        },
        "other_changes": {
            option for option, _label, _severity in STUDY_OTHER_CHANGE_OPTIONS
        },
    }
    if option_id not in allowed_options[path_id]:
        raise DashboardContractError(
            f"Study Design option {option_id!r} does not belong to {path_id!r}"
        )
    st.query_params.from_dict(state)


def exact_study_case(
    painting_payload: Mapping[str, Any],
    *,
    experiment_id: str,
    case_id: str,
) -> Mapping[str, Any]:
    """Return one exact case or fail closed; never select a nearby identity."""

    matches = [
        row
        for row in painting_payload["cases"]
        if str(row.get("experiment_id")) == experiment_id
        and str(row.get("case_id")) == case_id
    ]
    if len(matches) != 1:
        raise DashboardContractError(
            f"Study Design requires exactly one {case_id!r} record; found {len(matches)}"
        )
    painting_id = str(painting_payload["painting"]["painting_id"])
    record = matches[0]
    if painting_id not in str(record.get("case_id")):
        raise DashboardContractError(
            f"Study Design case identity does not belong to {painting_id}: {case_id}"
        )
    return record


def study_branch_options(
    painting_payload: Mapping[str, Any],
    path_id: str,
) -> list[dict[str, Any]]:
    """Resolve the exact visible option strip for one representative painting."""

    painting = painting_payload["painting"]
    painting_id = str(painting["painting_id"])
    clean_path = str(painting["clean_image_path"])
    options: list[dict[str, Any]] = []

    if path_id == "core":
        options.append(
            {
                "option_id": "clean_reference",
                "label": "Original",
                "detail": "controlled pre-damage reference",
                "case": None,
                "path": clean_path,
            }
        )
        for option_id, label in (
            ("zero_control", "Control"),
            ("scratch_thin", "Scratch"),
            ("loss_small", "Small loss"),
            ("loss_large", "Large loss"),
            ("mixed_damage", "Mixed"),
        ):
            case = exact_study_case(
                painting_payload,
                experiment_id="canonical_missing_region",
                case_id=f"canonical__{painting_id}__{option_id}",
            )
            options.append(
                {
                    "option_id": option_id,
                    "label": label,
                    "detail": str(case["case_id"]),
                    "case": case,
                    "path": str(case["input_image_path"]),
                }
            )
    elif path_id == "damage_size":
        for percent in (2, 4, 6, 8, 10, 15, 20):
            option_id = f"size_{percent:02d}pct"
            case = exact_study_case(
                painting_payload,
                experiment_id="damage_size_sensitivity",
                case_id=f"damage_size__{painting_id}__loss_large__{option_id}",
            )
            options.append(
                {
                    "option_id": option_id,
                    "label": f"{percent}%",
                    "detail": "large-loss target",
                    "case": case,
                    "path": str(case["input_image_path"]),
                }
            )
    elif path_id == "mask_placement":
        for number in range(1, 6):
            option_id = f"variant_{number:02d}"
            case = exact_study_case(
                painting_payload,
                experiment_id="mask_robustness",
                case_id=(
                    f"mask_robustness__{painting_id}__loss_large__"
                    f"target_12p5pct__{option_id}"
                ),
            )
            options.append(
                {
                    "option_id": option_id,
                    "label": f"Variant {number}",
                    "detail": "large loss · fixed at 12.5%",
                    "case": case,
                    "path": str(case["input_image_path"]),
                }
            )
    elif path_id == "other_changes":
        for option_id, label, severity in STUDY_OTHER_CHANGE_OPTIONS:
            case = exact_study_case(
                painting_payload,
                experiment_id="synthetic_degradation",
                case_id=f"synthetic_degradation__{painting_id}__{option_id}",
            )
            if not bool(case.get("four_method_eligible")):
                raise DashboardContractError(
                    f"Study Design image-change option is not method-eligible: {option_id}"
                )
            options.append(
                {
                    "option_id": option_id,
                    "label": label,
                    "detail": severity,
                    "case": case,
                    "path": str(case["input_image_path"]),
                }
            )
    else:
        raise DashboardContractError(f"Unknown Study Design path: {path_id}")

    expected_count = {"core": 6, "damage_size": 7, "mask_placement": 5, "other_changes": 4}[path_id]
    if len(options) != expected_count or len({row["option_id"] for row in options}) != expected_count:
        raise DashboardContractError(
            f"Study Design {path_id} option contract is incomplete"
        )
    return options


def _render_study_design_legacy(package: DashboardPackage) -> None:
    """Render the approved Study Design room with exact p001 evidence."""

    room = package.load_room("study_design")
    if len(room) != 13:
        raise DashboardContractError("Study Design must contain exactly 13 records")
    opening = room_catalogue_record(package, "study_design")
    population = package.population
    painting_payload = package.load_painting("p001")
    painting = painting_payload["painting"]
    core_cases = study_core_cases(package)

    condition_id = scalar_query("study_condition", "mixed_damage")
    if condition_id not in {"clean_reference", *STUDY_CORE_ASSETS}:
        condition_id = "mixed_damage"
    path_id = scalar_query("study_path", "core")
    if path_id not in {"core", "damage_size", "mask_placement", "other_changes"}:
        path_id = "core"
    category_id = scalar_query("study_category", str(painting["category"]))
    if category_id not in STUDY_CATEGORY_LABELS:
        category_id = str(painting["category"])
    note_id = scalar_query("study_note", "selection")
    if note_id not in STUDY_NOTE_COPY:
        note_id = "selection"

    clean_uri, clean_alt = local_asset_uri(
        package,
        STUDY_CLEAN_ASSET_ID,
        profiles=("standard", "thumb"),
    )
    if condition_id == "clean_reference":
        selected_spec: Mapping[str, str] = {
            "label": "Clean reference",
            "case_id": "",
            "source_path": str(painting["clean_image_path"]),
            "path": "",
            "sha256": "",
        }
        selected_case: Mapping[str, Any] | None = None
        selected_uri = clean_uri
    else:
        selected_spec = STUDY_CORE_ASSETS[condition_id]
        selected_case = core_cases[condition_id]
        selected_uri = file_data_uri(
            str(PROJECT_ROOT / selected_spec["path"]),
            str(selected_spec["sha256"]),
        )
    shell_uri = file_data_uri(str(STUDY_SHELL_PATH), STUDY_SHELL_SHA256)

    original_selected = " selected" if condition_id == "clean_reference" else ""
    original_current = ' aria-current="true"' if condition_id == "clean_reference" else ""
    condition_thumbnails = [
        f"""
<a class="study-specimen original{original_selected}" href="{study_href(study_condition='clean_reference', study_path='core')}" target="_self" aria-label="Show clean reference"{original_current}>
  <img src="{clean_uri}" alt="{html.escape(clean_alt, quote=True)}" loading="lazy">
  <span>Original</span>
</a>
"""
    ]
    for key, specification in STUDY_CORE_ASSETS.items():
        uri = file_data_uri(
            str(PROJECT_ROOT / specification["path"]),
            str(specification["sha256"]),
        )
        selected = " selected" if key == condition_id else ""
        current = ' aria-current="true"' if key == condition_id else ""
        condition_thumbnails.append(
            f"""
<a class="study-specimen{selected}" href="{study_href(study_condition=key, study_path='core')}" target="_self" aria-label="Show {html.escape(str(specification['label']), quote=True)}"{current}>
  <img src="{uri}" alt="p001 with {html.escape(str(specification['label']).casefold(), quote=True)} under the registered controlled protocol" loading="lazy">
  <span>{html.escape(str(specification['label']))}</span>
</a>
"""
        )

    branch_specs = (
        ("core", "▥", "Core test", "Clean + five conditions"),
        ("damage_size", "◌", "Damage size", "7 levels · 245 cases"),
        ("mask_placement", "⧉", "Mask position", "5 variants · 525 cases"),
        ("other_changes", "◫", "Other image changes", "1,155 registered"),
    )
    branch_html = []
    for key, glyph, label, summary in branch_specs:
        active = " selected" if key == path_id else ""
        current = ' aria-current="true"' if key == path_id else ""
        branch_html.append(
            f"""
<a class="study-path{active}" href="{study_href(study_path=key)}" target="_self" title="{html.escape(summary, quote=True)}"{current}>
  <b aria-hidden="true">{glyph}</b><span>{html.escape(label)}</span><small>{html.escape(summary)}</small>
</a>
"""
        )

    category_glyphs = {
        "abstraction_surrealism": "✣",
        "architecture_structured": "▥",
        "high_texture_brushwork": "⌁",
        "landscape_natural": "◒",
        "portrait_figure": "♙",
    }
    collection_rows = []
    for key, label in STUDY_CATEGORY_LABELS.items():
        active = " selected" if key == category_id else ""
        current = ' aria-current="true"' if key == category_id else ""
        collection_rows.append(
            f"""
<a class="collection-drawer{active}" href="{study_href(study_category=key)}" target="_self" title="60 paintings in this broad visual study group"{current}>
  <span class="drawer-glyph" aria-hidden="true">{category_glyphs[key]}</span>
  <span>{html.escape(label)}</span><strong>{int(population['paintings_per_category'])}</strong>
</a>
"""
        )

    note_rows = []
    for key, (label, copy) in STUDY_NOTE_COPY.items():
        active = " selected" if key == note_id else ""
        current = ' aria-current="true"' if key == note_id else ""
        detail = f'<small>{html.escape(copy)}</small>' if key == note_id else ""
        note_rows.append(
            f"""
<a class="study-note{active}" href="{study_href(study_note=key)}" target="_self" title="{html.escape(copy, quote=True)}"{current}>
  <span>{html.escape(label)}</span>{detail}<b aria-hidden="true">▣</b>
</a>
"""
        )

    selected_label = str(selected_spec["label"])
    if condition_id == "clean_reference":
        status_heading = "Clean digital<br>reference"
        status_text = (
            "The controlled pre-damage image used for comparison. It is not verified "
            "historical ground truth."
        )
        realized_percent = 0.0
    elif condition_id == "zero_control":
        status_heading = "Control — not a<br>restoration task"
        status_text = (
            "The unchanged control checks whether a method alters an image when no "
            "region needs repair."
        )
        realized_percent = 0.0
    else:
        status_heading = "Suitable for<br>restoration testing"
        status_text = (
            "Controlled synthetic damage created by the registered protocol. "
            "Eligibility is routing—not restoration success."
        )
        assert selected_case is not None
        realized_percent = 100.0 * float(selected_case["realized_damage_fraction"])

    scene = f"""
<main class="study-stage" aria-label="Study Design">
  <span class="build-marker" data-build="{APP_BUILD}" data-study-build="{STUDY_BUILD}" aria-hidden="true"></span>
  <img class="study-shell" src="{shell_uri}" alt="" aria-hidden="true">
  {navigation_html('study_design')}

  <section class="study-intro" aria-labelledby="study-title">
    <h1 id="study-title">Study Design</h1><span class="study-title-rule" aria-hidden="true"></span>
    <h2>{html.escape(str(opening['question']))}</h2>
    <p>{html.escape(str(opening['introduction']))}</p>
    <p class="study-boundary">{html.escape(str(opening['boundary']))}</p>
  </section>

  <div class="study-central-title" role="heading" aria-level="2">Follow one painting through the study</div>
  <figure class="study-main-image clean"><img src="{clean_uri}" alt="{html.escape(clean_alt, quote=True)}" fetchpriority="high"></figure>
  <figcaption class="study-main-caption clean">Original</figcaption>
  <figure class="study-main-image damaged"><img src="{selected_uri}" alt="p001 {html.escape(selected_label.casefold(), quote=True)} controlled input" fetchpriority="high"></figure>
  <figcaption class="study-main-caption damaged" title="Realized damage: {realized_percent:.1f}%">{html.escape(selected_label)}{'' if condition_id == 'clean_reference' else ' damage'}</figcaption>

  <section class="study-status" aria-label="Methodological routing status">
    <span class="status-seal" aria-hidden="true">✓</span>
    <h3>{status_heading}</h3>
    <p>{html.escape(status_text)}</p>
  </section>

  <section class="study-paths" aria-label="Choose a parallel study path">
    <h3>Choose a<br>study path</h3>{''.join(branch_html)}
  </section>
  <section class="study-specimens" aria-label="Clean reference and five core conditions">{''.join(condition_thumbnails)}</section>

  <section class="study-collection" aria-label="Collection categories">
    <h3>The collection</h3>{''.join(collection_rows)}
  </section>

  <section class="study-notes" aria-label="Study notes">
    <h3>Study notes</h3>{''.join(note_rows)}
  </section>

  <aside class="portrait-audit" aria-label="Focused portrait audit summary">
    <h3>Focused<br><span>portrait audit</span></h3>
    <img src="{clean_uri}" alt="Juan de Pareja, the opening portrait example" loading="lazy">
    <ul class="portrait-audit-stats" aria-label="Focused portrait audit population">
      <li><strong>{int(population['d02_portraits_screened'])}</strong><span>portraits screened</span></li>
      <li><strong>{int(population['d02_matched_cases'])}</strong><span>matched hand cases</span></li>
      <li><strong>{int(population['d02_matched_painting_count'])}</strong><span>paintings</span></li>
      <li class="reuse"><span>Reuses existing results.</span></li>
    </ul>
    <a href="?room=focused_portrait_review&amp;return_room=study_design" target="_self">Open mini study room →</a>
  </aside>

  <div class="study-wall-motto">Same<br>paintings.<br>Different<br>questions.<br>A clearer<br>past.</div>

  <section class="study-scope" aria-label="Study at a glance">
    <span class="scope-book paintings"><strong>{int(population['painting_count']):,}</strong> paintings</span>
    <span class="scope-book conditions"><strong>5</strong> core conditions</span>
    <span class="scope-book cases"><strong>{int(population['registered_case_count']):,}</strong> registered cases</span>
    <span class="scope-book eligible"><strong>{int(population['four_model_eligible_case_count']):,}</strong> method-eligible cases</span>
    <span class="scope-plaque">Study at a glance</span>
  </section>
</main>
"""
    st.markdown(scene, unsafe_allow_html=True)


@st.fragment
def render_study_design(package: DashboardPackage) -> None:
    """Render one exact, interactive Study Design state from N34 shards."""

    room = package.load_room("study_design")
    if len(room) != 13:
        raise DashboardContractError("Study Design must contain exactly 13 records")
    opening = room_catalogue_record(package, "study_design")
    population = package.population

    category_id = scalar_query("study_category", "portrait_figure")
    if category_id not in STUDY_CATEGORY_ANCHORS:
        raise DashboardContractError(f"Unknown Study Design category: {category_id}")
    anchor = STUDY_CATEGORY_ANCHORS[category_id]
    painting_id = str(anchor["painting_id"])
    painting_payload = package.load_painting(painting_id)
    painting = painting_payload["painting"]
    if (
        str(painting.get("category")) != category_id
        or str(painting.get("title")) != str(anchor["title"])
    ):
        raise DashboardContractError(
            f"Study Design representative identity drift for {category_id}"
        )

    path_id = scalar_query("study_path", "core")
    if path_id not in STUDY_PATH_DEFAULT_OPTIONS:
        raise DashboardContractError(f"Unknown Study Design path: {path_id}")
    options = study_branch_options(painting_payload, path_id)
    option_by_id = {str(row["option_id"]): row for row in options}
    option_id = scalar_query(
        "study_option",
        STUDY_PATH_DEFAULT_OPTIONS[path_id],
    )
    if option_id not in option_by_id:
        raise DashboardContractError(
            f"Study Design option {option_id!r} does not belong to {path_id!r}"
        )
    selected = option_by_id[option_id]
    selected_case = selected["case"]
    case_id = (
        str(selected_case["case_id"])
        if selected_case is not None
        else f"clean_reference__{painting_id}"
    )

    clean_path = str(painting["clean_image_path"])
    clean_uri = file_data_uri(
        str((PROJECT_ROOT / clean_path).resolve()),
        str(anchor["clean_sha256"]),
    )
    selected_uri = (
        clean_uri
        if selected_case is None
        else recorded_study_image_uri(str(selected["path"]))
    )
    portrait_anchor = STUDY_CATEGORY_ANCHORS["portrait_figure"]
    portrait_payload = package.load_painting(str(portrait_anchor["painting_id"]))
    portrait_audit_uri = file_data_uri(
        str(
            (
                PROJECT_ROOT
                / str(portrait_payload["painting"]["clean_image_path"])
            ).resolve()
        ),
        str(portrait_anchor["clean_sha256"]),
    )
    decorative_wall_uris: dict[str, str] = {}
    for decorative_key in ("abstraction_surrealism",):
        decorative_anchor = STUDY_CATEGORY_ANCHORS[decorative_key]
        decorative_payload = package.load_painting(
            str(decorative_anchor["painting_id"])
        )
        decorative_wall_uris[decorative_key] = file_data_uri(
            str(
                (
                    PROJECT_ROOT
                    / str(decorative_payload["painting"]["clean_image_path"])
                ).resolve()
            ),
            str(decorative_anchor["clean_sha256"]),
        )
    shell_uri = file_data_uri(str(STUDY_SHELL_PATH), STUDY_SHELL_SHA256)

    specimen_html: list[str] = []
    for row in options:
        row_option = str(row["option_id"])
        row_case = row["case"]
        row_case_id = (
            str(row_case["case_id"])
            if row_case is not None
            else f"clean_reference__{painting_id}"
        )
        uri = clean_uri if row_case is None else recorded_study_image_uri(str(row["path"]))
        is_selected = row_option == option_id
        selected_class = " selected" if is_selected else ""
        current = ' aria-current="true"' if is_selected else ""
        detail = str(row["detail"])
        specimen_html.append(
            f"""
<a class="study-specimen{selected_class}" href="{study_href(study_option=row_option)}" target="_self"
   data-study-option="{html.escape(row_option, quote=True)}" data-case-id="{html.escape(row_case_id, quote=True)}"
   aria-label="Show {html.escape(str(row['label']), quote=True)}: {html.escape(detail, quote=True)}"{current}>
  <img src="{uri}" alt="{html.escape(str(painting['title']), quote=True)} — {html.escape(str(row['label']), quote=True)}" loading="lazy">
  <span>{html.escape(str(row['label']))}</span>
  <small>{html.escape(detail)}</small>
</a>
"""
        )

    branch_specs = (
        ("core", "Core test", "Original + five conditions"),
        ("damage_size", "Damage size", "7 levels · 245 cases"),
        ("mask_placement", "Mask position", "5 variants · large loss"),
        ("other_changes", "Other image changes", "4 eligible families · 350 / 1,155"),
    )
    branch_html: list[str] = []
    for key, label, summary in branch_specs:
        active = " selected" if key == path_id else ""
        current = ' aria-current="true"' if key == path_id else ""
        branch_html.append(
            f'<a class="study-path{active}" '
            f'href="{study_href(study_path=key, study_option=STUDY_PATH_DEFAULT_OPTIONS[key])}" '
            f'target="_self" data-study-path="{key}" '
            f'title="{html.escape(summary, quote=True)}" '
            f'aria-label="{html.escape(label, quote=True)}: {html.escape(summary, quote=True)}"{current}>'
            f'<span class="study-path-icon icon-{key}" aria-hidden="true">{STUDY_PATH_ICONS[key]}</span>'
            f'<span class="study-path-label">{html.escape(label)}</span>'
            '</a>'
        )

    category_glyphs = {
        "abstraction_surrealism": "✣",
        "architecture_structured": "▥",
        "high_texture_brushwork": "⌁",
        "landscape_natural": "◒",
        "portrait_figure": "♙",
    }
    collection_rows: list[str] = []
    for key, label in STUDY_CATEGORY_LABELS.items():
        representative = STUDY_CATEGORY_ANCHORS[key]
        active = " selected" if key == category_id else ""
        current = ' aria-current="true"' if key == category_id else ""
        collection_rows.append(
            f"""
<a class="collection-drawer{active}" href="{study_href(study_category=key)}" target="_self"
   data-study-category="{key}" data-painting-id="{representative['painting_id']}"
   title="Representative: {html.escape(str(representative['title']), quote=True)} · 60 paintings in this broad visual group"{current}>
  <span class="drawer-glyph" aria-hidden="true">{category_glyphs[key]}</span>
  <span>{html.escape(label)}</span><strong>{int(population['paintings_per_category'])}</strong>
</a>
"""
        )

    note_label_lines = {
        "selection": "How paintings<br>were selected",
        "preprocessing": "How images were<br>prepared",
        "damage": "How controlled<br>damage was created",
        "focused_tests": "How focused tests work",
        "non_restoration": "Why some cases are<br>not restoration tasks",
        "portrait_audit": "How the portrait audit<br>was designed",
    }
    note_rows: list[str] = []
    for key, (label, copy) in STUDY_NOTE_COPY.items():
        popup_id = f"study-note-{key}"
        note_rows.append(
            f"""
<div class="study-note-wrap" data-study-note-id="{key}">
  <button class="study-note" type="button" popovertarget="{popup_id}" aria-haspopup="dialog" aria-expanded="false" data-study-note-trigger="{key}">
    <span>{note_label_lines[key]}</span>
  </button>
  <aside class="study-note-popup" id="{popup_id}" popover="auto" role="dialog" aria-label="{html.escape(label, quote=True)}">
    <button class="study-note-close" type="button" popovertarget="{popup_id}" popovertargetaction="hide" aria-label="Close note">×</button>
    <strong>{html.escape(label)}</strong><p>{html.escape(copy)}</p>
  </aside>
</div>
"""
        )

    selected_label = str(selected["label"])
    selected_detail = str(selected["detail"])
    realized_percent = (
        0.0
        if selected_case is None
        else 100.0 * float(selected_case.get("realized_damage_fraction") or 0.0)
    )
    if path_id == "core" and option_id == "clean_reference":
        status_kind = "reference"
        status_heading = "Reference only"
        status_text = (
            "Pre-damage comparison image; not verified historical ground truth."
        )
        selected_plaque_title = "Clean reference"
        selected_plaque_state = "Original"
    elif path_id == "core" and option_id == "zero_control":
        status_kind = "control"
        status_heading = "Control — no repair"
        status_text = (
            "Unchanged input checks whether a method alters content when no repair "
            "is needed."
        )
        selected_plaque_title = "Unchanged control"
        selected_plaque_state = "No repair"
    elif path_id == "core":
        status_kind = "restoration"
        status_heading = "Suitable for restoration testing"
        status_text = (
            "Controlled missing content stays within the painting area. "
            "Eligibility does not mean success."
        )
        selected_plaque_title = {
            "scratch_thin": "Thin scratch",
            "loss_small": "Small loss",
            "loss_large": "Large loss",
            "mixed_damage": "Mixed damage",
        }[option_id]
        selected_plaque_state = "Controlled damage"
    elif path_id == "damage_size":
        status_kind = "restoration"
        status_heading = "Suitable for restoration testing"
        status_text = (
            "One large-loss mask is tested at seven sizes to measure sensitivity to "
            "missing area."
        )
        selected_plaque_title = "Large-loss target"
        selected_plaque_state = selected_label
    elif path_id == "mask_placement":
        status_kind = "restoration"
        status_heading = "Suitable for restoration testing"
        status_text = (
            "Five masks keep 12.5% damage fixed and test sensitivity to position."
        )
        selected_plaque_title = selected_label
        selected_plaque_state = "Large loss · 12.5%"
    else:
        status_kind = "degradation"
        status_heading = "Studied as a degradation"
        status_text = (
            "Registered change tested by all four methods. It is not a missing-region "
            "restoration case."
        )
        selected_plaque_title = selected_label
        selected_plaque_state = selected_detail.title()

    title = str(painting["title"])
    display_title = str(anchor["display_title"])
    artist = str(painting["artist"])
    clean_art, art_matte = study_artwork_svg(
        clean_uri,
        f"Clean controlled reference for {title}",
        anchor,
    )
    selected_art, selected_matte = study_artwork_svg(
        selected_uri,
        f"{title} — {selected_plaque_title}, {selected_plaque_state}",
        anchor,
    )
    scene = f"""
<main class="study-stage" aria-label="Study Design"
      data-study-category="{category_id}" data-painting-id="{painting_id}"
      data-study-path="{path_id}" data-study-option="{html.escape(option_id, quote=True)}"
      data-case-id="{html.escape(case_id, quote=True)}">
  <span class="build-marker" data-build="{APP_BUILD}" data-study-build="{STUDY_BUILD}" aria-hidden="true"></span>
  <img class="study-shell" src="{shell_uri}" alt="" aria-hidden="true">
  {navigation_html('study_design')}

  <section class="study-intro" aria-labelledby="study-title">
    <h1 id="study-title">Study Design</h1><span class="study-title-rule" aria-hidden="true"></span>
    <h2>{html.escape(str(opening['question']))}</h2>
    <p>{html.escape(str(opening['introduction']))}</p>
    <p class="study-boundary">{html.escape(str(opening['boundary']))}</p>
  </section>

  <div class="study-central-title" role="heading" aria-level="2">Follow one painting through the study</div>
  <figure class="study-main-image clean" style="--art-matte:{art_matte}">{clean_art}</figure>
  <figcaption class="study-main-caption clean" title="{html.escape(title, quote=True)} · {html.escape(artist, quote=True)}" aria-label="{html.escape(title, quote=True)}, original controlled reference">
    <span class="caption-title">{html.escape(display_title)}</span><span class="caption-state">Original</span>
  </figcaption>
  <figure class="study-main-image damaged" style="--art-matte:{selected_matte}">{selected_art}</figure>
  <figcaption class="study-main-caption damaged" title="{html.escape(title, quote=True)} · exact case: {html.escape(case_id, quote=True)} · realized change: {realized_percent:.1f}%" aria-label="{html.escape(title, quote=True)}, {html.escape(selected_plaque_title, quote=True)}, {html.escape(selected_plaque_state, quote=True)}">
    <span class="caption-title">{html.escape(selected_plaque_title)}</span><span class="caption-state">{html.escape(selected_plaque_state)}</span>
  </figcaption>

  <section class="study-status status-{status_kind}" aria-label="Methodological routing status">
    <span class="status-seal" aria-hidden="true">✓</span>
    <div class="status-heading" role="heading" aria-level="3">{html.escape(status_heading)}</div>
    <span class="status-rule" aria-hidden="true"></span>
    <p>{html.escape(status_text)}</p>
  </section>

  <section class="study-paths" aria-label="Choose a parallel study path">
    <h3>Choose a<br>study path</h3>{''.join(branch_html)}
  </section>
  <section class="study-specimens path-{path_id}" aria-label="{html.escape(path_id.replace('_', ' ').title(), quote=True)} options"
           data-specimen-count="{len(options)}" style="--specimen-count:{len(options)}">{''.join(specimen_html)}</section>

  <section class="study-collection" aria-label="Collection categories">
    <h3>The collection</h3>{''.join(collection_rows)}
  </section>

  <section class="study-notes" aria-label="Study notes">
    <h3>Study notes</h3>{''.join(note_rows)}
  </section>

  <aside class="portrait-audit" aria-label="Focused portrait audit summary">
    <h3>Focused<br><span>portrait audit</span></h3>
    <a class="portrait-audit-link" href="?room=focused_portrait_review&amp;return_room=study_design" target="_self"
       aria-label="Open the focused portrait review for Juan de Pareja">
      <img src="{portrait_audit_uri}" alt="Juan de Pareja, the fixed portrait-audit anchor" loading="lazy">
      <span class="portrait-audit-caption">Juan de Pareja</span>
    </a>
    <ul class="portrait-audit-stats" aria-label="Focused portrait audit population">
      <li>{int(population['d02_portraits_screened'])} portraits screened</li>
      <li>{int(population['d02_matched_cases'])} matched hand cases</li>
      <li>{int(population['d02_matched_painting_count'])} paintings</li>
      <li class="reuse">Reuses existing results.</li>
    </ul>
  </aside>

  <figure class="study-wall-emblem upper" aria-hidden="true">
    <svg viewBox="0 0 72 250" preserveAspectRatio="none" focusable="false">
      <defs>
        <linearGradient id="conservation-ground" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="#211812" />
          <stop offset=".48" stop-color="#3f291b" />
          <stop offset="1" stop-color="#76502d" />
        </linearGradient>
        <linearGradient id="restored-glaze" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="#8b5c31" stop-opacity=".12" />
          <stop offset="1" stop-color="#d0a260" stop-opacity=".58" />
        </linearGradient>
        <clipPath id="conservation-canvas">
          <path d="M15 22 59 15 65 228 21 235Z" />
        </clipPath>
      </defs>
      <path class="vignette-frame" d="M8 14 64 5 70 238 14 247Z" />
      <path class="vignette-liner" d="M12 18 62 10 68 233 18 241Z" />
      <g clip-path="url(#conservation-canvas)">
        <rect x="8" y="11" width="56" height="226" fill="url(#conservation-ground)" />
        <path class="vignette-arch" d="M8 70Q36 29 64 70V11H8Z" />
        <path class="vignette-hair" d="M18 87q0-34 19-42 21 5 20 39-1 23-8 33H25q-8-10-7-30Z" />
        <path class="vignette-face" d="M27 67q9-13 19-2l3 26q-2 21-13 22-11-2-13-22Z" />
        <path class="vignette-face-shadow" d="M23 80q8-7 14-5v38q-11-2-14-22Z" />
        <path class="vignette-brow" d="M27 82q5-4 10 0m3 0q5-4 9 0M35 88l-2 10 5 1m-8 7q7 5 14 0" />
        <path class="vignette-collar" d="m18 112 18 17 19-18 8 26-27 27-28-26Z" />
        <path class="vignette-coat" d="M7 140q11-16 29-12 19-4 29 12l7 97H0Z" />
        <path class="vignette-lapel" d="m16 137 20 27 20-28-8 65-12 23-13-23Z" />
        <path class="vignette-restored" d="M36 11h28v226H36Z" />
        <g class="vignette-cracks">
          <path d="M11 30l11 13-7 15 12 12-7 19M9 122l13 10-7 20 11 16-9 20M31 14l-4 19 7 11-6 17M12 205l14-10 7 13-6 24" />
          <path d="m20 43 7 2m-12 13-5 5m12 68 9-2m-16 23-6 2m17 42 7-6" />
        </g>
        <path class="vignette-seam" d="M36 18q-4 22 1 43-5 29 0 54-5 31 0 60-4 31 0 55" />
        <path class="vignette-brush" d="m12 218 41-32 6 8-43 30Z" />
        <path class="vignette-bristle" d="m53 186 8-7 5 3-7 12Z" />
      </g>
      <path class="vignette-inner-rule" d="M15 22 59 15 65 228 21 235Z" />
      <path class="vignette-ornament" d="m18 14 36-6m-28 233 27-4" />
    </svg>
  </figure>
  <figure class="study-wall-art lower" aria-hidden="true"><img src="{decorative_wall_uris['abstraction_surrealism']}" alt=""></figure>
  <section class="study-scope" aria-label="Study at a glance">
    <span class="scope-book paintings"><strong>{int(population['painting_count']):,}</strong><span>paintings</span></span>
    <span class="scope-book conditions"><strong>5</strong><span>core conditions</span></span>
    <span class="scope-book cases"><strong>{int(population['registered_case_count']):,}</strong><span>registered cases</span></span>
    <span class="scope-book eligible"><strong>{int(population['four_model_eligible_case_count']):,}</strong><span>method-eligible cases</span></span>
    <span class="scope-plaque">Study at a glance</span>
  </section>
</main>
"""
    st.markdown(scene, unsafe_allow_html=True)
    with st.container(key="study_control_bridge"):
        for key in STUDY_PATH_DEFAULT_OPTIONS:
            st.button(
                f"Select Study Design path: {key}",
                key=f"study_bridge_path_{key}",
                on_click=apply_study_query,
                kwargs={
                    "study_path": key,
                    "study_option": STUDY_PATH_DEFAULT_OPTIONS[key],
                },
            )
        for key in STUDY_CATEGORY_ANCHORS:
            st.button(
                f"Select Study Design category: {key}",
                key=f"study_bridge_category_{key}",
                on_click=apply_study_query,
                kwargs={"study_category": key},
            )
        for row in options:
            row_option = str(row["option_id"])
            st.button(
                f"Select Study Design option: {row_option}",
                key=f"study_bridge_option_{row_option}",
                on_click=apply_study_query,
                kwargs={"study_option": row_option},
            )
    st.html(
        r"""
<script>
(() => {
  if (window.__studyNotesV2) return;
  window.__studyNotesV2 = true;
  let leaveTimer = null;
  const triggers = () => [...document.querySelectorAll('[data-study-note-trigger]')];
  const popups = () => [...document.querySelectorAll('.study-note-popup')];
  const sync = () => triggers().forEach((trigger) => {
    const popup = document.getElementById(trigger.getAttribute('popovertarget'));
    trigger.setAttribute('aria-expanded', String(Boolean(popup && popup.matches(':popover-open'))));
  });
  const closeAll = () => {
    popups().forEach((popup) => {
      if (popup.matches(':popover-open')) popup.hidePopover();
    });
    sync();
  };
  const isNoteSurface = (node) => node instanceof Element && Boolean(node.closest('[data-study-note-trigger], .study-note-popup'));
  document.addEventListener('click', (event) => {
    if (!isNoteSurface(event.target)) closeAll();
    requestAnimationFrame(sync);
  }, true);
  document.addEventListener('toggle', (event) => {
    if (event.target instanceof Element && event.target.matches('.study-note-popup')) sync();
  }, true);
  document.addEventListener('pointerover', (event) => {
    if (isNoteSurface(event.target) && leaveTimer) {
      clearTimeout(leaveTimer);
      leaveTimer = null;
    }
  }, true);
  document.addEventListener('pointerout', (event) => {
    if (window.matchMedia('(pointer: coarse)').matches) return;
    if (isNoteSurface(event.target) && !isNoteSurface(event.relatedTarget)) {
      if (leaveTimer) clearTimeout(leaveTimer);
      leaveTimer = setTimeout(closeAll, 260);
    }
  }, true);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeAll();
  }, true);
})();
(() => {
  if (window.__studySelectionBridgeV1) return;
  window.__studySelectionBridgeV1 = true;
  document.documentElement.dataset.studyBridgeDocument ||= `${Date.now()}-${Math.random()}`;
  const bridgeKey = (link) => {
    if (link.dataset.studyPath) return `study_bridge_path_${link.dataset.studyPath}`;
    if (link.dataset.studyCategory) return `study_bridge_category_${link.dataset.studyCategory}`;
    if (link.dataset.studyOption) return `study_bridge_option_${link.dataset.studyOption}`;
    return null;
  };
  document.addEventListener('click', (event) => {
    if (
      event.defaultPrevented || event.button !== 0 || event.metaKey ||
      event.ctrlKey || event.shiftKey || event.altKey ||
      !(event.target instanceof Element)
    ) return;
    const link = event.target.closest(
      '.study-stage a[data-study-path], .study-stage a[data-study-category], .study-stage a[data-study-option]'
    );
    if (!link) return;
    const key = bridgeKey(link);
    const button = key
      ? document.querySelector(`.st-key-${CSS.escape(key)} button`)
      : null;
    if (!button) return;
    event.preventDefault();
    button.click();
  }, true);
})();
</script>
""",
        unsafe_allow_javascript=True,
    )


def inject_theme() -> None:
    """Install the page shell and exact Foyer artboard rules."""

    st.markdown(
        r"""
<style>
:root {
  --museum-green: #033d38;
  --museum-ink: #17354a;
  --museum-red: #741c22;
  --museum-gold: #f1cf67;
  --museum-paper: #f7f0df;
  --museum-serif: "Palatino Linotype", "Book Antiqua", Palatino, Georgia, serif;
  --museum-sans: Candara, Optima, "Segoe UI", sans-serif;
}
html, body, [class*="css"] { font-family: var(--museum-sans); }
html, body { margin: 0; background: #071d21; }
[data-testid="stAppViewContainer"] { background: #071d21; }
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], footer { display: none !important; }
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stMain"] { overflow: visible; }
.stMainBlockContainer, .block-container {
  width: 100% !important; max-width: none !important; padding: 0 !important; margin: 0 !important;
}
[data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stMarkdownContainer"] { line-height: normal; }
[data-testid="stMarkdownContainer"] > p { margin: 0; }

.foyer-stage {
  position: relative; container-type: inline-size; width: min(100%, 1672px);
  aspect-ratio: 1672 / 941; margin: 0 auto; overflow: hidden; isolation: isolate;
  background: #ead8b5; color: var(--museum-ink);
  box-shadow: 0 0 48px rgba(0,0,0,.4);
}
.foyer-shell { position: absolute; inset: 0; z-index: 0; width: 100%; height: 100%; object-fit: fill; user-select: none; }
.foyer-stage a { text-decoration: none; }
.foyer-stage a:focus-visible, .foyer-stage [tabindex="0"]:focus-visible {
  outline: max(2px,.16cqw) solid #fff2a8; outline-offset: max(2px,.12cqw);
}

.museum-nav {
  position: absolute; z-index: 30; left: 2.33%; top: 0; width: 95.34%; height: 6.58%;
  display: grid; grid-template-columns: 18.7% 1fr 3.5% 4.1%; align-items: center;
  gap: .35cqw; padding: 0 1.7cqw 0 1.75cqw; color: #fff7df;
  font-family: var(--museum-serif); box-sizing: border-box;
}
.museum-brand { display: flex; align-items: center; gap: .75cqw; color: #fff8e4 !important; font-size: 1.15cqw; line-height: .94; }
.museum-mark { display: grid; place-items: center; width: 2.65cqw; height: 2.65cqw; flex: 0 0 auto; background: #fff9ec; border: .16cqw solid #a6232c; border-radius: .18cqw; }
.museum-mark svg { width: 78%; height: 78%; fill: none; stroke: #a6232c; stroke-width: 2.6; stroke-linecap: round; stroke-linejoin: round; }
.museum-navlinks { height: 100%; display: flex; align-items: center; justify-content: center; gap: .14cqw; }
.museum-navlinks .room-link {
  position: relative; display: grid; place-items: center; height: 100%; padding: 0 .78cqw;
  color: #f5ecdc; font-size: .93cqw; white-space: nowrap;
}
.museum-navlinks .room-link::after { content: ""; position: absolute; left: .7cqw; right: .7cqw; bottom: .48cqw; height: .16cqw; background: transparent; }
.museum-navlinks .room-link:hover, .museum-navlinks .room-link.active { color: #ffe77b; }
.museum-navlinks .room-link.active::after { background: #f3d25d; }
.museum-search { display: grid; place-items: center; color: #fff; }
.museum-search svg { width: 2.05cqw; height: 2.05cqw; fill: none; stroke: currentColor; stroke-width: 2.4; stroke-linecap: round; }
.museum-seal { display: grid; place-items: center; width: 2.75cqw; height: 2.75cqw; border: .11cqw solid #286a99; border-radius: 50%; color: #f8eee0; background: #09243b; font: 1.05cqw/1 var(--museum-sans); }

.foyer-intro { position: absolute; z-index: 4; left: 5.05%; top: 15.4%; width: 25.4%; color: var(--museum-ink); }
.foyer-intro h1 { width: 130%; margin: 0 -30% 1.2cqw 0; padding: 0 !important; color: var(--museum-red); font: 700 3.35cqw/.93 var(--museum-serif); letter-spacing: -.10cqw; transform: scaleX(.77); transform-origin: left top; }
.foyer-intro p { width: 94%; margin: 0 0 .50cqw; color: #193e5c; font: 1.16cqw/1.35 var(--museum-serif); }
.foyer-intro p.foyer-method-summary { width: 85%; line-height: 1.28; }
.foyer-intro blockquote { width: 85%; margin: .78cqw 0 0; padding: .78cqw 0 0 !important; border-top: .08cqw solid rgba(25,62,92,.32); border-left: 0 !important; border-inline-start: 0 !important; color: rgba(23,75,118,.91); opacity: .93 !important; font: italic 1.43cqw/1.23 "Book Antiqua", Palatino, Georgia, serif; letter-spacing: -.025cqw; transform: rotate(-.22deg); transform-origin: left top; }

.hero-live { position: absolute; z-index: 3; left: 38%; top: 14.25%; width: 19%; height: 43.35%; display: grid; place-items: center; margin: 0; overflow: hidden; clip-path: polygon(1.55% 1.05%, 98.85% 0%, 99.35% 99.05%, 0% 100%); transform: rotate(-.16deg) skewY(-.10deg); transform-origin: 50% 50%; background: #191714; }
.hero-live img { width: 100%; height: 100%; object-fit: cover; object-position: 50% 42%; transform: scale(1.025); filter: saturate(.97) contrast(1.02); box-shadow: 0 0 1.2cqw rgba(0,0,0,.42); }
.hero-caption { position: absolute; z-index: 5; left: 40.43%; top: 62.04%; width: 14.30%; height: 6.95%; display: grid; place-items: center; padding: .18cqw .55cqw; box-sizing: border-box; color: rgba(38,63,82,.91); text-align: center; font: .99cqw/1.22 "Book Antiqua", Palatino, Georgia, serif; letter-spacing: -.018cqw; transform: rotate(-.28deg); transform-origin: center; }

.foyer-slogan { position: absolute; z-index: 5; left: 61.92%; top: 19.55%; width: 7.25%; color: rgba(255,239,204,.84); font: 1.08cqw/1.37 "Book Antiqua", Palatino, Georgia, serif; letter-spacing: .015cqw; text-transform: uppercase; text-shadow: 0 1px 1px rgba(67,20,16,.24); transform: perspective(24cqw) rotateY(-2.4deg) rotateZ(-1.55deg) skewY(-.42deg); transform-origin: left top; }
.foyer-slogan::after { content: ""; display: block; width: 3.02cqw; margin-top: .73cqw; border-top: .08cqw solid rgba(245,210,122,.76); }
.foyer-actions { position: absolute; z-index: 8; left: 60.72%; top: 42.25%; width: 15.05%; height: 17.65%; display: grid; grid-template-rows: 1fr 1fr; gap: 1.12cqw; }
.foyer-action { display: grid; grid-template-columns: 2.8cqw 1fr 1.35cqw; align-items: center; gap: .62cqw; padding: .55cqw .78cqw; color: #fff9e9 !important; font: 1.14cqw/1.08 var(--museum-serif); box-sizing: border-box; }
.foyer-action small { display: block; margin-top: .24cqw; color: #e9dbc0; font: .79cqw/1 var(--museum-sans); }
.action-medallion { display: grid; place-items: center; width: 2.42cqw; height: 2.42cqw; border-radius: 50%; color: #073e3c; background: #fff8e8; box-shadow: 0 .12cqw .25cqw rgba(0,0,0,.3); font: 1.15cqw/1 var(--museum-sans); }
.action-arrow { font: 1.72cqw/1 var(--museum-serif); text-align: right; }
.foyer-action:hover { color: #ffe677 !important; transform: translateX(.12cqw); }

.corridor-link { position: absolute; z-index: 7; left: 76.85%; top: 33.35%; width: 6.35%; color: rgba(255,226,120,.88) !important; text-align: center; font: .96cqw/1.34 "Book Antiqua", Palatino, Georgia, serif; letter-spacing: -.012cqw; text-shadow: 0 1px 1px rgba(14,46,67,.35); transform: perspective(20cqw) rotateY(-8.2deg) rotateZ(-1.85deg) skewY(-1.15deg); transform-origin: center; }
.corridor-link b { display: block; margin-top: .22cqw; font: 1.62cqw/1 var(--museum-serif); }
.corridor-motto { position: absolute; z-index: 5; left: 91.18%; top: 23.45%; width: 5.15%; color: rgba(239,206,126,.84); font: .89cqw/1.39 "Book Antiqua", Palatino, Georgia, serif; letter-spacing: .012cqw; text-transform: uppercase; text-align: left; text-shadow: 0 1px 1px rgba(18,50,70,.30); transform: perspective(18cqw) rotateY(-10.5deg) rotateZ(-2.05deg) skewY(-1.35deg); transform-origin: left center; }
.corridor-motto::after { content: ""; display: block; width: 2.25cqw; margin-top: .64cqw; border-top: .08cqw solid rgba(232,202,112,.74); }

.foyer-footer { position: absolute; z-index: 12; left: 2.60%; top: 83.50%; width: 94.68%; height: 13.86%; display: grid; grid-template-columns: 37.1% 62.9%; box-sizing: border-box; }
.collection-block { min-height: 0; height: 100%; padding: 1.05cqw 1.3cqw .65cqw 1.55cqw; box-sizing: border-box; border-right: .08cqw solid rgba(74,54,40,.35); overflow: hidden; }
.collection-block h2 { margin: 0 0 .72cqw; padding: 0 !important; color: #8c2026; font: 700 .84cqw/1 var(--museum-sans); letter-spacing: .12cqw; text-transform: uppercase; }
.scope-items { display: grid; grid-template-columns: .9fr .9fr 1fr 1.35fr; gap: .72cqw; }
.scope-item { min-width: 0; display: grid; grid-template-columns: 2.55cqw 1fr; gap: .46cqw; align-items: center; color: #173d5a; }
.scope-icon { display: grid; place-items: center; width: 2.3cqw; height: 2.3cqw; color: #a1242b; }
.scope-icon svg { width: 100%; height: 100%; fill: none; stroke: currentColor; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; }
.scope-copy strong { display: block; color: #8e2027; font: 700 1.22cqw/1 var(--museum-serif); }
.scope-copy span { display: block; margin-top: .15cqw; color: #183d5a; font: .78cqw/1.02 var(--museum-serif); }

.museum-route { position: relative; min-height: 0; height: 100%; padding: 2.38cqw .85cqw .35cqw 2.7cqw; box-sizing: border-box; overflow: visible; }
.route-track { position: relative; display: grid; grid-template-columns: 1.24fr repeat(7,1fr); align-items: start; }
.route-line { position: absolute; z-index: 0; inset: .15cqw 0 auto 0; width: 100%; height: 2cqw; overflow: visible; pointer-events: none; }
.route-line polyline { fill: none; stroke: #2e6893; stroke-width: 1.6; stroke-dasharray: 5 4; stroke-linecap: round; stroke-linejoin: round; vector-effect: non-scaling-stroke; }
.route-stop { position: relative; z-index: 2; min-width: 0; text-align: center; }
.route-stop:nth-child(3) { transform: translateY(.67cqw); }
.route-stop:nth-child(4) { transform: translateY(-.05cqw); }
.route-stop:nth-child(5) { transform: translateY(.52cqw); }
.route-stop:nth-child(6) { transform: translateY(.08cqw); }
.route-stop:nth-child(7) { transform: translateY(.58cqw); }
.route-stop:nth-child(8) { transform: translateY(.12cqw); }
.route-stop:nth-child(9) { transform: translateY(.28cqw); }
.route-dot { position: relative; z-index: 3; display: block; width: 1.06cqw; height: 1.06cqw; margin: 0 auto .48cqw; box-sizing: border-box; border: .19cqw solid #174f7c; border-radius: 50%; background: #f7f0df; }
.route-stop.current .route-dot { border-color: #bc2831; box-shadow: 0 0 0 .14cqw #f7f0df; }
.route-stop.current .route-pin { position: absolute; z-index: 2; left: calc(50% - .725cqw); top: -1.7cqw; width: 1.45cqw; height: 1.45cqw; border-radius: 50% 50% 50% 0; background: #bd2530; transform: rotate(-45deg); }
.route-stop.current .route-pin::after { content: ""; position: absolute; width: .48cqw; height: .48cqw; left: .49cqw; top: .49cqw; border-radius: 50%; background: #f8e6ae; }
.route-name { display: block; color: #153e5e; font: .73cqw/1.05 var(--museum-serif); }
.route-name strong { color: #a7222b; }
.route-preview { position: absolute; z-index: 20; left: 50%; bottom: 6cqw; width: 19.2cqw; min-height: 6.45cqw; display: grid; grid-template-columns: 4.65cqw 1fr; gap: .58cqw; padding: .55cqw; box-sizing: border-box; opacity: 0; visibility: hidden; transform: translate(-50%, .5cqw); transition: opacity .12s ease, transform .12s ease; border: .08cqw solid #9d805b; border-radius: .25cqw; background: rgba(255,250,239,.985); box-shadow: 0 .65cqw 1.4cqw rgba(22,31,32,.27); text-align: left; pointer-events: none; }
.route-preview::after { content: ""; position: absolute; left: 50%; bottom: -.42cqw; width: .72cqw; height: .72cqw; background: #fffaf0; border-right: .08cqw solid #9d805b; border-bottom: .08cqw solid #9d805b; transform: translateX(-50%) rotate(45deg); }
.route-preview img { width: 4.65cqw; height: 5.5cqw; object-fit: cover; border: .08cqw solid #927652; }
.route-preview strong { display: block; color: #761e25; font: 700 .88cqw/1 var(--museum-serif); }
.route-preview p { margin: .22cqw 0 .15cqw; color: #183e59; font: 700 .66cqw/1.12 var(--museum-sans); }
.route-preview span { display: block; max-height: 2.05cqw; overflow: hidden; color: #40576a; font: .55cqw/1.16 var(--museum-sans); }
.route-preview a { display: inline-block; margin-top: .22cqw; color: #07534d; font: 700 .58cqw/1 var(--museum-sans); pointer-events: auto; }
.route-stop:hover .route-preview, .route-stop:focus-within .route-preview, .route-stop:focus .route-preview { opacity: 1; visibility: visible; transform: translate(-50%,0); pointer-events: auto; }
.route-stop:nth-last-child(-n+2) .route-preview { left: auto; right: 0; transform: translate(0,.5cqw); }
.route-stop:nth-last-child(-n+2):hover .route-preview, .route-stop:nth-last-child(-n+2):focus .route-preview { transform: translate(0,0); }
.route-stop:nth-child(2) .route-preview { left: 0; transform: translate(0,.5cqw); }
.route-stop:nth-child(2):hover .route-preview, .route-stop:nth-child(2):focus .route-preview { transform: translate(0,0); }

.tour-card { position: absolute; z-index: 40; right: 2.7%; top: 8%; width: 22%; padding: 1cqw 1.1cqw; box-sizing: border-box; border: .12cqw solid #d9ae52; background: rgba(5,56,53,.97); color: #fff5dc; box-shadow: 0 .8cqw 1.8cqw rgba(0,0,0,.34); }
.tour-step { margin-bottom: .35cqw; color: #f1d06d; font: 700 .63cqw/1 var(--museum-sans); letter-spacing: .08cqw; text-transform: uppercase; }
.tour-card strong { font: 1.1cqw/1.08 var(--museum-serif); }
.tour-card p { margin: .45cqw 0 .65cqw; color: #f1e7d0; font: .68cqw/1.28 var(--museum-sans); }
.tour-actions { display: flex; align-items: center; gap: .8cqw; }
.tour-actions a { padding: .48cqw .65cqw; color: #083e3a; background: #f4d26d; font: 700 .66cqw/1 var(--museum-sans); }
.tour-actions a.quiet { color: #fff2d1; background: transparent; border: .06cqw solid rgba(255,255,255,.42); }

.study-stage {
  position: relative; container-type: inline-size; width: min(100%, 1672px);
  aspect-ratio: 1672 / 941; margin: 0 auto; overflow: hidden; isolation: isolate;
  background: #e7ddd2; color: #15120e; box-shadow: 0 0 48px rgba(0,0,0,.42);
}
.study-shell { position: absolute; inset: 0; z-index: 0; width: 100%; height: 100%; object-fit: fill; user-select: none; }
.study-stage a { text-decoration: none; }
.build-marker { display: none !important; }
.study-stage a:focus-visible { outline: max(2px,.15cqw) solid #f7d86b; outline-offset: max(1px,.08cqw); }

.study-intro { position: absolute; z-index: 4; left: 8.18%; top: 15.55%; width: 22.95%; color: #14213a; font-family: var(--museum-serif); }
.study-intro h1 { margin: 0; padding: 0 !important; color: #111517; font: 600 3.22cqw/.98 var(--museum-serif); letter-spacing: -.11cqw; }
.study-title-rule { display: block; width: 2.9cqw; margin: .78cqw 0 .92cqw; border-top: .12cqw solid rgba(25,28,27,.72); }
.study-intro h2 { width: 93%; margin: 0 0 1.08cqw; padding: 0 !important; color: #16243f; font: 500 1.48cqw/1.08 var(--museum-serif); letter-spacing: -.035cqw; }
.study-intro p { width: 92%; margin: 0; color: rgba(27,43,74,.96); font: .98cqw/1.24 var(--museum-serif); }
.study-intro .study-boundary { width: 84%; margin-top: .55cqw; padding-top: .5cqw; border-top: .07cqw solid rgba(67,62,50,.42); color: rgba(30,42,63,.84); font-size: .84cqw; line-height: 1.18; transform: rotate(-.10deg); }

.study-central-title { position: absolute; z-index: 5; left: 37.55%; top: 14.05%; width: 29.35%; margin: 0; padding: 0 !important; color: #17120e; text-align: center; white-space: nowrap; font: 600 1.92cqw/1 var(--museum-serif); letter-spacing: -.05cqw; }
.study-main-image { position: absolute; z-index: 3; margin: 0; overflow: hidden; background: linear-gradient(rgba(255,255,255,.025),rgba(0,0,0,.085)),var(--art-matte,#171511); box-shadow: inset 0 0 .46cqw rgba(16,12,8,.42); }
.study-main-image::after { content: ""; position: absolute; inset: 0; z-index: 2; pointer-events: none; box-shadow: inset 0 0 .24cqw rgba(15,10,7,.48), inset 0 0 0 .04cqw rgba(244,222,176,.16); }
.study-art { display: block; width: 100%; height: 100%; overflow: hidden; }
.study-art image { filter: saturate(.96) contrast(1.02); }
.study-main-image.clean { left: 35.82%; top: 22.02%; width: 11.77%; height: 27.40%; }
.study-main-image.damaged { left: 51.43%; top: 22.54%; width: 9.44%; height: 26.65%; }
.study-main-caption { position: absolute; z-index: 6; display: grid; grid-template-rows: 1fr 1fr; align-content: center; justify-items: center; height: 2.42%; padding: .08cqw .22cqw .06cqw; overflow: hidden; box-sizing: border-box; color: rgba(48,36,25,.95); text-align: center; font-family: var(--museum-serif); transform: rotate(-.18deg); }
.study-main-caption.clean { left: 37.86%; top: 49.68%; width: 7.25%; }
.study-main-caption.damaged { left: 52.48%; top: 49.72%; width: 7.00%; transform: rotate(-.12deg); }
.study-main-caption .caption-title, .study-main-caption .caption-state { display: block; max-width: 100%; overflow: hidden; white-space: nowrap; }
.study-main-caption .caption-title { align-self: end; color: rgba(54,42,29,.88); font: 500 .58cqw/.98 var(--museum-serif); letter-spacing: -.008cqw; }
.study-main-caption .caption-state { align-self: start; margin-top: .04cqw; color: rgba(43,31,21,.98); font: 600 .64cqw/.98 var(--museum-serif); letter-spacing: -.012cqw; }

.study-status { position: absolute; z-index: 7; left: 62.61%; top: 32.4%; width: 7.04%; height: 17.8%; display: grid; grid-template-columns: 1.38cqw minmax(0,1fr); grid-template-rows: auto auto minmax(0,1fr); column-gap: .34cqw; align-content: start; padding: .62cqw .48cqw .42cqw .62cqw; overflow: hidden; box-sizing: border-box; color: #2d261d; font-family: var(--museum-serif); transform: rotate(-.22deg); }
.study-status .status-seal { grid-column: 1; grid-row: 1; display: grid; place-items: center; width: 1.34cqw; height: 1.34cqw; margin-top: .04cqw; border-radius: 50%; color: #f5ead1; background: #006453; box-shadow: 0 .08cqw .16cqw rgba(0,0,0,.24); font: 700 .74cqw/1 var(--museum-sans); }
.study-status .status-heading { grid-column: 2; grid-row: 1; min-width: 0; margin: 0; padding: 0 !important; color: #2c251c; font: 600 .69cqw/1.04 var(--museum-serif); letter-spacing: -.014cqw; }
.study-status .status-rule { grid-column: 1 / -1; grid-row: 2; display: block; width: 1.45cqw; margin: .48cqw 0 .44cqw; border-top: .07cqw solid rgba(73,60,43,.48); }
.study-status p { grid-column: 1 / -1; grid-row: 3; min-width: 0; margin: 0; overflow: hidden; color: rgba(51,43,31,.91); font: .56cqw/1.11 var(--museum-serif); letter-spacing: -.005cqw; }

.study-paths { position: absolute; z-index: 8; left: 32.55%; top: 53.88%; width: 36.84%; height: 7.75%; display: grid; grid-template-columns: 14.96% 19.35% 1.14% 19.35% .81% 19.51% 1.14% 23.58%; box-sizing: border-box; font-family: var(--museum-serif); }
.study-paths h3 { display: grid; place-items: center start; margin: 0; padding: .52cqw .28cqw .48cqw .75cqw !important; color: rgba(48,38,27,.94); font: 500 .94cqw/1.08 var(--museum-serif); letter-spacing: -.012cqw; transform: translateY(.34cqw); }
.study-path { position: relative; display: grid; grid-template-rows: 1.92cqw .98cqw; place-items: center; align-content: center; min-width: 0; margin: 0; padding: .34cqw .24cqw .30cqw; color: rgba(53,40,28,.93) !important; box-sizing: border-box; text-align: center; overflow: hidden; transition: background-color .12s ease,box-shadow .12s ease; }
.study-path[data-study-path="core"] { grid-column: 2; }
.study-path[data-study-path="damage_size"] { grid-column: 4; }
.study-path[data-study-path="mask_placement"] { grid-column: 6; }
.study-path[data-study-path="other_changes"] { grid-column: 8; }
.study-path-icon { display: grid; width: 3.08cqw; height: 1.62cqw; place-items: center; align-self: end; opacity: .78; }
.study-path-icon svg { display: block; width: 100%; height: 100%; overflow: visible; filter: drop-shadow(0 .03cqw .02cqw rgba(255,248,225,.36)); }
.study-path-label { display: block; align-self: start; max-width: 100%; color: rgba(53,40,28,.94); white-space: nowrap; font: 500 .76cqw/1 var(--museum-serif); letter-spacing: -.014cqw; }
.study-path.selected { color: #261d14 !important; background: rgba(255,248,226,.46); box-shadow: inset 0 0 0 .06cqw rgba(176,129,53,.42),0 .08cqw .22cqw rgba(75,47,24,.15); }
.study-path.selected .study-path-icon { opacity: .88; }
.study-path:hover { background: rgba(255,247,224,.32); box-shadow: inset 0 0 0 .05cqw rgba(156,113,55,.24); }

.study-specimens { --specimen-size:4.55cqw; --specimen-gap:1.05cqw; position: absolute; z-index: 6; left: 34.45%; top: 62.90%; width: 32.84%; height: 11.35%; display: grid; grid-template-columns: repeat(var(--specimen-count),var(--specimen-size)); justify-content: center; align-items: start; gap: var(--specimen-gap); box-sizing: border-box; font-family: var(--museum-serif); isolation: isolate; }
.study-specimens[data-specimen-count="4"] { --specimen-size:4.85cqw; --specimen-gap:2.55cqw; }
.study-specimens[data-specimen-count="5"] { --specimen-size:4.65cqw; --specimen-gap:1.82cqw; }
.study-specimens[data-specimen-count="6"] { --specimen-size:4.55cqw; --specimen-gap:1.05cqw; }
.study-specimens[data-specimen-count="7"] { --specimen-size:4.05cqw; --specimen-gap:.64cqw; }
.study-specimens::before { content:""; position:absolute; z-index:0; left:-1.15cqw; right:-1.15cqw; top:-.34cqw; bottom:-.28cqw; pointer-events:none; background:radial-gradient(circle at 18% 28%,rgba(222,194,160,.10),transparent 23%),radial-gradient(circle at 76% 68%,rgba(79,59,42,.09),transparent 30%),linear-gradient(90deg,rgba(150,124,100,.98),rgba(176,151,126,.97) 46%,rgba(150,127,106,.98)); box-shadow:inset 0 .08cqw .28cqw rgba(238,213,182,.09),inset 0 -.08cqw .28cqw rgba(68,49,34,.14); -webkit-mask-image:linear-gradient(90deg,transparent,black 4%,black 96%,transparent); mask-image:linear-gradient(90deg,transparent,black 4%,black 96%,transparent); }
.study-specimen { position:relative; z-index:1; display:grid; grid-template-rows:var(--specimen-size) minmax(1.38cqw,auto); align-content:start; min-width:0; color:#292218 !important; text-align:center; }
.study-specimen::before { content:""; position:absolute; z-index:3; left:50%; top:-.29cqw; width:.42cqw; height:.42cqw; pointer-events:none; border-radius:50%; background:radial-gradient(circle at 38% 32%,#f0d79e 0 18%,#8a642e 22% 62%,#3f2b18 68% 100%); box-shadow:0 .05cqw .08cqw rgba(0,0,0,.42); transform:translateX(-50%); }
.study-specimen img { display:block; width:100%; height:var(--specimen-size); padding:.12cqw; object-fit:cover; object-position:50% 46%; filter:saturate(.95) contrast(1.02); background:#251912; border:.24cqw ridge #5a3923; box-shadow:0 .12cqw .22cqw rgba(43,29,18,.42),inset 0 0 .07cqw rgba(168,119,67,.38); box-sizing:border-box; }
.study-specimen span { display:grid; place-items:start center; min-height:1.38cqw; margin-top:.20cqw; padding:.05cqw .08cqw 0; overflow:hidden; color:rgba(45,35,25,.97); background:transparent; border:0; box-sizing:border-box; white-space:normal; text-wrap:balance; text-shadow:0 .035cqw .035cqw rgba(241,224,196,.58); font:500 .66cqw/.98 var(--museum-serif); letter-spacing:-.012cqw; }
.study-specimen small { display:none; }
.study-specimen.selected img, .study-specimen.original img { outline: .09cqw solid rgba(151,103,48,.88); outline-offset: .05cqw; box-shadow: 0 .12cqw .34cqw rgba(0,0,0,.34); }
.study-specimen:hover img { outline: .09cqw solid #b68245; outline-offset: .05cqw; }

.study-collection { position: absolute; z-index: 7; left: 11.10%; top: 60.36%; width: 15.95%; height: 25.35%; display: grid; grid-template-rows: 19.1% repeat(5,16.18%); overflow: visible; box-sizing: border-box; font-family: var(--museum-serif); }
.study-collection h3 { display: grid; place-items: center; justify-self: start; width: 7.25cqw; margin: 0 0 0 1.22cqw; padding: 0 !important; color: #2c2016; text-align: center; font: 500 .88cqw/1 var(--museum-serif); letter-spacing: -.012cqw; transform: rotate(-.2deg); }
.collection-drawer { display: grid; grid-template-columns: 2.45cqw minmax(0,1fr) 2cqw; align-items: center; column-gap: .40cqw; min-width: 0; padding: .16cqw .55cqw; overflow: hidden; color: #eadcc5 !important; background: rgba(58,34,19,.62); box-sizing: border-box; border-top: .04cqw solid rgba(231,204,157,.22); font: .72cqw/1 var(--museum-serif); }
.collection-drawer > span:not(.drawer-glyph) { min-width: 0; overflow: hidden; white-space: nowrap; }
.collection-drawer strong { justify-self: end; min-width: 1.75cqw; color: inherit; text-align: right; font: 600 .91cqw/1 var(--museum-serif); }
.drawer-glyph { justify-self: center; color: #e9d3a5; text-align: center; font: .96cqw/1 var(--museum-serif); }
.collection-drawer.selected { color: #2b2016 !important; background: rgba(239,221,188,.93); box-shadow: inset 0 0 .3cqw rgba(78,50,28,.25); }
.collection-drawer.selected .drawer-glyph { color: #55351d; }
.collection-drawer:hover { color: #fff2d0 !important; background: rgba(92,59,31,.42); }
.collection-drawer.selected:hover { color: #2b2016 !important; background: rgba(244,228,198,.98); }

.study-notes { position: absolute; z-index: 8; left: 72.91%; top: 15.83%; width: 10.59%; height: 53.24%; display: block; box-sizing: border-box; font-family: var(--museum-serif); }
.study-notes h3 { position: absolute; left: 0; right: 0; top: .38cqw; height: 11.8%; display: grid; place-items: center; margin: 0; padding: 0 !important; color: #eee0ca; font: 500 1.30cqw/1 var(--museum-serif); text-shadow: 0 .08cqw .12cqw rgba(0,0,0,.65); transform: rotate(-.72deg); transform-origin: center; }
.study-note-wrap { position: absolute; left: 0; width: 100%; min-height: 0; }
.study-note-wrap[data-study-note-id="selection"] { left: 4.5%; top: 14.57%; width: 94.35%; height: 12.38%; }
.study-note-wrap[data-study-note-id="preprocessing"] { top: 28.94%; height: 12.77%; }
.study-note-wrap[data-study-note-id="damage"] { top: 43.31%; height: 12.77%; }
.study-note-wrap[data-study-note-id="focused_tests"] { top: 57.49%; height: 12.38%; }
.study-note-wrap[data-study-note-id="non_restoration"] { top: 71.66%; height: 13.17%; }
.study-note-wrap[data-study-note-id="portrait_audit"] { top: 86.63%; height: 13.37%; }
.study-note { position: relative; display: grid; place-items: center start; width: 100%; height: 100%; margin: 0; padding: .28cqw .55cqw .27cqw 1.02cqw; color: rgba(239,222,194,.93) !important; background: transparent; box-sizing: border-box; border: 0; text-align: left; cursor: pointer; font: .82cqw/1.08 var(--museum-serif); text-shadow: 0 .06cqw .10cqw rgba(0,0,0,.52); }
.study-note-wrap:not([data-study-note-id="selection"]) .study-note { width: 84%; height: 100%; margin: 0 0 0 4%; padding: .25cqw .20cqw .23cqw .72cqw; background: transparent; border: 0; border-radius: 0; box-shadow: none; transform: none; }
.study-note-wrap[data-study-note-id="selection"] .study-note { color: #2b2016 !important; text-shadow: none; }
.study-note b { display: none; }
.study-note:hover { color: #fff3d4 !important; background: transparent; text-shadow: 0 .06cqw .12cqw rgba(0,0,0,.72); }
.study-note-wrap[data-study-note-id="selection"] .study-note:hover { color: #2b2016 !important; background: rgba(255,247,226,.18); }
.study-note[aria-expanded="true"], .study-note-wrap:has(.study-note-popup:popover-open) .study-note { color: #352719 !important; background: rgba(240,224,196,.95); box-shadow: inset 0 0 .35cqw rgba(79,51,27,.28); text-shadow: none; }
.study-note-wrap:not([data-study-note-id="selection"]):has(.study-note-popup:popover-open) .study-note { color: #f5dfba !important; background: transparent; box-shadow: none; text-shadow: 0 .06cqw .12cqw rgba(0,0,0,.72); }
.study-note-popup { width: min(34rem,78vw); margin: auto; padding: 1.45rem 3.2rem 1.5rem 1.55rem; color: #33271d; background: #f3e7cf; border: 2px solid #765638; border-radius: .3rem; box-shadow: 0 1.2rem 3rem rgba(20,12,7,.48), inset 0 0 0 4px rgba(255,250,231,.68); font-family: var(--museum-serif); }
.study-note-popup::backdrop { background: rgba(14,22,21,.24); backdrop-filter: blur(1px); }
.study-note-popup strong { display: block; padding-bottom: .65rem; color: #173f3b; border-bottom: 1px solid rgba(83,60,35,.32); font-size: 1.32rem; }
.study-note-popup p { margin: .85rem 0 0 !important; font: 1.02rem/1.48 var(--museum-serif); }
.study-note-close { position: absolute; right: .72rem; top: .58rem; width: 2rem; height: 2rem; padding: 0; color: #443120; background: transparent; border: 1px solid rgba(82,58,33,.35); border-radius: 50%; cursor: pointer; font: 1.45rem/1 var(--museum-serif); }

.portrait-audit { position: absolute; z-index: 7; left: 88.64%; top: 29.82%; width: 8.0%; height: 34.8%; color: #322216; font-family: var(--museum-serif); }
.portrait-audit h3 { width: 6.55cqw; margin: 0; padding: 0 !important; font: 600 1.10cqw/1.02 var(--museum-serif); letter-spacing: -.02cqw; }
.portrait-audit h3 span { white-space: nowrap; }
.portrait-audit h3::after { content: ""; display: block; width: 1.65cqw; margin: .60cqw 0 0; border-top: .08cqw solid rgba(67,48,31,.56); }
.portrait-audit-link { position: absolute; display: block !important; left: .42cqw; top: 4.20cqw; width: 5.88cqw; height: 8.02cqw; margin: 0 !important; overflow: visible; color: #342417 !important; border: 0 !important; }
.portrait-audit-link img { display: block; width: 5.42cqw; height: 5.95cqw; margin: 0; object-fit: cover; object-position: 50% 43%; filter: saturate(.91) contrast(1.03); transition: filter .12s ease; }
.portrait-audit-link:hover img, .portrait-audit-link:focus-visible img { filter: saturate(1) contrast(1.06) brightness(1.04); }
.portrait-audit-caption { position:absolute; left:-.08cqw; top:7.08cqw; width:5.86cqw; height:.72cqw; display:grid; place-items:center; overflow:hidden; color:rgba(48,31,19,.96); text-align:center; white-space:nowrap; font-family:var(--museum-serif); font-size:.63cqw; font-weight:600; line-height:1; letter-spacing:-.012cqw; transform:rotate(.25deg); }
.study-stage .portrait-audit-stats { position:absolute; left:0; top:13.15cqw; width:6.65cqw; display:grid; grid-template-rows:repeat(4,auto); row-gap:.015cqw; margin:0; padding:0; overflow:visible; color:rgba(52,36,22,.93); list-style:none; font-family:var(--museum-serif); font-size:clamp(7px,.68cqw,12px); font-weight:400; line-height:1.22; letter-spacing:-.018cqw; transform:none; }
.study-stage .portrait-audit-stats li { display: block; min-width: 0; margin: 0; padding: 0; font-size: inherit; font-weight: 400; line-height: inherit; white-space: nowrap; }
.study-stage .portrait-audit-stats .reuse { display: block; }

.study-wall-emblem { position: absolute; z-index: 5; margin: 0; overflow: hidden; pointer-events: none; }
.study-wall-emblem.upper { left:95.28%; top:12.15%; width:3.59%; height:21.86%; clip-path:polygon(8% 4.4%,90% 0,100% 95.6%,18% 100%); }
.study-wall-emblem svg { display:block; width:100%; height:100%; padding:.34cqw .16cqw .40cqw .20cqw; box-sizing:border-box; opacity:1; transform:none; filter:drop-shadow(0 .08cqw .06cqw rgba(20,12,7,.42)); }
.study-wall-emblem .vignette-frame { fill:#24160f; stroke:#15100d; stroke-width:4; }
.study-wall-emblem .vignette-liner { fill:#8a5b2e; stroke:#bd8a46; stroke-width:3; }
.study-wall-emblem .vignette-arch { fill:#120f0d; opacity:.72; }
.study-wall-emblem .vignette-hair { fill:#100e0c; stroke:#070605; stroke-width:1.4; }
.study-wall-emblem .vignette-face { fill:#8a5735; stroke:#2c1d15; stroke-width:1.1; }
.study-wall-emblem .vignette-face-shadow { fill:#34231a; opacity:.82; }
.study-wall-emblem .vignette-brow { fill:none; stroke:#211711; stroke-width:1.8; stroke-linecap:round; }
.study-wall-emblem .vignette-collar { fill:#c5a46e; stroke:#4d3522; stroke-width:1.3; }
.study-wall-emblem .vignette-coat { fill:#171310; stroke:#080706; stroke-width:1.5; }
.study-wall-emblem .vignette-lapel { fill:#3f2a1d; opacity:.92; }
.study-wall-emblem .vignette-restored { fill:url(#restored-glaze); mix-blend-mode:screen; }
.study-wall-emblem .vignette-cracks { fill:none; stroke:#d1b276; stroke-width:1.3; stroke-linecap:round; stroke-linejoin:round; opacity:.88; }
.study-wall-emblem .vignette-seam { fill:none; stroke:#be8a43; stroke-width:1.5; stroke-dasharray:4 3; opacity:.82; }
.study-wall-emblem .vignette-brush { fill:#633a20; stroke:#17100c; stroke-width:1.2; }
.study-wall-emblem .vignette-bristle { fill:#c5a36e; stroke:#352317; stroke-width:1; }
.study-wall-emblem .vignette-inner-rule { fill:none; stroke:#d0a05c; stroke-width:2; }
.study-wall-emblem .vignette-ornament { fill:none; stroke:#1b130e; stroke-width:2.2; stroke-linecap:round; }
.study-wall-art { position: absolute; z-index: 5; margin: 0; overflow: hidden; pointer-events: none; background: #33281d; box-shadow: inset 0 0 .18cqw rgba(10,8,6,.56); transform-origin: center; }
.study-wall-art img { display: block; width: 100%; height: 100%; object-fit: cover; filter: saturate(.72) sepia(.12) contrast(.94) brightness(.76); }
.study-wall-art.lower { left: 96.47%; top: 38.58%; width: 2.63%; height: 21.15%; clip-path: polygon(0 4.5%,100% 0,93% 98.5%,4.5% 100%); transform: none; }
.study-wall-art.lower img { position: relative; top: -18.1%; width: 100%; height: 136.2%; object-position: 52% 45%; filter: saturate(.65) sepia(.18) contrast(.92) brightness(.72); }

.study-scope { position: absolute; z-index: 9; inset: 0; pointer-events: none; color: #ead7aa; font-family: var(--museum-serif); }
.scope-book { position: absolute; display: flex; align-items: center; justify-content: center; height: 2.55%; padding: 0 .2cqw; box-sizing: border-box; white-space: nowrap; text-shadow: 0 .07cqw .10cqw rgba(0,0,0,.72); font: 500 .94cqw/1 var(--museum-serif); letter-spacing: -.012cqw; }
.scope-book strong { display: inline; margin: 0 .24cqw 0 0; font-weight: 600; }
.scope-book.paintings { left: 53.90%; top: 77.85%; width: 9.30%; transform: rotate(1.1deg); }
.scope-book.conditions { left: 53.20%; top: 80.78%; width: 10.40%; transform: rotate(1deg); }
.scope-book.cases { left: 65.05%; top: 78.30%; width: 10.88%; padding: 0 .42cqw; font-size: .84cqw; transform: rotate(2.1deg); }
.scope-book.eligible { left: 65.05%; top: 81.55%; width: 11.48%; padding: 0 .42cqw; color: #ead5a3; font-size: .82cqw; transform: rotate(1.6deg); }
.scope-plaque { position: absolute; left: 60.65%; top: 84.17%; width: 6.82%; height: 2.98%; display: flex; align-items: center; justify-content: center; color: #3a2919; font: 500 .78cqw/1 var(--museum-serif); letter-spacing: -.012cqw; transform: rotate(.1deg); }

.pending-shell { min-height: 100vh; background: linear-gradient(140deg,#0a3f3c,#132d3d); color: #fff6dc; }
.pending-shell .museum-nav { position: relative; left: 2.33%; width: 95.34%; height: 62px; }
.pending-room { min-height: calc(100vh - 62px); display: grid; place-items: center; text-align: center; }
.pending-room .plaque { max-width: 680px; padding: 2rem; border: 1px solid #d2ac54; background: rgba(0,0,0,.2); }
.pending-room h1 { margin: 0 0 .7rem; font: 3rem/1 var(--museum-serif); }
.pending-room p { line-height: 1.5; color: #e7ddca; }
.pending-room a { color: #ffe076; }

@media (max-width: 780px) {
  html, body { overflow-x: hidden; overflow-y: auto; }
  [data-testid="stAppViewContainer"] { overflow-x: hidden !important; overflow-y: auto !important; background: #f4ead4; }
  [data-testid="stMain"] { overflow-x: hidden !important; overflow-y: visible !important; }
  .foyer-stage { width: 100%; min-height: 1240px; aspect-ratio: auto; overflow: visible; background: linear-gradient(#0b3e3d 0 78px,#f6eddc 78px 100%); }
  .foyer-shell { opacity: .25; height: 610px; object-fit: cover; object-position: center top; }
  .museum-nav { position: relative; left: 0; width: 100%; height: auto; min-height: 78px; grid-template-columns: 1fr auto auto; padding: 10px 16px; background: rgba(3,52,49,.97); }
  .museum-brand { font-size: 17px; }.museum-mark { width: 36px; height: 36px; }.museum-seal { width: 36px; height: 36px; font-size: 13px; }.museum-search svg { width: 28px; height: 28px; }
  .museum-navlinks { grid-column: 1 / -1; justify-content: flex-start; overflow-x: auto; height: 38px; }
  .museum-navlinks .room-link { height: 38px; padding: 0 10px; font-size: 13px; }
  .foyer-intro, .hero-live, .hero-caption, .foyer-slogan, .foyer-actions, .corridor-link, .corridor-motto, .foyer-footer { position: relative; left: auto; top: auto; width: auto; height: auto; }
  .foyer-intro { z-index: 5; padding: 35px 7vw 25px; }.foyer-intro h1 { font-size: clamp(42px,9vw,70px); }.foyer-intro p { font-size: 18px; }.foyer-intro p.foyer-method-summary { width: 100%; }.foyer-intro blockquote { font-size: 24px; }
  .hero-live { width: min(76vw,520px); height: auto; aspect-ratio: 1; margin: 10px auto; background: #191d20; border: 12px ridge #c99536; }.hero-live img { width: 100%; height: 100%; }
  .hero-caption { width: min(72vw,470px); margin: 12px auto 22px; min-height: 62px; padding: 8px; background: #f2e2c5; border: 1px solid #987045; font-size: 17px; }
  .foyer-slogan { width: min(84vw,620px); margin: 25px auto 12px; padding: 20px; color: #f9ebc5; background: #8a292b; font-size: 23px; }
  .foyer-actions { width: min(84vw,620px); margin: 0 auto 25px; height: 148px; gap: 12px; }.foyer-action { grid-template-columns: 44px 1fr 28px; padding: 10px 16px; font-size: 18px; background: #07514b; border: 1px solid #d7b653; }.action-medallion { width: 38px; height: 38px; font-size: 18px; }.action-arrow { font-size: 26px; }.foyer-action small { font-size: 12px; }
  .corridor-link, .corridor-motto { display: none; }
  .foyer-footer { display: block; margin: 20px 4vw 0; background: rgba(255,250,239,.97); border: 1px solid #aa8b61; }
  .collection-block { padding: 18px; border-right: 0; border-bottom: 1px solid rgba(74,54,40,.3); }.collection-block h2 { font-size: 14px; }.scope-items { grid-template-columns: repeat(2,1fr); gap: 16px; }.scope-item { grid-template-columns: 40px 1fr; }.scope-icon { width: 36px; height: 36px; }.scope-copy strong { font-size: 20px; }.scope-copy span { font-size: 13px; }
  .museum-route { padding: 112px 14px 20px; overflow-x: auto; }.route-track { min-width: 720px; }.route-name { font-size: 11px; }.route-dot { width: 16px; height: 16px; border-width: 3px; }.route-preview { width: 260px; min-height: 88px; bottom: 48px; grid-template-columns: 72px 1fr; gap: 8px; padding: 8px; }.route-preview img { width: 72px; height: 72px; }.route-preview strong { font-size: 13px; }.route-preview p { font-size: 10px; }.route-preview span { font-size: 9px; max-height: 30px; }.route-preview a { font-size: 10px; }
  .tour-card { position: fixed; left: 5vw; right: 5vw; top: 105px; width: auto; padding: 16px; }.tour-step { font-size: 11px; }.tour-card strong { font-size: 20px; }.tour-card p { font-size: 13px; }.tour-actions a { font-size: 12px; padding: 8px 10px; }

  .study-stage { width: 100%; min-height: 0; aspect-ratio: auto; overflow: visible; background: #eee5d7; display: grid; grid-template-columns: 7vw minmax(0,1fr) minmax(0,1fr) 7vw; align-content: start; }
  .study-shell { opacity: .18; height: 720px; object-fit: cover; object-position: center top; }
  .study-stage .museum-nav { position: relative; left: 0; width: 100%; height: auto; grid-column: 1 / -1; grid-row: 1; }
  .study-intro, .study-central-title, .study-main-image, .study-main-caption, .study-status,
  .study-paths, .study-specimens, .study-collection, .study-notes, .portrait-audit,
  .study-scope { position: relative; left: auto; top: auto; width: auto; height: auto; }
  .study-intro { grid-column: 2 / 4; grid-row: 2; padding: 42px 0 20px; }.study-intro h1 { font-size: clamp(45px,9vw,68px); }.study-title-rule { width: 48px; margin: 12px 0 16px; }.study-intro h2 { width: 100%; font-size: 25px; }.study-intro p, .study-intro .study-boundary { width: 100%; font-size: 16px; }
  .study-central-title { grid-column: 2 / 4; grid-row: 3; padding: 24px 0 14px !important; text-align: left; white-space: normal; font-size: 32px; }
  .study-main-image.clean, .study-main-image.damaged { left: auto; top: auto; width: min(38vw,320px); height: auto; aspect-ratio: .76; margin: 0; border: 9px ridge #8b6337; justify-self: center; }
  .study-main-image.clean { grid-column: 2; grid-row: 4; }.study-main-image.damaged { grid-column: 3; grid-row: 4; }
  .study-main-caption.clean, .study-main-caption.damaged { left: auto; top: auto; width: min(38vw,320px); height: auto; min-height: 54px; margin: 8px 0 18px; padding: 7px 12px; text-align: center; transform: none; justify-self: center; background: rgba(242,226,197,.96); border: 1px solid #987045; }
  .study-main-caption .caption-title { font-size: 14px; }.study-main-caption .caption-state { margin-top: 4px; font-size: 16px; }
  .study-main-caption.clean { grid-column: 2; grid-row: 5; }.study-main-caption.damaged { grid-column: 3; grid-row: 5; }
  .study-status { grid-column: 2 / 4; grid-row: 6; grid-template-columns: 28px minmax(0,1fr); column-gap: 10px; margin: 0 0 22px; padding: 18px; border: 1px solid #a98a62; background: rgba(249,239,218,.95); }.study-status .status-seal { width: 28px; height: 28px; margin: 0; font-size: 15px; }.study-status .status-heading { font-size: 18px; }.study-status .status-rule { width: 28px; margin: 10px 0; }.study-status p { font-size: 14px; }
  .study-paths { grid-column: 2 / 4; grid-row: 7; margin: 20px 0; display: grid; grid-template-columns: repeat(2,1fr); gap: 10px; }.study-paths h3 { grid-column: 1 / -1; font-size: 20px; padding: 0 0 8px !important; transform:none; }.study-path { grid-column: auto !important; min-height: 88px; grid-template-rows: 40px 22px; padding: 8px; border: 1px solid #aa8960; background: rgba(244,232,207,.9); }.study-path-icon { width: 52px; height: 30px; }.study-path-label { font-size: 16px; }
  .study-specimens { --specimen-size:auto !important; grid-column: 2 / 4; grid-row: 8; margin: 22px 0; grid-template-columns: repeat(3,1fr); gap:20px; }.study-specimens::before { display:none; }.study-specimen { grid-template-rows:auto auto; }.study-specimen img { height:auto; aspect-ratio:1; }.study-specimen span { min-height:0; padding:6px; font-size:14px; }.study-specimen small { display:block; font-size:11px; }
  .study-collection, .study-notes, .portrait-audit { grid-column: 2 / 4; margin: 26px 0; padding: 18px; border: 1px solid #8c6540; background: rgba(68,42,24,.95); }
  .study-collection { grid-row: 9; }.study-notes { grid-row: 10; }.portrait-audit { grid-row: 11; }
  .study-collection { display: grid; grid-template-rows: auto repeat(5,48px); }.study-collection h3 { color: #f2dfbd; font-size: 22px; }.collection-drawer { grid-template-columns: 28px 1fr 34px; padding: 8px 12px; font-size: 14px; }.drawer-glyph { font-size: 18px; }.collection-drawer strong { font-size: 16px; }
  .study-notes { display: grid; grid-template-rows: auto repeat(6,minmax(58px,auto)); }.study-notes h3 { position: relative; inset: auto; height: auto; font-size: 22px; transform: none; }.study-note-wrap { position: relative !important; inset: auto !important; width: auto !important; height: auto !important; }.study-note-wrap::after { display: none; }.study-note { padding: 10px 12px; font-size: 14px; }.study-note small { font-size: 11px; }
  .portrait-audit { color: #f0dfbf; }.portrait-audit h3 { font-size: 22px; }.portrait-audit-link { width: min(220px,48vw); height: auto; margin: 15px 0 22px !important; }.portrait-audit-link img { width: 100%; height: auto; aspect-ratio: 1; margin: 0; border: 7px ridge #9c733f; box-sizing: border-box; }.portrait-audit-caption { position: static; height: auto; margin-top: 6px; color: #f0dfbf; font-size: 13px; transform: none; }.portrait-audit-stats { color: #eadabd; font-size: 15px; }
  .study-wall-art, .study-wall-emblem { display: none; }
  .study-scope { grid-column: 2 / 4; grid-row: 12; display: grid; grid-template-columns: repeat(2,1fr); gap: 12px; margin: 26px 0 55px; }.scope-book, .scope-plaque { position: relative; left: auto !important; top: auto !important; width: auto !important; height: auto; min-height: 56px; padding: 8px; color: #f0dfb4 !important; background: #194d3f; font-size: 15px; transform: none !important; }.scope-book.conditions { background: #6d2730; }.scope-book.cases { background: #7a572d; }.scope-book.eligible { background: #153043; }.scope-plaque { grid-column: 1 / -1; min-height: 34px; color: #47331d !important; background: #dec697; }
}
@media (max-width: 640px) {
  .museum-nav { padding-inline: 10px; }
  .museum-brand { font-size: 15px; }
  .museum-mark, .museum-seal { width: 32px; height: 32px; }
  .foyer-intro { padding-inline: 24px; }
  .foyer-intro h1 { width: 100%; margin-right: 0; transform: none; font-size: clamp(39px, 12vw, 56px); }
  .foyer-intro p { width: 100%; font-size: 17px; }
  .foyer-intro blockquote { width: 100%; font-size: 22px; }
  .scope-items { grid-template-columns: 1fr 1fr; }
  .museum-route { padding-left: 8px; padding-right: 8px; }
  .study-stage { grid-template-columns: 24px minmax(0,1fr) 24px; }
  .study-intro, .study-central-title, .study-status, .study-paths, .study-specimens,
  .study-collection, .study-notes, .portrait-audit, .study-scope { grid-column: 2; }
  .study-intro { grid-row: 2; padding-top: 38px; }.study-intro h1 { font-size: clamp(42px,13vw,58px); }.study-intro h2 { font-size: 24px; }.study-intro p, .study-intro .study-boundary { font-size: 15px; }
  .study-central-title { grid-row: 3; font-size: 30px; }
  .study-main-image.clean, .study-main-image.damaged { width: min(72vw,280px); }
  .study-main-image.clean { grid-column: 2; grid-row: 4; }.study-main-caption.clean { grid-column: 2; grid-row: 5; }
  .study-main-image.damaged { grid-column: 2; grid-row: 6; }.study-main-caption.damaged { grid-column: 2; grid-row: 7; }
  .study-status { grid-row: 8; }.study-paths { grid-row: 9; grid-template-columns: 1fr; }.study-paths h3 { grid-column: 1; }
  .study-specimens { grid-row: 10; grid-template-columns: repeat(2,1fr); gap: 16px; }
  .study-collection { grid-row: 11; }.study-notes { grid-row: 12; }.portrait-audit { grid-row: 13; }
  .study-scope { grid-row: 14; grid-template-columns: 1fr; }.study-scope .scope-plaque { grid-column: 1; }
}
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { transition: none !important; scroll-behavior: auto !important; } }
.st-key-study_control_bridge { display:none !important; }
</style>
""",
        unsafe_allow_html=True,
    )


def render_exhibition_foyer(package: DashboardPackage) -> None:
    """Render the approved Foyer as one live, evidence-bound museum artboard."""

    package.load_room("exhibition_foyer")
    opening = package.bootstrap["opening"]
    painting = package.load_painting(str(opening["painting_id"]))["painting"]
    hero_asset = bound_asset_id(
        package,
        display_id="foyer.hero.p001",
        room_id="exhibition_foyer",
    )
    hero_uri, hero_alt = local_asset_uri(
        package,
        hero_asset,
        profiles=("standard", "thumb"),
    )
    shell_uri = file_data_uri(str(FOYER_SHELL_PATH), FOYER_SHELL_SHA256)
    caption = (
        f"{html.escape(str(painting['painting_id']))} · "
        f"{html.escape(str(painting['title']))} ·<br>"
        f"{html.escape(str(painting['artist']))} · "
        f"{html.escape(str(painting['date_or_period']))}"
    )
    text = str(opening["text"])
    first_sentence, _, remainder = text.partition(". ")
    first_paragraph = first_sentence + ("." if not first_sentence.endswith(".") else "")
    second_paragraph = remainder or (
        "We compare images, measurements, stability and review warnings. "
        "A convincing image is not automatically historically correct."
    )
    scene = f"""
<main class="foyer-stage" aria-label="Exhibition Foyer">
  <img class="foyer-shell" src="{shell_uri}" alt="" aria-hidden="true">
  {navigation_html('exhibition_foyer')}
  <section class="foyer-intro" aria-labelledby="foyer-title">
    <h1 id="foyer-title">How should we<br>judge an AI-restored<br>painting?</h1>
    <p>{html.escape(first_paragraph)}</p>
    <p class="foyer-method-summary">{html.escape(second_paragraph)}</p>
    <blockquote>“{html.escape(str(opening['boundary']))}”</blockquote>
  </section>
  <figure class="hero-live">
    <img src="{hero_uri}" alt="{html.escape(hero_alt, quote=True)}" fetchpriority="high">
  </figure>
  <figcaption class="hero-caption">{caption}</figcaption>
  <div class="foyer-slogan">Same<br>paintings.<br>Different<br>methods.<br>Clearer<br>evidence.</div>
  <div class="foyer-actions" aria-label="Foyer actions">
    <a class="foyer-action" href="?room=exhibition_foyer&amp;tour=1" target="_self">
      <span class="action-medallion" aria-hidden="true">▶</span>
      <span>Take the guided tour<small>about 6 min</small></span><span class="action-arrow" aria-hidden="true">→</span>
    </a>
    <a class="foyer-action" href="#museum-route" target="_self">
      <span class="action-medallion" aria-hidden="true">⌁</span>
      <span>Explore freely</span><span class="action-arrow" aria-hidden="true">→</span>
    </a>
  </div>
  <a class="corridor-link" href="?room=study_design" target="_self">To<br>Study Design<b aria-hidden="true">→</b></a>
  <div class="corridor-motto">Art<br>meets<br>evidence<br>across<br>time</div>
  <div class="foyer-footer">
    {collection_html(package)}
    {route_html(package)}
  </div>
  {guided_tour_html(package)}
</main>
"""
    st.markdown(scene, unsafe_allow_html=True)


def inject_metric_theme() -> None:
    """Inject Batch 4 styles without changing approved Foyer/Study CSS."""

    st.markdown(
        r"""
<style>
.metric-stage { position:relative; width:min(100%,1672px); aspect-ratio:1672/941; margin:0 auto; overflow:hidden; background:#273641; container-type:inline-size; color:#f4eadc; font-family:var(--museum-serif); }
.metric-stage *, .metric-stage *::before, .metric-stage *::after { box-sizing:border-box; }
.metric-shell { position:absolute; z-index:0; inset:0; width:100%; height:100%; object-fit:fill; pointer-events:none; user-select:none; }
.metric-stage .museum-nav { z-index:40; }
.metric-stage .museum-nav a { text-decoration:none !important; font-family:var(--museum-serif); font-weight:400; }
.metric-stage .museum-brand { font-size:1.15cqw; line-height:.94; }
.metric-stage .museum-navlinks .room-link { font-size:.93cqw; }
.metric-intro { position:absolute; z-index:8; left:8.85%; top:16.25%; width:21.95%; color:#f5eadb; text-shadow:0 .07cqw .12cqw #111a; }
.metric-intro h1 { margin:0; font:500 2.62cqw/.97 var(--museum-serif); letter-spacing:-.07cqw; }
.metric-title-rule { display:block; width:3.1cqw; border-top:.12cqw solid #e8e0d3; margin:1.3cqw 0 1.15cqw; }
.metric-intro h2 { width:100%; margin:0 0 1.25cqw; font:500 1.36cqw/1.2 var(--museum-serif); }
.metric-stage .metric-intro p { margin:0 0 1.05cqw; font:400 1.05cqw/1.32 var(--museum-serif); }
.metric-intro blockquote { margin:1.1cqw 0 0; padding:.24cqw 0 .24cqw 1.0cqw; border-left:.22cqw solid #eaa53d; font:500 1.09cqw/1.28 var(--museum-serif); }
.metric-case { position:absolute; z-index:10; left:32.65%; top:12.28%; width:23.2%; height:5.2%; display:grid; place-items:center; padding:.25cqw .8cqw; color:#3b291a; text-align:center; }
.metric-case strong { min-width:0; font:italic 400 1.02cqw/1.2 Georgia, 'Times New Roman', serif; white-space:nowrap; text-shadow:0 .04cqw #f4dfb580; }
.metric-case strong span { font-size:inherit; }
.metric-chip { border:0; padding:.22cqw .34cqw; background:#6b4229cc; color:#f1dfbc; font:600 .64cqw/1 var(--museum-serif); cursor:default; }
.metric-control { position:absolute; z-index:12; top:13.15%; height:3.8%; border:.08cqw solid #c99543; background:#182b31d9; color:#f1e6d4; box-shadow:inset 0 0 0 .08cqw #172126,0 .12cqw .2cqw #0008; font:500 .86cqw/1 var(--museum-serif); }
.metric-control.change { left:57.02%; width:8.12%; }.metric-control.surprise { left:65.78%; width:7.52%; }
.metric-control:hover,.metric-control:focus-visible { color:#ffd36d; outline:.12cqw solid #f0b24e; outline-offset:.08cqw; }
.st-key-metric_painting_selector,.st-key-metric_surprise_button { position:absolute !important; z-index:70; margin:0 !important; }
.st-key-metric_painting_selector { left:57.02%; top:13.08%; width:8.15%; }
.st-key-metric_surprise_button { left:65.78%; top:13.08%; width:7.52%; }
.st-key-metric_painting_selector [data-baseweb="select"] > div { min-height:2.05cqw !important; height:2.05cqw !important; border:.08cqw solid #c99543 !important; border-radius:0 !important; background:#182b31e8 !important; box-shadow:inset 0 0 0 .06cqw #172126,0 .1cqw .2cqw #0008 !important; color:#f1e6d4 !important; }
.st-key-metric_painting_selector [data-baseweb="select"] span { color:#f1e6d4 !important; font:500 .66cqw/1 var(--museum-serif) !important; }
.st-key-metric_painting_selector [data-testid="stSelectbox"] { margin:0 !important; }
.st-key-metric_surprise_button button { width:100%; min-height:2.05cqw !important; height:2.05cqw !important; border:.08cqw solid #c99543 !important; border-radius:0 !important; background:#182b31e8 !important; color:#f1e6d4 !important; box-shadow:inset 0 0 0 .06cqw #172126,0 .1cqw .2cqw #0008 !important; font:500 .72cqw/1 var(--museum-serif) !important; padding:0 .35cqw !important; }
.st-key-metric_surprise_button button:hover { color:#ffd36d !important; border-color:#f0b24e !important; }
.metric-painting { position:absolute; z-index:5; left:34.33%; top:21.15%; width:26.91%; height:38.26%; margin:0; overflow:hidden; background:#242525; clip-path:polygon(0 0,100% 0,100% 100%,72.4% 100%,72.4% 96.4%,27.1% 96.4%,27.1% 100%,0 100%); }
.metric-painting > img { display:block; width:100%; height:100%; object-fit:cover; object-position:center; }
.metric-lens-live { position:absolute; z-index:9; left:44%; top:20%; width:44%; aspect-ratio:1; border-radius:50%; overflow:hidden; border:.33cqw ridge #bf7b23; box-shadow:0 0 0 .16cqw #26170d,0 .3cqw .55cqw #0009,inset 0 0 .9cqw #1c0d08; cursor:grab; touch-action:none; }
.metric-lens-live:active { cursor:grabbing; }
.metric-lens-live img { position:absolute; display:block; object-fit:cover; max-width:none; pointer-events:none; }
.metric-stage[data-metric-lens="pixel"] .metric-lens-live img,
.metric-stage[data-metric-lens="structure"] .metric-lens-live img,
.metric-stage[data-metric-lens="perceptual"] .metric-lens-live img,
.metric-stage[data-metric-lens="features"] .metric-lens-live img { opacity:0; }
.metric-lens-live::after { content:""; position:absolute; inset:0; border-radius:50%; background:radial-gradient(circle at 37% 28%,rgba(255,255,255,.23),transparent 35%,rgba(14,42,56,.13) 67%,rgba(3,12,19,.28)); pointer-events:none; }
.metric-drag-note { position:absolute; z-index:10; left:41.72%; top:58.05%; width:11.78%; height:2.95%; display:grid; place-items:center; color:#3d2818; font:500 .78cqw/1 var(--museum-serif); }
.metric-thumbs { position:absolute; z-index:8; left:32.95%; top:65.36%; width:29.55%; height:13.8%; display:grid; grid-template-columns:repeat(3,1fr); gap:4.3%; }
.metric-thumb { position:relative; display:grid; grid-template-rows:minmax(0,1fr) 2.2cqw; min-height:0; border:0; padding:0; background:transparent; color:#2f1d12; cursor:pointer; font-family:var(--museum-serif); }
.metric-thumb img { width:100%; height:100%; display:block; object-fit:cover; border:.18cqw ridge #9b632b; background:#242525; filter:saturate(.88); }
.metric-thumb span { min-width:0; display:grid; place-items:center; padding-top:.16cqw; font-size:.76cqw; line-height:1; }
.metric-thumb.active img { outline:.15cqw solid #e8b55d; outline-offset:-.22cqw; }
.metric-region-panel { position:absolute; z-index:10; left:64.0%; top:19.77%; width:10.95%; height:47.18%; color:#38291c; font-family:Georgia, 'Times New Roman', serif; }
.metric-region-panel h3 { position:absolute; left:.9cqw; top:1.0cqw; margin:0; padding:0 !important; font:400 1.04cqw/1 Georgia, 'Times New Roman', serif; transform:rotate(-.35deg); }
/* Seven hit areas sit between the shell's own ruled lines; no duplicate rules. */
.metric-regions { position:absolute; left:.54cqw; top:2.61cqw; width:calc(100% - 1.15cqw); height:18.4cqw; display:grid; grid-template-rows:repeat(7,minmax(0,1fr)); }
.metric-region { display:grid; grid-template-columns:2.5cqw minmax(0,1fr) .55cqw; align-items:center; gap:.48cqw; min-height:0; width:100%; border:0; padding:0 .28cqw; background:transparent; color:#38291c; font:400 .79cqw/1.08 Georgia, 'Times New Roman', serif; text-align:left; cursor:pointer; }
.metric-region > span:not(.metric-region-icon) { transform:rotate(-.35deg); }
.metric-region-icon { position:relative; display:block; width:2.5cqw; height:1.9cqw; overflow:hidden; background:#928c80; }
.metric-region-icon img { position:absolute; inset:0; display:block; width:100%; height:100%; object-fit:fill; filter:grayscale(1) sepia(.3); opacity:.65; }
.metric-region-icon img.metric-region-mask { mix-blend-mode:screen; opacity:.88; filter:sepia(.25); }
.metric-region:is([data-region="content"],[data-region="crop"],[data-region="outside"],[data-region="patches"]) .metric-region-icon { filter:grayscale(1); }
.metric-region:is([data-region="content"],[data-region="crop"],[data-region="outside"],[data-region="patches"]) .metric-region-mask { mix-blend-mode:multiply; opacity:.48; filter:grayscale(1); }
.metric-region[data-region="patches"] .metric-region-icon::after { content:""; position:absolute; inset:0; background:repeating-linear-gradient(0deg,transparent 0 30%,#55493899 31% 33%),repeating-linear-gradient(90deg,transparent 0 30%,#55493899 31% 33%); }
.metric-region::after { content:""; width:.48cqw; height:.48cqw; border-radius:50%; background:#456779; box-shadow:inset 0 0 0 .06cqw #243d49; }
.metric-region[data-role="primary"]::after { background:#ad710f; box-shadow:inset 0 0 0 .06cqw #6e4304; }
.metric-region.active { background:linear-gradient(90deg,#dca54b55,#eac78d88,#dca54b55); }
.metric-region:focus-visible { outline:.13cqw solid #78501b; outline-offset:-.12cqw; }
.metric-legend { position:absolute; left:.94cqw; top:21.75cqw; right:.65cqw; margin:0; display:grid; gap:.4cqw; font:400 .63cqw/1.15 Georgia, 'Times New Roman', serif; }
.metric-legend span::before { content:""; display:inline-block; width:.5cqw; height:.5cqw; margin-right:.4cqw; border-radius:50%; vertical-align:-.04cqw; background:#a96c0c; }
.metric-legend span:nth-child(2)::before { background:#456779; }.metric-legend span:nth-child(3)::before { content:"×"; width:.52cqw; height:.52cqw; border-radius:0; background:none; font:bold .9cqw/.5 var(--museum-serif); }
.metric-cabinet { position:absolute; z-index:10; left:78.83%; top:9.55%; width:15.5%; height:51.0%; color:#efdfc4; }
.metric-cabinet > h2 { position:absolute; top:.62cqw; left:.45cqw; right:.3cqw; margin:0; padding:0 !important; text-align:center; transform:skewY(-2.6deg); font:400 1.18cqw/1.05 Georgia, 'Times New Roman', serif; text-shadow:0 .07cqw .12cqw #160d08; }
.metric-cabinet > p { position:absolute; top:2.05cqw; left:.4cqw; right:.3cqw; margin:0; text-align:center; transform:skewY(-2.6deg); font:400 .71cqw/1.1 Georgia, 'Times New Roman', serif; }
.metric-lenses { position:absolute; left:0; top:3.36cqw; width:100%; display:flex; flex-direction:column; gap:0; }
/* Reuse the shell's actual drawer faces, borders and handles as an accordion.
   Source rectangles: closed (1318,146,259,48), open (1318,335,259,138). */
.metric-lens { position:relative; flex:none; height:2.87cqw; border:0; padding:0; background-image:var(--metric-drawer-shell); background-size:100cqw 56.28cqw; background-position:-78.83cqw -8.73cqw; background-repeat:no-repeat; color:#efdfc4; text-align:left; font-family:Georgia, 'Times New Roman', serif; }
.metric-lens-head { position:relative; width:100%; height:2.87cqw; display:grid; grid-template-columns:1.65cqw minmax(0,1fr); align-items:center; gap:1.0cqw; border:0; padding:.12cqw 2.8cqw .1cqw 1.05cqw; background:transparent; color:inherit; font:400 .88cqw/1.08 Georgia, 'Times New Roman', serif; text-align:left; cursor:pointer; }
.metric-lens-head > .lens-label { transform:translateY(.18cqw) rotate(-1.1deg); text-shadow:0 .045cqw .07cqw #160d08a0; }
.metric-lens-head .glyph { display:block; width:1.65cqw; height:1.65cqw; transform:translateY(.18cqw) rotate(-1.1deg); }
.metric-lens-head .glyph img { display:block; width:100%; height:100%; }
.metric-lens-head .drawer-grip { display:none; }
.metric-lens-body { display:none; height:5.38cqw; padding:.22cqw .9cqw .5cqw; overflow:auto; scrollbar-width:thin; scrollbar-color:#886439 transparent; color:#3b291a; background:transparent; box-shadow:none; font:400 .72cqw/1.16 Georgia, 'Times New Roman', serif; }
.metric-lens-body strong { display:block; margin-bottom:.48cqw; font-weight:400; }.metric-lens-body p { margin:0; }
.metric-lens.active { height:8.25cqw; background-position:-78.83cqw -20.04cqw; color:#3b291a; transform:skewY(-1.1deg); transform-origin:center; }
.metric-lens.active .metric-lens-head { background:transparent; color:inherit; box-shadow:none; }
.metric-lens.active .lens-label { transform:translateY(.18cqw); text-shadow:none; }
.metric-lens.active .glyph { transform:translateY(.18cqw); }
.metric-lens.active .glyph img { filter:brightness(.25) sepia(.65); }
.metric-lens.active .drawer-grip { display:block; position:absolute; right:1.08cqw; top:.94cqw; width:1.4cqw; height:1.0cqw; background-image:var(--metric-drawer-shell); background-size:100cqw 56.28cqw; background-position:-91.75cqw -9.58cqw; background-repeat:no-repeat; border:0; box-shadow:none; }
.metric-lens.active .metric-lens-body { display:block; }
.metric-lens-head:focus-visible { outline:.1cqw dotted #d4b374; outline-offset:-.4cqw; }
/* Pivot the complete original plaque at its right edge: left lower, right higher. */
.metric-plaque-mount { position:absolute; z-index:11; left:78.83%; top:61%; width:15.5%; height:16%; background:#38281b; }
.metric-plaque-mount::before { content:""; position:absolute; left:0; right:0; top:-.22cqw; height:.24cqw; background:#38281b; }
.metric-plaque-sheet { position:absolute; inset:0; background-size:100cqw 56.28cqw; background-position:-78.83cqw -34.33cqw; background-repeat:no-repeat; transform:skewY(-2deg); transform-origin:top right; }
.metric-plaque { position:absolute; z-index:11; left:.77cqw; top:.42cqw; width:14.05cqw; height:7.85cqw; padding:.2cqw .3cqw; overflow:auto; overscroll-behavior:contain; scrollbar-width:thin; scrollbar-color:#8b6c40 transparent; overflow-wrap:anywhere; color:#39291b; font:400 .7cqw/1.2 Georgia, 'Times New Roman', serif; }
.metric-conservation-study { position:absolute; left:4.15%; top:17.25%; width:2.85%; height:25.5%; object-fit:fill; transform:skewY(18deg); transform-origin:top left; mix-blend-mode:multiply; pointer-events:none; }
.metric-dune-cover { position:absolute; left:91.3%; top:84.7%; width:7.7%; height:11.5%; object-fit:fill; transform:skewY(14deg) skewX(-1.5deg); transform-origin:top left; pointer-events:none; }
.metric-arrakis-art { position:absolute; left:96.05%; top:15.7%; width:3.75%; height:23%; object-fit:fill; transform:skewY(-16deg); transform-origin:top left; filter:saturate(.72) brightness(.91); pointer-events:none; }
.metric-plaque h3 { margin:0 0 .35cqw; padding:0 !important; font:400 .84cqw/1.12 Georgia, 'Times New Roman', serif; }.metric-plaque p { margin:.3cqw 0; }
.metric-plaque .tone-blue { color:#254e96; }.metric-plaque .tone-red { color:#a13126; }.metric-plaque .tone-pale { color:#76634a; }.metric-plaque .tone-dark { color:#211b19; }.metric-plaque .tone-bright { color:#8a5300; }
.metric-plaque [class^="tone-"] { font-weight:700; }
.metric-plaque details { margin-top:.35cqw; }
.metric-plaque summary { cursor:pointer; color:#6a4929; font-style:italic; }
.metric-plaque summary:focus-visible { outline:1px dotted #654a29; }
.metric-ledger { position:absolute; z-index:12; inset:0; color:#443321; pointer-events:none; font-family:Georgia, 'Times New Roman', serif; }
.metric-ledger-page { position:absolute; left:9.0%; top:74.65%; width:13.8%; transform:rotate(-4.5deg) skewX(8deg); transform-origin:top left; text-shadow:0 .035cqw #f8e4c180; }
.metric-ledger h2 { margin:0 0 .7cqw; padding:0 !important; text-align:left; white-space:nowrap; font:400 .86cqw/1.1 Georgia, 'Times New Roman', serif; }
.metric-ledger ul { list-style:none; margin:0; padding:0; }
.metric-ledger li { white-space:nowrap; }
.metric-ledger li b { display:inline-block; min-width:1.35cqw; font-weight:400; font-size:1.18cqw; }
.metric-ledger a { position:absolute; left:25.05%; top:88.15%; width:9.0%; height:2.7%; display:grid; place-items:center; border:.06cqw solid #705738a0; border-radius:.1cqw; color:#493522 !important; text-decoration:none !important; font:.76cqw/1 Georgia, 'Times New Roman', serif; transform:rotate(-6deg) skewX(10deg); pointer-events:auto; }
.metric-ledger a:focus-visible { outline:2px solid #67471f; outline-offset:2px; }
.metric-ledger-leaf { position:absolute; left:26.15%; top:80.05%; width:5.3%; height:7.3%; object-fit:contain; opacity:.68; mix-blend-mode:multiply; transform:rotate(-6deg) skewX(10deg); }
.metric-ledger-note { position:absolute; z-index:13; left:23.72%; top:74.16%; width:7.55%; height:3.65%; display:flex; align-items:center; justify-content:center; color:#49341e; text-align:center; transform:matrix(1,-.083,.29,1,0,0); transform-origin:center; font:400 .76cqw/1.12 Georgia, 'Times New Roman', serif; }
.metric-interpretation { position:absolute; z-index:12; left:73.1%; top:80.45%; width:11.55%; height:12.9%; display:flex; flex-direction:column; justify-content:center; padding:.3cqw .2cqw; color:#443020; text-align:center; transform:rotate(3deg) skewX(1deg); transform-origin:center; text-shadow:0 .035cqw #fae4bd70; }
.metric-interpretation strong { display:block; margin:0 0 .35cqw; font:400 .86cqw/1.05 Georgia, 'Times New Roman', serif; }
.metric-stage .metric-interpretation p { margin:0; font:400 .64cqw/1.16 Georgia, 'Times New Roman', serif !important; }
.metric-side-book { position:absolute; z-index:10; left:4.42%; top:63.4%; width:6.25%; color:#d19b48; text-align:center; transform:rotate(1deg); font:600 .71cqw/1.35 var(--museum-serif); text-shadow:0 .08cqw .08cqw #000; }
.metric-picker-popover { width:min(420px,88vw); padding:16px; border:1px solid #b88842; background:#efe0c6; color:#2d2118; box-shadow:0 14px 42px #0009; font-family:var(--museum-serif); }.metric-picker-popover::backdrop { background:#07141377; }.metric-picker-popover label { display:block; margin-bottom:8px; font-weight:700; }.metric-picker-popover input { width:100%; padding:8px; border:1px solid #8f6a42; background:#fff9ed; }.metric-picker-popover p { font-size:13px; }.metric-picker-popover button { padding:7px 12px; border:1px solid #75502f; background:#163a38; color:#f4eadc; }
@media (max-width:780px) {
  .metric-stage { width:100%; min-width:760px; margin:0; }
  [data-testid="stMain"] { overflow-x:auto !important; }
}
.st-key-metric_control_bridge { display:none !important; }
.metric-painting > img { object-fit:fill; }
.metric-lens-live canvas { width:100%; height:100%; display:block; }
.metric-lens-live[hidden] { display:none !important; }
.metric-lens-live::after { background:none; }
.metric-lens-live:focus-visible { outline:2px solid #ffe0a0; outline-offset:3px; }
.metric-patch-outline { position:absolute; z-index:8; border:1px dashed #ffdb81; pointer-events:none; }
.metric-patch-outline[hidden] { display:none !important; }
.metric-loupe-readout { position:static; margin:.3cqw 0; color:#513820; font:italic .64cqw/1.2 Georgia, 'Times New Roman', serif; }
.metric-sr-only { position:absolute; width:1px; height:1px; padding:0; overflow:hidden; clip-path:inset(50%); white-space:nowrap; }
.metric-region:disabled { cursor:not-allowed; opacity:.48; text-decoration:line-through; }
.metric-region:disabled::after { content:'×'; background:none; box-shadow:none; color:#632a24; font-size:.9cqw; }
.metric-region.recommended { outline:.1cqw dashed #946521; outline-offset:-.2cqw; }
.metric-selection-notice { position:absolute; left:.9cqw; right:.8cqw; top:24.85cqw; max-height:1.35cqw; overflow:auto; font:.58cqw/1.12 var(--museum-serif); margin:0; color:#542517; }
.metric-stage .metric-lens-body p { font:400 .72cqw/1.16 Georgia, 'Times New Roman', serif !important; }
.metric-stage .metric-plaque p { font:400 .69cqw/1.2 Georgia, 'Times New Roman', serif !important; }
.metric-stage .metric-plaque p.quiet { font-size:.63cqw !important; }
.metric-stage .metric-selection-notice { font-size:.62cqw !important; }
.metric-stage .metric-ledger li { font:400 .9cqw/1.65 Georgia, 'Times New Roman', serif !important; }
.metric-stage .museum-mark img { width:78%; height:78%; display:block; }
.metric-stage .museum-search img { width:2.05cqw; height:2.05cqw; display:block; }
/* The shell supplies the real brass-edged plates; controls supply ink only. */
.st-key-metric_painting_selector .react-aria-ComboBox [role="group"],
.st-key-metric_painting_selector [data-baseweb="select"] > div,
.st-key-metric_surprise_button button { min-height:0 !important; height:calc(var(--metric-unit, 1vw) * 1.8) !important; background:transparent !important; border:0 !important; border-radius:0 !important; box-shadow:none !important; }
.st-key-metric_painting_selector input[role="combobox"] { color:#edd6a6 !important; background:transparent !important; min-width:0 !important; padding:0 calc(var(--metric-unit, 1vw) * .4) !important; text-align:center; font:italic 400 calc(var(--metric-unit, 1vw) * .8)/1.2 Georgia, 'Times New Roman', serif !important; }
.st-key-metric_painting_selector button { color:#dbc092 !important; background:transparent !important; border:0 !important; width:calc(var(--metric-unit, 1vw) * 1.1) !important; padding:0 !important; }
.st-key-metric_painting_selector button svg { width:calc(var(--metric-unit, 1vw) * .85); height:calc(var(--metric-unit, 1vw) * .85); }
.st-key-metric_surprise_button button { position:absolute !important; inset:0 !important; display:flex !important; align-items:center !important; justify-content:center !important; }
.st-key-metric_surprise_button button p { margin:0 !important; color:#edd6a6 !important; font:italic 400 calc(var(--metric-unit, 1vw) * .85)/1.2 Georgia, 'Times New Roman', serif !important; }
.st-key-metric_painting_selector:focus-within, .st-key-metric_surprise_button button:focus-visible { outline:1px dotted #ebcc91 !important; outline-offset:-3px; }
body:has(.metric-stage) [data-testid="stSelectboxVirtualDropdown"]:has([aria-label="Change painting"]) { background:#e2ccaa !important; border:1px solid #75512c !important; border-radius:2px !important; min-width:240px; box-shadow:0 5px 15px #100c08a0 !important; }
body:has(.metric-stage) [role="listbox"][aria-label="Change painting"],
body:has(.metric-stage) [role="listbox"][aria-label="Change painting"] [role="option"] { background:#e2ccaa !important; color:#352416 !important; font:14px/1.4 Georgia, 'Times New Roman', serif !important; }
body:has(.metric-stage) [role="listbox"][aria-label="Change painting"] [role="option"]:is(:hover,[data-focused],[aria-selected="true"]) { background:#b99463 !important; color:#21170f !important; }
</style>
""",
        unsafe_allow_html=True,
    )


@st.fragment
def render_metric_framework(package: DashboardPackage) -> None:
    """Render a package-driven Metric Framework without full-page selection reloads."""

    inject_metric_theme()
    room = package.load_room("metric_framework")
    if len(room) != 12:
        raise DashboardContractError("Metric Framework must contain exactly 12 records")
    opening = room_catalogue_record(package, "metric_framework")
    registered = set(package.bindings_for(room_id="metric_framework")["payload_ref"].astype(str))
    for asset_id in METRIC_OPENING_ASSETS.values():
        if f"asset:{asset_id}" not in registered:
            raise DashboardContractError(f"Metric opening asset is not registered: {asset_id}")

    lookup = package.painting_lookup.copy()
    painting_ids = tuple(lookup["painting_id"].astype(str))
    painting_labels = {
        str(row.painting_id): f"{row.painting_id} · {row.title}"
        for row in lookup.itertuples(index=False)
    }
    if st.session_state.get("metric_painting_selector") not in set(painting_ids):
        requested = scalar_query("metric_painting", "p018")
        st.session_state["metric_painting_selector"] = requested if requested in painting_ids else "p018"
    painting_id = st.selectbox(
        "Change painting",
        painting_ids,
        format_func=painting_labels.__getitem__,
        key="metric_painting_selector",
        label_visibility="collapsed",
        on_change=remember_metric_painting,
    )
    painting_payload = package.load_painting(str(painting_id))
    painting = painting_payload["painting"]

    # This room teaches how region and metric choice change the reading of one
    # stable exhibit. Case/model comparisons belong to Model Gallery and Case
    # Explorer, so the approved Metric Framework does not expose those controls.
    case_id = f"canonical__{painting_id}__mixed_damage"
    case_matches = [
        row for row in painting_payload["cases"]
        if str(row["case_id"]) == case_id
    ]
    if len(case_matches) != 1:
        raise DashboardContractError(
            f"Metric Framework requires exactly one canonical mixed-damage case for {painting_id}"
        )
    case = case_matches[0]

    expected_candidate_id = f"candidate__lama__{case_id}__c00"
    candidate_matches = [
        row for row in painting_payload["candidates"]
        if str(row["candidate_id"]) == expected_candidate_id
        and str(row["case_id"]) == case_id
        and str(row["model_id"]) == "lama"
        and str(row.get("availability_state", "")).startswith("available")
    ]
    if len(candidate_matches) != 1:
        raise DashboardContractError(
            f"Metric Framework requires exactly one canonical LaMa candidate for {painting_id}"
        )
    candidate = candidate_matches[0]
    candidate_id = expected_candidate_id
    st.button(
        "Surprise me",
        key="metric_surprise_button",
        on_click=advance_metric_painting,
        args=(painting_ids,),
    )

    import importlib
    from restoration_eval import metric_inspection_view
    # Streamlit reruns the room while imported helper modules can remain cached.
    # Reload this small presentation-only module; never reload scientific models.
    metric_inspection_view = importlib.reload(metric_inspection_view)
    load_inspection = metric_inspection_view.load_inspection
    from restoration_eval.metric_inspection import LENSES, REGIONS
    routes = candidate["asset_routes"]
    try:
        evidence = load_inspection(PROJECT_ROOT, str(painting_id))
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Inspection evidence is unavailable for {painting_id}: {exc}")
        return
    if evidence["candidate_id"] != candidate_id or evidence["case_id"] != case_id:
        raise DashboardContractError("Inspection evidence belongs to a different restoration")
    uris = {
        "reference": recorded_metric_image_uri(str(painting["clean_image_path"])),
        "damaged": recorded_metric_image_uri(str(case["input_image_path"])),
        "restored": recorded_metric_image_uri(str(routes["restored"][0])),
    }
    evidence["views"] = uris
    shell_uri = file_data_uri(str(METRIC_SHELL_PATH), METRIC_SHELL_SHA256)
    # Use a direct image declaration: the full-resolution data URI is too large
    # for Chromium's custom-property token limit. All states share one image.
    st.markdown(
        f"<style>.metric-cabinet .metric-lens, .metric-cabinet .metric-lens.active .drawer-grip, .metric-plaque-sheet {{ background-image: url('{shell_uri}'); }}</style>",
        unsafe_allow_html=True,
    )
    # Reference-style pictograms are code-native line work, not font glyphs.
    lens_icon_paths = {
        "pixel": '<path d="M2 2h8v8H2zM14 2h8v8h-8zM2 14h8v8H2zM14 14h8v8h-8z"/><path d="M6 2v8M2 6h8M18 14v8M14 18h8"/>',
        "structure": '<path d="M2 6c4-7 7 7 12 0s6 2 8-2M2 12c4-7 7 7 12 0s6 2 8-2M2 18c4-7 7 7 12 0s6 2 8-2"/>',
        "perceptual": '<path d="M1 12Q12-2 23 12Q12 26 1 12Z"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1"/>',
        "features": '<path d="m4 7 8-4 8 6-3 11-12-2L4 7l13 13M12 3l5 17M4 7l16 2L5 18"/><circle cx="4" cy="7" r="2"/><circle cx="12" cy="3" r="2"/><circle cx="20" cy="9" r="2"/><circle cx="17" cy="20" r="2"/><circle cx="5" cy="18" r="2"/>',
        "spatial": '<path d="m3 3 7-2 5 4 6-2v18l-7 2-5-4-6 2ZM10 2l-1 17M15 5l-1 17M6 8l3 3 3-2 5 6M14 15h3v-3"/>',
        "local": '<path d="m1 6 5-5m-5 11L12 1M1 18 18 1M3 22 22 3M9 23 23 9m-8 14 8-8M1 9l14 14M1 3l20 20M6 1l17 17M12 1l11 11m-5-11 5 5"/>',
        "semantic": '<path d="M6 3h12M21 6v12M18 21H6M3 18V6M7 7h10v10H7z"/><path d="M1 1h4v4H1zM19 1h4v4h-4zM1 19h4v4H1zM19 19h4v4h-4z"/>',
    }
    lens_icons = {
        key: "data:image/svg+xml;base64," + base64.b64encode(
            ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
             'stroke="#ead3a4" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">'
             + paths + '</svg>').encode()
        ).decode() for key, paths in lens_icon_paths.items()
    }
    lens_rows = [
        f'''<section class="metric-lens{' active' if key == 'spatial' else ''}" data-lens="{key}">
<button class="metric-lens-head" type="button" aria-expanded="{'true' if key == 'spatial' else 'false'}"><span class="glyph" aria-hidden="true"><img src="{lens_icons[key]}" alt=""></span><span class="lens-label">{html.escape(spec[0])}</span><span class="drawer-grip" aria-hidden="true"></span></button>
<div class="metric-lens-body"><strong>{html.escape(spec[1])}</strong><p>{html.escape(spec[2])}</p></div></section>'''
        for key, spec in LENSES.items()
    ]
    region_rows = [
        f'<button class="metric-region" type="button" data-region="{key}" aria-pressed="false"><span class="metric-region-icon" aria-hidden="true"><img src="{uris["reference"]}" alt="">'
        + (f'<img class="metric-region-mask" src="{evidence["regions"][key]["uri"]}" alt="">' if key != 'whole' else '')
        + f'</span><span>{html.escape(spec[0])}</span></button><span class="metric-sr-only" id="metric-reason-{key}"></span>'
        for key, spec in REGIONS.items()
    ]
    title = html.escape(str(painting["title"]), quote=True)
    ledger_leaf_uri = "data:image/svg+xml;base64," + base64.b64encode(
        (PROJECT_ROOT / "streamlit_assets/ornaments/ledger_botanical.svg").read_bytes()
    ).decode()
    conservation_study_uri = "data:image/svg+xml;base64," + base64.b64encode(
        (PROJECT_ROOT / "streamlit_assets/ornaments/conservation_study.svg").read_bytes()
    ).decode()
    dune_cover_uri = "data:image/svg+xml;base64," + base64.b64encode(
        (PROJECT_ROOT / "streamlit_assets/ornaments/dune_archive_cover.svg").read_bytes()
    ).decode()
    arrakis_art_uri = "data:image/png;base64," + base64.b64encode(
        (PROJECT_ROOT / "streamlit_assets/ornaments/arrakis_desert.png").read_bytes()
    ).decode()
    scene = f'''
<main class="metric-stage" aria-label="Metric Framework" data-metric-lens="spatial" data-metric-region="damaged" data-painting-id="{painting_id}" data-case-id="{case_id}" data-candidate-id="{candidate_id}" data-content-bbox="{html.escape(json.dumps(evidence['content_bbox']), quote=True)}" data-load-state="initializing">
<span class="build-marker" data-build="{APP_BUILD}" data-metric-build="{METRIC_BUILD}" data-loader-version="{evidence.get('loader_version', 'legacy')}" aria-hidden="true"></span><img class="metric-shell" src="{shell_uri}" alt="" aria-hidden="true">{navigation_html('metric_framework')}
<img class="metric-conservation-study" src="{conservation_study_uri}" alt="" aria-hidden="true">
<img class="metric-dune-cover" src="{dune_cover_uri}" alt="" aria-hidden="true">
<img class="metric-arrakis-art" src="{arrakis_art_uri}" alt="" aria-hidden="true">
<section class="metric-intro" aria-labelledby="metric-title"><h1 id="metric-title">Metric Framework</h1><span class="metric-title-rule"></span><h2>{html.escape(str(opening['question']))}</h2><p>{html.escape(str(opening['introduction']))}</p><blockquote>{html.escape(str(opening['boundary']))}</blockquote></section>
<section class="metric-case" aria-label="Selected evidence identity"><strong>Featured case: <span>{painting_id} · Mixed damage · LaMa</span></strong></section>
<figure class="metric-painting" aria-label="Painting with draggable diagnostic lens"><img src="{uris['restored']}" alt="{title} restored by LaMa"><div class="metric-lens-live" tabindex="0" role="group" aria-label="Inspection lens. Drag or use arrow keys." hidden><canvas aria-hidden="true"></canvas></div></figure>
<div class="metric-drag-note">Drag to inspect · 1.65×</div>
<section class="metric-thumbs" aria-label="Selected image states"><button class="metric-thumb" type="button" data-view="reference" aria-pressed="false"><img src="{uris['reference']}" alt="{title} reference"><span>Reference</span></button><button class="metric-thumb" type="button" data-view="damaged" aria-pressed="false"><img src="{uris['damaged']}" alt="{title} damaged"><span>Damaged</span></button><button class="metric-thumb active" type="button" data-view="restored" aria-pressed="true"><img src="{uris['restored']}" alt="{title} restored"><span>Restored</span></button></section>
<section class="metric-region-panel" aria-label="Select a region"><h3>Select a region</h3><div class="metric-regions">{''.join(region_rows)}</div><div class="metric-legend"><span>Primary — headline evidence</span><span>Diagnostic — supporting evidence</span><span>Prohibited — not valid here</span></div><p class="metric-selection-notice" role="status" aria-live="polite"></p></section>
<aside class="metric-cabinet" aria-label="Choose an evidence lens"><h2>Choose an evidence lens</h2><p>Select a lens to see its metrics.</p><div class="metric-lenses">{''.join(lens_rows)}</div></aside>
<div class="metric-plaque-mount"><div class="metric-plaque-sheet"><section class="metric-plaque" aria-live="polite"><h3>Loading inspection evidence…</h3><div class="metric-loupe-readout" aria-live="off">Loading evidence…</div></section></div></div>
<section class="metric-ledger" aria-label="Restoration Metric Policy Ledger"><div class="metric-ledger-page"><h2>Restoration Metric Policy Ledger</h2><ul><li><b>7</b> evidence lenses · 7 regions</li><li><b>37</b> spatial inspection pairs</li><li><b>12</b> incompatible pairs disabled</li><li><b>13</b> underlying metric families</li></ul></div><img class="metric-ledger-leaf" src="{ledger_leaf_uri}" alt="" aria-hidden="true"><a href="?room=research_archive" target="_self">Open full policy ledger →</a></section><div class="metric-ledger-note"><span>11 quality anchors<br>kept separate</span></div>
<aside class="metric-interpretation"><strong>Same restoration.<br>Different question.<br>Sometimes a different conclusion.</strong><p>That is why we do not average everything into one universal score.</p></aside><div class="metric-side-book">MEASURE<br>COMPARE<br>UNDERSTAND<br>PRESERVE</div>
</main>'''
    import re
    # st.html sanitizes inline SVG. Preserve the existing navigation artwork as
    # an SVG image without changing the approved shared navigation function.
    def isolated_navigation_svg(match):
        svg = match.group(0)
        stroke = "#a6232c" if '0 0 40 40' in svg else "#0085bd"
        svg = svg.replace('<svg ', f'<svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="{stroke}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" ', 1)
        return '<img alt="" src="data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode() + '">'
    scene = re.sub(r"<svg\b.*?</svg>", isolated_navigation_svg, scene, flags=re.DOTALL)
    from restoration_eval.room_runtime import room_html, room_controller
    revision = room_html(scene)
    controller = (PROJECT_ROOT / "streamlit_assets/metric_controller.js").read_text(encoding="utf-8")
    serialized = json.dumps(evidence, ensure_ascii=True).replace("</", "<\\/")
    import streamlit.components.v1 as components
    room_controller(controller.replace("__METRIC_PAYLOAD__", serialized), revision)


def render_pending_room(package: DashboardPackage, room_id: str) -> None:
    package.load_room(room_id)
    label = ROOM_LABELS[room_id]
    batch = ROOM_BATCHES.get(room_id, 7)
    if room_id == "focused_portrait_review":
        return_room = scalar_query("return_room", "trustworthiness")
        if return_room not in {"study_design", "trustworthiness", "case_explorer"}:
            raise DashboardContractError(
                f"Invalid Focused Portrait Review return room: {return_room}"
            )
        return_label = ROOM_LABELS[return_room]
        st.markdown(
            f"""
<main class="pending-shell" data-child-room="focused_portrait_review" data-return-room="{return_room}">
  {navigation_html('trustworthiness')}
  <section class="pending-room"><div class="plaque">
    <h1>Focused Portrait Review</h1>
    <p>This is the one shared D02 mini study room. Study Design, Trustworthiness and Case Explorer all enter this same evidence partition.</p>
    <p>The full interactive room is scheduled with the Trustworthiness implementation; no duplicate portrait-audit room is being created here.</p>
    <p><a href="?room={return_room}" target="_self">Return to {html.escape(return_label)} →</a></p>
  </div></section>
</main>
""",
            unsafe_allow_html=True,
        )
        return
    st.markdown(
        f"""
<main class="pending-shell">
  {navigation_html(room_id)}
  <section class="pending-room"><div class="plaque">
    <h1>{html.escape(label)}</h1>
    <p>This approved room is deliberately closed while Notebook 35 Batch {batch} translates it into live, evidence-bound components.</p>
    <p><a href="?room=exhibition_foyer" target="_self">Return to the Exhibition Foyer →</a></p>
  </div></section>
</main>
""",
        unsafe_allow_html=True,
    )


def main() -> None:
    config, package = load_application()
    inject_theme()
    room_id = active_room(config)
    from restoration_eval.room_runtime import install_room_navigation
    install_room_navigation(room_id)
    if room_id == "exhibition_foyer":
        render_exhibition_foyer(package)
    elif room_id == "study_design":
        render_study_design(package)
    elif room_id == "metric_framework":
        render_metric_framework(package)
    elif room_id == "model_gallery":
        import importlib
        from restoration_eval import model_gallery as gallery_data
        from restoration_eval import model_gallery_view as gallery_view
        # This room lives in imported modules. Some local Streamlit launchers do
        # not watch newly imported files; refresh only when their sources change.
        signature = tuple(Path(module.__file__).stat().st_mtime_ns
                          for module in (gallery_data, gallery_view))
        if getattr(gallery_view, "_loaded_source_signature", None) != signature:
            importlib.reload(gallery_data)
            importlib.reload(gallery_view)
            gallery_view._loaded_source_signature = signature
        gallery_view.render_model_gallery(package, navigation_html("model_gallery"))
    elif room_id == "stability_lab":
        import importlib
        from restoration_eval import stability_lab as stability_data
        from restoration_eval import stability_lab_view as stability_view
        signature = tuple(Path(module.__file__).stat().st_mtime_ns
                          for module in (stability_data, stability_view))
        if getattr(stability_view, "_loaded_source_signature", None) != signature:
            importlib.reload(stability_data)
            importlib.reload(stability_view)
            stability_view._loaded_source_signature = signature
        stability_view.render_stability_lab(package, navigation_html("stability_lab"))
    elif room_id == "trustworthiness":
        import importlib
        from restoration_eval import trustworthiness as trust_data
        from restoration_eval import trustworthiness_view as trust_view
        signature = tuple(Path(module.__file__).stat().st_mtime_ns
                          for module in (trust_data, trust_view))
        if getattr(trust_view, "_loaded_source_signature", None) != signature:
            importlib.reload(trust_data)
            importlib.reload(trust_view)
            trust_view._loaded_source_signature = signature
        trust_view.render_trustworthiness(package, navigation_html("trustworthiness"))
    elif room_id == "case_explorer":
        import importlib
        from restoration_eval import case_explorer as case_data
        from restoration_eval import case_explorer_view as case_view
        signature = tuple(Path(module.__file__).stat().st_mtime_ns
                          for module in (case_data, case_view))
        if getattr(case_view, "_loaded_source_signature", None) != signature:
            importlib.reload(case_data)
            importlib.reload(case_view)
            case_view._loaded_source_signature = signature
        case_view.render_case_explorer(package, navigation_html("case_explorer"))
    elif room_id == "focused_portrait_review":
        import importlib
        from restoration_eval import focused_portrait as portrait_data
        from restoration_eval import focused_portrait_view as portrait_view
        signature = tuple(Path(module.__file__).stat().st_mtime_ns
                          for module in (portrait_data, portrait_view))
        if getattr(portrait_view, "_loaded_source_signature", None) != signature:
            importlib.reload(portrait_data)
            importlib.reload(portrait_view)
            portrait_view._loaded_source_signature = signature
        portrait_view.render_focused_portrait(package, navigation_html("trustworthiness"))
    else:
        render_pending_room(package, room_id)


if __name__ == "__main__":
    main()
