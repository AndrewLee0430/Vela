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
// 2026-08-29 (same day, founder ruled): the term chips and the 🔗 glyph — the
// last #b794f4-family raw literals — are neutralised too. They carried no
// semantic meaning (they name the correlated items, e.g. "eGFR"), so nothing
// is lost but the theme-blindness.
//
// The chips use `bg-text/12`, NOT the source chips' `bg-text/8`, and the
// reason is that the token pair states a CONTRAST DELTA, not an absolute
// colour: the source chips sit on the PAGE (a 0-alpha ground, so /8 is an
// 8-point step), while these sit ON this card (`bg-text/6`), where /8 would
// be a 2-point step and read as a smudge rather than a chip. /12 restores a
// 6-point step — the nearest existing token to the source chips' own
// contrast. Verified by rendering both variants side by side on the card in
// BOTH themes, not by arithmetic alone. Text stays `text-text/65`, identical
// to the source chips; the decorative aria-hidden glyph sits one step below
// at `text-text/45`.
export default function ClinicalCorrelationCard({ correlation, children }: ClinicalCorrelationCardProps) {
    return (
        <div className="rounded-xl p-5 mb-4 bg-text/6 border border-text/10">
            <div className="flex items-start justify-between gap-3 mb-3">
                <div className="min-w-0 flex flex-wrap items-center gap-1.5">
                    <span aria-hidden="true" className="text-sm text-text/45">
                        {'\u{1F517}'}
                    </span>
                    {correlation.items_referenced.map((term, i) => (
                        <span
                            key={i}
                            className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-text/12 text-text/65"
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
