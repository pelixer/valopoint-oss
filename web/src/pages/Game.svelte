<script>
  // Match detail (design v2 · 10/11): series odds, veto, per-set predictions and context.
  import { app, persisted } from '../lib/store.svelte.js';
  import { scorelines, seriesOrdered, vetoMaps } from '../lib/engine.js';
  import { groupOf, resolveTeams } from '../lib/bracket.js';
  import { cap, fx, kst, pct } from '../lib/format.js';
  import { lockedFor } from '../lib/ledger.js';

  let { arg } = $props();
  let [bid, mid] = $derived((arg ?? '').split('/'));
  let br = $derived(app.brackets.find((b) => b.id === bid));
  let m = $derived(br?.matches.find((x) => x.id === mid));
  const locks = persisted('bracket-locks', {}).get();
  let teams = $derived(br && m ? resolveTeams(br, { ...(br.results ?? {}), ...(locks[br.id] ?? {}) })[m.id] : {});
  let A = $derived(teams.a), B = $derived(teams.b);
  let TA = $derived(app.engine.teams[A]), TB = $derived(app.engine.teams[B]);
  let bo = $derived(m?.best_of ?? 3);
  let winner = $derived(br?.results?.[m?.id] ?? null);
  let played = $derived(!!winner);

  // map order: actual veto if published, otherwise the model's predicted veto
  let pmap = $derived(A && B ? Object.fromEntries(app.model.maps.map((mp) => [mp, app.engine.mapProb(A, B, mp)])) : {});
  let actualOrder = $derived(m?.veto?.order?.length ? m.veto.order : null);
  let sv = $derived(A && B ? app.engine.series(A, B, bo) : null);
  // most likely veto sequence from the teams' recent ban/pick tendencies (fallback: stat-greedy)
  let order = $derived(actualOrder ?? sv?.seqs?.[0]?.[0] ?? (A && B ? vetoMaps(pmap, bo, true) : []));
  let ps = $derived(order.map((mp) => app.engine.mapProb(A, B, mp)));
  let pSeries = $derived(ps.length ? (actualOrder ? seriesOrdered(ps) : sv.p) : null);
  let presence = $derived(sv?.presence ? Object.entries(sv.presence).sort((x, y) => y[1] - x[1]) : []);

  // who picked each map (veto steps carry team tags)
  let pickOf = $derived(Object.fromEntries((m?.veto?.steps ?? []).filter((s) => s[1] !== 'ban').map((s) => [s[2], s[1] === 'remains' ? '결정' : `${s[0]} 픽`])));
  // pre-match predictions from the accuracy check (played matches only)
  let preMatch = $derived((app.model.event_eval?.matches ?? []).find((x) => String(x.match_id) === String(m?.match_id ?? m?.vlr_id)));
  let flip = $derived(preMatch ? preMatch.team_a !== A : false);
  let pre = $derived(preMatch ? Object.fromEntries(preMatch.maps.map((x) => [x.map, { p: flip ? 1 - x.p : x.p, win: flip ? 1 - x.win : x.win }])) : null);
  // final score from A's side, e.g. "2-0"
  let score = $derived(preMatch?.score ? (flip ? preMatch.score.split('-').reverse().join('-') : preMatch.score) : null);
  // prediction locked in the append-only ledger before the match started
  let ledgerEntry = $derived(br && m ? lockedFor(app.ledger, br.id, m) : null);
  let ledgerP = $derived(ledgerEntry && A && B ? (ledgerEntry.team_a === A ? ledgerEntry.p : ledgerEntry.team_b === A ? 1 - ledgerEntry.p : null) : null);
  // for finished matches show what was predicted BEFORE the match (no hindsight)
  let shownSeries = $derived(preMatch ? (preMatch.team_a === A ? preMatch.p : 1 - preMatch.p) : pSeries);
  let setPs = $derived(order.map((mp, i) => pre?.[mp]?.p ?? ps[i]));
  // set-score odds: over all veto sequences (veto model) unless the actual maps are known
  let lines = $derived.by(() => {
    if (!setPs.length) return [];
    const d = !actualOrder && !played && sv?.lines ? sv.lines : scorelines(setPs);
    return Object.entries(d).sort((x, y) => (+y[0][0] - +y[0][2]) - (+x[0][0] - +x[0][2]));
  });

  const roster = (T) => (T?.roster ?? []).map((id) => ({ id, ...app.model.players[id] })).filter((p) => p.name);
  function playerOnMap(p, mp) {
    const mix = p.mix?.[mp] ?? p.mix?.['*'] ?? {};
    const agent = Object.entries(mix).sort((x, y) => y[1] - x[1])[0]?.[0];
    return { pp: p.maps?.[mp]?.pp ?? p.pp, rounds: p.maps?.[mp]?.rounds ?? 0, agent };
  }
  const rec = (T, mp) => T?.map_record?.[mp];
  let h2h = $derived((TA?.recent ?? []).filter((r) => r[1] === B).slice(-8).reverse());
  const form = (T) => (T?.recent ?? []).slice(-10);
  let axes = $derived(app.model.style_axes ?? []);
  const teamStyle = (T) => {
    const ps = roster(T).filter((p) => p.style);
    return ps.length ? Object.fromEntries(axes.map((a) => [a.key, ps.reduce((s, p) => s + p.style[a.key], 0) / ps.length])) : null;
  };
  let sa = $derived(teamStyle(TA)), sb = $derived(teamStyle(TB));
  // short team label for table headers: "100 Thieves" → 100T, "Team Liquid" → TL, "FUT Esports" → FUT
  function abbr(n) {
    if (!n || n.length <= 5) return n ?? '';
    const w = n.split(/\s+/);
    if (w.length === 1) return n.slice(0, 5);
    if (/^\d+$/.test(w[0])) return w[0] + w[1][0];
    if (/^[A-Z0-9]{2,4}$/.test(w[0])) return w[0];
    return w.map((x) => x[0]).join('').slice(0, 4).toUpperCase();
  }
  const when = (iso) => iso ? new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', month: 'numeric', day: 'numeric', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(iso)) + ' KST' : '일정 미정';
  // no live scores: "live" = started and still inside a normal series length
  let since = $derived(m?.time ? Date.now() - Date.parse(m.time) : -1);
  let live = $derived(!played && since >= 0 && since < (bo === 5 ? 5.5 : bo === 1 ? 1.5 : 3.5) * 3600e3);
  let waiting = $derived(!played && since >= 0 && !live);
</script>

{#if !m}
  <p class="note">경기를 찾을 수 없습니다.</p>
{:else}
  {@const g = groupOf(m)}
  <div class="hdr">
    <span class="gchip" class:final={g.key === 'GF'} style="--gc:{g.color}">{g.label}</span>
    <span class="dim small">{m.round} · Bo{bo}</span>
    <span class="num when">{when(m.time)}</span>
    <span class="st" class:done={played} class:live>{played ? '종료' : live ? '진행 중' : waiting ? '결과 대기' : '경기 전'}</span>
  </div>

  {#if !(A && B)}
    <section class="bug tbd"><span class="disp">대진 미정</span><span class="note">앞 경기 결과가 나와야 팀이 정해집니다.</span></section>
  {:else}
    {#if played}
      <section class="bug" class:noscore={!score}>
        {#each [[A, 'a'], [B, 'b']] as [t, s]}
          <div class="side {s}" class:win={winner === t} style="order:{s === 'a' ? 0 : 2}">
            <span class="res">{winner === t ? '✓ 승' : '패'}</span>
            <span class="disp tn">{t}</span>
          </div>
        {/each}
        {#if score}<div class="score num" style="order:1">{score.split('-')[0]}<em>:</em>{score.split('-')[1]}</div>{/if}
      </section>
    {:else}
      <section class="bug">
        <div class="side a"><span class="badge sm {TA?.region}">{TA?.region}</span><span class="disp tn">{A}</span></div>
        <div class="vs disp">VS</div>
        <div class="side b"><span class="badge sm {TB?.region}">{TB?.region}</span><span class="disp tn">{B}</span></div>
      </section>
    {/if}
    <div class="odds">
      <div class="or"><span class="num big red">{pct(shownSeries)}</span><span class="lbl">{played ? (preMatch ? '경기 전 예측' : '현재 모델') : 'Series'}</span><span class="num big">{pct(1 - shownSeries)}</span></div>
      <div class="vbar" style="height:8px; margin-top:8px; opacity:{played ? 0.7 : 1}"><span style="width:{(shownSeries * 100).toFixed(1)}%"></span><span></span></div>
      <div class="cap">{played ? '시리즈' : '시리즈 승률'} · 맵 순서: {actualOrder ? '실제 밴픽' : sv?.basis === 'veto_model' ? '예상 밴픽(팀 밴픽 성향)' : '예상 밴픽(모델)'}</div>
      {#if played && ledgerP != null}<div class="cap">기록된 예측({kst(ledgerEntry.recorded_at)}): {A} {pct(ledgerP)}</div>{/if}
      {#if lines.length}
        <div class="dist">
          {#each lines as [s, q]}
            {@const aw = +s[0] > +s[2]}
            <div class:aw class:real={score === s}><span class="num s">{s}</span><span class="num q">{pct(q)}</span></div>
          {/each}
        </div>
        <div class="cap row"><span>{A} 기준 세트 스코어{played ? ' · 경기 전 예측' : ''}</span><span>레드 = {abbr(A)} 승{score ? ' · 채움 = 실제' : ''}</span></div>
      {/if}
    </div>

    {#if !actualOrder && presence.length}
      <div class="sec"><div><span class="k">Veto · projected</span><span class="t">예상 밴픽</span></div></div>
      <div class="card">
        {#each sv.seqs.slice(0, 3) as [seq, q], k}
          <div class="ord" class:first={k === 0}><span class="num r">{k + 1}</span><span class="disp">{seq.map(cap).join(' → ')}</span><span class="num p">{pct(q, 1)}</span></div>
        {/each}
        <div class="small muted" style="margin:14px 0 4px">맵 등장 확률</div>
        {#each presence as [mp, q], i}
          <div class="app"><span class="disp">{cap(mp)}</span><div class="ab"><i style="width:{(q * 100).toFixed(0)}%; background:{i < 3 ? 'var(--text)' : 'var(--muted)'}"></i></div><span class="num">{pct(q)}</span></div>
        {/each}
        <p class="note">두 팀의 최근 밴/픽 기록({(app.model.veto_model?.events ?? []).map((e) => e.replace(/^(VCT \d{4}: |Valorant )/, '')).join(', ')})으로 밴픽 순서를 모두 따져 계산(선밴 팀은 반반). 세트 순서는 가장 가능성 높은 경우이고, 시리즈 승률은 모든 경우를 확률 가중 평균했습니다.</p>
      </div>
    {/if}

    <div class="sec"><div><span class="k">By set{played ? ' · result' : ''}</span><span class="t">{played ? '세트별 예측과 결과' : '세트별 예측'}</span></div></div>
    {#each order as mp, i}
      {@const p = setPs[i]}
      {@const ra = rec(TA, mp)}
      {@const rb = rec(TB, mp)}
      {@const ppa = 500 + 1000 * (TA?.theta?.[mp] ?? 0)}
      {@const ppb = 500 + 1000 * (TB?.theta?.[mp] ?? 0)}
      {@const res = pre?.[mp]}
      {@const unplayed = played && pre && !res}
      <div class="set" class:unplayed>
        <div class="sh">
          <span class="sn">Set {i + 1}</span><span class="disp sm">{cap(mp)}</span>
          <span class="how">{pickOf[mp] ?? (actualOrder ? '' : i === order.length - 1 ? '결정(예상)' : '픽(예상)')}</span>
          {#if res}
            {@const ok = (res.p > 0.5) === (res.win === 1)}
            <span class="rt" class:ok>{ok ? '○' : '×'} {res.win === 1 ? A : B} 승</span>
          {:else if unplayed}<span class="rt off">미진행</span>{/if}
        </div>
        <div class="sp">
          {#if played}<span class="small muted">경기 전 예측</span>{/if}
          <div class="pr"><span class="num red">{pct(p)}</span><span class="num">{pct(1 - p)}</span></div>
          <div class="vbar" style="height:6px; margin-top:4px"><span style="width:{(p * 100).toFixed(1)}%"></span><span></span></div>
        </div>
        {#if unplayed}
          <p class="note" style="padding:0 12px 10px; margin:6px 0 0">{score ?? ''}{score ? '으로 ' : ''}끝나 열리지 않은 세트. 예측만 남김.</p>
        {:else}
          <div class="st3">
            <span></span><span class="h">{abbr(A)}</span><span class="h">{abbr(B)}</span>
            <span class="k">맵 팀 PP</span><span class="num" class:hi={ppa > ppb} class:red={ppa > ppb}>{fx(ppa, 0)}</span><span class="num" class:hi={ppb > ppa}>{fx(ppb, 0)}</span>
            <span class="k">최근 1년 전적</span><span class="num">{ra ? `${ra[1]}승 ${ra[0] - ra[1]}패` : '–'}</span><span class="num">{rb ? `${rb[1]}승 ${rb[0] - rb[1]}패` : '–'}</span>
            <span class="k">라운드 승률</span><span class="num">{ra ? pct(ra[2] / ra[3]) : '–'}</span><span class="num">{rb ? pct(rb[2] / rb[3]) : '–'}</span>
          </div>
          <details>
            <summary>선수별 {cap(mp)} PP · 예상 요원</summary>
            <div class="pl">
              {#each [TA, TB] as T}
                <div>
                  {#each roster(T) as pl}
                    {@const v = playerOnMap(pl, mp)}
                    <a href={`#/player/${pl.id}`}><span class="nm">{pl.name} <em>{cap(v.agent ?? '')}</em></span><span class="num">{fx(v.pp)}</span></a>
                  {/each}
                </div>
              {/each}
            </div>
          </details>
        {/if}
      </div>
    {/each}
    <p class="note">맵 승률 = 출전 로스터 5명의 해당 맵 PP(예상 요원 기준) 합 차이 + 지역 보정. 팀의 맵 전적·최근 폼·플레이 스타일은 검증 결과 예측을 개선하지 않아 참고 정보로만 표시합니다.</p>

    {#if sa && sb}
      <div class="sec"><div><span class="k">Attributes · roster avg</span><span class="t">속성 비교</span></div></div>
      <div class="card attrs">
        <div class="arow head"><span class="disp">{abbr(A)}</span><span></span><span></span><span></span><span class="disp r">{abbr(B)}</span></div>
        {#each axes as ax}
          {@const va = Math.round(sa[ax.key])}
          {@const vb = Math.round(sb[ax.key])}
          <div class="arow">
            <span class="num" class:lead={va > vb}>{va}</span>
            <div class="ab l"><i style="width:{va}%"></i><b></b></div>
            <span class="ak">{ax.label}</span>
            <div class="ab r"><i style="width:{vb}%"></i><b></b></div>
            <span class="num r" class:lead={vb > va}>{vb}</span>
          </div>
        {/each}
        <p class="note" style="font-size:11px">로스터 5명의 역할 내 백분위 평균. 눈금 = 50(역할 평균).</p>
      </div>
    {/if}

    <div class="sec"><div><span class="k">Head to head · 1y</span><span class="t">상대 전적</span></div></div>
    {#if h2h.length}
      <div class="card">
        {#each h2h as r}
          <div class="h2"><span class="num muted">{r[0]}</span><span class="disp">{cap(r[2])}</span><span class="num" class:w={r[3] > r[4]} class:l={r[3] < r[4]}>{r[3] > r[4] ? '○' : '×'} {abbr(A)} {r[3]}:{r[4]}</span></div>
        {/each}
      </div>
    {:else}
      <div class="empty"><span class="num">0</span><span>최근 1년 맞대결 기록이 없습니다.</span></div>
    {/if}

    <div class="sec"><div><span class="k">Last 10 maps</span><span class="t">최근 10맵 흐름</span></div></div>
    <div class="card fs">
      {#each [[A, TA], [B, TB]] as [n, T]}
        {@const f = form(T)}
        {@const w = f.filter((r) => r[3] > r[4]).length}
        <div class="frow">
          <span class="disp">{n}</span>
          <div class="cells">{#each f as r}<span class="num" class:w={r[3] > r[4]} title="{r[0]} vs {r[1]} {r[2]} {r[3]}:{r[4]}">{r[3] > r[4] ? 'W' : 'L'}</span>{/each}</div>
          <span class="num rc">{w}-{f.length - w}</span>
        </div>
      {/each}
      <span class="note" style="font-size:11px">왼쪽이 오래된 맵. W = 맵 승(채움), L = 맵 패(테두리).</span>
    </div>
  {/if}
{/if}

<style>
  a { color: inherit; text-decoration: none; }
  .note { font-size: 12px; line-height: 1.55; color: var(--muted); margin: 8px 0 0; }
  .card .note { font-size: 11px; }
  .red { color: var(--accent); }
  .hdr { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .when { font-family: var(--font-display); font-weight: 600; font-size: 15px; }
  .st { margin-left: auto; font-size: 11px; font-weight: 600; color: var(--muted); height: 20px; display: flex; align-items: center; padding: 0 7px; }
  .st.done { color: var(--text-dim); box-shadow: inset 0 0 0 1px var(--line-strong); }
  .st.live { background: var(--accent); color: var(--accent-ink); font-weight: 800; }

  .bug {
    position: relative; margin-top: 10px; display: grid; grid-template-columns: minmax(0, 1fr) 64px minmax(0, 1fr);
    background: var(--surface); clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px);
    animation: wipe var(--dur-slow) var(--ease-out) backwards;
  }
  .bug.noscore { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  .bug.tbd { display: flex; flex-direction: column; padding: 16px; }
  .bug.tbd .disp { font-size: 28px; }
  .side { padding: 14px 12px; display: flex; flex-direction: column; gap: 4px; min-width: 0; }
  .side.a { box-shadow: inset 4px 0 0 var(--side-a); }
  .side.b { box-shadow: inset -4px 0 0 var(--side-b); align-items: flex-end; text-align: right; }
  .side.a .badge { align-self: flex-start; }
  .tn { font-weight: 800; font-size: 28px; line-height: .95; overflow-wrap: anywhere; }
  .side .res { font-size: 12px; font-weight: 700; color: var(--muted); }
  .side.win { background: var(--text); color: var(--accent-ink); }
  .side.win .res { color: var(--accent-ink); }
  .side:not(.win) .tn { color: inherit; }
  .bug:has(.win) .side:not(.win) { color: var(--muted); }
  .vs, .score { display: flex; align-items: center; justify-content: center; background: var(--bg-2); }
  .vs { font-weight: 800; font-size: 22px; color: var(--muted); }
  .score { font-weight: 800; font-size: 40px; gap: 4px; padding: 0 8px; }
  .score em { font-style: normal; font-size: 24px; color: var(--muted); }

  .odds { background: var(--surface); margin-top: 2px; padding: 12px; }
  .or { display: flex; justify-content: space-between; align-items: baseline; }
  .big { font-weight: 800; font-size: 40px; line-height: .9; }
  .lbl { font-family: var(--font-display); font-weight: 600; font-size: 11px; letter-spacing: var(--tracking-label); color: var(--muted); text-transform: uppercase; }
  .cap { font-size: 11px; color: var(--muted); margin-top: 6px; }
  .cap.row { display: flex; justify-content: space-between; gap: 8px; }
  .dist { display: grid; grid-auto-columns: minmax(0, 1fr); grid-auto-flow: column; gap: 2px; margin-top: 10px; }
  .dist > div { padding: 8px 6px; background: var(--bg-2); display: flex; flex-direction: column; align-items: center; gap: 2px; }
  .dist .s { font-weight: 800; font-size: 20px; line-height: 1; }
  .dist .q { font-weight: 700; font-size: 15px; color: var(--text-dim); }
  .dist .aw { background: rgba(242, 67, 79, .1); }
  .dist .aw .s { color: var(--accent); }
  .dist .real { background: var(--text); }
  .dist .real .s, .dist .real .q { color: var(--accent-ink); }

  .ord { display: grid; grid-template-columns: 22px minmax(0, 1fr) 44px; gap: 8px; align-items: center; height: 36px; padding: 0 8px; background: var(--bg-2); margin-bottom: 6px; }
  .ord.first { background: var(--surface-2); }
  .ord .r { font-weight: 800; font-size: 16px; color: var(--muted); }
  .ord.first .r { color: var(--accent); }
  .ord .disp { font-size: 18px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .ord .p { font-weight: 700; font-size: 16px; text-align: right; color: var(--text-dim); }
  .app { display: grid; grid-template-columns: 64px minmax(0, 1fr) 40px; gap: 10px; align-items: center; height: 28px; }
  .app .disp { font-size: 17px; }
  .app .num { font-weight: 700; font-size: 16px; text-align: right; }
  .ab { height: 4px; background: var(--bg); }
  .ab i { display: block; height: 4px; }

  .set { background: var(--surface); clip-path: var(--clip-chamfer); margin-bottom: 8px; }
  .set.unplayed { opacity: .6; }
  .sh { display: flex; align-items: center; gap: 10px; padding: 10px 12px 0; }
  .sn { font-family: var(--font-display); font-weight: 700; font-size: 13px; letter-spacing: .1em; color: var(--muted); text-transform: uppercase; }
  .sh .sm { font-weight: 800; font-size: 26px; line-height: 1; }
  .how { font-size: 12px; color: var(--muted); }
  .rt { margin-left: auto; font-size: 12px; font-weight: 700; padding: 3px 6px; color: var(--bad); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--bad) 40%, transparent); white-space: nowrap; }
  .rt.ok { color: var(--good); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--good) 40%, transparent); }
  .rt.off { color: var(--muted); box-shadow: inset 0 0 0 1px var(--line-strong); font-weight: 600; }
  .sp { padding: 8px 12px 0; }
  .pr { display: flex; justify-content: space-between; font-weight: 800; font-size: 20px; }
  .pr .num { font-weight: 800; }
  .st3 { display: grid; grid-template-columns: minmax(0, 1fr) 72px 72px; padding: 8px 12px 0; font-size: 13px; }
  .st3 > span { padding: 6px 0; border-top: 1px solid var(--line); text-align: right; }
  .st3 > span:nth-child(-n + 3) { border-top: 0; padding: 4px 0; }
  .st3 .h { font-family: var(--font-display); font-weight: 700; font-size: 14px; color: var(--text-dim); }
  .st3 .k { text-align: left; color: var(--text-dim); }
  .st3 .num { font-weight: 700; font-size: 16px; color: var(--text-dim); }
  .st3 .num.hi { color: var(--text); }
  .st3 .num.hi.red { color: var(--accent); }
  details { border-top: 1px solid var(--line); margin-top: 4px; }
  summary { display: flex; align-items: center; gap: 8px; height: var(--hit); padding: 0 12px; font-size: 13px; color: var(--text-dim); cursor: pointer; list-style: none; }
  summary::-webkit-details-marker { display: none; }
  summary::before { content: "▶"; font-size: 10px; transition: transform var(--dur-fast) var(--ease-out); }
  details[open] summary::before { transform: rotate(90deg); }
  .pl { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 0 12px 10px; font-size: 13px; }
  .pl > div { min-width: 0; }
  .pl a { display: flex; justify-content: space-between; gap: 6px; padding: 3px 0; }
  .pl .nm { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pl em { font-style: normal; color: var(--muted); }

  .attrs { padding: 10px 12px; }
  .arow { display: grid; grid-template-columns: 32px minmax(0, 1fr) 56px minmax(0, 1fr) 32px; gap: 6px; align-items: center; height: 30px; }
  .arow.head { height: auto; padding-bottom: 4px; font-size: 13px; color: var(--text-dim); }
  .arow .num { font-weight: 700; font-size: 17px; color: var(--text-dim); }
  .arow .num.lead { color: var(--text); }
  .arow .r { text-align: right; }
  .arow .ak { text-align: center; font-size: 12px; font-weight: 600; }
  .arow .ab { position: relative; height: 6px; background: var(--bg); }
  .arow .ab i { position: absolute; top: 0; bottom: 0; height: auto; transition: width var(--dur-slow) var(--ease-out); }
  .arow .ab.l i { right: 0; background: var(--side-a); }
  .arow .ab.r i { left: 0; background: var(--side-b); }
  .arow .ab b { position: absolute; top: -3px; bottom: -3px; width: 1px; background: var(--muted); }
  .arow .ab.l b { right: 50%; }
  .arow .ab.r b { left: 50%; }

  .h2 { display: grid; grid-template-columns: 86px minmax(0, 1fr) auto; gap: 8px; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--line); font-size: 15px; }
  .h2:last-child { border-bottom: 0; }
  .h2 .w { color: var(--good); font-weight: 700; }
  .h2 .l { color: var(--bad); font-weight: 700; }
  .empty { display: flex; align-items: center; gap: 12px; padding: 14px 12px; background: var(--bg-2); box-shadow: inset 0 0 0 1px var(--line); outline: 1px dashed var(--line-strong); outline-offset: -5px; font-size: 13px; color: var(--text-dim); }
  .empty .num { width: 28px; height: 28px; flex: none; display: grid; place-items: center; font-weight: 800; font-size: 16px; color: var(--muted); box-shadow: inset 0 0 0 1px var(--line-strong); }

  .fs { display: flex; flex-direction: column; gap: 8px; }
  .frow { display: grid; grid-template-columns: 80px minmax(0, 1fr) 40px; gap: 6px; align-items: center; }
  .frow .disp { font-size: 16px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .cells { display: grid; grid-template-columns: repeat(10, minmax(0, 1fr)); gap: 3px; }
  .cells span { height: 24px; display: grid; place-items: center; font-weight: 800; font-size: 13px; color: var(--bad); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--bad) 50%, transparent); }
  .cells span.w { background: var(--good); color: var(--bg); box-shadow: none; }
  .rc { font-weight: 700; font-size: 15px; text-align: right; color: var(--text-dim); }
</style>
