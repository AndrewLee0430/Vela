"use client"

import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';

export type RiskTier = 'green' | 'yellow' | 'red';

const RISK_COLORS: Record<RiskTier, { bg: string; text: string; border: string; solid: string }> = {
    green:  { bg: 'rgb(var(--color-success) / 0.12)', text: 'rgb(var(--color-success))', border: 'rgb(var(--color-success) / 0.3)', solid: 'rgb(var(--color-success))' },
    yellow: { bg: 'rgb(var(--color-warning) / 0.12)', text: 'rgb(var(--color-warning))', border: 'rgb(var(--color-warning) / 0.3)', solid: 'rgb(var(--color-warning))' },
    red:    { bg: 'rgb(var(--color-danger) / 0.12)',  text: 'rgb(var(--color-danger))',  border: 'rgb(var(--color-danger) / 0.3)',  solid: 'rgb(var(--color-danger))' },
};

const RISK_EMOJI: Record<RiskTier, string> = {
    green: '\u{1F7E2}',
    yellow: '\u{1F7E1}',
    red: '\u{1F534}',
};

// RISK_BORDER_COLOR (the cards' coloured left accent bar) was DELETED
// 2026-08-29 with the bars it existed for. Its only two consumers were
// ExplainItemCard and ClinicalCorrelationCard, both of which now render a
// neutral surface — verified by census, not assumed. `solid` survives in
// RISK_COLORS above because the badge's own text colour reads from it.

interface RiskBadgeProps {
    tier: RiskTier;
}

export default function RiskBadge({ tier }: RiskBadgeProps) {
    const { lang } = useLang();
    const ui = getUI(lang);
    const c = RISK_COLORS[tier];
    const label = tier === 'green' ? ui.riskGreen : tier === 'yellow' ? ui.riskYellow : ui.riskRed;
    return (
        <span
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap"
            style={{ background: c.bg, color: c.text, border: `1px solid ${c.border}` }}
        >
            <span aria-hidden="true">{RISK_EMOJI[tier]}</span>
            <span>{label}</span>
        </span>
    );
}
