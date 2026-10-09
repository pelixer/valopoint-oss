import { createEngine } from './engine.js';

export const app = $state({ model: null, engine: null, brackets: [], bracketsAt: null, ledger: [], error: null, route: parse() });

function parse() {
  const [path, qs] = location.hash.replace(/^#\/?/, '').split('?');
  const [page, ...rest] = path.split('/');
  const query = Object.fromEntries(new URLSearchParams(qs ?? ''));
  // the old match tab now lives in the bracket tab ("자유 대결")
  if (page === 'match') return { page: 'bracket', arg: null, query: { mode: 'free', ...query } };
  return { page: page || 'home', arg: rest.map(decodeURIComponent).join('/') || null, query };
}

window.addEventListener('hashchange', () => {
  const prev = app.route;
  app.route = parse();
  // switching modes inside one page keeps the scroll position
  if (prev.page !== app.route.page || prev.arg !== app.route.arg) window.scrollTo(0, 0);
});

export async function loadModel() {
  try {
    const res = await fetch(`./data/model.json?t=${Date.now()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const model = await res.json();
    app.model = model;
    app.engine = createEngine(model);
    app.brackets = model.brackets ?? [];
    // live bracket (refreshed twice a day, independently of the model)
    try {
      const b = await fetch(`./data/brackets.json?t=${Date.now()}`);
      if (b.ok) {
        const bj = await b.json();
        if (bj.brackets?.length) { app.brackets = bj.brackets; app.bracketsAt = bj.generated_at; }
      }
    } catch {}
    // append-only record of pre-match predictions
    try {
      const l = await fetch(`./data/ledger.json?t=${Date.now()}`);
      if (l.ok) {
        // team names renamed by a data source change (old -> new), per bracket
        const al = Object.assign({}, ...app.brackets.map((b) => b.aliases ?? {}));
        const rn = (t) => al[t] ?? t;
        app.ledger = (await l.json()).map((e) => (e.team_a in al || e.team_b in al ? { ...e, team_a: rn(e.team_a), team_b: rn(e.team_b) } : e));
      }
    } catch {}
  } catch (e) {
    app.error = String(e);
  }
}

// small persisted per-device settings (locked bracket results etc.)
export function persisted(key, init) {
  let v = init;
  try { const s = localStorage.getItem(key); if (s) v = JSON.parse(s); } catch {}
  return {
    get: () => v,
    set: (nv) => { v = nv; try { localStorage.setItem(key, JSON.stringify(nv)); } catch {} },
  };
}

// per-page view state kept while moving around the app (and in this tab after a reload)
export function viewState(key, init) {
  let v = init;
  try { const s = sessionStorage.getItem(`view:${key}`); if (s) v = { ...init, ...JSON.parse(s) }; } catch {}
  return {
    get: () => v,
    set: (nv) => { v = nv; try { sessionStorage.setItem(`view:${key}`, JSON.stringify(nv)); } catch {} },
  };
}
