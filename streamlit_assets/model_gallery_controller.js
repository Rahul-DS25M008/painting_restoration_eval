/* Presentation only: coordinates, selectors, inspection. No scientific computation. */
(() => {
  const payload = __GALLERY_PAYLOAD__;
  const doc = window.parent.document;
  const mainModels = ['opencv_telea', 'lama', 'hint_places2', 'stable_diffusion_inpainting'];
  function mount(stage) {
    const build = payload.version + ':engraving-alignment-v4';
    if (stage.dataset.controllerReady === build) return;
    const abort = new AbortController();
    const on = (node, event, callback) => node.addEventListener(event, callback, {signal: abort.signal});
    const find = selector => stage.querySelector(selector);
    const all = selector => [...stage.querySelectorAll(selector)];
    let model = payload.initial_model;
    let evidence = payload.initial_evidence;
    let previousFocus;
    const dialog = find('.gallery-dialog');
    const body = find('.gallery-dialog-body');
    function node(tag, text, className) {
      const element = doc.createElement(tag);
      if (text !== undefined) element.textContent = String(text);
      if (className) element.className = className;
      return element;
    }
    function button(text, callback) {
      const b = node('button', text); b.type = 'button'; b.addEventListener('click', callback); return b;
    }
    const valid = row => row && row.status === 'ok' && Number.isFinite(row.restored_value);
    function metric(id, key = evidence) { return payload.models[id]?.metrics[key]; }
    function number(value) {return Number.isFinite(value) ? value.toFixed(5) : 'Unavailable';}
    function url(extra = {}) {
      const u = new URL(window.parent.location.href);
      u.searchParams.set('room', 'model_gallery');
      u.searchParams.set('gallery_painting', payload.painting_id);
      u.searchParams.set('gallery_case', payload.case_id);
      u.searchParams.set('gallery_model', model);
      u.searchParams.set('gallery_evidence', evidence);
      u.searchParams.delete('gallery_document');
      Object.entries(extra).forEach(([key, value]) => value === null ? u.searchParams.delete(key) : u.searchParams.set(key, value));
      return u;
    }
    function sourceLink(id) {
      const link = node('a', 'Download the original full HTML report →', 'gallery-report-link');
      link.href = url({gallery_document: id}).href;
      link.target = '_self';
      return link;
    }
    function navigate(destination) {
      // Use a normal link owned by the gallery document. Direct top-location
      // assignment from Streamlit's component iframe is sandbox-restricted.
      const link = doc.createElement('a');
      link.href = destination.href;
      link.target = '_self';
      link.hidden = true;
      stage.append(link);
      link.click();
      link.remove();
    }
    // Project the display content window onto each actual four-corner frame.
    // Solve a homography; this is display geometry, not an image/metric rewrite.
    function transform(quad, scale, width = 768, height = 768) {
      const src = [[0,0],[width,0],[width,height],[0,height]], rows = [];
      src.forEach(([x,y], i) => {
        const [u,v] = quad[i].map(n => n * scale);
        rows.push([x,y,1,0,0,0,-u*x,-u*y,u], [0,0,0,x,y,1,-v*x,-v*y,v]);
      });
      for (let col=0; col<8; col++) {
        let pivot=col;
        for(let r=col+1;r<8;r++) if(Math.abs(rows[r][col])>Math.abs(rows[pivot][col])) pivot=r;
        [rows[col],rows[pivot]]=[rows[pivot],rows[col]];
        const divisor=rows[col][col];
        rows[col]=rows[col].map(v=>v/divisor);
        for(let r=0;r<8;r++) if(r!==col) {const factor=rows[r][col];rows[r]=rows[r].map((v,k)=>v-factor*rows[col][k]);}
      }
      const [a,b,c,d,e,f,g,h]=rows.map(r=>r[8]);
      return `matrix3d(${a},${d},0,${g},${b},${e},0,${h},0,0,1,0,${c},${f},0,1)`;
    }
    const planes = [
      ['.gallery-model-plaque', [[800,612],[1041,613],[1060,736],[789,736]],270,132],
      ['.gallery-hint-book', [[1117,644],[1233,649],[1242,723],[1112,719]],132,86],
      ['.gallery-sdxl-plaque', [[1337,700],[1514,728],[1514,770],[1337,742]],190,50],
      ['.gallery-sdxl-drawer', [[1339,749],[1501,780],[1501,800],[1339,769]],190,25],
    ];
    // Source coordinates measured at the inner lip, not the outer ornamental frame.
    const frameQuads = [
      [[165,331],[345,349],[345,488],[165,489]],
      [[479,355],[650,359],[650,489],[479,489]],
      [[1023,361],[1195,358],[1195,488],[1023,489]],
      [[1338,351],[1522,339],[1522,488],[1338,489]],
      [[707,340],[958,340],[958,508],[707,508]],
      [[540,618],[750,615],[743,726],[512,726]],
      [[1380,584],[1549,598],[1521,678],[1328,653]],
    ];
    all('.gallery-projected').forEach((frame,i)=>frame.dataset.quad=JSON.stringify(frameQuads[i]));
    if (payload.content_bbox) {
      const [x0,y0,x1,y1] = payload.content_bbox;
      all('.gallery-projected img').forEach(img=> {
        Object.assign(img.style,{position:'absolute',width:`${768/(x1-x0)*100}%`,height:`${768/(y1-y0)*100}%`,left:`${-x0/(x1-x0)*100}%`,top:`${-y0/(y1-y0)*100}%`});
      });
      stage.dataset.displayContentBbox=JSON.stringify(payload.content_bbox);
    }
    find('.gallery-model-plaque').append(find('.gallery-evidence-readout'));
    const sdxlLettering=node('div');
    sdxlLettering.append(...find('.gallery-sdxl-plaque').childNodes);
    find('.gallery-sdxl-plaque').append(sdxlLettering);
    // Real text along shallow curves, matching the concave marble entablature.
    // Keep the semantic headings available to assistive technology.
    const heading=find('.gallery-heading');
    const headingSvg=doc.createElementNS('http://www.w3.org/2000/svg','svg');
    headingSvg.setAttribute('viewBox','0 0 1000 150');
    headingSvg.setAttribute('aria-hidden','true');
    const headingDefs=doc.createElementNS(headingSvg.namespaceURI,'defs');
    headingSvg.append(headingDefs);
    [['h1','M 40 28 Q 500 98 960 28','58'],['h2','M 5 77 Q 500 113 995 77','29'],['p','M 20 118 Q 500 145 980 118','19']].forEach(([tag,d,size],i)=>{
      const source=heading.querySelector(tag),id=`gallery-wall-arc-${i}`;
      const path=doc.createElementNS(headingSvg.namespaceURI,'path');path.id=id;path.setAttribute('d',d);headingDefs.append(path);
      const text=doc.createElementNS(headingSvg.namespaceURI,'text');text.setAttribute('font-size',size);text.setAttribute('text-anchor','middle');
      if(i===0)text.setAttribute('font-weight','600');
      const textPath=doc.createElementNS(headingSvg.namespaceURI,'textPath');textPath.setAttribute('href','#'+id);textPath.setAttribute('startOffset','50%');textPath.textContent=source.textContent;
      text.append(textPath);headingSvg.append(text);source.classList.add('gallery-accessible-heading');
    });
    heading.append(headingSvg);
    // Match the engraved two-line reference; scope details remain in the records.
    const footer=find('.gallery-conclusion');
    const svg=doc.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('viewBox','0 0 760 92');svg.setAttribute('aria-hidden','true');
    const defs=doc.createElementNS(svg.namespaceURI,'defs');
    [['gallery-inscription-arc','M 12 22 Q 380 54 748 22'],['gallery-inscription-subarc','M 105 66 Q 380 84 655 66']].forEach(([id,d])=>{const path=doc.createElementNS(svg.namespaceURI,'path');path.id=id;path.setAttribute('d',d);defs.append(path);});
    svg.append(defs);
    [['gallery-inscription-arc','LaMa led 10 of 11 separate quality anchors · Telea led crop SSIM','22'],['gallery-inscription-subarc','Separate comparisons · no combined score','21']].forEach(([id,text,size])=>{
      const line=doc.createElementNS(svg.namespaceURI,'text');line.setAttribute('font-size',size);line.setAttribute('text-anchor','middle');
      const path=doc.createElementNS(svg.namespaceURI,'textPath');path.setAttribute('href','#'+id);path.setAttribute('startOffset','50%');path.textContent=text;line.append(path);svg.append(line);
    });
    footer.replaceChildren(svg);
    footer.setAttribute('aria-label','Overall registered comparison: LaMa led 10 of 11 separate quality anchors; Telea led crop SSIM. Separate comparisons, no combined score.');
    function fitFrames() {
      const scale = stage.getBoundingClientRect().width / 1672;
      all('[data-quad]').forEach(element => {
        element.style.transform = transform(JSON.parse(element.dataset.quad), scale);
        element.style.visibility = 'visible';
      });
      planes.forEach(([selector,quad,w,h])=>{
        const el=find(selector);
        el.style.width=w+'px';el.style.height=h+'px';
        el.style.transform=transform(quad,scale,w,h);
      });
    }
    function fitViewport() {
      const top=Math.max(0,stage.getBoundingClientRect().top);
      const available=Math.max(160,window.parent.innerHeight-top-16);
      stage.style.width=`min(100%, ${available*1672/941}px, 1920px)`;
      fitFrames();
    }
    function close() {dialog.close();previousFocus?.focus();}
    function open(title, kind = 'record') {
      if (!dialog.open) previousFocus = doc.activeElement;
      dialog.dataset.kind=kind;
      find('#gallery-dialog-title').textContent = title;
      body.replaceChildren();
      body.append(node('p', {record:'Collection archive / Method dossier',evidence:'Conservation bench / Recorded evidence',decision:'Research library / Decision study',bounded:'Side collection / Bounded study'}[kind], 'gallery-dossier-kicker'));
      if (!dialog.open) dialog.showModal();
      dialog.scrollTop=0;
      find('[data-close]').focus();
    }
    function stats(items) {
      const strip=node('div',undefined,'gallery-stat-strip');
      items.forEach(([value,label])=>{const card=node('div',undefined,'gallery-stat');card.append(node('strong',value),node('span',label));strip.append(card);});
      return strip;
    }
    function chapter(title, items, index) {
      const card=node('section',undefined,'gallery-dossier-chapter');
      card.append(node('span',index,'gallery-chapter-number'),node('h3',title));
      const list=node('ul');items.forEach(text=>list.append(node('li',text)));card.append(list);return card;
    }
    on(find('[data-close]'), 'click', close);
    on(dialog, 'cancel', () => previousFocus?.focus());
    on(dialog, 'click', e => {if(e.target===dialog) {const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)close();}});
    function identity(id) {
      const candidate = payload.models[id].candidate;
      const identity=node('section',undefined,'gallery-dossier-identity');
      identity.append(node('h3',payload.painting_label),node('p',payload.case_label));
      const accession=node('details');accession.append(node('summary','Accession & candidate identity'),node('code', `Case: ${payload.case_id} | Candidate: ${candidate.candidate_id}`));identity.append(accession);
      if (candidate.prompt_variant_id) identity.append(node('p', `Recorded primary candidate · seed ${candidate.seed} · prompt ${candidate.prompt_variant_id}. No seed or prompt is substituted.`));
      body.append(identity);
      if (payload.experiment === 'synthetic_degradation') body.append(node('p', 'Supplementary synthetic masked-removal diagnostic; not a general degradation-removal or historical-recovery claim.', 'gallery-boundary'));
    }
    function evidenceTable(ids, selected) {
      const spec = payload.evidence[evidence];
      const table = node('table');
      table.setAttribute('aria-label', `${spec.label} for this exact case`);
      const head = node('tr');
      ['Method','Damaged input','Restored candidate','Signed improvement'].forEach(x=>head.append(node('th',x)));
      const thead=node('thead');thead.append(head);table.append(thead);
      const tbody=node('tbody');
      ids.forEach(id=> {
        const row=metric(id), tr=node('tr');
        if(id===selected)tr.className='gallery-selected-record';
        [payload.models[id].label, valid(row)?number(row.damaged_value):'Unavailable',valid(row)?number(row.restored_value):'Unavailable',valid(row)?number(row.improvement_value):row?.issue||'No valid recorded row'].forEach(x=>tr.append(node('td',x)));
        tbody.append(tr);
      });
      const scroll=node('div',undefined,'gallery-table-scroll');
      table.append(tbody);scroll.append(table);body.append(node('h3','The comparison ledger'),scroll);
      body.append(node('p', `${spec.label} · ${spec.direction}. ${spec.explanation}`));
      body.append(node('p', 'Values are recorded N13 full-reference measurements for this case. Positive signed improvement means lower error / higher similarity than the damaged input. Neither this metric nor visual plausibility establishes historical correctness.', 'gallery-boundary'));
    }
    function inspect(id = model, initialView = 'restored') {
      const entry = payload.models[id];
      open(`${entry.label} · inspect this case`,id==='sdxl_inpainting'?'bounded':'evidence');identity(id);
      const controls=node('div',undefined,'gallery-inspection-controls');
      const img=node('img',undefined,'gallery-inspection-image');
      const caption=node('figcaption');
      const views={reference:payload.reference,damaged:payload.damaged,restored:entry.uri,mask:payload.mask};
      function view(name) {
        img.src=views[name];img.alt=`${payload.painting_id} ${name} ${name==='restored'?entry.label:''}`;
        controls.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===name)));
        caption.textContent = `${name==='restored'?entry.label+' restoration':name.charAt(0).toUpperCase()+name.slice(1)} · complete recorded 768 × 768 canvas`;
      }
      Object.keys(views).forEach(name=> {const b=button(name.charAt(0).toUpperCase()+name.slice(1),()=>view(name));b.dataset.view=name;controls.append(b);});
      const bench=node('div',undefined,'gallery-inspection-bench'),figure=node('figure',undefined,'gallery-inspection-figure'),notes=node('aside',undefined,'gallery-inspection-notes');
      figure.append(controls,img,caption);
      const row=metric(id),spec=payload.evidence[evidence];
      notes.append(node('span','Selected measurement','gallery-dossier-kicker'),node('h3',spec?.label||'Recorded evidence'));
      notes.append(stats([[number(valid(row)?row.damaged_value:null),'Damaged input'],[number(valid(row)?row.restored_value:null),'Restored candidate'],[number(valid(row)?row.improvement_value:null),'Signed improvement']]));
      notes.append(node('p',spec?`${spec.direction}. ${spec.explanation}`:'No valid recorded measurement.'),node('p','One case, one measurement—not the overall rank.','gallery-boundary'));
      if(id==='sdxl_inpainting')notes.append(node('p','Bounded collection · excluded from the four-method full-scope ranking.','gallery-boundary'));
      bench.append(figure,notes);body.append(bench);view(initialView);
      if(id==='sdxl_inpainting') {
        body.append(node('p','Bounded SDXL study: 24 completed / 35 scheduled cases, across 19 paintings with completed results. One timeout and ten skipped. Not included in the full-scope ranking.','gallery-boundary'));
        evidenceTable([id],id);
      } else evidenceTable(mainModels,id);
      body.append(button('Open model record',()=>record(id)));
    }
    function dictionary(title, values) {
      const details=node('details'),summary=node('summary',title),grid=node('dl',undefined,'gallery-record-grid');
      Object.entries(values).forEach(([key,value])=> {
        if(key==='resolved_path'||value===null||value==='')return;
        grid.append(node('dt',key.replaceAll('_',' ')),node('dd',typeof value==='object'?JSON.stringify(value):String(value)));
      });
      details.append(summary,grid);return details;
    }
    function record(id = model) {
      const entry=payload.models[id],card=entry.card;
      open(`${entry.label} · full model record`);identity(id);
      body.append(node('p',card.original_purpose,'gallery-dossier-lead'));
      body.append(stats([[card.evaluated_painting_count,'Paintings'],[card.evaluated_case_count,'Cases'],[card.evaluated_candidate_count,'Candidates'],[`${Number(card.median_runtime_seconds).toFixed(3)} s`,'Recorded median runtime']]));
      body.append(node('p','Runtime is workstation-specific, not a portable benchmark.','gallery-dossier-footnote'));
      const chapters=node('div',undefined,'gallery-chapter-pair');
      chapters.append(chapter('What this method brings',JSON.parse(card.strengths_json||'[]'),'01'),chapter('What to watch for',JSON.parse(card.weaknesses_json||'[]'),'02'));
      body.append(chapters);
      body.append(node('p','Overall registered comparison: LaMa led 10 of 11 separate quality anchors; Telea led crop SSIM. This is population-level evidence across 300 paintings, not a ranking of the selected case. Most anchors use 2,320 non-zero cases; structural affinity uses 2,620. Separate comparisons; no combined score.','gallery-boundary'));
      body.append(node('p',card.domain_gap,'gallery-boundary'));
      body.append(dictionary('Exact selected candidate, input hashes, configuration, seed and prompt',entry.candidate));
      body.append(dictionary('Complete recorded model card, licenses and limitations',card));
      body.append(sourceLink(id));
      body.append(node('p','Additional SD seed and prompt studies belong to Stability Lab. This room consistently shows each case’s recorded primary candidate, selected without metric-based cherry-picking.'));
    }
    function hint() {
      const d=payload.hint;open('Why was HINT selected?','decision');
      body.append(node('span','Selected for the main study · HINT','gallery-decision-seal'));
      body.append(stats([[d.pilot_scope.paintings,'Pilot paintings'],[d.pilot_scope.cases,'Pilot cases'],[d.pilot_scope.candidates,'Candidates'],[d.paired_evidence.separate_anchor_count,'Separate anchors']]));
      body.append(node('p',`${d.pilot_scope.paintings} paintings · ${d.pilot_scope.cases} cases · ${d.pilot_scope.candidates} candidates. A separate method-selection pilot, not the overall 300-painting ranking.`));
      body.append(node('h3',`HINT selected over MAT`));
      body.append(node('p',`${d.paired_evidence.separate_anchor_count} separate anchors · ${d.paired_evidence.paired_comparison_count} paired comparisons: HINT ${d.paired_evidence.hint_case_anchor_wins} wins, MAT ${d.paired_evidence.mat_case_anchor_wins}, ${d.paired_evidence.ties} ties. No combined score.`));
      body.append(stats([[d.paired_evidence.hint_case_anchor_wins,'HINT case–anchor wins'],[d.paired_evidence.mat_case_anchor_wins,'MAT case–anchor wins'],[d.paired_evidence.ties,'Ties']]));
      [['selection_rationale','The selection rationale'],['human_visual_assessment','At the viewing bench'],['limitations','The limits of this decision']].forEach(([key,title],i)=>body.append(chapter(title,d[key],`0${i+1}`)));
      body.append(sourceLink('hint_decision'));
    }
    function sdxl() {
      if(payload.models.sdxl_inpainting) {inspect('sdxl_inpainting');return;}
      open('SDXL · bounded study','bounded');
      body.append(node('span','No completed result for this exact case','gallery-decision-seal'));
      body.append(stats([[24,'Completed cases'],[35,'Scheduled cases'],[19,'Paintings with results']]));
      body.append(node('p',`No completed SDXL result for ${payload.case_id}. Status: ${payload.sdxl_status.replaceAll('_',' ')}.`));
      body.append(node('p',payload.sdxl_reason));
      body.append(node('p','Only 24 of 35 scheduled cases completed: one timeout and ten skipped. Completed results cover 19 paintings. Availability is matched by exact case ID, never by painting alone.','gallery-boundary'));
      body.append(node('p','SDXL is excluded from the four-method overall ranking. Choose a different actual case to inspect its availability; no substitute result is shown here.'));
      body.append(sourceLink('sdxl_inpainting'));
    }
    function update() {
      const entry=payload.models[model],card=entry.card;
      stage.dataset.selectedModel=model;
      stage.dataset.candidateId=entry.candidate.candidate_id;
      all('[data-model]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.model===model)));
      const img=find('[data-table-image] img');img.src=entry.uri;img.alt=`${entry.label} restoration for ${payload.case_id}`;
      find('[data-model-name]').textContent=entry.label;
      find('[data-model-coverage]').textContent=`${card.evaluated_case_count.toLocaleString()} / 2,620 cases`;
      find('[data-model-runtime]').textContent=`Recorded median ${Number(card.median_runtime_seconds).toFixed(2)} s`;
      const descriptions={opencv_telea:['Strength · fast, local interpolation','Watch for · lost large-scale structure'],lama:['Strength · broader image context','Watch for · smoothed or unsupported detail'],hint_places2:['Strength · mask-aware context','Watch for · photographic domain gap'],stable_diffusion_inpainting:['Strength · prompt-guided synthesis','Watch for · plausible invented detail']};
      find('[data-model-strength]').textContent=descriptions[model][0];
      find('[data-model-caution]').textContent=descriptions[model][1];
      const select=find('#gallery-evidence');select.replaceChildren();
      Object.entries(payload.evidence).forEach(([key,spec])=>{const option=node('option',spec.label);option.value=key;option.disabled=!valid(metric(model,key));option.title=option.disabled?'No valid recorded metric for this case and region':spec.explanation;select.append(option);});
      const requested=evidence;
      if(!payload.evidence[evidence]||!valid(metric(model,evidence))) evidence=Object.keys(payload.evidence).find(key=>valid(metric(model,key)))||'';
      select.value=evidence;select.disabled=!evidence;
      stage.dataset.evidence=evidence;
      const row=metric(model),spec=payload.evidence[evidence];
      find('[data-evidence-readout]').textContent=spec?`${spec.label} · ${number(row?.restored_value)} →`:'No valid recorded evidence';
      find('[data-evidence-note]').textContent=requested!==evidence?'Valid alternative':'This case';
      find('.gallery-live').textContent=`${entry.label} selected. ${find('[data-evidence-readout]').textContent}. ${requested!==evidence?'The previous evidence choice is unavailable for this case.':''}`;
    }
    all('[data-model]').forEach(b=>on(b,'click',()=>{model=b.dataset.model;update();}));
    all('[data-action]').forEach(b=>on(b,'click',()=> {
      ({inspect:()=>inspect(),damaged:()=>inspect(model,'damaged'),record:()=>record(),hint,sdxl})[b.dataset.action]?.();
    }));
    on(find('#gallery-evidence'),'change',e=>{evidence=e.target.value;update();});
    on(find('#gallery-painting'),'change',e=>{
      stage.dataset.loading='true';find('.gallery-live').textContent='Loading selected painting and its declared mixed-damage opening case…';
      navigate(url({gallery_painting:e.target.value,gallery_case:null}));
    });
    on(find('#gallery-case'),'change',e=>{stage.dataset.loading='true';navigate(url({gallery_case:e.target.value}));});
    const resize=new ResizeObserver(fitFrames);resize.observe(stage);on(window.parent,'resize',fitViewport);fitViewport();update();
    const cleanup=new MutationObserver(()=>{if(!stage.isConnected){abort.abort();resize.disconnect();cleanup.disconnect();if(dialog.open)dialog.close();}});
    cleanup.observe(doc.body,{childList:true,subtree:true});
    stage.dataset.controllerReady=build;
  }
  function attempt(){const stage=doc.querySelector(`.model-stage[data-case-id="${payload.case_id}"]`);if(stage){mount(stage);return true;}return false;}
  if(!attempt()){const observer=new MutationObserver(()=>{if(attempt())observer.disconnect();});observer.observe(doc.body,{childList:true,subtree:true});setTimeout(()=>observer.disconnect(),15000);}
})();
