"""Read-only N35 room-check utilities; importing this module performs no checks.

These helpers do not launch a server, generate evidence or persist N35 outputs.
AppTest exercises Python rendering/callbacks, never browser JavaScript.
"""
from __future__ import annotations

import ast
from contextlib import ExitStack, contextmanager
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
from pathlib import Path
import sys
import subprocess
import time
import unittest
from unittest.mock import patch


def digest(path, mode="binary"):
    raw = Path(path).read_bytes()
    if mode == "lf_normalized":
        raw = raw.replace(b"\r\n", b"\n")
    elif mode != "binary":
        raise ValueError(f"Unknown hash mode: {mode}")
    return hashlib.sha256(raw).hexdigest()


def snapshot(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): digest(p)
            for p in sorted(root.rglob("*")) if p.is_file()} if root.exists() else {}


def notebook_source_digest(path):
    """Pin cell structure/source, allowing normal output/metadata autosaves."""
    notebook = json.loads(Path(path).read_text(encoding="utf-8"))
    source = [(c["cell_type"], "".join(c["source"])) for c in notebook["cells"]]
    return hashlib.sha256(json.dumps(source, ensure_ascii=True).encode()).hexdigest()


def safe_path(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path outside project: {relative}")
    return path


def verify_freeze(root, relative):
    manifest = json.loads(safe_path(root, relative).read_text(encoding="utf-8"))
    if manifest.get("status") != "user_approved_visual_freeze":
        raise ValueError("Expected an approved visual-freeze manifest")
    files = manifest["files"]
    if not files or len({r["path"] for r in files}) != len(files):
        raise ValueError("Empty or duplicate freeze entries")
    from n35_backend_delta import baseline_source
    from n35_publication_delta import publication_baseline, verify_added_files
    if relative == "config/publication/research_archive_freeze.json":
        verify_added_files(root)
    result = []
    for r in files:
        observed = digest(safe_path(root, r["path"]), r["hash_mode"])
        baseline = baseline_source(Path(root), r["path"]) if r["path"].endswith(".py") else None
        if baseline is None and r["hash_mode"] == "lf_normalized":
            current = safe_path(root, r["path"]).read_text(encoding="utf-8")
            baseline = publication_baseline(root, r["path"], current)
        if baseline is not None and r["hash_mode"] == "lf_normalized":
            observed = hashlib.sha256(baseline.encode()).hexdigest()
        result.append({"path": r["path"], "expected": r["sha256"], "observed": observed})
    return result


def normalize_gallery_transport(source):
    """Undo only the two approved non-visual e88feea5 transport substitutions.

    The result is compared to the original a2bf09e8 Gallery freeze. Any other
    edit still changes that checksum; no current bytes become a new baseline.
    """
    replacements = (
        ('    from .room_runtime import room_html, room_controller\n'
         '    revision = room_html(re.sub(r"<svg\\b.*?</svg>", svg_image, scene, flags=re.DOTALL))',
         '    st.html(re.sub(r"<svg\\b.*?</svg>", svg_image, scene, flags=re.DOTALL))'),
        ('    room_controller(controller.replace("__GALLERY_PAYLOAD__", serialized), revision)',
         '    components.html("<script>" + controller.replace("__GALLERY_PAYLOAD__", serialized) + "</script>", height=0, scrolling=False)'),
    )
    for current, previous in replacements:
        if source.count(current) != 1:
            raise ValueError("Approved Gallery transport substitution missing or ambiguous")
        source = source.replace(current, previous, 1)
    return source


def verify_gallery_freeze(root):
    rows = verify_freeze(root, "config/publication/model_gallery_freeze.json")
    for row in rows:
        if row["path"] == "src/restoration_eval/model_gallery_view.py":
            from n35_backend_delta import baseline_source
            source = baseline_source(Path(root), row["path"])
            row["raw_observed"] = row["observed"]
            row["observed"] = hashlib.sha256(normalize_gallery_transport(source).encode()).hexdigest()
            row["normalization"] = "Only approved e88feea5 room transport; visual source unchanged"
    # The transport's implementation remains pinned by the later approved freeze.
    runtime = [r for r in verify_freeze(root, "config/publication/museum_visit_freeze.json")
               if r["path"] == "src/restoration_eval/room_runtime.py"]
    if len(runtime) != 1:
        raise ValueError("Missing approved shared transport fingerprint")
    return rows + runtime


def literals(path):
    result = {}
    for node in ast.parse(Path(path).read_text(encoding="utf-8")).body:
        targets = (node.targets if isinstance(node, ast.Assign) else
                   [node.target] if isinstance(node, ast.AnnAssign) else [])
        for target in targets:
            if isinstance(target, ast.Name):
                try:
                    result[target.id] = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    pass  # Computed assignments are deliberately not executed.
    return result


@contextmanager
def offline():
    """Block outbound Python network attempts, including attempts caught by app code."""
    attempts = []

    def denied(*args, **kwargs):
        attempts.append("outbound_network_attempt")
        raise RuntimeError("N35 local validation forbids outbound network access")

    with ExitStack() as stack:
        for name in ("socket.create_connection", "socket.socket.connect",
                     "socket.socket.connect_ex", "urllib.request.urlopen",
                     "urllib.request.urlretrieve"):
            stack.enter_context(patch(name, side_effect=denied))
        yield attempts


def app_html(app):
    """Include both legacy Markdown scenes and current st.html scenes."""
    return "\n".join([str(e.value) for e in app.markdown]
                     + [str(e.proto.body) for e in app.get("html")])


def app_errors(app):
    return ([str(e.value) for e in app.exception]
            + [str(e.value) for e in app.error])


def controller_payload(app):
    """Read the exact JSON handed to the room controller without executing JS."""
    found = []
    for element in app.get("iframe"):
        source = str(element.proto.srcdoc)
        if "MuseumReadiness.watch" not in source:
            continue
        for match in re.finditer(r"\bconst\s+data\s*=\s*(?=\{)", source):
            value, _ = json.JSONDecoder().raw_decode(source[match.end():])
            found.append(value)
    if len(found) != 1:
        raise ValueError(f"Expected one exact room-controller payload; found {len(found)}")
    return found[0]


def room_smoke(app_path, query, timeout=120):
    from streamlit.testing.v1 import AppTest
    start = time.monotonic()
    with offline() as attempts:
        app = AppTest.from_file(str(app_path), default_timeout=timeout)
        for key, value in query.items():
            app.query_params[key] = value
        app.run()
    return {"app": app, "html": app_html(app), "errors": app_errors(app),
            "network_attempts": attempts, "elapsed_seconds": time.monotonic() - start}


def _flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item


def run_suite(root, group):
    """Run only current room tests, without treating skipped/empty suites as passing.

    The Gallery's frozen historical notebook-hash assertion is NOT a scientific
    assertion. Replace only that obsolete test with a current before/after
    notebook-source + canonical-output snapshot check; retain its frozen file unchanged.
    Execution counts and outputs may legitimately autosave during a user run.
    """
    root = Path(root).resolve()
    groups = {"study": ("test_dashboard_application.py",),
              "metric": ("test_metric_inspection.py",),
              "gallery": ("test_model_gallery.py",),
              "stability": ("test_stability_lab.py",),
              "trust_portrait": ("test_trustworthiness.py", "test_trustworthiness_presentation.py", "test_focused_portrait.py"),
              "case": ("test_case_explorer.py", "test_room_runtime.py"),
              "archive": ("test_research_archive.py",)}
    if group not in groups:
        raise ValueError(f"Unknown suite: {group}")
    notebook = root / "notebooks/35_dashboard_and_deployment_validation.ipynb"
    output = root / "outputs/35_dashboard_and_deployment_validation"
    before = (notebook_source_digest(notebook), snapshot(output))
    for folder in (root / "src", root / "tools"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    selected, excluded = [], []
    with offline() as attempts:
        for filename in groups[group]:
            spec = importlib.util.spec_from_file_location(
                "n35_checks_" + Path(filename).stem, root / "tests" / filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for test in _flatten(unittest.defaultTestLoader.loadTestsFromModule(module)):
                if (group == "gallery" and isinstance(test, unittest.FunctionTestCase)
                        and test.shortDescription() == "test_notebook_is_not_modified_by_gallery_work"):
                    excluded.append(test.shortDescription())
                else:
                    selected.append(test)
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite(selected))
    after = (notebook_source_digest(notebook), snapshot(output))
    unchanged = before == after
    integrity_changes = {
        "notebook_source_changed": before[0] != after[0],
        "notebook_source_before": before[0],
        "notebook_source_after": after[0],
        "canonical_output_changes": sorted(
            path for path in set(before[1]) | set(after[1])
            if before[1].get(path) != after[1].get(path)),
    }
    expected_exclusions = (["test_notebook_is_not_modified_by_gallery_work"]
                           if group == "gallery" else [])
    minimum = {"study": 29, "metric": 25, "gallery": 10, "stability": 13,
               "trust_portrait": 28, "case": 21, "archive": 16}[group]
    return {"group": group, "run": result.testsRun, "skipped": len(result.skipped),
            "failures": len(result.failures), "errors": len(result.errors),
            "excluded_historical_checks": excluded,
            "current_notebook_source_and_canonical_outputs_unchanged": unchanged,
            "integrity_changes": integrity_changes,
            "remediation": ("" if unchanged else
                "Save all pasted cells and cell types before rerunning. Do not edit notebook source while checks run. "
                "If canonical outputs changed, investigate that mutation; do not waive the guard."),
            "network_attempts": attempts, "transcript": stream.getvalue(),
            "passed": (result.wasSuccessful() and not result.skipped
                       and result.testsRun >= minimum and not attempts and unchanged
                       and excluded == expected_exclusions)}


def required_stages(checks, names):
    """Require nonempty successful stages, not merely an empty failure collection."""
    for name in names:
        rows = [c for c in checks if c.validation_stage == name]
        if not rows or any(not c.passed and c.severity == "blocking" for c in rows):
            raise RuntimeError(f"Run the prerequisite cell successfully first: {name}")


def verify_later_room_freeze(root, name):
    """Honor original room freezes plus only the approved e88feea5 transport delta."""
    configs = {
        "stability_lab": ('re.sub(r"<svg\\b.*?</svg>", nav_svg, scene, flags=re.DOTALL)',
                          'controller.replace("__STABILITY_PAYLOAD__", serialized)'),
        "trustworthiness": ('nav_images("".join(parts))', 'js.replace("__TRUST_PAYLOAD__", serialized)'),
        "focused_portrait": ("f'<style>{css}</style>'+room_markup(data,navigation,shell,reference)",
                             "js.replace('__PORTRAIT_PAYLOAD__',serialized)"),
    }
    rows = verify_freeze(root, f"config/publication/{name}_freeze.json")
    if name not in configs:
        if name != "research_archive":
            raise ValueError("Unknown room freeze")
        return rows
    expression, controller = configs[name]
    for row in rows:
        if row["path"] != f"src/restoration_eval/{name}_view.py":
            continue
        source = safe_path(root, row["path"]).read_text(encoding="utf-8")
        before = '    from .room_runtime import room_html, room_controller\n    revision = room_html(' + expression + ')'
        after = '    st.html(' + expression + ')'
        old_controller = ("    components.html('<script>'+" + controller + "+'</script>',height=0,scrolling=False)"
                          if name == "focused_portrait" else
                          '    components.html("<script>" + ' + controller + ' + "</script>", height=0, scrolling=False)')
        replacements = ((before, after), ('    room_controller(' + controller + ', revision)', old_controller))
        for current, original in replacements:
            if source.count(current) != 1:
                raise ValueError(f"Missing/ambiguous approved transport substitution: {name}")
            source = source.replace(current, original, 1)
        row["raw_observed"] = row["observed"]
        row["observed"] = hashlib.sha256(source.encode()).hexdigest()
        row["normalization"] = "Two approved e88feea5 non-visual transport substitutions only"
    return rows


def verify_committed_files(root, revision, relatives):
    """Compare to an explicit approved commit, never bless the current worktree."""
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("A full immutable Git commit is required")
    rows = []
    for relative in relatives:
        local = safe_path(root, relative).read_bytes()
        if relative.endswith(".py"):
            from n35_backend_delta import baseline_source
            local = baseline_source(Path(root), relative).encode()
        saved = subprocess.run(["git", "show", f"{revision}:{relative}"], cwd=root,
                               capture_output=True, check=True, timeout=30).stdout
        if saved.startswith(b"version https://git-lfs.github.com/spec/v1"):
            raise ValueError("A Git LFS pointer is not the saved artifact bytes")
        if Path(relative).suffix in (".py", ".js", ".css", ".json", ".cjs", ".html"):
            saved, local = saved.replace(b"\r\n", b"\n"), local.replace(b"\r\n", b"\n")
        rows.append(dict(path=relative, expected=hashlib.sha256(saved).hexdigest(),
                         observed=hashlib.sha256(local).hexdigest()))
    return rows


def node_checks(root, filenames):
    """Run explicit offline controller unit scripts, not browser interaction tests."""
    node = os.environ.get("N35_NODE") or shutil.which("node")
    if not node:
        # Optional existing desktop runtime; no installation or PATH mutation.
        bundled = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
        if bundled.is_file():
            node = str(bundled)
    if not node:
        raise RuntimeError("Node is needed only for validation scripts. Set N35_NODE to an existing node executable and rerun; no test was skipped.")
    rows = []
    for filename in filenames:
        path = safe_path(root, filename)
        syntax = subprocess.run([node, "--check", str(path)], cwd=root,
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        result = subprocess.run([node, str(path)], cwd=root,
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        rows.append(dict(path=filename, syntax_returncode=syntax.returncode,
                         returncode=result.returncode, stdout=result.stdout, stderr=result.stderr,
                         passed=syntax.returncode == result.returncode == 0))
    return rows
