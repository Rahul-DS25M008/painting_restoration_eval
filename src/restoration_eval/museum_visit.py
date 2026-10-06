"""Opt-in visitor overlay. Never alters a room's scene, styles or evidence."""
import json
import logging
from pathlib import Path
from streamlit import runtime
import streamlit.components.v1 as components

ASSETS=Path(__file__).resolve().parents[2]/'streamlit_assets/museum_visit'


def tour_media():
    """Register same-origin, range-capable media; never inline the MP4 in HTML.

    This small adapter uses the media manager behind st.video in our pinned
    Streamlit 1.56 runtime. Registration must occur on each session run (not in
    a cached function), so Streamlit retains the media for that session.
    The browser gets only URLs; the controller requests the film on Play.
    """
    video = ASSETS / 'media/tour-overview-v1.mp4'
    poster = ASSETS / 'media/tour-overview-v1.jpg'
    if not video.is_file() or not poster.is_file() or not runtime.exists():
        return None
    try:
        manager = runtime.get_instance().media_file_mgr
        return {
            'video': manager.add(str(video), 'video/mp4', 'museum-visit.video'),
            'poster': manager.add(str(poster), 'image/jpeg', 'museum-visit.poster'),
            'duration': 115,
        }
    except (OSError, RuntimeError, AttributeError):
        logging.getLogger(__name__).exception('Tour overview unavailable; room route remains available')
        return None


def render_museum_visit(room, legacy_launch=False):
    payload=json.loads((ASSETS/'tour.json').read_text(encoding='utf-8'))
    payload.update(room=room,legacyLaunch=bool(legacy_launch),media=tour_media() if room == 'exhibition_foyer' else None)
    script=(ASSETS/'controller.js').read_text(encoding='utf-8')
    css=(ASSETS/'visit.css').read_text(encoding='utf-8')
    encoded=json.dumps(payload,ensure_ascii=True).replace('</','<\\/')
    css_encoded=json.dumps(css).replace('</','<\\/')
    components.html('<script>'+script+'\nMuseumVisit.install(window,'+encoded+','+css_encoded+');</script>',height=0,scrolling=False)
