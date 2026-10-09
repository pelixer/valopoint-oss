// My bracket (design v2 · 4a): my winner picks for a whole event, locked at each
// match's start time and scored against official results. Stored on this device only.
// Pure functions here; the page keeps the state.
import { groupOf } from './bracket.js';

/** A match is locked once it has started (or already has a result). */
export const isLocked = (m, results, now = Date.now()) =>
  !!results?.[m.id] || (!!m.time && now >= Date.parse(m.time));

/** "그룹 A 최종전" → "A조 최종전", "상위 8강" stays. */
export function shortRound(m) {
  return (m.round ?? m.id).replace(/^그룹 ([A-H]) /, '$1조 ');
}

/** Match titles that tell same-round matches apart: "상위 8강 3", "A조 오프닝 1", "결승". */
export function matchTitles(br) {
  const byRound = {};
  for (const m of br.matches) (byRound[shortRound(m)] ??= []).push(m.id);
  const out = {};
  for (const [r, ids] of Object.entries(byRound)) ids.forEach((id, i) => (out[id] = ids.length > 1 ? `${r} ${i + 1}` : r));
  return out;
}

const label = (ref, titles) => {
  const m = /^([WL]):(.+)$/.exec(ref);
  if (!m) return ref;
  return `${titles[m[2]] ?? m[2]} ${m[1] === 'W' ? '승자' : '패자'}`;
};

/**
 * Teams in every slot of my bracket.
 * Each side: {t: name|null, kind: 'fixed' | 'pred' | 'tbd', label, waiting}
 *   fixed = decided by seeds/official results, pred = filled by my own pick of the
 *   feeding match, tbd = unknown (feeding match not picked, or started and no result yet).
 */
export function slots(br, picks = {}, now = Date.now()) {
  const results = br.results ?? {};
  const byId = Object.fromEntries(br.matches.map((m) => [m.id, m]));
  const titles = matchTitles(br);
  const out = {};
  const side = (ref) => {
    const r = /^([WL]):(.+)$/.exec(ref);
    if (!r) {
      const s = /^S(\d+)$/.exec(ref);
      return { t: s ? br.teams[Number(s[1]) - 1] : ref, kind: 'fixed' };
    }
    const [, wl, src] = r;
    const pair = out[src];
    const lbl = label(ref, titles);
    if (!pair || !byId[src]) return { t: null, kind: 'tbd', label: lbl };
    const both = pair.a.t && pair.b.t;
    const winner = results[src];
    if (winner) {
      // official result: winner by name, loser = the other official team
      const w = winner;
      const l = both ? (pair.a.t === w ? pair.b.t : pair.a.t) : null;
      const t = wl === 'W' ? w : l;
      return t ? { t, kind: 'fixed' } : { t: null, kind: 'tbd', label: lbl };
    }
    if (isLocked(byId[src], results, now)) return { t: null, kind: 'tbd', label: lbl, waiting: true };
    const p = picks[src];
    if (!both || !p || (p !== pair.a.t && p !== pair.b.t)) return { t: null, kind: 'tbd', label: lbl };
    const t = wl === 'W' ? p : (p === pair.a.t ? pair.b.t : pair.a.t);
    return { t, kind: 'pred' };
  };
  for (const m of br.matches) out[m.id] = { a: side(m.a), b: side(m.b) };
  return out;
}

/** Teams eliminated by official results (lost a match with no later match for them). */
function eliminated(br, sl) {
  const out = new Set();
  const results = br.results ?? {};
  const feeds = new Set(br.matches.flatMap((m) => [m.a, m.b]).filter((r) => /^L:/.test(r)).map((r) => r.slice(2)));
  for (const m of br.matches) {
    const w = results[m.id];
    const { a, b } = sl[m.id];
    if (!w || !a.t || !b.t) continue;
    const loser = w === a.t ? b.t : a.t;
    if (!feeds.has(m.id)) out.add(loser);
  }
  return out;
}

/**
 * State of every match in my bracket:
 *   open | pick | tbd | wait | noresp | hit | miss | void
 * void = my picked team can no longer be in this match (eliminated earlier).
 */
export function states(br, picks = {}, now = Date.now()) {
  const sl = slots(br, picks, now);
  const results = br.results ?? {};
  const out = {};
  const gone = eliminated(br, sl);
  for (const m of br.matches) {
    const { a, b } = sl[m.id];
    const p = picks[m.id];
    const inPair = p && (p === a.t || p === b.t);
    const known = a.t && b.t;
    const w = results[m.id];
    let st;
    if (w) st = !p ? 'noresp' : p === w ? 'hit' : inPair ? 'miss' : 'void';
    else if (isLocked(m, results, now)) st = !p ? 'noresp' : (known && !inPair) || gone.has(p) ? 'void' : 'wait';
    // not started: void only when the picked team is out (eliminated, or both teams are
    // known and it is not one of them); with an open slot it may still arrive
    else if (p && (gone.has(p) || (known && !inPair))) st = 'void';
    else if (!known) st = p ? 'pick' : 'tbd';
    else st = p ? 'pick' : 'open';
    out[m.id] = st;
  }
  return { slots: sl, states: out };
}

/**
 * After changing a pick, later picks that no longer fit their match are cleared
 * (only for matches that are not locked yet). Returns {picks, cleared: [matchId]}.
 */
export function prune(br, picks, now = Date.now()) {
  const next = { ...picks };
  const cleared = [];
  for (let pass = 0; pass < 4; pass++) {
    const sl = slots(br, next, now);
    let changed = false;
    for (const m of br.matches) {
      const p = next[m.id];
      if (!p || isLocked(m, br.results, now)) continue;
      const { a, b } = sl[m.id];
      // a pick is kept while its team is in the slot, or while a feeding match is
      // started and waiting for its result (it cannot be judged yet)
      const fits = p === a.t || p === b.t || a.waiting || b.waiting;
      if (!fits) {
        delete next[m.id];
        cleared.push(m.id);
        changed = true;
      }
    }
    if (!changed) break;
  }
  return { picks: next, cleared };
}

/** Toggle a pick on an unlocked match, then prune dependent picks. */
export function choose(br, picks, matchId, team, now = Date.now()) {
  const m = br.matches.find((x) => x.id === matchId);
  if (!m || isLocked(m, br.results, now)) return { picks, cleared: [] };
  const next = { ...picks };
  if (next[matchId] === team) delete next[matchId];
  else next[matchId] = team;
  return prune(br, next, now);
}

/** Stages for navigation: group letters, then U, L, F (order of first appearance). */
export function stages(br) {
  const seen = new Map();
  for (const m of br.matches) {
    const g = groupOf(m);
    if (!seen.has(g.key)) seen.set(g.key, { ...g, ids: [] });
    seen.get(g.key).ids.push(m.id);
  }
  return [...seen.values()];
}

/**
 * Model pick per match, frozen at lock time:
 *   snapshot taken on this device while the match was still open, else the
 *   append-only ledger's last pre-match record, else the accuracy check's pre-match value.
 * Returns {team, p} or null.
 */
export function modelPick({ snap, ledger, preMatch }) {
  if (snap) return snap;
  if (ledger) return { team: ledger.p >= 0.5 ? ledger.team_a : ledger.team_b, p: Math.max(ledger.p, 1 - ledger.p) };
  if (preMatch) return { team: preMatch.p >= 0.5 ? preMatch.team_a : preMatch.team_b, p: Math.max(preMatch.p, 1 - preMatch.p) };
  return null;
}

/**
 * Me vs model on matches with a result that I picked (no-response matches excluded).
 * model: {matchId: {team}} frozen picks.
 */
export function score(br, picks, model, now = Date.now()) {
  const { states: st } = states(br, picks, now);
  // one set for both sides: result in, I picked, and the model's frozen pick is known
  let n = 0, me = 0, mdl = 0, voids = 0, noModel = 0, noresp = 0;
  for (const m of br.matches) {
    const w = br.results?.[m.id];
    if (!w) continue;
    if (!picks[m.id]) { noresp++; continue; }
    if (!model[m.id]) { noModel++; continue; }
    n++;
    if (st[m.id] === 'hit') me++;
    if (st[m.id] === 'void') voids++;
    if (model[m.id].team === w) mdl++;
  }
  const picked = br.matches.filter((m) => picks[m.id]).length;
  return { n, me, model: mdl, modelN: n, voids, noModel, noresp, picked, total: br.matches.length, results: Object.keys(br.results ?? {}).length };
}

/** My picks vs the model's current/frozen picks: {same, diff} over matches where both exist. */
export function agreement(picks, model) {
  let same = 0, diff = 0;
  for (const [id, t] of Object.entries(picks)) {
    if (!model[id]) continue;
    if (model[id].team === t) same++; else diff++;
  }
  return { same, diff };
}

/** Earliest unlocked match without a pick (the next deadline). */
export function nextDeadline(br, picks, now = Date.now()) {
  return br.matches
    .filter((m) => m.time && !picks[m.id] && !isLocked(m, br.results, now))
    .sort((a, b) => a.time.localeCompare(b.time))[0] ?? null;
}

/** My champion: pick of the final match. */
export const champion = (br, picks) => picks[br.final ?? 'GF'] ?? null;
