"""Approved six-section D04 narrative. Only formatting of validated saved evidence."""
from __future__ import annotations

import base64
import hashlib
import html
import io
import json
from pathlib import Path

import pandas as pd
from PIL import Image

VERSION='1.0.0'


def e(value): return html.escape(str(value),quote=True)
def p(text): return '<p>'+text+'</p>'
def callout(text): return '<div class="finding">'+text+'</div>'


class Report:
    def __init__(self,ctx):
        self.ctx=ctx; self.assets=[];self.claims=[];self.trace=[]
        self.root=ctx['root'];self.out=ctx['canonical_output_root'];self.section=''

    def number(self,table,field=None,filters=None,operation='value',decimals=0,scale=1):
        frame=self.ctx['tables'][table]; selected=frame
        for k,v in (filters or {}).items(): selected=selected.loc[selected[k].eq(v)]
        if operation=='count': value=len(selected)
        elif operation=='nunique': value=selected[field].nunique()
        elif operation=='sum': value=pd.to_numeric(selected[field]).sum()
        else:
            if len(selected)!=1: raise ValueError(f'Ambiguous report value: {table}/{filters}/{field}')
            value=float(selected.iloc[0][field])
        value=float(value); key=f'claim_{len(self.claims)+1:04d}'
        display=f'{value*scale:,.{decimals}f}'
        self.claims.append(dict(claim_id=key,section=self.section,table=table,field=field or '',
            filters_json=json.dumps(filters or {},sort_keys=True),operation=operation,value=value,
            display_scale=scale,decimals=decimals,display_value=display,
            source_table_sha256=self.ctx['table_hashes'][table]))
        return f'<span data-claim="{key}">{display}</span>'

    def value(self,pid,model,field,decimals=3):
        return self.number('comparison',field,dict(pair_id=pid,model_id=model),decimals=decimals)

    def uncertainty(self,pid,metric,region,decimals=5):
        return self.number('uncertainty_summary','value',dict(painting_id=pid,metric_name=metric,region_id=region),decimals=decimals)

    def trace_role(self,key,role,sources,status='preserved'):
        resolved=[]
        for source in sources:
            candidate=self.out/source if source.split('/',1)[0] in {'data','metrics','work','figures','reports'} else self.root/source
            resolved.append(candidate.relative_to(self.root).as_posix())
        self.trace.append(dict(mock_element_id=key,mock_section=self.section,approved_role=role,
            final_section=self.section,canonical_evidence_source='; '.join(resolved),implementation_status=status,deviation_reason=''))

    def figure(self,key,relative,caption,tiles,sources,role=None):
        file=self.root/relative
        with Image.open(file) as im:
            im=im.convert('RGB');maximum=self.ctx['policy']['visuals']['embedded_max_width']
            if im.width>maximum: im.thumbnail((maximum,10000),Image.Resampling.LANCZOS)
            buf=io.BytesIO();im.save(buf,format='JPEG',quality=self.ctx['policy']['visuals']['embedded_jpeg_quality'],subsampling=0)
            width,height=im.size
        raw=buf.getvalue();digest=hashlib.sha256(raw).hexdigest()
        self.assets.append(dict(asset_id=key,section=self.section,source_path=relative,
            source_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),mime_type='image/jpeg',
            embedded_sha256=digest,embedded_size_bytes=len(raw),width=width,height=height,
            tile_count=tiles,source_dependencies_json=json.dumps(sorted(set(sources))),caption=caption))
        self.trace_role(key,role or caption,sources)
        return f'<figure id="{e(key)}"><button class="enlarge" type="button" aria-label="Enlarge {e(key)}"><img loading="lazy" width="{width}" height="{height}" data-asset="{e(key)}" src="data:image/jpeg;base64,{base64.b64encode(raw).decode()}" alt="{e(caption)}"></button><figcaption>{e(caption)}</figcaption></figure>'

    def owned_figure(self,key,caption):
        r=self.ctx['figures'].set_index('figure_id').loc[key]
        return self.figure(key,r.relative_path,caption,int(r.tile_count),json.loads(r.sources_json))

    def old_figure(self,key,rel,caption,tiles):
        file=self.out/rel
        return self.figure(key,file.relative_to(self.root).as_posix(),caption,tiles,[file.relative_to(self.root).as_posix()])

    def start(self,index):
        spec=self.ctx['policy']['sections'][index];self.section=spec['id']
        self.trace_role('section_'+str(index+1),spec['title'],['config/evaluation/real_damage_report.yaml'])
        alignment=['Approved physical-damage extension','RQ2 · descriptive extension','RQ1',
                   'RQ3','RQ1 and RQ2 · descriptive extension','RQ1–RQ3 · optional expert assessment'][index]
        return f'<section id="{e(self.section)}" data-report-section="{e(self.section)}"><h2>{index+1}. {e(spec["title"])}</h2><p class="question">{e(spec["question"])} <span>{e(alignment)}</span></p>'


def table(headers,rows,identifier):
    return '<div class="table-scroll"><table id="'+identifier+'"><thead><tr>'+''.join('<th>'+e(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def credits(ctx,pid,synthetic=False):
    if synthetic:
        pair=ctx['selection'].set_index('painting_id').loc[pid];row=ctx['synthetic_artworks'].set_index('painting_id').loc[pair.synthetic_painting_id]
    else: row=ctx['physical_artworks'].set_index('painting_id').loc[pid]
    row=row.fillna('')
    credit=str(row.get('source_credit',row.get('source','')))
    # Full author attribution supplements historical panel captions; source records are unchanged.
    if not synthetic and pid=='rd004': credit='Photograph by Tyler Bell. '+credit
    if not synthetic and pid=='rd005': credit='Photograph by BeakheadIntrados. '+credit
    return '<p class="credit">'+e(credit)+' · '+e(row.get('license',''))+' · <a href="'+e(row.get('source_url',''))+'">Source record</a>'+(' · <a href="'+e(row.get('license_url'))+'">Licence</a>' if row.get('license_url') else '')+'. Display adaptations: resizing, reviewed mask overlays, crops and digital reconstructions.</p>'


def render(ctx):
    r=Report(ctx);parts=[];obs=ctx['observations'];cmp=ctx['tables']['comparison'];u=ctx['tables']['uncertainty_summary']
    art=ctx['physical_artworks'].set_index('painting_id');panels=ctx['tables']['panel_manifest'].set_index('pair_id')
    parts.append(r.start(0))
    parts.append(p('The physical-damage pilot reveals substantial differences between visually integrating a repair, suppressing damage and reconstructing plausible content. Stable Diffusion produced convincing continuations in several irregular losses, particularly the garden fresco and torn landscape. Its advantage did not extend to every repair: Telea better suppressed the selected crack network in <em>Black Square</em>, while LaMa provided a more restrained continuation of the Roman wall panel.'))
    parts.append(callout('These results support examining restoration behaviour case by case. A visually complete output can contain unsupported new details, while a simple fill can be effective when the surrounding surface provides sufficient information.'))
    r.trace_role('opening_findings','Approved headline findings and conditional method conclusions',['data/case_observations.csv'])
    indicators=[('Physical paintings',r.number('candidates','painting_id',operation='nunique')),
        ('Primary restorations',r.number('candidates',filters={'candidate_role':'primary'},operation='count')),
        ('Physical candidates including repeats',r.number('candidates',operation='count')),
        ('Four-seed SD groups',r.number('candidates','uncertainty_group_id',{'model_id':'stable_diffusion_inpainting'},operation='nunique')),
        ('Saved synthetic restorations',r.number('comparison',operation='count')),
        ('Changed pixels outside masks',r.number('technical_checks','changed_outside_pixels',operation='sum'))]
    parts.append('<div class="kpis">'+''.join('<div><strong>'+v+'</strong><span>'+k+'</span></div>' for k,v in indicators)+'</div>')
    r.trace_role('coverage_indicators','Population and exact preservation indicators',['data/candidates.csv','metrics/technical_checks.csv','metrics/synthetic_comparison.csv'])
    parts.append(p('Outside-mask preservation is successful enforcement of the compositing rule, not evidence that reconstructed content is correct. All methods retain the same surrounding pixels, including unmasked deterioration. The selected masks are research repair targets rather than exhaustive or conservator-validated condition maps.'))
    parts.append(r.owned_figure('overview','The ten damaged inputs and selected repair targets. Cyan marks only the selected masks. The five operational categories each contain two paintings; they do not establish independent art-historical category effects.'))
    parts.append(p('Telea, LaMa, HINT and Stable Diffusion reuse the established restoration pipelines. Inputs are prepared on the unchanged 768-pixel canvas; SD uses 512-pixel inference followed by masked compositing. The primary SD seed is 2026. One targeted prompt per physical painting was frozen from its damaged input before inference and held fixed across seeds 2026–2029. The saved synthetic SD counterparts instead use the earlier generic prompt.'))
    parts.append(p('The observations below were made by the assistant through inspection of full images and detail crops and approved by the researcher. Model identities were visible. They are qualitative descriptions, not blinded expert ratings, numerical visual scores or a statistical model ranking. No clean reference exists for the physical targets.'))
    r.trace_role('scope_and_review','Prompt policies, selected masks and non-expert qualitative review',['data/prompt_policy.csv','data/case_observations.csv','data/synthetic_comparators.csv'])
    parts.append('</section>')

    parts.append(r.start(1))
    parts.append(p('The complete gallery retains every painting and every primary method. Compare the unobscured damaged input with the separate mask view before judging a repair. The second row enlarges the largest connected mask component with a fixed margin; the figure study also includes the approved arm-boundary crop. These display crops do not redefine metric regions. Click any image to enlarge it.'))
    rows=[]
    for pid,g in obs.groupby('painting_id',sort=True):
        rows.append([f'<a href="#case-{pid}">{pid}</a> — '+e(art.loc[pid,'title']),e(g.iloc[0].case_conclusion)])
    parts.append(table(['Painting','Comparative visual finding'],rows,'case-summary'))
    r.trace_role('all_case_summary','Ten-case comparative assessment table',['data/case_observations.csv'])
    extended={
        'rd004':'In the garden fresco, SD continues the blue sky and introduces foliage that fits the surrounding painted scene. Telea produces smooth patches, LaMa leaves conspicuous pale areas, and HINT introduces orange artifacts. SD therefore provides the most visually integrated primary reconstruction in this case. The conclusion concerns integration with the surviving painting; the missing leaves and branches cannot be verified.',
        'rd003':'The broad tear exposes a clear difference between filling an area and matching its visible surroundings. Telea creates a faceted strip, LaMa leaves a dark wedge and HINT produces an incompatible blue texture. The primary SD candidate restores more compatible sky tones. A dark tear-like trace remains, and the repeated-seed panels below show that its treatment changes between runs. Surrounding abrasion outside the selected target remains in all candidates.',
        'rd007':'A near-uniform dark surface gives local interpolation useful information. Telea suppresses the selected bright cracks more effectively than SD. LaMa and HINT also reduce the light network, although some dark pattern remains. SD leaves conspicuous bright lines across all four displayed seeds. This is a clear counterexample to automatically preferring generative detail. It concerns virtual filling of the approved mask, not a recommendation to remove physical craquelure.',
        'rd006':'The target is a selected neutral infill/lacuna in an already conserved wall painting, not untreated fresh damage. LaMa gives a quiet textured continuation. SD inserts a red motif, and changing only its seed produces different designs. Those alternatives can look compatible with painted decoration, but the surviving input does not establish which, if any, belongs there. Added visual content is therefore not sufficient evidence of a better reconstruction.'}
    for pid,g in obs.groupby('painting_id',sort=True):
        parts.append(f'<article id="case-{pid}"><h3>{pid} · {e(art.loc[pid,"title"])}</h3>')
        coverage=r.value(pid,'opencv_telea','physical_damage_fraction',4)
        parts.append(p(e(g.iloc[0].inspected_region)+' Selected content fraction: '+coverage+'.'))
        parts.append(r.owned_figure('case_'+pid,'Damaged input, separate mask overlay and four primary outputs, followed by display-only repair details. SD uses seed 2026. Surviving deterioration outside the mask is intentionally unchanged.'))
        notes=g.set_index('model_id')
        parts.append(table(['Method','Visible behaviour'],[[e(comparison_label(m)),e(notes.loc[m,'observation'])] for m in ctx['model_order']],'observations-'+pid))
        parts.append(callout(e(g.iloc[0].case_conclusion)))
        r.trace_role('case_findings_'+pid,'All four method observations and case conclusion',['data/case_observations.csv',ctx['policy']['observations']])
        if pid in extended:
            parts.append(p(extended[pid]));r.trace_role('extended_'+pid,'Approved extended discussion of success, failure or unsupported content',['data/case_observations.csv'])
        parts.append(credits(ctx,pid));parts.append('</article>')
    parts.append('</section>')

    parts.append(r.start(2))
    parts.append(p('The saved checks record '+r.number('technical_checks',operation='count')+' physical candidates with '+r.number('technical_checks','changed_outside_pixels',operation='sum')+' changed pixels outside their masks and '+r.number('technical_checks','changed_padding_pixels',operation='sum')+' changed padding pixels. This confirms that the delivered images honour the preservation rule. It does not rank the quality of the repaired interiors.'))
    parts.append(r.old_figure('boundary_plot','work/diagnostics/primary_boundary_descriptors.png','Raw inner/outer three-pixel band contrast for the primary candidates. Crosses show the damaged input. Natural contours affect these descriptors; a smaller value alone does not establish better restoration.',2))
    rows=[]
    for pid in ['rd004','rd007']:
        rows.append([e(art.loc[pid,'title']),r.value(pid,'opencv_telea','physical_restored_boundary_delta_e_gap'),r.value(pid,'stable_diffusion_inpainting','physical_restored_boundary_delta_e_gap')])
    parts.append(table(['Physical case','Telea: boundary colour gap','SD: boundary colour gap'],rows,'boundary-examples'))
    r.trace_role('boundary_examples','Two numerical examples interpreted alongside visible repairs',['metrics/real_damage_diagnostics.csv','metrics/synthetic_comparison.csv'])
    parts.append(p('These values are CIEDE2000 differences between the mean colours of the inner and outer bands. They are not reference-based seam errors or averages of corresponding-pixel colour errors. In the garden fresco, Telea has a smaller gap despite visibly patchier reconstruction. Its smooth fill can bring average colours closer without recovering plausible foliage. In <em>Black Square</em>, SD’s larger gap accompanies the conspicuous bright network.'))
    parts.append(callout('Boundary evidence identifies one aspect of a transition. Its interpretation becomes stronger when the location and corresponding reconstruction are visible. The fresco demonstrates disagreement with perceived integration; Black Square demonstrates agreement.'))
    parts.append(p('Inside-mask edit magnitude describes how much the delivered candidate differs from the damaged input. A large change may remove conspicuous damage or introduce an unsuitable replacement. A small change may preserve useful context or leave damage unresolved. We therefore retain edit descriptors for inspection without treating the damaged photograph as a clean reference or assigning a universal direction of improvement.'))
    r.trace_role('diagnostic_interpretation','Preservation, edit magnitude and raw boundary limits plus practical assertions',['metrics/technical_checks.csv','metrics/real_damage_diagnostics.csv'])
    parts.append('</section>')

    parts.append(r.start(3))
    parts.append(p('Four seeds are retained for each painting with the same case, targeted prompt and generation settings. The primary output remains seed 2026; no favourable alternative replaces it in the four-method comparison. Variation is empirical disagreement between generated candidates, not calibrated confidence or a probability that the reconstruction is correct.'))
    specs=[('pixel_rgb_std_mean','masked_region'),('pairwise_lpips_distance','mask_bbox_crop')]
    pixel=u.loc[u.metric_name.eq(specs[0][0])&u.region_id.eq(specs[0][1])].set_index('painting_id').value.astype(float)
    percept=u.loc[u.metric_name.eq(specs[1][0])&u.region_id.eq(specs[1][1])].set_index('painting_id').value.astype(float)
    if not (pixel.idxmin()=='rd006' and pixel.idxmax()=='rd003' and percept.idxmax()=='rd006'):
        raise ValueError('Saved evidence no longer supports the approved variability assertions')
    parts.append(r.owned_figure('variability_measures','Two separate saved variability summaries for all ten groups. The left uses masked RGB values scaled to 0–1; the right uses learned perceptual distance over the mask bounding-box crop. Their scales, representations and spatial supports differ.'))
    rows=[]
    for pid in ['rd006','rd003']:
        rows.append([e(art.loc[pid,'title']),r.uncertainty(pid,*specs[0]),r.uncertainty(pid,*specs[1])])
    parts.append(table(['Case','Mean masked RGB standard deviation','Mean pairwise crop LPIPS'],rows,'variability-examples'))
    r.trace_role('variability_examples','Lowest pixel variation versus highest perceptual disagreement; largest pixel variation',['metrics/uncertainty_summary.csv'])
    parts.append(p('The Roman wall has the lowest mean masked pixel variation among these ten groups but the highest crop LPIPS disagreement. Its alternatives differ visibly in depicted form: the fixed prompt produces a red motif, a different collection of coloured shapes, an angular design and a circular ornament. Comparatively small average pixel variation therefore does not establish stable depicted content. The torn landscape has the largest masked pixel variation, consistent with its changing tear repair. These observations concern different measurement definitions, not interchangeable stability scores.'))
    parts.append(callout('Repeated candidates reveal alternatives hidden by a single convincing output. The wall panel and landscape show why both the measurement and its region must remain explicit.'))
    for pid in sorted(art.index):
        opened=' open' if pid in ctx['policy']['visuals']['enlarged_seed_discussions'] else ''
        parts.append(f'<details{opened}><summary>{pid} · {e(art.loc[pid,"title"])} — all four seeds</summary>')
        parts.append(r.owned_figure('seed_'+pid,'Damaged input and all four SD seeds, with the same input-defined detail crop below. The prompt is fixed within this painting. Candidate agreement does not establish historical correctness.'))
        parts.append(credits(ctx,pid));parts.append('</details>')
    for n in (1,2):
        parts.append('<details><summary>Spatial variability maps — set '+str(n)+'</summary>')
        parts.append(r.old_figure('uncertainty_maps_'+str(n),f'work/diagnostics/uncertainty_maps_0{n}.png',
            'Saved RGB standard-deviation maps use one shared display scale. Cyan outlines the selected repair region. The display ceiling is the pooled masked 99th percentile; raw arrays remain unclipped. Preserved outside-mask pixels have zero variation.',15))
        parts.append('</details>')
    r.trace_role('stability_scope','Fixed prompts, fixed primary seed, different measures and no calibrated-confidence interpretation',['data/prompt_policy.csv','metrics/seed_pairwise.csv','metrics/uncertainty_summary.csv'])
    parts.append('</section>')

    parts.append(r.start(4))
    parts.append(p('The ten synthetic counterparts were selected from saved Controlled-300 inputs before inspecting D04 restoration outcomes. They provide contextual comparisons, with reference fidelity available only on the synthetic side. The physical paintings, depicted subjects, mask geometry and surviving surfaces differ. Physical SD uses targeted prompts; synthetic SD uses the generic prompt. This comparison cannot isolate a causal effect of physical versus synthetic damage.'))
    parts.append(r.old_figure('input_matching','work/comparison/input_matching.png','Preselected input matches retain substantial differences in mask fragmentation despite approximately similar coverage. Component count uses the existing connectivity definition; it is not a count of independent damage events.',2))
    row=cmp.loc[cmp.pair_id.eq('rd009')&cmp.model_id.eq('opencv_telea')].iloc[0]
    parts.append(p('For rd009 and its comparator, selected mask coverage is '+r.number('comparison','physical_damage_fraction',dict(pair_id='rd009',model_id='opencv_telea'),decimals=2,scale=100)+'% and '+r.number('comparison','synthetic_damage_fraction',dict(pair_id='rd009',model_id='opencv_telea'),decimals=2,scale=100)+'%, but the masks contain '+r.value('rd009','opencv_telea','physical_component_count',0)+' and '+r.value('rd009','opencv_telea','synthetic_component_count',0)+' connected components. Similar area therefore does not mean equivalent damage geometry.'))
    r.trace_role('matching_interpretation','Coverage and fragmentation contrast, with prompt-policy disclosure',['data/synthetic_comparators.csv','metrics/synthetic_comparison.csv'])
    for pid in sorted(art.index):
        panel=panels.loc[pid];prominent=pid in ctx['policy']['visuals']['prominent_synthetic_pairs']
        parts.append('<details'+(' open' if prominent else '')+'><summary>'+pid+' · '+e(panel.physical_title)+' ↔ '+e(panel.synthetic_title)+'</summary>')
        for kind in ('full','detail'):
            parts.append(r.figure('comparison_'+kind+'_'+pid,panel[kind+'_panel_path'],
                ('Full painting context. ' if kind=='full' else 'Independently selected largest-component detail crops; these are not corresponding subjects or new metric regions. ')+
                'Physical restorations above; saved synthetic restorations and known reference below. Numerical fidelity values apply only to the original synthetic evaluation regions. Physical targeted SD prompt; synthetic generic SD prompt.',11,
                [panel[kind+'_panel_path'], 'outputs/d04_real_damage_restoration_and_evaluation/metrics/synthetic_comparison.csv']))
        metric_rows=[[e(comparison_label(model)),r.value(pid,model,'synthetic_masked_mae'),
                      r.value(pid,model,'synthetic_crop_ssim',4),r.value(pid,model,'synthetic_crop_lpips',4)]
                     for model in ctx['model_order']]
        parts.append(table(['Saved synthetic candidate','Masked MAE ↓','Crop SSIM ↑','Crop LPIPS ↓'],metric_rows,'synthetic-metrics-'+pid))
        parts.append(p('Reference measurements above apply only to the synthetic case. No corresponding physical fidelity scores are available.'))
        if prominent:
            if pid=='rd004':
                parts.append(p('SD’s physical garden fresco is well integrated. In the separate synthetic <em>Landscape on a River</em>, SD introduces a pale building absent from the known reference. LaMa’s masked MAE is '+r.value(pid,'lama','synthetic_masked_mae')+' versus SD’s '+r.value(pid,'stable_diffusion_inpainting','synthetic_masked_mae')+', and crop LPIPS is '+r.value(pid,'lama','synthetic_crop_lpips',4)+' versus '+r.value(pid,'stable_diffusion_inpainting','synthetic_crop_lpips',4)+'.'))
                parts.append(callout('The synthetic reference exposes a specific content error that visual plausibility alone cannot resolve. A persuasive physical reconstruction can likewise contain unverifiable new content.'))
            elif pid=='rd007':
                parts.append(p('Telea works well on the physical painting’s near-uniform dark field. In <em>Several Circles</em>, the larger missing forms cause Telea to stretch neighbouring colours into wedges, while LaMa reconstructs more convincing rounded shapes. LaMa’s saved masked MAE is '+r.value(pid,'lama','synthetic_masked_mae')+' compared with Telea’s '+r.value(pid,'opencv_telea','synthetic_masked_mae')+'. SD adds rounded features too, but their number and placement differ from the reference.'))
                parts.append(callout('Continuing a nearly uniform surface and recovering missing geometric forms place different demands on the models. Broad category membership alone does not determine the preferable method.'))
            else:
                parts.append(p('SD leaves conspicuous line-like disruption in both inspected examples. In the synthetic <em>The Toilet of Bathsheba</em>, its masked MAE is '+r.value(pid,'stable_diffusion_inpainting','synthetic_masked_mae')+' compared with Telea’s '+r.value(pid,'opencv_telea','synthetic_masked_mae')+'; crop LPIPS is '+r.value(pid,'stable_diffusion_inpainting','synthetic_crop_lpips',4)+' versus '+r.value(pid,'opencv_telea','synthetic_crop_lpips',4)+'.'))
                parts.append(callout('Under the evaluated configurations, generating richer content did not translate into effective suppression of these narrow damaged regions. This is a concrete counterweight to SD’s successful broader-loss reconstructions.'))
            r.trace_role('synthetic_story_'+pid,'Approved physical/core comparison with visual and metric interpretation',['metrics/synthetic_comparison.csv','work/comparison/synthetic_reference_metrics.csv'])
        parts.append(credits(ctx,pid)+credits(ctx,pid,synthetic=True));parts.append('</details>')
    r.trace_role('synthetic_scope','All ten frozen comparisons; saved MAE/SSIM/LPIPS restricted to synthetic cases',['work/comparison/synthetic_reference_metrics.csv','data/synthetic_comparators.csv'])
    parts.append('</section>')

    parts.append(r.start(5))
    parts.append(callout('The pilot demonstrates that the framework supports meaningful inspection when clean references are unavailable. SD provides some of the most convincing continuations of larger, irregular losses; simpler methods are more effective for particular crack repairs; and generative completions sometimes introduce unsupported motifs. Preservation checks, boundary descriptors, visual inspection and repeated-seed evidence expose different aspects of these outcomes.'))
    parts.append(p('These physical cases extend the controlled study by showing what remains assessable without ground truth and which conclusions become unavailable. They support conditional comparisons between the evaluated pipelines, rather than a universal recommendation of one model. HINT’s conspicuous colour artifacts in several larger repairs also show why an available learned method must be inspected under the actual checkpoint and input conditions used here. The ten selected paintings do not establish general method or category effects.'))
    rows=[['RQ1','Boundary and variability examples demonstrate why complementary measurements and their spatial regions must remain visible. A favourable scalar alone can conceal an unconvincing repair.'],
          ['RQ2','The physical cases extend the method comparison descriptively. SD’s strong examples coexist with Telea’s effective crack suppression and LaMa’s restrained fill. This pilot does not replace the matched Controlled-300 benchmark.'],
          ['RQ3','The fixed-prompt four-seed groups reveal alternative completions and different kinds of disagreement. They provide stability evidence without establishing a correct completion or calibrated confidence.']]
    parts.append(table(['Thesis question','Contribution from this pilot'],[[e(x),e(y)] for x,y in rows],'thesis-alignment'))
    r.trace_role('thesis_synthesis','Explicit RQ1–RQ3 contribution and conditional method conclusions',['data/case_observations.csv','metrics/real_damage_diagnostics.csv','metrics/uncertainty_summary.csv'])
    parts.append('<h3>Limitations that affect interpretation</h3>')
    parts.append(p('The pilot has no clean physical references, no blinded expert ratings and only two examples per operational category. Source photographs differ in age, resolution, lighting and prior conservation. Some targets are neutral fills in conserved wall paintings. Masks are non-exhaustive and researcher-approved rather than conservator-validated; remaining unmasked damage must be distinguished from an unsuccessful selected repair. Primary model identities were visible during qualitative review.'))
    parts.append(p('Physical and synthetic examples use different paintings, mask fragmentation and SD prompt policies. No physical fidelity score, pooled cross-domain ranking, causal domain effect, calibrated uncertainty or physical conservation approval is inferred. The documented SD resolution and compositing policy belong to the evaluated pipeline; these results do not isolate the effects of resolution, prompts or architecture separately.'))
    r.trace_role('limitations','Consolidated limitations near final conclusions',['data/prompt_policy.csv','data/case_observations.csv','data/synthetic_comparators.csv'])
    parts.append('<h3>Optional expert-study handoff</h3>')
    parts.append(p('The retained cases support concrete questions for a future art or conservation assessment: Do specialists prefer SD’s additional foliage and scene detail? Do they favour LaMa’s restrained wall fill over generated motifs? Do they agree that Telea better fulfils the selected crack-filling objective? How do preferences change when the clean synthetic reference reveals invented content?'))
    parts.append(p('The proposed assessment would first show damaged inputs and anonymised restorations with model identities and metric values withheld and presentation order varied. It would ask about visual coherence, boundary integration, plausible forms and unresolved defects. Synthetic references would then be revealed to examine fidelity and changes in preference. Expertise, consent and repeated ratings would be handled explicitly. This is a handoff for a future optional assessment, not a claim that it has been conducted.'))
    r.trace_role('expert_handoff','Specific future questions and staged reference-reveal assessment',[ctx['policy']['proposal'],'data/case_observations.csv'])
    parts.append('<details><summary>Technical provenance, prompts and runtime scope</summary>')
    parts.append(p('D03 source preparation and reviewed masks remain unchanged. All scientific measurements are read from saved Batch 8–9 evidence. Numerical values in this report are recorded with table filters in the claim catalogue; image sources, hashes, tile counts and approved mock elements are recorded separately. The report is self-contained and requires no network access for its narrative images.'))
    parts.append('<dl><dt>Batch 9 execution fingerprint</dt><dd><code>'+e(ctx['upstream_summary']['execution_fingerprint'])+'</code></dd><dt>Report evidence fingerprint</dt><dd><code>'+e(ctx['execution_fingerprint'])+'</code></dd></dl>')
    prompts=ctx['tables']['candidates'].query("model_id == 'stable_diffusion_inpainting' and candidate_role == 'primary'")
    parts.append(table(['Painting','Fixed targeted prompt'],[[e(x.painting_id),e(x.prompt)] for x in prompts.itertuples()],'targeted-prompts'))
    runtime=ctx['tables']['runtime_summary']
    columns=[c for c in ['model_id','stage','completed_candidates','recorded_case_runtime_seconds','recorded_command_runtime_seconds','runtime_scope'] if c in runtime]
    parts.append(p('The following original runtime records have different measurement scopes. Case-call and whole-command durations are not directly comparable, and historical stage completion flags are not the final notebook completion gate.'))
    parts.append(table(columns,[[e(v) for v in row] for row in runtime[columns].itertuples(index=False,name=None)],'runtime-scope'))
    parts.append('</details>')
    r.trace_role('provenance','Unicode credits, exact prompts, fingerprints and separate runtime scopes',['data/model_provenance.csv','data/prompt_policy.csv','metrics/runtime_summary.csv'],status='upgraded_additively')
    parts.append('</section>')
    body='\n'.join(parts)
    nav=''.join('<a href="#'+e(s['id'])+'">'+str(i+1)+'. '+e(s['title'])+'</a>' for i,s in enumerate(ctx['policy']['sections']))
    page='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(ctx['policy']['title'])+'</title><style>'+CSS+'</style></head><body><header><p class="eyebrow">D04 · supplementary physical-damage study</p><h1>'+e(ctx['policy']['title'])+'</h1><p>'+e(ctx['policy']['subtitle'])+'</p></header><nav>'+nav+'</nav><main>'+body+'</main><dialog id="image-view"><button id="close-image" aria-label="Close enlarged image">Close ×</button><img alt="Enlarged evidence panel"></dialog><script>'+JS+'</script></body></html>'
    return page,pd.DataFrame(r.assets),pd.DataFrame(r.claims),pd.DataFrame(r.trace)


def comparison_label(model):
    return {'opencv_telea':'Telea','lama':'LaMa','hint_places2':'HINT','stable_diffusion_inpainting':'Stable Diffusion'}[model]


CSS='''
:root{color-scheme:light;--ink:#203c37;--green:#173e36;--paper:#faf7ee;--line:#d6cbb2}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:#252b28;font:17px/1.65 Georgia,'Times New Roman',serif}
header{background:var(--green);color:#fff5dd;padding:48px max(5vw,24px)}h1{max-width:1100px;font-size:clamp(28px,3.2vw,46px);line-height:1.17;margin:12px 0}header p{max-width:1000px}
.eyebrow{font:13px Arial,sans-serif;text-transform:uppercase;letter-spacing:2px}nav{display:flex;flex-wrap:wrap;gap:10px 24px;padding:20px 5vw;border-bottom:1px solid var(--line);font:14px Arial,sans-serif}
a{color:#1e6256}nav a{max-width:340px}main{max-width:1280px;margin:auto;padding:20px 32px 70px}section{padding-top:28px;border-bottom:1px solid var(--line);padding-bottom:36px}h2{font-size:30px;line-height:1.25;color:var(--ink)}h3{font-size:23px;color:var(--ink)}p{max-width:1080px}.question{font-style:italic}.question span{display:block;font:12px/1.5 Arial,sans-serif;color:#68665c;margin-top:7px}
.finding{border-left:5px solid #9d6e37;background:#eee6d3;padding:17px 22px;margin:22px 0;max-width:1120px}.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:28px 0}.kpis div{background:#e8eee5;padding:18px;border:1px solid #c4d0c2}.kpis strong{display:block;font-size:36px;color:var(--green)}.kpis>div>span{font:14px/1.5 Arial,sans-serif}
figure{margin:24px 0;background:white;border:1px solid var(--line);padding:12px}.enlarge{display:block;border:0;padding:0;width:100%;background:transparent;cursor:zoom-in}.enlarge img{display:block;width:100%;height:auto}figcaption,.credit{font:13px/1.55 Arial,sans-serif;color:#575a52;padding:10px 2px}.credit{overflow-wrap:anywhere}article{margin:30px 0;padding-bottom:22px;border-bottom:1px dotted #a99c7c}
.table-scroll{overflow-x:auto;margin:22px 0}table{width:100%;border-collapse:collapse;font:14px/1.55 Arial,sans-serif}th{text-align:left;background:#e3e9df;color:var(--green)}th,td{padding:11px;border:1px solid #cec9ba;vertical-align:top}td{min-width:130px}details{margin:18px 0;border:1px solid var(--line);padding:14px;background:#fffdf6}summary{cursor:pointer;font-weight:bold;color:var(--green)}code{font:12px monospace;overflow-wrap:anywhere}dd{margin-left:0}dialog{max-width:98vw;max-height:96vh;padding:12px;border:1px solid #777;overflow:auto}dialog::backdrop{background:#000b}dialog img{display:block;max-width:none;width:auto;max-height:none}#close-image{position:sticky;top:0;left:0;padding:12px;z-index:2;background:#183e36;color:white;border:0;cursor:pointer}
@media(max-width:650px){main{padding:12px}.kpis{grid-template-columns:repeat(2,1fr)}h2{font-size:25px}body{font-size:16px}figure{padding:5px}dialog img{width:2000px}}
@media print{nav,button#close-image{display:none}header{background:white;color:#183e36}details{display:block}section,article{break-inside:auto}figure{break-inside:avoid}}
'''
JS='''const dlg=document.getElementById('image-view');document.querySelectorAll('.enlarge').forEach(b=>b.addEventListener('click',()=>{const i=b.querySelector('img');dlg.querySelector('img').src=i.src;dlg.querySelector('img').alt=i.alt;dlg.showModal();}));document.getElementById('close-image').onclick=()=>dlg.close();'''
