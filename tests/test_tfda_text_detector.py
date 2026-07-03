# -*- coding: utf-8 -*-
"""FP corpus + behavior gate for the free-text TFDA brand detector (ADR 007 a1-i, v195).

Business rule pinned (CLAUDE.md Rule 17): Research's QUERY-AUGMENT annotation is only
safe if the detector can NEVER fire on ordinary clinical/everyday CJK text. A false
positive here injects a wrong "X = <ingredient> per TFDA 許可證" identity fact into a
medical answer — worse than the mis-ID bug it fixes. This corpus is the HARD GATE:
if any case fails, the a1-i build stops (per the approved staged plan).

Sections:
  1. MUST-NOT-MATCH — short-stem (≤2 char) collisions, blocklisted generic/commodity
     terms, and non-key clinical words. Detector must return [].
  2. MUST-MATCH — real brands: sentence-initial, mid-sentence, full-name,
     longest-match-wins.
  3. AMBIGUITY — 太田胃散-class: detected, flagged ambiguous, NO identity.
  4. MIXED — CJK brand + English INN in one query.
  5. STRUCTURAL — index invariants (no reachable key <3 chars, blocklist absent),
     match cap, English-only input, dedup.

Run: python tests/test_tfda_text_detector.py   (or via pytest)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services.tfda_lookup import (  # noqa: E402
    detect_brands_in_text, _scan_index, GENERIC_CLASS_TERMS, MIN_DETECT_KEY_LEN,
)

# ── 1. MUST-NOT-MATCH ────────────────────────────────────────────────────────────
# Each sentence embeds a real table key that must be UNREACHABLE (≤2-char stem or
# blocklisted generic term) or a common clinical word that is not a key at all.
MUST_NOT_MATCH = [
    # mandated by the build spec
    "胃痛好幾天了怎麼辦",            # 胃 (1-char stem)
    "心律不整要吃什麼藥",            # 心律 (2-char stem)
    "感冒藥怎麼選",                  # 感冒藥 IS a 3-char ambiguous stem → blocklisted
    "美好的一天",                    # 美好 (2-char stem — resolves to a 6-active cold remedy!)
    # short-stem collisions derived from the by_stem scan (all real ≤2-char keys)
    "立克次體感染的治療",            # 立克
    "牙痛怎麼辦",                    # 牙痛
    "遇到急事要保持鎮定",            # 鎮定
    "睡前想好好舒眠",                # 舒眠
    "他的肝裕度不好",                # 肝裕 (contrived but embeds the key)
    "傷口很疏痛",                    # 疏痛
    "鼻爽了許多",                    # 鼻爽
    "多喝水多休息",                  # 水 (1-char)
    # blocklisted generic / commodity terms (real ≥3-char table keys)
    "打點滴的葡萄糖濃度是多少",      # 葡萄糖 (resolved DEXTROSE — must be suppressed)
    "生理食鹽水可以洗鼻子嗎",        # 生理食鹽水 (resolved NaCl — suppressed)
    "雙氧水消毒傷口好嗎",            # 雙氧水 (ambiguous — suppressed)
    "止咳糖漿有哪些成分",            # 止咳糖漿 (ambiguous — suppressed)
    "感冒糖漿可以混著喝嗎",          # 感冒糖漿 (ambiguous — suppressed)
    "氯化鉀點滴要多快",              # 氯化鉀 (ambiguous — suppressed)
    "紫藥水還買得到嗎",              # 紫藥水 (suppressed)
    "眼藥水一天點幾次",              # 眼藥水 (suppressed)
    # common clinical words that are NOT table keys (sanity)
    "高血壓怎麼控制",
    "糖尿病可以吃什麼水果",
    "高血脂需要吃藥嗎",
]


def test_must_not_match():
    for s in MUST_NOT_MATCH:
        hits = detect_brands_in_text(s)
        assert hits == [], f"FALSE POSITIVE on {s!r}: {[(h['token'], h['resolution'].status) for h in hits]}"


# ── 2. MUST-MATCH ────────────────────────────────────────────────────────────────

def test_brand_sentence_initial():
    hits = detect_brands_in_text("冠脂妥高血脂可以吃嗎")
    assert len(hits) == 1, f"expected exactly 冠脂妥: {hits}"
    h = hits[0]
    assert h["token"] == "冠脂妥" and h["start"] == 0
    assert h["resolution"].status == "resolved"
    assert h["resolution"].ingredients == ["ROSUVASTATIN CALCIUM"]
    assert h["resolution"].licenses, "許可證 anchors must be present"


def test_brand_mid_sentence():
    hits = detect_brands_in_text("請問冠脂妥怎麼吃")
    assert [h["token"] for h in hits] == ["冠脂妥"]
    assert hits[0]["resolution"].ingredients == ["ROSUVASTATIN CALCIUM"]


def test_full_name_longest_match_wins():
    # 冠脂妥膜衣錠10毫克 is a by_name key; the 3-char stem 冠脂妥 is inside it.
    # Longest-match must consume the FULL name (span never re-matches).
    hits = detect_brands_in_text("醫生開了冠脂妥膜衣錠10毫克給我")
    assert len(hits) == 1, f"expected one longest match: {hits}"
    assert hits[0]["token"] == "冠脂妥膜衣錠10毫克"
    assert hits[0]["resolution"].status == "resolved"
    assert hits[0]["resolution"].ingredients == ["ROSUVASTATIN CALCIUM"]


def test_second_resolved_brand():
    hits = detect_brands_in_text("保栓通吃多久要回診")
    assert [h["token"] for h in hits] == ["保栓通"]
    assert hits[0]["resolution"].ingredients == ["CLOPIDOGREL HYDROGEN SULFATE"]


# ── 3. AMBIGUITY ────────────────────────────────────────────────────────────────

def test_ambiguous_brand_flag_only_no_identity():
    hits = detect_brands_in_text("太田胃散怎麼吃")
    assert len(hits) == 1, f"太田胃散 must be detected exactly once: {hits}"
    h = hits[0]
    assert h["token"] == "太田胃散", "longest match must win over inner 胃散/胃"
    assert h["resolution"].status == "ambiguous"
    assert h["resolution"].ingredients == [], "ambiguous must carry NO identity"


# ── 4. MIXED CJK + English ──────────────────────────────────────────────────────

def test_mixed_cjk_brand_with_english_inn():
    text = "冠脂妥和warfarin一起吃可以嗎"
    hits = detect_brands_in_text(text)
    assert [h["token"] for h in hits] == ["冠脂妥"]
    # spans must not touch the Latin text
    h = hits[0]
    assert text[h["start"]:h["end"]] == "冠脂妥"
    assert "warfarin" in text[h["end"]:]


# ── 5. STRUCTURAL invariants ────────────────────────────────────────────────────

def test_index_has_no_short_or_blocklisted_keys():
    idx = _scan_index()
    assert idx, "scan index must build from the committed table"
    for first_char, keys in idx.items():
        for k in keys:
            assert len(k) >= MIN_DETECT_KEY_LEN, f"short key reachable: {k!r}"
            assert k not in GENERIC_CLASS_TERMS, f"blocklisted key reachable: {k!r}"
        # longest-first ordering (the longest-match guarantee)
        lens = [len(k) for k in keys]
        assert lens == sorted(lens, reverse=True), f"index not longest-first at {first_char!r}"


def test_match_cap():
    hits = detect_brands_in_text("冠脂妥保栓通循利寧安比西林都在吃", max_matches=3)
    assert len(hits) == 3, f"cap must hold: {[h['token'] for h in hits]}"


def test_english_only_returns_empty():
    assert detect_brands_in_text("does warfarin interact with aspirin") == []
    assert detect_brands_in_text("") == []


def test_repeated_brand_dedupes():
    hits = detect_brands_in_text("冠脂妥早上吃還是晚上吃冠脂妥")
    assert [h["token"] for h in hits] == ["冠脂妥"]


# ── 6. Endpoint annotation helper (server._annotate_research_question) ──────────
# B2 case 6 (unit half): pure-English questions must pass through BYTE-IDENTICAL.

os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


def test_english_question_byte_identical():
    from api.server import _annotate_research_question
    q = "What are the interactions between warfarin and aspirin?"
    out = _annotate_research_question(q)
    assert out is q, "English question must be returned as the SAME object (byte-identical)"


def test_cjk_nonbrand_question_byte_identical():
    from api.server import _annotate_research_question
    q = "高血壓怎麼控制比較好"
    assert _annotate_research_question(q) is q


def test_resolved_brand_annotation_append_only():
    from api.server import _annotate_research_question
    q = "冠脂妥高血脂可以吃嗎"
    out = _annotate_research_question(q)
    assert out.startswith(q), "append-not-replace: original question must lead"
    assert "冠脂妥 = ROSUVASTATIN CALCIUM" in out
    assert "per TFDA (Taiwan) 藥品許可證" in out
    assert "identity mapping only, not a safety or approval statement" in out


def test_ambiguous_brand_annotation_no_identity():
    from api.server import _annotate_research_question
    q = "太田胃散可以配溫水吃嗎"
    out = _annotate_research_question(q)
    assert out.startswith(q)
    assert "matches multiple distinct TFDA (Taiwan) products" in out
    assert "do NOT assume its identity" in out
    assert "=" not in out.replace(q, ""), "ambiguous annotation must carry NO identity mapping"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL  {name}: {e}")
    print(f"\n{'ALL PASS' if failures == 0 else f'{failures} FAILED'}")
    sys.exit(1 if failures else 0)
