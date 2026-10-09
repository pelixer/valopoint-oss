<script>
  // N-gon radar ("attribute graph"): one vertex per axis, so 6 axes -> hexagon,
  // 10 axes -> decagon. Values are 0-100 percentiles.
  let { axes = [], series = [], size = 300 } = $props();
  // series: [{ values: {key: 0-100}, color, label, dashed? }]

  const pad = 54;
  let n = $derived(axes.length);
  let r = $derived(size / 2 - pad);
  let c = $derived(size / 2);
  const angle = (i) => -Math.PI / 2 + (2 * Math.PI * i) / n;
  const pt = (i, v) => [c + (r * v * Math.cos(angle(i))) / 100, c + (r * v * Math.sin(angle(i))) / 100];
  const val = (s, a) => Math.max(0, Math.min(100, s?.values?.[a.key] ?? 0));
  const poly = (s) => axes.map((a, i) => pt(i, val(s, a)).join(',')).join(' ');
  const ring = (v) => axes.map((_, i) => pt(i, v).join(',')).join(' ');
  function anchor(i) {
    const x = Math.cos(angle(i));
    return x > 0.25 ? 'start' : x < -0.25 ? 'end' : 'middle';
  }
  // value labels only when one series is the subject (the others are references)
  let main = $derived(series.filter((s) => !s.dashed));
</script>

{#if n >= 3}
  <svg viewBox="0 0 {size} {size}" width="100%" style="max-width:{size}px; display:block; margin:0 auto; overflow:visible" role="img"
    aria-label="속성 그래프: {axes.map((a) => `${a.label} ${Math.round(series[0]?.values?.[a.key] ?? 0)}`).join(', ')}">
    {#each [25, 75, 100] as v}
      <polygon points={ring(v)} fill="none" stroke="var(--line)" stroke-width="1" />
    {/each}
    {#each axes as _, i}
      {@const [x, y] = pt(i, 100)}
      <line x1={c} y1={c} x2={x} y2={y} stroke="var(--line)" stroke-width="1" />
    {/each}
    {#each series as s}
      <polygon class="shape" points={poly(s)} fill={s.dashed ? 'none' : s.color} fill-opacity={s.dashed ? 0 : 0.18}
        stroke={s.color} stroke-width={s.dashed ? 1.5 : 2} stroke-dasharray={s.dashed ? '4 3' : ''} stroke-linejoin="miter" />
    {/each}
    {#each main as s}
      {#each axes as a, i}
        {@const [x, y] = pt(i, val(s, a))}
        <rect x={x - 3} y={y - 3} width="6" height="6" fill={s.color} />
      {/each}
    {/each}
    {#each axes as a, i}
      {@const [x, y] = pt(i, 122)}
      <text {x} y={y - 2} text-anchor={anchor(i)} font-size="12" font-weight="600" fill="var(--text)" font-family="var(--font-body)">{a.label}</text>
      {#if main.length === 1}
        {@const v = Math.round(val(main[0], a))}
        <text {x} y={y + 15} text-anchor={anchor(i)} font-size="17" font-weight="700" fill={v >= 50 ? 'var(--text)' : 'var(--text-dim)'} font-family="var(--font-num)">{v}</text>
      {/if}
    {/each}
  </svg>
  {#if series.length > 1}
    <div class="legend">
      {#each series as s}
        <span><i style={s.dashed ? `border-top:2px dashed ${s.color}` : `height:2px; background:${s.color}`}></i>{s.label}</span>
      {/each}
    </div>
  {/if}
{/if}

<style>
  .shape { transition: all var(--dur-slow) var(--ease-out); }
  .legend { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; font-size: 12px; color: var(--text-dim); margin-top: 2px; }
  .legend span { display: inline-flex; align-items: center; gap: 6px; }
  .legend i { display: inline-block; width: 14px; }
</style>
