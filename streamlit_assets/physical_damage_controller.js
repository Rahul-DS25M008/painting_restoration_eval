/* Display-only views over verified D03/D04 artifacts. No metric computation. */
(async () => {
  const host=window.parent, doc=host.document, stage=doc.querySelector('.pd-stage');
  if(!stage)return;
  host.__physicalRoomCleanup?.();
  const data=__PHYSICAL_DATA__, state={mode:'whole',mask:false};
  try { Object.assign(state,JSON.parse(host.sessionStorage.getItem('physical-room-view')||'{}')); } catch (_) {}
  if(!['whole','detail'].includes(state.mode))state.mode='whole';
  let alive=true, dialog=null, restoreFocus=null;
  const abort=new AbortController();let frameObserver;
  host.__physicalRoomCleanup=()=>{alive=false;abort.abort();frameObserver?.disconnect();dialog?.remove();};
  function node(tag,text,cls){const n=doc.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n;}
  function para(parent,text,cls){const p=node('p',text,cls);parent.append(p);return p;}
  function heading(parent,text){parent.append(node('h3',text));}
  function external(parent,label,url){try{const u=new URL(url);if(!['http:','https:'].includes(u.protocol))return;const a=node('a',label);a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';parent.append(a);}catch(_) {}}
  function table(parent,headers,rows){const scroll=node('div',undefined,'pd-scroll'),t=node('table'),head=node('thead'),tr=node('tr');headers.forEach(h=>tr.append(node('th',h)));head.append(tr);t.append(head);const body=node('tbody');rows.forEach(values=>{const r=node('tr');values.forEach(v=>r.append(node('td',v??'\u2014')));body.append(r);});t.append(body);scroll.append(t);parent.append(scroll);}
  function number(value,digits=4){return value!=='' && value!==undefined && Number.isFinite(Number(value))?Number(value).toFixed(digits):'\u2014';}
  function remember(){try{host.sessionStorage.setItem('physical-room-view',JSON.stringify(state));}catch(_) {}}
  const imageCache=new Map();
  function load(uri){if(!imageCache.has(uri))imageCache.set(uri,new Promise((resolve,reject)=>{const image=new host.Image();image.onload=()=>resolve(image);image.onerror=()=>reject(Error('A saved evidence image could not be loaded.'));image.src=uri;}));return imageCache.get(uri);}
  function crop(){return state.mode==='detail'?data.detail:data.content;}
  let overlay;
  function draw(canvas,image,bounds,showMask=false){const [x,y,x1,y1]=bounds,w=x1-x,h=y1-y;canvas.width=w;canvas.height=h;const ctx=canvas.getContext('2d');ctx.drawImage(image,x,y,w,h,0,0,w,h);if(showMask&&overlay)ctx.drawImage(overlay,x,y,w,h,0,0,w,h);}
  function action(parent,label,fn){const button=node('button',label);button.type='button';button.addEventListener('click',fn,{signal:abort.signal});parent.append(button);return button;}
  function close(){if(data.panel){const a=node('a');a.href=data.links.close;doc.body.append(a);a.click();a.remove();}else{dialog?.close();dialog?.remove();dialog=null;restoreFocus?.focus();}}
  function open(title,fromServer=false){dialog?.remove();restoreFocus=doc.activeElement;dialog=node('dialog',undefined,'pd-dialog');dialog.setAttribute('aria-label',title);const header=node('header');header.append(node('h2',title));const closeButton=node('button','\u00d7','pd-close');closeButton.type='button';closeButton.setAttribute('aria-label','Close inspection');closeButton.addEventListener('click',close);header.append(closeButton);const body=node('div',undefined,'pd-body');dialog.append(header,body);doc.body.append(dialog);dialog.addEventListener('cancel',e=>{e.preventDefault();close();});dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)close();}});dialog.showModal();if(fromServer){const nav=node('nav');nav.setAttribute('aria-label','Evidence panels');for(const [key,label] of Object.entries({evidence:'Observations & diagnostics',seeds:'Four seeds',comparison:'Controlled comparison',sources:'Sources & settings',report:'Full report'})){const a=node('a',label);a.href=data.links[key];if(data.panel===key)a.setAttribute('aria-current','page');nav.append(a);}body.append(nav);}return body;}
  const images=await Promise.all(data.images.map(r=>load(r.uri))).catch(e=>{stage.querySelector('.pd-table-note').textContent=e.message;return null;});
  if(!images||!alive)return;
  try {const mask=await load(data.mask);overlay=node('canvas');overlay.width=mask.naturalWidth;overlay.height=mask.naturalHeight;const context=overlay.getContext('2d');context.drawImage(mask,0,0);const pixels=context.getImageData(0,0,overlay.width,overlay.height);for(let i=0;i<pixels.data.length;i+=4){const selected=pixels.data[i]>=128;pixels.data[i]=241;pixels.data[i+1]=174;pixels.data[i+2]=53;pixels.data[i+3]=selected?130:0;}context.putImageData(pixels,0,0);}catch(e){stage.querySelector('[data-mask]').disabled=true;}
  function paint(){stage.querySelectorAll('[data-print]').forEach(c=>draw(c,images[Number(c.dataset.print)],crop(),state.mask));stage.querySelectorAll('[data-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mode===state.mode)));stage.querySelector('[data-mask]').setAttribute('aria-pressed',String(state.mask));stage.querySelector('[data-mask]').textContent=state.mask?'Hide mask':'Show mask';stage.querySelector('.pd-table-note').textContent=state.mode==='detail'?'Same saved display crop across all five images \u00b7 not a metric region \u00b7 click to enlarge':'Click an image to inspect \u00b7 selected repair targets only \u00b7 SD primary seed 2026';remember();}
  paint();
  stage.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>{state.mode=b.dataset.mode;paint();},{signal:abort.signal}));
  stage.querySelector('[data-mask]').addEventListener('click',()=>{state.mask=!state.mask;paint();},{signal:abort.signal});
  await Promise.all(data.collection.map(async item=>{const img=await load(item.uri);if(alive)draw(stage.querySelector(`[data-exhibit="${item.id}"]`),img,item.content);}));
  if(!alive)return;
  // Map each whole-painting selector to its four inner frame corners. The
  // scientific table and enlarged views use draw() without this projection.
  function fitFrames(){stage.querySelectorAll('[data-exhibit]').forEach(canvas=>{
    if(host.matchMedia('(max-width:900px)').matches){canvas.style.transform='none';canvas.dataset.mounted='true';return;}
    const [[x0,y0],[x1,y1],[x2,y2],[x3,y3]]=JSON.parse(canvas.dataset.corners);
    const dx1=x1-x2,dx2=x3-x2,dx3=x0-x1+x2-x3,dy1=y1-y2,dy2=y3-y2,dy3=y0-y1+y2-y3;
    const det=dx1*dy2-dx2*dy1,g=(dx3*dy2-dx2*dy3)/det,h=(dx1*dy3-dx3*dy1)/det;
    const a=x1-x0+g*x1,b=x3-x0+h*x3,d=y1-y0+g*y1,e=y3-y0+h*y3;
    const {width:w,height:v}=canvas.parentElement.getBoundingClientRect();
    canvas.style.transform=`matrix3d(${[a,d*v/w,0,g/w,b*w/v,e,0,h/v,0,0,1,0,x0*w,y0*v,0,1].join(',')})`;
    canvas.dataset.mounted='true';
  });}
  fitFrames();frameObserver=new host.ResizeObserver(fitFrames);frameObserver.observe(stage);
  stage.dataset.ready='true';
  stage.querySelectorAll('[data-image]').forEach(button=>button.addEventListener('click',()=>{
    const initial=Number(button.dataset.image),body=open(`${data.case} \u00b7 ${data.artwork.title}`),tools=node('div',undefined,'pd-modal-tools');body.append(tools);
    const title=node('h3',data.images[initial].label),canvas=node('canvas',undefined,'pd-enlarged');body.append(title,canvas);let selected=initial;
    const update=()=>{title.textContent=data.images[selected].label;canvas.setAttribute('aria-label',`${title.textContent}, ${state.mode==='detail'?'saved detail crop':'full painting'}`);draw(canvas,images[selected],crop(),state.mask);paint();};
    data.images.forEach((item,i)=>action(tools,item.label,()=>{selected=i;update();}));
    const regionTools=node('div',undefined,'pd-modal-tools');body.append(regionTools);action(regionTools,'Full painting',()=>{state.mode='whole';update();});action(regionTools,'Same detail',()=>{state.mode='detail';update();});action(regionTools,'Toggle mask',()=>{state.mask=!state.mask;update();});update();
    para(body,`Repair mask: ${number(data.mask_fraction*100,2)}% of image content. ${data.mask_note}`);
    para(body,'The full painting view omits preprocessing padding only. The detail view is the saved largest-component crop with a 32-pixel margin; it is not an evaluation region. These are possible completions, not known original content.','pd-note');
  },{signal:abort.signal}));
  if(!data.panel)return;
  const titles={evidence:'Observations & diagnostics',seeds:'Four Stable Diffusion seeds',comparison:'Physical and controlled examples',sources:'Sources & settings',report:'D04 \u00b7 Complete study report'};
  const body=open(`${data.case} \u00b7 ${titles[data.panel]}`,true);
  if(data.panel==='evidence'){
    para(body,data.observations[0]?.case_conclusion||'No approved case conclusion recorded.','pd-note');
    para(body,'Saved visual inspection by the assistant, approved by the author with model identities visible. These observations are not an expert survey or a numerical quality ranking.');
    table(body,['Primary method','Inspected region','Saved observation'],data.observations.map(r=>[data.labels[r.model_id],r.inspected_region,r.observation]));
    heading(body,'What changed at the selected repair boundary?');
    para(body,'The gaps below describe transitions between mean colours in inner and outer 3-pixel boundary bands. Neither a small gap nor a large edit proves that the repair is correct. L* is lightness; \u0394E00 is CIEDE2000 colour difference.');
    table(body,['Method','L* gap: input \u2192 repair','\u0394E00 gap: input \u2192 repair','Inside-mask edit (RGB 0\u20131)','Changed outside pixels'],data.diagnostics.map(r=>{const c=data.candidates.find(c=>c.candidate_id===r.candidate_id);return [data.labels[r.model_id],`${number(r.input_boundary_Lstar_gap,2)} \u2192 ${number(r.restored_boundary_Lstar_gap,2)}`,`${number(r.input_boundary_delta_e_gap,2)} \u2192 ${number(r.restored_boundary_delta_e_gap,2)}`,number(r.masked_edit_rgb_mean),c?.changed_outside_pixels];}));
    para(body,`Selected repair mask: ${number(data.mask_fraction*100,2)}% of content. ${data.mask_note}`);
    para(body,'Outside-mask preservation is enforced by compositing and checked in the saved outputs; it is not evidence of historical accuracy. No physical-case MAE, SSIM or LPIPS against a clean reference is available.','pd-note');
  }else if(data.panel==='seeds'){
    para(body,'The prompt and generation settings remain fixed within this painting. Seed 2026 is the primary SD candidate used at the table; the other three were not selected as replacements.');
    const grid=node('div',undefined,'pd-seeds');body.append(grid);
    await Promise.all(data.seeds.map(async r=>{const figure=node('figure'),canvas=node('canvas');figure.append(canvas,node('figcaption',`Seed ${r.seed}${r.seed==='2026'?' \u00b7 primary':''}`));grid.append(figure);draw(canvas,await load(r.uri),data.content);canvas.setAttribute('aria-label',`Stable Diffusion seed ${r.seed}`);}));
    heading(body,'Saved variability evidence');
    const selected=data.uncertainty.filter(r=>(r.metric_name==='pixel_rgb_std_mean'&&['masked_region','outside_mask_content'].includes(r.region_id))||(r.metric_name==='pairwise_lpips_distance'&&r.region_id==='mask_bbox_crop'));
    table(body,['Measurement','Region','Saved value','Unit'],selected.map(r=>[r.metric_name,r.region_id,number(r.value,5),r.value_unit]));
    para(body,'Seed disagreement describes variability, not a probability of correctness. Pairwise LPIPS here compares generated candidates with one another, not with a clean original.','pd-note');
    const fig=node('img');fig.src=data.seed_figure;fig.alt='Saved four-seed variability figure for '+data.case;body.append(fig);
  }else if(data.panel==='comparison'){
    const c=data.comparison,s=data.comparison_sources;
    para(body,`Controlled example: ${c.synthetic_title}. This is a different artwork, selected by category and approximate input damage characteristics\u2014not by restoration scores.`);
    table(body,['Input characteristic','Physical case','Controlled example'],[['Selected damage coverage',number(Number(c.real_damage_fraction)*100,2)+'%',number(Number(c.synthetic_damage_fraction)*100,2)+'%'],['Mask components',c.real_component_count,c.synthetic_component_count],['Damage type','Observed physical losses',c.synthetic_mask_type]]);
    para(body,c.mismatch_note);
    para(body,'Physical SD uses a painting-specific targeted prompt; the controlled example retains its saved prompt and settings. Differences cannot be attributed to physical versus synthetic damage alone. The controlled reference is not a clean reference for the physical painting.','pd-note');
    data.comparison_images.forEach((uri,i)=>{const fig=node('figure'),img=node('img');img.src=uri;img.alt=i?'Saved matched display crops, physical and controlled artworks':'Saved full physical and controlled comparison panel';fig.append(img,node('figcaption',i?'Saved detail panel. Display crops are not metric regions.':'Saved D04 comparison panel, with the controlled clean reference labelled separately.'));body.append(fig);});
    heading(body,'Reference metrics \u2014 controlled example only');
    table(body,['Method','Masked MAE \u2193','Crop LPIPS \u2193','Crop SSIM \u2191'],data.comparison_metrics.map(r=>[data.labels[r.model_id],number(r.synthetic_masked_mae,3),number(r.synthetic_crop_lpips,5),number(r.synthetic_crop_ssim,5)]));
    para(body,`${s.physical_title} \u00b7 ${s.physical_credit} \u00b7 ${s.physical_license}`);external(body,'Physical artwork source',s.physical_source_url);
    para(body,`${s.synthetic_title} \u00b7 ${s.synthetic_license}`);external(body,'Controlled artwork source',s.synthetic_source_url);
  }else if(data.panel==='sources'){
    const a=data.artwork;
    heading(body,a.title);table(body,['Source record','Value'],['artist','date_or_period','category','source_credit','source_photographer','license','rights_basis','derivative_notice','damage_observation','annotation_cautions'].filter(k=>a[k]).map(k=>[k==='date_or_period'?'Source date / period (may be photograph date)':k.replaceAll('_',' '),a[k]]));
    const links=node('p');external(links,'Artwork / photograph source',a.source_url);links.append(doc.createTextNode(' \u00b7 '));external(links,'Licence',a.license_url);body.append(links);
    para(body,`Case: ${data.case_id}. Mask covers selected repair targets, not every visible defect.`);
    const sd=data.candidates.find(r=>r.model_id==='stable_diffusion_inpainting');heading(body,'Recorded targeted SD prompt');para(body,sd.prompt);heading(body,'Negative prompt');para(body,sd.negative_prompt||'None recorded.');
    table(body,['Method','Primary seed','Inference size','Compositing'],data.candidates.map(r=>[data.labels[r.model_id],r.model_id==='stable_diffusion_inpainting'?r.seed:'Not stochastic',`${r.inference_width||r.width} \u00d7 ${r.inference_height||r.height}`,r.compositing_policy||'See outside-mask preservation check']));
    data.candidates.forEach(r=>{const details=node('details');details.append(node('summary',data.labels[r.model_id]+' \u00b7 reproducibility record'));const fields=['candidate_id','configuration_id','model_config_path','model_config_sha256','checkpoint_sha256','model_artifact_sha256','repository_revision','hf_model_id','model_revision','precision','device','num_inference_steps','guidance_scale','strength','scheduler','inpaint_radius','prompt_policy_id','prompt_sha256','input_image_path','input_image_sha256','mask_path','mask_sha256','restored_path','restored_sha256'];table(details,['Setting','Recorded value'],fields.filter(k=>r[k]).map(k=>[k,r[k]]));body.append(details);});
    para(body,'All displayed producer files are verified against the completed D03/D04 artifact manifests. This supplementary room does not alter the Controlled-300 population.');
  }else if(data.panel==='report'){
    para(body,'The complete saved D04 report covers all ten paintings, the four primary methods, seed variability, controlled examples and the final completion checks.');
    const download=node('a','Download the saved HTML report');download.href=data.report_uri;download.download='D04_real_damage_evaluation.html';body.append(download);
    const frame=node('iframe');frame.title='Complete D04 physical-damage evaluation report';frame.setAttribute('sandbox','allow-scripts allow-downloads');frame.src=data.report_uri;body.append(frame);
  }
})().catch(error=>{const stage=window.parent.document.querySelector('.pd-stage');if(stage){const note=stage.querySelector('.pd-table-note');if(note)note.textContent='Evidence view unavailable: '+error.message;}console.error(error);});
