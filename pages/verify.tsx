"use client"

import { useState, FormEvent, useRef, useCallback } from 'react';
import Head from 'next/head';
import { useAuth, useUser } from '@clerk/nextjs';
import FeedbackBar from '../components/FeedbackBar';
import UpgradeModal from '../components/UpgradeModal';
import Toast from '../components/Toast';
import PHIWarning from '../components/PHIWarning';
import PageShell from '../components/PageShell';
import AnonymousUpgradeCTA from '../components/AnonymousUpgradeCTA';
import { setQueryId, getAnonFingerprint, track } from '../utils/analytics';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';
import { formatInteractionSummary, getSeverityLabel, getRiskLevelLabel } from '../utils/i18n-verify';

// Verify accent color
const ACCENT = '#63b3ed';

interface DrugInteraction {
    drug_pair: [string, string];
    severity: string;                 // canonical enum (Critical/Major/Moderate/Minor)
    severity_label?: string | null;   // localized display (e.g. "嚴重")
    description: string;
    clinical_recommendation: string;
    source: string;
    source_url?: string;
}

interface VerifyResponse {
    drugs_analyzed: string[];
    interactions: DrugInteraction[];
    summary: string;
    risk_level: string;
    risk_level_label?: string | null;
    response_language?: string | null;
    query_time_ms: number;
    disclaimer?: string;
    query_id?: string | null;
}

function VerifyForm() {
    const { getToken } = useAuth();
    const { isSignedIn } = useUser();
    const { lang } = useLang();
    const ui = getUI(lang);

    const [drugs, setDrugs]   = useState('');
    const [result, setResult] = useState<VerifyResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError]   = useState('');

    const isRunningRef = useRef(false);
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    const [showDailyCapToast, setShowDailyCapToast] = useState(false);
    const [anonNoticeMsg, setAnonNoticeMsg] = useState<string | null>(null);
    const [anonQuotaCta, setAnonQuotaCta] = useState<{ used: number; limit: number } | null>(null);
    const [showThirdQueryCta, setShowThirdQueryCta] = useState(false);
    const [phiError, setPhiError] = useState<{detail: string; suggestion: string} | null>(null);

    const handleReset = () => { setDrugs(''); setResult(null); setError(''); setPhiError(null); setQueryId(null); };

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

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        if (isRunningRef.current) return;

        const drugList = drugs.split('\n').map(d => d.trim()).filter(Boolean);
        if (drugList.length < 2) {
            setError(ui.enterTwoDrugs);
            return;
        }

        const t0 = Date.now();
        const computeSeverityDist = (interactions: DrugInteraction[]) => {
            const dist = { Critical: 0, Major: 0, Moderate: 0, Minor: 0 };
            for (const i of interactions) {
                if (i.severity in dist) {
                    dist[i.severity as keyof typeof dist]++;
                }
            }
            return dist;
        };

        isRunningRef.current = true;
        setLoading(true); setError(''); setResult(null); setPhiError(null);
        setQueryId(null);

        try {
            const headers: Record<string, string> = { 'Content-Type': 'application/json' };
            if (isSignedIn) {
                const token = await getToken({ skipCache: true });
                if (!token) { setError(ui.authRequired); return; }
                headers['Authorization'] = `Bearer ${token}`;
            } else {
                const fp = getAnonFingerprint();
                if (!fp) { setError('Session unavailable. Please refresh and try again.'); return; }
                headers['X-Anon-Fingerprint'] = fp;
                track('anonymous_query_submitted', { feature: 'verify', anon_id: fp });
            }

            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/verify`, {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    drugs: drugList,
                    patient_context: null,
                    response_language: lang,  // PRD § 2.9: align LLM output language with UI locale
                }),
            });

            if (res.status === 400) {
                const data = await res.json().catch(() => ({}));
                // Unwrap FastAPI HTTPException's nested detail envelope.
                // phi_blocked uses a flat JSONResponse where detail is a string,
                // so guard on object-ness before unwrapping.
                const d = (typeof data.detail === 'object' && data.detail !== null) ? data.detail : data;
                const code = d.type ?? d.error;
                if (code === 'phi_blocked') {
                    setPhiError({ detail: d.detail, suggestion: d.suggestion });
                    return;
                }
                if (code === 'invalid_fingerprint') {
                    setError('Session unavailable. Please refresh and try again.');
                    return;
                }
            }
            if (res.status === 403) {
                const data = await res.json().catch(() => ({}));
                const d = (typeof data.detail === 'object' && data.detail !== null) ? data.detail : data;
                const code = d.type ?? d.error;
                if (code === 'signup_required') {
                    setError('Sign up required to continue. Please create a free account.');
                    return;
                }
                if (code === 'limit_reached') {
                    setShowUpgradeModal(true);
                    return;
                }
                setError(ui.sessionExpired);
                return;
            }
            if (res.status === 429) {
                const data = await res.json().catch(() => ({}));
                const d = (typeof data.detail === 'object' && data.detail !== null) ? data.detail : data;
                const code = d.type ?? d.error;
                if (code === 'anonymous_quota_exceeded') {
                    const used = typeof d.used === 'number' ? d.used : 0;
                    const limit = typeof d.limit === 'number' ? d.limit : 0;
                    track('anonymous_quota_hit', { feature: 'verify', attempts: used });
                    setAnonQuotaCta({ used, limit });
                    return;
                }
                setShowDailyCapToast(true);
                return;
            }
            if (res.status === 503) {
                const data = await res.json().catch(() => ({}));
                const d = (typeof data.detail === 'object' && data.detail !== null) ? data.detail : data;
                const code = d.type ?? d.error;
                if (code === 'budget_exceeded') {
                    setAnonNoticeMsg('Service temporarily at capacity. Please try again later.');
                    return;
                }
                setError(`Service temporarily unavailable. Please try again later.`);
                return;
            }
            if (res.status === 401) {
                setError(ui.sessionExpired);
                return;
            }
            if (!res.ok) throw new Error(`Server error (${res.status}). Please try again.`);

            const data: VerifyResponse = await res.json();
            setResult(data);
            if (data.query_id) setQueryId(data.query_id);
            track('verify_completed', {
                input_drug_count: data.drugs_analyzed.length,
                interaction_count: data.interactions.length,
                risk_level: data.risk_level,
                interaction_severity_distribution: computeSeverityDist(data.interactions),
                response_language: data.response_language ?? null,
                elapsed_ms: Date.now() - t0,
                backend_query_time_ms: typeof data.query_time_ms === 'number'
                    ? data.query_time_ms : null,
            });
            if (!isSignedIn) maybeTriggerThirdQueryCta();

        } catch (err: any) {
            setError(err.message || 'Analysis failed. Please try again.');
            track('verify_failed', {
                error_code: err?.name === 'TypeError' ? 'network_error'
                    : (err?.message ?? 'unknown'),
                elapsed_ms: Date.now() - t0,
            });
        } finally {
            setLoading(false);
            isRunningRef.current = false;
        }
    }

    const getRiskBadge = (level: string) => {
        const map: Record<string, string> = {
            Critical: 'bg-red-50 text-red-700 border-red-200',
            Major:    'bg-red-50 text-red-700 border-red-200',
            Moderate: 'bg-yellow-50 text-yellow-700 border-yellow-200',
            Minor:    'bg-blue-50 text-blue-700 border-blue-200',
            Low:      'bg-green-50 text-green-700 border-green-200',
        };
        return map[level] ?? 'bg-gray-50 text-gray-700 border-gray-200';
    };

    const getSeverityStyle = (severity: string) => {
        const map: Record<string, string> = {
            Critical: 'border-red-400 bg-red-50 dark:bg-red-900/20',
            Major:    'border-red-400 bg-red-50 dark:bg-red-900/20',
            Moderate: 'border-yellow-400 bg-yellow-50 dark:bg-yellow-900/20',
            Minor:    'border-blue-300 bg-blue-50 dark:bg-blue-900/20',
        };
        return map[severity] ?? 'border-gray-300 bg-gray-50 dark:bg-gray-700';
    };

    const getSeverityBadge = (severity: string) => {
        const map: Record<string, string> = {
            Critical: 'bg-red-100 text-red-800',
            Major:    'bg-red-100 text-red-800',
            Moderate: 'bg-yellow-100 text-yellow-800',
            Minor:    'bg-blue-100 text-blue-800',
        };
        return map[severity] ?? 'bg-gray-100 text-gray-800';
    };

    const getInteractionSummary = (interactions: DrugInteraction[]) => {
        if (interactions.length === 0) {
            return { text: ui.noInteractions, color: 'rgba(255,255,255,0.5)' };
        }
        const severityOrder = ['Critical', 'Major', 'Moderate', 'Minor'];
        // Accumulate counts + carry backend-localized label (severity_label) for formatter
        const buckets: Record<string, { label?: string; count: number }> = {};
        let highestIdx = severityOrder.length;
        for (const i of interactions) {
            const key = i.severity;
            if (!buckets[key]) {
                buckets[key] = { label: i.severity_label || undefined, count: 0 };
            }
            buckets[key].count += 1;
            const idx = severityOrder.indexOf(key);
            if (idx !== -1 && idx < highestIdx) highestIdx = idx;
        }
        const breakdown = severityOrder
            .filter(s => buckets[s])
            .map(s => ({ canonical: s, label: buckets[s].label, count: buckets[s].count }));
        const colorMap: Record<string, string> = {
            Critical: '#f87171', Major: '#f87171', Moderate: '#fbbf24', Minor: '#60a5fa',
        };
        const highest = highestIdx < severityOrder.length ? severityOrder[highestIdx] : 'Minor';
        return {
            text: formatInteractionSummary(lang, interactions.length, breakdown),
            color: colorMap[highest] || 'rgba(255,255,255,0.5)',
        };
    };

    return (
        <div className="container mx-auto px-4 py-8 max-w-5xl">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight" style={{ color: "#ffffff" }}>{ui.verifyTitle}</h1>
                    <p className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.5)" }}>{ui.verifySubtitle}</p>
                </div>
                {(result || drugs) && !loading && (
                    <button onClick={handleReset} className="text-sm font-medium px-3 py-1 rounded-lg transition-all"
                        style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.3)', color: 'rgba(255,255,255,0.7)' }}
                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.1)'; }}
                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}>
                        {ui.newBtn}
                    </button>
                )}
            </div>

            {/* Language box */}
            <div className="rounded-xl p-4 text-sm mb-6" style={{ background: 'rgba(56,189,248,0.05)', border: '1px solid rgba(56,189,248,0.3)' }}>
                <p style={{ color: 'rgba(56,189,248,0.9)' }}>
                    <span className="font-semibold">{ui.verifyInfoBox}</span>
                </p>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
                {/* Input */}
                <div className="rounded-xl p-6" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="space-y-3">
                            <label className="block text-sm font-medium" style={{ color: "rgba(255,255,255,0.8)" }}>
                                {ui.drugListLabel} <span className="font-normal" style={{ color: "rgba(255,255,255,0.5)" }}>{ui.drugListHint}</span>
                            </label>
                            {/* Quick-add chips */}
                            <div className="flex flex-wrap gap-2">
                                {["Warfarin","Aspirin","Metformin","Lisinopril","Atorvastatin",
                                  "Amiodarone","Clopidogrel","Fluoxetine","Omeprazole","Metoprolol",
                                  "Tramadol","Simvastatin","Clarithromycin","Ibuprofen","Digoxin"].map(drug => (
                                    <button
                                        key={drug}
                                        type="button"
                                        onClick={() => setDrugs(prev => prev ? prev + '\n' + drug : drug)}
                                        className="px-3 py-1 text-xs rounded-full transition-all duration-200"
                                        style={{ background: "rgba(99,179,237,0.1)", border: "1px solid rgba(99,179,237,0.3)", color: "rgba(99,179,237,0.9)" }}
                                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = "rgba(99,179,237,0.22)"; }}
                                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = "rgba(99,179,237,0.1)"; }}
                                    >
                                        + {drug}
                                    </button>
                                ))}
                            </div>
                            <textarea
                                id="drugs"
                                required
                                rows={6}
                                value={drugs}
                                onChange={(e) => setDrugs(e.target.value)}
                                disabled={loading}
                                className="w-full px-4 py-3 rounded-lg focus:outline-none focus:ring-2 font-mono text-sm disabled:opacity-60 transition-shadow"
                                style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.15)", color: "rgba(255,255,255,0.85)" }}
                                placeholder={"Metformin\nAspirin\nWarfarin"}
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full text-white font-medium py-2.5 px-6 rounded-lg transition-opacity disabled:opacity-50 text-sm"
                            style={{ background: ACCENT }}
                        >
                            {loading ? ui.analyzingBtn : ui.analyzeBtn}
                        </button>
                    </form>

                    {phiError && !loading && (
                        <div className="mt-4">
                            <PHIWarning detail={phiError.detail} suggestion={phiError.suggestion} onDismiss={() => setPhiError(null)} />
                        </div>
                    )}

                    {error && (
                        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg border border-red-100 text-sm">
                            {error}
                        </div>
                    )}
                </div>

                {/* Results */}
                <div className="rounded-xl p-6 flex flex-col" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>
                    {!result && !loading && (
                        <div className="flex items-center justify-center h-full text-sm" style={{ color: "rgba(255,255,255,0.4)" }}>
                            {ui.verifyEmpty}
                        </div>
                    )}

                    {loading && (
                        <div className="text-center py-16">
                            <div className="w-8 h-8 border-2 border-gray-200 border-t-blue-400 rounded-full animate-spin mx-auto" />
                            <p className="mt-4 text-sm text-gray-400">{ui.analyzingMsg}</p>
                        </div>
                    )}

                    {result && (
                        <div className="space-y-6">
                            {/* Summary */}
                            <div>
                                <div className="flex justify-between items-start mb-3">
                                    <h2 className="text-base font-semibold" style={{ color: "#ffffff" }}>
                                        {ui.analysisSummary}
                                    </h2>
                                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${getRiskBadge(result.risk_level)}`}>
                                        {result.risk_level_label || getRiskLevelLabel(lang, result.risk_level)}
                                    </span>
                                </div>
                                {(() => {
                                    const summary = getInteractionSummary(result.interactions);
                                    return (
                                        <p className="text-sm font-medium mb-3" style={{ color: summary.color }}>
                                            {summary.text}
                                        </p>
                                    );
                                })()}
                                <FeedbackBar
                                    query={`Drugs: ${result.drugs_analyzed.join(', ')}`}
                                    response={result.summary}
                                    category="verify"
                                />
                                <p className="text-xs text-gray-300 dark:text-gray-600 mt-3">
                                    {result.drugs_analyzed.join(', ')} · {(result.query_time_ms / 1000).toFixed(2)}s
                                </p>
                            </div>

                            {/* Interactions */}
                            {result.interactions.length > 0 && (
                                <div>
                                    <div className="space-y-3">
                                        {result.interactions.map((interaction, idx) => (
                                            <div key={idx} className={`border-l-4 rounded-lg p-4 ${getSeverityStyle(interaction.severity)}`}>
                                                <div className="flex justify-between items-start mb-2">
                                                    <p className="font-semibold text-base text-slate-900 dark:text-slate-100">
                                                        {interaction.drug_pair[0]} ↔ {interaction.drug_pair[1]}
                                                    </p>
                                                    <span className={`px-2 py-0.5 rounded text-xs font-medium ml-2 flex-shrink-0 ${getSeverityBadge(interaction.severity)}`}>
                                                        {interaction.severity_label || getSeverityLabel(lang, interaction.severity)}
                                                    </span>
                                                </div>
                                                <div className="space-y-2 text-sm leading-relaxed text-gray-800 dark:text-gray-200">
                                                    <p>{interaction.description}</p>
                                                    {interaction.clinical_recommendation && (
                                                        <p className="opacity-90">{interaction.clinical_recommendation}</p>
                                                    )}
                                                    <p className="text-xs text-gray-600 dark:text-gray-400 italic">
                                                        Source:{' '}
                                                        {interaction.source_url ? (
                                                            <a href={interaction.source_url} target="_blank" rel="noopener noreferrer"
                                                               className="underline hover:opacity-80">
                                                                {interaction.source}
                                                            </a>
                                                        ) : interaction.source}
                                                    </p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {result.disclaimer && (
                                <p className="text-xs text-gray-400 pt-2 border-t border-gray-100 dark:border-gray-700">
                                    ⚠️ {result.disclaimer}
                                </p>
                            )}
                            {showThirdQueryCta && !isSignedIn && (
                                <AnonymousUpgradeCTA
                                    trigger="third_query"
                                    onDismiss={() => setShowThirdQueryCta(false)}
                                />
                            )}
                        </div>
                    )}
                </div>
            </div>

            <div className="mt-8 border-t pt-6 space-y-2 text-xs" style={{ borderColor: "rgba(99,179,237,0.35)", color: "rgba(255,255,255,0.4)" }}>
                <p className="font-medium" style={{ color: "rgba(255,255,255,0.6)" }}>{ui.dataSourcesTitle}</p>
                <p dangerouslySetInnerHTML={{ __html: ui.verifyAttr1 }} />
                <p dangerouslySetInnerHTML={{ __html: ui.verifyAttr2 }} />
                <p dangerouslySetInnerHTML={{ __html: ui.verifyAttr3 }} />
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
                    quotaDetails={{ feature: 'verify', used: anonQuotaCta.used, limit: anonQuotaCta.limit }}
                    onDismiss={() => setAnonQuotaCta(null)}
                />
            )}
        </div>
    );
}

export default function Verify() {
    return (
        <PageShell
            activePage="verify"
            allowAnonymous
            extraHead={
                <Head>
                    <meta name="robots" content="noindex, nofollow" />
                </Head>
            }
        >
            <VerifyForm />
        </PageShell>
    );
}