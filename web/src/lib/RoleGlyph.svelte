<script>
  // role glyphs (design v1): duelist ◆, initiator ▲, controller ●, sentinel ■
  let { role, size = 11, color = 'currentColor' } = $props();
  const shape = {
    duelist: 'transform:rotate(45deg) scale(.8)',
    initiator: 'clip-path:polygon(50% 0,100% 100%,0 100%)',
    controller: 'border-radius:50%',
    sentinel: '',
  };
</script>

<span aria-hidden="true" style="display:inline-block; flex:none; width:{size}px; height:{size}px; background:{color}; {shape[role] ?? 'opacity:.5'}"></span>
