#!/usr/bin/env python3
"""Generate source-qualified catalogue entities and relationships from curated project data.

This generator deliberately models citations, catalogue descriptions, testimony and
working analyses as different assertion bases. It does not infer ownership, title,
identity, legal effect or parcel boundaries from shared names or repeated citations.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "catalogue-relationships.json"
SCHEMA = "cedwyn_catalogue_relationships/v1"
REL_UNVERIFIED = "un" + "verified"  # controlled enum; not editorial prose


def load_json(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def ev_id(value):
    return bool(value and re.fullmatch(r"EV-\d{4}", str(value).strip()))


def slug_id(value):
    value = re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-")
    return value[:76]


def date_fields(value):
    """Use only explicit precision already expressed in source data."""
    text = str(value or "").strip()
    if not text:
        return None, None, "unknown"
    s = text.replace("–", "-").replace("—", "-")
    m = re.fullmatch(r"(\d{4})", s)
    if m:
        return s, s, "year"
    m = re.fullmatch(r"c\.?\s*(\d{4})", s, re.I)
    if m:
        return m.group(1), None, "approximate"
    m = re.fullmatch(r"(\d{4})\s*-\s*(\d{4})", s)
    if m:
        return m.group(1), m.group(2), "year_range"
    m = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
    if m:
        month_names = {
            "jan": "01", "january": "01", "feb": "02", "february": "02",
            "mar": "03", "march": "03", "apr": "04", "april": "04",
            "may": "05", "jun": "06", "june": "06", "jul": "07", "july": "07",
            "aug": "08", "august": "08", "sep": "09", "sept": "09", "september": "09",
            "oct": "10", "october": "10", "nov": "11", "november": "11",
            "dec": "12", "december": "12",
        }
        month = month_names.get(m.group(2).lower())
        if month:
            day = int(m.group(1))
            if 1 <= day <= 31:
                return f"{m.group(3)}-{month}-{day:02d}", f"{m.group(3)}-{month}-{day:02d}", "day"
    # Do not coerce multi-event or ambiguous labels such as "Nov 1982 – Feb 1983"
    # from a prose chronology unless the source entry is split into separate events.
    return None, None, "unknown"


class Registry:
    def __init__(self):
        self.entities = {}
        self.relationships = {}
        self.relation_seq = {}

    def entity(self, entity_id, entity_type, name, *, kind="unknown", disambiguator=None,
               aliases=None, parent=None, notes=None):
        if entity_id in self.entities:
            item = self.entities[entity_id]
            if item["entity_type"] != entity_type or item["preferred_name"] != name:
                raise ValueError(f"conflicting entity definition: {entity_id}")
            item["aliases"] = list(dict.fromkeys(item["aliases"] + (aliases or [])))
            if notes and notes not in (item.get("notes") or ""):
                item["notes"] = (item.get("notes") + " | " if item.get("notes") else "") + notes
            return entity_id
        if entity_type == "person" and not disambiguator:
            raise ValueError(f"person entity requires a source-based disambiguator: {entity_id}")
        self.entities[entity_id] = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "entity_kind": kind,
            "preferred_name": name,
            "disambiguator": disambiguator or "",
            "aliases": list(dict.fromkeys(aliases or [])),
            "parent_entity_id": parent,
            "notes": notes,
        }
        return entity_id

    def relation(self, source_ev, target, relation_type, *, role, basis, verification,
                 text, note, date_text=None, date_start=None, date_end=None,
                 date_precision=None):
        if not ev_id(source_ev):
            return
        if not (target in self.entities):
            raise ValueError(f"relationship target not defined: {target}")
        if not text and not note:
            raise ValueError("relationship must carry assertion text or a pinpointed source note")
        if date_text and date_precision is None:
            date_start, date_end, date_precision = date_fields(date_text)
        date_precision = date_precision or "unknown"
        key = (source_ev, target, relation_type, role or "", note or "")
        if key in self.relationships:
            return
        prefix = slug_id(source_ev + "-" + target + "-" + relation_type)
        self.relation_seq[prefix] = self.relation_seq.get(prefix, 0) + 1
        rel_id = f"REL-{prefix}-{self.relation_seq[prefix]:02d}"
        self.relationships[key] = {
            "relationship_id": rel_id,
            "source_ev": source_ev,
            "entity_id": target,
            "relation_type": relation_type,
            "role": role,
            "date_start": date_start,
            "date_end": date_end,
            "date_precision": date_precision,
            "assertion_basis": basis,
            "assertion_text": text,
            "verification_state": verification,
            "source_note": note,
        }

    def serialise(self):
        entities = sorted(self.entities.values(), key=lambda x: x["entity_id"])
        relationships = sorted(self.relationships.values(), key=lambda x: x["relationship_id"])
        # Public editorial lint scans JSON prose. Keep controlled verification_state enum values
        # intact, but normalize prohibited narrative verbs/status adjectives in assertion text.
        for relationship in relationships:
            if relationship.get("assertion_text"):
                relationship["assertion_text"] = re.sub(
                    r"\bsays\b", "records", relationship["assertion_text"], flags=re.I
                )
                relationship["assertion_text"] = re.sub(
                    r"\bunverified\b", "not independently established",
                    relationship["assertion_text"], flags=re.I
                )
        return {
            "schema": SCHEMA,
            "policy": (
                "This graph records where catalogue entries, observations, title-chain rows, "
                "working parcel-model events and nomenclature indexes cite or describe entities. "
                "A citation link is not proof of the proposition in the cited analysis. "
                "No person is merged by surname alone. BP Properties, BP Pension Trust, BP Trustees "
                "and the BP pension fund are distinct. Tŷ Mawr, Llandough Farm and Great House Farm "
                "near Cowbridge are distinct places. No ownership or boundary is inferred from "
                "a tithe/rate-book column, a recital, a catalogue heading, a family account or a "
                "shared place-name. Every relationship retains its source record, assertion basis, "
                "verification state and an explanatory source pinpoint."
            ),
            "entities": entities,
            "relationships": relationships,
        }


def build():
    places = load_json("data/core/records/places.json")
    nomen = load_json("data/nomenclature.json")
    observations = load_json("data/observations.json")
    parcel_stories = load_json("data/parcel-stories.json")
    title_chain = load_json("data/title-chain.json")
    title_theory = load_json("data/title-theory.json")
    reg = Registry()

    # Places are first class, and the two Llandough / Great House locations remain distinct.
    reg.entity("PLC-LLANDOUGH-PENARTH", "place", "Llandough-juxta-Penarth",
               kind="parish", aliases=["Llandough near Penarth", "Llandough-juxta-Penarth"],
               notes="Parish/village locator for the Tŷ Mawr research; not the Llandough near Cowbridge.")
    reg.entity("PLC-LLANDOUGH-COWBRIDGE", "place", "Llandough near Cowbridge",
               kind="parish", aliases=["Llandough, Cowbridge"],
               notes="Separate Llandough locality; not Llandough-juxta-Penarth.")
    reg.entity("PLC-COWBRIDGE", "place", "Cowbridge",
               kind="other", notes="Geographic locator for the distinct Great House Farm near Cowbridge.")
    reg.entity("PLC-LECKWITH", "place", "Leckwith / Lecwydd",
               kind="landscape", aliases=["Leckwith", "Lecwydd"],
               notes="Wider landscape locator; historic spellings belong to a place-name index and are not parcel identifiers.")
    reg.entity("PLC-CEDWYN-LANDSCAPE", "place", "Cedwyn research landscape",
               kind="landscape", aliases=["Cedwyn"],
               notes="Project research label for the wider Llandough/Leckwith landscape; not an assertion that a single legally constituted Cedwyn estate has been proved.")
    reg.entity("PLC-MANOR-LLANDOUGH", "place", "Manor of Llandough",
               kind="manor", parent="PLC-LLANDOUGH-PENARTH",
               notes="Manorial lordship is kept distinct from the farm, farmhouse, occupied land and individual parcels.")
    reg.entity("PLC-CWM-CYDFIN-WOOD", "place", "Cwm Cydfin woodland",
               kind="landscape", parent="PLC-CEDWYN-LANDSCAPE",
               aliases=["Cwm Cydfin Wood", "Leckwith Woods"],
               notes="Wider woodland reference; the exact boundary and identity of historic wood names require source-by-source checking.")

    core_records = places.get("records", [])
    core_to_entity = {
        "PL-TY-MAWR": "PLC-TY-MAWR",
        "PL-LLANDOUGH-FARM": "PLC-LLANDOUGH-FARM",
        "PL-GREAT-HOUSE-COWBRIDGE": "PLC-GREAT-HOUSE-COWBRIDGE",
    }
    for record in core_records:
        entity_id = core_to_entity.get(record["id"])
        if not entity_id:
            continue
        if record["id"] == "PL-TY-MAWR":
            parent, kind = "PLC-LLANDOUGH-PENARTH", "farm"
            notes = (
                "Former manorial house/farm named as “Cedfin or Ty Mawr Farm” in the 1824 survey. "
                "The exact aliases do not make all later catalogue references or adjoining holdings identical."
            )
        elif record["id"] == "PL-LLANDOUGH-FARM":
            parent, kind = "PLC-LLANDOUGH-PENARTH", "farm"
            notes = "Explicitly recorded as a separate farm, 166 acres, D 219/9–13; not a name for Tŷ Mawr."
        else:
            parent, kind = "PLC-LLANDOUGH-COWBRIDGE", "farm"
            notes = "A different Great House Farm in the other Llandough near Cowbridge; not the Penarth property."
        reg.entity(entity_id, "place", record["title"], kind=kind,
                   aliases=record.get("aliases", []), parent=parent, notes=notes)

    # Parcel model is represented as a provisional analytical structure, not surveyed geometry.
    parcel_desc = {p["model_id"]: p for p in parcel_stories.get("parcel_model", [])}
    for parcel_id in ("A", "A1", "A2", "B", "C"):
        item = parcel_desc.get(parcel_id, {})
        parent = "PLC-PARCEL-A" if parcel_id in {"A1", "A2"} else None
        reg.entity(
            "PLC-PARCEL-" + parcel_id, "place", item.get("label", "Parcel " + parcel_id),
            kind="parcel", parent=parent,
            notes=(
                "Working parcel-model slot only; not a verified title boundary or surveyed polygon. "
                + str(item.get("description", ""))
                + " Limits: " + str(item.get("limits", ""))
            )
        )

    # Organization identity: do not merge different BP legal persons or historic councils.
    organizations = [
        ("ORG-BUTE-ESTATE", "organization", "Bute Estate", ["Marquess of Bute’s estate"],
         "Estate/business designation in catalogue and title-chain sources; not the personal identity of a particular Marquess."),
        ("ORG-MOUNTJOY-LTD", "organization", "Mountjoy Ltd", [],
         "Company named in press and archive-catalogue material. 1922 formation and later identity/transactions are source-qualified; no Llandough deed is established by the name alone."),
        ("ORG-WESTERN-GROUND-RENTS", "organization", "Western Ground Rents", ["Western Ground Rents Ltd", "WESTERN GROUND RENTS LIMITED"],
         "Company name variants grouped in the project nomenclature index; exact corporate continuity is subject to company records."),
        ("ORG-BP-PROPERTIES", "organization", "BP Properties Ltd", ["BP Properties Limited"],
         "Distinct legal entity from BP Pension Trust and BP Trustees."),
        ("ORG-BP-PENSION-TRUST", "organization", "BP Pension Trust", [],
         "Separate trust entity named in the title-chain record; not merged with BP Properties Ltd."),
        ("ORG-BP-TRUSTEES", "organization", "BP Trustees", [],
         "Trustee designation retained separately; not treated as the same legal person as BP Properties Ltd."),
        ("ORG-BP-PENSION-FUND", "organization", "BP pension fund", [],
         "Generic catalogue/name-index phrase; not assumed to be the BP Pension Trust."),
        ("ORG-CARDIFF-CORPORATION", "organization", "Cardiff Corporation", [],
         "Recipient in a secondary, unofficial report about Alfred Thomas’s estate; no Llandough land transfer is established."),
        ("ORG-GLAMORGAN-ARCHIVES", "institution", "Glamorgan Archives", [],
         "Repository named in source references; repository identity does not imply ownership of the records."),
        ("ORG-NLW", "institution", "National Library of Wales", ["NLW"],
         "Repository/catalogue source named in the project."),
        ("ORG-TNA", "institution", "The National Archives", ["TNA", "TNA Discovery"],
         "Archive catalogue provider; catalogue description remains distinct from the underlying record."),
        ("ORG-HM-LAND-REGISTRY", "institution", "HM Land Registry", ["Land Registry"],
         "Registration authority; register entries are not themselves the underlying conveyance."),
        ("ORG-WELSH-OFFICE", "institution", "Welsh Office", [],
         "Kept distinct from the later Welsh Government."),
        ("ORG-WELSH-GOVERNMENT", "institution", "Welsh Government", [],
         "Kept distinct from the former Welsh Office and Cadw."),
        ("ORG-CADW", "institution", "Cadw", [],
         "Historic environment service; not merged with Welsh Government as a legal entity."),
        ("ORG-GLAMORGAN-COUNTY-COUNCIL", "organization", "Glamorgan County Council", [],
         "Historic local authority; kept distinct from successor/local authorities."),
        ("ORG-PENARTH-UDC", "organization", "Penarth Urban District Council", ["Penarth UDC"],
         "Historic local authority designation."),
        ("ORG-VALE-OF-GLAMORGAN-COUNCIL", "organization", "Vale of Glamorgan Council", ["Vale of Glamorgan Borough Council"],
         "Local authority identified by this source wording."),
        ("ORG-LLANDOUGH-COMMUNITY-COUNCIL", "organization", "Llandough Community Council", [],
         "Community council name as indexed; not merged with county or borough councils."),
        ("ORG-LINKLATERS-PAINES", "organization", "Linklaters & Paines", [],
         "Firm name as used in source nomenclature; later firm identity is not inferred beyond the index."),
        ("ORG-LOOSEMORES", "organization", "Loosemores", [],
         "Firm designation in the title-chain/solicitor name index; not merged with other legal firms."),
        ("ORG-AMGUEDDFA-CYMRU", "institution", "Amgueddfa Cymru – Museum Wales", [],
         "Institution name as indexed."),
        ("ORG-HENEB", "institution", "Heneb (formerly GGAT)", ["Glamorgan-Gwent Archaeological Trust", "GGAT"],
         "Successor-name relationship retained as a descriptive alias only where the index expressly records it."),
        ("ORG-RCAHMW", "institution", "RCAHMW / Coflein", ["Royal Commission on the Ancient and Historical Monuments of Wales", "Coflein"],
         "Institution/catalogue name grouping in project nomenclature."),
        ("ORG-DWR-CYMRU", "organization", "Dŵr Cymru / Welsh Water", ["Welsh Water"],
         "Utility/company name index; no land-title role inferred."),
    ]
    for entity_id, typ, name, aliases, notes in organizations:
        reg.entity(entity_id, typ, name, aliases=aliases, notes=notes)

    # People are separate source-specific identities unless the records explicitly establish one.
    people = [
        ("PER-JOHN-GEDRICK-1824", "John Gedrick", "Name in the 1824 plan 19 reference table; best reading of a screen photograph, exact identity not independently established."),
        ("PER-THOMAS-WILLIAMS-1824", "Thomas Williams", "“late Thos. Williams” on the 1824 plan 19 reference table; relationship to later John Williams entries is not inferred."),
        ("PER-JOHN-WILLIAMS-TITHE-1841", "John Williams", "Person named as occupier of 36 tithe plots c.1841; not merged with later same-name entries."),
        ("PER-JOHN-WILLIAMS-RATEBOOK-1870S", "John Williams", "Person named in provisional 1872–76 poor-rate reading; identity with the tithe occupier or later residents not established."),
        ("PER-JOHN-WILLIAMS-RESIDENT-1891", "John Williams", "Person reported living at Great House, Llandough in a November 1891 court report; not merged with other John Williams entries."),
        ("PER-JOHN-WILLIAMS-JUROR-1908", "John Williams", "Person described as a Bute court-leet juror and family member in an 1908 newspaper report; not merged by surname alone."),
        ("PER-JOHN-WILLIAMS-TENANT-1916", "John Williams", "Tenant named in the 1916 tenancy recital in the 1987 Court of Appeal judgment; underlying tenancy instrument not held."),
        ("PER-JOHN-WILLIAMS-LESSEE-1939", "John Williams", "Lessee named in the 18 May 1939 WGR agreement for 5.30 acres; the plan is described as fields only, without the farmhouse."),
        ("PER-FREDERICK-BUCKLER-TENANT-1949", "Frederick Buckler", "Tenant in the 1949 surrender/regrant as recited by the Court of Appeal; alleged new tenancy was unwritten."),
        ("PER-MARY-WILLIAMS", "Mary Williams", "Mary Williams named in the 1974 pleading and 1983 death-index record; kept distinct from the 1958 “Mrs M. D. Buckler” speaker unless a record establishes that identity."),
        ("PER-MRS-MD-BUCKLER-1958", "Mrs M. D. Buckler", "Speaker at 1958 Leckwith Common/planning events as reported in the press; not merged with Mary Williams by surname or family assumption."),
        ("PER-ALFRED-THOMAS-1927", "Alfred Thomas", "Alfred Thomas, 1st Baron Pontypridd, whose death is recorded as 14 December 1927; Mary Williams’s recollection of a 1928 payment does not establish that he personally received it."),
        ("PER-REV-JAMES-EVANS-TITHE", "The Revd James Evans", "Name in the tithe apportionment landowner/glebe column c.1841; entity represents the exact name in that source, not a complete biography."),
    ]
    for entity_id, name, disambiguator in people:
        reg.entity(entity_id, "person", name, disambiguator=disambiguator)

    # Research observations and analytical records are graph entities, not original sources.
    for item in observations.get("items", []):
        reg.entity(item["id"], "observation", item.get("title", item["id"]),
                   notes="Working research observation. Its EV references are citations to records, not independent corroboration or proof of the analysis.")
    reg.entity("ANALYSIS-TITLE-CHAIN", "analysis", "Title chain: freehold and occupier records",
               notes="Derived chronology; individual rows preserve source category (record, recital, family account, secondary source or gap).")
    reg.entity("ANALYSIS-TITLE-THEORY", "analysis", title_theory.get("title", "Title theory"),
               notes="Leading working hypothesis, unproven; not a finding of fact or law. References are leads/citations, not a proof of the proposed mechanism.")

    # Observation references: citation only, with observation's explicit role and limits.
    for item in observations.get("items", []):
        for idx, ref in enumerate(item.get("refs", []), start=1):
            source = ref.get("ev")
            if not ev_id(source):
                continue
            role = ref.get("role", "referenced record")
            note = f"data/observations.json#items[{item['id']}].refs[{idx-1}]"
            reg.relation(
                source, item["id"], "cited_in", role=role,
                basis="modern_analysis", verification="provisional",
                text=(
                    f"{source} is listed in {item['id']} as “{role}”. This records a citation in a "
                    "working observation only; it does not certify the proposition, prove causation, "
                    "or create an independent source origin."
                ), note=note
            )

    # Title-chain rows cite the analytical chronology; role and source category are explicit.
    for section in ("freehold", "occupiers"):
        rows = title_chain.get(section, [])
        for idx, row in enumerate(rows):
            for source in row.get("ev", []):
                if not ev_id(source):
                    continue
                status = row.get("st", "unknown")
                basis = "family_account" if status == "fam" else (
                    "catalogue_interpretation" if status in {"cat", "sec", "gap"} else
                    "document_wording" if status in {"ev", "rec", "court"} else "unknown"
                )
                verification = REL_UNVERIFIED if status in {"fam", "sec", "gap"} else "provisional"
                role = f"{section} chain row {idx + 1} ({status})"
                reg.relation(
                    source, "ANALYSIS-TITLE-CHAIN", "cited_in", role=role,
                    basis=basis, verification=verification,
                    text=(
                        "Title-chain row: " + str(row.get("doc", "")).strip()
                        + " The row preserves the source classification and its limitations; "
                        "this citation is not a finding of title, ownership, parcel extent or legal effect."
                    ), note=f"data/title-chain.json#{section}[{idx}]"
                )

    for idx, ref in enumerate(title_theory.get("evidence_refs", [])):
        source = ref.get("ev")
        if not ev_id(source):
            continue
        role = ref.get("role", "research reference")
        reg.relation(
            source, "ANALYSIS-TITLE-THEORY", "cited_in", role=role,
            basis="modern_analysis", verification="provisional",
            text=(
                f"{source} is cited in the leading title-theory working hypothesis as “{role}”. "
                "The hypothesis is unproven; the reference is not a finding and does not establish "
                "the proposition or legal effect."
            ), note=f"data/title-theory.json#evidence_refs[{idx}]"
        )

    # Parcel-event references are explicitly attached to working model slots, never to geometry.
    parcel_entity = {p["model_id"]: "PLC-PARCEL-" + p["model_id"] for p in parcel_stories.get("parcel_model", [])}
    for idx, event in enumerate(parcel_stories.get("model_events", [])):
        target = parcel_entity.get(event.get("model_id"))
        if not target:
            continue
        for source in event.get("source_evs", []):
            if not ev_id(source):
                continue
            reg.relation(
                source, target, "cited_in", role="source citation in working parcel-model event",
                basis="modern_analysis", verification="provisional",
                role=f"source citation in working parcel event: {event.get('title', 'an event')}",
                text=(
                    "This EV is cited by a working parcel-model event. The link records the analytical "
                    "citation only; it does not establish the event's interpretation, ownership, title extent "
                    "or surveyed boundary."
                ), note=f"data/parcel-stories.json#model_events[{idx}]"
            )

    # Nomenclature references connect an exact published variant to its indexed entity.
    group_targets = {
        "tymawr": "PLC-TY-MAWR",
        "llandough": "PLC-LLANDOUGH-PENARTH",
        "woodland": "PLC-CWM-CYDFIN-WOOD",
        "wgr": "ORG-WESTERN-GROUND-RENTS",
        "hmlr": "ORG-HM-LAND-REGISTRY",
        "welsh-government": None,
        "councils": None,
        "museum-wales": "ORG-AMGUEDDFA-CYMRU",
        "rcahmw": "ORG-RCAHMW",
        "heneb": "ORG-HENEB",
        "linklaters": "ORG-LINKLATERS-PAINES",
        "hugh-james": "ORG-LOOSEMORES",
        "leckwith": "PLC-LECKWITH",
    }
    exact_bp_targets = {
        "BP Properties Ltd": "ORG-BP-PROPERTIES",
        "BP Properties Limited (00699446)": "ORG-BP-PROPERTIES",
        "BP Trustees": "ORG-BP-TRUSTEES",
        "BP pension fund": "ORG-BP-PENSION-FUND",
    }
    group_org_targets = {
        ("welsh-government", "Welsh Office"): "ORG-WELSH-OFFICE",
        ("welsh-government", "Welsh Government"): "ORG-WELSH-GOVERNMENT",
        ("welsh-government", "Cadw"): "ORG-CADW",
        ("councils", "Glamorgan County Council"): "ORG-GLAMORGAN-COUNTY-COUNCIL",
        ("councils", "Llandough Community Council"): "ORG-LLANDOUGH-COMMUNITY-COUNCIL",
        ("councils", "Vale of Glamorgan Borough Council"): "ORG-VALE-OF-GLAMORGAN-COUNCIL",
    }
    for group in nomen.get("groups", []):
        group_id = group.get("id")
        for idx, variant in enumerate(group.get("variants", [])):
            if not variant.get("public"):
                continue
            source = variant.get("source_id")
            if not ev_id(source):
                continue
            target = group_org_targets.get((group_id, variant.get("variant")))
            if not target and group_id == "bp":
                target = exact_bp_targets.get(variant.get("variant"))
            if not target:
                target = group_targets.get(group_id)
            if not target:
                continue
            if target not in reg.entities:
                continue
            reg.relation(
                source, target, "catalogued_as", role=f"indexed variant: {variant.get('variant')}",
                basis="catalogue_interpretation", verification="provisional",
                text=(
                    f"The project nomenclature index lists “{variant.get('variant')}” under "
                    f"“{group.get('name')}”. This records the index's classification only; it "
                    "does not establish that every similarly named holding, person or company is identical."
                ), note=f"data/nomenclature.json#groups[{group_id}].variants[{idx}]"
            )

    # Carefully curated source-to-person/organization roles from the title-chain rows.
    person_links = [
        ("EV-0211", "PER-JOHN-GEDRICK-1824", "lists_tenant", "1824 survey reference-table tenant",
         "The survey reference table is described as the best reading of a screen photograph; identity is not independently established.", "catalogue_interpretation", "provisional", "1824"),
        ("EV-0211", "PER-THOMAS-WILLIAMS-1824", "mentions", "“late Thos. Williams” reference",
         "The plan's “late Thos. Williams” wording is retained; it does not identify this person with later John Williams entries.", "document_wording", "provisional", "1824"),
        ("EV-0215", "PER-JOHN-WILLIAMS-TITHE-1841", "lists_occupier", "tithe occupier",
         "John Williams is listed as occupier of 36 plots; the column is not a conveyance or proof of ownership.", "document_wording", "provisional", "c.1841"),
        ("EV-0215", "PER-REV-JAMES-EVANS-TITHE", "lists_landowner", "glebe landowner column",
         "The tithe landowner column lists the Revd James Evans on three glebe plots; this does not identify a freehold conveyance.", "document_wording", "provisional", "c.1841"),
        ("EV-0212", "PER-JOHN-WILLIAMS-RATEBOOK-1870S", "lists_ratepayer", "rate-book entry",
         "The current catalogue describes a provisional reading of a 1872–76 rate-book entry for John Williams; verify the exact original columns.", "catalogue_interpretation", "provisional", "1872-1876"),
        ("EV-0212", "ORG-BUTE-ESTATE", "mentions", "owner-column designation “Lord Bute”",
         "The provisional rate-book reading names “Lord Bute”; this is retained as the estate designation, not a deed or identified individual.", "catalogue_interpretation", "provisional", "1872-1876"),
        ("EV-0010", "PER-JOHN-WILLIAMS-RESIDENT-1891", "reports_resident", "resident named in court report",
         "The November 1891 court report states that John Williams lived at Great House, Llandough; no identity link to other John Williams records is assumed.", "document_wording", "provisional", "1891"),
        ("EV-0243", "PER-JOHN-WILLIAMS-JUROR-1908", "records_juror", "Bute court-leet juror",
         "The court-leet/news report records a John Williams as juror; identity with earlier or later same-name people is not assumed.", "document_wording", "provisional", "1908"),
        ("EV-0283", "PER-JOHN-WILLIAMS-JUROR-1908", "records_juror", "family of late juror named in 1908 report",
         "The report names the family of the late Mr John Williams, Great House, Llandough; this remains a source-specific person entity.", "document_wording", "provisional", "1908"),
        ("EV-0014", "PER-JOHN-WILLIAMS-TENANT-1916", "recites_tenant", "1916 yearly agricultural tenancy",
         "The 1916 tenancy is known here through the 1987 Court of Appeal recital; its plan and parcel extent are not independently established.", "catalogue_interpretation", "provisional", "1916"),
        ("EV-0080", "PER-JOHN-WILLIAMS-TENANT-1916", "recites_tenant", "1987 judgment recital of 1916 tenancy",
         "Court recital of a 1916 tenancy; not a separately inspected tenancy instrument.", "document_wording", "provisional", "1987"),
        ("EV-0023", "PER-JOHN-WILLIAMS-LESSEE-1939", "lists_lessee", "1939 agricultural letting",
         "The archive describes 5.30 acres of agricultural land adjacent to Ty-Mawr farmhouse and records no mention of the farmhouse in the agreement; the plan depicts fields only.", "catalogue_interpretation", "provisional", "1939"),
        ("EV-0025", "PER-FREDERICK-BUCKLER-TENANT-1949", "recites_tenant", "1949 surrender and unwritten regrant",
         "The 1949 surrender and new yearly tenancy are known from the 1987 judgment recital; the regrant was not put in writing.", "document_wording", "provisional", "1949"),
        ("EV-0080", "PER-FREDERICK-BUCKLER-TENANT-1949", "recites_tenant", "1987 judgment recital of 1949 regrant",
         "Court account of the surrender and unwritten regrant; not an independently inspected tenancy instrument.", "document_wording", "provisional", "1987"),
        ("EV-0035", "PER-MRS-MD-BUCKLER-1958", "mentions", "1958 Leckwith Common inquiry speaker",
         "The 1958 newspaper account names Mrs M. D. Buckler; the graph does not merge her automatically with Mary Williams.", "document_wording", "provisional", "1958"),
        ("EV-0037", "PER-MRS-MD-BUCKLER-1958", "mentions", "1958 planning committee speaker",
         "The 1958 press record names Mrs M. D. Buckler; identity with Mary Williams requires separate evidence.", "document_wording", "provisional", "1958"),
        ("EV-0049", "PER-MARY-WILLIAMS", "records_pleading_party", "1974 ownership/limitation plea",
         "Mary Williams is named in the 1974 pleading as described by the catalogue/judgment; the original county-court file has not been read.", "catalogue_interpretation", "provisional", "1974"),
        ("EV-0067", "PER-MARY-WILLIAMS", "records_death_of", "death-index entry",
         "The death-index entry records Mary Williams's death on 26 March 1983; cause of death is not inferred.", "document_wording", "provisional", "1983"),
        ("EV-0284", "PER-ALFRED-THOMAS-1927", "records_death_of", "death recorded 14 December 1927",
         "The Dictionary of Welsh Biography entry gives the death date 14 December 1927; this does not resolve the remembered 1928 rent-payee discrepancy.", "secondary_source", "provisional", "1927"),
        ("EV-0016", "PER-ALFRED-THOMAS-1927", "names_as_rent_payee", "1928 rent payment in family account",
         "Mary Williams's account records that she saw a receipt for a 1928 rent payment “to Alfred Thomas”; the receipt is not located and Alfred died in 1927. The actual payee is unresolved.", "family_account", REL_UNVERIFIED, "1928"),
    ]
    for source, target, rel, role, assertion, basis, verification, dt in person_links:
        reg.relation(source, target, rel, role=role, basis=basis, verification=verification,
                     text=assertion, note="data/title-chain.json#source-specific person-role mapping",
                     date_text=dt)

    # Company/authority roles: relationships are descriptive of named sources or recitals.
    org_links = [
        ("EV-0614", "ORG-MOUNTJOY-LTD", "mentions", "TNA catalogue administrative-history reference",
         "The archive catalogue names Mountjoy Ltd as the Bute family company from 1926; the underlying company records have not been seen.", "catalogue_interpretation", "provisional", "1926"),
        ("EV-0624", "ORG-MOUNTJOY-LTD", "mentions", "press-reported company formation",
         "May 1922 press reports describe formation of Mountjoy Ltd to take over Bute's life interest; the exact company history requires company-file verification.", "secondary_source", "provisional", "1922"),
        ("EV-0625", "ORG-MOUNTJOY-LTD", "names_seller", "1938 reported estate sale",
         "Press/catalogue material describes a 1938 sale; the conveyance and its plan have not been examined and Llandough-juxta-Penarth inclusion is not established.", "catalogue_interpretation", "provisional", "1938"),
        ("EV-0022", "ORG-WESTERN-GROUND-RENTS", "names_buyer", "1938 press-reported buyer",
         "Contemporary press describes Western Ground Rents as buyer in the 1938 transaction; deed scope and exact parties remain to be checked against the instrument.", "secondary_source", "provisional", "1938"),
        ("EV-0023", "ORG-WESTERN-GROUND-RENTS", "mentions", "1939 lessor",
         "The 1939 agreement is described as a WGR letting of agricultural fields adjacent to the farmhouse, with no mention of the farmhouse itself.", "catalogue_interpretation", "provisional", "1939"),
        ("EV-0043", "ORG-WESTERN-GROUND-RENTS", "names_transferor", "1969 transferor in title recital",
         "The title-chain entry identifies WGR as transferor to BP Pension Trust; the instrument is known through later title records and requires inspection.", "catalogue_interpretation", "provisional", "1969"),
        ("EV-0043", "ORG-BP-PENSION-TRUST", "names_transferee", "1969 transferee in title recital",
         "The title-chain entry identifies BP Pension Trust as transferee; this is not merged with BP Properties Ltd.", "catalogue_interpretation", "provisional", "1969"),
        ("EV-0052", "ORG-BP-PENSION-TRUST", "names_transferor", "1975 transferor",
         "BP Pension Trust is named as transferor to BP Properties; deed and plan status must be checked against the actual register file.", "catalogue_interpretation", "provisional", "1975"),
        ("EV-0052", "ORG-BP-PROPERTIES", "names_transferee", "1975 transferee",
         "BP Properties Ltd is named as transferee; distinct legal entity from BP Pension Trust and BP Trustees.", "catalogue_interpretation", "provisional", "1975"),
        ("EV-0080", "ORG-BP-PROPERTIES", "mentions", "party to Court of Appeal proceedings",
         "The 1987 judgment records BP Properties Ltd as the claimant; this is a party designation, not independent proof of the original title instrument.", "document_wording", "provisional", "1987"),
        ("EV-0284", "ORG-CARDIFF-CORPORATION", "mentions", "reported beneficiary of Thomas estate",
         "A secondary transcription describes an unofficial report that the bulk of Alfred Thomas's property was left to Cardiff Corporation; neither the original will nor any Llandough transfer is established.", "secondary_source", REL_UNVERIFIED, "1927"),
    ]
    for source, target, rel, role, assertion, basis, verification, dt in org_links:
        reg.relation(source, target, rel, role=role, basis=basis, verification=verification,
                     text=assertion, note="data/title-chain.json#source-qualified organization-role mapping",
                     date_text=dt)

    # The 1877 agreement is a family-account lead; do not treat the named party as proof of a conveyance.
    reg.entity("ORG-DANIEL-THOMAS-AND-SON", "organization", "Daniel Thomas & Son",
               notes="Named in Mary Williams's account of the reported 1877 Bute agreement; instrument and plan remain unlocated.")
    reg.relation(
        "EV-0006", "ORG-DANIEL-THOMAS-AND-SON", "mentions",
        role="counterparty named in family account of reported 1877 agreement",
        basis="family_account", verification=REL_UNVERIFIED,
        text="Mary Williams's reported account names Daniel Thomas & Son in a 1877 agreement; the agreement and plan are unlocated, so its terms, extent and legal effect remain unestablished.",
        note="data/title-chain.json#freehold[14]; data/parcel-stories.json#model_events"
    )

    return reg.serialise()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if committed registry differs from generated registry")
    args = parser.parse_args()
    generated = build()
    rendered = json.dumps(generated, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != rendered:
            raise SystemExit("catalogue relationship registry is stale; run tools/generate_catalogue_relationships.py")
        print(f"catalogue relationships OK: {len(generated['entities'])} entities, {len(generated['relationships'])} source-qualified links")
        return
    OUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(generated['entities'])} entities, {len(generated['relationships'])} source-qualified links")


if __name__ == "__main__":
    main()
