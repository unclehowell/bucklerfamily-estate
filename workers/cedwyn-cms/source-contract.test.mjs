import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const engine = readFileSync(new URL("./engine.js", import.meta.url), "utf8");
const worker = readFileSync(new URL("./index.js", import.meta.url), "utf8");
const admin = readFileSync(new URL("./admin.txt", import.meta.url), "utf8");
const relay = readFileSync(new URL("./relay/relay.mjs", import.meta.url), "utf8");
const workflow = readFileSync(new URL("../../.github/workflows/cms-relay.yml", import.meta.url), "utf8");

test("CMS source has no dependency on the retired central repository", () => {
  for (const [name, text] of [["engine", engine], ["worker", worker], ["admin UI", admin], ["relay", relay], ["workflow", workflow]]) {
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

test("writes and reads use the compartment repository; shared builds use the platform repository", () => {
  assert.ok(engine.includes("const c = job.compartment, branch = c.branch, repo = c.repo || PLATFORM_REPO"));
  assert.ok(worker.includes("E.rawAt(c.repo || E.PLATFORM_REPO"));
  assert.ok(worker.includes("/repos/${E.PLATFORM_REPO}/actions/workflows/build.yml/dispatches"));
  assert.ok(admin.includes("/repos/${c.repo||'unclehowell/bucklerfamily-estate'}/git/trees/"));
  assert.ok(relay.includes("E.commit(gh, job)"));
});

test("central site data and sandbox remain confined to platform-owned paths", () => {
  assert.ok(engine.includes("only: /^workers\\/cedwyn-cms\\/sandbox\\/"));
  assert.ok(engine.includes("only: /^[^/]+\\.json$/"));
  assert.ok(engine.includes("=== PLATFORM_REPO && c.branch === 'main'"));
});

test("the relay now checks out the successor main branch and preserves relay auth", () => {
  assert.ok(workflow.includes("ref: main"));
  assert.ok(!workflow.includes("ref: cms"));
  assert.ok(workflow.includes("CMS_RELAY_KEY"));
  assert.ok(workflow.includes("CMS_CROSS_REPO_TOKEN"));
  assert.ok(workflow.includes("workers/cedwyn-cms/relay/relay.mjs"));
});

test("legacy queues fail closed and pre-migration publishes cannot be reverted into another repository", () => {
  assert.ok(worker.includes("legacy single-repository draft"));
  assert.ok(worker.includes("if (!last.repo)"));
});
