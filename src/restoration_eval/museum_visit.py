"""Opt-in visitor overlay. Never alters a room's scene, styles or evidence."""
import json
from pathlib import Path
import streamlit.components.v1 as components

ASSETS=Path(__file__).resolve().parents[2]/'streamlit_assets/museum_visit'


def render_museum_visit(room, legacy_launch=False):
    payload=json.loads((ASSETS/'tour.json').read_text(encoding='utf-8'))
    payload.update(room=room,legacyLaunch=bool(legacy_launch))
    script=(ASSETS/'controller.js').read_text(encoding='utf-8')
    css=(ASSETS/'visit.css').read_text(encoding='utf-8')
    encoded=json.dumps(payload,ensure_ascii=True).replace('</','<\\/')
    css_encoded=json.dumps(css).replace('</','<\\/')
    components.html('<script>'+script+'\nMuseumVisit.install(window,'+encoded+','+css_encoded+');</script>',height=0,scrolling=False)
