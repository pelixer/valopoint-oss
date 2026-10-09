<script>
  import { app } from '../lib/store.svelte.js';
  import { ROLE_LABEL, cap, fx, wikiLink } from '../lib/format.js';
  import Radar from '../lib/Radar.svelte';
  import RoleGlyph from '../lib/RoleGlyph.svelte';

  let { name } = $props();
  let t = $derived(app.engine.teams[name]);
  let rank = $derived(app.model.teams.findIndex((x) => x.name === name) + 1);
  const RC = { AMER: 'var(--r-amer)', EMEA: 'var(--r-emea)', PAC: 'var(--r-pac)', CN: 'var(--r-cn)' };
  let roster = $derived(t ? t.roster.map((id) => ({ id, ...app.model.players[id] })).filter((p) => p.name) : []);
  const mainAgent = (p) => Object.entries(p.agents ?? {}).sort((a, b) => b[1].rounds - a[1].rounds)[0]?.[0];
  // card fill: player PP on the league-wide range
  let ppRange = $derived.by(() => {
    const v = Object.values(app.model.players).map((p) => p.pp);
    return [Math.min(...v), Math.max(...v)];
  });
  const fill = (pp) => `${(((pp - ppRange[0]) / (ppRange[1] - ppRange[0] || 1)) * 62 + 8).toFixed(0)}%`;
  let best = $derived(roster.length ? Math.max(...roster.map((p) => p.pp)) : null);

  let axes = $derived(app.model.style_axes ?? []);
  let teamStyle = $derived.by(() => {
    const ps = roster.filter((p) => p.style);
    if (!ps.length) return null;
    return Object.fromEntries(axes.map((a) => [a.key, ps.reduce((s, p) => s + p.style[a.key], 0) / ps.length]));
  });

  // map PP relative to the team's pool average; bar centred on the team PP
  let maps = $derived(t ? [...app.model.maps].map((m) => ({ m, v: 500 + 1000 * t.theta[m] })).sort((a, b) => b.v - a.v) : []);
  let span = $derived(Math.max(8, ...maps.map((x) => Math.abs(x.v - (t?.pp ?? 500)))));
  const sgn = (x) => `${x >= 0 ? '+' : '−'}${Math.abs(x).toFixed(1)}`;
  let nameSize = $derived(t ? Math.min(64, Math.floor(560 / Math.max(t.name.length, 1))) : 64);
</script>

{#if !t}
  <p>팀을 찾을 수 없습니다.</p>
{:else}
  <section class="hero" style="--rc:{RC[t.region]}">
    <i class="edge"></i>
    <div class="top"><span class="badge {t.region}">{t.region}</span><span class="lbl">Power rank</span><span class="num rk">#{rank} / {app.model.teams.length}</span></div>
    <h1 class="disp name" style="font-size:{nameSize}px">{t.name}</h1>
    <div class="ppline">
      <div class="ppbig"><span class="num">{fx(t.pp, 0)}</span><b>Team PP</b></div>
      <div class="vs500"><span>평균 팀 500 대비</span><span class="num" class:up={t.pp >= 500} class:down={t.pp < 500}>{t.pp >= 500 ? '▲' : '▼'} {t.pp >= 500 ? '+' : '−'}{Math.abs(t.pp - 500).toFixed(0)}</span></div>
    </div>
    <div class="links">
      <a href={`#/bracket?mode=free&a=${encodeURIComponent(t.name)}`}>이 팀으로 대결 ›</a>
      {#if wikiLink(t.name)}<a class="wl" href={wikiLink(t.name)} target="_blank" rel="noopener">Liquipedia ↗</a>{/if}
    </div>
  </section>

  <div class="sec"><div><span class="k">Lineup · {roster.length}</span><span class="t">로스터</span></div></div>
  <div class="lineup" style="--n:{roster.length}">
    {#each roster as p, i}
      {@const a = mainAgent(p)}
      <a class="lc rise" class:best={p.pp === best} style="--i:{i}" href={`#/player/${p.id}`}>
        <div class="fill" style="height:{fill(p.pp)}"></div>
        <div class="fill-top" style="bottom:{fill(p.pp)}"></div>
        <div class="lcin">
          <RoleGlyph role={p.role} size={10} color="var(--text)" />
          <span class="role">{ROLE_LABEL[p.role] ?? p.role}</span>
          {#if a}<span class="ag disp">{a.replace('/', '').slice(0, 3).toUpperCase()}</span>{/if}
          <span class="num pp">{fx(p.pp)}</span>
          <span class="disp nm">{p.name}</span>
          <span class="num rd">{p.rounds}R</span>
        </div>
      </a>
    {/each}
  </div>
  <p class="note">채움 높이 = 선수 PP({fx(ppRange[0])}–{fx(ppRange[1])} 범위). 배지 = 가장 많이 쓴 요원. 카드를 누르면 선수 상세.</p>

  {#if teamStyle}
    <div class="sec"><div><span class="k">Attributes · roster avg</span><span class="t">팀 속성</span></div></div>
    <div class="card">
      <Radar {axes} series={[{ values: teamStyle, color: 'var(--accent)', label: t.name }, { values: Object.fromEntries(axes.map((a) => [a.key, 50])), color: 'var(--muted)', label: '평균 50', dashed: true }]} />
      <p class="note" style="font-size:11px">로스터 5명의 역할 내 백분위 평균.</p>
    </div>
  {/if}

  <div class="sec"><div><span class="k">Map pool · {maps.length}</span><span class="t">맵별 팀 PP</span></div></div>
  <div class="card maps">
    {#each maps as x, i}
      {@const d = x.v - t.pp}
      {@const w = Math.min(50, (Math.abs(d) / span) * 50)}
      {@const tone = i === 0 ? 'good' : i === maps.length - 1 ? 'bad' : d >= 0 ? 'pos' : 'neg'}
      <div class="mrow">
        <span class="disp">{cap(x.m)}</span>
        <div class="mb"><i class="mid"></i><i class="v {tone}" style="left:{d >= 0 ? 50 : 50 - w}%; width:{Math.max(w, 1)}%"></i></div>
        <span class="num mv">{fx(x.v)}</span>
        <span class="num d {tone}">{i === 0 ? '▲ ' : i === maps.length - 1 ? '▼ ' : ''}{sgn(d)}</span>
      </div>
    {/each}
    <div class="mfoot"><span>가운데 선 = 팀 PP {fx(t.pp, 0)}</span><span>▲ 강한 맵 · ▼ 약한 맵</span></div>
  </div>
{/if}

<style>
  a { color: inherit; text-decoration: none; }
  .hero {
    position: relative; padding: 16px 16px 6px;
    background: linear-gradient(115deg, var(--surface) 0 64%, color-mix(in srgb, var(--rc) 14%, transparent) 64%);
    clip-path: polygon(14px 0, 100% 0, 100% calc(100% - 14px), calc(100% - 14px) 100%, 0 100%, 0 14px);
    animation: wipe var(--dur-slow) var(--ease-out) backwards;
  }
  .edge { position: absolute; left: 0; top: 14px; bottom: 0; width: 4px; background: var(--rc); }
  .top { display: flex; align-items: center; gap: 8px; }
  .lbl { font-family: var(--font-display); font-weight: 600; font-size: 12px; letter-spacing: var(--tracking-label); color: var(--text-dim); text-transform: uppercase; }
  .rk { font-weight: 800; font-size: 16px; color: var(--accent); }
  .name { font-weight: 800; line-height: .9; margin: 10px 0 0; letter-spacing: 0; overflow-wrap: anywhere; }
  .ppline { display: flex; align-items: flex-end; justify-content: space-between; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--line-strong); position: relative; }
  .ppline::before { content: ""; position: absolute; top: -1px; left: 0; width: 56px; height: 2px; background: var(--accent); }
  .ppbig { display: flex; align-items: flex-end; gap: 6px; }
  .ppbig .num { font-weight: 800; font-size: 60px; line-height: .82; }
  .ppbig b { font-family: var(--font-display); font-weight: 700; font-size: 15px; letter-spacing: .1em; color: var(--accent); margin-bottom: 2px; text-transform: uppercase; }
  .vs500 { display: flex; flex-direction: column; align-items: flex-end; font-size: 12px; color: var(--muted); }
  .vs500 .num { font-weight: 700; font-size: 22px; }
  .vs500 .up { color: var(--good); }
  .vs500 .down { color: var(--bad); }
  .links { display: flex; justify-content: space-between; margin: 2px -6px 0; }
  .links a { height: var(--hit); display: flex; align-items: center; padding: 0 6px; font-size: 13px; font-weight: 600; }
  .links .wl { color: var(--accent); }

  .lineup { display: grid; grid-template-columns: repeat(var(--n), minmax(0, 1fr)); gap: 4px; }
  .lc {
    position: relative; height: 208px; background: var(--surface); overflow: hidden;
    clip-path: polygon(0 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%);
  }
  .lc.best { box-shadow: inset 0 0 0 1px var(--accent); }
  .fill { position: absolute; left: 0; right: 0; bottom: 0; background: linear-gradient(180deg, rgba(242, 67, 79, .28), rgba(242, 67, 79, .06)); }
  .fill-top { position: absolute; left: 0; right: 0; height: 2px; background: var(--accent); }
  .lcin { position: relative; display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 10px 4px 0; height: 100%; }
  .role { font-size: 11px; color: var(--text-dim); }
  .ag { font-size: 11px; letter-spacing: .04em; padding: 1px 4px; background: var(--bg); box-shadow: inset 0 0 0 1px var(--line-strong); }
  .lcin .pp { margin-top: auto; font-weight: 800; font-size: 24px; line-height: 1; }
  .lcin .nm { width: 100%; text-align: center; font-size: 17px; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .lcin .rd { font-size: 12px; color: var(--muted); padding-bottom: 10px; }
  .note { font-size: 11px; line-height: 1.5; color: var(--muted); margin: 8px 0 0; }

  .maps { padding: 4px 12px; }
  .mrow { display: grid; grid-template-columns: 72px minmax(0, 1fr) 54px 52px; gap: 10px; align-items: center; height: 42px; border-bottom: 1px solid var(--line); }
  .mrow .disp { font-size: 18px; }
  .mb { position: relative; height: 10px; }
  .mb .mid { position: absolute; left: 50%; top: -4px; bottom: -4px; width: 1px; background: var(--line-strong); }
  .mb .v { position: absolute; top: 2px; height: 6px; transition: width var(--dur-slow) var(--ease-out); }
  .v.good { background: var(--good); }
  .v.bad { background: var(--bad); }
  .v.pos { background: var(--text-dim); }
  .v.neg { background: var(--line-strong); }
  .mrow .mv { font-weight: 700; font-size: 18px; text-align: right; }
  .d { font-weight: 700; font-size: 14px; text-align: right; color: var(--muted); white-space: nowrap; }
  .d.good { color: var(--good); }
  .d.bad { color: var(--bad); }
  .mfoot { display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); padding: 8px 0 6px; }
</style>
