// Guard / unit test: /history render fallbacks (HISTORY car segment 1).
//
// WHAT BREAKS IF THIS FAILS (CLAUDE.md Rule 17/18): legacy rows — every verify
// row written before segment 1 (summary strings) and every research row whose
// stored markdown doesn't match the Rule-12 section format — must take the
// plain-text fallback branch, never render blank, and never crash the page.
// And new-format verify JSON must parse to the cards path with the fields the
// renderer keys on (canonical severity, attribution_kind, summary).
// Segment 3 (Research half B): research_v1 JSON rows must parse to the
// markdown + citations path (the section parser is fed the MARKDOWN, never the
// JSON); pre-segment-3 plain-markdown rows, malformed JSON and foreign-kind
// JSON must all return null → the half-A path on the raw stored text.
//
// No test runner → transpile the REAL sources standalone:
//   * utils/researchSections.ts has zero imports — transpiled whole.
//   * parseVerifyAnswer / parseResearchAnswer are extracted VERBATIM from
//     pages/history.tsx at run time, so this guard cannot silently drift from
//     the page — if a function is renamed or moved, this fails loudly instead
//     of testing a stale copy.
// HISTORY HONESTY car segment 3: the trust-signal DECISION (researchTrustSignal,
// extracted verbatim) and the shared FallbackBanner / ProvenanceLine components
// RENDERED through react-dom/server (transpiled into tests/results/, gitignored).
// Run: node tests/history_render_fallback_guard.mjs   (also run by
// tests/test_history_render_fallback.py inside the pytest count)
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import ts from 'typescript';
import React from 'react';
import ReactDOMServer from 'react-dom/server';

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

// ── 3. Research half B: research_v1 safe-parse extracted verbatim ───────────
const rsFnMatch = pageSrc.match(/function parseResearchAnswer[\s\S]*?\n\}/);
check(!!rsFnMatch, 'parseResearchAnswer not found in pages/history.tsx — update this guard');
let parseResearchAnswer = null;
if (rsFnMatch) {
  const prJs = ts.transpileModule('export ' + rsFnMatch[0], OPTS).outputText;
  ({ parseResearchAnswer } = await import('data:text/javascript,' + encodeURIComponent(prJs)));
}

if (parseResearchAnswer) {
  // Legacy rows — every research row written before segment 3 is plain markdown
  // (conforming or not) and must take the half-A path on the raw text.
  check(parseResearchAnswer(conforming) === null,
    'pre-segment-3 conforming markdown → null (half-A sections on the raw text)');
  check(parseResearchAnswer('plain prose answer with no headers') === null,
    'pre-segment-3 free text → null (pre-wrap on the raw text)');
  check(parseResearchAnswer('') === null, 'empty answer → null (fallback), not a crash');
  // Malformed / foreign-kind JSON → null, never a throw, never a blank card.
  check(parseResearchAnswer('{"kind": "research_v1", "answer": ') === null,
    'truncated JSON → null (pre-wrap on the raw text, never blank)');
  check(parseResearchAnswer('null') === null, 'JSON null → null (fallback)');
  check(parseResearchAnswer('{"interactions": [], "summary": "x"}') === null,
    'foreign-kind JSON (a verify payload) → null');
  check(parseResearchAnswer('{"kind": "research_v1", "answer": 42, "citations": []}') === null,
    'research_v1 with a non-string answer → null (never render a number as markdown)');
  check(parseResearchAnswer('{"kind": "research_v2", "answer": "x", "citations": []}') === null,
    'unknown kind → null (a future schema must not be half-rendered by this branch)');

  // New-format payload → markdown + citations, with the section parser fed the MARKDOWN.
  const citations = [
    { id: 1, source_type: 'pubmed', source_id: 'PMID:1', title: 'T1', snippet: 's1',
      url: 'https://pubmed.ncbi.nlm.nih.gov/1/', credibility: 'peer-reviewed', year: '2021' },
    { id: 2, source_type: 'dailymed', source_id: 'setid:abc', title: 'T2', snippet: 's2',
      url: 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=abc', credibility: 'official' },
  ];
  const payload = JSON.stringify({ kind: 'research_v1', answer: conforming, citations });
  const parsed = parseResearchAnswer(payload);
  check(parsed !== null, 'research_v1 payload → cards path');
  eq(parsed?.answer, conforming, 'markdown round-trips byte-identically out of the JSON');
  eq(parsed?.citations?.map(c => c.id), [1, 2], 'citation ids reach the CitationPanel');
  eq(parsed?.citations?.[0]?.source_type, 'pubmed', 'citation objects reach the panel unshaped');
  const viaJson = parseResearchSections(stripLlmDisclaimer(parsed?.answer ?? ''));
  check(viaJson !== null && viaJson.length === 2,
    'JSON row → the section parser sees the MARKDOWN and yields 2 sections');
  check(!!viaJson?.[0]?.content.includes('[1]'),
    '[N] markers stay literal text on the JSON path too (resolution is the adjacent panel, as on /research)');
  // Citations key missing → [] (older writer / hand-seeded row), never a crash on .length.
  const noCit = parseResearchAnswer(JSON.stringify({ kind: 'research_v1', answer: conforming }));
  eq(noCit?.citations, [], 'missing citations key → empty list');

  // ── Segment 2 (HISTORY HONESTY car, founder ruling D2 (i) 2026-09-04): the writer
  // adds an OPTIONAL `fallback` boolean to research_v1. The parser must KEEP it
  // (rendering is segment 3) and must treat absence as UNKNOWN — never as false —
  // because every row written before segment 2 lacks the key and was never
  // observed either way.
  const fbTrue = parseResearchAnswer(JSON.stringify({ kind: 'research_v1', answer: conforming, citations: [], fallback: true }));
  check(fbTrue !== null && fbTrue.fallback === true,
    'segment 2: fallback:true survives the parse (a no-literature answer stays marked)');
  const fbFalse = parseResearchAnswer(JSON.stringify({ kind: 'research_v1', answer: conforming, citations, fallback: false }));
  check(fbFalse !== null && fbFalse.fallback === false,
    'segment 2: fallback:false survives the parse (a grounded answer is marked as observed-grounded)');
  check(noCit !== null && noCit.fallback === undefined,
    'pre-segment-2 v1 row (no fallback key) → fallback undefined = UNKNOWN, never false');
  const fbJunk = parseResearchAnswer(JSON.stringify({ kind: 'research_v1', answer: conforming, citations: [], fallback: 'yes' }));
  check(fbJunk !== null && fbJunk.fallback === undefined,
    'non-boolean fallback value → undefined (UNKNOWN), never a truthy string rendered as a caveat');
  // JSON row whose markdown is NON-conforming → parsed (citations kept) but the
  // section parser returns null → the pre-wrap path must show the MARKDOWN, not the JSON.
  const nonConforming = parseResearchAnswer(JSON.stringify({ kind: 'research_v1', answer: 'plain prose', citations }));
  check(nonConforming !== null && parseResearchSections(nonConforming.answer) === null,
    'non-conforming markdown inside JSON → pre-wrap path');
  check(nonConforming?.answer === 'plain prose' && !nonConforming.answer.startsWith('{'),
    'the pre-wrap text is the markdown, never the raw JSON');
}

// ── 4. HISTORY HONESTY car segment 3: the trust signal on /history ──────────
// (a) The DECISION — researchTrustSignal(parsed), extracted verbatim from
//     pages/history.tsx. fallback:true → the FallbackBanner (no provenance line,
//     even with citations — mutually exclusive, fallback wins as on /research);
//     fallback:false + ≥1 citation → the ProvenanceLine; UNKNOWN (no key,
//     non-boolean, legacy row) → NEITHER. Absence is never rendered as grounded.
const tsFnMatch = pageSrc.match(/function researchTrustSignal[\s\S]*?\n\}/);
check(!!tsFnMatch, 'researchTrustSignal not found in pages/history.tsx — update this guard');
let researchTrustSignal = null;
if (tsFnMatch) {
  const tsJs = ts.transpileModule('export ' + tsFnMatch[0], OPTS).outputText;
  ({ researchTrustSignal } = await import('data:text/javascript,' + encodeURIComponent(tsJs)));
}
const sigCits = [
  { id: 1, source_type: 'pubmed', source_id: 'PMID:1', title: 'T1', snippet: 's1', url: 'https://pubmed.ncbi.nlm.nih.gov/1/' },
  { id: 2, source_type: 'pubmed', source_id: 'PMID:2', title: 'T2', snippet: 's2', url: 'https://pubmed.ncbi.nlm.nih.gov/2/' },
];
if (researchTrustSignal && parseResearchAnswer) {
  const row = (extra) => parseResearchAnswer(JSON.stringify({ kind: 'research_v1', answer: conforming, ...extra }));
  eq(researchTrustSignal(row({ citations: [], fallback: true })), 'fallback',
    'fallback:true, 0 citations → the FallbackBanner');
  eq(researchTrustSignal(row({ citations: sigCits, fallback: true })), 'fallback',
    'fallback:true WITH citations → still the banner, never the provenance line (mutual exclusivity as on /research)');
  eq(researchTrustSignal(row({ citations: sigCits, fallback: false })), 'provenance',
    'fallback:false + ≥1 citation → the ProvenanceLine');
  eq(researchTrustSignal(row({ citations: [], fallback: false })), 'none',
    'fallback:false + 0 citations → nothing (no count to show; /research renders null here too)');
  eq(researchTrustSignal(row({ citations: sigCits })), 'none',
    'pre-segment-2 v1 row (no fallback key) WITH citations → NEITHER: UNKNOWN is never rendered as grounded');
  eq(researchTrustSignal(row({ citations: [] })), 'none',
    'pre-segment-2 v1 row, no citations → neither (the old noCit case is unchanged)');
  eq(researchTrustSignal(row({ citations: sigCits, fallback: 'yes' })), 'none',
    'non-boolean fallback → neither (never a truthy string read as a caveat)');
  eq(researchTrustSignal(null), 'none', 'legacy plain-markdown row (parser null) → neither');
}

// (b) The MARKERS — the shared components render the i18n strings the user
//     actually reads. Real render via react-dom/server: the component, the UI
//     strings and the source-label map are transpiled into tests/results/
//     (gitignored) so relative imports resolve; classic JSX runtime so no
//     jsx-runtime named-export interop is needed.
const esc = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
const TSX_OPTS = { compilerOptions: { module: 'ESNext', target: 'ES2020', jsx: 'react' } };
const outDir = new URL('./results/_history_trust_signal/', import.meta.url);
let trust = null, uiMod = null;
try {
  mkdirSync(outDir, { recursive: true });
  const emit = (srcRel, outName, rewrite = (x) => x) => {
    const src = readFileSync(new URL(srcRel, import.meta.url), 'utf8');
    writeFileSync(new URL(outName, outDir), rewrite(ts.transpileModule(src, TSX_OPTS).outputText));
  };
  emit('../utils/i18n-ui.ts', 'i18n-ui.mjs');
  emit('../utils/sourceLabels.ts', 'sourceLabels.mjs');
  emit('../components/ResearchTrustSignal.tsx', 'ResearchTrustSignal.mjs', (js) =>
    "import React from 'react';\n" + js
      .replace(/^\s*"use client";?\s*$/m, '')   // a Next directive; an unused expression under node/eslint
      .replace(/from ['"]\.\.\/utils\/i18n-ui['"]/g, "from './i18n-ui.mjs'")
      .replace(/from ['"]\.\.\/utils\/sourceLabels['"]/g, "from './sourceLabels.mjs'"));
  trust = await import(new URL('ResearchTrustSignal.mjs', outDir).href);
  uiMod = await import(new URL('i18n-ui.mjs', outDir).href);
} catch (e) {
  check(false, `shared trust-signal components not renderable (components/ResearchTrustSignal.tsx): ${e.message}`);
}
if (trust && uiMod) {
  const render = (Comp, props) => ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, props));
  const en = uiMod.getUI('en'), zh = uiMod.getUI('zh-TW');
  check(typeof trust.FallbackBanner === 'function' && typeof trust.ProvenanceLine === 'function',
    'FallbackBanner + ProvenanceLine are named exports of components/ResearchTrustSignal');
  const bannerEn = render(trust.FallbackBanner, { lang: 'en' });
  check(bannerEn.includes(esc(en.noLiteratureFound)), 'FallbackBanner (en) renders noLiteratureFound — the caveat the user reads');
  check(bannerEn.includes(esc(en.fallbackBasis)), 'FallbackBanner (en) renders the fallbackBasis body line (Rule 19: carried, not just the title)');
  const bannerZh = render(trust.FallbackBanner, { lang: 'zh-TW' });
  check(bannerZh.includes(esc(zh.noLiteratureFound)) && !bannerZh.includes(esc(en.noLiteratureFound)),
    'FallbackBanner follows the lang PROP (zh-TW strings, not English) — no hook inside the shared component');
  const prov = render(trust.ProvenanceLine, { lang: 'en', citations: sigCits });
  check(prov.includes(esc(en.provenanceSourced.replace('{count}', '2'))),
    'ProvenanceLine renders the sourced-count sentence with the REAL citation count (2), not a self-label');
  check(!/bg-white|text-gray-/.test(prov),
    'ProvenanceLine tooltip carries no light-only classes (§3.6 item 4: bg-white / text-gray-600 was illegible in dark)');
  check(prov.includes('--color-paper-2') && prov.includes('--color-card-border'),
    'ProvenanceLine tooltip surface + border come from theme tokens (legible in both schemes)');
  const provZh = render(trust.ProvenanceLine, { lang: 'zh-TW', citations: sigCits });
  check(provZh.includes(esc(zh.provenanceSourced.replace('{count}', '2'))),
    'ProvenanceLine follows the lang PROP (zh-TW)');
  const provEmpty = render(trust.ProvenanceLine, { lang: 'en', citations: [] });
  check(typeof provEmpty === 'string', 'ProvenanceLine with 0 citations does not throw (the render rule, not the component, gates it)');
}

// ── Report ──────────────────────────────────────────────────────────────────
if (failures.length) {
  console.log('FAILURES:');
  for (const f of failures) console.log('  ✗ ' + f);
  process.exit(1);
}
console.log('history_render_fallback_guard: all checks passed');
process.exit(0);
