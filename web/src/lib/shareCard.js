// "내 대진표" share card (design 4a · P6): drawn on a canvas at a fixed size
// (feed 1080×1350, story 1080×1920) and handed to the share sheet as a PNG.
// Canvas 2D only: solid fills, gradients, chamfered panels, two web fonts. No filters.
import { app } from './store.svelte.js';
import { stages } from './pickem.js';

const C = {
  bg: '#0B0F17', surface: '#141A26', surface2: '#1B2232', line: '#263042', lineStrong: '#3A465C',
  text: '#EEE8DE', dim: '#B9B3A9', muted: '#8A8F9A', accent: '#F2434F', ink: '#14080A',
  good: '#6EE7A0', bad: '#FF8A5C', warn: '#F5C451',
};
const BAR = '"Barlow Condensed", "Pretendard Variable", sans-serif';
const PRE = '"Pretendard Variable", Pretendard, sans-serif';
const GROUP = { A: '#5B9DFF', B: '#B48CFF', C: '#45D49A', D: '#F5B94A', E: '#FF7EB6', F: '#3CC8D8', G: '#C6D86A', H: '#FF9C66', U: '#EEE8DE', L: '#8A8F9A' };

function chamfer(ctx, x, y, w, h, c) {
  ctx.beginPath();
  ctx.moveTo(x + c, y); ctx.lineTo(x + w, y); ctx.lineTo(x + w, y + h - c);
  ctx.lineTo(x + w - c, y + h); ctx.lineTo(x, y + h); ctx.lineTo(x, y + c); ctx.closePath();
}
function text(ctx, s, x, y, { font, size, weight = 700, color = C.text, align = 'left', spacing = 0 }) {
  ctx.font = `${weight} ${size}px ${font}`;
  ctx.fillStyle = color;
  ctx.textAlign = align;
  ctx.textBaseline = 'alphabetic';
  if ('letterSpacing' in ctx) ctx.letterSpacing = `${spacing}px`;
  ctx.fillText(s, x, y);
  if ('letterSpacing' in ctx) ctx.letterSpacing = '0px';
}
function ellipsize(ctx, s, maxW) {
  if (ctx.measureText(s).width <= maxW) return s;
  let t = s;
  while (t.length > 1 && ctx.measureText(`${t}…`).width > maxW) t = t.slice(0, -1);
  return `${t}…`;
}
/** Largest size (step 4px) at which `s` fits in `lines` lines of width maxW. */
function fit(ctx, s, maxW, { max, min, lines = 3, weight = 800 }) {
  const words = s.split(/\s+/);
  for (let size = max; size >= min; size -= 4) {
    ctx.font = `${weight} ${size}px ${BAR}`;
    const out = [];
    let cur = '';
    for (const w of words) {
      const next = cur ? `${cur} ${w}` : w;
      if (ctx.measureText(next).width <= maxW) cur = next;
      else { if (cur) out.push(cur); cur = w; }
    }
    if (cur) out.push(cur);
    if (out.length <= lines && out.every((l) => ctx.measureText(l).width <= maxW)) return { size, lines: out };
  }
  ctx.font = `${weight} ${min}px ${BAR}`;
  return { size: min, lines: [ellipsize(ctx, s, maxW)] };
}
const fmtDate = (ms) => {
  const d = new Date(ms);
  const p = (o) => new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', ...o }).format(d).replace(/\D/g, '');
  return `${p({ year: 'numeric' })}. ${p({ month: 'numeric' })}. ${p({ day: 'numeric' })}.`;
};

async function loadFonts() {
  if (!document.fonts?.load) return;
  const ko = '내 우승 예상 픽 완료 대회 종료 결과 대기 적중 빗나감 결승 상위 하위 강 모델과 다른 데이터 무관한 팬 프로젝트 조 경기';
  await Promise.all([
    document.fonts.load(`800 100px "Barlow Condensed"`), document.fonts.load(`700 40px "Barlow Condensed"`),
    document.fonts.load(`600 24px "Barlow Condensed"`),
    document.fonts.load(`700 28px "Pretendard Variable"`, ko), document.fonts.load(`500 24px "Pretendard Variable"`, ko),
  ]);
}

/**
 * Draw the card. data: {br, picks, states, slots, score, champion, path (time order), story, now, model,
 *   advance, finalists, semis, agree}
 * Returns a canvas.
 */
export async function renderCard(data) {
  await loadFonts();
  const { br, picks, states, score, champion, story, now, advance = [], semis = [], agree } = data;
  const path = data.path ?? [];
  const W = 1080, H = story ? 1920 : 1350, X = 80, R = W - 80;
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = H;
  const ctx = cv.getContext('2d');
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  // static scanlines
  ctx.fillStyle = 'rgba(238,232,222,0.018)';
  for (let y = 0; y < H; y += 3) ctx.fillRect(0, y, W, 1);
  ctx.strokeStyle = C.line; ctx.lineWidth = 2; ctx.strokeRect(1, 1, W - 2, H - 2);

  const finished = !!br.results?.[br.final ?? 'GF'];
  // header
  ctx.save(); ctx.translate(X + 11, 92); ctx.rotate(Math.PI / 4); ctx.fillStyle = C.accent; ctx.fillRect(-9, -9, 18, 18); ctx.restore();
  text(ctx, 'valopoint', X + 34, 104, { font: BAR, size: 44, weight: 700 });
  text(ctx, 'MY BRACKET', R, 102, { font: BAR, size: 24, weight: 600, color: C.dim, align: 'right', spacing: 4 });
  ctx.fillStyle = C.accent; ctx.fillRect(X, 140, 96, 5);
  const ev = fit(ctx, br.name.toUpperCase(), R - X, { max: 76, min: 48, lines: 2 });
  ev.lines.forEach((l, i) => text(ctx, l, X, 224 + i * ev.size * 0.95, { font: BAR, size: ev.size, weight: 800 }));
  let y = 224 + (ev.lines.length - 1) * ev.size * 0.95 + 46;
  text(ctx, `${fmtDate(now)} ${finished ? '대회 종료' : score.results ? '진행 중' : '픽 완료'}`, X, y, { font: PRE, size: 26, weight: 500, color: C.dim });
  y += 50;

  // champion panel
  const ph = story ? 440 : 420;
  chamfer(ctx, X, y, R - X, ph, 28);
  ctx.save(); ctx.clip();
  ctx.fillStyle = C.surface; ctx.fillRect(X, y, R - X, ph);
  ctx.fillStyle = 'rgba(242,67,79,0.22)';
  ctx.beginPath(); ctx.moveTo(X, y); ctx.lineTo(X + 330, y); ctx.lineTo(X + 330 - ph * Math.tan((25 * Math.PI) / 180), y + ph); ctx.lineTo(X, y + ph); ctx.closePath(); ctx.fill();
  ctx.restore();
  ctx.strokeStyle = C.dim; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(R - 52, y + 22); ctx.lineTo(R - 24, y + 22); ctx.lineTo(R - 24, y + 50); ctx.stroke();
  text(ctx, '✦ 내 우승 예상', X + 40, y + 64, { font: PRE, size: 28, weight: 700, color: C.accent });
  if (finished) {
    const ok = br.results[br.final ?? 'GF'] === champion;
    ctx.fillStyle = ok ? C.text : 'transparent';
    const tw = 170, tx = R - 60 - tw;
    if (ok) ctx.fillRect(tx, y + 34, tw, 42); else { ctx.strokeStyle = C.bad; ctx.strokeRect(tx, y + 34, tw, 42); }
    text(ctx, ok ? '✓ 우승 적중' : '× 우승 빗나감', tx + tw / 2, y + 64, { font: PRE, size: 24, weight: 800, color: ok ? C.ink : C.bad, align: 'center' });
  }
  const cn = fit(ctx, champion ?? '아직 고르지 않음', R - X - 80, { max: 176, min: 84, lines: 2 });
  const lh = cn.size * 0.92;
  cn.lines.forEach((l, i) => text(ctx, l, X + 40, y + 96 + cn.size * 0.8 + i * lh, { font: BAR, size: cn.size, weight: 800, color: champion ? C.text : C.muted }));
  let py = y + 96 + cn.size * 0.8 + (cn.lines.length - 1) * lh + 64;
  // panel rows: the final first, then the other upper semifinalists
  const fin = path.find((p) => p.final);
  const others = semis.filter((t) => t && t !== champion);
  const prow = [
    fin && { label: '결승', val: fin.opp ? `vs ${fin.opp}` : '상대 미정', size: 46, color: C.accent, vc: C.text },
    others.length && { label: '상위 4강', val: others.join(' · '), size: 38, color: C.muted, vc: C.dim },
  ].filter(Boolean);
  for (const r of prow) {
    if (py + 8 > y + ph - 16) break;
    ctx.fillStyle = C.line; ctx.fillRect(X + 40, py - r.size - 6, R - X - 80, 2);
    text(ctx, r.label, X + 40, py, { font: PRE, size: 26, weight: 700, color: r.color });
    ctx.font = `700 ${r.size}px ${BAR}`;
    text(ctx, ellipsize(ctx, r.val, R - X - 280), X + 200, py, { font: BAR, size: r.size, weight: 700, color: r.vc });
    py += r.size + 26;
  }
  y += ph + 40;

  // story: champion path in time order (final is in the panel), then the per-match strip by stage
  if (story) {
    const steps = path.filter((p) => !p.final);
    if (steps.length) {
      text(ctx, '우승까지', X, y + 20, { font: PRE, size: 24, weight: 700, color: C.dim });
      y += 36;
      for (const p of steps) {
        ctx.fillStyle = C.surface; ctx.fillRect(X, y, R - X, 66);
        ctx.fillStyle = C.accent; ctx.fillRect(X, y, 6, 66);
        text(ctx, p.round, X + 28, y + 44, { font: PRE, size: 28, weight: 600, color: C.muted });
        ctx.font = `700 40px ${BAR}`;
        text(ctx, ellipsize(ctx, p.opp ? `vs ${p.opp}` : '상대 미정', R - X - 320), X + 290, y + 47, { font: BAR, size: 40, weight: 700 });
        y += 72;
      }
      y += 28;
    }
    text(ctx, `${br.matches.length} MATCHES`, X, y + 20, { font: BAR, size: 24, weight: 600, color: C.dim, spacing: 4 });
    y += 44;
    const st = stages(br);
    const gap = 8, cellGap = 3, total = br.matches.length, ch = 130;
    const avail = R - X - gap * (st.length - 1);
    let x = X;
    for (const s of st) {
      const w = (avail * s.ids.length) / total;
      ctx.fillStyle = GROUP[s.key] ?? C.accent; ctx.fillRect(x, y, w, 4);
      const cw = (w - cellGap * (s.ids.length - 1)) / s.ids.length;
      s.ids.forEach((id, i) => {
        const cx = x + i * (cw + cellGap), cy = y + 12;
        const k = states[id];
        const fill = { hit: 'rgba(110,231,160,0.14)', miss: 'rgba(255,138,92,0.14)', void: 'rgba(245,196,81,0.14)', wait: C.lineStrong, noresp: C.surface, pick: 'rgba(242,67,79,0.16)', open: C.surface, tbd: C.surface }[k];
        ctx.fillStyle = fill; ctx.fillRect(cx, cy, cw, ch);
        const sym = { hit: ['○', C.good], miss: ['×', C.bad], void: ['!', C.warn], pick: [picks[id] ? '◆' : '', C.accent] }[k];
        if (sym && sym[0]) text(ctx, sym[0], cx + cw / 2, cy + ch / 2 + 12, { font: PRE, size: Math.min(34, cw * 0.9), weight: 800, color: sym[1], align: 'center' });
      });
      text(ctx, s.key === 'GF' ? 'F' : s.label, x, y + ch + 50, { font: PRE, size: 22, weight: 600, color: C.muted });
      x += w + gap;
    }
    y += ch + 80;
  }

  // group qualifiers by my picks: one row per group
  const by = H - 230;
  if (advance.length) {
    text(ctx, '조별 진출 · 내 픽', X, y + 20, { font: PRE, size: 24, weight: 700, color: C.dim });
    y += 44;
    const rh = Math.min(58, (by - 80 - y) / advance.length);
    if (rh >= 40) {
      for (const a of advance) {
        ctx.fillStyle = C.surface; ctx.fillRect(X, y, R - X, rh - 6);
        ctx.fillStyle = GROUP[a.g] ?? C.accent; ctx.fillRect(X, y, 6, rh - 6);
        text(ctx, `${a.g}조`, X + 26, y + rh * 0.62, { font: PRE, size: 24, weight: 700, color: C.dim });
        const names = a.teams.map((t, i) => `${i + 1}. ${t ?? '—'}`);
        const cw = (R - X - 120) / Math.max(names.length, 1);
        names.forEach((n, i) => {
          ctx.font = `700 30px ${BAR}`;
          text(ctx, ellipsize(ctx, n, cw - 16), X + 110 + i * cw, y + rh * 0.66, { font: BAR, size: 30, weight: 700, color: a.teams[i] ? C.text : C.muted });
        });
        y += rh;
      }
    }
  }

  // score block
  ctx.fillStyle = C.line; ctx.fillRect(X, by - 40, R - X, 2);
  const model = data.model ?? {};
  const diff = agree?.diff ?? Object.keys(picks).filter((id) => model[id] && model[id].team !== picks[id]).length;
  if (score.n) {
    text(ctx, 'ME', X, by + 8, { font: BAR, size: 24, weight: 700, color: C.accent, spacing: 4 });
    text(ctx, `${score.me}`, X, by + 110, { font: BAR, size: 120, weight: 800 });
    ctx.font = `800 120px ${BAR}`;
    text(ctx, `/${score.n}`, X + ctx.measureText(`${score.me}`).width + 8, by + 110, { font: BAR, size: 52, weight: 800, color: C.muted });
    text(ctx, '적중', X, by + 150, { font: PRE, size: 24, weight: 500, color: C.muted });
    text(ctx, 'VS', W / 2, by + 90, { font: BAR, size: 30, weight: 600, color: C.muted, align: 'center' });
    text(ctx, 'MODEL', R, by + 8, { font: BAR, size: 24, weight: 700, color: C.dim, align: 'right', spacing: 4 });
    ctx.font = `800 52px ${BAR}`;
    const tail = `/${score.modelN}`;
    const tw = ctx.measureText(tail).width;
    text(ctx, tail, R, by + 110, { font: BAR, size: 52, weight: 800, color: C.muted, align: 'right' });
    text(ctx, `${score.model}`, R - tw - 8, by + 110, { font: BAR, size: 120, weight: 800, align: 'right' });
    text(ctx, '적중', R, by + 150, { font: PRE, size: 24, weight: 500, color: C.muted, align: 'right' });
  } else {
    text(ctx, `${score.picked}`, X, by + 110, { font: BAR, size: 120, weight: 800 });
    ctx.font = `800 120px ${BAR}`;
    text(ctx, `/ ${score.total}`, X + ctx.measureText(`${score.picked}`).width + 12, by + 110, { font: BAR, size: 52, weight: 800, color: C.muted });
    text(ctx, '픽 완료 · 결과 대기', X, by + 150, { font: PRE, size: 24, weight: 500, color: C.muted });
    text(ctx, '모델과 다른 픽', R, by + 40, { font: PRE, size: 24, weight: 500, color: C.muted, align: 'right' });
    text(ctx, `${diff}`, R, by + 110, { font: BAR, size: 72, weight: 800, color: C.accent, align: 'right' });
  }
  const src = app.model?.meta?.source_info;
  text(ctx, src ? `데이터: ${src.name}${src.license ? ` · ${src.license}` : ''}` : `데이터: ${app.model?.meta?.source ?? ''}`, X, H - 40, { font: PRE, size: 20, weight: 500, color: C.muted });
  text(ctx, 'Riot Games와 무관한 팬 프로젝트', R, H - 40, { font: PRE, size: 20, weight: 500, color: C.muted, align: 'right' });
  return cv;
}

/**
 * Render the card to a PNG file. Sharing happens in a second tap (shareFile): iOS Safari only
 * opens the share sheet right after a user gesture, and rendering (fonts, canvas) takes too long.
 * Returns {file, url} (url: object URL for the preview; revoke it when done).
 */
export async function makeCard(data) {
  const cv = await renderCard(data);
  const blob = await new Promise((res, rej) => cv.toBlob((b) => (b ? res(b) : rej(new Error('PNG 변환 실패'))), 'image/png'));
  const file = new File([blob], 'valopoint-my-bracket.png', { type: 'image/png' });
  return { file, url: URL.createObjectURL(blob) };
}

export const canShareFile = (file) => !!navigator.canShare?.({ files: [file] });

/** Open the share sheet; call directly from a click handler. */
export async function shareFile(file) {
  await navigator.share({ files: [file], title: '내 대진표 · valopoint' });
}
