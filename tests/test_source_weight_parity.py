# -*- coding: utf-8 -*-
"""PARITY GATE for the source-weighting ACTIVATION (PRD §2.10.3).

THE pre-ship evidence for turning SOURCE_WEIGHT_ACTIVE ON: the LIVE-activated ranking
(retrieve(source_weight_active=True)) must equal the ranking the SHADOW already logged
for the same pool. If the activation seam differed from the shadow measurement point,
the shadow's v198 data would not predict live behavior.

Two levels of proof:
  1. PURE PARITY — rank_by_composite_v1(pool) order == build_shadow_record(pool)'s
     V1_rank order, over many synthetic pools (incl. ties + promotion across the cutoff).
     Both are pure functions of the pool; this proves they compute the identical V1
     ordering because they share classify_tier / source_weight / tier_weight / the V1
     formula / the stable sort.
  2. SEAM PARITY (end-to-end) — through the REAL retrieve() + reranker (LLM/search
     stubbed for determinism): activation-ON returns exactly the shadow's V1 top_k, and
     activation-OFF is byte-identical to a no-flag run (nothing dropped/added; only order).

Run: python tests/test_source_weight_parity.py   (or via pytest)
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("TEST_MODE", "true")

from api.models.schemas import RetrievedDocument, SourceType, CredibilityLevel  # noqa: E402
from api.services import source_weight_shadow as sws  # noqa: E402

TOP_K = 5


# ── Level 1: pure parity (rank_by_composite_v1 == build_shadow_record V1_rank) ─────────
def _doc(i, source_type, pubtypes, title=""):
    return RetrievedDocument(
        content=f"content {i} " * 5, source_type=source_type, source_id=f"SRC:{i}",
        title=title or f"Title {i}", url=f"https://x/{i}",
        credibility=CredibilityLevel.OFFICIAL if source_type == SourceType.FDA
        else CredibilityLevel.PEER_REVIEWED,
        year="2023", relevance_score=0.5, publication_types=pubtypes or [],
    )


def _shadow_v1_order(pool):
    """The shadow's V1 ordering: source_ids sorted by V1_rank asc (0 = top)."""
    rec = sws.build_shadow_record(pool, top_k=TOP_K)
    per = rec["per_doc"]
    return [d["source_id"] for d in sorted(per, key=lambda d: d["V1_rank"])]


def _synthetic_pools():
    """Deterministic pools spanning: label-above-study inversion, ties, and a label doc
    sitting BELOW the rerank cutoff that V1 promotes across it."""
    fda = lambda i, rr: (_doc(i, SourceType.FDA, []), rr)                 # tier2 ×1.5, sw ×1.5 → 2.25
    tfda = lambda i, rr: (_doc(i, SourceType.TFDA, []), rr)              # tier2 ×1.5, sw ×1.5 → 2.25
    local = lambda i, rr: (_doc(i, SourceType.LOCAL, []), rr)           # tier2 ×1.5, sw ×1.5 → 2.25
    obs = lambda i, rr: (_doc(i, SourceType.PUBMED, ["Observational Study"]), rr)  # tier4 ×1.0, sw ×1.0
    rct = lambda i, rr: (_doc(i, SourceType.PUBMED, ["Randomized Controlled Trial"]), rr)  # tier3 ×1.2
    guide = lambda i, rr: (_doc(i, SourceType.PUBMED, ["Practice Guideline"]), rr)  # tier1 ×2.0
    case = lambda i, rr: (_doc(i, SourceType.PUBMED, ["Case Reports"]), rr)         # tier5 ×0.7

    pools = []
    # A: classic label-drowned-by-studies — FDA label reranked low, V1 lifts it.
    pools.append([obs(0, 0.95), obs(1, 0.90), rct(2, 0.85), obs(3, 0.80), fda(4, 0.55), obs(5, 0.50)])
    # B: two labels + a guideline competing at the top.
    pools.append([obs(0, 0.92), fda(1, 0.70), guide(2, 0.60), tfda(3, 0.65), case(4, 0.99), obs(5, 0.88)])
    # C: exact-tie V1 (rr chosen so products collide) — tie must break by reranked order.
    #    obs rr=0.90 → V1 0.90 ; fda rr=0.40 → V1 0.90. reranked order: obs(0) before fda(1).
    pools.append([obs(0, 0.90), fda(1, 0.40), obs(2, 0.90), rct(3, 0.75), obs(4, 0.30)])
    # D: label BELOW the top_k cutoff that V1 promotes across it (pool > top_k).
    pools.append([obs(0, 0.99), obs(1, 0.95), obs(2, 0.92), obs(3, 0.90), obs(4, 0.88), fda(5, 0.62), obs(6, 0.55)])
    # E: local-corpus (cached FDA labeling) tier-2 promotion — the load-bearing founder decision.
    pools.append([obs(0, 0.93), rct(1, 0.80), local(2, 0.58), case(3, 0.99), obs(4, 0.70)])
    # F: all same source+tier (no reorder expected — V1 order == rerank order).
    pools.append([obs(0, 0.90), obs(1, 0.80), obs(2, 0.70), obs(3, 0.60), obs(4, 0.50)])
    return pools


def test_pure_parity_rank_equals_shadow_v1():
    for n, pool in enumerate(_synthetic_pools()):
        live_order = [d.source_id for d in sws.rank_by_composite_v1(pool)]
        shadow_order = _shadow_v1_order(pool)
        assert live_order == shadow_order, (
            f"POOL {n} parity break:\n live  ={live_order}\n shadow={shadow_order}")
        # top_k slice parity (what the user actually sees).
        assert live_order[:TOP_K] == shadow_order[:TOP_K]


def test_pure_parity_does_not_mutate_scores():
    pool = _synthetic_pools()[0]
    before = [(d.source_id, d.relevance_score) for d, _ in pool]
    sws.rank_by_composite_v1(pool)
    after = [(d.source_id, d.relevance_score) for d, _ in pool]
    assert before == after, "rank_by_composite_v1 must not mutate doc.relevance_score"


def test_reorder_is_pure_permutation_no_drop_or_add():
    for pool in _synthetic_pools():
        src_in = sorted(d.source_id for d, _ in pool)
        src_out = sorted(d.source_id for d in sws.rank_by_composite_v1(pool))
        assert src_in == src_out, "activation must only reorder — never drop/add a source"


# ── Level 2: seam parity (end-to-end through real retrieve() + reranker) ───────────────
def _make_docs():
    """8 docs: i%3==0 → FDA label (tier2), else PubMed observational (tier4)."""
    return [
        RetrievedDocument(
            content=f"Doc about warfarin bleeding risk number {i}. " * 3,
            source_type=(SourceType.FDA if i % 3 == 0 else SourceType.PUBMED),
            source_id=f"SRC:{i}", title=f"Title {i}", url=f"https://x/{i}",
            credibility=CredibilityLevel.OFFICIAL if i % 3 == 0 else CredibilityLevel.PEER_REVIEWED,
            year="2023", relevance_score=0.5 + i * 0.01,
            publication_types=([] if i % 3 == 0 else ["Observational Study"]))
        for i in range(8)
    ]


def _build_stub_retriever():
    from api.rag.retriever import HybridRetriever
    r = HybridRetriever(enable_local=True, enable_pubmed=False, enable_fda=False, enable_tfda=False)

    async def _fake_rewrite(query):
        return ["warfarin bleeding risk"]
    r._rewrite_query = _fake_rewrite

    async def _fake_local(query, max_results):
        return _make_docs()
    r._search_local = _fake_local

    async def _fake_filter(original_query, documents):
        return documents
    r._filter_by_relevance = _fake_filter

    class _StubResp:
        def __init__(self, content):
            self.content = content
            self.input_tokens = 0
            self.output_tokens = 0

    async def _fake_complete(req):
        # scores in INPUT order → doc i gets score below; rerank sorts desc.
        return _StubResp("[30, 40, 50, 60, 70, 80, 90, 95]")
    r.reranker._provider.complete = _fake_complete
    return r


def test_seam_activation_on_equals_shadow_v1_topk():
    """The live-activated top_k == the V1 top_k the shadow logs for the same pool."""
    async def run():
        r = _build_stub_retriever()
        # One call: shadow captures the pool AND activation reorders — same pool, so the
        # returned docs must equal the shadow's V1 top_k derived from that very sink.
        sink = []
        docs_on, status = await r.retrieve("warfarin safety", max_results=TOP_K,
                                           shadow_sink=sink, source_weight_active=True)
        return docs_on, status, sink
    docs_on, status, sink = asyncio.run(run())
    assert status == "ok"
    live_topk = [d.source_id for d in docs_on]
    shadow_v1_topk = _shadow_v1_order(sink)[:TOP_K]
    # THE GATE: live activation == the shadow's V1 top_k for the same pool.
    assert live_topk == shadow_v1_topk, (
        f"SEAM PARITY BREAK:\n live  ={live_topk}\n shadow={shadow_v1_topk}")
    # Concrete effect (post-rerank the desc-sorted pool gets scores 30..95, so doc0=0.95…
    # doc7=0.30; FDA labels are docs 0/3/6 → ×2.25). V1 lifts the low-reranked FDA label
    # SRC:6 (rerank rank 6) INTO the top-5 and SRC:3 up to rank 1 — the §2.10.3 label-
    # above-study effect. (SRC:6 vs SRC:1 order rides a float detail — 0.4×1.5×1.5 =
    # 0.9000000000000001 > 0.9 — which is identical on both paths, hence parity-safe.)
    assert live_topk == ["SRC:0", "SRC:3", "SRC:6", "SRC:1", "SRC:2"], live_topk
    # Robust claim independent of the float tie: the bottom-reranked FDA label is promoted
    # across the cutoff (present ON, absent OFF).
    assert "SRC:6" in live_topk


def test_seam_activation_off_is_byte_identical_to_today():
    """SOURCE_WEIGHT_ACTIVE OFF → returned order == a plain no-flag run (rerank order)."""
    def snap(docs):
        return [(d.source_id, round(d.relevance_score, 6), d.to_citation(i + 1).id)
                for i, d in enumerate(docs)]

    async def run():
        r1 = _build_stub_retriever()
        base, _ = await r1.retrieve("warfarin safety", max_results=TOP_K)
        r2 = _build_stub_retriever()
        off, _ = await r2.retrieve("warfarin safety", max_results=TOP_K, source_weight_active=False)
        return snap(base), snap(off)

    base, off = asyncio.run(run())
    assert base == off, f"OFF must be byte-identical:\n base={base}\n off ={off}"
    # OFF is the plain rerank order (desc by reranked relevance_score) = SRC:0..SRC:4;
    # note SRC:6 (an FDA label) is NOT in the OFF top-5 — activation is what promotes it.
    assert [s for s, _, _ in off] == ["SRC:0", "SRC:1", "SRC:2", "SRC:3", "SRC:4"], off
    assert "SRC:6" not in [s for s, _, _ in off]


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
