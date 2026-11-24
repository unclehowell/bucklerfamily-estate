#!/usr/bin/env node
'use strict';

/* Cold-load test for web/_cedwyn/evidence-browser.js (30 Oct 2026).
   The page markup never includes /_cedwyn/cat.js; the catalogue view must load
   the client itself before its first read. Simulates a cold page (window.Cedwyn
   absent), lets the injected script resolve asynchronously, and asserts the
   catalogue renders - including a CSSCPSG block - plus the designed degradation
   when the client load genuinely fails. No timers in the code under test. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '..', 'web', '_cedwyn', 'evidence-browser.js'), 'utf8');
assert.ok(!/setTimeout|setInterval/.test(source.match(/function clientReady[\s\S]*?\n  \}/)[0]),
  'clientReady must await the script load event, never a timer');

function element(tag) {
  return {
    tagName: tag.toUpperCase(), children: [], className: '', textContent: '',
    id: '', hidden: false, value: '', href: '', src: '', async: false,
    onload: null, onerror: null, listeners: {},
    setAttribute(k, v) { (this.attrs = this.attrs || {})[k] = String(v); },
    getAttribute(k) { return (this.attrs || {})[k] || null; },
    appendChild(child) { this.children.push(child); return child; },
    replaceChildren() { this.children = []; },
    addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); },
    querySelector() { return null; }, querySelectorAll() { return []; }
  };
}

function findAll(node, pred, out) {
  out = out || [];
  (node.children || []).forEach(c => { if (pred(c)) out.push(c); findAll(c, pred, out); });
  return out;
}

const row = {
  ev: 'EV-0001', title: '1955 possession order entry', path: '/research/evidence/ev-0001-order/',
  evidence_grade: 2, independent_origin_id: 'origin-1955-order', grade_note: 'Known through a later judgment.',
  aliases_json: '[]', description: 'Neutral record description.', description_status: 'assessed',
  transcript: '', transcript_status: 'not_assessed',
  interpretation: 'Interpretation kept separate.', interpretation_status: 'assessed',
  source_verification_status: 'reviewed', limitations: 'Underlying order copy not independently inspected.',
  source_date_text: '1955', source_date_start: '1955', source_date_end: '1955',
  source_date_precision: 'year', source_date_sort: '1955',
  analysis_date_text: null, catalogued_at: '2026-11-21', updated_at: null,
  record_type: 'court_judgment', record_type_label: 'Judgment',
  evidence_label: 'COURT JUDGMENT', status_text: 'Catalogue text read; original order not inspected.',
  availability_state: 'unknown', inspection_state: 'catalogue_only',
  verification_state: 'provisional', access_state: 'online', completeness_state: 'partial',
  holder_text: null, repository_text: 'Court archive', reference_text: 'CC/1955/14',
  repository_reference_text: null, access_note: 'Catalogue online.',
  provenance_text: 'Catalogue entry, not original instrument.',
  summary_text: 'A catalogue summary, explicitly attributed to the catalogue.',
  shows_text: 'What the judgment records.',
  does_not_show_text: 'The original order itself.',
  canonical_url: 'https://bucklerfamily.estate/research/evidence/ev-0001-order/',
  html_canonical_url: null, html_title: 'EV-0001 — 1955 possession order entry',
  meta_description: 'Evidence catalogue record EV-0001.',
  og_title: null, og_description: null, og_url: null, page_modified_at: null,
  structured_data_present: 1,
  metadata_audit_json: JSON.stringify({
    title_present: true, title_contains_record_id: true, description_present: true,
    canonical_present: true, canonical_matches_expected: true, og_title_present: true,
    og_description_present: true, og_url_present: true, og_url_matches_expected: true,
    structured_data_present: true, structured_data_valid: true,
    structured_data_matches_record: true, title_unique: true,
    description_unique: true, canonical_url_unique: true
  }),
  field_states_json: JSON.stringify({ holder_text: 'unknown', repository_text: 'present', reference_text: 'present' }),
  csscpsg_json: JSON.stringify({
    schema: 'csscpsg/1',
    scores: { S1: 1, S2: 2, S3: 0, S4: 1, S5: 2, S6: 0 },
    why: { S1: 'Recited as covering the whole of the farm.' },
    timing: [{ event: 'Notice to quit expired 2 Feb 1955', score: 0, why: 'Yearly tenancy anniversary: explained.' }],
    result: { compliant: true, S: 6, T: 0, D: 6 }
  }),
  catalogue_page_text: 'Published catalogue entry text.', catalogue_text_truncated: 0
};

function buildContext(opts) {
  const window = {};
  const state = { clientLoads: 0, queries: [] };
  const db = {
    query: async (sql) => {
      state.queries.push(sql);
      if (sql.includes("pragma_table_info('artifact_assessments')")) return [{ name: 'ev' }, { name: 'csscpsg_json' }];
      if (sql.includes("pragma_table_info('evidence_metadata')")) return [{ name: 'ev' }, { name: 'field_states_json' }];
      if (sql.includes("pragma_table_info('evidence_relationships')")) return [{ name: 'relationship_id' }];
      if (sql.includes("pragma_table_info('evidence_source_refs')")) return [{ name: 'source_ref_id' }];
      if (sql.includes('SUM(CASE WHEN')) return [{ total: 1, described: 1, transcribed: 0, interpreted: 1 }];
      if (sql.includes('FROM evidence_source_refs')) return [{
        source_ref_id: 'EV-0001:SRC-001', ev: 'EV-0001', seq: 1,
        holder: null, repository: 'Court archive', reference: 'CC/1955/14',
        repository_reference_text: null, source_url: 'https://archives.example.org/cc-1955-14',
        access_note: 'Catalogue online.', provenance_note: 'Catalogue only.',
        source_text: 'Court archive | CC/1955/14'
      }];
      if (sql.includes('FROM evidence_catalogue ec')) return [row];
      return [];
    }
  };
  const registry = {};
  ['[data-status]', '[data-results]', '#cw-eb-query', '[data-more]', '[data-coverage]', 'form', '[data-reset]']
    .forEach(sel => { registry[sel] = element(sel === 'form' ? 'form' : 'div'); });
  const modeButtons = [element('button'), element('button')];
  const root = element('section');
  root.querySelector = sel => registry[sel] || null;
  root.querySelectorAll = sel => (sel === '[data-mode]' ? modeButtons : []);
  const document = {
    readyState: 'loading',
    head: element('head'), documentElement: element('html'),
    querySelector: sel => (sel === '[data-cedwyn-evidence-browser]' ? root : null),
    createElement: element
  };
  const realAppend = document.head.appendChild.bind(document.head);
  document.head.appendChild = script => {
    assert.equal(script.src, '/_cedwyn/cat.js', 'must load the catalogue client URL');
    state.clientLoads++;
    setTimeout(() => {
      if (opts.clientSucceeds) {
        window.Cedwyn = { db: async () => db, sectionDb: async () => db };
        script.onload && script.onload();
      } else {
        script.onerror && script.onerror();
      }
    }, 0);
    return realAppend(script);
  };
  window.document = document;
  const context = { window, document, navigator: {}, console, URL, JSON, Promise, setTimeout, clearTimeout };
  vm.runInNewContext(source, context, { filename: 'evidence-browser.js' });
  return { window, document, root, registry, state };
}

async function flush(times) {
  for (let i = 0; i < (times || 8); i++) await new Promise(r => setTimeout(r, 0));
}

async function main() {
  // Cold load, client fetch succeeds: the view must render without any click.
  const ok = buildContext({ clientSucceeds: true });
  await flush();
  assert.equal(ok.state.clientLoads, 1, 'exactly one client script injection');
  const status = ok.registry['[data-status]'].textContent;
  assert.ok(status.startsWith('Level 1 · Artifacts'), 'cold load should render artifacts, got: ' + status);
  assert.ok(status.includes('Wiki section database'), 'theme slice source should be named, got: ' + status);
  const results = ok.registry['[data-results]'];
  assert.equal(results.children.length, 1, 'one record card rendered');
  const csBoxes = findAll(results, n => (n.className || '').includes('cw-eb-csscpsg'));
  assert.equal(csBoxes.length, 1, 'the record renders its CSSCPSG block');
  const s1 = findAll(csBoxes[0], n => (n.textContent || '').startsWith('S1 Scope: 1'));
  assert.equal(s1.length, 1, 'S1 score line rendered with reasoning');
  assert.ok(ok.registry['[data-coverage]'].textContent.includes('1 records'), 'coverage line populated');
  assert.equal(findAll(results, n => n.textContent === 'Structured record metadata · separate from source interpretation').length, 1,
    'normalized record metadata should render');
  assert.equal(findAll(results, n => n.textContent === 'Catalogue summary (labelled catalogue text, not original source wording)').length, 1,
    'explicit catalogue summaries should render with attribution');
  assert.equal(findAll(results, n => n.textContent.includes('A catalogue summary, explicitly attributed to the catalogue.')).length, 1,
    'catalogue summary text should render');
  assert.equal(findAll(results, n => n.textContent === 'Availability').length, 1,
    'separate availability state should render');
  assert.equal(findAll(results, n => n.textContent === 'Missing-value semantics · null values are not silently converted to empty strings').length, 1,
    'missing-value state semantics should render');
  assert.equal(findAll(results, n => n.textContent === 'HTML / search metadata audit').length, 1,
    'HTML metadata audit should render');
  assert.equal(findAll(results, n => n.textContent === 'Structured repository / source references').length, 1,
    'structured source references should render');
  assert.equal(findAll(results, n => n.href === 'https://archives.example.org/cc-1955-14').length, 1,
    'the cited repository URL should be linked');
  assert.ok(findAll(results, n => n.textContent === 'Structured data identifies this record: present / matches').length === 1,
    'record-specific structured data audit should render');

  // Genuine client failure: the designed degradation must survive.
  const bad = buildContext({ clientSucceeds: false });
  await flush();
  assert.equal(bad.state.clientLoads, 1, 'one injection attempt before failing');
  assert.ok(bad.registry['[data-status]'].textContent.startsWith('Could not read the catalogue:'),
    'failure keeps the designed status, got: ' + bad.registry['[data-status]'].textContent);
  const retry = findAll(bad.registry['[data-results]'],
    n => (n.textContent || '').includes('The source register remains below'));
  assert.equal(retry.length, 1, 'retry guidance still offered on genuine failure');

  console.log('test_evidence_browser_client: OK (cold load renders incl. CSSCPSG; genuine failure degrades as designed)');
}

main().catch(err => { console.error(err); process.exit(1); });
