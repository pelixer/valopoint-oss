<script>
  // Option list bottom sheet in the Picker style (replaces native <select> popups, which the
  // browser draws light on some systems). Tapping a row picks it and closes the sheet.
  // options: [{value, label, sub?, group?}] — rows with the same `group` are listed under one label.
  let { kicker = 'Select', title, options, value, onpick, onclose } = $props();
  let groups = $derived.by(() => {
    const out = [];
    for (const o of options) {
      const g = o.group ?? '';
      let cur = out[out.length - 1];
      if (!cur || cur.name !== g) out.push((cur = { name: g, items: [] }));
      cur.items.push(o);
    }
    return out;
  });
  let box = $state();
  $effect(() => { box?.querySelector('.row.sel')?.scrollIntoView({ block: 'center' }); box?.focus({ preventScroll: true }); });
</script>

<div class="bg" role="presentation" onclick={onclose}></div>
<div class="sheet" role="dialog" aria-modal="true" aria-label={title} tabindex="-1" bind:this={box}
  onkeydown={(e) => e.key === 'Escape' && onclose()}>
  <div class="grab"><span></span></div>
  <div class="head">
    <div><span class="k">{kicker}</span><span class="t">{title}</span></div>
    <button class="x" onclick={onclose} aria-label="닫기">×</button>
  </div>
  <div class="list">
    {#each groups as g}
      {#if g.name}<div class="gl">{g.name}</div>{/if}
      {#each g.items as o (o.value)}
        <button class="row" class:sel={o.value === value} aria-pressed={o.value === value} onclick={() => { onpick(o.value); onclose(); }}>
          <span class="nm">{o.label}</span>
          {#if o.sub}<span class="sub">{o.sub}</span>{/if}
          <span class="ck">{o.value === value ? '✓' : ''}</span>
        </button>
      {/each}
    {/each}
  </div>
</div>

<style>
  .bg { position: fixed; inset: 0; z-index: 30; background: rgba(5, 7, 11, .72); animation: fade var(--dur-med) var(--ease-out); }
  @keyframes fade { from { opacity: 0; } }
  .sheet {
    position: fixed; left: 0; right: 0; bottom: 0; z-index: 31; max-width: 720px; margin: 0 auto;
    max-height: min(560px, 82vh); background: var(--bg-2); box-shadow: 0 -1px 0 var(--line-strong); outline: none;
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
  .t { font-weight: 800; font-size: 19px; color: var(--text); }
  .x { width: var(--hit); height: var(--hit); border: 0; background: none; color: var(--text-dim); font-size: 20px; cursor: pointer; }
  .list { flex: 1; overflow-y: auto; padding: 6px 16px calc(14px + env(safe-area-inset-bottom)); overscroll-behavior: contain; }
  .gl { padding: 14px 0 4px; font-family: var(--font-display); font-weight: 600; font-size: 11px; letter-spacing: var(--tracking-label); color: var(--muted); text-transform: uppercase; }
  .row {
    width: 100%; display: grid; grid-template-columns: minmax(0, 1fr) auto 24px; gap: 12px; align-items: center; height: 48px;
    border: 0; border-bottom: 1px solid var(--line); background: none; color: var(--text); padding: 0 10px; text-align: left; cursor: pointer;
  }
  .row.sel { background: var(--surface-2); box-shadow: inset 3px 0 0 var(--accent); }
  .nm { font-size: 15px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .row.sel .nm { font-weight: 800; }
  .sub { font-size: 12px; color: var(--muted); }
  .ck { color: var(--accent); font-weight: 800; text-align: right; }
</style>
