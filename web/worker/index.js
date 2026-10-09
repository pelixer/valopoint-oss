// valopoint Worker: serves the built app (static assets) and runs the hourly results check.
// Cron (wrangler.jsonc "triggers"): reads the published bracket and, when a started match has no
// result yet (or at the 6-hourly refresh), dispatches the GitHub "update-data" workflow, which
// imports from Liquipedia, rebuilds the bracket and model, commits and redeploys.
// Needs the Worker secret GH_DISPATCH_TOKEN: a fine-grained GitHub token for pelixer/valopoint
// with "Actions: Read and write". Without it the cron only logs.
import { regularHour, resultsDue } from './due.js';

const REPO = 'pelixer/valopoint';
const WORKFLOW = 'update-data.yml';

export default {
  fetch(request, env) {
    return env.ASSETS.fetch(request);
  },

  async scheduled(event, env) {
    const now = event.scheduledTime;
    let brackets = [];
    try {
      const res = await env.ASSETS.fetch(new Request('https://assets.local/data/brackets.json'));
      if (res.ok) brackets = (await res.json()).brackets ?? [];
    } catch (e) {
      console.log('brackets.json unreadable', String(e));
    }
    const due = resultsDue(brackets, now);
    const regular = regularHour(now);
    if (!due.length && !regular) {
      console.log('no results due');
      return;
    }
    console.log(due.length ? `results due: ${due.join(', ')}` : '6-hourly refresh');
    if (!env.GH_DISPATCH_TOKEN) {
      console.log('GH_DISPATCH_TOKEN not set; not dispatching');
      return;
    }
    const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.GH_DISPATCH_TOKEN}`, Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'valopoint-cron',
      },
      body: JSON.stringify({ ref: 'main' }),
    });
    console.log(`dispatch ${WORKFLOW}: HTTP ${r.status}${r.ok ? '' : ` ${(await r.text()).slice(0, 300)}`}`);
  },
};
