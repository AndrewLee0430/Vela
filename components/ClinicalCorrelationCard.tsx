"use client"

import { ReactNode } from 'react';
import RiskBadge, { RiskTier, RISK_BORDER_COLOR } from './RiskBadge';
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

export default function ClinicalCorrelationCard({ correlation, children }: ClinicalCorrelationCardProps) {
    const borderColor = RISK_BORDER_COLOR[correlation.risk_tier];
    return (
        <div
            className="rounded-xl p-5 mb-4"
            style={{
                background: 'rgba(139,92,246,0.06)',
                border: '1px solid rgba(139,92,246,0.2)',
                borderLeft: `3px solid ${borderColor}`,
            }}
        >
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
