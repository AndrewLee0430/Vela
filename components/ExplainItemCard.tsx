"use client"

import { ReactNode } from 'react';
import RiskBadge, { RiskTier } from './RiskBadge';

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

// 2026-08-29 — the risk-tier COLOURED LEFT ACCENT BAR is removed (founder
// direction: the Explain result surface carried too many colours). No
// information channel is lost: the bar was a pure DUPLICATE of RiskBadge,
// which renders the same `risk_tier` as a TEXT LABEL ("General Information" /
// "Needs Attention" / "Consult Immediately") plus colour — text being the
// stronger channel of the two, and the only one a colour-blind reader could
// ever use. The enum itself is untouched and still drives the badge, the
// PostHog `risk_tier_distribution`, and the backend's yellow/red
// citation-limitation note (`api/services/explain_service.py`).
export default function ExplainItemCard({ item, children }: ExplainItemCardProps) {
    return (
        <div className="rounded-xl p-5 mb-4 bg-text/6 border border-text/10">
            <div className="flex items-start justify-between gap-3 mb-3">
                <div className="min-w-0">
                    <p className="text-base font-semibold leading-tight text-text">
                        {item.term}
                    </p>
                    {item.value && (
                        <p className="text-sm font-mono mt-0.5 break-all text-text/65">
                            {item.value}
                        </p>
                    )}
                </div>
                <RiskBadge tier={item.risk_tier} />
            </div>
            <p className="text-sm leading-relaxed whitespace-pre-line text-text/85">
                {item.explanation}
            </p>
            {children && (
                <div className="mt-3 pt-3 border-t border-t-text/8">
                    <div className="flex flex-wrap gap-1.5">{children}</div>
                </div>
            )}
        </div>
    );
}
