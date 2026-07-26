import { useEffect, useState } from 'react';
import { getUI } from '../utils/i18n-ui';
import type { LangCode } from '../utils/i18n';
import { track } from '../utils/analytics';
import {
  LocaleCategory,
  getAuthoritiesForCategories,
  getTier1Authorities,
  TIER2_AUTHORITIES,
} from '../utils/localeHint';
import type { CountryCode, ResolutionLevel } from '../utils/country';

// 在地差異提示 panel (b1). Two independent axes (RULE 1):
//   answer language (lang)      → picks the keyword list + the panel TEXT (caller already gated it)
//   resolved country            → picks WHICH authorities (Tier-1 country data, or Tier-2 fallback)
// Resolving a country never changes the panel language; it only decides which authorities are named.
// A resolved country with no Tier-1 data yet (JP/KR/TH in b1) → Tier-2, not an empty panel (RULE 2).

const CAT_LABEL_KEY: Record<LocaleCategory, 'localeHintCatDosing' | 'localeHintCatReimbursement' | 'localeHintCatIndication' | 'localeHintCatContraindication'> = {
  dosing: 'localeHintCatDosing',
  reimbursement: 'localeHintCatReimbursement',
  indication: 'localeHintCatIndication',
  contraindication: 'localeHintCatContraindication',
};

interface LocaleHintPanelProps {
  matchedCategories: LocaleCategory[];
  lang: string;                       // answer/UI language — panel text; only 'en' / 'zh-TW' in b1
  resolvedCountry: CountryCode | null; // waterfall output — picks authorities (null → Tier-2)
  resolutionLevel: ResolutionLevel;    // which waterfall level produced the country (analytics)
  resetKey?: string | null;            // changes per new query → re-shows a dismissed panel
}

export default function LocaleHintPanel({ matchedCategories, lang, resolvedCountry, resolutionLevel, resetKey }: LocaleHintPanelProps) {
  const ui = getUI(lang as LangCode);

  const tier1 = getTier1Authorities(resolvedCountry);
  const tier: 1 | 2 = tier1 ? 1 : 2;
  const authoritySet = tier1 ? tier1.authorities : TIER2_AUTHORITIES;
  const authorities = getAuthoritiesForCategories(authoritySet, matchedCategories);

  // Country name for the heading/lead, in the PANEL language (en / zh-TW only in b1).
  const panelLang: 'en' | 'zh-TW' = lang === 'zh-TW' ? 'zh-TW' : 'en';
  const countryName = tier1 ? tier1.panel_name[panelLang] : '';
  const title = tier1 ? ui.localeHintTitle.replace('{country}', countryName) : ui.localeHintTitleTier2;
  const lead = tier1 ? ui.localeHintLead.replace('{country}', countryName) : ui.localeHintLeadTier2;

  // Dismissal is per-query: dismissing hides the CURRENT panel, but a NEW query (resetKey change)
  // re-shows it (NOT the PRD §5.1 cross-session persistence that caused "fires once then never again").
  const [dismissed, setDismissed] = useState(false);
  useEffect(() => { setDismissed(false); }, [resetKey]);

  // Fire the display event once per query the panel is shown for.
  useEffect(() => {
    if (dismissed || !matchedCategories.length || !authorities.length) return;
    track('locale_hint_displayed', {
      resolved_country: resolvedCountry,
      resolution_level: resolutionLevel,
      tier,
      matched_categories: matchedCategories,
      authorities_shown: authorities.map(a => a.short_name),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetKey, dismissed]);

  if (dismissed || !matchedCategories.length || !authorities.length) return null;

  const onDismiss = () => {
    setDismissed(true);
    track('locale_hint_dismissed', { resolved_country: resolvedCountry, tier });
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
        {title}
      </p>
      <p className="text-sm mb-3" style={{ color: 'rgb(var(--color-text) / 0.75)' }}>
        {lead}
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
            onClick={() => track('locale_hint_clicked', { resolved_country: resolvedCountry, tier, authority_short_name: a.short_name })}
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
