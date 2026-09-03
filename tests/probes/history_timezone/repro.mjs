// created_at timezone reproduction — Rule 20 committed evidence for the
// TECH_DEBT [HONESTY][P2] "timestamps shown in the wrong timezone" entry
// (filed 2026-09-03) and the HISTORY HONESTY car, segment 1.
//
// What it proves: the SAME instant, serialized two ways by the API, renders as
// two different wall-clock times in pages/history.tsx — because an offset-less
// date-time string is parsed as LOCAL time by ECMAScript, and one carrying
// "+00:00" is parsed as UTC. The formatter and its options are copied VERBATIM
// from pages/history.tsx:285-288; the viewer timezone is pinned to Asia/Taipei
// (UTC+8, the founder's screenshot timezone).
//
//   BEFORE (fly 244 wire)     "2026-09-03T03:21:37"        -> "Sep 3, 2026, 03:21 AM"   (WRONG: UTC read as local)
//   AFTER  (segment-1 wire)   "2026-09-03T03:21:37+00:00"  -> "Sep 3, 2026, 11:21 AM"   (the actual Taipei wall clock)
//
// Also records the MySharesTab.tsx skew: Date.parse(naive) - Date.parse(+00:00)
// for the same instant = -8 h in Taipei, which is why a share made a minute ago
// read as "~8 hours ago".
//
// Usage (TZ is pinned inside the script; the env prefix is belt-and-braces):
//   TZ=Asia/Taipei node tests/probes/history_timezone/repro.mjs
// Writes result.json next to this file. Exits 1 if TZ is not honoured or any
// expectation fails — a silent wrong-TZ run would look like a pass.
process.env.TZ = 'Asia/Taipei'; // must precede any Date use (Node re-reads TZ lazily)

import { writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

// pages/history.tsx:285-288 — verbatim
const OPTS = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
const render = (wire) => new Date(wire).toLocaleString('en-US', OPTS);

// Pin check: the probe is meaningless unless the process really is UTC+8.
const offsetMin = new Date('2026-09-03T00:00:00Z').getTimezoneOffset();
const resolvedTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
if (offsetMin !== -480) {
  console.error(`TZ not honoured: getTimezoneOffset()=${offsetMin} (expected -480), resolved=${resolvedTz}`);
  process.exit(1);
}

// The exact wire strings. Rows 1-2 are the pydantic BEFORE/AFTER strings for
// datetime(2026,9,3,3,21,37) (reproduced in the segment-1 report). Rows 3-4 are
// the real-row shape with microseconds (the §10 gate row, dev id 2334, was
// stored as 03:21:37.726010) — V8 must accept 6 fractional digits for the fix
// to work on real rows, so that is asserted too.
const CASES = [
  { id: 'before_naive',           wire: '2026-09-03T03:21:37',              expected: 'Sep 3, 2026, 03:21 AM' },
  { id: 'after_utc_offset',       wire: '2026-09-03T03:21:37+00:00',        expected: 'Sep 3, 2026, 11:21 AM' },
  { id: 'before_naive_micros',    wire: '2026-09-03T03:21:37.726010',       expected: 'Sep 3, 2026, 03:21 AM' },
  { id: 'after_utc_offset_micros',wire: '2026-09-03T03:21:37.726010+00:00', expected: 'Sep 3, 2026, 11:21 AM' },
];

const rows = CASES.map((c) => {
  const ms = Date.parse(c.wire);
  const rendered = Number.isFinite(ms) ? render(c.wire) : 'INVALID DATE';
  return {
    ...c,
    parsed_epoch_ms: ms,
    parsed_utc: Number.isFinite(ms) ? new Date(ms).toISOString() : null,
    rendered_in_taipei: rendered,
    pass: rendered === c.expected,
  };
});

const skewMs = Date.parse(CASES[0].wire) - Date.parse(CASES[1].wire);
const result = {
  probe: 'tests/probes/history_timezone/repro.mjs',
  purpose: 'Same instant, naive vs +00:00 wire string, rendered through pages/history.tsx formatter under Asia/Taipei',
  node: process.version,
  tz_env: process.env.TZ,
  tz_resolved: resolvedTz,
  getTimezoneOffset_min: offsetMin,
  formatter: "new Date(wire).toLocaleString('en-US', {year:'numeric', month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'})",
  cases: rows,
  myshares_skew: {
    note: 'components/MySharesTab.tsx relativeTime()/daysSince() use Date.parse(iso); naive minus +00:00 for the SAME instant',
    naive_minus_utc_ms: skewMs,
    naive_minus_utc_hours: skewMs / 3600000,
    expected_hours: -8,
    pass: skewMs === -8 * 3600000,
  },
};
result.all_pass = rows.every((r) => r.pass) && result.myshares_skew.pass;

const out = join(dirname(fileURLToPath(import.meta.url)), 'result.json');
writeFileSync(out, JSON.stringify(result, null, 2) + '\n');
for (const r of rows) console.log(`${r.pass ? 'PASS' : 'FAIL'}  ${r.id.padEnd(24)} ${r.wire.padEnd(34)} -> ${r.rendered_in_taipei}`);
console.log(`${result.myshares_skew.pass ? 'PASS' : 'FAIL'}  myshares skew: naive - utc = ${skewMs / 3600000} h`);
console.log(`wrote ${out}`);
process.exit(result.all_pass ? 0 : 1);
