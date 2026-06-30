# -*- coding: utf-8 -*-
"""
Build a DETERMINISTIC 中文品名/英文品名 → 主成分 (active-ingredient) lookup table
from the pinned TFDA id=37 (未註銷藥品許可證資料集) snapshot.

Per ADR 007 + ADR 003 + TECH_DEBT: brand→ingredient is a FACTUAL-LOOKUP problem, solved by
a deterministic table — NOT by model-swap or prompt-tuning. This script is pure data
transformation; no model, no network at build time (reads the pinned snapshot).

Fixes the open 冠脂妥→wrong-drug residual: the LLM was confident-wrong (said simvastatin);
the TFDA license data says ROSUVASTATIN CALCIUM.

The NORMALIZATION (norm_ws / canonical / brand_stem / parse_ingredients …) is IMPORTED from
api/services/tfda_lookup.py — the SINGLE SOURCE OF TRUTH shared with the runtime resolver,
so the table's keys and the runtime's query keys can never drift.

Edge cases handled (all flagged by the 2026-06-29 data probe):
  1. FILTER     — keep 製劑 + 未註銷(註銷狀態 empty) + 有效日期 >= today; drop 原料藥/菌疫/硬空膠囊 + expired.
  2. COMBO      — 主成分略述 is ";;"-delimited for multi-active products → split into a list.
  3. NAME NORM  — 中文品名 is a full product string ("冠脂妥膜衣錠10毫克"); derive a brand STEM
                  (strip quoted 廠商 prefix + 劑型 + 劑量) so a user typing "冠脂妥" resolves.
                  The full name is kept as the primary (exact) key, keyed QUOTE-INSENSITIVELY
                  via canonical() so 「"美"利風油」 resolves a query of 美利風油 (decision ②).
  4. DEDUP+AMBIG— collapse duplicate license rows; a stem (or full name) that maps to >1 DISTINCT
                  ingredient-set is recorded as AMBIGUOUS (no silent pick — defer, like the
                  no-fabrication principle).

Usage:  python scripts/build_tfda_brand_ingredient.py
Output: data/tfda/brand_ingredient.json
"""
import json
import re
import sys
import zipfile
import datetime
from pathlib import Path

# Repo root on sys.path so `from api.services...` imports when run as scripts/<file>.py
# (no PYTHONPATH needed — same pattern as scripts/deletion_dryrun.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api.services.tfda_lookup import (  # noqa: E402  (shared normalization — single source of truth)
    norm_ws, canonical, brand_stem, parse_ingredients, ambiguity_key,
)

SNAPSHOT_ZIP = Path("data/tfda/snapshot_20260630/drug_license_id37.zip")
OUT_PATH = Path("data/tfda/brand_ingredient.json")
TODAY = datetime.date.today().strftime("%Y/%m/%d")  # 有效日期 format is YYYY/MM/DD (lexicographic == chronological)


def main():
    z = zipfile.ZipFile(SNAPSHOT_ZIP)
    recs = json.loads(z.read(z.namelist()[0]).decode("utf-8"))
    stats = {"input_rows": len(recs)}

    # ---- STEP 1: filter ----
    def license_kind(r):
        return (r.get("許可證種類") or "").replace("　", "").strip()

    kept = []
    drop_kind = drop_cancelled = drop_expired = 0
    for r in recs:
        if license_kind(r) != "製劑":
            drop_kind += 1; continue
        if str(r.get("註銷狀態", "")).strip():
            drop_cancelled += 1; continue
        eff = str(r.get("有效日期", "")).strip()
        if not re.match(r"\d{4}/\d{2}/\d{2}", eff) or eff < TODAY:
            drop_expired += 1; continue
        kept.append(r)
    stats.update(dropped_non_製劑=drop_kind, dropped_cancelled=drop_cancelled,
                 dropped_expired_or_no_date=drop_expired, rows_after_filter=len(kept), today=TODAY)

    # ---- STEP 2-4: build maps ----
    # by_name is keyed on canonical(中文品名) — quote-insensitive (decision ②) so the runtime
    # query canonical("美利風油") resolves the record stored under 「"美"利風油」.
    by_name = {}   # canonical(中文品名) → record
    en_index = {}  # canonical(英文品名).upper() → set of canonical 中文品名 (alternate lookup)
    stem_map = {}  # canonical(stem) → {ingredient_sets: set(frozenset), products: set, licenses: set}
    combo_count = 0

    for r in kept:
        zh = norm_ws(r.get("中文品名", ""))
        en = norm_ws(r.get("英文品名", ""))
        if not zh:
            continue
        raw_list, clean_list = parse_ingredients(r.get("主成分略述", ""))
        if not clean_list:
            continue
        if len(clean_list) > 1:
            combo_count += 1
        lic = r.get("許可證字號", "")
        key = canonical(zh)
        stem = canonical(brand_stem(zh))
        # AMBIGUITY KEY is order-independent (a set) AND collapses ONLY the SULPH↔SULF
        # British/American spelling of the same word (ambiguity_key) — e.g.
        # 'CLOPIDOGREL HYDROGEN SULPHATE' == '...SULFATE'. Decision ① still holds for
        # everything else: QUETIAPINE vs QUETIAPINE FUMARATE etc. stay DISTINCT → ambiguous.
        # The DISPLAY repr (ingr_repr) keeps TFDA's original spelling; only the key is canonical.
        ingr_key = frozenset(ambiguity_key(c) for c in clean_list)
        ingr_repr = sorted(clean_list)

        rec = by_name.get(key)
        if rec is None:
            rec = {"display_name": zh, "english": en, "form": r.get("劑型", ""),
                   "stem": stem, "licenses": [lic] if lic else [],
                   "is_combo": len(clean_list) > 1, "ambiguous": False,
                   "ingredient_sets": [ingr_repr], "_keys": {ingr_key}}
            by_name[key] = rec
        else:
            if lic and lic not in rec["licenses"]:
                rec["licenses"].append(lic)
            if ingr_key not in rec["_keys"]:
                rec["_keys"].add(ingr_key)
                rec["ingredient_sets"].append(ingr_repr)
                rec["ambiguous"] = True   # same (canonical) name, set-distinct ingredients → ambiguous

        if en:
            en_index.setdefault(canonical(en).upper(), set()).add(key)

        sm = stem_map.setdefault(stem, {"key_repr": {}, "products": set(), "licenses": set()})
        sm["key_repr"].setdefault(ingr_key, ingr_repr)   # display = original spelling, first-wins per canonical key
        sm["products"].add(zh)
        if lic:
            sm["licenses"].add(lic)

    # finalize stem map (ambiguous = >1 distinct ingredient-KEY under one stem; the key
    # collapses SULPH/SULF spelling, so display reprs keep TFDA's original spelling)
    by_stem = {}
    ambiguous_stems = []
    for stem, sm in stem_map.items():
        sets = sorted(sm["key_repr"].values())   # one original-spelling repr per canonical key
        amb = len(sets) > 1
        by_stem[stem] = {"ambiguous": amb, "ingredient_sets": sets,
                         "products": sorted(sm["products"]),
                         "licenses": sorted(sm["licenses"])}
        if amb:
            ambiguous_stems.append(stem)

    stats.update(distinct_full_names=len(by_name), distinct_stems=len(by_stem),
                 combo_products=combo_count, ambiguous_stems=len(ambiguous_stems),
                 ambiguous_full_names=sum(1 for v in by_name.values() if v["ambiguous"]),
                 distinct_english_names=len(en_index))

    out = {
        "_meta": {
            "source": "TFDA id=37 未註銷藥品許可證資料集",
            "snapshot": str(SNAPSHOT_ZIP), "built_at": TODAY,
            "filters": "製劑 + 未註銷(註銷狀態 empty) + 有效日期>=today; dropped 原料藥/菌疫/硬空膠囊 + expired",
            "normalization": "by_name keyed on canonical(中文品名) (quote-insensitive); stem = strip quoted 廠商 prefix + trailing 劑量 + trailing 劑型, then canonical()",
            "ambiguity_rule": "stem or full-name → >1 distinct ingredient-set ⇒ ambiguous=true (lookup must defer, not guess). Comparison key collapses ONLY SULPH↔SULF spelling (US/UK); display keeps original.",
            "stats": stats,
        },
        "by_name": {k: {kk: vv for kk, vv in v.items() if kk != "_keys"} for k, v in by_name.items()},
        "by_stem": by_stem,
        "english_to_zh": {k: sorted(v) for k, v in en_index.items()},
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print("=== BUILD STATS ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"  output: {OUT_PATH} ({OUT_PATH.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
