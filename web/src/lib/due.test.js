import test from 'node:test';
import assert from 'node:assert/strict';
import { regularHour, resultsDue } from '../../worker/due.js';

test('results are due 75 min after the start until they arrive (48 h at most)', () => {
  const now = Date.parse('2026-10-09T12:00:00Z');
  const t = (h) => new Date(now - h * 3600e3).toISOString();
  const br = [{ name: 'X', results: { c: 'A' }, matches: [
    { id: 'a', time: t(2) }, { id: 'b', time: t(0.5) }, { id: 'c', time: t(3) }, { id: 'd', time: t(72) }, { id: 'e', time: t(-2) }] }];
  assert.deepEqual(resultsDue(br, now), ['X: a']);
  assert.equal(regularHour(Date.parse('2026-10-09T06:17:00Z')), true);
  assert.equal(regularHour(Date.parse('2026-10-09T07:17:00Z')), false);
});
