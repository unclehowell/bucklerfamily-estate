import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const engine = readFileSync(new URL("./engine.js", import.meta.url), "utf8");
const worker = readFileSync(new URL("./index.js", import.meta.url), "utf8");
const relay = readFileSync(new URL("./relay/relay.mjs", import.meta.url), "utf8");
const workflow = readFileSync(new URL("../../.github/workflows/cms-relay.yml", import.meta.url), "utf8");

test("CMS source has no dependency on the retired central repository", () => {
  for (const [name, text] of [["engine", engine], ["worker", worker], ["relay", relay], ["workflow", workflow]]) {
    assert.doesNotMatch(text, /unclehowell\/cedwyn(?:\/|["'\x60 ]|$)/, name);
    assert.doesNotMatch(text, /raw\.githubusercontent\.com\/unclehowell\/cedwyn\//, name);
  }
  assert.match(engine, /PLATFORM_REPO = 'unclehowell\/bucklerfamily-estate'/);
});

test("CMS compartments derive split application destinations from the central manifest", () => {
  assert.match(engine, /manifest\.apps/);
  assert.match(engine, /a\.mode === 'split-repo'/);
  assert.match(engine, /a\.repo/);
  assert.match(engine, /repo: app\.repo, branch: 'main'/);
  assert.match(worker, /split-repos\.json/);
  assert.match(worker, /E\.compartments\(JSON\.parse\(E\.unutf8\(b\)\), JSON\.parse\(E\.unutf8\(m\)\)\)/);
});

test("writes and reads use the compartment repository; shared builds use the platform repository", () => {
  assert.match(engine, /const c = job\.compartment, branch = c\.branch, repo = c\.repo \|\| PLATFORM_REPO/);
  assert.match(worker, /E\.rawAt\(c\.repo \|\| E\.PLATFORM_REPO/);
  assert.match(worker, /repos\/\$\{E\.PLATFORM_REPO\}\/actions\/workflows\/build\.yml\/dispatches/);
  assert.match(relay, /E\.commit\(gh, job\)/);
});

test("central site data and sandbox remain confined to platform-owned paths", () => {
  assert.match(engine, /prefix: 'workers\/cedwyn-cms\/sandbox\//);
  assert.match(engine, /only: \^workers/);
  assert.match(engine, /prefix: '', only: \^\[\^\/\]\+\\.json\$/);
  assert.match(engine, /=== PLATFORM_REPO && c\.branch === 'main'/);
});

test("the relay now checks out the successor main branch and preserves relay auth", () => {
  assert.match(workflow, /ref: main/);
  assert.doesNotMatch(workflow, /ref: cms/);
  assert.match(workflow, /CMS_RELAY_KEY/);
  assert.match(workflow, /CMS_CROSS_REPO_TOKEN/);
  assert.match(workflow, /workers\/cedwyn-cms\/relay\/relay\.mjs/);
});

test("legacy queues fail closed and pre-migration publishes cannot be reverted into another repository", () => {
  assert.match(worker, /legacy single-repository draft/);
  assert.match(worker, /if \(!last\.repo\)/);
});
