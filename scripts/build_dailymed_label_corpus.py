# -*- coding: utf-8 -*-
"""Build the DailyMed US-label corpus (Research 5th-source — OFFLINE artifact).

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

── B-1 PER-SECTION REBUILD ──────────────────────────────────────────────────────────
Each clinically-relevant LOINC section becomes its OWN doc + OWN embedding (was: ONE
whole-label to_text() doc per label). Section text is taken FULL and UN-TRUNCATED via
dm._collect_prose(sec) + dm._flatten_tables(sec) called DIRECTLY — never _section_text /
to_text — so nothing Verify reads is touched, and the label's own interaction TABLE is
kept in full. Indications is now included (A2-typo fix, _LOINC_INDICATIONS="34067-9",
fly 205; the Stage-A whole-label artifact had 0 indications from the "34067-0" typo).

DETERMINISM (`--reuse-setids`, DEFAULT): reuses the PINNED reference selection from the
Stage-A snapshot (data/dailymed/label_docs.json — the (moiety, setid, marketing_category,
spl_version) tuples already produced by _resolve_moiety/_pick_reference), re-fetches each
reference SPL, and re-parses per-section. SAME setids → SAME per-section docs. The full
network re-resolve (monthly re-pull) is preserved behind `--resolve`; the selection logic
(_resolve_moiety / _pick_reference / TIERS) is UNCHANGED — only the post-parse doc
construction changed (whole-label → per-section) + the dedup key (setid → (setid, loinc)).

NOTHING here is wired into live retrieval (no SourceType.DAILYMED, no _search_dailymed) —
this is a standalone DORMANT artifact for founder review before the Stage-B 🔴 wiring.

Usage:
    python scripts/build_dailymed_label_corpus.py                 # STEP 1: reuse pinned setids, re-fetch+per-section -> label_docs.json (network)
    python scripts/build_dailymed_label_corpus.py --resolve       # STEP 1 (full re-pull): re-resolve moieties from scratch (~25 min network)
    python scripts/build_dailymed_label_corpus.py --embed         # STEP 2: + embed -> label_emb.npy (needs OPENAI_API_KEY)
    python scripts/build_dailymed_label_corpus.py --limit N       # bounded slice for a quick dry-run
"""
import argparse
import asyncio
import io
import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402
from api.data_sources.dailymed import (  # noqa: E402 (reuse v201 parse/fetch/prose/table extractors)
    DailyMedClient,
    _NS,
    _LOINC_DRUG_INTERACTIONS,
    _LOINC_BOXED_WARNING,
    _LOINC_CONTRAINDICATIONS,
    _LOINC_WARNINGS_PRECAUTIONS,
    _LOINC_INDICATIONS,
    _LOINC_DOSAGE,
)

EMBEDDING_MODEL = "text-embedding-3-small"   # HARD PARITY with local/TFDA (build_tfda…:54, factory.py:32) — dim 1536
V2 = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
# marketing_category_code tiers, reference-preferred first.
TIERS = [("C73594", "NDA"), ("C73607", "NDA_authorized_generic"), ("C73584", "ANDA"), (None, "other")]

# The 6 clinically-relevant LOINC sections → (short slug, loinc, display name). One doc per
# NON-EMPTY section. Interactions first (the Verify grounding target); order is cosmetic here.
SECTIONS = [
    ("interactions",       _LOINC_DRUG_INTERACTIONS,     "Drug Interactions"),
    ("boxed",              _LOINC_BOXED_WARNING,         "Boxed Warning"),
    ("contraindications",  _LOINC_CONTRAINDICATIONS,     "Contraindications"),
    ("warnings",           _LOINC_WARNINGS_PRECAUTIONS,  "Warnings and Precautions"),
    ("indications",        _LOINC_INDICATIONS,           "Indications and Usage"),
    ("dosage",             _LOINC_DOSAGE,                "Dosage and Administration"),
]

# One embedding per whole section (mirror TFDA's single-unit indication docs). Guard: a
# pathologically long section sub-chunks with ~10% overlap. Warfarin's longest (dosage ~11k)
# is well under this — the guard is a safety net, not the common path.
MAX_SECTION_CHARS = 24000     # ~6k tokens
CHUNK_OVERLAP = 0.10

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


def _chunks(text: str) -> list[str]:
    """Single-unit unless the section exceeds MAX_SECTION_CHARS; then sub-chunk with ~10%
    overlap (guard for a pathologically long section; rarely triggered)."""
    if len(text) <= MAX_SECTION_CHARS:
        return [text]
    step = max(1, int(MAX_SECTION_CHARS * (1 - CHUNK_OVERLAP)))
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i + MAX_SECTION_CHARS])
        i += step
    return out


def _find_section(root, loinc):
    """The tiny section-find loop from dm._section_text (first match), WITHOUT the cap."""
    for sec in root.iter(f"{_NS}section"):
        code = sec.find(f"{_NS}code")
        if code is not None and code.get("code") == loinc:
            return sec
    return None


def _section_docs_from_spl(dm, xml: bytes, moiety, marketing_category, setid, spl_version) -> list[dict]:
    """Parse a reference SPL → one doc per NON-EMPTY clinically-relevant LOINC section.
    Uses dm._collect_prose + dm._flatten_tables DIRECTLY (full uncapped text)."""
    try:
        root = ET.fromstring(xml)
    except Exception:
        return []
    brand, generic, _mfr = dm._parse_names(root, moiety)
    url = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={setid}"
    docs: list[dict] = []
    for slug, loinc, display in SECTIONS:
        sec = _find_section(root, loinc)
        if sec is None:
            continue
        prose = dm._collect_prose(sec)          # FULL, uncapped
        tables = dm._flatten_tables(sec)        # FULL flattened table (the grounding payload)
        combined = "\n".join(p for p in (prose, tables) if p).strip()
        if not combined:                        # genuinely empty section → no doc
            continue
        parts = _chunks(combined)
        multi = len(parts) > 1
        for idx, chunk in enumerate(parts):
            sid = f"DailyMed:{setid}#{loinc}" + (f"~{idx}" if multi else "")
            docs.append({
                "content": chunk,
                "source_type": "dailymed",
                "source_id": sid,                       # unique per (setid, loinc[, chunk])
                "title": f"{brand} ({generic}) — {display}",
                "url": url,                             # setid deep-link, same for all sections of a label
                "credibility": "official",
                "doc_type": "dailymed_label_section",
                "moiety": moiety,
                "marketing_category": marketing_category,
                "setid": setid,
                "spl_version": spl_version,
                "rxcui": None,                          # OPEN: not cheaply per-setid; keyed on moiety
                "loinc": loinc,                         # B-2: name which section a hit came from
                "section_type": slug,
                **({"chunk": idx, "chunk_total": len(parts)} if multi else {}),
            })
    return docs


async def _resolve_moiety(sem, http, dm, moiety, snapshot_meta):
    """FULL re-resolve path (--resolve). Selection (TIERS/_pick_reference) UNCHANGED; only
    the post-parse construction is now per-section via _section_docs_from_spl."""
    async with sem:
        for code, tier in TIERS:
            cands = await _resolve_candidates(http, moiety, code)
            if not cands:
                continue
            setid, title, ver = _pick_reference(cands, moiety)
            xml = await dm._fetch_spl_xml(setid)
            if xml is None:
                continue
            docs = _section_docs_from_spl(dm, xml, moiety, tier, setid, ver)
            return {"moiety": moiety, "marketing_category": tier, "setid": setid,
                    "spl_version": ver, "docs": docs}
        return {"moiety": moiety, "marketing_category": None, "setid": None, "docs": []}   # miss


def _load_pinned_refs():
    """Reuse the Stage-A reference selection: the distinct (setid, moiety, marketing_category,
    spl_version) tuples already resolved into data/dailymed/label_docs.json. This is the OUTPUT
    of _resolve_moiety/_pick_reference — so selection/scope is held fixed; only doc construction
    changes. Returns (refs, prior_snapshot)."""
    payload = json.loads(DOCS_PATH.read_text(encoding="utf-8"))
    prior_snapshot = payload.get("_meta", {}).get("stats", {}).get("snapshot_db_published_date", "unknown")
    seen, refs = set(), []
    for d in payload["documents"]:
        sid = d.get("setid")
        if not sid or sid in seen:
            continue
        seen.add(sid)
        refs.append({
            "setid": sid,
            "moiety": d.get("moiety"),
            "marketing_category": d.get("marketing_category"),
            "spl_version": d.get("spl_version"),
        })
    return refs, prior_snapshot


async def _fetch_and_build(sem, http, dm, ref) -> list[dict]:
    async with sem:
        xml = await dm._fetch_spl_xml(ref["setid"])
        if xml is None:
            return []
        return _section_docs_from_spl(dm, xml, ref["moiety"], ref["marketing_category"],
                                      ref["setid"], ref["spl_version"])


async def build_docs(limit=None, resolve=False):
    dm = DailyMedClient()
    sem = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient(timeout=30.0) as http:
        # current DailyMed db_published_date (transparency; content is setid-immutable)
        try:
            meta = (await http.get(f"{V2}/spls.json", params={"pagesize": "1"})).json().get("metadata", {})
            snapshot = meta.get("db_published_date", "unknown")
        except Exception:
            snapshot = "unknown"

        t0 = time.time()
        if resolve:
            moieties = mono_moieties()
            if limit:
                moieties = moieties[:limit]
            backbone = len(moieties)
            results = await asyncio.gather(*[_resolve_moiety(sem, http, dm, m, snapshot) for m in moieties])
            labels = [r for r in results if r.get("setid")]
            misses = backbone - len(labels)
            prior_snapshot = None
            built_from = "full re-resolve (mono_moieties → NDA-preferred reference label)"
            per_label_docs = [r["docs"] for r in labels]
            tier_source = {(r["setid"]): r["marketing_category"] for r in labels}
        else:
            refs, prior_snapshot = _load_pinned_refs()
            if limit:
                refs = refs[:limit]
            backbone = len(refs)
            per_label = await asyncio.gather(*[_fetch_and_build(sem, http, dm, r) for r in refs])
            # a label contributes ≥1 section-doc unless the SPL fetch failed / had 0 sections
            labels = [r for r, ds in zip(refs, per_label) if ds]
            misses = backbone - len(labels)
            per_label_docs = [ds for ds in per_label if ds]
            built_from = "reuse pinned Stage-A reference setids (selection held fixed; re-fetch + per-section)"
            tier_source = {r["setid"]: r["marketing_category"] for r in refs}
        dt = time.time() - t0

    # flatten per-section docs; dedup by (setid, loinc[, chunk]) = source_id
    seen, docs, dup = set(), [], 0
    for ds in per_label_docs:
        for d in ds:
            if d["source_id"] in seen:
                dup += 1
                continue
            seen.add(d["source_id"])
            docs.append(d)
    docs.sort(key=lambda d: (d["moiety"] or "", d["setid"], d["section_type"], d.get("chunk", 0)))

    # ── stats ────────────────────────────────────────────────────────────────────────
    n_labels = len(per_label_docs)
    section_type_breakdown = {}
    for d in docs:
        section_type_breakdown[d["section_type"]] = section_type_breakdown.get(d["section_type"], 0) + 1
    tier_breakdown = {}
    for sid in {d["setid"] for d in docs}:
        t = tier_source.get(sid)
        tier_breakdown[t] = tier_breakdown.get(t, 0) + 1
    sub_chunked = sum(1 for d in docs if "chunk" in d)
    longest = max((len(d["content"]) for d in docs), default=0)
    stats = {
        "build_mode": "resolve" if resolve else "reuse_pinned_setids",
        "built_from": built_from,
        "backbone_reference_labels": backbone,
        "labels_with_sections": n_labels,
        "labels_dropped_zero_sections_or_fetch_fail": misses,
        "total_section_docs": len(docs),
        "avg_sections_per_label": round(len(docs) / n_labels, 2) if n_labels else 0,
        "section_type_breakdown": section_type_breakdown,
        "tier_breakdown": tier_breakdown,
        "source_id_collisions": dup,
        "sub_chunked_docs": sub_chunked,
        "longest_section_chars": longest,
        "snapshot_db_published_date": snapshot,
        "prior_stage_a_snapshot": prior_snapshot,
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
    ap = argparse.ArgumentParser(description="Build DailyMed US-label corpus (per-section, offline)")
    ap.add_argument("--embed", action="store_true", help="also embed -> label_emb.npy (needs OPENAI_API_KEY)")
    ap.add_argument("--resolve", action="store_true",
                    help="full network re-resolve of moieties (monthly re-pull); default reuses pinned Stage-A setids")
    ap.add_argument("--limit", type=int, default=None, help="bounded slice for a dry-run")
    args = ap.parse_args()

    if args.embed and DOCS_PATH.exists() and not args.limit and not args.resolve and _docs_are_per_section():
        payload = json.loads(DOCS_PATH.read_text(encoding="utf-8"))
        docs = payload["documents"]
    else:
        docs, stats = asyncio.run(build_docs(limit=args.limit, resolve=args.resolve))
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        DOCS_PATH.write_text(json.dumps(
            {"_meta": {"source": "DailyMed v2 SPL (US labels), market-overlap = TFDA mono moieties",
                       "granularity": "PER-SECTION (one doc per non-empty clinically-relevant LOINC section)",
                       "scope": "mono-ingredient TFDA moieties -> NDA-preferred US reference label",
                       "embedding_model": EMBEDDING_MODEL,
                       "reference_selection": "marketing_category_code NDA>NDA_AG>ANDA>other, mono title, max spl_version",
                       "sections": [f"{slug} ({loinc})" for slug, loinc, _ in SECTIONS],
                       "full_text": "dm._collect_prose + dm._flatten_tables (uncapped); NOT _section_text/to_text",
                       "monthly_re_pull": "re-run with --resolve; snapshot pinned by db_published_date below",
                       "stats": stats},
             "documents": docs}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("=== DAILYMED PER-SECTION CORPUS STATS ===")
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


def _docs_are_per_section() -> bool:
    """Guard the --embed reuse-docs shortcut: only reuse an on-disk docs file if it is already
    the per-section shape (avoids embedding a stale whole-label artifact)."""
    try:
        payload = json.loads(DOCS_PATH.read_text(encoding="utf-8"))
        return payload.get("_meta", {}).get("granularity", "").startswith("PER-SECTION")
    except Exception:
        return False


if __name__ == "__main__":
    main()
