"""Reference-aligned Research Archive presentation; other rooms are untouched."""
import base64
import html
import json
import mimetypes
import re

import streamlit as st
import streamlit.components.v1 as components

from .model_gallery import image_uri
from .research_archive import ROOT, catalogue, href, payload, selected_file, verify_manifest
from .room_runtime import room_html, room_controller
from .dashboard_application import DashboardContractError


def rect(x,y,w,h):
    return f'left:{x/1672*100:.5f}%;top:{y/941*100:.5f}%;width:{w/1672*100:.5f}%;height:{h/941*100:.5f}%'


def reference_window(box):
    """Lossless CSS viewport into the approved 1672 × 941 reference pixels."""
    x,y,w,h=box
    return f'background-size:{1672/w*100:.6f}% {941/h*100:.6f}%;background-position:{x/(1672-w)*100:.6f}% {y/(941-h)*100:.6f}%'


def room_markup(data,navigation,shell,lettering=None,portraits=None):
    esc=html.escape
    parts=[f'<main class="ra-stage" aria-label="Research Archive" style="background-image:url({shell})">',navigation]
    if lettering:
        parts.append(f'<img class="ra-lettering-source" src="{esc(lettering)}" alt="" hidden>')
    # Decorative ink only: preserve the original room, parchment and frame pixels.
    for name,box in [('azhdaha',(1264,290,47,56)),('leto_ii',(1102,347,33,43)),('dragon',(1334,339,39,43))]:
        if portraits and name in portraits:
            parts.append(f'<img class="ra-portrait ra-portrait-{name}" src="{esc(portraits[name],quote=True)}" alt="" aria-hidden="true" draggable="false" style="{rect(*box)}">')
    def text(cls,box,content): parts.append(f'<div class="{cls}" style="{rect(*box)}">{content}</div>')
    def button(action,box,label,cls='ra-label',aria=None):
        parts.append(f'<button type="button" class="{cls}" data-action="{action}" aria-label="{esc(aria or re.sub("<[^>]+>"," ",label))}" style="{rect(*box)}">{label}</button>')
    def art(box,content,cls='ra-art'):
        parts.append(f'<div class="{cls} ra-reference-window" style="{rect(*box)};{reference_window(box)}"><div class="ra-art-copy">{content}</div></div>')
    def art_button(action,box,label,cls='ra-art-button'):
        parts.append(f'<button type="button" class="{cls} ra-art-button ra-reference-window" data-action="{esc(action)}" aria-label="{esc(label)}" title="{esc(label)}" style="{rect(*box)};{reference_window(box)}"><span class="ra-art-copy">{esc(label)}</span></button>')
    art((532,58,620,125),'<h1>Research Archive</h1><h2>Trace every conclusion to its saved evidence.</h2><p>The archive records what was used, what passed, what is missing, and where each artifact lives.</p>','ra-title')
    art((291,60,161,107),'EVIDENCE<br>PRESERVES<br>TRUTH','ra-wall-inscription')
    art((1231,62,183,107),'QUESTIONS<br>ADVANCE<br>CONSERVATION','ra-wall-inscription')
    art((789,341,90,88),'ART<br>TECHNOLOGY<br>EVIDENCE<br>HUMANITY')
    art_button('search',(39,213,159,62),'Search the archive')
    art_button('search',(42,271,153,58),'Search all Archive catalogues')
    pop=data['population']
    for action,y,label,count in [('paintings',338,'Paintings',pop['painting_count']),('cases',386,'Cases',pop['registered_case_count']),('candidates',435,'Candidates',pop['indexed_inspectable_candidate_count']),('reports',485,'Reports',pop['n32_browsable_record_count']),('models',533,'Models',pop['model_report_count'])]:
        art_button(action,(40,y-6,156,43),f'{label} · {count:,}')
    art((40,577,157,46),'Controlled-300 records only')
    for action,box,label in [('paintings',(283,215,188,55),'Painting Provenance'),('reports',(499,243,191,43),'Case & Painting Reports'),('models',(997,244,161,41),'Model Reports'),('runs',(1197,222,195,51),'Runs & Checksums')]:
        art_button(action,box,label)
    art((1463,223,145,60),'Limits are part of the record')
    for group,y,h in [('Dataset',286,52),('Models',347,49),('Interpretation',405,46),('Use',463,42)]:
        art_button('limits:'+group,(1483,y,102,h),group)
    art((1470,524,135,55),'No universal quality score<br>No conservation approval')
    art((642,540,192,192),'Final evaluation · N33<br>Study record<br>33-stage primary pipeline<br>2 supplementary studies: N12A · D02<br>24 final figures<br>49 evidence claims<br>18 recorded limitations')
    # D01 is a linked frozen decision, not a third supplementary study. The
    # original two-study lettering stays exact; the existing popup includes D01.
    for action,y,label in [('runs',585,'33-stage primary pipeline'),('runs',609,'N12A and D02 supplementary studies; D01 linked decision'),('figures',632,'24 final figures'),('claims',655,'49 evidence claims'),('limits',679,'18 recorded limitations')]:
        button(action,(648,y,186,24),f'<span class="ra-art-copy">{esc(label)}</span>','ra-art-hit',label)
    art((858,552,216,28),'Evidence trace')
    art_button('final_sources',(862,581,213,43),'Trace saved evidence sources')
    art((865,634,229,29),f"{data['checks']['passed']} / {data['checks']['total']} final-report checks passed")
    # Restore the seal's lower edge without importing the reference's sample run text.
    art((863,633,47,45),'Final-report validation seal','ra-validation-seal')
    n33=next(s for s in data['stages'] if s['id']=='N33')
    text('ra-run-caption',(912,666,186,37),f'<span>Run</span><code>{esc(n33["run_id"])}</code><span>Recorded commit</span><code>{esc(n33["git_commit"])}</code>')
    for action,x,w,label in [('final_report',861,74,'Open report'),('final_sources',940,81,'Trace sources'),('verify',1025,83,'Verify checksum')]:
        art_button(action,(x,711,w,29),label)
    for action,box,label in [('paintings',(374,683,144,32),'Source Ledger'),('runs',(374,717,148,36),'Run Manifests'),('models',(376,754,147,38),'Model Cards'),('checksums',(376,790,153,39),'Checksum Index')]:
        art_button(action,box,label)
    art_button('reports',(547,708,156,128),'Browse reports: 331 N32 records, five model reports, one final evaluation')
    for action,box,label in [('destinations',(1243,632,87,61),'GitHub code & compact records'),('publications:candidates',(1348,643,95,63),'HF Candidates restorations'),('publications:diagnostics',(1457,652,114,67),'HF Diagnostics maps, metrics & reports')]:
        art_button(action,box,label)
    art_button('zenodo',(1238,724,134,71),'Zenodo published · '+data['zenodo']['version']+' · '+data['zenodo']['doi'],cls='ra-zenodo-published')
    art_button('publications',(1391,742,178,76),f'{data["individual_publications"]:,} / {data["individual_publications"]:,} individually published artifacts recorded remotely verified')
    parts.append('<dialog class="ra-dialog" aria-labelledby="ra-dialog-title"><header><div class="ra-dialog-heading"><small>THE RESEARCH ARCHIVE</small><h2 id="ra-dialog-title"></h2><p class="ra-dialog-context">Saved evidence · Exact identities · Original sources</p></div><button data-action="close" aria-label="Close Archive record">×</button></header><div class="ra-dialog-body"></div><footer class="ra-dialog-footer"><span>PAINTING RESTORATION EVIDENCE MUSEUM</span><span>Read the record. Keep its limits.</span></footer></dialog><span class="ra-sr" role="status" aria-live="polite"></span></main>')
    parts.append('<section class="ra-access" aria-label="Archive quick access">'+''.join(f'<button data-archive-action="{a}">{t}</button>' for a,t in [('search','Search archive'),('runs','Runs & lineage'),('reports','Reports'),('paintings','Painting provenance'),('limits','Limitations'),('publications','Publications'),('bundles','Bundle releases')])+'</section>')
    return ''.join(parts)


def nav_images(markup):
    def replace(match):
        svg=match.group(0)
        stroke='#a6232c' if '0 0 40 40' in svg else '#0085bd'
        svg=svg.replace('<svg ',f'<svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="{stroke}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" ',1)
        return '<img alt="" src="data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()+'">'
    return re.sub(r'<svg\b.*?</svg>',replace,markup,flags=re.DOTALL)


def render_research_archive(package,navigation):
    identity=str(st.query_params.get('ar_record','N33'))
    view=str(st.query_params.get('ar_view',''))
    try:
        data=payload(package,identity,view,st.query_params.get('ar_painting'))
        report_id=st.query_params.get('ar_report')
        artifact=st.query_params.get('ar_file')
        verify=st.query_params.get('ar_verify')
        if report_id or artifact or verify:
            st.markdown('<section style="max-width:1100px;margin:24px auto;color:#ead9b2"><h1>Research Archive · exact saved evidence</h1><a target="_self" href="'+html.escape(href(record=identity,view='record'),quote=True)+'">← Return to Research Archive</a></section>',unsafe_allow_html=True)
            if report_id:
                if report_id not in {r['report_id'] for r in data['reports']}: raise ValueError('Unknown report; nothing substituted')
                result=package.local_report_bytes(report_id)
                if result is None:
                    st.warning('The exact report is unavailable locally. Remote fallback is deferred; no report was substituted.')
                    return
                raw,name=result
                st.caption('Original saved report · SHA-256 verified against the N34 report index. Verification confirms byte identity, not scientific correctness.')
                st.download_button('Download original saved report',raw,file_name=name,mime='text/html')
                components.html(raw.decode('utf-8'),height=780,scrolling=True)
            elif verify:
                if verify!='manifest': raise ValueError('Unknown verification request')
                result=verify_manifest(package,identity)
                st.success('Selected run-manifest checksum matches the saved Archive index.')
                st.json(result)
            else:
                raw,item=selected_file(package,identity,artifact)
                st.caption(item['role'])
                st.code(item['path']+'\nSHA-256: '+item['sha256'])
                st.download_button('Download verified saved artifact',raw,file_name=item['path'].rsplit('/',1)[-1],mime=mimetypes.guess_type(item['path'])[0] or 'application/octet-stream')
                suffix=item['path'].rsplit('.',1)[-1]
                if suffix=='png': st.image(raw,width='stretch')
                elif suffix=='html': components.html(raw.decode('utf-8'),height=780,scrolling=True)
                elif len(raw)<1024*1024 and suffix in ('json','csv','md','yaml','txt'): st.code(raw.decode('utf-8-sig'),language='json' if suffix=='json' else None)
            return
        css=(ROOT/'streamlit_assets/research_archive.css').read_text(encoding='utf-8')
        portraits={name:image_uri(str(ROOT/'streamlit_assets/rooms/archive_portraits'/f'{name}.png')) for name in ('azhdaha','leto_ii','dragon')}
        revision=room_html('<style>'+css+'</style>'+room_markup(data,nav_images(navigation),image_uri(str(ROOT/'streamlit_assets/rooms/research_archive_shell.png')),image_uri(str(ROOT/'streamlit_assets/rooms/research_archive_lettering.png')),portraits))
        js=(ROOT/'streamlit_assets/research_archive_controller.js').read_text(encoding='utf-8')
        serialized=json.dumps(data,ensure_ascii=True,allow_nan=False).replace('</','<\\/')
        room_controller(js.replace('__ARCHIVE_PAYLOAD__',serialized),revision)
    except (ValueError,FileNotFoundError,KeyError,DashboardContractError) as exc:
        st.error('Research Archive could not display this exact record: '+str(exc))
        st.markdown('[Return to Research Archive](?room=research_archive)')
