<script>
  import { app, persisted } from '../lib/store.svelte.js';
  import { simulateBracket } from '../lib/engine.js';
  import { fx, kst, pct } from '../lib/format.js';
  import { groupOf, groupTable, resolveTeams } from '../lib/bracket.js';
  import MatchCard from '../lib/MatchCard.svelte';
  import FreeMatch from '../lib/FreeMatch.svelte';
  import MyBracket from '../lib/MyBracket.svelte';

  let free = $derived(app.route.query?.mode === 'free');
  let mineMode = $derived(app.route.query?.mode === 'mine');

  const store = persisted('bracket-locks', {});
  let idx = $state(0);
  let br = $derived(app.brackets[idx]);
  // official results from the data source + my own what-if locks
  let mine = $state(store.get());
  let myLocks = $derived(br ? Object.keys(mine[br.id] ?? {}).filter((k) => !br.results?.[k]) : []);
  let locked = $derived(br ? { ...(br.results ?? {}), ...(mine[br.id] ?? {}) } : {});
  let full = $derived(br?.kind === 'full' || br?.kind === undefined);
  let sim = $derived(br && br.matches.length && !free && !mineMode ? simulateBracket(app.engine, br, locked, 20000) : null);
  let odds = $derived(sim ? Object.entries(sim.champion).sort((a, b) => b[1] - a[1]).slice(0, 10) : []);
  let done = $derived(br ? Object.keys(br.results ?? {}).length : 0);
  let ev = $derived(app.model.event_eval);
  // pre-match predictions (from the accuracy check) for matches already played
  let preMatch = $derived(Object.fromEntries((ev?.matches ?? []).map((m) => [m.match_id, m])));
  function preP(m, team) {
    const e = preMatch[String(m.match_id ?? m.vlr_id)];
    if (!e) return null;
    return team === e.team_a ? e.p : 1 - e.p;
  }

  let fixed = $derived(br ? resolveTeams(br, locked) : {});
  const view = persisted('bracket-view', { mode: 'time', filter: 'ALL' });
  let mode = $state(view.get().mode);
  let filter = $state(view.get().filter);
  $effect(() => view.set({ mode, filter }));
  let groups = $derived.by(() => {
    const seen = new Map();
    for (const m of br?.matches ?? []) { const g = groupOf(m); if (!seen.has(g.key)) seen.set(g.key, g); }
    return [...seen.values()];
  });
  // a stored filter from an older version may name a group that no longer exists
  $effect(() => { if (filter !== 'ALL' && groups.length && !groups.some((g) => g.key === filter)) filter = 'ALL'; });
  let visible = $derived((br?.matches ?? []).filter((m) => filter === 'ALL' || groupOf(m).key === filter));

  // matches in the order they are (or were) played, grouped by KST date
  const dayKey = (iso) => iso ? new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', month: 'long', day: 'numeric', weekday: 'short' }).format(new Date(iso)) : '일정 미정';
  let days = $derived.by(() => {
    const ms = [...visible].sort((x, y) => (x.time ?? '9999').localeCompare(y.time ?? '9999'));
    const g = [];
    for (const m of ms) {
      const d = dayKey(m.time);
      const last = g.at(-1);
      if (last && last.day === d) last.items.push(m);
      else g.push({ day: d, items: [m] });
    }
    return g;
  });

  function lock(mid, team) {
    if (br.results?.[mid]) return;
    const cur = { ...(mine[br.id] ?? {}) };
    if (cur[mid] === team) delete cur[mid];
    else cur[mid] = team;
    mine = { ...mine, [br.id]: cur };
    store.set(mine);
  }
  // copy my bracket's picks into the what-if locks (open matches only)
  let myPicks = $derived(br ? (persisted('mybracket', {}).get()[br.id]?.picks ?? {}) : {});
  function fromMyBracket() {
    const cur = {};
    for (const [mid, t] of Object.entries(myPicks)) if (!br.results?.[mid]) cur[mid] = t;
    mine = { ...mine, [br.id]: cur };
    store.set(mine);
  }
  function reset() {
    mine = { ...mine, [br.id]: {} };
    store.set(mine);
  }
  let showAll = $state(false);
  let evMatches = $derived(ev?.matches ? [...ev.matches].reverse() : []);
</script>

<div class="modes" role="tablist" aria-label="대진 모드">
  <a href="#/bracket" class:on={!free && !mineMode} role="tab" aria-selected={!free && !mineMode}>대회</a>
  <a href="#/bracket?mode=mine" class:on={mineMode} role="tab" aria-selected={mineMode}>내 대진표</a>
  <a href="#/bracket?mode=free" class:on={free} role="tab" aria-selected={free}>자유 대결</a>
</div>

{#if free}
  {#key app.route.query?.a}<FreeMatch preset={app.route.query?.a ?? null} />{/key}
{:else if mineMode}
  <MyBracket />
{:else if !app.brackets.length}
  <p class="note">아직 불러온 대진이 없습니다. 진행 중인 국제전이 있으면 자동으로 표시됩니다.</p>
{:else}
  {#if app.brackets.length > 1}
    <select bind:value={idx} style="margin-top:10px">
      {#each app.brackets as b, i}<option value={i}>{b.name}</option>{/each}
    </select>
  {/if}
  <section class="head">
    <span class="corner tr"></span>
    <div class="kicker">Bracket · 20,000 sims</div>
    <div class="name disp">{br.name}</div>
    <div class="prog">
      <!-- in time order: finished, started without a result yet, upcoming -->
      <div class="segs">{#each [...br.matches].sort((x, y) => (x.time ?? '').localeCompare(y.time ?? '')) as m}<span class:on={!!br.results?.[m.id]} class:wait={!br.results?.[m.id] && m.time && Date.parse(m.time) <= Date.now()}></span>{/each}</div>
      <span class="num">{done}<em>/{br.matches.length}</em></span>
    </div>
    <div class="note">{#if app.bracketsAt}대진 갱신 {kst(app.bracketsAt)} · {/if}20,000회 시뮬레이션</div>
    {#if br.assumed?.length}<div class="assumed"><i></i><span>플레이오프 대진({br.assumed.join(', ')})은 조별 순위 기반 추정이며, 확정되면 자동으로 바뀝니다.</span></div>{/if}
  </section>

  {#if full && odds.length}
    <div class="sec"><div><span class="k">Title chances</span><span class="t">우승 확률</span></div><span class="side" class:mine={myLocks.length}>{myLocks.length ? '내 가정 섞임 · 재계산됨' : '공식 결과 기준'}</span></div>
    <div class="card odds">
      {#each odds as [t, p], i}
        <div class="odd">
          <span class="num r" class:first={i === 0}>{i + 1}</span>
          <span class="disp t">{t}</span>
          <div class="ob"><i style="width:{((p / odds[0][1]) * 100).toFixed(1)}%" class:first={i === 0}></i></div>
          <span class="num p">{pct(p, 1)}</span>
        </div>
      {/each}
    </div>
  {/if}

  <div class="sec" style="margin-bottom:10px"><div><span class="k">Matches · {br.matches.length}</span><span class="t">경기</span></div></div>
  <div class="ctl">
    <div class="seg2" role="group" aria-label="보기">
      <button class:on={mode === 'time'} onclick={() => (mode = 'time')}>시간순</button>
      <button class:on={mode === 'group'} onclick={() => (mode = 'group')}>그룹별</button>
    </div>
    <button class="reset" class:live={myLocks.length} disabled={!myLocks.length} onclick={reset}>내 가정 초기화{myLocks.length ? ` (${myLocks.length})` : ''}</button>
  </div>
  <div class="ctl2">
    {#if Object.keys(myPicks).length}<button class="fill" onclick={fromMyBracket}>◆ 내 대진표 픽으로 가정 채우기</button>{/if}
  </div>
  <div class="chips" role="group" aria-label="그룹 필터">
    <button class="chip" class:on={filter === 'ALL'} onclick={() => (filter = 'ALL')}><span>전체</span></button>
    {#each groups as g}
      <button class="chip" class:on={filter === g.key} onclick={() => (filter = g.key)}><span><i class="gdot" style="background:{filter === g.key ? 'var(--accent-ink)' : g.color}"></i>{g.label}</span></button>
    {/each}
  </div>
  <p class="note" style="margin:4px 0 12px">팀 버튼을 누르면 그 팀이 이긴다고 가정해 이후 확률을 다시 계산합니다(내 기기에만 저장).</p>

  {#snippet card(m)}
    <MatchCard {m} bid={br.id} group={groupOf(m)} teams={fixed[m.id]} official={br.results?.[m.id]} mine={mine[br.id]?.[m.id]}
      projected={sim?.slot?.[m.id]} {preP} onlock={(t) => lock(m.id, t)} />
  {/snippet}

  {#if mode === 'time'}
    {#each days as d}
      <div class="dayhead">{d.day}</div>
      {#each d.items as m (m.id)}{@render card(m)}{/each}
    {/each}
  {:else}
    {#each groups.filter((g) => filter === 'ALL' || g.key === filter) as g}
      {@const items = br.matches.filter((m) => groupOf(m).key === g.key).sort((x, y) => (x.time ?? '9999').localeCompare(y.time ?? '9999'))}
      {@const table = /^[A-H]$/.test(g.key) ? groupTable(br, g.key) : []}
      <section class="gblock">
        <div class="gtitle"><i style="background:{g.color}"></i><b>{g.label}</b><span class="rule"></span><span class="meta">{table.length ? `${table.length}팀 · ` : ''}{items.length}경기</span></div>
        {#if table.length}
          <div class="stand" style="--n:{table.length}">
            {#each table as [t, r], i}
              <div class:lead={i === 0}><span class="disp">{t}</span><span class="num" class:good={i === 0 && r.w} class:bad={i === table.length - 1 && r.l}>{r.w}-{r.l}</span></div>
            {/each}
          </div>
        {/if}
        {#each items as m (m.id)}{@render card(m)}{/each}
      </section>
    {/each}
  {/if}
{/if}

{#if !free && !mineMode && ev?.matches?.length}
  {@const s = ev.summary}
  <div class="sec"><div><span class="k">Track record</span><span class="t">예측 검증</span></div></div>
  <div class="card track">
    <div class="kpis">
      <div><span class="l">시리즈 적중</span><span class="num v">{s.series_all.n ? (s.series_all.accuracy * 100).toFixed(0) : '–'}<small>%</small></span><span class="l">{Math.round(s.series_all.accuracy * s.series_all.n)} / {s.series_all.n}경기</span></div>
      <div><span class="l">Log loss</span><span class="num v">{fx(s.series_all.log_loss, 3)}</span><span class="l">동전 0.693</span></div>
      <div><span class="l">맵 · Elo 대비</span><span class="num v">{s.maps.n ? (s.maps.accuracy * 100).toFixed(0) : '–'}<small>%</small></span><span class="l">Elo {s.maps_elo.n ? (s.maps_elo.accuracy * 100).toFixed(0) : '–'}%</span></div>
    </div>
    <div class="tbl">
      <span class="h">구분</span><span class="h r">경기</span><span class="h r">적중</span><span class="h r">Log loss</span>
      {#each [['전체 (시리즈)', s.series_all, true], ['팀별 첫 경기', s.series_first_match], ['두 번째 경기부터', s.series_later], ['맵 단위', s.maps], ['맵 단위 · Elo 비교', s.maps_elo]] as [label, x, bold]}
        <span style="font-weight:{bold ? 700 : 400}">{label}</span><span class="num r">{x.n}</span><span class="num r b">{x.n ? pct(x.accuracy) : '–'}</span><span class="num r">{x.n ? fx(x.log_loss, 3) : '–'}</span>
      {/each}
    </div>
    <p class="note" style="font-size:11px">표본이 작아 적중률은 운의 영향이 큽니다. Log loss(낮을수록 좋음, 동전 0.693)가 더 믿을 만한 지표입니다. 각 팀의 첫 경기는 대회 전 데이터만으로, 두 번째 경기부터는 그 전까지의 대회 결과를 넣어 다시 학습한 모델로 예측했습니다.</p>
  </div>
  {#each evMatches.slice(0, showAll ? undefined : 6) as m}
    <div class="lg">
      <span class="sym" class:ok={m.correct}>{m.correct ? '○' : '×'}</span>
      <div><span class="disp sc">{m.team_a} {m.score} {m.team_b}</span><span class="meta">{m.stage} · 예측 {m.p >= 0.5 ? m.team_a : m.team_b} 승 {pct(Math.max(m.p, 1 - m.p))} · {m.basis_a === 'pre-event' || m.basis_b === 'pre-event' ? '대회 전 기준' : '대회 결과 반영'}</span></div>
    </div>
  {/each}
  {#if evMatches.length > 6}
    <button class="more" onclick={() => (showAll = !showAll)}>{showAll ? '접기' : `전체 ${evMatches.length}경기 보기 ›`}</button>
  {/if}
{/if}

<style>
  .modes { display: grid; grid-template-columns: 1fr 1fr 1fr; background: var(--bg-2); box-shadow: inset 0 0 0 1px var(--line); }
  .modes a { height: var(--hit); display: flex; align-items: center; justify-content: center; font-size: 14px; color: var(--text-dim); text-decoration: none; }
  .modes a.on { font-weight: 700; color: var(--text); background: var(--surface-2); box-shadow: inset 0 -2px 0 var(--accent); }
  .note { font-size: 12px; line-height: 1.55; color: var(--muted); margin-top: 8px; }

  .head { position: relative; margin-top: 14px; padding: 14px 16px; background: var(--surface); clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px); }
  .name { font-weight: 800; font-size: 32px; line-height: .95; text-transform: uppercase; margin-top: 6px; }
  .prog { display: flex; align-items: center; gap: 10px; margin-top: 10px; }
  .segs { flex: 1; display: flex; gap: 2px; height: 6px; }
  .segs span { flex: 1; background: var(--line); }
  .segs span.on { background: var(--text); }
  .segs span.wait { background: repeating-linear-gradient(135deg, var(--text-dim) 0 2px, transparent 2px 4px); }
  .prog .num { font-weight: 700; font-size: 17px; }
  .prog em { font-style: normal; color: var(--muted); }
  .assumed { display: flex; gap: 8px; align-items: flex-start; margin-top: 8px; padding: 8px 10px; background: var(--bg-2); font-size: 12px; line-height: 1.5; color: var(--text-dim); }
  .assumed i { flex: none; width: 6px; height: 6px; margin-top: 6px; background: var(--warn); }

  .sec .side { order: 3; font-size: 12px; color: var(--muted); margin-bottom: 2px; }
  .sec .side.mine { color: var(--accent); }
  .odds { padding: 2px 12px; }
  .odd { display: grid; grid-template-columns: 20px minmax(0, 1fr) 96px 52px; gap: 10px; align-items: center; height: 40px; border-bottom: 1px solid var(--line); }
  .odd:last-child { border-bottom: 0; }
  .odd .r { font-weight: 700; font-size: 16px; color: var(--muted); text-align: right; }
  .odd .r.first { color: var(--accent); }
  .odd .t { font-size: 19px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .odd .p { font-weight: 700; font-size: 19px; text-align: right; }
  .ob { height: 4px; background: var(--bg); }
  .ob i { display: block; height: 4px; background: var(--text-dim); transition: width var(--dur-slow) var(--ease-out); }
  .ob i.first { background: var(--accent); }

  .ctl { display: flex; gap: 8px; align-items: center; }
  .seg2 { flex: 1; display: grid; grid-template-columns: 1fr 1fr; background: var(--bg-2); box-shadow: inset 0 0 0 1px var(--line); }
  .seg2 button { height: var(--hit); border: 0; background: none; font-size: 14px; color: var(--text-dim); cursor: pointer; }
  .seg2 button.on { color: var(--text); font-weight: 700; background: var(--surface-2); box-shadow: inset 0 -2px 0 var(--accent); }
  .ctl2 { display: flex; }
  .fill { height: 36px; margin-top: 6px; padding: 0 10px; border: 0; background: none; color: var(--accent); font-size: 12px; font-weight: 700; cursor: pointer; }
  .reset { height: var(--hit); padding: 0 12px; border: 0; background: none; font-size: 13px; font-weight: 600; color: var(--muted); cursor: pointer; }
  .reset.live { color: var(--accent); outline: 1px dashed var(--accent); outline-offset: -1px; }
  .chips { margin-top: 4px; }
  .gdot { width: 7px; height: 7px; display: inline-block; }
  .chip > span { gap: 6px; padding: 0 11px; font-weight: 700; white-space: nowrap; }

  .gblock { margin-bottom: 16px; }
  .gtitle {
    display: flex; align-items: center; gap: 10px; height: 36px; position: sticky; z-index: 4; background: var(--bg);
    top: calc(env(safe-area-inset-top) + var(--topbar-h)); margin-bottom: 8px;
  }
  .gtitle i { width: 8px; height: 8px; }
  .gtitle b { font-weight: 800; font-size: 18px; }
  .gtitle .rule { flex: 1; height: 1px; background: var(--line); }
  .gtitle .meta { font-size: 12px; color: var(--muted); }
  .stand { display: grid; grid-template-columns: repeat(var(--n), minmax(0, 1fr)); gap: 2px; margin-bottom: 8px; }
  .stand > div { padding: 8px; background: var(--surface); display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .stand > div.lead { background: var(--surface-2); }
  .stand .disp { font-size: 16px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .stand .num { font-weight: 700; font-size: 20px; }
  .stand .good { color: var(--good); }
  .stand .bad { color: var(--bad); }

  .track { padding: 12px; }
  .kpis { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 2px; margin-bottom: 12px; }
  .kpis > div { padding: 10px; background: var(--bg-2); display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .kpis .l { font-size: 11px; color: var(--muted); }
  .kpis .v { font-weight: 800; font-size: 32px; line-height: 1; }
  .kpis small { font-size: 18px; }
  .tbl { display: grid; grid-template-columns: minmax(0, 1fr) 40px 52px 56px; gap: 0 6px; font-size: 13px; align-items: center; }
  .tbl > span { padding: 7px 0; border-bottom: 1px solid var(--line); }
  .tbl .h { font-size: 11px; color: var(--muted); padding: 0 0 6px; border-bottom-color: var(--line-strong); }
  .tbl .r { text-align: right; }
  .tbl .num { font-size: 16px; }
  .tbl .b { font-weight: 700; }
  .lg { display: grid; grid-template-columns: 28px minmax(0, 1fr); gap: 10px; align-items: start; padding: 10px 0; border-bottom: 1px solid var(--line); }
  .lg > div { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
  .sym { width: 24px; height: 24px; display: grid; place-items: center; font-size: 14px; font-weight: 800; color: var(--bad); box-shadow: inset 0 0 0 1px var(--bad); }
  .sym.ok { color: var(--good); box-shadow: inset 0 0 0 1px var(--good); }
  .sc { font-size: 18px; line-height: 1.1; }
  .lg .meta { font-size: 12px; line-height: 1.45; color: var(--muted); }
  .more { height: var(--hit); border: 0; background: none; padding: 0; font-size: 13px; font-weight: 600; color: var(--accent); cursor: pointer; }
</style>
