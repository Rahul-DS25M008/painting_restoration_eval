/* Wait for this exact render, including dialogs outside <main> in st.html. */
const MuseumReadiness = {
  watch(win, revision, initialize) {
    const doc=win.parent.document, mounted=new WeakSet();
    let stopped=false;
    function attempt(){
      if(stopped)return;
      const stage=doc.querySelector(`main[data-room-render="${revision}"]`);
      if(!stage || mounted.has(stage))return;
      const container=stage.closest('.stHtml');
      if(!container || !win.parent.__museumNavigation?.ready)return;
      // During replacement Streamlit may briefly retain an old room first.
      const selector='.'+[...stage.classList].find(c=>c.endsWith('-stage'));
      if(doc.querySelector(selector)!==stage)return;
      if(stage.classList.contains('ce-stage') &&
         (!container.querySelector('.ce-dialog') || !container.querySelector('.ce-access-bar')))return;
      mounted.add(stage);
      try{initialize();stage.dataset.runtimeReady=revision;}
      catch(error){stage.dataset.runtimeError=String(error);console.error('Room initialization failed',error);}
    }
    const observer=new win.MutationObserver(attempt);
    observer.observe(doc.documentElement,{childList:true,subtree:true});
    // The bridge is an independent iframe; its ready message may precede DOM changes.
    const interval=win.setInterval(attempt,150);
    function dispose(){stopped=true;observer.disconnect();win.clearInterval(interval);}
    win.addEventListener('unload',dispose,{once:true});
    attempt();
    return dispose;
  }
};
if(typeof module!=='undefined')module.exports=MuseumReadiness;
