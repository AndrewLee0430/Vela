"""
api/utils/language_detector.py
統一語言偵測模組 — v1.0

所有 endpoint（research / verify / explain）共用同一個語言偵測邏輯。
加新語言只需更新此檔案。
"""

import re

# ─── Language map ────────────────────────────────────────────────────────────
# ISO 639-1 code → human-readable name for prompts
LANGUAGE_NAMES: dict[str, str] = {
    "zh": "Traditional Chinese (繁體中文)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "es": "Spanish (Español)",
    "fr": "French (Français)",
    "de": "German (Deutsch)",
    "it": "Italian (Italiano)",
    "pt": "Portuguese (Português)",
    "th": "Thai (ภาษาไทย)",
    "en": "English",
}

# ─── Unicode range heuristics (fast, no API call) ────────────────────────────

def _detect_by_script(text: str) -> str | None:
    """
    Fast script-based detection using Unicode ranges.
    Returns ISO 639-1 code or None if ambiguous.
    """
    counts: dict[str, int] = {k: 0 for k in LANGUAGE_NAMES}

    for ch in text:
        cp = ord(ch)
        # CJK Unified Ideographs — Chinese / Japanese Kanji
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            counts["zh"] += 1
            counts["ja"] += 1   # Kanji is shared; disambiguate below
        # Hiragana / Katakana → definitively Japanese
        elif (0x3040 <= cp <= 0x309F) or (0x30A0 <= cp <= 0x30FF):
            counts["ja"] += 5   # strong signal
            counts["zh"] -= 1
        # Hangul → Korean
        elif 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF:
            counts["ko"] += 5
        # Thai
        elif 0x0E00 <= cp <= 0x0E7F:
            counts["th"] += 5

    # CJK disambiguation: if Hiragana/Katakana found, it's Japanese
    if counts["ja"] > 3 and counts["ja"] > counts["zh"]:
        return "ja"
    if counts["ko"] > 3:
        return "ko"
    if counts["th"] > 3:
        return "th"
    if counts["zh"] > 3:
        return "zh"

    return None  # Latin-script languages need keyword heuristics


# Common medical stopwords per language (Latin-script disambiguation)
_LATIN_SIGNALS: dict[str, list[str]] = {
    "es": ["medicamento", "mg", "diario", "dosis", "veces", "al día", "referencia",
           "paciente", "actuale", "medicamentos"],
    "fr": ["médicament", "fois", "par jour", "référence", "actuels", "patient",
           "milligramme", "résultats", "analyse"],
    "de": ["täglich", "zweimal", "Referenz", "Medikamente", "einmal", "aktuell",
           "Milligramm", "Laborwerte", "Patient"],
    "it": ["farmaci", "giorno", "riferimento", "volta", "attuale", "paziente",
           "milligrammo", "analisi", "risultati"],
    "pt": ["medicamento", "vezes", "diário", "referência", "atual", "paciente",
           "miligramo", "análise", "resultados"],
}


def _detect_latin_language(text: str) -> str:
    """
    Heuristic detection for Latin-script European languages.
    Returns best-guess ISO code or 'en' as default.
    """
    text_lower = text.lower()
    scores: dict[str, int] = {lang: 0 for lang in _LATIN_SIGNALS}

    for lang, signals in _LATIN_SIGNALS.items():
        for signal in signals:
            if signal.lower() in text_lower:
                scores[lang] += 1

    best_lang = max(scores, key=lambda k: scores[k])
    if scores[best_lang] >= 2:
        return best_lang
    return "en"


# ─── Public API ──────────────────────────────────────────────────────────────

def detect_language(text: str) -> str:
    """
    Detect the primary language of input text.
    Returns ISO 639-1 code (e.g. 'en', 'zh', 'ja', 'fr').

    Strategy:
    1. Unicode script heuristics (fast, no API call)
    2. Latin keyword signals for European languages
    3. Default to 'en'
    """
    if not text or not text.strip():
        return "en"

    # Step 1: Script-based detection
    script_lang = _detect_by_script(text)
    if script_lang:
        return script_lang

    # Step 2: Latin-script language disambiguation
    return _detect_latin_language(text)


def get_language_instruction(lang_code: str) -> str:
    """
    Returns an explicit language instruction string for system prompts.
    Example: 'LANGUAGE: Respond entirely in French (Français).'
    """
    lang_name = LANGUAGE_NAMES.get(lang_code, f"the same language as the input ({lang_code})")
    return f"LANGUAGE: Respond entirely in {lang_name}. Do NOT switch to English."


def get_language_name(lang_code: str) -> str:
    """Human-readable language name for display / logging."""
    return LANGUAGE_NAMES.get(lang_code, lang_code)