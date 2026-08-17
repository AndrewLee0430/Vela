// History page READ-ONLY guard — asserts that viewing history cannot write.
//
// Rule 20: this is committed evidence (script), not scratch.
// Usage: node tests/probes/history_readonly_smoke.mjs      (reads SOURCE, no build needed)
//
// ─────────────────────────────────────────────────────────────────────────────
// THE BUSINESS RULE (CLAUDE.md Rule 17)
// ─────────────────────────────────────────────────────────────────────────────
// WHAT BREAKS IF THIS FAILS: reading your own history writes new history.
//
// From the initial commit (631b6e5, 2026-02-13) until 2026-08-17, expanding a
// Verify entry on /history POSTed to /api/verify to re-fetch the interaction
// list, because only a count roll-up was ever stored. Over the four systems that
// grew around it afterwards, that one fetch came to:
//   * run a DIFFERENT query than the original — patient_context was dropped and
//     response_language never sent, so the "details" could be clinically
//     different from what the user saw, and could come back in English;
//   * render those interactions with NO Option-C attribution, making the history
//     surface less honest than the live Verify page;
//   * deduct a credit and write a fresh AuditLog + ChatHistory row — so the
//     history table recorded reads as if they were queries;
//   * fail silently to an empty Interactions block once quota ran out.
//
// None of that is visible in review. A `fetch` with `method: 'POST'` inside a
// display helper reads like data loading. It survived six months of review.
//
// 🔴 THIS GUARD IS NOT HERE TO FORBID A FUTURE MUTATION. If history genuinely
// needs to write — a per-entry delete is already scoped — whoever builds it must
// DELETE THIS PROBE DELIBERATELY, in the same commit, with the reasoning
// written down. Removing it IS the decision point. That is its entire job.
// (Same pattern as the Clerk non-destructive guard, tests/test_deletion_coverage.py.)
//
// ─────────────────────────────────────────────────────────────────────────────
// ⚠️ SCOPE OF WHAT THIS PROBE PROVES  (added 2026-08-17)
// ─────────────────────────────────────────────────────────────────────────────
// This probe reads THE SOURCE TEXT OF pages/history.tsx AND NOTHING ELSE.
// It does not read that file's imported components, and it does not walk the
// transitive mount tree. Green here means:
//
//     "no write ORIGINATES in this page's own source"
//
// It does NOT mean "this page cannot write", and the difference is not
// hypothetical. pages/history.tsx renders ShareButton, and clicking Share does
// issue a write. Mounting this page transitively reaches four distinct write
// endpoints:
//
//   /api/share/create        components/ShareModal.tsx:107
//                            ^ NOT ShareButton.tsx — that file has no fetch at
//                              all; it only renders the modal (:159). Anyone
//                              re-deriving this scope note will look in the
//                              wrong file first, as the first draft of it did.
//   /api/checkout/dodo       components/UpgradeModal.tsx:32
//                            ^ reachable from this page's OWN direct import,
//                              and again via ProFeatureOverlay and Navbar.
//   /api/subscription/cancel components/Navbar.tsx:138      (via PageShell)
//   /api/bug-report          components/BugReportButton.tsx:84 (via PageShell)
//
// Three of the four arrive through PageShell / ProFeatureOverlay — chrome this
// page never names. That is fine: a user clicking Share or Upgrade is not a
// read-path write, and the read-path write is the whole subject of this probe.
//
// 🔴 DO NOT WIDEN THIS PROBE TO THE MOUNT TREE. It would then fail on ordinary
// chrome, and a probe that fails on ordinary chrome gets deleted inside a
// month — taking the assertion that actually matters with it. The scope is
// narrow ON PURPOSE. Widen the SENTENCE you write about it instead.

import { readFileSync } from "node:fs";

const SRC_PATH = new URL("../../pages/history.tsx", import.meta.url);
const raw = readFileSync(SRC_PATH, "utf8");

// Strip comments and JSX comment blocks BEFORE matching. This repo has been
// bitten three times by prose satisfying a substring check — most recently the
// Clerk handler's own docstring, which says it does NOT call the deletion
// helper and thereby matched a search for that helper. The paragraph above this
// line contains the word POST several times; without stripping, this probe
// would fail on its own explanation.
const code = raw
  .replace(/\/\*[\s\S]*?\*\//g, " ")   // /* … */ and JSX {/* … */} bodies
  .replace(/^\s*\/\/.*$/gm, " ");      // // line comments

const MUTATING = ["POST", "PUT", "PATCH", "DELETE"];

const checks = [];
const add = (name, ok, observed) => checks.push([name, ok, observed]);

// ── The property: no mutating HTTP verb anywhere in the page ────────────────
for (const verb of MUTATING) {
  // `method: 'POST'` in any quoting style, and the bare fetch-options shorthand.
  const re = new RegExp(`method\\s*:\\s*['"\`]${verb}['"\`]`, "i");
  const hit = re.exec(code);
  add(`no ${verb} request in pages/history.tsx`, hit === null,
    hit ? code.slice(Math.max(0, hit.index - 60), hit.index + 40).replace(/\s+/g, " ") : "—");
}

// Belt and braces: some codebases pass the verb via a variable or a helper.
add("no mutating verb string anywhere in the page's code",
  !MUTATING.some((v) => new RegExp(`['"\`]${v}['"\`]`).test(code)),
  MUTATING.filter((v) => new RegExp(`['"\`]${v}['"\`]`).test(code)).join(", ") || "—");

// The specific regression, pinned by name so it cannot come back quietly.
add("the live re-run helper is gone", !/fetchVerifyDetails/.test(code), "—");
add("no verifyDetails state", !/verifyDetails/.test(code), "—");

// ── POSITIVE CONTROLS ───────────────────────────────────────────────────────
// Without these, every assertion above is satisfied by an empty or deleted
// file. "No POST" must mean "reads, and only reads" — not "does nothing".
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
const commentOnlyMarker = "/* Verify */";
add("comment stripping is actually working",
  raw.includes(commentOnlyMarker) && !code.includes("Verify */"),
  raw.includes(commentOnlyMarker) ? "marker present in raw, stripped from code" : "marker not in source — update this control");

let failed = 0;
for (const [name, ok, observed] of checks) {
  if (!ok) failed++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${ok ? "" : `  (observed: ${observed})`}`);
}
console.log(`\n${checks.length - failed}/${checks.length} passed`);
process.exit(failed === 0 ? 0 : 1);
