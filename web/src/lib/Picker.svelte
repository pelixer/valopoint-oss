<script>
  // Team picker bottom sheet (design v2 · 09). Picking the team already on the other side swaps them.
  import { app } from './store.svelte.js';
  import { fx } from './format.js';

  let { side = 'b', current, other, onpick, onclose } = $props();
  let q = $state('');
  let region = $state('ALL');
  let sel = $state(current);
  const norm = (x) => (x ?? '').toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '');
  const RC = { AMER: 'var(--r-amer)', EMEA: 'var(--r-emea)', PAC: 'var(--r-pac)', CN: 'var(--r-cn)' };
  let list = $derived(app.model.teams.map((t, i) => ({ ...t, rank: i + 1 }))
    .filter((t) => (region === 'ALL' || t.region === region) && norm(t.name).includes(norm(q.trim()))));
  let input = $state();
  $effect(() => { input?.focus({ preventScroll: true }); });
</script>

<div class="bg" role="presentation" onclick={onclose}></div>
<div class="sheet" role="dialog" aria-modal="true" aria-label={side === 'a' ? '왼쪽 팀 선택' : '상대 팀 선택'} tabindex="-1"
  onkeydown={(e) => e.key === 'Escape' && onclose()}>
  <div class="grab"><span></span></div>
  <div class="head">
    <div><span class="k">Select · {side === 'a' ? 'left' : 'right'} side</span><span class="t">{side === 'a' ? '왼쪽 팀 선택' : '상대 팀 선택'}</span></div>
    <button class="x" onclick={onclose} aria-label="닫기">×</button>
  </div>
  <div class="sbox">
    <input bind:this={input} type="search" placeholder="팀 검색" bind:value={q} autocomplete="off" aria-label="팀 검색" />
    {#if q}<button onclick={() => (q = '')} aria-label="검색어 지우기">×</button>{/if}
  </div>
  <div class="regions">
    {#each ['ALL', 'AMER', 'EMEA', 'PAC', 'CN'] as r}
      <button class:on={region === r} onclick={() => (region = r)}>{r === 'ALL' ? '전체' : r}</button>
    {/each}
  </div>
  <div class="list">
    {#each list as t (t.name)}
      <button class="row" class:sel={sel === t.name} class:other={t.name === other} onclick={() => (sel = t.name)}>
        <i style="background:{RC[t.region]}"></i>
        <div class="nm"><span class="disp">{t.name}</span><span class="sub">{t.region} · {t.rank}위{t.name === other ? ` · ${side === 'a' ? '오른쪽' : '왼쪽'} 팀` : ''}</span></div>
        <span class="num">{fx(t.pp, 0)}</span>
        <span class="ck">{sel === t.name ? '✓' : ''}</span>
      </button>
    {/each}
    {#if !list.length}<p class="note">일치하는 팀이 없습니다.</p>{/if}
  </div>
  <p class="note">팀명 부분 일치(악센트 무시). 반대편에 고른 팀을 고르면 양쪽을 맞바꿉니다.</p>
  <div class="foot"><button class="go" disabled={!sel} onclick={() => onpick(sel)}>{sel}{sel === other ? '와 자리 바꾸기' : '로 대결'}</button></div>
</div>

<style>
  .bg { position: fixed; inset: 0; z-index: 30; background: rgba(5, 7, 11, .72); animation: fade var(--dur-med) var(--ease-out); }
  @keyframes fade { from { opacity: 0; } }
  .sheet {
    position: fixed; left: 0; right: 0; bottom: 0; z-index: 31; max-width: 720px; margin: 0 auto;
    height: min(560px, 82vh); background: var(--bg-2); box-shadow: 0 -1px 0 var(--line-strong);
    clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%);
    display: flex; flex-direction: column; animation: up var(--dur-med) var(--ease-out);
  }
  @keyframes up { from { transform: translateY(100%); } }
  @media (prefers-reduced-motion: reduce) { .sheet, .bg { animation: fade var(--dur-fast) linear; } }
  .grab { display: flex; justify-content: center; padding-top: 8px; }
  .grab span { width: 36px; height: 3px; background: var(--line-strong); }
  .head { display: flex; align-items: center; justify-content: space-between; padding: 10px 6px 0 16px; }
  .head > div { display: flex; flex-direction: column; gap: 2px; }
  .k { font-family: var(--font-display); font-weight: 600; font-size: 11px; letter-spacing: var(--tracking-label); color: var(--text-dim); text-transform: uppercase; }
  .t { font-weight: 800; font-size: 19px; }
  .x { width: var(--hit); height: var(--hit); border: 0; background: none; color: var(--text-dim); font-size: 20px; cursor: pointer; }
  .sbox { margin: 10px 16px 0; height: var(--hit); display: flex; align-items: center; gap: 10px; padding: 0 4px 0 14px; background: var(--surface); box-shadow: inset 0 0 0 1px var(--line); }
  .sbox:focus-within { box-shadow: inset 0 0 0 1px var(--accent); }
  .sbox::before { content: ""; flex: none; width: 11px; height: 11px; border-radius: 50%; box-shadow: inset 0 0 0 1.5px var(--muted); }
  .sbox input { flex: 1; min-width: 0; height: var(--hit); background: none; border: 0; outline: none; color: var(--text); font-size: 16px; -webkit-appearance: none; appearance: none; }
  .sbox input::-webkit-search-cancel-button { display: none; }
  .sbox button { width: var(--hit); height: var(--hit); border: 0; background: none; color: var(--text-dim); font-size: 18px; }
  .regions { display: flex; gap: 4px; padding: 6px 16px 0; }
  .regions button { height: 30px; padding: 0 11px; border: 0; background: var(--surface); box-shadow: inset 0 0 0 1px var(--line); color: var(--text); font-weight: 600; font-size: 12px; cursor: pointer; }
  .regions button.on { background: var(--accent); color: var(--accent-ink); box-shadow: none; }
  .list { flex: 1; overflow-y: auto; padding: 8px 16px 0; overscroll-behavior: contain; }
  .row {
    width: 100%; display: grid; grid-template-columns: 4px minmax(0, 1fr) auto 24px; gap: 12px; align-items: center; height: 52px;
    border: 0; border-bottom: 1px solid var(--line); background: none; color: var(--text); padding: 0 10px 0 0; text-align: left; cursor: pointer;
  }
  .row i { height: 100%; }
  .row.sel { background: var(--surface-2); outline: 1px solid var(--accent); outline-offset: -1px; }
  .row.other:not(.sel) { opacity: .45; }
  .nm { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
  .nm .disp { font-size: 20px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .sub { font-size: 11px; color: var(--muted); }
  .row .num { font-weight: 700; font-size: 20px; }
  .ck { color: var(--accent); font-weight: 800; }
  .note { padding: 10px 16px 0; margin: 0; font-size: 11px; line-height: 1.5; color: var(--muted); }
  .foot { padding: 10px 16px calc(14px + env(safe-area-inset-bottom)); }
  .go {
    width: 100%; height: 48px; border: 0; background: var(--accent); color: var(--accent-ink); font-weight: 800; font-size: 15px; cursor: pointer;
    clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px);
  }
  .go:disabled { opacity: .4; }
</style>
