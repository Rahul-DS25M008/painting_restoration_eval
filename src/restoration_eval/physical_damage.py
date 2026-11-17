"""Read-only D03/D04 exhibit bindings, independent of the frozen N34 package.

No inference, metric computation or source-artifact rewriting occurs here.
Every displayed producer artifact is checked against its producer manifest.
"""
from __future__ import annotations

import base64
import csv
from functools import lru_cache
import hashlib
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D03 = "outputs/d03_real_damage_dataset_preparation"
D04 = "outputs/d04_real_damage_restoration_and_evaluation"
OPENING = "rd004"
MODELS = ("opencv_telea", "lama", "hint_places2", "stable_diffusion_inpainting")
LABELS = dict(zip(MODELS, ("Telea", "LaMa", "HINT", "Stable Diffusion")))
PANELS = ("", "evidence", "seeds", "comparison", "sources", "report")
CATEGORIES = (
    ("portrait_figure", "Portrait / figure", ("rd001", "rd002")),
    ("landscape_natural", "Landscape", ("rd003", "rd004")),
    ("architecture_structured", "Architecture", ("rd005", "rd006")),
    ("abstraction_surrealism", "Abstraction", ("rd007", "rd008")),
    ("high_texture_brushwork", "Texture / brushwork", ("rd009", "rd010")),
)


def local_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError(f"Physical-study artifact unavailable: {relative}")
    return path


@lru_cache(maxsize=160)
def _checked_bytes(path: str, mtime: int, size: int | None, digest: str) -> bytes:
    data = Path(path).read_bytes()
    if (size is not None and len(data) != size) or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"Physical-study integrity check failed: {Path(path).name}")
    return data


def registry() -> dict:
    result = {}
    for producer in (D03, D04):
        path = local_path(f"{producer}/manifests/artifacts.csv")
        for row in csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig"))):
            key = row["relative_path"]
            if key in result and result[key]["checksum"] != row["checksum"]:
                raise ValueError(f"Conflicting artifact registration: {key}")
            result[key] = row
    # D03 registers image collections. Their manifest-verified tables bind
    # each member to its own SHA-256; D04 registers individual files directly.
    for table, path_field, hash_field in (
        ("preprocessed_images", "processed_path", "sha256"),
        ("masks", "mask_path", "mask_sha256"),
    ):
        for row in rows(f"{D03}/data/{table}.csv", result):
            result[row[path_field]] = {
                "validation_status": "passed", "checksum": row[hash_field],
                "size_bytes": row.get("size_bytes", ""),
            }
    return result


def verified_bytes(relative: str, index: dict, expected: str | None = None) -> bytes:
    record = index.get(relative)
    if not record or record["validation_status"] != "passed":
        raise ValueError(f"Unverified physical-study artifact: {relative}")
    if expected and record["checksum"] != expected:
        raise ValueError(f"Physical-study cross-reference mismatch: {relative}")
    path = local_path(relative)
    return _checked_bytes(str(path), path.stat().st_mtime_ns,
                          int(record["size_bytes"]) if record["size_bytes"] else None, record["checksum"])


def rows(relative: str, index: dict) -> list[dict]:
    return list(csv.DictReader(io.StringIO(verified_bytes(relative, index).decode("utf-8-sig"))))


def app_media_url(url: str) -> str:
    """Resolve media under the visible app, including Cloud's /~/+/ proxy.

    MediaFileManager returns a server-root path; raw HTML/CSS bypasses the
    base-path rewriting used by Streamlit's native image components.
    """
    from urllib.parse import urlsplit
    parsed = urlsplit(url)
    prefix, separator, filename = parsed.path.rpartition("/media/")
    if (parsed.scheme or parsed.netloc or not separator or not filename
            or "/" in filename or parsed.query or parsed.fragment):
        raise ValueError("Unexpected Streamlit media URL")
    return "media/" + filename


def media(relative: str, index: dict, expected=None) -> str:
    """Register same-origin media on every render; large evidence loads on demand."""
    import mimetypes
    from streamlit import runtime
    data = verified_bytes(relative, index, expected)
    mime = mimetypes.guess_type(relative)[0] or "application/octet-stream"
    if runtime.exists():
        return app_media_url(runtime.get_instance().media_file_mgr.add(data, mime, f"physical:{relative}"))
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def static_media(relative: str) -> str:
    from streamlit import runtime
    path = local_path(relative)
    if runtime.exists():
        return app_media_url(runtime.get_instance().media_file_mgr.add(str(path), "image/png", f"physical:{relative}"))
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def payload(painting_id=OPENING, panel="", media_fn=media) -> dict:
    """Join exact case/candidate identities; never pick a seed by appearance."""
    index = registry()
    artworks = rows(f"{D03}/data/artworks.csv", index)
    artwork = {r["painting_id"]: r for r in artworks}
    expected_ids = {p for _, _, group in CATEGORIES for p in group}
    if len(artworks) != 10 or set(artwork) != expected_ids:
        raise ValueError("Physical room requires the approved ten-painting cohort")
    for category, _, group in CATEGORIES:
        if any(artwork[p]["category"] != category for p in group):
            raise ValueError("Physical-study category binding changed")
    if painting_id not in artwork:
        raise ValueError("Unknown physical-study painting")
    if panel not in PANELS:
        raise ValueError("Unknown physical-study evidence panel")
    processed = {r["painting_id"]: r for r in rows(f"{D03}/data/preprocessed_images.csv", index)}
    masks = {r["painting_id"]: r for r in rows(f"{D03}/data/masks.csv", index)}
    candidates = [r for r in rows(f"{D04}/data/candidates.csv", index) if r["painting_id"] == painting_id]
    primary = {r["model_id"]: r for r in candidates if r["candidate_role"] == "primary"}
    seeds = sorted((r for r in candidates if r["model_id"] == MODELS[-1]), key=lambda r: int(r["seed"]))
    mask = masks[painting_id]
    if (len(candidates) != 7 or set(primary) != set(MODELS) or
            [r["seed"] for r in seeds] != ["2026", "2027", "2028", "2029"] or
            primary[MODELS[-1]]["seed"] != "2026"):
        raise ValueError("Incomplete physical-study candidate coverage")
    for row in candidates:
        if (row["status"] != "completed" or row["case_id"] != mask["case_id"] or
                row["input_image_sha256"] != mask["input_sha256"] or row["mask_sha256"] != mask["mask_sha256"]):
            raise ValueError("Physical-study candidate input binding mismatch")
    panel_row = next(r for r in rows(f"{D04}/work/comparison/panels.csv", index) if r["pair_id"] == painting_id)
    detail = [int(panel_row[f"physical_detail_{v}"]) for v in ("x0", "y0", "x1", "y1")]
    def content(p):
        return [int(processed[p][f"content_{v}"]) for v in ("x_min", "y_min", "x_max", "y_max")]
    bounds = content(painting_id)
    if not (bounds[0] <= detail[0] < detail[2] <= bounds[2] and bounds[1] <= detail[1] < detail[3] <= bounds[3]):
        raise ValueError("Physical-study display crop lies outside image content")
    observations = [r for r in rows(f"{D04}/data/case_observations.csv", index) if r["painting_id"] == painting_id]
    for row in observations:
        candidate = primary[row["model_id"]]
        if row["candidate_id"] != candidate["candidate_id"] or row["restored_sha256"] != candidate["restored_sha256"]:
            raise ValueError("Observation does not describe the displayed primary candidate")
    data = {
        "case": painting_id, "panel": panel, "artwork": artwork[painting_id], "case_id": mask["case_id"],
        "content": bounds, "detail": detail, "crop_policy": panel_row["detail_crop_policy"],
        "mask_fraction": float(mask["mask_fraction_content"]), "mask_note": mask["target_description"],
        "mask": media_fn(mask["mask_path"], index, mask["mask_sha256"]),
        "images": [{"label": "Damaged input", "uri": media_fn(mask["input_path"], index, mask["input_sha256"])}] + [
            {"label": LABELS[m], "model": m, "candidate": primary[m]["candidate_id"],
             "uri": media_fn(primary[m]["restored_path"], index, primary[m]["restored_sha256"])} for m in MODELS],
        "collection": [{"id": r["painting_id"], "title": r["title"], "category": r["category"],
                        "content": content(r["painting_id"]),
                        "uri": media_fn(processed[r["painting_id"]]["processed_path"], index, processed[r["painting_id"]]["sha256"])} for r in artworks],
        "observations": observations, "candidates": [primary[m] for m in MODELS],
    }
    if panel == "evidence":
        data["diagnostics"] = [r for r in rows(f"{D04}/metrics/real_damage_diagnostics.csv", index)
                               if r["painting_id"] == painting_id and r["candidate_role"] == "primary"]
    elif panel == "seeds":
        data["seeds"] = [{"seed": r["seed"], "candidate": r["candidate_id"], "uri": media_fn(r["restored_path"], index, r["restored_sha256"])} for r in seeds]
        data["uncertainty"] = [r for r in rows(f"{D04}/metrics/uncertainty_summary.csv", index) if r["painting_id"] == painting_id]
        data["seed_figure"] = media_fn(f"{D04}/figures/seed_variability/{painting_id}.png", index)
    elif panel == "comparison":
        data["comparison"] = next(r for r in rows(f"{D04}/data/synthetic_comparators.csv", index) if r["painting_id"] == painting_id)
        data["comparison_metrics"] = [r for r in rows(f"{D04}/metrics/synthetic_comparison.csv", index) if r["pair_id"] == painting_id]
        data["comparison_sources"] = panel_row
        data["comparison_images"] = [media_fn(panel_row[f"{kind}_panel_path"], index, panel_row[f"{kind}_panel_sha256"]) for kind in ("full", "detail")]
    elif panel == "report":
        data["report_uri"] = media_fn(f"{D04}/reports/real_damage_evaluation.html", index)
    return data
