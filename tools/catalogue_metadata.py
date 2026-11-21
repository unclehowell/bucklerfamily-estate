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
import math
import re


CANONICAL_BASE = "https://bucklerfamily.estate"
ENTITY_TYPES = {"person", "place", "organization", "institution", "legal_body", "document", "observation", "analysis"}
PLACE_KINDS = {"parish", "manor", "farm", "church", "parcel", "landscape", "building", "other", "unknown"}
RELATION_TYPES = {
    "owned_by", "occupied_by", "tenanted_by", "patron_of", "rector_of",
    "located_in", "part_of", "depicts", "transcribes", "analyses",
    "derived_from", "cites", "cited_in", "catalogued_as", "records_name_for_place",
    "lists_tenant", "lists_occupier", "lists_landowner", "lists_ratepayer", "reports_resident",
    "records_juror", "recites_tenant", "lists_lessee", "records_pleading_party",
    "addresses_correspondence_to", "records_death_of", "names_as_rent_payee",
    "mentions", "same_source_as", "transferred_from", "transferred_to",
    "names_seller", "names_buyer", "names_transferor", "names_transferee",
    "grants_rights_to", "other",
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
    """Return date bounds with source precision; never manufacture missing components."""
    raw = optional_text(value)
    empty = {"date_start": None, "date_end": None, "date_precision": "unknown", "date_sort": None}
    if not raw:
        return empty
    s = raw.replace("–", "-").replace("—", "-").replace("−", "-")
    s = re.sub(r"\s+", " ", s).strip()

    months = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
        "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
        "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
        "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
    }
    month_pattern = "(?:" + "|".join(sorted(months, key=len, reverse=True)) + ")"

    approximate = re.fullmatch(r"(?:c(?:irca)?\.?|ca\.?|about|approximately)\s*(\d{4})", s, re.I)
    if approximate and _valid_year(approximate.group(1)):
        year = approximate.group(1)
        return {"date_start": year, "date_end": None, "date_precision": "approximate", "date_sort": year}

    # Explicit full-date ranges: 17 May - 23 Dec 1938 or 17-23 May 1938.
    m = re.fullmatch(r"(\d{1,2})\s+(" + month_pattern + r")\s*-\s*(\d{1,2})\s+(" + month_pattern + r")\s+(\d{4})", s, re.I)
    if m and _valid_year(m.group(5)):
        try:
            start = date(int(m.group(5)), months[m.group(2).lower()], int(m.group(1)))
            end = date(int(m.group(5)), months[m.group(4).lower()], int(m.group(3)))
            if start <= end:
                return {"date_start": start.isoformat(), "date_end": end.isoformat(),
                        "date_precision": "range", "date_sort": start.isoformat()}
        except ValueError:
            pass

    m = re.fullmatch(r"(\d{1,2})\s*-\s*(\d{1,2})\s+(" + month_pattern + r")\s+(\d{4})", s, re.I)
    if m and _valid_year(m.group(4)):
        try:
            start = date(int(m.group(4)), months[m.group(3).lower()], int(m.group(1)))
            end = date(int(m.group(4)), months[m.group(3).lower()], int(m.group(2)))
            if start <= end:
                return {"date_start": start.isoformat(), "date_end": end.isoformat(),
                        "date_precision": "range", "date_sort": start.isoformat()}
        except ValueError:
            pass

    # Month ranges: Nov 1982 - Feb 1983.
    m = re.fullmatch(r"(" + month_pattern + r")\s+(\d{4})\s*-\s*(" + month_pattern + r")\s+(\d{4})", s, re.I)
    if m and _valid_year(m.group(2)) and _valid_year(m.group(4)):
        start = "%04d-%02d" % (int(m.group(2)), months[m.group(1).lower()])
        end = "%04d-%02d" % (int(m.group(4)), months[m.group(3).lower()])
        if start <= end:
            return {"date_start": start, "date_end": end, "date_precision": "range", "date_sort": start}

    # Valid ISO day/month, and conventional written day/month dates.
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


class _VisibleBodyTextParser(HTMLParser):
    """Collect visible body text, excluding head, scripts, styles and hidden templates."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.skip_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "body":
            self.in_body = True
        if self.in_body and tag in {"script", "style", "noscript", "template"}:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.in_body and tag in {"script", "style", "noscript", "template"} and self.skip_depth:
            self.skip_depth -= 1
        if tag == "body":
            self.in_body = False

    def handle_data(self, data):
        if self.in_body and not self.skip_depth:
            self.parts.append(data)


def visible_body_text_length(html_text):
    parser = _VisibleBodyTextParser()
    parser.feed(html_text or "")
    parser.close()
    return len(re.sub(r"\s+", " ", " ".join(parser.parts)).strip())


def _row(parser, *labels):
    for label in labels:
        key = re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()
        if key in parser.rows:
            return parser.rows[key]
    return {"value": None, "links": []}


def _record_type(label):
    """Classify documentary content, never the digital file format or evidence grade."""
    if not label:
        return "unknown"
    s = re.sub(r"\s+", " ", label.lower()).strip()
    if "law" in s and ("note" in s or "analysis" in s or "research" in s):
        return "legal_analysis"
    if "legislation" in s or "enacted text" in s or "statute" in s:
        return "legislation"
    kinds = []
    checks = [
        ("archival_catalogue", ("catalogue", "administrative history")),
        ("court_judgment", ("judgment", "judgement")),
        ("press_report", ("press", "newspaper")),
        ("manorial_record_group", ("manorial", "court leet", "court baron")),
        ("correspondence", ("correspondence", "letter", "email")),
        ("deed_or_conveyance", ("deed", "conveyance", "instrument")),
        ("cartographic_record", ("map", "plan", "survey", "tithe apportionment")),
        ("photograph", ("photograph", "photo")),
        ("research_analysis", ("analysis", "research artifact", "research analysis", "analysis table")),
        ("testimony", ("testimony", "witness", "family account")),
        ("press_report", ("press report", "newspaper report")),
    ]
    for code, terms in checks:
        if any(term in s for term in terms) and code not in kinds:
            kinds.append(code)
    if len(kinds) > 1:
        return "composite_record"
    if kinds:
        return kinds[0]
    if "record" in s:
        return "published_record"
    if "law" in s or "legal" in s:
        return "legal_reference"
    return "other"


def _states(status, evidence_label, access_note=None):
    s = (status or "").lower()
    label = (evidence_label or "").lower()
    access_text = (access_note or "").lower()
    combined = s + " " + label
    # Access is a separate dimension. Only the access field or an explicit
    # legacy paywall/appointment/restriction phrase can populate it.
    access_combined = access_text
    if not access_combined or access_combined in {"unknown", "pending", "not stated"}:
        if re.search(r"\bpaywall(?:ed)?\b|\bappointment required\b|\brestricted access\b|\baccess restricted\b|\bopen access\b|\bonline only\b|\breading room access\b", combined):
            access_combined = combined

    if re.search(r"\bnot located\b|\bnot found\b|\bunable to locate\b|\bcould not locate\b", combined):
        availability = "not_located"
    elif re.search(r"\breference located\b|\breference found\b|\bcatalogue entry located\b|\bcatalogue reference found\b", combined):
        availability = "reference_located"
    elif re.search(r"\bpartly held\b|\bpartially held\b", combined):
        availability = "partly_held"
    elif re.search(r"\bnot held\b|\bno copy\b|\bnot in custody\b|\bunavailable\b", combined):
        availability = "unavailable"
    elif re.search(r"\bcopy held\b|\bheld\b", combined):
        availability = "copy_held"
    else:
        availability = "unknown"

    if re.search(r"\bcatalogue[- ]only\b", combined) or ("catalogue text" in combined and re.search(r"\bread\b|\bentries read\b", combined)):
        inspection = "catalogue_only"
    elif re.search(r"\bsearch[- ]result text\b|\bsearch results text\b|\bsearch-result transcript\b", combined):
        inspection = "search_result_only"
    elif re.search(r"\bpartly read\b|\bpartially read\b", combined):
        inspection = "partly_read"
    elif re.search(r"\bnot yet seen\b|\bnot inspected\b|\bnot seen\b|\boriginal (?:document|instrument|image|page) not seen\b", combined):
        inspection = "not_inspected"
    elif re.search(r"\bocr text\b|\btranscription only\b|\btranscribed text\b", combined) and re.search(r"\bimage not seen\b|\bpage image not seen\b|\boriginal not seen\b|\bnot checked\b", combined):
        inspection = "transcription_only"
    elif re.match(r"^\s*read\b", s) or s.strip() == "read":
        inspection = "read_in_full"
    else:
        inspection = "unknown"

    if re.search(r"\bnot verified\b|\bnot independently verified\b|\bnot verified independently\b", combined):
        verification = "unverified"
    elif "provisional" in combined or "working" in combined:
        verification = "provisional"
    elif re.search(r"\bverified\b|\bconfirmed\b", combined):
        verification = "verified"
    else:
        verification = "unknown"

    if "paywall" in access_combined or "paywalled" in access_combined:
        access = "paywalled"
    elif "appointment" in access_combined:
        access = "appointment_required"
    elif "restricted" in access_combined or "closed to the public" in access_combined:
        access = "restricted"
    elif re.search(r"\bview(?:ed)?(?:\s+free)?\s+at\b|\bconsult at\b|\breading room\b|\bin person\b", access_combined):
        access = "on_site"
    elif re.search(r"\bopen access\b|\bfreely available online\b|\bview free online\b|\bdownload free\b|\bpublicly accessible online\b", access_combined):
        access = "open"
    elif re.search(r"\bonline only\b|\bonline access\b|\bavailable online\b|\bweb access\b", access_combined):
        access = "online"
    else:
        access = "unknown"

    if re.search(r"\bnot complete\b|\bincomplete\b|\bpartial(?:ly)?\b|\bpartly\b|\btruncated\b", combined):
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
    if re.search(r"\bwithheld\b|\bredacted\b", text):
        return "withheld"
    if re.search(r"\bnot applicable\b|\bn/?a\b", text):
        return "not_applicable"
    if re.search(r"\bunknown\b|\bnot known\b|\bnot recorded\b|\bnot stated\b", text):
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
    summary_row = _row(parser, "summary", "catalogue summary", "public summary")
    shows_row = _row(parser, "shows", "what it shows")
    does_not_show_row = _row(parser, "does not show", "doesn't show", "what it does not show")
    analysis_row = _row(parser, "analysis date", "date of analysis")
    updated_row = _row(parser, "updated at", "last updated", "page modified")

    source_date_text = optional_text(date_row["value"])
    parsed_date = parse_date_range(source_date_text)
    summary_text = optional_text(summary_row["value"]) or _first_paragraph_value(parser.paragraphs, {"summary", "catalogue summary", "public summary"})
    shows_text = optional_text(shows_row["value"]) or _first_paragraph_value(parser.paragraphs, {"shows", "what it shows"})
    does_not_show_text = optional_text(does_not_show_row["value"]) or _first_paragraph_value(parser.paragraphs, {"does not show", "doesn't show", "what it does not show"})
    type_label = optional_text(type_row["value"])
    evidence_label = optional_text(label_row["value"])
    status_text = optional_text(status_row["value"])
    availability, inspection, verification, access, completeness = _states(status_text, evidence_label, optional_text(access_row["value"]))

    page_path = page_path if page_path.startswith("/") else "/" + page_path
    if not page_path.endswith("/"):
        page_path += "/"
    expected_canonical = CANONICAL_BASE + page_path
    html_canonical = optional_text(parser.canonical)
    if html_canonical:
        canonical_parts = urlparse(html_canonical)
        base_parts = urlparse(CANONICAL_BASE)
        if canonical_parts.scheme == base_parts.scheme and canonical_parts.netloc == base_parts.netloc and canonical_parts.path:
            expected_canonical = html_canonical
    html_title = optional_text("".join(parser.title))
    meta_description = optional_text(parser.meta.get("description"))
    og_title = optional_text(parser.meta.get("og:title"))
    og_description = optional_text(parser.meta.get("og:description"))
    og_url = optional_text(parser.meta.get("og:url"))
    modified = optional_text(parser.meta.get("article:modified_time") or parser.meta.get("og:updated_time") or parser.meta.get("last-modified")) or optional_text(updated_row["value"])
    source_date_text = source_date_text
    analysis_date_text = optional_text(analysis_row["value"])
    def structured_matches(value):
        if isinstance(value, list):
            return any(structured_matches(item) for item in value)
        if not isinstance(value, dict):
            return False
        if value.get("identifier") == ev or value.get("@id") == expected_canonical:
            return True
        if value.get("url") == expected_canonical and value.get("name") == html_title:
            return True
        return structured_matches(value.get("@graph")) if value.get("@graph") is not None else False

    structured_matches_record = False
    for payload in parser.jsonld:
        try:
            if structured_matches(json.loads(payload)):
                structured_matches_record = True
                break
        except (TypeError, ValueError):
            pass

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
        "server_rendered_text_present": visible_body_text_length(html_text) > 500,
        "structured_data_present": bool(parser.jsonld),
        "structured_data_valid": all(_valid_json(x) for x in parser.jsonld) if parser.jsonld else False,
        "structured_data_matches_record": structured_matches_record,
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
        "summary_text": summary_text,
        "shows_text": shows_text,
        "does_not_show_text": does_not_show_text,
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
            "summary_text": _field_state(summary_text),
            "shows_text": _field_state(shows_text),
            "does_not_show_text": _field_state(does_not_show_text),
            "record_type_label": _field_state(type_label),
            "evidence_label": _field_state(evidence_label),
            "status_text": _field_state(status_text),
        }, ensure_ascii=False, sort_keys=True),
    }

    source_text_parts = [metadata[k] for k in (
        "holder_text", "repository_text", "reference_text", "repository_reference_text",
        "access_note", "provenance_text"
    ) if metadata[k]]
    source_urls = _external_urls(
        parser, expected_canonical,
        {"holder", "repository", "repository reference", "reference", "archive reference", "source reference", "provenance", "source provenance"}
    )
    source_refs = []
    if source_text_parts or source_urls:
        for index, source_url in enumerate(source_urls or [None], start=1):
            source_refs.append({
                "source_ref_id": "%s:SRC-%03d" % (ev, index),
                "ev": ev,
                "seq": index,
                "holder": metadata["holder_text"],
                "repository": metadata["repository_text"],
                "reference": metadata["reference_text"],
                "repository_reference_text": metadata["repository_reference_text"],
                "source_url": source_url,
                "access_note": metadata["access_note"],
                "provenance_note": metadata["provenance_text"],
                "source_text": " | ".join(source_text_parts) or None,
            })
    return metadata, source_refs


def _valid_json(value):
    try:
        json.loads(value)
        return True
    except (TypeError, ValueError):
        return False



def ensure_evidence_alias_redirects(dist_path, page_candidates):
    """301 duplicate Wiki EV routes to their Research canonical route where both exist."""
    dist_path = Path(dist_path)
    redirect_file = dist_path / "_redirects"
    existing_lines = redirect_file.read_text("utf-8").splitlines() if redirect_file.is_file() else []
    existing_sources = set()
    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) >= 2:
            existing_sources.add(parts[0].casefold())

    new_rules = []
    for _ev, candidates in sorted(page_candidates.items()):
        research = [item for item in candidates if item[0] == 0]
        wiki = [item for item in candidates if item[0] == 1]
        if not research or not wiki:
            continue
        target_relative = min(research, key=lambda item: item[1])[1]
        target = "/" + target_relative.lstrip("/")
        target = target.rsplit("/index.html", 1)[0].rstrip("/") + "/"
        for _priority, relative_path, _page_file in wiki:
            source = "/" + relative_path.lstrip("/")
            source = source.rsplit("/index.html", 1)[0].rstrip("/") + "/"
            if source == target or source.casefold() in existing_sources:
                continue
            if not source.startswith("/wiki/evidence/") or not target.startswith("/research/evidence/"):
                continue
            new_rules.append("%s %s 301" % (source, target))

    if new_rules:
        # Exact route rules precede broad existing rules; existing rules are preserved.
        redirect_file.write_text("\n".join(new_rules + existing_lines).rstrip() + "\n", encoding="utf-8")
    return new_rules


def ensure_catalogue_html_metadata(ev, page_path, html_text, metadata=None):
    """Add record-specific SEO metadata to generated evidence pages, preserving page content."""
    from html import escape
    metadata = metadata or {}
    canonical = CANONICAL_BASE + (page_path if page_path.startswith("/") else "/" + page_path)
    canonical = canonical.rstrip("/") + "/"
    requested_canonical = optional_text(metadata.get("canonical_url"))
    if requested_canonical:
        requested_parts = urlparse(requested_canonical)
        base_parts = urlparse(CANONICAL_BASE)
        if requested_parts.scheme == base_parts.scheme and requested_parts.netloc == base_parts.netloc and requested_parts.path:
            canonical = requested_canonical.rstrip("/") + "/"
    title = optional_text(metadata.get("html_title")) or "Evidence catalogue record"
    if str(ev).lower() not in title.lower():
        title = str(ev) + " — " + title
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
    title_pattern = re.compile(r"<title\b[^>]*>.*?</title\s*>", re.I | re.S)
    title_tag = "<title>%s</title>" % escaped_title
    if title_pattern.search(head):
        head = title_pattern.sub(lambda _: title_tag, head, count=1)
    else:
        head = insert_head_tag(head, title_tag)
    head = upsert_canonical(head)
    head = upsert_meta(head, "name", "description", escaped_description)
    head = upsert_meta(head, "property", "og:title", escaped_title)
    head = upsert_meta(head, "property", "og:description", escaped_description)
    head = upsert_meta(head, "property", "og:url", escaped_url)

    parser = _RecordParser()
    parser.feed(head)
    parser.close()

    def matches_record(value):
        if isinstance(value, list):
            return any(matches_record(item) for item in value)
        if not isinstance(value, dict):
            return False
        if value.get("identifier") == ev or value.get("@id") == canonical:
            return True
        if value.get("url") == canonical and value.get("name") == title:
            return True
        graph = value.get("@graph")
        return matches_record(graph) if graph is not None else False

    record_schema_present = False
    for payload in parser.jsonld:
        try:
            if matches_record(json.loads(payload)):
                record_schema_present = True
                break
        except (TypeError, ValueError):
            pass
    if not record_schema_present:
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

def _valid_position(value):
    return (
        isinstance(value, list) and len(value) in (2, 3) and
        all(
            not isinstance(part, bool) and isinstance(part, (int, float)) and math.isfinite(float(part))
            for part in value
        )
    )


def _valid_line(value):
    return isinstance(value, list) and len(value) >= 2 and all(_valid_position(p) for p in value)


def _valid_polygon(value):
    if not isinstance(value, list) or not value:
        return False
    for ring in value:
        if not isinstance(ring, list) or len(ring) < 4:
            return False
        if not all(_valid_position(p) for p in ring) or ring[0] != ring[-1]:
            return False
    return True


def _valid_geojson_geometry(value, expected_type=None):
    if not isinstance(value, dict):
        return False
    geometry_type = value.get("type")
    if expected_type and geometry_type != expected_type:
        return False
    coordinates = value.get("coordinates")
    if geometry_type == "Point":
        return _valid_position(coordinates)
    if geometry_type == "MultiPoint":
        return isinstance(coordinates, list) and bool(coordinates) and all(_valid_position(p) for p in coordinates)
    if geometry_type == "LineString":
        return _valid_line(coordinates)
    if geometry_type == "MultiLineString":
        return isinstance(coordinates, list) and bool(coordinates) and all(_valid_line(line) for line in coordinates)
    if geometry_type == "Polygon":
        return _valid_polygon(coordinates)
    if geometry_type == "MultiPolygon":
        return isinstance(coordinates, list) and bool(coordinates) and all(_valid_polygon(poly) for poly in coordinates)
    if geometry_type == "GeometryCollection":
        geometries = value.get("geometries")
        return isinstance(geometries, list) and bool(geometries) and all(
            _valid_geojson_geometry(geometry) for geometry in geometries
        )
    return False


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
        has_spatial_data = geometry is not None or label_point is not None
        if has_spatial_data and (not optional_text(item.get("crs"))):
            raise ValueError("spatial entity %s needs a declared CRS" % entity_id)
        if has_spatial_data and not optional_text(item.get("transformation_method")):
            raise ValueError("spatial entity %s needs an explicit transformation_method (use 'none' if untransformed)" % entity_id)
        if has_spatial_data and "positional_uncertainty_m" not in item:
            raise ValueError("spatial entity %s must state positional_uncertainty_m; use null when unknown" % entity_id)
        if has_spatial_data and (not item.get("geometry_source_ev") or item.get("geometry_source_ev") not in known_evs):
            raise ValueError("spatial entity %s needs a known geometry_source_ev" % entity_id)
        if geometry is not None:
            if geometry_type not in {
                "Point", "MultiPoint", "LineString", "MultiLineString",
                "Polygon", "MultiPolygon", "GeometryCollection"
            }:
                raise ValueError("spatial entity %s has an unsupported GeoJSON geometry_type" % entity_id)
            if not _valid_geojson_geometry(geometry, geometry_type):
                raise ValueError("spatial entity %s has invalid GeoJSON geometry or type mismatch" % entity_id)
        if label_point is not None and not _valid_geojson_geometry(label_point, "Point"):
            raise ValueError("spatial entity %s label_point must be a valid GeoJSON Point, separate from its boundary geometry" % entity_id)
        uncertainty = item.get("positional_uncertainty_m")
        if uncertainty is not None and (
            isinstance(uncertainty, bool) or not isinstance(uncertainty, (int, float)) or
            not math.isfinite(float(uncertainty)) or uncertainty < 0
        ):
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
        date_precision = optional_text(item.get("date_precision")) or "unknown"
        if date_precision not in {"day", "month", "year", "year_range", "approximate", "unknown", "unparsed"}:
            raise ValueError("relationship %s has an uncontrolled date_precision" % rel_id)
        assertion_text = optional_text(item.get("assertion_text"))
        source_note = optional_text(item.get("source_note"))
        if not assertion_text and not source_note:
            raise ValueError("relationship %s needs assertion_text or a source_note pinpointing its evidence" % rel_id)
        if relation_type not in RELATION_TYPES or basis not in ASSERTION_BASES or verification not in VERIFICATION_STATES:
            raise ValueError("relationship %s has an uncontrolled relation, assertion basis or verification state" % rel_id)
        clean_relationships.append({
            "relationship_id": rel_id, "source_ev": source_ev, "target_ev": target_ev,
            "entity_id": entity_id, "relation_type": relation_type,
            "role": optional_text(item.get("role")),
            "date_start": optional_text(item.get("date_start")),
            "date_end": optional_text(item.get("date_end")),
            "date_precision": date_precision,
            "assertion_basis": basis,
            "assertion_text": assertion_text,
            "verification_state": verification,
            "source_note": source_note,
        })
        relation_ids.add(rel_id)
    return clean_entities, clean_relationships
