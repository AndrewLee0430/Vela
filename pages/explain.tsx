"use client"

import { useState, FormEvent, useRef } from 'react';
import { useAuth, SignedIn, SignedOut, RedirectToSignIn, UserButton } from '@clerk/nextjs';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import Link from 'next/link';
import Image from 'next/image';
import Toast from '../components/Toast';

const ACCENT = '#68d391';

class FatalError extends Error {}

interface ExplainSource {
    source_type: string;
    label: string;
    url?: string;
    description?: string;
}

const SOURCE_STYLES: Record<string, { bg: string; text: string; border: string }> = {
    LOINC:       { bg: 'bg-blue-50 dark:bg-blue-900/20',   text: 'text-blue-700 dark:text-blue-300',   border: 'border-blue-200 dark:border-blue-700' },
    MedlinePlus: { bg: 'bg-green-50 dark:bg-green-900/20', text: 'text-green-700 dark:text-green-300', border: 'border-green-200 dark:border-green-700' },
    FDA:         { bg: 'bg-red-50 dark:bg-red-900/20',     text: 'text-red-700 dark:text-red-300',     border: 'border-red-200 dark:border-red-700' },
    RxNorm:      { bg: 'bg-purple-50 dark:bg-purple-900/20', text: 'text-purple-700 dark:text-purple-300', border: 'border-purple-200 dark:border-purple-700' },
};

function SourceBadge({ source }: { source: ExplainSource }) {
    const s = SOURCE_STYLES[source.source_type] ?? SOURCE_STYLES['MedlinePlus'];
    const badge = (
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${s.bg} ${s.text} ${s.border}`}>
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
    const [showToast, setShowToast]   = useState(false);
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
            await fetchEventSource('http://127.0.0.1:8000/api/explain', {
                signal: controller.signal, method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${jwt}` },
                body: JSON.stringify({ report_text: reportText }),
                openWhenHidden: true,
                async onopen(response) {
                    if (response.ok) return;
                    if (response.status === 403 || response.status === 401) throw new FatalError('Session expired.');
                    if (response.status === 429) throw new FatalError('Too many requests. Please wait.');
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
                        else if (data.type === 'error')   { setError(data.content); setLoading(false); }
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

    return (
        <div className="container mx-auto px-4 py-8 max-w-3xl">
            <div className="mb-6">
                <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "#ffffff" }}>Understand Your Medical Report</h1>
                <p className="text-sm" style={{ color: "rgba(255,255,255,0.5)" }}>Paste any lab results, diagnosis, or medical document — explained in plain language with verified sources.</p>
            </div>
            {error && (
                <div className="mb-5 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg border border-red-100 text-sm">{error}</div>
            )}

            <form onSubmit={handleSubmit} className="rounded-xl p-6 space-y-5" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>
                <div className="space-y-2">
                    <label htmlFor="report" className="block text-sm font-medium" style={{ color: "rgba(255,255,255,0.8)" }}>
                        Medical Report / Lab Results
                    </label>
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
                        <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Explanation</h2>
                        <button onClick={() => { navigator.clipboard.writeText(output); setShowToast(true); }}
                            className="text-xs text-gray-400 hover:text-white transition-colors">
                            Copy to clipboard
                        </button>
                    </div>
                    <div className="rounded-lg p-3 mb-5 border text-sm" style={{ background: 'rgba(251,191,36,0.06)', borderColor: 'rgba(251,191,36,0.3)' }}>
                        <p className="text-yellow-800 dark:text-yellow-200">
                            ⚠️ <strong>For educational purposes only.</strong> This explanation does not replace professional medical advice.
                        </p>
                    </div>
                    <div className="prose prose-invert max-w-none prose-sm prose-headings:font-semibold prose-h2:text-base prose-h2:border-b prose-h2:border-gray-100 dark:prose-h2:border-gray-700 prose-h2:pb-1 prose-p:leading-relaxed prose-li:leading-relaxed">
                        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{output}</ReactMarkdown>
                    </div>
                    {loading && <span className="inline-block w-1.5 h-4 rounded-sm animate-pulse ml-0.5 mt-2" style={{ background: ACCENT }} />}
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
        </div>
    );
}

export default function Explain() {
    return (
        <main className="min-h-screen" style={{ background: "linear-gradient(135deg, #0a1628 0%, #0f2040 45%, #1a1035 75%, #0d1a2e 100%)" }}>
            <nav className="border-b" style={{ background: "linear-gradient(135deg, #0a1628 0%, #0f2040 45%, #1a1035 75%, #0d1a2e 100%)", borderColor: "rgba(255,255,255,0.07)" }}>
                <div className="container mx-auto px-4 py-3">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-8">
                            <Link href="/" className="group relative flex items-center" title="Homepage">
                                <Image src="/coral_logo.png" alt="Vela" width={60} height={60} style={{ objectFit: 'contain' }} />
                                <span className="absolute -bottom-7 left-1/2 -translate-x-1/2 text-xs bg-gray-800 text-white px-2 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                                  Homepage
                                </span>
                              </Link>
                            <div className="hidden md:flex items-center gap-6 text-sm">
                                <Link href="/research" className="text-gray-400 hover:text-white transition-colors">Research</Link>
                                <Link href="/verify"   className="text-gray-400 hover:text-white transition-colors">Verify</Link>
                                <Link href="/explain"  className="font-medium transition-colors" style={{ color: ACCENT }}>Explain</Link>
                                <Link href="/history"  className="text-gray-400 hover:text-white transition-colors">History</Link>
                            </div>
                        </div>
                        <UserButton showName={true} />
                    </div>
                </div>
            </nav>
            <SignedIn><ExplainForm /></SignedIn>
            <SignedOut><RedirectToSignIn /></SignedOut>
        </main>
    );
}