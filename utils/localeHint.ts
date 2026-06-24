// utils/localeHint.ts — 在地差異提示 (local-difference / authorities-pointer) Tier-1 Taiwan PoC.
//
// Probe 1: FRONTEND-ONLY, deterministic keyword trigger (NO backend, NO LLM, NO SSE).
// The panel NAMES which dimensions may differ locally and POINTS to official authorities —
// it asserts NO clinical fact and states NO specific local value. Vela has NOT integrated
// TFDA/NHI data; the panel copy is explicit that it's for the user's own verification.
//
// Schema-shaped so it ports cleanly to a YAML data file in a later probe.

export type LocaleCategory = 'dosing' | 'reimbursement' | 'indication' | 'contraindication';

export interface Authority {
  short_name: string;
  name_native: string;
  name_en: string;
  url_native: string;
  covers: LocaleCategory[];
}

export interface LocaleAuthorities {
  locale: string;
  language: string;
  name_native: string;
  name_en: string;
  last_reviewed: string;
  authorities: Authority[];
}

// Tier-1 Taiwan. URLs are the exact, already-verified homepages — do NOT add deep-link /
// search-pattern URLs (they drift); homepage only for the PoC.
export const TW_AUTHORITIES: LocaleAuthorities = {
  locale: 'TW',
  language: 'zh-TW',
  name_native: '台灣',
  name_en: 'Taiwan',
  last_reviewed: '2026-06-23',
  authorities: [
    {
      short_name: 'TFDA',
      name_native: '衛生福利部食品藥物管理署',
      name_en: 'Taiwan Food and Drug Administration',
      url_native: 'https://www.fda.gov.tw/',
      covers: ['dosing', 'indication', 'contraindication'],
    },
    {
      short_name: 'NHI',
      name_native: '衛生福利部中央健康保險署',
      name_en: 'National Health Insurance Administration',
      url_native: 'https://www.nhi.gov.tw/',
      covers: ['reimbursement'],
    },
  ],
};

// Keyword map — TUNED BY DOGFOOD (see docs/locale_hint_dogfood_queries.md). Keep each category's
// list editable here in one place. PRECISION over coverage.
// NOTE: '交互作用' (interaction) and '不良反應/副作用' (adverse-effects/side-effects) are
// DELIBERATELY excluded — they appear in many general answers and would over-fire.
// 2026-06-24 NARROWING (dogfood: v0 over-fired — any sufficiently complete drug answer contains a
// number or a boilerplate 禁忌 section, so the panel read as wallpaper). Dosing/contraindication
// were narrowed to DECISION/STRONG-signal terms only:
//  - dosing: dropped the over-broad 劑量/用量/dose/dosage/mg/劑型 (mere mention of a number) — kept
//    only decision-oriented terms (起始/最大/調整 劑量, titrat, regimen).
//  - contraindication: dropped the over-broad 禁忌/禁忌症/注意事項/警語/contraindicat/warning
//    (boilerplate "禁忌與警示" sections) — kept only strong, locally-relevant ones (黑框警告 / boxed warning).
const KEYWORDS: Record<LocaleCategory, string[]> = {
  dosing: ['起始劑量', '最大劑量', '調整劑量', '劑量調整', '每日劑量', 'titrat', 'regimen'],
  reimbursement: ['給付', '健保', '自費', '給付條件', '給付規定', '部分負擔', '事前審查', 'health insurance', 'reimburse', 'coverage', 'formulary', 'copay'],
  indication: ['適應症', '核准適應症', '仿單', '許可證', '核准用途', '標示外', 'indication', 'approved use', 'label', 'off-label', 'licensed'],
  contraindication: ['黑框', '黑框警告', 'black box', 'boxed warning'],
};

const CATEGORY_ORDER: LocaleCategory[] = ['dosing', 'reimbursement', 'indication', 'contraindication'];

/**
 * Deterministic trigger. Caller passes user-query + final-answer concatenated.
 * ASCII keywords match case-insensitively; CJK keywords match as-is (no case folding needed).
 * Returns the de-duplicated matched categories (CATEGORY_ORDER order), empty if none.
 */
export function detectLocaleCategories(text: string): LocaleCategory[] {
  if (!text) return [];
  const lower = text.toLowerCase();
  const matched: LocaleCategory[] = [];
  for (const cat of CATEGORY_ORDER) {
    if (KEYWORDS[cat].some(kw => lower.includes(kw.toLowerCase()))) {
      matched.push(cat);
    }
  }
  return matched;
}

/**
 * TW authorities whose `covers` intersects the matched categories (TFDA-before-NHI order
 * preserved). A pure-dosing question shows TFDA only; a reimbursement question shows NHI.
 */
export function getAuthoritiesForCategories(cats: LocaleCategory[]): Authority[] {
  if (!cats.length) return [];
  return TW_AUTHORITIES.authorities.filter(a => a.covers.some(c => cats.includes(c)));
}
