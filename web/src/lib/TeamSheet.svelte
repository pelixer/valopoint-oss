<script>
  // Team info sheet for one match of "내 대진표" (design 4a · P4).
  import { app } from './store.svelte.js';
  import { cap, fx, pct } from './format.js';
  import RoleGlyph from './RoleGlyph.svelte';
  import { badges, buildContext } from './profile.js';
  import { shortRound } from './pickem.js';

  let { m, bid, group, a, b, pick = null, locked = false, when = '', onpick, onclose } = $props();
  let bo = $derived(m.best_of ?? 3);
  let s = $derived(a && b ? app.engine.series(a, b, bo) : null);
  let TA = $derived(app.engine.teams[a]), TB = $derived(app.engine.teams[b]);
  let rank = (n) => app.model.teams.findIndex((t) => t.name === n) + 1;
  let lines = $derived(s?.lines ? Object.entries(s.lines).sort((x, y) => (+y[0][0] - +y[0][2]) - (+x[0][0] - +x[0][2])) : []);
  let maps = $derived(s ? Object.entries(s.pmap).map(([mp, p]) => ({ mp, p, pr: s.presence?.[mp] ?? null }))
    .sort((x, y) => (y.pr ?? y.p) - (x.pr ?? x.p)) : []);
  let ctx = $derived(buildContext(app.model, app.brackets));
  const keys = (T) => (T?.roster ?? []).map((id) => ({ id, ...app.model.players[id] })).filter((p) => p.name)
    .sort((x, y) => y.pp - x.pp).slice(0, 3);
  const RC = { AMER: 'var(--r-amer)', EMEA: 'var(--r-emea)', PAC: 'var(--r-pac)', CN: 'var(--r-cn)' };
  let axes = $derived(app.model.style_axes ?? []);
  const style = (T) => {
    const ps = (T?.roster ?? []).map((id) => app.model.players[id]).filter((p) => p?.style);
    return ps.length ? Object.fromEntries(axes.map((x) => [x.key, ps.reduce((acc, p) => acc + p.style[x.key], 0) / ps.length])) : null;
  };
  let sa = $derived(style(TA)), sb = $derived(style(TB));
  const form = (T) => (T?.recent ?? []).slice(-10);
  const arrow = (d) => `${d >= 0 ? '▲' : '▼'} ${Math.abs(d).toFixed(1)}`;
</script>

<div class="bg" role="presentation" onclick={onclose}></div>
<div class="sheet" role="dialog" aria-modal="true" aria-label="{a} 대 {b} 팀 정보" tabindex="-1" onkeydown={(e) => e.key === 'Escape' && onclose()}>
  <div class="grab"><span></span></div>
  <div class="hd">
    <span class="g"><i style="background:{group.color}"></i>{group.label}</span>
    <span class="rd">{shortRound(m).replace(/^[A-H]조 /, '')}</span>
    <span class="num wh">{when} · Bo{bo}</span>
    <button class="x" onclick={onclose} aria-label="닫기">×</button>
  </div>
  <div class="body">
    <div class="vs">
      {#each [[a, TA], [b, TB]] as [n, T], i}
        <div class="tm" class:r={i === 1}>
          <span class="disp nm">{n ?? '팀 미정'}</span>
          {#if T}<span class="meta"><span class="badge sm {T.region}">{T.region}</span>{rank(n)}위 · <b class="num">{fx(T.pp, 0)}</b></span>{/if}
        </div>
        {#if i === 0}<span class="v">VS</span>{/if}
      {/each}
    </div>

    {#if s}
      <div class="ser">
        <div class="sr"><span class="num big">{pct(s.p)}{#if s.p > 0.5}<em class="m">M</em>{/if}</span><span class="lbl">시리즈 승률 · Bo{bo}</span><span class="num big dim">{#if s.p < 0.5}<em class="m">M</em>{/if}{pct(1 - s.p)}</span></div>
        <div class="vbar" style="height:6px"><span style="width:{(s.p * 100).toFixed(1)}%"></span><span></span></div>
      </div>

      {#if lines.length}
        <div class="sub">세트 스코어 · {a} 기준</div>
        <div class="dist">{#each lines as [k, q]}<div><span class="num">{k.replace('-', '–')}</span><span class="num q">{pct(q)}</span></div>{/each}</div>
      {/if}

      <div class="subrow"><span class="sub">맵별 승률 · {a} 기준</span><span class="cap">{s.presence ? '등장 확률 순' : '승률 순'}</span></div>
      {#each maps as x}
        <div class="mp">
          <span class="disp">{cap(x.mp)}</span>
          <div class="pr">{#if x.pr != null}<span class="pb"><i style="width:{(x.pr * 100).toFixed(0)}%"></i></span><span class="num">{pct(x.pr)}</span>{/if}</div>
          <div class="mb"><span style="width:{(x.p * 100).toFixed(1)}%"></span><span></span><i></i></div>
          <span class="num">{pct(x.p)}</span>
        </div>
      {/each}
      {#if s.seqs?.length}<div class="cap">예상 맵 순서: {s.seqs[0][0].map(cap).join(' → ')} ({pct(s.seqs[0][1], 1)})</div>{/if}

      <div class="sub" style="margin-top:6px">키 플레이어</div>
      <div class="keys">
        {#each [TA, TB] as T}
          <div class="kcol">
            {#each keys(T) as p, j}
              {@const tags = badges(p, ctx)}
              <a class="kp" class:top={j === 0} href={`#/player/${p.id}`} onclick={onclose}>
                <div class="kl"><span class="kn"><RoleGlyph role={p.role} size={8} color="var(--text-dim)" /><span class="disp">{p.name}</span></span><span class="num">{fx(p.pp)}</span></div>
                {#if j === 0 && p.profile?.form}<span class="kf" class:up={p.profile.form.delta >= 0}>{arrow(p.profile.form.delta)} 최근 폼{#if tags[0]} · {tags[0].label}{/if}</span>{/if}
              </a>
            {/each}
          </div>
        {/each}
      </div>
      <div class="cap">팀별 PP 상위 3명 · 누르면 선수 상세</div>

      {#if sa && sb}
        <div class="sub" style="margin-top:6px">속성 · 최근 10맵</div>
        <div class="attrs">
          {#each axes as ax}
            <span class="num l">{Math.round(sa[ax.key])}</span>
            <div class="ab l"><i style="width:{sa[ax.key]}%"></i></div>
            <span class="ak">{ax.label}</span>
            <div class="ab r"><i style="width:{sb[ax.key]}%"></i></div>
            <span class="num r">{Math.round(sb[ax.key])}</span>
          {/each}
        </div>
        <div class="forms">
          {#each [TA, TB] as T}
            <div class="cells">{#each form(T) as r}<span class:w={r[3] > r[4]}>{r[3] > r[4] ? 'W' : 'L'}</span>{/each}</div>
          {/each}
        </div>
      {/if}
      <a class="full" href={`#/game/${bid}/${m.id}`} onclick={onclose}>경기 상세 전체 ›</a>
    {:else}
      <p class="cap" style="margin-top:12px">앞 경기를 골라야 두 팀이 정해집니다.</p>
    {/if}
  </div>
  {#if a && b}
    <div class="foot">
      {#each [a, b] as t}
        <button class="pk" class:sel={pick === t} disabled={locked} onclick={() => onpick(t)}>
          <span class="bar"></span><span class="dia"></span>
          <span class="t"><span class="disp">{t}</span><small>{locked ? (pick === t ? '내 픽 · 잠김' : '잠김') : pick === t ? '내 픽 · 다시 누르면 해제' : '이 팀으로 고르기'}</small></span>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  a { color: inherit; text-decoration: none; }
  .bg { position: fixed; inset: 0; z-index: 30; background: rgba(5, 7, 11, .72); animation: fade var(--dur-med) var(--ease-out); }
  @keyframes fade { from { opacity: 0; } }
  .sheet {
    position: fixed; left: 0; right: 0; bottom: 0; z-index: 31; max-width: 720px; margin: 0 auto; max-height: 88vh;
    background: var(--bg-2); box-shadow: 0 -1px 0 var(--line-strong);
    clip-path: polygon(16px 0, 100% 0, 100% 100%, 0 100%, 0 16px); display: flex; flex-direction: column;
    animation: up var(--dur-med) var(--ease-out);
  }
  @keyframes up { from { transform: translateY(100%); } }
  @media (prefers-reduced-motion: reduce) { .sheet, .bg { animation: fade var(--dur-fast) linear; } }
  .grab { display: flex; justify-content: center; padding-top: 8px; }
  .grab span { width: 36px; height: 4px; background: var(--line-strong); }
  .hd { display: flex; align-items: center; gap: 8px; height: var(--hit); padding: 0 4px 0 16px; }
  .g { display: flex; align-items: center; gap: 5px; font-size: 11px; font-weight: 700; }
  .g i { width: 7px; height: 7px; }
  .rd { font-size: 13px; font-weight: 600; }
  .wh { font-family: var(--font-display); font-size: 15px; color: var(--muted); }
  .x { margin-left: auto; width: var(--hit); height: var(--hit); border: 0; background: none; font-size: 20px; color: var(--text-dim); cursor: pointer; }
  .body { overflow-y: auto; overscroll-behavior: contain; padding: 4px 16px 12px; display: flex; flex-direction: column; gap: 10px; }
  .vs { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); gap: 8px; align-items: end; }
  .tm { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
  .tm.r { align-items: flex-end; text-align: right; }
  .nm { font-weight: 800; font-size: 30px; line-height: .95; overflow-wrap: anywhere; }
  .meta { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--muted); }
  .meta b { font-size: 15px; color: var(--text); }
  .v { font-family: var(--font-display); font-weight: 600; font-size: 14px; color: var(--muted); padding-bottom: 22px; }
  .ser { display: flex; flex-direction: column; gap: 6px; margin-top: 4px; }
  .sr { display: flex; justify-content: space-between; align-items: baseline; }
  .big { display: flex; align-items: center; gap: 6px; font-weight: 800; font-size: 34px; line-height: 1; }
  .big.dim { color: var(--text-dim); }
  .m { font-style: normal; width: 18px; height: 18px; display: grid; place-items: center; box-shadow: inset 0 0 0 1px var(--muted); font-weight: 700; font-size: 12px; color: var(--text-dim); }
  .lbl, .cap { font-size: 11px; color: var(--muted); }
  .lbl { font-size: 12px; }
  .sub { font-size: 12px; font-weight: 700; color: var(--text-dim); }
  .subrow { display: flex; justify-content: space-between; align-items: baseline; }
  .dist { display: grid; grid-auto-columns: minmax(0, 1fr); grid-auto-flow: column; gap: 4px; }
  .dist > div { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 8px 0; background: var(--surface); }
  .dist .num { font-weight: 700; font-size: 15px; }
  .dist .q { font-weight: 400; font-size: 17px; color: var(--text-dim); }
  .mp { display: grid; grid-template-columns: 62px 64px minmax(0, 1fr) 36px; gap: 8px; align-items: center; height: 28px; }
  .mp .disp { font-size: 16px; }
  .mp > .num { font-weight: 700; font-size: 16px; text-align: right; }
  .pr { display: flex; align-items: center; gap: 4px; }
  .pr .pb { flex: 1; height: 3px; background: var(--surface-2); }
  .pr .pb i { display: block; height: 3px; background: var(--muted); }
  .pr .num { font-size: 12px; color: var(--muted); width: 26px; text-align: right; }
  .mb { position: relative; display: flex; height: 6px; gap: 1px; }
  .mb span:first-child { background: var(--side-a); }
  .mb span:nth-child(2) { flex: 1; background: var(--side-b); }
  .mb i { position: absolute; left: 50%; top: -3px; bottom: -3px; width: 1px; background: var(--bg-2); }
  .keys { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 6px; }
  .kcol { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
  .kp { display: flex; flex-direction: column; gap: 4px; padding: 0 10px; min-height: 40px; justify-content: center; background: var(--surface); }
  .kp.top { padding: 10px; box-shadow: inset 0 2px 0 var(--accent); }
  .kl { display: flex; align-items: baseline; justify-content: space-between; gap: 6px; }
  .kn { display: flex; align-items: center; gap: 6px; min-width: 0; }
  .kn .disp { font-size: 17px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .kp.top .kn .disp, .kp.top .kl > .num { font-size: 22px; font-weight: 800; }
  .kl > .num { font-weight: 700; font-size: 17px; }
  .kf { font-size: 11px; color: var(--bad); font-weight: 700; }
  .kf.up { color: var(--good); }
  .attrs { display: grid; grid-template-columns: 26px minmax(0, 1fr) 48px minmax(0, 1fr) 26px; gap: 4px 6px; align-items: center; font-size: 11px; }
  .attrs .num { font-weight: 700; font-size: 14px; color: var(--text-dim); }
  .attrs .r { text-align: right; }
  .attrs .ak { text-align: center; color: var(--text-dim); }
  .attrs .ab { position: relative; height: 5px; background: var(--bg); }
  .attrs .ab i { position: absolute; top: 0; bottom: 0; }
  .attrs .ab.l i { right: 0; background: var(--side-a); }
  .attrs .ab.r i { left: 0; background: var(--side-b); }
  .forms { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .cells { display: grid; grid-template-columns: repeat(10, minmax(0, 1fr)); gap: 2px; }
  .cells span { height: 18px; display: grid; place-items: center; font-family: var(--font-display); font-weight: 800; font-size: 11px; color: var(--bad); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--bad) 50%, transparent); }
  .cells span.w { background: var(--good); color: var(--bg); box-shadow: none; }
  .full { align-self: flex-end; height: var(--hit); display: flex; align-items: center; font-size: 13px; font-weight: 600; color: var(--accent); }
  .foot { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 6px; padding: 10px 16px calc(12px + env(safe-area-inset-bottom)); box-shadow: 0 -1px 0 var(--line); }
  .pk { height: 56px; display: grid; grid-template-columns: 3px 22px minmax(0, 1fr); align-items: center; border: 0; padding: 0; background: var(--surface-2); color: var(--text); text-align: left; cursor: pointer; }
  .pk:disabled { cursor: default; opacity: .7; }
  .pk .bar { align-self: stretch; }
  .pk .dia { justify-self: center; width: 9px; height: 9px; transform: rotate(45deg); box-shadow: inset 0 0 0 1.5px var(--line-strong); }
  .pk .t { display: flex; flex-direction: column; min-width: 0; }
  .pk .disp { font-size: 19px; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pk small { font-size: 11px; color: var(--muted); }
  .pk.sel { background: linear-gradient(90deg, rgba(242, 67, 79, .22), var(--surface-2) 80%); }
  .pk.sel .bar { background: var(--pick); }
  .pk.sel .dia { background: var(--pick); box-shadow: none; }
  .pk.sel small { color: var(--pick); font-weight: 700; }
</style>
