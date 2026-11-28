import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const engine = readFileSync(new URL("./engine.js", import.meta.url), "utf8");
const worker = readFileSync(new URL("./index.js", import.meta.url), "utf8");
const admin = readFileSync(new URL("./admin.txt", import.meta.url), "utf8");

test("CMS source has no dependency on the retired central repository", () => {
  for (const [name, text] of [["engine", engine], ["worker", worker], ["admin UI", admin]]) {
    assert.doesNotMatch(text, /unclehowell\/cedwyn(?:\/|["'\x60 ]|$)/, name);
    assert.doesNotMatch(text, /raw\.githubusercontent\.com\/unclehowell\/cedwyn\//, name);
  }
  assert.ok(engine.includes("PLATFORM_REPO = 'unclehowell/bucklerfamily-estate'"));
});

test("CMS compartments derive split application destinations from the central manifest", () => {
  assert.ok(engine.includes("manifest && Array.isArray(manifest.apps)"));
  assert.ok(engine.includes("a.mode === 'split-repo'"));
  assert.ok(engine.includes("repo: app.repo, branch: 'main'"));
  assert.ok(worker.includes("'split-repos.json'"));
  assert.ok(worker.includes("E.compartments(JSON.parse(E.unutf8(b)), JSON.parse(E.unutf8(m)))"));
});

test("reads and writes use the selected compartment repository; central builds use the platform", () => {
  assert.ok(engine.includes("const c = job.compartment, branch = c.branch, repo = c.repo || PLATFORM_REPO"));
  assert.ok(worker.includes("E.rawAt(c.repo || E.PLATFORM_REPO"));
  assert.ok(worker.includes("/repos/${E.PLATFORM_REPO}/actions/workflows/build.yml/dispatches"));
  assert.ok(admin.includes("/repos/${c.repo||'unclehowell/bucklerfamily-estate'}/git/trees/"));
});

test("central site data and sandbox remain confined to platform-owned paths", () => {
  assert.ok(engine.includes("only: /^workers\\/cedwyn-cms\\/sandbox\\/"));
  assert.ok(engine.includes("only: /^[^/]+\\.json$/"));
  assert.ok(engine.includes("=== PLATFORM_REPO && c.branch === 'main'"));
});

test("native Cron drains queued work through the existing encrypted CMS token", () => {
  assert.ok(worker.includes("async scheduled(controller, env, ctx)"));
  assert.ok(worker.includes("async function drainQueue(env)"));
  assert.ok(worker.includes("const token = await ghToken(env)"));
  assert.ok(worker.includes("const queued = (await listJobs(env, 'q:', 10)).reverse()"));
  assert.ok(worker.includes("github_write_token_unavailable"));
  assert.ok(worker.includes("repository_write_access_unavailable"));
  assert.ok(worker.includes("if (!res.ok && /^ref read (401|403|404)\\b/.test(res.error || '')) return job;"));
  assert.ok(worker.includes("Never consume queued work when the stored credential cannot read the selected app repository."));
});

test("legacy queued drafts fail closed and pre-migration publishes cannot be reverted into another repository", () => {
  assert.ok(worker.includes("legacy single-repository draft"));
  assert.ok(worker.includes("if (!last.repo)"));
  assert.ok(worker.includes("await env.CMS.put('q:' + job.key"));
});
