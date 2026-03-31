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
    "zh-TW": "Traditional Chinese (繁體中文)",
    "zh-CN": "Simplified Chinese (简体中文)",
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

# High-frequency characters unique to Traditional Chinese (繁→簡 pairs where forms differ)
# These chars have distinct simplified counterparts; presence → Traditional Chinese
_TRADITIONAL_CHARS = set(
    # Core high-frequency
    "醫藥體國說來對會時個問關長發學經號運點變廣區歲爲團與書從開實認議應種選際達進產質過講歡還這風飛"
    "鑽錢鐘記設該話請護觀證農邊遠適連遊離難電飯齊齒龍龜親覽觸較課評計專導態總戲戰機構東歷歸氣決"
    "準溫滿營獨環裡買車輸轉辦動務勞華參堅壓夢壞執備園圍圖則創劃員協寫節線練續網義習聯腦萬號處補視"
    "訂診詞試語誤調談論識貨費資賽購輕載辭遷鄉錄鍵隨雜黨響項順題飲驗髮鬥鸞麗齡"
    # Medical / common additions
    "腎臟雙於膽腸頭腦針劑療癥斷檢歷壓獲歸須頻雖僅強歸歡測傳獲價優僅億儀優償據擔擴攝數斷歲歷歸歲歸歲歸歲"
    "豐貧質鐵鈣鉀鈉鏈類顯願預餘駐驗齡點齊"
)
# High-frequency characters unique to Simplified Chinese
# These chars have distinct traditional counterparts; presence → Simplified Chinese
_SIMPLIFIED_CHARS = set(
    # Core high-frequency
    "医药体国说来对会时个问关长发学经号运点变广区岁为团与书从开实认议应种选际达进产质过讲欢还这风飞"
    "钻钱钟记设该话请护观证农边远适连游离难电饭齐齿龙龟亲览触较课评计专导态总戏战机构东历归气决"
    "准温满营独环里买车输转办动务劳华参坚压梦坏执备园围图则创划员协写节线练续网义习联脑万号处补视"
    "订诊词试语误调谈论识变货费资赛购轻较载辞迁乡录键随杂党龙响项顺题饮验发斗鸾丽龄"
    # Medical / common additions
    "肾脏双于胆肠头脑针剂疗症断检历压获归须频虽仅强归欢测传获价优仅亿仪优偿据担扩摄数断岁历归"
    "丰贫质铁钙钾钠链类显愿预余驻验龄点齐"
)

# ─── Unicode range heuristics (fast, no API call) ────────────────────────────

def _classify_zh_variant(text: str) -> str:
    """
    Distinguish Traditional vs Simplified Chinese.
    Returns 'zh-TW' or 'zh-CN'.
    Default: 'zh-TW' (primary market is Taiwan).
    Only returns 'zh-CN' if Simplified-only chars are found AND no Traditional chars.
    """
    has_trad = any(ch in _TRADITIONAL_CHARS for ch in text)
    has_simp = any(ch in _SIMPLIFIED_CHARS for ch in text)

    if has_trad:
        return "zh-TW"
    if has_simp and not has_trad:
        return "zh-CN"
    return "zh-TW"  # default to Traditional


def _detect_by_script(text: str) -> str | None:
    """
    Fast script-based detection using Unicode ranges.
    Returns language code or None if ambiguous.
    """
    cjk_count = 0
    ja_count = 0
    ko_count = 0
    th_count = 0

    for ch in text:
        cp = ord(ch)
        # CJK Unified Ideographs — Chinese / Japanese Kanji
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            cjk_count += 1
            ja_count += 1   # Kanji is shared; disambiguate below
        # Hiragana / Katakana → definitively Japanese
        elif (0x3040 <= cp <= 0x309F) or (0x30A0 <= cp <= 0x30FF):
            ja_count += 5   # strong signal
            cjk_count -= 1
        # Hangul → Korean
        elif 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF:
            ko_count += 5
        # Thai
        elif 0x0E00 <= cp <= 0x0E7F:
            th_count += 5

    # CJK/Japanese/Korean/Thai take priority over Latin characters.
    # Medical reports often mix local language with English terminology,
    # so even a single non-Latin character should trigger detection.
    if ja_count > 0 and ja_count > cjk_count:
        return "ja"
    if ko_count > 0:
        return "ko"
    if th_count > 0:
        return "th"
    if cjk_count > 0:
        return _classify_zh_variant(text)

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
    Returns language code (e.g. 'en', 'zh-TW', 'zh-CN', 'ja', 'fr').

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
    if lang_code == "en":
        return ""  # 英文不需要額外指令
    # Backward compat: bare "zh" → "zh-TW"
    if lang_code == "zh":
        lang_code = "zh-TW"
    lang_name = LANGUAGE_NAMES.get(lang_code)
    if lang_name:
        return f"LANGUAGE: Respond entirely in {lang_name}. Do NOT switch to English."
    return ""  # 未知語言：不注入指令，讓模型自行匹配用戶語言


def get_language_name(lang_code: str) -> str:
    """Human-readable language name for display / logging."""
    if lang_code == "zh":
        lang_code = "zh-TW"
    return LANGUAGE_NAMES.get(lang_code, lang_code)