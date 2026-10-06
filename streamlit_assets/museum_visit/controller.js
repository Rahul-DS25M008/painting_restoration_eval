/* An opt-in visitor layer. No room DOM, evidence selection, or artwork is rewritten. */
const MuseumVisit={
  storageKey:'museum.visit.v1',
  normalize(value,stops){
    const rooms=new Set(stops.map(s=>s.room));
    return {version:1,active:value?.active===true,minimized:value?.minimized===true,visited:[...new Set(Array.isArray(value?.visited)?value.visited.filter(r=>rooms.has(r)):[])],lastMain:rooms.has(value?.lastMain)?value.lastMain:null};
  },
  arrive(state,room,stops){const next=this.normalize(state,stops);if(next.active&&stops.some(s=>s.room===room)){if(!next.visited.includes(room))next.visited.push(room);next.lastMain=room;}return next;},
  totalSeconds(stops){return stops.reduce((sum,s)=>sum+s.seconds,0);},
  roomURL(room,stops,detour){if(!stops.some(s=>s.room===room)&&room!==detour?.room)throw Error('Unknown museum room');return '?'+new URLSearchParams({room});},
  install(win,data,css){
    const parent=win.parent,doc=parent.document,api=this;
    function mediaURL(path) {
      if (!path.startsWith('/media/')) return path;
      // Preserve the app directory, including Community Cloud's /~/+/ prefix.
      return new URL(path.slice(1), parent.location.href).href;
    }
    parent.__museumVisit?.dispose();
    const host=doc.createElement('div');host.id='museum-visit-root';
    const style=doc.createElement('style');style.textContent=css;host.append(style);doc.body.append(host);
    // Hide only this zero-height transport, not any room component.
    win.frameElement?.closest('[data-testid="stElementContainer"]')?.style.setProperty('display','none','important');
    let state,storageOK=true,previousFocus=null,disposed=false;
    try{state=api.normalize(JSON.parse(parent.sessionStorage.getItem(api.storageKey)||'null'),data.stops);}catch{storageOK=false;state=api.normalize(null,data.stops);}
    const legacyLaunch=data.legacyLaunch&&new URL(parent.location.href).searchParams.get('tour')==='1';
    if(legacyLaunch){const url=new URL(parent.location.href);url.searchParams.delete('tour');parent.history.replaceState(parent.history.state,'',url);}
    if(legacyLaunch&&data.room!=='exhibition_foyer')state.active=true;
    state=api.arrive(state,data.room,data.stops);
    function save(){try{parent.sessionStorage.setItem(api.storageKey,JSON.stringify(state));}catch{storageOK=false;}}
    save();
    const el=(tag,text,cls)=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n;};
    function button(text,fn,where,cls='mv-button'){const b=el('button',text,cls);b.type='button';b.addEventListener('click',fn);where.append(b);return b;}
    function eyebrow(text,where){where.append(el('p',text,'mv-eyebrow'));}
    const dialog=el('dialog',undefined,'mv-dialog');dialog.setAttribute('aria-labelledby','mv-dialog-title');host.append(dialog);
    const panel=el('aside',undefined,'mv-guide');panel.setAttribute('aria-label','Museum tour companion');panel.hidden=true;host.append(panel);
    const dock=button('Your museum passport',()=>showGuide(),host,'mv-dock');dock.hidden=true;
    function index(){return data.stops.findIndex(s=>s.room===data.room);}
    function current(){return data.stops[index()];}
    function pauseVideo(){for(const video of dialog.querySelectorAll('video'))video.pause();}
    function closeDialog(){pauseVideo();dialog.close();if(state.active)collapse();if(previousFocus?.isConnected)previousFocus.focus();}
    function modal(kicker,title,subtitle){
      if(!dialog.open)previousFocus=doc.activeElement;
      pauseVideo();panel.hidden=true;dock.hidden=true;dialog.replaceChildren();delete dialog.dataset.tourView;
      const header=el('header'),copy=el('div');eyebrow(kicker,copy);const h=el('h2',title);h.id='mv-dialog-title';copy.append(h);if(subtitle)copy.append(el('p',subtitle,'mv-subtitle'));header.append(copy);button('×',closeDialog,header,'mv-close').setAttribute('aria-label','Close visitor guide');dialog.append(header);
      const body=el('div',undefined,'mv-body');dialog.append(body);if(!dialog.open)dialog.showModal();dialog.scrollTop=0;return body;
    }
    function navigate(room){
      pauseVideo();
      state.minimized=false;save();if(room===data.room){if(dialog.open)dialog.close();showGuide();return;}
      const a=el('a');a.href=api.roomURL(room,data.stops,data.detour);if(state.active&&!storageOK)a.href+='&tour=1';a.target='_self';host.append(a);a.click();a.remove();
    }
    function begin(fresh){
      pauseVideo();
      if(fresh)state=api.normalize(null,data.stops);state.active=true;
      if(fresh&&data.room==='exhibition_foyer'){state=api.arrive(state,data.room,data.stops);save();dialog.close();showGuide();}
      else{const next=data.stops.find(s=>!state.visited.includes(s.room))||data.stops[0];navigate(next.room);}
    }
    function routeList(where,interactive=false){
      const list=el('ol',undefined,'mv-route');
      for(const [i,s]of data.stops.entries()){
        const visited=state.visited.includes(s.room),row=el('li');row.className=visited?'is-visited':'';
        const mark=el('span',visited?'✓':String(i+1).padStart(2,'0'),'mv-route-number');mark.setAttribute('aria-label',visited?'Visited':'Stop '+(i+1));
        const copy=el('div');copy.append(el('strong',s.label),el('small',s.chapter));row.append(mark,copy,el('span',s.seconds+' sec','mv-route-time'));
        if(interactive){const b=button('Visit '+s.label,()=>{state.active=true;navigate(s.room);},row,'mv-route-jump');b.setAttribute('aria-label','Visit '+s.label);}
        list.append(row);
      }
      where.append(list);
    }
    function introduction(initialView='overview'){
      const body=modal('YOUR MUSEUM PASSPORT',data.title);
      const headerCopy=dialog.querySelector('header > div');
      const subtitle=el('p',data.subtitle,'mv-subtitle');headerCopy.append(subtitle);
      const tabs=el('div',undefined,'mv-tour-tabs');tabs.setAttribute('role','tablist');tabs.setAttribute('aria-label','Museum tour views');headerCopy.append(tabs);
      const overview=el('section',undefined,'mv-overview'),rooms=el('section');
      for(const [name,section]of [['overview',overview],['rooms',rooms]]){section.id='mv-tour-'+name;section.setAttribute('role','tabpanel');section.setAttribute('aria-labelledby','mv-tab-'+name);body.append(section);}
      const tabButtons={};
      function selectView(name,focus=false){
        pauseVideo();const isOverview=name==='overview';dialog.dataset.tourView=name;
        overview.hidden=!isOverview;rooms.hidden=isOverview;subtitle.hidden=isOverview;
        headerCopy.querySelector('.mv-eyebrow').textContent=isOverview?'YOUR MUSEUM PASSPORT':'A CURATOR’S ROUTE / YOUR MUSEUM PASSPORT';
        for(const [key,b]of Object.entries(tabButtons)){b.setAttribute('aria-selected',String(key===name));b.tabIndex=key===name?0:-1;}
        dialog.scrollTop=0;if(focus)tabButtons[name].focus();
      }
      for(const [name,label]of [['overview','Tour Overview'],['rooms','Explore Rooms']]){
        const b=button(label,()=>selectView(name),tabs,'mv-tour-tab');b.id='mv-tab-'+name;b.setAttribute('role','tab');b.setAttribute('aria-controls','mv-tour-'+name);tabButtons[name]=b;
        b.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();selectView(event.key==='Home'?'overview':event.key==='End'?'rooms':name==='overview'?'rooms':'overview',true);});
      }
      overview.append(el('p','Eight rooms. One short introduction.','mv-overview-intro'));
      const player=el('div',undefined,'mv-video-shell'),video=el('video');video.preload='none';video.playsInline=true;video.setAttribute('aria-label','Tour Overview — eight-room museum film, 1 minute 55 seconds');
      const status=el('p',undefined,'mv-video-status');status.setAttribute('role','status');status.hidden=true;
      if(data.media?.video&&data.media?.poster){
        video.poster = mediaURL(data.media.poster);
        player.append(video);
        const play=button('▶',async()=>{
          status.hidden = true;
          if (!video.getAttribute('src')) {
            video.src = mediaURL(data.media.video);
          }
          video.controls=true;play.hidden=true;
          try{await video.play();if(!dialog.open||overview.hidden)video.pause();}
          catch{if(!dialog.open||overview.hidden)return;play.hidden=false;status.textContent='Playback did not start. Try Play again, or explore the rooms below.';status.hidden=false;}
        },player,'mv-video-play');play.setAttribute('aria-label','Play Tour Overview (1:55)');
        const duration=el('span','1:55','mv-video-duration');player.append(duration);
        video.addEventListener('playing',()=>{duration.hidden=true;play.hidden=true;status.hidden=true;});
        video.addEventListener('error',()=>{play.hidden=false;status.textContent='The film could not load. You can retry Play or continue to Explore Rooms.';status.hidden=false;});
        video.addEventListener('ended',()=>{play.hidden=false;});
        overview.append(player,status);
      }else overview.append(el('p','The film is unavailable right now. The complete eight-room route is still ready to explore.','mv-note'));
      overview.append(el('p','Watch first, then explore at your own pace.','mv-overview-caption'));
      const actions=el('div',undefined,'mv-actions');overview.append(actions);button('Explore Rooms →',()=>selectView('rooms',true),actions,'mv-button mv-primary');
      renderRoute(rooms);
      selectView(initialView==='rooms'?'rooms':'overview');
    }
    function renderRoute(body){
      const summary=el('div',undefined,'mv-ticket');for(const [value,label]of [['8','principal rooms'],['≈ 6 min','at your own pace'],['1','question to carry']]){const c=el('div');c.append(el('strong',value),el('span',label));summary.append(c);}body.append(summary);
      body.append(el('p','Start with what you see. Learn how it was tested. Leave knowing where the evidence ends. Each stop offers one small thing to notice—not a lecture or a score.','mv-intro'));
      routeList(body);
      body.append(el('p','Six minutes is a suggested pace, not a countdown. Nothing advances automatically. The Focused Portrait Review is an optional side room, outside this estimate.','mv-note'));
      if(!storageOK)body.append(el('p','This browser cannot save your passport between rooms. The route still works, but visit stamps may reset.','mv-note'));
      const actions=el('div',undefined,'mv-actions');body.append(actions);
      const incomplete=state.visited.length>0&&state.visited.length<data.stops.length;
      if(incomplete)button('Resume your visit →',()=>begin(false),actions,'mv-button mv-primary');
      button(incomplete?'Start a fresh passport':'Begin the six-minute tour →',()=>begin(true),actions,incomplete?'mv-button':'mv-button mv-primary');
      button('I’d rather wander',explore,actions,'mv-button mv-quiet');
      body.append(el('p','Your visit stays in this browser tab. No account, no analytics, no assessment.','mv-footnote'));
    }
    function explore(){
      const body=modal('AN OPEN DOOR / NO RIGHT ORDER','Follow your curiosity.','There is no correct first room. Start with the question that pulls you in.');
      const grid=el('div',undefined,'mv-invitations');body.append(grid);
      for(const item of data.invitations){const card=el('button',undefined,'mv-invitation');card.type='button';card.append(el('span',item.mark,'mv-eyebrow'),el('strong',item.label),el('p',item.text),el('span',data.stops.find(s=>s.room===item.room).label+' ↗','mv-destination'));card.addEventListener('click',()=>{state.active=false;navigate(item.room);});grid.append(card);}
      body.append(el('p','The room map and top navigation are always your compass. Open a label, follow an original report, or come back for the guided route whenever you like.','mv-note'));
      const actions=el('div',undefined,'mv-actions');body.append(actions);
      button('Let me wander',()=>{state.active=false;save();closeDialog();dock.hidden=true;panel.hidden=true;},actions,'mv-button mv-primary');button('Show me the six-minute route',()=>introduction('rooms'),actions,'mv-button mv-quiet');
    }
    function collapse(){state.minimized=true;save();panel.hidden=true;dock.hidden=!state.active;if(state.active){const s=current();dock.textContent='◈  Your passport · '+(s?(index()+1)+' / 8':'side room');}}
    function end(){state.active=false;save();panel.hidden=true;dock.hidden=true;}
    function passport(){
      const body=modal('A RECORD OF YOUR VISIT','The questions you carried.',state.visited.length+' of 8 rooms visited. Stamps mark visits, not expertise.');routeList(body,true);body.append(el('p','You can revisit any room. No timer, no grades, and no conclusion is awarded for finishing the route.','mv-note'));const actions=el('div',undefined,'mv-actions');body.append(actions);button('Back to this room',()=>{dialog.close();showGuide();},actions,'mv-button mv-primary');button('End guided visit',()=>{end();dialog.close();},actions,'mv-button mv-quiet');
    }
    function finish(){
      const complete=state.visited.length===data.stops.length;end();
      const body=modal(complete?'YOUR PASSPORT / EIGHT ROOMS VISITED':'YOUR PASSPORT / A VISIT IN PROGRESS',complete?'You followed the evidence.':'There is more to discover.',complete?'The most useful souvenir is a better question.':state.visited.length+' of 8 rooms visited. Pick up the thread whenever you like.');
      if(complete){const stamps=el('div',undefined,'mv-stamps');for(const s of data.stops)stamps.append(el('span',s.stamp));body.append(stamps);body.append(el('blockquote','“What supports this conclusion—and what would make me reconsider it?”'));body.append(el('p','You have moved from appearance to experiment, from measurements to limitations, and from a single restoration to its original record. That is a route for asking better questions—not conservation approval.','mv-intro'));}
      else routeList(body,true);
      const actions=el('div',undefined,'mv-actions');body.append(actions);if(!complete)button('Continue to the next unvisited room →',()=>begin(false),actions,'mv-button mv-primary');button('Stay and explore',()=>{dialog.close();},actions,complete?'mv-button mv-primary':'mv-button');button('Return to the Foyer',()=>navigate('exhibition_foyer'),actions,'mv-button mv-quiet');
    }
    function showGuide(){
      if(!state.active)return;state.minimized=false;save();panel.replaceChildren();panel.hidden=false;dock.hidden=true;
      const i=index(),s=current(),detour=!s;
      const top=el('div',undefined,'mv-guide-top');eyebrow(detour?'OPTIONAL SIDE ROOM':'YOUR PASSPORT / STOP '+(i+1)+' OF 8',top);button('−',collapse,top,'mv-minimize').setAttribute('aria-label','Minimize tour companion');panel.append(top);
      panel.append(el('h2',s?s.chapter:'A closer look at people'));
      panel.append(el('p',s?s.question:data.detour.question,'mv-question'));
      const meta=el('p',s?s.label+' · about '+s.seconds+' sec':data.detour.label+' · outside the six-minute route','mv-guide-meta');panel.append(meta);
      panel.append(el('p',s?s.look:data.detour.look,'mv-look'));
      if(s){const note=el('details'),summary=el('summary','A thought to take with you');note.append(summary,el('p',s.takeaway));panel.append(note);}
      const progress=el('div',undefined,'mv-progress');progress.setAttribute('aria-label',state.visited.length+' of 8 rooms visited');data.stops.forEach((stop,n)=>{const dot=el('span',String(n+1));dot.className=(state.visited.includes(stop.room)?'is-visited ':'')+(n===i?'is-current':'');dot.title=stop.label;progress.append(dot);});panel.append(progress);
      const actions=el('div',undefined,'mv-guide-actions');panel.append(actions);
      if(detour)button('Back to the main route →',()=>navigate(state.lastMain||data.detour.returnRoom),actions,'mv-button mv-primary');
      else if(i===data.stops.length-1)button('Finish your visit →',finish,actions,'mv-button mv-primary');
      else button('Next: '+data.stops[i+1].label+' →',()=>navigate(data.stops[i+1].room),actions,'mv-button mv-primary');
      button('Look around',collapse,actions,'mv-button');
      const footer=el('div',undefined,'mv-guide-footer');panel.append(footer);if(i>0)button('← Previous room',()=>navigate(data.stops[i-1].room),footer,'mv-text-button');button('Passport',passport,footer,'mv-text-button');button('End tour',end,footer,'mv-text-button');
    }
    dialog.addEventListener('cancel',event=>{event.preventDefault();closeDialog();});
    dialog.addEventListener('close',pauseVideo);
    const bindings=new WeakSet(),abort=new parent.AbortController();
    function bind(){if(disposed)return;for(const target of doc.querySelectorAll('.foyer-action[data-museum-visit]')){if(bindings.has(target))continue;bindings.add(target);target.addEventListener('click',event=>{if(event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;event.preventDefault();event.stopImmediatePropagation();(target.dataset.museumVisit==='tour'?introduction:explore)();},{capture:true,signal:abort.signal});}}
    const observer=new parent.MutationObserver(bind);observer.observe(doc.body,{childList:true,subtree:true});bind();
    function dispose(){if(disposed)return;disposed=true;pauseVideo();abort.abort();observer.disconnect();host.remove();}
    parent.__museumVisit={dispose};win.addEventListener('unload',dispose,{once:true});
    if(state.active){if(state.minimized)collapse();else showGuide();}else if(legacyLaunch&&data.room==='exhibition_foyer')introduction();
  }
};
if(typeof module!=='undefined')module.exports=MuseumVisit;
