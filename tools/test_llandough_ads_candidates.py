#!/usr/bin/env python3
"""Checks the rights-held Llandough candidates, without network or publication."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import views

source = ROOT / 'data/core/records/llandough-ads-candidates.json'
doc = json.loads(source.read_text(encoding='utf-8'))
records = doc['records']
assert {r['id'] for r in records} == {'AR-9050', 'AR-9051'}
schema = views.load_schema()
for r in records:
    assert not views.validate(r, schema), (r['id'], views.validate(r, schema))
    assert r['kind'] == 'catalogue_candidate'
    assert r['public'] is False
    assert r['scope']['disposition'] == 'on_hold'
    assert r['description'] and r['interpretation'] and r['transcript_status']
    assert 'transcript' not in r
    assert r['provenance']['holder'] == 'Archaeology Data Service'
    assert any(link['rel'] == 'source' and link['to'].startswith('https://archaeologydataservice.ac.uk/') for link in r['links'])
assert views.select(records, {}) == [], 'rights-held candidates must not appear in public views'
for rid in ('AR-9050', 'AR-9051'):
    count = 0
    for p in (ROOT / 'data/core/records').glob('*.json'):
        payload = json.loads(p.read_text(encoding='utf-8'))
        count += sum(r.get('id') == rid for r in payload.get('records', []))
    assert count == 1, (rid, count)
print('PASS: two schema-subset-checked, unique, on-hold, non-public metadata candidates; no transcript or copy claimed')
