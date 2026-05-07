"""Server-side localized strings for Verify pipeline.

Mirrors api/i18n/explain_strings.py shape. Verify previously relied on
the schema-level hardcoded English default in api/models/schemas.py
(VerifyResponse.disclaimer), which was never overridden by the handler
— so zh-TW (and every other locale) saw English. This file gives the
handler a 16-language source it can call from the resolved
response_language.

Copy ported verbatim from pages/research.tsx DISCLAIMERS (lines 30-47):
that map has been shipped and reviewed in production for the Research
feature, and Verify's intended wording is functionally identical
("for reference, verify with clinical guidelines"). Reusing the same
strings keeps register consistent across features without introducing
unreviewed translations.

16 languages: en, zh-TW, zh-CN, ja, ko, es, fr, de, it, pt, th, ar, hi, bn, he, vi.
"""

from typing import Dict


VERIFY_DISCLAIMERS: Dict[str, str] = {
    "en": "⚠️ For informational purposes only. Always verify with clinical guidelines and consult a qualified professional.",
    "zh-TW": "⚠️ 本資訊僅供參考，請依據臨床指引並諮詢合格醫療專業人員。",
    "zh-CN": "⚠️ 本信息仅供参考，请依据临床指南并咨询合格医疗专业人员。",
    "ja": "⚠️ 本情報は参考用です。臨床ガイドラインを確認し、資格のある医療専門家にご相談ください。",
    "ko": "⚠️ 본 정보는 참고용입니다. 임상 지침을 확인하고 자격을 갖춘 의료 전문가와 상담하십시오.",
    "es": "⚠️ Solo con fines informativos. Verifique con las guías clínicas y consulte a un profesional cualificado.",
    "fr": "⚠️ À titre informatif uniquement. Vérifiez avec les directives cliniques et consultez un professionnel qualifié.",
    "de": "⚠️ Nur zu Informationszwecken. Überprüfen Sie die klinischen Leitlinien und konsultieren Sie einen qualifizierten Fachmann.",
    "it": "⚠️ Solo a scopo informativo. Verificare con le linee guida cliniche e consultare un professionista qualificato.",
    "pt": "⚠️ Apenas para fins informativos. Verifique com as diretrizes clínicas e consulte um profissional qualificado.",
    "th": "⚠️ ข้อมูลนี้ใช้เพื่อการอ้างอิงเท่านั้น กรุณาตรวจสอบตามแนวทางปฏิบัติทางคลินิกและปรึกษาผู้เชี่ยวชาญที่มีคุณสมบัติ",
    "ar": "⚠️ هذه المعلومات للأغراض المرجعية فقط. يرجى التحقق من الإرشادات السريرية واستشارة متخصص مؤهل.",
    "hi": "⚠️ यह जानकारी केवल संदर्भ उद्देश्यों के लिए है। कृपया नैदानिक दिशानिर्देशों से सत्यापित करें और किसी योग्य पेशेवर से परामर्श करें।",
    "bn": "⚠️ এই তথ্য শুধুমাত্র তথ্যসূত্র উদ্দেশ্যে। অনুগ্রহ করে ক্লিনিক্যাল নির্দেশিকা যাচাই করুন এবং একজন যোগ্য পেশাদারের সাথে পরামর্শ করুন।",
    "he": "⚠️ מידע זה מיועד לצורכי עיון בלבד. אנא אמתו מול הנחיות קליניות והתייעצו עם איש מקצוע מוסמך.",
    "vi": "⚠️ Thông tin này chỉ mang tính chất tham khảo. Vui lòng kiểm tra theo hướng dẫn lâm sàng và tham khảo ý kiến chuyên gia có trình độ.",
}


def get_verify_disclaimer(lang: str) -> str:
    """Return the localized Verify disclaimer; fall back to English if
    `lang` isn't one of the 16 first-class locales."""
    return VERIFY_DISCLAIMERS.get(lang) or VERIFY_DISCLAIMERS["en"]
