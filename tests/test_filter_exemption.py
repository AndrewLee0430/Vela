# -*- coding: utf-8 -*-
"""Official-label SAFETY-section exemption (DailyMed recall-miss [P1] surface iii).

`_filter_by_relevance` (gpt-4.1-mini) sometimes drops a RETRIEVED-above-threshold DailyMed
safety section (e.g. #34073-7 Drug Interactions) it should keep. This ADDITIVE exemption
re-adds a dropped whitelisted official-label safety section. It must:
  - re-add a dropped whitelisted section (interactions/contraindications/warnings/boxed);
  - be ADDITIVE — never drop a doc the filter kept, never reorder the kept docs;
  - NOT re-add a dropped DESCRIPTIVE section (indications/dosage);
  - NOT duplicate a section the filter already kept;
  - only operate on RETRIEVED candidates (it cannot resurrect a never-retrieved doc).

Provider stubbed to return a fixed relevance-filter index list (no network).

Run: python tests/test_filter_exemption.py  (or venv/Scripts/pytest tests/test_filter_exemption.py)
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("TEST_MODE", "true")

from api.models.schemas import RetrievedDocument, SourceType, CredibilityLevel  # noqa: E402
from api.rag import retriever as retriever_mod  # noqa: E402


class _StubResp:
    def __init__(self, content):
        self.content = content
        self.input_tokens = 0
        self.output_tokens = 0


def _retriever_with_filter_output(index_json: str):
    """HybridRetriever with all sources OFF (no store loads) and the relevance-filter LLM
    stubbed to return `index_json` (the kept-index array)."""
    r = retriever_mod.HybridRetriever(enable_local=False, enable_pubmed=False, enable_fda=False,
                                      enable_tfda=False, enable_dailymed=False)

    async def _complete(req):
        return _StubResp(index_json)
    r._provider.complete = _complete
    return r


def _dm(loinc, i, score=0.63):
    return RetrievedDocument(
        content=f"DailyMed section {loinc} content about the drug's {loinc}. " * 3,
        source_type=SourceType.DAILYMED, source_id=f"DailyMed:setid-{i}#{loinc}",
        title=f"DRUG (generic) — {loinc}", url="https://dailymed/x",
        credibility=CredibilityLevel.OFFICIAL, year="2023", relevance_score=score)


def _pub(i, score=0.85):
    return RetrievedDocument(
        content=f"PubMed study {i} about the drug interaction. " * 3,
        source_type=SourceType.PUBMED, source_id=f"PMID:{i}", title=f"Study {i}",
        url="https://pubmed/x", credibility=CredibilityLevel.PEER_REVIEWED, year="2023",
        relevance_score=score)


# ── the whitelist constant ────────────────────────────────────────────────────────
def test_whitelist_is_exactly_the_four_safety_loincs():
    wl = set(retriever_mod._SAFETY_SECTION_WHITELIST)
    assert wl == {"34073-7", "34070-3", "43685-7", "34066-1"}, wl


# ── re-add a dropped whitelisted section ──────────────────────────────────────────
def test_dropped_interaction_section_is_readded():
    # docs: [0]=pubmed(kept) [1]=pubmed(kept) [2]=DailyMed #34073-7 interactions (filter drops it)
    docs = [_pub(1), _pub(2), _dm("34073-7", 3)]
    r = _retriever_with_filter_output("[0, 1]")   # filter keeps 0,1 — drops the interaction section
    out = asyncio.run(r._filter_by_relevance("is drug X safe with warfarin", docs))
    ids = [d.source_id for d in out]
    assert "DailyMed:setid-3#34073-7" in ids, f"interaction section must be re-added: {ids}"


def test_all_four_whitelisted_loincs_are_readded():
    for loinc in ("34073-7", "34070-3", "43685-7", "34066-1"):
        docs = [_pub(1), _dm(loinc, 9)]
        r = _retriever_with_filter_output("[0]")  # drops the DailyMed section
        out = asyncio.run(r._filter_by_relevance("safety q", docs))
        assert any(d.source_id == f"DailyMed:setid-9#{loinc}" for d in out), f"{loinc} not re-added"


# ── additive property ─────────────────────────────────────────────────────────────
def test_additive_kept_docs_unchanged_and_not_reordered():
    docs = [_pub(1), _pub(2), _dm("34070-3", 3)]
    r = _retriever_with_filter_output("[0, 1]")
    out = asyncio.run(r._filter_by_relevance("q", docs))
    # the filter's kept docs (0,1) must appear FIRST, in filter order, unchanged
    assert [d.source_id for d in out[:2]] == ["PMID:1", "PMID:2"], [d.source_id for d in out]
    # exemption is an ADDITION at the end
    assert out[-1].source_id == "DailyMed:setid-3#34070-3"
    assert len(out) == 3


def test_no_kept_doc_is_ever_dropped():
    docs = [_pub(1), _dm("34073-7", 2), _pub(3)]
    r = _retriever_with_filter_output("[0, 1, 2]")  # filter keeps ALL
    out = asyncio.run(r._filter_by_relevance("q", docs))
    assert {d.source_id for d in out} == {"PMID:1", "DailyMed:setid-2#34073-7", "PMID:3"}


# ── negative cases ────────────────────────────────────────────────────────────────
def test_descriptive_section_not_readded():
    # #34067-9 indications is DESCRIPTIVE, NOT whitelisted → stays dropped
    docs = [_pub(1), _dm("34067-9", 3)]
    r = _retriever_with_filter_output("[0]")
    out = asyncio.run(r._filter_by_relevance("q", docs))
    assert all("34067-9" not in d.source_id for d in out), "indications must NOT be re-added"


def test_kept_whitelisted_section_not_duplicated():
    docs = [_pub(1), _dm("34073-7", 3)]
    r = _retriever_with_filter_output("[0, 1]")  # filter already KEEPS the section
    out = asyncio.run(r._filter_by_relevance("q", docs))
    n = sum(1 for d in out if d.source_id == "DailyMed:setid-3#34073-7")
    assert n == 1, f"section must appear once, got {n}"


def test_non_dailymed_without_loinc_not_exempted():
    # an FDA whole-label doc (no #loinc in source_id) is not a whitelisted section
    fda = RetrievedDocument(content="fda label", source_type=SourceType.FDA,
                            source_id="fda-drugX-label", title="DRUG (generic)", url="u",
                            credibility=CredibilityLevel.OFFICIAL, relevance_score=0.75)
    docs = [_pub(1), fda]
    r = _retriever_with_filter_output("[0]")  # drops the fda doc
    out = asyncio.run(r._filter_by_relevance("q", docs))
    assert all(d.source_id != "fda-drugX-label" for d in out), "FDA whole-label must not be exempted"


def test_exemption_only_operates_on_retrieved_candidates():
    # exemption iterates `documents` only — it cannot invent a section not in the candidate list
    docs = [_pub(1), _pub(2)]  # no DailyMed section present at all
    r = _retriever_with_filter_output("[0]")
    out = asyncio.run(r._filter_by_relevance("q", docs))
    assert all(not d.source_id.startswith("DailyMed:") for d in out)
    assert [d.source_id for d in out] == ["PMID:1"]


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
