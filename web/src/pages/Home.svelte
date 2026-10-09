<script>
  // Home (design v2): the live international event at a glance, today's matches, MVP race.
  import { app } from '../lib/store.svelte.js';
  import { simulateBracket } from '../lib/engine.js';
  import { groupOf, resolveTeams } from '../lib/bracket.js';
  import { fx, kstShort, pct } from '../lib/format.js';
  import { buildContext, highlights } from '../lib/profile.js';
  import Glyph from '../lib/Glyph.svelte';
  import { persisted } from '../lib/store.svelte.js';
  import { nextDeadline } from '../lib/pickem.js';

  let br = $derived(app.brackets.find((b) => b.kind === 'full' || b.kind === undefined) ?? null);
  let done = $derived(br ? Object.keys(br.results ?? {}).length : 0);
  let total = $derived(br?.matches.length ?? 0);
  let live = $derived(!!br && done < total);
  // title odds from official results only (my what-if locks stay on the bracket tab)
  let sim = $derived(live ? simulateBracket(app.engine, br, br.results ?? {}, 20000) : null);
  let odds = $derived(sim ? Object.entries(sim.champion).sort((a, b) => b[1] - a[1]).slice(0, 3) : []);

  const dayKey = (iso) => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul' }).format(new Date(iso));
  const hm = (iso) => new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(iso));
  const dayLabel = (iso) => new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Seoul', month: 'numeric', day: 'numeric', weekday: 'short' }).format(new Date(iso)).replace(/^(\w+), (\d+)\/(\d+)$/, '$2.$3 $1').toUpperCase();
  // today's matches in KST; if none, the next match day
  let fixed = $derived(br ? resolveTeams(br, br.results ?? {}) : {});
  let day = $derived.by(() => {
    if (!br) return null;
    const ms = br.matches.filter((m) => m.time && !br.results?.[m.id]).sort((a, b) => a.time.localeCompare(b.time));
    const today = dayKey(new Date().toISOString());
    const todays = br.matches.filter((m) => m.time && dayKey(m.time) === today).sort((a, b) => a.time.localeCompare(b.time));
    if (todays.length) return { today: true, label: dayLabel(todays[0].time), items: todays };
    if (!ms.length) return null;
    const next = dayKey(ms[0].time);
    return { today: false, label: dayLabel(ms[0].time), items: ms.filter((m) => dayKey(m.time) === next) };
  });

  let ctx = $derived(buildContext(app.model, app.brackets));
  let hot = $derived.by(() => {
    const hs = highlights(ctx, 3);
    return hs.find((s) => s.key === 'mvp') ?? hs.find((s) => s.key === 'power') ?? null;
  });
  let topTeams = $derived(app.model.teams.slice(0, 5));
  // my bracket line under the event block
  let myPicks = $derived(br ? (persisted('mybracket', {}).get()[br.id]?.picks ?? {}) : {});
  let myDl = $derived(br ? nextDeadline(br, myPicks) : null);
</script>

{#if br && live}
  <a class="event" href="#/bracket">
    <span class="corner tr"></span>
    <div class="ev-top"><span class="live"><i></i>Live event</span><span class="prog">{done} / {total} 경기 완료</span></div>
    <div class="ev-name disp">{br.name}</div>
    <div class="ev-bar"><span style="width:{((done / total) * 100).toFixed(1)}%"></span></div>
    <div class="ev-meta"><span>우승 확률 · 20,000회 시뮬레이션</span>{#if app.bracketsAt}<span class="num">{kstShort(app.bracketsAt)} 갱신</span>{/if}</div>
    <div class="odds">
      {#each odds as [t, p], i}
        <div class="odd">
          <span class="num r" class:first={i === 0}>{i + 1}</span>
          <span class="disp t">{t}</span>
          <div class="ob"><i style="width:{((p / odds[0][1]) * 100).toFixed(0)}%" class:first={i === 0}></i></div>
          <span class="num p">{pct(p, 1)}</span>
        </div>
      {/each}
    </div>
    <div class="more"><span>대진 전체 ›</span></div>
  </a>
  <a class="mybr" href="#/bracket?mode=mine">
    <i></i>
    <div><b>내 대진표 <span class="num">{Object.keys(myPicks).length}/{total}</span></b>
      <span>{myDl ? `다음 마감 ${kstShort(myDl.time)}` : Object.keys(myPicks).length ? '남은 픽 없음 · 결과 대기' : '대회 전체 승자를 미리 골라 보세요'}</span></div>
    <em>{Object.keys(myPicks).length ? '이어서' : '고르기'} ›</em>
  </a>

  {#if day}
    <div class="sec"><div><span class="k">{day.today ? 'Today' : 'Next'} · {day.label}</span><span class="t">{day.today ? '오늘 경기' : '다음 경기'}</span></div></div>
    <div class="today">
      {#each day.items as m, i}
        {@const f = fixed[m.id] ?? {}}
        {@const g = groupOf(m)}
        {@const p = f.a && f.b ? app.engine.series(f.a, f.b, m.best_of ?? 3).p : null}
        {@const win = br.results?.[m.id]}
        <a class="tm rise" style="--i:{i}; --gc:{g.color}" href={`#/game/${br.id}/${m.id}`}>
          <div class="tm-when"><span class="num">{hm(m.time)}</span><span class="grp"><i></i>{g.label}</span></div>
          <div class="tm-body">
            {#if f.a && f.b}
              <div class="vs"><span class="disp" class:lost={win && win !== f.a}>{f.a}</span><span class="v">VS</span><span class="disp r" class:lost={win && win !== f.b}>{f.b}</span></div>
              <div class="pbar"><span class="num">{pct(p)}</span><div class="vbar"><span style="width:{(p * 100).toFixed(1)}%"></span><span></span></div><span class="num r">{pct(1 - p)}</span></div>
            {:else}
              {@const proj = Object.entries(sim?.slot?.[m.id] ?? {}).sort((x, y) => y[1] - x[1]).slice(0, 3)}
              <div class="vs"><span class="muted">대진 미정</span></div>
              {#if proj.length}<span class="proj">진출 예상 {#each proj as [t, q], k}{k ? ' · ' : ''}<b>{t}</b> {pct(q)}{/each}</span>{/if}
            {/if}
            <span class="meta">{m.round} · Bo{m.best_of ?? 3} · {win ? `종료 · ${win} 승` : '경기 전'}</span>
          </div>
        </a>
      {/each}
    </div>
  {/if}
{:else}
  <div class="kicker">Power ranking</div>
  <h1>팀 파워 Top 5</h1>
  {#each topTeams as t, i}
    <a class="trow" href={`#/team/${encodeURIComponent(t.name)}`}>
      <span class="num r" class:first={i === 0}>{i + 1}</span>
      <span class="disp">{t.name}</span><span class="badge sm {t.region}">{t.region}</span>
      <span class="num p">{fx(t.pp, 0)}</span>
    </a>
  {/each}
  <a class="detail-link" href="#/teams">팀 랭킹 전체 ›</a>
{/if}

{#if hot}
  <div class="sec">
    <div><span class="k" style="display:flex; align-items:center; gap:6px"><Glyph name={hot.icon} size={11} color="var(--accent)" />{hot.key === 'mvp' ? 'MVP race' : 'Power top'}</span><span class="t">화제 선수</span></div>
    <a class="seclink" href="#/players">선수 탭 ›</a>
  </div>
  <div class="mvp">
    {#each hot.rows.slice(0, 3) as r, i}
      <a class="mv" class:first={i === 0} href={`#/player/${r.p.id}`}>
        <span class="num r">{i + 1}</span>
        <span class="disp n">{r.p.name}</span>
        <span class="tn">{r.p.team}</span>
        <span class="num v">{r.value}</span>
      </a>
    {/each}
  </div>
{/if}

<style>
  a { color: inherit; text-decoration: none; }
  .event {
    position: relative; display: block; padding: 16px;
    background: linear-gradient(115deg, rgba(242, 67, 79, .18) 0 38%, var(--surface) 38%);
    clip-path: polygon(14px 0, 100% 0, 100% calc(100% - 14px), calc(100% - 14px) 100%, 0 100%, 0 14px);
    animation: wipe var(--dur-slow) var(--ease-out) backwards;
  }
  .ev-top { display: flex; align-items: center; gap: 8px; }
  .live {
    display: flex; align-items: center; gap: 5px; height: 20px; padding: 0 7px; background: var(--accent); color: var(--accent-ink);
    font-family: var(--font-display); font-size: 12px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase;
  }
  /* static dot; one glow pulse on entry, never an endless loop */
  .live i { width: 5px; height: 5px; border-radius: 50%; background: var(--accent-ink); }
  .live { animation: pulse 1s var(--ease-out) 1; }
  @media (prefers-reduced-motion: reduce) { .live { animation: none; } }
  @keyframes pulse { 0% { box-shadow: 0 0 0 0 var(--accent-glow); } 60% { box-shadow: 0 0 0 8px transparent; } }
  .prog { font-family: var(--font-display); font-weight: 600; font-size: 13px; letter-spacing: .06em; color: var(--text-dim); }
  .ev-name { font-weight: 800; font-size: 44px; line-height: .92; margin-top: 10px; text-transform: uppercase; }
  .ev-bar { height: 3px; margin-top: 12px; background: var(--bg); }
  .ev-bar span { display: block; height: 3px; background: var(--accent); }
  .ev-meta { display: flex; align-items: center; justify-content: space-between; margin-top: 14px; font-size: 12px; color: var(--muted); }
  .ev-meta .num { font-size: 13px; }
  .odds { display: flex; flex-direction: column; margin-top: 6px; }
  .odd { display: grid; grid-template-columns: 22px minmax(0, 1fr) 110px 56px; gap: 10px; align-items: center; height: 40px; border-top: 1px solid var(--line); }
  .odd .r { font-weight: 800; font-size: 20px; color: var(--muted); }
  .odd .r.first { color: var(--accent); }
  .odd .t, .odd .p { font-size: 20px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .odd .p { font-weight: 700; text-align: right; }
  .ob { height: 4px; background: var(--bg); }
  .ob i { display: block; height: 4px; background: var(--text-dim); transition: width var(--dur-slow) var(--ease-out); }
  .ob i.first { background: var(--accent); }
  .more { display: flex; justify-content: flex-end; margin: 4px -8px -10px 0; }
  .more span { height: var(--hit); display: flex; align-items: center; padding: 0 8px; font-size: 13px; font-weight: 600; color: var(--accent); }
  @media (max-width: 360px) { .odd { grid-template-columns: 22px minmax(0, 1fr) 70px 52px; } .ev-name { font-size: 36px; } }

  .mybr { display: grid; grid-template-columns: 10px minmax(0, 1fr) auto; gap: 12px; align-items: center; margin-top: 8px; padding: 12px 14px; background: var(--surface); }
  .mybr i { width: 9px; height: 9px; background: var(--accent); transform: rotate(45deg); }
  .mybr div { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .mybr b { font-size: 15px; }
  .mybr b .num { font-size: 17px; }
  .mybr span { font-size: 12px; color: var(--muted); }
  .mybr em { font-style: normal; font-size: 13px; font-weight: 600; color: var(--accent); }
  .today { display: flex; flex-direction: column; gap: 8px; }
  .tm { display: grid; grid-template-columns: 52px minmax(0, 1fr); background: var(--surface); clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px); }
  .tm-when { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; background: var(--bg-2); box-shadow: inset -1px 0 0 var(--line); }
  .tm-when .num { font-weight: 700; font-size: 18px; }
  .grp { display: flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 700; white-space: nowrap; }
  .grp i { width: 6px; height: 6px; background: var(--gc); }
  .tm-body { padding: 10px 12px; display: flex; flex-direction: column; gap: 6px; min-width: 0; }
  .vs { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); gap: 8px; align-items: baseline; }
  .vs .disp { font-size: 19px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .vs .disp.r { text-align: right; }
  .vs .lost { color: var(--muted); }
  .vs .v { font-family: var(--font-display); font-weight: 600; font-size: 13px; color: var(--muted); }
  .pbar { display: grid; grid-template-columns: 34px minmax(0, 1fr) 34px; gap: 8px; align-items: center; }
  .pbar .num { font-weight: 700; font-size: 16px; color: var(--text-dim); }
  .pbar .num.r { text-align: right; }
  .meta { font-size: 11px; color: var(--muted); }
  .proj { font-size: 12px; color: var(--text-dim); line-height: 1.45; }
  .proj b { font-family: var(--font-display); font-weight: 700; font-size: 14px; color: var(--text); }

  .seclink { font-size: 13px; font-weight: 600; color: var(--accent); margin-bottom: 2px; order: 3; }
  .mvp { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
  .mv { position: relative; padding: 10px; background: var(--surface); display: flex; flex-direction: column; gap: 4px; min-width: 0; }
  .mv.first { box-shadow: inset 0 2px 0 var(--accent); }
  .mv .r { font-weight: 800; font-size: 28px; line-height: .85; color: var(--muted); }
  .mv.first .r { color: var(--accent); }
  .mv .n { font-size: 19px; line-height: 1.2; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mv .tn { font-size: 11px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mv .v { font-weight: 800; font-size: 26px; line-height: 1; margin-top: 4px; }

  .trow { display: grid; grid-template-columns: 26px auto 1fr auto; gap: 10px; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--line); }
  .trow .r { font-weight: 800; font-size: 22px; color: var(--muted); text-align: right; }
  .trow .r.first { color: var(--accent); }
  .trow .disp { font-size: 20px; }
  .trow .badge { justify-self: start; }
  .trow .p { font-weight: 700; font-size: 24px; }
</style>
