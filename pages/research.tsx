"use client"

import { useState, FormEvent, useRef, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import rehypeRaw from 'rehype-raw';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { FatalError, makeOnOpen, sseOnError } from '../utils/sse';
import CitationPanel, { Citation } from '../components/CitationPanel';
import FeedbackBar from '../components/FeedbackBar';
import UpgradeModal from '../components/UpgradeModal';
import Toast from '../components/Toast';
import PHIWarning from '../components/PHIWarning';
import PageShell from '../components/PageShell';
import ProFeatureOverlay from '../components/ProFeatureOverlay';
import ResearchSection from '../components/ResearchSection';
import { exportResearchPdf } from '../utils/exportPdf';

const ACCENT = '#ff8e6e';

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
    evidence: '\u{1F7E2}' | '\u{1F7E1}' | '\u{1F534}' | null;
    content: string;
}

function parseResearchSections(text: string): ParsedSection[] | null {
    // Match headers like: ## Summary 🟢 — English   or   ## 摘要 🟡 — 繁體中文
    const headerRegex = /^##\s+(.+?)(?:\s+(🟢|🟡|🔴))?\s*(?:—\s*.+)?$/gm;
    const matches = [...text.matchAll(headerRegex)];
    if (matches.length === 0) return null;

    const sections: ParsedSection[] = [];
    for (let i = 0; i < matches.length; i++) {
        const match = matches[i];
        const title = match[1].trim();
        const evidence = (match[2] as ParsedSection['evidence']) || null;
        const start = match.index! + match[0].length;
        const end = i + 1 < matches.length ? matches[i + 1].index! : text.length;
        // Remove leading --- separator
        const content = text.slice(start, end).replace(/^\s*---\s*/g, '').trim();
        if (content) {
            sections.push({ title, evidence, content });
        }
    }
    return sections.length > 0 ? sections : null;
}

const defaultSuggestions = [
    "What are the common side effects of Metformin?",
    "Which drugs interact with Warfarin?",
    "Contraindications of ACE inhibitors in hypertension?",
    "DOACs vs Warfarin — key differences?",
    "When to use beta-blockers in heart failure?",
    "ワルファリンの副作用は何ですか？",
    "Metformin 腎臟不好的病人可以用嗎？",
    "Welche Wechselwirkungen hat Aspirin mit Blutverdünnern?",
    "Quels sont les effets secondaires des statines?",
    "Safety of antibiotics in pregnancy?",
];

const EVIDENCE_LEVELS = [
    { emoji: '🟢', label: 'Strong evidence', tip: 'Supported by systematic reviews, RCTs, or major guidelines' },
    { emoji: '🟡', label: 'Moderate', tip: 'Based on observational studies or conditional recommendations' },
    { emoji: '🔴', label: 'Limited', tip: 'Limited evidence found in retrieved sources — consider searching this topic separately' },
];

function EvidenceLegend() {
    const [expanded, setExpanded] = useState(false);
    return (
        <div className="mt-4 text-center">
            <div className="inline-flex items-center gap-4 text-xs" style={{ color: 'rgba(255,255,255,0.45)' }}>
                {EVIDENCE_LEVELS.map(({ emoji, label, tip }) => (
                    <span key={emoji} className="relative group">
                        <span className="cursor-help transition-colors hover:text-slate-200">{emoji} {label}</span>
                        {/* Desktop hover tooltip */}
                        <span
                            className="absolute bottom-full left-1/2 mb-2 hidden group-hover:block z-50"
                            style={{ transform: 'translateX(-50%)' }}
                        >
                            <span
                                className="block rounded-lg shadow-lg p-2 text-xs text-left whitespace-normal w-56"
                                style={{ background: '#1e293b', border: '1px solid #475569', color: '#cbd5e1' }}
                            >
                                {tip}
                            </span>
                            <span
                                className="block mx-auto"
                                style={{ width: 0, height: 0, borderLeft: '5px solid transparent', borderRight: '5px solid transparent', borderTop: '5px solid #475569' }}
                            />
                        </span>
                    </span>
                ))}
                {/* Mobile info toggle */}
                <button
                    className="md:hidden ml-1 rounded-full"
                    style={{ color: 'rgba(255,255,255,0.35)' }}
                    onClick={() => setExpanded(e => !e)}
                    aria-label="Evidence level info"
                >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
                    </svg>
                </button>
            </div>
            {/* Mobile expanded panel */}
            {expanded && (
                <div
                    className="md:hidden mt-2 rounded-lg p-3 text-left text-xs space-y-1.5 mx-auto max-w-sm"
                    style={{ background: '#1e293b', border: '1px solid #475569', color: '#cbd5e1' }}
                >
                    {EVIDENCE_LEVELS.map(({ emoji, label, tip }) => (
                        <p key={emoji}>{emoji} <span className="font-medium">{label}</span> — {tip}</p>
                    ))}
                </div>
            )}
        </div>
    );
}

function FallbackBanner() {
    return (
        <div className="mb-4 flex items-start gap-3 p-4 rounded-lg" style={{ background: "rgba(245,158,11,0.12)", border: "1px solid rgba(245,158,11,0.3)" }}>
            <span className="text-amber-500 text-sm mt-0.5 font-bold">⚠</span>
            <div>
                <p className="text-sm font-semibold" style={{ color: "#fbbf24" }}>
                    No literature found for this query
                </p>
                <p className="text-sm mt-0.5" style={{ color: "rgba(251,191,36,0.8)" }}>
                    This answer is based on general medical knowledge, not retrieved PubMed or FDA literature.
                    Please verify with current clinical guidelines before applying clinically.
                </p>
            </div>
        </div>
    );
}

function ResearchForm() {
    const { getToken } = useAuth();

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
    const [phiError, setPhiError] = useState<{detail: string; suggestion: string} | null>(null);
    const [detectedLang, setDetectedLang] = useState<string>('en');

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
    }, [getToken]);

    const answerRef    = useRef<HTMLDivElement>(null);
    const inputRef     = useRef<HTMLInputElement>(null);
    const isRunningRef = useRef(false);
    const [selectedSuggestion, setSelectedSuggestion] = useState<string | null>(null);

    useEffect(() => {
        if (answerRef.current && answer) {
            answerRef.current.scrollTop = answerRef.current.scrollHeight;
        }
    }, [answer]);

    const handleReset = () => {
        setQuestion(''); setAnswer(''); setCitations([]);
        setQueryTime(null); setError(''); setIsFallback(false); setStatusMsg(''); setPhiError(null);
        setSelectedSuggestion(null);
    };

    const runSearch = useCallback(async (q: string) => {
        if (!q.trim() || isRunningRef.current) return;
        isRunningRef.current = true;

        setAnswer(''); setCitations([]); setQueryTime(null);
        setLoading(true); setError(''); setIsFallback(false); setStatusMsg(''); setPhiError(null); setDetectedLang('en');

        const controller = new AbortController();

        try {
            const jwt = await getToken({ skipCache: true });
            if (!jwt) {
                setError('Authentication required. Please sign in again.');
                setLoading(false);
                isRunningRef.current = false;
                return;
            }

            await fetchEventSource(`${process.env.NEXT_PUBLIC_API_URL}/api/research`, {
                signal: controller.signal,
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${jwt}` },
                body: JSON.stringify({ question: q, max_results: 5 }),
                openWhenHidden: true,

                onopen: makeOnOpen({
                    onPhiBlocked: (detail, suggestion) => setPhiError({ detail, suggestion }),
                    onLimitReached: () => setShowUpgradeModal(true),
                }),

                onmessage(ev) {
                    try {
                        const data = JSON.parse(ev.data);
                        if (data.type === 'status')        setStatusMsg(data.content);
                        else if (data.type === 'language') setDetectedLang(data.lang || 'en');
                        else if (data.type === 'answer')   { setStatusMsg(''); setAnswer(prev => prev + data.content); }
                        else if (data.type === 'fallback') setIsFallback(true);
                        else if (data.type === 'citations') setCitations(data.content);
                        else if (data.type === 'error') {
                            if (data.error === 'limit_reached') {
                                setShowUpgradeModal(true);
                            } else if (data.error === 'daily_cap_reached') {
                                setShowDailyCapToast(true);
                            } else {
                                setError(data.content || data.error || 'An error occurred.');
                            }
                        }
                        else if (data.type === 'done')     { setLoading(false); if (data.query_time_ms) setQueryTime(data.query_time_ms); }
                    } catch {}
                },

                onclose() { setLoading(false); },

                onerror: sseOnError,
            });

        } catch (err: any) {
            controller.abort();
            setLoading(false);
            setError(err instanceof Error ? err.message : 'Unknown error. Please try again.');
        } finally {
            isRunningRef.current = false;
        }
    }, [getToken]);

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        await runSearch(question);
    }

    return (
        <div className="flex flex-col gap-4 max-w-5xl mx-auto">
            {/* Title row */}
            <div className="flex justify-between items-start">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight" style={{ color: "#ffffff" }}>Medical Research</h1>
                    <p className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.5)" }}>Evidence-based answers from PubMed 36M+ and official FDA drug data.</p>
                </div>
                {(answer || question) && (
                    <button onClick={handleReset} className="text-sm font-medium px-3 py-1 rounded-lg transition-all mt-1"
                        style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.3)', color: 'rgba(255,255,255,0.7)' }}
                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.1)'; }}
                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}>
                        + New
                    </button>
                )}
            </div>

            {/* Info box */}
            <div className="rounded-xl p-4 text-sm" style={{ background: "rgba(255,142,110,0.1)", border: "1px solid rgba(255,142,110,0.35)" }}>
                <p style={{ color: "rgba(255,142,110,0.95)" }}>
                    <span className="font-semibold">Ask in any language</span> — answered from PubMed 36M+ and FDA official data.
                </p>
            </div>

            {/* Main layout */}
            <div className="flex flex-col lg:flex-row gap-6">
                {/* Left: answer area */}
                <div className="flex-1 flex flex-col">
                    <div className="rounded-xl p-6 flex flex-col" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>

                        {phiError && !loading && (
                            <PHIWarning detail={phiError.detail} suggestion={phiError.suggestion} onDismiss={() => setPhiError(null)} />
                        )}

                        {error && !loading && (
                            <div className="mb-4 p-3 rounded-lg border text-sm" style={{ background: "rgba(239,68,68,0.1)", borderColor: "rgba(239,68,68,0.3)", color: "rgba(255,150,150,0.9)" }}>
                                {error}
                            </div>
                        )}

                        <div ref={answerRef} className="overflow-y-auto mb-4 min-h-[300px] max-h-[500px]">
                            {!answer && !loading && (
                                <div className="text-center py-12">
                                    <div className="space-y-3">
                                        <p className="text-xs uppercase tracking-widest" style={{ color: "rgba(255,255,255,0.35)" }}>Try these</p>
                                        <p className="text-xs mb-2" style={{ color: "rgba(148,163,184,0.8)" }}>
                                            Ask one question at a time for the most accurate, evidence-based results.
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
                                                            background: isSelected ? "rgba(255,142,110,0.15)" : "rgba(255,255,255,0.06)",
                                                            border: `1px solid ${isSelected ? "#ff8e6e" : "rgba(255,255,255,0.15)"}`,
                                                            color: isSelected ? "#ff8e6e" : "rgba(255,255,255,0.7)",
                                                            transform: isSelected ? "scale(1.05)" : "scale(1)",
                                                            opacity: hasSel && !isSelected ? 0.5 : 1,
                                                        }}
                                                        onMouseEnter={e => {
                                                            if (!isSelected) {
                                                                (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,142,110,0.6)";
                                                                (e.currentTarget as HTMLElement).style.color = "#ff8e6e";
                                                                (e.currentTarget as HTMLElement).style.opacity = "1";
                                                            }
                                                        }}
                                                        onMouseLeave={e => {
                                                            if (!isSelected) {
                                                                (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.15)";
                                                                (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.7)";
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
                                <div className="flex items-center gap-3 py-8" style={{ color: "rgba(255,255,255,0.5)" }}>
                                    <div className="w-4 h-4 border-2 border-t-orange-400 rounded-full animate-spin flex-shrink-0" style={{ borderColor: "rgba(255,255,255,0.2)", borderTopColor: "#ff8e6e" }} />
                                    <span className="text-sm">{statusMsg}</span>
                                </div>
                            )}

                            {(answer || loading) && (
                                <div>
                                    {isFallback && !loading && <FallbackBanner />}
                                    {(() => {
                                        const cleanAnswer = !loading ? stripLlmDisclaimer(answer) : answer;
                                        const sections = !loading ? parseResearchSections(cleanAnswer) : null;
                                        const proseStyle = {
                                            color: "rgba(255,255,255,0.85)",
                                            '--tw-prose-headings': '#ffffff',
                                            '--tw-prose-bold': '#ffffff',
                                            '--tw-prose-links': '#ff8e6e',
                                            '--tw-prose-bullets': 'rgba(255,255,255,0.5)',
                                            '--tw-prose-counters': 'rgba(255,255,255,0.5)',
                                            '--tw-prose-code': '#ff8e6e',
                                            '--tw-prose-hr': 'rgba(255,255,255,0.15)',
                                        } as React.CSSProperties;

                                        if (sections && !loading) {
                                            return (
                                                <>
                                                    {sections.map((sec, i) => (
                                                        <ResearchSection key={i} title={sec.title} evidence={sec.evidence}>
                                                            <div className="prose max-w-none prose-sm prose-headings:font-semibold prose-h2:text-base" style={proseStyle}>
                                                                <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>{sec.content}</ReactMarkdown>
                                                            </div>
                                                        </ResearchSection>
                                                    ))}
                                                    <p className="text-xs mt-3 mb-1" style={{ color: 'rgba(255,255,255,0.35)' }}>
                                                        {DISCLAIMERS[detectedLang] || DISCLAIMERS['en']}
                                                    </p>
                                                    <EvidenceLegend />
                                                </>
                                            );
                                        }

                                        return (
                                            <>
                                                <div className="prose max-w-none prose-sm prose-headings:font-semibold prose-h2:text-base" style={proseStyle}>
                                                    <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>{cleanAnswer}</ReactMarkdown>
                                                </div>
                                                {!loading && (
                                                    <p className="text-xs mt-3" style={{ color: 'rgba(255,255,255,0.35)' }}>
                                                        {DISCLAIMERS[detectedLang] || DISCLAIMERS['en']}
                                                    </p>
                                                )}
                                            </>
                                        );
                                    })()}
                                    {loading && answer && (
                                        <span className="inline-block w-1.5 h-4 rounded-sm animate-pulse ml-0.5" style={{ background: ACCENT }} />
                                    )}
                                    {!loading && answer && !error && (
                                        <>
                                            <FeedbackBar query={question} response={answer} category="research" />
                                            <div className="mt-3 inline-block">
                                                <ProFeatureOverlay isLocked={plan !== 'pro'} featureName="Export">
                                                    <button
                                                        onClick={() => exportResearchPdf(question, answer, citations)}
                                                        className="inline-flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-lg transition-all cursor-pointer"
                                                        style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.55)' }}
                                                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.12)'; (e.currentTarget as HTMLElement).style.color = 'white'; }}
                                                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.06)'; (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.55)'; }}
                                                    >
                                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                                                        Export with Citations
                                                    </button>
                                                </ProFeatureOverlay>
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}
                        </div>

                        {queryTime && (
                            <p className="text-xs mb-2" style={{ color: "rgba(255,255,255,0.35)" }}>
                                Query time: {(queryTime / 1000).toFixed(2)}s
                            </p>
                        )}

                        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2">
                            <input
                                ref={inputRef}
                                type="text"
                                value={question}
                                onChange={(e) => { setQuestion(e.target.value); setSelectedSuggestion(null); }}
                                placeholder="Ask a clinical question in any language..."
                                className="flex-1 px-4 py-2.5 text-sm rounded-lg focus:outline-none transition-shadow"
                                style={{ background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.15)", color: "#ffffff" }}
                                disabled={loading}
                            />
                            <button
                                type="submit"
                                disabled={loading || !question.trim()}
                                className="px-5 py-2.5 text-white text-sm font-medium rounded-lg transition-opacity disabled:opacity-50"
                                style={{ background: ACCENT }}
                            >
                                {loading ? (
                                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                ) : 'Search'}
                            </button>
                        </form>

                    </div>
                </div>

                {/* Right: citations */}
                <div className="w-full lg:w-96 flex flex-col">
                    <div className="rounded-xl p-6 flex-1 overflow-hidden" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>
                        <CitationPanel citations={citations} isLoading={loading && citations.length === 0} />
                    </div>
                </div>
            </div>

            <p className="text-xs mt-4 text-center" style={{ color: "rgba(255,255,255,0.35)" }}>
                {DISCLAIMERS[detectedLang] || DISCLAIMERS['en']}
            </p>

            <div className="mt-8 border-t pt-6 space-y-2 text-xs" style={{ borderColor: "rgba(255,142,110,0.35)", color: "rgba(255,255,255,0.4)" }}>
                <p className="font-medium" style={{ color: "rgba(255,255,255,0.6)" }}>Data Sources & Attribution</p>
                <p>
                    Research results powered by{' '}
                    <a href="https://pubmed.ncbi.nlm.nih.gov" target="_blank" rel="noopener noreferrer" className="underline opacity-70 hover:opacity-100">PubMed®</a>
                    {' '}(National Library of Medicine).
                </p>
                <p>
                    Drug data from FDA official drug labels via{' '}
                    <a href="https://dailymed.nlm.nih.gov" target="_blank" rel="noopener noreferrer" className="underline opacity-70 hover:opacity-100">DailyMed</a>
                    {' '}(FDA/NLM).
                </p>
                <p>
                    Vela is not affiliated with or endorsed by NLM, FDA, or any U.S. government agency.
                </p>
            </div>

        <UpgradeModal isOpen={showUpgradeModal} onClose={() => setShowUpgradeModal(false)} />
            {showDailyCapToast && (
                <Toast
                    message="You've reached today's usage limit. Resets at midnight UTC."
                    type="warning"
                    onClose={() => setShowDailyCapToast(false)}
                    duration={5000}
                />
            )}
        </div>
    );
}

export default function Research() {
    return (
        <PageShell activePage="research">
            <div className="container mx-auto px-4 py-8">
                <ResearchForm />
            </div>
        </PageShell>
    );
}