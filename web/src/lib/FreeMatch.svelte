<script>
  // Free match-up (design v2 · 08), formerly the match tab: any two teams, Bo1/3/5.
  import { app, persisted } from './store.svelte.js';
  import { cap, fx, pct } from './format.js';
  import Picker from './Picker.svelte';

  let { preset = null } = $props();
  const saved = persisted('match', {});
  let a = $state(preset ?? saved.get().a ?? app.model.teams[0]?.name);
  let b = $state(saved.get().b ?? app.model.teams[1]?.name);
  if (a === b) b = app.model.teams.find((t) => t.name !== a)?.name;
  let bo = $state(saved.get().bo ?? 3);
  $effect(() => saved.set({ a, b, bo }));
  let picking = $state(null);

  let f = $derived(a && b && a !== b ? app.engine.series(a, b, bo) : null);
  let maps = $derived(f ? Object.entries(f.pmap).sort((x, y) => y[1] - x[1]) : []);
  const T = (n) => app.engine.teams[n];
  function pick(side, name) {
    if (side === 'a') { if (name === b) b = a; a = name; } else { if (name === a) a = b; b = name; }
    picking = null;
  }
</script>

<div class="plates">
  <button class="plate pa" onclick={() => (picking = 'a')}>
    <i class="edge"></i>
    <span class="badge sm {T(a)?.region}">{T(a)?.region}</span>
    <span class="disp nm">{a}</span>
    <span class="pp num">{fx(T(a)?.pp, 0)} PP <em>▼ 변경</em></span>
  </button>
  <button class="plate pb" onclick={() => (picking = 'b')}>
    <i class="edge"></i>
    <span class="badge sm {T(b)?.region}">{T(b)?.region}</span>
    <span class="disp nm">{b}</span>
    <span class="pp num"><em>변경 ▼</em> {fx(T(b)?.pp, 0)} PP</span>
  </button>
  <div class="mid">
    <span class="vs disp">VS</span>
    <button class="swap" onclick={() => ([a, b] = [b, a])} aria-label="좌우 맞바꾸기">⇄</button>
  </div>
</div>

<div class="bos" role="group" aria-label="세트 수">
  {#each [1, 3, 5] as n}<button class:on={bo === n} onclick={() => (bo = n)} aria-pressed={bo === n}>Bo{n}</button>{/each}
</div>

{#if f}
  <div class="series">
    <div class="sr">
      <div class="col"><span class="tn">{a}</span><span class="num big red">{pct(f.p)}</span></div>
      <span class="lbl">Series · Bo{bo}</span>
      <div class="col r"><span class="tn">{b}</span><span class="num big">{pct(1 - f.p)}</span></div>
    </div>
    <div class="vbar thick"><span style="width:{(f.p * 100).toFixed(1)}%"></span><span></span></div>
    <div class="foot"><span>팀 PP {fx(T(a)?.pp, 0)} vs {fx(T(b)?.pp, 0)}</span><span>맵 순서 = 예상 밴픽</span></div>
  </div>

  <div class="sec"><div><span class="k">Map win · {a}</span><span class="t">맵별 승률</span></div></div>
  <div class="card mw">
    {#each maps as [m, p]}
      <div class="mrow">
        <span class="disp">{cap(m)}</span>
        <span class="num l">{pct(p)}</span>
        <div class="mbar"><span style="width:{(p * 100).toFixed(1)}%"></span><span></span><i></i></div>
        <span class="num rr">{pct(1 - p)}</span>
      </div>
    {/each}
    <div class="mfoot"><span>왼쪽 = {a}</span><span>오른쪽 = {b}</span></div>
  </div>

  <div class="sec"><div><span class="k">Pick · ban</span><span class="t">예상 맵 순서</span></div></div>
  {#each [[a, f.veto.aFirst, 'var(--side-a)'], [b, f.veto.bFirst, 'var(--side-b)']] as [n, seq, c]}
    <div class="order" style="box-shadow: inset 3px 0 0 {c}">
      <span class="ol">{n} 선밴</span>
      <div class="seq disp">{#each seq as m, i}{#if i}<em>›</em>{/if}<small>{i + 1}</small>{cap(m)}{/each}</div>
    </div>
  {/each}
  <p class="note">각 팀이 자기 승률이 가장 낮은 맵을 밴하고 가장 높은 맵을 픽한다고 가정. 두 순서의 평균이 시리즈 승률입니다.</p>
{/if}

{#if picking}
  <Picker side={picking} current={picking === 'a' ? a : b} other={picking === 'a' ? b : a}
    onpick={(n) => pick(picking, n)} onclose={() => (picking = null)} />
{/if}

<style>
  .plates { position: relative; margin-top: 14px; display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 2px; }
  .plate {
    position: relative; min-height: 132px; padding: 14px 14px 12px; border: 0; color: var(--text); text-align: left; cursor: pointer;
    display: flex; flex-direction: column; gap: 6px; align-items: flex-start; min-width: 0;
  }
  .pa { background: linear-gradient(115deg, rgba(242, 67, 79, .22) 0 46%, var(--surface) 46%); clip-path: polygon(12px 0, 100% 0, 100% 100%, 0 100%, 0 12px); }
  .pb { background: linear-gradient(295deg, rgba(238, 232, 222, .12) 0 46%, var(--surface) 46%); clip-path: polygon(0 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%); align-items: flex-end; text-align: right; }
  .edge { position: absolute; top: 12px; bottom: 0; width: 4px; }
  .pa .edge { left: 0; background: var(--side-a); }
  .pb .edge { right: 0; top: 0; bottom: 12px; background: var(--side-b); }
  .nm { font-weight: 800; font-size: 30px; line-height: .95; max-width: 100%; overflow-wrap: anywhere; padding-right: 22px; }
  .pb .nm { padding: 0 0 0 22px; }
  .pp { margin-top: auto; font-weight: 700; font-size: 15px; color: var(--text-dim); }
  .pp em { font-style: normal; color: var(--muted); font-size: 13px; }
  .mid { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center; gap: 4px; }
  .vs { font-weight: 800; font-size: 22px; letter-spacing: .04em; background: var(--bg); padding: 0 6px; }
  .swap {
    width: var(--hit); height: var(--hit); display: grid; place-items: center; border: 0; background: var(--bg); box-shadow: inset 0 0 0 1px var(--line-strong);
    color: var(--text); font-size: 18px; cursor: pointer; clip-path: var(--clip-chamfer-sm);
  }
  .bos { display: grid; grid-template-columns: repeat(3, 1fr); margin-top: 10px; background: var(--bg-2); box-shadow: inset 0 0 0 1px var(--line); }
  .bos button { height: var(--hit); border: 0; background: none; color: var(--text); font-family: var(--font-display); font-size: 18px; font-weight: 700; cursor: pointer; }
  .bos button.on { background: var(--accent); color: var(--accent-ink); }
  .series { margin-top: 12px; padding: 14px 12px 12px; background: var(--surface); clip-path: var(--clip-chamfer); }
  .sr { display: flex; justify-content: space-between; align-items: flex-end; gap: 6px; }
  .col { display: flex; flex-direction: column; min-width: 0; }
  .col.r { align-items: flex-end; }
  .tn { font-size: 11px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 140px; }
  .big { font-weight: 800; font-size: 56px; line-height: .85; }
  .big.red { color: var(--accent); }
  .lbl { font-family: var(--font-display); font-weight: 600; font-size: 12px; letter-spacing: var(--tracking-label); color: var(--muted); margin-bottom: 6px; text-transform: uppercase; white-space: nowrap; }
  .vbar.thick { height: 8px; margin-top: 12px; }
  .vbar > span:first-child { transition: width var(--dur-slow) var(--ease-out); }
  .foot { display: flex; justify-content: space-between; margin-top: 6px; font-size: 11px; color: var(--muted); }
  .mw { padding: 2px 12px; }
  .mrow { display: grid; grid-template-columns: 70px 36px minmax(0, 1fr) 36px; gap: 8px; align-items: center; height: 40px; border-bottom: 1px solid var(--line); }
  .mrow .disp { font-size: 18px; }
  .mrow .num { font-weight: 700; font-size: 17px; }
  .mrow .l { color: var(--accent); }
  .mrow .rr { text-align: right; color: var(--text-dim); }
  .mbar { position: relative; display: flex; height: 6px; gap: 2px; }
  .mbar span:first-child { background: var(--side-a); transition: width var(--dur-slow) var(--ease-out); }
  .mbar span:nth-child(2) { flex: 1; background: var(--side-b); opacity: .85; }
  .mbar i { position: absolute; left: 50%; top: -4px; bottom: -4px; width: 1px; background: var(--bg); }
  .mfoot { display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); padding: 8px 0 6px; }
  .order { background: var(--surface); padding: 10px 12px; display: flex; flex-direction: column; gap: 8px; margin-bottom: 6px; }
  .ol { font-size: 12px; color: var(--muted); }
  .seq { display: flex; align-items: center; gap: 6px; font-size: 20px; flex-wrap: wrap; }
  .seq small { font-family: var(--font-body); font-size: 12px; color: var(--muted); font-weight: 400; }
  .seq em { font-style: normal; color: var(--line-strong); }
  .note { font-size: 11px; line-height: 1.55; color: var(--muted); margin: 8px 0 0; }
</style>
