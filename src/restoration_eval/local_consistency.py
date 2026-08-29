"""Model-agnostic local texture, colour, and seam diagnostics.

Notebook 17 uses this module for canonical computation. The implementation
keeps proxy evidence explicit: texture and brushstroke-like measurements are
image-processing diagnostics, not authentication, semantic recognition, or
conservation approval. Local SSIM is computed as a valid rectangular
full-frame map before boundary pixels are summarized; sparse-pixel SSIM is
never computed directly.
"""

from __future__ import annotations

import hashlib
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import matplotlib.pyplot as plt
import cv2
import numpy as np
import pandas as pd
import yaml
from matplotlib import colormaps
from matplotlib.colors import Normalize, TwoSlopeNorm
from PIL import Image, ImageDraw
from scipy.ndimage import laplace, sobel, uniform_filter
from skimage.color import deltaE_ciede2000, rgb2gray, rgb2lab
from skimage.feature import graycomatrix, graycoprops, local_binary_pattern
from skimage.metrics import structural_similarity

from .regions import Region, build_standard_regions, effect_support_region
from .schemas import (
    LOCAL_CONSISTENCY_COLUMNS,
    LOCAL_CONSISTENCY_MAP_MANIFEST_COLUMNS,
    LOCAL_CONSISTENCY_MAP_MANIFEST_SCHEMA,
    LOCAL_CONSISTENCY_SCHEMA,
    validate_dataframe,
)


LOCAL_CONSISTENCY_MODULE_NAME = "restoration_eval.local_consistency"
LOCAL_CONSISTENCY_MODULE_VERSION = "1.0.3"
LOCAL_CONSISTENCY_METRIC_VERSION = "local_consistency_metrics.v1"
LOCAL_CONSISTENCY_MAP_VERSION = "local_consistency_map_images.v1"
LOCAL_CONSISTENCY_RENDERER_VERSION = "local_consistency_map_renderer.v1"
MAP_TYPES = ("texture", "colour", "seam")
ProgressCallback = Callable[[str], None]


@dataclass(frozen=True)
class LocalConsistencyRunResult:
    """Canonical metric execution result with resume counts."""

    metrics: pd.DataFrame
    completed_candidates: int
    reused_candidates: int


@dataclass(frozen=True)
class LocalConsistencyMapRunResult:
    """Canonical map execution result with resume counts."""

    map_images: pd.DataFrame
    completed_candidates: int
    reused_candidates: int


def load_local_consistency_config(path: str | Path) -> dict[str, Any]:
    """Load and validate the Notebook 17 configuration."""

    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Local-consistency config not found: {config_path}")
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Local-consistency configuration must be a mapping")
    if payload.get("config_schema_version") != "local_consistency_config.v1":
        raise ValueError("Unsupported local-consistency configuration schema")
    config = payload.get("local_consistency")
    if not isinstance(config, dict):
        raise ValueError("Configuration is missing local_consistency")
    required = {
        "notebook_id", "notebook_stem", "metric_schema_version",
        "metric_version", "map_manifest_version", "map_renderer_version",
        "inputs", "output", "colour_policy", "texture_policy", "regions",
        "metric_plan", "visualization", "execution", "representative_panels",
        "evidence_policy", "expected_counts", "known_limitations",
    }
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(f"local_consistency is missing keys: {missing}")
    if config["metric_version"] != LOCAL_CONSISTENCY_METRIC_VERSION:
        raise ValueError("Configured metric version disagrees with the helper")
    if config["map_manifest_version"] != LOCAL_CONSISTENCY_MAP_VERSION:
        raise ValueError("Configured map-manifest version disagrees with the helper")
    if config["map_renderer_version"] != LOCAL_CONSISTENCY_RENDERER_VERSION:
        raise ValueError("Configured renderer version disagrees with the helper")
    if tuple(config["visualization"]["map_types"]) != MAP_TYPES:
        raise ValueError(f"Map types must be {MAP_TYPES}")
    regions = config["regions"]
    if int(regions["outside_ring_inner_offset_pixels"]) != int(
        regions["boundary_width_pixels"]
    ):
        raise ValueError(
            "Outside-ring inner offset must equal the canonical boundary width"
        )
    texture = config["texture_policy"]
    if int(texture["local_window_pixels"]) < 3 or int(
        texture["local_window_pixels"]
    ) % 2 == 0:
        raise ValueError("local_window_pixels must be an odd integer of at least 3")
    for key in ("progress_interval_candidates", "checkpoint_interval_candidates"):
        if int(config["execution"][key]) <= 0:
            raise ValueError(f"{key} must be positive")
    counts = config["expected_counts"]
    if int(counts["texture_rows_total"]) != (
        int(counts["texture_descriptor_rows"]) + int(counts["texture_map_rows"])
    ):
        raise ValueError("Texture row-count components do not sum")
    if int(counts["total_metric_rows"]) != (
        int(counts["texture_rows_total"])
        + int(counts["colour_rows"])
        + int(counts["seam_rows"])
    ):
        raise ValueError("Metric-family row counts do not sum")
    if int(counts["candidate_map_images"]) != (
        int(counts["mapped_primary_candidates"]) * len(MAP_TYPES)
    ):
        raise ValueError("Candidate map count disagrees with mapped population")
    return payload


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    return config["local_consistency"]


def resolve_path(path_value: str | Path, project_root: str | Path) -> Path:
    """Resolve one project-relative or absolute path."""

    path = Path(str(path_value).strip())
    return path if path.is_absolute() else Path(project_root) / path


def project_relative_path(path: str | Path, project_root: str | Path) -> str:
    """Return a normalized repository-relative path."""

    return Path(path).resolve().relative_to(Path(project_root).resolve()).as_posix()


def sha256_path(path: str | Path) -> str:
    """Return the SHA-256 digest of one file."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_dataframe_atomic(
    dataframe: pd.DataFrame,
    path: str | Path,
    *,
    attempts: int = 8,
    retry_delay_seconds: float = 0.25,
) -> None:
    """Write CSV atomically with bounded Windows replacement retries."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + f".{os.getpid()}.tmp")
    dataframe.to_csv(temporary, index=False)
    last_error: OSError | None = None
    delay = float(retry_delay_seconds)
    for attempt in range(int(attempts)):
        try:
            os.replace(temporary, target)
            return
        except OSError as error:
            last_error = error
            if attempt + 1 < int(attempts):
                time.sleep(delay)
                delay = min(delay * 2.0, 2.0)
    temporary.unlink(missing_ok=True)
    assert last_error is not None
    raise last_error


def make_map_id(candidate_id: str) -> str:
    """Return a compact deterministic identifier for one candidate map group."""

    value = str(candidate_id).strip()
    if not value:
        raise ValueError("candidate_id must be non-empty")
    return "lcm_" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def make_metric_id(
    candidate_id: str,
    metric_family: str,
    metric_name: str,
    region_id: str,
    *,
    metric_version: str = LOCAL_CONSISTENCY_METRIC_VERSION,
) -> str:
    """Return a compact deterministic primary key for one metric row."""

    payload = "|".join(
        (str(candidate_id), metric_family, metric_name, region_id, metric_version)
    )
    return "lcmr_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def make_map_image_id(map_id: str, map_type: str) -> str:
    """Return a compact deterministic primary key for one map asset."""

    payload = f"{map_id}|{map_type}|{LOCAL_CONSISTENCY_RENDERER_VERSION}"
    return "lcmi_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def load_rgb_array(path: str | Path, project_root: str | Path) -> np.ndarray:
    """Load one RGB image as float32 values in the native 0-255 range."""

    resolved = resolve_path(path, project_root)
    if not resolved.is_file():
        raise FileNotFoundError(f"RGB image not found: {resolved}")
    with Image.open(resolved) as image:
        return np.asarray(image.convert("RGB"), dtype=np.float32)


def load_mask_array(path: str | Path, project_root: str | Path) -> np.ndarray:
    """Load one mask/effect image without discarding grayscale support."""

    resolved = resolve_path(path, project_root)
    if not resolved.is_file():
        raise FileNotFoundError(f"Mask/effect image not found: {resolved}")
    with Image.open(resolved) as image:
        return np.asarray(image.convert("L"), dtype=np.uint8)


def _require_image_geometry(*arrays: np.ndarray) -> None:
    shapes = {tuple(np.asarray(array).shape) for array in arrays}
    if len(shapes) != 1:
        raise ValueError(f"Image geometry mismatch: {sorted(shapes)}")
    shape = np.asarray(arrays[0]).shape
    if len(shape) != 3 or shape[2] != 3:
        raise ValueError(f"Expected H x W x 3 RGB arrays, received {shape}")


def build_candidate_regions(
    row: Mapping[str, Any] | pd.Series,
    mask_values: np.ndarray,
    *,
    config: Mapping[str, Any],
) -> dict[str, Region]:
    """Build the Notebook 17 regions through the canonical helper."""

    settings = _settings(config)["regions"]
    threshold = int(float(row["mask_threshold"]))
    active_mask = np.asarray(mask_values) >= threshold
    content_bbox = tuple(
        int(float(row[column]))
        for column in (
            "content_x_min", "content_y_min", "content_x_max", "content_y_max"
        )
    )
    regions = build_standard_regions(
        active_mask,
        content_bbox=content_bbox,
        mask_bbox_margin=int(settings["mask_bbox_margin_pixels"]),
        boundary_width_pixels=int(settings["boundary_width_pixels"]),
        include_outside_boundary=True,
        outside_boundary_width_pixels=int(settings["outside_ring_outer_width_pixels"]),
    )
    if str(row["experiment_id"]) == "synthetic_degradation":
        regions["degradation_support"] = effect_support_region(
            mask_values,
            support_threshold=float(settings["effect_support_threshold"]),
        )
    return {
        region_id: regions[region_id]
        for region_id in settings["standard_region_order"]
        if region_id in regions and regions[region_id].validity_status == "valid"
    }


def _rgb_to_gray(rgb: np.ndarray) -> np.ndarray:
    return np.asarray(rgb2gray(np.clip(rgb, 0, 255) / 255.0), dtype=np.float32)


def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    return np.asarray(
        rgb2lab(np.clip(rgb, 0, 255) / 255.0, illuminant="D65", observer="2"),
        dtype=np.float32,
    )


def _gradient(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    gy = sobel(gray, axis=0, mode="reflect") / 8.0
    gx = sobel(gray, axis=1, mode="reflect") / 8.0
    magnitude = np.hypot(gx, gy).astype(np.float32)
    orientation = np.mod(np.arctan2(gy, gx), np.pi).astype(np.float32)
    return magnitude, orientation


def _local_energy(gray: np.ndarray, window: int) -> np.ndarray:
    magnitude, _ = _gradient(gray)
    energy = np.sqrt(
        np.maximum(uniform_filter(magnitude * magnitude, size=window, mode="reflect"), 0)
    )
    return energy.astype(np.float32)


def _local_ssim_map(reference_l: np.ndarray, candidate_l: np.ndarray) -> np.ndarray:
    _, score_map = structural_similarity(
        reference_l.astype(np.float32) / 100.0,
        candidate_l.astype(np.float32) / 100.0,
        data_range=1.0,
        win_size=7,
        gaussian_weights=True,
        sigma=1.5,
        use_sample_covariance=False,
        full=True,
    )
    return np.asarray(score_map, dtype=np.float32)


def _region_values(array: np.ndarray, region: Region) -> np.ndarray:
    return np.asarray(array)[region.mask]


def _finite_region_values(array: np.ndarray, region: Region) -> np.ndarray:
    values = np.asarray(array)[region.mask]
    return values[np.isfinite(values)]


def _resize_gray_for_descriptors(gray: np.ndarray, maximum_side: int) -> np.ndarray:
    height, width = gray.shape
    scale = min(1.0, float(maximum_side) / max(height, width))
    if scale >= 1.0:
        return gray.astype(np.float32, copy=False)
    new_size = (max(8, int(round(width * scale))), max(8, int(round(height * scale))))
    source = Image.fromarray(np.clip(gray * 255.0, 0, 255).astype(np.uint8))
    resized = source.resize(new_size, Image.Resampling.LANCZOS)
    return np.asarray(resized, dtype=np.float32) / 255.0


def _hellinger(first: np.ndarray, second: np.ndarray) -> float:
    one = np.asarray(first, dtype=np.float64)
    two = np.asarray(second, dtype=np.float64)
    one = one / max(float(one.sum()), np.finfo(float).eps)
    two = two / max(float(two.sum()), np.finfo(float).eps)
    return float(np.sqrt(np.sum((np.sqrt(one) - np.sqrt(two)) ** 2)) / np.sqrt(2.0))


def _periodicity_score(gray: np.ndarray, exclusion: int) -> float:
    values = np.asarray(gray, dtype=np.float64)
    values = values - float(values.mean())
    energy = float(np.sum(values * values))
    if energy <= np.finfo(float).eps:
        return 0.0
    autocorrelation = np.fft.fftshift(
        np.fft.ifft2(np.abs(np.fft.fft2(values)) ** 2).real
    )
    autocorrelation /= max(float(autocorrelation.max()), np.finfo(float).eps)
    cy, cx = np.array(autocorrelation.shape) // 2
    y0, y1 = max(0, cy - exclusion), min(autocorrelation.shape[0], cy + exclusion + 1)
    x0, x1 = max(0, cx - exclusion), min(autocorrelation.shape[1], cx + exclusion + 1)
    autocorrelation[y0:y1, x0:x1] = -np.inf
    finite = autocorrelation[np.isfinite(autocorrelation)]
    return float(max(0.0, finite.max())) if finite.size else 0.0


def compute_texture_descriptors(
    gray_crop: np.ndarray,
    *,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Compute bounded crop-level texture and brushstroke-proxy descriptors."""

    policy = _settings(config)["texture_policy"]
    gray = _resize_gray_for_descriptors(
        np.asarray(gray_crop, dtype=np.float32),
        int(policy["descriptor_maximum_side_pixels"]),
    )
    gray_u8 = np.clip(np.rint(gray * 255.0), 0, 255).astype(np.uint8)
    points = int(policy["lbp_points"])
    radius = int(policy["lbp_radius"])
    lbp = local_binary_pattern(gray_u8, points, radius, method=str(policy["lbp_method"]))
    lbp_histogram, _ = np.histogram(
        lbp, bins=np.arange(0, points + 3), range=(0, points + 2), density=False
    )
    lbp_histogram = lbp_histogram.astype(np.float64)
    lbp_histogram /= max(float(lbp_histogram.sum()), np.finfo(float).eps)

    levels = int(policy["glcm_levels"])
    quantized = np.floor(gray_u8.astype(np.float64) * levels / 256.0).astype(np.uint8)
    quantized = np.clip(quantized, 0, levels - 1)
    angles = np.deg2rad(np.asarray(policy["glcm_angles_degrees"], dtype=float))
    matrix = graycomatrix(
        quantized,
        distances=[int(value) for value in policy["glcm_distances"]],
        angles=angles,
        levels=levels,
        symmetric=True,
        normed=True,
    )
    glcm_vector = np.asarray([
        float(graycoprops(matrix, "contrast").mean()) / float((levels - 1) ** 2),
        float(graycoprops(matrix, "homogeneity").mean()),
        float(graycoprops(matrix, "energy").mean()),
        (float(graycoprops(matrix, "correlation").mean()) + 1.0) / 2.0,
    ], dtype=np.float64)

    gabor_values: list[float] = []
    kernel_size = int(policy["gabor_kernel_size"])
    if kernel_size < 3 or kernel_size % 2 == 0:
        raise ValueError("gabor_kernel_size must be an odd integer of at least 3")
    for frequency in policy["gabor_frequencies"]:
        for angle_degrees in policy["gabor_angles_degrees"]:
            kernel = cv2.getGaborKernel(
                (kernel_size, kernel_size),
                sigma=float(policy["gabor_sigma"]),
                theta=float(np.deg2rad(angle_degrees)),
                lambd=1.0 / float(frequency),
                gamma=float(policy["gabor_gamma"]),
                psi=float(policy["gabor_phase_offset"]),
                ktype=cv2.CV_32F,
            )
            norm = float(np.sum(np.abs(kernel)))
            if norm > np.finfo(float).eps:
                kernel = kernel / norm
            response = cv2.filter2D(
                gray.astype(np.float32), cv2.CV_32F, kernel,
                borderType=cv2.BORDER_REFLECT,
            )
            magnitude = np.abs(response)
            gabor_values.extend((float(magnitude.mean()), float(magnitude.std())))

    gradient_magnitude, orientation = _gradient(gray)
    gradient_floor = float(policy["orientation_gradient_floor"])
    weights = gradient_magnitude[gradient_magnitude >= gradient_floor]
    angles_selected = orientation[gradient_magnitude >= gradient_floor]
    if weights.size:
        coherence = float(
            np.abs(np.sum(weights * np.exp(2j * angles_selected)))
            / max(float(weights.sum()), np.finfo(float).eps)
        )
        orientation_histogram, _ = np.histogram(
            angles_selected,
            bins=int(policy["orientation_bins"]),
            range=(0.0, np.pi),
            weights=weights,
        )
    else:
        coherence = 0.0
        orientation_histogram = np.zeros(int(policy["orientation_bins"]), dtype=float)
    orientation_histogram = orientation_histogram.astype(np.float64)
    orientation_histogram /= max(
        float(orientation_histogram.sum()), np.finfo(float).eps
    )
    return {
        "lbp_histogram": lbp_histogram,
        "glcm_vector": glcm_vector,
        "gabor_vector": np.asarray(gabor_values, dtype=np.float64),
        "gradient_magnitude_mean": float(gradient_magnitude.mean()),
        "edge_density": float(
            np.mean(gradient_magnitude >= float(policy["edge_gradient_threshold"]))
        ),
        "orientation_coherence": coherence,
        "orientation_histogram": orientation_histogram,
        "periodicity_score": _periodicity_score(
            gray, int(policy["periodicity_center_exclusion_pixels"])
        ),
    }


def compare_texture_descriptors(
    reference: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, float]:
    """Convert descriptors into lower-is-better reference errors."""

    return {
        "lbp_histogram_distance": _hellinger(
            reference["lbp_histogram"], candidate["lbp_histogram"]
        ),
        "gabor_response_distance": float(
            np.linalg.norm(reference["gabor_vector"] - candidate["gabor_vector"])
            / math.sqrt(len(reference["gabor_vector"]))
        ),
        "glcm_feature_distance": float(
            np.linalg.norm(reference["glcm_vector"] - candidate["glcm_vector"])
            / math.sqrt(len(reference["glcm_vector"]))
        ),
        "gradient_magnitude_error": abs(
            float(reference["gradient_magnitude_mean"])
            - float(candidate["gradient_magnitude_mean"])
        ),
        "edge_density_error": abs(
            float(reference["edge_density"]) - float(candidate["edge_density"])
        ),
        "orientation_coherence_error": abs(
            float(reference["orientation_coherence"])
            - float(candidate["orientation_coherence"])
        ),
        "orientation_histogram_distance": _hellinger(
            reference["orientation_histogram"], candidate["orientation_histogram"]
        ),
        "periodicity_excess_proxy": max(
            0.0,
            float(candidate["periodicity_score"])
            - float(reference["periodicity_score"]),
        ),
    }


def compute_local_texture_maps(
    clean_gray: np.ndarray,
    candidate_gray: np.ndarray,
    *,
    config: Mapping[str, Any],
) -> dict[str, np.ndarray]:
    """Return local texture error, smoothing, and detail-excess maps."""

    policy = _settings(config)["texture_policy"]
    window = int(policy["local_window_pixels"])
    epsilon = float(policy["local_energy_epsilon"])
    tolerance = float(policy["detail_ratio_tolerance"])
    clean_energy = _local_energy(clean_gray, window)
    candidate_energy = _local_energy(candidate_gray, window)
    denominator = np.maximum(clean_energy, epsilon)
    ratio = candidate_energy / denominator
    error = np.abs(candidate_energy - clean_energy) / denominator
    supported = clean_energy >= epsilon
    return {
        "local_texture_error": error.astype(np.float32),
        "smoothing_proxy": (supported & (ratio < 1.0 - tolerance)).astype(np.float32),
        "hallucinated_detail_proxy": (
            supported & (ratio > 1.0 + tolerance)
        ).astype(np.float32),
    }


def compute_colour_maps(
    clean_lab: np.ndarray,
    candidate_lab: np.ndarray,
    *,
    minimum_chroma: float,
) -> dict[str, np.ndarray]:
    """Return ΔE00, hue-shift, and chroma-shift maps."""

    delta_e = np.asarray(deltaE_ciede2000(clean_lab, candidate_lab), dtype=np.float32)
    clean_chroma = np.hypot(clean_lab[:, :, 1], clean_lab[:, :, 2])
    candidate_chroma = np.hypot(candidate_lab[:, :, 1], candidate_lab[:, :, 2])
    clean_hue = np.arctan2(clean_lab[:, :, 2], clean_lab[:, :, 1])
    candidate_hue = np.arctan2(candidate_lab[:, :, 2], candidate_lab[:, :, 1])
    hue_difference = np.abs(
        np.angle(np.exp(1j * (candidate_hue - clean_hue)))
    ) * (180.0 / np.pi)
    hue_valid = (clean_chroma >= minimum_chroma) & (
        candidate_chroma >= minimum_chroma
    )
    hue_difference = np.where(hue_valid, hue_difference, np.nan)
    return {
        "delta_e": delta_e,
        "hue_shift_degrees": hue_difference.astype(np.float32),
        "chroma_shift": np.abs(candidate_chroma - clean_chroma).astype(np.float32),
    }


def _lab_histogram(
    values: np.ndarray, policy: Mapping[str, Any]
) -> np.ndarray:
    ranges = policy["lab_histogram_ranges"]
    histogram, _ = np.histogramdd(
        np.asarray(values, dtype=np.float64),
        bins=[int(value) for value in policy["lab_histogram_bins"]],
        range=[ranges["l"], ranges["a"], ranges["b"]],
    )
    return histogram.ravel()


def _histogram_wasserstein(
    first: np.ndarray,
    second: np.ndarray,
    *,
    value_range: Sequence[float],
    bins: int,
) -> float:
    """Approximate one-dimensional Wasserstein distance on fixed bin edges."""

    low, high = (float(value_range[0]), float(value_range[1]))
    edges = np.linspace(low, high, int(bins) + 1, dtype=np.float64)
    first_hist, _ = np.histogram(first, bins=edges)
    second_hist, _ = np.histogram(second, bins=edges)
    first_mass = first_hist.astype(np.float64)
    second_mass = second_hist.astype(np.float64)
    first_mass /= max(float(first_mass.sum()), np.finfo(float).eps)
    second_mass /= max(float(second_mass.sum()), np.finfo(float).eps)
    bin_width = (high - low) / int(bins)
    return float(
        np.sum(np.abs(np.cumsum(first_mass) - np.cumsum(second_mass)))
        * bin_width
    )


def compute_colour_region_metrics(
    clean_lab: np.ndarray,
    candidate_lab: np.ndarray,
    colour_maps: Mapping[str, np.ndarray],
    region: Region,
    *,
    config: Mapping[str, Any],
) -> dict[str, float]:
    """Compute the configured colour metrics within one canonical region."""

    policy = _settings(config)["colour_policy"]
    delta_values = _finite_region_values(colour_maps["delta_e"], region)
    hue_values = _finite_region_values(colour_maps["hue_shift_degrees"], region)
    chroma_values = _finite_region_values(colour_maps["chroma_shift"], region)
    clean_values = np.asarray(clean_lab)[region.mask]
    candidate_values = np.asarray(candidate_lab)[region.mask]
    ranges = policy["lab_histogram_ranges"]
    wasserstein_bins = int(policy["channel_wasserstein_bins"])
    result = {
        "delta_e_ciede2000_mean": float(np.mean(delta_values)),
        "delta_e_ciede2000_median": float(np.median(delta_values)),
        "delta_e_ciede2000_p95": float(np.percentile(delta_values, 95)),
        "hue_shift_mean_degrees": (
            float(np.mean(hue_values)) if hue_values.size else math.nan
        ),
        "chroma_shift_mean": float(np.mean(chroma_values)),
        "lab_l_wasserstein": _histogram_wasserstein(
            clean_values[:, 0], candidate_values[:, 0],
            value_range=ranges["l"], bins=wasserstein_bins,
        ),
        "lab_a_wasserstein": _histogram_wasserstein(
            clean_values[:, 1], candidate_values[:, 1],
            value_range=ranges["a"], bins=wasserstein_bins,
        ),
        "lab_b_wasserstein": _histogram_wasserstein(
            clean_values[:, 2], candidate_values[:, 2],
            value_range=ranges["b"], bins=wasserstein_bins,
        ),
        "lab_histogram_hellinger": _hellinger(
            _lab_histogram(clean_values, policy),
            _lab_histogram(candidate_values, policy),
        ),
    }
    return result


def _orientation_mismatch_map(
    clean_orientation: np.ndarray,
    candidate_orientation: np.ndarray,
    clean_gradient: np.ndarray,
    candidate_gradient: np.ndarray,
    *,
    floor: float,
) -> np.ndarray:
    mismatch = 0.5 * (
        1.0 - np.cos(2.0 * (candidate_orientation - clean_orientation))
    )
    valid = np.maximum(clean_gradient, candidate_gradient) >= floor
    return np.where(valid, mismatch, np.nan).astype(np.float32)


def _mean_or_nan(values: np.ndarray) -> float:
    finite = np.asarray(values)[np.isfinite(values)]
    return float(finite.mean()) if finite.size else math.nan


def _cross_boundary_metrics(
    clean_lab: np.ndarray,
    candidate_lab: np.ndarray,
    regions: Mapping[str, Region],
) -> tuple[float, float]:
    inner = regions["inner_boundary_band"].mask
    outer = regions["outer_boundary_band"].mask
    clean_l_gap = abs(float(clean_lab[:, :, 0][inner].mean()) - float(clean_lab[:, :, 0][outer].mean()))
    candidate_l_gap = abs(
        float(candidate_lab[:, :, 0][inner].mean())
        - float(candidate_lab[:, :, 0][outer].mean())
    )
    clean_inner = clean_lab[inner].mean(axis=0)
    clean_outer = clean_lab[outer].mean(axis=0)
    candidate_inner = candidate_lab[inner].mean(axis=0)
    candidate_outer = candidate_lab[outer].mean(axis=0)
    clean_colour_gap = float(deltaE_ciede2000(clean_inner, clean_outer))
    candidate_colour_gap = float(
        deltaE_ciede2000(candidate_inner, candidate_outer)
    )
    return (
        abs(candidate_l_gap - clean_l_gap),
        abs(candidate_colour_gap - clean_colour_gap),
    )


def _image_context(rgb: np.ndarray, *, config: Mapping[str, Any]) -> dict[str, Any]:
    gray = _rgb_to_gray(rgb)
    lab = _rgb_to_lab(rgb)
    gradient, orientation = _gradient(gray)
    return {
        "rgb": rgb,
        "gray": gray,
        "lab": lab,
        "gradient": gradient,
        "orientation": orientation,
        "laplacian": np.abs(laplace(lab[:, :, 0], mode="reflect")).astype(np.float32),
    }


def _value_unit(metric_name: str) -> str:
    if "fraction" in metric_name or "density" in metric_name or "coherence" in metric_name:
        return "fraction"
    if "hue" in metric_name:
        return "degrees"
    if "delta_e" in metric_name or "colour" in metric_name or "chroma" in metric_name:
        return "CIELAB_difference"
    if metric_name.startswith("lab_l_"):
        return "L_star"
    if metric_name.startswith("lab_a_") or metric_name.startswith("lab_b_"):
        return "Lab_axis_units"
    if "luminance" in metric_name:
        return "L_star"
    if "ssim" in metric_name or "orientation" in metric_name or "hellinger" in metric_name:
        return "unitless"
    if "gradient" in metric_name or "texture" in metric_name or "gabor" in metric_name:
        return "normalized_unitless"
    return "unitless"


def _evidence_component(metric_family: str, metric_name: str, region_id: str) -> str:
    if metric_family == "texture_descriptor":
        if metric_name == "periodicity_excess_proxy":
            return "repeated_texture_proxy"
        if any(token in metric_name for token in ("gradient", "edge", "orientation")):
            return "brushstroke_structure_proxy"
        return "texture_descriptor_reconstruction"
    if metric_family == "texture_map":
        if metric_name == "smoothing_proxy_fraction":
            return "excessive_smoothing_proxy"
        if metric_name == "hallucinated_detail_proxy_fraction":
            return "texture_hallucination_proxy"
        if "boundary" in region_id:
            return "texture_boundary_consistency"
        return "local_texture_reconstruction"
    if metric_family == "colour":
        if region_id in {"inner_boundary_band", "outer_boundary_band", "boundary_ring"}:
            return "colour_boundary_transition"
        if region_id in {"outside_mask_content", "outside_boundary_ring", "full_image"}:
            return "colour_global_spillover"
        return "colour_reconstruction"
    if "spillover" in metric_name:
        return "boundary_spillover"
    if region_id == "boundary_ring":
        return "seam_transition"
    return "seam_band_consistency"


def _optional_float(value: Any) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else math.nan
    except (TypeError, ValueError):
        return math.nan


def _optional_text(value: Any) -> str:
    """Return stable nullable text without serializing missing values as 'nan'."""

    if value is None:
        return ""
    try:
        if bool(pd.isna(value)):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def _append_metric_row(
    records: list[dict[str, Any]],
    row: Mapping[str, Any] | pd.Series,
    region: Region,
    *,
    metric_family: str,
    metric_name: str,
    damaged_value: float,
    restored_value: float,
    config: Mapping[str, Any],
    issue: str = "",
) -> None:
    damaged = _optional_float(damaged_value)
    restored = _optional_float(restored_value)
    if math.isfinite(damaged) and math.isfinite(restored):
        improvement = damaged - restored
        status = "ok"
    elif (
        (not math.isfinite(damaged) or not math.isfinite(restored))
        and any(token in metric_name for token in ("hue", "orientation"))
    ):
        improvement = math.nan
        status = "not_applicable"
        issue = issue or (
            "No sufficiently chromatic pixels in this region"
            if "hue" in metric_name
            else "No sufficiently strong oriented gradients in this region"
        )
    else:
        improvement = math.nan
        status = "error"
        issue = issue or "Metric value is non-finite"
    settings = _settings(config)
    candidate_id = str(row["candidate_id"])
    records.append({
        "local_consistency_id": make_metric_id(
            candidate_id, metric_family, metric_name, region.region_id,
            metric_version=str(settings["metric_version"]),
        ),
        "case_id": str(row["case_id"]),
        "candidate_id": candidate_id,
        "model_id": str(row["model_id"]),
        "painting_id": str(row["painting_id"]),
        "dataset_id": str(row["dataset_id"]),
        "dataset_scope": str(row["dataset_scope"]),
        "experiment_id": str(row["experiment_id"]),
        "damage_or_degradation_type": str(row["damage_or_degradation_type"]),
        "target_damage_fraction": _optional_float(row.get("target_damage_fraction")),
        "realized_damage_fraction": _optional_float(row.get("realized_damage_fraction")),
        "candidate_index": int(float(row["candidate_index"])),
        "seed": _optional_float(row.get("seed")),
        "prompt_policy_id": _optional_text(row.get("prompt_policy_id", "")),
        "prompt_variant_id": _optional_text(row.get("prompt_variant_id", "")),
        "execution_role": str(row.get("execution_role", "primary")),
        "is_zero_control": bool(row["is_zero_control"]),
        "metric_family": metric_family,
        "metric_name": metric_name,
        "evidence_component": _evidence_component(
            metric_family, metric_name, region.region_id
        ),
        "region_id": region.region_id,
        "region_type": region.region_type,
        "spatial_support": region.spatial_support,
        "region_pixel_count": int(region.pixel_count),
        "damaged_value": damaged,
        "restored_value": restored,
        "improvement_value": improvement,
        "improvement_direction": "damaged_minus_restored",
        "value_unit": _value_unit(metric_name),
        "metric_version": str(settings["metric_version"]),
        "region_policy_version": str(settings["regions"]["policy_version"]),
        "evidence_role": str(settings["evidence_policy"]["evidence_role"]),
        "is_final_trustworthiness_flag": False,
        "status": status,
        "issue": issue,
    })


def _texture_region_metrics(
    maps: Mapping[str, np.ndarray], region: Region
) -> dict[str, float]:
    error = _finite_region_values(maps["local_texture_error"], region)
    return {
        "local_texture_error_mean": float(np.mean(error)),
        "local_texture_error_p95": float(np.percentile(error, 95)),
        "smoothing_proxy_fraction": float(
            np.mean(_region_values(maps["smoothing_proxy"], region))
        ),
        "hallucinated_detail_proxy_fraction": float(
            np.mean(_region_values(maps["hallucinated_detail_proxy"], region))
        ),
    }


def _seam_local_maps(
    clean: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    colour_error_map: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    orientation_floor = 0.01
    return {
        "local_luminance_error": np.abs(
            clean["lab"][:, :, 0] - candidate["lab"][:, :, 0]
        ),
        "local_colour_error": (
            np.asarray(colour_error_map, dtype=np.float32)
            if colour_error_map is not None
            else np.asarray(
                deltaE_ciede2000(clean["lab"], candidate["lab"]),
                dtype=np.float32,
            )
        ),
        "local_gradient_mismatch": np.abs(
            clean["gradient"] - candidate["gradient"]
        ),
        "local_orientation_mismatch": _orientation_mismatch_map(
            clean["orientation"], candidate["orientation"],
            clean["gradient"], candidate["gradient"], floor=orientation_floor,
        ),
        "local_ssim_map_error": 1.0 - _local_ssim_map(
            clean["lab"][:, :, 0], candidate["lab"][:, :, 0]
        ),
        "transition_roughness_mismatch": np.abs(
            clean["laplacian"] - candidate["laplacian"]
        ),
    }


def _mean_map_metric(maps: Mapping[str, np.ndarray], name: str, region: Region) -> float:
    return _mean_or_nan(_region_values(maps[name], region))


def compute_case_local_consistency(
    case_candidates: pd.DataFrame,
    *,
    project_root: str | Path,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Compute every configured local-consistency row for one case."""

    if case_candidates.empty:
        return pd.DataFrame(columns=LOCAL_CONSISTENCY_COLUMNS)
    if case_candidates["case_id"].nunique() != 1:
        raise ValueError("compute_case_local_consistency accepts exactly one case_id")
    base = case_candidates.iloc[0]
    clean_rgb = load_rgb_array(base["clean_image_path"], project_root)
    damaged_rgb = load_rgb_array(base["input_image_path"], project_root)
    mask_values = load_mask_array(base["mask_or_effect_path"], project_root)
    _require_image_geometry(clean_rgb, damaged_rgb)
    if mask_values.shape != clean_rgb.shape[:2]:
        raise ValueError("Mask geometry does not match image geometry")
    regions = build_candidate_regions(base, mask_values, config=config)
    clean = _image_context(clean_rgb, config=config)
    damaged = _image_context(damaged_rgb, config=config)
    colour_policy = _settings(config)["colour_policy"]
    minimum_chroma = float(colour_policy["minimum_chroma_for_hue_degrees"])
    damaged_texture_maps = compute_local_texture_maps(
        clean["gray"], damaged["gray"], config=config
    )
    damaged_colour_maps = compute_colour_maps(
        clean["lab"], damaged["lab"], minimum_chroma=minimum_chroma
    )
    damaged_seam_maps = (
        _seam_local_maps(
            clean, damaged, colour_error_map=damaged_colour_maps["delta_e"]
        )
        if not bool(base["is_zero_control"])
        else {}
    )
    descriptor_region = regions.get("mask_bbox_crop")
    clean_descriptor = damaged_descriptor = None
    if descriptor_region is not None:
        bbox = descriptor_region.bbox
        assert bbox is not None
        x0, y0, x1, y1 = bbox
        clean_descriptor = compute_texture_descriptors(
            clean["gray"][y0:y1, x0:x1], config=config
        )
        damaged_descriptor = compare_texture_descriptors(
            clean_descriptor,
            compute_texture_descriptors(
                damaged["gray"][y0:y1, x0:x1], config=config
            ),
        )

    damaged_colour_cache: dict[str, dict[str, float]] = {}
    for region_id in _settings(config)["regions"]["colour_regions"]:
        region = regions.get(region_id)
        if region is not None:
            damaged_colour_cache[region_id] = compute_colour_region_metrics(
                clean["lab"], damaged["lab"], damaged_colour_maps, region,
                config=config,
            )

    records: list[dict[str, Any]] = []
    for _, candidate in case_candidates.iterrows():
        restored_rgb = load_rgb_array(candidate["restored_path"], project_root)
        _require_image_geometry(clean_rgb, restored_rgb)
        restored = _image_context(restored_rgb, config=config)
        restored_texture_maps = compute_local_texture_maps(
            clean["gray"], restored["gray"], config=config
        )
        restored_colour_maps = compute_colour_maps(
            clean["lab"], restored["lab"], minimum_chroma=minimum_chroma
        )

        if descriptor_region is not None and clean_descriptor is not None:
            x0, y0, x1, y1 = descriptor_region.bbox  # type: ignore[misc]
            restored_descriptor = compare_texture_descriptors(
                clean_descriptor,
                compute_texture_descriptors(
                    restored["gray"][y0:y1, x0:x1], config=config
                ),
            )
            assert damaged_descriptor is not None
            for metric_name in _settings(config)["metric_plan"][
                "texture_descriptor"
            ]["metric_names"]:
                _append_metric_row(
                    records, candidate, descriptor_region,
                    metric_family="texture_descriptor",
                    metric_name=str(metric_name),
                    damaged_value=damaged_descriptor[str(metric_name)],
                    restored_value=restored_descriptor[str(metric_name)],
                    config=config,
                )

        for region_id in _settings(config)["regions"]["texture_map_regions"]:
            region = regions.get(region_id)
            if region is None:
                continue
            damaged_values = _texture_region_metrics(damaged_texture_maps, region)
            restored_values = _texture_region_metrics(restored_texture_maps, region)
            for metric_name in _settings(config)["metric_plan"]["texture_map"][
                "metric_names"
            ]:
                _append_metric_row(
                    records, candidate, region,
                    metric_family="texture_map", metric_name=str(metric_name),
                    damaged_value=damaged_values[str(metric_name)],
                    restored_value=restored_values[str(metric_name)], config=config,
                )

        for region_id in _settings(config)["regions"]["colour_regions"]:
            region = regions.get(region_id)
            if region is None:
                continue
            restored_values = compute_colour_region_metrics(
                clean["lab"], restored["lab"], restored_colour_maps, region,
                config=config,
            )
            damaged_values = damaged_colour_cache[region_id]
            for metric_name in _settings(config)["metric_plan"]["colour"][
                "metric_names"
            ]:
                _append_metric_row(
                    records, candidate, region,
                    metric_family="colour", metric_name=str(metric_name),
                    damaged_value=damaged_values[str(metric_name)],
                    restored_value=restored_values[str(metric_name)], config=config,
                )

        if not bool(candidate["is_zero_control"]):
            restored_seam_maps = _seam_local_maps(
                clean, restored, colour_error_map=restored_colour_maps["delta_e"]
            )
            for region_id in _settings(config)["regions"]["seam_inner_outer_regions"]:
                region = regions[region_id]
                for metric_name in _settings(config)["metric_plan"][
                    "seam_inner_outer"
                ]["metric_names"]:
                    _append_metric_row(
                        records, candidate, region, metric_family="seam",
                        metric_name=str(metric_name),
                        damaged_value=_mean_map_metric(
                            damaged_seam_maps, str(metric_name), region
                        ),
                        restored_value=_mean_map_metric(
                            restored_seam_maps, str(metric_name), region
                        ),
                        config=config,
                    )
            boundary = regions["boundary_ring"]
            damaged_l_gap, damaged_c_gap = _cross_boundary_metrics(
                clean["lab"], damaged["lab"], regions
            )
            restored_l_gap, restored_c_gap = _cross_boundary_metrics(
                clean["lab"], restored["lab"], regions
            )
            boundary_values = {
                "cross_boundary_luminance_discontinuity_error": (
                    damaged_l_gap, restored_l_gap
                ),
                "cross_boundary_colour_discontinuity_error": (
                    damaged_c_gap, restored_c_gap
                ),
                "boundary_gradient_mismatch": (
                    _mean_map_metric(damaged_seam_maps, "local_gradient_mismatch", boundary),
                    _mean_map_metric(restored_seam_maps, "local_gradient_mismatch", boundary),
                ),
                "boundary_orientation_mismatch": (
                    _mean_map_metric(damaged_seam_maps, "local_orientation_mismatch", boundary),
                    _mean_map_metric(restored_seam_maps, "local_orientation_mismatch", boundary),
                ),
                "boundary_local_ssim_map_error": (
                    _mean_map_metric(damaged_seam_maps, "local_ssim_map_error", boundary),
                    _mean_map_metric(restored_seam_maps, "local_ssim_map_error", boundary),
                ),
                "transition_roughness_mismatch": (
                    _mean_map_metric(damaged_seam_maps, "transition_roughness_mismatch", boundary),
                    _mean_map_metric(restored_seam_maps, "transition_roughness_mismatch", boundary),
                ),
            }
            for metric_name in _settings(config)["metric_plan"]["seam_boundary"][
                "metric_names"
            ]:
                damaged_value, restored_value = boundary_values[str(metric_name)]
                _append_metric_row(
                    records, candidate, boundary, metric_family="seam",
                    metric_name=str(metric_name), damaged_value=damaged_value,
                    restored_value=restored_value, config=config,
                )
            outside = regions["outside_boundary_ring"]
            spillover = np.mean(
                np.abs(restored_rgb.astype(np.float32) - damaged_rgb.astype(np.float32)),
                axis=2,
            )[outside.mask]
            for metric_name, restored_value in {
                "boundary_spillover_change_mean": float(np.mean(spillover)),
                "boundary_spillover_change_p95": float(np.percentile(spillover, 95)),
            }.items():
                _append_metric_row(
                    records, candidate, outside, metric_family="seam",
                    metric_name=metric_name, damaged_value=0.0,
                    restored_value=restored_value, config=config,
                )

    result = pd.DataFrame(records, columns=LOCAL_CONSISTENCY_COLUMNS)
    validation = validate_dataframe(result, LOCAL_CONSISTENCY_SCHEMA)
    if not validation.passed:
        raise ValueError(
            f"Computed local-consistency rows violate schema: {validation.to_dict()}"
        )
    return result


def expected_rows_for_candidate(row: Mapping[str, Any] | pd.Series) -> int:
    """Return the exact v1 metric-row count for one normalized candidate."""

    if bool(row["is_zero_control"]):
        return 27
    total = 131
    if str(row["experiment_id"]) == "synthetic_degradation":
        total += 13
    return total


def expected_metric_row_count(worklist: pd.DataFrame) -> int:
    """Return the analytical row count for a normalized worklist."""

    return int(sum(expected_rows_for_candidate(row) for _, row in worklist.iterrows()))


def validate_local_consistency_metrics(
    metrics: pd.DataFrame,
    worklist: pd.DataFrame,
    *,
    expected_rows: int | None = None,
) -> dict[str, Any]:
    """Return compact schema, coverage, and scientific-policy validation."""

    schema = validate_dataframe(metrics, LOCAL_CONSISTENCY_SCHEMA)
    expected = expected_metric_row_count(worklist) if expected_rows is None else int(expected_rows)
    candidate_counts = metrics.groupby("candidate_id").size().to_dict()
    count_mismatches = {
        str(row.candidate_id): {
            "expected": expected_rows_for_candidate(row._asdict()),
            "observed": int(candidate_counts.get(str(row.candidate_id), 0)),
        }
        for row in worklist.itertuples(index=False)
        if int(candidate_counts.get(str(row.candidate_id), 0))
        != expected_rows_for_candidate(row._asdict())
    }
    sparse_ssim = metrics.loc[
        metrics["metric_name"].str.contains("ssim", case=False, na=False)
        & metrics["region_id"].isin({"masked_region", "degradation_support"})
    ]
    error_rows = int(metrics["status"].eq("error").sum()) if not metrics.empty else 0
    result = {
        "passed": bool(
            schema.passed
            and len(metrics) == expected
            and not count_mismatches
            and sparse_ssim.empty
            and error_rows == 0
        ),
        "schema_passed": bool(schema.passed),
        "expected_rows": expected,
        "observed_rows": int(len(metrics)),
        "candidate_count_mismatches": count_mismatches,
        "duplicate_primary_keys": int(
            metrics["local_consistency_id"].duplicated(keep=False).sum()
        ) if "local_consistency_id" in metrics else len(metrics),
        "sparse_ssim_rows": int(len(sparse_ssim)),
        "error_rows": error_rows,
        "not_applicable_rows": int(metrics["status"].eq("not_applicable").sum()),
    }
    if result["duplicate_primary_keys"]:
        result["passed"] = False
    return result


def _candidate_checkpoint_complete(
    candidate: Mapping[str, Any], metrics: pd.DataFrame
) -> bool:
    subset = metrics.loc[
        metrics["candidate_id"].astype(str).eq(str(candidate["candidate_id"]))
    ]
    return bool(
        len(subset) == expected_rows_for_candidate(candidate)
        and not subset["local_consistency_id"].duplicated().any()
        and not subset["status"].eq("error").any()
    )


def run_local_consistency_metrics(
    worklist: pd.DataFrame,
    *,
    project_root: str | Path,
    config: Mapping[str, Any],
    checkpoint_path: str | Path | None = None,
    progress_callback: ProgressCallback | None = None,
) -> LocalConsistencyRunResult:
    """Compute or strictly resume the complete candidate-level metric table."""

    checkpoint = Path(checkpoint_path) if checkpoint_path else None
    metrics = (
        pd.read_csv(checkpoint)
        if checkpoint is not None and checkpoint.is_file()
        else pd.DataFrame(columns=LOCAL_CONSISTENCY_COLUMNS)
    )
    completed_ids = {
        str(row.candidate_id)
        for row in worklist.itertuples(index=False)
        if _candidate_checkpoint_complete(row._asdict(), metrics)
    }
    reused = len(completed_ids)
    total = len(worklist)
    processed = reused
    interval = int(_settings(config)["execution"]["checkpoint_interval_candidates"])
    progress_interval = int(
        _settings(config)["execution"]["progress_interval_candidates"]
    )
    started = time.perf_counter()
    last_checkpoint_count = processed
    for case_id, case_frame in worklist.groupby("case_id", sort=True):
        pending = case_frame.loc[
            ~case_frame["candidate_id"].astype(str).isin(completed_ids)
        ]
        if pending.empty:
            continue
        computed = compute_case_local_consistency(
            pending, project_root=project_root, config=config
        )
        metrics = (
            computed.copy()
            if metrics.empty
            else pd.concat([metrics, computed], ignore_index=True)
        )
        completed_ids.update(pending["candidate_id"].astype(str))
        processed += len(pending)
        should_checkpoint = (
            processed - last_checkpoint_count >= interval or processed == total
        )
        if should_checkpoint:
            metrics = metrics.drop_duplicates(
                "local_consistency_id", keep="last"
            ).loc[:, LOCAL_CONSISTENCY_COLUMNS]
            if checkpoint is not None:
                execution = _settings(config)["execution"]
                write_dataframe_atomic(
                    metrics, checkpoint,
                    attempts=int(execution["atomic_replace_attempts"]),
                    retry_delay_seconds=float(execution["atomic_replace_retry_seconds"]),
                )
            last_checkpoint_count = processed
        if progress_callback is not None and (
            processed % progress_interval < len(pending) or processed == total
        ):
            elapsed = time.perf_counter() - started
            throughput = (processed - reused) / elapsed if elapsed > 0 else 0.0
            progress_callback(
                f"Local consistency: {processed}/{total} "
                f"({100.0 * processed / total:.1f}%) | elapsed={elapsed:.1f}s | "
                f"throughput={throughput:.3f} candidates/s | latest_case={case_id}"
            )
    metrics = metrics.drop_duplicates(
        "local_consistency_id", keep="last"
    ).sort_values(
        ["candidate_id", "metric_family", "metric_name", "region_id"],
        kind="stable",
    ).reset_index(drop=True).loc[:, LOCAL_CONSISTENCY_COLUMNS]
    return LocalConsistencyRunResult(metrics, len(completed_ids), reused)


def select_map_candidates(worklist: pd.DataFrame) -> pd.DataFrame:
    """Select the predeclared primary, non-zero candidate map population."""

    selected = worklist.loc[
        worklist["execution_role"].astype(str).eq("primary")
        & ~worklist["is_zero_control"].astype(bool)
    ].copy()
    if selected.duplicated(["case_id", "model_id"]).any():
        raise ValueError("Primary map population is not unique by case_id/model_id")
    return selected.sort_values(
        ["model_id", "case_id", "candidate_id"], kind="stable"
    ).reset_index(drop=True)


def compute_display_scales(
    metrics: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Derive shared map scales from canonical full-population metrics."""

    percentile = float(_settings(config)["visualization"]["scale_percentile"])
    definitions = {
        "texture": ("local_texture_error_p95", None),
        "colour": ("delta_e_ciede2000_p95", None),
        "seam": ("boundary_gradient_mismatch", "boundary_ring"),
    }
    scales: dict[str, dict[str, Any]] = {}
    for family, (metric_name, region_id) in definitions.items():
        subset = metrics.loc[metrics["metric_name"].eq(metric_name)]
        if region_id is not None:
            subset = subset.loc[subset["region_id"].eq(region_id)]
        values = np.concatenate([
            pd.to_numeric(subset["damaged_value"], errors="coerce").to_numpy(),
            pd.to_numeric(subset["restored_value"], errors="coerce").to_numpy(),
        ])
        values = values[np.isfinite(values) & (values >= 0)]
        vmax = float(np.percentile(values, percentile)) if values.size else 1.0
        vmax = max(vmax, np.finfo(float).eps)
        scales[family] = {
            "vmin": 0.0,
            "vmax": vmax,
            "center": 0.0,
            "error_cmap": str(_settings(config)["visualization"]["error_colormap"]),
            "improvement_cmap": str(
                _settings(config)["visualization"]["improvement_colormap"]
            ),
            "scale_scope": (
                f"global candidate metric {percentile:g}th percentile; "
                f"source_metric={metric_name}"
            ),
        }
    return scales


def compute_candidate_display_maps(
    row: Mapping[str, Any] | pd.Series,
    *,
    project_root: str | Path,
    config: Mapping[str, Any],
) -> tuple[dict[str, dict[str, np.ndarray]], dict[str, Region]]:
    """Compute damaged, restored, and signed-improvement maps for three families."""

    clean_rgb = load_rgb_array(row["clean_image_path"], project_root)
    damaged_rgb = load_rgb_array(row["input_image_path"], project_root)
    restored_rgb = load_rgb_array(row["restored_path"], project_root)
    mask_values = load_mask_array(row["mask_or_effect_path"], project_root)
    _require_image_geometry(clean_rgb, damaged_rgb, restored_rgb)
    regions = build_candidate_regions(row, mask_values, config=config)
    clean = _image_context(clean_rgb, config=config)
    damaged = _image_context(damaged_rgb, config=config)
    restored = _image_context(restored_rgb, config=config)
    minimum_chroma = float(
        _settings(config)["colour_policy"]["minimum_chroma_for_hue_degrees"]
    )
    damaged_texture = compute_local_texture_maps(
        clean["gray"], damaged["gray"], config=config
    )["local_texture_error"]
    restored_texture = compute_local_texture_maps(
        clean["gray"], restored["gray"], config=config
    )["local_texture_error"]
    damaged_colour = compute_colour_maps(
        clean["lab"], damaged["lab"], minimum_chroma=minimum_chroma
    )["delta_e"]
    restored_colour = compute_colour_maps(
        clean["lab"], restored["lab"], minimum_chroma=minimum_chroma
    )["delta_e"]
    boundary_mask = regions["boundary_ring"].mask
    damaged_seam = np.where(
        boundary_mask, np.abs(clean["gradient"] - damaged["gradient"]), np.nan
    ).astype(np.float32)
    restored_seam = np.where(
        boundary_mask, np.abs(clean["gradient"] - restored["gradient"]), np.nan
    ).astype(np.float32)
    return ({
        "texture": {
            "damaged_error": damaged_texture,
            "restored_error": restored_texture,
            "signed_improvement": damaged_texture - restored_texture,
        },
        "colour": {
            "damaged_error": damaged_colour,
            "restored_error": restored_colour,
            "signed_improvement": damaged_colour - restored_colour,
        },
        "seam": {
            "damaged_error": damaged_seam,
            "restored_error": restored_seam,
            "signed_improvement": damaged_seam - restored_seam,
        },
    }, regions)


def _colourize(
    values: np.ndarray,
    *,
    cmap_name: str,
    norm: Normalize,
    no_data_rgba: Sequence[int],
) -> np.ndarray:
    array = np.asarray(values, dtype=np.float32)
    valid = np.isfinite(array)
    safe = np.where(valid, array, 0.0)
    rgba = np.rint(colormaps[cmap_name](norm(safe)) * 255.0).astype(np.uint8)
    rgba[~valid] = np.asarray(no_data_rgba, dtype=np.uint8)
    return rgba


def save_family_map_panel(
    maps: Mapping[str, np.ndarray],
    path: str | Path,
    *,
    scale: Mapping[str, Any],
    no_data_rgba: Sequence[int],
    compress_level: int = 9,
) -> None:
    """Save one fast three-panel damaged/restored/improvement PNG."""

    vmax = float(scale["vmax"])
    error_norm = Normalize(vmin=0.0, vmax=vmax, clip=True)
    signed_norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
    panels = [
        _colourize(
            maps["damaged_error"], cmap_name=str(scale["error_cmap"]),
            norm=error_norm, no_data_rgba=no_data_rgba,
        ),
        _colourize(
            maps["restored_error"], cmap_name=str(scale["error_cmap"]),
            norm=error_norm, no_data_rgba=no_data_rgba,
        ),
        _colourize(
            maps["signed_improvement"], cmap_name=str(scale["improvement_cmap"]),
            norm=signed_norm, no_data_rgba=no_data_rgba,
        ),
    ]
    height, width = panels[0].shape[:2]
    label_height = 24
    canvas = Image.new("RGBA", (width * 3, height + label_height), (255, 255, 255, 255))
    labels = ("Damaged error", "Restored error", "Improvement (+ better)")
    draw = ImageDraw.Draw(canvas)
    for index, (panel, label) in enumerate(zip(panels, labels)):
        canvas.paste(Image.fromarray(panel, mode="RGBA"), (index * width, label_height))
        draw.text((index * width + 6, 5), label, fill=(0, 0, 0, 255))
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target, format="PNG", compress_level=int(compress_level))


def _map_record(
    row: Mapping[str, Any] | pd.Series,
    *,
    map_id: str,
    map_type: str,
    path: Path,
    project_root: str | Path,
    scale: Mapping[str, Any],
) -> dict[str, Any]:
    with Image.open(path) as image:
        width, height = image.size
        mode = image.mode
        fmt = image.format
    return {
        "map_image_id": make_map_image_id(map_id, map_type),
        "asset_kind": "candidate_map",
        "map_id": map_id,
        "candidate_id": str(row["candidate_id"]),
        "case_id": str(row["case_id"]),
        "model_id": str(row["model_id"]),
        "painting_id": str(row["painting_id"]),
        "map_type": map_type,
        "selection_role": "primary_nonzero_candidate",
        "relative_path": project_relative_path(path, project_root),
        "sha256": sha256_path(path),
        "size_bytes": int(path.stat().st_size),
        "width": int(width),
        "height": int(height),
        "image_mode": str(mode),
        "format": str(fmt),
        "cmap": f"{scale['error_cmap']}|{scale['improvement_cmap']}",
        "vmin": -float(scale["vmax"]),
        "vmax": float(scale["vmax"]),
        "center": 0.0,
        "scale_scope": str(scale["scale_scope"]),
        "quantization_policy": "RGBA uint8 presentation panel; metrics remain float",
        "no_data_policy": "configured neutral RGBA outside seam support",
        "renderer_version": LOCAL_CONSISTENCY_RENDERER_VERSION,
        "status": "passed",
        "issue": "",
    }


def save_candidate_map_assets(
    row: Mapping[str, Any] | pd.Series,
    *,
    project_root: str | Path,
    maps_root: str | Path,
    config: Mapping[str, Any],
    scales: Mapping[str, Mapping[str, Any]],
) -> pd.DataFrame:
    """Compute and save the three canonical map panels for one candidate."""

    family_maps, _ = compute_candidate_display_maps(
        row, project_root=project_root, config=config
    )
    map_id = make_map_id(str(row["candidate_id"]))
    output_root = Path(maps_root) / str(row["model_id"]) / map_id
    visual = _settings(config)["visualization"]
    records = []
    for map_type in MAP_TYPES:
        path = output_root / f"{map_type}.png"
        save_family_map_panel(
            family_maps[map_type], path, scale=scales[map_type],
            no_data_rgba=visual["no_data_rgba"],
            compress_level=int(visual["png_compress_level"]),
        )
        records.append(_map_record(
            row, map_id=map_id, map_type=map_type, path=path,
            project_root=project_root, scale=scales[map_type],
        ))
    frame = pd.DataFrame(records, columns=LOCAL_CONSISTENCY_MAP_MANIFEST_COLUMNS)
    validation = validate_dataframe(frame, LOCAL_CONSISTENCY_MAP_MANIFEST_SCHEMA)
    if not validation.passed:
        raise ValueError(f"Map rows violate schema: {validation.to_dict()}")
    return frame


def _candidate_maps_complete(
    candidate_id: str,
    manifest: pd.DataFrame,
    *,
    project_root: str | Path,
) -> bool:
    subset = manifest.loc[
        manifest["candidate_id"].astype(str).eq(str(candidate_id))
        & manifest["asset_kind"].eq("candidate_map")
    ]
    if len(subset) != len(MAP_TYPES) or set(subset["map_type"]) != set(MAP_TYPES):
        return False
    if subset["map_image_id"].duplicated().any():
        return False
    for row in subset.itertuples(index=False):
        path = resolve_path(row.relative_path, project_root)
        if not path.is_file() or sha256_path(path) != str(row.sha256):
            return False
    return True


def run_local_consistency_maps(
    map_candidates: pd.DataFrame,
    *,
    project_root: str | Path,
    maps_root: str | Path,
    config: Mapping[str, Any],
    scales: Mapping[str, Mapping[str, Any]],
    checkpoint_path: str | Path | None = None,
    progress_callback: ProgressCallback | None = None,
) -> LocalConsistencyMapRunResult:
    """Generate or strictly resume the primary-candidate map population."""

    checkpoint = Path(checkpoint_path) if checkpoint_path else None
    manifest = (
        pd.read_csv(checkpoint)
        if checkpoint is not None and checkpoint.is_file()
        else pd.DataFrame(columns=LOCAL_CONSISTENCY_MAP_MANIFEST_COLUMNS)
    )
    completed_ids = {
        str(row.candidate_id)
        for row in map_candidates.itertuples(index=False)
        if _candidate_maps_complete(
            str(row.candidate_id), manifest, project_root=project_root
        )
    }
    reused = len(completed_ids)
    total = len(map_candidates)
    execution = _settings(config)["execution"]
    checkpoint_interval = int(execution["checkpoint_interval_candidates"])
    progress_interval = int(execution["progress_interval_candidates"])
    started = time.perf_counter()
    for number, (_, row) in enumerate(map_candidates.iterrows(), start=1):
        candidate_id = str(row["candidate_id"])
        if candidate_id not in completed_ids:
            computed = save_candidate_map_assets(
                row, project_root=project_root, maps_root=maps_root,
                config=config, scales=scales,
            )
            manifest = (
                computed.copy()
                if manifest.empty
                else pd.concat([manifest, computed], ignore_index=True)
            )
            completed_ids.add(candidate_id)
        if number % checkpoint_interval == 0 or number == total:
            manifest = manifest.drop_duplicates(
                "map_image_id", keep="last"
            ).loc[:, LOCAL_CONSISTENCY_MAP_MANIFEST_COLUMNS]
            if checkpoint is not None:
                write_dataframe_atomic(
                    manifest, checkpoint,
                    attempts=int(execution["atomic_replace_attempts"]),
                    retry_delay_seconds=float(execution["atomic_replace_retry_seconds"]),
                )
        if progress_callback is not None and (
            number % progress_interval == 0 or number == total
        ):
            elapsed = time.perf_counter() - started
            generated = max(0, number - reused)
            throughput = generated / elapsed if elapsed > 0 else 0.0
            progress_callback(
                f"Local-consistency maps: {number}/{total} "
                f"({100.0 * number / total:.1f}%) | elapsed={elapsed:.1f}s | "
                f"throughput={throughput:.3f} candidates/s | "
                f"latest_candidate={candidate_id}"
            )
    manifest = manifest.drop_duplicates(
        "map_image_id", keep="last"
    ).sort_values(
        ["model_id", "candidate_id", "map_type"], kind="stable"
    ).reset_index(drop=True).loc[:, LOCAL_CONSISTENCY_MAP_MANIFEST_COLUMNS]
    return LocalConsistencyMapRunResult(manifest, len(completed_ids), reused)


def register_selected_panel(
    path: str | Path,
    *,
    project_root: str | Path,
    selection_role: str,
    cross_model: bool,
    candidate_id: str = "",
    case_id: str = "",
    model_id: str = "",
    painting_id: str = "",
) -> pd.DataFrame:
    """Register one deterministic selected review panel in the map manifest."""

    panel_path = Path(path)
    if not panel_path.is_file():
        raise FileNotFoundError(f"Selected panel not found: {panel_path}")
    relative = project_relative_path(panel_path, project_root)
    map_id = "lcp_" + hashlib.sha256(relative.encode("utf-8")).hexdigest()[:16]
    map_type = (
        "cross_model_local_consistency_panel"
        if cross_model
        else "local_consistency_candidate_panel"
    )
    with Image.open(panel_path) as image:
        width, height = image.size
        mode, fmt = image.mode, image.format
    record = {
        "map_image_id": make_map_image_id(map_id, map_type),
        "asset_kind": "selected_panel",
        "map_id": map_id,
        "candidate_id": str(candidate_id),
        "case_id": str(case_id),
        "model_id": str(model_id),
        "painting_id": str(painting_id),
        "map_type": map_type,
        "selection_role": str(selection_role),
        "relative_path": relative,
        "sha256": sha256_path(panel_path),
        "size_bytes": int(panel_path.stat().st_size),
        "width": int(width),
        "height": int(height),
        "image_mode": str(mode),
        "format": str(fmt),
        "cmap": "mixed_panel",
        "vmin": 0.0,
        "vmax": 0.0,
        "center": math.nan,
        "scale_scope": "panel-specific layout using canonical global family scales",
        "quantization_policy": "matplotlib PNG presentation panel",
        "no_data_policy": "not_applicable",
        "renderer_version": LOCAL_CONSISTENCY_RENDERER_VERSION,
        "status": "passed",
        "issue": "",
    }
    frame = pd.DataFrame([record], columns=LOCAL_CONSISTENCY_MAP_MANIFEST_COLUMNS)
    validation = validate_dataframe(frame, LOCAL_CONSISTENCY_MAP_MANIFEST_SCHEMA)
    if not validation.passed:
        raise ValueError(f"Selected panel row violates schema: {validation.to_dict()}")
    return frame


def validate_map_manifest(
    manifest: pd.DataFrame,
    *,
    project_root: str | Path,
    verify_checksums: bool = False,
) -> dict[str, Any]:
    """Validate map schema, paths, formats, and optional checksums."""

    schema = validate_dataframe(manifest, LOCAL_CONSISTENCY_MAP_MANIFEST_SCHEMA)
    missing: list[str] = []
    checksum_mismatches: list[str] = []
    invalid_images: list[str] = []
    for row in manifest.itertuples(index=False):
        path = resolve_path(row.relative_path, project_root)
        if not path.is_file():
            missing.append(str(row.relative_path))
            continue
        try:
            with Image.open(path) as image:
                image.verify()
        except Exception:
            invalid_images.append(str(row.relative_path))
        if verify_checksums and sha256_path(path) != str(row.sha256):
            checksum_mismatches.append(str(row.relative_path))
    passed = bool(
        schema.passed and not missing and not checksum_mismatches and not invalid_images
    )
    return {
        "passed": passed,
        "schema_passed": bool(schema.passed),
        "rows": int(len(manifest)),
        "missing_paths": missing,
        "checksum_mismatches": checksum_mismatches,
        "invalid_images": invalid_images,
        "duplicate_primary_keys": int(
            manifest["map_image_id"].duplicated(keep=False).sum()
        ) if "map_image_id" in manifest else len(manifest),
    }


def render_candidate_review_panel(
    row: Mapping[str, Any] | pd.Series,
    *,
    project_root: str | Path,
    config: Mapping[str, Any],
    scales: Mapping[str, Mapping[str, Any]],
    output_path: str | Path,
    selection_role: str,
) -> plt.Figure:
    """Render one full human-review panel with source images and three maps."""

    clean = load_rgb_array(row["clean_image_path"], project_root).astype(np.uint8)
    damaged = load_rgb_array(row["input_image_path"], project_root).astype(np.uint8)
    restored = load_rgb_array(row["restored_path"], project_root).astype(np.uint8)
    mask = load_mask_array(row["mask_or_effect_path"], project_root)
    family_maps, regions = compute_candidate_display_maps(
        row, project_root=project_root, config=config
    )
    figure, axes = plt.subplots(2, 4, figsize=(18, 9), constrained_layout=True)
    for axis, image, title in zip(
        axes[0, :3], (clean, damaged, restored), ("Clean", "Damaged", "Restored")
    ):
        axis.imshow(image)
        axis.set_title(title)
        axis.axis("off")
    axes[0, 3].imshow(mask, cmap="gray", vmin=0, vmax=255)
    axes[0, 3].contour(regions["boundary_ring"].mask, levels=[0.5], colors="cyan")
    axes[0, 3].set_title("Mask/effect + boundary")
    axes[0, 3].axis("off")
    for axis, family in zip(axes[1, :3], MAP_TYPES):
        scale = scales[family]
        shown = axis.imshow(
            family_maps[family]["restored_error"],
            cmap=str(scale["error_cmap"]), vmin=0.0, vmax=float(scale["vmax"]),
        )
        axis.set_title(f"{family.title()} restored error")
        axis.axis("off")
        figure.colorbar(shown, ax=axis, fraction=0.046, pad=0.04)
    improvement = family_maps["seam"]["signed_improvement"]
    limit = float(scales["seam"]["vmax"])
    shown = axes[1, 3].imshow(
        improvement, cmap=str(scales["seam"]["improvement_cmap"]),
        norm=TwoSlopeNorm(vmin=-limit, vcenter=0.0, vmax=limit),
    )
    axes[1, 3].set_title("Seam improvement (+ better)")
    axes[1, 3].axis("off")
    figure.colorbar(shown, ax=axes[1, 3], fraction=0.046, pad=0.04)
    figure.suptitle(
        f"{selection_role} | {row['model_id']} | {row['case_id']} | "
        "diagnostic proxies only",
        fontsize=13,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(target, dpi=180, bbox_inches="tight")
    return figure


__all__ = [
    "LOCAL_CONSISTENCY_MAP_VERSION",
    "LOCAL_CONSISTENCY_METRIC_VERSION",
    "LOCAL_CONSISTENCY_MODULE_NAME",
    "LOCAL_CONSISTENCY_MODULE_VERSION",
    "LOCAL_CONSISTENCY_RENDERER_VERSION",
    "LocalConsistencyMapRunResult",
    "LocalConsistencyRunResult",
    "MAP_TYPES",
    "build_candidate_regions",
    "compare_texture_descriptors",
    "compute_candidate_display_maps",
    "compute_case_local_consistency",
    "compute_colour_maps",
    "compute_colour_region_metrics",
    "compute_display_scales",
    "compute_local_texture_maps",
    "compute_texture_descriptors",
    "expected_metric_row_count",
    "expected_rows_for_candidate",
    "load_local_consistency_config",
    "make_map_id",
    "make_map_image_id",
    "make_metric_id",
    "project_relative_path",
    "render_candidate_review_panel",
    "register_selected_panel",
    "resolve_path",
    "run_local_consistency_metrics",
    "run_local_consistency_maps",
    "save_candidate_map_assets",
    "save_family_map_panel",
    "select_map_candidates",
    "sha256_path",
    "validate_local_consistency_metrics",
    "validate_map_manifest",
    "write_dataframe_atomic",
]
