"""
PHI (Protected Health Information) Detection Middleware
支援多國個資偵測：台灣、日本、美國

隱私保護原則：
- 攔截包含 PHI 的請求，防止傳送至 LLM
- 支援多國格式偵測
- 提供清晰的錯誤訊息引導使用者

Modes (PRD § 4.5 PHASE B 修訂):
- ``mode='guard'`` (default) — preserves all existing 5+ callers
  (Research / Verify / Explain / feedback / bug-report). Returns
  ``Optional[str]`` (PHI type or None).
- ``mode='share'`` — adds NHI 健保號 + 姓名+年齡 combo patterns on
  top of the existing 10. Locale-aware: 繁中 / 英 / 日 first-class;
  other 13 locales degrade to ``mode='guard'`` silently AND mark the
  result with ``unknown_locale_fallback=True`` so the frontend can
  show a stronger generic warning. Returns a dataclass with
  ``(is_safe, reasons, unknown_locale_fallback)``.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Medical units — used to exclude false positives from numeric patterns
_MEDICAL_UNIT_AFTER = re.compile(
    r'\s*(?:mg|mL|mmol|dL|g/dL|kg|IU|mcg|µg|units?|mmHg|%|mEq|ng|pg|fL|cells?|copies)',
    re.IGNORECASE
)
_MEDICAL_UNIT_BEFORE = re.compile(
    r'(?:ref|range|value|level|count|result|dose|concentration)\s*[:=]?\s*$',
    re.IGNORECASE
)


# ============ Share-mode: locale buckets ============
# First-class locales receive their own targeted patterns. Anything
# else falls back to mode='guard' AND sets unknown_locale_fallback so
# the UI can warn the user that the auto-check is partial.
_SHARE_FIRST_CLASS_LOCALES = {"zh-TW", "en", "ja"}


@dataclass
class ShareDetectResult:
    """Return shape for ``PHIDetector.detect(text, mode='share')``.

    is_safe:
        True if no PHI / share-specific pattern hit. The frontend
        should still show the generic disclaimer regardless.
    reasons:
        Human-readable list of every pattern that fired. Empty when
        is_safe=True. Used by the Share Modal to show *which* type
        was detected (e.g. "Taiwan ID", "NHI", "Name+age combo").
    unknown_locale_fallback:
        True when the caller passed an unsupported locale (or none
        could be inferred) and the share-mode patterns therefore did
        NOT run — only the 10 existing guard patterns did. Frontend
        uses this to render a stronger generic warning.
    """

    is_safe: bool
    reasons: list[str] = field(default_factory=list)
    unknown_locale_fallback: bool = False


class PHIDetector:
    """
    多國 PHI 偵測器

    支援格式：
    - 台灣：身分證、手機號碼
    - 日本：My Number（需關鍵字）、手機號碼
    - 美國：SSN（需分隔符或關鍵字）、電話號碼、MRN
    - 通用：Email、信用卡號

    Share-mode adds:
    - TW NHI 健保號 (12-digit, keyword-anchored or zh-TW standalone)
    - Name+age combo (zh-TW, en, ja) — last-line defense for case
      reports / patient narratives that name+age accidentally pin
      to a real person.
    """

    # ============ 台灣 Taiwan ============
    TAIWAN_ID_PATTERN = re.compile(
        r'\b[A-Z][12]\d{8}\b',  # 身分證：A123456789
        re.IGNORECASE
    )

    TAIWAN_PHONE_PATTERN = re.compile(
        r'\b09\d{8}\b'  # 手機：09xxxxxxxx
    )

    # ============ 日本 Japan ============
    # My Number requires keyword prefix to avoid false positives on arbitrary 12-digit numbers
    JAPAN_MY_NUMBER_KEYWORD = re.compile(
        r'(?:マイナンバー|個人番号|my\s*number)\s*[:：]?\s*',
        re.IGNORECASE
    )
    JAPAN_MY_NUMBER_FORMAT = re.compile(
        r'\d{4}[-\s]?\d{4}[-\s]?\d{4}'
    )

    JAPAN_PHONE_PATTERN = re.compile(
        r'\b0[789]0[-\s]?\d{4}[-\s]?\d{4}\b'  # 手機：090-1234-5678
    )

    # ============ 美國 USA ============
    # SSN: require dash separators (123-45-6789) OR keyword prefix (SSN/Social Security)
    USA_SSN_WITH_DASH = re.compile(
        r'\b(?!000|666|9\d{2})\d{3}-\d{2}-\d{4}\b'  # Exclude invalid: 000, 666, 9xx
    )
    USA_SSN_KEYWORD = re.compile(
        r'(?:SSN|Social\s+Security(?:\s+Number)?)\s*[:：#]?\s*',
        re.IGNORECASE
    )
    USA_SSN_PLAIN = re.compile(
        r'(?!000|666|9\d{2})\d{3}[-\s]?\d{2}[-\s]?\d{4}'
    )

    USA_PHONE_PATTERN = re.compile(
        r'\b\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}\b'  # 電話：(123) 456-7890
    )

    USA_MRN_PATTERN = re.compile(
        r'\bMRN[-:\s]?\d{6,10}\b',  # Medical Record Number
        re.IGNORECASE
    )

    # ============ 通用 Universal ============
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )

    CREDIT_CARD_PATTERN = re.compile(
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'  # 信用卡：1234-5678-9012-3456
    )

    # 病歷號格式 — only used in sanitize_for_log(), NOT in detect().
    # Reason: patterns like \b[A-Z]{2,3}\d{6,10}\b and \b\d{8,12}\b are too broad
    # for blocking (would false-positive on NDC codes, lab reference numbers, etc.),
    # but useful for masking in audit logs as a defense-in-depth measure.
    MEDICAL_RECORD_PATTERNS = [
        re.compile(r'\b[A-Z]{2,3}\d{6,10}\b'),  # AB123456789
        re.compile(r'\b\d{8,12}\b'),            # 純數字病歷號
    ]

    # ============ Share-mode: TW NHI 健保號 ============
    # NHI member IDs are 12 digits. Keyword-anchored variant works
    # across locales — heuristic: keyword 健保 / 健保卡 / NHI within
    # 10 chars before a 12-digit run. Example match: "健保號 123456789012".
    NHI_KEYWORD_PATTERN = re.compile(
        r'(?:健保(?:卡|號|證)?|NHI)[^\d]{0,10}(\d{12})\b',
        re.IGNORECASE
    )
    # zh-TW standalone variant: a bare 12-digit run inside Chinese
    # text is rarely something other than NHI / case file numbers and
    # is worth blocking when sharing. Caller restricts this to zh-TW.
    NHI_STANDALONE_PATTERN = re.compile(r'(?<!\d)\d{12}(?!\d)')

    # ============ Share-mode: Name+age combos ============
    # zh-TW: 中文姓名 (2-4) + (optional separator) + 年齡 + 歲|y/o|歲女|歲男|岁
    NAME_AGE_ZH_TW_PATTERN = re.compile(
        r'[一-鿿]{2,4}\s*[,，、 ]?\s*\d{1,3}\s*(?:歲女|歲男|歲|岁|y/o)'
    )

    # en: capitalized first + last + age + y/o or years old
    NAME_AGE_EN_PATTERN = re.compile(
        r'\b[A-Z][a-z]+\s+[A-Z][a-z]+,?\s+(?:a\s+)?\d{1,3}[- ]?(?:y/?o|years?[- ]old)\b',
        re.IGNORECASE,
    )

    # ja: hiragana / katakana / kanji name (2-5) + sep + age + 歳
    NAME_AGE_JA_PATTERN = re.compile(
        r'[一-鿿぀-ゟ゠-ヿ]{2,5}[,、 ]\s*\d{1,3}\s*歳'
    )

    @classmethod
    def _has_medical_context(cls, text: str, match_start: int, match_end: int) -> bool:
        """Check if a numeric match is surrounded by medical units/context."""
        after_text = text[match_end:match_end + 20]
        if _MEDICAL_UNIT_AFTER.match(after_text):
            return True
        before_text = text[max(0, match_start - 30):match_start]
        if _MEDICAL_UNIT_BEFORE.search(before_text):
            return True
        return False

    @classmethod
    def _detect_guard(cls, text: str) -> Optional[str]:
        """Original 10-pattern guard. Identical behavior to pre-PHASE-B
        ``detect()``. Kept as a private helper so both modes can call
        it without duplicating logic."""
        if not text or len(text.strip()) == 0:
            return None

        # 台灣身分證
        if cls.TAIWAN_ID_PATTERN.search(text):
            return "Taiwan ID (台灣身分證)"

        # 台灣手機
        if cls.TAIWAN_PHONE_PATTERN.search(text):
            return "Taiwan Phone (台灣手機號碼)"

        # 日本 My Number — requires keyword prefix
        kw_match = cls.JAPAN_MY_NUMBER_KEYWORD.search(text)
        if kw_match:
            after_kw = text[kw_match.end():]
            if cls.JAPAN_MY_NUMBER_FORMAT.match(after_kw):
                return "Japan My Number (日本個人番號)"

        # 日本手機
        if cls.JAPAN_PHONE_PATTERN.search(text):
            return "Japan Phone (日本手機號碼)"

        # 美國 SSN — with dash separators (most reliable)
        m = cls.USA_SSN_WITH_DASH.search(text)
        if m and not cls._has_medical_context(text, m.start(), m.end()):
            return "US SSN (美國社會安全號碼)"

        # 美國 SSN — with keyword prefix (no dash required)
        kw_match = cls.USA_SSN_KEYWORD.search(text)
        if kw_match:
            after_kw = text[kw_match.end():]
            if cls.USA_SSN_PLAIN.match(after_kw):
                return "US SSN (美國社會安全號碼)"

        # 美國 MRN
        if cls.USA_MRN_PATTERN.search(text):
            return "US MRN (美國病歷號)"

        # 美國電話 — area code format provides reasonable specificity
        m = cls.USA_PHONE_PATTERN.search(text)
        if m and not cls._has_medical_context(text, m.start(), m.end()):
            # Only flag if it looks like a phone (has parentheses or dashes)
            matched = m.group(0)
            if '(' in matched or '-' in matched:
                return "US Phone (美國電話號碼)"

        # Email — only flag personal-looking emails
        if cls.EMAIL_PATTERN.search(text):
            email_match = cls.EMAIL_PATTERN.search(text)
            email = email_match.group(0)
            if re.search(r'\d+[a-z]+|\b(john|mary|patient)\d*\b', email, re.IGNORECASE):
                return "Email (個人電子郵件)"

        # 信用卡
        if cls.CREDIT_CARD_PATTERN.search(text):
            cc_match = cls.CREDIT_CARD_PATTERN.search(text)
            if cc_match and not re.search(r'20\d{2}', cc_match.group(0)):
                return "Credit Card (信用卡號)"

        return None

    @classmethod
    def _detect_share_extras(cls, text: str, locale: Optional[str]) -> list[str]:
        """Run share-mode-only patterns. Caller decides whether to
        invoke this based on locale; this method does NOT reason
        about fallback semantics itself."""
        reasons: list[str] = []

        # NHI keyword-anchored — locale-agnostic (anyone can write 健保 / NHI)
        if cls.NHI_KEYWORD_PATTERN.search(text):
            reasons.append("TW NHI (健保號)")

        # NHI standalone — only enable for zh-TW because a bare 12-digit
        # number in en / ja is too ambiguous (could be MRN, lab ID).
        if locale == "zh-TW" and cls.NHI_STANDALONE_PATTERN.search(text):
            # Avoid double-firing when the keyword variant already hit
            if "TW NHI (健保號)" not in reasons:
                reasons.append("TW NHI (健保號 standalone)")

        # Name+age combos — restrict each to its own first-class locale
        if locale == "zh-TW" and cls.NAME_AGE_ZH_TW_PATTERN.search(text):
            reasons.append("Name+age combo (zh-TW)")
        if locale == "en" and cls.NAME_AGE_EN_PATTERN.search(text):
            reasons.append("Name+age combo (en)")
        if locale == "ja" and cls.NAME_AGE_JA_PATTERN.search(text):
            reasons.append("Name+age combo (ja)")

        return reasons

    @classmethod
    def detect(
        cls,
        text: str,
        mode: str = "guard",
        locale: Optional[str] = None,
    ):
        """
        偵測文字中是否包含 PHI

        Args:
            text: 要檢查的文字
            mode: 'guard' (default) preserves the legacy contract.
                'share' adds NHI + name+age combo patterns and returns
                a richer dataclass.
            locale: BCP-47 tag (e.g. 'zh-TW', 'en', 'ja'). Only honored
                in mode='share'.

        Returns:
            mode='guard'  → Optional[str]: PHI type, or None.
            mode='share'  → ShareDetectResult.
        """
        if mode == "guard":
            return cls._detect_guard(text)

        if mode != "share":
            raise ValueError(f"PHIDetector.detect: unknown mode {mode!r}")

        # ── share mode ────────────────────────────────────────────
        reasons: list[str] = []
        guard_hit = cls._detect_guard(text)
        if guard_hit:
            reasons.append(guard_hit)

        if locale and locale in _SHARE_FIRST_CLASS_LOCALES:
            reasons.extend(cls._detect_share_extras(text, locale))
            unknown_fallback = False
        elif locale is None:
            # Caller didn't tell us — run all 3 first-class buckets
            # so we don't silently skip detection. Mark fallback so
            # the UI can show a stronger generic warning.
            for loc in ("zh-TW", "en", "ja"):
                for r in cls._detect_share_extras(text, loc):
                    if r not in reasons:
                        reasons.append(r)
            unknown_fallback = True
        else:
            # Other 13 locales: no first-class share patterns; rely
            # only on the existing guard hits.
            unknown_fallback = True

        return ShareDetectResult(
            is_safe=not reasons,
            reasons=reasons,
            unknown_locale_fallback=unknown_fallback,
        )

    @classmethod
    def sanitize_for_log(cls, text: Optional[str], mask_char: str = "***") -> Optional[str]:
        """
        對文字進行脫敏處理，用於 Audit Log

        Args:
            text: 要處理的文字
            mask_char: 遮罩字符

        Returns:
            脫敏後的文字
        """
        if not text:
            return text

        sanitized = text

        # Mask known patterns
        sanitized = cls.TAIWAN_ID_PATTERN.sub(mask_char, sanitized)
        sanitized = cls.TAIWAN_PHONE_PATTERN.sub(mask_char, sanitized)
        sanitized = cls.JAPAN_MY_NUMBER_FORMAT.sub(mask_char, sanitized)
        sanitized = cls.JAPAN_PHONE_PATTERN.sub(mask_char, sanitized)
        sanitized = cls.USA_SSN_WITH_DASH.sub(mask_char, sanitized)
        sanitized = cls.USA_MRN_PATTERN.sub(mask_char, sanitized)
        sanitized = cls.USA_PHONE_PATTERN.sub(mask_char, sanitized)
        sanitized = cls.EMAIL_PATTERN.sub(mask_char, sanitized)
        sanitized = cls.CREDIT_CARD_PATTERN.sub(mask_char, sanitized)

        # Defense-in-depth: also mask broad patterns in logs
        for pattern in cls.MEDICAL_RECORD_PATTERNS:
            sanitized = pattern.sub(mask_char, sanitized)

        return sanitized

    @classmethod
    def is_safe(cls, text: str) -> bool:
        """
        快速檢查文字是否安全（不含 PHI）

        Args:
            text: 要檢查的文字

        Returns:
            True 如果安全，False 如果包含 PHI
        """
        return cls.detect(text) is None


# ============================================================
# Smoke test (PHASE B step 1)
# Run: python -m api.middleware.phi_handler
# ============================================================
if __name__ == "__main__":  # pragma: no cover
    cases = [
        ("健保號 123456789012, metformin 適合嗎", "zh-TW", False, "TW NHI keyword"),
        ("王小明 65 歲 metformin 適合嗎", "zh-TW", False, "zh-TW name+age"),
        ("John Doe, 65 y/o, takes warfarin", "en", False, "en name+age"),
        ("田中 65歳 メトホルミン", "ja", False, "ja name+age"),
        ("Is metformin appropriate for type 2 diabetes?", "en", True, "clean en"),
        ("metformin 二型糖尿病 第一線藥物嗎", "zh-TW", True, "clean zh-TW"),
        # Standalone 12-digit only fires for zh-TW
        ("Lab batch number 123456789012 expired", "en", True, "12-digit en (no NHI keyword)"),
        ("批號 123456789012 已過期", "zh-TW", False, "12-digit zh-TW standalone"),
    ]

    print("== mode='share' ==")
    all_pass = True
    for text, locale, expect_safe, label in cases:
        res = PHIDetector.detect(text, mode="share", locale=locale)
        ok = res.is_safe is expect_safe
        all_pass = all_pass and ok
        print(f"[{'PASS' if ok else 'FAIL'}] {label}: is_safe={res.is_safe} reasons={res.reasons} fallback={res.unknown_locale_fallback}")

    print("\n== mode='guard' (legacy contract preserved) ==")
    # On the same name+age strings, guard mode returns None — that's
    # the whole point of mode='share': don't regress the existing 5+
    # callers that should NOT block name+age.
    for text, locale, _expect_safe, label in cases:
        res = PHIDetector.detect(text)
        print(f"  guard: {label} -> {res!r}")

    # Unknown locale → fallback flag
    res = PHIDetector.detect("田中 65歳 メトホルミン", mode="share", locale="th")
    print(f"\nunknown locale 'th' → fallback={res.unknown_locale_fallback} is_safe={res.is_safe}")

    print("\nALL PASS" if all_pass else "\nSOME FAILED")
