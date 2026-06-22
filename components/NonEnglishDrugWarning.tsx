import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';
import { track } from '../utils/analytics';

// ADR 003 — Verify force-English guidance. Shown when the user submits a drug
// line containing non-Latin script. Read-only external drug-lookup links + two
// actions ("I'll edit" primary / "Submit anyway" secondary). No backend/LLM
// drug resolution — guidance only.

// Each entry links to an official/authoritative DRUG-LOOKUP page (not a homepage).
// `label` is a proper noun (kept in English per CLAUDE.md Rule 16).
const HELP_LINKS: { label: string; url: string }[] = [
    // Taiwan FDA 西藥許可證查詢 (drug-license search). NOTE: curl could not verify
    // (HTTP 000 — gov server blocks automated probes; parent fda.gov.tw is live 200).
    { label: 'TFDA', url: 'https://info.fda.gov.tw/MLMS/H0001.aspx' },
    // Drugs.com Drug Interactions Checker (most relevant for Verify).
    { label: 'Drugs.com', url: 'https://www.drugs.com/drug_interactions.html' },
    // PMDA (Japan) approved drug information (English). Verified 200.
    { label: 'PMDA', url: 'https://www.pmda.go.jp/english/review-services/reviews/approved-information/drugs/0001.html' },
    // MFDS (Korea) integrated drug information (nedrug). Verified 200.
    { label: 'MFDS', url: 'https://nedrug.mfds.go.kr/index' },
];

interface NonEnglishDrugWarningProps {
    onModify: () => void;
    onProceed: () => void;
}

export default function NonEnglishDrugWarning({ onModify, onProceed }: NonEnglishDrugWarningProps) {
    const { lang } = useLang();
    const ui = getUI(lang);
    return (
        <div className="rounded-xl p-4 mb-4" style={{
            background: 'rgb(var(--color-warning) / 0.08)',
            border: '1px solid rgb(var(--color-warning) / 0.3)',
        }}>
            <div className="flex items-start gap-3">
                <span className="text-base mt-0.5" style={{ color: 'rgb(var(--color-warning))' }}>&#x26A0;</span>
                <div className="flex-1">
                    <p className="text-sm font-semibold mb-1" style={{ color: 'rgb(var(--color-text) / 0.9)' }}>
                        {ui.nonEnglishWarningTitle}
                    </p>
                    <p className="text-sm mb-3" style={{ color: 'rgb(var(--color-text) / 0.75)' }}>
                        {ui.nonEnglishWarningBody}
                    </p>

                    {/* External drug-lookup links (read-only, new tab) */}
                    <p className="text-xs mb-1" style={{ color: 'rgb(var(--color-text) / 0.6)' }}>
                        {ui.verifyInputHelpLinksLabel}
                    </p>
                    <div className="flex flex-wrap gap-2 mb-4">
                        {HELP_LINKS.map(link => (
                            <a
                                key={link.label}
                                href={link.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={() => track('non_english_help_link_clicked', { feature: 'verify', link: link.label })}
                                className="px-3 py-1 text-xs rounded-full transition-all duration-200"
                                style={{ background: 'rgb(var(--color-text) / 0.06)', border: '1px solid rgb(var(--color-text) / 0.2)', color: 'rgb(var(--color-text) / 0.8)' }}
                                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgb(var(--color-text) / 0.12)'; }}
                                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgb(var(--color-text) / 0.06)'; }}
                            >
                                {link.label} &#x2197;
                            </a>
                        ))}
                    </div>

                    <div className="flex flex-wrap gap-2">
                        {/* Primary (default-highlighted): I'll edit */}
                        <button
                            type="button"
                            onClick={onModify}
                            className="text-sm font-medium py-1.5 px-4 rounded-lg text-white transition-opacity hover:opacity-90"
                            style={{ background: 'rgb(var(--color-brand))' }}
                        >
                            {ui.verifyInputActionModify}
                        </button>
                        {/* Secondary (grey): Submit anyway (not recommended) */}
                        <button
                            type="button"
                            onClick={onProceed}
                            className="text-sm py-1.5 px-4 rounded-lg transition-colors"
                            style={{ background: 'transparent', border: '1px solid rgb(var(--color-text) / 0.3)', color: 'rgb(var(--color-text) / 0.6)' }}
                            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgb(var(--color-text) / 0.08)'; }}
                            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                        >
                            {ui.verifyInputActionProceed}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
