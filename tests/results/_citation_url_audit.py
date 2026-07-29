# -*- coding: utf-8 -*-
"""Task 1b(3) + 1c — force an openFDA citation end-to-end, then RESOLVE-test one URL per source type.

1b(3): Research fans out to openFDA every query but Phase 1 measured it CITED 0/18, so its URL
       construction has never been exercised in a rendered citation. Force it with a source_filter
       so the value is OBSERVED, not inferred.
1c:    populated != resolves. Fetch one representative URL per source type; report HTTP status and
       the final URL after redirects. Distinguish a broken link from a bot-block (TECH_DEBT
       precedent: moh.gov.my is tool-unconfirmed / browser-confirmed behind a WAF).

READ-ONLY.
"""
import asyncio, io, json, os, sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(r"C:\Users\andre\projects\Vela")
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TEST_MODE", "true")
from dotenv import load_dotenv                    # noqa: E402
load_dotenv(ROOT / ".env", override=True)
import httpx                                      # noqa: E402
from api.rag.retriever import HybridRetriever     # noqa: E402
from api.models.schemas import SourceType         # noqa: E402

OUT = ROOT / "tests" / "results" / "citation_url_audit.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"}


async def force_openfda():
    """Retrieve with source_filter=[FDA] so openFDA docs must reach the returned set."""
    r = HybridRetriever()
    docs, status = await r.retrieve(query="metformin side effects and warnings",
                                    max_results=5, source_filter=[SourceType.FDA])
    out = []
    for d in docs:
        out.append({"source_type": str(getattr(d.source_type, "value", d.source_type)),
                    "source_id": d.source_id, "url": d.url,
                    "citation_url": d.to_citation(1).url})
    return status, out


def resolve(url, label):
    if not url:
        return {"label": label, "url": url, "status": None, "final": None,
                "verdict": "NO URL — nothing to resolve"}
    try:
        with httpx.Client(follow_redirects=True, timeout=30.0, headers=UA) as c:
            resp = c.get(url)
        final = str(resp.url)
        same = final.rstrip("/") == url.rstrip("/")
        verdict = ("OK" if resp.status_code == 200 and same else
                   f"REDIRECTED to {final}" if resp.status_code == 200 else
                   f"HTTP {resp.status_code}")
        if resp.status_code in (403, 429):
            verdict = f"HTTP {resp.status_code} — possible bot-block, needs browser confirm"
        return {"label": label, "url": url, "status": resp.status_code,
                "final": final, "verdict": verdict}
    except Exception as e:
        return {"label": label, "url": url, "status": None, "final": None,
                "verdict": f"FETCH ERROR {type(e).__name__}: {e}"}


def main():
    rep = {}
    print("=== TASK 1b(3): forced openFDA citation, observed end-to-end ===")
    status, docs = asyncio.run(force_openfda())
    rep["openfda_forced"] = {"status": status, "docs": docs}
    if not docs:
        print("  !! could not surface an openFDA doc — reporting as UNOBSERVED, not inferred")
    for d in docs:
        print(f"  source_type={d['source_type']:9} source_id={d['source_id'][:34]:34}")
        print(f"        url          = {d['url']!r}")
        print(f"        citation.url = {d['citation_url']!r}")

    print("\n=== TASK 1c: resolve one representative URL per source type ===")
    corpus_dm = json.load(open(ROOT / "data/dailymed/label_docs.json", encoding="utf-8"))["documents"]
    corpus_tf = json.load(open(ROOT / "data/tfda/indication_corpus.json", encoding="utf-8"))["documents"]
    samples = [
        ("pubmed",        "https://pubmed.ncbi.nlm.nih.gov/12667121/"),
        ("dailymed",      next(d["url"] for d in corpus_dm if d.get("url"))),
        ("tfda",          next(d["url"] for d in corpus_tf if d.get("url"))),
        ("openFDA (live)", docs[0]["url"] if docs else "https://labels.fda.gov/"),
        ("local (corpus)", ""),   # 690/690 empty — branch (3), stays empty by design
    ]
    rows = [resolve(u, lab) for lab, u in samples]
    rep["resolve"] = rows
    print(f"\n{'source':16} {'HTTP':>6}  verdict")
    print("-" * 96)
    for r in rows:
        print(f"{r['label']:16} {str(r['status'] or '—'):>6}  {r['verdict'][:70]}")
        if r["url"]:
            print(f"{'':16}        url:   {r['url'][:78]}")
        if r["final"] and r["final"].rstrip('/') != (r["url"] or '').rstrip('/'):
            print(f"{'':16}        final: {r['final'][:78]}")

    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
