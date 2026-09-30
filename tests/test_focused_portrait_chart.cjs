const assert=require('node:assert/strict');
const {portraitPlotGeometry,portraitDifference,portraitObservation,portraitNextReview,portraitLightnessSummary}=require('../streamlit_assets/focused_portrait_controller.js');
for(const rows of [
  [{estimate:.2,interval_low:.1,interval_high:.3}],
  [{estimate:-.3,interval_low:-.7,interval_high:.2}],
  [{estimate:0,interval_low:0,interval_high:0}]
]){
  const before=JSON.stringify(rows),g=portraitPlotGeometry(rows,'estimate');
  assert.ok(g.min<0 && g.max>0);
  for(const r of rows)for(const v of [r.estimate,r.interval_low,r.interval_high,0])assert.ok(Number.isFinite(g.x(v))&&g.x(v)>=124&&g.x(v)<=350);
  assert.equal(JSON.stringify(rows),before);
}
assert.throws(()=>portraitPlotGeometry([{estimate:NaN,interval_low:0,interval_high:1}],'estimate'));
assert.throws(()=>portraitPlotGeometry([],'estimate'));
assert.deepEqual([...portraitDifference([1,100,255,255],[21,75,200,255])],[20,25,55,255]);
assert.deepEqual([...portraitDifference([0,0,0,255],[0,0,0,255])],[0,0,0,255]);
assert.throws(()=>portraitDifference([1],[1]));
assert.throws(()=>portraitDifference([1,2,3,255],[]));
console.log('D02 chart geometry and exact absolute-RGB preview tests passed.');
const review={digit_count_error:0,missing_digits:false,duplicated_digits:false,fused_digits:true,contour_failure:true,wrist_or_arm_discontinuity:false,non_anatomical_texture:true};
assert.equal(portraitObservation(review,'digits').state,'recorded');
assert.equal(portraitObservation(review,'digits').rows.length,4);
assert.equal(portraitObservation(review,'wrist').state,'not-recorded');
assert.deepEqual(portraitObservation(review,'contour').rows.map(r=>r.key),['contour_failure']);
assert.deepEqual(portraitObservation(review,'texture').rows.map(r=>r.key),['non_anatomical_texture']);
assert.equal(portraitObservation({},'wrist').state,'unavailable');
assert.throws(()=>portraitObservation(review,'invented'));
const catalogue=[
  {blind_review_code:'R005',painting_id:'p269',overall_anatomy_failure:true},
  {blind_review_code:'R006',painting_id:'p269',overall_anatomy_failure:true},
  {blind_review_code:'R007',painting_id:'p271',overall_anatomy_failure:true},
  {blind_review_code:'R002',painting_id:'p260',overall_anatomy_failure:false},
  {blind_review_code:'R003',painting_id:'p260',overall_anatomy_failure:false},
  {blind_review_code:'R013',painting_id:'p284',overall_anatomy_failure:false}
];
const snapshot=JSON.stringify(catalogue);
assert.equal(portraitNextReview(catalogue,'R005',true).blind_review_code,'R007');
assert.equal(portraitNextReview(catalogue,'R005',false).blind_review_code,'R002');
assert.equal(portraitNextReview(catalogue,'R002',false).blind_review_code,'R013');
assert.equal(portraitNextReview(catalogue.slice(0,1),'R005',true),null);
assert.equal(JSON.stringify(catalogue),snapshot);
const row=(metric,low,high)=>({metric_name:metric,interval_low:low,interval_high:high});
const associations=[row('chroma',-2,-1),row('chroma',-1,-.1),row('chroma',-.9,-.01),row('chroma',-.5,.5),...Array.from({length:4},()=>row('mae',-.4,.3))];
assert.deepEqual(portraitLightnessSummary(associations,'chroma'),{negative:3,positive:0,uncertain:1,total:4,reading:'Negative association in 3/4 methods.'});
assert.equal(portraitLightnessSummary(associations,'mae').reading,'No clear association in 4/4 methods.');
assert.equal(portraitLightnessSummary([row('x',0,1)],'x').uncertain,1);
assert.equal(portraitLightnessSummary([row('x',1,2)],'x').positive,1);
assert.throws(()=>portraitLightnessSummary([], 'x'));
console.log('Distinct observation fields, review transitions and metric-specific interpretations passed.');
