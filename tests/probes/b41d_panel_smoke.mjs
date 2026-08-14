// Landing panel SSG smoke — asserts what the STATIC EXPORT actually ships, not
// what the source intends. Run after `npm run build` (reads out/index.html).
//
// Rule 20: this is committed evidence (script + result), not scratch.
// Usage: node tests/probes/b41d_panel_smoke.mjs
//
// History: created at B4.1c as b41c_ssg_smoke.mjs (16/16); renamed and extended
// at B4.1d, when the panel copy gained per-word spans — which broke every
// raw-HTML substring assertion the B4.1c version relied on. Copy is therefore
// now checked against the DECODED TEXT CONTENT, and the markup that carries it
// is checked separately.
import { readFileSync, readdirSync } from "node:fs";

const html = readFileSync(new URL("../../out/index.html", import.meta.url), "utf8");

// The retired-machinery checks below must read the JS BUNDLE, not the document.
// index.html contains no application code at all (every script tag is JSON-LD,
// Clerk's CDN, __NEXT_DATA__ or a hashed src), so asserting "no gsap in
// index.html" is a check that cannot fail — it would report PASS with GSAP
// fully re-added and the panel pinned again. Rule 17: that is dead weight.
const chunkDir = new URL("../../out/_next/static/chunks/", import.meta.url);
const chunkFiles = [];
const collectChunks = (dir) => {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory()) collectChunks(new URL(`${e.name}/`, dir));
    else if (e.name.endsWith(".js")) chunkFiles.push(new URL(e.name, dir));
  }
};
collectChunks(chunkDir);
const bundle = chunkFiles.map((f) => readFileSync(f, "utf8")).join("\n");

// Tags out, entities decoded, whitespace collapsed — what a reader actually sees.
const text = html
  .replace(/<script[\s\S]*?<\/script>/gi, " ")
  .replace(/<[^>]+>/g, " ")
  .replace(/&#x27;|&#39;/g, "'")
  .replace(/&quot;/g, '"')
  .replace(/&amp;/g, "&")
  .replace(/&nbsp;/g, " ")
  .replace(/\s+/g, " ")
  .trim();

const HEADLINE = "Ask in your language. Decisions grounded in evidence.";
const SUB =
  "Access authoritative medical evidence in the language you know best, backed by sources you can verify.";
const RETIRED_SUB_TAIL = "with citations you can open and check";
// B4.2 — the Research demo still. The filename is asserted literally: a probe
// that only checked "an <img> exists" would pass against a placeholder.
const DEMO_SRC = "/media/demo-research-20260814.png";
const DEMO_ALT = "Screenshot of a Research answer with citations.";

const countIn = (haystack, needle) => haystack.split(needle).length - 1;
const count = (needle) => countIn(text, needle);
const countHtml = (needle) => countIn(html, needle);

// Word counts the reveal depends on: space-split, same rule as the component.
const HEADLINE_WORDS = HEADLINE.split(" ").length; // 8
const SUB_WORDS = SUB.split(" ").length; // 17
const revealSpans = countHtml("data-reveal-word");
const gradientSpans = countHtml("panel-gradient-text");

const checks = [
  // ── Copy: present exactly once, as readable text ──────────────────────────
  ["panel headline text present exactly once", count(HEADLINE) === 1, count(HEADLINE)],
  ["panel sub text present exactly once (B4.1d rewrite)", count(SUB) === 1, count(SUB)],
  [
    "retired sub tail now appears ONCE only (the Research card, not the panel)",
    count(RETIRED_SUB_TAIL) === 1,
    count(RETIRED_SUB_TAIL),
  ],

  // ── Reveal markup: every word wrapped, gradient on the headline only ──────
  [
    `every panel word is a reveal span (${HEADLINE_WORDS}+${SUB_WORDS})`,
    revealSpans === HEADLINE_WORDS + SUB_WORDS,
    revealSpans,
  ],
  ["gradient class on the headline words only", gradientSpans === HEADLINE_WORDS, gradientSpans],
  [
    "words ship VISIBLE — no inline opacity/transform in the export",
    !/data-reveal-word[^>]*style="[^"]*(?:opacity|transform)/.test(html),
    "—",
  ],
  // The separator between word spans must be a REAL space text node. Checked
  // against raw HTML on purpose: the tag-stripping above replaces every tag
  // with a space, so it silently re-inserts exactly the character a deleted
  // separator would have removed — the copy checks cannot see this regression.
  // Dropping it renders the headline as "Askinyourlanguage." (the spans are
  // inline-block, so no whitespace collapses in for them).
  [
    `word spans separated by real spaces (${HEADLINE_WORDS - 1}+${SUB_WORDS - 1} gaps)`,
    countHtml("</span> <span data-reveal-word") === HEADLINE_WORDS + SUB_WORDS - 2,
    countHtml("</span> <span data-reveal-word"),
  ],

  // ── B4.2 demo image ───────────────────────────────────────────────────────
  ["demo image present exactly once", countHtml(DEMO_SRC) === 1, countHtml(DEMO_SRC)],
  // Raw HTML, not the extracted text: alt lives in an ATTRIBUTE, and the
  // tag-stripping above deletes attributes along with the tag.
  ["demo alt text present", countHtml(`alt="${DEMO_ALT}"`) === 1, countHtml(`alt="${DEMO_ALT}"`)],
  // The no-CLS guarantee: explicit intrinsic dimensions AND an aspect-ratio
  // container. Losing either reintroduces layout shift on load; losing the
  // aspect-ratio also means the planned <video> swap becomes a layout change.
  ['img carries width="1975"', /<img[^>]*width="1975"/.test(html), "—"],
  ['img carries height="1114"', /<img[^>]*height="1114"/.test(html), "—"],
  ["container carries the intrinsic aspect-ratio", html.includes("aspect-[1975/1114]"), "—"],
  ['img is lazy + async', /<img[^>]*loading="lazy"/.test(html) && /<img[^>]*decoding="async"/.test(html), "—"],
  [
    "demo image ships VISIBLE (no inline opacity/transform)",
    !/data-reveal-media[^>]*style="[^"]*(?:opacity|transform)/.test(html),
    "—",
  ],
  [
    "demo image is NOT word-revealed",
    !/data-reveal-media[\s\S]{0,400}?data-reveal-word/.test(html),
    "—",
  ],
  ["hairline border is token-based (no literal)", html.includes("border-paper/15"), "—"],

  // ── Retired machinery stays retired (checked in the BUNDLE, not the doc) ──
  ["no panelLine markup/ids", !/panelLine|panel-line/i.test(html), "—"],
  ["no dots markup", !/panel-dot|data-dot|aria-label="[^"]*dot/i.test(html), "—"],
  ["no __panelDiag handle", !html.includes("__panelDiag") && !bundle.includes("__panelDiag"), "—"],
  [
    `no gsap/ScrollTrigger in any of ${chunkFiles.length} JS chunks`,
    !/ScrollTrigger|registerPlugin|from"gsap"|require\("gsap"\)/.test(bundle),
    "—",
  ],
  ["no pin-spacer", !/pin-spacer/i.test(html) && !/pin-spacer/i.test(bundle), "—"],

  // ── Pills ─────────────────────────────────────────────────────────────────
  ["pill: Try Research", count("Try Research") === 1, count("Try Research")],
  ["pill: Try Verify", count("Try Verify") === 1, count("Try Verify")],
  ["pill: Try Explain", count("Try Explain") === 1, count("Try Explain")],

  // ── Geometry ──────────────────────────────────────────────────────────────
  ["panel + cards containers at max-w-5xl (2)", countHtml("max-w-5xl") === 2, countHtml("max-w-5xl")],
  ["no max-w-7xl on landing", countHtml("max-w-7xl") === 0, countHtml("max-w-7xl")],
  ["hero at min-h-[90vh]", html.includes("min-h-[90vh]"), "—"],
  ["panel at md:min-h-[80vh] (B4.1d)", html.includes("md:min-h-[80vh]"), "—"],
  ["panel section pt-12 md:pt-16", /pt-12\s+md:pt-16/.test(html), "—"],
  ["panel section pb-16 md:pb-20", /pb-16\s+md:pb-20/.test(html), "—"],

  // ── Unchanged surroundings still render ───────────────────────────────────
  ["chevron scroll hint still present", /animate-bounce/.test(html), "—"],
];

let failed = 0;
for (const [name, ok, observed] of checks) {
  if (!ok) failed++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${ok ? "" : `  (observed: ${observed})`}`);
}
console.log(`\n${checks.length - failed}/${checks.length} passed`);
process.exit(failed === 0 ? 0 : 1);
