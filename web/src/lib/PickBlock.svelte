<script>
  // One match in "내 대진표" (design 4a · PickBlock, 9 states).
  // Tap a team to pick; hold a team (400ms) or tap the header for the team sheet.
  import { shortRound } from './pickem.js';

  let { m, group, sides, st, title = null, locked = false, pick = null, winner = null, probs = null, model = null, when = '', foot = null, onpick, oninfo } = $props();
  // probs: [pA, pB] series odds (0-1) or null; model: team the model favours (frozen once locked)
  const BADGE = {
    open: ['경기 전', ''], pick: ['내 픽', 'pick'], tbd: ['팀 미정', 'line'], wait: ['잠김 · 결과 대기', 'line'],
    noresp: ['미응답', 'line'], hit: ['○ 적중', 'hit'], miss: ['× 빗나감', 'miss'], void: ['! 무효', 'void'],
  };
  let badge = $derived(BADGE[st] ?? BADGE.open);
  // a void pick is shown in the slot it was meant for: the open slot if there is one,
  // otherwise as an extra row above the two real teams
  let voidPick = $derived(st === 'void' && pick && pick !== sides.a.t && pick !== sides.b.t ? pick : null);
  let voidAt = $derived(!voidPick ? -1 : !sides.a.t ? 0 : !sides.b.t ? 1 : -1);
  let rows = $derived.by(() => {
    const r = [sides.a, sides.b].map((s, i) => (i === voidAt ? { ...s, t: voidPick, voided: true, seat: s.label } : s));
    return voidPick && voidAt === -1 ? [{ t: voidPick, voided: true, seat: null, extra: true }, ...r] : r;
  });

  let timer = null, held = false, sx = 0, sy = 0;
  function down(e) {
    held = false; sx = e.clientX; sy = e.clientY;
    clearTimeout(timer);
    timer = setTimeout(() => { held = true; oninfo?.(); }, 400);
  }
  function move(e) { if (Math.hypot(e.clientX - sx, e.clientY - sy) > 8) clearTimeout(timer); }
  function up() { clearTimeout(timer); }
  function tap(t) {
    if (held) { held = false; return; }
    if (!locked && t) onpick?.(t);
  }
</script>

<article class="pb" class:locked id={`pk-${m.id}`}>
  <button class="hd" onclick={() => oninfo?.()} aria-label="{shortRound(m)} 팀 정보">
    <span class="g"><i style="background:{group.color}"></i>{group.label}</span>
    <span class="rd">{(title ?? shortRound(m)).replace(/^[A-H]조 /, '')}</span>
    <span class="num wh">{when}</span>
    <span class="bd {badge[1]}">{#if locked}<svg viewBox="0 0 12 12" width="9" height="9" aria-hidden="true"><path d="M3 5.5V4a3 3 0 0 1 6 0v1.5M2.5 5.5h7v5h-7z" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>{/if}{badge[0]}</span>
  </button>
  <div class="rows">
    {#each rows as s, ri}
      {@const i = rows.length === 3 ? ri - 1 : ri}
      {#if !s.t}
        <div class="row tbd"><span></span><span></span><span class="tn">{s.waiting ? `${s.label} · 결과 대기` : s.label}</span><span></span><span></span></div>
      {:else}
        {@const sel = pick === s.t}
        {@const voided = !!s.voided}
        {@const dim = !!pick && !sel && !voided}
        {@const p = probs && !voided && i >= 0 ? probs[i] : null}
        <button class="row" class:sel class:voided class:dim class:fade={locked && !!pick && !sel && !winner}
          class:pred={s.kind === 'pred'} disabled={locked || voided} aria-pressed={sel}
          onpointerdown={down} onpointermove={move} onpointerup={up} onpointercancel={up} onpointerleave={up}
          oncontextmenu={(e) => e.preventDefault()} onclick={() => tap(s.t)}>
          <span class="bar"></span>
          <span class="dia"></span>
          <span class="tn"><span class="nm">{s.t}</span>{#if voided}<small>{s.extra ? '내 픽 · 이 경기에 올 수 없음' : `자리: ${s.seat ?? ''}`}</small>{/if}</span>
          <span class="tags">
            {#if voided}<em class="out">탈락</em>{/if}
            {#if winner === s.t}<em class="win">✓ 승</em>{/if}
            {#if model === s.t}<em class="m" title="모델 픽">M</em>{/if}
          </span>
          <span class="num pc" class:hi={model === s.t}>{p == null ? (locked || !probs ? '–' : '') : `${Math.round(p * 100)}%`}</span>
        </button>
      {/if}
    {/each}
  </div>
  {#if foot}<p class="foot">{foot}</p>{/if}
</article>

<style>
  .pb { background: var(--surface); clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px); scroll-margin-top: calc(var(--topbar-h) + 60px); }
  .hd {
    width: 100%; display: flex; align-items: center; gap: 8px; height: 32px; padding: 0 10px; border: 0; border-bottom: 1px solid var(--line);
    background: none; color: var(--text); cursor: pointer; text-align: left; min-width: 0;
  }
  .g { display: flex; align-items: center; gap: 5px; flex: none; font-size: 11px; font-weight: 700; }
  .g i { width: 7px; height: 7px; }
  .rd { font-size: 12px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
  .wh { flex: none; font-family: var(--font-display); font-size: 14px; color: var(--muted); }
  .bd {
    margin-left: auto; flex: none; display: flex; align-items: center; gap: 4px; height: 20px; padding: 0 6px; font-size: 11px; font-weight: 700;
    color: var(--muted); white-space: nowrap;
  }
  .bd.pick { color: var(--pick); box-shadow: inset 0 0 0 1px var(--pick); }
  .bd.line { color: var(--text-dim); box-shadow: inset 0 0 0 1px var(--line-strong); }
  .bd.hit { color: var(--res-hit); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--res-hit) 40%, transparent); }
  .bd.miss { color: var(--res-miss); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--res-miss) 40%, transparent); }
  .bd.void { color: var(--res-void); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--res-void) 40%, transparent); }
  .rows { display: flex; flex-direction: column; gap: 2px; padding: 8px; }
  .row {
    display: grid; grid-template-columns: 3px 22px minmax(0, 1fr) auto 46px; align-items: center; min-height: 48px; width: 100%;
    border: 0; padding: 0; background: var(--surface-2); color: var(--text); text-align: left; cursor: pointer;
    -webkit-touch-callout: none; user-select: none; -webkit-user-select: none; touch-action: manipulation;
    transition: background var(--dur-fast) var(--ease-snap), opacity var(--dur-fast);
  }
  .row:disabled { cursor: default; }
  .row .bar { align-self: stretch; background: transparent; transform-origin: center; }
  .row .dia { justify-self: center; width: 9px; height: 9px; transform: rotate(45deg); box-shadow: inset 0 0 0 1.5px var(--line-strong); }
  .row .tn {
    font-family: var(--font-display); font-weight: 700; font-size: 20px; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    display: flex; flex-direction: column;
  }
  .row .tn small { font-family: var(--font-body); font-size: 11px; font-weight: 500; color: var(--muted); text-decoration: none; }
  .row .tn .nm { overflow: hidden; text-overflow: ellipsis; }
  .row.pred .tn { text-decoration: underline dotted var(--pick-pred-line); text-underline-offset: 4px; }
  .row.sel { background: linear-gradient(90deg, var(--pick-wash), var(--surface-2) 72%); }
  .row.sel .bar { background: var(--pick); animation: grow var(--dur-fast) var(--ease-snap); }
  .row.sel .dia { background: var(--pick); box-shadow: none; animation: pop var(--dur-fast) var(--ease-snap); }
  .row.sel .tn { font-weight: 800; }
  .row.dim .tn { color: var(--text-dim); }
  .row.fade { opacity: var(--lock-dim); }
  .row.voided { background: color-mix(in srgb, var(--res-void) 7%, transparent); }
  .row.voided .bar { background: var(--res-void); }
  .row.voided .dia { box-shadow: inset 0 0 0 1.5px var(--res-void); background: none; }
  .row.voided .tn .nm { color: var(--text-dim); text-decoration: line-through; }
  .row.voided:disabled { cursor: default; }
  .out { height: 18px; padding: 0 5px; display: grid; place-items: center; font-size: 11px; font-weight: 700; color: var(--res-void); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--res-void) 45%, transparent); }
  @keyframes grow { from { transform: scaleY(0); } }
  @keyframes pop { from { transform: rotate(45deg) scale(.6); } }
  @media (prefers-reduced-motion: reduce) { .row.sel .bar, .row.sel .dia { animation: none; } }
  .tags { display: flex; align-items: center; gap: 4px; padding-left: 6px; }
  .tags em { font-style: normal; }
  .win { height: 18px; padding: 0 5px; display: grid; place-items: center; font-size: 11px; font-weight: 800; background: var(--text); color: var(--accent-ink); }
  .m { width: 16px; height: 16px; display: grid; place-items: center; box-shadow: inset 0 0 0 1px var(--muted); font-family: var(--font-display); font-weight: 700; font-size: 11px; color: var(--text-dim); }
  .pc { text-align: right; padding-right: 10px; font-weight: 700; font-size: 18px; color: var(--muted); }
  .pc.hi { color: var(--text); }
  .row.tbd { cursor: default; background: transparent; outline: 1px dashed var(--slot-tbd); outline-offset: -1px; }
  .row.tbd .tn { font-family: var(--font-body); font-weight: 500; font-size: 14px; color: var(--muted); }
  .foot { margin: -2px 10px 0; padding: 0 0 10px; font-size: 11px; line-height: 1.5; color: var(--muted); }
</style>
