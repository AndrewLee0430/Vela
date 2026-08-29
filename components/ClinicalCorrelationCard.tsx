"use client"

import { ReactNode } from 'react';
import RiskBadge, { RiskTier } from './RiskBadge';
import { ExplainSource } from './ExplainItemCard';

export interface ClinicalCorrelation {
    items_referenced: string[];
    insight: string;
    risk_tier: RiskTier;
    citations: ExplainSource[];
}

interface ClinicalCorrelationCardProps {
    correlation: ClinicalCorrelation;
    /** Pre-rendered citation badges. Parent owns SourceBadge styling/tooltips. */
    children?: ReactNode;
}

// 2026-08-29 — the panel's light-PURPLE surface becomes the SAME neutral
// surface as ExplainItemCard (`bg-text/6 border border-text/10`), and the
// risk-tier left accent bar goes with it, consistent with that card. The
// purple was raw literals (`rgba(139,92,246,…)`) — theme-blind by
// construction, the fly-219/220 class.
// ⚠️ FLAGGED, NOT CHANGED (founder's call, one round-trip): the term chips
// below and the 🔗 glyph are still purple raw literals (#b794f4 family). They
// carry NO semantic meaning — they name the correlated items (e.g. "eGFR") —
// so neutralising them would delete no channel, but the founder's direction
// named the panel BACKGROUND, so scope stops here.
export default function ClinicalCorrelationCard({ correlation, children }: ClinicalCorrelationCardProps) {
    return (
        <div className="rounded-xl p-5 mb-4 bg-text/6 border border-text/10">
            <div className="flex items-start justify-between gap-3 mb-3">
                <div className="min-w-0 flex flex-wrap items-center gap-1.5">
                    <span
                        aria-hidden="true"
                        className="text-sm"
                        style={{ color: 'rgba(183,148,244,0.9)' }}
                    >
                        {'\u{1F517}'}
                    </span>
                    {correlation.items_referenced.map((term, i) => (
                        <span
                            key={i}
                            className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                            style={{
                                background: 'rgba(183,148,244,0.12)',
                                color: '#b794f4',
                                border: '1px solid rgba(183,148,244,0.3)',
                            }}
                        >
                            {term}
                        </span>
                    ))}
                </div>
                <RiskBadge tier={correlation.risk_tier} />
            </div>
            <p className="text-sm leading-relaxed whitespace-pre-line text-text/85">
                {correlation.insight}
            </p>
            {children && (
                <div className="mt-3 pt-3 border-t border-t-text/8">
                    <div className="flex flex-wrap gap-1.5">{children}</div>
                </div>
            )}
        </div>
    );
}
