import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(fileURLToPath(import.meta.url));
const source = await readFile(path.join(root, "worker.js"), "utf8");

test("ghf-status reads only the successor catalogue and split app repositories", () => {
  assert.ok(source.includes("https://raw.githubusercontent.com/unclehowell/bucklerfamily-estate/main/.github/daily-refresh/apps.json"));
  assert.ok(source.includes("feedLatest('unclehowell/bucklerfamily-estate', 'main', 'data/core')"));
  assert.ok(source.includes("const keyOf = a => [a.repo, 'main'];"));
  assert.doesNotMatch(source, /unclehowell\/cedwyn(?:\/|["'])/);
});
