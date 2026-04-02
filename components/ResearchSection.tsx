"use client"

import { ReactNode } from 'react';

interface ResearchSectionProps {
    title: string;
    evidence: '\u{1F7E2}' | '\u{1F7E1}' | '\u{1F534}' | null;
    children: ReactNode;
}

const borderColors: Record<string, string> = {
    '\u{1F7E2}': '#22c55e',
    '\u{1F7E1}': '#eab308',
    '\u{1F534}': '#ef4444',
};

export default function ResearchSection({ title, evidence, children }: ResearchSectionProps) {
    const borderColor = evidence ? borderColors[evidence] || '#475569' : '#475569';

    return (
        <div
            className="rounded-lg p-4 mb-4"
            style={{
                background: 'rgba(30,41,59,0.3)',
                borderLeft: `3px solid ${borderColor}`,
            }}
        >
            <p className="text-sm font-semibold mb-2" style={{ color: '#e2e8f0' }}>
                {title}
            </p>
            <div>{children}</div>
        </div>
    );
}
