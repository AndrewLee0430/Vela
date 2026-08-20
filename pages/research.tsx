"use client"

import { useState, FormEvent, useRef, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/router';
import { useAuth, useUser } from '@clerk/nextjs';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import rehypeRaw from 'rehype-raw';
import Head from 'next/head';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { FatalError, makeOnOpen, sseOnError } from '../utils/sse';
import CitationPanel, { Citation } from '../components/CitationPanel';
import { detectSourceType, sourceLabelFor, resolvedSourceLabel, sourceCountTooltip } from '../utils/sourceLabels';
import FeedbackBar from '../components/FeedbackBar';
import { useShareContext } from '../contexts/ShareContext';
import UpgradeModal from '../components/UpgradeModal';
import Toast from '../components/Toast';
import PHIWarning from '../components/PHIWarning';
import PageShell from '../components/PageShell';
import ProFeatureOverlay from '../components/ProFeatureOverlay';
import ResearchSection from '../components/ResearchSection';
import LocaleHintPanel from '../components/LocaleHintPanel';
import { detectLocaleCategories } from '../utils/localeHint';
import { resolveCountry, type CountryCode, type LocaleSetting, type ResolutionLevel } from '../utils/country';
import { readRaw } from '../utils/userContext';
import AnonymousUpgradeCTA from '../components/AnonymousUpgradeCTA';
import { exportResearchPdf } from '../utils/exportPdf';
import { setQueryId, getAnonFingerprint, track } from '../utils/analytics';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';
import { getExtra } from '../utils/i18n-extra';

const DISCLAIMERS: Record<string, string> = {
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

const DISCLAIMER_STRIP_RE = /⚠️\s*(This information|For informational purposes|For reference only|本資訊|本信息|本情報|본 정보|Solo con fines|À titre|Nur zu|Solo a scopo|Apenas para|ข้อมูลนี้|هذه المعلومات|यह जानकारी|এই তথ্য|מידע זה|Thông tin này|Please consult|僅供參考|仅供参考).*$/gm;

function stripLlmDisclaimer(text: string): string {
    return text.replace(DISCLAIMER_STRIP_RE, '').trim();
}

interface ParsedSection {
    title: string;
    content: string;
}

// Language-agnostic header parsing. Matches any "## <header>" line and sanitizes
// the title — works whether the LLM emits the clean English form (## Summary —
// English) or the bracketed non-English form (## [臨床注意事項] / ## [臨床注意事項 — 繁體中文]).
// (Evidence-emoji extraction was removed with the indicator redesign; sanitizeTitle
// keeps a defensive emoji-strip in case a model still emits one.)
function parseResearchSections(text: string): ParsedSection[] | null {
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

// Fixed multilingual sample queries — showcases "Ask in any language" feature.
// Intentionally NOT translated: the mix of languages itself is the message.
const defaultSuggestions = [
    "小孩發燒幾度需要看醫生？",
    "What are the common side effects of Metformin?",
    "ワルファリンの副作用は何ですか？",
    "老人血壓藥可以跟鈣片一起吃嗎？",
    "¿Es seguro usar antibióticos durante el embarazo?",
    "DOACs vs Warfarin — key differences?",
    "高齢者の骨粗しょう症に最も効果的な治療法は？",
    "糖尿病老人的降血糖藥物選擇？",
    "ما هي التفاعلات الدوائية للميتفورمين؟",
    "심부전에서 베타차단제는 언제 사용하나요?",
];

// Per-answer trust signal (design X): provenance derived from REAL retrieved-source
// counts, not a model self-label. Renders only when there are citations; the
// no-literature floor is the FallbackBanner (mutually exclusive — see render).
// Source names come from the shared sourceLabels map so the line, the reference
// cards, and the panel sub-header never drift (local + fda merge into one "FDA").
function ProvenanceLine({ citations }: { citations: Citation[] }) {
    const { lang } = useLang();
    const ui = getUI(lang);
    const counts = new Map<string, number>();
    for (const c of citations) {
        const label = resolvedSourceLabel(sourceLabelFor(c), ui);
        counts.set(label, (counts.get(label) || 0) + 1);
    }
    return (
        <div className="mb-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs" style={{ color: 'rgb(var(--color-text) / 0.45)' }}>
            <span>{ui.provenanceSourced.replace('{count}', String(citations.length))}</span>
            {[...counts.entries()].map(([label, n]) => (
                <span key={label} className="relative group">
                    <span className="px-2 py-0.5 rounded-full cursor-help inline-block" style={{ background: 'rgb(var(--color-text) / 0.08)' }}>
                        {label} {n}
                    </span>
                    <span className="absolute left-0 top-full mt-2 w-56 bg-white rounded-lg shadow-lg px-3 py-2 z-50 hidden group-hover:block text-xs leading-relaxed text-gray-600">
                        {sourceCountTooltip(ui.sourceCountTip, label, n)}
                    </span>
                </span>
            ))}
        </div>
    );
}

function FallbackBanner() {
    const { lang } = useLang();
    const ui = getUI(lang);
    return (
        <div className="mb-4 flex items-start gap-3 p-4 rounded-lg" style={{ background: "rgb(var(--color-warning) / 0.12)", border: "1px solid rgb(var(--color-warning) / 0.3)" }}>
            <span className="text-sm mt-0.5 font-bold" style={{ color: "rgb(var(--color-warning))" }}>⚠</span>
            <div>
                <p className="text-sm font-semibold" style={{ color: "rgb(var(--color-warning))" }}>
                    {ui.noLiteratureFound}
                </p>
                <p className="text-sm mt-0.5" style={{ color: "rgb(var(--color-warning) / 0.8)" }}>
                    {ui.fallbackBasis}
                </p>
            </div>
        </div>
    );
}

function ResearchForm() {
    const router = useRouter();
    const { getToken } = useAuth();
    const { isSignedIn } = useUser();
    const { lang } = useLang();
    const ui = getUI(lang);
    const extra = getExtra(lang);

    const [question, setQuestion]   = useState('');
    const [answer, setAnswer]       = useState('');
    const [citations, setCitations] = useState<Citation[]>([]);
    const [loading, setLoading]     = useState(false);
    const [queryTime, setQueryTime] = useState<number | null>(null);
    const [error, setError]         = useState<string>('');
    const [isFallback, setIsFallback] = useState(false);
    const [statusMsg, setStatusMsg] = useState<string>('');
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    const [showDailyCapToast, setShowDailyCapToast] = useState(false);
    const [anonNoticeMsg, setAnonNoticeMsg] = useState<string | null>(null);
    const [anonQuotaCta, setAnonQuotaCta] = useState<{ used: number; limit: number } | null>(null);
    const [showThirdQueryCta, setShowThirdQueryCta] = useState(false);
    const [phiError, setPhiError] = useState<{detail: string; suggestion: string} | null>(null);
    const [detectedLang, setDetectedLang] = useState<string>('en');
    const [localQueryId, setLocalQueryId] = useState<string | null>(null);
    const { setShareData, clearShareData } = useShareContext();

    // 在地差異提示 (Probe 1) — gated OFF for real users by default. Enabled via build-time
    // NEXT_PUBLIC_LOCALE_HINT_ENABLED='true', or per-browser via localStorage preview hatch
    // (read in an effect to avoid an SSR/hydration mismatch on the static-exported page).
    const [localeHintPreview, setLocaleHintPreview] = useState(false);
    useEffect(() => {
        if (typeof window !== 'undefined' && localStorage.getItem('vela_locale_hint_preview') === '1') {
            setLocaleHintPreview(true);
        }
    }, []);
    const localeHintEnabled = process.env.NEXT_PUBLIC_LOCALE_HINT_ENABLED === 'true' || localeHintPreview;
    // Recompute against the COMPLETE final answer once streaming finishes. useMemo keyed on
    // [answer, loading, …] guarantees a recompute when `answer` finalizes (gate requires !loading).
    // Suppressed on no-retrieval/fallback answers (isFallback) — on those the answer is ungrounded
    // ("基於一般醫學知識"), and the panel would lend it false local-authority credibility (stopgap;
    // the deeper generator fix is a separate task).
    // RULE 1 — two independent axes: the ANSWER LANGUAGE (en / zh-TW in b1) picks the keyword list
    // (does the panel fire?), the resolved COUNTRY picks the authorities (Tier-1 or Tier-2 fallback).
    const localeHint = useMemo(() => {
        const none = { categories: [] as ReturnType<typeof detectLocaleCategories>, country: null as CountryCode | null, level: 'none' as ResolutionLevel };
        if (!(localeHintEnabled && (lang === 'zh-TW' || lang === 'en') && !loading && !isFallback && answer)) return none;
        const categories = detectLocaleCategories(question + '\n' + answer, lang);
        if (!categories.length) return none;
        // COUNTRY is resolved only when a keyword actually matched. Timezone (L3) is browser-only.
        const raw = readRaw();
        const timeZone = typeof window !== 'undefined' ? Intl.DateTimeFormat().resolvedOptions().timeZone : null;
        const { country, level } = resolveCountry({
            settingsLocale: (raw.locale as LocaleSetting | undefined) ?? null,
            workLanguage: raw.work_language ?? null,
            timeZone,
            uiLang: lang,
        });
        return { categories, country, level };
    }, [localeHintEnabled, lang, loading, isFallback, question, answer]);

    // ADR-007 (d) authority-row suppression — the answer's normalized citation source_types, for
    // LocaleHintPanel's filterUngroundedAuthorities. WIRING CHOICE (closes the stale-deps hazard
    // rather than inheriting it): the trigger memo above deliberately does NOT read `citations`,
    // so its dep array stays honest and untouched; this is its own memo keyed on [citations], and
    // the filter runs INSIDE the panel from this prop — every setCitations re-renders the panel
    // with the fresh set (the SSE `citations` event precedes `done`, and even a late citation
    // update would still re-render the filter). No manually-synchronized dep list involved.
    const citationSourceTypes = useMemo(
        () => new Set<string>(citations.map(c => detectSourceType(c))),
        [citations],
    );

    const [plan, setPlan] = useState<'free' | 'pro'>(() => {
        if (typeof window === 'undefined') return 'free';
        try {
            const raw = localStorage.getItem('vela_plan_cache');
            if (raw) {
                const { plan: p, ts } = JSON.parse(raw);
                if (Date.now() - ts < 5 * 60 * 1000) return p;
            }
        } catch {}
        return 'free';
    });

    useEffect(() => {
        if (!isSignedIn) return; // L0 anonymous: no plan concept
        (async () => {
            try {
                const token = await getToken({ skipCache: true });
                if (!token) return;
                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/user/status`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (res.ok) {
                    const data = await res.json();
                    setPlan(data.plan_type === 'pro' ? 'pro' : 'free');
                }
            } catch {}
        })();
    }, [getToken, isSignedIn]);

    const answerRef    = useRef<HTMLDivElement>(null);
    const inputRef     = useRef<HTMLInputElement>(null);
    const isRunningRef = useRef(false);
    const heroQueryConsumedRef = useRef(false);
    const [selectedSuggestion, setSelectedSuggestion] = useState<string | null>(null);

    // Follow the stream while it is running.
    useEffect(() => {
        if (answerRef.current && answer) {
            answerRef.current.scrollTop = answerRef.current.scrollHeight;
        }
    }, [answer]);

    // B4.5 A — …then LAND ON THE SUMMARY when generation actually finishes.
    //
    // The defect: the effect above pins the pane to the bottom on every token,
    // so when the last chunk arrives the user is parked at the END of a long
    // answer and has to scroll UP to find the Summary — the payoff of the whole
    // query. Founder-reported on /research.
    //
    // The trigger is the `loading` true→false EDGE, not a timeout and not a gap
    // in tokens. `loading` goes false in exactly two places, both real end-of-
    // stream signals: the SSE `done` event and `onclose()`. A premature scroll
    // that later tokens undo would be worse than the current behaviour, so the
    // edge — not `loading === false` — is what fires this.
    //
    // ORDERING: `loading` is also what swaps the raw stream for the composed
    // render (ProvenanceLine + parseResearchSections → <ResearchSection> cards,
    // all gated on `!loading` below). Because both are driven by the same state
    // change, this effect runs AFTER React has committed that new DOM, so the
    // scroll lands on the composed Summary rather than being invalidated by it.
    // Scrolling to 0 is also height-independent, so the re-render changing the
    // pane's scrollHeight cannot affect where we end up.
    //
    // NOT FIGHTING THE USER: there is no user scroll position to preserve here.
    // The follow effect above overwrites scrollTop on EVERY chunk, so a manual
    // scroll during generation is already destroyed within one token — the
    // "user scrolled away deliberately" state cannot survive to completion in
    // the first place. Given that, snapping to the top is strictly better than
    // being left at the bottom. (Making the follow yield to a manual scroll is
    // a separate, larger change and is not in this baton.)
    const wasLoadingRef = useRef(false);
    useEffect(() => {
        const wasLoading = wasLoadingRef.current;
        wasLoadingRef.current = loading;
        if (!wasLoading || loading) return;      // only the true→false edge
        const el = answerRef.current;
        if (!el || !answer) return;              // nothing to land on
        // Reduced motion gets an instant jump; everyone else gets the smooth
        // travel, which also makes it legible that the pane MOVED.
        const reduce = typeof window !== 'undefined'
            && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        el.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
    }, [loading, answer]);

    // PRD § 4.5 UX polish 2/3 — Navbar Share button is driven by
    // ShareContext. Populate when the answer is fully ready (not loading,
    // no error, query_id received from the SSE stream); clear while
    // streaming so the button hides; clear on unmount so nav-away
    // resets the Navbar state.
    useEffect(() => {
        if (loading) {
            clearShareData();
            return;
        }
        if (!error && answer && question && localQueryId) {
            setShareData({
                queryId: localQueryId,
                queryText: question,
                answerText: answer,
                citations,
                feature: 'research',
            });
        }
    }, [loading, error, answer, question, localQueryId, citations, setShareData, clearShareData]);

    useEffect(() => {
        return () => clearShareData();
    }, [clearShareData]);

    const handleReset = () => {
        setQuestion(''); setAnswer(''); setCitations([]);
        setQueryTime(null); setError(''); setIsFallback(false); setStatusMsg(''); setPhiError(null);
        setSelectedSuggestion(null);
        setQueryId(null);
        setLocalQueryId(null);
    };

    const maybeTriggerThirdQueryCta = useCallback(() => {
        if (typeof window === 'undefined') return;
        try {
            if (sessionStorage.getItem('vela_anon_cta_third_shown') === '1') return;
            const raw = sessionStorage.getItem('vela_anon_query_count') ?? '0';
            const next = (parseInt(raw, 10) || 0) + 1;
            sessionStorage.setItem('vela_anon_query_count', String(next));
            if (next === 3) {
                sessionStorage.setItem('vela_anon_cta_third_shown', '1');
                setShowThirdQueryCta(true);
            }
        } catch {}
    }, []);

    const runSearch = useCallback(async (q: string) => {
        if (!q.trim() || isRunningRef.current) return;
        isRunningRef.current = true;

        const t0 = Date.now();
        // Local accumulators mirror state for telemetry — runSearch is useCallback'd
        // with deps that don't include answer/citations/isFallback/detectedLang, so
        // direct reads in case 'done' would be stale. Locals are scoped to this
        // single query lifecycle, no staleness risk.
        let localAnswer = '';
        let localCitations: Citation[] = [];
        let localIsFallback = false;
        let localDetectedLang: string | null = null;
        // Telemetry now reflects REAL provenance, not the removed emoji self-label:
        // section_count (layout) + per-source_type counts from the citations array.
        const computeResearchTelemetry = (markdown: string, cites: Citation[]) => {
            const sections = parseResearchSections(markdown) ?? [];
            const source_distribution: Record<string, number> = {};
            for (const c of cites) {
                const key = (c.source_type || '').toString().trim().toLowerCase() || 'unknown';
                source_distribution[key] = (source_distribution[key] || 0) + 1;
            }
            return { sections_count: sections.length, source_distribution };
        };

        setAnswer(''); setCitations([]); setQueryTime(null);
        setLoading(true); setError(''); setIsFallback(false); setStatusMsg(''); setPhiError(null); setDetectedLang('en');
        setQueryId(null);
        setLocalQueryId(null);

        const controller = new AbortController();

        try {
            const headers: Record<string, string> = { 'Content-Type': 'application/json' };
            if (isSignedIn) {
                const jwt = await getToken({ skipCache: true });
                if (!jwt) {
                    setError(ui.authRequired);
                    setLoading(false);
                    isRunningRef.current = false;
                    return;
                }
                headers['Authorization'] = `Bearer ${jwt}`;
            } else {
                const fp = getAnonFingerprint();
                if (!fp) {
                    setError('Session unavailable. Please refresh and try again.');
                    setLoading(false);
                    isRunningRef.current = false;
                    return;
                }
                headers['X-Anon-Fingerprint'] = fp;
                track('anonymous_query_submitted', { feature: 'research', anon_id: fp });
            }

            await fetchEventSource(`${process.env.NEXT_PUBLIC_API_URL}/api/research`, {
                signal: controller.signal,
                method: 'POST',
                headers,
                body: JSON.stringify({ question: q, max_results: 5, response_language: lang }),
                openWhenHidden: true,

                onopen: makeOnOpen({
                    onPhiBlocked: () => setPhiError({ detail: ui.phiDetail, suggestion: ui.phiSuggestion }),
                    onLimitReached: () => setShowUpgradeModal(true),
                    onSignupRequired: () => setError('Sign up required to continue. Please create a free account.'),
                    onAnonymousQuotaExceeded: (_msg, details) => {
                        const used = details?.used ?? 0;
                        const limit = details?.limit ?? 0;
                        track('anonymous_quota_hit', { feature: 'research', attempts: used });
                        setAnonQuotaCta({ used, limit });
                    },
                    onBudgetExceeded: () => setAnonNoticeMsg('Service temporarily at capacity. Please try again later.'),
                    onInvalidFingerprint: () => setError('Session unavailable. Please refresh and try again.'),
                }),

                onmessage(ev) {
                    try {
                        const data = JSON.parse(ev.data);
                        if (data.type === 'query_id') {
                            if (data.query_id) {
                                setQueryId(data.query_id);
                                setLocalQueryId(data.query_id);
                            }
                        }
                        else if (data.type === 'status') {
                            const statusMap: Record<string, string> = {
                                // Multi-step honest status (each backed by a real backend stage)
                                'Searching the literature': ui.statusStepSearch,
                                'Checking & ranking sources': ui.statusStepRank,
                                'Generating answer': ui.statusStepGenerate,
                                // Legacy strings (pre-multi-step) — kept for graceful mapping
                                'Searching medical literature...': ui.statusSearching,
                                'Analyzing documents...': ui.statusAnalyzingDocs,
                            };
                            setStatusMsg(statusMap[data.content] || data.content);
                        }
                        else if (data.type === 'language') {
                            localDetectedLang = typeof data.lang === 'string' ? data.lang : null;
                            setDetectedLang(data.lang || 'en');
                        }
                        else if (data.type === 'answer')   {
                            setStatusMsg('');
                            const chunk = typeof data.content === 'string' ? data.content : '';
                            localAnswer += chunk;
                            setAnswer(prev => prev + chunk);
                        }
                        else if (data.type === 'fallback') { localIsFallback = true; setIsFallback(true); }
                        else if (data.type === 'citations') {
                            const safeCitations = Array.isArray(data.content) ? data.content : [];
                            localCitations = safeCitations;
                            setCitations(safeCitations);
                        }
                        else if (data.type === 'error') {
                            // Note: Research uses .error-first; Explain (§ 2.7 Step 2C) uses .code-first.
                            // Phase 1A polish will harmonize backend error response shape.
                            const code = data.error ?? data.code;
                            if (code === 'limit_reached') {
                                setShowUpgradeModal(true);
                            } else if (code === 'daily_cap_reached') {
                                setShowDailyCapToast(true);
                            } else {
                                setError(data.content || code || 'An error occurred.');
                                track('research_failed', {
                                    error_code: code ?? 'unknown',
                                    elapsed_ms: Date.now() - t0,
                                });
                            }
                        }
                        else if (data.type === 'done')     {
                            setLoading(false);
                            const queryTimeMs = typeof data.query_time_ms === 'number' ? data.query_time_ms : null;
                            if (queryTimeMs !== null) setQueryTime(queryTimeMs);
                            if (!isSignedIn) maybeTriggerThirdQueryCta();
                            const stripped = stripLlmDisclaimer(localAnswer);
                            const { sections_count, source_distribution } = computeResearchTelemetry(stripped, localCitations);
                            track('research_completed', {
                                citation_count: localCitations.length,
                                section_count: sections_count,
                                source_distribution,
                                used_fallback: localIsFallback,
                                input_language: localDetectedLang,
                                elapsed_ms: Date.now() - t0,
                                backend_query_time_ms: queryTimeMs,
                            });
                        }
                    } catch {}
                },

                onclose() { setLoading(false); },

                onerror: sseOnError,
            });

        } catch (err: any) {
            controller.abort();
            setLoading(false);
            const code = err?.code as string | undefined;
            const sseMsg: Record<string, string> = {
                session_expired: ui.sseSessionExpired,
                too_many_requests: ui.sseTooManyRequests,
                server_error: ui.sseServerError,
                connection_lost: ui.sseConnectionLost,
            };
            setError(code && sseMsg[code] ? sseMsg[code] : (err instanceof Error ? err.message : ui.sseConnectionLost));
        } finally {
            isRunningRef.current = false;
        }
    }, [getToken, isSignedIn, ui, maybeTriggerThirdQueryCta]);

    useEffect(() => {
        if (!router.isReady) return;
        if (heroQueryConsumedRef.current) return;
        const raw = router.query.q;
        const q = Array.isArray(raw) ? raw[0] : raw;
        if (typeof q !== 'string') return;
        const trimmed = q.trim();
        if (!trimmed) return;
        heroQueryConsumedRef.current = true;
        setQuestion(trimmed);
        void runSearch(trimmed);
        router.replace('/research', undefined, { shallow: true });
    }, [router, runSearch]);

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        await runSearch(question);
    }

    return (
        <div className="flex flex-col gap-4 max-w-5xl mx-auto">
            {/* Title row */}
            <div className="flex justify-between items-start">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight" style={{ color: "rgb(var(--color-text))" }}>{ui.researchTitle}</h1>
                    <p className="text-sm mt-1" style={{ color: "rgb(var(--color-text) / 0.5)" }}>{ui.researchSubtitle}</p>
                </div>
                {(answer || question) && (
                    <button onClick={handleReset} className="text-sm font-medium px-3 py-1 rounded-lg transition-all mt-1"
                        style={{ background: 'transparent', border: '1px solid rgb(var(--color-text) / 0.3)', color: 'rgb(var(--color-text) / 0.7)' }}
                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgb(var(--color-text) / 0.1)'; }}
                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}>
                        {ui.newBtn}
                    </button>
                )}
            </div>

            {/* Info box */}
            <div className="rounded-xl p-4 text-sm bg-text/5 border border-text/12">
                <p className="text-text/85">
                    <span className="font-semibold">{ui.researchInfoBox}</span>
                </p>
            </div>

            {/* Main layout */}
            <div className="flex flex-col lg:flex-row gap-6">
                {/* Left: answer area */}
                <div className="flex-1 flex flex-col">
                    <div className="rounded-xl p-6 flex flex-col" style={{ background: "rgb(var(--color-text) / 0.06)", border: "1px solid rgb(var(--color-text) / 0.1)" }}>

                        {phiError && !loading && (
                            <PHIWarning detail={phiError.detail} suggestion={phiError.suggestion} onDismiss={() => setPhiError(null)} />
                        )}

                        {error && !loading && (
                            <div className="mb-4 p-3 rounded-lg border text-sm" style={{ background: "rgb(var(--color-danger) / 0.1)", borderColor: "rgb(var(--color-danger) / 0.3)", color: "rgb(var(--color-danger-soft) / 0.9)" }}>
                                {error}
                            </div>
                        )}

                        <div ref={answerRef} className="overflow-y-auto mb-4 min-h-[300px] max-h-[500px]">
                            {!answer && !loading && (
                                <div className="text-center py-12">
                                    <div className="space-y-3">
                                        <p className="text-xs uppercase tracking-widest" style={{ color: "rgb(var(--color-text) / 0.35)" }}>{ui.tryThese}</p>
                                        <p className="text-xs mb-2" style={{ color: "rgb(var(--color-text) / 0.5)" }}>
                                            {ui.askOneQuestion}
                                        </p>
                                        <div className="flex flex-wrap justify-center gap-2">
                                            {defaultSuggestions.map((s) => {
                                                const isSelected = selectedSuggestion === s;
                                                const hasSel = selectedSuggestion !== null;
                                                return (
                                                    <button
                                                        key={s}
                                                        onClick={() => {
                                                            setQuestion(s);
                                                            setSelectedSuggestion(s);
                                                            setTimeout(() => inputRef.current?.focus(), 0);
                                                        }}
                                                        disabled={loading}
                                                        className="px-3 py-1.5 text-xs rounded-full disabled:opacity-50 transition-all duration-200"
                                                        style={{
                                                            background: isSelected ? "rgb(var(--color-brand) / 0.15)" : "rgb(var(--color-text) / 0.06)",
                                                            border: `1px solid ${isSelected ? "rgb(var(--color-brand))" : "rgb(var(--color-text) / 0.15)"}`,
                                                            color: isSelected ? "rgb(var(--color-brand))" : "rgb(var(--color-text) / 0.7)",
                                                            transform: isSelected ? "scale(1.05)" : "scale(1)",
                                                            opacity: hasSel && !isSelected ? 0.5 : 1,
                                                        }}
                                                        onMouseEnter={e => {
                                                            if (!isSelected) {
                                                                (e.currentTarget as HTMLElement).style.borderColor = "rgb(var(--color-brand) / 0.6)";
                                                                (e.currentTarget as HTMLElement).style.color = "rgb(var(--color-brand))";
                                                                (e.currentTarget as HTMLElement).style.opacity = "1";
                                                            }
                                                        }}
                                                        onMouseLeave={e => {
                                                            if (!isSelected) {
                                                                (e.currentTarget as HTMLElement).style.borderColor = "rgb(var(--color-text) / 0.15)";
                                                                (e.currentTarget as HTMLElement).style.color = "rgb(var(--color-text) / 0.7)";
                                                                (e.currentTarget as HTMLElement).style.opacity = hasSel ? "0.5" : "1";
                                                            }
                                                        }}
                                                    >
                                                        {s}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {loading && !answer && statusMsg && (
                                <div className="flex items-center gap-3 py-8" style={{ color: "rgb(var(--color-text) / 0.5)" }}>
                                    <div className="w-4 h-4 border-2 rounded-full animate-spin flex-shrink-0" style={{ borderColor: "rgb(var(--color-text) / 0.2)", borderTopColor: "rgb(var(--color-brand))" }} />
                                    <span className="text-sm">{statusMsg}</span>
                                </div>
                            )}

                            {(answer || loading) && (
                                <div>
                                    {/* Single trust signal, mutually exclusive: 0 sources → FallbackBanner floor (keeps the clinical caveat); ≥1 source → ProvenanceLine. */}
                                    {!loading && (isFallback
                                        ? <FallbackBanner />
                                        : citations.length > 0 ? <ProvenanceLine citations={citations} /> : null)}
                                    {(() => {
                                        const cleanAnswer = !loading ? stripLlmDisclaimer(answer) : answer;
                                        const sections = !loading ? parseResearchSections(cleanAnswer) : null;
                                        const proseStyle = {
                                            color: "rgb(var(--color-text) / 0.85)",
                                            '--tw-prose-headings': 'rgb(var(--color-text))',
                                            '--tw-prose-bold': 'rgb(var(--color-text))',
                                            '--tw-prose-links': 'rgb(var(--color-brand))',
                                            '--tw-prose-bullets': 'rgb(var(--color-text) / 0.5)',
                                            '--tw-prose-counters': 'rgb(var(--color-text) / 0.5)',
                                            '--tw-prose-code': 'rgb(var(--color-brand))',
                                            '--tw-prose-hr': 'rgb(var(--color-text) / 0.15)',
                                        } as React.CSSProperties;

                                        if (sections && !loading) {
                                            return (
                                                <>
                                                    {sections.map((sec, i) => (
                                                        <ResearchSection key={i} title={sec.title}>
                                                            <div className="prose max-w-none prose-sm prose-headings:font-semibold prose-h2:text-base" style={proseStyle}>
                                                                <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>{sec.content}</ReactMarkdown>
                                                            </div>
                                                        </ResearchSection>
                                                    ))}
                                                    <p className="text-xs mt-3 mb-1" style={{ color: 'rgb(var(--color-text) / 0.35)' }}>
                                                        {DISCLAIMERS[detectedLang] || DISCLAIMERS['en']}
                                                    </p>
                                                </>
                                            );
                                        }

                                        return (
                                            <>
                                                <div className="prose max-w-none prose-sm prose-headings:font-semibold prose-h2:text-base" style={proseStyle}>
                                                    <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>{cleanAnswer}</ReactMarkdown>
                                                </div>
                                                {!loading && (
                                                    <p className="text-xs mt-3" style={{ color: 'rgb(var(--color-text) / 0.35)' }}>
                                                        {DISCLAIMERS[detectedLang] || DISCLAIMERS['en']}
                                                    </p>
                                                )}
                                            </>
                                        );
                                    })()}
                                    {loading && answer && (
                                        <span className="inline-block w-1.5 h-4 rounded-sm animate-pulse ml-0.5" style={{ background: 'rgb(var(--color-brand))' }} />
                                    )}
                                    {!loading && answer && !error && (
                                        <>
                                            <FeedbackBar query={question} response={answer} category="research" />
                                            <div className="mt-3 inline-block">
                                                <ProFeatureOverlay isLocked={plan !== 'pro'} featureName={extra.proFeatExport}>
                                                    <button
                                                        onClick={() => exportResearchPdf(question, answer, citations)}
                                                        className="inline-flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-lg transition-all cursor-pointer"
                                                        style={{ background: 'rgb(var(--color-text) / 0.06)', border: '1px solid rgb(var(--color-text) / 0.15)', color: 'rgb(var(--color-text) / 0.55)' }}
                                                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgb(var(--color-text) / 0.12)'; (e.currentTarget as HTMLElement).style.color = 'rgb(var(--color-text))'; }}
                                                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgb(var(--color-text) / 0.06)'; (e.currentTarget as HTMLElement).style.color = 'rgb(var(--color-text) / 0.55)'; }}
                                                    >
                                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                                                        {ui.exportCitations}
                                                    </button>
                                                </ProFeatureOverlay>
                                            </div>
                                            {showThirdQueryCta && !isSignedIn && (
                                                <AnonymousUpgradeCTA
                                                    trigger="third_query"
                                                    onDismiss={() => setShowThirdQueryCta(false)}
                                                />
                                            )}
                                        </>
                                    )}
                                </div>
                            )}
                        </div>

                        {queryTime && (
                            <p className="text-xs mb-2" style={{ color: "rgb(var(--color-text) / 0.35)" }}>
                                {ui.queryTime} {(queryTime / 1000).toFixed(2)}s
                            </p>
                        )}

                        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2">
                            <input
                                ref={inputRef}
                                type="text"
                                value={question}
                                onChange={(e) => { setQuestion(e.target.value); setSelectedSuggestion(null); }}
                                placeholder={ui.researchPlaceholder}
                                className="flex-1 px-4 py-2.5 text-sm rounded-lg focus:outline-none transition-shadow"
                                style={{ background: "rgb(var(--color-text) / 0.07)", border: "1px solid rgb(var(--color-text) / 0.15)", color: "rgb(var(--color-text))" }}
                                disabled={loading}
                            />
                            <button
                                type="submit"
                                disabled={loading || !question.trim()}
                                className="px-5 py-2.5 text-white text-sm font-medium rounded-lg transition-opacity disabled:opacity-50"
                                style={{ background: 'rgb(var(--color-brand))' }}
                            >
                                {loading ? (
                                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                ) : ui.searchBtn}
                            </button>
                        </form>

                    </div>
                </div>

                {/* Right: citations */}
                <div className="w-full lg:w-96 flex flex-col">
                    <div className="rounded-xl p-6 flex-1 overflow-hidden flex flex-col" style={{ background: "rgb(var(--color-text) / 0.06)", border: "1px solid rgb(var(--color-text) / 0.1)" }}>
                        {/* References always render in their source language (English) by design — Vela does
                            NOT translate medical literature (translation could distort clinical accuracy). This
                            small caption reassures non-English users it's intentional, not missing i18n. Shown
                            ONLY when the UI language is not English AND there is ≥1 citation → English users +
                            empty/loading panels render nothing (no layout shift). i18n-keyed, never LLM-generated. */}
                        {lang !== 'en' && citations.length > 0 && (
                            <p className="text-xs mb-3 text-text/40">
                                {ui.citationLanguageNote}
                            </p>
                        )}
                        <div className="flex-1 min-h-0">
                            <CitationPanel citations={citations} isLoading={loading && citations.length === 0} />
                        </div>
                    </div>
                </div>
            </div>

            {/* 在地差異提示 — renders only when enabled + zh-TW/en answer + ≥1 category matched + at
                least one authority row survives the ADR-007 (d) grounded-answer suppression;
                otherwise renders nothing (no layout shift). Does not alter answer/citations/disclaimer. */}
            <LocaleHintPanel matchedCategories={localeHint.categories} lang={lang} resolvedCountry={localeHint.country} resolutionLevel={localeHint.level} resetKey={localQueryId} citationSourceTypes={citationSourceTypes} />

            {answer && (
            <p className="text-xs mt-4 text-center" style={{ color: "rgb(var(--color-text) / 0.35)" }}>
                {DISCLAIMERS[detectedLang] || DISCLAIMERS['en']}
            </p>
            )}

            <div className="mt-8 border-t pt-6 space-y-2 text-xs" style={{ borderColor: "rgb(var(--color-text) / 0.15)", color: "rgb(var(--color-text) / 0.4)" }}>
                <p className="font-medium" style={{ color: "rgb(var(--color-text) / 0.6)" }}>{ui.dataSourcesTitle}</p>
                <p dangerouslySetInnerHTML={{ __html: ui.researchAttr1 }} />
                <p dangerouslySetInnerHTML={{ __html: ui.researchAttr2 }} />
                <p dangerouslySetInnerHTML={{ __html: ui.researchAttr3 }} />
                {/* TFDA OGDL v1.0 顯名 attribution (provenance sweep 2026-08-20) — the TFDA licence
                    corpus has been a Research source since v193; the footer must attribute it. */}
                <p dangerouslySetInnerHTML={{ __html: ui.researchAttr4 }} />
            </div>

        <UpgradeModal isOpen={showUpgradeModal} onClose={() => setShowUpgradeModal(false)} />
            {showDailyCapToast && (
                <Toast
                    message={ui.dailyCapToast}
                    type="warning"
                    onClose={() => setShowDailyCapToast(false)}
                    duration={5000}
                />
            )}
            {anonNoticeMsg && (
                <Toast
                    message={anonNoticeMsg}
                    type="warning"
                    onClose={() => setAnonNoticeMsg(null)}
                    duration={5000}
                />
            )}
            {anonQuotaCta && (
                <AnonymousUpgradeCTA
                    trigger="quota_hit"
                    quotaDetails={{ feature: 'research', used: anonQuotaCta.used, limit: anonQuotaCta.limit }}
                    onDismiss={() => setAnonQuotaCta(null)}
                />
            )}
        </div>
    );
}

export default function Research() {
    return (
        <PageShell
            activePage="research"
            allowAnonymous
            extraHead={
                <Head>
                    <meta name="robots" content="noindex, nofollow" />
                </Head>
            }
        >
            <div className="container mx-auto px-4 py-8">
                <ResearchForm />
            </div>
        </PageShell>
    );
}