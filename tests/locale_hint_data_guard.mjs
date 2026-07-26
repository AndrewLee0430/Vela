// Guard / unit test: localeHint.ts country-keyed data + the no-data→Tier-2 rule + language-aware
// keyword detection (在地差異 b1).
//
// WHAT BREAKS IF THIS FAILS: (1) a resolved country with no Tier-1 data yet (JP/KR/TH in b1) must
// fall to Tier-2, NOT render a broken/empty panel (Rule 2); (2) the existing TW authority data must
// stay byte-identical (b1 is a restructure, and the fly-210 TW gate is now a regression suite);
// (3) detection must be language-aware — the answer language picks WHICH keyword list.
//
// No test runner → transpile utils/localeHint.ts standalone (its only import is `import type` from
// ./country, erased at transpile). Run: node tests/locale_hint_data_guard.mjs
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const src = readFileSync(new URL('../utils/localeHint.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(src, { compilerOptions: { module: 'ESNext', target: 'ES2020' } }).outputText;
const mod = await import('data:text/javascript,' + encodeURIComponent(js));
const { getTier1Authorities, TIER2_AUTHORITIES, detectLocaleCategories, getAuthoritiesForCategories } = mod;

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

// 6. getAuthoritiesForCategories filters by covers∩cats (order preserved).
const dosingOnly = getAuthoritiesForCategories(sg.authorities, ['dosing']);
eq(dosingOnly.map(a => a.short_name), ['HSA'], 'SG dosing → HSA only (not MOH)');
const reimb = getAuthoritiesForCategories(sg.authorities, ['reimbursement']);
eq(reimb.map(a => a.short_name), ['MOH'], 'SG reimbursement → MOH only');

if (failures.length) {
  console.error(`localeHint data GUARD FAILED (${failures.length}):\n - ` + failures.join('\n - '));
  process.exit(1);
}
console.log('PASS  localeHint data — Tier-1 lookup + no-data→Tier-2, TW byte-identical, SG/MY verified, language-aware detection, category filter');
