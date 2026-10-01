const test=require('node:test');
const assert=require('node:assert/strict');
const {archiveFilter,archiveSafeURL,archiveURL}=require('../streamlit_assets/research_archive_controller.js');
test('search is literal, case-insensitive, and requires every term',()=>{
 const rows=[{id:'N33',title:'Final evaluation'},{id:'D01',title:'Frozen pilot decision'}];
 assert.deepEqual(archiveFilter(rows,'N33 FINAL'),[rows[0]]);
 assert.deepEqual(archiveFilter(rows,'not present'),[]);
 assert.equal(archiveFilter(rows,'').length,2);
 assert.equal(archiveFilter(rows,'.*').length,0);
});
test('source links reject active-content schemes',()=>{
 for(const url of ['javascript:alert(1)','data:text/html,bad','file:///C:/private','not a url'])assert.equal(archiveSafeURL(url),null);
 assert.equal(archiveSafeURL('https://example.org/source'),'https://example.org/source');
});
test('Archive navigation stays same-room and encodes exact identity',()=>{
 const query=new URLSearchParams(archiveURL({record:'N33',file:'outputs/a&b.json',view:null}).slice(1));
 assert.equal(query.get('room'),'research_archive');
 assert.equal(query.get('ar_file'),'outputs/a&b.json');
 assert.equal(query.has('ar_view'),false);
});
