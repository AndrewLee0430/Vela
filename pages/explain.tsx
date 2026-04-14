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
import ProFeatureOverlay from '../components/ProFeatureOverlay';
import PageShell from '../components/PageShell';
import { useLang } from '../utils/LangContext';
import { getUI, getLoincTooltip as getLoincTooltipI18n } from '../utils/i18n-ui';
import { getExtra } from '../utils/i18n-extra';

const ACCENT = '#68d391';

const EXPLAIN_DISCLAIMER_RE = /\n*⚠️?\s*(This explanation|For reference purposes|本說明|本解释|この説明|이 설명|Esta explicación|Cette explication|Diese Erklärung|Questa spiegazione|Esta explicação|คำอธิบายนี้|هذا الشرح|यह व्याख्या|এই ব্যাখ্যা|הסבר זה|Giải thích này|Please consult|does not replace|僅供參考|仅供参考).*$/gm;

function stripExplainDisclaimer(text: string): string {
    return text.replace(EXPLAIN_DISCLAIMER_RE, '').trim();
}

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

function getSourceUrl(source: ExplainSource): string | null {
    // Use backend-provided URL if available (MedlinePlus articles, DailyMed)
    if (source.url) return source.url;

    // LOINC: no clickable link (public pages require login)
    if (source.source_type === 'LOINC') return null;

    if (source.source_type === 'RxNorm') {
        const match = source.label.match(/RxNorm\s+(.+)/i);
        if (match) return `https://mor.nlm.nih.gov/RxNav/search?searchBy=String&searchTerm=${encodeURIComponent(match[1].trim())}`;
    }
    return null;
}

function useLoincTooltip(label: string): string {
    const { lang } = useLang();
    return getLoincTooltipI18n(lang, label);
}

function LoincBadge({ source, index = 0 }: { source: ExplainSource; index?: number }) {
    const s = SOURCE_STYLES['LOINC'];
    const [show, setShow] = useState(false);
    const wrapperRef = useRef<HTMLSpanElement>(null);
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const tip = useLoincTooltip(source.label);

    useEffect(() => {
        if (!show) return;
        function handleClick(e: MouseEvent) {
            if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
                setShow(false);
            }
        }
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [show]);

    return (
        <span
            ref={wrapperRef}
            className="relative inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium cursor-default"
            style={{ background: s.bg, color: s.text, border: `1px solid ${s.border}` }}
            onMouseEnter={() => {
                if (timerRef.current) clearTimeout(timerRef.current);
                timerRef.current = setTimeout(() => setShow(true), 200);
            }}
            onMouseLeave={() => {
                if (timerRef.current) clearTimeout(timerRef.current);
                timerRef.current = setTimeout(() => setShow(false), 150);
            }}
            onClick={(e) => { e.stopPropagation(); setShow(prev => !prev); }}
        >
            {source.label}
            {/* Popover */}
            <span
                className={`absolute bottom-full z-50 ${index === 0 ? 'left-0' : 'left-1/2'}`}
                style={{
                    transform: `${index === 0 ? '' : 'translateX(-50%) '}translateY(${show ? '0' : '4px'})`,
                    opacity: show ? 1 : 0,
                    pointerEvents: show ? 'auto' : 'none',
                    transition: 'opacity 200ms, transform 200ms',
                    marginBottom: '8px',
                }}
            >
                <span
                    className="block rounded-lg shadow-lg px-3 py-2 text-xs leading-relaxed min-w-[250px] max-w-[300px]"
                    style={{ background: '#1e293b', border: '1px solid #475569', color: '#e2e8f0', whiteSpace: 'normal' }}
                >
                    {tip}
                </span>
                {/* Arrow */}
                <span
                    className={`absolute ${index === 0 ? 'left-4' : 'left-1/2'}`}
                    style={{ transform: index === 0 ? '' : 'translateX(-50%)', top: '100%', marginTop: '-1px' }}
                >
                    <span style={{
                        display: 'block', width: 0, height: 0,
                        borderLeft: '6px solid transparent',
                        borderRight: '6px solid transparent',
                        borderTop: '6px solid #475569',
                    }} />
                    <span className="absolute left-1/2" style={{
                        transform: 'translateX(-50%)', top: '-7px',
                        width: 0, height: 0,
                        borderLeft: '5px solid transparent',
                        borderRight: '5px solid transparent',
                        borderTop: '5px solid #1e293b',
                    }} />
                </span>
            </span>
        </span>
    );
}

function SourceBadge({ source, index = 0 }: { source: ExplainSource; index?: number }) {
    const s = SOURCE_STYLES[source.source_type] ?? SOURCE_STYLES['MedlinePlus'];
    const url = getSourceUrl(source);

    if (source.source_type === 'LOINC') {
        return <LoincBadge source={source} index={index} />;
    }

    if (url) {
        return (
            <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition-opacity hover:opacity-80"
                style={{ background: s.bg, color: s.text, border: `1px solid ${s.border}` }}
            >
                {source.label}
                <span className="text-[10px] opacity-60">↗</span>
            </a>
        );
    }

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
    const { lang } = useLang();
    const ui = getUI(lang);
    const extra = getExtra(lang);
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
            if (data.type === 'pro_required') {
                throw Object.assign(new Error('pro_required'), { proRequired: true });
            }
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
            setUploadError(ui.uploadPdfOrImage);
            return;
        }
        if (file.size > MAX_FILE_SIZE) {
            setUploadState('error');
            setUploadError(ui.fileTooLarge);
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
                setUploadError(ui.couldNotExtract);
                return;
            }

            setExtractedText(text);
            setUploadState('preview');
        } catch (err: any) {
            if (err?.proRequired) {
                setUploadState('idle');
                setShowUpgradeModal(true);
            } else {
                setUploadState('error');
                setUploadError(ui.couldNotExtract);
            }
        }
    }, [extractFromPdf, extractFromImage, plan, ui]);

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
                    onPhiBlocked: () => setPhiError({ detail: ui.phiDetail, suggestion: ui.phiSuggestion }),
                    onLimitReached: () => setShowUpgradeModal(true),
                }),
                onmessage(ev) {
                    if (!ev.data || ev.data.trim() === '') return;
                    try {
                        const data = JSON.parse(ev.data);
                        if (data.type === 'status') {
                            const statusMap: Record<string, string> = {
                                'Analyzing your report...': ui.statusAnalyzingReport,
                                'Looking up verified sources...': ui.statusLookingUp,
                                'Generating explanation...': ui.statusGenerating,
                            };
                            setStatusMsg(statusMap[data.content] || data.content);
                        }
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
            const code = err?.code as string | undefined;
            const sseMsg: Record<string, string> = {
                session_expired: ui.sseSessionExpired,
                too_many_requests: ui.sseTooManyRequests,
                server_error: ui.sseServerError,
                connection_lost: ui.sseConnectionLost,
            };
            setError(code && sseMsg[code] ? sseMsg[code] : (err instanceof Error ? err.message : ui.sseConnectionLost));
        } finally { isRunningRef.current = false; }
    }

    const handleReset = () => {
        setReportText(''); setOutput(''); setSources([]); setError(''); setStatusMsg(''); setPhiError(null);
        handleUploadReset();
    };

    const sampleQueries = [
        "eGFR 45 mL/min (ref >60), HbA1c 7.8%, Metformin 1000mg BID",
        "血紅素 10.2 g/dL（參考值 12-16）、白血球 12,500/μL（偏高）",
        "GOT 68 U/L、GPT 92 U/L、總膽紅素 2.1 mg/dL",
        "Glucosa en ayunas 156 mg/dL (ref 70-110), HbA1c 8.2%",
        "Sodium 138, Potassium 3.3 (LOW), Creatinine 1.5 (HIGH), Glucose 142 (HIGH)",
    ];

    return (
        <div className="container mx-auto px-4 py-8 max-w-3xl">
            <div className="flex justify-between items-start mb-6">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "#ffffff" }}>{ui.explainTitle}</h1>
                    <p className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.5)" }}>{ui.explainSubtitle}</p>
                </div>
                {(output || reportText) && (
                    <button onClick={handleReset} className="text-sm font-medium px-3 py-1 rounded-lg transition-all mt-1"
                        style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.3)', color: 'rgba(255,255,255,0.7)' }}
                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.1)'; }}
                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}>
                        {ui.newBtn}
                    </button>
                )}
            </div>

            {/* Language box */}
            <div className="rounded-xl p-4 text-sm mb-6" style={{ background: 'rgba(74,222,128,0.05)', border: '1px solid rgba(74,222,128,0.3)' }}>
                <p style={{ color: 'rgba(74,222,128,0.9)' }}>
                    <span className="font-semibold">{ui.explainInfoBox}</span>
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
                        {ui.reportLabel}
                    </label>

                    {/* Upload area */}
                    {!output && (
                        <>
                            {uploadState === 'idle' && (
                                <>
                                    <ProFeatureOverlay isLocked={plan !== 'pro'} featureName={extra.proFeatPdfUpload}>
                                        <div
                                            className="rounded-lg p-6 text-center cursor-pointer transition-all"
                                            style={{
                                                border: `2px dashed ${dragOver ? 'rgba(74,222,128,0.7)' : 'rgba(74,222,128,0.4)'}`,
                                                background: dragOver ? 'rgba(74,222,128,0.1)' : 'rgba(74,222,128,0.05)',
                                            }}
                                            onClick={() => plan === 'pro' && fileInputRef.current?.click()}
                                            onDragOver={e => { if (plan === 'pro') { e.preventDefault(); setDragOver(true); } }}
                                            onDragLeave={() => setDragOver(false)}
                                            onDrop={plan === 'pro' ? handleDrop : undefined}
                                        >
                                            <input
                                                ref={fileInputRef}
                                                type="file"
                                                accept=".pdf,image/jpeg,image/png,image/webp"
                                                className="hidden"
                                                onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
                                            />
                                            <div className="text-2xl mb-2" style={{ opacity: 0.7 }}>📄</div>
                                            <p className="text-sm font-medium" style={{ color: 'rgba(74,222,128,0.9)' }}>{ui.uploadReport}</p>
                                            <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.4)' }}>{ui.uploadHint}</p>
                                        </div>
                                    </ProFeatureOverlay>
                                    <p className="text-xs text-center py-1" style={{ color: 'rgba(255,255,255,0.3)' }}>
                                        ─── {ui.pasteBelow} ───
                                    </p>
                                </>
                            )}

                            {uploadState === 'uploading' && (
                                <div className="rounded-lg p-6 text-center" style={{ border: '2px dashed rgba(74,222,128,0.4)', background: 'rgba(74,222,128,0.05)' }}>
                                    <div className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin mx-auto mb-2" style={{ borderColor: 'rgba(74,222,128,0.6)', borderTopColor: 'transparent' }} />
                                    <p className="text-sm" style={{ color: 'rgba(74,222,128,0.9)' }}>{ui.extractingText}</p>
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
                                        {ui.tryAgainBtn}
                                    </button>
                                </div>
                            )}

                            {uploadState === 'preview' && (
                                <div className="rounded-lg p-4 space-y-3" style={{ border: '1px solid rgba(74,222,128,0.3)', background: 'rgba(74,222,128,0.05)' }}>
                                    <div>
                                        <p className="text-sm font-medium" style={{ color: 'rgba(74,222,128,0.9)' }}>
                                            ✅ {ui.textExtractedFrom} {extractedFileName}
                                        </p>
                                        <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.5)' }}>
                                            {ui.reviewBeforeSubmit}
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
                                        ⚠️ {ui.imageQualityWarning}
                                    </p>
                                    <div className="flex gap-3">
                                        <button
                                            type="button"
                                            onClick={handleUseText}
                                            className="px-4 py-2 text-sm font-medium rounded-lg transition-opacity text-white"
                                            style={{ background: ACCENT }}
                                        >
                                            {ui.useThisText}
                                        </button>
                                        <button
                                            type="button"
                                            onClick={handleUploadReset}
                                            className="px-4 py-2 text-sm rounded-lg transition-all"
                                            style={{ border: '1px solid rgba(255,255,255,0.3)', color: 'rgba(255,255,255,0.7)', background: 'transparent' }}
                                            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.1)'; }}
                                            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                                        >
                                            {ui.uploadDifferentFile}
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
                        placeholder={ui.explainPlaceholder}
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
                            {statusMsg || ui.processingBtn}
                        </span>
                    ) : ui.explainBtn}
                </button>
            </form>

            {output && (
            <p className="text-xs mt-3 text-center" style={{ color: "rgba(255,255,255,0.35)" }}>
                {ui.explainDisclaimer}
            </p>
            )}

            {sources.length > 0 && (
                <div className="mt-5 rounded-xl p-5" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>
                    <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">{ui.verifiedSources}</p>
                    <div className="flex flex-wrap gap-2">
                        {sources.map((src, i) => <SourceBadge key={i} source={src} index={i} />)}
                    </div>
                </div>
            )}

            {output && (
                <section className="mt-5 rounded-xl p-6" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-base font-semibold" style={{ color: "#ffffff" }}>{ui.explanation}</h2>
                        <button onClick={() => { navigator.clipboard.writeText(output); setShowToast(true); }}
                            className="text-xs text-gray-400 hover:text-white transition-colors">
                            {ui.copyClipboard}
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
                        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{loading ? output : stripExplainDisclaimer(output)}</ReactMarkdown>
                    </div>
                    {loading && <span className="inline-block w-1.5 h-4 rounded-sm animate-pulse ml-0.5 mt-2" style={{ background: ACCENT }} />}
                    {!loading && !error && (
                        <FeedbackBar query={reportText} response={output} category="explain" />
                    )}
                </section>
            )}

            <div className="mt-8 border-t pt-6 space-y-2 text-xs" style={{ borderColor: "rgba(104,211,145,0.35)", color: "rgba(255,255,255,0.4)" }}>
                <p className="font-medium" style={{ color: "rgba(255,255,255,0.6)" }}>{ui.dataSourcesTitle}</p>
                <p dangerouslySetInnerHTML={{ __html: ui.explainAttr1 }} />
                <p dangerouslySetInnerHTML={{ __html: ui.explainAttr2 }} />
                <p dangerouslySetInnerHTML={{ __html: ui.explainAttr3 }} />
            </div>

            {showToast && <Toast message={ui.copiedToClipboard} onClose={() => setShowToast(false)} />}
            <UpgradeModal isOpen={showUpgradeModal} onClose={() => setShowUpgradeModal(false)} />
            {showDailyCapToast && (
                <Toast
                    message={ui.dailyCapToast}
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
