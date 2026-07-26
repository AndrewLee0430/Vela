// Guard / unit test: resolveCountry() — the 在地差異 (b1) locale-detection waterfall.
//
// WHAT BREAKS IF THIS FAILS: the panel points a user at the WRONG country's authorities, or
// silently disables SG/MY (whose only implicit path is timezone L3). The waterfall precedence
// L1 Settings > L2 work_language > L3 timezone > L4 ui_lang is safety-relevant: reordering L3
// below L4 makes SG + MY unreachable (both English-speaking → no L2/L4 signal).
//
// No test runner in this repo → transpile utils/country.ts in-memory with the installed
// `typescript` package (it has zero runtime imports — signals are plain strings — so the output
// is self-contained) and exercise the real export. Run: node tests/resolve_country_guard.mjs
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const src = readFileSync(new URL('../utils/country.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(src, {
  compilerOptions: { module: 'ESNext', target: 'ES2020' },
}).outputText;
const mod = await import('data:text/javascript,' + encodeURIComponent(js));
const { resolveCountry, COUNTRY_CODES } = mod;

const failures = [];
function eq(actual, expected, msg) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a !== e) failures.push(`${msg}\n      expected ${e}\n      got      ${a}`);
}

// helper: build the full signal object with everything null unless overridden
const R = (o = {}) => resolveCountry({ settingsLocale: null, workLanguage: null, timeZone: null, uiLang: null, ...o });

// 0. Value set = the 6 Tier-1 countries (OTHER is a settings sentinel, NOT a resolvable country).
eq([...COUNTRY_CODES].sort(), ['JP', 'KR', 'MY', 'SG', 'TH', 'TW'], 'COUNTRY_CODES value set');

// 1. L1 Settings locale — a chosen country wins outright.
for (const c of ['TW', 'JP', 'KR', 'SG', 'MY', 'TH']) {
  eq(R({ settingsLocale: c }), { country: c, level: 'settings' }, `L1 settings=${c}`);
}
// 1b. L1 'OTHER' is TERMINAL → no country (Tier 2), and does NOT fall through to timezone.
eq(R({ settingsLocale: 'OTHER', timeZone: 'Asia/Taipei', workLanguage: 'zh-TW' }),
   { country: null, level: 'settings' }, 'L1 OTHER is terminal (no fall-through to TW)');
// 1c. L1 beats L3 (row 10 behavioral).
eq(R({ settingsLocale: 'SG', timeZone: 'Asia/Taipei' }),
   { country: 'SG', level: 'settings' }, 'L1 SG overrides L3 Asia/Taipei');

// 2. L2 work_language — ONLY these four map; everything else falls through.
eq(R({ workLanguage: 'zh-TW' }), { country: 'TW', level: 'work_language' }, 'L2 zh-TW');
eq(R({ workLanguage: 'ja' }),    { country: 'JP', level: 'work_language' }, 'L2 ja');
eq(R({ workLanguage: 'ko' }),    { country: 'KR', level: 'work_language' }, 'L2 ko');
eq(R({ workLanguage: 'th' }),    { country: 'TH', level: 'work_language' }, 'L2 th');
for (const l of ['en', 'ms', 'pt', 'es', 'ar', 'zh-CN']) {
  eq(R({ workLanguage: l }), { country: null, level: 'none' }, `L2 ${l} must NOT guess a country`);
}

// 3. L3 timezone — the six Asia zones; anything else falls through.
eq(R({ timeZone: 'Asia/Taipei' }),        { country: 'TW', level: 'timezone' }, 'L3 Asia/Taipei');
eq(R({ timeZone: 'Asia/Tokyo' }),         { country: 'JP', level: 'timezone' }, 'L3 Asia/Tokyo');
eq(R({ timeZone: 'Asia/Seoul' }),         { country: 'KR', level: 'timezone' }, 'L3 Asia/Seoul');
eq(R({ timeZone: 'Asia/Singapore' }),     { country: 'SG', level: 'timezone' }, 'L3 Asia/Singapore');
eq(R({ timeZone: 'Asia/Kuala_Lumpur' }),  { country: 'MY', level: 'timezone' }, 'L3 Asia/Kuala_Lumpur');
eq(R({ timeZone: 'Asia/Bangkok' }),       { country: 'TH', level: 'timezone' }, 'L3 Asia/Bangkok');
eq(R({ timeZone: 'America/New_York' }),   { country: null, level: 'none' }, 'L3 unknown TZ falls through');

// 4. L4 ui_lang — same four as L2, only when nothing above resolved.
eq(R({ uiLang: 'ja' }), { country: 'JP', level: 'ui_lang' }, 'L4 uiLang ja');
eq(R({ uiLang: 'en' }), { country: null, level: 'none' }, 'L4 uiLang en falls through');

// 5. PRECEDENCE — L2 beats L3 beats L4; and CRUCIALLY L3 must stay ABOVE L4.
eq(R({ workLanguage: 'ja', timeZone: 'Asia/Singapore' }),
   { country: 'JP', level: 'work_language' }, 'L2 beats L3');
// SG/MY reachability guard: en work_language falls through, timezone SG must win over ui_lang.
eq(R({ workLanguage: 'en', timeZone: 'Asia/Singapore', uiLang: 'ja' }),
   { country: 'SG', level: 'timezone' }, 'L3 must NOT be reordered below L4 (SG reachability)');
eq(R({ workLanguage: 'en', timeZone: 'Asia/Kuala_Lumpur', uiLang: 'ja' }),
   { country: 'MY', level: 'timezone' }, 'L3 MY reachability over L4');

// 6. Nothing resolves → null / none (→ the panel's Tier-2 path).
eq(R(), { country: null, level: 'none' }, 'no signals → none');
eq(R({ workLanguage: 'en', timeZone: 'America/New_York', uiLang: 'en' }),
   { country: null, level: 'none' }, 'all-unmapped → none');

if (failures.length) {
  console.error(`resolveCountry GUARD FAILED (${failures.length}):\n - ` + failures.join('\n - '));
  process.exit(1);
}
console.log('PASS  resolveCountry — L1>L2>L3>L4 precedence, SG/MY timezone reachability, OTHER terminal, unmapped fall-through');
