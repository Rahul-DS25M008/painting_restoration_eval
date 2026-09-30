/* Coordinate-preserving conservation loupe. No network navigation or metric inference. */
(() => {
  const payload = __METRIC_PAYLOAD__;
  const doc = window.parent.document;
  const storageKey = 'museum.metric.inspection.v1';
  function mount(stage) {
    if (stage.dataset.controllerReady === payload.version) return;
    const abort = new AbortController();
    const on = (node, event, fn) => node.addEventListener(event, fn, {signal:abort.signal});
    const painting = stage.querySelector('.metric-painting');
    const base = painting.querySelector(':scope > img');
    const loupe = stage.querySelector('.metric-lens-live');
    const canvas = loupe.querySelector('canvas');
    const plaque = stage.querySelector('.metric-plaque');
    const readout = stage.querySelector('.metric-loupe-readout');
    const note = stage.querySelector('.metric-selection-notice');
    const patchOutline=doc.createElement('div');
    patchOutline.className='metric-patch-outline';patchOutline.hidden=true;
    patchOutline.setAttribute('aria-hidden','true');painting.append(patchOutline);
    let saved = {};
    try { saved = JSON.parse(sessionStorage.getItem(storageKey) || '{}'); } catch (_) {}
    let state = {lens: saved.lens || 'spatial', region: saved.region === null ? null : (saved.region || 'damaged'), view: saved.view || 'restored'};
    if (!payload.lenses[state.lens]) state.lens='spatial';
    if (!payload.views[state.view]) state.view='restored';
    if (state.region && !payload.pairs[`${state.lens}:${state.region}`]?.allowed) state.region=null;
    let x=.5,y=.5, generation=0, active=null, rendered=null, currentPatch=-1;
    const loaded = new Map();
    function load(uri) {
      if (!loaded.has(uri)) loaded.set(uri,new Promise((resolve,reject)=> {
        const img=new Image(); img.onload=()=>resolve(img); img.onerror=()=>{loaded.delete(uri);reject(new Error('Image could not be decoded'));}; img.src=uri;
      }));
      return loaded.get(uri);
    }
    function persist(){try{sessionStorage.setItem(storageKey,JSON.stringify(state));}catch(_){} }
    function textNode(tag,text,cls='') { const e=doc.createElement(tag);e.textContent=text;e.className=cls;return e; }
    function directionNode(text) {
      const p=doc.createElement('p');
      // Colour the named cue only, not its explanation or arbitrary page text.
      text.split(/\b(blue|red|pale|dark|bright)\b/gi).forEach((part,i)=>{
        p.append(i%2 ? textNode('span',part,`tone-${part.toLowerCase()}`) : doc.createTextNode(part));
      });
      return p;
    }
    function plaqueFor(spec) {
      plaque.replaceChildren();
      Object.assign(plaque.dataset,{lens:state.lens,metric:spec.metric,region:state.region,policyRole:spec.role,evidenceKey:stage.dataset.evidenceKey});
      plaque.append(textNode('h3',spec.metric),textNode('p',`${spec.region_label} · ${spec.role}`),directionNode(spec.direction),textNode('p',spec.limitation,'quiet'));
      const details=doc.createElement('details');
      details.append(textNode('summary','Measurements & support'),readout,textNode('p',spec.calculation));
      const labels=spec.split ? (state.lens==='features'?['CLIP','DINO']:['DINO','Affinity']) : ['Mean'];
      details.append(textNode('p',spec.summary.map((s,i)=>`${labels[i]}: ${s.mean.toFixed(4)}`).join(' · ')));
      details.append(textNode('p',`Fixed scale ${spec.scale.map(s=>s.join(' to ')).join(' / ')} · ${spec.units}`,'quiet'));
      details.append(textNode('p','Hatched: outside support / not evaluated','quiet'));
      plaque.append(details);plaque.scrollTop=0;
      if(spec.pixel_metrics) plaque.title=`MAE ${spec.pixel_metrics.mae}; MSE ${spec.pixel_metrics.mse}; PSNR ${spec.pixel_metrics.psnr===null?'∞':spec.pixel_metrics.psnr.toFixed(2)+' dB'}. The loupe displays RGB error, not a PSNR heatmap.`;
      else plaque.title=spec.limitation;
    }
    function updateButtons() {
      stage.dataset.metricLens=state.lens;stage.dataset.metricRegion=state.region||'';stage.dataset.baseView=state.view;
      stage.querySelectorAll('.metric-lens').forEach(row=>{const yes=row.dataset.lens===state.lens;row.classList.toggle('active',yes);row.querySelector('button').setAttribute('aria-expanded',String(yes));});
      stage.querySelectorAll('.metric-region').forEach(b=>{
        const spec=payload.pairs[`${state.lens}:${b.dataset.region}`];
        b.disabled=!spec.allowed;b.setAttribute('aria-disabled',String(!spec.allowed));
        b.dataset.role=spec.role;b.dataset.policyRole=spec.role;b.dataset.canonicalRegion=spec.canonical_region;
        const yes=state.region===b.dataset.region;b.classList.toggle('active',yes);b.setAttribute('aria-pressed',String(yes));
        b.classList.toggle('recommended',!state.region&&b.dataset.region===spec.recommended);
        b.title=spec.allowed?`${spec.region_label}: ${spec.role} — ${spec.metric}`:spec.reason;
        const reason=stage.querySelector(`#metric-reason-${b.dataset.region}`);reason.textContent=spec.reason;
        b.setAttribute('aria-describedby',reason.id);
      });
      stage.querySelectorAll('.metric-thumb').forEach(b=>{const yes=b.dataset.view===state.view;b.classList.toggle('active',yes);b.setAttribute('aria-pressed',String(yes));});
      persist();
    }
    function geometry() {
      // Fit the entire registered canvas to the shell opening. Base, evidence,
      // pointer coordinates and patch outlines share this same two-axis mapping.
      // Region selection changes support, never the painting's framing.
      const bounds=[0,0,payload.shape[1],payload.shape[0]];
      const frame=painting.getBoundingClientRect();
      const result={w:frame.width,h:frame.height,left:0,top:0,bounds};
      Object.assign(base.style,{position:'absolute',width:`${result.w}px`,height:`${result.h}px`,left:`${result.left}px`,top:`${result.top}px`,maxWidth:'none'});
      return result;
    }
    function anchorControls() {
      const r=stage.getBoundingClientRect();
      [['.st-key-metric_painting_selector',.573,.075],['.st-key-metric_surprise_button',.661,.067]].forEach(([selector,left,width])=>{
        const node=doc.querySelector(selector);if(!node)return;
        const values={position:'fixed',left:`${r.left+left*r.width}px`,top:`${r.top+.1355*r.height}px`,width:`${width*r.width}px`,height:`${.032*r.height}px`,'--metric-unit':`${r.width/100}px`};
        Object.entries(values).forEach(([k,v])=>node.style.setProperty(k,v,'important'));
      });
    }
    function render() {
      if(!rendered||!active){loupe.hidden=true;patchOutline.hidden=true;return;}
      loupe.hidden=false;
      const g=geometry(),size=Math.min(painting.clientWidth*.43,painting.clientHeight*.64);
      patchOutline.hidden=state.region!=='patches'||currentPatch<0;
      if(!patchOutline.hidden){
        const p=payload.patches[currentPatch];
        Object.assign(patchOutline.style,{left:`${g.left+p[0]/payload.shape[1]*g.w}px`,top:`${g.top+p[1]/payload.shape[0]*g.h}px`,width:`${(p[2]-p[0])/payload.shape[1]*g.w}px`,height:`${(p[3]-p[1])/payload.shape[0]*g.h}px`});
        patchOutline.dataset.window=p.join(',');
      }
      loupe.style.width=`${size}px`;loupe.style.height=`${size}px`;
      const left=Math.max(0,Math.min(painting.clientWidth-size,g.left+x*g.w-size/2));
      const top=Math.max(0,Math.min(painting.clientHeight-size,g.top+y*g.h-size/2));
      loupe.style.left=`${left}px`;loupe.style.top=`${top}px`;
      const dpr=window.devicePixelRatio||1,w=loupe.clientWidth,h=loupe.clientHeight;
      canvas.width=Math.max(1,Math.round(w*dpr));canvas.height=Math.max(1,Math.round(h*dpr));
      const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);ctx.clearRect(0,0,w,h);
      const zoom=1.65,sw=w/g.w*payload.shape[1]/zoom,sh=h/g.h*payload.shape[0]/zoom;
      const sx=x*payload.shape[1]-sw/2,sy=y*payload.shape[0]-sh/2;
      ctx.fillStyle='#242b2a';ctx.fillRect(0,0,w,h);
      ctx.imageSmoothingEnabled=!['features','semantic'].includes(state.lens)&&state.region!=='patches';
      rendered.forEach((img,i)=>{ctx.save();if(rendered.length===2){ctx.beginPath();ctx.rect(i*w/2,0,w/2,h);ctx.clip();}ctx.drawImage(img,sx,sy,sw,sh,0,0,w,h);ctx.restore();});
      if(rendered.length===2){ctx.strokeStyle='#e9cc83';ctx.beginPath();ctx.moveTo(w/2,0);ctx.lineTo(w/2,h);ctx.stroke();}
      ctx.strokeStyle='#f5dfae';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(w/2-4,h/2);ctx.lineTo(w/2+4,h/2);ctx.moveTo(w/2,h/2-4);ctx.lineTo(w/2,h/2+4);ctx.stroke();
      let suffix=`x ${Math.round(x*payload.shape[1])}, y ${Math.round(y*payload.shape[0])}`;
      if(state.region==='patches'&&currentPatch>=0){const vals=active.patch_values.map(v=>v[currentPatch].toFixed(4));suffix=`Window ${currentPatch+1} · ${vals.join(' / ')}`;}
      readout.textContent=`Inspection point · ${suffix}`;
      Object.assign(loupe.dataset,{x:String(x),y:String(y),patch:String(currentPatch),zoom:String(zoom),enabled:'true',mapKind:active.recipe});
      loupe.setAttribute('aria-label',`${active.metric}, ${active.region_label}. ${suffix}. Drag or use arrow keys; Shift moves faster.`);
    }
    function snap(nx,ny) {
      if(state.region!=='patches'){currentPatch=-1;return [nx,ny];}
      let best=Infinity,index=0;
      payload.patches.forEach((p,i)=>{const cx=(p[0]+p[2])/2/payload.shape[1],cy=(p[1]+p[3])/2/payload.shape[0],d=(cx-nx)**2+(cy-ny)**2;if(d<best){best=d;index=i;}});
      currentPatch=index;const p=payload.patches[index];return [(p[0]+p[2])/2/payload.shape[1],(p[1]+p[3])/2/payload.shape[0]];
    }
    function move(nx,ny){const b=geometry().bounds;[x,y]=snap(Math.max(b[0]/payload.shape[1],Math.min(b[2]/payload.shape[1],nx)),Math.max(b[1]/payload.shape[0],Math.min(b[3]/payload.shape[0],ny)));render();}
    function compose(map,mask,baseImg) {
      const c=doc.createElement('canvas');[c.width,c.height]=[payload.shape[1],payload.shape[0]];const ctx=c.getContext('2d');
      ctx.drawImage(baseImg,0,0,c.width,c.height);ctx.globalAlpha=.84;ctx.drawImage(map,0,0,c.width,c.height);ctx.globalAlpha=1;
      const m=doc.createElement('canvas');m.width=c.width;m.height=c.height;const mc=m.getContext('2d');mc.drawImage(mask,0,0);const md=mc.getImageData(0,0,m.width,m.height);
      const image=ctx.getImageData(0,0,c.width,c.height);
      // Map alpha also carries invalid encoder tokens / SSIM border support.
      mc.clearRect(0,0,m.width,m.height);mc.drawImage(map,0,0);const validity=mc.getImageData(0,0,m.width,m.height).data;
      for(let j=0;j<image.data.length;j+=4){if(md.data[j]<128||validity[j+3]===0){const px=(j/4)%c.width,py=Math.floor(j/4/c.width),v=(px+py)%16<3?98:56;image.data[j]=v;image.data[j+1]=v;image.data[j+2]=v;image.data[j+3]=255;}}
      ctx.putImageData(image,0,0);return c;
    }
    async function select(reset=true) {
      const request=++generation;updateButtons();stage.dataset.requestGeneration=String(request);stage.dataset.evidenceKey='';active=null;rendered=null;loupe.hidden=true;loupe.dataset.enabled='false';
      loupe.setAttribute('aria-disabled','true');patchOutline.hidden=true;
      for(const key of Object.keys(plaque.dataset))delete plaque.dataset[key];
      plaque.removeAttribute('title');
      base.src=payload.views[state.view];base.alt=`${payload.title} — ${state.view}`;
      geometry();
      if(!state.region){stage.dataset.loadState='awaiting-region';plaque.replaceChildren(textNode('h3','Choose a compatible region'),textNode('p','The highlighted region is recommended. Disabled regions explain why they cannot be used.'));readout.textContent='Choose a region to inspect';return;}
      const spec=payload.pairs[`${state.lens}:${state.region}`];
      if(!spec?.allowed)return;
      stage.dataset.loadState='loading';readout.textContent='Loading aligned evidence…';
      try {
        const [baseImg,mask,...maps]=await Promise.all([load(payload.views[state.view]),load(payload.regions[state.region].uri),...spec.maps.map(n=>load(payload.assets[n].uri))]);
        if(request!==generation||!stage.isConnected)return;
        active=spec;rendered=maps.map(m=>compose(m,mask,baseImg));
        stage.dataset.evidenceKey=`${payload.candidate_id}:${state.lens}:${state.region}:${payload.version}`;
        plaqueFor(spec);if(reset){[x,y]=snap(...payload.regions[state.region].centre);}
        stage.dataset.loadState='ready';loupe.setAttribute('aria-disabled','false');render();
      } catch(error) {
        if(request!==generation)return;active=null;rendered=null;loupe.hidden=true;patchOutline.hidden=true;stage.dataset.loadState='error';stage.dataset.evidenceKey='';plaque.replaceChildren(textNode('h3','Evidence unavailable'),textNode('p','This map could not be loaded. Choose another combination or reload.'));readout.textContent='Evidence failed to load';console.error('Metric evidence load failed',error);
      }
    }
    stage.querySelectorAll('.metric-lens-head').forEach(b=>on(b,'click',()=>{
      state.lens=b.closest('[data-lens]').dataset.lens;
      if(state.region&&!payload.pairs[`${state.lens}:${state.region}`].allowed){note.textContent=payload.pairs[`${state.lens}:${state.region}`].reason;state.region=null;}
      else note.textContent='';select(true);
    }));
    stage.querySelectorAll('.metric-region').forEach(b=>on(b,'click',()=>{if(b.disabled)return;state.region=b.dataset.region;note.textContent='';select(true);}));
    stage.querySelectorAll('.metric-thumb').forEach(b=>on(b,'click',()=>{state.view=b.dataset.view;select(false);}));
    let dragging=false;
    on(loupe,'pointerdown',e=>{if(!active)return;dragging=true;loupe.setPointerCapture(e.pointerId);loupe.focus();e.preventDefault();});
    on(loupe,'pointermove',e=>{if(!dragging)return;const rect=painting.getBoundingClientRect(),g=geometry();move((e.clientX-rect.left-g.left)/g.w,(e.clientY-rect.top-g.top)/g.h);});
    on(loupe,'pointerup',()=>{dragging=false;});on(loupe,'pointercancel',()=>{dragging=false;});
    on(loupe,'keydown',e=>{
      const dirs={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]};if(!active||!dirs[e.key])return;e.preventDefault();
      const g=geometry(),step=e.shiftKey?18:7,d=dirs[e.key];
      if(state.region==='patches')move(x+d[0]*112/payload.shape[1],y+d[1]*112/payload.shape[0]);
      else move(x+d[0]*step/g.w,y+d[1]*step/g.h);
    });
    const resize=new ResizeObserver(()=>{anchorControls();render();});resize.observe(painting);
    on(window.parent,'scroll',anchorControls);on(window.parent,'resize',anchorControls);anchorControls();
    const cleanup=new MutationObserver(()=>{if(!stage.isConnected){abort.abort();resize.disconnect();cleanup.disconnect();loaded.clear();}});cleanup.observe(doc.body,{childList:true,subtree:true});
    stage.dataset.controllerReady=payload.version;select(true);
  }
  // Streamlit may commit the scene after executing st.html. Observe the commit
  // instead of binding stale controls from the preceding fragment render.
  function attempt(){const stage=doc.querySelector(`.metric-stage[data-painting-id="${payload.painting_id}"]`);if(stage){mount(stage);return true;}return false;}
  if(!attempt()){const observer=new MutationObserver(()=>{if(attempt())observer.disconnect();});observer.observe(doc.body,{childList:true,subtree:true});setTimeout(()=>observer.disconnect(),15000);}
})();
