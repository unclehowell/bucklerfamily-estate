
const SITES = ["bucklerfamily.estate", "www.bucklerfamily.estate", "wayback.bucklerfamily.estate", "bpvsbuckler.bucklerfamily.estate", "dartboard.bucklerfamily.estate", "email.bucklerfamily.estate", "clerk.bucklerfamily.estate", "research.bucklerfamily.estate", "fcg.bucklerfamily.estate", "records.bucklerfamily.estate", "review.bucklerfamily.estate", "authorities.bucklerfamily.estate", "2026-10-22.bucklerfamily.estate", "wiki.bucklerfamily.estate", "timeline.bucklerfamily.estate", "archives.bucklerfamily.estate", "ghf-app.bucklerfamily.estate", "qa.bucklerfamily.estate", "bucklervsbp.bucklerfamily.estate", "greathousefarmwiki.wordpress.com"];
const PAGES = ["wayback", "bpvsbuckler", "2026-10-22", "ghf-independent-review", "ghf-primary-records", "ghf-public-authorities", "bucklerfamilyfarm", "ghf-app"];
// --- Daily webapp refresh, Cloudflare half (even live "N of 59" slots). Owner ask 11 Nov 2026: every webapp refreshed daily
// from the central DB, only when its data changed; odd slots on GitHub Actions, even slots on this Worker's cron (04:35 UTC).
// For each even app in the successor .github/daily-refresh/apps.json: changed if its dedicated repo's main has a commit newer than
// the live build (/_cedwyn/reports/build.json built_at) minus margin_minutes; central-view apps
// also when data/core changed. Reads public commit feeds only (no token). The verdict is kept in KV and served at
// /daily-refresh.json; the GitHub half (webapps-daily-odd.yml, 05:25 UTC) reads it and runs at most ONE site build. — Sion's Tab agent
const DR_CRON = '35 4 * * *';
const DR_APPS = 'https://raw.githubusercontent.com/unclehowell/bucklerfamily-estate/main/.github/daily-refresh/apps.json';
const DR_BUILD = 'https://cedwyn.bucklerfamily.estate/_cedwyn/reports/build.json';
async function feedLatest(repo, ref, path) {
  const u = `https://github.com/${repo}/commits/${ref}${path ? '/' + path : ''}.atom`;
  try {
    const r = await fetch(u, { headers: { 'user-agent': 'cedwyn-daily-refresh/1.0', accept: 'application/atom+xml' }, cf: { cacheTtl: 0 } });
    if (!r.ok) return { err: `${u.slice(19)} ${r.status}` };
    const t = await r.text(); const d = [...t.matchAll(/<updated>([^<]+)<\/updated>/g)].map(m => m[1]);
    const id = (t.match(/Commit\/([0-9a-f]{7})/) || [])[1] || '';
    return d.length > 1 ? { at: d[1], sha: id } : { err: `${u.slice(19)} no entries` };
  } catch (e) { return { err: String(e).slice(0, 120) }; }
}
async function runEven(env) {
  const out = { schema: 'cedwyn-daily-refresh-even/1.0', checked_at: new Date().toISOString(), lane: 'cloudflare', changed: [], checked: 0, errors: [] };
  try {
    const cfg = await (await fetch(DR_APPS + '?cb=' + Date.now(), { cf: { cacheTtl: 0 } })).json();
    const stamp = await (await fetch(DR_BUILD + '?cb=' + Date.now(), { cf: { cacheTtl: 0 } })).json().catch(() => ({}));
    out.live_build = stamp;
    const built = Date.parse(stamp.built_at || '') || Date.now();
    const cut = built - (cfg.margin_minutes || 45) * 60e3;
    const core = await feedLatest('unclehowell/bucklerfamily-estate', 'main', 'data/core');
    out.central_core_last_commit = core.at || null;
    const coreChanged = !!core.at && Date.parse(core.at) > cut;
    const apps = (cfg.apps || []).filter(a => a.lane === 'cloudflare');
    const keyOf = a => [a.repo, 'main'];
    const keys = [...new Map(apps.map(a => [keyOf(a).join('@'), keyOf(a)])).values()];
    const seen = {};
    for (let i = 0; i < keys.length; i += 6) {
      const part = keys.slice(i, i + 6);
      const res = await Promise.all(part.map(([r, b]) => feedLatest(r, b)));
      part.forEach(([r, b], j) => { seen[r + '@' + b] = res[j]; });
    }
    out.checked = keys.length;
    for (const a of apps) {
      const [r, b] = keyOf(a); const s = seen[r + '@' + b] || {};
      if (s.err) { out.errors.push(`${a.app}: ${s.err}`); continue; }
      const why = [];
      if (Date.parse(s.at) > cut) why.push(`${r}@${b} ${s.sha} at ${s.at}`);
      if (a.central_view && coreChanged) why.push(`central catalogue data/core changed at ${core.at}`);
      if (why.length) out.changed.push({ slot: a.slot || a.nav_no, app: a.app, repo: a.repo, mode: a.mode, why });
    }
  } catch (e) { out.errors.push(String(e).slice(0, 200)); }
  await env.GHF_STATUS.put('daily-refresh', JSON.stringify(out));
  return out;
}
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function probe(host) {
  const t0 = Date.now();
  try {
    const r = await fetch('https://' + host + '/', { method: 'GET', redirect: 'manual', cf: { cacheTtl: 0 } , headers: {'user-agent':'ghf-status-check'} });
    return { host, status: r.status, ms: Date.now() - t0, location: r.headers.get('location') || null };
  } catch (e) { return { host, status: 0, ms: Date.now() - t0, error: String(e).slice(0, 120) }; }
}
async function runChecks(env) {
  const results = await Promise.all(SITES.map(probe));
  const doc = { checked_at: new Date().toISOString(), results };
  await env.GHF_STATUS.put('checks', JSON.stringify(doc));
  return doc;
}
function page(checks, snap, keeper) {
  const ok = s => s >= 200 && s < 400;
  const rows = (checks?.results || []).map(r => `<tr><td><a href="https://${esc(r.host)}/">${esc(r.host)}</a></td><td class="${ok(r.status)?'ok':'bad'}">${r.status || 'down'}</td><td>${r.ms} ms</td></tr>`).join('');
  const up = (checks?.results || []).filter(r => ok(r.status)).length, n = (checks?.results || []).length;
  const snapRows = snap ? Object.entries(snap.counts || {}).map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join('') : '';
  const keepRows = keeper ? (keeper.projects || []).map(p => `<tr><td>${esc(p.project)}</td><td>${esc(p.branch)}</td><td>${esc((p.deployed||'').slice(0,7))}</td><td>${esc((p.head||'').slice(0,7))}</td><td class="${p.fresh?'ok':'bad'}">${p.fresh?'fresh':esc(p.action||'stale')}</td></tr>`).join('') : '';
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Great House Farm — flywheel status</title><style>
body{font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif;max-width:860px;margin:2rem auto;padding:0 1rem;color:#1d2a1f;background:#f7f5ef}
h1{font-size:1.5rem;margin:.2rem 0}h2{font-size:1.1rem;margin-top:1.8rem;border-bottom:1px solid #cfc8b6;padding-bottom:.2rem}
table{border-collapse:collapse;width:100%}td,th{padding:.3rem .5rem;border-bottom:1px solid #e3ddcc;text-align:left}
.ok{color:#1e7a32;font-weight:600}.bad{color:#b3261e;font-weight:600}.muted{color:#6b6b5e;font-size:.85rem}a{color:#2c5d3a}
</style></head><body>
<p class="muted">Great House Farm (Tŷ Mawr), Llandough</p>
<h1>Flywheel status</h1>
<p>Sites up: <b>${up} / ${n}</b> · checked ${esc(checks?.checked_at || 'not yet')}</p>
<h2>Project flywheel</h2>
${snap ? `<table>${snapRows}</table><p class="muted">Snapshot updated ${esc(snap.updated_at)}. ${esc(snap.note || '')}</p>` : '<p class="muted">No snapshot yet.</p>'}
<h2>Deploy freshness (Cloudflare Pages vs GitHub branch head)</h2>
${keeper ? `<table><tr><th>Project</th><th>Branch</th><th>Deployed</th><th>Head</th><th></th></tr>${keepRows}</table><p class="muted">Keeper run ${esc(keeper.checked_at)}</p>` : '<p class="muted">No keeper run recorded yet.</p>'}
<h2>Sites</h2><table><tr><th>Site</th><th>HTTP</th><th>Time</th></tr>${rows}</table>
<p class="muted">Primary record: <a href="https://greathousefarmwiki.wordpress.com/">greathousefarmwiki.wordpress.com</a>. JSON: <a href="/status.json">/status.json</a></p>
</body></html>`;
}

// Weekly public-interest digest: published feed only; excludes technical work logs and private correspondence.
const DGS='https://bucklerfamily.estate',DGF='https://bucklerfamily.estate/blog/feed.json';
function dgy(d){const p=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/London',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(d),g=k=>p.find(x=>x.type===k).value;return g('year')+'-'+g('month')+'-'+g('day');}
function dga(s,n){const d=new Date(s+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+n);return d.toISOString().slice(0,10);}
function dgm(s){const d=new Date(s+'T12:00:00Z');d.setUTCDate(d.getUTCDate()-((d.getUTCDay()+6)%7));return d.toISOString().slice(0,10);}
function dgfmt(s){return new Date(s+'T12:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'});}
function dgu(s){try{const u=new URL(s);return ['bucklerfamily.estate','cedwyn.bucklerfamily.estate'].includes(u.hostname)?DGS+u.pathname:'';}catch(e){return '';}}
const dge=s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const DGNAV="<nav class=\"cw-slotnav\" data-cw-nav=\"1.3.0\" data-cw-slot=\"36\" aria-label=\"All webapps\"><style>.cw-slotnav{display:flex;flex-wrap:wrap;align-items:center;gap:2px 6px;margin:0;padding:4px 8px;background:#000;color:#fff;font:14px/1.3 Barlow,'Helvetica Neue',Arial,sans-serif;box-sizing:border-box;max-width:100%;overflow:hidden}.cw-slotnav a{color:#fff;text-decoration:none}.cw-slotnav .cw-sn-arr{flex:0 0 40px;font-size:30px;line-height:40px;text-align:center}.cw-slotnav .cw-sn-name{flex:1 1 0;min-width:0;text-align:center;overflow-wrap:anywhere;text-transform:uppercase;letter-spacing:.06em}.cw-slotnav small{display:block;color:#0F9DF0;letter-spacing:.12em;font-size:11px}.cw-slotnav details{flex:1 0 100%;min-width:0}.cw-slotnav summary{cursor:pointer;font-size:12px;color:#ccc;padding:2px 0}.cw-slotnav ol{margin:4px 0 6px 2.2em;padding:0;font-size:13px}.cw-slotnav li{margin:3px 0}.cw-slotnav [aria-current]{font-weight:700;color:#0F9DF0}html.ghf-v2-pre .cw-slotnav,html.ghf-v2-on .cw-slotnav{display:none!important}</style><a class=\"cw-sn-arr\" href=\"/online/whattheydontsay/\" rel=\"prev\" aria-label=\"Previous webapp: What They Don&#x27;t Say\" title=\"Previous webapp: What They Don&#x27;t Say\">&#8249;</a><span class=\"cw-sn-name\"><b>Blog</b><small>36 of 59</small></span><a class=\"cw-sn-arr\" href=\"/online/hubspot/\" rel=\"next\" aria-label=\"Next webapp: HubSpot \u00b7 Task Control\" title=\"Next webapp: HubSpot \u00b7 Task Control\">&#8250;</a><details><summary>All webapps (59)</summary><ol><li value=\"1\"><a href=\"/wiki/\">Legal Wiki &amp; Evidence</a></li><li value=\"2\"><a href=\"/docs/\">Docs \u00b7 Evidence Catalogue</a></li><li value=\"3\"><a href=\"/wayback/\">Wayback Vault</a></li><li value=\"4\"><a href=\"/maps/\">Map Room</a></li><li value=\"5\"><a href=\"/infographic/\">The Land Changing Hands</a></li><li value=\"6\"><a href=\"/ebooks/\">E-book Shelf</a></li><li value=\"7\"><a href=\"/story/\">The Story &amp; Documentary</a></li><li value=\"8\"><a href=\"/thousand-cuts/\">1000 Cuts</a></li><li value=\"9\"><a href=\"/fb/\">Farm Album</a></li><li value=\"10\"><a href=\"/arcade/\">Arcade</a></li><li value=\"11\"><a href=\"/chess/\">Chessboard</a></li><li value=\"12\"><a href=\"/csscpsg/\">Grammar House</a></li><li value=\"13\"><a href=\"/courtdrills/\">Court Drills</a></li><li value=\"14\"><a href=\"/online/fcg/\">FCG \u00b7 Fraud, Concealment and Government involvement</a></li><li value=\"15\"><a href=\"/oldbill/\">Old Bill \u00b7 Who Gained, Who Lost</a></li><li value=\"16\"><a href=\"/accounts/\">Counting House</a></li><li value=\"17\"><a href=\"/online/authorities/\">Public Authorities &amp; Council Chamber</a></li><li value=\"18\"><a href=\"/online/wdtk/\">FOI Requests</a></li><li value=\"19\"><a href=\"/online/review/\">Independent Review</a></li><li value=\"20\"><a href=\"/research/\">Research Library</a></li><li value=\"21\"><a href=\"/online/qa/\">Q&amp;A Hall</a></li><li value=\"22\"><a href=\"/online/projects/\">Project Office</a></li><li value=\"23\"><a href=\"/app/\">Case Office</a></li><li value=\"24\"><a href=\"/online/chat/\">Ask the Archive</a></li><li value=\"25\"><a href=\"/online/watchtower/\">Watchtower</a></li><li value=\"26\"><a href=\"/online/email/\">Post Office &amp; Calendar</a></li><li value=\"27\"><a href=\"/online/dartboard/\">Disclosure Dartboard</a></li><li value=\"28\"><a href=\"/estate/\">Cedwyn Estate</a></li><li value=\"29\"><a href=\"/directory/\">Cedwyn Directory</a></li><li value=\"30\"><a href=\"/patagonia/\">Great House Farm II \u00b7 Patagonia</a></li><li value=\"31\"><a href=\"/wales/\">Virtual Tour \u00b7 Wales</a></li><li value=\"32\"><a href=\"/shop/\">Gift Shop &amp; Marketplace</a></li><li value=\"33\"><a href=\"/familytree/\">Family Tree</a></li><li value=\"34\"><a href=\"/kissed-frogs/\">Kissed Frogs</a></li><li value=\"35\"><a href=\"/online/whattheydontsay/\">What They Don&#x27;t Say</a></li><li value=\"36\"><a href=\"/blog/\" aria-current=\"page\">Blog</a></li><li value=\"37\"><a href=\"/online/hubspot/\">HubSpot \u00b7 Task Control</a></li><li value=\"38\"><a href=\"/online/that-old-chestnut/\">That Old Chestnut</a></li><li value=\"39\"><a href=\"/online/forensic/\">Forensic Assessments</a></li><li value=\"40\"><a href=\"/mr-wolf/\">Mr Wolf</a></li><li value=\"41\"><a href=\"/releases/\">The Release Machine</a></li><li value=\"42\"><a href=\"/tithe-h3/\">Tithe H3</a></li><li value=\"43\"><a href=\"/online/cloudflare/\">Cloudflare</a></li><li value=\"44\"><a href=\"/spill/\">Spill</a></li><li value=\"45\"><a href=\"/analytics/\">Analytics</a></li><li value=\"46\"><a href=\"/chubut-h3/\">Chubut H3</a></li><li value=\"47\"><a href=\"/garden/\">Flower Garden</a></li><li value=\"48\"><a href=\"/documentary/\">Cedwyn \u00b7 documentary</a></li><li value=\"49\"><a href=\"/nomenclature/\">Nomenclature</a></li><li value=\"50\"><a href=\"/records/\">Primary Records</a></li><li value=\"51\"><a href=\"/fb2/\">farmbook 2 \u00b7 Today</a></li><li value=\"52\"><a href=\"/nft-art/\">The Garden Gallery</a></li><li value=\"53\"><a href=\"/online/cyberspace/\">The Digital Estate</a></li><li value=\"54\"><a href=\"/meeting/\">The Council Chamber</a></li><li value=\"55\"><a href=\"/online/emails/\">The Post Office \u00b7 Calendar</a></li><li value=\"56\"><a href=\"/preservation/\">Preservation Register</a></li><li value=\"57\"><a href=\"/language-forensics/\">Language Forensics</a></li><li value=\"58\"><a href=\"/piano-hero/\">Piano Hero</a></li><li value=\"59\"><a href=\"/uptime/\">Uptime</a></li></ol></details></nav><!--/cw-slotnav-->";
// Browser edition: the Blog's own article pattern (runtime theme "blog", /blog/blog.css, header "BLOG 36 OF 59"). The header finds its area by path, and /subscribe/digest/ matches none, so the page names its parent path (window.__cedwynLP) for that lookup. The email HTML is built separately and is unchanged.
function dgblog(xs,start,end,intro){let b='';for(const c of ['FOI & public records','Records searches & provenance','Research & heritage','New visitor features']){const a=xs.filter(x=>x.cat===c);if(!a.length)continue;b+='<h2>'+dge(c)+'</h2>';for(const x of a)b+='<div class="bl-it"><h3>'+dge(x.t)+'</h3><p>'+dge(x.s)+'</p>'+(x.src?'<p class="bl-src">Source: '+dge(x.src)+'</p>':'')+((x.u||x.a)?'<p>'+(x.u?'<a href="'+dge(x.u)+'">Read update</a>':'')+(x.u&&x.a?' · ':'')+(x.a?'<a href="'+dge(x.a)+'">Open new feature</a>':'')+'</p>':'')+'</div>';}
return '<!doctype html><html lang="en-GB" data-cw-nolevels><head><script src="/_cedwyn/runtime.js?v=18" data-theme="blog"></script><script>window.__cedwynLP="/blog/digest/";</script><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/blog/blog.css"><meta name="robots" content="noindex"><title>Great House Farm weekly update \u00b7 Cedwyn</title><style>.bl-dg h2{font-size:1.25rem;margin:1.6em 0 .4em;letter-spacing:.02em}.bl-dg h3{font-size:1.1rem;margin:1.2em 0 .3em;line-height:1.3}.bl-dg .bl-src{opacity:.75;font-size:.85rem;line-height:1.5}.bl-dg .bl-it{border-top:1px solid #8884;padding-top:.2em}.bl-dg .bl-foot{margin-top:2em;opacity:.85;font-size:.9rem}.bl-dg .bl-kick{letter-spacing:.14em;text-transform:uppercase;font-size:.8rem;opacity:.7;margin:0}</style></head><body>'+DGNAV+'<main class="bl-wrap bl-dg" id="blog-main" data-cw-nolevels data-cw-noclamp><article class="bl-post" data-cw-nolevels><p class="bl-kick">Weekly field notes</p><p class="bl-date"><time datetime="'+dge(end)+'">'+dge(dgfmt(start))+' to '+dge(dgfmt(end))+'</time></p><h1>Great House Farm &amp; T\u0177 Mawr: weekly update</h1><p class="bl-sum">'+dge(intro)+'</p>'+b+'<p class="bl-foot">Items are reviewed public-case summaries. Raw private correspondence and internal technical logs are not included.</p><p class="bl-foot"><a href="'+DGS+'/blog/">Project blog</a> \u00b7 <a href="'+DGS+'/subscribe/?topic=digest">Subscribe to the weekly digest</a></p></article></main><script src="/_cedwyn/ghf/ghf-boot.js?v=2.1.30"></script></body></html>';}
async function dgmake(env,send,opt){opt=opt||{};const only=Array.isArray(opt.emails)?opt.emails.map(x=>String(x).trim().toLowerCase()).filter(x=>/^[^@\s]+@[^@\s]+$/.test(x)).slice(0,10):[],ow=only.length?' AND lower(email) IN ('+only.map(()=>'?').join(',')+')':'';
 const mon=dgm(dgy(new Date())),start=dga(mon,-7),end=dga(mon,-1),archive=DGS+'/subscribe/digest/'+start+'/',key='weekly-digest:'+start;
 const corr=/^r\d{1,2}$/.test(opt.corr||'')?opt.corr:'',id='wd-'+start.replace(/-/g,'')+(corr?'-'+corr:'');
 // send gate: a week is "made" only when its broadcast fully drained (settle() marks it done). An archived page or a
 // failed/partial send never suppresses a later scheduled run. Preview (send=false) is read-only for send state.
 if(send){const done=await env.DB.prepare("SELECT id FROM cl_broadcasts WHERE id=? AND status='done'").bind(id).first();if(done)return {ok:true,skip:'already sent',archive};}
 const r=await fetch(DGF+'?d='+Date.now(),{cf:{cacheTtl:0}});if(!r.ok)throw new Error('feed '+r.status);
 const f=await r.json(),xs=(f.items||[]).filter(p=>{const t=p.title||'',z=(p.tags||[]).join(' '),v=t+' '+z+' '+(p.summary||''),d=p.date_published||p.date_modified;return d&&dgy(new Date(d))>=start&&dgy(new Date(d))<=end&&!/work[\s-]?log|agent work|chatgpt work|instinct work|deployment|developer notes|infrastructure|code change|technical log/i.test(t+' '+z)&&/FOI|EIR|freedom of information|environmental information|correspondence|not held|disclosure|public authority|Great House|Tŷ Mawr|Ty Mawr|Llandough|Leckwith|heritage|history|woodland|farm|archaeolog|estate|museum|building|construction|engineering|archive|tithe|parish/i.test(v);}).map(p=>{const t=p.title||'Project update',v=t+' '+(p.summary||''),feature=/new feature|new interactive|new webapp|feature added|now available|new map|new tour/i.test(v);return {t,s:(p.summary||'New public project update').slice(0,420),u:dgu(p.url),a:feature?dgu(p.external_url):'',day:dgy(new Date(p.date_published||p.date_modified)),cat:/FOI|EIR|freedom of information|environmental information|correspondence|not held|disclosure/i.test(v)?'FOI & public records':feature?'New visitor features':'Research & heritage'};}).filter(x=>x.u);
 // second source: reviewed public-ready items for the week (KV key digest-extra:<week start>, a JSON array of {t,s,u,cat,day}); estate links or whatdotheyknow.com/request links only, no private content
 try{const ex=JSON.parse(await env.GHF_STATUS.get('digest-extra:'+start)||'[]');if(Array.isArray(ex))for(const e of ex.slice(0,30)){let u=dgu(e&&e.u);if(!u)try{const q=new URL(e&&e.u);if(q.protocol==='https:'&&q.hostname==='www.whatdotheyknow.com'&&q.pathname.startsWith('/request/'))u=q.origin+q.pathname+q.hash;}catch(_){}if((u||(e&&e.src))&&e.t&&['FOI & public records','Records searches & provenance','Research & heritage','New visitor features'].includes(e.cat))xs.push({t:String(e.t).slice(0,200),s:String(e.s||'').slice(0,900),u,src:String((e&&e.src)||'').slice(0,240),a:'',day:String(e.day||'').slice(0,10),cat:e.cat});}}catch(e){}
 const hasExtras=!!(await env.GHF_STATUS.get('digest-extra:'+start)),finalized=!!(await env.GHF_STATUS.get('digest-final:'+start));
 if(send&&!corr&&!finalized){await env.GHF_STATUS.put('weekly-digest:held',JSON.stringify({week:start,at:new Date().toISOString(),reason:'week not marked final (digest-final) - coverage not confirmed'}));return {ok:false,status:'held-not-final',start,end,items:xs.length,recipients:0,archive};}
 // empty-week guard: never archive or send a "nothing happened" edition; hold and flag it instead
 if(!xs.length){if(send){await env.GHF_STATUS.put('weekly-digest:held',JSON.stringify({week:start,at:new Date().toISOString(),reason:'no items from feed or reviewed extras'}));}if(!send)return {ok:false,status:'held-empty',start,end,items:0,recipients:0,archive};return {ok:false,status:'held-empty',start,end,items:0,recipients:0,archive};}
 let rows='';for(const c of ['FOI & public records','Records searches & provenance','Research & heritage','New visitor features']){const a=xs.filter(x=>x.cat===c);if(a.length){rows+='<tr><td style="padding:20px 25px 5px;font:700 18px Georgia;color:#183b2e">'+c+'</td></tr>';for(const x of a)rows+='<tr><td style="padding:12px 25px;border-bottom:1px solid #e7e2d6"><b style="font:17px Georgia">'+dge(x.t)+'</b><p style="font:14px/1.6 Arial">'+dge(x.s)+'</p>'+(x.src?'<p style="font:12px/1.5 Arial;color:#666">Source: '+dge(x.src)+'</p>':'')+(x.u?'<a href="'+dge(x.u)+'" style="color:#286347">Read update</a>':'')+(x.a?' · <a href="'+dge(x.a)+'" style="color:#286347">Open new feature</a>':'')+'</td></tr>';}}
 if(!rows)rows='<tr><td style="padding:24px">No new public updates met the digest criteria this week.</td></tr>';
 const intro='A plain-English round-up of FOI and public-record updates, heritage research and non-technical project progress.';
 const html='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Great House Farm weekly update</title><body style="margin:0;background:#f2f0e8;padding:24px 8px"><table width="100%"><tr><td align="center"><table width="100%" style="max-width:680px;background:#fff;border:1px solid #e3ddcf;border-radius:12px" cellpadding="0" cellspacing="0"><tr><td style="padding:30px 25px;background:#183b2e;border-bottom:5px solid #b99a5d;color:white"><small style="letter-spacing:2px;color:#d9c79e">WEEKLY FIELD NOTES</small><h1 style="font:normal 30px Georgia">Great House Farm &amp; Tŷ Mawr</h1><p>Public records · heritage · project progress</p><small>'+dgfmt(start)+' to '+dgfmt(end)+'</small></td></tr><tr><td style="padding:20px 25px;font:15px/1.6 Arial">'+intro+'</td></tr>'+rows+'<tr><td style="padding:20px 25px;background:#f7f5ef;font:13px/1.6 Arial"><a style="color:#286347" href="'+archive+'">Open this email in your browser</a><br>Items are reviewed public-case summaries. Raw private correspondence and internal technical logs are not included.<br><a style="color:#286347" href="'+DGS+'/blog/">Project blog</a> · <a style="color:#286347" href="'+DGS+'/subscribe/?topic=digest">Subscribe</a></td></tr></table></td></tr></table></body></html>';
 const plain='Great House Farm & Tŷ Mawr weekly update\n'+dgfmt(start)+' to '+dgfmt(end)+'\n\nOpen in browser: '+archive+'\n\n'+'Items are reviewed public-case summaries. Raw private correspondence and internal technical logs are not included.\n\n'+xs.map(x=>x.cat+'\n'+x.t+'\n'+x.s+'\n'+(x.src?'Source: '+x.src+'\n':'')+x.u+(x.a?'\nNew feature: '+x.a:'')).join('\n\n');
 const browserHtml=dgblog(xs,start,end,intro);
 if(!send){return {ok:true,start,end,items:xs.length,recipients:0,status:'preview',archive,previewHtml:browserHtml};}
if(send&&!corr){let hl=[];try{hl=JSON.parse(await env.GHF_STATUS.get('digest-hold-addresses')||'[]').map(x=>String(x).toLowerCase());}catch(_){}if(hl.length){const el=((await env.DB.prepare("SELECT lower(email) e FROM cl_subscribers WHERE status='confirmed' AND test=0 AND (','||topics||',') LIKE '%,digest,%'").bind().all()).results||[]).map(r=>r.e);if(el.some(e=>hl.includes(e))){await env.GHF_STATUS.put('weekly-digest:held',JSON.stringify({week:start,at:new Date().toISOString(),reason:'an address on the hold list is eligible for the full-list send; owner decision needed'}));return {ok:false,status:'held-recipient-hold',start,end,items:xs.length,recipients:0,archive};}}}
 await env.GHF_STATUS.put(key,browserHtml);await env.GHF_STATUS.put('weekly-digest:latest',start);
 let n=0,status='archived';if((corr||opt.manual)&&!only.length)throw new Error('corrected send needs explicit recipients');const q=await env.DB.prepare("SELECT COUNT(*) n FROM cl_subscribers WHERE status='confirmed' AND test=0 AND (','||topics||',') LIKE '%,digest,%'"+ow).bind(...only).first();n=Number(q&&q.n||0);if(n){const subject=(corr?'Corrected: ':'')+'Great House Farm weekly update - week ending '+dgfmt(end),old=await env.DB.prepare('SELECT id FROM cl_broadcasts WHERE id=?').bind(id).first();if(corr&&old){const ex=((await env.DB.prepare('SELECT email FROM cl_outbox WHERE broadcast_id=?').bind(id).all()).results||[]).map(r=>String(r.email).toLowerCase());if(ex.length&&only.some(e=>!ex.includes(e)))throw new Error('recipient set differs from the original correction send');}const stB=env.DB.prepare("INSERT OR IGNORE INTO cl_broadcasts (id,msgid,created_at,sender,subject,body,total,sent,failed,status,test) VALUES (?,?,?,?,?,?,?,0,0,'sending',0)").bind(id,'<'+id+'@bucklerfamily.estate>',new Date().toISOString(),'weekly-digest',subject,JSON.stringify({html,text:plain,att:[]}),n),stO=env.DB.prepare("INSERT OR IGNORE INTO cl_outbox (broadcast_id,email) SELECT ?,email FROM cl_subscribers WHERE status='confirmed' AND test=0 AND (','||topics||',') LIKE '%,digest,%'"+ow).bind(id,...only);if(typeof env.DB.batch==='function')await env.DB.batch([stB,stO]);else{await stB.run();await stO.run();}/* atomic when batch exists; outbox insert is idempotent (UNIQUE broadcast_id,email) and runs on every attempt, so a retry repairs a missing outbox without duplicating delivery */const x=await fetch('https://bucklerfamily.estate/api/list/digest-drain',{method:'POST',headers:{'x-digest-drain-key':env.DIGEST_DRAIN_KEY||''}});if(!x.ok)throw new Error('mailer '+x.status);status='queued';const bc=await env.DB.prepare('SELECT status,sent,failed,total FROM cl_broadcasts WHERE id=?').bind(id).first();if(bc){status=bc.status==='done'?'sent':'queued';if(bc.status==='done'&&Number(bc.failed)===0){await env.GHF_STATUS.delete('weekly-digest:held');await env.GHF_STATUS.delete('weekly-digest:last-error');}else await env.GHF_STATUS.put('weekly-digest:last-error','pending or partial send, week '+start+', sent '+bc.sent+' failed '+bc.failed+' of '+bc.total);return {ok:true,start,end,items:xs.length,recipients:n,status,sent:bc.sent,failed:bc.failed,total:bc.total,id,archive};}}
 return {ok:true,start,end,items:xs.length,recipients:n,status,archive};
}
async function dgpage(env,u){const m=u.pathname.match(/\/subscribe\/digest\/(\d{4}-\d{2}-\d{2})\/?$/),w=m?m[1]:await env.GHF_STATUS.get('weekly-digest:latest'),h=w?await env.GHF_STATUS.get('weekly-digest:'+w):null;return new Response(h||'<!doctype html><meta name="viewport" content="width=device-width"><main style="max-width:680px;margin:8vh auto;padding:24px;font:16px/1.6 Arial;background:#fff"><h1>Great House Farm &amp; Tŷ Mawr</h1><p>The weekly public-interest digest will appear here.</p><a href="/subscribe/?topic=digest">Subscribe</a></main>',{headers:{'content-type':'text/html; charset=utf-8'}});}
async function dgtick(env){const p=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/London',weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date()),v=k=>(p.find(x=>x.type===k)||{}).value;if(v('weekday')==='Mon'&&['09','10','11'].includes(v('hour')))try{const r=await dgmake(env,true);if(r&&r.ok===false)await env.GHF_STATUS.put('weekly-digest:last-error','held: '+r.status+' week '+r.start);}catch(e){await env.GHF_STATUS.put('weekly-digest:last-error',String(e).slice(0,300));}}
// End weekly digest.

const j = s => { let v = null; try { v = JSON.parse(s || 'null'); if (typeof v === 'string') v = JSON.parse(v); } catch (e) {} return v; };
export default {
  async fetch(req, env, ctx) {
    const u = new URL(req.url);
    if (u.pathname === '/subscribe/digest/preview/') { try { const r=await dgmake(env,false); return new Response(r.previewHtml||'Held: no items for this week yet.',{status:r.previewHtml?200:503,headers:{'content-type':'text/html; charset=utf-8','cache-control':'no-store'}}); } catch(e) { return new Response('Preview unavailable: '+String(e).slice(0,180),{status:503}); } }
    if (u.pathname.startsWith('/subscribe/digest')) return await dgpage(env,u);
    if (u.pathname === '/__weekly-digest-resend' && req.method === 'POST') { if (!env.DIGEST_DRAIN_KEY || req.headers.get('x-weekly-digest-key') !== env.DIGEST_DRAIN_KEY) return new Response('forbidden',{status:403}); try { const raw=((await req.json().catch(()=>({}))).emails),ok=Array.isArray(raw)&&raw.length>0&&raw.length<=10&&raw.every(x=>typeof x==='string'&&/^[^@\s]+@[^@\s]+$/.test(x.trim()));const cp=u.searchParams.get('corr')||'';if(!ok||!/^r\d{1,2}$/.test(cp))return Response.json({error:'correction id (corr=rN) and explicit valid recipients required'},{status:400});return Response.json(await dgmake(env,true,{corr:u.searchParams.get('corr')||'',emails:raw,manual:true})); } catch(e) { return Response.json({error:String(e).slice(0,200)},{status:500}); } }
    if (u.pathname === '/__weekly-digest-preview' && req.method === 'POST') { if (!env.DIGEST_DRAIN_KEY || req.headers.get('x-weekly-digest-key') !== env.DIGEST_DRAIN_KEY) return new Response('forbidden',{status:403}); try { return Response.json(await dgmake(env,false)); } catch(e) { return Response.json({error:String(e)},{status:500}); } }
    let checks = j(await env.GHF_STATUS.get('checks'));
    if (!checks || (Date.now() - Date.parse(checks.checked_at)) > 3 * 3600e3) checks = await runChecks(env);
    const snap = j(await env.GHF_STATUS.get('snapshot'));
    const keeper = j(await env.GHF_STATUS.get('keeper'));
    if (u.pathname === '/daily-refresh.json') {
      let dr = j(await env.GHF_STATUS.get('daily-refresh'));
      if (u.searchParams.get('run') === '1' && (!dr || (Date.now() - Date.parse(dr.checked_at)) > 6 * 3600e3)) dr = await runEven(env);
      return new Response(JSON.stringify(dr || { note: 'no daily refresh check yet' }, null, 1), { headers: { 'content-type': 'application/json', 'cache-control': 'no-store', 'access-control-allow-origin': '*' } });
    }
    if (u.pathname === '/status.json') return new Response(JSON.stringify({ checks, snapshot: snap, keeper }, null, 1), { headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=120', 'access-control-allow-origin': '*' } });
    if (u.pathname !== '/') return new Response('Not found', { status: 404 });
    return new Response(page(checks, snap, keeper), { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=120' } });
  },
  async scheduled(event, env, ctx) { ctx.waitUntil(event.cron === DR_CRON ? runEven(env) : runChecks(env)); if (event.cron !== DR_CRON) ctx.waitUntil(dgtick(env)); }
};
