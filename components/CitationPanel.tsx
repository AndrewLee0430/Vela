"use client"

import { useState } from 'react';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';

export interface Citation {
    id: number;
    source_type: 'pubmed' | 'fda' | 'local';
    source_id: string;
    title: string;
    snippet: string;
    url: string;
    credibility: 'peer-reviewed' | 'official' | 'internal';
    year?: string;
    authors?: string;
    journal?: string;
}

interface CitationPanelProps {
    citations: Citation[];
    isLoading?: boolean;
}

function useCredibilityConfig() {
    const { lang } = useLang();
    const ui = getUI(lang);
    return {
        'peer-reviewed': { label: ui.peerReviewed, bg: 'rgba(255,142,110,0.15)', color: '#ff8e6e', stars: 5, tooltip: ui.peerReviewedTip },
        'official':      { label: ui.official,       bg: 'rgba(99,179,237,0.15)',  color: '#63b3ed', stars: 5, tooltip: ui.officialTip },
        'internal':      { label: ui.internal,       bg: 'rgba(160,174,192,0.15)', color: '#a0aec0', stars: 3, tooltip: ui.internalTip },
    };
}

const sourceTypeConfig = {
    'pubmed': { label: 'PubMed', color: '#68d391' },
    'fda':    { label: 'FDA',    color: '#63b3ed' },
    'local':  { label: 'Local',  color: '#a0aec0' },
};

function StarRating({ count }: { count: number }) {
    return (
        <span>
            {Array.from({ length: 5 }).map((_, i) => (
                <svg
                    key={i}
                    className={`inline w-4 h-4 ${i < count ? 'fill-yellow-400' : 'fill-gray-600'}`}
                    viewBox="0 0 20 20"
                >
                    <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z" />
                </svg>
            ))}
        </span>
    );
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

function CitationCard({ citation }: { citation: Citation }) {
    const [expanded, setExpanded] = useState(false);
    const { lang } = useLang();
    const ui = getUI(lang);
    const credibilityConfig = useCredibilityConfig();

    const sourceConfig = sourceTypeConfig[citation.source_type];
    const credConfig   = credibilityConfig[citation.credibility];
    const abstract     = extractAbstract(citation.snippet);
    const isLong       = abstract.length > 200;
    const display      = !expanded && isLong ? abstract.slice(0, 200) + '…' : abstract;

    return (
        <div 
            className="rounded-lg p-4 hover:shadow-md transition-shadow"
            style={{ background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.12)" }}
        >
            {/* Header */}
            <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                    <span className="font-semibold" style={{ color: sourceConfig.color }}>
                        [{citation.id}] {sourceConfig.label}
                    </span>
                </div>
                <span className="relative group flex-shrink-0 ml-2">
                    <span
                        className="text-xs px-2 py-1 rounded-full font-medium cursor-help"
                        style={{ background: credConfig.bg, color: credConfig.color }}
                    >
                        {credConfig.label}
                    </span>
                    <span className="absolute right-0 top-full mt-2 w-64 bg-white rounded-lg shadow-lg px-4 py-3 z-50 hidden group-hover:block">
                        <span className="flex items-center gap-2 mb-1">
                            <svg className="w-4 h-4 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                            <span className="text-sm font-semibold text-gray-800">{credConfig.label}</span>
                        </span>
                        <span className="text-xs text-gray-500 leading-relaxed block">{credConfig.tooltip}</span>
                    </span>
                </span>
            </div>

            {/* Title */}
            <h4 className="font-medium mb-1 line-clamp-2" style={{ color: "#ffffff" }}>
                {citation.title}
            </h4>

            {/* Authors / Journal / Year */}
            <div className="text-sm mb-2" style={{ color: "rgba(255,255,255,0.5)" }}>
                {citation.authors && <span>{citation.authors}</span>}
                {citation.journal && <span> • {citation.journal}</span>}
                {citation.year    && <span> ({citation.year})</span>}
            </div>

            {/* Credibility stars */}
            <div className="flex items-center gap-2 mb-3">
                <span className="text-xs" style={{ color: "rgba(255,255,255,0.7)" }}>{ui.credibilityLabel}</span>
                <StarRating count={credConfig.stars} />
            </div>

            {/* Abstract */}
            {display && (
                <div className="text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.7)" }}>
                    <p>{display}</p>
                    {isLong && (
                        <button
                            onClick={() => setExpanded(!expanded)}
                            className="text-xs mt-1 transition-colors"
                            style={{ color: "rgba(148,163,184,1)" }}
                            onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = '#e2e8f0'}
                            onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = 'rgba(148,163,184,1)'}
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
                className="inline-flex items-center gap-1 text-sm hover:underline mt-3"
                style={{ color: "#ff8e6e" }}
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
                <div key={i} className="rounded-lg p-4 animate-pulse" style={{ background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.12)" }}>
                    <div className="flex items-center gap-2 mb-2">
                        <div className="w-6 h-6 rounded" style={{ background: "rgba(255,255,255,0.1)" }}></div>
                        <div className="h-4 rounded w-20" style={{ background: "rgba(255,255,255,0.1)" }}></div>
                    </div>
                    <div className="h-4 rounded w-3/4 mb-2" style={{ background: "rgba(255,255,255,0.1)" }}></div>
                    <div className="h-3 rounded w-1/2 mb-2" style={{ background: "rgba(255,255,255,0.08)" }}></div>
                    <div className="h-3 rounded w-full" style={{ background: "rgba(255,255,255,0.08)" }}></div>
                    <div className="h-3 rounded w-full mt-1" style={{ background: "rgba(255,255,255,0.08)" }}></div>
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
                <p className="text-center text-sm" style={{ color: "rgba(255,255,255,0.4)" }}>{ui.referencesEmpty}</p>
            </div>
        );
    }

    const sourceStats = citations.reduce((acc, c) => {
        acc[c.source_type] = (acc[c.source_type] || 0) + 1;
        return acc;
    }, {} as Record<string, number>);

    return (
        <div className="h-full flex flex-col">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                {ui.referencesTitle} ({citations.length})
            </p>

            <div className="flex gap-2 mb-4 text-xs">
                {Object.entries(sourceStats).map(([source, count]) => (
                    <span
                        key={source}
                        className="px-2 py-1 rounded-full"
                        style={{ background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.65)" }}
                    >
                        {source}: {count}
                    </span>
                ))}
            </div>

            <div className="flex-1 overflow-y-auto space-y-3">
                {citations.map((citation) => (
                    <CitationCard key={citation.id} citation={citation} />
                ))}
            </div>

            <div className="mt-4 pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.1)" }}>
                <p className="text-xs text-center" style={{ color: "rgba(255,255,255,0.35)" }}>
                    {ui.verifyReference}
                </p>
            </div>
        </div>
    );
}