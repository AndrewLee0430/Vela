"use client"

import { ReactNode } from 'react';
import RiskBadge, { RiskTier, RISK_BORDER_COLOR } from './RiskBadge';

export interface ExplainSource {
    source_type: string;
    label: string;
    url?: string;
    description?: string;
}

export interface ExplainItem {
    term: string;
    value: string;
    explanation: string;
    risk_tier: RiskTier;
    citations: ExplainSource[];
}

interface ExplainItemCardProps {
    item: ExplainItem;
    /** Pre-rendered citation badges. Parent owns SourceBadge styling/tooltips. */
    children?: ReactNode;
}

export default function ExplainItemCard({ item, children }: ExplainItemCardProps) {
    const borderColor = RISK_BORDER_COLOR[item.risk_tier];
    return (
        <div
            className="rounded-xl p-5 mb-4"
            style={{
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderLeft: `3px solid ${borderColor}`,
            }}
        >
            <div className="flex items-start justify-between gap-3 mb-3">
                <div className="min-w-0">
                    <p className="text-base font-semibold leading-tight" style={{ color: '#ffffff' }}>
                        {item.term}
                    </p>
                    {item.value && (
                        <p
                            className="text-sm font-mono mt-0.5 break-all"
                            style={{ color: 'rgba(255,255,255,0.65)' }}
                        >
                            {item.value}
                        </p>
                    )}
                </div>
                <RiskBadge tier={item.risk_tier} />
            </div>
            <p
                className="text-sm leading-relaxed whitespace-pre-line"
                style={{ color: 'rgba(255,255,255,0.85)' }}
            >
                {item.explanation}
            </p>
            {children && (
                <div
                    className="mt-3 pt-3"
                    style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}
                >
                    <div className="flex flex-wrap gap-1.5">{children}</div>
                </div>
            )}
        </div>
    );
}
