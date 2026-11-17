"""Export the self-contained Academy source as a static, offline-readable page."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACADEMY = ROOT / "docs" / "academy"


def build():
    source = (ACADEMY / "source.html").read_text(encoding="utf-8")
    document = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">
<title>Restoration Evidence Academy — Controlled-300 and Physical Damage</title>
<style>:root{color-scheme:light dark;background:light-dark(#fff,#181818)}html,body{margin:0}body{box-sizing:border-box;padding:1rem;background:inherit}</style>
</head>
<body>
""" + source + "\n</body>\n</html>\n"
    (ACADEMY / "index.html").write_text(document, encoding="utf-8", newline="\n")
    print(f"Built docs/academy/index.html ({len(document.encode('utf-8')):,} bytes)")


if __name__ == "__main__":
    build()
