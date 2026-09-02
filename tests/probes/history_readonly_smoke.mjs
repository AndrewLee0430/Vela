// History page WRITE-SCOPE guard — asserts the ONLY mutation originating in
// pages/history.tsx is the per-entry DELETE to /api/history/{id}.
//
// Rule 20: this is committed evidence (script), not scratch.
// Usage: node tests/probes/history_readonly_smoke.mjs      (reads SOURCE, no build needed)
//
// ─────────────────────────────────────────────────────────────────────────────
// NARROWED 2026-09-02 (HISTORY car, delete segment — founder ruling #10)
// ─────────────────────────────────────────────────────────────────────────────
// Until this segment, this probe asserted "reads, and only reads": NO mutating
// HTTP verb anywhere in the page. That property is now FALSE BY DESIGN — the
// per-entry delete (founder-ratified option (d)(iii), 2026-09-01/02) puts one
// deliberate DELETE fetch in this page. The probe's own header made removal
// the decision point: "whoever builds it must DELETE THIS PROBE DELIBERATELY,
// in the same commit, with the reasoning written down."
//
// The reasoning: NARROWED, not retired. The business rule this probe exists
// for is NOT "the page never mutates" — it is "READING history cannot write"
// (the 2026-02→08 regression: expanding a Verify entry POSTed to /api/verify,
// deducted a credit, and wrote fresh AuditLog+ChatHistory rows — invisible in
// review for six months). A user-confirmed delete is not a read-path write; a
// re-run POST still is. So the guard keeps everything that pins the original
// regression and carves out exactly the one sanctioned mutation:
//   * NO POST / PUT / PATCH anywhere in the page (unchanged);
//   * EXACTLY ONE DELETE, and it targets /api/history/ (the sanctioned call);
//   * the re-run helper stays pinned gone by name (unchanged);
//   * positive controls: still a live read surface (unchanged).
// The filename keeps "readonly" for continuity of the ledger references that
// point here (TECH_DEBT / BACKLOG / recon baton); the property it now pins is
// the narrowed one stated in line 1.
//
// ─────────────────────────────────────────────────────────────────────────────
// THE BUSINESS RULE (CLAUDE.md Rule 17)
// ─────────────────────────────────────────────────────────────────────────────
// WHAT BREAKS IF THIS FAILS: reading your own history writes new history.
//
// From the initial commit (631b6e5, 2026-02-13) until 2026-08-17, expanding a
// Verify entry on /history POSTed to /api/verify to re-fetch the interaction
// list, because only a count roll-up was ever stored. Over the four systems
// that grew around it afterwards, that one fetch came to run a DIFFERENT query
// than the original, render with NO Option-C attribution, deduct a credit and
// write a fresh AuditLog + ChatHistory row, and fail silently once quota ran
// out. None of that is visible in review — a `fetch` with `method: 'POST'`
// inside a display helper reads like data loading. It survived six months.
//
// ─────────────────────────────────────────────────────────────────────────────
// ⚠️ SCOPE OF WHAT THIS PROBE PROVES  (2026-08-17, wording corrected 08-18)
// ─────────────────────────────────────────────────────────────────────────────
// This probe reads THE SOURCE TEXT OF pages/history.tsx AND NOTHING ELSE. It
// does not walk the transitive mount tree. Green here means "the only mutation
// ORIGINATING in this page's own source is the sanctioned per-entry delete".
// It does NOT mean "this page cannot otherwise write": mounting it still
// reaches /api/share/create (ShareModal via ShareButton), /api/checkout/dodo
// (ProFeatureOverlay / Navbar), /api/subscription/cancel (Navbar via
// PageShell) and /api/bug-report (BugReportButton via PageShell). All are
// user-initiated actions in components this page composes — not read-path
// writes, and not this probe's subject.
//
// 🔴 DO NOT WIDEN THIS PROBE TO THE MOUNT TREE. It would then fail on ordinary
// chrome, and a probe that fails on ordinary chrome gets deleted inside a
// month — taking the assertion that actually matters with it. The scope is
// narrow ON PURPOSE. Widen the SENTENCE you write about it instead.

import { readFileSync } from "node:fs";

const SRC_PATH = new URL("../../pages/history.tsx", import.meta.url);
const raw = readFileSync(SRC_PATH, "utf8");

// Strip comments and JSX comment blocks BEFORE matching. This repo has been
// bitten three times by prose satisfying a substring check; the paragraphs
// above contain POST and DELETE several times — without stripping, this probe
// would fail on its own explanation.
const code = raw
  .replace(/\/\*[\s\S]*?\*\//g, " ")   // /* … */ and JSX {/* … */} bodies
  .replace(/^\s*\/\/.*$/gm, " ");      // // line comments

const FORBIDDEN = ["POST", "PUT", "PATCH"];   // DELETE is sanctioned — see below

const checks = [];
const add = (name, ok, observed) => checks.push([name, ok, observed]);

// ── Property 1: no read-path mutating verb in the page ──────────────────────
for (const verb of FORBIDDEN) {
  // `method: 'POST'` in any quoting style.
  const re = new RegExp(`method\\s*:\\s*['"\`]${verb}['"\`]`, "i");
  const hit = re.exec(code);
  add(`no ${verb} request in pages/history.tsx`, hit === null,
    hit ? code.slice(Math.max(0, hit.index - 60), hit.index + 40).replace(/\s+/g, " ") : "—");
}

// Belt and braces: no forbidden verb passed via a variable or helper either.
add("no forbidden verb string anywhere in the page's code",
  !FORBIDDEN.some((v) => new RegExp(`['"\`]${v}['"\`]`).test(code)),
  FORBIDDEN.filter((v) => new RegExp(`['"\`]${v}['"\`]`).test(code)).join(", ") || "—");

// ── Property 2: exactly ONE DELETE, and it is the sanctioned endpoint ───────
const deleteVerbs = code.match(/['"`]DELETE['"`]/g) || [];
add("exactly one DELETE verb string (the sanctioned per-entry delete)",
  deleteVerbs.length === 1, `${deleteVerbs.length} occurrence(s)`);
// The one DELETE must sit in a fetch whose URL is /api/history/{id} — a
// DELETE aimed anywhere else is NOT sanctioned and must fail here.
add("the DELETE fetch targets /api/history/{id}",
  /fetch\s*\(\s*`[^`]*\/api\/history\/\$\{[^`]*`\s*,\s*\{\s*method:\s*'DELETE'/.test(code), "—");

// ── The specific regression, pinned by name so it cannot come back quietly ──
add("the live re-run helper is gone", !/fetchVerifyDetails/.test(code), "—");
add("no verifyDetails state", !/verifyDetails/.test(code), "—");

// ── POSITIVE CONTROLS ───────────────────────────────────────────────────────
// Without these, every assertion above is satisfied by an empty or deleted
// file. The page must still be a live read surface.
const fetches = code.match(/fetch\s*\(/g) || [];
add("the page still fetches (it is a read surface, not an empty one)",
  fetches.length >= 2, `${fetches.length} fetch call(s)`);
add("it still reads /api/history", /\/api\/history/.test(code), "—");
add("it still reads /api/user/status", /\/api\/user\/status/.test(code), "—");
add("it still renders the stored answer", /item\.answer/.test(code), "—");
// And a control on the stripper itself: the page's own JSX comments must be
// removed. Verified against a marker that exists in the source ONLY inside a
// comment, so if stripping ever silently stops working this fails rather than
// quietly widening what the checks above see.
const commentOnlyMarker = "Footer: share + per-entry delete";
add("comment stripping is actually working",
  raw.includes(commentOnlyMarker) && !code.includes(commentOnlyMarker),
  raw.includes(commentOnlyMarker) ? "marker present in raw, stripped from code" : "marker not in source — update this control");

let failed = 0;
for (const [name, ok, observed] of checks) {
  if (!ok) failed++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${ok ? "" : `  (observed: ${observed})`}`);
}
console.log(`\n${checks.length - failed}/${checks.length} passed`);
process.exit(failed === 0 ? 0 : 1);
