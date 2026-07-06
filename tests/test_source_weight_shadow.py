# -*- coding: utf-8 -*-
"""Source-weighting SHADOW — tier classifier + composite record unit tests (v198).

Business rule pinned (CLAUDE.md Rule 17): the shadow's would-be rankings are only
trustworthy if tier classification is deterministic and matches the PRD §2.10.6 map.
These tests pin the publication_type mapping, the title/journal keyword fallback, the
source-default tiers (incl. the founder-flagged local default), and the composite
record's rank/inversion math. Pure functions — no LLM, no network.

Run: python tests/test_source_weight_shadow.py   (or via pytest)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services import source_weight_shadow as sw  # noqa: E402


class _Doc:
    """Minimal stand-in for RetrievedDocument (classifier reads attrs only)."""
    def __init__(self, source_type="pubmed", publication_types=None, title="", journal="",
                 year=None, source_id="X"):
        self.source_type = source_type
        self.publication_types = publication_types
        self.title = title
        self.journal = journal
        self.year = year
        self.source_id = source_id


# ── publication_type mapping ────────────────────────────────────────────────────
def test_pubtype_guideline_is_tier1():
    assert sw.classify_tier(_Doc(publication_types=["Practice Guideline"]))[0] == 1


def test_pubtype_systematic_review_and_meta_are_tier2():
    assert sw.classify_tier(_Doc(publication_types=["Systematic Review"]))[0] == 2
    assert sw.classify_tier(_Doc(publication_types=["Meta-Analysis"]))[0] == 2


def test_pubtype_rct_is_tier3():
    assert sw.classify_tier(_Doc(publication_types=["Randomized Controlled Trial"]))[0] == 3


def test_pubtype_observational_is_tier4():
    assert sw.classify_tier(_Doc(publication_types=["Observational Study"]))[0] == 4


def test_pubtype_case_report_is_tier5():
    assert sw.classify_tier(_Doc(publication_types=["Case Reports"]))[0] == 5


def test_most_specific_lowest_tier_wins():
    # A doc tagged both RCT (3) and Meta-Analysis (2) → the stronger (2) wins.
    t, reason = sw.classify_tier(_Doc(publication_types=["Randomized Controlled Trial", "Meta-Analysis"]))
    assert t == 2, f"expected tier 2, got {t} ({reason})"


# ── keyword fallback (no/uninformative publication_type) ─────────────────────────
def test_title_keyword_systematic_review():
    assert sw.classify_tier(_Doc(title="A systematic review of statin safety"))[0] == 2


def test_title_keyword_guideline():
    assert sw.classify_tier(_Doc(title="2025 Clinical Practice Guideline for Hypertension"))[0] == 1


def test_title_keyword_survey_is_tier5():
    assert sw.classify_tier(_Doc(title="A survey of physician knowledge, attitude and practice"))[0] == 5


def test_journal_hint_cochrane():
    assert sw.classify_tier(_Doc(journal="Cochrane Database of Systematic Reviews"))[0] == 2


def test_pubmed_default_when_nothing_matches():
    t, reason = sw.classify_tier(_Doc(title="Some ordinary mechanistic paper"))
    assert t == sw.DEFAULT_TIER == 4
    assert "default" in reason


# ── source-default tiers ─────────────────────────────────────────────────────────
def test_label_sources_default_tier2():
    for st in ("fda", "tfda", "dailymed"):
        t, reason = sw.classify_tier(_Doc(source_type=st))
        assert t == 2, f"{st} should be Tier 2, got {t}"
        assert "label-source default" in reason


def test_local_default_tier2_and_flagged():
    t, reason = sw.classify_tier(_Doc(source_type="local"))
    assert t == 2
    assert "FOUNDER-FLAGGED" in reason, "local default must carry the founder-review flag"


def test_weights_match_spec():
    assert sw.source_weight(_Doc(source_type="fda")) == 1.5
    assert sw.source_weight(_Doc(source_type="pubmed")) == 1.0
    assert sw.TIER_WEIGHTS == {1: 2.0, 2: 1.5, 3: 1.2, 4: 1.0, 5: 0.7}


# ── composite record math ────────────────────────────────────────────────────────
def test_record_variant_ranks_and_inversion():
    # Construct a pool where a label (FDA, Tier 2, ×1.5×1.5=2.25 multiplier) is
    # currently BELOW a Tier-4 observational PubMed study (×1.0×1.0=1.0), but has a
    # lower rerank score. V1 should invert them.
    label = _Doc(source_type="fda", source_id="FDA:1", title="Official label")
    study = _Doc(source_type="pubmed", publication_types=["Observational Study"],
                 source_id="PMID:2", title="Observational study")
    # pool order = reranker order (study first at 0.80, label second at 0.60)
    pool = [(study, 0.80), (label, 0.60)]
    rec = sw.build_shadow_record(pool, top_k=1)

    # current ranks
    assert rec["per_doc"][0]["current_rank"] == 0  # study
    assert rec["per_doc"][1]["current_rank"] == 1  # label
    # V1: study 0.80×1.0×1.0=0.80 ; label 0.60×1.5×1.5=1.35 → label now rank 0
    label_row = next(d for d in rec["per_doc"] if d["source_id"] == "FDA:1")
    study_row = next(d for d in rec["per_doc"] if d["source_id"] == "PMID:2")
    assert label_row["V1_rank"] == 0 and study_row["V1_rank"] == 1
    # top-1 set changed; label entered, study left
    assert rec["summary"]["top_k_changed_under_V1"] is True
    assert rec["summary"]["V1_entered_topk"] == ["FDA:1"]
    assert rec["summary"]["V1_left_topk"] == ["PMID:2"]
    # inversion flag recorded; label promoted into top_k
    assert len(rec["inversion_flags"]) == 1
    assert rec["label_promoted_into_topk"] == ["FDA:1"]
    # tier distribution: one Tier-2 (label) + one Tier-4 (study)
    assert rec["tier_distribution"] == {"2": 1, "4": 1}


def test_record_no_change_when_order_already_authority_aligned():
    label = _Doc(source_type="fda", source_id="FDA:1")
    study = _Doc(source_type="pubmed", publication_types=["Observational Study"], source_id="PMID:2")
    pool = [(label, 0.90), (study, 0.50)]  # label already on top
    rec = sw.build_shadow_record(pool, top_k=1)
    assert rec["summary"]["top_k_changed_under_V1"] is False
    assert rec["inversion_flags"] == []
    assert rec["label_promoted_into_topk"] == []


def test_to_sink_dict_drops_query_and_titles():
    pool = [(_Doc(source_type="fda", source_id="FDA:1", title="secret title"), 0.7)]
    rec = sw.build_shadow_record(pool, top_k=1, query_label="raw user query")
    sink = sw.to_sink_dict(rec)
    assert "query_label" not in sink
    assert all("title" not in d for d in sink["per_doc"])
    assert sink["per_doc"][0]["source_id"] == "FDA:1"  # non-title fields kept


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
    print(f"\n{'ALL PASS' if failures == 0 else f'{failures} FAILED'}")
    sys.exit(1 if failures else 0)
