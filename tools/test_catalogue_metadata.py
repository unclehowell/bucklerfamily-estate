#!/usr/bin/env python3
"""Regression tests for conservative catalogue metadata extraction and relation validation."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue_metadata import extract_record_metadata, parse_date_range, validate_relationship_registry


class DatePrecisionTests(unittest.TestCase):
    def test_year_is_not_expanded_to_fake_day(self):
        got = parse_date_range("1824")
        self.assertEqual(got, {
            "date_start": "1824", "date_end": "1824",
            "date_precision": "year", "date_sort": "1824"
        })

    def test_day_month_and_year_are_normalized(self):
        got = parse_date_range("7 May 1958")
        self.assertEqual(got["date_start"], "1958-05-07")
        self.assertEqual(got["date_precision"], "day")

    def test_year_range_is_preserved_as_year_precision(self):
        got = parse_date_range("1926–1940")
        self.assertEqual(got["date_start"], "1926")
        self.assertEqual(got["date_end"], "1940")
        self.assertEqual(got["date_precision"], "year_range")

    def test_zero_month_and_day_are_not_valid_dates(self):
        got = parse_date_range("1824-00-00")
        self.assertIsNone(got["date_start"])
        self.assertIsNone(got["date_sort"])
        self.assertEqual(got["date_precision"], "unparsed")

    def test_multiple_dates_are_not_reduced_to_one_date(self):
        got = parse_date_range("11 June 1904; 23 March 1905")
        self.assertIsNone(got["date_start"])
        self.assertEqual(got["date_precision"], "unparsed")


class PageMetadataTests(unittest.TestCase):
    def test_record_fields_statuses_sources_and_html_audit(self):
        page = """<!doctype html><html><head>
        <title>EV-0001 — Sample archive record</title>
        <meta name="description" content="Record-specific description">
        <link rel="canonical" href="https://bucklerfamily.estate/research/evidence/ev-0001-sample/">
        <meta property="og:title" content="EV-0001 — Sample archive record">
        <meta property="og:description" content="A sample record">
        <meta property="og:url" content="https://bucklerfamily.estate/research/evidence/ev-0001-sample/">
        <script type="application/ld+json">{"@context":"https://schema.org","@type":"CreativeWork"}</script>
        </head><body><article><table>
        <tr><th>Date of document</th><td>7 May 1958</td></tr>
        <tr><th>Type</th><td>Press report</td></tr>
        <tr><th>Evidence label</th><td>CONTEMPORANEOUS PRESS REPORT</td></tr>
        <tr><th>Status</th><td>READ (catalogue text); original newspaper not yet seen.</td></tr>
        <tr><th>Repository</th><td>Glamorgan Archives</td></tr>
        <tr><th>Reference</th><td>DX/123/4 <a href="https://archives.example.org/item/123">catalogue</a></td></tr>
        <tr><th>Access</th><td>View free at the archive.</td></tr>
        <tr><th>Provenance</th><td>Catalogue entry read on 21 November 2026.</td></tr>
        <tr><th>Related entries</th><td><a href="/research/evidence/ev-0002/">EV-0002</a></td></tr>
        </table><p class="meta">Evidence register · added 2026-11-21</p>
        <p><strong>Shows:</strong> The report records a public meeting.</p>
        <p><strong>Does not show:</strong> The original minutes have not been inspected.</p>
        </article></body></html>"""
        md, src = extract_record_metadata(
            "EV-0001", "/research/evidence/ev-0001-sample/", page
        )
        self.assertEqual(md["source_date_start"], "1958-05-07")
        self.assertEqual(md["source_date_precision"], "day")
        self.assertEqual(md["record_type"], "press_report")
        self.assertEqual(md["inspection_state"], "catalogue_only")
        self.assertEqual(md["access_state"], "open")
        self.assertEqual(md["repository_text"], "Glamorgan Archives")
        self.assertEqual(md["reference_text"], "DX/123/4 catalogue")
        self.assertIn("public meeting", md["shows_text"])
        self.assertIn("original minutes", md["does_not_show_text"])
        self.assertEqual(md["canonical_url"], "https://bucklerfamily.estate/research/evidence/ev-0001-sample/")
        self.assertEqual(md["catalogued_at"], "2026-11-21")
        self.assertIsNotNone(src)
        self.assertEqual(src["source_url"], "https://archives.example.org/item/123")


class RelationshipValidationTests(unittest.TestCase):
    def test_disambiguated_people_and_role_types_are_supported(self):
        entities, relations = validate_relationship_registry({
            "entities": [{
                "entity_id": "PER-0001", "entity_type": "person",
                "preferred_name": "John Williams", "disambiguator": "tenant recorded at Great House Farm"
            }, {
                "entity_id": "PLC-0001", "entity_type": "place",
                "entity_kind": "farm", "preferred_name": "Great House Farm"
            }],
            "relationships": [{
                "relationship_id": "REL-0001", "source_ev": "EV-0001",
                "entity_id": "PER-0001", "relation_type": "tenanted_by",
                "assertion_basis": "document_wording", "verification_state": "provisional",
                "date_start": "1916", "date_end": "1928", "date_precision": "year_range"
            }]
        }, {"EV-0001"})
        self.assertEqual(len(entities), 2)
        self.assertEqual(relations[0]["relation_type"], "tenanted_by")
        self.assertIsNone(relations[0]["target_ev"])

    def test_person_without_disambiguator_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "disambiguator"):
            validate_relationship_registry({
                "entities": [{
                    "entity_id": "PER-0001", "entity_type": "person",
                    "preferred_name": "John Williams"
                }],
                "relationships": []
            }, {"EV-0001"})

    def test_unknown_source_record_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "known source_ev"):
            validate_relationship_registry({
                "entities": [],
                "relationships": [{
                    "relationship_id": "REL-0001", "source_ev": "EV-9999",
                    "target_ev": "EV-0001", "relation_type": "cites"
                }]
            }, {"EV-0001"})


if __name__ == "__main__":
    unittest.main()
