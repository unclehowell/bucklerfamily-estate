#!/usr/bin/env python3
"""Checks the rights-held Llandough collection-page candidate, without network or publication."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import views

source = ROOT / 'data/core/records/llandough-ads-candidates.json'
doc = json.loads(source.read_text(encoding='utf-8'))
records = doc['records']
assert {r['id'] for r in records} == {'AR-9051'}
assert all(r['id'] != 'AR-9050' for r in records), 'Knight article already exists as MED-0098'
assert doc['catalogue_audit']['knight']['existing_id'] == 'MED-0098'
assert doc['catalogue_audit']['knight']['catalogue_url'] == 'https://bucklerfamily.estate/catalogue/?id=MED-0098'
assert set(doc['catalogue_audit']['holbrook_thomas']['existing_ids']) == {'MED-0096', 'MED-0097'}
schema = views.load_schema()
for r in records:
    assert not views.validate(r, schema), (r['id'], views.validate(r, schema))
    assert r['kind'] == 'catalogue_candidate'
    assert r['public'] is False
    assert r['scope']['disposition'] == 'on_hold'
    assert r['description'] and r['interpretation'] and r['transcript_status']
    assert 'transcript' not in r
    assert 'Archaeology Data Service' in r['provenance']['holder']
    assert any(link['rel'] == 'source' and link['to'].startswith('https://archaeologydataservice.ac.uk/') for link in r['links'])
assert views.select(records, {}) == [], 'rights-held candidate must not appear in public views'
for rid in ('AR-9051',):
    count = 0
    for p in (ROOT / 'data/core/records').glob('*.json'):
        payload = json.loads(p.read_text(encoding='utf-8'))
        count += sum(r.get('id') == rid for r in payload.get('records', []))
    assert count == 1, (rid, count)
print('PASS: one schema-checked, unique, on-hold ADS collection-page candidate; no duplicate Knight candidate or transcript/copy claim')
