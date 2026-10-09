<script>
  // Bracket match card (design v1, five states): upcoming, live, finished,
  // my what-if lock, teams not decided. Left team = red, right team = off-white.
  import { app } from './store.svelte.js';
  import { kstShort, pct } from './format.js';

  let { m, bid, group, teams, official, mine, projected = null, preP = () => null, onlock } = $props();
  // official: winner from the data source; mine: my what-if pick (ignored once official)
  let bo = $derived(m.best_of ?? 3);
  let a = $derived(teams?.a);
  let b = $derived(teams?.b);
  let known = $derived(!!(a && b));
  let p = $derived(known ? app.engine.series(a, b, bo).p : null);
  let assumed = $derived(!official && !!mine);
  // no live scores: "live" = started and still inside a normal series length, no result yet
  let state = $derived.by(() => {
    if (official) return 'done';
    if (assumed) return 'mine';
    const t = m.time ? Date.parse(m.time) : NaN;
    if (!Number.isNaN(t) && Date.now() >= t) {
      return Date.now() - t < (bo === 5 ? 5.5 : bo === 1 ? 1.5 : 3.5) * 3600e3 ? 'live' : 'wait';
    }
    return 'pre';
  });
  let final = $derived(group.key === 'GF');
  let pa = $derived(state === 'done' ? preP(m, a) : p);
  const top4 = (o) => Object.entries(o ?? {}).sort((x, y) => y[1] - x[1]).slice(0, 4);
</script>

<article class="mc" class:final style="--gc:{group.color}">
  <header>
    <span class="gchip" class:final>{group.label}</span>
    <span class="num when">{kstShort(m.time) || '일정 미정'}</span>
    <span class="meta">{m.round} · Bo{bo}</span>
    {#if state === 'live'}<span class="st live"><i></i>진행 중</span>
    {:else if state === 'done'}<span class="st done">종료</span>
    {:else if state === 'mine'}<span class="st mine">내 가정</span>
    {:else if state === 'wait'}<span class="st">결과 대기</span>
    {:else if known}<span class="st">경기 전</span>{/if}
  </header>

  {#if known}
    <div class="sides">
      {#each [[a, 0], [b, 1]] as [t, i]}
        {@const q = i === 0 ? p : 1 - p}
        {@const won = (official ?? mine) === t}
        {@const pre = i === 0 ? pa : pa == null ? null : 1 - pa}
        <button class="side" class:right={i === 1}
          class:win={state === 'done' && won} class:lose={(state === 'done' || state === 'mine') && !won}
          class:pick={state === 'mine' && won}
          disabled={state === 'done'} aria-pressed={won}
          onclick={() => onlock(t)}>
          <span class="disp tn">{t}</span>
          {#if state === 'done'}
            <span class="res">{#if won}<b>✓ 승</b>{:else}<b>패</b>{/if}{#if pre != null} · 경기 전 예측 {pct(pre)}{/if}</span>
          {:else if state === 'mine'}
            <span class="res" class:accent={won}>{won ? '승 (가정)' : '패 (가정)'}</span>
          {:else}
            <span class="disp q">{pct(q)}</span>
          {/if}
        </button>
      {/each}
    </div>
    {#if state === 'mine'}
      <div class="hatchbar"></div>
    {:else if pa != null}
      <div class="vbar" style="margin:6px 10px 0; opacity:{state === 'done' ? 0.5 : 1}"><span style="width:{(pa * 100).toFixed(1)}%"></span><span></span></div>
    {/if}
  {:else if projected}
    <div class="slots">
      <span class="lbl">진출 예상</span>
      {#each top4(projected) as [t, q]}
        <div class="slot"><span class="disp">{t}</span><div class="sb"><i style="width:{(q * 100).toFixed(0)}%"></i></div><span class="num">{pct(q)}</span></div>
      {/each}
    </div>
  {/if}

  <footer>
    <span class="hint">
      {#if !known}
      {:else if state === 'done'}{pa != null ? '막대 = 경기 전 예측' : ''}
      {:else if state === 'mine'}다시 누르면 해제 · 내 기기에만 저장
      {:else if state === 'live' || state === 'wait'}경기 전 예측 유지 · 결과 들어오면 갱신
      {:else}팀을 누르면 이긴다고 가정{/if}
    </span>
    <a class="detail-link" href={`#/game/${bid}/${m.id}`}>세트별 예측 ›</a>
  </footer>
</article>

<style>
  .mc {
    background: var(--surface); margin-bottom: 10px;
    clip-path: var(--clip-chamfer);
  }
  .mc.final { box-shadow: inset 0 2px 0 var(--accent); }
  header { display: flex; align-items: center; gap: 8px; height: 34px; padding: 0 12px; border-bottom: 1px solid var(--line); min-width: 0; }
  .when { font-family: var(--font-display); font-weight: 600; font-size: 15px; white-space: nowrap; }
  .meta { font-size: 12px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
  .st { margin-left: auto; flex: none; font-size: 11px; font-weight: 600; color: var(--muted); height: 20px; display: flex; align-items: center; gap: 5px; padding: 0 7px; white-space: nowrap; }
  .st.live { background: var(--accent); color: var(--accent-ink); font-weight: 800; }
  /* static dot; one glow pulse on entry, never an endless loop */
  .st.live i { width: 5px; height: 5px; border-radius: 50%; background: var(--accent-ink); }
  .st.live { animation: pulse 1s var(--ease-out) 1; }
  @keyframes pulse { 0% { box-shadow: 0 0 0 0 var(--accent-glow); } 60% { box-shadow: 0 0 0 8px transparent; } }
  @media (prefers-reduced-motion: reduce) { .st.live { animation: none; } }
  .st.done { color: var(--text-dim); box-shadow: inset 0 0 0 1px var(--line-strong); }
  .st.mine { color: var(--accent); font-weight: 700; outline: 1px dashed var(--accent); outline-offset: -1px; }

  .sides { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 2px; padding: 10px 10px 0; }
  .side {
    min-height: 64px; padding: 8px 10px; border: 0; background: var(--surface-2); color: var(--text);
    text-align: left; cursor: pointer; display: flex; flex-direction: column; justify-content: center; gap: 2px; min-width: 0;
    transition: background var(--dur-fast) var(--ease-out);
  }
  .side.right { text-align: right; align-items: flex-end; }
  .side:disabled { cursor: default; }
  .tn { max-width: 100%; font-size: 21px; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .q { font-size: 26px; line-height: 1; color: var(--text-dim); }
  .res { font-size: 12px; color: var(--muted); display: flex; gap: 4px; align-items: center; white-space: nowrap; }
  .res b { font-weight: 700; }
  .res.accent { color: var(--accent); font-weight: 700; }
  .side.lose { background: var(--bg-2); }
  .side.lose .tn { color: var(--muted); }
  .side.win { background: var(--text); color: var(--accent-ink); }
  .side.win .tn { font-weight: 800; }
  .side.win .res { color: var(--accent-ink); font-weight: 600; }
  .side.win .res b { font-weight: 800; }
  .side.pick {
    background: var(--hatch-assume), var(--surface-2);
    outline: 1px dashed var(--accent); outline-offset: -1px;
    animation: flash var(--dur-slow) var(--ease-snap);
  }
  @keyframes flash { 0% { box-shadow: inset 0 0 0 40px var(--accent-glow); } 100% { box-shadow: inset 0 0 0 40px transparent; } }
  @media (prefers-reduced-motion: reduce) { .side.pick { animation: none; } }
  .hatchbar { height: 4px; margin: 6px 10px 0; background: repeating-linear-gradient(135deg, var(--accent) 0 3px, transparent 3px 6px); opacity: .6; }
  .vbar > span:first-child { transition: width var(--dur-slow) var(--ease-out); }

  .slots { padding: 10px 12px 0; display: flex; flex-direction: column; gap: 7px; }
  .slots .lbl { font-size: 12px; color: var(--muted); }
  .slot { display: grid; grid-template-columns: minmax(0, 1fr) 120px 40px; gap: 10px; align-items: center; }
  .slot .disp { font-size: 17px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .slot .num { font-weight: 700; font-size: 17px; text-align: right; }
  .sb { height: 3px; background: var(--bg); }
  .sb i { display: block; height: 3px; background: var(--text-dim); }

  footer { display: flex; align-items: center; justify-content: space-between; height: var(--hit); padding: 0 4px 0 12px; }
  .hint { font-size: 11px; color: var(--muted); }
</style>
