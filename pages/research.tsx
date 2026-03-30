"use client"

import { useState, FormEvent, useRef, useEffect, useCallback } from 'react';
import { useAuth, SignedIn, SignedOut, RedirectToSignIn } from '@clerk/nextjs';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import CitationPanel, { Citation } from '../components/CitationPanel';
import FeedbackBar from '../components/FeedbackBar';
import UpgradeModal from '../components/UpgradeModal';
import Toast from '../components/Toast';
import MobileNav from '../components/MobileNav';
import Navbar from '../components/Navbar';

// Research accent color
const ACCENT = '#ff8e6e';

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

class FatalError extends Error {}

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

    const answerRef    = useRef<HTMLDivElement>(null);
    const isRunningRef = useRef(false);

    useEffect(() => {
        if (answerRef.current && answer) {
            answerRef.current.scrollTop = answerRef.current.scrollHeight;
        }
    }, [answer]);

    const handleReset = () => {
        setQuestion(''); setAnswer(''); setCitations([]);
        setQueryTime(null); setError(''); setIsFallback(false); setStatusMsg('');
    };

    const runSearch = useCallback(async (q: string) => {
        if (!q.trim() || isRunningRef.current) return;
        isRunningRef.current = true;

        setAnswer(''); setCitations([]); setQueryTime(null);
        setLoading(true); setError(''); setIsFallback(false); setStatusMsg('');

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

                async onopen(response) {
                    if (response.ok) return;
                    if (response.status === 403) {
                        // 可能是 limit_reached 或 session expired
                        const data = await response.json().catch(() => ({}));
                        if (data.error === 'limit_reached') {
                            setShowUpgradeModal(true);
                            throw new FatalError('');
                        }
                        throw new FatalError('Session expired. Please refresh and sign in again.');
                    }
                    if (response.status === 429)
                        throw new FatalError('Too many requests. Please wait a moment and try again.');
                    throw new FatalError(`Server error (${response.status}). Please try again.`);
                },

                onmessage(ev) {
                    try {
                        const data = JSON.parse(ev.data);
                        if (data.type === 'status')        setStatusMsg(data.content);
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

                onerror(err) {
                    if (err instanceof FatalError) throw err;
                    throw new FatalError(err instanceof Error ? err.message : 'Connection lost. Please try again.');
                },
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
        <div className="flex flex-col gap-4 max-w-[80%] mx-auto">
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
                    <span className="font-semibold">Ask in any language</span> — we search in English and answer in yours. Grounded in peer-reviewed literature and official FDA drug data.
                </p>
            </div>

            {/* Main layout */}
            <div className="flex flex-col lg:flex-row gap-6">
                {/* Left: answer area */}
                <div className="flex-1 flex flex-col">
                    <div className="rounded-xl p-6 flex flex-col" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>

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
                                        <div className="flex flex-wrap justify-center gap-2">
                                            {defaultSuggestions.map((s, i) => (
                                                <button
                                                    key={i}
                                                    onClick={() => { setQuestion(s); runSearch(s); }}
                                                    disabled={loading}
                                                    className="px-3 py-1.5 text-xs rounded-full disabled:opacity-50 transition-all duration-200"
                                                    style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.15)", color: "rgba(255,255,255,0.7)" }}
                                                    onMouseEnter={e => {
                                                        (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,142,110,0.6)";
                                                        (e.currentTarget as HTMLElement).style.color = "#ff8e6e";
                                                    }}
                                                    onMouseLeave={e => {
                                                        (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.15)";
                                                        (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.7)";
                                                    }}
                                                >
                                                    {s}
                                                </button>
                                            ))}
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
                                <div 
                                    className="prose max-w-none prose-sm prose-headings:font-semibold prose-h2:text-base"
                                    style={{
                                        color: "rgba(255,255,255,0.85)",
                                        '--tw-prose-headings': '#ffffff',
                                        '--tw-prose-bold': '#ffffff',
                                        '--tw-prose-links': '#ff8e6e',
                                        '--tw-prose-bullets': 'rgba(255,255,255,0.5)',
                                        '--tw-prose-counters': 'rgba(255,255,255,0.5)',
                                        '--tw-prose-code': '#ff8e6e',
                                        '--tw-prose-hr': 'rgba(255,255,255,0.15)',
                                    } as React.CSSProperties}
                                >
                                    {isFallback && !loading && <FallbackBanner />}
                                    <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{answer}</ReactMarkdown>
                                    {loading && answer && (
                                        <span className="inline-block w-1.5 h-4 rounded-sm animate-pulse ml-0.5" style={{ background: ACCENT }} />
                                    )}
                                    {!loading && answer && !error && (
                                        <FeedbackBar query={question} response={answer} category="research" />
                                    )}
                                </div>
                            )}
                        </div>

                        {queryTime && (
                            <p className="text-xs mb-2" style={{ color: "rgba(255,255,255,0.35)" }}>
                                Query time: {(queryTime / 1000).toFixed(2)}s
                            </p>
                        )}

                        <form onSubmit={handleSubmit} className="flex gap-2">
                            <input
                                type="text"
                                value={question}
                                onChange={(e) => setQuestion(e.target.value)}
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
                <div className="lg:w-96 flex flex-col">
                    <div className="rounded-xl p-6 flex-1 overflow-hidden" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>
                        <CitationPanel citations={citations} isLoading={loading && citations.length === 0} />
                    </div>
                </div>
            </div>

            <p className="text-xs mt-4 text-center" style={{ color: "rgba(255,255,255,0.35)" }}>
                ⚠️ For informational purposes only. Always verify with clinical guidelines and consult a qualified professional.
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
        <main className="min-h-screen pb-20 md:pb-0" style={{ background: "linear-gradient(135deg, #0a1628 0%, #0f2040 45%, #1a1035 75%, #0d1a2e 100%)" }}>
            <Navbar activePage="research" />
            <SignedIn>
                <div className="container mx-auto px-4 py-8">
                    <ResearchForm />
                </div>
            </SignedIn>
            <SignedOut><RedirectToSignIn /></SignedOut>
            <MobileNav />
        </main>
    );
}