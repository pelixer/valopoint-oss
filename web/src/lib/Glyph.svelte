<script>
  // Drawn glyphs (design v2) replacing emoji: 14px grid, own geometry, no official icons.
  let { name, size = 14, color = null } = $props();
  const G = {
    mvp: ['var(--accent)', 'fill', 'M7 1l1.5 4.5L13 7 8.5 8.5 7 13 5.5 8.5 1 7l4.5-1.5z'],
    rise: ['var(--good)', 'stroke', 'M3 7.5l4-4 4 4M3 11.5l4-4 4 4'],
    steady: ['var(--text)', 'stroke', 'M1.5 7h11M1.5 3.5v7M12.5 3.5v7'],
    intl: ['var(--text)', 'stroke', 'M3.5 1.5h7v4L7 9 3.5 5.5zM7 9v3M4 12.5h6'],
    league: ['var(--text)', 'stroke', 'M1 12.5h12M5 12.5v-7h4v7M1 12.5v-4h4M9 12.5v-5h4v5'],
    power: ['var(--warn)', 'fill', 'M8.5 1L3 8h3.5L5.5 13 11 6H7.5z'],
    stage: ['var(--text)', 'stroke', 'M1 11.5Q7 2.5 13 11.5M4 11.5Q7 7 10 11.5M1 12.5h12'],
    agent: ['var(--text)', 'fill', 'M1.5 11.5L1 3.5l3.5 3L7 2l2.5 4.5 3.5-3-.5 8z'],
    map: ['var(--text)', 'stroke', 'M1.5 3L5 1.5l4 1.5 3.5-1.5V11L9 12.5 5 11l-3.5 1.5zM5 1.5V11M9 3v9.5'],
    globe: ['var(--text-dim)', 'stroke', 'M12.5 7a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0zM1.5 7h11M7 1.5c-2.6 3-2.6 8 0 11M7 1.5c2.6 3 2.6 8 0 11'],
    pct: ['var(--text)', 'stroke', 'M2.5 12.5V9M7 12.5V6M11.5 12.5V2.5'],
    swing: ['var(--bad)', 'stroke', 'M1 9l3-5 3 7 3-6 3 3'],
  };
  let g = $derived(G[name]);
  let c = $derived(color ?? g?.[0]);
</script>

{#if g}
  <svg viewBox="0 0 14 14" width={size} height={size} aria-hidden="true" style="flex:none"
    fill={g[1] === 'fill' ? c : 'none'} stroke={g[1] === 'stroke' ? c : 'none'} stroke-width="1.6"><path d={g[2]} /></svg>
{/if}
