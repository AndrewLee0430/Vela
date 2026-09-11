# HISTORY RENDER LEFTOVERS car — opened 2026-09-11 (Segment 1 = items A + C 📋 GATE 9/9 founder-PASS — PUSHING · Segment 2 = item B, TRANSPORT RULED (ii), not started)

> **STATUS — Segment 1: 📋 GATE §2 PASSED 9/9 founder-PASS (2026-09-11) — PUSHING.** Rows 1–9 PASS; row 10 is the machine row, already filled (CSS hash `466e58439a1a5bbd`). **Provenance:** founder blanket statement 「Gate 沒問題」 in the 2026-09-11 conversation, transcribed under the closeout authorization (zh-TW transcription precedent, as at §6 / §8 / §10 / §13 of the history-honesty baton); **no per-row screenshots were retained** — stated so the record does not imply evidence it does not have. **ROW 5 RULING (founder, 2026-09-11): the paragraph-spacing inversion is ACCEPTED as parity with /research.** Markdown paragraphs sit flush because preflight sets `p{margin:0}` and nothing re-adds it; the 4b narrow ruling STANDS and `.vela-md-list` is **NOT** widened with a `p` rule. **SEGMENT 2 TRANSPORT RULED — (ii)**, see §3. This commit is the pre-push docs commit; prod is still fly 252 until the ship entry below is written.

> *(build-time status, kept as the record)* ~~**STATUS — Segment 1 (item A: reroute /history's no-section research path through `<ReactMarkdown>` · item C: delete the dead `components/MarkdownRenderer.tsx` and the orphan `.markdown-content` block): 🔧 BUILT LOCAL, NOT pushed, NOT deployed (2026-09-11).**~~ *(the rest of that line, also historical: prod still fly 252 = `07e704dbb625898f79f3fa899edfdf46aeb879dd` at machine version 253; code commits on `main` ahead of `origin`; "Gate §2 is BLANK — the founder fills it"; push and deploy founder-only. The gate is now filled — see §2.)*

**Authority:** `TECH_DEBT.md` → `[OTHER][P3] markdown not rendered on /history's no-section path` (filed 2026-09-07) · `[OTHER][P3] dead component — components/MarkdownRenderer.tsx` and `[OTHER][P3] orphan CSS — .markdown-content` (both filed 2026-09-09) · the **2026-09-11 read-only probe** (this session, HEAD `430ef01`) · founder ruling 2026-09-11. CLAUDE.md Rules 12 / 17 / 18 / 19 / 20 / 24 / 25 apply.

**Workflow Step 0 note:** no prior `docs/batons/` baton was the input to this segment — the inputs were the three TECH_DEBT entries, the 2026-09-11 read-only probe and the founder's build brief — so `check_baton.py` had nothing to check on the way in. This file is the car's baton from here on.

---

## Segments

| # | segment | scope in one line | status |
|---|---|---|---|
| 1 | **A + C — render leftovers** | **A**: /history's research no-section path renders through the SAME `<ReactMarkdown>` + `.vela-md-list` wrapper the sections path uses, fed the STRIPPED markdown (Rule 19 parity with /research). **C**: delete `components/MarkdownRenderer.tsx` (0 importers since the commit that created it) and the `.markdown-content` `@layer base` block (0 users since `cae7b31`, 0 bytes in the bundle) | **📋 GATE §2 9/9 founder-PASS 2026-09-11 — PUSHING** (build record §1; gate §2 transcribed; readbacks §4 after the deploy) |
| 2 | **B — Explain legacy disclaimer** | 291 of 852 Dev-branch Explain rows take the pre-wrap fallback and render NO disclaimer, while JSON rows render their stored one (`[HONESTY][P3]`, filed 2026-09-09) | **TRANSPORT RULED — (ii) read-time server field** (founder, 2026-09-11); **NOT started**, see §3 |

**Segment 2 was blocked on one decision, not on effort — and that decision is now MADE (founder, 2026-09-11): option (ii).** The 16 Explain disclaimer strings live only in Python (`api/i18n/explain_strings.py` → `EXPLAIN_DISCLAIMERS`, 16 keys, re-derived 2026-09-11). There is **no frontend Explain disclaimer source at all** — `git grep -n -i "explain.*disclaimer" -- pages/ components/ utils/` returns only the two `pages/history.tsx` lines that read the STORED string. The two options put to the founder were:

- **(i) frontend copy** — a `utils/` module holding the 16 Explain strings, keyed by the UI `lang`, plus a **parity guard** against the Python map. Cost: a second copy of 16 medical strings; the 2026-05 share/explore disclaimer drift (14 of 16 locales) is the precedent for why a copy without a parity check drifts. **→ DECLINED 2026-09-11.**
- **(ii) read-time server field** — `/api/history` fills a `disclaimer` on legacy Explain rows from `get_disclaimer(lang)` at READ time, so the frontend keeps rendering a stored string and there stays exactly ONE source. Cost: a server change on the history read path, and the language key is the request's, not the row's. **→ ✅ RULED 2026-09-11.**

**Founder ruling 2026-09-11 — (ii).** Rationale, recorded as the founder's, not as an AI recommendation: **one source of truth**, no second copy of the 16 Explain strings, and no parity guard to maintain. **Accepted cost:** a server change on the history read path, and a caption keyed to the REQUEST's language rather than the row's. Scope sketch in **§3** — ruled, **not started**.

---

## §0 Repo assertion (Rule 24) — Segment 1 build session, 2026-09-11

```
git rev-parse --show-toplevel  ->  C:/Users/andre/projects/Vela
git rev-parse HEAD             ->  430ef01e257986856f86f950e07a300bce872d81
git status --short             ->  the 4 known untracked only
                                   (.superpowers/, 3 public/media/*.png)
```

Both asserted as the first tool call of the session and stated in the reply, before any read of the codebase. HEAD matched the expected value in the brief, so no STOP.

---

## §1 Segment 1 build record (AI-written, facts and pointers only) — 2026-09-11

### 1a. Founder ruling 2026-09-11 — VERBATIM (from the build brief)

> 「照你建議」 — i.e. **scope = A + C**; **item B DEFERRED** to its own segment pending a transport ruling, (i) frontend copy of the 16 Explain strings + parity guard **vs** (ii) `/api/history` read-time `disclaimer` field for legacy Explain rows via `get_disclaimer(lang)`.

Basis named by the brief: the 2026-09-11 read-only probe (same session, same HEAD).

### 1b. Rule 25 — cited (probe / brief / ledgers) vs derived at `430ef01` BEFORE editing

Every line was re-derived at HEAD before a single edit. **Unit is stated per row** — a line number, a count of rows, a count of files, a count of rules.

| # | claim | cited | derived at `430ef01` | unit | match |
|---|---|---|---|---|---|
| 1 | item A block | `pages/history.tsx:394-416` | the `return (` is at **:395**, the block ends at **:416**; **:394** is the closing `}` of the `if (sections)` branch. The inner wrapper actually replaced is **:398-410** | line | **NO — off by one at the start**; the brief's range included the preceding brace |
| 2 | item A pre-wrap `<p>` | `:398` (TECH_DEBT, at `8802a8d`) / `:399` (4b baton) | wrapper `<div>` opens **:398**, its `className` is **:399**, the `<p>` is **:407** | line | rotted since filing; both old numbers point inside the right block |
| 3 | /research no-section site | `research.tsx:615` (TECH_DEBT) | **:600** wrapper, **:601** `<ReactMarkdown>` | line | rotted |
| 4 | /history sections `<ReactMarkdown>` | `:378` (TECH_DEBT) | **:384** | line | rotted |
| 5 | Explain legacy pre-wrap (NOT touched) | `:451-466`, `<p>` at `:463` | wrapper **:455**, `<p>` **:463**, block **:453-466** | line | **matches** |
| 6 | `.markdown-content` block | `styles/globals.css:22-80`, 13 rules | `@layer base {` opens **:22**, closes **:80**; **13** rule blocks, **all 13** `.markdown-content` — brace-matched, and asserted in the delete script that no non-`.markdown-content` selector lives inside | lines / rules | **matches** |
| 7 | the comment naming the block | `globals.css:260-261` | the sentence spans **:259-261** ("The orphan" begins at the end of :259) | line | **NO — the cited range cuts the sentence's first clause** |
| 8 | 4b guard count checks | `:84` `hMd===1` · `:105` `hPre===2` · `:122` total `===3` · `:195` plugin-set `1` · `:91` style · `:108` MarkdownRenderer · `:162` `.markdown-content` | **all seven at exactly those lines** | line | **matches, 7/7** |
| 9 | disclaimer guard pre-wrap assertion | `history_research_disclaimer_guard.mjs:78` | **:78** | line | **matches** |
| 10 | pytest baseline | "record says 442/28" | **442 passed / 28 skipped**, exit 0, 302.33 s — RE-RUN, not inherited | tests | **matches** |
| 11 | lint baseline | 22 (7e/15w) | **22 problems (7 errors, 15 warnings)**, normalized to a sorted `file:line:col severity rule` set for an identity diff, not a count diff | problems | **matches** |
| 12 | CSS bundle hash | `466e58439a1a5bbd` | **`466e58439a1a5bbd.css`, 46 861 bytes** on disk before the build | hash / bytes | **matches** |
| 13 | `MarkdownRenderer.tsx` importers | 0 | **0** — `git grep` finds only its 5 self-references; `git log -S MarkdownRenderer -- pages components` returns **only `a5b399f`**, the commit that ADDED it, so it has never had an importer | importers | **matches, and stronger than cited** |
| 14 | files a C cleanup touches | "2 files" (probe §C3) | **2 product files** (`components/MarkdownRenderer.tsx`, `styles/globals.css`) **+ 2 test files** (`research_list_render_guard.mjs`, `test_research_list_render.py`) = **4** | files | **NO — the cited 2 counted product files only; the unit was never stated** |
| 15 | the no-section population | probe: 54 rows (4 `research_v1` + 50 legacy) | **54**, re-derived this session on the same Dev branch; **34 of the 54** carry markdown markers | rows | **matches** |

**Two cited line ranges were wrong at the edges (rows 1 and 7) and one cited count was right about product files but silent about its unit (row 14).** None changed the work; all three are recorded because silence about a difference is indistinguishable from not having looked.

### 1c. Item A — the exact change (`pages/history.tsx`, ONE branch, two hunks)

**Hunk 1 — one stripped string, read by both paths.** Before, the strip was applied only to the parser's input, so the BRANCH DECISION saw stripped text while the RENDER saw raw text:

```diff
                                     const markdown = researchParsed?.answer ?? item.answer;
-                                    const sections = markdown ? parseResearchSections(stripLlmDisclaimer(markdown)) : null;
+                                    const cleanMarkdown = markdown ? stripLlmDisclaimer(markdown) : '';
+                                    const sections = cleanMarkdown ? parseResearchSections(cleanMarkdown) : null;
```

**Hunk 2 — the no-section render.** The wrapper is now byte-identical in class list and style object to the sections path at `:383` and to /research at `:600`:

```diff
                                             {trustBlock}
-                                            <div
-                                                className="prose max-w-none prose-sm prose-headings:font-semibold"
-                                                style={{
-                                                    color: "rgb(var(--color-text) / 0.8)",
-                                                    '--tw-prose-headings': 'rgb(var(--color-text))',
-                                                    '--tw-prose-bold': 'rgb(var(--color-text))',
-                                                    '--tw-prose-bullets': 'rgb(var(--color-text) / 0.5)',
-                                                } as React.CSSProperties}
-                                            >
-                                                <p className="whitespace-pre-wrap text-sm leading-relaxed" style={{ color: "rgb(var(--color-text) / 0.75)" }}>
-                                                    {markdown}
-                                                </p>
+                                            <div className="prose max-w-none prose-sm prose-headings:font-semibold prose-h2:text-base vela-md-list" style={researchProseStyle}>
+                                                <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>{cleanMarkdown}</ReactMarkdown>
                                             </div>
                                             <p className="text-xs mt-3" style={{ color: 'rgb(var(--color-text) / 0.35)' }}>
                                                 {getResearchDisclaimer(lang)}
```

`{trustBlock}` above, the `getResearchDisclaimer(lang)` line and `{citationBlock}` below are **unchanged** — the diff shows them as context, not as edits. The inline 4-token style object is gone because `researchProseStyle` (`:49-58`) is a superset of it: it adds `--tw-prose-links`, `--tw-prose-counters`, `--tw-prose-code` and `--tw-prose-hr`, and the two `::marker` rules in `.vela-md-list` read `--tw-prose-bullets` / `--tw-prose-counters` from it.

**NO third path was added.** The brief's instruction and the probe agree against the TECH_DEBT entry's own fix-path text: the branch is decided by `sections === null` **alone**, never by `researchParsed === null`. Deriving it on the Dev branch — **1113 of 1175 research rows are legacy AND take the sections path**, so a "legacy → pre-wrap" variant would be a path for a population that does not exist. The entry's fix-path sentence is corrected in TECH_DEBT rather than implemented.

**A2 — the Explain legacy pre-wrap block at `:453-466` is NOT touched.** It is item B's territory. The 4b guard now asserts BOTH halves of that: `hPre.length === 1` (one pre-wrap wrapper survives) and an explicit check that the Explain half of the page still contains `whitespace-pre-wrap`, so a later segment cannot delete it silently.

### 1d. Rule 19 — what /research renders AROUND its no-section answer, carried or not

The probe's table, re-marked after the change. **Rows that moved are bold.**

| Around the answer | /research | /history no-section, AFTER | status |
|---|---|---|---|
| `<ReactMarkdown>` with `[remarkGfm, remarkBreaks]` + `[rehypeRaw]` | `:600-601` | **`:410-411`, the identical call** | **CARRIED** |
| `.vela-md-list` class | `:600` | **`:410`** | **CARRIED** |
| prose token object | `proseStyle`, 8 tokens `:570-579` | **`researchProseStyle`, the same 8 tokens `:49-58`** | **CARRIED** (was 4 of 8) |
| the text is the STRIPPED answer | `cleanAnswer` `:568` | **`cleanMarkdown`** | **CARRIED** (0 of 54 rows affected today — carried anyway) |
| trust signal above | `:564-566` from live flags | `:409` from the persisted flag; UNKNOWN → neither | carried at segment 3 |
| disclaimer line under the body | `:603-607` keyed `detectedLang` | `:412-414` keyed UI `lang` | carried at segment 4a |
| citation panel + English-references caption | right column `:681-689` | `:367-376`, only with ≥1 stored citation | carried at segment 3; N/A for legacy rows (none stored) |
| page-level third disclaimer | `:699-703` | none | **N/A** — per page, not per row |
| FeedbackBar · PDF export · AnonymousUpgradeCTA · LocaleHintPanel · streaming cursor | `:611`, `:616`, `:618-633`, `:634`, `:697` | none | **N/A** — live-query surfaces |
| Share | Navbar ShareContext `:219-241` | footer ShareButton `:557-568` | carried, different mechanism |
| blank line between paragraphs | collapsed | **now collapsed too** | **PARITY — accepted consequence, see below** |

**The paragraph-spacing inversion, stated as a fact and verified, not assumed.** Tailwind preflight sets `blockquote,dd,dl,figure,h1,h2,h3,h4,h5,h6,hr,p,pre{margin:0}` — grepped verbatim out of the compiled bundle — and **nothing re-adds a `p` margin**: `.vela-md-list p` = **0** rules and `.prose p` = **0** rules in that same bundle (the typography plugin is unregistered by the 4b ruling, and `.vela-md-list` is list-only by that ruling). So markdown paragraphs render as separate `<p>` blocks with **zero vertical gap**. The old `whitespace-pre-wrap` paragraph preserved the stored `\n\n` as visible blank lines. Net: on the no-section path, **lists and bold now render, and paragraph gaps close** — which is exactly what /research has always looked like. It is **parity, and it is a visible change**; gate row 5 exists for it. Per-row numbers: dev row **175** has **5** paragraphs, row **2345** has **4**.

Widening `.vela-md-list` with a `p` margin would fix the gap and would also break the 4b "narrow" ruling — guard (c)'s `ALLOWED_SEL` / `ALLOWED_PROP` sets reject any selector or property outside `ul / ol / li / li::marker`. **Not done. Flagged in §1h for the founder.**

### 1e. Item A — real effect, on the real rows (Rule 17, probe committed)

`tests/probes/history_render_leftovers/render_no_section_rows.mjs` executes the REAL `utils/researchSections.ts` (transpiled, not re-implemented) and the page's exact plugin set over the actual stored text of the gate's rows. Result JSON: `tests/probes/history_render_leftovers/no_section_render_20260911.json` (2 878 bytes). Input row text is Dev-DB content and is NOT committed.

| dev row | path | literal markers the pre-wrap path SHOWED the reader | elements the reroute RENDERS | chars stripped |
|---|---|---|---|---|
| **175** (legacy, no-section) | no-section | `**` ×14 · `- ` lines ×12 | `ul` 3 · `li` 12 · `strong` 7 · `p` 5 | **0** |
| **2345** (`research_v1`, no-section) | no-section | `**` ×2 · `- ` lines ×6 | `ul` 2 · `li` 6 · `strong` 1 · `p` 4 | **0** |
| **2347** (CONTROL, sections) | sections(2) | — | `h2` 2 · `ul` 6 · `li` 19 · `strong` 5 · `p` 6 | **0** |

`chars stripped = 0` on all three independently reproduces the probe's "0 of 54 rows carry a strippable LLM disclaimer" — the strip is carried for correctness, and changes nothing visible today.

### 1f. Item C — the exact deletion

- **`components/MarkdownRenderer.tsx` — DELETED** (`git rm`, 48 lines). Added by `a5b399f` (2026-03-12) in a 9-file commit; touched once since, by `b5c7771` (2026-05-27, the theme token migration). `git log -S MarkdownRenderer -- pages components` → **only `a5b399f`**: it never had an importer. It sat inside the Tailwind content glob (`tailwind.config.js:4-7` scans `./components/**`) carrying the fullest `prose` variant set in the repo plus 9 `--tw-prose-*` tokens, all inert.
- **`styles/globals.css` `@layer base { … }` at `:22-80` — DELETED** (59 lines + the trailing blank = 60 removed). The delete script brace-matched the block and asserted every selector inside it was `.markdown-content` before removing anything; **13 of 13**, nothing else lived in that layer. Last carrier removed by `cae7b31` (2026-03-06).
- **`styles/globals.css` `:259-261` — REWRITTEN.** The `.vela-md-list` comment said the orphan "is deliberately NOT reused" and pointed at `:22-80`; it now records that 4b declined to reuse it and that this segment deleted it, and names what it carried (h1–h6 sizes, 1em paragraph margins, a light-only `hr` colour `#e5e7eb`).

**C2 — the ordering hazard, from the probe's Rule 18 list, handled.** `tests/research_list_render_guard.mjs:108` was `check(!read('components/MarkdownRenderer.tsx').includes(CLASS), …)`, and `read()` is `readFileSync`: deleting the file first makes the guard **throw ENOENT and die**, which is not a failed check but a dead guard. The guard edit therefore landed **in the same commit as the delete, and was run green before committing**. Both C assertions were inverted rather than dropped — a deleted thing that comes back is now a loud failure:

```js
check(!existsSync(join(ROOT, 'components', 'MarkdownRenderer.tsx')),
  'components/MarkdownRenderer.tsx is back — it was deleted as dead code (0 importers); …');
check(!css.includes('.markdown-content'),
  'styles/globals.css defines .markdown-content again — it was deleted as an orphan (0 users, 0 bytes in the bundle); …');
```

`tailwind.config.js` is **untouched** — the content glob still scans `./components/**`, guard (d) still asserts `plugins: []`.

### 1g. Tests (TDD — RED watched first, then GREEN)

Phase A and phase C were driven separately so that **each commit is green on its own**.

**RED, phase A** (guards updated to the new expectations, pages still unchanged):

- `research_list_render_guard.mjs` → **7 failure(s)**: `hMd` 1≠2 · `hPre` 2≠1 · class total 3≠4 · history plugin-set count 1≠2 · the research branch still carries `whitespace-pre-wrap` · the branch makes 1 `<ReactMarkdown>` call, not 2 · the branch does not hoist `stripLlmDisclaimer(markdown)` into a const.
- `history_research_disclaimer_guard.mjs` → **2 failure(s)**: 1 `<ReactMarkdown>` render path, expected 2 · the branch still carries `whitespace-pre-wrap`.
- `history_render_fallback_guard.mjs` → **green throughout, by design** — it is the CONTROL: its subject is the parsers, and none of its logic changed.

**A guard bug caught by its own RED run, and fixed before GREEN.** The first RED printed *"the no-section `<ReactMarkdown>` is not fed **sections**"* — the loose regex `const (\w+) = [^;]*stripLlmDisclaimer\(markdown\)[^;]*;` had matched `const sections = markdown ? parseResearchSections(stripLlmDisclaimer(markdown)) : null`, capturing the PARSER's output as if it were the stripped text. The "does it hoist a const" check was therefore passing for the wrong reason (Rule 17: a check that passes against the wrong thing is dead weight). Tightened so the initializer must END at the strip call, with at most a ternary else-branch after it; the first RED count of 8 became the honest **7**. Recorded because the run that caught it is the reason to watch RED at all.

**GREEN, phase A:** all three guards pass after the two `pages/history.tsx` hunks. No rebuild was needed — item A adds no CSS, so guard (e)'s compiled-bundle checks were never invalidated.

**RED, phase C** (guard assertions inverted, file and CSS block still present): `research_list_render_guard.mjs` → **2 failure(s)**, one per inverted assertion. **GREEN** after `git rm` + the CSS block delete.

**Wording-only, zero logic:** `history_render_fallback_guard.mjs` had 6 messages and comments reading "pre-wrap path", which is now false for the research branch. All 6 rewritten to "no-section". **Proof of zero logic change**: with comment lines removed and every string literal masked, the before and after files are **byte-identical** (`diff` empty), and the `check(` count is **48 → 48**.

**Guard size:** `research_list_render_guard.mjs` **43 → 51** `check(` occurrences (+8) · `history_research_disclaimer_guard.mjs` **21 → 23** (+2) · `history_render_fallback_guard.mjs` **48 → 48** (0).

The rewritten disclaimer-guard assertion is stronger than the one it replaces: counting calls cannot see WHICH path lost its line, so it now pins the **order** — every `<ReactMarkdown>` path must be FOLLOWED by `getResearchDisclaimer(lang)` before the next path starts.

### 1h. Readbacks

| readback | before | after | note |
|---|---|---|---|
| `python -m pytest -q` | **442 passed / 28 skipped**, exit 0 (302.33 s) — DERIVED this session, not inherited | **442 passed / 28 skipped**, exit 0 (251.24 s) | **+0 tests**, as predicted: the guard changes ride the two existing pytest wrappers (`test_research_list_render.py`, `test_history_research_disclaimer.py`) rather than adding cases |
| `npx tsc --noEmit` | exit **0** | exit **0** | |
| `npm run lint` | **22 problems (7 errors, 15 warnings)** | **22 problems (7 errors, 15 warnings)** | problem set diffed by **identity** (file + line + col + severity + rule), sorted: **IDENTICAL**, not merely the same total |
| `npm run build` | — | exit **0**, "Compiled successfully in 81s", **Exporting (15/15)** | |
| CSS bundle hash | `466e58439a1a5bbd.css`, 46 861 bytes | **`466e58439a1a5bbd.css`, 46 861 bytes — UNCHANGED** | predicted before the build: both deleted things were already tree-shaken, and item A adds no CSS. A changed hash was the STOP condition; it did not change |
| bundle `.vela-md-list` | 7 | **7** | |
| bundle `markdown-content` | 0 | **0** | 0 before the delete too — the orphan never reached the bundle |
| bundle `prose-h2:pb-1` | 0 | **0** | the dead component's variant set was inert |
| bundle `.prose` selectors | 0 | **0** | plugin still unregistered |
| bundle `--tw-prose-*` declarations / `var()` reads | 0 / 2 | **0 / 2** | the two `::marker` rules |
| i18n keys | — | **+0** | no `i18n` / `locale` file in `git status --porcelain` |
| line endings | — | **LF-only on every touched file**, 0 CRLF, 0 bare CR (measured byte-wise; `git ls-files --eol` = `i/lf w/lf`) | the autocrlf warning is the usual cosmetic one |
| 3 `.mjs` guards | green at HEAD | **all 3 green** | |

`git diff HEAD --stat`: **7 files, 138 insertions, 151 deletions** — `components/MarkdownRenderer.tsx` −48 · `pages/history.tsx` +37/−… · `styles/globals.css` −69 net · 3 guards · 1 pytest wrapper.

### 1i. Flagged in passing, NOT fixed (collaboration principle #4 — the founder chooses)

1. **Paragraph gaps close to zero on the rerouted path** (§1d). Parity with /research, verified in the bundle. A `.vela-md-list p { margin: … }` rule would restore spacing on BOTH pages and would break the 4b "narrow" ruling that guard (c) enforces. Not done, not filed as new debt — it is a consequence of this change and belongs to the founder's gate row 5.
2. **`_EXPLAIN_PROMPT_FALLBACK` instructs the LLM to write a disclaimer** — `api/services/explain_service.py:66-72` ends "End with a short disclaimer in the same language.", which CLAUDE.md **Rule 10** forbids. Dormant: it is used only in the `FileNotFoundError` branch at `:74-79`, when `api/prompts/explain_system.md` is missing — and that file says the opposite twice (`:103`, `:238`). **Filed as a new `[OTHER][P3]`.**
3. **`_explain_history_payload` does not exist.** `TECH_DEBT.md` and the 4b baton both name it as the Explain history writer. `git grep` finds it in those two documents and nowhere in the code: Explain rows are written inline at `api/server.py:1706-1707` (`full_answer = json.dumps(event.content)`) and `:1717-1722`. **Corrected in the item B entry.**
4. **The Explain JSON write path predates its cited commit.** The entry dates it from `30bd0b5` (2026-05-07); the earliest JSON Explain row on the Dev branch is **2026-04-27**, ten days earlier. The legacy set runs 2026-03-22 → 2026-04-20 and is closed either way. Which commit actually started writing JSON is **not verified** — stated as unknown rather than guessed. **Corrected in the item B entry.**
5. **Both hedges in the item B entry are empty sets**, re-derived: JSON Explain rows with `items[]` but no `disclaimer` = **0**; rows that parse as JSON but lack `items[]` = **0**. So the pre-wrap population is exactly the 291 non-JSON legacy rows, and `answer NOT LIKE '{%'` and a real `JSON.parse` agree on that number.

### 1j. What this change does to OTHER documents' line citations (Rule 25, stated not silent)

`pages/history.tsx` is **+21 / −16 = net +5 lines**, and the shift is not uniform — it accumulates across three hunks. Derived old → new for every anchor the ledgers cite:

| old | new | what it is |
|---|---|---|
| ≤ 350 | unchanged | imports, parsers, `researchProseStyle`, the row header |
| 383 → | **398** | sections-path wrapper |
| 384 → | **399** | sections-path `<ReactMarkdown>` |
| 388-390 → | **403-405** | sections-path disclaimer line |
| **398-410** → | **REPLACED by 413-415** | the old pre-wrap block — this is the change |
| 423 → | **428** | Explain `try {` |
| 452 / 455 / 463 → | **457 / 460 / 468** | Explain legacy comment / wrapper / `<p>` |
| 485 / 541 → | **490 / 546** | expanded-content div / ShareButton comment |

The **closed** `history_honesty_car_20260903.md` baton cites several of these and was **NOT rewritten** — it is a historical record of a closed car, and CLAUDE.md's own convention is that line numbers rot and entries are found by title. Its fact-check reports **0 WRONG** and 48 DRIFTED, of which the `pages/history.tsx:423 → BLANK LINE` line is newly caused by this change; the rest predate it.

**One suppression was added**, with its reason, to `tests/probes/baton_check/suppressions.json`: `^components/MarkdownRenderer[.]tsx$`. Deleting a file makes every document that cites it — including the closed 4b baton, 4 mentions — fail `check_baton.py` forever with "NOT IN REPO", for a claim that is accurate history. The suppression hides the **citation**, never the file's return: `research_list_render_guard.mjs` (b) asserts the file stays absent, so a silent reappearance is still caught loudly. Without it, the new baton reported 1 load-bearing WRONG and the 4b baton would have started reporting one too.

---

## §2 Segment 1 — eye gate (TRANSCRIBED 2026-09-11 — founder 9/9 PASS; row 10 = machine)

**Recipe.** Two terminals from the repo root:

```bash
# terminal 1 — backend, auth skipped for local testing
TEST_MODE=true uvicorn api.server:app --reload --port 8000

# terminal 2 — frontend
npm run dev            # http://localhost:3000
```

Open `/history`, **hard-refresh first (Ctrl+Shift+R)** — the CSS bundle name is unchanged, so a stale cache looks identical to a working change. Expand the row named in each row's ID column. Toggle light/dark with the app's own scheme control.

**BEFORE screenshots (rows 1–4 only), if wanted:** `git stash push pages/history.tsx` → hard-refresh → shoot → `git stash pop`. Stash **only that file**; the guards are committed with the change and a stash of everything would make them RED while stashed.

⚠️ **There is already a stash on this repo** — `stash@{0}: On main: PHASE D partial work before crash`, pre-existing, not created by this segment. `git stash push` pushes the new entry to `stash@{0}` and moves that one to `stash@{1}`, so a plain `git stash pop` still pops the right thing — but check `git stash list` before and after, and do **not** pop twice.

| # | what to look at | what PASS means | PASS / FAIL + note |
|---|---|---|---|
| 1 | `/history`, **row 2345** (`research_v1`, no-section), **LIGHT** | Markdown RENDERS: `**bold**` is bold (1 site), `- ` lines are bullets with indent (6 items, 2 lists) — no literal asterisks or hyphens. The FallbackBanner is still ABOVE the answer. The disclaimer line is still BELOW it. No citation panel (the row has none) | **PASS** (founder) |
| 2 | same row, **DARK** | Same as row 1; bullet markers legible against the dark ground (they read `--tw-prose-bullets` from `researchProseStyle`) | **PASS** (founder) |
| 3 | `/history`, **row 175** (legacy, no-section — the 34-of-54 class that carries markdown markers), **LIGHT** | 12 bullets across 3 lists, 7 bold runs, no literal `**`. No trust signal (legacy = UNKNOWN), no citation panel. Disclaimer line below | **PASS** (founder) |
| 4 | same row, **DARK** | Same as row 3 | **PASS** (founder) |
| 5 | **PARAGRAPH SPACING** — row 2345 (or 175) on `/history` vs the same shape on `/research` | The accepted consequence: paragraph gaps are now CLOSED, matching /research. Judge whether "blank lines collapse, matches /research behaviour" is acceptable, or whether the tighter text is worse than the literal markers it replaced. *(A same-text /research comparison cannot be produced by re-running the query — a new answer is a new answer. Compare against the fly-248 §6 screenshot of 2345 if it was kept; otherwise judge the /research look-and-feel on any current answer.)* | **PASS — ACCEPTED as parity with /research** (founder, 2026-09-11). The flush paragraphs are the agreed trade for markdown actually rendering. **The 4b narrow ruling STANDS: `.vela-md-list` is NOT widened with a `p` rule**, so no heading / p / a / code rule enters the set and guard (c)'s ALLOWED_SEL / ALLOWED_PROP stay as they are. |
| 6 | **CONTROL** — `/history`, **row 2347** (sections path), **LIGHT** | UNCHANGED from fly 252: two section cards, `## ` headings, 19 bullets, disclaimer, citation panel | **PASS** (founder) |
| 7 | **CONTROL** — row 2347, **DARK** | UNCHANGED | **PASS** (founder) |
| 8 | **CONTROL** — `/history`, an **Explain legacy row (id 8)**, LIGHT **and** DARK | UNCHANGED — still the plain pre-wrap paragraph, still NO disclaimer. Item B is deferred; this row must look exactly as it did on fly 252 | **PASS** (founder) |
| 9 | **CONTROL (item C)** — `/research`, run any query whose answer has a list | UNCHANGED from fly 252: bullets / numbers with indent. Deleting the dead component and the orphan CSS must move nothing | **PASS** (founder) |
| 10 | **MACHINE ROW** — CSS bundle hash | `out/_next/static/css/` = **`466e58439a1a5bbd.css`, 46 861 bytes** — the same hash prod serves at fly 252. **Filled by Claude Code: ✅ CONFIRMED** (build after both changes; `markdown-content` 0 · `prose-h2:pb-1` 0 · `.vela-md-list` 7 · `.prose` selectors 0) | ✅ (machine) |

**Gate result: 9 / 9 founder-PASS** (rows 1–9) **+ row 10 machine-CONFIRMED = 10 / 10** · date **2026-09-11** · founder **AndrewLee0430**

**Provenance, stated plainly:** the founder's verdict was a single blanket statement — 「Gate 沒問題」 — not nine separate row calls, and **no screenshots were retained**. It is transcribed here under the closeout authorization using the same zh-TW transcription precedent as the history-honesty gates. Row 10 is the only row with machine evidence behind it (the CSS hash readback). A future reader should not read rows 1–9 as independently evidenced observations.

---

## §3 Segment 2 — RULED, NOT STARTED (founder transport ruling 2026-09-11)

**The ruling: option (ii).** `/api/history` fills a `disclaimer` on legacy Explain rows at READ time from `get_disclaimer(lang)`. Option (i), a frontend copy of the 16 Explain strings plus a parity guard, is **DECLINED**. Rationale, the founder's: **one source of truth**, no second copy of the 16 medical strings, no parity guard to maintain. **Accepted cost:** a server change on the history read path, and a caption keyed to the REQUEST's language rather than the row's.

**This section is a SCOPE SKETCH, not a plan and not a build.** Everything below is derived at `c710450`; nothing is written, nothing is decided beyond the transport itself.

### 3a. The endpoint, as it stands today

`api/server.py:2012` — `@app.get("/api/history", response_model=list[ChatHistoryEntry])`, whose handler signature takes exactly two dependencies: `creds` and `db`. The model is `ChatHistoryEntry` (`api/server.py:1991-2009`), **5 fields**: `id`, `session_type`, `question`, `answer`, `created_at`.

### 3b. ⚠️ The `response_model` implication — a SILENT failure if missed

The explicit `response_model` on this GET is not incidental: it was added by **founder ruling #5 on 2026-09-02** (the delete segment) specifically so `user_id` stopped being serialized. FastAPI therefore **filters the response to the model's declared fields**.

**Consequence for segment 2: setting a `disclaimer` on the row object is not enough — a field absent from `ChatHistoryEntry` is silently DROPPED, with a 200 and a well-formed body.** There is no error surface. So the field must be added to the model (optional, default `None`) in the same change, and a test must assert it survives the round trip through the endpoint rather than only that the handler set it.

This is the same shape as the segment-1 ENOENT hazard: the mechanism that is supposed to protect the change is the thing that hides it.

### 3c. The language key — an OPEN question, not a decided one

`get_disclaimer(lang)` needs a `lang`, and **`/api/history` currently receives no language input at all** — no body (it is a GET), no query parameter, no `Request`. So segment 2 has to choose how `lang` arrives. The existing helper `_resolve_response_language(body_value, request)` (`api/server.py:126-134`) resolves `body.response_language` → first `Accept-Language` tag → `"en"`; on a GET the first link is unavailable, so it would degrade to the header chain unless a query parameter is added.

**Not decided here.** What is already settled by the ruling is the honesty consequence, and it should be stated in the product's own terms: legacy Explain rows store **no** language, so the caption renders in the language the REQUEST resolves to, which can differ from the language the stored explanation is written in. That is the same trade segment 4a accepted for Research (baton §9c). JSON Explain rows keep rendering their STORED string, so on one page a legacy row's caption and a JSON row's caption can be in different languages.

### 3d. Population — derived, and it cannot grow

**291 of 852** Explain rows on the Dev branch take the pre-wrap path (`ep-spring-voice…`, SELECT-only, re-derived 2026-09-11). Both halves that the TECH_DEBT entry hedged on are **empty sets**: 0 JSON rows carry `items[]` without a `disclaimer`, and 0 rows parse as JSON but lack `items[]`. So the pre-wrap population is exactly the non-JSON legacy rows, `answer NOT LIKE '{%'` and a real `JSON.parse` agree, and 291 + 561 = 852 reconciles. The set runs **2026-03-22 → 2026-04-20** and is closed: every Explain row written since carries a stored disclaimer. **The prod count has never been read.**

### 3e. Guard shape

Mirror `tests/history_research_disclaimer_guard.mjs`: one disclaimer render inside the Explain branch's pre-wrap path, zero elsewhere, and the ORDER check segment 1 added (a render path must be FOLLOWED by its caption). Add a server-side test that a legacy row round-trips the field through the endpoint — that is the check that catches §3b. ⚠️ The Explain wording is **not** the Research wording, so `utils/researchDisclaimer.ts` must not be reused; a Research caption under an Explain answer would be the wrong sentence.

### 3f. Not in this segment

The Rule 10 `[OTHER][P3]` filed 2026-09-11 — `_EXPLAIN_PROMPT_FALLBACK` (`api/services/explain_service.py:66-72`) telling the LLM "End with a short disclaimer in the same language." — is adjacent but separate, and stays OPEN in TECH_DEBT.

---

**NOT pushed. NOT deployed.** Prod remains fly 252 (`07e704dbb625898f79f3fa899edfdf46aeb879dd`, machine v253).
