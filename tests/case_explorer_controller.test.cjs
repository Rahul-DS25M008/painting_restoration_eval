const test=require('node:test');
const assert=require('node:assert/strict');
const {ceFilter,ceUrl,ceScope,ceRandom}=require('../streamlit_assets/case_explorer_controller.js');

test('one-field pickers preserve upstream choices and release downstream defaults',()=>{
  const current={experiment_id:'core',case_id:'mixed',model_id:'lama'};
  const rows=[{candidate_id:'a',experiment_id:'core',case_id:'mixed',model_id:'lama'},
    {candidate_id:'b',experiment_id:'core',case_id:'mixed',model_id:'sd'},
    {candidate_id:'c',experiment_id:'core',case_id:'scratch',model_id:'lama'},
    {candidate_id:'d',experiment_id:'size',case_id:'size02',model_id:'lama'}];
  assert.equal(ceScope(rows,current,'experiment').length,4);
  assert.deepEqual(ceScope(rows,current,'damage').map(x=>x.candidate_id),['a','b','c']);
  assert.deepEqual(ceScope(rows,current,'model').map(x=>x.candidate_id),['a','b']);
  assert.deepEqual(ceScope(rows,current,'candidate').map(x=>x.candidate_id),['a']);
  assert.equal(ceRandom(rows,()=>0).candidate_id,'a');
  assert.equal(ceRandom(rows,()=>.999).candidate_id,'d');
  assert.equal(ceRandom([]),null);
});

test('candidate filters keep seed and prompt identities distinct',()=>{
  const rows=[{candidate_id:'a',seed:2026,prompt_variant_id:'p00'},
              {candidate_id:'b',seed:2027,prompt_variant_id:'p00'},
              {candidate_id:'c',seed:2026,prompt_variant_id:'p05'},
              {candidate_id:'d',seed:null,prompt_variant_id:null}];
  assert.deepEqual(ceFilter(rows,{seed:'2026',prompt_variant_id:'p05'}).map(x=>x.candidate_id),['c']);
  assert.deepEqual(ceFilter(rows,{seed:'2029'}),[]);
  assert.equal(ceFilter(rows,{seed:'',prompt_variant_id:''}).length,4);
});
test('navigation retains exact candidate and discards stale map or report state',()=>{
  const state={painting:{painting_id:'p018'},candidate:{candidate_id:'candidate:a & b'},layer:'colour'};
  const url=ceUrl(state,{ce_layer:'texture'});
  const params=new URLSearchParams(url.slice(1));
  assert.equal(params.get('ce_candidate'),'candidate:a & b');
  assert.equal(params.get('ce_layer'),'texture');
  assert.equal(params.has('ce_map'),false);
  assert.equal(params.has('ce_report'),false);
  assert.equal(new URLSearchParams(ceUrl(state,{ce_painting:'p002',ce_candidate:''}).slice(1)).has('ce_candidate'),false);
});
