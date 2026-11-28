import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(fileURLToPath(import.meta.url));
const source = await readFile(path.join(root, "index.js"), "utf8");

test("agent-ready serves the supplement from the successor repository", () => {
  assert.ok(source.includes("https://raw.githubusercontent.com/unclehowell/bucklerfamily-estate/main/web/ebooks/supplement/cedwyn-supplement-2026-10-25.pdf"));
  assert.doesNotMatch(source, /unclehowell\/cedwyn(?:\/|["'])/);
});
