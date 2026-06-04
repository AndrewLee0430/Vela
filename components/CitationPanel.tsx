"use client"

import { useState } from 'react';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';
import { track } from '../utils/analytics';

// PRD 2.3 citation source_type enum (lowercase, canonical)
export type CitationSourceType =
    | 'pubmed'
    | 'fda'
    | 'loinc'
    | 'medlineplus'
    | 'rxnorm'
    | 'who'
    | 'nice'
    | 'ema'
    | 'cochrane'
    | 'local'
    | 'localauthority'
    | 'other';

export interface Citation {
    id: number;
    source_type: string; // Widened — normalized via detectSourceType() before use
    source_id: string;
    title: string;
    snippet: string;
    url: string;
    credibility: 'peer-reviewed' | 'official' | 'internal';
    year?: string;
    authors?: string;
    journal?: string;
}

function detectSourceType(citation: Citation): CitationSourceType {
    const raw = (citation.source_type || '').toString().trim().toLowerCase();
    const known: CitationSourceType[] = [
        'pubmed', 'fda', 'loinc', 'medlineplus', 'rxnorm',
        'who', 'nice', 'ema', 'cochrane', 'local', 'localauthority', 'other',
    ];
    if ((known as string[]).includes(raw)) return raw as CitationSourceType;

    const url = (citation.url || '').toLowerCase();
    try {
        const host = new URL(citation.url).hostname.toLowerCase();
        if (host.includes('pubmed.ncbi.nlm.nih.gov') || host.includes('ncbi.nlm.nih.gov/pubmed')) return 'pubmed';
        if (host.includes('fda.gov') || host.includes('accessdata.fda.gov')) return 'fda';
        if (host.includes('loinc.org')) return 'loinc';
        if (host.includes('medlineplus.gov')) return 'medlineplus';
        if (host.includes('dailymed.nlm.nih.gov') || host.includes('rxnav.nlm.nih.gov')) return 'rxnorm';
        if (host.includes('who.int')) return 'who';
        if (host.includes('nice.org.uk')) return 'nice';
        if (host.includes('ema.europa.eu')) return 'ema';
        if (host.includes('cochrane.org') || host.includes('cochranelibrary.com')) return 'cochrane';
    } catch {
        // URL parse failed — fall through to `other`
        if (url.includes('pubmed')) return 'pubmed';
        if (url.includes('fda.gov')) return 'fda';
    }
    return 'other';
}

interface CitationPanelProps {
    citations: Citation[];
    isLoading?: boolean;
}

function useCredibilityConfig() {
    const { lang } = useLang();
    const ui = getUI(lang);
    return {
        'peer-reviewed': { label: ui.peerReviewed, bg: 'rgba(255,142,110,0.15)', color: '#ff8e6e', tooltip: ui.peerReviewedTip },
        'official':      { label: ui.official,       bg: 'rgba(99,179,237,0.15)',  color: '#63b3ed', tooltip: ui.officialTip },
        'internal':      { label: ui.internal,       bg: 'rgba(160,174,192,0.15)', color: '#a0aec0', tooltip: ui.internalTip },
    };
}

const sourceTypeConfig: Record<CitationSourceType, { label: string; color: string }> = {
    'pubmed':        { label: 'PubMed',      color: '#68d391' },
    'fda':           { label: 'FDA',         color: '#63b3ed' },
    'loinc':         { label: 'LOINC',       color: '#f6ad55' },
    'medlineplus':   { label: 'MedlinePlus', color: '#9f7aea' },
    'rxnorm':        { label: 'RxNorm',      color: '#ed64a6' },
    'who':           { label: 'WHO',         color: '#4fd1c5' },
    'nice':          { label: 'NICE',        color: '#90cdf4' },
    'ema':           { label: 'EMA',         color: '#fbb6ce' },
    'cochrane':      { label: 'Cochrane',    color: '#b794f4' },
    'local':         { label: 'Local',       color: '#a0aec0' },
    'localauthority':{ label: 'Local',       color: '#a0aec0' },
    'other':         { label: 'Source',      color: '#a0aec0' },
};

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
    const credibilityConfig = useCredibilityConfig();

    const normalizedSourceType = detectSourceType(citation);
    const sourceConfig = sourceTypeConfig[normalizedSourceType];
    const credConfig   = credibilityConfig[citation.credibility];
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

    const sourceStats = citations.reduce((acc, c) => {
        acc[c.source_type] = (acc[c.source_type] || 0) + 1;
        return acc;
    }, {} as Record<string, number>);

    return (
        <div className="h-full flex flex-col">
            <p className="text-xs font-semibold text-text/50 uppercase tracking-wider mb-2">
                {ui.referencesTitle} ({citations.length})
            </p>

            <div className="flex gap-2 mb-4 text-xs">
                {Object.entries(sourceStats).map(([source, count]) => (
                    <span
                        key={source}
                        className="px-2 py-1 rounded-full bg-text/8 text-text/65"
                    >
                        {source}: {count}
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