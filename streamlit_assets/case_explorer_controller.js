/* Read-only presentation of registered candidate evidence. No scientific compute. */
function ceFilter(rows, filters) {
  return rows.filter(row => Object.entries(filters).every(([key, value]) =>
    !value || String(row[key] ?? "") === String(value)));
}
function ceUrl(state, updates = {}) {
  const params = new URLSearchParams({room:"case_explorer", ce_painting:state.painting.painting_id,
    ce_candidate:state.candidate.candidate_id, ce_layer:state.layer, ...updates});
  for (const [key, value] of [...params]) if (value === "" || value === "null") params.delete(key);
  return "?" + params.toString();
}
function ceScope(rows, current, field) {
  const keys={experiment:[],damage:['experiment_id'],model:['case_id'],candidate:['case_id','model_id']}[field];
  if(!keys) return [];
  return ceFilter(rows,Object.fromEntries(keys.map(key=>[key,current[key]])));
}
function ceRandom(rows, random=Math.random) {
  if(!rows.length) return null;
  return rows[Math.min(rows.length-1,Math.floor(random()*rows.length))];
}
if (typeof module !== "undefined" && module.exports) module.exports = {ceFilter, ceUrl, ceScope, ceRandom};
if (typeof window !== "undefined") (() => {
  const data = __CASE_EXPLORER_PAYLOAD__;
  const doc = window.parent.document;
  const stage = doc.querySelector(".ce-stage"), dialog = doc.querySelector(".ce-dialog");
  if (!stage || !dialog) return;
  // Streamlit sanitizes URL-valued inline custom properties. Reuse the single
  // verified source image for all ten CSS windows after HTML sanitization.
  const sheet=stage.querySelector('.ce-sheet-source');
  if(sheet)stage.querySelectorAll('.ce-neighbour-mini').forEach(el=>el.style.setProperty('background-image',`url("${sheet.src}")`,'important'));
  // Static labels only: original reference lettering, never scientific imagery.
  const lettering=stage.querySelector('.ce-lettering-source');
  if(lettering)stage.querySelectorAll('.ce-reference-window').forEach(el=>{
    el.style.setProperty('background-image',`url("${lettering.src}")`,'important');
    el.classList.add('has-reference');
  });
  const titleArtwork=stage.querySelector('.ce-title-source');
  if(titleArtwork)stage.querySelector('.ce-title').style.setProperty('background-image',`url("${titleArtwork.src}")`,'important');
  const fitIdentity=()=>{const el=stage.querySelector('.ce-record-plaque');el.style.fontSize='1.15cqw';const ratio=(el.clientWidth-4)/el.scrollWidth;if(ratio<1)el.style.fontSize=(1.15*ratio)+'cqw';};
  const roomResize=new ResizeObserver(fitIdentity);roomResize.observe(stage);fitIdentity();
  window.addEventListener('unload',()=>roomResize.disconnect(),{once:true});
  const body = dialog.querySelector(".ce-dialog-body"), heading = dialog.querySelector("h2");
  const c = data.candidate, p = data.painting;
  const esc = value => String(value ?? "Not recorded").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
  const pretty = value => String(value ?? "Not applicable").replaceAll("_", " ");
  const code = value => `<code>${esc(value)}</code>`;
  const note = text => `<div class="ce-note">${text}</div>`;
  const option = (value,label,selected=false) => `<option value="${esc(value)}" ${selected?"selected":""}>${esc(label)}</option>`;
  const navigate = url => { const a=doc.createElement("a"); a.href=url; a.target="_self"; doc.body.append(a); a.click(); a.remove(); };
  const go = updates => navigate(ceUrl(data,updates));
  const button = (action,label) => `<button type="button" data-action="${esc(action)}">${esc(label)}</button>`;
  let previousFocus;
  function open(title, html) {
    if (!dialog.open) previousFocus=doc.activeElement;
    heading.textContent=title; body.innerHTML=html;
    dialog.querySelector('.ce-dialog-context').textContent=[p.painting_id,pretty(data.case.case_id.split(p.painting_id+'__').pop()),data.labels[c.model_id]||c.model_id].join(' · ');
    dialog.classList.toggle('ce-dialog-wide',html.includes('ce-compare'));
    if (!dialog.open) dialog.showModal();
    dialog.scrollTop=0;
  }
  dialog.querySelector("[data-close]").addEventListener("click",event=>{event.preventDefault();event.stopPropagation();dialog.close();});
  dialog.addEventListener("close",()=>previousFocus?.focus());
  dialog.addEventListener("click",event=>{if(event.target===dialog)dialog.close();});

  function record() {
    const fields = {...data.case,...c};
    const keys=["candidate_id","case_id","model_id","experiment_id","population_role","seed","prompt_variant_id","candidate_record_id","restored_sha256","uncertainty_group_id"];
    open("The selected record",`<p class="ce-intro">${esc(p.title)} · ${esc(p.artist)}. Every view and saved measurement in this room is bound to this one candidate.</p>
      <div class="ce-grid"><section class="ce-card"><h3>Identity</h3><dl>${keys.map(k=>`<dt>${esc(pretty(k))}</dt><dd>${code(fields[k])}</dd>`).join("")}</dl></section>
      <section class="ce-card"><h3>Recorded review trace</h3><dl><dt>Recommendation</dt><dd>${esc(pretty(c.recommendation_category))}</dd><dt>Missing required indicators</dt><dd>${esc(c.insufficient_flag_ids.length?c.insufficient_flag_ids.map(pretty).join(", "):"None recorded")}</dd><dt>Triggered flags</dt><dd>${esc(c.triggered_flag_ids.map(pretty).join(", ")||"None recorded")}</dd><dt>Evidence identifiers</dt><dd>${c.triggering_evidence_ids.map(code).join("<br>")||"None recorded"}</dd><dt>Source notebooks</dt><dd>${c.source_notebook_ids.map(id=>button("notebook:"+id,"N"+id)).join(" ")}</dd></dl>${button("trust","Trace exact Trustworthiness decision")}${note("A missing indicator is not a pass. A review status does not mean the displayed image metrics worsened.")}</section></div>
      <section class="ce-card" style="margin-top:18px"><h3>Reports for this record</h3><div class="ce-toolbar">${button('report:painting','Original painting report')}${data.reports.case?button('report:case','Original detailed case report'):'<span class="ce-badge">Not selected for a detailed case report</span>'}${data.review_code?button('portrait','D02 · exact reviewed candidate'):'<span class="ce-badge">D02 · no completed review for this candidate</span>'}</div><details><summary>Displayed asset paths & verification</summary><dl>${Object.entries(data.images).map(([k,v])=>`<dt>${esc(k)}</dt><dd>${code(v.path)}${v.reason?`<p class="ce-danger">${esc(v.reason)}</p>`:""}</dd>`).join("")}</dl><p>Each displayed source is checked against its N34 or registered producer checksum. Missing local evidence is not substituted.</p></details></section>`);
  }
  function availability(uncertaintyOnly=false){
    const layers=uncertaintyOnly?data.layers.filter(x=>x.key==='uncertainty'):data.layers;
    open(uncertaintyOnly?'Uncertainty for this candidate':'Available evidence',`<p class="ce-intro">Availability belongs to this exact saved output. A missing view is never replaced by another candidate’s map.</p><div class="ce-grid">${layers.map(item=>`<section class="ce-card"><h3>${esc(item.label)}</h3><span class="ce-badge ${item.available?'':'ce-badge-muted'}">${item.available?'Saved image available':'Not available'}</span><p>${esc(item.reason)}</p>${item.available?button('layer:'+item.key,'View '+item.label.toLowerCase()):''}</section>`).join('')}</div>${note('For deterministic methods, generative uncertainty is not applicable. For diffusion, uncertainty is empirical variation within a saved group—not calibrated confidence or correctness. No group is calculated in this room.')}`);
  }
  function sources(){
    open('Source notebooks',`<p class="ce-intro">The recorded producers behind this candidate’s evidence. Open a source to download its original notebook; no code is run here.</p><div class="ce-grid">${data.source_notebooks.map(source=>`<section class="ce-card"><span class="ce-badge">N${esc(source.id)}</span><h3>${esc(source.title)}</h3>${source.available?button('notebook:'+source.id,'Inspect source notebook →'):note('The recorded notebook is not available locally.')}</section>`).join('')}</div><div class="ce-toolbar">${button('record','Inspect the complete candidate record')}</div>`);
  }
  function metrics() {
    open("Saved measurements, exact scope",`<p class="ce-intro">Agreement with the controlled pre-damage digital reference—not historical authenticity. No combined score is calculated.</p>
      <div class="ce-grid ce-metric-cards">${data.metrics.map(item=>{const r=item.record,valid=r?.status==='ok';return `<section class="ce-card"><h3>${esc(item.label)}</h3><span class="ce-badge">${esc(item.region)}</span><span class="ce-badge">${esc(item.direction)}</span>${valid?`<div class="ce-metric-values"><div><small>Damaged</small><strong>${Number(r.damaged_value).toFixed(3)}</strong></div><span>→</span><div><small>Restored</small><strong>${Number(r.restored_value).toFixed(3)}</strong></div></div><p class="ce-metric-change">${Number(r.improvement_value).toFixed(3)} saved ${r.improvement_direction==='restored_minus_damaged'?'increase':'reduction'}</p><details><summary>Exact values & source record</summary><dl><dt>Damaged → restored</dt><dd>${code(r.damaged_value)} → ${code(r.restored_value)}</dd><dt>Saved improvement</dt><dd>${code(r.improvement_value)} · ${esc(pretty(r.improvement_direction))}</dd><dt>Region / status</dt><dd>${code(r.region_id)} · ${esc(r.status)}</dd><dt>Source row</dt><dd>${code(r.metric_row_id||r.local_consistency_id)}</dd><dt>Source</dt><dd>${code(r.source_path)}</dd><dt>Source SHA-256</dt><dd>${code(r.source_sha256)}</dd></dl></details>`:note(`No usable saved value${r?' · '+esc(r.status):''}. Unavailable is not zero.`)}</section>`}).join("")}</div>
      ${note("LPIPS (AlexNet) and SSIM use the mask bounding-box crop, including its surrounding context. ΔE 2000 uses the irregular damaged area. Values are copied from saved producer rows; the browser performs no metric recomputation.")}
      <div class="ce-toolbar">${button('export:metrics','Download these exact rows · JSON')}${button("trust","Open operational review trace")}</div>`);
  }
  function catalogue(focus='candidate') {
    focusedPicker(focus);
    return;
  }
  function focusedPicker(focus){
    const titles={category:'Category',painting:'Painting',experiment:'Experiment',damage:'Damage',model:'Model',candidate:'Candidate'};
    if(!titles[focus])focus='painting';
    const title=titles[focus],key={experiment:'experiment_id',damage:'case_id',model:'model_id',candidate:'candidate_id'}[focus];
    const scoped=ceScope(data.selector_rows,c,focus);
    let choices=[];
    if(focus==='category')choices=[...new Set(data.paintings.map(x=>x.category))].sort().map(value=>({value,label:pretty(value)}));
    else if(focus==='painting')choices=data.paintings.map(x=>({value:x.painting_id,label:`${x.painting_id} · ${x.title}`}));
    else choices=[...new Set(scoped.map(x=>String(x[key])))].sort().map(value=>({value,label:focus==='model'?(data.labels[value]||value):focus==='damage'?pretty(value.split(p.painting_id+'__').pop()):focus==='candidate'?(()=>{const r=scoped.find(x=>x.candidate_id===value);return `${r.seed===null?'Deterministic output':'Seed '+r.seed}${r.prompt_variant_id?' · '+pretty(r.prompt_variant_id):''} · ${value}`})():pretty(value)}));
    const contexts={category:'Choose a category. A painting and a compatible saved restoration will be picked at random.',painting:'All paintings are listed. A compatible experiment, damage, method and output will be picked at random for the painting you choose.',experiment:`Keep ${p.painting_id}. Choose one of its experiments; damage, method and output are filled at random.`,damage:`Keep ${p.painting_id} and ${pretty(c.experiment_id)}. Choose damage; a compatible method and output are filled at random.`,model:'Keep the current painting, experiment and damage. Choose a method; a compatible saved output is filled at random.',candidate:'Keep the current painting, experiment, damage and method. Choose the exact saved output.'};
    const current=focus==='category'?p.category:focus==='painting'?p.painting_id:c[key];
    open('Choose '+title.toLowerCase(),`<section class="ce-single-picker"><p class="ce-intro">${esc(contexts[focus])}</p><label>${title}<select data-single-choice aria-label="${title}">${choices.map(x=>option(x.value,x.label,x.value===String(current))).join('')}</select></label><p data-choice-count role="status"></p><button class="ce-primary" data-use-choice>Use this ${title.toLowerCase()} →</button>${note('Only existing, compatible saved records are selected. A random completion is fixed in the URL, so reloading keeps the same result.')}</section>`);
    const select=body.querySelector('[data-single-choice]');
    const matches=()=>scoped.filter(x=>String(x[key])===select.value);
    const update=()=>{const count=focus==='category'?data.paintings.filter(x=>x.category===select.value).length:focus==='painting'?null:matches().length;body.querySelector('[data-choice-count]').textContent=count===null?'Other choices will be filled for this painting.':`${count} compatible ${focus==='category'?'paintings':'saved outputs'}.`;body.querySelector('[data-use-choice]').disabled=!choices.length;};
    select.onchange=update;update();
    body.querySelector('[data-use-choice]').onclick=()=>{if(focus==='category'||focus==='painting'){const pid=focus==='painting'?select.value:ceRandom(data.paintings.filter(x=>x.category===select.value))?.painting_id;if(pid)go({ce_painting:pid,ce_candidate:'',ce_random:'1',ce_layer:'difference'});}else{const chosen=ceRandom(matches());if(chosen)go({ce_candidate:chosen.candidate_id,ce_layer:'difference'});}};
  }
  function compare(focused=null) {
    const labels={clean:"Clean controlled reference",damaged:"Damaged input",mask:"Mask / effect support",restored:"Selected restoration",evidence:"Saved "+data.layers.find(x=>x.key===data.layer).label};
    open("Inspect the restoration",`<p class="ce-intro">The full saved images, uncropped. Switch between a large inspection view and all five views together.</p>
      <div class="ce-toolbar ce-view-controls"><button data-overview>Compare all five</button><label>Large view<select data-large-select aria-label="Large inspection view">${Object.keys(labels).map(k=>option(k,labels[k],k===(focused||'restored'))).join('')}</select></label><button data-large-button>Inspect large view</button></div>
      <div class="ce-toolbar ce-zoom-controls"><button data-zoom-out aria-label="Zoom out">−</button><label>Shared zoom <input type="range" min="1" max="5" step=".1" value="1" data-zoom aria-label="Synchronized image zoom"></label><output data-zoom-value>1.0×</output><button data-zoom-in aria-label="Zoom in">+</button><button data-reset-view>Reset view</button></div>
      <div class="ce-comparison"><figure class="ce-large-figure" hidden><div class="ce-viewport ce-large-viewport" tabindex="0" aria-label="Large image; drag or use arrow keys to pan"></div><figcaption></figcaption></figure>
      <div class="ce-compare">${Object.entries(data.images).map(([key,item])=>`<figure><div class="ce-viewport" tabindex="0" aria-label="${esc(labels[key])}; drag or use arrow keys to pan">${item.uri?`<img src="${esc(item.uri)}" alt="${esc(labels[key])}">`:`<span>${esc(item.reason||"Unavailable")}</span>`}</div><figcaption><button data-show-image="${key}">${esc(labels[key])}</button></figcaption></figure>`).join("")}</div></div>
      ${note("Drag to pan; arrow keys work when an image is focused. The same zoom is shared across the normalized image canvases. Producer panels with legends retain their own geometry. The small wall frames show cropped details; these inspection views preserve every pixel.")}
      <div class="ce-toolbar">${button("map","Map provenance & variants")}${button("metrics","Inspect saved measurements")}</div>`);
    let zoom=1, x=0,y=0,drag=null;
    const apply=()=>{body.querySelectorAll(".ce-viewport img").forEach(img=>img.style.transform=`translate(${x}%,${y}%) scale(${zoom})`);body.querySelector("[data-zoom-value]").textContent=zoom.toFixed(1)+"×";};
    body.querySelector("[data-zoom]").oninput=e=>{zoom=Number(e.target.value);apply();};
    body.querySelector("[data-reset-view]").onclick=()=>{zoom=1;x=y=0;body.querySelector("[data-zoom]").value=1;apply();};
    for(const [selector,step] of [['[data-zoom-in]',.25],['[data-zoom-out]',-.25]])body.querySelector(selector).onclick=()=>{zoom=Math.max(1,Math.min(5,zoom+step));body.querySelector('[data-zoom]').value=zoom;apply();};
    const showLarge=key=>{const figure=body.querySelector('.ce-large-figure'),item=data.images[key];figure.hidden=false;body.querySelector('.ce-comparison').classList.add('ce-comparison-single');figure.querySelector('.ce-viewport').innerHTML=item.uri?`<img src="${esc(item.uri)}" alt="${esc(labels[key])}">`:`<span>${esc(item.reason||'Unavailable')}</span>`;figure.querySelector('figcaption').textContent=labels[key];body.querySelector('[data-large-select]').value=key;body.querySelector('[data-overview]').setAttribute('aria-pressed','false');body.querySelector('[data-large-button]').setAttribute('aria-pressed','true');apply();};
    body.querySelector('[data-overview]').onclick=()=>{body.querySelector('.ce-large-figure').hidden=true;body.querySelector('.ce-comparison').classList.remove('ce-comparison-single');body.querySelector('[data-overview]').setAttribute('aria-pressed','true');body.querySelector('[data-large-button]').setAttribute('aria-pressed','false');};
    body.querySelector('[data-large-button]').onclick=()=>showLarge(body.querySelector('[data-large-select]').value);
    body.querySelector('[data-large-select]').onchange=e=>showLarge(e.target.value);
    body.querySelectorAll('[data-show-image]').forEach(el=>el.onclick=()=>showLarge(el.dataset.showImage));
    body.querySelectorAll(".ce-viewport").forEach(el=>{el.onpointerdown=e=>{drag={x:e.clientX,y:e.clientY,ox:x,oy:y};el.setPointerCapture(e.pointerId);};el.onpointermove=e=>{if(!drag)return;x=Math.max(-200,Math.min(200,drag.ox+(e.clientX-drag.x)/el.clientWidth*100));y=Math.max(-200,Math.min(200,drag.oy+(e.clientY-drag.y)/el.clientHeight*100));apply();};el.onpointerup=el.onpointercancel=()=>drag=null;el.onkeydown=e=>{const offsets={ArrowLeft:[-5,0],ArrowRight:[5,0],ArrowUp:[0,-5],ArrowDown:[0,5]};if(offsets[e.key]){e.preventDefault();x=Math.max(-200,Math.min(200,x+offsets[e.key][0]));y=Math.max(-200,Math.min(200,y+offsets[e.key][1]));apply();}};});
    if(focused&&data.images[focused])showLarge(focused);
  }
  function mapDetails() {
    const layer=data.layers.find(x=>x.key===data.layer), image=data.images.evidence;
    const scale=data.map_record;
    open("Saved map · "+layer.label,`<p class="ce-intro">${esc(layer.reason)}. These are saved producer outputs, not a new heat map.</p><div class="ce-toolbar">${layer.paths.map((path,i)=>button("map-variant:"+i,PathName(path))).join("")||"No saved variant"}${button('compare:evidence','Inspect with zoom')}</div>${image.uri?`<img class="ce-panel-image" src="${esc(image.uri)}" alt="Selected evidence map">`:note(esc(image.reason))}<details><summary>Recorded scale & provenance</summary><p>${code(image.path)}</p>${scale?`<dl>${["map_type","cmap","vmin","vmax","center","scale_scope","no_data_policy","renderer_version","sha256"].filter(k=>scale[k]!==null&&scale[k]!==undefined&&scale[k]!=='').map(k=>`<dt>${esc(pretty(k))}</dt><dd>${code(scale[k])}</dd>`).join("")}</dl>`:""}</details>${note("Semantic and structural diagnostics are evidence about controlled-reference agreement, not historical plausibility. Deterministic uncertainty is not applicable, never zero.")}`);
  }
  function PathName(path){return path.split("/").pop().replaceAll("_"," ");}
  function neighbour(lane,rank){
    const query='query_03_landscape_natural_lower_risk';
    const row=data.retrieval.find(r=>r.query_id===query&&r.lane===lane&&Number(r.neighbor_rank)===rank);
    if(!row)return;
    const painting=data.paintings.find(x=>x.painting_id===row.neighbor_painting_id);
    open('Neighbour '+rank+' · '+pretty(lane),`<div class="ce-neighbour-detail"><figure><div class="ce-neighbour-portrait" role="img" aria-label="Clicked stored neighbour image"></div><figcaption>The same image detail shown in the selected frame.</figcaption></figure><section><span class="ce-badge ${lane==='flagged'?'ce-flagged':''}">${esc(pretty(lane))} · rank ${rank}</span><h3>${esc(painting?.title||row.neighbor_painting_id)}</h3><p>${esc(row.neighbor_painting_id)} · ${esc(data.labels[row.neighbor_model_id]||row.neighbor_model_id)}</p><p>${esc(pretty(row.neighbor_recommendation_category))}</p><div class="ce-similarity"><div><small>DINOv2 similarity</small><strong>${Number(row.cosine_similarity).toFixed(3)}</strong></div><div><small>CLIP similarity</small><strong>${row.secondary_cosine_similarity?Number(row.secondary_cosine_similarity).toFixed(3):'Unavailable'}</strong></div></div><button class="ce-primary" data-open-neighbour>Open this exact restoration →</button></section></div>${note('A neighbour of the stored p018 HINT dirt/dust example—not a newly computed match for the current room. Similarity is context, not correctness.')}<details><summary>Exact saved identity and similarity values</summary><dl><dt>Candidate</dt><dd>${code(row.neighbor_candidate_id)}</dd><dt>Source row</dt><dd>${code(row.neighbor_record_id)}</dd><dt>DINOv2 / CLIP</dt><dd>${code(row.cosine_similarity)} / ${code(row.secondary_cosine_similarity)}</dd></dl></details><div class="ce-toolbar">${button('retrieval:2','View all ten neighbour records')}${button('retrieval-panel:'+query,'View the complete original tile panel')}</div>`);
    const tile=stage.querySelector(`[data-action="neighbour:${lane}:${rank}"]`),portrait=body.querySelector('.ce-neighbour-portrait');
    dialog.querySelector('.ce-dialog-context').textContent=`${row.neighbor_painting_id} · ${data.labels[row.neighbor_model_id]||row.neighbor_model_id} · stored query 03`;
    portrait.style.backgroundImage=`url("${sheet.src}")`;portrait.style.backgroundSize=tile.style.backgroundSize;portrait.style.backgroundPosition=tile.style.backgroundPosition;
    body.querySelector('[data-open-neighbour]').onclick=()=>go({ce_painting:row.neighbor_painting_id,ce_candidate:row.neighbor_candidate_id,ce_layer:'difference'});
  }
  function retrieval(index=0) {
    const queries=[...new Set(data.retrieval.map(x=>x.query_id))];const query=queries[index]||queries[0];
    const rows=data.retrieval.filter(x=>x.query_id===query).sort((a,b)=>(a.lane===b.lane?Number(a.neighbor_rank)-Number(b.neighbor_rank):a.lane==='lower_risk'?-1:1)), first=rows[0], selected=first.query_candidate_id===c.candidate_id;
    open("Related cases · stored retrieval",`<p class="ce-intro">Ten saved queries, five lower-risk and five flagged neighbours per query. Similarity supplies context, not correctness.</p>
      ${note(selected?"This stored query matches the selected candidate.":`<strong>Separate stored example.</strong> ${esc(first.query_painting_id)} · ${esc(data.labels[first.query_model_id]||first.query_model_id)} · ${esc(pretty(first.query_case_id.split(first.query_painting_id+'__').pop()))}. This is not retrieval for the active restoration.`)}
      <label>Stored query<select data-query>${queries.map((q,i)=>option(i,pretty(q),q===query)).join("")}</select></label>
      <p>Selected candidate eligibility: DINOv2 ${c.retrieval_dino_eligible?"eligible":"ineligible"}; CLIP ${c.retrieval_clip_eligible?"eligible":"ineligible"}. Across the inspection population, 735 candidates lack eligible retrieval evidence.</p>
      <p>DINOv2 is the primary ranking; CLIP is a separate secondary comparison. Self, same-case and same-painting matches are excluded.</p>
      <div class="ce-table-scroll" tabindex="0" role="region" aria-label="Recorded neighbours"><table><thead><tr><th>Lane / rank</th><th>Neighbour</th><th>DINOv2<br>similarity</th><th>CLIP<br>similarity</th><th>Recorded status</th></tr></thead><tbody>${rows.map(r=>`<tr><td><span class="ce-badge ${r.lane==='flagged'?'ce-flagged':''}">${esc(pretty(r.lane))} · ${esc(r.neighbor_rank)}</span></td><td><button data-neighbour="${esc(r.neighbor_candidate_id)}" data-painting-id="${esc(r.neighbor_painting_id)}">${esc(r.neighbor_painting_id)} · ${esc(data.labels[r.neighbor_model_id]||r.neighbor_model_id)} →</button><details><summary>Exact case & record</summary>${code(r.neighbor_case_id)}<br>${code(r.neighbor_candidate_id)}<br>${code(r.neighbor_record_id)}</details></td><td title="${esc(r.cosine_similarity)}">${Number(r.cosine_similarity).toFixed(3)}</td><td title="${esc(r.secondary_cosine_similarity)}">${r.secondary_cosine_similarity?Number(r.secondary_cosine_similarity).toFixed(3):'Unavailable'}</td><td>${esc(pretty(r.neighbor_recommendation_category))}</td></tr>`).join("")}</tbody></table></div>
      <div class="ce-toolbar">${button("retrieval-panel:"+query,"Open original saved retrieval panel")}${button('export:retrieval','Download the 100 recorded neighbour rows · JSON')}</div>`);
    body.querySelector("[data-query]").onchange=e=>retrieval(Number(e.target.value));
    body.querySelectorAll("[data-neighbour]").forEach(el=>el.onclick=()=>go({ce_painting:el.dataset.paintingId,ce_candidate:el.dataset.neighbour,ce_layer:"difference"}));
  }
  function counterfactual(family) {
    const titles={damage_size:'Damage size',mask_placement:'Mask placement',cross_model:'Model',metric_subset:'Metric choice',diffusion_seed:'Seed',prompt_policy:'Prompt',evidence_family_removal:'Evidence removed'};
    const rows=data.counterfactual_choices.filter(r=>r.family===family),values=[...new Set(rows.map(r=>r.value))];
    const label=value=>family==='cross_model'?(data.labels[value]||value):rows.find(r=>r.value===value).label;
    const title=titles[family];
    open('Choose '+title.toLowerCase(),`<section class="ce-single-picker"><p class="ce-intro">Choose only ${title.toLowerCase()}. Other factors come from a compatible saved study example.</p><label>${title}<select data-cf-choice aria-label="${title}">${values.map(value=>option(value,label(value))).join('')}</select></label><p data-cf-count role="status"></p><button class="ce-primary" data-use-cf>Use this ${title.toLowerCase()} →</button>${note('Choices come from the original fourteen N29 comparisons. The current painting is kept when a matching example exists; otherwise a compatible study case is picked at random. No new restoration or policy result is computed.')}</section>`);
    const select=body.querySelector('[data-cf-choice]');
    const update=()=>{body.querySelector('[data-cf-count]').textContent=`${rows.filter(r=>r.value===select.value).length} compatible saved examples.`;body.querySelector('[data-use-cf]').disabled=!values.length;};select.onchange=update;update();
    body.querySelector('[data-use-cf]').onclick=()=>{const matches=rows.filter(r=>r.value===select.value),same=matches.filter(r=>r.painting_id===p.painting_id),chosen=ceRandom(same.length?same:matches);if(chosen)go({ce_painting:chosen.painting_id,ce_candidate:chosen.candidate_id,ce_layer:'difference',ce_cf:family,ce_value:chosen.value,ce_cf_panel:chosen.panel_path});};
  }
  function comparisonResult(){
    const r=data.selected_comparison,policy=r.record;
    const content=policy?`<div class="ce-grid"><section class="ce-card"><h3>Complete framework</h3><p>${esc(policy.baseline_triggered_flag_count)} triggered flags</p><p>${esc(policy.baseline_insufficient_flag_count)} insufficient indicators</p></section><section class="ce-card"><h3>Selected policy</h3><p>${esc(policy.scenario_triggered_flag_count)} triggered flags</p><p>${esc(policy.scenario_insufficient_flag_count)} insufficient indicators</p></section></div>${note(`${esc(policy.changed_flag_count)} recorded flag-state changes. This is a saved evaluation-policy comparison for the same restoration, not a different restored image.`)}`:`<figure><img class="ce-panel-image ce-chosen-restoration" src="${esc(data.images.restored.uri)}" alt="Selected saved ${esc(r.label)} restoration"><figcaption>${esc(r.painting_id)} · ${esc(data.labels[r.model_id]||r.model_id)} · ${esc(r.label)}</figcaption></figure>`;
    open('Saved choice · '+pretty(r.family),`<p class="ce-intro">${esc(r.family==='cross_model'?(data.labels[r.value]||r.value):r.label)}</p><span class="ce-badge">Compatible saved study example</span><section class="ce-cf-result">${content}</section><details><summary>Exact selection and source</summary><p>${code(r.candidate_id)}</p><p>${code(r.case_id)}</p>${policy?`<p>${code(policy.stability_id)}</p>`:''}</details>${note('This choice loads an existing recorded example. Other factors were filled from compatible records. Selected comparisons are not causal proof.')}<div class="ce-toolbar">${button('counterfactual:'+r.family,'Choose another '+pretty(r.family))}${button('panel:'+r.panel_path,'View the complete original comparison')}</div>`);
  }
  function act(action) {
    if(action==="catalogue"||action.startsWith('catalogue:'))catalogue(action.split(':')[1]||'painting');
    else if(action==="record")record();
    else if(action==="sources")sources();
    else if(action==="metrics")metrics();
    else if(action==="compare"||action.startsWith('compare:'))compare(action.split(':')[1]||null);
    else if(action==="surprise"){const choices=data.selector_rows.filter(x=>x.candidate_id!==c.candidate_id);if(choices.length)go({ce_candidate:choices[Math.floor(Math.random()*choices.length)].candidate_id,ce_layer:'difference'});}
    else if(action==='availability'||action==='uncertainty')availability(action==='uncertainty');
    else if(action==="map")mapDetails();
    else if(action==="retrieval"||action.startsWith("retrieval:"))retrieval(Number(action.split(":")[1]??2));
    else if(action.startsWith('neighbour:')){const [,lane,rank]=action.split(':');neighbour(lane,Number(rank));}
    else if(action.startsWith("counterfactual:"))counterfactual(action.split(":")[1]);
    else if(action.startsWith("layer:"))go({ce_layer:action.split(":")[1]});
    else if(action.startsWith("map-variant:"))go({ce_map:data.layers.find(x=>x.key===data.layer).paths[Number(action.split(":")[1])],ce_view:'map'});
    else if(action.startsWith("report:"))go({ce_report:action.split(":")[1]});
    else if(action.startsWith("export:"))go({ce_export:action.split(":")[1]});
    else if(action.startsWith("notebook:"))go({ce_notebook:action.split(":")[1]});
    else if(action.startsWith("panel:"))go({ce_panel:action.slice(6)});
    else if(action.startsWith("retrieval-panel:")){const path=data.retrieval_panels.find(x=>x.endsWith("/"+action.slice(16)+".png"));if(path)go({ce_panel:path});}
    else if(action==="trust")navigate("?"+new URLSearchParams({room:"trustworthiness",trust_candidate:c.candidate_id}));
    else if(action==="portrait"&&data.review_code)navigate("?"+new URLSearchParams({room:"focused_portrait_review",return_room:"case_explorer",portrait_review:data.review_code}));
    else if(action==="limits")open("Read the evidence with care",`<p class="ce-intro">This is a controlled digital experiment—not a physical-treatment recommendation.</p><div class="ce-grid"><section class="ce-card"><h3>What the reference means</h3><p>The clean image predates the simulated damage. It is not historical ground truth or evidence of material authenticity.</p></section><section class="ce-card"><h3>What a flag means</h3><p>An operational inspection aid, not an expert verdict. Missing evidence is neither zero nor a pass.</p></section><section class="ce-card"><h3>What similarity means</h3><p>Context from saved DINOv2 neighbours with separate CLIP comparison—not proof of restoration quality.</p></section></div>${note("Local step-3 preview: saved evidence only. Remote bundling and full deployment validation remain outside this checkpoint.")}`);
  }
  stage.onclick=e=>{const target=e.target.closest("[data-action]");if(target&&!target.disabled)act(target.dataset.action);};
  doc.querySelector('.ce-access-bar').onclick=e=>{const target=e.target.closest('[data-action]');if(target)act(target.dataset.action);};
  body.onclick=e=>{const target=e.target.closest("[data-action]");if(target&&!target.disabled)act(target.dataset.action);};
  if(data.selected_comparison)comparisonResult();
  else if(data.open_panel)open("Original saved study panel",`${note("A selected N29 study example—not automatically evidence for the active room candidate. Read the panel identities. Selected comparisons are not causal proof.")}<p>${code(data.open_panel.path)}</p><img class="ce-panel-image" src="${esc(data.open_panel.uri)}" alt="Original saved N29 study panel">`);
  else if(data.open_view==='map')mapDetails();
})();
