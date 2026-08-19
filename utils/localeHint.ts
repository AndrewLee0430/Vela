// utils/localeHint.ts — 在地差異提示 (local-difference / authorities-pointer). Tier-1 country-keyed
// (TW / SG / MY) + Tier-2 international fallback (WHO / NICE / EMA / Cochrane).
//
// FRONTEND-ONLY, deterministic keyword trigger (NO backend, NO LLM, NO SSE). The panel NAMES which
// dimensions may differ locally and POINTS to official authorities — it asserts NO clinical fact and
// states NO specific local value. Vela has NOT integrated authority data; the copy is explicit that
// it's for the user's own verification.
//
// COUNTRY ≠ LANGUAGE (probe found `locale` overloaded). Country (from utils/country.ts resolveCountry)
// selects WHICH authorities; the answer/UI language selects WHICH keyword list + the panel text.

import type { CountryCode } from './country';
import type { CitationSourceType } from './sourceLabels';

export type LocaleCategory = 'dosing' | 'reimbursement' | 'indication' | 'contraindication';

export interface Authority {
  short_name: string;
  name_native: string;
  name_en: string;
  url_native: string;
  covers: LocaleCategory[];
  // ADR-007 (d): the citation `source_type` this authority's documents carry once Vela has
  // ingested its corpus (TFDA → 'tfda'). DATA, not a user-visible string — the match key is the
  // source_type enum value, matched EXACTLY against the answer's citations (Rule 23: never derive
  // the key by name/substring). Absent → this authority has no integrated corpus and the
  // grounded-answer suppression below can never touch it.
  integrated_source?: CitationSourceType;
}

export interface LocaleAuthorities {
  country: CountryCode;
  // Country name AS SHOWN in the panel heading, per panel language. Kept as data (only the two
  // panel languages) rather than i18n keys — the panel renders ONLY in en / zh-TW in b1, so this
  // avoids adding country-name keys to the 14 placeholder i18n locales (no new visible i18n debt).
  panel_name: { en: string; 'zh-TW': string };
  last_reviewed: string;
  authorities: Authority[];
  // OPTIONAL per-country category-label override (b1-fix). The i18n `localeHintCat*` keys are the
  // COUNTRY-NEUTRAL default used by every country and by Tier-2; a country sets an entry here ONLY
  // when its own domestic term is genuinely better for its users. Absent → neutral default, so a
  // new country needs ZERO extra data. This is a generic data-driven lookup, NOT render-logic
  // special-casing — see getCategoryLabelOverride + LocaleHintPanel.
  cat_labels?: Partial<Record<LocaleCategory, { en: string; 'zh-TW': string }>>;
}

// ── Taiwan (Tier-1) — authorities BYTE-IDENTICAL to fly-210 (restructure, not re-authoring). ──
const TW_TFDA: Authority = {
  short_name: 'TFDA',
  name_native: '衛生福利部食品藥物管理署',
  name_en: 'Taiwan Food and Drug Administration',
  url_native: 'https://www.fda.gov.tw/',
  covers: ['dosing', 'indication', 'contraindication'],
  // ADR-007 (d): v193 shipped the 10,941-doc TFDA indication corpus; its citations carry
  // source_type 'tfda' (utils/sourceLabels.ts detectSourceType). Display fields above are
  // BYTE-IDENTICAL to fly-210 — this key is additive data, not a re-authoring.
  integrated_source: 'tfda',
};
const TW_NHI: Authority = {
  short_name: 'NHI',
  name_native: '衛生福利部中央健康保險署',
  name_en: 'National Health Insurance Administration',
  url_native: 'https://www.nhi.gov.tw/',
  covers: ['reimbursement'],
};

// ── Singapore (Tier-1) — HSA + MOH. English is Singapore's official language (name_native = name_en).
//    URLs HTTP-200 verified 2026-07-24 (hsa.gov.sg, moh.gov.sg). ──
const SG_HSA: Authority = {
  short_name: 'HSA',
  name_native: 'Health Sciences Authority',
  name_en: 'Health Sciences Authority',
  url_native: 'https://www.hsa.gov.sg/',
  covers: ['dosing', 'indication', 'contraindication'],
};
const SG_MOH: Authority = {
  short_name: 'MOH',
  name_native: 'Ministry of Health',
  name_en: 'Ministry of Health',
  url_native: 'https://www.moh.gov.sg/',
  covers: ['reimbursement'],
};

// ── Malaysia (Tier-1) — NPRA + MOH. name_native is the confirmed official Malay name.
//    npra.gov.my HTTP-200 verified 2026-07-24. ──
const MY_NPRA: Authority = {
  short_name: 'NPRA',
  name_native: 'Bahagian Regulatori Farmasi Negara',
  name_en: 'National Pharmaceutical Regulatory Agency',
  url_native: 'https://www.npra.gov.my/',
  covers: ['dosing', 'indication', 'contraindication'],
};
// moh.gov.my — TOOL-UNCONFIRMED (403 to automated checks: both curl w/ browser UA and WebFetch)
// / BROWSER-CONFIRMED at the b1 prod gate (row 2), 2026-07-26. The 403 is a WAF bot-block, not a
// dead site: this is the official Malaysia MOH domain and the structural sibling of the
// HTTP-200-confirmed moh.gov.sg. ⚠️ The PRD §5.1.1 monthly url_native HEAD-check cron will 403 on
// this entry FOREVER — it needs an allowlist exception when that cron is built, or this one
// permanently-crying URL erodes the whole link-health layer. See TECH_DEBT [P2 · link-health cron].
const MY_MOH: Authority = {
  short_name: 'MOH',
  name_native: 'Kementerian Kesihatan Malaysia',
  name_en: 'Ministry of Health Malaysia',
  url_native: 'https://www.moh.gov.my/',
  covers: ['reimbursement'],
};

// Tier-1 country → authorities. ONLY TW/SG/MY have data in b1; JP/KR/TH resolve (via the waterfall)
// but have no entry here → getTier1Authorities returns null → the panel renders Tier-2 (Rule 2).
// TW-only category-label override (b1-fix). Taiwan's single-payer scheme IS "健保 / NHI", so the
// domestic term is more precise than the neutral default FOR TAIWANESE USERS. It was previously
// hardcoded into the i18n `localeHintCatReimbursement` string itself, which meant a Malaysian user
// on an MY panel saw the chip "NHI reimbursement" — Taiwan's insurer, named to a Malaysian
// pharmacist (found at the b1 prod gate). The neutral default now lives in i18n; TW opts back in
// here. Any country may add its own override; none is required.
const TW_CAT_LABELS: LocaleAuthorities['cat_labels'] = {
  reimbursement: { en: 'NHI reimbursement', 'zh-TW': '健保給付' },
};

const LOCALE_DATA: Partial<Record<CountryCode, LocaleAuthorities>> = {
  TW: { country: 'TW', panel_name: { en: 'Taiwan', 'zh-TW': '台灣' }, last_reviewed: '2026-06-23', authorities: [TW_TFDA, TW_NHI], cat_labels: TW_CAT_LABELS },
  SG: { country: 'SG', panel_name: { en: 'Singapore', 'zh-TW': '新加坡' }, last_reviewed: '2026-07-24', authorities: [SG_HSA, SG_MOH] },
  MY: { country: 'MY', panel_name: { en: 'Malaysia', 'zh-TW': '馬來西亞' }, last_reviewed: '2026-07-24', authorities: [MY_NPRA, MY_MOH] },
};

/** Tier-1 authorities for a resolved country, or null when the country has no data yet (→ Tier-2). */
export function getTier1Authorities(country: CountryCode | null): LocaleAuthorities | null {
  return (country && LOCALE_DATA[country]) || null;
}

/**
 * The country's own label for a category, or null when it has none (→ caller uses the neutral i18n
 * default). Tier-2 passes null and therefore ALWAYS gets the neutral default. Pure + exported so
 * the data guard can assert no non-TW entry ever carries a TW-specific term.
 */
export function getCategoryLabelOverride(
  data: LocaleAuthorities | null,
  cat: LocaleCategory,
  lang: 'en' | 'zh-TW',
): string | null {
  return data?.cat_labels?.[cat]?.[lang] ?? null;
}

// ── Tier-2 international fallback — shown when no Tier-1 country resolves, or a resolved country has
//    no Tier-1 data. URLs HTTP-200 verified 2026-07-24. ──
export const TIER2_AUTHORITIES: Authority[] = [
  { short_name: 'WHO', name_native: 'World Health Organization', name_en: 'World Health Organization', url_native: 'https://www.who.int/', covers: ['dosing', 'indication', 'contraindication'] },
  { short_name: 'NICE', name_native: 'National Institute for Health and Care Excellence', name_en: 'National Institute for Health and Care Excellence', url_native: 'https://www.nice.org.uk/', covers: ['reimbursement', 'indication', 'contraindication'] },
  { short_name: 'EMA', name_native: 'European Medicines Agency', name_en: 'European Medicines Agency', url_native: 'https://www.ema.europa.eu/', covers: ['dosing', 'indication', 'contraindication'] },
  { short_name: 'Cochrane', name_native: 'Cochrane', name_en: 'Cochrane', url_native: 'https://www.cochrane.org/', covers: ['dosing', 'indication', 'contraindication'] },
];

// ── Keyword maps — the ANSWER LANGUAGE selects which list (RULE 1). ──
// zh-TW list: BYTE-IDENTICAL to fly-210 (TUNED BY DOGFOOD, docs/locale_hint_dogfood_queries.md).
// PRECISION over coverage. '交互作用'/'不良反應/副作用' DELIBERATELY excluded (over-fire).
// 2026-06-24 NARROWING: dosing dropped 劑量/用量/dose/dosage/mg/劑型 (mere number); contraindication
// dropped 禁忌/禁忌症/注意事項/警語/contraindicat/warning (boilerplate) — kept decision/strong terms only.
const KEYWORDS_ZH_TW: Record<LocaleCategory, string[]> = {
  dosing: ['起始劑量', '最大劑量', '調整劑量', '劑量調整', '每日劑量', 'titrat', 'regimen'],
  reimbursement: ['給付', '健保', '自費', '給付條件', '給付規定', '部分負擔', '事前審查', 'health insurance', 'reimburse', 'coverage', 'formulary', 'copay'],
  indication: ['適應症', '核准適應症', '仿單', '許可證', '核准用途', '標示外', 'indication', 'approved use', 'label', 'off-label', 'licensed'],
  contraindication: ['黑框', '黑框警告', 'black box', 'boxed warning'],
};

// EN list (b1, NEW): mirrors the zh-TW list at the SAME v188 precision bar — DECISION / STRONG-signal
// terms only, never generic boilerplate. Deliberately NOT included (would over-fire on ordinary
// English answers): bare 'dose'/'dosage'/'mg', bare 'coverage'/'label'/'indication', generic
// 'contraindicated'/'warning'/'interaction'/'side effect'.
//
// CALIBRATED TIGHTER THAN zh-TW BY DESIGN (29 EN vs 34 zh-TW). zh-TW fires only on zh-TW answers,
// validated in one country; EN fires on English answers GLOBALLY and English is many users' default
// UI language — the same false-positive RATE is a far larger absolute volume, and a panel that
// becomes wallpaper cannot be un-rung. Widen later from PostHog data if it under-fires.
//
// 2026-07-26 pre-ship narrowing (founder review of the STEP-0 proposal):
//   - indication: DROPPED 'prescribing information' / 'package insert' — DailyMed has been the 5th
//     Research retrieval source since fly 206 and fly 209/211 both raised the rate at which official
//     label safety sections reach the cited pool; these two terms are those label documents' OWN
//     NAMES, so they would fire on a large share of drug answers with no local-difference angle.
//   - dosing: DROPPED bare 'titrate' / 'titration' — generic clinical prose verbs, the English
//     equivalent of the bare dosage terms v188 stripped from zh-TW. 'dose titration' KEPT.
//   - SUBSTRING de-dup (matching is `lower.includes(kw)`, NOT word-boundary): dropped
//     'renal dose adjustment' + 'hepatic dose adjustment' (covered by 'dose adjustment'),
//     'reimbursement' (covered by 'reimburse'), 'co-payment' (covered by 'co-pay'). Zero
//     behavior change — each dropped term's matches are a subset of a retained term's.
// Counts: dosing 6 · reimbursement 12 · indication 8 · contraindication 3 = 29.
//
// KNOWN MINOR RECALL GAP (parked for the PostHog tuning round, deliberately NOT fixed): substring
// matching means 'subsidy' does NOT cover 'subsidies' (different stem). The obvious stem 'subsidi'
// would false-match 'subsidiary', and adding bare 'subsidies' alone is over-fitting to one plural.
// Resolve it with data, not a guess.
//
// KNOWN b1 LIMITATION (documented, deliberately NOT fixed): `contraindication` contains only
// boxed-warning phrasings — one concept, and a US-FDA-specific construct. In b1 it effectively
// detects "the answer mentions a US boxed warning", not contraindications generally. Revisit once
// PostHog shows the real category distribution; adding terms now would be guessing without data.
const KEYWORDS_EN: Record<LocaleCategory, string[]> = {
  dosing: ['starting dose', 'initial dose', 'maximum dose', 'dose adjustment', 'dose titration', 'dosing regimen'],
  reimbursement: ['reimburse', 'formulary', 'insurance coverage', 'out-of-pocket', 'out of pocket', 'copay', 'co-pay', 'prior authorization', 'prior authorisation', 'subsidy', 'subsidized', 'subsidised'],
  indication: ['approved indication', 'licensed indication', 'off-label', 'off label', 'approved use', 'marketing authorization', 'marketing authorisation', 'label indication'],
  contraindication: ['black box warning', 'black-box warning', 'boxed warning'],
};

const CATEGORY_ORDER: LocaleCategory[] = ['dosing', 'reimbursement', 'indication', 'contraindication'];

/**
 * Deterministic, LANGUAGE-AWARE trigger. `lang` = the answer language and picks the keyword list;
 * only en / zh-TW answers fire in b1 (any other language → [], panel does not render). Caller passes
 * user-query + final-answer concatenated. ASCII keywords match case-insensitively; CJK as-is.
 * Returns the de-duplicated matched categories (CATEGORY_ORDER order), empty if none.
 */
export function detectLocaleCategories(text: string, lang: string): LocaleCategory[] {
  if (!text) return [];
  const keywords = lang === 'zh-TW' ? KEYWORDS_ZH_TW : lang === 'en' ? KEYWORDS_EN : null;
  if (!keywords) return [];
  const lower = text.toLowerCase();
  const matched: LocaleCategory[] = [];
  for (const cat of CATEGORY_ORDER) {
    if (keywords[cat].some(kw => lower.includes(kw.toLowerCase()))) {
      matched.push(cat);
    }
  }
  return matched;
}

/**
 * The authorities (from a Tier-1 country's set OR TIER2_AUTHORITIES) whose `covers` intersects the
 * matched categories, source order preserved. A pure-dosing question shows the regulator only; a
 * reimbursement question shows the insurance/ministry authority.
 */
export function getAuthoritiesForCategories(authorities: Authority[], cats: LocaleCategory[]): Authority[] {
  if (!cats.length) return [];
  return authorities.filter(a => a.covers.some(c => cats.includes(c)));
}

// ── ADR-007 (d) pointer→grounding graduation, option (ii): authority-row suppression. ──
//
// The registry of citation source_types Vela has ACTUALLY integrated into Research retrieval.
// PLURAL BY CONSTRUCTION (Rule 23): today it holds only 'tfda' (the v193 indication corpus).
// When a b2 ingest lands (JP/KR/TH — or any future authority corpus), EXTEND THIS SET (and set
// `integrated_source` on the authority) — never rewrite the mechanism.
export const INTEGRATED_AUTHORITY_KEYS: ReadonlySet<string> = new Set(['tfda']);

/**
 * ADR-007 (d): drop the pointer row for an authority whose integrated corpus GROUNDED this very
 * answer — on that screen `localeHintNote` ("Vela has not integrated data from these authorities")
 * is false for that row (the fly-214 gate Finding 3 contradiction). Keeps every authority that
 * (a) has no `integrated_source`, or (b) whose key is not in INTEGRATED_AUTHORITY_KEYS (mapped but
 * not yet ingested), or (c) whose source_type is absent from this answer's citations — so
 * un-grounded answers keep the protective pointer. Pure + exported so the data guard can assert
 * it (the getCategoryLabelOverride precedent).
 */
export function filterUngroundedAuthorities(
  authorities: Authority[],
  citationSourceTypes: ReadonlySet<string>,
): Authority[] {
  return authorities.filter(a =>
    !a.integrated_source
    || !INTEGRATED_AUTHORITY_KEYS.has(a.integrated_source)
    || !citationSourceTypes.has(a.integrated_source)
  );
}
