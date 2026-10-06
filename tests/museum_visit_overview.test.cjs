const test=require('node:test');
const assert=require('node:assert/strict');
const visit=require('../streamlit_assets/museum_visit/controller.js');
const data=require('../streamlit_assets/museum_visit/tour.json');

// Deliberately small DOM double: exercise the real controller's events, without
// a browser, network, DOM dependency or changes to scientific evidence.
class Element {
  constructor(tag,doc){this.tag=tag;this.doc=doc;this.children=[];this.attrs={};this.listeners={};this.dataset={};this.hidden=false;this.paused=true;this.currentTime=0;this.isConnected=true;}
  append(...nodes){for(const n of nodes){n.parent=this;this.children.push(n);}}
  replaceChildren(...nodes){this.children=[];this.append(...nodes);}
  setAttribute(k,v){this.attrs[k]=String(v);}
  getAttribute(k){return this.attrs[k]??this[k]??null;}
  addEventListener(k,fn){(this.listeners[k]??=[]).push(fn);}
  async fire(k,event={}){for(const fn of this.listeners[k]||[])await fn(event);}
  click(){return this.fire('click');}
  all(){return this.children.flatMap(n=>[n,...n.all()]);}
  querySelectorAll(q){return this.all().filter(n=>q.startsWith('.')?n.className?.split(' ').includes(q.slice(1)):n.tag===q);}
  querySelector(q){return q==='header > div'?this.querySelector('header')?.children[0]:this.querySelectorAll(q)[0];}
  showModal(){this.open=true;}
  close(){this.open=false;this.fire('close');}
  pause(){this.paused=true;this.pauseCount=(this.pauseCount||0)+1;}
  play(){this.paused=false;return this.fire('playing');}
  focus(){this.doc.activeElement=this;}
  remove(){this.parent.children=this.parent.children.filter(n=>n!==this);}
}
function setup(media={video:'/media/tour.mp4',poster:'/media/poster.jpg',duration:115},href='http://localhost:8501/?room=exhibition_foyer&tour=1'){
  const doc={createElement(tag){return new Element(tag,this);}};doc.body=new Element('body',doc);
  doc.querySelectorAll=q=>doc.body.querySelectorAll(q);
  const storage=new Map();const parent={document:doc,location:{href},history:{replaceState(){}},sessionStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},AbortController,MutationObserver:class{observe(){}disconnect(){}}};
  visit.install({parent,addEventListener(){}},{...data,room:'exhibition_foyer',legacyLaunch:true,media},'');
  return {doc,parent,storage,dialog:doc.body.querySelector('dialog'),find:text=>doc.body.all().find(n=>n.textContent===text),video:()=>doc.body.querySelector('video')};
}
test('overview is default; media is click-to-load and does not stamp a visit',async()=>{
  const h=setup();assert.equal(h.dialog.dataset.tourView,'overview');
  assert.equal(h.video().getAttribute('src'),null);assert.equal(h.video().preload,'none');assert.equal(h.video().paused,true);
  assert.equal(h.video().poster,'http://localhost:8501/media/poster.jpg');assert.equal(h.video().playsInline,true);
  assert.deepEqual(JSON.parse(h.storage.get(visit.storageKey)).visited,[]);
  await h.find('▶').click();assert.equal(h.video().src,'http://localhost:8501/media/tour.mp4');assert.equal(h.video().controls,true);assert.equal(h.video().paused,false);
  assert.deepEqual(JSON.parse(h.storage.get(visit.storageKey)).visited,[]);
});
test('Cloud media retains the parent app prefix and remains click-to-load',async()=>{
  const h=setup(undefined,'https://example.streamlit.app/~/+/?room=exhibition_foyer&tour=1');
  assert.equal(h.video().poster,'https://example.streamlit.app/~/+/media/poster.jpg');
  assert.equal(h.video().getAttribute('src'),null);
  await h.find('▶').click();
  assert.equal(h.video().src,'https://example.streamlit.app/~/+/media/tour.mp4');
  assert.equal(h.video().controls,true);
});
test('media URLs already carrying a path or origin are not rewritten',async()=>{
  for(const prefix of ['/custom/media/','https://example.streamlit.app/~/+/media/']){
    const media={video:prefix+'tour.mp4',poster:prefix+'poster.jpg',duration:115};
    const h=setup(media,'https://example.streamlit.app/~/+/?room=exhibition_foyer&tour=1');
    assert.equal(h.video().poster,media.poster);
    await h.find('▶').click();assert.equal(h.video().src,media.video);
  }
});
test('room tab retains the exact eight-room route and pauses video without reload',async()=>{
  const h=setup();await h.find('▶').click();h.video().currentTime=31;
  await h.find('Explore Rooms').click();assert.equal(h.dialog.dataset.tourView,'rooms');assert.equal(h.video().paused,true);
  const route=h.doc.body.querySelector('.mv-route');assert.equal(route.children.length,8);
  for(const [i,row]of route.children.entries()){assert.equal(row.children[0].textContent,String(i+1).padStart(2,'0'));assert.equal(row.children[1].children[0].textContent,data.stops[i].label);assert.equal(row.children[2].textContent,data.stops[i].seconds+' sec');}
  await h.find('Tour Overview').click();assert.equal(h.video().currentTime,31);assert.equal(h.video().paused,true);
  await h.find('Explore Rooms →').click();assert.equal(h.doc.activeElement,h.find('Explore Rooms'));
});
test('tab keyboard navigation and modal close pause safely',async()=>{
  const h=setup();await h.find('▶').click();
  await h.find('Tour Overview').fire('keydown',{key:'ArrowRight',preventDefault(){}});
  assert.equal(h.dialog.dataset.tourView,'rooms');assert.equal(h.find('Explore Rooms').getAttribute('aria-selected'),'true');assert.equal(h.find('Tour Overview').tabIndex,-1);
  await h.find('Explore Rooms').fire('keydown',{key:'Home',preventDefault(){}});
  assert.equal(h.dialog.dataset.tourView,'overview');
  await h.video().play();await h.find('×').click();assert.equal(h.video().paused,true);assert.equal(h.dialog.open,false);
});
test('begin uses original opt-in passport; disposal stops playback',async()=>{
  const h=setup();await h.find('Explore Rooms').click();await h.find('Begin the six-minute tour →').click();
  assert.deepEqual(JSON.parse(h.storage.get(visit.storageKey)).visited,['exhibition_foyer']);assert.equal(h.dialog.open,false);
  const video=h.video();await video.play();h.parent.__museumVisit.dispose();assert.equal(video.paused,true);
});
test('missing film leaves the full route usable',async()=>{
  const h=setup(null);assert.equal(h.video(),undefined);assert.ok(h.find('The film is unavailable right now. The complete eight-room route is still ready to explore.'));
  await h.find('Explore Rooms →').click();assert.equal(h.dialog.dataset.tourView,'rooms');assert.ok(h.find('Begin the six-minute tour →'));
});
test('a delayed play completion cannot keep audio running after changing tabs',async()=>{
  const h=setup();let finish;h.video().play=()=>new Promise(resolve=>{finish=()=>{h.video().paused=false;resolve();};});
  const started=h.find('▶').click();await h.find('Explore Rooms').click();finish();await started;assert.equal(h.video().paused,true);
});
