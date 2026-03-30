"use client"

import { useState, FormEvent, useRef } from 'react';
import { useAuth, SignedIn, SignedOut, RedirectToSignIn } from '@clerk/nextjs';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import FeedbackBar from '../components/FeedbackBar';
import Toast from '../components/Toast';
import UpgradeModal from '../components/UpgradeModal';
import MobileNav from '../components/MobileNav';
import Navbar from '../components/Navbar';

const ACCENT = '#68d391';

class FatalError extends Error {}

interface ExplainSource {
    source_type: string;
    label: string;
    url?: string;
    description?: string;
}

const SOURCE_STYLES: Record<string, { bg: string; text: string; border: string }> = {
    LOINC:       { bg: 'rgba(99,179,237,0.12)',   text: '#63b3ed', border: 'rgba(99,179,237,0.3)'   },
    MedlinePlus: { bg: 'rgba(104,211,145,0.12)', text: '#68d391', border: 'rgba(104,211,145,0.3)' },
    FDA:         { bg: 'rgba(252,129,129,0.12)', text: '#fc8181', border: 'rgba(252,129,129,0.3)' },
    RxNorm:      { bg: 'rgba(183,148,244,0.12)', text: '#b794f4', border: 'rgba(183,148,244,0.3)' },
};

function SourceBadge({ source }: { source: ExplainSource }) {
    const s = SOURCE_STYLES[source.source_type] ?? SOURCE_STYLES['MedlinePlus'];
    const badge = (
        <span 
            className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
            style={{ background: s.bg, color: s.text, border: `1px solid ${s.border}` }}
        >
            {source.label}
        </span>
    );

    if (source.url) {
        return (
            <a href={source.url} target="_blank" rel="noopener noreferrer" className="hover:opacity-75 transition-opacity">
                {badge}
            </a>
        );
    }

    // Non-clickable badge with tooltip explaining why
    return (
        <span
            className="relative group cursor-default"
            title="LOINC is the international standard for lab test terminology. Full records require a free LOINC account at loinc.org"
        >
            {badge}
            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 px-3 py-2 text-xs text-white bg-gray-800 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 text-center leading-relaxed">
                LOINC is the international standard for lab terminology.
                Full records require a free account at loinc.org.
            </span>
        </span>
    );
}

function ExplainForm() {
    const { getToken } = useAuth();
    const [reportText, setReportText] = useState('');
    const [output, setOutput]         = useState('');
    const [sources, setSources]       = useState<ExplainSource[]>([]);
    const [loading, setLoading]       = useState(false);
    const [statusMsg, setStatusMsg]   = useState('');
    const [error, setError]           = useState('');
    const [showToast, setShowToast]       = useState(false);
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    const [showDailyCapToast, setShowDailyCapToast] = useState(false);
    const isRunningRef = useRef(false);

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        if (isRunningRef.current) return;
        isRunningRef.current = true;
        setOutput(''); setSources([]); setError(''); setStatusMsg(''); setLoading(true);
        const controller = new AbortController();
        try {
            const jwt = await getToken({ skipCache: true });
            if (!jwt) { setError('Authentication required.'); setLoading(false); isRunningRef.current = false; return; }
            let accumulated = '';
            await fetchEventSource(`${process.env.NEXT_PUBLIC_API_URL}/api/explain`, {
                signal: controller.signal, method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${jwt}` },
                body: JSON.stringify({ report_text: reportText }),
                openWhenHidden: true,
                async onopen(response) {
                    if (response.ok) return;
                    if (response.status === 403) {
                        const data = await response.json().catch(() => ({}));
                        if (data.error === 'limit_reached') {
                            setShowUpgradeModal(true);
                            throw new FatalError('');
                        }
                        throw new FatalError('Session expired.');
                    }
                    if (response.status === 429) {
                        setShowDailyCapToast(true);
                        throw new FatalError('');
                    }
                    throw new FatalError(`Server error (${response.status}).`);
                },
                onmessage(ev) {
                    if (!ev.data || ev.data.trim() === '') return;
                    try {
                        const data = JSON.parse(ev.data);
                        if (data.type === 'status')       setStatusMsg(data.content);
                        else if (data.type === 'sources') setSources(data.content ?? []);
                        else if (data.type === 'answer')  { accumulated += data.content; setOutput(accumulated); }
                        else if (data.type === 'done')    { setLoading(false); setStatusMsg(''); }
                        else if (data.type === 'error') {
                            if (data.error === 'limit_reached') {
                                setShowUpgradeModal(true);
                            } else if (data.error === 'daily_cap_reached') {
                                setShowDailyCapToast(true);
                            } else {
                                setError(data.content || data.error || 'An error occurred.');
                            }
                            setLoading(false);
                        }
                    } catch {}
                },
                onclose() { setLoading(false); setStatusMsg(''); },
                onerror(err) {
                    if (err instanceof FatalError) throw err;
                    throw new FatalError(err instanceof Error ? err.message : 'Connection lost.');
                },
            });
        } catch (err: any) {
            controller.abort(); setLoading(false); setStatusMsg('');
            setError(err instanceof Error ? err.message : 'Unknown error.');
        } finally { isRunningRef.current = false; }
    }

    const handleReset = () => {
        setReportText(''); setOutput(''); setSources([]); setError(''); setStatusMsg('');
    };

    const sampleQueries = [
        "eGFR 45 mL/min (ref >60), HbA1c 7.8%, Metformin 1000mg BID",
        "Sodium 138, Potassium 3.3 (LOW), Creatinine 1.5 (HIGH), Glucose 142 (HIGH)",
        "TSH 12.5 mIU/L (ref 0.4-4.0)",
        "Atorvastatin 40mg, Metoprolol 25mg, Aspirin 81mg, Ramipril 5mg",
    ];

    return (
        <div className="container mx-auto px-4 py-8 max-w-3xl">
            <div className="flex justify-between items-start mb-6">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "#ffffff" }}>Understand Your Medical Report</h1>
                    <p className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.5)" }}>Evidence-based · Verified Sources</p>
                </div>
                {(output || reportText) && (
                    <button onClick={handleReset} className="text-sm font-medium px-3 py-1 rounded-lg transition-all mt-1"
                        style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.3)', color: 'rgba(255,255,255,0.7)' }}
                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.1)'; }}
                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}>
                        + New
                    </button>
                )}
            </div>

            {/* Privacy notice */}
            <div className="rounded-lg p-4 mb-6 border" style={{ background: 'rgba(74,222,128,0.05)', borderColor: 'rgba(74,222,128,0.3)' }}>
                <p className="text-sm" style={{ color: 'rgba(74,222,128,0.9)' }}>
                    <strong>Privacy:</strong> Paste lab results or medical documents only — no personal names or identifying information. Your report is processed securely and not stored.
                </p>
            </div>

            {error && (
                <div className="mb-5 p-3 rounded-lg border text-sm" style={{ background: "rgba(252,129,129,0.12)", borderColor: "rgba(252,129,129,0.3)", color: "#fc8181" }}>{error}</div>
            )}

            <form onSubmit={handleSubmit} className="rounded-xl p-6 space-y-5" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>
                <div className="space-y-2">
                    <label htmlFor="report" className="block text-sm font-medium" style={{ color: "rgba(255,255,255,0.8)" }}>
                        Medical Report / Lab Results
                    </label>

                    {/* Sample query tags */}
                    {!output && (
                        <div className="flex flex-wrap gap-2 pb-1">
                            {sampleQueries.map((s, i) => (
                                <button
                                    key={i}
                                    type="button"
                                    onClick={() => setReportText(s)}
                                    disabled={loading}
                                    className="px-3 py-1.5 text-xs rounded-full disabled:opacity-50 transition-all duration-200"
                                    style={{ background: "rgba(104,211,145,0.08)", border: "1px solid rgba(104,211,145,0.3)", color: "rgba(104,211,145,0.85)" }}
                                    onMouseEnter={e => {
                                        (e.currentTarget as HTMLElement).style.borderColor = "rgba(104,211,145,0.6)";
                                        (e.currentTarget as HTMLElement).style.background = "rgba(104,211,145,0.18)";
                                    }}
                                    onMouseLeave={e => {
                                        (e.currentTarget as HTMLElement).style.borderColor = "rgba(104,211,145,0.3)";
                                        (e.currentTarget as HTMLElement).style.background = "rgba(104,211,145,0.08)";
                                    }}
                                >
                                    {s}
                                </button>
                            ))}
                        </div>
                    )}

                    <textarea
                        id="report" required rows={12} value={reportText}
                        onChange={(e) => setReportText(e.target.value)} disabled={loading}
                        className="w-full px-4 py-3 rounded-lg focus:outline-none focus:ring-2 disabled:opacity-60 font-mono text-sm" style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.15)", color: "rgba(255,255,255,0.85)" }}
                        placeholder={"Paste your lab results or medical report here.\n\nExamples:\neGFR 45 mL/min (ref >60), HbA1c 7.8%, Metformin 1000mg BID\n\n腎絲球過濾率 45，糖化血色素 7.8%，Metformin 1000mg 每日兩次"}
                    />
                    <p className="text-xs text-gray-400">Supports English, Traditional Chinese, Japanese, Korean, Spanish, and more.</p>
                </div>
                <button
                    type="submit" disabled={loading || !reportText.trim()}
                    className="w-full text-white font-medium py-2.5 px-6 rounded-lg transition-opacity disabled:opacity-50 text-sm"
                    style={{ background: ACCENT }}
                >
                    {loading ? (
                        <span className="flex items-center justify-center gap-2">
                            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            {statusMsg || 'Processing...'}
                        </span>
                    ) : 'Explain My Report'}
                </button>
            </form>

            <p className="text-xs mt-3 text-center" style={{ color: "rgba(255,255,255,0.35)" }}>
                ⚠️ Explanations may contain errors. Always consult your doctor for medical advice.
            </p>

            {sources.length > 0 && (
                <div className="mt-5 rounded-xl p-5" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>
                    <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Verified Sources</p>
                    <div className="flex flex-wrap gap-2">
                        {sources.map((src, i) => <SourceBadge key={i} source={src} />)}
                    </div>
                </div>
            )}

            {output && (
                <section className="mt-5 rounded-xl p-6" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-base font-semibold" style={{ color: "#ffffff" }}>Explanation</h2>
                        <button onClick={() => { navigator.clipboard.writeText(output); setShowToast(true); }}
                            className="text-xs text-gray-400 hover:text-white transition-colors">
                            Copy to clipboard
                        </button>
                    </div>
                    <div className="rounded-lg p-3 mb-5 border text-sm" style={{ background: 'rgba(251,191,36,0.06)', borderColor: 'rgba(251,191,36,0.3)' }}>
                        <p style={{ color: "rgba(251,191,36,0.85)" }}>
                            ⚠️ Explanations may contain errors. Always consult your doctor for medical advice.
                        </p>
                    </div>
                    <div 
                        className="prose max-w-none prose-sm prose-headings:font-semibold prose-h2:text-base prose-h2:pb-1 prose-p:leading-relaxed prose-li:leading-relaxed"
                        style={{
                            color: "rgba(255,255,255,0.85)",
                            '--tw-prose-headings': '#ffffff',
                            '--tw-prose-bold': '#ffffff',
                            '--tw-prose-links': '#68d391',
                            '--tw-prose-bullets': 'rgba(255,255,255,0.5)',
                            '--tw-prose-counters': 'rgba(255,255,255,0.5)',
                            '--tw-prose-code': '#68d391',
                            '--tw-prose-hr': 'rgba(255,255,255,0.15)',
                        } as React.CSSProperties}
                    >
                        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{output}</ReactMarkdown>
                    </div>
                    {loading && <span className="inline-block w-1.5 h-4 rounded-sm animate-pulse ml-0.5 mt-2" style={{ background: ACCENT }} />}
                    {!loading && !error && (
                        <FeedbackBar query={reportText} response={output} category="explain" />
                    )}
                </section>
            )}

            <div className="mt-8 border-t pt-6 space-y-2 text-xs" style={{ borderColor: "rgba(104,211,145,0.35)", color: "rgba(255,255,255,0.4)" }}>
                <p className="font-medium" style={{ color: "rgba(255,255,255,0.6)" }}>Data Sources & Attribution</p>
                <p>
                    Lab test terminology provided by{' '}
                    <a href="https://loinc.org" target="_blank" rel="noopener noreferrer" className="underline opacity-70 hover:opacity-100">LOINC®</a>
                    {' '}(Regenstrief Institute, Inc.). LOINC® is a registered trademark of Regenstrief Institute, Inc.
                    Vela is not affiliated with or endorsed by Regenstrief Institute.
                </p>
                <p>
                    Drug and health information courtesy of{' '}
                    <a href="https://medlineplus.gov" target="_blank" rel="noopener noreferrer" className="underline opacity-70 hover:opacity-100">MedlinePlus</a>
                    {' '}and the{' '}
                    <a href="https://www.nlm.nih.gov" target="_blank" rel="noopener noreferrer" className="underline opacity-70 hover:opacity-100">U.S. National Library of Medicine (NLM)</a>.
                    Vela is not affiliated with or endorsed by NLM or any U.S. government agency.
                </p>
                <p>
                    Drug name standardization powered by{' '}
                    <a href="https://www.nlm.nih.gov/research/umls/rxnorm" target="_blank" rel="noopener noreferrer" className="underline opacity-70 hover:opacity-100">RxNorm</a>
                    {' '}(NLM). Drug label data from{' '}
                    <a href="https://dailymed.nlm.nih.gov" target="_blank" rel="noopener noreferrer" className="underline opacity-70 hover:opacity-100">DailyMed</a>
                    {' '}(FDA/NLM).
                </p>
            </div>

            {showToast && <Toast message="Copied to clipboard" onClose={() => setShowToast(false)} />}
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

export default function Explain() {
    return (
        <main className="min-h-screen pb-20 md:pb-0" style={{ background: "linear-gradient(135deg, #0a1628 0%, #0f2040 45%, #1a1035 75%, #0d1a2e 100%)" }}>
            <Navbar activePage="explain" />
            <SignedIn><ExplainForm /></SignedIn>
            <SignedOut><RedirectToSignIn /></SignedOut>
            <MobileNav />
        </main>
    );
}