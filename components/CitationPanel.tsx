"use client"

import { useState } from 'react';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';
import { track } from '../utils/analytics';
import { detectSourceType, sourceLabelFor } from '../utils/sourceLabels';

export interface Citation {
    id: number;
    source_type: string; // Widened — normalized via detectSourceType() before use
    source_id: string;
    title: string;
    snippet: string;
    url: string;
    // Full backend CredibilityLevel enum (schemas.py). The retriever currently
    // only emits peer-reviewed/official, but clinical-trial/review/internal are
    // valid values — keep the type in sync and fall back safely at lookup time.
    credibility: 'peer-reviewed' | 'official' | 'clinical-trial' | 'review' | 'internal';
    year?: string;
    authors?: string;
    journal?: string;
}

interface CitationPanelProps {
    citations: Citation[];
    isLoading?: boolean;
}

function extractAbstract(raw: string): string {
    const lines = raw.split('\n');
    const abstractIdx = lines.findIndex(l => /^#{1,3}\s*abstract/i.test(l.trim()));

    let text = '';
    if (abstractIdx !== -1) {
        text = lines.slice(abstractIdx + 1).join(' ').trim();
    } else {
        text = lines
            .filter(l => {
                const t = l.trim();
                return t.length > 0
                    && !t.startsWith('#')
                    && !/^\*\*(Authors?|Journal|PMID|Background|Methods?|Results?|Conclusions?|Objective)s?\*\*/i.test(t);
            })
            .join(' ')
            .trim();
    }

    text = text.replace(/\*\*[A-Z][A-Z\s\/]{1,20}:\*\*/g, '').trim();
    text = text.replace(/\s{2,}/g, ' ').trim();
    return text;
}

function CitationCard({ citation, position }: { citation: Citation; position: number }) {
    const [expanded, setExpanded] = useState(false);
    const { lang } = useLang();
    const ui = getUI(lang);

    const normalizedSourceType = detectSourceType(citation);
    const source = sourceLabelFor(citation);                 // one user-language source name (A1)
    const sourceTooltip = source.tooltipKey ? ui[source.tooltipKey] : undefined;
    const abstract     = extractAbstract(citation.snippet);
    const isLong       = abstract.length > 200;
    const display      = !expanded && isLong ? abstract.slice(0, 200) + '…' : abstract;

    const handleSourceClick = () => {
        // Fire-and-forget — never block the link navigation
        try {
            track('citation_clicked', {
                source_type: normalizedSourceType,
                url: citation.url,
                citation_position: position,
            });
        } catch {
            // Swallow — analytics must never break UX
        }
    };

    return (
        <div className="rounded-lg p-4 hover:shadow-md transition-shadow bg-text/7 border border-text/12">
            {/* Header — single user-language source name (neutral color). The trust
                detail that used to be a separate, redundant credibility badge now
                lives in the source name's hover tooltip. */}
            <div className="flex items-start mb-2">
                <span className="relative group">
                    <span className={`font-semibold inline-flex items-center gap-1 ${sourceTooltip ? 'cursor-help' : ''}`} style={{ color: 'rgb(var(--color-text))' }}>
                        [{citation.id}] {source.label}
                        {sourceTooltip && (
                            // Discoverability affordance: a subtle ⓘ telling users the
                            // source name is hoverable. Neutral color (no semantic color),
                            // inside the same group → hovering name OR icon shows the tooltip.
                            <svg aria-label={ui.moreInfo} role="img" className="w-3 h-3 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'rgb(var(--color-text) / 0.4)' }}>
                                <circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" />
                            </svg>
                        )}
                    </span>
                    {sourceTooltip && (
                        <span className="absolute left-0 top-full mt-2 w-64 bg-white rounded-lg shadow-lg px-4 py-3 z-50 hidden group-hover:block">
                            <span className="flex items-center gap-2 mb-1">
                                <svg className="w-4 h-4 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                                <span className="text-sm font-semibold text-gray-800">{source.label}</span>
                            </span>
                            <span className="text-xs text-gray-500 leading-relaxed block">{sourceTooltip}</span>
                        </span>
                    )}
                </span>
            </div>

            {/* Title */}
            <h4 className="font-medium mb-1 line-clamp-2 text-text">
                {citation.title}
            </h4>

            {/* Authors / Journal / Year */}
            <div className="text-sm mb-2 text-text/50">
                {citation.authors && <span>{citation.authors}</span>}
                {citation.journal && <span> • {citation.journal}</span>}
                {citation.year    && <span> ({citation.year})</span>}
            </div>

            {/* Abstract */}
            {display && (
                <div className="text-sm leading-relaxed text-text/70">
                    <p>{display}</p>
                    {isLong && (
                        <button
                            onClick={() => setExpanded(!expanded)}
                            className="text-xs mt-1 transition-colors"
                            style={{ color: "rgb(var(--color-text) / 0.5)" }}
                            onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = 'rgb(var(--color-text))'}
                            onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = 'rgb(var(--color-text) / 0.5)'}
                        >
                            {expanded ? ui.showLess : ui.showMore}
                        </button>
                    )}
                </div>
            )}

            {/* Source link */}
            <a
                href={citation.url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={handleSourceClick}
                onAuxClick={handleSourceClick}
                className="inline-flex items-center gap-1 text-sm hover:underline mt-3"
                style={{ color: "rgb(var(--color-brand))" }}
            >
                {ui.viewSource}
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
            </a>
        </div>
    );
}

function LoadingSkeleton() {
    return (
        <div className="space-y-4">
            {[1, 2, 3].map((i) => (
                <div key={i} className="rounded-lg p-4 animate-pulse bg-text/7 border border-text/12">
                    <div className="flex items-center gap-2 mb-2">
                        <div className="w-6 h-6 rounded bg-text/10"></div>
                        <div className="h-4 rounded w-20 bg-text/10"></div>
                    </div>
                    <div className="h-4 rounded w-3/4 mb-2 bg-text/10"></div>
                    <div className="h-3 rounded w-1/2 mb-2 bg-text/8"></div>
                    <div className="h-3 rounded w-full bg-text/8"></div>
                    <div className="h-3 rounded w-full mt-1 bg-text/8"></div>
                </div>
            ))}
        </div>
    );
}

export default function CitationPanel({ citations, isLoading }: CitationPanelProps) {
    const { lang } = useLang();
    const ui = getUI(lang);

    if (isLoading) {
        return (
            <div className="h-full">
                <LoadingSkeleton />
            </div>
        );
    }

    if (citations.length === 0) {
        return (
            <div className="h-full flex items-center justify-center">
                <p className="text-center text-sm text-text/40">{ui.referencesEmpty}</p>
            </div>
        );
    }

    // Group by the user-facing label (shared map) so local + fda MERGE into one
    // "FDA" bucket — matching the cards + the answer provenance line.
    const sourceStats = citations.reduce((acc, c) => {
        const label = sourceLabelFor(c).label;
        acc[label] = (acc[label] || 0) + 1;
        return acc;
    }, {} as Record<string, number>);

    return (
        <div className="h-full flex flex-col">
            <p className="text-xs font-semibold text-text/50 uppercase tracking-wider mb-2">
                {ui.referencesTitle} ({citations.length})
            </p>

            <div className="flex gap-2 mb-4 text-xs">
                {Object.entries(sourceStats).map(([label, count]) => (
                    <span
                        key={label}
                        className="px-2 py-1 rounded-full bg-text/8 text-text/65"
                    >
                        {label} {count}
                    </span>
                ))}
            </div>

            <div className="flex-1 overflow-y-auto space-y-3">
                {citations.map((citation, idx) => (
                    <CitationCard key={citation.id} citation={citation} position={idx + 1} />
                ))}
            </div>

            <div className="mt-4 pt-3 border-t border-t-text/10">
                <p className="text-xs text-center text-text/35">
                    {ui.verifyReference}
                </p>
            </div>
        </div>
    );
}