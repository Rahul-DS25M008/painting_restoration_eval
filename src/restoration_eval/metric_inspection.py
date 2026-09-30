"""Explicit public contract for the Metric Framework's spatial companions.

These are inspection diagnostics, separate from the frozen benchmark tables.
Every enabled pair requires a registered raster; scalar-only fallback is forbidden.
"""
from __future__ import annotations

VERSION = "metric_inspection.v1"
REGIONS = {
    "whole": ("Whole image", "full_image"),
    "content": ("Painting content", "content_region"),
    "damaged": ("Damaged area", "masked_region"),
    "crop": ("Damage crop", "mask_bbox_crop"),
    "boundary": ("Boundary", "boundary_ring"),
    "outside": ("Outside repair", "outside_mask_content"),
    "patches": ("Local patches", "patch_window"),
}
LENSES = {
    "pixel": ("Pixel difference", "Absolute RGB error · MAE · MSE · PSNR", "Locate numerical differences from the clean reference."),
    "structure": ("Structure", "Local SSIM deficit", "Locate changes in luminance, contrast and structure."),
    "perceptual": ("Perceptual similarity", "Spatial LPIPS · AlexNet", "Inspect learned perceptual distance at its actual spatial resolution."),
    "features": ("Learned visual features", "CLIP · DINOv2", "Split view: CLIP left, DINO right. The two representations stay separate."),
    "spatial": ("Spatial change & improvement", "Signed improvement · Outside change", "Find where restoration improved or worsened reference error, or altered untouched content."),
    "local": ("Texture, colour & seams", "Texture residual · ΔE2000 · Seam mismatch", "The region selects the appropriate surface, colour or boundary diagnostic."),
    "semantic": ("Local meaning & layout", "DINO similarity · Reference affinity", "Split view: local representation left, layout-affinity drift right. Neither proves meaning."),
}
ROLES = {
    "pixel": "DPPPPPD", "structure": "DPXPXXD", "perceptual": "DPXPXXD",
    "features": "DPXPXXD", "spatial": "DPPDPPD", "local": "DPPPPPP",
    "semantic": "DPXPXXP",
}
RECOMMENDED = {key: ("damaged" if key in {"pixel", "spatial"} else "crop") for key in LENSES}


def resolve_pair(lens: str, region: str) -> dict:
    if lens not in LENSES or region not in REGIONS:
        raise ValueError(f"Unknown inspection pair: {lens}/{region}")
    role = dict(P="primary", D="diagnostic", X="prohibited")[ROLES[lens][list(REGIONS).index(region)]]
    result = dict(lens=lens, region=region, region_label=REGIONS[region][0],
                  canonical_region=REGIONS[region][1], role=role,
                  recommended=RECOMMENDED[lens], allowed=role != "prohibited")
    if role == "prohibited":
        return {**result, "reason": f"{LENSES[lens][0]} requires a contiguous rectangular image. {REGIONS[region][0]} is an irregular pixel set. Choose Damage crop or Painting content."}
    metric, recipe, units, limitation = {
        "pixel": ("Absolute RGB error", "pixel", "RGB / 255", "Pixel error does not describe meaning or historical correctness."),
        "structure": ("Local SSIM deficit", "ssim", "1 − SSIM", "A local structural proxy; not historical correctness."),
        "perceptual": ("Spatial LPIPS (AlexNet)", "lpips", "LPIPS distance", "Spatial companion; its mean is not the frozen scalar LPIPS score."),
        "features": ("Local CLIP / DINO distance", "features", "1 − cosine", "Coarse feature cells, not pixel attribution or semantic ground truth."),
        "spatial": ("Signed improvement", "improvement", "RGB / 255", "Improved reference fidelity does not establish historical correctness."),
        "local": ("Local texture residual", "texture", "relative energy error", "Texture energy is a surface proxy, not brushstroke authentication."),
        "semantic": ("DINO / affinity drift", "semantic", "cosine distance / affinity drift", "Representation and layout proxies; not a detector of historical meaning."),
    }[lens]
    if lens == "spatial" and region == "outside":
        metric, recipe, units = "Outside-repair alteration", "change", "RGB / 255"
    if lens == "local" and region in {"whole", "damaged", "outside"}:
        metric, recipe, units = "Colour difference ΔE2000", "colour", "ΔE2000"
        limitation = "Digital colour difference, not pigment analysis."
    if lens == "local" and region == "boundary":
        metric, recipe, units = "Boundary-gradient mismatch", "seam", "luminance gradient"
        limitation = "Measures seam discontinuity relative to the reference."
    if region == "patches":
        metric = "Patch " + metric[0].lower() + metric[1:]
    return {**result, "metric": metric, "recipe": recipe, "units": units,
            "limitation": limitation, "reason": "", "split": lens in {"features", "semantic"},
            "direction": "Blue: improved · red: worsened · pale: unchanged" if recipe == "improvement" else "Dark: lower difference · bright: higher difference",
            "calculation": "Damaged reference error − restored reference error" if recipe == "improvement" else
                "Restored − damaged absolute RGB difference" if recipe == "change" else "Restored compared with the clean digital reference"}


def public_contract() -> dict:
    return {f"{lens}:{region}": resolve_pair(lens, region) for lens in LENSES for region in REGIONS}
