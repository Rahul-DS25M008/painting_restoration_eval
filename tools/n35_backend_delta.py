"""Explicit nonvisual source delta, keeping original freeze baselines intact."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

BASE = "cf64ab2b4e8b3b90598dbd4b3b6a7ee983eb35f8"
ALLOWED = {
    "streamlit_app.py": ["file_data_uri", "recorded_study_image_uri", "recorded_metric_image_uri"],
    "src/restoration_eval/model_gallery.py": ["metric_index", "image_uri"],
    "src/restoration_eval/model_gallery_view.py": ["render_model_gallery"],
    "src/restoration_eval/stability_lab.py": ["spatial_index", "seed_catalogue"],
    "src/restoration_eval/trustworthiness.py": ["candidate_index", "assignment_records", "policy_records", "threshold_record"],
    "src/restoration_eval/focused_portrait.py": ["verified_source"],
    "src/restoration_eval/metric_inspection_view.py": ["load_inspection"],
    "src/restoration_eval/research_archive.py": ["selected_file"],
    "src/restoration_eval/case_explorer.py": ["payload"],
    "src/restoration_eval/dashboard_application.py": ["DashboardPackage.local_report_bytes"],
}


def sha(text): return hashlib.sha256(text.encode()).hexdigest()


def remaining_ast(source, allowed):
    tree = ast.parse(source)
    def kept(node, prefix=""):
        if isinstance(node, (ast.Import, ast.ImportFrom)): return False
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and prefix + node.name in allowed: return False
        if isinstance(node, ast.ClassDef): node.body = [r for r in node.body if kept(r, node.name + ".")]
        return True
    tree.body = [node for node in tree.body if kept(node)]
    return ast.dump(tree, include_attributes=False)


def baseline_source(root, relative):
    current = (root / relative).read_text(encoding="utf-8")
    path = root / "config/publication/n35_backend_delta.json"
    if not path.is_file(): return current
    manifest = json.loads(path.read_text())
    entry = manifest["files"].get(relative)
    if not entry: return current
    if sha(current) != entry["after_sha256"] or sha(entry["before_source"]) != entry["before_sha256"]:
        raise ValueError("Unreviewed change to backend delta: " + relative)
    if remaining_ast(current, ALLOWED[relative]) != remaining_ast(entry["before_source"], ALLOWED[relative]):
        raise ValueError("Change outside declared backend functions: " + relative)
    return entry["before_source"]


def build(root):
    files = {}
    for relative, allowed in ALLOWED.items():
        before = subprocess.check_output(["git", "show", BASE + ":" + relative], cwd=root).decode().replace("\r\n", "\n")
        after = (root / relative).read_text(encoding="utf-8")
        if remaining_ast(before, allowed) != remaining_ast(after, allowed):
            raise ValueError("Change outside backend scope: " + relative)
        # All presentation string literals in the sole changed view stay exact.
        if relative.endswith("model_gallery_view.py"):
            strings = lambda s: [n.value for n in ast.walk(ast.parse(s)) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
            if strings(before) != strings(after):
                # Additional identity lookups may repeat existing keys only.
                if set(strings(before)) != set(strings(after)):
                    raise ValueError("Presentation text changed")
        files[relative] = dict(before_sha256=sha(before), after_sha256=sha(after), before_source=before, allowed_functions=allowed)
    target = root / "config/publication/n35_backend_delta.json"
    target.write_text(json.dumps(dict(schema="n35_backend_delta.v1", base_commit=BASE,
        scope="User-requested nonvisual deployment adapters. Original frozen manifests remain unchanged.", files=files), indent=2)+"\n", encoding="utf-8")
    print("Recorded", len(files), "scoped backend deltas; untouched AST verified")


if __name__ == "__main__": build(Path(__file__).resolve().parents[1])
