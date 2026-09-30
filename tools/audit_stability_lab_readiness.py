"""Read-only inventory and bindings audit; emits JSON, never alters producer outputs."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "src"))
from restoration_eval.stability_lab import test_catalogue, seed_catalogue, selection, catalogue, metric, FAMILIES


def audit():
    cat=test_catalogue(); groups=seed_catalogue(); selected=selection({}); models=catalogue()["models"]
    values=[{"case_id":r["case_id"],**metric(models["lama"][r["case_id"]]["candidate_id"],"spatial_masked_error")} for r in selected["rows"]]
    def sha(path):return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    return {"status":"ready_for_initial_preview", "read_only":True,
        "focused_paintings":len(cat["paintings"]),"damage_cases":len(cat["size"]),"mask_cases":len(cat["mask"]),
        "generated_degradations":len(cat["degradation"]),"eligible_degradations":sum(r["degradation_family"] in FAMILIES for r in cat["degradation"]),
        "seed_groups":len(groups),"seed_memberships":sum(len(g["members"]) for g in groups.values()),"seed_pairs":sum(len(g["pairs"]) for g in groups.values()),
        "seed_prompts":sorted({g["prompt"] for g in groups.values()}),"opening_trajectory":values,
        "shell_sha256":sha("streamlit_assets/rooms/stability_lab_shell.png"),
        "approved_reference_sha256":sha("docs/dashboard_design_finalists/approved_current/07_stability_lab_final.png"),
        "n35_sha256":sha("notebooks/35_dashboard_and_deployment_validation.ipynb"),
        "caveats":["Canonical N18 groups have no per-case rendered overlay; numeric evidence remains available.","Fifth bottle opens excluded-task explanation, not a restoration ranking.","No hosted deployment has been created or tested."]}


if __name__=="__main__":
    print(json.dumps(audit(),indent=2,allow_nan=False))
