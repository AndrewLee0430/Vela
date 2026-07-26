// utils/country.ts — 在地差異 (b1) COUNTRY axis. Country ≠ language (probe found `locale`
// overloaded 3 ways). This module owns COUNTRY only: the CountryCode value set, the Settings
// `locale` value type, and the pure locale-detection waterfall resolver.
//
// resolveCountry() is a PURE function (zero network, zero localStorage, zero imports) so it is
// unit-testable in isolation (tests/resolve_country_guard.mjs transpiles this file standalone).

// The 6 Tier-1 countries. OTHER is a Settings sentinel, NOT a resolvable country.
export const COUNTRY_CODES = ['TW', 'JP', 'KR', 'SG', 'MY', 'TH'] as const;
export type CountryCode = (typeof COUNTRY_CODES)[number];

// The Settings `locale` field value: a Tier-1 country, or an explicit "international" choice.
export type LocaleSetting = CountryCode | 'OTHER';

// Which waterfall level produced the result (for PostHog measurability + debugging).
export type ResolutionLevel = 'settings' | 'work_language' | 'timezone' | 'ui_lang' | 'none';

export interface CountryResolution {
  country: CountryCode | null;
  level: ResolutionLevel;
}

export interface CountrySignals {
  settingsLocale: LocaleSetting | null;   // L1 — Settings My Context country field
  workLanguage: string | null;            // L2 — vela_user_context.work_language
  timeZone: string | null;                // L3 — Intl.DateTimeFormat().resolvedOptions().timeZone
  uiLang: string | null;                  // L4 — active UI language
}

// L2 / L4 — language → country. ONLY these four are 1:1 unambiguous; en/ms/pt/es/ar are
// multi-country and zh-CN is not Tier-1, so they are deliberately absent (never guess).
const LANG_TO_COUNTRY: Record<string, CountryCode> = {
  'zh-TW': 'TW',
  ja: 'JP',
  ko: 'KR',
  th: 'TH',
};

// L3 — IANA timezone → country. SG + MY are English-speaking (no L2/L4 signal), so timezone
// is their ONLY implicit path — L3 MUST stay above L4 or they become unreachable.
const TIMEZONE_TO_COUNTRY: Record<string, CountryCode> = {
  'Asia/Taipei': 'TW',
  'Asia/Tokyo': 'JP',
  'Asia/Seoul': 'KR',
  'Asia/Singapore': 'SG',
  'Asia/Kuala_Lumpur': 'MY',
  'Asia/Bangkok': 'TH',
};

function isCountryCode(v: string): v is CountryCode {
  return (COUNTRY_CODES as readonly string[]).includes(v);
}

/**
 * Pure waterfall resolver. First level to yield a country wins; otherwise fall through;
 * nothing → { country: null, level: 'none' } (the panel then renders Tier 2).
 *
 * L1 Settings locale is authoritative: a chosen country wins; the explicit 'OTHER' sentinel
 * is TERMINAL (country: null, level: 'settings') and does NOT fall through to timezone —
 * the user has said "use international sources".
 */
export function resolveCountry(signals: CountrySignals): CountryResolution {
  const { settingsLocale, workLanguage, timeZone, uiLang } = signals;

  // L1 — Settings (authoritative)
  if (settingsLocale != null) {
    if (settingsLocale === 'OTHER') return { country: null, level: 'settings' };
    if (isCountryCode(settingsLocale)) return { country: settingsLocale, level: 'settings' };
    // any unexpected stored value: ignore and fall through
  }

  // L2 — work_language
  if (workLanguage && LANG_TO_COUNTRY[workLanguage]) {
    return { country: LANG_TO_COUNTRY[workLanguage], level: 'work_language' };
  }

  // L3 — timezone (MUST stay above L4)
  if (timeZone && TIMEZONE_TO_COUNTRY[timeZone]) {
    return { country: TIMEZONE_TO_COUNTRY[timeZone], level: 'timezone' };
  }

  // L4 — UI language
  if (uiLang && LANG_TO_COUNTRY[uiLang]) {
    return { country: LANG_TO_COUNTRY[uiLang], level: 'ui_lang' };
  }

  return { country: null, level: 'none' };
}
