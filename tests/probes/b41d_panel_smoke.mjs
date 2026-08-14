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
// is checked separately. Extended again at B4.2 (demo still) and B4.3
// (recolor / 92vh / CTA), then at B4.3 R4 when the still became a VIDEO.
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

// B4.3 R4 — the Research demo VIDEO replaces the B4.2 still. Every filename is
// asserted LITERALLY: a probe that only checked "a <video> exists" would pass
// against a placeholder, and one that only checked "a poster attribute exists"
// would pass with the poster still pointing at the retired PNG.
const DEMO_SRC = "/media/research-demo.mp4";
const DEMO_POSTER = "/media/research-demo-poster.jpg";
const RETIRED_PNG = "/media/demo-research-20260814.png";
// <video> has no alt attribute; panelDemoAlt is carried across as aria-label.
const DEMO_ALT = "Screenshot of a Research answer with citations.";

const countIn = (haystack, needle) => haystack.split(needle).length - 1;
const count = (needle) => countIn(text, needle);
const countHtml = (needle) => countIn(html, needle);

// The panel's media slot, sliced out so "no <img> survives here" is a check on
// the SLOT rather than on a fixed-width window that a longer tag would slide
// past. Ends at the section boundary: the cards section below has its own
// markup and must not leak into the assertion.
const mediaSlot = (() => {
  const i = html.indexOf("data-reveal-media");
  if (i < 0) return "";
  const j = html.indexOf("</section>", i);
  return html.slice(i, j < 0 ? html.length : j);
})();

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

  // ── B4.3 R4 demo VIDEO ────────────────────────────────────────────────────
  ["demo video src present exactly once", countHtml(DEMO_SRC) === 1, countHtml(DEMO_SRC)],
  ["exactly one <video> element on the page", countHtml("<video") === 1, countHtml("<video")],
  ["the <video> is inside the panel media slot", mediaSlot.includes("<video"), "—"],
  [
    "poster is the committed jpg, exactly once",
    countHtml(`poster="${DEMO_POSTER}"`) === 1,
    countHtml(`poster="${DEMO_POSTER}"`),
  ],

  // ── The B4.2 still is GONE, not merely unreferenced by the <video> ────────
  // A surviving <img> would double the media and re-ship 859 KB below the fold.
  ["retired B4.2 PNG no longer referenced", countHtml(RETIRED_PNG) === 0, countHtml(RETIRED_PNG)],
  ["no <img> survives in the panel media slot", !mediaSlot.includes("<img"), "—"],

  // ── Accessibility: alt did not simply vanish in the swap ──────────────────
  // Raw HTML, not the extracted text: aria-label lives in an ATTRIBUTE, and the
  // tag-stripping above deletes attributes along with the tag.
  [
    "panelDemoAlt carried across as aria-label",
    countHtml(`aria-label="${DEMO_ALT}"`) === 1,
    countHtml(`aria-label="${DEMO_ALT}"`),
  ],

  // ── Playback contract ─────────────────────────────────────────────────────
  // Without muted the autoplay policy rejects play(); without playsinline iOS
  // takes the video fullscreen the moment it starts. React emits the attribute
  // as `playsInline` (capital I) — HTML attribute names are case-insensitive,
  // so this is correct markup, but the check must be too.
  ["video is muted", /<video[^>]*\smuted[=\s>]/i.test(html), "—"],
  ["video is playsinline", /<video[^>]*\splaysinline[=\s>]/i.test(html), "—"],
  ["video loops", /<video[^>]*\sloop[=\s>]/i.test(html), "—"],
  // preload="none" is the whole mobile-data story: the 1.92 MB is not fetched
  // until the panel is scrolled to, and never at all below md, where the poster
  // is the media and playback never starts.
  ['video is preload="none"', /<video[^>]*preload="none"/i.test(html), "—"],
  // The guarantee is "never plays off-screen". An autoplay ATTRIBUTE starts the
  // video as soon as it parses and would hand that guarantee to a browser
  // heuristic (Chrome defers off-screen muted autoplay; Firefox does not).
  // Playback is IntersectionObserver-driven instead, so the attribute must be
  // absent — this check is what stops someone "fixing" it back in.
  ["video carries NO autoplay attribute (observer-driven)", !/<video[^>]*\sautoplay/i.test(html), "—"],
  // NOT "IntersectionObserver appears in the bundle" — useFadeIn already uses
  // one, so that check passes with usePanelVideo deleted outright: Rule 17 dead
  // weight. These two discriminate. useFadeIn's observer is threshold .15 and
  // nothing else on the landing page calls .play(), so each of these is 1 only
  // while the viewport gate exists. The 0?\. tolerates either minifier form.
  [
    "viewport gate ships (its own observer at threshold .25, not useFadeIn's .15)",
    (bundle.match(/threshold:0?\.25/g) || []).length === 1,
    (bundle.match(/threshold:0?\.25/g) || []).length,
  ],
  [
    "playback is JS-driven (.play() present exactly once)",
    countIn(bundle, ".play()") === 1,
    countIn(bundle, ".play()"),
  ],

  // ── Zero CLS, carried across from B4.2 with the REAL encode dimensions ────
  // 1440x812 is what ffprobe reports for research-demo.mp4. Reusing the PNG's
  // 1975x1114 would reserve a 0.08%-wrong box and squash the frame.
  ['video carries width="1440"', /<video[^>]*width="1440"/.test(html), "—"],
  ['video carries height="812"', /<video[^>]*height="812"/.test(html), "—"],
  [
    "explicit aspect-ratio restates the encode ratio (not UA-dependent)",
    /aspect-ratio:\s*1440\s*\/\s*812/.test(html),
    "—",
  ],
  [
    "retired PNG geometry is gone (no 1975/1114 box, no aspect- class)",
    !/(?:width|height)="(?:1975|1114)"/.test(html) && !html.includes("aspect-[1975/1114]"),
    "—",
  ],

  // ── The B4.3 reveal still wraps the media, unchanged ──────────────────────
  [
    "demo media ships VISIBLE (no inline opacity/transform)",
    !/data-reveal-media[^>]*style="[^"]*(?:opacity|transform)/.test(html),
    "—",
  ],
  ["demo media is NOT word-revealed", !/data-reveal-media[\s\S]{0,400}?data-reveal-word/.test(html), "—"],
  // Alpha-agnostic on purpose — B4.3 raised it /15 -> /20 because the panel
  // lightened. What must not regress is that it stays a TOKEN, not a literal.
  ["hairline border is token-based (no literal)", /border-paper\/\d+/.test(html), "—"],

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
  // Two now: the card pill AND the B4.3 panel CTA (same key, by design).
  ["pill: Try Research (card + panel CTA)", count("Try Research") === 2, count("Try Research")],
  ["pill: Try Verify", count("Try Verify") === 1, count("Try Verify")],
  ["pill: Try Explain", count("Try Explain") === 1, count("Try Explain")],

  // ── B4.3 recolor / single-viewport / CTA ─────────────────────────────────
  ["panel uses the new bg-panel token", html.includes("bg-panel"), "—"],
  ["panel no longer borrows bg-text", !/rounded-3xl bg-text/.test(html), "—"],
  ["min-h-[80vh] removed", !html.includes("md:min-h-[80vh]"), "—"],
  ["panel capped at md:max-h-[92vh]", html.includes("md:max-h-[92vh]"), "—"],
  ["panel has a definite md:h-[92vh] (flex-1 needs it)", html.includes("md:h-[92vh]"), "—"],
  [
    "media claims the remainder (md:flex-1 + md:min-h-0)",
    html.includes("md:flex-1") && html.includes("md:min-h-0"),
    "—",
  ],
  [
    "CTA pill present exactly once, href=/research",
    countHtml('href="/research"') === 2,
    countHtml('href="/research"'),
  ],
  ["CTA reuses the tryResearch string (no new key)", count("Try Research") === 2, count("Try Research")],
  ["CTA is the inverted tone (bg-paper text-panel)", html.includes("bg-paper text-panel"), "—"],
  ["media hairline raised to paper/20", html.includes("border-paper/20"), "—"],

  // ── Geometry ──────────────────────────────────────────────────────────────
  ["panel + cards containers at max-w-5xl (2)", countHtml("max-w-5xl") === 2, countHtml("max-w-5xl")],
  ["no max-w-7xl on landing", countHtml("max-w-7xl") === 0, countHtml("max-w-7xl")],
  ["hero at min-h-[90vh]", html.includes("min-h-[90vh]"), "—"],
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
