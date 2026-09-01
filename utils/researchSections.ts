// Research answer section parsing — extracted VERBATIM from pages/research.tsx
// (HISTORY car segment 1) so /history renders stored research answers through the
// SAME parser the live page uses. CLAUDE.md Rule 12: api/rag/generator.py is the
// source of truth for the two-`## `-section format; this parser (and its Python
// mirror, api/services/share_renderer.py::parse_research_sections) follow it,
// never the reverse.

const DISCLAIMER_STRIP_RE = /⚠️\s*(This information|For informational purposes|For reference only|本資訊|本信息|本情報|본 정보|Solo con fines|À titre|Nur zu|Solo a scopo|Apenas para|ข้อมูลนี้|هذه المعلومات|यह जानकारी|এই তথ্য|מידע זה|Thông tin này|Please consult|僅供參考|仅供参考).*$/gm;

export function stripLlmDisclaimer(text: string): string {
    return text.replace(DISCLAIMER_STRIP_RE, '').trim();
}

export interface ParsedSection {
    title: string;
    content: string;
}

// Language-agnostic header parsing. Matches any "## <header>" line and sanitizes
// the title — works whether the LLM emits the clean English form (## Summary —
// English) or the bracketed non-English form (## [臨床注意事項] / ## [臨床注意事項 — 繁體中文]).
// (Evidence-emoji extraction was removed with the indicator redesign; sanitizeTitle
// keeps a defensive emoji-strip in case a model still emits one.)
export function parseResearchSections(text: string): ParsedSection[] | null {
    const headerRegex = /^##\s+(.+?)\s*$/gm;
    const matches = [...text.matchAll(headerRegex)];
    if (matches.length === 0) return null;

    const sanitizeTitle = (raw: string): string =>
        raw
            .replace(/[🟢🟡🔴]/gu, '')            // strip evidence emoji (any position)
            .replace(/\s+[—–]\s*.+$/u, '')        // strip " — Lang" suffix (spaced em/en-dash only)
            .replace(/^[\[【［\s]+/u, '')          // strip leading brackets [ 【 ［
            .replace(/[\]】］\s]+$/u, '')          // strip trailing brackets ] 】 ］
            .trim();

    const sections: ParsedSection[] = [];
    for (let i = 0; i < matches.length; i++) {
        const match = matches[i];
        const header = match[1];
        const title = sanitizeTitle(header);
        const start = match.index! + match[0].length;
        const end = i + 1 < matches.length ? matches[i + 1].index! : text.length;
        // Remove leading --- separator
        const content = text.slice(start, end).replace(/^\s*---\s*/g, '').trim();
        if (content) {
            sections.push({ title, content });
        }
    }
    return sections.length > 0 ? sections : null;
}
