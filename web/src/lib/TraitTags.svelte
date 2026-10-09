<script>
  // personality tags: good/bad always carry ▲/▼; neutral ones carry their glyph
  import Glyph from './Glyph.svelte';
  let { tags = [], max = Infinity, small = false } = $props();
  const sym = { good: '▲', bad: '▼' };
</script>

{#if tags.length}
  <div class="tags" class:sm={small}>
    {#each tags.slice(0, max) as t}
      <span class="tag {t.tone}">{#if sym[t.tone]}<span aria-hidden="true">{sym[t.tone]}</span>{:else if t.icon}<Glyph name={t.icon} size={small ? 10 : 11} color="var(--text-dim)" />{/if}{t.label}</span>
    {/each}
  </div>
{/if}
