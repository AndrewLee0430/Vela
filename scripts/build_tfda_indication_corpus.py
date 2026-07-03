# -*- coding: utf-8 -*-
"""
Build the TFDA 官方核准適應症 (Taiwan-approved-indication) grounding-lite corpus from the
pinned id=37 snapshot — a SEPARATE, bounded, CITABLE retrieved corpus for Research
(ADR 007 candidate a1, the 適應症 half). INDICATION ONLY this pass (用法用量 dropped — it's
only 48% covered; dosing is a later follow-up).

Per ADR 007 ingest-and-cite: each doc CITES what the TFDA label SAYS (the approved indication),
with the 許可證字號 as the citation anchor. NO LLM-generated local rules, no individualized
advice, no safety content (this dataset has none — see the ⚠ framing line in each doc).

Shares the SAME snapshot read + active/未註銷/non-expired/製劑 filter + normalization as the T2a
brand→ingredient build (both import api/services/tfda_lookup.py) → ONE parse, no drift.

KEYING (founder decision ①): one doc per (ingredient-set × distinct 適應症 text). Products that
share BOTH the ingredient set AND the indication text collapse into one doc (cite a representative
許可證 + "N 項同成分同適應症許可證"); genuinely-distinct indications stay separate docs.

Usage:
    python scripts/build_tfda_indication_corpus.py            # STEP 1: parse → indication_corpus.json (deterministic, no network)
    python scripts/build_tfda_indication_corpus.py --embed    # STEP 2: + embed → indication_index.json
Output:
    data/tfda/indication_corpus.json   (docs only — deterministic, reviewable)
    data/tfda/indication_index.json    (docs + embeddings — loaded by the TFDA retrieval source)
"""
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api.services.tfda_lookup import (  # noqa: E402  (shared read/filter/normalization — single source of truth)
    norm_ws, ambiguity_key, parse_ingredients, norm_indication,
    load_snapshot_records, snapshot_ref_date, filter_active_preparations,
)

SNAPSHOT_ZIP = Path("data/tfda/snapshot_20260630/drug_license_id37.zip")
CORPUS_PATH = Path("data/tfda/indication_corpus.json")   # docs (content + metadata), row-aligned with the .npy
EMB_PATH = Path("data/tfda/indication_emb.npy")          # float16 embeddings — compact (a JSON-float index would exceed GitHub's 100MB limit)
TFDA_PORTAL_URL = "https://mcp.fda.gov.tw/"   # portal base — fallback when a doc has no 許可證字號
# a1-iii (2026-07-01 recon, scheme live-verified): per-字號 deep-link to that drug's 仿單資料
# page. Some licenses have no structured label yet → the page may 404; the user clicking a
# citation link in-browser is a normal outbound link (same risk class as the portal base).
TFDA_DETAIL_URL = "https://mcp.fda.gov.tw/im_detail_pdf/{lic}"


def _citation_url(rep_lic: str) -> str:
    """Deep-link per 許可證字號 (URL-encoded); portal base when the 字號 is missing —
    never emit a broken path."""
    if rep_lic:
        return TFDA_DETAIL_URL.format(lic=quote(rep_lic, safe=""))
    return TFDA_PORTAL_URL
EMBEDDING_MODEL = "text-embedding-3-small"    # same model as the local drug vector store


def build_docs():
    recs = load_snapshot_records(SNAPSHOT_ZIP)
    ref_date = snapshot_ref_date(SNAPSHOT_ZIP)
    kept, fstats = filter_active_preparations(recs, ref_date)

    # group key = (ingredient-set canonical, normalized 適應症 text)
    groups = {}   # key -> {ingr_repr, indication, products: {zh: {en, form}}, licenses: set}
    dropped_no_indication = dropped_no_ingredient = 0
    for r in kept:
        zh = norm_ws(r.get("中文品名", ""))
        if not zh:
            continue
        _, clean_list = parse_ingredients(r.get("主成分略述", ""))
        if not clean_list:
            dropped_no_ingredient += 1; continue
        indication = norm_indication(r.get("適應症", ""))
        if not indication:
            dropped_no_indication += 1; continue

        ingr_ckey = frozenset(ambiguity_key(c) for c in clean_list)   # SULPH/SULF-collapsed key (same as T2a)
        key = (ingr_ckey, indication)
        g = groups.get(key)
        if g is None:
            g = {"ingr_repr": sorted(clean_list), "indication": indication,
                 "products": {}, "licenses": set()}
            groups[key] = g
        en = norm_ws(r.get("英文品名", ""))
        form = norm_ws(r.get("劑型", ""))
        g["products"].setdefault(zh, {"en": en, "form": form})
        lic = norm_ws(r.get("許可證字號", ""))
        if lic:
            g["licenses"].add(lic)

    docs = []
    for g in groups.values():
        # representative product = shortest 中文品名 then alphabetical (the base brand, deterministic)
        rep_zh = min(g["products"], key=lambda z: (len(z), z))
        rep = g["products"][rep_zh]
        ingr = " + ".join(g["ingr_repr"])
        n = len(g["licenses"])
        extra = f"（+ {n - 1} 項同成分同適應症許可證）" if n > 1 else ""
        rep_lic = sorted(g["licenses"])[0] if g["licenses"] else ""
        en_disp = f" ({rep['en']})" if rep["en"] else ""
        content = (
            "[TFDA 核准適應症 — Taiwan-approved indication]\n"
            f"主成分 {ingr} | 代表品名 {rep_zh}{en_disp} | 劑型 {rep['form']}\n"
            f"許可證字號 {rep_lic}{extra}\n"
            f"適應症（TFDA-approved indication）: {g['indication']}\n"
            "⚠ 本節僅含 TFDA 核准之「適應症」，不含禁忌症／警語／交互作用／不良反應／用法用量"
            "（these require the full 仿單, id=39 / a2 — NOT in this dataset）。"
        )
        docs.append({
            "content": content,
            "source_type": "tfda",
            "source_id": rep_lic,
            "title": rep_zh,
            "url": _citation_url(rep_lic),   # a1-iii deep-link (portal base if no 字號)
            "credibility": "official",
            "doc_type": "tfda_indication",
            "drug_name": ingr,
            "licenses": sorted(g["licenses"]),
            "product_count": len(g["products"]),
        })

    docs.sort(key=lambda d: (d["drug_name"], d["title"]))   # deterministic order
    stats = {
        **fstats,
        "dropped_no_ingredient": dropped_no_ingredient,
        "dropped_no_indication": dropped_no_indication,
        "distinct_indication_docs": len(docs),
    }
    return docs, stats, ref_date


def embed_documents(docs, batch_size=100):
    from openai import OpenAI
    client = OpenAI()
    texts = [d["content"] for d in docs]
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"   embedding batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1} ({len(batch)})...")
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        embeddings.extend([item.embedding for item in resp.data])
    return embeddings


def main():
    ap = argparse.ArgumentParser(description="Build TFDA indication grounding-lite corpus")
    ap.add_argument("--embed", action="store_true", help="also embed → indication_index.json (needs OPENAI_API_KEY)")
    args = ap.parse_args()

    docs, stats, ref_date = build_docs()
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CORPUS_PATH.write_text(json.dumps({"_meta": {"source": "TFDA id=37 未註銷藥品許可證資料集 適應症",
                                                 "snapshot": str(SNAPSHOT_ZIP), "built_at": ref_date,
                                                 "scope": "適應症 ONLY (用法用量 dropped, 48% coverage)",
                                                 "keying": "per (ingredient-set × distinct 適應症 text)",
                                                 "stats": stats},
                                       "documents": docs}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("=== INDICATION CORPUS STATS ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"  corpus: {CORPUS_PATH} ({CORPUS_PATH.stat().st_size:,} bytes)")

    if args.embed:
        from dotenv import load_dotenv
        import numpy as np
        load_dotenv()
        print(f"🔨 Embedding {len(docs)} docs with {EMBEDDING_MODEL}...")
        embeddings = embed_documents(docs)
        # float16 keeps the .npy compact (~33MB vs ~200MB JSON); cosine ranking is insensitive
        # to the precision drop (we cast to float32 at search time). Row order == CORPUS_PATH docs.
        arr = np.asarray(embeddings, dtype=np.float16)
        np.save(EMB_PATH, arr)
        print(f"💾 embeddings: {EMB_PATH} ({EMB_PATH.stat().st_size / (1024*1024):.1f} MB, shape={arr.shape}, dtype=float16)")


if __name__ == "__main__":
    main()
