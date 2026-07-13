# -*- coding: utf-8 -*-
"""Verify DailyMed surface — Option C ingest-and-cite (2026-07-08 build).

Business rules pinned (CLAUDE.md Rule 17 — what breaks if these fail):
  (i)   main-path grounding — a DailyMed 34073-7 label reaches the LLM context AND
        the emitted interaction cites the exact SPL (drugInfo.cfm?setid=). If this
        fails, Verify stops grounding descriptions in the label's own words.
  (ii)  fallback-honesty chain — DailyMed miss → openFDA → no-label, each with its
        own honest source string. If this fails, a fallback tier mislabels provenance.
  (iii) honest-severity split — the DailyMed source string states severity is Vela-AI,
        not label-stated (the v199 fake-authority lesson, DailyMed edition).
  (iv)  anti-regression — the banned "FDA Label Analysis"-family strings never emit.
  (v)   SaMD boundary — no "must not be combined"/prohibition verdict is emitted, and
        the prompt carries the no-verdict rule (ADR 004/007 ingest-and-cite).
  (vi)  table-handling — a table-only 34073-7 section flattens to non-vacuous cited
        text (not just "See Table 4"), so table-dependent labels still ground.

All network-free: DailyMedClient / FDAClient / the LLM are stubbed. Run:
    python tests/test_verify_dailymed.py   (or via pytest)
"""
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["TEST_MODE"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from api.data_sources.dailymed import DailyMedClient  # noqa: E402
from api.server import (  # noqa: E402
    DAILYMED_GROUNDED_SOURCE, OPENFDA_ANALYSIS_SOURCE, _resolve_interaction_source,
    ATTR_DAILYMED_GROUNDED, ATTR_OPENFDA_ANALYSIS, ATTR_NO_LABEL,
)

BANNED_SOURCE_STRINGS = ("FDA Label Analysis", "FDA Label / AI Analysis")
BANNED_VERDICTS = (
    "must not be combined", "must not combine", "do not combine",
    "cannot be combined", "contraindicated combination", "never combine",
)

# ── Stub label + clients ─────────────────────────────────────────────────────────────
class _FakeDMLabel:
    def __init__(self, generic, setid, interactions):
        self.generic_name = generic
        self.brand_name = generic.title()
        self.setid = setid
        self.drug_interactions = interactions

    def to_text(self):
        return f"# {self.brand_name} ({self.generic_name})\n## Drug Interactions\n{self.drug_interactions}"


class _StubDailyMed:
    """Returns a mapping of drug->_FakeDMLabel (or a label with no interactions / nothing)."""
    def __init__(self, by_drug):
        self._by_drug = by_drug

    async def search_drug_labels(self, drug, limit=1):
        lbl = self._by_drug.get(drug.lower())
        return [lbl] if lbl is not None else []


class _FakeFDALabel:
    generic_name = "aspirin"
    brand_name = "Aspirin"
    manufacturer = "StubCo"
    source_id = "FDA:stub"
    url = "https://example/fda"

    def to_text(self):
        return "ASPIRIN FDA label. Drug interactions: increased bleeding risk with anticoagulants."


class _StubFDA:
    def __init__(self, by_drug):
        self._by_drug = by_drug

    async def search_drug_labels(self, drug, limit=1):
        lbl = self._by_drug.get(drug.lower())
        return [lbl] if lbl is not None else []


class _Resp:
    def __init__(self, content):
        self.content = content
        self.input_tokens = 1
        self.output_tokens = 1


class _CapturingProvider:
    def __init__(self, content):
        self._content = content
        self.last_user_content = None

    async def complete(self, req):
        # Capture the user message so we can assert the label passage reached context.
        for m in req.messages:
            if m.get("role") == "user":
                self.last_user_content = m.get("content")
        return _Resp(self._content)


class _StubBinding:
    def __init__(self, provider):
        self.model = "stub-model"
        self.provider = provider


def _run_verify(dm_by_drug, fda_by_drug, llm_json, drugs, lang="en"):
    """Drive POST /api/verify with all three sources stubbed. Returns (json, provider)."""
    import api.middleware.guards as guards
    import api.server as server
    from fastapi.testclient import TestClient

    async def _always_medical(text):
        return True, ""

    async def _no_deduct(db, user_id, feature):
        return None

    provider = _CapturingProvider(llm_json)
    orig = (guards.check_medical_intent, server._verify_binding,
            server.fda_client, server.dailymed_client, server.deduct_credits)
    guards.check_medical_intent = _always_medical
    server._verify_binding = _StubBinding(provider)
    server.dailymed_client = _StubDailyMed(dm_by_drug)
    server.fda_client = _StubFDA(fda_by_drug)
    server.deduct_credits = _no_deduct
    try:
        client = TestClient(server.app)
        resp = client.post("/api/verify", json={
            "drugs": drugs, "patient_context": None, "response_language": lang,
        })
        assert resp.status_code == 200, resp.text
        return resp.json(), provider
    finally:
        (guards.check_medical_intent, server._verify_binding,
         server.fda_client, server.dailymed_client, server.deduct_credits) = orig


_DM_PASSAGE = "Concomitant use with anticoagulants increases bleeding risk; monitor INR closely."
_LLM_ONE_INTERACTION = (
    '{"interactions": [{"drugs": ["warfarin", "amoxicillin"], "severity": "Major", '
    '"description": "The label reports concomitant anticoagulant use increases bleeding '
    'risk; monitor INR closely.", "recommendation": "Monitor INR; adjust dose as needed."}], '
    '"summary": "1 interaction", "risk_level": "Major"}'
)


# ── (i) main-path grounding ──────────────────────────────────────────────────────────
def test_main_path_dailymed_grounding_and_setid_deeplink():
    dm = {
        "warfarin": _FakeDMLabel("warfarin", "SETID-WARF", _DM_PASSAGE),
        "amoxicillin": _FakeDMLabel("amoxicillin", "SETID-AMOX", "Probenecid co-administration is not recommended."),
    }
    data, provider = _run_verify(dm, {}, _LLM_ONE_INTERACTION, ["warfarin", "amoxicillin"])
    assert data["interactions"], "main path should return the interaction"
    it = data["interactions"][0]
    assert it["source"] == DAILYMED_GROUNDED_SOURCE, it["source"]
    assert "drugInfo.cfm?setid=SETID-WARF" in it["source_url"], it["source_url"]
    # The DailyMed 34073-7 passage must have reached the LLM context (grounding wiring).
    assert provider.last_user_content and _DM_PASSAGE in provider.last_user_content
    assert "Drug label data (DailyMed primary" in provider.last_user_content


# ── (ii) fallback-honesty chain ──────────────────────────────────────────────────────
def test_fallback_chain_openfda_when_dailymed_missing():
    """DailyMed miss on aspirin (OTC, no 34073-7) → openFDA fallback → v199 source."""
    dm = {"warfarin": _FakeDMLabel("warfarin", "SETID-WARF", _DM_PASSAGE)}  # aspirin absent
    fda = {"aspirin": _FakeFDALabel()}
    data, _ = _run_verify(dm, fda, _LLM_ONE_INTERACTION, ["warfarin", "aspirin"])
    sources = {it["source"] for it in data["interactions"]}
    # The single emitted interaction names warfarin (DailyMed) → grounded source wins the
    # match; but the mixed pool proves both tiers coexist without error.
    assert data["interactions"], "mixed DailyMed+openFDA pool should still analyze"
    assert sources <= {DAILYMED_GROUNDED_SOURCE, OPENFDA_ANALYSIS_SOURCE}
    for s in sources:
        assert s not in BANNED_SOURCE_STRINGS


def test_fallback_chain_no_label_stays_honest():
    """DailyMed miss AND openFDA miss AND no spell-match → the no-label path, whose
    source string is the pre-existing honest 'Clinical Knowledge (No FDA label available)'."""
    llm = ('{"interactions": [{"drugs": ["zzalpha", "zzbeta"], "severity": "Minor", '
           '"description": "d", "recommendation": "r"}], "summary": "s", "risk_level": "Minor"}')
    data, _ = _run_verify({}, {}, llm, ["zzalpha", "zzbeta"])
    assert data["verification_status"] in ("ok",), data.get("verification_status")
    for it in data["interactions"]:
        assert it["source"] == "Clinical Knowledge (No FDA label available)", it["source"]


# ── (iii) honest-severity split ──────────────────────────────────────────────────────
def test_dailymed_source_marks_severity_as_vela_ai():
    dm = {"warfarin": _FakeDMLabel("warfarin", "SETID-WARF", _DM_PASSAGE),
          "amoxicillin": _FakeDMLabel("amoxicillin", "SETID-AMOX", "text")}
    data, _ = _run_verify(dm, {}, _LLM_ONE_INTERACTION, ["warfarin", "amoxicillin"])
    it = data["interactions"][0]
    assert "severity is Vela's AI interpretation" in it["source"], it["source"]
    # description traces to the label passage (grounded), severity kept separately.
    assert "bleeding risk" in it["description"].lower()
    assert it["severity"] == "Major"


# ── (iv) anti-regression ─────────────────────────────────────────────────────────────
def test_no_fake_authority_strings_in_payload_or_source():
    dm = {"warfarin": _FakeDMLabel("warfarin", "SETID-WARF", _DM_PASSAGE),
          "amoxicillin": _FakeDMLabel("amoxicillin", "SETID-AMOX", "text")}
    data, _ = _run_verify(dm, {}, _LLM_ONE_INTERACTION, ["warfarin", "amoxicillin"])
    for it in data["interactions"]:
        for banned in BANNED_SOURCE_STRINGS:
            assert banned not in it["source"], it["source"]
    # source inspection: the banned strings live nowhere in the Verify code path.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in ("api/server.py", "api/models/schemas.py", "api/data_sources/dailymed.py"):
        text = open(os.path.join(root, rel), encoding="utf-8").read()
        for banned in BANNED_SOURCE_STRINGS:
            assert banned not in text, f"{banned!r} present in {rel}"


# ── (v) SaMD boundary ────────────────────────────────────────────────────────────────
def test_no_prohibition_verdict_emitted():
    dm = {"warfarin": _FakeDMLabel("warfarin", "SETID-WARF", _DM_PASSAGE),
          "amoxicillin": _FakeDMLabel("amoxicillin", "SETID-AMOX", "text")}
    data, _ = _run_verify(dm, {}, _LLM_ONE_INTERACTION, ["warfarin", "amoxicillin"])
    for it in data["interactions"]:
        blob = f"{it['description']} {it['clinical_recommendation']}".lower()
        for verdict in BANNED_VERDICTS:
            assert verdict not in blob, f"verdict phrasing leaked: {verdict!r}"


def test_prompt_carries_no_verdict_rule():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt = open(os.path.join(root, "api/prompts/verify_system.md"), encoding="utf-8").read()
    assert "NO combine/don't-combine verdicts" in prompt or "must not be combined" in prompt.lower(), \
        "verify_system.md must carry the explicit no-verdict rule"
    assert "Ground each" in prompt, "verify_system.md must carry the grounding instruction"


# ── (vi) table-handling (client-level, deterministic XML) ────────────────────────────
_TABLE_ONLY_SPL = (
    '<document xmlns="urn:hl7-org:v3"><component><structuredBody><component>'
    '<section>'
    '<code code="34073-7" codeSystem="2.16.840.1.113883.6.1" displayName="DRUG INTERACTIONS SECTION"/>'
    '<title>7 DRUG INTERACTIONS</title>'
    '<text><paragraph>See Table 4 for clinically relevant interactions.</paragraph>'
    '<table><tbody>'
    '<tr><td>Metformin</td><td>increases risk of lactic acidosis</td><td>monitor renal function</td></tr>'
    '<tr><td>Rifampin</td><td>decreases exposure</td><td>avoid coadministration</td></tr>'
    '</tbody></table></text>'
    '</section>'
    '</component></structuredBody></component></document>'
)


def test_table_only_section_flattens_to_nonvacuous_text():
    root = ET.fromstring(_TABLE_ONLY_SPL)
    text = DailyMedClient()._section_text(root, "34073-7")
    assert text, "section must be located + extracted"
    # NOT just the 'See Table 4' pointer — the flattened rows must be present.
    for token in ("Metformin", "lactic acidosis", "Rifampin", "avoid coadministration"):
        assert token in text, f"flattened table lost {token!r}: {text!r}"
    assert " — " in text, "table rows should linearize as 'cell — cell'"


def test_absent_section_returns_none():
    """OTC Drug-Facts shape (no 34073-7) → None, so the server falls back."""
    otc = ('<document xmlns="urn:hl7-org:v3"><component><structuredBody><component>'
           '<section><code code="42229-5" displayName="SPL UNCLASSIFIED SECTION"/>'
           '<text><paragraph>Ask a doctor before use.</paragraph></text></section>'
           '</component></structuredBody></component></document>')
    assert DailyMedClient()._section_text(ET.fromstring(otc), "34073-7") is None


# ── Baton A: option (b) — bound prose, ALWAYS keep the full interaction TABLE ──────────
def _spl_34073(prose: str = "", rows: list | None = None) -> str:
    """Minimal SPL with a 34073-7 section: a <paragraph> of `prose` + a <table> of `rows`."""
    para = f"<paragraph>{prose}</paragraph>" if prose else ""
    tbody = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in (rows or []))
    table = f"<table><tbody>{tbody}</tbody></table>" if tbody else ""
    return ('<document xmlns="urn:hl7-org:v3"><component><structuredBody><component>'
            '<section>'
            '<code code="34073-7" codeSystem="2.16.840.1.113883.6.1" displayName="DRUG INTERACTIONS SECTION"/>'
            f'<text>{para}{table}</text>'
            '</section></component></structuredBody></component></document>')


def test_long_section_keeps_full_table_past_2000():
    """REGRESSION PIN (Baton A). What breaks if this fails: a drug-interaction table that
    sits past char 2000 (the label's per-drug CYP450 enumeration) is dropped → Verify
    grounds on text where major interactions (warfarin+fluconazole) are ABSENT → under-warn
    while attribution claims 'grounded'. This FAILS on v201 (blob hard-cut at 2000 drops the
    trailing table) and PASSES after option (b) (prose bounded, full table always appended)."""
    long_prose = "CYP450 interaction narrative sentence. " * 80   # ~3120 chars > 2000
    spl = _spl_34073(long_prose, rows=[
        ["CYP2C9 Inhibitors", "amiodarone, fluconazole, fluvoxamine, metronidazole"],
        ["CYP Inducers", "rifampin, carbamazepine, phenytoin"],
    ])
    text = DailyMedClient()._section_text(ET.fromstring(spl), "34073-7")
    assert text, "section must be extracted"
    # The table (and its drug enumeration) sits past char 2000 — it MUST survive.
    for drug in ("fluconazole", "rifampin", "carbamazepine"):
        assert drug in text, f"dropped table drug {drug!r} — the v201 under-grounding bug: {len(text)=}"
    assert "..." in text[:2100], "prose portion should be bounded (~2000 + ellipsis)"
    assert " — " in text, "flattened table rows retained"


def test_section_with_content_never_renders_empty_but_empty_stays_none():
    """INVARIANT GUARD (protects server.py:1214 truthiness → tier=dailymed + setid). A
    section with ANY content (prose OR table) must return non-empty; only a genuinely
    empty section returns None (so a real label never false-flips to the openFDA tier)."""
    c = DailyMedClient()
    prose_only = c._section_text(ET.fromstring(_spl_34073("Concomitant use increases bleeding risk.")), "34073-7")
    assert prose_only and "bleeding risk" in prose_only, "prose-only section must be non-empty"
    table_only = c._section_text(ET.fromstring(_spl_34073(rows=[["Warfarin", "monitor INR"]])), "34073-7")
    assert table_only and "Warfarin" in table_only, "table-only section must be non-empty"
    empty = c._section_text(ET.fromstring(_spl_34073()), "34073-7")   # no prose, no table
    assert empty is None, "a genuinely empty section must return None (no false tier flip)"


def test_dailymed_to_text_carries_full_table_past_cut():
    """to_text() (what Verify feeds the LLM at server.py:1370) must carry the full table."""
    long_prose = "Interaction narrative. " * 120   # >2000
    spl = _spl_34073(long_prose, rows=[["CYP2C9 Inhibitors", "fluconazole, amiodarone"]])
    lbl = DailyMedClient()._parse_spl(spl.encode("utf-8"), "SETID-X", "warfarin")
    assert lbl is not None and lbl.drug_interactions   # invariant: truthy
    assert "fluconazole" in lbl.to_text(), "to_text must carry the full interaction table"


def test_openfda_to_text_keeps_full_interaction_section():
    """openFDA parity (Baton A, fda.py). openFDA sections are single prose blobs; the
    interaction/contraindication drug enumerations live INLINE. The safety sections must
    NOT be truncated, so a drug named past char 2000 still reaches the Verify LLM."""
    from api.data_sources.fda import FDADrugLabel
    late_interaction = ("Interaction narrative. " * 120) + " Coadministration with FLUCONAZOLE raises INR."
    lbl = FDADrugLabel(brand_name="Coumadin", generic_name="warfarin", manufacturer="X",
                       drug_interactions=late_interaction)
    txt = lbl.to_text()
    assert "FLUCONAZOLE" in txt, "openFDA interaction section must not truncate the late drug enumeration"
    # non-grounding narrative stays bounded (parity rationale): a long indications field is capped.
    lbl2 = FDADrugLabel(brand_name="X", generic_name="x", manufacturer="X",
                        indications="Indicated for. " * 200)
    assert "..." in lbl2.to_text(), "narrative (indications) stays bounded via _truncate"


# ── Baton A2-typo: the INDICATIONS LOINC must be 34067-9 (was a "34067-0" typo) ───────
def _spl_indications(text: str) -> str:
    """Minimal SPL with a 34067-9 INDICATIONS & USAGE section (the real SPL code)."""
    return ('<document xmlns="urn:hl7-org:v3"><component><structuredBody><component>'
            '<section>'
            '<code code="34067-9" codeSystem="2.16.840.1.113883.6.1" displayName="INDICATIONS &amp; USAGE SECTION"/>'
            f'<text><paragraph>{text}</paragraph></text>'
            '</section></component></structuredBody></component></document>')


def test_indications_loinc_is_34067_9_and_populates():
    """REGRESSION PIN (Baton A2-typo). `_LOINC_INDICATIONS` was "34067-0" — a typo for the
    real SPL "INDICATIONS & USAGE SECTION" code 34067-9 — so .indications NEVER populated
    (0/1040 in the Stage-A corpus). This FAILS pre-fix (the 34067-0 code matches no section
    → .indications is None) and PASSES after. What breaks if it fails: Verify's to_text()
    silently omits the entire indications section from the LLM context."""
    from api.data_sources.dailymed import _LOINC_INDICATIONS
    assert _LOINC_INDICATIONS == "34067-9", f"indications LOINC regressed to {_LOINC_INDICATIONS!r}"
    spl = _spl_indications("Warfarin is indicated for prophylaxis and treatment of venous thrombosis.")
    lbl = DailyMedClient()._parse_spl(spl.encode("utf-8"), "SETID-IND", "warfarin")
    assert lbl is not None
    assert lbl.indications and "prophylaxis and treatment" in lbl.indications, \
        f"indications must now populate: {lbl.indications!r}"
    assert "## Indications and Usage" in lbl.to_text(), "to_text must render the indications section"


# ── unit: source resolver ────────────────────────────────────────────────────────────
def test_resolve_source_prefers_dailymed_and_deeplinks_setid():
    prov = [{"drug": "warfarin", "label": None, "setid": "S1", "tier": "dailymed"},
            {"drug": "aspirin", "label": None, "setid": None, "tier": "openfda"}]
    src, url, kind = _resolve_interaction_source(["warfarin", "aspirin"], prov)
    assert src == DAILYMED_GROUNDED_SOURCE and "setid=S1" in url
    assert kind == ATTR_DAILYMED_GROUNDED

    src2, url2, kind2 = _resolve_interaction_source(["aspirin", "ibuprofen"], prov)
    assert src2 == OPENFDA_ANALYSIS_SOURCE  # matched the openFDA-tier drug
    assert kind2 == ATTR_OPENFDA_ANALYSIS


def test_no_confident_match_never_invents_a_setid_citation():
    """ANTI-FALSE-CITATION (citation integrity, v197/v199 class). What breaks if this
    fails: a Verify card cites a DailyMed SPL that did NOT state the interaction — fake
    authority. When an interaction's drugs match NO provenance entry (CJK→INN
    substitution, LLM rename, multi-word names), we must fail HONEST — never attach a
    specific setid deep-link for an unmatched label."""
    prov = [{"drug": "warfarin", "label": None, "setid": "abc", "tier": "dailymed"}]
    src, url, kind = _resolve_interaction_source(["SomeRenamedDrug", "OtherDrug"], prov)
    assert src != DAILYMED_GROUNDED_SOURCE, f"must not claim DailyMed grounding: {src!r}"
    assert src == OPENFDA_ANALYSIS_SOURCE, src
    assert kind == ATTR_OPENFDA_ANALYSIS, kind   # NOT dailymed_grounded — no false citation
    assert "setid=abc" not in (url or ""), f"must not cite the unmatched setid: {url!r}"
    assert "drugInfo.cfm?setid=" not in (url or ""), f"no specific setid deep-link at all: {url!r}"


def test_openfda_tier_match_does_not_borrow_a_dailymed_setid():
    """A pair that matches only an openFDA-tier entry must NOT borrow a co-retrieved
    DailyMed entry's setid (that DailyMed label is a different drug)."""
    prov = [{"drug": "warfarin", "label": None, "setid": "WSET", "tier": "dailymed"},
            {"drug": "ibuprofen", "label": None, "setid": None, "tier": "openfda"}]
    src, url, kind = _resolve_interaction_source(["ibuprofen", "naproxen"], prov)
    assert src == OPENFDA_ANALYSIS_SOURCE, src
    assert kind == ATTR_OPENFDA_ANALYSIS, kind
    assert "setid=WSET" not in (url or ""), f"borrowed a foreign setid: {url!r}"
    assert "drugInfo.cfm?setid=" not in (url or "")


def test_attribution_kind_set_per_tier_via_endpoint():
    """The STABLE attribution_kind enum (what the frontend renders honesty from) is set
    correctly per tier. What breaks if this fails: the frontend keys the honesty marker
    off attribution_kind — a wrong/missing kind mis-renders (or drops) the marker."""
    # DailyMed-grounded main path.
    dm = {"warfarin": _FakeDMLabel("warfarin", "SETID-WARF", _DM_PASSAGE),
          "amoxicillin": _FakeDMLabel("amoxicillin", "SETID-AMOX", "text")}
    data, _ = _run_verify(dm, {}, _LLM_ONE_INTERACTION, ["warfarin", "amoxicillin"])
    assert data["interactions"][0]["attribution_kind"] == ATTR_DAILYMED_GROUNDED

    # No-label fallback path.
    llm = ('{"interactions": [{"drugs": ["zzalpha", "zzbeta"], "severity": "Minor", '
           '"description": "d", "recommendation": "r"}], "summary": "s", "risk_level": "Minor"}')
    data2, _ = _run_verify({}, {}, llm, ["zzalpha", "zzbeta"])
    for it in data2["interactions"]:
        assert it["attribution_kind"] == ATTR_NO_LABEL, it["attribution_kind"]


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL  {name}: {e}")
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"ERROR {name}: {type(e).__name__}: {e}")
    print(f"\n{'ALL PASS' if failures == 0 else f'{failures} FAILED'}")
    sys.exit(1 if failures else 0)
