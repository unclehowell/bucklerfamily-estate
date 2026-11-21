#!/usr/bin/env python3
"""Conservative extraction and validation for the public evidence catalogue.

Only explicit page labels and unambiguous date forms are normalized. Original
wording is retained; absent or ambiguous values remain NULL/unknown.
"""
from __future__ import annotations

from html.parser import HTMLParser
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse
import json
import re


CANONICAL_BASE = "https://bucklerfamily.estate"
ENTITY_TYPES = {"person", "place", "organization", "institution", "legal_body", "document"}
PLACE_KINDS = {"parish", "manor", "farm", "church", "parcel", "landscape", "building", "other", "unknown"}
RELATION_TYPES = {
    "owned_by", "occupied_by", "tenanted_by", "patron_of", "rector_of",
    "located_in", "part_of", "depicts", "transcribes", "analyses",
    "derived_from", "cites", "mentions", "same_source_as", "other",
}
ASSERTION_BASES = {"document_wording", "catalogue_interpretation", "family_account", "modern_analysis", "unknown"}
VERIFICATION_STATES = {"verified", "provisional", "unverified", "not_assessed"}


def optional_text(value):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    return value or None


def _valid_year(value):
    year = int(value)
    return 1000 <= year <= 2100


def parse_date_range(value):
    """Return partial ISO bounds without inventing month/day components."""
    raw = optional_text(value)
    if not raw:
        return {"date_start": None, "date_end": None, "date_precision": "unknown", "date_sort": None}
    s = raw.replace("–", "-").replace("—", "-").replace("−", "-")
    s = re.sub(r"\s+", " ", s).strip()

    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return {"date_start": s, "date_end": s, "date_precision": "day", "date_sort": s}
        except ValueError:
            pass

    m = re.fullmatch(r"(\d{4})-(\d{2})", s)
    if m and _valid_year(m.group(1)) and 1 <= int(m.group(2)) <= 12:
        return {"date_start": s, "date_end": s, "date_precision": "month", "date_sort": s}

    m = re.fullmatch(r"(\d{4})\s*-\s*(\d{4})", s)
    if m and _valid_year(m.group(1)) and _valid_year(m.group(2)) and int(m.group(1)) <= int(m.group(2)):
        return {"date_start": m.group(1), "date_end": m.group(2), "date_precision": "year_range", "date_sort": m.group(1)}

    m = re.fullmatch(r"(\d{4})", s)
    if m and _valid_year(m.group(1)):
        return {"date_start": s, "date_end": s, "date_precision": "year", "date_sort": s}

    months = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
        "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
        "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
        "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
    }
    m = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
    if m and m.group(2).lower() in months and _valid_year(m.group(3)):
        try:
            d = date(int(m.group(3)), months[m.group(2).lower()], int(m.group(1)))
            iso = d.isoformat()
            return {"date_start": iso, "date_end": iso, "date_precision": "day", "date_sort": iso}
        except ValueError:
            pass

    m = re.fullmatch(r"([A-Za-z]+)\s+(\d{4})", s)
    if m and m.group(1).lower() in months and _valid_year(m.group(2)):
        iso = "%04d-%02d" % (int(m.group(2)), months[m.group(1).lower()])
        return {"date_start": iso, "date_end": iso, "date_precision": "month", "date_sort": iso}

    return {"date_start": None, "date_end": None, "date_precision": "unparsed", "date_sort": None}


class _RecordParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = {}
        self.paragraphs = []
        self.meta = {}
        self.canonical = None
        self.title = []
        self._in_title = False
        self._in_script = False
        self._script_parts = []
        self.jsonld = []
        self._row_cells = []
        self._cell_kind = None
        self._cell_parts = []
        self._cell_links = []
        self._in_p = False
        self._p_parts = []

    def handle_starttag(self, tag, attrs):
        attrs = {str(k).lower(): v for k, v in attrs}
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or attrs.get("http-equiv") or "").strip().lower()
            if key and attrs.get("content") is not None:
                self.meta[key] = attrs.get("content")
        elif tag == "link" and "canonical" in (attrs.get("rel") or "").lower().split():
            self.canonical = attrs.get("href")
        elif tag == "tr":
            self._row_cells = []
        elif tag in ("th", "td"):
            self._cell_kind = tag
            self._cell_parts = []
            self._cell_links = []
        elif tag == "a" and self._cell_kind == "td" and attrs.get("href"):
            self._cell_links.append(attrs["href"])
        elif tag == "p":
            self._in_p = True
            self._p_parts = []
        elif tag == "script" and (attrs.get("type") or "").lower() == "application/ld+json":
            self._in_script = True
            self._script_parts = []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        elif tag in ("th", "td") and self._cell_kind:
            self._row_cells.append((self._cell_kind, "".join(self._cell_parts), list(self._cell_links)))
            self._cell_kind = None
        elif tag == "tr":
            headers = [x for x in self._row_cells if x[0] == "th"]
            values = [x for x in self._row_cells if x[0] == "td"]
            if headers and values:
                key = re.sub(r"[^a-z0-9]+", " ", headers[0][1].lower()).strip()
                val = optional_text(values[0][1])
                links = values[0][2]
                if key:
                    self.rows.setdefault(key, {"value": val, "links": []})
                    if val and self.rows[key]["value"] != val:
                        self.rows[key]["value"] = (self.rows[key]["value"] or "") + " | " + val
                    self.rows[key]["links"].extend(links)
        elif tag == "p" and self._in_p:
            self.paragraphs.append(optional_text("".join(self._p_parts)))
            self._in_p = False
        elif tag == "script" and self._in_script:
            self.jsonld.append("".join(self._script_parts))
            self._in_script = False

    def handle_data(self, data):
        if self._in_title:
            self.title.append(data)
        if self._cell_kind:
            self._cell_parts.append(data)
        if self._in_p:
            self._p_parts.append(data)
        if self._in_script:
            self._script_parts.append(data)


def _row(parser, *labels):
    for label in labels:
        key = re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()
        if key in parser.rows:
            return parser.rows[key]
    return {"value": None, "links": []}


def _record_type(label):
    if not label:
        return "unknown"
    s = label.lower()
    if "catalogue" in s or "administrative history" in s:
        return "archival_catalogue"
    if "judgment" in s or "judgement" in s:
        return "court_judgment"
    if s.startswith("law") or "legislation" in s or "enacted text" in s:
        return "legislation"
    if "press" in s or "newspaper" in s:
        return "press_report"
    if "manorial" in s:
        return "manorial_record_group"
    if "correspondence" in s or "letter" in s or "email" in s:
        return "correspondence"
    if "deed" in s or "conveyance" in s:
        return "deed_or_conveyance"
    if "map" in s or "plan" in s or "survey" in s:
        return "cartographic_record"
    if "photograph" in s or "photo" in s:
        return "photograph"
    if "analysis" in s or "research artifact" in s or "research analysis" in s:
        return "research_analysis"
    if "testimony" in s or "witness" in s or "family account" in s:
        return "testimony"
    if "record" in s:
        return "published_record"
    return "other"


def _states(status, evidence_label):
    s = (status or "").lower()
    label = (evidence_label or "").lower()
    combined = s + " " + label

    if re.search(r"\bnot held\b|\bno copy\b|\bnot in custody\b", combined):
        availability = "not_held"
    elif re.search(r"\bpartly held\b|\bpartially held\b", combined):
        availability = "partly_held"
    elif re.search(r"\bheld\b", combined):
        availability = "held"
    else:
        availability = "unknown"

    if "catalogue text" in combined and re.search(r"\bread\b|\bentries read\b", combined):
        inspection = "catalogue_only"
    elif re.search(r"\bpartly read\b|\bpartially read\b", combined):
        inspection = "partly_read"
    elif re.search(r"\bnot yet seen\b|\bnot inspected\b|\bnot seen\b", combined):
        inspection = "not_inspected"
    elif re.match(r"^\s*read\b", s) or s.strip() == "read":
        inspection = "read_in_full"
    else:
        inspection = "unknown"

    if re.search(r"\bnot verified\b|\bnot independently verified\b|\bnot verified independently\b", combined):
        verification = "unverified"
    elif "provisional" in combined:
        verification = "provisional"
    elif re.search(r"\bverified\b|\bconfirmed\b", combined):
        verification = "verified"
    else:
        verification = "unknown"

    if "paywall" in combined or "paywalled" in combined:
        access = "paywalled"
    elif "appointment" in combined:
        access = "appointment_required"
    elif "restricted" in combined or "closed to the public" in combined:
        access = "restricted"
    elif "view free" in combined or "open access" in combined or "freely available" in combined:
        access = "open"
    elif "view at" in combined or "consult at" in combined or "reading room" in combined:
        access = "on_site"
    elif "online" in combined:
        access = "online"
    else:
        access = "unknown"

    if re.search(r"\bpartial(?:ly)?\b|\bpartly\b|\btruncated\b|\bincomplete\b", combined):
        completeness = "partial"
    elif re.search(r"\bcomplete\b|\bfull text held\b", combined):
        completeness = "complete"
    else:
        completeness = "unknown"
    return availability, inspection, verification, access, completeness


def _first_paragraph_value(paragraphs, labels):
    for paragraph in paragraphs:
        if not paragraph:
            continue
        m = re.match(r"^([^:]+):\s*(.*)$", paragraph)
        if m and m.group(1).strip().lower() in labels:
            return optional_text(m.group(2))
    return None


def _field_state(value):
    """Return a controlled missing-value state without discarding original wording."""
    if value is None or not str(value).strip():
        return "unknown"
    text = str(value).strip().lower()
    if re.search(r"\bwithheld\\b|\\bredacted\\b", text):
        return "withheld"
    if re.search(r"\bnot applicable\\b|\\bn/?a\\b", text):
        return "not_applicable"
    if re.search(r"\bunknown\\b|\\bnot known\\b|\\bnot recorded\\b|\\bnot stated\\b", text):
        return "unknown"
    return "present"


def _catalogued_date(paragraphs):
    for paragraph in paragraphs:
        if not paragraph:
            continue
        m = re.search(r"\badded\s+(\d{4}-\d{2}-\d{2})\b", paragraph, re.I)
        if m:
            parsed = parse_date_range(m.group(1))
            if parsed["date_precision"] == "day":
                return m.group(1)
    return None


def _external_urls(parser, page_url, keys):
    urls = []
    for key in keys:
        row = parser.rows.get(key, {})
        for href in row.get("links", []):
            url = urljoin(page_url, href)
            parsed = urlparse(url)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                urls.append(url)
    return sorted(set(urls))


def extract_record_metadata(ev, page_path, html_text):
    """Extract one metadata row plus at most one structured source-reference row."""
    parser = _RecordParser()
    if html_text:
        parser.feed(html_text)
        parser.close()

    date_row = _row(parser, "date of document", "document date", "date")
    type_row = _row(parser, "type", "record type")
    label_row = _row(parser, "evidence label", "evidence type")
    status_row = _row(parser, "status", "record status")
    holder_row = _row(parser, "holder")
    repository_row = _row(parser, "repository")
    reference_row = _row(parser, "reference", "archive reference", "source reference")
    combined_row = _row(parser, "repository / reference", "repository and reference")
    access_row = _row(parser, "access", "access note")
    provenance_row = _row(parser, "provenance", "source provenance")
    analysis_row = _row(parser, "analysis date", "date of analysis")
    updated_row = _row(parser, "updated at", "last updated", "page modified")

    source_date_text = optional_text(date_row["value"])
    parsed_date = parse_date_range(source_date_text)
    type_label = optional_text(type_row["value"])
    evidence_label = optional_text(label_row["value"])
    status_text = optional_text(status_row["value"])
    availability, inspection, verification, access, completeness = _states(status_text, evidence_label)

    page_path = page_path if page_path.startswith("/") else "/" + page_path
    if not page_path.endswith("/"):
        page_path += "/"
    expected_canonical = CANONICAL_BASE + page_path
    html_canonical = optional_text(parser.canonical)
    html_title = optional_text("".join(parser.title))
    meta_description = optional_text(parser.meta.get("description"))
    og_title = optional_text(parser.meta.get("og:title"))
    og_description = optional_text(parser.meta.get("og:description"))
    og_url = optional_text(parser.meta.get("og:url"))
    modified = optional_text(parser.meta.get("article:modified_time") or parser.meta.get("og:updated_time") or parser.meta.get("last-modified")) or optional_text(updated_row["value"])
    source_date_text = source_date_text
    analysis_date_text = optional_text(analysis_row["value"])
    audit = {
        "title_present": bool(html_title),
        "title_contains_record_id": bool(html_title and ev and ev.lower() in html_title.lower()),
        "description_present": bool(meta_description),
        "canonical_present": bool(html_canonical),
        "canonical_matches_expected": bool(html_canonical and html_canonical.rstrip("/") == expected_canonical.rstrip("/")),
        "og_title_present": bool(og_title),
        "og_description_present": bool(og_description),
        "og_url_present": bool(og_url),
        "og_url_matches_expected": bool(og_url and og_url.rstrip("/") == expected_canonical.rstrip("/")),
        "server_rendered_text_present": bool(html_text and len(re.sub(r"<[^>]+>", " ", html_text)) > 500),
        "structured_data_present": bool(parser.jsonld),
        "structured_data_valid": all(_valid_json(x) for x in parser.jsonld) if parser.jsonld else False,
        "related_links_present": bool(_row(parser, "related entries")["links"]),
        "explicit_source_date_present": bool(source_date_text),
        "page_modified_date_present": bool(modified),
    }

    metadata = {
        "ev": ev,
        "source_date_text": source_date_text,
        "source_date_start": parsed_date["date_start"],
        "source_date_end": parsed_date["date_end"],
        "source_date_precision": parsed_date["date_precision"],
        "source_date_sort": parsed_date["date_sort"],
        "analysis_date_text": analysis_date_text,
        "analysis_date_start": parse_date_range(analysis_date_text)["date_start"],
        "analysis_date_end": parse_date_range(analysis_date_text)["date_end"],
        "analysis_date_precision": parse_date_range(analysis_date_text)["date_precision"],
        "catalogued_at": _catalogued_date(parser.paragraphs),
        "updated_at": modified,
        "record_type": _record_type(type_label),
        "record_type_label": type_label,
        "evidence_label": evidence_label,
        "status_text": status_text,
        "availability_state": availability,
        "inspection_state": inspection,
        "verification_state": verification,
        "access_state": access,
        "completeness_state": completeness,
        "holder_text": optional_text(holder_row["value"]),
        "repository_text": optional_text(repository_row["value"]),
        "reference_text": optional_text(reference_row["value"]),
        "repository_reference_text": optional_text(combined_row["value"]),
        "access_note": optional_text(access_row["value"]),
        "provenance_text": optional_text(provenance_row["value"]),
        "shows_text": _first_paragraph_value(parser.paragraphs, {"shows", "what it shows"}),
        "does_not_show_text": _first_paragraph_value(parser.paragraphs, {"does not show", "doesn't show", "what it does not show"}),
        "canonical_url": expected_canonical,
        "html_canonical_url": html_canonical,
        "html_title": html_title,
        "meta_description": meta_description,
        "og_title": og_title,
        "og_description": og_description,
        "og_url": og_url,
        "page_modified_at": modified,
        "structured_data_present": 1 if parser.jsonld else 0,
        "metadata_audit_json": json.dumps(audit, ensure_ascii=False, sort_keys=True),
        "field_states_json": json.dumps({
            "source_date_text": _field_state(source_date_text),
            "analysis_date_text": _field_state(analysis_date_text),
            "holder_text": _field_state(optional_text(holder_row["value"])),
            "repository_text": _field_state(optional_text(repository_row["value"])),
            "reference_text": _field_state(optional_text(reference_row["value"])),
            "repository_reference_text": _field_state(optional_text(combined_row["value"])),
            "access_note": _field_state(optional_text(access_row["value"])),
            "provenance_text": _field_state(optional_text(provenance_row["value"])),
        }, ensure_ascii=False, sort_keys=True),
    }

    source_text_parts = [metadata[k] for k in (
        "holder_text", "repository_text", "reference_text", "repository_reference_text",
        "access_note", "provenance_text"
    ) if metadata[k]]
    source_urls = _external_urls(
        parser, expected_canonical,
        {"repository reference", "repository", "reference", "archive reference", "source reference"}
    )
    source_ref = None
    if source_text_parts or source_urls:
        source_ref = {
            "source_ref_id": ev + ":SRC-1",
            "ev": ev,
            "seq": 1,
            "holder": metadata["holder_text"],
            "repository": metadata["repository_text"],
            "reference": metadata["reference_text"],
            "repository_reference_text": metadata["repository_reference_text"],
            "source_url": source_urls[0] if source_urls else None,
            "access_note": metadata["access_note"],
            "provenance_note": metadata["provenance_text"],
            "source_text": " | ".join(source_text_parts) or None,
        }
    return metadata, source_ref


def _valid_json(value):
    try:
        json.loads(value)
        return True
    except (TypeError, ValueError):
        return False



def ensure_catalogue_html_metadata(ev, page_path, html_text, metadata=None):
    """Add record-specific SEO metadata to generated evidence pages, preserving page content."""
    from html import escape
    metadata = metadata or {}
    canonical = CANONICAL_BASE + (page_path if page_path.startswith("/") else "/" + page_path)
    canonical = canonical.rstrip("/") + "/"
    title = optional_text(metadata.get("html_title")) or str(ev)
    description = optional_text(metadata.get("meta_description"))
    if not description:
        type_label = optional_text(metadata.get("record_type_label"))
        label = optional_text(metadata.get("evidence_label"))
        description = "Evidence catalogue record %s: %s%s. Catalogue description, source wording and interpretation are kept distinct." % (
            ev, title,
            (" — " + type_label) if type_label else ((" — " + label) if label else "")
        )
    description = re.sub(r"\s+", " ", description).strip()[:300]
    escaped_description = escape(description, quote=True)
    escaped_title = escape(title, quote=True)
    escaped_url = escape(canonical, quote=True)

    def insert_head_tag(source, tag):
        marker = re.search(r"</head\s*>", source, re.I)
        if marker:
            return source[:marker.start()] + tag + source[marker.start():]
        return source

    def upsert_meta(source, key_name, key_value, content):
        attr = re.escape(key_name)
        value = re.escape(key_value)
        pattern = re.compile(
            r"<meta\b(?=[^>]*\b" + attr + r"\s*=\s*(['\"])" + value + r"\1)[^>]*>",
            re.I
        )
        tag = '<meta %s="%s" content="%s">' % (key_name, key_value, content)
        if pattern.search(source):
            return pattern.sub(lambda _: tag, source, count=1)
        return insert_head_tag(source, tag)

    def upsert_canonical(source):
        pattern = re.compile(
            r"<link\b(?=[^>]*\brel\s*=\s*(['\"])canonical\1)[^>]*>",
            re.I
        )
        tag = '<link rel="canonical" href="%s">' % escaped_url
        if pattern.search(source):
            return pattern.sub(lambda _: tag, source, count=1)
        return insert_head_tag(source, tag)

    head_match = re.search(r"<head\b[^>]*>", html_text, re.I)
    if not head_match:
        return html_text, {"updated": False, "reason": "missing_head"}
    head_end = head_match.end()
    head = html_text[:]
    head = upsert_canonical(head)
    head = upsert_meta(head, "name", "description", escaped_description)
    head = upsert_meta(head, "property", "og:title", escaped_title)
    head = upsert_meta(head, "property", "og:description", escaped_description)
    head = upsert_meta(head, "property", "og:url", escaped_url)

    parser = _RecordParser()
    parser.feed(head)
    parser.close()
    if not parser.jsonld:
        structured = json.dumps({
            "@context": "https://schema.org",
            "@type": "CreativeWork",
            "identifier": ev,
            "name": title,
            "description": description,
            "url": canonical,
        }, ensure_ascii=False).replace("</", "<\\/")
        tag = '<script type="application/ld+json">%s</script>' % structured
        marker = re.search(r"</head\s*>", head, re.I)
        if marker:
            head = head[:marker.start()] + tag + head[marker.start():]
    updated = head != html_text
    return head, {"updated": updated, "canonical_url": canonical, "description": description}

def validate_relationship_registry(doc, known_evs):
    """Validate explicit entity and relationship records; never auto-merge names."""
    entities = doc.get("entities", [])
    relationships = doc.get("relationships", [])
    if not isinstance(entities, list) or not isinstance(relationships, list):
        raise ValueError("entities and relationships must be arrays")
    entity_ids = set()
    clean_entities = []
    for item in entities:
        entity_id = optional_text(item.get("entity_id"))
        entity_type = optional_text(item.get("entity_type"))
        name = optional_text(item.get("preferred_name"))
        disambiguator = optional_text(item.get("disambiguator"))
        if not entity_id or entity_id in entity_ids:
            raise ValueError("each entity needs a unique non-empty entity_id")
        if entity_type not in ENTITY_TYPES or not name:
            raise ValueError("entity %s needs a supported entity_type and preferred_name" % entity_id)
        if entity_type == "person" and not disambiguator:
            raise ValueError("person entity %s needs a disambiguator; never merge by surname alone" % entity_id)
        entity_kind = optional_text(item.get("entity_kind")) or "unknown"
        if entity_type == "place" and entity_kind not in PLACE_KINDS:
            raise ValueError("place entity %s has an unsupported place kind" % entity_id)
        geometry = item.get("geometry")
        label_point = item.get("label_point")
        geometry_type = optional_text(item.get("geometry_type"))
        if geometry is not None and (not item.get("crs") or not geometry_type):
            raise ValueError("spatial entity %s needs CRS and geometry_type" % entity_id)
        if geometry is not None and geometry_type not in {
            "Point", "MultiPoint", "LineString", "MultiLineString",
            "Polygon", "MultiPolygon", "GeometryCollection"
        }:
            raise ValueError("spatial entity %s has an unsupported GeoJSON geometry_type" % entity_id)
        if geometry is not None and not isinstance(geometry, (dict, list)):
            raise ValueError("geometry for %s must be a JSON object or array" % entity_id)
        uncertainty = item.get("positional_uncertainty_m")
        if uncertainty is not None and (isinstance(uncertainty, bool) or not isinstance(uncertainty, (int, float)) or uncertainty < 0):
            raise ValueError("spatial entity %s has invalid positional_uncertainty_m" % entity_id)
        if item.get("geometry_source_ev") and item.get("geometry_source_ev") not in known_evs:
            raise ValueError("spatial entity %s cites an unknown geometry_source_ev" % entity_id)
        clean_entities.append({
            "entity_id": entity_id, "entity_type": entity_type, "entity_kind": entity_kind,
            "preferred_name": name, "disambiguator": disambiguator,
            "aliases_json": json.dumps(item.get("aliases", []), ensure_ascii=False),
            "parent_entity_id": optional_text(item.get("parent_entity_id")),
            "crs": optional_text(item.get("crs")),
            "geometry_type": geometry_type,
            "geometry_json": json.dumps(geometry, ensure_ascii=False) if geometry is not None else None,
            "label_point_json": json.dumps(label_point, ensure_ascii=False) if label_point is not None else None,
            "transformation_method": optional_text(item.get("transformation_method")),
            "positional_uncertainty_m": uncertainty,
            "geometry_source_ev": optional_text(item.get("geometry_source_ev")),
            "notes": optional_text(item.get("notes")),
        })
        entity_ids.add(entity_id)

    for entity in clean_entities:
        parent_id = entity.get("parent_entity_id")
        if parent_id and parent_id not in entity_ids:
            raise ValueError("entity %s points to an unknown parent_entity_id" % entity["entity_id"])

    clean_relationships = []
    relation_ids = set()
    for item in relationships:
        rel_id = optional_text(item.get("relationship_id"))
        source_ev = optional_text(item.get("source_ev"))
        target_ev = optional_text(item.get("target_ev"))
        entity_id = optional_text(item.get("entity_id"))
        relation_type = optional_text(item.get("relation_type"))
        basis = optional_text(item.get("assertion_basis")) or "unknown"
        verification = optional_text(item.get("verification_state")) or "not_assessed"
        if not rel_id or rel_id in relation_ids or source_ev not in known_evs:
            raise ValueError("relationship needs a unique ID and a known source_ev")
        if bool(target_ev) == bool(entity_id):
            raise ValueError("relationship %s must name exactly one target_ev or entity_id" % rel_id)
        if target_ev and target_ev not in known_evs:
            raise ValueError("relationship %s points to an unknown target_ev" % rel_id)
        if entity_id and entity_id not in entity_ids:
            raise ValueError("relationship %s points to an unknown entity_id" % rel_id)
        if relation_type not in RELATION_TYPES or basis not in ASSERTION_BASES or verification not in VERIFICATION_STATES:
            raise ValueError("relationship %s has an uncontrolled relation, assertion basis or verification state" % rel_id)
        clean_relationships.append({
            "relationship_id": rel_id, "source_ev": source_ev, "target_ev": target_ev,
            "entity_id": entity_id, "relation_type": relation_type,
            "role": optional_text(item.get("role")),
            "date_start": optional_text(item.get("date_start")),
            "date_end": optional_text(item.get("date_end")),
            "date_precision": optional_text(item.get("date_precision")) or "unknown",
            "assertion_basis": basis,
            "assertion_text": optional_text(item.get("assertion_text")),
            "verification_state": verification,
            "source_note": optional_text(item.get("source_note")),
        })
        relation_ids.add(rel_id)
    return clean_entities, clean_relationships
