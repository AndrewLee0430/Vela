# -*- coding: utf-8 -*-
"""Relevance-filter attrition on REAL Research queries — MEASUREMENT ONLY, in-process.

ZERO api/ CHANGE BY CONSTRUCTION. This harness attaches a logging.Handler to the
EXISTING logger `api.rag.retriever` (retriever.py:29) and reads log records that
production already emits today:

    :225  "Retrieved %d docs, %d unique after dedup"          -> merge + dedup
    :75   "[CutExempt] re-added %d ..."                        -> stage-1 exemption
    :531  "Relevance filter: %d -> %d documents kept"          -> THE FILTER
    :527  "[FilterExempt] re-added %d ... : %s"                -> filter exemption
    :291  "Final: %d documents returned"                       -> post-collapse, PRE-slice
    :535  "Relevance filter failed: %s, returning all documents" -> FAIL-OPEN

⚠️ ARITHMETIC NOTE, verified in source: retriever.py:529 does
`filtered = filtered + exempted` BEFORE :531 logs. So the logged OUT count ALREADY
INCLUDES the FilterExempt re-adds. Raw LLM-kept = out - exempted.

⚠️ FAIL-OPEN: when :535 fires the filter did NOT run — a `relevance_score >= 0.45`
threshold ran instead (RELEVANCE_THRESHOLD, retriever.py:32). Those runs are counted
and EXCLUDED from the filter statistics.

PARITY: identical case set / N / flags / transport to tests/results/_poolsize_harvest.py.
READ-ONLY on product code. This file lives under tests/results/ (gitignored).
"""
import asyncio, io, json, logging, os, sys, time
from collections import Counter
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(r"C:\Users\andre\projects\Vela")
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TEST_MODE", "true")
os.environ["SOURCE_WEIGHT_ACTIVE"] = "true"          # prod state, same as the harvest
from dotenv import load_dotenv                        # noqa: E402
load_dotenv(ROOT / ".env", override=True)
from api.rag.retriever import HybridRetriever         # noqa: E402
from api.server import _annotate_research_question    # noqa: E402

N = int(os.environ.get("FILTER_N", "3"))
OUT = ROOT / "tests" / "results" / f"filter_attrition_{time.strftime('%Y%m%d_%H%M%S')}.json"

# ── the capture handler: attached OUTSIDE api/, reads what production already emits ──
LOGGER_NAME = "api.rag.retriever"


class Capture(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.buf = []

    def emit(self, record):
        self.buf.append((record.levelno, record.msg, record.args))

    def reset(self):
        self.buf = []

    def parse(self):
        """-> dict of the stages production logged for ONE retrieve() call."""
        out = {"dedup_in": None, "dedup_unique": None, "cut_exempt_n": 0,
               "filter_in": None, "filter_out": None, "filter_exempt_n": 0,
               "filter_exempt_ids": [], "final_pre_slice": None,
               "fail_open": False, "all_filtered_out": False,
               "rerank_failed": False, "source_weight_inert": False}
        for lvl, msg, args in self.buf:
            if not isinstance(msg, str):
                continue
            if msg.startswith("Retrieved %d docs"):
                out["dedup_in"], out["dedup_unique"] = args[0], args[1]
            elif msg.startswith("[CutExempt]"):
                out["cut_exempt_n"] += args[0]
            elif msg.startswith("Relevance filter: %d -> %d"):
                out["filter_in"], out["filter_out"] = args[0], args[1]
            elif msg.startswith("[FilterExempt]"):
                out["filter_exempt_n"] += args[0]
                out["filter_exempt_ids"] += list(args[1]) if isinstance(args[1], (list, tuple)) else []
            elif msg.startswith("Final: %d documents"):
                out["final_pre_slice"] = args[0]
            elif msg.startswith("Relevance filter failed"):
                out["fail_open"] = True
            elif msg.startswith("Relevance check: all documents filtered out"):
                out["all_filtered_out"] = True
            elif msg.startswith("Rerank failed"):
                out["rerank_failed"] = True
            elif msg.startswith("[SOURCE_WEIGHT_INERT]"):
                out["source_weight_inert"] = True
        return out


def load_cases():
    d = json.load(open(ROOT / "tests" / "golden_dataset.json", encoding="utf-8"))
    cases = d if isinstance(d, list) else d.get("cases", [])
    return [(c["id"], c["query"]) for c in cases
            if c.get("category") == "research" and (c["id"].startswith("R") or c["id"].startswith("TB"))]


async def main():
    lg = logging.getLogger(LOGGER_NAME)
    lg.setLevel(logging.DEBUG)          # harness-side only; api/ untouched
    cap = Capture()
    lg.addHandler(cap)

    cases = load_cases()
    r = HybridRetriever()
    rep = {"N": N, "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "transport": "in-process retriever.retrieve(); stages read from the EXISTING "
                        "api.rag.retriever logger — ZERO api/ change",
           "max_results": 5, "source_weight_active": True,
           "logger_captured": LOGGER_NAME,
           "arithmetic_note": "retriever.py:529 appends the exemption BEFORE :531 logs, so "
                              "filter_out ALREADY INCLUDES filter_exempt_n. "
                              "raw_llm_kept = filter_out - filter_exempt_n.",
           "cases": {}}
    print(f"=== filter attrition: {len(cases)} cases x N={N} ===\n", flush=True)

    for cid, q in cases:
        annotated = _annotate_research_question(q)
        runs = []
        for i in range(N):
            cap.reset()
            t0 = time.perf_counter()
            try:
                docs, status = await r.retrieve(query=annotated, max_results=5,
                                                source_weight_active=True)
                st = cap.parse()
                st.update({"run": i, "status": status,
                           "latency_s": round(time.perf_counter() - t0, 1),
                           "pool_size": len(docs)})
                if st["filter_in"] is not None and st["filter_out"] is not None:
                    st["raw_llm_kept"] = st["filter_out"] - st["filter_exempt_n"]
                    st["removed"] = st["filter_in"] - st["filter_out"]
                    st["removal_rate"] = round(st["removed"] / st["filter_in"], 4) if st["filter_in"] else None
                runs.append(st)
            except Exception as e:
                runs.append({"run": i, "error": f"{type(e).__name__}: {e}"})
        rep["cases"][cid] = {"query": q[:90], "runs": runs}
        rep["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
        sizes = [x.get("pool_size") for x in runs if "pool_size" in x]
        fil = [(x.get("filter_in"), x.get("filter_out")) for x in runs if x.get("filter_in") is not None]
        fo = sum(1 for x in runs if x.get("fail_open"))
        print(f"  {cid:6} pool={str(sizes):12} filter={str(fil):28}"
              f"{'  FAIL_OPEN=%d' % fo if fo else ''}", flush=True)

    rep["complete"] = True
    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}", flush=True)
    lg.removeHandler(cap)


if __name__ == "__main__":
    asyncio.run(main())
