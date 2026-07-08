"use client"

import { useState, FormEvent, useRef, useCallback, useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { useAuth, useUser } from '@clerk/nextjs';
import FeedbackBar from '../components/FeedbackBar';
import { useShareContext } from '../contexts/ShareContext';
import UpgradeModal from '../components/UpgradeModal';
import Toast from '../components/Toast';
import PHIWarning from '../components/PHIWarning';
import NonEnglishDrugWarning from '../components/NonEnglishDrugWarning';
import PageShell from '../components/PageShell';
import AnonymousUpgradeCTA from '../components/AnonymousUpgradeCTA';
import { setQueryId, getAnonFingerprint, track } from '../utils/analytics';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';
import { formatInteractionSummary, getSeverityLabel, getRiskLevelLabel,
         getAiSeverityNote, getSourceCaptionByKind, getSourcePrefix } from '../utils/i18n-verify';

// ADR 003 — flag a drug line as non-English ONLY if it contains a non-Latin SCRIPT
// (CJK / kana / Hangul / Cyrillic / Hebrew / Arabic / Thai / Devanagari / Bengali).
// Accented-Latin INNs (à, é, ñ, ø … in Latin-1/Extended) must NOT trigger.
const NON_LATIN_SCRIPT = /[　-〿぀-ヿ㐀-䶿一-鿿豈-﫿가-힯ᄀ-ᇿ㄰-㆏Ѐ-ӿ֐-׿؀-ۿݐ-ݿ฀-๿ऀ-ॿঀ-৿]/;
function hasNonLatinScript(drugList: string[]): boolean {
    return drugList.some(d => NON_LATIN_SCRIPT.test(d));
}

interface DrugInteraction {
    drug_pair: [string, string];
    severity: string;                 // canonical enum (Critical/Major/Moderate/Minor)
    severity_label?: string | null;   // localized display (e.g. "嚴重")
    description: string;
    clinical_recommendation: string;
    source: string;
    source_url?: string;
    attribution_kind?: string;        // stable Option-C key: dailymed_grounded | openfda_analysis | no_label
}

interface TfdaGrounding {
    query: string;          // user-entered token, verbatim
    ingredients: string[];  // resolved TFDA 主成分 (INN); >1 for combos
    is_combo: boolean;
    licenses: string[];     // TFDA 許可證字號
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
    // ADR 007 T2a structured transparency (additive — absent on old/cached responses)
    tfda_groundings?: TfdaGrounding[] | null;
    verification_status?: string | null;   // "ok" | "deferred_ambiguous_brand"
    deferred_brands?: string[] | null;
}

// Split a free-text prefill (e.g. cross-page ?prefill= carry-over) into the
// newline-delimited drug list this page expects. Symbolic separators only
// (+, comma, &) — " and " is intentionally excluded (can't distinguish
// "Drug and Drug" from "Drug and <context>" without NLP). Falls back to the
// raw string if no confident split; the user reviews before manual submit.
function splitDrugsForPrefill(raw: string): string {
    const s = raw.trim();
    if (!s) return '';
    const seps = [/\s*\+\s*/, /\s*,\s*/, /\s*&\s*/];
    for (const sep of seps) {
        const parts = s.split(sep).map(p => p.trim()).filter(Boolean);
        if (parts.length >= 2 && parts.every(p => p.length <= 40)) {
            return parts.join('\n');
        }
    }
    return s;
}

function VerifyForm() {
    const { getToken } = useAuth();
    const { isSignedIn } = useUser();
    const { lang } = useLang();
    const ui = getUI(lang);
    const router = useRouter();
    const prefillConsumedRef = useRef(false);

    const [drugs, setDrugs]   = useState('');
    const [result, setResult] = useState<VerifyResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError]   = useState('');

    const isRunningRef = useRef(false);
    // ADR 003 — force-English guidance state
    const [nonEnglishWarn, setNonEnglishWarn] = useState(false);
    const wasWarnedRef = useRef(false);          // showed the warning this attempt-cycle
    const drugsTextareaRef = useRef<HTMLTextAreaElement>(null);
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    const [showDailyCapToast, setShowDailyCapToast] = useState(false);
    const [anonNoticeMsg, setAnonNoticeMsg] = useState<string | null>(null);
    const [anonQuotaCta, setAnonQuotaCta] = useState<{ used: number; limit: number } | null>(null);
    const [showThirdQueryCta, setShowThirdQueryCta] = useState(false);
    const [phiError, setPhiError] = useState<{detail: string; suggestion: string} | null>(null);
    const [localQueryId, setLocalQueryId] = useState<string | null>(null);
    const { setShareData, clearShareData } = useShareContext();

    const handleReset = () => { setDrugs(''); setResult(null); setError(''); setPhiError(null); setNonEnglishWarn(false); wasWarnedRef.current = false; setQueryId(null); setLocalQueryId(null); };

    // PRD § 4.5 UX polish 2/3 — Navbar Share button via ShareContext.
    useEffect(() => {
        if (loading) {
            clearShareData();
            return;
        }
        if (!error && result && localQueryId) {
            setShareData({
                queryId: localQueryId,
                queryText: `Drugs: ${result.drugs_analyzed.join(', ')}`,
                answerText: result.summary,
                citations: result.interactions.map(i => ({
                    title: `${i.drug_pair[0]} ↔ ${i.drug_pair[1]} (${i.severity})`,
                    url: i.source_url ?? null,
                    text: i.description,
                })),
                feature: 'verify',
            });
        }
    }, [loading, error, result, localQueryId, setShareData, clearShareData]);

    useEffect(() => {
        return () => clearShareData();
    }, [clearShareData]);

    // Cross-page ?prefill= receiver — prefill the drugs textarea, no auto-submit.
    // Mirrors research.tsx's ?q= consume pattern (minus the auto-run).
    useEffect(() => {
        if (!router.isReady) return;
        if (prefillConsumedRef.current) return;
        const raw = router.query.prefill;
        const v = Array.isArray(raw) ? raw[0] : raw;
        if (typeof v !== 'string') return;
        const trimmed = v.trim();
        if (!trimmed) return;
        prefillConsumedRef.current = true;
        setDrugs(splitDrugsForPrefill(trimmed));
        router.replace('/verify', undefined, { shallow: true });
    }, [router]);

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

        // ADR 003 — force-English guard: block submit on non-Latin script, guide
        // the user to the English INN BEFORE the (English-indexed) backend runs.
        if (hasNonLatinScript(drugList)) {
            wasWarnedRef.current = true;
            setNonEnglishWarn(true);
            track('non_english_input_detected', { feature: 'verify', drug_line_count: drugList.length });
            return;
        }
        // Clean entry after a prior warning → the user corrected it.
        if (wasWarnedRef.current) {
            track('non_english_input_corrected', { feature: 'verify' });
            wasWarnedRef.current = false;
        }

        await doVerify(drugList);
    }

    // "Submit anyway (not recommended)" — bypass the guard, use the EXISTING
    // Verify pipeline unchanged (ADR 003: the proceed path is the normal flow).
    function handleProceedAnyway() {
        setNonEnglishWarn(false);
        wasWarnedRef.current = false;
        track('non_english_input_proceeded_anyway', { feature: 'verify' });
        const drugList = drugs.split('\n').map(d => d.trim()).filter(Boolean);
        if (drugList.length < 2) { setError(ui.enterTwoDrugs); return; }
        void doVerify(drugList);
    }

    async function doVerify(drugList: string[]) {
        if (isRunningRef.current) return;

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
        setLocalQueryId(null);

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
            if (data.query_id) {
                setQueryId(data.query_id);
                setLocalQueryId(data.query_id);
            }
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

    // Severity → semantic token mapping (flips per theme; AA-tuned in both):
    // Critical/Major=danger, Moderate=warning, Minor=info, Low=success.
    const getRiskBadge = (level: string) => {
        const map: Record<string, string> = {
            Critical: 'bg-danger/10 text-danger border-danger/30',
            Major:    'bg-danger/10 text-danger border-danger/30',
            Moderate: 'bg-warning/10 text-warning border-warning/30',
            Minor:    'bg-info/10 text-info border-info/30',
            Low:      'bg-success/10 text-success border-success/30',
        };
        return map[level] ?? 'bg-text/8 text-text/70 border-text/15';
    };

    const getSeverityStyle = (severity: string) => {
        const map: Record<string, string> = {
            Critical: 'border-danger bg-danger/10',
            Major:    'border-danger bg-danger/10',
            Moderate: 'border-warning bg-warning/10',
            Minor:    'border-info bg-info/10',
        };
        return map[severity] ?? 'border-text/30 bg-text/5';
    };

    const getSeverityBadge = (severity: string) => {
        const map: Record<string, string> = {
            Critical: 'bg-danger/15 text-danger',
            Major:    'bg-danger/15 text-danger',
            Moderate: 'bg-warning/15 text-warning',
            Minor:    'bg-info/15 text-info',
        };
        return map[severity] ?? 'bg-text/10 text-text/70';
    };

    const getInteractionSummary = (interactions: DrugInteraction[]) => {
        if (interactions.length === 0) {
            return { text: ui.noInteractions, color: 'rgb(var(--color-text) / 0.5)' };
        }
        const severityOrder = ['Critical', 'Major', 'Moderate', 'Minor'];
        // Accumulate counts by canonical severity enum. Labels are resolved
        // frontend-side from the enum via i18n-verify (NOT the LLM's
        // severity_label free-text, which leaks wrong-language values — see
        // the deterministic enum-authority fix below).
        const buckets: Record<string, { count: number }> = {};
        let highestIdx = severityOrder.length;
        for (const i of interactions) {
            const key = i.severity;
            if (!buckets[key]) {
                buckets[key] = { count: 0 };
            }
            buckets[key].count += 1;
            const idx = severityOrder.indexOf(key);
            if (idx !== -1 && idx < highestIdx) highestIdx = idx;
        }
        const breakdown = severityOrder
            .filter(s => buckets[s])
            .map(s => ({ canonical: s, count: buckets[s].count }));
        const colorMap: Record<string, string> = {
            Critical: 'rgb(var(--color-danger))',
            Major:    'rgb(var(--color-danger))',
            Moderate: 'rgb(var(--color-warning))',
            Minor:    'rgb(var(--color-info))',
        };
        const highest = highestIdx < severityOrder.length ? severityOrder[highestIdx] : 'Minor';
        return {
            text: formatInteractionSummary(lang, interactions.length, breakdown),
            color: colorMap[highest] || 'rgb(var(--color-text) / 0.5)',
        };
    };

    return (
        <div className="container mx-auto px-4 py-8 max-w-5xl">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight" style={{ color: "rgb(var(--color-text))" }}>{ui.verifyTitle}</h1>
                    <p className="text-sm mt-1" style={{ color: "rgb(var(--color-text) / 0.5)" }}>{ui.verifySubtitle}</p>
                </div>
                {(result || drugs) && !loading && (
                    <button onClick={handleReset} className="text-sm font-medium px-3 py-1 rounded-lg transition-all"
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
                    <span className="font-semibold">{ui.verifyInfoBox}</span>
                </p>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
                {/* Input */}
                <div className="rounded-xl p-6" style={{ background: "rgb(var(--color-text) / 0.06)", border: "1px solid rgb(var(--color-text) / 0.1)" }}>
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="space-y-3">
                            <label className="block text-sm font-medium" style={{ color: "rgb(var(--color-text) / 0.8)" }}>
                                {ui.drugListLabel} <span className="font-normal" style={{ color: "rgb(var(--color-text) / 0.5)" }}>{ui.drugListHint}</span>
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
                                        style={{ background: "rgb(var(--color-text) / 0.06)", border: "1px solid rgb(var(--color-text) / 0.15)", color: "rgb(var(--color-text) / 0.7)" }}
                                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = "rgb(var(--color-text) / 0.12)"; }}
                                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = "rgb(var(--color-text) / 0.06)"; }}
                                    >
                                        + {drug}
                                    </button>
                                ))}
                            </div>
                            <textarea
                                ref={drugsTextareaRef}
                                id="drugs"
                                required
                                rows={6}
                                value={drugs}
                                onChange={(e) => setDrugs(e.target.value)}
                                disabled={loading}
                                className="w-full px-4 py-3 rounded-lg focus:outline-none focus:ring-2 font-mono text-sm disabled:opacity-60 transition-shadow"
                                style={{ background: "rgb(var(--color-text) / 0.05)", border: "1px solid rgb(var(--color-text) / 0.15)", color: "rgb(var(--color-text) / 0.85)" }}
                                placeholder={"Metformin\nAspirin\nWarfarin"}
                            />
                            {/* ADR 003 — always-visible English-input nudge (shown before any error) */}
                            <p className="text-xs" style={{ color: "rgb(var(--color-text) / 0.55)" }}>
                                {ui.verifyInputHint} <span style={{ color: "rgb(var(--color-text) / 0.4)" }}>{ui.verifyInputExample}</span>
                            </p>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full text-white font-medium py-2.5 px-6 rounded-lg transition-opacity disabled:opacity-50 text-sm"
                            style={{ background: 'rgb(var(--color-brand))' }}
                        >
                            {loading ? ui.analyzingBtn : ui.analyzeBtn}
                        </button>
                    </form>

                    {nonEnglishWarn && !loading && (
                        <div className="mt-4">
                            <NonEnglishDrugWarning
                                onModify={() => {
                                    setNonEnglishWarn(false);
                                    drugsTextareaRef.current?.focus();
                                }}
                                onProceed={handleProceedAnyway}
                            />
                        </div>
                    )}

                    {phiError && !loading && (
                        <div className="mt-4">
                            <PHIWarning detail={phiError.detail} suggestion={phiError.suggestion} onDismiss={() => setPhiError(null)} />
                        </div>
                    )}

                    {error && (
                        <div className="mt-4 p-3 bg-danger/10 text-danger rounded-lg border border-danger/20 text-sm">
                            {error}
                        </div>
                    )}
                </div>

                {/* Results */}
                <div className="rounded-xl p-6 flex flex-col" style={{ background: "rgb(var(--color-text) / 0.06)", border: "1px solid rgb(var(--color-text) / 0.1)" }}>
                    {!result && !loading && (
                        <div className="flex items-center justify-center h-full text-sm" style={{ color: "rgb(var(--color-text) / 0.4)" }}>
                            {ui.verifyEmpty}
                        </div>
                    )}

                    {loading && (
                        <div className="text-center py-16">
                            <div className="w-8 h-8 border-2 border-text/20 border-t-brand rounded-full animate-spin mx-auto" />
                            <p className="mt-4 text-sm text-text/50">{ui.analyzingMsg}</p>
                        </div>
                    )}

                    {result && (
                        <div className="space-y-6">
                            {/* Summary */}
                            <div>
                                {/* ADR 007 T2a: an ambiguous-brand DEFER is a REFUSED verification, and a
                                    failed_no_data run is an INCOMPLETE one — neither may present as a clean
                                    "no interactions found" result. */}
                                {(() => {
                                    const isDeferred = result.verification_status === 'deferred_ambiguous_brand';
                                    const isFailed = result.verification_status === 'failed_no_data';
                                    const notClean = isDeferred || isFailed;
                                    return (
                                        <>
                                            <div className="flex justify-between items-start mb-3">
                                                <h2 className="text-base font-semibold" style={{ color: "rgb(var(--color-text))" }}>
                                                    {ui.analysisSummary}
                                                </h2>
                                                <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${notClean ? 'bg-warning/10 text-warning border-warning/30' : getRiskBadge(result.risk_level)}`}>
                                                    {notClean ? ui.verifyDeferredBadge : getRiskLevelLabel(lang, result.risk_level)}
                                                </span>
                                            </div>
                                            {notClean ? (
                                                <div className="rounded-lg border border-warning/30 bg-warning/10 p-3 mb-3 text-sm">
                                                    <p className="font-medium text-warning mb-1">
                                                        ⚠️ {isDeferred
                                                            ? ui.verifyDeferredMsg.replace('{brands}', (result.deferred_brands ?? []).join(', '))
                                                            : ui.verifyFailedMsg}
                                                    </p>
                                                    <p className="text-text/70">{isDeferred ? ui.verifyDeferredAdvice : ui.verifyFailedAdvice}</p>
                                                </div>
                                            ) : (() => {
                                                const summary = getInteractionSummary(result.interactions);
                                                return (
                                                    <p className="text-sm font-medium mb-3" style={{ color: summary.color }}>
                                                        {summary.text}
                                                    </p>
                                                );
                                            })()}
                                        </>
                                    );
                                })()}
                                {/* ADR 007 T2a grounding-transparency note — a provenance line
                                    (deterministic TFDA brand→INN mapping), subordinate to the verdict. */}
                                {(result.tfda_groundings?.length ?? 0) > 0 && (
                                    <div className="space-y-0.5 mb-3">
                                        {result.tfda_groundings!.map((g, i) => (
                                            <p key={i} className="text-xs text-text/50">
                                                {(g.is_combo ? ui.verifyTfdaGroundingComboNote : ui.verifyTfdaGroundingNote)
                                                    .replace('{query}', g.query)
                                                    .replace('{ingredients}', g.ingredients.join(' + '))}
                                            </p>
                                        ))}
                                    </div>
                                )}
                                <FeedbackBar
                                    query={`Drugs: ${result.drugs_analyzed.join(', ')}`}
                                    response={result.summary}
                                    category="verify"
                                />
                                <p className="text-xs text-text/40 mt-3">
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
                                                    <p className="font-semibold text-base text-text">
                                                        {interaction.drug_pair[0]} ↔ {interaction.drug_pair[1]}
                                                    </p>
                                                    {/* Severity badge + Option-C AI-severity marker in the SAME eyeline:
                                                        the severity is Vela's AI judgment, NOT the label's grading. */}
                                                    <div className="flex flex-col items-end ml-2 flex-shrink-0">
                                                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${getSeverityBadge(interaction.severity)}`}>
                                                            {getSeverityLabel(lang, interaction.severity)}
                                                        </span>
                                                        <span className="text-[10px] leading-tight text-text/50 mt-0.5 text-right max-w-[9rem]"
                                                              title={getAiSeverityNote(lang)}>
                                                            ⓘ {getAiSeverityNote(lang)}
                                                        </span>
                                                    </div>
                                                </div>
                                                <div className="space-y-2 text-sm leading-relaxed text-text/85">
                                                    <p>{interaction.description}</p>
                                                    {interaction.clinical_recommendation && (
                                                        <p className="opacity-90">{interaction.clinical_recommendation}</p>
                                                    )}
                                                    {/* Attribution: localized caption keyed off the STABLE
                                                        attribution_kind enum (NOT the raw English source string). */}
                                                    <p className="text-xs text-text/55 italic">
                                                        {getSourcePrefix(lang)}{' '}
                                                        {interaction.source_url ? (
                                                            <a href={interaction.source_url} target="_blank" rel="noopener noreferrer"
                                                               className="underline hover:opacity-80">
                                                                {getSourceCaptionByKind(lang, interaction.attribution_kind)}
                                                            </a>
                                                        ) : getSourceCaptionByKind(lang, interaction.attribution_kind)}
                                                    </p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {result.disclaimer && (
                                <p className="text-xs text-text/40 pt-2 border-t border-text/10">
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

            <div className="mt-8 border-t pt-6 space-y-2 text-xs" style={{ borderColor: "rgb(var(--color-text) / 0.15)", color: "rgb(var(--color-text) / 0.4)" }}>
                <p className="font-medium" style={{ color: "rgb(var(--color-text) / 0.6)" }}>{ui.dataSourcesTitle}</p>
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