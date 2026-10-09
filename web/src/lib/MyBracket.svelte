<script>
  // "내 대진표" (design 4a): pick every match of the event, locked at start, scored later.
  import { app, persisted } from './store.svelte.js';
  import { groupOf } from './bracket.js';
  import { lockedFor } from './ledger.js';
  import { agreement, champion, choose, isLocked, matchTitles, modelPick, nextDeadline, score, shortRound, stages, states } from './pickem.js';
  import PickBlock from './PickBlock.svelte';
  import TeamSheet from './TeamSheet.svelte';
  import { canShareFile, makeCard, shareFile } from './shareCard.js';

  let br = $derived(app.brackets.find((b) => b.kind === 'full' || b.kind === undefined) ?? null);
  const store = persisted('mybracket', {});
  let data = $state(store.get());
  // picks saved under team names the data source later renamed (bracket.aliases: old -> new)
  const renamed = (o, f) => Object.fromEntries(Object.entries(o ?? {}).map(([k, v]) => [k, f(v)]));
  let mine = $derived.by(() => {
    const raw = br ? (data[br.id] ?? { picks: {}, snaps: {} }) : { picks: {}, snaps: {} };
    const al = br?.aliases;
    if (!al) return raw;
    return { ...raw, picks: renamed(raw.picks, (t) => al[t] ?? t), snaps: renamed(raw.snaps, (s) => (s && al[s.team] ? { ...s, team: al[s.team] } : s)) };
  });
  let picks = $derived(mine.picks ?? {});
  function save(next) {
    data = { ...data, [br.id]: { ...mine, ...next } };
    store.set(data);
  }

  // the clock decides locks; refresh it every 30 s
  let now = $state(Date.now());
  $effect(() => { const t = setInterval(() => (now = Date.now()), 30000); return () => clearInterval(t); });

  let comp = $derived(br ? states(br, picks, now) : null);
  let byId = $derived(br ? Object.fromEntries(br.matches.map((m) => [m.id, m])) : {});
  let titles = $derived(br ? matchTitles(br) : {});
  const probs = (m) => {
    const { a, b } = comp.slots[m.id];
    if (!a.t || !b.t) return null;
    const p = app.engine.series(a.t, b.t, m.best_of ?? 3).p;
    return [p, 1 - p];
  };
  let preMatch = $derived(Object.fromEntries((app.model.event_eval?.matches ?? []).map((x) => [String(x.match_id), x])));
  // model pick: current favourite while open; frozen once the match starts
  function model(m) {
    const { a, b } = comp.slots[m.id];
    if (isLocked(m, br.results, now)) {
      const snap = mine.snaps?.[m.id];
      const ok = snap && [a.t, b.t].includes(snap.team);
      return modelPick({ snap: ok ? snap : null, ledger: lockedFor(app.ledger, br.id, m), preMatch: preMatch[String(m.match_id ?? m.vlr_id)] })?.team ?? null;
    }
    const p = probs(m);
    return p ? (p[0] >= 0.5 ? a.t : b.t) : null;
  }
  // keep a device-side snapshot of the model pick for open matches with both teams official
  $effect(() => {
    if (!br || !comp) return;
    const snaps = { ...(mine.snaps ?? {}) };
    let changed = false;
    for (const m of br.matches) {
      const { a, b } = comp.slots[m.id];
      if (isLocked(m, br.results, now) || a.kind !== 'fixed' || b.kind !== 'fixed' || !a.t || !b.t) continue;
      const p = app.engine.series(a.t, b.t, m.best_of ?? 3).p;
      const s = { team: p >= 0.5 ? a.t : b.t, p: Math.max(p, 1 - p) };
      if (snaps[m.id]?.team !== s.team || Math.abs((snaps[m.id]?.p ?? 0) - s.p) > 0.005) { snaps[m.id] = s; changed = true; }
    }
    if (changed) save({ snaps });
  });
  let modelMap = $derived(br && comp ? Object.fromEntries(br.matches.map((m) => [m.id, model(m)]).filter(([, t]) => t).map(([k, t]) => [k, { team: t }])) : {});
  let sc = $derived(br && comp ? score(br, picks, modelMap, now) : null);
  let open = $derived(br ? br.matches.filter((m) => !isLocked(m, br.results, now)) : []);
  let complete = $derived(!!br && open.length > 0 && open.every((m) => picks[m.id]));
  let champ = $derived(br ? champion(br, picks) : null);

  // undo toast for picks that a change cleared
  let toast = $state(null);
  let toastTimer;
  // the completion summary (P5) is shown once, right after the last open match is picked
  let doneView = $state(false);
  function pick(m, t) {
    const before = picks;
    const wasComplete = complete;
    const r = choose(br, picks, m.id, t, now);
    save({ picks: r.picks });
    if (!wasComplete && open.every((x) => r.picks[x.id])) {
      doneView = true;
      if (curTab) location.hash = href(null);
      scrollTo(null);
    }
    clearTimeout(toastTimer);
    if (r.cleared.length) {
      toast = { text: `뒤쪽 픽 ${r.cleared.length}개를 비웠습니다`, undo: before };
      toastTimer = setTimeout(() => (toast = null), 5000);
    } else toast = null;
  }
  function undo() { if (toast?.undo) save({ picks: toast.undo }); toast = null; }

  let sheet = $state(null);
  let showFix = $state(false);
  const when = (iso) => {
    if (!iso) return '일정 미정';
    const d = new Date(iso);
    const f = (o) => new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', ...o }).format(d);
    return `${f({ month: 'numeric' }).replace('월', '')}.${f({ day: 'numeric' }).replace('일', '')} (${f({ weekday: 'short' })}) ${f({ hour: '2-digit', minute: '2-digit', hour12: false })}`;
  };
  const left = (iso) => {
    const h = (Date.parse(iso) - now) / 3600e3;
    return h < 1 ? `${Math.max(1, Math.round(h * 60))}분 남음` : h < 48 ? `${Math.round(h)}시간 남음` : `${Math.round(h / 24)}일 남음`;
  };

  // navigation: group letters, then the playoffs as one page
  let stage = $derived(app.route.query?.stage ?? null);
  let st = $derived(br ? stages(br) : []);
  let groups = $derived(st.filter((s) => /^[A-H]$/.test(s.key)));
  let po = $derived(st.filter((s) => !/^[A-H]$/.test(s.key)));
  const count = (ids) => ids.filter((id) => picks[id]).length;
  const href = (k) => `#/bracket?mode=mine${k ? `&stage=${k}` : ''}`;
  let tabs = $derived([...groups.map((g) => ({ k: g.key, label: g.key, color: g.color, ids: g.ids })),
    ...(po.length ? [{ k: 'PO', label: '플레이오프', ids: po.flatMap((s) => s.ids) }] : [])]);
  let curTab = $derived(tabs.find((t) => t.k === stage) ?? null);
  let firstOpen = $derived(tabs.find((t) => t.ids.some((id) => !picks[id] && !isLocked(byId[id], br.results, now))) ?? null);
  let deadline = $derived(br ? nextDeadline(br, picks, now) : null);
  let toFix = $derived(br ? br.matches.filter((m) => comp.states[m.id] === 'void' && !isLocked(m, br.results, now)) : []);

  // group advance (my picks): winners of matches whose winner leaves the group
  function advance(g) {
    const inG = new Set(g.ids);
    // references from matches outside the group (the playoffs) to winners inside it
    const out = br.matches.filter((m) => !inG.has(m.id)).flatMap((m) => [m.a, m.b])
      .filter((r) => /^W:/.test(r) && inG.has(r.slice(2))).map((r) => r.slice(2));
    return [...new Set(out)].map((id) => byId[id]).sort((x, y) => (x.time ?? '').localeCompare(y.time ?? '')).map((m) => picks[m.id] ?? null);
  }
  // champion path through the playoffs, in match order (the share card puts the final first)
  let path = $derived(champ ? po.flatMap((s) => s.ids).map((id) => byId[id]).filter((m) => picks[m.id] === champ)
    .sort((x, y) => (x.time ?? '').localeCompare(y.time ?? '')).map((m) => {
      const { a, b } = comp.slots[m.id];
      return { round: shortRound(m), opp: a.t === champ ? b.t : a.t, final: m.id === (br.final ?? 'GF') };
    }) : []);
  // finalists and the four teams before them, by my picks
  const feeders = (m) => [m?.a, m?.b].filter((r) => /^W:/.test(r ?? '')).map((r) => byId[r.slice(2)]).filter(Boolean);
  let finalM = $derived(br ? byId[br.final ?? 'GF'] : null);
  let finalists = $derived(finalM ? [comp.slots[finalM.id].a.t, comp.slots[finalM.id].b.t] : []);
  let semis = $derived.by(() => {
    const uf = feeders(finalM)[0];
    return feeders(uf).flatMap((m) => [comp.slots[m.id].a.t, comp.slots[m.id].b.t]);
  });
  let agree = $derived(agreement(picks, modelMap));
  let firstLock = $derived(br ? [...br.matches].filter((m) => m.time).sort((a, b) => a.time.localeCompare(b.time))[0] : null);
  // live sections (P7): today, tomorrow, recent results — by KST date
  const day = (ms) => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul' }).format(new Date(ms));
  let live = $derived(!!br && sc.results > 0 && sc.picked > 0);
  let todayM = $derived(br ? br.matches.filter((m) => m.time && day(Date.parse(m.time)) === day(now) && !toFix.includes(m)) : []);
  let tomorrowM = $derived(br ? br.matches.filter((m) => m.time && day(Date.parse(m.time)) === day(now + 86400e3) && !toFix.includes(m)) : []);
  let recent = $derived(br ? br.matches.filter((m) => br.results?.[m.id] && !todayM.includes(m)).sort((a, b) => (b.time ?? '').localeCompare(a.time ?? '')).slice(0, 4) : []);
  const dayTitle = (ms) => new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', month: 'numeric', day: 'numeric', weekday: 'short' }).format(new Date(ms));
  // strip of every match by stage for the scoreboard
  const CELL = { hit: 'hit', miss: 'miss', void: 'void', wait: 'wait', noresp: 'wait', pick: 'pk', open: 'open', tbd: 'fut' };

  function scrollTo(id) {
    if (id == null) { window.scrollTo({ top: 0 }); return; }
    document.getElementById(`pk-${id}`)?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center' });
  }
  let sharing = $state(false);
  // share image: render first, then show a preview with share / save (second tap opens the sheet)
  let card = $state(null);
  async function share() {
    sharing = true;
    try {
      const c = await makeCard({ br, picks, states: comp.states, slots: comp.slots, score: sc, champion: champ, path, story: false, now, model: modelMap,
        advance: groups.map((g) => ({ g: g.key, teams: advance(g) })), finalists, semis, agree });
      card = { ...c, share: canShareFile(c.file) };
    } catch (e) {
      alert(`이미지를 만들지 못했습니다: ${e?.message ?? e}`);
    } finally { sharing = false; }
  }
  async function sendCard() {
    try { await shareFile(card.file); } catch (e) { if (e?.name !== 'AbortError') alert(`공유하지 못했습니다: ${e?.message ?? e}`); }
  }
  function closeCard() { URL.revokeObjectURL(card.url); card = null; }
</script>

{#snippet block(m, foot = null)}
  {@const g = groupOf(m)}
  <PickBlock {m} group={g} sides={comp.slots[m.id]} st={comp.states[m.id]} title={titles[m.id]} locked={isLocked(m, br.results, now)}
    pick={picks[m.id] ?? null} winner={br.results?.[m.id] ?? null}
    probs={probs(m)} model={model(m)} when={when(m.time)} {foot} onpick={(t) => pick(m, t)} oninfo={() => (sheet = m)} />
{/snippet}

{#snippet champPanel(done)}
  <section class="champ" class:done>
    <span class="corner tr"></span>
    <span class="ck">✦ 내 우승 예상</span>
    <span class="disp cn">{champ}</span>
    {#each path as p}<div class="pr" class:fin={p.final}><span>{p.round}</span><b class="disp">{p.opp ? `vs ${p.opp}` : '상대 미정'}</b></div>{/each}
  </section>
{/snippet}

{#snippet vsModel()}
  {@const tot = agree.same + agree.diff}
  <div class="vm">
    <div class="vmh"><span>나 vs 모델</span>{#if !live && !sc.n}<em>결과 전</em>{/if}</div>
    <div class="vmb"><span style="flex:{agree.same}"></span><span style="flex:{agree.diff}"></span></div>
    <div class="vml"><span>모델과 같은 픽 <b>{agree.same}</b></span><span class="d">모델과 다른 픽 <b>{agree.diff}</b></span></div>
    {#if tot && !sc.n}<p class="note" style="margin-top:4px">결과가 나오면 갈린 {agree.diff}경기에서 승부가 납니다.</p>{/if}
  </div>
{/snippet}

{#if !br}
  <p class="note">진행 중인 국제전 대진이 들어오면 여기서 고를 수 있습니다.</p>
{:else if !curTab && doneView}
  <!-- completion summary (P5), once after the last pick -->
  <div class="dhead"><span class="k red">My bracket · complete</span><span class="num cnt">{sc.picked}<em> / {sc.total}</em></span></div>
  <div class="dbar"><span></span></div>
  {@render champPanel(true)}
  <div class="tiles">
    <div><span class="l">결승 진출</span>{#each finalists as t}<b class="disp">{t ?? '—'}</b>{/each}</div>
    <div><span class="l">{semis.length ? '상위 4강' : '4강'}</span><b class="disp sm">{semis.filter(Boolean).join(' · ') || '—'}</b></div>
  </div>
  {@render vsModel()}
  {#if firstLock}
    <p class="lockn"><svg viewBox="0 0 12 12" width="12" height="12"><path d="M3 5.5V4a3 3 0 0 1 6 0v1.5M2.5 5.5h7v5h-7z" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>
      <span>첫 잠금은 <b>{when(firstLock.time)} {titles[firstLock.id]}</b>입니다. 그 전까지는 모두 고칠 수 있고, 이후는 경기 시작 순서대로 하나씩 잠깁니다.</span></p>
  {/if}
  <button class="cta" disabled={sharing} onclick={share}>{sharing ? '이미지 만드는 중…' : '⇪ 공유 이미지'}</button>
  <div class="shares one">
    <button class="sh" onclick={() => (doneView = false)}>대진표 다시 보기</button>
  </div>
{:else if !curTab}
  <!-- overview (P1 before results · P7 while the event runs) -->
  {#if live}
    <section class="board">
      <div class="vs3">
        <div><span class="k red">Me</span><span class="num big">{sc.me}<em>/{sc.n}</em></span><span class="l">적중</span></div>
        <span class="v">VS</span>
        <div class="r"><span class="k">Model</span><span class="num big">{sc.model}<em>/{sc.modelN}</em></span><span class="l">적중</span></div>
      </div>
      <div class="strip">
        {#each st as s}
          <div class="sg" style="--gc:{s.color}; flex:{s.ids.length}">
            {#each s.ids as id}<span class="c {CELL[comp.states[id]]}">{{ hit: '○', miss: '×', void: '!' }[comp.states[id]] ?? ''}</span>{/each}
          </div>
        {/each}
      </div>
      <div class="bl"><span>결과 <b>{sc.results}</b> · 결과 대기 <b>{br.matches.filter((m) => comp.states[m.id] === 'wait').length}</b> · 남은 <b>{br.matches.length - sc.results}</b></span>{#if toFix.length}<span class="warn">! 무효 {toFix.length}</span>{/if}</div>
      <p class="bn">같은 {sc.n}경기로 비교: 결과가 나왔고 내가 고른 경기{sc.noresp ? ` · 미응답 ${sc.noresp} 제외` : ''}{sc.noModel ? ` · 모델 기록 없음 ${sc.noModel} 제외` : ''}</p>
    </section>
  {:else}
    <section class="hero" class:done={complete}>
      <span class="corner tr"></span>
      <span class="kick">My bracket · {br.name.replace(/^Valorant /i, '')}</span>
      <div class="ht"><span class="tt">내 대진표</span><span class="num cnt">{sc.picked}<em> / {sc.total}</em></span></div>
      <div class="segs">
        {#each tabs as t}
          <div style="flex:{t.ids.length}">{#each t.ids as id}<span class:on={!!picks[id]}></span>{/each}</div>
        {/each}
      </div>
      <div class="sl"><span>조별 {groups.reduce((n, g) => n + g.ids.length, 0)}</span><span>{po.map((s) => `${s.label} ${s.ids.length}`).join(' · ')}</span></div>
      <p class="note" style="margin-top:12px">기기에만 저장 · 경기 시작 시각에 그 경기 픽이 잠깁니다 · 결과가 나오면 자동 채점</p>
    </section>
  {/if}

  {#if champ}{@render champPanel(false)}{/if}
  {#if sc.picked && !live}{@render vsModel()}{/if}

  {#if deadline}
    {@const s2 = comp.slots[deadline.id]}
    {@const soon = Date.parse(deadline.time) - now < 24 * 3600e3}
    <a class="dl" class:soon href={href(groupOf(deadline).key.match(/^[A-H]$/) ? groupOf(deadline).key : 'PO')}>
      <svg viewBox="0 0 14 14" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M7 1.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11zM7 4v3.2l2 1.3" /></svg>
      <span class="l">다음 마감 · <b>{left(deadline.time)}</b></span>
      <span class="w">{titles[deadline.id]} · <span class="disp">{s2.a.t ?? s2.a.label} vs {s2.b.t ?? s2.b.label}</span> <span class="num">{when(deadline.time)}</span></span>
    </a>
  {/if}

  {#if live && todayM.length}
    <div class="dh">오늘 · {dayTitle(now)}</div>
    <div class="list">{#each todayM as m (m.id)}{@render block(m)}{/each}</div>
  {/if}
  {#if live && tomorrowM.length}
    <div class="dh">내일 · {dayTitle(now + 86400e3)} <em>— 고칠 수 있음</em></div>
    <div class="list">{#each tomorrowM as m (m.id)}{@render block(m)}{/each}</div>
  {/if}
  {#if toFix.length}
    <div class="dh">다시 골라야 함</div>
    <div class="list">{#each toFix.slice(0, showFix ? undefined : 3) as m (m.id)}{@render block(m, '내가 고른 팀이 이 경기에 올 수 없게 됐습니다. 경기 전까지 다시 고를 수 있습니다.')}{/each}</div>
    {#if toFix.length > 3}<button class="more" onclick={() => (showFix = !showFix)}>{showFix ? '접기' : `${toFix.length - 3}경기 더 보기`}</button>{/if}
  {/if}
  {#if live && recent.length}
    <div class="dh">최근 결과</div>
    <div class="list">{#each recent as m (m.id)}{@render block(m)}{/each}</div>
  {/if}

  <div class="stages">
    {#each tabs as t}
      {@const first = t.ids.map((id) => byId[id]).filter((m) => m.time).sort((a, b) => a.time.localeCompare(b.time))[0]}
      {@const soon = first && !isLocked(first, br.results, now) && Date.parse(first.time) - now < 24 * 3600e3}
      <a class="srow" href={href(t.k)}>
        <i style="background:{t.color ?? 'var(--text)'}"></i>
        <b>{t.k === 'PO' ? '플레이오프' : `${t.k}조`}</b>
        <span class:soon>{first ? `${when(first.time)}${soon ? ` · ${left(first.time)}` : ''}` : '일정 미정'}</span>
        <span class="num" class:dim={count(t.ids) === t.ids.length}>{count(t.ids)}/{t.ids.length}</span>
        <em>›</em>
      </a>
    {/each}
  </div>
  <p class="note">대회 보기의 "내 가정"과는 따로 저장됩니다. 가정은 시뮬레이션용이고, 내 대진표는 잠기고 채점되는 기록입니다. 모델 픽(M)은 경기가 시작되는 순간의 예측으로 고정됩니다.</p>
  {#if firstOpen}<a class="cta" href={href(firstOpen.k)}>이어서 고르기 · {firstOpen.k === 'PO' ? '플레이오프' : `${firstOpen.k}조`} ›</a>{/if}
  {#if sc.picked}
    <div class="shares one">
      <button class="sh" disabled={sharing} onclick={share}>{sharing ? '이미지 만드는 중…' : '⇪ 공유 이미지'}</button>
    </div>
  {/if}
{:else}
  <!-- stage pages (P2 · P3) -->
  <div class="tabs">
    {#each tabs as t}
      <a href={href(t.k)} class:on={t.k === curTab.k}>{#if t.color}<i style="background:{t.color}"></i>{/if}{t.label}{#if t.k !== curTab.k}<span class="num">{count(t.ids)}/{t.ids.length}</span>{/if}</a>
    {/each}
  </div>
  {#if curTab.k !== 'PO'}
    {@const g = groups.find((x) => x.key === curTab.k)}
    {@const adv = advance(g)}
    {@const ix = tabs.findIndex((t) => t.k === curTab.k)}
    <div class="sh2">
      <div><span class="k" style="color:{g.color}">Group {g.key} · double elim</span><span class="t">{g.key}조</span><span class="note" style="margin:0">{new Set(g.ids.flatMap((id) => [comp.slots[id].a, comp.slots[id].b]).filter((s) => s.kind === 'fixed' && s.t).map((s) => s.t)).size}팀 · {g.ids.length}경기 · {adv.length}팀이 플레이오프로</span></div>
      <span class="num cnt">{count(g.ids)}<em> / {g.ids.length}</em></span>
    </div>
    <div class="list">{#each g.ids as id (id)}{@render block(byId[id])}{/each}</div>
    <div class="adv">
      <span class="note" style="margin:0">{g.key}조 진출 · 내 픽 기준</span>
      {#each adv as t, i}<span class="num r">{i + 1}위</span><span class="disp">{t ?? '—'}</span>{/each}
    </div>
    {#if tabs[ix + 1]}<a class="next" href={href(tabs[ix + 1].k)}>{tabs[ix + 1].k === 'PO' ? '플레이오프' : `${tabs[ix + 1].k}조`}로 ›</a>{/if}
  {:else}
    {@const ids = po.flatMap((s) => s.ids)}
    {@const rounds = [...new Map(ids.map((id) => [byId[id].round, []])).keys()].map((r) => ({ r, ids: ids.filter((id) => byId[id].round === r) }))}
    {@const remaining = ids.filter((id) => !picks[id] && !isLocked(byId[id], br.results, now) && comp.states[id] !== 'tbd')}
    <div class="sh2">
      <div><span class="k red">Playoffs</span><span class="t">플레이오프</span></div>
      <span class="num cnt">{count(ids)}<em> / {ids.length}</em></span>
    </div>
    <div class="mini" role="navigation" aria-label="플레이오프 미니 트리">
      {#each rounds as r, i}
        <div class="mc" class:sep={i > 0 && groupOf(byId[r.ids[0]]).key !== groupOf(byId[rounds[i - 1].ids[0]]).key}>
          <div class="cells">{#each r.ids as id}<button class="cell {comp.states[id]}" aria-label={shortRound(byId[id])} onclick={() => scrollTo(id)}></button>{/each}</div>
          <span>{r.r.replace(/^(상위|하위) /, '')}</span>
        </div>
      {/each}
    </div>
    <div class="legend"><span><i class="lg pick"></i>픽</span><span><i class="lg open"></i>미선택</span><span><i class="lg tbd"></i>팀 미정</span><span>칸을 누르면 그 경기로</span></div>
    {#each po as s}
      <div class="sec small"><div><span class="k">{s.key === 'U' ? 'Upper' : s.key === 'L' ? 'Lower' : 'Grand final'}</span><span class="t">{s.key === 'U' ? '상위 브래킷' : s.key === 'L' ? '하위 브래킷' : '결승'}</span></div></div>
      <div class="list">{#each s.ids as id (id)}{@render block(byId[id])}{/each}</div>
    {/each}
    {#if remaining.length}<button class="cta" onclick={() => scrollTo(remaining[0])}>남은 {remaining.length}경기 고르기 · {shortRound(byId[remaining[0]])} ›</button>
    {:else}<a class="next" href={href(null)}>요약 보기 ›</a>{/if}
  {/if}
{/if}

{#if card}
  <div class="cardbg" role="presentation" onclick={(e) => e.target === e.currentTarget && closeCard()}>
    <div class="cardbox" role="dialog" aria-modal="true" aria-label="공유 이미지">
      <img src={card.url} alt="내 대진표 공유 이미지" />
      <p class="note">이미지를 길게 눌러 사진에 저장할 수도 있습니다.</p>
      <div class="cardbtns">
        {#if card.share}<button class="cta" onclick={sendCard}>⇪ 공유</button>{/if}
        <a class="sh" href={card.url} download="valopoint-my-bracket.png">저장</a>
        <button class="sh" onclick={closeCard}>닫기</button>
      </div>
    </div>
  </div>
{/if}

{#if toast}
  <div class="toast" role="status"><span>{toast.text}</span><button onclick={undo}>되돌리기</button></div>
{/if}

{#if sheet}
  {@const sl = comp.slots[sheet.id]}
  <TeamSheet m={sheet} bid={br.id} group={groupOf(sheet)} a={sl.a.t} b={sl.b.t} pick={picks[sheet.id] ?? null}
    locked={isLocked(sheet, br.results, now)} when={when(sheet.time)} onpick={(t) => pick(sheet, t)} onclose={() => (sheet = null)} />
{/if}

<style>
  a { color: inherit; text-decoration: none; }
  .note { font-size: 12px; line-height: 1.55; color: var(--muted); margin: 10px 0 0; }
  .red { color: var(--accent) !important; }
  .list { display: flex; flex-direction: column; gap: 10px; }

  .hero { position: relative; margin-top: 14px; padding: 14px 16px 16px; background: linear-gradient(115deg, rgba(242, 67, 79, .16) 0 34%, var(--surface) 34%); clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px); }
  .kick, .ck { font-family: var(--font-display); font-weight: 600; font-size: 12px; letter-spacing: var(--tracking-label); color: var(--text-dim); text-transform: uppercase; }
  .ht { display: flex; align-items: flex-end; justify-content: space-between; margin-top: 6px; }
  .tt { font-weight: 800; font-size: 28px; letter-spacing: var(--tracking-ko-head); }
  .cnt { font-weight: 800; font-size: 44px; line-height: .85; }
  .cnt em { font-style: normal; font-size: 24px; color: var(--muted); }
  .segs { display: flex; gap: 4px; margin-top: 12px; }
  .segs > div { display: flex; gap: 1px; }
  .segs span { flex: 1; height: 8px; background: var(--bg); box-shadow: inset 0 0 0 1px var(--line); transition: background var(--dur-med) var(--ease-out); }
  .segs span.on { background: var(--pick); box-shadow: none; }
  .sl { display: flex; justify-content: space-between; margin-top: 5px; font-family: var(--font-display); font-size: 12px; color: var(--muted); }
  .hero.done { box-shadow: inset 0 0 0 1px var(--accent-glow); animation: glow var(--dur-fast) linear 240ms 1; }
  @keyframes glow { 50% { box-shadow: inset 0 0 0 1px var(--accent), 0 0 24px var(--accent-glow); } }

  .board { margin-top: 14px; padding: 14px 14px 12px; background: linear-gradient(115deg, rgba(242, 67, 79, .16) 0 34%, var(--surface) 34%); clip-path: var(--clip-chamfer); }
  .vs3 { display: grid; grid-template-columns: 1fr auto 1fr; align-items: end; }
  .vs3 > div { display: flex; flex-direction: column; }
  .vs3 .r { align-items: flex-end; }
  .vs3 .k { font-family: var(--font-display); font-weight: 700; font-size: 11px; letter-spacing: var(--tracking-label); color: var(--text-dim); text-transform: uppercase; }
  .big { font-weight: 800; font-size: 48px; line-height: .9; }
  .big em { font-style: normal; font-size: 22px; color: var(--muted); }
  .vs3 .l { font-size: 11px; color: var(--muted); }
  .vs3 .v { font-family: var(--font-display); font-weight: 600; color: var(--muted); padding-bottom: 20px; }
  .strip { display: flex; gap: 3px; margin-top: 12px; }
  .sg { display: flex; gap: 1px; border-top: 2px solid var(--gc); padding-top: 3px; min-width: 0; }
  .c { flex: 1; min-width: 0; height: 16px; display: grid; place-items: center; font-size: 10px; font-weight: 800; background: var(--surface); box-shadow: inset 0 0 0 1px var(--line); color: var(--muted); }
  .c.hit { background: color-mix(in srgb, var(--res-hit) 12%, transparent); color: var(--res-hit); box-shadow: none; }
  .c.miss { background: color-mix(in srgb, var(--res-miss) 12%, transparent); color: var(--res-miss); box-shadow: none; }
  .c.void { background: color-mix(in srgb, var(--res-void) 12%, transparent); color: var(--res-void); box-shadow: none; }
  .c.wait { background: var(--line-strong); box-shadow: none; }
  .c.pk { background: var(--pick-wash); box-shadow: none; }
  .c.open { box-shadow: inset 0 0 0 1px var(--pick); }
  .bl { display: flex; justify-content: space-between; margin-top: 8px; font-size: 12px; color: var(--muted); }
  .bl b { color: var(--text); }
  .bl .warn { color: var(--res-void); font-weight: 700; }

  .champ { position: relative; display: flex; flex-direction: column; gap: 6px; margin-top: 10px; padding: 14px 16px; background: linear-gradient(115deg, rgba(242, 67, 79, .22) 0 30%, var(--surface) 30%); clip-path: var(--clip-chamfer); }
  .champ .ck { color: var(--accent); }
  .cn { font-weight: 800; font-size: 46px; line-height: .95; padding-bottom: .14em; overflow-wrap: anywhere; }
  .champ.done .cn { animation: wipe var(--dur-slow) var(--ease-out) 360ms backwards; }
  @media (prefers-reduced-motion: reduce) { .champ.done .cn, .hero.done { animation: none; } }
  .pr.fin span { color: var(--accent); }
  .dhead { display: flex; justify-content: space-between; align-items: flex-end; margin-top: 16px; }
  .dhead .k { font-family: var(--font-display); font-weight: 600; font-size: 12px; letter-spacing: var(--tracking-label); text-transform: uppercase; }
  .dhead .cnt { font-size: 32px; }
  .dhead .cnt em { font-size: 20px; }
  .dbar { height: 4px; margin: 8px 0 4px; background: var(--bg); }
  .dbar span { display: block; height: 4px; background: var(--accent); animation: fillbar var(--dur-med) var(--ease-snap) both; }
  @keyframes fillbar { from { width: 92%; } to { width: 100%; } }
  .tiles { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 8px; }
  .tiles > div { padding: 12px; background: var(--surface); display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .tiles .l { font-size: 11px; color: var(--muted); margin-bottom: 4px; }
  .tiles .disp { font-size: 19px; line-height: 1.15; }
  .tiles .disp.sm { font-size: 16px; }
  .vm { margin-top: 8px; padding: 12px; background: var(--surface); box-shadow: inset 0 0 0 1px var(--line); }
  .vmh { display: flex; justify-content: space-between; font-size: 13px; font-weight: 700; }
  .vmh em { font-style: normal; font-size: 11px; color: var(--warn); }
  .vmb { display: flex; gap: 2px; height: 6px; margin: 10px 0 6px; }
  .vmb span:first-child { background: var(--text-dim); }
  .vmb span:last-child { background: var(--accent); }
  .vml { display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); }
  .vml b { font-family: var(--font-num); font-size: 16px; color: var(--text); }
  .vml .d b { color: var(--accent); }
  .lockn { display: flex; gap: 8px; align-items: flex-start; font-size: 12px; line-height: 1.55; color: var(--muted); margin: 12px 0 0; }
  .lockn svg { flex: none; margin-top: 3px; }
  .lockn b { color: var(--text); }
  .bn { font-size: 11px; color: var(--muted); margin: 6px 0 0; }
  .dh { display: flex; align-items: center; gap: 8px; margin: 22px 0 8px; font-weight: 800; font-size: 15px; }
  .dh em { font-style: normal; font-weight: 600; font-size: 12px; color: var(--text-dim); }
  .dh::after { content: ""; flex: 1; height: 1px; background: var(--line); }
  .pr { display: grid; grid-template-columns: 64px minmax(0, 1fr); gap: 8px; align-items: baseline; padding: 4px 0; border-top: 1px solid var(--line); font-size: 12px; color: var(--muted); }
  .pr .disp { font-size: 16px; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .dl { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 4px 12px; align-items: center; margin-top: 10px; padding: 12px 14px; background: var(--surface); box-shadow: inset 0 2px 0 var(--line-strong); color: var(--text-dim); }
  .dl svg { grid-row: span 2; }
  .dl.soon { box-shadow: inset 0 2px 0 var(--warn); color: var(--warn); }
  .dl .l { font-size: 12px; color: var(--text-dim); }
  .dl .l b { color: inherit; }
  .dl.soon .l b { color: var(--warn); }
  .dl .w { font-size: 14px; font-weight: 700; color: var(--text); }
  .dl .w .disp { font-size: 17px; }
  .dl .w .num { font-size: 15px; color: var(--muted); font-weight: 600; }

  .stages { display: flex; flex-direction: column; margin-top: 8px; }
  .srow { display: grid; grid-template-columns: 10px 76px minmax(0, 1fr) auto 18px; gap: 10px; align-items: center; min-height: 52px; border-bottom: 1px solid var(--line); }
  .srow i { width: 8px; height: 8px; }
  .srow b { font-size: 15px; white-space: nowrap; }
  .srow span { font-size: 12px; color: var(--muted); }
  .srow span.soon { color: var(--warn); }
  .srow .num { font-weight: 700; font-size: 20px; color: var(--text); }
  .srow .num.dim { color: var(--text-dim); }
  .srow em { font-style: normal; color: var(--muted); font-size: 18px; }
  .cta {
    display: flex; align-items: center; justify-content: center; width: 100%; height: 52px; margin-top: 12px; border: 0; cursor: pointer;
    background: var(--accent); color: var(--accent-ink); font-weight: 800; font-size: 16px;
    clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px);
  }
  .more { height: var(--hit); border: 0; background: none; padding: 0; font-size: 13px; font-weight: 600; color: var(--accent); cursor: pointer; }
  .shares { display: grid; grid-template-columns: 2fr 1fr; gap: 6px; margin-top: 8px; }
  .shares.one { grid-template-columns: 1fr; }
  .cardbg { position: fixed; inset: 0; z-index: 80; display: flex; align-items: center; justify-content: center; padding: 16px; background: rgba(5, 7, 12, .94); }
  .cardbox { width: min(420px, 100%); max-height: 100%; display: flex; flex-direction: column; gap: 8px; overflow: auto; }
  .cardbox img { width: 100%; height: auto; display: block; box-shadow: 0 0 0 1px var(--line-strong); }
  .cardbtns { display: grid; grid-auto-flow: column; grid-auto-columns: 1fr; gap: 6px; }
  .cardbtns .cta { margin: 0; }
  .cardbtns a.sh { display: flex; align-items: center; justify-content: center; text-decoration: none; }
  .sh { height: 48px; border: 0; background: var(--surface-2); box-shadow: inset 0 0 0 1px var(--line-strong); color: var(--text); font-weight: 700; font-size: 14px; cursor: pointer; }
  .sh:disabled { opacity: .5; }

  .tabs { display: flex; gap: 4px; overflow-x: auto; scrollbar-width: none; margin: 4px -16px 0; padding: 4px 16px 0; }
  .tabs a { flex: none; display: flex; align-items: center; gap: 5px; height: 34px; padding: 0 10px; background: var(--surface); font-size: 13px; font-weight: 600; }
  .tabs a i { width: 7px; height: 7px; }
  .tabs a .num { color: var(--muted); }
  .tabs a.on { background: var(--text); color: var(--accent-ink); font-weight: 800; }
  .sh2 { display: flex; align-items: flex-end; justify-content: space-between; margin: 16px 0 10px; }
  .sh2 > div { display: flex; flex-direction: column; gap: 2px; }
  .sh2 .k { font-family: var(--font-display); font-weight: 600; font-size: 12px; letter-spacing: var(--tracking-label); text-transform: uppercase; }
  .sh2 .t { font-weight: 800; font-size: 26px; letter-spacing: var(--tracking-ko-head); }
  .sh2 .cnt { font-size: 32px; line-height: 1; }
  .sh2 .cnt em { font-size: 20px; }
  .adv { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 6px 12px; margin-top: 10px; padding: 12px 14px; background: var(--bg-2); box-shadow: inset 0 0 0 1px var(--line); }
  .adv .note { grid-column: 1 / 3; }
  .adv .r { font-weight: 700; font-size: 15px; color: var(--muted); }
  .adv .disp { font-size: 20px; }
  .next { display: flex; align-items: center; justify-content: center; height: 52px; margin-top: 10px; background: var(--surface-2); box-shadow: inset 0 0 0 1px var(--line-strong); font-weight: 700; font-size: 15px; }

  .mini { display: flex; gap: 6px; padding: 10px; background: var(--bg-2); box-shadow: inset 0 0 0 1px var(--line); }
  .mc { flex: 1; display: flex; flex-direction: column; gap: 4px; padding-left: 4px; min-width: 0; }
  .mc.sep { border-left: 1px solid var(--line-strong); }
  .mc .cells { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 3px; min-height: 58px; }
  .cell { height: 10px; border: 0; padding: 0; cursor: pointer; background: var(--surface-2); outline: 1px solid var(--line-strong); outline-offset: -1px; }
  .cell.pick, .cell.wait { background: var(--pick); outline: none; }
  .cell.hit { background: var(--res-hit); outline: none; }
  .cell.miss { background: var(--res-miss); outline: none; }
  .cell.void { background: var(--res-void); outline: none; }
  .cell.tbd { background: transparent; outline-style: dashed; }
  .mc span { font-size: 10px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .legend { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 6px; font-size: 11px; color: var(--muted); }
  .legend span { display: flex; align-items: center; gap: 5px; }
  .lg { width: 10px; height: 6px; display: inline-block; }
  .lg.pick { background: var(--pick); }
  .lg.open { background: var(--surface-2); outline: 1px solid var(--line-strong); }
  .lg.tbd { outline: 1px dashed var(--line-strong); }

  .toast {
    position: fixed; left: 16px; right: 16px; bottom: calc(var(--tabbar-h) + env(safe-area-inset-bottom) + 10px); z-index: 20; max-width: 688px; margin: 0 auto;
    display: flex; align-items: center; gap: 8px; min-height: 48px; padding: 0 4px 0 14px; background: var(--surface-2); box-shadow: inset 0 0 0 1px var(--line-strong);
    font-size: 13px; animation: tin var(--dur-med) var(--ease-out);
  }
  @keyframes tin { from { transform: translateY(100%); opacity: 0; } }
  .toast button { margin-left: auto; height: var(--hit); padding: 0 10px; border: 0; background: none; font-size: 13px; font-weight: 700; color: var(--accent); cursor: pointer; }
</style>
