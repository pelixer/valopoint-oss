<script>
  // Data credit next to the data on every page (Liquipedia CC BY-SA requires attribution
  // close to the data, with backlinks) and Riot's fan-project notice.
  import { app } from './store.svelte.js';
  let { href = null, label = null } = $props();
  let info = $derived(app.model?.meta?.source_info ?? { name: app.model?.meta?.source });
</script>

<footer class="credit">
  {#if info?.name && info.name !== 'synthetic'}
    <span>
      {#if info.url}데이터: <a href={href ?? info.url} target="_blank" rel="noopener">{label ?? info.name} ↗</a>{#if info.license} · <a href={info.license_url ?? info.url} target="_blank" rel="noopener license">{info.license}</a>{/if} · 가공·재계산된 값
      {:else}데이터: {info.name}{/if}
    </span>
  {/if}
  <span>valopoint was created under Riot Games' "Legal Jibber Jabber" policy using assets owned by Riot Games. Riot Games does not endorse or sponsor this project.</span>
</footer>
