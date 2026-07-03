# -*- coding: utf-8 -*-
"""
Runtime loader + resolver for the TFDA brand→ingredient lookup table (ADR 007 T2a).

Deterministic 中文品名 / brand-stem → 主成分 (INN) resolution for Verify's
「仍要送出（不建議）」 proceed-anyway path. A Chinese brand (冠脂妥) resolves to its TFDA
active ingredient (ROSUVASTATIN CALCIUM) instead of the LLM's confident-wrong guess
(it said simvastatin). Ambiguous names DEFER — they never silently pick one product
(the no-fabrication principle applied to lookup).

ADDITIVE by contract: a miss returns status="miss" and the caller falls through to
EXACTLY today's behavior. resolve_brand() is TOTAL — it never raises; any internal
problem (missing table, malformed record) degrades to status="miss".

The NORMALIZATION below is the SINGLE SOURCE OF TRUTH shared with the build script
(scripts/build_tfda_brand_ingredient.py imports it) so the on-disk table keys and the
runtime query keys can never drift.
"""
import datetime
import json
import logging
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

# data/tfda/brand_ingredient.json resolved relative to the repo root via __file__,
# so it works regardless of CWD (Docker WORKDIR=/app → /app/data/tfda/...).
#   api/services/tfda_lookup.py → parents[0]=services, [1]=api, [2]=repo root
TABLE_PATH = Path(__file__).resolve().parents[2] / "data" / "tfda" / "brand_ingredient.json"

# ── Normalization (SHARED with scripts/build_tfda_brand_ingredient.py) ──────────────

# Quote characters stripped at match time (decision ②: quote-insensitive matching).
# Quotes don't change the drug — 「"美"利風油」 ≡ 美利風油. Stripping is a safe miss→hit.
_QUOTE_CHARS = "\"“”＂「」『』'＇’‘`｀"
_QUOTE_RE = re.compile("[" + re.escape(_QUOTE_CHARS) + "]")

# CJK presence gate: only Chinese tokens are resolved. Latin/English INN tokens
# (warfarin, aspirin) return "miss" untouched → English path keeps today's behavior.
_CJK_RE = re.compile(r"[㐀-䶿一-鿿豈-﫿]")

# Dosage forms to strip from the tail of 中文品名 (longest first → greedy correct match).
DOSAGE_FORMS = [
    "持續性藥效膜衣錠", "持續性藥效錠", "腸溶微粒膠囊", "口服懸液用顆粒", "口服懸浮液用粉",
    "膜衣錠", "糖衣錠", "腸溶錠", "口含錠", "舌下錠", "發泡錠", "咀嚼錠", "分散錠", "包衣錠",
    "持續性藥效膠囊", "緩釋膠囊", "腸溶膠囊", "硬膠囊", "軟膠囊", "膠囊劑", "膠囊",
    "口服液劑", "口服溶液劑", "口服懸液劑", "口服懸浮液", "內服液劑", "外用液劑", "溶液劑",
    "糖漿劑", "乳膏劑", "軟膏劑", "凝膠劑", "乳液劑", "貼片劑", "貼布", "栓劑",
    "注射劑", "注射液", "注射用粉", "點眼劑", "眼用懸液劑", "眼藥水", "鼻噴劑", "吸入劑",
    "散劑", "顆粒劑", "細粒劑", "錠劑", "口服錠", "錠", "液", "粉", "膏", "丸",
]
# leading manufacturer prefix in quotes: "福元" / 「中美」 / 『…』 / ＂…＂
QUOTE_PREFIX = re.compile(r'^[\s]*["“”＂「『]([^"“”＂」』]{1,12})["“”＂」』]\s*')
# trailing dosage tokens: number(+sep) + unit, optionally repeated
DOSE_TOKEN = re.compile(
    r'(?:[\d０-９][\d０-９.,．／/×xX\-－~～]*\s*'
    r'(?:公絲|毫克|微克|奈克|公克|克|毫升|公升|公撮|％|%|單位|國際單位|億|萬|'
    r'MG|MCG|ML|G|IU|U|MEQ|mg|mcg|ml|iu))+\s*$'
)


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def canonical(s: str) -> str:
    """Match key: drop quote chars anywhere + collapse whitespace (decision ②)."""
    return norm_ws(_QUOTE_RE.sub("", s or ""))


def has_cjk(s: str) -> bool:
    return bool(_CJK_RE.search(s or ""))


def clean_ingredient(raw: str) -> str:
    """Strip the trailing '( … )' salt/synonym/EQ-TO parenthetical; keep inline salt."""
    s = norm_ws(raw)
    s = re.sub(r"\s*\([^()]*\)\s*$", "", s).strip()   # one trailing parenthetical
    s = re.sub(r"\s*\([^()]*\)\s*$", "", s).strip()   # a second, if nested-ish
    return norm_ws(s).upper()


def parse_ingredients(field_val: str):
    """主成分略述 → (raw_list, clean_list). Combos are ';;'-delimited."""
    raw_list = [norm_ws(p) for p in (field_val or "").split(";;") if norm_ws(p)]
    clean_list = []
    for p in raw_list:
        c = clean_ingredient(p)
        if c and c not in clean_list:
            clean_list.append(c)
    return raw_list, clean_list


def norm_indication(text: str) -> str:
    """Normalize 適應症 text for display + keying. Collapse whitespace ONLY — this is
    CITED label text (ingest-and-cite), never a rewrite; the Chinese content is preserved
    verbatim so what we cite is exactly what the TFDA label says."""
    return norm_ws(text)


# ── Shared snapshot read + filter (ONE read, ONE filter set for BOTH TFDA consumers:
#    T2a brand→ingredient lookup AND grounding-lite indication corpus — no drift) ────────

def load_snapshot_records(zip_path) -> list:
    """Read the pinned id=37 snapshot ZIP → list of raw record dicts."""
    z = zipfile.ZipFile(str(zip_path))
    return json.loads(z.read(z.namelist()[0]).decode("utf-8"))


def snapshot_ref_date(zip_path) -> str:
    """Derive the reference date (YYYY/MM/DD) from the pinned snapshot dir name
    (…/snapshot_YYYYMMDD/…), so 有效日期 expiry is evaluated AS-OF the pinned snapshot —
    reproducible (not `today()`, which drifts and would make rebuilds non-deterministic)."""
    m = re.search(r"snapshot_(\d{4})(\d{2})(\d{2})", str(zip_path))
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    return datetime.date.today().strftime("%Y/%m/%d")   # fallback only


def _license_kind(r: dict) -> str:
    return (r.get("許可證種類") or "").replace("　", "").strip()


def filter_active_preparations(records: list, ref_date: str):
    """Shared filter for BOTH TFDA consumers: keep 製劑 + 未註銷(註銷狀態 empty) +
    有效日期 >= ref_date; drop 原料藥/菌疫/硬空膠囊 + cancelled + expired.
    Returns (kept_records, stats)."""
    kept = []
    drop_kind = drop_cancelled = drop_expired = 0
    for r in records:
        if _license_kind(r) != "製劑":
            drop_kind += 1; continue
        if str(r.get("註銷狀態", "")).strip():
            drop_cancelled += 1; continue
        eff = str(r.get("有效日期", "")).strip()
        if not re.match(r"\d{4}/\d{2}/\d{2}", eff) or eff < ref_date:
            drop_expired += 1; continue
        kept.append(r)
    stats = {"input_rows": len(records), "dropped_non_製劑": drop_kind,
             "dropped_cancelled": drop_cancelled, "dropped_expired_or_no_date": drop_expired,
             "rows_after_filter": len(kept), "ref_date": ref_date}
    return kept, stats


# British/American orthography of the SAME word: "SULPH" (UK) vs "SULF" (US). The ONLY
# spelling pair collapsed — e.g. 'CLOPIDOGREL HYDROGEN SULPHATE' == '...SULFATE',
# 'SULPHASALAZINE' == 'SULFASALAZINE'. There is no drug pair that differs ONLY by SULPH/SULF
# yet is a DIFFERENT compound, so this never merges distinct drugs.
_SULPH_RE = re.compile(r"SULPH", re.IGNORECASE)


def ambiguity_key(ingredient: str) -> str:
    """AMBIGUITY COMPARISON KEY for an ingredient string. Collapses ONLY the SULPH↔SULF
    British/American spelling of the same word; everything else is left intact. Two ingredient
    strings are "the same" iff they are identical after this single replacement — so
    QUETIAPINE vs QUETIAPINE FUMARATE, PYRIDOXINE vs VITAMIN B6, salts, hydrates and synonyms
    all stay DISTINCT (decision ①). This is SPELLING canonicalization, NOT salt/synonym
    equivalence. The ingredient DISPLAY string keeps TFDA's original spelling; only this key
    is canonical."""
    return _SULPH_RE.sub("SULF", ingredient or "")


def brand_stem(zh_name: str) -> str:
    """Derive a brand stem: strip quoted 廠商 prefix, trailing 劑量, trailing 劑型."""
    s = norm_ws(zh_name)
    s = QUOTE_PREFIX.sub("", s).strip()          # drop leading "廠商"
    prev = None
    while prev != s:                              # strip dose tokens then a form, repeat until stable
        prev = s
        s = DOSE_TOKEN.sub("", s).strip()
        for f in DOSAGE_FORMS:
            if s.endswith(f) and len(s) > len(f):
                s = s[: -len(f)].strip()
                break
    s = DOSE_TOKEN.sub("", s).strip()
    return s or norm_ws(zh_name)                  # never return empty → fall back to full name


# ── Runtime resolution ──────────────────────────────────────────────────────────────

@dataclass
class Resolution:
    """Result of resolving one user-entered drug token against the TFDA table."""
    status: str                              # "resolved" | "ambiguous" | "miss"
    query: str = ""                          # original input token
    ingredients: list = field(default_factory=list)   # resolved INN(s) — for "resolved"
    is_combo: bool = False                   # True when >1 active in one product
    matched: str = ""                        # the full-name / stem that matched
    match_type: str = ""                     # "name" | "stem" | ""
    licenses: list = field(default_factory=list)        # TFDA 許可證字號 (citation)
    candidate_products: list = field(default_factory=list)   # for "ambiguous"
    candidate_sets: list = field(default_factory=list)       # for "ambiguous"


_TABLE = None
_LOAD_FAILED = False
_LOCK = Lock()

# ── Free-text brand detection (ADR 007 a1-i — Research QUERY-AUGMENT) ────────────────
#
# Research receives FREE TEXT (no structured drug list), so brand resolution there
# needs a detector over the query string. Design constraints (2026-07-03 probe):
#   - LONGEST-MATCH-FIRST per position; a consumed span never re-matches.
#   - Minimum key length 3 (1,218 stems are ≤2 chars — 胃/心律/美好-class common words).
#   - Curated GENERIC_CLASS_TERMS blocklist: commodity/class terms that ARE table keys
#     (感冒藥, 葡萄糖, 生理食鹽水, 雙氧水…) must never annotate — a license-count cap was
#     measured and rejected (resolved-stem max = 19 安比西林, real brands reach 8 → no
#     usable threshold). Transliterated GENERICS (紅黴素→ERYTHROMYCIN) stay matchable
#     on purpose — resolving them is correct, not a false positive.
#   - Ambiguous keys are DETECTED but carry status="ambiguous" — callers must use them
#     as an ambiguity flag ONLY, never for identity (no-fabrication principle).

MIN_DETECT_KEY_LEN = 3
MAX_TEXT_MATCHES = 3

GENERIC_CLASS_TERMS = frozenset({
    # symptom-class product terms
    "感冒藥", "感冒液", "感冒錠", "感冒膠囊", "感冒糖漿", "止咳糖漿", "咳嗽糖漿",
    "止痛藥", "退燒藥", "安眠藥", "眼藥水", "皮膚藥膏",
    # commodity / chemical / household terms that are also product names
    "葡萄糖", "生理食鹽水", "沖洗用食鹽水", "食鹽水", "氯化鈉", "氯化鉀", "氯化鈣",
    "氧化鎂", "氧化鋅", "碳酸鈣", "硫酸鎂", "雙氧水", "黃藥水", "紫藥水", "碘藥水",
    "維他命", "維生素", "綜合維他命", "胰島素", "黃體素", "甘油", "酒精", "凡士林",
})

_SCAN_INDEX = None  # first CJK char -> [candidate keys, longest first]


def _scan_index():
    """Lazy, thread-safe index over by_name + by_stem keys eligible for free-text
    detection (len ≥ MIN_DETECT_KEY_LEN, CJK, not a generic class term)."""
    global _SCAN_INDEX
    if _SCAN_INDEX is not None:
        return _SCAN_INDEX
    table = _load()
    if not table:
        return None
    with _LOCK:
        if _SCAN_INDEX is not None:
            return _SCAN_INDEX
        idx: dict = {}
        for source in ("by_name", "by_stem"):
            for k in table.get(source, {}):
                if len(k) < MIN_DETECT_KEY_LEN or not has_cjk(k) or k in GENERIC_CLASS_TERMS:
                    continue
                idx.setdefault(k[0], []).append(k)
        for lst in idx.values():
            lst.sort(key=len, reverse=True)
        _SCAN_INDEX = idx
    return _SCAN_INDEX


def detect_brands_in_text(text: str, max_matches: int = MAX_TEXT_MATCHES) -> list:
    """
    Deterministic free-text CJK brand detection for Research (a1-i QUERY-AUGMENT).

    TOTAL: never raises; non-CJK text, table-load failure, or no match all return [].
    Left-to-right scan; at each position the LONGEST eligible key wins and its span is
    consumed (never re-matched). Repeated brands dedupe to one entry. Returns at most
    `max_matches` entries of {start, end, token, resolution: Resolution} — callers use
    resolution.status: "resolved" → identity fact; "ambiguous" → ambiguity flag ONLY.
    """
    try:
        if not text or not has_cjk(text):
            return []
        idx = _scan_index()
        if not idx:
            return []
        results: list = []
        seen: set = set()
        i, n = 0, len(text)
        while i < n and len(results) < max_matches:
            matched = None
            for k in idx.get(text[i], ()):  # longest-first within this start char
                if text.startswith(k, i):
                    matched = k
                    break
            if matched is None:
                i += 1
                continue
            end = i + len(matched)
            if matched not in seen:
                seen.add(matched)
                r = resolve_brand(matched)
                if r.status in ("resolved", "ambiguous"):
                    results.append({"start": i, "end": end, "token": matched, "resolution": r})
            i = end  # consumed span never re-matches
        return results
    except Exception as e:  # defense in depth — detection must never break Research
        logger.warning("[TFDA] detect_brands_in_text failed: %s", e)
        return []


def _load():
    """Lazy, thread-safe, fail-soft load of the lookup table. Returns dict or None."""
    global _TABLE, _LOAD_FAILED
    if _TABLE is not None or _LOAD_FAILED:
        return _TABLE
    with _LOCK:
        if _TABLE is not None or _LOAD_FAILED:
            return _TABLE
        try:
            with open(TABLE_PATH, encoding="utf-8") as fh:
                _TABLE = json.load(fh)
            meta = _TABLE.get("_meta", {})
            logger.info("[TFDA] lookup table loaded: %s (built_at=%s, names=%d, stems=%d)",
                        TABLE_PATH.name, meta.get("built_at"),
                        len(_TABLE.get("by_name", {})), len(_TABLE.get("by_stem", {})))
        except Exception as e:
            _LOAD_FAILED = True
            logger.warning("[TFDA] lookup table unavailable (%s) — brand resolution disabled, "
                           "Verify falls through to today's behavior", e)
    return _TABLE


def reset_cache():
    """Test helper — force a reload on the next resolve_brand() call."""
    global _TABLE, _LOAD_FAILED, _SCAN_INDEX
    with _LOCK:
        _TABLE = None
        _LOAD_FAILED = False
        _SCAN_INDEX = None


def _resolved_from_sets(sets, *, query, matched, match_type, licenses):
    """A non-ambiguous record has exactly one distinct ingredient set."""
    ingredients = list(sets[0])
    return Resolution(
        status="resolved", query=query, ingredients=ingredients,
        is_combo=len(ingredients) > 1, matched=matched, match_type=match_type,
        licenses=list(licenses or []),
    )


def resolve_brand(name: str) -> Resolution:
    """
    Resolve a user-entered drug token to its TFDA active ingredient(s).

    TOTAL: never raises. Non-CJK tokens, table-load failures, and unmatched tokens
    all return status="miss" so the caller falls through to today's behavior.

    Lookup order (quote-insensitive throughout, decision ②):
      1. exact full 中文品名 (by_name, keyed on canonical())
      2. brand stem (by_stem, keyed on canonical(brand_stem()))
      3. miss
    """
    miss = Resolution(status="miss", query=name)
    try:
        if not name or not has_cjk(name):
            return miss
        table = _load()
        if not table:
            return miss

        q_canon = canonical(name)

        # 1. exact full-name match (quote-insensitive)
        rec = table.get("by_name", {}).get(q_canon)
        if rec:
            sets = rec.get("ingredient_sets") or []
            if rec.get("ambiguous") or len(sets) > 1:
                return Resolution(
                    status="ambiguous", query=name,
                    matched=rec.get("display_name") or q_canon, match_type="name",
                    candidate_sets=sets,
                    candidate_products=[rec.get("display_name") or q_canon],
                )
            if sets:
                return _resolved_from_sets(
                    sets, query=name, matched=rec.get("display_name") or q_canon,
                    match_type="name", licenses=rec.get("licenses"),
                )

        # 2. brand-stem match (quote-insensitive)
        stem_q = canonical(brand_stem(name))
        srec = table.get("by_stem", {}).get(stem_q)
        if srec:
            sets = srec.get("ingredient_sets") or []
            if srec.get("ambiguous") or len(sets) > 1:
                return Resolution(
                    status="ambiguous", query=name, matched=stem_q, match_type="stem",
                    candidate_sets=sets,
                    candidate_products=list(srec.get("products") or [])[:8],
                )
            if sets:
                return _resolved_from_sets(
                    sets, query=name, matched=stem_q, match_type="stem",
                    licenses=srec.get("licenses"),
                )

        return miss
    except Exception as e:  # defense in depth — resolution must never break Verify
        logger.warning("[TFDA] resolve_brand(%r) failed: %s", name, e)
        return miss
