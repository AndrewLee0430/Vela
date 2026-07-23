# -*- coding: utf-8 -*-
"""Lever-2 additive cut-exemption (recall-miss [P1]): re-add a whitelisted DailyMed safety
section the candidates[:20] cut would drop. ADDITIVE — never drops/reorders a survived doc."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("TEST_MODE", "true")
from api.models.schemas import RetrievedDocument, SourceType, CredibilityLevel  # noqa: E402
from api.rag import retriever as rmod  # noqa: E402


def _dm(loinc, i, score=0.61):
    return RetrievedDocument(content=f"DailyMed {loinc} {i} " * 3, source_type=SourceType.DAILYMED,
                             source_id=f"DailyMed:setid-{i}#{loinc}", title=f"DRUG — {loinc}",
                             url="u", credibility=CredibilityLevel.OFFICIAL, year="2023", relevance_score=score)


def _pub(i, score=0.85):
    return RetrievedDocument(content=f"study {i} " * 3, source_type=SourceType.PUBMED,
                             source_id=f"PMID:{i}", title=f"Study {i}", url="u",
                             credibility=CredibilityLevel.PEER_REVIEWED, year="2023", relevance_score=score)


def test_below_cut_interaction_section_is_readded():
    section = _dm("34073-7", 9)
    candidates = [_pub(1), _pub(2)]
    unique = candidates + [section]
    out = rmod._cut_exemption(candidates, unique)
    assert "DailyMed:setid-9#34073-7" in [d.source_id for d in out]


def test_additive_survivors_unchanged_and_not_reordered():
    section = _dm("34070-3", 9)
    candidates = [_pub(1), _pub(2)]
    unique = candidates + [section]
    out = rmod._cut_exemption(candidates, unique)
    assert [d.source_id for d in out[:2]] == ["PMID:1", "PMID:2"]
    assert out[-1].source_id == "DailyMed:setid-9#34070-3"
    assert len(out) == 3


def test_exempted_appended_after_survivor_even_when_higher_score():
    # The exempted below-cut section is given a HIGHER relevance_score than the survivor.
    # A pure-append helper keeps the survivor FIRST; a mutant that sorts by score would put
    # the section first. This proves order-independence (the additive contract), not just "append".
    survivor = _pub(1, score=0.5)
    section = _dm("34073-7", 9, score=0.9)      # higher score, but was below the cut
    candidates = [survivor]
    unique = [survivor, section]
    out = rmod._cut_exemption(candidates, unique)
    assert [d.source_id for d in out] == ["PMID:1", "DailyMed:setid-9#34073-7"], \
        f"survivor must stay first (pure append, not score-sort): {[d.source_id for d in out]}"


def test_all_four_whitelisted_loincs_readded():
    for loinc in ("34073-7", "34070-3", "43685-7", "34066-1"):
        candidates = [_pub(1)]
        unique = candidates + [_dm(loinc, 5)]
        out = rmod._cut_exemption(candidates, unique)
        assert any(d.source_id == f"DailyMed:setid-5#{loinc}" for d in out), loinc


def test_section_already_in_candidates_not_duplicated():
    section = _dm("34073-7", 9)
    candidates = [_pub(1), section]
    unique = candidates
    out = rmod._cut_exemption(candidates, unique)
    assert sum(1 for d in out if d.source_id == "DailyMed:setid-9#34073-7") == 1


def test_descriptive_section_not_readded():
    candidates = [_pub(1)]
    unique = candidates + [_dm("34067-9", 9)]
    out = rmod._cut_exemption(candidates, unique)
    assert all("34067-9" not in d.source_id for d in out)


def test_canary_no_op_when_no_whitelisted_below_cut():
    candidates = [_pub(1), _pub(2)]
    unique = candidates + [_pub(3)]
    out = rmod._cut_exemption(candidates, unique)
    assert [d.source_id for d in out] == ["PMID:1", "PMID:2"]


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print(f"PASS  {name}")
            except AssertionError as e:
                failures += 1; print(f"FAIL  {name}: {e}")
    print(f"\n{'ALL PASS' if not failures else f'{failures} FAILED'}")
    sys.exit(1 if failures else 0)
