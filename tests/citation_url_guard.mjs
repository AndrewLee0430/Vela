// Guard: citation URLs must be usable, or explicitly exempt.
//
// WHAT BREAKS IF THIS FAILS: a citation renders "View source" with an unusable href. An
// `<a href="">` navigates to the CURRENT page, so the Next.js static-export SPA remounts
// /research at its empty state and the user LOSES their answer and references. That shipped
// to prod and survived three human-eye gates inside the one chip nobody clicked
// (docs/citation_deeplink_diagnosis.md).
//
// TWO LAYERS:
//   1. DATA  — every corpus document either has a usable https URL, or belongs to a source
//              with a DOCUMENTED exemption (below).
//   2. RENDER— isUsableSourceUrl() must reject exactly the values that cause the bug.
//
// ⚠️ NECESSARY BUT NOT SUFFICIENT. A non-empty https URL is not proof the link RESOLVES, and
// not proof it points at the CITED DOCUMENT. Resolve-verification status, 2026-07-29
// (tests/results/_citation_url_audit.py):
//   pubmed    https://pubmed.ncbi.nlm.nih.gov/12667121/          HTTP 200  document ✅
//   dailymed  drugInfo.cfm?setid=…                               HTTP 200  document ✅
//   tfda      mcp.fda.gov.tw/im_detail_pdf/… (percent-encoded)   HTTP 200  document ✅
//   openFDA   https://labels.fda.gov/                            HTTP 200  ⚠️ HOMEPAGE, NOT the
//             cited document — hard-coded at api/data_sources/fda.py:31-33. Passes this guard
//             by construction; recorded as a PROVENANCE finding, deliberately not "fixed" here.
//   local     ""                                                 ⛔ DEPRECATED — see below.
//
// ⛔ `local` — the EXEMPTION IS RETIRED, REPLACED BY A STRONGER INVARIANT (2026-07-29, c1).
//   The old exemption said: "690 docs ship url:'' by design; the RENDER guard suppresses the
//   anchor." That exemption's SUBJECT is gone — the corpus is no longer retrieved at all
//   (api/server.py `enable_local=False`), because every one of its documents is field-label
//   scaffolding with no values (payload <= 20 chars, max 5, median 1).
//   An exemption whose subject no longer exists is dead weight and would silently pass, so it
//   is replaced by the invariant that actually matters now:
//
//       LOCAL MUST NOT BE RETRIEVED — and if it ever is again, its URLs must be usable.
//
//   That is enforced CONDITIONALLY below: flipping `enable_local` back to True re-arms the
//   full URL check against the corpus, which still ships 690 empty URLs — so a silent
//   re-enable FAILS this guard instead of quietly restoring the answer-destroying bug.
//   ⛔ Do NOT "fix" a failure here by generating search URLs from drug names.
//
// Run: node tests/citation_url_guard.mjs
import { readFileSync } from 'node:fs';

const ROOT = new URL('..', import.meta.url);
const failures = [];
const check = (cond, msg) => { if (!cond) failures.push(msg); };

// ── layer 1: DATA ────────────────────────────────────────────────────────────────
const CORPORA = [
  { name: 'DailyMed', path: 'data/dailymed/label_docs.json', key: 'documents' },
  { name: 'TFDA',     path: 'data/tfda/indication_corpus.json', key: 'documents' },
];

const usable = (u) => /^https?:\/\/[^/\s]+/i.test((u ?? '').trim());

for (const c of CORPORA) {
  let raw;
  try {
    raw = JSON.parse(readFileSync(new URL(c.path, ROOT), 'utf8'));
  } catch {
    check(false, `${c.name}: corpus not readable at ${c.path} (build it before gating)`);
    continue;
  }
  const docs = raw[c.key];
  const bad = docs.filter(d => !usable(d.url));
  check(bad.length === 0,
    `${c.name}: ${bad.length}/${docs.length} documents have no usable https URL ` +
    `(e.g. ${bad.slice(0, 3).map(d => d.source_id).join(', ')})`);
}

// ── layer 1b: the LOCAL DEPRECATION invariant (replaces the retired exemption) ────
// The local corpus ships 690 empty URLs. It is safe ONLY because it is not retrieved.
// So assert the deprecation itself, and re-arm the URL check if it is ever undone.
const server = readFileSync(new URL('api/server.py', ROOT), 'utf8');
const localEnabled = /enable_local\s*=\s*True/.test(server);
check(!localEnabled,
  'api/server.py has enable_local=True — the local drug corpus is DEPRECATED (c1, 2026-07-29). ' +
  'It ships 690 documents with url:"" and <=20 chars of content; re-enabling it restores ' +
  'empty-href citations. If this is deliberate, the corpus must first gain usable per-document ' +
  'URLs — and see docs/local_corpus_decision_20260729.md before doing that.');

if (localEnabled) {
  // Re-armed: if someone re-enables local, hold it to the SAME bar as every other source.
  try {
    const raw = JSON.parse(readFileSync(new URL('data/drug_vectordb/index.json', ROOT), 'utf8'));
    const docs = raw.documents ?? [];
    const bad = docs.filter(d => !usable(d.url));
    check(bad.length === 0,
      `local: re-enabled, but ${bad.length}/${docs.length} documents still have no usable https URL ` +
      `(e.g. ${bad.slice(0, 3).map(d => d.source_id).join(', ')})`);
  } catch {
    check(false, 'local: re-enabled but data/drug_vectordb/index.json is not readable');
  }
}

// ── layer 2: RENDER — isUsableSourceUrl() semantics ──────────────────────────────
// Mirrors components/CitationPanel.tsx exactly; kept in sync by the assertions below.
const isUsableSourceUrl = (url) => {
  const u = (url ?? '').trim();
  if (!u) return false;
  return /^https?:\/\/[^/\s]+/i.test(u);
};

// MUST reject — each of these produces the answer-destroying same-page navigation, or worse.
for (const bad of ['', '   ', null, undefined, '/research', 'research', '#',
                   'javascript:alert(1)', 'data:text/html,x', 'labels.fda.gov']) {
  check(isUsableSourceUrl(bad) === false, `isUsableSourceUrl(${JSON.stringify(bad)}) must be false`);
}
// MUST accept — real citation URLs observed in live payloads (all HTTP 200, see header).
for (const good of ['https://pubmed.ncbi.nlm.nih.gov/12667121/',
                    'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=ca73b519-015a-436d-aa3c-af53492825a1',
                    'https://mcp.fda.gov.tw/im_detail_pdf/%E8%A1%9B%E7%BD%B2',
                    'https://labels.fda.gov/']) {
  check(isUsableSourceUrl(good) === true, `isUsableSourceUrl(${JSON.stringify(good)}) must be true`);
}

// The component must actually GATE the anchor on this helper — not merely export it.
const panel = readFileSync(new URL('components/CitationPanel.tsx', ROOT), 'utf8');
check(/isUsableSourceUrl\(citation\.url\)\s*&&/.test(panel),
  'CitationPanel.tsx must gate the <a> on isUsableSourceUrl(citation.url) && …');
check(/export function isUsableSourceUrl/.test(panel),
  'CitationPanel.tsx must export isUsableSourceUrl so this guard tests the real helper');

if (failures.length) {
  console.error(`citation-url GUARD FAILED (${failures.length}):\n - ` + failures.join('\n - '));
  process.exit(1);
}
console.log('PASS  citation URLs — DailyMed/TFDA usable, local DEPRECATED (enable_local=False), ' +
            'isUsableSourceUrl rejects empty/relative/non-http, anchor is gated');
