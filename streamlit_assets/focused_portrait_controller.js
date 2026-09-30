/* D02 presentation only: immutable source records and deterministic pixel views. */
function portraitPlotGeometry(rows, field) {
  if (!rows.length || rows.some(r=>![r[field],r.interval_low,r.interval_high].every(Number.isFinite))) throw Error('Missing interval evidence');
  const lo=Math.min(0,...rows.map(r=>r.interval_low)), hi=Math.max(0,...rows.map(r=>r.interval_high));
  const pad=(hi-lo||1)*.09, min=lo-pad, max=hi+pad;
  return {min,max,x:v=>124+(v-min)/(max-min)*226};
}
function portraitDifference(clean, restored) {
  if(clean.length!==restored.length || clean.length%4) throw Error('Different image dimensions');
  const result=new Uint8ClampedArray(clean.length);
  for(let i=0;i<result.length;i+=4){for(let k=0;k<3;k++)result[i+k]=Math.abs(clean[i+k]-restored[i+k]);result[i+3]=255;}
  return result;
}
function portraitObservation(review, category) {
  const themes={
    digits:{title:'Digits',fields:['digit_count_error','missing_digits','duplicated_digits','fused_digits'],question:'Were digit count, separation, or presence problems recorded?'},
    contour:{title:'Contour',fields:['contour_failure'],question:'Was a malformed hand outline recorded?'},
    wrist:{title:'Wrist',fields:['wrist_or_arm_discontinuity'],question:'Was a wrist or arm discontinuity recorded?'},
    texture:{title:'Texture',fields:['non_anatomical_texture'],question:'Was non-anatomical texture recorded inside the reviewed anatomy?'}
  };
  const theme=themes[category];if(!theme)throw Error('Unknown observation category');
  const rows=theme.fields.map(key=>({key,value:review[key]??null}));
  const present=rows.some(r=>r.value===true||(typeof r.value==='number'&&r.value>0));
  const complete=rows.every(r=>typeof r.value==='boolean'||typeof r.value==='number');
  return {...theme,rows,state:present?'recorded':complete?'not-recorded':'unavailable'};
}
function portraitNextReview(catalogue, code, failure) {
  const current=catalogue.find(r=>r.blind_review_code===code);
  if(!current)throw Error('Unknown current review');
  const choices=catalogue.filter(r=>r.overall_anatomy_failure===failure&&r.blind_review_code!==code);
  if(!choices.length)return null;
  const index=catalogue.indexOf(current),ordered=[...catalogue.slice(index+1),...catalogue.slice(0,index)];
  const matches=ordered.filter(r=>choices.includes(r));
  return matches.find(r=>r.painting_id!==current.painting_id)||matches[0];
}
function portraitLightnessSummary(rows, metric) {
  const selected=rows.filter(r=>r.metric_name===metric);
  if(!selected.length||selected.some(r=>![r.interval_low,r.interval_high].every(Number.isFinite)||r.interval_low>r.interval_high))throw Error('Missing lightness intervals');
  const negative=selected.filter(r=>r.interval_high<0).length,positive=selected.filter(r=>r.interval_low>0).length,total=selected.length,uncertain=total-negative-positive;
  const reading=uncertain===total?`No clear association in ${total}/${total} methods.`:negative&&positive?'Association directions differ by method.':negative?`Negative association in ${negative}/${total} methods.`:`Positive association in ${positive}/${total} methods.`;
  return {negative,positive,uncertain,total,reading};
}
if(typeof module!=='undefined') module.exports={portraitPlotGeometry,portraitDifference,portraitObservation,portraitNextReview,portraitLightnessSummary};
if(typeof window!=='undefined') (()=>{
  const data=__PORTRAIT_PAYLOAD__,doc=window.parent.document;
  const metricLabels={mae:'RGB MAE',delta_e_ciede2000_mean:'CIEDE2000',ssim:'SSIM penalty',chroma_error_mean:'Chroma error',lightness_error_mean:'Lightness error',psnr:'PSNR (error-oriented)',rmse:'RGB RMSE'};
  const units={mae:'normalized RGB error',delta_e_ciede2000_mean:'CIEDE2000',ssim:'SSIM loss',chroma_error_mean:'CIELAB chroma error',lightness_error_mean:'CIELAB lightness error',psnr:'oriented dB',rmse:'normalized RGB error'};
  const models=['opencv_telea','lama','hint_places2','stable_diffusion_inpainting'],colors=['#ae7b26','#28746b','#467a9c','#b45c45'];
  function mount(stage){
    if(stage.dataset.controllerReady===data.version)return;
    stage.dataset.controllerReady=data.version;
    const find=s=>stage.querySelector(s),dialog=find('.fpr-dialog'),body=find('.fpr-dialog-body');
    let lastFocus,handMetric='mae',lightMetric='chroma_error_mean';
    const imageCache={};
    const node=(tag,text,cls)=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n;};
    const plain=v=>String(v??'Unavailable').replaceAll('_',' ');
    const fmt=v=>typeof v==='number'?Number(v.toPrecision(6)).toString():plain(v);
    function p(text,cls,parent=body){const n=node('p',text,cls);parent.append(n);return n;}
    function actionRow(){let row=body.lastElementChild;if(!row?.classList.contains('fpr-action-row')){row=node('div',undefined,'fpr-action-row');body.append(row);}return row;}
    function button(label,action,parent=body){const n=node('button',label);n.type='button';n.addEventListener('click',()=>action());(parent===body?actionRow():parent).append(n);return n;}
    function detail(title,value){const n=node('details');n.append(node('summary',title),node('pre',JSON.stringify(value,null,2)));body.append(n);}
    function open(title){if(!dialog.open)lastFocus=doc.activeElement;find('#fpr-dialog-title').textContent=title;body.replaceChildren();find('.fpr-dialog-context').textContent='RECORD '+data.review.blind_review_code+' / '+data.review.painting_id+' · D02 EVIDENCE COLLECTION';if(!dialog.open)dialog.showModal();dialog.scrollTop=0;body.scrollTop=0;}
    function close(){dialog.close();lastFocus?.focus();}
    function table(headers,rows,parent=body){const wrap=node('div',undefined,'fpr-table-wrap'),t=node('table'),thead=node('thead'),head=node('tr'),tbody=node('tbody');headers.forEach(h=>{const th=node('th',h);th.scope='col';head.append(th);});thead.append(head);t.append(thead,tbody);rows.forEach(row=>{const tr=node('tr');row.forEach(v=>{const cell=node('td');if(typeof v==='boolean')cell.append(node('span',v?'Present':'Not recorded','fpr-evidence-tag '+(v?'present':'absent')));else{cell.textContent=fmt(v);if(typeof v==='number')cell.className='fpr-number';}tr.append(cell);});tbody.append(tr);});wrap.append(t);wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label',headers.join(' / ')+' table');parent.append(wrap);}
    function select(label,options,value,change,parent=body){const field=node('label',undefined,'fpr-field'),n=node('select');field.append(node('span',label));n.setAttribute('aria-label',label);for(const [key,title] of options){const o=node('option',title);o.value=key;o.selected=key===value;n.append(o);}n.addEventListener('change',()=>change(n.value));field.append(n);parent.append(field);return n;}
    function download(label,rows,name){if(!rows.length)return;const keys=Object.keys(rows[0]),cell=v=>'"'+String(v??'').replaceAll('"','""')+'"',csv=[keys.map(cell).join(','),...rows.map(r=>keys.map(k=>cell(r[k])).join(','))].join('\r\n');const a=node('a',label,'fpr-download');a.href='data:text/csv;charset=utf-8,'+encodeURIComponent(csv);a.download=name;actionRow().append(a);}
    function provenance(){const footer=node('footer',undefined,'fpr-provenance');footer.append(node('span','RECORD PROVENANCE'),node('p','D02 · '+data.review.blind_review_code+' · '+data.review.review_unit_id+' · '+data.review.candidate_id));body.append(footer);}
    function stats(items){const grid=node('div',undefined,'fpr-stat-grid');for(const [value,label] of items){const card=node('div');card.append(node('strong',value),node('span',label));grid.append(card);}body.append(grid);}
    function print(kind,full,caption){const figure=node('figure',undefined,'fpr-inspection-print'),canvas=node('canvas');figure.append(canvas,node('figcaption',caption));body.append(figure);safePaint(canvas,kind,full);}
    function navigate(code,resource,panel){const url=new URL(window.parent.location.href);url.searchParams.set('room','focused_portrait_review');url.searchParams.set('return_room',data.return_room);url.searchParams.set('portrait_review',code);url.searchParams.delete('portrait_resource');url.searchParams.delete('portrait_panel');if(resource)url.searchParams.set('portrait_resource',resource);if(panel)url.searchParams.set('portrait_panel',panel);const a=node('a');a.href=url.toString();a.target='_self';stage.append(a);find('.fpr-sr').textContent='Loading exact recorded review '+code+'…';a.click();a.remove();}
    function plot(rows,field,metric,large=false){
      rows=[...rows].sort((a,b)=>models.indexOf(a.model_id)-models.indexOf(b.model_id));
      const g=portraitPlotGeometry(rows,field),ns='http://www.w3.org/2000/svg',svg=doc.createElementNS(ns,'svg');
      svg.setAttribute('viewBox','0 0 374 155');svg.setAttribute('role','img');svg.setAttribute('aria-label',metricLabels[metric]+' · recorded estimates with uncertainty intervals');
      function el(tag,attrs,text){const e=doc.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;svg.append(e);return e;}
      el('line',{x1:g.x(0),x2:g.x(0),y1:4,y2:113,stroke:'#776951','stroke-dasharray':'3 3'});
      for(let i=0;i<5;i++){const v=g.min+(g.max-g.min)*i/4,x=g.x(v);el('line',{x1:x,x2:x,y1:113,y2:119,stroke:'#776951'});el('text',{x,y:130,'text-anchor':'middle','font-size':9,fill:'#5e513e'},Math.abs(v)<1e-9?'0':Number(v.toPrecision(3)));}
      rows.forEach((r,i)=>{const y=14+i*27,color=colors[models.indexOf(r.model_id)];el('text',{x:117,y:y+4,'text-anchor':'end','font-size':11,fill:'#332a1f'},data.labels[r.model_id]);el('line',{x1:g.x(r.interval_low),x2:g.x(r.interval_high),y1:y,y2:y,stroke:color,'stroke-width':2});for(const value of [r.interval_low,r.interval_high])el('line',{x1:g.x(value),x2:g.x(value),y1:y-4,y2:y+4,stroke:color});const dot=el('circle',{cx:g.x(r[field]),cy:y,r:4,fill:color});const title=doc.createElementNS(ns,'title');title.textContent=`${data.labels[r.model_id]}: ${r[field]} [${r.interval_low}, ${r.interval_high}]`;dot.append(title);});
      el('line',{x1:124,x2:350,y1:113,y2:113,stroke:'#776951'});el('text',{x:237,y:147,'text-anchor':'middle','font-size':9,fill:'#5e513e'},field==='estimate'?(metric==='ssim'?'Control − hand · SSIM':'Hand − control · '+units[metric]):'Adjusted standardized L* coefficient');return svg;
    }
    function updateCharts(){find('.fpr-hand-chart').replaceChildren(plot(data.hand.filter(r=>r.metric_name===handMetric),'estimate',handMetric));find('.fpr-lightness-chart').replaceChildren(plot(data.light.filter(r=>r.metric_name===lightMetric),'coefficient',lightMetric));const summary=portraitLightnessSummary(data.light,lightMetric);find('.fpr-lightness-reading').textContent=summary.reading;const counts=find('.fpr-lightness-counts');counts.replaceChildren();for(const [i,[label,value,cls]] of [['negative',summary.negative,'negative'],['cross zero',summary.uncertain,'uncertain'],['positive',summary.positive,'positive']].entries()){if(i)counts.append(doc.createTextNode(' · '));counts.append(node('span',value+' '+label,cls));}find('.fpr-lightness-scope').textContent=metricLabels[lightMetric]+' · '+summary.total+' methods';}
    function loadImage(key){if(!imageCache[key])imageCache[key]=new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>resolve(image);image.onerror=()=>reject(Error('Image unavailable: '+key));image.src=data.images[key];});return imageCache[key];}
    function cropFor(kind){return kind==='control'?data.control_crop:data.crop;}
    async function paint(canvas,kind,full=false){
      const originalKind=kind;if(kind==='annotation-mini')kind='annotation';if(kind==='blind-clean')kind='clean';if(kind==='blind-restored')kind='restored';
      const box=full?[0,0,768,768]:cropFor(kind),[x0,y0,x1,y1]=box,w=x1-x0,h=y1-y0;canvas.width=w;canvas.height=h;
      const ctx=canvas.getContext('2d'),key=['control','annotation'].includes(kind)?'clean':kind==='difference'?'clean':kind;
      if(kind==='difference'&&data.registered.d02_r005_difference_crop&&!full){const image=new Image();await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=reject;image.src=data.registered.d02_r005_difference_crop.uri;});ctx.drawImage(image,0,0,w,h);return;}
      const image=await loadImage(key);if(image.naturalWidth!==768||image.naturalHeight!==768)throw Error('Unexpected normalized image dimensions');ctx.drawImage(image,x0,y0,w,h,0,0,w,h);
      if(kind==='difference'){
        const clean=ctx.getImageData(0,0,w,h);ctx.drawImage(await loadImage('restored'),x0,y0,w,h,0,0,w,h);const restored=ctx.getImageData(0,0,w,h);clean.data.set(portraitDifference(clean.data,restored.data));ctx.putImageData(clean,0,0);
      }
      if(kind==='damaged'||kind==='annotation'||kind==='control'){
        const ids=kind==='control'?data.control_indices:data.hand_indices;ctx.fillStyle=kind==='control'?'rgba(205,157,46,.65)':'rgba(182,71,58,.55)';
        ids.forEach(id=>{const x=id%768-x0,y=Math.floor(id/768)-y0;if(x>=0&&x<w&&y>=0&&y<h)ctx.fillRect(x,y,1,1);});
        if(kind!=='control'){ctx.strokeStyle='#56b2a5';ctx.lineWidth=full?2:1.2;ctx.beginPath();data.polygon.forEach(([x,y],i)=>i?ctx.lineTo(x-x0,y-y0):ctx.moveTo(x-x0,y-y0));ctx.closePath();ctx.stroke();}
      }
      if(full&&!['difference','control'].includes(kind)){ctx.strokeStyle='#e0b53d';ctx.lineWidth=2;ctx.strokeRect(data.crop[0],data.crop[1],data.crop[2]-data.crop[0],data.crop[3]-data.crop[1]);}
      canvas.setAttribute('aria-label',originalKind+' · '+data.review.blind_review_code+(full?' · full normalized canvas':' · recorded crop'));
    }
    function safePaint(canvas,kind,full=false){paint(canvas,kind,full).catch(error=>{canvas.replaceWith(node('p',error.message,'fpr-status-error'));});}
    function imageDrawer(kind,full=false){const titles={clean:'Clean reference',damaged:'Damage & anatomical overlap',restored:'Restored painting',difference:'Absolute RGB difference',control:'Matched non-hand control',mask:'Binary damage mask',annotation:'Anatomical annotation'};open((titles[kind]||plain(kind))+' · '+data.review.blind_review_code);p(data.title+' · '+data.labels[data.review.model_id]);
      if(kind==='damaged'||kind==='annotation')p('Teal outline: reviewed anatomical annotation. Red tint: damaged pixels inside that annotation. The damage mask is separate from the anatomy annotation.','fpr-boundary');
      if(kind==='control')p(`Gold marks the original ${data.control.control_pixel_count.toLocaleString()} matched non-hand pixels. The crop gives context; only those sparse pixels form the control. No convenient substitute was chosen.`,'fpr-boundary');
      if(kind==='difference')p('Absolute per-channel RGB difference |clean − restored|, without contrast normalization. Black means identical pixels. This is not an anatomy judgement. '+(data.review.blind_review_code==='R005'?'The crop is the registered N34 rendition.':'This browser preview is calculated from the verified source bytes; it is not a new saved scientific artifact.'),'fpr-boundary');
      print(kind,full,plain(kind)+' / '+(full?'Full normalized canvas':'Recorded crop')+' / '+data.review.blind_review_code);button(full?'Show recorded crop':'Show full normalized canvas',()=>imageDrawer(kind,!full));if(kind==='damaged')button('Inspect complete binary damage mask',()=>imageDrawer('mask',full));button('Read blind review',reviewDrawer);detail('Exact image paths and crop',{crop:cropFor(kind),clean:data.review.clean_image_path,damaged:data.review.damaged_image_path,restored:data.review.restored_path,mask:data.review.mask_path,registered:data.registered.d02_r005_difference_crop?.asset_id});provenance();}
    function formation(){open('How the study was formed');const s=data.scope;stats([[s.screened,'portraits screened'],[s.hand_cases,'matched hand cases'],[s.reviews,'blind review units']]);table(['Stage','Recorded count'],[['Portraits screened',s.screened],['Included / excluded',s.included+' / '+s.excluded],['Reviewed / retained annotations',s.annotations+' / '+s.retained],['Anatomy–damage intersections',s.intersections],['Eligible records',s.eligible],['Matched hand cases / independent paintings',s.hand_cases+' / '+s.hand_paintings],['Blind review units / cases / methods',s.reviews+' / '+s.review_cases+' / 4']]);p('Annotations were reviewed before the outcome-gated analysis. The independent inferential unit is the painting, not each pixel or candidate.');p('This selected, controlled portrait audit is separate from automated N27 flagging. It does not establish conservation correctness.','fpr-boundary');button('Eligibility and matched control',eligibility);}
    function eligibility(){open('Why this hand case counts');const o=data.overlap,c=data.control;table(['Recorded measure','Value'],[['Damaged hand pixels',o.damaged_anatomical_pixels],['Anatomical pixels',o.anatomical_pixel_count],['Fraction affected',o.anatomical_fraction_affected],['Matched control pixels',c.control_pixel_count],['Hand/control overlap',c.hand_control_overlap_pixels],['Feature match score',c.feature_match_score]]);p('Eligibility requires at least 256 damaged anatomical pixels and 5% affected anatomy, with a viable same-case non-hand control of at least 256 damaged pixels.');button('Inspect annotation and overlap',()=>imageDrawer('annotation'));button('Inspect exact matched control',()=>imageDrawer('control'));detail('Original matched design (retained report CSV)',c);detail('Source overlap row',o);provenance();}
    function handDrawer(){open('Hand penalty · matched within-case evidence');p('Damaged hands were harder to restore in this audit. All 12 primary estimates are worse-oriented positive; 10 meet the BH-corrected significance rule. No single method minimized all three penalties.','fpr-boundary');select('Detailed hand metric',['mae','delta_e_ciede2000_mean','ssim'].map(k=>[k,metricLabels[k]]),handMetric,k=>{handMetric=k;find('[aria-label="Hand penalty metric"]').value=k;updateCharts();handDrawer();});const rows=data.hand.filter(r=>r.metric_name===handMetric);body.append(plot(rows,'estimate',handMetric,true));p('Positive means worse for damaged hands relative to matched controls. SSIM is oriented as control − hand; error metrics are hand − control. Intervals are painting-cluster bootstrap intervals, not per-pixel confidence.');table(['Method','Estimate','Lower','Upper','BH q'],rows.map(r=>[data.labels[r.model_id],r.estimate,r.interval_low,r.interval_high,r.q_value]));p('45 matched cases from 20 independent paintings. Model labels identify the estimates; this is not a leaderboard.');detail('Full-precision registered summary rows',rows);download('Download hand summary',data.hand,'d02_hand_summary.csv');}
    function lightness(){open('Rendered lightness · exploratory context');p('No consistent overall association across 24 model–metric analyses: zero clearly positive, three negative chroma-error associations, and 21 intervals crossing zero. Rendered L* is not race, ethnicity, or identity.','fpr-boundary');select('Detailed lightness metric',Object.keys(metricLabels).filter(k=>k!=='ssim').map(k=>[k,metricLabels[k]]),lightMetric,k=>{lightMetric=k;find('[aria-label="Rendered lightness metric"]').value=k;updateCharts();lightness();});const rows=data.light.filter(r=>r.metric_name===lightMetric);body.append(plot(rows,'coefficient',lightMetric,true));p('Positive coefficients mean error-oriented restoration error rises with rendered lightness. Negative means it falls. Adjustments: damaged skin fraction, median chroma, and local lightness contrast. PSNR is error-oriented, not raw higher-is-better PSNR.');table(['Method','Coefficient','Lower','Upper','Recorded state'],rows.map(r=>[data.labels[r.model_id],r.coefficient,r.interval_low,r.interval_high,r.association_state]));button('Inspect 30 profiles and 10 context matches',contextDrawer);detail('Full-precision adjusted rows',rows);download('Download lightness summary',data.light,'d02_lightness_summary.csv');}
    function contextDrawer(pid=data.profiles[0].painting_id){open('Rendered lightness · profiles and matched context');select('Rendered-lightness painting profile',data.profiles.map(r=>[r.painting_id,r.painting_id+' · '+r.title]),pid,contextDrawer);const r=data.profiles.find(r=>r.painting_id===pid);p('Declared rendered-lightness grouping: '+plain(r.rendered_lightness_bin),'fpr-boundary');table(['Image-context measure','Recorded value'],[['Median clean-region L*',r.median_clean_region_lstar],['Median chroma',r.median_clean_region_chroma],['Local L* contrast',r.clean_region_lstar_contrast],['Annotated pixels',r.annotated_skin_pixel_count],['Eligible skin cases',r.eligible_skin_case_count],['Source',r.source],['Medium',r.medium],['Style / period',r.style_or_period]]);const matches=data.matches.filter(m=>m.lower_painting_id===pid||m.higher_painting_id===pid);p(matches.length?'Recorded context matches for this painting:':'No retained context match for this painting; no partner is substituted.');table(['Lower L* painting','Higher L* painting','L* separation','Match cost','Source / medium / style match'],matches.map(m=>[m.lower_painting_id,m.higher_painting_id,m.lstar_separation,m.match_cost,[m.source_match,m.medium_match,m.style_match].join(' / ')]));p('30 profiles and 10 context matches in total. These groups describe rendered image measurements, not demographic categories.','fpr-boundary');detail('Original profile',r);download('Download 30 profiles',data.profiles,'d02_skin_profiles.csv');download('Download 10 context matches',data.matches,'d02_skin_context_matches.csv');}
    function reviewDrawer(){
      open('Blind visual review · '+data.review.blind_review_code);const r=data.review;
      p((r.overall_anatomy_failure?'Visible anatomy failure':'Acceptable counterexample')+' · '+r.reviewer_confidence+' confidence','fpr-boundary');
      p(r.painting_id+' · '+data.title+' · '+data.labels[r.model_id]+' · '+plain(r.damage_family));
      p(r.review_notes,'fpr-review-note');const pair=node('div',undefined,'fpr-image-pair');
      for(const kind of ['clean','restored']){const figure=node('figure'),c=node('canvas');figure.append(c,node('figcaption',plain(kind)+' · recorded crop'));pair.append(figure);safePaint(c,kind);}body.append(pair);
      table(['Observation','Recorded outcome'],['digit_count_error','missing_digits','duplicated_digits','fused_digits','contour_failure','articulation_failure','wrist_or_arm_discontinuity','non_anatomical_texture'].map(k=>[plain(k),r[k]]));
      p('25 of 32 review units showed a visible anatomy failure. Eight cases, four methods, model names hidden during the bounded Codex-assisted review. These judgements are not expert/conservator ground truth.');
      button('Visible failure',()=>cycle(true));button('Acceptable counterexample',()=>cycle(false));detail('Original unblinded review row',r);provenance();
    }
    function observationDrawer(category){
      const focus=portraitObservation(data.review,category);open(focus.title+' observations · '+data.review.blind_review_code);
      const tabs=node('div',undefined,'fpr-observation-tabs');body.append(tabs);for(const key of ['digits','contour','wrist','texture']){const b=button(plain(key),()=>observationDrawer(key),tabs);b.setAttribute('aria-pressed',String(key===category));}
      p(focus.question);
      p(focus.state==='recorded'?focus.title+' issue recorded':focus.state==='not-recorded'?'No '+category+' issue recorded':'Observation unavailable','fpr-boundary fpr-observation-result '+focus.state);
      table(['Selected observation','Recorded outcome'],focus.rows.map(r=>[plain(r.key),r.value===true?'Present':r.value===false?'Not recorded':r.value===null?'Unavailable':r.value]));
      p('The source records these findings for the shared hand crop; it does not provide separate '+category+' boxes or masks. No feature-specific highlight has been invented.','fpr-boundary');
      const pair=node('div',undefined,'fpr-image-pair');for(const kind of ['clean','restored']){const figure=node('figure'),c=node('canvas');figure.append(c,node('figcaption',plain(kind)+' · shared recorded hand crop'));pair.append(figure);safePaint(c,kind);}body.append(pair);
      p('Whole-review note (not a feature-specific explanation): '+data.review.review_notes);
      button('Open all recorded observations',reviewDrawer);provenance();
    }
    function cycle(failure){const next=portraitNextReview(data.catalogue,data.review.blind_review_code,failure);if(!next){open('No additional matching review');p('No different recorded example is available in this group.');return;}navigate(next.blind_review_code,undefined,'review');}
    function selection(pid=data.review.painting_id,model=data.review.model_id){open('Select a recorded portrait review');p('32 reviewed candidates across eight cases and four methods. Selectors are restricted to this study; no unrelated restoration or seed is substituted.');select('Reviewed painting',[['all','All reviewed portraits'],...[...new Set(data.catalogue.map(r=>r.painting_id))].map(k=>[k,k])],pid,k=>selection(k,model));select('Reviewed method',[['all','All four methods'],...models.map(k=>[k,data.labels[k]])],model,k=>selection(pid,k));const list=node('div',undefined,'fpr-record-list');body.append(list);for(const r of data.catalogue.filter(r=>(pid==='all'||r.painting_id===pid)&&(model==='all'||r.model_id===model))){button(`${r.blind_review_code} · ${r.painting_id} · ${data.labels[r.model_id]} · ${plain(r.damage_family)}`,()=>navigate(r.blind_review_code),list);} }
    function annotations(){open('Reviewed annotation · '+plain(data.review.region_type));p('The anatomy polygon was reviewed independently of the damage mask. Teal is the polygon; red marks its damaged pixel intersection.','fpr-boundary');print('annotation',true,'Reviewed anatomy / Full normalized canvas / '+data.review.blind_review_code);detail('Original anatomical annotation',data.annotation);button('Eligibility and matched control',eligibility);download('Download selected annotation',[data.annotation],'d02_selected_annotation.csv');provenance();}
    function tables(){open('Tables · selected paired evidence');p('Values below belong to the selected candidate and exact matched-control ID. No new statistics were computed.');table(['Metric','Hand','Control','Worse-oriented difference','Support'],data.metrics.map(r=>[r.metric_name,r.hand_value,r.control_value,r.hand_worse_oriented_difference,r.spatial_support]));download('Download selected paired rows',data.metrics,'d02_selected_hand_rows.csv');download('Download all 32 review records',data.catalogue,'d02_manual_reviews.csv');download('Download hand summary',data.hand,'d02_hand_summary.csv');download('Download lightness summary',data.light,'d02_lightness_summary.csv');detail('Full selected paired records',data.metrics);provenance();}
    function methods(){
      open('Methods & limits');p('A focused, outcome-gated D02 study—not an automated N27 flag family. Rendered lightness is an image property, not race, ethnicity, or identity. No inherent model-bias claim is justified.','fpr-boundary');
      const grid=node('div',undefined,'fpr-method-grid');
      for(const [title,text] of [
        ['01 / Matched hand evidence','Same-case matched non-hand controls, painting as independent unit, painting-cluster bootstrap intervals and Benjamini–Hochberg correction. Stable Diffusion seeds are collapsed before painting-level inference; SDXL remains descriptive, outside the four-method primary estimates.'],
        ['02 / Rendered lightness','30 profiles, 10 context matches, six metrics × four models. Adjusted associations retain image-context covariates and uncertainty. They do not establish demographic fairness or historical correctness.'],
        ['03 / Blind visual review','32 units from eight cases, model identities hidden during a bounded Codex-assisted review. This is not independent expert validation.'],
        ['04 / Reading the prints','The five prints use recorded crop coordinates. Inspect any print for full-canvas context. Difference views are absolute RGB differences, not a diagnostic verdict. Sparse control pixels, not the entire crop, define the comparison.']
      ]){const section=node('section');section.append(node('h3',title));p(text,undefined,section);grid.append(section);}body.append(grid);
      detail('Runtime provenance',{source:data.source,release:data.release_id,review_unit_id:data.review.review_unit_id,hand_control_id:data.review.hand_control_id});button('Open original D02 report',()=>navigate(data.review.blind_review_code,'report'));
    }
    const actions={close,formation,eligibility,hand:handDrawer,lightness,review:reviewDrawer,select:selection,annotation:annotations,tables,methods,report:()=>navigate(data.review.blind_review_code,'report'),failure:()=>cycle(true),counterexample:()=>cycle(false),previous:()=>step(-1),next:()=>step(1)};
    function step(delta){const i=data.catalogue.findIndex(r=>r.blind_review_code===data.review.blind_review_code);navigate(data.catalogue[(i+delta+data.catalogue.length)%data.catalogue.length].blind_review_code);}
    stage.addEventListener('click',event=>{const target=event.target.closest('[data-action]');if(!target)return;const action=target.dataset.action;if(action.startsWith('image:'))imageDrawer(action.slice(6));else if(action.startsWith('observation:'))observationDrawer(action.slice(12));else if(actions[action])actions[action]();});
    dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
    find('[aria-label="Hand penalty metric"]').addEventListener('change',event=>{handMetric=event.target.value;updateCharts();});
    find('[aria-label="Rendered lightness metric"]').addEventListener('change',event=>{lightMetric=event.target.value;updateCharts();});
    updateCharts();stage.querySelectorAll('canvas[data-canvas]').forEach(c=>safePaint(c,c.dataset.canvas));
    find('.fpr-sr').textContent='Loaded '+data.review.blind_review_code+' with exact D02 evidence.';
    if(new URL(window.parent.location.href).searchParams.get('portrait_panel')==='review')reviewDrawer();
  }
  function attempt(){const stage=doc.querySelector('.fpr-stage');if(stage&&stage.dataset.version===data.version){mount(stage);return true;}return false;}
  if(!attempt()){const observer=new MutationObserver(()=>{if(attempt())observer.disconnect();});observer.observe(doc.body,{childList:true,subtree:true});setTimeout(()=>observer.disconnect(),20000);}
})();
