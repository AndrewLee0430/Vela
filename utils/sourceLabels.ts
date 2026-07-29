// utils/sourceLabels.ts
// Single source of truth for how a citation's source_type is shown to users.
// Imported by the reference card, the panel sub-header, and the answer provenance
// line so the three can never drift. A1 design: ONE user-language source name per
// card (no separate credibility badge); credibility was a synonym for source_type,
// so the trust detail lives in the source-name tooltip instead.
//
// Key relabels:
//  - `local` (our cached FDA drug labeling, relabeled from `fda_label` in the
//    vector store) DISPLAYS as "FDA" and MERGES with live `fda` into one bucket —
//    both are FDA official drug labeling. The internal word "Local" never reaches users.
//  - `dailymed` reserved for Phase 1B (official drug labeling family).
//  - `localauthority` → neutral "Source" (unproven as FDA, never produced today —
//    do NOT misattribute FDA trust to it).
// Colors live nowhere here: source names render in the neutral text token; no source
// wears a semantic/quality color (the old PubMed success-green was misleading).

// PRD 2.3 citation source_type enum (lowercase, canonical) + dailymed (Phase 1B).
export type CitationSourceType =
    | 'pubmed'
    | 'fda'
    | 'tfda'
    | 'dailymed'
    | 'loinc'
    | 'medlineplus'
    | 'rxnorm'
    | 'who'
    | 'nice'
    | 'ema'
    | 'cochrane'
    | 'local'
    | 'localauthority'
    | 'other';

// Minimal structural shape so this module does not depend on the full Citation
// interface (avoids a circular import with CitationPanel).
export interface SourceLike {
    source_type?: string;
    url?: string;
}

// tooltipKey references a UITranslations key, resolved per-language by the component
// via getUI(lang)[tooltipKey]. The trust copy is reused from the old credibility tips.
// labelKey (a1-ii) mirrors that pattern for the ONE non-proper-noun label (the TFDA
// scope descriptor); proper-noun labels (PubMed, FDA, …) stay static per Rule 16.
export interface SourceLabel {
    label: string;                    // static fallback (proper nouns; also the safety net)
    labelKey?: 'tfdaSourceLabel';     // optional i18n indirection, resolved via getUI
    tooltipKey?: 'peerReviewedTip' | 'officialTip';
}

// Resolve the user-language display label. Callers pass getUI(lang); the structural
// param type keeps this module free of an i18n-ui import (mirrors tooltipKey usage).
export function resolvedSourceLabel(source: SourceLabel, ui: { tfdaSourceLabel: string }): string {
    return source.labelKey ? (ui[source.labelKey] || source.label) : source.label;
}

export const SOURCE_LABELS: Record<string, SourceLabel> = {
    pubmed:         { label: 'PubMed',     tooltipKey: 'peerReviewedTip' },
    fda:            { label: 'FDA',        tooltipKey: 'officialTip' },
    // ⛔ LEGACY-ONLY as of 2026-07-29 (c1): the local drug corpus is DEPRECATED and no
    // longer retrieved (`api/server.py` enable_local=False), so NEW answers can never
    // carry source_type 'local'. This entry is KEPT ON PURPOSE as a fallback for
    // PERSISTED citations — shared/explore public pages re-render on demand from stored
    // citation JSON (share_renderer.render_public_page), so removing it would silently
    // relabel already-published pages. Deleting it is NOT free: it is a user-visible
    // string change on live URLs (Rule 16). Do not remove without founder sign-off.
    local:          { label: 'FDA',        tooltipKey: 'officialTip' },   // cached FDA labeling → MERGES into FDA
    // ADR 007 grounding-lite: SCOPE-ACCURATE label (approved indication ONLY) — deliberately
    // NOT a bare "TFDA" that would imply full-label/safety authority (cf. the "FDA Label
    // Analysis" mislabel lesson). Kept as its OWN bucket — must NOT merge with FDA.
    tfda:           { label: 'TFDA 核准適應症', labelKey: 'tfdaSourceLabel', tooltipKey: 'officialTip' },
    dailymed:       { label: 'DailyMed',   tooltipKey: 'officialTip' },   // reserved (Phase 1B)
    loinc:          { label: 'LOINC' },
    medlineplus:    { label: 'MedlinePlus' },
    rxnorm:         { label: 'RxNorm' },
    who:            { label: 'WHO' },
    nice:           { label: 'NICE' },
    ema:            { label: 'EMA' },
    cochrane:       { label: 'Cochrane' },
    localauthority: { label: 'Source' },   // unproven/never-produced → neutral, NOT merged into FDA
    other:          { label: 'Source' },
};

export function detectSourceType(citation: SourceLike): CitationSourceType {
    const raw = (citation.source_type || '').toString().trim().toLowerCase();
    const known: CitationSourceType[] = [
        'pubmed', 'fda', 'tfda', 'dailymed', 'loinc', 'medlineplus', 'rxnorm',
        'who', 'nice', 'ema', 'cochrane', 'local', 'localauthority', 'other',
    ];
    if ((known as string[]).includes(raw)) return raw as CitationSourceType;

    const url = (citation.url || '').toLowerCase();
    try {
        const host = new URL(citation.url || '').hostname.toLowerCase();
        if (host.includes('pubmed.ncbi.nlm.nih.gov') || host.includes('ncbi.nlm.nih.gov/pubmed')) return 'pubmed';
        if (host.includes('fda.gov.tw')) return 'tfda';   // TW TFDA (mcp.fda.gov.tw) — BEFORE the US fda.gov check
        if (host.includes('fda.gov') || host.includes('accessdata.fda.gov')) return 'fda';
        if (host.includes('loinc.org')) return 'loinc';
        if (host.includes('medlineplus.gov')) return 'medlineplus';
        if (host.includes('dailymed.nlm.nih.gov')) return 'dailymed';   // was 'rxnorm' — DailyMed is its own official-labeling source
        if (host.includes('rxnav.nlm.nih.gov')) return 'rxnorm';
        if (host.includes('who.int')) return 'who';
        if (host.includes('nice.org.uk')) return 'nice';
        if (host.includes('ema.europa.eu')) return 'ema';
        if (host.includes('cochrane.org') || host.includes('cochranelibrary.com')) return 'cochrane';
    } catch {
        // URL parse failed — fall through to `other`
        if (url.includes('pubmed')) return 'pubmed';
        if (url.includes('fda.gov')) return 'fda';
    }
    return 'other';
}

// The single resolver every user-facing surface uses: normalize → label + tooltip.
export function sourceLabelFor(citation: SourceLike): SourceLabel {
    return SOURCE_LABELS[detectSourceType(citation)] ?? SOURCE_LABELS.other;
}

// Count-chip tooltip formatters. Live here (alongside the label map) so the
// provenance line AND the panel sub-header substitute {count}/{source} IDENTICALLY
// — the copy itself is one i18n key, the formatting is this one helper → no drift.
// Callers pass the resolved template (ui.sourceCountTip / ui.referencesCountTip).
export function sourceCountTooltip(template: string, sourceLabel: string, count: number): string {
    return template.replace('{count}', String(count)).replace('{source}', sourceLabel);
}

export function referencesCountTooltip(template: string, count: number): string {
    return template.replace('{count}', String(count));
}
