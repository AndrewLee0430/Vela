// Guard: the Research disclaimer line is ONE shared source rendered on BOTH
// /research and /history (HISTORY HONESTY car segment 4a, item (b)).
//
// WHAT BREAKS IF THIS FAILS (CLAUDE.md Rule 17/19): every Research answer
// redisplayed on /history used to carry NO "for informational purposes only ...
// consult a qualified professional" line, while /research showed it under the
// same answer (TECH_DEBT [HONESTY][P2], filed 2026-09-07). The fix moves the
// 16-language map out of pages/research.tsx into utils/researchDisclaimer.ts
// and renders it in the /history research branch on BOTH render paths (the
// section cards and the legacy pre-wrap paragraph). If the map is duplicated
// back into a page, the two surfaces drift (the 2026-05 share/explore
// disclaimer drift, 14 of 16 locales, is the precedent); if a render path
// loses the call, that path silently redisplays a medical answer uncaptioned.
//
// No test runner -> the shared module (zero imports) is transpiled and
// EXECUTED; the two pages are checked as source (comments stripped).
// Run: node tests/history_research_disclaimer_guard.mjs   (also run by
// tests/test_history_research_disclaimer.py inside the pytest count)
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const failures = [];
function check(cond, msg) { if (!cond) failures.push(msg); }
const stripComments = (src) => src.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/^\s*\/\/.*$/gm, ' ');
const OPTS = { compilerOptions: { module: 'ESNext', target: 'ES2020' } };

const LANGS = ['en', 'zh-TW', 'zh-CN', 'ja', 'ko', 'es', 'fr', 'de', 'it', 'pt', 'th', 'ar', 'hi', 'bn', 'he', 'vi'];
const EN_LITERAL = 'For informational purposes only';
const WARN_GLYPH = '⚠️ ';
const IMPORT_RE = /import\s*\{[^}]*\bgetResearchDisclaimer\b[^}]*\}\s*from\s*'\.\.\/utils\/researchDisclaimer'/;

// -- 1. The shared module exists, exports the 16-language map + accessor, and the accessor works
const modPath = fileURLToPath(new URL('../utils/researchDisclaimer.ts', import.meta.url));
check(existsSync(modPath), 'utils/researchDisclaimer.ts is missing - the shared disclaimer source does not exist');
if (existsSync(modPath)) {
  const src = readFileSync(modPath, 'utf8');
  const mod = await import('data:text/javascript,' + encodeURIComponent(ts.transpileModule(src, OPTS).outputText));
  const { RESEARCH_DISCLAIMERS, getResearchDisclaimer } = mod;
  check(typeof getResearchDisclaimer === 'function', 'getResearchDisclaimer is not exported');
  check(RESEARCH_DISCLAIMERS && typeof RESEARCH_DISCLAIMERS === 'object', 'RESEARCH_DISCLAIMERS map is not exported');
  if (RESEARCH_DISCLAIMERS) {
    const keys = Object.keys(RESEARCH_DISCLAIMERS).sort();
    check(JSON.stringify(keys) === JSON.stringify([...LANGS].sort()), `map keys are not exactly the 16 locales: ${keys.join(',')}`);
    for (const l of LANGS) {
      const v = RESEARCH_DISCLAIMERS[l];
      check(typeof v === 'string' && v.startsWith(WARN_GLYPH), `${l}: value must start with the warning glyph + space`);
      check(typeof v === 'string' && v.length > 20, `${l}: value suspiciously short`);
    }
    check((RESEARCH_DISCLAIMERS.en || '').includes(EN_LITERAL), 'en value lost the informational-use sentence');
  }
  if (typeof getResearchDisclaimer === 'function' && RESEARCH_DISCLAIMERS) {
    check(getResearchDisclaimer('zh-TW') === RESEARCH_DISCLAIMERS['zh-TW'], 'accessor does not return the locale string');
    check(getResearchDisclaimer('xx-unknown') === RESEARCH_DISCLAIMERS.en, 'accessor does not fall back to en for an unknown key');
    check(getResearchDisclaimer('') === RESEARCH_DISCLAIMERS.en, 'accessor does not fall back to en for an empty key');
  }
}

// -- 2. /research imports the shared source and keeps NO local copy
const researchSrc = stripComments(readFileSync(new URL('../pages/research.tsx', import.meta.url), 'utf8'));
check(IMPORT_RE.test(researchSrc), 'pages/research.tsx does not import getResearchDisclaimer from ../utils/researchDisclaimer');
check(!/const\s+DISCLAIMERS\s*[:=]/.test(researchSrc), 'pages/research.tsx still carries a page-local DISCLAIMERS map (duplicate source)');
check(!researchSrc.includes(EN_LITERAL), 'pages/research.tsx still carries the disclaimer literal (duplicate source)');
check((researchSrc.match(/getResearchDisclaimer\(detectedLang\)/g) || []).length === 3,
  '/research must render the disclaimer at its 3 pre-existing sites, keyed by detectedLang (the SSE language event)');

// -- 3. /history imports the shared source and renders it in the research branch on BOTH paths
const historySrc = stripComments(readFileSync(new URL('../pages/history.tsx', import.meta.url), 'utf8'));
check(IMPORT_RE.test(historySrc), 'pages/history.tsx does not import getResearchDisclaimer from ../utils/researchDisclaimer');
check(!historySrc.includes(EN_LITERAL), 'pages/history.tsx carries the disclaimer literal (duplicate source)');
const rStart = historySrc.indexOf("item.session_type === 'research' && (() => {");
const rEnd = historySrc.indexOf("item.session_type === 'explain' && (() => {");
check(rStart > -1 && rEnd > rStart, 'could not locate the /history research branch (research IIFE before explain IIFE) - update this guard');
if (rStart > -1 && rEnd > rStart) {
  const branch = historySrc.slice(rStart, rEnd);
  const calls = (branch.match(/getResearchDisclaimer\(lang\)/g) || []).length;
  check(calls >= 2, `/history research branch renders getResearchDisclaimer(lang) ${calls} time(s); need one per render path (sections + pre-wrap) = 2`);
  check(branch.includes('whitespace-pre-wrap'), 'the legacy pre-wrap path disappeared from the research branch');
  const outside = historySrc.slice(0, rStart) + historySrc.slice(rEnd);
  check(!/getResearchDisclaimer\(/.test(outside), 'getResearchDisclaimer is called outside the research branch - Verify/Explain rows render their STORED disclaimer and must stay untouched');
}

if (failures.length) {
  console.error(`history_research_disclaimer_guard: ${failures.length} failure(s)`);
  for (const f of failures) console.error('  - ' + f);
  process.exit(1);
}
console.log('history_research_disclaimer_guard: all checks passed');
