<script>
  import SourceCredit from './lib/SourceCredit.svelte';
  import { app, loadModel } from './lib/store.svelte.js';
  import Teams from './pages/Teams.svelte';
  import Team from './pages/Team.svelte';
  import Players from './pages/Players.svelte';
  import Player from './pages/Player.svelte';
  import Home from './pages/Home.svelte';
  import Bracket from './pages/Bracket.svelte';
  import Model from './pages/Model.svelte';
  import Game from './pages/Game.svelte';

  loadModel();

  const tabs = [
    { id: 'home', label: '홈', icon: 'M12 3l9 9-9 9-9-9zM12 9l3 3-3 3-3-3z' },
    { id: 'teams', label: '팀', icon: 'M4 6h16M4 12h16M4 18h10' },
    { id: 'players', label: '선수', icon: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0' },
    { id: 'bracket', label: '대진', icon: 'M4 5h5v5H4zM4 14h5v5H4zM9 7.5h3v9H9M12 12h4M16 9.5h4v5h-4z' },
    { id: 'model', label: '모델', icon: 'M4 19V9m6 10V5m6 14v-7m4 7H3' },
  ];
  const tabOf = { team: 'teams', player: 'players', game: 'bracket' };
  const tabLabel = Object.fromEntries(tabs.map((t) => [t.id, t.label]));
  let active = $derived(tabOf[app.route.page] ?? app.route.page);
  let detail = $derived(app.route.page in tabOf);
  let info = $state(false);

  // in-app navigation depth: go back in history when we came from inside the app,
  // otherwise to the tab the detail page belongs to
  let depth = 0;
  window.addEventListener('hashchange', () => (depth += 1));
  function back(e) {
    if (depth > 0) { e.preventDefault(); depth -= 2; history.back(); }
  }
</script>

<header class="topbar">
  <div class:home={!detail}>
    {#if detail}
      <a class="backlink" href={`#/${active}`} onclick={back}><b>‹</b>{tabLabel[active]}</a>
      <a class="logo" href="#/home" aria-label="valopoint 홈"><span style="font-size:18px">valopoint</span></a>
    {:else}
      <a class="logo" href="#/home" aria-label="valopoint 홈"><span>valopoint</span></a>
      <span></span>
    {/if}
    <button class="info-btn" aria-label="정보" onclick={() => (info = true)}><span>i</span></button>
  </div>
</header>

<main>
  {#if app.error}
    <div class="card">데이터를 불러오지 못했습니다: {app.error}</div>
  {:else if !app.model}
    <p class="muted">불러오는 중…</p>
  {:else}
    {#if app.model.meta.source === 'synthetic'}
      <div class="banner">합성(가짜) 데이터로 만든 데모입니다. 실제 경기 데이터가 들어오면 교체됩니다.</div>
    {/if}
    {#key app.route.page + (app.route.arg ?? '')}
      <div class="page">
        {#if app.route.page === 'home'}<Home />
        {:else if app.route.page === 'teams'}<Teams />
        {:else if app.route.page === 'team'}<Team name={app.route.arg} />
        {:else if app.route.page === 'players'}<Players />
        {:else if app.route.page === 'player'}<Player id={app.route.arg} />
        {:else if app.route.page === 'bracket'}<Bracket />
        {:else if app.route.page === 'model'}<Model />
        {:else if app.route.page === 'game'}<Game arg={app.route.arg} />
        {:else}<Home />{/if}
      </div>
    {/key}
    <SourceCredit />
  {/if}
</main>

<nav class="tabbar">
  {#each tabs as t}
    <a href={`#/${t.id}`} class:on={active === t.id} aria-current={active === t.id ? 'page' : undefined}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin={t.id === 'home' ? 'miter' : 'round'}><path d={t.icon} /></svg>
      <span>{t.label}</span>
    </a>
  {/each}
</nav>

{#if info}
  <div class="sheet-bg" role="presentation" onclick={() => (info = false)}>
    <div class="sheet" role="dialog" aria-label="valopoint 정보" tabindex="-1" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.key === 'Escape' && (info = false)}>
      <div class="kicker">About</div>
      <p style="color:var(--text); font-weight:700; font-size:16px; margin:6px 0">valopoint</p>
      <p style="margin:0 0 10px">VCT 선수 기록으로 매긴 파워포인트(PP)와 국제전 승부·대진 예측을 보여 주는 비영리 팬 프로젝트입니다. 확률은 통계 모델의 예측일 뿐이며 결과를 보장하지 않습니다. 금전이 오가는 예측·베팅과 무관하며, 내 대진표에는 상품이나 보상이 없습니다.</p>
      <p style="margin:0 0 10px">경기·선수 데이터는 Liquipedia(CC BY-SA 3.0)에서 받아 가공했습니다. 이 사이트의 통계와 예측 값도 같은 CC BY-SA 3.0 조건을 따릅니다.</p>
      <p style="margin:0 0 10px">개인정보를 수집하지 않습니다. 계정·쿠키·분석 도구가 없고, 내 대진표의 픽은 이 기기의 브라우저에만 저장됩니다.</p>
      <SourceCredit />
      <button class="btn" style="width:100%; margin-top:14px" onclick={() => (info = false)}>닫기</button>
    </div>
  </div>
{/if}

<style>
  /* backwards fill: no transform left behind, so sheets inside a page can cover the bars */
  .page { animation: page-in var(--dur-slow) var(--ease-out) backwards; }
  @keyframes page-in { from { opacity: 0; transform: translateX(12px); } }
  @media (prefers-reduced-motion: reduce) {
    .page { animation: page-fade var(--dur-fast) linear backwards; }
    @keyframes page-fade { from { opacity: 0; } }
  }
</style>
