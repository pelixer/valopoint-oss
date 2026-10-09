<script>
  // Model room (design v2 · 12): "does it predict well?" first, model internals after.
  import { app } from '../lib/store.svelte.js';
  import { fx, kstShort, pct } from '../lib/format.js';
  import { lockedResults, summarize } from '../lib/ledger.js';

  const m = app.model;
  const bt = m.meta.backtest_map ?? {};
  const w = Object.entries(m.meta.diag?.weights ?? {});
  const wmax = Math.max(...w.map(([, v]) => Math.abs(v)), 1e-9);
  const rel = m.calib?.reliability ?? [];
  // reliability chart: predicted 50–100% (x) vs actual 30–100% (y)
  const W = 334, H = 220, L = 34, R = 10, T = 10, B = 28;
  const X = (p) => L + ((p - 0.5) / 0.5) * (W - L - R);
  const Y = (p) => T + (1 - (p - 0.3) / 0.7) * (H - T - B);
  let locked = $derived(lockedResults(app.ledger, app.brackets));
  let sum = $derived(summarize(locked));
  let pending = $derived.by(() => {
    const done = new Set(locked.map((r) => r.bracket + '/' + r.match));
    const last = new Map();
    for (const e of app.ledger ?? []) if (!done.has(e.bracket + '/' + e.match)) last.set(e.bracket + '/' + e.match, e);
    return [...last.values()].filter((e) => !e.match_time || Date.parse(e.match_time) > Date.now())
      .sort((a, b) => Date.parse(a.match_time ?? 0) - Date.parse(b.match_time ?? 0));
  });
  let firstRecord = $derived((app.ledger ?? []).reduce((a, e) => (!a || e.recorded_at < a ? e.recorded_at : a), null));
  const KEY = { kpr: 'KPR', dpr: 'DPR', apr: 'APR', fkpr: 'FKPR', fdpr: 'FDPR', adr: 'ADR', kast: 'KAST' };
  const LABEL = { kpr: '킬/라운드', dpr: '데스/라운드', apr: '어시/라운드', fkpr: '선킬/라운드', fdpr: '선데스/라운드', adr: 'ADR', kast: 'KAST' };
  const RC = { AMER: 'var(--r-amer)', EMEA: 'var(--r-emea)', PAC: 'var(--r-pac)', CN: 'var(--r-cn)' };
  const sgn = (x, d = 1) => `${x >= 0 ? '+' : '−'}${Math.abs(x).toFixed(d)}`;
  const two = (iso) => kstShort(iso).replace(/\s(\d\d:\d\d)$/, '\n$1');
</script>

<div class="kicker">Model room</div>
<h1 style="margin-bottom:0">모델</h1>
<div class="meta3">
  <div><span class="l">기준일</span><span class="num v">{m.meta.as_of}</span></div>
  <div><span class="l">데이터</span><span class="num v">{m.meta.data_from} ~</span></div>
  <div><span class="l">갱신 KST</span><span class="num v">{kstShort(m.meta.generated_at)}</span></div>
</div>
<p class="note">{[m.meta.live_events?.length ? `진행 중 국제전 반영: ${m.meta.live_events.join(', ')}` : null, `출처 ${m.meta.source_info?.name ?? m.meta.source}`].filter(Boolean).join(' · ')}</p>

<div class="sec"><div><span class="k">Backtest · intl maps</span><span class="t">백테스트 (walk-forward)</span></div></div>
<div class="bt">
  <div class="acc"><span class="l">정확도</span><span class="num v">{bt.accuracy != null ? (bt.accuracy * 100).toFixed(1) : '–'}<small>%</small></span><span class="l">평가 맵 {bt.n ?? '–'}</span></div>
  <div class="ll">
    {#each [['Log loss', bt.log_loss, 0.693, 3], ['Brier', bt.brier, 0.25, 4]] as [k, v, coin, d]}
      <div class="lr"><span class="l">{k}</span><span class="num">{fx(v, d)}</span></div>
      <div class="lb"><i style="width:{v != null ? Math.min(100, (v / coin) * 100).toFixed(1) : 0}%"></i><b></b></div>
    {/each}
    <span class="l">레드 눈금 = 동전(0.693 · 0.25). 짧을수록 좋음</span>
  </div>
</div>

<div class="sec"><div><span class="k">Calibration</span><span class="t">보정 그래프</span></div></div>
<div class="card">
  {#if rel.length}
    <svg viewBox="0 0 {W} {H + 8}" style="width:100%; display:block; overflow:visible" role="img" aria-label="예측 확률 대 실제 승률">
      {#each [0.3, 0.5, 0.7, 0.9] as t}
        <line x1={L} x2={W - R} y1={Y(t)} y2={Y(t)} stroke="var(--line)" />
        <text x={L - 6} y={Y(t) + 4} text-anchor="end" font-size="11" fill="var(--muted)" font-family="var(--font-num)">{t * 100}%</text>
      {/each}
      {#each [0.5, 0.6, 0.7, 0.8, 0.9, 1] as t}
        <text x={X(t)} y={H - 10} text-anchor="middle" font-size="11" fill="var(--muted)" font-family="var(--font-num)">{Math.round(t * 100)}%</text>
      {/each}
      <line x1={X(0.5)} y1={Y(0.5)} x2={X(1)} y2={Y(1)} stroke="var(--text-dim)" stroke-dasharray="3 4" />
      <polyline fill="none" stroke="var(--accent)" stroke-width="1.5" points={rel.map((b) => `${X(b.pred)},${Y(b.actual)}`).join(' ')} />
      {#each rel as b}
        {@const r = 3 + Math.sqrt(b.n) * 0.9}
        <rect x={X(b.pred) - r} y={Y(b.actual) - r} width={2 * r} height={2 * r} fill="rgba(242,67,79,.25)" stroke="var(--accent)" stroke-width="1.5" transform="rotate(45 {X(b.pred)} {Y(b.actual)})" />
      {/each}
      <text x={(L + W - R) / 2} y={H + 4} text-anchor="middle" font-size="11" fill="var(--muted)">예측한 유력팀 승률 → · 실제 승률 ↑</text>
    </svg>
    <div class="tbl">
      <span class="h">예측 구간</span><span class="h r">맵</span><span class="h r">평균 예측</span><span class="h r">실제</span>
      {#each rel as b}
        <span class="num">{pct(b.lo)}–{pct(b.hi)}</span><span class="num r dim">{b.n}</span><span class="num r">{pct(b.pred, 1)}</span><span class="num r b">{pct(b.actual, 1)}</span>
      {/each}
    </div>
    <p class="note">국제전 맵을 walk-forward(해당 경기 이전 데이터만으로)로 예측한 결과입니다. 점이 점선(완벽 보정) 위에 있으면 70%라고 한 경기를 실제로 70% 이깁니다. 점 크기 = 표본 수.</p>
  {:else}
    <p class="note">다음 모델 갱신 후 표시됩니다.</p>
  {/if}
</div>

<div class="sec"><div><span class="k">Ledger</span><span class="t">기록된 경기 전 예측</span></div></div>
<div class="card">
  {#if sum}
    <div class="lsum"><span class="num big">{sum.correct}/{sum.n} <em>{pct(sum.correct / sum.n)}</em></span><span class="l">모델 기대 {fx(sum.expected, 1)} · Log loss {fx(sum.logLoss, 3)} · Brier {fx(sum.brier, 3)}</span></div>
    {#each [...locked].reverse() as r}
      {@const fav = r.p >= 0.5 ? r.team_a : r.team_b}
      <div class="lrow"><span class="num t">{two(r.match_time)}</span><span class="disp">{fav} <em>{pct(Math.max(r.p, 1 - r.p))}</em></span><span class="res" class:ok={r.correct}>{r.correct ? '○' : '×'} {r.winner}</span></div>
    {/each}
  {:else}
    <p class="note" style="margin-top:0">아직 기록된 예측으로 끝난 경기가 없습니다.</p>
  {/if}
  {#if pending.length}
    <div class="ph">기록 중 (경기 전)</div>
    {#each pending as e}
      <div class="lrow pend"><span class="num t">{two(e.match_time)}</span><span class="disp">{e.team_a} vs {e.team_b}</span><span class="num p">{pct(e.p)}</span></div>
    {/each}
  {/if}
  <p class="note">00시·12시(KST) 갱신 때마다 시작 전인 경기의 예측을 시각과 함께 추가만 하는 파일(ledger.json)에 남깁니다.{#if firstRecord} 기록 시작 {kstShort(firstRecord)}.{/if} 경기가 끝나면 시작 직전 마지막 기록으로 채점합니다. 기존 기록은 수정하지 않으며, 저장소의 Git 이력이 그 증거입니다.</p>
</div>

<div class="sec"><div><span class="k">Stat weights</span><span class="t">학습된 stat 가중치</span></div></div>
<div class="card wts">
  {#each w as [k, v]}
    {@const ww = (Math.abs(v) / wmax) * 50}
    <div class="wrow">
      <span class="disp">{KEY[k] ?? k}</span><span class="l">{LABEL[k] ?? ''}</span>
      <div class="wb"><b></b><i style="left:{v >= 0 ? 50 : 50 - ww}%; width:{Math.max(ww, 0.8)}%; background:{v >= 0 ? 'var(--good)' : 'var(--bad)'}"></i></div>
      <span class="num" style="color:{v >= 0 ? 'var(--good)' : 'var(--bad)'}">{v >= 0 ? '▲' : '▼'} {Math.abs(v).toFixed(4)}</span>
    </div>
  {/each}
  <p class="note">역할군 내 표준화 후, 맵 라운드 승률에 대한 회귀로 추정한 기여도. ▲ 양수 = 높을수록 좋음, ▼ 음수 = 높을수록 나쁨.</p>
</div>

<div class="sec"><div><span class="k">Region adjust</span><span class="t">지역 보정</span></div></div>
<div class="regs">
  {#each Object.entries(m.regions) as [r, v]}
    <div style="--rc:{RC[r]}"><span class="rk disp">{r}</span><span class="num pp">{sgn(v.offset_pp)}</span><span class="l">PP/선수</span><span class="num g">{sgn(v.gamma, 3)}</span><span class="l">국제전 γ</span></div>
  {/each}
</div>
<p class="note" style="font-size:11px">PP 보정: 국제전 stat으로 추정한 지역 수준(리그 간 환산). γ: stat으로 설명되지 않는 국제전 승패 잔차(최근 2년, 시간 가중). 보정 기울기 β = {fx(m.calib.beta, 3)}</p>

<div class="two">
  <div>
    <div class="sec small"><div><span class="k">Shrinkage</span><span class="t">축소 강도</span></div></div>
    <div class="box">
      {#each Object.entries(m.meta.diag?.shrinkage_k_rounds ?? {}) as [k, v]}
        <div class="kv"><code>{k}</code><span class="num">{fx(v, 0)}</span></div>
      {/each}
      <p class="note" style="font-size:10px">절반 신뢰에 필요한 라운드 수</p>
    </div>
  </div>
  {#if m.veto_model}
    <div>
      <div class="sec small"><div><span class="k">Veto model</span><span class="t">밴픽 모델</span></div></div>
      <div class="box vm">
        <span class="num big">{m.veto_model.n}<em> 건</em></span>
        <span class="dim small">반영 기간: {m.veto_model.events.map((e) => e.replace(/^(VCT \d{4}: |Valorant )/, '')).join(', ')}</span>
        <span class="note" style="font-size:10px; margin:0">검증 181경기: 실제 맵이 예상 세트 순서에 든 비율 55%(그리디 44%), 시리즈 log loss 0.6678 → 0.6671</span>
      </div>
    </div>
  {/if}
</div>

<style>
  .note { font-size: 12px; line-height: 1.55; color: var(--muted); margin: 6px 0 0; }
  .card .note { font-size: 11px; margin-top: 8px; }
  .l { font-size: 11px; color: var(--muted); }
  .meta3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 2px; margin-top: 14px; }
  .meta3 > div { padding: 10px; background: var(--surface); display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .meta3 .v { font-weight: 700; font-size: 17px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  .bt { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 2px; }
  .bt > div { padding: 12px; background: var(--surface); display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .acc { box-shadow: inset 0 2px 0 var(--accent); }
  .acc .v { font-weight: 800; font-size: 40px; line-height: 1; }
  .acc small { font-size: 20px; }
  .ll { gap: 6px !important; }
  .lr { display: flex; justify-content: space-between; align-items: baseline; margin-top: 2px; }
  .lr .l { font-size: 12px; }
  .lr .num { font-weight: 700; font-size: 20px; }
  .lb { height: 3px; background: var(--bg); position: relative; }
  .lb i { position: absolute; left: 0; top: 0; bottom: 0; background: var(--text-dim); }
  .lb b { position: absolute; left: 100%; top: -3px; bottom: -3px; width: 1px; background: var(--accent); }

  .tbl { display: grid; grid-template-columns: minmax(0, 1fr) 44px 64px 56px; gap: 0 4px; font-size: 13px; margin-top: 10px; }
  .tbl > span { padding: 5px 0; border-bottom: 1px solid var(--line); }
  .tbl .h { font-size: 11px; color: var(--muted); border-bottom-color: var(--line-strong); }
  .tbl .num { font-size: 15px; }
  .tbl .r { text-align: right; }
  .tbl .dim { color: var(--text-dim); }
  .tbl .b { font-weight: 700; }

  .lsum { display: flex; flex-wrap: wrap; gap: 4px 14px; align-items: baseline; margin-bottom: 8px; }
  .big { font-weight: 800; font-size: 28px; }
  .big em { font-style: normal; font-size: 18px; color: var(--text-dim); }
  .lrow { display: grid; grid-template-columns: 52px minmax(0, 1fr) auto; gap: 10px; align-items: center; padding: 8px 0; border-top: 1px solid var(--line); }
  .lrow.pend { border-top-style: dashed; border-top-color: var(--line-strong); }
  .lrow .t { font-size: 14px; color: var(--muted); line-height: 1.1; white-space: pre-line; }
  .lrow .disp { font-size: 17px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .lrow .disp em { font-style: normal; color: var(--text-dim); }
  .lrow .res { font-size: 13px; font-weight: 700; color: var(--bad); white-space: nowrap; max-width: 150px; overflow: hidden; text-overflow: ellipsis; }
  .lrow .res.ok { color: var(--good); }
  .lrow .p { font-weight: 700; font-size: 17px; text-align: right; }
  .ph { font-size: 12px; font-weight: 700; margin: 12px 0 4px; }

  .wts { padding: 6px 12px 10px; }
  .wrow { display: grid; grid-template-columns: 44px 74px minmax(0, 1fr) 62px; gap: 8px; align-items: center; height: 32px; border-bottom: 1px solid var(--line); }
  .wrow .disp { font-size: 15px; }
  .wb { position: relative; height: 6px; }
  .wb b { position: absolute; left: 50%; top: -4px; bottom: -4px; width: 1px; background: var(--line-strong); }
  .wb i { position: absolute; top: 0; bottom: 0; }
  .wrow .num { font-weight: 700; font-size: 15px; text-align: right; white-space: nowrap; }

  .regs { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 2px; }
  .regs > div { padding: 10px 8px; background: var(--surface); display: flex; flex-direction: column; gap: 4px; box-shadow: inset 0 3px 0 var(--rc); min-width: 0; }
  .rk { font-size: 12px; letter-spacing: .08em; color: var(--rc); }
  .regs .pp { font-weight: 800; font-size: 26px; line-height: 1; }
  .regs .g { font-weight: 700; font-size: 16px; color: var(--text-dim); margin-top: 4px; }
  .regs .l { font-size: 10px; }

  .two { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 8px; margin-top: 8px; }
  .two .sec { margin: 20px 0 8px; }
  .two .sec::after { display: none; }
  .two .sec .t { font-size: 17px; }
  .box { background: var(--surface); padding: 8px 10px; }
  .kv { display: flex; justify-content: space-between; align-items: baseline; height: 28px; border-bottom: 1px solid var(--line); gap: 6px; }
  .kv code { font-family: ui-monospace, Menlo, monospace; font-size: 11px; color: var(--text-dim); overflow: hidden; text-overflow: ellipsis; }
  .kv .num { font-weight: 700; font-size: 17px; }
  .vm { display: flex; flex-direction: column; gap: 4px; }
  .vm .big { font-size: 26px; line-height: 1; }
  .vm .big em { font-size: 13px; color: var(--muted); }
  .vm .small { font-size: 11px; line-height: 1.5; }
</style>
