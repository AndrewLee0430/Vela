# -*- coding: utf-8 -*-
"""B0 (post fly 226) — public FAQ copy must not describe REMOVED features.

THE BUSINESS RULE (CLAUDE.md Rule 17)
-------------------------------------
The FAQ told users, in all 16 languages, to rely on a 🟢🟡🔴 evidence-strength
grading ("Strong evidence (green)…") that the generator STOPPED EMITTING at
3ad3ddc (2026-06-10) — removed precisely because it was an unverified LLM
self-label — and whose last dead render path was deleted at fly 221. Public
copy teaching users to trust a signal that was removed as untrustworthy is a
live honesty defect, and nothing caught it for two months.

SCOPE, stated honestly: this is a REGRESSION guard for that specific removed
feature, not a general dead-feature detector. It fails if the deleted Q&A (or
its colour-grading language) reappears in any locale; it cannot know about the
NEXT feature that gets removed. The general defence is the removal checklist:
when a user-visible feature dies, grep the FAQ.
"""
import re
from pathlib import Path

import pytest

_FAQ = Path(__file__).resolve().parents[1] / "utils" / "i18n-faq.ts"

# The 16 deleted question strings, verbatim (harvested from the pre-B0 file).
_DELETED_QUESTIONS = [
    "What does evidence strength mean?",
    "證據強度是什麼意思？",
    "证据强度是什么意思？",
    "エビデンス強度とは？",
    "근거 강도란?",
    "¿Qué significa la fuerza de la evidencia?",
    "Que signifie la force de l\\u2019évidence ?",
    "Was bedeutet Evidenzstärke?",
    "Cosa significa forza dell\\u2019evidenza?",
    "O que significa força da evidência?",
    "ความแข็งแกร่งของหลักฐาน หมายความว่าอะไร?",
    "ماذا تعني قوة الدليل؟",
    "साक्ष्य शक्ति का क्या अर्थ है?",
    "প্রমাণের শক্তি কী মানে?",
    "מה המשמעות של עוצמת ראיות?",
    "Độ mạnh bằng chứng nghĩa là gì?",
]

# The colour-as-grade signature in each language: "(green)"-style parentheticals
# from the deleted answers. Any one of these reappearing means grading language
# is back, even under a differently-worded question.
_GRADING_SIGNATURES = [
    "(green)", "（綠色）", "（绿色）", "（緑）", "(녹색)", "(verde)", "(vert)",
    "(grün)", "(เขียว)", "(أخضر)", "(हरा)", "(সবুজ)", "(ירוק)", "(xanh)",
    "evidence-graded", "evidence strength",
]


@pytest.fixture(scope="module")
def faq_source() -> str:
    return _FAQ.read_text(encoding="utf-8")


def test_deleted_evidence_strength_qa_stays_deleted(faq_source):
    hits = [q for q in _DELETED_QUESTIONS if q in faq_source]
    assert not hits, (
        f"the removed evidence-strength FAQ entry has REAPPEARED in {len(hits)} "
        f"locale(s): {hits[:3]} — the feature it describes was removed at 3ad3ddc "
        "as an unverified LLM self-label; public copy must not teach users to rely on it."
    )


def test_no_colour_grading_language_in_faq(faq_source):
    hits = [s for s in _GRADING_SIGNATURES if s in faq_source]
    assert not hits, (
        f"colour-graded evidence language found in the FAQ: {hits} — "
        "Vela does not render an evidence-strength colour grade (removed 3ad3ddc / fly 221)."
    )


def test_the_guard_actually_fires():
    """A guard that cannot fail is dead weight — prove both checks fire."""
    tampered = _FAQ.read_text(encoding="utf-8") + "\n// (green) evidence strength"
    assert any(s in tampered for s in _GRADING_SIGNATURES)
    assert "What does evidence strength mean?" not in tampered  # deletion check is independent


def test_faq_file_still_has_all_16_locales(faq_source):
    """Guard the guard: an emptied file would pass the absence checks above."""
    for loc in ("en:", "'zh-TW':", "'zh-CN':", "ja:", "ko:", "es:", "fr:", "de:",
                "it:", "pt:", "th:", "ar:", "hi:", "bn:", "he:", "vi:"):
        assert re.search(r"^  " + re.escape(loc), faq_source, re.M), f"locale block missing: {loc}"
    # and the reworded answers actually exist (the fix landed, not just the deletion)
    assert "traced to their sources" in faq_source
    assert "回答都可追溯至其來源" in faq_source
