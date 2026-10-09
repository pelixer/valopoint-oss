<script>
  import { app } from '../lib/store.svelte.js';
  import { REGION_LABEL, fx } from '../lib/format.js';
  import { buildContext } from '../lib/profile.js';

  let region = $state('ALL');
  let q = $state('');
  const norm = (x) => (x ?? '').toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '');
  let ctx = $derived(buildContext(app.model, app.brackets));
  // bar scale: weakest to strongest team, tick at the 500 average
  let lo = $derived(Math.min(...app.model.teams.map((t) => t.pp)));
  let hi = $derived(Math.max(...app.model.teams.map((t) => t.pp)));
  const bar = (pp) => `${(((pp - lo) / (hi - lo || 1)) * 100).toFixed(1)}%`;
  let tick = $derived(`${(((500 - lo) / (hi - lo || 1)) * 100).toFixed(1)}%`);
  let teams = $derived(app.model.teams
    .map((t, i) => ({
      ...t, rank: i + 1, inEvent: ctx.participants.has(t.name),
      names: (t.roster ?? []).map((id) => app.model.players[id]?.name ?? id).join(' · '),
    }))
    .filter((t) => (region === 'ALL' || t.region === region)
      && (norm(t.name).includes(norm(q.trim())) || norm(t.names).includes(norm(q.trim())))));
  let hero = $derived(teams[0]);
  let duo = $derived(teams.slice(1, 3));
  let rest = $derived(teams.slice(3));
  const href = (t) => `#/team/${encodeURIComponent(t.name)}`;
</script>

<div class="kicker">Power ranking · {app.model.teams.length} teams</div>
<h1 style="margin-bottom:0">팀 파워 랭킹</h1>

<div class="search-box">
  <input type="search" placeholder="팀 또는 선수 검색" bind:value={q} id="team-search" autocomplete="off" aria-label="팀 검색" />
  {#if q}<button onclick={() => (q = '')} aria-label="검색어 지우기">×</button>{/if}
</div>
<div class="chips" role="group" aria-label="지역">
  {#each ['ALL', 'AMER', 'EMEA', 'PAC', 'CN'] as r}
    <button class="chip" class:on={region === r} onclick={() => (region = r)} aria-pressed={region === r}><span>{r === 'ALL' ? '전체' : REGION_LABEL[r]}</span></button>
  {/each}
</div>
<div class="note">
  <span>팀 PP = 현재 로스터 5명 PP 합(맵 풀 평균, 지역 보정 포함). 500 = 평균 팀.</span>
  {#if ctx.participants.size}<span class="ev"><i class="pin"></i>{ctx.eventName} 참가</span>{/if}
</div>

{#if hero}
  <a class="hero" href={href(hero)}>
    <span class="corner tr"></span><span class="corner bl"></span>
    <div class="hero-grid">
      <span class="hero-rank num">{hero.rank}</span>
      <div class="hero-name">
        <div class="line"><span class="badge {hero.region}">{hero.region}</span>{#if hero.inEvent}<i class="pin"></i>{/if}</div>
        <span class="disp">{hero.name}</span>
      </div>
      <div class="hero-pp">
        <span class="lbl">Team PP</span>
        <span class="num">{fx(hero.pp, 0)}</span>
      </div>
    </div>
    <div class="hero-roster disp">{hero.names}</div>
    <div class="bar hero-bar"><span style="width:{bar(hero.pp)}"></span><i class="tick" style="left:{tick}"></i></div>
  </a>
{/if}

{#if duo.length}
  <div class="duo">
    {#each duo as t, i}
      <a class="duo-card rise" style="--i:{i + 1}" href={href(t)}>
        <div class="duo-top"><span class="num r">{t.rank}</span><span class="num p">{fx(t.pp, 0)}</span></div>
        <span class="disp nm">{t.name}</span>
        <div class="line"><span class="badge {t.region}">{t.region}</span>{#if t.inEvent}<i class="pin"></i>{/if}</div>
        <span class="ros">{t.names}</span>
        <div class="bar thin"><span style="width:{bar(t.pp)}; background:var(--text)"></span><i class="tick" style="left:{tick}; background:var(--muted)"></i></div>
      </a>
    {/each}
  </div>
{/if}

<div class="rest">
  {#each rest as t, i (t.name)}
    <a class="trow rise" style="--i:{Math.min(i, 12) + 3}" href={href(t)}>
      <span class="num r">{t.rank}</span>
      <div class="mid">
        <div class="line"><span class="disp nm">{t.name}</span><span class="badge sm {t.region}">{t.region}</span>{#if t.inEvent}<i class="pin"></i>{/if}</div>
        <span class="ros">{t.names}</span>
      </div>
      <span class="num p">{fx(t.pp, 0)}</span>
      <div class="tbar"><span style="width:{bar(t.pp)}"></span><i style="left:{tick}"></i></div>
    </a>
  {/each}
</div>

{#if !teams.length}
  <div class="empty">
    <span class="kicker" style="justify-content:center">No results</span>
    <b>일치하는 팀이 없습니다</b>
    <button class="btn" onclick={() => { q = ''; region = 'ALL'; }}>검색·필터 지우기</button>
  </div>
{/if}

<style>
  .note { font-size: 12px; line-height: 1.5; color: var(--muted); margin-top: 6px; display: flex; gap: 10px; flex-wrap: wrap; }
  .ev { display: inline-flex; align-items: center; gap: 5px; }
  .line { display: flex; align-items: center; gap: 6px; min-width: 0; }
  a { color: inherit; text-decoration: none; }

  .hero {
    position: relative; display: block; margin-top: 16px; padding: 14px 16px;
    background: linear-gradient(115deg, rgba(242, 67, 79, .16) 0 30%, var(--surface) 30%);
    clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px);
    animation: wipe var(--dur-slow) var(--ease-out) backwards;
  }
  .hero-grid { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 14px; align-items: end; }
  .hero-rank { font-weight: 800; font-size: 76px; line-height: .78; color: var(--accent); }
  .hero-name { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
  .hero-name .disp {
    font-size: 30px; line-height: .95; padding-bottom: .16em; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2;
    -webkit-box-orient: vertical; overflow-wrap: anywhere;
  }
  .hero-pp { display: flex; flex-direction: column; align-items: flex-end; }
  .hero-pp .lbl { font-family: var(--font-display); font-weight: 600; font-size: 11px; letter-spacing: var(--tracking-label); color: var(--text-dim); text-transform: uppercase; }
  .hero-pp .num { font-weight: 800; font-size: 44px; line-height: .9; }
  .hero-roster { margin-top: 12px; font-weight: 600; font-size: 15px; color: var(--text-dim); letter-spacing: .01em; }
  .hero-bar { margin-top: 10px; overflow: visible; }

  .duo { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 8px; margin-top: 8px; }
  .duo-card {
    position: relative; padding: 12px; background: var(--surface); display: flex; flex-direction: column; gap: 6px; min-width: 0;
    clip-path: var(--clip-chamfer);
  }
  .duo-top { display: flex; align-items: flex-start; justify-content: space-between; }
  .duo-top .r { font-weight: 800; font-size: 40px; line-height: .8; color: var(--text-dim); }
  .duo-top .p { font-weight: 800; font-size: 32px; line-height: .85; }
  .duo-card .nm { font-size: 21px; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .duo-card .ros { font-size: 11px; line-height: 1.45; color: var(--muted); }
  .bar.thin { height: 3px; margin-top: 2px; overflow: visible; }

  .rest { margin-top: 8px; }
  .trow {
    display: grid; grid-template-columns: 30px minmax(0, 1fr) auto; gap: 4px 12px; align-items: center;
    padding: 11px 0 10px; border-bottom: 1px solid var(--line);
  }
  .trow .r { font-weight: 700; font-size: 22px; color: var(--muted); text-align: right; }
  .mid { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .trow .nm { font-size: 20px; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
  .trow .ros { font-size: 12px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .trow .p { font-weight: 700; font-size: 26px; }
  .tbar { grid-column: 2 / 4; height: 2px; background: var(--surface-2); position: relative; margin-top: 4px; }
  .tbar span { position: absolute; left: 0; top: 0; bottom: 0; background: var(--muted); }
  .tbar i { position: absolute; top: -2px; bottom: -2px; width: 1px; background: var(--text-dim); }

  .empty { margin-top: 16px; padding: 28px 16px; background: var(--surface); display: flex; flex-direction: column; align-items: center; gap: 10px; text-align: center; }
  .empty b { font-size: 16px; }
  .empty .btn { background: none; box-shadow: inset 0 0 0 1px var(--line-strong); padding: 0 16px; }
</style>
