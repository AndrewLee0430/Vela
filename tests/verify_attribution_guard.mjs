// Guard: the Option-C attribution mapping must stay wired (CLAUDE.md Rule 17).
//
// WHAT BREAKS IF THIS FAILS: the Verify honesty marker silently disappears (or reads as
// label-stated) for an attribution_kind whose caption mapping was dropped/renamed. The
// enum + this guard exist precisely so that failure goes RED here instead of vanishing
// from the rendered card unnoticed.
//
// No test runner in this repo → we transpile utils/i18n-verify.ts in-memory with the
// installed `typescript` package (its only import is `import type`, erased at transpile,
// so the output is self-contained) and exercise the real exports.
//
// Run: node tests/verify_attribution_guard.mjs
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const src = readFileSync(new URL('../utils/i18n-verify.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(src, {
  compilerOptions: { module: 'ESNext', target: 'ES2020' },
}).outputText;
const mod = await import('data:text/javascript,' + encodeURIComponent(js));

const { ATTRIBUTION_KINDS, getSourceCaptionByKind, getAiSeverityNote } = mod;

// The locales that define their own provenance block (others fall back to en via pick()).
const DEFINED_LOCALES = ['en', 'zh-TW', 'zh-CN', 'ja', 'ko', 'es', 'de'];

// Each stable kind must resolve to a caption that carries its distinguishing token — this
// catches a rename/drop where the SAFE fallback would otherwise mask the break by still
// returning a (wrong) non-empty caption.
const KIND_TOKEN = {
  dailymed_grounded: /dailymed/i,
  openfda_analysis: /fda/i,
  no_label: /clinical|no fda label/i,
};

const failures = [];
function check(cond, msg) { if (!cond) failures.push(msg); }

// 0. The enum is exactly the three ratified values.
check(
  JSON.stringify([...ATTRIBUTION_KINDS].sort()) ===
    JSON.stringify(['dailymed_grounded', 'no_label', 'openfda_analysis']),
  `ATTRIBUTION_KINDS drifted: ${JSON.stringify(ATTRIBUTION_KINDS)}`,
);

// 1. Every kind → a non-empty caption in every defined locale, and the EN caption carries
//    the kind's distinguishing token (so a mis-map is caught, not masked by the fallback).
for (const kind of ATTRIBUTION_KINDS) {
  for (const lang of DEFINED_LOCALES) {
    const cap = getSourceCaptionByKind(lang, kind);
    check(typeof cap === 'string' && cap.trim().length > 0,
      `empty caption for kind=${kind} lang=${lang}`);
  }
  const enCap = getSourceCaptionByKind('en', kind);
  check(KIND_TOKEN[kind].test(enCap),
    `kind=${kind} EN caption lost its token (${KIND_TOKEN[kind]}): ${JSON.stringify(enCap)}`);
}

// 2. The AI-severity marker is present (non-empty) in every defined locale.
for (const lang of DEFINED_LOCALES) {
  const note = getAiSeverityNote(lang);
  check(typeof note === 'string' && note.trim().length > 0,
    `empty aiSeverityNote for lang=${lang}`);
}

// 3. SAFE default: an unknown/absent kind still yields a non-empty caption == the
//    openfda_analysis caption (an honesty marker, NEVER empty, NEVER label-stated).
const openfdaCap = getSourceCaptionByKind('en', 'openfda_analysis');
for (const bogus of [undefined, null, '', 'totally_unknown_kind']) {
  const cap = getSourceCaptionByKind('en', bogus);
  check(cap === openfdaCap && cap.trim().length > 0,
    `unsafe fallback for ${JSON.stringify(bogus)}: ${JSON.stringify(cap)}`);
}

// 4. Wording fix (P3): zh-TW severity marker reads 研判 (inference), not 判定 (verdict).
const zhtw = getAiSeverityNote('zh-TW');
check(zhtw.includes('研判'), `zh-TW marker should use 研判: ${JSON.stringify(zhtw)}`);
check(!zhtw.includes('判定'), `zh-TW marker still uses verdict-toned 判定: ${JSON.stringify(zhtw)}`);

if (failures.length) {
  console.error('GUARD FAILED:\n - ' + failures.join('\n - '));
  process.exit(1);
}
console.log(`PASS  attribution guard — ${ATTRIBUTION_KINDS.length} kinds × ${DEFINED_LOCALES.length} locales, safe-default + 研判 wording OK`);
