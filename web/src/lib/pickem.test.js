import test from 'node:test';
import assert from 'node:assert/strict';
import { slots, states, choose, prune, score, nextDeadline, stages, modelPick, champion } from './pickem.js';

// one GSL group (4 teams) feeding a final against a seeded team
const T0 = Date.parse('2026-01-10T00:00:00Z');
const at = (h) => new Date(T0 + h * 3600e3).toISOString();
const br = (results = {}) => ({
  id: 't', teams: ['A', 'B', 'C', 'D', 'E'], final: 'GF', results,
  matches: [
    { id: 'A-O1', a: 'S1', b: 'S2', round: '그룹 A 오프닝', time: at(10) },
    { id: 'A-O2', a: 'S3', b: 'S4', round: '그룹 A 오프닝', time: at(12) },
    { id: 'A-W', a: 'W:A-O1', b: 'W:A-O2', round: '그룹 A 승자전', time: at(30) },
    { id: 'A-E', a: 'L:A-O1', b: 'L:A-O2', round: '그룹 A 패자전', time: at(32) },
    { id: 'A-D', a: 'L:A-W', b: 'W:A-E', round: '그룹 A 최종전', time: at(50) },
    { id: 'GF', a: 'W:A-W', b: 'S5', round: '결승', time: at(80) },
  ],
});
const before = T0; // nothing started

test('picks fill later slots as predicted teams', () => {
  const p = { 'A-O1': 'A', 'A-O2': 'D' };
  const sl = slots(br(), p, before);
  assert.deepEqual([sl['A-W'].a.t, sl['A-W'].a.kind, sl['A-W'].b.t], ['A', 'pred', 'D']);
  assert.deepEqual([sl['A-E'].a.t, sl['A-E'].b.t], ['B', 'C']);
  assert.equal(sl['A-D'].a.kind, 'tbd');
  assert.equal(sl['A-D'].a.label, 'A조 승자전 패자');
  assert.equal(slots(br(), {}, before)['A-W'].a.label, 'A조 오프닝 1 승자');
  assert.equal(sl['GF'].b.kind, 'fixed');
});

test('changing an earlier pick clears picks that no longer fit', () => {
  let p = { 'A-O1': 'A', 'A-O2': 'D', 'A-W': 'A', 'GF': 'A' };
  const r = choose(br(), p, 'A-O1', 'B', before);
  assert.equal(r.picks['A-O1'], 'B');
  assert.equal(r.picks['A-W'], undefined);
  assert.equal(r.picks['GF'], undefined);
  assert.deepEqual(r.cleared.sort(), ['A-W', 'GF']);
  // tapping the same team again removes the pick
  assert.equal(choose(br(), r.picks, 'A-O1', 'B', before).picks['A-O1'], undefined);
});

test('locked matches cannot change and are scored', () => {
  const p = { 'A-O1': 'A', 'A-O2': 'D', 'A-W': 'A' };
  const b = br({ 'A-O1': 'A', 'A-O2': 'C' });
  const now = Date.parse(at(13));
  assert.deepEqual(choose(b, p, 'A-O1', 'B', now).picks, p);
  const { states: st, slots: sl } = states(b, p, now);
  assert.equal(st['A-O1'], 'hit');
  assert.equal(st['A-O2'], 'miss');
  // my A-W pick A still fits (A really won); the other side is now official C
  assert.equal(sl['A-W'].b.t, 'C');
  assert.equal(sl['A-W'].b.kind, 'fixed');
  assert.equal(st['A-W'], 'pick');
  // D lost the opener: a pick of D in the loser's match stays valid, but a pick of D to win the group is void
  const st2 = states(b, { ...p, 'A-W': 'D' }, now).states;
  assert.equal(st2['A-W'], 'void');
});

test('a started match without result makes the next slot wait, not clear', () => {
  const p = { 'A-O1': 'A', 'A-O2': 'D', 'A-W': 'A', 'GF': 'A' };
  const now = Date.parse(at(31)); // A-W started, no result
  const sl = slots(br({ 'A-O1': 'A', 'A-O2': 'D' }), p, now);
  assert.equal(sl['GF'].a.kind, 'tbd');
  assert.equal(sl['GF'].a.waiting, true);
  assert.deepEqual(prune(br({ 'A-O1': 'A', 'A-O2': 'D' }), p, now).cleared, []);
  assert.equal(states(br({ 'A-O1': 'A', 'A-O2': 'D' }), p, now).states['A-W'], 'wait');
});

test('an open slot keeps a downstream pick pending, not void', () => {
  // A-O1 decided (A won), A-O2 not picked yet: GF pick A waits for A-W to be decided
  const b = br({ 'A-O1': 'A' });
  const p = { 'A-O1': 'A', GF: 'D' };
  const st = states(b, p, Date.parse(at(11))).states;
  assert.equal(st.GF, 'pick');
});

test('no-response matches are left out of the score; model compared on the same set', () => {
  const b = br({ 'A-O1': 'A', 'A-O2': 'C', 'A-W': 'A' });
  const p = { 'A-O1': 'A', 'A-W': 'C' };
  const s = score(b, p, { 'A-O1': { team: 'B' }, 'A-W': { team: 'A' }, 'A-O2': { team: 'C' } }, Date.parse(at(40)));
  assert.deepEqual([s.n, s.me, s.model, s.modelN, s.noresp, s.picked, s.results], [2, 1, 1, 2, 1, 2, 3]);
  // a match without a frozen model pick leaves both denominators
  const s2 = score(b, p, { 'A-O1': { team: 'B' } }, Date.parse(at(40)));
  assert.deepEqual([s2.n, s2.modelN, s2.noModel], [1, 1, 1]);
});

test('deadline, stages, champion, model pick fallback', () => {
  const p = { 'A-O1': 'A' };
  assert.equal(nextDeadline(br(), p, before).id, 'A-O2');
  assert.deepEqual(stages(br()).map((s) => s.key), ['A', 'GF']);
  assert.equal(champion(br(), { GF: 'E' }), 'E');
  assert.deepEqual(modelPick({ ledger: { team_a: 'A', team_b: 'B', p: 0.3 } }), { team: 'B', p: 0.7 });
  assert.deepEqual(modelPick({ snap: { team: 'A', p: 0.6 }, ledger: { team_a: 'A', team_b: 'B', p: 0.3 } }), { team: 'A', p: 0.6 });
  assert.equal(modelPick({}), null);
});
