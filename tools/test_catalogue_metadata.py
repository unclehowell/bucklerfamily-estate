#!/usr/bin/env python3
"""Regression tests for conservative catalogue metadata extraction and relation validation."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue_metadata import ensure_catalogue_html_metadata, extract_record_metadata, parse_date_range, validate_relationship_registry, visible_body_text_length, _states


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

    def test_approximate_year_keeps_approximation_and_sort_anchor(self):
        got = parse_date_range("circa 1824")
        self.assertEqual(got["date_start"], "1824")
        self.assertIsNone(got["date_end"])
        self.assertEqual(got["date_precision"], "approximate")
        self.assertEqual(got["date_sort"], "1824")

    def test_approximate_year_variants_are_supported(self):
        for value in ("c. 1841", "ca. 1841", "about 1841", "approximately 1841"):
            with self.subTest(value=value):
                self.assertEqual(parse_date_range(value)["date_precision"], "approximate")

    def test_availability_distinguishes_reference_from_copy(self):
        self.assertEqual(_states("Reference located", "", "")[0], "reference_located")
        self.assertEqual(_states("Copy held", "", "")[0], "copy_held")
        self.assertEqual(_states("Not held", "", "")[0], "unavailable")
        self.assertEqual(_states("Not located", "", "")[0], "not_located")



class VisibleBodyTextTests(unittest.TestCase):
    def test_script_and_style_text_do_not_count_as_visible_evidence_text(self):
        source = "<html><head><style>" + ("fake text " * 200) + "</style></head><body>" + \
                 "<script>" + ("not rendered " * 300) + "</script></body></html>"
        self.assertEqual(visible_body_text_length(source), 0)

    def test_visible_body_prose_is_counted(self):
        source = "<html><body><article>" + ("Visible source catalogue text. " * 30) + "</article></body></html>"
        self.assertGreater(visible_body_text_length(source), 500)


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
        <tr><th>Reference</th><td>DX/123/4 <a href="https://archives.example.org/item/123">catalogue</a> <a href="https://archives.example.org/repository">repository</a></td></tr>
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
        self.assertEqual(md["access_state"], "on_site")
        self.assertEqual(md["repository_text"], "Glamorgan Archives")
        self.assertEqual(md["reference_text"], "DX/123/4 catalogue repository")
        self.assertEqual(__import__("json").loads(md["field_states_json"])["holder_text"], "unknown")
        self.assertEqual(__import__("json").loads(md["field_states_json"])["reference_text"], "present")
        self.assertIn("public meeting", md["shows_text"])
        self.assertIn("original minutes", md["does_not_show_text"])
        self.assertEqual(md["canonical_url"], "https://bucklerfamily.estate/research/evidence/ev-0001-sample/")
        self.assertEqual(md["catalogued_at"], "2026-11-21")
        self.assertEqual(len(src), 2)
        self.assertEqual({item["source_url"] for item in src}, {
            "https://archives.example.org/item/123",
            "https://archives.example.org/repository"
        })


class HtmlMetadataEnrichmentTests(unittest.TestCase):
    def test_missing_head_metadata_is_added_and_auditable(self):
        source = """<!doctype html><html><head><meta charset="utf-8">
        <title>EV-0002 — Sample archive entry</title></head>
        <body><h1>EV-0002 — Sample archive entry</h1><p>Catalogue record text.</p></body></html>"""
        md, _ = extract_record_metadata("EV-0002", "/research/evidence/ev-0002-sample/", source)
        enriched, result = ensure_catalogue_html_metadata(
            "EV-0002", "/research/evidence/ev-0002-sample/", source, md
        )
        self.assertTrue(result["updated"])
        self.assertIn('<link rel="canonical" href="https://bucklerfamily.estate/research/evidence/ev-0002-sample/">', enriched)
        self.assertIn('property="og:title"', enriched)
        self.assertIn('property="og:description"', enriched)
        self.assertIn('property="og:url"', enriched)
        self.assertIn('name="description"', enriched)
        final_md, _ = extract_record_metadata(
            "EV-0002", "/research/evidence/ev-0002-sample/", enriched
        )
        audit = __import__("json").loads(final_md["metadata_audit_json"])
        self.assertTrue(audit["canonical_matches_expected"])
        self.assertTrue(audit["og_url_matches_expected"])
        self.assertTrue(audit["structured_data_matches_record"])

    def test_wiki_alias_uses_preferred_research_canonical(self):
        page = """<html><head>
        <title>EV-0004 — Wiki alias</title>
        <link rel="canonical" href="https://bucklerfamily.estate/research/evidence/ev-0004-record/">
        <meta property="og:url" content="https://bucklerfamily.estate/research/evidence/ev-0004-record/">
        </head><body>Wiki alias page content.</body></html>"""
        md, _ = extract_record_metadata("EV-0004", "/wiki/evidence/ev-0004-record/", page)
        self.assertEqual(md["canonical_url"], "https://bucklerfamily.estate/research/evidence/ev-0004-record/")
        enriched, _ = ensure_catalogue_html_metadata(
            "EV-0004", "/wiki/evidence/ev-0004-record/", page, md
        )
        self.assertIn(
            '<link rel="canonical" href="https://bucklerfamily.estate/research/evidence/ev-0004-record/">',
            enriched
        )
        audit = __import__("json").loads(md["metadata_audit_json"])
        self.assertTrue(audit["canonical_matches_expected"])
        self.assertTrue(audit["og_url_matches_expected"])

    def test_access_is_not_inferred_from_generic_status(self):
        page = """<html><head><title>EV-0005 — Record</title></head><body>
        <table><tr><th>Status</th><td>Catalogue text read; source not inspected.</td></tr></table>
        </body></html>"""
        md, _ = extract_record_metadata("EV-0005", "/research/evidence/ev-0005-record/", page)
        self.assertEqual(md["inspection_state"], "catalogue_only")
        self.assertEqual(md["access_state"], "unknown")

    def test_existing_unrelated_jsonld_is_preserved_and_record_schema_added(self):
        source = """<html><head><title>EV-0003 — Sample</title>
        <script type="application/ld+json">{"@context":"https://schema.org","@type":"WebSite","name":"Site"}</script>
        </head><body>Record</body></html>"""
        md, _ = extract_record_metadata("EV-0003", "/research/evidence/ev-0003-sample/", source)
        enriched, _ = ensure_catalogue_html_metadata(
            "EV-0003", "/research/evidence/ev-0003-sample/", source, md
        )
        self.assertIn('"@type":"WebSite"', enriched)
        self.assertIn('"@type": "CreativeWork"', enriched)
        self.assertIn('"identifier": "EV-0003"', enriched)
        final_md, _ = extract_record_metadata(
            "EV-0003", "/research/evidence/ev-0003-sample/", enriched
        )
        audit = __import__("json").loads(final_md["metadata_audit_json"])
        self.assertTrue(audit["structured_data_matches_record"])


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
                "assertion_text": "The record identifies the named person as tenant.",
                "source_note": "EV-0001, tenancy clause; page 2.",
                "date_start": "1916", "date_end": "1928", "date_precision": "year_range"
            }]
        }, {"EV-0001"})
        self.assertEqual(len(entities), 2)
        self.assertEqual(relations[0]["relation_type"], "tenanted_by")
        self.assertIsNone(relations[0]["target_ev"])

    def test_relationship_without_pinpointed_source_support_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "assertion_text or a source_note"):
            validate_relationship_registry({
                "entities": [{
                    "entity_id": "PER-0001", "entity_type": "person",
                    "preferred_name": "John Williams", "disambiguator": "tenant in an identified lease"
                }],
                "relationships": [{
                    "relationship_id": "REL-0001", "source_ev": "EV-0001",
                    "entity_id": "PER-0001", "relation_type": "tenanted_by",
                    "assertion_basis": "document_wording"
                }]
            }, {"EV-0001"})

    def test_person_without_disambiguator_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "disambiguator"):
            validate_relationship_registry({
                "entities": [{
                    "entity_id": "PER-0001", "entity_type": "person",
                    "preferred_name": "John Williams"
                }],
                "relationships": []
            }, {"EV-0001"})

    def test_spatial_geometry_requires_full_provenance(self):
        doc = {
            "entities": [{
                "entity_id": "PLC-0001", "entity_type": "place", "entity_kind": "farm",
                "preferred_name": "Great House Farm", "crs": "EPSG:27700",
                "geometry_type": "Polygon", "geometry": {"type": "Polygon", "coordinates": []},
                "transformation_method": "digitised from EV-0001 plan",
                "positional_uncertainty_m": None, "geometry_source_ev": "EV-0001"
            }],
            "relationships": []
        }
        entities, _ = validate_relationship_registry(doc, {"EV-0001"})
        self.assertEqual(entities[0]["crs"], "EPSG:27700")
        self.assertIsNone(entities[0]["positional_uncertainty_m"])

    def test_spatial_geometry_without_uncertainty_declaration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "positional_uncertainty_m"):
            validate_relationship_registry({
                "entities": [{
                    "entity_id": "PLC-0001", "entity_type": "place", "entity_kind": "farm",
                    "preferred_name": "Great House Farm", "crs": "EPSG:27700",
                    "geometry_type": "Polygon", "geometry": {"type": "Polygon", "coordinates": []},
                    "transformation_method": "digitised", "geometry_source_ev": "EV-0001"
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
