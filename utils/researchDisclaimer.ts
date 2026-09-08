// Research disclaimer line — ONE source for BOTH surfaces that redisplay a Research
// answer (HISTORY HONESTY car segment 4a, 2026-09-08; Rule 12 spirit: one source, two
// consumers):
//   * pages/research.tsx keys it by `detectedLang` = the SSE `language` event, which
//     carries the UI-RESOLVED response language (api/server.py `_resolve_response_language`
//     — Research does not detect the answer language; the event name predates that change).
//   * pages/history.tsx keys it by the UI `lang` — research_v1 rows store no language, and
//     the UI lang is the same key /research used at answer time unless the user has since
//     switched UI language (then the caption language differs from the stored answer's;
//     it is still the disclaimer).
// The 16 values were moved out of pages/research.tsx BYTE-IDENTICAL (the page-local map
// they replace was never an i18n-ui key — kept as a map to avoid a 16-row i18n churn).
// The ⚠️ glyph is part of each value; render sites must not prepend another (the Verify
// double-⚠️ of 2026-09-02 is the precedent). Rule 10: disclaimers are frontend-rendered.
// Pinned by tests/history_research_disclaimer_guard.mjs.

export const RESEARCH_DISCLAIMERS: Record<string, string> = {
    'en': '\u26A0\uFE0F For informational purposes only. Always verify with clinical guidelines and consult a qualified professional.',
    'zh-TW': '\u26A0\uFE0F 本資訊僅供參考，請依據臨床指引並諮詢合格醫療專業人員。',
    'zh-CN': '\u26A0\uFE0F 本信息仅供参考，请依据临床指南并咨询合格医疗专业人员。',
    'ja': '\u26A0\uFE0F 本情報は参考用です。臨床ガイドラインを確認し、資格のある医療専門家にご相談ください。',
    'ko': '\u26A0\uFE0F 본 정보는 참고용입니다. 임상 지침을 확인하고 자격을 갖춘 의료 전문가와 상담하십시오.',
    'es': '\u26A0\uFE0F Solo con fines informativos. Verifique con las gu\u00EDas cl\u00EDnicas y consulte a un profesional cualificado.',
    'fr': '\u26A0\uFE0F \u00C0 titre informatif uniquement. V\u00E9rifiez avec les directives cliniques et consultez un professionnel qualifi\u00E9.',
    'de': '\u26A0\uFE0F Nur zu Informationszwecken. \u00DCberpr\u00FCfen Sie die klinischen Leitlinien und konsultieren Sie einen qualifizierten Fachmann.',
    'it': '\u26A0\uFE0F Solo a scopo informativo. Verificare con le linee guida cliniche e consultare un professionista qualificato.',
    'pt': '\u26A0\uFE0F Apenas para fins informativos. Verifique com as diretrizes cl\u00EDnicas e consulte um profissional qualificado.',
    'th': '\u26A0\uFE0F ข้อมูลนี้ใช้เพื่อการอ้างอิงเท่านั้น กรุณาตรวจสอบตามแนวทางปฏิบัติทางคลินิกและปรึกษาผู้เชี่ยวชาญที่มีคุณสมบัติ',
    'ar': '\u26A0\uFE0F هذه المعلومات للأغراض المرجعية فقط. يرجى التحقق من الإرشادات السريرية واستشارة متخصص مؤهل.',
    'hi': '\u26A0\uFE0F यह जानकारी केवल संदर्भ उद्देश्यों के लिए है। कृपया नैदानिक दिशानिर्देशों से सत्यापित करें और किसी योग्य पेशेवर से परामर्श करें।',
    'bn': '\u26A0\uFE0F এই তথ্য শুধুমাত্র তথ্যসূত্র উদ্দেশ্যে। অনুগ্রহ করে ক্লিনিক্যাল নির্দেশিকা যাচাই করুন এবং একজন যোগ্য পেশাদারের সাথে পরামর্শ করুন।',
    'he': '\u26A0\uFE0F מידע זה מיועד לצורכי עיון בלבד. אנא אמתו מול הנחיות קליניות והתייעצו עם איש מקצוע מוסמך.',
    'vi': '\u26A0\uFE0F Thông tin này chỉ mang tính chất tham khảo. Vui lòng kiểm tra theo hướng dẫn lâm sàng và tham khảo ý kiến chuyên gia có trình độ.',
};

/** The disclaimer for `lang`, falling back to English for any unknown or empty key. */
export function getResearchDisclaimer(lang: string): string {
    return RESEARCH_DISCLAIMERS[lang] || RESEARCH_DISCLAIMERS['en'];
}
