// agent-ready — the agent layer for every Great House Farm site (bucklerfamily.estate).
// Serves robots.txt, sitemap.xml (when the site has none), llms.txt (+ an agent section appended to a curated one),
// llms-full.txt, /.well-known/mcp.json, /agent/* (read-only JSON tools) and /agent/webmcp.js (navigator.modelContext tools).
// On the homepage of the sites routed here it adds JSON-LD (WebSite + Organization) where missing, an llms.txt link,
// the WebMCP script where the site loads no shared header, and a <noscript> summary where the page has little text without JS.
// Anything it does not own, or any error, passes straight through to the site. Source: work/agent-ready (build.py). Sion's Tab agent.
import REGTXT from "./registry.txt";
import { withFooter, llmsSection } from "./footer.js";
const REG = JSON.parse(REGTXT);
import WEBMCP from "./webmcp.txt";

const FROZEN = /^2026-10-22\./;
// Webb–Rich Family Archive (Over Stowey, Somerset) is its own archive: its own values, no Great House Farm estate links (24 Oct 2026).
const WB = (h) => /(^|\.)webbrich\.bucklerfamily\.estate$/.test(h);
const VER = REG._version;
const J = (o, s = 200, extra = {}) => new Response(JSON.stringify(o, null, 1), { status: s, headers: { "content-type": "application/json; charset=utf-8", "access-control-allow-origin": "*", "cache-control": "public, max-age=900", "x-agent-ready": VER, ...extra } });
const T = (t, ct = "text/plain; charset=utf-8", s = 200) => new Response(t, { status: s, headers: { "content-type": ct, "access-control-allow-origin": "*", "cache-control": "public, max-age=900", "x-agent-ready": VER } });
const HEDGE = /(?:[Cc]ase theories on these sites are )?(?:[Tt]his is )?[Oo]ur case,? (?:prospective(?: only)?|not a finding of any court)[.;,]?|[Nn]ot a finding of any court\.?|(?:[Tt]emplate prepared by Sion's Tab agent;\s*)?[Nn]ot legal advice(?:; review by a qualified solicitor\/attorney recommended)?[.;,]?/g;
const unhedge = (t) => t.replace(HEDGE, "").replace(/[ \t]{2,}/g, " ");
const esc = (s) => String(s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function site(host) { const k = REG.alias[host] || host; return REG.sites[k] ? { key: k, ...REG.sites[k] } : null; }

function robots(S, host) {
  const b = `https://${host}`;
  let t = `# ${S.name} — agents, crawlers and answer engines are welcome.${/^cedwyn\./.test(host) ? "" : " Sion's Tab agent."}\n# Guide for language models: ${b}/llms.txt · Tools and data (MCP discovery): ${b}/.well-known/mcp.json · Page index: ${b}/agent/pages.json\n`;
  t += "User-agent: *\nAllow: /\n";
  for (const d of S.disallow || []) t += `Disallow: ${d}\n`;
  t += `\nSitemap: ${b}/sitemap.xml\n`;
  for (const x of EXTRA_SITEMAPS[host] || []) t += `Sitemap: ${b}${x}\n`; // garden-store 0.4.0
  if (/^cedwyn\./.test(host)) t += `Sitemap: ${b}/sitemap-core.xml\n`; // sales-fix run 12
  if (/^cedwyn\./.test(host)) t += `Sitemap: ${b}/feed.xml\n`; // Atom feed (sales-fix run 13)
  if (S.licence) t += `# ${S.licence}\n`;
  return t;
}

function sitemap(S, host) {
  const ok = (u) => !(/^cedwyn\./.test(host) && SF12SKIP.test(u));
  const urls = (S.pages || []).filter((p) => ok(p.u)).map((p) => `<url><loc>${esc("https://" + host + p.u)}</loc>${S.lastmod ? `<lastmod>${S.lastmod}</lastmod>` : ""}</url>`).concat((S.extra || []).filter(ok).map((u) => `<url><loc>${esc("https://" + host + encodeURI(u))}</loc></url>`));
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join("\n")}\n</urlset>\n`;
}

function agentSection(S, host) {
  const b = `https://${host}`;
  let t = `## For AI agents (machine-readable, read-only)\n`;
  t += `- [Tools and data endpoints (MCP discovery)](${b}/.well-known/mcp.json): every tool below as JSON, callable with a plain GET.\n`;
  t += `- [Page index](${b}/agent/pages.json): every page with its title and description.\n`;
  t += `- [Search this site](${b}/agent/search?q=${WB(host) ? "Over%20Stowey" : "Great%20House%20Farm"}): GET /agent/search?q=… returns matching pages with snippets.\n`;
  t += `- [Read one page as text](${b}/agent/page?slug=/): GET /agent/page?slug=<path>.\n`;
  for (const d of S.data || []) t += `- [${d.name}](${d.url.startsWith("http") ? d.url : b + d.url}): ${d.desc}\n`;
  for (const x of S.tools || []) t += `- Tool \`${x.name}\`: ${x.description} GET ${b}/agent/tool/${x.name}\n`;
  t += `- In a browser that supports WebMCP (navigator.modelContext), the same tools are registered on the page.\n`;
  return t;
}

function llms(S, host) {
  const b = `https://${host}`;
  let t = `# ${S.name}\n\n> ${S.desc}\n\n`;
  if (S.about) t += S.about + "\n\n";
  t += `## Key pages\n`;
  for (const p of (S.pages || []).slice(0, 60)) t += `- [${p.t || p.u}](${b}${p.u})${p.d ? ": " + p.d : ""}\n`;
  t += "\n" + agentSection(S, host);
  if (!WB(host)) t += `\n## The wider estate\n- [Home: the Disclosure Dartboard](https://bucklerfamily.estate/) · [all sites with their own llms.txt](https://bucklerfamily.estate/llms.txt)\n- [Great House Farm Legal Wiki](https://greathousefarmwiki.wordpress.com/): the evidence catalogue.\n`;
  return t;
}

function llmsFull(S, host) {
  let t = llms(S, host) + "\n\n# Full text of each page\n";
  for (const p of S.pages || []) t += `\n\n## ${p.t || p.u}\nURL: https://${host}${p.u}\n${p.d ? p.d + "\n" : ""}\n${p.x || ""}\n`;
  return t;
}

const GENERIC = [
  { name: "list_pages", description: "List every page on this site with its title, path and one-line description.", inputSchema: { type: "object", properties: {} }, endpoint: "/agent/pages.json" },
  { name: "search", description: "Search this site's pages (titles, headings and text). Returns the best matches with a snippet.", inputSchema: { type: "object", properties: { q: { type: "string", description: "Words to search for" }, limit: { type: "integer", description: "Max results (default 10)" } }, required: ["q"] }, endpoint: "/agent/search" },
  { name: "get_page", description: "Get one page's title, description, headings and main text by its path (slug), e.g. / or /risk-register/.", inputSchema: { type: "object", properties: { slug: { type: "string", description: "Page path, e.g. /brief/" } }, required: ["slug"] }, endpoint: "/agent/page" },
];

function toolsFor(S) {
  return GENERIC.concat((S.tools || []).map((x) => ({ name: x.name, description: x.description, inputSchema: x.inputSchema || { type: "object", properties: {} }, endpoint: "/agent/tool/" + x.name, source: x.src || x.url || null })));
}

function mcp(S, host) {
  const b = `https://${host}`;
  return {
    schema: WB(host) ? "agent-discovery/1.0" : "ghf-agent-discovery/1.0", generated: REG._generated, name: S.name, description: S.desc, url: b + "/",
    note: "Read-only. Every tool is a plain HTTPS GET that returns JSON; arguments go in the query string. The same tools are registered with navigator.modelContext (WebMCP) on the site's pages where the browser supports it.",
    llms: b + "/llms.txt", llms_full: b + "/llms-full.txt", sitemap: b + "/sitemap.xml", pages: b + "/agent/pages.json", webmcp_script: b + "/agent/webmcp.js",
    tools: toolsFor(S).map((t) => ({ name: t.name, description: t.description, inputSchema: t.inputSchema, annotations: { readOnlyHint: true }, http: { method: "GET", url: b + t.endpoint }, source: t.source || undefined })),
    data: (S.data || []).map((d) => ({ ...d, url: d.url.startsWith("http") ? d.url : b + d.url })),
    estate: WB(host) ? undefined : { home: "https://bucklerfamily.estate/", sites: REG._sites },
  };
}

function words(q) { return String(q || "").toLowerCase().split(/[^\p{L}\p{N}]+/u).filter((w) => w.length > 1); }
function snippet(x, ws) {
  const l = (x || "").toLowerCase(); let i = -1;
  for (const w of ws) { i = l.indexOf(w); if (i >= 0) break; }
  const s = Math.max(0, i - 120); return (s ? "…" : "") + (x || "").slice(s, s + 320) + "…";
}
function search(S, host, q, limit) {
  const ws = words(q); if (!ws.length) return { query: q, results: [] };
  const res = [];
  for (const p of S.pages || []) {
    const t = (p.t || "").toLowerCase(), h = (p.h || []).join(" ").toLowerCase(), d = (p.d || "").toLowerCase(), x = (p.x || "").toLowerCase();
    let sc = 0; for (const w of ws) sc += (t.includes(w) ? 6 : 0) + (h.includes(w) ? 3 : 0) + (d.includes(w) ? 2 : 0) + (x.includes(w) ? 1 : 0);
    if (sc) res.push({ score: sc, url: `https://${host}${p.u}`, slug: p.u, title: p.t, description: p.d, snippet: snippet(p.x, ws) });
  }
  res.sort((a, b) => b.score - a.score);
  return { query: q, count: res.length, results: res.slice(0, Math.min(+limit || 10, 50)) };
}
function page(S, host, slug) {
  slug = String(slug || "/"); if (!slug.startsWith("/")) slug = "/" + slug;
  const c = [slug, slug.endsWith("/") ? slug.slice(0, -1) : slug + "/"];
  const p = (S.pages || []).find((p) => c.includes(p.u)) || (S.pages || []).find((p) => p.u.replace(/\/$/, "").endsWith(slug.replace(/\/$/, "")) && slug !== "/");
  if (!p) return null;
  return { url: `https://${host}${p.u}`, slug: p.u, title: p.t, description: p.d, headings: p.h, text: p.x, captured: REG._generated, note: "Text as served without JavaScript at the capture time; the live page is at url." };
}

// ---------- tool runners ----------
async function getJSON(u) { const r = await fetch(u, { headers: { accept: "application/json", "user-agent": "ghf-agent-ready" }, cf: { cacheTtl: 300 } }); if (!r.ok) throw new Error("source " + r.status); return r.json(); }
function records(o, key, flatten) {
  if (key) { for (const k of key.split(".")) o = o ? o[k] : o; }
  if (Array.isArray(o) && !flatten) return o;
  if (flatten) { const out = []; const walk = (v) => { if (Array.isArray(v)) { v.forEach(walk); return; } if (!v || typeof v !== "object") return; const kids = Object.values(v).filter((x) => x && typeof x === "object"); if (!kids.length) { out.push(v); return; } const scal = Object.fromEntries(Object.entries(v).filter(([, x]) => x === null || typeof x !== "object")); if (Object.keys(scal).length >= 2 && Object.values(v).every((x) => !Array.isArray(x) || !x.length)) out.push(scal); kids.forEach(walk); }; walk(o); return out; }
  let best = []; const scan = (v, d) => { if (d > 3 || !v || typeof v !== "object") return; if (Array.isArray(v)) { if (v.length > best.length && v.some((x) => x && typeof x === "object")) best = v; return; } for (const x of Object.values(v)) scan(x, d + 1); };
  scan(o, 0); return best;
}
function filt(rs, args, fields) {
  const ws = words(args.q); let out = rs;
  if (ws.length) out = out.filter((r) => { const s = JSON.stringify(r).toLowerCase(); return ws.every((w) => s.includes(w)); });
  for (const f of fields || []) if (args[f]) { const v = String(args[f]).toLowerCase(); out = out.filter((r) => JSON.stringify(r[f] ?? r).toLowerCase().includes(v)); }
  const lim = Math.min(+args.limit || 25, 200);
  return { total: rs.length, matched: out.length, returned: Math.min(lim, out.length), records: out.slice(0, lim).map((r) => { const s = JSON.stringify(r); return s.length > 4000 ? { _truncated: true, ...JSON.parse(JSON.stringify(r, (k, v) => (typeof v === "string" && v.length > 600 ? v.slice(0, 600) + "…" : v))) } : r; }) };
}
function stripTags(h) { return h.replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>/gi, " ").replace(/<br\s*\/?>/gi, "\n").replace(/<\/(p|div|li|h\d|tr)>/gi, "\n").replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;|&#x27;/g, "'").replace(/[ \t]+/g, " ").replace(/\n\s*\n+/g, "\n").trim(); }
function tables(html) {
  const out = [];
  for (const tm of html.matchAll(/<table[\s\S]*?<\/table>/gi)) {
    const rows = [...tm[0].matchAll(/<tr[\s\S]*?<\/tr>/gi)].map((r) => [...r[0].matchAll(/<t([hd])[^>]*>([\s\S]*?)<\/t[hd]>/gi)].map((c) => ({ th: c[1].toLowerCase() === "h", v: stripTags(c[2]) })));
    if (!rows.length) continue;
    let head = rows[0].every((c) => c.th) ? rows.shift().map((c) => c.v) : null;
    const cap = (tm[0].match(/<caption[^>]*>([\s\S]*?)<\/caption>/i) || [])[1];
    out.push({ caption: cap ? stripTags(cap) : undefined, columns: head || undefined, rows: rows.map((r) => (head ? Object.fromEntries(r.map((c, i) => [head[i] || "col" + i, c.v])) : r.map((c) => c.v))) });
  }
  return out;
}
async function doc(u) {
  const r = await fetch(u, { headers: { "user-agent": "ghf-agent-ready", accept: "text/html" } }); if (!r.ok) throw new Error("page " + r.status);
  const h = await r.text(); const title = stripTags((h.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [])[1] || "");
  const main = (h.match(/<main[\s\S]*?<\/main>/i) || h.match(/<body[\s\S]*<\/body>/i) || [h])[0];
  return { url: u, title, tables: tables(main), text: stripTags(main).slice(0, 60000), links: [...new Set([...main.matchAll(/href="([^"#]+)"/g)].map((m) => new URL(m[1], u).href))].slice(0, 300) };
}
async function runTool(S, host, name, args) {
  const x = (S.tools || []).find((t) => t.name === name); if (!x) return J({ error: "no such tool", tools: toolsFor(S).map((t) => t.name) }, 404);
  const abs = (u) => (u.startsWith("http") ? u : `https://${host}${u}`);
  try {
    if (x.kind === "json") { let o = await getJSON(abs(x.src)); if (x.key) for (const k of x.key.split(".")) o = o[k]; return J({ source: abs(x.src), data: o }); }
    if (x.kind === "filter") { const srcs = [].concat(x.src); let rs = []; for (const s of srcs) rs = rs.concat(records(await getJSON(abs(s)), x.key, x.flatten)); return J({ source: srcs.map(abs), ...filt(rs, args, x.fields) }); }
    if (x.kind === "proxy") { const u = new URL(abs(x.src)); for (const [k, v] of Object.entries(args)) if (v !== "" && v != null && k !== "limit") u.searchParams.set(k, v); const d = await getJSON(u.href); const lim = Math.min(+args.limit || 25, 200); if (d && Array.isArray(d.records) && d.records.length > lim) { d.total_records = d.records.length; d.records = d.records.slice(0, lim); d.note = "First " + lim + " records; add limit=… (max 200) for more, or GET " + u.href + " for all."; } return J({ source: u.href, data: d }); }
    if (x.kind === "tables") {
      const want = String(args.register || args.name || "").toLowerCase(); const m = x.map || {};
      const keys = want && m[want] ? [want] : Object.keys(m);
      if (want && !m[want]) return J({ error: "unknown register", options: Object.keys(m) }, 400);
      const out = {}; for (const k of keys) { try { const d = await doc(abs(m[k])); out[k] = { url: d.url, title: d.title, tables: d.tables, text: d.tables.length ? undefined : d.text.slice(0, 8000) }; } catch (e) { out[k] = { url: abs(m[k]), error: String(e.message || e) }; } }
      return J({ live: true, fetched: new Date().toISOString(), registers: out });
    }
    if (x.kind === "highlight") {
      const idx = await doc(abs(x.src)); const id = String(args.id || "").toLowerCase();
      const cands = idx.links.filter((l) => new URL(l).host === host && x.pattern && new RegExp(x.pattern, "i").test(l));
      const pick = id ? cands.find((l) => l.toLowerCase().includes(id)) : cands.sort().reverse()[0];
      if (!pick) return J({ error: "report not found", available: cands }, 404);
      const d = await doc(pick); return J({ live: true, report: { url: d.url, title: d.title, text: d.text.slice(0, 40000), tables: d.tables }, available: cands });
    }
    if (x.kind === "page") { const d = await doc(abs(x.src)); return J({ live: true, ...d }); }
  } catch (e) { return J({ error: String(e.message || e), source: x.src }, 502); }
  return J({ error: "tool kind" }, 500);
}

// ---------- homepage enrichment ----------
function jsonld(S, host) {
  if (WB(host)) { const o = { "@type": "Organization", "@id": "https://webbrich.bucklerfamily.estate/#org", name: "Webb–Rich Family Archive", alternateName: ["Rich family of Over Stowey", "Over Stowey, Somerset"], url: "https://webbrich.bucklerfamily.estate/" }; return JSON.stringify({ "@context": "https://schema.org", "@graph": [o, { "@type": "WebSite", "@id": `https://${host}/#website`, url: `https://${host}/`, name: S.name, description: S.desc, inLanguage: "en-GB", publisher: { "@id": o["@id"] }, potentialAction: { "@type": "SearchAction", target: `https://${host}/agent/search?q={search_term_string}`, "query-input": "required name=search_term_string" } }] }).replace(/</g, "\\u003c"); }
  const org = { "@type": "Organization", "@id": "https://bucklerfamily.estate/#org", name: "Great House Farm (Tŷ Mawr) · Cedwyn Estate", alternateName: ["Williams–Buckler family estate", "Tŷ Mawr, Llandough-juxta-Penarth"], url: "https://bucklerfamily.estate/", email: "info@bucklerfamily.estate", sameAs: ["https://greathousefarmwiki.wordpress.com/", "https://www.facebook.com/901925066346636"] };
  return JSON.stringify({ "@context": "https://schema.org", "@graph": [org, { "@type": "WebSite", "@id": `https://${host}/#website`, url: `https://${host}/`, name: S.name, description: S.desc, inLanguage: "en-GB", publisher: { "@id": "https://bucklerfamily.estate/#org" }, isPartOf: host === "bucklerfamily.estate" ? undefined : { "@id": "https://bucklerfamily.estate/#website" }, potentialAction: { "@type": "SearchAction", target: `https://${host}/agent/search?q={search_term_string}`, "query-input": "required name=search_term_string" } }] }).replace(/</g, "\\u003c");
}
function noscript(S, host) {
  let h = `<noscript><section data-ghf-agent-summary style="max-width:760px;margin:1em auto;padding:0 1em"><h2>${esc(S.name)}</h2><p>${esc(S.desc)}</p>${S.about ? `<p>${esc(S.about)}</p>` : ""}<ul>`;
  for (const p of (S.pages || []).slice(0, 40)) h += `<li><a href="${esc(p.u)}">${esc(p.t || p.u)}</a>${p.d ? " — " + esc(p.d) : ""}</li>`;
  return h + `</ul><p><a href="/llms.txt">Plain-text guide (llms.txt)</a> · <a href="/.well-known/mcp.json">Tools and data (JSON)</a></p></section></noscript>`;
}
async function home(req, S, host) {
  const r = await fetch(req);
  const ct = r.headers.get("content-type") || "";
  if (r.status !== 200 || !ct.includes("text/html")) return r;
  const head = [`<link rel="alternate" type="text/plain" href="/llms.txt" title="Guide for language models" data-ghf-agent>`, `<link rel="alternate" type="application/json" href="/.well-known/mcp.json" title="Agent tools and data" data-ghf-agent>`];
  if (!S.jsonld) head.push(`<script type="application/ld+json" data-ghf-agent>${jsonld(S, host)}</script>`);
  if (!S.loadsHeader) head.push(`<script src="/agent/webmcp.js?v=${VER}" async data-ghf-webmcp></script>`);
  let rw = new HTMLRewriter().on("head", { element(e) { e.append(head.join(""), { html: true }); } });
  if (S.thin) rw = rw.on("body", { element(e) { e.append(noscript(S, host), { html: true }); } });
  const out = rw.transform(r); const hs = new Headers(out.headers); hs.set("x-agent-ready", VER);
  return new Response(out.body, { status: out.status, statusText: out.statusText, headers: hs });
}

async function origin(req) { try { const r = await fetch(req); const ct = r.headers.get("content-type") || ""; if (r.status !== 200 || ct.includes("text/html")) return null; const t = await r.text(); if (/^\s*</.test(t) && !/^\s*<\?xml|<urlset|<sitemapindex/.test(t)) return null; return { t, ct }; } catch (e) { return null; } }

const SF8P = { "/ebooks/supplement/cedwyn-supplement-2026-10-25.pdf": "https://raw.githubusercontent.com/unclehowell/bucklerfamily-estate/main/web/ebooks/supplement/cedwyn-supplement-2026-10-25.pdf" }; // sales-fix run 8
const SF8 = { "/ebooks/sample-chapter": "/ebooks/free/", "/ebooks/sample-chapter/": "/ebooks/free/", "/ebooks/supplement/cedwyn-supplement-2026-10-25.pdf": "/ebooks/cedwyn/", "/dartboard/coins/terms/": "/dartboard/terms/", "/dartboard/coins/terms": "/dartboard/terms/", "/wayback/pdf/ghf-ebook-v1-free-sample.pdf": "/ebooks/free/", "/dartboard/ebook/api/free": "/ebooks/free/", "/dartboard/free": "/ebooks/free/", "/dartboard/free/": "/ebooks/free/" }; // sales-fix run 8
const SF12CORE = ["/", "/ebooks/", "/ebooks/all-four/", "/ebooks/free/", "/ebooks/enwau/", "/ebooks/cedwyn/", "/ebooks/dartboard/", "/ebooks/fcg/", "/ebooks/projects/", "/ebooks/recorded-incidents/", "/ebooks/tymawr-deaths/", "/ebooks/tymawr-heritage/", "/ebooks/williams-buckler-family/", "/ebooks/library/", "/title-chain/", "/research/bp-properties-v-buckler/", "/research/demolition-1988/", "/research/timeline/", "/research/evidence/", "/research/evidence/ev-0215-tithe-apportionment-john-williams-c1841/", "/research/evidence/ev-0248-marconi-in-wales-may-1897-contemporary-press/", "/research/woodland/", "/research/", "/wales/", "/argentina/", "/patagonia/", "/story/", "/nomenclature/", "/dartboard/", "/wiki/", "/email/", "/wayback/", "/projects/", "/documentary/", "/shop/"]; // cedwyn core sitemap: shop, book pages and hub pages first (sales-fix run 12)
const SF12LASTMOD = {"/":"2026-10-27","/ebooks/":"2026-10-30","/ebooks/all-four/":"2026-10-30","/ebooks/free/":"2026-10-30","/ebooks/enwau/":"2026-10-30","/ebooks/cedwyn/":"2026-10-30","/ebooks/dartboard/":"2026-10-30","/ebooks/fcg/":"2026-10-30","/ebooks/projects/":"2026-10-30","/ebooks/recorded-incidents/":"2026-10-30","/ebooks/tymawr-deaths/":"2026-10-30","/ebooks/tymawr-heritage/":"2026-10-30","/ebooks/williams-buckler-family/":"2026-10-30","/ebooks/library/":"2026-10-30","/title-chain/":"2026-10-26","/research/bp-properties-v-buckler/":"2026-10-30","/research/demolition-1988/":"2026-10-30","/research/timeline/":"2026-10-30","/research/evidence/":"2026-10-30","/research/evidence/ev-0215-tithe-apportionment-john-williams-c1841/":"2026-10-26","/research/evidence/ev-0248-marconi-in-wales-may-1897-contemporary-press/":"2026-10-27","/research/woodland/":"2026-10-30","/research/":"2026-10-29","/wales/":"2026-10-26","/argentina/":"2026-10-26","/patagonia/":"2026-10-26","/nomenclature/":"2026-10-29","/wiki/":"2026-10-24","/email/":"2026-10-26","/wayback/":"2026-10-27","/projects/":"2026-10-30","/documentary/":"2026-10-30","/shop/":"2026-10-27"}; // per-URL last change of the page source (newest commit touching it), 30 Oct 2026; refresh: work/agent-ready/core_lastmod.py
const SF13FEED = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<feed xmlns=\"http://www.w3.org/2005/Atom\" xml:lang=\"en-GB\"><id>https://cedwyn.bucklerfamily.estate/feed.xml</id><title>Tŷ Mawr e-books · Cedwyn</title><subtitle>New and updated e-books from the records of Great House Farm (Tŷ Mawr), Llandough. First editions free; updated editions £4.99; all-four bundle £19.96.</subtitle><link rel=\"self\" type=\"application/atom+xml\" href=\"https://cedwyn.bucklerfamily.estate/feed.xml\"/><link rel=\"hub\" href=\"https://pubsubhubbub.appspot.com/\"/><link rel=\"alternate\" type=\"text/html\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/\"/><author><name>Cedwyn Estate</name><uri>https://cedwyn.bucklerfamily.estate/</uri></author><updated>2026-10-30T16:37:33Z</updated><entry><id>https://cedwyn.bucklerfamily.estate/ebooks/enwau/</id><title>Enwau: the names of Tŷ Mawr · Cedwyn e-books</title><link rel=\"alternate\" type=\"text/html\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/enwau/\"/><link rel=\"enclosure\" type=\"image/jpeg\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/enwau/cover.jpg\"/><updated>2026-10-26T00:00:00Z</updated><summary type=\"text\">A forensic register of every name and identity of Tŷ Mawr, the town of Llandough-juxta-Penarth and the estate: 108 entries, each with its form, date, source document, who wrote it and our note. Free first edition.</summary></entry>\n<entry><id>https://cedwyn.bucklerfamily.estate/ebooks/</id><title>Great House Farm (Tŷ Mawr) e-books · Llandough, Penarth · Welsh history</title><link rel=\"alternate\" type=\"text/html\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/\"/><link rel=\"enclosure\" type=\"image/jpeg\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/covers/great-house-farm-wiki-0.2.1.jpg\"/><updated>2026-10-27T01:06:24Z</updated><summary type=\"text\">E-books on Great House Farm (Tŷ Mawr), Llandough-juxta-Penarth: Welsh history, the Williams–Buckler family, and BP Properties v Buckler [1987], the adverse possession case. PDF, instant download.</summary></entry>\n<entry><id>https://cedwyn.bucklerfamily.estate/ebooks/all-four/</id><title>All four Great House Farm e-books · Tŷ Mawr bundle · £19.96</title><link rel=\"alternate\" type=\"text/html\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/all-four/\"/><link rel=\"enclosure\" type=\"image/jpeg\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/shop/img/all-four-cover.jpg\"/><updated>2026-10-30T16:37:33Z</updated><summary type=\"text\">All four Great House Farm (Tŷ Mawr) e-books in one bundle, £19.96: Welsh history from Llandough and Penarth and BP Properties v Buckler [1987], the adverse possession case. Four PDFs, instant download.</summary></entry>\n<entry><id>https://cedwyn.bucklerfamily.estate/ebooks/free/</id><title>Free first edition: the Great House Farm Legal Wiki (PDF)</title><link rel=\"alternate\" type=\"text/html\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/free/\"/><link rel=\"enclosure\" type=\"image/jpeg\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/shop/img/fcg-cover.jpg\"/><updated>2026-10-30T16:37:33Z</updated><summary type=\"text\">Get the first edition of the Great House Farm (Tŷ Mawr) Legal Wiki free: 2,033 pages of evidence register, timeline, judgments and maps as one PDF.</summary></entry>\n<entry><id>https://cedwyn.bucklerfamily.estate/ebooks/tymawr-heritage/</id><title>Tŷ Mawr · History and heritage of Great House Farm, Llandough</title><link rel=\"alternate\" type=\"text/html\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/tymawr-heritage/\"/><link rel=\"enclosure\" type=\"image/jpeg\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/shop/img/tymawr-heritage-cover.jpg\"/><updated>2026-10-30T16:37:33Z</updated><summary type=\"text\">The history and heritage of Great House Farm, Llandough. 43-page PDF e-book, £4.99. Great House Farm (Tŷ Mawr), Llandough, Penarth: Welsh history and BP Properties v Buckler [1987], the adverse possession case.</summary></entry>\n<entry><id>https://cedwyn.bucklerfamily.estate/ebooks/williams-buckler-family/</id><title>The Williams–Buckler Family · Tŷ Mawr family history e-book</title><link rel=\"alternate\" type=\"text/html\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/williams-buckler-family/\"/><link rel=\"enclosure\" type=\"image/jpeg\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/shop/img/williams-buckler-family-cover.jpg\"/><updated>2026-10-30T16:37:33Z</updated><summary type=\"text\">People, records and a family tree of Tŷ Mawr. 34-page PDF e-book, £4.99. Great House Farm (Tŷ Mawr), Llandough, Penarth: Welsh history and BP Properties v Buckler [1987], the adverse possession case.</summary></entry>\n<entry><id>https://cedwyn.bucklerfamily.estate/ebooks/cedwyn/</id><title>Cedwyn · Names, places, legend and title of Tŷ Mawr · free e-book</title><link rel=\"alternate\" type=\"text/html\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/cedwyn/\"/><link rel=\"enclosure\" type=\"image/jpeg\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/shop/img/cedwyn-cover.jpg\"/><updated>2026-10-30T16:37:33Z</updated><summary type=\"text\">The old names of Great House Farm, Llandough, the places that carry them, the giant, the saint and the title tested from the first record of the name, the 1824 David Stewart survey. 32-page PDF e-book, free first edition. Great House Farm (Tŷ Mawr), Llandough, Penarth: Welsh history and BP Properties v Buckler [1987], the adverse possession case.</summary></entry>\n<entry><id>https://cedwyn.bucklerfamily.estate/ebooks/recorded-incidents/</id><title>Recorded Incidents · Tŷ Mawr, Llandough in the police and court record</title><link rel=\"alternate\" type=\"text/html\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/recorded-incidents/\"/><link rel=\"enclosure\" type=\"image/jpeg\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/shop/img/recorded-incidents-cover.jpg\"/><updated>2026-10-30T16:37:33Z</updated><summary type=\"text\">Tŷ Mawr in the police, court and press record, 1891–1989. 44-page PDF e-book, £4.99. Great House Farm (Tŷ Mawr), Llandough, Penarth: Welsh history and BP Properties v Buckler [1987], the adverse possession case.</summary></entry>\n<entry><id>https://cedwyn.bucklerfamily.estate/ebooks/tymawr-deaths/</id><title>The Tŷ Mawr Deaths · Llandough casebook 1855–1990 e-book</title><link rel=\"alternate\" type=\"text/html\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/tymawr-deaths/\"/><link rel=\"enclosure\" type=\"image/jpeg\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/shop/img/tymawr-deaths-cover.jpg\"/><updated>2026-10-30T16:37:33Z</updated><summary type=\"text\">A casebook on the timing of the Williams and Buckler deaths at Great House Farm, Llandough, 1855–1990. 69-page PDF e-book, £4.99. Great House Farm (Tŷ Mawr), Llandough, Penarth: Welsh history and BP Properties v Buckler [1987], the adverse possession case.</summary></entry>\n<entry><id>https://cedwyn.bucklerfamily.estate/ebooks/fcg/</id><title>Great House Farm / Tŷ Mawr — our case and lines of enquiry · FCG e-book</title><link rel=\"alternate\" type=\"text/html\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/fcg/\"/><link rel=\"enclosure\" type=\"image/jpeg\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/shop/img/fcg-cover.jpg\"/><updated>2026-10-30T16:37:33Z</updated><summary type=\"text\">Great House Farm / Tŷ Mawr — our case and lines of enquiry. 221-page PDF e-book, £4.99. Great House Farm (Tŷ Mawr), Llandough, Penarth: Welsh history and BP Properties v Buckler [1987], the adverse possession case.</summary></entry>\n<entry><id>https://cedwyn.bucklerfamily.estate/ebooks/dartboard/</id><title>The Disclosure Dartboard · FOI escalation e-book · Great House Farm</title><link rel=\"alternate\" type=\"text/html\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/dartboard/\"/><link rel=\"enclosure\" type=\"image/jpeg\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/shop/img/dartboard-cover.jpg\"/><updated>2026-10-30T16:37:33Z</updated><summary type=\"text\">Institutions and their escalation ladders. 404-page PDF e-book, £4.99. Great House Farm (Tŷ Mawr), Llandough, Penarth: Welsh history and BP Properties v Buckler [1987], the adverse possession case.</summary></entry>\n<entry><id>https://cedwyn.bucklerfamily.estate/ebooks/projects/</id><title>Great House Farm Projects · Tŷ Mawr PRINCE2 dossier e-book</title><link rel=\"alternate\" type=\"text/html\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/projects/\"/><link rel=\"enclosure\" type=\"image/jpeg\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/shop/img/projects-cover.jpg\"/><updated>2026-10-30T16:37:33Z</updated><summary type=\"text\">The PRINCE2 project dossier of the Tŷ Mawr digital estate and its evidence-recovery programme. 187-page PDF e-book, £4.99. Great House Farm (Tŷ Mawr), Llandough, Penarth: Welsh history and BP Properties v Buckler [1987], the adverse possession case.</summary></entry>\n<entry><id>https://cedwyn.bucklerfamily.estate/ebooks/library/</id><title>The Llandough–Leckwith Landscape Library — E-books — Great House Farm / Tŷ Mawr</title><link rel=\"alternate\" type=\"text/html\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/library/\"/><link rel=\"enclosure\" type=\"image/jpeg\" href=\"https://cedwyn.bucklerfamily.estate/ebooks/covers/great-house-farm-wiki-0.2.1.jpg\"/><updated>2026-10-30T16:37:33Z</updated><summary type=\"text\">121 short e-books on Great House Farm (Tŷ Mawr), Llandough, the Williams–Buckler family and the Llandough–Leckwith landscape. First editions free.</summary></entry>\n<entry><id>https://cedwyn.bucklerfamily.estate/title-chain/</id><title>Title chain · Tŷ Mawr · Cedwyn</title><link rel=\"alternate\" type=\"text/html\" href=\"https://cedwyn.bucklerfamily.estate/title-chain/\"/><updated>2026-10-27T01:06:24Z</updated><summary type=\"text\">Title chain of Tŷ Mawr, Llandough: the Williams family line at the house, then every title others assert over it, tested link by link against its source; gaps shown as gaps.</summary></entry></feed>\n"; // cedwyn Atom feed of the e-books, WebSub hub (sales-fix run 13)
const SF12SKIP = /\/thank-you\/|^\/ebooks\/read\/$|^\/argentina\/(authorities|chat|cyberspace|dartboard|email|emails|fcg|movie|projects|qa|review|wales|watchtower|wdtk)\/$|^\/movie\/$/; // night-shift traffic 5 Nov 2026: paths that now 301 (to /online/*, /documentary/, /wales/) kept out of the sitemap; their targets are in the registry extra list // noindex pages kept out of the cedwyn sitemap (sales-fix run 12)
// garden-store 0.4.0 (2 Nov 2026): the apex sitemap and robots.txt also list the Garden Store's own sitemap (every page and product);
// its URLs are merged into the apex urlset; llms.txt on the apex points agents at its dropship catalogue and MCP endpoint.
const EXTRA_SITEMAPS = { "bucklerfamily.estate": ["/garden-store/sitemap.xml"] };
const EXTRA_SRC = { "/garden-store/sitemap.xml": "https://cedwyn.bucklerfamily.estate/garden-store/sitemap.xml" };
const EXTRA_LLMS = { "cedwyn.bucklerfamily.estate": "\n## Sections added or renamed since 23 Oct 2026 (refreshed 9 Nov 2026)\n- [Online](https://cedwyn.bucklerfamily.estate/online/): the online sections of Cedwyn (history, records, guided tour, e-books); several former /argentina/* pages now live here.\n- [Documentary](https://cedwyn.bucklerfamily.estate/documentary/): Cedwyn, a documentary, one two-minute scene at a time through the chronology of Tŷ Mawr (/movie/ redirects here).\n- [Blog](https://cedwyn.bucklerfamily.estate/blog/): short posts on the history, heritage and records of Tŷ Mawr, each linked to its record; feed at /blog/rss.xml.\n- [Tithe H3](https://cedwyn.bucklerfamily.estate/tithe-h3/): the Stewart estate plan parcels traced through the 1841 tithe map onto a modern map, with grid references and H3 hexagons.\n- [Missing records register](https://cedwyn.bucklerfamily.estate/research/missing-records/): blank evidence pages (MR-nnnn) for records that should exist but are not held.\n- [Books that mention the farm](https://cedwyn.bucklerfamily.estate/research/books/): printed books with page references.\n- [The Release Machine](https://cedwyn.bucklerfamily.estate/releases/): publication dates of related documents, 1987-2026, each linked to its source.\n- [Spill](https://cedwyn.bucklerfamily.estate/spill/): tell Cedwyn about a record it has not published yet.\n- [That Old Chestnut](https://cedwyn.bucklerfamily.estate/online/that-old-chestnut/): replies from public bodies to information requests, read line by line, each with the statute it relies on.\n- [What they don't say](https://cedwyn.bucklerfamily.estate/online/whattheydontsay/): dated questions to public bodies and record holders: what was asked, when an answer was due, what came back and what is still unanswered.\n- [Forensic assessments](https://cedwyn.bucklerfamily.estate/forensic/): each institution in the record, its role, its replies to information requests and what changed since each assessment.\n- [Family tree](https://cedwyn.bucklerfamily.estate/familytree/): the Williams–Buckler family of Tŷ Mawr; every person and link names its record, every gap is marked not yet found.\n- [Chubut H3](https://cedwyn.bucklerfamily.estate/chubut-h3/): the Cedwyn field outline from the Tithe H3 map set on the Golfo Nuevo coast, true size, in H3 hexagons.\n- [NFT Flower Gallery](https://cedwyn.bucklerfamily.estate/nft-art/): digital editions repainted as gardens from photographs, maps and plans in the Wayback Vault; each piece is a catalogue record.\n- [Great House II in 3D](https://cedwyn.bucklerfamily.estate/argentina-3d/): a 3D world of the Patagonian steppe near Puerto Madryn with Tŷ Mawr, the Great House, reconstructed from the 1974 measured survey and the family album photographs; real sun for the place and the hour.\n- [Hive](https://cedwyn.bucklerfamily.estate/hive/) and [open jobs](https://cedwyn.bucklerfamily.estate/hive/jobs/): the drafting board where contributing agents take the next open job.\n\n## Machine-readable (current)\n- MCP server (read-only, streamable HTTP, no auth): https://cedwyn.bucklerfamily.estate/mcp/archive ; server card /.well-known/mcp/server-card.json\n- Agent library index: /agents.json (entry /academy/, work board /academy/work.json)\n- Sitemaps: /sitemap.xml (all pages), /sitemap-core.xml (shop, e-books and hub pages)\n", "bucklerfamily.estate": "\n## Garden Store (machine-readable)\n- /garden-store/llms.txt : guide to the plant store (Garden City supplies, ships and takes payment; this site never does)\n- /garden-store/products.json : dropship catalogue with supplier order links, shipping and returns\n- POST /garden-store/mcp : MCP server (read-only tools search_products, list_products, get_product, get_dropship_terms); discovery /garden-store/.well-known/mcp\n- /garden-store/feed.xml : Google Merchant Center product feed\n" };
let MERGE_NOTE = "";
async function mergeSitemaps(base, host, env) {
  MERGE_NOTE = "";
  try {
    let add = "";
    for (const x of EXTRA_SITEMAPS[host] || []) {
      const src = EXTRA_SRC[x] || `https://${host}${x}`; const r = env && env.GARDEN_STORE ? await env.GARDEN_STORE.fetch(new Request(src)) : await fetch(src, { cf: { cacheTtl: 3600, cacheEverything: true } }); // service binding: a same-zone fetch skips the store Worker
      if (!r.ok) { MERGE_NOTE = "src " + r.status; continue; }
      const t = await r.text(); const m = t.match(/<url>[\s\S]*<\/url>/); if (m) add += "\n" + m[0].split("https://cedwyn.bucklerfamily.estate").join(`https://${host}`);
    }
    if (!add) { MERGE_NOTE = MERGE_NOTE || "no urls"; return base; } MERGE_NOTE = "merged";
    return base.replace(/<urlset([^>]*)>/, (s, at) => /xmlns:image/.test(at) ? s : `<urlset${at} xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">`).replace(/\s*<\/urlset>\s*$/, add + "\n</urlset>\n");
  } catch (e) { MERGE_NOTE = "err " + String(e && e.message || e).slice(0, 60); return base; }
}
export default {
  async fetch(req, env, ctx) {
    ctx.passThroughOnException();
    const url = new URL(req.url), host = url.hostname, p = url.pathname;
    if (req.method !== "GET" && req.method !== "HEAD") return fetch(req);
    if (host === "cedwyn.bucklerfamily.estate" && SF8P[p]) { const o = await fetch(SF8P[p], { cf: { cacheTtl: 86400, cacheEverything: true } }); if (o.ok) return new Response(o.body, { headers: { "content-type": "application/pdf", "content-disposition": "inline", "cache-control": "public, max-age=86400", "x-agent-ready": "sf8" } }); } // committed file the Pages build does not serve (sales-fix run 8)
    if (host === "cedwyn.bucklerfamily.estate" && SF8[p]) return new Response(null, { status: 302, headers: { location: "https://cedwyn.bucklerfamily.estate" + SF8[p], "cache-control": "public, max-age=300", "x-agent-ready": "sf8" } }); // dead buy-path links -> live pages (sales-fix run 8)
    if (p === "/fa677e0431be909a80ac62103516fbd0.txt") return new Response("fa677e0431be909a80ac62103516fbd0", { headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "public, max-age=3600" } }); // IndexNow key (sales-fix run 6)
    if (host === "cedwyn.bucklerfamily.estate" && p === "/sitemap-core.xml") return new Response(`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${SF12CORE.map((u) => `<url><loc>https://cedwyn.bucklerfamily.estate${u}</loc>${SF12LASTMOD[u] ? `<lastmod>${SF12LASTMOD[u]}</lastmod>` : ""}</url>`).join("\n")}\n</urlset>\n`, { headers: { "content-type": "application/xml; charset=utf-8", "cache-control": "public, max-age=3600", "x-agent-ready": "sf12" } }); // core sitemap (sales-fix run 12)
    if (host === "cedwyn.bucklerfamily.estate" && (p === "/feed.xml" || p === "/ebooks/feed.xml")) { const H13 = { "content-type": "application/atom+xml; charset=utf-8", "cache-control": "public, max-age=3600", "etag": "W/\"sf13-9dc68a5112e738c3\"", "last-modified": "Fri, 30 Oct 2026 16:37:33 GMT", "link": "<https://pubsubhubbub.appspot.com/>; rel=\"hub\", <https://cedwyn.bucklerfamily.estate/feed.xml>; rel=\"self\"", "x-agent-ready": "sf13" }; const inm = req.headers.get("if-none-match"), ims = req.headers.get("if-modified-since"); if ((inm && inm.split(",").map(s => s.trim()).includes(H13.etag)) || (!inm && ims && new Date(ims) >= new Date(H13["last-modified"]))) return new Response(null, { status: 304, headers: H13 }); return new Response(SF13FEED, { headers: H13 }); } // e-book Atom feed (sales-fix run 13); conditional GET added 27 Oct (blog worker)
    if (FROZEN.test(host)) return p === "/" && req.method === "GET" ? withFooter(await fetch(req), host) : fetch(req);
    const S = site(host); if (!S) return p === "/" && req.method === "GET" ? withFooter(await fetch(req), host) : fetch(req);
    try {
      if (p === "/robots.txt") return T(robots(S, host));
      if (p === "/sitemap.xml") { if (S.origin && S.origin.sitemap) { if (!EXTRA_SITEMAPS[host]) return fetch(req); const o = await fetch(req); const ot = o.ok ? await o.text() : ""; if (/<urlset/.test(ot)) { const r = T(await mergeSitemaps(ot, host, env), "application/xml; charset=utf-8"); r.headers.set("x-agent-ready-merge", "origin " + (MERGE_NOTE || "none")); return r; } if (/<sitemapindex/.test(ot)) { const r = T(ot.replace(/<\/sitemapindex>/, EXTRA_SITEMAPS[host].map((x) => `<sitemap><loc>https://${host}${x}</loc></sitemap>`).join("") + "</sitemapindex>"), "application/xml; charset=utf-8"); r.headers.set("x-agent-ready-merge", "origin index"); return r; } return fetch(req); } if (EXTRA_SITEMAPS[host]) { const r = T(await mergeSitemaps(sitemap(S, host), host, env), "application/xml; charset=utf-8"); r.headers.set("x-agent-ready-merge", MERGE_NOTE || "none"); return r; } return T(sitemap(S, host), "application/xml; charset=utf-8"); }
      if (p === "/llms.txt") { if (S.origin && S.origin.llms) { const o = await origin(req); if (o) { const r = T(unhedge(o.t).replace(/\s*$/, "") + "\n\n" + agentSection(S, host) + llmsSection() + (EXTRA_LLMS[host] || "")); r.headers.set("x-agent-ready-origin", "1"); return r; } } return T(llms(S, host) + llmsSection() + (EXTRA_LLMS[host] || "")); }
      if (p === "/llms-full.txt") return T(llmsFull(S, host));
      if (p === "/.well-known/mcp.json" || p === "/.well-known/webmcp.json" || p === "/agent/" || p === "/agent" || p === "/agent/index.json") return J(mcp(S, host));
      if (p === "/agent/tools.json") return J({ site: S.name, generated: REG._generated, tools: toolsFor(S) });
      if (p === "/agent/pages.json") return J({ site: S.name, url: `https://${host}/`, generated: REG._generated, count: (S.pages || []).length, pages: (S.pages || []).map((x) => ({ url: `https://${host}${x.u}`, slug: x.u, title: x.t, description: x.d })) });
      if (p === "/agent/search") return J(search(S, host, url.searchParams.get("q"), url.searchParams.get("limit")));
      if (p === "/agent/page") { const r = page(S, host, url.searchParams.get("slug") || url.searchParams.get("path")); return r ? J(r) : J({ error: "page not found", hint: "GET /agent/pages.json for slugs" }, 404); }
      if (p.startsWith("/agent/tool/")) return runTool(S, host, decodeURIComponent(p.slice(12)), Object.fromEntries(url.searchParams));
      if (p === "/agent/webmcp.js" || p === "/ghf-lang/ghf-webmcp.js") return T(WB(host) ? WEBMCP.replace(/^\/\*![\s\S]*?\*\/\s*/, "") : WEBMCP, "application/javascript; charset=utf-8");
      if (p === "/" && S.home) return withFooter(await home(req, S, host), host);
    } catch (e) { return fetch(req); }
    return p === "/" ? withFooter(await fetch(req), host) : fetch(req);
  },
};
