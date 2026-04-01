"use client"

import { useState, useEffect, FormEvent, useRef, useCallback, DragEvent } from 'react';
import { useAuth } from '@clerk/nextjs';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { FatalError, makeOnOpen, sseOnError } from '../utils/sse';
import FeedbackBar from '../components/FeedbackBar';
import Toast from '../components/Toast';
import PHIWarning from '../components/PHIWarning';
import UpgradeModal from '../components/UpgradeModal';
import PageShell from '../components/PageShell';

const ACCENT = '#68d391';

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
    return (
        <span
            className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
            style={{ background: s.bg, color: s.text, border: `1px solid ${s.border}` }}
        >
            {source.label}
        </span>
    );
}

type UploadState = 'idle' | 'uploading' | 'preview' | 'error';

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
    const [phiError, setPhiError] = useState<{detail: string; suggestion: string} | null>(null);
    const isRunningRef = useRef(false);
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

    // Upload state
    const [uploadState, setUploadState] = useState<UploadState>('idle');
    const [uploadError, setUploadError] = useState('');
    const [extractedText, setExtractedText] = useState('');
    const [extractedFileName, setExtractedFileName] = useState('');
    const [dragOver, setDragOver] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const MAX_FILE_SIZE = 10 * 1024 * 1024;
    const ALLOWED_TYPES = ['application/pdf', 'image/jpeg', 'image/png', 'image/webp'];

    const extractFromPdf = useCallback(async (file: File): Promise<string> => {
        const pdfjsLib = await import('pdfjs-dist');
        pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;
        const arrayBuffer = await file.arrayBuffer();
        const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
        const pages: string[] = [];
        for (let i = 1; i <= pdf.numPages; i++) {
            const page = await pdf.getPage(i);
            const content = await page.getTextContent();
            const text = content.items.map((item: any) => item.str).join(' ');
            if (text.trim()) pages.push(text);
        }
        return pages.join('\n\n');
    }, []);

    const extractFromImage = useCallback(async (file: File): Promise<string> => {
        const token = await getToken({ skipCache: true });
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/explain/extract-image`, {
            method: 'POST',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: formData,
        });
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.detail || 'Extraction failed');
        }
        const data = await res.json();
        return data.text || '';
    }, [getToken]);

    const handleFile = useCallback(async (file: File) => {
        setUploadError('');

        // Double-check Pro gate (frontend)
        if (plan !== 'pro') {
            setShowUpgradeModal(true);
            return;
        }

        if (!ALLOWED_TYPES.includes(file.type)) {
            setUploadState('error');
            setUploadError('Please upload a PDF or image file (JPG, PNG).');
            return;
        }
        if (file.size > MAX_FILE_SIZE) {
            setUploadState('error');
            setUploadError('File too large. Maximum size is 10MB.');
            return;
        }

        setUploadState('uploading');
        setExtractedFileName(file.name);

        try {
            let text: string;
            if (file.type === 'application/pdf') {
                text = await extractFromPdf(file);
            } else {
                text = await extractFromImage(file);
            }

            if (!text.trim()) {
                setUploadState('error');
                setUploadError('Could not extract text. Please paste your report manually.');
                return;
            }

            setExtractedText(text);
            setUploadState('preview');
        } catch {
            setUploadState('error');
            setUploadError('Could not extract text. Please paste your report manually.');
        }
    }, [extractFromPdf, extractFromImage, plan]);

    const handleDrop = useCallback((e: DragEvent) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
    }, [handleFile]);

    const handleUseText = () => {
        setReportText(extractedText);
        setUploadState('idle');
        setExtractedText('');
        setExtractedFileName('');
    };

    const handleUploadReset = () => {
        setUploadState('idle');
        setExtractedText('');
        setExtractedFileName('');
        setUploadError('');
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        if (isRunningRef.current) return;
        isRunningRef.current = true;
        setOutput(''); setSources([]); setError(''); setStatusMsg(''); setLoading(true); setPhiError(null);
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
                onopen: makeOnOpen({
                    onPhiBlocked: (detail, suggestion) => setPhiError({ detail, suggestion }),
                    onLimitReached: () => setShowUpgradeModal(true),
                }),
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
                onerror: sseOnError,
            });
        } catch (err: any) {
            controller.abort(); setLoading(false); setStatusMsg('');
            setError(err instanceof Error ? err.message : 'Unknown error.');
        } finally { isRunningRef.current = false; }
    }

    const handleReset = () => {
        setReportText(''); setOutput(''); setSources([]); setError(''); setStatusMsg(''); setPhiError(null);
        handleUploadReset();
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

            {/* Language box */}
            <div className="rounded-xl p-4 text-sm mb-6" style={{ background: 'rgba(74,222,128,0.05)', border: '1px solid rgba(74,222,128,0.3)' }}>
                <p style={{ color: 'rgba(74,222,128,0.9)' }}>
                    <span className="font-semibold">Ask in any language</span> — explained with LOINC, RxNorm &amp; MedlinePlus.
                </p>
            </div>

            {phiError && !loading && (
                <PHIWarning detail={phiError.detail} suggestion={phiError.suggestion} onDismiss={() => setPhiError(null)} />
            )}

            {error && (
                <div className="mb-5 p-3 rounded-lg border text-sm" style={{ background: "rgba(252,129,129,0.12)", borderColor: "rgba(252,129,129,0.3)", color: "#fc8181" }}>{error}</div>
            )}

            <form onSubmit={handleSubmit} className="rounded-xl p-6 space-y-5" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>
                <div className="space-y-2">
                    <label htmlFor="report" className="block text-sm font-medium" style={{ color: "rgba(255,255,255,0.8)" }}>
                        Medical Report / Lab Results
                    </label>

                    {/* Upload area */}
                    {!output && (
                        <>
                            {uploadState === 'idle' && (
                                <>
                                    {plan === 'pro' ? (
                                        <div
                                            className="rounded-lg p-6 text-center cursor-pointer transition-all"
                                            style={{
                                                border: `2px dashed ${dragOver ? 'rgba(74,222,128,0.7)' : 'rgba(74,222,128,0.4)'}`,
                                                background: dragOver ? 'rgba(74,222,128,0.1)' : 'rgba(74,222,128,0.05)',
                                            }}
                                            onClick={() => fileInputRef.current?.click()}
                                            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                                            onDragLeave={() => setDragOver(false)}
                                            onDrop={handleDrop}
                                        >
                                            <input
                                                ref={fileInputRef}
                                                type="file"
                                                accept=".pdf,image/jpeg,image/png,image/webp"
                                                className="hidden"
                                                onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
                                            />
                                            <div className="text-2xl mb-2" style={{ opacity: 0.7 }}>📄</div>
                                            <p className="text-sm font-medium" style={{ color: 'rgba(74,222,128,0.9)' }}>Upload Report</p>
                                            <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>PDF or image (JPG, PNG) · Max 10MB</p>
                                        </div>
                                    ) : (
                                        <div
                                            className="rounded-lg p-6 text-center transition-all cursor-not-allowed"
                                            style={{
                                                border: '2px dashed rgba(255,255,255,0.15)',
                                                background: 'rgba(255,255,255,0.03)',
                                                opacity: 0.6,
                                            }}
                                            onClick={() => setShowUpgradeModal(true)}
                                        >
                                            <div className="text-2xl mb-2" style={{ opacity: 0.4 }}>📄</div>
                                            <p className="text-sm font-medium" style={{ color: 'rgba(255,255,255,0.5)' }}>Upload Report</p>
                                            <p className="text-xs mt-1" style={{ color: '#ff8e6e' }}>
                                                PDF &amp; image upload is a Pro feature. Upgrade to unlock.
                                            </p>
                                        </div>
                                    )}
                                    <p className="text-xs text-center py-1" style={{ color: 'rgba(255,255,255,0.3)' }}>
                                        ─── or paste text below ───
                                    </p>
                                </>
                            )}

                            {uploadState === 'uploading' && (
                                <div className="rounded-lg p-6 text-center" style={{ border: '2px dashed rgba(74,222,128,0.4)', background: 'rgba(74,222,128,0.05)' }}>
                                    <div className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin mx-auto mb-2" style={{ borderColor: 'rgba(74,222,128,0.6)', borderTopColor: 'transparent' }} />
                                    <p className="text-sm" style={{ color: 'rgba(74,222,128,0.9)' }}>Extracting text...</p>
                                </div>
                            )}

                            {uploadState === 'error' && (
                                <div className="rounded-lg p-4 text-center" style={{ border: '2px dashed rgba(252,129,129,0.4)', background: 'rgba(252,129,129,0.05)' }}>
                                    <p className="text-sm mb-3" style={{ color: '#fc8181' }}>{uploadError}</p>
                                    <button
                                        type="button"
                                        onClick={handleUploadReset}
                                        className="text-xs px-3 py-1 rounded-lg transition-all"
                                        style={{ border: '1px solid rgba(255,255,255,0.3)', color: 'rgba(255,255,255,0.7)' }}
                                    >
                                        Try Again
                                    </button>
                                </div>
                            )}

                            {uploadState === 'preview' && (
                                <div className="rounded-lg p-4 space-y-3" style={{ border: '1px solid rgba(74,222,128,0.3)', background: 'rgba(74,222,128,0.05)' }}>
                                    <div>
                                        <p className="text-sm font-medium" style={{ color: 'rgba(74,222,128,0.9)' }}>
                                            ✅ Text extracted from {extractedFileName}
                                        </p>
                                        <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.5)' }}>
                                            Please review before submitting — check numbers carefully.
                                        </p>
                                    </div>
                                    <textarea
                                        rows={6}
                                        value={extractedText}
                                        onChange={e => setExtractedText(e.target.value)}
                                        className="w-full px-3 py-2 rounded-lg font-mono text-xs focus:outline-none focus:ring-2"
                                        style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.85)', minHeight: '120px' }}
                                    />
                                    <p className="text-xs" style={{ color: 'rgba(251,191,36,0.7)' }}>
                                        ⚠️ Image quality may affect accuracy. Verify all numbers before submitting.
                                    </p>
                                    <div className="flex gap-3">
                                        <button
                                            type="button"
                                            onClick={handleUseText}
                                            className="px-4 py-2 text-sm font-medium rounded-lg transition-opacity text-white"
                                            style={{ background: ACCENT }}
                                        >
                                            Use This Text
                                        </button>
                                        <button
                                            type="button"
                                            onClick={handleUploadReset}
                                            className="px-4 py-2 text-sm rounded-lg transition-all"
                                            style={{ border: '1px solid rgba(255,255,255,0.3)', color: 'rgba(255,255,255,0.7)', background: 'transparent' }}
                                            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.1)'; }}
                                            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                                        >
                                            Upload Different File
                                        </button>
                                    </div>
                                </div>
                            )}
                        </>
                    )}

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
                ⚠️ Explanations are for reference only. Always consult your doctor for medical advice.
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
        <PageShell activePage="explain">
            <ExplainForm />
        </PageShell>
    );
}
