# -*- coding: utf-8 -*-
"""Pool-size distribution harvest (MEASUREMENT-ONLY, in-process).

⚠️ TRANSPORT DEVIATION — STATED, NOT HIDDEN.
The baton asked for this via `tests/run_golden_tests.py` (the new `pool_identity` capture).
On this machine that is NOT VIABLE: the box has 8.1 GB RAM with ~1.0 GB free, and the uvicorn
server — which holds three embedding corpora (local 690 + TFDA 10941 + DailyMed 4608) — is
killed by the OS after ~10 requests. Observed twice today: the server log ends cleanly
mid-request with NO traceback (the signature of an external kill, not a crash), and every
subsequent golden case returns ERROR. Only 5 cases of pass 1 survived.

This harness measures the SAME OBJECT through a different transport: it calls
`retriever.retrieve()` in-process, which is exactly the document list the golden runner's
`pool_identity` is derived from (server.py:903 citations <- generator.py:179 <- these docs).
One process instead of two; no generation, no judge. Proven on this machine: the pair-aware
M1 harness completed 120 consecutive retrievals in one process on 2026-07-27.

WHAT IS LOST BY THE DEVIATION: PASS/WARN/FAIL verdicts. The verdict-vs-pool_size correlation
sub-question therefore CANNOT be answered from this run — reported as NOT MEASURED rather
than estimated from the 10 surviving golden-runner records (too thin to support a claim).

NETWORK-NOISE FILTER: identical rule to the pair-aware M1 probe — a run where every source
returned zero docs short-circuits at retriever.py:203-205 returning ("no_results"|"error")
and is EXCLUDED from the denominator and counted separately. `irrelevant` is NOT excluded
(docs were retrieved, the filter dropped them — a real retrieval outcome).

READ-ONLY on product code.
"""
import asyncio, io, json, os, sys, time
from collections import Counter
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(r"C:\Users\andre\projects\Vela")
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TEST_MODE", "true")
os.environ["SOURCE_WEIGHT_ACTIVE"] = "true"          # prod state
from dotenv import load_dotenv                        # noqa: E402
load_dotenv(ROOT / ".env", override=True)
from api.rag.retriever import HybridRetriever         # noqa: E402
from api.server import _annotate_research_question    # noqa: E402

N = int(os.environ.get("POOLSIZE_N", "3"))
OUT = ROOT / "tests" / "results" / f"poolsize_harvest_{time.strftime('%Y%m%d_%H%M%S')}.json"


def load_cases():
    d = json.load(open(ROOT / "tests" / "golden_dataset.json", encoding="utf-8"))
    cases = d if isinstance(d, list) else d.get("cases", [])
    out = []
    for c in cases:
        if c.get("category") != "research":
            continue
        cid = c["id"]
        if cid.startswith("R") or cid.startswith("TB"):
            out.append((cid, c["query"]))
    return out


async def run_case(r, cid, query):
    annotated = _annotate_research_question(query)
    runs = []
    for i in range(N):
        t0 = time.perf_counter()
        try:
            docs, status = await r.retrieve(query=annotated, max_results=5,
                                            source_weight_active=True)
            runs.append({"run": i, "status": status,
                         "latency_s": round(time.perf_counter() - t0, 1),
                         "pool_size": len(docs),
                         "source_ids": [d.source_id for d in docs],
                         "source_types": [str(getattr(d.source_type, "value", d.source_type))
                                          for d in docs]})
        except Exception as e:
            runs.append({"run": i, "error": f"{type(e).__name__}: {e}"})
    return runs


def partition(runs):
    usable, netexc, errored = [], [], []
    for x in runs:
        if "error" in x:
            errored.append(x)
        elif x.get("status") in ("no_results", "error"):
            netexc.append(x)
        else:
            usable.append(x)
    return usable, netexc, errored


def churn(usable):
    """Union turnover across runs. 1.0 = no doc common to all runs; 0.0 = identical pools."""
    sets = [set(u["source_ids"]) for u in usable if u["source_ids"]]
    if len(sets) < 2:
        return None
    union = set().union(*sets)
    inter = set.intersection(*sets)
    pair, n = [], len(sets)
    for a in range(n):
        for b in range(a + 1, n):
            u = sets[a] | sets[b]
            pair.append(len(sets[a] & sets[b]) / len(u) if u else 1.0)
    return {"union": len(union), "intersection": len(inter),
            "turnover": round(1 - len(inter) / len(union), 3) if union else 0.0,
            "mean_pairwise_jaccard": round(sum(pair) / len(pair), 3) if pair else None}


async def main():
    cases = load_cases()
    r = HybridRetriever()
    rep = {"N": N, "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "transport": "in-process retriever.retrieve() (see module docstring for why)",
           "max_results": 5, "source_weight_active": True, "cases": {}}
    print(f"=== pool-size harvest: {len(cases)} cases x N={N} ===\n", flush=True)

    for cid, q in cases:
        runs = await run_case(r, cid, q)
        usable, netexc, errored = partition(runs)
        sizes = [u["pool_size"] for u in usable]
        ch = churn(usable)
        rep["cases"][cid] = {
            "query": q[:90], "runs": runs,
            "usable": len(usable), "network_excluded": len(netexc), "errored": len(errored),
            "pool_sizes": sizes,
            "min": min(sizes) if sizes else None, "max": max(sizes) if sizes else None,
            "mode": Counter(sizes).most_common(1)[0][0] if sizes else None,
            "any_le2": any(s <= 2 for s in sizes), "n_le2": sum(1 for s in sizes if s <= 2),
            "churn": ch,
        }
        rep["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
        e = rep["cases"][cid]
        print(f"  {cid:6} sizes={str(sizes):16} min/max/mode={e['min']}/{e['max']}/{e['mode']}"
              f"  turnover={ch['turnover'] if ch else '—'}"
              f"{'  [EXCL net=%d err=%d]' % (len(netexc), len(errored)) if (netexc or errored) else ''}",
              flush=True)

    rep["complete"] = True
    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
