// Guard / unit test: /history render fallbacks (HISTORY car segment 1).
//
// WHAT BREAKS IF THIS FAILS (CLAUDE.md Rule 17/18): legacy rows — every verify
// row written before segment 1 (summary strings) and every research row whose
// stored markdown doesn't match the Rule-12 section format — must take the
// plain-text fallback branch, never render blank, and never crash the page.
// And new-format verify JSON must parse to the cards path with the fields the
// renderer keys on (canonical severity, attribution_kind, summary).
//
// No test runner → transpile the REAL sources standalone:
//   * utils/researchSections.ts has zero imports — transpiled whole.
//   * parseVerifyAnswer is extracted VERBATIM from pages/history.tsx at run
//     time, so this guard cannot silently drift from the page — if the function
//     is renamed or moved, this fails loudly instead of testing a stale copy.
// Run: node tests/history_render_fallback_guard.mjs   (also run by
// tests/test_history_render_fallback.py inside the pytest count)
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const failures = [];
function check(cond, msg) { if (!cond) failures.push(msg); }
function eq(a, e, msg) { if (JSON.stringify(a) !== JSON.stringify(e)) failures.push(`${msg}: expected ${JSON.stringify(e)} got ${JSON.stringify(a)}`); }

const OPTS = { compilerOptions: { module: 'ESNext', target: 'ES2020' } };

// ── 1. Research: the shared parser the page now renders through ─────────────
const rsSrc = readFileSync(new URL('../utils/researchSections.ts', import.meta.url), 'utf8');
const rsJs = ts.transpileModule(rsSrc, OPTS).outputText;
const rs = await import('data:text/javascript,' + encodeURIComponent(rsJs));
const { parseResearchSections, stripLlmDisclaimer } = rs;

// Rule-12-conforming stored answer → two titled section cards.
const conforming = '## Summary — 繁體中文\n\nMetformin 是第一線用藥 [1]。\n\n---\n\n## Clinical Notes — 繁體中文\n\n- 腎功能 eGFR < 30 停用 [2]\n';
const sections = parseResearchSections(conforming);
check(sections !== null && sections.length === 2, 'conforming answer → 2 sections');
eq(sections?.[0]?.title, 'Summary', 'title sanitized (" — Lang" suffix stripped)');
check(!!sections?.[1]?.content.includes('eGFR'), 'section content preserved');
check(!!sections?.[0]?.content.includes('[1]'),
  '[N] markers stay literal text (non-resolving — half B deferred, no fake links)');

// Legacy / non-conforming / empty rows → null → the pre-wrap fallback branch.
check(parseResearchSections('plain prose answer with no headers') === null,
  'no-header legacy answer → null (fallback branch)');
check(parseResearchSections('') === null, 'empty answer → null (fallback), not a crash');
check(parseResearchSections('## OnlyHeader\n') === null,
  'header with no content → null (fallback), not an empty card');

// The LLM-disclaimer strip runs before parsing (same order as /research).
check(!stripLlmDisclaimer('text\n⚠️ For informational purposes only. x').includes('informational'),
  'trailing LLM disclaimer stripped before parsing');

// ── 2. Verify: safe-parse extracted verbatim from pages/history.tsx ─────────
const pageSrc = readFileSync(new URL('../pages/history.tsx', import.meta.url), 'utf8');
const fnMatch = pageSrc.match(/function parseVerifyAnswer[\s\S]*?\n\}/);
check(!!fnMatch, 'parseVerifyAnswer not found in pages/history.tsx — update this guard');
let parseVerifyAnswer = null;
if (fnMatch) {
  const pvJs = ts.transpileModule('export ' + fnMatch[0], OPTS).outputText;
  ({ parseVerifyAnswer } = await import('data:text/javascript,' + encodeURIComponent(pvJs)));
}

if (parseVerifyAnswer) {
  // Legacy summary rows — the three shapes every pre-segment-1 site wrote.
  check(parseVerifyAnswer('Found 1 interaction(s): 1 Major') === null,
    'legacy main-site summary → null (plain-box fallback)');
  check(parseVerifyAnswer('⚠️ No FDA label data found. Possible interaction.') === null,
    'legacy fb_summary → null (plain-box fallback)');
  check(parseVerifyAnswer('TFDA grounding — x. No FDA label data found. Please use specific drug names.') === null,
    'legacy fallback_summary (TFDA-prefixed) → null (plain-box fallback)');
  // Malformed / wrong-shape JSON → null, never a throw out of the parser.
  check(parseVerifyAnswer('{"summary": "json but no interactions array"}') === null,
    'JSON without interactions[] → null (fallback)');
  check(parseVerifyAnswer('null') === null, 'JSON null → null (fallback)');
  check(parseVerifyAnswer('') === null, 'empty answer → null (fallback)');
  // New-format payload → the cards path, with the renderer's key fields intact.
  const payload = JSON.stringify({
    drugs_analyzed: ['aspirin', 'warfarin'],
    interactions: [{ drug_pair: ['aspirin', 'warfarin'], severity: 'Major',
      description: 'd', clinical_recommendation: 'r', source: 's',
      source_url: null, attribution_kind: 'dailymed_grounded' }],
    summary: 'Found 1 interaction(s): 1 Major', risk_level: 'Major',
    risk_level_label: null, response_language: 'en', disclaimer: 'x',
    tfda_groundings: null, verification_status: 'ok',
  });
  const parsed = parseVerifyAnswer(payload);
  check(parsed !== null && parsed.interactions.length === 1, 'new-format payload → cards path');
  eq(parsed?.interactions?.[0]?.severity, 'Major', 'canonical severity enum reaches the renderer');
  eq(parsed?.interactions?.[0]?.attribution_kind, 'dailymed_grounded',
    'attribution_kind enum reaches the renderer');
  eq(parsed?.summary, 'Found 1 interaction(s): 1 Major',
    'summary present — the ShareButton text source for new-format rows');
}

// ── Report ──────────────────────────────────────────────────────────────────
if (failures.length) {
  console.log('FAILURES:');
  for (const f of failures) console.log('  ✗ ' + f);
  process.exit(1);
}
console.log('history_render_fallback_guard: all checks passed');
process.exit(0);
