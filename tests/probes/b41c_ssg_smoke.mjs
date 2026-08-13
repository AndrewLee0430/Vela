// B4.1c SSG smoke — asserts what the STATIC EXPORT actually ships, not what
// the source intends. Run after `npm run build` (reads out/index.html).
//
// Rule 20: this is committed evidence (script + its small result), not scratch.
// Usage: node tests/probes/b41c_ssg_smoke.mjs
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../../out/index.html", import.meta.url), "utf8");

const HEADLINE = "Ask in your language. Decisions grounded in evidence.";
const SUB_FRAGMENT = "Access authoritative medical evidence in the language you know best";

const count = (needle) => html.split(needle).length - 1;

const checks = [
  // Content: one static H1 + one sub, each exactly once
  ["panel headline present exactly once", count(HEADLINE) === 1, count(HEADLINE)],
  ["panel sub present exactly once", count(SUB_FRAGMENT) === 1, count(SUB_FRAGMENT)],

  // Retired slideshow: no panelLine copy, no dots, no diagnostics handle
  ["no panelLine markup/ids", !/panelLine|panel-line/i.test(html), "—"],
  ["no dots markup", !/panel-dot|data-dot|aria-label="[^"]*dot/i.test(html), "—"],
  ["no __panelDiag handle", !html.includes("__panelDiag"), "—"],
  ["no gsap/ScrollTrigger reference", !/gsap|ScrollTrigger/i.test(html), "—"],
  ["no pin-spacer", !/pin-spacer/i.test(html), "—"],

  // Pills carry the three try* labels
  ["pill: Try Research", count("Try Research") === 1, count("Try Research")],
  ["pill: Try Verify", count("Try Verify") === 1, count("Try Verify")],
  ["pill: Try Explain", count("Try Explain") === 1, count("Try Explain")],

  // Containers at 64rem (max-w-5xl), and the old 80rem container is gone
  ["panel + cards containers at max-w-5xl (2)", count("max-w-5xl") === 2, count("max-w-5xl")],
  ["no max-w-7xl on landing", count("max-w-7xl") === 0, count("max-w-7xl")],

  // Gap reduction + hero
  ["hero at min-h-[90vh]", html.includes("min-h-[90vh]"), "—"],
  ["panel section pt-12 md:pt-16", /pt-12\s+md:pt-16/.test(html), "—"],
  ["panel section pb-16 md:pb-20", /pb-16\s+md:pb-20/.test(html), "—"],

  // Unchanged surroundings still render
  ["chevron scroll hint still present", /animate-bounce/.test(html), "—"],
];

let failed = 0;
for (const [name, ok, observed] of checks) {
  if (!ok) failed++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${ok ? "" : `  (observed: ${observed})`}`);
}
console.log(`\n${checks.length - failed}/${checks.length} passed`);
process.exit(failed === 0 ? 0 : 1);
