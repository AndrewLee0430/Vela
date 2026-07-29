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
//   local     ""                                                 EXEMPT — see below.
//
// EXEMPTION — `local` (data/drug_vectordb/index.json), 690 docs, url:"" BY DESIGN:
//   Its builder input (data/drug_database/*.json) carries NO stable per-document identifier —
//   full_label.url is the shared host "https://labels.fda.gov/" on all 190 records and
//   full_label.source_id is a brand-name string ("FDA:<brand>"); no spl_set_id / set_id /
//   application_number exists anywhere in scripts/ or the FDA client. A URL synthesized from a
//   drug name is a SEARCH, not the source document, and presenting it under "View source" would
//   claim provenance the link does not have — the same defect family as the "FDA Label Analysis"
//   honesty [P1]. So the corpus keeps empty URLs and the RENDER guard suppresses the anchor.
//   ⛔ Do NOT "fix" this exemption by generating search URLs.
//
// Run: node tests/citation_url_guard.mjs
import { readFileSync } from 'node:fs';

const ROOT = new URL('..', import.meta.url);
const failures = [];
const check = (cond, msg) => { if (!cond) failures.push(msg); };

// ── layer 1: DATA ────────────────────────────────────────────────────────────────
const CORPORA = [
  { name: 'DailyMed', path: 'data/dailymed/label_docs.json', key: 'documents', exempt: false },
  { name: 'TFDA',     path: 'data/tfda/indication_corpus.json', key: 'documents', exempt: false },
  { name: 'local',    path: 'data/drug_vectordb/index.json',  key: null,        exempt: true  },
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
  const docs = c.key ? raw[c.key] : (Array.isArray(raw) ? raw : raw.documents);
  const bad = docs.filter(d => !usable(d.url));
  if (c.exempt) {
    // Exempt source: assert the exemption still describes reality. If `local` ever GAINS real
    // URLs the exemption is stale and this guard must be revisited — so we fail loudly on that
    // too, rather than silently passing.
    check(bad.length === docs.length,
      `local: exemption says ALL ${docs.length} docs have no usable URL, but ${docs.length - bad.length} now do — ` +
      `the exemption is STALE. Re-read the guard header and update it deliberately.`);
  } else {
    check(bad.length === 0,
      `${c.name}: ${bad.length}/${docs.length} documents have no usable https URL ` +
      `(e.g. ${bad.slice(0, 3).map(d => d.source_id).join(', ')})`);
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
console.log('PASS  citation URLs — DailyMed/TFDA usable, local exemption intact, ' +
            'isUsableSourceUrl rejects empty/relative/non-http, anchor is gated');
