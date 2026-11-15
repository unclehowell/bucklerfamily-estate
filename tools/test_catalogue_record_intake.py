#!/usr/bin/env python3
"""Regression checks for the fixed-field core catalogue intake and LLAN94 entries."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import views

CORE_SCHEMA = json.loads((ROOT / "data/core/schema/core-record.schema.json").read_text(encoding="utf-8"))
FORM_SCHEMA = json.loads((ROOT / "data/core/schema/catalogue-record-intake.schema.json").read_text(encoding="utf-8"))
TEMPLATE = json.loads((ROOT / "data/core/schema/catalogue-record-template.json").read_text(encoding="utf-8"))
SOURCE = json.loads((ROOT / "data/core/records/archaeology-catalogue-2026-11-15.json").read_text(encoding="utf-8"))

core_fields = set(CORE_SCHEMA["properties"])
form_record = FORM_SCHEMA["properties"]["records"]["items"]["properties"]["record"]
template_record = TEMPLATE["records"][0]["record"]

assert FORM_SCHEMA["version"] == "1.0.0"
assert FORM_SCHEMA["source_schema"]["version"] == CORE_SCHEMA["version"]
assert set(form_record["properties"]) == core_fields - {"id"}
assert set(form_record["required"]) == core_fields - {"id"}
assert set(template_record) == core_fields - {"id"}
assert TEMPLATE["target"] == "catalogue"
assert TEMPLATE["catalogue_checked"] is True
assert template_record["public"] is False
assert FORM_SCHEMA["properties"]["target"]["const"] == "catalogue"
assert FORM_SCHEMA["properties"]["catalogue_checked"]["const"] is True

expected = {"AR-9052", "AR-9053", "AR-9054", "AR-9055", "AR-9056"}
rows = SOURCE["records"]
assert {r["id"] for r in rows} == expected
assert len(rows) == len(expected)

seen = set()
for r in rows:
    assert set(r) == core_fields, (r["id"], sorted(set(r) - core_fields), sorted(core_fields - set(r)))
    assert r["id"] not in seen, r["id"]
    seen.add(r["id"])
    assert not views.validate(r, CORE_SCHEMA), (r["id"], views.validate(r, CORE_SCHEMA))
    assert r["kind"] == "catalogue_candidate"
    assert r["public"] is True
    assert r["scope"]["disposition"] == "catalogue_only"
    assert r["description"] and r["transcript"] and r["transcript_status"] and r["interpretation"]
    assert r["provenance"]["holder"] and r["provenance"]["reference"]
    assert any(link["rel"] == "source_catalogue" and link["to"].startswith("https://") for link in r["links"])
    assert views.check_public("catalogue", r) == [], (r["id"], views.check_public("catalogue", r))

all_records, problems = views.load_core()
assert not problems, problems
all_ids = [r["id"] for r in all_records]
assert len(all_ids) == len(set(all_ids)), "duplicate IDs in the combined master catalogue"
assert expected.issubset(set(all_ids))

print("PASS: fixed form matches core schema v0.5.0 with every non-ID field required")
print("PASS: blank template carries all fields, catalogue target, and private intake default")
print("PASS: five unique, complete, source-linked archaeology catalogue records validate")
print("PASS: public text checks and combined catalogue ID checks")
