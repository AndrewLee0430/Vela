"use client"

import { useState, useEffect, FormEvent, useRef, useCallback, DragEvent } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { useAuth, useUser } from '@clerk/nextjs';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { FatalError, makeOnOpen, sseOnError } from '../utils/sse';
import FeedbackBar from '../components/FeedbackBar';
import { useShareContext } from '../contexts/ShareContext';
import Toast from '../components/Toast';
import PHIWarning from '../components/PHIWarning';
import UpgradeModal from '../components/UpgradeModal';
import ProFeatureOverlay from '../components/ProFeatureOverlay';
import PageShell from '../components/PageShell';
import ExplainLockedForAnonymous from '../components/ExplainLockedForAnonymous';
import ExplainItemCard, { ExplainItem } from '../components/ExplainItemCard';
import ClinicalCorrelationCard, { ClinicalCorrelation } from '../components/ClinicalCorrelationCard';
import { setQueryId, track } from '../utils/analytics';
import { Info } from 'lucide-react';
import { useLang } from '../utils/LangContext';
import {
  getUI,
  getLoincTooltip as getLoincTooltipI18n,
  getRxnormTooltip as getRxnormTooltipI18n,
  getMedlineplusTooltip as getMedlineplusTooltipI18n,
  getFdaTooltip as getFdaTooltipI18n,
  type UITranslations,
} from '../utils/i18n-ui';
import { getExtra } from '../utils/i18n-extra';

interface ExplainSource {
    source_type: string;
    label: string;
    url?: string;
    description?: string;
}

interface ExplainResponse {
    items: ExplainItem[];
    clinical_correlations: ClinicalCorrelation[];
    disclaimer: string;
}

const SOURCE_STYLES: Record<string, { bg: string; text: string; border: string }> = {
    LOINC:       { bg: 'rgba(99,179,237,0.12)',   text: '#63b3ed', border: 'rgba(99,179,237,0.3)'   },
    MedlinePlus: { bg: 'rgba(104,211,145,0.12)', text: '#68d391', border: 'rgba(104,211,145,0.3)' },
    FDA:         { bg: 'rgba(252,129,129,0.12)', text: '#fc8181', border: 'rgba(252,129,129,0.3)' },
    RxNorm:      { bg: 'rgba(183,148,244,0.12)', text: '#b794f4', border: 'rgba(183,148,244,0.3)' },
};

// Generic error UX (2026-04-29): SSE pipeline error_code → i18n key.
// `error` state holds either an error_code from this map (resolved by
// resolveErrorMessage), a transport code (already resolved to a string at
// the catch site via sseMsg lookup), or a raw fallback string.
const ERROR_KEY_MAP: Record<string, keyof UITranslations> = {
    empty_input: 'explainErrorEmptyInput',
    no_values_in_input: 'explainErrorNoValues',
    input_too_long: 'explainErrorInputTooLong',
    openai_api_error: 'explainErrorService',
    schema_validation_failed: 'explainErrorSchemaValidation',
    output_truncated: 'explainErrorTruncated',
    generic: 'explainErrorGeneric',
};

function resolveErrorMessage(error: string, ui: UITranslations): string {
    if (!error) return '';
    const i18nKey = ERROR_KEY_MAP[error];
    if (i18nKey) return ui[i18nKey] as string;
    return error;
}

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
    const { lang } = useLang();

    if (source.source_type === 'LOINC') {
        return <LoincBadge source={source} index={index} />;
    }

    // Bug 2 fix (2026-04-29): non-LOINC pills previously had NO tooltip.
    // Add entity-substituted hover tooltip via HTML title attribute.
    let tooltip = '';
    if (source.source_type === 'RxNorm') tooltip = getRxnormTooltipI18n(lang, source.label);
    else if (source.source_type === 'MedlinePlus') tooltip = getMedlineplusTooltipI18n(lang, source.label);
    else if (source.source_type === 'FDA') tooltip = getFdaTooltipI18n(lang, source.label);

    if (url) {
        return (
            <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                title={tooltip}
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
            title={tooltip}
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
    const { isSignedIn, isLoaded } = useUser();
    const { lang } = useLang();
    const ui = getUI(lang);
    const extra = getExtra(lang);
    const router = useRouter();
    const prefillConsumedRef = useRef(false);
    const [reportText, setReportText] = useState('');
    const [result, setResult]         = useState<ExplainResponse | null>(null);
    const [sources, setSources]       = useState<ExplainSource[]>([]);
    const [loading, setLoading]       = useState(false);
    const [statusMsg, setStatusMsg]   = useState('');
    const [error, setError]           = useState('');
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    const [showDailyCapToast, setShowDailyCapToast] = useState(false);
    const [phiError, setPhiError] = useState<{detail: string; suggestion: string} | null>(null);
    const [localQueryId, setLocalQueryId] = useState<string | null>(null);
    const isRunningRef = useRef(false);
    const { setShareData, clearShareData } = useShareContext();

    // PRD § 4.5 UX polish 2/3 — Navbar Share button via ShareContext.
    useEffect(() => {
        if (loading) {
            clearShareData();
            return;
        }
        if (!error && result && localQueryId && reportText) {
            setShareData({
                queryId: localQueryId,
                queryText: reportText,
                answerText: JSON.stringify(result, null, 2),
                citations: (sources ?? []).map(s => ({
                    title: (s as { title?: string | null }).title ?? null,
                    url: (s as { url?: string | null }).url ?? null,
                    text: null,
                })),
                feature: 'explain',
            });
        }
    }, [loading, error, result, localQueryId, reportText, sources, setShareData, clearShareData]);

    useEffect(() => {
        return () => clearShareData();
    }, [clearShareData]);

    // Cross-page ?prefill= receiver — prefill the report textarea, no auto-submit.
    // Declared above the isLoaded/!isSignedIn early-return so hook order stays legal;
    // fires regardless of the anon lock (state is harmlessly set behind it).
    useEffect(() => {
        if (!router.isReady) return;
        if (prefillConsumedRef.current) return;
        const raw = router.query.prefill;
        const v = Array.isArray(raw) ? raw[0] : raw;
        if (typeof v !== 'string') return;
        const trimmed = v.trim();
        if (!trimmed) return;
        prefillConsumedRef.current = true;
        setReportText(trimmed);
        router.replace('/explain', undefined, { shallow: true });
    }, [router]);
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
        // Generic error UX (2026-04-29): preemptive length check so we never
        // hit the pydantic 422 path. Backend pre-stream check is defense-in-
        // depth for any caller that bypasses this client check.
        if (reportText.length > 5000) {
            setError('input_too_long');
            track('explain_failed', { error_code: 'input_too_long', elapsed_ms: 0 });
            return;
        }
        isRunningRef.current = true;
        const t0 = Date.now();
        let detectedLang: string | null = null;
        const computeRiskDist = (r: ExplainResponse) => {
            const dist: Record<'green' | 'yellow' | 'red', number> = { green: 0, yellow: 0, red: 0 };
            for (const item of r.items) dist[item.risk_tier]++;
            for (const corr of r.clinical_correlations) dist[corr.risk_tier]++;
            return dist;
        };
        setResult(null); setSources([]); setError(''); setStatusMsg(''); setLoading(true); setPhiError(null);
        setQueryId(null);
        setLocalQueryId(null);
        const controller = new AbortController();
        try {
            const jwt = await getToken({ skipCache: true });
            if (!jwt) { setError('Authentication required.'); setLoading(false); isRunningRef.current = false; return; }
            await fetchEventSource(`${process.env.NEXT_PUBLIC_API_URL}/api/explain`, {
                signal: controller.signal, method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${jwt}` },
                body: JSON.stringify({ report_text: reportText, response_language: lang }),
                openWhenHidden: true,
                onopen: makeOnOpen({
                    onPhiBlocked: () => setPhiError({ detail: ui.phiDetail, suggestion: ui.phiSuggestion }),
                    onLimitReached: () => setShowUpgradeModal(true),
                }),
                onmessage(ev) {
                    if (!ev.data || ev.data.trim() === '') return;
                    try {
                        const data = JSON.parse(ev.data);
                        if (data.type === 'query_id') {
                            if (data.query_id) {
                                setQueryId(data.query_id);
                                setLocalQueryId(data.query_id);
                            }
                        }
                        else if (data.type === 'identified') {
                            if (typeof data.language === 'string') detectedLang = data.language;
                            // Note: data.items[] is also available here (entities extracted
                            // by backend Stage 1) but intentionally unused — Step 6 scope
                            // is telemetry only, not mid-flight UX.
                        }
                        else if (data.type === 'status') {
                            const statusMap: Record<string, string> = {
                                'Analyzing your report...': ui.statusAnalyzingReport,
                                'Looking up verified sources...': ui.statusLookingUp,
                                'Generating explanation...': ui.statusGenerating,
                            };
                            setStatusMsg(statusMap[data.content] || data.content);
                        }
                        else if (data.type === 'sources') setSources(data.content ?? []);
                        else if (data.type === 'explain_result') {
                            if (data.content) {
                                const result: ExplainResponse = data.content;
                                setResult(result);
                                track('explain_completed', {
                                    items_count: result.items.length,
                                    correlations_count: result.clinical_correlations.length,
                                    risk_tier_distribution: computeRiskDist(result),
                                    input_language: detectedLang,
                                    elapsed_ms: Date.now() - t0,
                                });
                            }
                        }
                        else if (data.type === 'done')    { setLoading(false); setStatusMsg(''); }
                        else if (data.type === 'error') {
                            const code = data.code ?? data.error ?? 'generic';
                            if (code === 'limit_reached') {
                                setShowUpgradeModal(true);
                            } else if (code === 'daily_cap_reached') {
                                setShowDailyCapToast(true);
                            } else {
                                // Generic error UX (2026-04-29): store the
                                // error_code; resolveErrorMessage maps it to
                                // an i18n string at render time.
                                setError(code);
                                track('explain_failed', {
                                    error_code: code,
                                    elapsed_ms: Date.now() - t0,
                                });
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
        setReportText(''); setResult(null); setSources([]); setError(''); setStatusMsg(''); setPhiError(null);
        setQueryId(null);
        setLocalQueryId(null);
        handleUploadReset();
    };

    const sampleQueries = [
        "eGFR 45 mL/min (ref >60), HbA1c 7.8%, Metformin 1000mg BID",
        "血紅素 10.2 g/dL（參考值 12-16）、白血球 12,500/μL（偏高）",
        "膽固醇 240 mg/dL（偏高）、三酸甘油酯 180 mg/dL、高密度脂蛋白 38 mg/dL（偏低）",
        "Glucosa en ayunas 156 mg/dL (ref 70-110), HbA1c 8.2%",
        "Sodium 138, Potassium 3.3 (LOW), Creatinine 1.5 (HIGH), Glucose 142 (HIGH)",
    ];

    if (isLoaded && !isSignedIn) {
        return <ExplainLockedForAnonymous />;
    }

    return (
        <div className="container mx-auto px-4 py-8 max-w-3xl">
            <div className="flex justify-between items-start mb-6">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: "rgb(var(--color-text))" }}>{ui.explainTitle}</h1>
                    <p className="text-sm mt-1" style={{ color: "rgb(var(--color-text) / 0.5)" }}>{ui.explainSubtitle}</p>
                </div>
                {(result || reportText) && (
                    <button onClick={handleReset} className="text-sm font-medium px-3 py-1 rounded-lg transition-all mt-1"
                        style={{ background: 'transparent', border: '1px solid rgb(var(--color-text) / 0.3)', color: 'rgb(var(--color-text) / 0.7)' }}
                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgb(var(--color-text) / 0.1)'; }}
                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}>
                        {ui.newBtn}
                    </button>
                )}
            </div>

            {/* Language box */}
            <div className="rounded-xl p-4 text-sm mb-6 bg-text/5 border border-text/12">
                <p className="text-text/85">
                    <span className="font-semibold">{ui.explainInfoBox}</span>
                </p>
            </div>

            {phiError && !loading && (
                <PHIWarning detail={phiError.detail} suggestion={phiError.suggestion} onDismiss={() => setPhiError(null)} />
            )}

            {error && (
                <div className="mb-5 p-3 rounded-lg border text-sm" style={{ background: "rgb(var(--color-danger) / 0.12)", borderColor: "rgb(var(--color-danger) / 0.3)", color: "rgb(var(--color-danger-soft))" }}>{resolveErrorMessage(error, ui)}</div>
            )}

            <form onSubmit={handleSubmit} className="rounded-xl p-6 space-y-5" style={{ background: "rgb(var(--color-text) / 0.06)", border: "1px solid rgb(var(--color-text) / 0.1)" }}>
                <div className="space-y-2">
                    <label htmlFor="report" className="block text-sm font-medium" style={{ color: "rgb(var(--color-text) / 0.8)" }}>
                        {ui.reportLabel}
                    </label>

                    {/* Upload area */}
                    {!result && (
                        <>
                            {uploadState === 'idle' && (
                                <>
                                    <ProFeatureOverlay isLocked={plan !== 'pro'} featureName={extra.proFeatPdfUpload}>
                                        <div
                                            className="rounded-lg p-6 text-center cursor-pointer transition-all"
                                            style={{
                                                border: `2px dashed ${dragOver ? 'rgb(var(--color-text) / 0.4)' : 'rgb(var(--color-text) / 0.2)'}`,
                                                background: dragOver ? 'rgb(var(--color-text) / 0.08)' : 'rgb(var(--color-text) / 0.04)',
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
                                            <p className="text-sm font-medium text-text/85">{ui.uploadReport}</p>
                                            <p className="text-xs mt-1" style={{ color: 'rgb(var(--color-text) / 0.4)' }}>{ui.uploadHint}</p>
                                        </div>
                                    </ProFeatureOverlay>
                                    <p className="text-xs text-center py-1" style={{ color: 'rgb(var(--color-text) / 0.3)' }}>
                                        ─── {ui.pasteBelow} ───
                                    </p>
                                </>
                            )}

                            {uploadState === 'uploading' && (
                                <div className="rounded-lg p-6 text-center" style={{ border: '2px dashed rgb(var(--color-text) / 0.2)', background: 'rgb(var(--color-text) / 0.04)' }}>
                                    <div className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin mx-auto mb-2" style={{ borderColor: 'rgb(var(--color-brand) / 0.6)', borderTopColor: 'transparent' }} />
                                    <p className="text-sm text-text/85">{ui.extractingText}</p>
                                </div>
                            )}

                            {uploadState === 'error' && (
                                <div className="rounded-lg p-4 text-center" style={{ border: '2px dashed rgb(var(--color-danger) / 0.4)', background: 'rgb(var(--color-danger) / 0.05)' }}>
                                    <p className="text-sm mb-3" style={{ color: 'rgb(var(--color-danger-soft))' }}>{uploadError}</p>
                                    <button
                                        type="button"
                                        onClick={handleUploadReset}
                                        className="text-xs px-3 py-1 rounded-lg transition-all"
                                        style={{ border: '1px solid rgb(var(--color-text) / 0.3)', color: 'rgb(var(--color-text) / 0.7)' }}
                                    >
                                        {ui.tryAgainBtn}
                                    </button>
                                </div>
                            )}

                            {uploadState === 'preview' && (
                                <div className="rounded-lg p-4 space-y-3" style={{ border: '1px solid rgb(var(--color-text) / 0.15)', background: 'rgb(var(--color-text) / 0.05)' }}>
                                    <div>
                                        <p className="text-sm font-medium text-text/85">
                                            ✅ {ui.textExtractedFrom} {extractedFileName}
                                        </p>
                                        <p className="text-xs mt-1" style={{ color: 'rgb(var(--color-text) / 0.5)' }}>
                                            {ui.reviewBeforeSubmit}
                                        </p>
                                    </div>
                                    <textarea
                                        rows={6}
                                        value={extractedText}
                                        onChange={e => setExtractedText(e.target.value)}
                                        className="w-full px-3 py-2 rounded-lg font-mono text-xs focus:outline-none focus:ring-2"
                                        style={{ background: 'rgb(var(--color-text) / 0.05)', border: '1px solid rgb(var(--color-text) / 0.15)', color: 'rgb(var(--color-text) / 0.85)', minHeight: '120px' }}
                                    />
                                    <p className="text-xs" style={{ color: 'rgb(var(--color-warning) / 0.7)' }}>
                                        ⚠️ {ui.imageQualityWarning}
                                    </p>
                                    <div className="flex gap-3">
                                        <button
                                            type="button"
                                            onClick={handleUseText}
                                            className="px-4 py-2 text-sm font-medium rounded-lg transition-opacity text-white"
                                            style={{ background: 'rgb(var(--color-brand))' }}
                                        >
                                            {ui.useThisText}
                                        </button>
                                        <button
                                            type="button"
                                            onClick={handleUploadReset}
                                            className="px-4 py-2 text-sm rounded-lg transition-all"
                                            style={{ border: '1px solid rgb(var(--color-text) / 0.3)', color: 'rgb(var(--color-text) / 0.7)', background: 'transparent' }}
                                            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgb(var(--color-text) / 0.1)'; }}
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
                    {!result && (
                        <div className="flex flex-wrap gap-2 pb-1">
                            {sampleQueries.map((s, i) => (
                                <button
                                    key={i}
                                    type="button"
                                    onClick={() => setReportText(s)}
                                    disabled={loading}
                                    className="px-3 py-1.5 text-xs rounded-full disabled:opacity-50 transition-all duration-200"
                                    style={{ background: "rgb(var(--color-text) / 0.06)", border: "1px solid rgb(var(--color-text) / 0.15)", color: "rgb(var(--color-text) / 0.7)" }}
                                    onMouseEnter={e => {
                                        (e.currentTarget as HTMLElement).style.borderColor = "rgb(var(--color-text) / 0.3)";
                                        (e.currentTarget as HTMLElement).style.background = "rgb(var(--color-text) / 0.12)";
                                    }}
                                    onMouseLeave={e => {
                                        (e.currentTarget as HTMLElement).style.borderColor = "rgb(var(--color-text) / 0.15)";
                                        (e.currentTarget as HTMLElement).style.background = "rgb(var(--color-text) / 0.06)";
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
                        className="w-full px-4 py-3 rounded-lg focus:outline-none focus:ring-2 disabled:opacity-60 font-mono text-sm" style={{ background: "rgb(var(--color-text) / 0.05)", border: "1px solid rgb(var(--color-text) / 0.15)", color: "rgb(var(--color-text) / 0.85)" }}
                        placeholder={ui.explainPlaceholder}
                    />
                </div>
                <button
                    type="submit" disabled={loading || !reportText.trim()}
                    className="w-full text-white font-medium py-2.5 px-6 rounded-lg transition-opacity disabled:opacity-50 text-sm"
                    style={{ background: 'rgb(var(--color-brand))' }}
                >
                    {loading ? (
                        <span className="flex items-center justify-center gap-2">
                            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            {statusMsg || ui.processingBtn}
                        </span>
                    ) : ui.explainBtn}
                </button>
            </form>

            {loading && statusMsg === ui.statusGenerating && (
                <p className="text-xs mt-2 text-center" style={{ color: "rgb(var(--color-text) / 0.4)" }}>
                    {ui.statusGeneratingHint}
                </p>
            )}

            {result && (
            <p className="text-xs mt-3 text-center" style={{ color: "rgb(var(--color-text) / 0.35)" }}>
                {result.disclaimer}
            </p>
            )}

            {sources.length > 0 && (
                <div className="mt-5 rounded-xl p-5" style={{ background: "rgb(var(--color-text) / 0.06)", border: "1px solid rgb(var(--color-text) / 0.1)" }}>
                    <p className="text-xs font-semibold text-text/50 uppercase tracking-wider mb-3">{ui.verifiedSources}</p>
                    <div className="flex flex-wrap gap-2">
                        {sources.map((src, i) => <SourceBadge key={i} source={src} index={i} />)}
                    </div>
                    {/* Citation-scope transparency banner (2026-04-29 Path 1 RAG defense). Explains
                        that explanation body is general medical knowledge while citations are limited
                        to verified authoritative sources — preempts "Vela has weak sources" misread. */}
                    <div className="mt-3 flex items-start gap-2 text-xs leading-relaxed" style={{ color: "rgb(var(--color-text) / 0.35)" }}>
                        <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" aria-hidden="true" />
                        <p>{ui.citationScopeBanner}</p>
                    </div>
                </div>
            )}

            {result && (
                <section className="mt-5 rounded-xl p-6" style={{ background: "rgb(var(--color-text) / 0.06)", border: "1px solid rgb(var(--color-text) / 0.1)" }}>
                    <div className="mb-4">
                        <h2 className="text-base font-semibold" style={{ color: "rgb(var(--color-text))" }}>{ui.explanation}</h2>
                    </div>

                    {/* Per-item / per-correlation citation strips removed (Bug X2/X3, 2026-04-29):
                        the page-level "已驗證來源" section above is the single source of truth
                        for retrieved citations. LLM-emitted citation labels could be verbose
                        (e.g. "eGFR — value: 45 mL/min (reference: >60)") and duplicated the
                        page-level pills, which is noisy UX. */}
                    {result.items.map((item, i) => (
                        <ExplainItemCard key={`item-${i}`} item={item} />
                    ))}

                    {result.clinical_correlations.length > 0 && (
                        <div className="mt-6">
                            <p className="text-xs font-semibold text-text/50 uppercase tracking-wider mb-3">
                                {ui.clinicalCorrelations}
                            </p>
                            {result.clinical_correlations.map((corr, i) => (
                                <ClinicalCorrelationCard key={`corr-${i}`} correlation={corr} />
                            ))}
                        </div>
                    )}

                    <FeedbackBar query={reportText} response={JSON.stringify(result, null, 2)} category="explain" />
                </section>
            )}

            <div className="mt-8 border-t pt-6 space-y-2 text-xs" style={{ borderColor: "rgb(var(--color-text) / 0.15)", color: "rgb(var(--color-text) / 0.4)" }}>
                <p className="font-medium" style={{ color: "rgb(var(--color-text) / 0.6)" }}>{ui.dataSourcesTitle}</p>
                <p dangerouslySetInnerHTML={{ __html: ui.explainAttr1 }} />
                <p dangerouslySetInnerHTML={{ __html: ui.explainAttr2 }} />
                <p dangerouslySetInnerHTML={{ __html: ui.explainAttr3 }} />
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
        </div>
    );
}

export default function Explain() {
    return (
        <PageShell
            activePage="explain"
            allowAnonymous
            extraHead={
                <Head>
                    <meta name="robots" content="noindex, nofollow" />
                </Head>
            }
        >
            <ExplainForm />
        </PageShell>
    );
}
