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
export interface SourceLabel {
    label: string;
    tooltipKey?: 'peerReviewedTip' | 'officialTip';
}

export const SOURCE_LABELS: Record<string, SourceLabel> = {
    pubmed:         { label: 'PubMed',     tooltipKey: 'peerReviewedTip' },
    fda:            { label: 'FDA',        tooltipKey: 'officialTip' },
    local:          { label: 'FDA',        tooltipKey: 'officialTip' },   // cached FDA labeling → MERGES into FDA
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
        'pubmed', 'fda', 'dailymed', 'loinc', 'medlineplus', 'rxnorm',
        'who', 'nice', 'ema', 'cochrane', 'local', 'localauthority', 'other',
    ];
    if ((known as string[]).includes(raw)) return raw as CitationSourceType;

    const url = (citation.url || '').toLowerCase();
    try {
        const host = new URL(citation.url || '').hostname.toLowerCase();
        if (host.includes('pubmed.ncbi.nlm.nih.gov') || host.includes('ncbi.nlm.nih.gov/pubmed')) return 'pubmed';
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
