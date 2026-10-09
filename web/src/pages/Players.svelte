<script>
  import TraitTags from '../lib/TraitTags.svelte';
  import Glyph from '../lib/Glyph.svelte';
  import RoleGlyph from '../lib/RoleGlyph.svelte';
  import { app, viewState } from '../lib/store.svelte.js';
  import { tick } from 'svelte';
  import { REGION_LABEL, ROLE_LABEL, cap, fx } from '../lib/format.js';
  import { badges, buildContext, highlights } from '../lib/profile.js';
  import OptionSheet from '../lib/OptionSheet.svelte';

  // filters, list length and scroll survive a visit to a player page and back
  const DEFAULTS = { region: 'ALL', role: 'ALL', map: '', agent: '', q: '', shown: 60, y: 0 };
  const view = viewState('players', DEFAULTS);
  const saved = view.get();
  let region = $state(saved.region);
  let role = $state(saved.role);
  let map = $state(saved.map);
  let agent = $state(saved.agent);
  let q = $state(saved.q);
  let open = $state({});
  let shown = $state(saved.shown);
  let filtered = $derived(region !== 'ALL' || role !== 'ALL' || !!map || !!agent || !!q);
  function resetFilters() { region = 'ALL'; role = 'ALL'; map = ''; agent = ''; q = ''; shown = 60; }
  $effect(() => { view.set({ ...view.get(), region, role, map, agent, q, shown }); });
  $effect(() => {
    if (saved.y > 0) tick().then(() => requestAnimationFrame(() => window.scrollTo(0, saved.y)));
    const onScroll = () => view.set({ ...view.get(), y: window.scrollY });
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  });
  const norm = (x) => (x ?? '').toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '');

  const all = Object.entries(app.model.players).map(([id, p]) => ({ id, ...p }));
  const agents = [...new Set(all.flatMap((p) => Object.keys(p.agents)))].sort();
  // map / agent pickers (bottom sheets in the app style instead of native selects)
  let picking = $state(null);
  const usedBy = (a) => all.filter((p) => p.agents[a]).length;
  const ROLE_ORDER = ['duelist', 'initiator', 'controller', 'sentinel'];
  const roleOf = (a) => app.model.roles?.[a] ?? '';
  let agentOptions = $derived([{ value: '', label: '모든 요원' },
    ...[...agents].sort((x, y) => (ROLE_ORDER.indexOf(roleOf(x)) + 9) % 9 - (ROLE_ORDER.indexOf(roleOf(y)) + 9) % 9 || x.localeCompare(y))
      .map((a) => ({ value: a, label: cap(a), group: ROLE_LABEL[roleOf(a)] ?? '기타', sub: `${usedBy(a)}명` }))]);
  let mapOptions = $derived([{ value: '', label: '모든 맵' }, ...app.model.maps.map((m) => ({ value: m, label: cap(m) }))]);
  let ctx = $derived(buildContext(app.model, app.brackets));
  let sections = $derived(highlights(ctx, 10));
  let tags = $derived(Object.fromEntries(all.map((p) => [p.id, badges(p, ctx)])));
  // card kicker and short chip label per highlight
  const META = {
    mvp: ['MVP race', '이번 대회'], rising: ['On the rise', '요즘 뜨는'], steady: ['Steady', '꾸준한'],
    career: ['International', '국제전'], league: ['League best', '지역리그'], power: ['Power top', '파워 Top'],
    bigstage: ['Big stage', '큰 무대'], agent: ['Agent master', '요원 장인'], map: ['Map specialist', '맵'],
  };

  function value(p) {
    if (map && agent) return p.grid[map]?.[agent] != null ? { pp: p.grid[map][agent], n: null } : null;
    if (agent) return p.agents[agent] ? { pp: p.agents[agent].pp, n: p.agents[agent].rounds } : null;
    if (map) return p.maps[map] ? { pp: p.maps[map].pp, n: p.maps[map].rounds } : { pp: p.pp, n: 0 };
    return { pp: p.pp, n: p.rounds };
  }

  let searching = $derived(q.trim().length > 0);
  let rows = $derived(
    all
      .filter((p) => searching || ((region === 'ALL' || p.region === region) && (role === 'ALL' || p.role === role)))
      .filter((p) => !searching || norm(p.name).includes(norm(q.trim())) || norm(p.team).includes(norm(q.trim())))
      .map((p) => ({ p, v: searching ? { pp: p.pp, n: p.rounds } : value(p) }))
      .filter((r) => r.v)
      .sort((a, b) => b.v.pp - a.v.pp),
  );
  $effect(() => { region; role; map; agent; q; shown = 60; });

  // carousel: chips jump to a card; the active card follows the scroll position
  let strip = $state();
  let active = $state(0);
  function jump(i) {
    const card = strip?.children[i];
    if (card) strip.scrollTo({ left: card.offsetLeft - strip.offsetLeft - 16, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    active = i;
  }
  const nearest = () => Math.max(0, Math.min(sections.length - 1, Math.round(strip.scrollLeft / ((strip.children[0]?.offsetWidth ?? 1) + 10))));
  function onScroll() {
    if (!drag) active = nearest();
  }
  // desktop: drag with the mouse (touch scrolls natively), arrows and keyboard
  let drag = null;
  let dragging = $state(false);
  let moved = false;
  function down(e) {
    if (e.pointerType !== 'mouse' || e.button !== 0) return;
    drag = { x: e.clientX, left: strip.scrollLeft };
    moved = false;
  }
  function move(e) {
    if (!drag) return;
    const dx = e.clientX - drag.x;
    if (!moved && Math.abs(dx) < 6) return;
    if (!moved) { moved = true; dragging = true; strip.setPointerCapture(e.pointerId); }
    strip.scrollLeft = drag.left - dx;
  }
  function up() {
    if (!drag) return;
    const wasMoved = moved;
    drag = null;
    if (wasMoved) { dragging = false; jump(nearest()); }
  }
  // a drag must not also open the player under the cursor
  function click(e) {
    if (moved) { e.preventDefault(); e.stopPropagation(); moved = false; }
  }
  function key(e) {
    if (e.key === 'ArrowRight') { e.preventDefault(); jump(Math.min(sections.length - 1, active + 1)); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); jump(Math.max(0, active - 1)); }
  }
</script>

{#snippet rankRow(p, v, i)}
  <a class="prow" class:rise={i < 12} style="--i:{i}" href={`#/player/${p.id}`}>
    <span class="num r" class:top={i < 3}>{i + 1}</span>
    <div class="mid">
      <div class="line"><RoleGlyph role={p.role} size={9} color="var(--text-dim)" /><span class="disp nm">{p.name}</span><span class="badge sm {p.region}">{p.region}</span></div>
      <span class="sub">{p.team} · {ROLE_LABEL[p.role] ?? p.role}{v.n != null ? ` · ${v.n}R` : ''}</span>
      <TraitTags tags={tags[p.id] ?? []} max={2} small />
    </div>
    <span class="num pp">{fx(v.pp)}</span>
  </a>
{/snippet}

<div class="kicker">Players · {all.length}</div>
<h1 style="margin-bottom:0">선수</h1>
<div class="search-box">
  <input type="search" placeholder="선수 또는 팀 검색" bind:value={q} id="player-search" autocomplete="off" aria-label="선수 검색" />
  {#if q}<button onclick={() => (q = '')} aria-label="검색어 지우기">×</button>{/if}
</div>

{#if searching}
  <p class="note">{rows.length}명</p>
  {#each rows.slice(0, shown) as { p, v }, i (p.id)}{@render rankRow(p, v, i)}{/each}
  {#if !rows.length}<div class="empty"><b>일치하는 선수가 없습니다</b></div>{/if}
{:else}
  <div class="chips" role="tablist" aria-label="하이라이트">
    {#each sections as s, i}
      <button class="chip" class:on={active === i} onclick={() => jump(i)} role="tab" aria-selected={active === i}>
        <span><Glyph name={s.icon} size={13} color={active === i ? 'var(--accent-ink)' : null} />{META[s.key]?.[1] ?? s.title}</span>
      </button>
    {/each}
  </div>
  <div class="hl-wrap">
  <button class="nav prev" onclick={() => jump(Math.max(0, active - 1))} disabled={active === 0} aria-label="이전 카드">‹</button>
  <button class="nav next" onclick={() => jump(Math.min(sections.length - 1, active + 1))} disabled={active === sections.length - 1} aria-label="다음 카드">›</button>
  <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
  <div class="hl" class:dragging bind:this={strip} onscroll={onScroll} tabindex="0" role="region" aria-label="하이라이트 카드"
    onpointerdown={down} onpointermove={move} onpointerup={up} onpointercancel={up} onclickcapture={click} onkeydown={key}
    ondragstart={(e) => e.preventDefault()}>
    {#each sections as s, i}
      <section class="hl-card" class:on={active === i}>
        <div class="hl-k"><Glyph name={s.icon} /><span class:red={s.key === 'mvp'}>{META[s.key]?.[0] ?? ''}</span><em class="num">{i + 1} / {sections.length}</em></div>
        <div class="hl-t">{s.title}</div>
        <div class="hl-rows">
          {#each s.rows.slice(0, open[s.key] ? 10 : 5) as r, j}
            <a class="hl-row" href={`#/player/${r.p.id}`}>
              <span class="num hr" class:first={j === 0}>{j + 1}</span>
              <div class="hm">
                <div class="line"><span class="disp">{r.p.name}</span><span class="badge sm {r.p.region}">{r.p.region}</span></div>
                <span class="sub">{r.p.team} · {r.sub}</span>
              </div>
              <span class="num hv">{r.value}</span>
            </a>
          {/each}
        </div>
        {#if s.rows.length > 5}
          <button class="hl-more" onclick={() => (open = { ...open, [s.key]: !open[s.key] })}>{open[s.key] ? '접기' : `더 보기 (${s.rows.length})`}</button>
        {/if}
        <p class="hl-note">{s.note}</p>
      </section>
    {/each}
  </div>
  </div>
  <div class="ticks" aria-hidden="true">
    {#each sections as _, i}<span class:on={active === i}></span>{/each}
    <em class="touch">좌우로 넘기기</em><em class="mouse">드래그하거나 ‹ › 로 넘기기</em>
  </div>

  <div class="sec" style="margin-bottom:10px"><div><span class="k">Ranking · {rows.length}</span><span class="t">전체 랭킹</span></div>
    {#if filtered}<button class="reset" onclick={resetFilters}>↺ 필터 초기화</button>{/if}</div>
  <div class="chips" style="margin-top:0" role="group" aria-label="지역">
    {#each ['ALL', 'AMER', 'EMEA', 'PAC', 'CN'] as r}
      <button class="chip" class:on={region === r} onclick={() => (region = r)} aria-pressed={region === r}><span>{r === 'ALL' ? '전체' : REGION_LABEL[r]}</span></button>
    {/each}
  </div>
  <div class="roles" role="group" aria-label="역할">
    {#each ['ALL', 'duelist', 'initiator', 'controller', 'sentinel'] as r}
      <button class:on={role === r} onclick={() => (role = r)} aria-pressed={role === r}>{#if r !== 'ALL'}<RoleGlyph role={r} size={9} color="currentColor" />{/if}{r === 'ALL' ? '전체' : ROLE_LABEL[r]}</button>
    {/each}
  </div>
  <div class="sels">
    <button class="sel" class:on={map} aria-haspopup="dialog" onclick={() => (picking = 'map')}><span class="l">맵</span><span class="v">{map ? cap(map) : '모든 맵'}</span><span class="arw">▼</span></button>
    <button class="sel" class:on={agent} aria-haspopup="dialog" onclick={() => (picking = 'agent')}><span class="l">요원</span><span class="v">{agent ? cap(agent) : '모든 요원'}</span><span class="arw">▼</span></button>
  </div>
  <p class="note">PP 100 = 평균 선수. +10 PP ≈ 팀 라운드 승률 +1%p 기여. 표본이 적은 조합은 선수 전체값 쪽으로 축소 추정됩니다.</p>
  {#each rows.slice(0, shown) as { p, v }, i (p.id)}{@render rankRow(p, v, i)}{/each}
{/if}
{#if rows.length > shown}
  <button class="btn" style="width:100%; margin-top:10px" onclick={() => (shown += 60)}>더 보기 ({rows.length - shown}명 남음)</button>
{/if}

{#if picking === 'map'}
  <OptionSheet kicker="Filter · map" title="맵 선택" options={mapOptions} value={map} onpick={(v) => (map = v)} onclose={() => (picking = null)} />
{:else if picking === 'agent'}
  <OptionSheet kicker="Filter · agent" title="요원 선택" options={agentOptions} value={agent} onpick={(v) => (agent = v)} onclose={() => (picking = null)} />
{/if}

<style>
  a { color: inherit; text-decoration: none; }
  .note { font-size: 12px; line-height: 1.5; color: var(--muted); margin: 8px 0 0; }
  .line { display: flex; align-items: center; gap: 7px; min-width: 0; }
  .sub { font-size: 12px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .chip > span { gap: 6px; padding: 0 11px; white-space: nowrap; }

  .hl {
    display: flex; gap: 10px; overflow-x: auto; scroll-snap-type: x mandatory; margin: 8px -16px 0; padding: 0 16px;
    scroll-padding: 0 16px; scrollbar-width: none;
    /* cards keep their own height: opening one card must not stretch the others */
    align-items: flex-start;
  }
  .hl:focus-visible { outline: 1px solid var(--accent); outline-offset: -1px; }
  .hl.dragging { scroll-snap-type: none; cursor: grabbing; user-select: none; }
  .hl-wrap { position: relative; }
  .nav { display: none; }
  @media (hover: hover) and (pointer: fine) {
    .hl { cursor: grab; }
    .nav {
      display: grid; place-items: center; position: absolute; top: 50%; z-index: 2; transform: translateY(-50%);
      width: 36px; height: 56px; border: 0; background: var(--bg-2); box-shadow: inset 0 0 0 1px var(--line-strong);
      color: var(--text); font-size: 26px; cursor: pointer; opacity: .9;
    }
    .nav.prev { left: -12px; }
    .nav.next { right: -12px; }
    .nav:hover:not(:disabled) { background: var(--accent); color: var(--accent-ink); }
    .nav:disabled { opacity: 0; pointer-events: none; }
  }
  .hl::-webkit-scrollbar { display: none; }
  .hl-card {
    flex: none; width: min(318px, 82vw); scroll-snap-align: start; background: var(--surface); padding: 14px 14px 4px;
    clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px);
    display: flex; flex-direction: column; transition: box-shadow var(--dur-med) var(--ease-out);
  }
  .hl-card.on { box-shadow: inset 0 2px 0 var(--accent); }
  .hl-k { display: flex; align-items: center; gap: 8px; }
  .hl-k span { font-family: var(--font-display); font-weight: 600; font-size: 11px; letter-spacing: var(--tracking-label); color: var(--text-dim); text-transform: uppercase; }
  .hl-k span.red { color: var(--accent); }
  .hl-k em { margin-left: auto; font-style: normal; font-size: 13px; color: var(--muted); }
  .hl-t { font-weight: 800; font-size: 19px; letter-spacing: -.01em; margin-top: 4px; }
  .hl-rows { margin-top: 8px; }
  .hl-row { display: grid; grid-template-columns: 24px minmax(0, 1fr) auto; gap: 10px; align-items: center; padding: 8px 0; border-top: 1px solid var(--line); }
  .hr {
    width: 22px; height: 22px; display: grid; place-items: center; font-weight: 800; font-size: 15px;
    background: var(--bg); color: var(--text-dim); clip-path: polygon(4px 0, 100% 0, 100% 100%, 0 100%, 0 4px);
  }
  .hr.first { background: var(--accent); color: var(--accent-ink); }
  .hm { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .hm .disp { font-size: 19px; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .hv { font-weight: 800; font-size: 24px; }
  .hl-more { display: flex; align-items: center; height: var(--hit); border: 0; border-top: 1px solid var(--line); background: none; padding: 0; font-size: 13px; font-weight: 600; color: var(--accent); cursor: pointer; text-align: left; }
  .hl-note { font-size: 11px; line-height: 1.5; color: var(--muted); margin: 0; padding: 4px 0 10px; }
  .ticks { display: flex; align-items: center; gap: 4px; margin-top: 10px; }
  .ticks span { height: 2px; width: 8px; background: var(--line-strong); transition: width var(--dur-med) var(--ease-snap), background var(--dur-med); }
  .ticks span.on { width: 20px; background: var(--accent); }
  .ticks em { margin-left: auto; font-style: normal; font-size: 11px; color: var(--muted); }
  .ticks .mouse { display: none; }
  @media (hover: hover) and (pointer: fine) { .ticks .touch { display: none; } .ticks .mouse { display: inline; } }

  .roles { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); background: var(--bg-2); box-shadow: inset 0 0 0 1px var(--line); margin-top: 4px; }
  .roles button {
    height: var(--hit); display: flex; align-items: center; justify-content: center; gap: 5px; border: 0; background: none;
    color: var(--text-dim); font-size: 13px; cursor: pointer; padding: 0; white-space: nowrap;
  }
  .roles button.on { background: var(--surface-2); color: var(--text); font-weight: 700; box-shadow: inset 0 -2px 0 var(--accent); }
  .sels { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 6px; }
  .reset { order: 3; align-self: flex-end; height: 26px; padding: 0 8px; border: 0; background: none; box-shadow: inset 0 0 0 1px var(--line-strong); color: var(--text-dim); font-size: 11px; font-weight: 600; cursor: pointer; }
  .sel { position: relative; display: flex; align-items: center; gap: 10px; width: 100%; min-width: 0; height: var(--hit); padding: 0 28px 0 12px;
    border: 0; background: var(--surface); box-shadow: inset 0 0 0 1px var(--line); color: var(--text); font: inherit; text-align: left; cursor: pointer; }
  .sel.on { box-shadow: inset 0 0 0 1px var(--accent); }
  .sel:focus-visible { outline: 1px solid var(--accent); outline-offset: -1px; }
  .sel .l { flex: none; font-size: 11px; color: var(--muted); }
  .sel .v { flex: 1; min-width: 0; font-size: 14px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .sel .arw { position: absolute; right: 12px; font-size: 11px; color: var(--muted); pointer-events: none; }

  .prow { display: grid; grid-template-columns: 28px minmax(0, 1fr) auto; gap: 4px 12px; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--line); }
  .prow .r { font-weight: 700; font-size: 22px; color: var(--muted); text-align: right; }
  .prow .r.top { color: var(--accent); }
  .mid { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
  .prow .nm { font-size: 20px; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .prow .pp { font-size: 26px; }
  .empty { margin-top: 16px; padding: 28px 16px; background: var(--surface); text-align: center; }
</style>
