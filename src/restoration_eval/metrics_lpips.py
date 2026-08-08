"""
LPIPS perceptual metrics for restoration evaluation.

The module compares damaged and restored images against the clean reference
using image-like spatial regions only:

- full_image;
- content_region;
- mask_bbox_crop for non-empty masks.

Sparse masked pixels are intentionally excluded because LPIPS operates on
ordered image patches, not unordered pixel selections.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import platform
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from PIL import Image


LPIPS_MODULE_NAME = "restoration_eval.metrics_lpips"
LPIPS_METRIC_SCHEMA_VERSION = "2.1.0"

DEFAULT_LPIPS_NET = "alex"
DEFAULT_LPIPS_INPUT_SIZE = 256
DEFAULT_MASK_BBOX_MARGIN = 8
DEFAULT_MASK_BINARY_THRESHOLD = 127

LPIPS_EVALUATION_REGIONS = (
    "full_image",
    "content_region",
    "mask_bbox_crop",
)

SEED_AND_CANDIDATE_COLUMNS = (
    "candidate_id",
    "candidate_index",
    "candidate_seed",
    "effective_candidate_seed",
    "prompt_policy_id",
    "prompt_variant_id",
    "prompt_template_name",
    "prompt_variant_family",
    "prompt_variant_order",
    "prompt_ablation_subset",
    "inference_mode",
    "execution_device",
    "scheduler_name",
    "num_inference_steps",
    "guidance_scale",
    "strength",
)


def get_package_version(package_name: str) -> str:
    """Return an installed package version, or ``not-installed``."""
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def validate_lpips_runtime_dependencies() -> pd.DataFrame:
    """Check optional packages needed for LPIPS computation."""
    dependency_rows = []

    for module_name, package_name, required in (
        ("torch", "torch", True),
        ("lpips", "lpips", True),
        ("PIL", "Pillow", True),
    ):
        module_spec = importlib.util.find_spec(module_name)
        installed = module_spec is not None
        dependency_rows.append(
            {
                "component": package_name,
                "module": module_name,
                "version": get_package_version(package_name),
                "required": required,
                "installed": installed,
                "passed": bool(installed or not required),
            }
        )

    return pd.DataFrame(dependency_rows)


def get_device(prefer_cuda: bool = True):
    """Return a torch device, preferring CUDA when requested and available."""
    torch = importlib.import_module("torch")

    if prefer_cuda and torch.cuda.is_available():
        return torch.device("cuda")

    return torch.device("cpu")


def load_lpips_model(
    net: str = DEFAULT_LPIPS_NET,
    device: Any | None = None,
):
    """Load an LPIPS model lazily so package import stays lightweight."""
    lpips = importlib.import_module("lpips")

    if device is None:
        device = get_device()

    model = lpips.LPIPS(net=net).to(device)
    model.eval()

    return model


def load_rgb_image(path: Path | str) -> Image.Image:
    """Load an image file as RGB."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    with Image.open(path) as image:
        return image.convert("RGB")


def load_mask_bool(
    path: Path | str,
    threshold: int = DEFAULT_MASK_BINARY_THRESHOLD,
) -> np.ndarray:
    """Load a mask as a boolean array where True marks damage."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Mask file not found: {path}")

    with Image.open(path) as image:
        mask_arr = np.asarray(image.convert("L"))

    return mask_arr > threshold


def pil_to_lpips_tensor(
    image: Image.Image,
    device: Any,
):
    """Convert a PIL image to an LPIPS tensor in the expected [-1, 1] range."""
    torch = importlib.import_module("torch")

    image_arr = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    tensor = torch.from_numpy(image_arr).permute(2, 0, 1).unsqueeze(0)
    tensor = tensor.mul(2.0).sub(1.0)

    return tensor.to(device)


def compute_lpips_distance(
    image_a: Image.Image,
    image_b: Image.Image,
    lpips_model: Any,
    device: Any,
) -> float:
    """Compute LPIPS distance between two same-sized PIL images."""
    if image_a.size != image_b.size:
        raise ValueError(
            f"LPIPS image-size mismatch: {image_a.size} vs {image_b.size}"
        )

    torch = importlib.import_module("torch")
    tensor_a = pil_to_lpips_tensor(image_a, device)
    tensor_b = pil_to_lpips_tensor(image_b, device)

    with torch.no_grad():
        value = lpips_model(tensor_a, tensor_b)

    return float(value.item())


def resize_for_lpips(
    image: Image.Image,
    size: int = DEFAULT_LPIPS_INPUT_SIZE,
) -> Image.Image:
    """Resize an image region to a square LPIPS input size."""
    return image.convert("RGB").resize(
        (int(size), int(size)),
        Image.Resampling.LANCZOS,
    )


def clip_box(
    box: tuple[int, int, int, int],
    image_size: tuple[int, int],
) -> tuple[int, int, int, int] | None:
    """Clip a PIL-style crop box to image bounds."""
    left, upper, right, lower = box
    width, height = image_size

    left = max(0, min(int(left), width))
    right = max(0, min(int(right), width))
    upper = max(0, min(int(upper), height))
    lower = max(0, min(int(lower), height))

    if right <= left or lower <= upper:
        return None

    return left, upper, right, lower


def get_content_box_from_row(
    row: pd.Series,
    image_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    """Get the recorded content-region box in PIL crop coordinates."""
    required_columns = (
        "content_x_min",
        "content_y_min",
        "content_x_max",
        "content_y_max",
    )

    missing_columns = [
        column
        for column in required_columns
        if column not in row.index
    ]

    if missing_columns:
        raise ValueError(f"Missing content-region columns: {missing_columns}")

    content_box = clip_box(
        (
            int(row["content_x_min"]),
            int(row["content_y_min"]),
            int(row["content_x_max"]),
            int(row["content_y_max"]),
        ),
        image_size=image_size,
    )

    if content_box is None:
        raise ValueError(
            "Invalid content box: "
            f"{[row[column] for column in required_columns]}"
        )

    return content_box


def get_mask_bbox(
    mask_bool: np.ndarray,
    margin: int = DEFAULT_MASK_BBOX_MARGIN,
) -> tuple[int, int, int, int] | None:
    """Return a padded mask bounding box in PIL crop coordinates."""
    if margin < 0:
        raise ValueError("mask_bbox_margin must be non-negative.")

    y_coords, x_coords = np.where(mask_bool)

    if len(x_coords) == 0:
        return None

    height, width = mask_bool.shape

    return clip_box(
        (
            int(x_coords.min()) - int(margin),
            int(y_coords.min()) - int(margin),
            int(x_coords.max()) + int(margin) + 1,
            int(y_coords.max()) + int(margin) + 1,
        ),
        image_size=(width, height),
    )


def make_square_crop_box(
    box: tuple[int, int, int, int],
    image_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    """Expand a crop box to a square while staying inside the image."""
    left, upper, right, lower = box
    width, height = image_size

    crop_width = right - left
    crop_height = lower - upper
    side = min(max(crop_width, crop_height), width, height)

    center_x = (left + right) // 2
    center_y = (upper + lower) // 2

    square_left = center_x - side // 2
    square_upper = center_y - side // 2
    square_right = square_left + side
    square_lower = square_upper + side

    if square_left < 0:
        square_right -= square_left
        square_left = 0

    if square_upper < 0:
        square_lower -= square_upper
        square_upper = 0

    if square_right > width:
        shift = square_right - width
        square_left -= shift
        square_right = width

    if square_lower > height:
        shift = square_lower - height
        square_upper -= shift
        square_lower = height

    clipped_box = clip_box(
        (square_left, square_upper, square_right, square_lower),
        image_size=image_size,
    )

    if clipped_box is None:
        raise ValueError(f"Invalid square crop box derived from {box}.")

    return clipped_box


def crop_image_region(
    image: Image.Image,
    box: tuple[int, int, int, int],
    resize_to: int = DEFAULT_LPIPS_INPUT_SIZE,
) -> Image.Image:
    """Crop an image region and resize it for LPIPS."""
    return resize_for_lpips(
        image.crop(box),
        size=resize_to,
    )


def _is_null_like(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _row_value(row: pd.Series, key: str, default: Any = "") -> Any:
    value = row.get(key, default)
    return default if _is_null_like(value) else value


def _safe_difference(left: float, right: float) -> float:
    if np.isnan(left) or np.isnan(right):
        return float("nan")

    return float(left - right)


def _normalise_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if _is_null_like(value):
        return False
    if isinstance(value, (int, np.integer)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _candidate_metadata(row: pd.Series) -> dict[str, Any]:
    return {
        column: _row_value(row, column)
        for column in SEED_AND_CANDIDATE_COLUMNS
        if column in row.index
    }


def _build_lpips_record(
    row: pd.Series,
    evaluation_region: str,
    region_box: tuple[int, int, int, int],
    damaged_lpips: float,
    restored_lpips: float,
    lpips_net: str,
    lpips_input_size: int,
    mask_bbox_margin: int,
    mask_binary_threshold: int,
    device_name: str,
    torch_version: str,
    lpips_package_version: str,
    metric_runtime_seconds: float,
    case_runtime_seconds: float,
    status: str = "ok",
    issue: str = "",
) -> dict[str, Any]:
    """Build one standardized LPIPS output record."""
    restoration_case_id = _row_value(
        row,
        "restoration_case_id",
        _row_value(row, "case_id"),
    )
    candidate_id = _row_value(row, "candidate_id", restoration_case_id)
    metric_case_id = _row_value(row, "metric_case_id", candidate_id)
    dataset_name = _row_value(row, "dataset_name", "canonical")
    mask_type = _row_value(
        row,
        "metric_mask_type",
        _row_value(row, "mask_type"),
    )
    mask_id = _row_value(row, "metric_mask_id", _row_value(row, "mask_id"))
    source_case_id = _row_value(
        row,
        "source_case_id",
        _row_value(row, "case_id"),
    )
    source_case_id_original = _row_value(
        row,
        "source_case_id_original",
        source_case_id,
    )
    is_zero_control = _normalise_bool(_row_value(row, "is_zero_control", False))
    left, upper, right, lower = region_box

    record = {
        "lpips_row_id": f"{metric_case_id}__{evaluation_region}__lpips",
        "lpips_case_id": metric_case_id,
        "metric_case_id": metric_case_id,
        "candidate_id": candidate_id,
        "restoration_case_id": restoration_case_id,
        "source_case_id": source_case_id,
        "source_case_id_original": source_case_id_original,
        "case_id": _row_value(row, "case_id", source_case_id),
        "dataset_name": dataset_name,
        "metric_applicability": _row_value(row, "metric_applicability", "primary"),
        "painting_id": _row_value(row, "painting_id"),
        "category": _row_value(row, "category"),
        "title": _row_value(row, "title"),
        "artist": _row_value(row, "artist"),
        "style": _row_value(row, "style", _row_value(row, "style_or_period")),
        "model_name": _row_value(row, "model_name"),
        "mask_id": mask_id,
        "mask_type": mask_type,
        "metric_mask_id": mask_id,
        "metric_mask_type": mask_type,
        "evaluation_region": evaluation_region,
        "region_pixel_count": int((right - left) * (lower - upper)),
        "region_x_min": int(left),
        "region_y_min": int(upper),
        "region_x_max": int(right),
        "region_y_max": int(lower),
        "mask_area_pixels": int(float(_row_value(row, "mask_area_pixels", 0) or 0)),
        "is_zero_control": is_zero_control,
        "mask_threshold_rule": f"> {mask_binary_threshold}",
        "mask_bbox_margin": int(mask_bbox_margin),
        "lpips_net": lpips_net,
        "lpips_input_size": int(lpips_input_size),
        "damaged_lpips": float(damaged_lpips),
        "restored_lpips": float(restored_lpips),
        "lpips_improvement": _safe_difference(damaged_lpips, restored_lpips),
        "metric_runtime_seconds": float(metric_runtime_seconds),
        "case_runtime_seconds": float(case_runtime_seconds),
        "lpips_schema_version": LPIPS_METRIC_SCHEMA_VERSION,
        "lpips_implementation_name": LPIPS_MODULE_NAME,
        "device": device_name,
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "pillow_version": Image.__version__,
        "torch_version": torch_version,
        "lpips_package_version": lpips_package_version,
        "status": status,
        "issue": issue,
    }

    record.update(_candidate_metadata(row))
    return record


def expected_lpips_rows_from_metadata(
    restoration_metadata: pd.DataFrame,
    mask_binary_threshold: int = DEFAULT_MASK_BINARY_THRESHOLD,
) -> int:
    """Return expected LPIPS row count for the image-like region policy."""
    return int(
        len(restoration_metadata) * 2
        + expected_lpips_region_counts_from_metadata(
            restoration_metadata,
            mask_binary_threshold=mask_binary_threshold,
        )["mask_bbox_crop"]
    )


def expected_lpips_region_counts_from_metadata(
    restoration_metadata: pd.DataFrame,
    mask_binary_threshold: int = DEFAULT_MASK_BINARY_THRESHOLD,
) -> dict[str, int]:
    """Return expected row counts by LPIPS evaluation region."""
    if "mask_path" not in restoration_metadata.columns:
        raise ValueError("Restoration metadata missing required column: mask_path")

    nonzero_mask_cases = sum(
        bool(np.any(load_mask_bool(mask_path, threshold=mask_binary_threshold)))
        for mask_path in restoration_metadata["mask_path"]
    )

    return {
        "full_image": int(len(restoration_metadata)),
        "content_region": int(len(restoration_metadata)),
        "mask_bbox_crop": int(nonzero_mask_cases),
    }


def compute_lpips_metrics_for_restorations(
    restoration_metadata: pd.DataFrame,
    lpips_model: Any,
    device: Any,
    lpips_net: str = DEFAULT_LPIPS_NET,
    target_size: int | tuple[int, int] | None = 768,
    mask_bbox_margin: int = DEFAULT_MASK_BBOX_MARGIN,
    lpips_input_size: int = DEFAULT_LPIPS_INPUT_SIZE,
    mask_binary_threshold: int = DEFAULT_MASK_BINARY_THRESHOLD,
    progress_every: int | None = 25,
) -> pd.DataFrame:
    """Compute LPIPS metrics for restoration outputs."""
    required_columns = [
        "case_id",
        "painting_id",
        "model_name",
        "clean_path",
        "damaged_path",
        "restored_path",
        "mask_path",
        "content_x_min",
        "content_y_min",
        "content_x_max",
        "content_y_max",
    ]
    missing_columns = [
        column
        for column in required_columns
        if column not in restoration_metadata.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Restoration metadata missing required columns: {missing_columns}"
        )

    if restoration_metadata.empty:
        raise ValueError("Restoration metadata is empty.")

    if target_size is None:
        expected_size = None
    elif isinstance(target_size, int):
        expected_size = (target_size, target_size)
    else:
        expected_size = tuple(target_size)

    sort_columns = [
        column
        for column in (
            "dataset_name",
            "painting_id",
            "mask_type",
            "candidate_index",
            "candidate_id",
            "case_id",
        )
        if column in restoration_metadata.columns
    ]
    sorted_metadata = (
        restoration_metadata
        .sort_values(sort_columns, kind="stable")
        .reset_index(drop=True)
    )

    records: list[dict[str, Any]] = []
    total_cases = len(sorted_metadata)
    computation_start_time = time.perf_counter()
    device_name = str(device)
    torch_version = get_package_version("torch")
    lpips_package_version = get_package_version("lpips")

    print("Starting LPIPS metric computation")
    print(f"  Cases: {total_cases}")
    print(f"  Target size: {expected_size or 'not enforced'}")
    print(f"  LPIPS net: {lpips_net}")
    print(f"  LPIPS input size: {lpips_input_size}")
    print(f"  Device: {device_name}")

    for case_index, (_, row) in enumerate(sorted_metadata.iterrows(), start=1):
        case_start_time = time.perf_counter()

        if progress_every and (
            case_index == 1
            or case_index % progress_every == 0
            or case_index == total_cases
        ):
            elapsed = time.perf_counter() - computation_start_time
            print(
                f"Computing LPIPS case {case_index}/{total_cases} "
                f"({row['case_id']}) | elapsed {elapsed:.2f}s"
            )

        try:
            clean_image = load_rgb_image(row["clean_path"])
            damaged_image = load_rgb_image(row["damaged_path"])
            restored_image = load_rgb_image(row["restored_path"])
            mask_bool = load_mask_bool(
                row["mask_path"],
                threshold=mask_binary_threshold,
            )

            if clean_image.size != damaged_image.size or clean_image.size != restored_image.size:
                raise ValueError(
                    f"Image size mismatch for case {row['case_id']}: "
                    f"clean={clean_image.size}, damaged={damaged_image.size}, "
                    f"restored={restored_image.size}"
                )

            if mask_bool.shape != (clean_image.size[1], clean_image.size[0]):
                raise ValueError(
                    f"Mask shape mismatch for case {row['case_id']}: "
                    f"mask={mask_bool.shape}, image={clean_image.size}"
                )

            if expected_size is not None and clean_image.size != expected_size:
                raise ValueError(
                    f"Unexpected image size for case {row['case_id']}: "
                    f"{clean_image.size}, expected {expected_size}"
                )

            region_boxes = {
                "full_image": (
                    0,
                    0,
                    clean_image.size[0],
                    clean_image.size[1],
                ),
                "content_region": get_content_box_from_row(
                    row,
                    image_size=clean_image.size,
                ),
            }

            mask_box = get_mask_bbox(mask_bool, margin=mask_bbox_margin)
            if mask_box is not None:
                region_boxes["mask_bbox_crop"] = make_square_crop_box(
                    mask_box,
                    image_size=clean_image.size,
                )

            row_records: list[dict[str, Any]] = []

            for evaluation_region, region_box in region_boxes.items():
                metric_start_time = time.perf_counter()

                clean_region = crop_image_region(
                    clean_image,
                    region_box,
                    resize_to=lpips_input_size,
                )
                damaged_region = crop_image_region(
                    damaged_image,
                    region_box,
                    resize_to=lpips_input_size,
                )
                restored_region = crop_image_region(
                    restored_image,
                    region_box,
                    resize_to=lpips_input_size,
                )

                damaged_lpips = compute_lpips_distance(
                    clean_region,
                    damaged_region,
                    lpips_model,
                    device,
                )
                restored_lpips = compute_lpips_distance(
                    clean_region,
                    restored_region,
                    lpips_model,
                    device,
                )

                metric_runtime_seconds = time.perf_counter() - metric_start_time
                row_records.append(
                    _build_lpips_record(
                        row=row,
                        evaluation_region=evaluation_region,
                        region_box=region_box,
                        damaged_lpips=damaged_lpips,
                        restored_lpips=restored_lpips,
                        lpips_net=lpips_net,
                        lpips_input_size=lpips_input_size,
                        mask_bbox_margin=mask_bbox_margin,
                        mask_binary_threshold=mask_binary_threshold,
                        device_name=device_name,
                        torch_version=torch_version,
                        lpips_package_version=lpips_package_version,
                        metric_runtime_seconds=metric_runtime_seconds,
                        case_runtime_seconds=0.0,
                    )
                )

            case_runtime_seconds = time.perf_counter() - case_start_time
            for record in row_records:
                record["case_runtime_seconds"] = float(case_runtime_seconds)
            records.extend(row_records)

        except Exception as exc:
            case_runtime_seconds = time.perf_counter() - case_start_time
            metric_case_id = row.get(
                "metric_case_id",
                row.get("candidate_id", row.get("case_id", "")),
            )
            records.append(
                {
                    "lpips_row_id": f"{metric_case_id}__error__lpips",
                    "lpips_case_id": metric_case_id,
                    "metric_case_id": metric_case_id,
                    "candidate_id": row.get("candidate_id", ""),
                    "restoration_case_id": row.get(
                        "restoration_case_id",
                        row.get("case_id", ""),
                    ),
                    "source_case_id": row.get("source_case_id", row.get("case_id", "")),
                    "source_case_id_original": row.get(
                        "source_case_id_original",
                        row.get("source_case_id", row.get("case_id", "")),
                    ),
                    "case_id": row.get("case_id", ""),
                    "dataset_name": row.get("dataset_name", "canonical"),
                    "metric_applicability": row.get("metric_applicability", "primary"),
                    "painting_id": row.get("painting_id", ""),
                    "category": row.get("category", ""),
                    "title": row.get("title", ""),
                    "artist": row.get("artist", ""),
                    "style": row.get("style", row.get("style_or_period", "")),
                    "model_name": row.get("model_name", ""),
                    "mask_id": row.get("metric_mask_id", row.get("mask_id", "")),
                    "mask_type": row.get("metric_mask_type", row.get("mask_type", "")),
                    "metric_mask_id": row.get("metric_mask_id", row.get("mask_id", "")),
                    "metric_mask_type": row.get(
                        "metric_mask_type",
                        row.get("mask_type", ""),
                    ),
                    "evaluation_region": "error",
                    "region_pixel_count": 0,
                    "region_x_min": None,
                    "region_y_min": None,
                    "region_x_max": None,
                    "region_y_max": None,
                    "mask_area_pixels": row.get("mask_area_pixels", 0),
                    "is_zero_control": row.get("is_zero_control", False),
                    "mask_threshold_rule": f"> {mask_binary_threshold}",
                    "mask_bbox_margin": int(mask_bbox_margin),
                    "lpips_net": lpips_net,
                    "lpips_input_size": int(lpips_input_size),
                    "damaged_lpips": np.nan,
                    "restored_lpips": np.nan,
                    "lpips_improvement": np.nan,
                    "metric_runtime_seconds": 0.0,
                    "case_runtime_seconds": float(case_runtime_seconds),
                    "lpips_schema_version": LPIPS_METRIC_SCHEMA_VERSION,
                    "lpips_implementation_name": LPIPS_MODULE_NAME,
                    "device": device_name,
                    "python_version": platform.python_version(),
                    "numpy_version": np.__version__,
                    "pandas_version": pd.__version__,
                    "pillow_version": Image.__version__,
                    "torch_version": torch_version,
                    "lpips_package_version": lpips_package_version,
                    "status": "error",
                    "issue": f"{type(exc).__name__}: {exc}",
                    **_candidate_metadata(row),
                }
            )

            print(
                f"  Error in LPIPS case {case_index}/{total_cases} "
                f"({row.get('case_id', '')}): {type(exc).__name__}: {exc}"
            )

    metrics_df = pd.DataFrame(records)
    elapsed_total = time.perf_counter() - computation_start_time

    print("LPIPS metric computation complete")
    print(f"  Runtime: {elapsed_total:.2f} seconds")
    print(f"  Output rows: {len(metrics_df)}")

    if "evaluation_region" in metrics_df.columns:
        print("  Region counts:")
        print(metrics_df["evaluation_region"].value_counts().to_string())

    if "status" in metrics_df.columns:
        print("  Status counts:")
        print(metrics_df["status"].value_counts(dropna=False).to_string())

    return metrics_df


def validate_lpips_metrics(
    lpips_df: pd.DataFrame,
    expected_rows: int | None = None,
    expected_region_counts: dict[str, int] | None = None,
    key_columns: Iterable[str] = (
        "dataset_name",
        "lpips_case_id",
        "model_name",
        "evaluation_region",
    ),
) -> pd.DataFrame:
    """Validate LPIPS output structure, row counts, status, and uniqueness."""
    required_columns = [
        "lpips_row_id",
        "lpips_case_id",
        "candidate_id",
        "restoration_case_id",
        "dataset_name",
        "painting_id",
        "model_name",
        "evaluation_region",
        "region_pixel_count",
        "damaged_lpips",
        "restored_lpips",
        "lpips_improvement",
        "lpips_schema_version",
        "lpips_implementation_name",
        "status",
        "issue",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in lpips_df.columns
    ]

    validation_rows: list[dict[str, Any]] = [
        {
            "check": "required_columns",
            "passed": not missing_columns,
            "detail": (
                "All required columns present."
                if not missing_columns
                else f"Missing columns: {missing_columns}"
            ),
        }
    ]

    if expected_rows is not None:
        validation_rows.append(
            {
                "check": "row_count",
                "passed": len(lpips_df) == expected_rows,
                "detail": f"Expected {expected_rows}, found {len(lpips_df)}.",
            }
        )

    if "status" in lpips_df.columns:
        error_rows = int((lpips_df["status"] == "error").sum())
        validation_rows.append(
            {
                "check": "no_error_rows",
                "passed": error_rows == 0,
                "detail": f"Error rows: {error_rows}.",
            }
        )

    available_key_columns = [
        column
        for column in key_columns
        if column in lpips_df.columns
    ]

    if len(available_key_columns) == len(tuple(key_columns)):
        duplicate_rows = int(
            lpips_df.duplicated(available_key_columns, keep=False).sum()
        )
        validation_rows.append(
            {
                "check": "unique_lpips_keys",
                "passed": duplicate_rows == 0,
                "detail": f"Rows participating in duplicate keys: {duplicate_rows}.",
            }
        )

    if expected_region_counts is not None and "evaluation_region" in lpips_df.columns:
        actual_region_counts = lpips_df["evaluation_region"].value_counts().to_dict()
        mismatches = {
            region: {
                "expected": int(expected_count),
                "actual": int(actual_region_counts.get(region, 0)),
            }
            for region, expected_count in expected_region_counts.items()
            if int(actual_region_counts.get(region, 0)) != int(expected_count)
        }
        validation_rows.append(
            {
                "check": "region_counts",
                "passed": not mismatches,
                "detail": (
                    "All evaluation-region counts match expectations."
                    if not mismatches
                    else f"Mismatches: {mismatches}"
                ),
            }
        )

    if "evaluation_region" in lpips_df.columns:
        invalid_regions = sorted(
            set(lpips_df["evaluation_region"].dropna().astype(str))
            - set(LPIPS_EVALUATION_REGIONS)
        )
        invalid_regions = [
            region
            for region in invalid_regions
            if region != "error"
        ]
        validation_rows.append(
            {
                "check": "region_policy",
                "passed": not invalid_regions,
                "detail": (
                    "All LPIPS rows use image-like evaluation regions."
                    if not invalid_regions
                    else f"Invalid LPIPS regions: {invalid_regions}"
                ),
            }
        )

    if "region_pixel_count" in lpips_df.columns and "status" in lpips_df.columns:
        invalid_counts = int(
            (
                lpips_df["status"].eq("ok")
                & lpips_df["region_pixel_count"].le(0)
            ).sum()
        )
        validation_rows.append(
            {
                "check": "positive_region_pixel_counts",
                "passed": invalid_counts == 0,
                "detail": (
                    f"Successful rows with non-positive region size: "
                    f"{invalid_counts}."
                ),
            }
        )

    numeric_columns = [
        column
        for column in ("damaged_lpips", "restored_lpips", "lpips_improvement")
        if column in lpips_df.columns
    ]
    if numeric_columns and "status" in lpips_df.columns:
        ok_numeric_df = (
            lpips_df.loc[lpips_df["status"].eq("ok"), numeric_columns]
            .apply(pd.to_numeric, errors="coerce")
        )
        finite_ok_values = bool(np.isfinite(ok_numeric_df.to_numpy(dtype=float)).all())
        validation_rows.append(
            {
                "check": "finite_successful_lpips_values",
                "passed": finite_ok_values,
                "detail": "Successful LPIPS values are finite.",
            }
        )

    return pd.DataFrame(validation_rows)


def summarize_lpips_metrics(
    lpips_df: pd.DataFrame,
    group_columns: list[str],
    summary_scope: str | None = None,
) -> pd.DataFrame:
    """Summarize LPIPS metrics for notebook display and reports."""
    missing_group_columns = [
        column
        for column in group_columns
        if column not in lpips_df.columns
    ]
    if missing_group_columns:
        raise ValueError(
            f"LPIPS dataframe missing group columns: {missing_group_columns}"
        )

    summary_df = lpips_df.copy()
    if "status" in summary_df.columns:
        summary_df = summary_df[summary_df["status"] != "error"].copy()

    if group_columns:
        grouped = (
            summary_df
            .groupby(group_columns, dropna=False, sort=False)
            .agg(
                rows=("lpips_row_id", "count"),
                cases=("lpips_case_id", "nunique"),
                median_damaged_lpips=("damaged_lpips", "median"),
                median_restored_lpips=("restored_lpips", "median"),
                median_lpips_improvement=("lpips_improvement", "median"),
                mean_damaged_lpips=("damaged_lpips", "mean"),
                mean_restored_lpips=("restored_lpips", "mean"),
                mean_lpips_improvement=("lpips_improvement", "mean"),
                improvement_rate=("lpips_improvement", lambda values: (values > 0).mean()),
                median_region_pixel_count=("region_pixel_count", "median"),
            )
            .reset_index()
        )
    else:
        grouped = pd.DataFrame(
            [
                {
                    "rows": int(len(summary_df)),
                    "cases": int(summary_df["lpips_case_id"].nunique()),
                    "median_damaged_lpips": summary_df["damaged_lpips"].median(),
                    "median_restored_lpips": summary_df["restored_lpips"].median(),
                    "median_lpips_improvement": summary_df["lpips_improvement"].median(),
                    "mean_damaged_lpips": summary_df["damaged_lpips"].mean(),
                    "mean_restored_lpips": summary_df["restored_lpips"].mean(),
                    "mean_lpips_improvement": summary_df["lpips_improvement"].mean(),
                    "improvement_rate": (summary_df["lpips_improvement"] > 0).mean(),
                    "median_region_pixel_count": summary_df["region_pixel_count"].median(),
                }
            ]
        )

    if summary_scope is not None:
        grouped.insert(0, "summary_scope", summary_scope)

    return grouped.round(6)


def rank_lpips_cases(
    lpips_df: pd.DataFrame,
    evaluation_region: str = "mask_bbox_crop",
    top_n: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return strongest and weakest LPIPS-improvement cases."""
    region_df = (
        lpips_df.loc[
            lpips_df["evaluation_region"].eq(evaluation_region)
            & lpips_df["status"].eq("ok")
        ]
        .copy()
    )

    strongest_df = (
        region_df
        .sort_values(
            ["lpips_improvement", "lpips_case_id"],
            ascending=[False, True],
            kind="stable",
        )
        .head(top_n)
        .reset_index(drop=True)
    )

    weakest_df = (
        region_df
        .sort_values(
            ["lpips_improvement", "lpips_case_id"],
            ascending=[True, True],
            kind="stable",
        )
        .head(top_n)
        .reset_index(drop=True)
    )

    return strongest_df, weakest_df
