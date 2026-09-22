// Guard: the Explain LEGACY (pre-wrap fallback) row on /history renders the
// server-supplied `item.disclaimer` — and NOTHING on the frontend carries a
// copy of the Explain disclaimer strings (HISTORY RENDER LEFTOVERS car,
// segment 2; TECH_DEBT [HONESTY][P3] "Explain LEGACY rows … WITHOUT any
// disclaimer"; transport ruled (ii) 2026-09-11, R1/R2 2026-09-22).
//
// WHAT BREAKS IF THIS FAILS (CLAUDE.md Rule 17/19): a legacy Explain row is a
// medical explanation with no stored caption. Segment 2 has /api/history fill
// `disclaimer` at READ time from the ONE Python source (api/i18n/
// explain_strings.py, 16 keys) keyed by `?locale=` — so (1) the page must ASK
// for it with the UI lang, (2) the pre-wrap path must RENDER it, and (5) no
// page may grow a second copy of the strings (option (i) was DECLINED
// 2026-09-11: two sources drift — the 2026-05 share/explore drift, 14 of 16
// locales, is the precedent). JSON Explain rows keep rendering their STORED
// parsed.disclaimer (R2) — (3) pins that those renders did not move.
//
// Source checks only (comments stripped), same technique as
// tests/history_research_disclaimer_guard.mjs. The Explain branch is located
// by the IIFE marker the research guard already uses; its END is the next
// `item.session_type ===` marker, derived — no line numbers hard-coded.
// Run: node tests/history_explain_disclaimer_guard.mjs   (also run by
// tests/test_history_explain_disclaimer.py inside the pytest count)
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const failures = [];
function check(cond, msg) { if (!cond) failures.push(msg); }
const stripComments = (src) => src.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/^\s*\/\/.*$/gm, ' ');
const count = (src, needle) => src.split(needle).length - 1;
const root = fileURLToPath(new URL('..', import.meta.url));

const historySrc = stripComments(readFileSync(join(root, 'pages', 'history.tsx'), 'utf8'));

// -- 1. The fetch asks for the caption in the UI language (R1: explicit ?locale=)
check(historySrc.includes('/api/history?locale='),
  'pages/history.tsx: the /api/history fetch does not pass ?locale= — the server would caption from Accept-Language (the browser), not the UI toggle');
check(historySrc.includes('encodeURIComponent(lang)'),
  'pages/history.tsx: ?locale= is not built from encodeURIComponent(lang) — the UI lang (useLang) must be the value sent');

// -- 2. EXACTLY ONE render of item.disclaimer, inside the Explain branch, AFTER the pre-wrap <p>
const eStart = historySrc.indexOf("item.session_type === 'explain' && (() => {");
check(eStart > -1, 'could not locate the /history Explain branch (explain IIFE marker) - update this guard');
let eEnd = -1;
if (eStart > -1) {
  const after = historySrc.slice(eStart + 1);
  const m = after.search(/item\.session_type === '/);
  eEnd = m > -1 ? eStart + 1 + m : historySrc.length;
}
// ONE render site = guard + value = 2 occurrences (the same unit as the parsed.disclaimer check below:
// `{item.disclaimer && (<p>{item.disclaimer}</p>)}`). 1 would mean an unguarded render; 4 a second site.
const total = count(historySrc, 'item.disclaimer');
check(total === 2, `item.disclaimer appears ${total} time(s) in pages/history.tsx (unit: occurrences); expected EXACTLY 2 = ONE render site (guard + value) — the Explain pre-wrap path only (R2: JSON rows keep parsed.disclaimer; Verify/Research untouched)`);
if (eStart > -1) {
  const branch = historySrc.slice(eStart, eEnd);
  const outside = historySrc.slice(0, eStart) + historySrc.slice(eEnd);
  check(count(branch, 'item.disclaimer') === 2, 'item.disclaimer is not rendered (guard + value) inside the Explain branch');
  check(count(outside, 'item.disclaimer') === 0, 'item.disclaimer is rendered OUTSIDE the Explain branch — Verify/Research rows must not caption from this field');
  // -- 6. The Explain pre-wrap <p> still exists INSIDE the Explain branch, and the caption FOLLOWS it.
  //       tests/research_list_render_guard.mjs:263 already asserts a whitespace-pre-wrap survives AFTER the
  //       research branch, and tests/test_history_render_fallback.py:64 asserts count >= 1 file-wide (both at
  //       d01ac6f). Neither says WHICH branch owns it; this guard asserts only that: it is the Explain one,
  //       and the disclaimer sits below the answer text, not above it.
  const preIdx = branch.indexOf('whitespace-pre-wrap');
  const discIdx = branch.indexOf('item.disclaimer');
  check(preIdx > -1, 'the Explain branch lost its whitespace-pre-wrap fallback <p> — the legacy path this segment captions no longer exists');
  check(preIdx > -1 && discIdx > preIdx,
    'item.disclaimer must be rendered AFTER the Explain whitespace-pre-wrap <p> (caption below the medical text, mirroring the JSON branch and the Research paths)');
  // the caption must be guarded (null on non-explain rows never reaches this branch, but a legacy row with a
  // server-side null must not render an empty <p>)
  check(/item\.disclaimer\s*&&/.test(branch), 'item.disclaimer must be conditionally rendered (`item.disclaimer && (...)`), like parsed.disclaimer is');
}

// -- 3. The two STORED-string renders (Explain JSON + Verify) did not move: 2 render sites × (guard + value)
//       = 4 occurrences, derived at d01ac6f. A count of 2 here would mean a site was deleted; 6 would mean one
//       was duplicated. Unit: occurrences, not sites.
const parsedCount = count(historySrc, 'parsed.disclaimer');
check(parsedCount === 4, `parsed.disclaimer appears ${parsedCount} time(s) (unit: occurrences); expected UNCHANGED at 4 (2 render sites × guard + value)`);

// -- 4. The Research disclaimer renders did not move (segment 4a, tests/history_research_disclaimer_guard.mjs)
const researchCount = count(historySrc, 'getResearchDisclaimer(');
check(researchCount === 2, `getResearchDisclaimer( appears ${researchCount} time(s); expected UNCHANGED at 2`);

// -- 5. NO frontend copy of any EXPLAIN_DISCLAIMERS value (option (i) DECLINED 2026-09-11; Rule 16 +0 keys)
//       Values are read from the ONE source, bounded to the EXPLAIN_DISCLAIMERS dict (lines 20-44 at d01ac6f —
//       the file holds three dicts; an unbounded sweep once counted 48 keys). Bounded by the dict's own
//       braces, not by line numbers, so the file can grow without breaking the guard.
const pySrc = readFileSync(join(root, 'api', 'i18n', 'explain_strings.py'), 'utf8');
const dictStart = pySrc.indexOf('EXPLAIN_DISCLAIMERS: Dict[str, str] = {');
const dictEnd = dictStart > -1 ? pySrc.indexOf('\n}', dictStart) : -1;
check(dictStart > -1 && dictEnd > dictStart, 'api/i18n/explain_strings.py: EXPLAIN_DISCLAIMERS dict not found - update this guard');
const values = [];
if (dictStart > -1 && dictEnd > dictStart) {
  for (const line of pySrc.slice(dictStart, dictEnd).split('\n')) {
    const m = line.match(/^\s*"([A-Za-z-]+)":\s*"(.*)",?\s*$/);
    if (m) values.push([m[1], m[2]]);
  }
}
check(values.length === 16, `EXPLAIN_DISCLAIMERS parsed to ${values.length} values (unit: dict keys); expected 16`);
const tsFiles = [];
(function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if (/\.(ts|tsx|js|jsx|mjs)$/.test(name)) tsFiles.push(p);
  }
})(join(root, 'pages'));
(function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if (/\.(ts|tsx|js|jsx|mjs)$/.test(name)) tsFiles.push(p);
  }
})(join(root, 'components'));
(function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if (/\.(ts|tsx|js|jsx|mjs)$/.test(name)) tsFiles.push(p);
  }
})(join(root, 'utils'));
check(tsFiles.length > 0, 'no frontend files found under pages/ components/ utils/ - update this guard');
for (const f of tsFiles) {
  // comments stripped, like every other check here: a comment that POINTS at the Python source
  // (utils/i18n-ui.ts:4647 "matches api/i18n/explain_strings.py pattern") is a pointer, not a copy.
  const src = stripComments(readFileSync(f, 'utf8'));
  for (const [key, value] of values) {
    const bare = value.replace(/^⚠️\s*/, '');
    check(!src.includes(value) && !(bare.length > 20 && src.includes(bare)),
      `${f.slice(root.length)} carries the Explain "${key}" disclaimer literal — the frontend must not hold a copy (option (i) DECLINED 2026-09-11)`);
  }
  check(!/explain_strings|EXPLAIN_DISCLAIMERS/.test(src), `${f.slice(root.length)} references the Python disclaimer source by name`);
}

if (failures.length) {
  console.error(`history_explain_disclaimer_guard: ${failures.length} failure(s)`);
  for (const f of failures) console.error('  - ' + f);
  process.exit(1);
}
console.log(`history_explain_disclaimer_guard: all checks passed (${tsFiles.length} frontend files scanned, ${values.length} disclaimer values)`);
