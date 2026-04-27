"use client"

import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';

export type RiskTier = 'green' | 'yellow' | 'red';

const RISK_COLORS: Record<RiskTier, { bg: string; text: string; border: string; solid: string }> = {
    green:  { bg: 'rgba(34,197,94,0.12)', text: '#22c55e', border: 'rgba(34,197,94,0.3)', solid: '#22c55e' },
    yellow: { bg: 'rgba(234,179,8,0.12)', text: '#eab308', border: 'rgba(234,179,8,0.3)', solid: '#eab308' },
    red:    { bg: 'rgba(239,68,68,0.12)', text: '#ef4444', border: 'rgba(239,68,68,0.3)', solid: '#ef4444' },
};

const RISK_EMOJI: Record<RiskTier, string> = {
    green: '\u{1F7E2}',
    yellow: '\u{1F7E1}',
    red: '\u{1F534}',
};

export const RISK_BORDER_COLOR: Record<RiskTier, string> = {
    green: RISK_COLORS.green.solid,
    yellow: RISK_COLORS.yellow.solid,
    red: RISK_COLORS.red.solid,
};

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
