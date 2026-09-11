// PROBE (Rule 20) — HISTORY RENDER LEFTOVERS car segment 1, item A.
//
// WHAT IT MEASURES: what the /history no-section research path actually PRODUCES
// for the gate's real Dev-branch rows, before vs after the reroute. The "before"
// is the stored text printed verbatim inside a whitespace-pre-wrap <p>; the
// "after" is that same text through the EXACT plugin set pages/history.tsx now
// uses ([remarkGfm, remarkBreaks] + [rehypeRaw]) and the REAL shared parser /
// strip from utils/researchSections.ts — transpiled and executed, never
// re-implemented, so this cannot drift from the page.
//
// WHY A PROBE AND NOT A GUARD: the guard pins the SEAM (which wrapper, which
// plugins, which const). This answers "will the founder SEE a difference on
// row 2345 and row 175", which is a question about stored data, not about code.
//
// INPUT (not committed — it is Dev-DB row text): a JSON file {id: answerText},
// dumped SELECT-only from the Dev branch after a DATABASE_URL host gate.
// OUTPUT (committed, small): element counts + bounded excerpts per row.
//
// Run: node tests/probes/history_render_leftovers/render_no_section_rows.mjs \
//        <rows.json> [out.json]
import { readFileSync, writeFileSync } from 'node:fs';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import rehypeRaw from 'rehype-raw';
import ts from 'typescript';

const rows = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const outPath = process.argv[3] || null;

const rsSrc = readFileSync(new URL('../../../utils/researchSections.ts', import.meta.url), 'utf8');
const rs = await import(
  'data:text/javascript,' +
  encodeURIComponent(ts.transpileModule(rsSrc, { compilerOptions: { module: 'ESNext', target: 'ES2020' } }).outputText)
);

const render = (md) =>
  renderToStaticMarkup(
    React.createElement(ReactMarkdown, { remarkPlugins: [remarkGfm, remarkBreaks], rehypePlugins: [rehypeRaw] }, md)
  );

const results = {};
for (const [id, raw] of Object.entries(rows)) {
  const clean = raw ? rs.stripLlmDisclaimer(raw) : '';
  const sections = clean ? rs.parseResearchSections(clean) : null;
  const html = render(clean);
  const el = (t) => (html.match(new RegExp(`<${t}[ >]`, 'g')) || []).length;
  const counts = {
    ul: el('ul'), ol: el('ol'), li: el('li'), strong: el('strong'), em: el('em'),
    h1: el('h1'), h2: el('h2'), h3: el('h3'), p: el('p'), br: el('br'), a: el('a'),
  };
  // markers the OLD pre-wrap path printed literally to the reader
  const literal = {
    bold_markers: (raw.match(/\*\*/g) || []).length,
    bullet_lines: (raw.match(/^\s*[-*] /gm) || []).length,
    numbered_lines: (raw.match(/^\s*\d+\. /gm) || []).length,
    blank_line_breaks: (raw.match(/\n\s*\n/g) || []).length,
  };
  results[id] = {
    path: sections === null ? 'no-section' : `sections(${sections.length})`,
    chars_stripped: raw.trim().length - clean.length,
    rendered_elements: counts,
    literal_markers_in_stored_text: literal,
    stored_excerpt: raw.slice(0, 200),
    rendered_excerpt: html.slice(0, 300),
  };
  console.log('='.repeat(72));
  console.log(`ROW ${id} — path=${results[id].path} stripped=${results[id].chars_stripped} chars`);
  console.log('LITERAL markers the pre-wrap path showed the reader:', JSON.stringify(literal));
  console.log('RENDERED elements:', JSON.stringify(counts));
  console.log('--- stored (first 200) ---');
  console.log(JSON.stringify(raw.slice(0, 200)));
  console.log('--- rendered (first 300) ---');
  console.log(html.slice(0, 300));
}

if (outPath) {
  writeFileSync(outPath, JSON.stringify({ derived_at: process.env.VELA_HEAD || 'see baton', rows: results }, null, 1), 'utf8');
  console.log('\nwrote', outPath);
}
