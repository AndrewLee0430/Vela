"use client"

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

// TODO Step 5: replace with getUI(lang).riskGreen / riskYellow / riskRed
const RISK_LABELS_FALLBACK: Record<RiskTier, string> = {
    green: 'General Information',
    yellow: 'Needs Attention',
    red: 'Consult Immediately',
};

export const RISK_BORDER_COLOR: Record<RiskTier, string> = {
    green: RISK_COLORS.green.solid,
    yellow: RISK_COLORS.yellow.solid,
    red: RISK_COLORS.red.solid,
};

interface RiskBadgeProps {
    tier: RiskTier;
    /** i18n key e.g. "explain.risk.yellow". Unused in Step 4 — see TODO Step 5. */
    labelKey?: string;
}

export default function RiskBadge({ tier, labelKey }: RiskBadgeProps) {
    // labelKey is reserved for Step 5 i18n wiring (will resolve
    // via getUI(lang).riskGreen/Yellow/Red or similar). Currently
    // unused; falls back to RISK_LABELS_FALLBACK[tier].
    void labelKey;
    const c = RISK_COLORS[tier];
    return (
        <span
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap"
            style={{ background: c.bg, color: c.text, border: `1px solid ${c.border}` }}
        >
            <span aria-hidden="true">{RISK_EMOJI[tier]}</span>
            <span>{RISK_LABELS_FALLBACK[tier]}</span>
        </span>
    );
}
