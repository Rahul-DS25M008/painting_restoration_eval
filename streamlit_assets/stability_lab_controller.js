/* Presentation only. All measurements and images come from recorded artifacts. */
(() => {
  const data = __STABILITY_PAYLOAD__;
  const doc = window.parent.document;
  function mount(stage) {
    if (stage.dataset.controllerReady === data.version) return;
    const find = s => stage.querySelector(s);
    const all = s => [...stage.querySelectorAll(s)];
    const dialog = find('.lab-dialog'), body = find('.lab-dialog-body');
    let previousFocus;
    const current = data.current;
    const fmt = v => Number.isFinite(v) ? v.toFixed(5) : 'Unavailable';
    function node(tag, text, cls) {
      const e = doc.createElement(tag);
      if (text !== undefined) e.textContent = String(text);
      if (cls) e.className = cls;
      return e;
    }
    function button(text, action) {const b = node('button', text); b.type = 'button'; b.addEventListener('click', action); return b;}
    function navigate(extra) {
      const targetTest=extra.stability_test || data.test;
      if(targetTest!=='seed' && !data.focused_paintings.includes(extra.stability_painting || data.painting)) {
        open('Outside the focused stress cohort');
        paragraph('This painting has recorded seed groups but is not one of the 35 focused stress-test paintings. Choose an eligible painting explicitly.','lab-boundary');
        body.append(button('Use opening painting p018 for this test →',()=>navigate({...extra,stability_painting:'p018',stability_case:null,stability_group:null})));return;
      }
      const u = new URL(window.parent.location.href);
      [...u.searchParams.keys()].forEach(k => {if (k !== 'room') u.searchParams.delete(k);});
      const state = {room:'stability_lab', stability_test:data.test, stability_painting:data.painting,
        stability_model:data.model, stability_evidence:data.evidence, stability_condition:data.condition,
        stability_family:data.family, stability_case:data.selected,
        stability_group:data.test === 'seed' ? data.seed?.id : null, ...extra};
      Object.entries(state).forEach(([k,v]) => {if(v !== null && v !== undefined) u.searchParams.set(k,String(v));});
      const a = node('a'); a.href = u.href; a.target = '_self'; stage.append(a);
      find('.lab-live').textContent = 'Loading the selected recorded evidence…';
      a.click(); a.remove();
    }
    function open(title) {
      previousFocus = doc.activeElement;
      find('#lab-dialog-title').textContent = title; body.replaceChildren();
      if (!dialog.open) dialog.showModal();
      dialog.scrollTop = 0;
    }
    function close() {dialog.close(); previousFocus?.focus();}
    function paragraph(text, cls) {const p = node('p',text,cls); body.append(p); return p;}
    function chapter(title, text) {const c = node('section',undefined,'lab-chapter'); c.append(node('h3',title),node('p',text)); body.append(c);return c;}
    function switchTest(kind) {
      if (kind === 'seed' && data.model !== 'stable_diffusion_inpainting') {seeds(); return;}
      navigate({stability_test:kind,stability_case:null,stability_group:null});
    }
    function ledger(kind) {
      const info = data.ledger[kind]; open(info.title);
      paragraph(info.counts,'lab-stat');
      chapter('What this test asks',data.notes[kind][1]);
      chapter('Recorded study finding',info.finding);
      paragraph(info.boundary,'lab-boundary');
      paragraph(info.source,'lab-image-caption');
      body.append(button('Explore this test →',() => switchTest(kind)));
    }
    function series() {
      if (data.test === 'seed') return data.seed.pairs.map(p => ({label:`${Number(p.seed_a)} / ${Number(p.seed_b)}`,value:p.status === 'ok' ? p.value : null,row:p.uncertainty_metric_id}));
      return data.points.map(p => ({label:p.label,value:p.metric.value,x:p.x,row:p.metric.row_id,case:p.case_id}));
    }
    function chart(big=false) {
      const points = series(); const ns='http://www.w3.org/2000/svg';
      const svg = doc.createElementNS(ns,'svg'); svg.setAttribute('viewBox','0 0 400 210'); svg.setAttribute('role','img');
      svg.setAttribute('aria-label','Recorded values: '+points.map(p=>`${p.label}: ${fmt(p.value)}`).join('; '));
      const el=(tag,attrs,text)=>{const e=doc.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));if(text!==undefined)e.textContent=text;svg.append(e);return e;};
      const vals = points.filter(p=>Number.isFinite(p.value)).map(p=>p.value);
      if (!vals.length) {el('text',{x:200,y:100,'text-anchor':'middle'},'No recorded values');return svg;}
      let lo=Math.min(...vals),hi=Math.max(...vals); const range=Math.max(hi-lo,Math.abs(hi)*.03,.001); lo-=range*.12; hi+=range*.12;
      if(data.evidence!=='crop_ssim' || data.test==='seed')lo=Math.max(0,lo);
      const py=v=>167-(v-lo)/(hi-lo)*138;
      const numeric=data.test==='size'; const xs=points.map((p,i)=>numeric?p.x:i);
      const xmin=Math.min(...xs),xmax=Math.max(...xs);
      const px=i=>xmax===xmin?220:48+(xs[i]-xmin)/(xmax-xmin)*328;
      [0,.5,1].forEach(t=>{const y=167-t*138;el('line',{x1:45,y1:y,x2:381,y2:y,stroke:'#896b3c',opacity:.28,'stroke-width':1});el('text',{x:39,y:y+4,'text-anchor':'end','font-size':big?11:14,fill:'#4c3921','font-family':'Georgia'},(lo+t*(hi-lo)).toFixed(hi<2?3:1));});
      el('path',{d:'M45 23V169H382',fill:'none',stroke:'#72532c','stroke-width':1.4});
      if(numeric && vals.length===points.length)el('polyline',{points:points.map((p,i)=>`${px(i)},${py(p.value)}`).join(' '),fill:'none',stroke:'#345c56','stroke-width':2.6});
      points.forEach((p,i)=>{
        if(Number.isFinite(p.value))el('circle',{cx:px(i),cy:py(p.value),r:p.case===data.selected?5.5:4,fill:p.case===data.selected?'#9e512c':'#345c56',stroke:'#f2e0bb','stroke-width':1});
        const label=data.test==='seed'?String(i+1):p.label.replace('Variant ','V');
        el('text',{x:px(i),y:190,'text-anchor':'middle','font-family':'Georgia','font-size':big?12:15,fill:'#51391f'},label);
      });
      el('text',{x:214,y:208,'text-anchor':'middle','font-family':'Georgia','font-size':11,fill:'#695135'},data.test==='size'?'Requested damage area':data.test==='seed'?'Recorded seed pair':data.test==='mask'?'Placement (same family + area)':'Recorded severity');
      return svg;
    }
    function chartRecord() {
      open(data.test==='seed'?'Seed-pair disagreement':data.evidence_spec.label+' · recorded trajectory');
      paragraph(data.painting_label+' · '+(data.model==='stable_diffusion_inpainting'?'Stable Diffusion':data.model==='lama'?'LaMa':data.model==='hint_places2'?'HINT':'Telea'));
      const plot=node('div',undefined,'lab-big-chart');const svg=chart(true);svg.style.width='100%';svg.style.height='100%';plot.append(svg);body.append(plot);
      paragraph(data.test==='seed'?'Masked-region pairwise RGB MAE · normalized RGB (0–1). Six pairs from four seeds; not independent observations or calibrated confidence.':data.evidence_spec.direction+' · '+data.evidence_spec.region+' · '+data.evidence_spec.unit,'lab-boundary');
      const table=node('table'),head=node('tr');['Condition','Recorded value','Source row'].forEach(t=>head.append(node('th',t)));table.append(head);
      series().forEach(p=>{const tr=node('tr',undefined,p.case===data.selected?'lab-row-current':'');tr.append(node('td',p.label),node('td',fmt(p.value)));const td=node('td');td.append(node('code',p.row));tr.append(td);table.append(tr);});body.append(table);
      paragraph(data.test==='seed'?data.seed.stem:current.metric.source,'lab-image-caption');
      paragraph(data.notes[data.test][1]);
      body.append(button('Open this test’s interpretation →',()=>ledger(data.test)));
    }
    function inspect(which, seedIndex) {
      const member=seedIndex!==undefined?data.seed.members[seedIndex]:null;
      open(member?'Recorded seed '+member.seed:which==='input'?'Controlled input · exact source':which==='reference'?'Controlled reference · exact source':which==='mask'?'Recorded mask · exact source':'Recorded restoration · exact source');
      const wrap=node('div',undefined,'lab-inspection'),figure=node('div'),img=node('img');
      img.src=member?member.uri:which==='input'?current.damaged:which==='reference'?data.reference:which==='mask'?current.mask:current.restored;
      img.alt=find('#lab-dialog-title').textContent;figure.append(img,node('p','Full normalized canvas. No padding removed in this inspection.','lab-image-caption'));
      const notes=node('div');notes.append(node('h3',data.painting_label),node('p',data.notes[data.test][0]),node('code',member?member.candidate_id:current.case_id));
      if(!member && (which==='input' || which==='restored')) {
        const value=which==='input'?current.metric.input_value:current.metric.value;
        notes.append(node('p',data.evidence_spec.label+' · '+fmt(value),'lab-stat'),node('p',(which==='input'?'Input':'Restoration')+' versus controlled reference · '+data.evidence_spec.direction+' · '+data.evidence_spec.region));
      }
      notes.append(node('p','The clean image is a controlled reference, not evidence of the original historical appearance.','lab-boundary'));
      const controls=node('div',undefined,'lab-controls');[['input','Input'],['restored','Restoration'],['reference','Reference'],['mask','Mask']].forEach(([k,t])=>controls.append(button(t,()=>inspect(k))));notes.append(controls);wrap.append(figure,notes);body.append(wrap);
    }
    function seeds() {
      open('Repeated-seed drawer');
      if(data.model!=='stable_diffusion_inpainting') {
        chapter('Stable Diffusion only','This method has no repeated-seed results. Switching is an explicit choice; no variability is invented for a deterministic method.');
        body.append(button('Switch to Stable Diffusion →',()=>navigate({stability_model:'stable_diffusion_inpainting'})));
        paragraph('Then choose Repeated seeds in the Test ledger.','lab-image-caption');return;
      }
      if(!data.seed) {
        chapter('No seed group for this case','This mask-placement or degradation case has no registered four-seed group. The recorded groups cover canonical and damage-size cases.');
        body.append(button('Choose a supported repeated-seed group →',()=>switchTest('seed')));return;
      }
      paragraph('4 seeds · 6 unordered pairs · '+data.seed.prompt,'lab-stat');
      const grid=node('div',undefined,'lab-seed-grid');data.seed.members.forEach((m,i)=>{const b=button('',()=>inspect('restored',i));const img=node('img');img.src=m.uri;img.alt='Recorded seed '+m.seed;b.append(img,node('p','Seed '+m.seed));grid.append(b);});body.append(grid);
      paragraph('Masked-region mean pixel RGB standard deviation: '+fmt(data.seed.std)+' · normalized RGB (0–1)');
      paragraph('Empirical disagreement only—not calibrated confidence. Low variability can be consistently wrong.','lab-boundary');
      if(data.seed.overlay){const img=node('img',undefined,'lab-overlay');img.src=data.seed.overlay;img.alt='Producer-rendered seed disagreement map with its original scale and labels';body.append(img);paragraph('Original N22 rendered overlay, including its recorded scale.','lab-image-caption');}
      else paragraph('This canonical group has recorded numeric variability; no per-case overlay is published by N18. Nothing has been generated to fill the gap.','lab-image-caption');
      body.append(node('code',data.seed.id+' · '+data.seed.case_id));
      if(data.test!=='seed')body.append(button('Open this group’s six-pair chart →',()=>navigate({stability_test:'seed',stability_group:data.seed.id,stability_case:null})));
    }
    function excluded() {
      open('Not an inpainting task');
      chapter('Keep the task boundary intact','Blur, fading and colour transformations are generated stress diagnostics, not missing-region restoration tasks. They are deliberately excluded from the four-method restoration view.');
      paragraph('1,155 generated cases; 350 eligible masked-removal cases.','lab-stat');
      paragraph('The glass specimens are decorative selectors, not measurements or simulated chemical samples.','lab-image-caption');
      paragraph('Procedural RGB stress does not establish physical ageing, chemical reversibility or conservation safety.','lab-boundary');
    }
    function maskCondition() {
      open('Choose a fixed mask condition');
      paragraph('Each family is paired with one target area. Compare five placements within a condition; do not interpret family and area as independently varied factors.','lab-boundary');
      const controls=node('div',undefined,'lab-controls');
      [['scratch_thin','Thin scratches · 2%'],['loss_small','Small loss · 4.5%'],['loss_large','Large loss · 12.5%']].forEach(([k,label])=>controls.append(button(label,()=>navigate({stability_test:'mask',stability_condition:k,stability_case:null,stability_group:null}))));body.append(controls);
    }
    function scope() {
      open('What “stable” can—and cannot—mean');
      chapter('Four different questions','Damage-size sensitivity, mask-placement robustness, procedural degradation stress and repeated-seed variability are separate tests. There is no combined stability score.');
      paragraph('The focused stress tests use 35 paintings, seven per category. Repeated cases are not independent paintings; this balanced cohort is not an art-historical style-effect claim.','lab-boundary');
      paragraph('Stable here means less change under this controlled test—not historically correct, safe to conserve or certain.');
      const controls=node('div',undefined,'lab-controls');Object.keys(data.ledger).forEach(k=>controls.append(button(data.ledger[k].title,()=>ledger(k))));body.append(controls);
    }
    all('[data-action]').forEach(b=>b.addEventListener('click',()=>{
      const a=b.dataset.action;
      if(a==='close')close();else if(a==='chart')chartRecord();else if(a==='seeds')seeds();else if(a==='scope')scope();else if(a==='excluded')excluded();else if(a==='mask-condition')maskCondition();else inspect(a);
    }));
    all('[data-ledger]').forEach(b=>b.addEventListener('click',()=>ledger(b.dataset.ledger)));
    all('[data-size]').forEach(b=>b.addEventListener('click',()=>navigate({stability_test:'size',stability_case:`damage_size__${data.painting}__loss_large__size_${b.dataset.size.padStart(2,'0')}pct`,stability_group:null})));
    all('[data-variant]').forEach(b=>{
      const variant=Number(b.dataset.variant);const point=data.test==='mask'?data.points[variant-1]:null;
      const preview=data.mask_previews[variant-1];
      if(preview){const img=node('img');img.src=preview;img.alt='';b.prepend(img);}
      b.setAttribute('aria-pressed',String(Boolean(point && point.case_id===data.selected)));
      b.addEventListener('click',()=>{
        navigate({stability_test:'mask',stability_case:data.mask_cases[variant-1] || null,stability_group:null});
      });
    });
    all('[data-family]').forEach(b=>{b.setAttribute('aria-pressed',String(data.test==='degradation' && data.family===b.dataset.family));b.addEventListener('click',()=>navigate({stability_test:'degradation',stability_family:b.dataset.family,stability_case:null,stability_group:null}));});
    all('[data-seed]').forEach(b=>b.addEventListener('click',()=>inspect('restored',Number(b.dataset.seed))));
    all('[data-selector]').forEach(s=>s.addEventListener('change',()=>{
      const key=s.dataset.selector;
      if(key==='model' && data.test==='seed' && s.value!=='stable_diffusion_inpainting'){
        const requested=s.value;s.value=data.model;open('Choose a test for this method');
        paragraph('Repeated seeds is Stable Diffusion only. To use the selected deterministic method, explicitly return to a damage-size test.');
        body.append(button('Use selected method in Damage size →',()=>navigate({stability_model:requested,stability_test:'size',stability_case:null,stability_group:null})));return;
      }
      const changes={['stability_'+key]:s.value};
      if(['painting','condition','family','group'].includes(key))changes.stability_case=null;
      if(key==='painting')changes.stability_group=null;
      navigate(changes);
    }));
    dialog.addEventListener('close',()=>previousFocus?.focus());
    dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)close();}});
    find('.lab-chart').append(chart());
    function cropContent() {
      const [x0,y0,x1,y1]=data.content_bbox;const w=x1-x0,h=y1-y0;
      all('.lab-main-image img,.lab-mini-image img,.lab-desk-thumbnail img').forEach(img=>{img.style.width=(768/w*100)+'%';img.style.height=(768/h*100)+'%';img.style.left=(-x0/w*100)+'%';img.style.top=(-y0/h*100)+'%';});
    }
    function fitViewport() {
      const top=Math.max(0,stage.getBoundingClientRect().top);
      const available=Math.max(160,window.parent.innerHeight-top-16);
      stage.style.width=`min(100%, ${available*1672/941}px, 1920px)`;
    }
    window.parent.addEventListener('resize',fitViewport);
    const cleanup=new MutationObserver(()=>{if(!stage.isConnected){window.parent.removeEventListener('resize',fitViewport);cleanup.disconnect();}});
    cleanup.observe(doc.body,{childList:true,subtree:true});
    cropContent();fitViewport();stage.dataset.controllerReady=data.version;
    find('.lab-live').textContent='Recorded Stability Lab evidence ready.';
  }
  function attempt(){const s=doc.querySelector('.stability-stage');if(s?.dataset.version===data.version){mount(s);return true;}return false;}
  if(!attempt()){const obs=new MutationObserver(()=>{if(attempt())obs.disconnect();});obs.observe(doc.body,{childList:true,subtree:true});setTimeout(()=>obs.disconnect(),30000);}
})();
