const test=require('node:test');
const assert=require('node:assert/strict');
const {museumInternalQuery}=require('../streamlit_assets/room_runtime/navigation.js');
const {watch}=require('../streamlit_assets/room_runtime/readiness.js');
const vm=require('node:vm');
const fs=require('node:fs');

test('bridge handshake, single-flight acknowledgement, and cross-room default navigation',()=>{
  const sent=[],listeners={},windowListeners={};
  const doc={documentElement:{dataset:{}},addEventListener:(type,fn)=>listeners[type]=fn,
    removeEventListener:(type,fn)=>{if(listeners[type]===fn)delete listeners[type];}};
  const parent={document:doc,location:{href:'http://localhost:8501/?room=case_explorer',search:'?room=case_explorer'},
    postMessage:message=>sent.push(message)};
  const window={parent,addEventListener:(type,fn)=>windowListeners[type]=fn};
  vm.runInNewContext(fs.readFileSync(require.resolve('../streamlit_assets/room_runtime/navigation.js'),'utf8'),{window,URL});
  assert.equal(parent.__museumNavigation.ready,false);
  const render=ack=>windowListeners.message({source:parent,data:{type:'streamlit:render',args:{room:'case_explorer',acknowledged:ack}}});
  render('');assert.equal(parent.__museumNavigation.ready,true);
  const click=href=>{
    let prevented=false;
    listeners.click({button:0,target:{closest:()=>({href,target:'_self',hasAttribute:()=>false})},preventDefault:()=>prevented=true});
    return prevented;
  };
  const updates=()=>sent.filter(m=>m.type==='streamlit:setComponentValue');
  assert.equal(click('http://localhost:8501/?room=trustworthiness'),false);
  assert.equal(updates().length,0);
  assert.equal(click('http://localhost:8501/?room=case_explorer&ce_layer=colour'),true);
  assert.equal(updates().length,1);
  click('http://localhost:8501/?room=case_explorer&ce_layer=boundary');
  assert.equal(updates().length,1);
  render(updates()[0].value.id);
  click('http://localhost:8501/?room=case_explorer&ce_layer=boundary');
  assert.equal(updates().length,2);
  windowListeners.unload();assert.equal(listeners.click,undefined);
});

test('only same-room local URLs use the Streamlit transport',()=>{
  const base='http://localhost:8501/?room=case_explorer&ce_painting=p018';
  assert.deepEqual(museumInternalQuery('?room=case_explorer&ce_layer=colour',base,'case_explorer'),{room:'case_explorer',ce_layer:'colour'});
  for(const url of ['?room=trustworthiness','https://example.org/?room=case_explorer','/other?room=case_explorer','#anchor'])
    assert.equal(museumInternalQuery(url,base,'case_explorer'),null);
});

function harness(){
  let stage=null, first=null, mutation, tick, unload, mounts=0, disconnected=false, cleared=false;
  const doc={documentElement:{},querySelector:s=>s.startsWith('main[')?stage:first};
  const win={parent:{document:doc},MutationObserver:class{constructor(cb){mutation=cb;}observe(){}disconnect(){disconnected=true;}},
    setInterval:cb=>{tick=cb;return 1;},clearInterval:()=>{cleared=true;},addEventListener:(_,cb)=>{unload=cb;}};
  const make=()=>({dataset:{},classList:Object.assign(['ce-stage'],{contains:c=>c==='ce-stage'}),closest:()=>({querySelector:()=>({})})});
  watch(win,'render-1',()=>mounts++);
  return {win,make,update(s,f=s){stage=s;first=f;mutation();},tick:()=>tick(),unload:()=>unload(),get mounts(){return mounts;},get cleaned(){return disconnected&&cleared;}};
}
test('late DOM and late bridge recover without refresh; repeat mutations do not double mount',()=>{
  const h=harness(),stage=h.make();
  h.update(stage);assert.equal(h.mounts,0);
  h.win.parent.__museumNavigation={ready:false};h.tick();assert.equal(h.mounts,0);
  h.win.parent.__museumNavigation.ready=true;h.tick();assert.equal(h.mounts,1);
  h.update(stage);h.tick();assert.equal(h.mounts,1);
  assert.equal(stage.dataset.runtimeReady,'render-1');
});
test('stale first DOM is not mounted, replacement is mounted once, unload cleans up',()=>{
  const h=harness();h.win.parent.__museumNavigation={ready:true};
  const stage=h.make();h.update(stage,h.make());assert.equal(h.mounts,0);
  h.update(stage);assert.equal(h.mounts,1);
  h.update(h.make());assert.equal(h.mounts,2);
  h.unload();h.tick();assert.equal(h.mounts,2);assert.ok(h.cleaned);
});
