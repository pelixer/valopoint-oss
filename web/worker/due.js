// When should the data job ask Liquipedia for results? (mirrors valopoint/brackets.py results_due)
// A match is due when it started at least `afterMin` minutes ago (a Bo3 ending 2:0 takes about
// that long), within the last `maxAgeH` hours, and the published bracket has no result for it.
export function resultsDue(brackets, now, afterMin = 75, maxAgeH = 48) {
  const out = [];
  for (const br of brackets ?? []) {
    for (const m of br.matches ?? []) {
      if (!m.time || br.results?.[m.id]) continue;
      const t = Date.parse(m.time);
      if (t <= now - afterMin * 60e3 && t >= now - maxAgeH * 3600e3) out.push(`${br.name}: ${m.id}`);
    }
  }
  return out;
}

// Regular refresh even without due matches: every 6 hours (00, 06, 12, 18 UTC).
export const regularHour = (now) => new Date(now).getUTCHours() % 6 === 0;
