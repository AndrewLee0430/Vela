"use client"

import { ReactNode } from 'react';

interface ResearchSectionProps {
    title: string;
    evidence: '\u{1F7E2}' | '\u{1F7E1}' | '\u{1F534}' | null;
    children: ReactNode;
}

const borderColors: Record<string, string> = {
    '\u{1F7E2}': 'rgb(var(--color-success))',
    '\u{1F7E1}': 'rgb(var(--color-warning))',
    '\u{1F534}': 'rgb(var(--color-danger))',
};

export default function ResearchSection({ title, evidence, children }: ResearchSectionProps) {
    const borderColor = evidence ? borderColors[evidence] || 'rgb(var(--color-text) / 0.3)' : 'rgb(var(--color-text) / 0.3)';

    return (
        <div
            className="rounded-lg p-4 mb-4"
            style={{
                background: 'rgb(var(--color-text) / 0.06)',
                borderLeft: `3px solid ${borderColor}`,
            }}
        >
            <p className="text-sm font-semibold mb-2" style={{ color: 'rgb(var(--color-text))' }}>
                {title}
            </p>
            <div>{children}</div>
        </div>
    );
}
