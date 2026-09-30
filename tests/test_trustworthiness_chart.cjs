// Fast, dependency-free presentation tests; no evidence-table loads or browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../streamlit_assets/trustworthiness_controller.js'), 'utf8');
const chartSource = source.slice(source.indexOf('    function drawChart(t)'), source.indexOf('    function updateWall()'));
const doc = {createElementNS(namespaceURI, tag) {
  return {namespaceURI, tag, attrs:{}, children:[], setAttribute(k,v){this.attrs[k]=String(v);}, append(n){this.children.push(n);}};
}};
const draw = vm.runInNewContext(chartSource + '\ndrawChart', {
  doc, fmt:n=>Number.isFinite(n)?n.toFixed(2):'Unavailable', plain:s=>String(s).replaceAll('_',' ')
});
const base = {indicator:'local_texture_error_p95', observed:.4709723085165021, warning:1.7923734879493693, critical:4.8924025321006255, direction:'higher_is_worse', state:'none'};
for (const record of [base, {...base, observed:10.053275680541985, state:'critical'}, {...base, warning:4.8}, {...base, indicator:'other', observed:-2, warning:-1, critical:-3, direction:'lower_is_worse'}]) {
  const before = JSON.stringify(record), svg = draw(record);
  assert.equal(JSON.stringify(record), before, 'Rendering must not mutate recorded evidence');
  assert.ok(svg.attrs['aria-label'].includes(String(record.observed)), 'Keep full precision in accessible evidence');
  assert.ok(svg.children.some(n=>n.textContent===record.observed.toFixed(2)), 'Badge uses this candidate, not reference numbers');
  for (const n of svg.children) for (const key of ['x','y','width','height','x1','x2','y1','y2','cx','cy']) {
    if(key in n.attrs) assert.ok(Number.isFinite(Number(n.attrs[key])), `Finite ${key}`);
    if(key==='width' && key in n.attrs) assert.ok(Number(n.attrs[key])>=0, 'Shading width cannot be negative');
  }
  assert.ok(!svg.children.some(n=>String(n.textContent).includes('50th')), 'Do not invent a median');
  for(const kind of ['warning','critical']) {
    const pointer=svg.children.find(n=>n.attrs['data-cutoff-pointer']===kind);
    const value=svg.children.find(n=>n.attrs['data-cutoff-value']===kind);
    const name=svg.children.find(n=>n.attrs['data-cutoff-name']===kind);
    assert.equal(Number(pointer.attrs['data-value']), record[kind]);
    assert.equal(Number(pointer.attrs.d.split(' ')[1]), Number(value.attrs.x), 'Value sits exactly below its pointer');
    assert.equal(value.textContent, record[kind].toFixed(2));
    assert.equal(value.attrs.fill, pointer.attrs.fill, 'Pointer and value share the threshold color');
    assert.equal(name.attrs.x,value.attrs.x);
  }
}
for (const missing of [null, {...base, observed:null}]) {
  assert.ok(draw(missing).children.some(n=>n.textContent==='Required evidence unavailable'));
}
console.log('Threshold chart checks passed: current/critical/lower-direction cases, missing evidence, numeric geometry, immutable values.');
