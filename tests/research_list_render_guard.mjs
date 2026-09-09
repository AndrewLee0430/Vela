// Guard: markdown lists on /research and /history render as LISTS — bullets,
// numbers, indent, marker colour — on the three live ReactMarkdown wrappers,
// through ONE narrow CSS rule set (HISTORY HONESTY car segment 4b, founder
// ruling 2026-09-09 = Option B: narrow list rules; the typography plugin stays
// unregistered; the orphan `.markdown-content` class is NOT reused).
//
// WHAT BREAKS IF THIS FAILS (CLAUDE.md Rule 17/19): `@tailwindcss/typography`
// is a dependency that was NEVER registered (`tailwind.config.js` `plugins: []`),
// so every `prose …` class on the two pages generates NO CSS, and Tailwind
// preflight's `ol,ul{list-style:none;margin:0;padding:0}` flattens every
// markdown `- ` / `1. ` list into plain lines — while the server-rendered share
// page shows bullets for the same markdown (TECH_DEBT [OTHER][P3] "prose is a
// NO-OP", surfaced 2026-09-03). The fix is a NEW class `.vela-md-list` in
// styles/globals.css scoped to ul / ol / li / li::marker ONLY, carried by the
// three wrappers that feed <ReactMarkdown>. If a wrapper loses the class, that
// surface silently goes flat again. If the rule set grows a heading / p / a /
// code rule, the "narrow" ruling is broken (that is Option A's blast radius —
// typography 0.5.19 would also wrap inline code in literal backticks). If the
// class lands on a pre-wrap wrapper or the dead MarkdownRenderer, scope drifted.
// If the plugin gets registered, both pages change everywhere `prose` is
// written. If the COMPILED bundle loses the rules (content-glob / @layer
// tree-shaking — exactly what happened to `.markdown-content`), the class is a
// no-op just like `prose` was, and the source-level checks cannot see it.
//
// No test runner -> the pages and the stylesheet are checked as SOURCE (comments
// stripped); the markdown pipeline is EXECUTED with the pages' exact plugin set;
// the compiled bundle under out/ is READ (fails LOUD when absent — Rule 18).
// Run: node tests/research_list_render_guard.mjs   (also run by
// tests/test_research_list_render.py inside the pytest count)
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join, relative } from 'node:path';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import rehypeRaw from 'rehype-raw';

const failures = [];
function check(cond, msg) { if (!cond) failures.push(msg); }
// Comments are blanked, NOT removed: every newline inside them survives so the
// line numbers in a failure message are the file's real lines (Rule 25).
const blank = (m) => m.replace(/[^\n]/g, ' ');
const stripComments = (src) => src
  .replace(/\{\/\*[\s\S]*?\*\/\}/g, blank)    // JSX {/* … */}
  .replace(/\/\*[\s\S]*?\*\//g, blank)        // /* … */
  .replace(/^\s*\/\/.*$/gm, blank);           // // …
const ROOT = fileURLToPath(new URL('..', import.meta.url));
const read = (rel) => readFileSync(join(ROOT, rel), 'utf8');

const CLASS = 'vela-md-list';
const PLUGIN_SET_RE = /<ReactMarkdown remarkPlugins=\{\[remarkGfm, remarkBreaks\]\} rehypePlugins=\{\[rehypeRaw\]\}>/g;

// Every `className="… prose max-w-none …"` wrapper, classified by what it feeds:
// 'markdown' = a <ReactMarkdown> follows within 12 lines; 'prewrap' = a
// whitespace-pre-wrap <p> follows (the legacy paragraph paths, NO markdown).
function proseWrappers(src) {
  const lines = src.split('\n');
  const out = [];
  lines.forEach((text, i) => {
    const m = text.match(/className="([^"]*\bprose max-w-none\b[^"]*)"/);
    if (!m) return;
    let kind = 'unknown';
    for (let j = i + 1; j <= Math.min(i + 12, lines.length - 1); j++) {
      if (lines[j].includes('<ReactMarkdown')) { kind = 'markdown'; break; }
      if (lines[j].includes('whitespace-pre-wrap')) { kind = 'prewrap'; break; }
    }
    out.push({ line: i + 1, className: m[1], classes: m[1].split(/\s+/), text, kind });
  });
  return out;
}

const researchSrc = stripComments(read('pages/research.tsx'));
const historySrc = stripComments(read('pages/history.tsx'));
const research = proseWrappers(researchSrc);
const history = proseWrappers(historySrc);

// -- (a) the THREE live ReactMarkdown wrappers carry the class, and keep the
//        inline token object whose --tw-prose-bullets / -counters the markers read
const rMd = research.filter((w) => w.kind === 'markdown');
const hMd = history.filter((w) => w.kind === 'markdown');
check(rMd.length === 2, `pages/research.tsx: expected 2 prose wrappers feeding <ReactMarkdown> (sections + streaming/no-section), found ${rMd.length} — update this guard if a render path was added or removed`);
check(hMd.length === 1, `pages/history.tsx: expected 1 prose wrapper feeding <ReactMarkdown> (research sections), found ${hMd.length} — update this guard if a render path was added or removed`);
for (const w of rMd) {
  check(w.classes.includes(CLASS), `pages/research.tsx:${w.line} ReactMarkdown wrapper lacks "${CLASS}" — markdown lists render FLAT on /research`);
  check(w.text.includes('style={proseStyle}'), `pages/research.tsx:${w.line} ReactMarkdown wrapper no longer applies style={proseStyle} — the ::marker colour reads its --tw-prose-bullets / --tw-prose-counters`);
}
for (const w of hMd) {
  check(w.classes.includes(CLASS), `pages/history.tsx:${w.line} ReactMarkdown wrapper lacks "${CLASS}" — markdown lists render FLAT on /history`);
  check(w.text.includes('style={researchProseStyle}'), `pages/history.tsx:${w.line} ReactMarkdown wrapper no longer applies style={researchProseStyle} — the ::marker colour reads its --tw-prose-bullets / --tw-prose-counters`);
}
for (const [name, src, obj] of [['pages/research.tsx', researchSrc, 'proseStyle'], ['pages/history.tsx', historySrc, 'researchProseStyle']]) {
  const m = src.match(new RegExp(`const ${obj} = \\{([\\s\\S]*?)\\} as React\\.CSSProperties`));
  check(!!m, `${name}: the ${obj} token object was not found — the ::marker colours read --tw-prose-bullets / --tw-prose-counters from it`);
  if (m) {
    check(m[1].includes("'--tw-prose-bullets'"), `${name}: ${obj} no longer sets --tw-prose-bullets (ul markers lose their colour in both schemes)`);
    check(m[1].includes("'--tw-prose-counters'"), `${name}: ${obj} no longer sets --tw-prose-counters (ol markers lose their colour in both schemes)`);
  }
}

// -- (b) scope: the two pre-wrap wrappers and the dead MarkdownRenderer do NOT
//        carry it, and the class appears exactly 3 times across the frontend
const hPre = history.filter((w) => w.kind === 'prewrap');
check(hPre.length === 2, `pages/history.tsx: expected 2 pre-wrap prose wrappers (research no-section + explain legacy), found ${hPre.length} — update this guard`);
for (const w of hPre) check(!w.classes.includes(CLASS), `pages/history.tsx:${w.line} pre-wrap wrapper carries "${CLASS}" — scope drift: no list can exist inside a whitespace-pre-wrap <p>`);
check([...research, ...history].every((w) => w.kind !== 'unknown'), 'a prose wrapper could not be classified (neither <ReactMarkdown> nor whitespace-pre-wrap within 12 lines) — update this guard');
check(!read('components/MarkdownRenderer.tsx').includes(CLASS), `components/MarkdownRenderer.tsx carries "${CLASS}" — it is a dead component (0 importers); the scope is the three live wrappers only`);
function walk(dir, acc = []) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p, acc); else if (/\.(tsx?|jsx?)$/.test(name)) acc.push(p);
  }
  return acc;
}
const hits = [];
for (const f of ['pages', 'components', 'utils'].flatMap((d) => walk(join(ROOT, d)))) {
  const n = (stripComments(readFileSync(f, 'utf8')).match(new RegExp(CLASS, 'g')) || []).length;
  if (n) hits.push(`${relative(ROOT, f).replace(/\\/g, '/')}:${n}`);
}
const total = hits.reduce((s, h) => s + Number(h.split(':').pop()), 0);
check(total === 3, `"${CLASS}" appears ${total} time(s) across pages/ components/ utils/ (${hits.join(', ') || 'nowhere'}) — expected exactly 3 (the live ReactMarkdown wrappers)`);

// -- (c) styles/globals.css: the rule set exists, is list-only, sits where it
//        beats preflight, and the orphan .markdown-content block is untouched
const css = stripComments(read('styles/globals.css'));
const rules = [];
const ruleRe = /([^{}]+)\{([^{}]*)\}/g;
let rm;
while ((rm = ruleRe.exec(css))) {
  for (const sel of rm[1].split(',').map((s) => s.trim()).filter(Boolean)) {
    if (sel.includes('.' + CLASS)) rules.push({ sel: sel.replace(/\s+/g, ' '), body: rm[2].replace(/\s+/g, ' ').trim() });
  }
}
const bySel = Object.fromEntries(rules.map((r) => [r.sel, r.body]));
check(rules.length > 0, `styles/globals.css defines no .${CLASS} rule at all`);
const ul = bySel[`.${CLASS} ul`], ol = bySel[`.${CLASS} ol`], li = bySel[`.${CLASS} li`];
const ulm = bySel[`.${CLASS} ul > li::marker`], olm = bySel[`.${CLASS} ol > li::marker`];
check(!!ul && /list-style-type:\s*disc\b/.test(ul), `.${CLASS} ul must set list-style-type: disc (preflight sets none)`);
check(!!ul && /padding-left:\s*1\.5rem\b/.test(ul), `.${CLASS} ul must set padding-left: 1.5rem — the share page value (api/templates/q_base.jinja2 .vela-prose ul/ol)`);
check(!!ol && /list-style-type:\s*decimal\b/.test(ol), `.${CLASS} ol must set list-style-type: decimal (preflight sets none)`);
check(!!ol && /padding-left:\s*1\.5rem\b/.test(ol), `.${CLASS} ol must set padding-left: 1.5rem — the share page value`);
check(!!li && /\bmargin(-top|-bottom)?:/.test(li), `.${CLASS} li must set a vertical margin`);
check(!!ulm && /color:\s*var\(--tw-prose-bullets\b/.test(ulm), `.${CLASS} ul > li::marker must read var(--tw-prose-bullets) — the token both pages set inline, so the marker follows the page's colour scheme`);
check(!!olm && /color:\s*var\(--tw-prose-counters\b/.test(olm), `.${CLASS} ol > li::marker must read var(--tw-prose-counters) — same reason`);
const ALLOWED_SEL = new Set([`.${CLASS} ul`, `.${CLASS} ol`, `.${CLASS} li`, `.${CLASS} ul > li::marker`, `.${CLASS} ol > li::marker`]);
const ALLOWED_PROP = new Set(['list-style-type', 'padding-left', 'margin', 'margin-top', 'margin-bottom', 'color']);
for (const r of rules) {
  check(ALLOWED_SEL.has(r.sel), `styles/globals.css: selector "${r.sel}" is outside the ruling's scope — ul / ol / li / li::marker ONLY (no heading, p, a, code, strong, hr, blockquote)`);
  for (const decl of r.body.split(';').map((d) => d.trim()).filter(Boolean)) {
    const prop = decl.split(':')[0].trim();
    check(ALLOWED_PROP.has(prop), `styles/globals.css: "${r.sel}" declares "${prop}" — outside the list-only scope`);
  }
}
// Where it lives: inside `@layer components` (emitted at the @tailwind components
// position, AFTER preflight) — and the selectors are (0,1,1) against preflight's
// (0,0,1), so they win on specificity regardless of order.
const layerIdx = css.indexOf('@layer components');
const firstIdx = css.indexOf('.' + CLASS);
check(layerIdx > -1 && firstIdx > layerIdx, `styles/globals.css: the .${CLASS} rules must sit inside an @layer components block (after preflight in the emitted order)`);
check(firstIdx > css.indexOf('@tailwind base'), `styles/globals.css: the .${CLASS} rules precede @tailwind base`);
check(/\.markdown-content ul \{[^}]*list-style-type: disc;[^}]*padding-left: 2em;/.test(css), 'the orphan .markdown-content block (globals.css:22-80) was altered — the ruling leaves it as-is, flagged not touched');

// -- (d) the typography plugin stays UNREGISTERED (Option A ruled out 2026-09-09)
const tw = stripComments(read('tailwind.config.js'));
check(/plugins:\s*\[\s*\]/.test(tw), 'tailwind.config.js: plugins is no longer empty — Option A (register @tailwindcss/typography) was ruled OUT 2026-09-09: 0.5.19 wraps inline code in literal backticks and restyles headings / paragraphs / links on every prose site');
check(!/require\(['"]@tailwindcss\/typography/.test(tw), 'tailwind.config.js registers @tailwindcss/typography — ruled out 2026-09-09');

// -- (e) the COMPILED bundle (out/_next/static/css) carries the rules and still
//        has no typography output — the class must survive the content glob and
//        @layer tree-shaking (what silently emptied .markdown-content)
const cssDir = join(ROOT, 'out', '_next', 'static', 'css');
const cssFiles = existsSync(cssDir) ? readdirSync(cssDir).filter((f) => f.endsWith('.css')) : [];
check(cssFiles.length > 0, 'out/_next/static/css/*.css not found — run `npm run build` first; this check pins the COMPILED bundle, not the source (Rule 18: a missing build is a failure, not a skip)');
if (cssFiles.length) {
  const bundle = cssFiles.map((f) => readFileSync(join(cssDir, f), 'utf8')).join('\n');
  check(new RegExp(`\\.${CLASS} ul\\s*\\{[^}]*list-style-type:\\s*disc`).test(bundle), `compiled CSS lacks \`.${CLASS} ul{list-style-type:disc…}\` — the class was tree-shaken (content glob / @layer) or the bundle is stale: rebuild`);
  check(new RegExp(`\\.${CLASS} ol\\s*\\{[^}]*list-style-type:\\s*decimal`).test(bundle), `compiled CSS lacks \`.${CLASS} ol{list-style-type:decimal…}\` — tree-shaken or stale: rebuild`);
  check(new RegExp(`\\.${CLASS} ul\\s*>\\s*li::marker\\s*\\{[^}]*var\\(--tw-prose-bullets`).test(bundle), `compiled CSS lacks the .${CLASS} ul > li::marker rule reading --tw-prose-bullets`);
  check(new RegExp(`\\.${CLASS} ol\\s*>\\s*li::marker\\s*\\{[^}]*var\\(--tw-prose-counters`).test(bundle), `compiled CSS lacks the .${CLASS} ol > li::marker rule reading --tw-prose-counters`);
  check(/ol,ul\s*\{[^}]*list-style:\s*none/.test(bundle), 'preflight `ol,ul{list-style:none}` is gone from the bundle — the rules were designed to BEAT it by specificity, not to rely on its absence; re-derive');
  const proseSel = (bundle.match(/\.prose[\s{:.,>\[-]/g) || []).length;
  check(proseSel === 0, `compiled CSS contains ${proseSel} .prose selector(s) — the typography plugin got registered`);
  const twDecl = (bundle.match(/--tw-prose-[a-z-]+\s*:/g) || []).length;
  check(twDecl === 0, `compiled CSS contains ${twDecl} --tw-prose-* DECLARATION(s) — only var() READS are expected (the two ::marker rules)`);
  const twReads = (bundle.match(/var\(--tw-prose-(bullets|counters)\b/g) || []).length;
  check(twReads === 2, `compiled CSS has ${twReads} var(--tw-prose-bullets|counters) read(s), expected exactly 2 (one per ::marker rule)`);
}

// -- (f) the markdown pipeline the pages use EMITS list elements — the rules
//        above style <ul>/<ol>/<li>; if remark-breaks (or a plugin change) ever
//        flattened a `- ` list into <p> + <br>, the CSS would have nothing to hit
for (const [name, src, expected] of [['pages/research.tsx', researchSrc, 2], ['pages/history.tsx', historySrc, 1]]) {
  const n = (src.match(PLUGIN_SET_RE) || []).length;
  check(n === expected, `${name}: ${n} <ReactMarkdown> call(s) with the exact plugin set [remarkGfm, remarkBreaks] + [rehypeRaw], expected ${expected} — the pipeline below is executed with that set; update both together`);
}
const render = (md) => renderToStaticMarkup(React.createElement(ReactMarkdown, { remarkPlugins: [remarkGfm, remarkBreaks], rehypePlugins: [rehypeRaw] }, md));
const bullets = render('Intro:\n- alpha\n- beta');            // the LLM shape: NO blank line before the list
check(/<ul>\s*<li>alpha<\/li>\s*<li>beta<\/li>\s*<\/ul>/.test(bullets), `a "- " list did not reach the DOM as <ul><li> through the pages' plugin set: ${bullets.replace(/\n/g, '\\n')}`);
const numbers = render('Intro:\n1. one\n2. two');
check(/<ol>\s*<li>one<\/li>\s*<li>two<\/li>\s*<\/ol>/.test(numbers), `a "1. " list did not reach the DOM as <ol><li> through the pages' plugin set: ${numbers.replace(/\n/g, '\\n')}`);
check(render('line one\nline two').includes('<br'), "remark-breaks is not active in the executed pipeline (no <br> for a soft break) — the guard is not running the pages' plugin set");

if (failures.length) {
  console.error(`research_list_render_guard: ${failures.length} failure(s)`);
  for (const f of failures) console.error('  - ' + f);
  process.exit(1);
}
console.log('research_list_render_guard: all checks passed');
