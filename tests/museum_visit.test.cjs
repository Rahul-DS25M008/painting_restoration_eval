const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const visit=require('../streamlit_assets/museum_visit/controller.js');
const data=require('../streamlit_assets/museum_visit/tour.json');

test('eight principal rooms form a six-minute route',()=>{
  assert.deepEqual(data.stops.map(s=>s.room),['exhibition_foyer','study_design','metric_framework','model_gallery','stability_lab','trustworthiness','case_explorer','research_archive']);
  assert.equal(visit.totalSeconds(data.stops),360);
  for(const s of data.stops)for(const key of ['label','chapter','question','look','takeaway','stamp'])assert.ok(s[key]);
});
test('corrupt or stale storage cannot inject rooms or duplicate stamps',()=>{
  assert.deepEqual(visit.normalize({active:'true',visited:['study_design','study_design','javascript:bad'],lastMain:'evil'},data.stops),{version:1,active:false,minimized:false,visited:['study_design'],lastMain:null});
  assert.equal(visit.normalize(null,data.stops).visited.length,0);
});
test('visiting is opt-in and idempotent; side room does not add a ninth stamp',()=>{
  const initial=visit.normalize(null,data.stops);
  assert.equal(visit.arrive(initial,'study_design',data.stops).visited.length,0);
  initial.active=true;
  const first=visit.arrive(initial,'study_design',data.stops);
  assert.deepEqual(visit.arrive(first,'study_design',data.stops),first);
  assert.deepEqual(visit.arrive(first,data.detour.room,data.stops),first);
  assert.equal(initial.visited.length,0);
});
test('all eight arrivals complete a passport without a timer',()=>{
  let state={active:true};
  for(const s of data.stops)state=visit.arrive(state,s.room,data.stops);
  assert.equal(state.visited.length,8);assert.equal(state.lastMain,'research_archive');
});
test('navigation allows only known room routes',()=>{
  for(const s of [...data.stops,data.detour])assert.equal(visit.roomURL(s.room,data.stops,data.detour),'?room='+s.room);
  assert.throws(()=>visit.roomURL('https://evil.example',data.stops,data.detour));
  for(const i of data.invitations)assert.ok(data.stops.some(s=>s.room===i.room));
});
test('styles are isolated and there is no automatic navigation timer',()=>{
  const css=fs.readFileSync('streamlit_assets/museum_visit/visit.css','utf8');
  for(const line of css.split('\n').filter(l=>l.includes('{')&&!l.trim().startsWith('@')))assert.ok(line.trim().startsWith('#museum-visit-root'));
  const script=fs.readFileSync('streamlit_assets/museum_visit/controller.js','utf8');
  assert.ok(!/setInterval|setTimeout|localStorage/.test(script));
  assert.ok(script.includes('sessionStorage'));
});
