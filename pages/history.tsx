"use client"

import { useState, useEffect } from 'react';
import Head from 'next/head';
import { useAuth } from '@clerk/nextjs';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import rehypeRaw from 'rehype-raw';
import UpgradeModal from '../components/UpgradeModal';
import ProFeatureOverlay from '../components/ProFeatureOverlay';
import PageShell from '../components/PageShell';
import ShareButton, { type ShareFeature } from '../components/ShareButton';
import ExplainItemCard, { type ExplainItem } from '../components/ExplainItemCard';
import ClinicalCorrelationCard, { type ClinicalCorrelation } from '../components/ClinicalCorrelationCard';
import ResearchSection from '../components/ResearchSection';
import VerifyInteractionCard, { type DrugInteraction, getRiskBadgeClass, getInteractionSummaryDisplay } from '../components/VerifyInteractionCard';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';
import { getExtra } from '../utils/i18n-extra';
import { getRiskLevelLabel } from '../utils/i18n-verify';
import { parseResearchSections, stripLlmDisclaimer } from '../utils/researchSections';

// ─── Design System ────────────────────────────────────────────────────────────
// C3: feature accents collapsed — features distinguished by label only, not color.
const FEATURE_LABELS: Record<string, string> = {
    research: 'Research',
    verify:   'Verify',
    explain:  'Explain',
};

function getFeatureLabel(type: string): string {
    return FEATURE_LABELS[type] ?? (type.charAt(0).toUpperCase() + type.slice(1));
}

// Same prose token set the live /research page uses, so stored answers render
// identically here (HISTORY car segment 1, Research half A).
const researchProseStyle = {
    color: "rgb(var(--color-text) / 0.85)",
    '--tw-prose-headings': 'rgb(var(--color-text))',
    '--tw-prose-bold': 'rgb(var(--color-text))',
    '--tw-prose-links': 'rgb(var(--color-brand))',
    '--tw-prose-bullets': 'rgb(var(--color-text) / 0.5)',
    '--tw-prose-counters': 'rgb(var(--color-text) / 0.5)',
    '--tw-prose-code': 'rgb(var(--color-brand))',
    '--tw-prose-hr': 'rgb(var(--color-text) / 0.15)',
} as React.CSSProperties;

// Verify rows: VerifyResponse-shaped JSON (HISTORY car segment 1) — same
// safe-parse-with-fallback pattern as Explain. Returns null for legacy
// summary-only rows and malformed JSON.
interface VerifyHistoryPayload {
    interactions: DrugInteraction[];
    summary?: string;
    risk_level?: string;
    tfda_groundings?: { query: string; ingredients: string[]; is_combo?: boolean }[] | null;
    disclaimer?: string;
    verification_status?: string | null;
}

function parseVerifyAnswer(answer: string): VerifyHistoryPayload | null {
    try {
        const p = JSON.parse(answer);
        if (p && Array.isArray(p.interactions)) return p as VerifyHistoryPayload;
    } catch {}
    return null;
}
// ─────────────────────────────────────────────────────────────────────────────

interface HistoryItem {
    id: number;
    user_id: string;
    session_type: string;
    question: string;
    answer: string;
    created_at: string;
}

function TypeTag({ type }: { type: string }) {
    return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide bg-text/8 text-text/85 border border-text/15">
            {getFeatureLabel(type)}
        </span>
    );
}

function HistoryList() {
    const { getToken } = useAuth();
    const { lang } = useLang();
    const ui = getUI(lang);
    const extra = getExtra(lang);
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedId, setExpandedId] = useState<number | null>(null);
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
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => { loadPlanAndHistory(); }, []);

    async function loadPlanAndHistory() {
        try {
            const token = await getToken({ skipCache: true });
            // Fetch plan status
            try {
                const statusRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/user/status`, {
                    headers: { 'Authorization': `Bearer ${token}` },
                });
                if (statusRes.ok) {
                    const statusData = await statusRes.json();
                    const fetched = statusData.plan_type === 'pro' ? 'pro' : 'free' as const;
                    setPlan(fetched);
                }
            } catch {}
            // Fetch history
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/history`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (!res.ok) throw new Error('Failed to load history');
            const data = await res.json();
            setHistory(data);
        } catch (err) {
            console.error('History load error:', err);
        } finally {
            setLoading(false);
        }
    }

    function handleToggle(item: HistoryItem) {
        if (expandedId === item.id) {
            setExpandedId(null);
        } else {
            setExpandedId(item.id);
        }
    }

    if (loading) {
        return (
            <div className="text-center py-16">
                <div className="animate-spin rounded-full h-10 w-10 border-2 border-text/20 border-t-text/50 mx-auto" />
                <p className="mt-4 text-sm text-text/50">{ui.loadingHistory}</p>
            </div>
        );
    }

    if (history.length === 0) {
        return (
            <div className="text-center py-16">
                <p className="text-text/50 mb-4">{ui.noHistory}</p>
                <Link href="/research" className="text-sm hover:text-text underline underline-offset-4" style={{ color: "rgb(var(--color-text) / 0.5)" }}>
                    {ui.startSearch}
                </Link>
            </div>
        );
    }

    const filteredHistory = searchQuery && plan === 'pro'
        ? history.filter(item => item.question.toLowerCase().includes(searchQuery.toLowerCase()))
        : history;

    return (
        <div className="space-y-3">
            {/* Free plan banner */}
            {plan === 'free' && (
                <div className="rounded-xl p-4 text-sm mb-2" style={{ background: 'rgb(var(--color-text) / 0.05)', border: '1px solid rgb(var(--color-text) / 0.15)' }}>
                    <p style={{ color: 'rgb(var(--color-text) / 0.7)' }}>
                        {ui.freeHistoryMsg}
                    </p>
                </div>
            )}

            {/* Search box */}
            <ProFeatureOverlay isLocked={plan !== 'pro'} featureName={extra.proFeatSearchHistory}>
                <div className="relative">
                    <input
                        type="text"
                        placeholder={ui.searchHistory}
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        disabled={plan !== 'pro'}
                        className="w-full px-4 py-2.5 rounded-lg text-sm focus:outline-none focus:ring-2 disabled:cursor-not-allowed"
                        style={{ background: 'rgb(var(--color-text) / 0.06)', border: '1px solid rgb(var(--color-text) / 0.12)', color: 'rgb(var(--color-text) / 0.85)' }}
                    />
                    <svg className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'rgb(var(--color-text) / 0.3)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                </div>
            </ProFeatureOverlay>

            {filteredHistory.map(item => {
                const isExpanded = expandedId === item.id;
                const verifyParsed = item.session_type === 'verify' ? parseVerifyAnswer(item.answer) : null;

                return (
                    <div
                        key={item.id}
                        className="rounded-xl overflow-hidden transition-shadow bg-text/6 border border-text/10"
                    >
                        {/* Header */}
                        <button
                            onClick={() => handleToggle(item)}
                            className="w-full px-6 py-4 flex items-center justify-between transition-colors text-left"
                            onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "rgb(var(--color-text) / 0.05)"}
                            onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = "transparent"}
                        >
                            <div className="flex items-center gap-3 min-w-0">
                                <TypeTag type={item.session_type} />
                                <div className="min-w-0">
                                    <p className="font-medium truncate text-sm history-question" style={{ color: "rgb(var(--color-text) / 0.85)" }}>
                                        {item.question.length > 80
                                            ? item.question.slice(0, 80) + '...'
                                            : item.question}
                                    </p>
                                    <p className="text-xs text-text/50 mt-0.5">
                                        {new Date(item.created_at).toLocaleString('en-US', {
                                            year: 'numeric', month: 'short', day: 'numeric',
                                            hour: '2-digit', minute: '2-digit',
                                        })}
                                    </p>
                                </div>
                            </div>

                            <svg
                                className={`w-4 h-4 text-text/50 flex-shrink-0 ml-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                                fill="none" stroke="currentColor" viewBox="0 0 24 24"
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                        </button>

                        {/* Expanded content */}
                        {isExpanded && (
                            <div className="px-6 py-5 border-t" style={{ borderColor: "rgb(var(--color-text) / 0.08)" }}>

                                {/* Research — Rule 12 section format via the shared parser the live
                                    /research page uses. Bare [N] markers stay plain text exactly as on
                                    /research (no citations stored — half B deferred; no fake links).
                                    Non-conforming/legacy rows fall back to the pre-wrap rendering. */}
                                {item.session_type === 'research' && (() => {
                                    const sections = item.answer ? parseResearchSections(stripLlmDisclaimer(item.answer)) : null;
                                    if (sections) {
                                        return (
                                            <div>
                                                {sections.map((sec, i) => (
                                                    <ResearchSection key={i} title={sec.title}>
                                                        <div className="prose max-w-none prose-sm prose-headings:font-semibold prose-h2:text-base" style={researchProseStyle}>
                                                            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>{sec.content}</ReactMarkdown>
                                                        </div>
                                                    </ResearchSection>
                                                ))}
                                            </div>
                                        );
                                    }
                                    return (
                                        <div
                                            className="prose max-w-none prose-sm prose-headings:font-semibold"
                                            style={{
                                                color: "rgb(var(--color-text) / 0.8)",
                                                '--tw-prose-headings': 'rgb(var(--color-text))',
                                                '--tw-prose-bold': 'rgb(var(--color-text))',
                                                '--tw-prose-bullets': 'rgb(var(--color-text) / 0.5)',
                                            } as React.CSSProperties}
                                        >
                                            <p className="whitespace-pre-wrap text-sm leading-relaxed" style={{ color: "rgb(var(--color-text) / 0.75)" }}>
                                                {item.answer}
                                            </p>
                                        </div>
                                    );
                                })()}

                                {/* Explain — §2.7 structured JSON: {items, clinical_correlations, disclaimer}.
                                    Safe-parse + fallback to plain text for legacy pre-§2.7 records. */}
                                {item.session_type === 'explain' && (() => {
                                    let parsed: { items?: ExplainItem[]; clinical_correlations?: ClinicalCorrelation[]; disclaimer?: string } | null = null;
                                    try {
                                        parsed = JSON.parse(item.answer);
                                    } catch {
                                        parsed = null;
                                    }
                                    if (parsed && Array.isArray(parsed.items)) {
                                        return (
                                            <div>
                                                {parsed.disclaimer && (
                                                    <p className="text-xs mb-4 text-center" style={{ color: "rgb(var(--color-text) / 0.35)" }}>
                                                        {parsed.disclaimer}
                                                    </p>
                                                )}
                                                {parsed.items.map((it, i) => (
                                                    <ExplainItemCard key={`item-${i}`} item={it} />
                                                ))}
                                                {parsed.clinical_correlations && parsed.clinical_correlations.length > 0 && (
                                                    <div className="mt-6">
                                                        <p className="text-xs font-semibold text-text/50 uppercase tracking-wider mb-3">
                                                            {ui.clinicalCorrelations}
                                                        </p>
                                                        {parsed.clinical_correlations.map((corr, i) => (
                                                            <ClinicalCorrelationCard key={`corr-${i}`} correlation={corr} />
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    }
                                    // Fallback: legacy pre-§2.7 records or malformed JSON — render as plain text.
                                    return (
                                        <div
                                            className="prose max-w-none prose-sm prose-headings:font-semibold"
                                            style={{
                                                color: "rgb(var(--color-text) / 0.8)",
                                                '--tw-prose-headings': 'rgb(var(--color-text))',
                                                '--tw-prose-bold': 'rgb(var(--color-text))',
                                                '--tw-prose-bullets': 'rgb(var(--color-text) / 0.5)',
                                            } as React.CSSProperties}
                                        >
                                            <p className="whitespace-pre-wrap text-sm leading-relaxed" style={{ color: "rgb(var(--color-text) / 0.75)" }}>
                                                {item.answer}
                                            </p>
                                        </div>
                                    );
                                })()}

                                {/* Verify */}
                                {(item.session_type === 'verify' || item.session_type === 'research' || item.session_type === 'explain') && (
                                    <div className="mt-3">
                                        <ShareButton
                                            feature={item.session_type as ShareFeature}
                                            queryId={String(item.id)}
                                            queryText={item.question}
                                            // New-format Verify rows store JSON — the SHARE text is the
                                            // summary line inside it (the exact string legacy rows stored
                                            // whole); never publish the raw payload.
                                            answerText={verifyParsed?.summary ?? item.answer}
                                            citations={[]}
                                            source="history"
                                        />
                                    </div>
                                )}

                                {/* Verify — VerifyResponse-shaped JSON rows (HISTORY car segment 1)
                                    safe-parse into the SAME cards the live /verify page renders
                                    (shared VerifyInteractionCard: enum-keyed labels, AI-severity
                                    marker, attribution_kind captions). Legacy summary-only rows
                                    fall back to the plain box unchanged — no backfill possible. */}
                                {item.session_type === 'verify' && (() => {
                                    const parsed = verifyParsed;
                                    if (parsed) {
                                        const isFailed = parsed.verification_status === 'failed_no_data';
                                        const summaryDisplay = getInteractionSummaryDisplay(lang, parsed.interactions);
                                        return (
                                            <div className="space-y-4">
                                                <div className="flex justify-between items-start gap-3">
                                                    {isFailed ? (
                                                        <div className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-sm flex-1">
                                                            <p className="font-medium text-warning mb-1">⚠️ {ui.verifyFailedMsg}</p>
                                                            <p className="text-text/70">{ui.verifyFailedAdvice}</p>
                                                        </div>
                                                    ) : (
                                                        <p className="text-sm font-medium" style={{ color: summaryDisplay.color }}>
                                                            {summaryDisplay.text}
                                                        </p>
                                                    )}
                                                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border flex-shrink-0 ${isFailed ? 'bg-warning/10 text-warning border-warning/30' : getRiskBadgeClass(parsed.risk_level ?? '')}`}>
                                                        {isFailed ? ui.verifyDeferredBadge : getRiskLevelLabel(lang, parsed.risk_level ?? 'Unknown')}
                                                    </span>
                                                </div>
                                                {(parsed.tfda_groundings?.length ?? 0) > 0 && (
                                                    <div className="space-y-0.5">
                                                        {parsed.tfda_groundings!.map((g, i) => (
                                                            <p key={i} className="text-xs text-text/50">
                                                                {(g.is_combo ? ui.verifyTfdaGroundingComboNote : ui.verifyTfdaGroundingNote)
                                                                    .replace('{query}', g.query)
                                                                    .replace('{ingredients}', g.ingredients.join(' + '))}
                                                            </p>
                                                        ))}
                                                    </div>
                                                )}
                                                {parsed.interactions.length > 0 && (
                                                    <div className="space-y-3">
                                                        {parsed.interactions.map((interaction, idx) => (
                                                            <VerifyInteractionCard key={idx} interaction={interaction} lang={lang} />
                                                        ))}
                                                    </div>
                                                )}
                                                {parsed.disclaimer && (
                                                    <p className="text-xs text-text/40 pt-2 border-t border-text/10">
                                                        ⚠️ {parsed.disclaimer}
                                                    </p>
                                                )}
                                            </div>
                                        );
                                    }
                                    // Fallback: legacy pre-segment-1 summary rows — render unchanged.
                                    return (
                                        <div className="space-y-4">
                                            <div className="rounded-lg p-4" style={{ background: "rgb(var(--color-text) / 0.05)" }}>
                                                <p className="text-sm" style={{ color: "rgb(var(--color-text) / 0.75)" }}>{item.answer}</p>
                                            </div>
                                        </div>
                                    );
                                })()}
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}

export default function History() {
    const { lang } = useLang();
    const extra = getExtra(lang);
    return (
        <PageShell
            activePage="history"
            extraHead={
                <>
                    <Head>
                        <meta name="robots" content="noindex, nofollow" />
                    </Head>
                    <style>{`
                        .history-question::selection { background: rgb(var(--color-text) / 0.15); color: rgb(var(--color-text) / 0.85); }
                        .history-question::-moz-selection { background: rgb(var(--color-text) / 0.15); color: rgb(var(--color-text) / 0.85); }
                    `}</style>
                </>
            }
        >
            <div className="container mx-auto px-4 py-10 max-w-3xl">
                <h1 className="text-2xl font-bold mb-8 tracking-tight" style={{ color: "rgb(var(--color-text))" }}>
                    {extra.historyPageTitle}
                </h1>
                <HistoryList />
            </div>
        </PageShell>
    );
}