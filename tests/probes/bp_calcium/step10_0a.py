"""SEGMENT 1d · STEP 0a — what does the rewriter's provider call RETURN on "calcium and lisinopril"? (≤ 3 LLM calls)

Wraps `provider.complete` on THIS harness's retriever instance (observation-only: records `req.model` + `response.content`
verbatim, returns the response untouched) and `_translate_to_medical_english` (to see whether the silent fallback fired),
then calls `_rewrite_query` 3 times (K=1 each; the k=3 union is NOT called). Verdict per call: model ECHOES the input /
returns < 3 strings / silent fallback fired.
"""
import asyncio
import json
from pathlib import Path

from _harness import assert_dev_db, production_retriever

import sys  # noqa: E402
HERE = Path(__file__).resolve().parent
# optional: python step10_0a.py "<query>" <out-suffix>   (default = the bare pair)
QUERY = sys.argv[1] if len(sys.argv) > 1 else "calcium and lisinopril"
OUT = HERE / f"step10_0a_raw_rewrite{('_' + sys.argv[2]) if len(sys.argv) > 2 else ''}.json"


async def main():
    dev = assert_dev_db()
    r, cfg = production_retriever()
    raws, fallbacks = [], []
    orig_complete = r._provider.complete
    orig_tr = r._translate_to_medical_english

    async def cap(req):
        resp = await orig_complete(req)
        raws.append({"model": req.model, "response_format": getattr(req, "response_format", None),
                     "content": resp.content})
        return resp

    async def tr(q):
        fallbacks.append(q)
        return await orig_tr(q)

    r._provider.complete = cap
    r._translate_to_medical_english = tr
    calls = []
    for i in range(3):
        n_raw, n_fb = len(raws), len(fallbacks)
        out = await r._rewrite_query(QUERY)
        raw = raws[n_raw]["content"] if len(raws) > n_raw else None
        fb = len(fallbacks) > n_fb
        verdict = ("SILENT FALLBACK fired (zero parsed strings)" if fb else
                   "ECHOES the input as a 1-element array" if out == [QUERY] else
                   f"returns {len(out)} string(s)" + (" (< 3)" if len(out) < 3 else ""))
        calls.append({"call": i + 1, "raw_content": raw, "parsed": out, "fallback_fired": fb, "verdict": verdict})
        print(f"[call {i+1}] raw={raw!r}\n          parsed={out} fallback={fb} -> {verdict}", flush=True)
    res = {"query": QUERY, "db_branch": dev, "model": r._model, "calls": calls,
           "n_provider_calls": len(raws), "n_fallbacks": len(fallbacks)}
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    asyncio.run(main())
