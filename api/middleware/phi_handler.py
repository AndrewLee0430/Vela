"""
PHI (Protected Health Information) Detection Middleware
支援多國個資偵測：台灣、日本、美國

隱私保護原則：
- 攔截包含 PHI 的請求，防止傳送至 LLM
- 支援多國格式偵測
- 提供清晰的錯誤訊息引導使用者
"""

import re
import logging
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


class PHIDetector:
    """
    多國 PHI 偵測器

    支援格式：
    - 台灣：身分證、手機號碼
    - 日本：My Number（需關鍵字）、手機號碼
    - 美國：SSN（需分隔符或關鍵字）、電話號碼、MRN
    - 通用：Email、信用卡號
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
    def detect(cls, text: str) -> Optional[str]:
        """
        偵測文字中是否包含 PHI

        Args:
            text: 要檢查的文字

        Returns:
            偵測到的 PHI 類型，若無則返回 None
        """
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
