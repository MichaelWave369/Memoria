import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {evaluate} from './abstention.mjs';
const read=name=>JSON.parse(readFileSync(new URL(name,import.meta.url),'utf8'));
const fixture=read('abstention-fixture-v1.json');
const frozen=read('abstention-results-v1.json');
assert.equal(fixture.calibration.queries.length,12);
assert.equal(fixture.evaluation.queries.length,36);
assert.deepEqual(evaluate(fixture),frozen);
for(const key of ['direct','relational']) assert.equal(frozen.calibration[key].grid.length,18);
for(const result of Object.values(frozen.evaluation)){
 const m=result.metrics;
 assert.equal(m.correct+m.wrong+m.abstain_positive,20);
 assert.equal(m.false_accept+m.abstain_negative,16);
 assert.equal(m.admitted,m.correct+m.wrong+m.false_accept);
}
const g=frozen.evaluation.guarded_relational;
assert.equal(g.metrics.correct,20);
assert.equal(g.metrics.false_accept,2);
assert.equal(g.metrics.by_family.ambiguous.abstain,6);
assert.equal(g.metrics.by_family.misleading.false_accept,2);
assert.equal(frozen.evaluation.always_abstain.metrics.selective_error,null);
// Verify evaluation labels cannot alter selected calibration gates.
const altered=structuredClone(fixture);
for(const q of altered.evaluation.queries) q.target=null;
assert.deepEqual(evaluate(altered).calibration,frozen.calibration);
console.log(JSON.stringify(Object.fromEntries(Object.entries(frozen.evaluation).map(([k,v])=>[k,v.metrics])),null,2));
