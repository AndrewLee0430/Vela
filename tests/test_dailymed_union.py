# -*- coding: utf-8 -*-
"""Lever-1: DailyMed-only K-union rewrite set (K parallel _rewrite_query calls + raw augment)."""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("TEST_MODE", "true")
from api.rag import retriever as rmod  # noqa: E402


def _stub_retriever(rewrite_batches):
    """rewrite_batches: list of lists; each _rewrite_query call pops the next batch."""
    r = rmod.HybridRetriever(enable_local=False, enable_pubmed=False, enable_fda=False,
                             enable_tfda=False, enable_dailymed=True)
    calls = {"n": 0}
    seq = list(rewrite_batches)

    async def _fake_rewrite(q):
        i = calls["n"]; calls["n"] += 1
        return seq[i] if i < len(seq) else seq[-1]
    r._rewrite_query = _fake_rewrite
    r._rw_calls = calls
    return r


def test_union_dedupes_across_k_calls_and_appends_raw():
    r = _stub_retriever([["a", "b"], ["b", "c"], ["c", "d"]])
    out = asyncio.run(r._dailymed_union_queries("RAWQ", k=3))
    assert out == ["a", "b", "c", "d", "RAWQ"]          # union first-seen + raw appended
    assert r._rw_calls["n"] == 3                          # exactly k calls


def test_raw_not_duplicated_if_already_emitted():
    r = _stub_retriever([["RAWQ", "b"]])
    out = asyncio.run(r._dailymed_union_queries("RAWQ", k=1))
    assert out == ["RAWQ", "b"]                           # raw already present → not re-appended


def test_calls_run_in_parallel():
    import time
    r = rmod.HybridRetriever(enable_local=False, enable_pubmed=False, enable_fda=False,
                             enable_tfda=False, enable_dailymed=True)

    async def _slow(q):
        await asyncio.sleep(0.2); return ["q1", "q2"]
    r._rewrite_query = _slow

    async def run():
        t0 = time.perf_counter()
        await r._dailymed_union_queries("RAWQ", k=3)
        return time.perf_counter() - t0
    dt = asyncio.run(run())
    assert dt < 0.4, f"k=3 parallel should be ~0.2s, got {dt:.2f}s (serial would be ~0.6s)"


def test_returns_empty_when_dailymed_disabled():
    r = rmod.HybridRetriever(enable_local=False, enable_pubmed=False, enable_fda=False,
                             enable_tfda=False, enable_dailymed=False)
    called = {"n": 0}

    async def _fake(q):
        called["n"] += 1; return ["x"]
    r._rewrite_query = _fake
    out = asyncio.run(r._dailymed_union_queries("RAWQ", k=3))
    assert out == [] and called["n"] == 0                 # no wasted rewrite calls when DM off


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
