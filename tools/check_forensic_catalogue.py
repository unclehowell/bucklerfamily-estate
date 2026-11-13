#!/usr/bin/env python3
"""Fail the public site build if a published forensic assessment lacks a live catalogue record.

The assessment source is the dedicated unclehowell/cedwyn-forensic repository assembled at
DIST/forensic/. The public catalogue API is checked as well as both local registration files.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

DIST = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
APP = DIST / "forensic"
SEMVER = re.compile(r"^(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?(?:\\+[0-9A-Za-z.-]+)?$")
FA_ID = re.compile(r"^FA-[0-9]{4,}$")


def fail(message: str) -> None:
    print(f"FORENSIC CATALOGUE GUARD FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"cannot read {path}: {exc}")


def main() -> None:
    directory = read_json(APP / "data.json")
    register = read_json(APP / "data" / "catalogue-records.json")
    assessed = [item for item in directory.get("institutions", []) if item.get("kind") == "assessed"]
    records = register.get("records", [])
    if not assessed:
        fail("directory has no assessed pages")
    if register.get("record_count") != len(records) or len(records) != len(assessed):
        fail(f"directory has {len(assessed)} assessed pages but register declares {len(records)}")
    if register.get("source_repository") != "unclehowell/cedwyn-forensic":
        fail("assessment register does not name its dedicated source repository")

    by_slug = {}
    seen_ids = set()
    for record in records:
        slug, rid, version = record.get("slug"), record.get("id"), record.get("version")
        if not slug or slug in by_slug:
            fail(f"duplicate or missing assessment slug: {slug!r}")
        if not rid or not FA_ID.fullmatch(rid) or rid in seen_ids:
            fail(f"invalid or duplicate catalogue ID for {slug}: {rid!r}")
        if not version or not SEMVER.fullmatch(version):
            fail(f"invalid SemVer for {slug}: {version!r}")
        if record.get("kind") != "forensic_assessment" or record.get("version_scheme") != "SemVer 2.0.0":
            fail(f"wrong record kind/version scheme for {slug}")
        if record.get("page") != f"/forensic/{slug}/":
            fail(f"incorrect page route for {slug}: {record.get('page')!r}")
        data = record.get("data") or {}
        if data.get("version") != version or data.get("version_scheme") != "SemVer 2.0.0":
            fail(f"record data does not repeat the canonical version for {slug}")
        by_slug[slug] = record
        seen_ids.add(rid)

    if len(seen_ids) != len(records):
        fail("catalogue IDs are not unique")

    by_directory_slug = {item.get("slug"): item for item in assessed}
    if set(by_slug) != set(by_directory_slug):
        missing = sorted(set(by_directory_slug) - set(by_slug))
        extra = sorted(set(by_slug) - set(by_directory_slug))
        fail(f"directory/register slug mismatch; missing={missing}, extra={extra}")

    for slug, item in by_directory_slug.items():
        record = by_slug[slug]
        if item.get("catalogue_id") != record["id"]:
            fail(f"directory catalogue ID differs for {slug}")
        if item.get("version") != record["version"]:
            fail(f"directory SemVer differs from register for {slug}")
        page = APP / slug / "index.html"
        if not page.is_file():
            fail(f"published page is missing: {page}")
        html = page.read_text(encoding="utf-8", errors="replace")
        match = re.search(r'<p\\s+class="fa-kicker">[^<]*?\\bv([0-9]+\\.[0-9]+\\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\\+[0-9A-Za-z.-]+)?)', html)
        if not match or match.group(1) != record["version"]:
            fail(f"page header SemVer does not match catalogue for {slug}")
    js_path = APP / "fa.js"
    js = js_path.read_text(encoding="utf-8", errors="replace")
    if "/forensic/data.json" not in js or "fa-catalogue-ref" not in js:
        fail("individual assessment pages do not display their catalogue ID/version")

    query = urllib.parse.urlencode({"kind": "forensic_assessment", "q": "FA-", "limit": "500"})
    url = "https://bucklerfamily.estate/api/catalogue?" + query
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "BucklerFamilyForensicCatalogueGuard/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            public = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        fail(f"public catalogue API could not be checked: {exc}")
    public_items = public.get("items", [])
    public_by_id = {item.get("id"): item for item in public_items}
    expected_ids = {record["id"] for record in records}
    if public.get("total") != len(records) or set(public_by_id) != expected_ids:
        fail(f"public catalogue has total={public.get('total')} and {len(public_by_id)} FA rows; expected {len(records)}")

    for slug, record in by_slug.items():
        item = public_by_id.get(record["id"]) or {}
        data = item.get("data") or {}
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                fail(f"public catalogue record {record['id']} has invalid data JSON")
        if item.get("kind") != "forensic_assessment" or item.get("page") != record["page"]:
            fail(f"public catalogue route/kind mismatch for {record['id']}")
        if data.get("version") != record["version"] or data.get("institution_slug") != slug:
            fail(f"public catalogue SemVer/institution mismatch for {record['id']}")

    print(f"FORENSIC CATALOGUE GUARD OK: {len(records)} pages; {len(seen_ids)} unique FA IDs; all SemVer headers match; all records are public on bucklerfamily.estate.")


if __name__ == "__main__":
    main()
