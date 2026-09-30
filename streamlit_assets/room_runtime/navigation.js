/* Streamlit v1 component transport. No layout or scientific data changes. */
function museumInternalQuery(href, currentHref, room) {
  const current=new URL(currentHref), target=new URL(href,current);
  if(target.origin!==current.origin || target.pathname!==current.pathname ||
     target.searchParams.get('room')!==room || target.hash) return null;
  return Object.fromEntries(target.searchParams);
}
if(typeof module!=='undefined')module.exports={museumInternalQuery};
if(typeof window!=='undefined')(()=>{
  const parent=window.parent, doc=parent.document;
  let room=null, pending=null, sequence=0;
  const instance=Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);
  doc.documentElement.dataset.museumDocumentId ||= instance;
  const send=(type,extra={})=>parent.postMessage({isStreamlitMessage:true,type,...extra},'*');
  function click(event){
    if(!room || event.defaultPrevented || event.button>0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)return;
    const anchor=event.target.closest?.('a[href]');
    if(!anchor || anchor.hasAttribute('download') || (anchor.target && anchor.target!=='_self'))return;
    const query=museumInternalQuery(anchor.href,parent.location.href,room);
    if(!query)return; // Cross-room navigation stays a normal full-page link.
    event.preventDefault();
    if(pending)return; // Single-flight: do not submit the old room twice.
    if(new URL(anchor.href).search===parent.location.search)return;
    pending=instance+':'+(++sequence);
    send('streamlit:setComponentValue',{value:{id:pending,room,query},dataType:'json'});
  }
  function dispose(){doc.removeEventListener('click',click,true);}
  parent.__museumNavigation?.dispose();
  const bridge={dispose,ready:false};
  parent.__museumNavigation=bridge;
  doc.addEventListener('click',click,true);
  window.addEventListener('unload',dispose,{once:true});
  window.addEventListener('message',event=>{
    if(event.source!==parent || event.data?.type!=='streamlit:render')return;
    room=event.data.args.room;
    bridge.ready=true;
    if(event.data.args.acknowledged===pending)pending=null;
    // Hide only this transport component, never any room or its controls.
    window.frameElement?.closest('[data-testid="stElementContainer"]')?.style.setProperty('display','none','important');
    send('streamlit:setFrameHeight',{height:0});
  });
  send('streamlit:componentReady',{apiVersion:1});
  send('streamlit:setFrameHeight',{height:0});
})();
