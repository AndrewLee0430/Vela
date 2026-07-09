"""
DailyMed API Client (NIH SPL / structured product labeling)

Mirrors api/data_sources/fda.py (the openFDA client): a structured label
dataclass + an async client that resolves a drug name to a label. Built for the
Verify DailyMed-primary integration; the later Research 5th-source increment reuses
the same client.

API contract (live-verified 2026-07-08):
- Resolve:  GET /v2/spls.json?drug_name={name} -> {"data":[{"setid","spl_version",...}]}
            (the /drugname/{name}/spls.json PATH form is DEAD — 302 -> HTML.)
- Label:    GET /v2/spls/{setid}.xml -> full SPL (XML only, HL7 CDA, ns urn:hl7-org:v3)
- Sections: <section> with <code code="{LOINC}"> — Drug Interactions = 34073-7
            (ABSENT on OTC Drug-Facts labels, e.g. aspirin/cetirizine -> caller falls back).

Ingest-and-cite (ADR 004/007): we extract + carry the label's own interaction-section
text (prose + flattened tables); we never synthesize a "cannot combine" verdict.
No API key, GET-only, no documented rate limit.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional
import xml.etree.ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

# SPL is HL7 CDA in this namespace.
_NS = "{urn:hl7-org:v3}"

# LOINC section codes (SPL). Drug Interactions is the one Verify grounds on.
_LOINC_DRUG_INTERACTIONS = "34073-7"
_LOINC_CONTRAINDICATIONS = "34070-3"
_LOINC_WARNINGS_PRECAUTIONS = "43685-7"
_LOINC_BOXED_WARNING = "34066-1"
_LOINC_INDICATIONS = "34067-0"
_LOINC_DOSAGE = "34068-7"

_MAX_SECTION_CHARS = 2000  # mirror fda.py's _truncate budget


@dataclass
class DailyMedLabel:
    """DailyMed SPL label — mirrors FDADrugLabel's public shape so the Verify path
    (and the later Research path) can consume it interchangeably."""

    brand_name: str
    generic_name: str
    manufacturer: str
    setid: str
    indications: Optional[str] = None
    warnings: Optional[str] = None
    drug_interactions: Optional[str] = None   # LOINC 34073-7 prose + flattened tables
    dosage: Optional[str] = None
    contraindications: Optional[str] = None
    boxed_warning: Optional[str] = None

    @property
    def url(self) -> str:
        # Deep-link the EXACT label version (setid), not a search page.
        return f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={self.setid}"

    @property
    def source_id(self) -> str:
        return f"DailyMed:{self.setid}"

    def to_text(self) -> str:
        """RAG text. FOREGROUNDS the drug-interactions section (the Verify grounding
        target) right after the header, then the other safety sections as available."""
        sections = [f"# {self.brand_name} ({self.generic_name})"]
        sections.append(f"**Manufacturer:** {self.manufacturer}")
        sections.append(f"**Source:** DailyMed (FDA Structured Product Labeling), setid {self.setid}")

        if self.drug_interactions:
            sections.append(f"\n## Drug Interactions\n{self.drug_interactions}")
        if self.boxed_warning:
            sections.append(f"\n## Boxed Warning\n{self.boxed_warning}")
        if self.contraindications:
            sections.append(f"\n## Contraindications\n{self.contraindications}")
        if self.warnings:
            sections.append(f"\n## Warnings and Precautions\n{self.warnings}")
        if self.indications:
            sections.append(f"\n## Indications and Usage\n{self.indications}")
        if self.dosage:
            sections.append(f"\n## Dosage and Administration\n{self.dosage}")

        return "\n".join(sections)


class DailyMedClient:
    """DailyMed v2 REST client. GET-only, no API key."""

    BASE_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2"

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    async def search_drug_labels(self, query: str, limit: int = 1) -> list[DailyMedLabel]:
        """Resolve a drug name to its most-recent SPL label.

        Resolve -> pick the MAX spl_version setid -> fetch that SPL XML -> parse
        sections. Returns [DailyMedLabel] (list for FDAClient parity) or [] on any
        miss/error. `limit` caps how many setids we materialize (Verify needs 1).
        The label is returned even when 34073-7 is absent — the CALLER inspects
        `.drug_interactions` and falls back to openFDA when it is empty.
        """
        try:
            setids = await self._resolve_setids(query)
            if not setids:
                return []
            # Most recent spl_version first; materialize up to `limit`.
            labels: list[DailyMedLabel] = []
            for setid, _ver in setids[:max(1, limit)]:
                xml = await self._fetch_spl_xml(setid)
                if xml is None:
                    continue
                label = self._parse_spl(xml, setid, fallback_name=query)
                if label is not None:
                    labels.append(label)
            return labels
        except Exception as e:
            logger.warning("[DailyMed] search_drug_labels error for '%s': %s: %s",
                           query, type(e).__name__, e)
            return []

    async def search_by_interaction(self, drug_name: str, limit: int = 1) -> list[DailyMedLabel]:
        """Labels whose Drug Interactions (34073-7) section is present + non-empty."""
        labels = await self.search_drug_labels(drug_name, limit=limit)
        return [lbl for lbl in labels if lbl.drug_interactions][:limit]

    # ── HTTP ─────────────────────────────────────────────────────────────────────
    async def _resolve_setids(self, query: str) -> list[tuple[str, int]]:
        """GET /v2/spls.json?drug_name=... -> [(setid, spl_version)], newest first."""
        params = {"drug_name": query}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.BASE_URL}/spls.json", params=params)
                if resp.status_code == 404:
                    return []
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning("[DailyMed] resolve error for '%s': %s: %s",
                           query, type(e).__name__, e)
            return []

        rows = data.get("data", []) if isinstance(data, dict) else []
        out: list[tuple[str, int]] = []
        for r in rows:
            sid = r.get("setid")
            if not sid:
                continue
            try:
                ver = int(r.get("spl_version") or 0)
            except (TypeError, ValueError):
                ver = 0
            out.append((sid, ver))
        # Most recent spl_version first (the label revision the label-holder last filed).
        out.sort(key=lambda t: t[1], reverse=True)
        return out

    async def _fetch_spl_xml(self, setid: str) -> Optional[bytes]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.BASE_URL}/spls/{setid}.xml")
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp.content
        except Exception as e:
            logger.warning("[DailyMed] SPL fetch error for setid %s: %s: %s",
                           setid, type(e).__name__, e)
            return None

    # ── XML parsing ────────────────────────────────────────────────────────────────
    def _parse_spl(self, xml: bytes, setid: str, fallback_name: str) -> Optional[DailyMedLabel]:
        try:
            root = ET.fromstring(xml)
        except Exception as e:
            logger.warning("[DailyMed] XML parse error for setid %s: %s", setid, e)
            return None

        brand, generic, mfr = self._parse_names(root, fallback_name)
        return DailyMedLabel(
            brand_name=brand,
            generic_name=generic,
            manufacturer=mfr,
            setid=setid,
            drug_interactions=self._section_text(root, _LOINC_DRUG_INTERACTIONS),
            contraindications=self._section_text(root, _LOINC_CONTRAINDICATIONS),
            warnings=self._section_text(root, _LOINC_WARNINGS_PRECAUTIONS),
            boxed_warning=self._section_text(root, _LOINC_BOXED_WARNING),
            indications=self._section_text(root, _LOINC_INDICATIONS),
            dosage=self._section_text(root, _LOINC_DOSAGE),
        )

    def _parse_names(self, root, fallback_name: str) -> tuple[str, str, str]:
        """Best-effort brand/generic/manufacturer from the SPL. Falls back to the
        query name — names are secondary; the interaction TEXT is the payload."""
        brand = fallback_name
        generic = fallback_name
        mfr = "DailyMed"
        # Brand: the manufactured product's <name>.
        prod = root.find(f".//{_NS}manufacturedProduct/{_NS}manufacturedProduct/{_NS}name")
        if prod is None:
            prod = root.find(f".//{_NS}manufacturedProduct/{_NS}name")
        if prod is not None and (prod.text or "").strip():
            brand = prod.text.strip()
        # Generic: <genericMedicine><name>.
        gen = root.find(f".//{_NS}genericMedicine/{_NS}name")
        if gen is not None and (gen.text or "").strip():
            generic = gen.text.strip()
        # Manufacturer: the represented / author organization name.
        org = root.find(f".//{_NS}representedOrganization/{_NS}name")
        if org is None:
            org = root.find(f".//{_NS}author//{_NS}representedOrganization/{_NS}name")
        if org is not None and (org.text or "").strip():
            mfr = org.text.strip()
        return brand, generic, mfr

    def _section_text(self, root, loinc: str) -> Optional[str]:
        """Locate the <section> with <code code="{loinc}"> and return its prose PLUS
        its <table> rows linearized to 'cell — cell' lines. Tables are the LABEL's own
        interaction lists (cited content), never a Vela-authored prohibition."""
        section = None
        for sec in root.iter(f"{_NS}section"):
            code = sec.find(f"{_NS}code")
            if code is not None and code.get("code") == loinc:
                section = sec
                break
        if section is None:
            return None

        prose = self._collect_prose(section)
        tables = self._flatten_tables(section)
        # Baton A / option (b): bound runaway PROSE (a single label's narrative can be huge)
        # but ALWAYS keep the FULL flattened TABLE. The label's own per-drug interaction
        # enumeration (e.g. warfarin's CYP450 inhibitor/inducer lists) lives in the tables
        # and IS the grounding payload — it must never be dropped by a blob-wide char cut.
        # (The v201 under-grounding bug: the table sat past char 2000 and vanished from what
        # Verify fed the LLM, so major interactions like warfarin+fluconazole were absent.)
        if len(prose) > _MAX_SECTION_CHARS:
            prose = prose[:_MAX_SECTION_CHARS] + "..."
        combined = "\n".join(p for p in (prose, tables) if p).strip()
        # INVARIANT (protects the server.py tiering truthiness → tier=dailymed + setid +
        # attribution_kind=dailymed_grounded): a section with ANY content (prose OR table)
        # returns non-empty; only a genuinely empty section → None.
        return combined or None

    def _collect_prose(self, section) -> str:
        """Visible text of the section EXCLUDING <table> subtrees (tables handled
        separately so we can linearize them explicitly)."""
        parts: list[str] = []

        def walk(el, in_table: bool):
            tag = el.tag.replace(_NS, "")
            it = in_table or tag == "table"
            if not it and el.text and el.text.strip():
                parts.append(el.text.strip())
            for child in el:
                walk(child, it)
                if not it and child.tail and child.tail.strip():
                    parts.append(child.tail.strip())

        walk(section, False)
        text = " ".join(parts)
        return re.sub(r"\s+", " ", text).strip()

    def _flatten_tables(self, section) -> str:
        """Linearize each <table> to 'cell — cell — cell' rows (the label's own
        interaction lists). One line per row; blank cells dropped."""
        lines: list[str] = []
        for table in section.iter(f"{_NS}table"):
            for row in table.iter(f"{_NS}tr"):
                cells: list[str] = []
                for cell in row:
                    if cell.tag.replace(_NS, "") not in ("td", "th"):
                        continue
                    txt = " ".join(t.strip() for t in cell.itertext() if t.strip())
                    txt = re.sub(r"\s+", " ", txt).strip()
                    if txt:
                        cells.append(txt)
                if cells:
                    lines.append(" — ".join(cells))
        return "\n".join(lines)
