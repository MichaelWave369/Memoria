import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {evaluate} from './benchmark.mjs';

const read = name => JSON.parse(readFileSync(new URL(name, import.meta.url), 'utf8'));
const fixture = read('fixture-v1.json');
const frozen = read('results-v1.json');
const actual = evaluate(fixture);
assert.equal(fixture.documents.length, 12);
assert.equal(fixture.queries.length, 24);
assert.equal(actual.rows.length, 120);
assert.deepEqual(actual, frozen);
for (const method of Object.values(actual.summary)) {
  assert.equal(method.positives, 18);
  assert.equal(method.negatives, 6);
  assert.equal(method.cost.candidate_comparisons, 288);
  assert.equal(method.false_accepts, 3);
}
assert.equal(actual.summary.relational_jaccard.by_family.alias.hit1, 6);
assert.equal(actual.summary.shuffled_relational.by_family.alias.hit1, 0);
assert.equal(actual.summary.shuffled_relational.by_family.alias.abstentions, 0);
assert.equal(actual.authority, 'NONE');
console.log(JSON.stringify(actual.summary, null, 2));
