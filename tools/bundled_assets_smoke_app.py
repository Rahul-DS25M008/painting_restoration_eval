"""Separate public-reader demonstration; never imports the production dashboard."""

from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from restoration_eval.bundled_assets import RemoteBundleReader, sha256_bytes  # noqa: E402

st.set_page_config(page_title="N16 bundle smoke", layout="wide")
st.title("N16 bundle-backed image access — smoke test")
st.caption("Separate transport proof. This does not change the public thesis dashboard.")

record_path = ROOT / "outputs/inventory/bundled_publication_n16_smoke.json"
if not record_path.is_file():
    st.error("Run the CLI remote verification and smoke-read first.")
    st.stop()
record = json.loads(record_path.read_text(encoding="utf-8"))
if record.get("status") != "smoke_reader_verified":
    st.error("The public reader has not passed the bounded smoke test.")
    st.stop()

cache = ROOT / ".codex_tmp/bundled_assets/streamlit_cache"
reader = RemoteBundleReader(record["repo_id"], record["revision"],
                            record["prefix"], cache)
catalogue = reader.catalogue()
painting_id = st.selectbox("Painting", sorted(catalogue["paintings"]))
painting_index = reader.painting(painting_id, catalogue)
assets = painting_index["assets"]
labels = {row["asset_id"]: f"{row['map_type']} — {row['model_id']} — {row['asset_id']}"
          for row in assets}
asset_id = st.selectbox("Original image asset", list(labels), format_func=labels.get)

started = time.perf_counter()
data, row = reader.read_asset(painting_id, asset_id)
elapsed = time.perf_counter() - started
st.image(io.BytesIO(data), caption=row["original_relative_path"],
         use_container_width=True)
st.download_button("Download exact original PNG bytes", data=data,
                   file_name=Path(row["original_relative_path"]).name,
                   mime="image/png")
st.json({"painting_id": painting_id, "asset_id": asset_id,
         "case_id": row["case_id"], "candidate_id": row["candidate_id"],
         "map_type": row["map_type"], "model_id": row["model_id"],
         "source_sha256": row["sha256"], "retrieved_sha256": sha256_bytes(data),
         "bundle": row["bundle_path"], "member": row["member_path"],
         "pinned_revision": record["revision"],
         "fetch_seconds": round(elapsed, 3),
         "downloads_this_render": reader.download_count,
         "bytes_downloaded_this_render": reader.download_bytes})
st.info("The browser receives the selected image bytes. The reader fetches only its "
        "indexed ZIP bundle on a cold miss, verifies checksums, then reuses a bounded disk cache.")
