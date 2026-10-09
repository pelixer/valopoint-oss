<script>
  import { app } from '../lib/store.svelte.js';
  import { ROLE_LABEL, cap, fx, wikiLink } from '../lib/format.js';
  import Radar from '../lib/Radar.svelte';
  import RoleGlyph from '../lib/RoleGlyph.svelte';
  import TraitTags from '../lib/TraitTags.svelte';
  import { badges, buildContext } from '../lib/profile.js';

  let { id } = $props();
  let p = $derived(app.model.players[id]);
  let agents = $derived(p ? Object.entries(p.agents).sort((a, b) => b[1].rounds - a[1].rounds) : []);
  let agentRounds = $derived(agents.reduce((s, [, v]) => s + v.rounds, 0));
  let maps = $derived(p ? Object.keys(p.grid).sort() : []);
  let axes = $derived(app.model.style_axes ?? []);
  let ctx = $derived(buildContext(app.model, app.brackets));
  let tags = $derived(p ? badges({ id, ...p }, ctx) : []);
  let prof = $derived(p?.profile ?? {});
  let ranks = $derived.by(() => {
    if (!p) return [];
    const P = ctx.byPP;
    const r = (f) => P.filter(f).findIndex((x) => x.id === id) + 1;
    return [['전체', r(() => true), P.length], [ROLE_LABEL[p.role] ?? p.role, r((x) => x.role === p.role), P.filter((x) => x.role === p.role).length],
      [p.region, r((x) => x.region === p.region), P.filter((x) => x.region === p.region).length]];
  });
  const roleOf = (a) => app.model.roles?.[a] ?? 'flex';
  const RC = { AMER: 'var(--r-amer)', EMEA: 'var(--r-emea)', PAC: 'var(--r-pac)', CN: 'var(--r-cn)' };
  // big name shrinks for long handles so it stays on one line at 390px
  let nameSize = $derived(p ? Math.min(84, Math.floor(600 / Math.max(p.name.length, 1))) : 84);

  // timeline: one point per event (PP of that event); international events are red diamonds
  const TW = 334, TH = 160, PL = 26, PR = 8, PB = 20, PT = 10;
  let tl = $derived(prof.timeline ?? []);
  let tlY = $derived.by(() => {
    const v = [...tl.map((e) => e[3]), p?.pp ?? 100];
    const lo = Math.min(80, ...v) - 5, hi = Math.max(120, ...v) + 5;
    return { lo, hi, y: (x) => PT + (1 - (x - lo) / (hi - lo)) * (TH - PT - PB) };
  });
  const tlX = (i, n) => PL + (n <= 1 ? (TW - PL - PR) / 2 : (i / (n - 1)) * (TW - PL - PR));
  let years = $derived.by(() => {
    const out = [];
    tl.forEach((e, i) => { const y = e[1].slice(0, 4); if (!out.length || out.at(-1)[0] !== y) out.push([y, i]); });
    return out;
  });
  const sgn = (x) => `${x >= 0 ? '+' : '−'}${Math.abs(x).toFixed(1)}`;
  const arrow = (x) => `${x >= 0 ? '▲' : '▼'} ${Math.abs(x).toFixed(1)}`;
  // the two most distinctive axes (furthest from the median), for a one-line summary
  let traits = $derived(p?.style ? axes.map((a) => ({ ...a, v: p.style[a.key] }))
    .sort((x, y) => Math.abs(y.v - 50) - Math.abs(x.v - 50)).slice(0, 2) : []);

  // map x agent heat: the six most played agents as columns, colour = vs this player's own PP
  let cols = $derived(agents.slice(0, 6).map(([a]) => a));
  function cell(v) {
    if (v == null) return 'transparent';
    const t = Math.max(-1, Math.min(1, ((v - (p.pp - 4)) / 8) * 2 - 1));
    const a = Math.abs(t);
    return t >= 0 ? `rgba(242,67,79,${(0.06 + 0.64 * a).toFixed(2)})` : `rgba(91,157,255,${(0.06 + 0.57 * a).toFixed(2)})`;
  }
  let eventName = $derived(app.model.meta.current_event?.name?.replace(/^Valorant /, ''));
</script>

{#if !p}
  <p>선수를 찾을 수 없습니다.</p>
{:else}
  <section class="hero">
    <span class="corner tr"></span>
    <div class="role"><RoleGlyph role={p.role} color="var(--text)" /><b>{ROLE_LABEL[p.role] ?? p.role}</b><span class="muted">· {p.rounds} 라운드</span></div>
    <h1 class="name disp" style="font-size:{nameSize}px">{p.name}</h1>
    <div class="teamline">
      <a class="teamlink" href={`#/team/${encodeURIComponent(p.team)}`}><i style="background:{RC[p.region]}"></i><span class="disp">{p.team} <em>›</em></span></a>
      <span class="badge {p.region}">{p.region}</span>
    </div>
    <div class="ppline">
      <div class="ppbig"><span class="num">{fx(p.pp)}</span><b>PP</b></div>
      <div class="ranks">
        {#each ranks as [lbl, r, n]}<span class="lbl">{lbl}</span><span class="num">{r}<small> /{n}</small></span>{/each}
      </div>
    </div>
    <div style="margin-top:14px"><TraitTags {tags} /></div>
    {#if wikiLink(id)}<div class="wiki"><a href={wikiLink(id)} target="_blank" rel="noopener">Liquipedia ↗</a></div>{/if}
  </section>

  <div class="sec"><div><span class="k">Form · Career</span><span class="t">폼 · 커리어</span></div></div>
  <div class="grid2">
    <div class="stat">
      <span class="lbl">최근 60일 폼</span>
      {#if prof.form}
        <div><span class="big">{prof.form.recent.toFixed(1)}</span> <span class="delta" class:up={prof.form.delta >= 0} class:down={prof.form.delta < 0}>{arrow(prof.form.delta)}</span></div>
        <span class="sub">이전 {prof.form.before.toFixed(1)} · {prof.form.maps}맵</span>
      {:else}<span class="sub">최근 경기 없음</span>{/if}
    </div>
    <div class="stat">
      <span class="lbl">꾸준함 (최근 1년)</span>
      {#if prof.steady}
        <span class="word">{prof.steady.rel ? `기복 ${Math.abs((1 - prof.steady.rel) * 100).toFixed(0)}% ${prof.steady.rel <= 1 ? '적음' : '많음'}` : fx(prof.steady.sd, 0)}</span>
        <span class="sub">같은 역할 평균 대비 · 하위 25% 경기 {prof.steady.floor.toFixed(0)}</span>
      {:else}<span class="sub">20맵 미만</span>{/if}
    </div>
    <div class="stat">
      <span class="lbl">국제전 (최근 2년)</span>
      {#if prof.intl}
        <div><span class="big">{prof.intl.pp.toFixed(1)}</span> <span class="delta" class:up={prof.intl.big_stage >= 0} class:down={prof.intl.big_stage < 0}>{arrow(prof.intl.big_stage)}</span></div>
        <span class="sub">{prof.intl.events}회 · {prof.intl.map_wins}승 {prof.intl.maps - prof.intl.map_wins}패 · 변화량 = 리그 대비</span>
      {:else}<span class="sub">출전 기록 없음</span>{/if}
    </div>
    <div class="stat" class:hot={prof.current}>
      <span class="lbl">{prof.current ? eventName : '최근 지역리그'}</span>
      {#if prof.current}
        <span class="big">{prof.current.pp.toFixed(1)}</span>
        <span class="sub">{prof.current.maps}맵 {prof.current.map_wins}승 {prof.current.maps - prof.current.map_wins}패</span>
      {:else if prof.league}
        <span class="big">{prof.league.pp.toFixed(1)}</span>
        <span class="sub">{prof.league.event} · {prof.league.maps}맵 {prof.league.map_wins}승</span>
      {:else}<span class="sub">–</span>{/if}
    </div>
  </div>
  {#if prof.intl?.list?.length}
    <p class="note">국제전 출전: {prof.intl.list.join(' · ')}</p>
  {/if}

  {#if tl.length}
    <div class="sec"><div><span class="k">By event</span><span class="t">대회별 퍼포먼스</span></div></div>
    <div class="card">
      <svg viewBox="0 0 {TW} {TH}" style="width:100%; display:block" role="img" aria-label="대회별 PP 추이">
        {#each [80, 100, 120, 140].filter((t) => t > tlY.lo && t < tlY.hi) as t}
          <line x1={PL} x2={TW - PR} y1={tlY.y(t)} y2={tlY.y(t)} stroke={t === 100 ? 'var(--line-strong)' : 'var(--line)'} stroke-dasharray={t === 100 ? '' : '2 4'} />
          <text x={PL - 6} y={tlY.y(t) + 4} text-anchor="end" font-size="11" fill={t === 100 ? 'var(--text-dim)' : 'var(--muted)'} font-family="var(--font-num)">{t}</text>
        {/each}
        <line x1={PL} x2={TW - PR} y1={tlY.y(p.pp)} y2={tlY.y(p.pp)} stroke="var(--accent)" stroke-opacity="0.7" stroke-dasharray="3 3" />
        <polyline class="draw" pathLength="1" fill="none" stroke="var(--muted)" stroke-width="1.2" points={tl.map((e, i) => `${tlX(i, tl.length)},${tlY.y(e[3])}`).join(' ')} />
        {#each tl as e, i}
          {@const x = tlX(i, tl.length)}
          {@const y = tlY.y(e[3])}
          {@const r = 2.5 + Math.min(4, e[2] / 8)}
          {#if e[4]}<rect x={x - r} y={y - r} width={2 * r} height={2 * r} fill="var(--accent)" transform="rotate(45 {x} {y})" />
          {:else}<circle cx={x} cy={y} {r} fill="var(--surface)" stroke="var(--text-dim)" stroke-width="1.5" />{/if}
        {/each}
        {#each years as [yr, i]}
          <text x={tlX(i, tl.length)} y={TH - 4} font-size="11" fill="var(--muted)" font-family="var(--font-num)">{yr}</text>
        {/each}
        <text x={TW - PR} y={tlY.y(p.pp) - 5} text-anchor="end" font-size="12" font-weight="700" fill="var(--accent)" font-family="var(--font-num)">{fx(p.pp)}</text>
      </svg>
      <div class="legend">
        <span><i class="pin" style="width:8px; height:8px"></i>국제전</span>
        <span><i class="ring"></i>지역리그</span>
        <span>크기 = 맵 수</span>
        <span><i style="width:14px; border-top:1px dashed var(--accent)"></i>현재 PP</span>
      </div>
      {#each [...tl].reverse() as e}
        <div class="ev">
          <span class="dot" style="background:{e[4] ? 'var(--accent)' : 'transparent'}"></span>
          <span class="evn" style="font-weight:{e[4] ? 700 : 400}">{e[0]}</span>
          <span class="num muted">{e[1].slice(0, 7)}</span>
          <span class="rec">{e[5]}승 {e[2] - e[5]}패</span>
          <span class="num evp">{e[3].toFixed(0)}</span>
        </div>
      {/each}
      <p class="note">대회별 맵 퍼포먼스(상대 보정, PP 척도). 대회 하나는 표본이 작아 흔들림이 큽니다.</p>
    </div>
  {/if}

  <div class="sec"><div><span class="k">Attributes</span><span class="t">속성</span></div></div>
  <div class="card">
    {#if p.style}
      <Radar {axes} series={[{ values: p.style, color: 'var(--accent)', label: p.name }, { values: Object.fromEntries(axes.map((a) => [a.key, 50])), color: 'var(--muted)', label: '같은 역할 평균', dashed: true }]} />
      <div style="font-weight:700; font-size:14px; margin-top:12px">
        {#each traits as t, i}{i ? ' · ' : ''}{t.label} {t.v >= 50 ? '높음' : '낮음'}{/each}
      </div>
      <p class="note" style="margin-top:4px">같은 역할군 선수 대비 백분위(최근 1년, {p.style.maps}맵). 50 = 역할 평균. 스타일 묘사용이며 승률 예측에는 쓰지 않습니다.</p>
    {:else}
      <p class="note" style="margin:0">최근 1년 출전 맵이 10개 미만이라 속성을 계산하지 않았습니다.</p>
    {/if}
  </div>

  <div class="sec"><div><span class="k">Map × agent</span><span class="t">맵 × 요원 PP</span></div></div>
  <div class="card heat">
    <div class="hrow head" style="--n:{cols.length}">
      <span class="muted">맵</span>
      {#each cols as a}<span class="disp">{cap(a)}</span>{/each}
    </div>
    {#each maps as m}
      <div class="hrow" style="--n:{cols.length}">
        <div class="hm"><span class="disp">{cap(m)}</span><span class="num muted">{p.maps[m]?.rounds ?? 0}R</span></div>
        {#each cols as a}
          {@const v = p.grid[m]?.[a]}
          {@const on = (p.mix[m]?.[a] ?? 0) >= 0.2}
          <span class="num hc" style="background:{cell(v)}; opacity:{on ? 1 : 0.42}; font-weight:{on ? 700 : 500}">{fx(v)}</span>
        {/each}
      </div>
    {/each}
    <div class="hlegend">
      <span class="num">−4</span><i></i><span class="num">+4 PP</span>
      <span style="margin-left:6px">흐린 칸 = 이 맵에서 거의 안 쓴 요원{#if agents.length > cols.length} · 아래에 {agents.length - cols.length}명 더{/if}</span>
    </div>
    <p class="note">색은 이 선수 평균 대비. 맵·요원별 차이는 표본이 적어 약 90맵 분량의 데이터가 쌓여야 절반만큼 반영되도록 보수적으로 추정합니다.</p>
  </div>

  <div class="sec" style="margin-bottom:8px"><div><span class="k">Agents · {agents.length}</span><span class="t">요원별</span></div></div>
  {#each agents as [a, v], i}
    <div class="ag rise" style="--i:{Math.min(i, 12)}">
      <div class="code"><span class="disp">{a.replace('/', '').slice(0, 3).toUpperCase()}</span><span class="g"><RoleGlyph role={roleOf(a)} size={6} color="var(--text-dim)" /></span></div>
      <div class="agm">
        <div class="agt"><span class="disp">{cap(a)}</span><span class="num muted">{v.rounds}R</span><span class="num share">{((v.rounds / Math.max(agentRounds, 1)) * 100).toFixed(1)}%</span></div>
        <div class="agbar"><span style="width:{((v.rounds / agents[0][1].rounds) * 100).toFixed(1)}%"></span></div>
      </div>
      <span class="num agp">{fx(v.pp)}</span>
    </div>
  {/each}
{/if}

<style>
  .hero {
    position: relative; padding: 16px 16px 14px;
    background: linear-gradient(115deg, var(--surface) 0 62%, rgba(242, 67, 79, .14) 62%);
    clip-path: polygon(14px 0, 100% 0, 100% calc(100% - 14px), calc(100% - 14px) 100%, 0 100%, 0 14px);
    animation: wipe var(--dur-slow) var(--ease-out) backwards;
  }
  .role { display: flex; align-items: center; gap: 8px; font-size: 13px; }
  .role b { font-weight: 600; }
  .name { font-weight: 800; line-height: .86; margin: 8px 0 -.2em; padding-bottom: .2em; letter-spacing: -.005em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .teamline { display: flex; align-items: center; gap: 6px; margin-top: 6px; height: var(--hit); }
  .teamlink { display: flex; align-items: stretch; height: 30px; background: var(--bg); color: var(--text); text-decoration: none; min-width: 0; }
  .teamlink i { width: 3px; flex: none; }
  .teamlink span { display: flex; align-items: center; gap: 6px; padding: 0 10px; font-size: 18px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .teamlink em { font-style: normal; color: var(--muted); font-size: 16px; }
  .ppline { display: flex; align-items: flex-end; justify-content: space-between; margin-top: 6px; padding-top: 12px; border-top: 1px solid var(--line-strong); position: relative; }
  .ppline::before { content: ""; position: absolute; top: -1px; left: 0; width: 56px; height: 2px; background: var(--accent); }
  .ppbig { display: flex; align-items: flex-end; gap: 6px; }
  .ppbig .num { font-weight: 800; font-size: 68px; line-height: .82; }
  .ppbig b { font-family: var(--font-display); font-weight: 700; font-size: 16px; letter-spacing: .1em; color: var(--accent); margin-bottom: 2px; }
  .ranks { display: grid; grid-template-columns: auto auto; gap: 2px 10px; align-items: baseline; }
  .ranks .lbl { font-size: 12px; color: var(--muted); text-align: right; }
  .ranks .num { font-weight: 700; font-size: 20px; }
  .ranks small { color: var(--muted); font-size: 14px; font-weight: 600; }
  .wiki { display: flex; justify-content: flex-end; margin: 4px -6px -10px 0; }
  .wiki a { height: var(--hit); display: flex; align-items: center; padding: 0 6px; font-size: 13px; font-weight: 600; text-decoration: none; }

  .note { font-size: 12px; line-height: 1.5; color: var(--muted); margin: 8px 0 0; }
  .card .note { font-size: 11px; line-height: 1.55; }
  .legend { display: flex; gap: 14px; flex-wrap: wrap; font-size: 11px; color: var(--muted); margin: 6px 0 10px; }
  .legend span { display: inline-flex; align-items: center; gap: 5px; }
  .legend .ring { width: 8px; height: 8px; border-radius: 50%; box-shadow: inset 0 0 0 1.5px var(--text-dim); }
  .ev { display: grid; grid-template-columns: 12px minmax(0, 1fr) 56px 64px 36px; gap: 6px; align-items: center; padding: 7px 0; border-top: 1px solid var(--line); font-size: 13px; }
  .ev .dot { width: 6px; height: 6px; transform: rotate(45deg); }
  .ev .evn { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .ev .num.muted { font-size: 14px; }
  .ev .rec { font-size: 12px; color: var(--text-dim); text-align: right; }
  .ev .evp { font-weight: 700; font-size: 17px; text-align: right; }
  .draw { stroke-dasharray: 1; stroke-dashoffset: 1; animation: draw var(--dur-slow) var(--ease-out) forwards; }
  @keyframes draw { to { stroke-dashoffset: 0; } }
  @media (prefers-reduced-motion: reduce) { .draw { animation: none; stroke-dashoffset: 0; } }

  .heat { padding: 10px 10px 12px; }
  .hrow { display: grid; grid-template-columns: 66px repeat(var(--n), minmax(0, 1fr)); gap: 1px; margin-bottom: 1px; }
  .hrow.head { align-items: end; padding-bottom: 6px; font-size: 11px; }
  .hrow.head .disp { font-size: 13px; text-align: center; color: var(--text-dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .hm { display: flex; flex-direction: column; justify-content: center; height: 36px; }
  .hm .disp { font-size: 15px; line-height: 1; }
  .hm .num { font-size: 12px; }
  .hc { display: flex; align-items: center; justify-content: center; height: 36px; font-size: 14px; }
  .hlegend { display: flex; align-items: center; gap: 8px; margin-top: 10px; font-size: 11px; color: var(--muted); flex-wrap: wrap; }
  .hlegend .num { font-size: 13px; }
  .hlegend i { flex: 1; min-width: 60px; height: 6px; background: linear-gradient(90deg, rgba(91, 157, 255, .63), var(--surface-2) 50%, rgba(242, 67, 79, .7)); }

  .ag { display: grid; grid-template-columns: 36px minmax(0, 1fr) 52px; gap: 12px; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--line); }
  .code {
    position: relative; width: 36px; height: 36px; display: grid; place-items: center; background: var(--surface-2);
    box-shadow: inset 0 0 0 1px var(--line-strong); clip-path: polygon(6px 0, 100% 0, 100% 100%, 0 100%, 0 6px);
  }
  .code .disp { font-size: 13px; letter-spacing: .04em; }
  .code .g { position: absolute; right: 3px; bottom: 3px; line-height: 0; }
  .agm { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
  .agt { display: flex; align-items: baseline; gap: 8px; }
  .agt .disp { font-size: 18px; line-height: 1; }
  .agt .num { font-size: 14px; }
  .agt .share { margin-left: auto; color: var(--text-dim); }
  .agbar { height: 3px; background: var(--surface-2); }
  .agbar span { display: block; height: 3px; background: var(--muted); }
  .agp { font-weight: 700; font-size: 22px; text-align: right; }
</style>
