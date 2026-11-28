import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./index.js", import.meta.url), "utf8");
const mapMatch = source.match(/const MAP = (\{.*?\});\nconst PLATFORM_REPO/s);
assert.ok(mapMatch, "API source map must be a parseable JSON literal");
const map = JSON.parse(mapMatch[1]);

test("API has no dependency on the retired central repository", () => {
  assert.doesNotMatch(source, /unclehowell\/cedwyn(?:\/|["'\x60 ]|$)/);
  assert.doesNotMatch(source, /raw\.githubusercontent\.com\/unclehowell\/cedwyn\//);
  assert.match(source, /const PLATFORM_REPO = "unclehowell\/bucklerfamily-estate";/);
});

test("split application history resolves to its dedicated source repository", () => {
  assert.equal(map.themes.wiki.repo, "unclehowell/cedwyn-wiki");
  assert.equal(map.themes.projects.repo, "unclehowell/cedwyn-projects");
  assert.equal(map.themes.ebooks.repo, "unclehowell/cedwyn-ebooks");
  assert.equal(map.themes.movie.repo, "unclehowell/cedwyn-documentary");
  assert.equal(map.themes.catalogue.repo, "unclehowell/cedwyn-catalogue");
  for (const [id, theme] of Object.entries(map.themes)) {
    if (theme.repo) {
      assert.equal(theme.b, "main", id + " must resolve through its dedicated main branch");
    }
  }
});

test("app-owned pages do not fall back to the central generic web directory", () => {
  for (const id of Object.keys(map.themes)) {
    if (map.themes[id].repo) assert.ok(!map.web.includes(id), id + " is directly mapped to its app repo");
  }
});

test("history URLs and commit queries use the repository attached to each candidate", () => {
  assert.match(source, /function histUrl\(c\).*c\.repo \|\| PLATFORM_REPO/s);
  assert.match(source, /repos\/.*c\.repo \|\| PLATFORM_REPO.*\/commits\?/s);
  assert.match(source, /cacheMatchesRepo/);
});

test("shared journal and guestbook assets use the successor platform", () => {
  assert.match(source, /bucklerfamily-estate\/main\/data\/journal\/pages\.json/);
  assert.match(source, /bucklerfamily-estate\/main\/web\/_cedwyn\/guestbook\/gb\.js/);
});
