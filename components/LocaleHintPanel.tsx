import { useEffect, useState } from 'react';
import { getUI } from '../utils/i18n-ui';
import type { LangCode } from '../utils/i18n';
import { track } from '../utils/analytics';
import {
  LocaleCategory,
  getAuthoritiesForCategories,
} from '../utils/localeHint';

// 在地差異提示 panel — Probe 1 (Taiwan Tier-1). Renders ONLY when the caller passes a
// non-empty matchedCategories AND lang === 'zh-TW' (the caller already gates this). It NAMES
// the dimensions that may differ in Taiwan and POINTS to TFDA/NHI for the user to verify —
// it asserts no clinical fact and implies no TFDA/NHI integration (see localeHint.note).

const CAT_LABEL_KEY: Record<LocaleCategory, 'localeHintCatDosing' | 'localeHintCatReimbursement' | 'localeHintCatIndication' | 'localeHintCatContraindication'> = {
  dosing: 'localeHintCatDosing',
  reimbursement: 'localeHintCatReimbursement',
  indication: 'localeHintCatIndication',
  contraindication: 'localeHintCatContraindication',
};

interface LocaleHintPanelProps {
  matchedCategories: LocaleCategory[];
  lang: string;
  resetKey?: string | null;   // changes per new query → re-shows a dismissed panel
}

export default function LocaleHintPanel({ matchedCategories, lang, resetKey }: LocaleHintPanelProps) {
  const ui = getUI(lang as LangCode);
  const authorities = getAuthoritiesForCategories(matchedCategories);

  // Dismissal is per-query: dismissing hides the CURRENT panel, but a NEW query (resetKey change)
  // re-shows it. (Deliberate dogfood scoping — NOT the PRD §5.1 cross-session persistence, which
  // permanently suppressed every later query and caused the "fires once then never again" bug.)
  const [dismissed, setDismissed] = useState(false);
  useEffect(() => { setDismissed(false); }, [resetKey]);

  // Fire the display event once per query the panel is shown for.
  useEffect(() => {
    if (dismissed || !matchedCategories.length || !authorities.length) return;
    track('locale_hint_displayed', {
      locale: 'TW',
      matched_categories: matchedCategories,
      authorities_shown: authorities.map(a => a.short_name),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetKey, dismissed]);

  if (dismissed || !matchedCategories.length || !authorities.length) return null;

  const onDismiss = () => {
    setDismissed(true);
    track('locale_hint_dismissed', { locale: 'TW' });
  };

  return (
    <div
      className="rounded-xl p-4 mt-4 relative"
      style={{ background: 'rgb(var(--color-warning) / 0.08)', border: '1px solid rgb(var(--color-warning) / 0.3)' }}
    >
      <button
        onClick={onDismiss}
        aria-label={ui.localeHintDismiss}
        className="absolute top-2 right-3 text-sm transition-colors"
        style={{ color: 'rgb(var(--color-text) / 0.4)' }}
        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = 'rgb(var(--color-text) / 0.8)'; }}
        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'rgb(var(--color-text) / 0.4)'; }}
      >
        &times;
      </button>

      <p className="text-sm font-semibold mb-1 pr-6" style={{ color: 'rgb(var(--color-text) / 0.9)' }}>
        {ui.localeHintTitle}
      </p>
      <p className="text-sm mb-3" style={{ color: 'rgb(var(--color-text) / 0.75)' }}>
        {ui.localeHintLead}
      </p>

      {/* Matched category chips */}
      <div className="flex flex-wrap gap-2 mb-3">
        {matchedCategories.map(cat => (
          <span
            key={cat}
            className="px-2.5 py-0.5 text-xs rounded-full"
            style={{ background: 'rgb(var(--color-text) / 0.08)', border: '1px solid rgb(var(--color-text) / 0.18)', color: 'rgb(var(--color-text) / 0.8)' }}
          >
            {ui[CAT_LABEL_KEY[cat]]}
          </span>
        ))}
      </div>

      {/* Authority links */}
      <div className="flex flex-col gap-2 mb-3">
        {authorities.map(a => (
          <a
            key={a.short_name}
            href={a.url_native}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => track('locale_hint_clicked', { locale: 'TW', authority_short_name: a.short_name })}
            className="flex items-center gap-2 text-sm transition-opacity hover:opacity-80"
            style={{ color: 'rgb(var(--color-text) / 0.85)' }}
          >
            <span
              className="px-2 py-0.5 text-[11px] rounded font-medium"
              style={{ background: 'rgb(var(--color-text) / 0.1)', color: 'rgb(var(--color-text) / 0.7)' }}
            >
              {a.short_name}
            </span>
            <span className="underline">{a.name_native}</span>
            <span aria-hidden>&#x2197;</span>
          </a>
        ))}
      </div>

      <p className="text-xs" style={{ color: 'rgb(var(--color-text) / 0.5)' }}>
        {ui.localeHintNote}
      </p>
    </div>
  );
}
