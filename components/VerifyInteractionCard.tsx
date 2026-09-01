"use client"

import type { LangCode } from '../utils/i18n';
import { formatInteractionSummary, getSeverityLabel, getAiSeverityNote,
         getSourceCaptionByKind, getSourcePrefix } from '../utils/i18n-verify';
import { getUI } from '../utils/i18n-ui';

// Shared Verify result-card rendering — extracted VERBATIM from pages/verify.tsx
// (HISTORY car segment 1) so /history inherits the same mitigations the live page
// applies around this data: severity/risk labels resolved from the CANONICAL enum
// (never the stored severity_label free-text), the Option-C AI-severity marker,
// and attribution captions keyed off the STABLE attribution_kind enum (never the
// raw English `source` string). Consumed by pages/verify.tsx (live results) and
// pages/history.tsx (stored VerifyResponse-shaped JSON rows).

export interface DrugInteraction {
    drug_pair: [string, string];
    severity: string;                 // canonical enum (Critical/Major/Moderate/Minor)
    severity_label?: string | null;   // localized display (e.g. "嚴重")
    description: string;
    clinical_recommendation: string;
    source: string;
    source_url?: string;
    attribution_kind?: string;        // stable Option-C key: dailymed_grounded | openfda_analysis | no_label
}

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

export const getRiskBadgeClass = (level: string) => {
    const map: Record<string, string> = {
        Critical: 'bg-danger/10 text-danger border-danger/30',
        Major:    'bg-danger/10 text-danger border-danger/30',
        Moderate: 'bg-warning/10 text-warning border-warning/30',
        Minor:    'bg-info/10 text-info border-info/30',
        Low:      'bg-success/10 text-success border-success/30',
    };
    return map[level] ?? 'bg-text/8 text-text/70 border-text/15';
};

// Localized summary line recomputed CLIENT-SIDE from the interactions array
// (canonical-enum buckets), never the server-built English `summary` string.
export const getInteractionSummaryDisplay = (lang: LangCode, interactions: DrugInteraction[]) => {
    if (interactions.length === 0) {
        return { text: getUI(lang).noInteractions, color: 'rgb(var(--color-text) / 0.5)' };
    }
    const severityOrder = ['Critical', 'Major', 'Moderate', 'Minor'];
    // Accumulate counts by canonical severity enum. Labels are resolved
    // frontend-side from the enum via i18n-verify (NOT the LLM's
    // severity_label free-text, which leaks wrong-language values).
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

export default function VerifyInteractionCard({ interaction, lang }: { interaction: DrugInteraction; lang: LangCode }) {
    return (
        <div className={`border-l-4 rounded-lg p-4 ${getSeverityStyle(interaction.severity)}`}>
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
    );
}
