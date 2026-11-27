import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {resolveRelation,evaluate} from './provenance.mjs';

const read=name=>JSON.parse(readFileSync(new URL(name,import.meta.url),'utf8'));
const fixture=read('provenance-fixture-v1.json');
const frozen=read('provenance-results-v1.json');
assert.deepEqual(evaluate(fixture,resolveRelation),frozen);
assert.deepEqual(frozen.summary,{scenarios:18,contract_matches:18,admitted:4,correct_admissions:3,wrong_admissions:1,abstentions:14});
for(const s of fixture.scenarios){
  const result=resolveRelation(s.records,s.request,s.withdrawn);
  assert.deepEqual(resolveRelation([...s.records].reverse(),s.request,[...s.withdrawn].reverse()),result);
  assert.equal(result.authority,'NONE');
}
const base=fixture.scenarios[0];
const run=(records=base.records,request=base.request,withdrawn=[])=>resolveRelation(records,request,withdrawn);
assert.throws(()=>run([...base.records,base.records[0]]),TypeError);
assert.throws(()=>run([{...base.records[0],review:'unknown'}]),TypeError);
assert.throws(()=>run([{...base.records[0],expires:10}]),TypeError);
assert.throws(()=>run([{...base.records[0],extra:true}]),TypeError);
assert.throws(()=>run(base.records,{...base.request,now:-1}),TypeError);
assert.throws(()=>run(base.records,{...base.request,app:'*'}),TypeError);
assert.throws(()=>run(base.records,base.request,['root:a','root:a']),TypeError);
assert.throws(()=>run(Array(129).fill(base.records[0])),TypeError);
assert.equal(run(base.records,{...base.request,now:10}).target,'router');
assert.equal(run(base.records,{...base.request,now:20}).reason,'NO_CURRENT_EVIDENCE');
assert.equal(run(base.records,base.request,['root:a','root:b']).target,null);
// Truth labels are scoring-only; changing them cannot alter admission.
const relabeled=structuredClone(fixture);
for(const s of relabeled.scenarios){s.truth='unrelated';s.expected=null;}
const withoutLabels=rows=>rows.map(({truth,expected,...row})=>row);
assert.deepEqual(withoutLabels(evaluate(relabeled,resolveRelation).rows),withoutLabels(frozen.rows));
console.log(JSON.stringify(frozen.summary,null,2));
