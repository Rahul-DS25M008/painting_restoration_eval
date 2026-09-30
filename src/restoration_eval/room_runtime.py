"""Non-visual room lifecycle and same-room Streamlit navigation.

The approved markup, styles, evidence and room controllers remain unchanged.
"""
import json
from pathlib import Path
import re
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

ASSETS = Path(__file__).resolve().parents[2] / "streamlit_assets/room_runtime"
PREFIXES = {
    "exhibition_foyer": (), "study_design": ("study_",),
    "metric_framework": ("metric_",), "model_gallery": ("gallery_",),
    "stability_lab": ("stability_",), "trustworthiness": ("trust_",),
    "focused_portrait_review": ("portrait_",), "case_explorer": ("ce_",),
    "research_archive": (),
}


def navigation_query(event, room):
    """Validate the transport boundary; room loaders validate evidence identities."""
    if not isinstance(event, dict) or event.get("room") != room:
        return None
    query = event.get("query")
    if not isinstance(query, dict) or query.get("room") != room or room not in PREFIXES:
        return None
    if len(query) > 40:
        return None
    for key, value in query.items():
        if not isinstance(key, str) or not isinstance(value, str) or len(value) > 4096:
            return None
        if key not in ("room", "tour") and not key.startswith(PREFIXES[room]):
            if not (room == "focused_portrait_review" and key == "return_room"
                    and value in ("study_design", "trustworthiness", "case_explorer")):
                return None
    return query


def install_room_navigation(room):
    """One invisible, bidirectional component; no browser document navigation."""
    bridge = components.declare_component("museum_room_navigation", path=str(ASSETS))
    st.html('<style>[data-testid="stElementContainer"]:has(iframe[title="restoration_eval.room_runtime.museum_room_navigation"]){display:none!important}</style>')
    event = bridge(room=room, acknowledged=st.session_state.get("_room_nav_ack", ""),
                   key="museum_room_navigation", default=None)
    if not isinstance(event, dict) or not isinstance(event.get("id"), str):
        return
    if event["id"] == st.session_state.get("_room_nav_ack"):
        return
    st.session_state["_room_nav_ack"] = event["id"]
    query = navigation_query(event, room)
    if query is not None and query != dict(st.query_params):
        st.query_params.from_dict(query)
    st.rerun()  # Acknowledge rejected/no-op requests too; never lock the bridge.


def room_html(markup):
    """Stamp each render so an earlier iframe cannot mount a later room's DOM."""
    revision = uuid4().hex
    stamped, count = re.subn(r"<main\b", f'<main data-room-render="{revision}"', markup, count=1)
    if count != 1:
        raise ValueError("Interactive room must contain a main element")
    st.html(stamped)
    return revision


def room_controller(script, revision):
    bootstrap = (ASSETS / "readiness.js").read_text(encoding="utf-8")
    source = bootstrap + "\nMuseumReadiness.watch(window, " + json.dumps(revision) + ", function(){\n" + script + "\n});"
    components.html("<script>" + source + "</script>", height=0, scrolling=False)
