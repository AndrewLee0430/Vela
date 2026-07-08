# -*- coding: utf-8 -*-
"""Build the DailyMed US-label corpus (Research 5th-source, Stage A — OFFLINE artifact).

Market-overlap scope (founder decision): US labels for the same active moieties Vela
already grounds in TW via the v193 TFDA indication corpus. Deterministic backbone = the
MONO-ingredient moieties of that corpus; each resolves to ONE US reference label.

Mirrors scripts/build_tfda_indication_corpus.py + TFDACorpusStore (vector_store.py:147):
  - identical embedder (text-embedding-3-small, S0a parity gate) + float16 .npy storage
  - ingest-and-cite (ADR 004/007): store the label's own text; NO DDI-verdict logic.

REFERENCE-LABEL SELECTION (solves the live [P2] repackager debt at BUILD time — the whole
point of the vector route): DailyMed /v2/spls.json?drug_name= returns hundreds of dupes
(atorvastatin → 402, top hit a repackager). We narrow SERVER-SIDE by marketing_category_code
(NDA C73594 > NDA-authorized-generic C73607 > ANDA C73584 > any), then pick the mono product
whose title matches the moiety, tie-break max spl_version. So each corpus doc cites the
originator/reference SPL, not a repackager.

NOTHING here is wired into live retrieval (no SourceType.DAILYMED, no _search_dailymed) —
this is a standalone artifact for founder review before the Stage-B 🔴 wiring.

Usage:
    python scripts/build_dailymed_label_corpus.py            # STEP 1: resolve+fetch+parse -> label_docs.json (network)
    python scripts/build_dailymed_label_corpus.py --embed    # STEP 2: + embed -> label_emb.npy (needs OPENAI_API_KEY)
    python scripts/build_dailymed_label_corpus.py --limit N  # bounded slice for a quick dry-run
"""
import argparse
import asyncio
import io
import json
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402
from api.data_sources.dailymed import DailyMedClient  # noqa: E402 (reuse v201 _parse_spl / _fetch_spl_xml)

EMBEDDING_MODEL = "text-embedding-3-small"   # HARD PARITY with local/TFDA (build_tfda…:54, factory.py:32) — dim 1536
V2 = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
# marketing_category_code tiers, reference-preferred first.
TIERS = [("C73594", "NDA"), ("C73607", "NDA_authorized_generic"), ("C73584", "ANDA"), (None, "other")]

TFDA_CORPUS = ROOT / "data/tfda/indication_corpus.json"
OUT_DIR = ROOT / "data/dailymed"
DOCS_PATH = OUT_DIR / "label_docs.json"
EMB_PATH = OUT_DIR / "label_emb.npy"
CONCURRENCY = 8


def mono_moieties() -> list[str]:
    """Deterministic backbone: distinct MONO-ingredient moieties of the TFDA corpus
    (single-ingredient TFDA drugs — the clean US-mono-label overlap)."""
    d = json.loads(TFDA_CORPUS.read_text(encoding="utf-8"))
    mono = {doc["drug_name"].strip() for doc in d["documents"]
            if " + " not in doc.get("drug_name", "") and doc.get("drug_name", "").strip()}
    return sorted(mono)


async def _resolve_candidates(http, moiety, code):
    params = {"drug_name": moiety, "pagesize": "50"}
    if code:
        params["marketing_category_code"] = code
    for attempt in range(2):
        try:
            r = await http.get(f"{V2}/spls.json", params=params)
            if r.status_code == 404:
                return []
            r.raise_for_status()
            rows = r.json().get("data", [])
            return [(x["setid"], x.get("title", ""), int(x.get("spl_version") or 0))
                    for x in rows if x.get("setid")]
        except Exception:
            if attempt == 0:
                await asyncio.sleep(0.5)
    return []


def _pick_reference(cands, moiety):
    """Prefer a title containing the moiety head-word, mono over combo (fewest ' and '),
    then the newest spl_version."""
    head = (moiety.split()[0].lower() if moiety.split() else moiety.lower())
    def score(c):
        _sid, title, ver = c
        t = title.lower()
        return (1 if head in t else 0, -t.count(" and "), ver)
    return max(cands, key=score)


async def _resolve_moiety(sem, http, dm, moiety, snapshot_meta):
    async with sem:
        for code, tier in TIERS:
            cands = await _resolve_candidates(http, moiety, code)
            if not cands:
                continue
            setid, title, ver = _pick_reference(cands, moiety)
            xml = await dm._fetch_spl_xml(setid)
            if xml is None:
                continue
            label = dm._parse_spl(xml, setid, fallback_name=moiety)
            if label is None:
                continue
            content = label.to_text()
            # truncation incidence on clinically-critical sections (report S2b/S3)
            def _trunc(s):
                return bool(s) and s.endswith("...")
            return {
                "content": content,
                "source_type": "dailymed",
                "source_id": label.source_id,             # DailyMed:{setid}
                "title": f"{label.brand_name} ({label.generic_name})",
                "url": label.url,                          # drugInfo.cfm?setid=
                "credibility": "official",
                "doc_type": "dailymed_label",
                "moiety": moiety,
                "marketing_category": tier,
                "setid": setid,
                "spl_version": ver,
                "rxcui": None,                             # OPEN: not cheaply per-setid; keyed on moiety (report)
                "_sections_present": [k for k in ("drug_interactions", "boxed_warning",
                                                  "contraindications", "warnings", "indications", "dosage")
                                      if getattr(label, k)],
                "_trunc": {k: _trunc(getattr(label, k)) for k in
                           ("boxed_warning", "contraindications", "warnings", "drug_interactions")},
            }
        return {"moiety": moiety, "marketing_category": None, "setid": None}   # miss (TW-only / OTC / no US label)


async def build_docs(limit=None):
    moieties = mono_moieties()
    if limit:
        moieties = moieties[:limit]
    dm = DailyMedClient()
    sem = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient(timeout=30.0) as http:
        # snapshot pin = DailyMed db_published_date at build time
        try:
            meta = (await http.get(f"{V2}/spls.json", params={"pagesize": "1"})).json().get("metadata", {})
            snapshot = meta.get("db_published_date", "unknown")
        except Exception:
            snapshot = "unknown"
        t0 = time.time()
        results = await asyncio.gather(*[_resolve_moiety(sem, http, dm, m, snapshot) for m in moieties])
        dt = time.time() - t0

    hits = [r for r in results if r.get("setid")]
    # dedup by setid (distinct moieties should map to distinct setids; collision → keep first, flag)
    seen, docs, dup = set(), [], 0
    for r in hits:
        if r["setid"] in seen:
            dup += 1
            continue
        seen.add(r["setid"])
        docs.append(r)
    docs.sort(key=lambda d: d["moiety"])

    tier_breakdown = {}
    for d in docs:
        tier_breakdown[d["marketing_category"]] = tier_breakdown.get(d["marketing_category"], 0) + 1
    trunc_counts = {s: sum(1 for d in docs if d["_trunc"].get(s)) for s in
                    ("boxed_warning", "contraindications", "warnings", "drug_interactions")}
    stats = {
        "backbone_mono_moieties": len(moieties),
        "resolved_docs": len(docs),
        "misses_no_us_label": len(moieties) - len(hits),
        "dup_setid_collisions": dup,
        "tier_breakdown": tier_breakdown,
        "trunc_incidence_on_critical_sections": trunc_counts,
        "snapshot_db_published_date": snapshot,
        "resolve_seconds": round(dt, 1),
    }
    return docs, stats


def embed_documents(docs, batch_size=100):
    from openai import OpenAI
    client = OpenAI()
    texts = [d["content"] for d in docs]
    out = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"   embedding batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1} ({len(batch)})...")
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        out.extend([item.embedding for item in resp.data])
    return out


def main():
    ap = argparse.ArgumentParser(description="Build DailyMed US-label corpus (Stage A, offline)")
    ap.add_argument("--embed", action="store_true", help="also embed -> label_emb.npy (needs OPENAI_API_KEY)")
    ap.add_argument("--limit", type=int, default=None, help="bounded slice for a dry-run")
    args = ap.parse_args()

    if args.embed and DOCS_PATH.exists() and not args.limit:
        payload = json.loads(DOCS_PATH.read_text(encoding="utf-8"))
        docs = payload["documents"]
    else:
        docs, stats = asyncio.run(build_docs(limit=args.limit))
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        DOCS_PATH.write_text(json.dumps(
            {"_meta": {"source": "DailyMed v2 SPL (US labels), market-overlap = TFDA mono moieties",
                       "scope": "mono-ingredient TFDA moieties -> NDA-preferred US reference label",
                       "embedding_model": EMBEDDING_MODEL,
                       "reference_selection": "marketing_category_code NDA>NDA_AG>ANDA>other, mono title, max spl_version",
                       "monthly_re_pull": "re-run STEP 1; snapshot pinned by db_published_date below",
                       "stats": stats},
             "documents": docs}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("=== DAILYMED LABEL CORPUS STATS ===")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        print(f"  docs: {DOCS_PATH} ({DOCS_PATH.stat().st_size:,} bytes)")

    if args.embed:
        from dotenv import load_dotenv
        import numpy as np
        load_dotenv()
        print(f"🔨 Embedding {len(docs)} docs with {EMBEDDING_MODEL}...")
        arr = np.asarray(embed_documents(docs), dtype=np.float16)   # float16 (mirror TFDA vector_store.py:175)
        np.save(EMB_PATH, arr)
        print(f"💾 embeddings: {EMB_PATH} ({EMB_PATH.stat().st_size / (1024*1024):.1f} MB, shape={arr.shape}, dtype=float16)")


if __name__ == "__main__":
    main()
