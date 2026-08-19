// Guard / unit test: localeHint.ts country-keyed data + the no-data→Tier-2 rule + language-aware
// keyword detection (在地差異 b1).
//
// WHAT BREAKS IF THIS FAILS: (1) a resolved country with no Tier-1 data yet (JP/KR/TH in b1) must
// fall to Tier-2, NOT render a broken/empty panel (Rule 2); (2) the existing TW authority data must
// stay byte-identical (b1 is a restructure, and the fly-210 TW gate is now a regression suite);
// (3) detection must be language-aware — the answer language picks WHICH keyword list.
//
// No test runner → transpile utils/localeHint.ts standalone (its only imports are `import type`
// from ./country and ./sourceLabels, erased at transpile). Run: node tests/locale_hint_data_guard.mjs
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const src = readFileSync(new URL('../utils/localeHint.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(src, { compilerOptions: { module: 'ESNext', target: 'ES2020' } }).outputText;
const mod = await import('data:text/javascript,' + encodeURIComponent(js));
const { getTier1Authorities, TIER2_AUTHORITIES, detectLocaleCategories, getAuthoritiesForCategories, getCategoryLabelOverride, INTEGRATED_AUTHORITY_KEYS, filterUngroundedAuthorities } = mod;

const CATS = ['dosing', 'reimbursement', 'indication', 'contraindication'];
const COUNTRIES = ['TW', 'SG', 'MY', 'JP', 'KR', 'TH'];
// TW-specific terms that must never reach a non-TW user. 'NHI' = Taiwan's single-payer insurer.
const TW_TERMS = ['NHI', '健保'];

const failures = [];
function check(cond, msg) { if (!cond) failures.push(msg); }
function eq(a, e, msg) { if (JSON.stringify(a) !== JSON.stringify(e)) failures.push(`${msg}: expected ${JSON.stringify(e)} got ${JSON.stringify(a)}`); }

// 1. Tier-1 lookup: TW/SG/MY have data; JP/KR/TH + null → null (→ Tier-2, Rule 2).
for (const c of ['TW', 'SG', 'MY']) check(getTier1Authorities(c) != null, `getTier1Authorities(${c}) should have data`);
for (const c of ['JP', 'KR', 'TH']) check(getTier1Authorities(c) === null, `getTier1Authorities(${c}) must be null → Tier-2`);
check(getTier1Authorities(null) === null, 'getTier1Authorities(null) === null');

// 2. TW authority data BYTE-IDENTICAL to fly-210 (TFDA + NHI; names/urls/covers unchanged).
const tw = getTier1Authorities('TW');
const tfda = tw.authorities.find(a => a.short_name === 'TFDA');
const nhi = tw.authorities.find(a => a.short_name === 'NHI');
eq(tfda?.name_native, '衛生福利部食品藥物管理署', 'TFDA name_native');
eq(tfda?.name_en, 'Taiwan Food and Drug Administration', 'TFDA name_en');
eq(tfda?.url_native, 'https://www.fda.gov.tw/', 'TFDA url');
eq([...tfda.covers].sort(), ['contraindication', 'dosing', 'indication'], 'TFDA covers');
eq(nhi?.name_native, '衛生福利部中央健康保險署', 'NHI name_native');
eq(nhi?.url_native, 'https://www.nhi.gov.tw/', 'NHI url');
eq(nhi?.covers, ['reimbursement'], 'NHI covers');
eq(tw.panel_name, { en: 'Taiwan', 'zh-TW': '台灣' }, 'TW panel_name');

// 3. SG + MY data present with the verified authorities/urls.
const sg = getTier1Authorities('SG');
check(sg.authorities.some(a => a.short_name === 'HSA' && a.url_native === 'https://www.hsa.gov.sg/'), 'SG HSA url');
check(sg.authorities.some(a => a.short_name === 'MOH' && a.url_native === 'https://www.moh.gov.sg/'), 'SG MOH url');
check(sg.authorities.find(a => a.short_name === 'HSA').covers.includes('dosing'), 'SG HSA covers dosing');
check(sg.authorities.find(a => a.short_name === 'MOH').covers.includes('reimbursement'), 'SG MOH covers reimbursement');
const my = getTier1Authorities('MY');
check(my.authorities.some(a => a.short_name === 'NPRA' && a.url_native === 'https://www.npra.gov.my/'), 'MY NPRA url');
eq(my.authorities.find(a => a.short_name === 'NPRA')?.name_native, 'Bahagian Regulatori Farmasi Negara', 'MY NPRA Malay name (confirmed)');
check(my.authorities.some(a => a.short_name === 'MOH' && a.url_native === 'https://www.moh.gov.my/'), 'MY MOH url');

// 4. Tier-2 = WHO / NICE / EMA / Cochrane.
eq([...TIER2_AUTHORITIES.map(a => a.short_name)].sort(), ['Cochrane', 'EMA', 'NICE', 'WHO'], 'TIER2 set');
check(TIER2_AUTHORITIES.every(a => /^https:\/\//.test(a.url_native)), 'TIER2 urls are https');

// 5. Language-aware detection: answer language picks the keyword list.
eq(detectLocaleCategories('起始劑量 5mg', 'zh-TW'), ['dosing'], 'zh-TW dosing keyword');
eq(detectLocaleCategories('a boxed warning applies', 'en'), ['contraindication'], 'en boxed-warning keyword');
eq(detectLocaleCategories('plain english answer, no trigger', 'en'), [], 'en no-trigger → []');
eq(detectLocaleCategories('起始劑量', 'ja'), [], 'unsupported answer language → [] (panel does not fire)');
// precision: a bare generic word must NOT trigger (v188 bar) — "dose" alone is not a decision term.
eq(detectLocaleCategories('the usual dose is 5 mg', 'en'), [], 'en bare "dose"/"mg" must NOT over-fire');
// 2026-07-26 EN calibration lock (founder pre-ship narrowing). WHAT BREAKS IF THIS FAILS: the EN list
// re-widens and the panel becomes wallpaper on ordinary drug answers — unrecoverable trust cost.
// (a) DailyMed label documents' own names must NOT fire — DailyMed is the 5th Research source and
//     fly 209/211 raised how often label sections reach the cited pool.
eq(detectLocaleCategories('see the prescribing information and package insert', 'en'), [], 'en label-document names must NOT fire');
// (b) bare titrate/titration are generic clinical prose verbs, not local-difference decision terms...
eq(detectLocaleCategories('titrate slowly; titration is guided by response', 'en'), [], 'en bare "titrate"/"titration" must NOT fire');
// (c) ...but the compound decision term is retained.
eq(detectLocaleCategories('dose titration is required in renal impairment', 'en'), ['dosing'], 'en "dose titration" still fires');

// 6. getAuthoritiesForCategories filters by covers∩cats (order preserved).
const dosingOnly = getAuthoritiesForCategories(sg.authorities, ['dosing']);
eq(dosingOnly.map(a => a.short_name), ['HSA'], 'SG dosing → HSA only (not MOH)');
const reimb = getAuthoritiesForCategories(sg.authorities, ['reimbursement']);
eq(reimb.map(a => a.short_name), ['MOH'], 'SG reimbursement → MOH only');

// 7. ANTI-LEAK (b1-fix): no TW-specific category label may reach a non-TW country or Tier-2.
//    WHAT BREAKS IF THIS FAILS: a Malaysian pharmacist sees the chip "NHI reimbursement" — Taiwan's
//    national insurer — on a Malaysia panel. Found at the b1 prod gate; the TW term was baked into
//    the shared i18n string. This assertion is what stops the same class of leak when b2 adds
//    JP/KR/TH, since those countries get their labels purely by NOT having an override.
for (const c of COUNTRIES.filter(c => c !== 'TW')) {
  const data = getTier1Authorities(c);
  if (!data) continue;                       // no Tier-1 data yet (JP/KR/TH) → Tier-2 path, checked below
  for (const cat of CATS) {
    for (const lang of ['en', 'zh-TW']) {
      const label = getCategoryLabelOverride(data, cat, lang);
      check(label === null || !TW_TERMS.some(t => label.includes(t)),
        `${c}.${cat}[${lang}] must not carry a TW-specific label (got ${JSON.stringify(label)})`);
    }
  }
}
// Tier-2 has no country data at all → getCategoryLabelOverride(null,…) must ALWAYS be null, so
// Tier-2 can only ever render the country-neutral i18n default.
for (const cat of CATS) {
  for (const lang of ['en', 'zh-TW']) {
    eq(getCategoryLabelOverride(null, cat, lang), null, `TIER2 ${cat}[${lang}] must have no override`);
  }
}
// TW itself KEEPS its domestic term — the override must survive, not be flattened away.
eq(getCategoryLabelOverride(getTier1Authorities('TW'), 'reimbursement', 'en'), 'NHI reimbursement', 'TW keeps NHI label (en)');
eq(getCategoryLabelOverride(getTier1Authorities('TW'), 'reimbursement', 'zh-TW'), '健保給付', 'TW keeps 健保給付 label (zh-TW)');
// TW must NOT override the other three — they are already country-neutral and correct everywhere.
for (const cat of ['dosing', 'indication', 'contraindication']) {
  eq(getCategoryLabelOverride(getTier1Authorities('TW'), cat, 'en'), null, `TW ${cat} needs no override`);
}

// 8. The i18n DEFAULTS themselves must be country-neutral — this is where the leak actually lived
//    (the shared `localeHintCatReimbursement` string read "NHI reimbursement" for every country).
//    Source-scan utils/i18n-ui.ts across ALL 16 locales, not just the two the panel renders.
const uiSrc = readFileSync(new URL('../utils/i18n-ui.ts', import.meta.url), 'utf8');
const catLines = uiSrc.split('\n').filter(l => /localeHintCat\w+\s*:/.test(l));
check(catLines.length >= 64, `expected >=64 localeHintCat* lines (16 locales x 4), got ${catLines.length}`);
for (const line of catLines) {
  const bad = TW_TERMS.find(t => line.includes(t));
  check(!bad, `i18n localeHintCat* default must be country-neutral, found "${bad}" in: ${line.trim()}`);
}

// 9. ADR-007 (d) authority-row suppression (option ii). WHAT BREAKS IF THIS FAILS: the panel tells
//    a Taiwanese user "Vela has not integrated data from these authorities" on a screen whose ONLY
//    source IS the integrated TFDA corpus (fly-214 gate Finding 3) — OR, inverted, the protective
//    pointer disappears from un-grounded answers where it is the only safeguard.
check(typeof filterUngroundedAuthorities === 'function', 'filterUngroundedAuthorities must exist and be exported');
check(INTEGRATED_AUTHORITY_KEYS instanceof Set, 'INTEGRATED_AUTHORITY_KEYS must exist and be a Set');
check(INTEGRATED_AUTHORITY_KEYS.has('tfda'), "INTEGRATED_AUTHORITY_KEYS must contain 'tfda' (the v193 corpus)");
const tfda2 = getTier1Authorities('TW').authorities.find(a => a.short_name === 'TFDA');
eq(tfda2?.integrated_source, 'tfda', "TW_TFDA.integrated_source must map to citation source_type 'tfda'");

// (i) REMOVES the integrated authority when its source_type grounded the answer (NHI untouched —
//     part of (iii): authorities outside the set pass through even when the filter fires).
const twAuths = getTier1Authorities('TW').authorities;
const grounded = filterUngroundedAuthorities(twAuths, new Set(['tfda', 'pubmed']));
check(!grounded.some(a => a.short_name === 'TFDA'), 'grounded answer: TFDA pointer row must be REMOVED');
check(grounded.some(a => a.short_name === 'NHI'), 'grounded answer: NHI (outside the set) must SURVIVE');

// (ii) KEEPS it when the answer is NOT grounded in that source — the protective pointer survives.
const ungrounded = filterUngroundedAuthorities(twAuths, new Set(['pubmed', 'dailymed']));
check(ungrounded.some(a => a.short_name === 'TFDA'), 'un-grounded answer: TFDA pointer row must be KEPT');
eq(ungrounded.length, twAuths.length, 'un-grounded answer: nothing may be dropped');
eq(filterUngroundedAuthorities(twAuths, new Set()).length, twAuths.length, 'empty citation set: nothing may be dropped');

// (iii) NEVER touches authorities outside the set — SG/MY/Tier-2 pass through byte-identically
//       even when 'tfda' (and everything else) is present in the citations.
const everything = new Set(['tfda', 'pubmed', 'dailymed', 'fda', 'who', 'nice', 'ema', 'cochrane']);
for (const [label, set] of [
  ['SG', getTier1Authorities('SG').authorities],
  ['MY', getTier1Authorities('MY').authorities],
  ['TIER2', TIER2_AUTHORITIES],
]) {
  eq(filterUngroundedAuthorities(set, everything), set, `${label} authorities must pass through the filter untouched`);
}

// (v) positive control: the filter genuinely fires on the general mechanism, not on a TFDA
//     special-case — a synthetic authority carrying an integrated key is removed too...
const synthetic = { short_name: 'SYN', name_native: 'x', name_en: 'x', url_native: 'https://x/', covers: ['dosing'], integrated_source: 'tfda' };
eq(filterUngroundedAuthorities([synthetic], new Set(['tfda'])).length, 0, 'positive control: synthetic integrated authority removed');
// ...while a mapped-but-NOT-integrated key (not in the set) survives even when cited — the set is
// load-bearing (mutation M3: emptying it must flip the removes-when-present checks above only).
const mappedNotIntegrated = { ...synthetic, integrated_source: 'dailymed' };
eq(filterUngroundedAuthorities([mappedNotIntegrated], new Set(['dailymed'])).length, 1, 'a key outside INTEGRATED_AUTHORITY_KEYS must never suppress');

if (failures.length) {
  console.error(`localeHint data GUARD FAILED (${failures.length}):\n - ` + failures.join('\n - '));
  process.exit(1);
}
console.log('PASS  localeHint data — Tier-1 lookup + no-data→Tier-2, TW byte-identical, SG/MY verified, language-aware detection, category filter, ADR-007 (d) suppression');
