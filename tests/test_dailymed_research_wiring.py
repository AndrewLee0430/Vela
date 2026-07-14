# -*- coding: utf-8 -*-
"""B-2 Phase 2 guard tests: DailyMed as the 5th Research retrieval source.

Covers the two behaviours the founder decisions pin:
  - multi-chunk collapse: sub-chunks (…#{loinc}~{i}) of the SAME section → ONE citation;
  - section-level granularity: DISTINCT sections of the same drug (…#{loinc_a} vs
    …#{loinc_b}) → SEPARATE citations (do NOT dedup on setid);
plus the source-weighting Tier-2 classification the SOURCE_WEIGHT_ACTIVE path relies on.

`_collapse_subchunks` does not use `self`, so we invoke it unbound (HybridRetriever
._collapse_subchunks(None, docs)) — no store/provider construction, no network.
"""
from api.models.schemas import RetrievedDocument, SourceType, CredibilityLevel
from api.rag.retriever import HybridRetriever
from api.services.source_weight_shadow import classify_tier, source_weight, _source_key

_URL = "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=SETID"


def _dm(source_id: str, title: str, score: float) -> RetrievedDocument:
    return RetrievedDocument(
        content="section text", source_type=SourceType.DAILYMED, source_id=source_id,
        title=title, url=_URL, credibility=CredibilityLevel.OFFICIAL, relevance_score=score,
    )


def _collapse(docs):
    return HybridRetriever._collapse_subchunks(None, docs)


def test_subchunks_of_one_section_collapse_to_one():
    """Two ~0/~1 chunks of the SAME section render as ONE citation (highest-ranked kept)."""
    base = "DailyMed:SETID#43685-7"
    docs = [_dm(base + "~0", "Cymbalta (duloxetine) — Warnings and Precautions", 0.82),
            _dm(base + "~1", "Cymbalta (duloxetine) — Warnings and Precautions", 0.71)]
    out = _collapse(docs)
    assert len(out) == 1
    assert out[0].source_id == base + "~0"   # first (highest-ranked) chunk survives


def test_distinct_sections_of_one_drug_stay_separate():
    """Different LOINC sections of the SAME drug are SEPARATE citations (section-level)."""
    docs = [_dm("DailyMed:SETID#34073-7", "Warfarin — Drug Interactions", 0.80),
            _dm("DailyMed:SETID#34070-3", "Warfarin — Contraindications", 0.70)]
    out = _collapse(docs)
    assert len(out) == 2
    assert {d.source_id for d in out} == {"DailyMed:SETID#34073-7", "DailyMed:SETID#34070-3"}


def test_subchunk_and_distinct_section_mixed():
    """~0/~1 of one section collapse; a different section of the same drug survives → 2 total."""
    docs = [_dm("DailyMed:SETID#43685-7~0", "Drug — Warnings", 0.9),
            _dm("DailyMed:SETID#43685-7~1", "Drug — Warnings", 0.8),
            _dm("DailyMed:SETID#34073-7", "Drug — Drug Interactions", 0.6)]
    out = _collapse(docs)
    assert len(out) == 2
    assert sorted(d.source_id for d in out) == ["DailyMed:SETID#34073-7", "DailyMed:SETID#43685-7~0"]


def test_non_dailymed_passthrough_unchanged():
    """Non-DailyMed source_ids (no '~') pass through untouched — collapse is a no-op for them."""
    docs = [
        RetrievedDocument(content="a", source_type=SourceType.PUBMED, source_id="PMID:12345678",
                          title="t", url="u", credibility=CredibilityLevel.PEER_REVIEWED, relevance_score=0.9),
        RetrievedDocument(content="b", source_type=SourceType.TFDA, source_id="TFDA:衛署藥製字第057803號",
                          title="t2", url="u2", credibility=CredibilityLevel.OFFICIAL, relevance_score=0.8),
    ]
    out = _collapse(docs)
    assert len(out) == 2
    assert [d.source_id for d in out] == ["PMID:12345678", "TFDA:衛署藥製字第057803號"]


def test_dailymed_classifies_tier2_x1_5():
    """The SOURCE_WEIGHT_ACTIVE composite must see a DailyMed doc as a Tier-2 ×1.5 label source."""
    d = _dm("DailyMed:SETID#34073-7", "W — Drug Interactions", 0.8)
    tier, reason = classify_tier(d)
    assert _source_key(d) == "dailymed"
    assert tier == 2, f"expected Tier 2, got {tier} ({reason})"
    assert source_weight(d) == 1.5


# ── Phase 4: debt-(2) host-map — the share-OG render must say "DailyMed", not "RxNorm" ──
from api.services.share_renderer import _detect_source_type, _SOURCE_TYPE_CONFIG

_DM_URL = "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=SETID"


def test_dailymed_source_type_renders_dailymed_label():
    """A live DailyMed citation (source_type present) renders the DailyMed chip in share-OG."""
    slug = _detect_source_type({"source_type": "dailymed", "url": _DM_URL})
    assert slug == "dailymed"
    assert _SOURCE_TYPE_CONFIG["dailymed"]["label"] == "DailyMed"


def test_dailymed_host_maps_to_dailymed_not_rxnorm():
    """A source_type-absent (old/cached) citation with the DailyMed host resolves via the
    host-map to 'dailymed' — the debt-(2) drift ('rxnorm') is fixed."""
    slug = _detect_source_type({"url": _DM_URL})   # no source_type → host-map fallback
    assert slug == "dailymed", f"host-map drift not fixed: got {slug!r}"
    assert _SOURCE_TYPE_CONFIG[slug]["label"] == "DailyMed"


def test_rxnav_host_still_maps_rxnorm():
    """Regression: the rxnav host must STILL map to rxnorm (only the DailyMed host changed)."""
    slug = _detect_source_type({"url": "https://rxnav.nlm.nih.gov/REST/rxcui.json"})
    assert slug == "rxnorm"
