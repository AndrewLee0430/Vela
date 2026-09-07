"use client"

import type { LangCode } from '../utils/i18n';
import type { Citation } from './CitationPanel';
import { getUI } from '../utils/i18n-ui';
import { sourceLabelFor, resolvedSourceLabel, sourceCountTooltip } from '../utils/sourceLabels';

// Shared Research trust signal — extracted VERBATIM from pages/research.tsx
// (HISTORY HONESTY car segment 3, Rule 19 carry-across) so /history inherits
// the same mitigations the live page applies around an answer: the
// no-literature caveat (FallbackBanner) and the per-answer provenance derived
// from REAL retrieved-source counts, never a model self-label (ProvenanceLine).
// The two are mutually exclusive — the RENDER SITE decides (fallback wins;
// provenance only with ≥1 citation); these components only draw.
// `lang` is a prop (VerifyInteractionCard precedent): no hook inside, so a
// non-page consumer (tests/history_render_fallback_guard.mjs §4 renders them
// through react-dom/server) can mount them without LangContext.
// Consumed by pages/research.tsx (live stream) and pages/history.tsx (stored
// research_v1 rows reading the persisted `fallback` flag).

// Tooltip surface — theme tokens. Was `bg-white … text-gray-600` (light-only;
// baton §3.6 item 4): illegible in dark on /research, and would have been
// carried to /history as-is. --color-paper-2 (card sheet) and --color-card-border
// are defined in BOTH schemes in styles/globals.css. Exported so the Verify
// card's ⓘ tooltip uses the SAME surface (one tooltip pattern, not two).
export const TOOLTIP_STYLE: React.CSSProperties = {
    background: 'rgb(var(--color-paper-2))',
    border: '1px solid rgb(var(--color-card-border))',
    color: 'rgb(var(--color-text) / 0.75)',
};

// Source names come from the shared sourceLabels map so the line, the reference
// cards, and the panel sub-header never drift (local + fda merge into one "FDA").
export function ProvenanceLine({ citations, lang }: { citations: Citation[]; lang: LangCode }) {
    const ui = getUI(lang);
    const counts = new Map<string, number>();
    for (const c of citations) {
        const label = resolvedSourceLabel(sourceLabelFor(c), ui);
        counts.set(label, (counts.get(label) || 0) + 1);
    }
    return (
        <div className="mb-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs" style={{ color: 'rgb(var(--color-text) / 0.45)' }}>
            <span>{ui.provenanceSourced.replace('{count}', String(citations.length))}</span>
            {[...counts.entries()].map(([label, n]) => (
                <span key={label} className="relative group">
                    <span className="px-2 py-0.5 rounded-full cursor-help inline-block" style={{ background: 'rgb(var(--color-text) / 0.08)' }}>
                        {label} {n}
                    </span>
                    <span className="absolute left-0 top-full mt-2 w-56 rounded-lg shadow-lg px-3 py-2 z-50 hidden group-hover:block text-xs leading-relaxed" style={TOOLTIP_STYLE}>
                        {sourceCountTooltip(ui.sourceCountTip, label, n)}
                    </span>
                </span>
            ))}
        </div>
    );
}

export function FallbackBanner({ lang }: { lang: LangCode }) {
    const ui = getUI(lang);
    return (
        <div className="mb-4 flex items-start gap-3 p-4 rounded-lg" style={{ background: "rgb(var(--color-warning) / 0.12)", border: "1px solid rgb(var(--color-warning) / 0.3)" }}>
            <span className="text-sm mt-0.5 font-bold" style={{ color: "rgb(var(--color-warning))" }}>⚠</span>
            <div>
                <p className="text-sm font-semibold" style={{ color: "rgb(var(--color-warning))" }}>
                    {ui.noLiteratureFound}
                </p>
                <p className="text-sm mt-0.5" style={{ color: "rgb(var(--color-warning) / 0.8)" }}>
                    {ui.fallbackBasis}
                </p>
            </div>
        </div>
    );
}
