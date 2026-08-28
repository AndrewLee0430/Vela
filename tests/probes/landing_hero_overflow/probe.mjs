// Landing hero-spotlight horizontal-overflow probe — LIVE PROD measurement.
//
// WHY (2026-08-27 landing recon, Phase 0): the ledger disagrees with itself.
// A B4.1c-era flag (2026-08-13) records `.hero-spotlight` REAL horizontal
// scroll — scrollWidth 491 vs clientWidth 360 — while fly 232 (2026-08-14,
// `61d49f1` header bump) shipped `overflow-x-clip` (375px overflow 131→0,
// reproduced against prod) and every B4.2→B4.6 sweep since reads hOverflow 0.
// This probe adjudicates against live prod. NOTE 491 − 360 = 131: the flag's
// clientWidth 360 at a "375px" viewport is what a classic ~15px scrollbar
// does in desktop/headless Chrome — so this probe records BOTH clientWidth
// and innerWidth at every width, and measures 360 explicitly (the flag's own
// unit), not just 375.
//
// Rule 20: committed evidence — this script + result.json (small; values,
// widths, prod revision, date inside). Re-running against live prod produces
// a NEW snapshot, not the one the finding was based on.
//
// Method: Playwright, system Chrome (channel: "chrome"), headless, mobile UA
// + touch. The overflow number is document.scrollingElement.scrollWidth −
// clientWidth (0 = no horizontal scroll). Element rects are ALSO enumerated,
// with the caveat that getBoundingClientRect ignores ancestor clipping — an
// element extending past the right edge inside an `overflow-x-clip` wrapper
// is the fly-232 fix WORKING (B4.2: "extends to x=492 but is clipped"), not a
// regression; only the scrollWidth delta says whether scroll exists.
//
// Deps: playwright (not a repo dependency — any install location works):
//   PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i playwright@1.62  (anywhere)
//   PLAYWRIGHT_DIR=<that dir> node tests/probes/landing_hero_overflow/probe.mjs
// (resolved via createRequire: repo node_modules first, PLAYWRIGHT_DIR fallback)
import { writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";

let chromium;
try {
  ({ chromium } = createRequire(import.meta.url)("playwright"));
} catch {
  const dir = process.env.PLAYWRIGHT_DIR;
  if (!dir) throw new Error("playwright not resolvable — npm i playwright, or set PLAYWRIGHT_DIR=<dir whose node_modules has it>");
  ({ chromium } = createRequire(join(dir, "noop.js"))("playwright"));
}

// 2026-08-28 (landing build car, Phase 3b): PROBE_URL overrides the target so
// the same method runs against a local static-export serve (Gate 6 style,
// :4321). A local run skips the /health readback (static serve has none) and
// writes result_local.json — the committed result.json stays the fly-240
// PROD evidence and is never overwritten by a local run.
const URL_ = process.env.PROBE_URL || "https://vela.an-tho.com/";
const IS_LOCAL = Boolean(process.env.PROBE_URL);
const WIDTHS = [360, 375, 390];
const UA =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1";

const browser = await chromium.launch({ channel: "chrome", headless: true });
const result = {
  probe: "landing_hero_overflow",
  date: new Date().toISOString(),
  url: URL_,
  prod_revision: null,
  method:
    "playwright@1.62.1 channel=chrome headless; mobile UA + hasTouch; overflow = scrollingElement.scrollWidth - clientWidth; rect enumeration ignores ancestor clipping (see header)",
  widths: [],
};

// prod revision recorded INSIDE the run, not inherited from an earlier readback
if (!IS_LOCAL) {
  const ctx0 = await browser.newContext();
  const health = await (await ctx0.request.get("https://vela.an-tho.com/health")).json();
  result.prod_revision = health.revision;
  await ctx0.close();
} else {
  result.prod_revision = null;
  result.local_head = process.env.PROBE_HEAD || null;
}

for (const width of WIDTHS) {
  const ctx = await browser.newContext({
    viewport: { width, height: 800 },
    userAgent: UA,
    hasTouch: true,
    isMobile: true,
    deviceScaleFactor: 3,
  });
  const page = await ctx.newPage();
  await page.goto(URL_, { waitUntil: "networkidle", timeout: 45000 });
  await page.waitForTimeout(1500); // fonts/late layout settle
  const m = await page.evaluate(() => {
    const se = document.scrollingElement;
    const hero = document.querySelector(".hero-spotlight");
    const hr = hero ? hero.getBoundingClientRect() : null;
    const iw = window.innerWidth;
    const offenders = [];
    for (const el of document.querySelectorAll("*")) {
      const r = el.getBoundingClientRect();
      if (r.right > iw + 0.5 && r.width > 0) {
        const cls = (el.getAttribute("class") || "").trim().split(/\s+/).slice(0, 3).join(".");
        offenders.push({
          selector: el.tagName.toLowerCase() + (cls ? "." + cls : ""),
          right: Math.round(r.right * 10) / 10,
          width: Math.round(r.width * 10) / 10,
        });
      }
    }
    return {
      innerWidth: iw,
      clientWidth: se.clientWidth,
      scrollWidth: se.scrollWidth,
      hOverflow: se.scrollWidth - se.clientWidth,
      hero: hr
        ? { left: Math.round(hr.left * 10) / 10, right: Math.round(hr.right * 10) / 10, width: Math.round(hr.width * 10) / 10 }
        : "NOT FOUND",
      rects_beyond_right_edge: offenders.slice(0, 12),
      rects_beyond_right_edge_total: offenders.length,
    };
  });
  result.widths.push({ viewport_width: width, ...m });
  await ctx.close();
}
await browser.close();

const out = new URL(IS_LOCAL ? "./result_local.json" : "./result.json", import.meta.url);
writeFileSync(out, JSON.stringify(result, null, 2) + "\n");
console.log(JSON.stringify(result, null, 2));
