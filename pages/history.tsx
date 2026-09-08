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
import { FallbackBanner, ProvenanceLine } from '../components/ResearchTrustSignal';
import CitationPanel, { type Citation } from '../components/CitationPanel';
import VerifyInteractionCard, { type DrugInteraction, getRiskBadgeClass, getInteractionSummaryDisplay } from '../components/VerifyInteractionCard';
import type { LangCode } from '../utils/i18n';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';
import { getExtra } from '../utils/i18n-extra';
import { getShare } from '../utils/i18n-share';
import { getRiskLevelLabel } from '../utils/i18n-verify';
import { parseResearchSections, stripLlmDisclaimer } from '../utils/researchSections';
import { getResearchDisclaimer } from '../utils/researchDisclaimer';

// ─── Design System ────────────────────────────────────────────────────────────
// C3: feature accents collapsed — features distinguished by label only, not color.
// HISTORY HONESTY car segment 3: the badge text comes from the EXISTING nav keys
// (utils/i18n-extra navResearch / navVerify / navExplain, 16 locales — the same
// strings Navbar + MobileNav show), not an English literal map that read
// "Research" under every UI language. Unknown session types keep the
// capitalized raw type — never blank.
function getFeatureLabel(type: string, lang: LangCode): string {
    const extra = getExtra(lang);
    const labels: Record<string, string> = {
        research: extra.navResearch,
        verify:   extra.navVerify,
        explain:  extra.navExplain,
    };
    return labels[type] ?? (type.charAt(0).toUpperCase() + type.slice(1));
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
    // "ok" | "failed_no_data" | "failed_analysis" — deferred_ambiguous_brand never persists (defer path writes no row)
    verification_status?: string | null;
}

function parseVerifyAnswer(answer: string): VerifyHistoryPayload | null {
    try {
        const p = JSON.parse(answer);
        if (p && Array.isArray(p.interactions)) return p as VerifyHistoryPayload;
    } catch {}
    return null;
}

// Research rows: research_v1 JSON (HISTORY car segment 3, half B) — the answer
// MARKDOWN plus the SAME citation list the live /research page streamed
// (api/server.py _research_history_payload). Same safe-parse-with-fallback
// pattern as Verify/Explain: null for pre-segment-3 plain-markdown rows,
// malformed JSON and foreign/unknown kinds — those render the raw stored text
// through the half-A path. NO backfill exists for old rows (citations were
// never written and no correlation key exists), so their [N] markers stay
// literal forever.
interface ResearchHistoryPayload {
    kind: 'research_v1';
    answer: string;
    citations: Citation[];
    // HISTORY HONESTY car segment 2 (founder ruling D2 (i) 2026-09-04): OPTIONAL —
    // true iff the live stream fell back to LLM knowledge (no literature retrieved).
    // Rows written before segment 2 have no key → undefined = UNKNOWN, never false.
    // Rendered by researchTrustSignal() below (segment 3): true → FallbackBanner,
    // false + citations → ProvenanceLine, UNKNOWN → neither.
    fallback?: boolean;
}

function parseResearchAnswer(answer: string): ResearchHistoryPayload | null {
    try {
        const p = JSON.parse(answer);
        if (p && p.kind === 'research_v1' && typeof p.answer === 'string') {
            return {
                kind: 'research_v1',
                answer: p.answer,
                citations: Array.isArray(p.citations) ? p.citations : [],
                fallback: typeof p.fallback === 'boolean' ? p.fallback : undefined,
            };
        }
    } catch {}
    return null;
}

// HISTORY HONESTY car segment 3 — the trust-signal decision for a STORED row,
// mirroring the /research render rule (fallback wins; provenance only with ≥1
// citation) with ONE addition the live page never faces: rows whose flag is
// UNKNOWN (pre-segment-2 — no key, or a non-boolean) get NEITHER, even when
// citations are present. An absent flag is never rendered as grounded
// (founder-overridable at the gate — baton §5). Pure and hook-free so the
// .mjs guard can extract and execute it verbatim; /research's `!loading` gate
// has no counterpart here — a stored row is never mid-stream.
function researchTrustSignal(parsed: ResearchHistoryPayload | null): 'fallback' | 'provenance' | 'none' {
    if (!parsed) return 'none';
    if (parsed.fallback === true) return 'fallback';
    if (parsed.fallback === false && parsed.citations.length > 0) return 'provenance';
    return 'none';
}
// ─────────────────────────────────────────────────────────────────────────────

// Mirrors ChatHistoryEntry (api/server.py) — the GET /api/history response
// model no longer serializes user_id (delete segment, recon §7-D1).
interface HistoryItem {
    id: number;
    session_type: string;
    question: string;
    answer: string;
    created_at: string;
}

function TypeTag({ type, lang }: { type: string; lang: LangCode }) {
    return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide bg-text/8 text-text/85 border border-text/15">
            {getFeatureLabel(type, lang)}
        </span>
    );
}

function HistoryList() {
    const { getToken } = useAuth();
    const { lang } = useLang();
    const ui = getUI(lang);
    const extra = getExtra(lang);
    const share = getShare(lang);
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedId, setExpandedId] = useState<number | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<HistoryItem | null>(null);
    const [deletingId, setDeletingId] = useState<number | null>(null);
    const [deleteError, setDeleteError] = useState(false);
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

    async function handleConfirmDelete() {
        if (!deleteTarget) return;
        setDeletingId(deleteTarget.id);
        setDeleteError(false);
        try {
            const token = await getToken({ skipCache: true });
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/history/${deleteTarget.id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (!res.ok) throw new Error('delete failed');
            setHistory(prev => prev.filter(i => i.id !== deleteTarget.id));
            if (expandedId === deleteTarget.id) setExpandedId(null);
            setDeleteTarget(null);
        } catch {
            // Keep the dialog open with the write-failure string — the user
            // can retry or cancel; the row is still in the list.
            setDeleteError(true);
        } finally {
            setDeletingId(null);
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
        <>
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
                const researchParsed = item.session_type === 'research' ? parseResearchAnswer(item.answer) : null;

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
                                <TypeTag type={item.session_type} lang={lang} />
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
                                    /research page uses. research_v1 rows (segment 3, half B) carry the
                                    markdown under `answer` and the streamed citation list, rendered
                                    through the SAME CitationPanel as /research; the section parser is
                                    always fed the MARKDOWN, never the JSON. Bare [N] markers stay plain
                                    text exactly as on /research (no marker→link mapping exists there
                                    either — resolution is the adjacent panel). Pre-segment-3 rows are
                                    plain markdown with no citations (unbackfillable); non-conforming /
                                    legacy / malformed rows fall back to the pre-wrap rendering.
                                    HISTORY HONESTY car segment 3: the FallbackBanner / ProvenanceLine
                                    trust signal renders above the answer from the persisted `fallback`
                                    flag (segment 2, fly 247); pre-segment-2 rows (UNKNOWN) get neither.
                                    HISTORY HONESTY car segment 4a: the SAME disclaimer line /research renders
                                    (shared utils/researchDisclaimer.ts, same tokens) now closes the answer body
                                    on BOTH paths, keyed by the UI `lang` — research_v1 stores no language, and
                                    /research's key is the UI-resolved response language anyway. */}
                                {item.session_type === 'research' && (() => {
                                    const markdown = researchParsed?.answer ?? item.answer;
                                    const sections = markdown ? parseResearchSections(stripLlmDisclaimer(markdown)) : null;
                                    // Single trust signal, mutually exclusive, ABOVE the answer as on
                                    // /research (Rule 19 carry-across of the shared components): the
                                    // persisted flag decides — see researchTrustSignal().
                                    const trustSignal = researchTrustSignal(researchParsed);
                                    const trustBlock = trustSignal === 'fallback'
                                        ? <FallbackBanner lang={lang} />
                                        : trustSignal === 'provenance' && researchParsed
                                            ? <ProvenanceLine citations={researchParsed.citations} lang={lang} />
                                            : null;
                                    // Same container + English-references caption as the /research right
                                    // column (Rule 19 carry-across); renders only when the row carries ≥1
                                    // citation — legacy rows have none to show and must not claim otherwise.
                                    const citationBlock = researchParsed && researchParsed.citations.length > 0 ? (
                                        <div className="mt-5 rounded-xl p-6" style={{ background: "rgb(var(--color-text) / 0.06)", border: "1px solid rgb(var(--color-text) / 0.1)" }}>
                                            {lang !== 'en' && (
                                                <p className="text-xs mb-3 text-text/40">
                                                    {ui.citationLanguageNote}
                                                </p>
                                            )}
                                            <CitationPanel citations={researchParsed.citations} />
                                        </div>
                                    ) : null;
                                    if (sections) {
                                        return (
                                            <div>
                                                {trustBlock}
                                                {sections.map((sec, i) => (
                                                    <ResearchSection key={i} title={sec.title}>
                                                        <div className="prose max-w-none prose-sm prose-headings:font-semibold prose-h2:text-base" style={researchProseStyle}>
                                                            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>{sec.content}</ReactMarkdown>
                                                        </div>
                                                    </ResearchSection>
                                                ))}
                                                <p className="text-xs mt-3 mb-1" style={{ color: 'rgb(var(--color-text) / 0.35)' }}>
                                                    {getResearchDisclaimer(lang)}
                                                </p>
                                                {citationBlock}
                                            </div>
                                        );
                                    }
                                    return (
                                        <div>
                                            {trustBlock}
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
                                                    {markdown}
                                                </p>
                                            </div>
                                            <p className="text-xs mt-3" style={{ color: 'rgb(var(--color-text) / 0.35)' }}>
                                                {getResearchDisclaimer(lang)}
                                            </p>
                                            {citationBlock}
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

                                {/* Verify — VerifyResponse-shaped JSON rows (HISTORY car segment 1)
                                    safe-parse into the SAME cards the live /verify page renders
                                    (shared VerifyInteractionCard: enum-keyed labels, AI-severity
                                    marker, attribution_kind captions). Legacy summary-only rows
                                    fall back to the plain box unchanged — no backfill possible. */}
                                {item.session_type === 'verify' && (() => {
                                    const parsed = verifyParsed;
                                    if (parsed) {
                                        const isFailedNoData = parsed.verification_status === 'failed_no_data';
                                        // HISTORY HONESTY car segment 2b (Rule 19 carry-across from /verify):
                                        // labels FOUND, both LLM attempts failed — same banner, its own headline.
                                        const isFailedAnalysis = parsed.verification_status === 'failed_analysis';
                                        const isFailed = isFailedNoData || isFailedAnalysis;
                                        const summaryDisplay = getInteractionSummaryDisplay(lang, parsed.interactions);
                                        return (
                                            <div className="space-y-4">
                                                <div className="flex justify-between items-start gap-3">
                                                    {isFailed ? (
                                                        <div className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-sm flex-1">
                                                            <p className="font-medium text-warning mb-1">⚠️ {isFailedAnalysis ? ui.verifyFailedAnalysisMsg : ui.verifyFailedMsg}</p>
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
                                                {!isFailed && parsed.interactions.length > 0 && (
                                                    <div className="space-y-3">
                                                        {parsed.interactions.map((interaction, idx) => (
                                                            <VerifyInteractionCard key={idx} interaction={interaction} lang={lang} />
                                                        ))}
                                                    </div>
                                                )}
                                                {parsed.disclaimer && (
                                                    <p className="text-xs text-text/40 pt-2 border-t border-text/10">
                                                        {/* The localized disclaimer string carries its own ⚠️ in all
                                                            16 locales — do not prepend a second marker here. */}
                                                        {parsed.disclaimer}
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

                                {/* Footer: share + per-entry delete. The delete control renders for
                                    EVERY session type (legacy/unknown rows included — any id works);
                                    Share stays gated to the three shareable features. */}
                                <div className="mt-3 flex items-center justify-between gap-3">
                                    {(item.session_type === 'verify' || item.session_type === 'research' || item.session_type === 'explain') ? (
                                        <ShareButton
                                            feature={item.session_type as ShareFeature}
                                            queryId={String(item.id)}
                                            queryText={item.question}
                                            // New-format Verify rows store JSON — the SHARE text is the
                                            // summary line inside it (the exact string legacy rows stored
                                            // whole); new-format Research rows share their MARKDOWN.
                                            // Never publish a raw payload to a public page.
                                            answerText={verifyParsed?.summary ?? researchParsed?.answer ?? item.answer}
                                            citations={[]}
                                            source="history"
                                        />
                                    ) : <span />}
                                    <button
                                        type="button"
                                        onClick={() => { setDeleteError(false); setDeleteTarget(item); }}
                                        className="px-3 py-1.5 text-xs font-medium rounded-lg transition-colors cursor-pointer flex-shrink-0"
                                        style={{
                                            background: 'transparent',
                                            border: '1px solid rgb(var(--color-danger) / 0.4)',
                                            color: 'rgb(var(--color-danger))',
                                        }}
                                    >
                                        {ui.historyDeleteBtn}
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                );
            })}
        </div>

        {/* Per-entry delete confirm dialog — third inline confirm modal in the
            codebase (after MySharesTab + Navbar); shared-modal extraction is
            filed as debt (founder ruling #6). Confirm text states
            irreversibility by construction — do NOT swap in the revoke string
            (revoke is reversible; this is not). */}
        {deleteTarget && (
            <div
                className="fixed inset-0 z-50 flex items-center justify-center p-4"
                style={{ background: 'rgba(0,0,0,0.7)' }}
                onClick={() => { if (deletingId === null) setDeleteTarget(null); }}
            >
                <div
                    role="dialog"
                    aria-modal="true"
                    className="w-full max-w-md rounded-2xl p-6 bg-bg-2 border border-text/12"
                    onClick={e => e.stopPropagation()}
                >
                    <h2 className="text-base font-semibold mb-3 text-text">
                        {ui.historyDeleteBtn}
                    </h2>
                    <p className="text-sm mb-5 text-text/70">
                        {ui.historyDeleteConfirm}
                    </p>
                    {deleteError && (
                        <p className="text-sm mb-4" style={{ color: 'rgb(var(--color-danger))' }}>
                            {ui.historyDeleteError}
                        </p>
                    )}
                    <div className="flex justify-end gap-2">
                        <button
                            type="button"
                            onClick={() => setDeleteTarget(null)}
                            disabled={deletingId !== null}
                            className="px-4 py-2 text-sm font-medium rounded-lg transition-colors cursor-pointer border border-text/20 text-text/85 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {share.modalCancel}
                        </button>
                        <button
                            type="button"
                            onClick={handleConfirmDelete}
                            disabled={deletingId !== null}
                            className="px-4 py-2 text-sm font-medium rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                            style={{ background: 'rgb(var(--color-danger) / 0.15)', border: '1px solid rgb(var(--color-danger) / 0.4)', color: 'rgb(var(--color-danger))' }}
                        >
                            {deletingId !== null ? ui.historyDeleting : ui.historyDeleteBtn}
                        </button>
                    </div>
                </div>
            </div>
        )}
        </>
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