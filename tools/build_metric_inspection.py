"""Build reproducible, aligned loupe companions without executing any notebook.

Usage: .venv/Scripts/python tools/build_metric_inspection.py --paintings p018
Omit --paintings for all 300 canonical mixed-damage LaMa exhibits.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np
import pandas as pd
from PIL import Image
from skimage.metrics import structural_similarity
from skimage.color import rgb2gray, rgb2lab, deltaE_ciede2000
from scipy.ndimage import sobel
from matplotlib import colormaps
from restoration_eval.dashboard_application import open_dashboard_package
from restoration_eval.metric_inspection import VERSION, public_contract
from restoration_eval.regions import (full_image_region, content_region, masked_region,
    mask_bbox_region, boundary_region, outside_mask_content_region, patch_regions)
from restoration_eval.local_consistency import compute_local_texture_maps, load_local_consistency_config
from restoration_eval.metrics_lpips import load_lpips_config, prepare_lpips_tensor
from restoration_eval.semantic_structural import (load_semantic_structural_config,
    load_semantic_feature_models, extract_local_token_batch)

DEST = ROOT / "streamlit_assets/evidence/metric_framework"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resize(values, size, nearest=False):
    return np.asarray(Image.fromarray(values.astype(np.float32)).resize(size,
        Image.Resampling.NEAREST if nearest else Image.Resampling.BILINEAR), dtype=np.float32)


def aligned(values, bbox, shape, *, nearest=False):
    x0, y0, x1, y1 = bbox
    result = np.full(shape, np.nan, np.float32)
    result[y0:y1, x0:x1] = resize(values, (x1-x0, y1-y0), nearest)
    return result


def unletterbox(values, width, height):
    # Same centered 224px geometry as extract_local_token_batch, with nearest
    # interpolation preserving the actual 7x7 / 16x16 token support.
    scale = 224 / max(width, height)
    w, h = max(1, round(width * scale)), max(1, round(height * scale))
    x, y = (224-w)//2, (224-h)//2
    dense = resize(values, (224, 224), True)
    return dense[y:y+h, x:x+w]


class Encoders:
    def __init__(self):
        import torch, lpips
        self.torch = torch
        torch.set_num_threads(4)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        torch.manual_seed(0)
        torch.backends.cudnn.benchmark = False
        self.lpconfig = load_lpips_config(ROOT / "config/evaluation/lpips.yaml")
        self.semconfig = load_semantic_structural_config(ROOT / "config/evaluation/semantic_structural.yaml")
        self.lp = lpips.LPIPS(net="alex", version="0.1", spatial=True, verbose=False).to(self.device).eval()
        self.models = load_semantic_feature_models(self.semconfig, device=self.device, local_only=True)
        print(f"Loaded pinned CLIP, DINOv2 and spatial LPIPS on {self.device}", flush=True)

    def lpips(self, ref, out):
        a, geometry = prepare_lpips_tensor(ref, self.lpconfig)
        b, _ = prepare_lpips_tensor(out, self.lpconfig)
        with self.torch.inference_mode():
            val = self.lp(a[None].to(self.device), b[None].to(self.device))[0,0].cpu().numpy()
        g = geometry
        return val[g.pad_top:g.pad_top+g.resized_height, g.pad_left:g.pad_left+g.resized_width]

    def semantic_batch(self, refs, outs):
        output = {}
        for key, model in self.models.items():
            values = []
            for start in range(0, len(refs), 12):
                ra, oa = refs[start:start+12], outs[start:start+12]
                tokens, globals_, valid = extract_local_token_batch(ra+oa,
                    feature_model_id=key, model_bundle=model, config=self.semconfig, device=self.device)
                n = len(ra)
                for i in range(n):
                    mask = valid[i] & valid[i+n]
                    dist = 1-np.sum(tokens[i]*tokens[i+n], axis=-1)
                    affinity = np.abs(np.sum(tokens[i]*globals_[i], axis=-1)-np.sum(tokens[i+n]*globals_[i],axis=-1))
                    values.append((np.where(mask, dist, np.nan), np.where(mask, affinity, np.nan)))
            output[key] = values
        return output


def regions_for(shape, bbox, mask):
    content = content_region(shape, bbox)
    regions = {
        "whole": full_image_region(shape), "content": content,
        "damaged": masked_region(mask & content.mask),
        "crop": mask_bbox_region(mask, margin=8, support_bbox=bbox),
        "boundary": boundary_region(mask, width_pixels=3, support_mask=content.mask),
        "outside": outside_mask_content_region(mask, content_bbox=bbox),
    }
    patches = patch_regions(shape, patch_size=224, stride=112,
        support_mask=content.mask, minimum_support_fraction=.5)
    return regions, patches


def patch_assignment(patches, shape):
    """Compute window ownership once for all diagnostics of a painting."""
    yy,xx=np.ogrid[:shape[0],:shape[1]]
    nearest=np.zeros(shape,np.int32)
    best=np.full(shape,np.inf)
    support=np.zeros(shape,bool)
    for index,p in enumerate(patches):
        cx,cy=(p.x_min+p.x_max)/2,(p.y_min+p.y_max)/2
        distance=(xx-cx)**2+(yy-cy)**2
        closer=distance<best
        nearest[closer]=index;best[closer]=distance[closer]
        support|=p.mask
    return nearest,support


def patch_field(values, patches, shape, assignment=None):
    # Voronoi assignment to actual overlapping window centres; no smoothing of
    # scalar window scores. The loupe snaps to and outlines the source window.
    nearest,support=assignment if assignment is not None else patch_assignment(patches,shape)
    return np.where(support, np.asarray(values)[nearest], np.nan).astype(np.float32)


def seam_difference(reference, restored):
    """Match the normalized Sobel convention of local_consistency._gradient."""
    gradient = lambda a: np.hypot(sobel(a, axis=0), sobel(a, axis=1)) / 8.0
    return np.abs(gradient(rgb2gray(reference))-gradient(rgb2gray(restored))).astype(np.float32)


def build_one(pid, package, geom, enc, local_config):
    target = DEST / pid
    target.mkdir(parents=True, exist_ok=True)
    payload = package.load_painting(pid)
    case_id = f"canonical__{pid}__mixed_damage"
    cid = f"candidate__lama__{case_id}__c00"
    case, = [x for x in payload["cases"] if x["case_id"] == case_id]
    candidate, = [x for x in payload["candidates"] if x["candidate_id"] == cid]
    sources = dict(reference=payload["painting"]["clean_image_path"], damaged=case["input_image_path"],
        restored=candidate["asset_routes"]["restored"][0], mask=case["mask_or_effect_path"])
    arrays = {k: np.asarray(Image.open(ROOT/v).convert("L" if k == "mask" else "RGB")) for k,v in sources.items()}
    ref, out, damaged = (arrays[k] for k in ("reference", "restored", "damaged"))
    shape = ref.shape[:2]
    assert ref.shape == out.shape == damaged.shape and shape == arrays["mask"].shape
    bbox = tuple(int(geom[f"content_{axis}_{edge}"]) for axis,edge in (("x","min"),("y","min"),("x","max"),("y","max")))
    regions, patches = regions_for(shape, bbox, arrays["mask"] >= 128)
    assert len(patches) > 0
    error = np.abs(ref.astype(np.float32)-out)/255
    pixel = error.mean(axis=-1)
    baseline = np.abs(ref.astype(np.float32)-damaged).mean(axis=-1)/255
    change = np.abs(out.astype(np.float32)-damaged).mean(axis=-1)/255
    refgray, outgray = rgb2gray(ref), rgb2gray(out)
    texture = compute_local_texture_maps(refgray, outgray, config=local_config)["local_texture_error"]
    raw = {"pixel": pixel, "improvement": baseline-pixel, "change": change, "texture": texture,
        "colour": deltaE_ciede2000(rgb2lab(ref), rgb2lab(out)), "seam": seam_difference(ref,out)}
    rects = [regions[x] for x in ("whole", "content", "crop")] + patches
    refs = [ref[r.y_min:r.y_max,r.x_min:r.x_max] for r in rects]
    outs = [out[r.y_min:r.y_max,r.x_min:r.x_max] for r in rects]
    sem = enc.semantic_batch(refs, outs)
    patch_values = {k: [] for k in ("pixel","improvement","texture","ssim","lpips","clip","dino","affinity")}
    for i, (r, a, b) in enumerate(zip(rects, refs, outs)):
        score, ssim = structural_similarity(a, b, data_range=255, channel_axis=2, full=True, win_size=7)
        deficit = 1-ssim.mean(axis=-1)
        # SSIM ignores the half-window border in its scalar reduction. Match
        # that support in the visual companion rather than imply padded evidence.
        deficit[:3] = np.nan; deficit[-3:] = np.nan; deficit[:,:3] = np.nan; deficit[:,-3:] = np.nan
        lp = enc.lpips(a,b)
        clip, _ = sem["clip_vit_b32"][i]
        dino, affinity = sem["dinov2_vits14"][i]
        if i < 3:
            name = ("whole", "content", "crop")[i]
            raw[f"ssim_{name}"] = aligned(deficit,r.bbox,shape)
            raw[f"lpips_{name}"] = aligned(lp,r.bbox,shape)
            for key, val in (("clip",clip),("dino",dino),("affinity",affinity)):
                raw[f"{key}_{name}"] = aligned(unletterbox(val,r.width,r.height),r.bbox,shape,nearest=True)
        else:
            for k in ("pixel","improvement","texture"):
                patch_values[k].append(float(np.mean(raw[k][r.mask])))
            for k, val in (("ssim",1-score),("lpips",np.mean(lp)),("clip",np.nanmean(clip)),("dino",np.nanmean(dino)),("affinity",np.nanmean(affinity))):
                patch_values[k].append(float(val))
    ownership=patch_assignment(patches,shape)
    for key, val in patch_values.items():
        raw[f"{key}_patches"] = patch_field(val,patches,shape,ownership)
    # Raw numeric companions retain source resolution; visualization scales are
    # fixed across paintings/regions, stated in every plaque, never auto-stretched.
    limits = {"pixel":(0,1),"improvement":(-1,1),"change":(0,1),"texture":(0,3),
        "colour":(0,100),"seam":(0,1),"ssim":(0,2),"lpips":(0,1),"clip":(0,2),"dino":(0,2),"affinity":(0,2)}
    assets = {}
    for key, val in raw.items():
        family = key.split("_")[0]
        lo, hi = limits[family]
        norm = np.clip((val-lo)/(hi-lo),0,1)
        rgba = colormaps["RdBu" if family == "improvement" else "magma"](np.nan_to_num(norm), bytes=True)
        rgba[...,3] = np.where(np.isfinite(val),255,0)
        path = target / f"{key}.png"
        Image.fromarray(rgba).save(path)
        assets[key] = dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),min=lo,max=hi,
            clipped_fraction=float(np.mean((val < lo)|(val > hi))))
    numeric_path = target / "numeric.npz"
    np.savez_compressed(numeric_path, **{k:v.astype(np.float16) for k,v in raw.items()})
    supports = {k:v.mask for k,v in regions.items()}
    supports["patches"] = np.logical_or.reduce([p.mask for p in patches])
    region_records = {}
    for key, mask in supports.items():
        path = target / f"support_{key}.png"
        Image.fromarray((mask*255).astype(np.uint8)).save(path)
        ys,xs = np.where(mask)
        centre = [float(xs.mean()/shape[1]),float(ys.mean()/shape[0])]
        # Ensure the initial inspection point belongs to the selected support.
        index = np.argmin((xs-centre[0]*shape[1])**2+(ys-centre[1]*shape[0])**2)
        centre = [float(xs[index]/shape[1]),float(ys[index]/shape[0])]
        region_records[key] = dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),centre=centre,pixels=int(mask.sum()))
    pairs = public_contract()
    for key, spec in pairs.items():
        if not spec["allowed"]:
            continue
        r, recipe = spec["region"],spec["recipe"]
        suffix = "patches" if r == "patches" else r
        if recipe in {"ssim","lpips"}: names = [f"{recipe}_{suffix}"]
        elif recipe == "features": names = [f"clip_{suffix}",f"dino_{suffix}"]
        elif recipe == "semantic": names = [f"dino_{suffix}",f"affinity_{suffix}"]
        elif r == "patches": names = [f"{recipe}_patches"]
        else: names = [recipe]
        spec["maps"] = names
        values = [raw[n][supports[r] & np.isfinite(raw[n])] for n in names]
        if any(len(v) == 0 for v in values):
            raise ValueError(f"Empty evidence {pid} {key}")
        spec["summary"] = [dict(mean=float(np.mean(v)),p95=float(np.percentile(v,95))) for v in values]
        spec["scale"] = [limits[n.split("_")[0]] for n in names]
        if r == "patches": spec["patch_values"] = [patch_values[n.split("_")[0]] for n in names]
        if spec["lens"] == "pixel":
            mse = float(np.mean(error[supports[r]]**2))
            spec["pixel_metrics"] = dict(mae=float(np.mean(pixel[supports[r]])),mse=mse,psnr=None if mse == 0 else float(-10*np.log10(mse)))
    meta = dict(version=VERSION,painting_id=pid,case_id=case_id,candidate_id=cid,
        title=payload["painting"]["title"],shape=list(shape),sources={k:dict(path=v,sha256=sha(ROOT/v)) for k,v in sources.items()},
        assets=assets,regions=region_records,pairs=pairs,
        patches=[list(p.bbox) for p in patches],numeric_sha256=sha(numeric_path),
        provenance={"purpose":"Spatial inspection companions; frozen benchmark tables unchanged", "torch":str(enc.torch.__version__),
            "device":enc.device,"lpips":"AlexNet v0.1 spatial=True; registered aspect-preserving resize",
            "feature_models":enc.semconfig["semantic_structural"]["feature_models"],
            "patches":"224x224 / stride112 / at least50% content; nearest-window display", "ssim":"RGB, win7, data_range255; 3px unsupported border",
            "texture":"Notebook17 local texture-energy residual", "seam":"absolute difference of normalized Sobel luminance-gradient magnitude", "seam_gradient_divisor":8,
            "numeric_storage":"float16 inspection archive; summaries calculated in float32"})
    manifest_tmp=target/"manifest.json.tmp"
    manifest_tmp.write_text(json.dumps(meta,allow_nan=False,separators=(",",":")),encoding="utf-8")
    manifest_tmp.replace(target/"manifest.json")
    return meta


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--paintings",nargs="*"); ap.add_argument("--force",action="store_true")
    args=ap.parse_args()
    package=open_dashboard_package(ROOT)
    ids=args.paintings or list(package.painting_lookup.painting_id.astype(str))
    geom=pd.read_csv(ROOT/"outputs/02_image_preprocessing/data/preprocessed_images.csv").set_index("painting_id")
    local=load_local_consistency_config(ROOT/"config/evaluation/local_consistency.yaml")
    enc=None; start=time.monotonic()
    for i,pid in enumerate(ids):
        existing=DEST/pid/"manifest.json"
        if existing.exists() and not args.force and json.loads(existing.read_text())["version"] == VERSION:
            continue
        if enc is None: enc=Encoders()
        build_one(pid,package,geom.loc[pid],enc,local)
        print(f"{i+1}/{len(ids)} {pid}: 37 pairs ready ({time.monotonic()-start:.1f}s)",flush=True)


if __name__ == "__main__": main()
