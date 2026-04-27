"""Server-side localized strings for Explain pipeline (PRD § 2.7 Step 5).

Disclaimers and Step 3 LOINC scope-guard downgrade notes are injected
server-side per PRD § 2.7 spec ("fixed string injected server-side").
Locale lookup mirrors Verify § 2.9 response_language pattern.

16 languages: en, zh-TW, zh-CN, ja, ko, es, fr, de, it, pt, th, ar, hi, bn, he, vi.

Translation confidence:
- 8 source (English baseline)
- 72 high (native register where possible — TW medical conventions, PRC
  NMPA, ja polite-formal medical, etc.)
- 8 medium (style choices flagged inline)
- 40 machine translation pending native review (ar/he/hi/bn/th × 8 strings)
"""

from typing import Dict


EXPLAIN_DISCLAIMERS: Dict[str, str] = {
    "en": "⚠️ This explanation is for reference only. It does not constitute medical advice. Please consult your healthcare provider.",
    # zh-TW: addressee unified to 醫師 (Amendment 1) — TW medical disclaimer convention.
    "zh-TW": "⚠️ 本解讀僅供參考，不構成醫療建議。請諮詢您的醫師。",
    # zh-CN: addressee unified to 医生 (Amendment 1 extended) — matches DOWNGRADE notes.
    "zh-CN": "⚠️ 本解读仅供参考，不构成医疗建议。请咨询您的医生。",
    # TODO native review: addressee broader than DOWNGRADE 「医師」 —
    # confirm preferred unification per ja medical disclaimer convention
    "ja": "⚠️ この解説は参考用であり、医療アドバイスではありません。医療従事者にご相談ください。",
    # TODO native review: addressee broader than DOWNGRADE 「의사」 —
    # confirm preferred unification per ko medical disclaimer convention
    "ko": "⚠️ 본 해설은 참고용이며 의료 조언이 아닙니다. 의료 제공자와 상담하십시오.",
    "es": "⚠️ Esta explicación es solo de referencia. No constituye consejo médico. Consulte a su proveedor de salud.",
    "fr": "⚠️ Cette explication est fournie à titre indicatif. Elle ne constitue pas un avis médical. Consultez votre professionnel de santé.",
    "de": "⚠️ Diese Erklärung dient nur als Referenz und stellt keinen medizinischen Rat dar. Bitte konsultieren Sie Ihren Arzt.",
    "it": "⚠️ Questa spiegazione è solo a scopo di riferimento. Non costituisce un parere medico. Consulta il tuo medico.",
    "pt": "⚠️ Esta explicação é apenas para referência. Não constitui aconselhamento médico. Consulte o seu profissional de saúde.",
    # th/ar/hi/bn/he: machine translation, native medical reviewer pending.
    "th": "⚠️ คำอธิบายนี้ใช้เพื่อการอ้างอิงเท่านั้น ไม่ถือเป็นคำแนะนำทางการแพทย์ กรุณาปรึกษาผู้ให้บริการด้านสุขภาพของคุณ",
    "ar": "⚠️ هذا الشرح للإشارة فقط. لا يشكل نصيحة طبية. يُرجى استشارة مقدم الرعاية الصحية.",
    "hi": "⚠️ यह व्याख्या केवल संदर्भ के लिए है। यह चिकित्सा सलाह नहीं है। कृपया अपने स्वास्थ्य देखभाल प्रदाता से परामर्श करें।",
    "bn": "⚠️ এই ব্যাখ্যা শুধুমাত্র রেফারেন্সের জন্য। এটি চিকিৎসা পরামর্শ নয়। অনুগ্রহ করে আপনার স্বাস্থ্যসেবা প্রদানকারীর সাথে পরামর্শ করুন।",
    "he": "⚠️ הסבר זה הוא לעיון בלבד. אינו מהווה ייעוץ רפואי. אנא היוועץ בנותן השירות הרפואי שלך.",
    "vi": "⚠️ Giải thích này chỉ mang tính tham khảo. Không phải là tư vấn y khoa. Vui lòng tham khảo ý kiến nhà cung cấp dịch vụ y tế.",
}


# Step 3 downgrade note (single item).
# zh-TW / zh-CN / ko render "code-lookup sources" as terminology-style
# "標準化編碼來源" / "标准化编码来源" / "표준 코드 출처" (Amendment 2).
EXPLAIN_DOWNGRADE_ITEM_NOTE: Dict[str, str] = {
    "en": "(Note: This item references code-lookup sources only; full clinical interpretation should be discussed with your physician.)",
    "zh-TW": "（註：此項目僅引用標準化編碼來源；完整的臨床判讀請與您的醫師討論。）",
    "zh-CN": "（注：此项目仅引用标准化编码来源；完整的临床判读请与您的医生讨论。）",
    "ja": "（注：この項目はコード参照のみを引用しています。完全な臨床的解釈については医師にご相談ください。）",
    "ko": "（참고: 이 항목은 표준 코드 출처만 참조합니다. 완전한 임상 해석은 의사와 상담하십시오.）",
    "es": "(Nota: Este elemento solo hace referencia a fuentes de búsqueda de códigos; la interpretación clínica completa debe consultarse con su médico.)",
    "fr": "(Remarque : Cet élément ne fait référence qu'à des sources de recherche par code ; l'interprétation clinique complète doit être discutée avec votre médecin.)",
    "de": "(Hinweis: Dieser Punkt verweist nur auf Code-Nachschlagequellen; die vollständige klinische Interpretation sollte mit Ihrem Arzt besprochen werden.)",
    "it": "(Nota: Questa voce fa riferimento solo a fonti di ricerca per codice; l'interpretazione clinica completa va discussa con il tuo medico.)",
    "pt": "(Nota: Este item refere-se apenas a fontes de pesquisa por código; a interpretação clínica completa deve ser discutida com o seu médico.)",
    "th": "(หมายเหตุ: รายการนี้อ้างอิงเฉพาะแหล่งค้นหารหัสเท่านั้น การตีความทางคลินิกฉบับสมบูรณ์ควรปรึกษากับแพทย์ของคุณ)",
    "ar": "(ملاحظة: يشير هذا البند إلى مصادر بحث الرموز فقط؛ يجب مناقشة التفسير السريري الكامل مع طبيبك.)",
    "hi": "(टिप्पणी: यह आइटम केवल कोड-लुकअप स्रोतों का संदर्भ देता है; पूर्ण नैदानिक व्याख्या के लिए अपने चिकित्सक से चर्चा करें।)",
    "bn": "(নোট: এই আইটেমটি শুধুমাত্র কোড-লুকআপ উৎসসমূহকে নির্দেশ করে; সম্পূর্ণ ক্লিনিকাল ব্যাখ্যা আপনার চিকিৎসকের সাথে আলোচনা করুন।)",
    "he": "(הערה: פריט זה מתייחס למקורות חיפוש קוד בלבד; פרשנות קלינית מלאה יש לדון עם הרופא שלך.)",
    "vi": "(Lưu ý: Mục này chỉ tham chiếu các nguồn tra cứu mã; việc diễn giải lâm sàng đầy đủ cần được thảo luận với bác sĩ của bạn.)",
}


# Step 3 downgrade note (correlation card).
# zh-TW uses 「除...之外」 phrasing for natural Chinese flow (Amendment 4 default).
EXPLAIN_DOWNGRADE_CORR_NOTE: Dict[str, str] = {
    "en": "(Note: Insufficient non-code-lookup evidence for this correlation; please consult your physician.)",
    "zh-TW": "（註：此關聯除標準化編碼來源之外缺乏其他證據；請諮詢您的醫師。）",
    "zh-CN": "（注：此关联缺乏标准化编码以外的证据；请咨询您的医生。）",
    "ja": "（注：この関連性については、コード参照以外の十分な根拠が得られませんでした。医師にご相談ください。）",
    "ko": "（참고: 이 연관성에 대한 표준 코드 출처 외 근거가 충분하지 않습니다. 의사와 상담하십시오.）",
    "es": "(Nota: Pruebas insuficientes fuera de las fuentes de búsqueda de códigos para esta correlación; consulte a su médico.)",
    "fr": "(Remarque : Preuves insuffisantes en dehors des sources de recherche par code pour cette corrélation ; veuillez consulter votre médecin.)",
    "de": "(Hinweis: Unzureichende Belege außerhalb von Code-Nachschlagequellen für diese Korrelation; bitte konsultieren Sie Ihren Arzt.)",
    "it": "(Nota: Prove insufficienti al di fuori delle fonti di ricerca per codice per questa correlazione; consulta il tuo medico.)",
    "pt": "(Nota: Evidências insuficientes fora das fontes de pesquisa por código para esta correlação; consulte o seu médico.)",
    "th": "(หมายเหตุ: หลักฐานนอกเหนือจากแหล่งค้นหารหัสไม่เพียงพอสำหรับความสัมพันธ์นี้ กรุณาปรึกษาแพทย์ของคุณ)",
    "ar": "(ملاحظة: لا توجد أدلة كافية خارج مصادر بحث الرموز لهذا الارتباط؛ يُرجى استشارة طبيبك.)",
    "hi": "(टिप्पणी: इस सहसंबंध के लिए कोड-लुकअप के अलावा पर्याप्त प्रमाण नहीं हैं; कृपया अपने चिकित्सक से परामर्श करें।)",
    "bn": "(নোট: এই সম্পর্কের জন্য কোড-লুকআপের বাইরে পর্যাপ্ত প্রমাণ নেই; অনুগ্রহ করে আপনার চিকিৎসকের সাথে পরামর্শ করুন।)",
    "he": "(הערה: אין מספיק ראיות מחוץ למקורות חיפוש קוד עבור קישור זה; אנא היוועץ ברופא שלך.)",
    "vi": "(Lưu ý: Không đủ bằng chứng ngoài các nguồn tra cứu mã cho mối tương quan này; vui lòng tham khảo ý kiến bác sĩ của bạn.)",
}


def get_disclaimer(lang: str) -> str:
    """Return the localized disclaimer; fallback to English if lang missing."""
    return EXPLAIN_DISCLAIMERS.get(lang) or EXPLAIN_DISCLAIMERS["en"]


def get_downgrade_item_note(lang: str) -> str:
    """Localized parenthetical for items downgraded by Step 3 LOINC scope guard."""
    return EXPLAIN_DOWNGRADE_ITEM_NOTE.get(lang) or EXPLAIN_DOWNGRADE_ITEM_NOTE["en"]


def get_downgrade_corr_note(lang: str) -> str:
    """Localized parenthetical for correlations downgraded by Step 3 LOINC scope guard."""
    return EXPLAIN_DOWNGRADE_CORR_NOTE.get(lang) or EXPLAIN_DOWNGRADE_CORR_NOTE["en"]
