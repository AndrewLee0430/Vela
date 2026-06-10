"use client"

import { ReactNode } from 'react';

interface ResearchSectionProps {
    title: string;
    children: ReactNode;
}

// Neutral card. The left accent is purely structural (no evidence/quality
// semantics) — the trust signal lives in the per-answer ProvenanceLine, driven
// by real retrieved-source counts, not a model self-label.
export default function ResearchSection({ title, children }: ResearchSectionProps) {
    return (
        <div
            className="rounded-lg p-4 mb-4"
            style={{
                background: 'rgb(var(--color-text) / 0.06)',
                borderLeft: '3px solid rgb(var(--color-text) / 0.15)',
            }}
        >
            <p className="text-sm font-semibold mb-2" style={{ color: 'rgb(var(--color-text))' }}>
                {title}
            </p>
            <div>{children}</div>
        </div>
    );
}
